# DIAGNOSI — Bulk, filtres i gestió de tasques de planificació

> Data: 2026-07-20 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, schema `fhort`.
> Abast: (A) superfícies de selecció múltiple + contracte de filtres de models; (B) esborrat de
> tasques Pending i convergència del formulari "Nou fitting" amb el camí del planificador.
> Convenció: cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi** (no especulat).
> Mapa previ: `DIAGNOSI_KANBAN_PLANIFICACIO` (21/06, pre-pla-únic S15) — TOTS els anclatges re-verificats
> post-S15 (el pla únic ha tocat ordre, recompute i invalidacions).

---

## Resum executiu (les conclusions que desbloquegen la decisió)

1. **El risc "select-all de 961 models" NO està exposat avui.** Models list limita la selecció als **25 de
   la pàgina visible** (no hi ha "seleccionar tot el filtrat"); Planning **no té select-all** (fila a fila).
   Cap payload bulk admet un CONJUNT/filtre — tots són **llistes d'IDs explícits del client**.
2. **El punt de trencament latent és `plan/assign-batch/`**: accepta `model_ids` de mida **il·limitada**,
   corre en **una sola transacció atòmica** amb bucle intern O(models×assignacions) + recompute de cua
   sencera per tècnic. Si algun dia s'afegeix "aplicar a tot el filtrat", aquest endpoint és el que peta.
3. **DELETE de ModelTask JA existeix per API** (`destroy` per defecte del ViewSet, gate `DEFINE_TASKS`),
   però **mort a la UI** i **sense cap neteja de pla**. Esborrar una **Pending pura** és estructuralment
   segur (0 fills CASCADE); esborrar una Pending **planificada** amb la `destroy()` crua deixa la cua del
   tècnic i `predicted_*` incoherents (no replica la cascada d'`unassign`).
4. **Contracte de filtres = dos punts d'entrada mirall** (`ModelFilter` i `by_model`) amb el mateix conjunt
   de paràmetres. **Asimetria de frontend**: el board del Dashboard exposa més eixos (customer/collection/dates)
   que la pròpia llista de Models (només search/fase/temporada).
5. **Camps de grading i watchpoints NO viatgen a cap llistat** (ni `size_system`, ni `grading_rule_set`,
   ni comptador de watchpoints oberts). El board porta counts/kanban_state; el ModelListSerializer no.
6. **"Nou fitting" i el planificador són funcions separades sense servei compartit.** `schedule_session`
   és un superconjunt estricte de `create_session`; convergibles tècnicament, però avui divergeixen en 7
   passos (estat, franja, attendees, recompute, guard, Production, visibilitat al calendari).

---

# BLOC A — Models: filtres i selecció

## A1 · Inventari de superfícies bulk (P1)

Només **DUES** superfícies tenen selecció múltiple + accions bulk. El **Dashboard board NO té selecció**
(`Dashboard.jsx` cards → `onClick navigate('/models/'+id)`, cap checkbox).

### Models list — `frontend/src/pages/Models.jsx`
- Estat de selecció: Set d'ids client — `Models.jsx:26`.
- Select-all: checkbox "tots" `Models.jsx:106` (`allOnPage`, `toggleAll` a `:54-58`) → marca **només la pàgina
  carregada** (`items`, 25). `selectedModels` (`:50`) = `items.filter(...)` → mai supera la pàgina.
  **NO EXISTEIX "seleccionar tot el filtrat".**
- Accions bulk via `ActionsMenu` (`Models.jsx:80`, `targets={selectedModels}`):

| Acció | Frontend | Endpoint | Mètode | Execució |
|---|---|---|---|---|
| Assign tasques | `plan.assignBatch` `endpoints.js:326` | `/api/v1/plan/assign-batch/` | POST | 1 crida batch (`TaskAssignWizard`) |
| Enviar a producció | `productions.requestProduction` `endpoints.js:299` | `/api/v1/models/{id}/request-production/` | POST | **loop per-model** (`runBulk`) |
| Avançar fase | `models.gate` `endpoints.js:62` | `/api/v1/models/{id}/gate/` | POST | **loop per-model** |
| Retrocedir fase | `models.regress` `endpoints.js:63` | `/api/v1/models/{id}/regress/` | POST | **loop per-model** |
| Assignar a comanda | `commerce.orderLines.assignModel` `endpoints.js:446` | `/api/v1/commerce/order-lines/{id}/assign-model/` | POST | **loop per-model** |
| Convocar fitting bulk | `fittingSessions.scheduleBulk` `endpoints.js:538` | `/api/v1/fitting-sessions/schedule-bulk/` | POST | 1 crida per FASE |

- `runBulk` (`ActionsMenu.jsx`) = **bucle client seqüencial** `for (const m of list) { await perModel(m) }` → **1 request HTTP
  per model**, feedback agregat "X fet / Y omesos", **no transaccional globalment** (fallada parcial deixa fets aplicats).

### Planning — `frontend/src/pages/Planning.jsx`
- Estat: Set de model_ids (tab Pendents) — `Planning.jsx:117`.
- Checkbox **només per-fila** `Planning.jsx:295` (`toggleSel` `:239`). **NO EXISTEIX checkbox "seleccionar tot"** en aquest panell.
- Única acció bulk: botó (`:269-272`) → modal `TaskAssignWizard` (`:326-332`) → **`assign-batch`**.
- Altres accions de Planning són **per-element**: unassign (`:244`), reassign PATCH (`:251`), reorder DnD (`:232`).

**Veredicte A1:** dues superfícies bulk, ambdues per **IDs explícits de la pàgina/selecció manual**. Cap "conjunt filtrat".

## A2 · Contracte de filtres (P2)

### Backend — Model list: `ModelFilter` + `ModelViewSet` (`backend/fhort/models_app/views.py`)
- `class ModelFilter(FilterSet)` `views.py:27`: `collection` icontains (`:35`), `data_objectiu` DateFromToRange
  (`:36` → `_after`/`_before`), `Meta.fields = [fase_actual, garment_type, responsable, temporada, any, customer,
  collection, data_objectiu]` (`:40-41`).
- `ModelViewSet` `views.py:44`: `filterset_class=ModelFilter` (`:47`), `search_fields=[codi_intern, codi_client,
  nom_prenda]` (`:48`), `ordering_fields=[prioritat, data_objectiu, data_entrada]` (`:49`), default `-prioritat` (`:50`).
- `fase-counts` (`:98`) reusa `filter_queryset` (mateix FilterSet) però tracta `responsable` com **assignee** (`:118-131`).

### Backend — board: `by_model` (`backend/fhort/tasks/views_b.py:83`)
Params (additius AND, invàlids ignorats): `search` (`:113-118`), `all=true` (`:208`), `temporada` (`:124-126`),
`estat` (`:127-129`), `fase_actual` (`:130-132`), `responsable=me|<id>` **assignee** (`:134-145`), `garment_type`
(`:147-149`), `any` (`:150-152`), `prioritat` (`:153-155`), `customer` (`:160-162`), `collection` (`:163-165`),
`data_objectiu_after/before` (`:166-173`), `ordering` whitelist `_ORDERING` (`:69-77`). És **mirall additiu** de
`ModelFilter` (comentari `:157-159`). Divergència coneguda: `responsable` = director (FilterSet) vs assignee (`by_model`/`fase-counts`).

### Frontend — exposició
- **Models list** (`Models.jsx`): només `search`, `fase`, `temporada` (`:22-24`, `:31-34`). **NO exposa** customer,
  collection, garment_type, responsable, any, data_objectiu, prioritat, ordering (fix a `-data_entrada`).
- **Dashboard board** (`Dashboard.jsx:137-151`): search, temporada, fase_actual, customer, collection,
  data_objectiu_after/before, responsable(me). **NO exposa** garment_type, any, prioritat, estat, ordering.
- **TROBALLA TRANSVERSAL:** el board exposa MÉS eixos que la llista de Models pròpia — la llista és la superfície menys equipada.

### Paginació
- Backend: `settings.py:217-218` (`DefaultPagination`, `PAGE_SIZE=25`); `fhort/pagination.py` `DefaultPagination(PageNumberPagination)`
  `page_size=25`, `page_size_query_param='page_size'`, `max_page_size=200`. **El tall és backend**, override `?page_size=` fins 200.
- `by_model` pagina amb la mateixa classe (`views_b.py:252`). Client replica el 25 (`Models.jsx:10`).

### Precedent "aplicar a tot el conjunt filtrat"
- **NO EXISTEIX cap operació HTTP que iteri el queryset filtrat-per-request sencer.** Les accions massives van per
  **ids explícits** (`ActionsMenu` `targets` = `selectedModels`; payloads `model_ids: ms.map(m=>m.id)`).
- **Cap endpoint d'export** de la llista de models/board (els `export_*` són de POM/grading, no de llista).
- Únic patró "iterar queryset sencer" = **management commands offline** amb filtres estàtics (no de request):
  `flag_incomplete_models.py:68`, `backfill_model_taxonomy.py:54` — **no reutilitzables com a acció d'usuari**.

**Veredicte A2:** filtres = dos entrypoints mirall; tall de paginació al backend (25, màx 200); cap precedent de "tot el filtrat".

## A3 · Camps al llistat (P3) — què hi ha / què NO

### `ModelListSerializer` (`backend/fhort/models_app/serializers.py:87`, fields `:104-135`)
- **JA viatgen:** id, codi_intern, codi_client, nom_prenda, collection, temporada, any, customer(+customer_nom),
  has_order, created_at, `garment_type`(nom via method `:137-138`), `garment_type_item_nom` (`:117`), fase_actual,
  responsable(nom), prioritat, data_objectiu, predicted_start/end, entrada_prod/arribada_proto/fitting_prev, tecnics, slots_*.
- **NO viatgen:** `size_system` (existeix `models.py:186`) · `grading_rule_set` (ruleset/target/fit/construction;
  el ViewSet fa `select_related` `views.py:63` però el serializer no l'inclou) · `garment_group` · `estat` (kanban de model) ·
  **comptador de watchpoints oberts** (relació `Model.watchpoints` `models.py:936` + `Watchpoint.estat` `:945` existeixen,
  però cap annotació) · **counts/kanban_state de tasques** (el prefetch `model_tasks` només serveix `tecnics`).

### `by_model` shape (`views_b.py:228-250`)
- **JA viatgen:** model_id, model_codi, model_nom, fase, `counts{pending,paused,in_progress,done}`, `kanban_state`,
  prioritat, temporada, estat, data_objectiu, responsable_id, `reanchored_by_start` (`:249`).
- **NO viatgen:** garment_type/garment_type_item, customer/collection (filtrables però no retornats), any/data_entrada/
  data_tancament (llegits al `values()` `:178` però fora del shape), size_system, grading_rule_set, watchpoints.

**Veredicte A3:** de les 5 capes, només arriben `garment_type`(nom) i `garment_type_item_nom`. Grading, size_system i
watchpoints NO viatgen enlloc; counts/kanban només al board.

## A4 · Riscos del bulk gran (P4)

- **Límit de mida:** `plan_assign_batch_view` (`planning/views.py:599-618`) valida només llistes **no buides** — **CAP màxim**.
  `max_page_size=200` limita **només GET**, no cossos POST.
- **Transaccionalitat:** `assign_batch` (`plan_service.py:235`) és **`@transaction.atomic`** amb **UN sol recompute al final**
  (`plan_service.py:364`). PERÒ el **Pas 2** itera `for mid in model_ids: for a in assignacions:` amb queries per-item
  (`.first()`, `.count()`, `lookup_estimated_minutes`) → **O(models×assignacions)** dins d'una transacció → llarga + locks
  si s'hi envien centenars. `gate_bulk_view` (`views_b.py:684`) **NO és atòmic** (èxit parcial). Els `runBulk` per-element = N transaccions independents.
- **Recompute O(n) del pla (post-S15):** `recompute_for_technicians` (`plan_service.py:48`) recalcula la **cua SENCERA**
  del tècnic. Bulk que el disparen: `assign_batch` (1 cop, `plan_service.py:364`), `unassign`/`assign` individuals,
  reorder (`views.py:537`), open-task/auto-start (`views_b.py:585,:593-594`), reassign (`views_b.py:335`). Els bulk
  gate/regress **NO** el disparen (`services_d`). Fittings: `schedule_session` (`services.py:211`), `schedule_bulk` (1 cop, `:295`).
- **Timeouts:** cap timeout explícit als endpoints bulk.
- **TROBALLA TRANSVERSAL:** el cost de recompute creix amb la **mida de la cua per tècnic**, no amb el nombre de models
  seleccionats — assignar molts models a pocs tècnics és el cas car.

**Veredicte A4:** cap límit/timeout als bulk. `assign-batch` és el candidat a peta si s'escala; els `runBulk` per-element
són N POSTs no-atòmics amb fallada parcial.

---

# BLOC B — Planificació: gestió de tasques

## B1 · Eliminar tasques Pending (P5)

### Existeix DELETE?
- **SÍ, per API**: `ModelTaskViewSet(viewsets.ModelViewSet)` (`views_b.py:43`) hereta `destroy()` de DRF. **NO hi ha `def
  destroy` propi per a ModelTask** (els `destroy` de `views_b.py:734/773` són `SupplierViewSet`/`CustomerViewSet`). Ruta
  `DELETE /api/v1/model-task-items/<pk>/` (`tasks/urls.py:15`).
- **Guard permís:** `get_permissions()` (`views_b.py:60-64`) → tot excepte list/retrieve/by_model → `HasCapability` amb
  `DEFINE_TASKS` (`:63`).
- **Guard scope:** `get_queryset()` → `scope_model_task_queryset` (`accounts/capabilities.py:74-95`): view_team → tot;
  define_tasks sense view_team → pròpies + no-assignades; cap → pròpies. Tasca d'altri assignada → 404 (fora scope).
- **UI:** `endpoints.js:214` `modelTasks.remove` existeix però **SENSE cap consumidor** (l'única `.remove` a pàgines és
  `garmentTypeItems`, no tasques). **Cap admin** (`tasks/admin.py` no registra ModelTask). → **DELETE abastable per API, mort a la UI.**

### Qui crea ModelTask (cicle de vida)
define-tasks (`views_b.py:370`, Pending/prevista, idempotent `:357-359`) · extra ad-hoc (`views_b.py:310`) ·
open-task crea-si-falta (`views_b.py:567`) · planificador (`plan_service.py:310`) · clone QA command (`clone_model_for_qa.py:118`).

### FKs ENTRANTS a ModelTask
| Model.camp | fitxer:línia | on_delete |
|---|---|---|
| `TimerEntrada.model_task` | `tasks/models.py:5` | **CASCADE** |
| `TaskTransition.model_task` | `tasks/models.py:124` | **CASCADE** |
| `Watchpoint.task` | `models_app/models.py:938` | SET_NULL |
| `WorkOrderAdjustment.model_task` | `commerce/models.py:553` | SET_NULL |
| `DeliveryNoteLine.model_task` | `commerce/models.py:706` | SET_NULL |

- **TROBALLA TRANSVERSAL:** `TechnicianQueueOrder` (`planning/models.py:80-82`) apunta a **Model + UserProfile, NO a
  ModelTask** (unicitat `(profile, model)`). `MeasurementChangeLog` (`models_app/models.py:616-627`) i `GateEvent`
  (`tasks/models.py:144`) apunten a **Model, no a la tasca**. → L'orfenesa de cua és a nivell de **model**, no de tasca.

### Una Pending pura té fills?
- **NO.** `TimerEntrada` (`services_c.py:23`) i `TaskTransition` (`services_c.py:39`) es creen **només dins
  `transition_task`** en passar a InProgress (`services_c.py:126,129,147`). Transicions permeses des de `Pending: {InProgress}`
  (`services_c.py:11-16`). Una Pending mai iniciada → **0 timers, 0 transitions**. Els SET_NULL (Watchpoint/adjustment/
  delivery) neixen de treball/facturació, no d'una Pending pura.

### Permisos (simetria d'esborrat)
- define-tasks/assign/unassign/extra tots gated `DEFINE_TASKS` (`_DefineTasks` `views_b.py:338-343`, `:400`, `:419-420`).
  → La simetria natural de l'esborrat és **`DEFINE_TASKS`**, que és exactament el que la `destroy()` ja aplica (`:63`).

### Què cal invalidar en esborrar una Pending PLANIFICADA
Patró anàleg = `unassign_model` (`plan_service.py:397-413`), que fa 3 coses que la `destroy()` crua **NO fa**:
1. `recompute_for_technicians([assignee_id])` (`plan_service.py:412`) — sense això la cua queda amb `planned_*` desfasats.
2. `cleanup_queue_order([assignee_id],[model_id])` (`plan_service.py:409`) — esborra `TechnicianQueueOrder(profile,model)`
   només si el profile ja no té cap no-Done d'aquell model (`:92-94`).
3. `Model.predicted_start/end = None` (`plan_service.py:411`) si el model queda sense no-Done planificades.

**Veredicte B1:** esborrar una **Pending pura** és estructuralment segur (0 fills CASCADE, cap FK entrant viu, QueueOrder no
penja de la tasca). Esborrar-ne una **planificada/assignada** amb la `destroy()` crua deixa la cua i `predicted_*` incoherents
→ cal replicar la cascada d'`unassign`. Restringir a `status='Pending'` evita destruir història (timers/transitions CASCADE) de
tasques ja treballades. Gate correcte = `DEFINE_TASKS` (ja aplicat).

## B2 · Formulari "Nou fitting" vs camí del planificador (P6)

### Formulari
`FittingSessionNew.jsx` payload (`:57-65`): fase, data, model, model_persona, assistents(**text lliure, no FK**), lloc, notes
→ `fittingSessions.create` (`endpoints.js:530`, `POST /api/v1/fitting-sessions/`) → `FittingSessionViewSet.create`
(`fitting/views.py:173-193`) → **`create_session`** (`fitting/services.py:127-157`). Un sol `FittingSession.objects.create`
(`:146-157`). **NO toca:** `estat` (→ default `'Oberta'`, `models.py:260`), start_time/end_time (null), duracio_minuts (null),
attendees (mai `.set()` → buit), convocatoria (null), **cap ModelTask**, **cap recompute**, **cap event de calendari explícit**.

### Planificador
`schedule_session` (`services.py:160-214`): guard solapament (`:187-199`), duracio default 10×N (`:179-185`),
`create(estat='Programada', start_time, end_time, duracio_minuts)` (`:200-205`), `attendees.set` (`:207`), **recompute** si
start_time (`:208-213`). `schedule_bulk` (`:217-301`): convocatoria uuid4 (`:239`), `transaction.atomic` (`:246`), encadena
via calendari (`:285-289`), **recompute únic al final** (`:292-295`). Via adaptativa `Production.expected_at` a la view
`schedule` (`views.py:271-298`). **Cap dels dos crea ModelTask.**

### Diferències camp a camp
| Camp/pas | create_session (formulari) | schedule_session / _bulk |
|---|---|---|
| `estat` | **'Oberta'** (default) `services.py:146`+`models.py:260` | **'Programada'** explícit `:204` |
| start_time/duracio | null / null | franja + 10×N `:179-185,:203` |
| attendees | **buit** | `.set(...)` `:207` / unió `:272` |
| ModelTask | cap | cap (paritat) |
| recompute pla | **no** | sí `:208-213` / 1 cop `:292-295` |
| guard solapament | **cap** | dur→409 / suau `:187-199` |
| Production adaptativa | no | sí (view) `:271-298` |
| calendari/gantt | invisible al tècnic sense attendee | event per attendee amb franja `:404-417` |

### Re-verificació ancoratge F2
`planning/views.py:352-354`: sense `VIEW_TEAM_TASKS` → `fitting_qs.filter(attendees=profile)`. Un fitting de `create_session`
(attendees buit) queda **exclòs del calendari per a tot usuari sense VIEW_TEAM_TASKS**. Matís: **amb** VIEW_TEAM_TASKS SÍ
apareix, com a event únic all-day (`views.py:387-393,:418+`). Els tres anclatges F2 (sense attendees/ModelTask/recompute) es mantenen.

### Compartició actual
**Funcions SEPARADES.** Comparteixen model `FittingSession`, taula, `FittingSessionViewSet` i serializer de sortida; NO
comparteixen `check_session_overlap` (`:188,250`), `recompute_for_technicians` (`:211,295`), `add_working_minutes` (`:235`),
`attendees.set`, ni l'assignació estat/franja. La validació XOR model/garment_set està **duplicada** (`:143-144` vs `:174-175`).

**Veredicte B2:** `schedule_session` és un **superconjunt estricte** de `create_session` (fa tot el que fa + estat/franja/
attendees/recompute/guard). Cap camp és exclusiu del formulari que el planificador no pugui escriure. Avui són **dues rutes
independents sense servei backend comú** — tècnicament convergibles.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| # | Element | Estat | Àncora |
|---|---|---|---|
| A | Select-all "tot el filtrat" (Models) | **NO EXISTEIX** (només pàgina 25) | `Models.jsx:54-58` |
| A | Select-all a Planning | **NO EXISTEIX** (fila a fila) | `Planning.jsx:295` |
| A | Payload bulk per conjunt/filtre | **NO EXISTEIX** (només ids explícits) | `ActionsMenu` / `views.py:604-611` |
| A | Límit de mida a `assign-batch` | **FALTA** (cap màxim) | `planning/views.py:599-618` |
| A | Filtres backend (Model) | EXISTEIX (FilterSet 8 camps) | `models_app/views.py:27-41` |
| A | Filtres frontend Models list | **DIFERENT** (només 3 de 8) | `Models.jsx:22-24` |
| A | Filtre per grading/size_system/watchpoints | **NO EXISTEIX** al llistat | `serializers.py:104-135` |
| A | Counts/kanban al ModelListSerializer | **NO EXISTEIX** (sí a by_model) | `serializers.py` / `views_b.py:228-250` |
| A | Export "tot el filtrat" | **NO EXISTEIX** (només commands offline) | `flag_incomplete_models.py:68` |
| B | DELETE de ModelTask (API) | EXISTEIX (destroy default, DEFINE_TASKS) | `views_b.py:43,60-64` |
| B | UI/consumidor del DELETE | **NO EXISTEIX** (`remove` orfe) | `endpoints.js:214` |
| B | Neteja de pla en el DELETE crua | **FALTA** (no replica unassign) | `plan_service.py:397-413` |
| B | Fills CASCADE d'una Pending pura | **NO EXISTEIX** (0 timers/transitions) | `services_c.py:23,39` |
| B | Servei compartit fitting-form ↔ planificador | **NO EXISTEIX** | `services.py:127` vs `:160` |
| B | Fitting del formulari al calendari del tècnic | **DIFERENT** (invisible sense attendee) | `planning/views.py:352-354` |

---

## 💡 PROPOSTES (a validar — NO són fets; decisió humana, Patró C)

> Separades expressament dels fets de dalt. Cap s'ha implementat.

- **💡 Select-all filtrat (#9):** si es vol tocar 961 models d'un cop, el patró segur seria un **endpoint que rebi el
  MATEIX contracte de filtres** (no una llista de 961 ids) i iteri el queryset server-side en **lots** (chunks) amb recompute
  **una sola vegada al final per tècnic afectat** — mai per element. Reaprofitaria `ModelFilter`/`by_model` com a font de conjunt.
  El punt a blindar és `assign-batch` (avui il·limitat i O(models×assignacions) en una transacció; `planning/views.py:599`).
- **💡 Filtres que falten a la llista (#9):** afegir al `ModelListSerializer` (i/o al shape de `by_model`) els eixos absents
  que es vulguin filtrar — grading (`grading_rule_set` i les seves capes), `size_system`, comptador de **watchpoints oberts**,
  counts/kanban — abans de poder-hi filtrar. Decisió de QUINS triar: humana.
- **💡 Eliminar Pending (#5):** exposar un DELETE **restringit a `status='Pending'`** que, quan la tasca estigui
  planificada/assignada, **repliqui la cascada d'`unassign`** (recompute + cleanup_queue_order + neteja `predicted_*`).
  El gate ja correcte és `DEFINE_TASKS`. Cablejar el `modelTasks.remove` orfe a la UI amb aquesta garantia.
- **💡 Convergència "Nou fitting" (deute S15):** com que `schedule_session` és superconjunt de `create_session`, la
  convergència natural és **un únic servei parametritzat** (mode "ràpid/obert" vs "programat") que sempre assigni attendees
  (o expliciti l'absència) perquè el fitting no caigui del calendari del tècnic. Unificaria també la validació XOR duplicada.
