# SEMBRA v5 · FASE B — ASSAIG SOBRE UNA CÒPIA RESTAURADA DE PROD

**Data:** 2026-08-23 · **Màquina:** la d'staging · **BD:** `ftt_assaig_v5` (PG18:5433), **nova
i pròpia** — fora de `ftt_staging` i de tota zona intocable.
**Font:** `docs/ordres/pre_tren_panys_sobirania_20260823_0622.dump` (dump de `fhort_textile`,
23/08 06:22 UTC) · **Corpus:** r2, sha256 `07d29bdc…` verificat a cada correguda.

> **AQUEST ÉS EL GATE HUMÀ.** El brief diu: *«El report de l'assaig és el gate humà: Agus el
> llegeix ABANS de la fase C.»* Aquí hi ha què faria cada comanda a PROD, mesurat sobre les
> dades de PROD. **La FASE C (staging real) i la FASE D (PROD) NO s'han executat.**
>
> **L'assaig ha servit per al que serveix un assaig:** ha trobat **un defecte del meu propi
> codi** (§①) que hauria aturat la finestra a PROD sense motiu, i ha posat xifres a tres coses
> que el brief donava per sabudes.

---

# 🚨 EL QUE QUEDA OBERT (dues decisions d'Agus, i una troballa)

## ① Els 25 models **SÓN inerts** — i el camí per saber-ho passa per un defecte meu

**Confirmat: els 25 models de C7-bis es poden tallar sense perdre cap cel·la.** La xifra del
brief és exacta. Però el primer mesurament deia el contrari, i val la pena que consti per què.

El predicat evident —«el contenidor cobreix aquest POM i cap resident no ho fa»— **no és el del
motor**. `pom/services.py:929-948` només llegeix el contenidor **si la PEÇA MARE no té cap
resident**:

```python
te_residents_la_mare = any(garment == '' for (pom_id, garment) in out)
if not te_residents_la_mare and model.grading_rule_set_id:   # ← només aquí entra el joc
```

I **els 25 models de PROD tenen residents a la mare, tots** (de 19 a 142 cada un). O sigui que
per als 25 el contenidor **ja és lletra morta des del 12/08**, i tallar-ne la FK no pot perdre
res. Amb el predicat evident, la finestra **s'aturava sencera** per un model amb 61 residents a
la mare. Corregit a `311873b2`, amb el cas al banc.

### 🚩 El que sí que surt, i és una troballa: **88 cel·les absents que ja hi són**

No les crea la finestra i no les resol; es reporten:

| model | absents |
|---|---|
| 1179 `BRW-FW26-0047` | **35** |
| 1189 `BRW-FW26-0053` | **19** |
| 173 `BRW-FW26-0011` | **15** |
| 1206 `BRW-FW26-0060` | **11** |
| 177 `BRW-FW26-0015` | 4 · 184 `BRW-FW26-0017` 2 · 163 `BRW-FW26-0001` 1 · 205 `BRW-FW26-0034` 1 |
| | **88** |

Són POMs **mesurats** al model que **cap regla resident no cobreix**: el motor no n'emet cel·la
(llei de cel·la absent). Al 173, quatre d'aquests POMs són `S`, `S2`, `EK1-ANTIC` i `EK2-ANTIC`
— els mateixos que S6 ve a reactivar i els que el catàleg tenia morts. **No és feina d'aquest
brief**, però és el material d'un tram de re-graduació que algú haurà de decidir.

## ② Els jocs condemnats són **28**, no 27 — i només **11** canviarien d'estat

| | |
|---|---|
| `GradingRuleSet` a PROD | **29** |
| supervivent (resolt **pel nom**, pany P3) | **1** — `GRADING BROWNIE 2026`, **pk 152** *(la pk del brief, aquí sí)* |
| condemnats | **28** *(el brief en diu 27)* |
| …dels quals **ja** inactius | **17** → la comanda no els toca |
| …dels quals **actius** | **11** → `actiu=False`. Cap `DELETE` |

Els 11 són els ISO (`EU Woven Woman Regular`, `EU Knit Woman Regular`, `EU Stretch Woman
Slim/Swim`, `EU Woven Man Regular`, `EU Knit Man/Baby/Toddler/Kids/Teen Regular`, `EU Woven
Woman Numeric`).

🔒 **Frontera G6, comptada i intacta:** **27 `SizingProfile`** i **22 `GarmentTypeItem`**
apunten a jocs que quedarien arxivats. **Cap escriptura** — és el que el brief mana («queden
arxivats amb els apuntadors intactes»), i ara està mesurat: no són 14 jocs amb apuntador, són
49 apuntadors.

## ③ **39 POMs vius de PROD es queden fora del v5** — i el brief comptava que hi entressin

El brief planeja *«els 112 amb lletra … els 26 vius sense família + l'1 viu amb CAT-UB»*. La
realitat del 23/08:

| | esperat pel brief | real |
|---|---|---|
| POMs vius | *(no el declarava)* | **141** |
| lligables al v5 (mapa Brownie del r2) | — | **104** → **102 lligats** + 2 que ja apuntaven a un altre global |
| **sense cap fila al v5** | — | **37** *(15 amb codi HOMÒNIM: mateixa lletra, altra mesura)* |
| remapats a les 14 famílies | *112 + 26 + 1 = 139* | **102** (42 moguts + 60 que ja hi eren) |
| vius que es queden sense família | — | **13** |

Els 37 sense fila no són soroll: hi ha `CR`/`CR1`/`CR3` (entrecuix), `FD`/`FE` (rise),
`FB`, `EK1`, `E6`/`E7`/`E8`, `FT`, `FS`… Uns quants **el v5 els resol com a DATUM d'un altre
POM** (el full `INSTANCIES` declara `incl_band`/`excl_band` per a `FD`/`FE`, `visible` per a
`FB`), i **l'eix DATUM no és a l'abast d'aquest brief**. Els altres, sense fila, no tenen
canònic.

---

# COM S'HA FET L'ASSAIG

```
CREATE DATABASE ftt_assaig_v5 OWNER ftt_staging;                       # PG18:5433
pg_restore -p 5433 -d ftt_assaig_v5 --no-owner --no-privileges \
           --role=ftt_staging docs/ordres/pre_tren_panys_sobirania_20260823_0622.dump
DB_NAME=ftt_assaig_v5 venv/bin/python manage.py migrate_schemas         # el dump era pre-0078
```

El dump porta `public` + `fhort` + `los` i, un cop migrat (0079 i 0080 incloses, les del tren
d'instàncies), **el terreny és el de PROD**: 521 `POMMaster` (141 vius · 380 d'arxiu), 53
`POMCategory`, 29 jocs, 25 models amb FK. Les xifres del brief que **SÍ que es confirmen** hi
són totes: **141/521**, **26 vius sense família**, **13 `CAT-*` de les quals 12 buides i
`CAT-UB` amb 1 viu + 84 d'arxiu**, **25 models amb FK**, **`S` i `S2` = pk 462 i 463**,
**joc Brownie = pk 152**.

Ordre executat: **empremta ABANS → S1→S7 en dry-run → S1→S6 escrivint → 2a i 3a passada →
empremta DESPRÉS → S7 escrivint → 2a passada d'S7 → empremta FINAL**. S7 va amb
`--espera "jocs arxivats=11"`, que és la xifra mesurada i **un acte humà declarat** (el brief
en deia 27; v. §②).

---

# ESPERAT vs REAL, COMANDA A COMANDA

## S1 · `sembra_families_sistema` (`public`)

| xifra | esperat | real |
|---|---|---|
| famílies del corpus | 14 | **14** ✅ |
| creades | — | **14** |
| famílies de `public` alienes al v5 (no tocades) | — | **15** *(vocabulari de sector)* |

## S2 · `sembra_cataleg_sistema --schema public --schema fhort`

| xifra | esperat | real |
|---|---|---|
| POMs del corpus · ACTIU · INACTIU | 165 · 161 · 4 | **165 · 161 · 4** ✅ |
| `POMGlobal` creats a `public` | — | **165** *(n'hi havia 125 de fora del v5, no tocats)* |
| `POMGlobal` creats a `fhort` | — | **165** *(n'hi havia 290 de fora del v5, no tocats)* |
| divergents / reescrits | — | **0 / 0** |

## S3 · `lliga_fhort_al_sistema --schema fhort`

| xifra | real |
|---|---|
| POMs vius / d'arxiu | **141 / 380** *(l'arxiu no es toca)* |
| **lligams nous** | **102** |
| sobirans respectats | **0** *(a PROD encara no n'hi ha cap)* |
| **lligams divergents, reportats i NO moguts** | **2** — `BR` (apunta a `LOSPOM-487`, el r2 diu `B6`) i `U4` (apunta a `LOSPOM-578`, el r2 diu `U4`) |
| sense destí al v5 | **37** *(15 homònims)* |
| globals amb més d'un POM del tenant | **1** — `I2`, el reclamen `J1` i `I2` |

## S4 · `sembra_alies_brownie --schema fhort`

| xifra | esperat | real |
|---|---|---|
| àlies al corpus | 105 | **105** ✅ |
| **creats** | — | **42** |
| ja correctes | — | **26** |
| **amb un altre destí, reportats i NO moguts** | — | **32** |
| sense POM lligat al seu global | — | **3** *(entre ells `BR` i `U4`, els dos contaminats)* |
| **AMBIGUS** (>1 POM al mateix global) | — | **2** — `J1` i `I2`, tots dos cap a `I2` |

🚩 **Els 32 conflictes tenen una forma, i val la pena llegir-la:** gairebé tots apunten a un POM
**`*-ANTIC`** (`EP → EP-ANTIC`, `EL → EL-ANTIC`, `IC → IC-ANTIC`…). Vol dir que **el codi de
Brownie encara resol contra el catàleg mort**. La sembra no els mou (create-only, literal del
brief), però **re-apuntar-los és un tram propi** i fins que no es faci, aquests 32 codis de
client segueixen anant a l'arxiu.

## S5 · `remap_families_fhort --schema fhort`

| xifra | esperat | real |
|---|---|---|
| **`CAT-*` buides esborrades** | **12** | **12** ✅ |
| `CAT-*` al tenant | — | **13** — `CAT-UB` es queda amb 84 POMs d'arxiu ☠️ |
| POMs remapats / ja hi eren | — | **42 / 60** |
| POMs vius sense fila al r2 (conserven família) | — | **39** |
| POMs d'arxiu tocats | — | **0** |
| famílies del v5 creades al tenant | — | **0** *(les 14 lletres ja hi eren)* |
| **famílies del v5 amb text divergent, NO tocades** | — | **14** |
| famílies velles que queden buides i **no** s'esborren | — | **7** — `J K V W X Y Z` |

## 🚩 S5, la decisió que queda oberta: **els rètols de les 14**

Les 14 lletres del v5 ja existeixen a `fhort` amb els noms de la v4, i **les 14 divergeixen**:

| codi | el tenant hi diu | el r2 hi diu | ordre |
|---|---|---|---|
| `E` | COLL · ESPATLLA · ESCOT · SOLAPA (E) | Coll, escot, espatlla i canesú · *Neck, neckline, shoulder and yoke* | 5 → 1 |
| `G` | CANALÉ, BAIXOS I GODET (G) | Acabats i vores · *Finishes and edges* | 7 → 9 |
| `N` | MOTIUS I APLICATS (N) | Elements aplicats i fornitures · *Applied elements and trims* | 15 → 14 |
| … | *(les 14, totes)* | | |

El pany les respecta i **no toca cap**. Conseqüència visible: **`/poms` ensenyarà les 14
famílies del v5 amb els rètols vells i l'ordre vell, i sense cap `nom_en`.**
**`--overwrite-from-xlsx` les posa al dia i ho fa constar. És decisió d'Agus.**

## S6 · `tancament_142 --schema fhort`

| xifra | esperat | real |
|---|---|---|
| POMs del tancament trobats | 2 | **2** ✅ — **pk 462 (`S`) i 463 (`S2`)**, les del brief |
| **reactivats** | — | **2** |
| família posada | — | **1** (`S`, pel mapa del r2) |
| **sense família resoluble** | — | **1** — **`S2`** |
| files del duplicat `SF`/«AH DEP» | — | **1** — pk **1076** `SF` «Armhole depth from HPS», **2 mesures de model** |

🚩 **`S2` no pot rebre família del v5**, i és el cas ③ altre cop: el `S2` del tenant és *Back
armhole along seam* i el `S2` del v5 és *Across width*. **El full no el mapa.** Es queda sense
família fins que Agus digui `--categoria CODI` (la candidata natural és **`A` · Pit i sisa**,
però **no s'ha posat**: no és una dada del corpus).

🚩 **El duplicat `SF` no es fusiona** (llei de la casa: vol joc daurat + banc de paritat). El
brief citava «284 “AH DEP” vs 1076»; al dump del 23/08 **només hi és la 1076** — la 284 ja no
existeix, i per tant **la fusió pot haver-se fet ja o la fila pot haver mort**. S'anota.

## S7 · `finestra_graduacio --schema fhort` (v. §① i §②)

| xifra | esperat | real |
|---|---|---|
| models amb FK a un joc | 25 | **25** ✅ |
| **FK tallades** (totes inertes) | 25 | **25** ✅ |
| cel·les absents PREEXISTENTS (reportades, no tocades) | — | **88** |
| **jocs arxivats** | 27 | **11** *(28 condemnats, 17 ja inactius)* — declarat amb `--espera` |
| `DELETE` fets | — | **0** |
| 2a passada | — | **0 talls · 0 arxivats · 28 ja inactius** |

---

# IDEMPOTÈNCIA — MESURADA EN VIU, DUES PASSADES MÉS

| comanda | 2a passada | 3a passada |
|---|---|---|
| S1 | creades **0** · iguals 14 | — |
| S2 | creats **0** · iguals 165 (× 2 schemes) | — |
| S3 | lligats **1** *(v. sota)* · ja lligats 102 | lligats **0** · ja lligats 103 |
| S4 | creats **0** · iguals 69 | creats **0** · iguals 69 |
| S5 | remapats **0** · ja hi eren 103 | remapats **0** |
| S6 | reactivats **0** · ja actius 2 | — |
| S7 | talls **0** · arxivats **0** · ja inactius 28 | — |

**L'únic moviment de la 2a passada és el que el §⑥ de la FASE A anuncia:** el `S` que S6 acaba
de reactivar entra al conjunt dels vius i S3 el lliga. A la tercera, **zero canvis a tot
arreu**: el tram convergeix.

---

# L'EMPREMTA (S0) — ABANS i DESPRÉS de l'assaig

| bloc | abans | després | |
|---|---|---|---|
| `poms` | 521 · `4f6477b6…` | 521 · `a82c071b…` | canvia el **lligam** i la **família** |
| `regles` | 1159 · `e176e5e3…` | 1159 · **`e176e5e3…`** | ⚖️ **IDÈNTIC** — el tram no toca cap regla |
| `families` | 53 · `360b8604…` | **41** · `a82c25aa…` | −12 `CAT-*` |
| `globals` | 290 · `6827f510…` | **455** · `5769fc69…` | +165 |
| **HASH GLOBAL** | `56963ce14801c04f…` | `044a3fd9f018af40…` | |

> El bloc `regles` **byte a byte igual** és la prova en viu de la llei @girth: 1 159 regles de
> catàleg i el tram no en toca ni una.

**I l'empremta no es mou amb S7:** el hash global després d'S6 i després d'S7 és **el mateix**
(`044a3fd9f018af40…`). Té sentit i val la pena dir-ho — la finestra toca `Model.grading_rule_set`
i `GradingRuleSet.actiu`, i **cap dels dos és catàleg**: el gate de la FASE E no els veurà, i
per tant **no es pot fer servir per verificar que la finestra s'ha fet**. Això es verifica amb
el report d'S7, no amb l'empremta.

**Estat final del tenant a l'assaig:** 143 vius (141 + 2 reactivats) · **106 amb canònic** · 37
sense · **13 vius sense família** · 41 famílies · l'arxiu de 380 intacte.

---

# QUÈ CAL PER PASSAR A LA FASE C

La FASE C (staging real, S1→S6, S7 fora) **està llesta per córrer** i no depèn de cap de les
tres decisions —a staging no hi ha `CAT-*`, ni condemnats, ni `S`/`S2` inactius—, però **el
brief la posa DESPRÉS del gate humà i per això no s'ha corregut**. La seqüència, quan Agus
doni el vist-i-plau:

```
cd /var/www/ftt-staging/backend
venv/bin/python manage.py sembra_families_sistema --no-dry-run
venv/bin/python manage.py sembra_cataleg_sistema --schema public --schema fhort --no-dry-run
venv/bin/python manage.py lliga_fhort_al_sistema  --schema fhort --no-dry-run
venv/bin/python manage.py sembra_alies_brownie    --schema fhort --no-dry-run
venv/bin/python manage.py remap_families_fhort    --schema fhort --no-dry-run \
    --espera "CAT-* buides esborrades=0"          # a staging no n'hi ha cap
venv/bin/python manage.py tancament_142           --schema fhort --no-dry-run
PGOPTIONS='-c default_transaction_read_only=on' venv/bin/python ../ops/sembra_v5/empremta.py
```

**El que staging donarà, mesurat en dry-run el 23/08:** 144 vius · **105 lligables** · **39
sense fila** (16 homònims) · **0 `CAT-*`** · `S` i `S2` **ja actius** (pk 1012 i 1013) · S7 **no
hi entra**.

🚨 **I una cosa que el gate de la FASE E ha de saber abans de començar:** staging i PROD
**arrencaven de catàlegs diferents** (144 POMs vius vs 141, i 521 files vs 144). L'empremta
compara **tot el `POMMaster`**, o sigui que **els hashos NO podran coincidir** mentre els dos
entorns no tinguin el mateix contingut de catàleg. La sembra v5 **no ho iguala**: sembra el
catàleg de SISTEMA (que sí que quedarà idèntic: mateixos 165 globals i mateixes 14 famílies) i
lliga el que cada entorn ja tenia. **El gate de la FASE E, tal com el brief el descriu
—“empremta staging == empremta PROD”—, avui no el pot passar ningú.** El que sí que és
comparable, i el que proposo com a gate real, és el **bloc `globals` i el bloc `families`**: són
els que el tram escriu, i han de sortir **idèntics als dos entorns**. Decisió d'Agus.

---

# CAP RASTRE FORA DE L'ASSAIG

**Cap escriptura a `ftt_staging`** (els dry-run hi han corregut i han fet `set_rollback`), cap a
PROD, cap `systemctl restart`, cap `npm run build`, cap push. La BD `ftt_assaig_v5` es queda
viva per si Agus la vol mirar; s'esborra amb
`sudo -u postgres psql -p 5433 -c 'DROP DATABASE ftt_assaig_v5;'`.

**Les decisions són d'Agus.**
