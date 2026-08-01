"""Onada 1 — HARNESS DE DUES CAPES: els lectors adaptats no col·lapsen.

Els tests de C1 (`test_capa_comporta_c1`) proven que la comporta BARRA la segona capa. Aquest
fitxer prova el contrari i és l'única manera de fer-ho mentre la comporta hi és: **l'alça per
a UNA taula, dins d'un savepoint que sempre es desfà**, escriu una fila `folre` al costat de
la seva `exterior`, i verifica que el lector les distingeix.

Sense això, els commits d'aquesta onada són inverificables per construcció: amb la comporta
tancada totes les files són 'exterior', tots els lectors donen el mateix resultat abans i
després, i el fumeig byte-idèntic —que és el green flag de no-regressió— no diu absolutament
res sobre si la capa s'ha entès bé. Prova el que el fumeig NO pot provar.

DDL transaccional: a Postgres un `ALTER TABLE … DROP CONSTRAINT` es desfà amb el savepoint,
igual que un INSERT. El test no deixa rastre, i `test_la_comporta_torna_a_estar_viva` ho
verifica al final llegint el catàleg de Postgres.

Quan C4 retiri les comportes, el `with comporta_alcada(...)` sobra i els asserts es queden.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import (BaseMeasurement, Model, SizeCheck,
                                     SizeCheckLine)
from fhort.pom.models import POMMaster

FOLRE = 'folre'
EXTERIOR = 'exterior'


@contextlib.contextmanager
def comporta_alcada(*taules):
    """Alça les comportes `*_capa_gate_c1` de `taules` dins d'un savepoint que SEMPRE es desfà.

    El `finally` no és decoratiu: si un assert peta a dins, la comporta ha de tornar igual.
    """
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                cur.execute(
                    f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                    f'DROP CONSTRAINT "{taula}_capa_gate_c1"'
                )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class LectorsCapaOnada1Test(TenantTestCase):

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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-O1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        # `get_or_create` i no `create`: l'usuari d'auth viu al schema COMPARTIT i sobreviu al
        # rollback de cada test, mentre que el que hi ha al tenant no. Crear-lo a seques
        # petava al segon test amb una unicitat que no té res a veure amb el que es prova.
        from fhort.accounts.models import UserProfile
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_onada1', defaults={'email': 'qa@onada1.test'})
        # `SizeFitting.creat_per`/`GradingVersion.creat_per` apunten a `accounts.UserProfile`,
        # no a l'usuari d'auth.
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA Onada 1', 'rol_nom': 'QA'})

    def _dues_capes_de_base(self):
        """La mateixa mesura del mateix POM a dues capes, amb toleràncies BEN distintes.

        Els números són a posta lluny l'un de l'altre: si un lector col·lapsa, l'assert no
        falla per un decimal sinó per un ordre de magnitud.
        """
        ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
            tolerancia_minus=0.5, tolerancia_plus=0.5, nom_fitxa='A-EXT')
        fol = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=98.0, ordre=2,
            tolerancia_minus=2.0, tolerancia_plus=2.0, nom_fitxa='A-FOL', capa=FOLRE)
        return ext, fol

    # ── C1 · les toleràncies de `pom` ────────────────────────────────────────────────

    def test_c1_el_mapa_de_tolerancies_no_col·lapsa_les_dues_capes(self):
        """`_tolerance_map` per POM sol es quedava amb l'última capa llegida i jutjava tota
        la família amb la seva vara.

        FASE_2/C1-ins — la clau del mapa és ara `(pom, capa, instancia)`. Aquest test segueix
        provant EXACTAMENT el mateix (que les dues capes no es col·lapsen); només parla la
        clau nova. La instància té el seu propi harness a `test_lectors_instancia_cins`.
        """
        from fhort.pom.s10_views import _tolerance_map

        with comporta_alcada('models_app_basemeasurement',
                             'models_app_measurementchangelog'):
            self._dues_capes_de_base()
            tol = _tolerance_map(self.model)

            self.assertEqual(len(tol), 2, 'les dues capes han de tenir entrada pròpia')
            self.assertEqual(tol[(self.pom.id, EXTERIOR, '')], (0.5, 0.5))
            self.assertEqual(tol[(self.pom.id, FOLRE, '')], (2.0, 2.0))

    # ── C5 · el serializer de Size Check ─────────────────────────────────────────────

    def test_c5_cada_linia_de_check_es_jutja_amb_la_tolerancia_de_la_seva_capa(self):
        """El veredicte fora/dins de tolerància és el producte d'aquesta vista. Amb el mapa
        per POM sol, la línia de folre el rebia amb la vara de l'exterior."""
        from fhort.models_app.serializers_size_check import SizeCheckGridSerializer

        with comporta_alcada('models_app_basemeasurement',
                             'models_app_measurementchangelog',
                             'models_app_sizecheckline'):
            self._dues_capes_de_base()
            check = SizeCheck.objects.create(model=self.model, talla_base_label='M')
            # Mateixa desviació (+1.0) a totes dues: dins de la tolerància del folre (±2.0),
            # FORA de la de l'exterior (±0.5). Si el lector col·lapsa, les dues coincideixen.
            SizeCheckLine.objects.create(size_check=check, pom=self.pom,
                                         valor_teoric=100.0, valor_real=101.0)
            SizeCheckLine.objects.create(size_check=check, pom=self.pom, capa=FOLRE,
                                         valor_teoric=98.0, valor_real=99.0)

            files = SizeCheckGridSerializer(check).data['lines']
            self.assertEqual(len(files), 2)
            per_codi = {f['codi_fitxa']: f for f in files}

            self.assertEqual(set(per_codi), {'A-EXT', 'A-FOL'},
                             'cada línia ha de portar el codi de fitxa de la SEVA capa')
            self.assertTrue(per_codi['A-EXT']['fora_tolerancia'],
                            '+1.0 sobre ±0.5 és fora: la línia d\'exterior ho ha de dir')
            self.assertFalse(per_codi['A-FOL']['fora_tolerancia'],
                             '+1.0 sobre ±2.0 és dins: la línia de folre no és fora')
            self.assertEqual(per_codi['A-EXT']['tol_plus'], 0.5)
            self.assertEqual(per_codi['A-FOL']['tol_plus'], 2.0)

    # ── C8 · la sembra de valors STEP ────────────────────────────────────────────────

    def _escala(self):
        """SizeSystem mínim perquè `escala_del_model` tingui geometria (llei S24b)."""
        from fhort.pom.models import SizeDefinition, SizeSystem
        ss = SizeSystem.objects.create(codi='TST-SS', nom='Test')
        for i, etiqueta in enumerate(['S', 'M', 'L'], start=1):
            SizeDefinition.objects.create(size_system=ss, etiqueta=etiqueta, ordre=i)
        self.model.size_system = ss
        self.model.save(update_fields=['size_system'])
        return ss

    def test_c8_la_sembra_step_llegeix_una_capa_i_no_la_barreja(self):
        """La clau del dict de `_sembra_step_des_dels_specs` és la TALLA, no el POM: sense
        àncora, cada talla la resolia l'últim spec llegit i la regla naixia amb valors de
        capes diferents barrejats."""
        from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
        from fhort.models_app.views import _sembra_step_des_dels_specs

        self._escala()
        sf = SizeFitting.objects.create(model=self.model, numero=1, codi='TST-SF1',
                                        tipus='PROTO', creat_per=self.perfil)
        gv = GradingVersion.objects.create(size_fitting=sf, is_active=True, version_number=1,
                                           creat_per=self.perfil)

        with comporta_alcada('fitting_gradedspec'):
            # Exterior: passos de 2 a banda i banda de la base (M).
            for talla, val in [('S', 98.0), ('M', 100.0), ('L', 102.0)]:
                GradedSpec.objects.create(grading_version=gv, pom=self.pom, size_label=talla,
                                          graded_value_cm=val, grading_type_applied='LINEAR')
            # Folre: mateix POM i mateixes talles, amb una escala DELIBERADAMENT distinta
            # (passos de 5 i 15). Si tinguessin el mateix pas, el test no distingiria res
            # encara que el lector col·lapsés.
            for talla, val in [('S', 5.0), ('M', 10.0), ('L', 25.0)]:
                GradedSpec.objects.create(grading_version=gv, pom=self.pom, size_label=talla,
                                          graded_value_cm=val, grading_type_applied='LINEAR',
                                          capa=FOLRE)

            valors = _sembra_step_des_dels_specs(self.model, self.pom.id)

            # `sembra_valors_step` retorna DELTES (increment respecte del veí cap a la base),
            # no absoluts: exterior → 2.0 a banda i banda; folre → 5.0 i 15.0.
            self.assertTrue(valors, 'la sembra hauria de retornar valors amb geometria vàlida')
            self.assertEqual(float(valors['S']), 2.0, 'S ve de l\'exterior, no del folre')
            self.assertEqual(float(valors['L']), 2.0, 'L ve de l\'exterior, no del folre')
            self.assertNotIn(15.0, {float(v) for v in valors.values()},
                             'un delta del folre s\'ha colat a la sembra de la regla')

    # ── C7 · la taula de mesures, per les seves DUES portes ──────────────────────────

    def _size_fitting(self, amb_graduacio):
        from fhort.fitting.models import GradingVersion, SizeFitting
        # `numero=2`: el model ja neix amb el seu primer SizeFitting.
        sf = SizeFitting.objects.create(model=self.model, numero=2, codi='TST-SF-C7',
                                        tipus='PROTO', creat_per=self.perfil)
        if not amb_graduacio:
            return sf, None
        gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                           version_number=1, creat_per=self.perfil)
        return sf, gv

    def _taula(self, sf):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from fhort.pom.grading_views import measurements_table_view

        req = APIRequestFactory().get(f'/api/v1/size-fittings/{sf.id}/taula-mesures/')
        force_authenticate(req, user=self.user)
        resp = measurements_table_view(req, sf_id=sf.id)
        if hasattr(resp, 'render'):
            resp.render()
        return resp

    def test_c7_la_taula_de_mesures_no_barreja_les_capes_per_cap_de_les_dues_portes(self):
        """`cells` i `poms_seen` s'omplen per dos camins excloents —specs graduats si el
        model té graduació, mesures base si no— i tots dos escriuen als MATEIXOS
        diccionaris, indexats per POM sol. Amb dues capes, la cel·la se la quedava la
        darrera fila llegida: una taula mig d'una capa i mig de l'altra segons la porta."""
        from fhort.fitting.models import GradedSpec

        # Porta 1 · mesures base, sense graduació.
        with comporta_alcada('models_app_basemeasurement',
                             'models_app_measurementchangelog'):
            self._dues_capes_de_base()          # exterior 100.0 · folre 98.0
            sf, _ = self._size_fitting(amb_graduacio=False)

            resp = self._taula(sf)

            self.assertEqual(resp.status_code, 200)
            cella = resp.data['cells'][str(self.pom.id)]['M']
            self.assertEqual(cella['value'], 100.0,
                             "la taula ha de dir el valor de l'exterior, no el del folre")

        # Porta 2 · specs graduats.
        with comporta_alcada('fitting_gradedspec'):
            sf2, gv = self._size_fitting(amb_graduacio=True)
            GradedSpec.objects.create(grading_version=gv, pom=self.pom, size_label='M',
                                      graded_value_cm=100.0, grading_type_applied='LINEAR')
            GradedSpec.objects.create(grading_version=gv, pom=self.pom, size_label='M',
                                      graded_value_cm=7.0, grading_type_applied='LINEAR',
                                      capa=FOLRE)

            resp = self._taula(sf2)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data['cells'][str(self.pom.id)]['M']['value'], 100.0,
                             'un valor graduat de folre s\'ha colat a la taula')

    # ── C9 · el node del pin: el carry-forward dels estadis ──────────────────────────

    def test_c9_un_estadi_de_folre_no_arrossega_valor_a_la_fila_de_l_exterior(self):
        """Els estadis són SNAPSHOTS per carry-forward. Per POM sol, una presa de folre
        s'arrossegava cap endavant per la fila de l'exterior: una base que aquella capa no
        ha tingut mai (mateix símptoma que FIX-2 va tancar per l'altra porta)."""
        from rest_framework.test import APIRequestFactory, force_authenticate

        from fhort.models_app.models import MeasurementChangeLog
        from fhort.models_app.views import base_stages_view

        with comporta_alcada('models_app_basemeasurement',
                             'models_app_measurementchangelog'):
            ext, fol = self._dues_capes_de_base()
            # Una presa per capa, amb valors inconfusibles i el mateix context/segon.
            for bm, valor in [(ext, 100.0), (fol, 7.0)]:
                MeasurementChangeLog.objects.create(
                    model=self.model, pom=self.pom, base_measurement=bm, capa=bm.capa,
                    context='FITTING', valor_anterior=1.0, valor_nou=valor)

            req = APIRequestFactory().get(f'/api/models/{self.model.id}/base-stages/')
            force_authenticate(req, user=self.user)
            resp = base_stages_view(req, self.model.id)
            resp.render() if hasattr(resp, 'render') else None

            self.assertEqual(resp.status_code, 200)
            files = {f['nom_fitxa']: f for f in resp.data['rows']}
            self.assertEqual(set(files), {'A-EXT', 'A-FOL'})

            # ✅ FASE_3 · L'ASSERT ESTRET. Abans això era un `assertNotIn` amb una nota que
            # deia «quan l'Onada 2 passi, aquesta igualtat es pot estrènyer a {100.0}».
            # L'Onada 2 ha passat: el signal de F1 ja estampa `capa` i `instancia` de la
            # `BaseMeasurement` que ha canviat, i la fila d'exterior ja NOMÉS veu el seu.
            #
            # La fila de folre en veu DOS, i els dos són seus: l'alta (98.0, que el signal
            # registra en néixer la mesura i que abans queia a l'exterior) i la presa
            # explícita (7.0). Que el 98.0 hagi APAREGUT aquí és, precisament, la prova que
            # el forat s'ha tancat: fins avui vivia a la fila de l'altra capa.
            self.assertEqual(set(files['A-EXT']['takes'].values()), {100.0},
                             'la fila d\'exterior ha de veure NOMÉS les seves preses')
            self.assertEqual(set(files['A-FOL']['takes'].values()), {98.0, 7.0},
                             'la fila de folre ha de veure la seva alta i la seva presa')

    # ── El rastre: cap ───────────────────────────────────────────────────────────────

    def test_la_comporta_torna_a_estar_viva(self):
        """El harness alça comportes: si el savepoint no les tornés, aquest fitxer deixaria
        la BD de test sense guard i els altres tests de capa passarien per una raó falsa."""
        with comporta_alcada('models_app_basemeasurement'):
            pass

        with connection.cursor() as cur:
            cur.execute(
                "SELECT conname FROM pg_constraint c "
                "JOIN pg_namespace n ON n.oid = c.connamespace "
                "WHERE n.nspname = %s AND c.contype = 'c' AND c.conname LIKE %s",
                [connection.schema_name, '%_capa_gate_c1'])
            self.assertEqual(len(cur.fetchall()), 9,
                             'el harness ha deixat una comporta per terra')
