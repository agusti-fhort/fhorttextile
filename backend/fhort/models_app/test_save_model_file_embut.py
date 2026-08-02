"""L'embut d'imatge al COLL de la cadena de versions, no només a les portes.

`upload_file_view` ja reduïa les imatges abans de cridar `save_model_file`, però és una
porta de moltes: la còpia model→model, l'import de catàleg→model, la federació i el
re-import d'extracció hi entraven per un altre costat i desaven els bytes crus. Aquí
s'afirma la llei al lloc on tots conflueixen: el que queda desat a `ModelFitxer` és
sempre pintable i de mida raonable, vingui d'on vingui.

Les afirmacions es fan sobre el fitxer REALMENT desat (`fitxer.fitxer`), no sobre el que
ha tornat l'embut: el que es prova és que les metadades i els bytes descriuen la mateixa
cosa. La suite de l'embut en si viu a `test_upload_imatge.py`; aquesta no la repeteix.
"""
import datetime
import hashlib
import io

from django.core.files.base import ContentFile
from django_tenants.test.cases import TenantTestCase
from PIL import Image

from fhort.models_app.models import Model, ModelFitxer
from fhort.models_app.services_fitxers import MAX_ADJUNT_DIM, save_model_file


def _imatge(mida, mode='RGB', format='JPEG'):
    """Bytes d'una imatge de SOROLL: un color pla es comprimeix a no res i mentiria sobre
    si la reducció aprima de debò. Mateix criteri que `test_upload_imatge`."""
    w, h = mida
    base = Image.effect_noise((max(1, w // 3), max(1, h // 3)), 64).convert('RGB')
    im = base.resize(mida, Image.NEAREST)
    if mode != 'RGB':
        im = im.convert(mode)
    buf = io.BytesIO()
    im.save(buf, format=format)
    return buf.getvalue()


def _heic(mida=(3000, 2000)):
    import pillow_heif
    pillow_heif.register_heif_opener()
    buf = io.BytesIO()
    Image.new('RGB', mida, (200, 30, 30)).save(buf, format='HEIF', quality=80)
    return buf.getvalue()


class EmbutAlCollTest(TenantTestCase):

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
        self.model = Model.objects.create(codi_intern='I1', codi_tenant='TST', any=2026,
                                          temporada='SS26', sequencial=1)

    def _desa(self, nom, contingut, **kw):
        """Una crida DIRECTA al servei, sense passar per cap porta: és exactament el que fan
        la còpia model→model, la federació i l'import de catàleg."""
        return save_model_file(self.model, ContentFile(contingut, name=nom), nom=nom, **kw)

    def _bytes_desats(self, fitxer):
        fitxer.fitxer.open('rb')
        try:
            return fitxer.fitxer.read()
        finally:
            fitxer.fitxer.close()

    # ── El que SÍ passa per l'embut ──────────────────────────────────────────
    def test_foto_gran_arriba_reduida_a_la_bd(self):
        original = _imatge((3000, 2000))
        fitxer = self._desa('IMG_4821.jpg', original, tipus='ALTRES')

        desats = self._bytes_desats(fitxer)
        im = Image.open(io.BytesIO(desats))
        self.assertEqual(im.size, (MAX_ADJUNT_DIM, 1000))
        self.assertLess(len(desats), len(original))

    def test_les_metadades_descriuen_el_fitxer_desat_no_loriginal(self):
        """L'ORDRE del fix: reduir primer, mesurar després. Si es calculessin sobre
        l'original, `mida_bytes` i `checksum` descriurien un fitxer que no existeix — i el
        checksum és justament el que la federació compara per no encadenar duplicats."""
        original = _imatge((3000, 2000))
        fitxer = self._desa('IMG_4821.jpg', original, tipus='ALTRES')

        desats = self._bytes_desats(fitxer)
        self.assertEqual(fitxer.mida_bytes, len(desats))
        self.assertEqual(fitxer.checksum, hashlib.sha256(desats).hexdigest())
        self.assertNotEqual(fitxer.checksum, hashlib.sha256(original).hexdigest())

    def test_png_amb_alfa_es_queda_png(self):
        """Aplanar l'alfa contra un fons destruiria el retall d'un sketch."""
        fitxer = self._desa('retall.png', _imatge((2400, 2400), mode='RGBA', format='PNG'),
                            tipus='ALTRES')

        self.assertEqual(fitxer.nom_fitxer, 'retall.png')
        im = Image.open(io.BytesIO(self._bytes_desats(fitxer)))
        self.assertEqual(im.format, 'PNG')
        self.assertEqual(im.size, (MAX_ADJUNT_DIM, MAX_ADJUNT_DIM))
        self.assertIn('A', im.getbands())

    def test_heic_es_desa_com_a_jpg(self):
        original = _heic()
        fitxer = self._desa('IMG_4821.heic', original, tipus='ALTRES')

        self.assertTrue(fitxer.nom_fitxer.endswith('.jpg'))
        self.assertTrue(fitxer.fitxer.name.endswith('.jpg'))
        self.assertEqual(fitxer.mimetype, 'image/jpeg')
        desats = self._bytes_desats(fitxer)
        im = Image.open(io.BytesIO(desats))
        self.assertEqual(im.format, 'JPEG')          # JPEG de debò, no una HEIC rebatejada
        self.assertEqual(im.size, (MAX_ADJUNT_DIM, 1000))
        self.assertLess(len(desats), len(original) * 4)

    # ── El que NO el toca ────────────────────────────────────────────────────
    def test_dxf_intacte_byte_a_byte(self):
        """Els no-ràsters no arriben ni a obrir-se: el patró CAD és el fitxer de treball
        del taller i un sol byte canviat el trencaria."""
        original = b'0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n'
        fitxer = self._desa('patro.dxf', original, tipus='PATRO')

        self.assertEqual(self._bytes_desats(fitxer), original)
        self.assertEqual(fitxer.checksum, hashlib.sha256(original).hexdigest())
        self.assertEqual(fitxer.mida_bytes, len(original))
        self.assertEqual(fitxer.nom_fitxer, 'patro.dxf')

    def test_imatge_que_ja_compleix_torna_byte_a_byte(self):
        """Una imatge que ja ha passat per una porta hi torna a passar (upload_file_view
        redueix i després crida el servei). La segona passada no ha de re-encodar res."""
        original = _imatge((MAX_ADJUNT_DIM, 800))
        fitxer = self._desa('ja_ok.jpg', original, tipus='ALTRES')

        self.assertEqual(self._bytes_desats(fitxer), original)
        self.assertEqual(fitxer.checksum, hashlib.sha256(original).hexdigest())

    # ── La invariant de cadena, intacta ──────────────────────────────────────
    def test_la_cadena_de_versions_no_queda_tocada(self):
        v1 = self._desa('foto.jpg', _imatge((3000, 2000)), tipus='ALTRES')
        v2 = self._desa('foto.jpg', _imatge((2600, 1800)), tipus='ALTRES',
                        versio_anterior=v1)

        v1.refresh_from_db()
        self.assertEqual((v1.versio, v1.is_current), (1, False))
        self.assertEqual((v2.versio, v2.is_current), (2, True))
        self.assertEqual(v2.versio_anterior_id, v1.pk)
        self.assertEqual(
            ModelFitxer.objects.filter(model=self.model, is_current=True).count(), 1)
