> ⚠️ SUPERADA 2026-07-07 — implementada (GAPs cadena tasca: 66fac8f/f53eb38). Consulta només com a històric.

# DIAGNOSI P0 — Cadena de tasca (obrir/iniciar/pausar/aturar/reobrir)

- **Data:** 2026-06-26
- **Branca / HEAD:** `dev` @ `13d2d46` (codi d'avui; posterior a edició inline 24/06, jubilació EscalatTask, fix `e3a439b` 25/06)
- **Patró:** A — diagnosi READ-ONLY. NO s'ha tocat codi ni dades ni s'ha fet migració.
- **Substitueix (refresca):** `DIAGNOSI_P0_PLA_TREBALL` (21/06), anterior als canvis d'edició inline.

> Convenció: **FET** = verificat amb fitxer:línia o dada. **💡 PROPOSTA** = recomanació, NO implementada.

---

## Resum executiu

- **El servei `transition_task` i la UI de WorkPlan són sòlids** contra transicions prohibides: el mapa `TRANSPORT` gateja els botons per estat i `playMine` té el guard `needsStart`. **Cap camí demana InProgress→InProgress ni Pending/Paused→Done.** (FET, P2)
- **GAP P0 (FET):** els camins que obren una tasca des de **WorkPlan → URL del ModelSheet** (`pom` via `?mode=entry` i `size_check` via `?task_id=`) deixen la tasca **InProgress però NO la registren a `activeTaskRef`**, l'únic mecanisme que la pausa en sortir. → **InProgress orfes + timers oberts que no es tanquen.** (P3)
- **Anomalia de dades (FET):** ara mateix **0 ModelTask InProgress** però **3 timers oberts orfes** sobre 2 tasques `pom` ja **Paused** (task 152 amb **2 timers**), totes del tècnic 1, del 25/06 vespre. (P4)
- `_close_open_timer` tanca **només `.first()`** → si una tasca acumula 2+ timers oberts, en queda un de penjat. (FET, P4)

---

## PREGUNTA 1 — Inventari exhaustiu de camins d'entrada a `transition`

Endpoints (FET): [endpoints.js:34](../../frontend/src/api/endpoints.js#L34) `openTask` → `POST /models/:id/open-task/` · [endpoints.js:171](../../frontend/src/api/endpoints.js#L171) `transition` → `POST /model-task-items/:id/transition/` · [endpoints.js:173](../../frontend/src/api/endpoints.js#L173) `claim`.

| # | Superfície (fitxer:línia) | Acció | `to_status` | Guard d'estat ABANS |
|---|---|---|---|---|
| 1 | [WorkPlan.jsx:219-236](../../frontend/src/components/model/WorkPlan.jsx#L219) `playMine` | Play (start/resume/reopen) | `InProgress` | **`needsStart = status !== 'InProgress'`** (:225) + UI `TRANSPORT` |
| 2 | [WorkPlan.jsx:203-214](../../frontend/src/components/model/WorkPlan.jsx#L203) `doTransition` | Play sense eina / Pause / Stop | param | només cridada des de playMine (needsStart) i handlePause/handleStop (gated TRANSPORT) |
| 3 | [WorkPlan.jsx:268](../../frontend/src/components/model/WorkPlan.jsx#L268) `handlePause` | Pause | `Paused` | botó visible **només si InProgress** (`TRANSPORT`, :54-59) |
| 4 | [WorkPlan.jsx:269](../../frontend/src/components/model/WorkPlan.jsx#L269) `handleStop` | Stop (fet 100%) | `Done` | botó visible **només si InProgress** (`TRANSPORT`) |
| 5 | [WorkPlan.jsx:247-265](../../frontend/src/components/model/WorkPlan.jsx#L247) `confirmHandoff` | claim + Play | `claim` → `InProgress` (via playMine) | claim primer; després playMine amb `needsStart` |
| 6 | [ModelSheet.jsx:186-200](../../frontend/src/pages/ModelSheet.jsx#L186) `enterEdit` | obrir tasca inline (botó) | `InProgress` (via open-task) | open-task guarda servidor-side (`if status != InProgress`) |
| 7 | [ModelSheet.jsx:160-167](../../frontend/src/pages/ModelSheet.jsx#L160) `openTaskAndGo` | porta-menú → navega | `InProgress` (via open-task) | igual (open-task) |
| 8 | [ModelSheet.jsx:201-206](../../frontend/src/pages/ModelSheet.jsx#L201) `exitEdit` / [:208-213](../../frontend/src/pages/ModelSheet.jsx#L208) efectes tab-change + unmount | Pause en sortir | `Paused` (via `pauseActiveTask`) | **`activeTaskRef != null`** (guard idempotent, :180-185) |
| 9 | [TechSheetEditor.jsx:554-567](../../frontend/src/pages/TechSheetEditor.jsx#L554) cleanup d'unmount | Pause en sortir de la fitxa | `Paused` | `if (taskId)` (fetch `keepalive`) |

**Backend que rep:** [views_b.py:384-410](../../backend/fhort/tasks/views_b.py#L384) `transition_task_view` (400 si `to_status` buit o `TransitionError`) · [views_b.py:468-512](../../backend/fhort/tasks/views_b.py#L468) `open_model_task_view` (transiciona InProgress **només si `status != 'InProgress'`**; `TransitionError` → **409**, no 400).

**Jubilats / inexistents avui (FET):** `KanbanTasks.jsx` **no existeix** (cap fitxer a `frontend/src/pages/`); `EscalatTask`/`ModelMeasurements` standalone **jubilats** → `/models/:id/mesures` és `MesuresRedirect` ([App.jsx:147](../../frontend/src/App.jsx#L147)) i `/models/:id/escalat` entra al ModelSheet amb `autoEdit` ([App.jsx:150](../../frontend/src/App.jsx#L150)). `watchpoints.reopen` ([endpoints.js:80](../../frontend/src/api/endpoints.js#L80)) és **domini Watchpoints, NO una transició de ModelTask** (fora d'abast).

---

## PREGUNTA 2 — El guard `e3a439b` (`needsStart`) i ALLOWED

**ALLOWED** ([services_c.py:11-16](../../backend/fhort/tasks/services_c.py#L11)):
```
Pending → {InProgress} · Paused → {InProgress} · InProgress → {Paused, Done} · Done → {InProgress}
```
Qualsevol altra combinació → `TransitionError` → **400** a la view de transition.

**On viu el guard (FET):**
- `needsStart = task.status !== 'InProgress'` a [WorkPlan.jsx:225](../../frontend/src/components/model/WorkPlan.jsx#L225) (dins `playMine`). Hereten aquest punt comú: handlePlay (propi), confirmHandoff (handoff), i qualsevol Play futur que passi per `playMine`.
- Guard equivalent al backend per a open-task: `if task.status != 'InProgress': transition_task(InProgress)` ([views_b.py:508](../../backend/fhort/tasks/views_b.py#L508)) → els camins 6/7 (enterEdit, openTaskAndGo) NO poden disparar InProgress→InProgress.
- Guard de pausa idempotent al ModelSheet: `pauseActiveTask` només transiciona si `activeTaskRef != null` ([ModelSheet.jsx:180-185](../../frontend/src/pages/ModelSheet.jsx#L180)) → evita Paused→Paused (400) del doble-pause.

**Pregunta crítica A — algun camí demana InProgress cegament (assumint Pending)?**
**FET: NO.** Tots els camins de Play passen per `playMine`/`needsStart` (frontend) o per open-task amb guard servidor (backend). El bug original (InProgress→InProgress 400) està tancat per partida doble.

**Pregunta crítica B — algun camí Pending→Done o Paused→Done (saltant InProgress)?**
**FET: NO des de la UI.** El mapa `TRANSPORT` ([WorkPlan.jsx:54-59](../../frontend/src/components/model/WorkPlan.jsx#L54)) només mostra **Stop/Pause quan la tasca és InProgress**; Play (→InProgress) només a Pending/Paused/Done. Per tant els botons no poden generar Pending/Paused→Done. Si arribés una crida directa amb aquesta transició, el backend la rebutjaria amb 400 (defensa de fons correcta).

> **Conclusió P2:** la cadena està blindada contra transicions prohibides. El risc NO és el 400 de transició; és el **timer/estat que queda obert** (P3/P4).

---

## PREGUNTA 3 — Trigger eina↔timer al món NOU (edició inline ModelSheet)

**Entrada/sortida de mode edició (FET):**
- `enterEdit(tab, code)` ([ModelSheet.jsx:186-200](../../frontend/src/pages/ModelSheet.jsx#L186)) → `openTask` (InProgress servidor) → desa `editTaskId` **i** `activeTaskRef.current = task_id` (:192).
- `exitEdit` ([:201-206](../../frontend/src/pages/ModelSheet.jsx#L201)) → `pauseActiveTask()` → Paused. Disparat per: canvi de tab ([:208-210](../../frontend/src/pages/ModelSheet.jsx#L208)) i **unmount** ([:211-213](../../frontend/src/pages/ModelSheet.jsx#L211)). Idempotent (ref a null després de la 1a pausa).
- **Coherència amb ALLOWED:** InProgress→Paused ✓. Sortir d'una tasca **ja Done**: `pauseActiveTask` només actua si `activeTaskRef != null`; després d'un Stop la tasca no es reobre sola, i el ref es buida en pausar → no es demana Done→Paused (que seria 400). ✓

**Camí intern `openTask`/`enterEdit` vs camí `?task_id=` — deriven del MATEIX punt? (verificació del 9720917)**
**FET: el MODE (entrada vs treball) sí deriva del tipus de tasca, però el TRACKING de pausa NO és comú.** `toolRoute` ([WorkPlan.jsx:24-39](../../frontend/src/components/model/WorkPlan.jsx#L24)):
- `pom` → `/models/:id?tab=Mesures&mode=entry` (sense task_id) → mode ENTRADA derivat de `entryMode` ([ModelSheet.jsx:152](../../frontend/src/pages/ModelSheet.jsx#L152)).
- `size_check` → `/models/:id?tab=Mesures&task_id=` → mode TREBALL via `autoTaskRef` ([ModelSheet.jsx:230-238](../../frontend/src/pages/ModelSheet.jsx#L230)).
- `grading` → `/models/:id/escalat?task_id=` → `autoEdit='Escalat'` → `enterEdit` ([:217-223](../../frontend/src/pages/ModelSheet.jsx#L217)).

### 🔴 GAP P0 (FET) — InProgress orfes des dels camins WorkPlan→URL
Només **`enterEdit`** (botó intern) i **`autoEdit`** (ruta `/escalat`) **omplen `activeTaskRef`** → són els únics que es pausen en sortir. En canvi:

1. **`pom` via WorkPlan** (`?mode=entry`): `playMine` obre InProgress (timer) i navega; al ModelSheet **NO es crida `enterEdit`** (el wizard d'entrada deriva de `?mode=entry`), `editTaskId` i `activeTaskRef` queden **null** → en sortir/desmuntar **NO es pausa** la tasca. **InProgress + timer queden penjats.**
2. **`size_check` via WorkPlan/redirect** (`?task_id=`): `autoTaskRef` ([:230-238](../../frontend/src/pages/ModelSheet.jsx#L230)) fixa `editTaskId` i `editing='Mesures'` **però NO `activeTaskRef`** → `pauseActiveTask` (que mira `activeTaskRef`) **no la pausa** en sortir. El comentari del codi (:228-229) diu "es pausa en sortir/desmuntar (com feia ModelMeasurements)", **però el codi no ho fa**.

> **Efecte:** una tasca oberta des de WorkPlan (pom/size_check) entra a InProgress, però el ModelSheet no la pausa quan l'usuari surt → estat InProgress i timer oberts que només es tanquen si, més tard, una ALTRA tasca del mateix tècnic dispara l'exclusió un-per-tècnic. Això explica els timers orfes de P4.

---

## PREGUNTA 4 — Estats bruts a staging (inventari, NO tocat)

Consultat amb `schema_context('fhort')`.

**FET — ModelTask InProgress ARA:** **0** (cap tasca InProgress; cap anomalia d'exclusió 2+/tècnic en aquest moment).

**FET — Recompte d'estats:** Pending 62 · Paused 16 · Done 8.

**FET — Timers oberts orfes (`fi IS NULL, actiu=True`):** **3**, tots del **tècnic 1**, sobre tasques **ja Paused** (incoherència: un timer obert hauria d'implicar InProgress):

| timer pk | task pk | model | task_type | estat tasca | inici |
|---|---|---|---|---|---|
| 169 | 152 | BRW-FW26-0015 | pom | **Paused** | 2026-06-25 18:39:41 |
| 170 | 152 | BRW-FW26-0015 | pom | **Paused** | 2026-06-25 18:41:51 |
| 166 | 167 | BRW-FW26-0006 | pom | **Paused** | 2026-06-25 18:32:19 |

- **Task 152 té DOS timers oberts.** `_close_open_timer` ([services_c.py:24-31](../../backend/fhort/tasks/services_c.py#L24)) tanca **només `.first()`** → en una situació de 2 timers oberts, en queda un de penjat de forma permanent. (FET)
- Totes són `pom` del tècnic 1, finestra **25/06 18:29-18:41** = sessió de proves d'ahir, just quan s'estaven validant els canvis d'edició inline + fixos. Coherent amb el GAP P3 (pom via WorkPlan no es pausa).

---

## Síntesi de riscos

| Risc | Estat | Evidència |
|---|---|---|
| 400 InProgress→InProgress (bug original) | ✅ **TANCAT** | needsStart (WorkPlan:225) + open-task guard (views_b:508) |
| 400 Pending/Paused→Done | ✅ **No accessible** des de UI | TRANSPORT (WorkPlan:54-59) |
| 400 Paused→Paused (doble-pause) | ✅ **TANCAT** | activeTaskRef/pauseActiveTask (ModelSheet:180-185) |
| **InProgress + timer orfe (pom `?mode=entry`)** | 🔴 **OBERT** | ModelSheet:152 no omple activeTaskRef |
| **InProgress + timer orfe (size_check `?task_id=`)** | 🔴 **OBERT** | ModelSheet:230-238 no omple activeTaskRef |
| Timer penjat si 2+ oberts | 🟠 **Latent** | _close_open_timer `.first()` (services_c:24) |
| 3 timers orfes a staging | 🟠 **Dades brutes** | timers 166/169/170 |

---

## 💡 PROPOSTES (NO implementades — decisió i implementació a part)

1. **Tancar el GAP de tracking de pausa** (causa arrel): fer que els camins `?mode=entry` (pom) i `?task_id=` (size_check) registrin la tasca a `activeTaskRef` (o unificar `pauseActiveTask` perquè miri `editTaskId` quan `activeTaskRef` és null), de manera que TOTS els camins que entren a una tasca InProgress la pausin en sortir/desmuntar. Punt comú únic, com ja s'ha fet amb `enterEdit`.
2. **Robustir `_close_open_timer`**: tancar **tots** els timers oberts de la tasca (no només `.first()`), o garantir invariant "≤1 timer obert per tasca" en obrir.
3. **Neteja de dades a staging** (després de validar): tancar/anul·lar els 3 timers orfes (166/169/170) i, si escau, reconciliar `started_at`/`temps_consumit`. NO fer-ho fins decidir-ho.
4. **Reconciliació defensiva** (opcional): comanda de management que detecti timers oberts sobre tasques no-InProgress i els tanqui (xarxa de seguretat contra futures fuites).

---

*Diagnosi read-only. Cap canvi de codi/dades. Generada per equip de diagnosi (director + investigadors + documentador).*
