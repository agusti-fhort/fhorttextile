"""FASE_2 — HARNESS DE FILES GERMANES v2: els lectors distingeixen els DOS eixos.

`test_capa_comporta_c1` i `test_instancia_comporta_cins` proven que les comportes BARREN.
`test_lectors_capa_onada1` prova que els lectors distingeixen dues CAPES. Aquest fitxer prova
el que faltava, i que no es dedueix de cap dels altres tres: que amb **tres files germanes
del mateix POM** —l'exterior de la instància única, un folre, i una segona instància de
l'exterior— cap lector adaptat a FASE_2 no en col·lapsa ni en barreja cap parell.

Per què v2 i no un cas més al fitxer d'Onada 1: perquè el mode de fallada que persegueix és
DIFERENT. Un lector que hagués crescut a `(pom, capa)` i s'hagués quedat allà passa TOTS els
tests d'Onada 1 i col·lapsa igualment les dues instàncies de l'exterior. La tercera fila és
la que ho detecta, i per això hi és a tots els casos.

Alça LES DUES comportes de cada taula, dins d'un savepoint que sempre es desfà. DDL
transaccional: a Postgres un `ALTER TABLE … DROP CONSTRAINT` es desfà amb el savepoint igual
que un INSERT — el test no deixa rastre, i l'últim cas ho verifica llegint el catàleg.

C4/G1-G4 (04/08) JA les ha retirades: el `with comportes_alcades(...)` és un no-op i els asserts es
queden.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import (BaseMeasurement, Model, SizeCheck,
                                     SizeCheckLine)
from fhort.pom.models import POMMaster

EXTERIOR = 'exterior'
FOLRE = 'folre'
#: La segona instància. Slug compost, com el que la UI compondrà a C4-ins.
LEFT = 'left'


@contextlib.contextmanager
def comportes_alcades(*taules):
    """Alça les DUES comportes (`_capa_gate_c1` i `_instancia_gate_cins`) de cada taula.

    Germà de `comporta_alcada()` d'Onada 1, que només n'alçava una. El `finally` no és
    decoratiu: si un assert peta a dins, les comportes han de tornar totes.
    """
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                for sufix in ('capa_gate_c1', 'instancia_gate_cins'):
                    # `IF EXISTS` — C4/G1-G4 (04/08) han retirat les 40 comportes: alçar-ne
                    # una que ja no hi és és el mateix estat, i el `finally` retorna igual.
                    cur.execute(
                        f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                        f'DROP CONSTRAINT IF EXISTS "{taula}_{sufix}"'
                    )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class LectorsInstanciaCinsTest(TenantTestCase):

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
        from django.contrib.auth import get_user_model

        from fhort.accounts.models import UserProfile
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-F2', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        # `get_or_create` i no `create`: l'usuari d'auth viu al schema COMPARTIT i sobreviu
        # al rollback de cada test (mateixa raó que a `test_lectors_capa_onada1`).
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_cins', defaults={'email': 'qa@cins.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA C1-ins', 'rol_nom': 'QA'})

    # ── Les tres files germanes ──────────────────────────────────────────────────────

    def _tres_germanes(self):
        """Exterior/'' · folre/'' · exterior/'left', amb toleràncies d'ordres de magnitud.

        Els números són a posta lluny els uns dels altres: si un lector col·lapsa, l'assert
        no falla per un decimal sinó per un ordre de magnitud. I els `nom_fitxa` són
        distints perquè la instància els EXIGEIX (CHECK `..._instancia_exigeix_nom`) — i
        perquè el nom de fitxa és, precisament, el que un humà faria servir per distingir-les.
        """
        ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
            tolerancia_minus=0.5, tolerancia_plus=0.5, nom_fitxa='A-EXT')
        fol = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=98.0, ordre=2,
            tolerancia_minus=2.0, tolerancia_plus=2.0, nom_fitxa='A-FOL', capa=FOLRE)
        esq = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=40.0, ordre=3,
            tolerancia_minus=9.0, tolerancia_plus=9.0, nom_fitxa='A-ESQ', instancia=LEFT)
        return ext, fol, esq

    # ── El mapa de toleràncies (s10 · s8) ────────────────────────────────────────────

    def test_el_mapa_de_tolerancies_te_una_entrada_per_germana(self):
        """`_tolerance_map` amb clau `(pom, capa)` es quedava amb l'última INSTÀNCIA llegida
        i jutjava la sisa dreta amb la tolerància de l'esquerra. Tres files, tres entrades."""
        from fhort.pom.s10_views import _tolerance_map

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            self._tres_germanes()
            tol = _tolerance_map(self.model)

            self.assertEqual(len(tol), 3, 'cada germana ha de tenir entrada pròpia')
            # SET-2/T6a (2026-08-11) — LA CLAU DEL MAPA TÉ UN TRAM MÉS: el `garment`. Pin
            # de FORMA i era el seu ofici caure avui — les toleràncies no s'han mogut
            # (0.5/2.0/9.0, les mateixes germanes), només la clau. Segueix exigint una
            # entrada PRÒPIA per germana, que és el que aquest test defensa.
            self.assertEqual(tol[(self.pom.id, EXTERIOR, '', '')], (0.5, 0.5))
            self.assertEqual(tol[(self.pom.id, FOLRE, '', '')], (2.0, 2.0))
            self.assertEqual(tol[(self.pom.id, EXTERIOR, LEFT, '')], (9.0, 9.0))

    # ── El serializer de Size Check ──────────────────────────────────────────────────

    def test_cada_linia_de_check_es_jutja_amb_la_tolerancia_de_la_SEVA_germana(self):
        """El veredicte fora/dins de tolerància és el producte d'aquesta vista. Amb la clau
        de dos trams, la línia de la instància el rebia amb la vara de l'exterior."""
        from fhort.models_app.serializers_size_check import SizeCheckGridSerializer

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog',
                               'models_app_sizecheckline'):
            self._tres_germanes()
            check = SizeCheck.objects.create(model=self.model, talla_base_label='M')
            # Mateixa desviació (+1.0) a totes tres: FORA de ±0.5 (exterior), dins de ±2.0
            # (folre) i dins de ±9.0 (instància). Si un lector col·lapsa, dues coincideixen.
            SizeCheckLine.objects.create(size_check=check, pom=self.pom,
                                         valor_teoric=100.0, valor_real=101.0)
            SizeCheckLine.objects.create(size_check=check, pom=self.pom, capa=FOLRE,
                                         valor_teoric=98.0, valor_real=99.0)
            SizeCheckLine.objects.create(size_check=check, pom=self.pom, instancia=LEFT,
                                         valor_teoric=40.0, valor_real=41.0)

            files = SizeCheckGridSerializer(check).data['lines']
            self.assertEqual(len(files), 3)
            per_codi = {f['codi_fitxa']: f for f in files}

            self.assertEqual(set(per_codi), {'A-EXT', 'A-FOL', 'A-ESQ'},
                             'cada línia ha de portar el codi de fitxa de la SEVA germana')
            self.assertTrue(per_codi['A-EXT']['fora_tolerancia'],
                            '+1.0 sobre ±0.5 és fora: la línia d\'exterior ho ha de dir')
            self.assertFalse(per_codi['A-FOL']['fora_tolerancia'])
            self.assertFalse(per_codi['A-ESQ']['fora_tolerancia'],
                             '+1.0 sobre ±9.0 és dins: la instància no és fora')
            self.assertEqual(per_codi['A-EXT']['tol_plus'], 0.5)
            self.assertEqual(per_codi['A-FOL']['tol_plus'], 2.0)
            self.assertEqual(per_codi['A-ESQ']['tol_plus'], 9.0)

    # ── El node del pin: el carry-forward dels estadis ───────────────────────────────

    def test_un_estadi_dactivitat_no_salta_dentre_germanes(self):
        """Els estadis són SNAPSHOTS per carry-forward. Amb la clau de dos trams, una presa
        sobre la sisa esquerra s'arrossegava cap endavant per la fila de la dreta: una base
        que aquella instància no ha tingut mai."""
        from rest_framework.test import APIRequestFactory, force_authenticate

        from fhort.models_app.models import MeasurementChangeLog
        from fhort.models_app.views import base_stages_view

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            ext, fol, esq = self._tres_germanes()
            # Una presa per germana, amb valors inconfusibles i el mateix context/segon.
            for bm, valor in [(ext, 100.0), (fol, 7.0), (esq, 40.0)]:
                MeasurementChangeLog.objects.create(
                    model=self.model, pom=self.pom, base_measurement=bm,
                    capa=bm.capa, instancia=bm.instancia,
                    context='FITTING', valor_anterior=1.0, valor_nou=valor)

            req = APIRequestFactory().get(f'/api/models/{self.model.id}/base-stages/')
            force_authenticate(req, user=self.user)
            resp = base_stages_view(req, self.model.id)
            resp.render() if hasattr(resp, 'render') else None

            self.assertEqual(resp.status_code, 200)
            files = {f['nom_fitxa']: f for f in resp.data['rows']}
            self.assertEqual(set(files), {'A-EXT', 'A-FOL', 'A-ESQ'})

            # Cada germana veu les SEVES preses i no les de les altres dues. Les files de
            # folre i d'exterior/'' en veuen una de sola perquè l'alta i la presa coincideixen
            # en valor; la de folre en veu dues (l'alta 98.0 i la presa 7.0).
            self.assertEqual(set(files['A-FOL']['takes'].values()), {98.0, 7.0})
            self.assertEqual(set(files['A-ESQ']['takes'].values()), {40.0})
            vals_ext = set(files['A-EXT']['takes'].values())

            # ✅ FASE_3 · L'ASSERT ESTRET. Aquí hi havia un tripwire —`assertNotEqual`— que
            # deia: la fila d'exterior encara veu valors que no són seus, i NO hi arriben per
            # cap lector sinó pel signal F1, que escrivia `MeasurementChangeLog` sense
            # estampar cap dels dos eixos i deixava caure les tres altes a `(pom, exterior,
            # '')`. El signal ja els estampa, i la fila només veu el seu.
            self.assertEqual(vals_ext, {100.0},
                             'la fila d\'exterior ha de veure NOMÉS la seva presa')

    # ── Els lectors DESANCORATS (C4): les tres germanes, cadascuna amb la seva ───────

    def test_els_lectors_serveixen_les_tres_germanes_amb_els_seus_eixos(self):
        """C4 — LA CARA B DE FASE_2 CAU, I CAU PERQUÈ TOCA.

        Aquest test es deia `test_els_lectors_ancorats_serveixen_nomes_la_instancia_unica` i
        exigia el contrari del que exigeix ara: amb tres germanes vives, que el lector en
        servís UNA. El seu propi docstring deia per què i fins quan — «els lectors que no
        poden portar la clau completa —el seu payload s'indexa per `pom_id` i **és contracte
        fins a C4-ins**— s'ancoren als DOS eixos».

        Això és C4. El payload de `base_measurements_with_units_view` ja porta `capa` i
        `instancia` a cada element, o sigui que la premissa d'aquell test —«no poden portar la
        clau completa»— ja no és certa, i l'àncora que en sortia hauria passat de contenció a
        pèrdua: tres mesures reals de la fitxa, dues de les quals no arribarien mai a la
        pantalla.

        El que NO s'afluixa és el motiu pel qual l'àncora existia: que el consumidor no en
        perdi cap en silenci. Abans es garantia servint-ne una de sola; ara es garanteix
        servint-les totes tres i exigint que **cada element digui quina és** — que és
        estrictament més fort, perquè un col·lapse tornaria a donar `count` < 3 i aquest
        assert cauria.
        """
        from rest_framework.test import APIRequestFactory, force_authenticate

        from fhort.pom.s6_views import base_measurements_with_units_view

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            self._tres_germanes()

            req = APIRequestFactory().get(
                f'/api/v1/models/{self.model.id}/base-measurements-units/')
            force_authenticate(req, user=self.user)
            resp = base_measurements_with_units_view(req, model_id=self.model.id)
            resp.render() if hasattr(resp, 'render') else None

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data['count'], 3,
                             'les tres germanes són mesures reals de la fitxa: hi han de ser')
            per_eixos = {(r['capa'], r['instancia']): r['base_value_cm']
                         for r in resp.data['results']}
            self.assertEqual(per_eixos, {
                (EXTERIOR, ''): 100.0,
                (FOLRE, ''): 98.0,
                (EXTERIOR, LEFT): 40.0,
            }, 'cada element ha de portar el valor de LA SEVA germana i dir quina és')

    def test_la_llista_del_taller_fa_una_fila_per_germana(self):
        """C4 — DUES CARES, DUES LÍNIES (decisió d'Agus, 04/08). Aquest test es deia
        `test_la_llista_del_taller_no_repeteix_la_fila_per_germana` i exigia el contrari.

        L'àncora que fixava («el taller veuria tres files repetint el MATEIX conjunt
        d'ancoratges i res que digués quina fila és quina») tenia dues meitats i només se'n
        sosté una. La que cau: ara cada fila SÍ que diu quina és, perquè el payload en porta
        `capa` i `instancia`. La que queda —que les germanes comparteixen ancoratges, perquè
        `PatternPOM` és `(pattern_piece, pom_master)` i no té els eixos— és real, però costa
        menys que el que l'àncora cobrava: un POM mesurat NOMÉS per instància desapareixia
        SENCER de la llista, i el patronista no veia que hi hagués res a mesurar-hi.

        El que NO s'afluixa és el motiu de l'àncora: que el taller no perdi cap mesura en
        silenci. Abans es garantia servint-ne una de sola; ara, servint-les totes tres i
        exigint que cada fila digui de qui és — que és estrictament més fort, perquè un
        col·lapse tornaria a donar `total` < 3 i aquests asserts cauríen.

        `PatternPOM` segueix sense tocar-se: aquest test no li demana res.
        """
        from rest_framework.test import APIRequestFactory, force_authenticate

        from fhort.patterns.models import PatternFile
        from fhort.patterns.views import PatternFileViewSet

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            self._tres_germanes()
            fp = PatternFile.objects.create(model=self.model, nom_fitxer='TST-PAT.dxf')

            vista = PatternFileViewSet.as_view({'get': 'model_poms'})
            req = APIRequestFactory().get(f'/api/patterns/files/{fp.id}/model-poms/')
            force_authenticate(req, user=self.user)
            resp = vista(req, pk=fp.id)
            if hasattr(resp, 'render'):
                resp.render()

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data['total'], 3,
                             'les tres germanes són feina real del taller: hi han de ser')

            per_eixos = {(f['capa'], f['instancia']): f for f in resp.data['results']}
            self.assertEqual(set(per_eixos), {(EXTERIOR, ''), (FOLRE, ''), (EXTERIOR, LEFT)},
                             'cada fila ha de dir de quina capa i de quina instància és')
            self.assertEqual(per_eixos[(EXTERIOR, '')]['nom_fitxa'], 'A-EXT')
            self.assertEqual(per_eixos[(FOLRE, '')]['nom_fitxa'], 'A-FOL')
            self.assertEqual(per_eixos[(EXTERIOR, LEFT)]['nom_fitxa'], 'A-ESQ')
            self.assertEqual(
                {k: float(f['valor_fitxa_cm']) for k, f in per_eixos.items()},
                {(EXTERIOR, ''): 100.0, (FOLRE, ''): 98.0, (EXTERIOR, LEFT): 40.0},
                'cada fila ha de portar el valor de LA SEVA germana')

            # L'àncora forta de cada fila segueix sent la PK de la mesura, que és per on el
            # front hi indexa (`ModelPomList`, `key={f.base_measurement}`).
            self.assertEqual(len({f['base_measurement'] for f in resp.data['results']}), 3)

    def test_el_patrimoni_que_viatja_no_emet_dues_claus_iguals(self):
        """El forat #2. `_llegeix_patrimoni` emet cada mesura amb `_clau_natural_pom`, que no
        porta cap dels dos eixos: sense àncora, tres mesures emetrien TRES entrades amb la
        MATEIXA clau, el destí en desaria una i les altres desapareixerien sense que cap de
        les dues cases se n'assabentés."""
        from fhort.tenants.federation_service import _llegeix_patrimoni

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            self._tres_germanes()
            patrimoni = _llegeix_patrimoni(self.model)

            mesures = patrimoni['mesures']
            self.assertEqual(len(mesures), 1)
            self.assertEqual(mesures[0]['nom_fitxa'], 'A-EXT')
            self.assertEqual(len({m['clau'] for m in mesures}), len(mesures),
                             'dues mesures no poden viatjar amb la mateixa clau natural')

    # ── El rastre: cap ───────────────────────────────────────────────────────────────

    def test_el_harness_no_deixa_rastre(self):
        """Deia «les dues comportes tornen a estar vives» i en comptava nou de cada família.
        C4/G1-G4 les han retirades totes; el que segueix fent falta és que el harness deixi
        l'esquema EXACTAMENT com el va trobar, o la resta del fitxer passaria per una raó
        falsa. Pel NOM i no per recompte: els dos nous són la xifra que va quedar ranci."""
        def noms_de_check():
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT conname FROM pg_constraint c "
                    "JOIN pg_namespace n ON n.oid = c.connamespace "
                    "WHERE n.nspname = %s AND c.contype = 'c'",
                    [connection.schema_name])
                return {row[0] for row in cur.fetchall()}

        abans = noms_de_check()
        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            pass

        self.assertEqual(noms_de_check(), abans, 'el harness ha canviat l\'esquema')
        self.assertEqual(
            {c for c in abans if c.endswith(('_capa_gate_c1', '_instancia_gate_cins'))},
            set(), 'una comporta ha sobreviscut a C4')
