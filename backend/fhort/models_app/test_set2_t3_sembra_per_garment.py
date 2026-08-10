"""SET-2/T3 — LA SEMBRA DE REGLES ÉS PER PEÇA, NO PER MODEL.

Aquest arnès vigila la meitat de T3 que no es veu a l'esquema. Obrir la clau de
`ModelGradingRule` a `('model','pom','garment')` no serveix de res si la sembra segueix
esborrant per MODEL: la clau deixaria conviure les regles de dues peces i el wipe les
tornaria a matar a la crida següent.

ELS DOS MALS QUE VIGILA, i eren de gravetat diferent:

  1. **DESTRUCTIU I SILENCIÓS** — el wipe era `model.grading_rules.all().delete()`. Sembrar
     la calceta esborrava les regles del top, de manera que l'última peça sembrada era
     l'única que en tenia. Ningú petava; el model simplement es quedava mig graduat.

  2. **IMMEDIAT** — `bulk_create` no porta conflict-handling, i amb la clau vella
     `('model','pom')` dues peces que compartissin un POM petaven amb `IntegrityError`
     abans i tot d'arribar al primer mal.

El test alça la comporta `_garment_gate_set2` dins d'un savepoint que sempre es desfà (el
patró de `test_lectors_capa_onada1`), perquè amb la comporta viva cap fila '02' pot existir
i els dos mals són inobservables.
"""
import contextlib
import datetime
from types import SimpleNamespace

from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import Model, ModelGradingRule
from fhort.models_app.services import materialize_model_grading_rules
from fhort.pom.models import POMMaster

MARE = ''
SEGONA = '02'
TAULA = 'models_app_modelgradingrule'


@contextlib.contextmanager
def comporta_garment_alcada(*taules):
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


class SembraPerGarmentTest(TenantTestCase):

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
            codi_intern='TST-T3', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def _regla_font(self, increment):
        """Una `GradingRule`-like: la sembra només en llegeix atributs."""
        return SimpleNamespace(
            pom_id=self.pom.id, logica='LINEAR', increment=increment, valors_step=None,
            increment_base=None, increment_break=None, talla_break_label=None,
            talla_break_pos=None, rule_set_id=None,
        )

    def test_sembrar_una_peca_no_esborra_les_regles_de_l_altra(self):
        """El mal destructiu: sembrar la calceta esborrava el top sencer, sense petar."""
        with comporta_garment_alcada(TAULA):
            materialize_model_grading_rules(
                self.model, [self._regla_font(1.0)], 'CANONICAL', garment=MARE)
            materialize_model_grading_rules(
                self.model, [self._regla_font(2.5)], 'CANONICAL', garment=SEGONA)

            per_garment = {
                r.garment: float(r.increment)
                for r in ModelGradingRule.objects.filter(model=self.model)
            }
            self.assertEqual(
                per_garment, {MARE: 1.0, SEGONA: 2.5},
                'sembrar una peça ha esborrat o trepitjat les regles de l\'altra')

    def test_dues_peces_poden_compartir_un_POM_amb_lleis_DIFERENTS(self):
        """La decisió D4, feta observable: el mateix POM, dues peces, dos increments.

        Amb la clau vella això era un `IntegrityError`; amb l'acta vella, una impossibilitat
        de domini. És exactament el que la reobertura havia de fer possible.
        """
        with comporta_garment_alcada(TAULA):
            materialize_model_grading_rules(
                self.model, [self._regla_font(1.0)], 'CANONICAL', garment=MARE)
            materialize_model_grading_rules(
                self.model, [self._regla_font(2.5)], 'CANONICAL', garment=SEGONA)

            self.assertEqual(
                ModelGradingRule.objects.filter(model=self.model, pom=self.pom).count(), 2)

    def test_re_sembrar_la_MATEIXA_peca_segueix_sent_idempotent(self):
        """EL CAS DE CONTROL, i el que prova que el filtre no talla de més.

        El wipe s'ha fet més estret, no s'ha suprimit: re-sembrar la mare ha de continuar
        substituint les SEVES regles i no acumular-ne. Si això caigués, el símptoma seria
        duplicats a la peça mare —el camí de tothom avui— i no ho veuria ningú fins que la
        clau petés.
        """
        with comporta_garment_alcada(TAULA):
            materialize_model_grading_rules(
                self.model, [self._regla_font(1.0)], 'CANONICAL', garment=MARE)
            materialize_model_grading_rules(
                self.model, [self._regla_font(9.0)], 'CANONICAL', garment=MARE)

            regles = ModelGradingRule.objects.filter(model=self.model, garment=MARE)
            self.assertEqual(regles.count(), 1, 're-sembrar la mare ha acumulat regles')
            self.assertEqual(float(regles.first().increment), 9.0)
