# DIAGNOSI GLOBAL — Tots els camins d'entrada a edició de mides/escalat

**Data:** 2026-06-26 · **Branca:** `dev` · **Patró:** A (READ-ONLY absolut, cap reapuntat)
**Abast:** la FOTO SENCERA dels camins cap a mides (`Mesures`) i escalat (`Escalat`), per veure TOTS els
caps solts que va deixar la jubilació de `/mesures` (J1) de cop, no un per un.

> ⚠️ **Conclusió capçalera (corregeix la hipòtesi de partida):** la queixa assumia que el camí
> **manual encara va a una pantalla vella**. **NO és cert a nivell de ruta**: cap camí navega ja a una
> pàgina standalone — tots conflueixen al **tab del ModelSheet**. El cap solt REAL de J1 és una
> **divisió d'editors dins la mateixa superfície**: l'entrada/manual/seed pinta amb `EditableTable`
> (portat de l'antic `ModelMeasurements`), mentre treball/consulta/escalat pinten amb `MeasureGrid`.
> Vegeu §3 i §5.

---

## PREGUNTA 1 — Inventari exhaustiu de pantalles de mides/escalat

### A) Rutes a `App.jsx`

| Ruta | Component | Estat | Destí / nota |
|---|---|---|---|
| `models/:id` ([App.jsx:144](frontend/src/App.jsx#L144)) | `ModelSheet` | ✅ VIVA | Full únic; conté els tabs `Mesures` i `Escalat` |
| `models/:id/mesures` ([App.jsx:147](frontend/src/App.jsx#L147)) | `MesuresRedirect` | 🔁 REDIRECT | → `/models/:id?tab=Mesures[&task_id=]` ([App.jsx:57-62](frontend/src/App.jsx#L57-L62)) |
| `models/:id/escalat` ([App.jsx:150](frontend/src/App.jsx#L150)) | `ModelSheet defaultTab="Escalat" autoEdit="Escalat"` | ✅ VIVA (ruta real) | Obre el tab Escalat en mode edició. **Asimetria:** és ruta real, no redirect |
| `models/:id/size-check` ([App.jsx:154](frontend/src/App.jsx#L154)) | `SizeCheckRedirect` | 🔁 REDIRECT | → `/models/:id?tab=Mesures[&task_id=]` ([App.jsx:47-52](frontend/src/App.jsx#L47-L52)) |
| `models/:id/teixit` ([App.jsx:151](frontend/src/App.jsx#L151)) | `ModelFabric` | ✅ VIVA | Teixit (no mides), però **conté un punt d'entrada** a Mesures (§2) |

Tots dos redirects conserven `task_id` si en porten i fan `<Navigate ... replace />` ([App.jsx:51](frontend/src/App.jsx#L51), [App.jsx:61](frontend/src/App.jsx#L61)).

### B) Tabs del `ModelSheet` (superfície única post-J1)

Array de tabs a [ModelSheet.jsx:22](frontend/src/pages/ModelSheet.jsx#L22):
`['Dashboard','Resum','Mesures','Escalat','Fitxa tècnica','Fitxers',"Registre d'activitat"]`

| Tab | Component(s) renderitzat(s) | Estat | Ref |
|---|---|---|---|
| **Mesures** | `MeasuresEntryPanel` (genesi/entrada) **O** `CheckMeasureEditor` (treball/consulta) | ✅ VIVA | render ~[ModelSheet.jsx:378-426](frontend/src/pages/ModelSheet.jsx#L378-L426) |
| **Escalat** | `PropagatedEditor` (inline) | ✅ VIVA | render ~[ModelSheet.jsx:428-448](frontend/src/pages/ModelSheet.jsx#L428-L448) |

### C) Components de mides/escalat — vius vs orfes

| Component | Fitxer | Estat | Qui l'usa |
|---|---|---|---|
| `MeasuresEntryPanel` | [components/model/MeasuresEntryPanel.jsx:19](frontend/src/components/model/MeasuresEntryPanel.jsx#L19) | ✅ VIU | tab Mesures (genesi) |
| `CheckMeasureEditor` | [components/model/CheckMeasureEditor.jsx](frontend/src/components/model/CheckMeasureEditor.jsx) | ✅ VIU | tab Mesures (treball/consulta) |
| `PropagatedEditor` | [pages/PropagatedEditor.jsx:15](frontend/src/pages/PropagatedEditor.jsx#L15) | ✅ VIU | tab Escalat |
| `MeasureGrid` (graella canònica) | [components/model/MeasureGrid.jsx](frontend/src/components/model/MeasureGrid.jsx) | ✅ VIU | `CheckMeasureEditor` ([:4](frontend/src/components/model/CheckMeasureEditor.jsx#L4),[:311](frontend/src/components/model/CheckMeasureEditor.jsx#L311)), `PropagatedEditor`, `FittingDetail`, `fittingGridAdapter` |
| `EditableTable` (graella d'entrada) | [components/EditableTable/EditableTable.jsx](frontend/src/components/EditableTable/EditableTable.jsx) | ⚠️ VIU PERÒ AÏLLAT | **NOMÉS** `MeasuresEntryPanel` ([MeasuresEntryPanel.jsx:3](frontend/src/components/model/MeasuresEntryPanel.jsx#L3),[:229](frontend/src/components/model/MeasuresEntryPanel.jsx#L229)) |
| `SizeMapSetup` | [pages/SizeMapSetup.jsx:81](frontend/src/pages/SizeMapSetup.jsx#L81) | ✅ VIU | Size Library (drawer); torna a Mesures (§2) |
| `MesuresRedirect` / `SizeCheckRedirect` | inline a [App.jsx:57-62](frontend/src/App.jsx#L57-L62) / [App.jsx:47-52](frontend/src/App.jsx#L47-L52) | 🔁 REDIRECT | — |
| `ModelMeasurements`, `SizeCheckWork`, `EscalatTask`, `MeasurementsChat` | — | ☠️ ELIMINATS | **No existeixen** al codi (grep buit). J1 ja en va treure el fitxer; només queden els redirects i el rastre a comentaris |

**FET:** no hi ha cap component orfe-però-routat ni cap pàgina standalone de mides viva. Les úniques
restes de l'antic són (i) els 2 redirects i (ii) `EditableTable` com a graella divergent (§5).

---

## PREGUNTA 2 — Tots els punts d'ENTRADA (qui navega cap a mides/escalat)

Grep global de navegació a `mesures|escalat|size-check|tab=Mesures|tab=Escalat|mode=entry` sobre
`frontend/src`. **Taula origen → destinació → viva/morta:**

| # | Origen (fitxer:línia · qui) | Destinació EXACTA | Estat |
|---|---|---|---|
| 1 | [App.jsx:51](frontend/src/App.jsx#L51) · `SizeCheckRedirect` | `/models/:id?tab=Mesures[&task_id=]` | ✅ (a tab viu) |
| 2 | [App.jsx:61](frontend/src/App.jsx#L61) · `MesuresRedirect` | `/models/:id?tab=Mesures[&task_id=]` | ✅ (a tab viu) |
| 3 | [WorkPlan.jsx:29](frontend/src/components/model/WorkPlan.jsx#L29) · `toolRoute` cas `pom` ("Definició POM") | `/models/:id?tab=Mesures&mode=entry` | ✅ |
| 4 | [WorkPlan.jsx:33](frontend/src/components/model/WorkPlan.jsx#L33) · `toolRoute` cas `size_check` ("Mesurar prenda") | `/models/:id?tab=Mesures&task_id=<id>` | ✅ |
| 5 | [WorkPlan.jsx:36](frontend/src/components/model/WorkPlan.jsx#L36) · `toolRoute` cas `grading` ("Escalat") | `/models/:id/escalat?task_id=<id>` | ✅ |
| 6 | [DashboardTab.jsx:201](frontend/src/components/model/DashboardTab.jsx#L201) · targeta artefacte "Grading" | `onOpenTab('Escalat')` (commuta tab, sense ruta) | ✅ |
| 7 | [DashboardTab.jsx:222](frontend/src/components/model/DashboardTab.jsx#L222) · targeta artefacte "Base" | `onOpenTab('Mesures')` (commuta tab, sense ruta) | ✅ |
| 8 | [ModelFabric.jsx:286](frontend/src/pages/ModelFabric.jsx#L286) · botó tornar del teixit | `/models/:id?tab=Mesures` | ✅ |
| 9 | [SizeMapSetup.jsx:127](frontend/src/pages/SizeMapSetup.jsx#L127) · fi del wizard de mapa de talles | `/models/:id?tab=Mesures` | ✅ |
| 10 | [ImportWizard.jsx:187](frontend/src/components/ImportWizard/ImportWizard.jsx#L187) · escapatòria "crear a Library" (1C-3b) | `/size-library?prefill=<...>` (**SURT** del flux de mides cap a Size Library) | ⚠️ sortida lateral |

### Entrades INTERNES (sense canvi de ruta — botons del propi ModelSheet)
Conflueixen totes al funnel `enterEdit(tab, code)` ([ModelSheet.jsx:186-200](frontend/src/pages/ModelSheet.jsx#L186-L200)):

| Origen | Acció | Ref |
|---|---|---|
| Botó "Editar mides" (tab Mesures) | `enterEdit('Mesures','pom')` → mode ENTRADA | ~[ModelSheet.jsx:399](frontend/src/pages/ModelSheet.jsx#L399) |
| Botó "Editar escalat" (tab Escalat) | `enterEdit('Escalat','grading')` | ~[ModelSheet.jsx:439](frontend/src/pages/ModelSheet.jsx#L439) |
| Botó "Propagar a grading" (origen Mesures) | en èxit → `setActiveTab('Escalat')` | [ModelSheet.jsx:255+](frontend/src/pages/ModelSheet.jsx#L255) |

### NO-entrades (verificat, importants per descartar)
- **Kanban / pàgina Tasques** ([pages/Tasks.jsx](frontend/src/pages/Tasks.jsx)): grep de `navigate|/models/|pom|size_check|grading|tab=` → **buit**. La pàgina de tasques **NO** és punt
  d'entrada a mides. ⚠️ El comentari de [WorkPlan.jsx:22](frontend/src/components/model/WorkPlan.jsx#L22) parla d'un `KanbanTasks.jsx` com a
  "mirall" — **aquest fitxer no existeix** (referència estancada; deute documental, no de codi).

**FET:** 10 punts de navegació + 3 botons interns. Tots apunten a superfície viva (tab del ModelSheet),
excepte la sortida lateral #10 (cap a Size Library, per disseny 1C-3b).

---

## PREGUNTA 3 — El wizard d'entrada de mides (les 4 vies)

Cor de `MeasuresEntryPanel`. Selector amb 2 targetes ([MeasuresEntryPanel.jsx:168-200](frontend/src/components/model/MeasuresEntryPanel.jsx#L168-L200)):
manual ([:177](frontend/src/components/model/MeasuresEntryPanel.jsx#L177)) i import ([:191](frontend/src/components/model/MeasuresEntryPanel.jsx#L191)). Les 4 vies lògiques:

| Via | On viu (fitxer:línia) | Què dispara | On acaba |
|---|---|---|---|
| **(a) Model nou buit** | useEffect inicial [:118-120](frontend/src/components/model/MeasuresEntryPanel.jsx#L118-L120) | si verge i sense plantilla → `materialitzar-poms` (POST) → `reloadTable('selector')` | selector → (manual) `EditableTable` |
| **(b) Seed plantilla item** | modal `seedOffer` [:146-160](frontend/src/components/model/MeasuresEntryPanel.jsx#L146-L160); oferta a [:116-117](frontend/src/components/model/MeasuresEntryPanel.jsx#L116-L117) | `confirmSeed()` → `materialitzar-poms` (POST) [:56-67](frontend/src/components/model/MeasuresEntryPanel.jsx#L56-L67) → `reloadTable('manual')` | `EditableTable` (graella sembrada) |
| **(c) Import fitxa** | targeta import [:191](frontend/src/components/model/MeasuresEntryPanel.jsx#L191) → `mode='import'` | `<ImportWizard>` [:262-268](frontend/src/components/model/MeasuresEntryPanel.jsx#L262-L268); en acabar `onComplete → onMaterialized()` | `CheckMeasureEditor` (via re-render del tab) · **o** sortida a `/size-library` ([ImportWizard.jsx:187](frontend/src/components/ImportWizard/ImportWizard.jsx#L187)) |
| **(d) Manual** | targeta manual [:177](frontend/src/components/model/MeasuresEntryPanel.jsx#L177) → `mode='manual'` | `<EditableTable>` [:229-243](frontend/src/components/model/MeasuresEntryPanel.jsx#L229-L243) amb POMs suggerits; "Veure taula" → `onMaterialized()` [:251-257](frontend/src/components/model/MeasuresEntryPanel.jsx#L251-L257) | `CheckMeasureEditor` (consulta) |

**Decisió wizard-vs-graella** (entrada al tab Mesures) — [ModelSheet.jsx:145-155](frontend/src/pages/ModelSheet.jsx#L145-L155):
`verge = !taulaRows.some(r => r.base_value_cm != null)`; `mesuresEntry = (verge || entryMode) && !taskParam`.
És a dir: `pom`/`?mode=entry`/model verge → ENTRADA (wizard); `size_check` (porta `task_id`) → TREBALL
(`CheckMeasureEditor`).

> 🎯 **Resposta directa a "quina va a la pantalla vella":** **CAP de les 4 navega a una pantalla vella.**
> Les 4 viuen dins el tab Mesures. PERÒ les vies (a),(b),(d) — i el tram d'edició de (c) abans de
> materialitzar — pinten amb **`EditableTable`** (graella heretada de l'antic `ModelMeasurements`,
> vegeu el comentari "mirall de ModelMeasurements" a [MeasuresEntryPanel.jsx:46](frontend/src/components/model/MeasuresEntryPanel.jsx#L46) i [:70](frontend/src/components/model/MeasuresEntryPanel.jsx#L70)),
> **no** amb la graella canònica `MeasureGrid`. Aquest és l'origen probable de la sensació de "pantalla
> vella": no és una ruta morta, és una **graella diferent** dins la superfície nova.

---

## PREGUNTA 4 — La destinació CANÒNICA única

Hi ha **dos nivells** de canonicitat, i el punt comú real és el segon:

**1) Contracte d'URL canònic** (el que tots els enllaços externs/tasques haurien d'usar):
- Mides treball: `/models/:id?tab=Mesures&task_id=<id>`
- Mides entrada/genesi: `/models/:id?tab=Mesures&mode=entry`
- Escalat: `/models/:id/escalat?task_id=<id>` (o `?tab=Escalat`)

Els redirects vells ([App.jsx:47-62](frontend/src/App.jsx#L47-L62)) ja normalitzen cap a aquest contracte.

**2) Punt comú INTERN (el funnel real)** — `ModelSheet`:
- `enterEdit(tab, code)` ([ModelSheet.jsx:186-200](frontend/src/pages/ModelSheet.jsx#L186-L200)) és l'única porta que obre tasca (`openTask` → InProgress,
  compta-temps) i commuta a edició.
- Totes les formes d'arribada hi conflueixen via 3 `useEffect` espills:
  - `autoEdit` (ruta `/escalat`) → `enterEdit` ([ModelSheet.jsx:217-223](frontend/src/pages/ModelSheet.jsx#L217-L223))
  - `?tab=Mesures&task_id=` (size_check) → `setEditing('Mesures')` + registre a `activeTaskRef` ([ModelSheet.jsx:230-240](frontend/src/pages/ModelSheet.jsx#L230-L240))
  - `?mode=entry` (pom) → `enterEdit('Mesures','pom')` ([ModelSheet.jsx:246-253](frontend/src/pages/ModelSheet.jsx#L246-L253))
- El cicle del compta-temps (pausa idempotent en sortir/desmuntar) viu a `pauseActiveTask` /
  `exitEdit` ([ModelSheet.jsx:180-213](frontend/src/pages/ModelSheet.jsx#L180-L213)).

**FET:** la destinació canònica única és **el tab del ModelSheet governat per `enterEdit`**; el
contracte d'URL `?tab=…[&task_id=|&mode=entry]` n'és la façana. Tots els camins de §2 ja hi apunten.

---

## Caps solts que va deixar J1 (síntesi — la foto)

> Tot el següent és **diagnòstic**. Cap reapuntat fet. Propostes marcades 💡.

1. **Divisió d'editors (el cap solt principal).** `EditableTable` (entrada/manual/seed/import-edit)
   conviu amb `MeasureGrid` (treball/consulta/escalat/fitting). Dues graelles per a mesures de base.
   *FET:* confirmat que `EditableTable` només l'usa `MeasuresEntryPanel`.
   💡 *PROPOSTA (no aplicada):* unificar l'entrada sobre `MeasureGrid`/`CheckMeasureEditor` per tancar
   la sensació de "pantalla vella".

2. **Asimetria de rutes.** `/mesures` i `/size-check` són redirects; `/escalat` és **ruta real** amb
   `autoEdit` ([App.jsx:150](frontend/src/App.jsx#L150)). Funciona, però trenca el patró "tot via `?tab=`".
   💡 *PROPOSTA:* avaluar si `/escalat` també hauria de ser `?tab=Escalat&task_id=` per simetria.

3. **Referència estancada a `KanbanTasks.jsx`** ([WorkPlan.jsx:22](frontend/src/components/model/WorkPlan.jsx#L22)): el fitxer no existeix.
   Deute documental; cap impacte funcional.

4. **Sortida lateral d'ImportWizard** a `/size-library?prefill=` ([ImportWizard.jsx:187](frontend/src/components/ImportWizard/ImportWizard.jsx#L187)): és per disseny
   (1C-3b decisió ii), però és l'únic camí que abandona el context del model durant l'entrada de mides.

5. **Rastres de comentari** als redirects i a `MeasuresEntryPanel` que citen components ja eliminats
   (`ModelMeasurements`, `EscalatTask`, `SizeCheckWork`) — útils com a història, però poden confondre.

---

### Metodologia (traçabilitat)
Investigació amb 3 investigadors de codi en paral·lel (inventari rutes · punts d'entrada · wizard) +
verificació adversarial directa del director sobre els fitxers clau (redirects, `toolRoute`, lògica
d'entrada de `ModelSheet`, `MeasuresEntryPanel`, fan-in d'`EditableTable`/`MeasureGrid`, absència de
routing al Kanban). La verificació va **refutar** la hipòtesi inicial ("manual → pantalla vella" com a
ruta) i la va reformular com a **divisió d'editors** (§5.1). Tot read-only.
