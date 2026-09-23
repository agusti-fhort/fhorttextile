"""REPARACIÓ 23/09, diagnosi 208 — `repara_base_des_de_fitting`.

Banc: el mateix escenari que `fitting/test_consolidacio_instancies_multiples.py`
(`UnaMesuradaDuesDerivadesTest`/`TresInstanciesMesuradesTest`) però ja CORROMPUT, com hauria
quedat abans del fix de COMMIT 1: dues `BaseMeasurement` germanes d'instància (extended, seam)
amb `origen='DERIVAT'` i un valor de propagació que NO és el que la modista va mesurar,
malgrat que hi ha una `PieceFittingLine` pròpia (decisio informat, `valor_real` rectificat) que
ho demostra. La comanda repara NOMÉS aquestes dues: `relaxed` ja és `origen='FITTED'` i no la
toca (guard: només `DERIVAT` amb mesura pròpia).

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.fitting.models import (FittingSession, GradingVersion, PieceFitting,
                                  PieceFittingLine, SizeFitting)
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import POMMaster

RELAXED, EXTENDED, SEAM = 'relaxed', 'extended', 'seam'


@contextlib.contextmanager
def comportes_alcades(*taules, eixos=('capa_gate_c1', 'instancia_gate_cins')):
    """V. `models_app/test_c3_e_connexio_derivacio.py` — mateix mecanisme."""
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


class ReparaBaseDesDeFittingTest(TenantTestCase):

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
            codi_intern='TST-REP208', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_rep208', defaults={'email': 'qa@rep208.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA Reparació', 'rol_nom': 'QA'})

    def _escenari_corromput(self):
        """3 germanes d'instància: `relaxed` correctament FITTED, `extended`/`seam` amb el
        valor de la trepitjada (DERIVAT) que el bug de commit 1 hauria pogut deixar."""
        b_rel = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=44.0, instancia=RELAXED,
            origen='FITTED', ordre=1, nom_fitxa='B-REL')
        b_ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=46.0, instancia=EXTENDED,
            origen='DERIVAT', ordre=2, nom_fitxa='B-EXT')
        b_seam = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=45.0, instancia=SEAM,
            origen='DERIVAT', ordre=3, nom_fitxa='B-SEAM')

        sf = SizeFitting.objects.create(model=self.model, numero=1, codi='TST-SF-REP208',
                                        tipus='PROTO', creat_per=self.perfil)
        gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                           version_number=1, creat_per=self.perfil)
        sessio = FittingSession.objects.create(
            model=self.model, fase=self.model.fase_actual, estat='Tancada',
            data=datetime.date(2026, 8, 2))
        pf = PieceFitting.objects.create(session=sessio, model=self.model, grading_version=gv)
        # La mesura pròpia que el bug va trepitjar: decisio informat i valor rectificat.
        PieceFittingLine.objects.create(
            piece_fitting=pf, pom=self.pom, size_label='M', capa='exterior',
            instancia=EXTENDED, valor_teoric=42.0, valor_real=43.0,
            decisio=PieceFittingLine.DECISIO_ADJUSTED)
        PieceFittingLine.objects.create(
            piece_fitting=pf, pom=self.pom, size_label='M', capa='exterior',
            instancia=SEAM, valor_teoric=41.0, valor_real=41.5,
            decisio=PieceFittingLine.DECISIO_ACCEPTED)
        return b_rel, b_ext, b_seam

    def test_dry_run_no_escriu_res(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            b_rel, b_ext, b_seam = self._escenari_corromput()
            out = StringIO()

            call_command('repara_base_des_de_fitting', f'--model={self.model.pk}', stdout=out)

            b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_ext.base_value_cm, 46.0, 'dry-run: cap escriptura')
            self.assertEqual(b_seam.base_value_cm, 45.0, 'dry-run: cap escriptura')
            sortida = out.getvalue()
            self.assertIn('DRY-RUN', sortida)
            self.assertIn(f'id={b_ext.pk}', sortida)
            self.assertIn(f'id={b_seam.pk}', sortida)

    def test_apply_repara_nomes_les_dues_derivades(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            b_rel, b_ext, b_seam = self._escenari_corromput()

            call_command('repara_base_des_de_fitting', f'--model={self.model.pk}', '--apply',
                        stdout=StringIO())

            b_rel.refresh_from_db(); b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_rel.base_value_cm, 44.0, 'ja era FITTED: no es toca')
            self.assertEqual(b_rel.origen, 'FITTED')
            self.assertEqual(b_ext.base_value_cm, 43.0, 'reparat amb el valor de la seva línia')
            self.assertEqual(b_ext.origen, 'FITTED')
            self.assertEqual(b_seam.base_value_cm, 41.5)
            self.assertEqual(b_seam.origen, 'FITTED')

    def test_idempotent_segona_passada_zero_canvis(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            self._escenari_corromput()
            call_command('repara_base_des_de_fitting', f'--model={self.model.pk}', '--apply',
                        stdout=StringIO())

            out2 = StringIO()
            call_command('repara_base_des_de_fitting', f'--model={self.model.pk}', '--apply',
                        stdout=out2)

            self.assertIn('0 fila', out2.getvalue())

    def test_no_toca_una_fila_que_no_es_derivat(self):
        """Guard: una BaseMeasurement STANDARD amb una línia candidata coincident no es toca —
        la comanda només considera `origen='DERIVAT'`."""
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            pom2 = POMMaster.objects.create(codi_client='C', nom_client='Maneguim')
            bm = BaseMeasurement.objects.create(
                model=self.model, pom=pom2, base_value_cm=30.0, instancia='',
                origen='STANDARD', ordre=1, nom_fitxa='C')
            sf = SizeFitting.objects.create(model=self.model, numero=1, codi='TST-SF-REP208B',
                                            tipus='PROTO', creat_per=self.perfil)
            gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                               version_number=1, creat_per=self.perfil)
            sessio = FittingSession.objects.create(
                model=self.model, fase=self.model.fase_actual, estat='Tancada',
                data=datetime.date(2026, 8, 2))
            pf = PieceFitting.objects.create(session=sessio, model=self.model, grading_version=gv)
            PieceFittingLine.objects.create(
                piece_fitting=pf, pom=pom2, size_label='M', capa='exterior', instancia='',
                valor_teoric=28.0, valor_real=32.0, decisio=PieceFittingLine.DECISIO_ADJUSTED)

            call_command('repara_base_des_de_fitting', f'--model={self.model.pk}', '--apply',
                        stdout=StringIO())

            bm.refresh_from_db()
            self.assertEqual(bm.base_value_cm, 30.0, 'STANDARD no és DERIVAT: no es toca')
            self.assertEqual(bm.origen, 'STANDARD')

    def test_repara_amb_candidata_sense_desviacio_ni_decisio(self):
        """Cas 2578 (LLEI Agus 24/09): la línia candidata pot NO tenir desviació
        (`valor_real == valor_teoric`) ni `decisio` informat i encara ha de servir per
        reparar una `BaseMeasurement` trepitjada — «mesurat» ja no exigeix cap de les dues."""
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            b_seam = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=45.0, instancia=SEAM,
                origen='DERIVAT', ordre=1, nom_fitxa='B-SEAM')
            sf = SizeFitting.objects.create(model=self.model, numero=1, codi='TST-SF-REP2578',
                                            tipus='PROTO', creat_per=self.perfil)
            gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                               version_number=1, creat_per=self.perfil)
            sessio = FittingSession.objects.create(
                model=self.model, fase=self.model.fase_actual, estat='Tancada',
                data=datetime.date(2026, 8, 2))
            pf = PieceFitting.objects.create(session=sessio, model=self.model, grading_version=gv)
            PieceFittingLine.objects.create(
                piece_fitting=pf, pom=self.pom, size_label='M', capa='exterior',
                instancia=SEAM, valor_teoric=41.0, valor_real=41.0)   # decisio='' (defecte)

            call_command('repara_base_des_de_fitting', f'--model={self.model.pk}', '--apply',
                        stdout=StringIO())

            b_seam.refresh_from_db()
            self.assertEqual(b_seam.base_value_cm, 41.0)
            self.assertEqual(b_seam.origen, 'FITTED')
