# QA-TALLER-D — La convenció de recorregut de vora

**Data:** 2026-08-25 · **Fil:** S46-MOTOR · Patró A
**Per a:** prerequisit 0 del solver v2 (`DISSENY_MOTOR_PARAMETRIC_V2` §5)
**Naturalesa:** DIAGNOSI (cens). La convenció es **ratifica després**, per Patró C.

> **Fronteres respectades.** Read-only absolut al repo. Cap `systemctl`, cap migració,
> cap escriptura a cap BD, **cap test executat**. Les mesures d'aquest informe són
> lectures de fitxers DXF/RUL del `media` i importacions en memòria del motor (que és
> Python pur: `engine/` no importa Django) — cap d'elles escriu res.
> **Aquest fitxer és l'única escriptura.**
>
> Fitxers modificats per la sessió paral·lela (ignorats, cap és del motor):
> `DECISIONS.md` · `docs/ordres/IMPLEMENTACIO_SOBIRANIA_POM_2026-08-22.md` ·
> `ops/maquetes/REPORT_CODA_BLOC_B.md` · `ops/qa/qa_f22_vocabulari_captures.py`.

---

## 0 · El veredicte en set línies

1. **No hi ha cap convenció, ni escrita ni imposada.** El motor pren el recorregut
   **tal com ve del DXF** i no el normalitza mai: no hi ha ni una sola línia
   d'orientació a tot `patterns/` ([Q1](#1--q1--extracció-dxf)).
2. **I el material real NO és homogeni.** De 91 vores tancades de 8 fitxers reals:
   **61 CCW i 30 CW**. Els 7 fitxers de PolyPattern són tots CCW; el **CALLIE**
   (l'únic sense `Author:`) és **CW de dalt a baix, 30 de 30**. L'orientació és una
   propietat del **CAD d'origen**.
3. 🚨 **Ja hi ha un defecte viu que en depèn.** `unfold_piece` desplega bé **7 de 13**
   peces amb doblec i **malament les altres 6**: en surten contorns que es creuen a
   ells mateixos. El criteri que les separa és **exactament** on el CAD va obrir la
   polilínia ([Q5](#5--q5--multi-peça-i-mirall)). No és un risc futur: és a `media` avui.
4. **La fracció ja és la moneda del sistema**, i ja hi ha **tres** models que la
   guarden. Un d'ells, `SegmentPreference`, **la transporta ENTRE FITXERS** sense cap
   ancoratge geomètric ([Q2](#2--q2--model-de-dades), [Q4](#4--q4--discrepàncies)).
5. **Els consumidors NO comparteixen assumpció**, però la discrepància no és on
   semblava: el motor de cotes i el matcher de costures són **immunes** al sentit; qui
   hi és sensible és **el desplegat, el verificador de round-trip i la preferència apresa**.
6. 🚨 **El matcher ja SAP el sentit relatiu de cada costura i el LLENÇA.** `Proposta.invertit`
   arriba al JSON de la proposta i **no hi ha cap camp on desar-lo** a `SewRelation`.
   És precisament el bit que el solver v2 necessitarà ([Q3a](#3a--seam_matchingpy), [Q4](#4--q4--discrepàncies)).
7. La premissa del brief sobre el RUL **no es compleix**: la clau d'emparellament del RUL
   és el **número de regla**, lligat al punt **per coordenada**, no per posició al bucle.
   El writer és immune al recorregut ([Q3c](#3c--el-writer-dxfrul)).

---

## 1 · Q1 — Extracció DXF

### 1.1 L'ordre és el NATIU, i no es toca

[`engine/aama_reader.py:334`](../../backend/fhort/patterns/engine/aama_reader.py#L334) —
els punts surten de la iteració de la polilínia d'`ezdxf`, en l'ordre en què el fitxer
els porta:

```python
pts_natius = [(v.dxf.location.x, v.dxf.location.y) for v in pl.vertices]
```

Entre aquesta línia i
[`:361`](../../backend/fhort/patterns/engine/aama_reader.py#L361), on la vora s'afegeix
al model, **l'única mutació és treure el vèrtex de tancament duplicat**
([`:345-347`](../../backend/fhort/patterns/engine/aama_reader.py#L345)):

```python
closed = _same_point(pts_natius[0], pts_natius[-1])
if closed:
    pts_natius = pts_natius[:-1]
```

**No hi ha cap `sort`, cap `reversed`, cap rotació i cap càlcul d'àrea signada.** El
`boundary_index` és l'ordre d'aparició de les polilínies dins del BLOCK, i l'`ordre` de
cada punt és la seva posició nativa
([`adapters.py:267-268`](../../backend/fhort/patterns/adapters.py#L267)):

```python
for i, boundary in enumerate(piece.boundaries):
    for ordre, p in enumerate(boundary.points):
```

### 1.2 Cens d'orientació sobre material real (shoelace)

L'àrea signada només està **definida en vores TANCADES**; en una vora oberta el signe és
soroll (el MEREDITH en dona una de −0,1 mm² sobre 321 punts, que no vol dir res). El cens
es fa, doncs, **només sobre tancades**:

| fitxer | CCW | CW | veredicte |
|---|---:|---:|---|
| `837_CORS_194_VESTIT_M3-4_AGUS.DXF` | 10 | 0 | tot CCW |
| `837__VESTIT_M3-4_s_cost.DXF` | 5 | 0 | tot CCW |
| `837__VESTIT_s_opcio_cost.DXF` | 5 | 0 | tot CCW |
| `TATE.DXF` | 18 | 0 | tot CCW |
| `AMELIA_AZUL_prova.dxf` | 4 | 0 | tot CCW |
| `MEREDITH_-_Retoque.DXF` | 15 | 0 | tot CCW |
| `niada.dxf` | 4 | 0 | tot CCW |
| **`CALLIE-…-08-07-2026.dxf`** | **0** | **30** | 🚨 **tot CW** |
| **TOTAL** | **61** | **30** | **67,0 % CCW** |

El **837**, que és el que el brief demanava mesurar, dona **10 de 10 CCW** (les 5 peces ×
capes TALL i COSIT): `CUELLO` +19 791 · `DELANTERO` +565 653 · `ESPALDA` +580 947 ·
`MANGA` +121 130 · `TAPETA` +13 641 mm².

### 1.3 🚨 L'orientació és una propietat del CAD D'ORIGEN

La correlació és perfecta:

| fitxer | primer TEXT de capçalera | orientació |
|---|---|---|
| 837, TATE, AMELIA, MEREDITH, niada | `Author: PolyPattern` | **CCW** |
| CALLIE | `Style Name: …` (**cap `Author:`**) | **CW** |

FTT ja té el detector de proveïdor
([`aama_reader.py:808-817`](../../backend/fhort/patterns/engine/aama_reader.py#L808),
`_guess_source_cad`), i **per al CALLIE retorna cadena buida**: el CAD que trenca la
regla és, a més, el que el motor no sap anomenar.

> **Conseqüència directa:** «confiar que el CAD ja ve CCW» **no és una opció**. La
> normalització s'ha de fer, i s'ha de fer a la porta d'entrada.

---

## 2 · Q2 — Model de dades

### 2.1 Com es persisteix

| taula | camp | què fixa |
|---|---|---|
| `PatternPiece` | [`contorns`](../../backend/fhort/patterns/models.py#L163) (JSON) | **només metadades** `[{index, role, layer, closed}]` — cap coordenada |
| `PatternPoint` | [`boundary_index`](../../backend/fhort/patterns/models.py#L289) + [`ordre`](../../backend/fhort/patterns/models.py#L290) | **ÉS el recorregut**: `ordre` = índex natiu del DXF |
| `PatternSegment` | [`vora`](../../backend/fhort/patterns/models.py#L351) + [`t_inici`/`t_fi`](../../backend/fhort/patterns/models.py#L356) | un tram en **fracció de longitud d'arc** |

L'ordenació canònica de lectura és
[`models.py:305`](../../backend/fhort/patterns/models.py#L305):
`['piece', 'mena', 'boundary_index', 'ordre', 'id']`.

### 2.2 ¿Hi ha noció d'ORIGEN o de SENTIT? — Sí, implícita, i ja és portant

**No hi ha cap camp** que digui «aquesta vora va en aquest sentit» ni «el bucle obre
aquí». Però la convenció **hi és, escrita a l'aritmètica**:

- **Origen** = el punt d'`ordre = 0`. `acumulats_vora`
  ([`segments.py:67-82`](../../backend/fhort/patterns/engine/segments.py#L67)) construeix
  la taula `t(i) = cum[i]/total` **des del primer vèrtex**.
- **Sentit** = el d'`ordre` creixent. `t` creix amb l'índex, sempre.
- **Tancament** = **implícit**. El vèrtex duplicat es treu en llegir
  ([`:345-347`](../../backend/fhort/patterns/engine/aama_reader.py#L345)) i es torna a
  posar en escriure
  ([`aama_writer.py:194`](../../backend/fhort/patterns/engine/aama_writer.py#L194)). A la
  BD, l'aresta de tancament **existeix però no té fila**: `acumulats_vora` li suma la
  longitud al total només si `closed`.

> 🔑 **L'origen ja és una decisió de disseny, no un detall.** El docstring de
> [`fraccio_tram`](../../backend/fhort/patterns/engine/segments.py#L84) ho diu:
> **`t_fi < t_inici` vol dir que el tram passa per l'origen de la vora.** Un tram no és
> un interval; és un **recorregut orientat** que pot donar la volta. Sense conèixer
> l'origen, `[0,9 → 0,1]` és indesxifrable.

### 2.3 El tram ja està direccionalment NORMALITZAT (i el gest de l'usuari s'hi perd)

[`tram_entre_punts`](../../backend/fhort/patterns/engine/segments.py#L105) tria per
defecte **l'arc CURT** i, sigui quin sigui, retorna sempre `(t_inici, t_fi)` de manera
que el tram es recorri **endavant**:
[`:167`](../../backend/fhort/patterns/engine/segments.py#L167) `fraccio_endavant = (t_b - t_a) % 1.0`,
i si guanya l'arc enrere els extrems **s'intercanvien**.

**Conseqüència:** si el patronista clica A i després B, i l'arc curt és B→A, el que es
desa és `(t_B, t_A)`. **El sentit del gest humà no es conserva**; només la geometria. Avui
no fa mal (una longitud no té signe), però el solver v2 parametritza *sobre* aquests trams.

---

## 3 · Q3 — Consumidors, un per un

### 3a · `seam_matching.py`

**Assumpció: CAP. És el mòdul més ben blindat del cens.**

`casen_piquets`
([`:408-425`](../../backend/fhort/patterns/engine/seam_matching.py#L408)) prova
**els dos sentits** i el sentit invers és literalment la **fracció mirall `1−f`**
([`:420`](../../backend/fhort/patterns/engine/seam_matching.py#L420)):

```python
invers = max(abs(x - y) for x, y in zip(sa, tuple(1.0 - v for v in reversed(sb))))
```

Les fraccions de piquet són **relatives al tram** (`piquets_del_tram`,
[`:372-405`](../../backend/fhort/patterns/engine/seam_matching.py#L372)), amb la mateixa
aritmètica modular que `fraccio_tram`, i el resultat viatja com
[`Proposta.invertit`](../../backend/fhort/patterns/engine/seam_matching.py#L289).

> 🚨 **Però el bit es perd.** `invertit` arriba al payload de la proposta
> ([`seam_proposals.py:246`](../../backend/fhort/patterns/seam_proposals.py#L246)) i
> **`SewRelation` no té cap camp on desar-lo**
> ([`models.py:637-690`](../../backend/fhort/patterns/models.py#L637): `segments_a`,
> `segments_b`, `tipus`, `nom`, `diferencial_cm`, `notes` — i prou). En acceptar la
> costura, **el sentit relatiu es llença**. És exactament el bit que el solver v2
> necessita per saber si la `t=0` d'un tram es troba amb la `t=0` o amb la `t=1` de l'altre.

### 3b · El motor de cotes

**Assumpció: CAP. No existeix cap «sentit positiu de la corba».**

| mode | com evita el sentit | on |
|---|---|---|
| `vora` | mesura **els dos camins** i es queda el curt | [`measure.py:254-272`](../../backend/fhort/patterns/engine/measure.py#L254) |
| `ortogonal` | producte vectorial i **descarta el signe explícitament** | [`:191-192`](../../backend/fhort/patterns/engine/measure.py#L191) |
| `projeccio` | `|Δ|` sobre l'eix | [`:134-161`](../../backend/fhort/patterns/engine/measure.py#L134) |
| `landmark` (offset) | 🚩 **eixos del FULL**, no de la vora | [`:239-252`](../../backend/fhort/patterns/engine/measure.py#L239) |

El comentari de `_ortogonal` és inequívoc: *«El SIGNE diria de quin costat de la línia cau
el punt; una caiguda no en té, de costat, així que es descarta»*.

> 🚩 **El mode `landmark` no deriva cap sentit de la corba: fa servir `down`/`up`/`left`/
> `right` = ±y, ±x del full.** Immune al recorregut, però **sensible al gir de la peça** —
> la contradicció que el mateix mòdul denuncia per al mode ortogonal
> ([`:36-40`](../../backend/fhort/patterns/engine/measure.py#L36)). No és objecte d'aquesta
> diagnosi, però és el mateix gènere de forat i val més que consti.

### 3c · El writer DXF+RUL

**Assumpció: preserva l'ordre. Però l'emparellament del RUL NO en depèn.**

- **DXF**: `_write_piece`
  ([`aama_writer.py:185-196`](../../backend/fhort/patterns/engine/aama_writer.py#L185))
  emet `boundary.points` **en l'ordre desat** i reposa el vèrtex de tancament.
- **RUL**: `RULWriter.write`
  ([`rul_writer.py:71`](../../backend/fhort/patterns/engine/rul_writer.py#L71)) itera
  **`sorted(table.regles)`** — per **número de regla**.
- **El lligam regla↔punt és GEOMÈTRIC**: `_rule_at`
  ([`aama_reader.py:433-461`](../../backend/fhort/patterns/engine/aama_reader.py#L433))
  casa el TEXT `# N` amb el punt **per coordenada** (`_same_point`), i
  `_write_rule_texts` el torna a escriure **a la coordenada del punt**.

> ✅ **La premissa del brief («la clau del RUL depèn de numeració → depèn del recorregut»)
> NO es compleix.** El número de regla està lligat a **on és el punt**, no a **quan surt**.
> Capgirar el recorregut no desplaça cap regla.

### 3d · El visor Konva (`PatternViewer`)

**Assumpció: la MATEIXA que el backend, i explícitament.**

[`patternGeometry.js:216-225`](../../frontend/src/components/pattern/patternGeometry.js#L216)
reimplementa `fraccio_tram` **citant el motor pel nom**, i `puntsDelSegment`
([`:265-300`](../../frontend/src/components/pattern/patternGeometry.js#L265)) recorre el
tram **en ordre de recorregut, no d'índex**, amb un comentari que explica que emetre'l per
índex «pintava una diagonal per dins de la peça».

Backend i frontend **estan alineats**. A més, el visor exposa el problema a l'usuari: com
que triar entre dos arcs és ambigu, hi ha una **tecla d'invertir**
([`arcDirigit`, `:405-412`](../../frontend/src/components/pattern/patternGeometry.js#L405)),
i la tria es conserva per arc
([`PatternViewer.jsx:379-383`](../../frontend/src/components/pattern/PatternViewer.jsx#L379)).

### 3e · L'auto-ancoratge

**No existeix cap consumidor: no està construït.**
`INFORME_CORPUS_I_AUTOANCORATGE_2026-08-24` és taxatiu: *«`PlacementProposal` **no
existeix**: ni model, ni migració, ni taula, ni un sol commit»*, i A11 conclou que sense
HPS identificats el mode ortogonal no es pot proposar.

El que SÍ hi ha, i com referencia el recorregut:

| model | com hi apunta | sensible al recorregut? |
|---|---|---|
| `PatternPOM` | [`definicio_mesura`](../../backend/fhort/patterns/models.py#L445): **ids de `PatternPoint`** | ❌ **NO** |
| `SewRelation` | M2M → `PatternSegment` ([`:660`](../../backend/fhort/patterns/models.py#L660)) | hereta del segment; **i perd el sentit** |
| `SewProposalRejection` | FK → `PatternSegment` | ❌ NO |
| `DartProposalRejection` | FK → `PatternPoint` | ❌ NO |
| `PatternSegment` | `vora` + `t_inici`/`t_fi` | ✅ **SÍ** (dins de la versió) |
| **`SegmentPreference`** | [`rol` (string) + `t_inici`/`t_fi`, **sense cap FK**](../../backend/fhort/patterns/models.py#L813) | 🚨 **SÍ, i ENTRE FITXERS** |

> 🚨 **`SegmentPreference` és el cas greu.** És, per disseny, una preferència que ha de
> **sobreviure el patró on es va aprendre** (*«si morís amb ell, no hauria après res»*) i
> aplicar-se a altres patrons que comparteixin nomenclatura de peça. S'aplica per
> **solapament de fraccions** (`preferencia_del_tram`,
> [`preferences.py:115-135`](../../backend/fhort/patterns/preferences.py#L115)) contra un
> `rol` que és **una cadena de text**, no una geometria.
>
> Una preferència apresa sobre un `FRONT` de PolyPattern (CCW, origen X) aplicada a un
> `FRONT` d'un altre CAD (CW, origen Y) **cau sobre un tros de vora completament
> diferent** — i en silenci, perquè `vegades` només compta reforços i **fa que la
> preferència sembli MÉS fiable com més vegades s'aplica malament**.

### 3f · `dart_detection.py` (no era al brief, i cal dir-ho)

**Assumpció: cap — i és l'exemple a imitar.** `apex_cap_enfora`
([`:147-160`](../../backend/fhort/patterns/engine/dart_detection.py#L147)) **mesura**
l'orientació en comptes de suposar-la:

```python
orientacio = 1.0 if _area_signada(pts) > 0 else -1.0
return (creu * orientacio) > 0
```

El docstring diu «en un contorn CCW…», però **el codi compensa** i funciona en tots dos
sentits. És l'únic lloc de tot `patterns/` on l'orientació es calcula.

---

## 4 · Q4 — Discrepàncies

### 4.1 La taula d'assumpcions

| mòdul | origen del bucle | sentit | veredicte |
|---|---|---|---|
| `aama_reader` (entrada) | el del DXF | el del DXF | **no normalitza** |
| `aama_writer` (sortida) | el desat | el desat | preserva |
| `rul_writer` | — | — | ✅ **immune** (clau = número de regla) |
| `segments` / `fraccio_tram` | `ordre = 0` | `ordre` creixent | **defineix la convenció de facto** |
| `seam_matching` | irrellevant | **prova els dos** | ✅ immune (però **llença** el resultat) |
| `measure` (`vora`/`ortogonal`/`projeccio`) | irrellevant | irrellevant | ✅ immune |
| `measure` (`landmark`) | irrellevant | **eixos del full** | 🚩 immune al recorregut, sensible al gir |
| `dart_detection` | irrellevant | **mesurat** | ✅ immune |
| `patternGeometry.js` (front) | `ordre = 0` | `ordre` creixent | ✅ **coincideix amb el backend** |
| `roundtrip._compare_piece` | **posicional** | **posicional** | 🚨 **sensible** |
| `unfold_piece` / `_mirror_points` | **exigeix l'eix al tancament** | depèn | 🚨 **sensible i ja trencat** |
| `SegmentPreference` | fracció crua | fracció crua | 🚨 **sensible ENTRE FITXERS** |

**No coincideixen totes.** Però les que xoquen no són les que el brief esperava.

### 4.2 Les parelles que xocarien, i amb quin símptoma

| # | parella | símptoma exacte | ja passa? |
|---|---|---|---|
| **D1** | `unfold_piece` ↔ l'origen que el CAD tria | **contorn desplegat que es creua a ell mateix**; l'àrea no dobla (fins a signe capgirat i àrea ≈ 0) | 🚨 **SÍ, avui, 6 peces** |
| **D2** | `SegmentPreference` ↔ un fitxer d'un altre CAD | la preferència apresa cau a **la fracció mirall `1−f`** o a un tram desplaçat; el taller pre-confirma la costura equivocada **en silenci** | latent (cal un 2n CAD amb el mateix `rol`) |
| **D3** | `seam_matching` ↔ `SewRelation` | el sentit relatiu es **calcula i es descarta**; el solver v2 no sabrà si `t=0` es troba amb `t=0` o amb `t=1` | 🚨 **SÍ** (pèrdua d'informació, no error visible) |
| **D4** | qualsevol normalització nova ↔ `roundtrip` | el comparador fa `zip(va.points, vb.points)` **per índex** ([`roundtrip.py:191`](../../backend/fhort/patterns/engine/roundtrip.py#L191)): normalitzar el sentit faria sortir **TOTS els punts com a `point_moved`** amb la geometria idèntica | futur (és el **cost de migració** de qualsevol convenció) |
| **D5** | `PatternSegment` ↔ reimportació del mateix estil | `adapters.py:183` esborra i recrea les peces; els trams es re-deriven, però **un tram DECLARAT reimportat sobre un origen diferent apunta a una altra vora** | mitigat: `PatternFile` és immutable (versió nova = fila nova) |

---

## 5 · Q5 — Multi-peça i mirall

### 5.1 El mecanisme

`unfold_piece` ([`aama_reader.py:575-610`](../../backend/fhort/patterns/engine/aama_reader.py#L575))
reflecteix la meitat sobre l'eix i concatena. `_mirror_points`
([`:650-666`](../../backend/fhort/patterns/engine/aama_reader.py#L650)):

```python
return points + tuple(reflectits)   # reflectits = [mirall(p) for p in reversed(points) if not _on_axis(p)]
```

La reflexió capgira el sentit i el `reversed()` el torna a capgirar, **de manera que en el
cas bo el sentit ES CONSERVA**. Mesurat: **11 de 13** peces amb doblec mantenen el signe.

**Ningú no ho normalitza** — no hi ha cap comprovació posterior del signe ni de la validesa
del contorn resultant.

### 5.2 🚨 Però la concatenació només és vàlida si l'eix toca el TANCAMENT

La concatenació `punts + reversed(mirall)` només tanca bé si la meitat original
**comença i acaba sobre l'eix**, és a dir si els punts de l'eix són els d'índex `0` i
`n−1`. Si el CAD va obrir la polilínia **a mig contorn**, la còpia s'empelta al lloc
equivocat i el contorn es creua.

Mesurat sobre les 13 peces amb doblec del `media` (ràtio = àrea després / àrea abans; ha
de ser **2,00**):

| fitxer | peça | n | índexs sobre l'eix | ràtio | |
|---|---|---:|---|---:|---|
| MEREDITH | `base_esqu` | 93 | `[0, 92]` | **2,00** | ✅ |
| MEREDITH | `BACK_RUFFL` | 41 | `[0, 39, 40]` | 1,96 | ✅ |
| MEREDITH | `FRONT_RUFFL` | 41 | `[0, 39, 40]` | 1,96 | ✅ |
| CALLIE | `1` | 22 | `[0, 21]` | **2,00** | ✅ |
| CALLIE | `7` | 8 | `[0, 7]` | **2,00** | ✅ |
| CALLIE | `8` | 7 | `[0, 6]` | **2,00** | ✅ |
| CALLIE | `16` | 28 | `[0, 27]` | **2,00** | ✅ |
| MEREDITH | `FRONT_&_BACK_SHOULDER_LACE` | 4 | `[0, 1]` | 1,50 | 🚨 |
| MEREDITH | `NECK_LACE` | 4 | `[0, 1]` | 1,50 | 🚨 |
| CALLIE | `3` | 6 | `[0, 1, 2]` | 1,36 | 🚨 |
| CALLIE | `11` | 10 | `[1, 2, 3, 4, 5]` | 0,93 | 🚨 |
| CALLIE | `13` | 6 | `[1, 2, 3]` | **−0,00** | 🚨 |
| CALLIE | `14` | 4 | `[1, 2]` | **−1,00** | 🚨 |

**La separació és perfecta:** les 7 correctes contenen **totes** els índexs `0` **i**
`n−1`; les 6 trencades **cap**. Cap altra variable (CAD, orientació, nombre de punts) les
separa — el MEREDITH és CCW i de PolyPattern, i també en té dues de trencades.

### 5.3 El cas `14`, sencer, perquè es vegi

Rectangle a la dreta d'un eix vertical a `x = 5210,14`:

```
ABANS (4 punts, CW)                   DESPRÉS (6 punts)
  0: (5335.21, -147.46)                 0: (5335.21, -147.46)
  1: (5210.14, -147.46)  ← EIX          1: (5210.14, -147.46)
  2: (5210.14,  272.54)  ← EIX          2: (5210.14,  272.54)
  3: (5335.12,  272.54)                 3: (5335.12,  272.54)
                                        4: (5085.16,  272.54)   ← salta l'eix
                                        5: (5085.07, -147.46)
```

El recorregut va fins a `x = 5335` (dreta) i **salta a `x = 5085`** (esquerra), creuant
tota la peça. **És un llaç en forma de vuit.** El rectangle correcte faria 250 × 420 =
105 000 mm²; el que surt en fa **|−52 511|**, exactament la meitat, perquè els dos lòbuls
es cancel·len.

> Els punts de l'eix són als índexs **1 i 2** — al mig del bucle. Amb els mateixos quatre
> punts oberts un lloc més enllà, la peça sortiria perfecta. **Aquest és el «bug de fase
> esperant data» del brief, i la data ja ha passat.**

### 5.4 CUT-2+2

**No n'hi ha cap al material.** Les peces simètriques del corpus són **de doblec**
(`has_fold`), no parells duplicats. La lateralitat explícita `left_`/`right_` que el
gimnàs N2 va veure a GarmentCodeData **no apareix a cap DXF d'FTT**. Queda com a forat
de cobertura, no com a troballa.

---

## 6 · Q6 — Proposta de convenció (per ratificar)

> **No implementar.** El que segueix és el que la diagnosi recomana que Patró C ratifiqui.

### 6.1 La proposta

| # | regla | proposta |
|---|---|---|
| **C1 · Sentit** | canònic | **CCW** (àrea signada > 0), normalitzat **en llegir** |
| **C2 · Origen** | quin vèrtex obre el bucle | **el de menor `(y, x)` lexicogràfic** |
| **C3 · Fracció** | norma | `t = 0` a l'origen del **tram**, creix en sentit canònic; `t_fi < t_inici` = travessa l'origen de la **vora** (ja vigent) |
| **C4 · Mirall** | tractament | **el sentit es normalitza en carregar**; la fracció **es conserva** |
| **C5 · Tancament** | explicitud | **implícit, com ara** (el vèrtex duplicat no es desa) |

### 6.2 Per què aquestes, i no unes altres

**C1 = CCW.** Perquè és el que **el 67 % del material real ja fa** i el 87,5 % dels
fitxers (7 de 8). Perquè és la convenció matemàtica estàndard (interior a l'esquerra), i
perquè **l'únic mòdul que avui calcula l'orientació —`dart_detection`— ja documenta CCW
com el cas de referència**. Normalitzar CCW no toca cap dels 7 fitxers de PolyPattern.

**C2 = menor `(y, x)`.** Mesurat sobre el material:

- **És únic.** Zero vèrtexs duplicats exactes en 3 796 + 3 203 + 459 punts (837, TATE,
  CALLIE). L'empat de `y` sí que existeix (fins a 5 vèrtexs a la mateixa `y` mínima al
  CALLIE), i **el desempat per `x` el resol**.
- **És estable sota graduació.** Provat sobre `niada` (l'únic material amb grading real:
  73 deltes no nuls de 101), aplicant les regles a les 5 talles: l'origen `min(y,x)` és
  **el mateix índex a S, M, L, XL i XXL** a les 4 peces.
  ⚠️ **Prova feble**: només 2–4 punts per peça hi porten regla no nul·la. **A validar amb
  un patró de grading dens abans de ratificar.**
- **És barat.** No demana cap dada nova: és un `min()` sobre punts que ja hi són.
- **I resol D1 de retruc**: amb un origen determinista, `_mirror_points` pot rotar el bucle
  perquè l'eix hi caigui al tancament, que és **exactament** la condició que la §5.2 ha
  aïllat.

**C4.** La fracció es conserva perquè `seam_matching` ja demostra que el mirall d'una
fracció és `1−f` i que això es pot **mesurar** en comptes de suposar
([`:420`](../../backend/fhort/patterns/engine/seam_matching.py#L420)).

### 6.3 Alternatives descartades

| alternativa | per què NO |
|---|---|
| **Deixar-ho com ara** (l'ordre del CAD) | El material **ja no és homogeni** (CALLIE) i **ja hi ha un defecte viu** (§5.2). El cost de no decidir és 6 peces mal desplegades avui i D2 el dia que entri un segon CAD. |
| **Normalitzar per proveïdor** (girar només els CAD coneguts com a CW) | `_guess_source_cad` retorna **cadena buida per al CALLIE**: el CAD que trencaria la regla és el que no sabem identificar. Una llista blanca de proveïdors és una llista que sempre va tard. |
| **Origen = vèrtex 0 del CAD** (statu quo) | Cost de migració zero, però **no és una convenció**: no sobreviu una reexportació ni és comparable entre fitxers, que és precisament el que `SegmentPreference` necessita. |
| **Origen = el vèrtex de regla de grading més baixa** | El grading és **opcional i escàs** (`grade_rule` és nullable per disseny; als punts de corba és sempre `None`). Una regla d'origen que no sempre es pot aplicar no és una regla. |
| **Origen = el punt de gir més proper a una cantonada** | Depèn de la classificació gir/corba, que és **derivada i revisable** (S6/S7). Ancorar l'origen a una decisió que l'usuari pot canviar el faria moure sota els peus dels trams ja desats. |
| **Fer explícit el tancament** (desar el vèrtex duplicat) | Duplicaria una veritat i, en moure el punt, en quedaria una de vella — exactament el que el comentari de `PatternPiece.contorns` ([`models.py:159-162`](../../backend/fhort/patterns/models.py#L159)) diu que s'ha evitat a posta. |
| **Guardar el sentit com a camp** en comptes de normalitzar | Trasllada la decisió a **tots** els consumidors, avui i futurs. Normalitzar a l'entrada la pren **un cop**. |

### 6.4 Cost de migració, per consumidor (llista, no xifres)

Si es ratifica C1+C2 (normalitzar en llegir):

| consumidor | cost | per què |
|---|---|---|
| `aama_reader` | **rotació + inversió a la porta d'entrada** | on va la normalització |
| `unfold_piece` / `_mirror_points` | **cap, o negatiu** | C2 li dona la precondició que li falta: **arregla D1** |
| `aama_writer` | **desfer la normalització en escriure**, o acceptar que el DXF de sortida té un ordre diferent del d'entrada | reproduir el fitxer és un requisit declarat del writer |
| `roundtrip._compare_piece` | 🚨 **el més car**: comparar **per geometria**, no per índex | avui `zip(...)` per posició faria sortir tots els punts com a moguts |
| `rul_writer` / `_rule_at` | **cap** | la clau és el número de regla, lligat per coordenada |
| `measure` (tots els modes) | **cap** | ja és immune al sentit |
| `seam_matching` | **cap** per a la detecció; **afegir el camp** `invertit` a `SewRelation` per no perdre D3 | el càlcul ja hi és |
| `dart_detection` | **cap** | ja mesura l'orientació |
| `patternGeometry.js` + `PatternViewer` | **cap de codi**; sí de **revalidació visual** | comparteix convenció amb el backend |
| `PatternSegment` **ja desats** | 🚨 **recalcular `t_inici`/`t_fi`** de les files existents | la fracció canvia si canvia origen o sentit |
| `SewRelation` / les dues `*Rejection` | **cap directe** | apunten per FK; segueixen el segment |
| `PatternPOM` | **cap** | apunta per id de punt |
| **`SegmentPreference`** | 🚨 **decidir**: recalcular, o **invalidar i tornar a aprendre** | les fraccions apreses són d'un altre sistema de coordenades; recalcular-les exigeix el patró d'origen, que `apres_a` deixa a `SET_NULL` |

> **La pregunta que Patró C ha de respondre primer** no és el sentit: és **què es fa amb
> les fraccions ja desades**. `PatternSegment` es pot recalcular (la geometria hi és).
> `SegmentPreference` **potser no** — i és el model dissenyat expressament per sobreviure.

---

## 7 · Els tests que caldria escriure

> ⚠️ **CAP D'AQUESTS S'HA EXECUTAT.** Es llisten, no es corren (llei de suites 23/08).
> Cap encara no existeix: `patterns/tests.py` no té cap prova d'orientació — l'única
> menció de CCW és un docstring a [`tests.py:5880`](../../backend/fhort/patterns/tests.py#L5880).

### 7.1 Blindatge de la convenció (C1/C2)

| # | test | que ha de fallar si… |
|---|---|---|
| T1 | llegir un DXF **CW** i afirmar que **totes** les vores tancades surten CCW | la normalització no s'aplica |
| T2 | llegir el mateix contorn amb el **vèrtex 0 rotat** i afirmar geometria **i `t` idèntiques** | l'origen no és canònic |
| T3 | afirmar que l'origen és el de **menor `(y,x)`**, amb un cas d'**empat de `y`** | el desempat per `x` falta |
| T4 | llegir → escriure → llegir un DXF CW i afirmar **zero diferències semàntiques** | la normalització trenca el round-trip |
| T5 | normalitzar dues vegades = normalitzar una (**idempotència**) | la normalització no és estable |

### 7.2 Regressió del defecte viu (§5.2) — **els que jo escriuria primer**

| # | test | que ha de fallar si… |
|---|---|---|
| T6 | per a **cada** peça amb doblec del `media`, afirmar `àrea(desplegada) ≈ 2 × àrea(mitja)` **amb el mateix signe** | el desplegat s'empelta al lloc equivocat (**avui falla a 6 de 13**) |
| T7 | afirmar que el contorn desplegat **no s'auto-intersecta** | la §5.3 (el vuit del CALLIE `14`) |
| T8 | cas dirigit amb els punts de l'eix **al mig del bucle** (`[1,2]` de 4) | la precondició no s'ha imposat |
| T9 | `fold_piece(unfold_piece(p))` ≡ `p` per a les 13 peces | el desplegat no és reversible on ara no ho és |

### 7.3 Consumidors

| # | test | que ha de fallar si… |
|---|---|---|
| T10 | `fraccio_tram` amb `t_fi < t_inici` (travessa l'origen) — **ja hauria d'existir** | la volta es torna a fer amb una resta |
| T11 | `tram_entre_punts`: afirmar que l'arc triat és el **curt** i que els extrems s'intercanvien | la normalització direccional canvia |
| T12 | `casen_piquets`: una parella que **només** casa invertida retorna `invertit=True` | es perd el sentit relatiu |
| T13 | 🚨 **`SewRelation` conserva el sentit** de la proposta que la va originar | D3 — **avui no hi ha camp: el test no es pot ni escriure sense migració** |
| T14 | `SegmentPreference` apresa sobre un CCW **no** s'aplica a la fracció mirall d'un CW | D2 |
| T15 | `roundtrip`: comparar **per geometria** i no per índex — afirmar zero diffs amb el bucle rotat | D4 |
| T16 | `measure`: els 4 modes donen el **mateix valor** amb el recorregut invertit | una regressió futura hi introdueix un signe |
| T17 | `dart_detection.apex_cap_enfora` dona el mateix veredicte en CW i en CCW | es perd la compensació d'orientació |

### 7.4 Material de prova que ja existeix

Cap test nou no necessita fitxers inventats:
`CALLIE-…` (CW pur, 30 vores; 6 peces de doblec, 4 trencades) ·
`MEREDITH_-_Retoque.DXF` (CCW amb 2 peces de doblec trencades) ·
`niada.dxf` + `niada.rul` (l'únic amb grading dens: 73 deltes no nuls) ·
`837_CORS_194_VESTIT_M3-4_AGUS.DXF` (CCW net, 10 de 10) · `TATE.DXF` (piquets).

---

## 8 · Rastre

Tot el que hi ha aquí és lectura. Les mesures es reprodueixen amb el venv del projecte
(`backend/venv/bin/python`) llegint `backend/media/fhort/pattern_files/`, i el motor
s'importa en memòria (`engine/` és Python pur, sense Django):

| mesura | com |
|---|---|
| §1.2 cens d'orientació | shoelace sobre `POLYLINE` **tancades**, per BLOCK i capa |
| §1.3 CAD d'origen | primer `TEXT` de modelspace + `_guess_source_cad` |
| §6.2 unicitat de `min(y,x)` | recompte de coordenades duplicades exactes (arrodonides a 1e-6) |
| §6.2 estabilitat sota grading | deltes del `.rul` aplicats per número de regla a les 5 talles de `niada`, `argmin(y,x)` per talla |
| §5.2 taula del desplegat | `AAMAReader().read()` → `unfold_piece()`, ràtio d'àrees signades i índexs amb `_on_axis` |
| §5.3 bolcat de la peça 14 | punts abans/després de `unfold_piece` |

**Cap ordre ha escrit res**, i no s'ha executat cap test.
