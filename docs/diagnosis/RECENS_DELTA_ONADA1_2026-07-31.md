# RE-CENS DELTA · ONADA 1 (TRAM C · CAPES) — 2026-07-31

> Patró A · READ-ONLY. Re-localització del cens de `DIAGNOSI_CAPA_POMS` (30/07, HEAD
> `98c0982e`) contra `dev` d'avui (HEAD `3efe7f4b`, represa de C1). Cens i prou: cap
> proposta de fix, cap dimensionament.

**Període auditat:** `98c0982e..3efe7f4b` — **57 commits** (NOMS-POM, TAULES, CAPÇALERA
v3.3, EDITOR-DIBUIX, GRADUACIÓ-porta-pròpia, FIX-1..4, represa de C1).

**VEREDICTE: DELTA NO TRIVIAL** — cap node CANVIAT ni DESAPAREGUT, però hi ha **4 lectors
per-POM NOUS** nascuts al període, més **1 lector preexistent que el cens no recull**.
L'Onada 1 no pot arrencar amb la llista de línies del cens: hi falten 5 punts.

---

## FASE A · Re-localització dels 20 nodes

**9 dels 15 fitxers de node són byte-idèntics al cens** (`git diff 98c0982e..HEAD` buit):
`s10_views.py` · `s8_views.py` · `s11_views.py` · `s6_views.py` · `fitting/serializers.py` ·
`serializers_size_check.py` · `pom_placement_views.py` · `grading_views.py` ·
`measureSources.jsx`. Tot node que hi viu és **IGUAL** per construcció.

Els 6 fitxers tocats: `graded_spec_views.py` (+13) · `repas_views.py` (+16) ·
`pom/services.py` (+23) · `CheckMeasureEditor.jsx` (+19) · `fittingGridAdapter.jsx` (+52) ·
`TechSheetEditor.jsx` (+824).

### Backend

**1 · `pom/services.py:711` `_load_model_overrides`** — cens 711 → ara **711**. `IGUAL`
```python
def _load_model_overrides(model_id: int) -> dict:
    """Return {(pom_id, size_label): value_cm} of per-model fitting overrides."""
    try:
```
L'únic canvi del període a aquest fitxer és a `_apply_rule` (~930, FIX-1): no toca el node.

**2 · `pom/s10_views.py:43-55` `_tolerance_map`** — `IGUAL`
```python
def _tolerance_map(model):
    """Asymmetric tolerance per pom from BaseMeasurement(model, pom).
    Returns {pom_id: (tol_minus, tol_plus)} …
```
El dict es construeix a `tol[bm.pom_id] = (tm, tp)` (L54) i es llegeix a
`tol_map.get(line.pom_id, …)` (L89).

**3 · `pom/s8_views.py:179-183`** (cens ~180) — `IGUAL`
```python
        tol_map = {}
        for bm in BaseMeasurement.objects.filter(model=model, is_active=True):
            …
            tol_map[bm.pom_id] = (tm, tp)
```

**4 · `pom/s11_views.py:161-165` `base_map` (→ POMAlert)** (cens ~162) — `IGUAL`
```python
        base_map = {
            bm.pom_id: float(bm.base_value_cm)
            for bm in BaseMeasurement.objects.filter(model=model, is_active=True)
```

**5 · `pom/s6_views.py:86-90`** — `IGUAL`
```python
        bms = BaseMeasurement.objects.filter(
            model_id=model_id, is_active=True
        ).select_related('pom', 'pom__pom_global', 'pom__categoria').order_by(
```

**6 · `fitting/graded_spec_views.py:85-98` (payload fitxa)** — cens 85-88 → ara **85-98**.
`MOGUT` **+ 1 lector NOU al mateix bloc** (v. B-N1)
```python
        bms = BaseMeasurement.objects.filter(model_id=sf.model_id).values(
            'pom_id', 'ordre', 'nom_fitxa', 'seccio',
            'nom_canonic_model', 'nom_traduit_model')          # ← R1/31-07
        ordre_map = {bm['pom_id']: bm['ordre'] for bm in bms}
        nom_fitxa_map = {bm['pom_id']: bm['nom_fitxa'] for bm in bms}
        seccio_map = {bm['pom_id']: bm['seccio'] for bm in bms}
        bateig_map = {bm['pom_id']: (…)}                        # ← NOU
```
La forma no canvia (segueix sent dict per `pom_id`): el bloc passa de **3 mapes a 4**.

**7 · `fitting/serializers.py:259-262` (+ comentari 255)** — `IGUAL`
```python
        # BaseMeasurement del model (unique per (model, pom)): aporta nom_fitxa …
        bm_data = list(BaseMeasurement.objects.filter(model_id=obj.model_id)
                       .values_list('pom_id', 'ordre', 'nom_fitxa', 'id'))
        ordre_map = {p: o for p, o, _, _ in bm_data}
```
⚠️ El comentari **«unique per (model, pom)»** (L255) segueix literal i ara és **fals a la
BD**: des de `3efe7f4b` la unicitat és `(model, pom, capa)`.

**8 · `models_app/serializers_size_check.py:81-84` `bm_map`** — `IGUAL`
```python
        bm_map = {
            bm.pom_id: bm
            for bm in BaseMeasurement.objects.filter(model_id=obj.model_id)
        }
```

**9 · `models_app/pom_placement_views.py:68-71` `bm_by_pom`** — `IGUAL`
```python
    bm_by_pom = {}
    if model_id:
        bm_by_pom = dict(BaseMeasurement.objects.filter(
            model_id=model_id, is_active=True).values_list('pom_id', 'id'))
```

**10 · `fitting/repas_views.py:253-259`** — cens ~250 → ara **253-259**. `MOGUT`
**+ 1 lector NOU al mateix bloc** (v. B-N2)
```python
        bm_data = list(BaseMeasurement.objects.filter(model_id=model.id)
                       .values_list('pom_id', 'ordre', 'nom_fitxa', 'id',
                                    'nom_canonic_model', 'nom_traduit_model'))
        ordre_map = {p: o for p, o, _, _, _, _ in bm_data}
        nom_fitxa_map = {p: nf for p, _, nf, _, _, _ in bm_data}
        bm_id_map = {p: i for p, _, _, i, _, _ in bm_data}
        bateig_map = {p: (nc or '', nt or '') for p, _, _, _, nc, nt in bm_data}   # ← NOU
```

**11 · `pom/grading_views.py:120-141`** — `IGUAL`
```python
                for bm in base_ms:
                    pom_id = bm.pom_id
                    if pom_id not in poms_seen:
                        …
                    cells[pom_id][model.base_size_label] = {…}
```

### Frontend

**12a · `TechSheetEditor.jsx:3452`** — cens 3317 → ara **3452** (+135). `MOGUT`, línia idèntica
```jsx
    const bmByPom = new Map(pomRows.map(bm => [bm.pom_id, bm]))
    …
        const bm = bmById.get(o.bmId) || bmByPom.get(o.pomId)          // L3457
```

**12b · `TechSheetEditor.jsx:5513`** — cens 5272 → ara **5513** (+241). `MOGUT`, línia idèntica
```jsx
      const bmByPom = new Map(pomRows.map(bm => [bm.pom_id, bm]))
        const bm = bmByPom.get(pomId)                                   // L5516
```

**12c · `TechSheetEditor.jsx:5614`** — cens 5373 → ara **5614** (+241). `MOGUT`, línia idèntica
```jsx
      const bmByPom = new Map(pomRows.map(bm => [bm.pom_id, bm]))
        const bm = bmByPom.get(p.pom_id)                                // L5621
```

**13 · `TechSheetEditor.jsx:276` `cotaLabelDe`** — cens 251 → ara **276** (+25). `MOGUT`,
línia idèntica byte a byte
```jsx
export const cotaLabelDe = (bm) => (bm && (bm.nom_fitxa || bm.codi_client || bm.pom_code_global)) || ''
```
Consumidors: L3459 · L5460 · L5518 · L5626 · L6638 (cens: 3324 · 5219 · 5277 · 5385 · 6359).

**14 · `CheckMeasureEditor.jsx:217-218` `lineByPom`** — `IGUAL` (línia exacta del cens)
```jsx
    const lineByPom = {}
    for (const l of (raw.check?.lines || [])) lineByPom[l.pom_id] = l
      const line = lineByPom[r.pom_id]                                  // L220
```
Els +19 del període (NOMS-POM: `onNomsSave`, camps `nom_*_model`) cauen **després** i no
toquen el node.

**15 · `measureSources.jsx:18-27` `pomMap`** — `IGUAL` (fitxer intocat)
```jsx
  const pomMap = new Map()
    if (!pomMap.has(l.pom_id)) pomMap.set(l.pom_id, {…})
    pomMap.get(l.pom_id).cells[l.size_label] = l
```

**16 · `fittingGridAdapter.jsx:144` `lineId = \`${pom_id}:${size}\``** — cens 140 → ara
**144** (+4). `MOGUT`, línia idèntica
```jsx
        active: { lineId: `${row.pom_id}:${s}`, value: v == null ? '' : v, baseValue: v },
```
Els +52 del període són `escalatRuleLeadCols` (FIX-4): columnes **per fila**, cap dict per POM.

---

## FASE B · Lectors NOUS

**B2 · JS/JSX: zero.** Cap línia afegida al període casa amb `byPom` · `pomMap` ·
`[pom_id]` · `pom_id]:` · `.pom_id ===`. Els 7 fitxers nous de front
(`GraduacioPanel.jsx`, `wizardUI.jsx`, `BateigInput.jsx`, `nomenclaturaPom.js`,
`plausibilitatMesura.js`…) **no llegeixen per POM**.

**B2 · Python: 4 lectors nous reals** (de 20 candidats; la resta, tests i cadenes de log).

| # | Lloc | Taula | Snippet | Veredicte |
|---|---|---|---|---|
| **N1** | `fitting/graded_spec_views.py:95-98` + `:116-118` | BaseMeasurement | `bateig_map = {bm['pom_id']: (bm['nom_canonic_model'] or '', …)}` → `bateig_map.get(row['pom_id'])` | **LECTOR NOU REAL** |
| **N2** | `fitting/repas_views.py:259` + `:276-277` | BaseMeasurement | `bateig_map = {p: (nc or '', nt or '') for p, …}` → `bateig_map.get(pom_id)` | **LECTOR NOU REAL** |
| **N3** | `models_app/services_size_check.py:35-40` | SizeCheckLine × BaseMeasurement | `ja_hi_son = set(SizeCheckLine…values_list('pom_id'))` → `.exclude(pom_id__in=ja_hi_son)` | **LECTOR NOU REAL** — creua DUES de les 9 taules per `pom_id` sol |
| **N4** | `models_app/views.py:3962-3964` (`_sembra_step_des_dels_specs`) | GradedSpec | `dict(GradedSpec.objects.filter(grading_version=gv, pom_id=pom_id, is_active=True).values_list('size_label','graded_value_cm'))` | **LECTOR NOU REAL** |

Falsos positius descartats (motiu d'una línia):
- `views.py:1691` `f'POM {pom_id}: {fora}'` · `services.py:2027` `f"…(pom={…pom_id})"` — cadenes de missatge, no lectura.
- `views.py:1958-1963` `ModelGradingRule…pom_id=pom_id` — `ModelGradingRule` **no té `capa`** per decisió 3c.1.
- ~14 ocurrències a `test_*.py` / `tests.py` — fixtures i asserts, no producte.
- `patterns/*` — fora d'abast (Fase 2, v. Fase C).

**B3 · Contrast amb el cens.** Un cinquè lector no és ni als 20 ni als exclosos, però
**NO és nou**: ja existia a `98c0982e`. El classifico a part per no falsejar-lo:

| # | Lloc | Taula | Snippet | Veredicte |
|---|---|---|---|---|
| **X1** | `models_app/views.py:2992` + `:3000`/`:3004` (`base_stages_view`) | MeasurementChangeLog + BaseMeasurement | `changes_by_ev[key][c.pom_id] = float(c.valor_nou)` · `snapshot.update(…)` · `displayed = {bm.pom_id for bm in bms}` | **NO CENSAT (preexistent)** — verificat present a `98c0982e` |

La query de sobre **sí** que ha canviat al període (`+ base_measurement__isnull=False`,
FIX-2), però el dict per `pom_id` ja hi era. És el node que el pin
`test_base_stages_no_regressio` (13/13) protegeix.

---

## FASE C · Vigència dels exclosos — **els 5 confirmats, cap tocat**

| Exclòs | Estat |
|---|---|
| `pom/services.py:747` `_load_base_measurements` | **INTOCAT**. Línia idèntica al cens (747 → 747), segueix sent `{bm.pom_id: bm.base_value_cm}`. Zona intocable → C3. |
| `pom/services.py:682` `_load_grading_rules` | **INTOCAT** (682 → 682). `ModelGradingRule` segueix **SENSE `capa`**: `3efe7f4b` no la toca, i l'auditoria de BD del mateix dia dona `te_capa=false` a `models_app_modelgradingrule` als dos schemas (510 files a `fhort`). Decisió 3c.1 vigent. |
| `patterns/views.py:544-548` (`ancorats`) | **INTOCAT** — `git diff 98c0982e..HEAD` buit per al fitxer. Clau `pom_master_id`, no `pom_id`. |
| `patterns/engine/grading_projection.py:179` | **INTOCAT** — diff buit. `poms_per_id` / `ids_amb_spec` / `codis_spec` per `pom_id`. |
| `patterns/adapters.py:585-624` | **INTOCAT** — diff buit. `pom_id=pom.pom_master_id`. |

Cap commit del període toca els tres fitxers de `patterns/`.

---

## FASE D · Taula final

| # | Node | Estat | Línia actual | Nota |
|---|---|---|---|---|
| 1 | `pom/services.py` `_load_model_overrides` | IGUAL | 711 | mateixa línia que al cens |
| 2 | `pom/s10_views.py` `_tolerance_map` | IGUAL | 43-55 | fitxer byte-idèntic |
| 3 | `pom/s8_views.py` `tol_map` | IGUAL | 179-183 | fitxer byte-idèntic |
| 4 | `pom/s11_views.py` `base_map` | IGUAL | 161-165 | fitxer byte-idèntic |
| 5 | `pom/s6_views.py` BaseMeasurement | IGUAL | 86-90 | fitxer byte-idèntic |
| 6 | `fitting/graded_spec_views.py` payload fitxa | MOGUT | 85-98 | 3 mapes → 4; el 4t és N1 |
| 7 | `fitting/serializers.py` `bm_data` | IGUAL | 259-262 | comentari 255 ara desactualitzat |
| 8 | `serializers_size_check.py` `bm_map` | IGUAL | 81-84 | fitxer byte-idèntic |
| 9 | `pom_placement_views.py` `bm_by_pom` | IGUAL | 68-71 | fitxer byte-idèntic |
| 10 | `fitting/repas_views.py` `bm_data` | MOGUT | 253-259 | 3 mapes → 4; el 4t és N2 |
| 11 | `pom/grading_views.py` `cells` | IGUAL | 120-141 | fitxer byte-idèntic |
| 12a | `TechSheetEditor.jsx` `bmByPom` | MOGUT | 3452 | +135, línia idèntica |
| 12b | `TechSheetEditor.jsx` `bmByPom` | MOGUT | 5513 | +241, línia idèntica |
| 12c | `TechSheetEditor.jsx` `bmByPom` | MOGUT | 5614 | +241, línia idèntica |
| 13 | `TechSheetEditor.jsx` `cotaLabelDe` | MOGUT | 276 | +25, línia idèntica |
| 14 | `CheckMeasureEditor.jsx` `lineByPom` | IGUAL | 217-218 | +19 al fitxer, tots després |
| 15 | `measureSources.jsx` `pomMap` | IGUAL | 18-27 | fitxer intocat |
| 16 | `fittingGridAdapter.jsx` `lineId` | MOGUT | 144 | +4, línia idèntica |
| **N1** | `graded_spec_views.py` `bateig_map` | **NOU** | 95-98 · 116-118 | BaseMeasurement · sprint NOMS-POM/R1 |
| **N2** | `repas_views.py` `bateig_map` | **NOU** | 259 · 276-277 | BaseMeasurement · sprint NOMS-POM/R1 |
| **N3** | `services_size_check.py` `ja_hi_son` | **NOU** | 35-40 | SizeCheckLine × BaseMeasurement · FIX-3 |
| **N4** | `views.py` `_sembra_step_des_dels_specs` | **NOU** | 3962-3964 | GradedSpec · sprint STEP |
| **X1** | `views.py` `base_stages_view` `changes_by_ev` | NO CENSAT (preexistent) | 2992 · 3000 · 3004 | ja hi era a `98c0982e` |

**Recompte:** 12 IGUAL · 8 MOGUT · **0 CANVIAT** · **0 DESAPAREGUT** · **4 NOUS** · 1 no censat.

---

## VEREDICTE

> **DELTA NO TRIVIAL** — cap dels 20 nodes ha canviat de forma ni ha desaparegut (8 només
> s'han desplaçat, amb la línia idèntica), però hi ha **4 lectors per-POM NOUS**
> (`graded_spec_views:95`, `repas_views:259`, `services_size_check:35`, `views:3962`) i **1
> lector preexistent fora del cens** (`base_stages_view`), i cap dels cinc no és a la llista
> de línies de l'Onada 1.
