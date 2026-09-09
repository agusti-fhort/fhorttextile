# CENS DE RONDES — tots els nodes que el tram tocaria

> **Patró A · READ-ONLY ABSOLUT.** Cap fitxer de producte tocat, cap migració, cap escriptura a
> BD, cap test executat. L'únic fitxer escrit és aquest report.
> **NO DECIDEIX RES.** Tot el que és lectura de disseny viu a §D, al final, separat dels fets.

---

## 0 · CAPÇAL — estat del repo i de la màquina

| Fet | Valor |
|---|---|
| Entorn | `178.105.48.204` · `/var/www/ftt-staging` · branca **`dev`** · schema **`fhort`** |
| HEAD | `5306df7e5dd2cfc04eb1aaebc88a2c6dce32b259` |
| `git log -1` | Agusti Fhort · **Sun Aug 23 14:53:25 2026 +0000** · `fix(pom): /api/schema/ tornava 500 — name_es declarat i fora de fields` |
| Canvis sense commitar | **133 entrades** a `git status --porcelain` (4 modificats + 129 untracked). Cap és una migració ni un `.py` sota `backend/fhort/`. Modificats: `DECISIONS.md`, `docs/ordres/IMPLEMENTACIO_SOBIRANIA_POM_2026-08-22.md`, `ops/maquetes/REPORT_CODA_BLOC_B.md`, `ops/qa/qa_f22_vocabulari_captures.py`. La resta són `.md`/`.csv`/`backend/scripts_tmp/` untracked. |
| Migracions sense commitar | **cap** (`git status \| grep migration` → buit) |
| Cua de migracions | **BUIDA** a `tasks`, `models_app`, `fitting`, `planning`, `commerce`, `pom`: cap fitxer de migració al disc sense fila a `django_migrations`. |
| `ftt-staging.service` | **active running**, MainPID 3692893, `ActiveEnterTimestamp = 2026-08-23 14:52:47 UTC` |
| `frontend/dist/index.html` | mtime **2026-08-23 12:42** |
| Càrrega | `load average: 0.06` — **cap suite en marxa** |

🚨 **DIVERGÈNCIA DESPLEGAT↔DISC (viva ara mateix).** El gunicorn va arrencar a les **14:52:47** i
el HEAD és de les **14:53:25**: el procés servit és **38 s més vell que HEAD**. I `frontend/dist`
és de les **12:42**, anterior a HEAD. Qualsevol QA per HTTP contra staging avui mesura codi
anterior a HEAD, backend i front. *(Fet, no proposta: no s'ha reiniciat res.)*

**Processos aliens vius** (no els he tocat): `manage.py runserver 127.0.0.1:8099` (PID 1402071,
des del 04/08) i `qa_serve.py` (PID 1362939, des del 04/08), tots dos restes de sessions
anteriors. Zones intocables (`/var/www/assessment`, `/trading`, `/webs`) amb els seus gunicorn
propis, no tocades.

### Foto de BD

Tota la lectura de BD s'ha fet dins **UNA** transacció
`BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` amb `ROLLBACK` final.

**Barana provada sobre una FILA QUE EXISTEIX:**

```
fila_diana | id 362 | status Paused          ← existeix
SAVEPOINT barana;
UPDATE tasks_modeltask SET status = status WHERE id = (SELECT min(id) FROM tasks_modeltask);
ERROR: cannot execute UPDATE in a read-only transaction     ← barana ACTIVA
ROLLBACK TO SAVEPOINT barana;
```

`txid_current_if_assigned() IS NULL = true` al final → **cap escriptura assignada**.
Foto: `2026-08-23 17:18:34 UTC`.

---

## 0-bis · 🚨 DIVERGÈNCIES AMB ELS ANCORATGES DEL BRIEF

Aquest bloc va primer perquè **canvia la premissa del tram sencer**.

### D-0 · LA RONDA JA ESTÀ CONSTRUÏDA

El brief diu «Una RONDA és el cicle encàrrec→entrega d'un model. […] **NO ho construeixes ara**».
El cens ha trobat que **la meitat de baix ja hi és, construïda, provada i amb porta HTTP**:

| Peça | On és | Estat |
|---|---|---|
| Model `Ronda` (`model`, `seq`, `motiu`, `oberta_el`, `tancada_el`) | `backend/fhort/tasks/models.py:132-177` | ✅ a BD (`fhort.tasks_ronda`), migració aplicada |
| `ModelTask.ronda` / `.mare` / `.motiu` (genealogia) | `backend/fhort/tasks/models.py:223-234` | ✅ |
| Resolutor únic `tasca_vigent` | `backend/fhort/tasks/services_r.py:46` | ✅ |
| `obrir_ronda` · `obrir_correccio` · `tancar_ronda` | `backend/fhort/tasks/services_r.py:88,148,203` | ✅ |
| `ronda_lliurable` · `rondes_lliurables` | `backend/fhort/tasks/services_r.py:213,229` | ✅ |
| `TaskType.es_lliurable` | `backend/fhort/tasks/models.py:118-122` | ✅ (5 de 15 tipus) |
| Porta HTTP `POST /api/v1/models/<id>/obrir-ronda/` | `backend/fhort/tasks/views_b.py:1692` + `tasks/urls.py:71` | ✅ |
| Contracte al serializer (`ronda`, `ronda_seq`, `mare`, `motiu`, `es_vigent`, `albaranada`, `es_lliurable`) | `backend/fhort/tasks/serializers_b.py:23-88` | ✅ |
| `Model.ronda_oberta` i `Model.lliurable_ronda_n` (detall i llista) | `backend/fhort/models_app/serializers.py:131,275,278,297,303` | ✅ |
| UI: `caraObrirTasca` (4 cares, una és LLIURADA→ronda) | `frontend/src/utils/caraObrirTasca.js:36` | ✅ |
| UI: `ObrirTascaDialog` amb opcions «Obrir ronda N» / «És una correcció» | `frontend/src/components/model/ObrirTascaDialog.jsx:31,61` | ✅ |
| UI: `BadgeLliurable` a fitxa i llista | `frontend/src/components/model/BadgeLliurable.jsx:15`; usat a `ModelSheet.jsx:1841` i `Models.jsx:340` | ✅ |
| i18n `obrir_tasca.lliurada_*` i `lliurable.*` | `ca/en/es` amb **paritat total** (4705 claus a cada idioma) | ✅ |
| Tests | `tasks/test_ronda.py` (29 tests), `tasks/test_tasca_vigent.py` (7), `tasks/test_contracte_f2.py` (14) | ✅ |

**El que NO hi és:** l'**ENTREGA** com a acte datat amb destinatari i contingut, i el **SEGELL**
de les tasques d'una ronda entregada. Avui la «volta lliurada» es DEDUEIX
(`ronda_lliurable` = totes les tasques `es_lliurable` a `Done`), no es DECLARA. No hi ha cap
model `Entrega`, cap camp de destinatari, cap acte. El que més s'hi assembla és
`commerce.DeliveryNote` (albarà comercial) i el guard `te_paret_albara`.

### D-1 · Fitxers citats al brief que NO existeixen amb aquell nom

| Al brief | A l'arbre real | Nota |
|---|---|---|
| `models_app/views.py :: _close_pom_task_for_model` | **`_assegura_pom_task_oberta`**, `backend/fhort/models_app/views.py:1946` | Renombrada a F1.2. **Ja no tanca**: assegura que la tasca està OBERTA. El comentari intern cita el §S-4 del brief com a defecte JA TANCAT (`tasca_vigent`, línia 1966). **ATURADA aplicada:** no he buscat cap altre equivalent; aquest és el mateix cos amb nom nou i el codi ho documenta explícitament. |
| `_reagenda_tasca_size_check` (a `services_size_check`) | **`reagenda_tasca(model, data_represa, task_type_code)`**, `backend/fhort/tasks/services_scheduling.py:15` | Extret i parametritzat a l'Sprint Y. `services_size_check.py:324-326` deixa la nota de la mudança. |
| `frontend/src/pages/WorkPlan.jsx` | `frontend/src/components/model/WorkPlan.jsx` (426 línies) | només canvia la ruta |
| `frontend/src/components/TaskTree.jsx` | `frontend/src/components/model/TaskTree.jsx` (262 línies) | només canvia la ruta |
| `frontend/src/components/SessionActions.jsx` | `frontend/src/components/model/SessionActions.jsx` (125 línies) | només canvia la ruta |
| `Contracte`/`LiniaContracte` «schema public, backoffice» | **`fhort.models_app_contracte` / `fhort.models_app_liniacontracte`** (schema **TENANT**), models a `backend/fhort/models_app/models.py:14,29` | A `public` hi ha `backoffice_tenantcontract` i `backoffice_contractline`, que són el contracte **SaaS FHORT↔tenant** (`backoffice/models.py:237`), una altra cosa. |
| «el grup de fitting s'emet com a `all_day` **multi-dia**» | **JA NO.** `planning/views.py:450-465` emet **un marcador per sessió REAL, al seu propi dia** (`start == end`), per G7 Bloc 4/4b. El comentari de :455-459 explica que abans sí que replicava el rang. | El front (`inRange`) encara SAP replicar per rang, però avui rep sempre `start==end`. |

`ModelSheet.jsx`, `TechSheetEntry.jsx`, `TallerPatro.jsx`, `tasks/models.py`, `tasks/views_b.py`,
`models_app/services_size_check.py`, `planning/plan_service.py`, `tasks/services_c.py`
**existeixen tots** amb el nom citat.

---

## R1 · IDENTITAT DE `ModelTask` — el node central

### La unicitat, com és avui

`backend/fhort/tasks/models.py:242-249`:

```python
constraints = [
    models.UniqueConstraint(
        fields=['model', 'task_type'],
        condition=models.Q(origen='prevista'),
        name='uniq_prevista_model_tasktype'),
]
```

🔑 **La unicitat ÉS JA PARCIAL.** Només val per a `origen='prevista'`. Les tasques `ad_hoc`
(extres B4a, rondes F1.1, correccions S-20) poden repetir `(model, task_type)` **des d'avui**.
`ordering = ['model', 'order']` (`:236`). **Cap `models.Index` declarat** a `ModelTask`.

### Taula de nodes

Convenció de la columna EXTENSIÓ: què li caldria per viure amb `(model, task_type, ronda)`.

| NODE · fitxer:línia | Què fa | QUI EL LLEGEIX | QUI L'ESCRIU | EXTENSIÓ | TESTS (R13) | VEREDICTE |
|---|---|---|---|---|---|---|
| `tasks/models.py:242` `uniq_prevista_model_tasktype` | unicitat parcial `(model, task_type)` WHERE `origen='prevista'` | l'ORM i les tres portes de creació | migració | **Res.** Ja tolera N tasques per `(model, task_type)`. Afegir-hi `ronda` la faria MÉS estricta i trencaria les correccions (que hereten `ronda` de la mare i conviuen amb ella dins la mateixa volta) | `tasks/test_ronda.py:88-95`, `test_contracte_f2.py` | **ES LLEGEIX** |
| `tasks/models.py:223-234` `ronda`/`mare`/`motiu` | genealogia; `ronda=NULL` = volta 1 implícita | `tasca_vigent`, `ModelTaskSerializer`, `rondes_lliurables` | `obrir_ronda`, `obrir_correccio` (mai el client: read-only al serializer, `serializers_b.py:88`) | ja hi és | `test_ronda.py`, `test_contracte_f2.py:69-89` | **ES LLEGEIX** |
| `tasks/services_r.py:46` `tasca_vigent(model, code, *, ronda=None)` | **EL RESOLUTOR ÚNIC**. 4 regles: ronda oberta > base+correccions · viva > Done · correcció més recent > mare · desempat `id` | 8 punts (sota) | — | ja parla de rondes. Si l'entrega segella, hi cal el filtre «no la d'una ronda entregada» **o** el segell ha de deixar les tasques `Done` i que la regla 3 les descarti sola | `tasks/test_tasca_vigent.py` (7), `test_ronda.py` (29) | **ES TOCA** |
| `tasks/services_r.py:35` `_ronda_oberta` | `Ronda` amb `tancada_el IS NULL`, `-seq` | `tasca_vigent`, `obrir_ronda`, `ModelSerializer.get_ronda_oberta` | — | «oberta» hauria de passar a «oberta **i no entregada**» si l'entrega no tanca la ronda | `test_ronda.py:171-179` | **ES TOCA** |
| `tasks/views_b.py:576` `open_model_task_view` | crea-si-falta + En curs; resol per `tasca_vigent` | front (`endpoints.js:100`) | crea `ModelTask` `origen='prevista'` | si la vigent és d'una ronda **entregada**, ha de refusar amb codi propi (avui només té `tasca_feta` i `tasca_albaranada`) | `tasks/test_j_consulta_treball.py` (25) | **ES TOCA** |
| `tasks/views_b.py:325` `define_model_tasks_view` | bulk crea `prevista`; idempotència per `(model_id, task_type_id, origen='prevista')` (`:340`) | front (`endpoints.js:92`) | `ModelTask` | **assumeix que «ja existeix» = la prevista.** Amb rondes segueix sent correcte (les de ronda són `ad_hoc`), però no sap res de rondes | `tasks/tests.py` (parcial) | **ES LLEGEIX** |
| `tasks/views_b.py:106` `by_model` | agrega per model; `Count` per estat sobre TOTES les tasques | Dashboard board | — | **compta el pla sencer**: amb N rondes, `done` i `pending` sumen totes les voltes. Cal partir per ronda o filtrar a la vigent | **CAP TEST** | **ES TOCA** |
| `tasks/views_b.py:479` `claim_task_view` | claim per `pk` directe (no `tasca_vigent`) | front | `assignee` + `traspassa_tram` | opera per pk: indiferent a la ronda | `tasks/test_exclusio_handoff.py` (13) | **NO ES TOCA** |
| `tasks/views_b.py:430` `transition_task_view` | transició per `pk` | front | via `transition_task` | punt on cauria la guarda «tasca de ronda entregada = intocable» (v. R2) | `test_stop_encadenat.py`, `test_j_consulta_treball.py` | **ES TOCA** |
| `tasks/views_b.py:361` `model_task_log_view` | log de `TaskTransition` del MODEL (totes les tasques, 300 files) | Registre d'activitat del ModelSheet | — | no diu de quina ronda és cada fila (`ModelTask.ronda` no viatja al payload) | **CAP TEST** | **ES TOCA** |
| `tasks/serializers_b.py:98` `get_es_vigent` | delega a `tasca_vigent` (no reimplementa) | UI | — | segueix sol el resolutor | `test_contracte_f2.py` | **ES LLEGEIX** |
| `models_app/views.py:1946` `_assegura_pom_task_oberta` | desar POM obre-si-cal; resol per `tasca_vigent` (`:1966`) | `gravar_pom_view` | `transition_task` | si la vigent és d'una ronda entregada → nou `reason` | `models_app/test_gate_mesures_pom_task.py` (9) | **ES TOCA** |
| `models_app/services_size_check.py:301` (crida) | reagenda per `reagenda_tasca` | — | `planned_*` | v. R7 §col·lisió ③ | `models_app/test_size_check_completa_linies.py` (8) | **ES LLEGEIX** |
| `tasks/services_scheduling.py:15` `reagenda_tasca` | fixa la tasca viva de `code` al calendari; passa per `tasca_vigent` (`:33`) | `resolve_size_check` | `planned_start/end/locked` | ja resol per ronda | **CAP TEST** | **ES LLEGEIX** |
| `tasks/services_batec.py:108` `batec_escriptura` | resol per `tasca_vigent`; bat la vigent | 18 punts d'escriptura | `TimerEntrada`, `transition_task` | una escriptura sobre una ronda entregada ha de topar com topa amb l'albarà (`:128`) | `test_batec_escriptura.py` (8), `test_batec_sobre_pausada.py` (6) | **ES TOCA** |
| `planning/plan_service.py:42` `_technician_queue` | cua = `ModelTask` no-Done de l'assignee | `recompute_for_technicians` | — | **no coneix la ronda**: la cua barreja voltes | `tasks/tests.py:174-258` | **ES LLEGEIX** |
| `planning/plan_service.py:197` `assign_model` | assigna TOTES les no-Done del model (o `task_ids`) | `assign_model_view` | `assignee`, `planned_*` | assignaria també les de voltes velles vives | `tasks/tests.py` | **ES TOCA** |
| `planning/plan_service.py:237` `assign_batch` | wizard multi-assign per `task_type_code` | `plan_assign_batch_view` | `assignee`, `planned_*` | **resol la tasca del model per `task_type_code`**: cal decidir quina volta | — | **ES TOCA** |
| `planning/plan_service.py:440` `unassign_model` · `:81` `cleanup_queue_order` · `:421` `cleanup_after_pending_delete` | netegen cua i ordre manual per `(profile, model)` | ViewSet + views | `TechnicianQueueOrder` | l'ordre manual és per **model**, no per volta | `tasks/tests.py:242-259` | **ES LLEGEIX** |
| `frontend/src/components/model/WorkPlan.jsx` | pla de treball del model | usuari | crida `transition`, `openTask` | camps que llegeix: `id`, `status`, `task_type_code`, `task_type_name`, `assignee_id`, `assignee_nom`, `temps_consumit_min`, `tipus_extern`, `origen`, `off_recipe`. **No llegeix `ronda` ni `ronda_seq`** | — | **ES TOCA** |
| `frontend/src/components/model/TaskTree.jsx` | arbre de tipus de tasca | usuari | `openTask` | llegeix `status`, `assignee_id`, `assignee_nom`, `task_type_code`, `temps_consumit_min`, `id` | — | **ES TOCA** |
| `frontend/src/components/model/SessionActions.jsx` | accions de sessió (2 usos de `.id`) | usuari | transicions | mínima superfície | — | **NO ES TOCA** |
| `frontend/src/pages/ModelSheet.jsx:1099-1113` | ja crida `models.obrirRonda({motiu, codes})` | usuari | ronda/correcció | ja hi és; li faltaria l'ENTREGA | — | **ES LLEGEIX** |
| `frontend/src/pages/TechSheetEntry.jsx` (134 l.) | entrada a la fitxa | usuari | — | no toca `ModelTask` directament | — | **NO ES TOCA** |
| `frontend/src/pages/TallerPatro.jsx` (1541 l.) | taller de patró | usuari | — | no llegeix camps de `ModelTask` de ronda | — | **NO ES TOCA** |

### Els vuit consumidors de `tasca_vigent` (cens exhaustiu)

1. `tasks/views_b.py:576` — `open_model_task_view`
2. `tasks/views_b.py:1641` — `crono_declarat_view`
3. `tasks/serializers_b.py:101` — `get_es_vigent`
4. `tasks/services_batec.py:108` — `batec_escriptura`
5. `tasks/services_scheduling.py:33` — `reagenda_tasca`
6. `tasks/services_r.py:130` — `obrir_ronda` (per resoldre les MARES)
7. `tasks/services_r.py:183` — `obrir_correccio` (idem)
8. `models_app/views.py:1966` — `_assegura_pom_task_oberta`

### 🔎 A MESURAR: hi ha CODI que llegeixi `Model.fase_actual` per decidir el CONTEXT d'una tasca?

**SÍ, en tres punts, i cap d'ells és pintar:**

| Punt | Què decideix amb la fase |
|---|---|
| `fitting/views.py:309` (`schedule_now`) | **estampa la fase del model a la sessió**: `fase=request.data.get('fase') or model.fase_actual`. La `FittingSession.fase` és un camp real (`fitting/models.py:318`) i queda congelat a la sessió. |
| `tasks/services_e.py:22` (`request_production`) | `if phase != model.fase_actual and not phase_passed_gate(...)` → **refusa** enviar a confecció una fase futura. |
| `fitting/services.py:1181-1182` (`advance_phase`) | `if pf.model.fase_actual != 'TOP' and not has_delivered_production(pf.model.pk, pf.model.fase_actual)` → **bloqueja l'avanç** si no hi ha confecció entregada per a la fase ACTUAL. |

Lectures que **només pinten** (no decideixen): `models_app/views.py:4355-4361` (`next_phase` del
dashboard), `planning/views.py:802` (barra del Gantt), `tasks/views_b.py:214` (`by_model`),
`models_app/serializers.py:166`, `tenants/federation_service.py:425,464`.

🚨 **La col·lisió, mesurada:** la fase **ja és un eix de context de treball** en tres decisions
dures, i una d'elles (`FittingSession.fase`) **la materialitza en una fila**. Una ronda que també
volgués ser el context de la feina tindria dos eixos que diuen «de quina volta és aquesta feina»
i cap dels dos els concilia. *(Sense veredicte de disseny: v. §D.)*

---

## R2 · LA MÀQUINA D'ESTATS I EL PUNT DEL SEGELL

### La taula `ALLOWED` — `backend/fhort/tasks/services_c.py:17-39`

```python
ALLOWED = {
    'Pending':    {'InProgress'},
    'Paused':     {'InProgress'},                      # Paused→Done NO hi és (decisió Agus 28/07)
    'InProgress': {'Paused', 'Done', 'Pending'},       # →Pending = ÚNICA entrada GUARDADA
    'Done':       {'InProgress'},                      # reobertura = rectificació
}
```

### `transition_task` — `services_c.py:276-431`, cos sencer

| Pas | Línies | Què fa |
|---|---|---|
| Validació `ALLOWED` | 288-290 | `TransitionError('Transició no permesa')` |
| **Guard J-bis** (`InProgress→Pending`) | 309-314 | exigeix `auto == AUTO_CONSULTA` **I** cap tram obert amb `escriptura_at` |
| **Guard d'albarà** (`Done→InProgress`) | 319-326 | `te_paret_albara(task)` → `TransitionError(code='tasca_albaranada')`. `force=True` el salta (només `retype_scaling_to_grading`) |
| Exclusió per tècnic | 331-346 | `_aplica_exclusio_tecnic(profile, task)` — tanca trams oberts del tècnic a ALTRES tasques i les pausa amb `auto='exclusio_inprogress'` |
| Timer | 348 / 356 | `_open_timer` (`:42`) / `_close_open_timer` (`:59`) |
| `started_at` / `finished_at` | 349-364 | `→Pending` neteja també `started_at` |
| Auto-assign | 367-368 | assigna si `assignee_id is None` |
| Log | 372 | `_log` → `TaskTransition` amb `auto` |
| Fase | 379 | `Model.objects.filter(pk=…, fase_actual='Pending').update(fase_actual='Dev')` |
| Encàrrec | 401-406 | `assign_work_order` (savepoint propi, no-fatal) |
| **Welford** | 408-412 | `if to_status == 'Done': record_actual_time(task)` |
| Federació | 425-429 | `sync_estat_segur(model, SENTIT_MADURESA)` a CADA canvi d'estat |
| Meritació | **NO HI ÉS** (381-395) | va marxar a `services_batec._meritar_si_cal` (F1.4 · D-10) |

`rectification_count` (`:470`) = `count(TaskTransition WHERE from='Done' AND to='InProgress')`.

### Callers EXHAUSTIUS de `transition_task`

**Backend (7 call-sites reals, 12 crides):**

| Fitxer:línia | Gest d'usuari que el dispara |
|---|---|
| `tasks/views_b.py:461` (`transition_task_view`) | Play / Pausa / Stop al kanban i al Pla de treball |
| `tasks/views_b.py:624` (`open_model_task_view`) | «Obrir tasca» des del menú de la fitxa / porta-menú |
| `tasks/views_b.py:772` (`sortir_sense_escriptura_view`, branca `pausa_si_cal`) | **desmuntatge**: tancar pestanya / navegar fora amb escriptura |
| `tasks/views_b.py:796` (`sortir_sense_escriptura_view`) | sortir d'una pantalla **sense haver escrit** (`auto=AUTO_CONSULTA`) |
| `tasks/services_batec.py:135` (`batec_escriptura`) | **qualsevol escriptura de dades** sobre el model (18 punts, v. R3) |
| `tasks/services_r.py:371` (`engega_crono_declarat`) | botó «engegar crono» d'una tasca `Externa-lliure` |
| `tasks/services_r.py:403` (`atura_crono_declarat`) | botó «aturar crono» |
| `tasks/management/commands/pausa_tasques_oblidades.py:102` | **cron** (`auto='cron_40min'`), xarxa de seguretat |
| `tasks/management/commands/retype_scaling_to_grading.py:66-67` | command de migració (`force=True`), no és gest d'usuari |
| `models_app/views.py:1975` (`_assegura_pom_task_oberta`) | **desar** la taula de mesures POM |

**Frontend (cap crida directa a `transition_task`; les portes HTTP):**

| Fitxer | Endpoint | Gest |
|---|---|---|
| `frontend/src/components/model/WorkPlan.jsx:231-238` | `modelTasks.transition` | Play/Pausa/Stop al pla del model |
| `frontend/src/pages/ModelSheet.jsx:519-540` | `models.openTask` (via `caraObrirTasca`) | obrir una eina des de la fitxa |
| `frontend/src/api/endpoints.js:434` | `POST model-task-items/<id>/transition/` | punt únic del client |
| `frontend/src/api/endpoints.js:448` | `POST model-tasks/<id>/sortir-sense-escriptura/` | sortida / desmuntatge |
| `frontend/src/api/endpoints.js:100` | `POST models/<id>/open-task/` | porta-menú |

### El gest de CONSULTA — on es marca avui

| Fet | Fitxer:línia |
|---|---|
| **Constant** `AUTO_CONSULTA = 'consulta_sense_escriptura'` | `tasks/services_c.py:14` |
| **Camp d'escriptura real** `TimerEntrada.escriptura_at` | `tasks/models.py:49-51` |
| **Únic escriptor** d'`escriptura_at` | `tasks/services_batec.py:151-153` i `:159-161` (sempre al mateix `update()` que `last_heartbeat`) |
| **Veredicte** `TimerEntrada.consulta` (3 estats: `None`/`False`/`True`) | `tasks/models.py:66-70`; l'estampa `_close_open_timer`, `services_c.py:78-80` |
| **Naixement jutjable** (`consulta=False`) | `services_c.py:54-56` (`_open_timer`) |
| **Qui el llegeix** | `TRAMS_SANS` (`services_i.py:44`, `~Q(consulta=True)`) i `tram_compta` (`:47`) → Welford, albarà, consum, tots els agregadors visibles |
| **Porta HTTP** | `tasks/views_b.py:705` `sortir_sense_escriptura_view` |
| **Serializer** | `ModelTaskSerializer.sessio_amb_escriptura`, `serializers_b.py:126` |

🔑 **És el senyal correcte per a l'obertura de ronda per gest**: `escriptura_at` és l'ÚNIC camp del
sistema que diu «hi ha hagut feina real» i el diu **només** `batec_escriptura`. I és també el que
impedeix que una consulta n'obri cap: `batec_escriptura` retorna `sense_tasca`/`acabada`/`refusada`
sense obrir res quan no toca (`services_batec.py:109-140`).

### On cauria la guarda «tasca de ronda entregada = intocable»

**`tasks/services_c.py:319`**, exactament al costat del guard d'albarà, dins del bloc
`if not force and frm == 'Done' and to_status == 'InProgress':`. És l'únic lloc pel qual passen
**totes** les reobertures (les 10 crides de sobre hi convergeixen).

### Què trencaria avui: quants camins depenen que `Done→InProgress` sigui legal

| Camí | Fitxer:línia | Depèn? |
|---|---|---|
| Rectificació explícita (`open-task` amb `{reobrir: true}`) | `views_b.py:602-613` | **SÍ, per disseny** |
| `_assegura_pom_task_oberta` (desar POM sobre tasca `Done`) | `models_app/views.py:1975` + comentari `:1972-1974` | **SÍ**: «Done → reobertura (rectificació): és una decisió del tècnic» |
| `engega_crono_declarat` sobre una `Done` | `services_r.py:369-373` | **SÍ** (indirecte) |
| `batec_escriptura` | `services_batec.py:113-131` | **NO** — des del 06/08 fa `no-op` explícit sobre `Done` |
| `caraObrirTasca` (front) | `caraObrirTasca.js:56` (`CARA_FETA`) | **NO** — exigeix gest des de J·R3 |
| `rectification_count` | `services_c.py:470` | llegeix el log, no la transició |
| `record_actual_time` a cada `→Done` | `services_c.py:412` | **SÍ**: cada re-tancament és una mostra Welford nova (v. R4) |
| Command `retype_scaling_to_grading` | `:66-67` | **SÍ**, amb `force=True` |

**Corpus mesurat (staging):** **11** transicions `Done→InProgress` sobre **8** tasques diferents.

---

## R3 · LES PORTES D'ENTRADA (obertura de treball)

| Porta · fitxer:línia | Obre? | Reobre? | Reassigna? | Pausa en sortir? | Capability | Gating real | Transicions per gest |
|---|---|---|---|---|---|---|---|
| `open_model_task_view` `views_b.py:536` | **SÍ** (crea-si-falta + `→InProgress`) | només amb `{reobrir:true}` (409 `tasca_feta` sense el gest) | només amb `{handoff:true}` (409 `tasca_dun_altre`) | no | `EXECUTE_TASKS` (`_ExecuteTasks:419`) | `get_allowed_task_types(request.user)` (`:568`), `code` discriminant `task_type_not_allowed` | **1** (`→InProgress`) o **0** (branca claim) |
| `transition_task_view` `views_b.py:430` | SÍ | SÍ (si `to_status='InProgress'` des de `Done`) | no (auto-assign si `assignee` null) | no | `EXECUTE_TASKS` | `get_allowed_task_types` només per `→InProgress` (`:456`); `auto` limitat a `_AUTO_DEL_CLIENT={'guard_30min'}` i només sobre `→Paused` | **1** |
| `claim_task_view` `views_b.py:479` | no (no toca `status`) | no | **SÍ** (self-only) | no | `EXECUTE_TASKS` | `get_allowed_task_types` (`:509`); obté per `pk` **sense** `scope_model_task_queryset` (decisió: dashboard transparent) | **0** transicions d'estat, **1** fila `auto='handoff'` |
| `sortir_sense_escriptura_view` `views_b.py:705` | no | no | no | **SÍ, condicionalment**: sense escriptura torna a l'estat d'ENTRADA (llegit del log, `:791-794`); amb escriptura i `pausa_si_cal` → `Paused` | `EXECUTE_TASKS` | tram propi obligatori (`tecnic=profile`, `:766`) | **1** |
| `define_model_tasks_view` `views_b.py:325` | crea `Pending`, **no** obre | no | no | no | `DEFINE_TASKS` (`_DefineTasks:319`) | — | **0** |
| `obrir_ronda_view` `views_b.py:1692` | crea `Pending` d'una volta nova | no (l'evita: crea feina nova) | assigna al `profile` que obre | no | `EXECUTE_TASKS` | `get_allowed_task_types` sobre **tots** els `codes` (`:1719-1724`) | **0** |
| `crono_declarat_view` `views_b.py:1604` | SÍ (via `engega_crono_declarat`) | SÍ (indirecte) | auto-assign | SÍ (`atura` → `Paused`) | `EXECUTE_TASKS` | només `TaskType.tipus == 'Externa-lliure'` (`services_r.py:357`) | **1** per gest |
| `temps_declarat_view` `views_b.py:1559` | no | no | no | no | `EXECUTE_TASKS` | `Externa-lliure` (`services_r.py:284`) | **0** |
| `ModelTaskViewSet` PATCH `views_b.py:300` | no | no | **SÍ** (assignee arbitrari) | no | `DEFINE_TASKS` | `scope_model_task_queryset` (`:61`) + `_validate_assignee` (`:238`) | **0** |
| `assign_model_view` / `unassign_model_view` `views_b.py:384,405` | no | no | SÍ (massiu) | no | `DEFINE_TASKS` | — | **0** |
| **Batec d'escriptura** `services_batec.py:87` | **SÍ** (`Pending`/`Paused` → `InProgress`) | **NO** (`Done` = no-op des del 06/08) | no | no | la de la vista que el porta | `tasca_vigent`; refús silenciós | **1** la primera vegada, **0** després |
| `pausa_tasques_oblidades` (cron) `:102` | no | no | no | SÍ (`auto='cron_40min'`) | — (command) | — | **1** |

### Les dues portes que obren-i-tanquen dins del mateix request

⚠️ **Cap de les dues ho fa avui.** Les dues han estat DESARMADES:

| Porta | Estat |
|---|---|
| `_assegura_pom_task_oberta` `models_app/views.py:1946` | **Ja no tanca.** F1.2: «DESAR NO TANCA MAI (D-2)». Ara només OBRE-si-cal. Comentari `:1949-1952`: abans tancava a cada desat i **28 de 49 transicions `→Done` eren repeticions sobre una tasca ja tancada**. Transicions per gest: **1** (`→InProgress`) o **0**. |
| `resolve_size_check` `models_app/services_size_check.py:148` | **Ja no tanca.** F1.2 (`:161-163` i `:287-297`): el bloc que tancava a `Done` dins d'un `try/except Exception` va marxar sencer. `tasca_finalitzada` es conserva al retorn i **és sempre `False`**. Transicions per gest: **0**. |

---

## R4 · TEMPS I APRENENTATGE — risc d'enverinament

### Nodes

| NODE · fitxer:línia | Què fa | Llegeix | Escriu |
|---|---|---|---|
| `tasks/models.py:4-77` `TimerEntrada` | tram de treball. Camps: `inici`, `fi`, `minuts`, `actiu`, `last_heartbeat`, `origen` (`mesurat`/`declarat`), `escriptura_at`, `consulta` | tot el sistema de temps | `_open_timer`, `_close_open_timer`, `batec_escriptura`, `declara_temps`, `corregeix_tram_declarat` |
| `services_c.py:42` `_open_timer` | obre tram (`consulta=False`, `origen` de la porta); tanca abans qualsevol obert de la MATEIXA tasca | — | `TimerEntrada` |
| `services_c.py:59` `_close_open_timer` | tanca TOTS els oberts; `minuts = max(0, (now-inici)//60)`; **dona el veredicte de consulta** (`:78-80`) | — | `fi`, `minuts`, `actiu`, `consulta` |
| `services_i.py:10` `WELFORD_MIN_SAMPLES = 5` | llindar seed→estadística | `effective_minutes`, `lookup_estimated_minutes` | — |
| `services_i.py:17` `MAX_MINUTS_TRAM = 1440` | sostre de plausibilitat, **exclusió no retall** | `TRAMS_SANS`, `tram_compta`, `declara_temps` | — |
| `services_i.py:44` `TRAMS_SANS` | `Q(fi__isnull=False, minuts__lte=1440) & ~Q(consulta=True)` | `_real_minutes`, `minuts_per_model_task`, `commerce/services.py`, consum | — |
| `services_i.py:73` `record_actual_time` | **Welford online** | `_real_minutes(task)` | `TaskTimeEstimate.n/mean_minutes/m2` |
| `services_i.py:104` `effective_minutes` | mitjana real si `n>=5` i `>0`, si no el seed; **contracte: enter>0 o None** | `TaskTimeEstimate` | — |
| `services_g.py:11` `lookup_estimated_minutes` | cascada de 4 graons | cel·la · empíric global · `TimeSeed` · None | — |
| `tasks/models.py:626-645` `TaskTimeEstimate` | `unique_together = [('garment_type_item','task_type')]` | tota la cascada | `record_actual_time`, `time_set_estimate_view` |
| `tasks/models.py:675-698` `TimeSeed` | `unique_together = [('scope','key')]`; `scope ∈ {task, phase}` | graó 3 | `time_capture_seed_view` |
| `ModelTask.estimated_minutes` `models.py:196` | **snapshot** en crear la tasca | `scheduler_service._pin_block`, Gantt | `define-tasks`, `open-task`, `obrir_ronda`, `obrir_correccio`, `recompute_for_technicians` |
| `plan_service.py:48-77` `recompute_for_technicians` | **re-resolució** del snapshot: només tasques `status == 'Pending'` i **no** `planned_locked` (`:66-72`) | `lookup_estimated_minutes` | `estimated_minutes` |

### 🔎 LA CLAU EXACTA DE LA CEL·LA WELFORD

`backend/fhort/tasks/services_i.py:86-87`:

```python
cell, _ = TaskTimeEstimate.objects.select_for_update().get_or_create(
    garment_type_item_id=item_id, task_type=model_task.task_type)
```

**La clau és `(Model.garment_type_item, ModelTask.task_type)`. NO hi entra ni el model, ni la
ronda, ni el tècnic, ni la fase.**

### 🔎 PREGUNTA MESURABLE: N tasques del mateix `task_type` sobre un model (una per ronda)

**Càlcul exacte, no intuïció.** Sigui un model M amb `garment_type_item = I`, i K tasques de
`task_type = T` (K = 1 prevista + K−1 de rondes/correccions). Cada una, en cada
transició `→Done`, executa `record_actual_time` (`services_c.py:412`), que:

1. calcula `x = _real_minutes(task_k)` = **Σ minuts dels trams SANS d'AQUELLA tasca**
   (`services_i.py:70`) — cada tasca té els seus trams propis, no comparteixen;
2. si `x <= 0` → surt sense mostra (`:84-85`);
3. si no, actualitza **la mateixa cel·la** `(I, T)` amb `n += 1`.

**Resultat: K mostres a la MATEIXA cel·la** `(I, T)`, cadascuna amb el valor de la seva volta.
I com que la transició no és idempotent, **cada re-tancament d'una mateixa tasca hi afegeix una
mostra més**: una tasca reoberta 3 cops i tancada 3 cops aporta 3 mostres, amb el **total acumulat
de tots els seus trams** cada vegada (no el delta). Això ja passa avui sense rondes i està escrit
al test `tasks/test_recompute_welford.py:121`: «`record_actual_time` es crida a CADA →Done:
re-tancar aporta una altra mostra, amb el total acumulat d'aquell moment».

**Efecte numèric sobre la mitjana:** amb rondes, la cel·la `(I, T)` aprendria «quant costa fer T
sobre un item I», barrejant primeres voltes (feina completa) amb correccions (feina parcial). El
Welford no distingeix les dues poblacions, i `WELFORD_MIN_SAMPLES = 5` s'assoliria **abans**
(més mostres per model) amb una mitjana **desplaçada cap avall** si les correccions són curtes.

### 🔎 El corpus actual (STAGING, foto 17:18 UTC)

**Transicions `→Done` per `ModelTask`:**

| nº de `→Done` | nº de tasques |
|---|---|
| 1 | 6 |
| 2 | 3 |

→ **9 tasques** han estat tancades alguna vegada; **3 de 9 (33 %) tenen més d'un `→Done`** — el
ping-pong d'avui, encara viu. 11 rectificacions sobre 8 tasques.

**Timers (102 files):**

| Fet | n |
|---|---|
| total | 102 |
| oberts (`fi IS NULL`) | 1 |
| **tancats amb `minuts = 0`** | **46** (45 % del total) |
| `consulta = true` | 10 |
| `consulta = false` | 11 |
| `consulta = NULL` (històric, no jutjat) | 81 |
| amb `escriptura_at` | 10 |
| `minuts > 1440` | **0** |

**Cel·les Welford:** 468 cel·les; **28** amb `n > 0`; **1 sola** amb `n >= 5` (madura).

🚨 **Els 46 trams de 0 minuts NO són descartats per `TRAMS_SANS`** (que només exclou `fi IS NULL`,
`minuts > 1440` i `consulta=True`). El que els descarta és el guard `x <= 0` de
`record_actual_time` (`services_i.py:84`) — però **només si el total de la tasca és 0**. Un tram
de 0 minuts dins d'una tasca amb altres trams **suma 0 i dilueix res**; el problema és que la
mostra que entra al Welford és el total, no el tram.

---

## R5 · MERITACIÓ I FRONTERA `public`↔`tenant`

| NODE · fitxer:línia | Què fa |
|---|---|
| `models_app/models.py:245` `Model.consumption_started_at` | marca «aquest model ja ha meritat». `null` = no |
| `models_app/models.py:69` `GarmentSet.consumption_started_at` | idem per al CONJUNT (SET-1 · A3) |
| `services_batec.py:54` `_meritar_si_cal(task)` | **EL GALLET** (F1.4 · D-10). Surt d'`escriure`, no d'`obrir`. Guard ràpid `if model.consumption_started_at is not None: return` (`:77`). No-fatal |
| `services_c.py:212` `_meritar_model` | **el guard d'idempotència ÉS** `Model.objects.filter(pk=…, consumption_started_at__isnull=True).update(...)` (`:216-218`); si `rows == 0` → `return` |
| `services_c.py:231` `_meritar_conjunt` | SET = 1 mèrit. Guard idèntic sobre `GarmentSet` (`:252-254`) + estampa TOTES les germanes (`:257-259`) |
| `models_app/models.py:1360` `ConsumptionRecord` | albarà de consum al TENANT. `model` i `garment_set` són **OneToOne** amb XOR (`:1385-1393`) |
| `services_c.py:195` `_emetre_meritacio` | envia el signal amb `actor_schema = connection.schema_name` |
| `tasks/signals.py:17` `model_consumption_started` | `Signal()` nu |
| `backoffice/receivers.py:7` `on_model_consumption_started` | **el receiver a `public`**: `with schema_context('public')` → `ModelConsumptionEvent.objects.get_or_create(opaque_ref=…)` |
| `backoffice/management/commands/reconcile_consumption.py` | reconciliació de forats; criteri: activitat de tasca + cap marca (`:74-83`) |
| `models_app/management/commands/clone_model_for_qa.py:91` | **buida** `consumption_started_at` al clon (llista de camps a `:91`) |
| `services_r.py:380` (`engega_crono_declarat`) | **segon gallet**: un model que comença per una tasca externa també merita |

### 🔎 Confirmació: la SEGONA RONDA NO REMERITA

**CONFIRMAT, i per dos guards independents:**

1. `services_batec.py:77-78` — `if model.consumption_started_at is not None: return` (surt abans
   de tocar res);
2. `services_c.py:216-219` — `UPDATE … WHERE consumption_started_at IS NULL` retorna `rows = 0` →
   `return` sense crear `ConsumptionRecord` ni emetre l'event.

I encara que el guard 1 no hi fos, `ConsumptionRecord.model` és **`OneToOneField`**
(`models_app/models.py:1369`): un segon registre pel mateix model **peta a la BD**.

**El punt exacte que caldria tocar el dia que es vulgui meritar per ronda** (només el nomeno):

- `services_c.py:212-228` `_meritar_model` — el seu guard d'idempotència i l'ancoratge
  `ConsumptionRecord.model` OneToOne;
- `models_app/models.py:1369-1376` — la cardinalitat OneToOne de `ConsumptionRecord`;
- `services_batec.py:77` — el guard ràpid de sortida.

**Corpus staging:** 3 models amb `consumption_started_at`, **2** `ConsumptionRecord`.

---

## R6 · GATES I ESTAT DEL MODEL

### Tots els escriptors de `Model.fase_actual` (enumeració exhaustiva)

| # | Fitxer:línia | Escriu | Context |
|---|---|---|---|
| 1 | `tasks/services_c.py:379` | `update(fase_actual='Dev')` **només si era `'Pending'`** | dins de `transition_task`, a cada `→InProgress` |
| 2 | `tasks/services_d.py:51,55` | `model.fase_actual = to_phase; save(update_fields=['fase_actual'])` | `advance_phase_gate` |
| 3 | `tasks/services_d.py:80-81` | idem, enrere | `regress_phase` |
| 4 | `models_app/tech_sheet_views.py:313` | `fase_actual='Proto'` a la creació | `create-from-sheet` |
| 5 | `models_app/management/commands/clone_model_for_qa.py:89` | `clone.fase_actual = 'Proto'` | clon de QA |
| 6 | `models_app/management/commands/sembra_model_837.py:581` | sembra | banc |
| — | `models_app/models.py:243` | `default='Pending'` | — |

🔑 **`fitting` NO l'escriu.** `fitting/services.py:1204-1207` ho declara explícitament: «fitting.
advance_phase TAMPOC escriu `Model.fase_actual` ni crea `GateEvent`. L'avanç de fase és competència
EXCLUSIVA de `tasks.advance_phase_gate`, únic amo de `fase_actual`». El bucle de `advance_phase`
(`:1196-1207`) **queda buit a posta**; `advanced` i `sealed` tornen sempre `[]`.

### Els gates

| NODE · fitxer:línia | Què fa | Qui el crida |
|---|---|---|
| `tasks/services_d.py:11` `model_ready_for_gate(model_id)` | **TOTES** les `ModelTask` del model a `Done` **i** n'hi ha ≥1 | `gate_ready_models_view` (`views_b.py:874`), `model_dashboard_view` (`models_app/views.py:4362`) |
| `tasks/services_d.py:38` `advance_phase_gate` | guard TOP · escriu `fase_actual` · `GateEvent(kind='advance')` · **`seal_model_grading`** · `_publica_maduresa` | `gate_model_view`, `gate_bulk_view`, `advance_phases_chain` |
| `tasks/services_d.py:69` `regress_phase` | només `fase_actual` enrere + `GateEvent(kind='regress')` | `regress_model_view` |
| `tasks/services_d.py:88` `advance_phases_chain` | seqüència de gates | `gate_model_view` amb `to_phases` |
| `tasks/models.py:282` `GateEvent` | log `from_phase`/`to_phase`/`kind`/`by`/`notes`/`at` | `phase_passed_gate` (`services_e.py:13`), `request_production` |
| `fitting/services.py:988` `seal_model_grading` | segella el grading del model | **només** `services_d.py:60-63` |

### `Model.estat` — el camp

**Definició:** `models_app/models.py:88-97`. Valors emmagatzemats: `Nou`, `EnCurs`, `EnRevisio`,
`Tancat` (les etiquetes «En curs», «En revisió» són **labels**, no valors).

**Recompte a BD (staging, schema `fhort`, amb delimitadors):**

| valor | n |
|---|---|
| `[Nou]` | **32** |

**El valor amb espai «En curs» NO hi és**: cap fila amb `[En curs]`. `data_tancament IS NOT NULL`: **0** files.

**Qui l'escriu:** pràcticament **ningú** al món tècnic. `clone_model_for_qa.py:90`
(`clone.estat = 'Nou'`) i `sembra_model_837.py:581`. `advance_phase_gate` **ja no l'escriu**, i el
comentari ho declara (`services_d.py:52-54`): «Bloc 3 (estat→fase): la terminalitat la marca
`fase == TOP`; el camp `estat` ja no es superficia (es retira al pas de migració diferit)».

**Qui el llegeix:** `views_b.py:96` (whitelist d'ordenació de `by_model`), `:226` (payload),
`ModelFilter` (`models_app/views.py:82`), `model_dashboard_view:4362`, `models_app/serializers.py`.

**Què passa a TOP:** `advance_phase_gate` refusa avançar des de `'TOP'` (`services_d.py:47-48`).
`advance_phase` del fitting salta els models a TOP (`fitting/services.py:1197-1199`).
`has_delivered_production` deixa d'exigir-se a TOP (`:1181`). **No hi ha cap escriptura de `estat`
a TOP.**

`fase_actual` a BD: `[Pending]` 28 · `[Dev]` 3 · `[Proto]` 1. **`GateEvent`: 0 files.**

### 🔎 Si l'obertura d'una ronda declarés una fase superior

**Capability necessària: `CLOSE_GATES`** (`accounts/capabilities.py:9`), que és la que gover­na
`gate_model_view`/`gate_bulk_view`/`regress_model_view` (`_CloseGates`, `views_b.py:699-701`).
Nota: `obrir_ronda_view` avui demana **`EXECUTE_TASKS`**, no `CLOSE_GATES`.

**Qui la té avui (rols):** `ROLE_CAPABILITIES` (`capabilities.py:27-36`) → `manager` i `admin`.
`technician` i `product_manager` **no**.

**Qui la té avui (usuaris reals del tenant `fhort`, 6 perfils):**

| id | usuari | rol | `CLOSE_GATES`? |
|---|---|---|---|
| 1 | `a.devant@fhort.cat` | admin | **SÍ** (ALL_CAPABILITIES) |
| 13 | Montse | manager | **SÍ** (rol + `grant` explícit) |
| 14 | Salva | admin | **SÍ** |
| 15 | Marta | technician | **NO** (`grant: ['schedule_fittings']`, `revoke: ['view_team_tasks']`) |
| 19 | `qa.loginunic@fhort.test` | technician | **NO** |
| 26 | `fhort` | technician | **NO** |

→ **3 de 6** perfils podrien declarar una fase des d'una ronda.

---

## R7 · FITTING — el focus del tram

### `FittingSession` — `backend/fhort/fitting/models.py:291-378`

| Camp | Tipus | Escriptor |
|---|---|---|
| `garment_set` / `model` | FK nullable, **XOR** per `CheckConstraint` `fittingsession_set_xor_model` (`:364-373`) | `schedule_session` (`services.py:321`) |
| `fase` | CharField amb `Model.FASE_CHOICES` | `schedule_session`; `schedule_now` hi posa `model.fase_actual` (`views.py:309`) |
| `data`, `start_time`, `end_time` | — | `schedule_session`, `reschedule_group` (`:1249`) |
| `estat` ∈ {`Programada`,`Oberta`,`Tancada`,`Anullada`} | default `'Oberta'` | `open_session` (`:465`), `_seal_session` (`:1088`), `discard_session` (`:1306`) |
| `duracio_minuts` | 10 min × models | `schedule_session`, `schedule_bulk` |
| `attendees` M2M | — | `set_group_attendees` (`:1382`) |
| `convocatoria` UUID | compartit pel bulk; null = individual | `schedule_bulk` (`:378`) |
| `started_at` / `finished_at` | marques REALS | `open_session` / `_seal_session` (`:1102-1104`) |
| `motiu_anullacio` | — | `discard_session` |

**QUANTS MODELS pot tocar una sessió:** el XOR mana. Amb `model` → **1** (i `PieceFitting` té
`unique_together = [('session','model')]`, `fitting/models.py:420`). Amb `garment_set` → **N**, un
`PieceFitting` per peça. La CONVOCATÒRIA (`convocatoria` UUID) agrupa **N sessions independents**,
no una sessió amb N models.

**Corpus staging:** 9 sessions, **9 amb `model`**, **0 amb `garment_set`**, **0 amb
`convocatoria`**. Estats: Oberta 4 · Tancada 2 · Programada 2 · Anullada 1. 9 `PieceFitting`.

### Qui ancora a qui (FK reals)

```
models_app.Model ──1:N──> fitting.SizeFitting          (unique_together model,numero)
       │                        │
       │                        └──1:N──> fitting.GradingVersion  (version_number, is_active)
       │                                          │
       │                                          └──1:N──> fitting.GradedSpec
       │
       ├──1:N──> fitting.FittingSession  (XOR amb GarmentSet)
       │                 │
       │                 └──1:N──> fitting.PieceFitting ──FK NOT NULL──> GradingVersion
       │                                    │                            (models.py:395)
       │                                    └──1:N──> fitting.PieceFittingLine
       │
       └──1:N──> models_app.SizeCheck ──1:N──> models_app.SizeCheckLine
```

🚨 **`SizeCheck` NO penja de `FittingSession`.** És una entitat NETA de `models_app`, deliberadament
desacoblada (`services_size_check.py:1-8`).

### 🔎 ON ES NUMERA EL «FIT n» avui

**`fitting.SizeFitting.numero`** (`fitting/models.py:24`, `PositiveIntegerField`), amb
`unique_together = [('model','numero')]` (`:56`). **No té autoincrement de model**: el `next_num`
el calculen els cridadors, i n'hi ha **6 diferents**:

| Fitxer:línia | Com |
|---|---|
| `models_app/views.py:3123` | `numero=next_num` |
| `models_app/extraction_views.py:3429,3604` | `while SizeFitting.objects.filter(model=model, numero=next_num).exists()` |
| `models_app/bulk_import_service.py:536` | `numero=1` fix |
| `models_app/signals.py:133` | `numero=number` (signal de creació de model) |
| `pom/services.py:594` | `numero=next_num` (`get_or_create_size_fitting`) |
| `clone_model_for_qa.py:129` / `sembra_model_837.py:622` | `numero=1` / del banc |

L'**altre** número que la UI ensenya és `GradingVersion.version_number` (`fitting/models.py:76`),
resolt per `_active_grading_version` (`services.py:931`, `-version_number`) i `vigent_grading_version`
(`:942`). **Corpus staging:** `max(SizeFitting.numero) = 2`, `max(GradingVersion.version_number) = 9`.

### Les operacions

| NODE · fitxer:línia | Què fa |
|---|---|
| `services.py:1088` `_seal_session` | idempotent (`estat=='Tancada'` → return). GarmentSet: només si `session_can_advance`. Escriu `estat`+`finished_at`, allibera la franja (`recompute_for_technicians`, `:1104-1107`), captura durada |
| `services.py:1075` `session_can_advance` | DERIVAT: tots els gates ∈ {OK, EXCEPCIO} i ≥1 peça |
| `services.py:1032` `set_piece_gate` | escriu `gate`,`gate_motiu`,`gate_per`,`gate_at`; `NO_OK` → **hook brain**; sempre `_seal_session` (3r trigger) |
| `services.py:782` `close_piece_fitting` | consolida la BASE a `BaseMeasurement`, Welford per `codi_client`, versionat funcional (v+1), segell — tot dins **una** `transaction.atomic` (`:818`) |
| `services.py:480` `create_piece_fitting` | camí lliure: materialitza `SizeFitting` i `GradingVersion` si falten (S45/B) en lloc de bloquejar |
| `services.py:897` `discard_piece_fitting` · `:1306` `discard_session` · `:1408` `delete_group` | descarts |
| `services.py:1249` `reschedule_group` · `:1322` `add_model_to_group` · `:1367` `remove_model_from_group` · `:1382` `set_group_attendees` | operacions de GRUP per `convocatoria` |
| `models_app/services_size_check.py:148` `resolve_size_check` | resol el check; **ja no propaga ni tanca tasca** |

### 🔎 `_reagenda_tasca_size_check` — el mecanisme que la ronda duplicaria

⚠️ **DIVERGÈNCIA:** avui es diu **`reagenda_tasca`** i viu a
`backend/fhort/tasks/services_scheduling.py:15` (extret i parametritzat a l'Sprint Y).

**Què fa exactament:**

```python
task = tasca_vigent(model, task_type_code)          # :33 — el resolutor únic
if task is None or task.status == 'Done': return False
d = date.fromisoformat(data_represa) if isinstance(str) else data_represa
naive_start = next_working_slot(prof, datetime.combine(d, time(8, 0)))     # :38 — 08:00
naive_end   = add_working_minutes(prof, naive_start, task.estimated_minutes or 60)   # :39
task.planned_start / planned_end / planned_locked = True                  # :40-43
```

**Amb quin calendari:** `planning/calendar_service.next_working_slot` + `add_working_minutes` —
el calendari laboral del PERFIL (`task.assignee`), amb `CompanyCalendar` i `Absencia` a sota.
Fallback de durada: **60 minuts** si no hi ha `estimated_minutes`.

**En quins casos es crida:** **un de sol**, `models_app/services_size_check.py:301-303`:

```python
if final_estat in ('Rebutjat', 'Descartat') and data_represa:
    reagendada = reagenda_tasca(model, data_represa, task_type_code='size_check')
```

És a dir: quan el size check es RESOL amb un veredicte que deixa la tasca VIVA (el tècnic diu
«aquest proto no serveix» o «avui no el mesuro») **i** ha triat una data de represa
(`serializers_size_check.py:48`: default avui + 5 dies laborables).

🚨 **LA COL·LISIÓ, MESURADA (sense veredicte):** la reagenda i la ronda responen **la mateixa
pregunta amb dos mecanismes**:

| | `reagenda_tasca` | Ronda nova |
|---|---|---|
| Unitat | la MATEIXA `ModelTask`, moguda al calendari | una `ModelTask` NOVA, `origen='ad_hoc'` |
| Identitat | es conserva (mateix `id`, mateix log, mateixos trams) | nova (`mare` apunta a l'anterior) |
| Comptador | cap | `Ronda.seq` puja |
| Temps | **acumula** sobre la mateixa tasca | tram nou, mostra Welford nova |
| Facturació | la mateixa línia | volta facturable a part |
| Gate | cap (`planned_locked = True` i prou) | `obrir_ronda` refusa si ja n'hi ha una d'oberta |

**«El proto no serveix, el refem» avui té dues portes que fan coses diferents i cap de les dues
sap de l'altra.** `reagenda_tasca` no consulta `Ronda`; `obrir_ronda` no consulta `planned_locked`.

### El hook `brain.on_fitting_measurement_changed`

`backend/fhort/fitting/brain.py:16`. **SEGUEIX SENT STUB** (`:25-31`: només `logger.info`, `return None`).

**Punts de crida (2):**
- `fitting/services.py:874-875` — dins de `close_piece_fitting`, quan hi ha hagut canvi
- `fitting/services.py:1059-1060` — dins de `set_piece_gate`, quan `resultat == 'NO_OK'`

### Gestos existents que serien «anunciar sessió» o «descarregar el full de fitting»

| Gest | Ruta | Fitxer |
|---|---|---|
| **Anunciar sessió (individual)** | `POST /api/v1/fitting-sessions/schedule/` | `fitting/views.py` → `services.schedule_session` (`services.py:321`) · front `endpoints.js:804` |
| **Anunciar sessió (aquí i ara)** | `POST /api/v1/fitting-sessions/schedule-now/` | `fitting/views.py:290-320` |
| **Anunciar convocatòria (bulk, N sessions encadenades)** | `POST /api/v1/fitting-sessions/schedule-bulk/` | `services.schedule_bulk` (`services.py:378`) · front `endpoints.js:809` |
| **Full de fitting (pantalla imprimible per model)** | `/fittings/:sessionId/full/:modelId` | `frontend/src/pages/FittingPrintSheet.jsx` · ruta a `App.jsx:420` |
| **Full de convocatòria** | `/fittings/convocatoria/:uuid` | `frontend/src/pages/FittingConvocatoriaSheet.jsx` · `App.jsx:475` |
| **Export CSV d'una peça** | `GET /api/v1/fittings/peca/<pf_id>/export/csv/` | `pom/s8_views.py:198`, registrat a `tasks/urls.py:247` |

🚩 **Anotat (fora de scope, NO tocat):** `ExportFittingCSV` (`frontend/src/components/ExportButton.jsx:88-98`)
construeix `/api/v1/fittings/${fittingId}/export/csv/` — **sense el segment `peca/`** que la ruta
registrada exigeix. A més **no s'importa enlloc** (`grep -rn ExportButton src --include=*.jsx` →
només `SizeSetDetail.jsx`, que importa `ExportSizeSetCSV` i `ExportGradingCSV`). O sigui: l'endpoint
existeix i **no té cap consumidor viu**, i l'únic embolcall que en tenia apunta a una URL que no hi és.

---

## R8 · CALENDARI (G7)

### `calendar_events_view` — `backend/fhort/planning/views.py:214-509`

**Les TRES fonts que agrega:**

| `tipus` | Font | Scope | Forma |
|---|---|---|---|
| `"tasca"` | `ModelTask` no-Done amb `planned_start` (`:238-241`) | `scope_model_task_queryset` (`:243`) | bloc HORARI, color del tècnic (`color_avatar`, fallback `#6b7280`) |
| `"confeccio"` | `Production` (`:289`) | **cap** (visible a tot autenticat) | `all_day=True`, color fix `#7c6f64` |
| `"fitting"` | `FittingSession` excloent `Anullada` (`:342-345`) | `attendees=profile` si no hi ha `VIEW_TEAM_TASKS` (`:353-356`) | horari si té `start_time`+durada; si no, marcador de dia |

**Forma exacta de l'event:**

```json
{ "id": "task-<id>|confeccio-<id>|fitting-<id>[-<att>]|fitting-conv-<uuid>[-<att>]-<sid>",
  "tipus": "tasca|confeccio|fitting",
  "start": "ISO amb offset Europe/Madrid  |  YYYY-MM-DD (all_day)",
  "end":   "idem",
  "titol": "<codi_intern> · <task_type|fitting fase|supplier · conf.>",
  "tecnic_id": int|null, "tecnic_nom": str|null,
  "color": "#rrggbb", "link": "/models/<id> | /fittings/<id>",
  "en_risc": bool,            // només 'tasca': planned_end.date() > model.data_objectiu
  "all_day": bool,            // absent als 'tasca'
  "tancada": bool,            // només 'fitting'
  "meta": { … }               // variable per tipus
}
```

### 🚨 El punt on el grup de fitting s'emet com a `all_day` multi-dia — **JA NO HI ÉS**

**`planning/views.py:450-465`** (G7 Bloc 4/4b): per cada convocatòria s'emet **un marcador per
`FittingSession` REAL, cada un al SEU dia**, amb `start_dt == end_dt` quan és all-day (`:461`).
El comentari `:455-459` documenta el canvi: «NO un rang/bloc: els dies SENSE sessió queden buits
(abans `inRange` replicava l'all-day a tot el rang primera→última)».

Un event **horari** (amb `start_time` i durada) surt amb `all_day=False` (`:454-457`); només sense
hora cau a marcador de dia.

### El punt del front que el replica per dia

**`frontend/src/pages/PlanningCalendar.jsx:171-178`:**

```js
const inRange = useCallback((e, d) => {           // :171
  const ds = startOfDay(d).getTime()
  return startOfDay(e._start).getTime() <= ds && ds <= startOfDay(e._end).getTime()
}, [])
const allDayByDay = useCallback((d) => shown.filter(e => e._allDay && inRange(e, d)), …)   // :177
const monthByDay  = useCallback((d) => shown.filter(e => e._allDay ? inRange(e, d) : sameDay(e._start, d)), …)  // :178
```

`enrich` (`:59-70`) marca `_allDay` i converteix `start`/`end` amb `parseLocalDate`.
**El mecanisme de replicació segueix viu**, però avui rep sempre `start == end` i replica un sol dia.

### El precedent de la confecció (col·lapse a un marcador al backend)

**`planning/views.py:305-308`:**

```python
# Marcador d'UN SOL DIA al dia d'entrega (expected_at), com fa fitting. Ja no es pinta com a
# banda de durada requested→expected (que replicava la confecció a tots els dies del tram).
# Sense expected_at, cau al dia d'enviament (requested_at).
marker_d = p.expected_at or req_d
```

### Cost de cada opció (sense triar)

| Opció | Fitxers | Superfície | Qui més ho veu |
|---|---|---|---|
| **Col·lapse al BACKEND** (precedent confecció + G7) | `planning/views.py` (1 fitxer, ~10 línies per font) | l'endpoint és **compartit** per `PlanningCalendar.jsx:127`, `Dashboard.jsx:452,482` | tots els consumidors alhora, sense desplegar front |
| **Expansió al FRONT** (`inRange`) | `PlanningCalendar.jsx:171-178` (ja existeix) | **només** `PlanningCalendar`; `Dashboard.jsx` NO fa servir `inRange` | el Dashboard veuria una cosa diferent del calendari |

**Consumidors reals de `calendar.events`:** `PlanningCalendar.jsx:127`, `Dashboard.jsx:452` i `:482`.

---

## R9 · PLANIFICACIÓ

| NODE · fitxer:línia | Entrades | Sortides | Què escriu |
|---|---|---|---|
| `planning/scheduler_service.py:117` `schedule(qs, now, save)` | queryset **o** llista d'objectes en memòria (preview) | `{placements, warnings, needs_estimate, models}` | si `save=True`: `planned_start/end` de les MOVIBLES + `Model.predicted_start/end` (`:236-250`, `.date()`) |
| — blindatge | `:141-142` | — | **mai** toca `Done` |
| — agrupació | `:164-170` | `warning 'sense assignee'` | — |
| — ordre | `:196-199` | `TechnicianQueueOrder` si existeix, si no ordre natural | — |
| `planning/models.py:72` `TechnicianQueueOrder` | `(profile, model, position)` | — | **SPARSE**: només els models amb ordre MANUAL hi tenen fila; la resta no en tenen. Clau composta `(0, position)` vs `(1, *_model_sort_key)` (`scheduler_service.py:196-199`). Corpus staging: **0 files** |
| `ModelTask.planned_start/end/locked` `models.py:200-208` | — | Gantt, calendari, `by_model.plan_start` | `schedule`, `reagenda_tasca`, `apply` |
| `Model.predicted_start/end` | DateField | Gantt (`planning/views.py:780`) | `scheduler_service.py:250` |
| `tasks/models.py:647` `PlanSnapshot` | immutable | `plan_snapshots_view` | `_save_snapshot` (`plan_service.py:98`) |

### TOTS els callers de `recompute_for_technicians` (9 call-sites)

| Fitxer:línia | Context |
|---|---|
| `tasks/views_b.py:316` | `ModelTaskViewSet.perform_update` — reassignació via PATCH |
| `tasks/views_b.py:530` | `claim_task_view` |
| `tasks/views_b.py:654` | `open_model_task_view`, branca handoff |
| `tasks/views_b.py:663` | `open_model_task_view`, «l'inici desplaça» |
| `fitting/services.py:372` | `schedule_session` |
| `fitting/services.py:456` | `schedule_bulk` |
| `fitting/services.py:1107` | `_seal_session` (allibera la franja) |
| `fitting/services.py:1244` | `_recompute_attendees` (operacions de grup) |
| `planning/views.py:552` | `plan_reorder_view` |
| `planning/plan_service.py:229, 388, 436, 455` | `assign_model`, `assign_batch`, `cleanup_after_pending_delete`, `unassign_model` |

### Endpoints de planning amb consumidor real al frontend

| Endpoint | Definit a `endpoints.js` | Usos reals (`.jsx`) | Veredicte |
|---|---|---|---|
| `plan/gantt/` | `plan.gantt` (:546) | **2** (`Planning.jsx`, 30 referències internes al resultat) | **VIU** |
| `plan/reorder/` | `plan.reorder` (:557) | **1** | **VIU** |
| `plan/eligible-attendees/` | `plan.eligibleAttendees` (:569) | **2** | **VIU** |
| `calendar/events/` | `calendar.events` (:577) | **3** (`PlanningCalendar`, `Dashboard`×2) | **VIU** |
| `company-calendar/` | `companyCalendar` (:582) | **31** | **VIU** |
| `users/<id>/jornada/` | `jornada` (:590) | **2** | **VIU** |
| `plan/compute/` | `plan.compute` (:549) | **0** | 🚩 **SENSE CONSUMIDOR** |
| `plan/preview/` | `plan.preview` (:551) | **0** | 🚩 **SENSE CONSUMIDOR** |
| `plan/apply/` | `plan.apply` (:553) | **0** | 🚩 **SENSE CONSUMIDOR** |
| `plan/snapshots/` | `plan.snapshots` (:554) | **0** | 🚩 **SENSE CONSUMIDOR** |
| `plan/eligible-technicians/` | `plan.eligibleTechnicians` (:561) | **0** | 🚩 **SENSE CONSUMIDOR** |
| `plan/assign-batch/` | `plan.assignBatch` (:565) | **0** | 🚩 **SENSE CONSUMIDOR** |
| `plan/current/` | **no hi és** a `endpoints.js` | **0** | 🚩 **NI DEFINIT** |
| `absencies/` | `absencies` (:595) | **0** | 🚩 **SENSE CONSUMIDOR** |

### 🔎 Si la barra del Gantt passés de TASCA a RONDA — nodes que llegeixen «tasca» com a unitat

Enumeració, sense proposar disseny:

1. `planning/scheduler_service.py:117` `schedule` — planifica **per tasca**; `placements` és una llista de `task_id`
2. `planning/scheduler_service.py:236-250` — agrega `Model.predicted_start/end` com a `min/max` **de les tasques del model**
3. `planning/plan_service.py:42` `_technician_queue` — la cua és una llista de `ModelTask`
4. `planning/plan_service.py:121` `_pin_block` — fixa **una tasca** per la seva `estimated_minutes`
5. `planning/plan_service.py:130` `preview` / `:171` `apply` — el paràmetre és `task_id`
6. `planning/models.py:72` `TechnicianQueueOrder` — ordre per `(profile, **model**)`, no per tasca ni per ronda
7. `planning/views.py:724` `gantt_view` — barra per MODEL, calculada des de `planned_end` de les tasques (`:773-780`)
8. `planning/views.py:238-284` `calendar_events_view`, font `tasca` — un event per `ModelTask`
9. `tasks/views_b.py:106` `by_model` — `plan_start = Min('planned_start')` de les no-Done
10. `tasks/views_b.py:100` `_DEFAULT_ORDER` — `Coalesce('plan_start','plan_start_all')`
11. `tasks/models.py:200-208` `planned_start/end/locked` — camps **de la tasca**
12. `tasks/services_scheduling.py:15` `reagenda_tasca` — fixa **una tasca**
13. `frontend/src/pages/Planning.jsx` — llegeix `.planned_start`, `.planned_end`, `.estimated_minutes`, `.status`, `.task_type_code`, `.assignee`, `.finished_at`
14. `tasks/models.py:647-668` `PlanSnapshot.result` — el JSON conté `models[<id>].predicted_*` i `placements[].task_id`

**Corpus staging:** 11 tasques amb `planned_start`, **0** amb `planned_locked`, 16 amb `assignee`,
**0** files a `TechnicianQueueOrder`, 1 `PlanSnapshot`.

---

## R10 · SUPERFÍCIES VIVES

### `kanban_state` — el càlcul exacte

**`backend/fhort/tasks/views_b.py:193-208`**, funció local dins de `by_model`:

```python
def kanban_state(pending, paused, in_progress, done):
    if in_progress > 0: return 'open'      # feina viva mana sobre l'estàtica
    if paused > 0:      return 'paused'
    if pending > 0:     return 'pending'
    return 'done'
```

Els quatre comptadors surten de `Count('id', filter=Q(status=…))` sobre **TOTES** les `ModelTask`
visibles del model (`:170-176`) — sense cap partició per ronda, `origen` ni `work_order`.

**Dos filtres més al mateix endpoint:**
- `:187` — `agg.filter(plan_start_all__isnull=False)` (C4a): **un model sense cap tasca amb
  `planned_start` no existeix al Board**;
- `:189-191` — sense `?all=true`, s'oculten els models on `pending+paused+in_progress == 0`.

**Qui el consumeix:** `frontend/src/pages/Dashboard.jsx` (2 lectures de `.kanban_state`, 4 de
`.counts`).

### Superfícies i camps de `ModelTask` que llegeixen (llista literal)

| Superfície | Fitxer | Camps literals |
|---|---|---|
| Board del Dashboard | `frontend/src/pages/Dashboard.jsx` | del payload de `by-model`: `model_id`, `model_codi`, `model_nom`, `fase`, `counts.{pending,paused,in_progress,done}`, `kanban_state`, `prioritat`, `temporada`, `estat`, `data_objectiu`, `responsable_id`, `reanchored_by_start` |
| Pla de treball | `frontend/src/components/model/WorkPlan.jsx` | `id`, `status`, `task_type_code`, `task_type_name`, `assignee_id`, `assignee_nom`, `temps_consumit_min`, `tipus_extern`, `origen`, `off_recipe`, i `paused_task_id` de la resposta de transition (`:234`) |
| Arbre de tasques | `frontend/src/components/model/TaskTree.jsx` | `status`, `assignee_id`, `assignee_nom`, `task_type_code`, `temps_consumit_min`, `id` |
| Accions de sessió | `frontend/src/components/model/SessionActions.jsx` | `id` (×2) |
| Compositor del dashboard del model | `backend/fhort/models_app/views.py:4329` → `:4408-4426` | `id`, `task_type(.name)`, `task_type_code`, `task_type_name`, `default_order`, `status`, `assignee_id`, `assignee_nom`, `temps_consumit_min`, `obertures`, `order`, `origen`, `off_recipe`. **No exposa `ronda` ni `motiu`** |
| Registre d'activitat | `backend/fhort/tasks/views_b.py:361` `model_task_log_view` | de `TaskTransition`: `id`, `task_type` (code), `from_status`, `to_status`, `by`, `auto`, `at`. **Cap camp de ronda.** Cap de 300 files |
| Planning (Gantt) | `frontend/src/pages/Planning.jsx` | `id`, `assignee`, `status`, `task_type_code`, `planned_start`, `planned_end`, `estimated_minutes`, `model_codi`, `finished_at` |
| Pestanyes del ModelSheet | `frontend/src/pages/ModelSheet.jsx` | via `caraObrirTasca(vigent, jo)` (`:519,540`): `albaranada`, `status`, `es_lliurable`, `obert_per`, `assignee`; i `model.ronda_oberta` (`:1158`), `model.lliurable_ronda_n` (`:1841`) |
| Llista de models | `frontend/src/pages/Models.jsx:340` | `m.lliurable_ronda_n` |

### 🔎 Existeix un marcador de «model acabat» que el tregui del board?

**Mesurat:**

| Candidat | Camp | Escriptor | Files a staging |
|---|---|---|---|
| **El filtre per defecte de `by_model`** | derivat (`pending+paused+in_progress == 0`) | cap: es calcula a la query (`views_b.py:189-191`) | — |
| **`plan_start_all IS NULL`** (C4a) | derivat de `planned_start` | `scheduler_service` | 4 models tenen tasques planificades → **28 dels 32 models no són al board** |
| `Model.estat = 'Tancat'` | `models_app/models.py:242` | **CAP escriptor viu** (`advance_phase_gate` va deixar d'escriure'l, `services_d.py:52-54`) | **0** |
| `Model.data_tancament` | `models_app/models.py:268` | cap escriptor localitzat | **0** |
| `Model.fase_actual = 'TOP'` | `:243` | `advance_phase_gate` | **0** |
| `Model.consumption_started_at` | `:245` | `_meritar_model` | 3 |
| `Model.reanchored_by_start` | — | `open_model_task_view:667` | 4 |

**Resposta de fet: NO hi ha cap marcador PERSISTIT de «model acabat».** El que treu un model del
board és un **derivat** (cap tasca viva) o la manca de planificació. `estat='Tancat'` existeix com a
choice i **no l'escriu ningú**: 0 files.

---

## R11 · ON ANCORAR `Ronda` i `Entrega`

### Apps candidates i HEAD de migracions (schema `fhort`, foto 17:18 UTC)

| App | Última migració aplicada | Cua |
|---|---|---|
| **`tasks`** | `0050_j_consulta_marca_escriptura` | **BUIDA** — i **`Ronda` ja hi viu** (`tasks_ronda`) |
| `models_app` | `0086_tram_f_breaks_intervals` | BUIDA |
| `fitting` | `0028_e2_b1_presa_at` | BUIDA |
| `commerce` | `0021_quotelinemodelintent` | BUIDA |
| `planning` | `0002_technicianqueueorder` | BUIDA |
| `pom` | `0083_alies_marca_edicio` | BUIDA |
| `accounts` | `0008_tenantconfig_legal_footer` | — |
| `backoffice` (public) | `0011_backfill_actor_schema_fhort` | — |
| `tenants` | `0007_tenantlink` | — |
| `patterns` | `0014_alter_patternpiece_rol_origen` | — |
| `files` | `0002_delete_fitxerversio` | — |
| `i18n_content` | `0001_initial` | — |

### Inventari del que ja té forma d'entrega o de lliurament

| Candidat | Fitxer:línia | Cicle | Podria ser «contingut d'entrega» sense canviar-lo? |
|---|---|---|---|
| **`commerce.DeliveryNote`** (albarà) | `commerce/models.py:666-724` | `DRAFT → ISSUED → INVOICED` | **SÍ, i ja hi és mig lligat.** `DeliveryNoteLine.model_task` (FK, `:748`) i `.model` (`:766`) existeixen; `te_paret_albara` (`services_c.py:84`) ja converteix «albaranada» en paret. Té `issued_by`, `invoiced_at/by`, `document_number`. **El que li falta és el DESTINATARI de la ronda** (té el del document, no el de la volta) i que **no és per model, és per client** |
| `commerce.DeliveryNoteLine` | `commerce/models.py:725-790` | — | **SÍ**: `line_kind ∈ {TASK, EXTRA, DEDUCTION, EXPENSE, MANUAL}`, `internal_minutes`, `visible` |
| **`tasks.Production`** | `tasks/models.py:426-450` | `Requested → InProgress → Delivered` (`services_e.py:33-35`) | **SÍ** com a fet de confecció (té `supplier`, `expected_at`, `delivered_at`, `phase`) — però és **cap al taller**, no cap al client. **0 files a staging** |
| **`models_app.ModelFitxer`** | `models_app/models.py:374-450` | `TIPUS_CHOICES` (11), `is_current`/`versio` | **SÍ**: `TECHSHEET` (.ftt) i `EXPORT` (PDF) són literalment els productes que una volta lliura |
| **Exportació de fitxa/PDF** | `POST /api/v1/ftt-documents/<id>/export/` (`models_app/urls.py:206`) | — | **SÍ**: genera el `ModelFitxer` tipus `EXPORT` |
| `fitting.FittingSession` (acta) | `fitting/models.py:291` | `Programada→Oberta→Tancada/Anullada` | **NO com a entrega**: és un esdeveniment intern, sense destinatari extern |
| `TaskType.es_lliurable` | `tasks/models.py:118-122` | flag | **SÍ**: **ja declara** quines tasques produeixen un lliurable. 5 de 15: `pattern_digit`, `pattern_cad`, `tech_sheet`, `scaling`, `marking` |
| `services_r.rondes_lliurables` | `services_r.py:229` | derivat | **SÍ**: retorna `[{seq, motiu, lliurat_el}]` amb `lliurat_el = Max(finished_at)` dels lliurables |
| `models_app.ConsumptionRecord` | `models_app/models.py:1360` | immutable | **NO**: és l'albarà de CONSUM SaaS, un mèrit per model/set, no una entrega de feina |

**Corpus staging:** `DeliveryNote` 2 (1 DRAFT, 1 ISSUED) · `DeliveryNoteLine` 4 · **línies amb
`model_task`: 0** · **`ModelTask` albaranades (ISSUED/INVOICED): 0** · `Production` 0.

### Contracte / LiniaContracte — **només inventari**

⚠️ **DIVERGÈNCIA:** viuen al **schema TENANT** (`fhort.models_app_contracte`,
`fhort.models_app_liniacontracte`), no a `public`/`backoffice`.

| Taula | Model | Camps | Files (fhort) | Escriptors vius |
|---|---|---|---|---|
| `models_app_contracte` | `models_app/models.py:14-26` | `nom`, `referencia`, `data_inici`, `data_fi`, `actiu` | **0** | només `ContracteSerializer` (`models_app/serializers.py:215-217`); FK des de `Model` (`models.py:278`) |
| `models_app_liniacontracte` | `models_app/models.py:29-40` | `contracte` (FK), `descripcio`, `quantitat`, `actiu` | **0** | idem; FK des de `Model` (`models.py:285`) |

A `public` hi ha **`backoffice_tenantcontract`** i **`backoffice_contractline`**
(`backoffice/models.py:237`: «Contracte SaaS entre FHORT i un tenant»), que són **una altra cosa** i
no tenen relació amb la ronda. Consumidor: `backoffice/billing_service.py:57`.

---

## R12 · VOCABULARI, i18n I TOKENS

### i18n — claus existents de ronda/entrega/lliurament

**PARITAT TOTAL: 4705 claus a `ca.json`, 4705 a `en.json`, 4705 a `es.json`.**

| Clau | ca | en | es |
|---|---|---|---|
| `obrir_tasca.lliurada_titol` | «{{tasca}}» ja està tancada i lliurada | is closed and delivered | ya está cerrada y entregada |
| `obrir_tasca.lliurada_cos` | ✅ | ✅ | ✅ |
| `obrir_tasca.lliurada_ronda` | Obrir ronda {{n}} · nova mostra | Open round {{n}} · new sample | Abrir ronda {{n}} · nueva muestra |
| `obrir_tasca.lliurada_ronda_nota` | ✅ | ✅ | ✅ |
| `obrir_tasca.lliurada_correccio` | ✅ | ✅ | ✅ |
| `obrir_tasca.lliurada_correccio_nota` | ✅ | ✅ | ✅ |
| `obrir_tasca.ronda_error` | ✅ | ✅ | ✅ |
| `lliurable.badge` | Lliurable · ronda {{n}} | Deliverable · round {{n}} | Entregable · ronda {{n}} |
| `lliurable.badge_titol` | ✅ | ✅ | ✅ |
| `lliurable.compacte` | Lliurable R{{n}} | Deliverable R{{n}} | Entregable R{{n}} |
| `lliurable.historic` | Lliurades: {{llista}} | Delivered: {{llista}} | Entregadas: {{llista}} |
| `lliurable.motiu_correccio` | R{{n}} correcció | R{{n}} correction | R{{n}} corrección |
| `lliurable.motiu_nova_mostra` | R{{n}} mostra | R{{n}} sample | R{{n}} muestra |

**Vocabulari comercial adjacent (ja existent, altre domini):** `deliverynotes.*` (albarà),
`…delivered_at` (`ca`: lliurament · `es`: entrega · `en`: delivered).

🔑 **El vocabulari CA fixat: «ronda» = volta · «lliurable» = producte acabat · «lliurar/entregar» =
l'acte.** El backend fa servir `Ronda.MOTIU_NOVA_MOSTRA` / `MOTIU_CORRECCIO`, i la UI ho tradueix a
«nova mostra» / «correcció».

### Tokens CSS — existeixen? amb quin nom real?

| El mockup dona per fet | Existeix a `frontend/src/index.css`? | Nom real |
|---|---|---|
| `--sel` | ✅ | `--sel: #f7f5f2` (`:66`) — «SELECCIÓ: fila/contenidor triat, sempre amb filet d'or 3px» |
| `--ok` | ✅ | `--ok: #2e7d32` (`:124`) + `--ok-bg: #e9f3ea` (`:125`) |
| `--gold` | ✅ | `--gold: #c27a2a` (`:24`) + `--gold-l`, `--gold-pale`, `--gold-border` (`:25,26,31`) |
| `--border` | ✅ | `--border: #e0d5c5` (`:39`) — «432 usos en 93 fitxers» |
| **`--paused`** | ❌ **NO EXISTEIX** | cap token d'estat «pausat». El més proper: `--warn` `#854f0b` / `--warn-bg` `#faeeda` (`:126-127`) o el trio de la norma `--warn-state`/`--warn-state-bg`/`--warn-ink` |
| **`--progress`** | ❌ **NO EXISTEIX** | el més proper: `--tram: #0969da` (`:141`, identitat del tram declarat) o `--accio`/`--accio-hover` |
| **`--soft`** | ❌ **NO EXISTEIX com a tal** | existeixen `--line-soft` i `--text-soft` |

**Inventari complet de tokens definits** (57): `--accio --accio-hover --base-hairline --bg-card
--bg-main --bg-muted --bg-page --bg-sidebar --border --charcoal --col-talla --err --err-bg
--fila-activa --fila-capa --fila-capa-activa --fila-neix --fs-body --fs-caption --fs-display
--fs-h1 --fs-h2 --fs-h3 --fs-label --gate --gate-bg --gold --gold-border --gold-l --gold-pale
--gray --gray-l --intern-bg --line --line-soft --llista-tria-max-h --model-band --ok --ok-bg
--panel --pdf-accent --placed-bg --r-card --r-ctrl --r-pill --sel --text-faint --text-main
--text-muted --text-soft --tram --tram-sel --warn --warn-bg --warn-ink --warn-state
--warn-state-bg --white`

⚠️ `--gold-pale` porta nota d'ELIMINACIÓ progressiva del sistema (`ui/Badge.jsx`, NORMA §1).

### Icones Tabler disponibles per a l'entrega (outline only)

Paquet: **`@tabler/icons-react ^3.44.0`** (`package.json:18`), més el webfont (classes `ti ti-*`).

**Ja EN ÚS al producte** (i per tant sense risc de dissonància): `ti-package`, `ti-package-export`,
`ti-send`, `ti-file-check`, `ti-file-invoice`, `ti-file-download`, `ti-history`, `ti-repeat`,
`ti-refresh`, `ti-checkbox`, `ti-circle-check`.

**Disponibles al paquet i NO usades encara** (totes outline): `IconTruckDelivery`, `IconTruck`,
`IconReceipt`, `IconSignature`, `IconCertificate`, `IconClipboardCheck`, `IconFileExport`,
`IconSend2`, `IconRotate`, `IconArrowsExchange`.

⚠️ Llei de la casa (`CLAUDE.md`): **outline only**, mai `-filled`; única excepció amb acta
`ti-pointer-filled`.

### Component `ui/` reutilitzable per a pastilles/xips/subtabs

| Component | Fitxer | Contracte | Nota |
|---|---|---|---|
| **`Badge`** | `frontend/src/components/ui/Badge.jsx:20` | 5 variants; **fons suau + tinta + VORA FINA del mateix color, sempre píndola** (NORMA §1) | «21 fitxers el munten». `gold` ja NO és semàfor |
| **`Xip`** | `frontend/src/components/ui/Xip.jsx` | **TRES estats i cap més**: repòs / seleccionat (`verd`→`--ok-bg` o `--sel`+filet d'or) / hover | Punt únic: abans n'hi havia dues còpies amb el mateix defecte. Porta l'acta del **quart estat fantasma** (shorthand vs longhand) |
| **`SubTabs`** | `frontend/src/components/ui/SubTabs.jsx` | `{items:[{key,label,icon?,badge?}], actiu, onTria, dreta?}`; `label` és **clau i18n** (es tradueix a dins) | **Tabs amb subratllat d'or**, mai píndoles (NORMA §8b-bis). `badge` nul o 0 → no es pinta |
| `BadgeLliurable` | `frontend/src/components/model/BadgeLliurable.jsx:15` | `{rondes, compacte, locale}` | **JA construït per a la ronda** |
| Altres `ui/` | `Card`, `Modal`, `Table`, `TaulaLlista`, `StatCard`, `PageMenu`, `Feedback`, `TimerWidget`, `PdfButton`, `Contenidor`, `Center`, `FileDropCard`, `AvisDiccionari`, `TranslatableField` | — | — |

---

## R13 · MAPA DE TESTS — el gate quirúrgic

⛔ **CAP TEST EXECUTAT.** Els recomptes són de `grep -c "    def test"`, no d'una correguda.

### Cobertura per fitxer de producte amb veredicte **ES TOCA**

| Fitxer de producte | Ruta de test (`manage.py test <ruta>`) | nº tests |
|---|---|---|
| `tasks/services_r.py` | `fhort.tasks.test_ronda` | **29** |
| | `fhort.tasks.test_tasca_vigent` | **7** |
| | `fhort.tasks.test_contracte_f2` | **14** |
| | `fhort.tasks.test_crono_declarat` | **11** |
| | `fhort.tasks.test_temps_declarat` | **13** |
| `tasks/services_c.py` | `fhort.tasks.test_stop_encadenat` | **6** |
| | `fhort.tasks.test_j_consulta_treball` | **25** |
| | `fhort.tasks.test_exclusio_handoff` | **13** |
| | `fhort.tasks.test_guard_tasca_oblidada` | **23** |
| | `fhort.tasks.test_batec_escriptura` | **8** |
| | `fhort.tasks.test_batec_sobre_pausada` | **6** |
| | `fhort.tasks.test_meritacio_batec` | **7** |
| | `fhort.tasks.test_recompute_welford` | **8** |
| | `fhort.tenants.tests_canal_estat` | **10** |
| `tasks/services_batec.py` | `fhort.tasks.test_batec_escriptura` · `test_batec_sobre_pausada` · `test_meritacio_batec` · `test_set1_meritacio` (6) · `test_recompute_welford` · `test_stop_encadenat` | 8+6+7+6+8+6 |
| `tasks/services_i.py` | `fhort.tasks.test_higiene_temps` | **6** |
| | `fhort.tasks.test_recompute_welford` · `test_j_consulta_treball` · `test_stop_encadenat` · `test_temps_declarat` | 8+25+6+13 |
| `tasks/services_g.py` | `fhort.tasks.tests` | **14** |
| | `fhort.models_app.test_ia_routing_i_cost` (11) · `test_set2_t2bis_modelgarment` (29) · `test_set2_t8_import_per_prenda` (18) · `fhort.fitting.test_q8_banc_taules_fitxa` (4) | (indirectes) |
| `tasks/views_b.py` | `fhort.tasks.tests` (14) · `fhort.tasks.tests_self_customer` (11) · `fhort.tasks.test_set1_composicio` (8) · `fhort.models_app.test_gate_mesures_pom_task` (9) · `fhort.tenants.tests_encarrecs` (25) | |
| `tasks/serializers_b.py` | `fhort.tasks.test_contracte_f2` (14) · `fhort.tasks.test_cataleg_visible` (3) | |
| `tasks/models.py` | **57 fitxers** el toquen (v. §llista sota) | |
| `tasks/services_d.py` | `fhort.fitting.test_d3121_veredicte` (16) · `fhort.models_app.test_c3_d_derivacio` (13) · `test_capa_comporta_c1` (6) · `test_instancia_comporta_cins` (13) · `test_set2_r3_germanes_garment` (3) | |
| `models_app/views.py` (`_assegura_pom_task_oberta`) | `fhort.models_app.test_gate_mesures_pom_task` | **9** |
| `models_app/services_size_check.py` | `fhort.models_app.test_size_check_completa_linies` | **8** |
| | `fhort.models_app.test_c3_e_connexio_derivacio` (7) · `test_escriptors_instancia_cins` (9) · `test_set2_t5_escriptors` (20) · `test_set2_r3_germanes_garment` (3) · `fhort.fitting.test_g6_estalitud` (13) | |
| `planning/plan_service.py` | `fhort.tasks.tests` | **14** (només `:174-259`) |
| `planning/scheduler_service.py` | `fhort.tenants.tests_encarrec_camps` | **3** |
| `planning/views.py` (`calendar_events_view`) | **CAP** | **0** |
| `tasks/views_b.py::by_model` / `kanban_state` | **CAP** | **0** |
| `tasks/views_b.py::model_task_log_view` | **CAP** | **0** |
| `tasks/services_scheduling.py::reagenda_tasca` | **CAP** | **0** |
| `fitting/services.py` | `fhort.fitting.test_e1_cicle_complet` (4) · `test_e1_guard_partit` (12) · `test_e1_r2_estructural` (5) · `test_e2_b1_marca_de_presa` (7) · `test_e3_cicle_mesurar_set` (5) · `test_d3121_veredicte` (16) · `test_s45_b_presa_sense_propagat` (11) · `test_set2_t5c_linies_per_garment` (6) · `fhort.pom.test_g6_grading_gates` (7) · `fhort.pom.test_tram_f_intervals` (47) | |

### 🚨 ELS TESTS QUE ES TRENCARAN — un per un, amb el motiu

#### (a) Assumeixen UNA SOLA `ModelTask` per `(model, task_type)`

| Test | Línia | Motiu exacte |
|---|---|---|
| `fhort.tenants.tests_canal_estat` | `tests_canal_estat.py:189` | `ModelTask.objects.get(model_id=…, task_type__code='ESCA')` — **`.get()` pelat**: amb una segona tasca del mateix code peta amb `MultipleObjectsReturned` |
| `fhort.planning.tests` | `planning/tests.py:84, 110, 117` | `assertTrue(ModelTask.objects.filter(model=…, task_type=…).exists())` — no peta, però **deixa de discriminar** quina volta ha entrat al pla |
| `fhort.models_app.test_set2_t5_escriptors` | `:308, :475` | `ModelTask.objects.get_or_create(model=…, task_type=…)` — el `get_or_create` **peta** amb 2+ files (`MultipleObjectsReturned`) |
| `fhort.models_app.test_origen_no_es_efecte_secundari` | `:78` | idem `get_or_create` |
| `fhort.models_app.test_c4_escriptura_germanes` | `:101` | idem `get_or_create` |
| `fhort.tasks.test_ronda` | `:295` | `ModelTask.objects.filter(model=…, task_type=…).delete()` — **esborra totes les voltes**, cosa que avui és el que vol el test; si el segell prohibís esborrar tasques entregades, canvia |

⚠️ Nota: els 3 `get_or_create` són **fixtures de setUp**, no assercions. Es trenquen només si el
banc del test arriba a tenir més d'una tasca del mateix tipus.

#### (b) Assumeixen que `Done→InProgress` és legal

| Test | Línia | Motiu |
|---|---|---|
| `fhort.tasks.test_batec_sobre_pausada` | `:178` | `assertTrue({'Paused','Done'} <= ALLOWED['InProgress'])` — asserció **directa sobre la taula** |
| `fhort.tasks.test_stop_encadenat` | `:122` | `assertNotIn('Done', ALLOWED['Paused'])` — asserció sobre la taula |
| `fhort.tasks.test_j_consulta_treball` | `:269-271` | `test_amb_el_GEST_si_que_es_reobre` — POST `open-task` amb `{'reobrir': True}` **espera 200 i reobertura** |
| `fhort.tasks.test_recompute_welford` | `:121` | «`record_actual_time` es crida a CADA →Done: re-tancar aporta una altra mostra» — **depèn de poder reobrir** per fabricar el segon `→Done` |
| `fhort.tasks.test_recompute_d3` | `:4-5` | tot el fitxer parteix de «Com que `Done→InProgress` és permesa (rectificació), cada re-tancament hi deixava una mostra nova» |
| `fhort.models_app.test_gate_mesures_pom_task` | (9 tests) | `_assegura_pom_task_oberta` reobre una `Done` per disseny (`models_app/views.py:1972-1975`) |
| `fhort.tasks.test_batec_escriptura` | `:122` | comprova que una `Done` **albaranada** no es reobre — si el segell s'hi afegeix, el motiu del refús canvia (`code` diferent) |

#### (c) Assumeixen el recompte de `by-model` / `kanban_state`

**CAP.** `grep -rn "kanban_state\|by-model" --include="test*.py"` → **0 resultats**.
🚨 **`by_model` (el board sencer, 133 línies) no té ni un test.**

#### (d) Assumeixen la clau de la cel·la Welford `(garment_type_item, task_type)`

| Test | Línia | Motiu |
|---|---|---|
| `fhort.tasks.test_recompute_welford` | `:100` | `TaskTimeEstimate.objects.get(garment_type_item=self.item, task_type=self.tt)` — **`.get()` per la clau exacta** |
| `fhort.tasks.test_stop_encadenat` | `:171-172, :186` | `filter(garment_type_item=…, task_type=…)` i `.get(...)` |
| `fhort.tasks.tests` | `:45-46` | `TaskTimeEstimate.objects.create(garment_type_item=item, task_type=self.task, …)` (fixtures dels 4 graons) |
| `fhort.tasks.test_recompute_d3` | `:80` | `.filter(model__garment_type_item=self.item, task_type=self.tt)` |

Si la clau guanyés un tercer eix (ronda, o «primera volta vs correcció»), **els quatre** deixarien
de trobar la cel·la o en trobarien una altra.

#### (e) Assumeixen la meritació a la primera tasca

| Test | Línia | Motiu |
|---|---|---|
| `fhort.tasks.test_set1_meritacio` | `:79-133` | `assertEqual(ConsumptionRecord.objects.count(), 1)` repetit ×6 — **UN mèrit per SET**, i que repetir el gest no en crea cap més |
| `fhort.tasks.test_meritacio_batec` | (7 tests) | tot el fitxer fixa que **el gallet és l'escriptura**, no l'obertura |
| `fhort.backoffice.tests_actor_schema` | `:24-42` | envia el signal directament; comprova `actor_schema` |

Si la ronda meritès, `count() == 1` passaria a `== n_rondes` i **tots** els asserts de
`test_set1_meritacio` caurien.

#### (f) Assumeixen la forma dels events de calendari

**CAP.** `grep -rn "calendar/events" --include="test*.py"` → **0 resultats**.
🚨 **`calendar_events_view` (296 línies, 3 fonts) no té ni un test de backend.** L'única cobertura
és visual, via els fums de `ops/qa/*.mjs`.

#### (g) Assumeixen la reagenda de size check

**CAP test la toca directament.** `grep -rn "reagenda\|data_represa" --include="test*.py"` → **0**.
Cobertura indirecta: `fhort.models_app.test_size_check_completa_linies` (8) exercita
`open_size_check`/`resolve_size_check` però **no la branca de reagenda**.

### Bancs de guàrdia i artefactes de QA que hi pengen

| Artefacte | Què verifica | Toca la ronda? |
|---|---|---|
| `ops/qa/banc_paritat_1383.py` | **EL GATE dels sprints de motor** (fix A · E · F). Read-only, model 1383, tenant `fhort`. Corre amb `PGOPTIONS='-c default_transaction_read_only=on'` | **NO** (motor de graduació) |
| `ops/qa/qa_j_consulta_treball.py` | **Els 4 casos de J (consulta ≠ treball) contra el banc 1383 VIU.** ⚠️ **AQUESTA QA ESCRIU**: obre tasques, escriu una mesura i mou l'estat de la 377; restaura el que canvia. No va per nginx+gunicorn (JWT), usa `APIClient` + `force_authenticate` | **SÍ, indirectament**: exercita `open-task`, `sortir-sense-escriptura` i `caraObrirTasca` |
| `ops/qa/qa_jbis_fitxa_consulta.py` | J-bis sobre la fitxa | SÍ, indirectament |
| `ops/qa/qa_q4_acta_i_sortida.py` | Acta de sessió Tancada + **el full `/fittings/<s>/full/<m>`** + «Gravar i tornar». Corre sobre el bundle REAL de `frontend/dist` amb fixture d'API | **SÍ**: el full de fitting és candidat a «contingut d'entrega» |
| `ops/qa/qa_auditoria_computats.py` · `qa_bidireccional.py` | conformitat mesurada (Bloc A) | NO |
| `ops/qa/qa_mount_modelsheet.py` | muntatge del ModelSheet | SÍ, indirectament (hi viu `ObrirTascaDialog`) |
| `ops/qa/qa_xip_quatre_estats.py` | els 4 estats del `Xip` de `ui/` | **SÍ** si el tram usa `Xip` |
| Model de QA `clone_model_for_qa` | `models_app/management/commands/clone_model_for_qa.py` — buida `consumption_started_at`, `fase_actual='Proto'`, `estat='Nou'`, `SizeFitting numero=1` | **SÍ**: qualsevol camp nou de ronda hi ha de decidir si es clona |
| Banc S45 model **pk 1383** · banc tram F **pk 1384** (`QA-TRAMF-0001`) | bancs vius a staging | motor, no ronda |

---

### 🎯 GATE PROPOSAT

| RUTES DE TEST MÍNIMES (cobreixen el canvi) | RUTES DE MÒDUL (si es toca codi compartit) | QUAN CALDRIA LA SENCERA |
|---|---|---|
| **Bloc RONDA/IDENTITAT** — 50 tests<br>`fhort.tasks.test_ronda` (29)<br>`fhort.tasks.test_tasca_vigent` (7)<br>`fhort.tasks.test_contracte_f2` (14) | `fhort.tasks` (**~200 tests**, 21 fitxers) | — |
| **Bloc MÀQUINA D'ESTATS** — 63 tests<br>`fhort.tasks.test_stop_encadenat` (6)<br>`fhort.tasks.test_j_consulta_treball` (25)<br>`fhort.tasks.test_exclusio_handoff` (13)<br>`fhort.tasks.test_guard_tasca_oblidada` (23)<br>*(si es toca `ALLOWED` o `transition_task`)* | `fhort.tasks` + `fhort.tenants.tests_canal_estat` (10) | Si es toca `ALLOWED`: la sencera, perquè `transition_task` és cridada des de 4 apps |
| **Bloc BATEC/MERITACIÓ** — 35 tests<br>`fhort.tasks.test_batec_escriptura` (8)<br>`fhort.tasks.test_batec_sobre_pausada` (6)<br>`fhort.tasks.test_meritacio_batec` (7)<br>`fhort.tasks.test_set1_meritacio` (6)<br>`fhort.backoffice.tests_actor_schema` (5)<br>`fhort.tasks.test_set1_composicio` (8) | `fhort.tasks` + `fhort.backoffice` | Si es toca la frontera `public`↔`tenant` (signal/receiver): **la sencera** — el receiver fa `schema_context('public')` |
| **Bloc TEMPS/WELFORD** — 60 tests<br>`fhort.tasks.test_recompute_welford` (8)<br>`fhort.tasks.test_recompute_d3` (9)<br>`fhort.tasks.test_higiene_temps` (6)<br>`fhort.tasks.test_temps_declarat` (13)<br>`fhort.tasks.test_crono_declarat` (11)<br>`fhort.tasks.tests` (14) | `fhort.tasks` | Si es toca `TRAMS_SANS` o `MAX_MINUTS_TRAM`: **la sencera** — d'aquesta línia pengen albarà, consum i tots els agregadors |
| **Bloc POM/SIZE CHECK** — 17 tests<br>`fhort.models_app.test_gate_mesures_pom_task` (9)<br>`fhort.models_app.test_size_check_completa_linies` (8) | `fhort.models_app` (**~600 tests**, 60 fitxers) | Si es toca `BaseMeasurement` o la derivació: `fhort.models_app` + `fhort.pom` |
| **Bloc PLANIFICACIÓ** — 17 tests<br>`fhort.planning.tests` (7)<br>`fhort.tasks.tests` (14, subconjunt `:174-259`) | `fhort.planning` + `fhort.tasks` | Si es toca `schedule()`: + `fhort.fitting` (4 callers de `recompute_for_technicians`) |
| **Bloc FITTING** — 113 tests<br>`fhort.fitting` sencer (16 fitxers) | `fhort.fitting` + `fhort.pom.test_g6_grading_gates` (7) + `fhort.pom.test_tram_f_intervals` (47) | Si es toca `close_piece_fitting` o `seal_model_grading`: **la sencera** |
| **Bloc COMERCIAL/ENTREGA** — 46 tests<br>`fhort.commerce.test_gate_comercial` (17)<br>`fhort.commerce.test_batch_assign` (7)<br>`fhort.commerce.test_intents_reattach` (13)<br>`fhort.commerce.test_unassign` (6)<br>`fhort.commerce.test_orphan_iva` (3) | `fhort.commerce` | Si es toca `DeliveryNote.status` o `te_paret_albara`: **la sencera** — el guard el llegeixen `transition_task`, `batec_escriptura`, `open-task` i el serializer |
| 🚨 **SENSE COBERTURA — cal escriure test NOU abans de tocar:**<br>· `by_model` / `kanban_state` (`views_b.py:106-236`)<br>· `calendar_events_view` (`planning/views.py:214-509`)<br>· `model_task_log_view` (`views_b.py:361`)<br>· `reagenda_tasca` (`services_scheduling.py:15`) | — | — |

**Quan caldria LA SENCERA (`python manage.py test fhort`, ~1.900 tests, 12 apps):**
① si es toca `tasks/models.py` (57 fitxers de test l'importen) · ② si es toca `ALLOWED` o
`transition_task` · ③ si es toca `TRAMS_SANS`/`MAX_MINUTS_TRAM` · ④ si s'afegeix una migració a
`tasks` o `models_app` · ⑤ si es toca la frontera `public`↔`tenant`.

⚠️ **Recordatori operatiu** (memòria, no mesurat avui): `unattended-upgrades` reinicia Postgres cap
a les **06:39 UTC** i mata una correguda llarga. I una suite morta a mitges deixa
`schema_name='test'` i produeix ~68 errors aliens a la següent.
⛔ **El temps de correguda es declararà quan l'Agus autoritzi la correguda. Aquí no se n'ha corregut cap.**

---

## R14 · DIMENSIONAMENT

> ⚠️ **TOTES LES XIFRES D'AQUEST BLOC SÓN D'STAGING** (`178.105.48.204`, BD `ftt_staging`, schema
> `fhort`), foto del **2026-08-23 17:18:34 UTC**. **NO són les de PROD.** Les que dimensionen la
> feina real (els 81 models, el R1 retroactiu) són de **PROD** i **es mesuraran a part**.
> **No barrejar mai xifres de dues fotos.**

| Entitat | n (STAGING) |
|---|---|
| `models_app.Model` | **32** |
| `tasks.ModelTask` | **16** (16 `prevista`, **0** `ad_hoc`) |
| `tasks.Ronda` | **0** (0 obertes) |
| `ModelTask` amb `ronda` / `mare` / `motiu='correccio'` | **0 / 0 / 0** |
| `tasks.TaskTransition` | **184** |
| `tasks.TimerEntrada` | **102** |
| `tasks.GateEvent` | **0** |
| `tasks.Production` | **0** |
| `tasks.PlanSnapshot` | **1** |
| `tasks.TaskTimeEstimate` | **468** (28 amb `n>0`, **1** amb `n>=5`) |
| `tasks.TimeSeed` | **8** |
| `tasks.TaskType` | **15** (5 `es_lliurable`, 4 `Externa-lliure`, 2 no `visible`) |
| `fitting.FittingSession` | **9** |
| `fitting.PieceFitting` | **9** |
| `fitting.SizeFitting` | **33** |
| `fitting.GradingVersion` | **16** |
| `commerce.DeliveryNote` | **2** (1 DRAFT, 1 ISSUED) |
| `commerce.DeliveryNoteLine` | **4** (**0** amb `model_task`) |
| `models_app.ConsumptionRecord` | **2** |
| `models_app.Contracte` / `LiniaContracte` | **0 / 0** |
| `planning.TechnicianQueueOrder` | **0** |
| `accounts.UserProfile` | **6** |

**Distribució de `ModelTask` per model:**

| nº de tasques | nº de models |
|---|---|
| 2 | 1 |
| 4 | 1 |
| 5 | 2 |

→ **només 4 models de 32 tenen cap tasca.** 28 models no en tenen ni una.
**Models amb ≥1 `Done`: 2.**

**`FittingSession`:** 9 amb `model`, **0** amb `garment_set`, **0** amb `convocatoria`
(0 convocatòries distintes). Estats: Oberta 4 · Tancada 2 · Programada 2 · Anullada 1.

**`GateEvent` per model:** cap fila (0 models).

**Planificació:** 11 tasques amb `planned_start` · **0** `planned_locked` · 16 amb `assignee` ·
4 models amb `reanchored_by_start`.

🚨 **El banc de staging és MAGRE per a aquest tram.** 0 rondes, 0 tasques `ad_hoc`, 0 albarans
lligats a tasques, 0 `GateEvent`, 0 `Production`, 0 convocatòries, 0 conjunts. **Tot el camí de la
ronda (i el de l'entrega) està sense exercitar amb dades vives a staging.** Qualsevol QA del tram
haurà de **fabricar** el banc, i això és una ESCRIPTURA (v. §E).

---

## R15 · TANCAMENT

### Taula resum — NODE → veredicte, ordenada per nombre d'extensions

| # ext. | NODE · fitxer:línia | Veredicte |
|---|---|---|
| **8** | `tasks/services_r.py:46` `tasca_vigent` — 8 consumidors | **ES TOCA** |
| **10** | `tasks/services_c.py:276` `transition_task` — 10 call-sites | **ES TOCA** |
| **13** | `tasks/models.py:179` `ModelTask` — **57 fitxers de test** + 9 apps | **ES TOCA** |
| **9** | `planning/plan_service.py:48` `recompute_for_technicians` — 9 call-sites | **ES LLEGEIX** |
| **18** | `tasks/services_batec.py:87` `batec_escriptura` — 18 punts d'escriptura | **ES TOCA** |
| **6** | `tasks/services_i.py:44` `TRAMS_SANS` — Welford, albarà, consum, agregadors | **ES LLEGEIX** |
| **6** | `fitting/models.py:24` `SizeFitting.numero` — 6 assignadors divergents | **ES LLEGEIX** |
| **5** | `tasks/models.py:132` `Ronda` — model, servei, porta, serializer, UI | **ES TOCA** |
| **5** | `tasks/services_c.py:84` `te_paret_albara` — `transition_task`, batec, `open-task`, serializer, front | **ES TOCA** |
| **4** | `tasks/views_b.py:536` `open_model_task_view` | **ES TOCA** |
| **4** | `tasks/serializers_b.py:23` `ModelTaskSerializer` | **ES TOCA** |
| **3** | `Model.fase_actual` com a CONTEXT — `fitting/views.py:309`, `services_e.py:22`, `fitting/services.py:1181` | **ES TOCA** |
| **3** | `tasks/services_i.py:73` `record_actual_time` (clau `(item, task_type)`) | **ES TOCA** |
| **3** | `tasks/services_d.py:38` `advance_phase_gate` (fase + GateEvent + segell) | **ES LLEGEIX** |
| **3** | `commerce.DeliveryNote` + `DeliveryNoteLine.model_task` | **ES LLEGEIX** |
| **2** | `tasks/views_b.py:106` `by_model` / `kanban_state` — **0 tests** | **ES TOCA** |
| **2** | `planning/views.py:214` `calendar_events_view` — **0 tests** | **ES TOCA** |
| **2** | `services_c.py:212/231` `_meritar_model`/`_meritar_conjunt` | **ES LLEGEIX** |
| **2** | `fitting/services.py:1088` `_seal_session` · `:1032` `set_piece_gate` | **ES LLEGEIX** |
| **1** | `tasks/services_scheduling.py:15` `reagenda_tasca` — **0 tests** | **ES TOCA** |
| **1** | `tasks/views_b.py:361` `model_task_log_view` — **0 tests** | **ES TOCA** |
| **1** | `models_app/views.py:1946` `_assegura_pom_task_oberta` | **ES TOCA** |
| **1** | `models_app/views.py:4329` `model_dashboard_view` | **ES TOCA** |
| **1** | `frontend/src/utils/caraObrirTasca.js:36` | **ES TOCA** |
| **1** | `frontend/src/components/model/ObrirTascaDialog.jsx:31` | **ES TOCA** |
| **1** | `frontend/src/components/model/WorkPlan.jsx` | **ES TOCA** |
| **1** | `frontend/src/components/model/TaskTree.jsx` | **ES TOCA** |
| **1** | `frontend/src/components/model/BadgeLliurable.jsx:15` | **ES LLEGEIX** |
| **1** | `frontend/src/pages/PlanningCalendar.jsx:171` `inRange` | **ES LLEGEIX** |
| 0 | `tasks/views_b.py:479` `claim_task_view` | **NO ES TOCA** |
| 0 | `frontend/src/components/model/SessionActions.jsx` | **NO ES TOCA** |
| 0 | `frontend/src/pages/TechSheetEntry.jsx` · `TallerPatro.jsx` | **NO ES TOCA** |
| 0 | `models_app.Contracte` / `LiniaContracte` (0 files, 0 escriptors) | **NO ES TOCA** |
| 0 | `public.backoffice_tenantcontract` / `contractline` (SaaS) | **NO ES TOCA** |
| 0 | `fitting/brain.py:16` (stub) | **NO ES TOCA** |

### LES 3 COL·LISIONS — mesurades, sense veredicte de disseny

#### ① Fase-com-a-context vs ronda-com-a-context

**Què llegeix `fase_actual` de debò per DECIDIR (no per pintar): 3 punts.**

| Punt | Decisió |
|---|---|
| `fitting/views.py:309` | **materialitza** la fase del model dins de `FittingSession.fase` (camp real, `fitting/models.py:318`) |
| `tasks/services_e.py:22` | refusa enviar a confecció una fase futura sense `GateEvent` |
| `fitting/services.py:1181-1182` | bloqueja l'avanç si no hi ha `Production` `Delivered` per a la fase actual |

**Mesura del pes:** `GateEvent` = **0 files** · `Production` = **0 files** ·
`fase_actual` a BD = `Pending` 28 / `Dev` 3 / `Proto` 1 · l'única escriptura automàtica de fase és
`Pending→Dev` (`services_c.py:379`). **Els tres punts de decisió existeixen al codi i cap d'ells ha
disparat mai a staging.**

**El fet dur:** hi ha **una** entitat que ja materialitza «de quina volta és aquesta feina», i és
`FittingSession.fase`, no la ronda. `ModelTask` **no té** cap camp de fase.

#### ② La clau de la cel·la Welford

**Clau exacta:** `(Model.garment_type_item, ModelTask.task_type)` — `services_i.py:86-87`,
`unique_together` a `tasks/models.py:639`.

**Mesura:**
- K tasques del mateix `task_type` sobre un model → **K mostres a la mateixa cel·la**, amb el total
  acumulat de cada tasca (v. R4, càlcul);
- una tasca re-tancada M vegades → **M mostres**, cadascuna amb el total **acumulat** (no el delta);
- corpus: **3 de 9** tasques tancades ja tenen 2 `→Done` avui, **sense rondes**;
- 468 cel·les, **1 sola** amb `n >= 5` → el llindar `WELFORD_MIN_SAMPLES = 5` encara no mana
  pràcticament enlloc a staging;
- 4 tests fan `.get()`/`.filter()` **per la clau exacta** i cauen si guanya un eix.

#### ③ `reagenda_tasca` vs la proposta de ronda nova

**El mateix esdeveniment de domini** («aquest proto no serveix / avui no el mesuro, tornem-hi el
dia X») **té dos mecanismes que no es coneixen:**

| | `reagenda_tasca` (`services_scheduling.py:15`) | `obrir_ronda`/`obrir_correccio` (`services_r.py:88,148`) |
|---|---|---|
| Disparador | `resolve_size_check` amb `final_estat ∈ {Rebutjat, Descartat}` **i** `data_represa` (`services_size_check.py:301`) | gest humà a `ObrirTascaDialog` → `POST obrir-ronda/` |
| Efecte | **mateixa** `ModelTask`, `planned_*` + `planned_locked=True` | **nova** `ModelTask` `ad_hoc` amb `mare` |
| Temps | acumula sobre la mateixa tasca (mateixos trams) | tram nou → mostra Welford nova |
| Comptador de mostres | cap | `Ronda.seq` (només `nova_mostra`; les correccions **no** el pugen, S-20) |
| Facturació | cap efecte | volta facturable a part |
| Coneixement mutu | **`reagenda_tasca` no consulta `Ronda`** — però **sí** passa per `tasca_vigent` (`:33`), que resol per ronda oberta | **`obrir_ronda` no consulta `planned_locked`** ni la reagenda |
| Tests | **0** | 50 |
| Files a staging | 0 tasques amb `planned_locked` | 0 rondes |

### Divergències entre els ancoratges del brief i l'arbre real

Totes al **§0-bis**. Resum: **7 divergències**, de les quals **1 canvia la premissa del tram**
(D-0: la ronda ja està construïda) i **2 són fitxers que no existeixen amb el nom citat**
(`_close_pom_task_for_model` → `_assegura_pom_task_oberta`; `_reagenda_tasca_size_check` →
`tasks/services_scheduling.reagenda_tasca`). En tots dos casos **he aturat el punt i ho reporto**,
sense buscar equivalents pel meu compte: el codi mateix documenta la mudança amb el nom vell.

### El que NO he pogut determinar, dit com a tal

1. **Les xifres de PROD.** Aquest cens només ha llegit `ftt_staging`. Els 81 models i el R1
   retroactiu del brief són de PROD i **no s'han mesurat**. No barrejo les dues fotos.
2. **Si les rondes s'han fet servir MAI en producció.** A staging n'hi ha 0. No ho puc saber sense
   llegir la BD de PROD.
3. **Quant triga cada bloc del gate.** ⛔ No s'ha executat cap test. El temps es declararà quan
   s'autoritzi la correguda.
4. **Si `by_model` i `calendar_events_view` funcionen com diuen.** No tenen ni un test i no n'he
   corregut cap: el que reporto és **la lectura del codi**, no una mesura.
5. **Si `ExportFittingCSV` alguna vegada va funcionar.** La URL que construeix no casa amb cap ruta
   registrada avui, i no té consumidor. No he mirat l'historial de git per no allargar el Patró A.
6. **El substrat de disseny (VAULT FTT-Brain del Mac).** No és al servidor i no l'he buscat.
7. **Quin és el destinatari d'una entrega.** No hi ha cap camp al sistema que ho digui per a una
   volta de feina. `DeliveryNote` té el client del **document**, i `Production` el **supplier**.
8. **`fitting/views.py` no l'he indexat sencer** (`schedule`, `open`, `close`, `advance`): n'he
   llegit el que R7 demana. Si el tram hi entra, cal un cens propi d'aquell fitxer.

### Riscos de concurrència — què hi ha en marxa al servidor ara mateix

| Fet | Valor |
|---|---|
| `load average` | **0.06 / 0.04 / 0.01** — cap suite ni cap build en marxa |
| `ftt-staging.service` | active running, PID 3692893, des de **14:52:47 UTC** |
| 🚨 **Divergència desplegat↔disc** | gunicorn **38 s més vell que HEAD**; `frontend/dist` de les **12:42**, ~2h abans de HEAD. **Una QA per HTTP avui mesura codi anterior a HEAD** |
| Processos aliens vius | `manage.py runserver :8099` (PID 1402071, del **04/08**) i `qa_serve.py` (PID 1362939, del **04/08**) — restes de sessions antigues, **no tocats** |
| Sessions concurrents | **133 canvis sense commitar** al working tree, dels quals 4 modificats i 129 untracked. Cap `.py` de `backend/fhort/`, cap migració. ⚠️ Llei de la casa: **l'índex de git és COMPARTIT** — un `git commit` sense pathspec s'enduria feina aliena |
| Zones intocables | `/var/www/assessment` i `/var/www/trading` amb gunicorn propis (supervisord PID 1499985) — **no tocades** |
| Finestra perillosa | `unattended-upgrades` reinicia Postgres cap a les **06:39 UTC** (memòria de sessions anteriors, no mesurat avui) |
| Escriptures fetes per aquest cens | **CAP.** Transacció `REPEATABLE READ READ ONLY` amb `ROLLBACK`, barana provada sobre la fila `id=362`, `txid_current_if_assigned() IS NULL` |

---

## §D · LECTURES DE DISSENY (totes juntes, cap barrejada amb els fets)

> **Això NO són fets ni decisions.** Són les preguntes que el cens deixa obertes perquè l'Agus
> decideixi. Cap d'elles s'ha construït ni s'ha començat.

**D-1 · La meitat que falta té nom: `Entrega`, no `Ronda`.** La ronda existeix, funciona i té UI.
El que no existeix és l'**acte datat amb destinatari i contingut**. Avui «lliurada» es DEDUEIX
(`ronda_lliurable`: totes les `es_lliurable` a `Done`) i el fet no es declara enlloc.

**D-2 · El segell no té on caure avui perquè no hi ha res que digui «entregada».** El punt exacte
seria `services_c.py:319`, al costat del guard d'albarà — però el predicat que hi hauria d'anar
(«la ronda d'aquesta tasca està entregada») no és consultable: `Ronda` només té `tancada_el`, i
«tancada» no és «entregada».

**D-3 · Ja hi ha una paret que fa gairebé això, i és l'albarà.** `te_paret_albara`
(`services_c.py:84`) ja converteix «facturada» en intocable, ja té `code='tasca_albaranada'`, ja té
cara pròpia al modal (`CARA_ALBARANADA`) i ja té 3 lectors. La pregunta és si l'entrega és una
segona paret o la mateixa vista des de l'altra banda.

**D-4 · Dos eixos de context conviuen i cap els concilia** (col·lisió ①): `FittingSession.fase`
materialitza la fase en una fila; `ModelTask.ronda` materialitza la volta. Cap dels dos sap de
l'altre.

**D-5 · El Welford aprendrà de dues poblacions barrejades** (col·lisió ②) sense cap eix que les
separi. Ja passa avui amb les rectificacions (3 de 9 tasques amb 2 `→Done`).

**D-6 · «El proto no serveix» té dues portes** (col·lisió ③) amb semàntiques oposades: reagendar
CONSERVA la identitat, obrir ronda la SUBSTITUEIX. Cap consulta l'altra.

**D-7 · El board no sap què és una volta.** `by_model` compta el pla sencer, i no té ni un test.
Amb N rondes, els comptadors sumen totes les voltes i `kanban_state` diria `pending` d'un model que
ja ha entregat la seva volta.

**D-8 · Tres superfícies llegeixen tasques i cap porta `ronda` al payload:** `model_task_log_view`
(el Registre d'activitat), `model_dashboard_view` (el compositor) i `by_model` (el board). El camp
existeix al serializer de detall (`ronda_seq`) però no arriba a cap de les tres.

**D-9 · Els tokens `--paused`, `--progress` i `--soft` del mockup no existeixen.** Cal decidir si es
creen (i amb quins valors, contra la NORMA §1b) o si el mockup s'expressa amb els que hi ha
(`--warn-state`/`--warn-ink`, `--tram`, `--line-soft`).

**D-10 · Quatre nodes sense cap test cauen dins del radi:** `by_model`/`kanban_state`,
`calendar_events_view`, `model_task_log_view` i `reagenda_tasca`. Tocar-los a cegues és tocar 429
línies de producte sense xarxa.

**D-11 · El banc de staging no serveix per provar aquest tram** (0 rondes, 0 `ad_hoc`, 0 albarans
lligats a tasques, 0 `GateEvent`, 0 `Production`, 0 convocatòries). **Fabricar-lo és ESCRIURE**, i
per tant surt del Patró A.

---

## §E · EL QUE NO ES POT SABER SENSE ESCRIURE — i aquí em paro

Per llei del brief («qualsevol cosa que exigiria escriure per mesurar-la: digues què no es pot
saber sense escriure, i para»), **NO he mesurat** cap d'aquestes i **paro** aquí:

1. **Si `obrir_ronda` funciona de debò contra el banc viu.** A staging hi ha **0 rondes**. Provar-ho
   exigeix crear una `Ronda` i N `ModelTask` → escriptura.
2. **Quantes mostres Welford aporta una segona volta i amb quin valor.** El càlcul de R4 és exacte
   **sobre el codi**; per mesurar-lo cal tancar una tasca de ronda → escriptura a
   `TaskTimeEstimate`.
3. **Si la segona ronda remerita.** El codi diu que no (dos guards + OneToOne). Comprovar-ho
   exigiria obrir una ronda i escriure-hi → `ConsumptionRecord` + event a `public`.
4. **Si el guard `tasca_albaranada` dispara de debò sobre una tasca de ronda.** A staging hi ha
   **0 `ModelTask` albaranades**: cal crear una `DeliveryNoteLine` amb `model_task` i emetre
   l'albarà → escriptura, i a més a `commerce`.
5. **La forma real dels events de calendari d'una convocatòria.** **0 convocatòries** a staging.
   Cal `schedule_bulk` → crea N `FittingSession`.
6. **Si `reagenda_tasca` i `obrir_ronda` col·lideixen a la pràctica.** Cal un `SizeCheck` resolt
   amb `data_represa` **i** una ronda oberta sobre el mateix model → dues escriptures.
7. **El temps de correguda de cada bloc del gate.** Executar tests **escriu** (crea l'esquema
   `test_*`, i una suite morta a mitges deixa `schema_name='test'`). ⛔ No n'he corregut cap.
8. **Si `by_model` retorna el que crec.** L'endpoint és `GET` i seria read-only, però per veure'l
   amb rondes cal que n'hi hagi → escriptura.
9. **Les xifres de PROD.** No hi he connectat. Fer-ho és una altra sessió amb la seva pròpia
   barana.

---

*Cens tancat. Cap fitxer de producte tocat · cap migració · cap escriptura a BD · cap test executat.*
*Únic fitxer escrit: aquest.*
