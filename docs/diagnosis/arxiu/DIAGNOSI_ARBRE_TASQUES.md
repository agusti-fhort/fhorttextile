> ⚠️ SUPERADA 2026-07-07 — implementada (fase al serializer + TaskTree, 3584542/1f2311d/3ff9455). Consulta només com a històric.

# DIAGNOSI — Arbre de selecció de tasques al Model Sheet

> Patró A, **READ-ONLY absolut**. Cap canvi, cap commit, cap push. Data: 2026-06-29.
> Abast: `frontend/src/pages/ModelSheet.jsx` + `backend/fhort/tasks/` (models/serializers/views/urls).
> FETS amb `fitxer:línia`. 💡 = proposta d'encaix. ⚖️ = decisió per a l'Agus.
> Objectiu: afegir un ARBRE (FASE → TIPUS DE TASCA → "Iniciar") que permeti al tècnic iniciar una
> tasca des del Model Sheet encara que no estigui assignada/planificada prèviament ("Sprint 2 Q2",
> mai entrat).

---

## RESUM EXECUTIU

- **El backend JA ho suporta tot.** L'endpoint `open-task` (POST `/api/v1/models/<id>/open-task/`)
  és **idempotent i crea-si-falta**: rep un `{code}` de TaskType, crea la `ModelTask` si no existeix
  i la posa `InProgress` (auto-assign + timer + fase Pending→Dev). No cal endpoint nou per **iniciar**.
- **El que falta és pura UI** + **un camp al serializer**: avui no hi ha cap pantalla que llisti
  els `TaskType` **agrupats per FASE** amb un botó "Iniciar". El catàleg existeix
  (`/task-types`, read-only) i el wizard d'assignació existeix (`TaskAssignWizard`), però cap dels
  dos és l'arbre fase→tipus→iniciar dins el Model Sheet.
- **Forat de dades:** `TaskTypeSerializer` **NO exposa `fase`**
  ([serializers_b.py:7-10](../../backend/fhort/tasks/serializers_b.py#L7-L10)). Sense `fase` al
  payload, el front no pot agrupar per fase amb l'endpoint estàndard. **És el bloqueig principal.**
- **No duplica el Kanban.** El Kanban viu al Dashboard global (per-model), i el `WorkPlan` del tab
  Dashboard del Model Sheet llista **només les ModelTask que ja existeixen**. L'arbre **complementa**:
  ofereix iniciar TaskTypes que **encara no són** ModelTask.
- L'"arbre global" (`origen='ad_hoc'`, Sprint 4) està **només esmentat en comentaris**; mai implementat
  ([models.py:66-69](../../backend/fhort/tasks/models.py#L66-L69),
  [serializers_b.py:26](../../backend/fhort/tasks/serializers_b.py#L26)).

---

## 1) MODEL SHEET actual — seccions/tabs

**Component principal:** `ModelSheet` — [ModelSheet.jsx:83](../../frontend/src/pages/ModelSheet.jsx#L83)
(`export default function ModelSheet({ defaultTab = 'Dashboard', autoEdit = null })`).

**Rutes** (App.jsx):
- [App.jsx:183](../../frontend/src/App.jsx#L183) — `models/:id` → ModelSheet (tab Dashboard per defecte).
- [App.jsx:189](../../frontend/src/App.jsx#L189) — `models/:id/escalat` → `defaultTab="Escalat" autoEdit="Escalat"`.
- [App.jsx:191](../../frontend/src/App.jsx#L191) — `models/:id/fitxers` → `defaultTab="Fitxers"`.

**Tabs** — [ModelSheet.jsx:22](../../frontend/src/pages/ModelSheet.jsx#L22):
`['Dashboard', 'Resum', 'Mesures', 'Escalat', 'Fitxa tècnica', 'Fitxers', "Registre d'activitat"]`.
Etiquetes i18n a [ModelSheet.jsx:24-32](../../frontend/src/pages/ModelSheet.jsx#L24-L32). Render dels
botons de tab a [ModelSheet.jsx:346-358](../../frontend/src/pages/ModelSheet.jsx#L346); `activeTab` a
[:99](../../frontend/src/pages/ModelSheet.jsx#L99). Query params: `?tab=` (:93), `?task_id=` (:94),
`?mode=entry` (:97).

| Tab | Component | Fitxer:línia |
|---|---|---|
| Dashboard | `DashboardTab` | import [ModelSheet.jsx:14](../../frontend/src/pages/ModelSheet.jsx#L14); render [:375-381](../../frontend/src/pages/ModelSheet.jsx#L375); fitxer `components/model/DashboardTab.jsx` |
| Resum | `TabSummary` (local) | [ModelSheet.jsx:762-1170](../../frontend/src/pages/ModelSheet.jsx#L762) |
| Mesures | `CheckMeasureEditor` / `MeasuresEntryPanel` | [ModelSheet.jsx:402-470](../../frontend/src/pages/ModelSheet.jsx#L402) |
| Escalat | `PropagatedEditor` | render [ModelSheet.jsx:473-493](../../frontend/src/pages/ModelSheet.jsx#L473) |
| Fitxa tècnica | `TechSheetTab` (local) | [ModelSheet.jsx:530-634](../../frontend/src/pages/ModelSheet.jsx#L530) |
| Fitxers | `TabFiles` (local) | [ModelSheet.jsx:1191-1435](../../frontend/src/pages/ModelSheet.jsx#L1191) |
| Registre d'activitat | `RegistreActivitatTab` | render [ModelSheet.jsx:521](../../frontend/src/pages/ModelSheet.jsx#L521) |

**Capçalera + accions:** `ModelSheetHeader` [ModelSheet.jsx:636-697](../../frontend/src/pages/ModelSheet.jsx#L636)
(render :335) i `ActionsMenu` [components/model/ActionsMenu.jsx](../../frontend/src/components/model/ActionsMenu.jsx)
(render ModelSheet.jsx:688): assign · production · fitting · convene_fitting · advance · back.

---

## 2) TASQUES al Model Sheet avui

- **Estat carregat:** `modelTaskRows` [ModelSheet.jsx:101](../../frontend/src/pages/ModelSheet.jsx#L101),
  via `modelTasks.listByModel(id)` ([:125-126](../../frontend/src/pages/ModelSheet.jsx#L125),
  reload a :110-128). Llista **només les ModelTask que ja existeixen** per al model.
- **Superfície de tasques visible = tab Dashboard → `WorkPlan`:**
  `DashboardTab` importa i renderitza `WorkPlan`
  ([DashboardTab.jsx:5](../../frontend/src/components/model/DashboardTab.jsx#L5),
  render [:130](../../frontend/src/components/model/DashboardTab.jsx#L130)).
  `WorkPlan` pinta la llista de tasques amb controls de transport (Play/Pause) i `playMine()` crida
  `models.openTask(modelId, task.task_type_code)`
  ([WorkPlan.jsx:235-256](../../frontend/src/components/model/WorkPlan.jsx#L235), crida a :240).
  🔴 **Limitació:** `WorkPlan` itera sobre `tasques` (ModelTask existents). **No** ofereix iniciar un
  TaskType que encara no és ModelTask.
- **Botons d'entrada a tasca des dels tabs** (camí "open-task"):
  - Mesures: "Iniciar POM" [ModelSheet.jsx:419-425](../../frontend/src/pages/ModelSheet.jsx#L419) i
    "Editar mides" [:443-449](../../frontend/src/pages/ModelSheet.jsx#L443) → `enterEdit('Mesures','pom')`.
  - Escalat: "Editar escalat" [:483-489](../../frontend/src/pages/ModelSheet.jsx#L483) →
    `enterEdit('Escalat','grading')`.
  - `enterEdit(tab, code)` [ModelSheet.jsx:197-211](../../frontend/src/pages/ModelSheet.jsx#L197) crida
    `models.openTask(parseInt(id), code)` (:200) i registra `activeTaskRef` per pausar.
  - Pausa idempotent: `pauseActiveTask()` [:191-196](../../frontend/src/pages/ModelSheet.jsx#L191) →
    `modelTasks.transition(tid, { to_status:'Paused' })`; cleanup a `exitEdit()` [:212-217] i unmount [:235-237].
- **Consum de tasca per URL** (patró Size Check J1b): `?task_id=` [:254-264](../../frontend/src/pages/ModelSheet.jsx#L254)
  entra en edició SENSE encunyar tasca nova.

→ **Estat de cada peça:** mostrar tasques existents = ✅ (WorkPlan). Iniciar tasca **no existent** des del
Model Sheet de forma genèrica (qualsevol TaskType, navegant per fase) = 🔴 **no existeix**.

---

## 3) TASKTYPE — catàleg de tipus de tasca

**Model `TaskType`** — [models.py:21-59](../../backend/fhort/tasks/models.py#L21):
- `code` SlugField unique [:38] · `name` [:39] · `default_order` (ordre canònic global) [:40] ·
  `active` [:41] · **`fase`** CharField choices, default 'Dev. tècnic' [:43] · `tipus` [:44] ·
  `eina` (slug d'eina) [:45-47] · `mode` [:48-49] · `facturable` [:50].
- Meta `ordering = ['default_order', 'code']` [:52-55].

**FASE_CHOICES** (6 fases, és un **CharField choices**, NO un model Phase) —
[models.py:26-33](../../backend/fhort/tasks/models.py#L26):
`Disseny · Dev. tècnic · Prototip · Mostres · Preproducció · Producció`.
(El `Model` té el mateix `FASE_CHOICES` a `models_app/models.py:94-101`, camp `fase_actual`.)

**Serializer `TaskTypeSerializer`** — [serializers_b.py:7-10](../../backend/fhort/tasks/serializers_b.py#L7):
fields = `['id', 'code', 'name', 'default_order', 'active']`.
⚠️ **`fase` NO s'exposa** → el front no pot agrupar per fase amb aquest endpoint.

**Endpoint llista** — `TaskTypeViewSet` (ReadOnlyModelViewSet) [views_b.py:29-39](../../backend/fhort/tasks/views_b.py#L29);
ruta `task-types` (DefaultRouter) [urls.py:12-17](../../backend/fhort/tasks/urls.py#L12) →
GET `/api/v1/task-types/` (filtra per `active`). Front: `taskTypes.list(params)`
[endpoints.js:180-185](../../frontend/src/api/endpoints.js#L180).

**Model `ModelTask`** (instància) — [models.py:61-101](../../backend/fhort/tasks/models.py#L61):
`model` FK [:70] · `task_type` FK PROTECT [:71] · `status` ∈ {Pending, Paused, InProgress, Done} [:63-64,:72] ·
`origen` ∈ {prevista, ad_hoc} default 'prevista' [:69,:73] · `assignee` FK SET_NULL [:74-75] · `order` [:76] ·
`started_at`/`finished_at` [:77-78] · `estimated_minutes` snapshot [:79-80] · `planned_*` (motor) [:82-87].
Meta: `ordering=['model','order']` [:92], **`unique_together=[('model','task_type')]`** [:97] → **una sola
ModelTask per (model, tipus)**.

---

## 4) CREAR / INICIAR una tasca — endpoint i validació

**Endpoint:** `open_model_task_view` — [views_b.py:468-526](../../backend/fhort/tasks/views_b.py#L468);
ruta POST `/api/v1/models/<model_id>/open-task/` [urls.py:59](../../backend/fhort/tasks/urls.py#L59).
**Body:** `{ "code": "<task_type_code>" }`. **Resposta:** `{ task_id, code, created, status, missing_config }`.
Permís: capability `execute_tasks`.

**Lògica (crea-si-falta + inicia):**
- Allow-list: `if code not in get_allowed_task_types(request.user)` → 403 (admin bypassa)
  [views_b.py:495](../../backend/fhort/tasks/views_b.py#L495).
- Cerca existent: `ModelTask.objects.filter(model=model, task_type=tt).first()` [:499]; si no hi és, la
  **crea** amb `status='Pending'`, `order=count`, `estimated_minutes` snapshot [:501-506].
- Si no és InProgress → `transition_task(task, 'InProgress', profile)` [:508-512]; si ja és InProgress
  d'un altre tècnic → **self-claim** sense re-transició [:513-519].
- Config check = **soft gate** (F4): informa `missing_config` però **no bloqueja** [:521-525].

**`transition_task`** — [services_c.py:46](../../backend/fhort/tasks/services_c.py#L46):
- Transicions permeses [:10-16]: Pending→InProgress · Paused→InProgress · InProgress→{Paused,Done} ·
  Done→InProgress (reobertura).
- **Una sola InProgress per tècnic** (global): en entrar a InProgress, pausa l'altra InProgress del
  mateix `assignee` i tanca el seu timer [:58-67].
- **Auto-assign** si `assignee_id is None` [:82-83]. Timer `_open_timer` [:69]; `started_at` [:70-71].
- **Fase del model** Pending→Dev en primera InProgress [:90-95]. Meritació/consum (no fatal) [:97-123].

**Front:** helper `models.openTask(id, code)` [endpoints.js:34](../../frontend/src/api/endpoints.js#L34).
Call sites: `ModelSheet.jsx:200` (`enterEdit`) i `WorkPlan.jsx:240` (`playMine`).
Transició: `modelTasks.transition(id, data)` [endpoints.js:173](../../frontend/src/api/endpoints.js#L173).

→ **Conclusió:** per **iniciar** una tasca des de l'arbre NO cal backend nou. Només cal cridar
`openTask(model_id, code)` amb el `code` triat. El backend crea+inicia+assigna+timer.

---

## 5) EL QUE JA EXISTEIX de "l'arbre"

- **Catàleg read-only `/task-types`:** `TaskTypes.jsx` [pages/TaskTypes.jsx:1-61](../../frontend/src/pages/TaskTypes.jsx#L1)
  (ruta [App.jsx:201](../../frontend/src/App.jsx#L201)) — taula plana (code/name/order/active). NO agrupa
  per fase, NO té "Iniciar". És només referència.
- **`TaskAssignWizard`** [components/TaskAssignWizard.jsx:43-453](../../frontend/src/components/TaskAssignWizard.jsx#L43):
  modal que tria **un** `task_type` + tècnic + dates i **assigna** (no inicia) en bloc. Selector de
  TaskType a [:215-235]; carrega `taskTypes.list({page_size:200})` [:66-73]. Usat a Planning i ActionsMenu.
  → és **assignació planificada**, no l'arbre fase→iniciar del tècnic.
- **`TimeTree`** [components/planning/TimeTree.jsx](../../frontend/src/components/planning/TimeTree.jsx)
  ("Arbre consultiu de temps", :6): arbre fase|tipus-de-peça → task_type → item, **només per a
  ESTIMACIONS de temps** (GET `time-analysis/tree/`). NO inicia tasques. Patró d'arbre reaprofitable
  visualment, però propòsit diferent.
- **"Arbre global" (`origen='ad_hoc'`, Sprint 4):** només en comentaris
  ([models.py:66-69](../../backend/fhort/tasks/models.py#L66),
  [serializers_b.py:26](../../backend/fhort/tasks/serializers_b.py#L26)); el camp `origen` mai s'escriu a
  `ad_hoc` (sempre default 'prevista'). **Mai implementat.** `WorkPlan` ja té el pintat preparat
  (`isOutOfCharge` = filet grana per `origen==='ad_hoc'`)
  [WorkPlan.jsx:72-74](../../frontend/src/components/model/WorkPlan.jsx#L72).
- **No s'ha trobat** cap stub/modal de "selecció de tasques" fase→tipus→iniciar.

---

## 6) DUPLICACIÓ / CONFLICTE amb el Kanban

- **Kanban global per-model:** viu al Dashboard home (`/`) — `ModelBoard`
  [pages/Dashboard.jsx:125-320](../../frontend/src/pages/Dashboard.jsx#L125), 4 columnes
  (pending/open/paused/done) [:28-33], dades via `modelTasks.byModel`
  [endpoints.js:166](../../frontend/src/api/endpoints.js#L166). La pàgina Kanban global antiga i
  `Tasks.jsx` estan **jubilades** ([App.jsx:198-200](../../frontend/src/App.jsx#L198)).
- **WorkPlan (tab Dashboard del Model Sheet):** llista les ModelTask del model amb transport.
- **No hi ha conflicte:** el Kanban i el WorkPlan operen sobre ModelTask **ja existents**. L'arbre
  cobreix el buit: **iniciar TaskTypes que encara no són ModelTask**. Tots tres comparteixen el mateix
  motor (`openTask`/`transition`), de manera que un cop l'arbre crea la tasca, apareix al WorkPlan i al
  Kanban automàticament. **Complementa, no duplica.**

---

## 7) 💡 PROPOSTA INICIAL d'encaix

### Backend (mínim, 1 canvi)
💡 **Exposar `fase` (i potser `eina`, `mode`, `facturable`) al `TaskTypeSerializer`**
([serializers_b.py:10](../../backend/fhort/tasks/serializers_b.py#L10)). És additiu i read-only; cap
migració. Sense això el front no pot agrupar per fase amb `/api/v1/task-types/`.
- ⚖️ Alternativa sense tocar backend: agrupar al front amb un mapa `code → fase` hardcodat (fràgil;
  desaconsellat). Recomanat exposar `fase`.

### Frontend (UI nova, reaprofitant handlers)
💡 **Component `TaskTree`** que:
1. `taskTypes.list({ active: true })` → agrupa per `fase` (ordre de `FASE_CHOICES`), dins cada fase
   ordena per `default_order`.
2. Marca quins TaskTypes **ja són** ModelTask (creuant amb `modelTaskRows`) per mostrar estat
   (no-iniciada / en-curs / feta) i evitar sorpreses — reusant `modelTasks.listByModel(id)` que el
   Model Sheet ja carrega ([ModelSheet.jsx:101,125](../../frontend/src/pages/ModelSheet.jsx#L101)).
3. Botó **"Iniciar"** per TaskType → `models.openTask(id, code)` (mateix camí que `enterEdit`/`playMine`)
   i, si el TaskType té `eina`/`mode`, navega a l'eina (reusar `toolRoute`/`toolTab` de
   [WorkPlan.jsx](../../frontend/src/components/model/WorkPlan.jsx)); registrar `activeTaskRef` per pausar.

**On col·locar-lo** (opcions per a ⚖️):
- **(A) Dins el tab Dashboard, sota/al costat de `WorkPlan`** com a secció "Iniciar una tasca"
  (col·lapsable). Avantatge: no afegeix tab; conviu amb la llista de tasques existents.
- **(B) Tab nou "Tasques"** a `TABS` ([ModelSheet.jsx:22](../../frontend/src/pages/ModelSheet.jsx#L22))
  que unifiqui WorkPlan (existents) + TaskTree (iniciar). Més net conceptualment; afegeix un tab.
- **(C) Botó/acció a `ActionsMenu`** ("Iniciar tasca…") que obre un modal `TaskTree` (reusant el
  patró de `TaskAssignWizard`). Mínima petjada visual; menys descobrible.
- 💡 Recomanació: **(A)** com a MVP (mínim risc, descobrible des d'on ja es veuen les tasques), amb
  porta oberta a (B) si creix.

### Ja existeix vs cal construir
| Peça | Estat | On |
|---|---|---|
| Endpoint iniciar tasca (`open-task`, crea+inicia) | ✅ existeix | [views_b.py:468](../../backend/fhort/tasks/views_b.py#L468) |
| Llista TaskTypes (GET) | ✅ existeix | [views_b.py:29](../../backend/fhort/tasks/views_b.py#L29) / [endpoints.js:180](../../frontend/src/api/endpoints.js#L180) |
| `fase` al payload de TaskType | 🔴 cal afegir | [serializers_b.py:10](../../backend/fhort/tasks/serializers_b.py#L10) |
| Llista ModelTask del model (per marcar estat) | ✅ existeix | [endpoints.js:163](../../frontend/src/api/endpoints.js#L163) |
| Helper `openTask(id, code)` + `toolRoute`/`toolTab` | ✅ existeix | [endpoints.js:34](../../frontend/src/api/endpoints.js#L34), WorkPlan.jsx |
| Component arbre fase→tipus→Iniciar | 🔴 cal construir | nou `TaskTree` |
| Patró de pausa (`activeTaskRef`/`exitEdit`) | ✅ reaprofitable | [ModelSheet.jsx:191-217](../../frontend/src/pages/ModelSheet.jsx#L191) |

---

## ⚖️ DECISIONS per a l'Agus

1. **Exposar `fase` al `TaskTypeSerializer`?** (recomanat sí; additiu, sense migració). Afegir també
   `eina`/`mode` permetria a l'arbre navegar directament a l'eina en iniciar.
2. **Ubicació de l'arbre:** (A) secció dins tab Dashboard · (B) tab nou "Tasques" · (C) modal des
   d'ActionsMenu. (Recomanat A com a MVP.)
3. **Filtrar TaskTypes per allow-list del tècnic?** `open-task` ja valida `get_allowed_task_types`
   ([views_b.py:495](../../backend/fhort/tasks/views_b.py#L495)). ⚖️ Mostrar a l'arbre **tots** els
   TaskTypes (i deixar que el 403 talli) o **només** els permesos? Recomanat: mostrar només els
   permesos (millor UX) — caldria un endpoint/camp que retorni l'allow-list al front (avui no exposat).
4. **Marcar `origen='ad_hoc'` quan s'inicia des de l'arbre?** El camp i el pintat (`isOutOfCharge`,
   filet grana) ja existeixen però `open-task` sempre crea amb `origen='prevista'`. ⚖️ Si l'arbre ha
   de distingir "fora d'encàrrec", caldria que `open-task` accepti/forci `ad_hoc` en aquest camí
   (petit canvi de backend a [views_b.py:505](../../backend/fhort/tasks/views_b.py#L505)).
5. **Estat per TaskType ja iniciat:** mostrar "En curs/Fet" i reconvertir "Iniciar"→"Continuar"
   (reusant la lògica de transport de `WorkPlan`) per evitar duplicar la percepció amb el WorkPlan.

---

*Diagnosi read-only. Cap fitxer de codi tocat. Cap commit, cap push.*
*Línies citades: verificades directament (serializers_b.py, ModelSheet/DashboardTab/WorkPlan, endpoints.js,
open-task) o reportades pels exploradors (views_b.py, services_c.py, models.py, urls.py); revalidar abans
d'implementar si han passat commits concurrents.*
