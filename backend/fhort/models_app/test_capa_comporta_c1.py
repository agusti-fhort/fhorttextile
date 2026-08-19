"""C1/T4 → C4 — LA CAPA JA ES POT ESCRIURE: el que abans barrava la comporta, ara entra.

HISTÒRIA, i cal per llegir els asserts: C1 va ensenyar al sistema l'IDIOMA de la capa
(catàleg + columna + claus) però NO el va deixar parlar-lo. Mentre la cadena de consumidors
—serializers, motor de grading, UI, import, fitxa— assumia una mesura per (model, POM), una
fila 'folre' escrita per accident no hauria petat enlloc: s'hauria fos dins les llistes com si
fos de l'exterior i hauria corromput en silenci mesures que són el producte. Per això hi havia
nou comportes, i a la BD i no a l'aplicació: és l'únic lloc que un `bulk_create`, un
`update()`, un loader de paquet o un `psql` a mà no poden esquivar.

**C4/G1-G4 (04/08) les han retirades totes.** Aquest fitxer no se'n va amb elles: GIRA
L'AFIRMACIÓ. On deia «la comporta rebutja aquesta fila» ara diu «aquesta germana entra i es
desa a la SEVA fila», i el cens diu que cap comporta de capa no ha sobreviscut. No és
relaxar-lo: la llei ha canviat i el test l'ha de dir.

El que NO ha canviat i segueix pinat: 'exterior' és el default de qui no diu res, i
`ModelGradingRule` segueix sense columna `capa` (§3c, «mateixos deltes»).

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import datetime

from django.db import connection
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import (BaseMeasurement, Model, SizeCheck,
                                     SizeCheckLine)
from fhort.pom.models import POMMaster

FOLRE = 'folre'
EXTERIOR = 'exterior'


class ComportaCapaC1Test(TenantTestCase):

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
            codi_intern='TST-C1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    # ── La germana entra, i es desa a la SEVA fila ───────────────────────────────────

    def test_una_mesura_base_de_folre_entra_a_la_seva_fila(self):
        """Deia «la comporta barra el folre». Ara la llei és que hi ENTRA, i el que s'ha de
        vigilar és l'altra meitat: que no trepitgi l'exterior. Dues files, dos eixos, dos
        valors — no una fila que en tapa una altra."""
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=98.0, capa=FOLRE)

        files = {(bm.capa, float(bm.base_value_cm))
                 for bm in BaseMeasurement.objects.filter(model=self.model, pom=self.pom)}
        self.assertEqual(files, {(EXTERIOR, 100.0), (FOLRE, 98.0)})

    def test_una_linia_de_size_check_de_folre_entra_a_la_seva_fila(self):
        check = SizeCheck.objects.create(model=self.model, talla_base_label='M')
        SizeCheckLine.objects.create(
            size_check=check, pom=self.pom, valor_teoric=100.0)
        SizeCheckLine.objects.create(
            size_check=check, pom=self.pom, valor_teoric=98.0, capa=FOLRE)

        files = {(linia.capa, float(linia.valor_teoric))
                 for linia in SizeCheckLine.objects.filter(size_check=check, pom=self.pom)}
        self.assertEqual(files, {(EXTERIOR, 100.0), (FOLRE, 98.0)})

    def test_l_update_massiu_mou_la_fila_filtrada_i_prou(self):
        """El camí que cap guard d'aplicació no cobriria —`queryset.update()` no passa per
        `save()`, ni pels signals, ni per cap serializer— ja no el barra ningú. Per això el
        que ara es vigila és que sigui QUIRÚRGIC: mou la fila filtrada i deixa estar l'altra.
        Un `update()` massiu que s'endugués les germanes seria el dany de debò."""
        altre_pom = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')
        mou = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        queda = BaseMeasurement.objects.create(
            model=self.model, pom=altre_pom, base_value_cm=80.0)

        BaseMeasurement.objects.filter(pk=mou.pk).update(capa=FOLRE)

        mou.refresh_from_db()
        queda.refresh_from_db()
        self.assertEqual(mou.capa, FOLRE)
        self.assertEqual(queda.capa, EXTERIOR)

    # ── El camí normal, intacte ──────────────────────────────────────────────────────

    def test_exterior_entra_i_es_el_default(self):
        """Retirar la comporta no pot haver trencat el camí normal: qui no diu res escriu
        'exterior' i entra. És la meitat que sempre es dona per suposada."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        bm.refresh_from_db()
        self.assertEqual(bm.capa, EXTERIOR)

    # ── El cens, girat: cap comporta viva ────────────────────────────────────────────

    def test_cap_comporta_de_capa_no_ha_sobreviscut(self):
        """Deia «les nou comportes hi són totes»; el forat silenciós era que en faltés una.
        Ara és exactament al revés: una comporta que hagués sobreviscut a C4/G1-G4 barraria
        la segona capa en un sistema que ja la sap llegir, escriure, graduar i mesurar.

        Es mira PEL NOM —el patró de la família sencera, no una xifra— perquè un recompte fix
        ja ha mossegat dues vegades: el 18 dels harnesses i el 42 del brief de retirada."""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT conname FROM pg_constraint c "
                "JOIN pg_namespace n ON n.oid = c.connamespace "
                "WHERE n.nspname = %s AND c.contype = 'c' AND c.conname LIKE %s",
                [connection.schema_name, '%_capa_gate_c1'])
            trobades = {row[0] for row in cur.fetchall()}

        self.assertEqual(trobades, set(),
                         f'comportes de capa vives després de C4: {sorted(trobades)}')

    def test_la_regla_de_grading_no_travessa_CAP_eix_de_germanor(self):
        """§3c: la regla es comparteix entre germanes («mateixos deltes»). Si algú li afegeix
        un eix de GERMANOR sense passar per la decisió d'arquitectura, aquest test l'atura.

        ── SET-2/T3 · ARA VIGILA EL PRINCIPI, NO UN NOM ─────────────────────────────────────
        Abans comprovava `column_name = 'capa'`, literal. La diagnosi SET-2 va demostrar que
        una columna NOVA hi passava sense fer-lo vermell: el guardià protegia un nom, no la
        llei. Ara itera `EIXOS_DE_GERMANOR`, la col·lecció canònica —i única— dels eixos pels
        quals dues files són dues cares de la MATEIXA mesura. El dia que el sistema n'aprengui
        un tercer, afegir-lo allà ja fa que aquest test el vigili.

        ⚠️ `garment` NO hi és A POSTA, i la seva absència d'aquesta llista és la decisió D4:
        és una FRONTERA, no un eix de germanor. Dues peces poden tenir lleis d'increments
        distintes (un top alfa i una calceta per mesos), i per això la clau SÍ que el
        travessa. Que aquest test no el vigili és el que el fa possible.
        """
        from fhort.models_app.services_derivacio import EIXOS_DE_GERMANOR

        for eix in EIXOS_DE_GERMANOR:
            with self.subTest(eix=eix):
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = %s AND table_name = %s AND column_name = %s",
                        [connection.schema_name, 'models_app_modelgradingrule', eix])
                    self.assertIsNone(
                        cur.fetchone(),
                        f'ModelGradingRule ha rebut una columna `{eix}`, que és un eix de '
                        "GERMANOR: una regla és una llei d'increments i les germanes en "
                        "comparteixen una de sola. És decisió d'arquitectura (Patró C), no "
                        "una peça d'sprint.")
