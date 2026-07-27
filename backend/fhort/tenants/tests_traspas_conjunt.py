"""SET-1 · C6 — el traspàs Brand→Studio CONSERVA el conjunt.

Fins ara `federation_service` no propagava ni `garment_set` ni `piece_number` (llista de camps
explícita, `:163-177`): un conjunt traspassat arribava al Studio com a N models solts amb codis
`-01`/`-02` i **la unitat comercial es dissolia en silenci** (risc #2 del dimensionat §A2). Res
fallava; simplement el producte que el client va comprar deixava d'existir a l'altra banda.

El que defensen aquests tests:
  1. Traspassar 2 de 3 parts → al Studio hi ha UN `GarmentSet` (clau natural `codi_base`) amb
     els 2 Models ben numerats.
  2. Re-traspassar la 3a → s'enganxa al MATEIX set, cap duplicat (`get_or_create` és el que fa
     que l'ordre i el nombre d'execucions siguin indiferents).
  3. `consumption_started_at` NO viatja: el mèrit és per tenant i el Studio no ha meritat res
     per rebre un model.
  4. `ConsumptionRecord` no viatja mai (confirmació, no canvi).

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_traspas_conjunt
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model, schema_context

from fhort.accounts.models import UserProfile
from fhort.models_app.models import ConsumptionRecord, GarmentSet, Model
from fhort.tenants.federation_service import traspassa
from fhort.tenants.models import Client, TenantLink
from fhort.tasks.models import Customer

BRAND = 'BRC'
STUDIO = 'STC'
User = get_user_model()


class TraspasConjuntTest(TenantTestCase):
    """Tenant per defecte = Studio. Segon tenant = Brand, amb un conjunt de 3 peces."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Estudi C'
        tenant.codi_tenant = STUDIO
        tenant.tipologia = Client.TIPOLOGIA_ESTUDI
        tenant.email_facturacio = 'sc@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.set_schema_to_public()
        TenantModel = get_tenant_model()
        cls.brand = TenantModel(
            schema_name='brc', nom='Marca C', codi_tenant=BRAND,
            tipologia=Client.TIPOLOGIA_MARCA, email_facturacio='mc@x.com',
        )
        cls.brand.save(verbosity=0)
        cls.brand.domains.create(domain='brc.test.com', is_primary=True)
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.brand.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        with schema_context('public'):
            TenantLink.objects.all().delete()
            TenantLink.objects.create(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)

        with schema_context('brc'):
            Model.objects.all().delete()
            GarmentSet.objects.all().delete()
            self.gs_codi = 'BRC-SS27-0500'
            gs = GarmentSet.objects.create(codi_base=self.gs_codi, nom_comercial='Trio',
                                           num_pieces=3)
            # El conjunt ja ha meritat AL BRAND: la marca no ha de viatjar.
            GarmentSet.objects.filter(pk=gs.pk).update(
                consumption_started_at='2026-01-01T10:00:00Z')
            for i in (1, 2, 3):
                Model.objects.create(
                    codi_intern=f'{self.gs_codi}-{i:02d}', codi_tenant=BRAND, any=2027,
                    temporada='SS', sequencial=500, nom_prenda=f'Peça {i}',
                    garment_set=gs, piece_number=i, studio_assignat=STUDIO)

        with schema_context('test'):
            Model.objects.all().delete()
            GarmentSet.objects.all().delete()
            Customer.objects.get_or_create(codi=BRAND, defaults={'nom': 'Marca C (extern)'})
            u, _ = User.objects.get_or_create(username='tecc', defaults={'email': 'tc@x.com'})
            UserProfile.objects.get_or_create(
                user=u, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})

    def _run(self, codis):
        # Es crida el SERVEI, no el command: `--codis` no és una opció de CLI (la selecció per
        # codis és de l'endpoint) i afegir-l'hi seria ampliar l'abast per a un test.
        return traspassa(brand_codi=BRAND, studio_codi=STUDIO, commit=True, codis=codis)

    def test_dues_parts_creen_un_sol_conjunt_al_desti(self):
        self._run([f'{self.gs_codi}-01', f'{self.gs_codi}-02'])
        with schema_context('test'):
            self.assertEqual(GarmentSet.objects.count(), 1)
            gs = GarmentSet.objects.get()
            self.assertEqual(gs.codi_base, self.gs_codi)
            self.assertEqual(gs.nom_comercial, 'Trio')
            self.assertEqual(gs.num_pieces, 3)
            peces = list(Model.objects.filter(garment_set=gs).order_by('piece_number'))
            self.assertEqual([p.piece_number for p in peces], [1, 2])
            self.assertEqual([p.codi_intern for p in peces],
                             [f'{self.gs_codi}-01', f'{self.gs_codi}-02'])

    def test_la_tercera_part_s_enganxa_al_mateix_set(self):
        self._run([f'{self.gs_codi}-01', f'{self.gs_codi}-02'])
        self._run([f'{self.gs_codi}-03'])
        with schema_context('test'):
            self.assertEqual(GarmentSet.objects.count(), 1)   # cap duplicat
            gs = GarmentSet.objects.get()
            self.assertEqual(Model.objects.filter(garment_set=gs).count(), 3)
            self.assertEqual(
                sorted(Model.objects.filter(garment_set=gs).values_list('piece_number', flat=True)),
                [1, 2, 3])

    def test_el_merit_no_viatja(self):
        """El mèrit és per tenant: el Studio no ha meritat res per rebre un model."""
        self._run([f'{self.gs_codi}-01'])
        with schema_context('test'):
            gs = GarmentSet.objects.get()
            self.assertIsNone(gs.consumption_started_at)
            self.assertEqual(ConsumptionRecord.objects.count(), 0)
            self.assertIsNone(Model.objects.get().consumption_started_at)
        # I al Brand la marca segueix intacta.
        with schema_context('brc'):
            self.assertIsNotNone(GarmentSet.objects.get().consumption_started_at)
