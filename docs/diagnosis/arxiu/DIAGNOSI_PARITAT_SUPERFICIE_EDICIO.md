> ⚠️ SUPERADA 2026-07-07 — implementada (3 GAPS resolts; Escalat convergit amb fitting, 96e7fc8/b495442). Consulta només com a històric.

# DIAGNOSI DE PARITAT — SUPERFÍCIE D'EDICIÓ: FITTING (canònic) → ESCALAT

**Patró A · read-only · branca `dev` · 2026-06-24**
Entorn: `/var/www/ftt-staging` (frontend React + backend Django). Dades schema **`fhort`** (no id=6).

**Regla mestra:** l'ANTIC FITTING (`FittingDetail` + `MeasureGrid` + `fittingGridAdapter` + endpoints
`piece-fitting-lines/*`) és la **font canònica de veritat**. Tota divergència d'Escalat és un **GAP a
corregir**, no una decisió de domini. Aquesta diagnosi **no implementa res**.

> **Titular:** Escalat i el fitting **ja comparteixen** `MeasureGrid` + `regimeLeadCol` + el mateix fitxer
> adapter. La divergència és a **(a) els builders** (`buildEscalat*` vs `buildFitting*`) i **(b) l'onSave**.
> Tres GAPS severs: **la base es bloqueja** (el fitting la deixa editar), **editar una cel·la NO propaga a
> les germanes** (el fitting sí, via `/propagar`), i **no hi ha eix de versions**. El botó "Propagar" SÍ
> existeix i SÍ es serveix (caché de navegador) — però ni tan sols és el que falta: el que falta és la
> **propagació a germanes en editar**. La via neta és **CONVERGIR** Escalat sobre el contracte del fitting.

---

## BLOC 1 — LA FONT CANÒNICA: QUÈ FA EL FITTING

| # | Capacitat | On (ruta:línia) | Comportament |
|---|---|---|---|
| 1A | Entrada/mode | [FittingDetail.jsx:467](../../frontend/src/pages/FittingDetail.jsx#L467); editable si sessió Oberta/Programada, `readOnly` si Tancada/Anullada | Carrega `piece-fittings/<id>/` (graella per peça) |
| 1B | **Talles editables** | [fittingGridAdapter.jsx:30-52](../../frontend/src/components/model/fittingGridAdapter.jsx#L30) `buildFittingRows` | `active: { lineId, value, baseValue }` **sense cap `readonly`** → **TOTES editables, base inclosa** |
| 1C | Desat cel·la | `MeasureGrid` `ActiveCell` debounce 800 ms → `makeFittingOnSave` ([adapter:140-146](../../frontend/src/components/model/fittingGridAdapter.jsx#L140)) | STEP → `PATCH piece-fitting-lines/<id>/`; LINEAR → `POST piece-fitting-lines/<id>/propagar/` |
| 1D | **Propaga a germanes** | [fitting/views.py:483-546](../../backend/fhort/fitting/views.py#L483) `propagar` → [grading_utils.py:546](../../backend/fhort/pom/grading_utils.py#L546) `propaga_ancoratges` | En editar (commit LINEAR): **ancora la cel·la i escriu `valor_real` de TOTES les germanes** (delta LINEAR); retorna `linies` → `MeasureGrid` refresca les germanes (excepte la del focus). **Automàtic, en temps real.** |
| 1E | Règim/breaks | `regimeLeadCol` ([adapter:69-99](../../frontend/src/components/model/fittingGridAdapter.jsx#L69)) → `setPomRegim` (`models/<id>/pom/<id>/regim/`) | Select LINEAR/STEP per POM; break informatiu (`regleLabel`) |
| 1F | **Eix de versions** | `buildFittingGroups` ([adapter:15-25](../../frontend/src/components/model/fittingGridAdapter.jsx#L15)) | `historyCols` = N versions (`v1`=Base, `v2`=Fit 1…) des de `evolucio[]` + columna activa |
| 1G | Accions UI | FittingDetail | Tancar peça (`close`+`seal`), descartar peça/sessió, fotos, gate, règim per cel·la; **la propagació NO és un botó: és automàtica en editar** |

**Veritat canònica (cor):** al fitting **(1B) la base és editable** i **(1D) editar una cel·la propaga el
delta a les talles germanes** automàticament (LINEAR), refrescant la fila sencera. Aquesta és la conducta
que Escalat ha de replicar.

---

## BLOC 2 — QUÈ FA (I NO) ESCALAT (PropagatedEditor)

| # | Mirall de 1x | On (ruta:línia) | Estat vs fitting |
|---|---|---|---|
| 2A | Entrada/mode | [EscalatTask.jsx:24](../../frontend/src/pages/EscalatTask.jsx#L24) munta `PropagatedEditor` **sense `readOnly`/`inline`** → tots dos `false` (editable, overlay); carrega `taula-mesures` | ✅ editable (com el fitting) |
| 2B | **Talles editables** | [fittingGridAdapter.jsx:124](../../frontend/src/components/model/fittingGridAdapter.jsx#L124) `buildEscalatRows`: `readonly: s === baseLabel` | ❌ **GAP — la base es BLOQUEJA** (el fitting no). A més el backend [views.py:~1316](../../backend/fhort/models_app/views.py#L1316) rebutja editar la base com a override |
| 2C | Desat cel·la | [PropagatedEditor.jsx:47-64](../../frontend/src/pages/PropagatedEditor.jsx#L47) `onGridSave` → `models.setSizeOverride` (debounce 800 ms igual) | ⚠️ **desa SÍ** (persisteix override), però per un camí distint |
| 2D | **Propaga a germanes** | `set_size_override_view` ([views.py:1239](../../backend/fhort/models_app/views.py#L1239)) → `ModelGradingOverride` (pin) + `generate_graded_specs` (re-grada des de **base**) | ❌ **GAP SEVER — NO propaga a germanes.** L'override PINA la cel·la; les germanes es recalculen des de la base (que no canvia) → **no es mouen**. El fitting propagava el delta a totes |
| 2E | Règim/breaks | `regimeLeadCol` + `setPomRegim` ([PropagatedEditor.jsx:67,94](../../frontend/src/pages/PropagatedEditor.jsx#L67)) | ✅ **IGUAL** (mateix component i endpoint) |
| 2F | **Eix de versions** | `buildEscalatGroups` ([adapter:105-115](../../frontend/src/components/model/fittingGridAdapter.jsx#L105)): `historyCols: [{ key:'vigent' }]` | ❌ **GAP — una sola columna 'vigent', sense versions** |
| 2G | Accions UI | barra [PropagatedEditor.jsx:109-133](../../frontend/src/pages/PropagatedEditor.jsx#L109): botó **Propagar** (conscient v+1) + Tancar | ⚠️ conjunt distint; el botó Propagar = acte de **versionar**, no la propagació-en-editar del fitting |

### 2W — Per què NO es veu el botó "Propagar" (resolt: NO és el codi)
- **Condició de render correcta:** barra a `(!readOnly || !inline)` i botó a `!readOnly`
  ([PropagatedEditor.jsx:109,113](../../frontend/src/pages/PropagatedEditor.jsx#L109)). EscalatTask passa
  `readOnly=false`, `inline=false` → **hauria de renderitzar**. (ModelSheet el passa `inline readOnly` →
  no surt, correcte.)
- **El bundle servit SÍ el conté:** `dist/assets/PropagatedEditor-D229XZZi.js` (build **13:37**, posterior
  al commit 423853a de les 12:20) conté `grading_propagate`/`generarGrading`/`ti-git-branch` (grep=1), i
  `readOnly:m=!1` (default false).
- **nginx el serveix:** `/etc/nginx/sites-available/ftt-staging` (enabled) → `root
  /var/www/ftt-staging/frontend/dist`.
  ⇒ **El botó es serveix.** Que l'usuari no el vegi = **caché del navegador** (index/bundle antic) → **hard
  refresh**. **NO és defecte de codi, NO és build stale.**
- **Matís clau:** encara que es vegi, el botó **NO resol** "edito XL i no propaga": fa *versionar*
  (generar v+1), no propagar a germanes (vegeu 2D).

### 2V — "Base editable en 186 / bloquejada en 185" (no es reprodueix)
`buildEscalatRows:124` bloqueja la base **sempre que `base_size_label` coincideixi amb una etiqueta del
run**. Dades reals: **186** base `'S'` i run `S·M·L·XL·XXL` → match **True**; **185** base `'L'` → match
**True**. ⇒ **la base es bloqueja en ELS DOS**; la percepció "editable en 186" **no es reprodueix** al codi
ni a les dades (probable bundle antic en caché o talla confosa). L'única manera que la base NO es bloquegi
seria `base_size_label` sense match al run (dada incoherent) — no és el cas. **El GAP real és independent:
el fitting MAI bloqueja la base; Escalat sí.**

### 2U — El hint "es re-propaga automàticament" (paradigma vell)
Clau i18n `model_measurements.propagated_hint` (ca/en/es), usada a
[PropagatedEditor.jsx:141](../../frontend/src/pages/PropagatedEditor.jsx#L141). El text promet
re-propagació automàtica, però el comportament real (2D) és **override que pina la cel·la i germanes
quietes**. **Contradicció literal vell↔real.**

---

## BLOC 3 — MATRIU DE PARITAT DE LA SUPERFÍCIE D'EDICIÓ

| Capacitat | Fitting (com) | Escalat (com) | Estat |
|---|---|---|---|
| Mode editable | per estat sessió | `readOnly=false` per task | ✅ IGUAL |
| **Base editable** | SÍ (cap `readonly`) | **NO** (`readonly: s===base`) | ❌ **GAP** |
| Desat cel·la | debounce → `propagar`/`update` | debounce → `setSizeOverride` | ⚠️ desa, camí distint |
| **Propagar a germanes en editar** | **SÍ** (`propaga_ancoratges`, refresca fila) | **NO** (override pina; base intacta) | ❌ **GAP SEVER** |
| Règim LINEAR/STEP | `regimeLeadCol`+`setPomRegim` | idèntic | ✅ IGUAL |
| Breaks | informatiu derivat | idèntic | ✅ IGUAL |
| **Eix de versions** | N versions (`evolucio[]`) | 1 col 'vigent' | ❌ **GAP** |
| Versionar (segellar treball) | tancar peça → v+1 | botó "Propagar conscient" → v+1 (Peça 2) | ✅ (anàleg) |

**Per a cada GAP — què reusar del fitting:**
- **Base editable (2B):** treure `readonly: s === baseLabel` de `buildEscalatRows`; el fitting demostra que
  la base s'edita com qualsevol cel·la activa. (Cal endpoint que accepti editar la base — avui el backend la
  rebutja.)
- **Propagar a germanes (2D):** reusar **`propaga_ancoratges`** (motor PUR, ja existeix) + un onSave estil
  **`makeFittingOnSave`** que cridi un endpoint model-level equivalent a `piece-fitting-lines/propagar`.
- **Versions (2F):** reusar **`buildFittingGroups`** (eix de versions) alimentat amb l'historial
  `GradingVersion`/`GradedSpec` del model.

---

## BLOC 4 — LA DECISIÓ ARQUITECTÒNICA: CONVERGIR (recomanat)

**4A — Ja comparteixen el component.** Escalat NO té graella pròpia: usa el **mateix `MeasureGrid`** i el
**mateix `regimeLeadCol`** del fitting, des del **mateix fitxer** `fittingGridAdapter.jsx`. L'única cosa
divergent són **dues funcions builder** (`buildEscalatGroups`/`buildEscalatRows`) i **l'onSave**
(`onGridSave`→`setSizeOverride`). ⇒ La solució neta **NO és pedaçar PropagatedEditor punt per punt**, sinó
**convergir Escalat sobre el contracte del fitting** (com es va fer amb Mesures el 24/06).

**4B — Què cal per alimentar `MeasureGrid` des d'Escalat amb el contracte del fitting:**
- **Reús tal qual:** `MeasureGrid` (cap canvi — ja suporta base editable, N versions, refresc de germanes),
  `regimeLeadCol`, `propaga_ancoratges` (motor), `buildFittingGroups`/`buildFittingRows` (o un builder
  convergit sense `readonly` de base i amb eix de versions).
- **Cal construir (dimensió mitjana):**
  1. **Endpoint model-level "propagar"** equivalent a `piece-fitting-lines/propagar`: rep (model, pom,
     talla-àncora, valor), crida `propaga_ancoratges`, i **escriu el resultat de totes les germanes** al
     magatzem del model. *Frontera de disseny real:* el fitting escriu `PieceFittingLine.valor_real`
     (sessió); Escalat no té sessió → cal decidir l'objectiu d'escriptura (overrides per germana, o
     re-derivar la base). Aquesta és la **única peça d'enginyeria nova**; el motor de propagació ja hi és.
  2. **Eix de versions a Escalat:** un endpoint/ampliació que torni l'historial `GradingVersion`+`GradedSpec`
     per alimentar `historyCols` (la diagnosi de paritat prèvia ja ho va marcar).
  3. **Treure el bloqueig de base** (frontend `buildEscalatRows` + backend `set-size-override`).
  4. **Reescriure el hint** (2U) perquè descrigui el comportament real.

**4C — Frontera amb Peça 1 (helper v+1) i Peça 2 (botó conscient):**
- **L'edició-per-cel·la amb propagació-a-germanes** (paritat fitting) és l'**AJUST continu** sobre la
  versió de treball vigent.
- **El botó "Propagar conscient"** (Peça 2 → `generate_grading_view new_version` → helper Peça 1) és l'acte
  de **VERSIONAR** (crear v+1, segellar el treball) — l'equivalent a "tancar peça" del fitting.
- **Relació neta:** edites talles (ajust, propaga a germanes en temps real) → quan estàs satisfet, prems
  **Propagar** i es crea la v+1. Dos nivells: *ajust* (per cel·la) vs *versionat conscient* (botó). Les
  Peces 1/2 **no s'han de refer**; encaixen com el "tancament" de la superfície convergida.

---

## BLOC 5 — DADES REALS (schema `fhort`)

**Model 186** (`FTT-CO27-0001`): base `'S'`, run `S·M·L·XL·XXL` (**base match=True** → base bloquejada per
codi). `SizeFitting=77`, **1 GradingVersion (v1 activa)**, **100 GradedSpec**, **1 ModelGradingOverride**.
20 BaseMeasurement (POMs); **els 20 tenen GradedSpec → cap FIT ACTUAL buit per a 186** (la "FIT ACTUAL
buida" observada no es dóna en aquest model; passaria amb POMs sense regla/spec, no és el cas).
**Model 185** (base `'L'`, match=True) → base també bloquejada. ⇒ confirma 2V: la inconsistència
percebuda no surt de les dades.

---

## VEREDICTE

- **Recorregut canònic del fitting:** obre editable per estat de sessió → **totes les talles editables,
  base inclosa** (`buildFittingRows`, sense `readonly`) → editar una cel·la (debounce 800 ms) → si LINEAR,
  `POST piece-fitting-lines/propagar` → **`propaga_ancoratges` escriu les germanes** i la fila es refresca →
  eix de versions `Base/Fit1/Fit2` des de `evolucio[]` → tancar peça crea v+1.
- **Matriu de paritat:** ✅ mode editable, règim/breaks, versionar-conscient. ❌ **base editable**, ❌
  **propagació a germanes en editar**, ❌ **eix de versions**. ⚠️ desat (camí distint: override vs propagar).
- **Per què a Escalat "no passa res" en editar XL:** **DESA SÍ** (`setSizeOverride` persisteix un override),
  però **NO propaga a les germanes** ([views.py:1239→1321](../../backend/fhort/models_app/views.py#L1239):
  l'override pina la cel·la i `generate_graded_specs` re-grada des de la base intacta) — el fitting, en
  canvi, propagava el delta a totes (`piece-fitting-lines/propagar`). La **base bloquejada** ve de
  `buildEscalatRows:124` (`readonly: s===baseLabel`), un bloqueig que el fitting **no** té. El **botó
  Propagar** SÍ existeix i SÍ es serveix (nginx→dist 13:37 amb el botó; render `readOnly=false`); que no es
  vegi = **caché del navegador** (hard refresh), i a més **no és el que cal** per propagar a germanes.
- **Decisió arquitectònica:** **CONVERGIR**, no pedaçar. Escalat ja usa `MeasureGrid`+`regimeLeadCol`+adapter
  del fitting; només divergeixen 2 builders i l'onSave. Fer que Escalat usi el contracte del fitting (base
  editable + propagar-a-germanes + versions). **Pedaçar** seria tocar 3-4 punts solts de `buildEscalat*`
  + `set-size-override` i quedaria un híbrid; **convergir** elimina la divergència d'arrel.
- **Reús tal qual:** `MeasureGrid`, `regimeLeadCol`, `propaga_ancoratges` (motor), `buildFitting*`. **A
  construir:** un endpoint model-level "propagar" (anchor → `propaga_ancoratges` → escriu germanes; única
  peça d'enginyeria nova — decidir objectiu d'escriptura model-level), l'alimentació de l'eix de versions, i
  treure el bloqueig de base. **Frontera Peça 1/2:** intactes; el botó conscient = acte de versionar (v+1),
  complementari a l'ajust-per-cel·la convergit. **Operatiu immediat:** hard refresh per veure el botó ja
  desplegat; reescriure el hint 2U.

*Fi de la diagnosi. No s'ha implementat res. Atura't aquí.*
