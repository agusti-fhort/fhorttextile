# PAS 4B — Consolidació del catàleg POM: informe d'execució

> Staging · `fhort` · dev. Data: 2026-07-19. Gate 4A validat per Agus. Dades només,
> dry-run primer, motor NO tocat, els 72 prims sense àlies LOS INTACTES. NO push.
> Command: `consolidate_pom_catalog --phase {fusio,translate,maps}` (idempotent, --dry-run).
> Config: `fhort/pom/seed_data/consolidate_pom_los.py` + `traduccions_pom_los.csv`.

## Resum

| fase | resultat |
|---|---|
| **fusió** | 13 fusions (14 prims) prim LOS → canònic ric · 38 refs mogudes · 1 col·lisió · GradedSpec esborrats · prims desactivats |
| **translate** | 53 prims COMPLETAR traduïts (ca) · 33 files CSV sense prim · **69 COMPLETAR sense traducció (pendents)** |
| **maps** | 8 GarmentPOMMap (només exemples explícits; **vault absent** → resta pendent) |

## FASE fusió (13 fusions · 14 prims)

Cada fusió: re-apunta `CustomerPOMAlias(LOS)` del prim → canònic (conserva `client_code`, el
nom del client es preserva a l'àlies); mou `BaseMeasurement`/`ModelGradingRule`/`MeasurementChangeLog`/
`ModelGradingOverride`/`ItemBaseMeasurement`/`ClientMesuraPerfil`/`POMAlert`/`PatternPOM`/
`POMEstadisticaTenant` via `.update()` per fila (evita el `save()` append-only i respecta
unique amb `IntegrityError`→col·lisió); esborra `GradedSpec` (regenerable); desactiva el prim
(`regles_grading` PROTECT → s'esborren al PAS 3).

| prim (id·codi·nom) | → canònic | refs mogudes | GradedSpec✗ | regles_grading |
|---|---|---|---|---|
| 434 `T.1` FRONT RISE | RI FR | 6 | 10 | 7 |
| 435 `T.2` BACK RISE | RI BK | 6 | 10 | 7 |
| 422 `L.4` FRONT NECK DROP | NK DR FR | 1 | — | 5 |
| 421 `L.5` BACK NECK DROP | NK DR BK | 1 | — | 5 |
| 419 `A.1` FRONT WIDTH | AC FR | 1 | — | 6 |
| 517 `A2` BACK WIDTH | AC BK | 1 | — | 4 |
| 423 `H` SLEEVE MUSCLE (1/2) | BIC | 1 | — | 3 |
| 551 `H` SLEEVE MUSCLE | BIC | 1 | — | 2 |
| 518 `B1` CHEST WIDTH RELAXED | CH RLX | 1 | — | 0 |
| 553 `H11` SLEEVE OPENING | SL OP | 1 | — | 3 |
| 431 `K.2` SHOULDER TO SHOULDER | AC SH | 10 | 10 | 6 |
| 519 `B2` CHEST WIDTH EXTENDED | CH STR | 1 | — | 0 |
| 528 `D` HIP WIDTH | HI PA | 1 | — | 5 |
| 468 `JJ` ELBOW WIDTH | ELB | 6 | — | 1 |

**1 col·lisió** (K.2→AC SH): un model ja tenia una mesura a AC SH → la mesura del prim K.2 no
es pot moure (unique) i **queda al prim desactivat** (el canònic preval). Anotat.
**Spot-check:** àlies `T1`→RI FR, `K2`→AC SH, `H`/`H19`→BIC, `A1`→AC FR — tots resolen a
canònic ric (glob=SI, maps>0). Prims desactivats amb 0 àlies i 0 GradedSpec.

## FASE translate (53 traduïts)

Crea `POMGlobal` (codi `LOSPOM-<id>`, tenant-local a fhort) amb `nom_ca` del CSV per als prims
LOS de detall sense equivalent canònic; enllaça `prim.pom_global`. Match CSV↔prim per àlies LOS
i, com a fallback, per codi del prim (variants de puntuació). Spot: `M4`→"Posició del tall",
`O16`→"Obertura butxaca davant", `AJ`→S1-M76 "Ample de coll", `M`→M-M79 "Llargada total".

- **33 files CSV sense prim aplicable** (l'àlies resol a un canònic ja traduït —D.1→THI, D.2→KNE,
  C.11→WB H…— o són GAPS sense POM: `B4·E.1·E.2·M.1·R.1·R.3·Z·SR9·S.R6·S.R7·AW·V.9/10/11·CB·EV·
  S.19/20/39/40·S.11·M.8·S.35·S.4·S.5·C.13·D.20·T.5·R2·O.21`).
- **69 prims COMPLETAR sense traducció** (el CSV no els cobreix → NO inventats, PENDENTS del
  gate següent): `V.13-M79·C.14-M79·O.27-M79·V.14-M79·F1·J1(×2)·FP·S8·A·A3·C3·C2·C5·C6·F2·E3·
  E4·E5·E7·MF·H7·H8·H9·G5·H14·GL·GN·GM·S27·S28·S30·T13·T14·V4·V5·V6·V7·S34·JC·S45·N4·U4·U7·S·
  AB·O9·O11·O12·O13·O14·O17·O28·O36·O38·O39·O40·O41·O33·O34·W4·W5·W6·W7·W9·S54·S55·SR2·SR3`.

## FASE maps (8 GarmentPOMMap · vault absent)

⚠ **`FTT-Brain/GRADING_SOURCES_LOSAN.md` NO és en aquest host** → no es pot derivar la
pertinença item↔POM. S'apliquen NOMÉS els exemples explícits i anatòmicament inequívocs del
brief (POM i item verificats), amb `pendent_revisio=True`:

- `D6`/`D7` (entrecames) → **baby_bodysuit** (2)
- `S.10`/`S.56`/`S53` (caputxa) → **hoodie** + **baby_sleepsuit** (6)

**PENDENT del vault** (no mapat, per no inventar): tota la resta de COMPLETAR — butxaques
`O.xx`/`W.xx` (→ trousers/jeans/shorts segons brief, però el set exacte per item necessita el
vault), canesús `S.xx`, punys, colls, plecs, pinces… Els POMs de PEUS `S.19/20/39/40` **no
existeixen** com a POM (no mapables). Cal el vault per completar aquesta fase.

## Verificació final

- **cap `CustomerPOMAlias` de LOS resol a un POM desactivat** ✓ (0).
- POMMaster: **319 actius · 16 desactivats** (14 prims fusionats + 2 previs) · **178 traduïts**
  (125 previs + 53) · 157 sense.
- Àlies LOS: 101 → ric/traduït · **69 → prim cru pendent de traducció**.
- GarmentPOMMap: 1537 (+8).
- `manage.py check` net · servei `ftt-staging.service` reiniciat (active).

## Pendents d'OK d'Agus / Montse (gate següent)
1. **Traducció ca dels 68-69 prims COMPLETAR** sense CSV (llista de dalt) — ampliar el CSV.
2. **Vault `GRADING_SOURCES_LOSAN.md`** per completar `GarmentPOMMap` de la resta de COMPLETAR
   (butxaques, canesús, etc.). Sense el vault no s'ha mapat (no inventar).
3. **Col·lisió K.2** (1 mesura al prim desactivat) — decidir si es descarta.
4. Els **72 prims sense àlies LOS** (altres imports, dades vives) segueixen intactes — decisió
   separada futura.

*Els 3 concerns commitats (fusió / translate / config-maps). Cap push.*
