# PAS 4B-ter — Tancament FINAL de la consolidació POM (informe)

> Staging · `fhort` · dev. Data: 2026-07-19. Dades només, dry-run primer, motor NO tocat.
> NO push. Command `consolidate_pom_catalog --phase {translate,maps}`. CSVs actualitzats:
> `traduccions_pom_los.csv` (v2, 198 files) + `pom_item_maps_los.csv` (7 gaps marcats).

## Resultat: circuit LOS 100% net

| invariant | valor |
|---|---|
| **POMs del circuit LOS (via àlies) sense traducció** | **0** ✓ |
| **àlies LOS → POM desactivat** | **0** ✓ |
| POMs del circuit LOS (via àlies) | 183 |
| POMMaster actius / traduïts | 339 / 269 |
| GarmentPOMMap total | 1748 |

## 1. Traduccions (CSV v2, diccionari sencer)

`traduccions_pom_los.csv` ampliat a **198 files** (descripcions de font, diccionari LOS complet).
Re-executat `--phase translate`: els **69 COMPLETAR pendents** del 4B-bis queden **tots traduïts**
(POMGlobal `LOSPOM-<id>` tenant-local amb `nom_ca`). **0 prims COMPLETAR sense traducció.**

**Fix del guard de translate:** s'ha tret la condició `garment_maps > 0` (excloïa prims LOS que
havien rebut `GarmentPOMMap` a la fase maps; els canònics ja els exclou la condició de
`pom_global` no-LOSPOM). Sense el fix quedaven 2 orfes (`O.21-M79`, `O.26-M79`) — ara traduïts.

## 2. Els 7 codes sense POM → [gap], creats i mapats

Marcats `[gap]` a `pom_item_maps_los.csv` i creats (LOS-local + traducció v2 + àlies LOS) +
mapats segons el CSV (14 `GarmentPOMMap`):

| codi | ca | items |
|---|---|---|
| S.35 | Ample de peça de coll | baby_top, baby_sleepsuit |
| C.13 | Posició del trau | trousers, jeans, shorts, tracksuit_pant, baby_leggings |
| S.R6 | Llargada de trava | trousers, jeans |
| S.R7 | Ample de trava | trousers, jeans |
| V.9 | Posició d'elàstic | baby_leggings |
| CB | Posició de tall davant | baby_top |
| EV | Pespunt d'alçada de cintura | baby_leggings |

> **C.13 / S.R6 / S.R7** eren els «3 codis pendents» de la sembra v2 (grading_rules v2) — **es
> tanquen aquí** (creats, traduïts, mapats).

## 3. Verificació

- **0 POMs del circuit LOS sense traducció** (cap àlies LOS resol a un POM sense `pom_global`).
- **0 àlies LOS → POM desactivat**.
- `manage.py check` net · servei `ftt-staging.service` reiniciat.
- Idempotent (reuse per codi exacte · `get_or_create` POM/POMGlobal/àlies/GarmentPOMMap).

## Estat final de la consolidació POM (PAS 4 complet)

- **13 fusions** (14 prims) prim LOS → canònic ric (4B).
- **~140 prims COMPLETAR traduïts** (ca) al llarg de 4B/4B-bis/4B-ter.
- **20 POMs NOUS** LOS-local creats (13 al 4B-bis + 7 al 4B-ter), traduïts, amb àlies i mapats.
- **211 GarmentPOMMap** LOS nous (197 + 14), `pendent_revisio=True` (Montse valida).
- **72 prims sense àlies LOS** (altres imports, dades vives) INTACTES.
- K.2: mesura òrfena de col·lisió esborrada.

**El catàleg POM del circuit LOS queda net i traduït, llest per a la re-sembra v3.**

*Pendent menor: els 72 prims no-LOS (decisió separada futura) i la revisió Montse dels
GarmentPOMMap `pendent_revisio`.*
