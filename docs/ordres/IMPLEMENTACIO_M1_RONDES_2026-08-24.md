# M1 · NUCLI DE RONDES — Entrega, tancament, rastre

> **Patró B · IMPLEMENTA.** Sprint acotat al backend. Cap fitxer de `patterns/**` ni del Taller
> tocat; cap tasca ni cap gest sobre el model **1383**.
> **Deliverable únic**: aquest fitxer. **Cap push** — el fa l'Agus.

---

## 0 · CAPÇAL

| Fet | Valor |
|---|---|
| Worktree | **`/var/www/ftt-m1`**, branca **`m1-rondes`**, creada de `dev` a `3f81313c` |
| Per què worktree | `dev` a `/var/www/ftt-staging` té el fil MOTOR (S46) treballant-hi **ara mateix**: mesurat al tancament, **21 commits sense push** i **140 entrades** a `git status --porcelain` (7 modificats *tracked*). Índex i arbre compartits ⇒ un `git add` s'endú feina aliena ([[ftt-commit-sense-pathspec-endu-el-stage-alie]]). El worktree té dir i índex propis |
| HEAD de sortida | `3f81313c` · *feat(patterns): el mètode PROJECCIÓ…* (del fil motor) |
| HEAD d'arribada | **8 commits** sobre `3f81313c`, cap push (l'últim és aquesta acta) |
| `.env` i `venv` | **enllaçats** al tree principal (`ln -s`), no copiats. No entren a git |
| Fitxers del motor tocats | **cap** (`git diff --stat 3f81313c..HEAD` no conté `patterns/`, ni `frontend/`, ni cap migració de `patterns`) |
| Model 1383 | **no tocat**: cap tasca, cap entrada al Taller. El banc són models NOUS |
| Servei | ⚠️ **`ftt-staging.service` NO reiniciat** — v. §7.1, és una divergència deliberada i raonada |

---

## 1 · FASE 0 · LECTURA PRÈVIA

Totes les línies citades són **de `3f81313c`** (l'estat d'abans d'aquest sprint).

### 0a · Què fa avui `obrir_ronda`: replica el joc de tasques de l'anterior?

**NO.** El joc de tasques el tria **qui crida**, no la volta anterior.

- `obrir_ronda(model, motiu, tasques_codes, *, profile=None)` — `tasks/services_r.py:88`.
- Els codes surten del paràmetre i es dedupliquen preservant l'ordre (`services_r.py:116`); els
  inexistents o inactius es **rebutgen** en lloc d'ignorar-se (`:123-125`).
- Es crea **una `ModelTask` per code rebut**, `origen='ad_hoc'`, `status='Pending'`
  (`:137-144`).
- L'únic lligam amb la volta anterior és **per code, un a un**:
  `mares = {code: tasca_vigent(model, code) for code in codes}` (`:130`), que omple `mare`.
  Si la volta anterior tenia una tasca d'un code que **no** es demana, aquella tasca no entra a
  la ronda nova i **ningú no la replica**.
- L'únic cridador de producte és la porta HTTP `obrir_ronda_view` (`tasks/views_b.py:1692`), que
  llegeix `codes` de `request.data` (`:1712`) — o sigui que **el joc el decideix la UI**
  (`ObrirTascaDialog`), mai la ronda anterior.

### 0b · Existeix l'obertura automàtica de R1 al primer gest de treball? La crea `tasca_vigent`?

**NO existeix, per cap gest. I `tasca_vigent` no crea res.**

- `Ronda.objects.create(...)` apareix **una sola vegada a tot el backend**: `services_r.py:135`,
  dins d'`obrir_ronda`. Cap altre punt del producte crea una `Ronda`.
- `tasca_vigent` (`services_r.py:46`) ho diu al seu propi contracte: *«No crea res, no transiciona
  res: és una consulta»* (`:53`). `_ronda_oberta` (`:35`) només llegeix.
- Els tres gestos de treball, un per un:

| Gest | Punt | Toca `Ronda`? |
|---|---|---|
| **obrir tasca** | `open_model_task_view`, `views_b.py:536` | **No.** Si no troba tasca en crea una `origen='prevista'` amb `ronda=NULL`, i el comentari de `views_b.py:575` ho diu explícitament: *«la ronda no es crea per aquí, es crea amb `obrir_ronda`»* |
| **assignar** | `assign_model_view` → `planning.plan_service` | **No.** Cap referència a `Ronda` |
| **programar** | `planning` / `services_scheduling.reagenda_tasca:15` | **No.** `planning/` no anomena `Ronda` ni un cop; `reagenda_tasca` la LLEGEIX a través de `tasca_vigent` (`:32`) i no en crea cap |

- I no és un oblit, és una **llei escrita**: la R1 és **implícita**. `Ronda`'s docstring
  (`tasks/models.py:147`): *«la ronda 1 és implícita (tota la feina històrica té
  `ModelTask.ronda = NULL`). **No hi ha cap backfill i no n'hi ha d'haver**»*. La numeració hi
  depèn: `seguent = (max(seq) or 1) + 1` (`services_r.py:133-134`) — la primera ronda
  **explícita** neix amb `seq = 2` precisament perquè la 1 ja es dóna per feta. I `tasca_vigent`
  hi depèn també (regla 2, `:65-69`): sense ronda oberta mana la **prevista**, que és la R1.

> 🚨 **0a i 0b contradiuen FIT-4, i aquí m'aturo.** V. §2.

### 0c · Què fa avui `tancar_ronda` amb les tasques vives?

**RES. Ni les mira.**

`tancar_ronda(ronda)` — `services_r.py:203-210` — fa una sola cosa:
`Ronda.objects.filter(pk=…, tancada_el__isnull=True).update(tancada_el=timezone.now())`.

La conseqüència és pitjor que «es queden obertes»: com que la volta ja no és oberta,
`tasca_vigent` torna a resoldre per la **prevista** (regla 2) — és el que fixa
`test_ronda.py:171`, `test_tancar_ronda_torna_la_vigencia_a_la_prevista`. Les `Pending`/`Paused`
de la volta segueixen vives al kanban i al Pla **i cap porta hi torna a entrar mai**: feina que
no és de ningú.

🚨 **I `tancar_ronda` no té ni una crida de producte.** `grep` a tot `backend/fhort`: els únics
cridadors són `test_ronda.py`. **Mai ha tingut porta HTTP.** D'aquí surt la resposta de permisos
de §4.

### 0d · Com es dedueix avui «lliurada» (`ronda_lliurable`)

- `ronda_lliurable(ronda)` — `services_r.py:213-226`: cert quan **totes** les tasques de la ronda
  amb `task_type.es_lliurable=True` són `Done`. Sense cap tasca lliurable retorna **False**
  (`:224-225`): *«no hi ha res per lliurar» no és «ja està lliurat»*.
- `es_lliurable` és un flag del catàleg (`tasks/models.py:118-122`), **5 de 15** tipus actius:
  `pattern_digit`, `pattern_cad`, `tech_sheet`, `scaling`, `marking`.
- `rondes_lliurables(model)` — `services_r.py:229-250`: hi afegeix
  `lliurat_el = Max(finished_at)` dels lliurables.
- Superfícies: `models_app/serializers.py:133` (detall) i `:303` (llista) com a
  `lliurable_ronda_n`; `ronda_oberta` a `:297`. Front: `BadgeLliurable`, `caraObrirTasca`.

**El que substitueix l'Entrega**: la pregunta. `ronda_lliurable` respon *«ja hi és tot?»*;
«entregada» és *«s'ha enviat?»*. Una fitxa acabada i no enviada dona `True`, i una volta enviada
a mitges no en dona cap. Per això `ronda_lliurable` **es queda tal qual**, com a senyal PREVI
(«ja es pot marcar entregable»), i **no** com a definició d'entregada.

---

## 2 · 🚨 ATURADA (Patró C) — FIT-4 no s'ha implementat

El brief autoritza a alinear 0a/0b «com a part d'aquest sprint». **No ho he fet**, i el motiu no
és el cost:

1. **No he pogut llegir FIT-4.** `FIL_RONDES_ENTREGUES_TANCAMENT.md` és **al vault**, i el vault
   no és accessible des d'aquesta màquina (`find / -name "FIL_RONDES*"` → cap resultat; cap
   `FIT-n` a tot el repo). Del brief només en tinc **les preguntes**, no el text de la decisió:
   sé que 0a i 0b hi contradiuen, però no sé **què** hi diu exactament que ha de passar.
2. **L'alineació de 0b no és un canvi acotat: és retirar una llei escrita.** «La R1 és
   implícita» viu, com a mínim, en cinc llocs que hi depenen entre si — el docstring de `Ronda`
   (`models.py:147`, que **prohibeix el backfill amb totes les lletres**), la fórmula
   `(max(seq) or 1) + 1` (`services_r.py:133`), la regla 2 de `tasca_vigent` (`:65-69`), el
   `ronda=NULL` d'`open-task` (`views_b.py:575`) i el contracte de `ronda_seq` («null = la 1a,
   implícita», `serializers_b.py`). Obrir R1 automàticament obliga a decidir **si R1 té `seq=1`,
   si les tasques `ronda=NULL` que ja hi ha s'hi adopten o no, i què passa amb els models que ja
   tenen feina feta** — tres decisions de producte que el brief no fixa i que jo no puc deduir.
3. És exactament el cas que `CLAUDE.md` reserva a l'aturada: **contradicció de paradigma**.

**El que sí que puc dir per a la decisió** (perquè arribi mastegada):

| Si FIT-4 vol… | Cost i radi | Trenca |
|---|---|---|
| `obrir_ronda` **proposa** el joc de l'anterior quan el cridador no en dóna cap | Petit i additiu (un `or` sobre `ronda_anterior.tasques`) | Res. Però és **codi mort**: l'única porta sempre envia `codes` |
| `obrir_ronda` **imposa** el joc de l'anterior | Mitjà | El contracte de `obrir_ronda_view` i tota la cara B d'`ObrirTascaDialog` (l'usuari tria codes) |
| **R1 automàtica** al primer gest | **Gros** — les 5 dependències de dalt + numeració + genealogia + `lliurable_ronda_n` | Els 3 gestos, `test_ronda` (`seq==2`), i obre la pregunta del backfill que el model prohibeix |

**La resta de l'sprint no en depèn** i s'ha entregat sencera: FIT-1, FIT-13, FIT-6 i FIT-2 no
toquen ni la numeració ni el joc de tasques d'`obrir_ronda`.

---

## 3 · FASE 1 · BANC SINTÈTIC

`ops/qa/banc_m1_rondes.py` — **idempotent** (guarda: `codi_intern` amb prefix `QA-M1-`), amb
`--remunta` per esborrar-lo i refer-lo. **Mai el 1383, mai el golden 162, mai un model real.**

Les rondes es creen **pel camí normal** (`services_r.obrir_ronda`) i els estats es mouen **per
`transition_task`**: un banc inserit a mà no tindria ni `mare`, ni fila a `TaskTransition`, i
FIT-6 s'hi provaria contra una cosa que el sistema no fabrica mai.

**Banc muntat a `fhort` (staging), 24/08 13:22 CEST** — tècnic del muntatge: `UserProfile 1`
(triat perquè **no tenia cap tram obert**: entrar a `InProgress` pausa la feina viva del tècnic):

| Model | Ronda acabada de muntar | Tasques (code : estat) |
|---|---|---|
| `QA-M1-0001` · *[QA-M1] Estats variats* | seq **2**, oberta | `pom:Done` · `tech_sheet:InProgress` · `grading:Paused` · `sample_check:Pending` |
| `QA-M1-0002` · *[QA-M1] Tot fet* | seq **2**, oberta | `pom:Done` · `tech_sheet:Done` |
| `QA-M1-0003` · *[QA-M1] Verge sense tasques* | — | (cap) |

**Estat VIU ara mateix a `fhort`** (el banc s'ha remuntat 3 cops; **els pk canvien a cada
`--remunta`**, per això la taula de dalt no en porta):

| Model | pk | Ronda | Entrega | Tasques |
|---|---|---|---|---|
| `QA-M1-0001` | **1397** | seq 2 **TANCADA** | `Entrega` pk **3** | les 4 a `Done` ← consumit pel fum de §7.2 |
| `QA-M1-0002` | **1398** | seq 2 oberta | — | `pom:Done` · `tech_sheet:Done` |
| `QA-M1-0003` | **1399** | — | — | (cap) |

> 🚨 **L'EXCLUSIÓ D'UN-INPROGRESS-PER-TÈCNIC ÉS GLOBAL, NO PER MODEL** — i el banc ho va
> descobrir sol. Muntat model a model, el banc sortia **sense cap tasca en curs**: la
> `InProgress` del 0001 la pausava la primera `→InProgress` del 0002, perquè
> `_aplica_exclusio_tecnic` (`services_c.py:124`) tanca els trams oberts d'aquell tècnic a
> **qualsevol** tasca de **qualsevol** model. Mesurat dos muntatges seguits, tots dos amb
> `tech_sheet:Paused` on s'esperava `InProgress`. El muntatge va ara en **dues passades** (primer
> tot el `Done`/`Paused` de tots els models, i les `InProgress` al final). No és un truc per
> esquivar la llei: és la llei, i és per això que **un banc no pot tenir dues `InProgress` del
> mateix tècnic**.

⚠️ El fum de §7.2 **consumeix** la ronda del `QA-M1-0001` (l'entrega la tanca i no es pot
desfer). Per tornar-hi: `venv/bin/python ../ops/qa/banc_m1_rondes.py --remunta`.

---

## 4 · FASE 2 · L'ENTREGA (FIT-1) i FIT-13

### El model — `tasks.Entrega`, al costat de `Ronda` (`tasks/models.py:180`)

| Camp | Tipus | Nota |
|---|---|---|
| `ronda` | **`OneToOneField`**(`Ronda`, CASCADE, `related_name='entrega'`) | v. la tria, sota |
| `data` | `DateTimeField(default=timezone.now)` | l'aporta qui informa; per defecte ara |
| `destinatari` | `CharField(200)` | **TEXT LLIURE**, no FK a `Customer` |
| `qui_informa` | FK `UserProfile`, `SET_NULL` | esborrar un usuari no esborra la història |
| `descripcio` | `TextField(blank=True)` | **TEXT LLIURE** del que s'ha enviat |
| `data_ok` · `qui_informa_ok` | nullables | el senyal **manual i posterior** del client |
| `created_at` | `auto_now_add` | quan es va **escriure la fila** ≠ `data` |

- **Cap FK a `ModelFitxer` / fitxa / patró** (FIT-1: event informat, no artefacte controlat).
  Hi ha un test que ho **guarda** (`test_l_entrega_no_lliga_cap_artefacte`).
- **Cap `data_prevista_retorn`** (micro-decisió M1). El mateix test ho fixa.

**OneToOne o FK+constraint?** → **`OneToOneField`**, i és el que la casa ja fa servir per a «un X
per Y»: `ConsumptionRecord.model` i `.garment_set` (`models_app/models.py:1369,1373`),
`WorkOrder.source_quote` (`commerce/models.py:338`), `UserProfile.user` (`accounts/models.py:6`),
`TechSheetTemplate.customer` (`models_app/tech_sheet_models.py:21`), `FttDocumentLock
.document_root` (`models_app/ftt_models.py:20`) i `BackofficeUser.usuari`
(`backoffice/models.py:39`) — **7 casos**. I a tot `fhort` **no
hi ha ni un sol `UniqueConstraint` d'un camp sol sobre un FK** (`grep` a §0 del treball). Amb
això, `ronda.entrega` és l'accés natural i `hasattr(ronda, 'entrega')` la pregunta natural.

### Els serveis — `tasks/services_r.py`

- `informar_entrega(ronda, *, destinatari, profile, descripcio='', data=None)` → `Entrega`.
  Rebutja destinatari buit, segona entrega i perfil absent (`EntregaError`).
- `informar_ok_client(entrega, *, profile, data_ok=None)`. **Un sol cop**: és un fet, no un
  interruptor. **No toca la ronda** (quan arriba, ja fa estona que és tancada).

### 🔒 FIT-13 — l'acte TANCA la ronda, i en **la mateixa transacció**

`informar_entrega` obre un `transaction.atomic()` i hi fa les dues coses. No és una precaució
decorativa: en dues transaccions, el dia que la segona fallés quedaria **una entrega informada
sobre una ronda viva**, que és exactament l'estat que no ha d'existir. O hi són totes dues o no
hi és cap — i el test `test_sense_destinatari_no_hi_ha_entrega` comprova que un rebuig **no deixa
la ronda tancada de rebot**.

`ronda_lliurable` **no s'ha tocat**: es queda com a senyal informatiu previ. El
`RondaSerializer` serveix les dues coses amb noms diferents i el consumidor no les pot confondre:
`lliurable` (deduït) i `entregada` (declarat).

### Les portes DRF — `tasks/views_b.py` + `tasks/urls.py`

| Porta | Mètode | Retorna |
|---|---|---|
| `/api/v1/rondes/<ronda_id>/entrega/` | `POST` | `201` + l'acte · `400` de forma · `400 entrega_invalida` · `409 ronda_no_tancable` · `404` |
| `/api/v1/entregues/<entrega_id>/ok-client/` | `PATCH` | `200` · `400` de forma · `400 ok_client_invalid` · `404` |
| `/api/v1/models/<model_id>/rondes/` | `GET` | `200` — les voltes amb l'entrega **niuada** |

**La FORMA la valida el serializer; el FET, el servei** — i el 400 queda repartit com toca.
`data` i `data_ok` arriben com a **text** per HTTP: passar-los crus al model els desaria sense
parsejar («ahir a la tarda» entrava com a data). El POST passa per `EntregaSerializer` i el PATCH
per un `DateTimeField`, i el rebuig és el 400 de camp de sempre de DRF; el `code`
(`entrega_invalida`) queda per als rebuigs de **fet** («una volta s'entrega un cop»).
🔑 Un dels tests d'això va trobar un `NameError` real a la resposta del PATCH —**500 al fum
HTTP**— mentre s'escrivia el commit.

La tercera porta **no és scope creep, és el que fa llegible la primera**: una ronda entregada és
una ronda **tancada**, i `Model.ronda_oberta` (`models_app/serializers.py:297`) no en pot ensenyar
mai cap. Sense aquesta porta, l'Entrega seria una dada que no es pot llegir des d'enlloc.

### 🚩 PERMISOS — `IsAuthenticated` amb TODO declarat

El brief demana «la mateixa capability que avui governa `tancar_ronda`». **No n'hi ha cap**:
`tancar_ronda` no té ni una crida de producte a tot `backend/fhort` (§0c) — mai ha tingut porta
HTTP i per tant mai ha tingut capability. **No n'he inventat cap.** La nota queda escrita al codi
(`views_b.py`, capçalera del bloc M1) amb la germana més propera per si l'Agus vol adoptar-la:
`obrir_ronda_view` va amb **`_ExecuteTasks`** (`EXECUTE_TASKS`, `views_b.py:419`) **més**
l'allow-list de `task_type` de qui obre.

**Decisió pendent d'Agus**, i no és òbvia: informar una entrega s'assembla més a un acte de **PM**
(`DEFINE_TASKS` / `CLOSE_GATES`) que a executar una tasca — i, com que l'acte **tanca la ronda i
la feina viva**, avui la porta és **més oberta que la d'obrir-la**. 🚩 **TODO(M1)**.

---

## 5 · FASE 3 · TANCAMENT FORÇAT (FIT-6)

`tancar_ronda(ronda, *, profile=None)` ara tanca **tota** la feina viva de la volta, via
`tanca_tasques_de_la_ronda`.

**Pel mecanisme únic, mai un `UPDATE`.** Cada tasca passa per `transition_task`. Amb un
`update(status='Done')` no hi hauria ni tram tancat, ni fila a `TaskTransition`, ni crida a
`record_actual_time`: el Welford no veuria el tancament d'una tasca que **sí** que s'havia
treballat, i el log diria que aquella feina segueix viva.

**I són DOS SALTS** (`Pending→InProgress→Done`), perquè `ALLOWED` **no té** `Pending→Done` ni
`Paused→Done` (`services_c.py:17-39`) i això és una decisió d'Agus (Patró C, 28/07, fixada a
`test_stop_encadenat:122`). S'aplica el mateix **play+stop encadenat** que el Stop d'una tasca
pausada, en comptes d'obrir cap camí nou a la taula. **La màquina d'estats no s'ha tocat.**

L'ordre de tancament és `InProgress → Paused → Pending` i **no és cosmètic**: cada entrada a
`InProgress` dispara `_aplica_exclusio_tecnic`, i tancant primer el que ja hi és s'evita omplir
el log de pauses que ningú no ha fet.

### 🔑 Com es discrimina el Welford — i per què **no calia cap guard nou**

La llei d'Agus («el Welford no mesura res d'una tasca que no s'ha executat») **ja la imposava el
sistema**, amb tres peces que ningú no havia escrit per a això:

1. `_open_timer` (`services_c.py:56`) fa néixer el tram del salt amb **`consulta=False`**
   («jutjable»).
2. `_close_open_timer` (`services_c.py:78`): en tancar-lo **sense cap `escriptura_at`**, el
   marca **`consulta=True`**.
3. `TRAMS_SANS` (`services_i.py:44`) l'exclou: `~Q(consulta=True)`. Per tant `_real_minutes` no
   el suma.
4. I `record_actual_time` (`services_i.py:83-85`) surt pel seu propi
   **`x = Decimal(_real_minutes(...)); if x <= 0: return None`** — *«sense temps real registrat →
   res a aprendre»*.

Resultat: una `Pending` mai tocada **no deixa cap mostra**; una tasca amb temps executat real
manté els seus trams i **la mostra és la de sempre**. Els dos casos tenen test
(`TancamentForcatWelfordTest`).

**Mesurat al banc VIU**, i el resultat és el mateix després de **tres** cicles complets de
muntatge + entrega (**12 tancaments forçats** en total, `garment_type_item` 4):

```
  pom            Done   trams=1 consulta=[True]        minuts=[0]
  tech_sheet     Done   trams=1 consulta=[True]        minuts=[0]
  grading        Done   trams=2 consulta=[True, True]  minuts=[0, 0]
  sample_check   Done   trams=1 consulta=[True]        minuts=[0]

  Welford (item 4):  pom  n=1 mean=199.00 · grading  n=1 mean=246.00 · tech_sheet  n=0
                     sample_check → la cel·la ni tan sols existeix
```

**Tots** els trams del tancament forçat surten `consulta=True` amb `minuts=0`. `tech_sheet`, que
s'ha tancat a la força **tres vegades**, segueix a **`n=0`**; `pom` i `grading` es queden clavats
als valors que ja tenien (història real d'altres models del mateix item, 199 i 246 min) i
`sample_check` no ha arribat mai a crear cel·la. Si el tancament forçat alimentés res, cap
d'aquests tres números podria ser el que és.

**Cap tasca migra a cap ronda següent**: `test_cap_tasca_migra_a_cap_ronda_seguent` compara el
conjunt de pks de `ModelTask` i de `Ronda` abans i després.

### ⚠️ Canvi de comportament declarat

`profile` passa a ser **obligatori quan queda feina viva** (`RondaError` si no n'hi ha). Tancar la
feina d'algú és un acte i ha de tenir autor al log; i, en tot cas, `TimerEntrada.tecnic` és
`NOT NULL`. Dues crides de `test_ronda.py` hi passen ara `profile=self.prof` (`:175`, `:180`);
cap asserció d'aquells tests ha canviat. Tancar una ronda **sense** feina viva segueix sent el
no-op idempotent de sempre, sense autor.

---

## 6 · FASE 4 · RASTRE DE REOBERTURA (FIT-2, backend only)

`Done→InProgress` **segueix legal**: el segell és TOU i això **no és un guard** — la funció nova
no pot rebutjar res. L'única cosa que canvia és que el log deixa dit que aquella feina ja
s'havia entregat. (És una conversa diferent de la paret **DURA** de l'albarà,
`te_paret_albara`, que sí que refusa.)

**On:** `TaskTransition.nota` (`TextField` nullable), no `ModelTask.motiu`. **Per què:**

- `TaskTransition` **és el log immutable** — ho diu el seu propi docstring (`models.py:315`): una
  fila per gest, que no es reescriu mai. Un rastre de reobertura **és un gest**.
- `ModelTask.motiu` és genealogia **mutable amb `choices`** (`nova_mostra`/`correccio`). Escriure-
  hi una frase hi encabiria un valor que no és cap dels dos i, sobretot, **esborraria el motiu de
  la volta**, que ningú no podria recuperar.
- I **no** va a `TaskTransition.auto`, encara que hi cabria: aquell camp significa «això no ho ha
  fet una persona» (`null` = gest humà, `models.py:326`), i reobrir és **un gest humà**.
  Posar-l'hi faria mentir el log per estalviar una columna. El test ho fixa
  (`assertIsNone(salt.auto)`).
- Precedent de forma: **`GateEvent.notes`** (`models.py:372`), la nota de l'altre log d'actes de
  la mateixa app.

El text és `reoberta després d'entrega de R{n}`, i **només** quan la tasca pertany a una ronda
**amb entrega informada**. Una tasca de la volta 1 (`ronda=NULL`) o d'una volta no entregada no
té res a rastrejar (dos tests). **La CARA del rastre és M2**; aquí només hi ha la dada.

---

## 7 · GATE CORREGUT

### 7.1 ⚠️ El servei NO s'ha reiniciat — i és deliberat

El brief demana `systemctl restart ftt-staging.service`. **No ho he fet, i fer-ho hauria estat
dolent per dues raons independents:**

1. **No hauria desplegat res meu.** El servei té `WorkingDirectory=/var/www/ftt-staging/backend`
   (`systemctl cat`): serveix **un altre arbre**. El meu codi viu a `/var/www/ftt-m1`. Un
   `restart` hauria deixat el smoke picant contra un backend que no porta cap d'aquestes portes.
2. **Hauria desplegat feina aliena a mig fer.** `/var/www/ftt-staging` té ara mateix **140
   entrades** sense commitar del fil MOTOR (7 d'elles `.py`/`.md` *tracked* modificats). **Els gates també són desplegament**
   ([[ftt-dev-concurrent-git]]): reiniciar el servei publica el backend d'una altra sessió, tal
   com estigui.

**El que s'ha fet en lloc seu** — i cobreix la mateixa lliçó (T8-ter: *build verd ≠ backend viu*):
un **gunicorn propi del worktree**, `--chdir /var/www/ftt-m1/backend`, a `127.0.0.1:8123`, com a
`www-data`, contra la **BD viva d'staging**. El fum hi va **per socket**, amb
`Host: staging.fhorttextile.tech` i `Authorization: Bearer`.

**I el desplegat s'ha comprovat igualment, perquè li he tocat la BD.** El servei real (`:8001`)
contesta `401` a `/api/v1/models/` i `/api/v1/task-types/` —viu i sa— i **`404`** a
`/api/v1/models/<id>/rondes/`, que és exactament el que ha de dir un backend que no porta aquest
codi. `ActiveEnterTimestamp = 2026-08-24 11:25:45 UTC`: **una altra sessió l'ha reiniciat pel seu
compte DESPRÉS de les meves dues migracions** (11:10 i 11:16 UTC) i l'arrencada és neta — les
migracions són additives i el codi vell no llegeix ni la taula ni la columna noves.

> 🔑 **La primera asserció del fum és `401`, no `200`.** Sense token la porta ha de contestar
> **401** i no **404**: 404 voldria dir que el backend servit **no porta aquest codi** — el
> gunicorn ranci de la lliçó del 21/08. És el criteri que distingeix «el backend és viu amb el
> meu codi» de «el backend és viu».

### 7.2 Fum HTTP — `ops/qa/qa_m1_entrega_http.py` · **12 OK · 0 FAIL** (correguda final)

```
BASE=http://127.0.0.1:8123 · Host=staging.fhorttextile.tech · model 1397 (QA-M1-0001)
  OK   sense token la porta contesta 401 (existeix i està tancada) · 401
  OK   GET rondes = 200
  OK   hi ha una ronda OBERTA al banc
  OK   encara no és entregada
  OK   POST entrega = 201
  OK   l'acte torna qui informa · Agustí Devant
  OK   la ronda ha quedat TANCADA (FIT-13)
  OK   i diu entregada=true amb l'acte niuat
  OK   cap tasca viva a la volta (FIT-6)
  OK   la segona entrega es rebutja amb 400
  OK   PATCH ok-client = 200 i data_ok informada
  OK   el segon ok-client es rebutja (és un fet, no un interruptor)
```

> 🚨 **El JWT vol el claim `tenant_schema`.** `RefreshToken.for_user()` pelat dona **401 «token no
> vàlid»** — el **mateix 401** que un token absent, i es confon amb un problema de permisos.
> El claim l'estampa `TenantTokenObtainPairSerializer.get_token` (`fhort/auth_jwt.py:47`) i el
> llegeix de l'**schema actiu**: s'ha de cridar dins del `schema_context`.

### 7.3 `manage.py check`

Net (`System check identified no issues (0 silenced)`) després de **cada** commit.

### 7.4 Suite — verd PROPORCIONAL (llei 23/08)

**RUTES EXACTES** (bloc RONDA del R13 del cens + les noves):

```
venv/bin/python manage.py test \
    fhort.tasks.test_ronda \
    fhort.tasks.test_tasca_vigent \
    fhort.tasks.test_contracte_f2 \
    fhort.tasks.test_m1_entrega \
    --settings=fhort.settings_m1 --keepdb
```

**RESULTAT: `Ran 113 tests in 357.493s` · `OK` · `EXIT=0`** — zero `FAIL`, zero `ERROR`.
(Els 113 són més que els ~50 que el R13 comptava amb `grep -c "    def test"`: `RondaLliurableTest`
**hereta** de `RondaTest` i en torna a córrer tots els mètodes. El nombre és el MESURAT.)

Una correguda anterior es va **matar a mitges** (bug detectat al PATCH, v. §4). Va deixar la fila
`tenants_client(schema_name='test')` **commitada** a la BD de test — el parany conegut, que a la
correguda següent hauria donat ~68 `UniqueViolation` de `setUpClass` que semblen teus i no ho són.
Netejat abans de rellançar (`delete from tenants_client where schema_name='test'` → **1 fila** +
`drop schema test cascade`), i per això aquest verd és net.

`settings_m1` només canvia `DATABASES['default']['TEST']['NAME']` a `test_ftt_m1_rondes`:
`test_ftt_staging` és **compartida** entre sessions concurrents i cadascuna destrueix la de
l'altra.

> ⚠️ **Divergència declarada amb el R13 del cens.** El cens demanaria la **sencera** en dos dels
> seus cinc supòsits: ① s'ha tocat `tasks/models.py` (57 fitxers de test l'importen) i ④ s'han
> afegit migracions a `tasks`. La **llei del 23/08 mana sobre el cens** i el brief ho fixa
> explícitament. Els dos canvis a `models.py` són **estrictament additius** (una classe nova i un
> camp nullable nou: cap camp existent tocat, cap `Meta` alterada), i el canvi a `services_c.py`
> és un paràmetre nou amb `default=None` als **tres** cridadors de `_log`, tots dins del mateix
> fitxer. Si l'Agus vol la sencera abans del merge, aquest és el motiu pel qual podria voler-la.

---

## 8 · MIGRACIONS NOVES

> Numeració comprovada **al disc** abans de generar-les, a **tots** els worktrees vius
> (`ftt-staging`, `ftt-m1`, `ftt-t7`, `ftt-t9`, `ftt-fixmes`, `ftt-m3`, `ftt-planning`,
> `ftt-tx`): el màxim real a `backend/fhort/tasks/migrations/` era **`0050`** a tot arreu.
> El fil motor no en porta cap de `tasks` (les seves són de `patterns`).

| Migració | Què fa | Estat |
|---|---|---|
| **`tasks/0051_m1_entrega`** | `+ Create model Entrega` | **APLICADA** a tots els schemes (`migrate_schemas`, mai `--schema`) |
| **`tasks/0052_m1_rastre_reobertura`** | `+ Add field nota to tasktransition` | **APLICADA** a tots els schemes |

**Auditades a la BD** (no només l'OK de django-tenants, que pot enganyar):

- `fhort.tasks_entrega` → 9 columnes: `id`, `data`, `destinatari`, `descripcio`, `data_ok`,
  `created_at`, `qui_informa_id`(NULL), `qui_informa_ok_id`(NULL), `ronda_id`.
- `fhort.tasks_tasktransition.nota` → `text`, nullable.
- `showmigrations` corregut **sempre** amb `tenant_command … --schema=fhort` (sense tenant respon
  per `public`, fals negatiu confirmat).

> 🚨 **DIVERGÈNCIA BD↔`dev` VIVA, i és la que més importa d'aquest report.** Les dues migracions
> estan **aplicades a la BD d'staging** però els seus fitxers viuen **només a la branca
> `m1-rondes`**. Mentre l'Agus no la fusioni a `dev`, `dev` té una BD amb dues migracions que el
> seu arbre no conté — exactament el forat que [[ftt-migracions-es-commiten-en-aplicar-se]]
> descriu i que **cap gate detecta**. Cap taula existent s'ha alterat, o sigui que el `dev`
> desplegat funciona igual (una taula nova i una columna nullable que ningú no llegeix); però el
> `makemigrations` de la propera sessió que treballi `tasks` a `dev` **veurà l'arbre, no la BD**,
> i podria proposar un `0051` que ja existeix a `django_migrations`.
> **Acció per a l'Agus: fusionar `m1-rondes` abans que cap altra sessió generi migracions de
> `tasks`.**

---

## 9 · COMMITS (branca `m1-rondes`, **cap push**)

| Hash | Concern |
|---|---|
| `ebca03c3` | `feat(tasks)`: l'Entrega — l'acte datat que declara una ronda entregada |
| `626e6236` | `feat(tasks)`: tancar una ronda tanca la seva feina, pel mecanisme únic |
| `632e4db1` | `feat(tasks)`: informar l'entrega — servei, contracte i portes DRF |
| `86ecf1d3` | `feat(tasks)`: el rastre de reobertura d'una tasca ja entregada |
| `370d0d41` | `test(tasks)`: els quatre invariants de M1, i el shim de BD de test propi |
| `53021824` | `chore(qa)`: el banc sintètic M1 i el fum HTTP de l'entrega |
| `e67a7c86` | `fix(tasks)`: la FORMA del payload de l'entrega la valida el serializer |
| *(HEAD)* | `docs(ordres)`: l'acta de M1 — **aquest fitxer** |

`13 fitxers de codi/QA, +1180 −10`, més aquesta acta. `git log -1 --stat` verificat després de **cada** commit; cap va endur-se
res aliè (el worktree té índex propi i el `git status` de sortida era net).

### 🟢 El merge no pot xocar: **intersecció de fitxers = 0**

Mesurat al tancament, amb el motor ja a `62fa8f52` (*docs(diagnosi): la gramàtica de cotes CAD*):

```
comm -12 <(git diff --name-only 3f81313c..m1-rondes | sort) \
         <(git diff --name-only 3f81313c..62fa8f52  | sort)
→ (buit)
```

Els meus **14** fitxers viuen tots a `backend/fhort/tasks/**`, `ops/qa/` i `docs/ordres/`; els
**16** del motor, a `backend/fhort/patterns/**`, `frontend/src/components/pattern/**`,
`frontend/src/i18n/*.json` i `docs/diagnosis/`. **Cap fitxer compartit, cap línia en disputa.**
I la migració nova del motor és **`patterns/0017_patternpom_cota_offset`**: no toca `tasks`, o
sigui que la numeració `0051`/`0052` que vaig reservar segueix sent bona.

**Res per pushejar per part meva.** El push el fa l'Agus i **portarà també els 21 commits del
motor** que `dev` té sobre `origin/dev`; aquests vuit viuen a `m1-rondes` i volen un **merge** a `dev` (el worktree es pot retirar
amb `git worktree remove /var/www/ftt-m1`, deixant la branca com a pin).

---

## 10 · DIVERGÈNCIES I TODOs DECLARATS

| # | Cosa | Estat |
|---|---|---|
| 🚨 1 | **FIT-4 (0a i 0b) NO implementat** — vault inaccessible + contradicció de paradigma | **ATURADA · decisió d'Agus** (§2) |
| 🚨 2 | **Migracions aplicades a la BD i no a `dev`** fins que es fusioni `m1-rondes` | **acció d'Agus** (§8) |
| 🚩 3 | **Permisos de l'Entrega**: `IsAuthenticated` + `TODO(M1)` al codi. Avui la porta que **tanca** la ronda és més oberta que la que l'obre | **decisió d'Agus** (§4) |
| 🚩 4 | **`ftt-staging.service` no reiniciat** (raonat a §7.1). El desplegat segueix sent el d'abans d'aquest sprint | informatiu |
| ✅ 5 | **Gunicorn de QA a `127.0.0.1:8123`** — **aturat al tancament**, no queda cap procés meu viu. Per tornar-hi (cal per rellançar el fum de §7.2), la comanda és al capdamunt de `qa_m1_entrega_http.py`. ⚠️ **No matis amb `pkill -f 8123`**: el patró es troba a si mateix a la línia de comandes del teu propi shell i et mata la sessió (m'ha passat dues vegades). `ps -eo pid,cmd \| grep '[g]unicorn.*8123'` i `kill` del **màster** | resolt |
| ⚠️ 6 | **Canvi de contracte**: `tancar_ronda` vol `profile` si queda feina viva | documentat (§5) |
| ⚠️ 7 | **Divergència amb el R13** del cens sobre la suite sencera (①/④) | raonada (§7.4) |
| ℹ️ 8 | **i18n**: M1 **no crea cap clau nova**. L'sprint és backend-only (la UI és M2) i no hi ha cap text nou de cara a l'usuari. Inventar claus ara obligaria M2 a rebatejar-les. La paritat ca/en/es queda **pendent de M1→M2**, no incomplerta | declarat |
| ℹ️ 9 | **Enumeracions de domini**: M1 **no n'afegeix cap**. `destinatari` i `descripcio` són text lliure per disseny (FIT-1); no hi ha cap `choices` nou, i per tant res a publicar a `/vocabulari/` | declarat |
| ℹ️ 10 | El banc `[QA-M1]` deixa **3 models nous vius** a `fhort` (**1397-1399**) i **3 `Entrega`** (pk 1-3, dels fums). Tot sintètic; `--remunta` els esborra i els refà | informatiu |

### Vist fora d'scope — **anotat, no tocat**

- `tancar_ronda` seguia **sense cap porta HTTP** i ara continua sense tenir-ne una de pròpia: es
  tanca **només** per l'Entrega. Si M2 vol un «tancar sense entregar», és una porta nova.
- `Model.ronda_oberta` (`models_app/serializers.py:297`) **no** s'ha tocat: no pot ensenyar mai
  una entrega (una ronda entregada és tancada), i afegir-hi res hauria estat soroll.
- `clone_model_for_qa` no decideix res sobre `Entrega`. Clonar un model amb rondes entregades
  hauria de decidir si l'acte es clona (probablement **no**: no s'ha entregat res del clon).
  🚩 **fora d'M1.**
