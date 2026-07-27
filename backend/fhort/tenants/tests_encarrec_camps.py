"""RETORN-0 — l'ANADA porta l'ENCÀRREC, no només la identitat.

Fins avui `instancia_al_studio` escrivia 16 camps i cap d'ells deia QUÈ demana la marca: el
Studio rebia `codi_intern`+config i havia de tornar a preguntar la col·lecció, la descripció,
el target, la construcció, la urgència i la data objectiu — dades que la marca ja tenia
escrites a la seva pròpia fila. No era una pèrdua de feina (la feina no ha de viatjar mai):
era una pèrdua de l'encàrrec.

El que defensen aquests tests:
  1. Els 6 camps arriben al Studio amb el MATEIX valor (round-trip literal).
  2. `prioritat` NULL al Brand no peta l'INSERT: cau al default del model (la columna és
     NOT NULL i un `None` explícit seria un IntegrityError).
  3. La frontera segueix on era: `fase_actual`, `estat` i `consumption_started_at` NO viatgen.

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_encarrec_camps
"""
import datetime

from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model, schema_context

from fhort.models_app.models import Model
from fhort.tenants.federation_service import traspassa
from fhort.tenants.models import Client, TenantLink
from fhort.tasks.models import Customer

BRAND = 'BRE'
STUDIO = 'STE'


class EncarrecCampsTest(TenantTestCase):
    """Tenant per defecte = Studio. Segon tenant = Brand amb un model ben omplert."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Estudi E'
        tenant.codi_tenant = STUDIO
        tenant.tipologia = Client.TIPOLOGIA_ESTUDI
        tenant.email_facturacio = 'se@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.set_schema_to_public()
        TenantModel = get_tenant_model()
        cls.brand = TenantModel(
            schema_name='bre', nom='Marca E', codi_tenant=BRAND,
            tipologia=Client.TIPOLOGIA_MARCA, email_facturacio='me@x.com',
        )
        cls.brand.save(verbosity=0)
        cls.brand.domains.create(domain='bre.test.com', is_primary=True)
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
        with schema_context('bre'):
            Model.objects.all().delete()
            Model.objects.create(
                codi_intern='BRE-SS27-0700', codi_tenant=BRAND, any=2027, temporada='SS',
                sequencial=700, nom_prenda='Jaqueta E', studio_assignat=STUDIO,
                collection='Primavera 27', descripcio='Jaqueta curta, coll mao.',
                prioritat=1, data_objectiu=datetime.date(2027, 3, 15),
                target='Woman', construction='Woven',
                # Estat que NO ha de viatjar mai: la fase i el mèrit són de cada casa.
                fase_actual='PP', consumption_started_at='2026-01-01T10:00:00Z',
            )
            Model.objects.create(
                codi_intern='BRE-SS27-0701', codi_tenant=BRAND, any=2027, temporada='SS',
                sequencial=701, nom_prenda='Samarreta E', studio_assignat=STUDIO,
                data_objectiu=None,
            )
        with schema_context('test'):
            Model.objects.all().delete()
            Customer.objects.get_or_create(codi=BRAND, defaults={'nom': 'Marca E (extern)'})

    def _run(self, codis=None):
        return traspassa(brand_codi=BRAND, studio_codi=STUDIO, commit=True, codis=codis)

    def test_els_sis_camps_de_l_encarrec_fan_round_trip(self):
        self._run(['BRE-SS27-0700'])
        with schema_context('test'):
            m = Model.objects.get(codi_intern='BRE-SS27-0700')
            self.assertEqual(m.collection, 'Primavera 27')
            self.assertEqual(m.descripcio, 'Jaqueta curta, coll mao.')
            self.assertEqual(m.prioritat, 1)
            self.assertEqual(m.data_objectiu, datetime.date(2027, 3, 15))
            self.assertEqual(m.target, 'Woman')
            self.assertEqual(m.construction, 'Woven')

    def test_l_encarrec_buit_no_inventa_res(self):
        """Un model sense encàrrec declarat arriba amb el mateix buit, no amb valors inventats.

        `prioritat` és NOT NULL als DOS costats (no s'hi pot posar un NULL ni volent): el que
        viatja és el default 3, i el guard del servei és la xarxa per si un dia deixés de
        ser-ho — mateixa forma defensiva que `scheduler_service._ordre_model`.
        """
        self._run(['BRE-SS27-0701'])
        with schema_context('test'):
            m = Model.objects.get(codi_intern='BRE-SS27-0701')
            self.assertEqual(m.prioritat, 3)
            self.assertIsNone(m.data_objectiu)
            self.assertEqual(m.collection, '')
            self.assertIsNone(m.target)

    def test_la_frontera_no_es_mou_la_feina_no_viatja(self):
        """L'encàrrec sí; la fase, el mèrit i l'estat no. Test NEGATIU explícit."""
        self._run(['BRE-SS27-0700'])
        with schema_context('test'):
            m = Model.objects.get(codi_intern='BRE-SS27-0700')
            self.assertEqual(m.fase_actual, 'Pending')
            self.assertIsNone(m.consumption_started_at)
            self.assertEqual(m.origen, Model.ORIGEN_EXTERN)
