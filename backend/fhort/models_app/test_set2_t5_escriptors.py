"""SET-2/T5 — la poda i el registre saben de la peça (2026-08-10).

Els dos vermells de prioritat del tram, i tots dos són del gènere que aquest sprint
persegueix: **danys que no criden**.

  1 · `_poda_mesures`, branca de la CLAU CURTA. Desactiva (`is_active=False`) tot el que no
      sigui a `keep_pom_ids`, i el cridador que hi arriba només sap dir POMs. Ja s'acotava a
      l'exterior de la instància única; sense `garment=''` hauria donat de baixa les files de
      TOTES les peces del model. Ningú peta: les mesures simplement deixen de comptar.

  2 · **Signal F1**. `MeasurementChangeLog` és APPEND-ONLY i no té cap unicitat: una fila
      escrita sense l'eix NO es pot corregir després. Si el log no copia el `garment`, el
      lector no podrà dir mai de quina peça parlava un canvi ja registrat — i la secció
      «preses reescrites per regla de germana», que ha de néixer d'aquest registre, neixeria
      cega.

Les comportes es lleven dins d'un savepoint que sempre es desfà (patró
`test_lectors_capa_onada1`), perquè amb elles vives cap fila '02' pot existir.
"""
import contextlib
import datetime

from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import BaseMeasurement, MeasurementChangeLog, Model
from fhort.models_app.views import _poda_mesures
from fhort.pom.models import POMMaster

MARE = ''
SEGONA = '02'
TAULES = ('models_app_basemeasurement', 'models_app_measurementchangelog')


@contextlib.contextmanager
def comportes_alcades(*taules):
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                cur.execute(
                    f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                    f'DROP CONSTRAINT IF EXISTS "{taula}_garment_gate_set2"'
                )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class PodaINoTocaLesAltresPecesTest(TenantTestCase):

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
        self.altre = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')
        self.model = Model.objects.create(
            codi_intern='TST-T5', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def _mesura(self, pom, garment=MARE, valor=100.0, nom='A'):
        return BaseMeasurement.objects.create(
            model=self.model, pom=pom, base_value_cm=valor, ordre=1,
            nom_fitxa=nom, garment=garment)

    def test_una_poda_amb_clau_CURTA_no_toca_les_files_de_les_altres_peces(self):
        """EL VERMELL PRINCIPAL DE T5.

        `keep_pom_ids` és una llista de POMs: no diu res de peces. Podar amb ella ha de
        deixar la 02 EXACTAMENT com estava —encara que el seu POM no hi surti—, perquè una
        llista de POMs no és una ordre d'esborrar la feina d'una altra peça.
        """
        with comportes_alcades(*TAULES):
            mare_conserva = self._mesura(self.pom, MARE, nom='A-MARE')
            mare_poda = self._mesura(self.altre, MARE, valor=80.0, nom='B-MARE')
            segona = self._mesura(self.altre, SEGONA, valor=60.0, nom='B-02')

            _poda_mesures(self.model, None, [self.pom.pk])

            mare_conserva.refresh_from_db()
            mare_poda.refresh_from_db()
            segona.refresh_from_db()
            self.assertTrue(mare_conserva.is_active, 'el POM conservat de la mare ha caigut')
            self.assertFalse(mare_poda.is_active, 'el POM no conservat de la mare no ha caigut')
            self.assertTrue(
                segona.is_active,
                'LA PODA HA DESACTIVAT LA FILA DE LA PEÇA 02 amb una crida que no en parlava')

    def test_EL_CAS_DE_CONTROL_la_poda_dun_model_dUNA_pesa_fa_el_de_sempre(self):
        """Que l'eix no talli de més: el 100% del corpus d'avui és d'una sola peça i la
        poda hi ha de fer exactament el que feia."""
        mante = self._mesura(self.pom, MARE, nom='A')
        cau = self._mesura(self.altre, MARE, valor=80.0, nom='B')

        n = _poda_mesures(self.model, None, [self.pom.pk])

        mante.refresh_from_db()
        cau.refresh_from_db()
        self.assertEqual(n, 1)
        self.assertTrue(mante.is_active)
        self.assertFalse(cau.is_active)

    def test_la_poda_per_FILA_distingeix_les_peces(self):
        """L'altra branca: amb `keep_mesures` (que SÍ porta identitat), conservar la fila de
        la mare no pot salvar la de la 02 ni a l'inrevés."""
        with comportes_alcades(*TAULES):
            mare = self._mesura(self.pom, MARE, nom='A-MARE')
            segona = self._mesura(self.pom, SEGONA, valor=60.0, nom='A-02')

            _poda_mesures(self.model,
                          [{'pom_id': self.pom.pk, 'capa': 'exterior',
                            'instancia': '', 'garment': MARE}],
                          [])

            mare.refresh_from_db()
            segona.refresh_from_db()
            self.assertTrue(mare.is_active)
            self.assertFalse(segona.is_active,
                             'la fila de la 02 no estava a la llista i havia de caure')


class ElRegistreCopiaLaPecaTest(TenantTestCase):
    """Signal F1 — append-only i sense unicitat: el que no s'escrigui aquí es perd per sempre."""

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
            codi_intern='TST-T5L', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def test_un_canvi_de_valor_a_la_02_queda_registrat_A_LA_02(self):
        """Sense això, el registre diria que el canvi va ser de la peça mare — i com que la
        taula és append-only, la mentida seria permanent."""
        with comportes_alcades(*TAULES):
            bm = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=50.0, ordre=1,
                nom_fitxa='A-02', garment=SEGONA)
            bm.base_value_cm = 55.0
            bm.save()

            apunts = list(MeasurementChangeLog.objects
                          .filter(model=self.model, pom=self.pom)
                          .values_list('garment', 'valor_nou'))
            self.assertIn((SEGONA, 55.0), apunts,
                          "el registre no ha copiat el garment del canvi de valor")

    def test_EL_CAS_DE_CONTROL_un_canvi_a_la_mare_segueix_dient_el_de_sempre(self):
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A')
        bm.base_value_cm = 103.0
        bm.save()

        apunts = list(MeasurementChangeLog.objects
                      .filter(model=self.model, pom=self.pom)
                      .values_list('garment', 'valor_nou'))
        self.assertIn((MARE, 103.0), apunts)


class LaCopiaCopiaLaPecaTest(TenantTestCase):
    """T5b — els col·lapses silenciosos: la còpia model→model i la materialització del check.

    Tots dos seguien un rastre que ja hi era («la còpia COPIA: els eixos surten de la fila
    d'origen, no de cap literal») i només els faltava el tercer eix.
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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-T5C', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def test_la_materialitzacio_del_check_no_deixa_cap_peca_fora(self):
        """`_materialize_lines` aparellava per (pom, capa, instancia): la PRIMERA peça
        bloquejava la materialització de les altres i la seva fila quedava INERTA a
        l'editor —el tècnic la veia i no la podia omplir—.

        EL CAS DE CONTROL TRENCA LA COINCIDÈNCIA: les dues files són del MATEIX POM, la
        MATEIXA capa i la MATEIXA instància. L'única cosa que les separa és la peça, o sigui
        que si l'aparellament no la mira, la segona no es materialitza.
        """
        from fhort.models_app.models import SizeCheck, SizeCheckLine
        from fhort.models_app.services_size_check import _materialize_lines

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog',
                               'models_app_sizecheckline'):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-MARE', garment=MARE)
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=60.0, ordre=2,
                nom_fitxa='A-02', garment=SEGONA)
            check = SizeCheck.objects.create(model=self.model, talla_base_label='M')
            # ⚠️ LA LÍNIA DE LA MARE JA HI ÉS. Sense això el test no provava res: `ja_hi_son`
            # es construeix de les línies EXISTENTS, i amb un check nou el conjunt és buit i
            # l'aparellament no s'arriba a consultar mai. Amb la línia de la mare present, la
            # clau curta la fa casar amb la fila de la 02 —mateix POM, mateixa capa, mateixa
            # instància— i la 02 es queda sense materialitzar. (Mutant supervivent caçat
            # 2026-08-10: el primer sospitós era el test, i ho era.)
            SizeCheckLine.objects.create(
                size_check=check, pom=self.pom, capa='exterior', instancia='',
                garment=MARE, valor_teoric=100.0)

            _materialize_lines(check, self.model)

            files = set(SizeCheckLine.objects
                        .filter(size_check=check)
                        .values_list('garment', 'valor_teoric'))
            self.assertEqual(
                files, {(MARE, 100.0), (SEGONA, 60.0)},
                'la primera peça ha bloquejat la materialització de la segona')
