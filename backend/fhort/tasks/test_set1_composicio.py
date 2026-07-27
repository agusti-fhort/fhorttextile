"""SET-1 · C1 — composició d'un item-conjunt: l'acció `parts/` i els guards del `clean()`.

Convenció del repo: `python manage.py test fhort.tasks` (no pytest).

`GarmentTypeItemPart.clean()` porta els dos guards que fan que un conjunt tingui forma: un item
no pot ser peça de si mateix, i un conjunt no pot contenir un altre conjunt (decisió 1: les
peces són parts internes 01/02/03, una sola alçada). Com que DRF no crida `Model.clean()` sol,
els invoca l'acció — i és aquesta cadena, no el model aïllat, la que aquests tests defensen.
"""
import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.models import GarmentType
from fhort.tasks.models import GarmentTypeItem, GarmentTypeItemPart
from fhort.tasks.views_b import GarmentTypeItemViewSet


class ComposicioSetTest(TenantTestCase):

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
        # L'acció `parts/` està gated a CONFIGURE (com tota escriptura del catàleg): cal un
        # perfil amb rol 'admin', no un superuser de Django — la capacitat viu al perfil.
        self.user = get_user_model().objects.create(username='confset')
        UserProfile.objects.update_or_create(user=self.user, defaults={'rol_nom': 'admin'})
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.gt = GarmentType.objects.create(codi_client='CMPGT', nom_client='Família',
                                             grup='SWIMWEAR')
        self.top = self._item('cmp_top', 'Top')
        self.bot = self._item('cmp_bot', 'Bottom')
        self.conjunt = self._item('cmp_set', 'Conjunt', is_set=True)

    def _item(self, code, name, **kw):
        return GarmentTypeItem.objects.create(garment_type=self.gt, code=code, name=name, **kw)

    def _put_parts(self, item, body):
        req = APIRequestFactory().put(
            f'/api/v1/garment-type-items/{item.id}/parts/', body, format='json')
        force_authenticate(req, user=self.user)
        view = GarmentTypeItemViewSet.as_view({'put': 'parts'})
        return view(req, pk=item.id)

    # ── l'acció ───────────────────────────────────────────────────────────────
    def test_put_parts_escriu_la_composicio(self):
        resp = self._put_parts(self.conjunt, [
            {'part_item': self.top.id, 'ordre': 1, 'nom_peca': 'Top'},
            {'part_item': self.bot.id, 'ordre': 2, 'nom_peca': 'Braga'},
        ])
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual([p['part_item'] for p in resp.data['parts']], [self.top.id, self.bot.id])
        self.assertEqual([p['nom_peca'] for p in resp.data['parts']], ['Top', 'Braga'])
        self.assertEqual(GarmentTypeItemPart.objects.filter(set_item=self.conjunt).count(), 2)

    def test_put_parts_es_reemplacament(self):
        self._put_parts(self.conjunt, [{'part_item': self.top.id, 'ordre': 1}])
        self._put_parts(self.conjunt, [{'part_item': self.bot.id, 'ordre': 1}])
        parts = GarmentTypeItemPart.objects.filter(set_item=self.conjunt)
        self.assertEqual(parts.count(), 1)
        self.assertEqual(parts.get().part_item_id, self.bot.id)

    def test_part_item_repetit_400(self):
        resp = self._put_parts(self.conjunt, [
            {'part_item': self.top.id}, {'part_item': self.top.id}])
        self.assertEqual(resp.status_code, 400)

    def test_body_que_no_es_llista_400(self):
        resp = self._put_parts(self.conjunt, {'part_item': self.top.id})
        self.assertEqual(resp.status_code, 400)

    # ── els guards del clean(), per l'acció ───────────────────────────────────
    def test_item_peca_de_si_mateix_400(self):
        resp = self._put_parts(self.conjunt, [{'part_item': self.conjunt.id}])
        self.assertEqual(resp.status_code, 400)

    def test_set_dins_de_set_400(self):
        altre = self._item('cmp_set2', 'Altre conjunt', is_set=True)
        resp = self._put_parts(self.conjunt, [{'part_item': altre.id}])
        self.assertEqual(resp.status_code, 400)

    def test_cicle_directe_400(self):
        """A conté B; B no pot contenir A."""
        b = self._item('cmp_setb', 'Conjunt B', is_set=True)
        GarmentTypeItemPart.objects.create(set_item=b, part_item=self.top, ordre=1)
        # `self.conjunt` conté `top`; ara `top` (que no és set) no pot contenir `conjunt` —
        # el cas real del cicle és entre dos items qualssevol.
        GarmentTypeItemPart.objects.create(set_item=self.conjunt, part_item=self.bot, ordre=1)
        fila = GarmentTypeItemPart(set_item=self.bot, part_item=self.conjunt, ordre=1)
        with self.assertRaises(ValidationError):
            fila.clean()

    def test_is_set_i_parts_surten_al_serializer(self):
        self._put_parts(self.conjunt, [{'part_item': self.top.id, 'ordre': 1, 'nom_peca': 'Top'}])
        req = APIRequestFactory().get(f'/api/v1/garment-type-items/{self.conjunt.id}/')
        force_authenticate(req, user=self.user)
        resp = GarmentTypeItemViewSet.as_view({'get': 'retrieve'})(req, pk=self.conjunt.id)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['is_set'])
        self.assertEqual(len(resp.data['parts']), 1)
        self.assertEqual(resp.data['parts'][0]['part_item_code'], 'cmp_top')
