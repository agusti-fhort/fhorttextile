"""TenantLink — el pont de federació Brand↔Studio (Federació v2, P1).

Les lleis que defensen:

  · EL TOKEN GOVERNA EL PONT, MAI EL TREBALL. Aturar o revocar un vincle no destrueix
    cap dada; només tanca el pont. REVOCAT és terminal.
  · TIPOLOGIA ÉS EL PRIMER CONSUMIDOR DE DOMINI. El Brand ha de ser 'marca' i l'Studio
    'estudi'; el vincle invertit es rebutja a clean().
  · UN VINCLE PER PARELLA. unique_together (brand, studio); token globalment únic.

Es munten DOS tenants reals: un Brand (marca) i un Studio (estudi), perquè la validació
de tipologies llegeix Client de debò, no un mock.

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_tenant_link
"""
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model

from fhort.tenants.models import Client, TenantLink

BRAND = 'MAR'
STUDIO = 'EST'


class TenantLinkTest(TenantTestCase):
    """El tenant per defecte fa de Brand (marca); un segon tenant fa d'Studio (estudi)."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Marca'
        tenant.codi_tenant = BRAND
        tenant.tipologia = Client.TIPOLOGIA_MARCA
        tenant.email_facturacio = 'm@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.set_schema_to_public()
        TenantModel = get_tenant_model()
        cls.studio = TenantModel(
            schema_name='est', nom='Estudi', codi_tenant=STUDIO,
            tipologia=Client.TIPOLOGIA_ESTUDI, email_facturacio='e@x.com',
        )
        cls.studio.save(verbosity=0)
        cls.studio.domains.create(domain='est.test.com', is_primary=True)
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.studio.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        TenantLink.objects.all().delete()

    # ── creació + token ───────────────────────────────────────────────────────
    def test_creacio_genera_token(self):
        link = TenantLink.objects.create(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        self.assertTrue(link.token)
        self.assertGreaterEqual(len(link.token), 40)   # token_urlsafe(32) ≈ 43 chars
        self.assertEqual(link.estat, TenantLink.ESTAT_ACTIU)

    def test_token_unic(self):
        link = TenantLink.objects.create(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            TenantLink.objects.create(
                brand_codi_tenant='OTR', studio_codi_tenant='ST2', token=link.token)

    # ── validació de tipologies ───────────────────────────────────────────────
    def test_validacio_tipologies_ok(self):
        link = TenantLink(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        link.clean()   # no ha de llançar: MAR és marca, EST és estudi

    def test_validacio_rebutja_invertit(self):
        """Brand=estudi / Studio=marca → invàlid."""
        link = TenantLink(brand_codi_tenant=STUDIO, studio_codi_tenant=BRAND)
        with self.assertRaises(ValidationError) as ctx:
            link.clean()
        self.assertIn('brand_codi_tenant', ctx.exception.message_dict)

    def test_validacio_rebutja_tenant_inexistent(self):
        link = TenantLink(brand_codi_tenant='XXX', studio_codi_tenant=STUDIO)
        with self.assertRaises(ValidationError):
            link.clean()

    # ── cicle de vida ─────────────────────────────────────────────────────────
    def test_cicle_actiu_aturat_actiu(self):
        link = TenantLink.objects.create(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        self.assertTrue(link.es_viu())

        link.aturar()
        self.assertEqual(link.estat, TenantLink.ESTAT_ATURAT)
        self.assertIsNotNone(link.aturat_at)
        self.assertFalse(link.es_viu())

        link.reactivar()
        self.assertEqual(link.estat, TenantLink.ESTAT_ACTIU)
        self.assertIsNone(link.aturat_at)
        self.assertTrue(link.es_viu())

    def test_revocat_terminal(self):
        link = TenantLink.objects.create(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        link.revocar()
        self.assertEqual(link.estat, TenantLink.ESTAT_REVOCAT)
        self.assertIsNotNone(link.aturat_at)

        with self.assertRaises(ValidationError):
            link.reactivar()
        with self.assertRaises(ValidationError):
            link.aturar()
        # revocar() de nou és idempotent (no llança, no canvia)
        link.revocar()
        self.assertEqual(link.estat, TenantLink.ESTAT_REVOCAT)

    def test_aturar_nomes_des_dactiu(self):
        link = TenantLink.objects.create(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        link.aturar()
        with self.assertRaises(ValidationError):
            link.aturar()   # ja aturat

    # ── unicitat de la parella ────────────────────────────────────────────────
    def test_unique_together(self):
        TenantLink.objects.create(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            TenantLink.objects.create(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)

    # ── seed idempotent ───────────────────────────────────────────────────────
    def test_seed_idempotent(self):
        call_command('seed_tenant_link', '--brand', BRAND, '--studio', STUDIO, verbosity=0)
        call_command('seed_tenant_link', '--brand', BRAND, '--studio', STUDIO, verbosity=0)
        links = TenantLink.objects.filter(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        self.assertEqual(links.count(), 1)
        self.assertTrue(links.first().token)
