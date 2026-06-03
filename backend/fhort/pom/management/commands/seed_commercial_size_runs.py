"""
Seed commercial (non-ISO) size runs into the canonical POM catalogue.

Creates two SizeSystem + their SizeDefinition rows, idempotently (get_or_create):

  KIDS_AGE_COM    — Kids Age, commercial (EU), 2–15/16 anys
  BABY_MONTHS_COM — Baby Months, commercial, 0M–9/12M

Commercial = norma_ref='' (no ISO badge); valor_numeric=None on every size
(these runs are designation-only, the numeric body refs live on ISO systems).

Scoping (django-tenants): 'pom' lives in SHARED_APPS *and* TENANT_APPS, so the
SizeSystem/SizeDefinition tables exist in BOTH the 'public' (canonical) schema
and each tenant schema. We seed both via schema_context so the commercial runs
are available to the canonical catalogue and to the working tenant 'fhort'.

Usage:
  python manage.py seed_commercial_size_runs                  # dry-run, all schemas
  python manage.py seed_commercial_size_runs --no-dry-run     # write, all schemas
  python manage.py seed_commercial_size_runs --schema public  # one schema only
  python manage.py seed_commercial_size_runs --schema fhort --no-dry-run

Safe by design: only creates the two NEW codes above. Never updates or touches
any pre-existing SizeSystem / SizeDefinition / SizingProfile.
"""

import argparse

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

ALL_SCHEMAS = ['public', 'fhort']

# ─────────────────────────────────────────────────────────────────────────────
# Data — the two commercial runs.
# SizeDefinition tuples: (ordre, etiqueta, age_months_min, age_months_max)
# valor_numeric is always None (commercial = designation-only).
# ─────────────────────────────────────────────────────────────────────────────
RUNS = [
    {
        'system': {
            'codi': 'KIDS_AGE_COM',
            'nom': 'Kids Age — Commercial (EU)',
            'descripcio': 'Run comercial per edats, bottomwear i topwear infantil 2–15/16 anys',
            'base_unit': 'AGE_YEARS',
            'norma_ref': '',      # comercial, sense badge ISO
            'actiu': True,
        },
        'definitions': [
            (1,  '2',      24,  35),
            (2,  '3',      36,  47),
            (3,  '4',      48,  59),
            (4,  '5',      60,  71),
            (5,  '6',      72,  83),
            (6,  '7',      84,  95),
            (7,  '8',      96,  107),
            (8,  '9/10',   108, 131),
            (9,  '11/12',  132, 155),
            (10, '13/14',  156, 179),
            (11, '15/16',  180, 203),
        ],
    },
    {
        'system': {
            'codi': 'BABY_MONTHS_COM',
            'nom': 'Baby Months — Commercial',
            'descripcio': 'Run comercial nadó per rangs de mesos 0M–9/12M',
            'base_unit': 'MONTHS',
            'norma_ref': '',      # comercial, sense badge ISO
            'actiu': True,
        },
        'definitions': [
            (1, '0M-1M',  0, 1),
            (2, '1M-3M',  1, 3),
            (3, '3M-6M',  3, 6),
            (4, '6M-9M',  6, 9),
            (5, '9M-12M', 9, 12),
        ],
    },
]


class Command(BaseCommand):
    help = 'Crea els runs de talles comercials KIDS_AGE_COM i BABY_MONTHS_COM (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action=argparse.BooleanOptionalAction,
            default=True,
            help='Imprimeix què faria sense escriure res (default). Usa --no-dry-run per escriure.',
        )
        parser.add_argument(
            '--schema',
            choices=['public', 'fhort', 'all'],
            default='all',
            help="Schema on actuar: public | fhort | all (default: all).",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        schema_opt = options['schema']
        schemas = ALL_SCHEMAS if schema_opt == 'all' else [schema_opt]

        mode = 'DRY-RUN (cap escriptura)' if dry_run else 'ESCRIPTURA REAL'
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'seed_commercial_size_runs — mode: {mode} — schemas: {schemas}'
        ))

        for schema in schemas:
            self._process_schema(schema, dry_run)

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(
                'DRY-RUN: no s\'ha escrit res. Torna a executar amb --no-dry-run per aplicar.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('Fet.'))

    # ──────────────────────────────────────────────────────────────────────
    def _process_schema(self, schema, dry_run):
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO(f'━━━ schema: {schema} ━━━'))

        with schema_context(schema):
            from fhort.pom.models import SizeSystem, SizeDefinition

            sys_created = defs_created = sys_exist = defs_exist = 0

            for run in RUNS:
                sysd = run['system']
                codi = sysd['codi']

                existing_ss = SizeSystem.objects.filter(codi=codi).first()

                if existing_ss:
                    sys_exist += 1
                    self.stdout.write(
                        f'  [=] SizeSystem {codi!r} ja existeix (id={existing_ss.id}) — no es toca'
                    )
                else:
                    sys_created += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  [+] SizeSystem {codi!r}  nom={sysd["nom"]!r}  '
                        f'base_unit={sysd["base_unit"]!r}  norma_ref={sysd["norma_ref"]!r}  actiu={sysd["actiu"]}'
                    ))

                # Decide existing definitions only if the system already exists.
                existing_labels = set()
                if existing_ss:
                    existing_labels = set(
                        existing_ss.talles.values_list('etiqueta', flat=True)
                    )

                for ordre, etiqueta, a_min, a_max in run['definitions']:
                    if etiqueta in existing_labels:
                        defs_exist += 1
                        self.stdout.write(
                            f'        [=] talla {etiqueta!r} ja existeix — no es toca'
                        )
                    else:
                        defs_created += 1
                        self.stdout.write(
                            f'        [+] talla ordre={ordre:>2} etiqueta={etiqueta!r:8} '
                            f'age_months=[{a_min}, {a_max}] valor_numeric=None'
                        )

                if not dry_run:
                    self._write_run(SizeSystem, SizeDefinition, run)

            self.stdout.write(
                f'  → resum {schema}: SizeSystem +{sys_created} (={sys_exist}) · '
                f'SizeDefinition +{defs_created} (={defs_exist})'
            )

    # ──────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def _write_run(self, SizeSystem, SizeDefinition, run):
        """Idempotent write of one run (only reached when not dry-run)."""
        sysd = run['system']
        ss, _ = SizeSystem.objects.get_or_create(
            codi=sysd['codi'],
            defaults={
                'nom': sysd['nom'],
                'descripcio': sysd['descripcio'],
                'base_unit': sysd['base_unit'],
                'norma_ref': sysd['norma_ref'],
                'actiu': sysd['actiu'],
            },
        )
        for ordre, etiqueta, a_min, a_max in run['definitions']:
            SizeDefinition.objects.get_or_create(
                size_system=ss,
                etiqueta=etiqueta,
                defaults={
                    'ordre': ordre,
                    'valor_numeric': None,
                    'age_months_min': a_min,
                    'age_months_max': a_max,
                },
            )
