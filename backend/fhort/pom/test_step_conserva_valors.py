"""El canvi a STEP CONSERVA els valors vigents (DIAGNOSI_GRADING_POP, veredicte 30/07).

Una regla STEP viu dels seus `valors_step`. Passar-hi des de LINEAR deixava el calaix buit,
i llavors `_apply_rule` retornava `None` per a CADA cel·la del POM; el `continue` de
`services.py:277` no reescrivia res i els `GradedSpec` de la regla anterior es quedaven a la
taula. La fila es CONGELAVA: números que ja no venien de cap regla, immunes a qualsevol
re-derivació posterior — inclosa la d'una base nova.

El fix sembra `valors_step` des dels specs VIGENTS del model per a aquell POM, com a DELTES
respecte de la base (contracte de `services.py:911`, aritmètica a
`grading_utils.sembra_valors_step`). La fila STEP neix amb els mateixos números que ja es
veien, ara editables I re-emesos.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.pom.grading_utils import sembra_valors_step
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem
from fhort.pom.services import generate_graded_specs


class SembraValorsStepPuraTest(TenantTestCase):
    """L'aritmètica sola: absoluts → deltes en format C, sense ORM pel mig."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    RUN = ['XXS', 'XS', 'S', 'M', 'L']

    def test_run_contigu_delta_per_aresta(self):
        """+1 uniforme: cada talla porta el seu pas, i el signe és el del format C
        (positiu cap enfora, també cap avall, perquè el motor RESTA en aquell sentit)."""
        valors = {'XXS': 98.0, 'XS': 99.0, 'S': 100.0, 'M': 101.0, 'L': 102.0}
        self.assertEqual(
            sembra_valors_step(valors, self.RUN, 'S'),
            {'XXS': 1.0, 'XS': 1.0, 'M': 1.0, 'L': 1.0},
        )

    def test_pas_variable_es_respecta(self):
        """No hi ha cap mitjana global: cada aresta conserva el SEU pas."""
        valors = {'XXS': 96.0, 'XS': 98.5, 'S': 100.0, 'M': 102.0, 'L': 105.0}
        self.assertEqual(
            sembra_valors_step(valors, self.RUN, 'S'),
            {'XXS': 2.5, 'XS': 1.5, 'M': 2.0, 'L': 3.0},
        )

    def test_run_no_contigu_reparteix_el_salt(self):
        """Llei S24b: el camí es recorre sobre el SISTEMA. Un model `XS·S·L` travessa la M,
        que no fabrica i de la qual no hi ha valor: el salt S→L es reparteix entre els dos
        passos. Tota talla travessada té entrada (si no, `_apply_rule` deixaria la cel·la
        absent) i les talles del model conserven el valor exacte."""
        valors = {'XS': 98.0, 'S': 100.0, 'L': 106.0}
        deltes = sembra_valors_step(valors, self.RUN, 'S')
        self.assertEqual(deltes, {'XS': 2.0, 'M': 3.0, 'L': 3.0})
        self.assertEqual(100.0 + deltes['M'] + deltes['L'], 106.0)   # el valor de L es conserva

    def test_geometria_incompleta_no_sembra_a_mitges(self):
        self.assertEqual(sembra_valors_step({'S': 100.0}, self.RUN, 'S'), {})       # una sola talla
        self.assertEqual(sembra_valors_step({'M': 1, 'L': 2}, self.RUN, 'S'), {})   # sense la base
        self.assertEqual(sembra_valors_step({'S': 100.0, 'M': 101.0}, self.RUN, 'XXL'), {})


class _StepBase(TenantTestCase):
    """Model amb run XXS·XS·S·M·L, base S, un POM amb regla resident LINEAR +1 (base 100)."""

    RUN = ['XXS', 'XS', 'S', 'M', 'L']
    BASE = 'S'
    VIGENTS = {'XXS': 98.0, 'XS': 99.0, 'S': 100.0, 'M': 101.0, 'L': 102.0}

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create(username='step')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Step', 'rol_nom': 'admin'})

        self.ss = SizeSystem.objects.create(codi='SS_ST', nom='SS step', base_unit='ALPHA')
        for i, et in enumerate(self.RUN):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)

        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest')
        self.model = Model.objects.create(
            codi_intern='TST-STEP', codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Test', size_system=self.ss,
            size_run_model='·'.join(self.RUN), base_size_label=self.BASE,
        )
        # Un signal de `Model` ja sembra el SizeFitting numero=1: reutilitzar-lo, no duplicar.
        self.sf = SizeFitting.objects.filter(model=self.model).order_by('numero').first()
        if self.sf is None:
            self.sf = SizeFitting.objects.create(
                model=self.model, numero=1, codi='SF-STEP', tipus='SizeSet',
                estat='Pendent', creat_per=self.profile,
            )

        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, is_active=True, ordre=0)
        ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='LINEAR', increment_base=1.0, actiu=True)

    def _regim(self, logica):
        from fhort.models_app.views import set_pom_regim_view
        req = self.factory.post('/regim/', {'logica': logica}, format='json')
        force_authenticate(req, user=self.user)
        return set_pom_regim_view(req, model_id=self.model.id, pom_id=self.pom.id)

    def _ajustar(self, talla, valor):
        """L'edició REAL de la taula de grading (escalat/ajustar-talla)."""
        from fhort.models_app.views import escalat_ajustar_talla_view
        req = self.factory.post('/ajustar-talla/',
                                {'pom_id': self.pom.id, 'talla': talla, 'valor': valor},
                                format='json')
        force_authenticate(req, user=self.user)
        return escalat_ajustar_talla_view(req, model_id=self.model.id)

    def _taula(self):
        gv = GradingVersion.objects.filter(
            size_fitting=self.sf, is_active=True).order_by('-version_number').first()
        return {s.size_label: s.graded_value_cm
                for s in GradedSpec.objects.filter(grading_version=gv, pom=self.pom)}

    def _regla(self):
        return ModelGradingRule.objects.get(model=self.model, pom=self.pom)


class StepConservaValorsTest(_StepBase):

    def test_linear_amb_specs_step_conserva_valors(self):
        """El cas de la diagnosi: la fila STEP neix amb els números que ja es veien."""
        generate_graded_specs(self.sf.id)
        self.assertEqual(self._taula(), self.VIGENTS)

        resp = self._regim('STEP')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._regla().valors_step,
                         {'XXS': 1.0, 'XS': 1.0, 'M': 1.0, 'L': 1.0})

        # I la fila re-emesa és la MATEIXA: sembrar no mou cap número.
        generate_graded_specs(self.sf.id)
        self.assertEqual(self._taula(), self.VIGENTS)
        self.assertEqual({s.grading_type_applied for s in GradedSpec.objects.filter(
            grading_version__size_fitting=self.sf, pom=self.pom)}, {'STEP'})

    def test_la_fila_re_emet_ja_no_es_congela(self):
        """El `continue` de `services.py:277` deixa de congelar.

        Amb el calaix buit, cap cel·la del POM es calculava i els specs VELLS es quedaven
        a la taula: canviar la base i re-derivar no movia res. Ara la regla STEP té deltes
        i la fila sencera es desplaça amb la base nova."""
        generate_graded_specs(self.sf.id)
        self._regim('STEP')

        BaseMeasurement.objects.filter(model=self.model, pom=self.pom).update(base_value_cm=110.0)
        generate_graded_specs(self.sf.id)

        self.assertEqual(self._taula(),
                         {'XXS': 108.0, 'XS': 109.0, 'S': 110.0, 'M': 111.0, 'L': 112.0})

    def test_step_linear_step_es_idempotent(self):
        """Anar i tornar no re-sembra: `valors_step` es conserva latent en LINEAR i el
        segon pas a STEP el troba poblat. Els mateixos deltes, sense deriva."""
        generate_graded_specs(self.sf.id)
        self._regim('STEP')
        deltes = self._regla().valors_step

        self.assertEqual(self._regim('LINEAR').status_code, 200)
        self.assertEqual(self._regla().valors_step, deltes)     # latent, intacte

        self.assertEqual(self._regim('STEP').status_code, 200)
        self.assertEqual(self._regla().valors_step, deltes)

    def test_model_sense_specs_step_neix_buit_sense_petar(self):
        """Un model que encara no s'ha graduat ha de poder passar a STEP: neix buit, 200."""
        self.assertFalse(GradedSpec.objects.filter(pom=self.pom).exists())

        resp = self._regim('STEP')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['logica'], 'STEP')
        self.assertIsNone(self._regla().valors_step)


class TotSegueixEditableDespresDelStepTest(_StepBase):
    """LLEI 2 (Agus, 30/07): després del canvi de règim, a la taula TOT és editable — la
    base, qualsevol talla, qualsevol step. El canvi de règim no restringeix cap edició."""

    def setUp(self):
        super().setUp()
        generate_graded_specs(self.sf.id)
        self.assertEqual(self._regim('STEP').status_code, 200)

    def test_editar_la_base_despres_del_canvi_mou_la_fila_sencera(self):
        """La base es desa i la fila RESPON: els deltes STEP la segueixen."""
        resp = self._ajustar('S', 110)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._taula(),
                         {'XXS': 108.0, 'XS': 109.0, 'S': 110.0, 'M': 111.0, 'L': 112.0})

    def test_editar_un_step_desa_la_cella_i_deixa_les_germanes(self):
        """Una talla no-base en règim STEP: override puntual, com al fitting. La cel·la
        editada canvia i cap germana es mou (els valors STEP són lliures)."""
        resp = self._ajustar('L', 105)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._taula(),
                         {'XXS': 98.0, 'XS': 99.0, 'S': 100.0, 'M': 101.0, 'L': 105.0})
