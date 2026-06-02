"""Backfill garment_type_item on legacy models (PAS 5, família → item migration).

For each model with an old garment_type and NO garment_type_item: assign the item per table A4,
then derive garment_type + garment_group from that item (same logic as _resolve_garment_def) so the
bridge is coherent. Tenant-scoped (default: fhort). Dry-run by default; --commit to write. All ORM.

Idempotent: a model that already has garment_type_item is SKIPPED.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

# old garment_type codi_client → destination item code (table A4)
BACKFILL = {
    'DRESS':         'dress_simple',
    'BABY_DRESS':    'baby_dress',
    'T_SHIRT':       't_shirt',
    'BLOUSE':        'blouse',
    'TROUSERS':      'trousers',
    'LEGGINGS':      'leggings',
    'JACKET':        'blazer',
    'BRA':           'bra',
    'SWIMSUIT':      'swimsuit',
    'BABY_BODYSUIT': 'baby_bodysuit',
}
# already a NEW family but missing item → default item + human-review flag (not clean legacy)
REVIEW = {
    'TAILORED_PANTS': 'trousers',
}


class Command(BaseCommand):
    help = 'Backfill garment_type_item on legacy models (família → item).'

    def add_arguments(self, parser):
        parser.add_argument('--commit', action='store_true',
                            help='Write to DB. Without it: dry-run (default).')
        parser.add_argument('--schema', default='fhort', help='Tenant schema (default: fhort).')

    def handle(self, *args, **opts):
        with schema_context(opts['schema']):
            self._run(opts['commit'], opts['schema'])

    def _run(self, commit, schema):
        from fhort.models_app.models import Model
        from fhort.pom.models import GarmentGroup
        from fhort.tasks.models import GarmentTypeItem

        def resolve_item(code):
            qs = list(GarmentTypeItem.objects.select_related('garment_type')
                      .filter(code=code, active=True))
            if not qs:
                raise CommandError(f"Item destí '{code}' no trobat o inactiu.")
            if len(qs) > 1:
                raise CommandError(f"Item code '{code}' ambigu ({len(qs)} coincidències).")
            return qs[0]

        rows = []   # (codi_intern, gt_actual, item, familia_derivada, estat)
        n_net = n_review = n_none = n_skip = 0

        @transaction.atomic
        def execute():
            nonlocal n_net, n_review, n_none, n_skip
            sp = transaction.savepoint()

            qs = Model.objects.select_related('garment_type', 'garment_type_item').order_by('id')
            for m in qs:
                gt_codi = m.garment_type.codi_client if m.garment_type_id else '(cap)'

                if m.garment_type_item_id:
                    rows.append((m.codi_intern, gt_codi, m.garment_type_item.code,
                                 m.garment_type_item.garment_type.codi_client, 'ja-té-item'))
                    n_skip += 1
                    continue

                code = BACKFILL.get(gt_codi)
                estat = 'backfill-net'
                if code is None:
                    code = REVIEW.get(gt_codi)
                    estat = 'revisió-TAILORED_PANTS' if code else None
                if code is None:
                    rows.append((m.codi_intern, gt_codi, '—', '—', 'sense-correspondència'))
                    n_none += 1
                    continue

                item = resolve_item(code)
                fam = item.garment_type
                # derivar família + grup (idèntic a _resolve_garment_def)
                m.garment_type_item = item
                m.garment_type = fam
                grp = GarmentGroup.objects.filter(codi=fam.grup).first()
                if grp is not None:
                    m.garment_group = grp
                m.save(update_fields=['garment_type_item', 'garment_type', 'garment_group'])

                rows.append((m.codi_intern, gt_codi, item.code, fam.codi_client, estat))
                if estat == 'backfill-net':
                    n_net += 1
                else:
                    n_review += 1

            if commit:
                transaction.savepoint_commit(sp)
            else:
                transaction.savepoint_rollback(sp)

        execute()

        mode = 'COMMIT' if commit else 'DRY-RUN'
        self.stdout.write(f"\n=== backfill_model_items [{mode}] · schema={schema} ===")
        self.stdout.write(f"\n{'MODEL':<18} {'GT ACTUAL':<16} {'ITEM':<16} {'FAMÍLIA DERIV.':<20} ESTAT")
        self.stdout.write('-' * 92)
        for codi, gt, item, fam, estat in rows:
            self.stdout.write(f"{codi:<18} {gt:<16} {item:<16} {fam:<20} {estat}")
        self.stdout.write('-' * 92)
        self.stdout.write(f"TOTALS: backfill-net={n_net} · revisió={n_review} · "
                          f"sense-correspondència={n_none} · ja-té-item={n_skip} · "
                          f"models={len(rows)}")
        if not commit:
            self.stdout.write("\n(dry-run: cap escriptura; tot revertit al savepoint)")
