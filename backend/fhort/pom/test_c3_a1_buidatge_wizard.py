"""C3-A1 — el buidatge del wizard respecta la germana i deixa rastre.

`save_base_size_view` buidava el valor amb `BaseMeasurement.objects.filter(model, pom_id)
.update(base_value_cm=None)`: un filtre CEC als dos eixos, per `.update()` de queryset i sense
cap transacció al fitxer. Era l'únic escriptor de `BaseMeasurement` de tot el backend que no
sabia dir de quina capa ni de quina instància parlava (DIAGNOSI_MOTOR_DERIVACIO_C3 §A9.4).

Amb les comportes tancades el defecte és INVERIFICABLE: totes les files són ('exterior', ''),
el filtre cec i el complet seleccionen el mateix conjunt, i qualsevol test passaria abans i
després del canvi sense dir res. Per això aquest fitxer alça la comporta per a UNA taula dins
d'un savepoint que sempre es desfà — el mateix patró que `test_lectors_capa_onada1.py:36-52`,
i per la mateixa raó: provar el que el fumeig no pot provar.

DDL transaccional: a Postgres un `ALTER TABLE … DROP CONSTRAINT` es desfà amb el savepoint
igual que un INSERT. El test no deixa rastre, i l'últim mètode ho verifica llegint el catàleg.

C4/G1-G4 (04/08) JA les ha retirades: el `with comportes_alcades(...)` és un no-op i els asserts es
queden tal com estan.

Convenció del repo: `python manage.py test fhort.pom` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import BaseMeasurement, MeasurementChangeLog, Model
from fhort.pom.models import MeasurementLayer, POMMaster
from fhort.pom.wizard_views import save_base_size_view

FOLRE = 'folre'
ESQUERRA = 'left'


#: Les DUES taules que cal alçar alhora per escriure una germana. No és una comoditat:
#: crear una `BaseMeasurement` de folre dispara el signal F1, que estampa la capa de la
#: instància al `MeasurementChangeLog` (signals.py:274-275, :322-323) — i aquella taula porta
#: la SEVA comporta. Alçar-ne només una fa petar el test amb un CheckViolation del changelog
#: que no té res a veure amb el que es prova. La cadena de mesura en té nou, de comportes;
#: aquestes dues són les que toca aquest camí.
TAULES_DEL_CAMI = ('models_app_basemeasurement', 'models_app_measurementchangelog')


@contextlib.contextmanager
def comportes_alcades(*taules, eixos=('capa_gate_c1',)):
    """Alça les comportes de `taules` dins d'un savepoint que SEMPRE es desfà.

    El `finally` no és decoratiu: si un assert peta a dins, les comportes han de tornar igual.
    """
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                for sufix in eixos:
                    # `IF EXISTS` — C4/G1-G4 (04/08) han retirat les 40 comportes: alçar-ne
                    # una que ja no hi és és el mateix estat, i el `finally` retorna igual.
                    cur.execute(
                        f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                        f'DROP CONSTRAINT IF EXISTS "{taula}_{sufix}"'
                    )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class BuidatgeWizardC3A1Test(TenantTestCase):

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
            codi_intern='TST-C3A1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        # `get_or_create` i no `create`: l'usuari d'auth viu al schema COMPARTIT i sobreviu al
        # rollback de cada test (mateix motiu que a test_lectors_capa_onada1.py).
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_c3a1', defaults={'email': 'qa@c3a1.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA C3-A1', 'rol_nom': 'QA'})
        # La vista exigeix un SizeFitting numero=1. `get_or_create` i no `create`: un signal ja
        # en crea un en néixer el Model, i crear-lo a seques és exactament la col·lisió
        # `fitting_sizefitting_model_id_numero` que té 53 tests de la suite en vermell des del
        # 28/07. Aquest test no hi entra.
        from fhort.fitting.models import SizeFitting
        SizeFitting.objects.get_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-C3A1', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.perfil},
        )
        self.factory = APIRequestFactory()

    def _buida(self, pom_id):
        """Crida la vista real demanant el buidatge del POM (valor 0 = buidar)."""
        request = self.factory.post(
            f'/api/v1/models/{self.model.pk}/guardar-talla-base/',
            {'poms': [{'pom_id': pom_id, 'valor_cm': 0}]}, format='json')
        force_authenticate(request, user=self.user)
        return save_base_size_view(request, self.model.pk)

    # ── L'eix CAPA ───────────────────────────────────────────────────────────────────

    def test_buidar_lexterior_no_buida_el_folre(self):
        """El cas que el filtre cec es menjava: dues capes, i només se'n buida una."""
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-EXT')
            fol = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=98.0, ordre=2,
                nom_fitxa='A-FOL', capa=FOLRE)

            resp = self._buida(self.pom.pk)
            self.assertEqual(resp.status_code, 200)

            ext.refresh_from_db()
            fol.refresh_from_db()
            self.assertIsNone(ext.base_value_cm, "l'exterior és el que s'havia de buidar")
            self.assertEqual(fol.base_value_cm, 98.0,
                             'el folre NO es toca: el filtre cec se n\'enduia el valor')

    def test_buidar_lexterior_no_buida_la_instancia(self):
        """Mateix defecte, segon eix: la sisa esquerra no és la mesura única."""
        with comportes_alcades(*TAULES_DEL_CAMI,
                               eixos=('capa_gate_c1', 'instancia_gate_cins')):
            ext = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-EXT')
            esq = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=40.0, ordre=2,
                nom_fitxa='A-ESQ', instancia=ESQUERRA)

            self._buida(self.pom.pk)

            ext.refresh_from_db()
            esq.refresh_from_db()
            self.assertIsNone(ext.base_value_cm)
            self.assertEqual(esq.base_value_cm, 40.0,
                             'la instància esquerra NO es toca')

    # ── El rastre ────────────────────────────────────────────────────────────────────

    def test_el_buidatge_deixa_entrada_al_changelog(self):
        """El `.update()` de queryset no disparava cap signal: el valor desapareixia mut."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A-EXT')

        self.assertEqual(MeasurementChangeLog.objects.filter(model=self.model).count(), 1,
                         'la creació de la mesura ja deixa la seva entrada')

        self._buida(self.pom.pk)

        logs = MeasurementChangeLog.objects.filter(model=self.model).order_by('id')
        self.assertEqual(logs.count(), 2, 'el buidatge ha de deixar la SEVA entrada')
        log = logs.last()
        self.assertEqual(log.valor_anterior, 100.0,
                         "valor_anterior ha de dir el valor que es perd, no None: "
                         "None en aquesta taula vol dir «és una creació» (models.py:842)")
        self.assertEqual(log.valor_nou, 0.0)
        self.assertEqual(log.capa, MeasurementLayer.SLUG_DEFECTE)
        self.assertEqual(log.instancia, '')
        self.assertEqual(log.base_measurement_id, bm.pk)
        self.assertEqual(log.created_by_id, self.user.pk)

    def test_el_changelog_del_buidatge_parla_de_la_SEVA_germana(self):
        """Una entrada mal atribuïda no es pot corregir: la taula és append-only."""
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-EXT')
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=98.0, ordre=2,
                nom_fitxa='A-FOL', capa=FOLRE)

            self._buida(self.pom.pk)

            log = (MeasurementChangeLog.objects
                   .filter(model=self.model, valor_nou=0.0).order_by('id').last())
            self.assertEqual(log.capa, MeasurementLayer.SLUG_DEFECTE)
            self.assertEqual(log.base_measurement_id, ext.pk)
            self.assertEqual(log.valor_anterior, 100.0,
                             'ha de dir 100 (exterior), no 98 (folre)')

    # ── No-regressió del camí feliç ──────────────────────────────────────────────────

    def test_buidar_un_pom_sense_fila_no_peta_ni_compta(self):
        resp = self._buida(self.pom.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['eliminats'], 0)

    def test_buidar_una_fila_ja_buida_no_duplica_rastre(self):
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=None, ordre=1, origen='TEMPLATE')
        n_abans = MeasurementChangeLog.objects.filter(model=self.model).count()

        resp = self._buida(self.pom.pk)

        self.assertEqual(resp.data['eliminats'], 1, 'la fila existeix: es compta com abans')
        self.assertEqual(MeasurementChangeLog.objects.filter(model=self.model).count(), n_abans,
                         'però no hi havia cap valor a perdre: cap entrada nova')

    def test_el_harness_no_deixa_rastre(self):
        """Deia que el DDL del harness s'havia desfet i que la comporta tornava a barrar la
        segona capa. C4/G1-G4 les han retirades: ja no n'hi ha cap per tornar, i el que es
        vigila és que el harness deixi l'esquema EXACTAMENT com el va trobar."""
        def noms_de_check():
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT conname FROM pg_constraint c "
                    "JOIN pg_namespace n ON n.oid = c.connamespace "
                    "WHERE n.nspname = %s AND c.contype = 'c'",
                    [connection.schema_name])
                return {row[0] for row in cur.fetchall()}

        abans = noms_de_check()
        with comportes_alcades(*TAULES_DEL_CAMI):
            pass

        self.assertEqual(noms_de_check(), abans, 'el harness ha canviat l\'esquema')
        self.assertEqual(
            {c for c in abans if c.endswith(('_capa_gate_c1', '_instancia_gate_cins'))},
            set(), 'una comporta ha sobreviscut a C4')
