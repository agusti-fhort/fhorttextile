"""Tests de `repunta_alies_retirats` (COMMIT 4, 16/09, DECISIONS.md).

Neteja de fons per als àlies que `find_pom_master` (COMMIT 1) ja deixa pendents perquè
reclamen un POM retirat: si tenen un hereu clar (mateix `pom_global` actiu), repunta'ls.
"""
import io

from django.core.management import call_command
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import CustomerPOMAlias, POMGlobal, POMMaster
from fhort.tasks.models import Customer


class _TenantBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'


class RepuntaAliesRetiratsTest(_TenantBase):

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')

    def _dry_run(self):
        out = io.StringIO()
        call_command('repunta_alies_retirats', customer='BRW', stdout=out)
        return out.getvalue()

    def _apply(self):
        out = io.StringIO()
        call_command('repunta_alies_retirats', customer='BRW', apply=True, stdout=out)
        return out.getvalue()

    def test_client_inexistent_atura_amb_error(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command('repunta_alies_retirats', customer='NO-EXISTEIX')

    def test_dry_run_no_escriu_res(self):
        canonic = POMGlobal.objects.create(codi='CAN1', nom_en='c1', nom_ca='c1', categoria='Q')
        retirat = POMMaster.objects.create(
            codi_client='R1', nom_client='retirat', actiu=False, pom_global=canonic)
        POMMaster.objects.create(
            codi_client='H1', nom_client='hereu', actiu=True, pom_global=canonic)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C1', pom=retirat, origen='DICCIONARI')

        sortida = self._dry_run()

        alias.refresh_from_db()
        self.assertEqual(alias.pom_id, retirat.id, 'dry-run no ha d\'escriure res')
        self.assertIn('REPUNTAR', sortida)
        self.assertIn('DRY-RUN', sortida)

    def test_apply_repunta_al_hereu_i_deixa_rastre(self):
        canonic = POMGlobal.objects.create(codi='CAN2', nom_en='c2', nom_ca='c2', categoria='Q')
        retirat = POMMaster.objects.create(
            codi_client='R2', nom_client='retirat', actiu=False, pom_global=canonic)
        hereu = POMMaster.objects.create(
            codi_client='H2', nom_client='hereu', actiu=True, pom_global=canonic)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C2', pom=retirat, origen='DICCIONARI')

        self._apply()

        alias.refresh_from_db()
        self.assertEqual(alias.pom_id, hereu.id)
        self.assertEqual(alias.origen, 'REPUNT_v5')
        self.assertIsNotNone(alias.editat_at)

    def test_sense_hereu_no_toca_res(self):
        canonic = POMGlobal.objects.create(codi='CAN3', nom_en='c3', nom_ca='c3', categoria='Q')
        retirat = POMMaster.objects.create(
            codi_client='R3', nom_client='retirat', actiu=False, pom_global=canonic)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C3', pom=retirat, origen='DICCIONARI')

        sortida = self._apply()

        alias.refresh_from_db()
        self.assertEqual(alias.pom_id, retirat.id, 'sense hereu, no hi ha res a repuntar')
        self.assertIn('SENSE HEREU', sortida)

    def test_pom_tenant_only_sense_pom_global_es_sense_hereu(self):
        """Un POM sense `pom_global` (tenant-only) no té cap clau per on trobar hereu."""
        retirat = POMMaster.objects.create(
            codi_client='R4', nom_client='retirat tenant-only', actiu=False, pom_global=None)
        CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C4', pom=retirat, origen='DICCIONARI')

        sortida = self._dry_run()

        self.assertIn('SENSE HEREU', sortida)

    def test_bessona_existent_no_es_toca_ni_es_duplica(self):
        """Si (customer, codi, hereu) ja existeix com a fila pròpia, repuntar la duplicaria:
        es deixa tal qual per revisió manual, no per la comanda."""
        canonic = POMGlobal.objects.create(codi='CAN5', nom_en='c5', nom_ca='c5', categoria='Q')
        retirat = POMMaster.objects.create(
            codi_client='R5', nom_client='retirat', actiu=False, pom_global=canonic)
        hereu = POMMaster.objects.create(
            codi_client='H5', nom_client='hereu', actiu=True, pom_global=canonic)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C5', pom=retirat, origen='DICCIONARI')
        bessona = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C5', pom=hereu, origen='IMPORT')

        self._apply()

        alias.refresh_from_db()
        bessona.refresh_from_db()
        self.assertEqual(alias.pom_id, retirat.id)
        self.assertEqual(bessona.pom_id, hereu.id)
        self.assertEqual(
            CustomerPOMAlias.objects.filter(customer=self.customer, client_code='C5').count(), 2)
