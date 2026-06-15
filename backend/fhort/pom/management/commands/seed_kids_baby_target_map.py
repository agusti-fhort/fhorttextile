"""seed_kids_baby_target_map — Capa 0b-1: repara el mapa target→SizeSystem infantil/baby.

Lliga els runs comercials NETS als seus targets i desactiva els sistemes TRENCATS:
  - KIDS_AGE_COM (SS net, run '2..15/16')  → {GIRL, BOY}        (unisex: el gènere viu al grading, no al run)
  - BABY_MONTHS_COM (SS net, run de mesos) → {BABY_GIRL, BABY_BOY, BABY_UNISEX}
  - BABY_MONTHS, TODDLER_EU, KIDS_EU (trencats) → actiu=False   (només actiu; no es toquen els seus targets antics)

Idempotent: re-executar no duplica lligams (.add() és idempotent + es comprova abans) ni
re-desactiva (no-op si ja inactiu). Resolució per CODI (no id). Resilient: si un Target o
SizeSystem no existeix en un esquema, AVÍS visible + skip (mai silenciós).

Esquema: pom és TENANT_APP; SizeSystem/Target són tenant-scoped → s'actua via schema_context
per esquema (com seed_commercial_size_runs). Default --dry-run (cal --no-dry-run per escriure).

Run:
  python manage.py seed_kids_baby_target_map --schema=fhort               # dry-run (default)
  python manage.py seed_kids_baby_target_map --schema=fhort --no-dry-run  # aplica a fhort
"""
import argparse

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

ALL_SCHEMAS = ['public', 'fhort']

# (codi SizeSystem net, [codis Target a lligar])
TARGET_LINKS = [
    ('KIDS_AGE_COM',    ['GIRL', 'BOY']),
    ('BABY_MONTHS_COM', ['BABY_GIRL', 'BABY_BOY', 'BABY_UNISEX']),
]

# codis SizeSystem trencats a desactivar (actiu=False; targets antics intactes)
DEACTIVATE = ['BABY_MONTHS', 'TODDLER_EU', 'KIDS_EU']


class Command(BaseCommand):
    help = ('Capa 0b-1: lliga SS41→{GIRL,BOY} i SS42→{BABY_GIRL,BABY_BOY,BABY_UNISEX} '
            'i desactiva els sistemes trencats SS34/SS36/SS37. Idempotent.')

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
            help='Schema on actuar: public | fhort | all (default: all).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        schema_opt = options['schema']
        schemas = ALL_SCHEMAS if schema_opt == 'all' else [schema_opt]

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'seed_kids_baby_target_map — mode: {"DRY-RUN" if dry_run else "WRITE"} '
            f'— schemas: {schemas}'))

        for schema in schemas:
            self._process_schema(schema, dry_run)

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(
                'DRY-RUN: cap canvi escrit. Usa --no-dry-run per aplicar.'))
        else:
            self.stdout.write(self.style.SUCCESS('Fet.'))

    def _process_schema(self, schema, dry_run):
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO(f'━━━ schema: {schema} ━━━'))
        with schema_context(schema):
            if dry_run:
                self._run(schema, write=False)
            else:
                with transaction.atomic():
                    self._run(schema, write=True)

    def _run(self, schema, write):
        from fhort.pom.models import SizeSystem, Target

        links_added = 0
        deactivated = 0

        # ---- 1. Lligams target→SizeSystem (M2M) ----
        for ss_codi, target_codis in TARGET_LINKS:
            ss = SizeSystem.objects.filter(codi=ss_codi).first()
            if ss is None:
                self.stdout.write(self.style.WARNING(
                    f'  SKIP: SizeSystem {ss_codi!r} no existeix a {schema} — lligams omesos.'))
                continue
            existents = set(ss.targets.values_list('codi', flat=True))
            for tc in target_codis:
                t = Target.objects.filter(codi=tc).first()
                if t is None:
                    self.stdout.write(self.style.WARNING(
                        f'  SKIP: Target {tc!r} no existeix a {schema} — lligam {ss_codi}→{tc} omès.'))
                    continue
                if tc in existents:
                    self.stdout.write(f'  = {ss_codi} → {tc} (ja existent)')
                    continue
                if write:
                    ss.targets.add(t)
                links_added += 1
                self.stdout.write(self.style.SUCCESS(f'  + {ss_codi} → {tc}'))

        # ---- 2. Desactivar sistemes trencats (només actiu) ----
        for ss_codi in DEACTIVATE:
            ss = SizeSystem.objects.filter(codi=ss_codi).first()
            if ss is None:
                self.stdout.write(self.style.WARNING(
                    f'  SKIP: SizeSystem {ss_codi!r} no existeix a {schema} — desactivació omesa.'))
                continue
            if not ss.actiu:
                self.stdout.write(f'  = {ss_codi} ja inactiu')
                continue
            if write:
                ss.actiu = False
                ss.save(update_fields=['actiu'])
            deactivated += 1
            self.stdout.write(self.style.SUCCESS(f'  ✗ {ss_codi} → actiu=False'))

        self.stdout.write(
            f'  → resum {schema}: lligams +{links_added}, desactivats {deactivated}')
