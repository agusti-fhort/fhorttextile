# DIAGNOSI — Catàleg canònic · i18n · Comercial · Federació Brand↔Studio

**Data:** 2026-07-07 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
**Backend:** `backend/fhort/<app>/` (apps: accounts, backoffice, fitting, models_app, planning, pom, tasks, tenants)
**Mètode:** director-investigació + 7 investigadors-codi paral·lels (un per bloc) + síntesi. Cap escriptura de codi, cap migració, cap restart.
**Abast:** estat real abans de decidir/trossejar les 3 capes: (1) i18n de TaskType per `code`; (2) mòdul comercial Comanda→Línia→Encàrrec→ModelTasks; (3) federació Brand↔Studio.

> Convenció: `fitxer:línia` sempre relatiu a `backend/fhort/` tret que s'indiqui. "NO EXISTEIX" = confirmat absent al codi (no especulat).

---

## BLOC A — Catàleg canònic de tasques (post-seed)

### A1. TaskType — camps, seed, read-only
- **Model** `tasks/models.py:21-58`. Camps: `code = SlugField(50, unique=True)` (`:38`), `name = CharField(200)` (`:39`), `default_order` (`:40`), `active` (`:41`), `fase` (choices Disseny/Dev.tècnic/Prototip/Mostres/Preproducció/Producció, `:43`), `tipus` (Interna/Externa-lliure, `:44`), `eina` (`:45`), `mode` (`:48`), `facturable` (`:50`). Meta `ordering=['default_order','code']` (`:52`).
- **Seed canònic** `tasks/migrations/0025_seed_canonical_task_types.py` — llista `CATALEG` (`:8-23`), `update_or_create(code=...)` (`:29`), unseed noop (`:38-40`). **14 codes** (ordre·code): `5 design_review · 6 design_clarify · 10 pattern_digit · 20 pattern_cad · 30 pattern_hand · 40 pom · 45 size_check · 46 grading · 50 tech_sheet · 55 pattern_review · 70 bom · 81 scaling · 82 marking · 90 Audit`.
- **Read-only efectiu:** `TaskTypeViewSet(ReadOnlyModelViewSet)` `tasks/views_b.py:29` (docstring: POST/PUT/PATCH/DELETE → 405 fins i tot admin), `permission_classes=[IsAuthenticated]` (`:36`), router `task-types` `tasks/urls.py:14`. Cap registre d'admin per TaskType.

**Veredicte A1: llest.** 9 camps, 14 codes canònics, API efectivament read-only.

### A2. Codes inconsistents + punts amb literals
- **Allow-list `get_allowed_task_types`** `accounts/capabilities.py:57-71`: **data-driven, cap literal** (admin → `TaskType.filter(active=True).values_list('code')` `:68`; no-admin → `profile.permisos['tasks']` `:71`).
- **Scheduler/planning:** tot indirecte via `.task_type.code` / `default_order` (`planning/scheduler_service.py:57-58,150,188,220`; `planning/plan_service.py:213-214,256-257`; `planning/views.py:200,274,283,543,610,692`). Cap literal.
- **Literals hardcoded** (data-ops i residus): `tasks/management/commands/retype_scaling_to_grading.py:37-38` (`code='scaling'`/`'grading'`); `pom/management/commands/restructure_garment_types_v2.py:22-23` (`TASK_ORDER` amb scaling+grading); `models_app/management/commands/clone_model_for_qa.py:115,117` (`'size_check'`); `models_app/services_size_check.py:217,262` (`task_type__code='size_check'`); `models_app/views.py:654` (`code='pom'`); `models_app/views.py:1448` (`code='scaling'` dins el watchpoint de propagació de grading).
- **Inconsistències:** (a) `'Audit'` (`0025:22`) capitalitzat (trenca la convenció slug-minúscula dels altres 13) i **orfe** (cap consumidor referencia `audit`); (b) residu `code='scaling'` a `models_app/views.py:1448` després del retype scaling→grading (probablement hauria de ser `'grading'`); `grading` (order 46) i `scaling` (order 81) coexisteixen al seed.

**Veredicte A2: cal X.** Allow-list i scheduler nets. Resoldre: `'Audit'` (minúscula + orfe) i el literal `code='scaling'` a `views.py:1448`.

### A3. TascaGlobal (app pom)
- **Existeix** `pom/models.py:102` (`codi` unique, `nom_en/ca/es`, `fase`, `tipus`, `minuts_estandard`, `es_gate`, `resultat_gate_opcions` JSON, `facturable`, `ordre_base`, `activa`). Creada a `pom/migrations/0001_initial.py:64`.
- **Consumidors vius: cap** (grep només model + migracions). L'únic FK que hi apuntava, `Tasca.tasca_global`, es va eliminar a `tasks/migrations/0026_...py:29-32`, i el model `Tasca` sencer suprimit (`:38-41`).

**Veredicte A3: cal X (codi mort, esborrable).** Sense lectors ni FKs → segur d'eliminar amb `DeleteModel`.

---

## BLOC B — Radi i18n de `TaskType.name`

### B1. Consumidors de `.name`
**Backend (tots lectura a request-time, cap persistit):** `tasks/serializers_b.py:17` (`source='task_type.name'`); `tasks/views_b.py:913,1006`; `models_app/views.py:1980,1993,2105,2107,2240`. `planning/` i `pom/` només usen `.code` (no `.name`).

**Frontend — ja i18n per `code`** via helper `frontend/src/utils/taskType.js:5` (`t('tasktype.${code}', {defaultValue: name||code})`): `TaskTree.jsx:154`, `WorkPlan.jsx:126,213`, `ModelTimeline.jsx:95`.

**Frontend — `.name` cru (NO passa pel helper i18n, ~11 punts):** `planning/TimeTree.jsx:92,171,284`; `pages/UsersRoles.jsx:184,254,287,464,673`; `TaskAssignWizard.jsx:230`; `pages/RegistreActivitat.jsx:139`. `frontend-backoffice/src`: **NO EXISTEIX** cap consumidor.

### B2. Persistència del name
**NO EXISTEIX** cap persistència de `TaskType.name`. Verificat i descartat: els únics `_snapshot` (`models_app/models.py:750-751` a `ConsumptionRecord`) desen el **Model** (`codi_intern`/`nom_prenda`, escrits a `tasks/services_c.py:107-108`), no el task type; `PlanSnapshot.result` (`tasks/models.py:312`, desat a `plan_service.py:96`) indexa per `.code`, mai `.name`; `ModelTask` només té snapshot `estimated_minutes`. Cap JSON/log/albarà/PDF copia el name.

**Veredicte B: llest (canvi segur).** Traduir per `code` NO trenca històrics (el name mai es persisteix). Únic pendent: encaminar ~11 render-sites de frontend (UsersRoles, TaskAssignWizard, RegistreActivitat, TimeTree) pel helper `taskTypeLabel` perquè es tradueixin.

---

## BLOC C — Identitat canònica cross-tenant

### C1. GarmentTypeItem (57 items)
- **Model a l'app `tasks`** (no pom): `tasks/models.py:213`. **Code estable: `code = SlugField(60)`** (`:219`) amb `unique_together=[('garment_type','code')]` (`:254`) → estable **per família**, NO globalment únic (FK a `pom.GarmentType` tenant-local). Camps: `garment_type` (FK CASCADE `:217`), `code`, `name`, `complexity_order`, `active`, `base_size_definition` (FK SET_NULL `:233`), `grading_rule_set` (FK PROTECT `:246`).
- **Seed dels 57:** `pom/management/commands/restructure_garment_types_v2.py` — taula `ITEMS` (`:88-162`), `update_or_create` (`:234-237`); també sembra 513=57×9 `TaskTimeEstimate` (`:245-249`). **fhort-ESPECÍFIC:** `TENANT='fhort'` (`:19`), `with schema_context(TENANT)` (`:205`). Comanda manual one-off, no lligada a cap hook.

**Veredicte C1: cal X.** Code estable existeix (per família), però el seed és manual i cablejat a `fhort`, no genèric.

### C2. GarmentType (17 famílies)
- **Tenant-local** `pom/models.py:372`: `codi_client = CharField(60)` (`:380`, **NO unique**) + FK `garment_type_global` → `GarmentTypeGlobal` (`:373-379`, SET_NULL). **Id canònic estable = `GarmentTypeGlobal.codi = CharField(80, unique=True)`** `pom/models.py:80` (catàleg public/shared, flag `is_system` `:87`).
- **Seed:** mateixa comanda `restructure_garment_types_v2.py` — `FAMILIES` (`:33-85`), `GarmentTypeGlobal` a public (`:197-202`), rèplica a tenant (`:205-213`), 17 `GarmentType` tenant per `codi_client` (`:216-224`). **fhort-ESPECÍFIC** (mateixa evidència).

**Veredicte C2: cal X.** Ancoratge canònic sòlid (`GarmentTypeGlobal.codi`, public+unique); seed manual fhort-específic.

### C3. Creació de tenants + hooks d'onboarding
- **Model** `Client(TenantMixin)` `tenants/models.py:58`, `auto_create_schema=True` (`:171`). Únic camí de creació: `ClientViewSet.create` `backoffice/views_tenants.py:56-79` → `serializer.save()` dispara `migrate_schemas` + `Domain.objects.create` (`:69`).
- **Hook d'onboarding que sembri el catàleg de garments: NO EXISTEIX.** Cap `post_schema_sync`/`schema_migrated`, cap comanda `bootstrap`/`onboard`/`seed_tenant`.
- **Únic seed automàtic per tenant nou** (via data-migrations TENANT_APPS a `auto_create_schema`): `tasks/migrations/0025_seed_canonical_task_types.py` (14 TaskType, GENÈRIC) i `tasks/migrations/0020_seed_self_customer.py` (self-customer). **Cap** migració sembra GarmentType/Global/Item.
- Seeds manuals necessaris i **no genèrics**: `restructure_garment_types_v2.py` (cablejat `fhort`); `pom/.../reseed_tenant_fhort.py` OBSOLET (aborta amb `CommandError` `:84-87`, path Excel cablejat).

**Veredicte C3: cal X (forat d'onboarding).** Un tenant nou rep TaskTypes + self-customer automàticament, però **NO** el catàleg de 17 famílies/57 items; l'única comanda existent està cablejada a `fhort`. Cal una comanda `seed_tenant` genèrica (parametritzada per schema) per a la federació.

---

## BLOC D — Motor de temps (Welford + cascada)

### D1. TaskTimeEstimate + Welford
- **Model** `tasks/models.py:276-294`: `garment_type_item` (FK), `task_type` (FK), `estimated_minutes` (PositiveInt null — seed), `n` (PositiveInt default 0), `mean_minutes` (Decimal 10,2), **`m2` (Decimal 16,4 — suma de quadrats Welford)** (`:286`). `unique_together=[('garment_type_item','task_type')]` (`:289`). **Welford COMPLET** (mean + n + M2), no només mean+n.
- **`record_actual_time`** `tasks/services_i.py:18-46`; update incremental (`:34-42`): `delta=x-mean; new_mean=mean+delta/n; delta2=x-new_mean; new_m2=m2+delta*delta2`. `select_for_update` (`:31`), `@transaction.atomic` + try/except no-fatal (`:44-46`), skip si no item o `x<=0`. Constant `WELFORD_MIN_SAMPLES=5` (`:10`). **`m2` s'acumula però cap lloc el llegeix** (variància encara no consumida). Cridat des de `tasks/services_c.py:128-129` (gate Done).

**Veredicte D1: llest.** Estructura Welford completa; `m2` acumulat però inert (oportunitat: intervals de confiança futurs).

### D2. Lectura d'estimats + None + cascada
- **`effective_minutes(cell)`** `tasks/services_i.py:49-58`: empíric si `n>=5 and mean>0`, si no el seed, si no **None**.
- **`lookup_estimated_minutes(model, task_type)`** `tasks/services_g.py:11-46` — **choke-point de la cascada**, 4 graons: (1) cel·la pròpia item×task (`:19-27`); (2) empíric global viu `Avg('mean_minutes')` sobre cel·les madures del task_type (`:31-35`); (3) `TimeSeed` tenant (`scope='task'` per code, si no `scope='phase'` per fase) (`:39-43`); (4) **`return None`** (`:45-46`, etiquetat "captura-PM: None — sprint posterior" = el forat deliberat).
- **Snapshot** a `ModelTask.estimated_minutes` en crear (`tasks/views_b.py:312-315`, `planning/plan_service.py:296-298`), pot ser None.
- **Forat de planificació:** el scheduler **salta** tasques sense estimació amb avís (`planning/scheduler_service.py:215-217`); reposicionar-les **llança ValueError** (`plan_service.py:120-121`); assign-batch amb data sense estimació → avís, va a cua desbloquejada (`plan_service.py:312-315`).
- **Punts d'endoll de la cascada:** primari `services_g.py:45-46` (el `return None` reservat "captura-PM"); graó tenant-default ja existent `services_g.py:39-43` (TimeSeed); terminal `effective_minutes` `services_i.py:58`.

**Veredicte D2: cal X (forat conegut i reservat).** El punt d'endoll de la cascada tenant→global ja està marcat (`services_g.py:45-46`); None es propaga i el scheduler el salta amb avís.

### D3. Recompute de la cua
- **Motor únic** `recompute_for_technicians(profile_ids)` `planning/plan_service.py:48-74`: per cada tècnic re-resol la durada de cada tasca mòbil via la cascada viva (`fresh=lookup_estimated_minutes(...)`, `:65-73`) i re-executa `schedule()` (`scheduler_service.py:117-254`).
- **Call-sites:** `assign_model` (`:225`), `assign_batch` (`:349-350`), `unassign_model` (`:390`), reorder endpoint `planning/views.py:534`; `apply`/`preview`/`compute` criden `schedule` directe (`plan_service.py:185/152/111`). Endpoints: `plan/reorder|assign-batch|compute|preview|apply` (`planning/views.py:505,596,97,113,132`).

**Veredicte D3: llest.** Convergència única a `recompute_for_technicians`; la re-resolució en replanificar ja re-consulta la cascada per tasca.

---

## BLOC E — Restes comercials/facturació

### E1. Estat per peça (schema · consumidors · escriptura)
| Entitat | Existeix | Schema | Fitxer | Escriptura |
|---|---|---|---|---|
| **Plan** | Sí | PUBLIC | `tenants/models.py:12` (preu_mensual, feature_flags JSON, `models_inclosos`, `preu_model_extra` 10,4, `moneda_pla`) | `PlanViewSet` `backoffice/urls.py:7,13`. Motor de billing **ignora** `Plan.preu_model_extra` a favor de ContractLine (`backoffice/models.py:106-107`) |
| **ContractLine** | Sí | PUBLIC | `backoffice/models.py:124` (FK contract+service, `preu`, `inclosos`, `unique_together(contract,service)`) | només niat a `TenantContractCreateSerializer.create` `serializers_contracts.py:49` (ADMIN) |
| **Invoice** (+InvoiceLine `:186`) | Sí | PUBLIC | `backoffice/models.py:147` (client FK, period, estat, total, UniqueConstraint auto) | `generate_invoice()` `billing_service.py:110,115` via `POST facturacio/generar/` |
| **ModelConsumptionEvent** | Sí | PUBLIC | `backoffice/models.py:63` (`codi_client`, `period`, `opaque_ref` UUID unique, `merited_at`) | sense HTTP: signal receiver `backoffice/receivers.py:11`, disparat des de `tasks/services_c.py:112` (task InProgress) |
| **consumption_started_at** | Sí (camp) | TENANT | `models_app/models.py:204` a `Model` | set-once `tasks/services_c.py:101-102` (1r task start); twin `ConsumptionRecord` `models_app/models.py:743` (OneToOne, `opaque_ref`) |
| **ServiceCatalog** | Sí | **PUBLIC (shared)** | `backoffice/models.py:80` (`code` unique, `tipus` tier_fee/model_count/manual, sense preu) | `ServiceCatalogViewSet` CRUD ADMIN `serveis/` `backoffice/urls.py:14` |

### E2. Suppliers + catàleg de clients + ancoratge del vincle
- **Supplier** `tasks/models.py:144` — **TENANT**, esquelètic (`name`, `type` workshop/factory, `active`); CRUD `SupplierViewSet` `tasks/views_b.py:622`; FK `Production.supplier` (`:195`). **Sense col·lisió** amb un futur catàleg backoffice de suppliers.
- **Catàleg de CLIENTS a nivell tenant: SÍ existeix** — `Customer` `tasks/models.py:161` (TENANT): `codi` (CharField 3, unique — prefix del codi_intern), `nom`, `active`, `is_self` (tenant com a propi client), **`codi_global` (CharField 3, null — hook reservat explícit per a la permeabilitat cross-tenant, sense lògica avui, `:172-174`)**, `logo`. CRUD `CustomerViewSet` `tasks/views_b.py:643`.
- **django-tenants** `Client(TenantMixin)` `tenants/models.py:58` (PUBLIC): `codi_tenant` (CharField 3, unique `:120`), `tipologia` estudi/marca (`:110`).
- **Ancoratge del vincle Brand↔Studio:** costat **public** = `Client.codi_tenant` + `Client.tipologia`; costat **tenant** = `Customer.codi` + el reservat **`Customer.codi_global`**. El self-customer (`is_self=True`, `codi=Client.codi_tenant`) ja pont eja els dos espais (`tasks/services_c.py:114`).

**Veredicte E: llest per endollar (sense col·lisió).** El món de facturació (Plan/ContractLine/Invoice/ServiceCatalog/ModelConsumptionEvent) viu **complet a PUBLIC**; el consum es merita des de la transició de tasca tenant. El hook cross-tenant ja té ancoratges reservats (`Customer.codi_global`, `Client.codi_tenant`).

---

## BLOC F — Punt d'inserció del flux comercial

### F1. Wizard d'entrada de model
- **Endpoint** `models/create-wizard/` `models_app/urls.py:188` → `create_model_wizard` `models_app/views.py:304` (escriu directe amb `Model.objects.create`, **sense serializer d'escriptura**). Segon camí: `models/create-from-sheet/` (`urls.py:124`).
- **Camps capturats** (`views.py:309-319` + `_resolve_garment_def` `:257-300`): year, season, `codi_client`, `customer`, nom_prenda, descripcio, collection, data_objectiu, multi-piece; derivats codi_intern/sequencial/estat; garment-def: `garment_type_item_id` (+ derivats garment_type/group), `size_system_id`, `grading_rule_set_id`, target, construction, size_run, base_size.
- **`garment_type_item` obligatori? NO** — `models_app/models.py:161-167` (`SET_NULL, null=True, blank=True`); el wizard el posa només `if d.get('garment_type_item_id')` (`views.py:266`).
- **On aniria el FK a línia de comanda:** al costat dels FKs de contracte existents `models_app/models.py:231-244` (`contracte` `:231`, `linia_contracte` `:238`, tots SET_NULL). L'stub `LiniaContracte` és a `models_app/models.py:29`. **No hi ha model `encarrec`/order avui.**

**Veredicte F1: llest (punt d'inserció clar).** `garment_type_item` NO és obligatori (⚠️ risc per al mòdul comercial que hi vulgui recolzar); el FK de comanda encaixa amb els FKs de contracte a `models.py:231-244`.

### F2. Creació de ModelTask + idempotència
- **4 punts de creació:** `define_model_tasks_view` `tasks/views_b.py:313`; open-task "porta-menú" `tasks/views_b.py:504`; assign-batch `planning/plan_service.py:297`; clone QA `clone_model_for_qa.py:118`. A més `ModelTaskViewSet` `views_b.py:41` (gate DEFINE_TASKS).
- **Comproven existència? SÍ, tots** (idempotents per `(model, task_type)`): `views_b.py:301-302,310-311` (docstring "Idempotència suau" `:292`); `views_b.py:499-506`; `plan_service.py:288-298`; `get_or_create` clone. **Backstop DB:** `unique_together=[('model','task_type')]` `tasks/models.py:97` ("Defensa de fons contra curses" `:95-96`).
- **Comentari deute duplicació ModelTask: NO EXISTEIX** (només la docstring d'idempotència + el comentari del constraint).

**Veredicte F2: llest.** Creació idempotent als 4 punts + constraint DB. El "deute anotat" de duplicació **no existeix** al codi.

### F3. ModelTask — camps i FK encàrrec
- **Camps** `tasks/models.py:61-100` (14): `model` (FK CASCADE), `task_type` (FK PROTECT), `status`, `origen` (prevista/ad_hoc), `assignee` (FK SET_NULL), `order`, `started_at`, `finished_at`, `estimated_minutes`, `planned_start/end`, `planned_locked`, `created_at`, `updated_at`. Reverse FKs: `TimerEntrada.model_task`, `TaskTransition.model_task`, `Watchpoint.task`.
- **Meta** `:91-97`: `ordering=['model','order']`, **`unique_together=[('model','task_type')]`**, **cap `indexes`**.
- **FK `encarrec` nul·lable sense col·lisió? SÍ** — ortogonal a `unique_together`, cap índex explícit; `AddField` additiu nul·lable, sense backfill.

**Veredicte F3: llest.** Un `encarrec = FK(null=True, blank=True, SET_NULL)` encaixa net (només `AddField`).

---

## BLOC G — Federació (viabilitat)

### G1. `transition_task` — acoblament estat/timer/Welford
- `tasks/services_c.py:46-131` `@transaction.atomic`. **Estat+timer = una unitat atòmica** (tanca timer d'altres tasques `:63`, obre `TimerEntrada` `:69`, tanca en sortir `:77`). **Welford desacoblat i no-fatal** (només a Done `:125-129`, `record_actual_time` amb try/except propi). **Atòmica niada per billing/meritació** (`:99`) amb try/except que no re-llança (`:119-123`).
- **Dependència del Model:** flip `fase_actual Pending→Dev` via queryset (`:95`, sense signals); billing llegeix `model.customer.codi` (`:104,114`) + snapshots text (`:107-108`); Welford llegeix `model.garment_type_item_id` (`services_i.py:25`). **Cap lectura de POM, cap materialització.**

**Veredicte G1: llest per a tasca local.** Una transició local només necessita `fase_actual` (i, si es manté billing, `customer.codi`/`garment_type_item_id`). L'acoblament a `customer` és l'únic a neutralitzar per a un model `origen=EXTERN`.

### G2. Què arrossega crear un Model
- `models_app/signals.py`: (1) `generate_model_code` pre_save (seq+codi_intern; **skippable** pre-fixant `codi_intern`); (2) **`sync_size_fitting` post_save → auto-crea `SizeFitting`** tret que `responsable_id=None` (**skippable**); (3) `recompute_import_watchpoint` (només `.update`, no crea); (4) `update_last_activity`.
- `tasks/signals.py:1-12`: els receivers que derivaven `fase_actual`/materialitzaven tasques **es van treure**. **Cap signal crea ModelTasks.** POMs només via `materialize_poms_view` `models_app/views.py:527-601` (explícit); tasques només via `define_model_tasks_view`.

**Veredicte G2: llest (opció Model local origen=EXTERN viable).** Crear un Model NO materialitza POMs ni tasques; només cal suprimir el seed de `SizeFitting` (`responsable=None` o guard `origen`).

### G3. Maduresa del model + pintat del recurs al Gantt
- **Maduresa** = `model_ready_for_gate(model_id)` `tasks/services_d.py:11-17`: True ssi tots els `ModelTask` són Done i n'hi ha ≥1. Gate `advance_phase_gate` (`:24-51`); endpoints `gate_ready_models_view` `views_b.py:605`, `gate_model_view` `:535`. (Maduresa de *temps* Welford és a part: `views_b.py:785`.)
- **Gantt pinta el tècnic** des de `ModelTask.assignee → UserProfile`: `nom_complet`, `color_avatar` (`planning/views.py:266-268,219`); events fitting/producció amb color fix i `tecnic_id=None` (`:289-291,314`). `calendar_events_view` `:214`, `gantt_view` (`planning/urls.py:30`), elegibles `plan_eligible_technicians_view` `:542`.

**Veredicte G3: llest.** Maduresa = "tots els ModelTask Done" (local, sense dependència de camps del Model). Un futur recurs EXTERNAL_STUDIO encaixa com a assignee sintètic (nom+color), sense més acoblament.

### G4. Handoffs i Watchpoints
- **Handoff: NO EXISTEIX** cap model.
- **Watchpoint** `models_app/models.py:840-870` (`model` FK, `task` FK SET_NULL, `text`, `dades` JSON, `estat` open/resolved, created/resolved). Creació: `bulk_import_service.py:476`, `models_app/views.py:1450`. Cicle: `WatchpointViewSet` `models_app/views.py:151-182` (create/resolve/reopen).

**Veredicte G4: cal X (només Watchpoint).** Handoffs no existeixen com a entitat; el Watchpoint (model-anchored, open→resolved, amb REST lifecycle) és el candidat net a federar com a event de bus, però el FK `task` (SET_NULL) caldria convertir-lo en referència opaca cross-tenant.

### G5. ModelFitxer + save_model_file
- **Servei únic** `models_app/services_fitxers.py:36-86` `@transaction.atomic` (docstring: "l'únic lloc que toca la invariant de cadena"). Versionat = cadena linked-list `versio_anterior` + un sol `is_current=True` (`:54-61,82-84`); checksum sha256, mida, mimetype; `get_version_chain` `:89-109`.
- **Binari físic:** `ModelFitxer.fitxer = FileField(upload_to='model_fitxers/%Y/%m/')` `models_app/models.py:388`; `MEDIA_ROOT=BASE_DIR/'media'` `settings.py:159-160`. **⚠️ NO hi ha storage per-tenant** (cap `TenantFileSystemStorage`/`DEFAULT_FILE_STORAGE` custom) → els binaris **comparteixen namespace de disc** entre tenants; només la fila DB és per-schema.

**Veredicte G5: llest (com a servei) amb caveat.** `save_model_file` és l'únic write-point (candidat a DeliverableRegistry). Caveat de federació: el media path **no** està aïllat per schema.

### G6. schema_context creuat + middleware de Host
- **Middleware:** `django_tenants.middleware.main.TenantMainMiddleware` `settings.py:84` (CORS al davant); resolució Host→schema per Domain (`TENANT_MODEL='tenants.Client'`, `TENANT_DOMAIN_MODEL='tenants.Domain'`). Cap middleware custom.
- **Cross-schema en request-path: NO EXISTEIX.** Tot `schema_context` runtime és `'public'` (SHARED, `backoffice/receivers.py:10`) o el **propi** schema del request (`pom/s9_views.py:119`). La iteració entre schemas de tenant només viu en **comandes offline** (`reconcile_consumption.py:59`, seeders).

**Veredicte G6: cal X (greenfield).** Host-resolution és django-tenants estàndard; **no hi ha cap primitiva de lectura cross-tenant** a reutilitzar. `public`/SHARED és l'única superfície compartida avui → la federació és terreny nou.

---

## Taula final de riscos detectats

| # | Bloc | Risc | Evidència | Severitat |
|---|---|---|---|---|
| R1 | A2 | `code='scaling'` residual al watchpoint de propagació (post retype→grading) | `models_app/views.py:1448` | Mitjà (lògica silenciosament errònia) |
| R2 | A2 | `'Audit'` capitalitzat + orfe (trenca convenció slug; cap consumidor) | `0025_seed:22` | Baix (cosmètic/neteja) |
| R3 | A3 | `TascaGlobal` codi mort amb taula viva a la DB | `pom/models.py:102` | Baix (confusió; esborrable) |
| R4 | B1 | ~11 render-sites de frontend mostren `.name` cru (no traduït) | `UsersRoles/TimeTree/TaskAssignWizard/RegistreActivitat` | Baix (i18n incompleta, no trenca res) |
| R5 | C3 | **Forat d'onboarding:** cap seed genèric de 17 famílies/57 items per a tenant nou; l'única comanda és cablejada a `fhort` | `restructure_garment_types_v2.py:19`; NO EXISTEIX hook | **Alt** (bloqueja federació multi-tenant real) |
| R6 | C1/C2 | Identitat de garment estable només **per família** (item) / via global (family); cap FK global a l'item | `tasks/models.py:254`; `pom/models.py:80` | Mitjà (cal política de codi canònic cross-tenant) |
| R7 | D2 | Tasques sense estimació: scheduler les **salta** (silenciós) i reposicionar-les **peta** (ValueError) | `scheduler_service.py:215`; `plan_service.py:120` | Mitjà (forat de planificació, ja reservat el punt de cascada) |
| R8 | F1 | `garment_type_item` **no obligatori** al wizard — el mòdul comercial que hi depengui pot rebre models sense item | `models_app/models.py:161`; `views.py:266` | Mitjà (integritat comercial) |
| R9 | G5 | Media **no aïllat per schema** (path pla compartit entre tenants) | `models_app/models.py:388`; `settings.py:159` | **Alt** (fuita/col·lisió de binaris en federació/DeliverableRegistry) |
| R10 | G6 | Cap primitiva de lectura cross-tenant; federació és greenfield sobre `public` | `settings.py:84`; runtime `schema_context` només public/propi | **Alt** (esforç d'arquitectura, no un fix) |
| R11 | G1/G2 | Acoblament de `transition_task`/creació de Model a `customer`/`SizeFitting` per a un model `origen=EXTERN` | `services_c.py:104,114`; `signals.py sync_size_fitting` | Mitjà (neutralitzable amb guard `origen`) |
| R12 | G4 | Handoffs no existeixen; Watchpoint té FK `task` local (a opacar per federar) | NO EXISTEIX Handoff; `models_app/models.py:848` | Mitjà (disseny d'events de bus) |

---

## Síntesi de veredictes (semàfor)

- **Capa 1 (i18n per code):** ✅ **llest** — name mai persistit (B2), helper ja existent; només encaminar ~11 render-sites (R4).
- **Capa 2 (comercial):** 🟡 **cal X petit** — món de billing complet a PUBLIC (E), ModelTask idempotent + FK `encarrec` encaixa net (F2/F3), punt d'inserció clar (F1); resoldre `garment_type_item` opcional (R8) i decidir el model `Encarrec`/`Comanda` (no existeix avui).
- **Capa 3 (federació Brand↔Studio):** 🔴 **greenfield amb bloquejadors** — ancoratges reservats existeixen (`Customer.codi_global`, `Client.codi_tenant`), model `origen=EXTERN` viable (G2), Gantt/maduresa desacoblats (G3); però **forat d'onboarding** (R5), **media no aïllat** (R9) i **cap primitiva cross-tenant** (R10) són prerequisits d'arquitectura.

*Diagnosi PATRÓ A — 7 investigadors paral·lels + síntesi Opus 4.8. Cap escriptura de codi. Fi.*
