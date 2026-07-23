"""Assignació Brand→Studio com a condició del traspàs (Federació v2, P6).

Les lleis que defensen:
  · DUES CLAUS INDEPENDENTS. El TenantLink autoritza el PONT; Model.studio_assignat autoritza
    CADA MODEL. Pont obert + sense assignació = NO viatja res (el test que faltava).
  · L'assignació és per Studio concret: assignar a un altre Studio no obre aquest traspàs.
  · --revocar treu el model del traspàs següent.
  · El command d'assignació respecta el mateix guard de vincle ACTIU; els codis mal escrits
    es reporten, mai en silenci.

Dos tenants reals: un Brand (marca) amb models i un Studio (estudi).

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_assignacio
"""
import io

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model, schema_context

from fhort.accounts.models import UserProfile
from fhort.models_app.models import Model
from fhort.tenants.models import Client, TenantLink
from fhort.tasks.models import Customer

BRAND = 'BRD'
STUDIO = 'STU'
User = get_user_model()


class AssignacioTest(TenantTestCase):

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
        with schema_context('public'):
            TenantLink.objects.all().delete()
            self.link = TenantLink.objects.create(
                brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)
        with schema_context('brd'):
            Model.objects.all().delete()
            for i in range(1, 11):   # 10 models, cap assignat (studio_assignat='')
                Model.objects.create(
                    codi_intern=f'BRD-SS27-{i:04d}', codi_tenant=BRAND, any=2027,
                    temporada='SS', sequencial=i, nom_prenda=f'M{i}')
        with schema_context('test'):
            Model.objects.all().delete()
            Customer.objects.get_or_create(codi=BRAND, defaults={'nom': 'Marca'})
            u, _ = User.objects.get_or_create(username='tec', defaults={'email': 't@x.com'})
            UserProfile.objects.get_or_create(
                user=u, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})

    def _instantiate(self, commit=True):
        out = io.StringIO()
        args = ['instantiate_external_models', '--brand', BRAND, '--studio', STUDIO]
        if commit:
            args.append('--commit')
        call_command(*args, stdout=out)
        return out.getvalue()

    def _assign(self, codis, studio=STUDIO, revocar=False, commit=True):
        out = io.StringIO()
        args = ['assign_models_to_studio', '--brand', BRAND, '--studio', studio, '--codis', codis]
        if revocar:
            args.append('--revocar')
        if commit:
            args.append('--commit')
        call_command(*args, stdout=out)
        return out.getvalue()

    def _studio_count(self):
        with schema_context('test'):
            return Model.objects.count()

    # ── EL TEST QUE FALTAVA: pont obert + sense assignació = res ────────────────
    def test_sense_assignacio_no_viatja_res(self):
        sortida = self._instantiate(commit=True)
        self.assertIn('assignats a STU: 0', sortida)
        self.assertEqual(self._studio_count(), 0)   # 10 models al Brand, 0 viatgen

    # ── assignar 3 de 10 → instantiate crea exactament 3 ───────────────────────
    def test_assignar_3_crea_3(self):
        self._assign('BRD-SS27-0001,BRD-SS27-0002,BRD-SS27-0003')
        self._instantiate(commit=True)
        self.assertEqual(self._studio_count(), 3)
        with schema_context('test'):
            self.assertTrue(Model.objects.filter(codi_intern='BRD-SS27-0001', origen=Model.ORIGEN_EXTERN).exists())
            self.assertFalse(Model.objects.filter(codi_intern='BRD-SS27-0004').exists())

    # ── assignació a un Studio diferent del vincle → no viatja ─────────────────
    def test_assignacio_a_altre_studio_no_viatja(self):
        with schema_context('brd'):   # assignat a un Studio que NO és el del traspàs
            Model.objects.filter(codi_intern__in=['BRD-SS27-0001', 'BRD-SS27-0002']).update(
                studio_assignat='OTH')
        self._instantiate(commit=True)
        self.assertEqual(self._studio_count(), 0)   # assignats a OTH, no a STU

    # ── --revocar treu el model del traspàs següent ────────────────────────────
    def test_revocar_treu_del_traspas(self):
        self._assign('BRD-SS27-0001,BRD-SS27-0002,BRD-SS27-0003')
        self._assign('BRD-SS27-0001,BRD-SS27-0002,BRD-SS27-0003', revocar=True)
        self._instantiate(commit=True)
        self.assertEqual(self._studio_count(), 0)
        with schema_context('brd'):   # els models segueixen al Brand
            self.assertEqual(Model.objects.count(), 10)

    # ── command sense vincle ACTIU → error dur ─────────────────────────────────
    def test_command_sense_vincle_actiu_error(self):
        with schema_context('public'):
            self.link.aturar()
        with self.assertRaises(CommandError):
            self._assign('BRD-SS27-0001')

    # ── codis inexistents → reportats, no silenciats ───────────────────────────
    def test_codis_inexistents_reportats(self):
        sortida = self._assign('BRD-SS27-0001,BRD-NO-EXISTEIX')
        self.assertIn('NO trobats al Brand: 1', sortida)
        self.assertIn('BRD-NO-EXISTEIX', sortida)
        with schema_context('brd'):
            self.assertEqual(Model.objects.filter(studio_assignat=STUDIO).count(), 1)   # només el bo
