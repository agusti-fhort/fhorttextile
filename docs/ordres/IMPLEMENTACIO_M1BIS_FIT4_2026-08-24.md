# M1-bis · FIT-4 — R1 automàtica i replicació a R2+

> **Patró B · IMPLEMENTA.** Backend only. Tanca el nucli de rondes; la UI és M2.
> **Deliverable únic**: aquest fitxer. **Cap push** — el fa l'Agus.
> Continua i **supera dues coses** de `IMPLEMENTACIO_M1_RONDES_2026-08-24.md` (§2 i §4), que
> queda segellada al capdamunt amb el que ja no hi és vigent.

---

## 0 · CAPÇAL

| Fet | Valor |
|---|---|
| Worktree | **`/var/www/ftt-m1`** (reutilitzat), branca nova **`m1bis-fit4`**, creada de `dev` a **`0e3a5eb6`** |
| Com s'ha posat al dia | `git checkout -b m1bis-fit4 0e3a5eb6` sobre el mateix worktree. **No calia rebase**: `m1-rondes` ja és dins de `0e3a5eb6` (el merge d'M1), o sigui que la branca nova en surt directament. L'arbre estava net (només el symlink `backend/venv`) |
| HEAD d'arribada | `47ad7228` — **5 commits de codi/QA**, cap push (+ aquesta acta) |
| Migracions noves | **CAP.** V. §6 — i és un fet verificat, no una omissió |
| Fitxers del motor tocats | **cap**: res de `patterns/**`, res de `frontend/**` |
| Model 1383 | **no tocat**: cap tasca, cap entrada al Taller |
| Servei | ⚠️ **`ftt-staging.service` NO reiniciat** (mateixa raó que a M1: serveix un altre arbre amb feina viva del motor). Fum amb gunicorn propi del worktree |

---

## 1 · FASE 0 · ELS GESTOS QUE HAN DE DISPARAR LA R1

### 1.1 · Cens complet: qui crea una `ModelTask` de producte

`grep` de `ModelTask.objects.create|get_or_create|ModelTask(` a tot `backend/fhort`, tests fora.
**Set punts**, i cadascun amb el seu ordre i la seva estimació escrits a mà:

| # | Punt | Gest de l'usuari | Ja tenia ronda? |
|---|---|---|---|
| **A** | `tasks/views_b.py:291` · `ModelTaskViewSet.extra` (`POST /model-task-items/extra/`) | extra **off_recipe** sobre un WorkOrder | ❌ naixia òrfena |
| **B** | `tasks/views_b.py:351` · `define_model_tasks_view` | **programar** la feina del model (bulk) | ❌ |
| **C** | `tasks/views_b.py:581` · `open_model_task_view` | **entrar-hi i executar** (crea-si-falta) | ❌ — i el comentari de `:575` ho deia: *«la ronda no es crea per aquí»* |
| **D** | `tasks/views_b.py:1646` · `crono_declarat_view` (`accio='engegar'`) | engegar el **crono** d'una externa | ❌ |
| **E** | `planning/plan_service.py:323` · `assign_batch._apply_one` | **wizard d'assignació** (crea si no hi és) | ❌ |
| F | `tasks/services_r.py:139` · `obrir_ronda` | +Ronda explícit | ✅ ja hi lligava |
| G | `tasks/services_r.py:194` · `obrir_correccio` | correcció | ✅ hereta la de la mare |

Fora de producte i **no tocats**: `models_app/management/commands/clone_model_for_qa.py:139` i
`sembra_model_837.py:766` (commands de QA/sembra).

### 1.2 · Gestos que **NO** creen tasques

| Punt | Què fa |
|---|---|
| `plan_service.assign_model:197` (`POST /models/<id>/assign/`) | assigna tasques **que ja existeixen**; si no n'hi ha cap de no-Done, **`ValueError`** |
| `plan_service.unassign_model:440` | desassigna |
| `models_app/views.py:1946` · `_assegura_pom_task_oberta` | **no crea**: si `tasca_vigent` no en troba cap, retorna `no_pom_task` |
| `services_scheduling.reagenda_tasca:15` (FIT-7) | només llegeix, via `tasca_vigent` |

### 1.3 · Hi ha UN punt únic on enganxar-ho? **NO. I no me n'he inventat cap.**

Els cinc punts A–E fan cadascun el seu `ModelTask.objects.create(...)` amb la seva pròpia lògica
d'`order` i d'`estimated_minutes`. No hi ha cap servei de creació de tasques pel qual passin tots
—a diferència de `transition_task` per als estats o `tasca_vigent` per a la resolució.

**Les dues sortides que he descartat, i per què:**

- **Un `pre_save`/`post_save` a `ModelTask`.** Seria el punt únic de debò, però s'enduria
  **tot**: les migracions de dades, `sembra_model_837`, `clone_model_for_qa` i els *fixtures* de
  ~57 fitxers de test. Fabricaria rondes on no hi ha cap gest humà, i violaria la sub-decisió (b)
  el primer cop que una migració toqués una tasca vella.
- **Un servei nou `crea_tasca(...)` que unifiqui els cinc.** És la refactorització correcta, però
  és un tram propi: cada punt té guards, permisos i respostes diferents, i unificar-los canviaria
  cinc portes HTTP en un sprint que havia de ser curt. **Anotat com a deute** (§8).

**El mínim de punts és 5**, i el que s'hi enganxa és **una sola línia**
(`ronda=ronda_del_gest(model)`) que crida **un sol servei**. La política viu en un lloc; el que es
reparteix és la crida.

### 1.4 · Contrast amb l'acta de M1 §2 — confirmat

| Afirmació d'M1 | Segueix sent certa? |
|---|---|
| `obrir_ronda` no replica: els codes els tria qui crida (`:116,:130,:137`) | ✅ (fins a aquest sprint) |
| `Ronda.objects.create` apareix **una sola vegada** a tot el backend | ✅ — i ara en són **dues**: aquella i `ronda_del_gest` |
| `mare = tasca_vigent(model, code)`, resolt **abans** de crear la Ronda (`:130`) | ✅ intacte |
| `motiu` es duplica a la Ronda i a la tasca; `obrir_ronda` les escriu iguals | ✅ intacte |
| `ronda_seq` = «null = la 1a, implícita» (`serializers_b.py:35`) | ❌ **ja no**: reescrit, v. §2.3 |

---

## 2 · FASE 1 · LA R1 NEIX DEL PRIMER GEST

### 2.1 · El servei — `services_r.ronda_del_gest(model)`

Tres respostes, i cap és arbitrària:

| Cas | Resposta | Per què |
|---|---|---|
| Hi ha una ronda **oberta** | **aquella** | FIT-4: *«es pot obrir una tasca lliure que ENTRA EN AQUESTA RONDA»*. La feina que apareix enmig d'una volta és feina d'aquella volta |
| El model **no té cap ronda** | **crea la R1, `seq=1`** | La llei nova |
| Té rondes però **totes tancades** | **`None`** | Obrir-ne una de nova aquí fabricaria una R(n+1) automàtica, i FIT-4 diu el contrari: *«R2+ neixen amb +Ronda explícit»*. Aquesta feina espera que el PM obri la volta. **Interpretació declarada** — v. §8 |

### 2.2 · On s'ha enganxat, i on **no**

Als cinc punts A–E, sempre **dins d'una transacció** amb la creació de la tasca: no pot quedar
mai una tasca sense la seva ronda. A `define-tasks` la ronda es resol **un cop per lot** —totes
les tasques d'una mateixa crida són del mateix gest i van a la mateixa volta.

🔒 **On NO s'ha enganxat, i és la meitat important de la feina:**

- **Assignar una tasca que ja existeix** (`assign_model`, i la branca `elif` d'`assign_batch`)
  **no li toca la ronda**. Assignar no és crear, i moure-la seria **migrar feina entre voltes**,
  que FIT-6 prohibeix.
- **`open-task` quan `tasca_vigent` troba una tasca**: no es crea res, i per tant no es toca res.
- Cap tasca `ronda=NULL` preexistent s'adopta.

> **Sobre FIT-4 i l'«assignació» com a primer gest.** FIT-4 llista l'assignació entre els gestos
> que fan néixer la R1, i la sub-decisió (b) prohibeix adoptar tasques `ronda=NULL`. Semblen
> xocar, però **no arriben a xocar mai**: `assign_model` **exigeix que ja hi hagi tasques**
> (`ValueError('El model no té tasques no-Done per assignar.')`, `plan_service.py:213`), o sigui
> que en un model d'ara endavant **no pot ser mai el primer gest** —alguna cosa n'ha creat abans,
> i allò ja va obrir la R1. Sobre un model LLEGAT sí que podria ser-ho, i és exactament la
> població que (b) diu de no tocar fins a M5. La branca d'`assign_batch` que **crea** la tasca sí
> que obre la R1 (test `test_gest_assign_batch`). No he hagut de triar res: les dues lleis apunten
> al mateix cop que es mira quin codi hi ha a sota.

### 2.3 · La llei escrita, canviada

**`tasks/models.py` · docstring de `Ronda`** — abans:

> *«`seq` és el número de volta dins del model (**la ronda 1 és implícita**: tota la feina
> històrica té `ModelTask.ronda = NULL`). No hi ha cap backfill i no n'hi ha d'haver […]»*

…i ara:

> *«`seq` … **comença a 1**. 🔄 **LA LLEI HA CANVIAT (M1-bis · FIT-4).** Fins avui la R1 era
> implícita […]. Ara **la R1 neix sola del PRIMER GEST DE TREBALL** […] i és l'ÚNICA volta que es
> crea sola. ⛔ **I LA PROHIBICIÓ DE BACKFILL ES MANTÉ — FINS AL RETROACTIU (M5).** L'obertura
> automàtica només mira endavant […]; el dia que es faci, es farà **com a acte declarat** al
> retroactiu de M5, no com a efecte secundari d'una migració.»*

Dos contractes més que deien la llei vella i que ara diuen la nova:

- `tasks/serializers_b.py:35` — `ronda_seq`: **`null` ja no vol dir «la 1a»**. Vol dir feina
  d'abans del canvi de llei, o feina nascuda amb totes les voltes del model tancades.
- `models_app/serializers.py:276` — `ronda_oberta`: `null` = el model no té cap volta **oberta**,
  no «encara no n'hi ha cap i la 1a és implícita».

### 2.4 · Idempotència sota concurrència

**La imposa la BD, no un `if`.** `Ronda.Meta.constraints` ja portava
`UniqueConstraint(fields=['model','seq'], name='uniq_ronda_model_seq')` des d'M1, i
`ronda_del_gest` s'hi recolza amb `get_or_create(model=model, seq=1, …)`: dos gestos simultanis
sobre el mateix model xoquen a la constraint i el perdedor rellegeix la fila del guanyador. **No
cal cap lock i no n'he posat cap** — un `select_for_update` aquí seria una segona política que
caldria mantenir al dia amb la primera. Tres tests ho fixen, un d'ells provant que la constraint
hi és de debò (`IntegrityError` en forçar la segona R1 a mà).

---

## 3 · FASE 2 · LA VOLTA NOVA HEREDA EL JOC

`codes_a_replicar(ronda)` retorna els **codes** (G9) de la volta, dedupats i **en l'ordre de
treball**. `obrir_ronda` els posa davant i **hi suma** els que demani el cridador.

| Regla | Com |
|---|---|
| Còpia per **CODE SLUG** (G9) | `dict.fromkeys(t.task_type.code for t in …)`. Files noves, mai les mateixes |
| Estats nous a **Pending**, temps a zero | és el que `obrir_ronda` ja feia; les replicades neixen sense `started_at`, `finished_at` ni timers |
| Genealogia `mare`/`motiu` | **com M1 la va deixar**, sense tocar (v. el defecte trobat a §8) |
| **No** es copien assignacions | no s'hereta l'`assignee` de la volta anterior. El que hi ha és el comportament actual (`assignee=profile`, qui obre), que FIT-4 diu de no tocar |
| **No** es copien timers ni notes | no es copia cap fila: només el joc de codes |
| La R(n) **no es toca** | FIT-6. Test que compara `(pk, status)` de totes les seves tasques abans i després |

**Els codes del cridador són ADDITIUS, no substitutius.** La proposta replicada no es pot
«desmarcar», i el motiu és literal a FIT-4: les replicades *«es poden no executar»* — la manera de
no fer-ne una és **no fer-la**, no treure-la de la volta. Conseqüència pràctica: `obrir_ronda`
accepta ara la llista **buida**, que passa a ser el cas normal d'un +Ronda que només vol repetir.

**Dos canvis de porta que la rèplica obligava:**

1. Un code **replicat** que el catàleg hagi desactivat des de l'altra volta **s'omet i es diu**
   (`codes_omesos` a la resposta). Un code **demanat** inexistent segueix sent rebuig dur. Sense
   això, desactivar un `TaskType` tombaria el +Ronda de tots els models que l'havien fet servir,
   sense que ningú hi hagués fet res.
2. **L'allow-list de `obrir_ronda_view` es queda només amb el que es DEMANA.** Aplicada també a la
   rèplica, un PM que no executi (posem) `pattern_cad` no podria obrir **cap** volta d'un model
   que en va fer: la porta de +Ronda quedaria tancada precisament per a qui l'ha de fer servir.
   El joc replicat no és una tria seva; és el que el model ja arrossega.

### 🚩 3.1 · ATURADA PARCIAL — el filtre del que NO es replica

El brief diu: *«Si la R(n) té tasques ad_hoc/lliures: còpia també? NO — només les de catàleg»*, i
demana aturar-se si el codi hi porta la contra. **Hi porta la contra, i aquesta és:**

| Camp que semblaria dir-ho | Per què **no** serveix |
|---|---|
| `origen='ad_hoc'` | **Totes** les tasques que crea `obrir_ronda` neixen `ad_hoc` **a posta** (`services_r.py:102-103`: és el que les deixa conviure amb la `prevista` sota la unique parcial). Filtrar per `origen='prevista'` replicaria tot R1→R2 i **res** de R2→R3 |
| `motiu='nova_mostra'` | Marca les que va proposar la volta anterior, però **la R1 no en té cap**: les seves tasques neixen dels gestos normals amb `motiu` NULL. R1→R2 no replicaria res |

I el fons del problema: **a la R1 les dues categories són indistingibles**, perquè la R1 no té
proposta — *totes* les seves tasques s'han obert lliurement.

**El que s'ha fet mentrestant** (i el test `test_la_R3_replica_de_la_R2_i_no_de_la_R1` en fixa la
conseqüència): s'exclou **`off_recipe=True`**, l'únic camp que literalment vol dir «extra fora de
la recepta». Les **correccions no calen a la llista**: comparteixen el `code` de la tasca que
corregeixen i la còpia va per code, o sigui que col·lapsen soles.

Viu en una constant amb nom, **`_NO_ES_REPLICA`** (`services_r.py`), perquè la teva decisió sigui
**una línia**. 🚩 **Decisió pendent d'Agus.**

---

## 4 · FASE 3 · LA CAPABILITY DE L'ENTREGA

`POST /rondes/<id>/entrega/` i `PATCH /entregues/<id>/ok-client/` passen de `IsAuthenticated` a
**`_ExecuteTasks`** (`EXECUTE_TASKS`) — *qui pot treballar pot entregar*. **El `TODO(M1)` queda
retirat del codi.** Amb això desapareix l'asimetria que vaig deixar declarada a M1: la porta que
**tanca** la ronda era més oberta que la que l'obre.

El `GET /models/<id>/rondes/` es queda a `IsAuthenticated`: **llegir no és treballar**.

Tres tests: 403 al POST sense la capability, 403 al PATCH, i 201 amb ella. El fum HTTP ho torna a
comprovar contra la porta real amb el JWT d'un usuari amb `permisos={'revoke': ['execute_tasks']}`.

---

## 5 · BANC I FUM

`ops/qa/banc_m1_rondes.py` (idempotent, `--remunta`) **ja no obre la R1 amb `obrir_ronda`**: la fa
néixer del gest, amb la mateixa línia que els cinc punts de producte. Un banc que l'obrís a mà
provaria un camí que el sistema ja no recorre.

| Model | Rondes | Tasques |
|---|---|---|
| `QA-M1-0001` · Estats variats | **R1** | `pom:Done` · `tech_sheet:InProgress` · `grading:Paused` · `sample_check:Pending` |
| `QA-M1-0002` · Tot fet | **R1** | `pom:Done` · `tech_sheet:Done` |
| `QA-M1-0003` · Verge | **cap** | (cap) — 🔑 **el control negatiu del tram**: sense gest no hi ha volta |
| `QA-M1-0004` · R1 tancada + R2 replicada | **R1✓ · R2** | R1: `pom:Done`,`tech_sheet:Done` · R2: `pom:Pending`,`tech_sheet:Pending` **sense demanar cap code** |

---

## 6 · MIGRACIONS NOVES

### **CAP.** I està verificat, no assumit.

```
$ venv/bin/python manage.py makemigrations tasks --dry-run
No changes detected in app 'tasks'
$ git diff --name-only 0e3a5eb6..HEAD | grep -c migrations
0
```

**Per què no en calia cap**, tot i que la llei ha canviat:

- `Ronda.seq` ja era `PositiveIntegerField` i **`uniq_ronda_model_seq` ja existia** (M1): `seq=1`
  hi cap sense tocar res, i la constraint que impedeix la R1 duplicada **ja hi era**.
- `ModelTask.ronda` ja era nullable amb `SET_NULL`.
- L'únic que ha canviat a `models.py` és el **docstring** de `Ronda`, que Django no migra.
- I sobretot: **no hi ha backfill** (sub-decisió b). Una migració de dades és exactament el que la
  llei prohibeix fins a M5.

> El màxim real de `backend/fhort/tasks/migrations/` es queda a **`0052`** (`0051_m1_entrega`,
> `0052_m1_rastre_reobertura`, tots dos d'M1 i ja fusionats a `dev`). **Aquest sprint no en
> reserva cap número**, o sigui que el fil motor té via lliure.

---

## 7 · GATE CORREGUT

### 7.1 · `manage.py check`

Net després de **cada** commit.

### 7.2 · Suite — verd PROPORCIONAL

```
venv/bin/python manage.py test \
    fhort.tasks.test_ronda fhort.tasks.test_tasca_vigent fhort.tasks.test_contracte_f2 \
    fhort.tasks.test_m1_entrega fhort.tasks.test_m1bis_fit4 \
    --settings=fhort.settings_m1 --keepdb
```

**`Ran 140 tests in 534.180s` · `OK` · `EXIT=0`** — zero `FAIL`, zero `ERROR`. (113 eren el gate
d'M1; **27 són nous**.) 🔑 **Cap test existent s'ha hagut de tocar**: la llei ha canviat i els 113
d'abans segueixen verds tal com estaven.

### 7.3 · Fum HTTP — `ops/qa/qa_m1bis_fit4_http.py` · **14 OK · 0 FAIL**

Per socket, `Host: staging.fhorttextile.tech`, JWT real, gunicorn propi del worktree a `:8123`
(**el servei `ftt-staging` NO s'ha reiniciat**: serveix `/var/www/ftt-staging`, que és l'arbre del
fil motor i té feina viva sense commitar).

```
  OK   el model treballat té UNA volta, i és la seq 1
  OK   i està oberta
  OK   el model VERGE no té cap volta (la R1 no la crea el model, la crea el gest)
  OK   open-task al verge = 200/201
  OK   el gest ha fet néixer la R1 (seq=1)
  OK   i la tasca del gest hi ha quedat lligada          · [('pom', 1)]
  OK   l'entrega de la R1 = 201 (i la tanca)
  OK   +Ronda amb codes buits = 201
  OK   la porta diu QUÈ ha replicat                      · ['pom', 'tech_sheet']
  OK   i la volta nova és la 2
  OK   les replicades neixen Pending
  OK   R1 tancada i R2 oberta, per la porta de lectura   · [(1, True), (2, False)]
  OK   sense execute_tasks, la porta d'entrega dona 403  · 403
```

El fum encadena les dues lleis **en l'ordre real**: s'entrega la volta (FIT-13, que la tanca) i
llavors se n'obre una altra, que ha de sortir amb el joc replicat.

---

## 8 · COMMITS, DIVERGÈNCIES I TODOs

| Hash | Concern |
|---|---|
| `b9a23ad8` | `feat(tasks)`: la R1 neix del primer gest de treball, i la llei vella se'n va |
| `24b0935f` | `feat(tasks)`: una volta nova neix amb el joc de tasques de l'anterior |
| `ea40649d` | `feat(tasks)`: la porta d'entrega passa a `_ExecuteTasks` (+ segell de l'acta d'M1) |
| `a3f4bdf4` | `test(tasks)`: els dos invariants de FIT-4, gest per gest |
| `47ad7228` | `chore(qa)`: el banc passa a néixer com mana FIT-4, i el fum HTTP del tram |

`10 fitxers, +771 −59`, més aquesta acta. `git log -1 --stat` després de cada commit.

| # | Cosa | Estat |
|---|---|---|
| 🚩 1 | **El filtre `_NO_ES_REPLICA`** — «no copiïs les ad_hoc/lliures» no és aplicable tal com està escrit (§3.1). Avui s'exclou només `off_recipe` | **decisió d'Agus**, una línia |
| 🚩 2 | **`ronda_del_gest` cas 3** (totes les voltes tancades → la feina nova neix `ronda=NULL`) és una **interpretació meva**, no una llei que m'hagis donat. L'alternativa seria obrir una R(n+1) sola, que xoca amb «R2+ són explícites» | **confirma-la o corregeix-la** |
| 🚨 3 | **DEFECTE TROBAT, no tocat** (el brief demana la genealogia «com M1 la va deixar»): `obrir_ronda` calcula `mare = tasca_vigent(model, code)` amb **totes les voltes tancades**, i llavors `tasca_vigent` cau a la regla 2 i retorna la **`prevista`** — o sigui la tasca de la **R1**, no la de la R(n) que s'acaba de tancar. La cadena de `mare` **salta les voltes intermèdies** a partir de la R3. Existia des d'M1; la rèplica el fa visible perquè ara sempre hi haurà R3. La solució és a tocar (la rèplica ja té les files de la R(n) a la mà), però canvia genealogia i **no ho he fet pel meu compte** | **tram propi** |
| 🚩 4 | **No hi ha cap servei únic de creació de `ModelTask`** (§1.3): cinc punts amb la seva pròpia lògica d'`order`/`estimated_minutes`. Unificar-los és la refactorització correcta i és un tram propi | deute anotat |
| ⚠️ 5 | **Canvi de contracte de porta**: `POST obrir-ronda` accepta `codes: []`, els codes són additius, i la resposta porta `codes_replicats`/`codes_omesos`. **M2 ho ha de saber**: el diàleg actual (`ObrirTascaDialog`) tria codes com si fossin la llista sencera | per a M2 |
| ⚠️ 6 | **L'allow-list de `obrir_ronda_view`** ja no s'aplica al joc replicat (§3, punt 2) | documentat al codi |
| ℹ️ 7 | **i18n**: cap clau nova. Backend only; cap text nou de cara a l'usuari | declarat |
| ℹ️ 8 | Banc `[QA-M1]` viu a `fhort` amb **4 models** i les seves rondes. Sintètic; `--remunta` el refà | informatiu |
| ✅ 9 | Gunicorn de QA del `:8123` **aturat** al tancament. ⚠️ No el matis amb `pkill -f 8123`: el patró es troba a si mateix i et mata la sessió | resolt |

### Vist fora d'scope — **anotat, no tocat**

- `tasca_vigent` **regla 2** segueix intacta i segueix sent correcta: amb la R1 explícita, les
  tasques `prevista` d'un model ara tenen `ronda=R1`, i la regla 1 les resol per la volta oberta
  sense passar per la 2. La 2 continua cobrint el cas «hi ha volta oberta però d'un altre abast».
- `reagenda_tasca` (FIT-7) **no s'ha tocat**.
- `clone_model_for_qa` segueix sense decidir res sobre `Ronda`: clonar un model amb voltes hauria
  de decidir si es clonen (probablement **no**). 🚩 fora d'M1-bis.

**Res per pushejar per part meva.** `m1bis-fit4` surt de `0e3a5eb6` i vol un **merge** a `dev`;
el worktree es pot retirar amb `git worktree remove /var/www/ftt-m1`, deixant la branca com a pin.
