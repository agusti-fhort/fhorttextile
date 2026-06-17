"""Test d'integració de l'@action propagar (PG-4b-2).

Propagació de delta en temps d'edició: ancorar una cel·la i, si el règim és LINEAR/canònic,
reescriure el valor_real de les germanes del mateix POM. valor_teoric mai es toca.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import (
    FittingSession, SizeFitting, GradingVersion, PieceFitting, PieceFittingLine,
)
from fhort.fitting.views import PieceFittingLineViewSet
from fhort.models_app.models import Model
from fhort.pom.models import (
    SizeSystem, SizeDefinition, GradingRuleSet, GradingRule, POMMaster,
)

TEORICS = {'S': 10.0, 'M': 20.0, 'L': 30.0, 'XL': 40.0}  # distints; han de quedar intactes


class PropagarActionTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='tester')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Tester', 'rol_nom': 'admin'})

        ss = SizeSystem.objects.create(codi='SS_T', nom='SS test', base_unit='ALPHA')
        self.talla_base = SizeDefinition.objects.create(size_system=ss, etiqueta='M', ordre=2)
        self.rs = GradingRuleSet.objects.create(nom='RS test')
        self.pom = POMMaster.objects.create(codi_client='P1', nom_client='POM 1')
        # Regla canònica LINEAR uniforme (fallback al rule_set; ModelGradingRule buida).
        self.rule = GradingRule.objects.create(
            rule_set=self.rs, pom=self.pom, talla_base=self.talla_base,
            logica='LINEAR', increment_base=2,
        )

        self.model = Model.objects.create(
            codi_intern='TST-1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L·XL', base_size_label='M',
            grading_rule_set=self.rs,
        )
        sf = SizeFitting.objects.create(model=self.model, codi='SF-TST-1', tipus='PRINCIPAL',
                                        numero=1, creat_per=self.profile)
        gv = GradingVersion.objects.create(size_fitting=sf, version_number=1, is_active=True,
                                           creat_per=self.profile)
        session = FittingSession.objects.create(
            model=self.model, fase='Dev', data=datetime.date(2026, 6, 17),
        )
        self.pf = PieceFitting.objects.create(
            session=session, model=self.model, grading_version=gv,
        )
        self.lines = {}
        for sl in ['S', 'M', 'L', 'XL']:
            self.lines[sl] = PieceFittingLine.objects.create(
                piece_fitting=self.pf, pom=self.pom, size_label=sl,
                valor_teoric=TEORICS[sl], valor_real=TEORICS[sl],
            )

        self.factory = APIRequestFactory()
        self.view = PieceFittingLineViewSet.as_view({'post': 'propagar'})

    def _propagar(self, line, valor_real):
        req = self.factory.post('/propagar/', {'valor_real': valor_real}, format='json')
        force_authenticate(req, user=self.user)
        return self.view(req, pk=line.pk)

    def _reals(self):
        return {sl: PieceFittingLine.objects.get(pk=self.lines[sl].pk).valor_real
                for sl in ['S', 'M', 'L', 'XL']}

    def _teorics(self):
        return {sl: PieceFittingLine.objects.get(pk=self.lines[sl].pk).valor_teoric
                for sl in ['S', 'M', 'L', 'XL']}

    # ── LINEAR/canònic: ancorar L=50 propaga valor_real S=46,M=48,L=50,XL=52. teoric intacte.
    def test_linear_propaga_i_teoric_intacte(self):
        resp = self._propagar(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['propagat'])
        self.assertEqual(self._reals(), {'S': 46, 'M': 48, 'L': 50, 'XL': 52})
        self.assertEqual(self._teorics(), TEORICS)   # valor_teoric SENSE canvis

    # ── STEP: no propaga; només desa la cel·la ancorada. Germanes valor_real intactes.
    def test_step_no_propaga(self):
        self.rule.logica = 'STEP'
        self.rule.increment_base = None
        self.rule.save()
        resp = self._propagar(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['propagat'])
        self.assertEqual(resp.data['motiu'], 'STEP')
        reals = self._reals()
        self.assertEqual(reals['L'], 50)                 # cel·la editada desada
        self.assertEqual(reals['S'], TEORICS['S'])       # germanes intactes
        self.assertEqual(reals['M'], TEORICS['M'])
        self.assertEqual(reals['XL'], TEORICS['XL'])
        self.assertEqual(self._teorics(), TEORICS)

    # ── Sense regla: no propaga; motiu 'sense_regla'. Germanes intactes.
    def test_sense_regla_no_propaga(self):
        self.rule.delete()
        resp = self._propagar(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['propagat'])
        self.assertEqual(resp.data['motiu'], 'sense_regla')
        reals = self._reals()
        self.assertEqual(reals['L'], 50)
        self.assertEqual(reals['S'], TEORICS['S'])
        self.assertEqual(reals['XL'], TEORICS['XL'])

    # ── R4 (PG-4b-3a): STEP amb increment_base poblat → el gate per `logica` bloqueja la
    # propagació igualment (motiu 'STEP', germanes intactes). Demostra que logica guanya.
    def test_step_amb_increment_base_no_propaga(self):
        self.rule.logica = 'STEP'        # increment_base=2 ES CONSERVA (latent)
        self.rule.save()
        resp = self._propagar(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['propagat'])
        self.assertEqual(resp.data['motiu'], 'STEP')
        reals = self._reals()
        self.assertEqual(reals['L'], 50)                 # cel·la editada desada
        self.assertEqual(reals['S'], TEORICS['S'])       # germanes intactes
        self.assertEqual(reals['M'], TEORICS['M'])
        self.assertEqual(reals['XL'], TEORICS['XL'])
