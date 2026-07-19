# FASE 1 · Sembra GradingRules v2 (resolució per alias) — informe

> Staging · `fhort` · dev. Data: 2026-07-18. Dades només, dry-run primer. NO push.
> Config: `fhort/pom/seed_data/grading_rules_losan_ss27_v2.json` (al costat de la v1).
> Command: `seed_losan_rules_v2` (idempotent, --dry-run per defecte).

## Mecànica

Igual que la v1, amb UNA diferència: les regles porten `alias` (codi del client), no codi
POMMaster. Resolució: `CustomerPOMAlias(customer=LOS, client_code=alias) → POMMaster`, provant
l'alias tal qual i variants de puntuació (`C4↔C.4`, `SR6↔S.R6`). Alias sense POM al diccionari
→ NO es crea, es llista. Convencions de camp idèntiques a la v1 (motor NO tocat): logica LINEAR,
`talla_base`=talla més petita (ordre 1), `increment`=`increment_base`, break per etiqueta,
`talla_break_pos`=NULL.

## Resultat: 126 creades + 2 actualitzades

| contenidor (identitat) | base | break | creades | actualitzades | skip |
|---|---|---|---|---|---|
| youth boy trousers (JEREMY) | 8 | — | 18 | 0 | 1 |
| baby baby_top (GLACIAR) | 03/06 | — | 16 | 0 | 0 |
| youth girl trousers (GALA) | 8 | 14 | 12 | 0 | 0 |
| man num trousers (ENRIC) | 38 | — | 20 | **1** | 2 |
| kids boy jeans (TARRAGONA) | 2 | 9/10 | 22 | 0 | 3 |
| woman t_shirt (DANIELA) | XS | — | 17 | 0 | 0 |
| woman num trousers (BUDAPEST) | 36 | — | 21 | **1** | 2 |

Idempotència confirmada (2n dry-run → 0 creades, 128 actualitzades).
**Total regles als contenidors LOS (v1+v2): 162** (36 v1 + 126 v2 noves).

## Tractament de l'overlap amb v1 (com demanava el brief)

L'alias `C` (WAIST WIDTH) resol a POM **`WA`**, que la v1 ja havia sembrat com a regla parcial
a 3 contenidors. Per `update_or_create(rule_set, pom)`:

- **ENRIC** (man num) i **BUDAPEST** (woman num): tenen `C`→WA → **actualitzen** la WA de v1
  (mateix POM, mateix valor 2.0). Sense duplicat (verificat: man_num té WA×1).
- **GALA** (youth girl trousers): v2 NO té `C` (té `C4`/`C1` = waist relaxed/extended, POMs
  diferents). La WA de v1 (WAIST WIDTH 1/2, ib 1.5 break 2.0) **conviu** amb les 12 noves →
  el contenidor queda amb 13 regles.
  ⚠️ **A decidir (Agus/Montse):** la WA parcial de v1 pot estar SUPERADA per C4/C1 de la fitxa
  GALA. No s'ha esborrat (fora d'abast d'aquest brief). Candidata a retirar a la fase de mesures.

Guard de col·lisió intra-contenidor (dos àlies del mateix contenidor → mateix POM): **0 detectades**.

## Alies NO resolts (8 instàncies, no sembrats)

Genuïnament sense POM mapat al diccionari LOS (provades totes les variants de puntuació):

| alias (fitxa) | descripció | contenidors afectats |
|---|---|---|
| `C13` (C.13) | BUTTONHOLE LOCATION | JEREMY, TARRAGONA |
| `SR6` (S.R6) | LOOP LENGTH | ENRIC, TARRAGONA, BUDAPEST |
| `SR7` (S.R7) | LOOP WIDTH | ENRIC, TARRAGONA, BUDAPEST |

→ Afegir aquests 3 codis al diccionari LOS (CustomerPOMAlias amb POM destí) i re-executar el
command (idempotent) per completar-los. Reforça la petició de nomenclatura pendent.

## Pendents del JSON (sense_regla_pendents, no sembrats): 2
- baby_top `AW` (CHEST MOTIVE LOCATION) — alias no al diccionari (GAP).
- woman t_shirt `GA` (SLEEVE INSEAM LENGTH) — increment no numèric a la fitxa (FALTA).

## Nota de resolució (diccionari LOS, verificat)
Mostres del mapatge alias→POM aplicat: `B→CH` · `C→WA` · `E→SK SW` · `D1→THI` · `D2→KNE` ·
`F→LEG OP` · `K→SH` · `K1→SH DR` · `H6→AH DEP` · `M→M-M79` · `L3→NK W` · `AJ→S1-M76` · `R8→BR` ·
`C11→WB H` · `D11→D.11-M79`. (El client anomena diferent; el POM canònic és el del diccionari.)

## Verd / restart / git
- `manage.py check` net · idempotència OK · servei `ftt-staging.service` reiniciat.

## Pendents d'OK d'Agus / Montse
1. **3 codis de diccionari** (C13/SR6/SR7) → mapar i re-seed.
2. **WA parcial de v1 a youth girl trousers** → retirar si C4/C1 la superen.
3. (Heretats) talla base/sample formal · 2 pendents AW/GA · deute SizingProfile 104/GIRL_LOS_03.
