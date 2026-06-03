"""
Sprint Excel-Map · PAS 3 — load the GarmentPOMMap ownership map (inline data, no Excel).

Idempotent and NON-destructive: update_or_create per (garment_type_item, pom). Never deletes.
Tenant-scoped (default 'fhort'). --dry-run by default; pass --commit to write.

Per cell rule (nivell K/M/O/D):
    nivell     = the literal
    is_key     = (nivell == 'K')
    obligatori = (nivell in ('K', 'M'))
    ordre      = 1-based position of the cell within the item's list

Resolution:
    POMMaster   via pom_global__codi = 'POM-XXX'  (skip + log if missing)
    GarmentTypeItem via code           (skip whole line + log if missing/ambiguous)
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context


# Canonical item maps. Each value is the raw "POM-XXX:nivell ..." line, verbatim.
RAW = {
    't_shirt': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:O POM-007:O POM-008:O POM-009:K POM-010:O POM-011:O POM-012:M POM-013:O POM-014:O POM-020:K POM-021:O POM-023:M POM-024:O POM-025:M POM-030:M POM-031:M POM-032:O POM-036:O POM-070:M POM-071:O POM-090:D POM-097:D POM-098:D POM-110:D POM-111:D',
    'hoodie': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:O POM-007:O POM-008:O POM-009:K POM-010:O POM-011:O POM-012:M POM-013:O POM-014:O POM-020:K POM-021:O POM-023:M POM-024:O POM-025:M POM-026:O POM-028:M POM-030:M POM-031:M POM-032:O POM-036:O POM-070:M POM-071:O POM-072:M POM-090:D POM-095:D POM-096:D POM-097:D POM-098:D POM-099:D POM-110:D POM-111:D',
    'skirt_straight': 'POM-050:K POM-051:O POM-052:M POM-060:K POM-062:M POM-070:M POM-071:O POM-090:D POM-093:D POM-094:D POM-097:D POM-098:D POM-099:D POM-110:D POM-111:D POM-112:D',
    'shorts': 'POM-041:M POM-043:K POM-044:K POM-045:O POM-050:K POM-051:O POM-052:M POM-055:K POM-056:M POM-057:O POM-070:M POM-071:O POM-090:D POM-097:D POM-098:D POM-099:D POM-110:D POM-111:D POM-112:D',
    'dress_simple': 'POM-001:K POM-003:K POM-004:K POM-005:M POM-006:O POM-007:O POM-008:O POM-009:K POM-010:O POM-011:O POM-012:M POM-013:O POM-014:O POM-020:K POM-021:O POM-023:M POM-024:O POM-025:M POM-030:M POM-031:M POM-032:O POM-036:O POM-061:K POM-062:O POM-070:M POM-071:O POM-090:D POM-093:D POM-094:D POM-097:D POM-098:D POM-110:D POM-111:D',
    'swimsuit': 'POM-050:K POM-051:O POM-052:O POM-055:M POM-056:M POM-057:O POM-085:K POM-086:M POM-087:O POM-088:K POM-089:M POM-090:D POM-099:M POM-110:D POM-111:D',
    'leggings': 'POM-026:O POM-028:M POM-041:M POM-042:O POM-043:K POM-044:K POM-045:O POM-050:K POM-051:K POM-052:M POM-055:K POM-056:M POM-057:O POM-070:M POM-071:O POM-072:M POM-090:D POM-097:D POM-098:D POM-099:M POM-110:D POM-111:D POM-112:D',
    'shirt_woven': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:M POM-007:O POM-008:O POM-009:K POM-010:M POM-011:O POM-012:M POM-013:O POM-014:M POM-020:K POM-021:O POM-022:O POM-023:M POM-024:O POM-025:M POM-027:M POM-030:M POM-031:M POM-032:O POM-033:M POM-034:M POM-035:O POM-036:O POM-070:M POM-071:O POM-090:D POM-091:D POM-092:M POM-094:D POM-097:D POM-098:D POM-110:D POM-111:D',
    'trousers': 'POM-040:K POM-041:M POM-042:M POM-043:K POM-044:K POM-045:K POM-050:K POM-051:O POM-052:M POM-055:K POM-056:M POM-057:O POM-070:M POM-071:O POM-090:D POM-094:D POM-097:D POM-098:D POM-099:D POM-110:D POM-111:D POM-112:D',
    'jeans': 'POM-040:K POM-041:M POM-042:M POM-043:K POM-044:K POM-045:K POM-050:K POM-051:O POM-052:M POM-055:K POM-056:M POM-057:O POM-070:M POM-071:O POM-090:M POM-097:D POM-098:D POM-110:D POM-111:D POM-112:D',
    'sweater': 'POM-002:K POM-005:M POM-006:O POM-009:K POM-010:O POM-011:O POM-012:O POM-013:O POM-014:O POM-020:K POM-021:O POM-023:M POM-024:O POM-025:M POM-026:O POM-028:M POM-030:M POM-031:M POM-032:O POM-036:M POM-070:M POM-071:O POM-072:M POM-080:K POM-081:O POM-082:K POM-090:D POM-097:D POM-098:D POM-110:D POM-111:D',
    'cardigan': 'POM-002:K POM-005:M POM-006:O POM-009:K POM-010:O POM-011:O POM-012:O POM-013:O POM-014:O POM-020:K POM-021:O POM-023:M POM-024:O POM-025:M POM-026:O POM-028:M POM-030:M POM-031:M POM-032:O POM-036:M POM-070:M POM-071:O POM-072:M POM-080:K POM-081:O POM-082:K POM-090:D POM-091:D POM-097:D POM-098:D POM-110:D POM-111:D',
    'dress_fancy': 'POM-001:K POM-003:K POM-004:K POM-005:M POM-006:O POM-007:O POM-008:O POM-009:K POM-010:O POM-011:O POM-012:M POM-013:O POM-014:O POM-020:K POM-021:O POM-023:M POM-024:O POM-025:M POM-030:M POM-031:M POM-032:O POM-036:O POM-061:K POM-062:O POM-070:M POM-071:O POM-090:D POM-091:D POM-093:D POM-094:D POM-097:D POM-098:D POM-110:D POM-111:D POM-112:D',
    'jumpsuit': 'POM-001:K POM-003:K POM-004:K POM-005:M POM-006:O POM-007:O POM-008:O POM-009:K POM-010:O POM-011:O POM-012:M POM-013:O POM-014:O POM-020:K POM-021:O POM-023:M POM-024:O POM-025:M POM-028:O POM-030:M POM-031:M POM-032:O POM-036:O POM-040:K POM-041:M POM-042:O POM-043:K POM-044:K POM-045:O POM-050:K POM-051:O POM-052:M POM-055:K POM-056:M POM-057:O POM-061:K POM-070:M POM-071:O POM-072:O POM-090:D POM-097:D POM-098:D POM-099:D POM-110:D POM-111:D POM-112:D',
    'pyjama_set': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:O POM-007:O POM-008:O POM-009:K POM-010:O POM-011:O POM-012:M POM-013:O POM-014:O POM-020:K POM-021:O POM-023:M POM-024:O POM-025:M POM-026:O POM-028:M POM-030:M POM-031:M POM-032:O POM-036:O POM-040:O POM-041:O POM-043:O POM-044:O POM-045:O POM-050:K POM-051:O POM-052:M POM-055:O POM-056:O POM-070:M POM-071:O POM-072:M POM-090:D POM-091:D POM-092:D POM-097:D POM-098:D POM-099:M POM-110:D POM-111:D POM-112:D',
    'gilet': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:M POM-007:O POM-008:O POM-009:K POM-010:O POM-011:O POM-012:M POM-013:O POM-014:O POM-020:K POM-021:O POM-023:M POM-024:O POM-025:M POM-030:M POM-031:M POM-032:O POM-036:O POM-070:M POM-071:O POM-090:D POM-091:D POM-092:D POM-093:D POM-097:D POM-098:D POM-100:K POM-110:D POM-111:D',
    'casual_jacket': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:M POM-007:O POM-008:M POM-009:K POM-010:M POM-011:O POM-012:M POM-013:M POM-014:M POM-020:K POM-021:O POM-022:M POM-023:M POM-024:O POM-025:M POM-027:O POM-030:M POM-031:M POM-032:O POM-033:D POM-034:D POM-035:D POM-036:O POM-070:M POM-071:O POM-090:D POM-091:D POM-092:D POM-093:M POM-094:D POM-097:D POM-098:D POM-100:K POM-101:M POM-102:O POM-103:D POM-110:D POM-111:D POM-112:D',
    'coat': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:M POM-007:O POM-008:M POM-009:K POM-010:M POM-011:O POM-012:M POM-013:M POM-014:M POM-020:K POM-021:O POM-022:M POM-023:M POM-024:O POM-025:M POM-027:O POM-030:M POM-031:M POM-032:O POM-033:D POM-034:D POM-035:D POM-036:O POM-070:M POM-071:O POM-090:D POM-091:D POM-092:D POM-093:M POM-095:D POM-096:D POM-097:D POM-098:D POM-100:K POM-101:O POM-103:D POM-110:D POM-111:D POM-112:D',
    'trench': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:M POM-007:O POM-008:M POM-009:K POM-010:M POM-011:O POM-012:M POM-013:M POM-014:M POM-020:K POM-021:O POM-022:M POM-023:M POM-024:O POM-025:M POM-027:O POM-030:M POM-031:M POM-032:O POM-033:D POM-034:D POM-035:D POM-036:O POM-070:M POM-071:O POM-090:M POM-091:D POM-092:D POM-093:M POM-095:D POM-096:D POM-097:D POM-098:D POM-100:K POM-101:O POM-103:D POM-110:D POM-111:D POM-112:D',
    'parka': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:M POM-007:O POM-008:M POM-009:K POM-010:M POM-011:O POM-012:M POM-013:M POM-014:M POM-020:K POM-021:O POM-022:M POM-023:M POM-024:O POM-025:M POM-026:O POM-027:O POM-028:M POM-030:M POM-031:M POM-032:O POM-033:D POM-034:D POM-035:D POM-036:O POM-070:M POM-071:O POM-072:M POM-090:M POM-095:M POM-096:M POM-097:D POM-098:D POM-100:K POM-103:D POM-110:D POM-111:D POM-112:D',
    'blazer': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:M POM-007:O POM-008:M POM-009:K POM-010:M POM-011:O POM-012:M POM-013:M POM-014:M POM-020:K POM-021:O POM-022:M POM-023:M POM-024:O POM-025:M POM-027:O POM-030:M POM-031:M POM-032:O POM-033:M POM-034:M POM-035:O POM-036:O POM-070:M POM-071:O POM-090:D POM-091:M POM-092:M POM-093:M POM-094:D POM-097:D POM-098:D POM-100:K POM-101:M POM-102:M POM-103:M POM-110:D POM-111:D POM-112:D',
    'leather_garment': 'POM-001:K POM-003:O POM-004:O POM-005:M POM-006:M POM-007:O POM-008:M POM-009:K POM-010:M POM-011:O POM-012:M POM-013:M POM-014:M POM-020:K POM-021:O POM-022:M POM-023:M POM-024:O POM-025:M POM-027:O POM-030:M POM-031:M POM-032:O POM-033:D POM-034:D POM-035:D POM-036:O POM-070:M POM-071:O POM-090:D POM-091:D POM-092:D POM-093:M POM-097:D POM-098:D POM-100:K POM-101:O POM-103:D POM-110:D POM-111:D POM-112:D',
}

# Aliases → canonical (copy the exact list of the referenced item).
ALIASES = {
    'polo': 't_shirt', 'top_sleeveless': 't_shirt', 'vest_top': 't_shirt',
    'bodysuit': 't_shirt', 'thermal_top': 't_shirt',
    'fleece_jacket': 'hoodie',
    'skirt_volume': 'skirt_straight',
    'shirt_dress': 'dress_simple',
    'bikini': 'swimsuit', 'swim_shorts': 'swimsuit',
    'culotte_cycling': 'leggings', 'tracksuit_pant': 'leggings',
    'blouse': 'shirt_woven', 'overshirt': 'shirt_woven', 'uniform_shirt': 'shirt_woven',
    'chino': 'trousers', 'workwear_pant': 'trousers',
    'twinset': 'sweater',
    'knit_gilet': 'cardigan',
    'dress_structured': 'dress_fancy',
    'dungarees': 'jumpsuit', 'playsuit': 'jumpsuit',
}


def _build_items():
    """item_code -> [(pom_code, nivell), ...] in order, resolving aliases."""
    out = {}
    for code, raw in RAW.items():
        out[code] = [tuple(tok.split(':')) for tok in raw.split()]
    for alias, base in ALIASES.items():
        out[alias] = list(out[base])
    return out


class Command(BaseCommand):
    help = 'PAS 3 · carrega el mapa GarmentPOMMap des de dades EMBEGUDES (idempotent, no destructiu)'

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort')
        parser.add_argument('--commit', action='store_true',
                            help='Escriu de veritat. Sense aquesta flag = dry-run (no toca res).')

    def handle(self, *args, **opts):
        schema = opts['schema']
        commit = opts['commit']
        items = _build_items()

        from fhort.pom.models import POMMaster, GarmentPOMMap
        from fhort.tasks.models import GarmentTypeItem

        mode = 'COMMIT' if commit else 'DRY-RUN'
        self.stdout.write(self.style.WARNING(
            f'\n=== load_map_inline · schema={schema} · {mode} ===\n'))

        with schema_context(schema):
            # Preload POMMaster by pom_global__codi.
            pm_by_code = {
                pm.pom_global.codi: pm
                for pm in POMMaster.objects.select_related('pom_global').filter(pom_global__isnull=False)
            }

            tot_create = tot_update = tot_cells = 0
            niv_global = {'K': 0, 'M': 0, 'O': 0, 'D': 0}
            skipped_poms = []   # (item_code, pom_code)
            skipped_items = []  # (item_code, reason)

            ctx = transaction.atomic() if commit else _noop()
            with ctx:
                for item_code in sorted(items):
                    cells = items[item_code]
                    matches = list(GarmentTypeItem.objects.filter(code=item_code))
                    if not matches:
                        skipped_items.append((item_code, 'item code no existeix'))
                        self.stdout.write(self.style.ERROR(f'  SALTAT item «{item_code}» — no existeix'))
                        continue
                    if len(matches) > 1:
                        skipped_items.append((item_code, f'code ambigu ({len(matches)} items)'))
                        self.stdout.write(self.style.ERROR(f'  SALTAT item «{item_code}» — ambigu ({len(matches)})'))
                        continue
                    item = matches[0]

                    niv = {'K': 0, 'M': 0, 'O': 0, 'D': 0}
                    n_create = n_update = 0
                    item_skipped_poms = []
                    for i, (pom_code, nivell) in enumerate(cells, 1):
                        tot_cells += 1
                        pom = pm_by_code.get(pom_code)
                        if pom is None:
                            skipped_poms.append((item_code, pom_code))
                            item_skipped_poms.append(pom_code)
                            continue
                        niv[nivell] += 1
                        niv_global[nivell] += 1
                        defaults = {
                            'nivell': nivell,
                            'is_key': nivell == 'K',
                            'obligatori': nivell in ('K', 'M'),
                            'ordre': i,
                        }
                        exists = GarmentPOMMap.objects.filter(
                            garment_type_item=item, pom=pom).exists()
                        if commit:
                            GarmentPOMMap.objects.update_or_create(
                                garment_type_item=item, pom=pom, defaults=defaults)
                        if exists:
                            n_update += 1; tot_update += 1
                        else:
                            n_create += 1; tot_create += 1

                    sk = f' · POMs saltats: {item_skipped_poms}' if item_skipped_poms else ''
                    self.stdout.write(
                        f'  {item_code:18} (id={item.id:<3}) '
                        f'K={niv["K"]:<2} M={niv["M"]:<2} O={niv["O"]:<2} D={niv["D"]:<2} '
                        f'| crear={n_create:<2} actualitzar={n_update:<2}{sk}')

            # Resum global
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('  ===== RESUM GLOBAL ====='))
            self.stdout.write(f'  items processats: {len(items) - len(skipped_items)} / {len(items)}')
            self.stdout.write(f'  cel·les totals: {tot_cells}')
            self.stdout.write(f'  nivell global: K={niv_global["K"]} M={niv_global["M"]} '
                              f'O={niv_global["O"]} D={niv_global["D"]}')
            self.stdout.write(f'  maps a CREAR: {tot_create} | a ACTUALITZAR: {tot_update} '
                              f'| total escrits: {tot_create + tot_update}')
            self.stdout.write(f'  POMs saltats (no existents): {len(skipped_poms)} '
                              f'{sorted(set(p for _, p in skipped_poms)) or ""}')
            self.stdout.write(f'  items saltats: {len(skipped_items)} {skipped_items or ""}')
            if not commit:
                self.stdout.write(self.style.WARNING('\n  DRY-RUN: res escrit. Passa --commit per aplicar.'))
            else:
                self.stdout.write(self.style.SUCCESS('\n  COMMIT fet.'))


class _noop:
    def __enter__(self): return self
    def __exit__(self, *a): return False
