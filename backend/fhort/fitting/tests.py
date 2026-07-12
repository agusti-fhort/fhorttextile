"""Test d'integració de l'@action propagar (PG-4b-2) i dels guards d'escriptura.

Propagació de delta en temps d'edició: ancorar la cel·la de la TALLA BASE i, si el règim és
LINEAR/canònic, reescriure el valor_real de les germanes del mateix POM. valor_teoric mai es toca.

P1 — l'ancoratge només es fa des de la talla base (`fitting_line_is_non_base` → 400): el fitting
és un ESTADI de la taula base i el treball multi-talla viu a Escalat (DECISIONS.md §2).
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
        self.session = session   # Oberta per defecte; els tests de guard la segellen.
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
        self.patch_view = PieceFittingLineViewSet.as_view({'patch': 'partial_update'})

    def _propagar(self, line, valor_real):
        req = self.factory.post('/propagar/', {'valor_real': valor_real}, format='json')
        force_authenticate(req, user=self.user)
        return self.view(req, pk=line.pk)

    def _patch(self, line, valor_real):
        req = self.factory.patch('/', {'valor_real': valor_real}, format='json')
        force_authenticate(req, user=self.user)
        return self.patch_view(req, pk=line.pk)

    def _seal(self, estat):
        self.session.estat = estat
        self.session.save(update_fields=['estat'])

    def _reals(self):
        return {sl: PieceFittingLine.objects.get(pk=self.lines[sl].pk).valor_real
                for sl in ['S', 'M', 'L', 'XL']}

    def _teorics(self):
        return {sl: PieceFittingLine.objects.get(pk=self.lines[sl].pk).valor_teoric
                for sl in ['S', 'M', 'L', 'XL']}

    # NOTA (P1): l'ancoratge SEMPRE es fa des de la talla BASE del model ('M' aquí). Les
    # altres talles són read-only al fitting (guard `fitting_line_is_non_base`) i es
    # treballen a Escalat — DECISIONS.md §2. Vegeu `test_no_base_*`.

    # ── LINEAR/canònic: ancorar M=50 propaga valor_real S=48,M=50,L=52,XL=54. teoric intacte.
    def test_linear_propaga_i_teoric_intacte(self):
        resp = self._propagar(self.lines['M'], 50)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['propagat'])
        self.assertEqual(self._reals(), {'S': 48, 'M': 50, 'L': 52, 'XL': 54})
        self.assertEqual(self._teorics(), TEORICS)   # valor_teoric SENSE canvis

    # ── STEP: no propaga; només desa la cel·la ancorada. Germanes valor_real intactes.
    def test_step_no_propaga(self):
        self.rule.logica = 'STEP'
        self.rule.increment_base = None
        self.rule.save()
        resp = self._propagar(self.lines['M'], 50)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['propagat'])
        self.assertEqual(resp.data['motiu'], 'STEP')
        reals = self._reals()
        self.assertEqual(reals['M'], 50)                 # cel·la editada (base) desada
        self.assertEqual(reals['S'], TEORICS['S'])       # germanes intactes
        self.assertEqual(reals['L'], TEORICS['L'])
        self.assertEqual(reals['XL'], TEORICS['XL'])
        self.assertEqual(self._teorics(), TEORICS)

    # ── Sense regla: no propaga; motiu 'sense_regla'. Germanes intactes.
    def test_sense_regla_no_propaga(self):
        self.rule.delete()
        resp = self._propagar(self.lines['M'], 50)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['propagat'])
        self.assertEqual(resp.data['motiu'], 'sense_regla')
        reals = self._reals()
        self.assertEqual(reals['M'], 50)
        self.assertEqual(reals['S'], TEORICS['S'])
        self.assertEqual(reals['XL'], TEORICS['XL'])

    # ── R4 (PG-4b-3a): STEP amb increment_base poblat → el gate per `logica` bloqueja la
    # propagació igualment (motiu 'STEP', germanes intactes). Demostra que logica guanya.
    def test_step_amb_increment_base_no_propaga(self):
        self.rule.logica = 'STEP'        # increment_base=2 ES CONSERVA (latent)
        self.rule.save()
        resp = self._propagar(self.lines['M'], 50)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['propagat'])
        self.assertEqual(resp.data['motiu'], 'STEP')
        reals = self._reals()
        self.assertEqual(reals['M'], 50)                 # cel·la editada (base) desada
        self.assertEqual(reals['S'], TEORICS['S'])       # germanes intactes
        self.assertEqual(reals['L'], TEORICS['L'])
        self.assertEqual(reals['XL'], TEORICS['XL'])

    # ── PG-4b-3a règim per-POM: helper de POST a l'endpoint set_pom_regim_view.
    def _regim(self, model_id, pom_id, logica):
        from fhort.models_app.views import set_pom_regim_view
        req = self.factory.post('/regim/', {'logica': logica}, format='json')
        force_authenticate(req, user=self.user)
        return set_pom_regim_view(req, model_id=model_id, pom_id=pom_id)

    def test_regim_crea_resident_step_conserva_increment_base(self):
        from fhort.models_app.models import ModelGradingRule
        pom2 = POMMaster.objects.create(codi_client='P2', nom_client='POM 2')
        GradingRule.objects.create(rule_set=self.rs, pom=pom2, talla_base=self.talla_base,
                                   logica='LINEAR', increment_base=3)
        mv0 = self.model.measurements_version
        resp = self._regim(self.model.id, self.pom.id, 'STEP')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['logica'], 'STEP')
        self.assertEqual(resp.data['origen'], 'MANUAL')
        self.assertEqual(resp.data['increment_base'], 2)        # conservat (latent)
        r = ModelGradingRule.objects.get(model=self.model, pom=self.pom)
        self.assertEqual(r.logica, 'STEP')
        self.assertEqual(r.origen, 'MANUAL')
        self.assertEqual(float(r.increment_base), 2)
        # POM #2 NO té resident (no s'ha tocat).
        self.assertFalse(ModelGradingRule.objects.filter(model=self.model, pom=pom2).exists())
        # Innocu sobre el grading persistent.
        self.model.refresh_from_db()
        self.assertEqual(self.model.measurements_version, mv0)

    def test_regim_update_no_duplica(self):
        from fhort.models_app.models import ModelGradingRule
        self._regim(self.model.id, self.pom.id, 'STEP')
        resp = self._regim(self.model.id, self.pom.id, 'LINEAR')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['logica'], 'LINEAR')
        self.assertEqual(
            ModelGradingRule.objects.filter(model=self.model, pom=self.pom).count(), 1)

    def test_regim_sense_fallback_400(self):
        from fhort.models_app.models import ModelGradingRule
        pom3 = POMMaster.objects.create(codi_client='P3', nom_client='POM 3')  # sense GradingRule
        resp = self._regim(self.model.id, pom3.id, 'STEP')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ModelGradingRule.objects.filter(model=self.model, pom=pom3).exists())

    def test_grid_exposa_regim_per_pom(self):
        from fhort.fitting.serializers import PieceFittingGridSerializer
        data = PieceFittingGridSerializer(self.pf).data
        line = next(l for l in data['lines'] if l['pom_id'] == self.pom.id)
        self.assertEqual(line['logica'], 'LINEAR')   # fallback (resident buida)
        self.assertEqual(line['increment_base'], 2)

    # ─────────────────────────────────────────────────────────────────────────
    # GUARD — escriptura sobre fitting segellat (Tancada/Anullada) → 409, res es desa.
    # La sessió queda Oberta per defecte; _seal() la passa a l'estat segellat.
    # ─────────────────────────────────────────────────────────────────────────

    # ── No-regressió: sessió Oberta → propagar i PATCH sobre la talla BASE funcionen.
    def test_oberta_propagar_i_patch_ok(self):
        resp = self._propagar(self.lines['M'], 50)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['propagat'])
        # PATCH de la cel·la base (autosave) sobre sessió Oberta.
        resp2 = self._patch(self.lines['M'], 99)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines['M'].pk).valor_real, 99)

    # ─────────────────────────────────────────────────────────────────────────
    # GUARD P1 — eix base: el fitting NOMÉS edita la talla base del model.
    # Les altres talles es treballen a Escalat (DECISIONS.md §2). 400, res es desa.
    # ─────────────────────────────────────────────────────────────────────────

    NO_BASE_DETAIL = ('El fitting només edita la talla base del model. '
                      'Les altres talles es treballen a Escalat.')

    def test_no_base_propagar_400_no_desa(self):
        resp = self._propagar(self.lines['L'], 50)     # 'L' no és la base ('M')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['detail'], self.NO_BASE_DETAIL)
        self.assertEqual(self._reals(), TEORICS)       # res s'ha desat
        self.assertEqual(self._teorics(), TEORICS)

    def test_no_base_patch_400_no_desa(self):
        original = PieceFittingLine.objects.get(pk=self.lines['XL'].pk).valor_real
        resp = self._patch(self.lines['XL'], 50)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['detail'], self.NO_BASE_DETAIL)
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines['XL'].pk).valor_real, original)

    def test_segellat_mana_sobre_eix(self):
        """Sessió segellada + línia no-base → 409 (estat), no 400 (eix): l'ordre dels guards
        és deliberat i estable."""
        self._seal('Tancada')
        resp = self._propagar(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 409)

    # ── Tancada: propagar → 409 i CAP valor_real canvia a BD (no n'hi ha prou amb el codi).
    def test_tancada_propagar_409_no_desa(self):
        self._seal('Tancada')
        resp = self._propagar(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['detail'], 'Sessió de fitting tancada; no es pot modificar.')
        self.assertEqual(self._reals(), TEORICS)          # res s'ha desat
        self.assertEqual(self._teorics(), TEORICS)

    # ── Tancada: PATCH valor_real → 409 i la cel·la NO canvia a BD.
    def test_tancada_patch_409_no_desa(self):
        self._seal('Tancada')
        original = PieceFittingLine.objects.get(pk=self.lines['L'].pk).valor_real
        resp = self._patch(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['detail'], 'Sessió de fitting tancada; no es pot modificar.')
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines['L'].pk).valor_real, original)

    # ── Anullada: propagar → 409 (cobreix els DOS estats segellats), res es desa.
    def test_anullada_propagar_409_no_desa(self):
        self._seal('Anullada')
        resp = self._propagar(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['detail'], 'Sessió de fitting tancada; no es pot modificar.')
        self.assertEqual(self._reals(), TEORICS)

    # ── Anullada: PATCH → 409 (simetria amb propagar per a l'estat Anullada).
    def test_anullada_patch_409_no_desa(self):
        self._seal('Anullada')
        original = PieceFittingLine.objects.get(pk=self.lines['L'].pk).valor_real
        resp = self._patch(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines['L'].pk).valor_real, original)
