# ESTAT_PROJECTE — FHORT Textile Tech (Capa de Projecte)

> **Actualitzat:** 2026-06-05 · **Servidor:** 178.105.217.125 (fhorttextile.tech, tenant `fhort`)
> **Stack:** Django 6 + django-tenants + PostgreSQL + DRF + JWT · React 19.2.6 + Vite + Nginx
> **Repo únic:** `agusti-fhort/fhorttextile`, branca `main`, a `/var/www/fhort-textile` (front + backend).
> **Servei:** `fhort.service` (Gunicorn). Intèrpret: `backend/venv/bin/python`.
> **Llengua:** treball en català · codi/UI anglès primari, català subtítol.
> **AQUEST SERVIDOR (178.105.217.125) = NOMÉS FHORT Textile Tech.** L'nginx d'aquí només serveix
>   `fhorttextile.tech` (vhosts `default` + `fhort-textile`; cap altre projecte). Les antigues "zones
>   intocables" `assessment`/`trading`/`webs` eren d'un **ALTRE servidor** (ERP Frappe, 178.105.48.204)
>   i **NO apliquen aquí**. Config de desplegament d'aquest servidor a `docs/deploy.md`.

---

## ACTUALITZACIÓ 2026-06-05 — Customer entity + Import massiu de col·lecció (bulk) + reconciliacions

### Commits recents (cec844e → c9bcbb7 = HEAD, verificats a `git log`)
| hash | data | resum |
|---|---|---|
| `cec844e` | 04/06 | Fix Garment Types: filtre `actiu` per defecte (oculta famílies inactives) |
| `eabe4d1` | 04/06 | **Customer entity** (`tasks.Customer`) + codi-gen de model unificat per client |
| `3bf08e9` | 04/06 | Pàgina **Clients** (`/clients`) + wizard de model **client-first** amb gate |
| `edcf8bf` | 04/06 | Refactor: extret component `CustomerSelector` |
| `80e09b7` | 04/06 | **Bulk import staging:** `BulkCollectionImport`/`BulkCollectionRow` + `ModelSequence` (comptador atòmic) |
| `90e19a7` | 05/06 | **Bulk import motor:** matching engine + generació de plantilla + pipeline d'import |
| `c9bcbb7` | 05/06 | **BulkImportWizard frontend** (stepper de 4 passos) |

### Funcionalitats implementades i COMPLETES (afegits d'aquest bloc)
- **Entitat Customer** (`tasks.Customer`, mirall esquelètic de `Supplier`): `codi` (3 chars, únic) =
  **font del prefix del `codi_intern`** dels models i abast de la seqüència. El tenant és **client d'ell
  mateix** (`is_self=True`, self-customer sembrat amb `codi = Client.codi_tenant`) → el codi-gen mai depèn
  de cap hardcode. Camp placeholder `codi_global` (ganxo per al registre cross-tenant del backoffice futur).
  Migracions tasks `0019`+`0020` (seed self-customer) + models_app `0032` (`Model.customer`).
  - **Codi-gen unificat per client:** `generate_model_code` deriva el prefix del `customer.codi` (camí
    manual = scan `MAX(sequencial)` al signal, sense canvis de contracte de l'API).
  - **Flux client-first** (front): pàgina **Clients** (`/clients`, `Customers.jsx` + `CustomerModal`) i
    **wizard de model** que demana el client primer (gate), amb component reutilitzable `CustomerSelector`.
- **Import massiu de col·lecció (bulk)** — N esquelets de model en una sola pujada d'Excel, **conceptualment
  separat de l'`ImportSession` single-model** del wizard de 5 passos. El **Customer és el context** de la
  importació (no una columna). Migració models_app `0033`.
  - **Staging** (`BulkCollectionImport` + `BulkCollectionRow`): flux `PUJAT → VALIDANT → PREVISAT → IMPORTAT
    / DESCARTAT`; cada fila desa `raw_data`, `estat` (OK/ERROR/AVIS/DUPLICAT), `errors` **llegibles pel
    client** i FK `model_creat` (enllaç al Model real, creat al commit parcial).
  - **`ModelSequence`** (comptador atòmic per `(customer, year, season)`, `unique_together`): el bulk
    **reserva un rang sencer** en una sola operació (`reserve_sequence_range`, `select_for_update`, mateix
    patró que `tasks/services_i.py`) → sense col·lisions de seqüencial en creació massiva. El `codi_base`
    d'un `GarmentSet` consumeix 1 número, igual que un model simple.
  - **Motor** (`bulk_import_service.py` + `matching.py`): matching `run_talles + target → SizeSystem`
    (`MatchResult` amb score 0..1, avisos no bloquejants, errors llegibles; ignora sistemes inactius/buits)
    + generació de plantilla Excel + pipeline d'import.
  - **Endpoints** (`bulk_import_views.py` + `urls.py`): `bulk-import/template/` (GET plantilla) ·
    `bulk-import/upload/` (POST staging+preview) · `bulk-import/<id>/commit/` (POST creació parcial) ·
    `bulk-import/<id>/errors-report/`.
  - **Front:** `BulkImportWizard.jsx` (stepper de **4 passos**), entrada des de `Models.jsx`.

### Reconciliacions de catàleg POM (xifres REALS a BD, tenant `fhort` 2026-06-05)
- **125 POMGlobal** (tots actius) · **144 POMMaster** · **19 POMMaster tenant-only** (`pom_global=None`)
  reconciliats via `reconcile_tenant_poms` (commit `72c3d42`). Maps POM dels **items baby autoritzats**
  (`author_baby_pom_maps`, `d3a7d73`). Catàleg canònic complet i estable. *(Nota: la xifra real de
  POMGlobal és 125, no 116.)*

### Falsos positius tancats (revisats — NO són bugs)
- **Assignació de tasques en bulk:** té **check explícit + `unique_together(model, task_type)`** (commit
  `34e7e62`) → **0 duplicats** possibles. No cal acció.
- **Modal de Planning:** **exclou `Done` per disseny** (el scheduler és Done-safe i les tasques finalitzades
  són immutables) → comportament correcte, no un defecte.

### Migracions cap (per app, actualitzades aquest bloc)
models_app `0033` · pom `0017` · fitting `0012` · tasks `0020` · planning `0002`.

---

## ACTUALITZACIÓ 2026-06-04 — Import Wizard + Catàleg POM nadó + neteja BD

### Commits recents (9e7ff11 → 75064db, verificats a `git log`)
| hash | data | resum |
|---|---|---|
| `9e7ff11` | 03/06 | POM System: Browser-assign per item + Catalogue read-only + neteja família→item (drop FK `garment_type`) |
| `11624f5` | 03/06 | Sprint B: tancament de taula (`Tancat`) + cicle de vida tasca POM (auto-iniciar en obrir, auto-tancar en finalitzar) |
| `e1469b5` | 03/06 | Catàleg POM +10 (flounce/yoke/estats) + camp nivell K/M/O/D + càrrega pertinença per item + correcció inch→cm + fix soft-delete POM + selecció teixit ISO |
| `34e7e62` | 03/06 | Grup A: `unique_together(model,task_type)` + calendari confecció marcador a data entrega + Kanban actius a dalt i auto-obrir |
| `046f7f7` | 03/06 | **Fase 1 robustesa extracció:** parse tolerant (`safe_json_parse`) + salvage per fila + `grading_status` no bloquejant (el grading mai tomba els POMs) |
| `1511a94` | 03/06 | Runs de talles comercials: command `seed_commercial_size_runs` (KIDS_AGE_COM + BABY_MONTHS_COM) |
| `aace69b` | 04/06 | Catàleg POM nadó +9 (peu/entrecuix/elàstic/half moon): command `seed_baby_poms` |
| `72c3d42` | 04/06 | Reconciliació POMMaster tenant-only: command `reconcile_tenant_poms` |
| `d3a7d73` | 04/06 | Pertinença POM items baby: command `author_baby_pom_maps` |
| `75064db` | 04/06 | **Wizard import 5 passos** (talles→POMs→mesures→teixit→guardar) + fix pantalla opcions manual/import |

### Funcionalitats implementades i COMPLETES (afegits d'aquest bloc)
- **Import Wizard de 5 passos** (`ImportWizard.jsx`, substitueix `ImportFromSheetWizard` jubilat). Importa
  una fitxa tècnica (PDF/Excel/imatge) **dins d'un Model existent**. Estat persistit a `ImportSession`
  (tenant). Verificat end-to-end contra l'API real (no validat visualment encara):
  - **W1 Talles** (`cribratge/` + `talles/`): Crida 1 barata (Opus, ~900 tokens, sense thinking) detecta
    nº models, tipologia, gènere, run de talles. **Gating bloquejant**: si una talla del document no té
    destí al run configurat → "Continuar" desactivat fins resoldre (treure talla o **Alinear** el run).
  - **W2 POMs** (`extraccio/` + `poms/`): Crida 2 (Opus 16k, visió) extreu POMs+valors+grading;
    `find_pom_master` (extret a funció de **mòdul** compartida) matcheja **nomenclatura client → POM canònic**
    (exact_code/synonym/description…); badge de confiança; activar/desactivar/afegir del catàleg.
  - **W3 Mesures** (`grading-preview/` + `mesures/`): taula editable POMs×talles amb valors del document;
    botó **Generar grading** que omple **només** talles buides via `preview_graded_specs` (motor reutilitzat,
    **sense persistir**); talla base ressaltada.
  - **W4 Teixit** (`teixit/`): formulari de teixit (camps de ModelFabric + ISO), opcional/skip.
  - **W5 Guardar** (`confirmar/`): **NORMES INAMOVIBLES** verificades — *mana el document* (crea NOMÉS
    BaseMeasurement dels POMs confirmats, **sense fusió de plantilla** i eliminant files buides preexistents);
    grading final **tancat** (SizeFitting `Tancat` + GradingVersion v1 + GradedSpec); **cap FittingSession**;
    PDF → **ModelFitxer(`Document`)** amb naming `{codi}_DOCUMENT_{NNN}` i **`versio_anterior`** (re-import = v2).
- **Fix pantalla d'opcions manual/import** (`ModelMeasurements.jsx`): ja **NO auto-salta a `manual`** quan el
  model té POMs; sempre espera que l'usuari triï. Excepció: taula **Tancada** → directe a vista lectura
  (nou flag `tancat` a `taula-mesures/`, des de `SizeFitting.estat='Tancat'`).
- **Fase 1 robustesa extracció** (`extraction_utils.py`): `safe_json_parse` (tolera fences/prosa/comes
  finals/el·lipsis) + `salvage_measurements` (recupera files POM una a una) → el grading malformat mai tomba
  els POMs. Usat per tot el wizard.
- **Catàleg POM nadó complet**: +9 POMs nadó + reconciliació tenant-only + pertinença a items baby + runs de
  talles comercials (KIDS_AGE_COM, BABY_MONTHS_COM).

### Pendents actius (ordenats per prioritat)
1. **Validació VISUAL end-to-end del wizard** (Kanban → obrir mides → Importar → W1..W5 → model amb mesures).
   El backend i les normes estan verificats a nivell de BD; falta la passada visual amb una fitxa real
   (la Brownie no és a la màquina).
2. **Decidir el flux d'extracció únic:** ara conviuen `extract-from-file` (vell) i `extract-sheet` (S17) a
   més del wizard nou. El wizard és el principal → jubilar/retirar els fluxos vells i el seu codi.
3. **SizingProfiles:** re-autoria cap a la nova estructura de 17 famílies (17 perfils encara apunten a l'antiga).
4. **POMBrowser-assign:** gate de permís + autorar els 23 items buits (8 famílies sense àncora).
5. **Pas 6 POM:** drop del FK vell `garment_type` a `GarmentPOMMap` (migració, quan POMBrowser-assign validat).
6. **Replanificació per endarreriment:** el motor empeny la cua; falta **disparador** (lazy en obrir vs cron).
7. **Trams 5 (calendari fittings schedule→open) i 6 (producció mostres + gate)** — diagnosticats, no construïts.
8. **3B-2** (pop-up de selecció múltiple a Planning) i **explotat per tècnic** de models repartits (validació visual).
9. **Neteja menor:** `TipologiaModel` jubilable, claus i18n velles, traduccions ca/es de les 17 famílies.

### Arquitectura actual (apps · models · estructura)
- **Apps backend** (`backend/fhort/`): `models_app` (10 models), `pom` (22, **shared+tenant**: els `*Global`
  viuen a `public`), `fitting` (8), `tasks` (14), `planning` (3), `accounts` (2), `tenants` (3, **shared**),
  `files` (1). django-tenants: `SHARED_APPS` (tenants, pom) vs `TENANT_APPS` (la resta).
- **Models clau:**
  - `models_app`: **Model** (esquelet + repositori; `garment_type_item` = baula del motor de temps),
    **BaseMeasurement** (mesura base per POM; `origen` IMPORTED/TEMPLATE…), **ModelFitxer** (fitxers amb
    versionat `versio`/`versio_anterior`, categoria `Document` per a la fitxa origen), **ImportSession** (NOU).
  - `fitting`: **SizeFitting** (contenidor de grading; estat `Tancat`) → **GradingVersion** (v1, `aprovada`)
    → **GradedSpec** (valor per POM×talla). **FittingSession**/**PieceFitting** = capa de proves (try-on),
    separada del grading.
  - `pom`: **POMGlobal/POMMaster** (catàleg), **GarmentPOMMap** (pertinença per `garment_type_item`),
    **SizeSystem/SizeDefinition** (talles amb edat/alçada), **GradingRuleSet/GradingRule**, **SizingProfile**.
  - `tasks`: **GarmentType/GarmentTypeItem** (17 famílies / 57+ items), **TaskType** (9), **ModelTask**,
    **TaskTimeEstimate** (matriu de temps), **TechnicianQueueOrder** (ordre manual de cua).
- **`ImportSession`** (`models_app`, migracions **0030**+**0031**, tenant-scoped): PK enter + `token` UUID;
  `estat` (INICI/CRIBRATGE/TALLES/EXTRACCIO/POMS/MESURES/MESURES_OK/IMPORT/CONFIRMAT/DESCARTAT);
  `document` FileField (`import_sessions/%Y/%m/`); FK `model`, FK `creat_per`, FK `tipologia_confirmada`
  (`tasks.GarmentTypeItem`); JSON `model_detectat`/`run_conciliat`/`poms_extrets`/`resultat`/`historia_xat`/`avisos`.
- **Endpoints wizard** (`extraction_views.py` + `urls.py`): `import-sessions/cribratge|<token>/talles|
  extraccio|poms|grading-preview|mesures|teixit|confirmar`. Helpers reutilitzats: `find_pom_master` (mòdul),
  `preview_graded_specs` (`pom/services.py`, no-persistent).
- **Migracions cap (per app):** models_app `0031`, pom `0017`, fitting `0012`, tasks `0018`, planning `0002`.

### Estat de la BD (tenant `fhort`) — BUIDAT 2026-06-04
**Tots els Models i dades dependents esborrats** (cascade des de Model, prèvia eliminació de FittingSession
per desbloquejar `PieceFitting` PROTECT): 14 Models + 168 BaseMeasurement + 294 GradedSpec + 6 GradingVersion
+ 4 SizeFitting + 3 FittingSession + 46 ModelTask + dependents. Counts ara **a 0** (Model, SizeFitting,
GradingVersion, GradedSpec, BaseMeasurement, FittingSession, PieceFitting, ModelTask, ImportSession,
ModelFitxer, GarmentSet). **Catàleg/config INTACTE:** POMGlobal 125 · POMMaster 144 · GarmentPOMMap 1529 ·
GarmentTypeItem 58 · GarmentType 59 · TaskType 9 · SizingProfile 17 · UserProfile 2. Tenant net per provar
el wizard d'import des de zero.

> ⚠️ Les seccions inferiors («ESTAT DE LA BD DE PROVA», «DADES DE PROVA AL TENANT») descriuen l'estat
> **anterior** a aquesta neteja i queden com a HISTÒRIC.

---

## MÈTODE DE TREBALL (rodat, respectar sempre)
- Diagnosi read-only → confirmació Agus → una peça → `manage.py check` / `npm run build` → un commit per peça.
- **Verificar `git log -1` després de CADA commit** (un commit es va perdre un cop i es va detectar tard).
- `git add` SELECTIU (repo únic: front i backend conviuen; no fer `git add .`).
- Migracions: ensenyar el fitxer de `makemigrations` abans de `migrate_schemas --tenant`; **auditar columnes
  reals** a la BD després (no fiar-se del missatge OK — quirk django-tenants).
- Peces que calculen dates/permisos: **provar amb sortida literal** i amb usuari sense permís (Montse
  technician), no només amb admin. Restart `fhort.service` després de canvis de backend.
- Documents de traspàs a `/root/fhort-sessions/` + mantenir aquest fitxer.

---

## ESTAT GENERAL — què està FET i desplegat

### 1. Capa de permisos (Opció A, sense migració)
- `capabilities.py`: `execute_tasks`, `define_tasks`, `schedule_fittings`, `close_gates`, `view_team_tasks`,
  `manage_users`, `configure`. `get_capabilities` = (ROLE_CAPABILITIES[rol] | grant) − revoke, des de
  `UserProfile.permisos` JSON `{grant, revoke, tasks}`. Allow-list de tipus de tasca per usuari (`tasks`),
  deny per defecte, bypass admin.
- Rols: technician {execute_tasks} · product_manager (+define_tasks +schedule_fittings) ·
  manager (+close_gates +view_team_tasks) · admin (ALL +manage_users +configure).
- Row-level scope a `ModelTaskViewSet.get_queryset` (sense `view_team_tasks` → només assignee propi).
- Enforcement per task_type: `define-tasks` (400) + `transition` (403), validat contra l'assignee.

### 2. Usuaris i rols (front, `/configuracio/usuaris`, gated manage_users)
- Matriu (abast/gestió via grant/revoke + tasques via permisos.tasks), filtres, bulk amb confirmació.
- Alta d'usuari (modal; login per USERNAME, password l'escriu l'admin). `UserViewSet`: List/Retrieve +
  PATCH + CREATE (create_user + signal crea profile) + `users/bulk/`.
- Usuari de prova: **Montse** (technician, user_id 13, password `Prova1234`).

### 3. Agregador by-model + Kanban mestre-detall (front, complet)
- `GET model-task-items/by-model/`: scope reusat, paginat, `?search=` (codi+nom), `?all=`,
  `?ordering=` (whitelist: nom_prenda, codi_intern, any, temporada, prioritat, data_entrada, data_objectiu,
  data_tancament, fase_actual, estat), filtres `temporada/estat/fase_actual/responsable(me)/garment_type/any/prioritat`.
  Files: `{model_id, model_codi, model_nom, fase, counts{pending,paused,in_progress,done}, prioritat,
  temporada, estat, data_objectiu, responsable_id}`.
- `KanbanTasks.jsx`: **5 columnes** (Models crema #fdf6ee + Pending/Paused/InProgress/Done blanques).
  Columna 1 cercable/ordenable/filtrable amb **scroll infinit**; selecció model → tasques en 4 estats.
  Filtre Responsable gated `view_team_tasks` (amagat per a tècnic). Reaprofita TaskCard/transicions/timer/
  toast 1-InProgress/403. Cartes de gate (Prioritat A) sintètiques de `gates/ready/` → `models/gate`.

### 4. Motor de planificació — BACKEND COMPLET (sprints A+B)
**Decisió clau:** motor determinista propi + llibreries de calendari (workalendar + python-networkdays) +
SVAR MIT per pintar. NO solver (Timefold descartat: cal JVM, lent en Python; el problema és determinista).
Fusió tram 8 (Planificador) + assignació en UN motor; `plan/compute` antic per-model-en-sèrie JUBILAT.

**Sprint A — calendari laboral (porta migracions):**
- `CompanyCalendar` (singleton/tenant): `horaris` JSON (trams per dia + pauses) + `festius_extra`.
  Horari REAL FHORT: dl-dj 08:00-13:00/14:00-17:00 · dv 08:00-15:00 · festius workalendar Catalunya.
- `UserProfile.jornada_override` (JSON, null = hereta empresa). Model `Absencia` (rangs simples).
- `calendar_service.py`: `next_working_slot` + `add_working_minutes(profile, start, minutes)` — primitiva
  provada (salta pauses/cap de setmana/festius CAT/absències). Endpoints `company-calendar/`,
  `users/<id>/jornada/`, `absencies/` (gated configure).
- Commits: 702cd5d, d8e2693, 09ba161.

**Sprint B — motor (porta migració):**
- `ModelTask.planned_start/planned_end/planned_locked` (migració 0015, columnes auditades).
- `scheduler_service.py`: motor determinista `schedule(qs, now, save)` → `{placements, warnings, models}`.
  Cua per tècnic; ordre prioritat (1=urgent) → data_objectiu → codi_intern; dins model per `default_order`.
  Durada = snapshot `estimated_minutes`. Locked = punt fix (tasques s'empenyen senceres al voltant).
  Warning si `planned_end > data_objectiu` o sense estimació/assignee. PROVAT amb dates reals.
- `plan_service.py` + endpoints `plan/compute` (refactor) + `plan/preview` (save=False, NO muta BD) +
  `plan/apply` (locked=True + desa). Tots gated `configure` (deny 403 provat amb Montse).
- Commits: 88ed31f, c1bffd2, e73efb2.
- **Assignació + recàlcul per cua sencera (commit 6e81cc7):** `assign_model` / `unassign_model` +
  `recompute_for_technicians` (recalcula TOTA la cua no-Done del/s tècnic/s afectat/s, com `apply` →
  **evita solapaments** amb la feina ja assignada; no recalcula "només el model"). Scheduler **Done-safe**:
  `schedule()` exclou `status='Done'` defensiu (no depèn dels cridadors). Endpoints `POST models/<id>/assign/`
  `{assignee_id, task_ids?}` i `POST models/<id>/unassign/` (treu assignee + buida `planned_*` + neteja
  `predicted_*`), gated `define_tasks`. Reassignar una tasca (PATCH `assignee` a `model-task-items`)
  recalcula les cues dels **dos** tècnics (el vell i el nou). Tasques **Done IMMUTABLES** (autor + finished_at
  + dates) en tots els casos — provat amb sortida literal.
- **Nota dates:** es desen UTC (USE_TZ, Europe/Madrid). El front de planificació pinta des del MOTOR (local);
  NO barrejar amb l'UTC del serializer de tasca.

### Catàleg TaskType (9 canòniques, tenant)
pattern_digit, pattern_cad (default_order 20), pattern_hand, scaling, marking, tech_sheet (default_order 60),
bom, pom, grading (name "Taula de talles"). `default_order` reals verificats (NO assumir).

---

## FRONT DE PLANIFICACIÓ (trams 0–2 FETS · tram 3 pendent)
**Decisió de Gantt/Calendar:** SVAR core MIT (`wx-react-gantt` + `wx-react-calendar`), React 19 OK. El core
MIT (timeline/drag/dependències/virtualització milers de tasques) és suficient; les features PRO
(working-calendar/auto-scheduling) NO calen perquè el motor és nostre. Frappe Gantt = pla B (100% lliure,
menys potent amb volum). Resta (DHTMLX/Bryntum/DevExtreme) = de pagament, descartades.

**Trams (0→2 FETS; 3 pendent):**
- ✅ **Tram 0 (backend mini):** `planned_start/end/locked` exposats al `ModelTaskSerializer` (read-only;
  comentari de fus UTC). `endpoints.js` complet: `plan.compute/preview/apply/snapshots`, `companyCalendar`,
  `jornada`, `absencies`. Commits 1ca18a4, 6662a26.
- ✅ **Tram 1A:** SVAR instal·lat (`wx-react-gantt` + `wx-react-calendar`, MIT, React 19 net, sense
  conflictes peerDeps). Pantalla **Calendari d'empresa** (`/configuracio/calendari`, gated `configure`,
  403-safe): editor de **trams horaris per dia** (7 files, inputs hora, +afegir/treure, validació
  inici<fi/solapaments). Commits 1b343f8, 4d60e7a.
- ✅ **Tram 1B:** secció **festius extra** (editor de dates) a la mateixa pantalla; desar envia
  `{horaris, festius_extra}` (anti-regressió verificada: no esborra horaris). Commit 3995dea.
  NOTA: `festius_extra` és **llista de dates ISO** (sense descripció; afegir-la requeriria canvi backend).
  **Jornada-per-tècnic i absències AJORNATS conscientment** (calendari únic per a tothom; el motor ja els
  suportaria). Vacances = es gestionen movent la data del model.
- ✅ **Tram 2:** pantalla **Planificació** (`/planificacio`, gated `define_tasks`/`configure`, 403-safe).
  Carpetes **Pendents** (models amb no-Done sense tècnic) / **Assignades** (totes les no-Done amb tècnic).
  Assignar model (bulk) → **pop-up** (tècnic + tasques opcionals) → `assign` → **compute automàtic**.
  Assignades: tècnic(s), data inici/temps estimat/data fi previstos, **flag "en risc"**
  (`planned_end > data_objectiu`), **mestre-detall** a tasques amb **autor de les Done** (col·laboració
  traçada). Desassignar (Done intactes). Reassignar tasca. Reaprofita el patró cerca/filtres del Kanban.
  Commits f1d02a2 (fix), e82bef1 (pantalla). Verificat visualment (admin + Montse 403).
- ✅ **Tram 3 — Peça 1 (code-splitting) FETA:** `React.lazy` + `<Suspense>` a `App.jsx` (Login i Shell
  eager; 27 pàgines lazy). Bundle inicial **746 kB → 394 kB (-47%)**, gzip 207→125 kB; chunks per ruta;
  avís Vite >500 kB desaparegut. Commits **4787b51** + **532685e** (estat).
- ✅ **Tram 3 — Peça 2 (CALENDARI propi) FETA.** **GIR DE DISSENY:** el **Gantt SVAR** es va construir
  (endpoint 2A + Gantt 2B) i es va **DESCARTAR** — problemes de render (tokens de format literals a la
  capçalera, color de risc no aplicat, tipografia desbordada, una fila per tasca) + ser **de pagament**
  (features PRO) + decisió de producte: una **vista de calendari tipus agenda** (com l'ERP de la clínica de
  psicologia) encaixa millor amb tasques curtes en horari laboral, és més entenedora, i prepara **capes
  futures** (fittings, fites de model) amb esdeveniments **linkables** a tasca/model. El calendari és **fet
  a mà en React pur** (sense llibreries), chunk lazy **15.8 kB**. Subpeces:
  - **2A (`a26396a`):** `GET plan/current` (read-only, scope `view_team_tasks`). Es manté **viu al backend**
    (el wrapper de client es va retirar en netejar el Gantt; l'endpoint segueix disponible).
  - **2B-cal-1 (`65f59b7`):** `GET calendar/events` — esdeveniment **UNIFICAT** `{id, tipus, start, end,
    titol, tecnic_id, tecnic_nom, color, link, en_risc, meta}` preparat per a capes futures (`tipus ∈
    tasca|fitting|fita`; avui només `tasca`). Reaprofita **`UserProfile.color_avatar`** (camp existent,
    default `#888888`) → **ZERO migració**. Scope al queryset (`view_team_tasks` → totes les cues; sinó
    propi profile). Dates **ISO amb offset +02:00**. `en_risc = localtime(planned_end).date() > data_objectiu`.
  - **2B-cal-2 (`230e1d3`):** calendari propi React — **graella laboral** (4 vistes Dia/Setmana/Mes/Llista)
    que llegeix `CompanyCalendar` (horaris mon..sun, trams `[["HH:MM","HH:MM"]]`, pausa = forat entre trams).
    Cel·les: **pausa** (gris ratllat) vs **no-laborable** (taronja pàl·lid `#f7ede0`) vs **avui** (daurat).
    Ruta **`/planificacio/calendari`** ungated (oberta a autenticats), menú al grup Tasques (visible al
    tècnic). **`Planning.jsx` (gestió, gated `define_tasks`/`configure`) INTACTE.**
  - **2B-cal-3 (`63e9614`):** esdeveniments sobre la graella — blocs amb **alçada per durada** (`HOUR_PX=60`,
    1px/min), **color per tècnic** (fons+vora+text), **risc com a OVERLAY** (anell + punt vermell, sense
    perdre el color del tècnic), solapaments en **lanes**, barra de **PILLS** per tècnic (filtre client-side),
    vista **Mes** (3 events + "+N") i **Llista** (badge "En risc"), **clic → `/models/<id>`**.
    **READ-ONLY** (cap edició; el drag entra a la Peça 3).
- ✅ **Tram 3 — Peça 3 (ORDRE MANUAL de la cua, drag individual) FETA.** L'usuari reordena models dins
  la cua d'un tècnic; el motor recalcula respectant aquest ordre. Subpeces:
  - **3A (`624d1f8`) — backend:** taula nova **`TechnicianQueueOrder(profile, model, position)`** amb
    **`unique_together (profile, model)`** (NO unique a `position` — la garanteix l'endpoint dins
    `transaction.atomic`). Endpoint **`POST plan/reorder/` `{assignee_id, model_ids:[...]}`** gated
    `define_tasks`: desa posicions + `recompute_for_technicians`. **Scheduler** respecta l'ordre manual via
    clau composta **`(0, position)`** si hi ha fila / **`(1, *ordre_natural)`** si no → manuals primer pel
    seu `position`, nous/sense-fila al final. L'ordre manual **SUBSTITUEIX** el natural i és **ESTABLE**;
    `en_risc` es manté (es calcula a la col·locació). Neteja d'òrfenes amb helper **`cleanup_queue_order`**,
    cridat a `unassign_model` i a la reassignació per-tasca (evita files orfes quan un model surt de la
    cua d'un tècnic). Migració **0002** auditada al tenant.
  - **3B (`d7fa76c`) — front:** tab **Assignades AGRUPAT per tècnic** (capçalera + llista per cua); **drag**
    de files amb **`@dnd-kit`** (un `SortableContext` **aïllat per grup** → no creua tècnics, coherent amb
    *"planificar ≠ reassignar"*). `onDragEnd`: `arrayMove` **òptic** → `plan/reorder` → `load()` (reconcilia
    les dates del recompute); **revert + toast** si falla. Ordre dins el grup per `predStart`. **Pendents** no
    draggables. **Models repartits** (`techIds>1`): **explotats per tècnic** (apareixen a cada grup amb dates
    calculades només sobre les tasques d'aquell tècnic) — implementat correcte però **NO validat visualment**
    (cap model repartit a les dades de prova actuals).
  - ⏳ **3B-2 (pop-up de selecció múltiple) AJORNAT** conscientment (refinament; la reordenació ja la cobreix
    el drag individual). Veure PENDENTS.

**LLIÇÓ CLAU — `assignee` és FK a `UserProfile`, NO a `User`:** mai assumir `User.id == UserProfile.id`
(coincideix avui per casualitat amb 2 usuaris; divergiria en escalar). Els serializers d'usuari
(`UserListSerializer`/`UserAdminSerializer`) ara exposen **`profile_id`**; el front mapeja i envia
`profile_id` com a `assignee_id` (selector, mapa de noms, payload) → desacoblat de `User.id`. Fix f1d02a2.

**Menú:** "Planificació" = fill del grup Tasques (gated `define_tasks`/`configure`); "Calendari d'empresa" =
fill de Configuració (gated `configure`).

---

## PENDENTS / DEUTE ANOTAT (no urgents)
- **Deute nou (sessió 2026-06-05, entitat Customer):**
  - **Rename `codi_client` → `referencia_client`** al `Model` (ajornat): la referència del client al model
    es diu encara `codi_client`, que ara xoca conceptualment amb `Customer.codi`. Renombrar (~20 llocs,
    canvi trivial mecànic + migració). No urgent.
  - **Feed de `MeasurementStat` (Welford) ha de passar a `model.customer.codi`** (`fitting/services.py:~211`,
    `update_client_profile(codi_client=model.codi_client, …)`): amb `Customer` ja existent, l'estadística
    s'ha de keyar per `model.customer.codi`, no per `model.codi_client`. **Canvi d'1 línia**, ajornat al
    sprint de mesures.
  - **Atomicitat del camí MANUAL del signal de codi-gen** (`generate_model_code`): fa **read-then-write
    sense lock** (scan `MAX(sequencial)`), a diferència del bulk (`select_for_update`). **Risc baix** (alta
    manual = 1 model, poca concurrència), ajornat.
- **3B-2 (pop-up de selecció múltiple) AJORNAT** (no descartat): *"defineix data d'inici del primer model"*
  → reordenar la selecció + **ancorar el primer**. Requeriria combinar `reorder` + `apply` (fixar data,
  `locked`) en una transacció (endpoint nou o dues crides). No crític: la reordenació ja la cobreix el
  **drag individual** (Peça 3B). Decisions de comportament pendents de tancar (data àncora `locked` vs
  indicació; selecció arbitrària vs col·lecció filtrada).
- **Models repartits entre tècnics:** l'**explotat per tècnic** a Planning està implementat però **pendent
  de validació visual** quan existeixi un model repartit real (cap a les dades de prova actuals).
- **Col·lecció:** NO existeix camp al Model → requereix camp nou + migració + poblar + filtre. Ajornat
  (es farà quan es refaci el Model).
- **Assignació a ModelSheet:** la cara "per model" de l'assignació, per quan es refaci ModelSheet (ara
  l'assignació la cobreix el motor: assignar = col·locar a la cua = planificar).
- **Auth per email:** ara login per username; tram futur transversal.
- **Endurir `transition`:** que comprovi `request.user == assignee` (avui la UI ho amaga però el backend no
  ho força).
- ~~**Code-splitting (React.lazy):** bundle ~747 kB i pujant. CRÍTIC quan entri el Gantt (Tram 3).~~
  **RESOLT** (Tram 3 Peça 1, commit 4787b51): 746→394 kB (-47%), pàgines lazy.
- **manualChunks de vendor:** optimització futura **descartada de moment** (guany marginal: el pes
  d'arrencada ja el va resoldre el code-splitting per ruta; el calendari és lazy i lleuger). **NO és deute.**
- **LIMITACIÓ — festius CAT al calendari:** la graella NO ombreja els festius oficials de Catalunya
  (`company-calendar/` només exposa `festius_extra`; els festius CAT viuen al motor via workalendar). El
  motor sí els salta → columna laboral buida aquell dia (p.ex. 24-juny Sant Joan). Solució futura: exposar
  els festius CAT resolts a `company-calendar/` (canvi backend menor).
- **CAVEAT colors de tècnic:** `UserProfile.color_avatar` té default genèric `#888888`; amb molts tècnics
  col·lidirien al calendari. Possible **2B-cal-1bis**: `get_next_color()` amb paleta fixa (12 colors, com la
  clínica). No cal amb 2 cues.
- **product_manager té `define_tasks` però NO `view_team_tasks`** → a Planning veu només les seves tasques
  (scope row-level). Decidir si product_manager ha de tenir `view_team_tasks` per assignar a l'equip.
- **Deep-link a fred a ruta protegida rebota a `/login`** (cursa `initAuth` al useEffect vs `ProtectedRoute`
  que renderitza amb `isAuthenticated:false`). Afegir estat de loading inicial / inicialitzar des de
  localStorage. Detectat fent les captures de verificació.
- **Festius extra amb descripció:** avui `festius_extra` és llista de dates ISO; afegir motiu = canvi backend
  menor (objectes en comptes de cadenes + ajustar el validador).
- **Botons Kanban a columnes estretes:** "Finalitzar" va just; resoldre en enriquir les fitxes del Kanban.
- **Garment Types finder 3 columnes** (POMs, tram futur).
- **Trams 5 (Calendari fittings: schedule→open, per dia), 6 (Producció mostres: request-production + gate
  obligatori)** — diagnosticats, no construïts.

---

## DECISIONS DE PRODUCTE CLAU (registre)
- Hub "Projectes" (Models, Kanban, Calendari, Producció mostres, Planificador). POMs = config tècnica.
  Configuració = General + Tipus de tasca + Proveïdors + Usuaris i rols + Calendari d'empresa.
- Kanban model-cèntric (primer el model, després les seves tasques); pensat per a escala (600 models).
- Usabilitat = filtrar i triar simple (sino entra en desús): cerca + ordre + filtres + scroll infinit.
- Motor: assignar = planificar (un sol motor). Tècnic veu dies; responsable veu Gantt amb dates/hores.
- Reposició = sobreescriu amb advertència + acceptació (drag → preview → apply); locked = punt fix.
- Prioritat: `Model.prioritat` 1-5 tal com està (1=urgent), sense A/B/C, sense migració.
- **Planificar en el temps ≠ reassignar tècnic:** la reassignació es fa entrant al model; el calendari/
  planificador només **ordena tasques i mostra dates de lliurament**. El **drag (Peça 3) serà NOMÉS
  reposició temporal**, mai canvi de tècnic.
- **Cost NO es modela al motor:** el sistema només extreu **temps**. El càlcul de cost queda per a la capa
  comercial (es deriva del temps per tècnic/tasca/model). **Cap camp de cost.**
- **Ordre manual de la cua = per (tècnic, model), NO per model:** un model pot estar **repartit** entre
  cues amb posicions diferents → per això una **taula `TechnicianQueueOrder(profile, model, position)`** i
  no un camp a `Model`.

---

## DECISIONS DE PRODUCTE / PRICING (registre nou)
- **Posicionament:** SaaS de **nínxol tècnic** (oficina tècnica digital + planificació de producció), **NO un
  PLM**. Complementa Centric/K3/Garem (que no fan la part tècnica), no competeix.
- **Comprador = direcció** (no el tècnic): valor = visibilitat de capacitat, dates i cost. *"No més dates de
  lliurament falses."* (Justifica els indicadors de direcció del Tram 3.)
- **Cost IA ~0,33 €/model** (trivial). Cost real = temps de suport (baix; es tecnifiquen processos coneguts).
- **Volums reals:** Brownie ~1.200 models/any; LOSAN ~2.400/any. Àncora de preu: ordre dels **30k€** (Garem).
  Model de preu: **tiers per volum anual + overflow per excés** (absorbeix l'estacionalitat).

---

## REGISTRE DE COMMITS (sessió 2026-06-01, branca main)
- Permisos/Usuaris/Kanban: 55ed54a, 50c668f, … , a0ac4b0 (agregador), 19377b9 (ordre+filtres),
  03faa51 (Kanban 5-col), b048904 (5 col iguals), be547ae (sort+filtres), ca6d1f5 (scroll infinit+Responsable gated).
- Sprint A (calendari): 702cd5d, d8e2693, 09ba161.
- Sprint B (motor): 88ed31f, c1bffd2, e73efb2; assign/unassign + recompute + Done-safe: 6e81cc7.
- Front planificació: 1ca18a4 + 6662a26 (Tram 0), 1b343f8 + 4d60e7a (Tram 1A), 3995dea (Tram 1B),
  f1d02a2 (fix profile_id) + e82bef1 (Tram 2 pantalla), 4787b51 (Tram 3 peça 1: code-splitting per ruta).
- Tram 3 Peça 2 (gir Gantt→calendari propi): 532685e (estat Peça 1) · a26396a (2A `plan/current`) ·
  *[Gantt SVAR 2B construït i DESCARTAT, no committejat]* · 65f59b7 (2B-cal-1 `calendar/events`) ·
  230e1d3 (2B-cal-2 graella laboral) · 63e9614 (2B-cal-3 esdeveniments) · bc26051 (2C estat).
- Tram 3 Peça 3 (ordre manual de cua): 624d1f8 (3A backend `TechnicianQueueOrder` + `plan/reorder`) ·
  d7fa76c (3B front drag per tècnic).

---

## ESTAT DE LA BD DE PROVA (tenant fhort)
Seed base: **12 models `FTT-SS26-0004..0015`** + **48 ModelTask planificades** (`planned_*`), **2 cues**
(Agus / Montse), **3 models en risc** (0004/0006/0011).
**Estat actual = POST-TEST 3A** (la BD s'ha deixat així a propòsit, útil per a 3B):
- Cua d'Agus **reordenada manualment** (files `TechnicianQueueOrder` per als seus models).
- Model **0004 (`FTT-SS26-0004`) DESASSIGNAT** (a Pendents) pel test de `cleanup_queue_order`.
Per tornar a **línia base** (48 tasques, 2 cues 24-24, sense ordre manual): reiniciar amb el bloc comentat
de `/root/fhort-sessions/seed_planning.py` **+ esborrar les files de `TechnicianQueueOrder`**.

---

## FASE DE CATÀLEGS I MODEL (pla original — HISTÒRIC)
> ⚠️ Pla inicial. **L'estat REAL i complet és a la secció «FASE DE CATÀLEGS I MODEL — COMPLETADA» al final del document.**

Objectiu: completar els catàlegs base amb UI d'edició i refer el funcional de Model (convergència).

**PRINCIPI TRANSVERSAL — coherència d'estil i estructura (val per a TOTES les pàgines noves):**
- Totes les pàgines noves segueixen el **MATEIX patró visual i estructural des de la construcció**:
  capçalera (títol + subtítol català), components comuns de taula/formulari/modal/botons, tokens de
  color i espaiat, tractament uniforme de **loading/buit/error**. **No reinventar per pàgina.**
- Abans de crear la primera pàgina nova (**TaskType editable**) es **fixa una PÀGINA-PATRÓ de
  referència** (candidates: les pàgines riques `/poms/grading` o `/poms/sizes`) que serà la plantilla
  explícita per a totes les noves, **inclosos els refer grans** (Garment Types, Model). *(Tria de la
  plantilla = decisió pendent, a tancar abans de TaskType.)*
- Al **tancament de la fase**: repàs general de consistència sobre tot el conjunt per unificar desviacions.

**Ordre d'execució (decidit):**
1. **Reordenació del menú lateral + neteja de duplicats i capes jubilades:**
   - **JUBILAR:** `Settings` antic (`configuracio/garment-types|size-systems|grading`) en favor de les
     pàgines riques (`/poms/sizes`, `/poms/grading`; garment-types es refà a nou). **Capa ANTIGA de
     fitting** (`/fitting`, `SizeFittingList/Detail`) jubilada en favor de `/fittings` (`FittingSession`).
   - **REAGRUPAR** el menú per famílies: **PROJECTES** (operativa) · **CONFIGURACIÓ TÈCNICA** (catàlegs)
     · **SISTEMA** (empresa/usuari). Avui la família de catàlegs està partida (POMs vs Configuració) i
     la planificació repartida en 3 llocs.
   - **Forats** per a pantalles noves: Catàleg de tasques (editable), Matriu de temps.
2. **TaskType (catàleg de tasques):** pantalla amb UI d'**EDICIÓ** (avui `/tasques/catalog` és vista).
3. **REFER Garment Types complet** (disseny antic desconnectat) + **GarmentTypeItems** + **MATRIU DE
   TEMPS** per (garment_type_item, task_type) — alimentaria el motor (avui `estimated_minutes` és
   manual). Peça gran amb disseny propi.
4. **Revisió/ompliment de catàlegs restants** segons calgui (Supplier si entra Production, etc.).
5. **REFER el funcional de Model** (ÚLTIM, convergència): llistat de models + fitxa amb pantalles d'estat
   (tasques, fittings, grading, planificació) + entrada Excel (ImportWizard existent) / manual +
   configuració de tipologia segons els catàlegs nous.

**DECISIONS:** Paquets de servei (`PaquetServei`/`Tasca`/`PaquetServeiTasca`) **DESCARTATS** (no apliquen,
sense pantalla). Capa antiga de Fitting i `Settings` antic **JUBILATS**.

---

## FASE DE CATÀLEGS — COMPLETADA
- **Peça 0** (`3ab51fb`): components base `ui/` (Center, Feedback, Modal, buttons) + Table i18n/token +
  migració Planning/PlanningCalendar. **Pàgina-patró fixada** (i18n, tokens, api/endpoints, Center/
  Feedback/Modal/Table, capçalera MONO).
- **Pas 1** (`f9d20bc`): menú en 3 famílies (PROJECTES / CONFIG TÈCNICA / SISTEMA) + jubilació `Settings`
  antic i capa Fitting antiga.
- **Pas 2** (`cc016cc`): TaskType editable (`/task-types`) + destroy 409 + `Tasks.jsx` aprimat.
- **Pas 3** (`028fd54`): Garment Types mestre-detall + matriu de temps integrada (items × 9 task_types)
  + gate GarmentType→CONFIGURE.
- **Pas 4A** (`8cdaaf5`): catàleg Suppliers (`/suppliers`) + destroy 409.
- **Pas 4B** (`d0bfebe`): confecció (Production) i fitting (FittingSession) al calendari (`calendar/events`
  + franja all-day a setmana/dia + chips a mes + avís tova fitting<expected_at). Decisions: data enviament
  = `requested_at`; scope visible a tothom; tipus `confeccio`/`fitting` amb `tecnic_id` null.
- **Reestructuració Garment Types** (`d8eb2e0`): **17 famílies + 57 items + 513 TaskTimeEstimate** (perfils
  L/M/P) + camp `descripcio` (GarmentType + Global). **Opció 2** (crear net + desactivar els 42 vells,
  SENSE esborrar → POM-maps/SizingProfiles intactes apuntant als vells). Seed antic jubilat (`.obsolete`).
  Accessoris descartats. Nadó ampliat (2 famílies).
- **Infra nginx** (fora git, a `docs/deploy.md`): `Cache-Control: no-cache` a index.html + immutable a
  `/assets/` + 404 real per assets inexistents (resol el *chunk stale*).

## PAS 5 — REFER MODEL (nucli COMPLETAT)
- **5A** (`1d783ea`): wizard d'esquelet **unificat** (identificació + família→ITEM + talles) + camps
  `collection`/`created_by`/`created_at` + jubilat camp `familia`. **BAULA DEL MOTOR activada:**
  `Model.garment_type_item` → `lookup_estimated_minutes` → `ModelTask.estimated_minutes` des de la matriu
  (provat end-to-end: model amb item → define-tasks → tasques amb minuts de la matriu).
- **5B + 5B-fix** (`66c9252`): **fitxa operativa.** Capçalera amb desplegable **Accions** (ActionsMenu) +
  estat/fase com a badge (sense stepper). Tabs com a **LOGS**: Resum·Mesures·Fitxers·Producció·Fitting·
  Anàlisi IA. Log de tasques al Resum (TaskTransition). Producció/Fitting informatius (el "Lliurat"=
  Delivered a Producció). **CICLE DE FASES: Pending·Dev·Proto·SizeSet·PP·TOP** (eliminat `Fit`; neix
  Pending). Fase = marcador **PARAL·LEL**, NO toca tasques (sempre obertes). **Auto-Dev** en arrencar 1a
  tasca (`transition_task`). Avançar/Retrocedir nets (`regress_phase` + `GateEvent.kind` advance/regress).
  Precondició fitting: `schedule_session` exigeix Production **Delivered** de la fase (bloqueig dur).
  `ModelTask` sense Cancelled. Menú: Kanban a primer nivell, Llistat de tasques jubilat (`Tasks.jsx` +
  `/tasques` orfes al repo). Topbar amb nom usuari + data + rellotge.
- **5C** (`1ca9176`): **llista de models refeta.** Layout fila/fitxa (2 files: descriptiva + operativa
  Fase/Entrada prod./Arribada proto/Fitting prev./Tècnic). **Selecció múltiple** (checks daurats,
  1=individual/N=bulk). Desplegable "Nou model" (manual / Excel pròximament). Desplegable **Accions**
  (ActionsMenu amb `targets[]`, bulk iteratiu + feedback agregat "X fet · Y omesos"; fitting aplica als
  elegibles). Dades **enriquides** (Subquery correlat per a les 3 dates + prefetch per al tècnic
  assignees, **sense N+1**). Filtre de fase corregit. Paginació configurable (`DefaultPagination`,
  `?page_size`). Checks daurats globals (`accent-color: var(--gold)` a index.css).

## DECISIONS DE PRODUCTE CLAU (Pas 5)
- **Model = esquelet** (wizard fins a talles) + **repositori del que va passant** (la fitxa). POM/sizing/
  grading es construeixen via **TASQUES**, a posteriori, no al wizard.
- **Tipologia del model = GarmentTypeItem** (`TipologiaModel` queda jubilable, no s'usa).
- **Combo-sets** (bikini, pijama, twin-set) = **1 item** cadascun (unitat de patronatge).
- **Fase paral·lela**, tasques sempre obertes; quan el model s'acaba, ningú hi torna si no se li demana.
- **Tècnic real = assignees de tasques** (`responsable` sovint null).

## SPRINT TASCA-POM — pertinença família→ITEM (FET · commit `452c723`, 2026-06-02)
**Fet i desplegat (tenant `fhort`):**
- **Pertinença POM moguda de família (`GarmentType`) a ITEM (`GarmentTypeItem`).** `GarmentPOMMap` amb FK
  `garment_type_item` (`db_constraint=False` — creua shared↔tenant: `pom` és SHARED, `tasks` tenant-only)
  + `pendent_revisio`. `garment_type` (família) queda **nul·lable** (drop diferit al Pas 6).
- **Seed** (`seed_pom_maps_to_items`): els 95 mapes vells = **àncores** d'item + **267 clons** de germans
  (clons `pendent_revisio=True` per ajust de delta). **362 mapes a item.** 23 items de **8 famílies sense
  àncora** queden BUITS (per autorar a POMBrowser).
- **Backfill** (`backfill_model_items`): 16 models legacy → `garment_type_item` assignat, família derivada.
  **16/16 coherents.**
- **Pont família tancat:** `Model.garment_type` deriva de `garment_type_item.garment_type`
  (`_resolve_garment_def`), per construcció.
- **Motor de grading únic:** `generate_graded_specs`. Grading inline de `set-measurements` **ELIMINAT**
  (bug `increment_cm` inexistent + ignorava `ModelGradingOverride`).
- **Materialització:** en obrir `/mesures`, els POMs de l'item s'instancien com a `BaseMeasurement` BUIDES
  (`origen='TEMPLATE'`, `base_value_cm=NULL`, `is_key`/`ordre` de plantilla). NO disparen log (guard al
  signal `base_value_cm is None`), NO s'esborren a guardar-talla-base. Endpoint
  `POST /models/<id>/materialitzar-poms/` (idempotent).
- **Porta d'entrada:** carta de tasca `pom` al Kanban → botó "Obrir mides" → `/mesures`. **Fitxa de model =
  consulta** (`EditableTable readOnly`) + enllaç "Editar a la tasca de POM".
- Migracions: pom `0014`/`0015` + models_app `0028`. **Eixos pertinença i grading independents.**

**Pendent d'aquest sprint:**
- **Pas 5:** jubilar `/garment-pom-map` (rutes App.jsx + menú; els seus endpoints `pom-map/*` són fantasma/404).
- **Pas 6:** drop del FK vell `garment_type` a `GarmentPOMMap` (migració, quan POMBrowser-assign validat).
- **POMBrowser-assign a `/poms`** (autoria de pertinença per Montse): llegir per item, matar `MOCK_POMS`,
  selector família→item, autorar els 23 items buits. **Backend ja llest** (`GarmentPOMMapViewSet` a item +
  filterset). Falta **gate de permís**.
- **Cicle de vida tasques Kanban:** auto-iniciar tasca en obrir-la, exclusió mútua (una en curs), auto-tancar
  en validar taula, ordenar models amb tasques actives a dalt.

## PENDENTS (anotats, no fets)
- **POM:** nucli **FET** — veure secció "SPRINT TASCA-POM". Pertinença a item, materialització TEMPLATE,
  motor únic, tasca com a porta. Les **95 GarmentPOMMap orfes ja repoblades** (àncores+clons a item).
  Resta: POMBrowser-assign (autoria Montse), Pas 5/6, cicle de vida Kanban (tot a la secció del sprint).
- ~~**5A-bis: import Excel → ESQUELET.**~~ **SUPERAT pel Import Wizard de 5 passos** (commit `75064db`,
  veure secció «ACTUALITZACIÓ 2026-06-04»): el wizard importa fitxa tècnica dins un Model existent.
  `ImportFromSheetWizard` + `ImportConfirmStep` **eliminats** (codi mort). Queda pendent **decidir el flux
  d'extracció únic** (`extract-from-file` vell / `extract-sheet` S17 / wizard nou) i retirar els vells.
- **Replanificació per endarreriment:** el motor ja empeny la cua; falta **disparador** (lazy en obrir vs
  cron). NO hi ha auto-pausa per horari ni infra de processos programats. Peça de planificació.
- **Neteja final:** extracció duplicada (`extract-from-file` / `extract-sheet`), orfe `Tasks.jsx`,
  `TipologiaModel`, claus i18n velles. *(`ImportConfirmStep`/`ImportFromSheetWizard` ja eliminats al `75064db`.)*
- **Traduccions ca/es** de les 17 famílies de Garment Types (ara `nom_ca`/`nom_es` = `nom_en` provisional).
- **POM-maps:** ✅ repoblats a item (sprint tasca-POM). **SizingProfiles:** re-autoria cap a la nova
  estructura de 17 famílies encara pendent.

## DADES DE PROVA AL TENANT `fhort` (a netejar al tancament)
- Seed planificació (`FTT-SS26-0004..0015`) + **model 131** (`FTT-FW27-0001`, complet amb item+tasques) +
  Production #3/#4 + FittingSession #9/#10 + models de verificació del 5A/5B/5C.
