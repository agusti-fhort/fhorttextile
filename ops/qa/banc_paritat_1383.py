#!/usr/bin/env python
"""BANC DE PARITAT DEL MOTOR DE GRADUACIÓ — model 1383 (BANC S45, tenant `fhort`).

EL GATE dels sprints de motor (fix A · E · F). Es corre ABANS i DESPRÉS de cada pas.

    cd /var/www/ftt-staging/backend
    PGOPTIONS='-c default_transaction_read_only=on' \
      venv/bin/python ../ops/qa/banc_paritat_1383.py [-v] [--model 1383] [--tenant fhort]

READ-ONLY: no escriu res, ni per l'ORM ni per cap servei. Cap `generate_graded_specs`, cap
`save()`. La sessió s'obre `default_transaction_read_only=on` per si de cas.

───────────────────────────────────────────────────────────────────────────────────────────
🚨 PER QUÈ EL BANC TÉ TRES BLOCS I NO UN
───────────────────────────────────────────────────────────────────────────────────────────
La diagnosi pre-sprints (§1.3, 21/08) va trobar que el fallback al camp llegat `increment`
**vivia a DOS nodes**, no a un:

    ① pom/services.py       `_apply_rule`, branca LINEAR      → motor de propagació (GradedSpec)
    ② pom/grading_utils.py  `increment_de_l_aresta`           → `propaga_ancoratges`, que serveix
                                                                la PRESA (fitting/views.py) i la
                                                                derivació de base (models_app)

Un banc que només mesurés ① podia donar VERD amb Escalat i la presa dient coses diferents
sobre la mateixa regla. Per això:

  · BLOC A — PARITAT DE GRADEDSPEC .... camí ①. Recalcula les cel·les amb el motor i les
                                        contrasta amb els `GradedSpec` de la versió vigent.
  · BLOC B — PARITAT DE LA PRESA ...... camí ②. `propaga_ancoratges` ancorada a CADA talla del
                                        run ha de reproduir la MATEIXA corba (llei FIX-1:
                                        «propagar des de qualsevol talla reprodueix la mateixa
                                        corba»). Si ① i ② divergeixen, això ho canta.
  · BLOC C — COHERÈNCIA DELS DOS NODES  sonda PURA (cap BD) sobre una regla amb `increment_base`
                                        a NULL — el cas que el corpus viu no té i que és
                                        exactament el que el fix A toca. **No exigeix un valor
                                        concret**: exigeix que els DOS nodes diguin el MATEIX,
                                        abans i després del fix.

Sortida i codi de sortida 0 només si els tres blocs són verds I el hash del joc és el de
referència.
"""
import os
import sys
import json
import hashlib
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402
django.setup()

from django_tenants.utils import schema_context  # noqa: E402

# Hash del joc `BRW-CATALEG-v3` (pk=219 a staging) tal com el va segellar la sembra del 21/08
# (SEMBRA_837_STAGING_2026-08-21.md §5). Si canvia, el joc sota el banc s'ha mogut i cap
# resultat anterior és comparable.
HASH_JOC_REFERENCIA = '096990db404b778a2140fffd8327c54294849b73d42ec67b3265247f9840989f'

TOL = 0.005     # els valors es comparen arrodonits a 2 decimals; això és mig últim dígit


# ─── hashos ────────────────────────────────────────────────────────────────────────────────
def _n(x):
    """Normalització numèrica: 4 decimals, o str, o None. La de `sembra_model_837`."""
    if x is None:
        return None
    try:
        return "%.4f" % float(x)
    except (TypeError, ValueError):
        return str(x)


def _hash(rows):
    rows = sorted(rows, key=lambda r: json.dumps(r, sort_keys=True, ensure_ascii=False))
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def hash_del_joc(rule_set):
    """Mateixa fórmula que `sembra_model_837._verifica_ruleset` (ordre de camps inclòs)."""
    from fhort.pom.models import GradingRule
    rows = [[getattr(r.pom.pom_global, 'codi', None) if r.pom.pom_global_id else None,
             r.pom.codi_client, r.logica, _n(r.increment), _n(r.increment_base),
             _n(r.increment_break), r.talla_break_label, r.talla_break_pos,
             getattr(r.talla_base, 'etiqueta', None),
             json.dumps(r.valors_step, sort_keys=True) if r.valors_step is not None else None,
             bool(r.actiu)]
            for r in GradingRule.objects.filter(rule_set=rule_set)
            .select_related('pom', 'pom__pom_global', 'talla_base')]
    return len(rows), _hash(rows)


def hash_de_les_residents(model):
    """Hash de les `ModelGradingRule` del model.

    Hi entra el `garment` (eix propi de les residents, que el joc del catàleg no té) i **hi entra
    `increment`**, perquè el backfill del fix A el toca i el gate ha de poder-ho veure. No hi entra
    `updated_at`: el gate mesura la LLEI, no quan es va desar.
    """
    from fhort.models_app.models import ModelGradingRule
    rows = []
    for r in (ModelGradingRule.objects.filter(model_id=model.pk)
              .select_related('pom').order_by('pk')):
        rows.append([
            r.pom.codi_client, r.garment, r.logica,
            _n(r.increment), _n(r.increment_base), _n(r.increment_break),
            r.talla_break_label, r.talla_break_pos,
            json.dumps(r.valors_step, sort_keys=True) if r.valors_step is not None else None,
            bool(r.actiu), r.origen, r.derivat_de_rule_set_id,
        ])
    return len(rows), _hash(rows)


# ─── BLOC A · paritat de GradedSpec ────────────────────────────────────────────────────────
def recalcula(model, verbose=False):
    """Reprodueix el bucle de `generate_graded_specs` SENSE escriure.

    Retorna {(pom_id, capa, instancia, garment, size_label): (valor, tipus)}.
    Espill fidel de `pom/services.py:229-311`; si aquell bucle canvia de forma, aquest ha de
    canviar amb ell — i que el gate ho canti és precisament la feina del gate.
    """
    from fhort.pom.services import (
        escala_del_model, _load_grading_rules_per_garment, _regla_de,
        _load_model_overrides, _poms_amb_override, _load_base_measurements, _apply_rule,
    )
    size_run, run_sistema, _pos, base_idx = escala_del_model(model)
    rules = _load_grading_rules_per_garment(model)
    overrides = _load_model_overrides(model.pk)
    nomes_override = _poms_amb_override(overrides)
    bases = _load_base_measurements(model.pk)

    if verbose:
        print(f"  size_run     {size_run}")
        print(f"  run_sistema  {run_sistema}   base_idx={base_idx}")
        print(f"  regles       {len(rules)}  ·  bases {len(bases)}  ·  overrides {len(overrides)}")

    warnings = []
    out = {}
    for (pom_id, capa, instancia, garment), base_val in bases.items():
        rule = _regla_de(rules, pom_id, garment)
        for size_label in size_run:
            i = _pos(size_label)
            steps = i - base_idx
            ov = overrides.get((pom_id, capa, instancia, garment, size_label))
            if ov is not None:
                val, gt = ov, 'EXCEPTION'
            elif (pom_id, capa, instancia, garment) in nomes_override and i == base_idx:
                val, gt = base_val, 'EXCEPTION'
            elif rule is None:
                continue
            else:
                val, gt = _apply_rule(rule, base_val, steps, i, base_idx,
                                      size_run=run_sistema, warnings=warnings)
            if val is None:
                continue
            out[(pom_id, capa, instancia, garment, size_label)] = (round(float(val), 2), gt)
    return out, warnings, (size_run, run_sistema, _pos, base_idx), rules, bases


def vigents(model):
    """Els `GradedSpec` actius de la GradingVersion VIGENT del SizeFitting de treball."""
    from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec
    sf = SizeFitting.objects.filter(model=model).order_by('numero').first()
    if sf is None:
        raise SystemExit("ATURADA · el model no té cap SizeFitting.")
    gv = GradingVersion.objects.filter(size_fitting=sf, is_active=True).first()
    if gv is None:
        raise SystemExit(f"ATURADA · el SizeFitting #{sf.pk} no té cap GradingVersion activa.")
    specs = {}
    for s in GradedSpec.objects.filter(grading_version=gv, is_active=True):
        specs[(s.pom_id, s.capa, s.instancia, s.garment, s.size_label)] = (
            round(float(s.graded_value_cm), 2), s.grading_type_applied)
    return sf, gv, specs


def bloc_a(model, calc, verbose):
    sf, gv, specs = vigents(model)
    print(f"  SizeFitting #{sf.pk} `{sf.codi}` · GradingVersion #{gv.pk} (v{gv.version_number}) vigent")

    claus = set(calc) | set(specs)
    ok = discrepa = absent = sobrer = 0
    detall = []
    for k in sorted(claus, key=lambda x: (x[0], x[3], x[1], x[2], x[4])):
        c, s = calc.get(k), specs.get(k)
        if c is None:
            sobrer += 1                       # spec a la taula que el motor no reprodueix
            detall.append(('SOBRER', k, None, s))
        elif s is None:
            absent += 1                       # el motor l'emetria i la taula no el té
            detall.append(('ABSENT', k, c, None))
        elif abs(c[0] - s[0]) > TOL:
            discrepa += 1
            detall.append(('DISCREPA', k, c, s))
        else:
            ok += 1

    print(f"\n  ▸ BLOC A · GradedSpec (camí `_apply_rule`)")
    print(f"    OK={ok}  DISCREPA={discrepa}  ABSENT={absent}  SOBRER={sobrer}"
          f"  |  specs a la taula={len(specs)}  |  files base={len({k[:4] for k in calc})}")
    if detall:
        print("    DETALL (fins a 40):")
        for tipus, k, c, s in detall[:40]:
            print(f"      {tipus:9} pom={k[0]} capa={k[1]!r} inst={k[2]!r} "
                  f"garment={k[3]!r} talla={k[4]:>4}  calc={c}  spec={s}")
    return (discrepa == 0 and absent == 0 and sobrer == 0), ok


# ─── BLOC B · paritat de la PRESA (propaga_ancoratges) ─────────────────────────────────────
def bloc_b(model, calc, geo, rules, bases, verbose):
    """La propagació per ANCORATGE ha de reproduir la corba del motor, des de QUALSEVOL talla.

    Mirall exacte del predicat de `fitting/views.py:705-707` (`propagar` de `PieceFittingLine`):
    STEP no propaga MAI; la resta propaga si és canònica o LINEAR. La geometria surt de
    `escala_del_model`, la MATEIXA font que fa servir el motor (llei S24b + FIX-1).

    Ancorar a CADA talla del run —no només a la base— és el que fa que aquest bloc mesuri la
    LLEI de l'aresta i no una coincidència: `increment_de_l_aresta` decideix el relleu contra la
    BASE, no contra l'ancoratge, i qualsevol canvi que ho trenqui surt aquí.
    """
    from fhort.pom.grading_utils import propaga_ancoratges
    from fhort.pom.services import _regla_de
    size_run, run_sistema, _pos, base_idx = geo
    base_label = model.base_size_label.strip()

    ok = dif = saltats = 0
    detall = []
    poms_propagats = set()
    for (pom_id, capa, instancia, garment), base_val in bases.items():
        rule = _regla_de(rules, pom_id, garment)
        if rule is None:
            saltats += 1
            continue
        logica = getattr(rule, 'logica', None)
        canonic = getattr(rule, 'increment_base', None) is not None
        if not ((logica != 'STEP') and (canonic or logica == 'LINEAR')):
            saltats += 1                       # la presa no propaga aquest règim: fora del bloc
            continue
        poms_propagats.add(pom_id)
        for ancora in size_run:                # ← des de CADA talla, no només la base
            esperat_ancora = calc.get((pom_id, capa, instancia, garment, ancora))
            if esperat_ancora is None:
                continue
            warnings = []
            teorics = propaga_ancoratges(
                rule, ancora, esperat_ancora[0], size_run, warnings=warnings,
                run_sistema=run_sistema, base_label=base_label)
            for lab in size_run:
                esperat = calc.get((pom_id, capa, instancia, garment, lab))
                obtingut = teorics.get(lab)
                if esperat is None:
                    continue
                if obtingut is None or abs(round(float(obtingut), 2) - esperat[0]) > TOL:
                    dif += 1
                    detall.append((pom_id, garment, ancora, lab, esperat[0], obtingut))
                else:
                    ok += 1

    print(f"\n  ▸ BLOC B · presa / ancoratges (camí `propaga_ancoratges` → `increment_de_l_aresta`)")
    print(f"    OK={ok}  DIVERGEIX={dif}  |  {len(poms_propagats)} POM propagables × "
          f"{len(size_run)} ancoratges × {len(size_run)} talles  |  files no propagables={saltats}")
    if detall:
        print("    DETALL (fins a 20):")
        for pom_id, g, anc, lab, esp, obt in detall[:20]:
            print(f"      pom={pom_id} garment={g!r}  ancora={anc:>4} → talla={lab:>4}  "
                  f"motor={esp}  presa={obt}")
    return dif == 0, ok


# ─── BLOC C · coherència dels DOS nodes del fallback ───────────────────────────────────────
class _ReglaSonda:
    """Regla en memòria, sense ORM i sense BD. NO es desa mai enlloc."""
    def __init__(self, **kw):
        self.pom_id = -1
        self.pom = None
        self.logica = 'LINEAR'
        self.increment = None
        self.increment_base = None
        self.increment_break = None
        self.talla_break_label = None
        self.valors_step = None
        for k, v in kw.items():
            setattr(self, k, v)


def bloc_c(geo):
    """🚨 EL BLOC QUE EXISTEIX PER AL FIX A.

    Sonda el cas que el corpus viu NO té i que és exactament el que el fix toca: una regla
    LINEAR amb `increment_base` a NULL i el camp llegat `increment` poblat.

    **No exigeix cap valor concret**, i és a posta: abans del fix els dos nodes cauen al llegat,
    després del fix tots dos l'han d'ignorar. El que aquest bloc exigeix, i que ha de valer en
    els dos règims, és que **els DOS nodes diguin el MATEIX** — que és la propietat que la
    diagnosi §1.3 va veure trencada i la que el fix ha de conservar per sempre.

    Compara, per a la mateixa regla i la mateixa geometria:
      ① `_apply_rule(...)`              → el que veurà l'Escalat
      ② `propaga_ancoratges(...)`       → el que veurà la presa
    """
    from fhort.pom.services import _apply_rule
    from fhort.pom.grading_utils import propaga_ancoratges
    size_run, run_sistema, _pos, base_idx = geo
    base_label = size_run[base_idx] if base_idx < len(size_run) else size_run[0]
    # `base_idx` ve en espai de SISTEMA; per a la sonda cal l'etiqueta, i la resolem igual que
    # el motor: la talla base és la que ocupa `base_idx` dins `run_sistema`.
    base_label = run_sistema[base_idx]
    BASE_VAL = 100.0

    casos = [
        ('LINEAR · ib=NULL · llegat 2.00 (EL CAS DEL FIX A)',
         _ReglaSonda(logica='LINEAR', increment=2.0)),
        ('LINEAR · ib=NULL · llegat NULL',
         _ReglaSonda(logica='LINEAR', increment=None)),
        ('LINEAR · ib=0.50 · llegat 2.00 (canònica: el llegat NO hi pinta res)',
         _ReglaSonda(logica='LINEAR', increment=2.0, increment_base=0.5)),
        ('LINEAR · ib=0.50 · brk=1.50 · break a la 4a del sistema',
         _ReglaSonda(logica='LINEAR', increment=9.9, increment_base=0.5,
                     increment_break=1.5, talla_break_label=run_sistema[base_idx + 1])),
    ]

    files = []
    coherents = incoherents = 0
    for nom, regla in casos:
        # ① Escalat
        esc = {}
        for lab in size_run:
            i = _pos(lab)
            v, _gt = _apply_rule(regla, BASE_VAL, i - base_idx, i, base_idx,
                                 size_run=run_sistema, warnings=[])
            esc[lab] = None if v is None else round(float(v), 2)
        # ② presa, ancorada a la BASE amb el valor base
        pre_raw = propaga_ancoratges(regla, base_label, BASE_VAL, size_run, warnings=[],
                                     run_sistema=run_sistema, base_label=base_label)
        pre = {lab: (None if pre_raw.get(lab) is None else round(float(pre_raw[lab]), 2))
               for lab in size_run}
        casa = all((esc[l] is None and pre[l] is None)
                   or (esc[l] is not None and pre[l] is not None and abs(esc[l] - pre[l]) <= TOL)
                   for l in size_run)
        coherents += 1 if casa else 0
        incoherents += 0 if casa else 1
        files.append((nom, esc, pre, casa))

    print(f"\n  ▸ BLOC C · coherència Escalat ↔ presa davant d'una regla incompleta (sonda pura)")
    for nom, esc, pre, casa in files:
        print(f"    {'✅' if casa else '❌'} {nom}")
        print(f"        escalat  " + " ".join(f"{l}={esc[l]}" for l in esc))
        print(f"        presa    " + " ".join(f"{l}={pre[l]}" for l in pre))
    print(f"    COHERENTS={coherents}  INCOHERENTS={incoherents}")
    return incoherents == 0, coherents


# ─── main ──────────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Banc de paritat del motor de graduació (read-only).")
    ap.add_argument('--model', type=int, default=1383)
    ap.add_argument('--tenant', default='fhort')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    with schema_context(a.tenant):
        from fhort.models_app.models import Model
        model = Model.objects.select_related('size_system', 'grading_rule_set').get(pk=a.model)
        print(f"BANC DE PARITAT · model pk={model.pk} `{model.codi_intern}` · tenant `{a.tenant}`")
        print(f"  sistema {model.size_system.codi} · run {model.size_run_model} "
              f"· base {model.base_size_label}")

        calc, warnings, geo, rules, bases = recalcula(model, a.verbose)
        if warnings:
            print(f"  warnings del motor: {len(warnings)}")
            for w in warnings[:10]:
                print("    · " + w)

        okA, nA = bloc_a(model, calc, a.verbose)
        okB, nB = bloc_b(model, calc, geo, rules, bases, a.verbose)
        okC, nC = bloc_c(geo)

        n_joc, h_joc = hash_del_joc(model.grading_rule_set)
        n_res, h_res = hash_de_les_residents(model)
        joc_ok = (h_joc == HASH_JOC_REFERENCIA)
        print()
        print(f"  HASH JOC        {h_joc}")
        print(f"                  ({n_joc} regles · `{model.grading_rule_set.codi_sistema}` "
              f"pk={model.grading_rule_set_id}) — "
              f"{'IDÈNTIC al de referència' if joc_ok else '⚠ DIVERGENT de ' + HASH_JOC_REFERENCIA}")
        print(f"  HASH RESIDENTS  {h_res}   ({n_res} ModelGradingRule)")

        tot = okA and okB and okC and joc_ok
        print()
        print(f"  VEREDICTE: {'✅ PARITAT' if tot else '❌ TRENCADA'}"
              f"  ·  A={'✔' if okA else '✘'}({nA})  B={'✔' if okB else '✘'}({nB})"
              f"  C={'✔' if okC else '✘'}({nC})  ·  {'joc intacte' if joc_ok else 'JOC MOGUT'}")
        return 0 if tot else 1


if __name__ == '__main__':
    sys.exit(main())
