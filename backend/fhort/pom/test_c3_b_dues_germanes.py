"""C3-B — dues germanes del mateix POM produeixen DUES files graduades completes.

Aquesta és la prova que abans no existia i que, fins a la Fase B, era impossible d'escriure:
`_load_base_measurements` indexava per `pom_id` sol, de manera que dues files germanes del
mateix POM entraven al dict amb la mateixa clau i l'última llegida guanyava. La perdedora no
perdia una cel·la — perdia la fila graduada SENCERA, sense excepció, sense log i sense rastre.

Amb les comportes de C1/C1-ins tancades el cas no es pot ni construir: totes les files són
('exterior', ''). Per això aquests tests alcen les comportes dins d'un savepoint que sempre es
desfà (patró `test_lectors_capa_onada1.py:36-52`, autoritzat expressament per a aquesta feina).
Fora d'aquest patró no s'hi fa cap DDL.

S'alcen TRES taules i no una, i cadascuna per un motiu propi:
  · `models_app_basemeasurement`      — per poder escriure la germana.
  · `models_app_measurementchangelog` — el signal F1 estampa la capa de la fila que s'escriu,
                                        i aquella taula porta la seva pròpia comporta.
  · `fitting_gradedspec`              — és ON HA D'ATERRAR el resultat: sense alçar-la, el
                                        motor calcularia bé i Postgres refusaria l'escriptura.

C4/G1-G4 (04/08) JA les ha retirades: el `with comportes_alcades(...)` és un no-op i els asserts es
queden tal com estan.

Convenció del repo: `python manage.py test fhort.pom` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.pom.models import MeasurementLayer, POMMaster, SizeDefinition, SizeSystem
from fhort.pom.services import (_load_base_measurements, generate_graded_specs,
                                preview_graded_specs)

FOLRE = 'folre'
ESQUERRA = 'left'
EXTERIOR = MeasurementLayer.SLUG_DEFECTE

#: Les tres taules del camí de graduació que porten comporta. V. el docstring del mòdul.
TAULES_DEL_CAMI = ('models_app_basemeasurement', 'models_app_measurementchangelog',
                   'fitting_gradedspec')


@contextlib.contextmanager
def comportes_alcades(*taules, eixos=('capa_gate_c1',)):
    """Alça les comportes de `taules` dins d'un savepoint que SEMPRE es desfà."""
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


class DuesGermanesC3BTest(TenantTestCase):

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
        self.ss = SizeSystem.objects.create(codi='SS_C3B', nom='SS C3-B', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='TST-C3B', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_c3b', defaults={'email': 'qa@c3b.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA C3-B', 'rol_nom': 'QA'})
        # `get_or_create`: un signal ja crea l'SF numero=1 en néixer el Model. Crear-lo a
        # seques és la col·lisió `fitting_sizefitting_model_id_numero` que té 53 tests de la
        # suite en vermell des del 28/07.
        from fhort.fitting.models import SizeFitting
        self.sf, _ = SizeFitting.objects.get_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-C3B', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.perfil},
        )
        # LINEAR +1: la fila d'una germana és base-1 · base · base+1. Amb dues germanes
        # separades per 2 cm, cap cel·la de l'una coincideix amb cap de l'altra — si el motor
        # les col·lapsés, l'assert no fallaria per un decimal sinó per files senceres.
        ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='LINEAR', increment=1.0, actiu=True)

    def _germanes_de_capa(self):
        ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A-EXT')
        fol = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=98.0, ordre=2, nom_fitxa='A-FOL',
            capa=FOLRE)
        return ext, fol

    def _specs(self):
        from fhort.fitting.models import GradedSpec
        from fhort.fitting.services import vigent_grading_version
        gv = vigent_grading_version(self.sf.pk)
        return {(s.capa, s.instancia, s.size_label): s.graded_value_cm
                for s in GradedSpec.objects.filter(grading_version=gv, pom=self.pom,
                                                   is_active=True)}

    # ── EL VERD (b) DE LA FASE B ─────────────────────────────────────────────────────

    def test_dues_capes_produeixen_DUES_files_graduades_completes(self):
        with comportes_alcades(*TAULES_DEL_CAMI):
            self._germanes_de_capa()

            n = generate_graded_specs(self.sf.pk)

            self.assertEqual(n, 6, '2 germanes × 3 talles = 6 cel·les, no 3')
            self.assertEqual(self._specs(), {
                (EXTERIOR, '', 'S'): 99.0,
                (EXTERIOR, '', 'M'): 100.0,
                (EXTERIOR, '', 'L'): 101.0,
                (FOLRE, '', 'S'): 97.0,
                (FOLRE, '', 'M'): 98.0,
                (FOLRE, '', 'L'): 99.0,
            }, 'cada germana ha de portar la SEVA fila sencera, amb els seus eixos')

    def test_dues_instancies_produeixen_DUES_files_graduades_completes(self):
        """Segon eix, mateix mecanisme: la sisa esquerra no és la mesura única."""
        with comportes_alcades(*TAULES_DEL_CAMI,
                               eixos=('capa_gate_c1', 'instancia_gate_cins')):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-EXT')
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=40.0, ordre=2,
                nom_fitxa='A-ESQ', instancia=ESQUERRA)

            n = generate_graded_specs(self.sf.pk)

            self.assertEqual(n, 6)
            self.assertEqual(self._specs(), {
                (EXTERIOR, '', 'S'): 99.0,
                (EXTERIOR, '', 'M'): 100.0,
                (EXTERIOR, '', 'L'): 101.0,
                (EXTERIOR, ESQUERRA, 'S'): 39.0,
                (EXTERIOR, ESQUERRA, 'M'): 40.0,
                (EXTERIOR, ESQUERRA, 'L'): 41.0,
            })

    def test_el_loader_ja_no_col·lapsa_les_germanes(self):
        """El node mestre, directament: dues files → dues entrades, no una."""
        with comportes_alcades(*TAULES_DEL_CAMI):
            self._germanes_de_capa()

            bases = _load_base_measurements(self.model.pk)

            self.assertEqual(bases, {
                (self.pom.pk, EXTERIOR, ''): 100.0,
                (self.pom.pk, FOLRE, ''): 98.0,
            }, 'la clau és la identitat sencera; abans això era {pom_id: 98.0}')

    def test_el_preview_diu_el_mateix_que_el_generador_amb_germanes(self):
        """La invariant que obliga les dues fronteres a créixer alhora, amb dues germanes."""
        with comportes_alcades(*TAULES_DEL_CAMI):
            self._germanes_de_capa()

            preview = preview_graded_specs(self.model, _load_base_measurements(self.model.pk))
            generate_graded_specs(self.sf.pk)
            generat = self._specs()

            aplanat = {(capa, ins, talla): val
                       for (_pom, capa, ins), fila in preview.items()
                       for talla, val in fila.items()}
            self.assertEqual(aplanat, generat,
                             'preview i generador han de coincidir cel·la a cel·la')

    # ── Compatibilitat de B.5: l'entrada escalar segueix valent ─────────────────────

    def test_el_preview_accepta_la_clau_escalar_de_l_import(self):
        """`extraction_views` li passa JSON `{pom_id: valor}`, que no pot dir tuples."""
        preview = preview_graded_specs(self.model, {self.pom.pk: 100.0})

        self.assertEqual(preview, {(self.pom.pk, EXTERIOR, ''): {'S': 99.0, 'M': 100.0,
                                                                 'L': 101.0}},
                         "una clau escalar és la mesura única del POM: ('exterior', '')")

    def test_la_clau_escalar_i_la_completa_donen_el_MATEIX(self):
        escalar = preview_graded_specs(self.model, {self.pom.pk: 100.0})
        completa = preview_graded_specs(self.model, {(self.pom.pk, EXTERIOR, ''): 100.0})
        self.assertEqual(escalar, completa)

    # ── No-regressió: amb UNA sola mesura res no es mou ─────────────────────────────

    def test_amb_una_sola_mesura_el_resultat_es_el_de_sempre(self):
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A-EXT')

        n = generate_graded_specs(self.sf.pk)

        self.assertEqual(n, 3)
        self.assertEqual(self._specs(), {
            (EXTERIOR, '', 'S'): 99.0,
            (EXTERIOR, '', 'M'): 100.0,
            (EXTERIOR, '', 'L'): 101.0,
        })

    def test_el_harness_no_deixa_rastre(self):
        """Deia «18 comportes a la cadena de mesura» (9 taules × 2 eixos). C4/G1-G4 les han
        retirades i el 18 va quedar ranci — és una de les dues xifres fixes que han mossegat
        avui. El que segueix sent cert i es vigila: el harness deixa l'esquema EXACTAMENT com
        el va trobar, i cap comporta no ha sobreviscut."""
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
