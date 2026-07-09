# DIAGNOSI_P0_PLA_TREBALL — lectura quirúrgica abans de P1 (servir l'encàrrec) i P3 (cablejar transport)

> **Patró A · READ-ONLY ABSOLUT.** Cap fitxer de producte tocat, cap migració, cap escriptura.
> Staging (`fhort`), branca `dev`, NOMÉS `/var/www/ftt-staging`. Equip DIAGNOSI: director +
> investigadors (Explore, read-only) + documentador. Protocol: `.claude/PROTOCOL_FASE_B.md`.
> Disseny congelat: `.claude/PLA_DE_TREBALL.md`. **Aquesta peça (P0) NO decideix res; porta els FETS.**
> Data: 2026-06-21.

---

## 0. Com llegir aquest document

- **FET** = afirmació sobre el codi/dades, amb `fitxer:línia` (rutes relatives a `/var/www/ftt-staging`).
- **💡 PROPOSTA** = recomanació de disseny, a la secció final, mai barrejada amb els fets.
- Verificació del documentador: els anclatges pivot (default_order, seeding de `ModelTask.order`,
  contracte de `transition`, ALLOWED, recompute a reassignació) i **una consulta a dades reals**
  (schema `fhort`) s'han executat a mà. On l'investigador no va poder llegir dades (va consultar
  sense `schema_context` → taules inexistents), el documentador ho ha refet.

---

## Titulars

- **P1 — L'ordre canònic JA EXISTEIX: `TaskType.default_order`.** No cal afegir cap camp nou. És
  un catàleg estable per TIPUS de tasca, idèntic per a tots els models, i el scheduler ja l'usa
  com a font de veritat. `ModelTask.order` és un concepte DIFERENT (ordre d'inserció per-model) i
  **empíricament divergeix** del canònic → NO és l'ordre de producció.
- **P2 — El camí de `transition` és complet i reutilitzable.** Endpoint `POST
  model-task-items/<pk>/transition/` body `{to_status}` → `{task_id, status, paused_task_id}`;
  l'exclusió un-InProgress es dispara SOLA al servei; el trigger eina↔timer viu al frontend
  (fire-and-forget, només si Pending/Paused); la reassignació és `PATCH model-task-items/<pk>/`
  `{assignee}` i dispara `recompute_for_technicians` sol al backend. P3/P4 ho han de **reusar tal qual**.

---

# PREGUNTA 1 — L'ORDRE CANÒNIC de les tasques existeix?

## 1.1 `TaskType` té un ordre canònic propi (FET)

- `TaskType` — `tasks/models.py:185-198`. Camps: `code` (SlugField únic), `name`, **`default_order`
  `PositiveIntegerField(default=0)` (`tasks/models.py:189`)**, `active`.
- `Meta.ordering = ['default_order', 'code']` (`tasks/models.py:193`) → l'ordenació natural del
  catàleg ÉS per `default_order`.
- **Catàleg real (FET, schema `fhort`, read-only)** — `default_order · code`:

  | default_order | code | actiu |
  |---|---|---|
  | 10 | pattern_digit | sí |
  | 20 | pattern_cad | sí |
  | 30 | pattern_hand | sí |
  | 40 | pom | sí |
  | 45 | size_check | sí |
  | 50 | tech_sheet | sí |
  | 55 | pattern_review | sí |
  | 70 | bom | sí |
  | 81 | scaling | sí |
  | 82 | marking | sí |
  | 90 | Audit | sí |

  → És exactament l'ordre de producció esquerra→dreta que el Pla de treball vol (patró→POM→
  size_check→fitxa→…→escalat→marcatge→auditoria). **Canònic, per tipus, idèntic per a tots els models.**

## 1.2 `ModelTask.order` — qui l'omple i amb quin criteri (FET)

- `ModelTask.order` `PositiveIntegerField(default=0)` (`tasks/models.py:210`); `Meta.ordering =
  ['model', 'order']` (`tasks/models.py:226`).
- **Escriptors** (els únics que assignen `order`):
  - `define_model_tasks_view` (`tasks/views_b.py:262`): carrega els tipus **ordenats per
    `default_order`** (`tasks/views_b.py:271`), i assigna `order = base_order + i` on `base_order =
    count(tasques existents del model)` (`tasks/views_b.py:280-288`). És a dir: **ordre d'inserció
    per-model, que APILA al final** de les tasques ja existents.
  - `assign_batch` (`planning/plan_service.py:280-282`): mateix patró (`order = count(...)`).
- **Conseqüència:** en la PRIMERA definició de tasques (base_order=0), `ModelTask.order` queda
  0,1,2… seguint la seqüència `default_order` → coincideix amb el canònic. Però si s'afegeixen
  tipus en una SEGONA tongada, els nous apilen al final segons l'ordre d'arribada, **divergint**
  del canònic.

## 1.3 Evidència empírica de la divergència (FET, schema `fhort`, read-only)

- **Model 162** — `mt.order · default_order · code`:
  - `0 · 40 · pom`
  - `1 · 50 · tech_sheet`
  - `2 · 45 · size_check`
  → `mt.order` posa **tech_sheet (50) ABANS de size_check (45)**: NO segueix el canònic. Prova que
  `ModelTask.order` ≠ ordre de producció.
- **Model 163** — `0·20 pattern_cad, 1·40 pom, 2·50 tech_sheet, 3·81 scaling, 4·90 Audit`: aquí
  `mt.order` SÍ és monòton en `default_order` (coincideix per casualitat de l'ordre d'inserció).
- **Conclusió empírica:** `ModelTask.order` és **inconsistent** com a ordre canònic — a vegades
  coincideix, a vegades no (162 ho refuta). Total: 79 ModelTask a 79 models (mostra petita; molts
  models amb 3 tasques). Cap evidència que `ModelTask.order` s'hagi reordenat manualment després de
  crear-se: cap escriptor el reescriu fora de la creació (no hi ha endpoint de reorder de tasques
  dins el model, a diferència de `TechnicianQueueOrder` que reordena MODELS dins la cua del tècnic).

## 1.4 Què governa l'ordre a les lectures AVUI (FET)

- `model-task-items` (list) i qualsevol query sense `order_by` explícit → `ModelTask.Meta.ordering
  = ['model','order']` (`tasks/models.py:226`) → mana **`ModelTask.order`** (l'ordre d'inserció).
- L'scheduler de planificació → `_task_sort_key` usa **`task.task_type.default_order`**
  (`planning/scheduler_service.py:56-58`) → mana el **canònic**.
- by_model (kanban col·1) → agrega comptadors per model, no ordena tasques dins
  (`tasks/views_b.py:90-213`).
- → Hi conviuen DOS ordres: el canònic (`default_order`, usat al motor) i el d'inserció
  (`ModelTask.order`, usat a les llistes REST per defecte). El Pla de treball vol el **canònic**.

## 1.5 VEREDICTE P1 (FET)

**(A) L'ordre canònic JA EXISTEIX a `TaskType.default_order`.** No cal afegir cap camp nou a
`TaskType`. És estable, per tipus, idèntic per a tots els models, i el scheduler ja l'usa com a
font de veritat (`scheduler_service.py:58`). `ModelTask.order` és un camp DIFERENT (ordre
d'inserció per-model) que **no** representa l'ordre de producció i empíricament hi divergeix
(model 162). Per al Pla de treball, l'ordre esquerra→dreta s'ha de derivar de
`TaskType.default_order`, NO de `ModelTask.order`.

---

# PREGUNTA 2 — Com s'invoca `transition_task` des del FRONTEND avui?

## 2.1 Contracte de l'endpoint `transition` (FET)

- **Ruta:** `POST /api/v1/model-task-items/<pk>/transition/` → `transition_task_view`
  (`tasks/views_b.py:356`).
- **Body EXACTE:** `{"to_status": "<estat>"}` amb `to_status ∈ {Pending, InProgress, Paused, Done}`.
- **Permís:** capability `execute_tasks` (`@permission_classes([_ExecuteTasks])`, `tasks/views_b.py:357`).
- **Validació extra:** si `to_status == 'InProgress'`, el `task.task_type.code` ha de ser a
  l'allow-list de l'usuari (`get_allowed_task_types`), tret d'admin (`tasks/views_b.py:375-379`).
- **Transicions vàlides** (font de veritat al servei) — `ALLOWED` a `tasks/services_c.py:11-16`:
  - `Pending → {InProgress}`
  - `Paused → {InProgress}`
  - `InProgress → {Paused, Done}`
  - `Done → {InProgress}` (reobertura = rectificació)
- **Retorn JSON:** `{"task_id": int, "status": str, "paused_task_id": int|null}`
  (`tasks/services_c.py:127`). `paused_task_id` no-null quan l'exclusió ha pausat una altra tasca.
- **Servei subjacent:** `transition_task(task, to_status, profile)` (`tasks/services_c.py:42`),
  `@transaction.atomic`; obre/tanca `TimerEntrada`, registra `TaskTransition`, i en `Done` alimenta
  Welford (`record_actual_time`, `tasks/services_c.py:121-124`).

## 2.2 L'exclusió un-InProgress-per-tècnic es dispara SOLA (FET)

- A `transition_task`, quan `to_status == 'InProgress'`: busca l'altra `InProgress` del mateix
  `profile`, li tanca el timer, la passa a `Paused`, ho registra i retorna `paused_task_id`
  (`tasks/services_c.py:54-63`). **El frontend NO l'ha de gestionar** — només pot mostrar un toast
  amb `paused_task_id`. Viu al servei → reutilitzable des de qualsevol superfície (kanban, Pla de treball).

## 2.3 Patró de crida del frontend a REUSAR (FET)

- **Client API:** `modelTasks.transition(id, data)` → `client.post('/api/v1/model-task-items/${id}/transition/', data)`
  amb `data = {to_status}` (`frontend/src/api/endpoints.js:129`).
- **Crida real (kanban):** `doTransition(task, toStatus)` →
  `modelTasks.transition(task.id, { to_status: toStatus })`, i si `res.data.paused_task_id` mostra
  toast `kanban.toast_paused` i recarrega el detall (`frontend/src/pages/KanbanTasks.jsx:232`).
- **Mapa d'accions per estat** (botons Play/Pause/Stop/Reopen) — `ACTIONS` a
  `frontend/src/pages/KanbanTasks.jsx:28-34`:

  | Estat | Acció(ns) | `to_status` | icona |
  |---|---|---|---|
  | `Pending` | start | `InProgress` | ti-player-play-filled |
  | `Paused` | resume | `InProgress` | ti-player-play-filled |
  | `InProgress` | pause / finish | `Paused` / `Done` | ti-player-pause-filled / ti-check |
  | `Done` | reopen | `InProgress` | ti-rotate-clockwise |

  Coincideix exactament amb `ALLOWED` del servei → el frontend NO inventa transicions.

## 2.4 Trigger eina↔timer (on viu, perquè P3 el replica) (FET)

- En obrir una eina des del kanban, el frontend dispara la transició a `InProgress`
  **fire-and-forget, només si la tasca és Pending o Paused**, i navega igualment encara que falli:
  - POM (mides): `if (canExecute && (status==='Pending'||status==='Paused')) onTransition(task,'InProgress'); navigate('/models/<id>/mesures')` (`frontend/src/pages/KanbanTasks.jsx:639-658`).
  - Fitxa tècnica: mateix patró → `navigate('/models/<id>/fitxa?task_id=<id>')` (`KanbanTasks.jsx:660-676`).
  - Size check: mateix patró → `navigate('/models/<id>/size-check')` (`KanbanTasks.jsx:678-697`).
- **Tancament:** en desmuntar l'editor de fitxa, dispara `to_status: 'Paused'` (fire-and-forget,
  keepalive) (`frontend/src/pages/TechSheetEditor.jsx:556-561`).
- → El trigger viu a la SUPERFÍCIE (frontend), no al servei. P3 ha de replicar aquest patró des de
  les targetes del Pla de treball (auto-InProgress en obrir l'eina si Pending/Paused; pausa en sortir).

## 2.5 Contracte de reassignació (per a P4) (FET)

- **Ruta:** `PATCH /api/v1/model-task-items/<pk>/` (`frontend/src/api/endpoints.js:126`,
  `modelTasks.patch`). ViewSet `ModelTaskViewSet`.
- **Body:** camps del `ModelTaskSerializer`; el rellevant per al handoff és **`{"assignee": <profile_id|null>}`**.
- **Permís/validació:** capability `define_tasks`; l'assignee ha de tenir el `task_type.code` a
  l'allow-list (`tasks/views_b.py:215-231`).
- **Automatisme (SOL, al backend):** `perform_update` (`tasks/views_b.py:237-253`) — si
  `old_assignee_id != new_assignee_id`: si es desassigna (nou=None i no-Done) buida `planned_*`;
  després crida `cleanup_queue_order([old,new],[model_id])` + **`recompute_for_technicians([old,new])`**.
  → El frontend només fa el PATCH; el recàlcul de cua dels dos tècnics passa sol.
- **Retorn:** la tasca actualitzada serialitzada (`ModelTaskSerializer`).

---

# 💡 PROPOSTA (a validar) — separada dels fets

> Disseny, no decisió ni implementació.

## A. Com hauria P1 de servir l'ordre

- **Servir l'ordre per `TaskType.default_order`** (el canònic confirmat), NO per `ModelTask.order`.
  El Pla de treball pinta esquerra→dreta segons `default_order` del tipus de cada `ModelTask`.
- Implementació mínima sense camp nou: a la lectura del Pla de treball (sigui un bloc nou o un
  `order_by('task_type__default_order')` sobre les `ModelTask` del model), ordenar per
  `task_type__default_order, task_type__code` (mateixa clau que `_task_sort_key` del scheduler →
  coherència amb la planificació). Afegir `task_type_code` i, si convé, `default_order` a la forma
  servida perquè el frontend pugui pintar i agrupar sense recalcular.
- **No cal afegir cap camp a TaskType.** Si en el futur es vol un ORDRE PER-MODEL editable (override
  manual de la seqüència d'un model concret), `ModelTask.order` ja és el substrat natural — però
  AVUI no s'usa així (s'omple a la creació i no es reordena), i el Pla de treball v1 no ho necessita.
  Decisió a prendre quan/si aparegui el cas; no és P1.
- ⚠️ **Aresta a tenir present (no bloca P1):** `default_order` posa `size_check (45)` abans de
  `tech_sheet (50)`, però hi ha models (162) on `ModelTask.order` els té a l'inrevés. Si el Pla de
  treball ordena per `default_order`, la seqüència mostrada pot diferir de l'ordre d'inserció que el
  kanban ensenya avui. És el comportament correcte (canònic), però convé que l'Agus ho validi
  visualment perquè és un canvi d'ordre percebut respecte al kanban.

## B. Com hauria P3 de reusar el camí existent sense duplicar lògica

- **Reusar el client API existent** `modelTasks.transition(id, {to_status})`
  (`endpoints.js:129`) — no crear cap fetch nou.
- **Reusar el mapa `ACTIONS`** (`KanbanTasks.jsx:28-34`) per derivar quins botons mostra cada
  targeta segons l'estat (Play/Pause/Stop/Reopen) → idèntic a `ALLOWED` del servei. 💡 Si es vol
  evitar duplicar el dict `ACTIONS` entre kanban i Pla de treball, es podria extreure a un mòdul
  compartit (p.ex. `frontend/src/.../taskActions.js`) i importar-lo des de tots dos — millora de
  reús, opcional, a decidir a P3 (no és obligatori per funcionar).
- **Replicar el patró fire-and-forget del trigger eina↔timer** (auto-InProgress en obrir l'eina
  només si Pending/Paused; pausa en sortir de l'editor) tal com fa el kanban
  (`KanbanTasks.jsx:639-697`, `TechSheetEditor.jsx:556-561`).
- **No tocar el backend per a P3:** `transition_task`, l'exclusió i el timer ja viuen al servei i es
  disparen sols. P3 és NOMÉS cablejat de frontend.
- **P4 (handoff de reassignació):** reusar `PATCH model-task-items/<pk>/ {assignee}`; el
  `recompute_for_technicians` es dispara sol (`tasks/views_b.py:250-253`). Cap endpoint nou per a
  la reassignació en si (el handoff com a entitat amb estat pendent/resolt és una altra peça, amb
  migració, fora de P0/P1/P3).

---

# Apèndix — fora d'scope detectat (ANOTAT, no tocat)

- **Doble ordre coexistent** (`ModelTask.order` d'inserció vs `TaskType.default_order` canònic):
  no és un bug que P0/P1 hagin de resoldre, però és deute conceptual. Si algun dia `ModelTask.order`
  s'ha de convertir en l'override per-model editable, caldrà decidir qui mana a cada lectura. Avui
  les llistes REST per defecte (`Meta.ordering`) usen `ModelTask.order` i el motor usa `default_order`
  → inconsistència latent entre el que mostra el kanban i el que planifica el motor. Anotat, no tocat.
- **`TaskType.code` 'Audit' amb majúscula** (la resta de codes són minúscula/snake): inconsistència
  cosmètica al catàleg de dades; no afecta P0. Anotat, no tocat.

---

*Document de diagnosi. READ-ONLY respectat: l'únic fitxer escrit és aquest. Cap codi de producte,
migració ni config modificats. Anclatges pivot i la consulta de dades reals (schema `fhort`)
re-verificats pel documentador; la resta marcada com a report d'investigador.*
