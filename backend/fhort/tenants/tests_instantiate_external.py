"""instantiate_external_models — el Studio instancia els models del Brand com a EXTERN.

Les lleis que defensen (Federació v2, P3):
  · EL VINCLE MANA. Sense TenantLink ACTIU no es fa res (sense vincle o aturat → error dur).
  · IDENTITAT + CONFIGURACIÓ, MAI FEINA. L'EXTERN conserva codi i sequencial del Brand,
    neix origen=EXTERN, i el signal li crea la SF buida — però no arrossega mesures ni regles.
  · NO ENVERINA LA SEQÜÈNCIA. Un EXTERN amb sequencial alt no fa saltar el comptador del
    Studio (integració amb P2).
  · IDEMPOTENT per codi_intern; config no aparellada → camp NULL + informe, mai bloqueig.

Es munten DOS tenants reals: un Brand (marca) amb models, i un Studio (estudi) buit.

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_instantiate_external
"""
import io

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model, schema_context

from fhort.accounts.models import UserProfile
from fhort.models_app.models import Model
from fhort.models_app.services import reserve_sequence_range
from fhort.pom.models import SizeSystem
from fhort.tenants.models import Client, TenantLink
from fhort.tasks.models import Customer

BRAND = 'BRD'
STUDIO = 'STU'
User = get_user_model()


class InstantiateExternalTest(TenantTestCase):
    """Tenant per defecte = Studio (estudi). Segon tenant = Brand (marca) amb models."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Estudi'
        tenant.codi_tenant = STUDIO
        tenant.tipologia = Client.TIPOLOGIA_ESTUDI
        tenant.email_facturacio = 's@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.set_schema_to_public()
        TenantModel = get_tenant_model()
        cls.brand = TenantModel(
            schema_name='brd', nom='Marca', codi_tenant=BRAND,
            tipologia=Client.TIPOLOGIA_MARCA, email_facturacio='m@x.com',
        )
        cls.brand.save(verbosity=0)
        cls.brand.domains.create(domain='brd.test.com', is_primary=True)
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.brand.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        # Vincle viu Brand→Studio.
        with schema_context('public'):
            TenantLink.objects.all().delete()
            self.link = TenantLink.objects.create(
                brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)

        # Brand: 3 models canònics amb sequencial ALT; el 1r porta un size_system natural.
        with schema_context('brd'):
            Model.objects.all().delete()
            SizeSystem.objects.all().delete()
            ss = SizeSystem.objects.create(codi='SYS-A', nom='Sistema A')
            self._brand_model('BRD-SS27-4711', 4711, size_system=ss)
            self._brand_model('BRD-SS27-4712', 4712)
            self._brand_model('BRD-SS27-4713', 4713)

        # Studio: buit de models; hi ha el Customer del Brand i un perfil (per al signal de la SF).
        with schema_context('test'):
            Model.objects.all().delete()
            Customer.objects.get_or_create(codi=BRAND, defaults={'nom': 'Marca (extern)'})
            u, _ = User.objects.get_or_create(username='tec', defaults={'email': 't@x.com'})
            UserProfile.objects.get_or_create(
                user=u, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})

    def _brand_model(self, codi, seq, size_system=None):
        # P6: el traspàs exigeix assignació explícita del Brand a aquest Studio.
        return Model.objects.create(
            codi_intern=codi, codi_tenant=BRAND, any=2027, temporada='SS',
            sequencial=seq, nom_prenda=codi, size_system=size_system,
            studio_assignat=STUDIO,
        )

    def _run(self, commit=False, limit=None, brand=BRAND, studio=STUDIO):
        out = io.StringIO()
        args = ['instantiate_external_models', '--brand', brand, '--studio', studio]
        if commit:
            args.append('--commit')
        if limit is not None:
            args += ['--limit', str(limit)]
        call_command(*args, stdout=out)
        return out.getvalue()

    # ── el vincle mana ─────────────────────────────────────────────────────────
    def test_sense_vincle_error(self):
        with self.assertRaises(CommandError):
            self._run(brand='NOPE')

    def test_vincle_aturat_error(self):
        with schema_context('public'):
            self.link.aturar()
        with self.assertRaises(CommandError):
            self._run(commit=True)

    def test_vincle_revocat_error(self):
        with schema_context('public'):
            self.link.revocar()
        with self.assertRaises(CommandError):
            self._run(commit=True)

    # ── creació EXTERN ─────────────────────────────────────────────────────────
    def test_creacio_extern_conserva_identitat_i_dispara_signals(self):
        self._run(commit=True)
        with schema_context('test'):
            m = Model.objects.get(codi_intern='BRD-SS27-4711')
            self.assertEqual(m.origen, Model.ORIGEN_EXTERN)
            self.assertEqual(m.sequencial, 4711)
            self.assertEqual(m.customer.codi, BRAND)
            # signal sync_size_fitting → SF buida creada
            from fhort.fitting.models import SizeFitting
            self.assertTrue(SizeFitting.objects.filter(model=m).exists())
            self.assertEqual(Model.objects.filter(origen=Model.ORIGEN_EXTERN).count(), 3)

    def test_extern_no_fa_saltar_la_sequencia_del_studio(self):
        self._run(commit=True)
        with schema_context('test'):
            customer = Customer.objects.get(codi=BRAND)
            # Tot el que hi ha és EXTERN (sequencial 4711-4713) → el terra local segueix a 0.
            first, last = reserve_sequence_range(customer, 2027, 'SS', 2)
            self.assertEqual((first, last), (1, 2))

    # ── idempotència ───────────────────────────────────────────────────────────
    def test_idempotent(self):
        primer = self._run(commit=True)
        self.assertIn('creats           : 3', primer)
        segon = self._run(commit=True)
        self.assertIn('creats           : 0', segon)
        self.assertIn('saltats (ja hi són): 3', segon)
        with schema_context('test'):
            self.assertEqual(Model.objects.count(), 3)

    # ── config no aparellada ───────────────────────────────────────────────────
    def test_config_no_aparellada_crea_amb_null_i_informa(self):
        # El Studio NO té SYS-A → el model 4711 es crea amb size_system NULL i s'informa.
        sortida = self._run(commit=True)
        self.assertIn('config NO aparellada', sortida)
        self.assertIn('SYS-A', sortida)
        with schema_context('test'):
            m = Model.objects.get(codi_intern='BRD-SS27-4711')
            self.assertIsNone(m.size_system_id)   # no bloqueja: NULL
            self.assertEqual(Model.objects.count(), 3)   # els 3 es creen igualment

    def test_config_aparellada_es_resol(self):
        # Amb SYS-A present al Studio, el pointer es resol.
        with schema_context('test'):
            SizeSystem.objects.create(codi='SYS-A', nom='Sistema A (studio)')
        self._run(commit=True)
        with schema_context('test'):
            m = Model.objects.get(codi_intern='BRD-SS27-4711')
            self.assertIsNotNone(m.size_system_id)
            self.assertEqual(m.size_system.codi, 'SYS-A')

    # ── dry-run ────────────────────────────────────────────────────────────────
    def test_dry_run_no_escriu(self):
        sortida = self._run(commit=False)
        self.assertIn('DRY-RUN', sortida)
        self.assertIn('a crear          : 3', sortida)
        with schema_context('test'):
            self.assertEqual(Model.objects.count(), 0)

    def test_limit(self):
        sortida = self._run(commit=False, limit=2)
        self.assertIn('llegits (assignats): 2', sortida)
