# J · CONSULTA ≠ TREBALL (modal, tasca, temps)

> **21/08/2026 · ✅ TRAM TANCAT · 4 commits a `dev`, CAP PUSH.**
> Substrat: `DIAGNOSI_PRE_SPRINTS_STAGING_2026-08-21.md` §2 + les tres regles d'Agus (Patró C).
> Banc: 16 tests (1 skip) + 21 comprovacions contra el model **1383** viu.

---

## 0 · LES TRES REGLES, I ON HA QUEDAT CADA UNA

| Regla | Estat | On viu |
|---|---|---|
| **R1** — sense escriptura, cap modal; la tasca torna sola | ✅ | `sortir_sense_escriptura_view` + `exitEdit` |
| **R2** — el temps de consulta no compta | ✅ | **una línia** a `TRAMS_SANS` + el seu bessó |
| **R3** — entrar no endú ni reobre | ✅ | dos guards a `open-task` + `caraObrirTasca` |

**Cap frontera dura tocada.** `transition_task` i `traspassa_tram` fan exactament el mateix que
ahir —J governa **quan** es criden, no què fan—; l'exclusió un-InProgress i el canal de federació
queden intactes per al treball real; la consulta no allibera ni reclama mai la mà.

---

## 1 · EL SENYAL — `batec_escriptura`, i per què no `last_heartbeat`

El tram J necessitava saber, en sortir d'una pantalla, si la sessió havia estat **treball o només
consulta**. La resposta ja la sabia un mòdul i ningú més: **cada crida de `batec_escriptura` és,
literalment, un punt on hi ha hagut escriptura de debò**.

És el mateix viatge que va fer la meritació SaaS (D-10) quan el fet facturable va passar de *«algú
ha obert una porta»* a *«algú hi ha ESCRIT»*, perquè *«tocar una porta tres segons per error
facturava»*. **J és aquell moviment aplicat al TEMPS.**

🚨 **I NO ÉS `last_heartbeat`**, encara que s'escriguin junts i al mateix `update()`. Aquell camp
té **dos emissors i un sol significat possible** —el guard hi diu «sóc davant la pantalla» i
l'escriptura hi diu «he escrit»— i per tant **no pot respondre la pregunta de la qual depèn tot
això**. La nota de `tasks/models.py` demanava que qui n'afegís un tercer escrigués allà mateix:
s'ha fet, i s'hi ha escrit per què això **no n'és un** — no duplica el senyal, en separa la meitat
que faltava.

### La marca primera, la inferència darrere (patró `presa_at`)

Dos camps amb feines diferents, i el segon es tanca al **tancament** del tram perquè és quan ja es
pot donar el veredicte: durant el tram, qui no ha escrit encara pot escriure.

| Camp | Què és | Qui l'escriu |
|---|---|---|
| `TimerEntrada.escriptura_at` | el GEST: última escriptura dins del tram | `batec_escriptura`, i **només ell** |
| `TimerEntrada.consulta` | el VEREDICTE: «aquí no s'hi ha escrit res» | `_close_open_timer` |

### 🚨 TRES ESTATS, i el tercer és el que fa que això sigui segur

- **`None` — no jutjat.** Tot l'històric, **i els trams que el desplegament enxampi oberts**: van
  néixer sense la marca, i condemnar-los per no tenir-la seria inventar-se que no s'hi va
  treballar. Compten exactament com sempre.
- **`False`** — nascut sota el règim nou (`_open_timer`), encara no jutjat.
- **`True`** — tancat sense cap escriptura.

Per això la clàusula és **`~Q(consulta=True)` i no `Q(consulta=False)`**. Amb la segona, la
migració hauria **buidat el Welford, l'albarà i el consum de cop**, en silenci i sense migració.
Hi ha un test que ho afirma sol. **Mesurat: 81 trams a `fhort`, tots a `NULL` després de migrar.**

---

## 2 · R2 · 🔒 EL LLINDAR NO ES TOCA I NO SE'N FABRICA UN DE PARAL·LEL

`MAX_MINUTS_TRAM` segueix sent **l'única constant de plausibilitat** del sistema. El descart de J
**no n'és una segona, perquè no és un llindar: és una MARCA**. No pregunta «quant ha durat?» sinó
«s'hi ha escrit?», que és una altra dimensió — i **havia de ser-ho**, perquè decidir-ho per durada
contradiria la decisió d'Agus escrita a `ModelSheet.jsx`:

> *«no hi ha hagut sessió» no vol dir «ha durat poc»: una sessió de dos minuts amb la tasca oberta
> ensenya el modal igual que una de dues hores.*

Entra a la **mateixa expressió** perquè comparteix el criteri del llindar —**exclusió, no
retall**—: d'un tram de consulta no en tenim zero minuts de feina, en tenim minuts que no són
feina. **Una línia** tapa Welford, `_real_minutes`, `minuts_per_model_task`, l'albarà
(`commerce/services.py` × 3), el registre de consum i els agregadors de `models_app/views.py`.

⚠️ `tram_compta` canvia amb ella: són **germans declarats i cap gate els compara**. Ara sí — hi ha
un test que els creua sobre cinc combinacions de (consulta × minuts).

---

## 3 · R3 · ENTRAR NO ENDÚ NI REOBRE

Dues coses passaven per la **mera entrada**, totes dues en silenci i totes dues irreversibles al
log:

| Forat | Per què existia | Ara |
|---|---|---|
| una `Done` es **REOBRIA** | `ALLOWED` permet `Done → InProgress` perquè la rectificació existeix com a ACTE, i la porta se'n servia sense voler | exigeix `reobrir: true` → si no, **409 `tasca_feta`** |
| la d'un altre es feia **SEVA** | `traspassa_tram` + `assignee`, sense preguntar | exigeix `handoff: true` → si no, **409 `tasca_dun_altre`** |

Cap de les dues és dolenta: totes dues són **gestos legítims** i es conserven senceres. El que no
poden ser és **l'efecte secundari de mirar**. És exactament el forat que `batec_escriptura` va
tancar el 06/08 per l'altra banda —*reobrir és un acte humà, no l'efecte d'un PATCH*— i que aquí
seguia viu per la porta del davant. Ara: **ni l'efecte d'una mirada.**

**409 i no 403**: no és manca de permís, és una decisió que ningú no ha pres encara, i el client
ha de poder oferir-la. La precedència és la mateixa que `caraObrirTasca` i `batec_escriptura` ja
apliquen: **l'albarà mana sobre tota la resta** —una tasca albaranada ha de dir que ho ESTÀ, no
«ja està feta»: són dues converses i la segona amaga la primera.

### 🚨 El front ja ho preguntava a MITGES, i és el que ho feia difícil de veure

`caraObrirTasca` tenia les tres cares i **deixava passar exactament aquests dos casos**. Es tanquen
amb dues línies i una cara nova (**FETA**, amb «Reobrir-la» — no ronda: una `Done` no lliurable no
té volta que obrir).

### 🚨 Dos tests AFIRMAVEN el forat

- «Done però NO lliurable» esperava `CARA_CAP` amb el comentari *«es reobre i prou»*. **«I prou»
  era el forat.**
- «assignada a un altre però sense ningú treballant-hi → CAP modal» duia el segell de **S-19**,
  però **el seu fixture passava l'`status` per defecte, que és `InProgress`**: no provava «feina
  prevista» sinó feina **COMENÇADA** amb el tram tancat (guard de tasca oblidada, o fuita). S-19
  no va decidir mai això. El cas de S-19 es prova ara amb `Pending`/`Paused` —els estats que S-19
  descrivia, i que **segueixen obrint sense fricció**— i el que el fixture tapava té test propi.

### 🔒 I un test existent ha evitat una regressió real

El dels **timers 116/117** («el TRAM mana sobre l'assignee»). La condició nova hi picava perquè no
mirava `obert_per`: amb tram propi la tasca és meva encara que la planificació digui una altra
cosa, i preguntar-hi hauria tornat a confondre planificació i realitat — **el que F1.5 va
separar**. La condició final només cobreix el buit que `obert_per` no veu: `InProgress` + **sense
tram** + d'un altre.

---

## 4 · R1 · SENSE ESCRIPTURA, CAP MODAL

Sortir preguntava sempre *«Has acabat?»* —una decisió que **porta a albarà**— encara que la sessió
hagués estat entrar, mirar i marxar.

La nota que ja hi havia a `exitEdit` deia que el criteri **no pot ser la durada**, i tenia raó; el
que li faltava era dir **quin ÉS**. «Hi ha hagut sessió» no vol dir «hi ha alguna cosa oberta»:
vol dir que **s'hi ha escrit**.

**Qui decideix és el SERVIDOR.** El client és el testimoni menys fiable de si s'ha escrit —i una
sessió pot morir sense passar per la sortida—: el front demana la tornada i obeeix el veredicte.
`{revertit:false}` (ha arribat una escriptura entremig, o el tram obert és d'un altre) cau al
modal de sempre.

La tornada és **una sola transició LEGAL** (`InProgress → Paused`), la mateixa que el modal ja fa,
marcada **`auto='consulta_sense_escriptura'`** — la llei del log diu que `auto` null és un gest
del tècnic i un slug és el sistema, i aquí el tècnic no ha decidit pausar res.

I **les dues meitats de J es tanquen amb el mateix gest**, per força, perquè són la mateixa
sessió: el tram que això tanca queda marcat `consulta=True` i els seus minuts no entren enlloc.

### 🚩 DECISIÓ PENDENT D'AGUS — «torna exactament on era» i `Pending`

`ALLOWED` **no té `InProgress → Pending`** —una tasca començada no pot tornar a «no començada»— i
l'ordre fixa la màquina d'estats com a **intacta**. Per tant:

- entrada des de **`Paused`** → torna a `Paused`: **exactament on era** ✅
- entrada des de **`Pending`** → queda **`Paused`** (i `started_at` queda posat) ⚠️

Obrir `InProgress → Pending` és una decisió sobre la màquina d'estats, no d'aquest tram. **Es diu
en veu alta en comptes de dissimular-la.**

---

## 5 · QA — els 4 casos de l'ordre, contra el 1383 viu

`ops/qa/qa_j_consulta_treball.py` · **21 comprovacions, 0 fallades**.

| # | Cas | Resultat |
|---|---|---|
| **a** | entrar per tasca, mirar, sortir | ✅ reverteix a `Paused`, temps **35 → 35**, tram `consulta=True`, `tram_compta` = False |
| **b** | entrar, editar una mesura, sortir | ✅ el batec marca `escriptura_at`, la sortida **NO** reverteix (`motiu: amb_escriptura`), la tasca queda En curs |
| **c** | entrar a tasca d'altri | ✅ **409 `tasca_dun_altre`** amb `obert_per_nom`; `assignee` intacte. Amb `handoff:true`, entra |
| **d** | entrar a una Feta | ✅ **409 `tasca_feta`**; segueix `Done`. Amb `reobrir:true`, entra |

Les tres regles es veuen alhora en tres trams de la mateixa tasca: **504** amb escriptura → compta;
**502** i **501** sense → `consulta=True`, fora dels agregadors.

🚩 **No va per nginx+gunicorn, i es diu.** El JWT de QA caduca en 1 h i **l'agent no en pot emetre**
(el classificador bloqueja `RefreshToken.for_user`). Es fa servir l'`APIClient` de DRF amb el Host
del tenant contra la **BD viva** — mateix URLconf, mateixa vista, mateixos permisos, mateix
serializer. El que no s'exercita és la capa nginx/gunicorn, que no és on viu res d'aquest tram.

### Dues trampes que han costat, i que queden escrites al banc

- **El batec va per SLUG i bat sobre la tasca D'AQUELL CODI**, no sobre «la que tinguis oberta». La
  primera versió del cas (b) obria `grading` i escrivia per `base-measurements/` (`SUP_MESURES`):
  el batec anava a la tasca `pom` —`Done` al 1383, per tant no-op— i el tram de `grading` es
  quedava sense marca. **No era un bug del tram: era la prova mal aparellada.**
- **`user.profile` CACHEJA.** Donar l'allow-list amb `p.save()` sense invalidar l'accessor fa que
  la vista vegi el perfil d'abans i respongui **403 `task_type_not_allowed`** — i aquell 403
  arriba **abans** del guard de J, o sigui que els tests semblen provar una cosa i no hi arriben.

---

## 6 · CENS — vist i NO tocat

- 🚩 **`TechSheetEditor.jsx` no té R1.** L'ordre el declarava fora de límits (sessió H hi era). La
  fitxa entra amb `?task_id=` i té la seva pròpia sortida: **una sessió de fitxa sense escriptura
  encara demana el modal**. És el mateix predicat i el senyal ja hi és (`sessio_amb_escriptura`);
  falta el punt de sortida d'aquell fitxer.
- 🚩 **R5 · la consulta CREA la tasca.** `open-task` segueix fent crea-si-falta (`views_b.py:578`)
  abans de tot. Les tres regles d'Agus no ho cobreixen i no s'ha tocat: obrir per mirar una tasca
  que no existeix encara la crea (`Pending`/`prevista`, amb ordre i estimació → entra al pla).
- 🚩 **R6 · `reanchored_by_start` i fase `Dev`.** Una entrada que sí que transiciona segueix
  traient el model de `Pending` i reancorant-lo al present. R1 desfà l'estat de la TASCA, no això.
- 🚩 **R4 · soroll de federació.** Cada transició publica al bessó de la marca. Amb R1 una consulta
  n'afegeix una segona (la tornada). Cap dany de dades; sí, soroll — i ara **menys** que abans a
  R3, perquè les entrades rebutjades amb 409 ja no en publiquen cap.
- ℹ️ **La QA escriu al banc 1383** (baseline v2, autoritzat per l'ordre): tres trams nous a la
  377, una escriptura de règim amb **el mateix valor** (`LINEAR ib=2.00 / brk=3.00`, sense canvi:
  verificat) i la 377 tornada a `Paused` amb `auto='qa_tram_j'`.
- ℹ️ **La suite d'una altra sessió ocupava la BD de test** tota l'estona. El banc de J s'ha corregut
  amb una BD de test pròpia via settings efímers (esborrats). Sense concurrència:
  `manage.py test fhort.tasks.test_j_consulta_treball`.

---

## 7 · COMMITS (cap push)

| Commit | Què |
|---|---|
| `79785ee4` | **R2** · la marca, el veredicte i la clàusula de `TRAMS_SANS` (+ migració 0050) |
| `36ddcb48` | **R3** · els dos gestos explícits, la cara FETA i els tests girats |
| `46813700` | **R1** · el predicat de sortida i la tornada silenciosa |
| `3aa804a2` | el banc: 16 tests + els 4 casos contra el 1383 |

**Porta verda:** `manage.py check` net · `migrate_schemas` (mai `--schema`) amb columnes auditades
per `information_schema` a `fhort` i `los` · `npm run build` ✓ · `eslint` **0 errors** ·
`node --test caraObrirTasca.test.js` **21/21** · `manage.py test …test_j_consulta_treball`
**16/16** (1 skip).
