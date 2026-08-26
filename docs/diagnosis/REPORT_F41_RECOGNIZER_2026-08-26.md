# F4.1 · Piece recognizer v1 — acta

**Data:** 2026-08-26 · **Patró B** · **Branca:** `f41-recognizer` · **Worktree:** `/var/www/ftt-f41`
**Fonts:** `REPORT_GCD_ONTOLOGY_2026-08-25.md` · `INFORME_GIMNAS_N2_GARMENTCODEDATA_2026-08-25.md` ·
`REPORT_GCD_CORPUS_IMPORT_2026-08-26.md` · `ftt_corpus` (128.974 designs, **només lectura**)

---

## 0 · El veredicte en cinc línies

1. 🚨 **La premissa del brief no sobreviu al seu propi examen.** El banc del corpus —1,4 M
   de panells de GarmentCode— treu **4 de 30 = 13 %** contra els patrons reals de la casa,
   i **cap llindar no separa l'encert de l'errada** (AUC 0,567 · 0,673). Per decisió de
   l'Agus queda construït, cacheat i provat, **i apagat**.
2. 🚨 **El sostre del corpus és del 50 % i no el mou cap geometria**: GarmentCode no té
   paraula per a `yoke`, `lining`, `facing`, `neckband`, `ruffle`, `placket` ni
   `interlining` — 15 de les 30 peces amb veritat de l'examen.
3. ✅ **El banc de TENANT sí que funciona: 10 de 10.** És el que s'envia, i el que creix
   sol cada vegada que algú confirma una peça.
4. 🚨 **El score és un MARGE, no una quota de vot.** La quota va ser mesurada i rebutjada:
   al corpus era **activament enganyosa** (10 de 26 errades amb ≥80 % dels vots).
5. ✅ **Examen real: 5 encerts · 0 errades · 45 silencis.** El criteri dur es compleix, i
   el llindar (0,20) és el doble del punt on les errades cauen a zero (0,10).

---

## 1 · L'arquitectura, amb `fitxer:línia`

| peça | on | què fa |
|---|---|---|
| `recognition/descriptor.py` | `backend/fhort/patterns/recognition/descriptor.py:1` | **LA** definició del descriptor. Un sol lloc, dos cridants |
| `recognition/ftt_geometry.py` | `…/ftt_geometry.py:1` | `PatternPiece` → l'espai del banc (mm→cm, quina vora, quin sentit) |
| `recognition/bank.py` | `…/bank.py:1` | `CorpusBank` (npz cacheat, lazy) i `TenantBank` (peces confirmades) |
| `recognition/recognizer.py` | `…/recognizer.py:1` | La cascada N1→N2→N3→N4 |
| `recognition/service.py` | `…/service.py:1` | L'ÚNIC lloc que escriu propostes, i el que no pot escriure res més |
| hook d'import | `patterns/views.py:470` | Corre en acabar l'import. No pot tombar la pujada |
| endpoint | `patterns/views.py:494` | `POST …/recognize/`, idempotent, **el mateix camí** |
| UI | `frontend/src/components/pattern/PieceIdentityList.jsx:1` | Pre-omplert + xip d'evidència + acceptar |
| comanda | `patterns/management/commands/build_recognition_bank.py` | Construeix el cache del corpus |
| laboratori | `ops/recognition/lab_exam.py` · `ops/recognition/lab_d2.py` | L'examen, sense BD i sense importar res |

### 1.1 🚨 Una sola funció de descriptor, i per què és la peça més fràgil

El banc compara una peça d'FTT contra panells del corpus per distància euclidiana en 40
dimensions. Si els dos costats calculen el vector **ni que sigui una mica diferent** —un
remostreig distint, una convenció de mirall, centímetres contra mil·límetres— totes les
distàncies són falses **i no es queixa res**: la consulta segueix tornant 200 veïns, només
que són els que no toquen.

Per això n'hi ha UNA, i un test que empeny la mateixa geometria pels dos camins:

```
skirt_front    desc_maxdiff=0.000e+00 contour_maxdiff=0.000e+00
right_ftorso   desc_maxdiff=0.000e+00 contour_maxdiff=0.000e+00
right_collar_front  desc_maxdiff=0.000e+00 contour_maxdiff=0.000e+00
```

**Bit a bit.** El test compara contra `/root/gcd_corpus/scripts/descriptors.py` —el codi
que va calcular de debò els 1,4 M de files— i no contra una relectura de com haurien de
ser: a la BD hi ha el que aquell codi va produir.

### 1.2 Els canals 6 i 7, emmascarats per al corpus

Mesurat, i no suposat:

| | corpus (1,4 M panells) | FTT (les cinc peces del 837) |
|---|---|---|
| vores per peça | mediana **5**, mitjana 6,68 | **8-28** punts de gir |

Una vora de GarmentCode és **paramètrica** —una Bézier cúbica pot ser tota una sisa—; una
vora d'FTT és un **gir de CAD**, i la mateixa sisa arriba com un sol tram amb cent vèrtexs
a dins. No compten el mateix, i posar-los al mateix canal seria un biaix constant a cada
consulta que no reportaria ningú. Al banc de TENANT **no s'emmascaren**: allà tots dos
costats són DXF.

---

## 2 · 🚨 Per què el corpus no proposa

### 2.1 L'examen, tal com va sortir

50 peces de cinc patrons reals llegides del disc, 30 amb veritat coneguda:

```
── corpus bank alone, variant=sew k=200 ──
  known truth   : 30
  HITS          : 4/30  = 13.3 %
```

### 2.2 El sostre, abans de tocar cap geometria

```
slugs que GarmentCode pot produir : 11
peces amb veritat                 : 30
...la veritat de les quals GC SAP DIR      : 15
...la veritat de les quals GC NO TÉ PARAULA: 15
   → yoke 4 · lining 3 · facing 2 · neckband 2 · ruffle 2 · placket 1 · interlining 1
SOSTRE = 15/30 = 50 %
```

**Cap feina de geometria no mou aquest número.** És vocabulari que no existeix a l'origen,
i ja ho deia l'ontologia (§5.1: 22 dels 30 slugs d'FTT GarmentCode no els pot produir).

### 2.3 I la meitat que sí que és a l'abast, tampoc

De les 15 peces que GC SÍ que sap anomenar, n'encerta 4. La causa és estructural i es
mesura en àrees:

| peça d'FTT | àrea | contrapart de GC | àrea mediana de GC | raó |
|---|---:|---|---:|---:|
| 837.DELANTERO (`front`) | 5.286 cm² | `ftorso` | 797 cm² | **6,6×** |
| 837.ESPALDA (`back`) | 5.466 cm² | `btorso` | 711 cm² | **7,7×** |
| 837.MANGA (`sleeve`) | 1.103 cm² | `sleeve_f` | 705 cm² | 1,6× |
| 837.CUELLO (`collar`) | 118 cm² | `collar_front` | 117 cm² | **1,0×** |

> 🔑 **GarmentCode SEMPRE parteix el vestit per la cintura** (cos + faldilla + cinturilla);
> un patronista de debò talla el davant d'un vestit d'una peça. El davant del 837 és
> `ftorso + skirt_front` alhora. I fixa't en el coll: **àrea idèntica (118 contra 117) i
> tot i així el kNN el va dir `skirt_front` amb 127 vots de 200** — o sigui que ni tan sols
> és només qüestió d'escala: la descomposició en panells de GarmentCode no és la
> descomposició en peces del taller.

### 2.4 🚨 El pitjor no és errar: és errar fort

| senyal | encerts (min/med/max) | errades (min/med/max) | AUC |
|---|---|---|---:|
| quota de vot | 0,60 / 0,72 / 0,85 | 0,28 / 0,69 / **0,99** | **0,567** |
| distància al 1r veí | 1,98 / 2,15 / 7,23 | 0,34 / 2,03 / 6,93 | 0,673 |

**10 de 26 errades arriben amb ≥80 % dels vots; només 1 de 4 encerts.** Amb n=4 encerts,
aquestes AUC són indistingibles del soroll. Un banc que s'equivoca el 87 % de les vegades
**i és més sorollós justament quan s'equivoca** no pot acostar-se a una proposta.

> El corpus queda construït, cacheat, provat i **apagat** darrere
> `FTT_RECOGNITION_USE_CORPUS`. Es queda perquè la mesura es pugui discutir, no perquè
> s'hagi d'engegar.

---

## 3 · La cascada que s'envia

```
N1  empremta idèntica a una peça CONFIRMADA del tenant  → proposta directa, score 1,0
N2  kNN al banc de tenant, score = MARGE                → candidat rol + cara
N3  coherència de graf contra SeamPairTemplate          → re-puntua (sostre +0,10)
N4  score < llindar                                     → CAP proposta
```

### 3.1 Per què el score és un marge

Amb un banc de deu files, la quota de vot no diu res; al corpus deia mentides. El marge és

```
(d_rival − d_millor) / (d_rival + d_millor)
```

on `d_rival` és la distància al millor veí **d'un rol diferent**. És adimensional, viu a
[0,1] i val exactament 1,0 quan no hi ha rival. Una diferència a seques voldria dir una
cosa diferent a cada mida de banc; una raó, no.

### 3.2 N3 informa, no mana

El sostre és una constant (`N3_MAX_BOOST = 0.10`) i el suport **només suma, mai resta**: el
catàleg és la gramàtica de GarmentCode, i un `placket` d'FTT pot ser perfectament correcte
i no tenir cap plantilla. El context es llegeix només de les peces que **ja** superen el
llindar: deixar que una peça insegura avali una altra peça insegura és com un patró es
convenç a si mateix d'una història.

---

## 4 · D2 · L'examen REAL (els titulars)

50 peces de `837` · `TATE` · `CALLIE` · `MEREDITH` · `AMELIA`, llegides del disc **sense
importar res i sense escriure cap dada de domini**.

```
── D2 · REAL EXAM · threshold 0.20 ──
  pieces          : 50
  proposed & RIGHT: 5
  proposed & WRONG: 0   <<< el criteri dur
  SILENT          : 45  (90 %)
```

**El 90 % de silenci és el resultat honest, no un fracàs.** El banc té avui cinc rols
confirmats (`collar`, `front`, `back`, `sleeve`, `placket`) i quatre dels cinc patrons de
l'examen no en comparteixen cap peça. Un reconeixedor que hagués proposat alguna cosa per a
les 45 hauria estat inventant.

### 4.1 El que sí que resol, i és el cas que passa cada dia

| cas | resultat |
|---|---|
| **re-import de geometria idèntica** (fitxer 18 contra el banc) | **5/5**, N1, score 1,000 |
| **versió nova del mateix patró** (fitxer 20 contra el 19) | **4/5** + 1 silenci honest |

El silenci del 4/5 és el `837.CUELLO`: marge 0,107 entre `collar` i `placket`, que en
aquest patró són dues tires petites. **És una moneda a l'aire i s'ha de veure com a tal.**

---

## 5 · D3 · La calibració del llindar

Escombrat sobre l'examen REAL (no sobre el laboratori):

| llindar | encerts | **errades** | silencis |
|---:|---:|---:|---:|
| 0,02 | 8 | **19** | 5 |
| 0,05 | 6 | **9** | 25 |
| 0,08 | 5 | **2** | 40 |
| **0,10** | 5 | **0** | 45 |
| 0,15 | 5 | **0** | 45 |
| **0,20 ← s'envia** | 5 | **0** | 45 |
| 0,30 | 5 | 0 | 45 |
| 0,50 | 5 | 0 | 45 |

**El llindar més baix amb zero errades és 0,10.** S'envia **0,20**: el doble, i entre 0,10
i 0,50 no es perd ni un encert, o sigui que el marge de seguretat és gratis.

La segona lectura, feta a part sobre 45 peces foranes: tota peça la veritat de la qual **no
és al banc** surt amb marge **≤ 0,099**, i tota proposta errònia **≤ 0,058**, mentre que
les propostes bones van de **0,255 a 1,000**. Dos poblacions separades per un buit.

Paràmetre de sistema: `FTT_RECOGNITION_MIN_SCORE` (`settings.py`), per entorn.

---

## 6 · Latència

| què | mesurat |
|---|---|
| reconèixer un patró de 5 peces | **110 – 172 ms** |
| construir el banc de tenant (10 peces) | inclòs en l'anterior |
| construir el cache del corpus (285.831 panells) | 5,7 s, un cop, offline |

Molt per sota del sostre de 2 s que justificaria una cua, i dos ordres de magnitud per sota
dels 10 s de la frontera del brief. **El hook corre síncron i no s'ha muntat cap
infraestructura de tasques**, que és el que la frontera demanava.

---

## 7 · La pantalla

**La regla de color, en una frase:** verd = un humà ho ha confirmat · taronja = una màquina
ho ha proposat · res = ningú no ho ha dit encara.

- El camp de rol arriba **pre-omplert** amb la proposta, amb el badge d'estat de dada que
  la norma ja té ratificat (`--warn-state` / `--warn-state-bg` / `--warn-ink`, §1b(d)).
  **Cap color nou**: un color nou per a una idea que ja en té un serien dos idiomes visuals.
- `proposta.is_confirmed` el decideix **el servidor**. El color d'un estat no s'endevina
  a la vista.
- El **xip d'evidència diu la raó, no el número**: «és la mateixa peça que 837.MANGA», «es
  cus amb front, back». Un score sense la seva raó és un número que ningú no pot discutir.
  El marge i el llindar hi són, però al `title`.
- **El silenci es diu**: «45 sense proposta» a la capçalera i un xip mut per peça amb el
  motiu. Sense això, «no ha sortit res» i «no s'ha executat» es veurien igual.
- Acceptar = un clic (✓ al xip). El gest en bloc existent no es toca.
- i18n ca/en/es amb paritat verificada · icones Tabler outline · colors per token.

---

## 8 · La garantia, i com es fa complir

`proposed_role` · `proposed_face` · `proposed_score` · `proposed_evidence` · `proposed_at`
són columnes **a part** de `piece_role` i `face`. No és estil: si compartissin columna, el
dia que el reconeixedor s'equivoqués ningú no podria dir si aquell rol el va decidir una
persona o una màquina — que és exactament la pregunta que caldria respondre.

I no és una promesa, és una llista: `recognition.service.UPDATE_FIELDS` és el que arriba a
la BD, i les columnes confirmades no hi són. El test ho asserta perquè la garantia
sobrevisqui a algú que hi afegeixi un camp amb pressa d'aquí a sis mesos.

**En confirmar, la proposta es conserva** i l'acta en copia el slug i el score. Sense això,
«quantes en va encertar?» seria immesurable el primer cop que algú re-corregués les
propostes.

---

## 9 · Tests

```
FTT_TEST_DB=test_ftt_f41 venv/bin/python manage.py test \
    fhort.patterns.tests_recognizer --settings=fhort.settings_test --keepdb
```

| classe | què defensa |
|---|---|
| `DescriptorPortTest` | els dos camins donen **el mateix vector** · una relliscada mm/cm és sorollosa |
| `CascadeTest` | N1 guanya N2 · N2 proposa · **N4 calla** · N3 re-puntua sense manar · el silenci porta evidència |
| `NeverTouchesConfirmedTest` | `UPDATE_FIELDS` **no pot** arribar a una columna confirmada · la proposta sobreviu a la confirmació |
| `EndpointTest` | el re-run és idempotent · la proposta arriba a l'API amb la seva evidència |

---

## 10 · Desviacions del brief, amb motiu

| desviació | motiu |
|---|---|
| **El corpus no proposa** (el brief el volia com a N2) | 13 % a l'examen real, sostre del 50 %, i cap llindar que separi. Decisió de l'Agus, 26/08 |
| N2 és el banc de TENANT i no el del corpus | és el que treu 10/10 |
| `k` per defecte 10 i no 200 | el banc de tenant té deu files; demanar-ne 200 seria demanar-les totes i dir-ne kNN |
| El senyal de PINÇA i el de POSICIÓ RELATIVA no puntuen | amb un banc de deu files **no es poden pesar honestament**, i un pes que ningú no pot mesurar és un número que algú confondrà amb evidència. N3 es queda amb la coherència de graf, que sí que té base |
| No hi ha cua de tasques | 110-172 ms per patró. La frontera del brief demanava reportar abans de muntar-ne, i no cal |

---

## 11 · Què queda

### Per a F4.2 (trams + landmarks)
`PatternSegment.edge_role` segueix **buit a tot arreu** i F4.1 no l'omple (D2 de F3). El
resolutor de landmarks (`pom/landmarks.py`) ja hi és i ja calcula l'HPS; el que li falta és
que algú —reconeixedor o patronista— posi rols a les vores.

### Per a F4.3 (costures)
La coherència de graf d'ara és feble a posta: compara rols de PEÇA. Amb rols de VORA,
`SeamPairTemplate` es podrà llegir sencer (vora amb vora) i N3 passarà de matís a senyal.

### 🚩 Per a l'Agus
1. **El banc creix confirmant.** Avui són 5 rols i 10 peces. Cada patró que la Montse
   identifiqui i confirmi el fa millor, i és l'única palanca que hi ha.
2. **DEREK no existeix en aquesta màquina.** El brief el posava a l'examen; no hi ha cap
   DXF amb aquest nom enlloc. L'examen s'ha fet amb 837 · TATE · CALLIE · MEREDITH ·
   AMELIA.
3. **El banc comú anonimitzat** segueix sent feina posterior, com dèieu. El disseny hi
   dona lloc: `TenantBank` es construeix d'un queryset, o sigui que un banc entre tenants
   és la mateixa classe amb un altre queryset i un pas d'anonimització. El que falta és el
   consentiment i la feina, no la forma del codi.
4. **Val la pena repetir l'examen quan el banc tingui 30-40 peces confirmades.** El llindar
   es va calibrar amb cinc rols; amb més rols el marge es fa més estret per construcció i
   0,20 podria haver de baixar. El laboratori (`ops/recognition/lab_d2.py --threshold`) ho
   torna a dir en un minut.

---

## 12 · Fronteres

| frontera | com s'ha comprovat |
|---|---|
| cap escriptura a `ftt_corpus` | connexió `readonly=True` sobre el rol `corpus_ro`, que només té SELECT |
| cap auto-confirmació enlloc | `UPDATE_FIELDS` no porta cap columna confirmada · test |
| cap dada de domini fora de `proposed_*` | l'examen llegeix els DXF del disc i no importa res |
| PROD | no existeix per a aquest sprint |
| push | cap |
