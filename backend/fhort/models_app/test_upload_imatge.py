"""L'embut d'imatge del servidor: tota imatge que entra surt pintable i de mida raonable.

La reducció és una operació que DESTRUEIX píxels, i per això les seves lleis s'afirmen una
a una: què es toca, què no es toca (byte a byte), i què passa quan Pillow no sap llegir el
que li donen. La conversió HEIC té la seva pròpia suite a `test_upload_heic.py`; aquí només
s'hi comprova que segueix vivint DINS de l'embut i que també redueix.
"""
import datetime
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase
from PIL import Image
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import Model, ModelFitxer
from fhort.models_app.services_fitxers import (MAX_ADJUNT_DIM, MAX_COSTAT_LLARG_PX,
                                               redueix_imatge)
from fhort.models_app.views import upload_file_view


def _imatge(mida, mode='RGB', format='JPEG'):
    """Bytes d'una imatge de SOROLL. Un color pla es comprimeix a no res i mentiria sobre si
    la reducció aprima; el soroll pesa com pesa una foto. Es genera petit i s'amplia amb
    NEAREST perquè el test no s'hi passi segons escrivint píxels un a un."""
    w, h = mida
    base = Image.effect_noise((max(1, w // 3), max(1, h // 3)), 64).convert('RGB')
    im = base.resize(mida, Image.NEAREST)
    if mode != 'RGB':
        im = im.convert(mode)
    buf = io.BytesIO()
    im.save(buf, format=format)
    return buf.getvalue()


def _puja(nom, contingut, content_type):
    """Un upload com el que arriba del navegador, passat per l'embut."""
    f = SimpleUploadedFile(nom, contingut, content_type=content_type)
    return redueix_imatge(f, nom, content_type)


def _obre(fitxer):
    fitxer.seek(0)
    return Image.open(io.BytesIO(fitxer.read()))


class EmbutImatgeTest(SimpleTestCase):

    # ── El que SÍ es toca ────────────────────────────────────────────────────
    def test_foto_gran_es_redueix_i_conserva_la_proporcio(self):
        f, nom = _puja('foto.jpg', _imatge((3000, 2000)), 'image/jpeg')
        im = _obre(f)
        self.assertEqual(im.size, (MAX_COSTAT_LLARG_PX, 1333))
        self.assertEqual(im.format, 'JPEG')
        self.assertEqual(nom, 'foto.jpg')

    def test_la_reduccio_aprima_el_fitxer(self):
        original = _imatge((3000, 2000))
        f, _ = _puja('foto.jpg', original, 'image/jpeg')
        self.assertLess(f.size, len(original))

    def test_png_sense_alfa_surt_jpeg(self):
        """La llei per defecte és JPEG: un PNG opac de 3000 px és una foto amb un contenidor
        que li va gran."""
        f, nom = _puja('sketch.png', _imatge((3000, 1000), format='PNG'), 'image/png')
        self.assertEqual(nom, 'sketch.jpg')
        self.assertEqual(_obre(f).format, 'JPEG')

    def test_png_amb_alfa_es_redueix_pero_es_queda_png(self):
        """Aplanar l'alfa contra un fons destruiria el retall d'un sketch: es redueix i prou."""
        f, nom = _puja('retall.png', _imatge((2400, 2400), mode='RGBA', format='PNG'),
                       'image/png')
        im = _obre(f)
        self.assertEqual(nom, 'retall.png')
        self.assertEqual(im.format, 'PNG')
        self.assertEqual(im.size, (MAX_COSTAT_LLARG_PX, MAX_COSTAT_LLARG_PX))
        self.assertIn('A', im.getbands())

    # ── El que NO es toca ────────────────────────────────────────────────────
    def test_imatge_que_ja_compleix_torna_byte_a_byte(self):
        original = _imatge((MAX_COSTAT_LLARG_PX, 800))
        f, nom = _puja('ok.jpg', original, 'image/jpeg')
        f.seek(0)
        self.assertEqual(f.read(), original)      # el límit exacte NO és "massa gran"
        self.assertEqual(nom, 'ok.jpg')

    def test_gif_intacte(self):
        """Pillow en llegiria només el primer fotograma: reduir no pot matar una animació."""
        original = _imatge((3000, 100), format='GIF')
        f, _ = _puja('anim.gif', original, 'image/gif')
        f.seek(0)
        self.assertEqual(f.read(), original)

    def test_no_raster_hi_passa_de_llarg(self):
        original = b'%PDF-1.4 no soc una imatge'
        f, nom = _puja('patro.pdf', original, 'application/pdf')
        f.seek(0)
        self.assertEqual(f.read(), original)
        self.assertEqual(nom, 'patro.pdf')

    def test_imatge_il_legible_es_desa_tal_qual(self):
        """Llei de `pom_vision_service`: un downscale no bloqueja mai una pujada. Si el fitxer
        no serveix ja ho dirà qui l'obri — l'embut no és el guard d'entrada."""
        original = b'aixo no es cap png'
        f, nom = _puja('trencada.png', original, 'image/png')
        f.seek(0)
        self.assertEqual(f.read(), original)
        self.assertEqual(nom, 'trencada.png')


class UploadImatgeDoorTest(TenantTestCase):
    """La porta d'Arxius desa el que l'embut ha tornat, no el que ha arribat."""

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
        self.model = Model.objects.create(codi_intern='I1', codi_tenant='TST', any=2026,
                                          temporada='SS26', sequencial=1)
        self.factory = APIRequestFactory()

    def test_la_foto_gran_arriba_reduida_a_la_bd(self):
        original = _imatge((3000, 2000))
        fitxer = SimpleUploadedFile('mobil.jpg', original, content_type='image/jpeg')
        req = self.factory.post(f'/api/v1/models/{self.model.pk}/upload-fitxer/',
                                {'fitxer': fitxer}, format='multipart')
        force_authenticate(req, user=self.user)
        resp = upload_file_view(req, model_id=self.model.pk)
        self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))

        mf = ModelFitxer.objects.get(model=self.model)
        mf.fitxer.open('rb')
        try:
            desat = mf.fitxer.read()
        finally:
            mf.fitxer.close()
        # El sostre dels ADJUNTS de model és MAX_ADJUNT_DIM, no el de l'embut per defecte:
        # una imatge de referència es consulta al visor, no es mira a prop com un asset del
        # `.ftt` (Agus, 02/08). La porta i el coll el comparteixen; vegeu `upload_file_view`.
        self.assertEqual(Image.open(io.BytesIO(desat)).size, (MAX_ADJUNT_DIM, 1000))
        # `mida_bytes` descriu el que hi ha al disc, no el que va sortir del mòbil.
        self.assertEqual(mf.mida_bytes, len(desat))
        self.assertLess(mf.mida_bytes, len(original))
