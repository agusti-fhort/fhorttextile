"""Tests de `repunta_alies_retirats` (COMMIT 4, 16/09, DECISIONS.md).

Neteja de fons per als àlies que `find_pom_master` (COMMIT 1) ja deixa pendents perquè
reclamen un POM retirat: si tenen un hereu clar, repunta'ls.

🔄 CRITERI D'HEREU (revisió 16/09): un POM ACTIU amb `codi_client` IGUAL al `client_code`
de l'ÀLIES (el que diu el CLIENT, case-insensitive) — no al `codi_client` del POM
retirat (únic per constraint de BD, mai el pot compartir cap altre POM) ni al
`pom_global`. Per això als fixtures d'aquí baix el POM retirat i l'hereu tenen
`codi_client` DIFERENTS a posta (p.ex. 'RETIRAT-C2' i 'C2'): és el `client_code` de
l'àlies qui ha de casar amb el de l'hereu, no el del retirat.
"""
import io

from django.core.management import call_command
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import CustomerPOMAlias, POMMaster
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
        retirat = POMMaster.objects.create(
            codi_client='RETIRAT-C1', nom_client='retirat', actiu=False)
        POMMaster.objects.create(codi_client='C1', nom_client='hereu', actiu=True)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C1', pom=retirat, origen='DICCIONARI')

        sortida = self._dry_run()

        alias.refresh_from_db()
        self.assertEqual(alias.pom_id, retirat.id, 'dry-run no ha d\'escriure res')
        self.assertIn('REPUNTAR', sortida)
        self.assertIn('DRY-RUN', sortida)

    def test_apply_repunta_al_hereu_i_deixa_rastre(self):
        retirat = POMMaster.objects.create(
            codi_client='RETIRAT-C2', nom_client='retirat', actiu=False)
        hereu = POMMaster.objects.create(codi_client='C2', nom_client='hereu', actiu=True)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C2', pom=retirat, origen='DICCIONARI')

        self._apply()

        alias.refresh_from_db()
        self.assertEqual(alias.pom_id, hereu.id)
        self.assertEqual(alias.origen, 'REPUNT_v5')
        self.assertIsNotNone(alias.editat_at)

    def test_hereu_amb_nom_buit_tambe_val(self):
        """«nom pot ser buit» (16/09): l'hereu es troba pel codi_client, no pel nom."""
        retirat = POMMaster.objects.create(
            codi_client='RETIRAT-C2B', nom_client='retirat', actiu=False)
        hereu = POMMaster.objects.create(codi_client='C2B', nom_client='', actiu=True)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C2B', pom=retirat, origen='DICCIONARI')

        self._apply()

        alias.refresh_from_db()
        self.assertEqual(alias.pom_id, hereu.id)

    def test_hereu_es_case_insensitive(self):
        retirat = POMMaster.objects.create(
            codi_client='RETIRAT-C2C', nom_client='retirat', actiu=False)
        hereu = POMMaster.objects.create(codi_client='c2c', nom_client='hereu', actiu=True)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C2C', pom=retirat, origen='DICCIONARI')

        self._apply()

        alias.refresh_from_db()
        self.assertEqual(alias.pom_id, hereu.id)

    def test_sense_hereu_no_toca_res(self):
        retirat = POMMaster.objects.create(
            codi_client='RETIRAT-C3', nom_client='retirat', actiu=False)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C3', pom=retirat, origen='DICCIONARI')

        sortida = self._apply()

        alias.refresh_from_db()
        self.assertEqual(alias.pom_id, retirat.id, 'sense hereu, no hi ha res a repuntar')
        self.assertIn('SENSE HEREU', sortida)

    def test_pom_tenant_only_sense_pom_global_tambe_pot_trobar_hereu(self):
        """El criteri NOU (codi_client == client_code) no depèn de `pom_global`: un POM
        tenant-only (pom_global=None) retirat POT tenir hereu si un altre POM tenant-only
        actiu comparteix `codi_client` amb el `client_code` de l'àlies."""
        retirat = POMMaster.objects.create(
            codi_client='RETIRAT-C4', nom_client='retirat tenant-only', actiu=False,
            pom_global=None)
        hereu = POMMaster.objects.create(
            codi_client='C4', nom_client='hereu tenant-only', actiu=True, pom_global=None)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C4', pom=retirat, origen='DICCIONARI')

        self._apply()

        alias.refresh_from_db()
        self.assertEqual(alias.pom_id, hereu.id)

    def test_bessona_existent_no_es_toca_ni_es_duplica(self):
        """Amb la migració 0088, dos àlies (customer, client_code) amb POM DIFERENT SÍ són
        legals (és exactament el cas 'alies_contradictoris' que detecta find_pom_master).
        Si ja hi ha una fila (customer, client_code, hereu) —el propi client ja ho havia
        après per un altre camí—, repuntar-hi la del POM retirat la DUPLICARIA en comptes
        de fondre-les: es deixa tal qual per revisió manual, no per aquesta comanda."""
        retirat = POMMaster.objects.create(
            codi_client='RETIRAT-C5', nom_client='retirat', actiu=False)
        hereu = POMMaster.objects.create(codi_client='C5', nom_client='hereu', actiu=True)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C5', pom=retirat, origen='DICCIONARI')
        bessona = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='C5', pom=hereu, origen='IMPORT')

        sortida = self._apply()

        alias.refresh_from_db()
        bessona.refresh_from_db()
        self.assertEqual(alias.pom_id, retirat.id, 'no es toca: repuntar duplicaria la bessona')
        self.assertEqual(bessona.pom_id, hereu.id, 'la bessona tampoc es toca')
        self.assertEqual(
            CustomerPOMAlias.objects.filter(customer=self.customer, client_code='C5').count(), 2,
            'segueixen sent DUES files — la comanda no en crea una tercera')
        self.assertIn('JA REPUNTAT', sortida)
