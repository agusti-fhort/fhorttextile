"""C4 · EL CAS POSITIU D'ACCEPTACIÓ — dues germanes vives han de sortir a CADA superfície.

✅ **VERD DES DEL BLOC 1 DE C4 (04/08).** Aquest fitxer va néixer saltat sencer i vermell a
posta: mesurava un forat obert. El bloc 1 el va tancar desancorant els lectors, i ara corre a
cada execució de `fhort.models_app` — de mesura del forat ha passat a guàrdia perquè no torni.
✅ **SENCER DES DEL BLOC 3 (04/08).** L'últim mètode saltat, `test_10` (model-poms del
taller), s'ha despertat: la contradicció de scope que el tenia aturat l'ha resolta l'Agus amb
la llei **dues cares, dues línies**. Cap mètode saltat: les 10 superfícies corren.

⚠️ **Segueix sent PROHIBIT fer-lo verd tocant-lo.** Si un assert d'aquí falla, el que s'ha
trencat és un lector, no l'assert: comparar només la germana d'exterior o acceptar 1 fila on
n'hi ha d'haver 4 destruiria l'única eina que mesura si els lectors segueixen sencers.

PER QUÈ AQUEST FITXER EXISTEIX
------------------------------
La diagnosi de C4 (`docs/diagnosis/DIAGNOSI_C4_ONA_REAL.md` §0.2) va trobar que els lectors de
payload **no s'han resolt i no s'han quedat igual: s'han ANCORAT**. Avui filtren explícitament
`capa='exterior', instancia=''`, amb acta escrita al codi que difereix el canvi de contracte a
C4 (l'exemple canònic és `fitting/graded_spec_views.py:97-104`).

Amb les comportes retirades i una germana viva, aquests endpoints **ja no col·lapsaran
(l'última guanya): AMAGARAN** —la germana no surt del `filter`—. Passar de «dada equivocada» a
«dada absent» és millor per a la integritat i **pitjor per a la detecció**: la pantalla es
veurà coherent i correcta, i faltarà una fila.

**Cap test d'avui pot veure això.** Amb les comportes vives, el conjunt filtrat i el conjunt
sencer són EL MATEIX conjunt: qualsevol test de no-regressió passa igual amb àncora i sense.
Per tant el green flag de C4 **no pot ser la no-regressió** —no trencarà res—: ha de ser un
test que AFIRMI que dues germanes vives surten a cada superfície. Això és aquest fitxer.

EL QUE VA MESURAR (03/08, HEAD `923c4c16`) I EL QUE VA TANCAR (04/08, bloc 1)
-----------------------------------------------------------------------------
De les **10 superfícies**, 6 amagaven la germana. El bloc 1 n'ha desancorat 5:

    ✅ base_stages                (models_app/views.py:3046)   ja hi era
    ✅ size-check                 (serializers_size_check)     ja hi era
    ✅ CSV de fitting             (pom/s8_views)               ja hi era
    ✅ fitting vs spec            (pom/s10_views)              ja hi era
    ✅ payload de fitxa           (fitting/graded_spec_views)  C4/1 · era 1 de 4
    ✅ repàs                      (fitting/repas_views)        C4/2 · eren 2 files per 4,
                                                               i una SENSE NOM
    ✅ s6 · mesures base          (pom/s6_views)               C4/3 · era 1 de 4
    ✅ s6 · specs graduats        (pom/s6_views)               C4/3 · era 1 de 4
    ✅ cells de grading           (pom/grading_views)          C4/4 · era 1 de 4
    ✅ deltes de taula de mesures (models_app/views.py:1771)   C4/5 · 4 files i 2 deltes
    ✅ model-poms del taller      (patterns/views.py:605)      C4/3 · era 1 de 4 — el
                                                               queryset desancorat al bloc 3;
                                                               `PatternPOM` NO s'ha tocat

**Hi havia DOS modes de fallada, i el segon era el pitjor de veure.** Cinc superfícies
AMAGAVEN (la germana no sortia del `filter`: faltava una fila i la pantalla es veia coherent).
La dels deltes NO amagava: pintava les quatre files i en resumia els deltes a un dict per
`pom_id` sol, o sigui que dues files ensenyaven el delta de la seva germana com si fos seu.

Les quatre que ja passaven ho feien perquè el seu queryset no filtrava I la seva clau de
sortida portava prou identitat (línia per línia, no dict per POM). Van ser el motlle de les
altres: no va caldre inventar cap forma nova.

EL BANC
-------
Bessó fidel del model **269 · BRW-FW27-0002** de staging (base `S`, run `XXS·XS·S·M·L`,
regla LINEAR +1), que és el banc que C3 va fer servir. Dues parelles de germanes, cadascuna
d'un eix, i amb els valors deliberadament lluny els uns dels altres perquè cap assert pugui
fallar per un decimal:

    POM A · parella de CAPA        A-EXT (exterior) 46.0   ·   A-FOL (folre) 40.0
    POM B · parella d'INSTÀNCIA    B-ESQ (left)     30.0   ·   B-DRE (right) 20.0

El POM B **no té cap fila d'instància única**: és el cas real d'un POM que només es mesura
per instància (la sisa esquerra i la dreta, sense «la sisa»). Contra un lector ancorat a
`instancia=''`, el POM B desapareix SENCER — cap fila, no una de sobrant.

Les 20 cel·les graduades resultants són totes distintes (44-48 · 38-42 · 28-32 · 18-22), o
sigui que cap assert pot passar per coincidència.

El harness de comporta alçada és el de `test_lectors_capa_onada1.py:35-52`, autoritzat
expressament per a aquesta feina: alça les comportes dins d'un savepoint que SEMPRE es desfà.
Cap DDL sobreviu al test.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import contextlib
import csv
import datetime
import io

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import (BaseMeasurement, MeasurementChangeLog,
                                     Model, ModelGradingRule, SizeCheck,
                                     SizeCheckLine)
from fhort.pom.models import (MeasurementLayer, POMMaster, SizeDefinition,
                              SizeSystem)

EXTERIOR = MeasurementLayer.SLUG_DEFECTE
FOLRE = 'folre'
ESQUERRA = 'left'
DRETA = 'right'

#: Les cinc taules gatejades que el camí d'aquest test travessa. No n'hi ha cap de sobrera:
#: `basemeasurement` per escriure la germana · `measurementchangelog` perquè el signal F1 hi
#: estampa els eixos dins la mateixa transacció · `gradedspec` perquè és on aterra el motor ·
#: `sizecheckline` i `piecefittingline` perquè són les dues taules de mesura presa.
TAULES = ('models_app_basemeasurement', 'models_app_measurementchangelog',
          'fitting_gradedspec', 'models_app_sizecheckline',
          'fitting_piecefittingline')

EIXOS = ('capa_gate_c1', 'instancia_gate_cins')

TALLES = ['XXS', 'XS', 'S', 'M', 'L']
BASE = 'S'

#: (nom_fitxa, capa, instancia, valor a talla base). L'ordre és el de `BaseMeasurement.ordre`.
GERMANES = (
    ('A-EXT', EXTERIOR, '', 46.0),
    ('A-FOL', FOLRE, '', 40.0),
    ('B-ESQ', EXTERIOR, ESQUERRA, 30.0),
    ('B-DRE', EXTERIOR, DRETA, 20.0),
)
NOMS = {n for n, _c, _i, _v in GERMANES}
BASES = {v for _n, _c, _i, v in GERMANES}



@contextlib.contextmanager
def comportes_alcades(*taules, eixos=EIXOS):
    """Alça les comportes de `taules` dins d'un savepoint que SEMPRE es desfà.

    El `finally` no és decoratiu: si un assert peta a dins, la comporta ha de tornar igual.
    L'invariant `..._instancia_exigeix_nom` NO s'alça mai: una germana ha de tenir nom, i
    aquesta regla ha de SOBREVIURE C4 (diagnosi §4.1).
    """
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                for sufix in eixos:
                    # `IF EXISTS` — C4/G1 (04/08): les comportes es RETIREN per grups, i a
                    # partir del primer aquest harness demana de treure'n algunes que ja no
                    # hi són. Sense això, cada grup retirat deixaria vermell tot el fitxer
                    # que precisament ha de demostrar que la retirada és segura.
                    # No afluixa res: alçar una comporta que no existeix és exactament el
                    # mateix estat que alçar-la, i el `finally` segueix retornant el
                    # savepoint tant si hi havia constraint com si no.
                    cur.execute(
                        f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                        f'DROP CONSTRAINT IF EXISTS "{taula}_{sufix}"'
                    )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class GermanesALesSuperficiesC4Test(TenantTestCase):
    """Cada mètode és UNA superfície de la llista de C4. El que falla, amaga la germana.

    ✅ C4/BLOC 1 — EL SKIP DE CLASSE SE'N VA. Aquest fitxer va néixer saltat sencer perquè
    mesurava un forat obert: 6 de les 10 superfícies amagaven la germana i un vermell permanent
    hauria embrutat la línia base. El bloc 1 les ha desancorades i el contracte ja corre a cada
    execució de `fhort.models_app`, que és on ha d'estar: vigilant que no torni a passar.

    Cap mètode saltat des del bloc 3: `test_10` (model-poms) s'hi va despertar amb la llei
    «dues cares, dues línies».
    """

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
        self.pom_a = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.pom_b = POMMaster.objects.create(codi_client='AH', nom_client='Sisa')
        self.ss = SizeSystem.objects.create(codi='SS_C4', nom='SS C4', base_unit='ALPHA')
        for i, et in enumerate(TALLES):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='TST-C4', codi_tenant='TST', any=2027, sequencial=2,
            temporada='FW27', size_system=self.ss,
            size_run_model='·'.join(TALLES), base_size_label=BASE,
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_c4', defaults={'email': 'qa@c4.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA C4', 'rol_nom': 'QA'})
        # `get_or_create`: un signal ja crea l'SF numero=1 en néixer el Model.
        from fhort.fitting.models import SizeFitting
        self.sf, _ = SizeFitting.objects.get_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-C4', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.perfil},
        )
        for pom in (self.pom_a, self.pom_b):
            ModelGradingRule.objects.create(
                model=self.model, pom=pom, logica='LINEAR', increment=1.0, actiu=True)

    # ── El banc ──────────────────────────────────────────────────────────────────────

    def _germanes(self):
        """Les quatre files. Toleràncies distintes per parella: 0.5 la primera, 2.0 la
        segona, perquè les superfícies que jutgen (s10, s8, size-check) puguin demostrar
        que cada línia s'ha jutjat amb LA SEVA vara i no amb la de la germana."""
        fetes = {}
        for ordre, (nom, capa, instancia, valor) in enumerate(GERMANES, start=1):
            fetes[nom] = BaseMeasurement.objects.create(
                model=self.model, pom=(self.pom_a if nom.startswith('A') else self.pom_b),
                base_value_cm=valor, ordre=ordre, nom_fitxa=nom,
                capa=capa, instancia=instancia,
                tolerancia_minus=(0.5 if ordre % 2 else 2.0),
                tolerancia_plus=(0.5 if ordre % 2 else 2.0),
            )
        return fetes

    def _graduacio(self):
        """Genera els specs. 4 germanes × 5 talles = 20 cel·les, totes distintes."""
        from fhort.pom.services import generate_graded_specs
        return generate_graded_specs(self.sf.pk)

    def _peca(self, bms):
        """Una PieceFitting amb una línia per germana, a talla base. La línia porta els
        eixos de la seva germana: és el que fa que s8/s10 la puguin jutjar amb la seva vara."""
        from fhort.fitting.models import (FittingSession, PieceFitting,
                                          PieceFittingLine)
        from fhort.fitting.services import vigent_grading_version
        sessio = FittingSession.objects.create(
            model=self.model, fase='SizeSet', data=datetime.date(2026, 8, 3), estat='Oberta')
        pf = PieceFitting.objects.create(
            session=sessio, model=self.model,
            grading_version=vigent_grading_version(self.sf.pk))
        for nom, capa, instancia, valor in GERMANES:
            PieceFittingLine.objects.create(
                piece_fitting=pf, pom=bms[nom].pom, size_label=BASE,
                valor_teoric=valor, valor_real=valor + 1.0,
                capa=capa, instancia=instancia)
        return pf

    def _req(self, ruta):
        req = APIRequestFactory().get(ruta)
        force_authenticate(req, user=self.user)
        return req

    @staticmethod
    def _render(resp):
        if hasattr(resp, 'render'):
            resp.render()
        return resp

    def _quatre(self, vistos, que):
        """L'assert que es repeteix: han de sortir LES QUATRE, i cadascuna amb el SEU valor."""
        self.assertEqual(len(vistos), 4,
                         f'{que}: hi ha 4 germanes vives i n\'han sortit {len(vistos)} — '
                         f'les que falten no col·lapsen, s\'AMAGUEN')
        self.assertEqual(set(vistos), BASES,
                         f'{que}: cada fila ha de portar el valor de LA SEVA germana')

    # ── 1 · base_stages (models_app/views.py:3046) ───────────────────────────────────

    def test_01_base_stages_treu_les_quatre_germanes(self):
        from fhort.models_app.views import base_stages_view

        with comportes_alcades(*TAULES):
            self._germanes()

            resp = self._render(base_stages_view(
                self._req(f'/api/models/{self.model.id}/base-stages/'), self.model.id))

            self.assertEqual(resp.status_code, 200)
            files = resp.data['rows']
            self.assertEqual({f['nom_fitxa'] for f in files}, NOMS,
                             'base-stages ha de pintar una fila per germana')
            self._quatre([f['base_value_cm'] for f in files], 'base-stages')

    # ── 2 · graded_spec_views (payload de la FITXA) ──────────────────────────────────

    def test_02_el_payload_de_fitxa_treu_les_quatre_germanes(self):
        from fhort.fitting.graded_spec_views import GradedSpecTableView

        with comportes_alcades(*TAULES):
            bms = self._germanes()
            self._graduacio()

            resp = self._render(GradedSpecTableView.as_view()(
                self._req(f'/api/v1/size-fittings/{self.sf.id}/graded-specs/'),
                sf_id=self.sf.id))

            self.assertEqual(resp.status_code, 200)
            files = resp.data['rows']
            self._quatre([f['valors'].get(BASE) for f in files], 'payload de fitxa')
            self.assertEqual({f['ref'] for f in files}, NOMS,
                             'cada fila ha de portar la nomenclatura de LA SEVA germana, '
                             'no la de la seva parella')
            del bms

    # ── 3 · repas_views ──────────────────────────────────────────────────────────────

    def test_03_el_repas_treu_les_quatre_germanes(self):
        with comportes_alcades(*TAULES):
            bms = self._germanes()
            self._graduacio()
            self._peca(bms)

            from fhort.fitting.repas_views import FittingRepasView
            resp = self._render(FittingRepasView.as_view()(
                self._req(f'/api/v1/models/{self.model.id}/fitting-repas/'),
                model_id=self.model.id))

            self.assertEqual(resp.status_code, 200)
            files = resp.data['rows']
            self.assertEqual({f['nom_fitxa'] for f in files}, NOMS,
                             'el Repàs ha de tenir una fila per germana')
            reals = [list(f['valors'].values())[0]['valor_teoric'] for f in files
                     if f['valors']]
            self._quatre(reals, 'repàs')

    # ── 4 · serializers_size_check ───────────────────────────────────────────────────

    def test_04_el_size_check_treu_les_quatre_germanes(self):
        from fhort.models_app.serializers_size_check import SizeCheckGridSerializer

        with comportes_alcades(*TAULES):
            bms = self._germanes()
            check = SizeCheck.objects.create(model=self.model, talla_base_label=BASE)
            for nom, capa, instancia, valor in GERMANES:
                SizeCheckLine.objects.create(
                    size_check=check, pom=bms[nom].pom,
                    valor_teoric=valor, valor_real=valor + 1.0,
                    capa=capa, instancia=instancia)

            files = SizeCheckGridSerializer(check).data['lines']

            self.assertEqual({f['codi_fitxa'] for f in files}, NOMS,
                             'cada línia ha de dir el codi de fitxa de LA SEVA germana')
            self._quatre([f['valor_teoric'] for f in files], 'size-check')
            # +1.0 sobre ±0.5 és FORA; sobre ±2.0 és DINS. Si una línia hereta la vara de la
            # germana, aquest parell s'inverteix.
            per_nom = {f['codi_fitxa']: f for f in files}
            self.assertTrue(per_nom['A-EXT']['fora_tolerancia'])
            self.assertFalse(per_nom['A-FOL']['fora_tolerancia'])
            self.assertTrue(per_nom['B-ESQ']['fora_tolerancia'])
            self.assertFalse(per_nom['B-DRE']['fora_tolerancia'])

    # ── 5 · pom/s6_views (les seves DUES portes) ─────────────────────────────────────

    def test_05a_s6_mesures_base_amb_unitats_treu_les_quatre(self):
        from fhort.pom.s6_views import base_measurements_with_units_view

        with comportes_alcades(*TAULES):
            self._germanes()

            resp = self._render(base_measurements_with_units_view(
                self._req(f'/api/v1/models/{self.model.id}/base-measurements-units/'),
                self.model.id))

            self.assertEqual(resp.status_code, 200)
            self._quatre([r['base_value_cm'] for r in resp.data['results']], 's6 · base')

    def test_05b_s6_specs_graduats_amb_unitats_treu_les_quatre(self):
        from fhort.pom.s6_views import graded_specs_with_units_view

        with comportes_alcades(*TAULES):
            self._germanes()
            self._graduacio()

            resp = self._render(graded_specs_with_units_view(
                self._req(f'/api/v1/size-fittings/{self.sf.id}/graded-units/'), self.sf.id))

            self.assertEqual(resp.status_code, 200)
            self._quatre([r['values'][BASE]['cm'] for r in resp.data['results']],
                         's6 · graduats')

    # ── 6 · pom/s8_views (CSV de fitting) ────────────────────────────────────────────

    def test_06_el_csv_de_fitting_treu_les_quatre_germanes(self):
        from fhort.pom.s8_views import export_fitting_csv_view

        with comportes_alcades(*TAULES):
            bms = self._germanes()
            self._graduacio()
            pf = self._peca(bms)

            resp = export_fitting_csv_view(
                self._req(f'/api/v1/fittings/peca/{pf.id}/export/csv/'), pf.id)

            self.assertEqual(resp.status_code, 200)
            files = list(csv.reader(io.StringIO(resp.content.decode('utf-8-sig'))))
            dades = [f for f in files if len(f) == 8 and f[2] == BASE]
            self._quatre([float(f[3]) for f in dades], 'CSV de fitting')
            # ±0.5 → FAIL · ±2.0 → PASS. Dues i dues: si una línia hereta la vara de la
            # germana, el repartiment deixa de ser 2-2.
            self.assertEqual(sorted(f[7] for f in dades), ['FAIL', 'FAIL', 'PASS', 'PASS'],
                             'cada línia s\'ha de jutjar amb la tolerància de la SEVA germana')

    # ── 7 · pom/s10_views (fitting vs spec, toleràncies) ─────────────────────────────

    def test_07_el_veredicte_de_toleranciess10_treu_les_quatre_germanes(self):
        from fhort.pom.s10_views import fitting_vs_spec_view

        with comportes_alcades(*TAULES):
            bms = self._germanes()
            self._graduacio()
            pf = self._peca(bms)

            resp = self._render(fitting_vs_spec_view(
                self._req(f'/api/v1/fittings/peca/{pf.id}/vs-spec/'), pf.id))

            self.assertEqual(resp.status_code, 200)
            self._quatre([r['spec_cm'] for r in resp.data['results']], 's10 · vs-spec')
            self.assertEqual(resp.data['resum']['fail'], 2,
                             'dues germanes tenen ±0.5 i +1.0 les treu de tolerància')

    # ── 8 · pom/grading_views (cells) ────────────────────────────────────────────────

    def test_08_les_cells_de_la_taula_de_grading_treuen_les_quatre(self):
        from fhort.pom.grading_views import measurements_table_view as taula_grading

        with comportes_alcades(*TAULES):
            self._germanes()
            self._graduacio()

            resp = self._render(taula_grading(
                self._req(f'/api/v1/size-fittings/{self.sf.id}/taula-mesures/'),
                sf_id=self.sf.id))

            self.assertEqual(resp.status_code, 200)
            self._quatre([c[BASE]['value'] for c in resp.data['cells'].values()],
                         'cells de grading')

    # ── 9 · models_app/views deltes (:1771) ──────────────────────────────────────────

    def test_09_els_deltes_de_la_taula_de_mesures_son_quatre(self):
        """Aquesta superfície NO amaga: pinta les quatre files (el queryset no filtra) i
        després en resumeix els deltes a un dict per `pom_id` sol. És l'altre mode de
        fallada del cens —COL·LAPSA—, i és pitjor de veure que l'absència: la pantalla
        ensenya quatre files i dues d'elles porten el delta de la germana."""
        from fhort.models_app.views import measurements_table_view as taula_mesures

        with comportes_alcades(*TAULES):
            self._germanes()
            self._graduacio()

            resp = self._render(taula_mesures(
                self._req(f'/api/models/{self.model.id}/measurements-table/'), self.model.id))

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(resp.data['rows']), 4, 'les quatre files hi són')
            self.assertEqual(len(resp.data['deltes']), 4,
                             'hi ha 4 germanes i el dict de deltes en té menys: dues '
                             'germanes comparteixen entrada i l\'última llegida guanya')
            self._quatre([r['graded'].get(BASE) for r in resp.data['rows']],
                         'graded de la taula de mesures')

    # ── 10 · patterns/views model-poms (:605) ────────────────────────────────────────

    def test_10_la_llista_del_taller_treu_les_quatre_germanes(self):
        """✅ DESPERTAT AL BLOC 3 (04/08). La contradicció de scope que el tenia saltat l'ha
        resolta l'Agus: **dues cares, dues línies**, i val també per a la llista del taller.

        El que el mantenia saltat eren dues coses que xocaven:

        ① el brief del bloc 1 excloïa patrons («NO: … tocar `PatternPOM`») i alhora llistava
           `model-poms` entre les 10 superfícies. Resolt distingint-les: s'ha desancorat el
           queryset de `BaseMeasurement` a `patterns/views.model_poms` i **`PatternPOM` no
           s'ha tocat** — no té els eixos ni a l'esquema i segueix fora de C4;

        ② un test committat fixava el contrari
           (`test_lectors_instancia_cins::test_la_llista_del_taller_no_repeteix_la_fila_per_germana`,
           que exigia UNA fila). Ha caigut i s'ha reescrit amb la llei nova
           (`…_fa_una_fila_per_germana`): les dues superfícies diuen ara el mateix.

        El que decidia era mesurable i pesava: amb l'àncora viva, un POM mesurat NOMÉS per
        instància (la sisa esquerra i la dreta, sense «la sisa») desapareixia SENCER de la
        llista i el patronista no veia que hi hagués res a mesurar-hi.

        🚩 EL QUE QUEDA OBERT I NO ÉS D'AQUÍ: dues germanes ensenyen els MATEIXOS
        `ancoratges`, perquè `PatternPOM` és `(pattern_piece, pom_master)` i no té els eixos.
        És el sostre dur de F2-patrons (§II.10: el DXF no sobreviu un roundtrip amb
        instància), i tancar-lo és decisió humana + migració.
        """
        from fhort.patterns.models import PatternFile
        from fhort.patterns.views import PatternFileViewSet

        with comportes_alcades(*TAULES):
            self._germanes()
            fp = PatternFile.objects.create(model=self.model, nom_fitxer='c4.dxf')

            vista = PatternFileViewSet.as_view({'get': 'model_poms'})
            resp = self._render(vista(
                self._req(f'/api/v1/patterns/files/{fp.id}/model-poms/'), pk=fp.id))

            self.assertEqual(resp.status_code, 200)
            files = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
            self.assertEqual({f['nom_fitxa'] for f in files}, NOMS,
                             'el taller ha de veure una fila per germana')
            self._quatre([f['valor_fitxa_cm'] for f in files], 'model-poms del taller')

    # ── El rastre: cap ───────────────────────────────────────────────────────────────

    def _comportes_vives(self):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN pg_namespace n ON n.oid = t.relnamespace "
                "WHERE n.nspname = %s AND c.conname LIKE ANY (ARRAY["
                "  '%%_capa_gate_c1', '%%_instancia_gate_cins'])",
                [connection.schema_name])
            return cur.fetchone()[0]

    def test_11_les_comportes_tornen_a_estar_vives(self):
        """Si el savepoint no les tornés, aquest fitxer deixaria la BD de test sense guard i
        la resta de tests de capa passarien per una raó falsa.

        C4/G1 (04/08) — l'assert comptava 18, el nombre de comportes que hi havia abans de
        començar a retirar-les. Comparar amb una xifra fixa vol dir que cada grup retirat
        trenca aquest test i que algú l'ha de tornar a escriure amb el número nou: una xifra
        que s'ha d'anar corregint no vigila res, només fa soroll. El que ha de ser cert és
        que el harness DEIXA L'ESQUEMA COM EL VA TROBAR, i això es diu comptant abans i
        després — val igual amb 18 comportes que amb 12 o amb cap."""
        abans = self._comportes_vives()

        with comportes_alcades(*TAULES):
            self.assertLessEqual(self._comportes_vives(), abans,
                                 'el harness ha d\'haver ALÇAT les que hi hagués')

        self.assertEqual(self._comportes_vives(), abans,
                         'el harness ha deixat una comporta per terra')

    def test_12_la_invariant_del_nom_sobreviu(self):
        """`instancia_exigeix_nom` NO és una comporta del tram: és la regla que fa
        distingible la germana a la pantalla, i ha de SOBREVIURE C4 (diagnosi §4.1).
        Aquest test la vigila DES DE DINS del harness: amb les dues comportes alçades, una
        germana anònima ha de seguir sent impossible."""
        from django.db import IntegrityError

        with comportes_alcades(*TAULES):
            with self.assertRaises(IntegrityError,
                                   msg='una germana sense nom de fitxa no pot existir'):
                with transaction.atomic():
                    BaseMeasurement.objects.create(
                        model=self.model, pom=self.pom_a, base_value_cm=1.0, ordre=9,
                        nom_fitxa='', instancia=ESQUERRA)


class ArtefactesDelBancC4Test(TenantTestCase):
    """El banc s'ha de poder construir SENSE cap germana i donar el de sempre.

    No està saltat: si aquest peta, el vermell dels altres no voldria dir «C4 amaga la
    germana» sinó «el fixture no es té dret». Amb una sola mesura per POM, el motor ha de
    donar exactament la fila de sempre i cap superfície ha de canviar.
    """

    @classmethod
    def setup_tenant(cls, tenant):
        return GermanesALesSuperficiesC4Test.setup_tenant(tenant)

    setUp = GermanesALesSuperficiesC4Test.setUp

    def test_amb_una_sola_mesura_per_pom_el_banc_dona_el_de_sempre(self):
        from fhort.fitting.models import GradedSpec
        from fhort.fitting.services import vigent_grading_version
        from fhort.pom.services import generate_graded_specs

        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_a, base_value_cm=46.0, ordre=1, nom_fitxa='A-EXT')

        n = generate_graded_specs(self.sf.pk)

        self.assertEqual(n, 5, '1 mesura × 5 talles = 5 cel·les')
        gv = vigent_grading_version(self.sf.pk)
        valors = {s.size_label: s.graded_value_cm
                  for s in GradedSpec.objects.filter(grading_version=gv, is_active=True)}
        self.assertEqual(valors, {'XXS': 44.0, 'XS': 45.0, 'S': 46.0, 'M': 47.0, 'L': 48.0})

    def test_el_signal_estampa_els_eixos_al_changelog(self):
        """La cadena G1 (mesura → signal → changelog) ha de portar els eixos: si això no
        fos cert, el vermell de `base-stages` seria del signal i no del lector."""
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_a, base_value_cm=46.0, ordre=1, nom_fitxa='A-EXT')

        logs = list(MeasurementChangeLog.objects.filter(model=self.model))

        self.assertTrue(logs, 'el signal F1 ha d\'haver escrit el rastre de l\'alta')
        self.assertEqual({(l.capa, l.instancia) for l in logs}, {(EXTERIOR, '')})
