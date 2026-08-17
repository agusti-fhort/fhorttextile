"""E1/B1 · EL GUARD DE L'EIX BASE ES PARTEIX: PRENDRE ≠ DECIDIR.

Substrat: `docs/diagnosis/DIAGNOSI_E1_MESURA_ESCALAT.md` (§2 QA · §5 QD).

── QUÈ CANVIA I PER QUÈ ─────────────────────────────────────────────────────────────────
El guard P1 (`fitting_line_is_non_base`) tancava **tota** escriptura de línia no-base amb un
400. Era correcte mentre l'única cosa que es podia fer amb una línia era DECIDIR-LA: el que
no es consolidava (`consolidate_base_from_fitting` ignora tot el que no és la base) no havia
d'entrar per la porta.

El flux E1 hi separa dos gestos que fins ara eren un:

  · **PRENDRE** — anotar la xifra de la peça FÍSICA que ha arribat en aquella talla. És una
    dada d'observació. Ha de poder viure a QUALSEVOL talla del run: aquest és el pas 1.
  · **DECIDIR** — el veredicte (`decisio` ∈ ACCEPTED/ADJUSTED/REJECTED). R2: **els ajustos
    només s'accepten a la TALLA BASE** i la propagació surt d'allà. Segueix sent 400.

── PER QUÈ OBRIR LA PRESA NO OBRE CAP PORTA DE DOMINI (cens fet, 17/08) ─────────────────
Una presa no-base **no arriba enlloc que decideixi res**:
  · `consolidate_base_from_fitting` (`services.py:515`) fa `size_label != base → continue`;
  · `close_piece_fitting` només consolida el que aquell helper li torna;
  · el Repàs ja té eix de talla propi (`repas_views.py:454`, `if l.size_label != talla`);
  · `comprovacio_views.py:220` filtra `size_label=talla`.
Els lectors que SÍ que canvien de resposta i ho han de fer: `linia_te_contingut`
(`esdeveniments.py:34` — algú HA mesurat, i el Repàs ho ha de dir) i els exports S8/S10, que
sempre han llistat totes les talles i fins ara hi trobaven la còpia del teòric.

🚨 **EL VERMELL D'AQUEST BANC, ABANS DEL CANVI** (documentat al report, no només aquí):
`test_presa_a_talla_NO_base_es_permesa` i les seves germanes donaven **400** amb el detall
`NON_BASE_LINE_DETAIL`. `test_DECISIO_a_talla_NO_base_es_400` ja passava — i ha de seguir
passant: és la meitat del guard que NO es toca.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import (
    FittingSession, SizeFitting, GradingVersion, PieceFitting, PieceFittingLine,
)
from fhort.fitting.services import NON_BASE_DECISIO_DETAIL, NON_BASE_LINE_DETAIL
from fhort.fitting.views import PieceFittingLineViewSet
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import (
    SizeSystem, SizeDefinition, GradingRuleSet, GradingRule, POMMaster,
)

TEORICS = {'S': 10.0, 'M': 20.0, 'L': 30.0, 'XL': 40.0}
BASE = 'M'


class GuardPartitBase(TenantTestCase):
    """Model amb run S·M·L·XL i base M. Fixture germà del de `fitting/tests.py`."""

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
        self.user = get_user_model().objects.create(username='tester_e1')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Tester', 'rol_nom': 'admin'})

        ss = SizeSystem.objects.create(codi='SS_E1', nom='SS E1', base_unit='ALPHA')
        talles = {et: SizeDefinition.objects.create(size_system=ss, etiqueta=et, ordre=i)
                  for i, et in enumerate(['S', 'M', 'L', 'XL'], start=1)}
        self.rs = GradingRuleSet.objects.create(nom='RS E1')
        self.pom = POMMaster.objects.create(codi_client='P1', nom_client='POM 1')
        GradingRule.objects.create(
            rule_set=self.rs, pom=self.pom, talla_base=talles[BASE],
            logica='LINEAR', increment_base=2,
        )
        self.model = Model.objects.create(
            codi_intern='E1-1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L·XL', base_size_label=BASE,
            size_system=ss, grading_rule_set=self.rs,
        )
        sf, _ = SizeFitting.objects.update_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-E1-1', 'tipus': 'PRINCIPAL', 'creat_per': self.profile},
        )
        self.sf = sf
        gv = GradingVersion.objects.create(size_fitting=sf, version_number=1, is_active=True,
                                           creat_per=self.profile)
        self.session = FittingSession.objects.create(
            model=self.model, fase='Dev', data=datetime.date(2026, 8, 17),
        )
        self.pf = PieceFitting.objects.create(
            session=self.session, model=self.model, grading_version=gv,
        )
        # ⚠️ LA MESURA BASE HA D'EXISTIR, i no és decoració del fixture: `close_piece_fitting`
        # crida `reconcilia_linies` ABANS de consolidar, i aquell helper esborra tota línia
        # que no tingui `BaseMeasurement` activa amb valor (`services.py:417-427`). Sense
        # això, tancar la peça n'esborra les 4 línies i el `close` no consolida res —
        # un verd per BUIT. Cap model real arriba mai a tenir línies sense mesura base.
        self.bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=TEORICS[BASE], is_active=True)
        self.lines = {
            sl: PieceFittingLine.objects.create(
                piece_fitting=self.pf, pom=self.pom, size_label=sl,
                valor_teoric=TEORICS[sl], valor_real=TEORICS[sl])
            for sl in TEORICS
        }
        self.factory = APIRequestFactory()
        self.patch_view = PieceFittingLineViewSet.as_view({'patch': 'partial_update'})
        self.propagar_view = PieceFittingLineViewSet.as_view({'post': 'propagar'})

    # ── helpers ──────────────────────────────────────────────────────────────────────────
    def _patch(self, line, **camps):
        req = self.factory.patch('/', camps, format='json')
        force_authenticate(req, user=self.user)
        return self.patch_view(req, pk=line.pk)

    def _propagar(self, line, valor_real):
        req = self.factory.post('/propagar/', {'valor_real': valor_real}, format='json')
        force_authenticate(req, user=self.user)
        return self.propagar_view(req, pk=line.pk)

    def _linia(self, sl):
        return PieceFittingLine.objects.get(pk=self.lines[sl].pk)

    def _seal(self, estat):
        self.session.estat = estat
        self.session.save(update_fields=['estat'])


class PresaNoBaseTest(GuardPartitBase):
    """LA MEITAT QUE S'OBRE: prendre una talla no-base."""

    def test_presa_a_talla_NO_base_es_permesa(self):
        """🔴→🟢 El pas 1 d'E1: la peça física de la L ha arribat i mesura 33."""
        resp = self._patch(self.lines['L'], valor_real=33)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._linia('L').valor_real, 33)
        # I la teòrica NO es mou: la presa no és una correcció de la corba.
        self.assertEqual(self._linia('L').valor_teoric, TEORICS['L'])

    def test_nota_a_talla_NO_base_es_permesa(self):
        """La nota viatja amb la presa: qui mesura dicta mentre mesura."""
        resp = self._patch(self.lines['XL'], nota='vora desbocada')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._linia('XL').nota, 'vora desbocada')

    def test_presa_a_la_BASE_segueix_permesa(self):
        """No-regressió: el camí de sempre no canvia."""
        resp = self._patch(self.lines[BASE], valor_real=21)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._linia(BASE).valor_real, 21)


class DecisioNomesABaseTest(GuardPartitBase):
    """LA MEITAT QUE ES QUEDA TANCADA: R2 — els ajustos s'accepten NOMÉS a la base."""

    def test_DECISIO_a_talla_NO_base_es_400(self):
        resp = self._patch(self.lines['L'], decisio='ACCEPTED')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['detail'], NON_BASE_DECISIO_DETAIL)
        self.assertEqual(self._linia('L').decisio, '')

    def test_DECISIO_a_la_BASE_es_permesa(self):
        resp = self._patch(self.lines[BASE], decisio='ADJUSTED')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._linia(BASE).decisio, 'ADJUSTED')

    def test_presa_i_decisio_al_MATEIX_payload_es_400_i_NO_desa_la_presa(self):
        """🚨 EL CAS QUE FA FALTA EL GUARD PER PAYLOAD I NO PER ENDPOINT.

        Un payload mixt no pot colar la decisió aprofitant que la presa és legal, ni desar
        la presa a mitges d'un rebuig: o entra tot o no entra res.
        """
        resp = self._patch(self.lines['L'], valor_real=77, decisio='ACCEPTED')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['detail'], NON_BASE_DECISIO_DETAIL)
        self.assertEqual(self._linia('L').valor_real, TEORICS['L'])   # la presa NO s'ha desat
        self.assertEqual(self._linia('L').decisio, '')

    def test_decisio_BUIDA_a_talla_no_base_tambe_es_400(self):
        """Desdir-se és decidir. `''` és el gest de treure el veredicte, no l'absència de gest:
        si passés, hi hauria un camí per tocar `decisio` fora de la base."""
        resp = self._patch(self.lines['L'], decisio='')
        self.assertEqual(resp.status_code, 400)

    def test_propagar_des_de_NO_base_segueix_400(self):
        """R2, l'altra meitat: la propagació surt de la base i de cap altre lloc."""
        resp = self._propagar(self.lines['L'], 50)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['detail'], NON_BASE_LINE_DETAIL)
        self.assertEqual(self._linia('L').valor_real, TEORICS['L'])


class OrdreDelsGuardsTest(GuardPartitBase):
    """L'ESTAT MANA SOBRE L'EIX, i segueix manant també per a la presa que ara és legal."""

    def test_sessio_segellada_barra_fins_i_tot_la_presa_no_base(self):
        self._seal('Tancada')
        resp = self._patch(self.lines['L'], valor_real=33)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self._linia('L').valor_real, TEORICS['L'])

    def test_sessio_anullada_barra_la_presa_no_base(self):
        self._seal('Anullada')
        resp = self._patch(self.lines['L'], valor_real=33)
        self.assertEqual(resp.status_code, 409)


class ConsolidacioIgnoraPresaNoBaseTest(GuardPartitBase):
    """LA PROMESA DEL GUARD PARTIT: obrir la presa NO obre cap escriptura de domini.

    És el test que fa que la resta sigui segura. Si algun dia algú fa que el `close`
    consolidi qualsevol talla, aquest vermell és el que ho dirà.
    """

    def test_una_presa_no_base_NO_toca_cap_BaseMeasurement_en_tancar(self):
        from fhort.fitting.services import close_piece_fitting
        self.assertEqual(self._patch(self.lines['L'], valor_real=99).status_code, 200)
        self.assertEqual(self._patch(self.lines['XL'], valor_real=98).status_code, 200)
        abans = list(BaseMeasurement.objects
                     .filter(model=self.model)
                     .values_list('pom_id', 'base_value_cm').order_by('pom_id'))
        close_piece_fitting(self.pf.pk, user_profile_id=self.profile.pk)
        despres = list(BaseMeasurement.objects
                       .filter(model=self.model)
                       .values_list('pom_id', 'base_value_cm').order_by('pom_id'))
        self.assertEqual(abans, despres)

    def test_la_presa_de_la_BASE_si_que_consolida(self):
        """El contrapunt: sense això, el test de sobre passaria amb el `close` trencat."""
        from fhort.fitting.services import close_piece_fitting
        self.assertEqual(self._patch(self.lines[BASE], valor_real=25).status_code, 200)
        close_piece_fitting(self.pf.pk, user_profile_id=self.profile.pk)
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom)
        self.assertEqual(bm.base_value_cm, 25)
