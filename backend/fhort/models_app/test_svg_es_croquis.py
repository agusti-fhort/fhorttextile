"""S1.1 (ordre Agus 24/09): un `.svg` pujat sense `tipus` explícit ÉS un croquis.

Verifica només el predicat nou de `save_model_file`/`_es_svg` (`services_fitxers.py`); la
resta de la invariant de cadena (versió, is_current, embut de ràster) ja té la seva pròpia
suite (`test_save_model_file_embut.py`, `test_upload_imatge.py`) i no es repeteix aquí.
"""
import datetime

from django.core.files.base import ContentFile
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import Model
from fhort.models_app.services_fitxers import save_model_file


class SvgEsCroquisTest(TenantTestCase):

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

    def test_svg_sense_tipus_esdeve_sketch_svg(self):
        fitxer = save_model_file(self.model, ContentFile(b'<svg/>', name='croquis.svg'),
                                 nom='croquis.svg')
        self.assertEqual(fitxer.tipus, 'SKETCH_SVG')

    def test_png_sense_tipus_es_queda_altres(self):
        fitxer = save_model_file(self.model, ContentFile(b'\x89PNG\r\n', name='foto.png'),
                                 nom='foto.png')
        self.assertEqual(fitxer.tipus, 'ALTRES')

    def test_svg_amb_tipus_explicit_mana(self):
        fitxer = save_model_file(self.model, ContentFile(b'<svg/>', name='net.svg'),
                                 nom='net.svg', tipus='SKETCH_NET')
        self.assertEqual(fitxer.tipus, 'SKETCH_NET')

    def test_svg_sense_content_type_per_extensio(self):
        """`_guess_mimetype` cau a `mimetypes.guess_type` per l'extensió quan el fitxer no
        porta `content_type` (com `ContentFile`, que és exactament el cas del Finder amb un
        navegador que no l'ompli): el defecte ha de disparar igualment."""
        fitxer = save_model_file(self.model, ContentFile(b'<svg/>', name='sense_ct.svg'),
                                 nom='sense_ct.svg')
        self.assertEqual(fitxer.mimetype, 'image/svg+xml')
        self.assertEqual(fitxer.tipus, 'SKETCH_SVG')

    def test_versio_nova_hereta_tipus_i_no_el_trepitja(self):
        """Una nova versió d'una cadena que JA tenia `ALTRES` (p.ex. pujada abans d'aquesta
        peça) hereta `ALTRES` del predecessor — el defecte de `.svg` només actua quan no hi
        ha ni `tipus` explícit ni predecessor a heretar."""
        v1 = save_model_file(self.model, ContentFile(b'<svg/>', name='v1.svg'),
                             nom='v1.svg', tipus='ALTRES')
        v2 = save_model_file(self.model, ContentFile(b'<svg/>', name='v2.svg'),
                             nom='v2.svg', versio_anterior=v1)
        self.assertEqual(v2.tipus, 'ALTRES')
