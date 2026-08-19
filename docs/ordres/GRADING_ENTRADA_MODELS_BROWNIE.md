# GRADING — ENTRADA CRUA DE MODELS BROWNIE (per comparar amb catàleg v3)

> **Obert:** 2026-08-06 · **Propòsit:** bústia d'entrada. L'Agus va pujant fitxes de grading
> de models Brownie (identificats per NOM, no tenen referència BRW encara — són fitxes soltes,
> no models creats a staging). Es guarden CRUES, tal com vénen del document. Quan n'hi hagi
> prou, es comparen contra `BROWNIE_CATALEG_POM_v3.xlsx` (full CATALEG, 119 codis) al projecte
> de Claude Chat.
> **Cap escriptura a BD. Cap ruleset tocat. Cap fitxer del repo tocat.** Això és matèria primera.
>
> Format per model: codi (tal com surt a la fitxa) · descripció EN · grading (Δ mm/cm segons
> règim del document) · valors per talla. Es respecta el nom del document; NO es normalitza
> contra el v3 aquí (això és precisament la comparació pendent).

---

## MODEL 1 · "Dessuadora Animal"

**Marca:** Brownie · **Talla base:** S · **Talles del run:** XXS · XS · S · M · L
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit — no especificat al document)

| CODI | DESCRIPCIÓ (EN) | GRADING | XXS | XS | S | M | L |
|---|---|---|---|---|---|---|---|
| **Bodice** | | | | | | | |
| A | 1/2 chest width (armpit to armpit) | 3 | 58 | 61 | 61 | 64 | 64 |
| D | 1/2 bottom width relaxed | 3 | 46 | 49 | 49 | 52 | 52 |
| D1 | 1/2 bottom width extended | 3 | 58 | 61 | 61 | 64 | 64 |
| G1 | Bottom hem / Bottom rib height | 0 | 5 | 5 | 5 | 5 | 5 |
| E2 | Across front width (11cm from HPS) | 1,5 | 48,5 | 50 | 50 | 51,5 | 51,5 |
| E3 | Across back width (11cm from HPS) | 1,5 | 49,5 | 51 | 51 | 52,5 | 52,5 |
| E | Shoulder to shoulder | 1,5 | 50,5 | 52 | 52 | 53,5 | 53,5 |
| E5 | Shoulder drop (from HSP to shoulder point) | 0 | 5,5 | 5,5 | 5,5 | 5,5 | 5,5 |
| E1 | Shoulder seam | 0,4 | 16,1 | 16,5 | 16,5 | 16,9 | 16,9 |
| E4 | Shoulder Forward | 0 | 1,5 | 1,5 | 1,5 | 1,5 | 1,5 |
| EK | Neck width seam to seam | 0,75 | 21,75 | 22,5 | 22,5 | 23,25 | 23,25 |
| EK1 | Front neck drop from HSP to seam | 0,4 | 9,1 | 9,5 | 9,5 | 9,9 | 9,9 |
| EK2 | Back neck drop from HSP to seam | 0 | 2,5 | 2,5 | 2,5 | 2,5 | 2,5 |
| F | Centre front length from HSP (incl hem/rib) | 1 | 60 | 61 | 61 | 62,5 | 62,5 |
| FF | Centre back length from HSP (incl hem/rib) | 1 | 60 | 61 | 61 | 62,5 | 62,5 |
| **Pocket** | | | | | | | |
| R3 | Pocket height at the center | 0,5 | 17,5 | 18 | 18 | 18,5 | 18,5 |
| R2 | Pocket width at the top | 1 | 20,5 | 21,5 | 21,5 | 22,5 | 22,5 |
| R4 | Pocket width at the bottom | 1 | 33 | 34 | 34 | 35 | 35 |
| R | Pocket opening | 0,75 | 14,75 | 15,5 | 15,5 | 16,25 | 16,25 |
| RR | Pocket opening height hem | 2 | 0 | 2 | 2 | 4 | 4 |
| **Hoodie** | | | | | | | |
| HO | 1/2 opening of the hoodie | 0,5 | 36,5 | 37 | 37 | 37,5 | 37,5 |
| HL | Hoodie's height at the shoulder point | 0,5 | 31 | 31,5 | 31,5 | 32 | 32 |
| HW | Width of the hoodie at 12cm from top edge | 0,5 | 25,5 | 26 | 26 | 26,5 | 26,5 |
| **Armhole** | | | | | | | |
| SF | Sleeve depth | 1 | 23,5 | 24,5 | 24,5 | 25,5 | 25,5 |
| S | Front armhole along seam | 1 | 24 | 25 | 25 | 26 | 26 |
| S2 | Back armhole along seam | 1 | 26 | 27 | 27 | 28 | 28 |
| **Sleeves** | | | | | | | |
| I | Sleeve length | 1 | 55 | 56 | 56 | 57 | 57 |
| J | 1/2 Bicep width | 0,8 | 23,5 | 24,3 | 24,3 | 25,1 | 25,1 |
| J1 | Sleeve opening relaxed | 0,5 | 8 | 8,5 | 8,5 | 9 | 9 |
| J3 | Sleeve hem / Sleeve cuff height | 0 | 5 | 5 | 5 | 5 | 5 |

**Notes crues (sense interpretar encara):**
- El document ve amb capçalera "ENGLISH" (sembla multi-idioma originalment, aquí només la part EN).
- `D1` "extended" té els mateixos valors que `A` (chest width) a totes les talles — coincidència a
  verificar contra el v3, no assumir errata.
- `G1` al v3 (full CATALEG) és "Rib height" (D-31 rebatejo G1↔D1 del Brief 4) — aquest document
  usa G1 per "Bottom hem / Bottom rib height", cal veure si quadra o si aquí ve del nom pre-rebateig.
- Talla de ruptura del grading: XS→S sense salt (mateixos valors a totes les files) — S=XS arreu;
  el salt real és XXS→XS i S→M. Consistent amb "talla base S" com a ancoratge inferior del bloc gran.

---

## MODEL 2 · "RUFFLES Faldilla Pantaló"

**Marca:** Brownie · **Talla base (SAMPLE SIZE):** S · **Talles del run:** XXS · XS · S · M · L
**Temporada:** WINTER 2027 · **Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Aquesta fitxa porta **dues columnes de GRADING** (no una com la de l'animal): `XXS-XS` i `XS-L`.
Es guarden totes dues tal com vénen — no s'assumeix quina és la "oficial" per comparar amb el v3
(el v3 porta 4 columnes de Δ per bracket: XXS→XS, XS→S, S→M, M→L; aquí només n'hi ha 2, cosa que
ja és una diferència d'estructura a resoldre a la comparació, no ara).

| CODI | DESCRIPCIÓ (EN) | GRAD. XXS-XS | GRAD. XS-L | XXS | XS | S | M | L |
|---|---|---|---|---|---|---|---|---|
| **(sense secció al document)** | | | | | | | | |
| B | 1/2 waist width at the top | 2 | 3 | 30 | 32 | 35 | 38 | 41 |
| BB | 1/2 waist width at the bottom | 2 | 3 | 31 | 33 | 36 | 39 | 42 |
| B1 | 1/2 waist width stretched out | 2 | 3 | 40 | 42 | 45 | 48 | 51 |
| BF | Waistband height | 0 | 0 | 7,2 | 7,2 | 7,2 | 7,2 | 7,2 |
| D | 1/2 bottom width spread out | 2 | 3 | 73 | 75 | 78 | 81 | 84 |
| G1 | Bottom height | 0 | 0 | 0,5 | 0,5 | 0,5 | 0,5 | 0,5 |
| FS | Total length at the CF | 0,5 | 1 | 32 | 32,5 | 33 | 34 | 35 |
| FS2 | Total length at the CB | 0,5 | 1 | 34,5 | 35 | 35,5 | 36,5 | 37,5 |
| FS3 | Total length at the side seams | 0,5 | 1 | 32,5 | 33 | 33,5 | 34,5 | 35,5 |
| FS4 | Top layer of the skirt length distance from waistband bottom seam | 0,5 | 1 | 21 | 21,5 | 22 | 23 | 24 |
| FS5 | Lining length difference between true length | 0 | 0 | 1 | 1 | 1 | 1 | 1 |
| **Lining (short)** | | | | | | | | |
| FR | Front rise excluding waistband | 0,7 | 1,1 | 16,7 | 17,4 | 18,5 | 19,6 | 20,7 |
| FE | Back rise excluding waistband | 0,9 | 1,5 | 27,6 | 28,5 | 30 | 31,5 | 33 |
| CT | 1/2 thigh width | 1,2 | 1,8 | 30 | 31,2 | 33 | 34,8 | 36,6 |
| M | 1/2 bottom width | 1,2 | 1,8 | 30 | 31,2 | 33 | 34,8 | 36,6 |
| M1 | Bottom hem height | 0 | 0 | 0,5 | 0,5 | 0,5 | 0,5 | 0,5 |
| F1 | Inseam length | 0 | 0,5 | 4,5 | 4,5 | 5 | 5,5 | 6 |
| FT | Side seam length excluding waistband | 0,5 | 1 | 21 | 21,5 | 22 | 23 | 24 |

**Notes crues (sense interpretar encara):**
- **FS5 apareix aquí, i el Brief 4 del v3 ja el va introduir com a POM nou** ("FS5 nou — Lining
  length difference, FIXED"). Primer punt de contacte real entre una fitxa i el v3: a comparar
  si el nom i el règim (FIXED, Δ=0 a totes les talles, valor 1 constant) coincideixen exactament.
- `G1` torna a aparèixer, aquí com "Bottom height" (③a fitxa: "Bottom hem / Bottom rib height" a
  l'animal). Tercer nom diferent pel mateix codi comptant el rebateig del v3 — reforça que G1 és
  un dels punts calents a portar a la Montse, no a decidir aquí.
  Fitxes ja acumulades → 3 usos diferents del codi G1.
- `M` i `CT` porten exactament els mateixos valors a totes les talles (1/2 thigh width = 1/2
  bottom width) — com el cas D1≈A de l'animal: pot ser real (peça sense entallament al baix de
  cuixa) o coincidència de la fitxa. No assumit.
- Capçalera amb metadades pròpies (DATE buit, COLOR buit, SEASON=WINTER 2027) que l'animal no
  portava — si les properes fitxes hi són consistents, es pot fer una capçalera de metadades
  comuna per a la comparació final.

---

## MODEL 3 · "KAYCE Blusa"

**Marca:** Brownie · **Color:** Blanco · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Aquesta fitxa **NO porta grading** — només talla S (sample size). Es guarda tal qual.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 50 |
| D | 1/2 bottom width relaxed | 61 |
| G1 | Bottom hem / Bottom rib height | 0,5 |
| E2 | Across front width (11cm from HPS) | 33 |
| E3 | Across back width (11cm from HPS) | 34,5 |
| E | Shoulder to shoulder | 34 |
| E5 | Shoulder drop (from HSP to shoulder point) | 1,5 |
| E1 | Shoulder seam | 8 |
| E4 | Shoulder Forward | 2 |
| EK | Neck width seam to seam | 18 |
| EK1 | Front neck drop from HSP to seam | 8,5 |
| EK2 | Back neck drop from HSP to seam | 2 |
| F | Centre front length from HSP (incl hem/rib) | 56 |
| FF | Centre back length from HSP (incl hem/rib) | 56 |
| F1 | Curve at side | 3 |
| M | Front piece distance from HPS (excl. lace) | 22 |
| M1 | Front piece width at the top (excl. lace) | 19 |
| M2 | Front piece width at the bottom (excl. lace) | 25 |
| **Armhole** | | |
| SF | Armhole depth from HPS | 22 |
| S | Front armhole along seam | 24,5 |
| S2 | Back armhole along seam | 26,5 |
| **Sleeves** | | |
| I | Sleeve length | 64 |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 81 |
| J | 1/2 Bicep width | 20 |
| J1 | Sleeve opening relaxed | 9 |
| J2 | Sleeve opening stretched out | 18 |
| J3 | Sleeve hem / Sleeve cuff height | 0,7 |
| **Back yoke** | | |
| L | Back yoke CB height from top edge | 14 |
| L2 | Yoke seam from armhole to armhole | 36,5 |
| **Back opening** | | |
| O | Back opening length | 10,5 |

---

## MODEL 4 · "MEREDITH Blusa"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Dues columnes de GRADING (`XXS-XS` i `XS-L`), com RUFFLES. Es guarda tal qual, incloent-hi les
cel·les buides del document (E4 a XS, VL a les dues columnes de grading).

| CODI | DESCRIPCIÓ (EN) | GRAD. XXS-XS | GRAD. XS-L | XXS | XS | S | M | L |
|---|---|---|---|---|---|---|---|---|
| **Bodice** | | | | | | | | |
| A | 1/2 chest width (armpit to armpit) | 2 | 3 | 43 | 45 | 48 | 51 | 54 |
| D | 1/2 bottom width relaxed | 2 | 3 | 32 | 34 | 37 | 40 | 43 |
| D1 | 1/2 bottom width stretched out | 2 | 3 | 53,5 | 55,5 | 58,5 | 61,5 | 64,5 |
| G1 | Bottom hem / Bottom rib height | 0 | 0 | 0,7 | 0,7 | 0,7 | 0,7 | 0,7 |
| E2 | Across front width (11cm from HPS) | 1 | 1,5 | 33,5 | 34,5 | 36 | 37,5 | 39 |
| E3 | Across back width (11cm from HPS) | 1 | 1,5 | 36 | 37 | 38,5 | 40 | 41,5 |
| E | Shoulder to shoulder | 1 | 1,5 | 40,5 | 41,5 | 43 | 44,5 | 46 |
| E5 | Shoulder drop (from HSP to shoulder point) | 0 | 0 | 3,5 | 3,5 | 3,5 | 3,5 | 3,5 |
| E1 | Shoulder width at true shoulder | 0,25 | 0,4 | 12,35 | 12,6 | 13 | 13,4 | 13,8 |
| E4 | Shoulder Forward | 0 | 0 | 0 | *(buit al document)* | 0 | 0 | 0 |
| EK | Neck width seam to seam | 0,5 | 0,75 | 16,25 | 16,75 | 17,5 | 18,25 | 19 |
| EK1 | Front neck drop from HSP to seam | 0,25 | 0,4 | 5,05 | 5,3 | 5,7 | 6,1 | 6,5 |
| EK2 | Back neck drop from HSP to seam | 0 | 0 | 3,5 | 3,5 | 3,5 | 3,5 | 3,5 |
| V | Frill width at the shoulder | 0 | 0 | 14,5 | 14,5 | 14,5 | 14,5 | 14,5 |
| VL | End of FRONT frill distance from HPS | *(buit)* | *(buit)* | 50 | 50 | 50 | 50 | 50 |
| F | Centre front length from HSP (incl hem/rib) | 1 | 1 | 51 | 52 | 53 | 54,5 | 56 |
| FF | Centre back length from HSP (incl hem/rib) | 1 | 1 | 51 | 52 | 53 | 54,5 | 56 |
| **Collar** | | | | | | | | |
| EP | Collarstand height at CB | 0 | 0 | 2,4 | 2,4 | 2,4 | 2,4 | 2,4 |
| **Armhole** | | | | | | | | |
| SF | Armhole depth from HPS | 0,7 | 1 | 23,8 | 24,5 | 25,5 | 26,5 | 27,5 |
| S | Front armhole along seam | 0,7 | 1 | 21,8 | 22,5 | 23,5 | 24,5 | 25,5 |
| S2 | Back armhole along seam | 0,7 | 1 | 20,3 | 21 | 22 | 23 | 24 |
| **Sleeves** | | | | | | | | |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 1,5 | 1,75 | 77,25 | 78,75 | 80,5 | 82,25 | 84 |
| J | 1/2 Bicep width | 0,6 | 0,8 | 16,6 | 17,2 | 18 | 18,8 | 19,6 |
| J1 | Sleeve opening relaxed | 0,3 | 0,5 | 8,2 | 8,5 | 9 | 9,5 | 10 |
| J2 | Sleeve opening stretched out | 0,6 | 0,8 | 18,6 | 19,2 | 20 | 20,8 | 21,6 |
| J3 | Sleeve hem / Sleeve cuff height | 0 | 0 | 0,5 | 0,5 | 0,5 | 0,5 | 0,5 |
| **Back opening** | | | | | | | | |
| O | Back opening length | 0 | 0 | 8,5 | 8,5 | 8,5 | 8,5 | 8,5 |

Nota literal: la fila de "Back opening" al document porta el codi com `0` (zero) no `O` (lletra O)
— es guarda com `O` aquí perquè és clarament l'intent (compara amb KAYCE, mateix camp, codi `O`
lletra), però es marca per confirmar-ho, no s'assumeix silenciosament.

---

## MODEL 5 · "TENDER Blusa"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — només talla S, com KAYCE.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 47 |
| D | 1/2 bottom width relaxed measured at the elastic band | 35 |
| D1 | 1/2 bottom width stretched out measured at the elastic band | 46 |
| G1 | Bottom hem / Bottom rib height | 0,5 |
| V | Ruffle at the hem | 7 |
| G2 | Elastic height at the waist | 0,8 |
| E2 | Across front width (11cm from HPS) | 32 |
| E3 | Across back width (11cm from HPS) | 34 |
| E | Shoulder to shoulder | 37,5 |
| E5 | Shoulder drop (from HSP to shoulder point) | 3,5 |
| E1 | Shoulder width at true shoulder | 8,5 |
| E4 | Shoulder Forward | 1 |
| EK | Neck width seam to seam | 20,5 |
| EK1 | Front neck drop from HSP to middle of first button | 8 |
| EK2 | Back neck drop from HSP to seam | 1,5 |
| F | Centre front length from HSP (incl hem/rib) | 58 |
| FF | Centre back length from HSP (incl hem/rib) | 57 |
| **Armhole** | | |
| SF | Armhole depth from HPS | 22,5 |
| S | Front armhole along seam | 23 |
| S2 | Back armhole along seam | 23 |
| **Sleeves** | | |
| I | Sleeve length | 63 |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 81,5 |
| J | 1/2 Bicep width | 17,5 |
| J1 | Sleeve opening relaxed | 9 |
| J2 | Sleeve opening stretched out | 15 |
| J3 | Sleeve hem / Sleeve cuff height | 0,7 |
| **(sense secció al document)** | | |
| O | Back opening length | 8 |

Nota literal: igual que a MEREDITH, el document escriu el codi de "Back opening length" com `0`
(zero) en lloc de `O` (lletra). Es guarda com `O` pel mateix motiu — dos cops seguits ja no sembla
atzar tipogràfic puntual, és un patró de la plantilla a confirmar.

---

## MODEL 6 · "NIKITA Pants"

**Marca:** Brownie (assumit — no consta explícitament al document, a diferència de la resta)
**Sample size:** S (únic valor a la fitxa) · **Font:** fitxa tècnica (Agus, xat 2026-08-06)
**Unitats:** cm (assumit)

Format diferent de la resta: descripció en castellà + anglès, **una sola columna de GRAD**
(no dues ni quatre com les altres), i dos codis (`F`, `FI`) porten la paraula **"broken"** al
lloc del número de grading en lloc d'un valor — es guarda literal, no s'interpreta com a 0 ni
com cap valor numèric.

| CODI | DESCRIPCIÓ (ES) | DESCRIPTION (EN) | GRAD | S |
|---|---|---|---|---|
| B | ancho cintura al canto | waist edge width | 2,0 | 36,0 |
| B1 | clavado cintura | seam waist width | 2,0 | 41,5 |
| FB | alto cinturilla | waist heigth | 0,0 | 7,5 |
| FC | posicion cadera | hip position | 0,5 | 20,0 |
| C | ancho total cadera | hip width | 2,0 | 48,0 |
| CT | ancho muslo | leg width | 1,3 | 31,3 |
| D | ancho bajo | bottom width | 0,5 | 29,0 |
| FD | tiro delantero desde cinturilla | front rise length adding waist band | 0,7 | 26,0 |
| FT | tiro detrás desde cinturilla | back rise with adding waist band | 1,3 | 36,5 |
| F | largo total | total length | **broken** | 104,0 |
| FI | largo entrepierna | inside length | **broken** | 77,7 |
| UT2 | ancho loop | loop width | 0,0 | 0,9 |
| UT1 | alto loop | loop length | 0,0 | 8,5 |
| BR | ancho bragueta | fly width | 0,0 | 3,5 |
| BR1 | largo dibujo bragueta | fly draw length | 0,5 | 10,0 |
| **(secció "bolsillos / pockets")** | | | | |
| R1 | largo bolsillo | pocket length | 0,5 | 13,5 |
| PR1 | posicion bolsillo detrás | back pocket position | 0,3 | 5,0 |
| PR2 | posicion bolsillo detrás | back pocket position | 0,3 | 5,5 |
| PR3 | posicion bolsillo desde centro | back pocket position from center | 0,6 | 4,5 |
| R3 | ancho bolsillo detrás | back pocket length | 0,5 | 12,0 |
| R4 | ancho bolsillo detrás | back pocket width | 0,5 | 1,2 |

Notes crues:
- `PR1` i `PR2` tenen la mateixa descripció ("posicion bolsillo detrás") per a dos codis diferents
  amb valors diferents (5,0 i 5,5) — es guarda tal qual, no es dedueix quina és quina.
- `"broken"` a `F` i `FI` sembla indicar que el grading d'aquell POM no és lineal (trencat/per
  trams), consistent amb el concepte "Talla de ruptura" que ja existeix al sistema (Bloc A5,
  09-08-06) — però això és tema d'anàlisi, no es resol aquí.
- No hi ha columna de talles XXS/XS/M/L: només S. És l'única fitxa amb GRAD + S sol sense la
  resta del run.

---

## MODEL 7 · "MILEY Vestit de punt"

**Font:** captura de pantalla (Agus, xat 2026-08-06) · **Sample size:** S (columna buida a la
imatge — no hi ha valor escrit) · **Unitats:** cm (assumit)

⚠️ **Nom coincident amb el model MILEY ja citat a `ESTAT_PROJECTE.md` (S35, 2026-08-06) com a
model intocable amb dany conegut** (4 regles MANUAL afectades, salt FF 35.0 pendent que l'Agus
arregli a mà). Es guarda la dada tal qual; **no s'assumeix que sigui el mateix registre** de
staging — és una fitxa de disseny/proto, no dada de BD. Confirmar-ho quan toqui, no ara.

Format diferent de la resta: no porta GRADING ni el run de talles (XXS-L). Porta **PROTO** (valor
mesurat al prototip) i **ADJUSTMENTS** (valor corregit, only on rows marked "ADJUSTED"). La
columna `S` de la imatge apareix buida (en blau, sense valor escrit).

| CODI | DESCRIPCIÓ (EN) | S | PROTO | ADJUSTMENTS | COMMENTS |
|---|---|---|---|---|---|
| **Bodice** | | | | | |
| A | 1/2 front chest width (armpit to armpit) | *(buit)* | 32 | 29 | ADJUSTED |
| A1 | 1/2 back chest width (armpit to armpit) | *(buit)* | 29,5 | 32,5 | ADJUSTED |
| D1 | 1/2 bottom width stretched out | *(buit)* | 132 | | |
| E2 | Across front width (16cm from HPS) | *(buit)* | 18 | | |
| F | Centre front length from HSP (incl hem/rib) | *(buit)* | 52 | 50 | ADJUSTED |
| FF | Centre back length | *(buit)* | 24,5 | | |
| F1 | Total side length relaxed | *(buit)* | 26 | 23,5 | ADJUSTED |
| F11 | Total side length extended | *(buit)* | 26 | 38,5 | ADJUSTED |
| EK | 1/2 neck width (measured at the top) | *(buit)* | 15 | 17 | ADJUSTED |
| **Armhole** | | | | | |
| SF | Armhole depth from HPS | *(buit)* | 26 | 27 | ADJUSTED |
| S | Front armhole along seam | *(buit)* | 24 | | |
| **Sequins piece** | | | | | |
| C | 1/2 hip width | *(buit)* | 47 | 48,5 | ADJUSTED |
| U1 | Sequins piece height | *(buit)* | 10 | 11 | ADJUSTED |
| **Skirt** | | | | | |
| FS | Skirt CF length | *(buit)* | 75 | | |
| FS1 | Skirt side length | *(buit)* | 67 | | |

Notes crues:
- Taula tallada a la imatge (acaba a FS1 — pot haver-hi més files no capturades).
- `E2` diu "16cm from HPS" — a la resta de fitxes (animal, KAYCE) E2 deia "11cm from HPS". Mateix
  codi, distància de referència diferent. Es guarda literal, no es corregeix.
- Aquesta és l'única fitxa amb el patró PROTO→ADJUSTMENTS en lloc de grading per talles; estructura
  incompatible amb les altres 6 tal qual, a resoldre a la comparació.

---

## MODEL 8 · "AITANA Faldilla Pantaló"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — porta dues columnes de valor: `S` i `SAMPLE / RECTI 1` (una rectificació de
mostra, no una talla). Estructura pròpia, diferent de les 7 anteriors.

| CODI | DESCRIPCIÓ (EN) | S | SAMPLE (RECTI 1) |
|---|---|---|---|
| B | 1/2 waist width | 34 | 35 |
| BF | Waistband height | 10 | 11 |
| FC | Hip position from top edge | 14 | 14 |
| C | 1/2 hip width | 45 | 44 |
| CT | 1/2 thigh width | 18 | 23 |
| M | 1/2 leg opening width | 18 | 24 |
| M1 | Bottom height | 1,8 | 2 |
| FT | Pants total length | 22 | 21 |
| F1 | Inseam length | 4 | 4 |
| FR | Front rise (excl. waistband) | 19,5 | 17,5 |
| FE | Back rise (excl. waistband) | 30,5 | 28,5 |
| **Skirt** | | | |
| FS | Total CF length of the skirt | 26 | 26 |
| FS2 | Total CB length of the skirt | 28 | 28 |
| D | 1/2 bottom width | 48 | 45 |
| G1 | Bottom height | 1,8 | 2 |

Notes crues:
- **G1 hi torna a aparèixer**, aquí com "Bottom height" (mateix nom que a RUFFLES) — quart ús
  documentat del codi entre les 8 fitxes, comptant el rebateig del v3.
- Els salts entre `S` i `RECTI 1` són grans en alguns codis (CT 18→23, M 18→24: +5/+6 cm) — és
  una rectificació de mostra real, no un error de transcripció aparent; es guarda tal qual.
- És la segona fitxa "faldilla pantaló" del lot (amb RUFFLES). Comparteix codis (B, BF, FC, C,
  CT, M, D, G1, FS, FR/FE) però amb algunes descripcions lleugerament diferents (p.ex. `M` aquí
  és "1/2 leg opening width", a RUFFLES `M` és "1/2 bottom width") — bon parell per contrastar
  a la comparació.

---

## MODEL 9 · "SUSI Faldilla"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — només talla S. Peça asimètrica (alçades diferents a dreta/esquerra al portar-la).

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| B | 1/2 waist width | 32 |
| D | 1/2 bottom width | 77 |
| G1 | Bottom hem height | 0,7 |
| **Yoke/waistband** | | |
| BF1 | Height at CF | 13 |
| BF2 | Height at the right side when wearing | 10 |
| BF3 | Height at the left side when wearing | 8 |
| BF4 | Height at the longest point | 16 |
| FS1 | Total length at the right side when wearing | 66 |
| FS2 | Total length at the left side when wearing | 56 |
| **Godet** | | |
| GD | Godet length at the longest point | 68 |
| GD1 | Godet length at the seams | 54,5 |
| **Cord** | | |
| LZ | Cord length | 185 |
| FZ | Cord width | 0,7 |

Notes crues:
- **G1 hi torna a aparèixer**, aquí com "Bottom hem height" — cinquè ús documentat del codi entre
  les 9 fitxes.
- `FS1`/`FS2` aquí signifiquen "right/left side when wearing" (asimetria) — a RUFFLES i MEREDITH
  `FS`/`FS2` volien dir CF/CB. Mateix parell de codis, semàntica de peça completament diferent.
  Punt fort a portar a la comparació/Montse.
- Peça amb vocabulari propi no vist a les 8 anteriors: "Yoke/waistband" asimètric, "Godet", "Cord"
  (LZ/FZ — cap altra fitxa porta cordó).

---

## MODEL 10 · "BEYONCÉ Top"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027 · **Data document:** 6/7/26
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — columna `S` buida (com MILEY), valor real només a `SAMPLE/PROTO`.

| CODI | DESCRIPCIÓ (EN) | S | SAMPLE (PROTO) |
|---|---|---|---|
| **Bodice** | | | |
| A | 1/2 chest width (armpit to armpit) | *(buit)* | 38,5 |
| D | 1/2 bottom width relaxed | *(buit)* | 32,5 |
| D1 | 1/2 bottom width extended | *(buit)* | 45 |
| AA | 1/2 back bottom piece width at top relaxed | *(buit)* | 34 |
| AA1 | 1/2 back bottom piece width at top stretched out | *(buit)* | 47 |
| EK | Top width from edge to edge | *(buit)* | 11 |
| LZ | Collar height | *(buit)* | 4 |
| LZ1 | Collar bow total length from edge to edge | *(buit)* | 118 |
| F | Centre front length at CF excluding collar | *(buit)* | 37 |
| FF | Back piece with sequins height at CB | *(buit)* | 6 |
| FF1 | Back bottom piece height at CB | *(buit)* | 12,5 |

Notes crues:
- **LZ ja havia aparegut a SUSI** com "Cord length" (185) — aquí és "Collar height" (4). Mateix
  codi, peça i significat totalment diferents (cordó vs coll). Cas clar per a la comparació.
- `EK` aquí és "Top width from edge to edge" — a totes les altres fitxes de la sèrie (animal,
  KAYCE, TENDER, RUFFLES, MEREDITH) `EK` és "Neck width seam to seam". Divergència notable.
- Columna `S` buida com a MILEY i BEYONCÉ — patró que ja són 2 de 10 fitxes amb aquesta
  estructura (sample buida, proto/ajustos amb el valor real).

---

## MODEL 11 · "BONITA Camiseta Manga Llarga"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027 · **Data document:** 6/7/26
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — columna `S` buida, valor real a `SAMPLE/PROTO 1`. Tercera fitxa amb aquest
patró (amb MILEY i BEYONCÉ).

| CODI | DESCRIPCIÓ (EN) | S | SAMPLE (PROTO 1) |
|---|---|---|---|
| **Bodice** | | | |
| A | 1/2 chest width (armpit to armpit) | *(buit)* | 39 |
| D | 1/2 bottom width relaxed | *(buit)* | 38,5 |
| G1 | Bottom hem / Bottom rib height | *(buit)* | 1,3 |
| E2 | Across front width (11cm from HPS) | *(buit)* | 27,5 |
| E3 | Across back width (11cm from HPS) | *(buit)* | 28 |
| EK | Neck width edge to edge | *(buit)* | 25 |
| EK1 | Front neck drop from HSP to edge | *(buit)* | 8,5 |
| EK2 | Back neck drop from HSP to edge | *(buit)* | 8 |
| F | Centre front length from HSP (incl hem/rib) | *(buit)* | 54 |
| FF | Centre back length from HSP (incl hem/rib) | *(buit)* | 54 |
| **Armhole** | | | |
| S | Front armhole along seam | *(buit)* | 16 |
| S2 | Back armhole along seam | *(buit)* | 17 |
| **Sleeves** | | | |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | *(buit)* | 81,5 |
| J | 1/2 Bicep width | *(buit)* | 14 |
| J1 | Sleeve opening relaxed | *(buit)* | 8,5 |
| J3 | Sleeve hem / Sleeve cuff height | *(buit)* | 1,3 |
| **Sleeve opening** | | | |
| O | Opening at sleeve | *(buit)* | 10 |

Notes crues:
- **G1 hi torna a aparèixer**, aquí com "Bottom hem / Bottom rib height" — mateix nom exacte que
  a la fitxa animal (Model 1). Sisè ús documentat del codi, i el primer que coincideix literalment
  amb un altre.
- **EK aquí és "Neck width edge to edge"** — un tercer significat pel mateix codi comptant BEYONCÉ
  ("Top width edge to edge") i les fitxes de coll clàssiques ("Neck width seam to seam").
- Codi de "sleeve opening" escrit com `0` (zero) al document, igual que MEREDITH i TENDER amb
  "back opening" — es guarda com `O` (lletra) pel mateix motiu, patró ja reconegut (tercer cop).
- És la fitxa amb el "chest width" (A=39) més gran de les de tipus samarreta/blusa sense el
  "1/2 back chest width" separat (A1) — a comparar amb KAYCE i TENDER que sí tenen aquest camí
  de mesura complet.

---

## MODEL 12 · "CAJA Camiseta Manga Llarga"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — només talla S, com KAYCE/TENDER/SUSI.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 40 |
| D | 1/2 bottom width relaxed | 40 |
| G1 | Bottom hem / Bottom rib height | 1,7 |
| E2 | Across front width (11cm from HPS) | 31 |
| E3 | Across back width (11cm from HPS) | 33 |
| EK | Neck width seam to seam | 17,5 |
| EK1 | Front neck drop from HSP to seam | 8,5 |
| EK2 | Back neck drop from HSP to seam | 1,5 |
| EP | Collar binding width | 0,7 |
| E | Shoulder to shoulder | 34 |
| E5 | Shoulder drop (from HSP to shoulder point) | 3,5 |
| E1 | Shoulder seam | 10 |
| E4 | Shoulder Forward | 1 |
| F | Centre front length from HSP (incl hem/rib) | 55 |
| FF | Centre back length from HSP (incl hem/rib) | 54 |
| SF | Sleeve depth from HPS | 20,5 |
| S | Front armhole along seam | 20,5 |
| S2 | Back armhole along seam | 21 |
| I | Sleeve length | 62 |
| J | 1/2 Bicep width | 13,5 |
| J1 | Sleeve opening relaxed | 9 |
| J3 | Sleeve hem / Sleeve cuff height | 1,5 |

Notes crues:
- **G1 hi torna a aparèixer**, "Bottom hem / Bottom rib height" — mateix nom que l'animal i
  BONITA (setè ús documentat del codi en total).
- **EK aquí és "Neck width seam to seam"**, com l'animal/KAYCE/TENDER/RUFFLES/MEREDITH — encaixa
  amb el grup majoritari, no amb la variant de BEYONCÉ/BONITA ("edge to edge"/"top width").
- Document sense secció visual (sense negretes "Bodice:"/"Armhole:"/"Sleeves:" separades a
  continuació d'EP) — es guarda en bloc únic tal com ve.
- Fitxa "bessona" de BONITA (mateixa família CAMISETA MANGA LARGA) però amb `EP` (Collar binding
  width) que BONITA no porta, i sense el codi `0`/`O` de sleeve opening que BONITA sí porta —
  bon parell per contrastar quan comparem.

---

## MODEL 13 · "LITTLE STAR Camiseta Manga Llarga"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)
**Nota d'Agus:** espatlla oberta (peça amb tall/obertura a l'espatlla — secció "Sleeve cut out"
pròpia, no vista a cap fitxa anterior).

Sense grading — només talla S.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 40 |
| D | 1/2 bottom width relaxed | 40 |
| G1 | Bottom hem / Bottom rib height | 1,7 |
| E2 | Across front width (11cm from HPS) | 30 |
| E3 | Across back width (11cm from HPS) | 31,5 |
| E | Shoulder to shoulder | 31 |
| E5 | Shoulder drop (from HSP to shoulder point) | 3 |
| E1 | Shoulder seam | 7 |
| E4 | Shoulder Forward | 1 |
| EK | Neck width edge to edge | 18 |
| EK1 | Front neck drop from HSP to edge | 8,5 |
| EK2 | Back neck drop from HSP to edge | 2 |
| F | Centre front length from HSP (incl hem/rib) | 51 |
| FF | Centre back length from HSP (incl hem/rib) | 50 |
| **Armhole** | | |
| SF | Sleeve depth from HPS | 20,5 |
| S | Front armhole along seam | 20 |
| S2 | Back armhole along seam | 21 |
| **Sleeves** | | |
| I | Sleeve length | 54 |
| J | 1/2 Bicep width | 12,5 |
| J1 | Sleeve opening relaxed | 9 |
| J3 | Sleeve hem / Sleeve cuff height | 1,7 |
| **Sleeve cut out** | | |
| CO | Cut out from shoulder seam at the front | 8 |
| CO1 | Cut out from shoulder seam at the back | 9,5 |
| CO2 | Cut out from shoulder to sleeve | 3,5 |

Notes crues:
- **G1 hi torna a aparèixer** amb el mateix nom que l'animal/BONITA/CAJA — vuitè ús documentat.
- **EK aquí és "Neck width edge to edge"** — coincideix amb LITTLE STAR i BEYONCÉ/BONITA (grup
  "edge to edge"), no amb CAJA/animal/KAYCE (grup "seam to seam"). Ara ja hi ha un grup de 3-4
  fitxes a cada banda d'aquesta divergència, no és un cas aïllat.
- **Secció nova "Sleeve cut out" (CO/CO1/CO2)** — únic codi observat fins ara relacionat amb
  l'obertura d'espatlla que comenta l'Agus; no apareix a cap altra fitxa del lot.
- Mateixa família CAMISETA MANGA LARGA que BONITA i CAJA (tercera variant), amb `A`=40 i `D`=40
  idèntics a CAJA — a contrastar si és la mateixa base de patró amb detall d'espatlla diferent.

---

## MODEL 14 · "MUSTARD Top Màniga Ranglan"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)
**Nota d'Agus:** màniga ranglan (construcció d'espatlla/màniga diferent de la clàssica — coherent
amb `S2`=31,5 molt més gran que `S`=25,5, i amb els qualificadors "excluding collar binding" que
no apareixen a cap altra fitxa).

Sense grading — només talla S.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 49 |
| D | 1/2 bottom width relaxed | 50 |
| G1 | Bottom hem / Bottom rib height | 1,5 |
| E2 | Across front width (11cm from HPS) | 25 |
| E3 | Across back width (11cm from HPS) | 24 |
| EK | Neck width edge to edge including collar binding | 17 |
| EK1 | Front neck drop from HSP to edge including collar binding | 8 |
| EK2 | Back neck drop from HSP to edge including collar binding | 2 |
| EP | Collar binding width | 1,8 |
| F | Centre front length from HSP (incl hem/rib) | 57 |
| FF | Centre back length from HSP (incl hem/rib) | 56 |
| **Armhole** | | |
| SF | Sleeve depth from HPS to seam excluding collar binding | 25,5 |
| S | Front armhole along seam to seam excluding collar binding | 25,5 |
| S2 | Back armhole along seam to seam excluding collar binding | 31,5 |
| **Sleeves** | | |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 80 |
| J | 1/2 Bicep width | 20 |
| J1 | Sleeve opening relaxed | 10 |
| J3 | Sleeve hem / Sleeve cuff height | 1,5 |

Notes crues:
- **G1 hi torna a aparèixer**, mateix nom habitual — novè ús documentat.
- **EK/EK1/EK2 aquí porten el qualificador "including collar binding"**, i `SF`/`S`/`S2` porten
  "excluding collar binding" — vocabulari de precisió no vist enlloc més del lot; consistent amb
  que sigui una peça amb coll/binding que cal distingir de la costura d'aro.
- `S2` (31,5) molt més gran que `S` (25,5) — a la resta de fitxes S i S2 solen ser semblants
  (diferència d'1-2). Aquí la diferència és de 6, i l'Agus ho lliga a la construcció ranglan.
  Es guarda com a dada, no s'interpreta més.
- És la tercera fitxa amb "chest width" alt (A=49) després de l'animal (61) i BEYONCÉ (38,5) —
  sense grading, no es pot situar en quina talla real cauria.

---

## MODEL 15 · "NIAGARA Camiseta Màniga Llarga"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)
**Nota d'Agus:** coll desbocat (off-shoulder/ample) — coherent amb `EK`=31 (neck width edge to
edge), el més gran de totes les fitxes amb aquest camp, i amb la doble mesura de `E2`/`E22`
(relaxed vs total width) que no apareix a cap altra fitxa.

Sense grading — només talla S. Primera fitxa amb secció "Pleats" (plecs).

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 41 |
| D | 1/2 bottom width relaxed | 36,5 |
| G1 | Bottom hem / Bottom rib height | 1,5 |
| E2 | Across front width (11cm from HPS) relaxed | 33 |
| E22 | Across front width (11cm from HPS) total width | 38 |
| E3 | Across back width (11cm from HPS) | 31 |
| E | Shoulder to shoulder | 38 |
| E5 | Shoulder drop (from HSP to shoulder point) | 3 |
| E1 | Shoulder seam | 4,7 |
| E4 | Shoulder Forward | 0 |
| EK | Neck width edge to edge | 31 |
| EK1 | Front neck drop from HSP to edge | 5 |
| EK2 | Back neck drop from HSP to edge | 3 |
| F | Centre front length from HSP (incl hem/rib) | 52 |
| FF | Centre back length from HSP (incl hem/rib) | 52 |
| **Pleats** | | |
| B1 | First pleat distance from armhole seam | 6 |
| B2 | Distance between pleats | 5,5 |
| BW | Pleat depth | 3 |
| **Armhole** | | |
| SF | Sleeve depth | 21 |
| S | Front armhole along seam | 21 |
| S2 | Back armhole along seam | 21 |
| **Sleeves** | | |
| I | Sleeve length | 61 |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 81 |
| J | 1/2 Bicep width | 13,5 |
| J1 | Sleeve opening relaxed | 9 |
| J3 | Sleeve hem / Sleeve cuff height | 1,5 |

Notes crues:
- **G1 hi torna a aparèixer**, mateix nom habitual — desè ús documentat.
- **E22 és un codi nou** (no vist a cap de les 14 fitxes anteriors), aparellat amb E2 per donar
  dues mesures del mateix punt (relaxed/total) — probablement específic de peces amb coll ample
  on la caiguda de la tela importa. Es guarda tal qual.
- **B1/B2/BW ("Pleats")** és secció nova — cap altra fitxa del lot porta plecs. Nota: B/B1 com a
  codis ja s'havien vist a RUFFLES i AITANA però com "waist width" (peces de cintura), aquí B1 és
  "first pleat distance" — mateix codi B1, tercer significat diferent.
- **EK=31 és, de llarg, el valor més gran de tot el lot per aquest codi** (la resta ronden 15-25),
  quadra amb la nota d'Agus del coll desbocat.

---

## MODEL 16 · "PEGASO Top"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — només talla S.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 48 |
| D | 1/2 bottom width relaxed | 49,5 |
| G1 | Bottom hem / Bottom rib height | 1,5 |
| E2 | Across front width (11cm from HPS) | 38,5 |
| E3 | Across back width (11cm from HPS) | 37,5 |
| E | Shoulder to shoulder | 41 |
| E5 | Shoulder drop (from HSP to shoulder point) | 4,5 |
| E1 | Shoulder seam | 12,5 |
| E4 | Shoulder Forward | 0 |
| EK | Neck width seam to seam | 20 |
| EK1 | Front neck drop from HSP to seam | 8 |
| EK2 | Back neck drop from HSP to seam | 2,5 |
| EP | Collar rib height | 1,5 |
| F | Centre front length from HSP (incl hem/rib) | 55 |
| FF | Centre back length from HSP (incl hem/rib) | 55 |
| **Armhole** | | |
| SF | Sleeve depth | 22,5 |
| S | Front armhole along seam | 23,5 |
| S2 | Back armhole along seam | 23,5 |
| **Sleeves** | | |
| I | Sleeve length | 19,5 |
| J | 1/2 Bicep width | 21 |
| J1 | Sleeve opening relaxed | 18 |
| J3 | Sleeve hem / Sleeve cuff height | 1,5 |

Notes crues:
- **G1 hi torna a aparèixer**, mateix nom habitual — onzè ús documentat.
- **EK aquí torna al grup "seam to seam"** (com l'animal/KAYCE/TENDER/RUFFLES/MEREDITH/CAJA),
  no al grup "edge to edge" (BEYONCÉ/BONITA/LITTLE STAR/NIAGARA).
- `I` (Sleeve length) = 19,5, molt curt comparat amb totes les altres fitxes amb màniga llarga
  (54-64) — és una màniga curta/cap; `J1` (sleeve opening relaxed = 18) també és gran en relació
  a `J` (bicep = 21), típic de màniga curta ampla. Es guarda tal qual, no s'etiqueta el tipus de
  màniga perquè el document no ho diu explícitament.
- `EP` aquí és "Collar rib height" — ja havia aparegut com "Collarstand height at CB" (MEREDITH)
  i "Collar binding width" (CAJA, MUSTARD) i "Collar height" (BEYONCÉ, com a LZ no EP). Quart nom
  diferent pel mateix codi EP.

---

## MODEL 17 · "ROSALIA Top Tirants"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — només talla S.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 37 |
| D | 1/2 bottom width relaxed | 42 |
| G1 | Bottom hem / Bottom rib height | *(buit al document)* |
| F | Centre front length at CF | 34 |
| FF | Centre back length at CB | 30 |
| **CF Sequins piece** | | |
| U | Width sequins piece | 4 |
| U1 | Height sequins piece | 10 |
| **Chest piece** | | |
| P | Height at side seam | 10 |
| P1 | Height at the center | 21 |
| **Cord** | | |
| LZ | Cord width | 0,5 |
| LZ1 | Cord length | 75 |

Notes crues:
- **G1 hi surt però sense valor** — dotzè cop que apareix el codi, primer cop buit. Es guarda com
  a buit, no com a 0 (a diferència d'altres fitxes on 0 és un valor real, p.ex. E4=0).
- **LZ/LZ1 ja havien aparegut a SUSI i BEYONCÉ**, tots dos cops amb significat de cordó/coll però
  ordre i unitat diferents: aquí LZ=width (0,5) i LZ1=length (75); a SUSI LZ=length (185) i
  FZ=width (0,7, codi diferent); a BEYONCÉ LZ=Collar height (4) i LZ1=Collar bow length (118).
  Tercer parell de significats pel mateix parell de codis LZ/LZ1.
- **U/U1 ("Sequins piece")** ja havien aparegut a MILEY amb el mateix nom exacte ("Sequins piece
  height" per U1) — primera coincidència neta de secció sencera entre dues fitxes d'estils
  diferents.
- Secció nova "Chest piece" (P/P1) no vista abans.

---

## MODEL 18 · "TWIST Top"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)
**Nota d'Agus:** obertura sobre el pit — coherent amb la secció nova "Cut out" (CO).

Sense grading — només talla S.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 35 |
| D | 1/2 bottom width relaxed | 35 |
| G1 | Bottom hem / Bottom rib height | 1,5 |
| E2 | Across front width (11cm from HPS) | 29 |
| E3 | Across back width (11cm from HPS) | 30 |
| E | Shoulder to shoulder | 32 |
| E5 | Shoulder drop (from HSP to shoulder point) | 3 |
| E1 | Shoulder seam | 7 |
| E4 | Shoulder Forward | 1 |
| EK | Neck width seam to seam | 16 |
| EK1 | Front neck drop from HSP to seam | 9 |
| EK2 | Back neck drop from HSP to seam | 2 |
| F | Centre front length from HSP (incl hem/rib) | 54 |
| FF | Centre back length from HSP (incl hem/rib) | 53 |
| **Armhole** | | |
| S | Front armhole along seam | 22 |
| S2 | Back armhole along seam | 21,5 |
| **Sleeves** | | |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 81 |
| J | 1/2 Bicep width | 13,5 |
| J1 | Sleeve opening relaxed | 9 |
| J3 | Sleeve hem / Sleeve cuff height | 1,5 |
| **Cut out** | | |
| CO | Cut out from HPS | 17,5 |

Notes crues:
- **G1 hi torna a aparèixer**, mateix nom habitual — tretzè ús documentat.
- **EK torna al grup "seam to seam"**, com PEGASO/animal/KAYCE/etc.
- **CO ja havia aparegut a LITTLE STAR** ("Cut out from shoulder seam at the front/back", secció
  "Sleeve cut out", 3 codis CO/CO1/CO2 per l'espatlla). Aquí és un sol codi CO amb descripció
  diferent ("Cut out from HPS", secció "Cut out" a seques) — mateix codi arrel, dues obertures de
  disseny diferents (espatlla vs pit). Consistent amb la nota de l'Agus.

---

## MODEL 19 · "RICHARD Trousers"

**Marca:** Brownie · **Color:** Azul · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — només talla S.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| B | 1/2 waist width | 37 |
| BF | Waistband height | 8,5 |
| FC | Hip position from top edge | *(buit al document)* |
| C | 1/2 hip width | 43,5 |
| CT | 1/2 thigh width | 34 |
| M | 1/2 leg opening width | 27,5 |
| M1 | Bottom height | 2 |
| FT | Pants total length | 104 |
| F1 | Inseam length | 82 |
| FR | Front rise (excl. waistband) | 29 |
| FE | Back rise (excl. waistband) | 38 |

Notes crues:
- Mateix vocabulari exacte de codis que AITANA (B, BF, FC, C, CT, M, M1, FT, F1, FR, FE) — la
  parella més neta de tot el lot per contrastar directament, codi a codi i nom a nom, quan es
  faci la comparació.
- `FC` sense valor — únic buit d'aquesta fitxa.

---

## MODEL 20 · "LEIXI Dress"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)
**Nota d'Agus:** sense tirants ni coll — coherent amb l'absència de codis EK/E/E1... (coll i
espatlla) i la presència de "Back top width relaxed/stretched out" (A2/A3), típic de peça
sense tirant fix.

Sense grading — només talla S.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 37 |
| A2 | Back top width relaxed | 34 |
| A3 | Back top width stretched out | 55 |
| FB | TOP: Centre front length (visible) | 33 |
| FB1 | TOP: Centre back length (visible) | 30 |
| FB2 | TOP LINING: Centre front length (visible) | 30 |
| FB3 | TOP LINING: Centre back length (visible) | 27 |
| **Skirt** | | |
| B | 1/2 waist width relaxed | 37,5 |
| B1 | 1/2 waist width stretched out | 45 |
| BF | Waistband height | 5 |
| D | 1/2 bottom width | 60 |
| G1 | Bottom hem | 0,3 |
| F | Total length at CF | 66 |
| FF | Total length at CB | 67 |

Notes crues:
- **G1 hi torna a aparèixer**, aquí curt ("Bottom hem", sense "/ Bottom rib height") — catorzè
  ús documentat del codi, i el nom més escurçat de tots.
- **FB/FB1/FB2/FB3** són codis nous, amb el patró "TOP" vs "TOP LINING" (exterior/folre) explícit
  al mateix nom — primera fitxa que distingeix folre al nom del codi en lloc d'una secció a part.
- `B`/`B1` aquí són "waist width" com a RUFFLES/AITANA/NIKITA (grup peces de cintura), no com a
  "pleat distance" (NIAGARA) — encaixa amb el grup majoritari per aquest codi.
- Peça combinada top+skirt (vestit) amb vocabulari de les dues famílies alhora — bon cas per la
  comparació de "quin GTI/família hauria de mapar aquesta fitxa".

---

## MODEL 21 · "OWEN Blusa"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — només talla S.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 46 |
| D | 1/2 bottom width relaxed | 48 |
| G1 | Bottom hem / Bottom rib height | 1,5 |
| E2 | Across front width (11cm from HPS) | 33 |
| E3 | Across back width (11cm from HPS) | 34,5 |
| E | Shoulder to shoulder | 37 |
| E5 | Shoulder drop (from HSP to shoulder point) | 4 |
| E1 | Shoulder width at true shoulder | 10,5 |
| E4 | Shoulder Forward | 1,5 |
| EK | Neck width seam to seam | 16 |
| EK1 | Front neck drop from HSP to seam | 7,5 |
| EK2 | Back neck drop from HSP to seam | 2 |
| LZ1 | Total cord length | 135 |
| F | Centre front length from HSP (incl hem/rib) | 52,5 |
| FF | Centre back length from HSP (incl hem/rib) | 52,5 |
| **Collar** | | |
| EP | Collarstand height at CB | 5,5 |
| U2 | First button measured from top | 1 |
| U3 | Last button measured from collar seam | 1 |
| **Armhole** | | |
| SF | Armhole depth from HPS | 24 |
| S | Front armhole along seam | 22 |
| S2 | Back armhole along seam | 24,5 |
| **Sleeves** | | |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 81 |
| J | 1/2 Bicep width | 19 |
| J1 | Sleeve opening relaxed | 14 |
| **Front opening** | | |
| O | Front opening length | 14 |

Notes crues:
- **G1 hi torna a aparèixer**, mateix nom habitual — quinzè ús documentat.
- **EK torna al grup "seam to seam"**.
- **EP aquí és "Collarstand height at CB"**, coincidència literal amb MEREDITH (mateix nom exacte)
  — segona coincidència neta de nom per aquest codi (els altres eren "binding width"/"rib height"
  /"collar height").
- **U2/U3 (botons) són codis nous** — primera fitxa amb mesures de posició de botonadura.
- Codi de "front opening length" torna a estar escrit com `0` (zero) — cinquè cop que passa aquest
  patró tipogràfic (MEREDITH, TENDER, BONITA, i ara OWEN), es guarda com `O` pel mateix motiu.
- `LZ1` aquí és "Total cord length" (sol, sense LZ) — quart significat vist pel codi LZ1 (SUSI:
  cord length del parell LZ/FZ; BEYONCÉ: collar bow length; ROSALIA: cord length del parell
  LZ/LZ1). Coincideix amb SUSI en el concepte (cordó) però aquí no hi ha LZ parella.

---

## MODEL 22 · "LLOYD Blusa"

**Marca:** Brownie · **Color:** Azulón · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)

Sense grading — només talla S.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 47,5 |
| D | 1/2 bottom width relaxed | 51 |
| G1 | Bottom hem / Bottom rib height | 0,5 |
| E2 | Across front width (11cm from HPS) | 34 |
| E3 | Across back width (11cm from HPS) | 36 |
| E | Shoulder to shoulder | 37 |
| E5 | Shoulder drop (from HSP to shoulder point) | **?** |
| E1 | Shoulder seam | 10,5 |
| E4 | Shoulder Forward | 1,5 |
| EK | Neck width seam to seam | 16 |
| EK1 | Front neck drop from HSP to seam | 21,5 |
| EK2 | Back neck drop from HSP to seam | 1,5 |
| F | Centre front length from HSP (incl hem/rib) | 54 |
| FF | Centre back length from HSP (incl hem/rib) | 54 |
| **Frilling** | | |
| VL | End of frill at the seam measured from HPS | 36 |
| VL1 | End of bottom frilling at CF measured from HPS | 40 |
| V | Side frill width measured at the shoulder seam | 3,5 |
| V1 | Top Front frill width measured at CB | 4 |
| V2 | Bottom Front frill width measured at CB | 5,5 |
| **Armhole** | | |
| S | Front armhole along seam | 23,5 |
| S2 | Back armhole along seam | 22,5 |
| **Sleeves** | | |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 81 |
| J | 1/2 Bicep width | 16 |
| J1 | Sleeve opening relaxed | 9 |
| J2 | Sleeve opening stretched out | 15 |
| J3 | Sleeve hem / Sleeve cuff height | 0,8 |
| **Front opening** | | |
| O | CF slit | 10 |

Notes crues:
- **`E5` porta literalment `?` al document** — es guarda tal qual, no s'interpreta com a buit ni
  com a 0. Únic cas de valor "signe d'interrogament" de tot el lot.
- **`EK1`=21,5 crida l'atenció**: a totes les altres fitxes amb aquest codi ("Front neck drop from
  HSP to seam"), els valors ronden 5-9,5. Aquí és 21,5, més del doble/triple. Es guarda literal —
  podria ser una peça amb escot molt pronunciat o un error de transcripció del document, no es
  decideix aquí.
- **G1 hi torna a aparèixer**, mateix nom habitual — setzè ús documentat.
- **EK torna al grup "seam to seam"**.
- **Secció "Frilling" (VL/VL1/V/V1/V2)** és nova respecte a totes les fitxes anteriors, tot i que
  `V`/`VL` individualment ja havien sortit (MEREDITH: "Frill width at the shoulder"/V, "End of
  FRONT frill..."/VL — descripcions molt semblants, bon parell per contrastar) i TENDER (V =
  "Ruffle at the hem", significat diferent).
- Codi de "front opening" torna a estar escrit `0` (zero) — sisè cop (després de MEREDITH,
  TENDER, BONITA, OWEN); es guarda com `O`.

---

## MODEL 23 · "JAMIE Blusa"

**Marca:** Brownie · **Sample size:** S · **Temporada:** WINTER 2027
**Font:** fitxa tècnica (Agus, xat 2026-08-06) · **Unitats:** cm (assumit)
**Nota:** capçalera de columna diu "GRADING" però la columna de grading és buida i només hi ha
`S` amb valor — igual que a la resta de fitxes sense grading real. Es guarda sense grading.

Molt semblant a KAYCE (mateixos valors A, D, G1, E2, E3, E, E5, E1≈, EK, EK1, EK2, F, FF, SF, S,
S2, I4, J, J1, J2, J3 — pràcticament idèntica), però sense M/M1/M2 (front piece/lace) i amb
seccions noves: "Front yoke" (P1) i "V" (frill at armhole, sense valor).

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| **Bodice** | | |
| A | 1/2 chest width (armpit to armpit) | 50 |
| D | 1/2 bottom width relaxed | 61 |
| G1 | Bottom hem / Bottom rib height | 0,5 |
| E2 | Across front width (11cm from HPS) | 33 |
| E3 | Across back width (11cm from HPS) | 34,5 |
| E | Shoulder to shoulder | 34 |
| E5 | Shoulder drop (from HSP to shoulder point) | 1,5 |
| E1 | Shoulder width at true shoulder | 8 |
| E4 | Shoulder Forward | 2 |
| EK | Neck width seam to seam | 18 |
| EK1 | Front neck drop from HSP to seam | 8,5 |
| EK2 | Back neck drop from HSP to seam | 2 |
| F | Centre front length from HSP (incl hem/rib) | 56 |
| FF | Centre back length from HSP (incl hem/rib) | 56 |
| **Armhole** | | |
| SF | Armhole depth from HPS | 22 |
| S | Front armhole along seam | 24,5 |
| S2 | Back armhole along seam | 26,5 |
| **Sleeves** | | |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 81 |
| J | 1/2 Bicep width | 20 |
| J1 | Sleeve opening relaxed | 9 |
| J2 | Sleeve opening stretched out | 18 |
| J3 | Sleeve hem / Sleeve cuff height | 0,5 |
| V | Frill at the armhole measured at the shoulder | *(buit al document)* |
| **Front yoke** | | |
| P1 | Front yoke side height from HPS | 22 |
| **Back yoke** | | |
| L | Back yoke height at CB | 16 |

Notes crues:
- **Parella clara amb KAYCE** (Model 3): mateixos codis i valors idèntics a A, D, G1, E2, E3, E,
  E5, EK, EK1, EK2, F, FF, SF, S, S2, I4, J, J1, J2 — probablement la mateixa base de patró amb
  variant de coll/espatlla (E1 "shoulder width at true shoulder"=8 aquí vs "shoulder seam"=8 a
  KAYCE — noms de camp diferents, valor igual) i acabats diferents (KAYCE porta M/M1/M2 + Back
  yoke L/L2 + Back opening; JAMIE porta Front yoke P1 + V buit).
- **L aquí és "Back yoke height at CB"**, a KAYCE L és "Back yoke CB height from top edge" —
  mateix codi, redacció diferent, per confirmar si és el mateix punt de mesura.
- **G1 hi torna a aparèixer**, mateix nom habitual — dissetè ús documentat.

---

## MODEL 24 · "PEPA" (BRW-SS27-0003 · Pant · SS 2027)

**Font:** captura de pantalla (Agus, xat 2026-08-06) · **Unitats:** cm · **Talla:** S (BASE)

⚠️ **Format molt diferent de les 23 fitxes anteriors**: no és un document client cru — porta
capçalera d'estil propi (targeta amb títol, referència `BRW-SS27-0003`, tipus de peça "Pant",
temporada), taula amb seccions netes en majúscula, i peu de pàgina "Measured at fitting
30/07/2026 · client nomenclature · 13 points of measure". Es guarda igualment, tal com ve, però
**s'anota la diferència de font sense interpretar-la** (podria ser una taula ja processada pel
sistema/algú, no una fitxa original del client). A confirmar quan toqui la comparació.

| CODI | POM | BASE · S |
|---|---|---|
| **Waist & waistband** | | |
| B | Waist width | 35,5 |
| BF | Waistband height | 4 |
| **Hip & thigh** | | |
| C | Hip width | 48 |
| CT | Thigh width | 30 |
| **Lengths & bottom** | | |
| FT | Pants length (outseam) | 102 |
| FI | Inseam length | 77,5 |
| D | Bottom width (leg opening) | 29 |
| G1 | Bottom hem height | 1,5 |
| **Rise** | | |
| FD | Front rise length (waistband included) | 26 |
| FE | Back rise length (waistband included) | 36,5 |
| **Pockets** | | |
| R2 | Pocket width | 12 |
| PR1 | Pocket position from side seam | 10 |
| PR2 | Pocket position from waistband | 10 |

Notes crues:
- **G1 hi torna a aparèixer**, aquí "Bottom hem height" — divuitè ús documentat.
- Codis PR1/PR2 ja havien aparegut a NIKITA (Model 6) amb noms similars ("back pocket position").
  Aquí sense "back", coherent si aquest pantaló no distingeix davant/darrere per a la butxaca.
- Referència pròpia `BRW-SS27-0003` — primer cop que una entrada d'aquest lot porta un codi de
  model real Brownie (les 23 anteriors eren totes fitxes sense referència).

---

## MODEL 25 · "SUZIE" (BRW-SS27-0001 · Vest · SS 2027)

**Font:** captura de pantalla (Agus, xat 2026-08-06) · **Unitats:** cm · **Talla:** S (BASE)

Mateix format "targeta" que PEPA (veure avís de Model 24). Peu: "Measured at fitting 30/07/2026
· client nomenclature · 14 points of measure".

| CODI | POM | BASE · S |
|---|---|---|
| **Widths, neck & shoulders** | | |
| A | 1/2 chest width (armpit to armpit) | 44 |
| E2 | Across front width (11cm from HPS) | 26,5 |
| E3 | Across back width (11cm from HPS) | 29 |
| E | Shoulder to shoulder | 30 |
| E1 | Shoulder width at true shoulder | 9,5 |
| E5 | Shoulder drop (from HPS to shoulder point) | 5,5 |
| E4 | Shoulder forward | 1,5 |
| EK | Neck width seam to seam | 10,5 |
| SF | Armhole depth from HPS | 24,5 |
| S | Front armhole along seam | 23 |
| S2 | Back armhole along seam | 28 |
| **Lengths** | | |
| F | Centre front length from HPS | 56 |
| FF | Centre back length from HPS | 54 |
| **Fixed** | | |
| EK3 | Back neck drop length at collar | 10 |

Notes crues:
- Peça "Vest" (armilla, sense mànigues) — coherent amb l'absència de codis J/J1/I de màniga.
- **EK3 és codi nou** (no vist a cap de les 23 fitxes anteriors), diferent d'EK1/EK2 que ja tenen
  significat fixat ("front/back neck drop from HPS to seam"). Aquí EK3 = "Back neck drop length
  at collar" — a confirmar si és el mateix concepte que EK2 amb un altre nom o una mesura pròpia.
- Referència `BRW-SS27-0001`.

---

## MODEL 26 · "MANDI" (BRW-SS27-0002 · Chaqueta · SS 2027)

**Font:** captura de pantalla (Agus, xat 2026-08-06) · **Unitats:** cm · **Talla:** S (BASE TALLA)

Mateix format "targeta" que PEPA/SUZIE, però **en català** (CODI/POM/TALLA S en lloc de
CODE/POM/BASE S) — primer document del lot en català, la resta sempre en anglès/castellà. Peu:
"Mesures preses al fitting del 30/07/2026 · nomenclatura de client · 27 punts de mesura".

| CODI | POM | BASE · S |
|---|---|---|
| **Amplades i contorns** | | |
| A | 1/2 chest width (armpit to armpit) | 49 |
| B | 1/2 waist width | 46 |
| BT | Waist position from HPS | 36 |
| D | 1/2 bottom width relaxed | 50 |
| E2 | Across front width (11cm from HPS) | 35,5 |
| E3 | Across back width (11cm from HPS) | 39 |
| E | Shoulder to shoulder | 41 |
| E5 | Shoulder drop (from HPS to shoulder point) | 4 |
| E1 | Shoulder width at true shoulder | 11,5 |
| E4 | Shoulder forward | 1,5 |
| EK | Neck width seam to seam | 17,5 |
| EK1 | Front neck drop from HPS to seam | 10 |
| EK2 | Back neck drop from HPS to seam | 2 |
| SF | Armhole depth from HPS | 26 |
| S | Front armhole along seam | 26 |
| S2 | Back armhole along seam | 25 |
| J | 1/2 Bicep width | 17,5 |
| J1 | Sleeve opening relaxed | 14 |
| **Llargs i màniga** | | |
| F | Centre front length from HPS | 67 |
| FF | Centre back length from HPS | 65,5 |
| F1 | Curve at side (difference between CB length and side seam) | 24,5 |
| I | Sleeve length | 61 |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 83 |
| **Fixos** | | |
| EP | Collar height at CB | 5 |
| **Col·locacions i detalls** | | |
| PKT D | Pocket length | 14 |
| PKT S | Pocket placement from side seam | 1 |
| PKT CF | Pocket placement from CF | 9,5 |

Notes crues:
- **BT és codi nou** ("Waist position from HPS") — no vist a cap fitxa anterior.
- **PKT D / PKT S / PKT CF** és una nomenclatura de butxaca amb prefix `PKT` en lloc dels codis
  R/R1-R4/PR1-PR3 vists a l'animal, RUFFLES i NIKITA — tercer sistema de nomenclatura de butxaca
  diferent al lot.
- **EP aquí és "Collar height at CB"** — un cinquè nom pel codi EP (ja portava "Collarstand height
  at CB" a MEREDITH i OWEN, "Collar binding width" a CAJA/MUSTARD, "Collar rib height" a PEGASO).
- Referència `BRW-SS27-0002`.

---

## MODEL 27 · "LEA Chaqueta de pell"

**Marca:** Brownie (assumit) · **Sample size:** S · **Font:** fitxa tècnica (Agus, xat 2026-08-06)
**Unitats:** cm (assumit) · Sense capçalera de metadades i sense grading.

| CODI | DESCRIPCIÓ (EN) | S |
|---|---|---|
| A | 1/2 chest width (armpit to armpit) | 50 |
| B | 1/2 waist width | 45,5 |
| D | 1/2 bottom width relaxed | 49 |
| E2 | Across front width (11cm from HPS) | 34,5 |
| E3 | Across back width (11cm from HPS) | 37,5 |
| E | Shoulder to shoulder | 40,5 |
| E5 | Shoulder drop (from HPS to shoulder point) | 7 |
| E1 | Shoulder width at true shoulder | 11,5 |
| E4 | Shoulder forward | 1 |
| EK | Neck width seam to seam | 18 |
| F | Centre front length from HPS stretched out | 64 |
| SF | Armhole depth from HPS | 22 |
| S | Front armhole along seam | 26 |
| I | Sleeve length | 65,5 |
| I4 | Sleeve length from CB over shoulderpoint (incl cuff) | 86,5 |
| J | 1/2 Bicep width | 17 |
| J4 | Elbow position measured from CB over shoulderpoint | 58 |
| JJ | 1/2 Elbow width | 16 |
| J3 | Sleeve hem height | 3 |
| B0 | First button position | 28 |
| A1 | Pocket position from side | 1,5 |
| A2 | Pocket position from CF | 10 |
| A3 | Pocket position from bottom | 20 |
| B1 | Pocket flap width | 14 |
| B2 | Pocket flap width | 7 |

Notes crues:
- Quart sistema de nomenclatura de butxaca del lot: `A1/A2/A3` (posició) i `B1/B2` (solapa),
  després de R/R1-R4/RR, PR1-PR3 i PKT D/S/CF.
- `A1`, `A2`, `A3`, `B1`, `B2` xoquen frontalment amb els seus usos anteriors (A1 = 1/2 back chest
  width a MILEY; A2/A3 = back top width a LEIXI; B1 = waist width extended a RUFFLES/AITANA i
  = first pleat distance a NIAGARA). Deriva forta del tècnic.
- `B0` (posició del primer botó) i `J4`/`JJ` (colze) són codis nous en aquest lot.

---

## PENDENT (per quan hi hagi prou models)

- Comparar codi a codi contra `BROWNIE_CATALEG_POM_v3.xlsx` full `CATALEG` (119 codis, columna
  `pom_id`, `LÒGICA`, `RÈGIM`, `FAM.`): quins codis d'aquestes fitxes no existeixen al v3, quins
  hi existeixen amb un altre nom, i si el grading (Δ) coincideix amb els deltes del v3 o els
  contradiu.
- Decidir amb l'Agus/Montse si aquestes fitxes són la FONT REAL que hauria d'ajustar el v3, o
  si el v3 ja és la llei i aquestes són per validar-lo.
- Cap d'aquestes dades s'ha sembrat enlloc. Són matèria primera fins que es decideixi.
