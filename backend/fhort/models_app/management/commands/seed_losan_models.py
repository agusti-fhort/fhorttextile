"""Sembra dels 961 models LOSAN SS27 (customer LOS) des del CSV versionat.

Reutilitza el camí bulk existent (`_build_model`, `reserve_sequence_range`, `build_catalog`):
NOMÉS afegeix el que el bulk no fa — B2 (grading_rule_set per NOM+LOS) i garment_group resolt
del catàleg — més la materialització dels watchpoints. NO crea tasques ni mesures (ordre CTO).

Dry-run per defecte; --apply escriu. Idempotent per (customer LOS, codi_client): un model que ja
existeix NO es sobreescriu. Lots ≤600 (límit del bulk). Font: LLEI_MODEL_CATALEGS (una font única).
"""
import csv
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

CSV_PATH = (Path(__file__).resolve().parents[3] / 'pom' / 'seed_data'
            / 'sembra_models_losan_ss27.csv')
BATCH = 600  # límit conegut del bulk


def _norm_name(s):
    """Forma normalitzada per al matching DEFENSIU de noms de ruleset (Decisió 1):
    NFC + equiparar guions (-/–/—) + col·lapsar espais + casefold. Amb el fitxer real els
    em-dash són reals i el matching hauria de casar EXACTE; això és la xarxa de seguretat."""
    s = unicodedata.normalize('NFC', s or '')
    s = s.replace('–', '-').replace('—', '-')  # en-dash, em-dash → guionet
    s = re.sub(r'\s+', ' ', s).strip()
    return s.casefold()


def _parse_temporada(val):
    """'SS27' → ('SS', 2027). Season = 2 primers chars; any = 2000 + darrers 2 dígits."""
    val = (val or '').strip()
    if len(val) < 4 or not val[2:].isdigit():
        return None, None
    return val[:2], 2000 + int(val[2:])


def _split_labels(val):
    """'S; M; L' → ['S','M','L']. Buit → []."""
    return [t.strip() for t in (val or '').replace(';', '·').split('·') if t.strip()]


def _split_watchpoints(val):
    """El CSV separa els tokens de watchpoint amb ' · ' (U+00B7). Retorna la llista de tokens."""
    return [t.strip() for t in (val or '').split('·') if t.strip()]


class Command(BaseCommand):
    help = "Sembra els 961 models LOSAN SS27 (customer LOS) des del CSV versionat (dry-run per defecte)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help="Escriu de debò. Sense això, dry-run (només informe).")
        parser.add_argument('--csv', default=str(CSV_PATH),
                            help="Ruta al CSV (per defecte el versionat a pom/seed_data/).")
        parser.add_argument('--schema', default='fhort',
                            help="Schema del tenant (django-tenants). Per defecte 'fhort'.")

    def handle(self, *args, **opts):
        with schema_context(opts['schema']):
            self._run(opts)

    def _run(self, opts):
        from fhort.pom.models import GradingRuleSet, GarmentType, GarmentGroup, SizeSystem
        from fhort.tasks.models import Customer, GarmentTypeItem
        from fhort.models_app.models import Model, Watchpoint
        from fhort.models_app.bulk_import_service import _build_model
        from fhort.models_app.services import reserve_sequence_range

        apply = opts['apply']
        path = Path(opts['csv'])
        if not path.exists():
            raise CommandError(f"CSV no trobat: {path}")

        los = Customer.objects.filter(codi='LOS').first()
        if not los:
            raise CommandError("Customer LOS no trobat al tenant.")

        # ── Catàlegs de resolució (natural key). Una sola lectura, font única. ──────────────
        gt_by_codi = {g.codi_client: g for g in GarmentType.objects.all()}
        item_by_code = {i.code: i for i in GarmentTypeItem.objects.select_related('garment_type')}
        ss_by_codi = {s.codi: s for s in SizeSystem.objects.all()}
        grp_by_codi = {g.codi: g for g in GarmentGroup.objects.all()}

        # B2 — índexs de rulesets del client LOS: exacte i normalitzat (Decisió 1).
        los_rs = list(GradingRuleSet.objects.filter(customer=los))
        rs_exact, rs_norm = {}, {}
        for rs in los_rs:
            rs_exact.setdefault(rs.nom, []).append(rs)
            rs_norm.setdefault(_norm_name(rs.nom), []).append(rs)

        existing_codis = set(
            Model.objects.filter(customer=los).values_list('codi_client', flat=True))

        # ── Comptadors i acumuladors de l'informe ──────────────────────────────────────────
        n_total = n_exists = n_blocked = 0
        n_ruleset = 0
        match_exact = match_norm = 0
        by_system, by_item, by_watchpoint = {}, {}, {}
        blocked_rows = []            # (codi_client, motiu)
        grup_contrast_warn = []      # (codi_client, csv_grup, cataleg_grup)
        creatable = []               # (row_dict, gt, item, ss, grs, grp, watch_tokens)

        with path.open(encoding='utf-8', newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                n_total += 1
                codi_client = (row.get('codi_client') or '').strip()

                # Idempotència per (LOS, codi_client): existent → no es toca.
                if codi_client in existing_codis:
                    n_exists += 1
                    continue

                reasons = []
                gt = gt_by_codi.get((row.get('garment_type') or '').strip())
                if gt is None:
                    reasons.append(f"garment_type '{row.get('garment_type')}' no resol")
                item = item_by_code.get((row.get('garment_type_item') or '').strip())
                if item is None:
                    reasons.append(f"garment_type_item '{row.get('garment_type_item')}' no resol")
                ss = ss_by_codi.get((row.get('size_system') or '').strip())
                if ss is None:
                    reasons.append(f"size_system '{row.get('size_system')}' no resol")

                # B2 — grading_rule_set per NOM+LOS. Buit → NULL (PENDING_GRADING ja al CSV).
                grs = None
                rs_name = (row.get('grading_rule_set') or '').strip()
                if rs_name:
                    exact = rs_exact.get(rs_name)
                    if exact and len(exact) == 1:
                        grs, how = exact[0], 'exact'
                    elif exact and len(exact) > 1:
                        reasons.append(f"ruleset '{rs_name}' AMBIGU (exacte, {len(exact)})")
                        how = None
                    else:
                        norm = rs_norm.get(_norm_name(rs_name))
                        if not norm:
                            reasons.append(f"ruleset '{rs_name}' no resol")
                            how = None
                        elif len(norm) > 1:
                            reasons.append(f"ruleset '{rs_name}' AMBIGU (normalitzat, {len(norm)})")
                            how = None
                        else:
                            grs, how = norm[0], 'normalized'
                    if grs is not None:
                        if how == 'exact':
                            match_exact += 1
                        else:
                            match_norm += 1

                if reasons:
                    n_blocked += 1
                    blocked_rows.append((codi_client, '; '.join(reasons)))
                    continue

                # garment_group des del CATÀLEG (Decisió 3): garment_type.grup (font única).
                grp = grp_by_codi.get(gt.grup)
                csv_grup = (row.get('garment_group') or '').strip()
                if csv_grup and gt.grup and csv_grup != gt.grup:
                    grup_contrast_warn.append((codi_client, csv_grup, gt.grup))

                watch_tokens = _split_watchpoints(row.get('watchpoints'))

                creatable.append((row, gt, item, ss, grs, grp, watch_tokens))
                if grs is not None:
                    n_ruleset += 1
                by_system[ss.codi] = by_system.get(ss.codi, 0) + 1
                by_item[item.code] = by_item.get(item.code, 0) + 1
                for tk in watch_tokens:
                    key = tk.split(':', 1)[0]  # agrupa 'MARCADORS_ERP_FILTRATS:10|12' → clau
                    by_watchpoint[key] = by_watchpoint.get(key, 0) + 1

        # ── APLICAR (només --apply) ─────────────────────────────────────────────────────────
        n_created = 0
        if apply and creatable:
            with transaction.atomic():
                # Reserva de seqüencials per (any, temporada). Tots són SS/2027, però ho fem general.
                buckets = {}
                for tup in creatable:
                    _, tp = _parse_temporada(tup[0].get('temporada'))
                    sp, _ = _parse_temporada(tup[0].get('temporada'))
                    buckets.setdefault((tp, sp), []).append(tup)

                new_models, new_watch = [], []  # (Model), (model_ref, text, dades)
                for (year, season), tups in buckets.items():
                    first, _last = reserve_sequence_range(los, year, season, len(tups))
                    seq = first
                    yy = str(year)[-2:].zfill(2)
                    for row, gt, item, ss, grs, grp, watch_tokens in tups:
                        codi_intern = f"{los.codi}-{season}{yy}-{str(seq).zfill(4)}"
                        r = {
                            'codi_client': (row.get('codi_client') or '').strip(),
                            'any': year, 'temporada': season,
                            'nom_prenda': (row.get('nom') or '').strip() or None,
                            'color_referencia': None,                       # Decisió 4: descartat
                            'collection': (row.get('familia_client') or '').strip(),  # Decisió 2
                            'garment_type': gt, 'garment_type_item': item,
                            'target': (row.get('target') or '').strip() or None,
                            'construction': (row.get('construccio') or '').strip() or None,
                            'size_system': ss,
                            'run_labels': _split_labels(row.get('talles_model')),
                            'base_size': (row.get('talla_base') or '').strip() or None,
                            'piece_number': None,
                        }
                        m = _build_model(los, codi_intern, seq, r, creat_per_profile=None)
                        m.grading_rule_set = grs
                        m.garment_group = grp                                # Decisió 3
                        new_models.append(m)
                        for tk in watch_tokens:
                            new_watch.append((codi_intern, tk))
                        seq += 1

                for i in range(0, len(new_models), BATCH):
                    Model.objects.bulk_create(new_models[i:i + BATCH])
                n_created = len(new_models)

                # Watchpoints de sistema (task=NULL) idempotents per (model, text).
                by_codi = {m.codi_intern: m for m in
                           Model.objects.filter(customer=los,
                                                 codi_intern__in=[c for c, _ in new_watch])}
                for codi_intern, text in new_watch:
                    m = by_codi.get(codi_intern)
                    if m is None:
                        continue
                    Watchpoint.objects.get_or_create(
                        model=m, text=text,
                        defaults={'task': None, 'dades': {'seed_token': text}, 'estat': 'open'})

        # ── INFORME ─────────────────────────────────────────────────────────────────────────
        w = self.stdout.write
        w("")
        w(f"{'APLICAT' if apply else 'DRY-RUN'} · sembra LOSAN SS27 (customer LOS #{los.id})")
        w(f"  files CSV totals ......... {n_total}")
        w(f"  ja existents (saltades) .. {n_exists}")
        w(f"  bloquejades .............. {n_blocked}")
        w(f"  a crear .................. {len(creatable)}")
        if apply:
            w(f"  CREATS ................... {n_created}")
        w(f"  amb grading_rule_set ..... {n_ruleset}  (exacte={match_exact} · normalitzat={match_norm})")
        w("  per size_system:")
        for k in sorted(by_system):
            w(f"      {k:<20} {by_system[k]}")
        w("  per item:")
        for k in sorted(by_item):
            w(f"      {k:<20} {by_item[k]}")
        w("  per watchpoint:")
        for k in sorted(by_watchpoint):
            w(f"      {k:<32} {by_watchpoint[k]}")
        if grup_contrast_warn:
            w(f"  ⚠️ contrast garment_group CSV≠catàleg ({len(grup_contrast_warn)}):")
            for codi, csvg, catg in grup_contrast_warn[:20]:
                w(f"      {codi}: CSV={csvg} · catàleg={catg}")
        if blocked_rows:
            w(f"  ⛔ files bloquejades ({len(blocked_rows)}):")
            for codi, motiu in blocked_rows[:40]:
                w(f"      {codi}: {motiu}")
        w("")
