"""Tests de `desvincula_description_match` (COMMIT 5, 16/09, DECISIONS.md).

El mode de fallada real del model 1216: files vinculades per `description_match` a un
POM que després es retira ('BR'). Aquesta comanda les torna a pendent (soft-desactivació,
mateix mecanisme que la poda de W5), conservant `nom_fitxa`/`notes` intactes.
"""
import io

from django.core.management import call_command
from django.core.management.base import CommandError
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import BaseMeasurement, MeasurementChangeLog, Model
from fhort.pom.models import POMMaster
from fhort.tasks.models import Customer


class _TenantBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'


class DesvinculaDescriptionMatchTest(_TenantBase):

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        self.pom_sospitos = POMMaster.objects.create(codi_client='BR', nom_client='sospitós')
        self.pom_bo = POMMaster.objects.create(codi_client='OK', nom_client='correcte')
        self.model = Model.objects.create(
            customer=self.customer, codi_intern='M1216', codi_client='C1216',
            codi_tenant='QA', any=2026, temporada='SS26', sequencial=1)

    def test_model_inexistent_atura_amb_error(self):
        with self.assertRaises(CommandError):
            call_command('desvincula_description_match', model=999999, pom='BR')

    def test_pom_inexistent_atura_amb_error(self):
        with self.assertRaises(CommandError):
            call_command('desvincula_description_match', model=self.model.id, pom='NO-EXISTEIX')

    def test_cens_sense_model_no_escriu(self):
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_sospitos, base_value_cm=1.0, nom_fitxa='X',
            notes='descripció', origen='IMPORTED', is_active=True)

        out = io.StringIO()
        call_command('desvincula_description_match', pom='BR', stdout=out)

        bm.refresh_from_db()
        self.assertTrue(bm.is_active, 'el cens no ha d\'escriure res')
        self.assertIn(self.model.codi_intern, out.getvalue())

    def test_dry_run_no_toca_res(self):
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_sospitos, base_value_cm=1.0, nom_fitxa='X',
            notes='descripció', origen='IMPORTED', is_active=True)

        out = io.StringIO()
        call_command('desvincula_description_match', model=self.model.id, pom='BR', stdout=out)

        bm.refresh_from_db()
        self.assertTrue(bm.is_active)
        self.assertIn('DRY-RUN', out.getvalue())
        self.assertIn('X', out.getvalue())

    def test_apply_desactiva_conserva_nom_fitxa_i_notes_i_no_esborra(self):
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_sospitos, base_value_cm=12.3, nom_fitxa='BND',
            notes='Back neck drop from HPS to edge', origen='IMPORTED', is_active=True)

        call_command('desvincula_description_match', model=self.model.id, pom='BR', apply=True)

        bm.refresh_from_db()
        self.assertFalse(bm.is_active)
        self.assertEqual(bm.nom_fitxa, 'BND')
        self.assertEqual(bm.notes, 'Back neck drop from HPS to edge')
        self.assertEqual(bm.pom_id, self.pom_sospitos.id, 'soft: el pom no es toca')
        self.assertTrue(BaseMeasurement.objects.filter(pk=bm.pk).exists(), 'res s\'esborra')

    def test_apply_deixa_rastre_a_measurementchangelog(self):
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_sospitos, base_value_cm=1.0, nom_fitxa='X',
            notes='d', origen='IMPORTED', is_active=True)

        call_command('desvincula_description_match', model=self.model.id, pom='BR', apply=True)

        self.assertTrue(MeasurementChangeLog.objects.filter(base_measurement=bm).exists())

    def test_apply_nomes_toca_el_pom_indicat_no_altres_files_del_model(self):
        dolenta = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_sospitos, base_value_cm=1.0, nom_fitxa='X',
            notes='d', origen='IMPORTED', is_active=True)
        bona = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_bo, base_value_cm=2.0, nom_fitxa='Y',
            notes='d2', origen='IMPORTED', is_active=True)

        call_command('desvincula_description_match', model=self.model.id, pom='BR', apply=True)

        dolenta.refresh_from_db()
        bona.refresh_from_db()
        self.assertFalse(dolenta.is_active)
        self.assertTrue(bona.is_active, 'una fila d\'un altre POM no s\'ha de tocar')

    def test_sense_pom_agafa_els_de_nom_buit(self):
        pom_buit = POMMaster.objects.create(codi_client='BUIT', nom_client='')
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=pom_buit, base_value_cm=1.0, nom_fitxa='Z',
            notes='d', origen='IMPORTED', is_active=True)

        call_command('desvincula_description_match', model=self.model.id, apply=True)

        bm.refresh_from_db()
        self.assertFalse(bm.is_active)
