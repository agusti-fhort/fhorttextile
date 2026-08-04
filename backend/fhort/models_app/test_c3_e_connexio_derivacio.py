"""C3-E — la derivació connectada als dos punts honestos, provada d'extrem a extrem.

De setze punts d'escriptura de mesura base, només DOS coneixen els seus eixos per CÒPIA i no
per literal —els hereten de la línia que els porta— i en tots dos hi són alhora la línia, la
fila escrita i el valor anterior: `fitting/services.py` (consolidació de fitting) i
`services_size_check.py` (resolució de size check). L'increment ja és calculable allà, sense
endevinar res. Són els dos que aquesta fase connecta.

EL QUE ES PROVA (regla d'Agus, 02/08): tocar l'exterior mou el folre pel valor correcte —es mou
el VALOR, mai el grading— i deixa rastre amb l'origen correcte. La folgança es conserva sola i
es comprova per RESTA: si algun dia es propagués l'absolut, cauria.

Amb les comportes de C1/C1-ins vives no hi ha cap germana i la connexió és un no-op; per això
aquests tests les alcen dins d'un savepoint que sempre es desfà.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.models_app.models import (BaseMeasurement, MeasurementChangeLog, Model,
                                     SizeCheck)
from fhort.pom.models import MeasurementLayer, POMMaster

FOLRE = 'folre'
EXTERIOR = MeasurementLayer.SLUG_DEFECTE


@contextlib.contextmanager
def comportes_alcades(*taules, eixos=('capa_gate_c1', 'instancia_gate_cins')):
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            # Les FK de Django són DEFERRABLE INITIALLY DEFERRED i el `setUp` ja ha escrit:
            # sense això Postgres refusa l'ALTER amb «pending trigger events».
            cur.execute('SET CONSTRAINTS ALL IMMEDIATE')
            for taula in taules:
                for sufix in eixos:
                    cur.execute(
                        f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                        f'DROP CONSTRAINT "{taula}_{sufix}"'
                    )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class _BaseE(TenantTestCase):

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
            codi_intern='TST-C3E', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_c3e', defaults={'email': 'qa@c3e.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA C3-E', 'rol_nom': 'QA'})

    def _parella(self, ext_val=54.0, fol_val=52.0):
        """L'exterior i el seu folre, amb 2 cm de folgança que ningú no ha declarat enlloc."""
        ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=ext_val, ordre=1, nom_fitxa='A-EXT')
        fol = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=fol_val, ordre=2, capa=FOLRE,
            nom_fitxa='A-FOL')
        return ext, fol


class DerivacioDesDelFittingTest(_BaseE):
    """`consolidate_base_from_fitting` — el primer punt honest."""

    def _consolida(self, valor_real):
        from fhort.fitting.models import (FittingSession, GradingVersion, PieceFitting,
                                          PieceFittingLine, SizeFitting)
        from fhort.fitting.services import consolidate_base_from_fitting

        sf = SizeFitting.objects.create(model=self.model, numero=2, codi='TST-SF-C3E',
                                        tipus='PROTO', creat_per=self.perfil)
        gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                           version_number=1, creat_per=self.perfil)
        sessio = FittingSession.objects.create(
            model=self.model, fase=self.model.fase_actual, data=datetime.date(2026, 8, 2))
        pf = PieceFitting.objects.create(session=sessio, model=self.model, grading_version=gv)
        # La línia de l'EXTERIOR a la talla base, rectificada pel tècnic.
        PieceFittingLine.objects.create(
            piece_fitting=pf, pom=self.pom, size_label='M',
            capa=EXTERIOR, instancia='',
            valor_teoric=54.0, valor_real=valor_real)
        return consolidate_base_from_fitting(pf, auth_user=self.user)

    def test_rectificar_lexterior_MOU_el_folre_i_conserva_la_folganca(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            ext, fol = self._parella()
            folganca = ext.base_value_cm - fol.base_value_cm     # 2.0, ningú no la declara

            self._consolida(56.0)

            ext.refresh_from_db()
            fol.refresh_from_db()
            self.assertEqual(ext.base_value_cm, 56.0, "l'exterior és el que s'ha mesurat")
            self.assertEqual(fol.base_value_cm, 54.0, 'el folre s\'ha mogut +2, com l\'exterior')
            self.assertEqual(ext.base_value_cm - fol.base_value_cm, folganca,
                             'la folgança es conserva SOLA: es mou el valor, no el grading')

    def test_el_folre_mogut_queda_marcat_com_a_DERIVAT(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            _ext, fol = self._parella()

            self._consolida(56.0)

            fol.refresh_from_db()
            self.assertEqual(fol.origen, 'DERIVAT',
                             "ningú no ha mesurat el folre: el sistema l'ha mogut")

    def test_el_REGISTRE_distingeix_la_presa_de_la_derivacio(self):
        """El que fa auditable la parella: dues entrades, i diuen coses diferents."""
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            ext, fol = self._parella()

            self._consolida(56.0)

            log_ext = (MeasurementChangeLog.objects.filter(base_measurement=ext)
                       .order_by('id').last())
            log_fol = (MeasurementChangeLog.objects.filter(base_measurement=fol)
                       .order_by('id').last())
            self.assertEqual(log_ext.context, 'fitting', 'la presa: algú ho ha mesurat')
            self.assertEqual(log_fol.context, 'derivat', 'la derivada: el sistema ho ha mogut')
            self.assertEqual(log_fol.valor_anterior, 52.0)
            self.assertEqual(log_fol.valor_nou, 54.0)
            self.assertEqual(log_fol.capa, FOLRE, 'i diu de QUINA germana parla')
            self.assertIn('Derivat de', log_fol.motiu)

    def test_sense_germana_no_passa_res(self):
        """El cas d'avui amb les comportes vives: la connexió és un no-op."""
        ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=54.0, ordre=1, nom_fitxa='A-EXT')

        self._consolida(56.0)

        ext.refresh_from_db()
        self.assertEqual(ext.base_value_cm, 56.0)
        self.assertEqual(BaseMeasurement.objects.filter(model=self.model).count(), 1,
                         'no s\'inventa cap germana')


class DerivacioDesDelSizeCheckTest(_BaseE):
    """`resolve_size_check` — el segon punt honest."""

    def _resol(self, valor_real):
        from fhort.models_app.models import SizeCheckLine
        from fhort.models_app.services_size_check import resolve_size_check

        sc = SizeCheck.objects.create(model=self.model, talla_base_label='M')
        SizeCheckLine.objects.create(
            size_check=sc, pom=self.pom, capa=EXTERIOR, instancia='',
            valor_teoric=54.0, valor_real=valor_real)
        # La signatura pren el PERFIL, no l'usuari d'auth: `auth_user` el dedueix ella (:188-192).
        return resolve_size_check(sc.pk, 'Acceptat', user_profile_id=self.perfil.pk)

    def test_acceptar_el_check_de_lexterior_MOU_el_folre(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'models_app_sizecheckline'):
            ext, fol = self._parella()
            folganca = ext.base_value_cm - fol.base_value_cm

            self._resol(56.0)

            ext.refresh_from_db()
            fol.refresh_from_db()
            self.assertEqual(ext.base_value_cm, 56.0)
            self.assertEqual(fol.base_value_cm, 54.0)
            self.assertEqual(ext.base_value_cm - fol.base_value_cm, folganca)

    def test_el_registre_del_size_check_tambe_marca_la_derivada(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'models_app_sizecheckline'):
            _ext, fol = self._parella()

            self._resol(56.0)

            log_fol = (MeasurementChangeLog.objects.filter(base_measurement=fol)
                       .order_by('id').last())
            self.assertEqual(log_fol.context, 'derivat')
            self.assertIn('size check', log_fol.motiu)

    def test_un_check_que_no_canvia_res_no_deriva(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'models_app_sizecheckline'):
            _ext, fol = self._parella()

            self._resol(54.0)          # el mateix valor que ja hi havia

            fol.refresh_from_db()
            self.assertEqual(fol.base_value_cm, 52.0, 'sense increment no hi ha res a propagar')
