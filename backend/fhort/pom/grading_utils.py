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
