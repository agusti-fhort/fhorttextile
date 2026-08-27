# REPORT ROSETTA 837 — el camp de la Montse contra la GV201 v9

**Data:** 2026-08-27 · **Fil:** F6-PRE · **Naturalesa:** DIAGNOSI amb dataset
**Banc:** model 1383 (`TRV-SS27-0001 · 837 VESTIT`) · `PatternFile#20` v3 · `GradingVersion#201` (v9, aprovada 24/08)
**Camp:** `docs/ordres/837 CORS 194 VESTIT M3-4 ESCALAT.DXF` · md5 `7d8297d4549fcb26f2e87bbed48ac4ea` · 799 870 B
**Mestre:** `media/fhort/pattern_files/837_CORS_194_VESTIT_M3-4_AGUS.DXF` · md5 `c77cf1c3a22fe491bf09a32bb6361247`
**Codi:** [`ops/rosetta/`](../../ops/rosetta/) · **Dataset:** [`ops/rosetta/parity_837.json`](../../ops/rosetta/parity_837.json) (919 KB)

> **Fronteres respectades.** Read-only absolut: només `SELECT` sobre el schema `fhort` i
> lectura del `media`. Cap migració, cap `systemctl`, cap escriptura a cap taula. El fitxer
> de la niada **no s'ha importat pel camí de producte** (25 blocs `_TALLA` crearien 25
> «peces»): entra com a material de banc. Escriptures de la sessió: aquest informe, el
> dataset, `ops/rosetta/*.py`, `ops/rosetta/README.md` i la còpia del DXF a `docs/ordres/`.
> Branca pròpia `f6-pre-rosetta`, cap push.

---

## 0 · El veredicte en set línies

1. **El banc és un camp de debò, no un ram de peces.** 25 blocs = 5 peces × 5 talles, amb
   recompte de vèrtexs, classificació gir/corba i orientació CCW **idèntics a les cinc
   talles**, i la talla base **byte a byte igual** al patró que el 1383 té importat
   (desviació 0,000000000 mm a les cinc peces). Les cinc verificacions d'ingesta passen i
   **totes cinc s'han vist caure en vermell** quan se'ls toca el que miren.
2. **CONVENCIÓ-1 deixa de ser una declaració i passa a ser una regla derivable:** l'origen
   de bucle és **l'argmin de Y del contorn de tall a la talla base**, i surt exactament als
   índexs que el brief donava (DELANTERO 30 · ESPALDA 259 · CUELLO 171 · MANGA 39 ·
   TAPETA 3). A les cinc peces l'argmin és **únic** — sense això seria una tria, no una regla.
3. 🚨 **La hipòtesi del brief sobre la MANGA queda REFUTADA per mesura.** El seu vèrtex més
   quiet es mou +3,000 mm per graó, que sembla col·locació; **no ho és**. Restar-ho puja el
   residu màxim de 23,86 a **32,47 mm** a XL (+36 %). La MANGA no porta translació: grada en
   els dos sentits i cap vèrtex no s'hi està quiet, que no és el mateix.
4. 🚨 **El camp NO porta capa 14**, i 19 de les 20 àncores de POM del 1383 hi viuen. La
   comparació només existeix perquè les àncores s'hi **transporten** — i el transport té
   tres lectures que **no diuen el mateix** allà on hi ha corba. La dispersió entre elles és
   la barra d'error de cada fila, i sis POMs la tenen prou gran per quedar **NO RESOLUBLES**
   sobre aquest banc: no desviats, **no decidibles**.
5. ✅ **On es pot decidir, la resposta és que sí: és el mateix vestit.** 10 POMs en paritat,
   amb els increments reproduïts **a la xifra de la fitxa** (B −2,00/+3,00/+6,00/+9,00 ·
   J1 −0,25/+0,25/+0,50/+0,75). I **el break de la F es reprodueix al camp de la Montse**:
   la fitxa demana +2/+2/+1 cm i el camp fa +2,00/+1,96/+1,00.
6. 🚨 **Un sol desacord és gros i no és soroll: la D.** La fitxa demana **+3,00 cm per
   talla** al baix i el camp de la Montse en grada **+0,50** — un factor 6, **75 mm
   acumulats a XL**. Es confirma per un camí que no passa pel transport: mesurat
   **directament sobre els piquets del fitxer de la Montse**, el baix fa 59,03 → 61,02 cm.
   No és un artefacte nostre: o la regla D del 1383 és mala, o el patró no grada el baix.
   **Decisió d'Agus/Montse, no de l'agent.**
7. ✅ **El cas positiu de la C2-bis passa 7 de 8.** Els POMs FIXED donen delta 0,00 —i no
   només els del coll i la tapeta (que no graden): també els quatre del DELANTERO i els dos
   de l'ESPALDA, que són **peces que sí graden**. L'únic que no tanca (E5) és dels sis no
   resolubles per portador, no un desmentiment.

---

## 1 · A — Ingesta i verificacions

`engine/aama_reader.py` ja llegeix aquest dialecte i ja tracta cada BLOCK com una peça: no
calia parser propi, i reutilitzar-lo té un guany que no és estalvi — el banc es llegeix amb
**el mateix codi** que llegirà el patró de producte, i una regressió del reader es veurà
aquí també. L'única feina afegida és agrupar els 25 blocs pel sufix del nom.

El que el fitxer diu de si mateix: `Author: PolyPattern` · `Units: Metric` ·
**`Sample Size: S`** · `Style Name: M.837.GEN`. Capçalera buida → unitats deduïdes per
geometria (1,0 mm/unitat, confiança baixa: mm i 1/10 mm són tots dos plausibles com a
factor, i la mida de les peces desempata).

| verificació | resultat |
|---|---|
| **A1 · recompte de vèrtexs** | idèntic a les cinc talles: CUELLO 566 · DELANTERO 498 · ESPALDA 462 · MANGA 280 · TAPETA 38 |
| **A2 · correspondència vèrtex a vèrtex** | classificació gir/corba invariant a les cinc talles, índex per índex, a les cinc peces |
| **A3 · orientació CCW** | 25 de 25 bucles CCW (àrea signada > 0) |
| **A4 · CONVENCIÓ-1, origen únic** | argmin de Y **únic** a les cinc peces → índexs 171 / 30 / 259 / 39 / 3 |
| **A5 · base ≡ patró mestre** | desviació màxima **0,000000000 mm** a les cinc peces, vèrtex a vèrtex |

**A5 és la que sosté tota la resta.** Sense ella el Rosetta compararia dos vestits
diferents i el que en sortís seria soroll amb decimals. Es mesura vèrtex a vèrtex i no per
capsa: dues peces poden compartir bbox i no compartir ni un punt.

**Les cinc s'han vist VERMELLES.** Girar un bucle → A3 cau · empatar dos vèrtexs a Y mínima
→ A4 cau (`2 vèrtexs empaten: [3, 10]`) · tocar una classificació → A2 cau (`M[7]:
curve≠turn`) · moure un vèrtex **0,001 mm** → A5 cau. Una sonda que no s'ha vist caure no és
una sonda: A2 va néixer amb un `pass` dins del bucle i comparava zero coses.

### 1.1 · El que el camp NO porta, i mana sobre tot el mètode

- 🚨 **Cap capa 14.** Capes presents: `1, 2, 3, 4, 7`. El patró mestre en té dues més
  (`8, 14`). El camp només grada el **contorn de tall**.
- **Cap número de regla.** Els `# N` que el mestre porta sobre els 28 girs del DELANTERO no
  hi són. El camp és **extensional** (coordenades per talla); les regles viuen al germà.
- **Piquets: 4–6 per peça** contra els 8–12 del mestre — el mestre en té de tall **i** de
  cosit; els del camp són el subconjunt de tall, i coincideixen tots.

---

## 2 · B — Alineació: separar la niada del grading

El brief donava dos mètodes; al material real en calen **tres**, i el tercer no és teòric.

| peça | mètode | àncora | residu màx (XL) | candidats mesurats |
|---|---|---|---:|---|
| CUELLO | origen fix | 0 | 0,00 mm | — (camp nul) |
| DELANTERO | origen fix | 242 | 60,95 mm | — |
| ESPALDA | origen fix | 0 | 60,62 mm | — |
| **MANGA** | **cap** | — | **23,86 mm** | desplaçament mínim = **32,47** · cap = **23,86** |
| TAPETA | origen fix | 0 | 0,00 mm | — (camp nul) |

**Quatre peces de cinc tenen origen fix**: hi ha un vèrtex que no es mou a cap talla, o
sigui que el CAD ja va niar les cinc clavades per aquell punt i no hi ha res a treure.

🚨 **La MANGA és el cas que el brief donava per resolt i no ho estava.** El seu vèrtex més
quiet (índex 123) es desplaça +3,000 / +5,999 / +8,998 mm — tan rodó que sembla col·locació,
i el brief ho llegia així («min 9 mm → porta translació»). **La mesura diu que no:** restar
aquest vector puja el residu màxim de 23,86 a 32,47 mm, un **+36 %**. El motiu és que la
màniga grada en els **dos** sentits (dx ∈ [−22,6, +9,5] mm a XL) i el 123 només és el punt
de gir del camp. Un mètode que triï per regla i no per xifra hauria escrit al dataset un
camp de desplaçament un terç més gran que el de debò.

**`alinea` decideix, doncs, mesurant:** corre els dos candidats i es queda el que deixa el
residu màxim més petit, i desa tots dos a `candidats_mm` perquè la tria s'auditi sense
tornar a córrer res.

⚠️ **Res de tot això toca la taula C.** Recta, vora, projecció i ortogonal són les quatre
invariants per translació: el Rosetta surt idèntic amb alineació i sense. L'alineació és per
al **dataset**, perquè el que el solver F6 haurà de reproduir sigui grading i no la posició
del full.

---

## 3 · C — El Rosetta

### 3.1 · El forat de la capa 14, i com es travessa

Les receptes `PatternPOM` del 1383 ancoren **19 de 20 àncores a la línia de cosit**. El camp
no la porta. No es resol ni ignorant-ho ni re-ancorant els POMs a mà: es resol
**transportant** cada punt del patró mestre amb el desplaçament del contorn de tall.

I «el desplaçament del contorn de tall **al costat**» no vol dir una sola cosa. Se'n corren
**tres**:

| portador | com ancora l'àncora al bucle de tall |
|---|---|
| `projeccio` *(canònic)* | el punt més proper del contorn (peu de la perpendicular), amb interpolació dins l'aresta |
| `vertex` | el **vèrtex** de tall més proper. El més cru i el més independent: no interpola res |
| `fraccio` | el punt del tall a la **mateixa fracció d'arc**, des de l'origen de CONVENCIÓ-1 de cada bucle |

🚨 **A la sisa del DELANTERO les tres divergeixen.** La projecció d'una àncora de cosit cau
a l'aresta 301 i el vèrtex més proper és el **306**: cinc vèrtexs de distància, perquè en una
corba «el més proper» i «el de la mateixa posició» no són el mateix punt. Allà on divergeixen,
el Δ del POM **és una propietat de la tria, no del vestit** — i per això la dispersió va a la
taula com a `incertesa` i no com a nota al peu.

🔑 **Porta d'entrada (C0).** A la talla base el desplaçament és zero per construcció, o sigui
que el valor que en surt ha de reproduir `PatternPOM.valor_mesurat_cm` a l'últim decimal. Ho
fa: **desviació màxima 0,0460 mm** sobre 20 POMs × 3 portadors, per sota dels 0,05 mm que és
mig decimal de com el camp es desa (dos decimals de cm). I els **3 840 `PatternPoint`** del
`PatternFile#20` casen amb el patró mestre: **0 incoherents**.

🔑 **Un altre detall que el brief demanava com a «fracció» i que la mesura ha corregit:**
l'origen del bucle de la costura **no** es busca amb l'argmin de Y propi. Es pren el punt de
la costura més proper a l'origen de tall. A quatre peces és el mateix; **a la TAPETA no**, i
allà l'argmin propi esbiaixa la fracció **0,368 del perímetre (209 mm d'arc)** en comptes de
0,0099 (7,8 mm). Dues parametritzacions només es poden comparar si l'origen és al mateix lloc
material, i «Y mínima» no ho garanteix en un bucle que no és el mateix bucle.

### 3.2 · La taula de paritat — Δ de deltes, en mm

`Δ de deltes = (quant grada el camp) − (quant diu la fitxa que grada)`, comptat des de la
base. És **la xifra del Rosetta**: el desacord de base entre patró i fitxa se'n va sol i el
que queda és només grading. Llindar 0,5 mm (proposat per la fase, pendent de ratificació).

| POM | peça | tipus | mèt. | XS | S | M | L | XL | \|Δ\|max | incert. | veredicte |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| E7 | CUELLO | FIXED | recta | +0,00 | +0,00 | +0,00 | +0,00 | +0,00 | 0,00 | 0,00 | **PARITAT** |
| A | DELANTERO | LINEAR | recta | −0,14 | +0,00 | −0,83 | −1,49 | −2,42 | 2,42 | 2,12 | NO RESOLUBLE |
| B | DELANTERO | LINEAR | recta | +0,00 | +0,00 | −0,00 | −0,00 | −0,00 | 0,00 | 0,00 | **PARITAT** |
| C | DELANTERO | LINEAR | recta | +0,00 | +0,00 | +0,00 | −0,01 | −0,01 | 0,01 | 0,93 | NO RESOLUBLE |
| **D** | DELANTERO | LINEAR | recta | **+10,02** | +0,00 | **−25,03** | **−50,06** | **−75,09** | **75,09** | 0,79 | 🚨 **DESVIAT** |
| E | DELANTERO | LINEAR | recta | +0,96 | +0,00 | −1,20 | −2,37 | −3,55 | 3,55 | 3,45 | NO RESOLUBLE |
| E5 | DELANTERO | FIXED | projeccio | −0,26 | +0,00 | −0,26 | −0,83 | −1,07 | 1,07 | 1,11 | NO RESOLUBLE |
| EK | DELANTERO | FIXED | projeccio | +0,00 | +0,00 | +0,05 | +0,10 | +0,12 | 0,12 | 0,04 | **PARITAT** |
| EK1 | DELANTERO | FIXED | projeccio | +0,00 | +0,00 | +0,04 | +0,07 | +0,10 | 0,10 | 0,04 | **PARITAT** |
| F | DELANTERO | LINEAR | recta | +0,00 | +0,00 | +0,04 | −0,32 | −0,35 | 0,35 | 0,12 | **PARITAT** |
| S | DELANTERO | LINEAR | vora | −1,72 | +0,00 | −0,16 | +0,56 | +1,60 | 1,72 | 1,05 | DESVIAT |
| SLT | DELANTERO | FIXED | recta | +0,29 | +0,00 | −0,32 | −0,40 | −0,25 | 0,40 | 0,08 | **PARITAT** |
| E1 | ESPALDA | LINEAR | recta | +0,31 | +0,00 | −0,89 | −1,69 | −2,51 | 2,51 | 2,32 | NO RESOLUBLE |
| EK2 | ESPALDA | FIXED | projeccio | +0,00 | +0,00 | +0,05 | +0,08 | +0,13 | 0,13 | 0,01 | **PARITAT** |
| G1 | ESPALDA | FIXED | recta | +0,00 | +0,00 | −0,00 | −0,00 | −0,00 | 0,00 | 0,01 | **PARITAT** |
| S2 | ESPALDA | LINEAR | vora | −1,42 | +0,00 | −0,05 | +0,06 | +1,38 | 1,42 | 1,56 | NO RESOLUBLE |
| SF | ESPALDA | LINEAR | projeccio | +0,62 | +0,00 | −0,42 | −0,88 | −1,25 | 1,25 | 0,49 | DESVIAT |
| I | MANGA | LINEAR | projeccio | −0,01 | +0,00 | +0,43 | +0,98 | +1,53 | 1,53 | 0,06 | DESVIAT |
| J1 | MANGA | LINEAR | recta | +0,00 | +0,00 | +0,00 | +0,00 | +0,01 | 0,01 | 0,15 | **PARITAT** |
| U | TAPETA | FIXED | recta | +0,00 | +0,00 | +0,00 | +0,00 | +0,00 | 0,00 | 0,00 | **PARITAT** |

**Com es llegeix el veredicte.** Desviació i incertesa es comparen **entre elles**, no
cadascuna amb el llindar. Una barra d'error de 0,8 mm damunt d'una desviació de 75 mm no fa
dubtosa la desviació; i una desviació de 0,01 mm amb una barra de 0,93 mm no és paritat, és
que no se sap.

- **DESVIAT** — |Δ| − incertesa > llindar: el desacord sobreviu a l'error.
- **PARITAT** — |Δ| + incertesa ≤ llindar: l'acord sobreviu a l'error.
- **NO RESOLUBLE** — la barra travessa el llindar. Sobre **aquest** banc no es pot dir, i el
  que falta per poder-ho dir és **la capa 14 graduada**.

### 3.3 · El mateix, en el llenguatge de la fitxa (increments en cm)

| POM | font | XS | S | M | L | XL |
|---|---|---:|---:|---:|---:|---:|
| A | fitxa | −2,00 | +0,00 | +3,00 | +6,00 | +9,00 |
| | camp | −2,01 | +0,00 | **+2,92** | +5,85 | +8,76 |
| B | fitxa | −2,00 | +0,00 | +3,00 | +6,00 | +9,00 |
| | camp | −2,00 | +0,00 | **+3,00** | +6,00 | +9,00 |
| C | fitxa | −2,00 | +0,00 | +3,00 | +6,00 | +9,00 |
| | camp | −2,00 | +0,00 | **+3,00** | +6,00 | +9,00 |
| **D** | fitxa | −1,50 | +0,00 | +3,00 | +6,00 | +9,00 |
| | camp | **−0,50** | +0,00 | **+0,50** | **+0,99** | **+1,49** |
| E | fitxa | +0,00 | +0,00 | +0,60 | +1,20 | +1,80 |
| | camp | +0,10 | +0,00 | +0,48 | +0,96 | +1,44 |
| **F** | fitxa | +0,00 | +0,00 | +2,00 | +4,00 | +5,00 |
| | camp | +0,00 | +0,00 | **+2,00** | **+3,97** | **+4,97** |
| S | fitxa | +0,00 | +0,00 | +0,80 | +1,60 | +2,40 |
| | camp | −0,17 | +0,00 | +0,78 | +1,66 | +2,56 |
| E1 | fitxa | +0,00 | +0,00 | +0,30 | +0,60 | +0,90 |
| | camp | +0,03 | +0,00 | +0,21 | +0,43 | +0,65 |
| S2 | fitxa | +0,00 | +0,00 | +0,80 | +1,60 | +2,40 |
| | camp | −0,14 | +0,00 | +0,80 | +1,61 | +2,54 |
| SF | fitxa | +0,00 | +0,00 | +0,50 | +1,00 | +1,50 |
| | camp | +0,06 | +0,00 | +0,46 | +0,91 | +1,37 |
| I | fitxa | +0,00 | +0,00 | +1,00 | +2,00 | +3,00 |
| | camp | −0,00 | +0,00 | +1,04 | +2,10 | +3,15 |
| J1 | fitxa | −0,25 | +0,00 | +0,25 | +0,50 | +0,75 |
| | camp | −0,25 | +0,00 | **+0,25** | +0,50 | +0,75 |

✅ **El break de la F es reprodueix.** La fitxa demana +2 / +2 / **+1** cm (l'últim graó és
la meitat) i el camp de la Montse fa +2,00 / +1,96 / **+1,00**. La nostra maquinària de
breaks codifica una cosa que la Montse va fer de debò al patró.

✅ **La predicció «XS = S» es compleix.** La fitxa declara increment zero a XS per a E, E1,
F, S, S2, SF i I; al camp aquests set es mouen entre −0,17 i +0,10 cm. I els cinc que la
fitxa **sí** grada a XS (A −2,00 · B −2,00 · C −2,00 · J1 −0,25) hi cauen clavats — **tots
menys la D**.

### 3.4 · Resum per peça

| peça | n | mitjana \|Δ\| | màx | ≤ 0,5 mm |
|---|---:|---:|---:|---|
| CUELLO | 4 | 0,00 mm | 0,00 mm | 4/4 |
| DELANTERO | 44 | 4,14 mm | 75,09 mm | 28/44 |
| ESPALDA | 20 | 0,59 mm | 2,51 mm | 12/20 |
| MANGA | 8 | 0,37 mm | 1,53 mm | 6/8 |
| TAPETA | 4 | 0,00 mm | 0,00 mm | 4/4 |
| **global** | **80** | **2,46 mm** | 75,09 mm | 58/80 |
| **global sense la D** | 76 | **0,48 mm** | 3,55 mm | 54/76 |

La mitjana global la fa la D tota sola: **traient-la, la mitjana cau de 2,46 a 0,48 mm i la
mediana és 0,10 mm.** El desacord del 837 no està repartit; està **concentrat en una regla**.

### 3.5 · El cas positiu de la C2-bis

| | POM | peça | \|Δ\|max | veredicte |
|---|---|---|---:|---|
| ✅ | E7 | CUELLO | 0,00 mm | PARITAT |
| 🚩 | E5 | DELANTERO | 1,07 mm | NO RESOLUBLE |
| ✅ | EK | DELANTERO | 0,12 mm | PARITAT |
| ✅ | EK1 | DELANTERO | 0,10 mm | PARITAT |
| ✅ | SLT | DELANTERO | 0,40 mm | PARITAT |
| ✅ | EK2 | ESPALDA | 0,13 mm | PARITAT |
| ✅ | G1 | ESPALDA | 0,00 mm | PARITAT |
| ✅ | U | TAPETA | 0,00 mm | PARITAT |

L'esmena d'Agus es verifica, **i amb més força de la que demanava**: coll i tapeta no graden
gens (els seus 566 i 38 vèrtexs són idèntics a les cinc talles, delta exacte 0,000), però
això sol seria trivial. El que val és que **sis dels vuit FIXED viuen en peces que SÍ
graden** — quatre al DELANTERO i dos a l'ESPALDA — i allà la peça es mou desenes de mil·límetres
mentre la mesura es queda quieta a ≤ 0,4 mm. **FIXED = restricció de delta zero dur** queda
justificat com a classe pròpia del solver, no com a cas particular de LINEAR amb increment 0.

### 3.6 · C3 · POMs no mesurables sobre el banc

| POM | motiu |
|---|---|
| **J** | **sense recepta `PatternPOM` al 1383.** Té `GradedSpec` a les cinc talles (16,30 / 16,60 / 17,35 / 18,10 / 18,85 cm, LINEAR +0,75/graó) però cap àncora al patró. És el 21è POM de la fitxa i el 20è del patró: **el forat és d'ancoratge, no de dada.** |

I els sis **NO RESOLUBLES** (A, C, E, E1, E5, S2), que no són el mateix: la seva mesura
existeix però depèn de quin portador es triï més que del vestit. Tots sis tenen les àncores
a la línia de cosit en zones de **corba** (sisa, escot, costat). El que els desbloquejaria és
tenir la capa 14 graduada — o re-ancorar-los a punts del contorn de tall.

---

## 4 · Anomalies (no són grading, i s'anoten)

Δ **absolut** a la base = el que el patró MESURA menys el que la fitxa DECLARA. No és
grading: és la distància entre el patró i la fitxa, i al 837 no és zero.

| POM | patró (cm) | fitxa @S (cm) | Δ @S | nota |
|---|---:|---:|---:|---|
| **EK** | 25,05 | 22,00 | **+30,5 mm** | 🚨 El més gros. El docstring de `PatternPOM` diu que `EK` «dona 26,8 en recta i ~22 en projecció H, i la fitxa declara 22,0» — però la recepta viva **ja és** `projeccio/H` i dona 25,05. Les àncores s'han mogut des que es va escriure aquella nota. **Cal re-ancorar EK o corregir la fitxa.** |
| SF | 22,40 | 22,00 | +4,0 mm | |
| J1 | 12,44 | 12,00 | +4,4 mm | |
| C | 53,57 | 54,00 | −4,3 mm | |
| S | 22,36 | 22,00 | +3,6 mm | |
| EK1 | 8,00 | 7,70 | +3,0 mm | |
| A | 44,29 | 44,00 | +2,9 mm | |
| F | 110,77 | 110,50 | +2,7 mm | |
| resta | | | ≤ 2,1 mm | |

**Cap d'aquests desacords contamina la taula C**: la comparació de deltes els cancel·la per
construcció. Però són la mesura de com de lluny està la fitxa del patró **avui**, i val la
pena mirar-s'ho abans que el solver F6 els doni per bons com a objectiu.

### 4.1 · La D, en detall — i per què no és culpa nostra

La fitxa demana +3,00 cm per talla al baix; el camp en grada +0,50. Per descartar que fos
artefacte del transport es va mesurar **pel camí curt: els piquets del fitxer de la Montse,
sense moure res**:

| talla | piquets del baix (mm) | amplada |
|---|---|---:|
| XS | (895,675 · 758,041) ↔ (895,675 · 1348,319) | **59,03 cm** |
| S | (895,674 · 755,548) ↔ (895,674 · 1350,812) | **59,53 cm** |
| M | (875,674 · 753,055) ↔ (875,674 · 1353,305) | **60,03 cm** |
| L | (855,674 · 750,562) ↔ (855,674 · 1355,798) | **60,52 cm** |
| XL | (845,673 · 748,069) ↔ (845,673 · 1358,291) | **61,02 cm** |

**+0,50 cm per graó, mesurat a la carn del fitxer.** El transport en deia +0,50 i el camí
directe també (separació entre les dues vies: 0,05 mm). El desacord és real.

I no és que la peça no gradi: al mateix DELANTERO, **A (pit) grada +2,92 · B (cintura) +3,00
· C (maluc) +3,00** — tots tres a la xifra de la fitxa. El baix, i només el baix, es queda a
la sisena part. Llegit en roba: **la volada del vestit disminueix amb la talla**.

🔑 **Pregunta per a la Montse (no la resol l'agent):** el baix del 837 grada +0,5 cm per
talla a posta —perquè amb 118 cm de vol ja n'hi ha prou i creixeria desproporcionat— o la
regla D del 1383 es va omplir copiant el +3 de l'A/B/C?

---

## 5 · D — El dataset: `ops/rosetta/parity_837.json`

919 KB. Tres blocs: `meta`, `peces`, `poms`.

**`meta`** — font i md5 dels dos fitxers, textos del document, unitats, talles i base,
model / `PatternFile` / `GradingVersion`, portador canònic i llista de portadors, l'enunciat
literal de CONVENCIÓ-1, com s'ha establert la correspondència, el llindar, i l'avís de la
capa 14 absent.

**`peces`** — per peça: `n_vertexs` · `origen_bucle` (CONVENCIÓ-1) · `tipus_vertex[]`
(gir/corba) · `fraccio_vertex[]` (fracció d'arc des de l'origen, 8 decimals) · `alineacio`
(mètode, àncora, translacions, candidats mesurats) · i per talla: `contorn_alineat[[x,y]]`,
`desplacament_vs_base[[dx,dy]]`, `piquets[[x,y]]`, `fil[x1,y1,x2,y2]`, `residu_max_mm`.
Coordenades a 4 decimals (el DXF en porta 3).

**`poms`** — 21 files amb `classe_restriccio` (**`delta_zero_dur`** per als FIXED,
`delta_lliure` per als LINEAR), `veredicte`, `carrier_max_mm`, `valor_patro_cm`,
`valor_fitxa_cm`, `valor_camp_cm` **pels tres portadors**, `delta_de_deltes_mm`,
`delta_absolut_mm` i `incertesa_portador_mm`.

**Com el llegirà F6:** el camp de desplaçament per vèrtex és l'objectiu a reproduir; les
fraccions són el sistema de coordenades on viuen les restriccions; `delta_zero_dur` són
igualtats dures; i `veredicte` diu quines files es poden fer servir com a criteri d'èxit i
quines no (les NO RESOLUBLES **no** han d'entrar al residu: penalitzarien el solver per una
ambigüitat del banc).

---

## 6 · El que això obre — brief del solver F6

1. 🔒 **CONVENCIÓ-1 és ratificable.** Ja no és una declaració: és `argmin(y)` del contorn de
   tall a la base, únic a les cinc peces, heretat per identitat d'índex. Falta el gest
   d'Agus (Patró C) per fixar-la com a llei.
2. 🚨 **El prerequisit dur del solver no és el solver: és la capa 14 graduada.** Sis dels 20
   POMs no es poden decidir sobre aquest banc perquè les seves àncores viuen a la costura i
   el camp només porta el tall. Dues sortides, i s'han de triar abans de construir:
   **(a)** demanar a la Montse la niada **amb capa 14**; **(b)** re-ancorar aquests sis POMs
   a punts del contorn de tall. La (a) no costa codi i la (b) canvia dades del 1383.
3. **La tolerància ≤ 0,5 mm és realista per a 14 POMs de 20 i no ho és per a sis.** Ratificar
   la xifra val la pena, però amb l'excepció escrita: sobre aquest banc, sis files hi tenen
   una barra d'error més gran que la tolerància mateixa.
4. **`FIXED` = classe pròpia del solver** (restricció d'igualtat dura, delta zero), verificat
   7/8 sobre peces que graden. No és un LINEAR amb increment 0.
5. **La D és una decisió de domini pendent** i bloqueja fer servir el DELANTERO com a criteri
   d'èxit global: mentre la regla D no es resolgui, el residu del solver al davant estarà
   dominat per un desacord que no és del solver.
6. **La J vol àncora.** És l'únic POM de la fitxa sense recepta al patró; ancorar-la puja el
   banc de 20 a 21 files.
7. **L'EK vol una mirada** abans que el solver l'agafi com a objectiu: 30,5 mm entre el que
   el patró mesura i el que la fitxa declara, amb una nota al codi que ja no descriu la
   recepta viva.
8. **Risc declarat, sense canvis:** un sol model de banc. El 837 és tot el que tenim per a
   graduació (D-INV-7), i cinc peces d'un vestit no cobreixen ni pantalons ni peces amb
   pinces ni res amb doblec materialitzat.
