"""Les fotos de fitting entren per l'embut, com les d'Arxius.

Aquesta era la porta CRUA del sistema: un `ImageField` nu, sense el guard d'extensió i mida
que regeix a Arxius (D12) i sense conversió — i és per on entren les fotos de mòbil, les més
grosses i les úniques que arriben en HEIC. El que s'afirma aquí és que la porta ha deixat
de ser una excepció.
"""
import datetime
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django_tenants.test.cases import TenantTestCase
from PIL import Image
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import FittingPhoto, FittingSession
from fhort.fitting.views import FittingPhotoViewSet
from fhort.models_app.models import Model
from fhort.models_app.services_fitxers import MAX_COSTAT_LLARG_PX


def _soroll(mida, format='JPEG'):
    w, h = mida
    im = Image.effect_noise((max(1, w // 3), max(1, h // 3)), 64).convert('RGB')
    buf = io.BytesIO()
    im.resize(mida, Image.NEAREST).save(buf, format=format)
    return buf.getvalue()


def _heic(mida=(3000, 2000)):
    import pillow_heif
    pillow_heif.register_heif_opener()
    buf = io.BytesIO()
    Image.open(io.BytesIO(_soroll(mida))).save(buf, format='HEIF', quality=80)
    return buf.getvalue()


class FotoFittingEmbutTest(TenantTestCase):

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
        self.model = Model.objects.create(codi_intern='F1', codi_tenant='TST', any=2026,
                                          temporada='SS26', sequencial=1)
        self.session = FittingSession.objects.create(
            model=self.model, fase='Dev', data=datetime.date(2026, 7, 31))
        self.factory = APIRequestFactory()
        self.view = FittingPhotoViewSet.as_view({'post': 'create'})

    def _puja(self, nom, contingut, content_type):
        f = SimpleUploadedFile(nom, contingut, content_type=content_type)
        req = self.factory.post('/api/v1/fitting-photos/',
                                {'session': self.session.pk, 'fitxer': f}, format='multipart')
        force_authenticate(req, user=self.user)
        return self.view(req)

    def _desada(self, foto):
        foto.fitxer.open('rb')
        try:
            return Image.open(io.BytesIO(foto.fitxer.read()))
        finally:
            foto.fitxer.close()

    def test_foto_de_mobil_es_desa_reduida(self):
        resp = self._puja('IMG_9001.jpg', _soroll((3000, 2000)), 'image/jpeg')
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        foto = FittingPhoto.objects.get(session=self.session)
        self.assertEqual(self._desada(foto).size, (MAX_COSTAT_LLARG_PX, 1333))

    def test_heic_entra_i_es_desa_jpeg(self):
        """Abans d'aquest embut, l'ImageField de DRF les rebutjava amb un 400 que no deia res
        a qui havia fet la foto amb un iPhone."""
        resp = self._puja('IMG_9002.HEIC', _heic(), 'image/heic')
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        foto = FittingPhoto.objects.get(session=self.session)
        self.assertTrue(foto.fitxer.name.endswith('.jpg'))
        im = self._desada(foto)
        self.assertEqual(im.format, 'JPEG')
        self.assertEqual(im.size, (MAX_COSTAT_LLARG_PX, 1333))

    def test_extensio_no_permesa_400(self):
        resp = self._puja('virus.exe', b'MZ', 'application/octet-stream')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(FittingPhoto.objects.exists())

    def test_foto_petita_intacta(self):
        original = _soroll((400, 300))
        resp = self._puja('petita.jpg', original, 'image/jpeg')
        self.assertEqual(resp.status_code, 201, getattr(resp, 'data', None))
        foto = FittingPhoto.objects.get(session=self.session)
        foto.fitxer.open('rb')
        try:
            self.assertEqual(foto.fitxer.read(), original)
        finally:
            foto.fitxer.close()
