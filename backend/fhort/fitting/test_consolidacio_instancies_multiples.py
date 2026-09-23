"""PATRÓ C (23/09) — consolidació fitting→base amb INSTÀNCIES MÚLTIPLES: un valor mesurat
mana sobre un de derivat.

EL BUG QUE ES REPARA (`consolidate_base_from_fitting`, `fitting/services.py`): la funció
escrivia cada línia mesurada I la derivava cap a les seves germanes EN EL MATEIX PAS, línia a
línia. Amb tres instàncies del mateix POM mesurades a la mateixa sessió de fitting (p.ex. B
relaxed + extended + seam, totes tres rectificades), la propagació d'una trepitjava el valor
acabat d'escriure d'una altra abans que li arribés el torn: qualsevol instància que NO fos la
darrera processada podia acabar amb `origen='DERIVAT'` i un valor que no era el que la modista
havia mesurat.

LA LLEI (Agus, Patró C): un valor MESURAT mana sobre un de DERIVAT. Es recullen primer TOTS
els valors mesurats de la sessió i s'escriuen; la derivació NOMÉS toca després les germanes
que no formen part d'aquest conjunt — i l'ordre de procés (determinista, per POM/capa/
instància) deixa de poder canviar el resultat.

Convenció del repo: `python manage.py test fhort.fitting` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.fitting.models import (FittingSession, GradingVersion, PieceFitting,
                                  PieceFittingLine, SizeFitting)
from fhort.fitting.services import consolidate_base_from_fitting
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import POMMaster

RELAXED, EXTENDED, SEAM = 'relaxed', 'extended', 'seam'


@contextlib.contextmanager
def comportes_alcades(*taules, eixos=('capa_gate_c1', 'instancia_gate_cins')):
    """V. `models_app/test_c3_e_connexio_derivacio.py` — mateix mecanisme, mateix motiu:
    sense alçar la comporta d'instància, `germanes_de` no troba mai cap germana i el test
    seria un no-op silenciós."""
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            cur.execute('SET CONSTRAINTS ALL IMMEDIATE')
            for taula in taules:
                for sufix in eixos:
                    cur.execute(
                        f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                        f'DROP CONSTRAINT IF EXISTS "{taula}_{sufix}"'
                    )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class _BaseInstanciesMultiples(TenantTestCase):

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
        self.pom = POMMaster.objects.create(codi_client='B', nom_client='Cintura')
        self.model = Model.objects.create(
            codi_intern='TST-PATC', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_patc', defaults={'email': 'qa@patc.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA Patró C', 'rol_nom': 'QA'})

    def _tres_instancies(self, relaxed=40.0, extended=42.0, seam=41.0):
        """Tres germanes d'INSTÀNCIA (mateixa capa, mateix POM): folgances 2.0 i 1.0, que
        ningú no declara enlloc — es comproven per RESTA, com a C3-E."""
        b_rel = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=relaxed, instancia=RELAXED,
            ordre=1, nom_fitxa='B-REL')
        b_ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=extended, instancia=EXTENDED,
            ordre=2, nom_fitxa='B-EXT')
        b_seam = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=seam, instancia=SEAM,
            ordre=3, nom_fitxa='B-SEAM')
        return b_rel, b_ext, b_seam

    def _sessio(self):
        sf = SizeFitting.objects.create(model=self.model, numero=2, codi='TST-SF-PATC',
                                        tipus='PROTO', creat_per=self.perfil)
        gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                           version_number=1, creat_per=self.perfil)
        sessio = FittingSession.objects.create(
            model=self.model, fase=self.model.fase_actual, data=datetime.date(2026, 9, 23))
        return PieceFitting.objects.create(session=sessio, model=self.model, grading_version=gv)

    def _linia(self, pf, instancia, teoric, real, presa_at=None):
        return PieceFittingLine.objects.create(
            piece_fitting=pf, pom=self.pom, size_label='M', capa='exterior',
            instancia=instancia, valor_teoric=teoric, valor_real=real, presa_at=presa_at)


class TresInstanciesMesuradesTest(_BaseInstanciesMultiples):
    """Cas 1 — les TRES instàncies del mateix POM rectificades a la mateixa sessió: cap pot
    trepitjar les altres dues."""

    def test_cada_instancia_conserva_el_seu_valor_mesurat(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)   # +4
            self._linia(pf, EXTENDED, 42.0, 43.0)  # +1
            self._linia(pf, SEAM, 41.0, 41.5)      # +0.5

            consolidate_base_from_fitting(pf, auth_user=self.user)

            b_rel.refresh_from_db(); b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_rel.base_value_cm, 44.0)
            self.assertEqual(b_ext.base_value_cm, 43.0)
            self.assertEqual(b_seam.base_value_cm, 41.5)
            self.assertEqual(b_rel.origen, 'FITTED')
            self.assertEqual(b_ext.origen, 'FITTED',
                             "l'extended té mesura pròpia: la propagació de relaxed NO la toca")
            self.assertEqual(b_seam.origen, 'FITTED',
                             "la seam té mesura pròpia: la propagació de cap altra la toca")


class UnaMesuradaDuesDerivadesTest(_BaseInstanciesMultiples):
    """Cas 2 — NOMÉS relaxed es mesura; extended i seam no tenen línia a la sessió i han de
    rebre la propagació de relaxed."""

    def test_les_dues_no_mesurades_reben_lincrement_de_la_mesurada(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)   # +4, únic mesurat

            consolidate_base_from_fitting(pf, auth_user=self.user)

            b_rel.refresh_from_db(); b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_rel.base_value_cm, 44.0)
            self.assertEqual(b_rel.origen, 'FITTED')
            self.assertEqual(b_ext.base_value_cm, 46.0, 'derivat: 42.0 + 4')
            self.assertEqual(b_ext.origen, 'DERIVAT')
            self.assertEqual(b_seam.base_value_cm, 45.0, 'derivat: 41.0 + 4')
            self.assertEqual(b_seam.origen, 'DERIVAT')


class OrdreInversTest(_BaseInstanciesMultiples):
    """Cas 3 — mateix escenari que el cas 1 però amb les línies creades en ordre invers
    (seam abans que relaxed): el resultat ha de ser IDÈNTIC, perquè la llei ja no depèn de
    l'ordre de procés un cop el conjunt mesurat es calcula abans de derivar cap."""

    def test_lordre_de_creacio_no_altera_el_resultat(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            # Creades EN ORDRE INVERS de com les processaria un `pk` ascendent qualsevol.
            self._linia(pf, SEAM, 41.0, 41.5)
            self._linia(pf, EXTENDED, 42.0, 43.0)
            self._linia(pf, RELAXED, 40.0, 44.0)

            consolidate_base_from_fitting(pf, auth_user=self.user)

            b_rel.refresh_from_db(); b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_rel.base_value_cm, 44.0)
            self.assertEqual(b_ext.base_value_cm, 43.0)
            self.assertEqual(b_seam.base_value_cm, 41.5)
            self.assertEqual(b_rel.origen, 'FITTED')
            self.assertEqual(b_ext.origen, 'FITTED')
            self.assertEqual(b_seam.origen, 'FITTED')


class InstanciaMesuradaSenseDesviacioTest(_BaseInstanciesMultiples):
    """Cas 4 (LLEI Agus 24/09, cas 2578) — `seam` es mesura IGUAL al teòric (sense
    desviació, `decisio` buida, però `presa_at` informat: el gest de confirmar-la és seu):
    és tan «mesurada» com `relaxed`/`extended`, i la seva propagació NO l'ha de trepitjar
    encara que ella mateixa no escrigui res de nou."""

    def test_la_no_desviada_no_es_trepitjada_per_les_altres_dues(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)   # +4, rectificada
            self._linia(pf, EXTENDED, 42.0, 43.0)  # +1, rectificada
            # mesurada i CONFIRMADA (presa_at informat), SENSE desviació, decisio buida —
            # `linia_te_contingut` la compta per `presa_at`, no per un valor que no canvia.
            self._linia(pf, SEAM, 41.0, 41.0, presa_at=timezone.now())

            consolidate_base_from_fitting(pf, auth_user=self.user)

            b_rel.refresh_from_db(); b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_rel.base_value_cm, 44.0)
            self.assertEqual(b_ext.base_value_cm, 43.0)
            self.assertEqual(b_seam.base_value_cm, 41.0,
                             'mesurada i confirmada: cap propagació de relaxed/extended la mou')
            self.assertEqual(b_seam.origen, 'FITTED',
                             'mesurada, no derivada — encara que el valor no hagi canviat')

    def test_confirmada_repara_un_origen_derivat_previ(self):
        """Si `seam` arribava DERIVAT (trepitjada d'una sessió anterior, abans del fix), una
        nova confirmació mesurada l'ha de tornar a FITTED amb el valor correcte."""
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            b_seam.base_value_cm = 45.0   # valor trepitjat, com deixaria el bug pre-a8575ec4
            b_seam.origen = 'DERIVAT'
            b_seam.save(update_fields=['base_value_cm', 'origen'])
            pf = self._sessio()
            self._linia(pf, SEAM, 41.0, 41.0, presa_at=timezone.now())  # confirmada de nou

            consolidate_base_from_fitting(pf, auth_user=self.user)

            b_seam.refresh_from_db()
            self.assertEqual(b_seam.base_value_cm, 41.0)
            self.assertEqual(b_seam.origen, 'FITTED')
