> ⚠️ SUPERADA 2026-07-07 — implementada (edició inline a05de34 + EscalatTask jubilada e80f17a). Consulta només com a històric.

# DIAGNOSI — EDICIÓ DINS EL MODELSHEET (recorregut lectura ↔ edició)

**Patró A · read-only · branca `dev` · 2026-06-24**
Entorn: `/var/www/ftt-staging` (frontend React + backend Django). Schema `fhort`.

**Objectiu (decidit per l'Agus, no re-obrir):** l'edició de Mesures i Escalat ha de viure **DINS** el
ModelSheet, a la mateixa tab, commutant **CONSULTA ↔ EDICIÓ** — no com a pàgina externa amb layout propi.
Així es manté tot el context (sidebar, pestanyes, capçalera, watchpoint).

> **Titular:** L'edició no és "fora del Shell" per falta de Layout — `/mesures` i `/escalat` SÍ viuen dins
> el `Shell` (sidebar). El problema és que són **rutes/components SEPARATS** (ModelMeasurements, EscalatTask)
> que **no renderitzen les tabs/capçalera/watchpoint del ModelSheet**, i `/escalat` a més pinta un
> **overlay `fixed inset-0`** que tapa el sidebar. Tots dos editors (`CheckMeasureEditor`,
> `PropagatedEditor`) **ja són editables via `readOnly=false`** i agnòstics a la ruta → es poden muntar
> editables dins la tab. El `task_id` i el compta-temps es poden obtenir/disparar **sense navegar**
> (`openTask` + `transition`). Jubilar les pàgines externes és NET un cop l'edició és inline.

---

## BLOC 1 — COM S'OBRE L'EDICIÓ AVUI (per què surt fora del context)

**1A · Tabs de consulta al ModelSheet.** [ModelSheet.jsx:239](../../frontend/src/pages/ModelSheet.jsx#L239)
munta `<CheckMeasureEditor model={model} readOnly />` (tab Mesures) i
[:254](../../frontend/src/pages/ModelSheet.jsx#L254) `<PropagatedEditor modelId inline readOnly />` (tab
Escalat). **Hereten el layout del ModelSheet (sidebar+tabs+capçalera): SÍ** — són contingut de la tab.

**1B · Botons "Editar mesures/escalat" → navegació externa.**
[ModelSheet.jsx:259](../../frontend/src/pages/ModelSheet.jsx#L259) `openTaskAndGo('pom', tid =>
/models/:id/mesures?task_id=)` i [:247](../../frontend/src/pages/ModelSheet.jsx#L247) `openTaskAndGo('scaling',
… /escalat?task_id=)`. Aquestes rutes ([App.jsx:139,141](../../frontend/src/App.jsx#L139)) renderitzen
**ModelMeasurements / EscalatTask**, NO ModelSheet.

**1C · El mecanisme exacte del trencament.**
- `/escalat` → `EscalatTask` → `<PropagatedEditor … />` **sense `inline`** → `outerStyle = { position:
  'fixed', inset: 0, zIndex: 50, background: rgba(0,0,0,.45) }`
  ([PropagatedEditor.jsx:60-63](../../frontend/src/pages/PropagatedEditor.jsx#L60)) → **overlay full-screen
  que TAPA el sidebar** (encara que tècnicament el Shell hi és a sota).
- `/mesures` → `ModelMeasurements` → `<div style={{ width:'100%', padding:'1rem' }}>`
  ([ModelMeasurements.jsx:193](../../frontend/src/pages/ModelMeasurements.jsx#L193)): **NO és overlay**, viu
  dins el `<main>` del Shell — però és un **component diferent del ModelSheet**, així que **no mostra les
  tabs/capçalera/watchpoint del ModelSheet**. L'usuari perd el context de pestanyes encara que el sidebar hi
  sigui.

**1D · El layout comú.** L'aporta `Shell`
([App.jsx:129](../../frontend/src/App.jsx#L129); [Shell.jsx](../../frontend/src/components/layout/Shell.jsx):
`Sidebar` + `Topbar` + `<main><Outlet/></main>`, `marginLeft:240`). **Totes** les rutes filles de `/`
(ModelSheet, ModelMeasurements, EscalatTask…) hi viuen dins. ⇒ El sidebar **no falta**; el que falta és que
l'edició sigui **una tab del ModelSheet en mode edició**, no una ruta germana. (Excepció real fora del Shell:
`/models/:id/fitxa` i `/clients/:id/plantilla`, [App.jsx:115-121](../../frontend/src/App.jsx#L115) — editors
full-screen a posta; NO és el cas de mesures/escalat.)

---

## BLOC 2 — QUÈ CAL PER A "EDICIÓ DINS LA TAB"

**2A · Els editors JA són editables sense ruta.**
- `CheckMeasureEditor({ model, readOnly=false, taskId, onResolved, onBack, onFeedback })`
  ([CheckMeasureEditor.jsx](../../frontend/src/components/model/CheckMeasureEditor.jsx)): l'**editabilitat
  depèn de `readOnly`, NO de `task_id`** (el `task_id` només viatja a `WatchpointsPanel` com a metadada
  d'origen). ModelMeasurements el munta editable (`readOnly` absent + `taskId`); ModelSheet el munta
  `readOnly`. **Res tècnic impedeix muntar-lo editable dins la tab** — canviar `readOnly` a `false` amb un
  botó que commuti mode.
- `PropagatedEditor({ inline, readOnly })`: `inline=true` (sense overlay) + `readOnly=false` (editable) →
  **editable dins la tab**, sense el `fixed inset-0`. Avui ModelSheet ja el munta `inline readOnly`; només
  cal alternar `readOnly`.

**2B · `task_id` sense navegar.** `openTaskAndGo`
([ModelSheet.jsx:120-127](../../frontend/src/pages/ModelSheet.jsx#L120)) fa `models.openTask(id, code)` **i
després** `navigate(...)`. La crida i la navegació són **independents**: `open_model_task_view`
([tasks/views_b.py](../../backend/fhort/tasks/views_b.py)) crea la tasca si cal + la posa `InProgress` +
retorna `{task_id}`. **Opcions (sense decidir):** (i) en entrar a mode edició cridar `openTask` i desar
`task_id` a estat local del ModelSheet (sense `navigate`); (ii) mantenir el `task_id` a estat mentre la tab
és en mode edició. Cap requereix canvi de ruta.

**2C · Compta-temps.** `transition_task`
([tasks/services_c.py:43](../../backend/fhort/tasks/services_c.py#L43)): `InProgress` obre `TimerEntrada`
(+ `started_at`, + tanca qualsevol altre `InProgress` del tècnic); `Paused`/`Done` tanca el timer. Avui el
timer s'**inicia** via `openTask`→`InProgress` (la navegació) i es **pausa** al **desmuntar la ruta**:
`EscalatTask.jsx:18-22` i `ModelMeasurements.jsx:50-54` fan `modelTasks.transition(taskId, {to_status:
'Paused'})` al cleanup. **Per a edició inline:** disparar `InProgress` en **entrar** a mode edició i `Paused`
en **sortir** (toggle a consulta, canvi de tab, o desmuntar ModelSheet) — mateixos endpoints, ancorats al
canvi de mode en comptes del canvi de ruta. Mapejat, no decidit.

**2D · Redundància i enllaços a reapuntar.** Un cop l'edició és inline, `ModelMeasurements` i `EscalatTask`
queden jubilables. Enllaços entrants a `/mesures`·`/escalat` (per reapuntar a la tab del ModelSheet):
| Font | ruta:línia | Destí |
|---|---|---|
| ModelSheet "Editar mesures" | [ModelSheet.jsx:259](../../frontend/src/pages/ModelSheet.jsx#L259) | inline (mode edició tab) |
| ModelSheet "Editar escalat" | [ModelSheet.jsx:247](../../frontend/src/pages/ModelSheet.jsx#L247) | inline (mode edició tab) |
| WorkPlan `pom`/`size_check`/`scaling` | [WorkPlan.jsx:26,29,31](../../frontend/src/components/model/WorkPlan.jsx#L26) | ModelSheet?tab=… (+openTask) |
| KanbanTasks (mides / size_check / scaling) | [KanbanTasks.jsx:652,691,710](../../frontend/src/pages/KanbanTasks.jsx#L652) | ModelSheet?tab=… |
| SizeMapSetup (import) | [SizeMapSetup.jsx:126](../../frontend/src/pages/SizeMapSetup.jsx#L126) | ModelSheet?tab=Mesures&session= |
| ModelFabric ("enrere") | [ModelFabric.jsx:286](../../frontend/src/pages/ModelFabric.jsx#L286) | ModelSheet?tab=Mesures |
| SizeCheckRedirect | [App.jsx:54](../../frontend/src/App.jsx#L54) | ModelSheet?tab=Mesures |

⇒ ~7-10 punts. La jubilació és **NETA** un cop l'edició inline funciona i els enllaços apunten a la tab.

---

## BLOC 3 — ELS ALTRES DEFECTES

**3A · Propagar a Escalat acumula columnes (BASE·FIT1·FIT2·FIT ACTUAL).**
Les columnes de versió surten de l'endpoint `grading-history` (Fase 2,
[views.py:grading_history_view](../../backend/fhort/models_app/views.py)) que torna **TOTES les
`GradingVersion`** del SizeFitting. Cada "Propagar a grading" (Fase 3 → `generate_grading_view new_version`)
crea **v+1** → s'acumulen com a columnes. **El GAP:** `ajustar-talla` (Fase 1) **neteja `ModelGradingOverride`**
(pins per cel·la, perquè la corba de la regla mani) — però això **NO és neteja de columnes de preses/versions**.
La neteja d'overrides ≠ poda de l'historial de versions. **On caldria decidir la neteja:** a l'acte conscient
Propagar (podar/superar versions antigues) o a `grading-history` (limitar les versions mostrades). ⚠️
**Tensió real amb la Fase 2** (que demanava "eix de versions visible"): cal decidir **quantes** versions es
mostren / si Propagar "parteix net". **Independent de D.**

**3B · Columna de presa BUIDA a /mesures.** Les columnes ("preses"/estadis) les construeix `base_stages_view`
([views.py:1618-1638](../../backend/fhort/models_app/views.py#L1618)): **events de `MeasurementChangeLog`
agrupats per `{context}@{segon}`**, amb snapshot carry-forward. Una columna apareix per **cada bucket
(context, segon)** amb almenys un `valor_nou` no nul. **Una columna "buida gravada"** surt quan un event de
log **no mapeja cap `BaseMeasurement` is_active visible** (p.ex. un POM després desactivat, o un write que
genera log sense valor displayable per a les files mostrades) → el bucket existeix a `stages` però `takes`
queda buit per a totes les files. És un **artefacte de dades a `MeasurementChangeLog`**, **independent de D**
(l'edició inline no el resol). La neteja viu a `base_stages_view` (descartar buckets sense cap valor
displayable) o a l'origen que crea el log espuri.

**3C · Layout "sota el sidebar".** **Confirmat conseqüència de 1C:** `/escalat` és un overlay `fixed inset-0`
que tapa el sidebar, i `/mesures` és una ruta separada sense les tabs del ModelSheet. **D (edició dins la tab)
ho resol d'arrel:** muntar `PropagatedEditor inline` (no overlay) i `CheckMeasureEditor` editables com a
contingut de la tab manté Shell + tabs + capçalera + watchpoint. ✅

---

## VEREDICTE

- **Com s'obre l'edició avui i per què surt fora del context (1):** els botons "Editar" **naveguen** a rutes
  germanes `/mesures` (ModelMeasurements) i `/escalat` (EscalatTask). Totes dues viuen dins el `Shell`
  (sidebar present), però **NO són el ModelSheet** → perden tabs/capçalera/watchpoint; i `/escalat` pinta un
  **overlay `fixed inset-0`** (PropagatedEditor sense `inline`) que tapa el sidebar. No és falta de Layout;
  és que l'edició és una **ruta separada**, no una **tab en mode edició**.
- **Què cal per a edició inline (2):** **res de nou als editors** — `CheckMeasureEditor` i `PropagatedEditor`
  ja són editables via `readOnly=false` i agnòstics a la ruta. Cal: (a) un **toggle de mode** consulta↔edició
  a la tab que alterni `readOnly`; (b) obtenir el **`task_id` sense navegar** (`models.openTask` → estat
  local); (c) **moure el cicle del timer** de mount/unmount de ruta a **enter/exit de mode edició**
  (`transition` InProgress/Paused); (d) `PropagatedEditor` editable cal `inline` (ja existeix) per evitar
  l'overlay.
- **Defectes que resol D:** **3C (layout)** ✅ d'arrel; i habilita la **jubilació neta (2D)** de
  ModelMeasurements/EscalatTask un cop reapuntats els ~7-10 enllaços. **Defectes INDEPENDENTS de D:** **3A**
  (acumulació de columnes de versió: poda a Propagar o límit a `grading-history`; en tensió amb l'eix de
  versions de la Fase 2 — decisió de domini) i **3B** (columna buida: artefacte de `MeasurementChangeLog`;
  filtrar buckets sense valor displayable a `base_stages_view`).
- **Ordre d'atac suggerit:** (1) **D — edició inline** a la tab del ModelSheet (toggle readOnly + openTask
  sense navegar + timer enter/exit + PropagatedEditor inline editable) → resol C i descontextualització; (2)
  **jubilar** ModelMeasurements/EscalatTask + reapuntar enllaços (Fase 4 que va quedar blocada, ara NETA); (3)
  **3A** decisió de poda/límit de versions; (4) **3B** filtre de buckets buits.
- **Dimensió:** D ≈ mitjana (ModelSheet: estat de mode + 2 toggles + timer lifecycle; reusa els editors tal
  qual). Jubilació ≈ petita-mitjana (esborrar 2 pàgines + reapuntar ~7-10 navegacions). 3A ≈ petita (decisió
  + 1 filtre/poda). 3B ≈ petita (1 filtre a `base_stages_view`).

*Fi de la diagnosi. No s'ha implementat res. Atura't aquí.*
