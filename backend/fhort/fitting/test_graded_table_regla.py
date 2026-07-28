"""graded-table exposa LA REGLA per fila — l'increment PER SALT i el break DECLARAT.

Per què cal: `deltas` (increment_applied_cm) és la distància ACUMULADA a la base
(`patterns/engine/ports.py:64`, `grading_projection.py:29`). Pintar-lo com si fos el pas
dona un múltiple enter erroni que depèn de quantes talles hi ha sota la base i de l'ordre
en què arriben — el defecte que la DIAGNOSI_DELTA_T1A va traçar al model 163 (Δ −4 quan la
regla diu 2) i al 166 (Δ +8, mateixa regla, ordre invers).

El que es fixa aquí és que la font declarada viatja al payload i que NO depèn de l'ordre
del document: `increment_base` és de la regla, no del resultat.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.graded_spec_views import GradedSpecTableView
from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.pom.models import (
    GradingRule, GradingRuleSet, POMMaster, SizeDefinition, SizeSystem,
)

# Run de 5 amb la base al mig: DUES talles per sota, la configuració que feia que el Δ
# pintat fos −2× l'increment real (cas TATE).
RUN = ['XXS', 'XS', 'S', 'M', 'L']
BASE = 'S'


class GradedTableReglaTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='tester')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Tester', 'rol_nom': 'admin'})

        self.ss = SizeSystem.objects.create(codi='SS_T', nom='SS test', base_unit='ALPHA')
        self.talles = {sl: SizeDefinition.objects.create(size_system=self.ss, etiqueta=sl, ordre=i)
                       for i, sl in enumerate(RUN)}
        self.rs = GradingRuleSet.objects.create(nom='RS test')
        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest width')

        self.model = Model.objects.create(
            codi_intern='TST-1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='·'.join(RUN), base_size_label=BASE,
            grading_rule_set=self.rs,
        )
        BaseMeasurement.objects.create(model=self.model, pom=self.pom, ordre=1, base_value_cm=47)

        self.sf = SizeFitting.objects.filter(model=self.model).first()
        self.gv = GradingVersion.objects.create(
            size_fitting=self.sf, version_number=1, is_active=True, creat_per=self.profile)

        self.factory = APIRequestFactory()
        self.view = GradedSpecTableView.as_view()

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _regla_ruleset(self, increment, break_label=None, increment_break=None, logica='LINEAR'):
        return GradingRule.objects.create(
            rule_set=self.rs, pom=self.pom, talla_base=self.talles[BASE], logica=logica,
            increment_base=increment, talla_break_label=break_label,
            increment_break=increment_break,
        )

    def _specs(self, ordre=RUN, increment=2.0):
        """Specs coherents amb una LINEAR d'`increment`: la base a 47 i ±increment per salt.
        `ordre` és l'ordre d'ALTA — és el que fixa l'ordre d'aparició de `size_labels`.
        """
        base_idx = RUN.index(BASE)
        for sl in ordre:
            salts = RUN.index(sl) - base_idx
            GradedSpec.objects.create(
                grading_version=self.gv, pom=self.pom, size_label=sl,
                graded_value_cm=47 + salts * increment,
                increment_applied_cm=salts * increment,
                grading_type_applied='LINEAR', is_active=True,
            )

    def _get(self):
        req = self.factory.get('/graded-table/')
        force_authenticate(req, user=self.user)
        return self.view(req, sf_id=self.sf.id)

    # ── G4.1 · LINEAR 2.0, base S, run de 5 → Δ '+2' a totes les files, Break buit ──
    def test_linear_increment_per_salt_i_break_buit(self):
        self._regla_ruleset(2.0)
        self._specs()
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        fila = resp.data['rows'][0]

        # La regla declarada, no el resultat acumulat.
        self.assertEqual(fila['increment_base'], 2.0)
        self.assertEqual(fila['talla_break_label'], '')
        self.assertEqual(fila['logica'], 'LINEAR')

        # I el que enganyava: l'acumulat de la 1a talla no-base val −4, DOS salts sota la base.
        self.assertEqual(fila['deltas']['XXS'], -4.0)
        self.assertNotEqual(fila['deltas']['XXS'], fila['increment_base'])

    # ── G4.2 · regla amb break declarat → Break = l'etiqueta de la regla ──
    def test_break_declarat_viatja_tal_qual(self):
        self._regla_ruleset(2.0, break_label='M', increment_break=3.0)
        self._specs()
        fila = self._get().data['rows'][0]
        self.assertEqual(fila['talla_break_label'], 'M')
        self.assertEqual(fila['increment_base'], 2.0)

    # ── G4.3 · camí F1: ModelGradingRule resident → mateixa lectura ──
    def test_regla_resident_mateixa_lectura(self):
        # Ruleset amb una regla DIFERENT: la resident ha de manar (prioritat de
        # _load_grading_rules), que és el que fa el motor.
        self._regla_ruleset(9.9)
        ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='LINEAR',
            increment_base=2.0, talla_break_label='M', actiu=True,
        )
        self._specs()
        fila = self._get().data['rows'][0]
        self.assertEqual(fila['increment_base'], 2.0)      # la resident, no el 9.9 del ruleset
        self.assertEqual(fila['talla_break_label'], 'M')

    # ── G4.4 · ordre invers de size_labels (cas model 166) → Δ IDÈNTIC ──
    def test_ordre_invers_del_document_no_mou_lincrement(self):
        self._regla_ruleset(2.0)
        self._specs(ordre=list(reversed(RUN)))
        d = self._get().data
        fila = d['rows'][0]

        # El document serveix les talles a l'inrevés…
        self.assertEqual(d['size_labels'], list(reversed(RUN)))
        # …i la 1a talla no-base passa a ser L, amb acumulat +4 (el 166 pintava +8 per això).
        self.assertEqual(fila['deltas']['L'], 4.0)
        # …però la regla no es mou: sempre +2, positiva, independent de l'ordre.
        self.assertEqual(fila['increment_base'], 2.0)

    # ── Sense regla i règims sense increment: null, no un zero que menteixi ──
    def test_sense_regla_increment_null(self):
        self._specs()
        fila = self._get().data['rows'][0]
        self.assertIsNone(fila['increment_base'])
        self.assertEqual(fila['talla_break_label'], '')
        self.assertIsNone(fila['logica'])

    def test_step_sense_increment_base(self):
        self._regla_ruleset(None, logica='STEP')
        self._specs()
        fila = self._get().data['rows'][0]
        self.assertIsNone(fila['increment_base'])
        self.assertEqual(fila['logica'], 'STEP')

    # ── El payload existent NO es mou (altres consumidors depenen de `deltas`) ──
    def test_increment_applied_cm_segueix_al_payload(self):
        self._regla_ruleset(2.0)
        self._specs()
        fila = self._get().data['rows'][0]
        self.assertEqual(fila['deltas'],
                         {'XXS': -4.0, 'XS': -2.0, 'S': 0.0, 'M': 2.0, 'L': 4.0})
        self.assertEqual(fila['valors']['S'], 47)
