"""U2/R2 · `capa` i `instancia` SURTEN PER L'API de `GarmentPOMMap`.

**El defecte que aquests tests tanquen.** Els dos camps eren al model des de C1/C1-ins i formen
part de la clau única `(garment_type_item, pom, capa, instancia)`, però `Meta.fields` del
serializer no els incloïa: **existien a la BD i eren invisibles per a qualsevol lector d'API**.
La pantalla del catàleg de peces en fa quatre columnes (Capa + el bloc Instància) i sense això
els seus desplegables i píndoles no tindrien on escriure.

**I la trampa que amaguen.** En completar-se la tupla de la `unique_together`, DRF hi enganxa
sol un `UniqueTogetherValidator`. Això és el que volem —un 400 net en comptes de
l'`IntegrityError`/500 d'abans— però el seu `enforce_required_fields` exigeix TOTS els camps de
la clau al `create`, i un camp de model amb `default` arriba a DRF només com a `required=False`,
sense default de serializer. Sense els `default` explícits del serializer, **tota crida que ja
existeix** —`MeasurementBaseGrid` crea amb `{garment_type_item, pom, ordre}`— **passaria a
rebre un 400 «This field is required»**. Per això el test de la no-regressió no és decoratiu:
és el que impedeix que aquesta millora trenqui la graella d'autoria d'items.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom.models import GarmentGroup, GarmentPOMMap, GarmentType, POMMaster
from fhort.tasks.models import GarmentTypeItem


class CapaInstanciaAPITest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='r2_configurador')
        # L'escriptura d'aquest ViewSet està gated CONFIGURE; el rol per defecte (technician)
        # no en té. Es rellegeix l'usuari perquè l'autenticació no arrossegui el rol cachejat.
        prof, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'R2'})
        prof.rol_nom = 'admin'
        prof.save(update_fields=['rol_nom'])
        self.user = get_user_model().objects.get(pk=self.user.pk)

        self.grup = GarmentGroup.objects.create(codi='R2_TOPS', nom='Tops')
        self.familia = GarmentType.objects.create(
            codi_client='R2_WOVEN', nom_client='Teixit pla', grup='R2_TOPS', grup_ref=self.grup)
        self.item = GarmentTypeItem.objects.create(
            garment_type=self.familia, code='r2_blouse', name='Blusa')
        self.pom = POMMaster.objects.create(codi_client='R2-A', nom_client='Amplada de pit')

        self.api = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        self.api.force_authenticate(user=self.user)
        self.url = '/api/v1/garment-pom-maps/'

    # ── LECTURA ───────────────────────────────────────────────────────────────

    def test_la_LECTURA_porta_capa_i_instancia(self):
        """Abans de R2 aquests dos camps no sortien: la pantalla no els podia ni pintar."""
        GarmentPOMMap.objects.create(
            garment_type_item=self.item, pom=self.pom, capa='folre', instancia='left-relaxed')

        resp = self.api.get(self.url, {'garment_type_item': self.item.pk})
        self.assertEqual(resp.status_code, 200)
        files = resp.data.get('results', resp.data)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['capa'], 'folre')
        self.assertEqual(files[0]['instancia'], 'left-relaxed')

    # ── ESCRIPTURA ────────────────────────────────────────────────────────────

    def test_l_ESCRIPTURA_desa_capa_i_instancia(self):
        resp = self.api.post(self.url, {
            'garment_type_item': self.item.pk, 'pom': self.pom.pk,
            'capa': 'entretela', 'instancia': 'right-extended', 'ordre': 3,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

        fila = GarmentPOMMap.objects.get(pk=resp.data['id'])
        self.assertEqual(fila.capa, 'entretela')
        self.assertEqual(fila.instancia, 'right-extended')

    def test_el_MATEIX_POM_a_DUES_capes_son_DUES_pertinences(self):
        """La raó de ser de la clau: exterior i folre del mateix POM no es trepitgen."""
        for capa in ('exterior', 'folre'):
            resp = self.api.post(self.url, {
                'garment_type_item': self.item.pk, 'pom': self.pom.pk, 'capa': capa,
            }, format='json')
            self.assertEqual(resp.status_code, 201, resp.data)

        self.assertEqual(
            GarmentPOMMap.objects.filter(garment_type_item=self.item, pom=self.pom).count(), 2)

    # ── EL DUPLICAT: 400 NET, NO UN 500 ───────────────────────────────────────

    def test_el_DUPLICAT_dona_400_i_no_un_500(self):
        """Abans de R2 la clau única no era completa al serializer: el duplicat arribava a la BD
        i petava amb `IntegrityError` — un 500 amb traça, no un missatge."""
        GarmentPOMMap.objects.create(
            garment_type_item=self.item, pom=self.pom, capa='exterior', instancia='')

        resp = self.api.post(self.url, {
            'garment_type_item': self.item.pk, 'pom': self.pom.pk,
            'capa': 'exterior', 'instancia': '',
        }, format='json')
        self.assertEqual(resp.status_code, 400, resp.data)

    def test_el_duplicat_IMPLICIT_tambe_dona_400(self):
        """Sense enviar capa ni instancia: els defaults les fan iguals a la fila que ja hi és."""
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=self.pom)

        resp = self.api.post(self.url, {
            'garment_type_item': self.item.pk, 'pom': self.pom.pk,
        }, format='json')
        self.assertEqual(resp.status_code, 400, resp.data)

    # ── LA NO-REGRESSIÓ (el motiu dels `default` explícits) ───────────────────

    def test_CREAR_sense_capa_ni_instancia_segueix_funcionant(self):
        """`MeasurementBaseGrid` crea amb `{garment_type_item, pom, ordre}` i prou. Si aquest
        test cau amb un 400 «This field is required», els `default` del serializer han
        desaparegut i la graella d'autoria d'items ha quedat trencada."""
        resp = self.api.post(self.url, {
            'garment_type_item': self.item.pk, 'pom': self.pom.pk, 'ordre': 0,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

        fila = GarmentPOMMap.objects.get(pk=resp.data['id'])
        self.assertEqual(fila.capa, 'exterior', 'el default del model ha de seguir manant')
        self.assertEqual(fila.instancia, '')

    def test_el_PATCH_parcial_no_reseteja_la_identitat(self):
        """Desar només l'ordre no pot moure de capa una fila. DRF salta els defaults en mode
        parcial i el validador omple la clau des de la instància."""
        fila = GarmentPOMMap.objects.create(
            garment_type_item=self.item, pom=self.pom, capa='folre', instancia='left-relaxed')

        resp = self.api.patch(f'{self.url}{fila.pk}/', {'ordre': 7}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)

        fila.refresh_from_db()
        self.assertEqual(fila.ordre, 7)
        self.assertEqual(fila.capa, 'folre', 'el PATCH parcial ha esborrat la capa')
        self.assertEqual(fila.instancia, 'left-relaxed')
