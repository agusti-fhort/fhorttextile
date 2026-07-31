"""Els bytes d'una imatge de la fitxa creuen la xarxa EXACTAMENT UN COP.

Abans, una foto col·locada a l'editor es quedava dins de `document.json` com a dataURL i
viatjava sencera a CADA autosave — i cada autosave escriu una versió nova del `.ftt`. Ara
la imatge puja en col·locar-la (l'embut la redueix i li dona nom), els bytes van amb el
PRIMER desat que la referencia, i a partir d'aquí el document només en porta `assets/<nom>`.
"""
import datetime
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase
from PIL import Image
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app import services_ftt, services_ftt_document as svc
from fhort.models_app.ftt_document_views import (FttAssetPrepareView, FttDocumentDetailView,
                                                 _assets_del_payload)
from fhort.models_app.models import Model
from fhort.models_app.services_fitxers import MAX_COSTAT_LLARG_PX

NOM_OK = '0123456789abcdef.jpg'


def _doc(src):
    return {'ftt_schema': 1, 'metadata': {}, 'pageFormat': 'A4L',
            'pages': [{'id': 'p1', 'objects': [
                {'id': 'g', 'type': 'group', 'children': [
                    {'id': 'i', 'type': 'image', 'src': src}]}]}]}


def _soroll(mida, format='JPEG'):
    w, h = mida
    im = Image.effect_noise((max(1, w // 3), max(1, h // 3)), 64).convert('RGB')
    buf = io.BytesIO()
    im.resize(mida, Image.NEAREST).save(buf, format=format)
    return buf.getvalue()


class AssetsDelPayloadTest(SimpleTestCase):
    """El guard del PATCH: què s'accepta i què no."""

    def test_troba_la_referencia_dins_d_un_grup(self):
        """Els objectes de l'editor són un ARBRE: una imatge dins d'un grup també compta."""
        self.assertEqual(services_ftt.noms_assets_referenciats(_doc('assets/' + NOM_OK)),
                         {NOM_OK})

    def test_l_asset_referenciat_entra(self):
        sortida = _assets_del_payload({NOM_OK: 'aGVp'}, _doc('assets/' + NOM_OK))
        self.assertEqual(sortida, {NOM_OK: b'hei'})

    def test_l_asset_sense_referencia_s_ignora(self):
        """Col·locar una foto i desfer-ho abans de desar no ha de deixar-ne rastre: seria un
        orfe per sempre, perquè save_document fusiona i no poda mai."""
        self.assertEqual(_assets_del_payload({NOM_OK: 'aGVp'}, _doc('assets/altre.jpg')), {})

    def test_un_nom_que_no_ha_fet_el_servidor_es_400(self):
        """Els noms viatgen a rutes dins del zip: un nom lliure hi escriuria on volgués."""
        with self.assertRaises(ValueError):
            _assets_del_payload({'../../etc/passwd': 'aGVp'}, _doc('assets/x'))

    def test_base64_trencat_es_400(self):
        with self.assertRaises(ValueError):
            _assets_del_payload({NOM_OK: 'no soc base64!!'}, _doc('assets/' + NOM_OK))

    def test_sense_assets_no_hi_ha_res_a_fer(self):
        self.assertEqual(_assets_del_payload(None, _doc('assets/x')), {})


class EmbutDeLEditorTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='tecnic')
        UserProfile.objects.get_or_create(user=self.user, defaults={'nom_complet': 'Tècnic'})
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.model = Model.objects.create(codi_intern='A1', codi_tenant='TST', any=2026,
                                          temporada='SS26', sequencial=1)
        self.head = svc.create_document(self.model)
        self.factory = APIRequestFactory()

    def _prepara(self, nom, contingut, content_type):
        f = SimpleUploadedFile(nom, contingut, content_type=content_type)
        req = self.factory.post(f'/api/v1/ftt-documents/{self.head.pk}/prepare-asset/',
                                {'fitxer': f}, format='multipart')
        force_authenticate(req, user=self.user)
        return FttAssetPrepareView.as_view()(req, fitxer_id=self.head.pk)

    def _desa(self, document_json, assets=None):
        cos = {'document_json': document_json}
        if assets is not None:
            cos['assets'] = assets
        req = self.factory.patch(f'/api/v1/ftt-documents/{self.head.pk}/', cos, format='json')
        force_authenticate(req, user=self.user)
        return FttDocumentDetailView.as_view()(req, fitxer_id=self.head.pk)

    def test_la_foto_torna_reduida_i_amb_nom_de_contingut(self):
        resp = self._prepara('IMG_7788.jpg', _soroll((3000, 2000)), 'image/jpeg')
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual((resp.data['amplada'], resp.data['alcada']),
                         (MAX_COSTAT_LLARG_PX, 1333))
        self.assertTrue(resp.data['dataurl'].startswith('data:image/jpeg;base64,'))
        self.assertRegex(resp.data['nom'], r'^[0-9a-f]{16}\.jpg$')

    def test_el_nom_surt_del_contingut_no_de_qui_el_puja(self):
        """El mateix binari col·locat dues vegades cau al mateix nom: el .ftt no engreixa."""
        bytes_foto = _soroll((2400, 1600))
        primer = self._prepara('a.jpg', bytes_foto, 'image/jpeg').data['nom']
        segon = self._prepara('un-altre-nom.jpg', bytes_foto, 'image/jpeg').data['nom']
        self.assertEqual(primer, segon)

    def test_els_bytes_viatgen_un_cop_i_el_document_nomes_en_porta_la_referencia(self):
        svc.acquire_lock(self.head, self.user)
        prep = self._prepara('foto.jpg', _soroll((2400, 1600)), 'image/jpeg').data
        nom = prep['nom']
        b64 = prep['dataurl'].split(',', 1)[1]

        # 1r desat: el document ja porta 'assets/<nom>' i els bytes hi van a part.
        resp = self._desa(_doc('assets/' + nom), assets={nom: b64})
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.head = self.model.fitxers.get(pk=resp.data['id'])
        desat = svc.load_document(self.head)
        self.assertIn(nom, desat['assets'])
        self.assertEqual(desat['document_json']['pages'][0]['objects'][0]['children'][0]['src'],
                         'assets/' + nom)

        # 2n desat: cap byte. L'asset segueix viu perquè save_document fusiona amb l'anterior.
        resp = self._desa(_doc('assets/' + nom))
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.head = self.model.fitxers.get(pk=resp.data['id'])
        self.assertIn(nom, svc.load_document(self.head)['assets'])

    def test_el_camí_vell_amb_dataurl_inline_segueix_funcionant(self):
        """Una fitxa anterior a l'embut (o un objecte que hi arriba per un altre camí) es
        continua sanejant al servidor: aquest sprint no en trenca cap."""
        svc.acquire_lock(self.head, self.user)
        petita = _soroll((40, 30))
        import base64
        src = 'data:image/jpeg;base64,' + base64.b64encode(petita).decode()
        resp = self._desa(_doc(src))
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        desat = svc.load_document(self.model.fitxers.get(pk=resp.data['id']))
        self.assertEqual(len(desat['assets']), 1)
        self.assertTrue(
            desat['document_json']['pages'][0]['objects'][0]['children'][0]['src']
            .startswith('assets/'))
