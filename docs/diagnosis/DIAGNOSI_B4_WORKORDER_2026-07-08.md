# DIAGNOSI — B4 WorkOrder + Expense + DeliveryNote (terreny real)

Data: 2026-07-08 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.

**Abast:** cartografiar el terreny real (models, serveis, estats, constraints) abans del
disseny fi de B4 — l'ordre de treball (WorkOrder), la seva relació amb tasques/extres/
deduccions, i l'albarà (DeliveryNote) que n'agrega el resultat. NO decideix; dimensiona.

**Convenció:** cada afirmació porta `fitxer:línia` (relatiu a l'arrel del repo).
`"NO EXISTEIX" = confirmat absent al codi` (grep buit), no especulat.
`💡 PROPOSTA (a validar)` = suggeriment de disseny, clarament separat del FET. Les
decisions són humanes (Patró C).

**Regla ja decidida (context, no re-oberta):** tasca de model assignat a WorkOrder → aquell
WorkOrder (`off_recipe` si fora de recepta); tasca de model sense WorkOrder → WorkOrder
col·lector lazy per (customer, mes); l'albarà agrega només WorkOrders: tasques acabades +
extres − deduccions per recepta no executada.

---

## Resum executiu (les conclusions que desbloquegen el disseny)

1. **WorkOrder, Expense i DeliveryNote NO EXISTEIXEN avui.** Cap `class WorkOrder`, cap
   `class DeliveryNote`, cap FK `Model↔order_line`. Només hi ha TODOs de roadmap a
   `commerce/models_base.py:5,18,28` i `commerce/services.py:20`. B4 és construcció nova
   sobre bastida existent, no refactor.

2. **El constraint `unique_together(model, task_type)` és el bloquejador central de la
   regla `off_recipe`** (`tasks/models.py:97`). Un EXTRA del mateix `task_type` que una
   tasca ja existent del model **viola la BD** (IntegrityError), i el camp `origen`
   (`prevista`/`ad_hoc`) NO forma part de la clau → no serveix per distingir-les. Cal una
   decisió d'esquema abans de poder representar extres del mateix tipus.

3. **El hook de meritació és un punt d'ancoratge idempotent i ja provat per al col·lector
   lazy.** El guard `if rows:` a `services_c.py:103` (UPDATE compare-and-set `consumption_
   started_at__isnull=True`) garanteix "exactament una vegada per model" a nivell BD, i ja
   té reconciliació de forats (`reconcile_consumption.py`). És el candidat natural a
   trigger de "crear/adjuntar WorkOrder col·lector on first InProgress".

4. **`Done` és l'ÚNIC estat terminal de ModelTask** (`tasks/models.py:63`). "Totes les
   tasques tancades" = totes en `Done`. Bloquegen un tancament: `Pending`, `InProgress` i
   sobretot `Paused` — que es pot generar **automàticament** (regla "1 InProgress per
   tècnic", `services_c.py:60-67`) i quedar penjada. No hi ha cap flag Blocked/Watchpoint
   sobre la tasca.

5. **DeliveryNote encaixa net com a 3a subclasse d'`AbstractDocument`** (customer, totals,
   numeració i PDF ja genèrics). L'únic punt no trivial és `DocumentDueDate`, que té un
   XOR dual-FK deliberat (decisió B3b, `commerce/models.py:401`) — enganxar-hi un tercer
   document reobre aquesta decisió.

6. **Impacte de dades ZERO per fer `customer` i `garment_type_item` obligatoris.** A l'únic
   tenant real (`fhort`, 20 models) els 20 tenen customer i GTI informats; cap NULL. La
   dificultat de fer-los obligatoris és de codi (guards al wizard), no de backfill.

---

## BLOC 1 — Naixement i màquina d'estats de ModelTask (Q1)

### Creadors de ModelTask (tots els naixements)
No hi ha `bulk_create` ni cap seed de ModelTask (**NO EXISTEIX**). Els naixements són:

| # | Origen | fitxer:línia | Mètode |
|---|--------|--------------|--------|
| 1 | Define-tasks (bulk + individual) | `backend/fhort/tasks/views_b.py:313` | `.create()`; salta `(model,task_type)` existents (comprova a `:301`) |
| 2 | Open-task des d'eina/kanban | `backend/fhort/tasks/views_b.py:504` | "crea-si-falta" (`.filter().first()` a `:499`) |
| 3 | Assign-batch (planificació) | `backend/fhort/planning/plan_service.py:310` | "buscar/crear canònica" (`.filter().first()` a `:293`); NO crea si `estimated_minutes is None` (`:302-309`) |
| 4 | ViewSet REST POST | `backend/fhort/tasks/views_b.py:259-261` (`perform_create`) | `ModelViewSet` complet (`:41`); gate `DEFINE_TASKS` (`:61`) |
| 5 | Command QA-clone | `backend/fhort/models_app/management/commands/clone_model_for_qa.py:118` | únic `get_or_create` de ModelTask (`task_type='size_check'`) |

**No hi ha creador anomenat "wizard".** El kanban no té creador dedicat: neix via #2.
**Patró comú a #1/#2/#3/#5:** tots fan `filter(model, task_type).first()` abans de crear →
**depenen implícitament de la unicitat `(model, task_type)`** (veure BLOC 2).

### Màquina d'estats real
- Camp `status` (`tasks/models.py:72`, default `Pending`). **STATUS_CHOICES**
  (`:63-64`): `Pending`, `Paused`, `InProgress`, `Done`. Només aquests 4.
- Transicions permeses — dict `ALLOWED` a `services_c.py:11-16`:
  `Pending→InProgress`, `Paused→InProgress`, `InProgress→{Paused,Done}`,
  `Done→InProgress` (reobertura = rectificació). Mai es torna a `Pending`.
- **Únic escriptor:** `transition_task(task, to_status, profile)` a `services_c.py:46-131`
  (`@transaction.atomic`); valida contra `ALLOWED` (`:52`), llança `TransitionError` (`:42`).
  Cridada des de `views_b.py:510` (open/claim) i `retype_scaling_to_grading.py:64-65`.
- Cada transició escriu `TaskTransition` immutable (`_log`, `services_c.py:38-39`; model
  `models.py:103`). `rectification_count` = transicions `Done→InProgress` (`services_c.py:134-137`).
- **Regla "1 InProgress per tècnic"** (`services_c.py:58-67`): en entrar a InProgress, l'altra
  InProgress del mateix `assignee` passa a `Paused` automàticament (tanca timer + log).

### "Done" i timestamps
- `Done` = valor literal de `status` (`models.py:63`); estat de compleció, reobrible només
  via rectificació. Assign-batch el tracta com immutable i l'omet (`plan_service.py:295-296`).
- `started_at` (`models.py:77`): set la 1a entrada a InProgress si és `None` (`services_c.py:70-71`);
  es CONSERVA en reobrir (`:72-74`).
- `finished_at` (`models.py:78`): set en `InProgress→Done` (`services_c.py:78-79`); es NETEJA
  (`None`) en reobrir `Done→InProgress`. **És l'únic segell de compleció** — NO existeix
  `completed_at`.
- `planned_start`/`planned_end` (`:82,:84`) = motor de planificació (no execució real).
  `created_at`/`updated_at` (`:88-89`) auto.
- **TROBALLA TRANSVERSAL:** `consumption_started_at` **NO** viu a ModelTask sinó al **Model**
  (`models_app/models.py:204`); veure BLOC 3.

**Veredicte BLOC 1:** màquina d'estats petita i determinista, un sol escriptor, log immutable.
El "quan es va acabar què" per tasca són `started_at`/`finished_at`; el detall temporal fi
és a TimerEntrada (BLOC 4). Llest per dissenyar sobre ell.

---

## BLOC 2 — Constraint `unique_together` i col·lisió d'EXTRA off_recipe (Q2) ⚠️ CRÍTIC

- **CONFIRMAT:** `Meta.unique_together = [('model', 'task_type')]` a `tasks/models.py:97`
  (comentari defensiu `:95-96`). Migració `tasks/migrations/0018_alter_modeltask_unique_together.py:14-17`
  (`AlterUniqueTogether({('model','task_type')})`). Commit `34e7e62` (Grup A, 2026-06-03) —
  verificat via `git show`.
- **Camps exactes:** `(model, task_type)`. NO inclou `origen`, `status` ni `assignee`. És
  `unique_together` clàssic, no un `UniqueConstraint` condicional.
- **Impacte sobre `off_recipe`:** una SEGONA ModelTask del mateix `task_type` per al mateix
  `model` **viola el constraint** (IntegrityError), **independentment de `origen`**. El camp
  `origen` (`prevista`/`ad_hoc`, `models.py:69,73`) NO forma part de la clau → NO permet
  distingir dues tasques del mateix tipus. Per tant **un "EXTRA off_recipe" del mateix
  task_type que una tasca existent NO cap sota l'esquema actual sense relaxar el constraint.**
- **Qui consumeix la unicitat avui** (i per tant qui es trencaria si es relaxa):
  `clone_model_for_qa.py:118` (`get_or_create`), i el patró filter-first-then-create a
  `views_b.py:301/313`, `views_b.py:499/504`, `plan_service.py:293/310`. El codi ja
  raona explícitament sobre "el task_type és la fulla" a `views_b.py:999-1004`.
- El propi codi ja topa amb la col·lisió en un altre context: `retype_scaling_to_grading.py:10-11`
  documenta que si el model ja té grading, no es pot re-tipar scaling, i ho gestiona
  esborrant/skip (`:47-54`).

**Veredicte BLOC 2: cal X — decisió d'esquema abans de dissenyar extres.** L'`off_recipe`
del mateix `task_type` és incompatible amb `unique_together(model,task_type)` tal com és.
💡 PROPOSTA (a validar): tres vies possibles a decidir per l'Agus —
(a) afegir `off_recipe`/`origen` a la clau (`unique_together(model,task_type,origen)` o
`UniqueConstraint` parcial només sobre `prevista`); (b) modelar els extres en una entitat
NOVA a nivell de WorkOrder (WorkOrderExtra) i no com a ModelTask, deixant ModelTask intacte;
(c) relaxar del tot i moure la garantia "1 de recepta per tipus" a la capa de servei. La (b)
evita tocar la clau que 4 camins consumeixen; la (a) i (c) obren radi. Sense decidir.

---

## BLOC 3 — Hook de consum com a trigger del col·lector lazy (Q3)

- **Punt d'ancoratge:** dins `transition_task`, bloc `if to_status == 'InProgress':`
  (`services_c.py:90-123`). La UPDATE que mereix és `services_c.py:100-102`:
  `Model.objects.filter(pk=task.model_id, consumption_started_at__isnull=True).update(...)`.
- **Camp:** `consumption_started_at` al **Model** (`models_app/models.py:204`; migració
  `0035_consumption_record_and_field.py:15-19`, que també crea `ConsumptionRecord` OneToOne).
  Escriptors: hook viu (`services_c.py:100-102`), backfill (`reconcile_consumption.py:117-118`),
  QA-clone (`clone_model_for_qa.py:83`). Lectors: planning (`planning/views.py:695`), i els
  propis guards `__isnull=True`.
- **Idempotència: SÍ, a nivell BD.** El guard és compare-and-set atòmic, no read-then-write:
  la meritació (ConsumptionRecord + signal `model_consumption_started`) només corre dins
  `if rows:` (`services_c.py:103`). Qualsevol crida posterior dona `rows=0` (el camp ja no
  és NULL) → no es re-dispara, fins i tot amb dues InProgress simultànies del mateix model
  (només una fila guanya). **NO hi ha `select_for_update`** — la serialització és només
  la UPDATE atòmica.
- **Schema-safety (django-tenants):** el hook corre al schema del tenant de la request;
  `transition_task` és `@transaction.atomic` (`:46`) amb un `atomic` anidat (savepoint) a
  `:99` dins un `try/except Exception` no-fatal (`:98-123`, `logger.exception` sense re-raise,
  comentari `:123`). **TROBALLA TRANSVERSAL / fragilitat:** el signal escriu a PUBLIC
  (`backoffice/receivers.py:10`, `schema_context('public')`) **dins** la transacció oberta al
  tenant — canvi de search_path a mitja transacció. Django-tenants ho suporta; el comportament
  exacte del commit-order public↔tenant amb connexió compartida és PENDENT DE VERIFICAR
  (no confirmable per lectura estàtica).
- **`reconcile_consumption.py`:** command de backfill (no automàtic). Troba models amb
  activitat (`model_tasks__status__in=['InProgress','Done','Paused']`) però
  `consumption_started_at IS NULL` (`:64-73`), reconstrueix `merited_at = MIN(TaskTransition
  where to_status='InProgress')` (`:83-87`) i fa la mateixa triple escriptura idempotent.
  Corre per tenant amb `schema_context` (`:59`), `--dry-run`/`--tenant` (`:31-39`).

**Veredicte BLOC 3: llest com a punt d'ancoratge.** El guard `if rows:` (`services_c.py:103`)
és estructuralment adequat i ja idempotent per crear-hi el WorkOrder col·lector lazy on first
InProgress. 💡 PROPOSTA (a validar): (a) la creació del WorkOrder ha d'anar dins `if rows:`,
mai a les vistes (`views_b.py:407/510` són dues superfícies); (b) decidir el schema del
WorkOrder (TENANT encaixa net al `atomic`; PUBLIC afegiria una 3a escriptura cross-schema);
(c) afegir la branca corresponent a `reconcile_consumption.py` per als forats, perquè
l'`except` silenciós (`:119-123`) no perdi WorkOrders. **Avís:** la unicitat "1 WorkOrder
col·lector per (customer, mes)" NO la garanteix aquest guard (que és per-model) — cal un
guard propi (constraint o get_or_create sobre (customer, mes)).

---

## BLOC 4 — TimerEntrada: font del detall temporal (Q4)

Model a `tasks/models.py:4-18`:

| Camp | fitxer:línia | Captura |
|---|---|---|
| `model_task` | `:5` | FK→ModelTask (CASCADE, `related_name='timers'`) — a quina tasca s'imputa |
| `tecnic` | `:6` | FK→`accounts.UserProfile` (PROTECT) — el treballador |
| `inici` | `:7` | DateTimeField obligatori — hora d'inici |
| `fi` | `:8` | DateTimeField nullable — tancament |
| `minuts` | `:9` | PositiveInteger nullable — durada calculada al tancar |
| `actiu` | `:10` | Boolean default True — timer obert |

- **Creació/tancament** (`views.py:15-59`): el `tecnic` s'assigna automàticament a l'usuari
  autenticat (`perform_create`, `:44`; read-only al serializer `:14`); `inici` l'aporta el
  **client** (no read-only, sense default de servidor — PENDENT DE VERIFICAR si algun altre
  punt el força al servidor). Al tancar (`@action tancar`, `:46-57`): `fi=timezone.now()`,
  `minuts=max(0, delta//60)`, `actiu=False` — tot hora de servidor.
- **Granularitat i límits:** múltiples timers per ModelTask (`related_name='timers'`). Coneix
  tècnic, inici, fi, minuts, i indirectament model + task_type (fase/facturable via
  `model_task.task_type`, `TaskType.facturable` a `models.py:50`). **NO coneix peça/piece**
  (la granularitat màxima és model×task_type, `unique_together` `:97`). **TROBALLA
  TRANSVERSAL:** l'API NO exposa el `task_type` del timer — el serializer serveix `tecnic_nom`
  i `model_task_codi` (`serializers.py:7-8`), no la fase/tipus; caldria JOIN.
- **NO EXISTEIX** cap agregador que sumi `TimerEntrada.minuts` cap a WorkOrder/albarà (grep
  buit dins `tasks/`).

**Veredicte BLOC 4: llest com a matèria primera.** TimerEntrada és el log granular
(tècnic × ModelTask × interval) que un WorkOrder/DeliveryNote agregaria per respondre "quin
dia es va fer què i quant". Mancances a preveure al disseny: no baixa a peça, i el
`task_type`/`facturable` s'ha d'exposar (avui requereix JOIN).

---

## BLOC 5 — Sessions de fitting: com s'incorporen al detall (Q5)

- **Models** (`fitting/models.py`): `FittingSession` (`:202-288`), `PieceFitting` (`:291-334`),
  `PieceFittingLine` (`:337-359`).
  - `FittingSession`: apunta a EXACTAMENT un `model` O un `garment_set` (XOR CheckConstraint
    `fittingsession_set_xor_model`, `:276-284`). Dates: `data` (DateField, `:230`),
    `start_time`/`end_time` (`:231-232`), reals `started_at`/`finished_at` (`:262-267`),
    `created_at` (`:244`). Persones: `responsable` (`:236`), `attendees` M2M (`:254`),
    `created_by` (`:245`), més camps lliures `model_persona`/`assistents`/`lloc`. `estat`
    (Programada/Oberta/Tancada/Anullada, `:242`), `fase` (`:229`), `convocatoria` UUID (`:258`).
  - `PieceFitting`: gate per peça (Pendent/OK/NO_OK/EXCEPCIO, `:309`) amb `gate_motiu`/`gate_per`/
    `gate_at` (`:310-318`); unique `(session, model)` (`:331`).
  - `PieceFittingLine`: POM × talla, teòric vs real (`valor_teoric`/`valor_real`, `:347-350`).
- **Creació:** `FittingSessionCreateSerializer` (`serializers.py:152-162`) → `create_session`
  (`services.py:100-130`). Vies de calendari `schedule`/`schedule_bulk` creen sessions
  'Programada' (`services.py:133,190`). **No captura customer ni cap referència a comanda.**
- **CRÍTIC — les sessions NO generen ModelTask.** Grep `modeltask|model_task` dins
  `fhort/fitting/` → **0 resultats**. Són un registre SEPARAT i autònom. **TROBALLA
  TRANSVERSAL:** l'únic pont cap a la capa producció és la via de calendari `schedule`, que
  opcionalment toca `tasks.Production` (NO ModelTask) per (model, fase) si es passa
  `expected_at` (`views.py:210-237`, no re-raise).
- **Camí a client:** `FittingSession.model → Model.customer` (`models_app/models.py:125`).
  Si la sessió apunta a `garment_set` (no `model`), el customer s'ha de resoldre pels models
  del set (PENDENT DE VERIFICAR el camí GarmentSet→customer). Dades ja serialitzades i
  llestes per llistar en una comanda: `data`, `fase`, `model`+codis, gates per peça
  (`FittingSessionDetailSerializer`, `serializers.py:119-149`).
- **NO EXISTEIX** cap FK sessió↔albarà/WorkOrder. (Existeix un `ConsumAlbara` a
  `models_app/models.py:744`, però cap referència des de fitting — PENDENT DE VERIFICAR
  el seu rol respecte del DeliveryNote de B4.)

**Veredicte BLOC 5: cal X — vincle nou.** Les claus per detallar sessions en un WorkOrder/
albarà ja hi són (data, fase, model→customer, gates), però **la relació explícita
sessió↔comanda/WorkOrder no existeix i s'ha de construir**. Les sessions són registre
autònom; incorporar-les és afegir un pont (per model+data+customer), no reusar un existent.

---

## BLOC 6 — Models sense comanda / on viuria l'assignació a WorkOrder (Q6)

- **`Model.customer`** EXISTEIX (`models_app/models.py:125-131`): FK→`tasks.Customer`
  (PROTECT), **nullable** (`:128-129`, comentari `:124`: "Nullable a BD per la transició; el
  wizard l'exigeix"). El wizard l'exigeix a UI (`frontend/src/pages/ModelWizard.jsx:183`);
  el backend NO el valida com a obligatori (`create_model_wizard`, `views.py:352`).
- **FK `Model↔order_line`: NO EXISTEIX.** Ni `Model` té camp cap a commerce (revisió
  `:117-314`), ni `SalesOrderLine` (`commerce/models.py:328-349`) té FK a `models_app.Model`
  (enllaça a `order` i a `commerce.Product`). Grep de `models_app.Model` dins `commerce/` = buit.
- **`WorkOrder`: NO EXISTEIX** (només TODO B4-B5: `commerce/models_base.py:28`, `models.py:5`,
  `services.py:20`). El disseny "WorkOrder = model × order_line (order_line nullable)" i
  "model assignat a WorkOrder" **no té avui cap suport a BD** — no existeix ni el model ni
  cap FK on viuria l'assignació.
- **TROBALLA TRANSVERSAL (homònim perillós):** `TechnicianQueueOrder`
  (`planning/models.py:72-93`) té `model = FK(Model)` (`:82`), però "Order" aquí = ordre/posició
  dins la cua d'un tècnic, **NO** comanda comercial. És l'únic FK entrant a Model amb "order".
- **COUNTS (read-only, executats):** un sol tenant real (`fhort`; l'altre és `public`).
  `fhort`: **20 models totals, 20 actius** (tots `estat='Nou'`; cap `Tancat`),
  **0 sense customer**, **0 amb GTI null**. `fase_actual`: Dev 14 · Proto 1 · Pending 4 · PP 1.

**Veredicte BLOC 6: cal X — l'assignació model→WorkOrder és estructura nova.** Avui tot Model
té customer (0 orfes), i el "on viuria l'assignació" no existeix. 💡 PROPOSTA (a validar):
el WorkOrder és qui portaria la FK (WorkOrder → model, i WorkOrder → order_line nullable),
no el Model; el col·lector lazy per (customer, mes) es recolza en `Model.customer`, que ja
està 100% informat a l'únic tenant.

---

## BLOC 7 — Tancament de WorkOrder amb la màquina d'estats real (Q7)

- **`Done` és l'únic estat terminal** de ModelTask (`models.py:63`; posa `finished_at` a
  `services_c.py:78-79`). El codi ja usa "totes Done" com a senyal: models amb totes les
  tasques Done s'oculten per defecte (`views_b.py:87`); planning exclou Done sistemàticament
  (`plan_service.py:31,44,208,402`).
- **Estats que bloquejarien un "all tasks closed":** `Pending` (no arrencada), `InProgress`
  (en execució, timer obert) i **`Paused`**. El `Paused` és el més delicat: **es pot generar
  automàticament** per la regla "1 InProgress per tècnic" (`services_c.py:60-67`) i quedar
  penjat sense acció explícita del tècnic.
- **NO EXISTEIX cap flag Blocked/Watchpoint/Tancat sobre ModelTask.** "Watchpoint" és concepte
  d'UI d'import/mides sobre el **Model** (`models_app/services.py:69,95,106`), no estat de
  tasca. "Tancat" és estat d'ALTRES entitats: `Model.estat` (`views_b.py:92`), `SizeFitting.estat`
  (`fitting/models.py:20`; `pom/services.py:197 CLOSED_STATE`), o fase terminal de Producció/TOP
  (`tasks/services_d.py:28,38-39`). Cap tanca una ModelTask.
- Els extres off_recipe (BLOC 2), si no es poden representar per la col·lisió de constraint,
  són un segon eix de "què bloqueja el tancament" a resoldre abans de definir-lo.

**Veredicte BLOC 7: terreny per tancar la decisió #5 (sense decidir).** "Totes les tasques
tancades" es tradueix operativament a "totes en `Done`". El risc real de tancament penjat no
és un flag sinó els `Paused` auto-generats. 💡 PROPOSTA (a validar): definir si un WorkOrder
pot tancar amb tasques `Paused` (i com es resolen), i si els extres no resolts (BLOC 2)
bloquegen. La `GateEvent` (`models.py:122`) registra avanç de fase del Model, no tanca tasques
— PENDENT DE VERIFICAR si ha d'intervenir.

---

## BLOC 8 — Encaix documental: DeliveryNote + DocumentDueDate (Q8)

- **`class DeliveryNote`: NO EXISTEIX** (només placeholder: `commerce/models_base.py:5,18,28`
  TODO B4-B5; `commerce/services.py:20` prefix `DN` previst). El choice `'delivery_note'`
  NO és a `DOC_TYPE_CHOICES` (només `quote`, `sales_order`, `models_base.py:26-27`).
- **`AbstractDocument`** (`commerce/models_base.py:15-65`, `abstract=True`) **ja proveeix:**
  `document_number` (`:38`), `doc_type` (`:41`), **`customer`** FK→`tasks.Customer` PROTECT
  (`:42-43`), `status` (`:44`), `issued_at`/`valid_until`, `payment_terms` (`:49-50`), **totals**
  `subtotal`/`tax_amount`/`total`/`tax_breakdown` (`:51-57`), `notes`, auditoria.
  Subclasses actuals: `Quote`+`QuoteLine` (`models.py:209,248`), `SalesOrder`+`SalesOrderLine`
  (`models.py:281,328`).
- **El PDF ja és genèric** per a qualsevol AbstractDocument (**TROBALLA TRANSVERSAL**):
  `generate_document_pdf(doc, doc_title=…)` (`pdf_service.py:137-140`); `generate_quote_pdf`
  n'és només un wrapper. Un DeliveryNote reusaria el PDF cridant-lo amb `doc_title='Albarà'`
  sense codi nou (PENDENT DE VERIFICAR: el layout assumeix venciments/totals; un albarà
  sovint no en porta — decisió de producte).
- **Cal afegir per a DeliveryNote:** choice `'delivery_note'` (`models_base.py:25-30`), prefix
  `DN` (`services.py:20`), `DeliveryNoteLine(AbstractDocumentLine)` amb FK `related_name='lines'`
  (la relació `lines` NO és a l'abstracta; cada Line la declara — `models.py:250,332`),
  `save()` + `recalculate_totals()` (clonables de SalesOrder, `models.py:307-322`), migració.
- **`DocumentDueDate`** (`commerce/models.py:399-427`): decisió B3b explícita "dues FK nullable +
  CHECK que exactament una és no-null, **NO GenericFK**" (docstring `:401-402`). FK `quote`
  (`:405-406`) i `sales_order` (`:407-408`), ambdues nullable; **CHECK
  `duedate_exactly_one_parent`** (`:416-420`, XOR estricte). Property `document` (`:425-427`)
  i generador `generate_due_dates` amb binari `isinstance(...) else 'sales_order'`
  (`services.py:104`) — **TROBALLA TRANSVERSAL:** qualsevol 3r tipus cauria erròniament a
  `sales_order`; s'ha de tocar sí o sí.

**Veredicte BLOC 8: DeliveryNote encaixa net com a 3a subclasse; el punt no trivial és
DocumentDueDate.** Dues vies dimensionades (SENSE decidir), i **només** rellevants si un
albarà porta venciments (PENDENT DE VERIFICAR de producte):
- 💡 **Via (a)** — 3a FK `delivery_note` nullable + reescriure el CHECK a "exactament una de
  tres" + branca a la property i al generador. Cost baix–mitjà, **escala malament**: cada nou
  doc_type (B4-B5 preveuen encara WorkOrder + Settlement) repeteix la cirurgia.
- 💡 **Via (b)** — GenericFK/taula pont: elimina el CHECK XOR, simplifica generador i property,
  cost constant després. Però migració de dades dels `due_dates` existents, trenca
  `on_delete=CASCADE` natiu i el `related_name='due_dates'` que consumeixen `services.py:97` i
  els `recalculate_totals`. **Reobre la decisió B3b** (`models.py:401`) → decisió humana.

---

## BLOC 9 — Wizard GTI obligatori (Q9)

- **`Model.garment_type_item`** EXISTEIX (`models_app/models.py:161-167`): FK→`tasks.GarmentTypeItem`
  (SET_NULL), **nullable** (`:163-165`). És la baula del motor de temps (matriu item×task_type,
  `views.py:260`).
- **Impacte de fer-lo obligatori: ZERO backfill.** Al tenant `fhort` (l'únic real): **0 models
  amb GTI null** (executat read-only). Cap NULL a migrar.
- **Punts on avui NO s'exigeix** (i on caldria el guard):
  1. `frontend/src/pages/ModelWizard.jsx:181-183` — `handleCreate` només valida `season` i
     `customerId`, no GTI; es pot crear sense GTI.
  2. `frontend/src/pages/ModelWizard.jsx:299-320` — pas 2, `GarmentTypeSelector` (gate visual).
  3. `backend/fhort/models_app/views.py:266` (`_resolve_garment_def` només assigna si ve al
     payload) i `:328-330` (l'única validació dura és `year`/`season`) — server-side.
  4. (Opcional a BD) `models_app/models.py:161-167` — treure `null=True, blank=True` +
     migració; el backfill és innecessari (0 NULL).

**Veredicte BLOC 9: llest, cost baix.** Fer GTI obligatori és afegir guards al wizard
(frontend `:181-183`/`:299-320` + backend `views.py:266`/`:328-330`); zero impacte de dades.

---

## TAULA FINAL de riscos (per al CTO)

| # | Àrea | Estat | Risc / bloqueig | Àncora |
|---|------|-------|-----------------|--------|
| R1 | **`off_recipe` mateix `task_type`** | ⚠️ BLOQUEJANT | `unique_together(model,task_type)` fa que un EXTRA del mateix tipus violi la BD; `origen` no és a la clau. Decisió d'esquema abans de dissenyar extres. | `tasks/models.py:97` |
| R2 | WorkOrder / DeliveryNote / Expense | Construcció nova | Cap dels tres existeix; no hi ha FK `Model↔order_line`. Bastida (AbstractDocument, hook) sí. | `commerce/models_base.py:28`; grep `class WorkOrder`/`DeliveryNote` buit |
| R3 | Trigger col·lector lazy | ✅ Ancoratge sòlid | `if rows:` idempotent per-model; però la unicitat "(customer, mes)" del col·lector NO la dona aquest guard — cal guard propi. | `services_c.py:103` |
| R4 | Escriptura cross-schema al hook | ⚠️ Fragilitat | Signal escriu a PUBLIC dins l'`atomic` del tenant; commit-order no confirmable per lectura. Si el WorkOrder és PUBLIC, s'hi afegeix una 3a escriptura. | `services_c.py:99`, `backoffice/receivers.py:10` |
| R5 | `except` silenciós al hook | ⚠️ Pèrdua silenciosa | Un WorkOrder que falli aquí es perd fins a reconcile; cal branca a `reconcile_consumption.py` des del principi. | `services_c.py:119-123` |
| R6 | Tancament de WorkOrder | Dimensionat | "Totes tancades" = totes `Done`; el `Paused` auto-generat ("1 InProgress per tècnic") és el risc de tancament penjat. Cap flag Blocked. | `services_c.py:60-67`; `tasks/models.py:63` |
| R7 | Sessions de fitting al detall | Vincle nou | No generen ModelTask; registre autònom sense FK a comanda. Claus per llistar-les hi són (model→customer, data, gates). | grep `model_task` a `fitting/` buit; `fitting/serializers.py:119-149` |
| R8 | TimerEntrada granularitat | Limitació | Font vàlida del detall temporal però no baixa a peça i no exposa `task_type`/`facturable` a l'API (cal JOIN). | `tasks/models.py:4-18`; `tasks/serializers.py:7-8` |
| R9 | DeliveryNote ↔ DocumentDueDate | Decisió humana | 3a FK (escala mal ×N doc_types) vs GenericFK (reobre decisió B3b). Només si l'albarà porta venciments. | `commerce/models.py:401,416-420` |
| R10 | GTI obligatori | ✅ Baix | Zero backfill (0 NULL); només guards al wizard front+back. | `ModelWizard.jsx:181-183`; `views.py:266` |
| R11 | Homònim `TechnicianQueueOrder` | Nota | "Order" = cua de tècnic, NO comanda; no confondre en dissenyar WorkOrder. | `planning/models.py:82` |
| R12 | `inici` de TimerEntrada del client | PENDENT | `inici` l'aporta el client sense default de servidor; verificar si algun punt el força. | `tasks/models.py:7`; `tasks/views.py:44` |

---

### PENDENTS DE VERIFICAR (fora de l'abast read-only o no confirmables per lectura)
- Commit-order public↔tenant dins l'`atomic` del hook amb connexió compartida (R4).
- Rol de `ConsumAlbara` (`models_app/models.py:744`) respecte del DeliveryNote de B4 (BLOC 5).
- Camí `GarmentSet→customer` quan una FittingSession apunta a set, no a model (BLOC 5).
- Si un albarà de B4 porta venciments (decideix si R9/DocumentDueDate aplica).
- Si `inici` de TimerEntrada es força al servidor en algun altre camí (R12).
