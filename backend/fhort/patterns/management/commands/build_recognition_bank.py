"""Build the corpus neighbour-bank cache (`.npz`) that the recognizer loads lazily.

Reading 1,4 M descriptors out of `ftt_corpus` takes ~17 s and 229 MB of transfer. A web
worker must never pay that on a request, so it is paid here, once, offline.

    python manage.py build_recognition_bank              # default fraction
    python manage.py build_recognition_bank --fraction 1 # the whole corpus
    python manage.py build_recognition_bank --compare    # measure what the fraction costs

`--fraction N` keeps one panel in N, deterministically (`id % N == 0`) and
**proportionally** — the natural role distribution is the prior, and flattening it would
throw away the +8,1 points the gym measured it is worth.

READ-ONLY against `ftt_corpus`: the `corpus_ro` role has SELECT and nothing else, and the
connection is opened `readonly=True` on top of it.
"""
from django.core.management.base import BaseCommand

from fhort.patterns.recognition import bank as B


class Command(BaseCommand):
    help = 'Build the corpus neighbour-bank cache for the piece recognizer.'

    def add_arguments(self, parser):
        parser.add_argument('--fraction', type=int, default=None,
                            help='Keep one panel in N (default: settings value).')
        parser.add_argument('--conninfo', default=None,
                            help='libpq conninfo file for ftt_corpus (read-only).')

    def handle(self, *args, **opts):
        from django.conf import settings
        fraction = opts['fraction'] or getattr(
            settings, 'FTT_RECOGNITION_CORPUS_FRACTION', 5)
        self.stdout.write('  building corpus bank, fraction 1 in {}...'.format(fraction))
        stats = B.build_corpus_cache(fraction, opts['conninfo'])
        B.invalidate_corpus_bank()
        self.stdout.write(self.style.SUCCESS(
            '  {rows} panels · {roles} roles · {megabytes} MB · {seconds}s\n  {path}'
            .format(**stats)))
