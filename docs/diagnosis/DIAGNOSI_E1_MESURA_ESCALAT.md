# DIAGNOSI E1 — Presa de mesures a l'Escalat (fit actual per talla)

> **Patró A · READ-ONLY.** Cap escriptura a BD, cap fitxer del repo modificat, cap worktree obert.
> **Data:** 2026-08-17 · **Substrat:** `ftt-staging`, branca `dev`, HEAD `254c8938`
> **⚠️ Estat del substrat:** el working tree té la feina NO COMMITADA d'una sessió concurrent
> (Patró B · F1 + Q1-bis). Tot el que es cita aquí és l'estat **POST-F1 al disc**, que és el que
> es construirà a sobre. El que corre a staging és un altre (v. §7.3).
>
> **Reorientació (addendum d'Agus, Patró C):** la hipòtesi «contracte estès vs illa nova» queda
> substituïda pel **flux de dos passos**, que no és una opció sinó LA forma. Aquest document en
> verifica la viabilitat (QA·QB·QC·QD) i manté Q1, Q5 i Q6.

---

## §0 · La forma decidida, dita amb els noms del codi

```
PAS 1 — ESCALAT · columna «Fit actual»          PAS 2 — «MESURAR PRENDA»
  pantalla: /models/:id  tab Escalat              pantalla: /models/:id  tab Mesures (editing)
  component: PropagatedEditor.jsx                 component: CheckMeasureEditor.jsx + fittingSource
  totes les talles del run, base inclosa          NOMÉS la talla base
  → s'hi anota la peça FÍSICA arribada            → acceptar/ajustar/rebutjar + propagació
```

Dues precisions de nomenclatura que canvien el que es pot reutilitzar (llei: *anomena la pantalla
per ruta + sub-vista, mai pel concepte*):

- **«Mesurar prenda» NO és el Size Check.** El rètol `presa.titol` = «Mesurar prenda»
  ([ca.json:4784](../../frontend/src/i18n/ca.json#L4784)) penja del botó ③
  [ModelSheet.jsx:1279-1286](../../frontend/src/pages/ModelSheet.jsx#L1279-L1286), que fa
  `enterEdit('Mesures','size_check')`. `size_check` és el **codi de TASCA**, no la superfície:
  el botó exigeix una `FittingSession` abans d'entrar ([ModelSheet.jsx:447-457](../../frontend/src/pages/ModelSheet.jsx#L447-L457))
  i el muntatge passa `source = fittingSession ? fittingSource : null`
  ([ModelSheet.jsx:1314-1320](../../frontend/src/pages/ModelSheet.jsx#L1314-L1320)).
  → **La superfície real de «Mesurar prenda» és `fittingSource`** ([measureSources.jsx:66-122](../../frontend/src/components/model/measureSources.jsx#L66-L122)):
  `PieceFitting` / `PieceFittingLine`, amb el veredicte ACCEPTED·ADJUSTED·REJECTED.
  La font `checkSource` (SizeCheck, `EditableTable`, decisió `tolerancia_acceptada`/`valor_descartat`)
  és el **fallback sense sessió** i la consulta read-only.
  Conseqüència directa: **el brief tenia raó** en dir que els tres estats són «els de Mesurar
  prenda» — viuen a [fitting/models.py:451-463](../../backend/fhort/fitting/models.py#L451-L463),
  no al SizeCheck.
- **Obrir «Mesurar prenda» ÉS UNA ESCRIPTURA.** `sessioDeFitting`
  ([ModelSheet.jsx:392-406](../../frontend/src/pages/ModelSheet.jsx#L392-L406)) crea una
  `FittingSession` amb `scheduleNow` si no n'hi ha cap viva, i `resolvePieceFitting`
  ([measureSources.jsx:47-64](../../frontend/src/components/model/measureSources.jsx#L47-L64))
  crea la `PieceFitting`, que **clona TOTS els `GradedSpec` a `PieceFittingLine`**
  ([fitting/services.py:329-353](../../backend/fhort/fitting/services.py#L329-L353)).
  El pas 2 del flux no és una pantalla de lectura: materialitza sessió + peça + N línies.
  Això mana sobre QB (§3).

---

## §1 · Q1 — Què fa avui la columna FIT ACTUAL de l'Escalat

### 1.1 El camí complet, front → back → taula

| # | Punt | Fitxer:línia |
|---|------|--------------|
| ① | Font de dades | `GET /api/v1/models/<id>/taula-mesures/` → [PropagatedEditor.jsx:32](../../frontend/src/pages/PropagatedEditor.jsx#L32) · vista [models_app/views.py:1982](../../backend/fhort/models_app/views.py#L1982) |
| ② | Construcció de cel·les | [fittingGridAdapter.jsx:358-393](../../frontend/src/components/model/fittingGridAdapter.jsx#L358-L393) |
| ③ | Guardes + despatx | [PropagatedEditor.jsx:102-124](../../frontend/src/pages/PropagatedEditor.jsx#L102-L124) (no-op · plausibilitat) |
| ④ | Escriptura | [PropagatedEditor.jsx:73-98](../../frontend/src/pages/PropagatedEditor.jsx#L73-L98) → `models.escalatAjustarTalla` [endpoints.js:165-168](../../frontend/src/api/endpoints.js#L165-L168) |
| ⑤ | Vista | `POST /api/v1/models/<id>/escalat/ajustar-talla/` → [models_app/views.py:3327](../../backend/fhort/models_app/views.py#L3327) |
| ⑥ | Taules escrites | v. 1.3 |

### 1.2 Què conté la cel·la avui (i per què NO és una presa)

[fittingGridAdapter.jsx:362-367](../../frontend/src/components/model/fittingGridAdapter.jsx#L362-L367):

```js
const v = s === baseLabel ? row.base_value_cm : (row.graded?.[s] ?? null)
cells[s] = { history: { vigent: v },
             active: { lineId: `${row.clau}:${s}`, value: v == null ? '' : v, baseValue: v } }
```

- La columna `history.vigent` («Base») i la columna activa («Fit actual», rètol
  `fitting.grid.fit_current` — [fittingGridAdapter.jsx:353](../../frontend/src/components/model/fittingGridAdapter.jsx#L353))
  **surten del MATEIX valor**: la corba teòrica vigent (`base_value_cm` a la base, `GradedSpec` a la resta).
- **No hi ha cap magatzem de «valor mesurat»**: escriure-hi reescriu la teòrica.
  El sistema **no distingeix avui «valor teòric del motor» de «valor mesurat de la peça arribada»**
  a l'Escalat. La distinció existeix, però només al fitting (`valor_teoric` vs `valor_real`,
  [fitting/models.py:437-438](../../backend/fhort/fitting/models.py#L437-L438)) i al size check
  ([models_app/models.py:1449-1450](../../backend/fhort/models_app/models.py#L1449-L1450)).
- **R1 avui és un mirall.** El vermell de la cel·la el fa `isModified(value, baseValue)`
  ([MeasureGrid.jsx:49-50](../../frontend/src/components/model/MeasureGrid.jsx#L49-L50) i
  [:77-84](../../frontend/src/components/model/MeasureGrid.jsx#L77-L84)) i, com que `value === baseValue`
  en carregar, la cel·la neix **mai vermella**, es posa vermella mentre teclejes i **torna a apagar-se
  després de desar i rellegir** (el nou valor ja és la teòrica). La banda de tolerància
  (`active.tol`, [MeasureGrid.jsx:80-83](../../frontend/src/components/model/MeasureGrid.jsx#L80-L83))
  **només la sembra la font `check`** ([CheckMeasureEditor.jsx:322](../../frontend/src/components/model/CheckMeasureEditor.jsx#L322));
  l'Escalat no en passa cap. → **R1 no existeix a l'Escalat, ni tan sols a mitges.**

### 1.3 On escriu, exactament

[models_app/views.py:3431-3492](../../backend/fhort/models_app/views.py#L3431-L3492), tres branques
segons règim i talla:

| Branca | Condició | Escriu |
|---|---|---|
| A · propaga | `rule` i `logica != STEP` i (canònic o LINEAR) — [:3429](../../backend/fhort/models_app/views.py#L3429) | `propaga_ancoratges` → nova base → **`BaseMeasurement`** via `_write_base` [:3449](../../backend/fhort/models_app/views.py#L3449) + **`.delete()` de tots els `ModelGradingOverride`** de la mesura [:3460-3462](../../backend/fhort/models_app/views.py#L3460-L3462) |
| B · base sense LINEAR | `talla == base_size` [:3464](../../backend/fhort/models_app/views.py#L3464) | **`BaseMeasurement`** via `_write_base` |
| C · pin puntual | STEP/FIXED/ZERO/sense regla, talla no-base | **`ModelGradingOverride`** upsert [:3480-3485](../../backend/fhort/models_app/views.py#L3480-L3485) + **`MeasurementChangeLog`** [:3487-3491](../../backend/fhort/models_app/views.py#L3487-L3491) |
| totes | sempre | **`GradedSpec`** re-derivat: `generate_graded_specs(sf.id)` [:3495](../../backend/fhort/models_app/views.py#L3495) |

`_write_base` ([models_app/views.py:3734-3782](../../backend/fhort/models_app/views.py#L3734-L3782))
fa `get_or_create` per `(model, pom, capa, instancia, garment)` i desa; el senyal F1
([models_app/signals.py:254](../../backend/fhort/models_app/signals.py#L254)) hi escriu el
`MeasurementChangeLog`.

### 1.4 Què desa: valor sol, procedència, moment, autor

| Dada | Branca A/B (base) | Branca C (no-base) |
|---|---|---|
| valor | `BaseMeasurement.base_value_cm` | `ModelGradingOverride.value_cm` |
| procedència | `origen` **NO es toca** (només al `defaults` d'una creació, `'STANDARD'`) | `motiu = 'Escalat · ajust talla (sense propagació)'` |
| moment | `BaseMeasurement.updated_at` (auto_now, **sobreescrit**) + `MeasurementChangeLog.created_at` (append-only) | `ModelGradingOverride.created_at` (**no** s'actualitza a l'upsert) + `MeasurementChangeLog.created_at` |
| autor | `_changed_by` → `MeasurementChangeLog.created_by` | `created_by` (perfil) + log |
| talla | **implícita** (és la base) | `size_label` |

🔑 **L'únic rastre que conserva la seqüència és el `MeasurementChangeLog`** (append-only,
[models_app/models.py:1020-1027](../../backend/fhort/models_app/models.py#L1020-L1027)), i hi entra
amb `base_measurement=NULL` per a les talles no-base — el senyal que `base_stages_view` fa servir
per no barrejar-los amb les preses de base ([models_app/views.py:3981-3992](../../backend/fhort/models_app/views.py#L3981-L3992)).

**Veredicte Q1:** la columna «Fit actual» de l'Escalat és, avui, **un editor de la corba teòrica**
amb rètol de presa. No sap dir «arribada», no sap dir «quan», no sap dir «acceptada», i el que
escriu és exactament allò contra el que s'hauria de comparar.

---

## §2 · QA — «Mesurar prenda» pot carregar-se amb abast d'UNA talla?

**Ja hi és. L'abast d'una sola talla —la base— és el que fa avui, i està clavat a TRES llocs
consistents. Cost del paràmetre: zero, perquè no cal cap paràmetre.**

| Capa | Punt | Mecanisme |
|---|---|---|
| Payload | [fitting/serializers.py:327](../../backend/fhort/fitting/serializers.py#L327) `obj.linies…all()` | **serveix TOTES les talles** (no filtra) |
| Projecció front | [measureSources.jsx:15-43](../../frontend/src/components/model/measureSources.jsx#L15-L43) `deriveFitting` + [:94](../../frontend/src/components/model/measureSources.jsx#L94) `buildFittingGroups(raw.baseLabel, …)` | **UN sol grup**: `model.base_size_label`. Sense base → `[]` ([fittingGridAdapter.jsx:63-64](../../frontend/src/components/model/fittingGridAdapter.jsx#L63-L64)) |
| Guard d'escriptura | [fitting/views.py:604-607](../../backend/fhort/fitting/views.py#L604-L607) → [fitting/services.py:41-54](../../backend/fhort/fitting/services.py#L41-L54) | **400** a tota escriptura de línia no-base (`partial_update` **i** `propagar`) |
| Consolidació | [fitting/services.py:515-516](../../backend/fhort/fitting/services.py#L515-L516) | `size_label != base_size` → `continue` |

Les quatre capes llegeixen **la mateixa font normalitzada igual**: `model.base_size_label` amb
`.strip()` als dos costats — condició escrita explícitament al docstring del guard
([fitting/services.py:44-46](../../backend/fhort/fitting/services.py#L44-L46)): *«si divergissin, la
vista acceptaria escriptures que el `close` descartaria en silenci»*.

**On és clavat l'abast, doncs:** a la **projecció** (front) i al **guard** (back), no a la query.
El backend continua enviant les N talles i el front en pinta una. Això és **bo per al flux**: el
pas 2 no necessita cap `?talla=`; ja **no pot** treballar cap altra talla.

⚠️ **Vora que no és de talla sinó de PEÇA:** `buildFittingGroups` retorna un grup per talla base,
però `CheckMeasureEditor` reparteix les files per contenidor de prenda
([CheckMeasureEditor.jsx:747-750](../../frontend/src/components/model/CheckMeasureEditor.jsx#L747-L750)).
Un model multipeça obre el pas 2 amb **totes les prendes**, cadascuna al seu contenidor. Si el pas 1
s'ha fet des del contenidor d'UNA peça, el pas 2 no hereta aquell abast. **No és un bloqueig; és
una decisió per a l'Agus** (§11-D3).

---

## §3 · QB — Pot hidratar valors que no venen de la seva pròpia presa?

**Sí — i la llei «res de localStorage» ja es compleix sola, perquè la hidratació és 100% de
servidor. El problema NO és el trasllat: és que el pas 1, tal com escriu avui, DESTRUEIX el
referent contra el qual el pas 2 hauria de comparar.**

### 3.1 Com hidrata avui el pas 2

`create_piece_fitting` ([fitting/services.py:329-353](../../backend/fhort/fitting/services.py#L329-L353)):

```python
PieceFittingLine.objects.create(…, valor_teoric=spec.graded_value_cm,
                                   valor_real=spec.graded_value_cm)  # còpia, editable
```

i `reconcilia_linies` fa el mateix per a les línies noves
([fitting/services.py:467-471](../../backend/fhort/fitting/services.py#L467-L471)).
→ **Els dos valors neixen iguals, clonats del `GradedSpec` del moment d'obrir.**

### 3.2 🚨 EL FORAT: el pas 1 es tapa amb ell mateix

Seqüència real amb el codi d'avui:

1. Pas 1: el tècnic escriu 52,0 a la cel·la **base** de «Fit actual» → branca A o B (§1.3) →
   `BaseMeasurement.base_value_cm = 52,0` **i** `generate_graded_specs` re-deriva tots els `GradedSpec`.
2. Pas 2: obrir «Mesurar prenda» crea la `PieceFitting` i clona els specs →
   `valor_teoric = 52,0`, `valor_real = 52,0`.
3. Resultat: **desviació zero**. `consolidate_base_from_fitting` fa
   `if abs(valor_real - valor_teoric) < 1e-6: continue`
   ([fitting/services.py:513-514](../../backend/fhort/fitting/services.py#L513-L514)) → **no consolida res**,
   perquè ja estava consolidat abans que ningú acceptés.

És exactament el patró de [[ftt-nom-local-que-repeteix-tapa-la-traduccio]]: **el forat es tapa amb
ell mateix**. R1 (vermell) no pot disparar mai, R2 (l'acceptació és a base) queda buida de
contingut —la base ja s'ha mogut al pas 1— i R3 no té tres valors sinó un repetit tres vegades.

### 3.3 «FIT ACTUAL persisteix amb identitat completa?» — la resposta camp a camp

| Eix requerit | Base (branca A/B) | No-base (branca C) |
|---|---|---|
| `pom` | ✅ `BaseMeasurement.pom` | ✅ `ModelGradingOverride.pom` |
| `capa` | ✅ | ✅ |
| `instancia` | ✅ | ✅ |
| `garment` | ✅ (des de F1, [views.py:3449-3451](../../backend/fhort/models_app/views.py#L3449-L3451)) | ✅ ([:3480-3482](../../backend/fhort/models_app/views.py#L3480-L3482)) |
| `talla` | ❌ **implícita** (la fila ÉS la base) | ✅ `size_label` |
| `moment` | ⚠️ només al log append-only | ⚠️ `created_at` no s'actualitza a l'upsert; el moment real només al log |
| **`estat`** (accepted/adjusted/rejected) | ❌ **no existeix** | ❌ **no existeix** |
| **«teòrica d'abans»** | ❌ es perd (sobreescrita) | ❌ el motor la recalcula |

**Què li falta, doncs, en una frase:** li falta **no ser la teòrica**. Els cinc eixos d'identitat
hi són tots; el que no hi ha és un lloc on una xifra pugui viure **al costat** de la teòrica en
comptes de **substituir-la**, amb estat i moment propis.

### 3.4 Els tres candidats de magatzem (sense decidir)

| Candidat | A favor | En contra |
|---|---|---|
| **①** `PieceFittingLine` amb `size_label` (ja el té!) | La taula **ja és exactament la forma demanada**: `valor_teoric` + `valor_real` + `decisio` ∈ {ACCEPTED, ADJUSTED, REJECTED} + `nota` + els tres eixos + `size_label`, i **ja hi ha una línia per talla** clonada dels specs. R3 surt de franc i és **literalment el mateix contracte**, no un de paral·lel | Obliga a **obrir el guard de no-base** ([fitting/services.py:41-54](../../backend/fhort/fitting/services.py#L41-L54)) per a l'escriptura del pas 1, i el guard és la peça que avui garanteix R2. Cal partir-lo en dos: **escriure ≠ acceptar**. Lliga el pas 1 a l'existència d'una `FittingSession` |
| **②** Taula nova `EscalatTake` (model, pom, capa, instancia, garment, size_label, valor, estat, moment, autor) | Cap col·lisió amb res viu; l'Escalat no depèn de cap sessió | Un **quart** magatzem de mesures (ja n'hi ha `BaseMeasurement`, `SizeCheckLine`, `PieceFittingLine`, `ModelGradingOverride`) → contradiu «no més pedaços: unificar el ja construït» (CLAUDE.md). Migració + 6 comportes d'eixos + serialitzadors + tests |
| **③** `ModelGradingOverride` amb un `motiu` especial | Zero migració | ☠️ **DESCARTAT PER RASTRE, no per gust**: «Propagar a grading» fa `ModelGradingOverride.objects.filter(model=model).delete()` ([models_app/views.py:3069](../../backend/fhort/models_app/views.py#L3069)) — la propagació que el pas 2 dispara **esborraria les preses que la justifiquen**. I l'override **alimenta el motor amb prioritat màxima** ([models_app/models.py:1042](../../backend/fhort/models_app/models.py#L1042)): una presa hi seria indistingible d'una decisió |

---

## §4 · QC — La propagació que dispara l'acceptació és l'estàndard? · FRONTERA G6

**Resposta binària: NO CAL TOCAR EL MOTOR. La frontera G6 no s'ha de creuar per aquest camí.**
Però hi ha una precisió que canvia el disseny del pas 2:

### 4.1 Acceptar ≠ propagar (D4, 2026-07-21)

**Avui, acceptar a «Mesurar prenda» NO propaga.** `close_piece_fitting`
([fitting/services.py:552-650](../../backend/fhort/fitting/services.py#L552-L650)):

1. `reconcilia_linies(pf)` — quadra amb el model viu;
2. `consolidate_base_from_fitting(pf)` — **només base**, només línies amb `valor_real ≠ valor_teoric`,
   **excloent REJECTED** ([fitting/services.py:506-509](../../backend/fhort/fitting/services.py#L506-L509))
   → `BaseMeasurement.base_value_cm`, `origen='FITTED'`, + derivació a germanes;
3. Welford;
4. `measurements_version += 1` — **i prou**. L'acta ho diu literal
   ([fitting/services.py:625-634](../../backend/fhort/fitting/services.py#L625-L634)): *«Tancar una
   peça de fitting ja NO propaga… Propagar és un acte conscient i té una sola porta»*.

La propagació és el **pas ④** del stepper
([ModelSheet.jsx:1294-1307](../../frontend/src/pages/ModelSheet.jsx#L1294-L1307))
→ `generate_grading_view` amb `new_version:true`
([models_app/views.py:3040-3113](../../backend/fhort/models_app/views.py#L3040-L3113)), que:
llenç net d'overrides → consolida fittings oberts → `bump_grading_version_and_generate(sf.id)`.

### 4.2 Per què això és «per sobre del motor»

Tots els punts d'entrada criden el motor **com a funció, amb la seva signatura d'avui**:

| Camí | Crida | Fitxer:línia |
|---|---|---|
| Escalat | `generate_graded_specs(sf.id)` | [views.py:3495](../../backend/fhort/models_app/views.py#L3495) |
| Propagar (in-place) | `generate_graded_specs(sf.id)` | [views.py:3121](../../backend/fhort/models_app/views.py#L3121) |
| Propagar (v+1) | `bump_grading_version_and_generate(sf.id, …)` | [views.py:3082](../../backend/fhort/models_app/views.py#L3082) |
| Fitting propagar | `propaga_ancoratges(rule, …)` (utilitat pura) | [fitting/views.py:703](../../backend/fhort/fitting/views.py#L703) |

El motor llegeix `BaseMeasurement` + `ModelGradingRule` + `ModelGradingOverride`. **Si el pas 1
deixa d'escriure aquestes tres taules i escriu un magatzem de preses, el motor no se n'assabenta
i no cal tocar-lo.** La propagació segueix sortint d'on surt avui.

**Corol·lari (important):** com que **acceptar no propaga**, el «acceptar = propagació estàndard +
taula final» de l'addendum vol dir, amb el codi d'avui, **dos gestos**: `close` (consolida base) i
després «Propagar». Fer-los un de sol és possible **fora del motor** —encadenant la crida existent—,
però **contradiu D4 i DECISIONS.md §2**, que van jubilar exactament aquesta auto-propagació.
**Decisió per a l'Agus** (§11-D1), no de l'agent.

---

## §5 · QD — La restricció «només des de base» queda estructural?

**Amb el flux tal com està descrit: NO, encara no — queda UN camí viu d'acceptació per talla
no-base, i és precisament el que el pas 1 fa servir.** Cens complet:

| # | Camí | Estat | Talla no-base? |
|---|---|---|---|
| 1 | `escalat_ajustar_talla_view` [views.py:3327](../../backend/fhort/models_app/views.py#L3327) | **🔴 VIU** — l'únic consumidor és [PropagatedEditor.jsx:86](../../frontend/src/pages/PropagatedEditor.jsx#L86) | **SÍ**: accepta qualsevol talla del run ([:3379-3380](../../backend/fhort/models_app/views.py#L3379-L3380)) i propaga des d'ella ([:3439-3446](../../backend/fhort/models_app/views.py#L3439-L3446)) |
| 2 | `set_size_override_view` [views.py:3196](../../backend/fhort/models_app/views.py#L3196) | **⚪ JUBILADA** — cap `path()` a [urls.py:234-236](../../backend/fhort/models_app/urls.py#L234-L236); l'import de [:15](../../backend/fhort/models_app/urls.py#L15) queda per `pom/test_g6_segell.py`. Cap consumidor JS ([endpoints.js:144-146](../../frontend/src/api/endpoints.js#L144-L146)) | (rebutjaria la base) |
| 3 | `PieceFittingLine` PATCH / `propagar` | **🟢 TANCAT** per `fitting_line_is_non_base` → 400 | NO |
| 4 | `SizeCheckLine` PATCH | **🟢 TANCAT per ESTRUCTURA**: la taula **no té `size_label`** ([models_app/models.py:1437-1486](../../backend/fhort/models_app/models.py#L1437-L1486)) | NO |
| 5 | `close_piece_fitting` | **🟢 TANCAT** ([services.py:515-516](../../backend/fhort/fitting/services.py#L515-L516)) | NO |
| 6 | `resolve_size_check` | **🟢 TANCAT** (només base, [services_size_check.py:238-256](../../backend/fhort/models_app/services_size_check.py#L238-L256)) | NO |
| 7 | Import W5 [extraction_views.py:3544](../../backend/fhort/models_app/extraction_views.py#L3544) | **🟡 VIU** però és **import**, no acceptació humana | SÍ (overrides de divergència) |

**Conclusió QD:** la restricció **queda estructural només si el pas 1 deixa de ser una acceptació**
— és a dir, si `escalat_ajustar_talla_view` deixa d'escriure `BaseMeasurement`/`ModelGradingOverride`
i passa a escriure el magatzem de preses. Mentre aquella vista visqui com avui, **l'Escalat és
alhora la presa i l'acceptació**, i R2 no és una regla del sistema sinó una convenció que la
pantalla podria trencar en un clic.

🚨 **I aquí hi ha una porta que ESPERA** ([[ftt-lectura-que-arma-escriptures]]): posar files
mesurables a totes les talles de l'Escalat **arma N×M gestos d'escriptura** que avui van directes a
la corba teòrica. El cens d'escriptures d'aquesta superfície és part d'obrir la lectura, no feina de
després.

---

## §6 · Q5 — Inventari per a la taula de fitxa tècnica

**Només inventari.** Q8 té el seu tram; aquí no es dissenya res.

### 6.1 Les variants de taula que ja existeixen

| Variant | Funció | Font | `kind` |
|---|---|---|---|
| T0 · Mesures talla base | [TechSheetEditor.jsx:5023](../../frontend/src/pages/TechSheetEditor.jsx#L5023) | `models/<id>/base-measurements/` | `pom_base` |
| T1a · Full de fitting | [:5086](../../frontend/src/pages/TechSheetEditor.jsx#L5086) | `base-measurements/` | `pom_fitting` |
| **T1b · Grading final** | [:5148](../../frontend/src/pages/TechSheetEditor.jsx#L5148) | **`fitting/<sf>/graded-table/`** | `pom_grading` |
| T3 · Repàs de fittings | [:5216](../../frontend/src/pages/TechSheetEditor.jsx#L5216) | `fitting/model/<id>/repas/` | `fitting_history` |
| T2 · BOM | [:5274](../../frontend/src/pages/TechSheetEditor.jsx#L5274) | (buida) | `bom` |
| Personalitzada | [:5295](../../frontend/src/pages/TechSheetEditor.jsx#L5295) | (buida) | — |

### 6.2 El que serveix per injectar-hi una taula nova (i que ja està construït)

- **La llei de partir** viu en un sol lloc amb banc: `partirTaules`
  ([utils/garmentFitxa.js:98-112](../../frontend/src/utils/garmentFitxa.js#L98-L112)), invocada per
  `partirEnTaules` ([TechSheetEditor.jsx:4987-4989](../../frontend/src/pages/TechSheetEditor.jsx#L4987-L4989)).
  Dos eixos: **prenda a fora, secció a dins**.
- **La col·locació** (`escalonat`, `inserirTaules`, `fitTableObj`)
  [TechSheetEditor.jsx:4991-5003](../../frontend/src/pages/TechSheetEditor.jsx#L4991-L5003) — N taules
  no neixen l'una damunt l'altra.
- **El render** és genèric: qualsevol objecte `{type:'table', columns, rows}` el pinta
  `buildTableCellPrimitives`. **Les taules d'aquesta casa no tenen títol** — la columna que porta la
  xifra declara de què parla ([:5012-5017](../../frontend/src/pages/TechSheetEditor.jsx#L5012-L5017)).
- **L'eix va a l'OBJECTE (`garmentId`) i mai a la pàgina** — round-trip opac provat
  ([garmentFitxa.js:17-21](../../frontend/src/utils/garmentFitxa.js#L17-L21)).
- **La T1b ja és una taula POM × talla** amb marca de talla base (`{sl}*` + `base:true`,
  [:5169-5171](../../frontend/src/pages/TechSheetEditor.jsx#L5169-L5171)): la geometria que E1-fitxa
  necessita (teòrica·arribada·propagada per talla) és **la seva amb columnes triplicades o amb
  sub-fila**, no una taula nova de zero.
- **Congelació**: `snapshot` amb `snapshot_at` — la fitxa és un document, no una vista viva
  ([:5206-5210](../../frontend/src/pages/TechSheetEditor.jsx#L5206-L5210)).

### 6.3 🚩 Docstring datat i FALS (troballa)

[TechSheetEditor.jsx:5186-5188](../../frontend/src/pages/TechSheetEditor.jsx#L5186-L5188) diu:
*«Les files de `graded-table/` encara NO porten la peça: cauen totes a la mare i la partició per
prenda no s'activa»*. **És fals des de SET-2/T6a**: `graded-table` serveix `'garment': s.garment`
a cada fila ([graded_spec_views.py:99-101](../../backend/fhort/fitting/graded_spec_views.py#L99-L101))
i n'ordena les files ([:201-206](../../backend/fhort/fitting/graded_spec_views.py#L201-L206)).
La partició per prenda de la T1b **ja funciona**. Mateix patró que els 4 docstrings falsos de
[[ftt-fitxa-multipeca-ja-construida]]: **una condició escrita en un comentari no és un gate**.
(La mateixa nota, a [:4976-4983](../../frontend/src/pages/TechSheetEditor.jsx#L4976-L4983), també
declara `ModelGarment` inexistent, i **existeix** a [models_app/models.py:1711](../../backend/fhort/models_app/models.py#L1711).)

### 6.4 E1-fitxa depèn de Q8?

**Ortogonal en la infraestructura, dependent en la DADA.** El mecanisme d'inserció, partició,
col·locació i congelació ja hi és i no cal esperar res (§6.2). El que E1-fitxa no pot tenir fins que
existeixi el magatzem de preses (§3.4) és **la columna «arribada»**: cap endpoint la serveix avui
perquè el valor no es desa enlloc. → **E1-fitxa és l'ÚLTIM bloc, i el seu bloqueig és E1-dades, no Q8.**

---

## §7 · Q6 — Mapa de col·lisió amb F1

### 7.1 Què està tocant F1 ara mateix (working tree, no commitat)

```
 backend/fhort/fitting/serializers.py               |  11 +/  3 -
 backend/fhort/models_app/views.py                  |  93 +/ 27 -
 frontend/src/api/endpoints.js                      |  12 +/  2 -
 frontend/src/components/EditableTable/EditableTable.jsx |  9 +/  2 -
 frontend/src/components/model/CheckMeasureEditor.jsx    | 46 +/ 11 -
 frontend/src/components/model/fittingGridAdapter.jsx    |  4 +/  2 -
 frontend/src/pages/PropagatedEditor.jsx            |  12 +/  2 -
 frontend/src/utils/filesDePresa.js(+.test)         |  51 +/  8 -
```

### 7.2 Encreuament amb el que E1 tocaria

| Fitxer | E1 el toca? | F1 el toca? | Ordre |
|---|---|---|---|
| `models_app/views.py` (`escalat_ajustar_talla_view`, `_write_base`) | **SÍ, al cor** | **SÍ** (+93/−27) | 🔴 **SÈRIE — bloqueja** |
| `pages/PropagatedEditor.jsx` | **SÍ, al cor** | **SÍ** | 🔴 **SÈRIE — bloqueja** |
| `components/model/fittingGridAdapter.jsx` (`buildEscalatRows`) | **SÍ** | **SÍ** | 🔴 **SÈRIE — bloqueja** |
| `api/endpoints.js` | SÍ (endpoint nou) | SÍ | 🟠 sèrie tova (fitxer compartit → v. [[ftt-dev-concurrent-git]]) |
| `components/model/CheckMeasureEditor.jsx` | probable (pas 2) | **SÍ** | 🟠 sèrie tova |
| `fitting/serializers.py` | possible (R3) | **SÍ** | 🟠 sèrie tova |
| `fitting/services.py` (guard base, consolidació) | **SÍ** | NO | 🟢 **ORTOGONAL** |
| `fitting/views.py` (`_rebuig_escriptura`) | **SÍ** | NO | 🟢 **ORTOGONAL** |
| `fitting/models.py` / `models_app/models.py` (migració del magatzem) | **SÍ** | NO | 🟢 **ORTOGONAL** |
| `pages/TechSheetEditor.jsx` + `utils/garmentFitxa.js` | SÍ (E1-fitxa) | NO | 🟢 **ORTOGONAL** |
| `components/model/MeasureGrid.jsx` (tolerància a l'Escalat) | SÍ (R1) | NO | 🟢 **ORTOGONAL** |

**Ordre de sèrie obligat:** cap línia de codi de **BLOC 1** (§10) es pot començar fins que F1
aterri en commit. La resta (migració del magatzem, guard partit, taula de fitxa) es pot preparar en
paral·lel perquè viu en fitxers que F1 no obre.

### 7.3 ⚠️ Dos avisos de substrat

1. **El gunicorn serveix el codi de quan va arrencar** ([[ftt-backend-desplegat-vs-disc]]). F1
   (`254c8938` + el working tree) **NO és el que corre a staging** fins que algú faci
   `systemctl restart ftt-staging`. Qualsevol QA d'E1 contra staging abans d'això mesura codi vell.
2. **`git add` de paths explícits NO protegeix** quan compartiu fitxer
   ([[ftt-dev-concurrent-git]]): `models_app/views.py`, `PropagatedEditor.jsx` i `endpoints.js` són
   els tres fitxers on E1 i F1 coincideixen. `git show --stat HEAD` després de cada commit.

---

## §8 · Troballes adjacents (llegides, NO tocades)

1. 🚨 **`base_stages_view` col·lapsa prendes al carry-forward.** El payload serveix `garment` per
   fila ([views.py:4077](../../backend/fhort/models_app/views.py#L4077)) però **la clau interna és
   de TRES camps**: `changes_by_ev[key][(c.pom_id, c.capa, c.instancia)]`
   ([:4017](../../backend/fhort/models_app/views.py#L4017)), `displayed`
   ([:4028](../../backend/fhort/models_app/views.py#L4028)) i `clau_bm`
   ([:4041](../../backend/fhort/models_app/views.py#L4041)). Amb el POM 962 del 1379 (viu a la mare
   i al Short amb la mateixa `(capa, instancia)`), **la presa d'una peça s'arrossega per la fila de
   l'altra** — exactament el símptoma que FIX-2 i C2/Onada 1 van tancar per als altres dos eixos.
   Alimenta Mesures i Comprovació. **Membre nou de la FAMÍLIA DE TRES** ([[ftt-s2-fixes-s36-pell]]).
2. 🚨 **`serializers_size_check.py` té les dues boques velles**: `bm_map` de tres camps
   ([:89-92](../../backend/fhort/models_app/serializers_size_check.py#L89-L92)) → la tolerància i el
   `nom_fitxa` d'una peça poden jutjar la línia d'una altra; i `_load_grading_rules` + `rules.get(line.pom_id)`
   ([:97](../../backend/fhort/models_app/serializers_size_check.py#L97) i
   [:106](../../backend/fhort/models_app/serializers_size_check.py#L106)) — **la 3a de les cinc boques
   de la llei de la mare**, l'única que F1 no ha tancat aquesta onada.
3. 🟡 `ModelGradingOverride.created_at` no s'actualitza a l'upsert
   ([views.py:3480-3485](../../backend/fhort/models_app/views.py#L3480-L3485)): el «moment» d'un pin
   re-editat menteix. Només el log diu la veritat.
4. 🟡 `escalat_ajustar_talla_view` **no té guard de talla base ni de sessió**: qualsevol usuari amb
   `EXECUTE_TASKS` pot moure la corba des de qualsevol talla en qualsevol moment.

---

## §9 · Veredicte sobre la forma (viabilitat del flux de dos passos)

**El flux és VIABLE i no exigeix tocar el motor. Però no és «cablejar dues pantalles que ja
existeixen»: el pas 1 avui fa la feina del pas 2, i mentre la faci, el pas 2 no té res a decidir.**

Tres afirmacions amb rastre:

1. ✅ **El pas 2 ja té l'abast d'una talla i el contracte de tres estats.** Res a construir:
   `PieceFittingLine` porta `size_label` + `valor_teoric` + `valor_real` + `decisio`
   {ACCEPTED, ADJUSTED, REJECTED} + els tres eixos, i el guard de base és a la porta d'entrada
   (§2). La hipòtesi original del brief («E1 = el contracte de Mesurar prenda estès amb l'eix de
   talla») era **més certa del que deia**: l'eix de talla **ja hi és a la taula**; el que està
   clavat a una talla és la **projecció** i el **guard**, no el model de dades.
2. 🔴 **El pas 1 no és una presa: és una escriptura de domini.** Escriu `BaseMeasurement` i
   re-deriva els specs dins de la mateixa crida (§1.3). Amb això, el pas 2 hidrata `valor_teoric`
   del valor que el pas 1 acaba d'escriure → **desviació zero, acceptació buida** (§3.2).
   **Aquest és EL bloqueig de la peça, i és un bloqueig de DADES, no de pantalles.**
3. 🟠 **«Acceptar = propagació estàndard» són dos gestos avui, per decisió de domini (D4).**
   Fusionar-los és possible fora del motor però reobre una llei tancada el 21/07 (§4.1).

**Illa nova o contracte estès?** → **Contracte estès, amb UNA taula nova possible i cap sistema
nou.** L'única cosa que no existeix és **on viu una xifra mesurada d'una talla no-base**; tota la
resta (estats, propagació, guard de base, taules de fitxa, partició per peça) ja està construïda.

---

## §10 · Dimensionament per blocs

| Bloc | Què | Depèn de | Fitxers | Mida |
|---|---|---|---|---|
| **B0** · Decisió | §11-D1 i §11-D2 (magatzem + gest d'acceptar) | — | — | Agus |
| **B1** · Magatzem de preses | Migració + model (o obertura de `PieceFittingLine` a l'escriptura no-base amb el guard partit) | B0 | `fitting/models.py` o `models_app/models.py` + migració | 🟢 **ortogonal a F1** |
| **B2** · Pas 1 deixa de ser acceptació | `escalat_ajustar_talla_view` escriu la presa i **no** `BaseMeasurement`/`Override`; el gest d'ajust de corba es conserva o se separa | **B1 + F1 aterrat** | `models_app/views.py`, `api/endpoints.js` | 🔴 **sèrie després de F1** |
| **B3** · R1 + R3 a l'Escalat | tres valors per cel·la + banda de tolerància real (`active.tol`, ja soportada per `MeasureGrid`) | B2 | `fittingGridAdapter.jsx`, `PropagatedEditor.jsx`, `MeasureGrid.jsx` | 🔴 **sèrie després de F1** |
| **B4** · Cens d'escriptures armades | tot gest que la lectura nova posa a l'abast (§5) | B3 | — | 🔴 va AMB B3, no després |
| **B5** · Pas 1 → pas 2 | porta d'«acceptar/rebutjar» que obre Mesurar prenda; **el pre-omplert no cal transportar-lo** si B1 tria el candidat ① (§3.4) | B2 | `PropagatedEditor.jsx`, `ModelSheet.jsx` | 🟠 sèrie tova |
| **B6** · R2 estructural | tancar el camí no-base d'acceptació + guard | B2 | `models_app/views.py`, `fitting/services.py` | 🟢 el guard és ortogonal |
| **B7** · E1-fitxa (R4) | variant de taula teòrica·arribada·propagada | B1 (dada) i **no** Q8 | `TechSheetEditor.jsx` (+ endpoint lector) | 🟢 **ortogonal a F1** |

**Camí crític:** B0 → B1 → *(esperar F1)* → B2 → B3+B4 → B5/B6 → B7.

---

## §11 · Decisions que queden per a l'Agus

- **D1 · «Acceptar» propaga o no?** Avui `close` consolida la base i **no** propaga (D4 /
  DECISIONS.md §2). L'addendum diu «acceptar = propagació estàndard + taula final». Opcions:
  (a) mantenir els dos gestos (acceptar → botó ④ Propagar); (b) encadenar-los només des d'aquest
  flux; (c) reobrir D4. **Cap és tècnicament costosa; totes tres toquen una llei escrita.**
- **D2 · On viu la mesura arribada d'una talla no-base?** Candidat ① (`PieceFittingLine` amb el
  guard partit en «escriure» vs «acceptar») o candidat ② (taula nova). ③ està descartat per rastre
  (§3.4). **① reutilitza el contracte de tres estats i no en crea cap de paral·lel; ② no lliga
  l'Escalat a una `FittingSession`.**
- **D3 · Abast de peça al pas 2.** Un model multipeça obre «Mesurar prenda» amb tots els
  contenidors (§2). Es filtra per la peça des d'on s'ha acceptat, o s'accepta el model sencer?
- **D4 · Què passa amb l'ajust de corba a l'Escalat?** Si el pas 1 passa a ser presa, **el gest
  d'ajustar la teòrica per talla desapareix o es queda com a gest a part?** Avui és la mateixa
  cel·la i el mateix clic.
- **D5 · Obrir el pas 2 escriu** (crea `FittingSession` + `PieceFitting` + N línies, §0). És
  acceptable que «acceptar/rebutjar» materialitzi una sessió de fitting, o el pas 2 ha d'entrar
  per una porta que no en creï?
- **D6 · Adjacents del §8** (1 i 2 són defectes vius de multipeça): entren en aquesta peça, en
  tenen una de pròpia, o s'anoten?

---

## §12 · Límits declarats

1. **No s'ha executat cap consulta a la BD.** Totes les afirmacions surten de codi al disc. Les
   afirmacions sobre dades reals (quantes peces `02` hi ha, si el POM 962 segueix a les dues
   prendes) **provenen de memòria de sessions anteriors i no s'han re-verificat**.
2. **No s'ha obert cap pantalla ni fet cap login** (una diagnosi read-only no s'autentica:
   escriuria `last_login`). Els comportaments de UI descrits estan **llegits al codi, no observats**.
3. **Substrat = disc, no desplegat.** El que corre a staging és anterior a F1 (§7.3).
4. **No s'ha llegit `pom/services.py::generate_graded_specs` per dins** (zona intocable G6): la
   frontera s'ha resolt pels **punts de crida**, que és el que la pregunta demanava. Si algú volgués
   canviar *com* gradua, aquesta diagnosi no en diu res.
5. **`fitting/serializers.py` i `models_app/views.py` es mouen sota els peus** (sessió concurrent):
   els números de línia d'aquests dos fitxers poden desplaçar-se en qüestió de minuts. Els
   **noms de funció** citats són l'àncora estable.
6. **No s'ha dissenyat la taula de fitxa** (Q5 = inventari, per encàrrec) ni s'ha entrat a Q8.
7. **`ModelGarment` i les comportes**: es donen per vius perquè el codi els llegeix i les migracions
   citades hi consten als comentaris; **no s'ha comprovat a `pg_constraint`**.
