"""C1-ins — LA COMPORTA D'INSTÀNCIA: cap escriptor pot crear una segona instància abans de C4-ins.

Germà exacte de `test_capa_comporta_c1`, amb l'eix canviat. C1-ins ensenya al sistema el
segon idioma —el que distingeix la sisa DRETA de l'ESQUERRA, el pit RELAXED de l'EXTENDED—
però no el deixa parlar-lo: la cadena de lectors encara indexa per `pom_id` (o, com a molt,
per `(pom_id, capa)`) i no s'adapta fins a FASE_2/FASE_3. Sense comporta, una segona
instància escrita per accident en aquesta finestra no petaria enlloc: es fondria dins les
llistes com la primera i corrompria en silenci mesures que són el producte.

El guard viu a la BD i no a l'aplicació pel mateix motiu que el de capa: és l'únic lloc que un
`bulk_create`, un `update()`, un loader de paquet o un `psql` a mà no poden esquivar.

**C4/G1-G4 (04/08) han retirat les nou comportes d'instància, i les nou de capa amb elles.**
Aquest fitxer GIRA L'AFIRMACIÓ i verifica TRES coses que no es proven soles:
  1. que la germana amb instància ENTRA i es desa a la SEVA fila, sense tapar la que ja hi
     era (on abans deia «no entra», amb l'`IntegrityError` de Postgres);
  2. que cap comporta de cap de les dues famílies no ha sobreviscut —una que quedés dreta
     barraria la sisa esquerra en un sistema que ja la sap llegir— i que `ModelGradingRule`
     segueix sense la columna (decisió Montse: «gradúen igual»);
  3. que el CHECK «instància ⇒ nom de fitxa» (decisió D1) SEGUEIX rebutjant. És l'única cosa
     del tram que no era bastida, i la retirada no se l'havia d'endur.

🔑 EL QUE ARA ÉS CERT, i és el que aquest fitxer vigila: **0 comportes de capa i d'instància ·
la invariant `instancia_exigeix_nom` viva.** Sempre PEL NOM, mai per recompte: una xifra fixa
ja ha mossegat dues vegades (el 18 dels harnesses, el 42 del brief de retirada).

El `comporta_instancia_alcada()` es queda tot i ser un no-op: alçar una comporta que ja no hi
és és el mateix estat, i el dia que el CHECK s'hagi de provar amb una comporta nova al davant
el harness ja hi serà.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.db import IntegrityError, connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import (BaseMeasurement, Model, SizeCheck,
                                     SizeCheckLine)
from fhort.pom.models import POMMaster

#: Els dos patrons de nom de les 40 comportes que C4/G1-G4 han retirat. Es censa pel PATRÓ i
#: no per una llista de noms: així també cau una comporta nova que es bategés igual.
PATRONS_DE_COMPORTA = ('%_capa_gate_c1', '%_instancia_gate_cins')

#: La invariant que NO era bastida i havia de sobreviure la retirada (decisió D1).
INVARIANT = 'models_app_basemeasurement_instancia_exigeix_nom'

#: L'instància de prova. Slug compost, com el que la UI compondrà a C4-ins.
LEFT = 'left-relaxed'


def noms_de_check(patro):
    """Els noms dels CHECK del schema del tenant que casen amb `patro`."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT conname FROM pg_constraint c "
            "JOIN pg_namespace n ON n.oid = c.connamespace "
            "WHERE n.nspname = %s AND c.contype = 'c' AND c.conname LIKE %s",
            [connection.schema_name, patro])
        return {row[0] for row in cur.fetchall()}


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

    # ── La germana entra, i es desa a la SEVA fila ───────────────────────────────────

    def test_una_mesura_base_amb_instancia_entra_a_la_seva_fila(self):
        """Deia «no entra». Ara entra, i el que es vigila és que la sisa esquerra no tapi la
        mesura que ja hi era: dues files amb la mateixa (model, POM) i instàncies diferents."""
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=97.0,
            nom_fitxa='A-ESQ', instancia=LEFT)

        files = {(bm.instancia, float(bm.base_value_cm))
                 for bm in BaseMeasurement.objects.filter(model=self.model, pom=self.pom)}
        self.assertEqual(files, {('', 100.0), (LEFT, 97.0)})

    def test_una_linia_de_size_check_amb_instancia_entra_a_la_seva_fila(self):
        check = SizeCheck.objects.create(model=self.model, talla_base_label='M')
        SizeCheckLine.objects.create(
            size_check=check, pom=self.pom, valor_teoric=100.0)
        SizeCheckLine.objects.create(
            size_check=check, pom=self.pom, valor_teoric=97.0, instancia=LEFT)

        files = {(linia.instancia, float(linia.valor_teoric))
                 for linia in SizeCheckLine.objects.filter(size_check=check, pom=self.pom)}
        self.assertEqual(files, {('', 100.0), (LEFT, 97.0)})

    def test_l_update_massiu_mou_la_fila_filtrada_i_prou(self):
        """El camí que cap guard d'aplicació no cobriria —`queryset.update()` no passa per
        `save()`, ni pels signals, ni per cap serializer— ja no el barra ningú. El que ara
        s'ha de vigilar és que sigui QUIRÚRGIC: bateja la fila filtrada i deixa estar l'altra."""
        altre_pom = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')
        mou = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, nom_fitxa='A')
        queda = BaseMeasurement.objects.create(
            model=self.model, pom=altre_pom, base_value_cm=80.0, nom_fitxa='B')

        BaseMeasurement.objects.filter(pk=mou.pk).update(instancia=LEFT)

        mou.refresh_from_db()
        queda.refresh_from_db()
        self.assertEqual(mou.instancia, LEFT)
        self.assertEqual(queda.instancia, '')

    # ── El camí normal, intacte ──────────────────────────────────────────────────────

    def test_la_instancia_unica_entra_i_es_el_default(self):
        """La comporta no pot haver trencat el camí normal: qui no diu res escriu la
        instància única —cadena buida, mai NULL— i entra."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        bm.refresh_from_db()
        self.assertEqual(bm.instancia, '')

    def test_els_dos_eixos_son_independents(self):
        """La instància no ha tapat la capa: cada eix es mou pel seu compte i una fila pot
        creuar-los tots dos sense que l'altre se n'assabenti. Deia que la comporta de capa
        seguia barrant; ara les dues han caigut i el que es prova és que segueixen sent DOS
        eixos i no un de sol."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        bm.refresh_from_db()
        self.assertEqual((bm.capa, bm.instancia), ('exterior', ''))

        creuada = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=96.0,
            capa='folre', nom_fitxa='A-ESQ-FOL', instancia=LEFT)
        creuada.refresh_from_db()
        self.assertEqual((creuada.capa, creuada.instancia), ('folre', LEFT))

        bm.refresh_from_db()
        self.assertEqual((bm.capa, bm.instancia), ('exterior', ''))

    # ── El cens, girat: cap comporta viva, la invariant sí ───────────────────────────

    def test_cap_comporta_de_cap_de_les_dues_families_no_ha_sobreviscut(self):
        """Deia «les nou comportes hi són totes» i el forat silenciós era que en faltés una.
        Ara és al revés: una comporta dreta barraria la germana en un sistema que ja la sap
        llegir i escriure. Es censen les DUES famílies alhora perquè cauen juntes i el que
        importa és que no en quedi cap, no de quina era."""
        for patro in PATRONS_DE_COMPORTA:
            trobades = noms_de_check(patro)
            self.assertEqual(trobades, set(),
                             f'comportes vives després de C4 ({patro}): {sorted(trobades)}')

    def test_la_invariant_de_domini_no_se_n_ha_anat_amb_les_comportes(self):
        """L'altra cara, i la que de debò fa mal si falla: `instancia_exigeix_nom` NO era
        bastida sinó llei —una instància sense nom de fitxa és il·legal— i havia de sobreviure
        les quatre retirades. Pel nom, perquè és una i té nom propi."""
        self.assertEqual(noms_de_check('%_exigeix_nom'), {INVARIANT},
                         'la invariant de domini ha caigut amb les comportes')

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

    def test_el_harness_no_deixa_rastre_i_la_invariant_segueix_viva(self):
        """Successor de `test_la_comporta_torna_a_estar_viva`, que mirava si la comporta havia
        tornat del savepoint. Ja no n'hi ha cap per tornar, però el que aquell test defensava
        segueix sent necessari: que el harness deixi l'esquema EXACTAMENT com el va trobar —si
        no, els tests d'aquest fitxer passarien per una raó falsa— i que la invariant, que és
        l'única cosa que queda dreta del tram, no marxi per una porta del davant."""
        abans = noms_de_check('%')
        with comporta_instancia_alcada(self.TAULA, 'models_app_measurementchangelog'):
            pass

        self.assertEqual(noms_de_check('%'), abans, 'el harness ha canviat l\'esquema')
        self.assertIn(INVARIANT, abans, 'la invariant de domini no és viva')
