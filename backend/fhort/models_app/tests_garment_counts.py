"""Tests de l'endpoint garment-counts + filtre garment_type_item (models_app).

Sprint UNIFICACIÓ SELECTORS · F1. Convenció del repo: fitxer `test*.py` dins de l'app,
executat amb `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

El que defensen, en dues frases: (1) garment-counts respecta EXACTAMENT els filtres actius
—filtrar per temporada canvia els counts— perquè reusa el ModelFilter canònic C1; (2) el nou
filtre `garment_type_item` funciona al list. Patró calcat de fase-counts (views.py).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import Model
from fhort.models_app.views import ModelViewSet
from fhort.pom.models import GarmentType
from fhort.tasks.models import GarmentTypeItem


class GarmentCountsTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='pm')
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        # Re-fetch: neteja qualsevol cache negatiu de la relació inversa user.profile.
        self.user = get_user_model().objects.get(pk=self.user.pk)

        # Dues famílies (GarmentType) i dos items dins la família A.
        self.gt_a = GarmentType.objects.create(codi_client='GTA', nom_client='Família A', grup='TOPS')
        self.gt_b = GarmentType.objects.create(codi_client='GTB', nom_client='Família B', grup='TOPS')
        self.it_a1 = GarmentTypeItem.objects.create(garment_type=self.gt_a, code='a1', name='Item A1')
        self.it_a2 = GarmentTypeItem.objects.create(garment_type=self.gt_a, code='a2', name='Item A2')

        self._seq = 0
        # SS: gt_a·it_a1, gt_a·it_a2, gt_b (sense item)
        self._mk(temporada='SS', garment_type=self.gt_a, garment_type_item=self.it_a1)
        self._mk(temporada='SS', garment_type=self.gt_a, garment_type_item=self.it_a2)
        self._mk(temporada='SS', garment_type=self.gt_b)
        # FW: gt_a·it_a1
        self._mk(temporada='FW', garment_type=self.gt_a, garment_type_item=self.it_a1)
        # Soroll: un model sense garment_type ni item — no ha d'aparèixer als mapes, sí al total.
        self._mk(temporada='SS')

    def _mk(self, **kw):
        self._seq += 1
        return Model.objects.create(
            codi_intern=f'M{self._seq}', codi_tenant='TST', any=2026,
            sequencial=self._seq, **kw)

    def _counts(self, **params):
        req = APIRequestFactory().get('/api/v1/models/garment-counts/', params)
        force_authenticate(req, user=self.user)
        return ModelViewSet.as_view({'get': 'garment_counts'})(req)

    def test_counts_sense_filtre(self):
        resp = self._counts()
        self.assertEqual(resp.status_code, 200)
        d = resp.data
        self.assertEqual(d['by_type'][self.gt_a.id], 3)
        self.assertEqual(d['by_type'][self.gt_b.id], 1)
        self.assertEqual(d['by_item'][self.it_a1.id], 2)
        self.assertEqual(d['by_item'][self.it_a2.id], 1)
        # total = conjunt filtrat sencer, inclòs el model sense node.
        self.assertEqual(d['total'], 5)

    def test_filtre_temporada_canvia_els_counts(self):
        resp = self._counts(temporada='FW')
        self.assertEqual(resp.status_code, 200)
        d = resp.data
        self.assertEqual(d['by_type'], {self.gt_a.id: 1})
        self.assertNotIn(self.gt_b.id, d['by_type'])
        self.assertEqual(d['by_item'], {self.it_a1.id: 1})
        self.assertEqual(d['total'], 1)

    def test_filtre_garment_type_item_canvia_els_counts(self):
        resp = self._counts(garment_type_item=self.it_a1.id)
        self.assertEqual(resp.status_code, 200)
        d = resp.data
        self.assertEqual(d['by_item'], {self.it_a1.id: 2})
        self.assertEqual(d['total'], 2)

    def test_list_filtra_per_garment_type_item(self):
        req = APIRequestFactory().get('/api/v1/models/', {'garment_type_item': self.it_a1.id})
        force_authenticate(req, user=self.user)
        resp = ModelViewSet.as_view({'get': 'list'})(req)
        self.assertEqual(resp.status_code, 200)
        results = resp.data['results'] if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        # Dos models amb it_a1 (un SS, un FW).
        self.assertEqual(len(results), 2)
