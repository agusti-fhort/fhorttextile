"""SET-2/T4 — dues PECES del mateix POM produeixen DUES files graduades, cadascuna amb la SEVA llei.

Germà exacte de `test_c3_b_dues_germanes`, amb l'eix canviat i una diferència de fons que és
tot el sentit de D4:

  · Dues GERMANES (capa/instància) comparteixen la llei d'increments i es diferencien només
    pel valor base. Una sola regla, dues files.
  · Dues PECES no: **poden tenir lleis distintes** (un top per talla alfa i una calceta per
    mesos). Dues regles, dues files, i cada fila ha de sortir de la seva.

EL MAL QUE VIGILA, que eren tres nodes encadenats i tots silenciosos:
  1. `_load_base_measurements` indexava per `(pom, capa, instancia)` → les dues peces entraven
     al dict amb la MATEIXA clau i l'última llegida guanyava. La perdedora no perdia una
     cel·la: perdia la FILA SENCERA, sense excepció, sense log i sense rastre.
  2. `_load_grading_rules` indexava `{pom_id: regla}`, un escalar → amb dues regles per al
     mateix POM, la segona **sobreescrivia la primera en memòria** i el motor graduava una
     peça sencera amb la llei de l'altra, sense un sol log.
  3. `_upsert_graded_spec` feia el lookup sense el garment → o reescrivia la fila de l'altra
     peça, o petava amb `MultipleObjectsReturned` quan n'hi hagués dues.

Amb les comportes de T2 vives el cas no es pot ni construir: totes les files són `garment=''`.
Per això s'alcen dins d'un savepoint que sempre es desfà (patró `test_lectors_capa_onada1`),
i se n'alcen TRES i no una, cadascuna pel seu motiu:
  · `models_app_basemeasurement`      — per poder escriure la mesura de la segona peça.
  · `models_app_modelgradingrule`     — per poder-li donar la SEVA llei (això és nou de T4: a
                                        C3 la regla no travessava cap eix i no calia alçar-la).
  · `fitting_gradedspec`              — és ON HA D'ATERRAR el resultat: sense alçar-la, el
                                        motor calcularia bé i Postgres refusaria l'escriptura.
"""
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem

MARE = ''
SEGONA = '02'
TAULES = ('models_app_basemeasurement', 'models_app_modelgradingrule', 'fitting_gradedspec')


@contextlib.contextmanager
def comportes_garment_alcades(*taules):
    """Alça les comportes `*_garment_gate_set2` dins d'un savepoint que SEMPRE es desfà."""
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


class MotorPerGarmentTest(TenantTestCase):

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
        self.ss = SizeSystem.objects.create(codi='SS_T4', nom='SS T4', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='TST-T4', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_t4', defaults={'email': 'qa@t4.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA T4', 'rol_nom': 'QA'})
        from fhort.fitting.models import SizeFitting
        self.sf, _ = SizeFitting.objects.get_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-T4', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.perfil},
        )

    def _specs(self):
        from fhort.fitting.models import GradedSpec
        from fhort.fitting.services import vigent_grading_version
        gv = vigent_grading_version(self.sf.pk)
        return {(s.garment, s.size_label): s.graded_value_cm
                for s in GradedSpec.objects.filter(grading_version=gv, pom=self.pom,
                                                   is_active=True)}

    def test_dues_peces_produeixen_DUES_files_amb_la_seva_propia_llei(self):
        """El verd de T4, i els tres nodes alhora.

        Increments BEN distints (+1 i +10) a posta: si el motor col·lapsés les regles, la
        fila perdedora no fallaria per un decimal sinó per un ordre de magnitud. I valors base
        distints (100 i 50) perquè un col·lapse de mesures també salti a la vista.
        """
        from fhort.pom.services import generate_graded_specs

        with comportes_garment_alcades(*TAULES):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-MARE', garment=MARE)
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=50.0, ordre=2,
                nom_fitxa='A-02', garment=SEGONA)
            ModelGradingRule.objects.create(
                model=self.model, pom=self.pom, logica='LINEAR', increment=1.0,
                actiu=True, garment=MARE)
            ModelGradingRule.objects.create(
                model=self.model, pom=self.pom, logica='LINEAR', increment=10.0,
                actiu=True, garment=SEGONA)

            generate_graded_specs(self.sf.pk)

            self.assertEqual(self._specs(), {
                (MARE, 'S'): 99.0, (MARE, 'M'): 100.0, (MARE, 'L'): 101.0,
                (SEGONA, 'S'): 40.0, (SEGONA, 'M'): 50.0, (SEGONA, 'L'): 60.0,
            }, 'les dues peces no han sortit senceres i cadascuna amb la seva llei')

    def test_una_peca_sense_regla_propia_HERETA_la_de_la_mare(self):
        """L'herència de D5 aplicada a la regla, i el que evita que el motor emmudeixi.

        Si `_regla_de` no caigués a la mare, una peça sense regles sembrades cauria a la llei
        de cel·la absent i no emetria CAP fila — un silenci, que és el mode de fallada que
        aquest sprint persegueix. Aquí la 02 no té regla pròpia i ha de graduar amb la del
        model, sobre el SEU valor base.
        """
        from fhort.pom.services import generate_graded_specs

        with comportes_garment_alcades(*TAULES):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-MARE', garment=MARE)
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=50.0, ordre=2,
                nom_fitxa='A-02', garment=SEGONA)
            ModelGradingRule.objects.create(
                model=self.model, pom=self.pom, logica='LINEAR', increment=1.0,
                actiu=True, garment=MARE)

            generate_graded_specs(self.sf.pk)

            self.assertEqual(self._specs(), {
                (MARE, 'S'): 99.0, (MARE, 'M'): 100.0, (MARE, 'L'): 101.0,
                (SEGONA, 'S'): 49.0, (SEGONA, 'M'): 50.0, (SEGONA, 'L'): 51.0,
            }, "la peça sense regla pròpia no ha heretat la llei de la mare")

    def test_EL_CAS_DE_CONTROL_un_sol_garment_gradua_exactament_com_abans(self):
        """El cas de control: que l'eix nou no talli de més.

        Un model d'una sola peça —el 100% del corpus d'avui— ha de sortir byte a byte com
        sortia. Si això caigués, el símptoma no seria un test vermell aquí sinó tot el
        catàleg graduant diferent, i és per això que la paritat del golden va a part.
        """
        from fhort.pom.services import generate_graded_specs

        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A')
        ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='LINEAR', increment=1.0, actiu=True)

        generate_graded_specs(self.sf.pk)

        self.assertEqual(self._specs(), {
            (MARE, 'S'): 99.0, (MARE, 'M'): 100.0, (MARE, 'L'): 101.0,
        })
