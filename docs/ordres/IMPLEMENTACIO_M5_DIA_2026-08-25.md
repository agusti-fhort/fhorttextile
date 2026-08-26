# M5-DIA · RETROACTIU DE LA R1 + NETEJA DEL TREN

> **Worktree** `/var/www/ftt-m5`, branca `m5-dia` · **8 commits, CAP PUSH** · cap restart del
> servei compartit. Aquesta sessió deixa la branca **LLESTA PER AL TREN**; la suite sencera va
> a la nit amb ordre a part — **aquí no se n'ha llançat cap**.

## 🚨 0 · UNA CORRECCIÓ DE BASE, ABANS DE RES

El brief diu «Base: dev amb M4 fusionat (merge d'Agus)». **Aquell merge encara no s'ha fet:**

```
$ git log --oneline -1 dev
2cdaccd5 merge: M3 — cicle de vida, tres estats, 4a columna com a fet d'entrega
$ git branch -a --contains d8fb8183
+ m4-comercial          ← M4 viu NOMÉS aquí
```

**S'ha basat el worktree en `m4-comercial` (`d8fb8183`)**, que és el que `dev` serà quan Agus
faci el merge. És l'única lectura que fa coherent la FASE 3: `settings_m4.py` només existeix en
aquella branca, i «cap fitxer amb nom de milestone» no es pot complir sense tenir-lo al davant.

⚠️ **Si el merge d'M4 a `dev` resol algun conflicte, aquesta branca vol un rebase abans del tren.**

---

## 1 · FASE 1 · EL RETROACTIU · `b2c311ec` + `80227efe`

### L'univers, mesurat

| | `fhort` | `los` |
|---|---|---|
| Models | 39 | 51 |
| … **amb almenys una `ModelTask`** | **10** | 0 |
| … sense cap tasca (FORA de l'univers, FIT-4) | 29 | 51 |
| `ModelTask` amb `ronda = NULL` | **18** | 0 |
| Models amb feina i **cap fila `Ronda`** (pre-llei purs) | **5** | 0 |

Els cinc no tenien cap volta: el cas més simple possible, **una R1 per model i prou**. Cap tenia
feina repartida entre voltes existents, o sigui que la clàusula «un model amb voltes i feina
solta també hi entra» del script no s'ha exercit a staging (hi és perquè el codi no ho pot donar
per fet).

### El script — `ops/retroactius/retroactiu_r1_m5.py`

Un **ACTE DECLARAT**, que és el que M1-bis exigia en aixecar la prohibició: es llegeix, es valida
en sec i s'aplica amb guarda. **No és una migració**, i per això aquest sprint no en porta cap.

Les quatre lleis, al codi:

| | |
|---|---|
| **FIT-4 · l'univers** | Models amb almenys una `ModelTask`. **0 tasques = cap R1** (mai han tingut cap gest; fabricar-los una volta seria inventar-la). |
| **FIT-1 · neixen OBERTES** | `tancada_el = NULL`, **cap `Entrega` fabricada**. Conseqüència buscada: **cap model canvia a «Entregats»**. |
| **Adopció total** | **TOTES** les tasques `ronda = NULL` del model. Aquí ja no hi ha «buit» ni «pre-primera»: tot el passat és R1. |
| **Només s'escriu `ronda`** | Ni motiu, ni mare, ni estats, ni timers, ni Welford, ni cap `TaskTransition`. `update()` de queryset → **`updated_at` tampoc es mou**. |

🔑 **La data no és la d'avui.** `Ronda.oberta_el` és `auto_now_add` i la fila neix amb l'hora
d'ara, que seria mentida per a feina de fa dues setmanes. Es corregeix amb un `UPDATE` posterior
al **mínim `created_at` de les tasques que adopta** (`auto_now_add` només dispara a l'INSERT).

**Per defecte va EN SEC** i desa la llista de validació. `--apply` exigeix
`--espera-models`/`--espera-tasques` i **avorta sense escriure** si l'univers no hi casa. Un
univers **buit no és discrepància**: és l'estat d'arribada, i per això la segona execució surt
amb 0 canvis en lloc de petar.

### La validació d'Agus, i les dues decisions

El dry-run es va desar a **`docs/ordres/RETROACTIU_R1_STAGING_DRYRUN.md`** (annex d'aquesta acta)
i es va aturar allà. Agus va resoldre les dues preguntes que la llista plantejava:

| | |
|---|---|
| **El 1383** (`TRV-SS27-0001`, banc del fil motor) | **INCLÒS.** «Intocable» ha volgut dir sempre *no li toquis el motor*, i el retroactiu no l'hi toca: ni graduació, ni patrons, ni mesures, ni POMs — només `ModelTask.ronda`. Deixar-lo fora hauria deixat un model pre-llei viu i **hauria bloquejat la FASE 2 sencera**. |
| **`QA-M1-0005`** (pre-llei fabricat) | **Adoptat com la resta, I retirat del banc.** Adoptar-lo sol no n'hi havia prou: un `banc_m1_rondes.py --remunta` **n'hauria refabricat un l'endemà**, ressuscitant una població que el codi ja no sap explicar. Les dues coses van juntes o cap. |

### El resultat, verificat **per SQL contra la taula**

```
[fhort] R1 creades=5 · tasques adoptades=18
[fhort] POST · ModelTask sense ronda=0 · models PRE-LLEI=0
[los]   univers buit → 0 canvis (idempotent)
```

| model | codi | seq | `oberta_el` | `tancada_el` | tasques | entregues |
|---|---|---|---|---|---|---|
| 1320 | `BRW-FW26-0001` | 1 | 2026-08-09 16:42 | **—** | 5 | **0** |
| 1322 | `BRW-26-FW-0002` | 1 | 2026-08-10 10:43 | **—** | 2 | **0** |
| 1379 | `BRW-FW26-0002` | 1 | 2026-08-16 14:51 | **—** | 4 | **0** |
| 1383 | `TRV-SS27-0001` | 1 | 2026-08-20 16:53 | **—** | 5 | **0** |
| 1496 | `QA-M1-0005` | 1 | 2026-08-24 20:44 | **—** | 2 | **0** |

Les cinc **OBERTES** i amb **zero `Entrega`**. **Cap model ha canviat de columna al board** — era
el resultat esperat i està mesurat: cap dels cinc tenia tota la feina a `Done`, o sigui que cap no
vivia a la 4a columna per l'excepció pre-llei.

**Segona execució = 0 canvis.** La idempotència no és una afirmació del docstring: està correguda.

### I les notes que declaraven la prohibició

`Ronda` i `ronda_del_gest` ja no diuen «fins al retroactiu de M5». Diuen que **l'acte s'ha fet**,
d'una sola vegada, i que **la prohibició segueix vigent per a tot el que no sigui aquell acte**:
l'obertura automàtica només mira endavant i no adopta res, avui igual que ahir.

---

## 2 · FASE 2 · LES DUES EXCEPCIONS AUTOEXTINGIBLES · `5be40c0c` + `0bc6287c`

Totes dues es van declarar autoextingibles a posta, i **totes dues s'havien apagat soles**: amb la
població pre-llei a **0**, cap de les dues branques trobava ningú.

### ② M3 · CODA C1 — la lectura vella de la 4a columna

Se'n va la línia `if row['ronda_seq'] is None: return 'done'` de `views_b.kanban_state`. La 4a
columna queda sent **només un fet d'entrega**, sense excepcions.

> ## 🚨 L'ACTA D'M3 DEIA «UNA LÍNIA I UN TEST», I EN VAN CAURE **TRES**
>
> L'acta d'M3 (§C4) instruïa: *«Es retira aquella línia i el test `test_EXCEPCIO_PRE_LLEI_…`, i
> **no hi ha res més a tocar**.»* Va semblar prudent mesurar-ho abans de creure-ho —llei
> `ftt-acta-al-codi-pot-mentir`— i la correguda amb la branca retirada dona **3 vermells**:
>
> | test | per què cau |
> |---|---|
> | `test_EXCEPCIO_PRE_LLEI_…` | mesurava l'excepció · **previst per l'acta** |
> | `test_i_l_excepcio_s_APAGA_SOLA_…` | mesurava l'autoextinció · l'acta no el nomena |
> | **`test_done_nomes_quan_tot_es_done`** | 🚨 **és un dels 14 de FASE 0b que l'acta donava per verds per sempre.** El seu fixture era un model amb feina i **sense volta** — després del retroactiu, una població impossible |
>
> Els dos primers se'n van i **un de sol els substitueix**
> (`test_M5_un_model_amb_feina_SEMPRE_te_volta_…`), que guarda la llei que queda. El tercer
> **s'inverteix**: passa a dir `test_cap_tasca_viva_JA_NO_es_done_per_si_sol`, amb un fixture real.
> La lliçó queda escrita al docstring de la classe perquè no s'hagi de tornar a descobrir.

`_amb_r1()` nou a la base de tests: dona la R1 **com ho fa el producte** (`ronda_del_gest`) als
casos que parlen de la VOLTA. Els 13 de precedència de feina viva no hi passen — aquella branca
no consulta la volta i el fixture no els canvia la resposta.

**by_model: 31 → 30 tests, OK.** (−2 retirats, +1 de substitució.)

### ① M2 · CODA-BIS — la barra de progrés global del pla pla

Se'n va el bloc `{!perVoltes && list.length > 0 && …}` de `WorkPlan.jsx`, i amb ell:

- `done` i `pct`, que ja no els llegia ningú més;
- la clau `model_sheet.dashboard.workplan.progress_pla` (ca/en/es);
- el bloc **B-bis** de `qa_m2_cara_pantalla.py`, que mesurava l'apagada. L'asserció **⑤** («amb
  voltes, cap barra global») queda viva i ara **val per a TOTS els models**;
- 🚨 **l'entrada `LLEGAT` de `banc_m1_rondes.py`** — v. la decisió d'Agus a §1.

**La branca del pla PLA (graella de `TaskCard`) es queda**, i no per descuit: si `rondes` no
carrega, el pla s'ha de seguir veient. Passa de ser un **cas de domini** a ser una **degradació**,
i el comentari ho diu. El que s'ha retirat és la BARRA, que és el que la CODA-BIS va construir i
el que el brief nomena.

---

## 3 · FASE 3 · NETEJA DEL TREN · `e782070c` + `d4a29290` + `690c8e6b`

### Els shims de settings → **un de sol, i parametritzat**

`settings_m1` · `settings_m3` · `settings_m3_gates` · `settings_m4` eren **quatre fitxers
idèntics tret d'una cadena**, cadascun amb el nom de l'sprint que el va necessitar. S'absorbeixen
a **`settings_test.py`**, on el nom de la BD deixa de ser una constant al codi i passa a ser
**paràmetre de la correguda**:

```
FTT_TEST_DB=test_ftt_nit venv/bin/python manage.py test … --settings=fhort.settings_test --keepdb
```

Resol millor el problema original —sessions concurrents que es destrueixen la BD de test— perquè
**dos blocs en paral·lel es donen dos noms sense afegir cap fitxer**. I s'ha dogfoodejat en aquest
mateix gate: els blocs RONDA i COMMERCE han corregut **alhora**, amb `test_ftt_m5dia` i
`test_ftt_m5comm`. Cap script viu referenciava els vells; només les actes, que són històric.

### 🚩 3 (M3) — `EstatBadge.jsx` mort · **RETIRAT**

Zero importadors, confirmat. 🔑 **I val la pena dir per què no saltava a la vista: n'hi havia DOS
amb el MATEIX NOM.** El viu és `components/commercial/estats.jsx` (4 pantalles el munten); el mort
era `components/EstatBadge.jsx`. Un `grep EstatBadge` ingenu feia semblar viu el mort.

### 🚩 4 (M3) — la columna «Estat» de `/models` · **JA DIU LA VERITAT**

Pintava un guió amb el motiu escrit a sota («Estat comercial: pendent del Kanban»), i **va ser
correcte el dia que es va escriure**: llavors `Model.estat` era l'estat INTERN
(`Nou/EnCurs/EnRevisio/Tancat`) i no el de la §8e. **M3 · FIT-9 va canviar el camp**: avui és el
CICLE DE VIDA amb tres estats i cap més, és el criteri de domini de les tres vistes d'aquesta
mateixa pantalla, i la llista ja el serveix.

Ara es pinta amb el **badge viu**, codis de `/vocabulari/` (`estats_model`, que ja existia) i mapa
de color de la §8e. **Cap estat nou.** La nota de columna buida i la seva clau i18n se'n van.

> `jubilat` va **NEUTRE i no vermell**: jubilar és una decisió de negoci (surt del catàleg), no
> una fallada, i el vermell de la §1 és per al que ha acabat MALAMENT. El distingeix la PARAULA —
> el mateix criteri que la decisió 2 d'`estats.jsx` aplica a `Paused`/`Pending`.

### Escombrada final

`grep -E "TODO\s*\(?\s*(M1|M2|M3|M4|M5)"` sobre `backend/fhort`, `frontend/src` i `ops` → **ZERO**.

Però quatre comentaris i **un missatge d'asserció** seguien afirmant que el passat esperava M5, i
això ja és fals:

| on | què deia |
|---|---|
| `test_m3_fit11.py:52` | el fixture de feina llegada era «la forma de la BD» — ara es diu **per què es conserva** (mesura que `mare_homologa` sap encadenar quan la volta anterior no té fila) |
| `test_m1bis_fit4.py:189` | el missatge deia «prohibit fins a M5» — ara diu que `ronda_del_gest` només mira endavant, i que el passat el va resoldre **el retroactiu, mai aquesta funció** |
| `test_m1bis_fit4.py:421` | la frontera de l'adopció del BUIT segueix manant igual, i el docstring diu per què |
| `WorkPlan.jsx:34` | el pla pla ja no és «la forma de tot model llegat»: és **degradació** |

**Fora d'abast, anotat i no tocat:** els `TODO B4c` / `TODO B5` de `commerce/` són marques del
full de ruta comercial (sèrie B), no de milestone.

---

## 4 · EL GATE DE DIA (quirúrgic — la suite és de nit)

| | |
|---|---|
| `manage.py check` | ✅ net després de cada commit |
| **Bloc RONDA sencer** (8 fitxers + `test_m4_desbordament`) | **`Ran 268 tests` · `OK`** |
| **`by_model`** | **`Ran 30 tests` · `OK`** ⚠️ el brief en deia 31: −2 retirats, +1 de substitució (§2) |
| **`cicle`** | **`Ran 35 tests` · `OK`** |
| **`COMMERCE`** | **`Ran 55 tests` · `OK`** |
| `npm run build` | ✅ verd |
| `npx eslint src` | ✅ **0 errors** (274 warnings, totes preexistents) |
| **Fum de pantalla** | **`20 OK · 0 FAIL`** + 4 captures |

```
# els dos blocs llargs, EN PARAL·LEL i cadascun amb la seva BD (dogfooding de `settings_test`)
FTT_TEST_DB=test_ftt_m5dia  venv/bin/python manage.py test <bloc RONDA>   --settings=fhort.settings_test --keepdb
FTT_TEST_DB=test_ftt_m5comm venv/bin/python manage.py test <bloc COMMERCE> --settings=fhort.settings_test --keepdb
```

**Migracions: cap de nova.** Els caps al disc segueixen sent `tasks 0053` · `models_app 0087` ·
`commerce 0022`, i `makemigrations --check` diu `No changes detected`. **És correcte per disseny**:
el retroactiu és un acte declarat, no un efecte secundari d'una migració.

### El fum de pantalla · `ops/qa/qa_m5_retroactiu_pantalla.py`

El retroactiu és una **escriptura silenciosa**: cap gest, cap toast, cap transició. La manera de
saber que ha anat bé no és el log del script —que diu el que el script *creu*— sinó mirar què
dibuixa el producte. Sobre `QA-M1-0005` (banc sintètic; **mai el 1383, mai un model real**):

| captura | què hi ha |
|---|---|
| **`m5_a1_fitxa_r1_retroactiva.png`** | **la peça**: el Pla de treball pintat PER VOLTES amb el contenidor `RONDA 1 · En curs · inici 24/08 · 20:44 · fi — · 1h 14m · 2 tasques`, el seu progrés propi `1/2 · 50%`, i **cap barra global** |
| `m5_b1_registre.png` | la volta al Registre, amb la data del PASSAT |
| `m5_c1_board.png` | el model al board amb el xip de volta, i **NO a «Entregats»** |
| `m5_d1_columna_estat.png` | `/models` amb la columna «Estat» pintant els badges i sense la nota del Kanban |

Dues mesures que valen la pena: la columna «Entregats» es mesura **PER DINS** (al `body` sencer hi
són tots i la mesura sortiria verda digués el que digués), i el substrat es mesura **abans** de
mirar cap pantalla (R1 oberta · 0 `Entrega` · 2 tasques · data del passat · **0 models pre-llei a
tot el tenant**).

⚠️ El fum **no escriu res de domini**. L'única escriptura és `planned_start` — precondició C4a del
board: sense planificar, el model no hi entra i la mesura sortiria verda sense mesurar res.

---

## 5 · ELS 8 COMMITS (cap push)

| | |
|---|---|
| `b2c311ec` | `feat(m5)` el retroactiu de la R1 — script declarat, amb dry-run i guarda |
| `80227efe` | `feat(m5)` el retroactiu **APLICAT** — 5 R1, 18 tasques, població pre-llei = 0 |
| `5be40c0c` | `refactor(m3-coda)` retirar l'excepció PRE-LLEI de la 4a columna |
| `0bc6287c` | `refactor(m2-coda-bis)` retirar la barra de progrés global PRE-LLEI |
| `e782070c` | `chore(tren)` un sol settings de suite, i cap fitxer amb nom de milestone |
| `d4a29290` | `feat(models)` la columna «Estat» diu la veritat, i el badge mort se'n va |
| `690c8e6b` | `docs(tren)` escombrada — les afirmacions «fins al retroactiu de M5» ja són falses |
| `b3a45caf` | `qa(m5)` fum de pantalla del retroactiu — 20 OK · 0 FAIL |

---

## 6 · RESUM DE 🚩 I DECISIONS PENDENTS

| # | Què | On |
|---|---|---|
| 🚨 **A** | **M4 no és a `dev`.** Aquesta branca surt de `m4-comercial`. Si el merge d'M4 resol conflictes, `m5-dia` vol un **rebase abans del tren** | §0 |
| 🚨 **B** | **L'acta d'M3 deia «una línia i un test» i en van caure TRES.** El tercer era un dels 14 que l'acta donava per verds per sempre. Mesurat, no suposat — i la lliçó queda al docstring de la classe | §2 |
| 🚩 **C** | **El model `QA-M1-0005` es diu «Llegat sense volta (pre-llei)» i ara TÉ volta.** El nom ja no descriu res. És dada del banc, no codi: renombrar-lo vol un gest sobre `fhort` i no s'ha fet sense demanar-ho. Un `banc_m1_rondes.py --remunta` l'esborra i **ja no el refabrica** | §1 |
| 🚩 **D** | **La branca del pla PLA de `WorkPlan.jsx` es queda com a degradació.** Avui és codi que no es pinta mai (cap model sense volta). Retirar-la deixaria el Pla en blanc si `rondes` no carrega; mantenir-la és codi mort per al camí feliç. **Decisió d'Agus** si es vol retirar del tot | §2 |
| 🚩 **E** | **La resta de `KanbanStateTest` (13 tests) segueix fabricant tasques amb `ronda = NULL`** —una població que ja no existeix— perquè la seva branca no consulta la volta i el fixture no els canvia la resposta. Fer-los realistes vol tocar `_tasca` i, en cascada, `BoardRondaAwareTest`. **Anotat i no tocat** (codi mínim) | §2 |
| 🚩 **F** | `TODO B4c` / `TODO B5` a `commerce/` — full de ruta comercial (sèrie B), fora d'abast d'M5 | §3 |
| ⛔ | **La suite sencera NO s'ha llançat**: el brief la reserva per a la nit, amb ordre a part | §4 |
