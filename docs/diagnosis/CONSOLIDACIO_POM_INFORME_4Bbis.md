# PAS 4B-bis — Tancament de la consolidació POM (informe)

> Staging · `fhort` · dev. Data: 2026-07-19. Dades només, dry-run primer, motor NO tocat,
> 72 prims sense àlies LOS intactes. NO push. Command `consolidate_pom_catalog --phase
> {maps,fixcoll,translate}`. CSVs: `pom_item_maps_los.csv` + `traduccions_pom_los.csv`.

## Resum

| acció | resultat |
|---|---|
| **maps** | 197 GarmentPOMMap creats (pendent_revisio) + **13 POMs NOUS** (LOS-local, traduïts, amb àlies) |
| **fixcoll (K.2)** | 1 mesura òrfena de col·lisió esborrada (id431, ara base_measurements=0) |
| **translate retry** | 69 COMPLETAR segueixen sense cobertura CSV → llista literal (avall) |

## 1. MAPS (pom_item_maps_los.csv · 87 files)

Cada POM del CSV entra als `GarmentPOMMap` dels items on les fitxes LOSAN l'usen (matching per
àlies LOS + codi, variants de puntuació). **197 GarmentPOMMap** nous (`pendent_revisio=True`).
Total GarmentPOMMap del tenant: 1734.

**POMs NOUS creats (13)** — files marcades `[POM NOU]`/`[gap]`, sense POM exacte previ: es crea
POMMaster LOS-local + POMGlobal (`LOSPOM-<id>`, traducció del CSV) + àlies LOS:

| codi | ca | families |
|---|---|---|
| S.19 · S.20 · S.39 · S.40 | Llargada/Ample/Posició/Llargada-davant de peu | baby_sleepsuit |
| B4 · E.1 · E.2 · M.1 · R.1 · R.3 | pit esquena · baixos davant/esquena · llargada davant · tirant llargada/posició | bikini, swimsuit |
| Z · SR9 · SR10 | volant · llaç ample/llargada | dress_simple |

> Reuse per **codi EXACTE** (sense variants): evita casar `E.1`→`E1`(Shoulder seam) o l'àlies
> preexistent `SR9`→JJ. Només `B3` (existia exacte) es va reutilitzar (no duplicat).

**7 codes del CSV referenciats però SENSE POM i no marcats `[gap]`** → NO creats (no inventar),
per completar al gate: `S.35` (collar piece) · `C.13` (buttonhole) · `S.R6`/`S.R7` (loops) ·
`V.9` (elastic loc) · `CB` (front cut) · `EV` (waist stitching). (Recomanació: marcar-los
`[gap]` al CSV o afegir-los al diccionari.)

## 2. FIXCOLL — K.2

L'única col·lisió de la fusió (K.2→AC SH: un model ja tenia AC SH) deixava 1 `BaseMeasurement`
òrfena al prim desactivat id431. Esborrada (`--phase fixcoll`). Verificat: id431
`base_measurements=0`. `regles_grading=6` es queden (moren al PAS 3).

## 3. TRADUCCIONS — 69 COMPLETAR encara sense cobertura

Reintent contra `traduccions_pom_los.csv` amb variants: **0 nous** (cap d'aquests codes hi és).
Llista literal (codi · descripció EN · àlies LOS) per ampliar el CSV al gate següent:

- **Butxaques** (no al maps CSV tampoc): `O9`/`O11`/`O12`/`O13`/`O14` (chest pocket) · `O17`
  (front pocket flap height) · `O28` (back pocket flap width) · `O33`/`O34` (coin pocket) ·
  `O36`/`O38`/`O39`/`O40`/`O41` (side pocket) · `W4`/`W5`/`W6`/`W7`/`W9` (inner pocket) ·
  `O.27-M79` (back pocket flap height).
- **Canesús**: `S27` (front yoke center) · `S28` (front yoke) · `S30` (back yoke).
- **Coll/tapeta**: `S` (collar height on top) · `S8` (collar opening ext) · `S34` (front cover
  width) · `S45` (back opening) · `AB` (contour collar total).
- **Puny/mànega**: `GL` (cuff opening inner) · `GM` (cuff difference) · `GN` (cuff height inner)
  · `H14` (sleeve opening ext) · `H7` (armhole point loc) · `H8` (front armhole) · `H9` (back
  armhole) · `G5` (elbow location).
- **Cintura/baixos/camal**: `C2` (front waist relaxed) · `C3` (waist location) · `C5` (back
  waist relaxed) · `C6` (back waist ext) · `E3`/`E4` (bottom width relaxed/ext) · `E5` (front
  bottom width) · `E7` (bottom height) · `F1`/`F2` (front/back leg opening).
- **Caputxa/cordó/plec/pinça/volant/peça**: `S54`/`S55` (hood length relaxed/ext) · `SR2`
  (drawstring length) · `SR3` (drawstring channel) · `T13` (pleat location) · `T14` (pleat) ·
  `V.13-M79` (dart length) · `V.14-M79` (dart location) · `U4` (flounce height) · `U7` (frill
  height) · `V4`/`V5`/`V6`/`V7` (piece width/ext/length/location).
- **Localitzacions/altres**: `A` (front width location) · `A3` (back width location) · `FP`
  (shoulder piece width) · `MF` (side seam moved forward) · `N4` (side opening) · `JC` (tape
  width) · `C.14-M79` (eyelet location) · `J1` (shoulder drop location + un 'Sleeve opening
  relaxed' via àlies H13).

## Verificació final

- **cap `CustomerPOMAlias` de LOS resol a un POM desactivat** ✓ (0).
- POMMaster: **332 actius** (319 + 13 nous) · 16 desactivats · **191 traduïts** (178 + 13).
- GarmentPOMMap: **1734** (+197) · K.2 id431 `base_measurements=0` ✓.
- `manage.py check` net · servei `ftt-staging.service` reiniciat.
- Idempotència: reuse per codi exacte + `get_or_create` (POM/POMGlobal/àlies/GarmentPOMMap).

## Pendents d'OK d'Agus / Montse
1. **Traducció ca dels 69 COMPLETAR** de dalt (ampliar `traduccions_pom_los.csv`).
2. **7 codes del maps CSV sense POM** (S.35/C.13/S.R6/S.R7/V.9/CB/EV) → marcar `[gap]` o
   afegir al diccionari perquè es creïn i mapin.
3. Els **72 prims sense àlies LOS** (altres imports, dades vives) segueixen intactes.
