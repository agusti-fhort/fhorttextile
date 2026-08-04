"""C1-ins — LA COMPORTA D'INSTÀNCIA: cap escriptor pot crear una segona instància abans de C4-ins.

Germà exacte de `test_capa_comporta_c1`, amb l'eix canviat. C1-ins ensenya al sistema el
segon idioma —el que distingeix la sisa DRETA de l'ESQUERRA, el pit RELAXED de l'EXTENDED—
però no el deixa parlar-lo: la cadena de lectors encara indexa per `pom_id` (o, com a molt,
per `(pom_id, capa)`) i no s'adapta fins a FASE_2/FASE_3. Sense comporta, una segona
instància escrita per accident en aquesta finestra no petaria enlloc: es fondria dins les
llistes com la primera i corrompria en silenci mesures que són el producte.

El guard viu a la BD i no a l'aplicació pel mateix motiu que el de capa: és l'únic lloc que un
`bulk_create`, un `update()`, un loader de paquet o un `psql` a mà no poden esquivar.

Aquest fitxer verifica TRES coses que no es proven soles:
  1. que la comporta barra, pel camí que de debò importa (l'`IntegrityError` de Postgres);
  2. que les NOU comportes hi són totes —una que faltés seria un forat silenciós—, i que
     `ModelGradingRule` segueix sense la columna (decisió Montse: «gradúen igual»);
  3. que el CHECK «instància ⇒ nom de fitxa» (decisió D1) rebutja de debò. Aquest tercer no
     es pot provar amb la comporta tancada —la comporta ja barra qualsevol instància abans
     que el CHECK hi arribi—, o sigui que s'alça la comporta DINS D'UN SAVEPOINT que sempre
     es desfà, calcant `comporta_alcada()` de `test_lectors_capa_onada1`.

⚠️ NO toca `test_capa_comporta_c1`: el seu pin de nou noms segueix vàlid tal qual, perquè
censa amb `LIKE '%_capa_gate_c1'` i les comportes noves tenen nom propi
(`*_instancia_gate_cins`). Les dues famílies conviuen sense trepitjar-se.

C4-ins retira les nou comportes per migració. El CHECK «instància ⇒ nom», en canvi, NO és
bastida: és llei de domini i sobreviu — quan aquell sprint passi, d'aquest fitxer se'n va
tot menys `ComportaInstanciaExigeixNomTest`.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.db import IntegrityError, connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import (BaseMeasurement, Model, SizeCheck,
                                     SizeCheckLine)
from fhort.pom.models import POMMaster

#: Les nou comportes de C1-ins, una per taula de `0073`/`0020`/`0056`.
#: `models_app_modelgradingrule` i `pom_gradingrule` NO hi són: la regla de graduació no
#: travessa cap dels dos eixos (decisió Montse, «la sisa dreta i l'esquerra gradúen igual»).
COMPORTES = [
    'models_app_basemeasurement_instancia_gate_cins',
    'models_app_measurementchangelog_instancia_gate_cins',
    'models_app_modelgradingoverride_instancia_gate_cins',
    'models_app_pomplacement_instancia_gate_cins',
    'models_app_sizecheckline_instancia_gate_cins',
    'fitting_gradedspec_instancia_gate_cins',
    'fitting_piecefittingline_instancia_gate_cins',
    'pom_garmentpommap_instancia_gate_cins',
    'pom_itembasemeasurement_instancia_gate_cins',
]

#: L'instància de prova. Slug compost, com el que la UI compondrà a C4-ins.
LEFT = 'left-relaxed'


@contextlib.contextmanager
def comporta_instancia_alcada(*taules):
    """Alça les comportes `*_instancia_gate_cins` de `taules` dins d'un savepoint que SEMPRE es desfà.

    Calcat de `test_lectors_capa_onada1.comporta_alcada`, que ja està provat. El `finally` no
    és decoratiu: si un assert peta a dins, la comporta ha de tornar igual. A Postgres el DDL
    és transaccional, o sigui que el `DROP CONSTRAINT` es desfà amb el savepoint igual que un
    INSERT — el test no deixa rastre, i el darrer test del fitxer ho verifica llegint el
    catàleg.
    """
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                # `IF EXISTS` — C4/G1-G4 (04/08) han retirat les 40 comportes: alçar-ne una
                # que ja no hi és és el mateix estat, i el `finally` retorna igual.
                cur.execute(
                    f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                    f'DROP CONSTRAINT IF EXISTS "{taula}_instancia_gate_cins"'
                )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class _BaseInstanciaTest(TenantTestCase):

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
        self.model = Model.objects.create(
            codi_intern='TST-CINS', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )


class ComportaInstanciaCinsTest(_BaseInstanciaTest):

    # ── La comporta barra ────────────────────────────────────────────────────────────

    def test_una_mesura_base_amb_instancia_no_entra(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0,
                nom_fitxa='A', instancia=LEFT)

    def test_una_linia_de_size_check_amb_instancia_no_entra(self):
        check = SizeCheck.objects.create(model=self.model, talla_base_label='M')
        with self.assertRaises(IntegrityError), transaction.atomic():
            SizeCheckLine.objects.create(
                size_check=check, pom=self.pom, valor_teoric=100.0, instancia=LEFT)

    def test_tampoc_hi_entra_per_update_massiu(self):
        """El camí que cap guard d'aplicació no cobriria: `queryset.update()` no passa per
        `save()`, ni pels signals, ni per cap serializer. La comporta sí que l'atura."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, nom_fitxa='A')
        with self.assertRaises(IntegrityError), transaction.atomic():
            BaseMeasurement.objects.filter(pk=bm.pk).update(instancia=LEFT)

    # ── La comporta deixa passar el que ha de passar ─────────────────────────────────

    def test_la_instancia_unica_entra_i_es_el_default(self):
        """La comporta no pot haver trencat el camí normal: qui no diu res escriu la
        instància única —cadena buida, mai NULL— i entra."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        bm.refresh_from_db()
        self.assertEqual(bm.instancia, '')

    def test_els_dos_eixos_son_independents(self):
        """La instància no ha tapat la capa: el default de C1 segueix vigent i la seva
        comporta segueix barrant. Dos eixos, dues comportes, cap d'elles absorbida per
        l'altra."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        bm.refresh_from_db()
        self.assertEqual((bm.capa, bm.instancia), ('exterior', ''))
        with self.assertRaises(IntegrityError), transaction.atomic():
            BaseMeasurement.objects.filter(pk=bm.pk).update(capa='folre')

    # ── El cens: cap forat ───────────────────────────────────────────────────────────

    def test_les_nou_comportes_existeixen_a_la_bd(self):
        """Una comporta que faltés seria un forat silenciós: la taula sense guard acceptaria
        la segona instància i ningú no se n'adonaria fins que les mesures ja fossin dolentes."""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT conname FROM pg_constraint c "
                "JOIN pg_namespace n ON n.oid = c.connamespace "
                "WHERE n.nspname = %s AND c.contype = 'c' AND c.conname LIKE %s",
                [connection.schema_name, '%_instancia_gate_cins'])
            trobades = {row[0] for row in cur.fetchall()}

        self.assertEqual(trobades, set(COMPORTES),
                         'falta (o sobra) alguna comporta d\'instància a la BD')

    def test_les_dues_families_de_comporta_conviuen(self):
        """El pin de `test_capa_comporta_c1` compta nou noms amb `LIKE '%_capa_gate_c1'`.
        Aquest test fixa que la família nova no l'ha contaminat: si algú bategés una comporta
        d'instància amb el sufix de capa, allà petaria un cens i aquí un altre."""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT conname FROM pg_constraint c "
                "JOIN pg_namespace n ON n.oid = c.connamespace "
                "WHERE n.nspname = %s AND c.contype = 'c' AND c.conname LIKE %s",
                [connection.schema_name, '%_capa_gate_c1'])
            capa = {row[0] for row in cur.fetchall()}

        self.assertEqual(len(capa), 9, 'el cens de comportes de capa ha canviat de mida')
        self.assertFalse(capa & set(COMPORTES), 'les dues famílies s\'han barrejat de nom')

    def test_la_regla_de_grading_no_te_ni_instancia_ni_comporta(self):
        """Decisió Montse: la sisa dreta i l'esquerra GRADÚEN IGUAL. Una regla és una llei
        d'increments, no un valor. Si algú li afegeix `instancia` sense passar per la decisió
        d'arquitectura, aquest test l'atura — igual que el seu germà ho fa per a la capa."""
        with connection.cursor() as cur:
            for taula in ('models_app_modelgradingrule', 'pom_gradingrule'):
                cur.execute(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = %s AND table_name = %s "
                    "AND column_name = 'instancia'",
                    [connection.schema_name, taula])
                self.assertIsNone(
                    cur.fetchone(),
                    f'{taula} ha rebut una columna `instancia`: és decisió '
                    "d'arquitectura (Patró C), no una peça d'sprint")


class ComportaInstanciaExigeixNomTest(_BaseInstanciaTest):
    """DECISIÓ D1 — una instància sense nom de fitxa és il·legal per construcció.

    Aquest CHECK no és bastida i no se'n va amb C4-ins: si una mesura es desdobla, l'única
    cosa que fa que les dues files siguin distingibles per a un humà —al croquis, a la taula,
    al paper— és el `nom_fitxa`. Dues files «pit» sense res que les separi visualment no són
    dues mesures: són un duplicat amb aparença de dada bona.

    Provar-ho exigeix alçar la comporta: amb ella tancada, `instancia` no pot ser mai
    diferent de '' i el CHECK no s'arriba a avaluar mai. S'alça dins d'un savepoint que
    sempre es desfà.
    """

    TAULA = 'models_app_basemeasurement'

    def test_instancia_sense_nom_de_fitxa_es_rebutjada(self):
        with comporta_instancia_alcada(self.TAULA):
            with self.assertRaises(IntegrityError), transaction.atomic():
                BaseMeasurement.objects.create(
                    model=self.model, pom=self.pom, base_value_cm=100.0,
                    instancia=LEFT, nom_fitxa='')

    def test_instancia_amb_nom_de_fitxa_entra(self):
        """La cara B: el CHECK no barra la instància, barra la instància ANÒNIMA. Si barrés
        totes dues, C4-ins es trobaria una llei que no deixa fer justament el que ha de fer.

        ⚠️ FASE_3 — cal alçar també la comporta del LOG: el signal F1 ja estampa els dos
        eixos, o sigui que crear una mesura amb instància hi escriu una fila amb instància.
        """
        with comporta_instancia_alcada(self.TAULA, 'models_app_measurementchangelog'):
            bm = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0,
                instancia=LEFT, nom_fitxa='A-ESQ')
            bm.refresh_from_db()
            self.assertEqual((bm.instancia, bm.nom_fitxa), (LEFT, 'A-ESQ'))

    def test_la_instancia_unica_pot_ser_anonima(self):
        """I la cara C, la que evita que el CHECK sigui una regressió: les mesures d'avui no
        tenen `nom_fitxa` obligatori i no n'han de tenir. La llei només s'activa quan hi ha
        instància."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, nom_fitxa='')
        bm.refresh_from_db()
        self.assertEqual((bm.instancia, bm.nom_fitxa), ('', ''))

    def test_la_comporta_torna_a_estar_viva(self):
        """El savepoint ha de deixar la BD com estava. Si aquest test peta, els anteriors han
        deixat una taula sense guard — i el següent sprint construiria sobre un forat."""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_constraint c "
                "JOIN pg_namespace n ON n.oid = c.connamespace "
                "WHERE n.nspname = %s AND c.conname = %s",
                [connection.schema_name, f'{self.TAULA}_instancia_gate_cins'])
            self.assertIsNotNone(cur.fetchone(), 'la comporta no ha tornat del savepoint')
