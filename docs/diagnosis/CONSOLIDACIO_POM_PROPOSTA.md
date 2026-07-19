# PAS 4A — Consolidació del catàleg POM: inventari + proposta (read-only)

> Staging · `fhort` · dev. Data: 2026-07-19. **Read-only: cap canvi.** Sortida per al GATE
> d'Agus (Montse si cal). Prerequisit de la re-sembra v3. Les 162 regles v1/v2 i els 18
> rulesets LOS s'esborraran al PAS 3 → les `GradingRule` NO compten com a refs a moure.
>
> **Principi (llei d'Agus):** preval l'àlies del CLIENT com a interfície; es consolida la
> brutícia del catàleg mestre per sota (POMs "prims": sense `pom_global`, sense
> `GarmentPOMMap`, sense traducció, que DUPLIQUEN un canònic ric). Cap POM supervivent
> del conjunt LOS pot quedar sense traducció/metadada.

## Resum executiu

- **335 POMMaster** · 125 amb `pom_global` (traduïts) · 210 sense.
- **208 PRIMS** (sense `pom_global` **i** sense `GarmentPOMMap`). Es parteixen en:
  - **136 amb àlies LOS** → **abast d'aquesta consolidació**.
  - **72 sense àlies LOS** → **FORA d'abast** (d'altres imports BRW/Mango; molts amb dades
    de model vives). No es toquen aquí.
- **Àlies LOS**: 170 total, tots mapats. **140 resolen a un prim** (a consolidar), 30 ja
  resolen a canònic ric (OK).
- Dels 136 prims LOS: **~15 FUSIÓ** (tenen canònic ric equivalent) · **~121 COMPLETAR**
  (mesura de detall LOS sense canònic real). **14 tenen dades de model vives** → refs reals
  a moure (no només re-apuntar l'àlies).
- **Cap dels 121 COMPLETAR té traducció local** avui → el PAS 4B els n'ha d'afegir.

Cens verificat via `_meta.related_objects` de POMMaster (13 relacions inverses exhaustives):
`estadistiques · client_aliases · garment_maps · item_base_measurements · regles_grading
(out-of-scope) · mesures_perfil · base_measurements · measurement_changes ·
model_grading_overrides · model_grading_rules · alerts · graded_specs · pattern_poms`.

---

## Categoria A — FUSIÓ (prim LOS → canònic ric)

Acció 4B: re-apuntar `CustomerPOMAlias(LOS).pom` del prim → canònic (l'àlies conserva el
`client_code`, el nom del client es preserva); moure la resta de refs vives; retirar el prim.
**Confiança** ✓ = descripció+semàntica clara · ⚠ = confirmar amb Montse.

| prim (id·codi·nom_client) | àlies LOS | refs vives | → canònic (codi · EN · maps) | conf. |
|---|---|---|---|---|
| 434 · `T.1` · FRONT RISE | T1 | bm1·gs10·mgr1·mcl1 | **RI FR** · Rise (front) · 17 | ✓ |
| 435 · `T.2` · BACK RISE | T2 | bm1·gs10·mgr1·mcl1 | **RI BK** · Rise (back) · 17 | ✓ |
| 422 · `L.4` · FRONT NECK DROP | L4 | — | **NK DR FR** · Neck drop front · 34 | ✓ |
| 421 · `L.5` · BACK NECK DROP | L5 | — | **NK DR BK** · Neck drop back · 31 | ✓ |
| 419 · `A.1` · FRONT WIDTH | A1 | — | **AC FR** · Across front · 27 | ✓ |
| 517 · `A2` · BACK WIDTH | A2 | — | **AC BK** · Across back · 28 | ✓ |
| 423 · `H` · SLEEVE MUSCLE (1/2) | H19 | — | **BIC** · Sleeve width at bicep · 34 | ✓ |
| 551 · `H` · SLEEVE MUSCLE | H | — | **BIC** · Sleeve width at bicep · 34 | ✓ |
| 518 · `B1` · CHEST WIDTH RELAXED | B1 | — | **CH RLX** · Chest width (relaxed) · 4 | ✓ |
| 553 · `H11` · SLEEVE OPENING | H11 | — | **SL OP** · Sleeve opening / cuff width · 33 | ✓ |
| 431 · `K.2` · SHOULDER TO SHOULDER | K2 | bm3·gs10·mgr3·mcl3 | **AC SH** · Across shoulder (back) · 31 | ⚠ |
| 519 · `B2` · CHEST WIDTH EXTENDED | B2 | — | **CH STR** · Chest width (stretched) · 4 | ⚠ |
| 520 · `B3` · FRONT CHEST WIDTH | B3 | — | **CH** (Chest width, 36) o AC FR | ⚠ |
| 528 · `D` · HIP WIDTH | D | — | **HI PA** · Hip width (pants) · 17 (o HI top·31) | ⚠ |
| 556 · `H16` · CUFF OPENING | H16 | — | **SL OP** · Sleeve opening / cuff width · 33 | ⚠ |

**Notes de verificació:** T.1/T.2/L.4/L.5 tenen el canònic idèntic (Rise/Neck drop front-back).
`A.1`/`A2` → across front/back (el canònic ric existeix: AC FR 27 maps, AC BK 28). `H`
(sleeve muscle) = BIC (bicep). `K.2` "shoulder to shoulder" ≈ AC SH "across shoulder (back)"
— plausible però semàntica de nom diferent → **⚠ Montse**. `D` (hip width): canònic depèn de
peça (HI top vs HI PA pantalons); LOS `D` s'usa a pantalons → **HI PA**, confirmar.

---

## Categoria B — COMPLETAR (prim LOS sense canònic ric)

Acció 4B: NO fusionar (no hi ha equivalent canònic real). Afegir **traducció local ca**
(taula de traduccions que aportarà Claude Chat al gate) + metadades pendents (gènere/fit
neutres, no aplica) + entrar-los als `GarmentPOMMap` dels items on les fitxes LOSAN els usen
(font: `GRADING_SOURCES_LOSAN.md` del vault). **Cap d'aquests té traducció avui.**

Agrupats per família (id·codi·nom_client). ~121 prims:

**Amplada/llargada de detall (relaxat/estès, no al canònic):**
`518→A` ja a A. `524 C1` WAIST WIDTH EXTENDED · `523 C4` WAIST WIDTH RELAXED · `525 C2` FRONT
WAIST WIDTH RELAXED · `526 C5` BACK WAIST WIDTH RELAXED · `527 C6` BACK WAIST EXTENDED · `521
C3` WAIST LOCATION · `522 CL` WAIST JOIN · `534 E3`/`535 E4` BOTTOM WIDTH RELAXED/EXTENDED ·
`536 E5` FRONT BOTTOM WIDTH · `537 E7` BOTTOM HEIGHT · `430 E.8` BOTTOM DIFFERENCE · `532 F5`/
`533 F6` LEG OPENING RELAXED/EXTENDED · `530 F1`/`531 F2` FRONT/BACK LEG OPENING.
*(⚠ `C4`/`C1` podrien mapar a WA/EL WA RLX; el canònic no distingeix relaxat/estès per a la
majoria de peces → COMPLETAR per defecte, Montse decideix si fusiona.)*

**Localitzacions (location, el canònic només té la mesura, no la ubicació):**
`515 A` FRONT WIDTH LOCATION · `516 A3` BACK WIDTH LOCATION · `514 BJ` FRONT&BACK WIDTH
LOCATION · `386 D.11-M79` HIP LOCATION · `529 D22` KNEE LOCATION · `568 M4` CUT LOCATION ·
`546 MF` SIDE SEAM MOVED FORWARD · `507 J1` SHOULDER DROP LOCATION · `508 J2` SHOULDER MOVE
FORWARD · `538 D18`/`540 D19` FRONT/BACK CROTCH WIDTH LOCATION.

**Butxaques (O.xx / W.xx) — sense canònic de butxaca detallat:**
`585 O9`·`586 O11`·`587 O12`·`588 O13`·`589 O14`·`590 O16`·`591 O17`·`592 O18`·`593 O19`·`594
O20`·`595 O23`·`596 O25`·`597 O28`·`603 O29`·`604 O30`·`605 O33`·`606 O34`·`598 O36`·`599 O38`·
`600 O39`·`601 O40`·`602 O41`·`394 O.27-M79`·`395 O.32-M79` · butxaca interior `607 W4`·`608
W5`·`609 W6`·`610 W7`·`611 W9`.

**Cantonells/canesús (yoke) i colls/tapetes:**
`564 S13`·`565 S25`·`561 S27`·`562 S28`·`563 S30` (yokes) · `474 E6`·`475 E7`·`476 E8`·`477
E88`·`584 AB`·`583 S2`·`577 S3`·`511 S8`·`582 S37`·`581 S` (collar/placket) · `573 S34` FRONT
COVER · `575 S45` BACK OPENING · `509 FP` SHOULDER PIECE.

**Punys/mànega detall:** `554 H14`·`555 H15`·`556 H16`(→ vegeu FUSIÓ ⚠)·`557 H17`·`558 GL`·
`559 GN`·`560 GM`·`552 G5` ELBOW LOC·`550 GA` SLEEVE INSEAM·`547 H7`·`548 H8`·`549 H9` ARMHOLE.

**Bragueta/entrecuix/canyella:** `487 BR` FLY WIDTH·`542 R9` FLY OPENING·`543 R10` FALSE FLY·
`539 D6`/`541 D7` CROTCH WIDTH·`617 C12`·`613/612 S55/S54`.

**Caputxa/cordó/serrell/plecs/pinces:** `425 S.10` HOOD LENGTH·`426 S.56` HOOD PIECE·`614 S53`
·`612 S54`·`613 S55` HOOD · `392 S.R1-M79`·`615 SR2`·`616 SR3` DRAWSTRING · `566 T13`/`567 T14`
PLEAT · `397 V.13-M79`/`396 V.14-M79` DART · `578 U4`·`579 U7`·`492 V` FRILL/RUFFLE · `580 V12`
FOLD · `569 V4`·`570 V5`·`571 V6`·`572 V7` PIECE.

**Altres LOS:** `512 U` RIB WIDTH·`513 U1` JETTING WIDTH·`510 L1` NECK TOTAL·`545 M20` BACK
LENGTH·`544 M19` FRONT LENGTH·`574 JC` TAPE WIDTH·`576 N4` SIDE OPENING·`385 C.14-M79` EYELET·
`497 IC2` ELBOW LENGTH·`468 JJ` ELBOW WIDTH (⚠ possible → ELB canònic 31 maps, confirmar)·
`427 T.5` EARS.

**⚠ Cas especial `389 M-M79` TOTAL LENGTH → COMPLETAR (NO fusionar):** confirmat el risc del
brief. "Total length" genèric s'usa a pantalons i tops; els canònics són específics (BL HPS
body length 37, OUTS outseam 13, DR L HPS dress 10, SK L skirt 2). No hi ha UN canònic
correcte → COMPLETAR, i a la re-sembra v3 mapar per peça (tops→BL HPS, pantalons→OUTS). Té
dades vives (bm1·gs10·mgr1·mcl1).

---

## Prims LOS amb DADES DE MODEL VIVES (14) — refs reals a moure

Aquests no es poden re-apuntar només per l'àlies: cal migrar `BaseMeasurement`,
`GradedSpec`, `ModelGradingRule`, `MeasurementChangeLog` al destí (o, si van a COMPLETAR,
mantenir-los). `GradedSpec` és regenerable (sortida del motor); `BaseMeasurement` és dada real.

| id·codi | bm | gs | mgr | mcl | destí proposat |
|---|---|---|---|---|---|
| 434 `T.1` | 1 | 10 | 1 | 1 | FUSIÓ→RI FR |
| 435 `T.2` | 1 | 10 | 1 | 1 | FUSIÓ→RI BK |
| 431 `K.2` | 3 | 10 | 3 | 3 | FUSIÓ→AC SH (⚠) |
| 457 `S` (Front armhole along seam) | 3 | 10 | 3 | 3 | COMPLETAR/AH? ⚠ |
| 386 `D.11-M79` | 1 | 10 | 1 | 1 | COMPLETAR (hip location) |
| 389 `M-M79` | 1 | 10 | 1 | 1 | COMPLETAR (total length) |
| 385 `C.14-M79` | 1 | 10 | 1 | 1 | COMPLETAR (eyelet loc) |
| 392 `S.R1-M79` | 2 | 10 | 2 | 2 | COMPLETAR (cord) |
| 394 `O.27-M79` | 1 | 10 | 1 | 1 | COMPLETAR (pocket) |
| 395 `O.32-M79` | 1 | 10 | 1 | 1 | COMPLETAR (pocket) |
| 396 `V.14-M79` | 1 | 10 | 1 | 1 | COMPLETAR (dart loc) |
| 397 `V.13-M79` | 1 | 10 | 1 | 1 | COMPLETAR (dart len) |
| 382 `S1-M76` (Collar width) | 2 | 36 | 0 | 2 | ⚠ NO-LOS? té àlies AJ; revisar |
| 468 `JJ` (Elbow width) | 0 | 0 | 2 | 0 | ⚠ FUSIÓ→ELB? |

---

## Prims SENSE àlies LOS (72) — FORA D'ABAST (només informar)

D'altres imports (BRW/Mango: sufixos `-M76`; noms com F/FF/J/I/E2/E4/EK1/EK2). **Molts amb
dades de model vives** (fins a `graded_specs=36`). NO es toquen en aquesta consolidació LOS.
Alguns dupliquen canònics (`I`→SL, `J`→BIC, `A.2`→AC BK, `E2`/`E4`/`EK1`/`EK2` neckline/thorax)
però consolidar-los és una decisió separada amb risc de dades vives → **diferit**. Exemples amb
dades: `1-M76`(gs36), `D1-M76`(gs36·mcl18), `E1-M76`(gs36), `G2s-M76`(gs36), `F1-M76`(gs36),
`437 F`(gs10), `438 FF`(gs10), `459 J`(gs10), `503 I`(gs5), `461 I3`, `465 E2`, `455 E4`,
`463 EK1`, `464 EK2`, `458 S2`, `382 S1-M76`(gs36).

---

## Traducció local (pas 4A.3)

- **FUSIÓ (~15):** l'àlies passa a resoldre a un canònic que **SÍ té traducció** (`pom_global`
  ca/en) → queden traduïts automàticament. La UI mostra canònic dalt + nom LOS sota (l'àlies).
- **COMPLETAR (~121):** el prim sobreviu i **NO té cap traducció** → el PAS 4B ha d'afegir la
  traducció ca (i en si cal) a cadascun. **Cap pot quedar sense.**

---

## GATE — decisions per a Agus / Montse

1. **Validar les 15 FUSIONS** (especialment les ⚠: K.2→AC SH, B2→CH STR, B3→CH/AC FR,
   D→HI PA, H16→SL OP, JJ→ELB).
2. **Confirmar M-M79 = COMPLETAR** (no fusió) i el mapatge per-peça a la v3.
3. **Aportar la taula de traduccions ca** per als ~121 COMPLETAR (Claude Chat).
4. **Confirmar l'abast**: NO tocar els 72 prims sense àlies LOS (dades vives d'altres imports).
5. Decidir el destí dels **14 prims LOS amb dades vives** (moure refs al canònic en FUSIÓ vs
   conservar en COMPLETAR) i dels `-M79` (artefactes d'un import LOS concret).

*Cap canvi aplicat. Aquest document és l'única sortida del PAS 4A. STOP fins al gate.*
