# DIAGNOSI_KANBAN_PLANIFICACIO — substrat per jubilar el Kanban global i fer-ne una "fulla de planificació"

> **Patró A · READ-ONLY ABSOLUT.** Cap fitxer de producte tocat, cap migració, cap escriptura.
> Staging (`fhort`), branca `dev`, NOMÉS `/var/www/ftt-staging`. Equip DIAGNOSI: director +
> investigadors (Explore, read-only) + documentador. Protocol: `.claude/PROTOCOL_FASE_B.md`.
> **Aquesta diagnosi NO decideix res.** Porta els FETS perquè l'Agus i el CTO decideixin, quan
> s'hi posin, si "jubilar+substituir" el Kanban és net o si el que toca és **transformar** el que
> ja existeix. Direcció contrastada: `.claude/TAXONOMIA_FLUX_MODEL.md` §8 punt 4.
> Data: 2026-06-21.

---

## 0. Com llegir aquest document

- **FET** = afirmació sobre el codi, sempre amb `fitxer:línia` (rutes relatives a `/var/www/ftt-staging`).
- **💡 PROPOSTA** = lectura/recomanació de disseny, sempre marcada i a la secció final, mai barrejada.
- Si una cosa no es pot determinar, es diu explícitament. Cap invenció.
- Verificació del documentador: els anclatges pivot (TechnicianQueueOrder, `plan_reorder_view`,
  callers de `recompute_for_technicians`, l'exclusió a `transition_task`, la primera columna) s'han
  re-grepat a mà. La resta és report d'investigador, marcat quan no s'ha re-verificat camp a camp.

---

## Titular per a la decisió

El **substrat de la "cua de models per tècnic" JA EXISTEIX i és VIU** (motor scheduler determinista +
`TechnicianQueueOrder` + `recompute_for_technicians` + la pestanya "Assignades" de `Planning.jsx` amb
semàfor de risc). El que **NO existeix** és el **disparador per maduresa** (el recompute és sempre
imperatiu: reassignació, reorder, fitting — mai "el model ha avançat") i les **nocions de primera
classe** que la fulla necessitaria (maduresa del model, tasca capdavantera, data per tasca, risc com
a camp). Per tant la fulla és, sobretot, **D-6 amb cara nova** per a la mecànica de cua, **+ derivació
fresca** per a maduresa/capdavantera/risc. El detall, a la §💡 PROPOSTA.

L'**exclusió un-InProgress-per-tècnic viu al SERVEI** (`transition_task`), no al kanban → sobreviu a
jubilar-lo. El dashboard-del-model i la tasca externa lliure ja en depenen sense passar pel kanban.

---

# PREGUNTA 1 — Què fa el Kanban global AVUI?

## 1.1 Frontend (FET)

- **Ruta:** `tasques/kanban` → `KanbanTasks` (lazy import `frontend/src/App.jsx:31`, route `frontend/src/App.jsx:138`).
- **Layout:** graella de **5 columnes fixes** `gridTemplateColumns: '230px repeat(4, minmax(0,1fr))'`
  (`frontend/src/pages/KanbanTasks.jsx:379-383`):
  - **Columna 1 = MODELS** (`KanbanTasks.jsx:384-440`): llista paginada de models + **cartes de gate**
    (validació de fase) a dalt. Cada model mostra els seus comptadors per estat (pending/paused/in_progress/done).
  - **Columnes 2–5 = ESTATS DE TASCA** del model SELECCIONAT (`KanbanTasks.jsx:442-472`): `Pending`,
    `Paused`, `InProgress`, `Done` (`COLUMNS` a `KanbanTasks.jsx:20-25`). **Només es poblen quan es
    clica un model** a la columna 1; el filtre per columna és `tk.status === col.key` (`KanbanTasks.jsx:444`).
- **Agrupació:** per **model** (no per tècnic, no per fase). Selecciones un model → en veus les tasques per estat.
- **Filtres:** cerca (`:70,273`), ordenació + direcció (`:78-79,279`), temporada (`:80,296`), estat del
  model (`:81,301`), responsable/assignee (`:82,308`), any (`:84,291`), tipus de peça i prioritat
  ("més filtres", `:83,365` / `:85,371`). Ordre per defecte de la columna models el dona el backend.
- **Components compartits vs locals:** només **`TimerWidget`** és extern i reutilitzat (import
  `KanbanTasks.jsx:6`; també a `TimeTracking.jsx`). Tota la resta és **inline i NO exportat**: `TaskCard`
  (`:604-714`), `GateRow` (`:553-601`), `ModelRow` (`:527-551`), `ColTitle`/`Count`/`ColorDot` (`:494-525`).

## 1.2 Backend (FET)

- **Endpoints que l'alimenten** (`tasks/urls.py`, `tasks/views_b.py`):
  - `GET model-task-items/by-model/` → `ModelTaskViewSet.by_model` (`tasks/views_b.py:90`). Una fila per
    model amb `counts:{pending,paused,in_progress,done}` calculats a BD via `Count(filter=Q(status=...))`
    (`tasks/views_b.py:162-188`); forma a `shape()` (`:190-208`). Ordre per defecte
    `('-in_progress','-pending','-paused','model__codi_intern')` (`:88`). **Re-verificat** (coincideix amb
    `docs/DIAGNOSI_DASHBOARD_FONTS.md` font 1).
  - `GET model-task-items/` → `ModelTaskViewSet` (`tasks/views_b.py:53`), `filterset_fields = ['model','status','task_type','assignee']`.
  - `POST model-task-items/<pk>/transition/` → `transition_task_view` (`tasks/views_b.py:356`), body `{to_status}`.
  - `GET models/<id>/task-log/` → `model_task_log_view` (`tasks/views_b.py:295`).
  - Gates: `GET gates/ready/` (`tasks/views_b.py:461`), `POST models/<id>/gate/` (`:391`), `regress/` (`:417`), `gates/bulk/` (`:439`).
- **Models de dades** (`tasks/models.py`): `ModelTask` (`:201-234`) — `status` STATUS_CHOICES
  `Pending/Paused/InProgress/Done` (`:203`), `assignee` FK null (`:208`), `order` (`:210`),
  `started_at/finished_at` (`:211-212`), `estimated_minutes` (`:213`), `planned_start/end/locked`
  (`:216-221`), `unique_together(model,task_type)` (`:231`). `TaskType` code SlugField + name (`:185-198`).
  `TaskTransition` (`:237-253`) log immutable `from_status/to_status/by/at`.
- **`transition_task`** (`tasks/services_c.py:42`): aplica la transició i, en entrar a `InProgress`,
  **pausa l'altra `InProgress` del mateix tècnic** (tanca timer + log) — l'**exclusió** és a
  `services_c.py:54-63` (re-verificat). També: obre/tanca `TimerEntrada` (`:19-31`), auto-assigna si
  `assignee` és null (report `:78-79`), marca `Model.fase_actual='Dev'` + meritació a la primera tasca
  (report `:91-119`), i `record_actual_time` (Welford) en `Done` (report `:124-125`). **Viu al SERVEI,
  `@transaction.atomic`, reutilitzable** — no acoblat a cap view del kanban.

## 1.3 La PRIMERA COLUMNA (backlog/entrada) — AÏLLADA de les columnes d'estat (FET)

> Aquesta és la peça que la taxonomia §8.4 diu que "sobreviu" del kanban actual.

- **NO existeix una columna "Backlog" separada** ni al frontend ni al backend (confirmat per dos
  investigadors). El kanban té: columna 1 = **models** (amb cartes de gate i comptadors), columnes 2–5 =
  **estats de tasca** del model seleccionat. (`KanbanTasks.jsx:379-472`).
- **"Tasca no començada / d'entrada" = `status='Pending'`**, l'estat inicial (`ModelTask.status` default
  `'Pending'`, `tasks/models.py:203`); transició d'arrencada `Pending→InProgress` (`KanbanTasks.jsx:29`).
  Al frontend és simplement la columna 2 (`tk.status === 'Pending'`).
- **Com es consultaria el backlog** (FET, sense entitat pròpia): és una **agregació**, no una taula.
  - Per model: `counts.pending` de `by-model` (`tasks/views_b.py:170`); el filtre per defecte d'aquest
    endpoint ja amaga models sense cap tasca activa (`Q(pending>0)|Q(paused>0)|Q(in_progress>0)`, `:188`).
  - Global de tasques d'entrada: `GET model-task-items/?status=Pending` (+ `&assignee__isnull=true` si es
    vol "no assignades"), via `filterset_fields` (`tasks/views_b.py:53`). **Aquest filtre existeix; no hi
    ha un endpoint "backlog" dedicat.**

---

# PREGUNTA 2 — Qui DEPÈN del Kanban global?

## 2.1 Què trencaria si es jubilés (FET)

**Frontend** — el kanban és força autocontingut:
- Els seus components de pintura (`TaskCard`, `GateRow`, `ModelRow`…) són **inline i NO exportats**
  (`KanbanTasks.jsx:494-714`) → **es perdrien**, però ningú més els importa (cap altra pantalla en depèn).
- Els seus **endpoints són compartits** (no exclusius del kanban): `model-task-items/by-model/` i
  `model-task-items/` també els crida `Planning.jsx:114-115`; `transition/` també el criden
  `TechSheetEditor.jsx:558` (a `Paused` en desmuntar, fire-and-forget) i el dashboard del model (F1).
  → jubilar el kanban **no** trenca aquests endpoints.
- `TimerWidget` és compartit (`TimeTracking.jsx`) → sobreviu.

**Backend** — res depèn del kanban com a tal:
- `transition_task` (servei) el criden, fora del kanban: la reassignació PATCH (`tasks/views_b.py`),
  obrir POMs (`models_app/views.py`, report `:530-545`), tancar size check
  (`models_app/services_size_check.py`, report `:237-244`). **El servei és el punt de veritat, no la view.**
- **Signals:** `tasks/signals.py` emet `model_consumption_started` des de `transition_task` (report
  `signals.py:17`); **no hi ha cap `@receiver(post_save, sender=ModelTask)`** ni automatisme lligat a
  `ModelTask`/`TaskTransition` (report, grep negatiu). L'estat de tasca **no té lògica acoblada al kanban**.

## 2.2 El sprint "cicle de vida tasques Kanban" — quant existeix i ON viu (FET)

> Classificació clau: **VIU AL SERVEI** (sobreviu a jubilar el kanban) vs **ACOBLAT AL KANBAN** (es perdria).

| Peça del cicle de vida | Implementat? | On viu | Servei o Acoblat |
|---|---|---|---|
| Exclusió un-InProgress-per-tècnic | **SÍ** | `transition_task` (`services_c.py:54-63`) | **SERVEI** ✅ |
| Auto-pausar l'altra InProgress del tècnic | **SÍ** | `services_c.py:58-63` | **SERVEI** ✅ |
| Timer server-side en InProgress | **SÍ** | `services_c.py:19-31` + `TimerEntrada` | **SERVEI** ✅ |
| `Model.fase_actual: Pending→Dev` en arrencar | **SÍ** | report `services_c.py:91` | **SERVEI** ✅ |
| Meritació (ConsumptionRecord + signal) a la 1a tasca | **SÍ** | report `services_c.py:96-119` | **SERVEI** ✅ |
| Rectificacions (Done→InProgress) | **SÍ** | `TaskTransition` log, report `services_c.py:130-133` | **SERVEI** ✅ |
| Welford (temps real) en Done | **SÍ** | report `services_c.py:124-125`→`services_i.py` | **SERVEI** ✅ |
| Obrir POM/SizeCheck → auto transició | **SÍ (parcial)** | trigger al **frontend** (`KanbanTasks.jsx:646`, `TechSheetEditor.jsx:558`, `models_app/views.py` report); lògica al servei | **SEMI** (trigger UI, lògica servei) |
| Auto-tancar tasca POM | **NO** (report: no existeix automatisme) | — | — |
| Auto-transicions sense clic (Pending→…→Done) | **NO** (report) | — | — |
| "Models amb tasques en curs a dalt" (ordenació) | **SÍ** | `KanbanTasks.jsx:227-228` (sort frontend) | **ACOBLAT** ❌ |
| UI de transicions manuals (botons d'estat) | **SÍ** | `TaskCard` inline (`KanbanTasks.jsx:604-714`) | **ACOBLAT** ❌ |
| Validació de gates (cartes) | **SÍ** | `GateRow` inline (`KanbanTasks.jsx:553-601`) + `gates/ready` | **ACOBLAT (UI)** ❌ |

**Conclusió P2 (FET):** gairebé tot el "cicle de vida" substantiu (exclusió, timer, meritació, fase,
Welford, log) **viu al servei i sobreviu**. El que és **acoblat al kanban** és **UI**: les targetes de
transició manual, l'ordenació "actius a dalt" i les cartes de gate. Cap dependència de dades es trencaria.

---

# PREGUNTA 3 — Què ja existeix de la "cua per tècnic" / planificació?

## 3.1 Les pàgines de Planificació (FET)

- **`Planning.jsx`** — ruta `/planificacio` (`App.jsx:36,143`). **Per al PM** (gated `define_tasks`/`configure`,
  report `Planning.jsx:96`). Dues pestanyes (report `:101`):
  - **"Pendents":** models sense tasques no-Done assignades (per assignar via wizard).
  - **"Assignades":** **agrupat per tècnic** (`assignedGroups`, report `:167`); **cada grup és la cua
    de models d'aquell tècnic, reordenable per drag&drop** (`@dnd-kit`, report `:205-218`). Per model:
    `codi`, `planned_start`, minuts estimats, `planned_end`, **semàfor de risc** (on_track/at_risk/critical),
    expandible a tasques. → **Això JA és una "fulla de planificació" per tècnic, amb cara de PM.**
  - Crida: `model-task-items/by-model/?all=true` + `model-task-items/` + `users/` + `POST plan/reorder/`
    (report `Planning.jsx:114-116,213`).
- **`PlanningCalendar.jsx`** — ruta `/planificacio/calendari` (`App.jsx:37,146`). **Per al tècnic**
  (qualsevol autenticat; veu el seu propi perfil, scope `view_team_tasks`). Calendari agenda (dia/setmana/
  mes/llista) amb blocs de durada. Crida `company-calendar/` + `calendar/events/` (report `:105-127`).
  Unifica 3 fonts: tasques planificades + confecció (Production) + fitting (FittingSession).
- **Backend planning** (`planning/urls.py`, `planning/views.py`): `plan/compute/` (`:96`), `plan/preview/`
  (`:114`), `plan/apply/` (`:133`), `plan/current/` (gantt read-only, `:167`), `calendar/events/` (`:213`),
  **`plan/reorder/` (`:494`)**, `plan/eligible-technicians/` (`:531`), `plan/assign-batch/` (`:585`).
  *(Línies de view: report d'investigador; els pivots reorder/recompute re-verificats — veure 3.2.)*

## 3.2 `TechnicianQueueOrder` i el motor (FET, re-verificat)

- **Model** (`planning/models.py:72-94`): `profile` FK→UserProfile `related_name='queue_orders'` (`:80`),
  `model` FK→Model `related_name='queue_orders'` (`:82`), `position` PositiveInteger (`:84`).
  `unique_together(('profile','model'))` (`:87`), `ordering=['profile_id','position']` (`:88`).
- **Naturalesa CLAU** (docstring `:73-79`, re-verificat): **és SPARSE — només es crea fila quan l'usuari
  reordena explícitament.** Assignar NO crea fila (el model nou va al final). L'scheduler prioritza els
  models amb fila pel seu `position`; els sense fila van per ordre natural (prioritat→data_objectiu→codi).
  → **La cua per tècnic és una PROJECCIÓ que calcula l'scheduler**; `TechnicianQueueOrder` només hi aporta
  els overrides manuals. (Encaixa literalment amb taxonomia §8.4: "la cua és una projecció ordenada, no
  una entitat que posseeix tasques".)
- **Escriptors:** `plan_reorder_view` (`update_or_create`, `planning/views.py:521`) i `cleanup_queue_order`
  (delete quan el tècnic ja no té tasques del model, report `plan_service.py:62-76`).
- **Lectors:** l'scheduler `_manual_positions(...).values_list('model_id','position')`
  (report `scheduler_service.py:61-69`). **Viu i actiu** (s'omple i es consulta), no esquelet.
- **`recompute_for_technicians(profile_ids)`** (report `plan_service.py:48-59`): recalcula la cua sencera
  (totes les no-Done) d'un tècnic cridant `schedule(..., save=True)`. **Tots els disparadors són
  IMPERATIUS** (re-verificat amb grep):
  - reassignació de tasca: `tasks/views_b.py:253`
  - reorder manual: `planning/views.py:523`
  - assign/assign_batch: `planning/plan_service.py:210,335,375`
  - ocupació/alliberament de fitting: `fitting/services.py:184,268,648,785`
  - **CAP disparador per maduresa / gate / progrés real.** (FET: grep negatiu confirmat.)
- **`estimated_minutes`** (`tasks/models.py:213`): snapshot congelat en crear la tasca; **NO es re-ajusta**
  per aprenentatge ni dispara recompute. `planned_start/end/locked` (`:216-221`): escrits/llegits per
  l'scheduler; `planned_locked` respectat. Coincideix amb `docs/DIAGNOSI_FASE_B.md` (D-6: estimated
  congelat, recompute no disparat per maduresa).

## 3.3 Les 4 nocions que la fulla necessitaria — existeixen avui? (FET)

| Noció | Estat | Com s'obtindria / on és | fitxer:línia |
|---|---|---|---|
| **Maduresa del model** (% tasques Done, fase…) | **NO EXISTEIX** com a camp/càlcul | Es derivaria de `model_tasks.filter(status='Done').count()/total`; `fase_actual` existeix però no és "maduresa" | `tasks/models.py:203` (status), `models_app/models.py:202` (fase) |
| **Tasca capdavantera** (següent pendent ordenada) | **IMPLÍCITA, no de primera classe** | Es derivaria `filter(status!='Done').order_by('order').first()`; l'scheduler ja ordena però no hi ha endpoint que retorni "la següent" | `tasks/models.py:210` (order); scheduler report `scheduler_service.py:47-69` |
| **Data informada** | **PARCIAL** | `Model.data_objectiu` existeix i l'usa l'scheduler per l'ordre natural; **no hi ha data per tasca** (`planned_end` és predicció, no compromís) | `models_app/models.py` (`data_objectiu`, report); scheduler report `:49-53` |
| **Risc / urgència** | **AD-HOC, no persistent** | Es calcula al vol comparant `planned_end > data_objectiu` (a `assign_batch`, report `plan_service.py:337-353`) i el semàfor `calcViabilitat` al frontend (`ModelSheet.jsx:54-64`, `Planning.jsx`); **no és camp de BD** | report `plan_service.py:347`; `frontend/.../ModelSheet.jsx:54-64` |

---

# 💡 PROPOSTA (a validar per l'Agus i el CTO) — separada dels fets

> Tot el que segueix és lectura de disseny, no decisió ni implementació.

## A. La "fulla de planificació": D-6 amb cara nova o construcció fresca?

**Veredicte: majoritàriament D-6 amb cara nova per a la MECÀNICA de cua; construcció fresca (derivació)
per a les NOCIONS de model.** Desglossat:

- **Ja hi és el substrat (cara nova, no construcció):**
  - Motor d'scheduling determinista per tècnic (`scheduler_service.schedule`), respecta calendari laboral,
    locks i ordre manual.
  - `TechnicianQueueOrder` (override manual) + `recompute_for_technicians` (recàlcul de cua sencera).
  - Una UI de cua-per-tècnic amb risc **ja existeix** a `Planning.jsx` pestanya "Assignades" — però amb
    **cara de PM** (global, totes les cues). La fulla de la taxonomia és la **mateixa dada amb cara de
    tècnic** (la MEVA cua) i amb el **model com a unitat** (no la tasca).
  - `data_objectiu`, `planned_*`, semàfor de risc: tots derivables del que ja es calcula.

- **Falta substrat (construcció fresca):**
  1. **Disparador per maduresa.** Avui `recompute` és 100% imperatiu; la taxonomia vol que la cua/estimació
     "respiri" amb la maduresa. **No hi ha cap trigger per progrés del model.** (Lligat a D-6 obert.)
  2. **"Maduresa del model" com a noció llegible** (avui no existeix; cal derivar-la o materialitzar-la).
  3. **"Tasca capdavantera" com a dada de primera classe** (avui implícita en l'ordre; cap endpoint la dóna).
  4. **Endpoint "la MEVA cua de models" amb cara de tècnic** (avui la cua es veu només des de la pantalla
     de PM; el dashboard del model és per-model, no hi ha el zoom-out per-tècnic orientat a l'executor).
  5. **Risc/data com a contracte estable** (avui ad-hoc al vol; si la fulla els mostra com a senyal
     d'acció, convé decidir si es persisteixen o es recalculen sempre).

**En una frase:** el motor i la taula de cua són **D-6 amb cara nova**; la **maduresa que governa el
recompute i les nocions de model (capdavantera, risc llegible)** són **construcció fresca**, i és
exactament el tros que `docs/DIAGNOSI_FASE_B.md` ja cataloga com a D-6 obert.

## B. Acoblaments a desfer ABANS de poder jubilar el kanban global amb seguretat

1. **UI de transició manual.** Les targetes d'estat (`TaskCard`, botons Pending→InProgress→Done) viuen
   **només dins el kanban** (`KanbanTasks.jsx:604-714`). El "Q4 crescut" del dashboard del model (taxonomia
   §8.4: columnes d'estat dins el model) ha de **reproduir aquesta UI** consumint el servei `transition_task`
   (que ja és reutilitzable) abans de retirar el kanban. *Cap canvi de backend; només re-ubicar UI.*
2. **Validació de gates.** Les cartes de gate (`GateRow`, `gates/ready`) viuen a la columna 1 del kanban
   (`KanbanTasks.jsx:553-601`). Cal decidir on van (dashboard del model? fulla de planificació?) abans de jubilar.
3. **Ordenació "models actius a dalt".** Lògica de frontend local al kanban (`KanbanTasks.jsx:227-228`);
   si es vol conservar, s'ha de reimplementar a la nova superfície.
4. **Cap acoblament de dades a desfer.** Els endpoints (`by-model`, `transition`, gates) i el servei
   `transition_task` (amb exclusió, timer, meritació, Welford) **són compartits i sobreviuen** — `Planning.jsx`,
   `TechSheetEditor.jsx` i el dashboard F1 ja els consumeixen sense passar pel kanban. Això fa la jubilació
   **neta a nivell de dades**: el risc és només de **cobertura d'UI**, no de trencar lògica.
5. **Disciplina (taxonomia §8.4):** construir el nou (kanban-del-model + fulla) **al costat** del global;
   jubilar-lo d'una passada conscient quan l'Agus confirmi que les peces noves el cobreixen del tot.

## C. Primera peça quan s'executi (proposta de seqüència)

Diagnosi → ja feta aquí (read-only). La **primera peça d'implementació** raonable seria un **endpoint
read "la meva cua de models per tècnic"** (zoom-out orientat a l'executor) que **projecti** el que
l'scheduler ja calcula + derivi tasca capdavantera + risc — additiu, sense tocar el kanban. D'aquí es
veuria si cal materialitzar maduresa o n'hi ha prou amb derivar-la. Reordena, com diu la taxonomia, D-4
(catàleg de tasques), D-6 (planificació per maduresa) i el sprint "cicle de vida tasques Kanban".

---

# Apèndix — fora d'scope detectat (ANOTAT, no tocat)

- **`docs/DIAGNOSI_FASE_B.md` D-13** (report Pregunta 3B): `record_actual_time` perdria la FK al model i
  descarta la mostra sense `garment_type_item` — afecta la qualitat de la convergència D-6. Deute conegut,
  no tocat.
- **`Model.predicted_start/predicted_end`** (report): es desen però cap view els llegeix (les tasques
  `planned_*` sí). Possible dada morta; a confirmar quan s'obri D-6. No tocat.
- **`TechnicianQueueOrder` sense constraint d'unicitat de `position`** (per disseny: duplicats transitoris
  durant reorder bulk, garantit per `transaction.atomic` a l'endpoint, `planning/models.py:77-79`). No és
  bug; anotat perquè qualsevol lectura de la cua ha d'ordenar per `position` assumint possibles col·lisions
  transitòries.

---

*Document de diagnosi. READ-ONLY respectat: l'únic fitxer escrit és aquest. Cap codi de producte,
migració ni config modificats. Anclatges pivot (cua per tècnic, reorder, callers de recompute, exclusió,
primera columna) re-verificats pel documentador; la resta marcada com a report d'investigador.*
