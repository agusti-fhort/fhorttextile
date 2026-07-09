> ⚠️ SUPERADA 2026-07-07 — estructura eliminada (model Tasca); substituïda per DIAGNOSI_ARBRE_TASQUES (2026-06-29). Consulta només com a històric.

# DIAGNOSI P0 — Catàleg de tasques: forma ACTUAL (pla) vs forma OBJECTIU (arbre 2 nivells, propietat del sistema)

**Tipus:** diagnosi READ-ONLY. No s'ha escrit res a BD, ni migracions, ni commits, ni restarts.
**Entorn:** venv `/var/www/ftt-staging/backend/venv/bin/python`, schema `fhort`, django-tenants.
**Equip:** Patró A. **Data:** 2026-06-25.

> **Nota d'ubicació:** la consigna demanava lliurar a `/root/fhort-sessions/`. S'ha desat a
> `ftt-staging/docs/diagnosis/` per coherència amb la convenció establerta (tots els
> `DIAGNOSI_*.md` germans hi viuen). Es pot copiar/moure si es vol l'altra ruta.

---

## ⚠️ TROBALLA TRANSVERSAL (llegir abans de les 6 seccions)

**Hi ha DOS catàlegs de tasca al codi, no un:**

1. **`TaskType`** — `fhort/tasks/models.py:185-198`. **PLA i simple** (`code`, `name`,
   `default_order`, `active`). **És el catàleg VIU**: 12 files al tenant fhort, i és el que
   referencien `ModelTask` i `TaskTimeEstimate`. Té UI d'edició i ViewSet.
2. **`Tasca`** — `fhort/tasks/models.py:4-71`. **RIC**: ja porta `fase`, `tipus_tasca`
   (Interna/Externa/Validació), `bloqueja_model`, `gate`, `facturable`, `ordre_base`. **Però
   està BUIT** (0 files al tenant fhort) i **cap de `ModelTask`/`TaskTimeEstimate` l'usa**.

> **Conseqüència per al disseny:** els atributs que es volen al node objectiu (fase, tipus,
> bloqueja_model, és_gate, facturable) **NO existeixen a `TaskType`** (el model viu); **SÍ
> existeixen a `Tasca`** (model mort). **Cap dels dos té jerarquia** (FK `parent` a si mateix).
> El que es vol és, de facto, la unió dels dos + un nivell d'arbre que avui no existeix enlloc.

---

## 1. MODEL `TaskType`

### 1.1 Camps reals — `fhort/tasks/models.py:185-198`

| Camp | Tipus | FET |
|---|---|---|
| `code` | `SlugField(max_length=50, unique=True)` | `models.py:187` — fa de slug/clau natural |
| `name` | `CharField(max_length=200)` | `models.py:188` |
| `default_order` | `PositiveIntegerField(default=0)` | `models.py:189` — ordre canònic **escalar** |
| `active` | `BooleanField(default=True)` | `models.py:190` |
| `Meta.ordering` | `['default_order', 'code']` | `models.py:193` |

- **i18n?** **NO** (FET). `name` és un sol `CharField`; no hi ha `name_ca`/`name_en` ni taula de
  traduccions. El docstring el descriu literalment com *"per-tenant, editable. Pla i simple"*
  (`models.py:186`).

### 1.2 Jerarquia (FK parent a si mateix)?

- **NO. 100% pla** (FET). No hi ha cap `ForeignKey('self')` ni camp `parent` a `TaskType`
  (`models.py:185-198`).

### 1.3 Flags objectiu — quins SÍ / quins NO a `TaskType`

| Flag objectiu | A `TaskType`? | A `Tasca` (model mort)? |
|---|---|---|
| `fase` | ❌ NO | ✅ `models.py:30-41` choices: Disseny/Tècnic/Prototip/Mostres/Preproducció/Producció |
| `tipus` (Interna/Externa/Validació) | ❌ NO | ✅ `tipus_tasca` `models.py:21-29` |
| `bloqueja_model` | ❌ NO | ✅ `models.py:51` |
| `és_gate` | ❌ NO | ✅ `gate` (BooleanField) `models.py:52` (+ `resultat_gate` `models.py:53-57`) |
| `facturable` | ❌ NO | ✅ `models.py:47-50` |
| ordre canònic | ✅ `default_order` (escalar) `models.py:189` | `ordre_base`+`ordre` `models.py:42,17` |

> **SUPÒSIT:** els valors de `Tasca.fase` (Disseny/Tècnic/…) **NO coincideixen** amb les fases
> reals del `Model` (Pending/Dev/Proto/SizeSet/PP/TOP — secció 4). Són dues taxonomies distintes.

### 1.4 `TaskType` vius al tenant fhort (FET — consulta directa schema `fhort`)

**12 files actives.** Cap inactiva. Valors reals (`code` · `name` · `default_order`):

| id | code | name | default_order |
|---|---|---|---|
| 8 | `pattern_digit` | Patró digitalització | 10 |
| 9 | `pattern_cad` | Patró CAD | 20 |
| 10 | `pattern_hand` | Patró a mà | 30 |
| 15 | `pom` | Definició POM | 40 |
| 20 | `size_check` | Mesurar prenda | 45 |
| 21 | `grading` | Escalat | 46 |
| 13 | `tech_sheet` | Fitxa tècnica | 50 |
| 19 | `pattern_review` | Revisió de patró CAD | 55 |
| 14 | `bom` | Definició BOM | 70 |
| 11 | `scaling` | Escalat CAD | 81 |
| 12 | `marking` | Marcada | 82 |
| 18 | `Audit` | Auditoria de model | 90 |

> Nota: `default_order` és dispers (10,20,30,40,45,46,50,55,70,81,82,90) → deixa forats per
> intercalar; útil però **escalar i global**, sense concepte de pare/fill.

---

## 2. UBICACIÓ (TENANT vs SHARED)

### 2.1 `TaskType` és TENANT (FET)

- `fhort.tasks` apareix **només a `TENANT_APPS`** — `fhort/settings.py:70`. **No** és a
  `SHARED_APPS` (`settings.py:36-59`). Per tant `TaskType` viu **dins l'esquema de cada tenant**
  (a `fhort`), no a `public`.
- Context: `pom` SÍ viu a tots dos (`settings.py:55, 68`); `backoffice` només public
  (`settings.py:58`). `tasks` és tenant pur.

### 2.2 TOTES les FK que apunten a `TaskType` (FET — grep exhaustiu, només 2)

| Model origen | Camp | on_delete | Anclatge | Files al tenant fhort |
|---|---|---|---|---|
| `ModelTask` | `task_type` | **PROTECT** | `models.py:206` | **87** |
| `TaskTimeEstimate` | `task_type` | **CASCADE** | `models.py:416` | **458** |

- `ModelTask.task_type` PROTECT → no es pot esborrar un `TaskType` amb instàncies (la UI ho
  tradueix a 409, secció 3).
- `TaskTimeEstimate.task_type` CASCADE → esborrar un `TaskType` **esborraria** les seves cel·les
  d'estimació.
- **Cross-schema?** **NO** (FET). Tots dos (`ModelTask`, `TaskTimeEstimate`) viuen a `fhort.tasks`
  (mateix esquema tenant que `TaskType`). Les FK són intra-schema.

> **⚠️ DISCREPÀNCIA amb la consigna:** la consigna parla de *"513 TaskTimeEstimate"*. El recompte
> **real** al tenant fhort és **458** (FET, consulta directa). Diferència de 55 files. Convé
> reconciliar la xifra abans de planificar res sobre ella.

> `TaskTimeEstimate` també té FK a `GarmentTypeItem` (`models.py:414`, CASCADE), que al seu torn
> apunta a `pom.GarmentType`/`pom.SizeDefinition`/`pom.GradingRuleSet` (`models.py:351,367,380`).
> `pom` viu a SHARED+TENANT, però la matriu d'estimació en si és intra-tenant.

---

## 3. SUPERFÍCIE D'EDICIÓ (el que caldrà jubilar si `TaskType` va a codi/SHARED)

### 3.1 `TaskTypeViewSet` — `fhort/tasks/views_b.py:29-50`

- `class TaskTypeViewSet(viewsets.ModelViewSet)` → **CRUD complet** (list/retrieve/create/
  update/partial_update/destroy).
- **Gating per acció** (`views_b.py` `get_permissions`):
  - `list`/`retrieve` → `IsAuthenticated`.
  - escriptura (create/update/delete) → capability **`DEFINE_TASKS`** (via `HasCapability`).
- `destroy` sobreescrit: retorna **409** si `ProtectedError` (per la PROTECT de `ModelTask`).
- **Serializer** — `fhort/tasks/serializers_b.py:7-10`: exposa exactament
  `['id', 'code', 'name', 'default_order', 'active']`.
- **Ruta** — `fhort/tasks/urls.py:28-35`: `router.register(r'task-types', TaskTypeViewSet)` →
  `/api/v1/task-types/`.

### 3.2 Pàgina/ruta frontend d'edició (FET)

- **Pàgina:** `frontend/src/pages/TaskTypes.jsx`. **Ruta:** `/task-types` (registrada a
  `frontend/src/App.jsx`).
- Crida: `GET /api/v1/task-types/?ordering=default_order`; `POST`/`PATCH`/`DELETE` a
  `/api/v1/task-types/`.
- Gating UI: `canEdit = me?.capabilities?.includes('define_tasks')`; el backend reforça amb
  `DEFINE_TASKS`. `code` queda bloquejat en edició (només `name`/`default_order`/`active`).

### 3.3 Allow-list `get_allowed_task_types` — `fhort/accounts/capabilities.py:57-71`

- Retorna el **set de `TaskType.code`** que un usuari pot EXECUTAR:
  - Admin (rol `admin` o capability `MANAGE_USERS`) → **tots** els `code` de `TaskType` actius
    (`capabilities.py:68`, query `values_list("code", flat=True)`).
  - No-admin → `set(profile.permisos["tasks"])` (default DENY si no hi ha clau).
- **Lligam clau:** la allow-list desa **`code`s de `TaskType`** dins `UserProfile.permisos["tasks"]`
  (JSON). És on l'usuari↔tasca s'acobla al catàleg per **string `code`**, no per PK.
- Punt d'aplicació (exec): `views_b.py:375-379` (transition), i `claim`/`open_model_task`.

### 3.4 Superfície d'edició de `Tasca` (el catàleg ric, mort) — context

- Existeix un `TascaViewSet` (`fhort/tasks/views_sprint1c.py`) a `/api/v1/tasques/`, gated només
  `IsAuthenticated` (sense `DEFINE_TASKS`), serialitzant `fase/tipus_tasca/gate/...`. **SUPÒSIT:**
  és superfície heretada Sprint 1C, avui sense dades (0 files) i sense consumidor de domini.

---

## 4. MOTOR DE GATES (per als flags `és_gate` / `bloqueja_model`)

### 4.1 Fase del `Model` — `fhort/models_app/models.py`

- Camp **`fase_actual`** = `CharField(max_length=20, default='Pending')` — `models_app/models.py:202`.
- **Valors de fase (FASE_CHOICES)** — `models_app/models.py:94-101`:
  `Pending → Dev → Proto → SizeSet → PP → TOP` (6 valors).
- Dimensió **separada** `estat` (Nou/EnCurs/EnRevisió/Tancat) — `models_app/models.py:87-92, 201`.

### 4.2 Lògica advance/regress — `fhort/tasks/services_d.py`

- `advance_phase_gate()` — `services_d.py:24-56`: escriu `model.fase_actual=to_phase`, posa
  `estat=Tancat` si arriba a TOP, **crea `GateEvent(kind='advance')`**, i crida
  `seal_model_grading()` (segellat de versió de grading, D-3).
- `regress_phase()` — `services_d.py:58-73`: només mou `fase_actual` enrere + `GateEvent(kind='regress')`.
- `advance_phases_chain()` — `services_d.py:76-83`: encadena diversos gates.
- **Endpoints** — `fhort/tasks/views_b.py`: `gate_model_view` (`/models/<id>/gate/`),
  `regress_model_view` (`/models/<id>/regress/`), `gate_bulk_view` (`/gates/bulk/`), tots gated
  per capability **`CLOSE_GATES`** (`views_b.py:500`).
- **`GateEvent`** és log append-only — `models.py:256-276`. **9 files** al tenant fhort (FET).

### 4.3 Relació fase ↔ TaskType/Tasca (FET)

- **Avui són PARAL·LELES, no acoblades.** Completar tasques **no** avança `fase_actual`. El comentari
  de `fhort/tasks/signals.py` (capçalera) ho diu: *"Cap SIGNAL deriva fase_actual"*.
- **Única excepció automàtica** (FET): arrencar la PRIMERA tasca (qualsevol `ModelTask`→`InProgress`)
  mou el model de `Pending`→`Dev` — `fhort/tasks/services_c.py:85-91`
  (`Model.objects.filter(pk=..., fase_actual='Pending').update(fase_actual='Dev')`). No depèn de
  QUIN `TaskType` és, ni de `gate`/`bloqueja_model`.
- La resta d'avenços de fase són **manuals** (acció humana amb `CLOSE_GATES`).
- **Cap flag `gate`/`bloqueja_model` de `TaskType` no governa res avui** perquè `TaskType` no té
  aquests camps; i els de `Tasca` no s'apliquen (model mort). El "gate" viu només a nivell de
  `Model.fase_actual` + `GateEvent`, **desacoblat del catàleg de tasques**.
- Lligam fase↔producció (col·lateral): `phase_passed_gate()` exigeix `GateEvent` per enviar fases
  FUTURES a confecció — `fhort/tasks/services_e.py:11-24`.

---

## 5. CABLEJAT `transition_task` (transport del Pla de treball)

### 5.1 Endpoint i payload (FET)

- **Ruta:** `POST /api/v1/model-task-items/<pk>/transition/` — `fhort/tasks/urls.py:73`.
- **View:** `transition_task_view(request, pk)` — `fhort/tasks/views_b.py:356-384`.
- **Payload:** `{"to_status": "InProgress"|"Paused"|"Done"|...}` — `views_b.py:359`.
- **Resposta:** `{'task_id', 'status', 'paused_task_id'}`.

### 5.2 Estats i transicions acceptades — `fhort/tasks/services_c.py:11-16`

```
ALLOWED = {
  'Pending':    {'InProgress'},
  'Paused':     {'InProgress'},
  'InProgress': {'Paused', 'Done'},
  'Done':       {'InProgress'},   # reobertura = rectificació
}
```
- Validació: `services_c.py:47-49` → `TransitionError` si la transició no hi és.
- Estats possibles de `ModelTask`: `Pending/Paused/InProgress/Done` — `models.py:203-204`.

### 5.3 Exclusió un-InProgress-per-tècnic (FET)

- `fhort/tasks/services_c.py:54-63`: en entrar a `InProgress`, busca una altra `ModelTask` del
  mateix `assignee` amb `status='InProgress'`, li tanca el timer, la passa a `Paused` i la
  retorna com `paused_task_id`. Regla **global** (a través de tots els models).

### 5.4 Gating i allow-list

- Capability **`EXECUTE_TASKS`** (`_ExecuteTasks`, `views_b.py:352-357`).
- A més, per a `InProgress`: `task.task_type.code not in get_allowed_task_types(user)` → 403
  (`views_b.py:375-379`).

### 5.5 Frontend (Kanban) (FET)

- API: `frontend/src/api/endpoints.js:167` →
  `modelTasks.transition(id, data) => client.post('/api/v1/model-task-items/${id}/transition/', data)`.
- Component: `frontend/src/pages/KanbanTasks.jsx` — `doTransition(task, toStatus)` (≈L232-251);
  mapa d'accions per estat a `KanbanTasks.jsx:29-35`.
- Auto-iniciar (fire-and-forget): obrir una eina (pom/tech_sheet/size_check/scaling) dispara
  `transition→InProgress` sense `await` (`KanbanTasks.jsx:647-708`).

---

## 6. RADI DE MIGRACIÓ (pla→arbre i tenant→codi/SHARED)

> Anàlisi de RADI/RISC. Cap recomanació d'implementació (per consigna).

### 6.1 Què s'arrossegaria en moure `TaskType` a SHARED/codi

| Punt | Anclatge | Què s'arrossega |
|---|---|---|
| `ModelTask.task_type` (PROTECT, 87 files) | `models.py:206` | Si `TaskType` passa a `public`, la FK des de taula tenant cap a taula shared és **cross-schema**. Caldria remapeig de PK tenant→PK canònica per a les 87 files. |
| `TaskTimeEstimate.task_type` (CASCADE, **458** files) | `models.py:416` | Mateix remapeig de PK; a més, CASCADE actiu (esborrar canònic ⇒ esborra cel·les). La matriu (item×task_type) s'ha de re-vincular per `code`. |
| Allow-list per `code` | `capabilities.py:57-71` | Desa `code`s a `UserProfile.permisos["tasks"]`. Si els `code`s canònics difereixen dels tenant, cal re-mapejar JSON de cada usuari. Avantatge: lliga per **`code`** (estable), no per PK. |
| Capability `DEFINE_TASKS` + UI | `views_b.py:29-50`, `TaskTypes.jsx`, ruta `/task-types` | Quedaria **a jubilar** (edició per tenant deixa de tenir sentit si el catàleg és del sistema). |
| Scheduler | `scheduler_service.py:58` | Ordena per `task_type.default_order` (escalar). |
| `lookup_estimated_minutes` | `services_g.py:4-17` | Punt (item, task_type)→cel·la; assumeix `task_type` és **fulla** amb cel·la única. |

### 6.2 Punts que un canvi pla→ARBRE trencaria (assumeixen `TaskType` pla / ordre escalar)

| Punt | Anclatge | Per què trenca amb arbre |
|---|---|---|
| Creació massiva de `ModelTask` | `views_b.py:271` (`.order_by('default_order')`) + `:287-289` | Ordena per escalar global; amb pare→fill, parells pare/fill s'intercalarien per `default_order` sense respectar el niu. |
| Ordre dins d'un model (scheduler) | `scheduler_service.py:58` (`(task_type.default_order, task.id)`) | Clau d'ordenació escalar; un arbre necessita clau composta (path pare/fill). |
| `Meta.ordering` del model | `models.py:193` (`['default_order','code']`) | Ordenació plana per defecte; un arbre voldria `parent` a la clau. |
| Vista detall de model | `models_app/views.py:1862` (`order_by('task_type__default_order','task_type__code')`) i `:1877` (exposa `default_order`) | Retorna llista plana; el front no rep estructura pare/fill. |
| Matriu d'estimació | `services_g.py:12-14`, `services_i.py:31-32`, `unique_together` `models.py:423` | Cel·la única per (item, task_type fulla). Un node **pare** no tindria cel·la → `lookup` torna None silenciós. |
| Allow-list | `capabilities.py:68` | Aplana tots els `code` (pares i fills barrejats) sense distingir nivell. |
| Serializer | `serializers_b.py:10` | Exposa `default_order` escalar, sense `parent`/nivell. |

### 6.3 Síntesi del radi (FET + SUPÒSIT)

- **FET:** només **2 FK** toquen `TaskType` (radi de remapeig acotat: 87 + 458 files), totes
  intra-tenant avui; la dependència crítica externa és la **allow-list per `code`** dins `permisos`
  de cada usuari.
- **FET:** l'ordre canònic existeix però és **escalar** (`default_order`); ≥6 punts el llegeixen
  assumint planitud (taula 6.2).
- **SUPÒSIT:** els atributs objectiu del node (fase/tipus/bloqueja/gate/facturable) ja tenen
  *esquema* a `Tasca` però **zero dades** i zero consum; el motor de gates viu desacoblat
  (`Model.fase_actual` + `GateEvent`), de manera que afegir `és_gate`/`bloqueja_model` al catàleg
  **no té avui cap consumidor** que els llegeixi — caldria cablejar-los de nou.

---

## 7. Diagnosi del model `Tasca` (cohort ELIMINADA 2026-06-25)

> **⚠️ COHORT ELIMINADA 2026-06-25** (dev, commit `5ce3a0a`). Aquesta secció és **històrica**:
> descriu la cohort tal com era ABANS de l'esborrat. La diagnosi va llistar **3** models
> (`Tasca` + `PaquetServei` + `PaquetServeiTasca`); la investigació prèvia a l'esborrat en va
> trobar **un 4t** no documentat: **`models_app.ModelServei`** (FK PROTECT → `tasks.PaquetServei`,
> de la mateixa migració `0005`). S'han esborrat **els 4** + el codi arrossegat (2 ViewSets, 2
> serializers, `views_sprint1c.py`/`serializers_sprint1c.py`, registres admin/router,
> `ModelServeiViewSet`). **0 files perdudes** (cap dels 4 tenia dades). **Gotcha de migració
> resolt:** `tasks.0026` calia reordenar a mà — `AlterUniqueTogether(None)` PRIMER, abans dels
> `RemoveField` (l'autodetector ho ordenava al revés i petava `FieldDoesNotExist` sobre `fhort`);
> i `models_app.0043` (DeleteModel `ModelServei`) corre ABANS de `tasks.0026` per alliberar la
> PROTECT. **NO tocats (vius):** `TipologiaModel` (57), `TimerEntrada` (86), `TaskType` (14).

> **VEREDICTE ORIGINAL (confirmat per l'esborrat): `Tasca` = [CODI MORT FUNCIONAL].** Tenia zero
> dades, zero consumidors de domini, zero consum de frontend. **No era esborrable d'un toc:**
> arrossegava 2 ViewSets, 2 serializers, registres d'admin, registres de router i els models
> germans `PaquetServei` + `PaquetServeiTasca` (FK CASCADE cap a `Tasca`) — i el 4t membre
> `ModelServei` (FK PROTECT) que la diagnosi no havia detectat. Sense pèrdua de dades (0 files).
> Era un fòssil de l'arrencada amb Frappe, abandonat quan el disseny va girar cap a
> `TaskType`/`ModelTask` (Sprint B).

### 7.1 Origen i llinatge (FET)

| Migració | Data/Sprint | Acció | Anclatge |
|---|---|---|---|
| `0001_initial` | inicial | Crea `TascaCataleg` + `ModelTasca` + `TimerEntrada` (era Frappe; `tasca_global → pom.tascaglobal`) | `migrations/0001_initial.py:18,34,59` |
| `0004_sprint1b_rename_tasca` | 2026-05-25, Sprint 1B | **CreateModel `Tasca`** (malgrat el nom "rename"): fusiona `TascaCataleg` + metadata de procés (`fase`/`tipus_tasca`/`gate`/`bloqueja_model`/`facturable`) | `migrations/0004_sprint1b_rename_tasca.py:15-40` |
| `0005_sprint1b_new_models` | Sprint 1B | Crea `PaquetServei` + `PaquetServeiTasca` (germans de `Tasca`) | `migrations/0005_sprint1b_new_models.py:14,33` |
| `0008_tasktype_modeltask` | Sprint B | Crea el **NOU** `TaskType` + `ModelTask` (catàleg paral·lel que el reemplaça) | `migrations/0008_tasktype_modeltask.py:16,31` |
| `0009_remove_timerentrada_model_tasca_and_more` | Sprint B | **DeleteModel `ModelTasca`** + repunta `TimerEntrada` (`model_tasca`→`model_task`) | `migrations/0009_...py:51-52, 15-32` |

- **El gir de disseny (FET):** Sprint B (0008) introdueix `TaskType`+`ModelTask` i 0009 **mata
  `ModelTasca`** (el model d'instàncies vell), però **deixa viu `Tasca`** (el catàleg vell) i els
  seus germans `PaquetServei`/`PaquetServeiTasca` com a orfes. El docstring del model ho admet:
  *"Task catalog (tenant). Merges legacy TascaCataleg + process metadata"* (`models.py:5`).

### 7.2 Rastre de Frappe (FET)

- **Exports Frappe literals** a `data/import_ops/`: `Tasca.json`, `Paquet_de_servei.json`,
  `Tipologia_de_model.json` — amb metadata de DocType ERPNext (`name` = docname hash p.ex.
  `"g22rvsh28p"`, `docstatus`, `idx`, `owner: "Administrator"`, `_user_tags`, `_comments`,
  `_liked_by`, `_assign`). `Tasca.json` conté tasques reals ("Recepció d'inputs del client",
  fase Disseny, etc.).
- `data/import_master.py:1`: *"Script d'importació del master data Frappe → models Django."*
- FK `tasca_global → pom.TascaGlobal` (`models.py:7-13`); `TascaGlobal` = catàleg global Frappe
  (`pom/models.py:102`, verbose 'Tasca global'), **0 files** a fhort i a public.
- **El loader no s'executa aquí (FET):** `data/import_models.py:3` apunta a
  `BASE = '/var/www/fhort-textile/backend/data/import_ops'` — un **path de desplegament diferent**
  (`fhort-textile`, no `ftt-staging`). Per això els JSON existeixen però `Tasca` té 0 files.

### 7.3 Referències entrants (FET)

| Origen | Tipus | Anclatge | Viu? |
|---|---|---|---|
| `PaquetServeiTasca.tasca` | **FK (CASCADE)** | `models.py:169` | Germà orfe (0 files) |
| `views.py:TascaViewSet` | ViewSet (legacy) | `views.py:18-26` | Registrat com a fallback |
| `views_sprint1c.py:TascaViewSet` | ViewSet (ric) | `views_sprint1c.py:12-22` | **Registrat actiu** a `/api/v1/tasques/` |
| `serializers.py` / `serializers_sprint1c.py` | Serializers | `serializers.py:12`, `serializers_sprint1c.py:8` | — |
| `admin.py` | Admin registrat | `admin.py:10-15` (i `PaquetServei*` :17-30) | Sí (Django admin) |
| Router | `/api/v1/tasques/`, `/api/v1/paquets-servei/` | `urls.py:14-21` | Endpoints vius |

- **Domini (scheduler/gates/creació de `ModelTask`/fitting/planning): ZERO consumidors** de `Tasca`
  (FET — grep exhaustiu; cap import de `Tasca` fora del trio sprint1c/legacy/admin).
- **Frontend: ZERO consum de l'entitat** (FET). `/tasques` i `/tasques/kanban` són **rutes de nav
  React** cap al Kanban (`Sidebar.jsx:50`, `Topbar.jsx:14-16`), que usa `model-task-items`
  (TaskType/ModelTask) — **no** `Tasca`. El "Catàleg" del menú apunta a `/task-types`
  (`Sidebar.jsx:61`). **Cap crida** a `/api/v1/tasques/` ni `/api/v1/paquets-servei/` a tot
  `frontend/src`.

> **Matís de veredicte:** `Tasca` no és *codi mort pur* en sentit estricte — és **abastable** via
> una ruta REST registrada + admin. Però és **mort de dades + mort de domini + mort de frontend**:
> els endpoints `/api/v1/tasques/` i `/api/v1/paquets-servei/` són closques CRUD vives però mai
> cridades.

### 7.4 Estat real (FET — consulta directa)

| Model | files a `fhort` | files a `public` | Admin | Seed que el pobli |
|---|---|---|---|---|
| `Tasca` | **0** | n/a (tenant app) | Sí | No (loader apunta a un altre path) |
| `PaquetServei` | **0** | n/a | Sí | No |
| `PaquetServeiTasca` | **0** | n/a | Sí | No |
| `TascaGlobal` (pom) | 0 | 0 | — | No |

### 7.5 Germans òrfens vs vius (FET)

- **Cohort ÒRFENA (0 files + cap consumidor de domini/frontend) → candidats a neteja conjunta:**
  `Tasca`, `PaquetServei`, `PaquetServeiTasca`. (+ `TascaGlobal` a `pom`, 0 files, fòssil global
  Frappe — fora de l'app `tasks`.)
- **Germans de la mateixa època que SÍ es consumeixen (NO tocar):**
  - `TipologiaModel` — **57 files** a fhort; viu (slots de càrrega per ruta de producció).
  - `TimerEntrada` — **86 files** a fhort; viu (timers de `ModelTask`, repuntat a 0009).

### 7.6 Si s'esborra `Tasca`: què cau amb ell (FET — abast de la neteja)

- Models: `Tasca`, `PaquetServei`, `PaquetServeiTasca` (l'últim té FK CASCADE a `Tasca`,
  `models.py:169`).
- Codi: `views.py:TascaViewSet`, `views_sprint1c.py` (`TascaViewSet`+`PaquetServeiViewSet`),
  `serializers.py:TascaSerializer`, `serializers_sprint1c.py`, registres a `admin.py:9-30`,
  registres de router a `urls.py:3-7, 14-21` (compte: `urls.py:3` importa `TascaViewSet` de
  `views.py` per al fallback del router → s'ha de desfer alhora).
- Endpoints que desapareixen: `/api/v1/tasques/`, `/api/v1/paquets-servei/` (sense consumidor).
- Dades: **cap pèrdua** (0 files a tots tres). Migració de `DeleteModel` neta.
- **SUPÒSIT:** els camps rics de `Tasca` (`fase`/`tipus_tasca`/`bloqueja_model`/`gate`/
  `facturable`) són l'esquema que es vol reaprofitar per enriquir `TaskType`; per tant la decisió
  "esborrar `Tasca`" i "enriquir `TaskType`" són la mateixa moneda (es copia el *disseny* dels
  camps, no les dades, que no existeixen).

---

## 8. Estat real del motor de temps (seed → Welford)

> **Resum de veredictes:** el motor d'aprenentatge **JA EXISTEIX i ESTÀ CABLEJAT** a la realitat
> (tancar tasca → alimenta Welford), amb separació neta seed/empíric. El **consum** existeix però
> és per **snapshot** (es congela en crear la `ModelTask`, no es rellegeix en viu). El **seed** és
> una matriu autorada a mà però **grollera** (3 perfils L/M/P × 9 tasques); **no hi ha herència per
> fase ni global-per-tasca**.

### 8.1 `services_i.py` sencer — [JA EXISTEIX]

| Funció | Signatura | Què fa | Anclatge |
|---|---|---|---|
| `_real_minutes` | `(model_task)` | Temps real = `SUM(timers.minuts)` (inclou rectificacions) | `services_i.py:13-15` |
| `record_actual_time` | `(model_task)` `@transaction.atomic` | Update Welford online de la cel·la (item×task_type): `n+1`, `delta`, `new_mean`, `m2`. Salta si no hi ha `garment_type_item` o `x<=0`. Defensiu: `try/except` → mai trenca el tancament | `services_i.py:18-46` |
| `effective_minutes` | `(cell)` | Retorna `round(mean_minutes)` si `n>=5 && mean>0`; si no, `estimated_minutes` (seed) | `services_i.py:49-53` |

- **Constant llindar (FET):** `WELFORD_MIN_SAMPLES = 5` — `services_i.py:10`.
- **Qui crida (FET, grep):**
  - `record_actual_time` ← **només** `services_c.py:124-125` (en `Done`).
  - `effective_minutes` ← `services_g.py:8,17` (dins `lookup_estimated_minutes`).
  - `lookup_estimated_minutes` ← `views_b.py:286,477` (creació de `ModelTask`) i `plan_service.py:281` (assignació en lot).

### 8.2 Model de la cel·la `TaskTimeEstimate` — [JA EXISTEIX, seed i empíric SEPARATS]

- Camps (FET, `models.py:410-428`): `garment_type_item` (FK CASCADE), `task_type` (FK CASCADE),
  **`estimated_minutes`** (= **SEED**, nullable), **`n`**, **`mean_minutes`**, **`m2`** (= Welford).
  `unique_together = ('garment_type_item','task_type')`.
- **Seed vs observat = columnes SEPARADES** (FET): el seed viu permanent a `estimated_minutes` i
  **mai** és sobreescrit per l'aprenentatge; l'empíric s'acumula a `n`/`mean_minutes`/`m2`.
- **Com distingeix "tinc seed" de "tinc 5 mostres" (FET):** pel comptador **`n`**. `effective_minutes`
  fa `cell.n >= 5` → empíric; si no → seed. No hi ha flag; el discriminador és `n`.

### 8.3 Alimentació (flux amunt) — [JA EXISTEIX I CABLEJAT]

- **FET:** `transition_task`, en arribar a `Done`, crida `record_actual_time(task)` —
  `services_c.py:121-125`. I `transition_task` és el servei del endpoint real del Kanban
  (`POST /api/v1/model-task-items/<pk>/transition/`, `views_b.py:356-384`, gated `EXECUTE_TASKS`).
  → El motor **NO és codi orfe**: cada tasca tancada per un tècnic alimenta la cel·la.
- **FET (porta única):** comentari a `models_app/views.py:601` declara que tancar és
  *"l'única porta: status=Done, finished_at, tanca timer, record_actual_time, log"* → no hi ha
  camí alternatiu a `Done` que salti l'alimentació.
- **Condicions de no-aprenentatge (FET, no bugs, disseny):** salta si el model no té
  `garment_type_item` (`services_i.py:25-27`) o si la suma de timers és `0` (`:29-30`). Per tant
  aprèn **només** models amb variant assignada i amb temps real registrat (timers server-side).

### 8.4 Consum (flux avall) — [JA EXISTEIX, però per SNAPSHOT, no en viu]

- **FET:** el scheduler **no llegeix la cel·la en viu**: usa el snapshot `ModelTask.estimated_minutes`
  — `scheduler_service.py:8` (*"Durada = snapshot `ModelTask.estimated_minutes` (NO la cel·la
  TaskTimeEstimate en viu)"*), `:215,218`.
- **FET:** el snapshot s'escriu **en crear la `ModelTask`** via `lookup_estimated_minutes` →
  `effective_minutes` (`views_b.py:286,289`, `:477,479`; `plan_service.py:281,283`). Per tant el
  guard Welford `>=5` **SÍ s'aplica**, però **al moment de crear la tasca**.
- **Conseqüència (FET):** Welford es consumeix **diferit**: una cel·la que arriba a 5 mostres només
  afecta les **tasques NOVES** creades a partir d'aleshores; les `ModelTask` ja existents conserven
  el snapshot vell. **Cap re-lectura en viu** del `mean_minutes` per a tasques ja creades.
- **FET:** ningú llegeix un "camp estàtic vell ignorant Welford" — tots els lectors passen per
  `effective_minutes`. El que és estàtic és el **snapshot per tasca**, no un camp paral·lel.

### 8.5 Seed actual — [JA EXISTEIX (autorada a mà, grollera)] · herència per fase/global — [NO EXISTEIX]

- **FET:** les cel·les seed es sembren amb el command `restructure_garment_types_v2.py` (app `pom`):
  `TaskTimeEstimate.update_or_create(..., defaults=dict(estimated_minutes=mins[idx]))` — `:245-248`.
- **Estructura del seed (FET):** NO és una matriu individual per (item×tasca). És **3 perfils de
  complexitat** `PROFILES = {'L','M','P'}` (≈275/365/950 min totals) × **9 tasques** `TASK_ORDER`
  (`:22-32`). Cada un dels 57 ITEMS tria **un** perfil (`profile` a `ITEMS`, `:233,240`) i el seu
  vector es **difon** a totes les seves cel·les. → només **27 valors seed distints** (3×9),
  replicats per item.
- **Cobertura parcial (FET):** `TASK_ORDER` té **9** dels **12** `TaskType`. **Sense seed**:
  `size_check`, `pattern_review`, `Audit` (no surten a `TASK_ORDER`, `:22-23`).
- **Reconciliació del "513 vs 458" (FET + SUPÒSIT):** el command sembraria **57 items × 9 tasques =
  513** cel·les (això explica la xifra "513" de consignes anteriors); el recompte **real** és **458**
  (§2). **SUPÒSIT:** el command no s'ha aplicat sencer / alguns items quedaren inactius / upserts
  parcials → 55 cel·les de diferència. Cal verificar-ho si la xifra importa.
- **Herència (FET):** **NO existeix** cap fallback "global per tasca" ni "per fase". Si no hi ha
  cel·la (item×task_type) → `lookup_estimated_minutes` torna `None` (`services_g.py:15-16`) i el
  scheduler avisa i no planifica (`scheduler_service.py:15,215`). El seed és pla, sense jerarquia.

### 8.6 Quadre de veredictes

| Bloc | Veredicte | Nota |
|---|---|---|
| `services_i.py` (Welford + effective) | **[JA EXISTEIX]** | complet i defensiu |
| Cel·la seed/empíric separats | **[JA EXISTEIX]** | discriminador = `n>=5` |
| Alimentació (Done → update) | **[JA EXISTEIX, CABLEJAT]** | via `transition_task`, porta única |
| Consum pel scheduler | **[JA EXISTEIX — per snapshot]** | Welford diferit a creació de tasca; no en viu |
| Seed autorada | **[JA EXISTEIX — grollera]** | 3 perfils × 9 tasques; 3 TaskType sense seed |
| Herència fase / global-per-tasca | **[NO EXISTEIX]** | sense fallback; None si manca cel·la |

---

## 9. Punts d'endoll de la cascada de resolució de temps (§2.4/§2.5)

> **Objectiu de cascada:** `empíric(item,task)` → `empíric_global(task)` → `llavor(task|fase)` →
> `demanar al PM`. **Estat real:** avui només existeixen el graó 1 (empíric per cel·la) i una
> variant del graó 3 (llavor per **item**, no per task/fase); els graons 2 i 4 **no existeixen** i
> el "global" s'ha de construir de zero (hi ha substrat de dades, no codi). El choke-point natural
> per endollar tota la cascada és **una sola funció**: `lookup_estimated_minutes` (services_g),
> que és l'únic lloc que té alhora `item` (via model) i `task_type`.

### 9.1 Punt d'entrada del `None` — [FET]

- `lookup_estimated_minutes(model, task_type)` — `services_g.py:4-17`:
  - `item_id = model.garment_type_item_id`; si **no item** → `return None` (`:9-11`).
  - `cell = TaskTimeEstimate.filter(item, task_type).first()`; si **no cel·la** → `return None` (`:15-16`).
  - altrament → `return effective_minutes(cell)` (`:17`).
- `effective_minutes(cell)` — `services_i.py:49-53` (on es decideix **seed-vs-empíric**):
  - `if cell.n >= WELFORD_MIN_SAMPLES(=5) and cell.mean_minutes > 0:` → `round(mean_minutes)` (`:51-52`) ← **graó 1 (empíric item,task)**.
  - `else:` → `cell.estimated_minutes` (seed, **pot ser None**) (`:53`) ← llavor per **item** (graó 3 fi).
- **Camí creació-de-ModelTask → snapshot** (3 punts, tots escriuen `estimated_minutes=est`):
  - `views_b.py:286` (`define_model_tasks_view`) i `:477` (`open_model_task_view`).
  - `plan_service.py:281` (`assign_batch`, dins el bucle de creació).
  - El snapshot es **congela** a la fila `ModelTask` en crear-la; després ningú el refresca (§9.5).

### 9.2 Què passa avui amb el `None` aigües avall — [FET]

| Lloc | Línia | Comportament amb `estimated_minutes is None` |
|---|---|---|
| Scheduler | `scheduler_service.py:215-217` | `_warn(t,'sense estimació de temps (no planificable)')` + **`continue`** → la tasca **NO es col·loca** (sense planned_*), i el model no l'agrega a `predicted_*`. |
| Pin/preview/apply | `plan_service.py:105-106` (`_pin_block`) | `raise ValueError('La tasca moguda no té estimació; no es pot reposicionar.')` |
| Wizard | `plan_service.py:297-300` (`assign_batch`) | `if (ps_raw or pe_raw) and not est_min:` → warning "sense estimació; assignat sense dates (va a cua)", `planned_locked=False`. |

- **Símptoma real:** la tasca s'assigna però **mai apareix planificada** (cap franja); el tècnic la
  veu a la cua sense dates i el `predicted_end` del model l'ignora. **SUPÒSIT:** `estimated_minutes=0`
  (no `None`) **sí** passa el guard i es planifica amb durada zero (`scheduler:215` només filtra
  `is None`); `assign_batch` però tracta `not est_min` (0 inclòs) com a sense-estimació.

### 9.3 El seed actual — [FET]

- Es desa amb el command `restructure_garment_types_v2.py`:
  `TaskTimeEstimate.update_or_create(item, task_type, defaults=estimated_minutes=mins[idx])` (`:245-248`).
- **Estructura:** `PROFILES = {'L','M','P'}` (≈275/365/950 min) × `TASK_ORDER` (9 tasques) (`:22-32`).
- **Assignació perfil→item:** el perfil L/M/P és el **5è element** de cada fila d'`ITEMS`
  (`(family, code, name, complexity_order, perfil)`, `:87-128`), usat **només en sembrar**
  (`mins = PROFILES[perfil]`, `:240`). **NO es persisteix a `GarmentTypeItem`**: l'item desa
  `complexity_order` (int, `models.py:257`) — un ordre dins la família, **independent** del perfil.
  → El mapa item→perfil **viu només dins el command** (efímer); a BD no hi ha cap camp de perfil.
- **Cobertura:** `TASK_ORDER` cobreix 9 dels (ara) 14 TaskType. **Sense seed:** `size_check`,
  `pattern_review`, `Audit` (no a `TASK_ORDER`, `:22-23`) i els 2 nous `design_review`/`design_clarify`
  (el command és anterior). Teòric 57×9=**513** (`:290`), real **458** (§2/§8).

### 9.4 Nivell GLOBAL (per task_type / per fase) — [NO EXISTEIX, però hi ha substrat]

- **FET:** cap agregat per `task_type` ni per `fase`. Totes les lectures de `TaskTimeEstimate` són:
  lookup puntual (`services_g`), update Welford (`services_i.py:31`), CRUD
  (`TaskTimeEstimateViewSet`, `views_b.py:718`) i el seed. **Cap `aggregate`/`Avg`/`annotate`** sobre
  `task_type` enlloc (grep exhaustiu).
- **Substrat present (SUPÒSIT d'implementació):** les 458 cel·les ja tenen `estimated_minutes` (seed)
  + `n`/`mean_minutes` (empíric). Un `empíric_global(task)` es podria calcular com
  `Avg(mean_minutes)` filtrant `task_type=… , n>=5` — però aquest càlcul **no existeix** i s'ha
  d'escriure de zero. El `task_type` no té cap camp de minuts propi (§1), de manera que un
  `llavor(task|fase)` també necessitaria una **font nova** (camp a TaskType, taula per fase, o constant).

### 9.5 Re-resolució en replanificar (decisió A) — [reusa snapshot; NO re-llegeix]

- **FET:** `recompute_for_technicians` (`plan_service.py:48-59`) crida
  `schedule(_technician_queue(prof), save=True)` (`:58`). `_technician_queue` (`:42-45`) retorna
  les `ModelTask` tal qual; `schedule` usa **`t.estimated_minutes`** (snapshot) a `scheduler:218`.
  → El recàlcul **reusa el snapshot vell**; **mai** torna a cridar `lookup_estimated_minutes`.
- **FET:** `assign_model` (`:177-212`) i `assign_batch` (`:215-356`) tampoc refresquen el snapshot de
  tasques **ja existents** (`assign_batch` només calcula `est` en **crear** una tasca nova, `:281`;
  per a una existent reusa `mt.estimated_minutes`, `:296`).
- **On forçar la re-lectura fresca (insertion point):** dins `recompute_for_technicians`, abans del
  `schedule` (`plan_service.py:56-58`), recalcular `t.estimated_minutes = lookup_estimated_minutes(
  t.model, t.task_type)` per a cada tasca movible no-locked de la cua (i desar-lo). És l'únic punt
  comú a tots els recàlculs (apply/assign/unassign hi passen). **SUPÒSIT:** caldria decidir si es
  refresquen també les `planned_locked` (probablement no: són punts fixos).

### 9.6 Endolls per graó (el lliurable)

| Graó de la cascada | Estat | ON s'insereix (fitxer:línia) |
|---|---|---|
| 1 · `empíric(item,task)` | **JA EXISTEIX** | `services_i.py:51-52` (`n>=5 → round(mean)`) |
| 2 · `empíric_global(task)` | **NO EXISTEIX** | NOU dins `services_g.lookup_estimated_minutes` entre `effective_minutes(cell)` i el `return None` (`services_g.py:15-17`): si la cel·la no dóna empíric, `Avg(mean_minutes)` sobre `TaskTimeEstimate.filter(task_type, n>=5)`. Requereix query nova (cap substrat de codi). |
| 3 · `llavor(task\|fase)` | **PARCIAL (només per item)** | avui = `cell.estimated_minutes` (`services_i.py:53`, llavor per **item**). El graó task/fase és NOU: fallback addicional a `lookup_estimated_minutes` quan no hi ha cel·la (`services_g.py:9-16`, els dos `return None`). Necessita **font nova** (camp minuts a TaskType o taula per fase). |
| 4 · `demanar al PM` | **NO EXISTEIX** | el `None` final que avui arriba a `scheduler:215`, `plan_service._pin_block:105` i `assign_batch:297`. L'endoll substitueix el `None` silenciós per un senyal/flag (p.ex. marca a `ModelTask` o warning estructurat) en el mateix `lookup_estimated_minutes` (retorn) i el seu consum a `assign_batch:297-300`. |
| Re-resolució (dec. A) | **NO EXISTEIX** | `recompute_for_technicians` abans de `schedule` (`plan_service.py:56-58`): refrescar `estimated_minutes` via `lookup_estimated_minutes` per tasca movible. |

> **Resum d'endoll:** tota la cascada (graons 2-3-4) cap dins **`lookup_estimated_minutes`**
> (`services_g.py:4-17`) com a font única; `effective_minutes` (`services_i.py`) es manté com a
> graó 1. La **propagació** als plans existents depèn d'afegir la re-lectura a
> `recompute_for_technicians` (sense això, la cascada només afecta tasques **noves**).

---

## 10. Per què `grading` no acumula temps

> **VEREDICTE: [A] + [D]** (no [B], no [C] pur). `grading` (Escalat, id=21) retorna `None` perquè
> (A) la feina d'escalat s'executa **sense una ModelTask de `grading` que arribi a Done** — el motor
> de grading és impulsat per **fitting**, no per tasques; i (D) **l'editor d'escalat que SÍ compta
> temps està cablejat a un altre code: `scaling`** (Escalat CAD, id=11), no `grading`. A sobre,
> `grading` té **0 cel·les seed** (el command de sembra el va saltar). No és [B] (no hi ha cap Done
> sense timers: simplement no hi ha cap Done) ni [C] pur (no és "immadur": és **mai alimentat + mai
> sembrat**).

### 10.1 Cel·les de grading — [FET, consulta directa fhort]

| code | cel·les | n≥5 | 0<n<5 | n=0 | amb seed | lookup |
|---|---|---|---|---|---|---|
| **grading** (21) | **0** | 0 | 0 | 0 | **0** | **None** |
| scaling (11) | 57 | 0 | 0 | 57 | 57 | seed (no None) |
| pom (15) | 57 | 0 | 9 | 48 | 57 | seed/empíric |
| size_check (20) | 2 | **2** | 0 | 0 | 0 | empíric madur |

- `grading` no té **ni una** cel·la → ni immadura ni madura: **mai alimentada i mai sembrada**.
- **Per què 0 seed:** `grading` **SÍ** és a `TASK_ORDER` del command (`restructure_garment_types_v2.py:23`)
  — la hipòtesi "no era a TASK_ORDER" és **incorrecta** (FET). El motiu real: el command construeix
  `tt_map` de `TaskType.objects.all()` al moment d'executar-se i **salta** els codes absents
  (`:229-244`, `if tt is None: continue`). El `TaskType` `grading` (pk=21) i `size_check` (pk=20)
  tenen PKs **més altes** que els 8 sembrats (pattern_* 8-10, pom 15, tech_sheet 13, bom 14,
  scaling 11, marking 12) → **postdaten el command** → saltats com a `missing_tasktypes` (SUPÒSIT
  fort, coherent amb 8×57=456 + 2 size_check = 458, i el "513 esperat" del propi command, `:290`).

### 10.2 ModelTask de grading — [FET]

- **1 sola** ModelTask de `grading` a tot el tenant: id=249, **model 182** (= el model QA de size-check
  `[QA-SC]`, memòria), `status=Paused`, `finished_at=None`, timers=[0,0,**76**]. → **0 Done**.
- Contrast: `pom` 19 MT (1 Done amb timer → 1 cel·la alimentada), `size_check` 3 MT (**2 Done amb
  timers → 2 cel·les madures n≥5**), `scaling` 18 MT (**0 Done**), `grading` **1 MT (0 Done)**.
- **El mecanisme d'alimentació FUNCIONA quan una tasca arriba a Done amb timers** (size_check ho
  prova: 2 Done → 2 cel·les n≥5). El forat de `grading` (i `scaling`) és que **cap tasca arriba a
  Done**: Welford només s'alimenta a `Done` (`services_c.py:121-125` → `record_actual_time`).
- **No és [B]:** no hi ha cap Done de grading sense timers; senzillament **0 Done**. El temps existeix
  (76 min en timers de la MT Paused) però **mai es liquida** perquè la tasca no es tanca.

### 10.3 El cablejat real de l'Escalat — [FET]

- **El motor de grading és impulsat per FITTING, no per tasques:** `generate_graded_specs(size_fitting_id)`
  (`pom/services.py:18`) i `bump_grading_version_and_generate(sf_id, …)` (`:461`) operen sobre un
  `SizeFitting`; **no creen ni transicionen cap ModelTask** (grep: cap `ModelTask`/`transition_task`/
  `record_actual_time` a `pom/services.py`, `grading_views.py`, `s9_views.py`). → **executa sense
  ModelTask → mai alimenta Welford** ([A]).
- **L'editor d'escalat que "compta temps" està cablejat a `scaling`, no a `grading`:**
  `KanbanTasks.jsx:615` `isScaling = task.task_type_code === 'scaling'`; el bloc `:702-720` obre
  `/models/{id}/escalat` amb el text `kanban.action.open_grading` ("Obrir escalat"). **No existeix
  cap bloc `isGrading`** a la TaskCard (només `pom`/`tech_sheet`/`size_check`/`scaling`). → el code
  `grading` (id=21) **no té cap eina** que creï/transicioni la seva ModelTask ([D] / anomalia de
  nomenclatura `grading` "Escalat" vs `scaling` "Escalat CAD").
- **Qui crea ModelTask de grading:** només els camins genèrics `define_model_tasks_view`
  (`views_b.py:275`) i `open_model_task_view` (`views_b.py:466`) — cap d'ells específic d'escalat;
  per això només existeix 1 MT de grading (creada a mà sobre el model QA).
- **Fins i tot `scaling` no madura:** té eina (`/escalat`) que auto-arrenca `InProgress`
  (`KanbanTasks.jsx:707-708`) i acumula timers (373 min), **però l'editor no fa cap auto-Done** →
  0 Done → Welford mai s'alimenta. `scaling` no és `None` només perquè està **sembrat** (57 seeds);
  `grading` sí és `None` perquè **no està sembrat**.

### 10.4 On s'hauria d'endollar (si es decideix cablejar) — [SUPÒSIT d'implementació, no implementat]

1. **Decisió de nomenclatura prèvia (bloquejant):** quin code és l'Escalat canònic — `grading`
   (id=21) o `scaling` (id=11)? Avui la feina viva passa per `scaling`; `grading` és orfe al layer
   de tasques (memòria: "anomalia nomenclatura EN ESPERA"). Sense resoldre això, cablejar `grading`
   crearia una tercera via.
2. **Falta el tancament (Done) de l'escalat:** l'eina `/escalat` (`KanbanTasks.jsx:702-720`) només
   fa `InProgress`; **no hi ha cap transició a Done** quan la feina s'acaba → `record_actual_time`
   (`services_c.py:121-125`) mai dispara. **Endoll:** un `transition_task(...,'Done')` en finalitzar/
   desar l'editor d'escalat (com fa el cicle genèric del Kanban), perquè el temps es liquidi.
3. **Si l'Escalat ha de viure al motor de fitting:** `generate_graded_specs` /
   `bump_grading_version_and_generate` (`pom/services.py:18,461`) haurien de **resoldre a Done una
   ModelTask d'escalat** en generar/segellar (avui són 100% task-agnostics) — mirall del que fa
   size_check, que SÍ tanca la seva tasca i per això madura.
4. **Seed pont:** independentment del cablejat, `grading` necessita seed (avui 0 cel·les) — re-córrer
   el seed amb el `TaskType` ja existent, o una fila `TimeSeed(scope='task', key='grading')` (graó 3,
   §9) — perquè deixi de ser `None` mentre no acumuli empíric.

---

## 11. Qui tanca les tasques (per què cap eina arriba a Done)

> **VEREDICTE: hipòtesi REFUTADA — el transport Play/Pause/STOP JA ESTÀ CONSTRUÏT i cablejat.**
> El **Stop humà** (WorkPlan) i el **finish** (Kanban) criden `transition_task(…, 'Done')` →
> `record_actual_time`. El forat NO és "falta el transport (a)". El forat és que, per a les eines
> **obertes** (scaling, grading, tech_sheet…), arribar a Done depèn **només del gest humà Stop**, i
> a les dades de staging **ningú l'ha premut**. `size_check` i `pom` maduren perquè tenen un
> **auto-Done programàtic** lligat a un **esdeveniment de domini discret** (resoldre el size check /
> tancar la taula POM) — cosa que les eines obertes NO tenen. → El tancament del forat és **(a)**:
> ja existeix; falta ús real. **(b)** auto-Done genèric "en tancar l'eina" seria CONTRARI al disseny
> (PLA_DE_TREBALL §3: "Stop és gest humà explícit, no surt de tancar l'eina"), excepte com a
> patró-`size_check` allà on hi hagi un esdeveniment de finalització discret.

### 11.1 Inventari de TOTS els camins a `status='Done'` — [FET]

| # | Camí | Tipus | Anclatge | Quins task_type |
|---|---|---|---|---|
| 1 | **WorkPlan · Stop** | manual (humà) | `WorkPlan.jsx:256` `handleStop → doTransition(task,'Done')`; actiu a InProgress+meva (`:52,135`) | tots (la tasca meva en curs) |
| 2 | **Kanban · finish** | manual (humà) | `KanbanTasks.jsx:33` `{to:'Done', key:'finish'}` → `onTransition(task,'Done')` | tots (InProgress) |
| 3 | **Resoldre size check** | **auto (domini)** | `services_size_check.py:211-223` `transition_task(task,'Done')` (força InProgress abans) | **només `size_check`** |
| 4 | **Tancar la taula POM** | **auto (domini)** | `_close_pom_task_for_model` `views.py:580-602` `transition_task(task,'Done')` | **només `pom`** |
| — | Motor (`transition_task`) | màquina d'estats | `services_c.py:14` `InProgress→{Paused,Done}`; `:121-125` `Done → record_actual_time` | base comuna |

- **No hi ha cap altre camí a Done.** Tots passen per `transition_task` (única porta; `views.py:582`
  ho diu literal: *"l'única porta: status=Done, finished_at, tanca timer, record_actual_time, log"*).
- Welford només s'alimenta a Done (`services_c.py:121-125`). Per tant **maduren només els task_type
  amb un camí 3/4 (auto) o on algú prem 1/2 (manual)**.

### 11.2 Per què `size_check` (i `pom`) SÍ tanquen — auto-Done de domini [FET]

- `size_check`: en **resoldre** el size check (acceptat), el backend força la tasca a Done
  automàticament (`services_size_check.py:220-222`: si no és InProgress hi passa, després Done).
  → 2 Done amb timers → **2 cel·les n≥5** (les úniques madures del tenant).
- `pom`: en **tancar la taula POM**, `_close_pom_task_for_model` fa el mateix (`views.py:598-601`).
  → 1 Done → 1 cel·la alimentada.
- **Patró comú:** tots dos tenen un **esdeveniment de domini discret de finalització** (resoldre /
  tancar taula) on enganxar l'auto-Done. NO violen el "Stop humà" perquè és el propi domini qui
  declara "fet", no el simple tancar l'editor.

### 11.3 Les eines obertes: auto-arrenquen, NO auto-tanquen — [FET]

- `scaling` (`/escalat`), `tech_sheet` (`/fitxa`), `pom`/`size_check` (`/mesures`): obrir l'eina fa
  **auto-Play (InProgress)** fire-and-forget (`KanbanTasks.jsx:649,668,688,708`; `WorkPlan.jsx:213-223`).
- **Cap d'aquests editors crida `transition→Done` en finalitzar/desar** (grep: cap `Done` als
  editors `escalat`/`mesures`/`fitxa`). Queden a InProgress/Paused fins que **un humà** prem Stop
  (WorkPlan) o finish (Kanban). En staging ningú ho ha fet per `scaling`/`grading` → **0 Done**.
- **`grading` és doblement orfe:** ni tan sols té ruta d'eina — `WorkPlan.toolRoute` (`:24-34`) i la
  TaskCard del Kanban només mapen `pom`/`tech_sheet`/`size_check`/`scaling`; `grading` cau a
  `default → null` → Play = InProgress sense navegar, i depèn 100% del Stop manual (que ningú prem).

### 11.4 El transport Stop ESTÀ construït i cablejat — [FET, refuta la hipòtesi]

- `WorkPlan.jsx` (PEÇA P3/P4a) renderitza el transport Play/Pause/**Stop** per tasca; `handleStop`
  (`:256`) = `doTransition(task,'Done')` → `modelTasks.transition(id,{to_status:'Done'})`
  (`endpoints.js:167`) → `transition_task_view` → `transition_task` → `record_actual_time`.
- El comentari `WorkPlan.jsx:254` cita el disseny: *"Stop = gest humà explícit 'feta, 100%' (MAI
  automàtic)"* = PLA_DE_TREBALL §3. És **intencional** que Stop sigui humà.
- Es renderitza al dashboard del model (`DashboardTab.jsx` → `<WorkPlan …/>`). → **el transport
  existeix i funciona**; el que falta a les dades de staging és **l'ús** (ningú ha premut Stop a
  scaling/grading).

### 11.5 Veredicte: com es tanca el forat d'aprenentatge

- **(a) Transport del Pla de treball [Stop humà] — JA FET.** El forat de scaling/grading es tanca
  **amb ús real** del Stop existent; no cal construir res. És un buit de **dades/ús**, no de cablejat.
- **(b) Auto-Done als editors — NOMÉS com a patró-`size_check`/`pom`**, lligat a un esdeveniment de
  domini discret (p.ex. `grading`: en **segellar/generar** l'escalat via fitting —
  `pom/services.py:18,461`, §10.4). Un auto-Done **genèric "en tancar l'editor" seria INCORRECTE i
  contrari al disseny** (tancar ≠ acabat; el tècnic pot pausar/reprendre).
- **(c) Cablejar cada editor a mà — NO cal** per al transport (ja hi és). Només té sentit per
  afegir l'auto-Done discret a un task_type concret (mirall de 3/4), que és l'opció (b) aplicada
  puntualment.

> **Síntesi:** el transport humà (a) ja resol el cas general. La maduració de `grading` queda
> bloquejada abans per dues coses de §10 (no té eina pròpia; nomenclatura `grading`↔`scaling`) i,
> un cop resoltes, pel fet que ningú prem Stop. Si es vol maduració **garantida** sense dependre de
> la disciplina humana, l'única via coherent amb el disseny és (b) puntual: un auto-Done en
> l'esdeveniment de segellat de l'escalat, com fa `size_check` en resoldre's.

---

## 12. Re-cablejat escalat: `grading` ↔ `scaling`

> **Decisió de domini (donada):** `grading` (id=21) = DEFINIR la regla de gradació (eina `/escalat`,
> feina de la Montse). `scaling` (id=11) = APLICAR la regla al patró CAD (eina futura, **no existeix
> avui**). L'eina `/escalat` està mal cablejada al code `scaling`; ha d'anar a `grading`.
> **Impacte del re-cablejat:** 4 punts de frontend a canviar (`'scaling'`→`'grading'`); **cap risc de
> permisos** (Montse té els dos); **0 dades empíriques en joc** (cap scaling MT ha arribat mai a Done
> → 0 cel·les madures); l'únic actiu de dades real són **373 min de timers** en 2 tasques Paused
> (decisió de re-etiquetat pendent) i els **57 seeds** de scaling (decisió d'herència pendent).

### 12.1 Cablejat frontend de `/escalat` — [FET] (4 punts acoblen l'eina a `scaling`)

| # | Punt | Anclatge | Què fa |
|---|---|---|---|
| 1 | Kanban TaskCard | `KanbanTasks.jsx:615` `isScaling = code==='scaling'` + bloc `:702-720` (navega `:710` `/escalat?task_id`) | botó "Obrir escalat" només per code `scaling` |
| 2 | WorkPlan toolRoute | `WorkPlan.jsx:31` `case 'scaling': return /escalat?task_id` | Play obre `/escalat` només per `scaling` |
| 3 | ModelSheet autoEdit | `ModelSheet.jsx:166` `autoEdit==='Escalat' ? 'scaling' : 'pom'` | la ruta `/escalat` obre/transiciona la tasca **`scaling`** |
| 4 | ModelSheet botó tab | `ModelSheet.jsx:349` `enterEdit('Escalat', 'scaling')` | editar el tab Escalat obre/transiciona la tasca **`scaling`** |

- **Mecanisme del compta-temps:** `enterEdit(tab, code)` → `models.openTask(id, code)` (`ModelSheet.jsx:139`)
  = `open_model_task_view` (crea-si-falta + InProgress). Per això editar Escalat arrenca la tasca
  **`scaling`**. Re-cablejar = canviar el `code` `'scaling'`→`'grading'` als 4 punts (i els comentaris
  "Escalat CAD (scaling)" a `KanbanTasks.jsx:614` / `WorkPlan.jsx:30`).
- **La ruta i l'editor:** `App.jsx:141` `models/:id/escalat → ModelSheet(defaultTab='Escalat',
  autoEdit='Escalat')` → `PropagatedEditor`. **L'editor edita la REGLA de gradació** (editar una
  cel·la PROPAGA per regla a les germanes: `escalat/ajustar-talla → propaga_ancoratges`,
  `PropagatedEditor.jsx:11`, `endpoints.js:57-58`). El propi docstring: *"Versionar és l'acte conscient
  'Propagar a grading'"*. → **CONFIRMAT (FET): l'eina és "definir regla de gradació", NO CAD.** Encaixa
  amb la decisió de domini.
- **i18n:** la clau ja és `kanban.action.open_grading` (`en.json:936` "Open grading", `es.json` "Abrir
  escalado", `ca.json` "Obrir escalat"). → re-cablejar **no necessita i18n nou**; la clau ja és
  grading-semàntica (només el `code` comparat és incorrecte).

### 12.2 Les 18 ModelTask de `scaling` — [FET, dades reals fhort]

| Grup | Quantes | Models | Status | Timers | Naturalesa |
|---|---|---|---|---|---|
| Lot FW26 | **15** | BRW-FW26-0001…0015 (163-177) | tots **Pending** | **0 min** | placeholders massius mai treballats (cap té grading MT) |
| QA | 1 (MT254) | BRW-26-SS-0002 (182) | Paused | 0 min | únic model amb grading MT **també** |
| Reals | **2** (MT252/253) | FTT-FW27-0001 (185), FTT-CO27-0001 (186) | Paused | **246 + 127 = 373 min** | feina d'escalat-regla real, assignee profile 1 |

- **Cap és feina de CAD** (l'eina CAD no existeix): els 373 min són **feina de regla d'escalat
  mal-etiquetada `scaling`** → segons la decisió, haurien de ser `grading`. (FET)
- **0 Done** entre les 18 → **cap ha alimentat Welford** → scaling segueix a 57 cel·les seed n=0
  (cap empíric en joc).
- **Impacte del re-cablejat sobre aquestes files (EXPOSAT, no decidit):** canviar el frontend
  **NO mou cap fila** — les 18 MT segueixen `scaling`. A partir d'ara, editar Escalat crearà/obrirà
  tasques **`grading`**. Conseqüències a decidir:
  - els **373 min** (MT252/253) queden penjats sota `scaling`, un code que ja no rep l'eina →
    o es **re-tipen** a grading (moure task_type + timers), o es deixen orfes. (Timers mai liquidats:
    Paused, no Done → no eren a Welford de totes maneres.)
  - els **15 placeholders** Pending: doblement orfes (scaling=CAD futur, no s'executa) → candidats a
    esborrar o re-tipar a grading.

### 12.3 Seed de `scaling` (57 cel·les) — [FET + decisió EXPOSADA]

- `scaling` té **57 seeds** (estimated_minutes L/M/P), tots **n=0**; `grading` té **0 cel·les**.
- Els 57 seeds es van autorar quan `scaling` ERA l'eina d'escalat (TASK_ORDER) → els minuts
  reflecteixen, versemblantment, el temps de **definir la regla** (la feina que ara és `grading`). (SUPÒSIT)
- **Decisió pendent (no decidir aquí):**
  - **(i)** `grading` **hereta** els 57 seeds (representen la feina d'escalat-regla) i `scaling`
    queda net fins que existeixi l'eina CAD; **o**
  - **(ii)** `scaling` **conserva** els seeds re-interpretats com a "aplicar al CAD" — però aleshores
    són **soroll** per a una eina que no s'executa, i `grading` segueix a 0 (→ `None`/graó-3 fins que
    acumuli o se sembri `TimeSeed`).
- Coherent amb §9/§10: si no s'hereta, `grading` necessitarà `TimeSeed(scope='task', key='grading')`
  o re-seed per no ser `None`.

### 12.4 Allow-list i permisos — [FET: re-cablejat SEGUR]

| usuari | rol | `permisos.tasks` | scaling | grading |
|---|---|---|---|---|
| Montse | manager | `[…, 'scaling', …, 'grading']` (9 codes) | ✅ | ✅ |
| Marta | technician | `['pom','tech_sheet','Audit']` | ❌ | ❌ |
| a.devant / Salva | admin | `[]` (bypass) | ✅ | ✅ |

- **Cap usuari té `scaling` sense `grading` ni viceversa.** La Montse (qui fa l'escalat) té **els dos**
  → re-cablejar l'eina a `grading` **NO la deixa sense permís**. (FET) Marta no fa escalat (cap dels
  dos). Admins bypass.
- → El re-cablejat és **net pel costat de permisos**: no cal tocar cap allow-list.

### 12.5 Resum d'impacte

| Àmbit | Impacte del re-cablejat scaling→grading |
|---|---|
| Frontend | 4 canvis de string `'scaling'`→`'grading'` (KanbanTasks:615, WorkPlan:31, ModelSheet:166, ModelSheet:349) + comentaris; i18n ja OK. |
| Permisos | **Cap** — Montse té els dos; ningú té un sense l'altre. |
| Dades empíriques | **Cap** — 0 scaling Done, 0 cel·les madures. |
| Timers | **373 min** (MT252/253) i 15 placeholders queden sota `scaling`; decisió de re-tipar/esborrar **pendent** (no la fa el canvi de frontend). |
| Seed | 57 seeds de scaling: decisió **herència→grading** vs **mantenir** pendent; sense herència, grading=`None` fins TimeSeed/empíric. |

---

## 13. Reconcepció de navegació: per-tasca dins el model + board per-model al dashboard

> **RECOMANACIÓ: JUBILAR la pantalla Kanban global (`/tasques/kanban`); FER CRÉIXER el Dashboard
> (`/`) cap al board per-model.** La meitat per-TASCA del Kanban ja té casa dins el ModelSheet
> (WorkPlan al tab Dashboard); la meitat per-MODEL (columna 1: comptes per estat + filtres + gate
> cards) és el llavor del board nou, que encaixa al Dashboard (ja és el landing del tècnic amb KPIs i
> llista de models). **Gran reús:** l'estat-kanban del model és DERIVABLE de l'endpoint `by-model`
> existent, i les "fites de calendari" ja les serveix `/api/v1/calendar/events/`. Mapatge de
> nomenclatura: els 4 estats "Pending/Open/Paused/Done" = `ModelTask.status`
> Pending/**InProgress**/Paused/Done (al codi és `InProgress`; "Open" és el terme de domini).

### 13.1 Inventari de pantalles — [FET]

| Pantalla | Fitxer | Què és | Font de dades | Granularitat | Ruta/menú |
|---|---|---|---|---|---|
| **Kanban** | `KanbanTasks.jsx` | master-detall 5 col: `[models \| Pending \| Paused \| InProgress \| Done]` (`:9-26`) | col1 = `modelTasks.byModel()` (`:121`); cols 2-5 = `fetchAllPages(modelTasks.list,{model})` (`:198`) | **mixta**: col1 per-model, cols 2-5 per-tasca | `/tasques/kanban` (`App.jsx:151`, `Sidebar.jsx:50`) |
| **Dashboard** | `Dashboard.jsx` | landing tècnic/PM: KPIs + 5 models recents | `/models/?...&limit` (`:9-49`) | per-model (llista) | `/` index (`App.jsx:131`, `Sidebar.jsx:47`) |
| **DashboardTab** | `model/DashboardTab.jsx` | TAB dins ModelSheet: "on sóc" + artefactes + tasques | `/models/{id}/dashboard/` (`:62-74`) | per-model (obert) | tab dins ModelSheet (`ModelSheet.jsx:266`) |
| **WorkPlan** | `model/WorkPlan.jsx` | graella de tasques del model + transport Play/Pause/Stop | `DashboardTab.tasques` (passat, `:129`) | per-tasca (d'1 model) | embegut a DashboardTab |
| **ModelSheet** | `ModelSheet.jsx` | hub per-model, 7 tabs | `/models/{id}/` | per-model | `/models/:id` (`App.jsx:136`) |

- **Tabs de ModelSheet** (`ModelSheet.jsx:21`): `['Dashboard','Resum','Mesures','Escalat','Fitxa tècnica','Fitxers',"Registre d'activitat"]`. **Les tasques del model ja viuen DINS el ModelSheet**, al tab Dashboard via WorkPlan (`:266`→`DashboardTab`→`:129 WorkPlan`). → "moure els estats de tasca dins el model" està **parcialment FET** (falta la vista 4-columnes; WorkPlan és graella plana).
- Polling Kanban 30s (`KanbanTasks.jsx:214-224`).

### 13.2 Estat-kanban del model: DERIVABLE de dades existents — [FET]

- **`by-model` JA agrega per-model:** `GET /api/v1/model-task-items/by-model/` (`views_b.py:78-188`)
  retorna per model `{model_id, model_codi, fase, counts:{pending,paused,in_progress,done}}`
  (`:97,184-188`), amb `in_progress=Count(filter=Q(status='InProgress'))` etc. (`:155-158`), ordenat
  `-in_progress,-pending,-paused,codi_intern` (`:76`), i **filtra fora els models tot-Done**
  (`:176`). Accepta els filtres de campanya (temporada/estat/responsable/garment_type/any/prioritat).
- **L'estat-kanban de 4 valors NO existeix com a camp**, però és **derivable trivialment** dels
  `counts` (lògica nova ~4 línies; p.ex. Open si `in_progress>0`; Paused si `paused>0 && in_progress=0`;
  Pending si només pending; Done si tot done). `KanbanTasks.jsx:38` ja en fa una versió
  (`isActiveModel = counts.in_progress>0 || counts.paused>0`).
  → **NO és "construir de zero": el substrat (counts) ja hi és; només falta la classificació + UI.**
- **`fase_actual` ≠ estat-kanban (CONFIRMAT, eixos independents):** `fase_actual` ∈
  Pending/Dev/Proto/SizeSet/PP/TOP (`models_app/models.py:94-101`) = fase de disseny (gates);
  `ModelTask.status` ∈ Pending/Paused/InProgress/Done (`tasks/models.py:105-109`) = execució. El board
  usa l'**estat-kanban derivat** per a les 4 columnes; els **comptadors "models per fase"** usen
  `fase_actual`.

### 13.3 Filtres i agregats — [FET + mancances]

- **Filtres del Model list** (`models_app/views.py:26`): `estat, fase_actual, garment_type,
  responsable, temporada, any`. `search`: `codi_intern, codi_client, nom_prenda` (`:27`). Ordre:
  `prioritat, data_objectiu, data_entrada` (`:28`).
- **Camps de campanya al model:** `temporada` (SS/FW/CO/SP), `any`, `customer` (FK, `:125-131`),
  `collection` (CharField, `:144`), `prioritat` (`:215`). → **`customer` i `collection` NO són a
  `filterset_fields`** avui: cal afegir-los per filtrar el board per client/col·lecció. (mancança)
- **Camps de data per filtrar:** `data_objectiu`, `data_entrada`, `data_tancament`,
  `predicted_start/end`, `created_at`, `consumption_started_at` (`models_app/models.py:204-229`).
  Filtres de **rang de dates NO existeixen** al filterset (cal `DateFromToRangeFilter` o similar). (mancança)
- **Comptadors per fase:** **NO existeix endpoint.** `Dashboard.jsx` fa KPIs amb crides
  `/models/?estat=…&limit` i compta al front (`:9-49`). Un comptador real seria
  `Model.objects.values('fase_actual').annotate(Count('id'))` (nou, ~3 línies). (mancança)

### 13.4 Fites de calendari: JA agregades — [FET, reutilitzable sencer]

- **`GET /api/v1/calendar/events/?start=…&end=…`** (`planning/views.py:210-488`) ja unifica 3 fonts:
  - **tasca** — `ModelTask.planned_start/planned_end` (`:236-282`), amb `en_risc` si `planned_end >
    data_objectiu`.
  - **confecció** — `Production.expected_at` (arribada de proto/mostra; `tasks/models.py:223-247`,
    view `:283-321`).
  - **fitting** — `FittingSession.data` (+`start_time`, `estat`; `fitting/models.py:202-289`, view
    `:326-486`), amb agrupació de convocatòria i `avis_abans_confeccio`.
  - Consumit per `PlanningCalendar.jsx`. Scope per `view_team_tasks`.
- → **"Properes fites" del dashboard = consulta a aquest endpoint** (rang futur, agrupar per
  model/tipus). **Cap view nova.** (GateEvent `at` és fita PASSADA, no hi entra.)

### 13.5 Per pantalla: reusable / jubilar / nou

| Pantalla | Reusable | Es jubila | Es construeix nou |
|---|---|---|---|
| **KanbanTasks** | col1 (by-model + filtres + gate cards + scroll infinit); `TaskCard` (~135 línies, tool-open isPom/isGrading + transport, `:605-739`) | la **pàgina** 5-col global + ruta `/tasques/kanban` + entrada de menú | — |
| **Dashboard** (`/`) | KPIs (counters), llista de models, és el landing | — (es **fa créixer**) | board per-model 4-col + comptadors per fase + llista de fites |
| **DashboardTab / WorkPlan** | WorkPlan (transport, toolRoute, handoff) ja mostra tasques del model | — | vista 4-columnes de les tasques del model (avui graella plana) — o nova tab "Tasques" |
| **ModelSheet** | hub + tabs + `enterEdit`/`openTask` (compta-temps) | — | rebre la vista per-tasca (les 4 columnes del Kanban absorbides aquí) |

### 13.6 Recomanació raonada: jubilar Kanban, NO el Dashboard

1. **El domini dissol el nivell-tasca global:** si els 4 estats viuen DINS el model, les columnes
   2-5 del Kanban perden el sentit com a pantalla global → la seva lògica va a ModelSheet (on WorkPlan
   ja la té a mitges). Mantenir el Kanban global contradiria la decisió.
2. **El board per-model encaixa al Dashboard:** el Dashboard ja és el **landing del tècnic** (`/`),
   ja té **comptadors** i **llista de models**. El board per-model (4 col + fites) hi creix natural,
   reusant `by-model` (estat derivat) i `calendar/events` (fites).
3. **Jubilar el Dashboard seria pitjor:** deixaria el board per-model sense casa natural i forçaria
   reusar la ruta `/tasques/kanban` —justament el nivell que el domini dissol— i perdria el rol de
   landing/KPIs.
4. **"Jubilar Kanban" ≠ esborrar-ho tot:** és retirar la **pàgina** 5-col; **collir** col1 → board del
   Dashboard, i `TaskCard`/transport → la vista per-tasca de ModelSheet.

> **Matís de feina (redueix l'esforç):** moure els estats "dins el model" està **parcialment fet**
> (WorkPlan al DashboardTab). El nou principalment és: (a) classificació estat-kanban derivada dels
> counts; (b) UI 4-col al Dashboard (per-model) i a ModelSheet (per-tasca); (c) comptadors per fase
> i llista de fites (ambdós sobre endpoints existents); (d) filtres `customer`/`collection` + rang de
> dates al backend.

### 13.7 Mapa de dependències (què toca què)

- **Backend reutilitzat (sense canvi de contracte):** `model-task-items/by-model/` (estat+counts per
  model), `calendar/events/` (fites), `models/` list + `models/{id}/dashboard/`.
- **Backend nou/ampliat:** afegir `customer`,`collection` (+ rang de dates) a `filterset_fields`
  (`models_app/views.py:26`); endpoint/anotació de **comptadors per fase**; (opcional) exposar
  l'**estat-kanban derivat** dins `by-model` perquè el front no el recalculi.
- **Frontend jubilat:** `KanbanTasks.jsx` (pàgina), ruta `App.jsx:151`, menú `Sidebar.jsx:50`.
- **Frontend nou/crescut:** `Dashboard.jsx` → board per-model (harvest de col1 + `TaskCard`);
  `ModelSheet`/`DashboardTab`/`WorkPlan` → vista 4-col per-tasca (nova tab o WorkPlan ampliat).
- **Risc/àncores a vigilar:** el `TaskCard` del Kanban (tool-open per `isGrading`/`isPom`…, ja
  re-cablejat a §12) i el de WorkPlan dupliquen lògica (deute anotat a `WorkPlan.jsx:21-23`); en
  moure-ho a ModelSheet, **convergir-los** (un sol TaskCard) evita el tercer duplicat. Les transicions
  segueixen per `transition_task` (intacte).

---

## 14. Estat d'implementació del Pla de treball + gaps

> **Resum:** el **contenidor (P2)** i el **transport Play/Pause/Stop (P3)** estan **FETS**; el
> **handoff de reassignació (§6 / P4a)** està **FET** (claim + diàleg + recompute). El que **falta**
> és tot el que depèn d'un **camp d'origen a `ModelTask`** (no existeix): el rendering **"fora
> d'encàrrec"** (codi present però INERT), la **"Tasca externa lliure"** (sense component), i el
> camí d'**iniciar una tasca ad-hoc**. També és gap el selector **"Què haig de fer"** (Fase→tasca)
> per al tècnic, tot i que els endpoints de creació ja existeixen. Nota transversal: el frontend
> **no consumeix** els camps nous del catàleg (`eina`/`tipus`/`fase`) — encara **hardcodeja l'eina
> per `code`**.

### 14.1 Taula per peça de disseny

| Peça (disseny) | Estat | Anclatge (FET) |
|---|---|---|
| **P2 · contenidor Pla de treball** | **JA FET** | `WorkPlan.jsx` renderitzat a `DashboardTab.jsx:129`; graella de `TaskCard` + barra de progrés (`WorkPlan.jsx:258-290`) |
| **P3 · transport Play/Pause/Stop** | **JA FET** | `WorkPlan.jsx` `handlePlay/Pause/Stop` (`:226,255,256`) → `modelTasks.transition`; Stop→Done (`:256`); TRANSPORT per estat (`:49-54`) |
| **Rending 1 · "Meva" (nítida)** | **JA FET** | `isMine` (`WorkPlan.jsx:168` `assignee_id === myProfileId`); transport operable; `opacity:1` (`:97`) |
| **Rending 2 · "D'altri" (fade + nom)** | **JA FET** | `otherTech` (`:90`); `opacity:0.55` (`:97`); mostra `assignee_nom` (`:116-119`); Pause/Stop apagats, Play=handoff (`:133-135`) |
| **Rending 3 · "Fora d'encàrrec" (filet grana)** | **GAP (visual INERT)** | el filet i l'etiqueta existeixen (`:94-95,121-126`) PERÒ `isOutOfCharge(_task){return false}` (`:57-58`) → **mai es pinta**; comentari literal *"TODO P4: derivar de l'origen/flag de tasca externa"* |
| **Tasca externa lliure (nom fix + text lliure, sense eina)** | **GAP** | cap component; grep `externa/lliure/free` → només el stub de `WorkPlan` i la clau i18n `out_of_charge`. No hi ha card de text lliure |
| **§6 / P4a · handoff de reassignació** | **JA FET** | Backend: `claim_task_view` (`views_b.py:377`) → `recompute_for_technicians` dels dos tècnics (`:395-396,420`). Frontend: Play sobre tasca d'altri → diàleg (`WorkPlan.jsx:226-229`), `confirmHandoff` → `modelTasks.claim` → `playMine` (`:234-252`); Modal (`:291-303`) |
| **Camp origen/prevista/ad-hoc a `ModelTask`** | **GAP** | `ModelTask` no té cap flag d'origen (grep `origen/prevista/ad_hoc/external` → res; només `planned_end` "Fi prevista"). És el camp que necessiten Rending-3 i la tasca ad-hoc |
| **D1 · "Què tinc fet" (artefactes)** | **JA FET** | `DashboardTab.jsx:174-239` (secció `section_done`): Fitxa / Grading / Base, cada un navega a la seva pestanya |
| **D2 · "Què haig de fer" (selector Fase→tasca)** | **GAP (per al tècnic); PARCIAL via wizard** | cap picker a `DashboardTab`/`WorkPlan`/`ModelSheet` (grep buit). Existeix `TaskAssignWizard` (assignar `task_type×persona×data`) però muntat a `Planning.jsx:324` i `ActionsMenu.jsx:217` (PM), no com a auto-servei del tècnic |
| **Arbre de tasques global / iniciar tasca arbitrària** | **GAP** | `/task-types` és **consulta read-only** (Sidebar `:61`); cap menú "iniciar tasca"; iniciar una no-prevista exigiria el flag ad-hoc (sobre) + UI |

### 14.2 Substrat de creació de tasques que JA existeix (per a D2 / ad-hoc) — [FET]

- `defineTasks` → `POST /models/{id}/define-tasks/ {task_type_ids:[…]}` (`endpoints.js:32`; backend `views_b.py:255-280`): crea ModelTasks en lot des d'una llista de TaskType.
- `openTask` → `POST /models/{id}/open-task/ {code}` (`endpoints.js:34`; backend `views_b.py:466`): crea-si-falta + transiciona; avui només el criden els editors d'eina (`ModelSheet.jsx:124,139`), no un picker lliure.
- `assignBatch` → `plan/assign-batch` (`endpoints.js:259`; `plan_service.assign_batch`): el wizard PM.
- → **Els 3 endpoints de creació ja hi són**; el gap de D2 és **UI** (un selector Fase→tasca al dashboard del model), no backend.

### 14.3 Nota transversal: el catàleg enriquit NO arriba al frontend — [FET]

- `ModelTaskSerializer` (`serializers_b.py`) exposa **només** `task_type_code` i `task_type_name`
  (`:107-...`), **no** `eina`/`tipus`/`fase`/`mode` (els camps afegits al catàleg al sprint anterior).
- Conseqüència: el frontend **hardcodeja** quina tasca té eina i quina (switch `toolRoute` per `code`
  a `WorkPlan.jsx:24-34`; `isPom/isGrading/…` a `KanbanTasks.jsx`). La noció de catàleg
  **"Externa-lliure = sense eina"** (`tipus`) **no és data-driven**: les Externa-lliure
  (`design_review`, `design_clarify`, `pattern_hand`, `Audit`) cauen a `toolRoute → null` per
  **omissió** (no són al switch), de manera que el Play les arrenca a InProgress **sense navegar**
  (`WorkPlan.jsx:220-222`) — funciona, però per casualitat, no perquè llegeixi `tipus`/`eina`.

### 14.4 Mapa net: què queda per construir de veritat

**Ja hi és (no reimplementar):** P2 contenidor · P3 transport (Play/Pause/Stop→Done) · rendings
Meva i D'altri · handoff §6 complet (claim+diàleg+recompute) · "Què tinc fet" (artefactes) · els 3
endpoints de creació de tasca · l'arrencada de tasques sense eina (transport manual).

**Gaps reals (per ordre de dependència):**
1. **Camp d'origen a `ModelTask`** (p.ex. `origen` ∈ {prevista, ad-hoc/externa}) — **desbloqueja**
   el rending "fora d'encàrrec" i la tasca ad-hoc. Migració additiva (nova columna) + exposar-lo al
   serializer.
2. **Activar el rending "fora d'encàrrec"**: substituir `isOutOfCharge` stub (`WorkPlan.jsx:57`) per
   la lectura del flag (1). El visual ja està pintat.
3. **Component "Tasca externa lliure"**: card amb nom fix + text lliure + transport manual (sense
   eina); requereix (1) per marcar-la i un camp de text (nou) o reusar notes.
4. **Selector "Què haig de fer" (D2)** al dashboard del model: UI Fase→tasca que crida
   `defineTasks`/`openTask` (backend ja llest).
5. **Camí "iniciar tasca arbitrària"** (arbre global): UI que crea ModelTask ad-hoc (depèn de 1).
6. **(transversal) Exposar `eina`/`tipus`/`fase` al `ModelTaskSerializer`** i fer el frontend
   data-driven (substituir els hardcodes de `toolRoute`/`isPom…`), perquè les Externa-lliure es
   tractin per `tipus`, no per omissió.

> **SUPÒSIT (nomenclatura de rendings):** el codi documenta **3** rendings (`WorkPlan.jsx:17`
> *"Tres rendings (§5): meva / d'altri / fora d'encàrrec"*). El disseny n'esmenta 5; els 2 restants
> mapen versemblantment a la **tasca externa lliure** i a una variant d'estat — tots dos dins els
> gaps de dalt. Convé confirmar el recompte amb PLA_DE_TREBALL §2/§5.

---

## 15. Què haig de fer unificat + eina Mesures

> **Tipus:** diagnosi READ-ONLY (data 2026-06-25). Cap escriptura, migració, commit ni restart.
> **Refà el disseny a partir de dues clarificacions de domini (Agus):**
> (1) **El FLUX no és la TASCA.** L'eina **Mesures** serveix MÚLTIPLES tasques (Definició POM, presa
> de mesures, size check). Que "Definició POM obri Mesures amb wizard d'importació" és **CORRECTE**,
> no un bug. (2) **"Properes fites" i "Què haig de fer" són LA MATEIXA cosa dins el model:** les
> fites d'un model (arriba proto, fitting, tasca pendent) SÓN el que el tècnic ha de fer en aquell
> model → es **fusionen en UNA zona** dins el ModelSheet; al **Dashboard global les fites
> DESAPAREIXEN**.

### 15.A Veredicte sobre la pantalla de Mesures: **BONA (viva, multi-mode)** — [FET]

**El camí "Definició POM" → Mesures (FET):**

| Tasca (code) | Ruta que obre | Anclatge |
|---|---|---|
| `pom` (Definició POM) | `/models/{id}/mesures` (**sense** task_id) | `WorkPlan.jsx:26` |
| `size_check` (Mesurar prenda) | `/models/{id}/mesures?task_id={id}` | `WorkPlan.jsx:29` |
| `tech_sheet` | `/models/{id}/fitxa?task_id={id}` | `WorkPlan.jsx:27` |
| `grading` (Escalat) | `/models/{id}/escalat?task_id={id}` | `WorkPlan.jsx:32` (re-cablejat §12) |

- La ruta `/models/:id/mesures` renderitza **`ModelMeasurements`** (pàgina standalone, lazy)
  — `App.jsx:137,26`. La ruta antiga `/size-check` **redirigeix** a `/mesures` conservant `task_id`
  (`SizeCheckRedirect`, `App.jsx:48-52,144`). **FET.**
- **`ModelMeasurements.jsx` és l'orquestrador VIU i multi-mode** (FET): estats
  `loading | selector | manual | import | resultat`, més `checkMode` (si `?task_id=` és una tasca
  `size_check` → renderitza `CheckMeasureEditor`). "Definició POM" (sense task_id) cau al **selector**
  (triar Manual vs **Importar**) → coherent amb la clarificació (1): el wizard d'importació és
  legítim, no un bug.
- **Graella S/M/L/XL/XXL + Δ + "Afegir POM"** (la img 2): la pinta **`EditableTable.jsx`** (modes
  manual/resultat de `ModelMeasurements`). L'editor de mesures compartit (check/fitting) és
  **`MeasureGrid.jsx`**, embolcallat per **`CheckMeasureEditor.jsx`**. **(detall de components:
  SUPÒSIT a partir de la investigació; l'orquestració i les rutes són FET.)**
- **Wizard d'importació:** `ImportWizard/ImportWizard.jsx` (5 passos: sizes→poms→measures→fabric→
  save), **integrat dins `ModelMeasurements`** (mode `import`), s'obre per botó del selector (no
  automàtic). **FET.**

**No hi ha editor antic viu (FET):** els components vells **NO existeixen en disc** —
`MeasurementTable.jsx` (esborrat a P1), `SizeCheckWork.jsx` (substituït per `MeasureGrid`),
`GarmentPOMMapEditor.jsx` (mort, endpoints `pom-map/*`→404). Les úniques referències són
**comentaris** residuals (`App.jsx:20-22`, `CheckMeasureEditor.jsx:9` *"substitueix SizeCheckWork"*).
→ **No hi ha fragmentació vell↔nou en codi enrutat.**

> **VEREDICTE: la pantalla de Mesures a què arriba "Definició POM" és la BONA** — `ModelMeasurements.jsx`
> (pàgina), viva i mantinguda, **una sola superfície multi-mode**. **Matís (no és "vell vs nou", és
> DUPLICACIÓ d'embolcall):** hi ha **dues entrades** a la mateixa base de components — (1) la pàgina
> standalone `/models/:id/mesures` (via Play sobre tasca pom/size_check) i (2) el **tab "Mesures"
> del ModelSheet**, que incrusta `CheckMeasureEditor` inline (`ModelSheet.jsx`). Mateixos
> `MeasureGrid`/`EditableTable` a sota; **convergir-les** és deute net (mirall del deute de TaskCard
> §13.7), no un bug.

**El "una superfície, modes diferents" — PARCIALMENT complert (SUPÒSIT/FET):** el catàleg **JA porta**
el mode (`TaskType.eina`/`TaskType.mode`: `pom`→`mesures`/`autoria_base`, `size_check`→`mesures`/`presa`
— §15.C, FET). Però el frontend **encara deriva la ruta i el mode per `code` hardcodejat**
(`toolRoute` switch, `WorkPlan.jsx:24-32`; `checkMode` per `task_id`), **no** llegint `eina`/`mode`
del catàleg. → El mecanisme "una eina, sub-modes" existeix de facto a `ModelMeasurements`, però **no
és data-driven** (lligam amb §14.3). Fer-lo data-driven és el pont net cap a la clarificació (1).

### 15.B Com obtenir les fites d'UN sol model — [FET]

- **`calendar/events` NO filtra per model (FET):** `GET /api/v1/calendar/events/`
  (`planning/views.py:212-488`) accepta **només** `start`/`end` (`:244`). No hi ha param `model_id`.
  *(El `model_ids` de `planning/views.py:100-105` és del motor `/plan/compute/`, no d'aquest
  endpoint.)*
- **Les 3 fonts de fita SÓN consultables per `model_id` (FK directa, FET):**

| Font | Model · camp data | FK a Model | Anclatge |
|---|---|---|---|
| Tasca | `ModelTask.planned_start/planned_end` | directa (`model`) | `tasks/models.py:107` |
| Confecció | `Production.expected_at` | directa (`model`) | `tasks/models.py:229` |
| Fitting | `FittingSession.data` (+`start_time`,`estat`) | directa (`model`, nullable XOR `garment_set`) | `fitting/models.py:202` |

- **Cap endpoint per-model serveix fites avui (FET):** `/models/{id}/dashboard/`
  (`models_app/views.py:1807-1934`) retorna les tasques **però SENSE `planned_*`**; `/timeline/`
  (`:1939-2037`) és historial passat. → buit d'agenda futura per-model.
- **Vies per obtenir-les (SUPÒSIT d'implementació, READ-ONLY):** **(A, mínima)** afegir
  `?model_id=` opcional a `calendar/events` i filtrar les 3 fonts al backend (reusa tota la lògica);
  **(B)** endpoint nou `/models/{id}/milestones/`; **(C)** filtrat al client (ineficient: avui el
  Dashboard ja descarrega TOTS els events de 14 dies). **A** és la de menys radi.

### 15.C Mapa de la zona unificada "Què haig de fer" = fites(model) + tasques-obribles(model)

**Pota 1 — fites(model):** §15.B (cal la via A/B; substrat de dades complet).

**Pota 2 — tasques-obribles(model) per fase:**
- **Catàleg enriquit JA existeix (FET):** `TaskType` té `fase` (6 choices: Disseny / Dev. tècnic /
  Prototip / Mostres / Preproducció / Producció), `tipus` (Interna / Externa-lliure), `eina`, `mode`,
  `facturable` — `tasks/models.py:68-93`. El docstring confirma la clarificació de domini: *"Gate i
  espera NO són tasca → no hi ha és_gate ni bloqueja_model aquí"*.
- **Seed real (FET, `migrations/0025_seed_canonical_task_types.py`):** 13 task types; **2 a
  `Disseny`** (`design_review`, `design_clarify`, tots dos Externa-lliure sense eina), **11 a
  `Dev. tècnic`**, **0** a Prototip/Mostres/Preproducció/Producció (gap de cobertura: la fase com a
  eix té 4 valors buits).
- **GAP de superfície (FET):** `TaskTypeSerializer` exposa només `['id','code','name','default_order',
  'active']` (`serializers_b.py:7-10`) → **no surt `fase`/`tipus`/`eina`/`mode`** → el frontend **no
  pot agrupar per fase avui**. Desbloqueig: afegir aquests camps al serializer (additiu, 1 línia) o
  un endpoint compositor.
- **Estat al model (FET):** quines ModelTask ja existeixen i amb quin estat → `/models/{id}/dashboard/`
  (`tasques[]`: `task_type_code`, `task_type_name`, `status`, `assignee`) i `by-model`. **Cap
  endpoint creua catàleg×model** (catàleg-per-fase + "ja existeix / es pot crear").
- **Picker Fase→tasca: GAP (FET).** No existeix selector al ModelSheet/DashboardTab/WorkPlan.
  `TaskAssignWizard.jsx` existeix (assignar `task_type×persona×data`) però és **eina del PM** (muntat
  a `ActionsMenu`/`Planning`), tria d'una llista **plana sense agrupar per fase**, i no és autoservei
  del tècnic.

**La zona unificada (síntesi de disseny):** una sola zona dins el **ModelSheet** (germana del "Pla de
treball" / WorkPlan), que ajunta — perquè per al tècnic són la mateixa pregunta sobre aquell model —:
(i) **fites del model** (§15.B: tasques planificades + confecció + fitting que arriben) i (ii)
**tasques-obribles per fase** (catàleg enriquit + estat al model). Substrat de creació ja llest (els
3 endpoints define-tasks/open-task/assign-batch, §14.2); el que falta és **exposar `fase` al
serializer** + la **via de fites per-model** + la **UI**.

### 15.D Què es retira del Dashboard global — [FET]

- **ES RETIRA:** la zona **"Properes fites"** = component `UpcomingMilestones`
  (`Dashboard.jsx:311-402`, cridat a `:521-522`; finestra `MILESTONES_DAYS=14`, `:300`). És
  **Sprint 5/3** (commit `b2aca22`), crida `calendar/events({start: avui, end: avui+14})` i agrupa
  per dia. Es mou a la zona per-model (§15.C); al global desapareix. *(També les claus i18n
  `dashboard.milestones.*` es mourien — no esborrar fins haver mogut.)*
- **ES MANTÉ:** KPI cards · **`ModelBoard`** 4-col per `kanban_state` (`Dashboard.jsx:99`,
  derivat al backend) · comptadors per fase · filtres de campanya · greeting.
- **Codes crus a "Properes fites" (causa arrel, FET):** el backend construeix el `titol` de l'event
  de **tasca** amb el **`code`** en cru — `f'{model.codi_intern} · {task_type.code}'`
  (`planning/views.py:270`) — i `meta.task_type` és el code, **no** el name (`:276-282`). (Confecció
  `:307` i fitting `:370` NO pateixen això: usen `supplier.name` / `fase`.) El front pinta
  `ev.titol` directe, **sense** `taskTypeLabel(t, code, name)`. → S'arregla al backend (usar
  `task_type.name`, o afegir `task_type_name` als `meta` per a lookup al front). Rellevant perquè
  aquesta lògica de fita **es mou** a la zona per-model: arrossegar-la tal qual replicaria el codi
  cru.

### 15.E Abast del board: "tots els models" vs "els meus" — [substrat backend JA HI ÉS]

- **`by-model` ja deriva "els meus" (FET):** `?responsable=me` filtra models on el **current user és
  ASSIGNEE d'≥1 ModelTask** (`views_b.py:130-140`, comentari *"FIX 2 — 'jo' = models on sóc ASSIGNEE
  ... no Model.responsable, sovint null"*). `?responsable=<id>` fa el mateix per a un perfil concret.
  → És exactament el doble abast informativa/executiva (TAXONOMIA §8.1) **a nivell de model**.
  ⚠️ Semàntica: "responsable" aquí = **tinc-tasca-assignada** (càrrega real), **no** `Model.responsable`
  (director del model).
- **Substrat de dades complet (FET):** `ModelTask.assignee` (FK `accounts.UserProfile`, nullable,
  `tasks/models.py:110-111`) — "models meus" = `Model` amb ≥1 `ModelTask.assignee = jo`, ja derivat.
- **Default per rol — info disponible (FET):** `UserProfile.rol_nom` + capabilities; **`VIEW_TEAM_TASKS`**
  la tenen manager/PM*/admin però **no** technician (`accounts/capabilities.py`). → el backend té el
  senyal per a un default (tècnic→meus, PM/admin→tots). **El default el decideix Agus** (aquí només
  es constata el substrat). *(matís: el mapa de capabilities per rol cal confirmar-lo amb
  `capabilities.py`; PM pot tenir o no `VIEW_TEAM_TASKS` segons la taula real.)*
- **Frontend: GAP (FET).** Cap toggle d'abast: `ModelBoard` (`Dashboard.jsx:99`) no passa
  `responsable` als params. Backend llest; falta **UI (toggle Tots↔Els meus) + persistència de
  preferència**.

### 15.F Resum d'endolls (el lliurable, READ-ONLY)

| Peça | Estat | On |
|---|---|---|
| Pantalla Mesures (Definició POM) | **BONA / viva / multi-mode** | `ModelMeasurements.jsx` (+ `EditableTable`/`MeasureGrid`/`CheckMeasureEditor`/`ImportWizard`) |
| Editor antic de mesures | **no existeix** (esborrat) | només comentaris (`App.jsx:20-22`, `CheckMeasureEditor.jsx:9`) |
| Duplicació d'entrada a Mesures | **deute** (convergir) | pàgina `/mesures` ↔ tab Mesures de `ModelSheet` |
| Mode data-driven (eina/mode del catàleg) | **GAP** (hardcode per code) | `WorkPlan.jsx:24-32` (lligam §14.3) |
| Fites per-model | **GAP backend** (substrat OK) | afegir `?model_id` a `calendar/events` (`planning/views.py:244`) |
| Catàleg per fase al front | **GAP serializer** | `TaskTypeSerializer` (`serializers_b.py:7-10`) no exposa `fase/tipus/eina/mode` |
| Picker Fase→tasca (tècnic) | **GAP** | no existeix; `TaskAssignWizard` és del PM, sense fase |
| Codes crus a fites | **bug menor** | `planning/views.py:270` (`code`→`name`) |
| Retirar "Properes fites" del global | **localitzat** | `Dashboard.jsx:311-402,521-522` (Sprint 5/3 `b2aca22`) |
| Board "els meus" (backend) | **JA FET** | `by-model ?responsable=me` (`views_b.py:130-140`) |
| Toggle abast (frontend) | **GAP** | `Dashboard.jsx:99` (ModelBoard no passa `responsable`) |

---

### Annex — recomptes reals al tenant `fhort` (FET, consulta directa schema `fhort`)

| Entitat | Files |
|---|---|
| `TaskType` | 12 (totes actives) |
| `ModelTask` | 87 |
| `TaskTimeEstimate` | 458 *(consigna deia 513 → revisar)* |
| `GateEvent` | 9 |
| `Tasca` (catàleg ric) | **0** |
| `PaquetServei` / `PaquetServeiTasca` | 0 / 0 |


## 16. Post-jubilació del Kanban (Sprint 5/4 `fc98cab`): forats, solapament board↔Planning, separació tècnic/PM

> **READ-ONLY.** Brúixola: `DIAGNOSI_KANBAN_PLANIFICACIO.md §B` (3 acoblaments a desfer ABANS de
> jubilar). Ahir es va esborrar `pages/KanbanTasks.jsx` (ruta `/tasques/kanban` + menú). Aquesta
> secció constata QUÈ VA QUEDAR de les 3 peces acoblades i exposa el solapament board↔Planning i el
> substrat de gating per als dos dashboards per rol. Cada afirmació: **[FET]** = verificada a codi /
> endpoint viu; **[SUPÒSIT]** = inferència.

### 16.A Inventari de les 3 peces acoblades (§B) — reubicada / orfe / perduda

| Peça (§B) | Vivia a (Kanban, esborrat) | Estat ara | Evidència |
|---|---|---|---|
| **(a) UI de transició manual** | `KanbanTasks.jsx:604-739` (`TaskCard` + botons) | **REUBICADA** ✅ | `WorkPlan.jsx:86-145` (`TaskCard`+`TransportBtn`), transicions `:199-258` (`modelTasks.transition`), mapa `TRANSPORT :50-55`. Embegut a `ModelSheet → DashboardTab → WorkPlan`. |
| **(b) Cartes de gate (cua "llest per gate")** | `KanbanTasks.jsx:553-601` (`GateRow`) + `gates/ready` | **ORFE** 🔴 | endpoint **viu i gated**: `gate_ready_models_view` (`tasks/views_b.py:600-611`, `@_CloseGates`), routat (`tasks/urls.py:81`). Company `gates/bulk` (`views_b.py:579`, `@_CloseGates`, routat `:80`). **Consumidors frontend = CAP**: només els helpers `gates.ready`/`gates.bulk` (`endpoints.js:189-190`), sense cap `.jsx` que els cridi (grep net). `GateRow` es va esborrar amb el Kanban. |
| **(c) Ordenació "models actius a dalt"** | `KanbanTasks.jsx:226-229` (sort local) | **SUPERSEDED / no reproduïda** 🟡 | El board nou agrupa per `kanban_state` en 4 columnes (`Dashboard.jsx:15` `BOARD_COLS=[pending,open,paused,done]`); dins cada columna mana l'ordre per defecte del backend (`-in_progress,-pending,-paused,codi`, `views_b.py`). El sort explícit "actius primer en una sola llista" no es reprodueix; no és forat funcional, però l'afordança "veure la feina viva d'un cop d'ull" canvia de paradigma. |

**Matís sobre (b) — el que SÍ sobreviu:** la validació de gate **per-model individual** existeix fora
del Kanban: `ActionsMenu.jsx:170` (`runAdvance → modelsApi.gate(id,{to_phase})`), renderitzat a
`ModelSheet.jsx:569` (un model) i `Models.jsx:81` (bulk sobre selecció). Backend `gate_model_view`
(`views_b.py:531`, `@_CloseGates`). → El que s'ha perdut **no** és "poder validar un gate", sinó la
**cua sintètica agregada** "aquests N models tenen totes les tasques Done i estan llestos pel seu
gate" (`gates/ready`), que era l'eina de cop-d'ull del PM/manager i **només** vivia a la columna 1 del
Kanban. **Aquest és el forat crític de la jubilació d'ahir** (§B.2 deia *"Cal decidir on van ABANS de
jubilar"* — la decisió no es va prendre → orfe).

### 16.B Solapament board (Dashboard) ↔ Planning

| Dimensió | `ModelBoard` (Dashboard `/`, Sprint 5) | `Planning` (`/planificacio`) |
|---|---|---|
| Gating | **CAP** (qualsevol autenticat; `Dashboard.jsx:99` només usa token, no capabilities) | **PM** `canPlan = define_tasks \|\| configure` (`Planning.jsx:96`); sense → pantalla bloquejada (`:239-244`) |
| Granularitat | per **model**, 4 col per `kanban_state` | per **tècnic** (cua), + carpeta "Pendents" (models sense assignar) |
| Acció | **navegar** → `/models/:id` (read-only) | **assignar** (`TaskAssignWizard`), **reordenar** (DnD `plan.reorder`), **reassignar/desassignar** |
| Endpoint base comú | `by-model ?all=true` (`Dashboard.jsx` ModelBoard) | `by-model ?all=true` (`Planning.jsx:114`) + `model-task-items` + `users` |
| Risc/viabilitat | no | sí (semàfor `on_track/at_risk/critical`, `Planning.jsx:70-80`) |

- **El solapament és de SUBSTRAT, no de funció:** tots dos parteixen de `by-model`, però el board és
  **executiu/navegacional** (on és cada model, entra-hi) i Planning és **de govern** (qui fa què,
  reordena, assigna). No es trepitgen en acció; es trepitgen en "una graella de models per estat".
  **[FET]**
- **Frontera proposada (NO decisió — opcions):**
  - **Opció 1 — mantenir separats per rol:** board → dashboard **tècnic** (`/`, executiu, "els meus");
    Planning + cua + gates → dashboard **PM** (govern). És el que demana la clarificació d'Agus.
  - **Opció 2 — Planning absorbeix el board:** un sol "centre de models" amb modes (navegar/assignar)
    segons capability. Menys pantalles, però barreja executiu i govern en una.
  - **Recomanació feble [SUPÒSIT]:** Opció 1 encaixa amb la intenció de dos dashboards per rol i amb el
    gating ja existent; deixa el board `/` lleuger (tècnic) i concentra el govern a Planning/PM.

### 16.C Substrat de gating per separar tècnic ↔ PM — [FET]

`ROLE_CAPABILITIES` (`accounts/capabilities.py:21-25`); `me` exposa `rol_nom` + `capabilities[]` +
`profile_id` (`accounts/serializers.py:19-25`):

| Rol | execute_tasks | define_tasks | close_gates | view_team_tasks |
|---|:--:|:--:|:--:|:--:|
| `technician` | ✅ | — | — | — |
| `product_manager` | ✅ | ✅ | — | — |
| `manager` | ✅ | ✅ | ✅ | ✅ |
| `admin` | ✅ | ✅ | ✅ | ✅ |

- ⚠️ **Matís important [FET]:** `close_gates` i `view_team_tasks` NO els té `product_manager`, només
  `manager`/`admin`. El "PM" de la clarificació d'Agus (valida fases + veu la cua de tot l'equip) ≈
  rol **`manager`** al codi, no `product_manager`. Cal que Agus confirmi el mapatge rol↔intenció.
- **Endolls de gating disponibles avui:**
  - Cartes de gate → gatejar per **`close_gates`** (com feia el Kanban: `canCloseGates`,
    `KanbanTasks.jsx:67` esborrat). Endpoint ja `@_CloseGates`.
  - Cua/assignació (Planning) → ja gatejat **`define_tasks||configure`** (`Planning.jsx:96`).
  - Board "tots vs els meus" → **`view_team_tasks`** distingeix qui pot veure l'equip (default
    tècnic→meus, PM/manager→tots). El backend ja ho té; **el front no ho consulta** al board.
- **El Dashboard NO ramifica per rol avui [FET]:** `ModelBoard` és idèntic per a tothom (no llegeix
  `capabilities`). El **menú** sí ramifica: `/` (dashboard) visible a tots (`Sidebar.jsx:47`),
  `/planificacio` gated `cap:'plan'` (`:51`), `/planificacio/calendari` obert (`:52`).

### 16.D Gap del toggle "tots / els meus" — [FET] (amplia §15.E)

- Backend **llest**: `by-model ?responsable=me` deriva "els meus" = models on sóc assignee d'≥1
  ModelTask (`views_b.py:127-138`); `?responsable=<id>` per a un perfil concret.
- Frontend **GAP**: `ModelBoard.buildParams` (`Dashboard.jsx:121`) **no** passa `responsable`; no hi ha
  cap toggle. El Kanban esborrat **sí** el tenia (gated `view_team_tasks`: `fResponsable` me/tech,
  `KanbanTasks.jsx:309-345`) → **aquesta UI també es va perdre amb la jubilació** (no només el board no
  la va néixer; existia i es va esborrar).
- Nota d'abast implícit: per a un `technician`, `by-model` ja ve **row-level-scoped** a les seves
  tasques (sense `view_team_tasks`) → "els meus" és l'estat de facto; el toggle té sentit sobretot per
  `manager` (veu tot, vol focalitzar "els meus"). **[FET/SUPÒSIT]**

### 16.E Mapa: forat de la jubilació (urgent) vs construcció nova

**🔴 Forats oberts AHIR per la jubilació (regressió — recuperar UI existent, backend intacte):**
1. **Cua de gates `gates/ready` orfe** (§16.A.b) — *el crític*. Surface perduda; reubicar a dashboard
   PM/manager gated `close_gates`. (També `gates/bulk` sense surface.)
2. **Toggle "tots/els meus" perdut** (§16.D) — existia al Kanban gated `view_team_tasks`; reubicar al
   board del tècnic. Backend `responsable=me` ja hi és.

**🟡 Canvi de paradigma (no forat, decidir si recuperar):**
3. Ordenació "actius a dalt" (§16.A.c) — superseded per les columnes; recuperable amb un sort dins
   columna o un mode "llista".

**🟢 Construcció nova (no és forat; és l'arquitectura dels dos dashboards):**
4. Ramificar el Dashboard per rol (tècnic executiu vs PM govern) — avui el board és únic per a tothom.
5. Decidir frontera board↔Planning (§16.B, Opció 1/2).
6. Per-model "què haig de fer" i fites per-model (ja diagnosticat a §15.C/§15.F: gaps de
   `calendar/events ?model_id` i catàleg per fase).

**✅ Sense forat (cobert):** UI de transició manual (WorkPlan) i validació de gate **per-model**
(ActionsMenu) sobreviuen intactes; cap acoblament de **dades** trencat (§B.4: `transition_task`,
`by-model`, gates → compartits i vius).

---

## 17. Dashboard del rol `manager` (govern) + Calendari-Gantt — cartografia de substrat

> **READ-ONLY (data 2026-06-25).** Cap escriptura, migració, commit ni restart. Aquesta secció
> **NO dissenya layout** (és Patró C amb l'Agus): porta els **FETS** (cada peça contra codi real,
> `fitxer:línia`, FET vs SUPÒSIT) perquè es dissenyi damunt de codi viu. **Decisió d'Agus: són DOS
> dissenys separats** — (1) el **dashboard `manager`** (reuneix accions de govern ja disperses + n'hi
> afegeix de noves) i (2) el **calendari-Gantt** (entrada de menú pròpia, reconcepció). Brúixoles:
> aquest mateix document (§13–§16, cua per tècnic, scheduler, `TechnicianQueueOrder`, gates orfes) +
> `DIAGNOSI_KANBAN_PLANIFICACIO.md` + `DIAGNOSI_DASHBOARD_FONTS.md` (les 8 fonts).
> **[FET]** = re-grepat a mà pel documentador en aquesta sessió; **[report]** = report d'investigador
> no re-verificat camp a camp; **[SUPÒSIT]** = inferència de disseny.

### 17.0 Titular per a la decisió — `manager` ÉS el rol de govern, i ja en té TOT el gating

**El substrat de permisos ja diferencia govern d'execució i el rol `manager` posseeix tota la família
d'accions de govern.** `ROLE_CAPABILITIES` (`accounts/capabilities.py:21-26`, **[FET]**):

| Rol | execute_tasks | define_tasks | schedule_fittings | close_gates | view_team_tasks | manage_users |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `technician` | ✅ | — | — | — | — | — |
| `product_manager` | ✅ | ✅ | ✅ | — | — | — |
| `manager` | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> ⚠️ **Correcció a §16.C [FET]:** la taula de §16.C **ometia la columna `schedule_fittings`** i deia
> que el PM no la té. El codi viu mostra que **PM i manager tenen tots dos `schedule_fittings`**; la
> diferència real govern↔PM és **`close_gates` + `view_team_tasks`** (només `manager`/`admin`). →
> El "PM que valida fases i veu tot l'equip" de la clarificació d'Agus és **literalment el rol
> `manager`** al codi. Cada acció de govern de la Família 1 ja està gatejada amb una capability que
> `manager` posseeix → **el dashboard `manager` és la projecció UI d'un conjunt d'accions que el
> backend ja autoritza i serveix; gairebé res del backend de govern és nou.**

**Conseqüència de les dues separacions:**
- **Dashboard `manager` ↔ Planning:** solapament de **substrat** (`by-model`), no de funció (§16.B).
  Planning (`/planificacio`, gated `define_tasks||configure`) ja és la superfície de **cua per tècnic +
  assignar + reordenar**. El dashboard `manager` afegeix el que va quedar **orfe o sense casa**: la
  **cua de gates `gates/ready`** (§16.A.b, el forat crític), els **comptadors agregats**, els **avisos**
  i el **toggle tots/els meus** (§16.D).
- **Calendari-Gantt ↔ calendari actual:** el calendari viu (`PlanningCalendar.jsx`) és **unitat=TASCA,
  eix=hores**; el Gantt nou és **unitat=MODEL, eix=dies**. Comparteixen les 3 fonts de `calendar/events`
  però el Gantt **reconcep** la projecció (barra-per-model, no event-per-tasca).

---

### 17.1 FAMÍLIA 1 — ACCIONS de govern · **majoritàriament EXISTEIX, dispers**

| Acció de govern | Estat | Backend (endpoint · `fitxer:línia`) | Gating | Frontend avui | FET? |
|---|---|---|---|---|---|
| **Assignar tasques (bulk)** | EXISTEIX | `POST plan/assign-batch/` → `plan_service.assign_batch` (`planning/views.py:585`; servei `plan_service.py:231` [report]) | `define_tasks` | `TaskAssignWizard.jsx` (muntat a `Planning.jsx:323` i `ActionsMenu.jsx:216`) | FET (endpoint/ruta); steps [report] |
| **Assignar/reassignar individual** | EXISTEIX | `PATCH model-task-items/<pk>/` (`ModelTaskViewSet`, `tasks/views_b.py:46`) + `POST models/<id>/assign/` (`:343`), `unassign/` (`:364`) | `define_tasks` | reassignació a `Planning.jsx` [report] | FET |
| **Wizard d'entrada de models** | EXISTEIX (ja desacoblat) | `POST models/` (`ModelViewSet.create`, `models_app/views.py` [report]) | (cap; qualsevol autenticat) | `ModelWizard.jsx`, **ruta pròpia** `/models/nou` (creació) i `/models/:id/editar` (`App.jsx:132,136`) | FET (ruta/component) |
| **Taula models per dates/prioritats + reordenar** | EXISTEIX | `POST plan/reorder/` (`planning/views.py:494`) → `TechnicianQueueOrder` (§3.2) | `define_tasks` | `Planning.jsx` pestanya "Assignades" (DnD `@dnd-kit`, per tècnic) | FET (endpoint); §3.2 |
| **Enviar a producció** | EXISTEIX | `POST models/<id>/request-production/` (`request_production_view`, `tasks/views_b.py:686`) | `schedule_fittings` (`@_ScheduleFittings`, `:685`) | `ActionsMenu` acció `production` [report] | FET |
| **Informar arribada de proto/mostra** | EXISTEIX | `POST productions/<pk>/status/` (`production_status_view`, `tasks/views_b.py:721`) → `Production.delivered_at`/`status='Delivered'` | `schedule_fittings` (`@_ScheduleFittings`, `:720`) | via `ProductionTab`/ActionsMenu [report] | FET (endpoint); `Production` model `tasks/models.py:229` |
| **Assignar protos per revisió de mides** | PARCIAL (via obrir tasca) | `POST models/<id>/open-task/ {code}` (`open_model_task_view`, `tasks/views_b.py:468`) crea+arrenca la tasca de mesura | `execute_tasks` | obre `/models/:id/mesures?task_id=` (§15.A) | FET (endpoint); no hi ha "acció de govern" dedicada |
| **Convocar fitting de N models + convidar** | EXISTEIX | `POST fitting-sessions/schedule/` (individual) + `schedule-bulk/` (grup `convocatoria` UUID) (`fitting/views.py` [report]); assistents M2M `attendees` | `schedule_fittings` | `ActionsMenu` (`fitting`/`convene_fitting`) + `FittingSessionNew.jsx` [report] | FET (model `fitting/models.py:202`, `convocatoria`/`attendees`); endpoints [report] |
| **Convidar assistents (picker)** | EXISTEIX | `GET plan/eligible-attendees/` (`planning/views.py` [report]) — usuaris amb `schedule_fittings` | — | a ActionsMenu/FittingNew | report |
| **Validar/avançar gate (individual)** | EXISTEIX | `POST models/<id>/gate/` (`gate_model_view`, `tasks/views_b.py:531`) · `regress/` (`:557`) | `close_gates` (`@_CloseGates`, `:530,556`) | `ActionsMenu` advance/back (`ModelSheet.jsx`, `Models.jsx` bulk) | FET |
| **Validar gates en lot (post-reunió)** | EXISTEIX | `POST gates/bulk/` (`gate_bulk_view`, `tasks/views_b.py:579`) | `close_gates` (`@_CloseGates`, `:578`) | **CAP consumidor** (helper `gates.bulk` sol) | FET |
| **🔴 Cua "llest per gate"** | EXISTEIX backend · **ORFE UI** | `GET gates/ready/` (`gate_ready_models_view`, `tasks/views_b.py:601`) — models amb totes les tasques Done | `close_gates` (`@_CloseGates`, `:600`) | **CAP** (es va perdre amb el Kanban, §16.A.b) | FET |

**Síntesi F1 (REÚS vs CONSTRUCCIÓ):**
- **REÚS quasi total de backend.** Les 11 accions tenen endpoint viu i gatejat amb una capability que
  `manager` ja té. **Cap endpoint nou** per a la mecànica de govern.
- **CONSTRUCCIÓ = recol·lecció d'UI dispersa + recuperar orfes.** El dashboard `manager` és el lloc
  natural per a: (1) **`gates/ready`** (forat crític — surface perduda, gatejar `close_gates`); (2)
  **`gates/bulk`** (sense surface); (3) reunir `ActionsMenu` (assign/production/fitting/gate) en accions
  de massa des d'una taula de models seleccionables. El **wizard de models ja és desacoblat** (ruta
  pròpia `/models/nou`): "moure'l al dashboard" = només **una entrada de menú/botó**, cap moviment
  estructural. **[SUPÒSIT de disseny]**

---

### 17.2 FAMÍLIA 2 — VISUALITZACIÓ analítica · **substrat parcial, falta agregació**

**1) Temps estadístic PER FASE — [substrat per-tasca SÍ; per-fase NO empíric]**
- **Welford és per `(garment_type_item × task_type)`, NO per fase** (`TaskTimeEstimate`,
  `tasks/models.py:318-332`, `unique_together=[('garment_type_item','task_type')]`; motor
  `services_i.py:19-46`). **[FET]** → no hi ha cap cel·la empírica per fase.
- **Existeix substrat de SEED per fase:** `TimeSeed` (`tasks/models.py:362-380`) té
  `scope ∈ {'task','phase'}` i `key = TaskType.fase` quan `scope='phase'`. **[FET]** → temps **per
  defecte** per fase sí; temps **observat** per fase no.
- **`TaskType.fase`** (6 choices: Disseny / Dev. tècnic / Prototip / Mostres / Preproducció /
  Producció, `tasks/models.py:68-85`). **[FET]** → l'eix `task_type→fase` existeix per fer el rollup.
- **NOU:** endpoint d'**agregació `TaskTimeEstimate` agrupat per `task_type__fase`** (mitjana ponderada
  per `n`). Substrat de dades complet; **càlcul/endpoint nou** (~poques línies). **[SUPÒSIT]**

**2) "Tira horitzontal de fases" — [component visual EXISTEIX, sense l'eix temps]**
- **`PhaseStepper.jsx`** (`frontend/src/components/PhaseStepper.jsx:5-12`): pinta una **tira
  horitzontal de 8 fases** (`Nou·Disseny·Tècnic·Prototip·Mostres·Preproducció·Producció·Tancat`) amb
  done/active/future segons `faseActual`. **[FET]** ⚠️ El seu enum **NO coincideix** amb
  `Model.FASE_CHOICES` (Pending/Dev/Proto/SizeSet/PP/TOP, `models_app/models.py:94`) ni amb
  `TaskType.FASE_CHOICES` — és un eix de presentació propi. **És el llavor visual; li falta el temps
  estadístic per fase (punt 1).**
- **`GateEvent`** (`tasks/models.py:164-183`: `from_phase/to_phase/at/kind`) **[FET]** = font dels
  **deltas reals entre fites de fase** (durada viscuda per fase). Avui llegible via el timeline (punt
  següent).
- **NOU:** combinar `PhaseStepper` (seqüència) + delta `GateEvent` (temps real per fase) + agregat del
  punt 1 (temps estadístic). **[SUPÒSIT]**

**3) Navegació per criteris amb drill-down — [filtres parcials]**
- `ModelTaskViewSet.filterset_fields = ['model','status','task_type','assignee']`
  (`tasks/views_b.py:46`) **[FET]** → **treballador** (`assignee`) i **task_type** filtrables directe.
- `ProductionViewSet.filterset_fields = ['model','phase','status','supplier']` (`:681`) **[FET]**.
- **Model list** filtra `estat, fase_actual, garment_type, responsable, temporada, any`
  (`models_app/views.py:26` [report §13.3]). **[FET via §13.3]** → **fase** i **garment_type** sí.
- **`garment_type_item` (eix "item"):** **NO** és a cap `filterset` de tasques/models; sí a un viewset
  veí (`tasks/views_b.py:760` `['garment_type_item','task_type']`). **[FET]** → filtrar tasques per
  item és **NOU**.
- **Agregats existents:** `by-model` (counts per estat, `tasks/views_b.py:79`) i **`fase-counts`**
  (vegeu correcció sota). **[FET]** Stats per treballador/fase/garment_type com a tals → **NOUS**.

**4) "Quan estarà acabat un model" (predicció) — [ES CALCULA, S'EXPOSA i ES LLEGEIX]**
- `Model.predicted_start/predicted_end` (`models_app/models.py:228-229`). **[FET]**
- **S'ESCRIUEN:** l'scheduler agrega `min(planned_start)/max(planned_end)` de les tasques i desa
  `.date()` quan `save=True` (`scheduler_service.py:232-246`, `.update(predicted_start=..., predicted_end=...)`);
  es **netegen** a `unassign` (`plan_service.py:389`). Disparadors = `plan/compute`, `plan/apply`,
  assign/reorder (imperatius, §3.2). **[FET]**
- **S'EXPOSEN:** `ModelDetailSerializer` és `fields='__all__'` (`models_app/serializers.py:111`) →
  `predicted_*` surten al detall del model. **[FET]**
- **ES LLEGEIXEN al front:** `ModelSheet.jsx:659` (default de data) i **`:785`** (`calcViabilitat(...,
  model.predicted_end)` → semàfor de viabilitat vs `data_objectiu`). **[FET]**
- ⚠️ **Correcció a l'apèndix de `DIAGNOSI_KANBAN_PLANIFICACIO.md`** ("es desen però cap view els
  llegeix"): **desfasat** — avui s'exposen (`__all__`) i el frontend els llegeix per la viabilitat.
- **NOU:** exposar-los **agregats** (per fase/treballador/garment_type, o una llista "models i la seva
  data prevista de fi") — el càlcul ja és viu; només falta l'endpoint/vista analítica. **[SUPÒSIT]**

**Síntesi F2:** substrat **més madur del que semblava**. Vius: `PhaseStepper`, `GateEvent`, `by-model`,
`fase-counts`, `predicted_*` (calculats+exposats+llegits), `timeline` (merge, sota). Nous: **agregació
de temps per fase** (rollup `task_type→fase` sobre Welford), **stats per eix** (treballador/fase/item),
i el **filtre per `garment_type_item`**.

---

### 17.3 FAMÍLIA 3 — CALENDARI-GANTT · **reusa fonts, reconcep projecció**

**Calendari actual (`PlanningCalendar.jsx`) — [FET/report]:** agenda pròpia (dia/setmana/mes/llista),
**unitat=TASCA amb hores** (`HOUR_PX` [report]). Consumeix `GET calendar/events/`
(`calendar_events_view`, `planning/views.py:213`) que **unifica 3 fonts** [FET, re-verificat el bloc]:
- **tasca** — `ModelTask.planned_start/planned_end`, `en_risc` si `> data_objectiu` (`:236-282` [report]).
- **confecció** — `Production.expected_at` (`:283-321` [report]; `model_id` directe).
- **fitting** — `FittingSession.data` (+ `start_time`, `attendees`), amb **partició per `convocatoria`**
  (`planning/views.py:326-486`; sessions soltes `convocatoria=None` separades de les agrupades) i
  dependència tova `avis_abans_confeccio` (fitting < `expected_at` del mateix model+fase, `:349-356`). **[FET]**

**Bug G7 (replicació diària de convocatòria) — [no es reprodueix al codi viu]:** el bloc de fitting
**agrupa per `convocatoria`** i, quan no hi ha hora, emet **UN event multi-dia** que abasta
`primera.data → última.data` del grup (no un event per dia). **[FET, re-llegit el bloc + report]** →
en la generació actual de `calendar/events` **no hi ha replicació per dia**; G7 com a "una convocatòria
es replica cada dia" **no es manifesta aquí**. ⚠️ Anotat perquè el **Gantt nou (unitat=model)** derivaria
les fites de fitting **directament de `FittingSession.data` per model**, evitant del tot la lògica de
partició per `convocatoria` — el terreny on G7 vivia.

**Reconcepció (unitat=MODEL, eix=DIES) — què es reusa / què es reconcep:**

| Peça del Gantt nou | Substrat existent | Estat |
|---|---|---|
| Barra inici→fi del model | `Model.predicted_start/predicted_end` (calculats, §17.2 punt 4) | **REUSA** [FET] |
| (alternativa) min/max de tasques | `min(planned_start)/max(planned_end)` (ja és el que l'scheduler agrega) | REUSA [FET] |
| % completat per model | **EXISTEIX** front: `WorkPlan.jsx:176-178` (`done/total` de tasques). Maduresa **bàsica** (no pondera durada/risc) | **REUSA** [report] |
| Fita crítica "arribada proto" | `Production.expected_at` (FK `model`, `tasks/models.py:236`) | REUSA [FET] |
| Fita crítica "fitting" | `FittingSession.data` (FK `model`, `fitting/models.py:230`) | REUSA [FET] |
| **"Dies d'espera"** entre fases | **CAP noció de wait/espera al codi** | **NOU** [report, grep negatiu] |
| Filtre **per model** | `calendar/events` accepta **NOMÉS `start`/`end`**, no `model_id` (`planning/views.py:244` [report]) | **NOU** (afegir `?model_id`) |
| Filtre **per usuari** | implícit: sense `view_team_tasks`, el queryset ja queda scoped (`:241` [report]) | REUSA [FET via scope] |
| Vista Gantt (barres/dies) | el calendari actual és agenda d'hores | **NOU** (component) |

**Síntesi F3:** **reusa fonts i models** (predicted_*, expected_at, FittingSession.data, scope per
usuari); **reconcep la projecció** (event-per-tasca→barra-per-model, hores→dies) i hi afegeix **dies
d'espera** (cap substrat) i **filtre `?model_id`** a `calendar/events`.

---

### 17.4 FAMÍLIA 4 — AVISOS accionables · **NO existeix; cal construir-ho**

- **No hi ha sistema de notificacions/avisos derivats d'estat.** Grep ampli a `*/models.py`:
  cap `Notification`/`Alert` generalista. **[FET, grep]**
- **`Watchpoint`** (`models_app/models.py:807-832`): **TEXT LLIURE human-authored** (`text=TextField`,
  `created_by` FK UserProfile, cicle `open→resolved`). **≠ avís derivat d'estat.** **[FET]**
- **`POMAlert`** (`fitting/models.py:98` [DASHBOARD_FONTS F3]): alertes **automàtiques de fitting**
  (desviació de mesura) — **no generalitzable** a avisos d'estat de model. **[report]**
- **`ImportSession.avisos`** (`models_app/models.py:415`, `JSONField`): avisos **dins el procés
  d'import**, no de l'estat del model. **[FET]**
- **Substrat per DERIVAR avisos (els senyals d'estat existeixen, però ningú els converteix en avís):**
  - tasca→`Done` i "model acabat" = totes les `ModelTask` Done (ja ho calcula `gates/ready`,
    `tasks/views_b.py:601`). **[FET]**
  - `Production.delivered_at`/`status='Delivered'` (arribada proto, `tasks/models.py` Production). **[FET]**
  - `GateEvent` (gate passat, `tasks/models.py:164`). **[FET]**
  - `FittingSession.estat`. **[FET]**
  - **Únic signal de domini propi:** `model_consumption_started` (`tasks/signals.py:17`), per a
    meritació — **no** per a avisos. **[report]**
- **CONSTRUCCIÓ NOVA:** un derivador d'avisos (regla d'estat → avís accionable) + persistència
  (model nou o reús de `Watchpoint` amb `origen='derivat'`) + endpoint de llista per al `manager`. El
  **substrat de senyals hi és tot**; el que no hi ha és la **capa que els llegeix i n'emet avisos**.
  Alternativa de mínim radi: **derivar-los al vol** (read) des de `gates/ready` + `productions` +
  `fitting-sessions` sense persistir-los. **[SUPÒSIT]**

---

### 17.5 Fronteres (dashboard `manager` ↔ Planning ↔ calendari nou)

- **Dashboard `manager` ↔ Planning (`/planificacio`):** **NO es trepitgen en funció** (§16.B). Planning
  = **cua per tècnic + assignar + reordenar** (gated `define_tasks||configure`). El dashboard `manager`
  = **govern de cop d'ull**: recupera `gates/ready` (orfe), `gates/bulk` (sense surface), comptadors
  (`by-model` + `fase-counts`), avisos (F4) i el toggle `tots/els meus` (`view_team_tasks`, §16.D).
  Comparteixen el substrat `by-model`; la frontera neta és **acció** (Planning assigna/reordena; el
  dashboard navega/valida/convoca). **[FET + SUPÒSIT de frontera]**
- **Dashboard `manager` ↔ Calendari-Gantt:** entrades de menú **separades** (decisió Agus). El
  dashboard és **estat+accions+avisos** (instantània de govern); el Gantt és **temps** (barres-model
  per dies). Comparteixen `predicted_*` i les fites (`expected_at`, `FittingSession.data`) però són
  superfícies diferents. **[SUPÒSIT]**
- **Calendari-Gantt ↔ calendari actual (`PlanningCalendar`):** **conviuen**. L'actual (tasca/hores, per
  al tècnic) no es jubila; el Gantt (model/dies, per al govern) és **una projecció nova sobre les
  mateixes 3 fonts** + `?model_id` nou. **[FET de fonts + SUPÒSIT]**

---

### 17.6 Correccions FET a docs germans (re-verificades aquesta sessió)

1. **`fase-counts` EXISTEIX** (`models_app/views.py:92-126`, `@action url_path='fase-counts'`,
   `qs.values('fase_actual').annotate(n=Count('id'))`) → **§13.3 ("Comptadors per fase: NO existeix
   endpoint") queda corregit.** **[FET]**
2. **El merge de timeline JA ESTÀ CONSTRUÏT:** `model_timeline_view` (`models_app/views.py:1959`) fa el
   merge de `MeasurementChangeLog` + `GateEvent` + `TaskTransition` a `{at,kind,actor,payload}`, i
   `ModelTimeline.jsx` (`frontend/src/components/model/ModelTimeline.jsx`) el consumeix (`/models/<id>/timeline/`).
   → **DASHBOARD_FONTS ("el merge del timeline és construcció nova") queda desfasat: ja existeix.**
   ⚠️ Només passat; el "futur" (fites/sessions) hi és anotat com a forat, no implementat. **[FET]**
3. **`predicted_*` calculats + exposats + llegits** (§17.2 punt 4) → apèndix KANBAN desfasat. **[FET]**
4. **Deriva de `fitxer:línia` a `tasks/models.py`:** DASHBOARD_FONTS (2026-06-20) dóna línies **stale**
   per a aquest fitxer (p.ex. `GateEvent` deia `:256`, avui `:164`; `Production` avui `:229`;
   `TaskTransition` `:145`; `TaskTimeEstimate` `:318`). El fitxer s'ha reordenat. **Aquesta secció usa
   les línies VIVES re-grepades 2026-06-25.** **[FET]**
5. **§16.C ometia `schedule_fittings`** i el PM sí que la té (§17.0). **[FET]**
