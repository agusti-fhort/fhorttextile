"""C3-A2 — la propagació de grading és UN acte, o no és.

`generate_grading_view` no obria cap `transaction.atomic()` i `ATOMIC_REQUESTS` no existeix
(settings.py:118-127). El LLENÇ NET d'overrides (`ModelGradingOverride.objects.filter(model)
.delete()`) es commitava tot sol, i si el motor petava tot seguit la vista retornava 400/500
amb els ajustos per cel·la JA ESBORRATS i sense cap manera de recuperar-los
(DIAGNOSI_MOTOR_DERIVACIO_C3 §A3.3).

Aquests tests simulen la petada del motor DESPRÉS del llenç net i exigeixen que els overrides
hi segueixin sent. Contra el codi d'abans peten: els overrides han desaparegut i el 400 diu que
no s'ha fet res quan de fet s'ha destruït patrimoni.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
# FIX-A/PAS-1c (21/08) — les fixtures d'aquest fitxer construïen la regla LINEAR amb el
# camp LLEGAT `increment`. Funcionava perquè el motor hi queia per fallback; des que el
# fallback no hi és (`_apply_rule`, llei D2), una regla sense `increment_base` NO gradua i
# no emet cap cel·la. El SUBJECTE d'aquestes proves no és el camp sinó el que hi ha a
# sobre (germanes, peces, transacció), o sigui que la fixture passa al camp que mana i
# CAP asserció es toca: si alguna hagués canviat de valor, el canvi no seria de fixture.
import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import (BaseMeasurement, ModelGradingOverride,
                                     ModelGradingRule, Model)
from fhort.models_app.views import generate_grading_view
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem


class TransaccioGradingC3A2Test(TenantTestCase):

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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        # El SizeSystem no és decoració del fixture: sense ell `escala_del_model` no pot
        # resoldre el run i la vista surt per un 400 («no té Size System assignat») ABANS
        # d'arribar al motor. Els tests de rollback passarien igual —el seu assert és un 400—
        # però passarien pel motiu equivocat, sense haver exercitat mai el llenç net.
        self.ss = SizeSystem.objects.create(codi='SS_C3A2', nom='SS C3-A2', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='TST-C3A2', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_c3a2', defaults={'email': 'qa@c3a2.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA C3-A2', 'rol_nom': 'QA'})
        # `get_or_create`: un signal ja crea l'SF numero=1 en néixer el Model. Crear-lo a
        # seques és la col·lisió `fitting_sizefitting_model_id_numero` que té 53 tests de la
        # suite en vermell des del 28/07; aquest fitxer no hi entra.
        from fhort.fitting.models import SizeFitting
        self.sf, _ = SizeFitting.objects.get_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-C3A2', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.perfil},
        )
        # `_te_regles` ha de dir que sí, o la vista surt per un 400 abans d'arribar al llenç net.
        ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='LINEAR', increment_base=1.0, actiu=True)
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A-EXT')
        # EL PATRIMONI EN JOC: l'ajust per cel·la que el llenç net esborra.
        self.override = ModelGradingOverride.objects.create(
            model=self.model, pom=self.pom, size_label='L', value_cm=42.0,
            motiu='ajust del tècnic que no s\'ha de perdre')
        self.factory = APIRequestFactory()

    def _propaga(self):
        request = self.factory.post(
            f'/api/v1/models/{self.model.pk}/generar-grading/',
            {'new_version': True}, format='json')
        force_authenticate(request, user=self.user)
        return generate_grading_view(request, self.model.pk)

    # ── El cas del brief ─────────────────────────────────────────────────────────────

    def test_una_petada_del_motor_deixa_els_overrides_INTACTES(self):
        """El llenç net es desfà amb la resta. Abans es commitava tot sol."""
        with mock.patch('fhort.pom.services.bump_grading_version_and_generate',
                        side_effect=ValueError('petada simulada del motor')) as bump:
            resp = self._propaga()

        self.assertEqual(resp.status_code, 400)
        # Que el 400 sigui EL NOSTRE. Sense aquests dos asserts el test passaria igual amb un
        # fixture incomplet (p.ex. sense SizeSystem), sortint per un 400 anterior al llenç net
        # i donant per bona una transacció que mai no s'ha arribat a exercitar.
        self.assertTrue(bump.called, 'el motor ha de ser CRIDAT: si no, no s\'ha provat res')
        self.assertIn('petada simulada', str(resp.data.get('error', '')))
        self.assertTrue(ModelGradingOverride.objects.filter(pk=self.override.pk).exists(),
                        "el llenç net s'ha de desfer amb la transacció: sense atòmic, "
                        "l'ajust del tècnic desapareixia i el 400 deia que no s'havia fet res")
        self.override.refresh_from_db()
        self.assertEqual(self.override.value_cm, 42.0)

    def test_una_petada_INESPERADA_tambe_desfa_el_llenc_net(self):
        """El camí del 500, que és el que es menja qualsevol error no previst."""
        with mock.patch('fhort.pom.services.bump_grading_version_and_generate',
                        side_effect=RuntimeError('bum')) as bump:
            resp = self._propaga()

        self.assertEqual(resp.status_code, 500)
        self.assertTrue(bump.called)
        self.assertTrue(ModelGradingOverride.objects.filter(pk=self.override.pk).exists())

    def test_una_petada_no_deixa_cap_versio_nova_viva(self):
        """L'altra meitat del dany: la v+1 creada i BUIDA amb l'anterior ja desactivada.

        Aquí NO es pot mockejar `bump_grading_version_and_generate`: és ell qui desactiva les
        actives i crea la v+1 (pom/services.py:876-880), o sigui que substituir-lo faria que la
        versió no arribés a néixer mai i el test passaria sense provar res. Es mocka el node de
        SOTA —el motor— perquè el bump faci la seva feina de debò i peti just després.
        """
        from fhort.fitting.models import GradingVersion
        # La versió vigent ha d'EXISTIR perquè el dany es pugui produir: el bump desactiva les
        # actives abans de crear la v+1, i el que es prova és que aquella torni. Sense aquesta
        # fila el test passaria amb 0 actives abans i 0 després, sense provar res.
        vigent = GradingVersion.objects.create(
            size_fitting=self.sf, version_number=1, is_active=True)
        n_abans = GradingVersion.objects.filter(size_fitting=self.sf).count()

        with mock.patch('fhort.pom.services.generate_graded_specs',
                        side_effect=ValueError('petada del motor després del bump')) as gen:
            resp = self._propaga()

        self.assertTrue(gen.called, 'el motor ha de ser cridat DESPRÉS de crear la v+1')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(GradingVersion.objects.filter(size_fitting=self.sf).count(), n_abans,
                         'cap versió nova ha de sobreviure a una propagació que ha petat')
        self.assertEqual(
            GradingVersion.objects.filter(size_fitting=self.sf, is_active=True).count(), 1,
            'i la que hi havia ha de tornar a estar activa: el bump la desactiva abans de '
            'crear la nova, i sense rollback el model es quedava sense cap versió vigent')
        vigent.refresh_from_db()
        self.assertTrue(vigent.is_active, 'i ha de ser LA MATEIXA, no una de nova')

    # ── No-regressió: el camí feliç segueix fent el que feia ─────────────────────────

    def test_el_cami_felic_propaga_i_esborra_els_overrides(self):
        """El llenç net és LLEI: quan la propagació surt bé, els overrides SÍ marxen."""
        resp = self._propaga()

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertFalse(ModelGradingOverride.objects.filter(pk=self.override.pk).exists(),
                         'el llenç net segueix sent llei quan la propagació té èxit')
        self.assertGreater(resp.data['graded_count'], 0,
                           'la propagació ha d\'haver escrit cel·les de debò')
