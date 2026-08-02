"""La neteja de les imatges que ja hi eren: `reprocessa_imatges_adjuntes`.

El fix de `save_model_file` només mira les imatges NOVES. Aquesta comanda és l'altra
meitat, i el que s'hi ha d'afirmar és sobretot el que NO fa: no toca el que ja compleix,
no toca els no-ràsters, no encadena versions i no escriu res sense `--apply`. Un dry-run
que menteixi és pitjor que no tenir-lo — és el que es mira abans de córrer-ho a PROD.

Les imatges s'insereixen a la BD SENSE passar per `save_model_file`, perquè el que la
comanda ha de netejar és precisament el que va entrar abans que el coll existís.
"""
import datetime
import hashlib
import io

from django.core.files.base import ContentFile
from django.core.management import call_command
from django_tenants.test.cases import TenantTestCase
from PIL import Image

from fhort.models_app.models import Model, ModelFitxer
from fhort.models_app.services_fitxers import MAX_ADJUNT_DIM


def _imatge(mida, format='JPEG'):
    w, h = mida
    base = Image.effect_noise((max(1, w // 3), max(1, h // 3)), 64).convert('RGB')
    buf = io.BytesIO()
    base.resize(mida, Image.NEAREST).save(buf, format=format)
    return buf.getvalue()


class ReprocessaImatgesTest(TenantTestCase):

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
        self.gran_bytes = _imatge((3000, 2000))
        self.petita_bytes = _imatge((800, 600))
        self.dxf_bytes = b'0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n'
        self.gran = self._crua('IMG_4821.jpg', self.gran_bytes, 'ALTRES')
        self.petita = self._crua('ja_petita.jpg', self.petita_bytes, 'ALTRES')
        self.dxf = self._crua('patro.dxf', self.dxf_bytes, 'PATRO')

    def _crua(self, nom, contingut, tipus):
        """Una fila com les que hi ha a PROD: bytes crus, entrats abans que el coll existís."""
        f = ModelFitxer(model=self.model, nom_fitxer=nom, tipus=tipus, versio=1,
                        is_current=True, mida_bytes=len(contingut),
                        checksum=hashlib.sha256(contingut).hexdigest(), origen='upload')
        f.fitxer.save(nom, ContentFile(contingut), save=False)
        f.save()
        return f

    def _bytes(self, fitxer):
        fitxer.refresh_from_db()
        fitxer.fitxer.open('rb')
        try:
            return fitxer.fitxer.read()
        finally:
            fitxer.fitxer.close()

    def _corre(self, *args):
        sortida = io.StringIO()
        call_command('reprocessa_imatges_adjuntes', '--schema', self.tenant.schema_name,
                     *args, stdout=sortida, stderr=sortida)
        return sortida.getvalue()

    # ── DRY-RUN ──────────────────────────────────────────────────────────────
    def test_dry_run_compta_be_i_no_toca_res(self):
        text = self._corre()

        self.assertIn('1 a reduir', text)
        self.assertIn('1 ja conformes', text)   # la petita. El dxf no és ni candidat: veure sota
        self.assertIn('0 amb error', text)
        self.assertIn('estalvi', text)
        # I sobretot: cap dels tres fitxers ha canviat ni un byte.
        self.assertEqual(self._bytes(self.gran), self.gran_bytes)
        self.assertEqual(self.gran.mida_bytes, len(self.gran_bytes))
        self.assertEqual(self._bytes(self.petita), self.petita_bytes)
        self.assertEqual(self._bytes(self.dxf), self.dxf_bytes)

    def test_el_dxf_no_es_ni_candidat(self):
        """Els no-ràsters no compten ni com a «saltats»: no entren a la llista."""
        text = self._corre()
        self.assertIn('2 imatge/s raster de 3 fitxers', text)
        self.assertNotIn('patro.dxf', text)

    # ── APPLY ────────────────────────────────────────────────────────────────
    def test_apply_redueix_la_gran_i_deixa_la_resta(self):
        self._corre('--apply')

        desats = self._bytes(self.gran)
        self.assertEqual(Image.open(io.BytesIO(desats)).size, (MAX_ADJUNT_DIM, 1000))
        self.assertLess(len(desats), len(self.gran_bytes))
        # Metadades recalculades sobre el que hi ha a disc, no heretades de l'original.
        self.assertEqual(self.gran.mida_bytes, len(desats))
        self.assertEqual(self.gran.checksum, hashlib.sha256(desats).hexdigest())

        self.assertEqual(self._bytes(self.petita), self.petita_bytes)
        self.assertEqual(self._bytes(self.dxf), self.dxf_bytes)
        self.assertEqual(self.dxf.checksum, hashlib.sha256(self.dxf_bytes).hexdigest())

    def test_no_encadena_cap_versio_nova(self):
        """Reduir no és un acte editorial: la cadena de versions no se n'assabenta."""
        self._corre('--apply')

        self.assertEqual(ModelFitxer.objects.count(), 3)
        self.gran.refresh_from_db()
        self.assertEqual((self.gran.versio, self.gran.is_current), (1, True))
        self.assertIsNone(self.gran.versio_anterior_id)

    def test_es_idempotent(self):
        self._corre('--apply')
        despres_del_primer = self._bytes(self.gran)

        text = self._corre('--apply')

        self.assertIn('0 reduïdes', text)
        self.assertIn('2 ja conformes', text)
        # Byte a byte: una segona passada no la re-encoda (cada re-encodat de JPEG hi deixa gra).
        self.assertEqual(self._bytes(self.gran), despres_del_primer)

    def test_una_imatge_corrupta_no_atura_la_neteja(self):
        self._crua('trencada.jpg', b'aixo no es cap jpeg', 'ALTRES')

        text = self._corre('--apply')

        # La corrupta l'absorbeix l'embut (desa l'original, llei de `pom_vision_service`):
        # ni peta ni compta com a reduïda. La gran s'ha reduït igualment.
        self.assertIn('1 reduïdes', text)
        self.assertEqual(Image.open(io.BytesIO(self._bytes(self.gran))).size,
                         (MAX_ADJUNT_DIM, 1000))
