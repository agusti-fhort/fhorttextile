"""S42/F7 — LA IDENTITAT D'UNA LÍNIA DEL FULL DE FITTING ÉS DE QUATRE EIXOS.

EL DANY, tal com es va veure al 1379 (Patró A · Q5/Q7). El POM 962 viu a les DUES prendes
del model amb la MATEIXA capa i la MATEIXA instància — només el `garment` els separa:

    bm 3344 · garment ''   (mare)  · nom_fitxa 'G1'
    bm 3354 · garment '02' (Short) · nom_fitxa 'M1'

`PieceFittingGridSerializer.get_lines` resolia cada línia amb `(pom, capa, instancia)` i els
quatre mapes que en pengen es construïen amb la mateixa clau curta sobre TOT el model. Amb la
frontera de prenda al mig, les dues files hi queien a sobre i **l'última escrita guanyava**:
les dues sortien amb `nom_fitxa 'M1'` i `bm_id 3354`.

I això no és només un rètol:

  · `nom_fitxa` és el que s'IMPRIMEIX a la columna CODE del full que va al fabricant
    (`FittingPrintSheet.jsx`): la fila de la mare sortia batejada com la del Short.
  · `bm_id` és el DESTÍ D'ESCRIPTURA del bateig des de la superfície de Fitting (P4):
    rebatejar la fila de la mare escrivia a la `BaseMeasurement` DE L'ALTRA PRENDA.

L'argument és, literal, el mateix que va fer entrar la capa (C2/Onada 1) i la instància
(FASE_2/C1-ins) a aquesta mateixa clau; el quart eix hi faltava. I la llei que aquell
comentari ja declara —**els mapes creixen ALHORA**— és per què aquí hi entren els cinc de cop
(els quatre de `BaseMeasurement` i el de `GradedSpec`): un que s'ancorés i un altre que no
deixaria una fila amb l'ordre d'una prenda i el nom d'una altra.

⚠️ EL CONTROL NO ÉS DECORATIU. Els dos casos d'una sola peça pinen que un model sense `'02'`
—que és tot el corpus d'ahir— surt EXACTAMENT igual que abans: la clau més llarga no pot
canviar res on no hi ha frontera.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.fitting.models import (
    FittingSession, GradedSpec, GradingVersion, PieceFitting, PieceFittingLine, SizeFitting,
)
from fhort.fitting.serializers import PieceFittingGridSerializer
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem

RUN = ['S', 'M', 'L']
BASE = 'M'
MARE = ''
SEGONA = '02'

# ⚠️ AQUÍ NO HI HA `comportes_garment_alcades`, i és a posta. Els tests germans d'aquesta
# família (`test_set2_t6a_graded_table_eix.py:47`) embolcallen el fixture en un helper que
# feia `DROP CONSTRAINT IF EXISTS … garment_gate_set2` dins d'un savepoint i el desfeia al
# `finally`. Les comportes **ja no existeixen** —verificat a `pg_constraint`, tant a la BD
# viva com a la de test—, o sigui que avui aquell helper només fa una cosa: el
# `savepoint_rollback` s'endú TAMBÉ les files del fixture. Un test que assereixi després del
# bloc troba la graella buida. S'hi va caure escrivint aquest fitxer i queda dit aquí perquè
# el proper que copiï el patró no hi torni a caure.


class _F7Base(TenantTestCase):
    """Fixture compartit i CAP test (mateix motiu que `_T6aBase`: `unittest` recull els
    mètodes heretats i una classe de control que hereti els casos els torna a córrer)."""

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
        self.user = get_user_model().objects.create(username='f7')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'F7', 'rol_nom': 'admin'})
        self.ss = SizeSystem.objects.create(codi='SS_F7', nom='SS F7', base_unit='ALPHA')
        for i, sl in enumerate(RUN):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=sl, ordre=i)
        # El POM de la frontera: un de sol, viu a les dues prendes (el 962 del 1379).
        self.pom = POMMaster.objects.create(codi_client='G1', nom_client='Bottom finish height')
        # I un POM que viu a UNA sola peça: el control de «res canvia on no hi ha frontera».
        self.pom_sol = POMMaster.objects.create(codi_client='B', nom_client='Waist width')
        self.model = Model.objects.create(
            codi_intern='TST-F7', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_system=self.ss, size_run_model='·'.join(RUN),
            base_size_label=BASE,
        )
        self.sf = SizeFitting.objects.filter(model=self.model).first()
        self.gv = GradingVersion.objects.create(
            size_fitting=self.sf, version_number=1, is_active=True, creat_per=self.profile)
        sessio = FittingSession.objects.create(
            model=self.model, fase='PROTO', data=datetime.date(2026, 8, 16))
        self.pf = PieceFitting.objects.create(
            session=sessio, model=self.model, grading_version=self.gv)

    # ── Peces del fixture ────────────────────────────────────────────────────
    def _bm(self, pom, garment, nom_fitxa, ordre, origen='STANDARD'):
        return BaseMeasurement.objects.create(
            model=self.model, pom=pom, capa='exterior', instancia='', garment=garment,
            nom_fitxa=nom_fitxa, ordre=ordre, base_value_cm=3.5, is_active=True,
            origen=origen)

    def _linia(self, pom, garment, valor):
        return PieceFittingLine.objects.create(
            piece_fitting=self.pf, pom=pom, size_label=BASE, capa='exterior', instancia='',
            garment=garment, valor_teoric=valor)

    def _spec(self, pom, garment, valor):
        return GradedSpec.objects.create(
            grading_version=self.gv, pom=pom, size_label=BASE, capa='exterior', instancia='',
            garment=garment, graded_value_cm=valor, increment_applied_cm=0,
            grading_type_applied='FIXED', is_active=True)

    def _files(self):
        return {
            (l['pom_id'], l['garment']): l
            for l in PieceFittingGridSerializer(self.pf).data['lines']
        }


class IdentitatLiniaPerGarmentTest(_F7Base):
    """EL PIN DEL DANY: el 1379, amb els noms i els valors ben distints perquè un col·lapse
    canti a la primera i no s'amagui darrere de dues xifres iguals."""

    def setUp(self):
        super().setUp()
        # Els `origen` són distints a posta: és el quart mapa de la família i sense dos
        # valors diferents un col·lapse no es veuria.
        self.bm_mare = self._bm(self.pom, MARE, 'G1', ordre=1, origen='MANUAL')
        self.bm_short = self._bm(self.pom, SEGONA, 'M1', ordre=2, origen='FITTED')
        self._linia(self.pom, MARE, 3.5)
        self._linia(self.pom, SEGONA, 3.5)
        self._spec(self.pom, MARE, 100.0)
        self._spec(self.pom, SEGONA, 50.0)
        self.files = self._files()

    def test_el_nom_de_cada_fila_es_el_de_la_SEVA_prenda(self):
        """El que s'imprimeix al full. Abans de F7: totes dues deien 'M1'."""
        self.assertEqual(self.files[(self.pom.id, MARE)]['nom_fitxa'], 'G1')
        self.assertEqual(self.files[(self.pom.id, SEGONA)]['nom_fitxa'], 'M1')
        # `nom` és el que la columna CODE del full pinta (nom_fitxa amb fallback al codi).
        self.assertEqual(self.files[(self.pom.id, MARE)]['nom'], 'G1')
        self.assertEqual(self.files[(self.pom.id, SEGONA)]['nom'], 'M1')

    def test_el_bm_id_de_cada_fila_apunta_a_la_SEVA_mesura(self):
        """LA PART GREU: `bm_id` és on el bateig ESCRIU. Abans de F7 les dues files
        apuntaven a la `BaseMeasurement` del Short."""
        self.assertEqual(self.files[(self.pom.id, MARE)]['bm_id'], self.bm_mare.id)
        self.assertEqual(self.files[(self.pom.id, SEGONA)]['bm_id'], self.bm_short.id)
        self.assertNotEqual(
            self.files[(self.pom.id, MARE)]['bm_id'],
            self.files[(self.pom.id, SEGONA)]['bm_id'],
            'dues prendes no poden compartir el destí d\'escriptura del bateig')

    def test_l_evolucio_de_cada_fila_porta_les_SEVES_xifres(self):
        """El cinquè mapa: `spec_map`. La columna d'evolució serveix justament per veure si
        una mesura s'ha mogut; amb la clau curta ensenyava la de l'altra prenda."""
        ev_mare = self.files[(self.pom.id, MARE)]['evolucio']
        ev_short = self.files[(self.pom.id, SEGONA)]['evolucio']
        self.assertEqual([e['valor_cm'] for e in ev_mare], [100.0])
        self.assertEqual([e['valor_cm'] for e in ev_short], [50.0])

    def test_l_origen_de_cada_fila_es_el_de_la_SEVA_mesura(self):
        """El quart mapa. `origen` és el que diu si una germana l'ha moguda el sistema
        (`DERIVAT`) o l'ha mesurada algú: atribuir-lo a la peça equivocada és dir que una
        mesura s'ha pres quan no s'ha pres."""
        self.assertEqual(len(self.files), 2)
        self.assertEqual(self.files[(self.pom.id, MARE)]['origen'], 'MANUAL')
        self.assertEqual(self.files[(self.pom.id, SEGONA)]['origen'], 'FITTED')


class PomDUnaSolaPecaTest(_F7Base):
    """CONTROL 1 — un POM que viu a UNA sola peça d'un model que en té dues: la clau més
    llarga no el pot moure."""

    def setUp(self):
        super().setUp()
        self.bm_mare = self._bm(self.pom, MARE, 'G1', ordre=1)
        self.bm_short = self._bm(self.pom, SEGONA, 'M1', ordre=2)
        self.bm_sol = self._bm(self.pom_sol, MARE, 'B', ordre=3)
        self._linia(self.pom, MARE, 3.5)
        self._linia(self.pom, SEGONA, 3.5)
        self._linia(self.pom_sol, MARE, 41.5)
        self.files = self._files()

    def test_el_pom_sense_germana_de_prenda_resol_igual_que_sempre(self):
        fila = self.files[(self.pom_sol.id, MARE)]
        self.assertEqual(fila['nom_fitxa'], 'B')
        self.assertEqual(fila['bm_id'], self.bm_sol.id)


class ModelDUnaSolaPecaTest(_F7Base):
    """CONTROL 2 — el corpus d'ahir: cap fila amb `garment`. Tot resol contra '' com sempre,
    i el payload ha de ser el mateix camp a camp."""

    def setUp(self):
        super().setUp()
        self.bm_a = self._bm(self.pom, MARE, 'G1', ordre=1)
        self.bm_b = self._bm(self.pom_sol, MARE, 'B', ordre=2)
        self._linia(self.pom, MARE, 3.5)
        self._linia(self.pom_sol, MARE, 41.5)
        self._spec(self.pom, MARE, 100.0)
        self.files = self._files()

    def test_un_model_duna_peca_surt_exactament_com_abans(self):
        self.assertEqual(len(self.files), 2)
        self.assertEqual(self.files[(self.pom.id, MARE)]['nom_fitxa'], 'G1')
        self.assertEqual(self.files[(self.pom.id, MARE)]['bm_id'], self.bm_a.id)
        self.assertEqual(self.files[(self.pom_sol.id, MARE)]['nom_fitxa'], 'B')
        self.assertEqual(self.files[(self.pom_sol.id, MARE)]['bm_id'], self.bm_b.id)
        self.assertEqual(
            [e['valor_cm'] for e in self.files[(self.pom.id, MARE)]['evolucio']], [100.0])

    def test_l_ordre_de_fitxa_es_conserva(self):
        """L'ordre surt de `BaseMeasurement.ordre` amb desempat per codi de client, i la
        clau més llarga no l'ha de tocar."""
        lines = PieceFittingGridSerializer(self.pf).data['lines']
        self.assertEqual([l['pom_id'] for l in lines], [self.pom.id, self.pom_sol.id])
