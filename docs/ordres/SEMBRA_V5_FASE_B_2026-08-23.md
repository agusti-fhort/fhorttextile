# SEMBRA v5 · FASE B — ASSAIG SOBRE UNA CÒPIA RESTAURADA DE PROD

**Data:** 2026-08-23 · **Màquina:** la d'staging · **BD:** `ftt_assaig_v5` (PG18:5433), **nova
i pròpia** — fora de `ftt_staging` i de tota zona intocable.
**Font:** `docs/ordres/pre_tren_panys_sobirania_20260823_0622.dump` (dump de `fhort_textile`,
23/08 06:22 UTC) · **Corpus:** r2, sha256 `07d29bdc…` verificat a cada correguda.

> **AQUEST ÉS EL GATE HUMÀ.** El brief diu: *«El report de l'assaig és el gate humà: Agus el
> llegeix ABANS de la fase C.»* Aquí hi ha què faria cada comanda a PROD, mesurat sobre les
> dades de PROD. **La FASE C (staging real) i la FASE D (PROD) NO s'han executat.**

---

# 🚨 EL QUE ATURA LA SEQÜÈNCIA (tres decisions d'Agus)

## ① S7 **ATURA sencera**: el model 173 perdria 11 cel·les si se li talla la FK

El brief dona *«els 25 models de C7-bis (=0 mesurat)»*. **Els 25 models hi són** —la xifra és
exacta— però la cobertura **re-mesurada avui** ja no és la del cens del 22/08:

```
model 173 · BRW-FW26-0011 · client BRW · joc «EU Woven Woman Regular» (pk 75)
  22 POMs mesurats · 61 regles residents · 77 regles al contenidor
  11 POMs que NOMÉS el contenidor cobreix:
     M-M79 «TOTAL LENGTH» · EK1-ANTIC · EK2-ANTIC · S «Front armhole along seam» ·
     S2 «Back armhole along seam» · J2 «WIDE STRETCHED CUFF» · F «Centre front length
     from HPS» · V «RUFFLE HEIGHT» · 0 «SLIT» · G1-ANTIC «Bottom hem height» ·
     D1 «1/2 bottom width stretched out»
```

Tallar-li la FK deixaria aquests 11 POMs a **cel·la absent**. Per això la comanda **no talla
cap dels 25 i no arxiva cap joc**: el brief mana abortar si algun surt >0, i surt.

> 🔑 **I fixa-t'hi:** dos dels 11 són **`S` i `S2`**, els mateixos que S6 ve a reactivar. El
> model 173 els mesura i els gradua **des del contenidor** perquè el catàleg els tenia morts.

**Les tres sortides, i totes són d'Agus:** (a) donar-li residents a aquests 11 abans de la
finestra; (b) deixar la FK d'aquest model i tallar els altres 24 (avui la comanda no ho fa: o
tots o cap); (c) acceptar la pèrdua i declarar-ho amb `--espera`.

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

Ordre executat: **empremta ABANS → S1→S7 en dry-run → S1→S6 escrivint → 2a passada → 3a
passada → empremta DESPRÉS**. S7 no arriba a escriure (§①).

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

## S7 · `finestra_graduacio --schema fhort` → **ATURA** (v. §① i §②)

| xifra | esperat | real |
|---|---|---|
| models amb FK a un joc | 25 | **25** ✅ |
| **FK tallades** | 25 | **0** — la finestra atura per 1 model |
| tallables si el 173 es resol | — | **24** |
| **jocs arxivats** | 27 | **11** *(28 condemnats, 17 ja inactius)* |

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
