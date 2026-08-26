# Dry-run de `seed_semantic_catalog` — la llista que l'Agus ha de validar

**Data:** 2026-08-26 · **Tram:** F3 · Patró B · **Estat:** ⏸️ **ATURAT esperant OK**
**Comanda:** `python manage.py seed_semantic_catalog --dry-run --llista`
**Fonts:** vocabulari = `docs/diagnosis/REPORT_GCD_ONTOLOGY_2026-08-25.md`
(GarmentCode@d449629, MIT) · freqüències = `ftt_corpus` (128.974 designs, CC-BY-4.0),
llegit en **read-only** amb `corpus_ro` + connexió `readonly=True`.

> **Res d'això s'ha escrit encara.** Les migracions SÍ estan aplicades (les taules
> existeixen, buides, als tres esquemes); el que espera l'OK és el CONTINGUT.

---

## 0 · Què s'escriuria, en quatre xifres

| taula | files | a quants esquemes | origen |
|---|---:|---|---|
| `pom_edgerole` | **27** | public · fhort · los | SEED · `is_system=True` · `pendent_revisio=False` |
| `pom_landmarkrole` | **8** | public · fhort · los | SEED · `is_system=True` · `pendent_revisio=False` |
| `pom_seampairtemplate` | **53** | public · fhort · los | IMPORT · `is_system=True` · **`pendent_revisio=True`** |
| `pom_gcpiecerolemap` | **24** | public · fhort · los | — |
| `pom_garmenttypeitemedgeprofile` | **0** | — | **buida a posta** (vegeu §5) |

Total: **112 files × 3 esquemes = 336 files.** Cap `DELETE`, cap `UPDATE` sobre res que
no hagi sembrat aquesta mateixa comanda.

---

## 1 · Les tres coses que vull que miris primer

### 1.1 🚨 El corpus va tapar un forat de la meva pròpia llista

La llista de plantilles surt de les 22 regles de costura del codi (informe §4.2). Un cop
mesurada contra el corpus, **quatre parelles reals no les recollia cap plantilla**, i la
més gran era enorme: `cuff/front ↔ cuff/back`, **241.004 costures en 47.912 patrons**.

No era vocabulari nou: **era la regla #16 mal acotada per mi.** #16 és
`bands.py:73-75`, les costures laterals d'un `StraightBandPanel` — i la cinturilla no és
l'únic panell d'aquella classe: **un puny també és una banda**, i es tanca amb les
mateixes dues costures. Afegida com a fila #24.

El mateix va passar, més petit, amb el creuat del puny de cama (#14: `pant_bottom` és una
interfície múltiple). Les tres files noves són `#16-cuff` i els dos creuats de `#14`.

> 🔑 **La lliçó operativa:** el cens del corpus no serveix només per omplir columnes de
> freqüència — **serveix per auditar la llista del vocabulari**. Una parella òrfena amb
> 241.000 costures no és soroll: és una regla que et vas deixar. Per això la llista
> d'òrfenes es queda a la comanda (`--llista` l'imprimeix sempre) i no és un fitxer d'un dia.

### 1.2 🚨 Un ZERO és una mesura, i n'hi ha dos que valen com una troballa

Dues plantilles surten a **0 de 128.974**, i el seu mirall no:

| plantilla | patrons | el seu mirall | patrons |
|---|---:|---|---:|
| `back/back.armhole ↔ sleeve/front.sleeve_cap` | **0** | `front/front.armhole ↔ sleeve/back.sleeve_cap` | 35.121 |
| `cuff/back.band_attach_upper ↔ pant/front.cuff_line` | **0** | `cuff/front… ↔ pant/back…` | 3.673 |

El cap de màniga travessa l'espatlla, o sigui que la **meitat del darrere** de la màniga
cus també contra la sisa del **davant** — però mai al revés. És una asimetria del
generador, no una llei d'ofici, i queda registrada com a xifra i no com a absència:
`observed_seams=0`, `observed_den=90.273`, i `observed_ref` diu literalment
`ZERO MESURAT`. **NULL vol dir «no s'ha mirat»; aquí s'ha mirat tot.**

### 1.3 🚨 El test va trobar que el `UNIQUE` no protegia RES

La convenció d'ordenació estava implementada (`ordena()` + `canonitza()` a `save()`) i el
`UniqueConstraint` sobre les 8 columnes escrit. **El test va escriure la mateixa costura
dues vegades, girada, i la segona va ENTRAR.**

`garment_type_item` és nul·lable i a Postgres **dos NULL no són iguals**: un `UNIQUE` que
el porti a la clau no casa mai quan la columna és NULL. I genèriques —`garment_type_item
= NULL`— ho són **les 53 files que aquesta sembra escriuria**. El pany hi era i no tancava
cap porta.

És la mateixa llei que ja ens va mossegar a `ftt-diagnosi-pre-sembra-v4`: *una FK
nul·lable a la clau trenca la unicitat EN SILENCI*. Partit en dues constraints parcials
(`WHERE garment_type_item_id IS NULL` / `IS NOT NULL`), migració `0085`, verificat amb
`\d` als tres esquemes.

> 🔑 Un test d'igualtat que no has vist VERMELL no val: aquest va donar
> `IntegrityError not raised`, que és exactament la frase que calia veure.

### 1.4 🚩 Dues parelles reals que l'ontologia NO sap anomenar

Queden dues òrfenes, i no s'inventa cap slug per tapar-les:

| parella | costures | patrons | què és |
|---|---:|---:|---|
| `centre · collar/back ↔ collar/back` | 16.296 | 16.296 | les dues meitats mirall del coll del darrere, unides al centre |
| `centre · collar/front ↔ collar/front` | 7.077 | 7.077 | idem, al davant |

§2.4 de l'informe té `collar_side_seam` (costat) i `collar_outer_edge` (vora exterior),
però **cap slug per al centre del coll**. Fer-ne un ara seria inventar vocabulari sense
evidència de codi. **Va a la llista de la Montse**, no a la sembra.

---

## 2 · `EdgeRole` — 27 files

Les 24 anatòmiques d'§2.4 més les 3 estructurals. `needs_piece_role=SÍ` marca les vores
POLISÈMIQUES d'§2.2: a GarmentCode `bottom` és cintura en un cos, baix en una faldilla,
línia de puny en una màniga i vora d'unió en una cinturilla. **Aquestes no es poden llegir
soles.**

| # | slug | zone | kind | mates | needs_piece_role | nom_en | nom_ca | nom_es | source_ref |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `neckline` | neck | opening | collar_attach |  | Neckline | Escot | Escote | `GarmentCode@d449629 bodice.py:351; collars.py:12-88` |
| 2 | `collar_attach` | neck | seam | neckline |  | Collar attach | Unió de coll | Unión de cuello | `GarmentCode@d449629 collars.py:169,259; bodice.py:333` |
| 3 | `collar_outer_edge` | neck | finished | -- | SI | Collar outer edge | Vora exterior del coll | Borde exterior del cuello | `GarmentCode@d449629 bands.py:24` |
| 4 | `collar_side_seam` | neck | seam | collar_side_seam | SI | Collar side seam | Costura lateral del coll | Costura lateral del cuello | `GarmentCode@d449629 collars.py:161-163` |
| 5 | `hood_attach` | neck | seam | neckline |  | Hood attach | Unió de caputxa | Unión de capucha | `GarmentCode@d449629 collars.py:324` |
| 6 | `hood_centre_seam` | neck | seam | hood_centre_seam |  | Hood centre seam | Costura central de la caputxa | Costura central de la capucha | `GarmentCode@d449629 collars.py:323` |
| 7 | `strapless_top` | torso | finished | -- |  | Strapless top edge | Vora de cos sense tirants | Borde de cuerpo sin tirantes | `GarmentCode@d449629 bodice.py:382-383` |
| 8 | `shoulder_seam` | shoulder | seam | shoulder_seam |  | Shoulder seam | Costura d'espatlla | Costura de hombro | `GarmentCode@d449629 bodice.py:75; bodice.py:211-213` |
| 9 | `armhole` | arm | opening | sleeve_cap |  | Armhole | Sisa | Sisa | `GarmentCode@d449629 bodice.py:306; sleeves.py:11-105` |
| 10 | `sleeve_cap` | arm | seam | armhole |  | Sleeve cap | Cap de màniga | Copa de manga | `GarmentCode@d449629 sleeves.py:180,289` |
| 11 | `sleeve_underarm_seam` | arm | seam | sleeve_underarm_seam | SI | Sleeve underarm seam | Costura de sota-màniga | Costura de bajo manga | `GarmentCode@d449629 sleeves.py:281-284` |
| 12 | `cuff_line` | any | seam | band_attach_upper | SI | Cuff line | Línia de puny | Línea de puño | `GarmentCode@d449629 sleeves.py:181,328-331` |
| 13 | `centre_front` | torso | seam | centre_front | SI | Centre front | Centre davant | Centro delantero | `GarmentCode@d449629 bodice.py:74; bodice.py:443-444` |
| 14 | `centre_back` | torso | seam | centre_back | SI | Centre back | Centre esquena | Centro espalda | `GarmentCode@d449629 bodice.py:126; bodice.py:445-446` |
| 15 | `side_seam` | torso | seam | side_seam | SI | Side seam | Costura lateral | Costura lateral | `GarmentCode@d449629 bodice.py:73,217; pants.py:115,232` |
| 16 | `waistline` | waist | seam | band_attach_upper | SI | Waistline | Línia de cintura | Línea de cintura | `GarmentCode@d449629 meta_garment.py:75; skirt_paneled.py:45` |
| 17 | `band_attach_upper` | waist | seam | waistline | SI | Band upper attach | Unió superior de banda | Unión superior de banda | `GarmentCode@d449629 bands.py:19` |
| 18 | `band_attach_lower` | waist | seam | waistline | SI | Band lower attach | Unió inferior de banda | Unión inferior de banda | `GarmentCode@d449629 bands.py:24` |
| 19 | `band_side_seam` | waist | seam | band_side_seam | SI | Band side seam | Costura lateral de banda | Costura lateral de banda | `GarmentCode@d449629 bands.py:74-75` |
| 20 | `inseam` | leg | seam | inseam | SI | Inseam | Entrecuix | Entrepierna | `GarmentCode@d449629 pants.py:120,233` |
| 21 | `crotch_seam` | leg | seam | crotch_seam |  | Crotch seam | Costura de tir | Costura de tiro | `GarmentCode@d449629 pants.py:119,289-290` |
| 22 | `hem` | any | finished | -- | SI | Hem | Baix | Bajo | `GarmentCode@d449629 skirt_paneled.py:49; pants.py:121` |
| 23 | `gore_seam` | any | seam | gore_seam | SI | Gore seam | Costura de gaia | Costura de nesga | `GarmentCode@d449629 skirt_paneled.py:497-501` |
| 24 | `dart_leg` | any | internal | dart_leg |  | Dart leg | Braç de pinça | Brazo de pinza | `GarmentCode@d449629 panel.py:238; edge_factory.py:313` |
| 25 | `godet_insert_seam` | any | structural | slit_edge |  | Godet insert seam | Costura d'inserció de godet | Costura de inserción de godet | `GarmentCode@d449629 godet.py:113-114` |
| 26 | `level_join_seam` | any | structural | level_join_seam |  | Level join seam | Costura d'unió de nivells | Costura de unión de niveles | `GarmentCode@d449629 skirt_levels.py:62-64` |
| 27 | `slit_edge` | any | structural | -- | SI | Slit edge | Vora d'obertura | Borde de abertura | `GarmentCode@d449629 skirt_paneled.py:192,218; circle_skirt.py:216; edge_factory.py:292` |

---

## 3 · `LandmarkRole` — 8 files

**Set de vuit i UNA sola evidencia.** El 2.371/2.371 de `hps_pont.txt` mesura el
PONT d'espatlla, i aquell pont evidencia dues regles: `hps` (un extrem) i
`shoulder_point` (l'altre). **Les altres sis van amb NULL**: son regles escrites amb
el mateix patro i mai mesurades, i manllevar-los el 2.371 del vei seria inventar-hi
una evidencia que no tenen.

| # | slug | zone | derivable | op | input | tiebreak | evidencia | nom_en | nom_ca | nom_es |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `hps` | shoulder | SI | shared_endpoint | neckline + shoulder_seam | -- | 2371/2371 | High point shoulder | Punt alt d'espatlla | Punto alto de hombro |
| 2 | `shoulder_point` | shoulder | SI | shared_endpoint | shoulder_seam + armhole | -- | 2371/2371 | Shoulder point | Punt d'espatlla | Punto de hombro |
| 3 | `underarm_point` | arm | SI | far_endpoint | armhole | lowest_y | NO MESURADA | Underarm point | Punt de sota-braç | Punto de sobaco |
| 4 | `neck_centre_point` | neck | SI | far_endpoint | neckline | away_from:hps | NO MESURADA | Neck centre point | Punt central d'escot | Punto central de escote |
| 5 | `waist_side_point` | waist | SI | shared_endpoint | side_seam + waistline | -- | NO MESURADA | Waist side point | Punt de cintura al costat | Punto de cintura en el costado |
| 6 | `hem_side_point` | any | SI | shared_endpoint | side_seam + hem | -- | NO MESURADA | Hem side point | Punt de baix al costat | Punto de bajo en el costado |
| 7 | `crotch_point` | leg | SI | shared_endpoint | inseam + crotch_seam | -- | NO MESURADA | Crotch point | Punt de tir | Punto de tiro |
| 8 | `underarm_seam_point` | arm | SI | shared_endpoint | sleeve_cap + sleeve_underarm_seam | -- | NO MESURADA | Underarm seam point | Punt de sota-màniga | Punto de bajo manga |

---

## 4 · `GCPieceRoleMap` — 24 files

Els 24 rols de GarmentCode cauen sobre **11 slugs d'FTT** (els 8 que el catàleg ja tenia
més els tres de D6, que tanquen els cinc únics forats). La reducció és forta i volguda:
**vuit rols cauen tots sobre `cuff`** —quatre conceptes (puny de màniga, puny de màniga
acampanat, puny de cama, puny de cama acampanat) × dues cares, que l'eix `face` absorbeix
en dos destins. L'acampanament és un eix de variant, no una peça diferent. Però vol dir
que **una plantilla d'FTT recull més d'una parella del corpus**, i per això les
freqüències s'agreguen dins de la BD i no sumant a mà.

| # | gc_role | ftt_slug | face | nota |
|---|---|---|---|---|
| 1 | `ftorso` | `front` | front | directe |
| 2 | `btorso` | `back` | back | directe |
| 3 | `sleeve_f` | `sleeve` | front | eix `face` (D1) |
| 4 | `sleeve_b` | `sleeve` | back | eix `face` (D1) |
| 5 | `skirt_front` | `skirt` | front | eix `face` (D1) |
| 6 | `skirt_back` | `skirt` | back | eix `face` (D1) |
| 7 | `skirt_panel` | `panel` | -- | faldilla de gaies: el panell no té cara |
| 8 | `wb_front` | `waistband` | front | eix `face` (D1) |
| 9 | `wb_back` | `waistband` | back | eix `face` (D1) |
| 10 | `sl_cuff_f` | `cuff` | front | puny de màniga |
| 11 | `sl_cuff_b` | `cuff` | back | puny de màniga |
| 12 | `sl_cuff_skirt_f` | `cuff` | front | puny de màniga ACAMPANAT (eix de variant) |
| 13 | `sl_cuff_skirt_b` | `cuff` | back | puny de màniga ACAMPANAT (eix de variant) |
| 14 | `pant_cuff_f` | `cuff` | front | puny de cama |
| 15 | `pant_cuff_b` | `cuff` | back | puny de cama |
| 16 | `pant_cuff_skirt_f` | `cuff` | front | puny de cama ACAMPANAT (eix de variant) |
| 17 | `pant_cuff_skirt_b` | `cuff` | back | puny de cama ACAMPANAT (eix de variant) |
| 18 | `collar_front` | `collar` | front | eix `face` (D1) |
| 19 | `collar_back` | `collar` | back | eix `face` (D1) |
| 20 | `pant_f` | `pant` | front | slug NOU (D6): FTT no tenia cama de pantaló |
| 21 | `pant_b` | `pant` | back | slug NOU (D6): FTT no tenia cama de pantaló |
| 22 | `hood` | `hood` | -- | slug NOU (D6): FTT no tenia caputxa |
| 23 | `ins_skirt_front` | `godet_insert` | front | slug NOU (D6): FTT no tenia godet |
| 24 | `ins_skirt_back` | `godet_insert` | back | slug NOU (D6): FTT no tenia godet |

---

## 5 · `SeamPairTemplate` — 53 files

**Totes amb `garment_type_item=NULL`** (plantilles generiques) i
**`pendent_revisio=True`**: les xifres son d'un corpus de tercers i els llindars de
D3 encara no els ha fixat ningu.

🚨 **El denominador NO son mai els 128.974.** `observed_den` es el total de designs
de les categories on **totes dues peces hi apareixen**, i aquesta llista es MESURA,
no s'endevina: una parella de pantalo es mesura sobre `jumpsuits,pants` (17.130), una
de faldilla sobre `dresses,skirts` (77.690). La regla i les categories de cada fila
viatgen dins d'`observed_ref`.

⚠️ **El corpus no sap que es una VORA.** `stitch` en desa l'INDEX (`{panel, edge}`) i
els noms d'interficie no se serialitzen (informe §4.1). Les files **#1 i #2**
(espatlla i costat del tors) son totes dues `front<->back` i **comparteixen xifra**:
436.842 costures son la SUMA de les dues costures. No es un error de mesura, es el
sostre del corpus, i `observed_ref` ho diu a les dues files perque ningu no llegeixi
el numero com si fos nomes d'una.

| # | regla | kind | costat A | costat B | co_gen | seams | patrons | den | % | categories |
|---|---|---|---|---|---|---:|---:|---:|---:|---|
| 1 | #1 | union | `back/back.shoulder_seam` | `front/front.shoulder_seam` |  | 436842 | 90273 | 90273 | 100.0 % | dresses,jumpsuits,upper_garments |
| 2 | #2 | union | `back/back.side_seam` | `front/front.side_seam` |  | 436842 | 90273 | 90273 | 100.0 % | dresses,jumpsuits,upper_garments |
| 3 | #3 | union | `front/front.armhole` | `sleeve/front.sleeve_cap` | SI | 105612 | 56514 | 90273 | 62.6 % | dresses,jumpsuits,upper_garments |
| 4 | #3 | union | `back/back.armhole` | `sleeve/back.sleeve_cap` | SI | 105612 | 56514 | 90273 | 62.6 % | dresses,jumpsuits,upper_garments |
| 5 | #3 | union | `front/front.armhole` | `sleeve/back.sleeve_cap` | SI | 64487 | 35121 | 90273 | 38.9 % | dresses,jumpsuits,upper_garments |
| 6 | #3 | union | `back/back.armhole` | `sleeve/front.sleeve_cap` | SI | 0 | 0 | 90273 | 0.0 % | dresses,jumpsuits,upper_garments |
| 7 | #4 | union | `collar/front.collar_attach` | `front/front.neckline` | SI | 14154 | 7077 | 90273 | 7.8 % | dresses,jumpsuits,upper_garments |
| 8 | #4 | union | `back/back.neckline` | `collar/back.collar_attach` | SI | 23344 | 11672 | 90273 | 12.9 % | dresses,jumpsuits,upper_garments |
| 9 | #5 | centre | `front/front.centre_front` | `front/front.centre_front` |  | 90273 | 90273 | 90273 | 100.0 % | dresses,jumpsuits,upper_garments |
| 10 | #6 | centre | `back/back.centre_back` | `back/back.centre_back` |  | 90273 | 90273 | 90273 | 100.0 % | dresses,jumpsuits,upper_garments |
| 11 | #7+#8 | union | `sleeve/back.sleeve_underarm_seam` | `sleeve/front.sleeve_underarm_seam` |  | 223643 | 56514 | 90273 | 62.6 % | dresses,jumpsuits,upper_garments |
| 12 | #9 | union | `cuff/front.band_attach_upper` | `sleeve/front.cuff_line` |  | 75542 | 41651 | 90273 | 46.1 % | dresses,jumpsuits,upper_garments |
| 13 | #9 | union | `cuff/back.band_attach_upper` | `sleeve/back.cuff_line` |  | 75542 | 41651 | 90273 | 46.1 % | dresses,jumpsuits,upper_garments |
| 14 | #10 | union | `pant/back.side_seam` | `pant/front.side_seam` |  | 102780 | 17130 | 17130 | 100.0 % | jumpsuits,pants |
| 15 | #11 | union | `pant/back.inseam` | `pant/front.inseam` |  | 102780 | 17130 | 17130 | 100.0 % | jumpsuits,pants |
| 16 | #12 | centre | `pant/front.crotch_seam` | `pant/front.crotch_seam` |  | 34260 | 17130 | 17130 | 100.0 % | jumpsuits,pants |
| 17 | #13 | centre | `pant/back.crotch_seam` | `pant/back.crotch_seam` |  | 34260 | 17130 | 17130 | 100.0 % | jumpsuits,pants |
| 18 | #14 | union | `cuff/front.band_attach_upper` | `pant/front.cuff_line` |  | 15882 | 7941 | 17130 | 46.4 % | jumpsuits,pants |
| 19 | #14 | union | `cuff/back.band_attach_upper` | `pant/back.cuff_line` |  | 15882 | 7941 | 17130 | 46.4 % | jumpsuits,pants |
| 20 | #14 | union | `cuff/front.band_attach_upper` | `pant/back.cuff_line` |  | 7346 | 3673 | 17130 | 21.4 % | jumpsuits,pants |
| 21 | #14 | union | `cuff/back.band_attach_upper` | `pant/front.cuff_line` |  | 0 | 0 | 17130 | 0.0 % | jumpsuits,pants |
| 22 | #15 | union | `skirt/back.side_seam` | `skirt/front.side_seam` |  | 236528 | 68513 | 77690 | 88.2 % | dresses,skirts |
| 23 | #16 | union | `waistband/back.band_side_seam` | `waistband/front.band_side_seam` |  | 124132 | 62066 | 128974 | 48.1 % | dresses,jumpsuits,pants,skirts,upper_garments |
| 24 | #16 | union | `cuff/back.band_side_seam` | `cuff/front.band_side_seam` |  | 241004 | 47912 | 99620 | 48.1 % | dresses,jumpsuits,pants,upper_garments |
| 25 | #17 | union | `cuff/front.band_attach_lower` | `cuff/front.waistline` |  | 29078 | 16367 | 99620 | 16.4 % | dresses,jumpsuits,pants,upper_garments |
| 26 | #17 | union | `cuff/back.band_attach_lower` | `cuff/back.waistline` |  | 29078 | 16367 | 99620 | 16.4 % | dresses,jumpsuits,pants,upper_garments |
| 27 | #18 | union | `panel.gore_seam` | `panel.gore_seam` |  | 89856 | 9177 | 77690 | 11.8 % | dresses,skirts |
| 28 | #19 | level_join | `skirt/front.hem` | `skirt/front.waistline` |  | 19480 | 7511 | 77690 | 9.7 % | dresses,skirts |
| 29 | #19 | level_join | `skirt/back.hem` | `skirt/back.waistline` |  | 19480 | 7511 | 77690 | 9.7 % | dresses,skirts |
| 30 | #20 | union | `front/front.waistline` | `waistband/front.band_attach_upper` |  | 124096 | 39845 | 90273 | 44.1 % | dresses,jumpsuits,upper_garments |
| 31 | #20 | union | `back/back.waistline` | `waistband/back.band_attach_upper` |  | 168502 | 39845 | 90273 | 44.1 % | dresses,jumpsuits,upper_garments |
| 32 | #20 | union | `skirt/front.waistline` | `waistband/front.band_attach_lower` |  | 34888 | 34888 | 77690 | 44.9 % | dresses,skirts |
| 33 | #20 | union | `skirt/back.waistline` | `waistband/back.band_attach_lower` |  | 90604 | 34888 | 77690 | 44.9 % | dresses,skirts |
| 34 | #20 | union | `pant/front.waistline` | `waistband/front.band_attach_lower` |  | 16184 | 8092 | 17130 | 47.2 % | jumpsuits,pants |
| 35 | #20 | union | `pant/back.waistline` | `waistband/back.band_attach_lower` |  | 48552 | 8092 | 17130 | 47.2 % | jumpsuits,pants |
| 36 | #20 | union | `panel.waistline` | `waistband/front.band_attach_lower` |  | 26066 | 4597 | 77690 | 5.9 % | dresses,skirts |
| 37 | #20 | union | `panel.waistline` | `waistband/back.band_attach_lower` |  | 22589 | 4597 | 77690 | 5.9 % | dresses,skirts |
| 38 | #20 | union | `front/front.waistline` | `skirt/front.waistline` |  | 69488 | 22829 | 48336 | 47.2 % | dresses |
| 39 | #20 | union | `back/back.waistline` | `skirt/back.waistline` |  | 106561 | 22829 | 48336 | 47.2 % | dresses |
| 40 | #20 | union | `front/front.waistline` | `pant/front.waistline` |  | 13573 | 4314 | 7783 | 55.4 % | jumpsuits |
| 41 | #20 | union | `back/back.waistline` | `pant/back.waistline` |  | 26026 | 4314 | 7783 | 55.4 % | jumpsuits |
| 42 | #20 | union | `front/front.waistline` | `panel.waistline` |  | 26164 | 3620 | 48336 | 7.5 % | dresses |
| 43 | #20 | union | `back/back.waistline` | `panel.waistline` |  | 27026 | 3620 | 48336 | 7.5 % | dresses |
| 44 | #21 | insert_join | `godet_insert/front.godet_insert_seam` | `skirt/front.slit_edge` |  | 77816 | 10448 | 77690 | 13.4 % | dresses,skirts |
| 45 | #21 | insert_join | `godet_insert/back.godet_insert_seam` | `skirt/back.slit_edge` |  | 77816 | 10448 | 77690 | 13.4 % | dresses,skirts |
| 46 | #22 | dart | `front/front.dart_leg` | `front/front.dart_leg` |  | 188408 | 47102 | 90273 | 52.2 % | dresses,jumpsuits,upper_garments |
| 47 | #22 | dart | `back/back.dart_leg` | `back/back.dart_leg` |  | 188408 | 47102 | 90273 | 52.2 % | dresses,jumpsuits,upper_garments |
| 48 | #22 | dart | `skirt/back.dart_leg` | `skirt/back.dart_leg` |  | 121052 | 30263 | 77690 | 39.0 % | dresses,skirts |
| 49 | #22 | dart | `pant/back.dart_leg` | `pant/back.dart_leg` |  | 68520 | 17130 | 17130 | 100.0 % | jumpsuits,pants |
| 50 | §2.4 | union | `front/front.neckline` | `hood.hood_attach` |  | 14354 | 7177 | 90273 | 8.0 % | dresses,jumpsuits,upper_garments |
| 51 | §2.4 | union | `back/back.neckline` | `hood.hood_attach` |  | 14354 | 7177 | 90273 | 8.0 % | dresses,jumpsuits,upper_garments |
| 52 | §2.4 | centre | `hood.hood_centre_seam` | `hood.hood_centre_seam` |  | 14354 | 7177 | 90273 | 8.0 % | dresses,jumpsuits,upper_garments |
| 53 | §2.4 | union | `collar/back.collar_side_seam` | `collar/front.collar_side_seam` |  | 23402 | 11701 | 90273 | 13.0 % | dresses,jumpsuits,upper_garments |

---

## 6 · ## Parelles MESURADES que cap plantilla no recull (2 de 51)
Vocabulari que l'ontologia no nomena. No es sembra res: es la llista per a
la sessio Montse i per a F4.

| kind | costat A | costat B | seams | patrons |
|---|---|---|---:|---:|
| centre | `collar/back` | `collar/back` | 16296 | 16296 |
| centre | `collar/front` | `collar/front` | 7077 | 7077 |

---

## 7 · `GarmentTypeItemEdgeProfile` — taula creada, **sembra buida**

No és un oblit: **el vocabulari genèric no sap encara quin GTI de casa li correspon.** Les
plantilles genèriques viuen a `SeamPairTemplate` amb `garment_type_item=NULL`; els perfils
per GTI concret els han de mapar l'Agus i la Montse. La taula existeix perquè quan aquella
sessió arribi no hagi de migrar res.

Al schema `fhort` hi ha GTIs reals; a `los`, els que hi hagi. **Cap dels dos s'ha tocat.**

---

## 8 · Desviacions del DDL de l'informe (§5.4), amb motiu

| desviació | motiu |
|---|---|
| `db_constraint=False` a les dues FK cap a `tasks.GarmentTypeItem` | **Mesurat**: sense això `migrate_schemas` PETA a `public` amb `relation "tasks_garmenttypeitem" does not exist`. `pom` viu a SHARED i TENANT, `tasks` només a TENANT. És el que ja fan les migracions 0025, 0040 i 0047. |
| **DOS** `UNIQUE` parcials a `SeamPairTemplate` | El DDL de l'informe no en porta cap i només **comenta** la convenció d'ordenació. Un de sol no bastava: amb `garment_type_item` NULL no casa mai (§1.3). Migració 0085. |
| `UNIQUE` canònic a `GarmentTypeItemEdgeProfile` | El DDL el porta; s'hi afegeix `face`, que el DDL ja llistava però no incloïa a la clau. |
| `mates_slug` és `''` i no `NULL` | Estil de casa: cap `CharField` nul·lable al catàleg (`PatternPieceRole`, `MeasurementLayer`). Buit = no es cus amb res. |
| `zone` de `cuff_line` és `any`, no `arm/leg` | El camp té 12 caràcters i un valor tancat. Un puny és de màniga **i** de cama; `any` és més honest que triar-ne una. |
| `centre_front`/`centre_back` amb `kind='seam'` | §2.4 en diu «seam/fold». GarmentCode sempre en fa costura (§4.4); el doblec és una decisió de taller que el `PatternPiece.doblec_original` ja registra. |
| `CatalegSemanticOrigenMixin` | Els 5 camps d'auditoria (`is_system`/`pendent_revisio`/`origen`/`display_order`/`source_ref`) surten a 4 taules. Escriure'ls 4 cops seria on començarien a divergir. |
| `GCPieceRoleMap` no és al DDL | La demana el brief (A3). Taula i no diccionari en un script: F4 l'ha de consultar en calent. |

---

## 9 · Què passa quan diguis que sí

```bash
cd /var/www/ftt-f3/backend
python manage.py seed_semantic_catalog            # aplica als 3 esquemes
python manage.py seed_semantic_catalog            # 2a passada: 0 creats, tot actualitzat
```

I després: recompte de guarda exacte per taula i esquema amb `psql` directe (no per l'ORM),
merge a `dev`, `systemctl restart ftt-staging.service` i smoke `curl`.

**Si vols canviar res —un `nom_ca`, un slug, una fila fora— es canvia AQUÍ i es torna a
córrer el dry-run.** Cap fila no ha entrat encara a cap taula.
