"""fhort/pom/grading_utils.py — utilitats pures de detecció de grading.

Funcions sense I/O ni persistència, compartides entre el wizard de Size Map
(size_map_views.py) i, més endavant, el camí d'import de fitxa. Aïllar-les aquí
evita importar un mòdul de *views* des d'un altre (i els cicles que això comporta).
"""
import logging

logger = logging.getLogger(__name__)


def _norm(label) -> str:
    """Normalitza una etiqueta per comparar (upper + strip), com fa el run."""
    return str(label or '').strip().upper()


def _step_equal(a, b):
    """Igualtat numèrica de valors_step (dict {etiqueta: delta} o None) amb tolerància
    0.001 sobre claus normalitzades (_norm). Funció de mòdul (PG-3): la comparteix
    `grading_rules_match`."""
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
    es resolen a FK via codi__iexact.

    P7 (2026-07-22): el DEUTE (PG-3) que hi havia aquí queda TANCAT — el match de target va
    per la M2M `targets`, que és ara la font única (el FK legacy `target` s'ha retirat).
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


def cerca_client_equivalent(customer, size_system, exclude_ids=()):
    """Rulesets de CLIENT existents per al mateix customer + size_system (candidats a reutilitzar).

    Avís-i-confirma TOU (Peça R): NO fusiona ni reutilitza automàticament; retorna els rulesets
    actius, `is_system_default=False`, del mateix client i sistema de talles, perquè el camí
    d'import els OFEREIXI al tècnic abans de derivar-ne un de nou (evita la duplicació 115/116).

    Trigger de "similar" = customer + size_system (decisió Agus). NO es filtra per eixos ni per
    solapament de POM: precisament els casos on els eixos difereixen (un ruleset amb
    construction/fit NULL i un altre amb WOVEN/REGULAR) són els que una dedup estricta per
    eixos no pot casar. Buit si falta customer o size_system.
    """
    from fhort.pom.models import GradingRuleSet
    if not (customer and size_system):
        return GradingRuleSet.objects.none()
    return (GradingRuleSet.objects
            .filter(is_system_default=False, actiu=True,
                    customer=customer, size_system=size_system)
            .exclude(id__in=[i for i in exclude_ids if i])
            .order_by('id'))


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


def run_del_document(values_per_fila, run_sistema):
    """REFERENT DE DERIVACIÓ (llei S24, 2026-07-22): el run del DOCUMENT, no el del sistema.

    Font única del `run` que alimenta ALHORA (a) el guard d'integritat («cap regla d'una
    taula incompleta», 2026-07-08), (b) `detect_grading` i (c) `derive_break_fields`. Que
    els tres comparteixin referent és el que impedeix les dues degradacions conegudes:
      - referent MÉS AMPLE que el document (run del SizeSystem) → files marcades incompletes
        i bloqueig fals (cas Meredith: doc XXS-L sobre un sistema de 8 talles);
      - referent MÉS ESTRET que el document (run del model) → deltes col·lapsats i break
        FABRICAT (bug model 166: S→L salta la M absent = 2 passos = fals «×2»).

    Pur: cap I/O, cap persistència. El `run_sistema` el llegeix el cridador (ja té les
    `SizeDefinition` a mà); aquí només s'ordena i es valida contra ell.

    Args:
        values_per_fila: iterable de dicts {etiqueta_document: valor} (una entrada per fila
            del document). Les claus amb valor None compten com a etiqueta present: la
            columna hi és, el que falta és el valor (això ho detecta el guard, no aquí).
        run_sistema: llista ORDENADA d'etiquetes del sistema de talles (cas del tenant).
            Buida = no hi ha sistema contra el qual validar (camí CREAR): s'accepta el
            document tal com ve, en ordre de primera aparició.

    Returns:
        (doc_run, etiquetes_desconegudes):
          - doc_run: etiquetes del TENANT presents al document, ordenades pel `run_sistema`
            (sense duplicats). És el referent.
          - etiquetes_desconegudes: etiquetes del document sense equivalència al sistema
            (check (d)). No és una talla que falti: és una talla que el sistema no coneix
            → error real, mai silenci.

    El pont de comparació és `canonical_size_label` (pont ÚNIC, llei 2026-07-08): salva
    XXL↔2XL, que `_norm` (upper+strip) no cobreix. Mai es persisteix la forma canònica:
    `doc_run` torna SEMPRE l'etiqueta del tenant.
    """
    from fhort.pom.size_labels import canonical_size_label

    # Etiquetes del document, en ordre de primera aparició (fallback sense sistema).
    doc_labels = []
    for fila in (values_per_fila or []):
        for k in (fila or {}).keys():
            if k not in doc_labels:
                doc_labels.append(k)

    if not run_sistema:
        return doc_labels, []

    canon_to_tenant = {canonical_size_label(e): e for e in run_sistema}
    ordre = {e: i for i, e in enumerate(run_sistema)}

    presents, desconegudes = set(), []
    for lbl in doc_labels:
        tenant = canon_to_tenant.get(canonical_size_label(lbl))
        if tenant is None:
            desconegudes.append(lbl)
        else:
            presents.add(tenant)

    doc_run = sorted(presents, key=lambda e: ordre[e])
    return doc_run, desconegudes


def run_sistema_de(size_system):
    """`SizeSystem` (o llista d'etiquetes, o None) → llista d'etiquetes ORDENADA per
    `SizeDefinition.ordre`.

    Adaptador únic perquè `run_del_model` es pugui cridar de les dues maneres: amb un
    `SizeSystem` (com fan les vistes, que tenen el model a mà) o amb una llista ja llegida
    (com fa `run_del_document`, i com fan els tests, que així no toquen BD). Una llista
    entra i surt intacta: qui la passa ja assumeix la responsabilitat de l'ordre.
    """
    if size_system is None:
        return []
    if isinstance(size_system, (list, tuple)):
        return [str(e).strip() for e in size_system if str(e).strip()]
    return [t.etiqueta.strip()
            for t in size_system.talles.order_by('ordre')
            if (t.etiqueta or '').strip()]


def run_del_model(etiquetes, size_system):
    """REFERENT D'ESCALA (llei S24b, 2026-07-22): l'ordre del run del MODEL el mana el SISTEMA.

    Germà de `run_del_document`, i el mateix principi aplicat a l'altre eix: allà el referent
    de DERIVACIÓ de regles és el run del document; aquí el referent d'ORDRE del run del model
    és la seqüència del `SizeSystem`. El run del model és un SUBCONJUNT — potencialment NO
    CONTIGU (un client que no fabrica la M) — que mai redefineix ni l'ordre ni la distància.

    Existeix perquè `Model.size_run_model` no tenia cap porta d'escriptura que ordenés: les 9
    vies del cens desaven l'ordre d'entrada (clic de l'usuari al wizard, ordre del document,
    ordre de la cel·la d'Excel). Amb el motor comptant els passos per POSICIÓ dins la llista,
    un run apendat com `XS·S·L·XXS·M` feia que la XXS gradués amb el SIGNE INVERTIT (cas real
    del model 166; vegeu `DIAGNOSI_ORDRE_RUN_MODEL_2026-07-22.md`).

    Pur en el sentit que importa: cap escriptura, cap efecte, resultat determinista. Si es
    passa una llista d'etiquetes com a `size_system` no toca BD en absolut (és així com el
    proven els tests); si es passa un `SizeSystem`, `run_sistema_de` en llegeix les talles.

    Args:
        etiquetes: iterable d'etiquetes del run del model, en qualsevol ordre i amb possibles
            duplicats (el toggle del wizard en pot produir). `None`/buides s'ignoren.
        size_system: `SizeSystem`, llista d'etiquetes ja ordenada, o None. **None (o sistema
            sense talles) = no hi ha res contra què ordenar**: es retornen les etiquetes tal
            com vénen, deduplicades, i cap desconeguda. És el camí legacy (p. ex.
            `tech_sheet_views`, que crea models sense sistema assignat): degradar amb gràcia,
            mai petar un import que fins ara funcionava.

    Returns:
        (run_ordenat, etiquetes_desconegudes):
          - run_ordenat: etiquetes del TENANT, sense duplicats, ordenades per
            `SizeDefinition.ordre`. Els forats són LEGÍTIMS i es conserven.
          - etiquetes_desconegudes: les que el sistema no coneix, en ordre d'aparició. NO
            entren al run. El cridador decideix: 400 al camí de producte (coherent amb el
            check (d) de la S24), avís al camí legacy.

    El pont de comparació és `canonical_size_label` (pont ÚNIC, llei 2026-07-08): salva
    XXL↔2XL, que un `upper+strip` no cobreix. Mai es persisteix la forma canònica: el run
    torna SEMPRE amb l'etiqueta del tenant.
    """
    from fhort.pom.size_labels import canonical_size_label

    # Etiquetes del model, en ordre d'aparició i sense duplicats (fallback sense sistema).
    vistes, model_labels = set(), []
    for e in (etiquetes or []):
        lbl = str(e or '').strip()
        if lbl and lbl not in vistes:
            vistes.add(lbl)
            model_labels.append(lbl)

    run_sistema = run_sistema_de(size_system)
    if not run_sistema:
        return model_labels, []

    canon_to_tenant = {canonical_size_label(e): e for e in run_sistema}
    ordre = {e: i for i, e in enumerate(run_sistema)}

    presents, desconegudes = set(), []
    for lbl in model_labels:
        tenant = canon_to_tenant.get(canonical_size_label(lbl))
        if tenant is None:
            desconegudes.append(lbl)
        else:
            presents.add(tenant)

    run_ordenat = sorted(presents, key=lambda e: ordre[e])
    return run_ordenat, desconegudes


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


# ═══════════════════════════════════════════════════════════════════════════════
# LLEI DEL CONTENIDOR (2026-07-16) — primitives del camí d'import segons la llei.
# Un GradingRuleSet de client = CONTENIDOR ACUMULATIU únic per
# (customer + size_system + garment_type_item + fit). L'import SEMBRA del contenidor
# (POMs de la fitxa), AMPLIA (POMs noves → afegir al contenidor), CONFLICTE per-regla,
# CREA només com a acte explícit. L'antic `derive_grading_rule_set` (creador automàtic 1D)
# va quedar JUBILAT per aquesta llei i ESBORRAT a P7 (2026-07-22); aquí es reutilitza el
# motor de detecció (detect_grading + derive_break_fields) per derivar les regles a
# sembrar/afegir, sense crear cap ruleset.
# ═══════════════════════════════════════════════════════════════════════════════

def _spec_from_detection(pm, res, base_def_id, run_ordenat):
    """Converteix la sortida de detect_grading (res) en un SPEC canònic uniforme (dict).
    Poblat sempre amb la forma aplicable (increment_base/break) via derive_break_fields, per
    poder comparar-lo contra les regles del contenidor amb el mateix llenguatge que el motor."""
    ib, ibrk, tlabel, tpos = derive_break_fields(
        res['logica'], res.get('increment'), res.get('valors_step'), run_ordenat)
    return {
        'pom_id': pm.id, 'pom': pm, 'talla_base_id': base_def_id,
        'logica': res['logica'], 'increment': res.get('increment') or 0,
        'valors_step': res.get('valors_step'),
        'increment_base': ib, 'increment_break': ibrk,
        'talla_break_label': tlabel, 'talla_break_pos': tpos,
    }


def derive_rules_from_fitxa(*, run_document, base_size, valors, confirmed_pom_ids,
                            size_system, avisos, bloqueigs=None):
    """DETECCIÓ pura de les regles d'una fitxa (sense persistència, sense ruleset).

    Reutilitza el motor de detecció (detect_grading per POM + derive_break_fields). Retorna
    una llista d'SPECS canònics uniformes (dicts), un per POM detectat; buida si no derivable.
    Substitueix el paper CREADOR de derive_grading_rule_set: aquí NOMÉS es detecta la forma;
    sembrar/afegir/materialitzar ho decideix el camí de la llei del contenidor a fora.

    REFERENT (llei S24): `run_document` — les talles del DOCUMENT, en llengua-tenant (el
    cridador hi ha aplicat el mateix aparellament que a `valors`). Abans el referent era
    `model.size_run_model`: si el run del model era MÉS ESTRET que el document, els deltes
    es calculaven entre veïns falsos i el break sortia FABRICAT. És el bug del model 166
    (run XS·S·L contra document XXS-L: S→L salta la M i val 2 passos → fals «×2» amb
    `talla_break_label='L'`). El referent final és la unió del run del document amb les
    talles realment presents a `valors`, ordenada pel sistema de talles.

    BLOQUEIG (llei d'integritat 2026-07-08, aquí per primer cop): una fila sense valor per a
    alguna talla del referent NO deriva cap regla amb deltes parcials — s'apunta a
    `bloqueigs` i el cridador ha d'aturar l'import. Abans només s'emetia un avís i la regla
    es persistia igualment: era el forat pel qual la llei encara es podia trencar.

    Args:
        bloqueigs: llista out-param (com `avisos`). Entrades
            {'tipus': 'fila_incompleta', 'pom_codi', 'missing_sizes'} o
            {'tipus': 'talles_desconegudes', 'etiquetes'}. Si el cridador no la passa, el
            comportament de bloqueig degrada a avís (cap cridador de producte ho fa).
    """
    from fhort.pom.models import SizeDefinition, POMMaster
    if bloqueigs is None:
        bloqueigs = []
    base_def = SizeDefinition.objects.filter(
        size_system=size_system, etiqueta__iexact=base_size,
    ).first() if (getattr(size_system, 'id', None) and base_size) else None

    run_sistema = list(
        SizeDefinition.objects.filter(size_system=size_system).order_by('ordre')
        .values_list('etiqueta', flat=True)) if getattr(size_system, 'id', None) else []
    # El document mana; les claus de `valors` hi entren perquè una columna amb valor és
    # columna del document encara que l'extracció no l'hagi rotulada al run detectat.
    files_ref = [{l: None for l in (run_document or [])}]
    files_ref += [valors.get(pid) or {} for pid in dict.fromkeys(confirmed_pom_ids)]
    run_ordenat, desconegudes = run_del_document(files_ref, run_sistema)
    if desconegudes:
        bloqueigs.append({'tipus': 'talles_desconegudes', 'etiquetes': desconegudes})
        avisos.append(
            "Talles del document sense equivalència al sistema de talles: "
            + ', '.join(desconegudes))
        return []

    if not run_ordenat or not base_size:
        avisos.append("Grading no derivat: manca run del document o talla base.")
        return []
    if base_def is None:
        avisos.append(
            f"Grading no derivat: talla base '{base_size}' no trobada al sistema de talles.")
        return []
    specs = []
    for pid in dict.fromkeys(confirmed_pom_ids):
        pm = POMMaster.objects.filter(id=pid).first()
        if not pm:
            continue
        vals = valors.get(pid) or {}
        # BLOQUEIG: cap regla d'una taula incompleta. Un forat intern amaga un break.
        missing = [s for s in run_ordenat if vals.get(s) is None]
        if missing:
            bloqueigs.append({'tipus': 'fila_incompleta',
                              'pom_codi': pm.codi_client, 'missing_sizes': missing})
            continue
        try:
            res = detect_grading(vals, run_ordenat, base_size)
        except Exception as e:
            avisos.append(f"POM {pm.codi_client}: detecció de grading fallida ({e}).")
            continue
        if res.get('warning'):
            avisos.append(f"POM {pm.codi_client}: {res['warning']}")
        if not res.get('logica'):
            avisos.append(f"POM {pm.codi_client}: grading no detectat; regla omesa.")
            continue
        specs.append(_spec_from_detection(pm, res, base_def.id, run_ordenat))
    if not specs and not bloqueigs:
        avisos.append("Cap regla de grading derivada dels valors.")
    return specs


def apply_scope_nodes(rule_set, nodes):
    """Reemplaça l'ÀMBIT D'APLICABILITAT (RuleSetScopeNode) d'un contenidor, idempotent (wipe&recreate).
    `nodes` = llista de dicts {node_type, group_codi | garment_type_id | garment_type_item_id}. Cada
    node valida EXACTAMENT un FK segons node_type; els nodes mal formats o inexistents s'ignoren. NO
    toca la identitat (garment_type_item de la constraint 0039); això és NOMÉS disponibilitat.
    Retorna la llista de nodes creats."""
    from fhort.pom.models import RuleSetScopeNode, GarmentGroup, GarmentType
    from fhort.tasks.models import GarmentTypeItem
    rule_set.scope_nodes.all().delete()
    creats = []
    vistos = set()
    for n in (nodes or []):
        nt = (n.get('node_type') or '').upper()
        node = RuleSetScopeNode(rule_set=rule_set, node_type=nt)
        if nt == RuleSetScopeNode.NODE_GROUP:
            g = GarmentGroup.objects.filter(codi=(n.get('group_codi') or '').strip()).first()
            if g is None:
                continue
            node.garment_group = g
            clau = ('GROUP', g.id)
        elif nt == RuleSetScopeNode.NODE_TYPE:
            gid = n.get('garment_type_id')
            if not gid or not GarmentType.objects.filter(pk=gid).exists():
                continue
            node.garment_type_id = gid
            clau = ('TYPE', gid)
        elif nt == RuleSetScopeNode.NODE_ITEM:
            iid = n.get('garment_type_item_id')
            if not iid or not GarmentTypeItem.objects.filter(pk=iid).exists():
                continue
            node.garment_type_item_id = iid
            clau = ('ITEM', iid)
        else:
            continue
        if clau in vistos:          # dedup dins del mateix payload (les unique parcials també ho guarden)
            continue
        vistos.add(clau)
        node.save()
        creats.append(node)
    return creats


def cerca_contenidor_client(customer, size_system, garment_type_item, fit_type):
    """DEPRECADA (G5, sprint MATCHER UNIFICAT) — cobreix NOMÉS la identitat dura (NIVELL 1) i
    ignora els contenidors AMPLI (item NULL) i la guarda d'ambigüitat. El camí d'import ja usa
    `resolve_grading_container` (M1). Queda viva perquè `size_map_views.py:731` encara la crida;
    G5 = migrar aquell caller i esborrar-la. NO afegir cap caller nou.

    EL contenidor de client per la IDENTITAT COMPLETA de la llei
    (customer + size_system + garment_type_item + fit_type). Únic per la constraint parcial
    `uniq_client_container_identity` (origen='CLIENT_RUN'). Retorna el GradingRuleSet o None
    (None = el client estrena la combinació → acte explícit de creació a fora).
    `customer`/`size_system` són imprescindibles; `garment_type_item`/`fit_type` poden ser None
    (llavors casa contra contenidors amb aquells eixos també a NULL)."""
    from fhort.pom.models import GradingRuleSet
    if not (customer and size_system):
        return None
    return (GradingRuleSet.objects.filter(
        origen=GradingRuleSet.ORIGEN_CLIENT_RUN, actiu=True,
        customer=customer, size_system=size_system,
        garment_type_item=garment_type_item, fit_type=fit_type,
    ).order_by('id').first())


def _scope_matches(rs, garment_group_codi, garment_type_id, garment_type_item_id):
    """Mirall EXACTE de scopeApplies(strict) del frontend (gradingAxes.js:88-102): sense
    scope_nodes → fallback al garment_group FK (per CODI); amb scope_nodes → casa si algun node
    ITEM/TYPE/GROUP coincideix amb l'eix corresponent. Mateixes laxituds (eixos NULL no casen)."""
    nodes = list(rs.scope_nodes.all())
    if not nodes:
        return rs.garment_group_id is not None and rs.garment_group.codi == garment_group_codi
    for n in nodes:
        if (n.node_type == 'ITEM' and garment_type_item_id is not None
                and n.garment_type_item_id == garment_type_item_id):
            return True
        if (n.node_type == 'TYPE' and garment_type_id is not None
                and n.garment_type_id == garment_type_id):
            return True
        if (n.node_type == 'GROUP' and garment_group_codi
                and n.garment_group_id is not None and n.garment_group.codi == garment_group_codi):
            return True
    return False


def resolve_grading_container(customer, size_system, target, construction, fit_type,
                             garment_group, garment_type_item=None):
    """MATCHER ÚNIC de contenidor de grading per al camí d'import (M1, sprint MATCHER UNIFICAT).

    La semàntica de MATCHING d'eixos és IDÈNTICA a matchingRuleSetsStrict del frontend
    (gradingAxes.js:151-162): mateixos eixos i laxituds — `targets` no-buit i inclou `target`,
    `construction`/`fit_type`/`size_system` coincidents i no-NULL, i abast per les DUES formes
    (garment_group FK o scope_nodes ITEM/TYPE/GROUP, via `_scope_matches`). Sobre aquest predicat,
    la LLEI DEL CONTENIDOR imposa prioritat i confidencialitat:

      NIVELL 1 (identitat dura, EXCEPCIÓ): contenidor CLIENT_RUN actiu amb `garment_type_item`
               EXACTE — la identitat de `cerca_contenidor_client`
               (customer + size_system + garment_type_item + fit_type). NO passa pel predicat
               d'eixos/abast (és identitat, no disponibilitat). Només s'avalua si hi ha item.
      NIVELL 2 (ampli): si el nivell 1 no en té, contenidor AMPLI (`garment_type_item` IS NULL)
               del MATEIX client (RUN-CLIENT: MAI d'un altre client) que casi el predicat d'eixos
               + abast.
      NIVELL 3: cap → None.

    GUARDA D'AMBIGÜITAT: si un nivell retorna >1 candidat, NO es resol (mai el primer
    arbitràriament): motiu='ambiguous' amb la llista de candidats.

    Paràmetres: `customer`/`size_system` = instàncies imprescindibles. `fit_type` = instància
    FitType (o None) — s'usa com a FK a la identitat i com a `.codi` al predicat. `target`,
    `construction`, `garment_group` = CODIS (str), igual que els eixos del frontend.
    `garment_type` (per als nodes TYPE) es DERIVA de `garment_type_item`.

    Retorna un dict {'container': GradingRuleSet|None, 'motiu': str, 'candidats': list}
    amb motiu ∈ {'exact','ampli','none','ambiguous'}.
    """
    from fhort.pom.models import GradingRuleSet
    if not (customer and size_system):
        return {'container': None, 'motiu': 'none', 'candidats': []}

    gti_id = getattr(garment_type_item, 'id', None)
    gt_id = getattr(garment_type_item, 'garment_type_id', None)

    # ── NIVELL 1 — identitat dura (només amb item). Mateix filtre que cerca_contenidor_client.
    if gti_id is not None:
        nivell1 = list(GradingRuleSet.objects.filter(
            origen=GradingRuleSet.ORIGEN_CLIENT_RUN, actiu=True,
            customer=customer, size_system=size_system,
            garment_type_item=garment_type_item, fit_type=fit_type,
        ).order_by('id'))
        if len(nivell1) > 1:
            return {'container': None, 'motiu': 'ambiguous', 'candidats': nivell1}
        if len(nivell1) == 1:
            return {'container': nivell1[0], 'motiu': 'exact', 'candidats': nivell1}

    # ── NIVELL 2 — ampli (item NULL) del MATEIX client amb el predicat d'eixos + abast.
    fit_codi = getattr(fit_type, 'codi', None)
    base_qs = GradingRuleSet.objects.filter(
        origen=GradingRuleSet.ORIGEN_CLIENT_RUN, actiu=True,
        customer=customer, size_system=size_system,
        garment_type_item__isnull=True,
    )
    if target:
        base_qs = base_qs.filter(targets__codi=target)      # no-buit + inclou target (paritat frontend)
    else:
        return {'container': None, 'motiu': 'none', 'candidats': []}
    if construction:
        base_qs = base_qs.filter(construction__codi=construction)
    else:
        return {'container': None, 'motiu': 'none', 'candidats': []}
    if fit_codi:
        base_qs = base_qs.filter(fit_type__codi=fit_codi)
    else:
        return {'container': None, 'motiu': 'none', 'candidats': []}
    candidats = [rs for rs in base_qs.distinct().prefetch_related('scope_nodes', 'targets')
                 if _scope_matches(rs, garment_group, gt_id, gti_id)]
    if len(candidats) > 1:
        return {'container': None, 'motiu': 'ambiguous', 'candidats': candidats}
    if len(candidats) == 1:
        return {'container': candidats[0], 'motiu': 'ampli', 'candidats': candidats}
    return {'container': None, 'motiu': 'none', 'candidats': []}


def rule_to_spec(r):
    """Normalitza una GradingRule (regla de contenidor) al mateix SPEC dict que la detecció."""
    return {
        'pom_id': r.pom_id, 'pom': getattr(r, 'pom', None), 'talla_base_id': r.talla_base_id,
        'logica': r.logica, 'increment': r.increment, 'valors_step': r.valors_step,
        'increment_base': r.increment_base, 'increment_break': r.increment_break,
        'talla_break_label': r.talla_break_label, 'talla_break_pos': r.talla_break_pos,
    }


def _num_eq(a, b, tol=0.001):
    if a is None and b is None:
        return True
    if (a is None) != (b is None):
        return False
    try:
        return abs(float(a) - float(b)) < tol
    except (TypeError, ValueError):
        return False


def spec_forms_match(a, b):
    """Igualtat de la FORMA APLICABLE (la que aplica el motor: increment_base + increment_break
    + talla_break_label). NO compara `increment` legacy (un contenidor curat el porta a 0 i
    condueix per increment_base) ni la talla base (invariant al grading, com grading_rules_match).
    Aquesta és la comparació-veritat per al CONFLICTE per-regla contenidor-vs-fitxa."""
    return (_num_eq(a.get('increment_base'), b.get('increment_base'))
            and _num_eq(a.get('increment_break'), b.get('increment_break'))
            and _norm(a.get('talla_break_label')) == _norm(b.get('talla_break_label')))


def classifica_fitxa_vs_contenidor(specs, container):
    """Classifica els SPECS de la fitxa contra les regles del contenidor, segons la llei:
      - SEMBRA:    POM compartit i forma idèntica → resident des del contenidor (autoritatiu).
      - AMPLIA:    POM de la fitxa que el contenidor NO té → afegir al contenidor.
      - CONFLICTE: POM compartit amb forma DIFERENT → tria conscient per-regla.
    (Les POMs del contenidor absents de la fitxa NO es toquen: no se sembren, resten al catàleg.)
    Retorna dict {'sembra': [spec], 'amplia': [spec], 'conflicte': [dict]}.
    """
    cont_by = {r.pom_id: r for r in container.regles.all()}
    sembra, amplia, conflicte = [], [], []
    for s in specs:
        cr = cont_by.get(s['pom_id'])
        if cr is None:
            amplia.append(s)
        elif spec_forms_match(s, rule_to_spec(cr)):
            sembra.append(rule_to_spec(cr))
        else:
            conflicte.append({
                'pom_id': s['pom_id'],
                'pom_codi': getattr(s.get('pom'), 'codi_client', None) or s['pom_id'],
                'spec_fitxa': s,
                'spec_container': rule_to_spec(cr),
                'regla_container_id': cr.id,
                'detall': (f"forma difereix (contenidor ib={cr.increment_base}"
                           f"/brk={cr.increment_break} vs fitxa ib={s['increment_base']}"
                           f"/brk={s['increment_break']})"),
            })
    return {'sembra': sembra, 'amplia': amplia, 'conflicte': conflicte}


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


def propaga_ancoratges(rule, anchor_label, anchor_val, size_run, warnings=None):
    """Propaga el delta CANÒNIC/LINEAR de la regla des d'UNA talla ancorada.

    Funció PURA (cap I/O, cap ORM). Règim LINEAR/canònic NOMÉS: el cridador NO la crida
    en règim STEP/FIXED/ZERO (allà els valors són lliures i no es propaguen).

    rule: forma canònica (`increment_base` [+ `talla_break_label` + `increment_break`])
          o LINEAR pur legacy (`increment` uniforme quan `increment_base` és None).
    anchor_label / anchor_val: la talla editada i el seu valor real — origen únic de la
          propagació.
    size_run: list d'etiquetes ordenades.
    warnings: acceptat per compatibilitat de signatura; canònic/LINEAR no genera avisos.

    Retorna {size_label: valor_teoric} per CADA talla del run (claus = etiquetes ORIGINALS),
    caminant el delta des de l'ancoratge.
    """
    run = [str(s).strip() for s in (size_run or [])]
    if not run:
        return {}
    norm_run = [_norm(s) for s in run]
    na = _norm(anchor_label)
    if na not in norm_run:                      # ancoratge fora del run (defensiu)
        return {lab: None for lab in run}
    anchor_idx = norm_run.index(na)
    anchor_val = float(anchor_val)

    # Delta de la regla: increment_base (+ break per ETIQUETA) o, si és None, increment uniforme.
    ib_raw = getattr(rule, 'increment_base', None)
    if ib_raw is not None:
        ib = float(ib_raw)
        brk_raw = getattr(rule, 'increment_break', None)
        brk = float(brk_raw) if brk_raw is not None else ib
        break_idx = None
        tbl = getattr(rule, 'talla_break_label', None)
        if tbl:
            tn = _norm(tbl)
            if tn in norm_run:
                break_idx = norm_run.index(tn)
    else:                                       # LINEAR pur legacy
        inc_raw = getattr(rule, 'increment', None)
        if inc_raw is None and warnings is not None:
            warnings.append(
                f"Regla sense delta definit (pom={getattr(rule, 'pom_id', None)}): "
                f"propagació plana (delta 0) des de l'ancoratge {anchor_label}.")
        ib = brk = float(inc_raw) if inc_raw is not None else 0.0
        break_idx = None

    out = {}
    for t_idx, label in enumerate(run):
        if t_idx == anchor_idx:
            out[label] = anchor_val
            continue
        # Camí d'acumulació des de l'ancoratge (mecànica canònica de _apply_rule, origen
        # = anchor_idx). Cada aresta s'indexa per la seva etiqueta SUPERIOR; el break és
        # posicional absolut → simètric amunt/avall, sense ambigüitat.
        if t_idx > anchor_idx:
            path, sign = range(anchor_idx + 1, t_idx + 1), 1.0
        else:
            path, sign = range(t_idx + 1, anchor_idx + 1), -1.0
        total = 0.0
        for j in path:
            total += brk if (break_idx is not None and j >= break_idx) else ib
        out[label] = anchor_val + sign * total

    return out
