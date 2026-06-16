"""fhort/pom/grading_utils.py — utilitats pures de detecció de grading.

Funcions sense I/O ni persistència, compartides entre el wizard de Size Map
(size_map_views.py) i, més endavant, el camí d'import de fitxa. Aïllar-les aquí
evita importar un mòdul de *views* des d'un altre (i els cicles que això comporta).
"""


def _norm(label) -> str:
    """Normalitza una etiqueta per comparar (upper + strip), com fa el run."""
    return str(label or '').strip().upper()


def _step_equal(a, b):
    """Igualtat numèrica de valors_step (dict {etiqueta: delta} o None) amb tolerància
    0.001 sobre claus normalitzades (_norm). Funció de mòdul (PG-3): la comparteixen
    l'anti-proliferació 1D de derive_grading_rule_set i grading_rules_match."""
    if not a and not b:
        return True
    if bool(a) != bool(b):
        return False
    na = {_norm(k): float(v) for k, v in a.items()}
    nb = {_norm(k): float(v) for k, v in b.items()}
    if set(na) != set(nb):
        return False
    return all(abs(na[k] - nb[k]) < 0.001 for k in na)


def grading_rules_match(model_rules, canonical_rules):
    """Compara regles residents (ModelGradingRule) vs regles d'un canònic (GradingRule).

    Compara la FORMA del grading, que és INVARIANT a la talla base: el motor (_apply_rule)
    ancora a model.base_size_label, no a rule.talla_base (mer metadata del seed). Per això NO
    es compara la talla base — fer-ho compararia l'ancoratge, no el grading, i emmascararia
    divergències reals quan el model i el canònic tenen bases diferents (cas normal: seeds
    ancorats a M, models a la seva pròpia base).

    4 dimensions:
      1. mateix conjunt de pom_id (estricte)
      2. logica (literal)
      3. increment (float(x or 0), tol 0.001)
      4. valors_step (via _step_equal de mòdul)

    NO compara increment_base/break directament (els canònics es deriven de logica+increment+
    valors_step). Retorna (match: bool, divergencies: list[dict]) amb el primer eix divergent
    per pom, {'pom_codi', 'detall'}, per construir l'advertència.
    """
    m_by = {r.pom_id: r for r in model_rules}
    c_by = {r.pom_id: r for r in canonical_rules}
    divs = []

    def _codi(rule):
        return getattr(getattr(rule, 'pom', None), 'codi_client', None) or getattr(rule, 'pom_id', '?')

    # (1) mateix conjunt de pom_id
    nomes_model = set(m_by) - set(c_by)
    nomes_canonic = set(c_by) - set(m_by)
    for pid in nomes_model:
        divs.append({'pom_codi': _codi(m_by[pid]), 'detall': 'POM al model però no al canònic'})
    for pid in nomes_canonic:
        divs.append({'pom_codi': _codi(c_by[pid]), 'detall': 'POM al canònic però no al model'})

    for pid in set(m_by) & set(c_by):
        mr, cr = m_by[pid], c_by[pid]
        # (2) logica
        if (mr.logica or '') != (cr.logica or ''):
            divs.append({'pom_codi': _codi(mr), 'detall': f'lògica {mr.logica} ≠ {cr.logica}'})
            continue
        # (3) increment
        if abs(float(mr.increment or 0) - float(cr.increment or 0)) >= 0.001:
            divs.append({'pom_codi': _codi(mr), 'detall': f'increment {mr.increment} ≠ {cr.increment}'})
            continue
        # (4) valors_step
        if not _step_equal(mr.valors_step, cr.valors_step):
            divs.append({'pom_codi': _codi(mr), 'detall': 'valors_step difereixen'})
            continue

    return (len(divs) == 0, divs)


def cerca_canonic_equivalent(model):
    """Busca el GradingRuleSet canònic (is_system_default=True) que encaixa amb la
    classificació del model. None si no n'hi ha cap o si falta la classificació mínima.

    Font de la classificació: els CAMPS PROPIS del model (no model.grading_rule_set, que
    seria circular en Cas A). target/construction/fit_type són codis (string) al model →
    es resolen a FK via codi__iexact, mateix patró que derive_grading_rule_set.

    DEUTE (PG-3): el match de target va per la M2M `targets` (autoritativa), mentre que
    l'anti-proliferació 1D de derive_grading_rule_set encara filtra pel FK legacy `target`.
    Si un canònic té el target a la M2M però no al FK (o viceversa) divergiran. No es toca
    el 1D avui; queda anotat com a deute fins que el FK `target` es retiri.
    """
    from fhort.pom.models import Target, ConstructionType, FitType, GradingRuleSet
    ss = model.size_system        # FK directe
    tgt = Target.objects.filter(codi__iexact=model.target).first() if model.target else None
    constr = ConstructionType.objects.filter(codi__iexact=model.construction).first() if model.construction else None
    fit = FitType.objects.filter(codi__iexact=model.fit_type).first() if model.fit_type else None
    if not (ss and tgt):          # classificació mínima per cercar
        return None
    # Eixos de match (regla de negoci): size_system + target + construction + fit_type. NO
    # garment_group: els seeds canònics ISO tenen garment_group=NULL, mentre que els models
    # solen portar-lo poblat → incloure'l faria que CAP model encaixés (fals "grading
    # específic" sistemàtic). El 1D sí filtra per garment_group perquè compara contra rulesets
    # CUSTOM derivats del propi model (que sí el porten); aquí comparem contra els seeds.
    # construction/fit_type None → WHERE ..._id IS NULL: un canònic sense construction/fit
    # encaixa amb un model sense construction/fit (intencional, no descuit).
    return GradingRuleSet.objects.filter(
        is_system_default=True,
        size_system=ss,
        construction=constr, fit_type=fit,
        targets=tgt,              # M2M (no el FK legacy `target`) — veure DEUTE al docstring
    ).distinct().first()


def detect_grading(valors_per_talla, run_ordenat, base_label) -> dict:
    """Detecta la lògica de grading d'un POM a partir dels seus valors per talla.

    Pur: cap I/O, cap persistència. Per cada salt calcula el delta respecte el veí
    cap a la base (format C: delta positiu en sentit de creixement cap enfora) i
    classifica LINEAR / FIXED / STEP.

    Args:
        valors_per_talla: dict {etiqueta: valor} d'aquest POM (claus en cas original).
        run_ordenat: list d'etiquetes del run, ja ordenada (cas original).
        base_label: etiqueta de la talla base.

    Returns:
        dict amb claus {'logica', 'increment', 'valors_step', 'warning'}:
          - logica: 'LINEAR' | 'FIXED' | 'STEP' | None
          - increment: float | None (per LINEAR/FIXED)
          - valors_step: dict {etiqueta: delta} | None (per STEP, claus = etiqueta real)
          - warning: str (buit si tot ha anat bé)
    """
    base_norm = _norm(base_label)
    run_norm = [_norm(x) for x in run_ordenat]
    base_idx = run_norm.index(base_norm) if base_norm in run_norm else None
    valors = {_norm(k): v for k, v in (valors_per_talla or {}).items()}

    logica = None
    increment = None
    valors_step = None
    warning = ''

    if base_idx is None:
        warning = f"Talla base '{base_label}' no és al run de talles."
    else:
        deltas = {}
        for j, lab in enumerate(run_norm):
            if j == base_idx:
                continue
            if j > base_idx:
                inner = run_norm[j - 1]
                v_out, v_in = valors.get(lab), valors.get(inner)
                sign = 1.0
            else:
                inner = run_norm[j + 1]
                v_out, v_in = valors.get(lab), valors.get(inner)
                sign = -1.0
            if v_out is None or v_in is None:
                warning = (warning + ' ' if warning else '') + \
                    f"Falta valor per calcular el delta de la talla {run_ordenat[j]}."
                continue
            # format C: delta positiu en sentit de creixement cap enfora.
            deltas[run_ordenat[j]] = round(sign * (float(v_out) - float(v_in)), 2)

        if deltas:
            # deltes en ordre de run (dict construït iterant run_norm). Comptem punts de canvi
            # de pas (transicions delta[i] != delta[i-1], tol 0.001): 0 o 1 break = LINEAR
            # (delta uniforme, o un sol esglaó com el CHEST — fórmula viva amb base+break);
            # ≥2 breaks (multi-esglaó o valors sense progressió) = STEP.
            vals = list(deltas.values())
            nb = 0
            prev = vals[0]
            for d in vals[1:]:
                if abs(d - prev) > 0.001:
                    nb += 1
                    prev = d
            if all(d == 0 for d in vals):
                logica, increment = 'FIXED', 0.0
            elif nb == 0:
                logica, increment = 'LINEAR', vals[0]
            elif nb == 1:
                # LINEAR amb UN break: increment = delta base; valors_step poblat com a origen
                # d'on derive_break_fields treu base+break.
                logica, increment, valors_step = 'LINEAR', vals[0], deltas
            else:
                logica, valors_step = 'STEP', deltas

    return {
        'logica': logica,
        'increment': increment,
        'valors_step': valors_step,
        'warning': warning,
    }


def derive_break_fields(logica, increment, valors_step, run_ordenat):
    """Forma canònica PEÇA A → (increment_base, increment_break, talla_break_label, talla_break_pos).

    Break AGNÒSTIC a la lògica: sempre que hi hagi `valors_step` amb claus que són etiquetes
    reals del run, deriva primer delta del run = base; primera etiqueta on el delta canvia =
    break. Funciona igual per LINEAR-amb-break (CHEST) i per STEP multi-break.
    Sense `valors_step` derivable → base = increment (LINEAR/FIXED pur), sense break.

    Blindatge above_xl: el filtre `l in run_ordenat` exclou la clau sintètica 'above_xl' (no és
    etiqueta del run) PER CONSTRUCCIÓ → mai break espuri. La forma ISO above_xl la resol la
    branca (b) inline del backfill, que NO passa per aquí.
    """
    ib = ibrk = tlabel = tpos = None
    seq = ([(l, valors_step[l]) for l in run_ordenat
            if l in valors_step and valors_step[l] is not None]
           if isinstance(valors_step, dict) else [])
    if seq:
        ib = float(seq[0][1])
        for l, d in seq:
            if abs(float(d) - ib) > 0.001:
                tlabel, ibrk = l, float(d)
                break
        tpos = run_ordenat.index(tlabel) if (tlabel and tlabel in run_ordenat) else None
    elif increment is not None:
        ib = float(increment or 0)
    return ib, ibrk, tlabel, tpos


def derive_grading_rule_set(*, size_run_model, base_size, valors, confirmed_pom_ids,
                            size_system, garment_group, target_codi, construction_codi,
                            fit_type_codi, nom, nom_sufix_unic, avisos):
    """Deriva (o reutilitza) el GradingRuleSet d'una graduació a partir dels valors per talla.

    Pura de model: rep run/base/valors + la classificació (per CODIS) + el nom, i RETORNA el
    GradingRuleSet (nou o reutilitzat) o None si no s'ha pogut derivar. NO toca cap model, NO
    fa re-apuntat, NO desa cap sessió. Acumula la traça a la llista `avisos` que rep.

    Extreta del bloc 3b del W5 (1B+1D) perquè el camí d'import de fitxa (W5) i la Size Library
    comparteixin EXACTAMENT la mateixa derivació. Anti-proliferació (1D): si ja existeix un
    ruleset no-system_default per la mateixa combinació amb graduació IDÈNTICA, es reutilitza.

    - size_system / garment_group: instàncies (o None) — entren a la combinació tal com resolen.
    - target_codi / construction_codi / fit_type_codi: CODIS (string); resolució a FK via
      codi__iexact aquí dins (None si no resol).
    - nom: nom primari del ruleset; nom_sufix_unic: sufix únic i determinista que s'hi afegeix
      NOMÉS si `nom` ja col·lisiona exacte (lògica de 1D).
    - La creació de ruleset+regles va dins un transaction.atomic() intern (savepoint): si peta,
      no queda cap ruleset orfe parcial; l'excepció propaga al cridador.

    DEUTE 1C-3: els avisos diuen "del model"; quan la Library sigui el segon cridador (sense
    model) cal fer-los neutres model/catàleg. A 1C-1 es mantenen idèntics (refactor pur).
    """
    from django.db import transaction
    from fhort.pom.models import (
        GradingRuleSet, GradingRule, SizeDefinition,
        Target, ConstructionType, FitType, POMMaster,
    )

    # detect_grading vol run_ordenat = LLISTA d'etiquetes (itera/indexa posicions), no un
    # string. Mateixa llista que el motor (services.py:156) → round-trip simètric dels deltes.
    run_ordenat = [
        s.strip() for s in (size_run_model or '').replace(';', '·').split('·')
        if s.strip()
    ]
    base_def = SizeDefinition.objects.filter(
        size_system=size_system, etiqueta__iexact=base_size,
    ).first() if (getattr(size_system, 'id', None) and base_size) else None

    if not run_ordenat or not base_size:
        avisos.append(
            "Grading no derivat: manca run o talla base al model; es manté el ruleset previ.")
        return None
    if base_def is None:
        avisos.append(
            f"Grading no derivat: talla base '{base_size}' no trobada al sistema de "
            f"talles del model; es manté el ruleset previ.")
        return None

    # Unicitat per la FK `pom` (no per pid): dos valors poden resoldre al mateix POMMaster
    # (p.ex. TOTAL LENGTH duplicat). dict.fromkeys conserva el primer-vist de forma
    # determinista → una sola regla per pom. detect_grading aïllat per POM (degrada, no peta).
    pom_specs = []
    for pid in dict.fromkeys(confirmed_pom_ids):
        pm = POMMaster.objects.filter(id=pid).first()
        if not pm:
            continue
        try:
            res = detect_grading(valors.get(pid) or {}, run_ordenat, base_size)
        except Exception as e:
            avisos.append(f"POM {pm.codi_client}: detecció de grading fallida ({e}).")
            continue
        if res.get('warning'):
            avisos.append(f"POM {pm.codi_client}: {res['warning']}")
        if not res.get('logica'):
            avisos.append(f"POM {pm.codi_client}: grading no detectat; regla omesa.")
            continue
        bv = valors.get(pid, {}).get(base_size)
        try:
            valor_base = float(bv) if bv not in (None, '') else 0
        except (TypeError, ValueError):
            valor_base = 0
        pom_specs.append((pm, res, valor_base))

    if not pom_specs:
        avisos.append(
            "Cap regla de grading derivada dels valors; es manté el ruleset previ del model.")
        return None

    with transaction.atomic():
        rs_target = Target.objects.filter(codi__iexact=target_codi).first() if target_codi else None
        rs_constr = ConstructionType.objects.filter(codi__iexact=construction_codi).first() if construction_codi else None
        rs_fit = FitType.objects.filter(codi__iexact=fit_type_codi).first() if fit_type_codi else None

        spec_by_pom = {pm.id: res for pm, res, _vb in pom_specs}
        candidat = None
        candidats = GradingRuleSet.objects.filter(
            is_system_default=False,
            size_system=size_system,
            garment_group=garment_group,
            target=rs_target,
            construction=rs_constr,
            fit_type=rs_fit,
        )
        for c in candidats:
            regles_c = list(c.regles.all())  # files reals del candidat
            # (1) MATEIX conjunt de pom_id (igualtat estricta, no subconjunt).
            if {r.pom_id for r in regles_c} != set(spec_by_pom):
                continue
            # (2)+(3) per cada pom: mateixa talla_base, logica, increment i valors_step.
            igual = True
            for r in regles_c:
                res_s = spec_by_pom[r.pom_id]
                if r.talla_base_id != base_def.id:
                    igual = False
                    break
                if (r.logica or '') != (res_s.get('logica') or ''):
                    igual = False
                    break
                if abs(float(r.increment or 0) - float(res_s.get('increment') or 0)) >= 0.001:
                    igual = False
                    break
                if not _step_equal(r.valors_step, res_s.get('valors_step')):
                    igual = False
                    break
            if igual:
                candidat = c
                break

        if candidat is not None:
            # REUTILITZAR: no es crea cap regla; el cridador re-apunta el model.
            avisos.append(
                f"Grading reutilitzat: ruleset existent #{candidat.id} '{candidat.nom}' "
                f"(graduació idèntica per la combinació; no s'ha creat cap ruleset nou).")
            return candidat

        # CREAR NOU. Nom desambiguat: si `nom` ja col·lisiona exacte (reimport del mateix model
        # amb graduació diferent), hi afegim el sufix únic determinista (1D).
        nom_final = nom
        if GradingRuleSet.objects.filter(nom=nom_final).exists():
            nom_final = f"{nom} · {nom_sufix_unic}"
        new_rule_set = GradingRuleSet.objects.create(
            nom=nom_final,
            size_system=size_system,
            garment_group=garment_group,
            target=rs_target,
            construction=rs_constr,
            fit_type=rs_fit,
            is_system_default=False,
            actiu=True,
        )
        if rs_target:
            new_rule_set.targets.add(rs_target)
        for pm, res, valor_base in pom_specs:
            # Peça A — omplir la forma canònica a més de valors_step (origen). STEP → derivar
            # increment_base/talla_break_label/increment_break del run; LINEAR → increment uniforme.
            ib, ibrk, tlabel, tpos = derive_break_fields(
                res['logica'], res.get('increment'), res.get('valors_step'), run_ordenat)
            GradingRule.objects.create(
                rule_set=new_rule_set,
                pom=pm,
                talla_base=base_def,
                logica=res['logica'],
                increment=res.get('increment') or 0,
                valors_step=res.get('valors_step'),
                valor_base=valor_base,
                increment_base=ib,
                increment_break=ibrk,
                talla_break_label=tlabel,
                talla_break_pos=tpos,
                actiu=True,
            )
        avisos.append(
            f"Grading nou: creat ruleset #{new_rule_set.id} (graduació específica "
            f"d'aquest model; cap candidat existent coincidia).")
        return new_rule_set


def suggest_valors_mode(valors, base_label, run_ordenat):
    """Suggereix si els valors de la taula són 'absoluts' o 'deltes' (increments).

    SUGGERIMENT PROVISIONAL, afinable amb fitxes reals de la Montse: només pre-selecciona el
    toggle (1C-2b), MAI decideix res. Pura, sense efectes. Davant dubte → 'absoluts' (= avui).

    Principi: la distinció real és la FORMA, no la magnitud absoluta. Senyal PRIMARI = MONOTONIA:
    els valors absoluts creixen talla a talla (chest, amplades, llargades… pugen amb la talla);
    els deltes són nivells plans/quasi plans (no acumulats). Senyal SECUNDARI de desempat =
    magnitud RELATIVA al base del mateix POM (delta ≪ base), MAI un llindar fix en cm. Decideix
    sobre l'AGREGAT de POMs; els POMs constants (p.ex. E.8 = 2,2,2…) són NEUTRES (ni creixent ni
    delta) i s'exclouen de l'agregat. Els llindars (0.5 creixents, 0.15 ratio) són PROVISIONALS.

    CONTRACTE: el mode deltes assumeix base ABSOLUTA + increments a la resta de talles (la cel·la
    base porta el valor absolut, p.ex. '6':42.4, no un delta). Deltes PURS sense base absoluta NO
    es contemplen: l'heurística cau a 'absoluts' i la conversió degrada amb gràcia (sense àncora,
    retorna el pom intacte). Si algun dia apareix una fitxa amb deltes purs sense base, és una
    peça NOVA (declarar la base a part), no un cas que aquest codi cobreixi silenciosament.

    valors: {pid:{talla:valor}} (claus en cas original). Retorna 'absoluts' | 'deltes'.
    """
    base_norm = _norm(base_label)
    run_norm = [_norm(x) for x in run_ordenat]
    TOL = 1e-9

    evaluables = 0   # POMs amb forma avaluable (no constants)
    creixents = 0    # POMs que pugen talla a talla en la majoria de trams
    ratios = []      # magnitud relativa (mediana cel·les-no-base / base) per POM amb base

    for pom_vals in (valors or {}).values():
        vnorm = {_norm(k): v for k, v in (pom_vals or {}).items()}
        seq = []
        for lab in run_norm:
            v = vnorm.get(lab)
            if v in (None, ''):
                continue
            try:
                seq.append(float(v))
            except (TypeError, ValueError):
                continue
        if len(seq) >= 3:
            inc = sum(1 for i in range(len(seq) - 1) if seq[i + 1] > seq[i] + TOL)
            dec = sum(1 for i in range(len(seq) - 1) if seq[i + 1] < seq[i] - TOL)
            total = len(seq) - 1
            if inc == 0 and dec == 0:
                pass  # constant → neutre, s'exclou de l'agregat
            else:
                evaluables += 1
                # creixent-fort: puja en la majoria (>=meitat) dels trams del run.
                if inc >= max(1, (total + 1) // 2):
                    creixents += 1

        # Desempat secundari: magnitud RELATIVA al base del mateix POM.
        bv = vnorm.get(base_norm)
        try:
            B = abs(float(bv)) if bv not in (None, '') else None
        except (TypeError, ValueError):
            B = None
        if B and B > TOL:
            no_base = []
            for lab, v in vnorm.items():
                if lab == base_norm or v in (None, ''):
                    continue
                try:
                    no_base.append(abs(float(v)))
                except (TypeError, ValueError):
                    continue
            if no_base:
                no_base.sort()
                k = len(no_base)
                med = no_base[k // 2] if k % 2 else (no_base[k // 2 - 1] + no_base[k // 2]) / 2.0
                ratios.append(med / B)

    # PRIMARI (monotonia): si la majoria de POMs avaluables creixen talla a talla → absoluts.
    if evaluables > 0 and (creixents / evaluables) > 0.5:
        return 'absoluts'

    # SECUNDARI (magnitud relativa): cel·les no-base ≪ base (p.ex. deltes ~1-2cm sobre base ~40
    # → ratio ~0.03) → deltes. Llindar 0.15 provisional, relatiu al base, mai absolut en cm.
    if ratios:
        ratios.sort()
        k = len(ratios)
        med_ratio = ratios[k // 2] if k % 2 else (ratios[k // 2 - 1] + ratios[k // 2]) / 2.0
        if med_ratio < 0.15:
            return 'deltes'

    # Default segur: sense senyal clar de delta → absoluts (= comportament d'avui).
    return 'absoluts'


def deltes_a_absoluts(valors, base_label, run_ordenat):
    """Converteix valors expressats com a INCREMENTS (deltes consecutius, format C) a ABSOLUTS.

    Inversa exacta del que detect_grading deriva: la cel·la base es manté (és l'absolut base);
    cap a la dreta de la base = base + suma acumulada dels deltes consecutius; cap a l'esquerra
    = base − suma acumulada. Mateixa convenció d'ordre/posició que detect_grading → cal el
    MATEIX run_ordenat (model.size_run_model).

    CONTRACTE: el mode deltes assumeix base ABSOLUTA + increments a la resta de talles (la cel·la
    base porta el valor absolut, p.ex. '6':42.4, no un delta). Deltes PURS sense base absoluta NO
    es contemplen: sense àncora (base absent del run o sense valor) la conversió degrada amb
    gràcia i retorna el pom intacte. Si algun dia apareix una fitxa amb deltes purs sense base,
    és una peça NOVA (declarar la base a part), no un cas que aquest codi cobreixi silenciosament.

    valors: {pid:{talla:valor}} (claus en cas original). Retorna un dict NOU amb les MATEIXES
    claus originals per pom, amb els valors convertits a absoluts. Robust: si manca la base o un
    delta intermedi, degrada amb gràcia (deixa les cel·les no-calculables amb el valor original;
    no peta). NO toca detect_grading.
    """
    base_norm = _norm(base_label)
    run_norm = [_norm(x) for x in run_ordenat]
    if base_norm not in run_norm:
        return valors  # sense base al run no es pot ancorar → es retorna tal qual
    base_idx = run_norm.index(base_norm)

    out = {}
    for pid, pom_vals in (valors or {}).items():
        vnorm = {_norm(k): v for k, v in (pom_vals or {}).items()}
        try:
            base_v = vnorm.get(base_norm)
            B = float(base_v) if base_v not in (None, '') else None
        except (TypeError, ValueError):
            B = None
        if B is None:
            out[pid] = dict(pom_vals)  # sense valor base no es pot convertir; intacte
            continue

        abs_by_norm = {base_norm: round(B, 2)}
        # Cap a la dreta de la base: suma acumulada dels deltes consecutius.
        acc = B
        for j in range(base_idx + 1, len(run_norm)):
            d = vnorm.get(run_norm[j])
            try:
                acc = acc + float(d) if d not in (None, '') else None
            except (TypeError, ValueError):
                acc = None
            if acc is None:
                break  # manca un delta → atura aquesta direcció (degrada)
            abs_by_norm[run_norm[j]] = round(acc, 2)
        # Cap a l'esquerra de la base: resta acumulada.
        acc = B
        for j in range(base_idx - 1, -1, -1):
            d = vnorm.get(run_norm[j])
            try:
                acc = acc - float(d) if d not in (None, '') else None
            except (TypeError, ValueError):
                acc = None
            if acc is None:
                break
            abs_by_norm[run_norm[j]] = round(acc, 2)

        # Reconstruir preservant les claus ORIGINALS d'entrada; cel·les no-calculables → valor
        # original (degradació amb gràcia, mai KeyError).
        out[pid] = {k: abs_by_norm.get(_norm(k), v) for k, v in pom_vals.items()}
    return out
