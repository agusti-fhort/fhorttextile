"""bootstrap_tenant --additive — materialització estrictament additiva (Federació v2, P5).

Les lleis que defensen:
  · ADDITIU = crear el que falta, NO tocar MAI el que ja existeix (get_or_create, no
    update_or_create). Ni camps ni M2M d'una fila preexistent es toquen.
  · Sense el flag, el comportament actual (update_or_create, sobreescriu) queda intacte.
  · --additive contra un destí ja ACTIU no en tanca l'onboarding ni en regenera la Template.

Dos tenants reals: un ORIGEN (src) amb catàleg i un DESTÍ (test) poblat.

    cd backend && venv/bin/python manage.py test fhort.tasks.tests_bootstrap_additive
"""
import io

from django.core.management import call_command
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model, schema_context

from fhort.pom.models import POMCategory, POMMaster, SizeSystem, Target
from fhort.tenants.models import Client


class BootstrapAdditiveTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Destí'
        tenant.codi_tenant = 'DST'
        tenant.tipologia = Client.TIPOLOGIA_ESTUDI
        tenant.email_facturacio = 'd@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.set_schema_to_public()
        TenantModel = get_tenant_model()
        cls.src = TenantModel(
            schema_name='src', nom='Origen', codi_tenant='SRC',
            tipologia=Client.TIPOLOGIA_MARCA, email_facturacio='s@x.com',
        )
        cls.src.save(verbosity=0)
        cls.src.domains.create(domain='src.test.com', is_primary=True)
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.src.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        self.dest_schema = self.tenant.schema_name
        for sch in ('src', self.dest_schema):
            with schema_context(sch):
                SizeSystem.objects.all().delete()
                Target.objects.all().delete()
                POMMaster.objects.all().delete()
                POMCategory.objects.all().delete()

    def _pom(self, schema, codi, categoria=None):
        with schema_context(schema):
            return POMMaster.objects.create(codi_client=codi, nom_client=codi, categoria=categoria)

    def _ss(self, schema, codi, nom, targets=()):
        with schema_context(schema):
            ss = SizeSystem.objects.create(codi=codi, nom=nom)
            for t in targets:
                ss.targets.add(t)
            return ss

    def _target(self, schema, codi):
        with schema_context(schema):
            return Target.objects.create(codi=codi, nom_en=codi)

    def _run(self, additive=False, dry=False):
        out = io.StringIO()
        call_command('bootstrap_tenant', self.dest_schema, source='src',
                     additive=additive, dry_run=dry, stdout=out, verbosity=1)
        return out.getvalue()

    # ── additiu no toca el preexistent (camps + M2M) ───────────────────────────
    def test_additiu_no_toca_existent(self):
        self._target('src', 'T1')
        self._ss('src', 'SS-X', 'SOURCE', targets=Target.objects.none())  # M2M s'omple sota
        with schema_context('src'):
            SizeSystem.objects.get(codi='SS-X').targets.add(Target.objects.get(codi='T1'))
        self._target(self.dest_schema, 'T1')
        self._ss(self.dest_schema, 'SS-X', 'DEST-ORIG')   # sense targets

        self._run(additive=True)

        with schema_context(self.dest_schema):
            ss = SizeSystem.objects.get(codi='SS-X')
            self.assertEqual(ss.nom, 'DEST-ORIG')                 # camp intacte
            self.assertEqual(ss.targets.count(), 0)               # M2M intacta

    # ── clau nova es crea ──────────────────────────────────────────────────────
    def test_clau_nova_creada(self):
        self._ss('src', 'SS-NEW', 'NOVA')
        self._run(additive=True)
        with schema_context(self.dest_schema):
            self.assertTrue(SizeSystem.objects.filter(codi='SS-NEW', nom='NOVA').exists())

    # ── mixt: N existents + M noves ────────────────────────────────────────────
    def test_mixt_skipped_i_created(self):
        self._ss('src', 'SS-X', 'SOURCE')     # existirà al destí
        self._ss('src', 'SS-NEW', 'NOVA')     # nova
        self._ss(self.dest_schema, 'SS-X', 'DEST-ORIG')

        sortida = self._run(additive=True)

        self.assertIn('SizeSystem', sortida)
        self.assertIn('1 creats', sortida)          # SS-NEW
        self.assertIn('1 ja existien', sortida)     # SS-X
        with schema_context(self.dest_schema):
            self.assertEqual(SizeSystem.objects.get(codi='SS-X').nom, 'DEST-ORIG')   # intacte
            self.assertTrue(SizeSystem.objects.filter(codi='SS-NEW').exists())       # creada

    # ── sense el flag: comportament actual (sobreescriu) ───────────────────────
    def test_sense_additive_sobreescriu(self):
        self._ss('src', 'SS-X', 'SOURCE')
        self._ss(self.dest_schema, 'SS-X', 'DEST-ORIG')
        self._run(additive=False)
        with schema_context(self.dest_schema):
            self.assertEqual(SizeSystem.objects.get(codi='SS-X').nom, 'SOURCE')   # sobreescrit

    # ── clau AMBIGUA al destí (deute de dades): saltar i reportar, mai crear ───
    def test_additiu_clau_ambigua_al_desti(self):
        """Reprodueix el cas PROD: 2 POMMaster amb el mateix codi_client (categoria 13 i NULL)
        al destí + un tercer amb el mateix codi a l'origen → saltat, reportat, cap 3a fila."""
        with schema_context(self.dest_schema):
            cat = POMCategory.objects.create(codi='C1')
        self._pom(self.dest_schema, 'DUP-1', categoria=cat)   # categoria != NULL
        self._pom(self.dest_schema, 'DUP-1', categoria=None)  # 2a fila, categoria NULL
        self._pom('src', 'DUP-1')                             # origen: mateix codi

        sortida = self._run(additive=True)

        self.assertIn('ambigus_al_desti', sortida)
        self.assertIn('DUP-1', sortida)
        self.assertIn('2 coincidències', sortida)
        with schema_context(self.dest_schema):
            # Cap 3a fila creada; les 2 preexistents intactes.
            self.assertEqual(POMMaster.objects.filter(codi_client='DUP-1').count(), 2)

    def test_additiu_clau_unica_regressio(self):
        """Clau única normal (0/1 coincidències): comportament de P5 sense canvis."""
        self._pom(self.dest_schema, 'UNIQ')   # 1 al destí
        self._pom('src', 'UNIQ')              # mateix codi a l'origen
        sortida = self._run(additive=True)
        self.assertNotIn('ambigus_al_desti', sortida)
        with schema_context(self.dest_schema):
            self.assertEqual(POMMaster.objects.filter(codi_client='UNIQ').count(), 1)  # saltat, no duplicat

    # ── additiu amb destí actiu: onboarding i template intactes ────────────────
    def test_additive_desti_actiu_no_tanca_onboarding(self):
        with schema_context('public'):
            self.tenant.estat = 'actiu'
            self.tenant.onboarding_complet = False
            self.tenant.save(update_fields=['estat', 'onboarding_complet'])
        self._ss('src', 'SS-NEW', 'NOVA')

        sortida = self._run(additive=True)

        self.assertIn('destí actiu', sortida)   # log explícit
        with schema_context('public'):
            c = get_tenant_model().objects.get(schema_name=self.dest_schema)
            self.assertFalse(c.onboarding_complet)   # NO s'ha tancat l'onboarding
