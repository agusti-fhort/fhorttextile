> ⚠️ SUPERADA 2026-07-07 — bug resolt (whitelist LOGICA_CHOICES complet, 3fa99c4). Consulta només com a històric.

# DIAGNOSI QUIRÚRGICA — 400 a `gravar-pom`: "logica ha de ser 'LINEAR' o 'STEP'"

**Data:** 2026-06-26 · **Branca:** `dev` · **Patró:** READ-ONLY (cap codi, cap push)
**Símptoma:** `gravar-pom` torna 400 `"logica ha de ser 'LINEAR' o 'STEP'"`, **repetit per cada POM**.
La pantalla mostra LINEAR a tots els selectors. Fila C.1 té break (delta 3 / break 4 / XXL).
**Hipòtesi Agus:** el codi interpreta que un break trenca LINEAR i envia `logica` invàlida.

---

## ⚖️ VEREDICTE (resum) — opció (c), i la hipòtesi del break queda REFUTADA

**No és el break.** És que **la validació de `gravar-pom` (whitelist `{LINEAR, STEP}`) és més
ESTRETA que el domini real del camp `logica` (`{LINEAR, STEP, FIXED, ZERO, EXCEPTION}`)**. Molts POMs
tenen una regla resident/​catàleg legítima amb `logica='FIXED'` (mesures que no graden). El flux:

1. `taula-mesures` retorna `logica = rule.logica` → p.ex. `'FIXED'` ([views.py:735](backend/fhort/models_app/views.py#L735)).
2. La graella POM carrega `row.logica='FIXED'`, però el `<select>` només té opcions LINEAR/STEP
   ([EditableTable.jsx:328-329](frontend/src/components/EditableTable/EditableTable.jsx#L328-L329)) → el navegador **mostra "LINEAR"** (primera opció) mentre l'estat
   intern segueix sent `'FIXED'`. ← d'aquí "la pantalla mostra LINEAR".
3. `buildPayload` envia `logica: r.logica || 'LINEAR'` → com que `'FIXED'` és truthy, **envia `'FIXED'`**
   ([EditableTable.jsx:128](frontend/src/components/EditableTable/EditableTable.jsx#L128)).
4. `gravar_pom_view` rebutja tot el que no sigui LINEAR/STEP → acumula l'error **per cada fila FIXED**
   ([views.py:964-966](backend/fhort/models_app/views.py#L964-L966)) i el retorna 400 unit amb `'; '` ([views.py:999](backend/fhort/models_app/views.py#L999),[:1010](backend/fhort/models_app/views.py#L1010)).

**Prova empírica (BD `fhort`, read-only):** catàleg `GradingRule` = **107 FIXED** / 578 LINEAR;
resident `ModelGradingRule` = **24 FIXED** / 92 LINEAR / 1 STEP. → FIXED és massiu i arriba a la graella.

**El break és innocent:** una fila LINEAR-amb-break (C.1) **passa** la validació i desa el break sense
problema (§2). El 400 el provoquen les files **FIXED**, no la del break. La coincidència que C.1 tingui
break ha despistat el diagnòstic.

---

## PREGUNTA 1 — Com construeix el frontend el camp `logica` de cada regla

**Cadena:** `MeasuresEntryPanel` (mode manual) → `<EditableTable onPomSave={savePom}>` → `buildPayload`
→ `models.gravarPom`.

- **Construcció del payload** — [EditableTable.jsx:114-134](frontend/src/components/EditableTable/EditableTable.jsx#L114-L134):
  ```js
  const rules = localRows.filter(r => r.pom_id).map(r => ({
    pom_id: r.pom_id,
    logica: r.logica || 'LINEAR',        // ← L128: NO deriva del break; reenvia el valor de la fila
    increment_base: r.increment_base ?? null,
    increment_break: r.increment_break ?? null,
    talla_break_label: r.talla_break_label || null,
  }))
  ```
  **FET:** el `logica` NO es deriva del break. Es llegeix de `row.logica` (el selector), amb fallback
  `'LINEAR'` només si és falsy. El break (`increment_break`/`talla_break_label`) va en camps a part i
  **no toca** `logica`.

- **El selector** — [EditableTable.jsx:318-330](frontend/src/components/EditableTable/EditableTable.jsx#L318-L330): `value={row.logica || 'LINEAR'}` amb NOMÉS dues opcions,
  `<option value="LINEAR">` i `<option value="STEP">`. Si `row.logica` és `'FIXED'`/`'ZERO'`/`'EXCEPTION'`,
  el control no té opció coincident → **mostra LINEAR visualment, però `row.logica` segueix sent
  `'FIXED'`** fins que l'usuari el canviï activament. El fallback `|| 'LINEAR'` **no** salva el cas
  perquè `'FIXED'` és truthy.

- **D'on surt `row.logica`:**
  - Files d'un model ja materialitzat (recàrrega/seed) → de `/taula-mesures/`, que serialitza
    `'logica': getattr(rule, 'logica', None)` ([views.py:735](backend/fhort/models_app/views.py#L735)). Si el rule és FIXED → `row.logica='FIXED'`.
  - Files d'un model verge (suggerits) → `pomsSuggerits.map(...)` ([MeasuresEntryPanel.jsx:263-269](frontend/src/components/model/MeasuresEntryPanel.jsx#L263-L269)) **no
    porten `logica`** → `undefined || 'LINEAR'` = `'LINEAR'` (vàlid). *(Per això un model 100% nou no
    falla; falla quan hi ha regles residents/catàleg FIXED carregades a la taula.)*

- **`savePom`** — [MeasuresEntryPanel.jsx:137-151](frontend/src/components/model/MeasuresEntryPanel.jsx#L137-L151): passa el payload tal qual a `models.gravarPom(id, payload)`; no
  transforma `logica`.

### Resposta a la pregunta CRÍTICA de l'Agus (per totes les files o només el break?)
**Per TOTES les files la `logica` de les quals estigui emmagatzemada com a FIXED/ZERO/EXCEPTION**
(no la del break). El missatge es repeteix perquè l'error s'acumula a la llista i s'uneix amb `'; '`
([views.py:999](backend/fhort/models_app/views.py#L999)). → Segons el propi criteri de distinció de l'Agus ("si surt per totes → NO és
el break"), **NO és el break**. Però tampoc és (b) "logica no inclosa al payload": la `logica` SÍ
s'inclou per cada fila ([EditableTable.jsx:128](frontend/src/components/EditableTable/EditableTable.jsx#L128)); el problema és que el VALOR inclòs (FIXED) no és a la
whitelist del backend.

---

## PREGUNTA 2 — Què valida `gravar_pom_view`, i comparació amb `set_pom_regim_view`

- **`gravar_pom_view`** — bucle de regles [views.py:960-996](backend/fhort/models_app/views.py#L960-L996):
  ```python
  logica = (r.get('logica') or '').strip().upper() or None     # L964
  if logica is not None and logica not in ('LINEAR', 'STEP'):   # L965  ← whitelist ESTRETA
      errors.append("logica ha de ser 'LINEAR' o 'STEP'")       # L966
      continue
  ...
  if 'increment_base'  in r: rule.increment_base  = _to_decimal(...)   # L985-986
  if 'increment_break' in r: rule.increment_break = _to_decimal(...)   # L987-988  ← break OK amb LINEAR
  if 'talla_break_label' in r: rule.talla_break_label = ...; rule.talla_break_pos = _break_pos(...)  # L989-992
  ```
  **Accepta LINEAR amb break?** SÍ: el break es desa a [views.py:987-992](backend/fhort/models_app/views.py#L987-L992) **independentment** de la
  lògica; LINEAR passa el filtre de [views.py:965](backend/fhort/models_app/views.py#L965). → **LINEAR-amb-break és vàlid** (consistent amb la
  llei canònica). **Rebutja** qualsevol `logica` ≠ LINEAR/STEP (FIXED/ZERO/EXCEPTION).

- **`set_pom_regim_view`** (el que "ja funciona" a Mesures) — [views.py:2334-2336](backend/fhort/models_app/views.py#L2334-L2336):
  ```python
  logica = (data.get('logica') or '').strip().upper() if has('logica') else None
  if logica is not None and logica not in ('LINEAR', 'STEP'):
      return Response({'detail': "logica ha de ser 'LINEAR' o 'STEP'."}, status=400)
  ```
  **Té EXACTAMENT la mateixa whitelist estreta `{LINEAR, STEP}`.** No és més tolerant.

  **Per què `set_pom_regim` no peta i `gravar-pom` sí — la divergència REAL (d'ÚS, no de regla):**
  `set_pom_regim` edita **UN** POM i només valida `logica` **si la clau ve** (`has('logica')`), amb
  l'usuari triant explícitament LINEAR o STEP al selector de l'editor d'Escalat → mai hi fa
  *round-trip* d'un FIXED preexistent. `gravar-pom`, en canvi, **reenvia en BLOC el `logica` de TOTES
  les files** (incloses les FIXED que l'usuari no ha tocat) → exposa el cas FIXED que la whitelist
  rebutja. **FET:** la regla de validació és idèntica; el que divergeix és que `gravar-pom` fa
  round-trip massiu d'un valor que el camp permet però la whitelist no.

---

## PREGUNTA 3 — Contracte de `ModelGradingRule.logica`

- **Domini del camp:** `ModelGradingRule.logica` usa `GradingRule.LOGICA_CHOICES`
  ([models_app/models.py:601](backend/fhort/models_app/models.py#L601)). Els choices ([pom/models.py:548-559](backend/fhort/pom/models.py#L548-L559)) són **CINC**:
  `LINEAR`, `STEP`, **`FIXED`**, **`ZERO`**, **`EXCEPTION`**.
- **LINEAR amb `increment_break` + `talla_break_label` és vàlid?** SÍ — és la forma canònica.
  `grading_utils.classify_grading` ([grading_utils.py:121-191](backend/fhort/pom/grading_utils.py#L121-L191)) classifica `0 o 1 break = LINEAR`
  (delta uniforme o un sol esglaó, p.ex. CHEST), `≥2 breaks = STEP` ([grading_utils.py:169-188](backend/fhort/pom/grading_utils.py#L169-L188)), i
  `derive_break_fields` ([grading_utils.py:198-204](backend/fhort/pom/grading_utils.py#L198-L204)) tracta igual LINEAR-amb-break i STEP. → confirma la
  **llei canònica**: una fila LINEAR amb UN break SEGUEIX sent LINEAR.
- **`FIXED` és un valor legítim de `logica`**, produït per `classify_grading` (retorna
  `'LINEAR' | 'FIXED' | 'STEP' | None`, [grading_utils.py:130](backend/fhort/pom/grading_utils.py#L130)) i present a BD (107 catàleg + 24 residents).
  → Una whitelist `{LINEAR, STEP}` **incompleix el contracte del camp**.

---

## Conclusió i propostes (no aplicades)

**Causa arrel (c):** desalineació domini↔validació. El camp `logica` admet 5 valors; `gravar_pom_view`
([views.py:965](backend/fhort/models_app/views.py#L965)) i `set_pom_regim_view` ([views.py:2335](backend/fhort/models_app/views.py#L2335)) només n'accepten 2. En fer
`gravar-pom` un *round-trip* en bloc del `logica` de cada fila, les regles FIXED (massives) reboten amb
400, repetit per POM. El break i la fila C.1 són innocents; la hipòtesi "el break trenca LINEAR" queda
**refutada** (LINEAR-amb-break passa i desa el break correctament).

| Opció plantejada | Veredicte |
|---|---|
| (a) el break es mal-interpreta com a no-LINEAR | 🔴 REFUTADA — el frontend no deriva logica del break; el backend accepta LINEAR+break |
| (b) `logica` no s'inclou al payload per cap fila | 🔴 REFUTADA — s'inclou sempre ([EditableTable.jsx:128](frontend/src/components/EditableTable/EditableTable.jsx#L128)) |
| **(c) validació més estreta que el contracte del camp** | ✅ **CONFIRMADA** (FIXED legítim → 400) |

### 💡 PROPOSTES (cap aplicada — diagnosi pura)
1. **Backend (mínima, desbloqueja sol):** ampliar la whitelist de `gravar_pom_view` (i, per coherència,
   `set_pom_regim_view`) al domini complet — reusar `GradingRule.LOGICA_CHOICES` en lloc del literal
   `('LINEAR','STEP')` ([views.py:965](backend/fhort/models_app/views.py#L965), [views.py:2335](backend/fhort/models_app/views.py#L2335)). Amb això, el round-trip d'un FIXED preexistent
   torna a ser vàlid.
2. **Frontend (coherència UX):** el `<select>` de règim ([EditableTable.jsx:328-329](frontend/src/components/EditableTable/EditableTable.jsx#L328-L329)) hauria de
   representar el valor real (afegir opcions FIXED/ZERO/EXCEPTION o, com a mínim, no **emmascarar**
   un FIXED mostrant "LINEAR"). Ara mateix mostra LINEAR però envia FIXED → enganya l'usuari i el
   payload alhora.
3. *(Decisió de producte, fora d'abast):* si es vol que el tècnic NOMÉS pugui posar LINEAR/STEP a
   `gravar-pom`, aleshores el frontend ha de **coercir** el valor mostrat (no només visualment) abans
   d'enviar; però això perdria el FIXED canònic del catàleg → es recomana (1).

---

### Metodologia
Lectura directa de la cadena completa (`MeasuresEntryPanel.savePom` → `EditableTable.buildPayload` →
`gravar_pom_view`), comparació amb `set_pom_regim_view`, contracte del model + `grading_utils`, i
**verificació empírica read-only a BD** dels valors reals de `logica`. Provenència git: la pantalla i
`gravar-pom` són d'avui (`c8f11fc` 09:17, `bb1bc24`); el gunicorn FTT es va reiniciar a les 09:26 → el
backend en execució **SÍ** porta aquest codi (descartat el patró "gunicorn stale"). Tot read-only.
