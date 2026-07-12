# DIAGNOSI — Tasca unificada de presa de mesures sobre peça física

> Data: 2026-07-10 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
> HEAD de la investigació: `8038d56`. **Cap línia de codi tocada.**
> Convenció: `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi (no especulat).**
> Addendum de `DIAGNOSI_DISSOLUCIO_FITTINGDETAIL_2026-07-10.md`.
> Equip: director-investigacio + investigador-codi ×4 + documentador.

**Decisió de l'Agus que emmarca aquest cens (no es re-litiga, es contrasta):** la
sessió/convocatòria és un **CONTENIDOR** que agenda i llança tasques; el treball sempre passa
per `ModelTask`. La tasca serveix fitting **i** check sobre maniquí (mateix acte físic, llei §2);
el que canvia és el camí d'entrada i l'origen al log (`FITTED` / `CHECKED`).

---

## Resum executiu

1. **La "tasca unificada" JA existeix com a `TaskType`: `code='size_check'`, name "Mesurar
   prenda", eina `mesures`, mode `presa` (pk=20 a fhort).** Sembrada al catàleg canònic
   (`tasks/migrations/0025_seed_canonical_task_types.py:15`). **No existeix cap `TaskType` de
   fitting** (confirmat absent): el fitting mai ha estat una tasca de catàleg. La decisió
   "size_check evolucionat vs type nou" es redueix a: **reusar el pk=20 o crear-ne un altre.**
2. **Reusar `size_check` no perd res; un type nou obliga a migrar dades reals.** Volums a fhort:
   **3 `ModelTask`** (2 Done, 1 Paused), **2 cel·les `TaskTimeEstimate` madures (n=5)**, **52
   `TaskTransition`**, i **5 literals `task_type__code='size_check'`** hardcoded. Un type nou
   parteix de n=0 al Welford i cal remapejar-ho tot; el pk (20) no s'usa mai com a àncora, el
   `code` sí.
3. **El cicle de vida de tasca és 100% heretable i net.** `transition_task`
   (`tasks/services_c.py:95-203`) —guard d'estats, exclusió "una-sola-InProgress per tècnic",
   timer, auto-assign, auto-start de fase, log— **no consulta `task_type.code` enlloc**.
   Qualsevol tasca llançada per la convocatòria ho hereta gratis. Els únics acoblaments són al
   mòdul comercial, aïllats en savepoints no-fatals, no a size_check.
4. **El patró de reagendament té UN sol punt d'acoblament dur.** `_reagenda_tasca_size_check`
   (`models_app/services_size_check.py:251-276`) és mecànicament genèric (només toca `planned_*`
   de `ModelTask` + calendari laboral), però (a) selecciona la tasca amb el literal
   `task_type__code='size_check'` (`:262`) i (b) viu al mòdul equivocat. El "+5 dies laborables"
   **no és de la reagenda**: és un default de UI al serializer (`serializers_size_check.py:72-75`).
5. **No hi ha doble comptabilitat de temps, perquè no hi ha TaskType de fitting.** Dos comptadors
   desacoblats: `TimerEntrada`→`TaskTimeEstimate` (feina tècnica) i
   `FittingSession`→`FittingDurationStat` (acte de prova). Mesuren actes diferents. 🔴 **Però si
   la unificació fa que l'acte de prova passi a ser una `ModelTask` de `size_check`, els dos
   comptadors passarien a mesurar el MATEIX acte** — és el risc de disseny número u.
6. **`FittingDurationStat` és un cul-de-sac: s'escriu i ningú el llegeix (confirmat absent), i a
   BD està BUIT (0 files).** La durada de fitting no apareix a cap informe de temps. La sessió
   139, de fet, tenia durada real ~377 min > guard de 240 → descartada, mai va entrar cap mostra.
7. **No hi ha cap àncora `ModelTask`↔`FittingSession` avui (confirmat absent als dos costats).**
   Les dues vies sense camp nou (Watchpoint.dades, convenció temporal) són d'alta fragilitat o
   abús semàntic. **El mínim fiable és 1 FK nullable**; els imports creuats són tots lazy, així
   que un FK per string és net en qualsevol direcció — el criteri decisiu és **on viu
   l'escriptor**, no el cicle d'imports.

---

# A1 — Catàleg de `TaskType`

## A1.a — El model i la identitat

**A1-1.** `TaskType` (`tasks/models.py:21-58`) és catàleg **canònic read-only** (el tenant no
l'edita, `:22`). Camps: `code` (`:38`, `SlugField unique` — **és la identitat**), `name` (`:39`),
`default_order` (`:40`), `active` (`:41`), `fase` (`:43`), `tipus` (`:44`), `eina` (`:45-47`),
`mode` (`:48-49`), `facturable` (`:50`). `__str__` = `code` (`:57-58`).

**A1-2.** **No hi ha `slug` separat ni s'usa el `pk` com a identitat de negoci.** El seed és
`update_or_create(code=...)` (`0025:29`), i tots els consumidors filtren per `task_type__code=`,
mai per pk. **Cap flag de gate/bloqueig** viu al `TaskType` (`:23-25`).

## A1.b — Les 14 instàncies (BD fhort, verificat)

**A1-3.** 14 files. Les rellevants per a la unificació:

| pk | code | name | eina | mode | fase |
|---|---|---|---|---|---|
| **20** | **`size_check`** | **Mesurar prenda** | **mesures** | **presa** | (Dev. tècnic) |
| 15 | `pom` | Definició POM | mesures | autoria_base | |
| 21 | `grading` | Escalat | escalat | propagacio | |

La resta: `design_review`, `design_clarify`, `pattern_digit/cad/hand/review`, `tech_sheet`,
`bom`, `scaling`, `marking`, `audit`.

## A1.c — Fitting i check al catàleg

**A1-4. `TaskType` de fitting: NO EXISTEIX (confirmat absent).** `grep -n "fitting"` a
`0025_seed_canonical_task_types.py` → cap. El fitting viu a `fhort.fitting` via
`FittingSession`/`PieceFitting`, **fora** del sistema de tasques.

**A1-5. El check SÍ: `code='size_check'` (pk=20), name "Mesurar prenda".** Sembrat a
`0025:15`. La `name` ja és genèrica ("Mesurar prenda"), no "size check" — **el catàleg ja anticipa
l'acte físic unificat**, només l'eina/mode l'ancoren al camí actual (`mesures`/`presa`).

**A1-6. Els 5 literals `'size_check'` hardcoded** (sempre `task_type__code=`, mai pk):
`models_app/services_size_check.py:217` (finalitza tasca en resoldre), `:262` (reagenda);
`models_app/management/commands/clone_model_for_qa.py:115,117` (clon QA). Qualsevol canvi de `code`
els trencaria; el pk no s'usa mai com a àncora.

## A1.d — Qui crea el catàleg (G9)

**A1-7.** Únic escriptor de producció: `0025_seed_canonical_task_types.py:29`
(`update_or_create(code=...)`, idempotent, `unseed`=noop). **Alta d'un `TaskType` nou = migració
nova amb entrada al `CATALEG`** → decisió humana, coherent amb G9 (catàleg canònic read-only).
Altres escriptors: fixtures de test (`tasks/tests.py:42,103,165`) i provisió de tenant
(`bootstrap_tenant.py:85,208`, que sembra cel·les d'estimació, no el type).

## A1.e — Estimacions Welford per `garment_type_item`

**A1-8.** El vincle temps és `TaskTimeEstimate` (`tasks/models.py:343-361`) = cel·la
**(`garment_type_item` × `task_type`) → minuts**. FKs `:347,349`, `unique_together` `:356`.
Camps: `estimated_minutes` (seed, `:350`), `n`/`mean_minutes`/`m2` (Welford, `:351-353`).
**El vincle passa sempre per `garment_type_item` (variant), no pel `garment_type` directe.**

**A1-9. Cadena de càlcul:** alimentació en tancar la tasca (`to_status=='Done'` →
`record_actual_time`, `tasks/services_c.py:200-201` → `services_i.py:19-46`); resolució per al
planificador via `lookup_estimated_minutes` (`services_g.py:11`), cascada de 4 graons (cel·la
pròpia madura `n≥5` → empíric global → `TimeSeed` → None). Llindar `WELFORD_MIN_SAMPLES=5`
(`services_i.py:10`).

## A1.f — `PaquetServeiTasca`: NO EXISTEIX (eliminat)

**A1-10.** Va existir (`0005_sprint1b_new_models.py:34`) i està **eliminat**
(`0026_remove_paquetserveitasca_paquet_and_more.py:36-38`: `DeleteModel PaquetServei`,
`PaquetServeiTasca`, `Tasca`). Cap referència viva. El concepte "paquets de servei que despleguen
tasques" es va retirar; **no cal considerar-lo** per a la unificació.

## A1.g — Volum per a la decisió (verificat a BD)

| Actiu de `size_check` | Volum | `on_delete` |
|---|---|---|
| `ModelTask` | **3** (2 Done, 1 Paused, 0 vives-actives) | PROTECT (`models.py:71`) |
| `TaskTimeEstimate` madures | **2** (item 30: n=5, 255 min · item 4: n=5, 75.8 min) | CASCADE (`models.py:349`) |
| `TaskTransition` | **52** | CASCADE (`models.py:118`) |
| Literals `code` hardcoded | **5** | — |

> **Veredicte A1 (cens, no decisió):** **reusar `size_check`** conserva 3 tasques, 2 cel·les
> Welford madures i 52 transicions sense migració, i la `name` ("Mesurar prenda") ja és genèrica.
> **Un `TaskType` nou** parteix de n=0 al Welford, obliga a remapejar 3 ModelTask (PROTECT), 2
> cel·les (CASCADE), 52 transicions i 5 literals, i és una migració de catàleg (decisió G9).
> La via de menys dades trencades és evolucionar el pk=20 (canviar-ne semàntica/eina/mode si cal),
> no crear-ne un de nou. **La decisió segueix sent de l'Agus.**

---

# A2 — Cicle de tasca heretable

## A2.a — `transition_task` pas a pas (`tasks/services_c.py:95-203`)

Signatura `transition_task(task, to_status, profile, force=False)`, `@transaction.atomic` (`:95`);
màquina d'estats `ALLOWED` (`:11-16`): Pending→InProgress; Paused→InProgress; InProgress→{Paused,
Done}; Done→InProgress (reobertura).

**A2-1.** Guard de transició (`:104-105`) → `TransitionError` si il·legal.

**A2-2.** Guard de reobertura albaranada (`:110-113`): Done→InProgress bloquejat si la tasca té
línia d'albarà ISSUED/INVOICED tret que `force=True`. **ACOBLAMENT COMERCIAL** via
`task.delivery_note_lines`, no size_check.

**A2-3. Exclusió "una sola InProgress per tècnic" (`:118-127`) — GENÈRIC.** En entrar a
InProgress, busca l'altra `ModelTask` InProgress del mateix `assignee` (qualsevol model/type), li
tanca el timer, la posa Paused i retorna el seu `paused_task_id`. Global per tècnic.

**A2-4. Timer (`:129-131`) — GENÈRIC.** `_open_timer` (invariant ≤1 obert, `:19-24`) crea
`TimerEntrada(inici=now, actiu=True)`; `started_at = now` només la 1a vegada. Tancament
`_close_open_timer` (`:30-35`): `minuts = max(0, (now−inici)//60)`. **La durada real d'una tasca =
suma de `TimerEntrada.minuts`** (`tasks/models.py:4-10`); no hi ha camp acumulador a `ModelTask`.

**A2-5.** Auto-assign (`:142-143`, GENÈRIC), desa estat + `TaskTransition` log (`:145-147`;
model `:115-131`: `from/to_status`, `by`, `at`, immutable → base de `rectification_count`).

**A2-6. Efectes de la 1a InProgress (`:149-195`), tots aïllats:** fase del model Pending→Dev
(`:150-155`, **GENÈRIC**); meritació SaaS (`:160-184`, savepoint no-fatal); work_order
(`:190-195`, savepoint, comercial). En Done: `record_actual_time` (`:197-201`, alimenta Welford).

> **Veredicte A2.a:** el nucli del cicle és **agnòstic del `TaskType`** — cap consulta a
> `task_type.code` dins `transition_task`. Una tasca unificada llançada per la convocatòria
> hereta timer, exclusió, auto-assign, auto-start de fase i log **sense tocar res**. Els únics
> acoblaments són comercials i aïllats.

## A2.b — Camps de temps de `ModelTask` (`tasks/models.py:61-89`)

`status` (`:63-64,72`: Pending/Paused/InProgress/Done); `started_at`/`finished_at` (`:77-78`);
`estimated_minutes` (`:79`, snapshot en crear); `planned_start`/`planned_end` (`:82-85`, motor
d'scheduling); `planned_locked` (`:86-87`, posició manual fixa); `created_at`/`updated_at`
(`:88-89`).

## A2.c — Reagendament: genèric amb un acoblament dur

**A2-7. Ubicació REAL:** `models_app/services_size_check.py:251-276` (**no** a `tasks/`/`planning/`;
el brief l'ubicava malament — TROBALLA TRANSVERSAL).

**A2-8. Què fa (`:261-273`):** troba la tasca `size_check` viva del model, i la fixa al calendari
laboral: `planned_start = next_working_slot(prof, combine(data, 08:00))`, `planned_end =
add_working_minutes(prof, start, estimated_minutes or 60)`, `planned_locked = True`. Gate tou:
sense tasca/error → False (`:264-265,275-276`). **Només toca `ModelTask` + calendari; cap taula de
check** (`SizeCheck`/`SizeCheckLine`).

**A2-9. L'acoblament dur és UNA línia:** `:262` filtra `task_type__code='size_check'`. És l'únic
vincle al type. Per reusar-la des de la convocatòria caldria parametritzar aquesta selecció; la
mecànica interna ja és 100% genèrica. (Anotat també: mal ubicada al mòdul de check; fallback `60`
min hardcoded a `:269`.)

**A2-10. El "+5 dies" NO és de la reagenda.** La funció accepta qualsevol `data_represa`. El +5 és
un default de UI: `serializers_size_check.py:70-75` → `add_working_days(localdate(), 5)`.

**A2-11. Cridador únic:** `resolve_size_check` (`services_size_check.py:230`) quan `final_estat ∈
('Rebutjat','Descartat')` amb `data_represa` (`:229`), via POST
`/size-checks/<pk>/resolve/` (`views_size_check.py:69`).

## A2.d — Dies laborables: genèric i reusable

**A2-12.** `planning/calendar_service.py`: `add_working_days` (`:119-133`), `add_working_minutes`
(`:96-116`), `next_working_slot`. Funcions lliures de mòdul, sense dependència de tasca ni type,
ja importades des de `models_app`, `fitting/services.py:235,925`, `planning/`. **Reusables tal
com són.**

## A2.e — Vincle tasca → fase

**A2-13.** `advance_phase_gate` (`tasks/services_d.py:24-51`): avança `fase_actual`, escriu
`GateEvent` (`:42-43`) i crida `seal_model_grading` (`:46-49`). Comentari clau (`:35-37`):
"avançar fase NOMÉS canvia el marcador; les ModelTask queden SEMPRE obertes".
`model_ready_for_gate` (`:11-17`): True si **totes** les ModelTask del model són Done (readiness).
Vincle invers d'escriptura: `transition_task` empeny Pending→Dev a la 1a InProgress
(`services_c.py:155`). Cicle i fase **desacoblats en tancament, acoblats en dos punts
d'escriptura**.

---

# A3 — Lligam sessions ↔ tasques a planificació

## A3.a — `calendar/events`: tres fonts, events separats

**A3-1.** `calendar_events_view` (`planning/views.py:214-499`) agrega **tres fonts** sota un
contracte comú, com a events **separats** (mai unificats):

| tipus | Queryset | fitxer:línia | Durada |
|---|---|---|---|
| `tasca` | `ModelTask.exclude(status='Done').filter(planned_start__isnull=False)` | `:237-286` | `planned_start`/`planned_end` |
| `confeccio` | `Production` | `:293-327` | marcador d'1 dia |
| `fitting` | `FittingSession.exclude(estat='Anullada')` | `:342-497` | bloc si `start_time`+durada; `_eff_minutes` (`:334-340`) |

**A3-2.** Un event `tasca` (`id='task-{id}'`, `:270`) i un `fitting` (`id='fitting-{id}'`,
`:408/420`) **coexisteixen com dues entrades independents**; no comparteixen id ni s'enllacen.

## A3.b — Els dos comptadors de temps

**A3-3. Timer de tasca:** `TimerEntrada` (`tasks/models.py:4-9`) → suma `_real_minutes`
(`services_i.py:13-15`) → Welford `record_actual_time` (`services_i.py:18-46`) sobre cel·la
(`item × task_type`). Alimentat en tancar (`services_c.py:200-201`, `models_app/views.py:794`).
Llegit per planning (`plan_service.py:72,301`) i informes (`views_b.py`).

**A3-4. Durada de sessió:** `FittingSession.started_at`/`finished_at`/`duracio_minuts`
(`fitting/models.py:251-266`). `_capture_duration` (`services.py:692-704`), cridat només des de
`_seal_session` (`:689`): `(now − combine(data,start_time)) / nº peces` →
`update_fitting_duration_stat` (`:707-722`). Guard de soroll: descarta si `<0` o `>240 min`
(`:701-702`).

**A3-5. 🔴 Avui NO hi ha doble comptabilitat — perquè no hi ha TaskType de fitting.** El timer de
tasca mesura feina tècnica (pom, grading…); la sessió mesura l'acte físic de prova. Actes
diferents, comptadors diferents. Cap FK creuada (verificat: model 185 té 2 sessions i 3 tasques,
sense referència mútua).

> **🔴 RISC DE DISSENY (la conseqüència directa de la unificació):** si l'acte de prova passa a ser
> una `ModelTask` de `size_check`, aleshores **la mateixa prova física tindria dos rellotges**: el
> `TimerEntrada` de la tasca (feina del tècnic) **i** el `duracio_minuts`/`FittingDurationStat` de
> la sessió contenidora. Avui estan desacoblats perquè viuen en mons separats; unificar-los els
> posa a mesurar el mateix. **PER DECIDIR:** quin rellotge mana quan la sessió és el contenidor i
> la tasca és el treball.

## A3.c — `FittingDurationStat`: cul-de-sac buit

**A3-6.** `FittingDurationStat` (`fitting/models.py:387-402`): Welford incremental de durada real,
**singleton global del tenant** (`get_or_create(pk=1)`, `:711`) — no segmentat per tècnic/garment/
fase. Camps `n_mostres`/`mitjana`/`m2_acum`/`desviacio` (`:391-395`).

**A3-7. Escrit per `update_fitting_duration_stat` (`:707-722`); LLEGIT PER NINGÚ (confirmat
absent).** No apareix a planning ni a informes.

**A3-8. A BD: 0 files (verificat).** La sessió 139 tenia durada real ~377 min > guard 240 →
descartada. Cap mostra ha entrat mai. **És una estadística escrita i mai consumida.**

## A3.d — L'únic acoblament real: la franja busy

**A3-9. TROBALLA TRANSVERSAL.** El sol contacte sessió↔planificació és
`scheduler_service._collect_busy_intervals` (`scheduler_service.py:95-114`), que llegeix les
`FittingSession` vives de l'assistent i les injecta com a franges `busy` (`:181-182`): les
`ModelTask` es col·loquen **al voltant** de la sessió. Per això `_seal_session`/`schedule_session`
criden `recompute_for_technicians` (`fitting/services.py:210,294,686`). Aquí la sessió consumeix
temps de cua **via `duracio_minuts`, no via cap tasca**.

**A3-10.** L'informe de temps per model (`time_by_model_view`, `views_b.py:1085`) **ignora la
durada de fitting**: només agrega `ModelTask` + `TimerEntrada` (`:1108-1121`). El temps de fitting
no és a cap informe.

## A3.e — Convivència a BD (model 185, verificat)

```
FittingSession: #138 Oberta (data 06-22, dur 10)  ·  #139 Tancada (data 07-11, start 09:00, conv 79e06e8a…)
ModelTask:      #252 grading Done  ·  #247 pom Paused  ·  #248 size_check Paused (planned 07-14 09:15, est 76)
```
18 models tenen sessions **i** tasques (162-177, 182, 185). **No es refereixen entre elles.**

---

# A4 — Àncora tasca ↔ sessió

## A4.a — Camps existents (cap punter creuat)

**A4-1. `ModelTask` (`tasks/models.py:61-95`):** FKs a `model` (`:70`), `task_type` (`:71`),
`assignee` (`:74`), `work_order` (`:92`). Camp `origen` = CharField amb 2 valors fixos
(`prevista`/`ad_hoc`, `:73`), **no un punter lliure**. **Cap FK a `FittingSession`/convocatòria;
cap `JSONField` (confirmat absent).** L'únic "contenidor" és `work_order`.

**A4-2. `FittingSession` (`fitting/models.py:202-268`):** FKs a `garment_set`/`model` (XOR),
`responsable`; M2M `attendees` (`:254`); `convocatoria` = **`UUIDField` null, no FK** (`:258`).
**Cap FK/M2M a `ModelTask` (confirmat absent).** Les úniques relacions inverses són `PieceFitting`
i `FittingPhoto` (mateixa app).

## A4.b — Via Watchpoint

**A4-3.** `Watchpoint.task` → FK a `ModelTask` (`SET_NULL`, `models_app/models.py:929-930`);
`Watchpoint.dades` → `JSONField null` (`:935`), amb semàntica **ja ocupada** (no-null = watchpoint
de sistema/import, `:932-934`). A BD: 5 watchpoints, `dades=None` en tots, 1 amb `task`, **cap
referencia una sessió.**

> **Verdict:** pont **possible però impropi** — `dades` té semàntica ocupada, un watchpoint és una
> advertència de model (no un connector d'agenda), i no és 1↔1 (un model pot tenir N watchpoints
> amb `task` NULL).

## A4.c — Via convenció temporal

**A4-4.** `ModelTask.planned_start` = **DateTimeField** (`:82`); `FittingSession.data` = **DateField**
+ `start_time` = **TimeField** nullable (`:230-231`). **Fragilitat ALTA:** tipus dispars; en bulk
sovint sense hora (només coincidiria el dia, `fitting/services.py:284-289`); múltiples tasques/
sessions el mateix dia; `planned_start` el recalcula el motor contínuament
(`recompute_for_technicians`) → **no és estable.**

## A4.d — Creadors (on s'injectaria l'àncora)

**A4-5. `ModelTask` — 5 creadors:** `_open_task` ad-hoc (`views_b.py:295`), `define_model_tasks_view`
(`:355`), **`open_task_view` (`:552`, crea-si-falta en obrir l'eina — AQUÍ s'obre "Mesurar
prenda")**, `plan_service.assign` (`plan_service.py:310`), `clone_model_for_qa` (`:118`). **Cap rep
avui un `session_id`.**

**A4-6. `FittingSession` — 3 creadors** (`create_session`/`schedule_session`/`schedule_bulk`,
`fitting/services.py:127-299`): **cap crea ni toca cap `ModelTask`.** Tasques i sessions són **mons
separats**; les úniques passarel·les són el segellat de fase (`services_d.py:46` →
`seal_model_grading`) i `Production`.

## A4.e — Direcció del FK: matís sobre imports

**A4-7.** Els imports creuats `tasks`↔`fitting` són **tots lazy** (dins funcions): `tasks` importa
`fitting` a `services_d.py:46`; `fitting` importa `tasks` a `views.py:227` i `services.py:757`. **A
nivell de mòdul, cap importa l'altre.** Per tant un **FK per string (`'fitting.FittingSession'` o
`'tasks.ModelTask'`) és net en qualsevol direcció** — Django resol el FK per string sense import,
i no hi ha cicle a nivell de mòdul. **El criteri de direcció no és el cicle d'imports** (contra la
lectura inicial), **sinó on viu l'escriptor** que coneix les dues bandes en el moment de crear.

## A4.f — Veredicte de vies (cens, no decisió)

| Via | Existeix avui | Cal afegir | Escriptor natural | Fragilitat |
|---|---|---|---|---|
| **FK `ModelTask.fitting_session`** | res | 1 FK nullable SET_NULL (per string) | `open_task_view` (`:552`) o la creació de sessió | **BAIXA** (1↔1 explícit) |
| **FK `FittingSession.model_task`** | res | 1 FK nullable (per string) | `schedule_session`/`schedule_bulk` — que avui **no coneixen cap tasca** | **BAIXA**, però obliga a fer arribar el `task_id` fins allà |
| Watchpoint (`.task` + `.dades`) | camps existents | 0 camps (escriure `session_id` a `dades`) | — | ALTA (abús semàntic, no 1↔1) |
| Convenció temporal | camps existents | 0 camps | — | ALTA (tipus dispars, hora nullable, volàtil) |
| Reús `convocatoria` UUID a ModelTask | UUID a sessió | 1 camp UUID a ModelTask (camp nou igualment) | creador de tasca | MITJANA (agrupa, no identifica 1 sessió) |

> **Cost G9 mínim:** un sol FK nullable. **Sense camp nou no hi ha via fiable** (només Watchpoint.
> dades o convenció temporal, totes dues impròpies/fràgils). El punt d'escriptura més natural ja
> existeix i coneix les dues bandes: **`open_task_view` (`tasks/views_b.py:552`)** obre la tasca
> `size_check` en obrir l'eina `mesures`; si la unificació fa que aquesta obertura vingui de la
> convocatòria, allà es tindria el `session_id` a mà. La decisió (direcció, o si cal l'àncora)
> és de l'Agus.

---

# CADENES OBERTES (declarades)

| # | Cadena | On es tanca / s'escapa |
|---|---|---|
| **CO-A1** | Reusar `size_check` vs type nou: 3 ModelTask (PROTECT) + 2 cel·les Welford + 52 transicions + 5 literals | `tasks/migrations/0025:15`; decisió G9 |
| **CO-A2** | `_reagenda_tasca_size_check` genèrica excepte `task_type__code='size_check'` | `models_app/services_size_check.py:262` |
| **CO-A3** | 🔴 unificar l'acte de prova en ModelTask crea DOS rellotges del mateix acte (TimerEntrada vs duracio_minuts/FittingDurationStat) | `fitting/services.py:692-722` vs `tasks/services_i.py` |
| **CO-A4** | `FittingDurationStat` escrit i mai llegit; 0 files a BD; guard 240 min descarta sessions llargues | `fitting/services.py:707-722`, `:701` |
| **CO-A5** | Cap àncora ModelTask↔FittingSession; mínim fiable = 1 FK nullable | `tasks/models.py:61-95`, `fitting/models.py:202-268` |
| **CO-A6** | El fitting NO és un TaskType; tota la seva vida (timer, fase, log) queda fora del cicle de tasca fins que s'unifiqui | A1-4 |
| CO-9 (heretada) | Motor de grading no auditat: zona intocable | `pom/grading_utils.py:560` |

---

# PER DECIDIR (Agus)

1. **Reusar `size_check` (pk=20) o `TaskType` nou** (A1.g). Reusar conserva dades i la `name` ja
   és genèrica; un type nou és una migració de catàleg (G9) i parteix de n=0 al Welford.
2. **Eina/mode de la tasca unificada.** `size_check` avui és eina `mesures`, mode `presa`. La
   unificació fitting+check ha de canviar-los, afegir-ne un de nou (`FITTED`/`CHECKED` com a
   sub-mode), o resoldre l'origen al log per una altra via? (A1-5.)
3. **🔴 Els dos rellotges** (A3.b, CO-A3). Quan la sessió és contenidor i la tasca és el treball,
   quin temps mana: el `TimerEntrada` de la tasca o el `duracio_minuts` de la sessió? Avui
   `FittingDurationStat` no el llegeix ningú i està buit — es jubila, o es connecta?
4. **Direcció de l'àncora** (A4.f). `ModelTask.fitting_session` (escriptor a `open_task_view`, ja
   coneix les dues bandes) o `FittingSession.model_task` (obliga a portar el `task_id` fins a
   `schedule_*`)? O es prova la convenció temporal (fràgil)?
5. **Extreure `_reagenda_tasca_size_check`** (A2.c, CO-A2). Per reusar-la des de la convocatòria
   cal parametritzar el `task_type__code` i, opcionalment, moure-la a `planning/`. És refactor de
   scope acotat.
6. **Qui llança la tasca des de la convocatòria.** Avui `schedule_bulk` només crea sessions
   (A4-6). Materialitzar la `ModelTask` en agendar, o en obrir la sessió, o en obrir l'eina
   (`open_task_view`, com ara)? Enllaça amb el punt d'inserció de GarmentSet de la diagnosi
   germana (CO-Y9).

---

# FRONTERES (què NO s'ha de tocar)

- **Motor de grading (G6):** intacte (heretat).
- **`transition_task` i el cicle de tasca** (`tasks/services_c.py`): es reusa, no es reescriu. El
  seu comportament genèric és el fonament de la unificació.
- **Catàleg `TaskType` canònic** (`tasks/models.py:21`, seed `0025`): alta/canvi = migració +
  decisió G9, mai escriptor tenant.
- **`close_piece_fitting`/`_seal_session`/`seal_model_grading`:** es criden, no es reescriuen
  (frontera heretada del Sprint X).
- **Zones `CLAUDE.md`:** POMs, grading engine, motor de patrons.

---

*Cap línia de codi tocada. Cap dada de staging modificada. Els FETS d'alt risc (identitat i pk de
`size_check`, volums de migració, cul-de-sac de `FittingDurationStat`, absència d'àncora, direcció
lazy dels imports) han estat re-verificats pel director contra la BD i el codi, no només contra els
informes dels investigadors.*
