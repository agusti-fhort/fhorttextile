> ⚠️ SUPERADA 2026-07-28 — codi resolt: graded-table exposa `increment_base`/`talla_break_label`
> per fila (a9666421) i `rowDelta`/`breakResum` llegeixen la regla declarada (abaf8f8e).
> **Queda pendent el gest de dades**: re-inserir les 4 taules T1b congelades (§4.3, models 163,
> 166, 177, 195) — cap recàlcul les toca. Consulta només com a històric.

# DIAGNOSI — La columna Δ de la taula de grading de la fitxa

**Data:** 2026-07-28 · **Entorn:** PROD `/var/www/fhort-textile` · **Mode:** read-only absolut
**Cas:** model **163** (`BRW-FW26-0001` Blusa TATE Crudo, tenant `fhort`), fitxa tècnica: Δ pinta
−4 (A), −2.4 (E2), −2 (E), −1 (EK) quan les regles diuen 2 · 1.2 · 1 · 0.5. Break: «XS · S · …».

**Res escrit:** cap `INSERT`/`UPDATE`/`DELETE`, cap `POST`/`PATCH`, cap fitxer del repo tocat, cap
restart. Els `.ftt` s'han obert amb `load_document` (lectura del FileField).

---

## VEREDICTE

> **La taula que porta Δ no és la T1a: és la T1b.** La T1a **no té columna Δ** — la seva columna
> «Regla/Δ» ja fa el correcte.
>
> **El bug és `rowDelta()` (`TechSheetEditor.jsx:686-693`): confon el DELTA ACUMULAT vs la talla
> base amb l'INCREMENT PER SALT.** Pinta `increment_applied_cm` de la **primera talla no-base de
> `size_labels`** — que a TATE és XXS, dos salts per sota → **−2× l'increment real**.
>
> **La mateixa arrel produeix el Break espuri:** com que els deltes acumulats **canvien a cada
> talla per construcció**, `esBreak` els marca **totes**. TATE té **0 regles amb break real** i la
> taula en pinta **18 de 23**.
>
> **NO és el camí F1 d'ahir.** El model 163 té `grading_rule_set_id = 146` — és el camí RULESET. El
> defecte és a la lectura de `graded-table`, comuna als dos camins, i data d'`aae7d5c`, molt
> anterior. **Afecta els dos camins per igual.**

---

## D1 · D'ON SURT EL Δ QUE ES PINTA

### 1.1 · Correcció de premissa: la T1a no té Δ

`insertTableT1a` (`frontend/src/pages/TechSheetEditor.jsx:4546-4555`) declara **vuit** columnes:

```js
{ key: 'ref' }, { key: 'pom' }, { key: 'base' }, { key: 'rule' },
{ key: 'break' }, { key: 'tol' }, { key: 'nova' }, { key: 'coment' }
```

**Cap `delta`.** La columna `rule` porta l'etiqueta **«Regla/Δ»** (`i18n/ca.json:2878`) — d'aquí ve
la confusió de nom. I el que hi posa és **correcte** (`TechSheetEditor.jsx:4564-4565`):

```js
fmtMeasure(rule?.increment_base, unit) ?? '',   // ← l'increment PER SALT, de la regla
rule?.talla_break_label || '',                  // ← el break DECLARAT a la regla
```

La columna `delta` amb capçalera `Δ` només existeix a **`insertTableT1b`**
(`TechSheetEditor.jsx:4613`), i el Break de la T1b és una **llista** calculada
(`breakResum`, `:4626-4628`) — que és exactament el format «XS · S · …» que s'ha vist. **La taula
inserida a TATE és la T1b.**

### 1.2 · El càlcul: no recalcula restant columnes, però tampoc llegeix la regla

**`TechSheetEditor.jsx:684-693`** — el codi sencer:

```js
// Delta de fila = increment de la GradingRule: primer increment no-zero de talla no-base.
// Tots 0 (grading FIXED) → '—'. Signe explícit (+1 / −0.5).
function rowDelta(row, baseSize, sizes) {
  for (const sl of sizes) {
    if (sl === baseSize) continue
    const d = row.deltas?.[sl]
    if (d && d !== 0) return d > 0 ? `+${d}` : `${String(d).replace('-', '−')}`
  }
  return '—'
}
```

**El comentari diu «increment de la GradingRule». El codi llegeix `row.deltas`.** No són el
mateix, i aquí és exactament on es trenca:

- **NO** recalcula restant valors de columnes.
- **NO** llegeix `increment_base` de cap regla (ni ruleset ni `ModelGradingRule`).
- **SÍ** llegeix `row.deltas[size_label]`, que ve del backend.

### 1.3 · Què és `deltas` — la cadena sencera

`backend/fhort/fitting/graded_spec_views.py:69,74`:

```python
'deltas': {},   # TS-4a: increment_applied_cm per talla (delta vs base)
...
rows_by_pom[pom.id]['deltas'][s.size_label] = float(s.increment_applied_cm or 0)
```

I `increment_applied_cm` el produeix el motor a **`backend/fhort/pom/services.py:281-290`**:

```python
graded_val = round(graded_val, 2)
increment = round(graded_val - base_val, 2)      # ← ACUMULAT vs la BASE, no per salt
_upsert_graded_spec(..., increment_applied_cm=increment, ...)
```

La semàntica està **declarada com a invariant** a dos llocs més:

- `backend/fhort/patterns/engine/ports.py:64`
  ```python
  delta_cm: float      # increment_applied_cm — DELTA vs la base. **+ = talla MÉS GRAN**
  ```
- `backend/fhort/patterns/engine/grading_projection.py:29`
  ```
  mesura(talla) − mesura(base) == increment_applied_cm(talla)
  ```

→ **`deltas[talla]` és la distància acumulada a la base, no l'increment per salt.**
`rowDelta` agafa la primera talla no-base de `size_labels` i en pinta l'acumulat com si fos el pas.

### 1.4 · El Break — mateixa arrel

`TechSheetEditor.jsx:4617-4628`:

```js
// Break = talla on el delta CANVIA respecte a la talla anterior (ordre de size_labels).
const esBreak = (row, sl, prevSl) => {
  const d = row.deltas?.[sl]
  const dPrev = prevSl != null ? row.deltas?.[prevSl] : undefined
  return prevSl != null && d != null && dPrev != null && d !== dPrev
}
const breakResum = (row) => sizeLabels
  .filter((sl, si) => esBreak(row, sl, si > 0 ? sizeLabels[si - 1] : null))
  .join(' · ')
```

La premissa («el delta canvia») **només seria certa amb deltes PER SALT**. Amb deltes acumulats,
una LINEAR pura dona −4 · −2 · 0 · +2 · +4: **tots diferents del seu anterior**. `esBreak` és cert
a **totes** les talles menys la primera → **el Break es pinta sempre**, hi hagi break o no.

El break REAL viu a `ModelGradingRule.talla_break_label` / `GradingRule.talla_break_label` — que és
el que la **T1a** llegeix (`:4565`) i el que fa la pantalla de RuleSets (`GradingRuleSets.jsx:548`).

**El Δ i el Break de la T1b no depenen de cap servei backend nou: tots dos els calcula el frontend
a la inserció, sobre el payload de `GET /api/v1/fitting/<sf>/graded-table/` (`:4597`).**

---

## D2 · LA FONT DE TATE — i quin camí afecta

### 2.1 · TATE grada per RULESET, no per regles residents

```
MODEL 163 = BRW-FW26-0001 Blusa TATE Crudo
  base_size_label     = S
  size_run_model      = XXS·XS·S·M·L        ← la base és la 3a de 5: DUES talles per sota
  grading_rule_set_id = 146                 ← camí RULESET (NO és el camí F1)
  ModelGradingRule    = 23 · BaseMeasurement = 26
  SizeFitting: 53 (BRW-FW26-0001-SF1, TallesGenerades) · 73 i 1058 (IMP-…, sense GradingVersion)
  sf 53 → gv 48 «Propagació conscient» · 115 specs actius
```

### 2.2 · Les regles reals contra el que es pinta

| POM (`nom_fitxa`) | `ModelGradingRule` | XXS | XS | **S (base)** | M | L | Δ **pintat** | Δ **correcte** |
|---|---|---|---|---|---|---|---|---|
| **A** Chest width | LINEAR `increment_base=2.00`, break=None | −4.0 | −2.0 | **0.0** | +2.0 | +4.0 | **−4** ❌ | **+2** |
| **E2** Thorax width front | LINEAR `1.20`, break=None | −2.4 | −1.2 | **0.0** | +1.2 | +2.4 | **−2.4** ❌ | **+1.2** |
| **E** Shoulder to shoulder | LINEAR `1.00`, break=None | −2.0 | −1.0 | **0.0** | +1.0 | +2.0 | **−2** ❌ | **+1** |
| **EK** Neck width | LINEAR `0.50`, break=None | −1.0 | −0.5 | **0.0** | +0.5 | +1.0 | **−1** ❌ | **+0.5** |

Els valors absoluts són **correctes** (A: 43 · 45 · 47 · 49 · 51, pas de +2 a cada salt). **El motor
gradua bé; només la casella Δ menteix.**

### 2.3 · Reproducció read-only del render sencer

`GET /api/v1/fitting/53/graded-table/` → 200, `base_size='S'`,
`size_labels=['XXS','XS','S','M','L']`. Aplicant `rowDelta` i `breakResum` verbatim:

| REF | POM | `deltas` | **Δ pintat** | **Break pintat** |
|---|---|---|---|---|
| A | Chest width | [−4, −2, 0, +2, +4] | **−4** | **XS · S · M · L** |
| D | Skirt sweep | [−4, −2, 0, +2, +4] | **−4** | **XS · S · M · L** |
| G1 | RIB HEIGHT | [0, 0, 0, 0, 0] | — | (buit) |
| E2 | THORAX WIDTH IN FRONT | [−2.4, −1.2, 0, +1.2, +2.4] | **−2.4** | **XS · S · M · L** |
| E | SHOULDER TO SHOULDER | [−2, −1, 0, +1, +2] | **−2** | **XS · S · M · L** |
| EK | Neck width | [−1, −0.5, 0, +0.5, +1] | **−1** | **XS · S · M · L** |

```
files de la taula          = 23
regles amb break REAL      = 0      ← CAP regla de TATE té talla_break_label
files amb Break PINTAT     = 18
files amb Δ negatiu pintat = 18
```

**Coincidència exacta amb el que es va veure a la fitxa.** Les 5 files restants són POMs amb delta
0 (regla ZERO/FIXED): Δ = '—' i Break buit — l'únic cas que surt bé, i per casualitat.

### 2.4 · Quin camí afecta: **TOTS DOS**

`rowDelta` llegeix `deltas`, que surt de `GradedSpec.increment_applied_cm`. El motor
(`pom/services.py:281`) escriu aquest camp **igual** vingui la regla d'un `GradingRuleSet` o d'un
`ModelGradingRule` resident: la font de la regla es resol **aigües amunt**, i el que arriba a
`GradedSpec` ja és el resultat. **`graded-table` no sap ni li importa d'on venia la regla.**

- **TATE (163) és camí RULESET** (`grading_rule_set_id=146`) i **falla**.
- El camí F1 fallaria idènticament: la seva T1b llegiria el mateix `graded-table`.
- **F1 (`06d3e13`, ahir 17:38) no hi té res a veure**: només va tocar `insertTableT1a` — la taula
  **sense** columna Δ.

**Data del defecte:** `git log -S "function rowDelta"` → **`aae7d5c` · «TS-4a-fix: delta columna
única (GradingRule)»**. El títol del commit declara la intenció (*GradingRule*) i el codi llegeix
`deltas`. **El bug és tan antic com la columna.**

---

## D3 · EL SIGNE I LA REFERÈNCIA — la convenció de la casa

### 3.1 · La referència canònica

**`frontend/src/pages/GradingRuleSets.jsx:520-529`** — la pantalla de regles, que és on el domini
declara la forma:

```jsx
{/* Δ/talla — Peça A: forma canònica (increment_base) com a TEXT read-only;
    regles no backfillades (increment_base null) → escalar editable (compat). */}
...
{r.increment_base != null
  ? (Number(r.increment_base) > 0 ? `+${Number(r.increment_base)} cm` : '—')
  : …}
```

I el Break, tres línies més avall (`:545-548`), surt de **`r.talla_break_label`** — **declarat, mai
deduït**.

### 3.2 · La convenció, en una frase

> **Δ = `increment_base` de la regla: l'increment PER SALT ASCENDENT, sempre positiu, amb signe
> `+` explícit i unitat. Break = `talla_break_label` de la regla, tal com està declarat.**

Concorda amb les tres fonts que ja ho fan bé:

| Superfície | Δ | Break | Cita |
|---|---|---|---|
| Pantalla de RuleSets | `+2 cm` | `talla_break_label` | `GradingRuleSets.jsx:528-529, 548` |
| **T1a de la fitxa** | `increment_base` | `talla_break_label` | `TechSheetEditor.jsx:4564-4565` |
| PDF de DALIA (d'ahir) | `+1` / `+0.2` | — | mateix camí T1a |
| **T1b de la fitxa** | ❌ `increment_applied_cm` de la 1a talla no-base | ❌ recalculat | `TechSheetEditor.jsx:686-693, 4617-4628` |

**El fix ja està escrit al mateix fitxer, seixanta línies més avall.** La T1a és la implementació
correcta de la mateixa idea.

### 3.3 · La regla general del defecte (més precisa que «−2×»)

El Δ pintat és:

```
increment_applied_cm(primera talla no-base de size_labels)
  = (distància en salts d'aquella talla a la base) × increment_base   [amb el signe de la direcció]
```

**Només és correcte quan la primera talla no-base de `size_labels` és exactament UN salt PER SOBRE
de la base.** En qualsevol altre cas és un múltiple enter erroni — i el signe depèn de l'ordre en
què el backend serveix les talles, no del domini. **Es confirma amb dades reals** (§D4): el model
166 té la mateixa base i el mateix run que TATE i pinta **`+8`** — quatre vegades l'increment i amb
el signe contrari, perquè al seu document `size_labels` arribava en un altre ordre.

**El «−2×» del cas TATE és la instància, no la llei.**

---

## D4 · RADI — quantes fitxes vigents porten el Δ mal calculat

### 4.1 · ¿Congelat o recalculat? **Les DUES coses, segons l'objecte**

| Objecte | Com es dibuixa | Δ | El fix el cura? |
|---|---|---|---|
| `type:'table'`, `kind:'pom_grading'` (**T1b**) | `buildTableCellPrimitives(obj)` (`:753-838`) llegeix **`obj.rows`**, strings ja resolts | **CONGELAT** al `.ftt` | **NO** |
| `type:'data_block'`, `kind:'graded_table'` (**legacy**) | `buildTablePrimitives(d)` (`:698-747`) crida **`rowDelta` en viu** (`:743`) sobre el JSON re-baixat a l'obrir (`:3132-3147`) | **EN VIU** | **SÍ** |
| `type:'table'`, `kind:'pom_fitting'` (**T1a**) | — | **cap columna Δ** | n/a |

La congelació de la T1b és deliberada i està declarada a `TechSheetEditor.jsx:4588-4592`
(*«Snapshot congelat: només afecta reinsercions»*): `filesDe` (`:4629-4635`) produeix **strings** i
`serializePages` els desa tal qual.

### 4.2 · Escombrada de tots els `.ftt` vigents

| | `fhort` | `los` |
|---|---|---|
| Documents `.ftt` vigents | **17** | **2** |
| Taules **T1b** (`pom_grading`, Δ congelat) | **4** | 0 |
| Taules **T1a** (`pom_fitting`, sense Δ) | 2 | 1 |
| Blocs **legacy** (`graded_table`, Δ en viu) | **1** | 0 |
| Documents il·legibles | 0 | 0 |

### 4.3 · Els documents afectats — **4 de 4 taules T1b estan malament**

| model | codi | `ModelFitxer` | v | base / run | salts sota base | Δ pintat (fila A) | Break | Cal re-inserir? |
|---|---|---|---|---|---|---|---|---|
| **163** | BRW-FW26-0001 (TATE) | **478** | 8 | S / XXS·XS·S·M·L | 2 | **−4** (real +2) | **`XS · S · M · L`** espuri | **SÍ** |
| **166** | BRW-FW26-0004 | **183** | 89 | S / XXS·XS·S·M·L | 2 | **+8** (real +2) | *(sense columna)* | **SÍ** |
| **177** | BRW-FW26-0015 | **87** | 10 | S / XS·S·M | 1 | **−3** | *(sense columna)* | **SÍ** |
| **195** | BRW-FW26-0024 | **72** | 10 | S / XXS·XS·S·M·L | 2 | **−5** | *(sense columna)* | **SÍ** |

**Cap se salva.** El 166 no surt a un filtre de «Δ negatiu» perquè el seu error és **positiu i
quàdruple** — motiu pel qual la §3.3 formula la llei i no el «−2×».

Tres dels quatre documents (166, 177, 195) són **anteriors a `aec0b79`** i **no tenen columna
Break**; només el de TATE (478, v8) la porta, i per això és l'únic amb el símptoma doble.

### 4.4 · El document que es cura sol

| model | codi | `ModelFitxer` | v | objecte | Δ |
|---|---|---|---|---|---|
| 178 | LOS-SS26-0001 | **11** | 1 | 1 bloc `graded_table` legacy | **es recalcula a cada obertura** → **el fix el cura sense tocar-lo** |

### 4.5 · Les taules T1a: **no afectades**

3 taules `pom_fitting` (2 a `fhort`, 1 a `los`). **No tenen columna Δ** i la seva «Regla/Δ» ja
llegeix `increment_base`. **Cap acció.**

---

## DIMENSIONAT DEL FIX

### Codi — **S**

| Peça | Cost | Detall |
|---|---|---|
| `rowDelta` ha de rebre l'increment per salt | **S** | `TechSheetEditor.jsx:686-693`. **La dada NO és al payload de `graded-table`**: cal o bé afegir-hi `increment_base` per fila (`fitting/graded_spec_views.py:59-71`, ~3 línies, mateix patró que `ordre`/`nom_fitxa` a `:82-84`), o bé derivar-la del delta acumulat dividint pels salts. **La primera és la bona** — la segona torna a deduir el que ja està declarat. |
| `esBreak`/`breakResum` han de llegir el break declarat | **S** | `TechSheetEditor.jsx:4617-4628` → substituir el càlcul per `talla_break_label`, com fa la T1a a `:4565`. Necessita el mateix afegit al payload. |
| Backend: exposar `increment_base` i `talla_break_label` per fila | **S** | `fitting/graded_spec_views.py`. La vista **ja** creua `BaseMeasurement` per model (`:82`); afegir-hi la regla és el mateix patró. **Sense migració.** |
| Alinear el format amb la casa | **S** | `+2 cm` amb signe explícit (`GradingRuleSets.jsx:529`). Avui la T1a fa `fmtMeasure(increment_base)` → «2» sense `+`. **Divergència menor anotada**, no bloquejant. |
| **Total** | **S** | ~15 línies en 2 fitxers. **Sense migració.** |

> ⚠️ **`rowDelta` té DOS consumidors** (`:743` render legacy i `:4633` inserció T1b). Canviar-ne la
> signatura els toca tots dos. El de `:743` es beneficia del fix immediatament (§4.4).

### Dades — re-inserció manual

**Cal, i no hi ha drecera.** Els strings són al `.ftt`; cap recàlcul els toca.

| # | model | codi | fitxa `.ftt` | acció |
|---|---|---|---|---|
| 1 | **163** | BRW-FW26-0001 (TATE) | 478 (v8) | esborrar la taula T1b i tornar-la a inserir |
| 2 | 166 | BRW-FW26-0004 | 183 (v89) | ídem |
| 3 | 177 | BRW-FW26-0015 | 87 (v10) | ídem |
| 4 | 195 | BRW-FW26-0024 | 72 (v10) | ídem |

**4 taules, 4 documents, tots a `fhort`. `los` no en té cap.** Cada re-inserció crea una versió
nova de la cadena (`save_document`), que és el comportament normal de l'editor: **no cal cap
data-op, cap SQL, cap migració** — són quatre gestos a la UI **després** de desplegar el fix.

---

## LÍMITS — el que no s'ha pogut verificar sense escriure

1. **No s'ha inserit cap taula.** El render s'ha reproduït replicant `rowDelta`/`esBreak`/
   `breakResum` **verbatim en Python** sobre la resposta real de `graded-table`. Coincideix amb el
   símptoma reportat fila a fila, però **no és el JS executant-se**.
2. **Per què el model 166 va rebre `size_labels` en un altre ordre** no s'ha investigat. El fet és
   ferm (Δ=`+8` amb base S i run XXS·XS·S·M·L al document desat); la causa —regeneració amb un
   altre ordre d'`id` de spec, o una versió anterior del serialitzador— queda oberta. **Reforça el
   veredicte** (l'ordre de `size_labels` no és contracte), no el debilita.
3. **Només s'han escombrat els `.ftt` `is_current=True`.** Les versions anteriors de cada cadena
   (TATE en té 8) poden portar més taules amb el mateix defecte; **no s'han comptat** perquè no són
   el que ningú obre.
4. **Els `.ftt` de `public`/SYS no s'han mirat** (no és tenant de treball), ni les
   `DocumentTemplate` del tenant: **una plantilla amb una T1b congelada propagaria el Δ dolent a
   cada document nou que s'hi instanciï**. No s'ha comprovat si n'hi ha cap.
5. **La columna «Regla/Δ» de la T1a no s'ha validat contra el PDF exportat** — s'ha llegit el codi
   (`:4564`) i s'ha confirmat que llegeix `increment_base`, no s'ha vist imprès a TATE (les seves 2
   taules T1a són a altres models).
6. **`GradingRule` (ruleset) vs `ModelGradingRule` (resident):** la taula de §2.2 llegeix les
   **residents**, que a TATE existeixen (23) tot i tenir ruleset. Els valors coincideixen amb els
   specs generats, així que són les que van manar — però **quina de les dues fonts va usar el motor
   a la gv 48 no s'ha traçat**; és irrellevant per al bug (§2.4) i no s'ha perseguit.

---

## Índex de comprovacions (fitxer:línia)

**D1** — `TechSheetEditor.jsx:684-693` (**`rowDelta`**), `:4546-4555` (columnes T1a),
`:4564-4565` (T1a correcta), `:4597` (fetch graded-table), `:4604-4616` (columnes T1b),
`:4617-4628` (`esBreak`/`breakResum`), `:4629-4635` (`filesDe`), `:743` (render legacy) ·
`fitting/graded_spec_views.py:59-71, 74, 82-91` · `pom/services.py:281-290` ·
`patterns/engine/ports.py:64` · `patterns/engine/grading_projection.py:20-29`

**D2** — dades de `fhort`: `Model 163` (`base_size_label='S'`, `size_run_model='XXS·XS·S·M·L'`,
`grading_rule_set_id=146`), `ModelGradingRule` de `pom_id` 273/459/457/301, `GradedSpec` de la
`gv 48` · `06d3e13` (F1, només `insertTableT1a`) · `aae7d5c` (naixement de `rowDelta`)

**D3** — `GradingRuleSets.jsx:520-529` (Δ canònic), `:545-548` (Break canònic) ·
`TechSheetEditor.jsx:4564-4565` · `i18n/ca.json:2877-2879` · `pages/fittingShared.jsx:29-34`
(`fmtMeasure`, sense signe)

**D4** — `TechSheetEditor.jsx:753-838` (`buildTableCellPrimitives`, congelat), `:698-747`
(`buildTablePrimitives`, en viu), `:3132-3147` (re-fetch dels `graded_table`), `:1727-1737`
(`serializePages`), `:4588-4592` (declaració del snapshot congelat) ·
`models_app/services_ftt_document.py:453-460` (`load_document`) · escombrada dels 19 `.ftt`
vigents de `fhort` + `los`
