# DIAGNOSI_REFACTOR — Síntesi accionable vell↔nou (FTT)

> Síntesi de `MAPA_SISTEMA_EXHAUSTIU.md`. READ-ONLY. NO decideix: marca ⚖️ per a l'Agus.
> Totes les referències `fitxer:línia` són heretades del MAPA. Cap ref nova inventada;
> les afirmacions sense font al MAPA es marquen "PENDENT DE VERIFICAR". Generat: 2026-06-22.

## (a) Graf vell ↔ nou

> Estats: **mort viu** (definit/exposat però mai exercit) · **doble camí** (vell i nou conviuen actius) · **òrfena** (sense escriptor/lector) · **documentat-no-implementat** (contracte declarat, codi no escrit).

| # | Camí VELL | Camí NOU (equivalent) | Estat | Refs (MAPA) |
|---|---|---|---|---|
| 1 | `Model.estat` (Nou/EnCurs/EnRevisio/Tancat) | `fase_actual` (Pending/Dev/Proto/SizeSet/PP/TOP) + `consumption_started_at` | **mort viu** — BD: `DISTINCT estat`='Nou' sempre; el cicle real el porten fase+flag | `models_app/models.py:201-204,83-101`; BD orquestrador (línies 56-63 MAPA) |
| 2 | Facturació via flag tenant: `Model.consumption_started_at` + `ConsumptionRecord` (OneToOne) | Event PUBLIC `ModelConsumptionEvent` (COUNT per {codi_client,period}) | **doble camí** — units per `opaque_ref` (sense FK); divergeixen (11 events vs 6 merited) | `models_app/models.py:760-777`; `backoffice/models.py:63-77`; `services_c.py:95-114` |
| 3 | Triple-escriptura meritació inline a `services_c.py:95-114` | Mateixa seqüència duplicada a `reconcile_consumption.py:113-146` | **doble camí** (de codi) — no factoritzat en servei únic; risc divergència | `services_c.py:95-114`; `reconcile_consumption.py:113-146` |
| 4 | Preu via `Plan.preu_model_extra`/`models_inclosos`/`moneda_pla` (Sprint 2) | Preu via `ContractLine.preu`/`inclosos`/`moneda` (Sprint 5) | **mort viu** — el motor `billing_service` NOMÉS llegeix ContractLine; Plan òrfe de lectura | `tenants/models.py:46-48`; `backoffice/models.py:106-107`; `billing_service.py:71-83` |
| 5 | `Client.actiu` (bool legacy) | `Client.estat` (onboarding/actiu/suspes/baixa) + property `es_actiu` | **mort viu** — cap codi escriu `client.actiu=` | `tenants/models.py:112,181-184` |
| 6 | `Client.adreca_fiscal` (CharField) | Adreça estructurada (linia1/linia2/ciutat/...) | **doble representació** (LEGACY explícit, "es buidarà via migració") | `tenants/models.py:128`; `serializers_tenants.py:58` |
| 7 | `SizeFitting` = TAULA de mesures/grading d'un model (Sprint 1-3, eix pom) | `FittingSession`/`PieceFitting` = esdeveniment de provatura (Sprint 5B) | **COL·LISIÓ DE NOM, NO de concepte** — conviuen; `PieceFitting.grading_version.size_fitting` enllaça els dos. Cap mort | `fitting/models.py:7-59,202-334` |
| 8 | Targets grading: `GradingRuleSet.target` FK legacy (`*_legacy`) | `GradingRuleSet.targets` M2M autoritatiu | **doble camí ACTIU** — la FK encara s'escriu (`size_map_views.py:572-573,580`), es clona (`s2_views.py:171,196`) i es llegeix (`s8_views.py:125`) | `pom/models.py:504-515` |
| 8b | (Patró ja resolt:) `SizeSystem.target` FK | `SizeSystem.targets` M2M | **migrat** — FK eliminada a migració 0021; matching usa només M2M | `matching.py:71`; `pom/migrations/0021` |
| 9 | Regles grading externes: `GradingRule` del `GradingRuleSet` compartit | `ModelGradingRule` resident al model (PG-0, `db_constraint=False`) | **doble camí** — `_load_grading_rules` prioritza resident, fallback a extern; per disseny fins backfill | `pom/services.py:356-377`; `models_app/models.py:623,646-649` |
| 10 | Override per talla compartit: `GradingException` (al rule_set, "leak to every model") | `ModelGradingOverride` (per-model, Sprint 5B.3) | **doble camí** — motor llegeix tots dos amb prioritat override>exception | `pom/services.py:92-100`; `models_app/models.py:587-603` |
| 11 | `GarmentPOMMapEditor.jsx` (eina VELLA, per família/garment-type) | `POMBrowser.jsx` (eina NOVA, assign per item) | **VELL = codi mort** — endpoints fantasma `pom-map/*`→404; usa `POMGlobal.codi_intern` inexistent; no enrutat | `App.jsx:20-21`; `POMBrowser.jsx`; migració pom 0016 |
| 12 | Import single-model: `extract_from_file_view`+`create_from_extraction_view` + `extraction_service.py` (httpx cru, `claude-opus-4-5`, prompt CAT `EXTRACTION_PROMPT`) | Wizard ImportSession 2-call (SDK, `claude-opus-4-7`/`claude-sonnet-4-6`, prompt EN `TECH_SHEET_EXTRACTION_PROMPT`, "el document mana") | **doble camí ACTIU** — ambdues rutes registrades (`urls.py:59-60`); el vell viu | `extraction_views.py:76-614,816-2001`; `extraction_service.py:81,162` |
| 13 | Eix `garment_type` (família) a GarmentPOMMap / Model | Eix `garment_type_item` (item) | **doble camí en migració** — pont `backfill_model_items.py` (10 mapes); FK `garment_type` ja eliminat de GarmentPOMMap (0016) | `tasks/models.py`; `backfill_model_items.py:13-29` |
| 14 | `Model.talla_base` (FK SizeDefinition) | `Model.base_size_label` (CharField) | **mort/eliminat** — camp tret a migració 0018; cap codi viu el llegeix | `models_app/migrations/0018`; `models_app/models.py:268` |
| 15 | `SizingProfile` (target+garment+construction+fit→size_system+ruleset) | `GarmentTypeItem.grading_rule_set`/`base_size_definition` (grading ancorat a l'Item) | **doble camí (sospitós)** — tots dos s'escriuen; cal confirmar si SizingProfile és el vell a deprecar | `pom/models.py:786`; `tasks/models.py:380` |
| 16 | `fitting.advance_phase` (escrivia `fase_actual` + segellava) | `tasks/services_d.py:advance_phase_gate` (únic amo de `fase_actual` + GateEvent + `seal_model_grading`) | **VELL buidat** — `advance_phase` ja NO escriu fase; `sealed`/`advanced` sempre buits; docstring desfasat; endpoint `advance-phase` encara exposat | `fitting/services.py:709,751-769`; `tasks/services_d.py:37` |
| 17 | Receivers `after_save/delete_model_task` que derivaven `fase_actual` des de tasques | Cap signal deriva fase; amo explícit = `advance_phase_gate` + auto `Pending→Dev` a `services_c.py:91` | **retirat (Sprint 0)** — documentat a la capçalera de signals | `tasks/signals.py:1-11` |
| 18 | Grading inline a set-measurements (`rule.increment_cm` inexistent→delta 0) | Motor `generate_graded_specs` / `_apply_rule` | **eliminat (codi mort retirat)** — documentat | `models_app/views.py:771-773` |
| 19 | Format pdfme `template_json['schemas']` | Format Konva v2 `template_json['pages']` | **compat de dades velles** — serializer accepta ambdós; motor nou només escriu `pages`; potencialment mort (0 fitxes antigues a staging, PENDENT DE VERIFICAR a BD) | `tech_sheet_serializers.py:26,31,48,53`; `TechSheetEditor.jsx:575` |
| 20 | s9 `setup_tenant_from_excel_view` escriu `POMGlobal.codi_intern/nom_cat/htm_*/is_key_measure` | (camps reals: `codi`/`nom_ca`/`descripcio_en`/`is_key`) | **BROKEN / mort viu** — cada fila peta, empassada per `except: pass`; el seed `pom_globals` mai escriu res | `s9_views.py:179-191` |
| 21 | `Tasks.jsx` (ruta `/tasques`) → `/api/v1/model-tasques/` | `KanbanTasks.jsx` (ruta `/tasques/kanban`) → `by-model`/`transition`/`claim` | **VELL trencat** — endpoint inexistent; sidebar no hi enllaça | `Tasks.jsx:34`; `App.jsx:150-151`; `Sidebar.jsx:50` |
| 22 | `TascaViewSet` legacy (`views.py:18`) | `views_sprint1c.TascaViewSet` / `PaquetServeiViewSet` | **doble registre** — `urls.py:13-18` registra sprint1c amb fallback legacy (inabastable); ambdós òrfens al frontend (`PaquetServei` però viu com FK des de `ModelServei`) | `tasks/urls.py:13-18`; `views.py:18`; `views_sprint1c.py:12-40` |
| 23 | `--gate` lila `#534ab7` (backoffice `index.css:30-31`) | `--gate`=`var(--ok)` verd (frontend `index.css:30-31`) | **token divergent vell↔nou entre apps** — frontend migrat, backoffice no | `frontend/src/index.css:30-31`; `frontend-backoffice/src/index.css:30-31` |

## (b) Punts calents (ordenats per blast radius)

> De més connectat a menys. Cada un: què és · què es trenca si es toca (🔗) · per què és calent.

**1. `Client.codi_tenant` / `Customer.codi` / `codi_client` (pivot universal d'identitat+facturació).**
És el mateix valor de 3 chars que deriva `schema_name`, el domini, el prefix de `codi_intern`, i és la clau fluixa public↔tenant.
🔗 Tocar-lo trenca: routing de tenant, codi-gen de models, recompte facturable (`ModelConsumptionEvent.codi_client`), unió albarà↔event, i `billing_service` (filtra per `codi_client` literal — si `customer.codi` i `Client.codi_tenant` divergeixen, la factura no quadra). Refs: `serializers_tenants.py:138`, `views_tenants.py:68`, `models_app/services.py:9-13`, `services_c.py:111`, `billing_service.py:63`.
Calent: única font d'identitat de tot el sistema; sense FK que el protegeixi (referència per valor).

**2. `transition_task` (`tasks/services_c.py:42`) — única porta a transicions de ModelTask.**
🔗 Toca: `TimerEntrada` (obrir/tancar comptador), `TaskTransition` (log), `Model.fase_actual` (auto Pending→Dev), `Model.consumption_started_at`+`ConsumptionRecord` (meritació), signal `model_consumption_started` (backoffice/reconcile), Welford `TaskTimeEstimate`, cascada de planning (`recompute_for_technicians`). Refs: `services_c.py:42-127,88-114`.
Calent: és la juntura 🅰️🅱️ on l'acció del tècnic (Kanban) dispara facturació, fase i estimacions alhora.

**3. `advance_phase_gate` (`tasks/services_d.py:25`) — únic amo de `fase_actual` endavant.**
🔗 Toca/crida: `GateEvent`, `seal_model_grading` (fitting — acobla tasks↔fitting↔grading), guard terminal TOP→`ESTAT_TANCAT`, `has_delivered_production`, `next_phase` (`views.py:1527-1539`), i el frontend `ActionsMenu.jsx:168-169`. Refs: `services_d.py:37,42-53,46`.
Calent: governa el cicle de vida real del model i el segellat de producció del grading.

**4. `generate_graded_specs` / `_apply_rule` (`pom/services.py:18,476`) — motor únic de grading.**
🔗 Trenca: grading_views (regenerar-talles), generar-grading, set-size-override, fitting close, services_size_check, extraction W5, clone_model_for_qa, wizard_views, preview import. Refs: `pom/services.py:18,142,476`.
Calent: coll d'ampolla del càlcul de talles; el criden ~10 camins. `_apply_rule` marcada "ZONA INTOCABLE".

**5. `find_pom_master` (`extraction_views.py:1070-1149`) — resolució única de POM mestre.**
🔗 Trenca els 4 camins de matching (vell, W2-PDF, W2-Excel, library-prefill) + size_map_views + la creació de POMMaster tenant-only. 6 estratègies. Refs: `extraction_views.py:1070-1149,325,1374,1244`.
Calent: tot el matching POM del sistema passa per aquí.

**6. `POMMaster` (entitat central del domini POM).**
🔗 El referencien `GarmentPOMMap`, `ItemBaseMeasurement`, `GradingRule`, `GradingException`, `ClientMesuraPerfil`, `POMEstadisticaTenant`, `BaseMeasurement`, `GradedSpec`. Tocar PK/`codi_client` trenca grading i matching (filtre `codi_client__iexact`). Refs: `pom/models.py:180-252`.
Calent: node de mesura del qual pengen 8+ entitats cross-app i cross-schema.

**7. `scheduler_service.schedule` + `calendar_service` (`planning/`).**
🔗 `schedule` escriu `ModelTask.planned_*` i `Model.predicted_*` (ho llegeixen `plan/current`, `calendar/events`, Gantt, `en_risc`, `eligible-technicians`). `calendar_service` és la base de scheduler+plan_service+fitting `schedule_bulk`+Size Check (`add_working_days`). `_collect_busy_intervals` depèn de `FittingSession`. Refs: `scheduler_service.py:117,95`; `calendar_service.py:81-175`.
Calent: motor determinista del qual depèn tota la planificació i l'agenda; acobla planning↔fitting↔tasks↔size-check.

**8. Signal `model_consumption_started` + `opaque_ref` (pont B→A de facturació).**
🔗 2 emissors (`services_c.py:108`, `reconcile_consumption.py:140`) / 1 receptor (`receivers.py:7`). `opaque_ref` ha de ser el MATEIX UUID a tenant i public; si es trenca la igualtat es duplica o es perd facturació. La idempotència és NOMÉS per `opaque_ref`. Refs: `tasks/signals.py:17`; `receivers.py:10-18`.
Calent: única via de materialització del fet facturable; idempotència fràgil (vegeu col·lisió 11 vs 6).

**9. `get_capabilities` / `HasCapability` (`accounts/capabilities.py`).**
🔗 Cor transversal de gating: l'importen tasks, fitting, pom, planning, models_app. Canviar-ne signatura/semàntica trenca el gating de totes. `rol_nom` CharField lliure → valor fora de `ROLE_CAPABILITIES` = set buit (usuari sense permisos). Refs: `capabilities.py:31,46,39`.
Calent: única font de veritat d'autorització de tot el servei.

**10. Tokens CSS `index.css` (frontend).**
🔗 66 fitxers usen `--gold`/`--cream`/`IBM Plex`; la font global `*{font-family}` afecta tota l'app. L'amplada del sidebar (240) i l'offset staging (28px) estan duplicats entre Shell/Sidebar/Topbar. Refs: `index.css:3-44`; `Shell.jsx:26`/`Sidebar.jsx:299`.
Calent: única font d'estil; canvis no coordinats trenquen el layout global.

**11. `GradedSpec` (sortida del motor de grading).**
🔗 Lectors: graded-table, taula-mesures, graded-specs-units, serializers, PieceFittingLine (clona specs), fitting-vs-spec. Refs: `fitting/models.py:163`; `fitting/services.py:296,325`.
Calent: tota la presentació de talles i la fitxa tècnica en depèn.

## (c) Col·lisions vell/nou a resoldre

> Punts on vell i nou XOQUEN i cal triar un. (Decisió = Agus; aquí només es nomena el conflicte.)

1. **Definició d'"estat del model" (eix 1):** `Model.estat` (declarat, mort) vs `fase_actual`+`consumption_started_at` (efectiu). Dos eixos d'estat conviuen; el filterset i l'índex encara exposen `estat`. `models_app/models.py:201-204,321`; `views.py:25`.

2. **Font de veritat de la facturació (eix 2):** flag tenant (`consumption_started_at`/`ConsumptionRecord`) vs event public (`ModelConsumptionEvent`). Quan divergeixen (11 events vs 6 merited per clons QA), **quin mana?** `services_c.py:95-114`; `backoffice/models.py:63-77`; `clone_model_for_qa.py:81-86`.

3. **Idempotència de l'event de consum:** avui per `opaque_ref` (UUID) — clonar QA deixa events públics orfes i pot sobrecomptar. Triar entre (a) que `clone_model_for_qa` purgui events públics, o (b) idempotència per `(codi_client, model)`. `receivers.py:11`; `clone_model_for_qa.py:83`.

4. **Targets de GradingRuleSet (eix 8):** FK legacy `target` (encara escrit/clonat/llegit) vs M2M `targets` autoritatiu. Cal retirar la FK (com es va fer a SizeSystem 0021) o mantenir el doble camí. `pom/models.py:504-515`; `size_map_views.py:572-573`; `s8_views.py:125`.

5. **Personalització de grading per talla (eixos 9-10):** TRES mecanismes coexisteixen — `ModelGradingRule` (resident), `ModelGradingOverride` (per-model), `GradingException` (compartit, "leak"). Triar quins es mantenen i amb quin rol. `pom/services.py:92-100,356-377`.

6. **Eines POM-assign (eix 11):** `POMBrowser` (nou, viu) vs `GarmentPOMMapEditor` (vell, codi mort amb endpoints 404). No es solapen en runtime (item vs família) però el vell encara és al repo. `App.jsx:20-21`.

7. **Pila d'import single-model (eix 12):** camí vell (`extraction_service.py`, model `claude-opus-4-5` via httpx, prompt CAT) vs wizard nou (SDK, `claude-opus-4-7`/`claude-sonnet-4-6`, "el document mana"). Ambdós registrats i actius. A més: el nou NO extreu imatges del PDF que el vell sí (`extract_images_from_pdf`). `urls.py:59-60`; `extraction_service.py:81,234`.

8. **`SizingProfile` vs `GarmentTypeItem.grading_rule_set` (eix 15):** dues fonts de "context de grading per Item", totes dues escrites. Cal dictaminar si SizingProfile és el vell a deprecar. `pom/models.py:786`; `tasks/models.py:380`.

9. **`fitting.advance_phase` buidat vs `advance_phase_gate` (eix 16):** el vell ja no fa res però l'endpoint `advance-phase` segueix exposat (`views.py:161`). Retirar l'endpoint o no.

10. **Asimetria `db_constraint=False` cross-schema:** `SizeCheckLine.pom` i `ModelGradingRule.pom` el declaren; `PieceFittingLine.pom`/`GradedSpec.pom`/`POMAlert.pom` NO, tot i ser el mateix patró tenant→public. Cal alinear. `models_app/models.py:833,648`; `fitting/models.py:346,175,119`.

11. **Gating de design freeze:** `approve_design_freeze_view` només exigeix `IsAuthenticated` (un technician pot congelar) mentre gate/regress exigeixen `close_gates`. El design freeze és gate de govern o aprovació de tècnic? `pom/wizard_views.py:17`; `tasks/views_b.py:444`.

12. **Doble escriptor de tancament de taula:** `confirm_base_size_view` duplica la lògica de `close_base`/`generate_graded_specs` (mín. 3 POMs, generar grading) en lloc de delegar. `pom/wizard_views.py:228-288`; `pom/services.py:283-286`.

13. **`Plan.tipologia` (3 valors, inclou enterprise) vs `Client.tipologia` (2 valors):** un Client amb pla Enterprise no pot reflectir-ho a la seva tipologia. `tenants/models.py:27-31,61-64`.

14. **Sistema d'icones backoffice:** webfont Tabler (`ti ti-*`) i paquet React `@tabler/icons-react` conviuen a la mateixa app. `frontend-backoffice/index.html:7`; `TenantsPage.jsx:3`.

## (d) Òrfenes / codi mort

> Llista consolidada amb `fitxer:línia`. (M)=mort viu, (O)=òrfena sense escriptor/lector, (DNI)=documentat-no-implementat, (B)=trencat.

**Backend — camps/models:**
- (M) `Model.estat` + tot `ESTAT_CHOICES` — sempre 'Nou' a BD. `models_app/models.py:201,83-92`.
- (B) Bug valor invàlid: `pom/wizard_views.py:38` escriu `'En curs'` (amb espai) ≠ constant `'EnCurs'`. `models_app/models.py:84`.
- (M) `Client.actiu` (bool) — cap escriptor. `tenants/models.py:112`.
- (M/LEGACY) `Client.adreca_fiscal`. `tenants/models.py:128`.
- (M) `Plan.preu_model_extra`/`models_inclosos`/`moneda_pla` — motor no els llegeix. `tenants/models.py:46-48`.
- (O) `POMEstadisticaGlobal` / `POMEstadisticaTenant` — cap referència fora de models.py/migracions. `pom/models.py:138-153,255-269`.
- (M) `POMMaster.is_key_measure` (property retorna sempre False) + alias-properties no-ORM. `pom/models.py:249-252`.
- (B) `s9_views.setup_tenant_from_excel_view` — escriu camps inexistents a POMGlobal, empassat per `except: pass`. `s9_views.py:179-191`.
- (?) `GradingRuleHistory.pom → POMGlobal` (no POMMaster) — incoherent; cap escriptor trobat al domini POM. `pom/models.py:829-830`.
- (O) `TipologiaModel` — model+migracions, cap viewset/serializer/import viu. `tasks/models.py:74`.
- (M) `Tasca.activa` vs `is_active` (doble flag); camps `slots_base`/`minuts_estandard`/`ordre` sense lectura viva. `tasks/models.py:16,59`.
- (DNI) `Customer.codi_global` — placeholder "sense lògica". `tasks/models.py:306-308`.
- (DNI) `PlanSnapshot.working_minutes_per_day`/`blocked_dates` mai poblats; `result.load_minutes`/`campaign_end` documentats no produïts. `tasks/models.py:440-441,447-448`.
- (M/ubicació) `PlanSnapshot` viu a `tasks/` però és 100% de `planning/`. `tasks/models.py:431`.
- (O) `SizeFitting.sf_pare`/`fills` — definits, només `select_related`, cap codi els escriu/navega. `fitting/models.py:27-33`.
- (M) `SizeFitting.tipus` — choices Proto/Fit/SizeSet/PP/TOP però l'únic creador força sempre `'SizeSet'`; test usa `'PRINCIPAL'` (valor inexistent). `pom/services.py:234`; `fitting/tests.py:57`.
- (M) Estats `SizeFitting.Pendent`/`BaseOberta` gairebé mai escrits. `fitting/models.py:16-17`.
- (M) `close_piece_fitting` retorna `override_changed` sempre False ("per compat. de forma"). `fitting/services.py:357,384,488`.
- (M/buidat) `fitting.advance_phase` — `sealed`/`advanced` sempre buits; docstring desfasat. `fitting/services.py:751-771,715`.
- (O) `ImportSession.historia_xat` — cap escriptura/lectura trobada (PENDENT DE VERIFICAR fora del domini 10). `models_app/models.py:414`.
- (M) `_POM_SYNONYMS` entrades `:1042-1055` (sobreescrites per `:1056-1066`, "last wins"). `extraction_views.py:1042-1066`.
- (O) `TechSheet.estat` (obert/tancat) — exposat al serializer, cap vista l'escriu/llegeix. `tech_sheet_models.py:15-25`.
- (O/DNI) `TechSheet.versio` — default 1, mai incrementat. `tech_sheet_models.py`.
- (O) `BackofficeActionLog` — cap `.create`/`save` enlloc. `backoffice/models.py:37`.
- (DNI) `Invoice`/`InvoiceLine` — model+migració+billing_service, però sense serializer/endpoint/UI; lifecycle esborrany→emesa→pagada no implementat. `backoffice/models.py:147-206,152`.
- (M) Rol `BackofficeUser.FACTURACIO` — definit, cap `HasBackofficeRole` l'usa. `backoffice/models.py:20`.
- (M/eliminat) `Model.talla_base` (FK) — tret a migració 0018. `models_app/migrations/0018`.
- (DNI) Brain `fitting/brain.py:16-32` — STUB confés, no propaga; `GradedSpec.generated_from_version` (stale link, no implementat). `fitting/models.py:182-186`.
- (DNI) Detecció specs stale `generated_from_version < measurements_version` — només es desa el link. `fitting/models.py:182-186`.

**Backend — vistes/endpoints/commands:**
- (M) Endpoints planning sense consumidor: `plan/compute|preview|apply|snapshots`. `endpoints.js:218-223`; backend complet.
- (M) Endpoints `jornada`/`absencies` sense UI (el motor sí els llegeix). `endpoints.js:256-268`; `calendar_service.py:47-63`.
- (M) `facturacio/generar/` sense UI (només curl/test). `views_contracts.py:48`.
- (B) `Tasks.jsx`→`/api/v1/model-tasques/` (endpoint inexistent). `Tasks.jsx:34`.
- (M/doble registre) `TascaViewSet` legacy + sprint1c. `tasks/urls.py:13-18`; `views.py:18`.
- (M, OBSOLET marcat) `reseed_tenant_fhort.py` — "NO EXECUTAR"; peta amb schema actual. `reseed_tenant_fhort.py:2-7`.
- (M, one-shot ja aplicat) `reconcile_tenant_poms` amb 19 ids hardcoded PROD-fhort. `reconcile_tenant_poms.py:30,33-36`.
- (pont consumible) `backfill_model_items.py`, `0027_data_fit_to_proto` — vell→nou ja migrat. `backfill_model_items.py:13-29`.

**Frontend — components/residus:**
- (M, declarat) `pages/GarmentPOMMapEditor.jsx` — codi mort, no enrutat, endpoints 404. `App.jsx:20-21`.
- (O) `components/MeasurementTable/MeasurementTable.jsx` — cap import (conté mock `mock-1..5`). `App.jsx:22`.
- (O) `components/MeasurementsChat/MeasurementsChat.jsx` — zero importadors.
- (residu) 8 `SPRINT_S*_INTEGRATION.txt` + `placeholder.txt` a `frontend/src/components/`.
- (M) Botó "Nou model" del Topbar — `showNewModel=false` fix. `Topbar.jsx:32,100-119`.
- (M, redirect-only) `/models/:id/size-check`→`SizeCheckRedirect`. `App.jsx:48-55,145`.
- (stale) Comentari desfasat a `TechSheetEditor.jsx:537-539` (afirma que el serializer no exposa `template_json`, però sí). `tech_sheet_serializers.py:17`.
- (compat/potencialment mort) Branch `template_json['schemas']` (pdfme antic). `tech_sheet_serializers.py:26,31,48,53`.

## (e) ⚖️ Decisions per a l'Agus (consolidades)

> Una llista numerada amb TOTS els ⚖️ dels 16 dominis. Cada una és una pregunta de decisió. NO les decideix la diagnosi.

**Identitat / cicle de vida del model (dominis 1-3):**
1. ¿Eliminar definitivament `Client.actiu` (bool) i `Client.adreca_fiscal` (LEGACY) amb migració de dades, o mantenir-los per compatibilitat? `tenants/models.py:112,128`.
2. ¿Crear la "comanda futura" de cleanup de Client+schema orfe (Domain fallit / baixa amb `auto_drop_schema=False`)? Avui no existeix. `views_tenants.py:66-67`.
3. ¿Alinear `Plan.tipologia` (3 valors, enterprise) amb `Client.tipologia` (2 valors)? `tenants/models.py:27-31,61-64`.
4. ¿Retirar el camp `Model.estat` (mort, sempre 'Nou') o reconciliar-lo amb `fase_actual`? Avui dos eixos d'estat conviuen. `models_app/models.py:201`.
5. Bug `'En curs'` vs `'EnCurs'` a `pom/wizard_views.py:38`: ¿corregir a la constant o el camp ja és per esborrar?
6. ¿Unificar la meritació en UN servei d'entrada única (avui duplicada `services_c` / `reconcile_consumption`)? `services_c.py:95-114`; `reconcile_consumption.py:113-146`.
7. `ModelConsumptionEvent` sense lligam a model: clonar QA deixa events públics orfes i pot sobrecomptar (11 vs 6). ¿Que `clone_model_for_qa` purgui events públics, o idempotència per `(codi_client, model)` i no només `opaque_ref`? `clone_model_for_qa.py:83`; `receivers.py:11`.
8. ¿Consolidar la definició canònica de "model iniciat" = `consumption_started_at IS NOT NULL` (meritació), independent de `fase_actual != 'Pending'`? `services_c.py:91,97`.

**Identitat / usuaris (domini 2):**
9. ¿Qui pot congelar (design_freeze)? Avui qualsevol `IsAuthenticated` (inclòs technician); ¿cal capability dedicada (`close_gates` o nova `design_freeze`)? `pom/wizard_views.py:17`.
10. `permisos.grant`/`revoke`: ¿mantenir com a feature backend sense UI, exposar-ho a la matriu, o eliminar-ho? `capabilities.py:41-43`.
11. `rol_nom` CharField lliure vs choices/FK a taula de rols (vocabulari hardcodejat i replicat al front). `capabilities.py`; `UsersRoles.jsx:11`.
12. `TenantConfig.unitat_mesura`/`norma` vs config equivalent en altres dominis (talles/POM): ¿una única font de configuració del tenant?

**Tasques / planning / calendari (dominis 4-6):**
13. ¿Esborrar `Tasks.jsx` + ruta `/tasques` + `TascaViewSet` legacy (pàgina trencada, endpoint inexistent)? `App.jsx:150`; `views.py:18`.
14. ¿Jubilar `views_sprint1c.TascaViewSet`/`PaquetServeiViewSet` + doble registre `tasques/`, mantenint `PaquetServei` (FK viu des de `ModelServei`)? `tasks/urls.py:13-18`.
15. `TipologiaModel`: ¿substituïda pel motor de planning → DROP o conservar com a master-data? `tasks/models.py:74`.
16. ¿Unificar `Tasca.activa`/`is_active` (doble flag) i decidir sort de `slots_base/minuts_estandard/ordre` sense ús?
17. ¿Moure `PlanSnapshot` de `tasks/` a `planning/` (domini real)? Implica migració.
18. ¿Confirmar que el planificador NO re-aprèn sobre tasques ja creades (snapshot congelat), o cal re-snapshot per a Welford en viu? `scheduler_service.py:8,215`.
19. ¿Què fer amb `plan/compute|preview|apply|snapshots` (backend complet sense UI)? ¿Es preveu UI de previst-vs-real o es jubilen? `PlanSnapshot` no té cap lector que compari snapshot vs real.
20. Camps `working_minutes_per_day`/`blocked_dates` de PlanSnapshot (mai poblats) i `result.load_minutes`/`campaign_end` (no produïts): ¿netejar o implementar?
21. **BUG replicació diària:** ¿corregir al FRONT (que `inRange`/render no expandeixi un all-day multi-dia) o al BACKEND (emetre el grup de fitting de convocatòria com a UN marcador, com es va fer amb la confecció)? Avui confecció mitigada, fitting-convocatòria NO. `PlanningCalendar.jsx:171-178`; `planning/views.py:447-449`.
22. ¿Construir o eliminar la UI de `jornada`/`absencies` (el motor els llegeix, no hi ha entrada de dades)? `calendar_service.py:47-63`.
23. ¿Ombrejar festius oficials CAT al front (avui només `festius_extra`; el motor SÍ respecta workalendar) per eliminar la divergència front/back? `PlanningCalendar.jsx:17`.

**POM / grading / talles (dominis 7, 8, 12):**
24. ¿Eliminar `GarmentPOMMapEditor.jsx` (+ `HTMTooltip` si no s'usa)? Codi mort confirmat amb endpoints 404. `App.jsx:20-21`.
25. ¿Futur de `s9_views.setup_tenant_from_excel_view` (trencat, emmascarat per `except: pass`): reparar contra el schema real o retirar l'endpoint? `s9_views.py:179-191`.
26. ¿Esborrar o implementar escriptors per `POMEstadisticaGlobal`/`POMEstadisticaTenant` (taules òrfenes)? `pom/models.py:138-153,255-269`.
27. ¿Fer que `confirm_base_size_view` delegui a `close_base`/`get_or_create_size_fitting` en lloc de duplicar la màquina d'estats? `wizard_views.py:228-288`.
28. ¿`POMMasterViewSet` ha de tenir gate `CONFIGURE` a l'escriptura (a diferència de GarmentType/GarmentPOMMap)? `pom/views.py:44-53`.
29. ¿Resoldre la incoherència `GradingRuleHistory.pom → POMGlobal` vs `POMMaster`? `pom/models.py:829-830`.
30. FK legacy `GradingRuleSet.target`: ¿retirar-la ja (com SizeSystem a 0021) o mantenir el doble camí? Encara s'escriu i es clona. `size_map_views.py:572`; `s2_views.py:171,196`.
31. ¿Confirmar que `GradingException` (camí compartit/leak) es manté només per a seeds ISO o es deprecia per-model davant `ModelGradingRule`/`ModelGradingOverride`? `pom/services.py:92-100`.
32. ¿Alinear `db_constraint=False` a `PieceFittingLine.pom`/`GradedSpec.pom`/`POMAlert.pom` amb `SizeCheckLine`/`ModelGradingRule`? Risc d'integritat cross-schema. `fitting/models.py:346,175,119`.
33. Stale-spec detection (`generated_from_version` vs `measurements_version`): documentada, mai implementada. ¿Prioritzar? `fitting/models.py:182-186`.
34. ¿`SizingProfile` és el camí VELL a deprecar (grading ancorat a l'Item via `GarmentTypeItem.grading_rule_set`) o conviuen? Avui els dos s'escriuen. `pom/models.py:786`; `tasks/models.py:380`.
35. `GarmentTypeItem.grading_rule_set` NOT NULL: la 2a migració promesa està pendent. ¿Quan tots els items tinguin ruleset? `tasks/models.py:374-376`.

**Fitting / Size Check (domini 9):**
36. ¿Gating de `set_piece_gate`/`close`/`resolve_size_check`/`propagar`: exigir `schedule_fittings`/`execute_tasks` en lloc de només `IsAuthenticated`? Avui qualsevol autenticat regradua i versiona. `fitting/views.py:419-490`.
37. Brain stub: ¿implementar la propagació stale/reobertura o retirar el hook? `fitting/brain.py`.
38. Camps òrfens `SizeFitting.sf_pare`/`fills` i estats `Pendent`/`BaseOberta`: ¿retirar o cablejar?
39. `tipus` de SizeFitting sempre 'SizeSet' hardcoded: ¿les choices Proto/Fit/PP/TOP tenen futur o es retiren? (test usa 'PRINCIPAL', inexistent).
40. `advance_phase` (fitting) buidada i endpoint `advance-phase` exposat: ¿es retira l'endpoint? `fitting/views.py:161`.
41. Deute (b): ¿afegir `size_check_ref` al log F1 per traçar l'origen del canvi base CHECKED? `services_size_check.py:183`.

**Import (domini 10):**
42. ¿Retirar el camí VELL sencer (`extraction_service.py`, `EXTRACTION_PROMPT`, `extract_from_file_view`+`create_from_extraction_view`, rutes `urls.py:59-60`)? És el doble camí més clar.
43. Si es manté el camí vell, ¿migrar-lo a SDK + model actual (avui `claude-opus-4-5` via httpx cru)?
44. ¿Eliminar `historia_xat` i les entrades mortes de `_POM_SYNONYMS` (`:1042-1055`)?
45. ¿El wizard nou (W5) ha d'extreure imatges del PDF com el vell (`extract_images_from_pdf`), o es perd a propòsit? `extraction_service.py:234`.
46. ¿Aclarir nomenclatura oficial `BulkCollectionImport` vs la referència `BulkImport` del brief? `models_app/models.py:702`.

**Fitxa tècnica (domini 11):**
47. ¿Tancar el "timer gap": l'autosave (`/update/`) ha de renovar `locked_at`, o cal endpoint heartbeat/re-lock? Editar >30 min exposa a force-unlock de tercers. `tech_sheet_editor_views.py:163-165`.
48. ¿`TechSheet.estat` i `TechSheet.versio` s'implementen (workflow obert/tancat, increment de versió) o s'eliminen com a morts?
49. ¿Renombrar un dels dos "tech sheet" (S17 extracció IA vs editor persistent) per evitar confusió permanent?
50. ¿La plantilla ha de desar/propagar `pageFormat` perquè la fitxa creada n'hereti el format? `TechSheetTemplateEditor.jsx:107`.
51. ¿Eliminar el branch legacy `schemas` del serializer (migrar/confirmar 0 fitxes antigues) o mantenir per compat? `tech_sheet_serializers.py:26`.

**Backoffice / facturació (dominis 13, 15):**
52. ¿Tancar el cicle d'Invoice (`esborrany→emesa→pagada` + Stripe, Sprint 7) o deixar el motor com a càlcul intern? Avui genera factures que ningú llegeix per API. `backoffice/models.py:152`.
53. ¿Cablejar `BackofficeActionLog` (auditoria real) o eliminar-lo com a òrfena? `backoffice/models.py:37`.
54. ¿`Plan.preu_model_extra`/`models_inclosos`/`moneda_pla` (Sprint 2): eliminar (i migració del Plan) o re-connectar com a default del ContractLine? `tenants/models.py:46-48`.
55. Línies `manual` del catàleg (el motor les salta, sense via de creació manual): ¿cal endpoint de facturació manual o es descarta `tipus='manual'`? `billing_service.py:73`.
56. Contractes vigents solapats: ¿validar unicitat de vigència o acceptar el `.first()` silenciós? `billing_service.py:33`.
57. Rol `FACTURACIO`: ¿gating real de `facturacio/generar/` i factures a aquest rol, o eliminar-lo del `TextChoices`? `backoffice/models.py:20`.

**Frontend (domini 14):**
58. ¿Esborrar les 3 òrfenes (`GarmentPOMMapEditor.jsx`, `MeasurementTable.jsx`, `MeasurementsChat.jsx`) i els 9 `.txt`/`placeholder.txt`? `App.jsx:22`.
59. ¿Unificar el sistema d'icones del backoffice (webfont Tabler O `@tabler/icons-react`, no tots dos)? `frontend-backoffice/index.html:7`.
60. ¿Migrar `--gate` del backoffice (`#534ab7` lila) al verd canònic o assumir tema propi? `frontend-backoffice/src/index.css:30-31`.
61. Política "outline-only": ¿acceptar `ti-star-filled`/`ti-player-play-filled` com a excepcions o substituir-les?
62. ¿Campanya de des-hardcodejar hex cap a tokens i centralitzar l'amplada del sidebar (240) i l'offset staging en constants compartides?
63. ¿Botó "Nou model" del Topbar (`showNewModel=false`): retirar definitivament o reactivar? `Topbar.jsx:32`.

**Seeds / migracions (domini 16):**
64. Default `--source 162` a `clone_model_for_qa` (golden hardcoded PROD-fhort): ¿treure el default (fer `--source` obligatori) o resoldre per TAG/codi en lloc de pk? `clone_model_for_qa.py:32`.
65. `reconcile_tenant_poms` amb 19 ids hardcoded (one-shot ja aplicat): ¿arxivar/eliminar ara? `reconcile_tenant_poms.py:30`.
66. `reseed_tenant_fhort` OBSOLET: ¿eliminar del repo o refer des de BD viva? `reseed_tenant_fhort.py:2-7`.
67. `backfill_model_items` i `0027_data_fit_to_proto` (ponts vell→nou ja consumits): ¿retirar un cop confirmat que no queden models legacy?
68. Rutes Excel absolutes `/root/fhort-sessions/*.xlsx` dins commands de sembra: ¿versionar al repo o deixar com a dependència externa del servidor?
