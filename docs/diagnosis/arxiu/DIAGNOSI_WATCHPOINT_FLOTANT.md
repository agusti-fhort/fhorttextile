> ⚠️ SUPERADA 2026-07-07 — implementada (WatchpointTrigger/Drawer al ModelSheet). Consulta només com a històric.

# DIAGNOSI — Watchpoint Flotant (overlay des de dalt de cada model)

**Patró:** A (read-only — cap canvi, push, migrate ni restart)
**Branca:** dev · **Entorn:** staging · **Data:** 2026-06-24
**Equip:** director-investigació + investigador-codi ×3 (entitat+backend / frontend-contenidor / fronteres-germans) + documentador (PROTOCOL_FASE_B)
**Regla de sessió:** visió global, no focal. Per cada peça: què la consumeix/alimenta, conseqüències de tocar-la, germans a reusar.
**Objectiu (a DISSENYAR, NO construir):** overlay flotant tipus xatbot, icona a dalt de cada model, desplegable per sobre de la pantalla, escriure recordatoris i veure el FIL CRONOLÒGIC (data/hora + text) de tots els watchpoints del model, independent de la pestanya activa.

---

## TL;DR

- **L'entitat i el backend JA estan COMPLETS** per a un fil obert→resolt. **Cap migració nova.**
- **El fil cronològic JA existeix com a component:** [WatchpointsPanel.jsx](frontend/src/components/model/WatchpointsPanel.jsx) (crear + llistar `-created_at` + resolve/reopen). Avui només viu DINS la pestanya Mesures ([CheckMeasureEditor.jsx:313](frontend/src/components/model/CheckMeasureEditor.jsx#L313)).
- **Punt d'ancoratge únic = `ModelSheetHeader`** ([ModelSheet.jsx:373-442](frontend/src/pages/ModelSheet.jsx#L373)), sempre visible sobre el switch de pestanyes. Allà ja viu l'`ActionsMenu`. **No cal tocar cap pestanya.**
- **Germà de presentació a reusar = `SizeSystemDrawer`** (drawer lateral overlay+panel fixed). El FIL = `WatchpointsPanel` (reusar tal qual). **Per tant l'overlay és ~90% composició de peces existents.**
- **Fronteres netes:** Dashboard (peça C), Fitxa tècnica (E) i Gates queden **FORA**. Avui els watchpoints NO es mostren al dashboard, NO bloquegen gates i NO van a la fitxa tècnica.

---

## BLOC 1 — L'ENTITAT (P6, migració 0042) — **COMPLETA**

### 1A. Model `Watchpoint` → [models.py:857-883](backend/fhort/models_app/models.py#L857)
| Camp | Tipus | Null | on_delete | Nota |
|---|---|---|---|---|
| `model` | FK→models_app.Model | NO | **CASCADE** | ancoratge obligatori al model |
| `task` | FK→tasks.ModelTask | **SÍ** | **SET_NULL** | origen (tasca on es crea); pot ser null |
| `text` | TextField | NO | — | text lliure |
| `estat` | CharField(10) | NO | — | choices `open`/`resolved`, default `open` |
| `created_by` | FK→accounts.UserProfile | SÍ | SET_NULL | autor |
| `created_at` | DateTimeField | — | — | `auto_now_add` |
| `resolved_by` | FK→accounts.UserProfile | SÍ | SET_NULL | qui resol |
| `resolved_at` | DateTimeField | SÍ | — | quan es resol |
| `resolution_note` | TextField | (blank) | — | per què es resol |

`Meta.ordering = ['-created_at']`. Migració **0042_watchpoint** ([fitxer](backend/fhort/models_app/migrations/0042_watchpoint.py)) crea exactament aquests camps (deps: accounts 0003, models_app 0041, tasks 0023). **Res a afegir.**

### 1B. Camp `estat` — cicle complet
`ESTAT_CHOICES = [('open','Oberta'), ('resolved','Resolta')]`. **La lògica de resolució existeix sencera:** `resolved_by` + `resolved_at` + `resolution_note` (qui/quan/per què), gestionada per les accions `resolve`/`reopen` del ViewSet (no només camps morts).

### 1C. FK `task` nullable — ancoratge només-model confirmat
`task` és `null=True, SET_NULL`. Un watchpoint pot viure **ancorat NOMÉS al model** (task=null vàlid). **Frontera cross-schema:** `Watchpoint`, `Model` i `ModelTask` viuen tots al **schema de tenant** (models_app + tasks són TENANT_APPS); no hi ha cap FK a `public`. `task_type_code` es deriva de `task.task_type.code` (també tenant). **Cap frontera public↔tenant problemàtica.**

---

## BLOC 2 — BACKEND — **JA EXPOSA TOT**

### 2A. `WatchpointViewSet` → [views.py:86-117](backend/fhort/models_app/views.py#L86)
- **ModelViewSet complet:** list / create / retrieve / update / destroy.
- **Filtrable:** `filterset_fields = ['model', 'estat', 'task']` → `?model=<id>&estat=open` ✓
- **Ordenable:** `ordering_fields=['created_at']`, default `-created_at` ✓ (fil cronològic natiu)
- **Permís:** `IsAuthenticated` (sense capability custom — qualsevol tècnic autenticat crea/resol).
- **Accions extra:** `POST {id}/resolve/` (posa estat+resolved_by/at+note) i `POST {id}/reopen/`.
- `perform_create` omple `created_by` des de `request.user.profile`.
- Registrat a [urls.py:41](backend/fhort/models_app/urls.py#L41) (`router.register('watchpoints', ...)`).
- Endpoints frontend ja definits a [endpoints.js:59-64](frontend/src/api/endpoints.js#L59): `list/create/resolve/reopen`.
- Serializer [serializers.py:159-172](backend/fhort/models_app/serializers.py#L159): exposa `created_by_nom`, `resolved_by_nom`, `task_type_code`; estat/autoria són `read_only` (gestionats pel servidor).

### 2B. Lògica P6 que resol la `task` d'origen — viu al FRONTEND, reusable
La decisió "agafa la ModelTask en curs del model" NO és al backend; la fa l'**ActionsMenu**: [ActionsMenu.jsx:183-186](frontend/src/components/model/ActionsMenu.jsx#L183) →
```js
const tasks = await modelTasks.list({ model: single.id, status: 'InProgress', page_size: 50 })
const enCurs = tasks.find(tk => tk.status === 'InProgress') || tasks[0]
// si no n'hi ha cap → taskId = null  (SET_NULL al backend ho accepta)
```
**Reusable des de l'overlay**: o bé es replica aquesta resolució, o bé l'overlay ancora a `task=null` (vàlid). Recomanació de disseny: reusar-la per conservar l'origen.

### 2C. CONSEQÜÈNCIES — on es llegeix avui (per no duplicar font)
- **Serializer del Model:** el `ModelDetailSerializer` NO exposa cap camp explícit de watchpoints ni comptador (no els injecta). El `ModelListSerializer` tampoc. → no hi ha agregació a mantenir.
- **Dashboard del model** (`GET /api/v1/models/<id>/dashboard/`, [views.py ~1539](backend/fhort/models_app/views.py#L1539)): **NO inclou watchpoints**; els `blockers` són només `tasks_open`.
- **Única lectura UI viva:** `WatchpointsPanel` dins `CheckMeasureEditor` (Mesures). **L'overlay ha de convergir amb aquesta MATEIXA font (l'endpoint `watchpoints.list`), no crear-ne una segona.**

---

## BLOC 3 — FRONTEND

### 3A. Handler de creació (P6) → [ActionsMenu.jsx:174-197](frontend/src/components/model/ActionsMenu.jsx#L174)
- Crida `watchpoints.create({ model, task: taskId, text })`.
- UI: reusa el `Modal` genèric ([ActionsMenu.jsx:249-262](frontend/src/components/model/ActionsMenu.jsx#L249)) amb textarea.
- **Claus i18n JA existents (ca/en/es) — l'overlay les reusa:**
  - `model_sheet.make_comment`, `model_sheet.comment_help`, `model_sheet.comment_placeholder`, `model_sheet.comment_save`, `model_sheet.comment_saved`, `model_sheet.comment_empty`
  - `watchpoints.title`, `watchpoints.open`, `watchpoints.show_resolved`, `watchpoints.hide_resolved`, `watchpoints.placeholder`, `watchpoints.add`, `watchpoints.empty`, `watchpoints.resolve`, `watchpoints.reopen`, `watchpoints.resolved_by`

### 3B. CONTENIDOR COMÚ = punt d'ancoratge únic → [ModelSheet.jsx](frontend/src/pages/ModelSheet.jsx)
- `ModelSheet()` renderitza **sempre** `<ModelSheetHeader>` ([:150](frontend/src/pages/ModelSheet.jsx#L150)) **per sobre** del switch de pestanyes ([:163](frontend/src/pages/ModelSheet.jsx#L163)) i del contingut de cada tab.
- `ModelSheetHeader` ([:373-442](frontend/src/pages/ModelSheet.jsx#L373)) ja conté `<ActionsMenu>` ([:433](frontend/src/pages/ModelSheet.jsx#L433)).
- **TABS** = `['Dashboard','Resum','Mesures','Escalat','Fitxa tècnica','Fitxers',"Registre d'activitat",'Anàlisi IA']` ([:17](frontend/src/pages/ModelSheet.jsx#L17)).
- ✅ **Hi ha UN únic punt d'ancoratge** (`ModelSheetHeader`), sempre visible, amb accés a `model` i a `reloadModel`. La icona flotant hi viu una sola vegada → **no cal tocar cap pestanya.**
- **Estat del model:** viu a `ModelSheet` via `useState` ([:84-91](frontend/src/pages/ModelSheet.jsx#L84): `model`, `activeTab`, `taulaRows`, `deltes`, `sizesAmbDades`…) + `reloadModel` ([:93](frontend/src/pages/ModelSheet.jsx#L93)).

### 3C. GERMANS de presentació (patró a reusar) — **SÍ n'hi ha**
| Patró | Fitxer:línia | Tècnica | Reusable per overlay? |
|---|---|---|---|
| **Drawer lateral** | [SizeSystemDrawer.jsx:4](frontend/src/components/SizeSystem/SizeSystemDrawer.jsx#L4) | overlay `fixed inset-0` (z200) + panell `fixed right-0` `min(680px,90vw)` (z201), tanca al clic fora, scroll intern | **SÍ — millor candidat (closest sibling)** |
| Modal centrat genèric | [ui/Modal.jsx:8](frontend/src/components/ui/Modal.jsx#L8) | `fixed inset-0` rgba + panell centrat, z50 | parcial (centrat, no lateral) |
| Drawer/modal gran wizard | [SizeAuthoringDrawer.jsx:8](frontend/src/components/SizeAuthoringDrawer.jsx#L8) | modal ample centrat z200 | parcial |
| Toast inferior | KanbanTasks/WorkPlan (`fixed bottom-24 left-50%` z60) | notificació efímera 3s | per als avisos, no el panell |
| Popover/menu | [ActionsMenu.jsx:218](frontend/src/components/model/ActionsMenu.jsx#L218) | relative+absolute + backdrop `fixed inset-0` z40 captura clics | patró de tancament-al-clic-fora reusable |

- **NO existeix cap FAB** (botó d'acció flotant) ni abstracció de portal: tots els overlays són `position:fixed` inline. La **icona disparadora és nova** (petita), però viu a `ModelSheetHeader`.
- **Recomanació:** shell de l'overlay = patró `SizeSystemDrawer` (drawer dret) + contingut = `WatchpointsPanel` (ja fet) + tancament-al-clic-fora com ActionsMenu.

### 3D. La fitxa JA llegeix watchpoints — **única font a convergir**
- `WatchpointsPanel` ([WatchpointsPanel.jsx](frontend/src/components/model/WatchpointsPanel.jsx)) és **ja el fil cronològic**: llista `-created_at`, mostra `text` + `created_by_nom · data · task_type_code` + (`resolved_by` si resolt), separa open/resolved, input crear, botons resolve/reopen. Props: `modelId`, `taskId`, `editable`.
- **Avui s'usa en UN sol lloc:** [CheckMeasureEditor.jsx:313](frontend/src/components/model/CheckMeasureEditor.jsx#L313) (pestanya Mesures, mode treball). L'overlay l'ha de **reusar**, no clonar.
- ⚠️ **Petit gap vs l'objectiu:** `fmtDate` ([:5](frontend/src/components/model/WatchpointsPanel.jsx#L5)) mostra **només data** (dd/mm/aa), NO hora. L'objectiu demana "data/hora petita" → caldria un ajust mínim a `fmtDate` (afegir hora) quan es dissenyi; afecta una sola línia.

---

## BLOC 4 — FRONTERES I CONSEQÜÈNCIES

### 4A. Dashboard (peça C) — **FORA d'àmbit de B**
[DashboardTab.jsx](frontend/src/components/model/DashboardTab.jsx) i l'endpoint `dashboard/` **NO mostren watchpoints** avui. "Les anotacions guanyen pes al dashboard" = **peça C (reordenar DashboardTab)**, que NO es construeix ara. **Frontera:** B = overlay flotant que reusa `WatchpointsPanel`; C = afegir comptador/pes a `DashboardTab`. **No colar C dins B.**

### 4B. Gates/fases — **purament informatiu, NO bloqueja**
`advance_phase_gate` ([tasks/services_d.py:25-84](backend/fhort/tasks/services_d.py#L25)) i `model_ready_for_gate` **no comproven watchpoints oberts** (els blockers són `tasks_open`). Grep `watchpoint` a `tasks/*.py` = 0. Els watchpoints "travessen els gates" (queden ancorats al model i el `task` origen es conserva via SET_NULL) **sense bloquejar cap transició**. **Frontera:** B NO toca gates; segueix sent informatiu.

### 4C. Fitxa tècnica (peça E) — **FORA d'àmbit (per disseny)**
Docstring del model: *"NO va a la fitxa tècnica"*. Grep `watchpoint` a `tech_sheet_models.py` / `tech_sheet_views.py` / frontend TechSheet = 0. **B NO toca la fitxa tècnica.**

### 4D. Risc de re-render / estat d'edició
- L'estat del model viu a `ModelSheet` (`useState`, [:84](frontend/src/pages/ModelSheet.jsx#L84)); pestanyes com Mesures/Escalat mantenen estat d'edició propi (`taulaRows`, `deltes`).
- **Risc principal:** si l'overlay (a `ModelSheetHeader`) crida `reloadModel`/`onChanged` en crear un watchpoint, **recarregaria tot el model i podria trencar una edició en curs** a Mesures/Escalat.
- **Mitigació de disseny (no implementada):** l'overlay ha de portar **estat local propi** (obert/tancat, text, items) i, en crear/resoldre, **recarregar només la seva pròpia llista** (com fa avui `WatchpointsPanel.load()`), **sense** tocar `reloadModel`. Així obrir/escriure a l'overlay no provoca re-mount de la pestanya activa.

---

## VEREDICTE

1. **L'entitat Watchpoint és COMPLETA** per a un fil cronològic open→resolved: té text, estat amb choices, created_by/at, resolved_by/at, resolution_note, i `task` nullable (SET_NULL) per ancorar només al model. **Cap migració necessària.**
2. **El backend JA exposa tot:** ViewSet CRUD filtrable per `?model` i `?estat`, ordenat `-created_at`, amb accions `resolve`/`reopen`; endpoints frontend i serializer (amb noms i `task_type_code`) ja existents. Permís: `IsAuthenticated`, sense capability custom.
3. **Punt d'ancoratge únic de l'overlay = `ModelSheetHeader`** ([ModelSheet.jsx:373](frontend/src/pages/ModelSheet.jsx#L373)), al costat de l'`ActionsMenu`, sempre visible i independent de la pestanya. No cal tocar cap pestanya.
4. **Patró de presentació a reusar:** drawer lateral `SizeSystemDrawer` (shell overlay+panell) + tancament-al-clic-fora estil `ActionsMenu`. **No existeix FAB** → la icona disparadora és l'únic element nou (petit).
5. **El que ja es reusa de P6:** el component **`WatchpointsPanel`** (és literalment el fil cronològic demanat), els endpoints `watchpoints.*`, les claus i18n `watchpoints.*` + `model_sheet.comment_*`, i la resolució de la ModelTask "InProgress" de l'`ActionsMenu`.
6. **Fronteres:** B = overlay flotant que reusa `WatchpointsPanel` ancorat al model. **FORA queden:** C (reordenar `DashboardTab` perquè les anotacions guanyin pes), E (fitxa tècnica — exclosa per disseny) i Gates (informatiu, no bloqueja).
7. **Conseqüències de tocar-ho:** mínimes i additives — afegir una icona+drawer a `ModelSheetHeader` reusant peces existents; no canvia backend, dashboard, gates ni fitxa tècnica.
8. **Migració necessària:** **NO.**
9. **Riscos:** (a) **re-render** — l'overlay ha de tenir estat local i recarregar només la seva llista, sense cridar `reloadModel`, per no trencar edicions a Mesures/Escalat; (b) **gap menor** — `WatchpointsPanel.fmtDate` mostra només data, no hora: cal un ajust d'una línia per complir "data/hora petita"; (c) **anclatge de task** a nivell de capçalera no té context de "tasca activa" com Mesures: reusar la resolució InProgress de l'ActionsMenu o ancorar a `task=null` (vàlid).

**NO implementat. Atur aquí (Patró A).**
