> ⚠️ SUPERADA 2026-07-07 — bug resolt (Play usa open-task idempotent, e854853/f9a6175). Consulta només com a històric.

# DIAGNOSI — 400 a `transition` en obrir la tasca POM des del dashboard

**Data:** 2026-06-26 · **Branca:** `dev` · **Patró:** READ-ONLY (cap codi, cap push)
**Símptoma:** obrir la tasca POM des del DASHBOARD del model → 400 a `model-task-items/250/transition/`
(repetit). Per Mesures (`?mode=entry`) funciona. **Hipòtesi Agus:** la tasca ja era Done.

---

## ⚖️ VEREDICTE (resum)

**La hipòtesi "ja era Done" és parcialment certa (històricament) però NO és la causa.** La ModelTask 250
està **InProgress** ara mateix. La causa real:

> El transport del dashboard (WorkPlan) obre la tasca amb una **transició CRUA** `→InProgress`
> ([WorkPlan.jsx:229](frontend/src/components/model/WorkPlan.jsx#L229)), que passa per la whitelist `ALLOWED` ([services_c.py:14](backend/fhort/tasks/services_c.py#L14)). `InProgress → InProgress`
> **NO hi és** → 400 "Transició no permesa". El guard `needsStart` que ho hauria d'evitar es basa en
> l'**estat de la TARGETA al frontend**, que amb una tasca tan rebotada (76 transicions, sessions
> concurrents) queda **OBSOLET** → el guard falla i es demana la transició invàlida.
> Mesures funciona perquè entra per `open-task`, que és **idempotent** (no fa mai InProgress→InProgress).

---

## PREGUNTA 1 — Estat real de ModelTask 250 (schema `fhort`, read-only)

| Camp | Valor |
|---|---|
| task_type | **`pom`** |
| status | **`InProgress`** (NO Done) |
| started_at | 2026-06-23 15:54 |
| finished_at | `None` |
| model | 186 · `FTT-CO27-0001` |
| assignee | profile **1 = Agustí Devant (a.devant@fhort.cat)** → la tasca és de l'usuari mateix |
| nre. transicions | **76** (molt rebotada) |

Historial recent (TaskTransition, últimes): `Paused→InProgress` (09:55:56), `InProgress→Paused`
(09:55:55), `Done→InProgress` (09:28:23), `InProgress→Done` (09:28:19), `Done→InProgress` (08:37)…
→ **churn ràpid** Done↔InProgress↔Paused. **Ara mateix: InProgress.** La hipòtesi "Done" descriu un
estat pel qual ha passat moltes vegades, però no l'actual.

---

## PREGUNTA 2 — Com obre el dashboard la tasca POM i per què 400

**Cadena:** DashboardTab → `<WorkPlan>` ([DashboardTab.jsx:130](frontend/src/components/model/DashboardTab.jsx#L130)) → `TaskCard` → botó Play → `handlePlay`
→ `playMine`.

- **Transició enviada:** `modelTasks.transition(250, { to_status: 'InProgress' })` →
  `POST /api/v1/model-task-items/250/transition/` ([endpoints.js:173](frontend/src/api/endpoints.js#L173), cridat a [WorkPlan.jsx:229](frontend/src/components/model/WorkPlan.jsx#L229)).
- **Per què 400:** `transition_task` valida contra `ALLOWED` ([services_c.py:52-53](backend/fhort/tasks/services_c.py#L52-L53)):
  ```python
  ALLOWED = { 'Pending':{'InProgress'}, 'Paused':{'InProgress'},
              'InProgress':{'Paused','Done'}, 'Done':{'InProgress'} }   # services_c.py:11-16
  if to_status not in ALLOWED.get(frm, set()):
      raise TransitionError(f'Transició no permesa: {frm} → {to_status}')   # → 400
  ```
  `InProgress → InProgress` **no hi és** → 400. (És exactament la transició que es demana sobre 250.)
- **El guard que ho hauria d'evitar** ([WorkPlan.jsx:225-229](frontend/src/components/model/WorkPlan.jsx#L225-L229), commit `e3a439b` 25/06):
  ```js
  const needsStart = task.status !== 'InProgress'
  if (route) { if (needsStart) modelTasks.transition(task.id,{to_status:'InProgress'}).catch(()=>{}); navigate(route) }
  ```
  El guard mira `task.status` de la **TARGETA** (dades de `model_dashboard_view`, que retorna l'estat
  cru, [views.py:2086](backend/fhort/models_app/views.py#L2086)). Si la targeta es va carregar quan 250 era `Done`/`Paused`/`Pending` i
  després ha passat a `InProgress` (sessió concurrent / el propi churn), `needsStart` és `true` amb un
  estat real `InProgress` → es demana `InProgress→InProgress` → **400**. El `.catch(()=>{})` empassa
  l'error (el camí amb-eina navega igualment), però el 400 és real i es repeteix a cada clic/intent
  amb dades obsoletes.
- **Per què el play és clicable tot i ser MEVA i InProgress:** `TransportBtn` bloqueja de debò el clic
  inactiu (`disabled={!active}` + `if (active) onClick()`, [WorkPlan.jsx:73-87](frontend/src/components/model/WorkPlan.jsx#L73)). Per a una tasca InProgress
  `transport.play=false` ([WorkPlan.jsx:57](frontend/src/components/model/WorkPlan.jsx#L57)) → play inactiu. Per tant el 400 NOMÉS es pot disparar quan la
  targeta mostra un estat **diferent d'InProgress** (obsolet) → play actiu → `needsStart=true`.

---

## PREGUNTA 3 — Per què Mesures funciona i el dashboard no (divergència)

| | Dashboard (WorkPlan) | Mesures (`?mode=entry` / botó "Editar POM") |
|---|---|---|
| Crida | `modelTasks.transition(id,{to_status:'InProgress'})` cru ([WorkPlan.jsx:229](frontend/src/components/model/WorkPlan.jsx#L229)) | `models.openTask(id,'pom')` → `open-task` ([ModelSheet.jsx enterEdit→openTask](frontend/src/pages/ModelSheet.jsx)) |
| Validació | `ALLOWED` estricta → **400 si InProgress→InProgress** | servei **idempotent / conscient de l'estat** |
| Resultat sobre 250 (InProgress) | 400 | OK (no-op) |

**`open-task` és idempotent** ([views_b.py:508-519](backend/fhort/tasks/views_b.py#L508-L519)):
```python
if task.status != 'InProgress':          # només transiciona si CAL
    transition_task(task, 'InProgress', profile)   # (si falla → 409, no 400 nu)
elif task.assignee_id != profile.id:     # ja En curs d'un altre → claim, sense re-transicionar
    task.assignee = profile; ...
# ja meva i En curs → NO-OP
```
→ `open-task` **mai** demana `InProgress→InProgress`; comprova l'estat **al servidor** (no a una
targeta obsoleta). Per això el camí de Mesures no peta i el del dashboard sí. El guard `needsStart`
del WorkPlan és un intent de replicar aquesta comprovació **al client**, però amb dades que poden
quedar obsoletes (≠ comprovar-ho al servidor com fa `open-task`).

---

## PREGUNTA 4 — Decisió a portar (fets per a l'Agus, NO implementar)

**Context:** la tasca `pom` 250 s'ha obert/reobert 76 vegades i fa churn Done↔InProgress↔Paused; ara
és InProgress. La reobertura d'un POM ja existeix com a **"Editar POM"** dins Mesures (camí `open-task`,
segur). El dashboard duplica l'obertura amb una transició crua fràgil davant d'estats obsolets.

**Opcions (per decidir):**

1. **Convergir el dashboard al camí segur (recomanació tècnica):** que el Play del WorkPlan obri la
   tasca via `open-task` (idempotent, comprova l'estat al servidor) en lloc de `transition` cru
   ([WorkPlan.jsx:229](frontend/src/components/model/WorkPlan.jsx#L229)). Elimina el 400 **independentment** de si la targeta està obsoleta, i
   unifica amb Mesures. És el mateix patró que ja resol el cas a Mesures.
   *(Alternativa mínima: re-llegir l'estat real abans de transicionar; però duplica el que `open-task`
   ja fa bé.)*

2. **Comportament de la tasca POM Done/reoberta al dashboard:** decidir si una `pom` ja completada
   (o en aquest estat de churn) ha de seguir mostrant transport de "play" al dashboard, o si la
   reobertura ha de quedar només a "Editar POM" (Mesures). Ocultar/inhabilitar-la NO resol per si sol
   el cas InProgress-obsolet (opció 1 sí).

3. **No fer res al frontend i acceptar el 400 empassat:** el camí amb-eina ja fa `.catch(()=>{})` i
   navega; el 400 és sorollós (network/console, "repetit") però no bloqueja la navegació. Queda com a
   deute si es prioritza una altra cosa.

**Fet clau per a la decisió:** el problema NO és "Done"; és **transició crua + estat de targeta
obsolet** vs **`open-task` idempotent**. La via 1 ataca l'arrel; la via 2 és una qüestió de producte
(afordança) ortogonal.

---

### Metodologia
Estat real de 250 i historial via shell read-only (schema `fhort`). Traça completa del transport
(WorkPlan `playMine`/`TransportBtn`/`TRANSPORT`), `ALLOWED` (`services_c.py`), serialització d'estat del
dashboard (`model_dashboard_view`) i contrast amb `open-task` (`views_b.py`). Provenència: el guard
`needsStart` és de `e3a439b` (25/06) i el bundle servit (dist 10:09) JA el conté → no és "bundle stale".
Tot read-only; cap canvi de codi a la Part C.
