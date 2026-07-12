"""Deriva els segments dels PatternFile que es van importar abans que existissin.

Els patrons pujats a S3/S4/S5 no tenen segments: la derivació de gir a gir arriba a S6 i
l'adapter els crea des d'ara en importar. Aquest command posa al dia els que ja hi eren,
sense haver-los de tornar a pujar.

**Idempotent**: només crea segments a les peces que no en tenen. Executar-lo dos cops no
duplica res. No toca cap altra dada.
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from fhort.patterns.adapters import DjangoGeometryStore
from fhort.patterns.engine.segments import segmentar_peca
from fhort.patterns.models import PatternFile, PatternPiece, PatternSegment


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
                    if row.segments.exists():
                        total_saltades += 1
                        self.stdout.write(
                            f'  · {row.nom_block}: ja té {row.segments.count()} segments, es salta.'
                        )
                        continue

                    piece = doc.piece(row.nom_block)
                    if piece is None:
                        self.stdout.write(self.style.WARNING(
                            f'  · {row.nom_block}: no s\'ha pogut carregar la geometria.'
                        ))
                        continue

                    segments = segmentar_peca(piece)
                    if not dry:
                        PatternSegment.objects.bulk_create([
                            PatternSegment(
                                piece=row, vora=s.vora, t_inici=s.t_inici, t_fi=s.t_fi,
                                tipus_vora=s.tipus_vora.value,
                            )
                            for s in segments
                        ])
                    total_creats += len(segments)
                    llarg = sum(s.longitud_mm for s in segments) / 10.0
                    self.stdout.write(
                        f'  · {row.nom_block}: {len(segments)} segments '
                        f'({llarg:.1f} cm de contorn).'
                    )

            prefix = '[dry-run] ' if dry else ''
            self.stdout.write(self.style.SUCCESS(
                f'{prefix}{total_creats} segments creats · '
                f'{total_saltades} peces saltades (ja en tenien).'
            ))
