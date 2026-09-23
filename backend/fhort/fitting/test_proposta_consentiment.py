"""LLEI Agus 24/09 — CONSENTIMENT DE GERMANES: la proposta (COMMIT 3), PURA i vista de fora
(`GET /api/v1/piece-fittings/{id}/proposta/`, `PieceFittingViewSet.proposta`).

Banc CANET-like: B relaxed+extended+seam (v. `fitting/test_consolidacio_instancies_multiples.py`,
mateix escenari de família). Substitueix el curl real: aquest agent no pot emetre el JWT de
QA (`ftt-qa-token-jwt-bloquejat`), i `APIRequestFactory` + `force_authenticate` exercita la
MATEIXA cadena (URL routing → permisos → view → serialització) sense servidor viu.

Convenció del repo: `python manage.py test fhort.fitting` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.fitting.models import (FittingSession, GradingVersion, PieceFitting,
                                  PieceFittingLine, SizeFitting)
from fhort.fitting.views import PieceFittingViewSet
from fhort.models_app.models import BaseMeasurement, Model, ModelInstanceOffset
from fhort.pom.models import POMMaster

RELAXED, EXTENDED, SEAM = 'relaxed', 'extended', 'seam'


@contextlib.contextmanager
def comportes_alcades(*taules, eixos=('capa_gate_c1', 'instancia_gate_cins')):
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


class _BaseProposta(TenantTestCase):

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
        self.factory = APIRequestFactory()
        self.pom = POMMaster.objects.create(codi_client='B', nom_client='Cintura')
        self.model = Model.objects.create(
            codi_intern='TST-CONSENT', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_consent', defaults={'email': 'qa@consent.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA Consentiment', 'rol_nom': 'QA'})

    def _tres_instancies(self, relaxed=40.0, extended=42.0, seam=41.0, origen_ext='DERIVAT',
                         origen_seam='FITTED'):
        b_rel = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=relaxed, instancia=RELAXED,
            origen='FITTED', ordre=1, nom_fitxa='B-REL')
        b_ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=extended, instancia=EXTENDED,
            origen=origen_ext, ordre=2, nom_fitxa='B-EXT')
        b_seam = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=seam, instancia=SEAM,
            origen=origen_seam, ordre=3, nom_fitxa='B-SEAM')
        return b_rel, b_ext, b_seam

    def _sessio(self):
        sf = SizeFitting.objects.create(model=self.model, numero=2, codi='TST-SF-CONSENT',
                                        tipus='PROTO', creat_per=self.perfil)
        gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                           version_number=1, creat_per=self.perfil)
        sessio = FittingSession.objects.create(
            model=self.model, fase=self.model.fase_actual, data=datetime.date(2026, 9, 24))
        return PieceFitting.objects.create(session=sessio, model=self.model, grading_version=gv)

    def _linia(self, pf, instancia, teoric, real):
        return PieceFittingLine.objects.create(
            piece_fitting=pf, pom=self.pom, size_label='M', capa='exterior',
            instancia=instancia, valor_teoric=teoric, valor_real=real)

    def _get_proposta(self, pf):
        req = self.factory.get(f'/api/v1/piece-fittings/{pf.pk}/proposta/')
        force_authenticate(req, user=self.user)
        return PieceFittingViewSet.as_view({'get': 'proposta'})(req, pk=pf.pk)


class PropostaAmbGermanesTest(_BaseProposta):
    """Cas CANET-like: `relaxed` es rectifica; `extended` (DERIVAT) i `seam` (FITTED) no
    tenen línia — han de sortir com a germanes amb defectes diferents."""

    def test_status_200_i_germanes_amb_defecte_per_origen(self):
        with comportes_alcades('models_app_basemeasurement', 'fitting_piecefittingline'):
            self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)   # +4, únic mesurat

            res = self._get_proposta(pf)

            self.assertEqual(res.status_code, 200)
            self.assertFalse(res.data['buit'])
            self.assertEqual(len(res.data['poms']), 1)
            bucket = res.data['poms'][0]
            self.assertEqual(bucket['pom'], 'B')
            self.assertEqual(len(bucket['mesurades']), 1)
            self.assertEqual(bucket['mesurades'][0]['instancia'], RELAXED)
            self.assertEqual(bucket['mesurades'][0]['abans'], 40.0)
            self.assertEqual(bucket['mesurades'][0]['ara'], 44.0)

            germanes = {g['instancia']: g for g in bucket['germanes']}
            self.assertEqual(set(germanes), {EXTENDED, SEAM})
            self.assertEqual(germanes[EXTENDED]['proposat'], 46.0)
            self.assertEqual(germanes[EXTENDED]['decisio_defecte'], 'PROPOSTA',
                             'origen DERIVAT: defecte proposta pre-usada')
            self.assertEqual(germanes[SEAM]['proposat'], 45.0)
            self.assertEqual(germanes[SEAM]['decisio_defecte'], 'MANTINGUT',
                             'origen FITTED (mesurat): defecte mantenir')
            self.assertIn("regla d'instància", germanes[EXTENDED]['regla_text'])
            self.assertIn('relaxed', germanes[EXTENDED]['regla_text'])

    def test_no_escriu_res(self):
        """PUR: cap BaseMeasurement es toca en demanar la proposta."""
        with comportes_alcades('models_app_basemeasurement', 'fitting_piecefittingline'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)

            self._get_proposta(pf)

            b_rel.refresh_from_db(); b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_rel.base_value_cm, 40.0)
            self.assertEqual(b_ext.base_value_cm, 42.0)
            self.assertEqual(b_seam.base_value_cm, 41.0)

    def test_delta_confirmat_del_model_guanya_al_calcul_en_viu(self):
        """Amb un `ModelInstanceOffset` ja confirmat per a (relaxed→extended), la proposta
        l'usa en lloc de l'increment d'aquesta sessió."""
        with comportes_alcades('models_app_basemeasurement', 'fitting_piecefittingline'):
            self._tres_instancies()
            ModelInstanceOffset.objects.create(
                model=self.model, pom=self.pom, capa='exterior',
                instancia_origen=RELAXED, instancia_desti=EXTENDED, delta=10.0)
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)   # +4 en viu, però el confirmat diu +10

            res = self._get_proposta(pf)

            germanes = {g['instancia']: g for g in res.data['poms'][0]['germanes']}
            self.assertEqual(germanes[EXTENDED]['proposat'], 52.0, '42.0 + 10 (confirmat)')
            self.assertIn('delta confirmat', germanes[EXTENDED]['regla_text'])


class PropostaBuidaTest(_BaseProposta):
    """Sense germanes afectades → `buit=True`, cap modal (LLEI Agus 24/09, punt 4)."""

    def test_buit_quan_no_hi_ha_cap_germana(self):
        pom_sol = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        BaseMeasurement.objects.create(
            model=self.model, pom=pom_sol, base_value_cm=50.0, ordre=1, nom_fitxa='A')
        pf = self._sessio()
        PieceFittingLine.objects.create(
            piece_fitting=pf, pom=pom_sol, size_label='M', capa='exterior', instancia='',
            valor_teoric=50.0, valor_real=54.0)

        res = self._get_proposta(pf)

        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['buit'])

    def test_buit_quan_totes_les_germanes_ja_son_mesurades(self):
        """Cas 1 de `test_consolidacio_instancies_multiples.py`: les TRES rectificades a la
        vegada — cap queda «no mesurada», per tant cap surt com a germana."""
        with comportes_alcades('models_app_basemeasurement', 'fitting_piecefittingline'):
            self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)
            self._linia(pf, EXTENDED, 42.0, 43.0)
            self._linia(pf, SEAM, 41.0, 41.5)

            res = self._get_proposta(pf)

            self.assertTrue(res.data['buit'])
            self.assertEqual(res.data['poms'][0]['germanes'], [])
