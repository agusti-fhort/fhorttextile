# DIAGNOSI — EL CICLE DE TASCA, FINS A L'ÚLTIMA CONSEQÜÈNCIA

Data: **2026-08-04** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
BD mesurada: `ftt_staging` (PG18, port 5433), schema `fhort`. Logs: `/var/log/nginx/ftt-staging-access.log`.

**Abast.** Tot el cicle de vida de `ModelTask`: qui l'obre, qui la tanca, qui no la toca, quant
temps en surt registrat, què n'aprèn el motor de temps i quina exclusió mútua hi ha de debò.

**Convenció.** Cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
(no especulat). Les xifres de BD són consultes `SELECT` fetes avui; el SQL va inline al text.
Les propostes van marcades `💡 PROPOSTA (a validar)` i **no** són decisions.

---

## RESUM EXECUTIU — les set coses que cal saber abans de decidir res

1. **El temps no es mesura perquè la tasca està tancada mentre es treballa.** El rellotge corre
   NOMÉS entre `enterEdit` i `exitEdit` de la superfície ([ModelSheet.jsx:225-247](frontend/src/pages/ModelSheet.jsx#L225-L247)).
   Tot el que es fa fora d'aquest parèntesi —consultar la taula, pujar fitxers, propagar grading,
   editar el `.ftt` des de "Modificar"— **no obre cap tasca i no compta cap minut**.

2. **El cas d'Agus és exacte i té una sola línia.** El botó "Modificar" del tab Fitxa tècnica és
   [ModelSheet.jsx:927](frontend/src/pages/ModelSheet.jsx#L927) i navega a `/models/:id/ftt/:fitxerId`
   **sense `task_id`**. L'editor llegeix `task_id` de la query ([TechSheetEditor.jsx:2566](frontend/src/pages/TechSheetEditor.jsx#L2566)),
   no en troba cap, i per tant **ni obre, ni reobre, ni reassigna, ni pausa res** — mentre autodesa
   cada 2 segons ([TechSheetEditor.jsx:3585-3622](frontend/src/pages/TechSheetEditor.jsx#L3585-L3622)).
   No és un bug amagat: està escrit i assumit al comentari [ModelSheet.jsx:774-775](frontend/src/pages/ModelSheet.jsx#L774-L775).

3. **El ping-pong és REAL i està mesurat.** Una sola `ModelTask` (id 250, model 186, `pom`) ha
   generat **17 transicions →Done** i per tant **17 mostres Welford**. De les 49 transicions →Done
   del tenant, **28 són repeticions sobre una tasca que ja havia estat tancada** (57 %).
   El punt exacte on s'obre-i-es-tanca en el mateix request:
   [models_app/views.py:1615-1618](backend/fhort/models_app/views.py#L1615-L1618).

4. **El motor de temps ja menteix en les DUES direccions, i ja mana.** La cel·la (item 22 × `pom`)
   diu **562 min de mitjana amb n=17** quan les 17 mostres surten d'**una sola tasca** de 760 min.
   La cel·la (item 5 × `pom`) diu **4 min amb n=5** i, com que n ≥ `WELFORD_MIN_SAMPLES`
   ([services_i.py:10](backend/fhort/tasks/services_i.py#L10)), **substitueix el seed de 30 min**.
   L'empíric global de `pom` (graó 2 de la cascada) és avui **283 min** contra una `TimeSeed` de 35.

5. **El modal d'1 minut no és un bug del guard: és una clau de QA que ha quedat encesa al
   navegador.** El llindar es llegeix de `localStorage` a la càrrega del mòdul
   ([GuardTascaOblidada.jsx:34-41](frontend/src/components/GuardTascaOblidada.jsx#L34-L41)).
   Mesurat: els batecs de la BD arriben als **63 s, 90 s** de l'obertura del tram → el llindar
   efectiu és **1 minut**, no 30. El comentari diu "per sessió de navegador" i és FALS:
   `localStorage` no caduca.

6. **L'exclusió mútua NO és per model. Ja és per tècnic** — i està trencada. La premissa del brief
   està invertida: [services_c.py:206](backend/fhort/tasks/services_c.py#L206) filtra per `assignee`,
   no per model. **Cap mutex per model existeix** (l'únic lock del sistema és el del document `.ftt`,
   [ftt_models.py:11](backend/fhort/models_app/ftt_models.py#L11)). I la invariant es trenca sola
   quan qui treballa ≠ qui té assignada la tasca: **hi ha un cas real a la BD** de dos trams
   simultanis del mateix tècnic (timers 116 i 117).

7. **Obrir una porta té conseqüències de facturació.** La primera `→InProgress` de qualsevol tasca
   **merita el model** (`ConsumptionRecord` + event a `public`,
   [services_c.py:238-258](backend/fhort/tasks/services_c.py#L238-L258)) i reancora el pla
   ([views_b.py:587-594](backend/fhort/tasks/views_b.py#L587-L594)). Tocar una porta 3 segons per
   error factura. Verificat a BD: `merited_at` == `started_at` de la primera tasca, en els 21 registres.

> ⚠️ **El model 195 NO EXISTEIX a staging.** `SELECT * FROM fhort.models_app_model WHERE id=195` →
> 0 files. El tenant té 45 models (ids 162…1307, amb el forat 189-246). Tampoc no hi ha **cap**
> traça de `models/195` a cap access log de nginx del servidor. Els `TaskTransition`/timers d'aquell
> matí **no són a aquesta BD** i no es poden reconstruir. Q3 es respon amb el corpus que SÍ hi és
> (49 →Done, 217 timers, i la sessió real d'avui sobre el model **188**), que dona la mateixa
> conclusió amb proves vives. Si el 195 era a PROD, el dump del 04/08 és de les 02:30 i tampoc no
> el tindria.

---

## BLOC Q1 — EL MAPA COMPLET DEL CICLE

### Q1.1 · Les úniques quatre portes del backend que toquen `ModelTask`

| # | Porta backend | Què fa | Fitxer:línia |
|---|---|---|---|
| A | `POST /api/v1/models/<id>/open-task/` | crea-si-falta + `→InProgress` (o *claim* si ja és En curs d'altri) | [views_b.py:518-622](backend/fhort/tasks/views_b.py#L518-L622) |
| B | `POST /api/v1/model-task-items/<pk>/transition/` | transició explícita (`InProgress`/`Paused`/`Done`) | [views_b.py:426-462](backend/fhort/tasks/views_b.py#L426-L462) |
| C | `POST /api/v1/model-task-items/<pk>/claim/` | reassigna a mi, **sense tocar estat ni timer** | [views_b.py:465-515](backend/fhort/tasks/views_b.py#L465-L515) |
| D | `PATCH /api/v1/model-task-items/<pk>/` | assignació de planificació (gate `define_tasks`) | [views_b.py:44-59](backend/fhort/tasks/views_b.py#L44-L59) |

Tot passa per **una sola** màquina d'estats, `transition_task`
([services_c.py:177-294](backend/fhort/tasks/services_c.py#L177-L294)), amb
`ALLOWED` a [services_c.py:11-16](backend/fhort/tasks/services_c.py#L11-L16):

```
Pending    → {InProgress}
Paused     → {InProgress}
InProgress → {Paused, Done}
Done       → {InProgress}   ← reobertura = rectificació
```

A més, **dos serveis de domini** obren-i-tanquen la tasca dins del seu propi request (§Q3):
- `_close_pom_task_for_model` — [models_app/views.py:1597-1619](backend/fhort/models_app/views.py#L1597-L1619)
- resolució de size check — [services_size_check.py:284-288](backend/fhort/models_app/services_size_check.py#L284-L288)

### Q1.2 · TAULA: porta d'usuari × comportament (la columna «res» és la que buscàvem)

| Porta (gest de l'usuari) | Obre? | Reobre (Done→InProgress)? | Reassigna? | Pausa en sortir? | Fitxer:línia |
|---|---|---|---|---|---|
| **Tab Mesures → "Editar mides"** | ✅ `openTask('pom')` | ✅ (open-task és idempotent) | ✅ (branca claim) | ✅ `exitEdit` | [ModelSheet.jsx:225-240](frontend/src/pages/ModelSheet.jsx#L225-L240) · [:241-247](frontend/src/pages/ModelSheet.jsx#L241-L247) |
| **Tab Escalat → "Editar graduació"** | ✅ `openTask('grading')` | ✅ | ✅ | ✅ | [ModelSheet.jsx:682-688](frontend/src/pages/ModelSheet.jsx#L682-L688) |
| **Tab Mesures amb `?task_id=` (J1b)** | ❌ consumeix la que ve | ❌ | ❌ | ✅ (registra `activeTaskRef`) | [ModelSheet.jsx:291-300](frontend/src/pages/ModelSheet.jsx#L291-L300) |
| **Tab Mesures amb `?fitting_session=`** | ✅ `openTask('size_check')` | ✅ | ✅ | ✅ | [ModelSheet.jsx:318-331](frontend/src/pages/ModelSheet.jsx#L318-L331) |
| **`?mode=entry` (Definició POM)** | ✅ `enterEdit('Mesures','pom')` | ✅ | ✅ | ✅ | [ModelSheet.jsx:344-351](frontend/src/pages/ModelSheet.jsx#L344-L351) |
| **`/models/:id/escalat` (autoEdit)** | ✅ | ✅ | ✅ | ✅ | [ModelSheet.jsx:278-283](frontend/src/pages/ModelSheet.jsx#L278-L283) |
| **Menú lateral → "Fitxa tècnica"** (`/fitxa-tecnica`) | ✅ `openTask('tech_sheet')` | ✅ | ✅ | ✅ (a l'unmount de l'editor) | [TechSheetEntry.jsx:40-68](frontend/src/pages/TechSheetEntry.jsx#L40-L68) · [TechSheetEditor.jsx:3391-3403](frontend/src/pages/TechSheetEditor.jsx#L3391-L3403) |
| 🔴 **Tab Fitxa tècnica → "Modificar"** | ❌ **RES** | ❌ **RES** | ❌ **RES** | ❌ **RES** | **[ModelSheet.jsx:927](frontend/src/pages/ModelSheet.jsx#L927)** |
| 🔴 **Tab Fitxa tècnica → "Previsualitzar"** | ❌ RES (idèntic a Modificar) | ❌ | ❌ | ❌ | [ModelSheet.jsx:924](frontend/src/pages/ModelSheet.jsx#L924) |
| 🔴 **Tab Fitxa tècnica → "Crear fitxa tècnica"** | ❌ RES (resolver sense `task_id`) | ❌ | ❌ | ❌ | [ModelSheet.jsx:863](frontend/src/pages/ModelSheet.jsx#L863) |
| 🔴 **Tab Fitxa tècnica → "Nova fitxa"** | ❌ RES | ❌ | ❌ | ❌ | [ModelSheet.jsx:801](frontend/src/pages/ModelSheet.jsx#L801) |
| **Pla de treball (Dashboard) → Play (meva)** | ✅ `openTask(code)` | ✅ | ✅ | depèn de l'eina | [WorkPlan.jsx:251-278](frontend/src/components/model/WorkPlan.jsx#L251-L278) |
| **Pla de treball → Play (d'altri) + handoff** | ✅ | ✅ | ✅ `claim` | ídem | [WorkPlan.jsx:289-306](frontend/src/components/model/WorkPlan.jsx#L289-L306) |
| **Pla de treball → Pause / Stop** | — | Stop sobre Paused fa `InProgress`+`Done` encadenats | — | — | [WorkPlan.jsx:320-337](frontend/src/components/model/WorkPlan.jsx#L320-L337) |
| **Tab Tasques → arbre "Iniciar"** | ✅ `openTask(code)` | ✅ | ✅ | ídem | [TaskTree.jsx:110-128](frontend/src/components/model/TaskTree.jsx#L110-L128) |
| **Taller de patró** (`/models/:id/patro/taller`) | ✅ `openTask('pattern_digit')` si no ve `?task_id=` | ✅ | ✅ | ✅ | [TallerPatro.jsx:199-227](frontend/src/pages/TallerPatro.jsx#L199-L227) |
| 🔴 **Tab Patró** (dins el ModelSheet) | ❌ **RES** — `PatternTab.jsx` no conté cap referència a tasques (grep: 0 coincidències de `openTask|transition|task_id`) | ❌ | ❌ | ❌ | [PatternTab.jsx](frontend/src/components/pattern/PatternTab.jsx) |
| **Mesures en mode sessió → "Gravar i tornar"** | — | — | — | **tanca a `Done`** | [SessionActions.jsx:44](frontend/src/components/model/SessionActions.jsx#L44) |
| **Mesures en mode sessió → "Descartar canvis"** | — | — | — | pausa | [SessionActions.jsx:54](frontend/src/components/model/SessionActions.jsx#L54) |
| 🔴 **Kanban** | **NO EXISTEIX** — no hi ha cap `Route` `tasques/kanban` a [App.jsx:294-410](frontend/src/App.jsx#L294-L410); [ModelFabric.jsx:120](frontend/src/pages/ModelFabric.jsx#L120) hi navega i cau al catch-all `*` → `/` | | | | |
| 🔴 **Llista de tasques / Planificació** | ❌ RES (només `PATCH assignee` i `DELETE`) | ❌ | ✅ només PATCH | ❌ | [Planning.jsx:251](frontend/src/pages/Planning.jsx#L251) · [:261](frontend/src/pages/Planning.jsx#L261) |
| 🔴 **Llista de models / Dashboard (targeta → model)** | ❌ RES | ❌ | ❌ | ❌ | [Dashboard.jsx:79](frontend/src/pages/Dashboard.jsx#L79) (`ModelCard`, només `navigate`) |
| 🔴 **"Editar model" (wizard, `/models/:id/editar`)** | ❌ RES | ❌ | ❌ | ❌ | [App.jsx:340](frontend/src/App.jsx#L340) |
| 🔴 **Pujar fitxers al model** | ❌ RES | ❌ | ❌ | ❌ | [models_app/views.py:2140](backend/fhort/models_app/views.py#L2140) |
| 🔴 **Propagar a grading (`generar-grading`)** | ❌ RES | ❌ | ❌ | ❌ | (cap `transition_task` al camí; grep exhaustiu a Q1.1) |
| 🔴 **Editar cel·les de la taula de mides** (`PATCH base-measurements/`, `escalat/ajustar-talla/`) | ❌ RES | ❌ | ❌ | ❌ | [endpoints.js:129-130](frontend/src/api/endpoints.js#L129-L130) · [:153](frontend/src/api/endpoints.js#L153) |

**Veredicte Q1:** de les 24 portes censades, **11 no toquen `ModelTask` en absolut**, i entre elles
hi ha les tres per on més s'escriu sobre un model: **editar la fitxa `.ftt`, pujar fitxers i editar
la graella de mides**. El cicle de tasca no cobreix el treball; cobreix **l'obertura de dues
superfícies concretes** (Mesures i Escalat) i prou.

---

## BLOC Q2 — EL CAS CONCRET D'AGUS, TRAÇAT SENCER

**Gest:** tab *Fitxa tècnica* d'un model → botó **"Modificar"**.
La cadena L10N és inequívoca: `tech_sheet.tab_edit` = `"Modificar"`
([i18n/ca.json:2658](frontend/src/i18n/ca.json#L2658)); és **l'únic** literal "Modificar" de la UI.

### Traça, pas a pas

| # | Què passa | Fitxer:línia |
|---|---|---|
| 1 | El botó fa `navigate('/models/<id>/ftt/<fitxerId>')` — **sense cap query param** | [ModelSheet.jsx:927](frontend/src/pages/ModelSheet.jsx#L927) |
| 2 | La ruta munta `TechSheetEditor` directament (no passa pel resolver) | [App.jsx:306-310](frontend/src/App.jsx#L306-L310) |
| 3 | L'editor llegeix `taskId = searchParams.get('task_id')` → **`null`** | [TechSheetEditor.jsx:2566](frontend/src/pages/TechSheetEditor.jsx#L2566) |
| 4 | `isEditMode = !!taskId` → `false`. Només afecta l'estat inicial del lock; **no bloqueja res** | [:2569](frontend/src/pages/TechSheetEditor.jsx#L2569) · [:2603](frontend/src/pages/TechSheetEditor.jsx#L2603) |
| 5 | Es demana el lock del document: `POST /api/v1/ftt-documents/<id>/lock/` | [:3381](frontend/src/pages/TechSheetEditor.jsx#L3381) |
| 6 | **Autosave cada 2 s**: `PATCH /api/v1/ftt-documents/<id>/` amb el document sencer | [:3585-3622](frontend/src/pages/TechSheetEditor.jsx#L3585-L3622) |
| 7 | El backend desa una versió nova i renova el lock. **Cap referència a `ModelTask`** en tot el fitxer (grep `ModelTask\|tasks` a `ftt_document_views.py`: **0 coincidències**) | [ftt_document_views.py:213-246](backend/fhort/models_app/ftt_document_views.py#L213-L246) |
| 8 | A l'unmount: **`if (taskId)`** → com que és `null`, **no es demana cap transició**. Només s'allibera el lock | [:3391-3403](frontend/src/pages/TechSheetEditor.jsx#L3391-L3403) |

### Què HAURIA de passar segons el disseny del cicle

El disseny sí que existeix i està implementat **a l'altra porta**: el menú lateral
*Fitxa tècnica* → `TechSheetEntry` fa `openTask(model.id, 'tech_sheet')` i **només navega si el
backend retorna `task_id`**, propagant-lo a la URL
([TechSheetEntry.jsx:46-54](frontend/src/pages/TechSheetEntry.jsx#L46-L54)). Igualment,
`WorkPlan` i `TaskTree` construeixen la ruta **amb** `?task_id=`
([WorkPlan.jsx:30](frontend/src/components/model/WorkPlan.jsx#L30) ·
[TaskTree.jsx:42](frontend/src/components/model/TaskTree.jsx#L42)).

### Què passa de debò

**Res.** La tasca `tech_sheet` del model queda com estava (Pending, Paused o Done), l'`assignee`
no canvia, no s'obre cap `TimerEntrada`, i el temps d'editar la fitxa **no existeix enlloc**.
L'única senyal a l'usuari és un badge discret "consulta" a la barra d'estat
([TechSheetEditor.jsx:7722-7731](frontend/src/pages/TechSheetEditor.jsx#L7722-L7731)) i el text del
tab que ho assumeix com a norma: *"Les fitxes es poden editar des del Kanban (tasca Fitxa tècnica)
o des del botó Modificar"* ([i18n/ca.json:2660](frontend/src/i18n/ca.json#L2660)) — text que a més
**remet a un Kanban que ja no existeix** (§Q1.2).

**No és una regressió: és una decisió escrita.** El comentari del tab ho diu literalment:
*"Consulta des del Model obre sense task_id → mode consulta (l'editor desa igual, però no imputa
temps). L'edició registrada es fa des del Kanban, que passa ?task_id=..."*
([ModelSheet.jsx:774-775](frontend/src/pages/ModelSheet.jsx#L774-L775)).
El problema és que **el Kanban que havia de ser l'altra meitat d'aquesta decisió està jubilat**, i
per tant "Modificar" ha quedat com **l'única porta pràctica** a les fitxes d'un model — i és la que
no compta.

**Fix mecànic (sense decisió):** el botó ha de fer `openTask(modelId,'tech_sheet')` i navegar amb
`?task_id=` en èxit, exactament com [TechSheetEntry.jsx:46-54](frontend/src/pages/TechSheetEntry.jsx#L46-L54).
Cal decidir només què fa "Previsualitzar" (§Q6 · D-1).

---

## BLOC Q3 — EL PING-PONG, MESURAT

### Q3.0 · Nota de mètode: el model 195

`SELECT id FROM fhort.models_app_model WHERE id=195;` → **0 files**.
`grep -c "models/195"` sobre **tots** els access logs del servidor (inclosos els `.gz`) → **0**.
El model no existeix i no ha existit en aquest host durant la retenció dels logs (14 dies).
Les 45 files vives van del 162 al 1307 amb el forat 189-246. **La sessió del 04/08 al matí sobre el
195 no és mesurable des d'aquí.**

El que SÍ hi és, i diu exactament el mateix:
- El corpus sencer de 217 timers i 457 transicions del tenant.
- La sessió **d'avui**, 04/08, sobre el **model 188** (§Q3.4), que és a la vegada la prova viva
  del forat més dolorós del document.

### Q3.1 · On s'obre i on es tanca la tasca en el flux de desat

**Els dos punts són la MATEIXA funció, i és una funció de tancament:**

```python
# backend/fhort/models_app/views.py:1613-1618
if task.status in ('Pending', 'Paused'):
    transition_task(task, 'InProgress', profile)   # ← L'OBRE  (línia 1616)
    task.refresh_from_db()
transition_task(task, 'Done', profile)             # ← LA TANCA (línia 1618)
```

Cridada des de **dues** portes de desat:
- `gravar_pom_view` → [models_app/views.py:2098](backend/fhort/models_app/views.py#L2098)
- `close_table_view` ("tancar taula") → [models_app/views.py:1586](backend/fhort/models_app/views.py#L1586)

Un tercer parell idèntic viu al size check:
[services_size_check.py:286-287](backend/fhort/models_app/services_size_check.py#L286-L287).

**Efecte quan la tasca ve de `Pending`/`Paused`:** `_open_timer` crea un `TimerEntrada` amb
`inici=now` ([services_c.py:19-24](backend/fhort/tasks/services_c.py#L19-L24)) i, mil·lisegons
després, `_close_open_timer` el tanca amb `minuts = int(segons // 60) = 0`
([services_c.py:27-35](backend/fhort/tasks/services_c.py#L27-L35)).

**Prova a BD** — transicions 193/194 de la `ModelTask` 250, separades per **10 mil·lisegons**, amb
el seu timer 106 de durada 11 ms:

```
193 | Paused     → InProgress | 2026-06-24 12:06:39.155402+00
194 | InProgress → Done       | 2026-06-24 12:06:39.165811+00
timer 106 | inici 12:06:39.152256 | fi 12:06:39.163138 | minuts 0
```

### Q3.2 · «S'obre i es tanca a CADA desat?» — resposta matisada, i és pitjor que un sí

**No exactament: es TANCA a cada desat, i es REOBRE al següent gest d'edició.** El bucle real és:

| Pas | Qui | Fitxer:línia |
|---|---|---|
| 1 | L'usuari entra a editar → `openTask` → `Paused/Done → InProgress` (obre timer) | [ModelSheet.jsx:229](frontend/src/pages/ModelSheet.jsx#L229) |
| 2 | L'usuari prem "Gravar POM" → `_close_pom_task_for_model` → **`→Done`** (tanca timer + `record_actual_time`) | [views.py:2098](backend/fhort/models_app/views.py#L2098) · [services_c.py:271-275](backend/fhort/tasks/services_c.py#L271-L275) |
| 3 | El front surt del mode entrada i **no reobre res** | [ModelSheet.jsx:248-266](frontend/src/pages/ModelSheet.jsx#L248-L266) |
| 4 | L'usuari continua treballant a la taula → **sense tasca, sense timer** | — |
| 5 | L'usuari torna a "Editar mides" → `openTask` → **`Done → InProgress` = RECTIFICACIÓ** | [services_c.py:14-15](backend/fhort/tasks/services_c.py#L14-L15) |

Cada volta del bucle deixa: **1 rectificació al log**, **1 mostra Welford nova amb el total
acumulat**, i un tram de temps al mig que **no s'ha comptat**.

**Prova a BD — la `ModelTask` 250 (model 186, `pom`), 17 voltes:**

```
   at                          | mostra Welford (min)
   2026-06-24 12:06:39         |  204
   2026-06-25 13:06:05         |  360
   2026-06-25 13:07:08         |  361   ← 63 s després de l'anterior
   2026-06-25 15:38:08         |  511
   2026-06-25 15:38:24         |  511   ← 16 s després, mostra IDÈNTICA
   2026-06-25 16:03:51         |  536
   2026-06-25 16:04:14         |  536   ← 23 s després, mostra IDÈNTICA
   2026-06-25 16:34:54         |  566
   2026-06-25 16:35:04         |  566   ← 10 s després, mostra IDÈNTICA
   2026-06-25 17:35:26         |  574
   2026-06-25 17:38:39         |  577
   2026-06-26 05:05:16         |  606
   2026-06-26 06:00:03         |  660
   2026-06-26 09:28:19         |  711
   2026-06-26 10:18:44         |  760
   2026-06-26 10:19:22         |  760   ← 38 s després, mostra IDÈNTICA
   2026-07-16 16:48:11         |  760   ← 3 setmanes després, mostra IDÈNTICA
```

**Cens del ping-pong a tot el tenant:**

| Mesura | Valor |
|---|---|
| Transicions `→Done` totals | **49** |
| `ModelTask` diferents que les han produït | **21** |
| Repeticions (`→Done` sobre una tasca ja tancada) | **28** (57 %) |
| Rectificacions `Done → InProgress` | **39** |
| Distribució de `→Done` per tasca | 15 tasques×1 · 2×2 · 2×3 · 1×**7** · 1×**17** |
| Parelles `→Done` a menys de 120 s l'una de l'altra | **5** |
| Timers tancats amb `minuts = 0` | **100 de 217** (46 %) |
| Timers oberts ara mateix (zombis) | **0** ✅ |
| Trams > 24 h (fuites històriques) | **0** ✅ (higiene de [services_i.py:17](backend/fhort/tasks/services_i.py#L17) ja aplicada) |

### Q3.3 · Quant temps queda REGISTRAT d'una sessió de treball real

Tres mesures, de la més optimista a la més honesta.

**(a) Dins d'un tram obert, el rellotge és bo.** Agrupant els trams del tècnic 1 en sessions
(tall a 20 min sense cap tram): 60 sessions, 8 958 min de finestra, **8 684 min registrats = 97 %**.
La pèrdua per truncament (`// 60` a [services_c.py:33](backend/fhort/tasks/services_c.py#L33))
és de **75 min sobre 9 852** registrats = **0,8 %**. **El problema no és el rellotge.**

**(b) El problema és el temps entre trams.** Per dia i tècnic, finestra (primer inici → últim fi)
contra minuts registrats:

| Dia | Trams | Finestra (min) | Registrats | **Forat** | % registrat |
|---|---|---|---|---|---|
| 2026-06-23 | 21 | 651 | 359 | 292 | 55 % |
| 2026-06-24 | 26 | 679 | 422 | 257 | 62 % |
| 2026-06-26 | 18 | 356 | 142 | 214 | 40 % |
| 2026-06-29 | 8 | 242 | 115 | 127 | 48 % |
| **2026-07-08** | 4 | **42** | **0** | **42** | **0 %** |
| 2026-07-10 | 6 | 976 | 297 | 679 | 30 % |
| **2026-07-27** | 3 | **37** | **0** | **37** | **0 %** |
| **2026-07-31** | 4 | **302** | **29** | **273** | **10 %** |

**Resposta directa a la pregunta:** d'una hora de treball real en surten registrats
**entre 0 i 60 minuts**, i el que decideix el resultat **no és quant s'ha treballat sinó si la
porta va quedar oberta**. Els dies 08/07 i 27/07 la resposta literal és **zero minuts** per a
finestres de 42 i 37 minuts amb 4 i 3 trams oberts.

**(c) El cas extrem, sobre una sola tasca.** La `ModelTask` 250 el 24/06, entre 12:36:55 i 16:42:19
(**4 h 05'** de rellotge de paret), té **8 trams consecutius, tots de 0 minuts**
(timers 109, 110, 115, 117, 118, 119, 120, 124). Registrat en aquella tasca: **0 minuts**.

### Q3.4 · La sessió d'AVUI (04/08), model 188 — el forat en directe

Del log de nginx d'avui (`ftt-staging-access.log`, 965 línies):

```
16:21:48  POST /api/v1/models/188/open-task/   → 409
16:56:47  POST /api/v1/models/188/open-task/   → 409
16:56:49  POST /api/v1/models/188/open-task/   → 409
16:56:51  POST /api/v1/models/188/open-task/   → 409
16:57:03  POST /api/v1/models/188/open-task/   → 409
18:17:06  POST /api/v1/models/188/open-task/   → 409
18:26:09  POST /api/v1/models/188/open-task/   → 200   (size_check → task 305)
18:26:09  POST /api/v1/size-checks/open/       → 200
18:27:38  POST /api/v1/timers/heartbeat/       → 200   ← el modal, 89 s després
18:27:41  POST /api/v1/model-task-items/305/transition/ → 200 (Paused)
18:28:14  POST /api/v1/models/188/open-task/   → 409
```

**Set 409 en dues hores.** La causa és determinista i verificada a BD:

```
ModelTask 256 (model 188, pom)         → status Done, work_order 13
ModelTask 272 (model 188, pattern_cad) → status Done, work_order 13
DeliveryNoteLine 13 → DeliveryNote 5 → status ISSUED
DeliveryNoteLine 14 → DeliveryNote 5 → status ISSUED
```

Guard de reobertura: **una tasca amb línia en albarà EMÈS no es pot reobrir**
([services_c.py:196-199](backend/fhort/tasks/services_c.py#L196-L199)). `open-task` el converteix
en un `409` genèric ([views_b.py:572-573](backend/fhort/tasks/views_b.py#L572-L573)), i el
frontend l'ensenya com **un toast genèric sense cap codi ni motiu**
([ModelSheet.jsx:238](frontend/src/pages/ModelSheet.jsx#L238)):
`t('model_sheet.open_task_err')`.

Resultat: **el model 188 té les portes de POM i patró tapiades per sempre**, ningú no sap per què,
i tota la feina que s'hi faci a partir d'ara **no pot tenir rellotge**. Registre real d'avui sobre
el 188: **1 minut** (timer 342).

### Q3.5 · La transacció no bloqueja la fila — dues pauses del mateix instant

`transition_task` és `@transaction.atomic` ([services_c.py:177](backend/fhort/tasks/services_c.py#L177))
però **la instància arriba ja llegida i sense `select_for_update`**
([views_b.py:442](backend/fhort/tasks/views_b.py#L442) · [:494](backend/fhort/tasks/views_b.py#L494)).
Grep de `select_for_update` a `fhort/tasks/`: **una sola aparició, i és a
[services_i.py:60](backend/fhort/tasks/services_i.py#L60)** (la cel·la Welford), **cap sobre `ModelTask`**.

Prova a BD — dues transicions `InProgress → Paused` sobre la mateixa tasca, separades per **6 ms**,
totes dues acceptades (la segona hauria d'haver estat `Paused → Paused` i rebotar amb 400):

```
230 | InProgress → Paused | 2026-06-24 16:42:19.572818+00
231 | InProgress → Paused | 2026-06-24 16:42:19.578198+00
```

**Veredicte Q3:** el ping-pong existeix, està quantificat (57 % de les tanques són repeticions) i
té dues causes independents: **(1)** el desat tanca la tasca i cap gest la reobre fins que
l'usuari torna a prémer "Editar", i **(2)** hi ha portes que no obren res, de manera que el treball
entre desats no té rellotge. La truncació i els timers zombis, en canvi, **ja estan resolts**.

---

## BLOC Q4 — EL MOTOR DE TEMPS

### Q4.1 · Què alimenta les mètriques (i què està aprenent amb el ping-pong)

**Cadena completa:**

```
transition_task(..., 'Done')            services_c.py:271-275
   └→ record_actual_time(task)          services_i.py:47-75
        └→ x = _real_minutes(task)      services_i.py:41-44   ← SUMA DE TOTS ELS TRAMS SANS
        └→ Welford sobre TaskTimeEstimate(garment_type_item × task_type)
   ...després...
lookup_estimated_minutes(model, tt)     services_g.py:11-46   ← cascada de 4 graons
   └→ effective_minutes(cell)           services_i.py:78-87   ← empíric si n ≥ 5
        └→ ModelTask.estimated_minutes (snapshot en crear la tasca)
        └→ plan_service (planificació)  planning/plan_service.py:54-58
```

🔴 **El defecte estructural és a [services_i.py:57](backend/fhort/tasks/services_i.py#L57):**
la mostra és **el total acumulat de la tasca**, no l'increment del darrer tram. Combinat amb
`Done → InProgress` permesa ([services_c.py:15](backend/fhort/tasks/services_c.py#L15)), cada
reobertura-i-retancament injecta **una mostra nova gairebé idèntica a l'anterior**. El propi
command de recompute ho documenta com a fet verificat, no com a sospita
([recompute_welford.py:11-15](backend/fhort/tasks/management/commands/recompute_welford.py#L11-L15)):
*"`n` de cada cel·la quadra amb el nombre de transicions →Done, no amb el de tasques Done."*

**Estat REAL de l'estadística, avui:**

| item | task_type | seed | **n** | mitjana (min) | Mana sobre el planificador? |
|---|---|---|---|---|---|
| 22 | `pom` | 30 | **17** | **562,29** | ✅ (n ≥ 5) — **les 17 mostres surten d'UNA tasca** |
| 4 | `size_check` | — | **7** | 199,86 | ✅ |
| 5 | `pom` | 30 | **5** | **4,00** | ✅ — **substitueix el seed de 30 min** |
| 30 | `size_check` | — | **5** | 255,00 | ✅ |
| 58 | `pom` | — | 4 | 13,75 | ❌ |
| 10 | `pom` | 30 | 3 | 41,67 | ❌ |
| … | | | | | (20 cel·les amb mostres de 460 totals; 58 mostres en total) |

**El cas (item 5 × `pom`) és el més il·lustratiu.** Les seves 5 mostres, reconstruïdes:
`2, 9, 3, 4, 2` minuts (una sisena de `0` va ser descartada per `x <= 0`). Són **les engrunes que
queden entre obrir la porta i prémer Gravar**. Amb n = 5 la cel·la passa el llindar i el
planificador deixa de fer servir el seed de 30 min per fer servir **4 minuts** com a durada d'una
tasca de definició de POMs.

**I la mateixa contaminació menteix cap amunt pel graó 2.** `lookup_estimated_minutes` fa la mitjana
de les cel·les madures de **qualsevol** item ([services_g.py:31-35](backend/fhort/tasks/services_g.py#L31-L35)):

| task_type | cel·les madures | **empíric global** | `TimeSeed` corresponent |
|---|---|---|---|
| `pom` | 2 | **283 min** | **35 min** ([tasks_timeseed](backend/fhort/tasks/models.py#L508)) |
| `size_check` | 2 | **227 min** | — |

Qualsevol model nou sense cel·la pròpia per a `pom` rep avui una estimació de **283 minuts** — **8×
la llavor**, derivada de dues cel·les de les quals una és el ping-pong de la tasca 250.

### Q4.2 · El comptador i el modal de pausa (el d'1 minut)

**D'on surt el llindar.** [GuardTascaOblidada.jsx:34-41](frontend/src/components/GuardTascaOblidada.jsx#L34-L41):

```js
// QA: per no esperar 30 minuts reals, els llindars es poden escurçar per sessió de navegador
//   localStorage.setItem('ftt_guard_llindar_min', '1')
//   localStorage.setItem('ftt_guard_gracia_min', '0.5')
const LLINDAR_MIN = llegeixMinuts('ftt_guard_llindar_min', 30)   // fins a l'avís
const GRACIA_MIN  = llegeixMinuts('ftt_guard_gracia_min', 3)     // per respondre'l
```

🔴 **Dos defectes en aquestes vuit línies:**
1. El comentari diu **"per sessió de navegador"** i és **fals**: `localStorage` és **persistent**.
   Qui va fer QA el 27/07 té el guard a 1 minut **des d'aleshores i per sempre**, en aquell perfil
   de navegador, sense cap indicador a la UI.
2. Es llegeix **una sola vegada, a la càrrega del mòdul** (constant de mòdul, no dins del
   component): ni recarregant la pàgina sense buidar `localStorage` es recupera el valor de
   producció.

**Mesura que ho confirma (segons des de l'obertura del tram fins al primer batec = temps que va
trigar a sortir el modal):**

```
timer 311 | 2026-07-31 06:32:38 → batec 06:33:41 |  63 s
timer 342 | 2026-08-04 18:26:09 → batec 18:27:38 |  90 s
```

Amb `LLINDAR_MIN = 30` el primer batec possible seria als **1 800 s**. **El llindar efectiu del
navegador d'Agus és 1 minut.**

**Què fa l'auto-pausa.** Passa per la mateixa porta que el kanban, amb marca
([GuardTascaOblidada.jsx:169-186](frontend/src/components/GuardTascaOblidada.jsx#L169-L186)):
`transition(taskId, {to_status:'Paused', auto:'guard_30min'})`. El backend només accepta del
client la marca `guard_30min` i només sobre `→Paused`
([views_b.py:421-423](backend/fhort/tasks/views_b.py#L421-L423) · [:455-457](backend/fhort/tasks/views_b.py#L455-L457)).

**Què registra quan pausa:** un `TaskTransition` amb `auto='guard_30min'`
([models.py:139-148](backend/fhort/tasks/models.py#L139-L148)) i el tancament del tram
(`minuts` = floor dels minuts transcorreguts). **MAI `Done`** — el Stop segueix sent humà.

**El dany, mesurat.** 10 transicions automàtiques al log; **9 són `guard_30min`** i sis d'elles
cauen sobre la **mateixa tasca 332 en 75 minuts**:

```
2026-07-31 06:35:11 · 07:33:44 · 07:38:43 · 07:46:35 · 07:48:35 · 07:50:35   (task 332, model 1302)
```

Tres auto-pauses en **4 minuts** (07:46 / 07:48 / 07:50). Aquell dia el model 1302 va registrar
**29 minuts sobre una finestra de 302** (§Q3.3): el guard mal calibrat **és** una de les causes
directes del forat de temps.

**La xarxa de sota segueix sense instal·lar.** El command existeix i és correcte
([pausa_tasques_oblidades.py](backend/fhort/tasks/management/commands/pausa_tasques_oblidades.py)),
amb llindar 40 min ([:32](backend/fhort/tasks/management/commands/pausa_tasques_oblidades.py#L32)),
però la seva pròpia capçalera diu **"CRONTAB (NO instal·lada — decisió d'Agus al deploy)"**
([:20-22](backend/fhort/tasks/management/commands/pausa_tasques_oblidades.py#L20-L22)).
Traça a BD: **1 sola** transició `cron_40min` de sempre, el 27/07 (execució manual).
Avui no hi ha cap timer zombi obert, però **no és perquè la xarxa hi sigui**.

### Q4.3 · Els 65 duplicats de Welford i el llindar inferior absent — segueixen?

**Els duplicats: SÍ, i estan quantificats.** No he pogut localitzar cap document que sostingui la
xifra concreta de **65** (grep sobre `docs/diagnosis/` + `TECH_DEBT.md`: **NO EXISTEIX**), de manera
que dono la mesura d'avui, feta amb la mateixa semàntica que el command de recompute:

| Mesura | Valor |
|---|---|
| Mostres Welford vives (`Σ n`) | **58** |
| De les quals produïdes per repetició `→Done` sobre una tasca ja tancada | **28** (48 %) |
| Cel·les on ≥ 1 mostra és duplicada | 6 de 20 |
| Cel·la pitjor | (22 × `pom`): **17 mostres d'una sola tasca** |

`recompute_welford` **reprodueix exactament** l'estat actual quan se li dona el mateix corpus (és
el seu test de correcció, [:30-31](backend/fhort/tasks/management/commands/recompute_welford.py#L30-L31)):
el meu recompte SQL independent dona el mateix `n` que la BD per a totes les cel·les amb mostres.
Això vol dir que **el recompute NO és el remei**: reprodueix fidelment la contaminació perquè la
contaminació és la semàntica actual, no un accident de dades.

**El llindar inferior: SÍ, segueix absent.** L'única guarda de mostra és
[services_i.py:58-59](backend/fhort/tasks/services_i.py#L58-L59): `if x <= 0: return None`.
No hi ha cap `MIN_MINUTS_MOSTRA`; grep de `MIN_MINUTS|llindar_inferior|MIN_SAMPLE`: **NO EXISTEIX**.
Per simetria hi ha `MAX_MINUTS_TRAM = 1440` per dalt
([services_i.py:17](backend/fhort/tasks/services_i.py#L17)) **i res per baix**. Conseqüència viva:
les mostres `2, 9, 3, 4, 2` de (item 5 × `pom`) són totes legals i totes manen.

**El que SÍ s'ha resolt** (i convé no reobrir-ho): higiene de trams > 24 h aplicada a totes les
lectures ([services_i.py:24](backend/fhort/tasks/services_i.py#L24), `TRAMS_SANS`), tancament de
**tots** els timers oberts i no només el primer
([services_c.py:27-35](backend/fhort/tasks/services_c.py#L27-L35)), i `last_heartbeat` read-only
al serializer ([serializers.py:14-16](backend/fhort/tasks/serializers.py#L14-L16)).
Cens actual: **0 timers oberts, 0 trams > 24 h**.

**Veredicte Q4:** el motor està sa; **el que li donen de menjar no ho està**. Amb 58 mostres de les
quals 28 són duplicats i 4 cel·les ja per damunt del llindar de maduresa, **el planificador ja fa
servir números inventats en producció**, i ho fa en les dues direccions (4 min per a un POM d'una
banda, 283 min per defecte de l'altra).

---

## BLOC Q5 — L'EXCLUSIÓ MÚTUA

### Q5.0 · La premissa del brief està invertida

> *"Avui és per model. La pregunta oberta d'Agus: hauria de ser per tècnic?"*

**Avui ja és per TÈCNIC, i per model no existeix.**
[services_c.py:204-215](backend/fhort/tasks/services_c.py#L204-L215):

```python
if to_status == 'InProgress':
    # Regla: una sola InProgress per tècnic (a qualsevol model)
    other = (ModelTask.objects.filter(assignee=profile, status='InProgress')
             .exclude(pk=task.pk).first())
    if other:
        _close_open_timer(other); other.status = 'Paused'; ...
        _log(other, 'InProgress', 'Paused', profile, auto='exclusio_inprogress')
```

**Cap mutex per model existeix.** L'únic lock del sistema és `FttDocumentLock`
([ftt_models.py:11-35](backend/fhort/models_app/ftt_models.py#L11-L35)), que és **per document
`.ftt` i per usuari**, amb TTL de 30 min ([services_ftt_document.py:26](backend/fhort/models_app/services_ftt_document.py#L26))
i força-si-ranci ([:53-64](backend/fhort/models_app/services_ftt_document.py#L53-L64)). No té res a
veure amb `ModelTask`.

### Q5.1 · Comportament REAL mesurat, cas per cas

| Escenari | Què passa de debò | Prova |
|---|---|---|
| **Un tècnic, dos models** | En obrir la 2a, la 1a es **pausa sola** amb `auto='exclusio_inprogress'`. Correcte per disseny. | [services_c.py:206-215](backend/fhort/tasks/services_c.py#L206-L215) · 0 casos al log (mai s'ha disparat) |
| **Dos tècnics, mateix model, tasques diferents** | **Res ho impedeix.** Tots dos poden tenir `InProgress` sobre el mateix model alhora. | cap filtre per `model` a la consulta d'exclusió |
| **Dos tècnics, la MATEIXA tasca (via `open-task`)** | El 2n **se la queda** (branca `elif`) **sense tancar el timer del 1r i sense escriure cap `TaskTransition`**. El tram del 1r segueix obert i imputant-li temps a ell. | [views_b.py:574-580](backend/fhort/tasks/views_b.py#L574-L580) |
| **Dos tècnics, la MATEIXA tasca (via `claim`)** | Idèntic: reassigna i recalcula cues, **no toca `status` ni timers** (està documentat com a intencionat a [:484](backend/fhort/tasks/views_b.py#L484)) | [views_b.py:503-515](backend/fhort/tasks/views_b.py#L503-L515) |
| **Actor ≠ assignee via `transition/`** | `_open_timer(task, B)` tanca el tram d'A i n'obre un per a B, **però `assignee` es queda a A** (només s'assigna si és `None`, [:230-231](backend/fhort/tasks/services_c.py#L230-L231)). B queda amb un tram obert sobre una tasca que la consulta d'exclusió **no veu** → **B pot obrir-ne una segona**. | 🔴 **La invariant es trenca sola** |

### Q5.2 · La invariant ja s'ha trencat — cas real a la BD

```sql
-- trams SOLAPATS del mateix tècnic sobre tasques diferents
timer 116 | tecnic 1 | task 253 | 2026-06-24 13:38:33 → 15:40:40  (122 min)
timer 117 | tecnic 1 | task 250 | 2026-06-24 13:59:50 → 14:00:14  (  0 min)
```

**Per què l'exclusió no va saltar:** la `ModelTask` 253 tenia trams del tècnic **13**
(timers 111-113, 24/06 12:38-12:45) i, com que `transition_task` només assigna `assignee` quan és
`None` ([:230-231](backend/fhort/tasks/services_c.py#L230-L231)), l'`assignee` va quedar al 13
mentre el tècnic **1** hi treballava. A les 13:59:50 la consulta
`filter(assignee=profile_1, status='InProgress')` **no va trobar la 253** i el tècnic 1 va acabar
amb **dos trams oberts alhora**. 122 minuts i 0 minuts es van registrar en paral·lel.

**Aquesta és la resposta a la pregunta d'Agus:** el problema no és si l'exclusió ha de ser per model
o per tècnic. **És que està ancorada a `assignee` (un camp de planificació) quan el rellotge està
ancorat a `tecnic` (qui hi és de debò).** Mentre siguin dos eixos diferents, qualsevol handoff,
claim o transició feta per algú altre que l'assignat obre un forat.

**Veredicte Q5:** l'exclusió per tècnic existeix, però és **inefectiva sempre que actor ≠ assignee**,
i **no hi ha cap protecció per model**. Un handoff deixa el rellotge corrent al tècnic anterior i
el nou treballa sense timer propi.

---

## BLOC Q6 — LA LLISTA DE DEMÀ

### 6.1 · FORATS (trencats, amb cas reproduïble) — ordenats per DOLOR

---

#### 🔴 F-1 · La fitxa tècnica es pot editar sense rellotge (el cas d'Agus)
**Fitxer:línia:** [ModelSheet.jsx:927](frontend/src/pages/ModelSheet.jsx#L927) (i el bessó [:924](frontend/src/pages/ModelSheet.jsx#L924), [:863](frontend/src/pages/ModelSheet.jsx#L863), [:801](frontend/src/pages/ModelSheet.jsx#L801))
**Reproduir:** obre un model → tab *Fitxa tècnica* → "Modificar" → mou qualsevol element del llenç
→ espera 3 s (autosave) → tanca. Comprova `SELECT * FROM fhort.tasks_tasktransition WHERE model_task_id IN (SELECT id FROM fhort.tasks_modeltask WHERE model_id=<id> )` ordenat per `at`: **cap fila nova**. La versió del `.ftt` sí que ha pujat.
**Dolor:** és la porta principal a les fitxes des que el Kanban va desaparèixer.

---

#### 🔴 F-2 · Set portes tapiades per l'albarà, amb missatge mut (model 188, AVUI)
**Fitxer:línia:** guard [services_c.py:196-199](backend/fhort/tasks/services_c.py#L196-L199) → 409 genèric [views_b.py:572-573](backend/fhort/tasks/views_b.py#L572-L573) → toast sense motiu [ModelSheet.jsx:238](frontend/src/pages/ModelSheet.jsx#L238)
**Reproduir:** model **188** (BRW-SS27-0001) → tab Mesures → "Editar mides" → **409**, toast genèric. Les tasques 256 (`pom`) i 272 (`pattern_cad`) són `Done` amb línia a l'albarà 5 (`ISSUED`).
**Traça viva:** 7× `409` avui entre 16:21 i 18:28 al log de nginx.
**Dolor:** el model queda **permanentment sense rellotge** per a aquelles tasques, i qui hi treballa no en sap el motiu. Afecta tots els models ja albaranats.

---

#### 🔴 F-3 · El desat tanca la tasca; res no la reobre fins al gest següent
**Fitxer:línia:** [models_app/views.py:1615-1618](backend/fhort/models_app/views.py#L1615-L1618), cridat des de [:2098](backend/fhort/models_app/views.py#L2098) i [:1586](backend/fhort/models_app/views.py#L1586); bessó a [services_size_check.py:286-287](backend/fhort/models_app/services_size_check.py#L286-L287)
**Reproduir:** Mesures → "Editar mides" → introdueix un valor → "Gravar POM" → segueix escrivint a la taula 10 minuts. Consulta els timers de la tasca: cap tram cobreix aquells 10 minuts, i el log té un `→Done` nou.
**Mesura:** 28 de 49 `→Done` són repeticions; 100 de 217 trams duren 0 minuts.

---

#### 🔴 F-4 · Welford aprèn el TOTAL a cada tancament, no l'increment
**Fitxer:línia:** [services_i.py:41-44](backend/fhort/tasks/services_i.py#L41-L44) + [:57](backend/fhort/tasks/services_i.py#L57)
**Reproduir:** tanca una tasca, reobre-la i torna-la a tancar sense treballar-hi. `TaskTimeEstimate.n` puja de 1 en 1 amb la **mateixa** mitjana.
**Dany viu:** cel·la (22 × `pom`) = **n 17, mitjana 562 min**, tota d'**una** tasca; cel·la (5 × `pom`) = **n 5, mitjana 4 min**, ja per damunt del llindar i substituint el seed de 30.
**Consequència aigües avall:** empíric global de `pom` = **283 min** contra `TimeSeed` = 35.

---

#### 🔴 F-5 · El guard està a 1 minut al navegador d'Agus, i no hi ha manera de saber-ho
**Fitxer:línia:** [GuardTascaOblidada.jsx:34-41](frontend/src/components/GuardTascaOblidada.jsx#L34-L41)
**Reproduir:** consola → `localStorage.getItem('ftt_guard_llindar_min')`. Si retorna `"1"`, el modal surt cada minut. `localStorage.removeItem('ftt_guard_llindar_min'); localStorage.removeItem('ftt_guard_gracia_min')` + recàrrega ho torna a 30/3.
**Prova:** batecs a 63 s i 90 s de l'obertura del tram (timers 311 i 342). Sis auto-pauses sobre la tasca 332 en 75 min el 31/07.
**Dolor doble:** molesta l'usuari **i** trosseja el temps registrat (29 min sobre 302 aquell dia).

---

#### 🟠 F-6 · Un handoff deixa el rellotge al tècnic antic
**Fitxer:línia:** [views_b.py:574-580](backend/fhort/tasks/views_b.py#L574-L580) (open-task) i [:503-515](backend/fhort/tasks/views_b.py#L503-L515) (claim)
**Reproduir:** tècnic A obre una tasca (queda `InProgress`, timer obert de A). Tècnic B fa Play sobre la mateixa tasca → confirma el handoff. La tasca passa a ser de B **sense cap `TaskTransition` i sense tancar el tram de A**. El guard de B no veu res (`timers.list` va scopat per `tecnic`, [tasks/views.py:30-38](backend/fhort/tasks/views.py#L30-L38)); el de A el pausarà i pausarà **la tasca de B**.

---

#### 🟠 F-7 · L'exclusió "una sola InProgress per tècnic" es pot esquivar sense voler
**Fitxer:línia:** [services_c.py:206](backend/fhort/tasks/services_c.py#L206) (filtra per `assignee`) contra [:230-231](backend/fhort/tasks/services_c.py#L230-L231) (només assigna si és `None`)
**Cas real:** timers 116 i 117, tècnic 1, solapats el 24/06 (§Q5.2).

---

#### 🟠 F-8 · Cap bloqueig de fila: dues transicions concurrents passen totes dues
**Fitxer:línia:** [views_b.py:442](backend/fhort/tasks/views_b.py#L442) · [:494](backend/fhort/tasks/views_b.py#L494) — `.get(pk=…)` sense `select_for_update`
**Cas real:** transicions 230 i 231, `InProgress → Paused` idèntiques, **6 ms** de diferència.

---

#### 🟡 F-9 · Text de la UI que remet a un Kanban jubilat
**Fitxer:línia:** [i18n/ca.json:2660](frontend/src/i18n/ca.json#L2660) (+ `en`/`es` [:2660](frontend/src/i18n/en.json#L2660)) i [ModelFabric.jsx:120](frontend/src/pages/ModelFabric.jsx#L120), que navega a `/tasques/kanban` → catch-all → `/`.
**Reproduir:** ModelFabric → tancar taula amb èxit → l'usuari acaba al Dashboard sense saber per què.

---

#### 🟡 F-10 · Doble `open-task` en obrir "Definició POM" des del pla de treball
**Fitxer:línia:** [WorkPlan.jsx:29](frontend/src/components/model/WorkPlan.jsx#L29) (ruta `?mode=entry` **sense** `task_id`) + [ModelSheet.jsx:344-351](frontend/src/pages/ModelSheet.jsx#L344-L351) (torna a cridar `openTask`)
**Prova:** log del 03/08, `05:02:52` i `05:02:53`, dos POST idèntics a `models/165/open-task/` amb referers diferents. Cada crida dispara `recompute_for_technicians` ([views_b.py:587-589](backend/fhort/tasks/views_b.py#L587-L589)).

---

#### 🟡 F-11 · `TimerEntrada` és un `ModelViewSet` complet: el client pot crear i esborrar trams
**Fitxer:línia:** [tasks/views.py:15-44](backend/fhort/tasks/views.py#L15-L44) — `POST/PUT/DELETE /api/v1/timers/` oberts amb `IsAuthenticated`. `perform_create` força `tecnic=jo`, però `inici`, `fi`, `minuts` i `model_task` són escrivibles (`minuts`/`fi` són read-only al serializer, [serializers.py:16](backend/fhort/tasks/serializers.py#L16), però `inici` i `model_task` no).
**Consequència:** el temps facturable és falsificable des del navegador i esborrable per `id`.

---

#### 🟡 F-12 · Mirar un model el merita i li reancora el pla
**Fitxer:línia:** [services_c.py:238-258](backend/fhort/tasks/services_c.py#L238-L258) (meritació SaaS) i [views_b.py:587-594](backend/fhort/tasks/views_b.py#L587-L594) (`recompute_for_technicians` + `reanchored_by_start`)
**Reproduir:** model verge → tab Mesures → "Editar mides" → tanca la pestanya als 3 s. Ha nascut un `ConsumptionRecord`, s'ha emès l'event a `public`, el model ha passat de `Pending` a `Dev` i la cua del tècnic s'ha recalculat.
**Prova:** els 21 `ConsumptionRecord` del tenant tenen `merited_at` == `started_at` de la primera tasca.

---

#### ⚪ F-13 · Comentari amb referència morta
[TechSheetEditor.jsx:7722](frontend/src/pages/TechSheetEditor.jsx#L7722) diu *"guard a :1862"*; a la línia 1862 hi ha codi de render de Konva. El guard real és `taskId` a [:2566](frontend/src/pages/TechSheetEditor.jsx#L2566).

---

### 6.2 · DECISIONS — només Agus les pot prendre

---

**D-1 · Quin gest ha d'obrir el rellotge de la fitxa tècnica?**
Avui "Modificar" i "Previsualitzar" fan **exactament el mateix** ([:924](frontend/src/pages/ModelSheet.jsx#L924) i [:927](frontend/src/pages/ModelSheet.jsx#L927)), i cap dels dos compta.
- **(a)** "Modificar" obre tasca (com [TechSheetEntry.jsx:46-54](frontend/src/pages/TechSheetEntry.jsx#L46-L54)); "Previsualitzar" queda en consulta read-only de debò.
- **(b)** Tots dos obren tasca (obrir la fitxa = treballar-hi).
- **(c)** Cap obre tasca i s'accepta que la fitxa es treballa des del pla de treball — però **llavors cal recuperar aquella porta**, perquè el Kanban ja no existeix.

---

**D-2 · Què vol dir que una tasca està "en curs"?**
- **(a) La porta oberta** (avui): el rellotge corre entre `enterEdit` i `exitEdit`.
- **(b) La sessió de treball**: la tasca s'obre en entrar al model i es tanca amb un gest explícit; els desats intermedis **no** la tanquen.
- **(c) L'escriptura**: qualsevol escriptura sobre el model obre-si-cal la tasca corresponent i li imputa el temps fins a la següent inactivitat.
La (b) i la (c) fan desaparèixer F-3 i bona part de F-4. La (a) el conserva per disseny.

---

**D-3 · Una mostra de temps = una tasca o un tancament?**
- **(a)** Una tasca = una mostra (la reobertura **actualitza** la mostra en comptes d'afegir-ne una).
- **(b)** Un tram = una mostra (l'increment, no l'acumulat).
- **(c)** Es queda com és i s'accepta que `n` compta tancaments.
Sigui quina sigui, **cal decidir també si es passa `recompute_welford --apply` després** — avui reprodueix fidelment la contaminació i no la neteja.

---

**D-4 · Hi ha d'haver llindar INFERIOR de mostra?**
Avui la guarda és només `x > 0` ([services_i.py:58-59](backend/fhort/tasks/services_i.py#L58-L59)). Amb ella, les mostres `2, 9, 3, 4, 2` min ja manen sobre el planificador.
- **(a)** `MIN_MINUTS_MOSTRA` (p.ex. 5) simètric a `MAX_MINUTS_TRAM`.
- **(b)** Cap llindar; es corregeix a l'arrel (D-2/D-3) i les engrunes deixen d'existir soles.

---

**D-5 · Es pot reobrir una tasca ja albaranada?**
El guard de [services_c.py:196-199](backend/fhort/tasks/services_c.py#L196-L199) és una **llei comercial** aplicada a una **porta de treball**.
- **(a)** Es manté i la porta obre una tasca **ad-hoc nova** (`origen='ad_hoc'`, ja previst a [models.py:78](backend/fhort/tasks/models.py#L78)) per a la feina posterior a l'albarà.
- **(b)** Es manté tal qual, però el 409 arriba amb `code` discriminant i missatge explícit (avui és mut).
- **(c)** Es permet reobrir i la rectificació genera línia al proper albarà.
**Sense aquesta decisió, el model 188 i tots els albaranats queden sense rellotge per sempre.**

---

**D-6 · L'exclusió s'ha d'ancorar a `assignee` o a qui treballa?**
- **(a)** L'exclusió passa a mirar els **trams oberts** (`TimerEntrada.tecnic`) en comptes de `assignee` — la invariant torna a ser certa sempre.
- **(b)** `transition_task` **sempre** reassigna l'`assignee` a qui executa (avui només si és `None`) — els dos eixos convergeixen.
- **(c)** Es manté i s'accepta que un handoff deixa el rellotge a l'anterior.

---

**D-7 · Quan un tècnic s'endú una tasca d'un altre, què passa amb el tram obert?**
Avui: res, i el tram segueix imputant a l'anterior ([views_b.py:574-580](backend/fhort/tasks/views_b.py#L574-L580)).
- **(a)** Es tanca el tram de l'anterior i se n'obre un de nou per al nou, amb `TaskTransition` marcat (`auto='handoff'`).
- **(b)** Es prohibeix el claim sobre una tasca amb tram obert (409 amb el nom de qui la té).

---

**D-8 · Dos tècnics poden treballar el mateix model alhora?**
Avui **sí** i sense cap traça. Cal dir si això és funcionalitat (fitting a dues mans) o accident.

---

**D-9 · S'instal·la la cron del guard?**
`pausa_tasques_oblidades` és a punt des del 27/07 i la seva capçalera diu que **la decisió de no instal·lar-la va ser d'Agus** ([:20-22](backend/fhort/tasks/management/commands/pausa_tasques_oblidades.py#L20-L22)). Ara no hi ha zombis, però tampoc no hi ha xarxa.

---

**D-10 · Obrir una eina ha de meritar?**
Avui la primera `→InProgress` **factura el model** (F-12). Cal dir si el fet facturable és
"algú ha obert una porta" o "algú ha treballat N minuts".

---

### 6.3 · FIXOS MECÀNICS (arreglables sense cap decisió)

| # | Fix | Fitxer:línia | Depèn de |
|---|---|---|---|
| M-1 | Treure el `?` i propagar `?task_id=` des de "Modificar" (calcar `TechSheetEntry`) | [ModelSheet.jsx:927](frontend/src/pages/ModelSheet.jsx#L927) | D-1 per a "Previsualitzar"; el botó d'edició és mecànic |
| M-2 | El 409 de reobertura ha de portar `code` discriminant i el frontend ha de dir el motiu | [views_b.py:572-573](backend/fhort/tasks/views_b.py#L572-L573) · [ModelSheet.jsx:238](frontend/src/pages/ModelSheet.jsx#L238) | — |
| M-3 | Corregir el comentari fals de les claus de QA ("per sessió de navegador" → `localStorage`, persistent) i afegir un indicador visible quan el llindar no és el de producció | [GuardTascaOblidada.jsx:34-37](frontend/src/components/GuardTascaOblidada.jsx#L34-L37) | — |
| M-4 | `select_for_update()` en llegir la `ModelTask` a les dues portes de transició | [views_b.py:442](backend/fhort/tasks/views_b.py#L442) · [:494](backend/fhort/tasks/views_b.py#L494) | — |
| M-5 | Treure la crida `openTask` redundant del camí `?mode=entry` (o treure `mode=entry` de la ruta i passar `task_id`) | [WorkPlan.jsx:29](frontend/src/components/model/WorkPlan.jsx#L29) · [ModelSheet.jsx:344-351](frontend/src/pages/ModelSheet.jsx#L344-L351) | — |
| M-6 | Tancar l'escriptura de `TimerEntrada` des del client (`ReadOnlyModelViewSet` + les dues accions) | [tasks/views.py:15](backend/fhort/tasks/views.py#L15) | — |
| M-7 | `ModelFabric` ha de navegar a una ruta que existeixi | [ModelFabric.jsx:120](frontend/src/pages/ModelFabric.jsx#L120) | — |
| M-8 | Reescriure `tech_sheet.tab_hint` als tres idiomes (parla d'un Kanban jubilat) | [ca.json:2660](frontend/src/i18n/ca.json#L2660) · [en.json:2660](frontend/src/i18n/en.json#L2660) · [es.json:2660](frontend/src/i18n/es.json#L2660) | — |
| M-9 | Corregir la referència morta `:1862` del comentari | [TechSheetEditor.jsx:7722](frontend/src/pages/TechSheetEditor.jsx#L7722) | — |
| M-10 | "Previsualitzar" i "Modificar" han de fer coses diferents (avui són el mateix `navigate`) | [ModelSheet.jsx:924](frontend/src/pages/ModelSheet.jsx#L924) · [:927](frontend/src/pages/ModelSheet.jsx#L927) | D-1 |

---

## TAULA FINAL PER AL CTO — EXISTEIX / FALTA / DIFERENT

| Peça | Estat | Nota |
|---|---|---|
| Màquina d'estats única (`transition_task`) | ✅ EXISTEIX | Cap camí paral·lel. Els guards hi passen per dins. |
| Log immutable de transicions amb marca d'automatisme | ✅ EXISTEIX | [models.py:130-156](backend/fhort/tasks/models.py#L130-L156) |
| Higiene de trams > 24 h a totes les lectures | ✅ EXISTEIX | 0 fuites vives |
| Tancament de tots els timers oberts (no només el 1r) | ✅ EXISTEIX | 0 zombis vius |
| Guard de tasca oblidada (client) | ⚠️ **DIFERENT** | Correcte, però **calibrat a 1 min** per una clau de QA persistent |
| Xarxa de seguretat (cron) | ❌ **FALTA** | Command llest; crontab no instal·lada |
| Rellotge a la fitxa tècnica des del Model | ❌ **FALTA** | El cas d'Agus (F-1) |
| Rellotge en editar la graella de mides | ❌ **FALTA** | `PATCH base-measurements/` no toca `ModelTask` |
| Rellotge en pujar fitxers / propagar grading | ❌ **FALTA** | Cap `transition_task` en aquests camins |
| Mostra Welford = increment del tram | ❌ **FALTA** | Avui és l'acumulat (F-4) |
| Llindar inferior de mostra | ❌ **NO EXISTEIX** | Només `x > 0` |
| Exclusió mútua per tècnic | ⚠️ **DIFERENT** | Ancorada a `assignee`, no a qui treballa; **trencada a la BD** (F-7) |
| Exclusió mútua per model | ❌ **NO EXISTEIX** | L'únic lock del sistema és el del document `.ftt` |
| Bloqueig de fila a la transició | ❌ **NO EXISTEIX** | Doble pausa real a 6 ms (F-8) |
| Kanban | ❌ **NO EXISTEIX** | Ruta jubilada; la UI i el codi encara hi remeten |
| Traça per reconstruir el model 195 | ❌ **NO EXISTEIX** | Ni a la BD ni a cap access log del servidor |

---

### Annex · consultes SQL usades (totes `SELECT`, schema `fhort`)

```sql
-- cens de timers i transicions
SELECT count(*) FROM tasks_timerentrada;                                  -- 217
SELECT count(*) FROM tasks_timerentrada WHERE fi IS NULL;                 -- 0
SELECT count(*) FROM tasks_timerentrada WHERE fi IS NOT NULL AND coalesce(minuts,0)=0;  -- 100
SELECT count(*) FROM tasks_timerentrada WHERE minuts > 1440;              -- 0
SELECT count(*) FROM tasks_tasktransition WHERE to_status='Done';         -- 49
SELECT count(*) FROM tasks_tasktransition WHERE from_status='Done' AND to_status='InProgress'; -- 39

-- mostres Welford reconstruïdes (mateixa semàntica que recompute_welford.py:42-56)
WITH done AS (
  SELECT tr.at, tr.model_task_id, m.garment_type_item_id item, mt.task_type_id
  FROM tasks_tasktransition tr
  JOIN tasks_modeltask mt ON mt.id = tr.model_task_id
  JOIN models_app_model m ON m.id = mt.model_id
  WHERE tr.to_status = 'Done')
SELECT d.item, tt.code, count(*), round(avg(s.x)::numeric,1)
FROM done d
JOIN tasks_tasktype tt ON tt.id = d.task_type_id
CROSS JOIN LATERAL (
  SELECT coalesce(sum(t.minuts),0) x FROM tasks_timerentrada t
  WHERE t.model_task_id = d.model_task_id AND t.fi IS NOT NULL
    AND t.minuts <= 1440 AND t.fi <= d.at) s
WHERE d.item IS NOT NULL GROUP BY 1,2 ORDER BY 3 DESC;

-- trams solapats del mateix tècnic (l'exclusió hauria de fer-ho impossible)
SELECT a.tecnic_id, a.id, a.model_task_id, b.id, b.model_task_id
FROM tasks_timerentrada a JOIN tasks_timerentrada b
  ON a.tecnic_id = b.tecnic_id AND a.id < b.id AND a.model_task_id <> b.model_task_id
 AND a.inici < coalesce(b.fi,'infinity') AND b.inici < coalesce(a.fi,'infinity');
```

---
*Patró A · read-only · cap fitxer del projecte tocat fora d'aquest document.*
