"""
Autora la pertinença POM (GarmentPOMMap) dels items baby del tenant fhort.

BLOC 1 — 3 items nous sense maps (creació pura):
    53 baby_sleepsuit (19), 54 baby_sleepbag (12), 55 baby_bloomers (12) = 43 nous

BLOC 2 — 5 items BABY_SEPARATES existents (afinar el set genèric clonat):
    56 baby_bodysuit, 57 baby_top, 58 baby_dress, 59 baby_leggings, 60 baby_swimwear
    Per cada item es defineix el SET FINAL desitjat. El command:
      - crea els maps del set que no existeixin (+)
      - actualitza nivell/obligatori/is_key/ordre dels que existeixen i difereixen (~)
      - elimina els maps existents que NO són al set desitjat (-)

El set desitjat és l'única font de veritat → estat final idempotent i reproduïble.
nivell: K=key (oblig+key), M=mandatory (oblig), O=optional.

Acotat EXCLUSIVAMENT als 8 items baby llistats. No toca cap altre item, POMMaster,
POMGlobal, SizeSystem ni res de l'ERP.

Run:  python manage.py author_baby_pom_maps               # dry-run
      python manage.py author_baby_pom_maps --no-dry-run  # escriu
"""
import argparse

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

SCHEMA = 'fhort'

# level → (obligatori, is_key)
LEVEL = {'K': (True, True), 'M': (True, False), 'O': (False, False)}

# Set FINAL desitjat per item: (pom_master_id, level). L'ordre de la llista = ordre.
ITEMS = {
    # ── BLOC 1 — items nous (creació pura) ──────────────────────────────────
    53: {  # baby_sleepsuit — pelele full-body (mànigues, cames, peu, entrecuix)
        'label': 'baby_sleepsuit',
        'set': [
            (273, 'K'), (281, 'K'), (282, 'O'), (308, 'M'), (301, 'M'),
            (292, 'M'), (297, 'O'), (312, 'M'), (311, 'O'), (413, 'K'),
            (409, 'M'), (410, 'K'), (411, 'M'), (412, 'O'), (359, 'M'),
            (414, 'O'), (415, 'O'), (416, 'O'), (417, 'O'),
        ],
    },
    54: {  # baby_sleepbag — sac full-body (sense cames ni peu)
        'label': 'baby_sleepbag',
        'set': [
            (273, 'K'), (281, 'K'), (282, 'O'), (308, 'M'), (301, 'M'),
            (287, 'O'), (292, 'O'), (341, 'K'), (359, 'M'), (361, 'O'),
            (414, 'O'), (417, 'O'),
        ],
    },
    55: {  # baby_bloomers — ranita (bottom, entrecuix, cames curtes)
        'label': 'baby_bloomers',
        'set': [
            (318, 'K'), (319, 'M'), (308, 'K'), (310, 'M'), (311, 'M'),
            (312, 'O'), (321, 'M'), (322, 'O'), (413, 'K'), (414, 'M'),
            (415, 'O'), (416, 'O'),
        ],
    },
    # ── BLOC 2 — items existents (afinar) ───────────────────────────────────
    56: {  # baby_bodysuit — body (snap, entrecuix curt)
        'label': 'baby_bodysuit',
        'set': [
            (273, 'K'), (281, 'K'), (282, 'O'), (301, 'M'), (302, 'O'),
            (359, 'M'), (360, 'K'), (361, 'M'), (292, 'O'), (295, 'O'),
            (413, 'K'), (414, 'O'),
        ],
    },
    57: {  # baby_top — topwear (mànigues/coll/pit)
        'label': 'baby_top',
        'set': [
            (273, 'K'), (281, 'K'), (282, 'O'), (301, 'M'), (302, 'O'),
            (277, 'M'), (280, 'O'), (292, 'M'), (295, 'O'), (297, 'O'),
            (361, 'O'),
        ],
    },
    58: {  # baby_dress — vestit
        'label': 'baby_dress',
        'set': [
            (273, 'K'), (281, 'K'), (282, 'O'), (301, 'M'), (302, 'O'),
            (276, 'M'), (359, 'O'), (361, 'O'), (292, 'O'), (295, 'O'),
        ],
    },
    59: {  # baby_leggings — pantaló (waist/hip/crotch/elastic)
        'label': 'baby_leggings',
        'set': [
            (318, 'K'), (319, 'M'), (308, 'K'), (310, 'M'), (311, 'M'),
            (312, 'M'), (313, 'O'), (321, 'M'), (322, 'O'), (413, 'K'),
            (414, 'M'), (416, 'O'),
        ],
    },
    60: {  # baby_swimwear — bany nadó (one-piece, sense mànigues)
        'label': 'baby_swimwear',
        'set': [
            (273, 'K'), (281, 'K'), (282, 'O'), (301, 'O'), (308, 'M'),
            (339, 'K'), (340, 'M'), (338, 'O'), (414, 'O'),
        ],
    },
}


class Command(BaseCommand):
    help = 'Autora/afina GarmentPOMMap dels 8 items baby del tenant fhort (dry-run per defecte).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action=argparse.BooleanOptionalAction,
            default=True,
            help='Imprimeix què faria sense escriure res (default). Usa --no-dry-run per escriure.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        mode = 'DRY-RUN (cap escriptura)' if dry_run else 'ESCRIPTURA REAL'
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'author_baby_pom_maps — mode: {mode} — schema: {SCHEMA} — items: {len(ITEMS)}'
        ))

        tot_c = tot_d = tot_u = tot_n = 0

        with schema_context(SCHEMA):
            from fhort.pom.models import GarmentPOMMap, POMMaster
            from fhort.tasks.models import GarmentTypeItem

            # Validació prèvia: tots els pom_master del set existeixen i són actius.
            all_pom_ids = {pid for cfg in ITEMS.values() for pid, _ in cfg['set']}
            valid = dict(POMMaster.objects.filter(pk__in=all_pom_ids).values_list('id', 'actiu'))
            bad = [pid for pid in all_pom_ids if pid not in valid or not valid[pid]]
            if bad:
                self.stderr.write(self.style.ERROR(
                    f'POMMaster invàlids/inactius al set: {sorted(bad)} — ABORTAT, no s\'escriu res.'))
                return

            for item_id, cfg in ITEMS.items():
                item = GarmentTypeItem.objects.filter(pk=item_id).first()
                if item is None or not item.active:
                    self.stdout.write(self.style.ERROR(
                        f"  item id={item_id} ({cfg['label']}) NO existeix o inactiu — skip"))
                    continue

                desired = cfg['set']
                desired_ids = [pid for pid, _ in desired]
                existing = {m.pom_id: m for m in GarmentPOMMap.objects.filter(garment_type_item=item)}

                creates, updates, unchanged, deletes = [], [], [], []

                # Creates / updates segons el set desitjat
                for ordre, (pid, lvl) in enumerate(desired, start=1):
                    oblig, key = LEVEL[lvl]
                    m = existing.get(pid)
                    if m is None:
                        creates.append((pid, lvl, ordre))
                    else:
                        if (m.nivell != lvl or bool(m.obligatori) != oblig
                                or bool(m.is_key) != key or m.ordre != ordre):
                            updates.append((pid, lvl, ordre, m))
                        else:
                            unchanged.append(pid)

                # Deletes: maps existents que NO són al set desitjat
                for pid, m in existing.items():
                    if pid not in desired_ids:
                        deletes.append((pid, m))

                self.stdout.write('')
                self.stdout.write(self.style.HTTP_INFO(
                    f"━━━ item {item_id} {cfg['label']} ━━━  "
                    f"+{len(creates)} creats · -{len(deletes)} eliminats · "
                    f"~{len(updates)} actualitzats · ={len(unchanged)} sense canvi  "
                    f"(final={len(desired)})"
                ))
                for pid, lvl, ordre in creates:
                    self.stdout.write(self.style.SUCCESS(
                        f"    [+] crea  pom={pid} nivell={lvl} ordre={ordre}"))
                for pid, lvl, ordre, m in updates:
                    self.stdout.write(
                        f"    [~] upd   pom={pid} nivell {m.nivell}→{lvl} "
                        f"oblig {int(m.obligatori)}→{int(LEVEL[lvl][0])} "
                        f"key {int(m.is_key)}→{int(LEVEL[lvl][1])} ordre {m.ordre}→{ordre}")
                for pid, m in deletes:
                    self.stdout.write(self.style.WARNING(
                        f"    [-] elim  pom={pid} (nivell={m.nivell})"))

                tot_c += len(creates); tot_d += len(deletes)
                tot_u += len(updates); tot_n += len(unchanged)

                if not dry_run:
                    self._apply(GarmentPOMMap, item, creates, updates, deletes)

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'TOTAL: +{tot_c} creats · -{tot_d} eliminats · ~{tot_u} actualitzats · ={tot_n} sense canvi'))
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY-RUN: no s'ha escrit res. Torna a executar amb --no-dry-run per aplicar."))
        else:
            self.stdout.write(self.style.SUCCESS('Fet.'))

    @transaction.atomic
    def _apply(self, GarmentPOMMap, item, creates, updates, deletes):
        for pid, m in deletes:
            m.delete()
        for pid, lvl, ordre in creates:
            oblig, key = LEVEL[lvl]
            GarmentPOMMap.objects.create(
                garment_type_item=item, pom_id=pid,
                nivell=lvl, obligatori=oblig, is_key=key, ordre=ordre,
            )
        for pid, lvl, ordre, m in updates:
            oblig, key = LEVEL[lvl]
            m.nivell = lvl; m.obligatori = oblig; m.is_key = key; m.ordre = ordre
            m.save(update_fields=['nivell', 'obligatori', 'is_key', 'ordre'])
