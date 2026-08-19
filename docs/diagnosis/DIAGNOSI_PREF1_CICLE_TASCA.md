# DIAGNOSI PRE-F1 — EL TERRENY EXACTE DEL CICLE DE TASCA

Data: **2026-08-05** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
HEAD mesurat: **`1f07faaa`** (conté els 11 commits locals del 04-05/08 — són la base, no brutícia)
BD: `ftt_staging` (PG, port 5433). Schemes vius: **`fhort`, `los`, `public`**.

> ⚠️ **HEAD s'ha mogut DURANT aquesta diagnosi** (sessions concurrents de dev): `1f07faaa` →
> **`b9323ce0`** (`d36b8cc7` «el catàleg v3 es RESOL contra staging» + `b9323ce0` «els 23 que no
> existien enlloc»). El `diff` d'aquests dos commits toca **només** `pom/seed_data/` i un command
> nou de `pom/management/`: **cap fitxer ancorat en aquest document**. Àncores re-verificades a
> `b9323ce0` per mostreig (`services_c.py:205`/`:212-213`, `models_app/views.py:1712-1714`,
> `tasks/views.py:85-87`, `views_b.py:560`, `ModelSheet.jsx:1001`/`:1004`) → **totes vives**.

**Abast.** Aquesta diagnosi **no proposa disseny**: mesura el terreny on F1 construirà, amb les
10 decisions ja preses com a context. Sis preguntes, totes de cens.

**Convenció.** Cada afirmació porta `fitxer:línia` **verificat a HEAD**. Quan l'informe
`INFORME_CICLE_TASCA_2026-08-05.md` o `DIAGNOSI_CICLE_TASCA_COMPLET.md` ja donen la resposta, es
cita i **es reverifica l'àncora**. "NO EXISTEIX" = confirmat absent (grep + BD), no especulat.

---

## ⚠️ AVÍS 0 · LES ÀNCORES DELS DOS DOCUMENTS ANTERIORS HAN DERIVAT

Els 11 commits locals han desplaçat **totes** les àncores citades als dos documents font. Abans de
res, la taula de conversió; qui implementi F1 amb les línies antigues picarà a lloc equivocat.

| Document font deia | A HEAD `1f07faaa` és | Peça |
|---|---|---|
| `services_c.py:177` | **`services_c.py:186-187`** | `transition_task` |
| `services_c.py:196-199` / `:199` (C5-UI) | **`services_c.py:205-213`** | guard `tasca_albaranada` |
| `services_c.py:204-215` / `:206` | **`services_c.py:218-229`** | exclusió una-InProgress-per-tècnic |
| `services_c.py:230-231` | **`services_c.py:244-245`** | assignee només si `None` |
| `services_c.py:238-258` | **`services_c.py:251-283`** | meritació + work_order |
| `services_c.py:271-275` | **`services_c.py:285-289`** | crida a `record_actual_time` |
| `models_app/views.py:1615-1618` | **`models_app/views.py:1712-1714`** | obre-i-tanca del desat |
| `models_app/views.py:2098` | **`models_app/views.py:2194`** | `gravar_pom_view` → close |
| `models_app/views.py:1586` | **`models_app/views.py:1682`** | `close_table_view` → close |
| `services_size_check.py:284-288` | **`services_size_check.py:284-288`** ✅ | (l'única que NO ha derivat) |
| `ModelSheet.jsx:924` / `:927` | **`ModelSheet.jsx:1001`** / **`:1004`** | Previsualitzar / Modificar |
| `GuardTascaOblidada.jsx:34-41` | **`GuardTascaOblidada.jsx:55-61`** | llindars (i el fix `55978598` ja hi és) |

Totes les altres àncores d'aquest document s'han llegit **a HEAD** i són les vigents.

---

# Q1 · LA COSTURA FITTING ↔ SIZE_CHECK

## Q1.1 · Veredicte en una frase

**La costura no existeix al backend.** Tot el pont fitting→tasca el fa **el frontend**, amb una
sola crida (`openTask`), i el retorn tasca→fitting el fa **una altra crida del frontend**
(`transition`). L'app `fitting` sencera **no importa `ModelTask` ni `transition_task` ni una sola
vegada**.

Verificació (grep a HEAD sobre tots els fitxers de `fhort/fitting/`):

```
fitting/services.py           → 1 import de tasks, i és `has_delivered_production` (services_e)
fitting/views.py              → 1 import de tasks, i és el model `Production`
fitting/brain.py              → 0
fitting/repas_views.py        → 0
fitting/graded_spec_views.py  → 0
```

Cap `ModelTask`, cap `transition_task`, cap `TaskType` en tota l'app.

## Q1.2 · Com NEIX la tasca `size_check` — pas a pas

**Ningú al backend del fitting la crea.** Els tres camins vius:

| # | Camí | Qui crea | Àncora HEAD |
|---|---|---|---|
| 1 | **Recepta del PM** — `POST models/<id>/define-tasks/` | `define_model_tasks_view` crea totes les de la llista amb `origen='prevista'` | [views_b.py:323](../../backend/fhort/tasks/views_b.py#L323) · `create` a [:337](../../backend/fhort/tasks/views_b.py#L337) i [:351](../../backend/fhort/tasks/views_b.py#L351) |
| 2 | **Planificador** — recompute de cua | `plan_service` crea la que falta | [planning/plan_service.py:323](../../backend/fhort/planning/plan_service.py#L323) |
| 3 | **🔑 LA PORTA REAL DEL FITTING** — `POST models/<id>/open-task/` amb `{code:'size_check', fitting_session_id}` | `open_model_task_view`: **crea-si-falta** + `→InProgress` + **escriu el FK a la sessió** | [views_b.py:521-630](../../backend/fhort/tasks/views_b.py#L521-L630) |

El camí 3 és el que dispara el fitting, i **el dispara el navegador**:

```
FittingConvocatoriaSheet.jsx:72   navigate(`/models/${s.model}?tab=Mesures&fitting_session=${s.id}`)
FittingDetail.jsx:565             <Navigate to={`/models/${session.model}?tab=Mesures&fitting_session=${session.id}`}/>
        ↓
ModelSheet.jsx:338-351            useEffect: si (tab=Mesures && fitting_session && !task_id)
ModelSheet.jsx:342                  models.openTask(id, 'size_check', fittingSessionParam)
        ↓
endpoints.js:79-81                POST /api/v1/models/<id>/open-task/ {code:'size_check', fitting_session_id}
        ↓
views_b.py:560-568                crea-si-falta ModelTask(origen='prevista')
views_b.py:571-574                transition_task(task,'InProgress') → obre TimerEntrada
views_b.py:608-623                escriu task.fitting_session = fs   +   open_session(fs) si Programada
```

**Punt clau per a F1:** `views_b.py:560` busca la tasca amb
`filter(model=model, task_type=tt, origen='prevista')`. Una tasca de **ronda 2** (que per força
serà `origen='ad_hoc'`, §Q4) **és invisible per a aquesta porta**: `open-task` sempre resoldrà
la prevista i mai la de ronda. Vegeu SORPRESA S-4.

## Q1.3 · Com es TRANSICIONA i es TANCA la tasca `size_check`

Tres portes de tancament, **cap d'elles és el mateix punt**:

| # | Qui la tanca | Gest de l'usuari | Àncora HEAD |
|---|---|---|---|
| A | **`resolve_size_check`** (backend) | «Gravar» del *Size Check* | [services_size_check.py:278-290](../../backend/fhort/models_app/services_size_check.py#L278-L290) |
| B | **`SessionActions.doSave`** (frontend) | «Gravar i tornar» del mode sessió | [SessionActions.jsx:44](../../frontend/src/components/model/SessionActions.jsx#L44) |
| C | Stop humà del Pla de treball / arbre | Stop | [WorkPlan.jsx:315-337](../../frontend/src/components/model/WorkPlan.jsx#L315-L337) |

**El camí A, literal a HEAD** ([services_size_check.py:281-288](../../backend/fhort/models_app/services_size_check.py#L281-L288)):

```python
task = (ModelTask.objects
        .filter(model=model, task_type__code='size_check')
        .exclude(status='Done').order_by('-id').first())
if task is not None:
    if task.status != 'InProgress':
        transition_task(task, 'InProgress', profile)   # Done només des d'InProgress
    transition_task(task, 'Done', profile)
```

Tres coses que F1 ha de saber d'aquest bloc:
1. És dins d'un `try/except Exception` amb **gate TOU** ([:289-290](../../backend/fhort/models_app/services_size_check.py#L289-L290)): si peta, **s'empassa l'excepció amb un `logger.warning`** i el `resolve` retorna èxit igualment. El guard d'albarà que llanci aquí **serà invisible**.
2. Només s'executa si `propagat == True`, és a dir **`final_estat == 'Acceptat'`** ([:197-201](../../backend/fhort/models_app/services_size_check.py#L197-L201)). Amb una sola línia `valor_descartat` l'estat final és `Rebutjat` i **la tasca no es tanca**.
3. El `.order_by('-id').first()` agafa **la més nova no-Done** — no la de la sessió. No mira `fitting_session_id`.

**El camí B** (`SessionActions.jsx:29-47`) fa la seqüència `close piece → seal session → transition
Done`, i el `transition` va embolcallat en `try{}catch{ /* no-op */ }`: **si el 400/409 arriba, es
menja en silenci** i la sessió queda Tancada amb la tasca viva.

**Reagendament quan NO es tanca** ([services_size_check.py:292-296](../../backend/fhort/models_app/services_size_check.py#L292-L296) → [tasks/services_scheduling.py:15-40](../../backend/fhort/tasks/services_scheduling.py#L15-L40)): escriu `planned_start`/`planned_end`/`planned_locked` **directament amb `.save(update_fields=...)`**, sense `transition_task` i **sense tocar `status`**.

## Q1.4 · `close_piece_fitting` i `consolidate_base_from_fitting` — hi toquen?

**NO. Cap de les dues toca `ModelTask`.** Verificat llegint-les senceres:

| Funció | Àncora HEAD | Què escriu | Toca ModelTask? |
|---|---|---|---|
| `consolidate_base_from_fitting` | [fitting/services.py:354-418](../../backend/fhort/fitting/services.py#L354-L418) | `BaseMeasurement` (origen `FITTED`) + `MeasurementChangeLog` (via senyal) + derivació a germanes | ❌ |
| `close_piece_fitting` | [fitting/services.py:421-527](../../backend/fhort/fitting/services.py#L421-L527) | l'anterior + Welford de POM (`update_client_profile`) + `measurements_version++` + `brain` stub + `_seal_session` | ❌ |

El tancament de la peça i el de la tasca són **dos actes independents units només pel frontend**
(`SessionActions.jsx:32` i `:44`).

## Q1.5 · La relació grading ↔ `sample_check`

### ❌ **`sample_check` NO EXISTEIX. Enlloc.**

- **Codi:** `grep -rn "sample_check" --include=*.py` sobre tot `backend/` → **0 coincidències**.
- **BD:** `SELECT code FROM <schema>.tasks_tasktype` als **tres** schemes → cap fila.

**F1 l'haurà de crear.** Cens complet dels TaskType vius, per si serveix de motlle:

`tasks_tasktype` viu **NOMÉS als schemes de tenant**: `to_regclass('public.tasks_tasktype')` →
**NULL**. `fhort` en té **15**, `los` en té **14**.

| code | name | fase | tipus | eina | mode | facturable | order | ModelTask a `fhort` |
|---|---|---|---|---|---|---|---|---|
| `patronatge` | Patronatge | Dev. tècnic | Interna | — | — | ✅ | **0** | **0** ⚠️ només a `fhort` |
| `design_review` | Revisió de disseny | Disseny | Externa-lliure | — | — | ✅ | 5 | 1 |
| `design_clarify` | Aclariments amb disseny | Disseny | Externa-lliure | — | — | ❌ | 6 | 0 |
| `pattern_digit` | Patró digitalització | Dev. tècnic | Interna | `patro` | `digitalitzar` | ✅ | 10 | 4 |
| `pattern_cad` | Patró CAD | Dev. tècnic | Interna | `patro` | `disseny_base` | ✅ | 20 | 16 |
| `pattern_hand` | Patró a mà | Dev. tècnic | Externa-lliure | — | — | ✅ | 30 | 0 |
| `pom` | Definició POM | Dev. tècnic | Interna | `mesures` | `autoria_base` | ✅ | 40 | **24** |
| `size_check` | **Mesurar prenda** | Dev. tècnic | Interna | `mesures` | `presa` | ✅ | 45 | 6 |
| `grading` | Escalat | Dev. tècnic | Interna | `escalat` | `propagacio` | ✅ | 46 | 18 |
| `tech_sheet` | Fitxa tècnica | Dev. tècnic | Interna | `fitxa` | `document` | ✅ | 50 | 17 |
| `pattern_review` | Revisió de patró CAD | Dev. tècnic | Interna | `patro` | `revisio` | ✅ | 55 | 0 |
| `bom` | Definició BOM | Dev. tècnic | Interna | `fitxa` | `bom` | ✅ | 70 | 0 |
| `scaling` | Escalat CAD | Dev. tècnic | Interna | `patro` | `escalat` | ✅ | 81 | 0 |
| `marking` | Marcada | Dev. tècnic | Interna | `patro` | `marcada` | ✅ | 82 | 0 |
| `audit` | Auditoria de model | Dev. tècnic | Externa-lliure | — | — | ❌ | 90 | 15 |

`los` = les mateixes 14, **sense `patronatge`** (i amb 0 `ModelTask` en total).

**No hi ha cap camp `es_lliurable`** al `TaskType` (§Q4.2). La decisió RONDA el demana; F1 el
crearà.

**El pont `grading` ↔ mostra:** el TaskType `grading` existeix i el porta l'eina `escalat`, però
**el seu tancament automàtic no existeix**: no hi ha cap `transition_task` al camí de
`generar-grading` (§Q2). L'única referència a `task_type__code='grading'` fora del catàleg és una
consulta de **lectura** a [models_app/views.py:2673](../../backend/fhort/models_app/views.py#L2673).

## Q1.6 · La convocatòria / programació de sessió (calendari)

| Peça | Àncora HEAD | Escriu | Referència a `ModelTask`? |
|---|---|---|---|
| `schedule_session` | [fitting/services.py:133-187](../../backend/fhort/fitting/services.py#L133-L187) | `FittingSession` (estat `Programada`) + M2M `attendees` | ❌ — només `recompute_for_technicians(attendees)` |
| `schedule_bulk` (convocatòria) | [fitting/services.py:190-274](../../backend/fhort/fitting/services.py#L190-L274) | N × `FittingSession` encadenades amb `convocatoria` UUID compartit | ❌ |
| `open_session` | [fitting/services.py:277-290](../../backend/fhort/fitting/services.py#L277-L290) | `estat: Programada→Oberta` | ❌ |
| operacions de grup (`reschedule_group`, `add_model_to_group`, …) | [fitting/services.py:844-1030](../../backend/fhort/fitting/services.py#L844-L1030) | `FittingSession` | ❌ |

**Conclusió Q1.6:** la convocatòria **només toca el calendari**. L'única unió amb la tasca és el
FK invers `ModelTask.fitting_session` ([tasks/models.py:109-110](../../backend/fhort/tasks/models.py#L109-L110)), i **s'escriu en un únic lloc de tot el codi**:
[views_b.py:619-621](../../backend/fhort/tasks/views_b.py#L619-L621), quan el navegador passa
`fitting_session_id` a `open-task`.

**Estat viu a BD:** de **101** `ModelTask` a `fhort`, **1 sola** té `fitting_session_id`. Hi ha 25
`FittingSession` (17 Programada · 3 Oberta · 5 Tancada). El pont existeix i està **pràcticament
verge**.

---

# Q2 · CENS EXACTE DE TANCAMENTS AUTOMÀTICS A `Done`

## Q2.0 · Mètode i tancament del cens

`grep -rn "transition_task"` sobre tot `backend/` (fora de tests i migracions) dona **exactament 8
punts de crida** productius. `grep` de `status='Done'` assignat directament: **cap escriptura**
(totes les coincidències són `filter`/`exclude`/`count`). `tasks/signals.py` **no té cap receiver**
([signals.py:1-11](../../backend/fhort/tasks/signals.py#L1-L11): retirats a Sprint 0). **No hi ha
cap camí a `Done` que no passi per `transition_task`.**

## Q2.1 · La taula del cens

| # | Punt de codi (HEAD) | Estat destí | Gest de l'usuari | TaskType afectat | És «no és el gest de tancar»? |
|---|---|---|---|---|---|
| 1 | **[models_app/views.py:1712-1714](../../backend/fhort/models_app/views.py#L1712-L1714)** (`_close_pom_task_for_model`), cridat des de **[:2194](../../backend/fhort/models_app/views.py#L2194)** (`gravar_pom_view`) | `InProgress` + **`Done`** | **«Gravar POM»** ([MeasuresEntryPanel.jsx:234](../../frontend/src/components/model/MeasuresEntryPanel.jsx#L234)) | **`pom`** (resol per `task_type__code='pom'`, `order_by('id').first()`) | ✅ **SÍ — el conegut** |
| 2 | mateixa funció, cridada des de **[:1682](../../backend/fhort/models_app/views.py#L1682)** (`close_table_view`) | `InProgress` + **`Done`** | «Tancar taula» → `POST models/<id>/tancar-taula/` | **`pom`** | ⚠️ mig-sí: «tancar taula» sona a tancar, però tanca la **tasca**, no la taula |
| 3 | **[services_size_check.py:286-287](../../backend/fhort/models_app/services_size_check.py#L286-L287)** (`resolve_size_check`) | `InProgress` + **`Done`** | **«Gravar»** del Size Check ([CheckMeasureEditor.jsx:388](../../frontend/src/components/model/CheckMeasureEditor.jsx#L388)) | **`size_check`** (`.exclude(status='Done').order_by('-id').first()`) | ✅ **SÍ — el germà que faltava** |
| 4 | **[SessionActions.jsx:44](../../frontend/src/components/model/SessionActions.jsx#L44)** (frontend) | **`Done`** | **«Gravar i tornar»** del mode sessió | el `taskId` que li passa `ModelSheet` (a la pràctica **`size_check`**) | ✅ **SÍ — tercer germà, i viu al navegador** |
| 5 | [WorkPlan.jsx:323-327](../../frontend/src/components/model/WorkPlan.jsx#L323-L327) (`handleStop`) | `InProgress` + `Done` encadenats | **Stop** | qualsevol | ❌ és el gest de tancar |
| 6 | [views_b.py:459](../../backend/fhort/tasks/views_b.py#L459) (`transition_task_view`) | el que demani el client | porta genèrica | qualsevol | ❌ és la porta explícita |
| 7 | [views_b.py:573](../../backend/fhort/tasks/views_b.py#L573) (`open_model_task_view`) | **`InProgress` només** | obrir eina | qualsevol | — (mai `Done`) |
| 8 | [pausa_tasques_oblidades.py:91](../../backend/fhort/tasks/management/commands/pausa_tasques_oblidades.py#L91) | **`Paused` només** | cron (no instal·lada, D-9) | qualsevol | — (mai `Done`) |
| 9 | [retype_scaling_to_grading.py:66-67](../../backend/fhort/tasks/management/commands/retype_scaling_to_grading.py#L66-L67) | `InProgress` + `Done`, **`force=True`** | command de migració | `scaling`→`grading` | ❌ no és acció d'usuari |

### 🔑 **Resposta a «busca'n TOTS els germans»: n'hi ha TRES, no un.**

`gravar_pom_view` (#1) tenia dos germans no censats a l'informe: **`resolve_size_check` (#3), al
backend**, i **`SessionActions.jsx:44` (#4), al frontend**. El #4 és especialment rellevant per a
F1 perquè **no és al backend**: qui vagi a matar el ping-pong tocant `services_*.py` el deixarà viu.

## Q2.2 · Qui DEPÈN que la tasca quedi `Done` després de desar

Això és el que F1 trencarà conscientment. Cens complet dels consumidors de `status='Done'`:

| Consumidor | Àncora HEAD | Què li passa si desar deixa de tancar | Gravetat |
|---|---|---|---|
| **`Model.pom_task_done`** (serializer) | [models_app/serializers.py:271-278](../../backend/fhort/models_app/serializers.py#L271-L278) — `filter(task_type__code='pom', status='Done').exists()` | passa a `False` | 🟠 **mitigat**: el gate de Mesures és `pomDone \|\| hasBaseValue` ([ModelSheet.jsx:187-189](../../frontend/src/pages/ModelSheet.jsx#L187-L189)) i el model amb valors segueix obert |
| **`finishPomEntry`** (optimisme del front) | [ModelSheet.jsx:268-286](../../frontend/src/pages/ModelSheet.jsx#L268-L286) — escriu `status:'Done'` a la fila **i** `model.pom_task_done = true` en local | **menteix**: pinta Done i el `reloadModel()` immediat el desmenteix → parpelleig | 🔴 **cal tocar-lo a F1** |
| **`generate_delivery_note`** — línies TASK | [commerce/services.py:610-611](../../backend/fhort/commerce/services.py#L610-L611) — `wo.tasks.filter(status='Done', off_recipe=False)` | la tasca **no entra a l'albarà** fins que algú premi Stop | 🔴 **és exactament D-10** («albarà només Done»): **el terreny ja hi és** |
| **preview d'albarà per client** | [commerce/services.py:731-733](../../backend/fhort/commerce/services.py#L731-L733) — `filter(status='Done', delivery_note_lines__isnull=True)` | ídem | 🔴 mateix punt |
| **`model_ready_for_gate`** | [tasks/services_d.py:12-17](../../backend/fhort/tasks/services_d.py#L12-L17) — `qs.exclude(status='Done').count() == 0` | el gate de fase **no s'obre** fins al Stop | 🟠 **és el comportament desitjat** amb D-2 (Stop=Done) |
| **canal d'estat a la marca (federació)** | [tenants/federation_service.py:398-408](../../backend/fhort/tenants/federation_service.py#L398-L408) — `n_done`, `totes_acabades` | la marca veu menys tasques fetes | 🟡 informatiu |
| **`recompute_welford`** | [recompute_welford.py:50](../../backend/fhort/tasks/management/commands/recompute_welford.py#L50) i [:111](../../backend/fhort/tasks/management/commands/recompute_welford.py#L111) — itera `to_status='Done'` | menys mostres, i **més netes** | 🟢 **millora** (és D-3) |
| **planificació** (`plan_service`, `planning/views`) | `exclude(status='Done')` a [plan_service.py:31](../../backend/fhort/planning/plan_service.py#L31), [:44](../../backend/fhort/planning/plan_service.py#L44), [:93](../../backend/fhort/planning/plan_service.py#L93), [:208](../../backend/fhort/planning/plan_service.py#L208), [:359](../../backend/fhort/planning/plan_service.py#L359), [:433](../../backend/fhort/planning/plan_service.py#L433), [:446](../../backend/fhort/planning/plan_service.py#L446), [views.py:183](../../backend/fhort/planning/views.py#L183), [:238](../../backend/fhort/planning/views.py#L238), [:540](../../backend/fhort/planning/views.py#L540) | la tasca **segueix a la cua** fins al Stop | 🟢 **és el que D-2 vol** |
| **`reagenda_tasca`** | [services_scheduling.py:24-26](../../backend/fhort/tasks/services_scheduling.py#L24-L26) — `.exclude(status='Done')` | més candidates | 🟢 |

### Tests que dependrien d'això: **CAP.**

Els 4 fitxers de test que toquen `gravar-pom`/`tancar-taula`/`resolve_size_check`
(`pom/test_guarda_rang_mesura.py`, `models_app/test_c3_e_connexio_derivacio.py`,
`fitting/test_g6_estalitud.py`, `models_app/test_c4_escriptura_germanes.py`) **no asserten cap
estat de tasca** (grep de `'Done'`/`pom_task`/`tasca_finalitzada` → 0 coincidències als quatre).
`models_app/test_gate_mesures_pom_task.py` sí que asserta `pom_task_done`, però **fixa l'estat
directament**, sense passar per cap porta de desat. **F1 no té cap vermell heretat per aquesta via.**

---

# Q3 · CENS DE PUNTS DE BATEC (superfícies de tècnic)

Llista tancada d'escriptures d'usuari sobre un model. Columna clau: **d'on surt el `model_id`**
per a la transició automàtica de sessió de D-1.

## Q3.1 · Fitxa `.ftt`

| Gest | Ruta | Vista (HEAD) | `model_id`? | Superfície |
|---|---|---|---|---|
| **Autosave (cada 2 s)** | `PATCH /api/v1/ftt-documents/<fitxer_id>/` | [ftt_document_views.py:213-246](../../backend/fhort/models_app/ftt_document_views.py#L213-L246) | 🟠 **DEDUÏBLE**: `head.model_id` (`ModelFitxer.model` FK, [models_app/models.py:414](../../backend/fhort/models_app/models.py#L414)) — **no al request** | `tech_sheet` |
| Crear fitxa | `POST /api/v1/models/<model_id>/ftt-document/` | [ftt_document_views.py:158](../../backend/fhort/models_app/ftt_document_views.py#L158) | ✅ **a la URL** | `tech_sheet` |
| Pujar imatge al llenç | `POST /api/v1/ftt-documents/<id>/prepare-asset/` | [ftt_document_views.py:118](../../backend/fhort/models_app/ftt_document_views.py#L118) | 🟠 deduïble via `ModelFitxer` | `tech_sheet` |
| Exportar PDF | `POST /api/v1/ftt-documents/<id>/export/` | [ftt_document_views.py:292](../../backend/fhort/models_app/ftt_document_views.py#L292) | 🟠 deduïble | `tech_sheet` |
| Desar com a plantilla | `POST /api/v1/ftt-documents/<id>/save-as-template/` | [ftt_document_views.py:314](../../backend/fhort/models_app/ftt_document_views.py#L314) | 🟠 deduïble | `tech_sheet` |

**No hi ha «save explícit»**: l'editor **només** té autosave amb `setTimeout` de 2 000 ms
([TechSheetEditor.jsx:3635-3665](../../frontend/src/pages/TechSheetEditor.jsx#L3635-L3665)). El
`fttHeadId.current` es reapunta a cada desat perquè `save_document` encadena versions — **l'id del
`ModelFitxer` canvia a cada batec**, però `model_id` no.

## Q3.2 · Mesures base

| Gest | Ruta | Vista (HEAD) | `model_id`? | Superfície |
|---|---|---|---|---|
| **Editar cel·la de la graella** | `PATCH /api/v1/base-measurements/<id>/` | [models_app/views.py:497-524](../../backend/fhort/models_app/views.py#L497-L524) (`BaseMeasurementViewSet`, `ModelViewSet` complet) | 🟠 **DEDUÏBLE**: `instance.model_id` | `pom` |
| Bateig de la fila | `PATCH /api/v1/base-measurements/<id>/noms/` | [models_app/views.py:3264](../../backend/fhort/models_app/views.py#L3264) | 🟠 deduïble | `pom` |
| Reordenar POMs | `POST /api/v1/models/<id>/base-measurements/reorder/` | [models_app/views.py:3231](../../backend/fhort/models_app/views.py#L3231) | ✅ **a la URL** | `pom` |
| **Gravar POM** | `POST /api/v1/models/<id>/gravar-pom/` | [models_app/views.py:1993](../../backend/fhort/models_app/views.py#L1993) | ✅ a la URL | `pom` · ⚠️ **tanca a Done** (Q2 #1) |
| Tancar taula | `POST /api/v1/models/<id>/tancar-taula/` | [models_app/views.py:1654](../../backend/fhort/models_app/views.py#L1654) | ✅ a la URL | `pom` · ⚠️ **tanca a Done** (Q2 #2) |
| Podar un POM | `POST /api/v1/models/<id>/pom/<pom_id>/desactivar/` | [models_app/views.py:4350](../../backend/fhort/models_app/views.py#L4350) | ✅ a la URL | `pom` |

## Q3.3 · Escalat / graduació

| Gest | Ruta | Vista (HEAD) | `model_id`? | Superfície |
|---|---|---|---|---|
| **Ajustar una talla** | `POST /api/v1/models/<id>/escalat/ajustar-talla/` | [models_app/views.py:2896](../../backend/fhort/models_app/views.py#L2896) | ✅ a la URL | `grading` |
| **Propagar a grading** | `POST /api/v1/models/<id>/generar-grading/` | [models_app/views.py:2558](../../backend/fhort/models_app/views.py#L2558) | ✅ a la URL | `grading` |
| Règim / regla d'un POM | `POST /api/v1/models/<id>/pom/<pom_id>/regim/` | [models_app/views.py:4463](../../backend/fhort/models_app/views.py#L4463) | ✅ a la URL | `grading` |

## Q3.4 · Fitxers i assets del model

| Gest | Ruta | Vista (HEAD) | `model_id`? | Superfície |
|---|---|---|---|---|
| **Pujar fitxer al model** | `POST /api/v1/models/<id>/upload-fitxer/` | [models_app/views.py:2236](../../backend/fhort/models_app/views.py#L2236) | ✅ a la URL | ambigua (cap TaskType propi) |
| Portar un `.ftt` d'un altre model | `POST /api/v1/model-fitxers/<id>/usar-al-model/` | `modelFitxers.usarAlModel`, [endpoints.js:194](../../frontend/src/api/endpoints.js#L194) | ✅ **al cos** (`{model_id}`) | ambigua |
| Portar un fitxer del catàleg | `POST /api/v1/item-fitxers/<id>/usar-al-model/` | [endpoints.js:206](../../frontend/src/api/endpoints.js#L206) | ✅ al cos | ambigua |

## Q3.5 · Fitting

| Gest | Ruta | Vista (HEAD) | `model_id`? | Superfície |
|---|---|---|---|---|
| **Autosave d'una línia de presa** | `PATCH /api/v1/piece-fitting-lines/<id>/` | [fitting/views.py:560-570](../../backend/fhort/fitting/views.py#L560-L570) | 🟠 **DEDUÏBLE**: `piece_fitting__model` ja va al `select_related` ([:568-569](../../backend/fhort/fitting/views.py#L568-L569)) | `size_check` |
| Propagar una línia | `POST /api/v1/piece-fitting-lines/<id>/propagar/` | mateix viewset | 🟠 deduïble | `size_check` |
| Veredicte de peça (gate) | `POST /api/v1/piece-fittings/<id>/set-gate/` | [endpoints.js:673](../../frontend/src/api/endpoints.js#L673) | 🟠 deduïble via `PieceFitting.model` | `size_check` |
| **Tancar peça** | `POST /api/v1/piece-fittings/<id>/close/` | [fitting/services.py:421](../../backend/fhort/fitting/services.py#L421) | 🟠 deduïble (`pf.model`) | `size_check` |
| Descartar preses | `POST /api/v1/piece-fittings/<id>/discard/` | [fitting/services.py:530](../../backend/fhort/fitting/services.py#L530) | 🟠 deduïble | `size_check` |
| Foto de fitting | `POST /api/v1/fitting-photos/` | [endpoints.js:690-697](../../frontend/src/api/endpoints.js#L690-L697) | 🔴 **NO** — va per `session`/`piece_fitting` | `size_check` |
| Notes de sessió | `PATCH /api/v1/fitting-sessions/<id>/` | [FittingDetail.jsx:272](../../frontend/src/pages/FittingDetail.jsx#L272) | 🟠 deduïble (`FittingSession.model`, nullable si és `garment_set`) | `size_check` |

## Q3.6 · Size Check

| Gest | Ruta | Vista (HEAD) | `model_id`? | Superfície |
|---|---|---|---|---|
| Obrir el check | `POST /api/v1/size-checks/open/` | [views_size_check.py:48-55](../../backend/fhort/models_app/views_size_check.py#L48-L55) | ✅ **al cos** (`{model_id}`) | `size_check` |
| **Anotar una línia** | `PATCH /api/v1/size-check-lines/<id>/` | [views_size_check.py:78-85](../../backend/fhort/models_app/views_size_check.py#L78-L85) | 🟠 deduïble (`size_check__model`) | `size_check` |
| **Gravar / Descartar** | `POST /api/v1/size-checks/<id>/resolve/` | [views_size_check.py:62-69](../../backend/fhort/models_app/views_size_check.py#L62-L69) | 🟠 deduïble | `size_check` · ⚠️ **tanca a Done** (Q2 #3) |

## Q3.7 · POM placements (cotes sobre el sketch)

| Gest | Ruta | Vista (HEAD) | `model_id`? | Superfície |
|---|---|---|---|---|
| **Desar precedent de cota** | `POST /api/v1/item-fitxers/<item_id>/pom-placements/` | [pom_placement_views.py:116-150](../../backend/fhort/models_app/pom_placement_views.py#L116-L150) | 🔴 **NO, I NO ÉS DEDUÏBLE** | — |

**🚨 Aquesta és l'única escriptura de tècnic del cens que no pot resoldre cap model.** La
col·locació viu al **CATÀLEG** (`POMPlacement.item_fitxer` → `ItemFitxer`,
[models_app/models.py:1397-1420](../../backend/fhort/models_app/models.py#L1397-L1420)), per decisió
explícita («la casa del precedent és l'ItemFitxer», D1). El `GET` accepta `?model_id=` per resoldre
`bm_id` ([:77](../../backend/fhort/models_app/pom_placement_views.py#L77)), però **el `POST` no el
llegeix ni el podria fer servir**: la fila que escriu no en té camp. Un tècnic que col·loca cotes
des de l'editor de fitxa **escriu fora del model**. → **SORPRESA S-1**.

## Q3.8 · Resum de Q3 per a D-1

| Cas | Quants | Què implica per a la transició automàtica de sessió |
|---|---|---|
| `model_id` **a la URL** | 10 | trivial: middleware/decorador sobre la vista |
| `model_id` **al cos** | 3 | trivial |
| `model_id` **deduïble d'una FK a 1 salt** | 10 | cal un resolutor per-recurs; **tots hi arriben** |
| `model_id` **NO deduïble** | **2** (`pom-placements` POST · `fitting-photos` POST) | el batec s'ha de fer **des del frontend** o no es fa |

**La superfície també és deduïble en tots els casos menys un**: la família de rutes ja mapeja 1:1
al `TaskType.eina`/`mode` del catàleg (§Q1.5) — `mesures`/`escalat`/`fitxa`/`patro`. L'excepció és
**`upload-fitxer`**, que no té TaskType propi (§Q3.4).

---

# Q4 · GENEALOGIA I ESTRUCTURA DE `ModelTask`

## Q4.1 · Camps reals a HEAD

Dump del model ([tasks/models.py:70-127](../../backend/fhort/tasks/models.py#L70-L127)), contrastat
amb `information_schema` (18 columnes a `fhort.tasks_modeltask`, idèntiques a `los`):

| Camp | Tipus | Null | Nota |
|---|---|---|---|
| `id` | bigint PK | — | |
| `model` | FK → `models_app.Model` **CASCADE** | NO | |
| `task_type` | FK → `TaskType` **PROTECT** | NO | |
| `status` | varchar(20) | NO | `Pending`\|`Paused`\|`InProgress`\|`Done` |
| **`origen`** | varchar(20) | NO | **`prevista`\|`ad_hoc`** — default `prevista` |
| `assignee` | FK → `accounts.UserProfile` SET_NULL | SÍ | camp de **planificació** |
| `order` | int ≥ 0 | NO | |
| `started_at` / `finished_at` | timestamptz | SÍ | |
| `estimated_minutes` | int ≥ 0 | SÍ | snapshot en crear |
| `planned_start` / `planned_end` / `planned_locked` | timestamptz / bool | SÍ / SÍ / NO | motor de scheduling |
| `created_at` / `updated_at` | timestamptz | NO | |
| `work_order` | FK → `commerce.WorkOrder` SET_NULL | SÍ | encàrrec (B4a) |
| `off_recipe` | bool | NO | extra fora de recepta |
| **`fitting_session`** | FK → `fitting.FittingSession` SET_NULL | SÍ | punter **MUTABLE** (Sprint Y) |

## Q4.2 · Les tres preguntes directes

### ❌ **FK tasca→tasca: NO EXISTEIX.**
Cap `parent`, cap `predecessora`, cap `depen_de`, cap self-FK. Verificat a **codi**
([models.py:70-124](../../backend/fhort/tasks/models.py#L70-L124): els 5 FK són a `Model`,
`TaskType`, `UserProfile`, `WorkOrder`, `FittingSession`) i a **BD** (`pg_constraint` sobre
`fhort.tasks_modeltask`: **5 FK, cap a `tasks_modeltask`**).
→ **La FK de la RONDA (`ModelTask` → entitat model·seq·motiu) és estructura NOVA.** F1 la crearà.

### ❌ **Camp motiu/origen de rectificació: NO EXISTEIX.**
`origen` és **un enum de 2 valors** (`prevista`/`ad_hoc`), no un text de motiu, i el seu significat
documentat ([models.py:74-78](../../backend/fhort/tasks/models.py#L74-L78)) és *«fora de
l'encàrrec»*, **no** *«correcció»* ni *«ronda»*. No hi ha cap `motiu`, `notes`, `rectifica_a` ni
`ronda`.
→ **Els valors `correcció` i `ronda` de D-5 no caben a `origen`.** O s'amplien els `ORIGEN_CHOICES`,
o van a l'entitat nova.

**On s'escriu `ad_hoc` avui:** UN sol punt productiu,
[views_b.py:291](../../backend/fhort/tasks/views_b.py#L291) (alta d'extra sobre un WorkOrder, cos
`{work_order, model, task_type}`, [:258](../../backend/fhort/tasks/views_b.py#L258)).
**Estat viu a BD: `origen='ad_hoc'` té ZERO files.** Les 101 `ModelTask` de `fhort` són totes
`prevista` (10 Done · 36 Paused · 55 Pending · **0 InProgress**). El camí de la ronda existeix al
model però **mai no s'ha exercit**.

### ⚠️ **Unique constraints: n'hi ha UNA, i és PARCIAL.**

```sql
CREATE UNIQUE INDEX uniq_prevista_model_tasktype
  ON fhort.tasks_modeltask USING btree (model_id, task_type_id)
  WHERE ((origen)::text = 'prevista'::text);
```

Viva **als dos schemes de tenant** (`fhort` i `los`) i declarada a
[tasks/models.py:119-123](../../backend/fhort/tasks/models.py#L119-L123). **Cap violació viva**
(query de duplicats → 0 files).

> **Resposta directa a «la ronda 2 en crearà una segona del mateix tipus — peta?»**
>
> **NO peta, SI I NOMÉS SI neix amb `origen != 'prevista'`.** La constraint és parcial justament
> per això. Però la contrapartida és dura i cal dir-la:
> **`open-task` no la trobarà mai** ([views_b.py:560](../../backend/fhort/tasks/views_b.py#L560):
> `filter(..., origen='prevista')`), i **`resolve_size_check` i `_close_pom_task_for_model`
> podrien tancar-la per accident** (§SORPRESA S-4).

## Q4.3 · `TaskType`: on viu, com es referencia, violacions de G9

**Camps** ([tasks/models.py:30-67](../../backend/fhort/tasks/models.py#L30-L67)):
`code` (SlugField(50), **unique**) · `name` · `default_order` · `active` · `fase` (6 choices) ·
`tipus` (`Interna`/`Externa-lliure`) · `eina` (slug, null) · `mode` (slug, null) · `facturable`.

**On viu: TENANT.** `to_regclass('public.tasks_tasktype')` → **NULL**. Les taules existeixen a
`fhort` i `los` i prou. Conseqüència directa per a F1: **crear `sample_check` i el flag
`es_lliurable` exigeix migració + sembra per tenant**, no una fila a `public`.

**⚠️ NO hi ha cap camp `es_lliurable`** ni res que s'hi assembli (`facturable` és una altra cosa:
mana sobre l'albarà, no sobre «és un lliurable»). La decisió RONDA el necessita → F1 el crea.

### ✅ **G9 (referència per slug): RESPECTADA al backend. ZERO violacions.**

`grep` de `task_type_id = <literal>`, `task_type=<literal>`, `TaskType.objects.get(pk=…)`,
`TaskType.objects.get(id=…)` sobre tot `backend/` → **0 coincidències**. Les 12 referències
productives són **totes** per `code`:

```
views_b.py:543  TaskType.objects.get(code=code, active=True)
views_b.py:1200 qs.filter(task_type__code=tt)
views_b.py:1253 TaskType.objects.get(code=code)
views_b.py:1283 TaskType.objects.filter(code=code).exists()
services_scheduling.py:25          filter(task_type__code=task_type_code)
services_size_check.py:282         filter(task_type__code='size_check')
models_app/views.py:1702           filter(task_type__code='pom')
models_app/views.py:2673           filter(task_type__code='grading')
models_app/serializers.py:278      filter(task_type__code='pom')
clone_model_for_qa.py:115          filter(code='size_check')
retype_scaling_to_grading.py:37-38 get(code='scaling') / get(code='grading')
```

**Zona grisa (no és violació, però convé saber-ho):** el contracte HTTP de
`POST models/<id>/define-tasks/` viatja **per id** (`{task_type_ids:[...]}`,
[endpoints.js:76](../../frontend/src/api/endpoints.js#L76)). Són ids **obtinguts en runtime** d'un
`GET` previ, no literals al codi — per tant no trenca G9, però és l'únic eix del sistema on un id
de `TaskType` creua la frontera. Al frontend els literals són **tots slugs**
(`'tech_sheet'`, `'pom'`, `'size_check'`, `'pattern_digit'`, `'grading'`).

---

# Q5 · ALBARÀ I MERITACIÓ, LA MECÀNICA EXACTA

## Q5.1 · Com lliga una línia d'albarà amb una `ModelTask`

**FK directa, no snapshot** —
[commerce/models.py:746-747](../../backend/fhort/commerce/models.py#L746-L747):

```python
model_task = models.ForeignKey('tasks.ModelTask', on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='delivery_note_lines')
```

Amb **quatre** punters de traçabilitat germans i tots nullable (`work_order`, `expense`,
`adjustment`, i `model` afegit a v2 [:764-765](../../backend/fhort/commerce/models.py#L764-L765)
«per compondre l'albarà agrupat per MODEL sense dependre de la cadena de FK»).

**Hi conviu un snapshot, però és de text i de temps, no d'identitat:** `description`
(`"{task_type.name} · {model.codi_intern}"`, [commerce/services.py:612](../../backend/fhort/commerce/services.py#L612))
i `internal_minutes` (Σ `TimerEntrada` sans, [:619-622](../../backend/fhort/commerce/services.py#L619-L622)),
que és **dada de lògica comercial fora del document** ([models.py:753-757](../../backend/fhort/commerce/models.py#L753-L757)).

⚠️ **`SET_NULL`, no `PROTECT`:** esborrar una `ModelTask` deixa la línia viva i **òrfena**, i el
guard d'albarà deixa de veure-la per sempre. (Contrast: `work_order` sí que és `PROTECT`.)

**Escriptura de la línia:** [commerce/services.py:596-603](../../backend/fhort/commerce/services.py#L596-L603)
(helper `_add` dins `generate_delivery_note`, [:527](../../backend/fhort/commerce/services.py#L527)).

**Estat viu a BD (`fhort`):** 2 albarans, 4 línies, **totes 4 amb `model_task_id`**.
`DeliveryNote 5 = ISSUED` (2 línies) · `DeliveryNote 10 = DRAFT` (2 línies).

## Q5.2 · El guard `tasca_albaranada` — ✅ verificat, ⚠️ àncora derivada

**C5-UI el situava a `services_c.py:199`. A HEAD és a
[services_c.py:205-213](../../backend/fhort/tasks/services_c.py#L205-L213):**

```python
if not force and frm == 'Done' and to_status == 'InProgress':
    if task.delivery_note_lines.filter(
            delivery_note__status__in=['ISSUED', 'INVOICED']).exists():
        raise TransitionError('No es pot reobrir una tasca ja albaranada (albarà emès).',
                              code='tasca_albaranada')
```

**Què mira EXACTAMENT** — quatre precisions que canvien el disseny de F1:

1. **Mira l'estat de l'ALBARÀ, no el de la línia.** `DeliveryNoteLine` **no té camp `status`**; el criteri és `delivery_note__status ∈ {ISSUED, INVOICED}`. Un `DRAFT` **no bloqueja** (documentat a [:202-204](../../backend/fhort/tasks/services_c.py#L202-L204): «encara es pot desfer esborrant el DRAFT»).
2. **Només dispara sobre `Done → InProgress`.** Qualsevol altra transició passa de llarg. Una tasca albaranada que arribés a `Paused` es podria reobrir sense tocar el guard.
3. **`force=True` el salta,** i és l'ÚNIC guard que `force` salta ([:192-193](../../backend/fhort/tasks/services_c.py#L192-L193)). Reservat al command de retipatge; cap porta d'usuari el passa.
4. **Les dues portes HTTP el retornen amb codis diferents:** `open-task` → **409** ([views_b.py:575-581](../../backend/fhort/tasks/views_b.py#L575-L581)); `transition/` → **400** ([views_b.py:460-464](../../backend/fhort/tasks/views_b.py#L460-L464)). El `code='tasca_albaranada'` viatja als dos (fix `fad10351`). → **SORPRESA S-2**.

**Cas viu a BD, reverificat avui:**

```
ModelTask 272 | model 188 | pattern_cad | Done | → DeliveryNoteLine → DeliveryNote 5 (ISSUED)
ModelTask 256 | model 188 | pom         | Done | → DeliveryNoteLine → DeliveryNote 5 (ISSUED)
```

**Són les dues úniques tasques tapiades de tot el tenant.** El cas de D-5 és real i acotat.

## Q5.3 · Meritació — el gallet i el que reancora

### On s'escriu

Tot dins de `transition_task`, **al bloc `if to_status == 'InProgress'`**
([services_c.py:251-283](../../backend/fhort/tasks/services_c.py#L251-L283)):

| Ordre | Efecte | Àncora HEAD |
|---|---|---|
| 1 | `Model.fase_actual: Pending → Dev` | [services_c.py:256](../../backend/fhort/tasks/services_c.py#L256) |
| 2 | **`ConsumptionRecord` + `consumption_started_at`** | [`_meritar_model`, services_c.py:123-139](../../backend/fhort/tasks/services_c.py#L123-L139) · [`_meritar_conjunt`, :142-183](../../backend/fhort/tasks/services_c.py#L142-L183) |
| 3 | **event `model_consumption_started` a `public`** | [`_emetre_meritacio`, services_c.py:106-120](../../backend/fhort/tasks/services_c.py#L106-L120) → [tasks/signals.py:15](../../backend/fhort/tasks/signals.py#L15) |
| 4 | `assign_work_order` (encàrrec) | [services_c.py:278-280](../../backend/fhort/tasks/services_c.py#L278-L280) → [:93-103](../../backend/fhort/tasks/services_c.py#L93-L103) |

**El gallet d'idempotència és un UPDATE condicional atòmic**, no un `if`:
`Model.objects.filter(pk=…, consumption_started_at__isnull=True).update(consumption_started_at=now)`
([services_c.py:127-130](../../backend/fhort/tasks/services_c.py#L127-L130)); la versió de conjunt
fa el mateix sobre `GarmentSet` ([:163-165](../../backend/fhort/tasks/services_c.py#L163-L165)).
**Un SET = 1 mèrit**, amb `code_snapshot = codi_base` ([:142-159](../../backend/fhort/tasks/services_c.py#L142-L159)).

Els blocs 2-4 van en **savepoints propis amb `except Exception: logger.exception` i sense
re-raise** ([:269-272](../../backend/fhort/tasks/services_c.py#L269-L272) i
[:281-283](../../backend/fhort/tasks/services_c.py#L281-L283)): **una meritació fallida no bloqueja
mai el tècnic**, i el forat el recull `reconcile_consumption`
([backoffice/management/commands/reconcile_consumption.py](../../backend/fhort/backoffice/management/commands/reconcile_consumption.py), criteri a [:68-76](../../backend/fhort/backoffice/management/commands/reconcile_consumption.py#L68-L76)).

### Què reancora del pla

Fora de `transition_task`, a la porta `open-task`
([views_b.py:591-602](../../backend/fhort/tasks/views_b.py#L591-L602)):

```python
if task.assignee_id:
    recompute_for_technicians([task.assignee_id])      # recalcula TOTA la cua del tècnic
    if started and not model.reanchored_by_start:      # `started` = aquesta crida va fer Pending→InProgress
        model.reanchored_by_start = True
        model.save(update_fields=['reanchored_by_start'])
```

I a la branca **claim** ([views_b.py:586-588](../../backend/fhort/tasks/views_b.py#L586-L588)):
`cleanup_queue_order` + `recompute_for_technicians` per als **dos** tècnics.

### 🔑 El mapa dels dos punts que F1 mourà

| Gallet | On és avui | Condició avui | Cap a on va (D-10) |
|---|---|---|---|
| **Meritació** | `services_c.py:261-273`, **dins** de `transition_task`, branca `to_status=='InProgress'` | *qualsevol* primera `→InProgress` (obrir una porta 3 s merita) | «1a **sessió amb batec**» → cal un senyal que avui **no arriba a `transition_task`** |
| **Gate d'albarà** | `commerce/services.py:610-611` i `:731-733` | `status='Done'` **ja hi és** | «només Done» → **ja hi és**; el que canvia és **què vol dir Done** (D-2) |

**Nota mecànica important:** els dos gallets viuen a **funcions diferents amb signatures
diferents**. `transition_task(task, to_status, profile, force, auto)` **no rep cap paràmetre
d'activitat**; el batec (`last_heartbeat`) viu al `TimerEntrada` i s'escriu des d'una acció HTTP
separada (§Q6). Moure la meritació a «1a sessió amb batec» vol dir **treure-la de
`transition_task`** o **passar-li un senyal nou**.

---

# Q6 · `TimerEntrada` I LA SESSIÓ

## Q6.1 · Estructura actual (8 columnes, verificat a BD)

[tasks/models.py:4-27](../../backend/fhort/tasks/models.py#L4-L27):

| Camp | Tipus | Null | Nota |
|---|---|---|---|
| `id` | bigint PK | NO | |
| `model_task` | FK → `ModelTask` **CASCADE**, `related_name='timers'` | NO | |
| `tecnic` | FK → `UserProfile` **PROTECT**, `related_name='timers'` | NO | **qui hi és de debò** |
| `inici` | timestamptz | NO | |
| `fi` | timestamptz | SÍ | `NULL` = tram obert |
| `minuts` | **PositiveIntegerField** | SÍ | `floor(segons/60)` |
| `actiu` | bool (default True) | NO | redundant amb `fi IS NULL` — **s'usen tots dos** |
| **`last_heartbeat`** | timestamptz | SÍ | **el batec que ja existeix** |

**Índexs/constraints:** només PK i els dos FK. **Cap unique, cap índex parcial.** La invariant «≤1
tram obert per tasca» és **només de codi** ([`_open_timer`, services_c.py:19-24](../../backend/fhort/tasks/services_c.py#L19-L24): tanca tots els oberts abans d'obrir). La BD no la imposa.

## Q6.2 · Com s'obre i es tanca dins de `transition_task`

| Moment | Codi | Àncora HEAD |
|---|---|---|
| **Obre** | `_close_open_timer(task)` **primer**, després `TimerEntrada.objects.create(model_task, tecnic=profile, inici=now, actiu=True)` | [services_c.py:19-24](../../backend/fhort/tasks/services_c.py#L19-L24), cridat a [:231](../../backend/fhort/tasks/services_c.py#L231) |
| **Tanca** | itera **TOTS** els oberts: `fi=now`, `minuts=max(0, int(Δs // 60))`, `actiu=False` | [services_c.py:27-35](../../backend/fhort/tasks/services_c.py#L27-L35), cridat a [:223](../../backend/fhort/tasks/services_c.py#L223) (exclusió) i [:239](../../backend/fhort/tasks/services_c.py#L239) (Paused/Done) |
| **Alimenta Welford** | `record_actual_time(task)` només a `Done` | [services_c.py:285-289](../../backend/fhort/tasks/services_c.py#L285-L289) → [services_i.py:47-75](../../backend/fhort/tasks/services_i.py#L47-L75) |

⚠️ **El tram s'ancora a `tecnic=profile` (qui executa); l'exclusió mira `assignee`**
([services_c.py:220](../../backend/fhort/tasks/services_c.py#L220)) i l'`assignee` **només s'escriu
si és `None`** ([:244-245](../../backend/fhort/tasks/services_c.py#L244-L245)). Els dos eixos
divergeixen — és F-7 de la diagnosi anterior, i **segueix intacte a HEAD**.

## Q6.3 · El batec que ja existeix

**`last_heartbeat` té una única porta d'escriptura:** l'acció
[`heartbeat`, tasks/views.py:59-83](../../backend/fhort/tasks/views.py#L59-L83)
(`POST /api/v1/timers/heartbeat/`, **sense pk** — el tram es busca pel perfil):

```python
timer = (self.get_queryset()
         .filter(fi__isnull=True, actiu=True, model_task__status='InProgress')
         .order_by('-inici').first())
if timer is None: return 404
timer.last_heartbeat = timezone.now()
timer.save(update_fields=['last_heartbeat'])
```

El serializer el té a `read_only_fields` ([serializers.py:16](../../backend/fhort/tasks/serializers.py#L16))
i el viewset ja és `ReadOnlyModelViewSet` (commit `89009858`,
[views.py:15](../../backend/fhort/tasks/views.py#L15)). **La superfície és neta.**

**Qui hi truca avui:** només el guard del client, en **confirmar el modal**
([GuardTascaOblidada.jsx](../../frontend/src/components/GuardTascaOblidada.jsx), llindars de
producció 30/3 a [:55-56](../../frontend/src/components/GuardTascaOblidada.jsx#L55-L56), override
d'un sol ús a [:60-61](../../frontend/src/components/GuardTascaOblidada.jsx#L60-L61)). **No hi truca
cap escriptura de dades.** El batec d'avui és *«sóc davant de la pantalla»*, no *«he escrit»*.

**🔑 El codi ja anticipa D-2 i ho diu literalment** ([tasks/models.py:15-16](../../backend/fhort/tasks/models.py#L15-L16)):

> *«GANXO F-MÀ (no construït): aquest és el senyal que alimentarà `last_activity_at` del TTL de la
> mà. Qui escrigui aquí haurà d'escriure els dos alhora, no inventar-se un segon batec.»*

I la mateixa advertència, repetida, a [tasks/views.py:78-79](../../backend/fhort/tasks/views.py#L78-L79).

## Q6.4 · Què permet l'esquema actual (mecànica, sense disseny)

**Sense cap migració:**
- **(a)** Sessió = **el tram obert**; batec = `last_heartbeat` d'aquest tram. Ja hi és sencer. Límit: el tram **mor a cada `Paused` i a cada `Done`** ([services_c.py:239](../../backend/fhort/tasks/services_c.py#L239)) — una sessió que hagi de sobreviure a una pausa no cap aquí.
- **(b)** Sessió = **la finestra `InProgress` de la `ModelTask`**; batec = `last_heartbeat` del seu tram obert. Mateix cost, mateix límit (`started_at` es conserva a la reobertura, `finished_at` es neteja: [services_c.py:232-236](../../backend/fhort/tasks/services_c.py#L232-L236)).
- **(c)** «Merita la 1a sessió amb batec» = `EXISTS(timers WHERE last_heartbeat IS NOT NULL)`. **Consultable avui**, sense esquema nou.

**Amb migració mínima (1 columna):**
- **(d)** `TimerEntrada.sessio` (FK nullable a una entitat nova) — permet que N trams formin **una** sessió i que la sessió sobrevisqui a pauses.
- **(e)** `TimerEntrada.motiu`/`origen` (varchar) — permetria distingir tram de treball / tram de handoff / tram de ronda **sense entitat nova**. Avui **no existeix**: el `TimerEntrada` no sap **per què** existeix.

**Límits durs de l'esquema, els digui qui els digui:**
- `minuts` és **PositiveIntegerField** i es calcula amb `// 60`: **una sessió de < 60 s val 0**, i el 0 no és distingible de «sense dada».
- `_close_open_timer` **no marca** per què tanca (ni `auto`, ni motiu): el `TaskTransition` sí que porta `auto` ([models.py:146-148](../../backend/fhort/tasks/models.py#L146-L148)), **el timer no**.
- **Cap índex impedeix dos trams oberts alhora** per tècnic ni per tasca.

## Q6.5 · ✅ L'anomalia de l'acció «tancar», verificada

**Àncora exacta a HEAD: [tasks/views.py:85-98](../../backend/fhort/tasks/views.py#L85-L98)**
(`POST /api/v1/timers/<pk>/tancar/`, router a [tasks/urls.py:6](../../backend/fhort/tasks/urls.py#L6)):

```python
@action(detail=True, methods=['post'], url_path='tancar')
def tancar(self, request, pk=None):
    timer = self.get_object()
    if timer.fi is not None: raise ValidationError('El timer ja està tancat.')
    now = timezone.now()
    timer.fi = now
    timer.minuts = max(0, int((now - timer.inici).total_seconds() // 60))
    timer.actiu = False
    timer.save(update_fields=['fi', 'minuts', 'actiu'])
```

**Confirmat:** cap `transition_task`, cap `TaskTransition`, cap `record_actual_time`, cap toc a
`ModelTask.status`. **La tasca queda `InProgress` sense tram obert** — l'anomalia «òrfena» que el
cron compta i no toca.

⚠️ **Sobreviu al fix `89009858`.** Passar el viewset a `ReadOnlyModelViewSet` va tancar
`POST/PUT/PATCH/DELETE` del router, però **les `@action` no en depenen**: `tancar` segueix sent una
escriptura pública amb només `IsAuthenticated`.

**Consumidor: un i prou** — [TimeTracking.jsx:43-53](../../frontend/src/pages/TimeTracking.jsx#L43-L53)
(`closeActive`), ruta `/temps` ([App.jsx:394](../../frontend/src/App.jsx#L394)). I aquest consumidor
**està trencat de dalt a baix** → **SORPRESA S-3**.

---

# SORPRESES

> Contradiccions amb les 10 decisions o amb els documents font. **No resoltes a posta** — anotades
> perquè les decideixi qui toca.

---

### 🚨 S-1 · Hi ha una escriptura de tècnic que **no pot saber de quin model és**

**`POST item-fitxers/<item_id>/pom-placements/`**
([pom_placement_views.py:116-150](../../backend/fhort/models_app/pom_placement_views.py#L116-L150))
desa la col·locació d'una cota. El tècnic la fa **des de l'editor de fitxa d'un model**, però la
fila que escriu (`POMPlacement`) penja de l'`ItemFitxer` del **catàleg** i **no té camp `model`**
([models_app/models.py:1418-1420](../../backend/fhort/models_app/models.py#L1418-L1420)). El `GET`
accepta `?model_id=`; el `POST` **ni el llegeix ni el podria desar**.

**Contradiu D-1** («transició automàtica de sessió» a partir de l'escriptura): per a aquesta
superfície **no hi ha `model_id` a cap banda del request**. El batec l'hauria de fer el frontend, o
aquest gest queda fora de la sessió. (Germà menor: `POST fitting-photos/`, que va per
`session`/`piece_fitting`.)

---

### 🚨 S-2 · El mateix rebuig d'albarà surt amb **dos codis HTTP diferents**

- `open-task` → **409 CONFLICT** ([views_b.py:575-581](../../backend/fhort/tasks/views_b.py#L575-L581))
- `transition/` → **400 BAD REQUEST** ([views_b.py:460-464](../../backend/fhort/tasks/views_b.py#L460-L464))

Els dos porten `code='tasca_albaranada'`, però un client que discrimini per **status** (i n'hi ha:
`SessionActions.jsx:35` mira `data.code`, però `ModelSheet` i `WorkPlan` miren
`err.response.status`) veurà dues coses diferents per a la mateixa paret. **D-5 crea una tasca nova
per FK quan es topa amb aquesta paret** — el disparador ha de ser fiable, i avui depèn de per quina
porta hagi entrat.

---

### 🚨 S-3 · La pàgina `/temps` **no llegeix cap camp que el servidor emeti**

[TimeTracking.jsx](../../frontend/src/pages/TimeTracking.jsx) llegeix `t.data_inici`, `t.data_fi` i
`t.created_at`. El serializer és `fields='__all__'` sobre `TimerEntrada`
([serializers.py:10-16](../../backend/fhort/tasks/serializers.py#L10-L16)), i els camps reals són
**`inici`, `fi`** — verificat a `information_schema`: **`created_at` no existeix** a la taula.

Conseqüències mecàniques, totes verificables:

| Línia | Codi | Efecte real |
|---|---|---|
| [:27](../../frontend/src/pages/TimeTracking.jsx#L27) | `ordering: '-data_inici'` | camp fora d'`ordering_fields` ([views.py:39](../../backend/fhort/tasks/views.py#L39)) → DRF l'ignora, cau al default |
| [:36](../../frontend/src/pages/TimeTracking.jsx#L36) | `find(t => t.actiu \|\| !t.data_fi)` | `!undefined === true` → **agafa el PRIMER tram de la llista, obert o no** |
| [:39-40](../../frontend/src/pages/TimeTracking.jsx#L39-L40) | `(t.data_inici \|\| t.created_at \|\| '')` → `'' === today` | **la llista del dia és SEMPRE buida** |
| [:60-64](../../frontend/src/pages/TimeTracking.jsx#L60-L64) | mateix patró | **el gràfic de 7 dies és SEMPRE 0** |

I el botó «tancar» (§Q6.5) **crida `tancar` sobre el tram que aquesta `find` retorni** — que
normalment ja està tancat → `400 'El timer ja està tancat.'`.

**Per què importa a F1:** l'informe presentava `tancar` com *«l'acció viva de la pàgina de temps»*.
**A la pràctica la pàgina no funciona**, i decidir si es manté, s'arregla o es jubila l'endpoint és
una decisió diferent de la que semblava.

---

### 🚨 S-4 · La tasca de RONDA **serà invisible per a `open-task` i esborrable per accident**

La constraint parcial permet la segona tasca del mateix tipus (§Q4.2) — però tres punts del codi
resolen «la tasca del model» **sense mirar `origen`**, i cadascun tria una fila diferent:

| Punt | Criteri | Quina agafa amb 2 tasques `pom`/`size_check` |
|---|---|---|
| [views_b.py:560](../../backend/fhort/tasks/views_b.py#L560) (`open-task`) | `origen='prevista'` | **sempre la prevista** → la de ronda **no s'obre mai per aquí** |
| [models_app/views.py:1701-1703](../../backend/fhort/models_app/views.py#L1701-L1703) (`_close_pom_task_for_model`) | `task_type__code='pom'`, **`order_by('id').first()`** | **la MÉS ANTIGA** → «Gravar POM» de la ronda 2 tancaria **la ronda 1** |
| [services_size_check.py:281-283](../../backend/fhort/models_app/services_size_check.py#L281-L283) | `task_type__code='size_check'`, `.exclude(status='Done').order_by('-id').first()` | **la MÉS NOVA no-Done** → criteri **oposat** al de dalt |

Dos resolutors de «la tasca del model» amb **ordre invers**, i cap dels dos filtra per `origen` ni
per `fitting_session`. **D-3 («una tasca = una mostra») i la RONDA («model·seq·motiu») exigeixen
unificar aquest criteri abans de crear la segona tasca**, o la ronda 2 corromprà la ronda 1.

---

### ⚠️ S-5 · `resolve_size_check` **s'empassa el guard d'albarà en silenci**

El tancament de la tasca viu dins d'un `try/except Exception` amb `logger.warning`
([services_size_check.py:278-290](../../backend/fhort/models_app/services_size_check.py#L278-L290)),
i el `resolve` **retorna èxit igualment** amb `tasca_finalitzada: False`.

Sobre una tasca albaranada, el `TransitionError('tasca_albaranada')` **mai arriba a l'usuari**: el
check es grava, la base es consolida, i la tasca queda viva sense que ningú ho sàpiga. El fix
`fad10351` (que el 409 digui la paret) **no cobreix aquest camí**. Germà: `SessionActions.jsx:44`
fa `catch { /* no-op */ }` amb el mateix efecte.

---

### ⚠️ S-6 · El `docstring` de `resolve_size_check` promet un `status` que ningú no escriu

[services_size_check.py:165-167](../../backend/fhort/models_app/services_size_check.py#L165-L167)
diu que el reagendament fixa *«planned_start/end (calendari laboral) + planned_locked, **status
Pending**»*. `reagenda_tasca`
([services_scheduling.py:33-36](../../backend/fhort/tasks/services_scheduling.py#L33-L36)) escriu
`update_fields=['planned_start','planned_end','planned_locked','updated_at']` — **`status` no hi
és**. Una tasca `Paused` reagendada **queda `Paused`**.

---

### ⚠️ S-7 · L'extracció «perquè la convocatòria el pugui reusar» **no té el segon consumidor**

`reagenda_tasca` es va extreure i parametritzar per `task_type_code`
([services_scheduling.py:3-7](../../backend/fhort/tasks/services_scheduling.py#L3-L7): *«perquè la
convocatòria (contenidor) el pugui reusar»*). **`grep` a tot el backend: un sol caller**, i és el
d'origen ([services_size_check.py:296](../../backend/fhort/models_app/services_size_check.py#L296)),
que hi passa `'size_check'` — el valor per defecte. El punt d'extensió de la convocatòria **existeix
i està buit**.

---

### ⚠️ S-8 · Un `TaskType` fantasma al capdavant de totes les llistes

**`patronatge`** (name «Patronatge») viu **només a `fhort`**, amb `default_order = 0` — o sigui
**primer de tota llista ordenada** ([models.py:62](../../backend/fhort/tasks/models.py#L62):
`ordering = ['default_order','code']`). No té `eina`, no té `mode`, **0 `ModelTask`**, i **cap
sembra del codi el crea** (`grep patronatge` sobre `backend/fhort/`: només comentaris de
`patterns/`). `los` no el té: **els dos tenants divergeixen en el catàleg canònic** que
[models.py:31-32](../../backend/fhort/tasks/models.py#L31-L32) declara *«propietat del sistema; el
tenant no l'edita»*.

---

### 🔵 S-9 · D-10 arriba amb mig terreny ja fet, i mig sense

- **«albarà només Done»** → ✅ **ja hi és**: `generate_delivery_note` i el preview ja filtren `status='Done'` ([commerce/services.py:611](../../backend/fhort/commerce/services.py#L611), [:732](../../backend/fhort/commerce/services.py#L732)). No cal tocar res; el que canvia és **el significat de Done** (D-2).
- **«merita la 1a sessió amb batec»** → 🔴 **no hi és**: la meritació viu **dins** de `transition_task` ([services_c.py:261-273](../../backend/fhort/tasks/services_c.py#L261-L273)) i `transition_task` **no rep cap senyal d'activitat**. El batec (`last_heartbeat`) viu al `TimerEntrada` i s'escriu des d'una acció HTTP separada. **Cal treure la meritació d'allà o passar-li un senyal nou** — no és un canvi de condició, és un canvi de lloc.
- ⚠️ I `reconcile_consumption` **merita pel criteri VELL** («hi ha activitat de tasca en `InProgress`/`Done`/`Paused`», [reconcile_consumption.py:68-76](../../backend/fhort/backoffice/management/commands/reconcile_consumption.py#L68-L76)). Si F1 canvia el gallet i no toca el reconcile, **el reconcile tornarà a meritar el que el gallet nou hagi decidit no meritar**.

---

### 🔵 S-10 · L'obertura de sessió de fitting és **idempotent només per accident**

[ModelSheet.jsx:337-351](../../frontend/src/pages/ModelSheet.jsx#L337-L351) protegeix la
materialització amb un `useRef` de mòdul-component (`autoSessionRef`). És **estat de client**: dues
pestanyes amb la mateixa URL `?fitting_session=` fan **dos `open-task`**. El backend és idempotent
en la creació de la tasca, però **cada crida dispara `recompute_for_technicians`**
([views_b.py:596](../../backend/fhort/tasks/views_b.py#L596)) i, si la sessió és `Programada`,
`open_session` ([:622-623](../../backend/fhort/tasks/views_b.py#L622-L623)) — que **llança
`ValueError` si ja no ho és**, fora de tot `try`. És el mateix patró de F-10 (doble `open-task`)
amb una branca que pot petar.

---

## APÈNDIX · Consultes SQL usades (totes `SELECT`, cap escriptura)

```sql
-- schemes vius
SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname <> 'information_schema';
--   fhort · los · public

-- TaskType per schema (public → to_regclass NULL)
SELECT to_regclass('public.tasks_tasktype');                                    -- NULL
SELECT code, name, fase, tipus, eina, mode, facturable, active, default_order
  FROM fhort.tasks_tasktype ORDER BY default_order, code;                       -- 15
SELECT ... FROM los.tasks_tasktype ORDER BY default_order, code;                -- 14 (sense `patronatge`)

-- estructura i constraints de ModelTask
SELECT column_name, data_type, is_nullable FROM information_schema.columns
 WHERE table_schema='fhort' AND table_name='tasks_modeltask';                   -- 18 columnes
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
 WHERE conrelid='fhort.tasks_modeltask'::regclass;                              -- 5 FK, cap self-FK
SELECT schemaname, indexname, indexdef FROM pg_indexes WHERE tablename='tasks_modeltask';
--   uniq_prevista_model_tasktype: UNIQUE (model_id, task_type_id) WHERE origen='prevista' · fhort i los

-- violacions vives de la constraint parcial
SELECT model_id, task_type_id, count(*) FROM fhort.tasks_modeltask
 WHERE origen='prevista' GROUP BY 1,2 HAVING count(*)>1;                        -- 0 files

-- distribució d'origen i estat
SELECT origen, status, count(*) FROM fhort.tasks_modeltask GROUP BY 1,2;
--   prevista/Done 10 · prevista/Paused 36 · prevista/Pending 55 · ad_hoc: CAP

-- ús per TaskType
SELECT tt.code, count(mt.id) FROM fhort.tasks_tasktype tt
  LEFT JOIN fhort.tasks_modeltask mt ON mt.task_type_id=tt.id GROUP BY 1;
SELECT count(*) FROM los.tasks_modeltask;                                       -- 0

-- TimerEntrada
SELECT column_name, data_type, is_nullable FROM information_schema.columns
 WHERE table_schema='fhort' AND table_name='tasks_timerentrada';                -- 8 col., cap created_at

-- albarà ↔ tasca
SELECT dn.id, dn.status, count(l.id), count(l.model_task_id)
  FROM fhort.commerce_deliverynote dn
  LEFT JOIN fhort.commerce_deliverynoteline l ON l.delivery_note_id=dn.id GROUP BY 1,2;
--   5 ISSUED 2/2 · 10 DRAFT 2/2

-- tasques tapiades pel guard (D-5)
SELECT mt.id, mt.model_id, tt.code, mt.status, dn.id, dn.status
  FROM fhort.tasks_modeltask mt
  JOIN fhort.tasks_tasktype tt ON tt.id=mt.task_type_id
  JOIN fhort.commerce_deliverynoteline l ON l.model_task_id=mt.id
  JOIN fhort.commerce_deliverynote dn ON dn.id=l.delivery_note_id
 WHERE dn.status IN ('ISSUED','INVOICED');
--   272/188/pattern_cad · 256/188/pom  → DeliveryNote 5 ISSUED

-- pont fitting ↔ tasca
SELECT count(*) FILTER (WHERE fitting_session_id IS NOT NULL), count(*) FROM fhort.tasks_modeltask;
--   1 de 101
SELECT estat, count(*) FROM fhort.fitting_fittingsession GROUP BY 1;
--   Programada 17 · Oberta 3 · Tancada 5
```

---

*Patró A · read-only · cap fitxer del projecte tocat fora d'aquest document · cap escriptura a BD ·
cap migració generada. Àncores verificades a HEAD `1f07faaa`.*
