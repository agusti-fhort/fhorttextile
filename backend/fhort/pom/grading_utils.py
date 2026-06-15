"""fhort/pom/grading_utils.py — utilitats pures de detecció de grading.

Funcions sense I/O ni persistència, compartides entre el wizard de Size Map
(size_map_views.py) i, més endavant, el camí d'import de fitxa. Aïllar-les aquí
evita importar un mòdul de *views* des d'un altre (i els cicles que això comporta).
"""


def _norm(label) -> str:
    """Normalitza una etiqueta per comparar (upper + strip), com fa el run."""
    return str(label or '').strip().upper()


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
            vals = list(deltas.values())
            if all(d == 0 for d in vals):
                logica, increment = 'FIXED', 0.0
            elif all(d == vals[0] for d in vals):
                logica, increment = 'LINEAR', vals[0]
            else:
                logica, valors_step = 'STEP', deltas

    return {
        'logica': logica,
        'increment': increment,
        'valors_step': valors_step,
        'warning': warning,
    }


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

    def _step_equal(a, b):
        # valors_step (dict {etiqueta: delta}) o None. Igualtat numèrica amb tolerància sobre
        # claus normalitzades (mateix criteri que el motor: _norm = str(x).strip().upper()).
        if not a and not b:
            return True
        if bool(a) != bool(b):
            return False
        na = {_norm(k): float(v) for k, v in a.items()}
        nb = {_norm(k): float(v) for k, v in b.items()}
        if set(na) != set(nb):
            return False
        return all(abs(na[k] - nb[k]) < 0.001 for k in na)

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
            GradingRule.objects.create(
                rule_set=new_rule_set,
                pom=pm,
                talla_base=base_def,
                logica=res['logica'],
                increment=res.get('increment') or 0,
                valors_step=res.get('valors_step'),
                valor_base=valor_base,
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
