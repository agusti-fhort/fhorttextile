"""E1/B3 · LA PRESA DE L'ESCALAT — dada d'observació, no edició de la corba.

Substrat: `docs/diagnosis/DIAGNOSI_E1_MESURA_ESCALAT.md` §1.3 (què escrivia) i §3.2 (per què
el pas 2 es mirava al mirall).

🚨 EL COR D'AQUEST BANC SÓN DOS `assertEqual` QUE NO MIREN LA RESPOSTA:
`test_la_presa_NO_toca_BaseMeasurement` i `test_la_presa_NO_re_deriva_els_specs`. Tota la
resta és contorn. La porta que aquesta substitueix (`escalat_ajustar_talla_view`) feia
EXACTAMENT aquestes dues coses a cada tecla —escrivia la base i re-derivava els specs—, i per
això «Mesurar prenda» clonava com a teòric el valor que el tècnic acabava d'anotar i la
desviació sortia sempre zero. Si algun dia algú torna a endollar una escriptura de domini
aquí dins, aquests dos tests són l'única cosa que ho dirà.

El fixture porta el POM viu a la MARE i a la peça `02` amb la mateixa `(capa, instancia)` —la
topologia del POM 962 del 1379—, perquè cap test pugui passar per casualitat amb una clau
parcial.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.escalat_presa_views import EscalatPresaView
from fhort.fitting.models import (
    FittingSession, GradedSpec, GradingVersion, PieceFitting, PieceFittingLine, SizeFitting,
)
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.identitat import clau_mesura
from fhort.pom.models import (
    GradingRule, GradingRuleSet, POMMaster, SizeDefinition, SizeSystem,
)

TEORICS = {'XS': 46.0, 'S': 48.0, 'M': 50.0, 'L': 52.0, 'XL': 54.0}
BASE = 'M'
MARE = ''
SEGONA = '02'


class PresaEscalatBase(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='tester_presa')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Tester', 'rol_nom': 'admin'})

        ss = SizeSystem.objects.create(codi='SS_P', nom='SS presa', base_unit='ALPHA')
        talles = {et: SizeDefinition.objects.create(size_system=ss, etiqueta=et, ordre=i)
                  for i, et in enumerate(TEORICS, start=1)}
        self.rs = GradingRuleSet.objects.create(nom='RS presa')
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        GradingRule.objects.create(rule_set=self.rs, pom=self.pom, talla_base=talles[BASE],
                                   logica='LINEAR', increment_base=2)
        self.model = Model.objects.create(
            codi_intern='E1-PRESA', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='XS·S·M·L·XL', base_size_label=BASE,
            size_system=ss, grading_rule_set=self.rs)

        # LA MESURA VIU A DUES PRENDES amb la mateixa (capa, instància): és el cas que impedeix
        # que un lookup parcial passi per casualitat.
        self.bm_mare = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, garment=MARE,
            base_value_cm=TEORICS[BASE], is_active=True)
        self.bm_02 = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, garment=SEGONA,
            base_value_cm=30.0, is_active=True)

        sf, _ = SizeFitting.objects.update_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-E1P-1', 'tipus': 'PRINCIPAL', 'creat_per': self.profile})
        self.gv = GradingVersion.objects.create(size_fitting=sf, version_number=1,
                                                is_active=True, creat_per=self.profile)
        self.factory = APIRequestFactory()
        self.view = EscalatPresaView.as_view()

    # ── helpers ─────────────────────────────────────────────────────────────────────────
    def _obre_presa(self, estat='Oberta'):
        """Obre la presa a mà (sessió + peça + línies), com fa el gest explícit."""
        sessio = FittingSession.objects.create(
            model=self.model, fase='Dev', data=datetime.date(2026, 8, 17), estat=estat)
        pf = PieceFitting.objects.create(session=sessio, model=self.model,
                                         grading_version=self.gv)
        self.lines = {}
        for garment, base_val in ((MARE, TEORICS[BASE]), (SEGONA, 30.0)):
            for sl, v in TEORICS.items():
                teoric = v if garment == MARE else base_val + (v - TEORICS[BASE])
                self.lines[(garment, sl)] = PieceFittingLine.objects.create(
                    piece_fitting=pf, pom=self.pom, size_label=sl, garment=garment,
                    valor_teoric=teoric, valor_real=teoric)
        self.sessio, self.pf = sessio, pf
        return pf

    def _get(self):
        req = self.factory.get('/presa/')
        force_authenticate(req, user=self.user)
        return self.view(req, model_id=self.model.id)

    def _post(self, **body):
        req = self.factory.post('/presa/', body, format='json')
        force_authenticate(req, user=self.user)
        return self.view(req, model_id=self.model.id)

    def _clau(self, garment=MARE, talla='L'):
        return f'{clau_mesura(self.pom.id, "exterior", "", garment)}:{talla}'

    def _bases(self):
        return sorted(BaseMeasurement.objects.filter(model=self.model)
                      .values_list('garment', 'base_value_cm'))


class SensePresaObertaTest(PresaEscalatBase):
    """No es crea sessió des d'una cel·la (decisió D5: OBERTA)."""

    def test_GET_diu_que_no_hi_ha_presa_i_no_es_queda_mut(self):
        r = self._get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['presa_oberta'], False)
        self.assertEqual(r.data['preses'], {})
        self.assertEqual(r.data['resum']['n_preses'], 0)
        self.assertEqual(r.data['base_size'], BASE)      # la pantalla segueix sabent el seu eix

    def test_POST_sense_presa_oberta_es_409_amb_codi_accionable(self):
        r = self._post(pom_id=self.pom.id, talla='L', valor=53)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['codi'], 'sense_presa_oberta')
        self.assertEqual(PieceFittingLine.objects.count(), 0)

    def test_una_sessio_SEGELLADA_no_es_una_presa_oberta(self):
        self._obre_presa(estat='Tancada')
        self.assertEqual(self._get().data['presa_oberta'], False)
        r = self._post(pom_id=self.pom.id, talla='L', valor=53)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['codi'], 'sense_presa_oberta')
        # I res s'ha desat sobre l'acta.
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines[(MARE, 'L')].pk).valor_real,
            TEORICS['L'])


class LaPresaNoEsUnaEscripturaDeDominiTest(PresaEscalatBase):
    """🚨 EL COR. La presa és observació; consolidar i propagar tenen les seves portes."""

    def setUp(self):
        super().setUp()
        self._obre_presa()

    def test_la_presa_NO_toca_BaseMeasurement(self):
        abans = self._bases()
        r = self._post(pom_id=self.pom.id, talla='L', valor=53.4)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._bases(), abans)

    def test_la_presa_de_la_TALLA_BASE_tampoc_toca_BaseMeasurement(self):
        """El cas que més s'hi assembla i el que abans SÍ escrivia: la base."""
        abans = self._bases()
        r = self._post(pom_id=self.pom.id, talla=BASE, valor=51.2)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._bases(), abans)

    def test_la_presa_NO_re_deriva_els_specs(self):
        GradedSpec.objects.create(grading_version=self.gv, pom=self.pom, size_label='L',
                                  graded_value_cm=52.0, grading_type_applied='LINEAR')
        abans = sorted(GradedSpec.objects.filter(grading_version=self.gv)
                       .values_list('size_label', 'graded_value_cm'))
        self._post(pom_id=self.pom.id, talla='L', valor=53.4)
        self.assertEqual(
            sorted(GradedSpec.objects.filter(grading_version=self.gv)
                   .values_list('size_label', 'graded_value_cm')), abans)

    def test_la_presa_NO_escriu_cap_veredicte(self):
        self._post(pom_id=self.pom.id, talla=BASE, valor=51.2)
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines[(MARE, BASE)].pk).decisio, '')


class AnotarLaPresaTest(PresaEscalatBase):

    def setUp(self):
        super().setUp()
        self._obre_presa()

    def test_anota_la_talla_no_base_i_torna_la_desviacio_calculada(self):
        r = self._post(pom_id=self.pom.id, talla='L', valor=53.4)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['id'], self._clau(MARE, 'L'))
        self.assertEqual(r.data['teoric'], 52.0)
        self.assertEqual(r.data['real'], 53.4)
        self.assertEqual(r.data['desviacio'], 1.4)
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines[(MARE, 'L')].pk).valor_real, 53.4)

    def test_valor_buit_TREU_la_presa_i_no_esborra_la_linia(self):
        self._post(pom_id=self.pom.id, talla='L', valor=53.4)
        r = self._post(pom_id=self.pom.id, talla='L', valor='')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['real'], None)
        self.assertEqual(r.data['desviacio'], None)
        linia = PieceFittingLine.objects.get(pk=self.lines[(MARE, 'L')].pk)
        self.assertEqual(linia.valor_real, TEORICS['L'])   # torna al teòric
        self.assertEqual(PieceFittingLine.objects.filter(pk=linia.pk).count(), 1)

    def test_la_presa_de_la_02_NO_toca_la_de_la_MARE(self):
        r = self._post(pom_id=self.pom.id, talla='L', valor=33.3, garment=SEGONA)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['id'], self._clau(SEGONA, 'L'))
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines[(SEGONA, 'L')].pk).valor_real, 33.3)
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines[(MARE, 'L')].pk).valor_real,
            TEORICS['L'])

    def test_aquesta_porta_NO_decideix(self):
        r = self._post(pom_id=self.pom.id, talla=BASE, valor=51, decisio='ACCEPTED')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data['codi'], 'presa_no_decideix')
        self.assertEqual(
            PieceFittingLine.objects.get(pk=self.lines[(MARE, BASE)].pk).valor_real,
            TEORICS[BASE])

    def test_la_guarda_de_rang_fisic_hi_es(self):
        r = self._post(pom_id=self.pom.id, talla='L', valor=22224.7)
        self.assertEqual(r.status_code, 422)

    def test_una_mesura_sense_linia_es_404_i_no_se_nINVENTA_cap(self):
        altre = POMMaster.objects.create(codi_client='ZZ', nom_client='Cap línia')
        n = PieceFittingLine.objects.count()
        r = self._post(pom_id=altre.id, talla='L', valor=10)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.data['codi'], 'sense_linia')
        self.assertEqual(PieceFittingLine.objects.count(), n)

    def test_calen_pom_i_talla(self):
        self.assertEqual(self._post(talla='L', valor=1).status_code, 400)
        self.assertEqual(self._post(pom_id=self.pom.id, valor=1).status_code, 400)


class LecturaDeLaPresaTest(PresaEscalatBase):

    def setUp(self):
        super().setUp()
        self._obre_presa()

    def test_LA_SEMBRA_NO_ES_UNA_PRESA(self):
        """10 línies vives, cap mesurada: `real` a null a totes i el recompte a zero."""
        r = self._get()
        self.assertEqual(r.data['resum']['n_linies'], 10)
        self.assertEqual(r.data['resum']['n_preses'], 0)
        self.assertEqual(r.data['resum']['talles_amb_presa'], [])
        self.assertTrue(all(c['real'] is None for c in r.data['preses'].values()))
        # …i el teòric hi és igualment: la columna esperada no depèn d'haver mesurat.
        self.assertEqual(r.data['preses'][self._clau(MARE, 'L')]['teoric'], 52.0)

    def test_despres_de_mesurar_el_resum_ho_diu(self):
        self._post(pom_id=self.pom.id, talla='L', valor=53.4)
        self._post(pom_id=self.pom.id, talla='XL', valor=55.0)
        r = self._get()
        self.assertEqual(r.data['resum']['n_preses'], 2)
        self.assertEqual(sorted(r.data['resum']['talles_amb_presa']), ['L', 'XL'])
        self.assertEqual(r.data['preses'][self._clau(MARE, 'L')]['desviacio'], 1.4)

    def test_el_resum_compta_les_DECISIONS_de_la_base_per_prenda(self):
        """La barra d'estat ha de poder dir quantes queden per decidir; les de base són les
        úniques que es decideixen (R2), i n'hi ha una per prenda."""
        r = self._get()
        self.assertEqual(r.data['resum']['pendents_base'], 2)   # mare + 02
        self.assertEqual(r.data['resum']['decidides_base'], 0)
        self.lines[(MARE, BASE)].decisio = 'ACCEPTED'
        self.lines[(MARE, BASE)].save(update_fields=['decisio'])
        r = self._get()
        self.assertEqual(r.data['resum']['decidides_base'], 1)
        self.assertEqual(r.data['resum']['pendents_base'], 1)

    def test_la_sessio_viatja_perque_el_flux_es_PAUSABLE(self):
        r = self._get()
        self.assertEqual(r.data['session']['id'], self.sessio.id)
        self.assertEqual(r.data['session']['data'], '2026-08-17')
        self.assertEqual(r.data['session']['estat'], 'Oberta')

    def test_la_clau_del_payload_es_la_que_MeasureGrid_entén(self):
        """`{clau}:{talla}` — la mateixa forma que `buildEscalatRows` fabrica com a `lineId`.
        Si divergissin, el refresc d'una cel·la no arribaria mai a la seva cel·la (el mode de
        fallada MUT que C4/BLOC 2 ② ja va tancar una vegada)."""
        r = self._get()
        self.assertIn(f'{self.pom.id}|exterior||:L', r.data['preses'])
        self.assertIn(f'{self.pom.id}|exterior||{SEGONA}:L', r.data['preses'])
