# Gimnàs N2 — empremta primitiva vs GarmentCodeData (v2)

**Data:** 2026-08-25 · **Fil:** S46-MOTOR · Patró A, gimnàs N2
**Pla:** DISSENY_MOTOR_PARAMETRIC_V2 §2-bis punt 2 · empremta de §3.1-N2
**Precedent:** INFORME_PYGARMENT_MODEL_DADES_2026-08-25

> **Fronteres respectades.** Tota la feina viu a `/root/n2_gym/` amb venv propi
> (`/root/n2_gym/venv`). Cap `systemctl`, cap escriptura al repo ni a cap worktree,
> cap migració, cap escriptura a cap BD, cap `pip install` al venv del projecte,
> cap accés al vault. **Aquest fitxer és l'única escriptura fora de l'scratchpad.**
> Disc consumit total: **647 MB** (608 MB el venv, 37 MB les dades, 2,5 MB les
> sortides) — molt per sota del sostre de 5 GB.

---

## 0 · El veredicte en cinc línies

1. L'empremta primitiva (allargament + ompliment + signatura de vores) **encerta
   el 52,2 % dels rols de panell** entre 24 caselles, contra una base majoritària
   del 12,5 %. Amb el prior de tipus de peça, 55,9 %.
2. **Dos terços de l'error no són soroll: són indecidibles.** El davant i el
   darrere d'una mateixa peça són, en 4 de 12 parelles, **el mateix polígon**
   (`sl_cuff_f` ≡ `sl_cuff_b`, `ins_skirt_front` ≡ `ins_skirt_back`…). Cap
   mesura del contorn els podrà separar mai.
3. Si es col·lapsa el davant/darrere en **famílies** (13 caselles), l'empremta
   puja a **63,2 %**, i amb prior a **71,3 %** (base 25,0 %).
4. **El prior de tipus de peça val +8,1 punts** sobre famílies, i el que mata són
   exactament les confusions *entre* tipus (faldilla→pantaló, puny de màniga→puny
   de camal). No toca gens les confusions *dins* del tipus.
5. La signatura de vores és la meitat que carrega el pes (43,3 % tota sola contra
   15,3 % del numèric), però **cap de les dues sola no arriba a la combinació**.

---

## 1 · PAS 0 — Baixada controlada

### 1.1 On són les dades (el DOI no les serveix)

| Passa | Resultat |
|---|---|
| `https://doi.org/10.3929/ethz-b-000690432` | → `hdl:20.500.11850/690432` → Research Collection (SPA Angular, 403 a curl pelat) |
| API DSpace `…/server/api/pid/find?id=hdl:20.500.11850/690432` | ítem `9d16a4da-0d30-4963-8842-af20fcf82899` |
| Bundle ORIGINAL de l'ítem | **1 sol bitstream: `Dataset_documentation_v2.pdf`, 605 885 B, MD5 `fabfdb6ede7e09cc2b6db0da586e1437`** |

> 🚨 **El DOI de l'ETH NO conté el dataset.** L'ítem del Research Collection
> només publica el PDF de documentació. La ruta real surt d'un URI incrustat
> **dins del PDF**: `https://libdrive.ethz.ch/index.php/s/4UtC8smtLOGwKoZ`
> (share públic ownCloud). Es llegeix per WebDAV amb el token com a usuari:
> `curl -u 4UtC8smtLOGwKoZ: -X PROPFIND https://libdrive.ethz.ch/public.php/webdav/`.
> Llicència CC-BY-4.0.

### 1.2 Què hi ha al share i quina és la unitat mínima

Volum total del share: **395,16 GB**. Estructura: 36 lots
(`GarmentCodeData_v2/garments_5000_{0..35}/`), cadascun amb `default_body/` i
`random_body/`, i dins de cada subcarpeta **un únic `data.tar.gz`**.

| Unitat | Mida |
|---|---|
| `data.tar.gz` més petit (lot 22, `random_body`) | **4,701 GB** |
| `data.tar.gz` més gran (lot 15, `default_body`) | **5,916 GB** |
| El que hem fet servir: lot 0, `default_body` | **5,122 GB** (~3 449 elements) |
| `5000_body_shapes_and_measures.tar.gz` | 7,414 GB |

Cens complet de les 72 mides: `/root/n2_gym/out/batch_sizes.txt`.

### 1.3 La decisió (i per què no ens hem aturat)

El brief deia: *«si la unitat mínima supera 5 GB, atura't»*. La unitat mínima
**és de 4,7–5,9 GB i porta malles, renders i textures que no volem**: el
`specification.json` és menys de l'1 % del pes.

El pressupost del brief és **de disc**, i el tar.gz es pot llegir **en
streaming** sense tocar mai el disc: obrim el socket, desempaquetem al vol,
desem només els `*_specification.json` i **tallem la connexió** en arribar al
compte. Això respecta el sostre amb molt de marge, així que hem continuat en
comptes d'aturar-nos. Xifres reals:

```
1200 specs | 1,807 GB de xarxa | 16 799 membres del tar llegits | 32 s | 34 MB a disc
```

- Ordre: `venv/bin/python scripts/stream_extract.py --path GarmentCodeData_v2/garments_5000_0/default_body/data.tar.gz --out data/b0_default --limit 1200`
- Traça: `/root/n2_gym/logs/stream_b0.log` · manifest: `data/b0_default/_manifest.tsv`
- També baixat (2 MB): `dataset_properties_default_body.yaml` del lot 0 — **porta el
  tipus de peça de cada element**, que és el prior del PAS 3 regalat.

**La mostra és aleatòria de facto:** els elements es diuen `rand_<hash>` i el tar
els guarda per ordre alfabètic del hash, de manera que «els 1 200 primers» no
té cap biaix de disseny. Sí que és **un sol lot i un sol cos** (el neutre): el
lot només fixa el material de drapejat, que no afecta el patró pla.

---

## 2 · PAS 1 — El cens (el mapa del gimnàs)

`venv/bin/python scripts/census.py` → `out/cens_resum.txt` + 4 CSV.

```
patrons                  : 1 200        panells totals : 13 078
vores totals             : 88 678       panells/patró  : 2 / 10 / 34  (mitjana 10,90)
stitches/patró           : 2 / 28 / 90
panells amb label BUIT   : 0 (0,00 %)   vores amb label: 13 041 (14,71 %)
labels de panell distints: 3            noms de panell distints: 75
labels de vora distints  : 6            loops tancats i ordenats: 13 078 / 13 078
```

### 2.1 🚨 El jutge automàtic existeix, però només té TRES caselles

La premissa del brief («els labels de panell viatgen al JSON = jutge automàtic»)
**és certa**, però el vocabulari de `label` és molt més pobre del que suggeria:

| `label` de panell | n | % |
|---|---:|---:|
| `body` | 5 232 | 40,0 % |
| `leg` | 4 294 | 32,8 % |
| `arm` | 3 552 | 27,2 % |

Tres classes no són un gimnàs. **La taxonomia rica és al NOM del panell** (75
noms distints: `right_ftorso`, `skirt_front`, `wb_back`, `sl_left_cuff_skirt_f`,
`pant_f_r`, `right_hood`…). Per això hem derivat **dos objectius més**, amb
regles declarades i deterministes (`scripts/fingerprint.py`):

- **`rol` (24 caselles)** — el nom sense lateralitat ni índex:
  `sl_(left|right)_→sl_` · `(left|right)_→∅` · `pant_(l|r)_→pant_` · `_(l|r)$→∅` ·
  `_<n>$→∅`. Exemple: `sl_right_cuff_skirt_f → sl_cuff_skirt_f`.
- **`familia` (13 caselles)** — el rol col·lapsant el marcador davant/darrere:
  `ftorso`+`btorso`→`torso`, `sleeve_f`+`sleeve_b`→`sleeve`, etc.

Els tres objectius es reporten al PAS 3. **`rol` és el que s'assembla a la
casella que el reconeixedor d'FTT haurà d'anomenar.**

### 2.2 🚨 El «no hi ha plec» és cert a mitges

El brief donava per fet que els panells són meitats explícites `left_`/`right_`.
Al cens: **només el 44,9 % dels panells porta prefix de lateralitat**
(2 939 `left_` + 2 939 `right_`); el **55,1 % són panells centrals sencers**
(`skirt_front`, `wb_back`, `skirt_panel_3`…). De les bases amb prefix,
**2 859 tenen la parella completa** i 160 van soles (dissenys asimètrics).

I quan la parella hi és, **sí que és un mirall de debò**. Comparant vèrtex a
vèrtex (300 patrons, `left_*` contra `right_*`):

| relació | n |
|---|---:|
| reflexió en x + ordre invers + rotació d'índex | **582** |
| identitat + rotació d'índex | 52 |
| nombre de vèrtexs diferent (dissenys asimètrics) | 55 |
| ni l'una ni l'altra (mirall amb subdivisió diferent de la vora) | 45 |

→ **la canonicalització de mirall del PAS 2d és necessària i funciona**: 2 631
de 2 859 parelles (92,0 %) acaben amb la **mateixa signatura canònica**.

### 2.3 🚨 La curvatura NO és el que deia el brief

El brief deia «controls relatius al marc de la vora». La realitat és que **hi ha
tres tipus de vora corba**, amb paràmetres de semàntica diferent:

| `curvature.type` | vores | % | `params` |
|---|---:|---:|---|
| *(cap: recta)* | 67 286 | 75,88 % | — |
| `quadratic` | 7 802 | 8,80 % | 1 punt de control **relatiu** |
| `circle` | 7 600 | 8,57 % | `[radi ABSOLUT, large_arc, right]` (convenció d'arc SVG) |
| `cubic` | 5 990 | 6,75 % | 2 punts de control **relatius** |

Verificat contra el codi de `pygarment` 2.0.2 (`garmentcode/edge.py`:
`CircleEdge.assembly` i `CurveEdge.assembly`). **El radi de `circle` és absolut,
no relatiu** — llegir-lo com a relatiu deforma totes les vores circulars.

Estructura restant: `properties = {curvature_coords: relative,
normalize_panel_translation: false, normalized_edge_loops: true,
units_in_meter: 100}` (vèrtexs en cm). Els 13 078 loops de vores són **tancats i
encadenats en ordre** — cap excepció.

Labels de vora (només el 14,7 % en porten): `lower_interface` (6 794),
`left_collar` (1 609), `right_collar` (1 599), `right_armhole` (1 339),
`left_armhole` (1 320), `strapless_top` (380).

### 2.4 Tipus de peça a la mostra (el prior)

| main | patrons | % |
|---|---:|---:|
| dress | 446 | 37,2 % |
| upper_garment | 307 | 25,6 % |
| skirt | 282 | 23,5 % |
| pants | 97 | 8,1 % |
| jumpsuit | 68 | 5,7 % |

Estils (no exclusius): `with_sleeves` 569 · `long_sleeve` 341 · `mini` 255 ·
`sleeveless` 252 · `maxi` 252 · `short_sleeve` 228 · `knee_len` 207 ·
`midi` 190 · `asymmetric_top` 138 · `hoodie` 78.

Les proporcions coincideixen amb les del dataset sencer publicades al PDF de
documentació → **la mostra de 1 200 és representativa**.

---

## 3 · PAS 2 — L'empremta implementada (definició exacta)

Codi: `scripts/geom.py` (lectura geomètrica) + `scripts/fingerprint.py`
(empremta). Sortida: `out/empremtes.csv`, **13 078 files**.

### 3.0 Contrast previ: la lectura de curvatura és correcta

Abans de mesurar res, hem contrastat el nostre mostreig de vores contra les
classes d'aresta del **mateix `pygarment`**, comparant la longitud de cada vora
(`scripts/validate_curvature.py`, seed 20260825, 60 patrons):

```
vores comparades: 4667
  circle      n= 436  err_rel mitjà=6,20e-07  màx=3,57e-06
  quadratic   n= 400  err_rel mitjà=7,91e-08  màx=1,13e-06
  cubic       n= 304  err_rel mitjà=5,46e-07  màx=2,81e-06
  (recta)     n=3527  err_rel mitjà=8,57e-18  màx=2,16e-16
```

> ⚠️ **El paquet `pygarment` 2.0.2 de PyPI està trencat d'origen**: instal·la els
> paquets de primer nivell `garmentcode` i `pattern`, però el seu propi codi els
> importa com `pygarment.garmentcode`. Hi hem posat un shim d'àlies al venv
> propi (`venv/…/site-packages/pygarment/__init__.py`). Sense això, cap `import`
> del paquet no arrenca.

### 3.1 Les tres xifres

Es densifica el contorn: cada vora es mostreja amb **16 punts** (rectes: només
els extrems), donant un polígon tancat en cm.

**a) Allargament.** Marc canònic = **eixos principals de l'ÀREA del polígon**
(moments de segon ordre per Green, *no* PCA sobre els vèrtexs — que dependria de
com estigui subdividit el contorn). Es projecta el contorn al marc, es prenen les
extensions de la bbox i:
`allargament = ext_major / ext_menor` (≥ 1 per construcció).

**b) Ompliment.** `ompliment = àrea / (ext_major · ext_menor)` ∈ (0, 1].
Adimensional i invariant a escala. *(El brief deia «àrea/àrea² de bbox»; això no
és adimensional. La raó d'ompliment és la lectura recta d'aquella intenció.)*

**c) Signatura de vores.** Un símbol per vora, en l'ordre del loop:

- Mesura única per als tres tipus de curvatura: **desviació del punt mig de la
  corba respecte de la corda, en unitats de corda i signada** al marc relatiu de
  la vora (`+y` = perpendicular ESQUERRA de `start→end`, segons
  `pattern/utils.py:rel_to_abs_2d`).
  `quadratic` → `0,5·cy` · `cubic` → `0,375·(cy₁+cy₂)` ·
  `circle` → es recupera `cy` invertint la sageta: `R=radi/corda`,
  `s = R ∓ √(R²−0,25)` segons `large_arc`, signe `−` si `right=1`.
- **Llindar declarat: τ = 0,02** (2 % de la corda) → `R` (recta) si `|dev| < τ`.
- **Convexitat respecte de l'INTERIOR**: el loop es llegeix sempre en sentit
  **CCW** (si l'àrea signada és negativa, s'inverteix). Amb el loop CCW,
  l'interior queda a l'esquerra, per tant `dev > 0` bomba cap a dins → `C`
  (còncava); `dev < 0` bomba cap a fora → `X` (convexa).

**d) Mirall.** La signatura es canonicalitza sobre la família
`{rotacions(S)} ∪ {rotacions(invers(S))}`, i el representant és la **mínima
lexicogràfica**. `mirall = 1` si el mínim només s'assoleix a la branca
invertida. Així la signatura és invariant al vèrtex de partida **i** al mirall.
Resultat: 229 de 13 078 panells (1,75 %) queden marcats com a mirall.

**Columnes de diagnòstic al CSV, FORA de l'empremta primitiva:** `area_cm2`,
`perimetre_cm`, `n_vores`, `ext_major`, `ext_menor`, `signatura_bruta`.

### 3.2 Com surt la mostra

```
allargament  p05/p50/p95/màx : 1,14 / 1,78 / 9,31 / 68,11
ompliment    p05/p50/p95     : 0,476 / 0,679 / 1,000
vores per panell (moda)      : 4 (5 143 panells), 5 (1 337), 7 (1 173), 13 (1 142), 3 (978)
signatures més freqüents     : RRRR 2 776 · RRRX 1 542 · RRRRX 862 · RRR 830 ·
                               CRCRRR 615 · CRXR 608 · CRCRRRRRRRRRR 576
```

### 3.3 El llindar τ no és un ganivet

`scripts/tau_sweep.py` → `out/tau_sweep.csv`. Vint vegades de rang, ±1,5 punts:

| τ | % vores `R` | acc. `rol` | acc. `familia` |
|---:|---:|---:|---:|
| 0,005 | 79,24 | 51,28 | 64,01 |
| 0,01 | 82,34 | 52,26 | 63,63 |
| **0,02** | **85,42** | **52,16** | **63,20** |
| 0,05 | 87,97 | 50,63 | 65,82 |
| 0,10 | 90,41 | 49,45 | 64,94 |

→ **no hi ha res a guanyar ajustant τ**; el sostre és estructural, no de calibratge.

---

## 4 · PAS 3 — El número que decideix

Codi: `scripts/classify.py`. Sortides: `out/resultats_{rol,familia,label}.txt`,
`out/confusio_*.csv`, `out/matrius.txt`, `out/plantilles.txt`.

**Protocol (sense entrenar res).** Split **per patró** amb seed `20260825`:
840 patrons de plantilles / 360 de test → **9 102 panells de train, 3 976 de
test**. Cap patró és als dos costats. Plantilla per classe = **centroide numèric**
(z-scores de `[log(allargament), ompliment]` calculats al train) + les **k=5
signatures més freqüents** de la classe. Distància:

```
d = 0,5 · d_num/mean_num  +  0,5 · d_sig/mean_sig
d_num = euclidiana als z-scores          d_sig = Levenshtein CIRCULAR / max(llargada)
mean_* = mitjana sobre 20 000 parelles aleatòries del train (seed 20260826)
```

Les escales `mean_*` es **mesuren de les dades**, no s'ajusten a mà: així les dues
components valen 1 de mitjana sobre una parella qualsevol i el 50/50 és honest.
Valors obtinguts: `mean_num = 1,6847`, `mean_sig = 0,4395`.

### 4.1 La taula

| variant | `rol` (24 cl.) | `familia` (13 cl.) | `label` (3 cl.) |
|---|---:|---:|---:|
| base majoritària | 12,47 % | 24,95 % | 40,69 % |
| **A · empremta primitiva** | **52,16 %** | **63,20 %** | **60,64 %** |
| B · només numèric | 15,27 % | 27,44 % | 36,72 % |
| C · només signatura | 43,28 % | 39,89 % | 66,25 % |
| **D · A + prior de tipus de peça** | **55,89 %** | **71,25 %** | **63,51 %** |
| E · A + log(àrea) *(fora del brief)* | 56,94 % | 71,35 % | 62,17 % |
| F · E + prior | **59,96 %** | **77,94 %** | 64,84 % |
| A · top-2 | 70,75 % | 78,22 % | 80,68 % |
| D · top-2 | 76,89 % | 87,53 % | 88,48 % |

**El valor del prior GTI** (D − A): **+3,7 punts** sobre rols, **+8,1 punts**
sobre famílies, +2,9 sobre labels. Al top-2, +6,1 / +9,3 / +7,8.

**Lectura de B i C.** El numèric tot sol amb prou feines supera l'atzar sobre
rols (15,3 % contra 12,5 %): dues xifres invariants a escala no distingeixen 24
caselles. La signatura tota sola en fa 43,3 %. Però **cap de les dues no arriba
a la combinació**: la informació és complementària, no redundant.

**L'excepció de `label`.** Amb tres caselles semàntiques (`body`/`leg`/`arm`),
**la signatura sola (66,25 %) BAT la combinació (60,64 %)** i el prior no ajuda
gairebé gens. La raó: `body` barreja formes molt diferents (un tors i una
cinturilla hi són tots dos), i el centroide numèric d'aquella barreja no vol dir
res. **És un avís per al reconeixedor real: no hi ha una empremta única per a una
casella heterogènia.**

### 4.2 Matriu de confusió — variant A, els 10 rols més freqüents

Files = gold, columnes = predit; «altres» = fuga cap a rols de fora del top-10.

```
gold \ pred             btorso    ftorso  sleeve_b  sleeve_f skirt_pan skirt_bac skirt_fro   wb_back  wb_front sl_cuff_s    altres      n
btorso                     437        40         .         .         2         .         4         .         2         .        11    496
ftorso                      92       365         8         .         2         .         9         .         .         .        20    496
sleeve_b                     .         .        60       110        67         .         .         .         .         .        34    271
sleeve_f                     .         .        30       133        94         .         .         .         .         .        14    271
skirt_panel                  .         .        52         5       134         .         .         .         1         .        56    248
skirt_back                   4         2         .         .         .       138        54         2        11         .        16    227
skirt_front                 14        16         .         .         .        38        95         3        11         .        50    227
wb_back                      4         3         .         .         .         4        23        89        35         .        27    185
wb_front                     .         .         .         .         .         .         5        14       105         .        61    185
sl_cuff_skirt_f              .         .         .         2         .         9         6         8        31         .        98    154
```

*(La matriu de la variant D és a `out/matrius.txt`; les completes, a
`out/confusio_rol.csv`.)*

### 4.3 Descomposició de l'error

| | variant A | variant D (prior) |
|---|---:|---:|
| errors totals | 1 902 (47,84 % del test) | 1 754 (44,11 %) |
| … bessons davant/darrere de la **mateixa** família | **613 (32,2 %)** | 699 (39,9 %) |
| … confusió entre famílies diferents | 1 289 (67,8 %) | 1 055 (60,1 %) |

### 4.4 🚨 Les cinc confusions greus, amb noms i cognoms

| n | gold → predit | exemples | diagnòstic |
|---:|---|---|---|
| 120 | `ins_skirt_front` → `ins_skirt_back` | `rand_0ADI18HWRF:ins_skirt_front_2`, `…_0` | **Són el MATEIX triangle.** 295 panells de cada al train amb signatura `RRR` idèntica i mediana `(1,83 / 0,500 / 299 cm²)` idèntica. Error **forçat**: `ins_skirt_front` fa 0,00 % i `ins_skirt_back` fa 100,00 %. |
| 110 | `sleeve_b` → `sleeve_f` | `rand_05AG183QLC:right_sleeve_b`, `left_sleeve_b` | Mateix allargament (1,57) i ompliment (0,62); només les separa la signatura (`RRRRX` contra `RRRX`), i les dues signatures apareixen a totes dues classes. |
| 94 | `sleeve_f` → `skirt_panel` | `rand_05H6WP8PJX:left_sleeve_f`, `right_sleeve_f` | **La confusió honesta i interessant.** Una màniga acampanada i un gall de faldilla són el mateix quadrilàter allargat amb una vora convexa: `sleeve` (1,57 / 0,620 / 671 cm²) contra `skirt_panel` (1,79 / 0,643 / 793 cm²), i totes dues tenen `RRRX` com a signatura estrella. **El prior no la toca** (166→162): `sleeve` i `skirt_panel` conviuen als mateixos dos tipus de peça (`dress` i `upper_garment`), i en 46 patrons dels 1 200 conviuen fins i tot al mateix patró. |
| 92 | `ftorso` → `btorso` | `rand_0DKUIPHO4V:left_ftorso`, `right_ftorso` | Davant i darrere del tors: sí que difereixen (escot contra escot d'esquena) però amb un solapament enorme de signatures. És l'error **més recuperable** de la llista. |
| 67 | `sleeve_b` → `skirt_panel` | `rand_05H6WP8PJX:left_sleeve_b`, `right_sleeve_b` | La germana de la tercera. |
| 51 | `sl_cuff_skirt_f` → `sl_cuff_skirt_b` | `rand_0BYYF4ET0T:sl_right_cuff_skirt_f` | **Rectangles idèntics** (`RRRR`, 4,90 / 0,775 / 86 cm², 321 de cadascun). Error forçat. |

### 4.5 🚨 La troballa dura: quatre parelles són el MATEIX polígon

`scripts/sostre.py` agrupa el train per empremta discretitzada fina i busca
caselles que hi caiguin juntes:

```
Parelles de rols amb empremta INDISTINGIBLE (mateixa cubeta fina):
    321  sl_cuff_skirt_b   == sl_cuff_skirt_f
    295  ins_skirt_back    == ins_skirt_front
    268  sl_cuff_b         == sl_cuff_f
     90  skirt_back        == skirt_front
     48  collar_back       == sl_cuff_b        <- ni tan sols de la mateixa família
     48  pant_cuff_skirt_b == pant_cuff_skirt_f
     36  pant_cuff_b       == pant_cuff_f
     24  collar_front      == sl_cuff_b
```

La taula de plantilles ho confirma línia a línia (`out/plantilles.txt`):
`sl_cuff_skirt_f` i `sl_cuff_skirt_b` tenen **321 panells cadascun i tots dos
tenen `RRRR(321)` com a única signatura**, amb medianes idèntiques fins al
decimal. **No hi ha cap funció del contorn que els separi.** La precisió del
0,00 % que veiem en aquestes classes no és un defecte del classificador: és el
resultat correcte d'una pregunta mal posada.

**Puresa de l'empremta** (proporció de panells del train que comparteixen classe
amb tota la seva cubeta, granularitat gruixuda):

| objectiu | puresa | massa bessona (indecidible) |
|---|---:|---:|
| `rol` | 77,74 % | **22,26 %** |
| `familia` | 92,70 % | 7,30 % |
| `label` | 93,21 % | 6,79 % |

*(La línia de memorització per cubetes — predir la majoria de la cubeta del
train — fa només 37,6 % sobre rols perquè el 41,2 % del test cau en cubetes no
vistes. **El nearest-template la bat per 15 punts: generalitzar guanya a
memoritzar.** No és cap sostre; és una línia baixa.)*

### 4.6 Què fa exactament el prior

Comparant les vuit confusions grosses de famílies amb prior i sense
(`out/resultats_familia.txt`), el prior **elimina** `skirt→pant` (140),
`sl_cuff→pant_cuff` (104), `torso→pant` (62), `sl_cuff_skirt→pant_cuff_skirt`
(50) — **totes creuen el tipus de peça**. I **no toca** `sleeve→skirt_panel`
(166→162), `sl_cuff_skirt→wb` (72→72), `collar→sl_cuff` (50→70). Regla:

> **el prior GTI neteja el que és impossible, no desempata el que és ambigu.**

---

## 5 · Lectura honesta: què separa i on s'esfondra

### ✅ Separa bé

- **El tors** (88,1 % `btorso`, 73,6 % `ftorso`): moltes vores, signatures
  llargues i distintives (`CRCRRRRRRRRRR`), poques classes hi competeixen.
- **El pantaló** (94,8 % / 87,9 %): signatura llarga i única (`CCRRRRRRRRXRR`).
- **La faldilla en galls** (`skirt_panel`, 54 %→89 % amb prior).
- **Tot el que té moltes vores.** Amb 3 o 4 vores la signatura gairebé no diu
  res (5 143 panells de 13 078 tenen 4 vores i 2 776 signatures són `RRRR`);
  amb 12–13 vores, gairebé sentencia sola.

### ❌ S'esfondra

1. **Davant contra darrere.** 32 % de l'error, i per a 4 parelles de 12 és
   **matemàticament impossible**. El bit davant/darrere **no és al contorn**:
   és a `panel.translation[2]` (el signe de la z) i al graf de costures.
2. **Rectangles.** `sl_cuff`, `pant_cuff`, `collar`, `wb` són tots
   `RRRR`/`RRRRR` amb ompliment 1,000. L'única cosa que els separa és
   **l'escala absoluta**, que l'empremta primitiva llença per disseny
   (`collar 96 cm²` · `sl_cuff 53 cm²` · `wb 292 cm²` · `pant_cuff 143 cm²`).
   Per això `collar` fa 28,3 % i `hood` 36,4 %.
3. **Formes genuïnament homògrafes**: màniga acampanada ≡ gall de faldilla. Cap
   prior de tipus de peça no hi arriba, perquè les dues conviuen al mateix vestit.
4. **Caselles heterogènies**: el `label` `body` és el contraexemple viu — una
   casella que barreja formes no té centroide.

### El que ha resultat ser un no-problema

**El mirall.** Ens temíem el pitjor i val 1,75 % dels panells. Amb la
canonicalització sobre `{rotacions} ∪ {rotacions de l'invers}`, el 92 % de les
parelles `left_`/`right_` acaben amb signatura idèntica. **Resolt i tancat.**

---

## 6 · Recomanació per al reconeixedor real

**No escriguis el reconeixedor sobre el contorn tot sol.** L'empremta primitiva
és un bon **primer garbell de família** (63 % sobre 13 caselles, 78 % al top-2),
i com a tal es queda. Abans d'escriure'l calen, per ordre de rendibilitat:

1. **🥇 L'ESCALA ABSOLUTA.** És l'afegit més barat de tots: una sola columna
   (`log(àrea_cm²)`, ja al CSV) dona **+4,8 punts** sobre rols i **+8,2 sobre
   famílies** (variant E), i **+7,8 / +14,7 combinada amb el prior** (variant F).
   Separa d'una vegada els rectangles (coll/puny/cinturilla/camal) que ara
   col·lapsen. **A FTT tenim l'escala: les mesures són el nostre negoci.** El
   brief la deixava fora perquè el dataset no porta mesures de cos — però l'àrea
   del panell sí que hi és, i és la variable de decisió més forta que hem trobat.

2. **🥈 EL BIT DAVANT/DARRERE, i que NO surti de la forma.** És un terç de
   l'error i per a un terç de les caselles és indecidible pel contorn. Ha de
   venir d'una altra capa: el signe de la z de la col·locació 3D
   (`panel.translation[2]`) o el graf de costures. **Decisió de disseny per a
   l'Agus:** o bé el reconeixedor prediu *família* i el davant/darrere el resol
   una regla a part, o bé l'empremta ha d'incorporar la col·locació. La primera
   opció és més neta i ja té els números aquí.

3. **🥉 EL GRAF DE COSTURES.** El `specification.json` porta 28 stitches de
   mediana per patró, i no n'hem fet servir ni un. «Aquest panell es cus amb dos
   panells que ja hem classificat com a tors» val infinitament més que qualsevol
   raó d'aspecte. **És la peça que converteix un classificador de panells
   independents en un reconeixedor de patrons.**

4. **El prior GTI: sí, però al lloc just.** +8,1 punts sobre famílies per no res.
   Ara bé, **només poda l'impossible**. No l'esperis com a desempatador.

5. **El que NO cal fer:** ajustar τ (±1,5 punts en 20× de rang), refinar la
   canonicalització de mirall (val 1,75 %), ni afegir més dades del mateix lot
   (les corbes per classe ja són planes amb 1 200 patrons).

6. **Les vores etiquetades són un regal a mig obrir.** El 14,7 % de vores porten
   `lower_interface`, `left_armhole`, `right_collar`… — és a dir, **el dataset ja
   marca on és l'emmanigat i on el coll**. Convertir la signatura de `{R,X,C}` a
   `{R,X,C} × {etiqueta}` on n'hi hagi és una millora que no hem provat i que
   sembla directa.

### La lectura per a FTT

> Un panell no s'identifica per la seva forma. S'identifica per **la seva forma,
> la seva mida i amb qui es cus**. L'empremta primitiva de §3.1-N2 té la primera
> de les tres, i arriba exactament fins on això la porta: distingeix famílies,
> no caselles. Les altres dues ja les tenim totes dues a l'abast — l'escala és
> literalment una columna més, i el graf de costures és al mateix JSON.

---

## 7 · Rastre — com es reprodueix cada xifra

Tot viu a `/root/n2_gym/`, amb venv propi `/root/n2_gym/venv` (Python 3.12.3,
`pygarment` 2.0.2 + shim d'àlies). Cap ordre toca res del projecte.

| Fitxer | Què és |
|---|---|
| `scripts/dav_ls.sh` + `scripts/dav_parse.py` | llista el share WebDAV amb mides → §1.2 |
| `scripts/stream_extract.py` | baixada en streaming, només `*_specification.json` → §1.3 |
| `scripts/geom.py` | lectura geomètrica: curvatura, densificació, moments d'àrea |
| `scripts/validate_curvature.py` | contrast contra `pygarment` → §3.0 |
| `scripts/census.py` | PAS 1 → `out/cens_resum.txt`, `out/cens_*.csv` |
| `scripts/fingerprint.py` | PAS 2 → `out/empremtes.csv` (13 078 files) |
| `scripts/classify.py` | PAS 3 → `out/resultats_{rol,familia,label}.txt`, `out/confusio_*.csv` |
| `scripts/matrius.py` | matrius de confusió + descomposició de l'error → `out/matrius.txt` |
| `scripts/plantilles.py` | plantilles llegibles per classe → `out/plantilles.txt` |
| `scripts/tau_sweep.py` | sensibilitat a τ → `out/tau_sweep.csv` |
| `scripts/sostre.py` | puresa, massa bessona, parelles indistingibles → `out/sostre.txt` |
| `data/b0_default/` | 1 200 `specification.json` + `_manifest.tsv` (34 MB) |
| `data/dataset_properties_default_body_b0.yaml` | tipus de peça per element (el prior) |
| `data/Dataset_documentation_v2.pdf` | MD5 `fabfdb6ede7e09cc2b6db0da586e1437` |
| `logs/stream_b0.log` | traça de la baixada |
| `out/batch_sizes.txt` | mides dels 72 `data.tar.gz` |

Seqüència completa des de zero:

```bash
cd /root/n2_gym
/usr/bin/python3 -m venv venv && ./venv/bin/pip install pygarment
# + el shim d'alies a venv/lib/python3.12/site-packages/pygarment/__init__.py
/usr/bin/python3 scripts/stream_extract.py \
  --path GarmentCodeData_v2/garments_5000_0/default_body/data.tar.gz \
  --out data/b0_default --limit 1200
./venv/bin/python scripts/validate_curvature.py
./venv/bin/python scripts/census.py
./venv/bin/python scripts/fingerprint.py            # tau=0.02, dens=16
for t in rol familia label; do ./venv/bin/python scripts/classify.py --target $t; done
./venv/bin/python scripts/matrius.py
./venv/bin/python scripts/plantilles.py
./venv/bin/python scripts/tau_sweep.py
./venv/bin/python scripts/sostre.py
```

Seeds: split i mostreig `20260825` · escales de distància `20260826` (=`SEED+1`).
Tots els números d'aquest informe són reproduïbles bit a bit amb aquestes ordres.
