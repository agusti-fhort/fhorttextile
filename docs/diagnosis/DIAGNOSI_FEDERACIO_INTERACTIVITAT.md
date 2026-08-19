# DIAGNOSI — Federació v2 · interactivitat Brand ⇄ Studio sobre el MATEIX model

**Data:** 2026-07-27 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
(HEAD `52b5974`).

**Abast.** Cens exhaustiu de les superfícies d'estat que pengen d'un `models_app.Model`, la
seva classificació en tres calaixos (identitat/config federada · local-per-actor ·
veritat-compartida) i el cens del transport existent. **NO conté cap recomanació**: la
decisió d'arquitectura de la interactivitat és Patró C.

**Convenció.** Tota afirmació sobre el codi porta `fitxer:línia` relativa a
`backend/fhort/`. **"NO EXISTEIX" = confirmat absent al codi**, verificat per grep exhaustiu,
mai especulat. Les propostes van marcades `💡 PROPOSTA (a validar)` i estan confinades al
BLOC 5.

**Fronteres respectades.** No es toca ni es proposa canviar G1 (motor `resolve`), G6, billing
ni el motor de patrons. Lleis aplicades al raonament: *«materialització prèvia, mai lectura
ORM en viu»* · *«meritació per actor»* · *«cap dada es destrueix en aturar/revocar el token»*.

---

## Resum executiu

1. **El traspàs mou 14 dels 59 camps del `Model` i CAP fila de cap altra taula.**
   `instancia_al_studio` (`tenants/federation_service.py:163-178`) escriu exactament
   `codi_intern · customer · codi_tenant · any · temporada · sequencial · origen ·
   nom_prenda · fit_type · base_size_label · size_run_model · garment_type_item ·
   size_system · grading_rule_set`. Els altres **45 camps del Model** i les **26 famílies
   d'estat que hi pengen** neixen a zero al Studio. El docstring ho declara com a llei:
   *«L'EXTERN NEIX AMB IDENTITAT I CONFIGURACIÓ, MAI AMB FEINA»*
   (`tenants/federation_service.py:112-113`).

2. **No existeix cap mecanisme de transport ni de sincronia més enllà de `traspassa`.**
   Verificat: els únics `schema_context()` fora de commands i tests són
   `tenants/federation_service.py:76,125,244` (el traspàs), `backoffice/receivers.py:14`
   (meritació→`public`), `backoffice/invoice_pdf.py:50` (dades de l'emissor) i
   `tenants/discovery_service.py:35` (login únic). **NO EXISTEIX** cap camí de retorn
   Studio→Brand, cap `sync`, cap re-lectura, cap event bus. `tenants/management/commands/`
   només conté `assign_models_to_studio.py`, `instantiate_external_models.py` i
   `seed_tenant_link.py`.

3. **Avui, si els dos treballen, hi ha DUES peces amb el mateix nom i cap relació.** El
   `codi_intern` és `unique=True` **per schema** (`models_app/models.py:129`), de manera que
   la mateixa cadena existeix com a dues files independents amb pks diferents. La idempotència
   del traspàs i l'`estat_local` de la safata es calculen comparant aquest string
   (`tenants/federation_service.py:134,245-247`) — **és l'únic lligam que hi ha entre les dues
   files, i és de només-lectura.**

4. **La hipòtesi del calaix B es confirma per a temps/tasques/Welford/meritació, però amb un
   matís.** `ModelTask`/`TaskTransition`/`TimerEntrada`/`TaskTimeEstimate` són intra-schema i
   no col·lideixen. La meritació **ja té l'actor resolt a nivell d'event**
   (`ModelConsumptionEvent.actor_schema`, `backoffice/models.py:93`, escrit a
   `tasks/services_c.py:181` → `backoffice/receivers.py:21`), però la **guarda d'unicitat**
   (`Model.consumption_started_at`, `tasks/services_c.py:162-164`, i `ConsumptionRecord` que
   és `OneToOneField`, `models_app/models.py:864`) és **per-schema**: dos actors meriten dues
   vegades la mateixa peça, cadascú un cop. Això és consistent amb la llei "meritació per
   actor" — **es documenta com a FET, no com a defecte**.

5. **La hipòtesi del calaix C es confirma i és més ampla del que el brief anticipava.** A més
   de mesures, fitxes, fittings, grading, fase i watchpoints, hi entren: `SizeCheck`,
   `POMAlert`, els 45 camps no-federats del `Model` (inclosos `garment_type`, `target`,
   `construction`, els `fabric_*`/`shrinkage_*`, `design_freeze_*` i `measurements_version`),
   el `POMPlacement` (que **no penja del Model sinó del CATÀLEG**, i per això divergeix per una
   via diferent) i tota la superfície `patterns` (motor de patrons, fora de frontera per a
   canvis però dins del cens).

6. **`POMPlacement` és el cas anòmal del cens i cal aïllar-lo.** No penja del `Model` sinó
   d'`ItemFitxer` → `GarmentTypeItem` (`models_app/models.py:1076-1077`), és a dir del
   **catàleg del tenant**. Dos tenants no comparteixen catàleg (`GarmentTypeItem` viu a
   `tasks`, app de tenant), i el traspàs resol `garment_type_item` **per clau natural**
   (`tenants/federation_service.py:141-148`), no per identitat. Conseqüència: el precedent de
   col·locació de cotes del Brand **no és visible ni derivable** des del Studio, encara que
   tots dos apuntin a un GTI amb el mateix `code`.

7. **El TenantLink governa el PONT, no la feina, i això ja és llei escrita i implementada.**
   `tenants/models.py:326-329`; `revocar()`/`aturar()` no toquen cap dada
   (`tenants/models.py:406-431`), i `es_viu()` només es consulta per **deixar passar el
   traspàs** (`tenants/federation_service.py:50`) i per **poblar la safata**
   (`tenants/federation_service.py:227`). Cap escriptura de feina consulta el vincle.

---

## BLOC 1 — Cens exhaustiu de superfícies d'estat penjades del Model

Convenció de la taula: **àncora** = com arriba al Model. **escriptors** = els punts que
insereixen/muten la fila (endpoints, serveis i signals; s'exclouen management commands de
sembra/QA i tests, marcats a part quan són rellevants).

### 1.1 Mesures i el seu log

| Superfície | Definició | Àncora | Escriptors (`fitxer:línia`) | Endpoint |
|---|---|---|---|---|
| `BaseMeasurement` | `models_app/models.py:568` | FK `model` (`:582`), unique `(model,pom)` (`:619`) | `models_app/views.py:1105,1115` (`materialize_poms_view`, `:986`) · `models_app/views.py:1402` (`set_measurements_view`, `:1373`) · `models_app/views.py:1528` (`gravar_pom_view`, `:1439`) · `models_app/views.py:1641` (reorder, `:1625`) · `models_app/views.py:1907` (`measurements_chat_view`, `:1821`) · `models_app/views.py:2375` (`_write_base`, `:2372`) · `models_app/extraction_views.py:2253` (`import_session_confirmar_view`, `:1833`) · `models_app/tech_sheet_views.py:364` · `models_app/services_size_check.py:179` (`resolve_size_check`, `:98`) · `fitting/services.py:369` (`consolidate_base_from_fitting`, `:345`) · `pom/wizard_views.py:205` (`save_base_size_view`, `:155`) · `BaseMeasurementViewSet` (`models_app/views.py:491`) | `POST models/<id>/materialitzar-poms/` (`urls.py:206`) · `POST models/<id>/set-measurements/` (`:211`) · `POST models/<id>/gravar-pom/` (`:208`) · `POST models/<id>/reorder-measurements/` (`:212`) · `POST models/<id>/xat-mesures/` (`:215`) · `POST import-sessions/<token>/confirmar/` (`:92`) |
| `MeasurementChangeLog` | `models_app/models.py:626` | FK `model` (`:637`) | **signal** `log_measurement_change` (`models_app/signals.py:263,295`) · `models_app/views.py:2197` (`set_size_override_view`, `:2120`) · `models_app/views.py:2343` (`escalat_ajustar_talla_view`, `:2244`) | — (derivat) |
| `SizeCheck` / `SizeCheckLine` | `models_app/models.py:887,923` | FK `model` (`:897`) | `models_app/services_size_check.py:70` (`open_size_check`) · resolució a `:98-179` · `SizeCheckViewSet` (`models_app/views_size_check.py`) | router `size-checks` (`urls.py:40`) |

**Llei d'escriptura vigent.** `BaseMeasurement` és estat **mutable amb l'últim escriptor
guanyant**: `update_or_create` a `models_app/views.py:1402` i `extraction_views.py:2253`,
`get_or_create`+assignació a `fitting/services.py:369` i `models_app/views.py:2375`. L'única
memòria del que hi havia abans és el log append-only (`models_app/models.py:667-674`:
`save()` prohibeix UPDATE, `delete()` prohibeix DELETE). **No hi ha ni versió, ni lock, ni
comparació d'estat previ**: qui escriu l'últim mana, i el log ho registra.

### 1.2 Fitxers, fitxa tècnica `.ftt` i catàleg

| Superfície | Definició | Àncora | Escriptors | Endpoint |
|---|---|---|---|---|
| `ModelFitxer` (inclou `.ftt` TECHSHEET i PDF EXPORT) | `models_app/models.py:354` | FK `model` (`:394`) | **únic escriptor de la invariant `is_current`/`versio`**: `models_app/services_fitxers.py:90` (`save_model_file`, `ModelFitxer(...)` a `:114`). Callers: `models_app/views.py:381,1684` · `models_app/services_ftt_document.py:445,487,504` · `models_app/extraction_views.py:2478` | `POST models/<id>/fitxers/` i el cicle `.ftt` (`models_app/ftt_document_views.py`) |
| `FttDocumentLock` | `models_app/ftt_models.py:11` | `document_root` = arrel de la cadena `versio_anterior` | `models_app/services_ftt_document.py:44` (`acquire_lock`), `:63-71` (`release_lock`) | cicle de l'editor `.ftt` |
| `DocumentTemplate` | `models_app/ftt_models.py:38` | tenant (no per-model) | `models_app/master_template.py:65` | — |
| `TechSheetTemplate` | `models_app/tech_sheet_models.py:13` | per `Customer` | `models_app/tech_sheet_editor_views.py:26` | editor de plantilla |
| `ItemFitxer` (catàleg) | `models_app/models.py:485` | FK `garment_type_item` — **NO al Model** | `models_app/services_fitxers.py:139` (`save_item_file`) | `models_app/item_fitxer_views.py` |

**Observació de forma.** El lock `.ftt` és **per-schema i per-cadena-de-versions**
(`document_root`, `models_app/services_ftt_document.py:28-33`). Dues cadenes en dos schemas
són dos documents lògics diferents amb dos locks independents: **el lock no protegeix res
cross-schema**, ni pretén fer-ho.

### 1.3 Fittings i grading materialitzat

| Superfície | Definició | Àncora | Escriptors |
|---|---|---|---|
| `SizeFitting` | `fitting/models.py:7` | FK `model` (`:23`), unique `(model,numero)` (`:56`), `codi` unique per schema (`:25`) | **signal** `sync_size_fitting` (`models_app/signals.py:131`, en crear el Model) · `pom/services.py:455` (`get_or_create_size_fitting`) · `pom/services.py:320,505` (updates d'estat) · `models_app/views.py:1983` · `models_app/extraction_views.py:2424` · `models_app/bulk_import_service.py:536-540` |
| `GradingVersion` | `fitting/models.py:62` | FK `size_fitting` (`:63`) | `pom/services.py:798` (`_get_or_create_grading_version`) · `pom/services.py:849,853` (`bump_grading_version_and_generate`) |
| `GradedSpec` | `fitting/models.py:181` | FK `grading_version` (`:190`) | `pom/services.py:1022` (`_upsert_graded_spec`) — sortida de `generate_graded_specs` |
| `FittingSession` | `fitting/models.py:220` | FK `model` (`:240`, XOR amb `garment_set`) | `fitting/services.py:173` (`schedule_session`) |
| `PieceFitting` / `PieceFittingLine` | `fitting/models.py:309,355` | FK `model` (`:321`) | `fitting/services.py:322` (`create_piece_fitting`) |
| `FittingPhoto` | `fitting/models.py:380` | FK `session` | pujada de fotos de sessió |
| `POMAlert` | `fitting/models.py:116` | FK `model` (`:129`) | `pom/s10_views.py:133` · `pom/s11_views.py:187` |
| `FittingDurationStat` | `fitting/models.py:405` | **singleton de tenant** (`pk=1`) | servei de tancament de sessió |
| `ModelGradingRule` | `models_app/models.py:717` | FK `model` (`:740`), unique `(model,pom)` (`:773`) | `models_app/services.py:185,199` (`materialize_model_grading_rules`) · `:213,225` (`..._from_specs`) · `models_app/views.py:1567` (`gravar_pom_view`) · `models_app/views.py:3465` (`set_pom_regim_view`, `:3420`) |
| `ModelGradingOverride` | `models_app/models.py:677` | FK `model` (`:692`), unique `(model,pom,size_label)` (`:710`) | `models_app/views.py:2184` (`set_size_override_view`) · `:2020,2326` (deletes) · `:2337` · `models_app/extraction_views.py:2386` |

**Invariant rellevant.** `GradingVersion` té **una sola activa per `SizeFitting` garantida per
BD** (`fitting/models.py:105-109`). És una invariant **intra-schema**: dos schemas poden tenir
cadascun la seva versió activa amb valors diferents, i la constraint no ho veu ni ho pot veure.

### 1.4 Fase, gates, watchpoints i timeline

| Superfície | Definició | Àncora | Escriptors |
|---|---|---|---|
| `Model.fase_actual` | `models_app/models.py:223` | camp del Model | `tasks/services_d.py:37,41` (`advance_phase_gate`) · `:65-66` (`regress_phase`) · `tasks/services_c.py:155` (primera tasca `Pending`→`Dev`) · `fitting/services.py:730-774` (tancament de sessió) |
| `GateEvent` | `tasks/models.py:140` | FK `model` (`:144`) | `tasks/services_d.py:42,67` |
| `Watchpoint` | `models_app/models.py:957` | FK `model` (`:963`) | `WatchpointViewSet` (`models_app/views.py:456`, `perform_create` `:465`, `resolve` `:468`, `reopen` `:479`) · `models_app/views.py:2052` (`generate_grading_view`) · `models_app/bulk_import_service.py:546-551` · `models_app/extraction_views.py:2400,2450` · **signal** `refresh_import_watchpoint` (`models_app/signals.py:145-173`, recalcula el WP d'import viu a cada save del Model) |
| Timeline | — (**no és una taula**) | — | `models_app/views.py:2782` (`model_timeline_view`) — **merge de LECTURA** de `MeasurementChangeLog` + `GateEvent` + `TaskTransition` (`:2785-2790`); **cap escriptura** (`:2791`) |
| `Model.design_freeze_at/by` | `models_app/models.py:309-315` | camps del Model | `pom/wizard_views.py:37-41` (`approve_design_freeze_view`, `:20`) |
| `Model.measurements_version` | `models_app/models.py:305` | camp del Model | `pom/services.py:857-859` (`F('measurements_version')+1` dins `bump_grading_version_and_generate`) |
| `Model.darrera_activitat` | `models_app/models.py:300` | camp del Model | **signal** `update_last_activity` (`models_app/signals.py:192`, a cada save) |

### 1.5 Tasques, temps, Welford i planificació

| Superfície | Definició | Àncora | Escriptors |
|---|---|---|---|
| `ModelTask` | `tasks/models.py:61` | FK `model` (`:70`) | `tasks/views_b.py:288,348,545` · `planning/plan_service.py:323` |
| `TaskTransition` | `tasks/models.py:121` | FK `model_task` (`:124`) | `tasks/services_c.py:39` (`_log`), via `transition_task` (`:96`) |
| `TimerEntrada` | `tasks/models.py:4` | FK `model_task` (`:5`) | `tasks/services_c.py:23` (`_open_timer`), tancament a `_close_open_timer` |
| `TaskTimeEstimate` (Welford `n`/`mean_minutes`/`m2`) | `tasks/models.py:359-369` | `(garment_type_item, task_type)` — **NO al Model** | `tasks/views_b.py:1168` |
| `TimeSeed` | `tasks/models.py:408` | tenant (`scope`,`key`) | `tasks/views_b.py:1196` |
| `ModelTask.planned_start/end/locked` | `tasks/models.py:82-87` | camps de la tasca | `tasks/services_scheduling.py:33-35` · `planning/scheduler_service.py:245-246` · `tasks/views_b.py:309` (reset) |
| `Model.predicted_start/end` | `models_app/models.py:249-250` | camps del Model | `planning/scheduler_service.py:236-250` |
| `PlanSnapshot` | `tasks/models.py:380` | tenant (campanya) | `planning/plan_service.py:100` |
| `TechnicianQueueOrder` | `planning/models.py:72` | FK `(profile, model)` (`:80-83`) | endpoint de reorder (`planning/views.py:136`) |
| `Model.reanchored_by_start` | `models_app/models.py:255` | camp del Model | auto-start / reorder |
| `Model.slots_*` (4 camps) | `models_app/models.py:283-286` | camps del Model | — |
| `Production` | `tasks/models.py:270` | FK `model` (`:276`) | `tasks/services_e.py:25` · `fitting/views.py:276` |

### 1.6 Meritació i comercial

| Superfície | Definició | Àncora | Escriptors |
|---|---|---|---|
| `Model.consumption_started_at` | `models_app/models.py:225` | camp del Model | `tasks/services_c.py:162-164` (`UPDATE ... WHERE consumption_started_at IS NULL` — **la guarda d'unicitat de la meritació**) |
| `ConsumptionRecord` | `models_app/models.py:860` | **`OneToOneField` `model`** (`:864`) | `tasks/services_c.py:167` · `backoffice/management/commands/reconcile_consumption.py:141` |
| `ModelConsumptionEvent` | `backoffice/models.py:79` — **viu a `public`** | ref fluixa `codi_client` + `opaque_ref` + `actor_schema` (`:84-93`) | `backoffice/receivers.py:15` (dins `schema_context('public')`, `:14`) |
| `QuoteLineModelIntent` | `commerce/models.py:284` | FK `model` (`:299`) | mòdul comercial |
| `WorkOrder` | `commerce/models.py:482` | FK `model` (`:514`) | `tasks/services_c.py:194` (`assign_work_order`) |
| `DeliveryNoteLine.model` | `commerce/models.py:764` | FK `model` | `commerce/services.py:799` |
| `AIUsage` | `models_app/models.py:999` | FK `model` (`:1025`) | `models_app/extraction_utils.py:175` |
| `ImportSession` | `models_app/models.py:525` | FK `model` (`:545`) | pipeline d'import (`models_app/extraction_views.py`) |

### 1.7 Cotes sobre sketch (POMPlacement) — el cas anòmal

`POMPlacement` (`models_app/models.py:1054`) **no penja del Model**: penja d'`ItemFitxer`
(`:1076-1077`, `on_delete=CASCADE`) i, per tant, de `GarmentTypeItem` — el **catàleg del
tenant**. Únic escriptor: `models_app/pom_placement_views.py:129` (`_desar_precedent`, `:96`),
endpoint `POST /api/v1/item-fitxers/<item_id>/pom-placements/` (`models_app/urls.py:201`), gate
CONFIGURE.

El vincle amb el model és **de lectura i indirecte**: el `GET` accepta `model_id` per resoldre
`bm_id` i materialitzar la cota viva (`models_app/pom_placement_views.py:12-17`), i el document
`.ftt` arriba al precedent a través de `ModelFitxer.derivat_de_item`
(`models_app/models.py:421-427`) / de l'etiqueta `sourceItemFitxer` de l'objecte sketch
(`models_app/pom_placement_views.py:3-7`). **Frontera G1 declarada al codi**: cap camí escriu
res al POM ni a `BaseMeasurement` (`models_app/pom_placement_views.py:20`).

### 1.8 Motor de patrons (cens; zona intocable per a canvis)

`patterns/models.py`: `PatternFile` (`:33`, FK `model` a `:42`, XOR amb `garment_type_item`),
i penjant-ne `PatternPiece` (`:150`), `PatternPoint` (`:195`), `PatternSegment` (`:242`),
`PatternPOM` (`:303`), `ExportAcknowledgement` (`:370`). Ancorats **directament al Model**:
`SewRelation` (`:427`, FK `:447`), `SewProposalRejection` (`:494`, FK `:517`),
`DartProposalRejection` (`:551`, FK `:566`), `SewToleranceAcceptance` (`:701`, FK `:728`,
append-only via `_AppendOnlyQuerySet` `:693`). `SegmentPreference` (`:603`) és **de tenant**
(preferència apresa del taller), no per-model.

### Veredicte BLOC 1: **llest**
26 famílies d'estat censades amb escriptor identificat. Cap superfície trobada té escriptor
cross-schema fora de `federation_service` i `backoffice/receivers`.

---

## BLOC 2 — Classificació en els tres calaixos

### Calaix A — IDENTITAT/CONFIG (ja viatja per `federation_service.traspassa`)

Verificat **camp a camp** contra `tenants/federation_service.py:87-104` (lectura al Brand) i
`:163-178` (escriptura al Studio). **Sentit: Brand → Studio, únic, una sola vegada per
`codi_intern`.**

| Camp escrit al Studio | Origen al Brand | Com viatja |
|---|---|---|
| `codi_intern` | `m.codi_intern` | literal — **clau natural i d'idempotència** (`:134`) |
| `customer` | — | **NO viatja**: es resol al Studio com `Customer.objects.filter(codi=brand_codi)` (`:126`); si no existeix → `FederacioError('customer_missing')` (`:128-130`) |
| `codi_tenant` | — | `= customer.codi` al Studio (`:166`), no el del Brand |
| `any`, `temporada`, `sequencial` | literals (`:92-94`) | literals |
| `origen` | — | forçat a `Model.ORIGEN_EXTERN` (`:170`) |
| `nom_prenda` | literal (`:91`) | literal |
| `fit_type` | literal (`:95`) | literal amb default `'Regular'` (`:172`) |
| `base_size_label`, `size_run_model` | literals (`:96-97`) | literals |
| `garment_type_item` | `gti.code` + `gti.garment_type.codi_client` (`:99-101`) | **clau natural**: `GarmentType.codi_client` → `GarmentTypeItem.code` (`:141-148`); no-aparellat → `NULL` + informe |
| `size_system` | `m.size_system.codi` (`:102`) | **clau natural** `SizeSystem.codi` (`:152`); no-aparellat → `NULL` + informe |
| `grading_rule_set` | `m.grading_rule_set.nom` (`:103`) | **clau natural** `GradingRuleSet.nom` (`:158`); no-aparellat → `NULL` + informe |

**Els no-aparellats NO bloquegen** (`tenants/federation_service.py:38-39,138`): el model neix
amb el camp a `NULL` i l'informe ho declara a `unmatched`.

**El traspàs dispara els signals del Studio** — és explícit i deliberat
(`tenants/federation_service.py:115-116`, `Model.objects.create()` i no `bulk_create`): al
Studio neixen `SizeFitting` buida (`models_app/signals.py:131`) i s'omple `darrera_activitat`
(`:192`).

### Calaix B — LOCAL-PER-ACTOR (viu al schema de qui executa; no col·lideix)

Hipòtesi del brief **confirmada** per a:

- `ModelTask` (`tasks/models.py:61`) — la constraint d'unicitat és `(model, task_type)` amb
  `origen='prevista'` (`:110-114`): **per-schema**, i els dos `model_id` són diferents files
  de schemas diferents.
- `TaskTransition` (`tasks/models.py:121`), `TimerEntrada` (`:4`) — pengen de la `ModelTask`
  local.
- `TaskTimeEstimate` amb el Welford `n`/`mean_minutes`/`m2` (`tasks/models.py:367-369`) —
  ancorat a `(garment_type_item, task_type)`, **catàleg del tenant**, mai al Model. Precedent
  de llei ja escrit: `bootstrap_tenant` copia `estimated_minutes` però **deixa el Welford a
  zero** perquè *«són història d'ús del tenant origen»*
  (`tasks/management/commands/bootstrap_tenant.py:29-31`).
- `TimeSeed` (`tasks/models.py:408`), `FittingDurationStat` (`fitting/models.py:405`),
  `SegmentPreference` (`patterns/models.py:603`), `PlanSnapshot` (`tasks/models.py:380`),
  `TechnicianQueueOrder` (`planning/models.py:72`) — tots de tenant o de tècnic.
- `AIUsage` (`models_app/models.py:999`), `ImportSession` (`:525`) — cost i pipeline de qui
  executa.
- `ModelTask.planned_start/end/locked` (`tasks/models.py:82-87`) — la planificació és de la
  cua de tècnics de cada casa.
- Mòdul comercial: `WorkOrder` (`commerce/models.py:482`), `DeliveryNoteLine`
  (`commerce/models.py:725`), `QuoteLineModelIntent` (`:284`) — l'encàrrec és de qui el cobra.

**Meritació — confirmada com a B, amb un fet que cal registrar.** La llei "meritació per actor"
**ja té suport a l'event**: `ModelConsumptionEvent.actor_schema` (`backoffice/models.py:88-93`)
s'omple amb `connection.schema_name` de qui obre la tasca (`tasks/services_c.py:181` →
`backoffice/receivers.py:21`). Ara bé, **la guarda d'unicitat és per-schema**:
`Model.consumption_started_at` (`tasks/services_c.py:162-164`) i `ConsumptionRecord`, que és
`OneToOneField(model)` (`models_app/models.py:864`). **Conseqüència literal:** si el Brand i el
Studio obren cadascun la primera tasca sobre la seva pròpia fila, es creen **dos
`ConsumptionRecord`** (un per schema) amb **dos `opaque_ref` diferents**, i per tant **dos
`ModelConsumptionEvent` a `public`** amb `actor_schema` diferent. `codi_client` també diferirà:
al Studio és `brand_codi` (`tenants/federation_service.py:126,166`); al Brand és el `codi` del
seu propi `Customer`. Això és exactament el que la llei "meritació per actor" descriu — **dues
cases treballant meriten dues vegades** — i es documenta com a FET verificat, no com a
anomalia. Nota: `ModelConsumptionEvent.exclos` (`backoffice/models.py:103`) ja existeix com a
capacitat d'exclusió, sense decisió associada.

**⚠️ Frontera B/C.** `Model.consumption_started_at` és **camp del Model**: pertany al calaix B
per semàntica (és per-actor) però **viu a la mateixa fila** que camps del calaix C. Qualsevol
partició per-superfície haurà de partir el `Model` **camp a camp**, no taula a taula.

### Calaix C — VERITAT-COMPARTIDA (els dos hi escriurien, cadascú al seu schema)

| # | Superfície | Per què és C |
|---|---|---|
| C1 | `BaseMeasurement` + `MeasurementChangeLog` | la mesura base és **de la peça**, no de qui la pren |
| C2 | `ModelGradingRule` + `ModelGradingOverride` | graduació resident, unique `(model,pom[,size])` |
| C3 | `SizeFitting` + `GradingVersion` + `GradedSpec` | el grading materialitzat de la peça |
| C4 | `FittingSession` + `PieceFitting` + `PieceFittingLine` + `FittingPhoto` | el veredicte del fitting és de la peça |
| C5 | `SizeCheck` + `SizeCheckLine` | validació del proto a talla base |
| C6 | `POMAlert` | desviacions detectades sobre la peça |
| C7 | `Model.fase_actual` + `GateEvent` | **la fase és de la peça, no de la casa** |
| C8 | `Watchpoint` | advertència que *«viatja amb el MODEL a través dels gates»* (`models_app/models.py:958`) |
| C9 | `ModelFitxer` (`.ftt`, patrons, sketches, exports) + `FttDocumentLock` | la fitxa tècnica és el document de la peça |
| C10 | Els **45 camps no-federats** del `Model` | vegeu 3.10 |
| C11 | `Model.measurements_version` + `Model.design_freeze_at/by` | comptadors i segells de la peça |
| C12 | `POMPlacement` | precedent geomètric de la cota; **divergeix per la via del catàleg**, no del Model |
| C13 | `patterns.*` (PatternFile i tota la seva descendència, SewRelation, acceptacions) | el patró és de la peça (**zona intocable per a canvis**) |
| C14 | `Production` | la confecció encarregada sobre la peça |

### Veredicte BLOC 2: **llest**
A = 14 camps · B = 13 famílies · C = 14 famílies. Cap superfície ha quedat sense calaix.
Una frontera detectada (`consumption_started_at`): el `Model` **no és particionable com a
taula**, només camp a camp.

---

## BLOC 3 — Calaix C, superfície per superfície

Per a cadascuna: **qui hi escriu avui i per on** · **quina llei la governa** · **què passaria
literalment si Brand i Studio hi escriuen** · **quin transport hi ha** (la resposta a l'última
és **cap** a totes; es repeteix perquè cada fila del cens ho ha de dir per si mateixa).

### C1 · `BaseMeasurement` + `MeasurementChangeLog`

**Qui hi escriu.** 12 punts d'escriptura censats a §1.1, entre ells 6 endpoints HTTP
(`materialitzar-poms`, `set-measurements`, `gravar-pom`, `reorder-measurements`,
`xat-mesures`, `import-sessions/<token>/confirmar`), el fitting
(`fitting/services.py:369`), el size check (`models_app/services_size_check.py:179`) i el
wizard (`pom/wizard_views.py:205`).

**Llei vigent.** **L'última mesura escrita és la veritat**, confirmat al codi: la clau és
`unique_together (model, pom)` (`models_app/models.py:619`) i tots els camins fan
`update_or_create`/`get_or_create`+assignació. No hi ha versió, ni lock, ni comparació d'estat
previ. La memòria del canvi és **append-only** al log (`models_app/models.py:667-674`), amb el
`context` derivat de l'`origen` (`models_app/signals.py:200-206`) i la traça opcional
`_fitting_ref`/`_motiu`/`_fora_de_tolerancia` (`:291-293`).

**Què passaria.** Dues taules de mesures completes i independents per a la mateixa peça. El
Brand escriu `PIT = 52,0`; el Studio escriu `PIT = 51,4` — **cap dels dos veu l'altre, cap dels
dos rep cap error, i els dos logs diuen la veritat sobre el seu propi schema**. La fitxa que
generi cadascú serà internament coherent i mútuament contradictòria. El log **no és
reconciliable a posteriori** sense un identificador comú: la `pk` de `BaseMeasurement` difereix
entre schemas i el log hi apunta per FK (`models_app/models.py:639-642`).

**Transport avui.** **CAP.** `BaseMeasurement` no apareix ni a `llegeix_models_del_brand`
(`tenants/federation_service.py:87-104`) ni a `instancia_al_studio` (`:163-178`).

### C2 · `ModelGradingRule` + `ModelGradingOverride`

**Qui hi escriu.** `models_app/services.py:185,199,213,225` (materialització des de regles o
des de specs), `models_app/views.py:1567` (`gravar-pom`), `:3465`
(`models/<id>/pom/<pom_id>/regim/`, `urls.py:223`). Overrides: `models_app/views.py:2184`
(`set_size_override_view`), `:2020` i `:2326` (deletes), `models_app/extraction_views.py:2386`.

**Llei vigent.** Unicitat `(model, pom)` (`models_app/models.py:773`) i
`(model, pom, size_label)` (`:710`). L'override **té prioritat sobre les regles** al motor
(`models_app/models.py:690`). La regla és **resident al model** precisament perquè no filtri a
altres models via plantilla compartida (`models_app/models.py:684-689`).

**Què passaria.** Dues graduacions residents per a la mateixa peça. Com que la regla resident
és el que el motor consumeix, **les dues cases generarien taules de talles diferents a partir
de la mateixa base**, encara que la base coincidís.

**Transport avui.** **CAP.** El que sí viatja és el **punter** `grading_rule_set`
(`tenants/federation_service.py:158`, per `nom`) — la plantilla externa, no la regla resident.

### C3 · `SizeFitting` + `GradingVersion` + `GradedSpec`

**Qui hi escriu.** `SizeFitting` neix sol al Studio en crear el model EXTERN (signal
`sync_size_fitting`, `models_app/signals.py:131`, disparat deliberadament pel traspàs,
`tenants/federation_service.py:115-116`). `GradingVersion`: `pom/services.py:798,849,853`.
`GradedSpec`: `pom/services.py:1022`, sortida de `generate_graded_specs` (`pom/services.py:166`).

**Llei vigent.** **Una sola `GradingVersion` activa per `SizeFitting`, imposada per BD**
(`fitting/models.py:105-109`) — perquè *«dues superfícies llegissin talles diferents del
mateix model»* és exactament el bug que G6/T1 va tancar (`fitting/models.py:99-100`). El
segell de producció (`aprovada`) **no** és únic: l'historial d'aprovades és legítim (`:102-104`).
`bump_grading_version_and_generate` desactiva totes les actives abans de crear la v+1
(`pom/services.py:846-855`) i incrementa `measurements_version` **abans** de propagar
(`:856-860`).

**Què passaria.** La constraint és intra-schema. **Cada casa tindria la seva pròpia v-activa
amb `GradedSpec` propis** i la BD diria que tot és correcte als dos costats. La invariant que
G6 va posar per evitar dues veritats de talles **no cobreix aquest cas**: està escrita a
nivell de `SizeFitting`, i n'hi hauria dos.

**Transport avui.** **CAP.**

### C4 · `FittingSession` + `PieceFitting` + `PieceFittingLine` + `FittingPhoto`

**Qui hi escriu.** `fitting/services.py:173` (`schedule_session`), `:322`
(`create_piece_fitting`), i el tancament a `fitting/services.py:730-774` — que **també escriu
`Model.fase_actual`** i segella la `GradingVersion`.

**Llei vigent.** `FittingSession` és XOR `garment_set`/`model` per CheckConstraint
(`fitting/models.py:294-301`). `PieceFitting` és unique `(session, model)` (`:349`) i porta el
seu propi gate (`:311-336`). El tancament d'un `PieceFitting` **consolida la base**
(`fitting/services.py:345-369` → C1) i pot **promoure override** a talla no-base
(`models_app/models.py:690`).

**Què passaria.** Dues sessions de fitting sobre la mateixa peça física, amb gates
independents. Com que el tancament escriu C1 i C7, **la divergència del fitting arrossega la
de mesures i la de fase**: és el node del calaix C amb més radi d'efecte.

**Transport avui.** **CAP.**

### C5 · `SizeCheck` + `SizeCheckLine`

**Qui hi escriu.** `models_app/services_size_check.py:70` (`open_size_check`) i `:98-179`
(`resolve_size_check`), via `SizeCheckViewSet` (`models_app/urls.py:40`).

**Llei vigent.** Historial repetible **sense** `unique_together` (`models_app/models.py:888-889`):
un model acumula N checks. En resoldre's amb `decisio='tolerancia_acceptada'`, el `valor_real`
**es propaga a la base** amb `origen='CHECKED'` (`models_app/models.py:938-942`,
`services_size_check.py:179`).

**Què passaria.** Dos historials paral·lels; i com que la resolució propaga a C1, dues
propagacions independents a dues bases diferents.

**Transport avui.** **CAP.**

### C6 · `POMAlert`

**Qui hi escriu.** `pom/s10_views.py:133`, `pom/s11_views.py:187` (`update_or_create`).

**Llei vigent.** Alerta derivada de comparar valor detectat vs esperat amb tolerància
asimètrica llegida de `BaseMeasurement(model, pom)` (`pom/s10_views.py:44,64`;
`pom/s8_views.py:164`). El camp `resolt_per_user_id` ja és un **id d'usuari cross-schema**
declarat (`fitting/models.py:160-161`).

**Què passaria.** Alertes diferents a cada casa, perquè el **llindar** (la base i les
toleràncies copiades del POM de catàleg, `models_app/models.py:600-603`) ja hauria divergit
per C1.

**Transport avui.** **CAP.**

### C7 · `Model.fase_actual` + `GateEvent`

**Qui hi escriu.** `tasks/services_d.py:37-42` (`advance_phase_gate`, escriu camp + event),
`:65-67` (`regress_phase`), `tasks/services_c.py:155` (la primera tasca `InProgress` treu el
model de `Pending`→`Dev`), `fitting/services.py:730-774` (el tancament de sessió avança fase).

**Llei vigent.** La fase avança **només per acceptació formal**, i cada moviment deixa un
`GateEvent` amb qui/quan/des d'on/cap a on (`tasks/models.py:141-142`). El `kind`
discrimina `advance`/`regress` (`:143`).

**Què passaria.** **La peça estaria en dues fases alhora.** El Brand la té a `PP` i el Studio
a `Proto`, els dos historials de gates són correctes, i qualsevol lectura de "en quina fase
està aquest model" depèn de quina casa la faci. És la divergència **més visible** del calaix C
perquè `fase_actual` és el que governa filtres, dashboards i el que `phase_passed_gate`
consulta (`tasks/services_e.py:22`).

**Transport avui.** **CAP.** `fase_actual` **no viatja** ni al traspàs inicial: el model EXTERN
neix amb el default `'Pending'` (`models_app/models.py:223`).

### C8 · `Watchpoint`

**Qui hi escriu.** `WatchpointViewSet` (`models_app/views.py:456`: create `:465`, `resolve`
`:468`, `reopen` `:479`), `models_app/views.py:2052`,
`models_app/bulk_import_service.py:546-551`, `models_app/extraction_views.py:2400,2450`, i el
signal `refresh_import_watchpoint` (`models_app/signals.py:145-173`).

**Llei vigent.** *«Advertència de TEXT LLIURE que viatja amb el MODEL a través dels gates»*
(`models_app/models.py:958`) — la llei diu explícitament **que viatja amb el model**. Cicle
`open`→`resolved` amb qui/quan/per què (`:972-979`). Els de sistema porten `dades` JSON i
`task IS NULL` (`:968-971`).

**Què passaria.** L'advertència que un tècnic escriu perquè *«un altre tècnic entengui»*
(`models_app/models.py:960-961`) **no arriba a l'altra casa**. La llei del model (viatja amb
el model a través dels gates) es compleix intra-schema i **es trenca a la frontera de la
federació** — el cas per al qual la llei existeix (una altra persona que reprèn la peça) és
precisament el que la federació crea.

**Transport avui.** **CAP.**

### C9 · `ModelFitxer` (`.ftt`, patrons, sketches, exports) + `FttDocumentLock`

**Qui hi escriu.** Escriptor únic de la invariant: `models_app/services_fitxers.py:90`
(`save_model_file`), amb 6 callers censats a §1.2. El lock:
`models_app/services_ftt_document.py:44,63-71`.

**Llei vigent.** *«Exactament un registre amb `is_current=True` per cadena `versio_anterior`»*
(`models_app/services_fitxers.py:4-6`), i **desar = versió nova encadenada, mai
sobreescriptura** (`models_app/services_ftt_document.py:11-12`). El lock és de **document
lògic** (arrel de la cadena), amb TTL de 30 min i force-if-stale
(`models_app/services_ftt_document.py:26,36-57`).

**Què passaria.** Dues cadenes de versions del mateix document, **cadascuna amb el seu propi
`is_current`**, i dos locks que no es veuen. La invariant "un sol cap de cadena" es compleix
dues vegades i **la promesa que el lock fa a l'usuari** («ningú més està editant aquest
document») **és falsa a través de la federació**. Nota afegida: el fitxer és `FileField` amb
storage **namespaced per tenant** (`models_app/models.py:480-481`; memòria
`ftt-media-namespace-tenant`), de manera que ni els bytes són el mateix objecte.

**Transport avui.** **CAP.**

### C10 · Els 45 camps no-federats del `Model`

Verificat per enumeració completa de `models_app/models.py:75-341` (59 camps de model
declarats; 14 viatgen). **No viatgen:**

`codi_client` (`:132`) · `studio_assignat` (`:159`) · `descripcio` (`:162`) ·
`color_referencia` (`:163`) · `collection` (`:165`) · **`garment_type` (`:167`)** ·
**`garment_group` (`:174`)** · `garment_set` (`:194`) · `piece_number` (`:201`) ·
**`target` (`:205`)** · **`construction` (`:206`)** · `estat` (`:222`) ·
**`fase_actual` (`:223`)** · `consumption_started_at` (`:225`) · `responsable` (`:229`) ·
`prioritat` (`:236`) · `data_entrada` (`:237`) · `created_by` (`:239`) · `created_at` (`:246`) ·
`data_objectiu` (`:247`) · `data_tancament` (`:248`) · `predicted_start`/`predicted_end`
(`:249-250`) · `reanchored_by_start` (`:255`) · `contracte` (`:257`) · `linia_contracte`
(`:264`) · `observacions` (`:272`) · `origen_patro` (`:274`) · `versio` (`:280`) ·
`slots_prev_tecnics`/`slots_prev_confeccio`/`slots_reals_tecnic`/`slots_reals_confeccio`
(`:283-286`) · `darrera_activitat` (`:300`) · **`measurements_version` (`:305`)** ·
**`design_freeze_at`/`design_freeze_by` (`:309-315`)** · `fabric_main` (`:325`) ·
`fabric_composition` (`:326`) · `shrinkage_type` (`:327`) · `shrinkage_warp` (`:329`) ·
`shrinkage_weft` (`:331`) · `shrinkage_pct` (`:333`) · `shrinkage_iso_key` (`:338`) ·
`fabric_notes` (`:340`).

**Bandera 1 — `garment_type` no viatja però `garment_type_item` sí.** El GTI es resol per clau
natural *a través de* `GarmentType.codi_client` (`tenants/federation_service.py:141-143`), però
el camp `Model.garment_type` **queda a NULL** al Studio. Model EXTERN amb GTI resolt i
`garment_type` buit és un estat que el codi permet i que cap guard detecta.

**Bandera 2 — el bloc de teixit/encongiment (7 camps) no viatja.** `shrinkage_*` és entrada del
càlcul; si el Brand l'omple i el Studio no, les dues cases treballen amb premisses físiques
diferents sobre la mateixa peça, sense cap avís.

**Bandera 3 — `target` i `construction` no viatgen** tot i ser els eixos que la cascada de
grading filtra (memòria `ftt-size-systems-cardinalitat`: l'eix és `size_system`, però `target`
governa la cascada del wizard).

### C11 · `measurements_version` i `design_freeze_*`

`measurements_version` (`models_app/models.py:305`, default 1) l'incrementa **només**
`pom/services.py:857-859`. `GradedSpec.generated_from_version` (`fitting/models.py:204`) hi
apunta per detectar specs ranci. Al Studio el model EXTERN neix amb `measurements_version=1`
independentment del que valgués al Brand → **els dos comptadors avancen per separat i no són
comparables**. `design_freeze_at/by` (`pom/wizard_views.py:37-41`) és un segell d'una casa que
l'altra no veu.

### C12 · `POMPlacement` (divergeix per la via del catàleg)

**Qui hi escriu.** `models_app/pom_placement_views.py:129`, endpoint
`POST /api/v1/item-fitxers/<item_id>/pom-placements/` (`models_app/urls.py:201`), gate CONFIGURE.

**Llei vigent.** *«La col·locació viu al CATÀLEG (ItemFitxer), no al model: una sola veritat que
els documents nascuts de l'item hereten»* (`models_app/models.py:1057-1058`). Unicitat
`(item_fitxer, pom, view_slot)` (`:1106-1108`). Cascada de resolució **EXACTE → GERMANA**
(altres `ItemFitxer` del mateix GTI) a `models_app/pom_placement_views.py:11-16,50-58`.

**Què passaria — i per què és diferent de la resta de C.** La cascada germana s'atura al
`GarmentTypeItem`, que és **una entitat de tenant**. El traspàs resol el GTI per clau natural
(`code` + `GarmentType.codi_client`) però **no comparteix la identitat**. Per tant: el Brand pot
tenir 40 precedents de col·locació sobre el seu sketch i el Studio **no en veu cap**, ni tan
sols com a "germana", perquè el seu GTI és una altra fila d'un altre schema. La divergència
aquí **no ve de dos escriptors sobre la mateixa superfície** sinó de **dos catàlegs que el
traspàs aparella per nom però no uneix**. Nota de context: la memòria `ftt-sembra-ai-report-f1`
registra que a PROD el cens de `POMPlacement`/òrfenes es va fer sobre `fhort`-staging i que
`los` és un subconjunt — el cens de precedents per tenant **no és el mateix** a cada casa.

**Transport avui.** **CAP.**

### C13 · `patterns.*` (cens; zona intocable)

`PatternFile` (`patterns/models.py:33`) i descendència, més `SewRelation` (`:427`),
`SewProposalRejection` (`:494`), `DartProposalRejection` (`:551`) i `SewToleranceAcceptance`
(`:701`, append-only per `_AppendOnlyQuerySet` `:693`), tots FK directa al `Model`. **Llei
vigent:** l'aprenentatge es fa **de la confirmació humana, mai de l'auto-match**
(`patterns/models.py:605-610`), i les acceptacions de tolerància són append-only (primera
baula d'auditoria del taller).

**Què passaria.** Dos patrons digitalitzats de la mateixa peça, dues cadenes d'acceptacions
d'auditoria, i cap manera de dir quina és la del taller que realment la va tallar.
**No es proposa cap canvi** (frontera declarada al brief i a `CLAUDE.md` §Zones intocables).

### C14 · `Production`

`tasks/models.py:270`, FK `model` (`:276`), escrit a `tasks/services_e.py:25` i
`fitting/views.py:276`. Guard vigent: `tasks/services_e.py:22` exigeix que la fase hagi passat
el gate (`phase_passed_gate`) — **i la fase és C7**. Si les fases divergeixen, **el guard de
producció respon diferent a cada casa per a la mateixa peça**.

### Veredicte BLOC 3: **llest**
14 superfícies del calaix C documentades amb escriptor, llei i conseqüència literal.
**Mecanisme de transport o sincronia per a qualsevol d'elles: CAP** — confirmat per cens
exhaustiu de `schema_context` (§Resum executiu 2) i de `tenants/management/commands/`.

---

## BLOC 4 — Cens del transport existent

### 4.1 `federation_service.traspassa` — la forma exacta

`tenants/federation_service.py:190-208`. Cadena: `resol_vincle` → `resol_schema`(×2) →
`llegeix_models_del_brand` → `instancia_al_studio` → informe.

| Propietat | Fet verificat |
|---|---|
| **Entitats que viatgen** | Exclusivament `models_app.Model`, i només els 14 camps de §Calaix A. **Cap altra taula** (`tenants/federation_service.py:112-116`) |
| **Sentit** | **Brand → Studio, unidireccional.** No existeix cap funció inversa (verificat: `tenants/management/commands/` només té 3 commands, i cap escriu al Brand des del Studio) |
| **Clau natural del model** | `codi_intern` (`:134`) |
| **Claus naturals de config** | `GarmentType.codi_client` + `GarmentTypeItem.code` (`:141-148`) · `SizeSystem.codi` (`:152`) · `GradingRuleSet.nom` (`:158`) |
| **Idempotència** | Per existència de `codi_intern` al Studio (`:134-136`): si hi és, va a `saltats` i **no s'actualitza res**. És **crear-si-no-hi-és**, mai un upsert |
| **Atomicitat** | `transaction.atomic()` embolcalla tota la creació quan `commit=True` (`:181-183`); amb `commit=False` recorre igual i no desa (dry-run real) |
| **Guard 1 (el pont)** | `TenantLink` existent **i** `es_viu()` (`:44-54`); errors `link_missing`/`link_not_active` |
| **Guard 2 (cada model)** | `Model.studio_assignat == studio_codi` (`:78`); sense assignació **res viatja** (`models_app/models.py:154-159`) |
| **Guard 3 (el destí)** | Ha d'existir `Customer(codi=brand_codi)` al Studio; si no → `customer_missing` (`:126-130`) — **no es crea, per decisió** |
| **Disciplina cross-schema** | El Brand es llegeix com a **dicts tancats** dins `schema_context`, mai objectes ORM vius (`:13-17`) — aplicació directa de la llei *«materialització prèvia, mai lectura ORM en viu»* |
| **Signals** | `Model.objects.create()` i **no** `bulk_create`, deliberadament, perquè els signals del Studio es disparin (`:115-117`) |
| **Errors** | `FederacioError` amb `codi` estable com a discriminant (`:28-34`); cada boca el tradueix (CommandError / HTTP) |
| **No-aparellats** | No bloquegen: camp a `NULL` + `unmatched` a l'informe (`:38-39,138`) |
| **Informe** | `{creats, saltats, unmatched, brand_codi, studio_codi, commit, total_brand, n_assignats, n_llegits}` (`:187,204-207`) |

**Les dues boques** (`tenants/federation_service.py:3-8`): el command
`tenants/management/commands/instantiate_external_models.py` i l'endpoint
`POST /api/v1/encarrecs/traspassar/` (`tenants/views_encarrecs.py:80-81`,
`tenants/urls.py:20`). **Cap regla de domini viu al command.**

**La safata** (`tenants/federation_service.py:211-265`, `GET /api/v1/encarrecs/`,
`tenants/views_encarrecs.py:68`): *«L'ESTAT ÉS UNA COMPARACIÓ, NO UN CAMP»* (`:214-217`) —
`estat_local ∈ {PENDENT, TRASPASSAT}` es calcula comparant `codi_intern` contra el schema del
Studio (`:244-254`). **No hi ha cap booleà "traspassat" a cap banda.** Només vincles ACTIUS
(`:227`); un tenant desaparegut es reporta com a `tenant_missing` en lloc de fer-se el
distret (`:233-236`).

### 4.2 L'assignació per-model (la segona clau)

`tenants/management/commands/assign_models_to_studio.py`. Escriu `Model.studio_assignat` **al
schema del BRAND** (`:100`), validant `TenantLink` ACTIU abans (`:45-52`). `--revocar` la buida
(`studio_assignat=''`, `:16`) — **no destrueix res**, només tanca la porta d'aquell model.
**NO EXISTEIX** endpoint HTTP per a aquesta assignació: només el command i el serializer que
exposa el camp en lectura (`models_app/serializers.py:117`).

### 4.3 Màquina d'estats del `TenantLink` i del token

`tenants/models.py:321-431`. **Tres estats** (`:342-349`): `ACTIU` · `ATURAT` · `REVOCAT`.

| Transició | Mètode | Regla |
|---|---|---|
| (alta) → `ACTIU` | `save()` genera token si falta (`:378-381`) | `clean()` exigeix que Brand sigui `tipologia='marca'` i Studio `'estudi'` (`:383-400`) |
| `ACTIU` → `ATURAT` | `aturar()` (`:406-413`) | només des d'`ACTIU`; segella `aturat_at`; **no destrueix res** |
| `ATURAT` → `ACTIU` | `reactivar()` (`:415-421`) | **només** des d'`ATURAT`; `REVOCAT` és terminal |
| qualsevol → `REVOCAT` | `revocar()` (`:423-431`) | idempotent; **terminal**; **no destrueix cap dada** |

**Unicitat:** `unique_together (brand_codi_tenant, studio_codi_tenant)` (`:369`) — **un sol
vincle per parella**, per sempre (per això reobrir un REVOCAT dona 409 i no una alta nova,
`tenants/views_recursos.py:99-104`).

**On viu:** a `public` (`fhort.tenants` és SHARED, `:330-334`), referències **per codi nu de 3
chars, mai FK** (`:336-339`), precedent `CodiAuth.tenant_schema`.

**El token, camí per camí:**
1. **Emissió** — `POST /api/v1/recursos/` (`tenants/views_recursos.py:89-119`); el token viatja
   a la resposta **un sol cop** (`:117-119`), i el serializer **no l'exposa mai més**
   (`tenants/serializers_recursos.py`, `list` a `:84-87`: *«Mai el token»*).
2. **Governança** — `POST recursos/<pk>/aturar|reactivar|revocar`
   (`tenants/views_recursos.py:135-145`), permís `EsMarca` + capacitat `CONFIGURE`
   (`:68-75`). ViewSet pla i no `ModelViewSet` **a posta**, perquè un PATCH sobre `estat`
   deixaria passar transicions que el model prohibeix (`:61-66`).
3. **Aterratge** — `POST /api/v1/customers/<pk>/vincular-token/` (`tasks/views_b.py:806-865`).
   **El token IDENTIFICA, no autoritza res de nou** (`:814-817`): només omple
   `Customer.codi_global` amb el `brand_codi_tenant`. Tres validacions (existeix · és ACTIU ·
   és MEU) amb **la mateixa resposta d'error per a les tres** (`400 token_invalid`, `:826-828`).
   `DELETE` només buida `codi_global`; **no toca el vincle** (`:830-831`).
   `codi_global` és read-only al serializer (`tasks/serializers_b.py:88`): l'única porta és
   aquesta acció.
4. **Lectura de l'estat des del Studio** — `TenantSerializer.get_vincle_estat`
   (`tasks/serializers_b.py:90-107`), consulta a `public` sense `schema_context` perquè el
   `search_path` del tenant ja hi arriba.

**Llei confirmada:** *«el token governa el PONT, mai la capacitat de treballar»*
(`tenants/models.py:326-329`). Verificat per absència: cap dels ~40 escriptors censats al BLOC 1
consulta `TenantLink`. Aturar o revocar **atura el traspàs i buida la safata**, i **no toca ni
una fila** de cap superfície de treball.

### 4.4 L'altre transport cross-schema que existeix (per completesa)

- **`bootstrap_tenant`** (`tasks/management/commands/bootstrap_tenant.py`) — copia el **CATÀLEG**
  tenant→tenant (no models ni feina). Lleis pròpies: idempotent-additiva amb `update_or_create`
  i mai `delete` (`:22-23`); **remapeig de FK per clau natural entre schemas, mai per pk**
  (`:24-26`); FK a entitats del tenant origen **no viatgen** (`:27-28`); **Welford net**
  (`:29-31`); auto-FK en dues passades (`:32-35`). ⚠️ Memòria `ftt-bootstrap-desti-poblat`:
  **no usable contra un destí poblat** — `update_or_create` sobreescriuria catàleg viu.
- **`backoffice/receivers.py:14`** — l'únic camí tenant→`public`, per a la meritació.
- **`tenants/discovery_service.py:35`** — recorregut de schemas del login únic (lectura).
- **`backoffice/invoice_pdf.py:50`** — lectura de dades de l'emissor (`EMISSOR_SCHEMA`).

### Veredicte BLOC 4: **llest**
El transport és **un**, **unidireccional**, **de creació** (no d'actualització), **de 14 camps**,
**gated per dues claus independents**, i **idempotent per no-fer-res**. La màquina d'estats del
vincle és de 3 estats amb `REVOCAT` terminal i **cap acte destructiu**.

---

## BLOC 5 — Opcions que el cens habilita

> **Enumeració, no recomanació.** La decisió és Patró C (Agus). Cada opció es llista amb les
> superfícies del calaix C que afectaria i el fet del cens que la fa possible o costosa.
> `💡 PROPOSTA (a validar)` s'aplica a tot aquest bloc.

**Opció 1 — Partició per superfície** (cada superfície té UN propietari declarat; l'altre la
llegeix o no la té).
- Afectaria: **totes les 14 del calaix C**, una decisió per cadascuna.
- El cens la fa viable: cada superfície té escriptors identificats i acotats (BLOC 1); les
  fronteres d'app ja estan netes.
- El cens n'assenyala el cost: **C10 obliga a partir el `Model` camp a camp**, no taula a
  taula, perquè `consumption_started_at` (calaix B) conviu a la mateixa fila que `fase_actual`
  (C7) i `measurements_version` (C11).
- Cas especial: **C12 (`POMPlacement`) no es pot partir per aquesta via**, perquè no penja del
  Model sinó del catàleg de cada tenant.

**Opció 2 — Relleus amb materialització** (la peça té un propietari **en cada moment**; el
canvi de mà materialitza un snapshot cap a l'altre schema).
- Afectaria: **C1, C2, C3, C4, C5, C7, C9, C11** — les superfícies que tenen un moment natural
  de relleu (tancament de fitting, gate de fase, tancament de base).
- El cens la fa viable: `traspassa` ja és exactament una materialització unidireccional amb
  claus naturals i disciplina de dicts (`tenants/federation_service.py:13-17`), i respecta la
  llei *«materialització prèvia, mai lectura ORM en viu»*. La segona materialització seria
  del mateix patró amb més entitats.
- El cens n'assenyala el cost: `traspassa` avui **no actualitza mai** (idempotència per
  no-fer-res, `:134-136`); un relleu exigeix decidir la política de col·lisió, que **no
  existeix enlloc del codi**.
- Precedent de llei ja escrit per al que **no** s'ha de materialitzar: el Welford net de
  `bootstrap_tenant` (`:29-31`) — el calaix B no viatja.

**Opció 3 — Sincronia per events** (cada escriptura emet un event que l'altre schema consumeix).
- Afectaria: potencialment **totes les 14 del calaix C**; amb més naturalitat **C1, C7, C8**,
  que ja tenen log append-only o event propi.
- El cens la fa viable: ja hi ha **tres fonts append-only** projectades a una forma comuna
  `{at, kind, actor, payload}` al timeline (`models_app/views.py:2785-2790`:
  `MeasurementChangeLog` + `GateEvent` + `TaskTransition`), i **un precedent de signal
  cross-schema en producció** (`tasks/signals.py` → `backoffice/receivers.py:14`, amb
  `actor_schema`).
- El cens n'assenyala el cost: el timeline és **només de lectura** i cobreix 3 de 14
  superfícies; C2/C3/C9/C12 **no tenen cap log** i haurien de guanyar-ne un. A més, els logs
  apunten per **FK a pks locals** (`models_app/models.py:639-642`), que no travessen schemas.

**Opció 4 — Cap de les anteriors: divergència acceptada i declarada** (les dues cases treballen
la seva còpia i el sistema ho diu explícitament en lloc de suggerir que és la mateixa peça).
- Afectaria: **cap superfície canvia**; el que canviaria és la **superfície de lectura** (dir a
  l'usuari que la peça té dues instàncies).
- El cens la fa viable: `Model.origen = EXTERN` (`models_app/models.py:151-153`) ja marca la
  còpia, i `estat_local` de la safata (`tenants/federation_service.py:249-254`) ja sap
  comparar-les per `codi_intern`.

**Transversal a totes les opcions (fet, no proposta):** la llei *«cap dada es destrueix en
aturar/revocar el token»* (`tenants/models.py:326-329,406-431`) obliga que qualsevol mecanisme
que s'esculli **degradi a "les dues cases conserven el que tenen"** quan el pont es tanca, mai
a un esborrat ni a un bloqueig d'escriptura.

---

## Taula final de riscos per al CTO

| # | Risc / fet | Superfícies | Evidència | Estat |
|---|---|---|---|---|
| R1 | **Dues veritats de mesura sense cap detecció.** Últim-escriptor-guanya intra-schema, cap comparació cross-schema | C1, C6 | `models_app/models.py:619`; `views.py:1402`; `fitting/services.py:369` | **OBERT** — cap mecanisme |
| R2 | **La peça pot estar en dues fases alhora.** `fase_actual` no viatja ni al traspàs inicial | C7, C14 | `tasks/services_d.py:37-42`; `models_app/models.py:223`; `tasks/services_e.py:22` | **OBERT** |
| R3 | **La invariant anti-dues-veritats de G6 no cobreix la federació.** `UniqueConstraint` d'una sola `GradingVersion` activa és per `SizeFitting`, i n'hi ha un per schema | C3 | `fitting/models.py:99-109` | **OBERT** — invariant intra-schema per disseny |
| R4 | **El lock `.ftt` promet exclusivitat que no té cross-schema.** Dues cadenes, dos `is_current`, dos locks | C9 | `services_ftt_document.py:28-57`; `services_fitxers.py:4-6` | **OBERT** |
| R5 | **El Watchpoint incompleix la seva pròpia llei a la frontera.** «Viatja amb el MODEL» però no travessa el pont | C8 | `models_app/models.py:958-961` | **OBERT** |
| R6 | **`POMPlacement` divergeix per una via diferent** (catàleg, no Model): la cascada germana s'atura al GTI local | C12 | `models_app/models.py:1057,1076`; `pom_placement_views.py:11-16` | **OBERT** — cap partició per-model l'arregla |
| R7 | **El `Model` no és particionable com a taula.** `consumption_started_at` (B) conviu amb `fase_actual` (C7) i `measurements_version` (C11) | C10, C11 | `models_app/models.py:223,225,305` | **A DECIDIR** |
| R8 | **`garment_type`/`garment_group`/`target`/`construction` no viatgen** tot i que `garment_type_item` sí (resolt *a través* de `garment_type.codi_client`) | Calaix A | `federation_service.py:141-143`; `models_app/models.py:167,174,205,206` | **BANDERA** |
| R9 | **7 camps de teixit/encongiment no viatgen**: premisses físiques divergents sense avís | C10 | `models_app/models.py:325-340` | **BANDERA** |
| R10 | **Doble meritació per peça (una per actor).** Guarda d'unicitat per-schema; `actor_schema` ja diferencia els events | Calaix B | `tasks/services_c.py:162-181`; `models_app/models.py:864`; `backoffice/models.py:88-93` | **CONFORME** amb «meritació per actor» — es registra com a fet |
| R11 | **`traspassa` no actualitza mai** (idempotència per no-fer-res): qualsevol relleu o re-materialització requereix una política de col·lisió **que no existeix** | Calaix A + qualsevol opció de BLOC 5 | `federation_service.py:134-136` | **A DECIDIR** |
| R12 | **Cap camí de retorn Studio→Brand.** Verificat per absència (3 commands, 2 endpoints, cap escriu al Brand) | Totes | `tenants/management/commands/`; `federation_service.py` | **NO EXISTEIX** |
| R13 | **Els logs append-only no són reconciliables cross-schema**: apunten per FK a pks locals | C1, C5 | `models_app/models.py:639-642` | **OBERT** — condiciona l'Opció 3 |
| R14 | **`patterns.*` divergiria igual** (dos patrons, dues cadenes d'auditoria append-only) | C13 | `patterns/models.py:427-728` | **ANOTAT** — zona intocable, no s'hi proposa res |

---

*Patró A · READ-ONLY. Cap escriptura a BD, cap commit de codi, cap migració. Aquest document
és l'única sortida de la sessió i queda SENSE COMMITAR, per la disciplina del patró.*
