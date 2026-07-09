> ⚠️ SUPERADA 2026-07-07 — implementada (redisseny columna dreta + Registre a tab Planning 41c066a). Consulta només com a històric.

# DIAGNOSI — Peça C: reordenar la columna dreta del Dashboard del model

**Patró:** A (read-only — cap canvi, push ni migrate) · **Branca:** dev · **Data:** 2026-06-24
**Equip:** director-investigació + investigador-codi ×N + documentador (PROTOCOL_FASE_B)
**Objectiu (a DISSENYAR, NO construir):** substituir el bloc dret "QUÈ HA CANVIAT" per DOS contenidors apilats de consulta amb scroll propi: (1) Watchpoints del model (fil complet), (2) Registre d'activitat. A més, jubilar la pestanya "Registre d'activitat" absorbint la peça F.

---

## TL;DR — la troballa que canvia el pla

⚠️ **El pla parteix d'una confusió de fonts.** "QUÈ HA CANVIAT" i la pestanya "Registre d'activitat" **NO són la mateixa dada ni la mateixa font**:

| | "QUÈ HA CANVIAT" (bloc dret) | Pestanya "Registre d'activitat" |
|---|---|---|
| Component | `ModelTimeline` | `RegistreActivitatTab` |
| Endpoint | `GET /models/<id>/timeline/` | `GET /models/<id>/albara/` |
| Contingut | **memòria multi-font**: measure_change + gate_advance/regress + **task_transition** | **albarà**: capçalera, StatCards de temps, taula de passos, repartiment **per tècnic**, totals, rectificacions, historial de transicions |

→ El "fil de transicions de tasca" que es vol al contenidor 2 **JA viu** dins "QUÈ HA CANVIAT" (com a `kind=task_transition`). La pestanya Registre és **molt més** (comptabilitat de temps per tècnic). **Jubilar-la i reduir-la a un "fil" NO és net: perdria el detall albarà.** Cal una decisió de frontera abans de dissenyar (§Veredicte).

---

## BLOC 1 — Com es construeix el Dashboard avui

### 1A. Estructura de [DashboardTab.jsx](frontend/src/components/model/DashboardTab.jsx)
Layout = `flex flexWrap` ([:17](frontend/src/components/model/DashboardTab.jsx#L17) `grid`), dues columnes sota un `WorkPlan` d'amplada total:
- **Dalt (amplada total):** `<WorkPlan>` (Pla de treball, Q4) — [:104](frontend/src/components/model/DashboardTab.jsx#L104).
- **Columna ESQUERRA** (`wrap` = `flex:'1 1 380px', maxWidth:760`, [:18](frontend/src/components/model/DashboardTab.jsx#L18)): Q1 "On sóc / bloquejos" ([:110](frontend/src/components/model/DashboardTab.jsx#L110)), "Artefactes vigents / Què tinc fet" ([:142](frontend/src/components/model/DashboardTab.jsx#L142)), "Estat tècnic" plegable ([:212](frontend/src/components/model/DashboardTab.jsx#L212)).
- **Columna DRETA = el bloc a substituir:** `<ModelTimeline modelId={modelId} />` — [DashboardTab.jsx:240](frontend/src/components/model/DashboardTab.jsx#L240). És el "QUÈ HA CANVIAT" (Q2·Memòria). El seu contenidor propi és la `<section style={{ flex:'1 1 420px', maxWidth:560 }}>` interna de ModelTimeline ([ModelTimeline.jsx:177](frontend/src/components/model/ModelTimeline.jsx#L177)).

### 1B. Font de "QUÈ HA CANVIAT"
`GET /api/v1/models/<id>/timeline/` → `model_timeline_view` ([views.py:1671](backend/fhort/models_app/views.py#L1671)), registrat a [urls.py:185](backend/fhort/models_app/urls.py#L185). Projecta a forma comuna **3 fonts**: `MeasurementChangeLog` (measure_change), `GateEvent` (gate_advance/regress), `TaskTransition` (task_transition). Ordre `-at`. El frontend ([ModelTimeline.jsx](frontend/src/components/model/ModelTimeline.jsx)) agrupa per dia, temps relatiu, scroll intern.
**No és el mateix** que la pestanya Registre (§2).

---

## BLOC 2 — La pestanya "Registre d'activitat" (la que es vol jubilar)

### 2A. Component + dades
Pestanya `"Registre d'activitat"` ([ModelSheet.jsx:18](frontend/src/pages/ModelSheet.jsx#L18), render [:251](frontend/src/pages/ModelSheet.jsx#L251)) → `<RegistreActivitatTab modelId={id} />` ([RegistreActivitatTab.jsx](frontend/src/components/model/RegistreActivitatTab.jsx)).
Font: `GET /api/v1/models/<id>/albara/` → `consumption_delivery_view` ([views.py:1460](backend/fhort/models_app/views.py#L1460), [urls.py:183](backend/fhort/models_app/urls.py#L183)). Agrega `ModelTask`/`TimerEntrada`/`TaskTransition`. Mostra: capçalera immutable (codi, període, merited_at), **3 StatCards** (temps total, passos, rectificacions), **taula de passos** (task_type, status, minuts, inici, fi), **repartiment per tècnic** (label, minuts), i **historial** col·lapsable de transicions (from→to, by, at).

### 2B. Comparació de font — decisiu
La pestanya Registre mostra **MOLT MÉS** que "QUÈ HA CANVIAT":
- L'**únic solapament** és l'historial de transicions (`TaskTransition`), que ja és a "QUÈ HA CANVIAT" com a `kind=task_transition`.
- **El que es perdria si es jubila reduint-la a un "fil de transicions"**: comptabilitat de **temps** (minuts per pas i total), **repartiment per tècnic**, **rectificacions**, taula de passos amb inici/fi, capçalera albarà (període/merited_at). Aquesta dada **NO és al timeline**.
→ **Jubilar-la NO és net** tret que es decideixi expressament que l'albarà per-model deixa d'estar accessible des de la fitxa.

### 2C. Enllaços a la pestanya
- La pestanya només es mostra via `activeTab` intern de ModelSheet; **cap deep-link** extern a `?tab=Registre` → jubilar-la no trenca navegació.
- ⚠️ Existeix una pàgina **global** diferent: `/registre-activitat` ([RegistreActivitat.jsx](frontend/src/pages/RegistreActivitat.jsx), al Sidebar [layout/Sidebar.jsx:49](frontend/src/components/layout/Sidebar.jsx#L49)). És una **LLISTA** de models meritats amb filtres/KPIs; en clicar una fila navega a `/models/<id>` ([RegistreActivitat.jsx:168](frontend/src/pages/RegistreActivitat.jsx#L168)) — **NO al detall albarà**. Per tant el detall albarà per-model (passos/per-tècnic/totals) **avui només és accessible des de la pestanya del model**. Si es jubila la pestanya, aquest detall queda **orfe d'accés** (la pàgina global no el reemplaça).

---

## BLOC 3 — Watchpoints al dashboard (contenidor 1)

### 3A. Reusabilitat de [WatchpointsPanel.jsx](frontend/src/components/model/WatchpointsPanel.jsx)
Sí, reusable en consulta: prop `editable=false` per defecte ([:11](frontend/src/components/model/WatchpointsPanel.jsx#L11)); amb `editable={false}` no mostra ni input ni botons resolve/reopen ([:52](frontend/src/components/model/WatchpointsPanel.jsx#L52),[:78](frontend/src/components/model/WatchpointsPanel.jsx#L78)). Llista per `?model` només ([:20](frontend/src/components/model/WatchpointsPanel.jsx#L20)); `taskId` és opcional (només per crear). Muntatge: `<WatchpointsPanel modelId={modelId} editable={false} />` → fil read-only de tot el model. ✓
- ⚠️ **Matís "fil COMPLET":** per defecte el panell mostra **només les obertes** (`visible = showResolved ? items : open`, [:37](frontend/src/components/model/WatchpointsPanel.jsx#L37)); les resoltes només amb el toggle "Veure resoltes". No té prop per arrencar mostrant-ho TOT. Per a un "fil seqüencial complet" caldria un petit afegit (prop `showAllByDefault` o equivalent) — no limita per quantitat, però sí filtra per estat per defecte.

### 3B. Conseqüència del doble muntatge (drawer + dashboard)
Mateix component, mateixa font (`watchpoints.list?model`), però **cada instància té el seu propi estat `items` i el seu propi `load`** ([:13](frontend/src/components/model/WatchpointsPanel.jsx#L13),[:18](frontend/src/components/model/WatchpointsPanel.jsx#L18)). En crear al drawer (B), la instància del dashboard (C) **NO es refresca sola** → queda obsoleta fins a remuntar/recarregar. **Risc:** incoherència temporal entre les dues vistes; no estan acoblades (és el mateix patró que el badge de la capçalera). Identificat, no resolt.

---

## BLOC 4 — Scroll propi i layout

### 4A. Patró de scroll intern — ja existeix (germà a reusar)
`ModelTimeline` **ja implementa** "capçalera fixa + llista amb scroll intern": [ModelTimeline.jsx:133](frontend/src/components/model/ModelTimeline.jsx#L133) `maxHeight:'75vh', overflowY:'auto'` + capçaleres de dia `position:sticky` ([:29](frontend/src/components/model/ModelTimeline.jsx#L29)). És el patró exacte a reusar per als dos contenidors.
- ⚠️ `WatchpointsPanel` **NO té scroll propi** (renderitza tots els ítems en línia). Contenidor 1 necessitarà un **wrap amb `maxHeight + overflowY`** al voltant del panell (copiant el patró de ModelTimeline). Dos contenidors apilats amb scroll independent → cadascun amb el seu `maxHeight` (p.ex. `calc()` o `vh` repartit), no un sol scroll comú.

### 4B. Amplada
Avui: dreta `maxWidth:560` (ModelTimeline §177), esquerra `maxWidth:760` (`wrap`). El `grid` és flex amb `flexWrap`, responsiu. Passar la dreta a ~50% (`flex:'1 1 0'` igualat amb l'esquerra) **rebalanceja** sense trencar res estructural; l'únic efecte sobre l'esquerra és reduir el seu `maxWidth` efectiu (conté cards i seccions, s'hi adapta). Impacte menor, no hi ha reestructuració de columna.

---

## BLOC 5 — Fronteres

### 5A. B (drawer) ↔ C (dashboard)
- **B** = escriure watchpoints des de qualsevol pestanya (drawer flotant a la capçalera, `editable=true`).
- **C** = consultar-los al dashboard (`editable=false`).
- Comparteixen `WatchpointsPanel` + font `watchpoints.list?model`. **No es dupliquen** dades; mateixa peça, dos modes. Frontera neta. L'únic acoblament a vigilar és la coherència del §3B (staleness entre instàncies).

### 5B. Backend
**Cap canvi de backend necessari.** `/timeline/`, `/albara/` i `watchpoints` ja existeixen. La peça C és **100% recomposició frontend** (reordenar DashboardTab + reusar WatchpointsPanel + decidir què alimenta el contenidor 2). La decisió de "què és Registre al contenidor 2" és de producte/frontend, no de dades.

---

## VEREDICTE

El bloc "QUÈ HA CANVIAT" és `<ModelTimeline>` a [DashboardTab.jsx:240](frontend/src/components/model/DashboardTab.jsx#L240), alimentat per `GET /models/<id>/timeline/` ([views.py:1671](backend/fhort/models_app/views.py#L1671); fonts MeasurementChangeLog + GateEvent + TaskTransition). La pestanya "Registre d'activitat" (`RegistreActivitatTab` → `GET /models/<id>/albara/`, [views.py:1460](backend/fhort/models_app/views.py#L1460)) mostra **MÉS**: temps per tècnic, totals, rectificacions, passos amb inici/fi i historial de transicions. **Jubilar-la NO és net**: l'únic solapament (transicions) ja és al timeline; es perdria tota la comptabilitat albarà, que avui **només** és accessible des d'aquesta pestanya (la pàgina global `/registre-activitat` és una llista, no el detall). `WatchpointsPanel` és reusable al dashboard amb `editable={false}`: **sí** (matís: per defecte només mostra obertes; per al "fil complet" cal una prop). Patró de scroll intern a reusar: **`ModelTimeline` (`maxHeight + overflowY` + sticky header)** — `WatchpointsPanel` no en té i necessitarà wrap. Amplada 50%: **no afecta estructuralment** l'esquerra (només redueix el seu maxWidth). Risc de coherència drawer↔dashboard: instàncies independents de WatchpointsPanel → la del dashboard queda obsoleta en crear al drawer fins a recàrrega. Backend: **cap canvi** (100% frontend).

**Decisió de frontera a prendre abans de dissenyar (no és tècnica, és de producte):** què és el "contenidor 2"?
- **(a) Fil de transicions de tasca** → reusar `/timeline/` filtrat a `kind=task_transition` (o l'historial de l'albarà). Net i lleuger, però **jubilar la pestanya perdria l'albarà** (temps/per-tècnic/totals) de la fitxa → caldria reubicar aquest detall (p.ex. fer que `/registre-activitat` global obri el detall albarà) per no perdre accés.
- **(b) Albarà sencer** → muntar `RegistreActivitatTab` dins el contenidor 2; conserva tota la dada però **no és un "fil seqüencial"** i no encaixa bé en un contenidor estret amb scroll (StatCards + múltiples taules).

Conseqüències de jubilar la pestanya (si s'acorda): treure de [ModelSheet.jsx](frontend/src/pages/ModelSheet.jsx) l'entrada a `TABS` ([:18](frontend/src/pages/ModelSheet.jsx#L18)), `TAB_LABELS` ([:27](frontend/src/pages/ModelSheet.jsx#L27)) i el render ([:251](frontend/src/pages/ModelSheet.jsx#L251)); l'import de `RegistreActivitatTab` ([:11](frontend/src/pages/ModelSheet.jsx#L11)) queda orfe si NO es reusa al contenidor 2 (i amb ell les claus i18n `albara.*` + `model_sheet.tab_activity_log`). La pàgina global `/registre-activitat` i el seu nav **no es toquen**.

**NO implementat. Atur aquí (Patró A).**
