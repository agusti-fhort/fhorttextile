"""SET-2/T5c — LA PRESA DE FITTING SAP DE QUINA PEÇA ÉS CADA LÍNIA.

Germà de `_poda_mesures` (T5a) amb el mateix dany i una altra taula: `reconcilia_linies`
(`fitting/services.py`) indexa els `BaseMeasurement` actius del model per
`(pom_id, capa, instancia)` i compara les `PieceFittingLine` amb la mateixa clau curta. La
identitat real d'una línia és de SIS camps —`(piece_fitting, pom, size_label, capa,
instancia, garment)`, unicitat declarada a `fitting/0026`— i la del seu origen, de quatre.

EL DANY, i NO és el que semblava. La primera lectura d'aquest node (cens del 10/08) el va
classificar com a esborrat destructiu: «`sobreres` + `.delete()` esborraria les línies de la
segona peça». **És fals, i el test ho demostra.** Deixant caure el `garment` a totes DUES
bandes de la comparació, el predicat de `sobreres` queda estrictament MÉS AMPLI que la
identitat: una línia de la 02 troba la seva germana de la mare a `actives` i sobreviu. Amb la
clau curta s'esborra de MENYS, no de més.

El dany real és per ABSÈNCIA, i és de la família que aquest sprint persegueix:

  ① `actives` COL·LAPSA les dues peces en una sola entrada (l'última llegida guanya), o sigui
     que `a_crear` no pot generar mai més d'una línia per (pom, capa, instància). La mesura
     de la segona peça **no arriba mai al full de presa**: la modista no la pren, i no hi ha
     res a la pantalla que digui que falta.
  ② `specs` col·lapsa igual, de manera que la línia que sí que neix pot rebre el `valor_teoric`
     de l'ALTRA peça — una xifra que sembla bona i no ho és.

I hi ha una TERCERA porta, del mateix dany i a la superfície d'escriptura, tancada en el
mateix commit: el filtre de propagació de `fitting/views.py` deia CINC camps sobre una
identitat de sis, o sigui que ancorar una cel·la escampava el seu `valor_real` derivat a la
germana de l'altra peça. És exactament el defecte que l'acta C3/E3 d'aquell mateix bloc
descriu per als eixos de germanor, un eix més tard.

Amb les comportes de T2 vives el cas no es pot construir: totes les files són `garment=''`.
S'alcen dins d'un savepoint que sempre es desfà (patró `test_set2_t4_motor_per_garment`).
"""
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.fitting.models import (FittingSession, GradingVersion, PieceFitting,
                                  PieceFittingLine, SizeFitting)
from fhort.fitting.services import reconcilia_linies
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem

MARE = ''
SEGONA = '02'
#: Les comportes que cal alçar, i cadascuna pel seu motiu — la llista no és decorativa:
#:  · `models_app_basemeasurement`    — per poder donar una mesura a la segona peça.
#:  · `fitting_piecefittingline`      — és ON HAN D'ATERRAR les línies que la reconciliació crea.
#:  · `fitting_gradedspec`            — el camí del `valor_teoric` quan hi ha specs.
#:  · `models_app_measurementchangelog` — ⚠️ no és òbvia i la primera versió la va oblidar:
#:    crear una `BaseMeasurement` dispara el signal que escriu al registre de canvis, o sigui
#:    que el fixture peta amb `CheckViolation` d'una taula que el test no anomena mai.
TAULES = ('models_app_basemeasurement', 'fitting_piecefittingline', 'fitting_gradedspec',
          'models_app_measurementchangelog')


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


class _T5cBase(TenantTestCase):

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
        self.ss = SizeSystem.objects.create(codi='SS_T5C', nom='SS T5c', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='TST-T5C', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_t5c', defaults={'email': 'qa@t5c.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA T5c', 'rol_nom': 'QA'})
        self.sf, _ = SizeFitting.objects.get_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-T5C', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.perfil},
        )
        self.gv = GradingVersion.objects.create(
            size_fitting=self.sf, version_number=1, is_active=True, creat_per=self.perfil)
        self.session = FittingSession.objects.create(
            model=self.model, fase='Dev', data=datetime.date(2026, 8, 11))
        self.pf = PieceFitting.objects.create(
            session=self.session, model=self.model, grading_version=self.gv)

    def _linies(self):
        return sorted(
            (l.garment, l.size_label, float(l.valor_teoric))
            for l in PieceFittingLine.objects.filter(piece_fitting=self.pf))


class ReconciliacioPerGarmentTest(_T5cBase):

    def test_dues_peces_del_mateix_POM_generen_DUES_linies(self):
        """El dany ①: valors base BEN distints (100 i 50) perquè el col·lapse salti a la vista.

        Sense el `garment` a la clau, `actives` en reté una de les dues i la presa neix amb la
        meitat de les mesures que el model té — sense error i sense avís.
        """
        with comportes_garment_alcades(*TAULES):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, garment=MARE)
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=50.0, ordre=2, garment=SEGONA)

            res = reconcilia_linies(self.pf)

            self.assertEqual(res['creades'], 2, 'la segona peça no ha arribat al full de presa')
            self.assertEqual(self._linies(), [(MARE, 'M', 100.0), (SEGONA, 'M', 50.0)])

    def test_una_linia_dune_peca_que_el_model_ja_no_te_SI_que_es_retira(self):
        """L'altra cara: amb la clau sencera, la línia de la 02 deixa de trobar recer a la
        germana de la mare. El model només té la mesura de la mare → la línia de la 02 és
        acta d'una mesura que ja no existeix i s'ha de retirar."""
        with comportes_garment_alcades(*TAULES):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, garment=MARE)
            PieceFittingLine.objects.create(
                piece_fitting=self.pf, pom=self.pom, size_label='M',
                valor_teoric=50.0, valor_real=50.0, garment=SEGONA)

            res = reconcilia_linies(self.pf)

            self.assertEqual(res['retirades'], 1)
            self.assertEqual(self._linies(), [(MARE, 'M', 100.0)])

    def test_una_linia_que_JA_hi_es_no_es_duplica(self):
        """`ja_hi_son` també ha de parlar de la peça: si no, la línia de la 02 existent no es
        reconeix i se'n crea una segona que xoca amb la unicitat de sis camps."""
        with comportes_garment_alcades(*TAULES):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, garment=MARE)
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=50.0, ordre=2, garment=SEGONA)
            PieceFittingLine.objects.create(
                piece_fitting=self.pf, pom=self.pom, size_label='M',
                valor_teoric=50.0, valor_real=50.0, garment=SEGONA)

            res = reconcilia_linies(self.pf)

            self.assertEqual((res['creades'], res['retirades']), (1, 0))
            self.assertEqual(self._linies(), [(MARE, 'M', 100.0), (SEGONA, 'M', 50.0)])


class CasDeControlUnaSolaPecaTest(_T5cBase):
    """El 100% del corpus d'avui. Ha de comportar-se EXACTAMENT com abans de T5c."""

    def test_un_model_duna_sola_peca_reconcilia_igual_que_sempre(self):
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1)

        res = reconcilia_linies(self.pf)

        self.assertEqual((res['creades'], res['retirades'], res['congelada']), (1, 0, False))
        self.assertEqual(self._linies(), [(MARE, 'M', 100.0)])

    def test_una_segona_passada_no_crea_ni_esborra_res(self):
        """Idempotència: és la propietat que fa que obrir una presa dos cops sigui inofensiu."""
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1)
        reconcilia_linies(self.pf)

        res = reconcilia_linies(self.pf)

        self.assertEqual((res['creades'], res['retirades']), (0, 0))
        self.assertEqual(self._linies(), [(MARE, 'M', 100.0)])

    def test_una_sessio_segellada_no_es_toca(self):
        """L'acta no es reescriu, i el garment no hi canvia res."""
        self.session.estat = 'Tancada'
        self.session.save(update_fields=['estat'])
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1)

        res = reconcilia_linies(self.pf)

        self.assertTrue(res['congelada'])
        self.assertEqual(self._linies(), [])
