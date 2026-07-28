"""Pujada de fotos HEIC (iPhone) als fitxers del model: entren HEIC, es desen JPEG.

Cas real: les fotos de fitting es fan amb el mòbil i un iPhone les desa en HEIC, que cap
navegador d'escriptori no pinta. La decisió és acceptar-les a la pujada i convertir-les al
servidor: el que arriba a la cadena de versions de `ModelFitxer` és SEMPRE un `.jpg`, i
l'original no es desa.

Les fixtures HEIC es fabriquen aquí amb `pillow_heif` (que també sap ESCRIURE HEIF) en lloc
de commitar un binari: així la prova diu què hi ha dins de la imatge —mida, color,
orientació— i pot afirmar sobre el resultat.
"""
import datetime
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django_tenants.test.cases import TenantTestCase
from PIL import Image
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import Model, ModelFitxer
from fhort.models_app.views import upload_file_view


def _heic_bytes(mida=(40, 20), color=(200, 30, 30), orientacio=None):
    """HEIC de debò, opcionalment amb el tag EXIF d'orientació."""
    import pillow_heif
    pillow_heif.register_heif_opener()
    im = Image.new('RGB', mida, color)
    buf = io.BytesIO()
    if orientacio is not None:
        exif = im.getexif()
        exif[274] = orientacio          # 274 = Orientation
        im.save(buf, format='HEIF', quality=80, exif=exif.tobytes())
    else:
        im.save(buf, format='HEIF', quality=80)
    return buf.getvalue()


def _jpeg_bytes(mida=(30, 30), color=(0, 120, 200)):
    buf = io.BytesIO()
    Image.new('RGB', mida, color).save(buf, format='JPEG', quality=90)
    return buf.getvalue()


def _png_bytes(mida=(12, 12)):
    buf = io.BytesIO()
    Image.new('RGBA', mida, (0, 0, 0, 0)).save(buf, format='PNG')
    return buf.getvalue()


class UploadHeicTest(TenantTestCase):

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
        self.model = Model.objects.create(codi_intern='H1', codi_tenant='TST', any=2026,
                                          temporada='SS26', sequencial=1)
        self.factory = APIRequestFactory()

    def _puja(self, nom, contingut, content_type):
        fitxer = SimpleUploadedFile(nom, contingut, content_type=content_type)
        req = self.factory.post(f'/api/v1/models/{self.model.pk}/upload-fitxer/',
                                {'fitxer': fitxer}, format='multipart')
        force_authenticate(req, user=self.user)
        return upload_file_view(req, model_id=self.model.pk)

    def _imatge_desada(self, mf):
        mf.fitxer.open('rb')
        try:
            return Image.open(io.BytesIO(mf.fitxer.read()))
        finally:
            mf.fitxer.close()

    # ── HEIC → JPEG ──────────────────────────────────────────────────────────
    def test_heic_es_desa_com_a_jpg(self):
        resp = self._puja('IMG_4821.HEIC', _heic_bytes(), 'image/heic')
        self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))

        mf = ModelFitxer.objects.get(model=self.model)
        self.assertEqual(mf.nom_fitxer, 'IMG_4821.jpg')     # nom original, extensió .jpg
        self.assertTrue(mf.fitxer.name.endswith('.jpg'))
        self.assertEqual(mf.mimetype, 'image/jpeg')
        # I el que hi ha desat és un JPEG de debò, no una HEIC amb un nom nou.
        self.assertEqual(self._imatge_desada(mf).format, 'JPEG')

    def test_no_es_desa_cap_heic(self):
        self._puja('IMG_4821.HEIC', _heic_bytes(), 'image/heic')
        noms = [f.nom_fitxer.lower() for f in ModelFitxer.objects.all()]
        self.assertEqual(len(noms), 1)                       # NOMÉS el JPEG
        self.assertFalse(any(n.endswith(('.heic', '.heif')) for n in noms))

    def test_heif_minuscula_i_mime_sense_extensio_reconeguda(self):
        """Safari de vegades puja la foto amb nom .jpg i el content_type correcte: mana el MIME."""
        self.assertIn(self._puja('foto.heif', _heic_bytes(), 'image/heif').status_code, (200, 201))
        self.assertIn(self._puja('safari.jpg', _heic_bytes(), 'image/heic').status_code, (200, 201))
        for mf in ModelFitxer.objects.all():
            self.assertEqual(self._imatge_desada(mf).format, 'JPEG')

    def test_orientacio_exif_aplicada(self):
        """Orientation=6 = girada 90°. La foto es desa DRETA: una 40×20 surt 20×40.

        S'afirma el RESULTAT, no el mecanisme: avui qui aplica el gir és el descodificador de
        `pillow_heif` (torna la imatge dreta i el tag a 1) i `exif_transpose` hi és de xarxa.
        """
        resp = self._puja('girada.heic', _heic_bytes(mida=(40, 20), orientacio=6), 'image/heic')
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(self._imatge_desada(ModelFitxer.objects.get(model=self.model)).size,
                         (20, 40))

    def test_sense_orientacio_la_mida_no_es_toca(self):
        self._puja('dreta.heic', _heic_bytes(mida=(40, 20)), 'image/heic')
        self.assertEqual(self._imatge_desada(ModelFitxer.objects.get(model=self.model)).size,
                         (40, 20))

    # ── Errors: 422, mai 500 ─────────────────────────────────────────────────
    def test_heic_corrupte_retorna_422(self):
        resp = self._puja('trencada.heic', b'no soc una imatge, nomes bytes', 'image/heic')
        self.assertEqual(resp.status_code, 422)
        self.assertIn('error', resp.data)
        self.assertFalse(ModelFitxer.objects.exists())       # no es desa res a mitges

    def test_heic_truncada_retorna_422(self):
        resp = self._puja('mitja.heic', _heic_bytes()[:60], 'image/heic')
        self.assertEqual(resp.status_code, 422)
        self.assertFalse(ModelFitxer.objects.exists())

    # ── NO-REGRESSIÓ: la resta de pujades no es toquen ───────────────────────
    def test_jpeg_intacte(self):
        original = _jpeg_bytes()
        resp = self._puja('foto.jpg', original, 'image/jpeg')
        self.assertIn(resp.status_code, (200, 201))
        mf = ModelFitxer.objects.get(model=self.model)
        self.assertEqual(mf.nom_fitxer, 'foto.jpg')
        mf.fitxer.open('rb')
        try:
            self.assertEqual(mf.fitxer.read(), original)     # byte a byte: no es reconverteix
        finally:
            mf.fitxer.close()

    def test_png_intacte(self):
        original = _png_bytes()
        resp = self._puja('sketch.png', original, 'image/png')
        self.assertIn(resp.status_code, (200, 201))
        mf = ModelFitxer.objects.get(model=self.model)
        self.assertEqual(mf.nom_fitxer, 'sketch.png')
        mf.fitxer.open('rb')
        try:
            self.assertEqual(mf.fitxer.read(), original)
        finally:
            mf.fitxer.close()

    def test_extensio_no_permesa_segueix_donant_400(self):
        resp = self._puja('virus.exe', b'MZ', 'application/octet-stream')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ModelFitxer.objects.exists())
