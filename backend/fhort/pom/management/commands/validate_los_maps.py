"""Validació dels GarmentPOMMap del circuit LOS (PAS 4B) — la Montse ha acceptat el document de
classificació (2026-07-19). Marca `pendent_revisio=False` EXACTAMENT als maps que casen amb els
parells (item, pom) de `pom_item_maps_los.csv` (la materialització del document).

Abast confirmat (Agus 19/07, opció 2): els parells del CSV LOS. Un map preexistent amb el MATEIX
parell (item, pom) queda cobert per la mateixa validació (el parell és el mateix, tant se val qui
el va crear). NO toca els maps LOS fora del CSV ni la resta de pendents del tenant.

Resolució de POM/item IDÈNTICA a `consolidate_pom_catalog._maps` (reusa `variants`, la config i el
mateix ordre àlies-LOS→codi) perquè el set sigui exactament el que el command va crear/tocar.
Idempotent (només toca els que encara són `pendent_revisio=True`). `--dry-run` per defecte.

    python manage.py validate_los_maps                # DRY-RUN (compta, rollback)
    python manage.py validate_los_maps --no-dry-run   # aplica + verifica
"""
import csv

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import POMMaster, CustomerPOMAlias, GarmentPOMMap
from fhort.tasks.models import Customer, GarmentTypeItem
from fhort.pom.seed_data import consolidate_pom_los as CFG
from fhort.pom.management.commands.consolidate_pom_catalog import variants, SEED_DIR


class Command(BaseCommand):
    help = 'Marca pendent_revisio=False als GarmentPOMMap del circuit LOS (parells del CSV).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        head = 'DRY-RUN' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== validate_los_maps · {head} ==='))

        with schema_context(opts['schema']), transaction.atomic():
            los = Customer.objects.get(codi=CFG.CUSTOMER_CODI)

            def prim_by_alias(code):
                for v in variants(code):
                    a = CustomerPOMAlias.objects.filter(
                        customer=los, client_code=v, pom__isnull=False).first()
                    if a:
                        return a.pom
                return None

            def resolve_pom(code, ev):
                # NOU/gap → codi EXACTE (el command el va crear); si no → àlies LOS, després codi.
                if ('[POM NOU' in ev) or ('[gap' in ev):
                    return POMMaster.objects.filter(codi_client=code).first()
                p = prim_by_alias(code)
                if p:
                    return p
                for v in variants(code):
                    m = POMMaster.objects.filter(codi_client=v).first()
                    if m:
                        return m
                return None

            with open(SEED_DIR / CFG.MAPS_CSV, encoding='utf-8') as fh:
                rows = list(csv.DictReader(fh))

            pairs = set()          # (garment_type_item_id, pom_id)
            no_pom, no_item = [], []
            for row in rows:
                code = row['codi_pom'].strip()
                pom = resolve_pom(code, row.get('evidencia_fitxa', ''))
                if not pom:
                    no_pom.append(code)
                    continue
                for itc in [s.strip() for s in row['items'].split(',') if s.strip()]:
                    it = GarmentTypeItem.objects.filter(code=itc).first()
                    if not it:
                        no_item.append(f'{code}->{itc}')
                        continue
                    pairs.add((it.id, pom.id))

            existing = {(m.garment_type_item_id, m.pom_id): m
                        for m in GarmentPOMMap.objects.filter(
                            garment_type_item_id__in=[p[0] for p in pairs])}
            matched = [existing[p] for p in pairs if p in existing]
            missing = [p for p in pairs if p not in existing]
            pending = [m for m in matched if m.pendent_revisio]

            self.stdout.write(f'  CSV: {len(rows)} files · parells (item,pom): {len(pairs)}')
            self.stdout.write(f'  maps trobats: {len(matched)} · sense map: {len(missing)} · '
                              f'POM no resolt: {len(no_pom)} {no_pom} · item no resolt: {len(no_item)} {no_item}')
            self.stdout.write(f'  pendent_revisio=True a marcar False: {len(pending)} '
                              f'(ja False: {len(matched) - len(pending)})')

            if dry:
                transaction.set_rollback(True)
                self.stdout.write('  (dry-run: rollback, res tocat)')
            else:
                n = GarmentPOMMap.objects.filter(
                    id__in=[m.id for m in pending]).update(pendent_revisio=False)
                self.stdout.write(self.style.SUCCESS(f'  ACTUALITZATS: {n}'))
                still = GarmentPOMMap.objects.filter(
                    id__in=[m.id for m in matched], pendent_revisio=True).count()
                self.stdout.write(f'  VERIFICACIÓ · pendents restants DINS del set del CSV: {still}')

        self.stdout.write(self.style.SUCCESS('=== FET ==='))
