"""§4 · EQUIVALÈNCIA DE LA MIGRACIÓ 1-break → INTERVALS. READ-ONLY, cap escriptura.

Forma d'intervals (decisió MULTI-BREAK v2):
  · delta GENERAL per defecte a totes les talles
  · N intervals (talla_inici → talla_final) inclusius, amb delta propi
  · el delta és ENTRE TALLES CONSECUTIVES

Regla de lectura proposada, i és la que reprodueix el motor d'avui:
  «una aresta pren el delta de l'interval que conté el seu EXTREM EXTERIOR (la talla
   de l'aresta més allunyada de la BASE); si cap interval no el conté, el GENERAL.»

MIGRACIÓ provada aquí:  general = increment_base
                        interval = [talla_break_label  ..  ÚLTIMA talla del SIZESYSTEM]
                        delta de l'interval = increment_break
                        (etiqueta SENSE desplaçar: la BD ja desa la convenció de MOTOR)
"""
import os, sys
sys.path.insert(0,'/var/www/ftt-staging/backend'); os.environ.setdefault('DJANGO_SETTINGS_MODULE','fhort.settings')
import django; django.setup()
from django_tenants.utils import schema_context
from fhort.pom.grading_utils import _norm, increment_de_l_aresta, _break_idx_de


# ── LA FORMA NOVA, implementada des de zero (no crida el motor) ───────────────
def a_intervals(rule, run_sistema):
    """1-break → {'general': float, 'intervals': [(i_ini, i_fi, delta)]} en índexs de sistema."""
    ib_raw = getattr(rule, 'increment_base', None)
    if ib_raw is None:
        inc = getattr(rule, 'increment', None)
        return {'general': float(inc) if inc is not None else 0.0, 'intervals': []}
    ib = float(ib_raw)
    brk_raw = getattr(rule, 'increment_break', None)
    brk = float(brk_raw) if brk_raw is not None else ib
    bidx = _break_idx_de(rule, run_sistema)
    if bidx is None:
        return {'general': ib, 'intervals': []}
    return {'general': ib, 'intervals': [(bidx, len(run_sistema) - 1, brk)]}


def aresta_interval(forma, base_idx, i, j):
    """El delta d'una aresta en forma d'INTERVALS. Cap referència al motor."""
    aresta = min(i, j)
    exterior = aresta + 1 if aresta >= base_idx else aresta
    for (ini, fi, delta) in forma['intervals']:
        if ini <= exterior <= fi:
            return delta
    return forma['general']


def corba(delta_de_l_aresta, base_val, base_idx, idx):
    """Valor d'una talla acumulant arestes des de la base (mateix ordre de suma que el motor)."""
    if idx == base_idx:
        return base_val
    lo, hi = (base_idx, idx) if idx > base_idx else (idx, base_idx)
    tot = sum(delta_de_l_aresta(k, k + 1) for k in range(lo, hi))
    return base_val + (tot if idx > base_idx else -tot)


def main():
    with schema_context('fhort'):
        from fhort.models_app.models import Model, ModelGradingRule, BaseMeasurement
        from fhort.pom.services import escala_del_model
        model = Model.objects.select_related('size_system').get(pk=1383)
        size_run, run_sistema, _pos, base_idx = escala_del_model(model)
        print(f"model 1383 · size_run {size_run} · run_sistema {run_sistema} · base_idx {base_idx}")
        print(f"MIGRACIÓ: interval = [talla_break_label .. {run_sistema[-1]}] (última del SIZESYSTEM)\n")

        bases = {bm.pom_id: float(bm.base_value_cm) for bm in
                 BaseMeasurement.objects.filter(model_id=1383, is_active=True,
                                                base_value_cm__isnull=False).exclude(base_value_cm=0)}
        regles = {r.pom_id: r for r in ModelGradingRule.objects
                  .filter(model_id=1383, actiu=True).select_related('pom')}

        ok = dif = 0
        detall = {}
        for pom_id, base_val in bases.items():
            r = regles.get(pom_id)
            if r is None or r.logica not in ('LINEAR', 'FIXED'):
                continue
            forma = a_intervals(r, run_sistema)
            fila_v, fila_n = {}, {}
            for lab in size_run:
                i = _pos(lab)
                if r.logica == 'FIXED' and getattr(r, 'increment_base', None) is None:
                    v = n = base_val                      # FIXED no passa per arestes
                else:
                    v = corba(lambda a, b: increment_de_l_aresta(r, run_sistema, base_idx, a, b),
                              base_val, base_idx, i)
                    n = corba(lambda a, b: aresta_interval(forma, base_idx, a, b),
                              base_val, base_idx, i)
                fila_v[lab], fila_n[lab] = round(v, 2), round(n, 2)
                if abs(v - n) > 0.005:
                    dif += 1
                else:
                    ok += 1
            detall[r.pom.codi_client] = (r, forma, fila_v, fila_n)

        print(f"CEL·LES  IDÈNTIQUES={ok}  DIVERGENTS={dif}   ({len(detall)} regles LINEAR/FIXED amb base)\n")

        for codi in ('A', 'C', 'D'):
            if codi not in detall:
                print(f"── POM {codi}: no és entre les regles amb mesura base"); continue
            r, forma, v, n = detall[codi]
            iv = ', '.join(f"[{run_sistema[a]}..{run_sistema[b]}] Δ={d}" for a, b, d in forma['intervals']) or '—'
            print(f"── POM {codi}  ({r.logica}, origen={r.origen})")
            print(f"   AVUI      ib={r.increment_base} · brk={r.increment_break} · break={r.talla_break_label} "
                  f"· increment(llegat)={r.increment}")
            print(f"   INTERVALS general Δ={forma['general']} · {iv}")
            print(f"   motor     " + "  ".join(f"{k}={v[k]}" for k in size_run))
            print(f"   intervals " + "  ".join(f"{k}={n[k]}" for k in size_run))
            print(f"   → {'IDÈNTIC' if v == n else 'DIVERGEIX'}\n")

        # El contra-experiment: la migració amb l'etiqueta DESPLAÇADA una posició.
        print("── CONTRA-EXPERIMENT · interval que comença a la talla SEGÜENT ──")
        dif2 = 0
        for codi, (r, _f, v, _n) in detall.items():
            bidx = _break_idx_de(r, run_sistema)
            if bidx is None or getattr(r, 'increment_base', None) is None:
                continue
            ib = float(r.increment_base)
            brk = float(r.increment_break) if r.increment_break is not None else ib
            f2 = {'general': ib, 'intervals': [(bidx + 1, len(run_sistema) - 1, brk)]}
            for lab in size_run:
                n2 = round(corba(lambda a, b: aresta_interval(f2, base_idx, a, b),
                                 float(bases[r.pom_id]), base_idx, _pos(lab)), 2)
                if abs(v[lab] - n2) > 0.005:
                    dif2 += 1
        print(f"   cel·les que es MOUEN si l'inici de l'interval es desplaça +1: {dif2}")


main()
