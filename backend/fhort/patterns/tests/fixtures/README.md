# Fixtures del motor de patrons

Material CAD **real** versionat a git deliberadament (excepció conscient a la regla de no
commitar binaris): és l'única manera que els tests del motor s'executin contra el format de
veritat i no contra una idea del format. Són fitxers de prova, no producció.

⚠️ Aquest directori NO ha de tenir mai `__init__.py`: `patterns/tests.py` (mòdul) i
`patterns/tests/` (dades) coexisteixen, i el mòdul només guanya la resolució d'import
mentre `tests/` no sigui un paquet.

## AMELIA_AZUL_prova.dxf

- **Font CAD: PolyPattern 11.0.1** (reatribuït 2026-07-12; el pla el donava per Tuka —
  ho desmenteix el `AUTHOR:` del RUL germà, la coma decimal dels TEXT i els 266 POINT).
- md5 `2ae0006e003ebe17326187d79bb587d5` · 31 344 bytes.
- Exemplar viu: `backend/media/fhort/import_sessions/2026/06/AMELIA_AZUL_prova.DXF`
  (mateix md5), pujat el 2026-06-23. Còpia de treball a `ops/motor-patrons/material/`.
- Contingut: 4 peces (`BACK`, `FRONT`, `BACK_LINI`, `FRONT_LINI`), talla única `M`.
- Particularitats que el fan bon fixture: **`HEADER` i `TABLES` buides** (sense `$INSUNITS`
  → les unitats s'han de deduir per geometria), **sense capa 14 (cosit)** ni capa 6
  (mirall), i una **capa 15 no catalogada** (TEXT d'autoria).

## AMELIA_AZUL_prova.rul

- md5 `e56202b0a3e1c06c62adf19ac849f4f1` · 228 bytes.
- `version ANSI/AAMA-292-B`, `AUTHOR: PolyPattern 11.0.1`, `UNITS: METRIC`.
- 5 talles (`XS S M L XL`), base `M`, **1 regla amb tots els deltes a zero**.
  L'estructura és el que es testeja, no els valors.

## Absents (FLAG)

- **Cap fitxer Tuka** (AAMA 2.1.1, ~92 punts). Quan arribi, serà la segona empremta i
  desbloquejarà el perfil `tuka` del writer (S2).

## TATE_prova.dxf

- **El patró real del QA**: Blusa TATE Crudo, model `BRW-FW26-0001` (Brownie). Còpia literal
  de l'exemplar viu `backend/media/fhort/pattern_files/TATE.DXF` (mateix md5).
- md5 `419337df26602569253e243af735ab78` · 332 260 bytes.
- Contingut: **10 peces** (`TATE_BACK`, `TATE_FRONT`, `TATE_SLEEVE`, `TATE_NECK_BAND`,
  `TATE_FRONT_YOKE`, `TATE_FACING_YOKE`, `TATE_FRONT_FACING`, `TATE_NECK_BAND_INTERLINING`,
  `1rst_collar`, `1rst_sleeve`). Sense RUL germà.
- **Per què cal, si ja hi ha l'AMELIA:** porta la **capa 14 (línia de COSIT)**, que l'AMELIA
  no té. És la vora de la qual es deriven els trams de veritat —`segmentar_peca` prefereix el
  cosit al tall— i fins ara aquella branca no s'havia exercit mai contra material real.
  A `TATE_FRONT`: vora de tall 196,6 cm · **vora de cosit 183,1 cm** (tancada, 169 punts),
  25 trams derivats que sumen exactament els 183,1 cm.
- També aporta vores tancades grans (258 punts al tall del davanter) i 30 punts de gir, que
  és el que fa que declarar un tram entre dos punts qualssevol tingui sentit de provar.
