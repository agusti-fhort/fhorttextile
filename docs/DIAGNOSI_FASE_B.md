# Diagnosi Fase B — Reencaix de FHORT al Model Viu

> **Document de DIAGNOSI (read-only).** Cap codi ha estat modificat per a la redacció d'aquest document. Només es descriu l'estat actual del sistema.
> **Nivell:** CONSERVADOR.
> **Font:** `DISSENY_MODEL_VIU.md` + investigació de codi sobre l'entorn *staging*, branca `dev`.
> **Convenció:** es distingeix sempre entre **fet** (amb referència `fitxer:línia`) i **proposta** (prefix `💡 PROPOSTA (a validar):`). Mai es barregen.

---

## 1. Resum executiu

**Centre de gravetat.** El sistema viu ha de tractar el **Model com a subjecte central amb patrimoni en dues dimensions: coneixement** (mesures, specs, decisions de fitting, fitxa tècnica) **i esforç** (temps, tasques, consum). Bona notícia: aquest patrimoni **ja existeix al codi** i és sòlid — `Model` és l'entitat central, `BaseMeasurement` guarda l'estat actual, `MeasurementChangeLog` és un log **append-only real** (rebutja UPDATE i DELETE), `TechSheet` i `ConsumptionRecord` viuen, i la cadena `Model→ModelTask→TimerEntrada` captura temps real. El que **falta no és el patrimoni sinó la seva lectura unificada**: no hi ha dashboard per-model ("on sóc / què ha canviat / atenció / què puc fer"), tot i que les fonts (log de mesures, timers, fase) ja hi són.

**Les 4-5 troballes més importants:**
1. **Col·lisió `SizeFitting` — RESOLTA per mapeig (Via A).** L'entitat `SizeFitting` del codi és el "contenidor-de-grading" (pare de les `GradingVersion`), **no** el "Size Fitting de talla base" del disseny, que és `SizeCheck`. No es fusionen, no es renombren: col·lisió purament de nomenclatura. Decisió CTO tancada.
2. **Fase repartida en 3 llocs independents** (`Model.fase_actual`, `FittingSession.fase`, `PieceFitting.gate`), amb **2 amos** de `fase_actual` malgrat un comentari que en proclama un de sol, i un mecanisme de sincronització **mort** (`recalculate_current_phase` no existeix, el signal es va retirar). La fase és poc fiable i contamina tota vista d'estat, gates i planificació.
3. **`GradingVersion` aprovada sense guard de segellat.** `close_piece_fitting` no comprova `aprovada` abans de crear `v+1`: una versió **segellada a producció es pot desactivar/substituir silenciosament**. És **risc de dades a producció avui** — únic ítem "corregir ara" de severitat alta junt amb la neteja de fase.
4. **Planificació no honesta + temps no agregable per model.** El recompute mai es dispara per maduresa/gates/progrés real (només per assignació i ocupació de fitting); `predicted_start/end` s'escriuen però **cap view els llegeix**; i el temps real s'agrega per cel·la i per tècnic, **mai per model** (es perd la FK). El snapshot de durada queda congelat i no aprèn.
5. **Menú del llenç i motor de patrons futurs.** Les 4 eines vives (fitxa tècnica, size set, fitting, POMs) són endpoints aïllats sense capa d'orquestració que projecti accions per fase/estat; el motor de patrons no existeix (futur íntegre, hexagonal).

**Què es reaprofita molt vs què és construcció nova.** Es **reaprofita molt**: RBAC (7 capacitats + 4 rols + overrides JSON, `HasCapability`), el scheduler determinista (`schedule`/`plan_service`/per-tècnic + override manual), el patró Welford (3 còpies), el log append-only de mesures, la màquina d'estats de tancament (`transition_task` + `TaskTransition` immutable + `rectification_count`), `GateEvent` i `regress_phase` (reversibilitat ja viva), i la **separació tenant/comercial** (frontera `opaque_ref`, ja sòlida — res a jubilar aquí). És **construcció nova**: dashboard per-model, arbre de dependències, tancament assistit binari, Watchpoint, capa de disseny formal + BOM + mortalitat, i la planificació per maduresa real.

**Decisions obertes i priorització.** Queden **15 decisions obertes (D-1..D-15)** + 1 lligada (D-OBERTA-1, dins del tancament assistit) + 1 resolta (col·lisió SizeFitting) + 2 deutes (T-1 traçabilitat, T-2 = D-2 enum). Es prioritzen en 3 blocs: **Bloc 1 Riscos/integritat** (D-1 guard de segellat, D-2 enum, D-3 fase mort) a **corregir ara, abans de tocar res**; **Bloc 2 Arquitectura** (catàleg dual, menú del llenç, planificació per maduresa, design freeze refós, permisos) a **decidir abans de sprint**; **Bloc 3 Construccions noves** (arbre, tancament assistit, intern/extern, Watchpoint, temps per model, motor de patrons, measurements_version) a **construir**. **Nota de consolidació:** les antigues D-10 i D-14 (totes dues sobre el design freeze) s'han **fusionat en una sola decisió** (D-7).

---

## 2. Col·lisió SizeFitting

### 2.1 Què demana el nou model

El disseny (`DISSENY_MODEL_VIU.md` §3.2, §7) distingeix **tres conceptes** de fitting que no s'han de confondre:

1. **"Size Fitting de talla base"** — valida la talla base del model. Segons el disseny, aquest concepte **NO propaga / NO escala** la resta de talles.
2. **"Grading Fitting"** — actua sobre **totes** les talles. Segons el disseny, **SÍ propaga / SÍ escala**.
3. El **contenidor per gate** — l'estructura que agrupa el treball de fitting d'una fase/gate.

El disseny avisa, a més, que en el codi ja existeix una entitat anomenada `SizeFitting` que **NO** correspon al "Size Fitting de talla base" del disseny, i que aquesta col·lisió de nomenclatura s'ha de resoldre **abans** de continuar amb la resta d'àrees.

### 2.2 Què hi ha avui (fets)

**Entitat `fitting.SizeFitting`** (`backend/fhort/fitting/models.py:7`):
- Camps: `model` (FK a Model, `related_name='size_fittings'`), `numero`, `codi` (`unique`), `tipus` (choices Proto/Fit/SizeSet/PP/TOP — a la pràctica només s'escriu `'Proto'` i `'SizeSet'`), `estat` (Pendent/BaseOberta/BaseTancada/TallesGenerades/Tancat), `sf_pare` (FK a si mateix, `related_name='fills'`), `base_tancada`, `data_tancament_base`.
- Constraints: `unique_together(model, numero)`; `codi` és únic global; **no hi ha cap unicitat per `tipus`**.

**Estructura morta:** `sf_pare` està **DECLARAT però MAI usat** enlloc (`fitting/models.py:27-33`).

**Relació 1→N amb GradingVersion:** 1 `SizeFitting` → N `GradingVersion` (`GradingVersion.size_fitting` FK, `fitting/models.py:63`). Una nova ronda de grading **NO** crea un `SizeFitting` nou: crea una `GradingVersion` `v+1` sobre el **MATEIX** `SizeFitting` (`fitting/services.py:349`, `fitting/services.py:433-437`).

**Singleton de facto per model:**
- `fitting/services.py:502` parla del *"single working SizeFitting"*.
- El signal `models_app/signals.py:109-121` crea 1 `SizeFitting` (`numero=1`, `tipus='Proto'`) si encara no n'hi ha cap.
- Però **estructuralment** la relació és 1 Model → N SizeFitting, i `extraction_views.py:1834-1838` pot crear un **2n** SizeFitting.

**`SizeFitting` NO té camp de fase/gate.** La fase real viu repartida en tres llocs:
- `Model.fase_actual` (`models_app/models.py:202`),
- `FittingSession.fase` (`fitting/models.py:229`),
- `PieceFitting.gate` (`fitting/models.py:291-309`).

El **veritable contenidor-per-gate** és `PieceFitting` (camps `gate`, `gate_per`, `gate_at`, `unique(session, model)`).

**Divergència d'enumeracions:**
- `Model.FASE_CHOICES`: Pending / Dev / Proto / SizeSet / PP / TOP.
- `SizeFitting.TIPUS_CHOICES`: Proto / Fit / SizeSet / PP / TOP.
- `'Fit'` (a TIPUS) vs `'Dev'` / `'Pending'` (a FASE) **no casen**.

**`SizeCheck` / `SizeCheckLine` = el "Size Fitting de talla base" del disseny** (`models_app/models.py:786-853`; `services_size_check.py:98-253`):
- `resolve_size_check`: en estat **Acceptat sense línies descartades**, escriu un `BaseMeasurement` amb `origen='CHECKED'` de la base; i **SI** `base_changed` **AND** el model té deltes → crea una `GradingVersion` nova, incrementa `measurements_version` i crida `generate_graded_specs(sf.pk)`, que **re-escala TOTES les talles**. És un **mirror** de `close_piece_fitting`.
- El `BaseMeasurement` generat pel SizeCheck **NO guarda referència estructurada** (`size_check_ref`): només text `'Size check · check {pk}'` (`services_size_check.py:182`).

**Grading Fitting = `GradingVersion` + engine + `PieceFitting`/`PieceFittingLine`:**
- Engine: `generate_graded_specs` (`pom/services.py:18-139`).
- `close_piece_fitting` (`fitting/services.py:341-476`) crea `GradingVersion` `v+1`, genera `GradedSpec` de totes les talles i crida el brain stub.
- Cadena: `SizeFitting (1)` → `(N) GradingVersion` → `(N) GradedSpec`; `PieceFitting` hi arriba via `grading_version.size_fitting` (`fitting/services.py:364`).
- **CONFIRMAT que escala totes les talles** (`pom/services.py:89`).

**Brain stub:** `brain.on_fitting_measurement_changed` és un **STUB** (*"no propagation yet"*, `fitting/services.py:455`). `measurements_version` només s'incrementa si `base_changed` (no en canvis només-override).

### 2.3 Taula de mapeig

| Concepte del disseny | Entitat de codi | Conflicte de nom? | Proposta |
|---|---|---|---|
| **"Size Fitting de talla base"** | `SizeCheck` / `SizeCheckLine` + `resolve_size_check` | **SÍ, crític** (el disseny diu "Fitting", el codi diu "Check"; col·lideix amb l'entitat `SizeFitting`) | 💡 PROPOSTA (a validar): fixar al glossari **"Size Fitting de talla base" ≡ `SizeCheck`**; **NO** renombrar `SizeCheck` amb "Fitting". |
| **"Grading Fitting"** | `GradingVersion` + engine + `PieceFitting` | NO | 💡 PROPOSTA (a validar): conservar; documentar que és un **procés sobre 3 entitats**. |
| **"contenidor-per-gate"** | `PieceFitting` | NO | 💡 PROPOSTA (a validar): conservar. |
| **"contenidor-de-grading"** | `SizeFitting` (entitat, singleton de facto) | **SÍ** (el nom suggereix "fitting de talles", però és el **pare** de les `GradingVersion`) | 💡 PROPOSTA (a validar): **Via A** desambiguar a glossari/UI, o **Via B** renombrar `SizeFitting` → `GradingContainer`/`ModelGrading` (cost alt). |

### 2.4 Resolució de la col·lisió

**Decisió de mapeig (no de codi):** l'entitat `SizeFitting` es mapeja al concepte **"contenidor-de-grading"** (pare de les `GradingVersion`), **NO** al "Size Fitting de talla base" del disseny — que correspon a `SizeCheck`. Les dues entitats **NO s'han de fusionar**. La col·lisió és **purament de NOMENCLATURA, no funcional**.

- **Via A (mínim risc, escollida):** conservar els noms de codi i desambiguar al glossari i a la UI.
- **Via B (neteja, cost alt) — DESCARTADA:** renombrar l'entitat `SizeFitting`. Es conserva aquí com a alternativa avaluada però no adoptada.

✅ **DECISIÓ CTO: Via A. Tancada.** (D-2 resolta, vegeu secció 12.)

### 2.5 Discrepància crítica

> **Decisió oberta de MOMENT (no de capacitat).** Lectura tancada-de-moment pel CTO; es resoldrà quan es dissenyi el "tancament assistit" (àrea Tasques). (Registrada també a la secció 12, D-1.)

**Lectura del CTO (tancada-de-moment):**

- El disseny vol la **propagació** (re-escalat de totes les talles) com a **DECISIÓ CONSCIENT de la tècnica**, **NO** com a efecte automàtic d'acceptar el size check.
- El codi **DIVERGEIX EN EL MOMENT (el QUI/QUAN), no en la capacitat**: `resolve_size_check` propaga **SOL en acceptar** (`services_size_check.py:213`, via `generate_graded_specs`) quan el model té deltes. Però el codi **SAP re-escalar bé** — la capacitat tècnica és correcta. El que falla és **QUI/QUAN decideix propagar**, no el càlcul.
- **NO es corregeix ara.** Es registra com a **decisió oberta** a resoldre **QUAN es dissenyi el "tancament assistit"** (àrea Tasques), on s'ubicarà el punt de decisió conscient.

**Naturalesa de la discrepància:** és de **MOMENT** (automatisme en acceptar **vs** decisió conscient de la tècnica), **NO de capacitat** (el motor de re-escalat funciona).

### 2.6 Decisions de reordenació

Registrades com a **fets de procés** de la diagnosi:

- **a)** Investigar la propagació (`SizeCheck` + `close_piece_fitting` **junts**) **ABANS** de gates, perquè `resolve_size_check` és un **mirror** de `close_piece_fitting`.
- **b)** A l'àrea Model, afegir la pregunta: com se sincronitza la "fase real" repartida en 3 llocs (`Model.fase_actual`, `FittingSession.fase`, `PieceFitting.gate`); `SizeFitting.tipus` **NO** és la fase real.
- **c)** Reenfocar l'àrea gates cap a `PieceFitting`, **no** `SizeFitting`.
- **d)** `sf_pare` és candidat a **codi mort** (baixa prioritat).
- **e)** Vigilar que els canvis **només-override NO** incrementin `measurements_version` (potencials specs obsolets no detectats).

---

## 3. Model i dashboard (Àrea 1)

### 3.1 Què demana el nou model

El **Model** és el subjecte central del sistema. Té patrimoni en **dues dimensions** que han de créixer i ser llegibles:

1. **Coneixement** acumulat (mesures, especificacions, decisions de fitting, fitxa tècnica).
2. **Esforç** acumulat (temps, tasques, consum de recursos).

A més, el disseny demana un **dashboard per-model** que respongui a quatre preguntes: **on sóc** (estat/fase), **què ha canviat** (diff temporal), **què requereix atenció** (alertes) i **què puc fer** (accions disponibles).

### 3.2 Què hi ha avui (fets)

**Entitat central `Model`** (`models_app/models.py:75`):
- `estat` (`ESTAT_CHOICES` `models_app/models.py:87`: Nou / EnCurs / EnRevisio / Tancat; default Nou; camp a `:201`).
- `fase_actual` (`FASE_CHOICES` `:94`: Pending / Dev / Proto / SizeSet / PP / TOP; default Pending; camp a `:202`).
- `design_freeze_at` (`:283`) + `design_freeze_by` FK (`:284`).
- `measurements_version` IntegerField default=1 (`:279`) — **STUB**: l'increment no està connectat encara de forma generalitzada.
- Config grading: `size_run_model` (`:264`), `base_size_label` (`:268`), `size_system` FK (`:186`), `grading_rule_set` FK (`:193`).
- Esforç: `slots_prev`/`slots_reals` (`:257-260`), `consumption_started_at` (`:204`).
- Index `[estat, fase_actual]` (`:321`).
- `related_names` que hi pengen: `fitxers`, `base_measurements`, `measurement_changes`, `grading_overrides`, `grading_rules`, `consumption_record` (O2O), `size_checks`, `tech_sheet` (O2O), `model_tasks`, `fitting_sessions`, `piece_fittings`, `peces`.

**Dimensió CONEIXEMENT (fets):**
- `BaseMeasurement` (`models_app/models.py:478`; camp `origen` `:520`, `ORIGEN_CHOICES` `:481`: STANDARD/IMPORTED/MANUAL/FITTED/CALCULATED/TEMPLATE/CHECKED; `unique(model, pom)` = **estat actual, no historial**) — **VIU**.
- `MeasurementChangeLog` (`:535`) — **APPEND-ONLY REAL**: `save()` rebutja UPDATE (`:576`), `delete()` sempre falla (`:582`); camps `valor_anterior`/`valor_nou`, `motiu` (`:554`), `created_by` (`:563`), `fitting_ref` FK→`fitting.SizeFitting` (`:557`), `fora_de_tolerancia` (`:561`, comentari *"drives re-opening propagation later"* = **stub**). **VIU**.
- `TechSheet` (`models_app/tech_sheet_models.py:14`, O2O; estat obert/tancat, `versio`, `template_json`, lock col·laboratiu) — **VIU**.
- `ModelGradingRule` (`:622`) — **STUB EXPLÍCIT**: comentari *"RES la consumeix encara"*.
- `ModelGradingOverride` (`:586`) — **VIU**.

**Dimensió ESFORÇ (fets):**
- `ConsumptionRecord` (`models_app/models.py:759`, O2O) — **VIU**.
- `TimerEntrada` (`tasks/models.py:116`) penja de **`ModelTask`, no de `Model`**; té `tecnic` + `minuts`. **VIU**.
- `TaskTimeEstimate` (`tasks/models.py:369`): cel·la `garment_type_item × task_type`, Welford (`n`/`mean`/`m2`); **NO per model**. **VIU**.
- `ModelConsumptionEvent` (`backoffice/models.py:63`, PUBLIC/SHARED).
- L'esforç **PER MODEL** SÍ és llegible avui via `consumption_delivery_view` (`models_app/views.py:1164`, URL `models/<id>/albara/` a `urls.py:177`): recorre `model.model_tasks` → timers, suma minuts per tasca i `per_tech`. Cadena `Model → ModelTask → TimerEntrada` (related `model_tasks` `tasks/models.py:205`). **VIU**.

**DASHBOARD (fets):**
- **NO hi ha dashboard unificat per-model** "on sóc / què ha canviat / atenció / accions".
- Peces parcials existents:
  - `consumption_delivery_view` (`views.py:1164`): albarà d'esforç + history de transicions de tasca (`:1208-1222`); cobreix temps/tasques/fase, **no** mesures. **VIU**.
  - `by_model` (`tasks/views_b.py:90`, GET `model-task-items/by-model/`): comptadors Kanban per estat + fase, multi-model. **VIU**.
- **DIFF TEMPORAL de MESURES**: `MeasurementChangeLog` existeix (append-only) **però CAP endpoint el serveix com a timeline per-model**. DELTA: el log existeix, el dashboard que el llegeix **NO**.

**FASE EN 3 LLOCS (troballa transversal, fets):** són **INDEPENDENTS**, cap signal/servei els sincronitza.
- `Model.fase_actual` té **DOS amos** malgrat el comentari `tasks/signals.py:6` (*"únic amo és fitting.advance_phase"*):
  1. `fitting/services.py:714` `advance_phase()` fa update.
  2. `tasks/services_d.py:36,:54` `advance_phase_gate()`/`regress_phase()` fan `model.save(update_fields=['fase_actual'])`; a més `tasks/services_c.py:91` (Pending→Dev), creació a 'Proto'.
- `FittingSession.fase` (`fitting/models.py:229`) = **INPUT** del request en crear sessió (`fitting/views.py:127,190,266,365`): l'usuari el tria, no es deriva.
- `PieceFitting.gate` (`fitting/models.py:309`) escrit només a `fitting/services.py:550` `set_piece_gate`; gate per peça independent.
- Pont real = **manual unidireccional** `advance_phase` (`fitting/services.py:647`→`:714`).
- Deute documentat `fitting/services.py:696`: `recalculate_current_phase` via signal — **PERÒ aquesta funció NO existeix** i el signal es va RETIRAR (`tasks/signals.py:1-7`): el TODO descriu un **mecanisme mort**.

### 3.3 Reutilitza / estén / jubila

- **REUTILITZA (viu):** `Model` com a subjecte central; `BaseMeasurement` (estat actual); `MeasurementChangeLog` (font del diff temporal, ja append-only); `TechSheet`; `ConsumptionRecord`; cadena `Model→ModelTask→TimerEntrada`; `consumption_delivery_view` i `by_model` com a fonts parcials d'un futur dashboard.
- **ESTÉN:**
  - 💡 PROPOSTA (a validar): un **endpoint de dashboard per-model** que agregui les 4 preguntes; pot reusar `MeasurementChangeLog` (timeline "què ha canviat"), `model.model_tasks`/timers (esforç), `fase_actual`/`estat` (on sóc) i les accions de fase/gate (què puc fer).
  - 💡 PROPOSTA (a validar): connectar l'increment de `measurements_version` (avui stub) als canvis de mesura rellevants.
  - 💡 PROPOSTA (a validar): connectar `fora_de_tolerancia` a la propagació/reobertura (avui stub, comentari `:561`).
- **JUBILA:**
  - `recalculate_current_phase` (TODO `fitting/services.py:696`) i el signal retirat (`tasks/signals.py:1-7`): **codi/TODO mort** a netejar.
  - `ModelGradingRule` (`:622`): stub no consumit; decidir si es desenvolupa o es jubila.

### 3.4 Què cal fer, com, quan, per què

- **QUÈ:** dissenyar el **dashboard per-model** i **reconciliar la fase repartida en 3 llocs**.
- **COM:** 💡 PROPOSTA (a validar): (a) endpoint agregador que llegeix les fonts vives; (b) decidir l'**únic amo** real de `fase_actual` i una funció de reconciliació explícita (no signal mort).
- **QUAN:** la reconciliació de fase és **prèvia** al dashboard "on sóc" (depèn que la fase sigui fiable); enllaça amb D-3.
- **PER QUÈ:** el patrimoni (coneixement + esforç) ja existeix però **no és llegible de forma unificada**; i la fase incoherent contamina qualsevol vista d'estat.

**Marcatge:** dashboard unificat = **futur**; `measurements_version`/`fora_de_tolerancia`/`ModelGradingRule`/`recalculate_current_phase` = **stub/mort**; la resta del patrimoni = **viu**.

---

## 4. Tasques / Kanban / arbre de dependències (Àrea 2)

### 4.1 Què demana el nou model

- **TaskType al codi / global / no-editable** (procés definit pel sistema, no pel tenant).
- **Arbre de dependències** "què dispara què" definit al codi.
- **Tancament assistit binari** amb preguntes dirigides (aquí s'ubica la decisió conscient de propagar — D-1).
- **Kanban de dues escales**: escala model vs escala plataforma.
- **Atribut intern/extern** per tipus de tasca, arribant al kanban operatiu.

### 4.2 Què hi ha avui (fets)

**CATÀLEG DUAL (troballa):** coexisteixen dos catàlegs sense FK entre ells:
- `Tasca` (catàleg "ric", `tasks/models.py:4-71`): editable **NOMÉS via Django admin** (`admin.py:10-14`), **sense API DRF**, **SENSE FK amb `ModelTask`**. Té `minuts_estandard`, `tipus_tasca` Interna/Externa/Validació (`:21-29`), `fase`, `gate`, `facturable`, `bloqueja_model`, `resultat_gate` OK/NO_OK/EXCEPCIO (`:53-57`). Docstring `:5`: *"Merges legacy TascaCataleg + process metadata"* — fusió **NO completada**.
- `TaskType` (catàleg "pla", `tasks/models.py:185-198`): **NOMÉS 4 camps** (`code`/`name`/`default_order`/`active`).
- El **kanban operatiu** (`ModelTask`) usa **`TaskType`**, no `Tasca`.

**`TaskType` és PER-TENANT i EDITABLE (fets):**
- És `TENANT_APPS` (`settings.py:70`), **no SHARED**.
- Editable via `TaskTypeViewSet` CRUD (`tasks/views_b.py:29-50`, ruta `task-types/` `urls.py:31`), escriptura gated per `DEFINE_TASKS`.
- Allow-list `get_allowed_task_types` existeix (`accounts/capabilities.py:57-71`).
- Durada viu **fora** del catàleg, a `TaskTimeEstimate`.
- **CONTRAST amb el disseny:** el disseny vol el procés **al codi / global / no-editable**; avui `TaskType` és **per-tenant i editable** de 4 camps. DELTA.

**ARBRE DE DEPENDÈNCIES: INEXISTENT/PLA (fets):**
- **Cap** FK self / M2M / taula / trigger entre `TaskType` ni entre `ModelTask`.
- Única ordenació **lineal**: `TaskType.default_order` + `ModelTask.order`.
- `PaquetServei`/`PaquetServeiTasca` (`models.py:134-182`) és una **llista plana ordenada** sobre `Tasca`, **no un arbre**.

**TANCAMENT (fets):**
- `transition_task` (`tasks/services_c.py:42-127`); ALLOWED (`:11-16`): Pending→InProgress, Paused→InProgress, InProgress→{Paused,Done}, **Done→InProgress** (reobertura = rectificació).
- `TaskTransition` és **LOG IMMUTABLE** (`models.py:237-253`, només create).
- `rectification_count` compta Done→InProgress (`services_c.py:130-133`).
- En tancar (→Done): tanca timer, `finished_at`, alimenta Welford `record_actual_time` (`services_c.py:121-125`); **NO** crea ronda nova vinculada.
- Gate de fase: `advance_phase_gate` avança fase quan **totes** les `ModelTask` són Done (`model_ready_for_gate` `services_d.py:11-17`).
- **TANCAMENT ASSISTIT binari: INEXISTENT** (grep negatiu de question/checklist/guided). `gate_model_view` (`views_b.py:391-414`) només `to_phase`/`notes`, **sense qüestionari**.

**KANBAN DUES ESCALES (fets):**
- Escala **model**: `ModelTaskViewSet` @action `by_model` (`views_b.py:90-213`).
- Escala **plataforma**: `gate_ready_models_view` (GET `gates/ready/` `views_b.py:461-473`) + list amb `scope_model_task_queryset` (`capabilities.py:74-95`).
- **No unificat** en un sol ViewSet.

**INTERN/EXTERN (fets):** **absent** de `TaskType` i `ModelTask`. Present **només** a `Tasca.tipus_tasca` (llegat) i `pom.TascaGlobal.tipus`; **no arriben** al kanban operatiu.

### 4.3 Reutilitza / estén / jubila

- **REUTILITZA (viu):** `ModelTask` + `TaskType` com a base operativa del kanban; `transition_task` + `TaskTransition` (log immutable) + `rectification_count` com a màquina d'estats de tancament; `advance_phase_gate`/`model_ready_for_gate` com a gate; les dues escales (`by_model` + `gates/ready/`).
- **ESTÉN:**
  - 💡 PROPOSTA (a validar): **arbre de dependències** (construcció nova): FK self/M2M o taula d'aristes "què dispara què" sobre `TaskType`/`ModelTask`.
  - 💡 PROPOSTA (a validar): **tancament assistit binari** amb preguntes dirigides sobre `transition_task`/`gate_model_view`; **aquí s'ubica la decisió conscient de propagar (D-1)**.
  - 💡 PROPOSTA (a validar): afegir **intern/extern** a `TaskType`/`ModelTask` (migrar de `Tasca.tipus_tasca`).
- **JUBILA / DECIDIR:**
  - Catàleg dual: 💡 PROPOSTA (a validar): completar la **fusió** `Tasca`→`TaskType` (o jubilar `Tasca` llegat) per evitar dos catàlegs paral·lels.

### 4.4 Què cal fer, com, quan, per què

- **QUÈ:** (1) resoldre el catàleg dual i decidir si `TaskType` passa a global/no-editable; (2) construir l'arbre de dependències; (3) construir el tancament assistit; (4) portar intern/extern al kanban; (5) unificar les dues escales.
- **COM:** 💡 PROPOSTA (a validar): un únic catàleg de procés, una taula de dependències, un endpoint de tancament amb qüestionari binari, i un ViewSet/serializer que serveixi les dues escales.
- **QUAN:** el **tancament assistit** és la peça on cau D-1 (propagació conscient), per tant té prioritat funcional; l'arbre de dependències és prerequisit del "què dispara què".
- **PER QUÈ:** avui el procés és **pla, editable pel tenant i sense dependències**; el disseny vol un procés **estructurat, global i amb tancament dirigit**.

**Marcatge:** `ModelTask`/`TaskType`/`transition_task`/gate = **viu**; arbre de dependències, tancament assistit, intern/extern al kanban = **futur**; `Tasca` llegat = **stub de fusió no completada**.

---

## 5. Fitting / gates / brain stub / SizeCheck (Àrea 3)

### 5.1 Què demana el nou model

- **4 gates** reversibles: Proto → Size Set → PP Sample → Producció.
- **Brain viu** per staleness / reobertura / watchpoints.
- **Watchpoint** com a entitat que **travessa gates**.
- **Segellat a producció** (la versió aprovada no s'ha de poder corrompre).

### 5.2 Què hi ha avui (fets)

**GATES (DELTA fort, fets):**
- `PieceFitting.gate` (`fitting/models.py:293-298`) choices Pendent/OK/NO_OK/EXCEPCIO = **4 valors de DECISIÓ per peça**, **NO** els 4 gates de fase del disseny.
- Les **FASES reals** viuen a `Model.fase_actual` (**6 valors**: Pending/Dev/Proto/SizeSet/PP/TOP, `models_app/models.py:94-101`).
- `GateEvent` SÍ existeix, **però a l'app TASKS, no fitting** (`tasks/models.py:256-275`: `from_phase`/`to_phase`/`kind` advance|regress/`by`/`notes`/`at`).
- **Reversibilitat VIVA:** `regress_phase` (`tasks/services_d.py:44-58`, + `GateEvent` regress, guard de fase anterior vàlida); endpoint POST `models/<id>/regress/` (`views_b.py:419-433`).
- **Doble camí d'avanç:** `tasks/services_d.py` `advance_phase_gate` (**sense** sessió) vs `fitting/services.py:647` `advance_phase` (**amb** sessió, **segella `GradingVersion`**, + `GateEvent` *"via fitting"* `:714-727`).
- `PieceFitting.gate` ↔ `fase_actual`: relació **indirecta**; el gate de peça és **precondició** (`session_can_advance` bloqueja si hi ha peces Pendent/NO_OK, `services.py:669-670`).

**GradingVersion / segellat (fets):**
- Cicle: `is_active`/`version_number`/`aprovada`/`aprovada_per`/`data_aprovacio` (`fitting/models.py:62-92`).
- `aprovada=True` = **segellat producció**, posat **només** per `advance_phase` (`services.py:707-710`).
- Canvi tardà **SÍ** genera `v+1`: `close_piece_fitting` desactiva les actives + `v = max+1` `is_active=True` (`services.py:433-444`).
- **PROBLEMA CRÍTIC:** **NO hi ha protecció contra superar una versió aprovada**. `close_piece_fitting` (`services.py:341-475`) **NO comprova `aprovada`** abans de crear `v+1`: una versió **segellada a producció** pot ser **desactivada/substituïda sense guard ni avís**. El comentari reconeix una *"legacy multi-active anomaly"* (`services.py:431-433`).

**BRAIN STUB (fets):**
- `fitting/brain.py` = **33 línies**. **UN únic hook** `on_fitting_measurement_changed` (`brain.py:16-32`) = **STUB pur** (`logger.info` + `return None`, **zero propagació**), cridat des de `close_piece_fitting` quan hi ha canvi (`services.py:456-462`).
- **CAP altre hook**: no staleness, no reobertura, no watchpoints.
- **Asimetria:** el mirror `SizeCheck` **NO crida el brain**.

**SIZECHECK accept/reject (VIU, a `models_app`, fets):**
- Estats Pendent/Acceptat/Rebutjat/Descartat (`models_app/models.py:789-794`).
- `resolve_size_check` (`services_size_check.py:98-253`): acció Acceptat|Descartat (`:123`); estat final segons decisions de línia (valor_descartat→Rebutjat **no propaga**; sense→Acceptat **propaga** `:142-146`).
- `_reagenda_tasca_size_check` **VIU** (`:256-282`): en Rebutjat/Descartat amb `data_represa` fixa `planned_start`/`planned_end`.
- **Gate tou:** tanca Kanban en Acceptat (`:216-230`, `ModelTask` size_check → Done).

**WATCHPOINT (fet):** **NO EXISTEIX enlloc** (0 matches a backend i frontend). **DELTA TOTAL.**

### 5.3 Reutilitza / estén / jubila

- **REUTILITZA (viu):** `Model.fase_actual` (6 fases) com a font de fase; `GateEvent` (log d'avanç/regrés ja existent); `regress_phase` + endpoint (reversibilitat ja viva); `GradingVersion` (cicle de segellat); `resolve_size_check` + `_reagenda_tasca_size_check` (accept/reject viu).
- **ESTÉN:**
  - 💡 SUPÒSIT a validar: **cal un guard** que impedeixi superar (desactivar/substituir) una `GradingVersion` `aprovada` abans de crear `v+1` (D-4).
  - 💡 PROPOSTA (a validar): mapeig **explícit** dels "4 gates" del disseny sobre les 6 fases de `Model.fase_actual` (no sobre `PieceFitting.gate`).
  - 💡 PROPOSTA (a validar): desenvolupar el **brain** (avui 1 hook stub): afegir staleness, reobertura i watchpoints; i fer-lo **simètric** (que el `SizeCheck` també el cridi).
  - 💡 PROPOSTA (a validar): **Watchpoint** com a entitat nova que travessa gates (construcció nova, DELTA total).
- **JUBILA / DECIDIR:**
  - Unificar el **doble camí d'avanç** (`advance_phase_gate` sense sessió vs `advance_phase` amb sessió) — enllaça amb D-3.

### 5.4 Què cal fer, com, quan, per què

- **QUÈ:** (1) protegir el segellat a producció (guard sobre `aprovada`); (2) mapejar els 4 gates del disseny a les fases reals; (3) desenvolupar el brain; (4) crear Watchpoint.
- **COM:** 💡 PROPOSTA (a validar): guard a `close_piece_fitting`/`resolve_size_check` abans de `v+1`; capa de mapeig gates↔fases; ampliar `brain.py` amb hooks reals i fer-lo simètric; nou model Watchpoint amb FK a gate/fase.
- **QUAN:** el **guard del segellat (D-4) és urgent** (risc de dades a producció avui). El brain i el Watchpoint són construcció posterior; depenen de la reconciliació de fase (D-3).
- **PER QUÈ:** avui una versió aprovada es pot corrompre silenciosament; el brain no propaga res; els watchpoints i el concepte de "4 gates" no existeixen.

**Marcatge:** `regress_phase`/`GateEvent`/`GradingVersion` cicle/`resolve_size_check` = **viu**; guard de segellat = **DELTA crític**; brain = **stub**; Watchpoint = **futur/inexistent**.

---

## 6. Eines i integració (menú del llenç) (Àrea 4)

### 6.1 Què demana el nou model

El disseny demana un **"menú del llenç"** del model: un conjunt d'**eines** (fitxa tècnica, size set, fitting, POMs, disseny de patrons, motor de patrons), distingint **internes/externes**, **orquestrades per fase/estat** del model. És a dir, no un grapat d'endpoints aïllats, sinó una capa que projecti **quines accions/eines estan disponibles** per a un model segons on és.

### 6.2 Què hi ha avui (fets)

**Inventari eina → entitat → endpoint → estat → consumeix temps:**

| Eina | Entitat | Endpoint(s) principals | Estat | Consumeix temps? |
|---|---|---|---|---|
| **Fitxa tècnica** | `TechSheet` (`models_app/tech_sheet_models.py`) | `models/extract-sheet/`, `models/create-from-sheet/`, `models/<id>/tech-sheet/` +lock/unlock/update, `customers/<id>/tech-sheet-template/` (`models_app/urls.py:139-157`) | **VIU** | **NO** |
| **Size set** | `SizeFitting` + `generate_graded_specs` (`pom/services.py`) | `models/<id>/generar-grading/` (`models_app/views.py:1039`, crida `generate_graded_specs(sf.id)` `:1079`); ViewSet `size-fittings` (`fitting/views.py:55`); `graded-table` (`fitting/urls.py:66`) | **VIU** | **NO** |
| **Fitting** | `FittingSession`/`PieceFitting` (`fitting/views.py`) | routers `fitting-sessions`/`piece-fittings`/`piece-fitting-lines`/`fitting-photos` (`fitting/urls.py:43-46`); convocatòria per UUID `group/<uuid>/reschedule|add-model|remove-model|attendees` | **VIU** | **NO** |
| **POMs** | `POMMaster` (app `pom`) | `poms/suggerits|cerca|crear-tenant|<id>/nomenclatura/`, `size-map/lookups|match|preview|grading-preview|create|systems/` (`pom/urls.py:38-64`); des de model `models/<id>/poms-suggerits|materialitzar-poms/` | **VIU** | **NO** |
| **Disseny de patrons / Motor** | **CAP entitat, CAP app, CAP endpoint** | — | **FUTUR íntegre** (`MOTOR_DE_PATRONS.md:388 §9`: PAT-0 parser+visor, PAT-1 anotació) | — |

**TROBALLA — les 4 eines vives NO generen consum de temps:** el temps viu en un **eix SEPARAT** (app `tasks`): `ModelTask` es crea a `tasks/views_b.py:287` (alta manual) i `planning/plan_service.py:282` (scheduler); `TimerEntrada` a `tasks/services_c.py:20`. **Cap eina del llenç està acoblada al cronòmetre.**

**MENÚ DEL LLENÇ — NO existeix cap noció unificada:** grep `canvas|llenç|menu.*eina|available.*action` a backend i `frontend-backoffice` = **0 matches**. Cada eina és un **endpoint aïllat** repartit en 4 apps (`models_app`/`fitting`/`pom`) + wizard. **Cap endpoint retorna les accions disponibles** per a un model segons la seva fase/estat. **DELTA:** eines disperses **sense capa d'orquestració/menú**.

**MOTOR hexagonal:** el doc (`MOTOR_DE_PATRONS.md:151 §3.4`, `:506`) diu *"Hexagonal NOMÉS al motor de patrons"*; avui **res hexagonal al codi** (Django/ORM clàssic). El "motor d'scheduling" (`planning/`) és **planificació de temps, NO el motor de patrons**, ni és hexagonal.

**Metadada dispersa (fets):**
- `TaskType` **NO** té cap camp `pattern_*` (només `code`/`name`/`default_order`/`active`); això és futur PAT-1.
- La metadada de **PROCÉS** (fase/gate/facturable/tipus_tasca/bloqueja_model) viu al model **llegat** `Tasca` (`tasks/models.py:4-72`).
- La metadada de **PATRONATGE per tipologia** (familia, garment_type, complexitat, **patrons_aprox**, slots CAD/digitalització/des-de-zero/conf-proto) viu a `TipologiaModel` (`tasks/models.py:74-112`) — **font real** dels "patrons aprox" i de la càrrega CAD.

### 6.3 Reutilitza / estén / jubila

- **REUTILITZA (viu):** les 4 eines vives (`TechSheet`, `SizeFitting`+`generate_graded_specs`, `FittingSession`/`PieceFitting`, `POMMaster`) com a accions del llenç; `TipologiaModel` com a font de patrons_aprox/càrrega CAD.
- **ESTÉN:**
  - 💡 PROPOSTA (a validar): una **capa d'orquestració** que **projecti les eines disponibles** per a un model segons fase/estat (el "menú del llenç" inexistent avui).
  - 💡 PROPOSTA (a validar): consolidar la metadada de procés/patró (avui dispersa a `Tasca` llegat + `TipologiaModel`) cap a un model coherent.
- **JUBILA / DECIDIR:** enllaça amb D-5 (catàleg dual): la metadada de procés a `Tasca` llegat és candidata a fusió.

### 6.4 Què cal fer, com, quan, per què

- **QUÈ:** (1) crear la capa d'orquestració "menú del llenç"; (2) decidir on viu la metadada de patró/procés; (3) ubicar el motor de patrons (FUTUR PAT-0+).
- **COM:** 💡 PROPOSTA (a validar): un endpoint que, donat un `model_id`, retorni les eines/accions disponibles segons `fase_actual`/`estat`; el motor de patrons com a mòdul hexagonal separat (segons `MOTOR_DE_PATRONS.md`).
- **QUAN:** el menú d'orquestració depèn que la fase sigui fiable (D-3) i que les eines existents quedin inventariades; el motor de patrons és construcció **futura** independent (PAT-0+).
- **PER QUÈ:** avui l'usuari no té cap vista unificada del que pot fer sobre un model; les eines existeixen però estan disperses i no es deriven de l'estat.

**Marcatge:** `TechSheet`/`SizeFitting`/`FittingSession`/`POMMaster`/`TipologiaModel` = **viu**; menú del llenç / capa d'orquestració = **futur/inexistent**; motor de patrons + hexagonal = **futur íntegre (PAT-0+)**.

---

## 7. Calendari / planificació (Àrea 5)

### 7.1 Què demana el nou model

- **Planificació honesta** que **recalcula la data per maduresa real** del model (no només per assignació).
- **Lectura per model** (el pla d'un model concret).
- **Dashboard del PM en temps real**.

### 7.2 Què hi ha avui (fets)

**SCHEDULER (VIU, fets):**
- `schedule(model_task_qs, now, save)` (`planning/scheduler_service.py:117`): **motor determinista sense solver**.
- Durada via `t.estimated_minutes` **snapshot** (`:215-218`); ordre via `_model_sort_key` (entre models) + `_task_sort_key` (per `task_type.default_order`) (`:47-58`).
- Col·loca **en sèrie** amb `_place` sobre `calendar_service` (`:80-92`). Desa `planned_start`/`planned_end` a `ModelTask` (`:241-243`) i **agrega** `Model.predicted_start`/`predicted_end` DateField (`:244-246`, `models_app/models.py:228-229`). **Unitat = `ModelTask`**.
- `PlanSnapshot` (`tasks/models.py:390`) = **foto immutable** previst-vs-real (`plan_service.py:79-85`); històric, **no** font del Gantt vigent.
- Orquestració `plan_service.py`: `compute_and_save` (`:88`), `preview` (`:111`), `apply` (`:151`), `recompute_for_technicians` (`:48`).

**PER TÈCNIC (fets):** el scheduler ordena **per tècnic** (`by_tech` `:163-168`, cua **independent** per tècnic; docstring `:3-4`). Ordre dins la cua: `TechnicianQueueOrder` (override **manual**, `_manual_positions` `:61-69`) o **natural** (`_model_sort_key`: prioritat → data_objectiu → codi). Reorder via `plan_reorder_view` (`views.py:494`).

**LECTURA PER MODEL — parcial/STUB (fets):**
- **No hi ha endpoint "pla d'un model".** El Gantt vigent `plan_current_view` (`views.py:167`) llegeix `ModelTask` amb `planned_start` agrupat per model/task_type, **query GLOBAL** (scope per perfil), **no per `model_id`**.
- `Model.predicted_start`/`predicted_end` **es DESEN però CAP view els llegeix** (només definició `models_app/models.py:228-229`).
- **DELTA:** no hi ha **lectura per-model de primera classe**.

**DURADA — snapshot congelat (fets):**
- Durada = snapshot `ModelTask.estimated_minutes`, **NO cel·la viva** (`scheduler_service.py:215-218`, docstring `:8`).
- El snapshot **es congela en CREAR la tasca** via `lookup_estimated_minutes` (`tasks/views_b.py:286-289`) que passa per `effective_minutes` (`services_i.py:49-53`: Welford si `n>=5`, sinó seed).
- `TaskTimeEstimate`/`effective_minutes` **només s'usen en crear** la `ModelTask`, **no en re-planificar**.
- `record_actual_time` (`services_i.py:18`) alimenta Welford en completar (`services_c.py:121-125`) → millora futurs snapshots de tasques **NOVES**, **però NO actualitza `estimated_minutes`** de tasques ja creades ni dispara recompute.
- **DELTA:** la planificació **no s'auto-ajusta** amb l'aprenentatge de temps real (snapshot congelat).

**MADURESA → DATA — INEXISTENT/FUTUR (fets, DELTA gran):**
- **NO hi ha recompute disparat per maduresa / gates / fitting-result / completació.** Recàlcul **estàtic** fins a trigger explícit. **Cap signal/post_save a `planning/`**.
- `recompute_for_technicians` (`plan_service.py:48`) recalcula la cua **sencera** del tècnic; disparadors **imperatius**: reassignació (`tasks/views_b.py:253`), `assign_batch` (`plan_service.py:335`/`375`), endpoint `plan_recompute` (`views.py:523`), fitting (`fitting/services.py:184`/`268`/`607`/`764` en ocupar/alliberar franja).
- **DELTA gran:** la *"planificació honesta per maduresa real"* és **INEXISTENT/FUTUR**; el sistema **mai recalcula per estat de maduresa / gates ni progrés real**.

**FITTING com a intervals (VIU, fets):**
- `FittingSession` **NO** té `planned_start`/`end`; té `data` (DateField `:230`), `start_time` (TimeField `:231`), `duracio_minuts` (`:251`).
- **Acoblament:** `_collect_busy_intervals` (`scheduler_service.py:95-114`) tracta `FittingSession` (attendees=profile, exclou Tancada/Anullada) com a **franja OCUPADA**; les tasques movibles **s'empenyen** (`:179-180`).
- **Invers:** crear/modificar/tancar un fitting amb franja **dispara `recompute_for_technicians`** (`fitting/services.py:184`/`268`/`607`/`764`). **VIU.**

### 7.3 Reutilitza / estén / jubila

- **REUTILITZA (viu):** `scheduler_service.schedule` (motor determinista); `plan_service` (compute/preview/apply/recompute); ordenació per tècnic + `TechnicianQueueOrder` (override manual); `PlanSnapshot` (històric previst-vs-real); acoblament fitting↔scheduler (franja ocupada + recompute invers).
- **ESTÉN:**
  - 💡 PROPOSTA (a validar): un **seam maduresa → recompute** (signal/servei) que recalculi la data quan canvia gate/fitting-result/progrés real, no només en assignació/ocupació.
  - 💡 PROPOSTA (a validar): un **endpoint de pla per-model** que llegeixi `Model.predicted_start`/`end` (avui escrits però morts) i les `ModelTask` del model.
  - 💡 PROPOSTA (a validar): reconnectar l'aprenentatge Welford perquè re-ajusti (o reavaluï) snapshots de tasques ja planificades, no només les noves.
- **JUBILA / DECIDIR:** `Model.predicted_start`/`end` són **camps escrits però no llegits** per cap view; decidir si s'exposen (estendre) o es jubilen.

### 7.4 Què cal fer, com, quan, per què

- **QUÈ:** (1) connectar maduresa/gates/progrés al recompute; (2) crear la lectura de pla per-model; (3) decidir el destí del snapshot congelat vs aprenentatge real.
- **COM:** 💡 PROPOSTA (a validar): seam `maduresa→recompute_for_technicians`; view `models/<id>/plan/`; política d'actualització de `estimated_minutes` (re-snapshot vs cel·la viva).
- **QUAN:** el recompute per maduresa depèn de la reconciliació de fase (D-3) i dels gates (secció 5); la lectura per-model habilita el "on sóc / quan" del dashboard (secció 3) i el dashboard del PM.
- **PER QUÈ:** avui la planificació només es mou per assignació i ocupació de fitting, mai per l'estat real del model; i el pla per-model no és llegible tot i que les dades (`predicted_start`/`end`) ja es desen.

**Marcatge:** scheduler / `plan_service` / per-tècnic / acoblament fitting = **viu**; lectura per-model = **parcial/STUB** (camps escrits, cap view); planificació honesta per maduresa = **INEXISTENT/futur**; snapshot de durada = **congelat (no auto-ajust)**.

---

## 8. Usuaris i permisos (Àrea 6) — tècnic vs manager vs PM

### 8.1 Què demana el nou model

- Rol **PM** que decideix el design freeze, planifica i assigna.
- Distinció **tècnic vs manager**.
- Capacitat **configure** (perfil Montse) per a configuració del sistema.
- **OK final autoritzat**.
- **No contaminar el model tècnic** amb la capa comercial.

### 8.2 Què hi ha avui (fets)

**RBAC del tenant (fets):**
- `accounts/capabilities.py:6-12`: **7 capacitats** — EXECUTE_TASKS / DEFINE_TASKS / SCHEDULE_FITTINGS / CLOSE_GATES / CONFIGURE / VIEW_TEAM_TASKS / MANAGE_USERS.
- `ROLE_CAPABILITIES` (`:20-26`): **4 rols** — technician (EXECUTE), product_manager (EXECUTE+DEFINE+SCHEDULE), manager (+CLOSE_GATES+VIEW_TEAM_TASKS), admin (ALL). DEFAULT_ROLE = technician (`:28`).
- `get_capabilities` (`:31-43`): base del rol ± overrides JSON `UserProfile.permisos` `{grant/revoke}`.
- `HasCapability` DRF (`:46-54`).
- `UserProfile` (`accounts/models.py:5-19`): `rol_nom` CharField **LLIURE** (no FK/choices), `permisos` JSON, `cost_hora`, `jornada_override`. Helpers `get_allowed_task_types` (`:57-71`), `scope_model_task_queryset` (`:74-95`).

**DELTA de rols (fets):**
- **(a) PM PARCIAL:** `product_manager` té DEFINE+SCHEDULE, però el **design freeze NO està gated**: `approve_design_freeze_view` només `IsAuthenticated` (`wizard_views.py:16-22`) — l'atribueix al **tècnic**. **GAP**.
- **(b) tècnic vs manager SÍ existeix:** technician vs manager (+CLOSE_GATES+VIEW_TEAM_TASKS).
- **(c) configure:** la capacitat CONFIGURE existeix i gateja pom/planning/customer/size-map (`pom/views.py:38`, `size_map_views.py:22`, `planning/views.py:29`, `views_b.py:509,600`), **PERÒ només la té admin** (`capabilities.py:25`). **No hi ha rol "configurador" no-admin** (el perfil Montse hauria de ser admin o rebre CONFIGURE via JSON). **GAP de rol**.
- **(d) OK final PARCIAL:** CLOSE_GATES + `gate_model_view` cobreix l'avanç autoritzat (manager/admin), però **no hi ha un "OK final/signatura" distint** dels gates de fase (DUBTÓS si el disseny el vol separat).

**Profunditats usuari/estudi — separació NETA (fets, django-tenants):**
- **Tenant:** `accounts.UserProfile` = RBAC de capacitats.
- **SHARED/public:** `backoffice.BackofficeUser` (`backoffice/models.py:9-34`), RBAC pròpia ADMIN/COMERCIAL/FACTURACIO/SUPORT (`:17-21`), independent de `is_staff`; `HasBackofficeRole` (`backoffice/views.py:58-81`); JWT pròpia.
- **Frontera comercial:** tota la capa comercial viu a `backoffice` SHARED (ServiceCatalog/TenantContract/ContractLine/Invoice/InvoiceLine/ModelConsumptionEvent `:63-207`); el consum tenant→public va via **ref FLUIXA** `opaque_ref` UUID + `codi_client`, **SENSE noms/codis de model** (`:63-77`).
- **CONCLUSIÓ:** *"no contaminar el model tècnic amb la comercial"* **JA està materialitzat i és sòlid**. **VIU.**

### 8.3 Reutilitza / estén / jubila

- **REUTILITZA (viu):** sistema de 7 capacitats + 4 rols + overrides JSON; `HasCapability`; distinció technician/manager; separació tenant/SHARED i frontera comercial (ja sòlida).
- **ESTÉN:**
  - 💡 PROPOSTA (a validar): afegir capacitat **APPROVE_FREEZE** i gatejar `approve_design_freeze_view` amb ella (avui només `IsAuthenticated`).
  - 💡 PROPOSTA (a validar): formalitzar el **rol PM** amb dret de freeze.
  - 💡 PROPOSTA (a validar): crear un **rol configurador no-admin** (perfil Montse) que tingui CONFIGURE sense ser admin.
  - 💡 PROPOSTA (a validar): substituir `rol_nom` text lliure per choices/FK.
- **JUBILA:** res a jubilar en aquesta àrea (la separació comercial ja és correcta).

### 8.4 Què cal fer, com, quan, per què

- **QUÈ:** tancar els GAPs de rol (freeze sense gate, configurador només-admin, OK final indefinit).
- **COM:** 💡 PROPOSTA (a validar): nova capacitat APPROVE_FREEZE, nou rol configurador, i decidir si l'OK final és una capacitat distinta de CLOSE_GATES.
- **QUAN:** el gate de freeze (D-10) depèn de l'àrea Model/design freeze (secció 10); el rol configurador pot anar de forma independent.
- **PER QUÈ:** avui qualsevol autenticat pot fer el freeze i només l'admin pot configurar; el disseny vol responsabilitats separades (PM, configurador).

**Marcatge:** RBAC de capacitats + separació comercial = **viu**; APPROVE_FREEZE, rol configurador, OK final separat = **futur**.

---

## 9. Economia del treball (Àrea 7) — temps / esforç

### 9.1 Què demana el nou model

- El **temps com a dimensió del patrimoni DEL MODEL**: l'esforç ha de ser llegible **per model**.
- **Identificar (no desenvolupar)** la lectura de **cost / rendibilitat**.

### 9.2 Què hi ha avui (fets)

**Patró Welford en TRES còpies (troballa — àlgebra idèntica, cel·la diferent, fets):**
1. `update_client_profile` (`pom/services.py:304`): cel·la `client × garment × pom × talla` → `ClientMesuraPerfil` (`pom/models.py:571`). És perfil de mesures **de CLIENT, no de model**.
2. `record_actual_time` (`tasks/services_i.py:19`): cel·la `garment_type_item × task_type` → `TaskTimeEstimate` (`tasks/models.py:369`, `unique(garment_type_item, task_type)`, `n`/`mean_minutes`/`m2`).
3. `update_fitting_duration_stat` (`fitting/services.py:628`): **SINGLETON GLOBAL** del tenant `get_or_create(pk=1)` → `FittingDurationStat` (`fitting/models.py:387`).
- **TROBALLA:** el docstring de `_capture_duration` (`services.py:614`) i el model (`:388`) diuen *"per model"* **PERÒ la implementació és global `pk=1`** — **nomenclatura enganyosa**.
- `WELFORD_MIN_SAMPLES=5` només existeix a `tasks/services_i.py:10`, usat a `:51`; les altres dues còpies **sense llindar** (apliquen des de `n=1`).

**Captura del temps (fets):**
- `TimerEntrada` (`tasks/models.py:116`): FK `ModelTask` (related `timers`), FK `tecnic`, `inici`/`fi`/`minuts`/`actiu` — **temps real**.
- `record_actual_time` cridat en tancar tasca (`services_c.py:124-125`).
- `_capture_duration` (`fitting/services.py:613`): durada de sessió (guard `<0` o `>240`), dividida pel nº de peces.

**TEMPS PER MODEL: NO agregable avui (fets):**
- `TaskTimeEstimate` **sense FK Model** (clau `garment_type_item × task_type`).
- `record_actual_time` (`services_i.py:25-27`) llegeix `model_task.model.garment_type_item_id`; **si no n'hi ha, DESCARTA la mostra**; l'agregat Welford **NO conserva la FK model** → **es perd la traça al model**.
- `FittingDurationStat` és **global**.
- `PlanSnapshot` (`tasks/models.py:390`): result JSON `load_minutes` per model = **foto de planificació**, no agregat real evolutiu.
- **DELTA:** el disseny vol temps com a **patrimoni DEL MODEL**; avui és patrimoni de la **CEL·LA** i del **TÈCNIC**. Per tenir temps/model: afegir FK model a l'agregat **o** reconstruir sumant `TimerEntrada` per `model_task__model` (no materialitzat).

**COST / RENDIBILITAT (fets):**
- Billing existeix a backoffice: `billing_service.py` `generate_invoice`/`_get_active_contract`.
- `ModelConsumptionEvent` (`backoffice/models.py:63`): **deliberadament SENSE codi/nom de model**, clau `codi_client × period × opaque_ref`.
- `ContractLine` (`:124`) + `TenantContract` (`:103`) + `ServiceCatalog` (`:80`) + `Invoice`/`InvoiceLine` (`:147`/`:186`). `ServiceCatalog.TIPUS_CHOICES` (`:84`): tier_fee/model_count/manual.
- **Assignació de cost per model/departament/col·lecció: NO** (cap camp `departament`/`collection`; `model_count` és recompte **anònim**).
- **Cap pont entre esforç real i facturació:** el cost que FHORT cobra **NO es deriva del temps real**.
- **DELTA:** cost per model/departament/col·lecció **INEXISTENT (futur)**; el que hi ha és **billing SaaS per tenant** (viu, Sprints 4-6), **desacoblat** del temps real.

### 9.3 Reutilitza / estén / jubila

- **REUTILITZA (viu):** `TimerEntrada` (captura real per `ModelTask`+`tecnic`); `record_actual_time`/`TaskTimeEstimate` (estimació per cel·la); el patró Welford; billing SaaS de backoffice.
- **ESTÉN:**
  - 💡 PROPOSTA (a validar): afegir **FK model a l'agregat de temps** o crear una **vista d'agregació** que sumi `TimerEntrada` per `model_task__model` (avui no materialitzat).
  - 💡 PROPOSTA (a validar): unificar/encapsular les **3 còpies de Welford** i homogeneïtzar el llindar `WELFORD_MIN_SAMPLES`.
- **JUBILA / CORREGIR:**
  - 💡 PROPOSTA (a validar): corregir la **nomenclatura enganyosa** de `FittingDurationStat` (docstring *"per model"* sobre un singleton global `pk=1`, `services.py:614`).

### 9.4 Què cal fer, com, quan, per què

- **QUÈ:** fer el temps **agregable per model**; **identificar** (no desenvolupar) la lectura cost/rendibilitat.
- **COM:** 💡 PROPOSTA (a validar): FK model a l'agregat **o** vista d'agregació sobre `TimerEntrada`; documentar que cost/rendibilitat per model és **futur** i avui NO existeix pont esforç↔facturació.
- **QUAN:** l'agregació per model habilita la dimensió "esforç" del dashboard (secció 3) i és prerequisit de qualsevol lectura de rendibilitat futura.
- **PER QUÈ:** avui el temps és patrimoni de la cel·la i del tècnic, no del model; i el cost facturat no es deriva del temps real.

**Marcatge:** `TimerEntrada`/`TaskTimeEstimate`/billing SaaS = **viu**; temps agregat per model = **DELTA**; cost/rendibilitat per model/departament/col·lecció = **futur/inexistent**; `FittingDurationStat` *"per model"* = **nomenclatura enganyosa a corregir**.

---

## 10. Capa de disseny i design freeze (Àrea 8)

### 10.1 Què demana el nou model

El disseny (`DISSENY_MODEL_VIU.md §3.0bis`) demana:
- Una **capa de disseny PRÈVIA al Proto** amb una **"fitxa de disseny"** (puja document).
- Un **design freeze governat pel PM** amb **DUES senyals**: acceptació del disseny **+** OK de compres/BOM.
- Una **anàlisi de mortalitat de models** (cost no madurat + causa de mort).

### 10.2 Què hi ha avui (fets)

**DESIGN FREEZE actual = segell de data simple (fets):**
- Camps `Model.design_freeze_at` + `design_freeze_by` FK (`models_app/models.py:283-289`, Sprint 7A).
- `approve_design_freeze_view` (`pom/wizard_views.py:16-49`) és un **SEGELL DE DATA SIMPLE**, **no un gate condicionat** (docstring `l.22`: *"Does not require measurements — visual/conceptual approval"*): si ja existeix → **idempotent**; si no → posa `design_freeze_at=now()` + `design_freeze_by`, i **si `estat=='Nou'` el passa a `'En curs'`**.
- **Permís:** `@permission_classes([IsAuthenticated])` (`l.16-17`) — **cap rol/PM**; **qualsevol autenticat**.
- **Reversió:** **cap endpoint d'unfreeze** (write-once de facto; només es neteja a `clone_model_for_qa.py:83`).
- **NO bloqueja res downstream:** cap tasca/transició/fitting el consulta.
- URL `models/<id>/aprovar-design-freeze/` (`models_app/urls.py:90`).
- **BUG:** `l.38` escriu `estat='En curs'` que **NO és un value vàlid** d'`ESTAT_CHOICES` (el value és `'EnCurs'`, label `'En curs'`) → **desa un estat fora d'enum** (Deute **T-2**, secció 12).

**HOMÒNIM (fets):** `check_design_freeze()` (`models_app/extraction_service.py:189-224`) valida el **JSON d'extracció IA** (nom/codi, garment_type, talla base, material, ≥3 POMs) → `{pass, blockers, warnings}`; és un **gate dur** a `create_from_extraction_view` (`extraction_views.py:158-164`, **422** si no passa). Hi ha **DOS "design freeze" homònims sense relació**: (a) el **segell de fase** (`approve_design_freeze_view`), (b) el **validador de completesa** del document IA (`check_design_freeze`).

**LES DUES SENYALS — NO existeixen (fets):**
- **Cap model/event** d'*"acceptació de disseny"* (el més proper, `GateEvent` `tasks/models.py:256-275`, és genèric de transició).
- **Validació BOM/compres INEXISTENT:** cap model/camp/event BOM/compres/purchase; **cap app de compres**. **Cap relació** disseny ↔ compres ↔ BOM.

**CAPA DE DISSENY prèvia — gairebé buida (fets):**
- `FASE_CHOICES` Pending → Dev → Proto → SizeSet → PP → TOP (`models_app/models.py:94-101`).
- `'Dev'` **existeix com a value** però **gairebé sense lògica** (única transició Pending→Dev en iniciar tasca, `tasks/services_c.py:91`); **no és una fase de disseny** amb tasca/fitxa pròpia; estat de pas buit.
- **Cap "tasca de disseny" prèvia al Proto:** el flux **salta a Proto** en crear `SizeFitting` (`signals.py:117`, `tech_sheet_views.py:306`, `clone_model_for_qa.py:81`).
- **FITXA DE DISSENY:** `ModelFitxer` (`models_app/models.py:328-372`) amb `FileField` (`:360`), `url_extern`, versionat, `pujat_per`, i `CATEGORIA_CHOICES` inclou `'Disseny'` (`:331`); ViewSet `ModelFitxerViewSet` (`views.py:73-75`). → **VIU** el contenidor genèric per pujar document de disseny, **però sense fase/gate que el lligui ni l'exigeixi**.

**MORTALITAT — inexistent (fets):**
- Estats `Model` Nou/EnCurs/EnRevisio/Tancat (`models_app/models.py:83-92`); **NO hi ha estat cancel·lat/mort** (`Tancat` = completat).
- **Cap causa de mort** ni **cost no madurat** al `Model` (cap camp motiu/causa sobre `Model`; els `motiu` existents són d'altres dominis: fitting `motiu_anullacio` `:268`, `gate_motiu` `:310`, tenants `motiu_baixa`, `MeasurementChangeLog`).
- Existeixen `slots_prev`/`reals` (`:257-260`) + `consumption_started_at` (`:204`) + `ModelConsumptionEvent`, **però cap concepte de cost meritat fins a la mort** ni anàlisi de mortalitat.

### 10.3 Reutilitza / estén / jubila

- **REUTILITZA (viu):** `ModelFitxer` categoria `'Disseny'` (pujada de document de disseny); `GateEvent` (log de transicions); `check_design_freeze` d'extracció (gate dur de completesa del document IA).
- **ESTÉN:**
  - 💡 PROPOSTA (a validar): convertir el freeze en un **gate de 2 senyals** (acceptació disseny + OK BOM/compres) **governat per una capacitat `APPROVE_FREEZE`** (enllaça amb D-10), amb rol PM i **reversió/unfreeze**.
  - 💡 PROPOSTA (a validar): modelar una **fase de disseny formal** prèvia al Proto que lligui `ModelFitxer` 'Disseny' a una tasca/gate (avui `'Dev'` és buit).
  - 💡 PROPOSTA (a validar): modelar l'**entitat BOM/compres** i la relació disseny↔compres (inexistent).
  - 💡 PROPOSTA (a validar): modelar la **mortalitat de models** (estat mort + causa + cost meritat fins a la mort).
- **JUBILA / CORREGIR:**
  - **BUG `estat='En curs'`** fora d'enum (`wizard_views.py:38`) → **corregir a `'EnCurs'`** (Deute T-2).
  - Resoldre l'**homonímia** dels dos "design freeze" (segell de fase vs validador de completesa).

### 10.4 Què cal fer, com, quan, per què

- **QUÈ:** (1) corregir el BUG d'enum (T-2); (2) convertir el segell en gate de 2 senyals governat pel PM; (3) modelar la fase de disseny formal i la fitxa lligada; (4) modelar BOM/compres; (5) modelar la mortalitat.
- **COM:** 💡 PROPOSTA (a validar): capacitat `APPROVE_FREEZE` + dues precondicions (acceptació disseny + OK BOM); fase de disseny amb tasca pròpia que exigeixi `ModelFitxer` 'Disseny'; entitat BOM; estat de mort + camps causa/cost meritat.
- **QUAN:** el gate de 2 senyals depèn de l'àrea Usuaris/permisos (D-10, capacitat `APPROVE_FREEZE`); el BUG T-2 es pot corregir de forma immediata i independent; BOM i mortalitat són construcció nova.
- **PER QUÈ:** avui el freeze és un segell que **qualsevol autenticat** pot posar, sense senyals, sense rol, sense reversió i sense efecte downstream; no hi ha fase de disseny formal ni BOM ni mortalitat, tot i que el contenidor de fitxa de disseny (`ModelFitxer` 'Disseny') ja viu.

**Marcatge:** `ModelFitxer` 'Disseny' / `GateEvent` / `check_design_freeze` extracció = **viu**; `approve_design_freeze_view` = **STUB** (segell write-once, `IsAuthenticated`, sense senyals/rol/reversió/downstream, **BUG enum**); 2 senyals + BOM/compres + fase de disseny formal + mortalitat = **futur/inexistent**.

---

## 11. Mapa de jubilacions

**Llegenda:** JUBILA (codi mort a eliminar) · CONSERVA-REUTILITZA (viu) · ESTÉN (viu, amplia) · CONSTRUEIX NOU (inexistent) · MIGRA/FUSIONA (llegat duplicat/desconnectat) · STUB A COMPLETAR (esquelet no connectat) · CORREGEIX (bug/nomenclatura).

### 11.1 Taula de jubilacions / correccions

| Peça | Ref | Categoria | Acció |
|---|---|---|---|
| `recalculate_current_phase` (TODO descriu mecanisme mort; la funció no existeix) | `fitting/services.py:696` | JUBILA (mort) | Eliminar TODO; reconciliació explícita de fase (D-3) |
| Signal de fase retirat (el TODO l'invoca però ja no hi és) | `tasks/signals.py:1-7` | JUBILA (mort) | Netejar; el comentari "únic amo" és fals (2 amos) |
| `sf_pare` (FK self de `SizeFitting`, declarat però mai usat) | `fitting/models.py:27-33` | JUBILA (mort, baixa prioritat) | Eliminar en netejar `SizeFitting` |
| Docstring enganyós `FittingDurationStat`/`_capture_duration` ("per model" sobre singleton global pk=1) | `fitting/services.py:614`, `fitting/models.py:388` | CORREGEIX (nomenclatura) | És global de tenant, no per model |
| BUG `estat='En curs'` (fora d'`ESTAT_CHOICES`; value correcte `'EnCurs'`) | `pom/wizard_views.py:38` | CORREGEIX (bug, Deute T-2) | Canviar a `'EnCurs'` |
| Catàleg llegat `Tasca` (ric, sense FK amb `ModelTask`, sense API; "Merges legacy TascaCataleg" fusió no completada) | `tasks/models.py:4-72` | MIGRA/FUSIONA (llegat) | Fusionar cap a `TaskType`; portar intern/extern i procés al kanban |
| Els dos "design freeze" homònims: (a) segell de fase; (b) validador completesa IA | (a) `pom/wizard_views.py:16-49`; (b) `models_app/extraction_service.py:189-224` | CORREGEIX (homonímia) + MIGRA | Desambiguar; (b) viu i es conserva; (a) a refundar (D-7) |
| `measurements_version` (increment no connectat) | `models_app/models.py:279` | STUB A COMPLETAR | Connectar (D-15) |
| `fora_de_tolerancia` ("drives re-opening propagation later") | `models_app/models.py:561` | STUB A COMPLETAR | Connectar a propagació/brain |
| `ModelGradingRule` ("RES la consumeix encara") | `models_app/models.py:622` | STUB A DECIDIR | Desenvolupar o jubilar |
| `Model.predicted_start`/`predicted_end` (escrits però mai llegits) | escrits `scheduler_service.py:244-246`; def. `models_app/models.py:228-229` | STUB A COMPLETAR/DECIDIR | Exposar via pla-per-model o jubilar |
| Brain `on_fitting_measurement_changed` (STUB pur: log + return None; únic hook; asimètric) | `fitting/brain.py:16-32`, crida `fitting/services.py:455-462` | STUB A COMPLETAR | Desenvolupar i fer simètric (que SizeCheck també el cridi) |
| Snapshot de durada congelat (`estimated_minutes` no re-ajustat per Welford) | `scheduler_service.py:215-218`, `tasks/views_b.py:286-289` | STUB A DECIDIR (política) | Re-snapshot vs cel·la viva (D-6) |
| Fase `'Dev'` (value sense lògica, estat de pas buit) | `models_app/models.py:94-101`; transició `tasks/services_c.py:91` | MIGRA/REFUNDA | Convertir en fase de disseny formal o jubilar |
| Doble camí d'avanç de fase (`advance_phase_gate` vs `advance_phase`) | `tasks/services_d.py` vs `fitting/services.py:647` | MIGRA/UNIFICA | Unificar (D-3) |

### 11.2 Es CONSERVA-REUTILITZA (viu, base sòlida)
`Model` (subjecte); `BaseMeasurement`; `MeasurementChangeLog` (append-only real); `TechSheet`; `ConsumptionRecord`; cadena `Model→ModelTask→TimerEntrada`; `consumption_delivery_view` + `by_model` (fonts parcials de dashboard); `ModelTask`+`TaskType`+`transition_task`+`TaskTransition` (immutable)+`rectification_count`; `advance_phase_gate`/`model_ready_for_gate`; `GateEvent`; `regress_phase` (reversibilitat viva); `GradingVersion` (cicle segellat); `resolve_size_check`+`_reagenda_tasca_size_check`; les 4 eines del llenç (`TechSheet`, `SizeFitting`+`generate_graded_specs`, `FittingSession`/`PieceFitting`, `POMMaster`); `TipologiaModel` (patrons_aprox/CAD); `scheduler_service.schedule`+`plan_service`; `TechnicianQueueOrder`; `PlanSnapshot` (històric); acoblament fitting↔scheduler; RBAC (7 capacitats + 4 rols + overrides JSON); `HasCapability`; separació tenant/SHARED i frontera comercial (`opaque_ref`); patró Welford; billing SaaS backoffice; `ModelFitxer` cat. 'Disseny'; `check_design_freeze` (extracció IA).

### 11.3 S'ESTÉN (viu, amplia base)
Dashboard per-model (reusa `MeasurementChangeLog`/timers/fase); arbre de dependències sobre `TaskType`/`ModelTask`; tancament assistit sobre `transition_task`/`gate_model_view`; intern/extern a `TaskType`/`ModelTask`; guard de `aprovada` a `close_piece_fitting`/`resolve_size_check`; mapeig 4 gates↔6 fases; capa "menú del llenç"; seam maduresa→recompute; endpoint pla-per-model; FK model a l'agregat de temps (o vista sobre `TimerEntrada`); capacitat `APPROVE_FREEZE` + rol PM + rol configurador; `rol_nom` text→choices/FK; freeze com a gate de 2 senyals.

### 11.4 Es CONSTRUEIX NOU (inexistent, DELTA total)
Dashboard unificat per-model; arbre de dependències "què dispara què"; tancament assistit binari; `Watchpoint`; capa "menú del llenç"; motor de patrons (PAT-0+, hexagonal); planificació honesta per maduresa; entitat BOM/compres; fase de disseny formal prèvia al Proto; mortalitat de models (estat mort + causa + cost meritat).

---

## 12. Riscos i decisions obertes per al CTO

> Decisions reordenades per IMPACTE i renumerades netes (D-1..D-15), agrupades en 3 blocs. La col·lisió SizeFitting (D-RESOLTA-2) està tancada; D-OBERTA-1 (propagació) es resol dins del tancament assistit (D-10). Les antigues D-10/D-14 (design freeze) s'han fusionat en D-7.

### Taula-índex

| D | Títol | Bloc | Severitat | Acció |
|---|---|---|---|---|
| D-1 | GradingVersion aprovada sense guard de segellat | 1 Riscos | Alta | Corregir ara |
| D-2 | `estat='En curs'` fora d'enum (Deute T-2) | 1 Riscos | Mitjana | Corregir ara |
| D-3 | Fase en 3 llocs + 2 amos + mecanisme mort | 1 Riscos | Alta | Corregir ara / decidir reconciliació |
| D-4 | Catàleg dual `Tasca`/`TaskType` + per-tenant editable | 2 Arquitectura | Alta | Decidir abans de sprint |
| D-5 | Menú del llenç inexistent + metadada de patró dispersa | 2 Arquitectura | Mitjana | Decidir abans de sprint |
| D-6 | Planificació per maduresa inexistent + lectura per-model morta + snapshot congelat | 2 Arquitectura | Alta | Decidir abans de sprint |
| D-7 | Design freeze (segell simple + capa disseny + mortalitat) [fusió D-10+D-14] | 2 Arquitectura | Alta | Decidir abans de sprint |
| D-8 | Usuaris/permisos: rol PM, configurador, freeze sense capacitat | 2 Arquitectura | Mitjana | Decidir abans de sprint |
| D-9 | Arbre de dependències | 3 Construccions | Mitjana | Construir |
| D-10 | Tancament assistit binari (resol D-OBERTA-1) | 3 Construccions | Alta | Construir |
| D-11 | Atribut intern/extern al kanban operatiu | 3 Construccions | Baixa | Construir |
| D-12 | Watchpoint (entitat que travessa gates) | 3 Construccions | Mitjana | Construir |
| D-13 | Temps com a patrimoni del model (FK temps↔model) | 3 Construccions | Alta | Construir |
| D-14 | Motor de patrons (PAT-0+, hexagonal) | 3 Construccions | Baixa | Construir |
| D-15 | `measurements_version` stub | 3 Construccions | Baixa | Construir/connectar |
| D-OBERTA-1 | Propagació SizeCheck: discrepància de MOMENT | lligada a D-10 | Mitjana | Decidir dins tancament assistit |
| D-RESOLTA-2 | Col·lisió nomenclatura `SizeFitting` | ✅ RESOLTA (Via A) | — | Tancada |
| T-1 | Ref estructurada SizeCheck→BaseMeasurement | Deute | Baixa | Decidir abans de sprint |
| T-2 | `estat='En curs'` fora d'enum (= D-2) | Deute | Mitjana | Corregir ara |

## BLOC 1 — RISCOS / INTEGRITAT DE DADES (resoldre ABANS de tocar res)

### D-1 — `GradingVersion` aprovada SENSE protecció de segellat · Alta · CORREGIR ARA
- **FET:** `close_piece_fitting` (`fitting/services.py:341-475`) no comprova `aprovada` abans de crear `v+1`; el mirror `SizeCheck` tampoc; comentari "legacy multi-active anomaly" (`fitting/services.py:431-433`). `aprovada=True` el posa només `advance_phase` (`fitting/services.py:707-710`).
- **IMPACTE:** una versió segellada a producció pot ser desactivada/substituïda silenciosament, sense guard ni avís → corrupció de dades a producció avui.
- 💡 **SUPÒSIT a validar:** afegir guard que impedeixi superar/desactivar una `GradingVersion` `aprovada` abans de `v+1` (o exigir reobertura explícita registrada). Correcció defensiva, no canvi de model.

### D-2 — `estat='En curs'` escrit fora d'`ESTAT_CHOICES` (Deute T-2) · Mitjana · CORREGIR ARA
- **FET:** `approve_design_freeze_view` (`pom/wizard_views.py:38`) escriu `estat='En curs'` (label); el value vàlid és `'EnCurs'`.
- **IMPACTE:** models amb estat fora d'enum → filtres, índex `[estat, fase_actual]` i màquines d'estat poden ignorar-los o trencar-se silenciosament.
- 💡 **SUPÒSIT a validar:** corregir a `'EnCurs'`. Immediat i independent. (Es manté com a Deute T-2.)

### D-3 — Fase repartida en 3 llocs + 2 amos + mecanisme mort · Alta · CORREGIR ARA (mort) / DECIDIR (reconciliació)
- **FET:** `Model.fase_actual` té 2 amos malgrat el comentari fals `tasks/signals.py:6`: (1) `fitting/services.py:714` `advance_phase`; (2) `tasks/services_d.py:36,:54` `advance_phase_gate`/`regress_phase` (+ creació `tasks/services_c.py:91`). `FittingSession.fase` (`fitting/models.py:229`) input de l'usuari; `PieceFitting.gate` (`fitting/models.py:309`) independent. `recalculate_current_phase` (TODO `fitting/services.py:696`) no existeix i el signal es va retirar (`tasks/signals.py:1-7`).
- **IMPACTE:** fase incoherent; contamina vista d'estat, gates i recompute per maduresa; el TODO mort enganya.
- 💡 **SUPÒSIT a validar:** netejar ja el TODO i signal morts; tractar `advance_phase` (fitting) com a únic pont real fins a una reconciliació explícita. **PREGUNTA AL CTO:** qui ha de ser l'amo únic de `fase_actual` (fitting o tasks)?

## BLOC 2 — ARQUITECTURA / REENCAIX ESTRUCTURAL

### D-4 — Catàleg dual `Tasca`(ric)/`TaskType`(pla) sense FK + `TaskType` per-tenant editable · Alta · DECIDIR ABANS DE SPRINT
- **FET:** `Tasca` (`tasks/models.py:4-72`, només Django admin, sense API, sense FK amb `ModelTask`, "Merges legacy TascaCataleg" no completada) coexisteix amb `TaskType` (4 camps, `tasks/models.py:185-198`), que usa el kanban. `TaskType` és TENANT i editable (`settings.py:70`, `views_b.py:29-50`); el disseny vol el procés al codi/global/no-editable.
- **IMPACTE:** dos catàlegs desincronitzats; el procés el pot editar el tenant, contra el disseny.
- 💡 **SUPÒSIT a validar:** completar la fusió cap a un únic catàleg. **PREGUNTA AL CTO:** `TaskType` global/no-editable (codi) o per-tenant amb allow-list?

### D-5 — Menú del llenç inexistent + metadada de patró/procés dispersa · Mitjana · DECIDIR ABANS DE SPRINT
- **FET:** 4 eines vives són endpoints aïllats en 3-4 apps; grep `canvas|llenç|available.*action` = 0. Metadada de procés a `Tasca` llegat; patronatge a `TipologiaModel` (`tasks/models.py:74-112`); `TaskType` sense `pattern_*`.
- **IMPACTE:** l'usuari no té vista unificada d'accions; no es deriven de l'estat.
- 💡 **SUPÒSIT a validar:** capa d'orquestració (endpoint model_id→accions per fase/estat) + consolidar metadada. Depèn de D-3.

### D-6 — Planificació honesta per maduresa inexistent + lectura per-model morta + snapshot congelat · Alta · DECIDIR ABANS DE SPRINT
- **FET:** recompute només per assignació/ocupació de fitting (`tasks/views_b.py:253`, `plan_service.py:335/375`, `fitting/services.py:184/268/607/764`), mai per maduresa/gates/progrés; cap signal a `planning/`. `Model.predicted_start/end` escrits (`scheduler_service.py:244-246`) però cap view els llegeix. `estimated_minutes` congelat en crear (`tasks/views_b.py:286-289`); Welford no re-ajusta tasques creades.
- **IMPACTE:** el pla mai reflecteix l'estat real; no hi ha pla per-model tot i desar-se; no aprèn.
- 💡 **SUPÒSIT a validar:** seam maduresa→recompute + endpoint pla-per-model que llegeixi els camps morts. **PREGUNTA AL CTO:** durada — re-snapshot en recompute o cel·la viva? Depèn de D-3.

### D-7 — Design freeze: segell simple sense gate/2 senyals/rol/reversió + capa de disseny i mortalitat inexistents · Alta · DECIDIR ABANS DE SPRINT
> Fusió de les antigues D-10 i D-14 (totes dues sobre el freeze).
- **FET:** `approve_design_freeze_view` (`pom/wizard_views.py:16-49`) és segell de data write-once: `IsAuthenticated` (cap rol/PM), sense reversió, sense efecte downstream. Dos "design freeze" homònims: segell de fase vs `check_design_freeze` validador IA (`extraction_service.py:189-224`). 2 senyals i BOM/compres inexistents; fase de disseny formal inexistent (`'Dev'` buit, `tasks/services_c.py:91`) tot i que `ModelFitxer` 'Disseny' (`models_app/models.py:331`) viu; mortalitat inexistent.
- **IMPACTE:** qualsevol autenticat congela un model sense senyals/rol/reversió ni efecte real; manca la capa de disseny prèvia al Proto i l'anàlisi de mortalitat.
- 💡 **SUPÒSIT a validar:** freeze com a gate de 2 senyals (acceptació disseny + OK BOM/compres) governat per capacitat `APPROVE_FREEZE` (D-8), amb rol PM i reversió; modelar fase de disseny (lligant `ModelFitxer` 'Disseny') i mortalitat; desambiguar els homònims. (El bug d'enum va a D-2/T-2.)

### D-8 — Usuaris/permisos: gaps rol PM/configurador + freeze sense capacitat · Mitjana · DECIDIR ABANS DE SPRINT
- **FET:** `product_manager` té DEFINE+SCHEDULE però el freeze no està gated (`IsAuthenticated`, `wizard_views.py:16-22`). `CONFIGURE` només admin (`capabilities.py:25`); cap rol configurador no-admin (Montse). `UserProfile.rol_nom` text lliure (`accounts/models.py:5-19`).
- **IMPACTE:** qualsevol autenticat fa el freeze; només admin configura; rols no tipats. Bloqueja D-7.
- 💡 **SUPÒSIT a validar:** capacitat `APPROVE_FREEZE` + rol PM + rol configurador no-admin; `rol_nom` text→choices/FK. La separació comercial tenant/SHARED ja és sòlida.

## BLOC 3 — CONSTRUCCIONS NOVES / FUNCIONALITAT FUTURA

### D-9 — Arbre de dependències · Mitjana · CONSTRUIR
- **FET:** cap FK self/M2M/taula/trigger entre `TaskType`/`ModelTask` (§4.2); ordenació lineal `default_order`+`ModelTask.order`; `PaquetServei` llista plana.
- **IMPACTE:** no hi ha "què dispara què"; prerequisit de propagació estructurada.
- 💡 **SUPÒSIT a validar:** taula d'aristes/FK self "què dispara què" sobre `TaskType`/`ModelTask`.

### D-10 — Tancament assistit binari (resol D-OBERTA-1) · Alta · CONSTRUIR
- **FET:** cap tancament assistit (grep negatiu question/checklist/guided); `gate_model_view` (`views_b.py:391-414`) només `to_phase`/`notes`.
- **IMPACTE:** és el punt on s'ubica la decisió conscient de propagar (resol D-OBERTA-1).
- 💡 **SUPÒSIT a validar:** endpoint de tancament amb qüestionari binari sobre `transition_task`/`gate_model_view`; allà es decideix la propagació.

### D-11 — Atribut intern/extern al kanban operatiu · Baixa · CONSTRUIR
- **FET:** absent de `TaskType`/`ModelTask`; només a `Tasca.tipus_tasca` (llegat, `tasks/models.py:21-29`) i `pom.TascaGlobal.tipus`.
- **IMPACTE:** el kanban no distingeix intern d'extern.
- 💡 **SUPÒSIT a validar:** portar intern/extern a `TaskType`/`ModelTask` (coordina amb D-4).

### D-12 — Watchpoint (entitat que travessa gates) · Mitjana · CONSTRUIR
- **FET:** `Watchpoint` no existeix (0 matches). Els "4 gates" del disseny ≠ `PieceFitting.gate` (Pendent/OK/NO_OK/EXCEPCIO, `fitting/models.py:293-298`); fases reals 6 (`Model.fase_actual`).
- **IMPACTE:** DELTA total; cap entitat travessa gates ni mapeig 4↔6.
- 💡 **SUPÒSIT a validar:** model `Watchpoint` amb FK a gate/fase + mapeig 4 gates↔6 fases. Depèn de D-3.

### D-13 — Temps com a patrimoni del model (FK temps↔model) · Alta · CONSTRUIR
- **FET:** `record_actual_time` (`tasks/services_i.py:25-27`) perd la traça al model (`TaskTimeEstimate` clau `garment_type_item × task_type`, sense FK Model; si no hi ha garment_type_item descarta la mostra). `FittingDurationStat` singleton global pk=1, docstring enganyós "per model" (`fitting/services.py:614`). Cap pont esforç↔facturació.
- **IMPACTE:** el temps és patrimoni de la cel·la i del tècnic, no del model; bloqueja la dimensió "esforç" del dashboard i la rendibilitat.
- 💡 **SUPÒSIT a validar:** FK model a l'agregat o vista sumant `TimerEntrada` per `model_task__model`; corregir nomenclatura `FittingDurationStat`. Cost/rendibilitat per model = identificar, no desenvolupar (futur).

### D-14 — Motor de patrons (PAT-0+, hexagonal) · Baixa · CONSTRUIR
- **FET:** cap entitat/app/endpoint; res hexagonal al codi (`MOTOR_DE_PATRONS.md:151 §3.4, :506`); el "motor d'scheduling" (`planning/`) no és el motor de patrons.
- **IMPACTE:** funcionalitat futura íntegra, independent.
- 💡 **SUPÒSIT a validar:** mòdul hexagonal separat (PAT-0 parser+visor, PAT-1 anotació). No bloqueja res.

### D-15 — `measurements_version` stub · Baixa · CONSTRUIR/CONNECTAR
- **FET:** `Model.measurements_version` (`models_app/models.py:279`), increment no connectat de forma generalitzada.
- **IMPACTE:** versionat de mesures poc fiable; risc de specs obsolets (només-override no incrementa).
- 💡 **SUPÒSIT a validar:** connectar l'increment als canvis de mesura rellevants (lligat a D-10/brain i `fora_de_tolerancia`).

## Decisions de referència conservades

### D-OBERTA-1 — Propagació al SizeCheck: discrepància de MOMENT (no de capacitat) · lligada a D-10
- **FET:** `resolve_size_check` propaga sol en acceptar (`services_size_check.py:213`, via `generate_graded_specs`) quan el model té deltes — mirror de `close_piece_fitting`. El codi sap re-escalar bé (`pom/services.py:89`); falla el QUI/QUAN, no el càlcul.
- **ESTAT:** no es corregeix ara; es resol dins del tancament assistit (D-10), on s'ubica el punt de decisió conscient.

### D-RESOLTA-2 — Col·lisió de nomenclatura `SizeFitting` · ✅ RESOLTA
- ✅ **RESOLTA pel CTO (Via A):** conservar noms i desambiguar a glossari/UI. `SizeFitting` ≡ "contenidor-de-grading"; "Size Fitting de talla base" ≡ `SizeCheck`. No es fusionen. Col·lisió purament de nomenclatura. (Via B — renombrar — descartada per cost alt.)

### Deute T-1 (traçabilitat) — referència estructurada SizeCheck→BaseMeasurement
- **FET:** el `BaseMeasurement` generat per size check no guarda `size_check_ref` estructurat: només text `'Size check · check {pk}'` (`services_size_check.py:182`).
- 💡 **PROPOSTA:** FK/referència estructurada del `BaseMeasurement` al `SizeCheck` origen. Rellevant pel test 11:47.

### Deute T-2 (correcció) — `estat='En curs'` fora d'enum
- Conservat; promocionat a D-2 (Bloc 1) per ser risc d'integritat. Correcció: `'En curs'`→`'EnCurs'` (`pom/wizard_views.py:38`).
