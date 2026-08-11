"""SET-2/T6a — `graded-table/` SERVEIX L'EIX DE LA PEÇA, i les seves files no col·lapsen.

És el prerequisit de la partició de la T1b per prenda (D7): `TechSheetEditor.jsx` ja passa
`data.rows` per `partirEnTaules`→`garmentDeFila`, i fins avui totes les files li queien a la
mare perquè el payload no portava el camp.

⚠️ PER QUÈ AIXÒ NO CONTRADIU EL REVERT DE `7cc133b5`, que va TREURE una clau `garment` del
payload de `base-measurements/`. Els dos motius d'aquell revert no apliquen aquí:

  (a) Allà se servia una DEFINICIÓ HEREDABLE (run, ruleset, talla base) — un valor que la peça
      pot no tenir i que s'ha de resoldre contra el model. Aquella resolució
      (`garment.X or model.X`) ha de viure en UN SOL PUNT (D5) i servir-la crua n'obria una
      segona via. Aquí no hi ha cap resolució: el `garment` d'una fila és l'eix PROPI de la
      fila, dada factual.
  (b) Allà la clau no tenia cap lector. Aquí en té un de nomenat (la T1b).

🔑 LA REGLA: **servir l'EIX D'UNA FILA és sempre legítim; servir una DEFINICIÓ RESOLTA, només
des del punt únic.**

EL QUE AQUEST FITXER NO TOCA: l'etiqueta de regla de la fila (`increment_base`, `logica`,
`talla_break_label`) segueix llegint la llei de la MARE, i és una decisió amb acta de T5
(`pom/services.py`, `_load_grading_rules`): cinc rètols de presentació la llegeixen a posta
mentre les comportes visquin, i es revisen el dia que es retirin. Servir l'eix de la fila no
obre aquella decisió; obrir-la aquí seria la segona via que T5 va evitar.
"""
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.graded_spec_views import GradedSpecTableView
from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem

RUN = ['S', 'M', 'L']
BASE = 'M'
MARE = ''
SEGONA = '02'
TAULES = ('fitting_gradedspec', 'models_app_basemeasurement', 'models_app_measurementchangelog')


@contextlib.contextmanager
def comportes_garment_alcades(*taules):
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


class _T6aBase(TenantTestCase):
    """Fixture compartit i CAP test.

    ⚠️ La classe de control heretava directament de la de l'eix i, com que `unittest` recull
    els mètodes heretats, tornava a córrer els tres casos multipeça amb un altre nom: el
    mutant els va fer sortir per duplicat (6 fallades de 3 defectes) i el recompte de la capa
    ràpida quedava inflat. El fixture es comparteix; els casos, no.
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
        from fhort.accounts.models import UserProfile
        self.user = get_user_model().objects.create(username='t6a')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'T6a', 'rol_nom': 'admin'})
        self.ss = SizeSystem.objects.create(codi='SS_T6A', nom='SS T6a', base_unit='ALPHA')
        for i, sl in enumerate(RUN):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=sl, ordre=i)
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Chest')
        self.model = Model.objects.create(
            codi_intern='TST-T6A', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_system=self.ss, size_run_model='·'.join(RUN),
            base_size_label=BASE,
        )
        self.sf = SizeFitting.objects.filter(model=self.model).first()
        self.gv = GradingVersion.objects.create(
            size_fitting=self.sf, version_number=1, is_active=True, creat_per=self.profile)
        self.factory = APIRequestFactory()
        self.view = GradedSpecTableView.as_view()

    def _spec(self, garment, valor):
        GradedSpec.objects.create(
            grading_version=self.gv, pom=self.pom, size_label=BASE,
            graded_value_cm=valor, increment_applied_cm=0,
            grading_type_applied='LINEAR', is_active=True, garment=garment)

    def _files(self):
        req = self.factory.get('/graded-table/')
        force_authenticate(req, user=self.user)
        return self.view(req, sf_id=self.sf.id).data['rows']


class GradedTableEixTest(_T6aBase):

    def test_dues_peces_del_mateix_POM_donen_DUES_files_amb_el_seu_valor(self):
        """EL PIN DEL DANY. Valors ben distints (100 i 50) perquè un col·lapse salti a la
        vista: sense l'eix a `ident`, les dues cauen a la mateixa fila i la fitxa n'imprimeix
        una amb la xifra de l'altra."""
        with comportes_garment_alcades(*TAULES):
            self._spec(MARE, 100.0)
            self._spec(SEGONA, 50.0)

            files = self._files()

            self.assertEqual(len(files), 2, 'les dues peces han col·lapsat en una fila')
            self.assertEqual(
                [(f['garment'], f['valors'][BASE]) for f in files],
                [(MARE, 100.0), (SEGONA, 50.0)])

    def test_la_fila_PUBLICA_leix_perque_la_T1b_hi_pugui_partir(self):
        """`garmentDeFila` llegeix `fila.garment`; sense el camp, tot cau a la mare."""
        with comportes_garment_alcades(*TAULES):
            self._spec(SEGONA, 50.0)

            self.assertEqual([f['garment'] for f in self._files()], [SEGONA])

    def test_les_files_duna_peca_van_JUNTES_i_la_mare_primer(self):
        """L'ordre: «la prenda a fora» (T9). Un POM d'ordre alt de la mare va abans que un
        POM d'ordre baix de la segona peça."""
        pom2 = POMMaster.objects.create(codi_client='SL', nom_client='Sleeve')
        with comportes_garment_alcades(*TAULES):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=99, garment=MARE)
            BaseMeasurement.objects.create(
                model=self.model, pom=pom2, base_value_cm=30.0, ordre=1, garment=SEGONA)
            self._spec(MARE, 100.0)
            GradedSpec.objects.create(
                grading_version=self.gv, pom=pom2, size_label=BASE, graded_value_cm=30.0,
                increment_applied_cm=0, grading_type_applied='LINEAR', is_active=True,
                garment=SEGONA)

            self.assertEqual([f['garment'] for f in self._files()], [MARE, SEGONA])

    def test_els_quatre_mapes_denriquiment_troben_la_fila_de_la_segona_peca(self):
        """`ordre`, `nom_fitxa`, `seccio` i el bateig surten de la `BaseMeasurement` de LA
        MATEIXA peça. Amb la clau curta, la fila de la 02 rebia el `ref` i la secció de la
        mare — un rètol de croquis atribuït a la peça equivocada."""
        with comportes_garment_alcades(*TAULES):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-MARE', seccio='cos', garment=MARE)
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=50.0, ordre=2,
                nom_fitxa='A-02', seccio='caputxa', garment=SEGONA)
            self._spec(MARE, 100.0)
            self._spec(SEGONA, 50.0)

            files = self._files()

            self.assertEqual([(f['garment'], f['ref'], f['seccio']) for f in files],
                             [(MARE, 'A-MARE', 'cos'), (SEGONA, 'A-02', 'caputxa')])


class CasDeControlUnaSolaPecaTest(_T6aBase):
    """El 100% del corpus d'avui: la taula ha de sortir EXACTAMENT com abans de T6a."""

    def test_una_sola_peca_dona_una_fila_amb_leix_de_la_mare(self):
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A')
        self._spec(MARE, 100.0)

        files = self._files()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['garment'], MARE)
        self.assertEqual(files[0]['valors'][BASE], 100.0)
        self.assertEqual(files[0]['ref'], 'A')

    def test_les_dues_germanes_de_capa_segueixen_sent_dues_files(self):
        """No-regressió de C4: l'eix nou no se'n menja cap dels dos vells."""
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='EXT')
        self._spec(MARE, 100.0)
        GradedSpec.objects.create(
            grading_version=self.gv, pom=self.pom, size_label=BASE, graded_value_cm=98.0,
            increment_applied_cm=0, grading_type_applied='LINEAR', is_active=True,
            capa='folre')

        files = self._files()

        self.assertEqual(len(files), 2)
        self.assertEqual([f['capa'] for f in files], ['exterior', 'folre'])
