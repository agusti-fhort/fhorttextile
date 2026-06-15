"""Backfill de la forma canònica de break a GradingRule (Peça A).

Omple increment_base / increment_break / talla_break_label / talla_break_pos a partir de
tres fonts, sense tocar valors_step (origen/auditoria). Idempotent (recomputa els mateixos
valors) i amb --dry-run (recompte sense desar).

Fonts:
  (a) STEP amb valors_step per-etiqueta (import): increment_base = delta inicial,
      talla_break_label = primera etiqueta on el delta canvia, increment_break = delta final.
  (b) LINEAR amb above_xl dins valors_step (ISO): increment_base = increment escalar,
      increment_break = above_xl, talla_break_label = la talla "per sobre de XL":
        - ruleset amb run i 'XL' no-últim → talla següent a XL (p.ex. 'XXL').
        - ruleset amb run i 'XL' últim → inert (label None; cap talla per sobre).
        - ruleset SENSE run (size_system NULL) i nom NO numèric/dress → 'XXL' (semàntica alpha).
        - numèric o dress sense run → NO-RESOLT (no inventem; queda amb valors_step + fallback).
  (c) LINEAR pur (sense above_xl) → increment_base = increment, talla_break_label None.
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context


def _n(x):
    return str(x or '').strip().upper()


class Command(BaseCommand):
    help = "Backfill canonical break fields on GradingRule (idempotent)."

    def add_arguments(self, p):
        p.add_argument('--schema', default='fhort')
        p.add_argument('--dry-run', action='store_true')

    def handle(self, *a, **o):
        from fhort.pom.models import GradingRule, SizeDefinition

        dry = o['dry_run']
        with schema_context(o['schema']):
            st = {'step': 0, 'iso_xxl': 0, 'inert': 0, 'linear': 0, 'noresolt': 0, 'skip': 0}
            noresolt_rs = {}
            run_cache = {}

            def run_of(rs):
                if not rs or not rs.size_system_id:
                    return []
                if rs.size_system_id not in run_cache:
                    run_cache[rs.size_system_id] = list(
                        SizeDefinition.objects.filter(size_system_id=rs.size_system_id)
                        .order_by('ordre').values_list('etiqueta', flat=True))
                return run_cache[rs.size_system_id]

            for r in GradingRule.objects.select_related('rule_set__size_system').all():
                vs = r.valors_step if isinstance(r.valors_step, dict) else None
                run = run_of(r.rule_set)
                ib = ibrk = tlabel = tpos = None

                if r.logica == 'STEP' and vs and 'above_xl' not in vs:
                    # (a) import STEP per-etiqueta
                    ordre = run if run else list(vs.keys())
                    seq = [(l, vs[l]) for l in ordre if l in vs and vs[l] is not None]
                    if not seq:
                        st['noresolt'] += 1
                        noresolt_rs[r.rule_set.nom] = noresolt_rs.get(r.rule_set.nom, 0) + 1
                        continue
                    ib = float(seq[0][1])
                    for l, d in seq:
                        if abs(float(d) - ib) > 0.001:
                            tlabel, ibrk = l, float(d)
                            break
                    tpos = run.index(tlabel) if (tlabel and tlabel in run) else None
                    st['step'] += 1

                elif vs and 'above_xl' in vs:
                    # (b) ISO above_xl
                    ib = float(r.increment or 0)
                    ibrk = float(vs['above_xl'])
                    up = [_n(x) for x in run]
                    nom = (r.rule_set.nom or '').lower()
                    if run and 'XL' in up and up.index('XL') + 1 < len(run):
                        tpos = up.index('XL') + 1
                        tlabel = run[tpos]
                        st['iso_xxl'] += 1
                    elif run and 'XL' in up:           # XL és l'última → inert
                        tlabel = None
                        st['inert'] += 1
                    elif not run and 'numeric' not in nom and 'dress' not in nom:
                        tlabel = 'XXL'                 # null-ss alpha → semàntica
                        st['iso_xxl'] += 1
                    else:                              # numèric/dress sense run → no-resolt
                        st['noresolt'] += 1
                        noresolt_rs[r.rule_set.nom] = noresolt_rs.get(r.rule_set.nom, 0) + 1
                        continue

                elif r.logica == 'LINEAR':
                    # (c) LINEAR pur
                    ib = float(r.increment or 0)
                    tlabel = None
                    st['linear'] += 1
                else:
                    st['skip'] += 1                    # FIXED/ZERO/etc → sense forma canònica
                    continue

                if not dry:
                    r.increment_base = ib
                    r.increment_break = ibrk
                    r.talla_break_label = tlabel
                    r.talla_break_pos = tpos
                    r.save(update_fields=['increment_base', 'increment_break',
                                          'talla_break_label', 'talla_break_pos'])

            self.stdout.write(self.style.SUCCESS(
                f"{'DRY-RUN ' if dry else ''}backfill: {st}"))
            if noresolt_rs:
                self.stdout.write("  no-resolts per ruleset:")
                for nom, n in sorted(noresolt_rs.items()):
                    self.stdout.write(f"    {n:>3}  {nom}")
