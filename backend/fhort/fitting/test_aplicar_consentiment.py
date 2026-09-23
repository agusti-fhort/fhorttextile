"""LLEI Agus 24/09 — CONSENTIMENT DE GERMANES: APLICAR (COMMIT 4).

`POST /api/v1/piece-fittings/{id}/close/` amb `decisions` al body — `PieceFittingViewSet.close`
→ `services.close_piece_fitting(..., decisions=...)` →
`services_consentiment.aplica_consolidacio_amb_consentiment`.

Banc CANET-like: B relaxed+extended+seam, els 3 casos (mantenir/proposta/manual), l'override
reescrit i la idempotència d'una 2a aplicació — substitueix el curl real (aquest agent no pot
emetre el JWT de QA, `ftt-qa-token-jwt-bloquejat`): `APIRequestFactory` + `force_authenticate`
exercita la mateixa cadena (URL routing → permisos → view → transacció → serialització).

Convenció del repo: `python manage.py test fhort.fitting` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.fitting.models import (FittingSession, FittingSisterDecision, GradingVersion,
                                  PieceFitting, PieceFittingLine, SizeFitting)
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


class _BaseAplicar(TenantTestCase):

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
            codi_intern='TST-APLICAR', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_aplicar', defaults={'email': 'qa@aplicar.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA Aplicar', 'rol_nom': 'QA'})

    def _tres_instancies(self, relaxed=40.0, extended=42.0, seam=41.0):
        b_rel = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=relaxed, instancia=RELAXED,
            origen='FITTED', ordre=1, nom_fitxa='B-REL')
        b_ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=extended, instancia=EXTENDED,
            origen='DERIVAT', ordre=2, nom_fitxa='B-EXT')
        b_seam = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=seam, instancia=SEAM,
            origen='FITTED', ordre=3, nom_fitxa='B-SEAM')
        return b_rel, b_ext, b_seam

    def _sessio(self):
        sf = SizeFitting.objects.create(model=self.model, numero=2, codi='TST-SF-APLICAR',
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

    def _close(self, pf, decisions=None, **extra):
        body = dict(extra)
        if decisions is not None:
            body['decisions'] = decisions
        req = self.factory.post(f'/api/v1/piece-fittings/{pf.pk}/close/', body, format='json')
        force_authenticate(req, user=self.user)
        return PieceFittingViewSet.as_view({'post': 'close'})(req, pk=pf.pk)


class TresCasosDeDecisioTest(_BaseAplicar):
    """`extended` (DERIVAT): usa la proposta. `seam` (FITTED): manté el seu valor.
    Amb una tercera germana (afegim `top` germana d'instància): valor manual."""

    def test_mantenir_proposta_i_manual(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline', 'fitting_fittingsisterdecision'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            b_top = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=39.0, instancia='top',
                origen='FITTED', ordre=4, nom_fitxa='B-TOP')
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)   # +4

            res = self._close(pf, decisions={
                str(b_ext.pk): 46.0,   # == proposat (42+4) → PROPOSTA
                str(b_seam.pk): 41.0,  # == actual (sense canvi) → MANTINGUT
                str(b_top.pk): 50.0,   # ni actual ni proposat (39+4=43) → MANUAL
            })

            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data['germanes_decidides'], 3)

            b_ext.refresh_from_db(); b_seam.refresh_from_db(); b_top.refresh_from_db()
            self.assertEqual(b_ext.base_value_cm, 46.0)
            self.assertEqual(b_ext.origen, 'DERIVAT')
            self.assertEqual(b_seam.base_value_cm, 41.0, 'MANTINGUT: no es toca')
            self.assertEqual(b_seam.origen, 'FITTED', 'MANTINGUT: origen intacte')
            self.assertEqual(b_top.base_value_cm, 50.0)
            self.assertEqual(b_top.origen, 'MANUAL', 'un humà hi ha escrit un valor propi')

            decisions_desades = {
                d.base_measurement_id: d.decisio
                for d in FittingSisterDecision.objects.filter(piece_fitting=pf)
            }
            self.assertEqual(decisions_desades[b_ext.pk], 'PROPOSTA')
            self.assertEqual(decisions_desades[b_seam.pk], 'MANTINGUT')
            self.assertEqual(decisions_desades[b_top.pk], 'MANUAL')

    def test_germana_sense_entrada_a_decisions_es_manté(self):
        """Tolerància: si el frontend no envia una germana afectada, es tracta com MANTINGUT
        (no com un error) — el defecte del modal ja l'hauria d'haver enviat explícit."""
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline', 'fitting_fittingsisterdecision'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)

            self._close(pf, decisions={})   # cap decisió explícita

            b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_ext.base_value_cm, 42.0, 'sense decisió: MANTINGUT, no es toca')
            self.assertEqual(b_seam.base_value_cm, 41.0)


class OverrideReescritTest(_BaseAplicar):

    def test_upsert_modelinstanceoffset_a_les_dues_bandes(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline', 'fitting_fittingsisterdecision'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)

            self._close(pf, decisions={str(b_ext.pk): 50.0, str(b_seam.pk): 41.0})

            directe = ModelInstanceOffset.objects.get(
                model=self.model, pom=self.pom, capa='exterior',
                instancia_origen=RELAXED, instancia_desti=EXTENDED)
            self.assertEqual(directe.delta, 6.0, '50.0 (final) − 44.0 (mesurat) = +6')
            invers = ModelInstanceOffset.objects.get(
                model=self.model, pom=self.pom, capa='exterior',
                instancia_origen=EXTENDED, instancia_desti=RELAXED)
            self.assertEqual(invers.delta, -6.0)

    def test_mantenir_tambe_confirma_una_relacio(self):
        """MANTINGUT és una decisió com les altres: confirma la folgança REAL encara que no
        segueixi cap regla ingènua."""
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline', 'fitting_fittingsisterdecision'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)

            self._close(pf, decisions={str(b_ext.pk): 42.0, str(b_seam.pk): 41.0})

            offset = ModelInstanceOffset.objects.get(
                model=self.model, pom=self.pom, capa='exterior',
                instancia_origen=RELAXED, instancia_desti=SEAM)
            self.assertEqual(offset.delta, -3.0, '41.0 (mantingut) − 44.0 (mesurat) = −3')


class IdempotenciaTest(_BaseAplicar):

    def test_segona_aplicacio_no_torna_a_decidir_res(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline', 'fitting_fittingsisterdecision'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)

            res1 = self._close(pf, decisions={str(b_ext.pk): 50.0, str(b_seam.pk): 41.0})
            self.assertEqual(res1.data['germanes_decidides'], 2)

            res2 = self._close(pf, decisions={str(b_ext.pk): 999.0, str(b_seam.pk): 999.0})
            self.assertEqual(res2.data['germanes_decidides'], 0,
                             'sense cap línia mesurada nova, deriva() no torna a proposar res')

            b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_ext.base_value_cm, 50.0, 'la 2a crida no ha tocat res')
            self.assertEqual(b_seam.base_value_cm, 41.0)


class SenseDecisionsCaminActualTest(_BaseAplicar):
    """Sense `decisions` al body: camí d'avui (`consolidate_base_from_fitting`), intacte."""

    def test_close_sense_decisions_deriva_tal_qual(self):
        with comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                               'fitting_piecefittingline'):
            b_rel, b_ext, b_seam = self._tres_instancies()
            pf = self._sessio()
            self._linia(pf, RELAXED, 40.0, 44.0)

            res = self._close(pf)   # cap clau 'decisions' al body

            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data['germanes_decidides'], 0)
            b_ext.refresh_from_db(); b_seam.refresh_from_db()
            self.assertEqual(b_ext.base_value_cm, 46.0, 'derivat sense consentiment (camí actual)')
            self.assertEqual(b_seam.base_value_cm, 45.0)
