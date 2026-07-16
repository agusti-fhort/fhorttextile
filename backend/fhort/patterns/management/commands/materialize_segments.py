"""Deriva els segments dels PatternFile que es van importar abans que existissin.

Els patrons pujats a S3/S4/S5 no tenen segments: la derivació de gir a gir arriba a S6 i
l'adapter els crea des d'ara en importar. Aquest command posa al dia els que ja hi eren,
sense haver-los de tornar a pujar.

Des de QA-TALLER-B fa el mateix amb els trams NATURALS (la mateixa vora llegida com poques
costures, `engine.natural_segments`), que A2 necessita per proposar. És el mateix problema
—una lectura derivada que neix a l'import i deixa enrere els patrons ja pujats— i per això
és el mateix command i no un de bessó: el dia que se n'afegís una tercera, la posada al dia
ja no s'hauria de tornar a inventar.

**Idempotent per ORIGEN**: només crea els trams d'una mena a les peces que no en tenen
d'aquella mena. Executar-lo dos cops no duplica res, i una peça que ja té `auto` però encara
no té `natural` rep només els que li falten. No toca cap altra dada.
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from fhort.patterns.adapters import DjangoGeometryStore
from fhort.patterns.engine.natural_segments import segmentar_peca_natural
from fhort.patterns.engine.segments import segmentar_peca
from fhort.patterns.models import PatternFile, PatternPiece, PatternSegment

#: Les lectures derivades que es materialitzen, i qui les calcula. Totes dues es desen:
#: l'`auto` és la granularitat fina (gest de precisió, aritmètica) i el `natural` és el que
#: una persona reconeix com una costura (A2 hi proposa). No es dedueixen l'una de l'altra.
DERIVADES = (
    (PatternSegment.ORIGEN_AUTO, segmentar_peca),
    (PatternSegment.ORIGEN_NATURAL, segmentar_peca_natural),
)


class Command(BaseCommand):
    help = 'Deriva els PatternSegment (de gir a gir) dels patrons ja importats.'

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort', help='Schema del tenant.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Diu què faria, sense escriure res.')

    def handle(self, *args, **opts):
        schema = opts['schema']
        dry = opts['dry_run']

        with schema_context(schema):
            store = DjangoGeometryStore()
            total_creats = 0
            total_saltades = 0

            for fp in PatternFile.objects.prefetch_related('pieces__points').all():
                doc = store.load_from(fp)
                self.stdout.write(f'PatternFile {fp.id} (v{fp.versio}, model {fp.model_id}):')

                for row in fp.pieces.all():
                    piece = None
                    for origen, derivar in DERIVADES:
                        # Es mira ORIGEN a ORIGEN: una peça que ja té trams DECLARATS però cap
                        # de derivat encara els necessita, i una que ja té `auto` pot encara no
                        # tenir `natural`. Mirar `segments.exists()` a seques la saltaria per
                        # culpa de la feina del patronista, que és justament el que no s'ha de
                        # perdre.
                        ja_hi_son = row.segments.filter(origen=origen)
                        if ja_hi_son.exists():
                            total_saltades += 1
                            self.stdout.write(
                                f'  · {row.nom_block}: ja té {ja_hi_son.count()} segments '
                                f'{origen}, es salta.'
                            )
                            continue

                        if piece is None:
                            piece = doc.piece(row.nom_block)
                        if piece is None:
                            self.stdout.write(self.style.WARNING(
                                f'  · {row.nom_block}: no s\'ha pogut carregar la geometria.'
                            ))
                            break

                        segments = derivar(piece)
                        if not dry:
                            PatternSegment.objects.bulk_create([
                                PatternSegment(
                                    piece=row, vora=s.vora, t_inici=s.t_inici, t_fi=s.t_fi,
                                    tipus_vora=s.tipus_vora.value,
                                    origen=origen,
                                )
                                for s in segments
                            ])
                        total_creats += len(segments)
                        llarg = sum(s.longitud_mm for s in segments) / 10.0
                        self.stdout.write(
                            f'  · {row.nom_block}: {len(segments)} segments {origen} '
                            f'({llarg:.1f} cm de contorn).'
                        )

            prefix = '[dry-run] ' if dry else ''
            self.stdout.write(self.style.SUCCESS(
                f'{prefix}{total_creats} segments creats · '
                f'{total_saltades} peces saltades (ja en tenien).'
            ))
