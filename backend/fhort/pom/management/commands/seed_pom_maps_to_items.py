"""Seed GarmentPOMMap from old family-level anchors onto the new GarmentTypeItem layer.

Migration família → item (PAS 2). Tenant-scoped (default schema: fhort). Read-only by default;
pass --commit to write. All ORM (the garment_type_item FK is db_constraint=False — never raw SQL).

(a) ANCHORS: copy each old GarmentType's maps verbatim (pom, is_key, ordre, obligatori) onto the
    destination item.
(b) SIBLINGS: clone the anchor's set onto the remaining active sibling items (provisional — to be
    reviewed so Montse can adjust the delta).
(c) NO-ANCHOR: families left empty on purpose (authored later in POMBrowser assign).

Idempotent: an item that already has maps is SKIPPED (never duplicated). Inactive items ignored.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

# (a) old family codi_client → destination item code
ANCHORS = [
    ('T_SHIRT',       't_shirt'),
    ('BLOUSE',        'blouse'),
    ('TROUSERS',      'trousers'),
    ('LEGGINGS',      'leggings'),
    ('DRESS',         'dress_simple'),
    ('JACKET',        'blazer'),
    ('BRA',           'bra'),
    ('SWIMSUIT',      'swimsuit'),
    ('BABY_BODYSUIT', 'baby_bodysuit'),
]

# (b) anchor item code → sibling item codes to clone (forced pendent_revisio)
SIBLINGS = {
    't_shirt':       ['polo', 'top_sleeveless', 'vest_top'],
    'blouse':        ['shirt_woven', 'overshirt', 'uniform_shirt'],
    'trousers':      ['chino', 'jeans', 'shorts', 'tracksuit_pant', 'workwear_pant'],
    'leggings':      ['culotte_cycling'],
    'dress_simple':  ['dress_fancy', 'shirt_dress', 'dress_structured'],
    'blazer':        ['gilet', 'casual_jacket'],
    'bra':           ['shapewear', 'corset'],
    'swimsuit':      ['bikini', 'swim_shorts'],
    'baby_bodysuit': ['baby_top', 'baby_dress', 'baby_leggings', 'baby_swimwear'],
}

# (c) families intentionally left empty (no anchor)
NO_ANCHOR_FAMILIES = [
    'KNIT_SWEATERS', 'KNIT_CARDIGANS', 'SWEATSHIRTS_MIDLAYERS', 'SKIRTS',
    'ADULT_JUMPSUITS', 'BABY_ONEPIECES', 'HEAVY_OUTERWEAR', 'UNDERWEAR',
]


class Command(BaseCommand):
    help = 'Seed GarmentPOMMap from old family anchors onto GarmentTypeItem (família → item).'

    def add_arguments(self, parser):
        parser.add_argument('--commit', action='store_true',
                            help='Write to DB. Without it: dry-run (default).')
        parser.add_argument('--schema', default='fhort', help='Tenant schema (default: fhort).')

    def handle(self, *args, **opts):
        commit = opts['commit']
        schema = opts['schema']
        with schema_context(schema):
            self._run(commit, schema)

    def _run(self, commit, schema):
        from fhort.pom.models import GarmentType, GarmentPOMMap
        from fhort.tasks.models import GarmentTypeItem

        review_field = any(f.name == 'pendent_revisio'
                           for f in GarmentPOMMap._meta.get_fields())

        def resolve_item(code):
            qs = list(GarmentTypeItem.objects.filter(code=code, active=True))
            if not qs:
                raise CommandError(f"Item destí '{code}' no trobat o inactiu.")
            if len(qs) > 1:
                raise CommandError(f"Item code '{code}' ambigu ({len(qs)} coincidències).")
            return qs[0]

        def resolve_old_gt(codi):
            cands = [gt for gt in GarmentType.objects.filter(codi_client=codi)
                     if GarmentPOMMap.objects.filter(garment_type=gt).exists()]
            if not cands:
                raise CommandError(f"GarmentType vell '{codi}' sense mapes (o no trobat).")
            if len(cands) > 1:
                raise CommandError(f"GarmentType '{codi}' ambigu ({len(cands)} amb mapes).")
            return cands[0]

        def item_has_maps(item):
            return GarmentPOMMap.objects.filter(garment_type_item=item).exists()

        def item_map_count(item):
            return GarmentPOMMap.objects.filter(garment_type_item=item).count()

        rows = []          # (family, item_code, n_poms, action)
        n_anchor = n_clone = n_skip = n_empty = 0

        @transaction.atomic
        def execute():
            nonlocal n_anchor, n_clone, n_skip, n_empty
            sp = transaction.savepoint()   # dry-run: roll back at the end

            for old_codi, anchor_code in ANCHORS:
                old_gt = resolve_old_gt(old_codi)
                dest = resolve_item(anchor_code)
                fam = dest.garment_type.codi_client
                src_maps = list(GarmentPOMMap.objects.filter(garment_type=old_gt)
                                .select_related('pom').order_by('ordre'))

                # --- (a) anchor ---
                if item_has_maps(dest):
                    rows.append((fam, anchor_code, item_map_count(dest), 'saltat-ja-té'))
                    n_skip += 1
                else:
                    for m in src_maps:
                        f = dict(garment_type_item=dest, garment_type=None, pom=m.pom,
                                 is_key=m.is_key, ordre=m.ordre, obligatori=m.obligatori)
                        if review_field:
                            f['pendent_revisio'] = getattr(m, 'pendent_revisio', False)
                        GarmentPOMMap.objects.create(**f)
                    rows.append((fam, anchor_code, len(src_maps), 'àncora'))
                    n_anchor += 1

                # --- (b) siblings (clone the anchor's source set) ---
                for sib_code in SIBLINGS.get(anchor_code, []):
                    sib = resolve_item(sib_code)
                    sfam = sib.garment_type.codi_client
                    if item_has_maps(sib):
                        rows.append((sfam, sib_code, item_map_count(sib), 'saltat-ja-té'))
                        n_skip += 1
                        continue
                    for m in src_maps:
                        f = dict(garment_type_item=sib, garment_type=None, pom=m.pom,
                                 is_key=m.is_key, ordre=m.ordre, obligatori=m.obligatori)
                        if review_field:
                            f['pendent_revisio'] = True
                        GarmentPOMMap.objects.create(**f)
                    rows.append((sfam, sib_code, len(src_maps), f'clon-de-{anchor_code}'))
                    n_clone += 1

            # --- (c) no-anchor families: report their active items as empty ---
            empties = (GarmentTypeItem.objects
                       .filter(garment_type__codi_client__in=NO_ANCHOR_FAMILIES, active=True)
                       .select_related('garment_type')
                       .order_by('garment_type__codi_client', 'complexity_order', 'code'))
            for it in empties:
                rows.append((it.garment_type.codi_client, it.code, 0, 'sense-àncora'))
                n_empty += 1

            if commit:
                transaction.savepoint_commit(sp)
            else:
                transaction.savepoint_rollback(sp)

        execute()

        # ── output ──
        mode = 'COMMIT' if commit else 'DRY-RUN'
        self.stdout.write(f"\n=== seed_pom_maps_to_items [{mode}] · schema={schema} ===")
        if not review_field:
            self.stdout.write("  ⚠ GarmentPOMMap NO té camp 'pendent_revisio' → el flag de revisió "
                              "dels clons NO es persisteix (decisió pendent abans del --commit).")
        self.stdout.write(f"\n{'FAMÍLIA':<24} {'ITEM':<22} {'#POMs':>6}  ACCIÓ")
        self.stdout.write('-' * 72)
        order = {'àncora': 0, 'clon-de-': 1, 'saltat-ja-té': 2, 'sense-àncora': 3}
        def keyf(r):
            a = r[3]
            grp = 1 if a.startswith('clon-de-') else order.get(a, 9)
            return (grp, r[0], r[1])
        for fam, item, n, action in sorted(rows, key=keyf):
            self.stdout.write(f"{fam:<24} {item:<22} {n:>6}  {action}")
        self.stdout.write('-' * 72)
        self.stdout.write(f"TOTALS: àncores sembrades={n_anchor} · clonats={n_clone} · "
                          f"saltats(ja-tenen)={n_skip} · buits(sense-àncora)={n_empty}")
        total_created = sum(n for _, _, n, a in rows if a == 'àncora' or a.startswith('clon-de-'))
        self.stdout.write(f"        mapes que es crearien = {total_created}")
        if not commit:
            self.stdout.write("\n(dry-run: cap escriptura; tot revertit al savepoint)")
