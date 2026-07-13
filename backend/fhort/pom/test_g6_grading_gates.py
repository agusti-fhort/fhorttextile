"""G6 · FASE 0 — els dos sagnats del grading (DIAGNOSI_G6_DUAL_PATH).

Executat amb `python manage.py test fhort.pom` (el projecte NO fa servir pytest).

  · **0a · Fork 4** (`pom/s6_views.py`): l'únic lector de `GradingVersion` que ordenava per
    `('-data','-id')` IGNORANT `is_active`. Sobre el SizeFitting real 52 (model 162) servia la
    v5 DESACTIVADA mentre la resta del sistema servia la v3 activa: dues superfícies de la UI
    ensenyaven talles diferents del mateix model. El test reprodueix aquella forma exacta.

"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import Model
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem


class _G6Base(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='g6')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'G6', 'rol_nom': 'admin'})

        self.ss = SizeSystem.objects.create(codi='SS_G6', nom='SS G6', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.talla_base = SizeDefinition.objects.get(size_system=self.ss, etiqueta='M')
        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest width')

    def _model(self, codi, *, rule_set=None):
        return Model.objects.create(
            codi_intern=codi, codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Test', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M', grading_rule_set=rule_set,
        )

    def _sf(self, model, codi, estat='Pendent'):
        return SizeFitting.objects.create(
            model=model, numero=1, codi=codi, tipus='SizeSet', estat=estat,
            creat_per=self.profile,
        )


class Fork4VersioVigentTest(_G6Base):
    """0a — `graded-specs-units/` ha de servir la versió VIGENT, com tothom."""

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.model = self._model('TST-162')
        self.sf = self._sf(self.model, 'SF-162', estat='Tancat')

        # La forma REAL del SizeFitting 52 (model 162): la v3 és l'ACTIVA, i la v5 —creada
        # DESPRÉS (data posterior, id més alt) i desactivada— és la que el fork servia.
        base = datetime.datetime(2026, 6, 8, 8, 0, tzinfo=datetime.timezone.utc)
        self.v3 = GradingVersion.objects.create(
            size_fitting=self.sf, version_number=3, is_active=True, aprovada=False)
        self.v5 = GradingVersion.objects.create(
            size_fitting=self.sf, version_number=5, is_active=False, aprovada=False)
        # `data` és auto_now_add: es força a posteriori perquè la v5 sigui la MÉS RECENT.
        GradingVersion.objects.filter(pk=self.v3.pk).update(data=base)
        GradingVersion.objects.filter(pk=self.v5.pk).update(
            data=base + datetime.timedelta(hours=9))

        for gv, valor in ((self.v3, 40.0), (self.v5, 99.0)):
            GradedSpec.objects.create(
                grading_version=gv, pom=self.pom, size_label='M',
                graded_value_cm=valor, grading_type_applied='LINEAR', is_active=True)

    def _get(self):
        from fhort.pom.s6_views import graded_specs_with_units_view
        req = self.factory.get(f'/graded-specs-units/{self.sf.id}/')
        force_authenticate(req, user=self.user)
        return graded_specs_with_units_view(req, sf_id=self.sf.id)

    def test_serveix_la_versio_ACTIVA_no_la_mes_recent(self):
        resp = self._get()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['grading_version_id'], self.v3.pk,
                         'ha de servir la v3 (activa), no la v5 (desactivada i més recent)')
        valors = [r['values']['M']['cm'] for r in resp.data['results']]
        self.assertEqual(valors, [40.0], 'el valor ha de venir de la v3 (activa), no el 99 de la v5')

    def test_coincideix_amb_la_resta_de_lectors(self):
        """El punt de tot plegat: aquesta superfície i les altres han de dir el MATEIX."""
        from fhort.fitting.services import vigent_grading_version

        self.assertEqual(self._get().data['grading_version_id'],
                         vigent_grading_version(self.sf).pk)

    def test_sense_cap_activa_cau_a_la_mes_recent(self):
        """El fallback de `vigent_grading_version` (anomalia de dades): si cap versió és
        activa, es continua servint alguna cosa — la més recent — en comptes de res."""
        GradingVersion.objects.filter(pk=self.v3.pk).update(is_active=False)

        self.assertEqual(self._get().data['grading_version_id'], self.v5.pk)
