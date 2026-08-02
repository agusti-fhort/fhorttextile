"""Passa per l'embut les imatges JA desades com a adjunts de model.

    python manage.py reprocessa_imatges_adjuntes                  # DRY-RUN, tots els tenants
    python manage.py reprocessa_imatges_adjuntes --schema fhort   # DRY-RUN, un sol tenant
    python manage.py reprocessa_imatges_adjuntes --apply          # ara sí, escriu

El fix de `save_model_file` para l'hemorràgia de les imatges NOVES: des d'ell, tot el que
entra a `ModelFitxer` passa per `redueix_imatge`. Però les que ja hi són van entrar crues
—a PROD hi ha IMG_XXXX.jpg de 5-6 MB tal com van sortir del mòbil— i el fix no les mira.
Aquesta comanda és l'altra meitat: recupera el pes que ja s'ha pagat.

NO CREA VERSIÓ NOVA. Reduir una imatge no és un acte editorial: ningú no ha decidit res
sobre aquell fitxer, i encadenar-hi un «v2» diria que sí. La cadena `versio_anterior`
explica la HISTÒRIA del document; això és manteniment del suport. Els bytes es reemplacen
al MATEIX registre i `mida_bytes`/`checksum`/`mimetype` es recalculen perquè segueixin
descrivint el que hi ha realment a disc. `is_current`/`versio` no es toquen: d'aquells
en segueix sent únic escriptor `save_model_file`.

IDEMPOTENT: la mida es llegeix de la capçalera de la imatge abans de res, i el que ja
compleix se salta sense descodificar-lo. Es pot córrer tantes vegades com calgui sense
degradar-la a cada passada (un JPEG re-encodat perd gra encara que no canviï de mida).

Un fitxer que peta —corrupte, format que Pillow no llegeix— es registra a ERROR i la
neteja CONTINUA amb els altres: la mateixa llei que la poda del desat. Una imatge dolenta
no pot deixar les altres 148 sense processar.
"""
import io
import logging
import os

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import get_tenant_model, schema_context

from fhort.models_app.models import ModelFitxer
from fhort.models_app.services_fitxers import (HEIC_EXTENSIONS, MAX_ADJUNT_DIM,
                                               RASTER_EXTENSIONS, redueix_imatge)

logger = logging.getLogger(__name__)


def _es_raster(nom):
    return os.path.splitext(nom or '')[1].lower() in RASTER_EXTENSIONS


def _mb(n):
    return f'{n / (1024 * 1024):.1f} MB'


class Command(BaseCommand):
    help = ('Redueix a MAX_ADJUNT_DIM les imatges ja desades a ModelFitxer. '
            'DRY-RUN per defecte: sense --apply no escriu res.')

    def add_arguments(self, parser):
        parser.add_argument('--schema', help='Només aquest schema de tenant.')
        parser.add_argument('--apply', action='store_true',
                            help='Escriu de debò. Sense això, només informa.')

    def handle(self, *args, **opts):
        aplica = opts['apply']
        known = list(get_tenant_model().objects
                     .exclude(schema_name='public')
                     .values_list('schema_name', flat=True))
        if opts['schema']:
            if opts['schema'] not in known:
                raise CommandError(
                    f"Schema '{opts['schema']}' no existeix. "
                    f"Tenants: {', '.join(known) or '(cap)'}")
            schemas = [opts['schema']]
        else:
            schemas = known

        if not aplica:
            self.stdout.write(self.style.WARNING(
                'DRY-RUN: no s\'escriu res. Torna-hi amb --apply per aplicar-ho.'))

        total = {'vistes': 0, 'reduides': 0, 'saltades': 0, 'errors': 0,
                 'abans': 0, 'despres': 0}
        for schema in schemas:
            with schema_context(schema):
                r = self._processa_tenant(schema, aplica)
            for k in total:
                total[k] += r[k]

        if len(schemas) > 1:
            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING('TOTAL'))
            self._resum(total, aplica)

    # ── un tenant ────────────────────────────────────────────────────────────
    def _processa_tenant(self, schema, aplica):
        res = {'vistes': 0, 'reduides': 0, 'saltades': 0, 'errors': 0,
               'abans': 0, 'despres': 0}
        noms_error = []

        candidats = [f for f in ModelFitxer.objects.all().order_by('id')
                     if _es_raster(f.nom_fitxer) and f.fitxer]
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'{schema}: {len(candidats)} imatge/s raster de '
            f'{ModelFitxer.objects.count()} fitxers'))

        for fitxer in candidats:
            res['vistes'] += 1
            try:
                canvi = self._reprocessa(fitxer, aplica)
            except Exception as exc:                       # noqa: BLE001 — cap fitxer atura la neteja
                res['errors'] += 1
                noms_error.append(fitxer.nom_fitxer)
                logger.error('Reprocessament fallit de ModelFitxer#%s (%s): %s',
                             fitxer.pk, fitxer.nom_fitxer, exc, exc_info=True)
                self.stdout.write(self.style.ERROR(
                    f'  ERROR  #{fitxer.pk} {fitxer.nom_fitxer}: {exc}'))
                continue

            if canvi is None:
                res['saltades'] += 1
                continue
            abans, despres, nom_nou = canvi
            res['reduides'] += 1
            res['abans'] += abans
            res['despres'] += despres
            marca = '' if aplica else '  (previst)'
            renom = f' → {nom_nou}' if nom_nou != fitxer.nom_fitxer else ''
            self.stdout.write(
                f'  #{fitxer.pk} {fitxer.nom_fitxer}{renom}: '
                f'{_mb(abans)} → {_mb(despres)}{marca}')

        self._resum(res, aplica)
        if noms_error:
            self.stdout.write(self.style.ERROR(
                f'  amb error: {", ".join(noms_error)}'))
        return res

    # ── un fitxer ────────────────────────────────────────────────────────────
    def _reprocessa(self, fitxer, aplica):
        """Retorna `(bytes_abans, bytes_despres, nom_nou)`, o None si no calia tocar-lo."""
        from PIL import Image

        fitxer.fitxer.open('rb')
        try:
            crus = fitxer.fitxer.read()
        finally:
            fitxer.fitxer.close()

        # SALT BARAT I PRIMER: `Image.open` llegeix la capçalera, no descodifica els píxels.
        # Aquí és on es guanya la idempotència — i on una segona passada sobre 149 imatges
        # ja netes costa mil·lisegons en lloc de minuts.
        try:
            with Image.open(io.BytesIO(crus)) as im:
                ja_compleix = max(im.size) <= MAX_ADJUNT_DIM
        except Exception:
            ja_compleix = False        # il·legible: que ho digui l'embut, que sap distingir-ho
        if ja_compleix and not _es_heic_nom(fitxer.nom_fitxer):
            return None

        nou, nom_nou = redueix_imatge(
            ContentFile(crus, name=fitxer.nom_fitxer), fitxer.nom_fitxer,
            fitxer.mimetype or '', max_dim=MAX_ADJUNT_DIM)
        nou.seek(0)
        bytes_nous = nou.read()
        if bytes_nous == crus:
            # L'embut ha decidit no tocar-la (imatge que Pillow no sap llegir: es desa
            # l'original, llei de `pom_vision_service`). No és un error, és un no-canvi.
            return None

        if aplica:
            self._reemplaça(fitxer, bytes_nous, nom_nou)
        return len(crus), len(bytes_nous), nom_nou

    def _reemplaça(self, fitxer, bytes_nous, nom_nou):
        """Bytes nous al MATEIX registre, i els vells fora del disc.

        ORDRE: escriure els bytes nous → confirmar la fila → esborrar els vells. Si peta pel
        mig, el pitjor cas és un fitxer orfe al disc (que `audit_fitxers` ja sap reportar);
        mai una fila que apunti a uns bytes que ja no hi són. L'atomic embolcalla NOMÉS
        l'UPDATE: un rollback no desfaria una escriptura a disc, i fer-lo per lots deixaria
        la meitat de les imatges reduïdes amb la fila sense actualitzar.
        """
        import hashlib
        import mimetypes

        vell = fitxer.fitxer.name
        fitxer.fitxer.save(nom_nou, ContentFile(bytes_nous), save=False)
        with transaction.atomic():
            fitxer.nom_fitxer = nom_nou
            fitxer.mida_bytes = len(bytes_nous)
            fitxer.checksum = hashlib.sha256(bytes_nous).hexdigest()
            fitxer.mimetype = mimetypes.guess_type(nom_nou)[0] or fitxer.mimetype
            # `fitxer` HI HA DE SER: `FileField.save(save=False)` escriu els bytes en un camí
            # NOU i actualitza `.name` només en memòria. Sense aquest camp a `update_fields`,
            # la fila es quedaria apuntant al camí vell —que tot seguit s'esborra— i la imatge
            # quedaria il·localitzable. És el que passava, i el que el test va enxampar.
            fitxer.save(update_fields=['fitxer', 'nom_fitxer', 'mida_bytes', 'checksum',
                                       'mimetype'])

        if fitxer.fitxer.name != vell:
            _esborra(vell)

    def _resum(self, r, aplica):
        verb = 'reduïdes' if aplica else 'a reduir'
        self.stdout.write(
            f"  {r['vistes']} vistes · {r['reduides']} {verb} · "
            f"{r['saltades']} ja conformes · {r['errors']} amb error")
        if r['reduides']:
            estalvi = r['abans'] - r['despres']
            pct = (estalvi / r['abans'] * 100) if r['abans'] else 0
            self.stdout.write(self.style.SUCCESS(
                f"  {_mb(r['abans'])} → {_mb(r['despres'])} "
                f"(estalvi {_mb(estalvi)}, {pct:.0f}%)"))


def _es_heic_nom(nom):
    return os.path.splitext(nom or '')[1].lower() in HEIC_EXTENSIONS


def _esborra(name):
    """Els bytes VELLS, un cop la fila ja apunta als nous. `delete_fitxer_bytes` no serveix
    aquí: treballa sobre el fitxer VIU d'una fila, i el que s'ha d'esborrar és el camí que
    aquella fila acaba de deixar enrere. Mateix criteri que ell, però: mai propaga —una
    escombrada fallida no pot desfer una reducció que ja és a la BD."""
    from django.core.files.storage import default_storage

    try:
        if default_storage.exists(name):
            default_storage.delete(name)
    except Exception:
        logger.warning("Bytes vells no esborrats: '%s'", name, exc_info=True)
