"""GUARDA DE RANG FÍSIC — el 22224,7 del POP no torna a entrar per cap porta.

Germana del FIX-4 i d'una altra naturalesa: el FIX-4 PREGUNTA (llindars relatius a la base,
on el legítim i l'errat es toquen), això BLOQUEJA (>400 cm o ≤0 cm no descriu cap peça de
roba). Les DUES portes per on una mesura entra al backend —`escalat/ajustar-talla/` i
`gravar_pom`— comparteixen el punt únic `pom/plausibilitat.py` i responen 422.

LLEI (Agus, 30/07): dins del rang, l'usuari mana. Cap altra restricció.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem
from fhort.pom.plausibilitat import CODI_MESURA_FORA_RANG, mesura_fora_de_rang
from fhort.pom.services import generate_graded_specs

IMPOSSIBLES = (22224.7, 400.1, 0, -3)     # el del POP, el just per sobre, el zero, el negatiu
LEGITIMS = (0.1, 1, 46, 120.5, 399.9, 400)


class RangMesuraPurTest(TenantTestCase):
    """La funció sola: què rebutja i, sobretot, què NO."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def test_els_extrems_justos_passen(self):
        for v in LEGITIMS:
            self.assertIsNone(mesura_fora_de_rang(v), v)

    def test_l_impossible_es_rebutja_amb_missatge(self):
        for v in IMPOSSIBLES:
            self.assertTrue(mesura_fora_de_rang(v), v)

    def test_el_no_numeric_no_es_feina_seva(self):
        """El guard de TIPUS ja viu a cada porta i té el seu propi 400."""
        for v in (None, '', 'abc', True):
            self.assertIsNone(mesura_fora_de_rang(v), v)


class _PortesBase(TenantTestCase):
    """Model amb run XXS·XS·S·M·L, base S, un POM amb base 100 i regla LINEAR +1."""

    RUN = ['XXS', 'XS', 'S', 'M', 'L']

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
        self.user = get_user_model().objects.create(username='rang')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Rang', 'rol_nom': 'admin'})

        self.ss = SizeSystem.objects.create(codi='SS_RG', nom='SS rang', base_unit='ALPHA')
        for i, et in enumerate(self.RUN):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)

        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest')
        self.model = Model.objects.create(
            codi_intern='TST-RANG', codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Test', size_system=self.ss,
            size_run_model='·'.join(self.RUN), base_size_label='S',
        )
        # Un signal de `Model` ja sembra el SizeFitting numero=1: reutilitzar-lo, no duplicar.
        self.sf = SizeFitting.objects.filter(model=self.model).order_by('numero').first()
        if self.sf is None:
            self.sf = SizeFitting.objects.create(
                model=self.model, numero=1, codi='SF-RANG', tipus='SizeSet',
                estat='Pendent', creat_per=self.profile,
            )

        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, is_active=True, ordre=0)
        ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='LINEAR', increment_base=1.0, actiu=True)

    def _ajustar(self, talla, valor):
        from fhort.models_app.views import escalat_ajustar_talla_view
        req = self.factory.post('/ajustar-talla/',
                                {'pom_id': self.pom.id, 'talla': talla, 'valor': valor},
                                format='json')
        force_authenticate(req, user=self.user)
        return escalat_ajustar_talla_view(req, model_id=self.model.id)

    def _gravar_pom(self, valor):
        from fhort.models_app.views import gravar_pom_view
        req = self.factory.post(
            '/gravar-pom/',
            {'measurements': [{'pom_id': self.pom.id, 'base_value_cm': valor}]},
            format='json')
        force_authenticate(req, user=self.user)
        return gravar_pom_view(req, model_id=self.model.id)

    def _taula(self):
        gv = GradingVersion.objects.filter(
            size_fitting=self.sf, is_active=True).order_by('-version_number').first()
        return {s.size_label: s.graded_value_cm
                for s in GradedSpec.objects.filter(grading_version=gv, pom=self.pom)}


class AjustarTallaTest(_PortesBase):

    def test_rebutja_i_no_escriu_res(self):
        generate_graded_specs(self.sf.id)
        vigent = self._taula()

        for valor in IMPOSSIBLES:
            resp = self._ajustar('S', valor)
            self.assertEqual(resp.status_code, 422, valor)
            self.assertEqual(resp.data['codi'], CODI_MESURA_FORA_RANG)
            self.assertTrue(resp.data['error'])
            self.assertEqual(self._taula(), vigent, f'{valor} no ha d\'escriure res')

    def test_el_rang_legitim_passa_i_desa(self):
        generate_graded_specs(self.sf.id)
        for valor in (0.1, 400):
            self.assertEqual(self._ajustar('S', valor).status_code, 200, valor)
        self.assertEqual(
            BaseMeasurement.objects.get(model=self.model, pom=self.pom).base_value_cm, 400)


class GravarPomTest(_PortesBase):

    def test_rebutja_i_no_escriu_res(self):
        for valor in IMPOSSIBLES:
            resp = self._gravar_pom(valor)
            self.assertEqual(resp.status_code, 422, valor)
            self.assertEqual(resp.data['codi'], CODI_MESURA_FORA_RANG)
        self.assertEqual(
            BaseMeasurement.objects.get(model=self.model, pom=self.pom).base_value_cm, 100.0)

    def test_el_rang_legitim_no_el_para_la_guarda(self):
        """Dins del rang la guarda no hi diu res i la petició continua el seu camí.

        Aquest model no té tasca POM oberta i `gravar_pom` hi té una precondició pròpia
        (400, «Cal obrir la tasca POM») que no té res a veure amb la mesura: el que aquí es
        fixa és que 120,5 cm NO és el que la fa fallar."""
        resp = self._gravar_pom(120.5)

        self.assertNotEqual(resp.status_code, 422)
        self.assertNotIn('codi', resp.data)
