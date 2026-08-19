# DIAGNOSI · BROWNIE CATÀLEG v3 — per què F1 s'atura (i F4/F5 amb ella)

> **Data:** 2026-08-05 · **Tram:** BRIEF 4 · Catàleg Brownie v3
> **Estat:** F2 i F3 EXECUTADES I VERDES (commits `b631b12d`, `1f07faaa`).
> **F1 ATURADA** per blocador dur, i F4/F5 amb ella perquè hi construeixen a sobre.
> **Cap escriptura feta a POMMaster, GradingRuleSet ni Model.**

## 0 · Precondició (verificada abans de tocar res)

L'avís D-31.4 **és viu**: `backend/fhort/models_app/views.py:651-680` retorna 409
`GRADING_RESIDENTS_WIPE` amb `residents`, `per_origen` i `imported` de primer nivell, i
`confirmat_residents` és un flag SEPARAT de `confirmat` (views.py:608-612). Test a
`tests_sembra_grading.py:1291`.

**Provat de cap a peus contra els 26 models de Brownie a staging, read-only:**

| model | codi | estat | resultat |
|---|---|---|---|
| 163 | BRW-FW26-0001 | Nou | **409** GRADING_RESIDENTS_WIPE · 34 residents (34 CLIENT_RUN) |
| 182 | BRW-26-SS-0002 | Nou | **409** · 62 residents (60 CANONICAL · 2 MANUAL) |
| 188 | BRW-SS27-0001 | Nou | **409** · 49 residents (39 CANONICAL · 10 MANUAL) |
| 267 | BRW-26-FW-0036 | Nou | **409** · 34 residents (34 CLIENT_RUN) |
| 268 | BRW-FW27-0001 | Nou | **409** · 34 residents (34 CLIENT_RUN) |
| 269 | BRW-FW27-0002 | Nou | **409** · 25 residents (**21 IMPORTED** · 4 MANUAL) |
| 174 · 1307 | | Nou | **400** GRADING_SIZE_SYSTEM_MISMATCH (run divergent — bloqueig dur, correcte) |
| els altres 18 | | Nou | cap avís: 0 regles residents, assignació neta |

**255 regles residents de Brownie en risc**, 21 d'elles IMPORTED (les que vénen del document
del client i que la clau de primer nivell existeix per fer visibles). Amb
`confirmat_residents=True` la validació retorna `None` i deixa passar. **El guard funciona.**
I `models Tancat (entregats) = 0` ✅ — la precondició d'F5 es compleix.

## 1 · El blocador: la columna `pom_id` del full és de PROD

El full `docs/BROWNIE_CATALEG_POM_v3.xlsx` porta una columna `pom_id` per als 119 codis.
**Aquells identificadors són de PROD i no valen a staging.** Dels 119:

| | comptatge |
|---|---|
| ✅ el pk del full coincideix amb l'àlies viu de Brownie | **31** |
| 🔴 **DIVERGENT** — el pk del full apunta a un POM DIFERENT del que l'àlies ja fa servir | **51** |
| 🟠 sense àlies · el pk existeix a staging (cal comprovar-lo un a un) | 7 |
| 🔴 sense àlies · el pk **NO EXISTEIX** a staging (787, 795, 796, 871, 874) | 3 |
| 🟡 àlies viu però el full no li dona pk (G1) | 1 |
| 🆕 sense àlies ni pk — POM a encunyar | 26 |

La deriva és sistemàtica (un desplaçament de ~5-6 posicions al bloc 4xx-5xx), que és
exactament el que passa quan dos entorns encunyen el mateix catàleg en ordre diferent.

### Què passaria si s'apliquessin (mostra de 5 dels 51)

| codi | mesura que és | apunta ARA a | si s'apliqués el full |
|---|---|---|---|
| `S` | Front armhole along seam | 457 · Front armhole along seam ✅ (**4 mesures BRW vives**) | 462 · BACK NECKLINE WIDTH |
| `E2` | Across front width | 465 · THORAX WIDTH IN FRONT ✅ (**4 mesures vives**) | 459 · 1/2 Bicep width |
| `U2` | 1st BUTTON | 498 · First button measured from collar seam ✅ (**1 mesura viva**) | 485 · POCKET MOUTH WIDTH |
| `V` | RUFFLE HEIGHT | 492 · RUFFLE HEIGHT ✅ | 498 · First button from collar seam |
| `IC` | ELBOW PATCH PLACEMENT | 495 · ELBOW POSITION | 504 · Sleeve length from CB over shoulderpoint |

**Els àlies vius de staging ja apunten al POM correcte en pràcticament tots els casos.**
Aplicar la columna del full no seria migrar el catàleg: seria trencar-lo, i sobre mesures
que ja tenen valors desats.

## 2 · Segon blocador, independent del primer: `POMMaster` és COMPARTIT amb LOSAN

El full és un catàleg **de client** (els codis de fitxa de Brownie). `POMMaster` és el
catàleg **del tenant**, i LOSAN hi entra amb 240 àlies propis.

**17 dels POMs que el v3 reanomena els fa servir també LOSAN.** Exemples:

| POM | es diu ara | el v3 el vol dir | LOSAN hi entra per |
|---|---|---|---|
| 273 | Chest width | 1/2 chest width (armpit to armpit) | `B` |
| 278 | Across shoulder (back) | Shoulder to shoulder | `K2` |
| 326 | Skirt sweep (bottom width) | Bottom width (leg opening) | `E` |
| 295 | Sleeve width at bicep | 1/2 Bicep width | `H`, `H19` |
| 297 | Sleeve opening / Cuff width | Sleeve opening relaxed | `H11`, `H.11` |
| 389 | TOTAL LENGTH | FRONT/BACK CENTER TOTAL LENGTH | `M` |

Escriure els noms del v3 a `POMMaster.nom_client` **filtraria la nomenclatura de Brownie
dins el catàleg de LOSAN**. La lectura alternativa —que «actualitza nom» vulgui dir la
descripció de l'ÀLIES i no el `nom_client` del POM— és compatible amb tot el full, però
llavors la columna `pom_id` no té feina a fer i la peça canvia de forma.
**Aquesta és una decisió de disseny, no una ambigüitat mecànica.**

## 3 · Tercer: ~15 codis no tenen POM resoluble a staging

Bona notícia primer: la majoria dels 26 «🆕 nous» **ja existeixen** a staging amb un codi
d'origen LOSAN, tal com el mateix full insinua («🆕 de LOSAN (D6)», «(S37)», «(AB)»…):

`CR`→539 D6 · `CR1`→541 D7 · `CR4`→413 CR L · `CP`→582 S37 · `CB1`→584 AB ·
`HP`→426 S.56 · `H1`→614 S53 · `HZ1`→616 SR3 · `XV`→513 U1 · `Q`→397 V.13-M79 ·
`QP`→396 V.14-M79 · `QTP`→566 T13 · `K`→669 C.13 · `KU`→385 C.14-M79 · `U4`→**578** (no 580)

Encunyar-los de nou duplicaria mesures que ja hi són. Però en queden amb **dos candidats o
cap**, i cadascun és una decisió d'identitat de POM (zona intocable per CLAUDE.md):

- `CR3` CROTCH WIDTH PLACEMENT → 538 (D18 · FRONT) **o** 540 (D19 · BACK)?
- `QT` PLEAT WIDTH → 345 (PLT DEP · Pleat depth) **o** 567 (T14 · PLEAT)?
- `W` ELASTIC WIDTH / `WP` ELASTIC PLACEMENT → 414/415/416 (EL RLX/EXT/POS) **o** 672 (V.9)?
- `N` MOTIVE PLACEMENT → només 683 (E.9 · **BOTTOM** motive location) — parcial
- `X` STITCHING WIDTH / `XP` → només 674 (EV · WAIST HEIGHT stitching) — parcial
- `KB` BUTTON PLACEMENT → cap (342 és Button **spacing**)
- `GD` / `GD1` GODET → **cap**, ni per nom ni per pk (795/796 no existeixen)
- `SLT` SLIT → el full diu «àlies `0` → pom 871»; a staging `0` → 461 (Sleeve slit) i 871 no existeix
- `ZL1` BOW LENGTH → cap (el pk 487 del full és FLY WIDTH; l'àlies `LZ1` viu apunta a ELBOW LENGTH ❌)
- `D1` / `G1` → el rebateig depèn de partir el POM 453 «Bottom hem / **Bottom rib height**», que avui conflacta les dues coses

## 4 · Contradiccions entre fulls (ja reportades a F3)

- **`PR2`** — CATALEG el declara POM PROPI («Pocket position from waistband», ✅ RESTITUÏT
  03/08, «NO es retira») i GERMANS_OFICIALS el declara 2a butxaca de PR1. Incompatibles.
  La lectura del CATALEG té POMMaster 357 (PKT WB) al darrere.
- **`J4`** — el brief demana desdoblar «IC, J4 (nous, buits)» del POM 504, però **J4 no és a
  cap full** i a staging no hi ha cap àlies `J4`.
- **`FF`/`F3`/`F4`** — el brief els demana «nous»; els tres ja existeixen com a àlies de
  Brownie, i el desdoblament del 389 ja és mig fet (FF→438 propi; F3 i F4 sí que comparteixen 389).
- **`IC`/`J4` del 504** — a staging IC→495, i el 504 és «Sleeve length from CB over
  shoulderpoint» (àlies `I4`). El compartiment que el full descriu no existeix aquí.

## 5 · Per què s'atura en comptes de decidir-ho l'agent

CLAUDE.md: *«No tocar POMs… tret que la peça ho demani explícitament»* — la peça ho demana,
però també: *«Aturar-se per blocador dur o contradicció de paradigma»*, i Patró C:
*«Claude Chat dissenya · Claude Code executa · l'Agus decideix»*. Les tres coses de sobre
(quin pk val, si es toca `nom_client` compartit, quin POM és cada codi ambigu) són decisions
d'identitat de dades, no feina mecànica.

I sobretot: **F4 i F5 hi construeixen a sobre.** El ruleset BRW-CATALEG-v3 és una regla PER
POM, i F5 migra 26 models reals cap a ell esborrant-los 255 regles residents. Sembrar-lo
sobre una resolució de POM inventada i després cremar les residents seria exactament
«construir sobre una peça no-verda», amb 21 regles IMPORTED entre les que cauen.

## 6 · Què cal per desbloquejar (una sola passada de decisions)

1. **La columna `pom_id` es descarta a staging?** (proposta: sí — resoldre per CODI contra
   l'àlies viu, i el `pom_id` només com a control creuat, mai escrit).
2. **«Actualitza nom» és `POMMaster.nom_client` o la descripció de l'àlies?** (proposta:
   l'àlies — `nom_client` és compartit amb LOSAN).
3. **Els ~15 codis ambigus de §3** — un POM cadascun, o encunyar-ne de nous.
4. **`PR2`** — POM propi o 2a butxaca.
5. **`J4`** — existeix o s'elimina del brief.

Amb això, F1/F4/F5 són una passada mecànica: la taula completa dels 119 codis és a §7 i la
sembra es pot escriure amb la mateixa forma que `seed_brownie_germans` (dry-run per defecte,
`update_or_create`, res que es repunti en silenci).

## 7 · Taula completa dels 119 codis (abans / després)

⚠️LOSAN marca els POMs que LOSAN també fa servir.

| CODI | nom v3 | pom_id full | resol a staging | estat | què hi ha al pk del full | candidat per NOM |
|---|---|---|---|---|---|---|
| `A` | 1/2 chest width (armpit to armpit) | 273 | 273 · Chest width ⚠️LOSAN | ✅ coincideix | CH · Chest width | — |
| `A1` | UNDERBUST WIDTH | 460 | 466 · UNDERBUST WIDTH | 🔴 DIVERGENT | J1 · Sleeve opening relaxed | 466:A1 |
| `E` | Shoulder to shoulder | 457 | 278 · Across shoulder (back) ⚠️LOSAN | 🔴 DIVERGENT | S · Front armhole along seam | 431:K.2 |
| `E1` | Shoulder width at true shoulder | 277 | 277 · Shoulder width ⚠️LOSAN | ✅ coincideix | SH · Shoulder width | — |
| `E2` | Across front width (11cm from HPS) | 459 | 465 · THORAX WIDTH IN FRONT | 🔴 DIVERGENT | J · 1/2 Bicep width | — |
| `E3` | Across back width (11cm from HPS) | 420 | 420 · BACK WIDTH | ✅ coincideix | A.2 · BACK WIDTH | — |
| `EK` | Neck width seam to seam | 301 | 301 · Neck width ⚠️LOSAN | ✅ coincideix | NK W · Neck width | — |
| `EKK` | BACK NECKLINE WIDTH | 454 | 462 · BACK NECKLINE WIDTH | 🔴 DIVERGENT | E1 · Shoulder seam | 462:EKK |
| `EK1` | Front neck drop from HPS to seam | 455 | 463 · FRONT NECKLINE DROP | 🔴 DIVERGENT | E4 · Shoulder Forward | — |
| `SF` | Armhole depth from HPS | 284 | 284 · Armhole depth ⚠️LOSAN | ✅ coincideix | AH DEP · Armhole depth | — |
| `S` | Front armhole along seam | 462 | 457 · Front armhole along seam ⚠️LOSAN | 🔴 DIVERGENT | EKK · BACK NECKLINE WIDTH | 457:S |
| `S2` | Back armhole along seam | 463 | 458 · Back armhole along seam | 🔴 DIVERGENT | EK1 · FRONT NECKLINE DROP | 458:S2 |
| `D` | Bottom width (leg opening) | 326 | 326 · Skirt sweep (bottom width) ⚠️LOSAN | ✅ coincideix | SK SW · Skirt sweep (bottom width) | — |
| `B` | Waist width | 515 | 275 · Waist width ⚠️LOSAN | 🔴 DIVERGENT | A · FRONT WIDTH LOCATION | 275:WA |
| `BT` | Waist position from HPS | 461 | 467 · WAIST DROP | 🔴 DIVERGENT | I3 · Sleeve slit | — |
| `I` | Sleeve length | 787 | 503 · Sleeve length | 🔴 DIVERGENT | INEXISTENT | 292:SL / 503:I |
| `J` | 1/2 Bicep width | 295 | 295 · Sleeve width at bicep ⚠️LOSAN | ✅ coincideix | BIC · Sleeve width at bicep | 459:J |
| `JJ` | SLEEVE WIDTH AT ELBOW | 464 | 296 · Sleeve width at elbow ⚠️LOSAN | 🔴 DIVERGENT | EK2 · BACK NECKLINE DROP | 296:ELB |
| `I2` | SLEEVE HEM WIDTH | 465 | 469 · SLEEVE HEM WIDTH | 🔴 DIVERGENT | E2 · THORAX WIDTH IN FRONT | 469:I2 |
| `J1` | Sleeve opening relaxed | 297 | 297 · Sleeve opening / Cuff width ⚠️LOSAN | ✅ coincideix | SL OP · Sleeve opening / Cuff width | 460:J1 |
| `J3` | CUFF HEIGHT | 299 | 299 · Cuff height ⚠️LOSAN | ✅ coincideix | CUF H · Cuff height | 299:CUF H |
| `I3` | CUFF SLIT | 502 | 461 · Sleeve slit | 🔴 DIVERGENT | M2 · Front piece width at the bottom (excl.lace) | — |
| `FJ` | WINGSPAN LENGTH | 467 | 470 · WINGSPAN LENGTH | 🔴 DIVERGENT | BT · WAIST DROP | 470:FJ |
| `F` | Centre front length from HPS | 468 | 437 · Centre front length at CF | 🔴 DIVERGENT | JJ · ELBOW WIDTH | — |
| `FF` | Centre back length from HPS | 389 | 438 · Centre back length at CB | 🔴 DIVERGENT | M-M79 · TOTAL LENGTH | — |
| `F1` | Curve at side (difference between CB length and side seam) | 469 | 437 · Centre front length at CF | 🔴 DIVERGENT | I2 · SLEEVE HEM WIDTH | — |
| `F2` | TOTAL SIDE LENGTH | 470 | 437 · Centre front length at CF | 🔴 DIVERGENT | FJ · WINGSPAN LENGTH | — |
| `F3` | FRONT CENTER TOTAL LENGTH | 389 | 389 · TOTAL LENGTH ⚠️LOSAN | ✅ coincideix | M-M79 · TOTAL LENGTH | — |
| `F4` | BACK CENTER TOTAL LENGTH | 389 | 389 · TOTAL LENGTH ⚠️LOSAN | ✅ coincideix | M-M79 · TOTAL LENGTH | — |
| `FB` | BODY LENGTH | 381 | 381 · Straight Back Body Length | ✅ coincideix | G2s-M76 · Straight Back Body Length | — |
| `E4` | Shoulder forward | 458 | 455 · Shoulder Forward | 🔴 DIVERGENT | S2 · Back armhole along seam | 455:E4 |
| `E5` | Shoulder drop (from HPS to shoulder point) | 286 | 286 · Shoulder drop ⚠️LOSAN | ✅ coincideix | SH DR · Shoulder drop | — |
| `EK2` | Back neck drop from HPS to seam | 456 | 464 · BACK NECKLINE DROP | 🔴 DIVERGENT | EP · Collarstand height at CB | — |
| `G1` | Rib height | — | 453 · Bottom hem / Bottom rib height | 🟡 àlies viu, full sense pk | — | — |
| `D1` | Bottom hem height | 503 | — | 🟠 sense àlies · pk existeix | I · Sleeve length | — |
| `BF` | Waistband height | 320 | 320 · Waistband height ⚠️LOSAN | ✅ coincideix | WB H · Waistband height | 320:WB H |
| `FC` | HIP POSITION | 380 | 380 · Hip Position | ✅ coincideix | E1-M76 · Hip Position | 380:E1-M76 |
| `C` | Hip width | 276 | 276 · Hip width (top) | ✅ coincideix | HI · Hip width (top) | 528:D |
| `CT` | Thigh width | 309 | 309 · Thigh width ⚠️LOSAN | ✅ coincideix | THI · Thigh width | 309:THI |
| `FR` | KNEE POSITION | 472 | 472 · KNEE POSITION | ✅ coincideix | FR · KNEE POSITION | 472:FR |
| `RT` | KNEE WIDTH | 310 | 310 · Knee width ⚠️LOSAN | ✅ coincideix | KNE · Knee width | 310:KNE |
| `M` | Leg opening | 311 | — | 🟠 sense àlies · pk existeix | LEG OP · Leg opening | 311:LEG OP |
| `FT` | Pants length (outseam) | 473 | 473 · PANTS LENGTH | ✅ coincideix | FT · PANTS LENGTH | — |
| `FI` | Inseam length | 312 | 312 · Inseam length | ✅ coincideix | INS · Inseam length | 312:INS |
| `FS` | SKIRT LENGTH | 324 | 324 · Skirt length | ✅ coincideix | SK L · Skirt length | 324:SK L |
| `FD` | Front rise length (waistband included) | 431 | 321 · Rise (front) ⚠️LOSAN | 🔴 DIVERGENT | K.2 · SHOULDER TO SHOULDER | — |
| `FE` | Back rise length (waistband included) | 432 | 322 · Rise (back) ⚠️LOSAN | 🔴 DIVERGENT | AW · ARTWORK POSITION | — |
| `GD` | GODET LENGTH AT LONGEST POINT | 795 | — | 🔴 sense àlies · pk INEXISTENT | INEXISTENT | — |
| `GD1` | GODET LENGTH AT THE SEAMS | 796 | — | 🔴 sense àlies · pk INEXISTENT | INEXISTENT | — |
| `CR` | FRONT CROTCH WIDTH | — | — | 🆕 sense àlies ni pk | — | 539:D6 |
| `CR1` | BACK CROTCH WIDTH | — | — | 🆕 sense àlies ni pk | — | 541:D7 |
| `CR3` | CROTCH WIDTH PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `CR4` | CROTCH LENGTH | — | — | 🆕 sense àlies ni pk | — | 413:CR L |
| `FS5` | Lining length difference | — | — | 🆕 sense àlies ni pk | — | — |
| `E6` | FRONT COLLAR PANEL HEIGHT | 474 | 474 · FRONT COLLAR PANEL HEIGHT | ✅ coincideix | E6 · FRONT COLLAR PANEL HEIGHT | 474:E6 |
| `E7` | CENTER COLLAR PANEL HEIGHT | 475 | 475 · CENTER COLLAR PANEL HEIGHT | ✅ coincideix | E7 · CENTER COLLAR PANEL HEIGHT | 475:E7 |
| `E8` | COLLAR PANEL LENGTH | 476 | 476 · COLLAR PANEL LENGTH | ✅ coincideix | E8 · COLLAR PANEL LENGTH | 476:E8 |
| `E88` | COLLAR JOIN | 477 | 477 · COLLAR JOIN | ✅ coincideix | E88 · COLLAR JOIN | 477:E88 |
| `EL` | FLAP WIDTH | 478 | 478 · FLAP WIDTH ⚠️LOSAN | ✅ coincideix | EL · FLAP WIDTH | 478:EL |
| `EP` | Collar height at CB | 479 | 456 · Collarstand height at CB | 🔴 DIVERGENT | PC · NECK PIPE WIDTH | — |
| `PC` | NECK PIPE WIDTH | 480 | 479 · NECK PIPE WIDTH | 🔴 DIVERGENT | T · SHOULDER LENGTH | 479:PC |
| `CP` | COLLAR PEAK | — | — | 🆕 sense àlies ni pk | — | 582:S37 |
| `CB1` | COLLAR TOTAL CONTOUR | — | — | 🆕 sense àlies ni pk | — | — |
| `HL` | HOOD LENGTH | 425 | 425 · HOOD LENGTH ⚠️LOSAN | ✅ coincideix | S.10 · HOOD LENGTH | 425:S.10 |
| `HW` | HOOD WIDTH | 347 | 347 · Hood width ⚠️LOSAN | ✅ coincideix | HD W · Hood width | 347:HD W |
| `H1` | HOOD WIDTH PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `HP` | HOOD PIECE WIDTH | — | — | 🆕 sense àlies ni pk | — | 426:S.56 |
| `HZ` | DRAWSTRING LENGTH | — | — | 🆕 sense àlies ni pk | — | — |
| `HZ1` | DRAWSTRING CHANNEL | — | — | 🆕 sense àlies ni pk | — | 616:SR3 |
| `L` | BACK YOKE | 436 | 484 · BACK YOKE | 🔴 DIVERGENT | D · 1/2 bottom width relaxed | 484:L |
| `P` | CENTER BACK YOKE HEIGHT | 489 | 484 · BACK YOKE | 🔴 DIVERGENT | TR · PLACKET HEIGHT | — |
| `P1` | SIDE YOKE HEIGHT | 437 | 442 · Chest piece height at center | 🔴 DIVERGENT | F · Centre front length at CF | — |
| `P2` | CENTER FRONT YOKE HEIGHT | 488 | 441 · Chest piece height at side seam | 🔴 DIVERGENT | BR1 · FLY LENGTH | — |
| `R` | POCKET MOUTH WIDTH | 490 | 485 · POCKET MOUTH WIDTH | 🔴 DIVERGENT | BL · FOLD LENGTH | 485:R |
| `R1` | POCKET MOUTH LENGTH | 491 | 486 · POCKET MOUTH LENGTH | 🔴 DIVERGENT | BW · FOLD WIDTH | 486:R1 |
| `R2` | Pocket width | 349 | 349 · Pocket width ⚠️LOSAN | ✅ coincideix | PKT W · Pocket width | 349:PKT W |
| `R3` | Pocket length | 435 | 390 · FRONT POCKET LENGTH ⚠️LOSAN | 🔴 DIVERGENT | T.2 · BACK RISE | — |
| `PR1` | Pocket position from side seam | 874 | 354 · Chest pocket position | 🔴 DIVERGENT | INEXISTENT | — |
| `PR2` | Pocket position from waistband | 357 | — | 🟠 sense àlies · pk existeix | PKT WB · Pocket placement from waistband | — |
| `BR` | FLY WIDTH | 492 | 487 · FLY WIDTH ⚠️LOSAN | 🔴 DIVERGENT | V · RUFFLE HEIGHT | 487:BR |
| `BR1` | FLY LENGTH | 493 | 488 · FLY LENGTH | 🔴 DIVERGENT | VR · RUFFLE LENGTH | 488:BR1 |
| `CR2` | ZIPPER | 341 | 341 · Zipper length ⚠️LOSAN | ✅ coincideix | ZIP L · Zipper length | — |
| `TR` | PLACKET HEIGHT | 494 | 489 · PLACKET HEIGHT | 🔴 DIVERGENT | JTA · SLEEVE STRAP / SLEEVE STRAP | 489:TR |
| `U` | FRONT OVERLAP | 495 | 439 · Width sequins piece (CF) | 🔴 DIVERGENT | IC · ELBOW POSITION | — |
| `U1` | BUTTON SPACING | 342 | 440 · Height sequins piece (CF) | 🔴 DIVERGENT | BTN SP · Button spacing | 342:BTN SP |
| `U2` | 1st BUTTON | 485 | 498 · First button measured from collar seam | 🔴 DIVERGENT | R · POCKET MOUTH WIDTH | — |
| `U3` | LAST BUTTON | 486 | 499 · Last button measured from armhole seam | 🔴 DIVERGENT | R1 · POCKET MOUTH LENGTH | — |
| `UT1` | LOOPS | 484 | 483 · LOOPS | 🔴 DIVERGENT | L · BACK YOKE | 483:UT1 |
| `K` | BUTTONHOLE PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `KB` | BUTTON PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `KU` | EYELET PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `ZF` | BELT WIDTH | 363 | — | 🟠 sense àlies · pk existeix | BELT W · Belt width | 363:BELT W |
| `ZL` | BELT LENGTH | 362 | — | 🟠 sense àlies · pk existeix | BELT L · Belt length | 362:BELT L |
| `ZL1` | BOW LENGTH | 487 | — | 🟠 sense àlies · pk existeix | BR · FLY WIDTH | 660:SR10 |
| `T` | STRAP LENGTH | 481 | 480 · SHOULDER LENGTH | 🔴 DIVERGENT | T1 · TIE WIDTH | 656:R.1 |
| `T1` | STRAP WIDTH | 482 | 481 · TIE WIDTH | 🔴 DIVERGENT | T2 · TIGHT POSITION | — |
| `T2` | STRAP PLACEMENT | 483 | 482 · TIGHT POSITION | 🔴 DIVERGENT | UT1 · LOOPS | — |
| `BL` | FOLD LENGTH | 496 | 490 · FOLD LENGTH | 🔴 DIVERGENT | IC1 · ELBOW WIDTH | 490:BL |
| `BW` | FOLD WIDTH | 497 | 491 · FOLD WIDTH | 🔴 DIVERGENT | IC2 · ELBOW LENGTH | 491:BW |
| `Q` | DART LENGTH | — | — | 🆕 sense àlies ni pk | — | 397:V.13-M79 |
| `QP` | DART PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `QT` | PLEAT WIDTH | — | — | 🆕 sense àlies ni pk | — | — |
| `QTP` | PLEAT PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `V` | RUFFLE HEIGHT | 498 | 492 · RUFFLE HEIGHT ⚠️LOSAN | 🔴 DIVERGENT | U2 · First button measured from collar seam | 492:V |
| `VR` | RUFFLE LENGTH | 499 | 493 · RUFFLE LENGTH | 🔴 DIVERGENT | U3 · Last button measured from armhole seam | 493:VR |
| `U4` | FLOUNCE HEIGHT | 580 | — | 🟠 sense àlies · pk existeix | V12 · FOLD | 578:U4 |
| `SLT` | SLIT | 871 | — | 🔴 sense àlies · pk INEXISTENT | INEXISTENT | — |
| `JTA` | SLEEVE STRAP | 500 | 494 · SLEEVE STRAP / SLEEVE STRAP | 🔴 DIVERGENT | D1 · 1/2 bottom width extended | — |
| `IC` | ELBOW PATCH PLACEMENT | 504 | 495 · ELBOW POSITION | 🔴 DIVERGENT | I4 · Sleeve length from CB over shoulderpoint (incl cuff) | — |
| `IC1` | ELBOW PATCH WIDTH | 505 | 296 · Sleeve width at elbow ⚠️LOSAN | 🔴 DIVERGENT | L1 · Back yoke side height from HPS | — |
| `IC2` | ELBOW PATCH LENGTH | 506 | 497 · ELBOW LENGTH ⚠️LOSAN | 🔴 DIVERGENT | 0 · Back opening length | — |
| `N` | MOTIVE PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `NF` | MOTIVE WIDTH | — | — | 🆕 sense àlies ni pk | — | — |
| `NL` | MOTIVE HEIGHT | — | — | 🆕 sense àlies ni pk | — | — |
| `W` | ELASTIC WIDTH | — | — | 🆕 sense àlies ni pk | — | — |
| `WP` | ELASTIC PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `X` | STITCHING WIDTH | — | — | 🆕 sense àlies ni pk | — | — |
| `XP` | STITCHING PLACEMENT | — | — | 🆕 sense àlies ni pk | — | — |
| `XV` | JETTING WIDTH | — | — | 🆕 sense àlies ni pk | — | 513:U1 |


TALLY: {'✅ coincideix': 31, '🔴 DIVERGENT': 51, '🟡 àlies viu, full sense pk': 1, '🟠 sense àlies · pk existeix': 7, '🔴 sense àlies · pk INEXISTENT': 3, '🆕 sense àlies ni pk': 26}

---

# ADDENDUM · 2026-08-05 · F1 reprès amb el criteri ratificat

Criteri (Agus, 05/08): **el v3 no importa `pom_id`; importa NOM + GRADING + ESTRUCTURA i els
casa contra el que staging ja té.** Ordre: àlies viu → `RESOLUCIO` (POM existent, sovint de
LOSAN) → `ENCUNYAR`. Taula a `backend/fhort/pom/seed_data/brownie_cataleg_v3.py`.

## Veredicte dels 119

| veredicte | codis |
|---|---|
| **UPDATE existent** (D1 · l'àlies viu de Brownie ja apunta al POM bo) | 82 |
| **♻️ àlies sobre POM existent** (D3 · reutilitzar, sovint via LOSAN) | 23 |
| **🆕 ENCUNYAR** (D4) | 14 |
| ❓ sense regla | 0 |

**48 dels codis resolts apunten a un POM que un altre client també fa servir** → per D2 el
nom canònic no es toca i l'etiqueta de Brownie va a l'àlies.

## FF / F3 / F4 / J4 — l'encàrrec explícit

**`FF` → POM 438: COHERENT. No s'hi toca res.** El desdoblament ja està fet i la feina és zero:
- àlies: **només `BRW:FF`** — no és compartit amb LOSAN;
- nom: POM «Centre back length at CB» + descripció d'àlies «Centre back length from HSP (incl
  hem/rib)» ≡ el que el full en diu, «Centre back length from HPS»;
- grading: rs115/rs124 hi donen LINEAR base **1,00**, que és el Δ XXS→XS del full (1 · 1 · 1,5
  · 1,5); el que el v3 hi afegeix és el BREAK, i això és feina d'F4, no d'F1.

**`J4`: no es pot encunyar.** No és a cap full del v3 — no en tenim nom, ni lògica, ni grading,
ni família. I el compartiment que el justificava no existeix a staging: el POM 504 és «I4 ·
Sleeve length from CB over shoulderpoint» amb àlies `BRW:I4`, i `IC` ja té POM propi (495).

**`F3`/`F4`: NO estan desdoblats** — v. col·lisions.

## 🔴 Col·lisions · més d'un concepte del v3 sobre un sol POM

Aquí «UPDATE el nom» no té resposta: un POM no pot dir-se dues coses. **No se n'ha tocat cap.**

| POM | mesures BRW vives | codis que hi cauen |
|---|---|---|
| 437 «Centre front length at CF» | **5** | `F` Centre front length from HPS · `F1` Curve at side (difference) · `F2` TOTAL SIDE LENGTH |
| 296 «Sleeve width at elbow» ⚠️LOS | **10** | `JJ` SLEEVE WIDTH AT ELBOW · `IC1` ELBOW PATCH WIDTH |
| 389 «TOTAL LENGTH» ⚠️LOS | 0 | `F3` FRONT CENTER TOTAL LENGTH · `F4` BACK CENTER TOTAL LENGTH |
| 484 «BACK YOKE» | 0 | `L` BACK YOKE · `P` CENTER BACK YOKE HEIGHT |
| 453 «Bottom hem / Bottom rib height» | 1 | `G1` Rib height · `D1` Bottom hem height — **resolta pel rebateig**: D1 es queda 453, G1 s'encunya |

Pista per a 296: a staging existeix **496 «IC1 · ELBOW WIDTH»**, avui sense àlies de Brownie —
podria ser el destí d'`IC1` sense encunyar res.

## ⚠️ Deriva de concepte dins dels UPDATE (13 de 82)

El nom del v3 i el del POM no parlen del mateix. En 7 casos el full ho anuncia («✏️ era
SHOULDER LENGTH») i és un rebateig legítim; en els altres l'àlies sembla mal enganxat i
renombrar el POM li canviaria el significat, no l'etiqueta:

| codi | v3 diu | el POM es diu | mesures | lectura |
|---|---|---|---|---|
| `P1` | SIDE YOKE HEIGHT | 442 · Chest piece height at center | 1 | canesú ≠ peça de pit |
| `P2` | CENTER FRONT YOKE HEIGHT | 441 · Chest piece height at side seam | 1 | íd. |
| `U` | FRONT OVERLAP | 439 · Width sequins piece (CF) | 1 | el full diu «la BD mana: U és FRONT OVERLAP» — però és la BD de PROD |
| `U1` | BUTTON SPACING | 440 · Height sequins piece (CF) | 1 | íd. |
| `F1` `F2` | v. col·lisions | 437 | 5 | |
| `IC` | ELBOW PATCH PLACEMENT | 495 · ELBOW POSITION | 0 | posició de colze ≠ posició de la coquera |
| `I3` | CUFF SLIT | 461 · Sleeve slit | 2 | prou proper: l'obertura de puny és una obertura de màniga |
| `BT` `T` `T1` `T2` `U2` | — | — | — | rebateigs que el full anuncia ✅ |

## D4 · els 14 a encunyar (pendents de repàs abans de crear-los)

| codi | nom | lògica | per què no es reutilitza res |
|---|---|---|---|
| `G1` | Rib height | FIXED | el rebateig; 453 conflacta baix+canalé, 300 és rib **cuff**, 329 rib **hem** |
| `FS5` | Lining length difference | FIXED | 596 és «front lining length» (llargada, no diferència) |
| `CR3` | Crotch width placement | LINEAR+BREAK | hi ha 538 FRONT i 540 BACK, cap de genèric |
| `KB` | Button placement | LINEAR+BREAK | 342 és «Button spacing» (separació ≠ col·locació) |
| `QT` | Pleat width | FIXED | 345 és «Pleat depth» (profunditat ≠ amplada) |
| `N` | Motive placement | LINEAR+BREAK | només 683 «BOTTOM motive location»; el v3 el vol genèric |
| `NF` | Motive width | FIXED | cap |
| `NL` | Motive height | FIXED | cap |
| `W` | Elastic width | FIXED | 414/415 són la goma relaxada/estirada (estats), no l'amplada |
| `X` | Stitching width | FIXED | només 674 «WAIST HEIGHT stitching» |
| `XP` | Stitching placement | LINEAR+BREAK | cap |
| `GD` | Godet length at longest point | LINEAR+BREAK | cap godet a staging (795 no existeix) |
| `GD1` | Godet length at the seams | LINEAR+BREAK | íd. (796 tampoc) |
| `SLT` | Slit | FIXED | 461 és «Sleeve slit», específic (871 no existeix) |

## Taula completa dels 119 amb veredicte

| CODI | nom v3 | lògica | Δ | veredicte | POM staging | compartit |
|---|---|---|---|---|---|---|
| `A` | 1/2 chest width (armpit to armpit) | LINEAR+BREAK | 2 · 3 · 3 · 3 | UPDATE existent | 273 · Chest width | LOS |
| `A1` | UNDERBUST WIDTH | LINEAR+BREAK | 1 · 1.5 · 1.5 · 1.5 | UPDATE existent | 466 · UNDERBUST WIDTH |  |
| `E` | Shoulder to shoulder | LINEAR+BREAK | 1 · 1.5 · 1.5 · 1.5 | UPDATE existent | 278 · Across shoulder (back) | LOS |
| `E1` | Shoulder width at true shoulder | LINEAR+BREAK | 0.25 · 0.4 · 0.4 · 0.4 | UPDATE existent | 277 · Shoulder width | LOS |
| `E2` | Across front width (11cm from HPS) | LINEAR+BREAK | 1 · 1.5 · 1.5 · 1.5 | UPDATE existent | 465 · THORAX WIDTH IN FRONT |  |
| `E3` | Across back width (11cm from HPS) | LINEAR+BREAK | 1 · 1.5 · 1.5 · 1.5 | UPDATE existent | 420 · BACK WIDTH |  |
| `EK` | Neck width seam to seam | LINEAR+BREAK | 0.5 · 0.75 · 0.75 · 0.75 | UPDATE existent | 301 · Neck width | LOS |
| `EKK` | BACK NECKLINE WIDTH | LINEAR+BREAK | 0.5 · 0.75 · 0.75 · 0.75 | UPDATE existent | 462 · BACK NECKLINE WIDTH |  |
| `EK1` | Front neck drop from HPS to seam | LINEAR+BREAK | 0.25 · 0.4 · 0.4 · 0.4 | UPDATE existent | 463 · FRONT NECKLINE DROP |  |
| `SF` | Armhole depth from HPS | LINEAR+BREAK | 0.7 · 1 · 1 · 1 | UPDATE existent | 284 · Armhole depth | LOS |
| `S` | Front armhole along seam | LINEAR+BREAK | 0.7 · 1 · 1 · 1 | UPDATE existent | 457 · Front armhole along seam | LOS |
| `S2` | Back armhole along seam | LINEAR+BREAK | 0.7 · 1 · 1 · 1 | UPDATE existent | 458 · Back armhole along seam |  |
| `D` | Bottom width (leg opening) | LINEAR+BREAK | 2 · 3 · 3 · 3 | UPDATE existent | 326 · Skirt sweep (bottom width) | LOS |
| `B` | Waist width | LINEAR+BREAK | 2 · 3 · 3 · 3 | UPDATE existent | 275 · Waist width | LOS |
| `BT` | Waist position from HPS | PENDENT | — | UPDATE existent | 467 · WAIST DROP |  |
| `I` | Sleeve length | LINEAR | 0.7 · 0.7 · 0.7 · 0.7 | UPDATE existent | 503 · Sleeve length |  |
| `J` | 1/2 Bicep width | LINEAR+BREAK | 0.6 · 0.8 · 0.8 · 0.8 | UPDATE existent | 295 · Sleeve width at bicep | LOS |
| `JJ` | SLEEVE WIDTH AT ELBOW | LINEAR+BREAK | 0.4 · 0.6 · 0.6 · 0.6 | UPDATE existent · 🔴COL·LISIÓ | 296 · Sleeve width at elbow | LOS |
| `I2` | SLEEVE HEM WIDTH | LINEAR+BREAK | 0.5 · 0.75 · 0.75 · 0.75 | UPDATE existent | 469 · SLEEVE HEM WIDTH |  |
| `J1` | Sleeve opening relaxed | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | UPDATE existent | 297 · Sleeve opening / Cuff width | LOS |
| `J3` | CUFF HEIGHT | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 299 · Cuff height | LOS |
| `I3` | CUFF SLIT | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 461 · Sleeve slit |  |
| `FJ` | WINGSPAN LENGTH | PENDENT | — | UPDATE existent | 470 · WINGSPAN LENGTH |  |
| `F` | Centre front length from HPS | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | UPDATE existent · 🔴COL·LISIÓ | 437 · Centre front length at CF |  |
| `FF` | Centre back length from HPS | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | UPDATE existent | 438 · Centre back length at CB |  |
| `F1` | Curve at side (difference between CB length and side seam) | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | UPDATE existent · 🔴COL·LISIÓ | 437 · Centre front length at CF |  |
| `F2` | TOTAL SIDE LENGTH | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | UPDATE existent · 🔴COL·LISIÓ | 437 · Centre front length at CF |  |
| `F3` | FRONT CENTER TOTAL LENGTH | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | UPDATE existent · 🔴COL·LISIÓ | 389 · TOTAL LENGTH | LOS |
| `F4` | BACK CENTER TOTAL LENGTH | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | UPDATE existent · 🔴COL·LISIÓ | 389 · TOTAL LENGTH | LOS |
| `FB` | BODY LENGTH | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | UPDATE existent | 381 · Straight Back Body Length |  |
| `E4` | Shoulder forward | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 455 · Shoulder Forward |  |
| `E5` | Shoulder drop (from HPS to shoulder point) | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 286 · Shoulder drop | LOS |
| `EK2` | Back neck drop from HPS to seam | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 464 · BACK NECKLINE DROP |  |
| `G1` | Rib height | FIXED | 0 · 0 · 0 · 0 | 🆕 ENCUNYAR (rebateig) | — |  |
| `D1` | Bottom hem height | FIXED | 0 · 0 · 0 · 0 | ♻️ àlies sobre POM existent | 453 · Bottom hem / Bottom rib height |  |
| `BF` | Waistband height | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 320 · Waistband height | LOS |
| `FC` | HIP POSITION | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | UPDATE existent | 380 · Hip Position |  |
| `C` | Hip width | LINEAR+BREAK | 1.5 · 2 · 2 · 2 | UPDATE existent | 276 · Hip width (top) |  |
| `CT` | Thigh width | LINEAR+BREAK | 1.2 · 1.8 · 1.8 · 1.8 | UPDATE existent | 309 · Thigh width | LOS |
| `FR` | KNEE POSITION | LINEAR+BREAK | 0.5 · 0.75 · 0.75 · 0.75 | UPDATE existent | 472 · KNEE POSITION |  |
| `RT` | KNEE WIDTH | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | UPDATE existent | 310 · Knee width | LOS |
| `M` | Leg opening | LINEAR+BREAK | 1.2 · 1.8 · 1.8 · 1.8 | ♻️ àlies sobre POM existent | 311 · Leg opening | LOS |
| `FT` | Pants length (outseam) | LINEAR+BREAK(S) | 0.5 · 0.5 · 1 · 1 | UPDATE existent | 473 · PANTS LENGTH |  |
| `FI` | Inseam length | LINEAR+BREAK | 0 · 0.5 · 0.5 · 0.5 | UPDATE existent | 312 · Inseam length |  |
| `FS` | SKIRT LENGTH | LINEAR+BREAK(S) | 0.5 · 0.5 · 1 · 1 | UPDATE existent | 324 · Skirt length |  |
| `FD` | Front rise length (waistband included) | LINEAR+BREAK | 0.7 · 1.1 · 1.1 · 1.1 | UPDATE existent | 321 · Rise (front) | FTT/LOS |
| `FE` | Back rise length (waistband included) | LINEAR+BREAK | 0.9 · 1.5 · 1.5 · 1.5 | UPDATE existent | 322 · Rise (back) | FTT/LOS |
| `GD` | GODET LENGTH AT LONGEST POINT | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | 🆕 ENCUNYAR (D4) | — |  |
| `GD1` | GODET LENGTH AT THE SEAMS | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | 🆕 ENCUNYAR (D4) | — |  |
| `CR` | FRONT CROTCH WIDTH | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | ♻️ àlies sobre POM existent | 539 · FRONT CROTCH WIDTH | LOS |
| `CR1` | BACK CROTCH WIDTH | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | ♻️ àlies sobre POM existent | 541 · BACK CROTCH WIDTH | LOS |
| `CR3` | CROTCH WIDTH PLACEMENT | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | 🆕 ENCUNYAR (D4) | — |  |
| `CR4` | CROTCH LENGTH | LINEAR+BREAK | 0.85 · 1.25 · 1.25 · 1.25 | ♻️ àlies sobre POM existent | 413 · Crotch length | LOS |
| `FS5` | Lining length difference | FIXED | 0 · 0 · 0 · 0 | 🆕 ENCUNYAR (D4) | — |  |
| `E6` | FRONT COLLAR PANEL HEIGHT | LINEAR+BREAK | 0.15 · 0.2 · 0.2 · 0.2 | UPDATE existent | 474 · FRONT COLLAR PANEL HEIGHT |  |
| `E7` | CENTER COLLAR PANEL HEIGHT | LINEAR+BREAK | 0.15 · 0.2 · 0.2 · 0.2 | UPDATE existent | 475 · CENTER COLLAR PANEL HEIGHT |  |
| `E8` | COLLAR PANEL LENGTH | LINEAR+BREAK | 0.5 · 0.75 · 0.75 · 0.75 | UPDATE existent | 476 · COLLAR PANEL LENGTH |  |
| `E88` | COLLAR JOIN | LINEAR+BREAK | 0.5 · 0.75 · 0.75 · 0.75 | UPDATE existent | 477 · COLLAR JOIN |  |
| `EL` | FLAP WIDTH | LINEAR+BREAK | 0.2 · 0.3 · 0.3 · 0.3 | UPDATE existent | 478 · FLAP WIDTH | LOS |
| `EP` | Collar height at CB | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 456 · Collarstand height at CB |  |
| `PC` | NECK PIPE WIDTH | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 479 · NECK PIPE WIDTH |  |
| `CP` | COLLAR PEAK | LINEAR+BREAK | 0.15 · 0.2 · 0.2 · 0.2 | ♻️ àlies sobre POM existent | 582 · COLLAR PEAK | LOS |
| `CB1` | COLLAR TOTAL CONTOUR | LINEAR+BREAK | 0.5 · 0.75 · 0.75 · 0.75 | ♻️ àlies sobre POM existent | 584 · CONTOUR COLLAR TOTAL | LOS |
| `HL` | HOOD LENGTH | LINEAR+BREAK | 0.5 · 0.75 · 0.75 · 0.75 | UPDATE existent | 425 · HOOD LENGTH | LOS |
| `HW` | HOOD WIDTH | LINEAR+BREAK | 0.5 · 0.75 · 0.75 · 0.75 | UPDATE existent | 347 · Hood width | LOS |
| `H1` | HOOD WIDTH PLACEMENT | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | ♻️ àlies sobre POM existent | 614 · HOOD WIDTH LOCATION | LOS |
| `HP` | HOOD PIECE WIDTH | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | ♻️ àlies sobre POM existent | 426 · HOOD PIECE WIDTH | LOS |
| `HZ` | DRAWSTRING LENGTH | LINEAR | 0.5 · 0.5 · 0.5 · 0.5 | ♻️ àlies sobre POM existent | 615 · DRAWSTRING LENGTH MEASURED AT POINT WHERE TIES | LOS |
| `HZ1` | DRAWSTRING CHANNEL | FIXED | 0 · 0 · 0 · 0 | ♻️ àlies sobre POM existent | 616 · DRAWSTRING CHANNEL | LOS |
| `L` | BACK YOKE | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | UPDATE existent · 🔴COL·LISIÓ | 484 · BACK YOKE |  |
| `P` | CENTER BACK YOKE HEIGHT | FIXED | 0 · 0 · 0 · 0 | UPDATE existent · 🔴COL·LISIÓ | 484 · BACK YOKE |  |
| `P1` | SIDE YOKE HEIGHT | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 442 · Chest piece height at center |  |
| `P2` | CENTER FRONT YOKE HEIGHT | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 441 · Chest piece height at side seam |  |
| `R` | POCKET MOUTH WIDTH | LINEAR+BREAK | 0.2 · 0.3 · 0.3 · 0.3 | UPDATE existent | 485 · POCKET MOUTH WIDTH |  |
| `R1` | POCKET MOUTH LENGTH | LINEAR+BREAK | 0.2 · 0.3 · 0.3 · 0.3 | UPDATE existent | 486 · POCKET MOUTH LENGTH |  |
| `R2` | Pocket width | LINEAR+BREAK | 0.2 · 0.3 · 0.3 · 0.3 | UPDATE existent | 349 · Pocket width | LOS |
| `R3` | Pocket length | LINEAR+BREAK | 0.2 · 0.3 · 0.3 · 0.3 | UPDATE existent | 390 · FRONT POCKET LENGTH | LOS |
| `PR1` | Pocket position from side seam | LINEAR+BREAK | 0.15 · 0.2 · 0.2 · 0.2 | UPDATE existent | 354 · Chest pocket position |  |
| `PR2` | Pocket position from waistband | LINEAR+BREAK | 0.15 · 0.2 · 0.2 · 0.2 | ♻️ àlies sobre POM existent | 357 · Pocket placement from waistband |  |
| `BR` | FLY WIDTH | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 487 · FLY WIDTH | LOS |
| `BR1` | FLY LENGTH | LINEAR+BREAK | 0.2 · 0.3 · 0.3 · 0.3 | UPDATE existent | 488 · FLY LENGTH |  |
| `CR2` | ZIPPER | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 341 · Zipper length | LOS |
| `TR` | PLACKET HEIGHT | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | UPDATE existent | 489 · PLACKET HEIGHT |  |
| `U` | FRONT OVERLAP | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 439 · Width sequins piece (CF) |  |
| `U1` | BUTTON SPACING | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 440 · Height sequins piece (CF) |  |
| `U2` | 1st BUTTON | LINEAR+BREAK | 0.15 · 0.2 · 0.2 · 0.2 | UPDATE existent | 498 · First button measured from collar seam |  |
| `U3` | LAST BUTTON | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 499 · Last button measured from armhole seam |  |
| `UT1` | LOOPS | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 483 · LOOPS |  |
| `K` | BUTTONHOLE PLACEMENT | LINEAR+BREAK | 0.15 · 0.2 · 0.2 · 0.2 | ♻️ àlies sobre POM existent | 669 · BUTTONHOLE LOCATION | LOS |
| `KB` | BUTTON PLACEMENT | LINEAR+BREAK | 0.15 · 0.2 · 0.2 · 0.2 | 🆕 ENCUNYAR (D4) | — |  |
| `KU` | EYELET PLACEMENT | LINEAR+BREAK | 0.15 · 0.2 · 0.2 · 0.2 | ♻️ àlies sobre POM existent | 385 · EYELET LOCATION | LOS |
| `ZF` | BELT WIDTH | FIXED | 0 · 0 · 0 · 0 | ♻️ àlies sobre POM existent | 363 · Belt width |  |
| `ZL` | BELT LENGTH | FIXED | 0 · 0 · 0 · 0 | ♻️ àlies sobre POM existent | 362 · Belt length | LOS |
| `ZL1` | BOW LENGTH | FIXED | 0 · 0 · 0 · 0 | ♻️ àlies sobre POM existent | 660 · BOW LENGTH |  |
| `T` | STRAP LENGTH | PENDENT | — | UPDATE existent | 480 · SHOULDER LENGTH |  |
| `T1` | STRAP WIDTH | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 481 · TIE WIDTH |  |
| `T2` | STRAP PLACEMENT | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | UPDATE existent | 482 · TIGHT POSITION |  |
| `BL` | FOLD LENGTH | LINEAR+BREAK | 1 · 1 · 1.5 · 1.5 | UPDATE existent | 490 · FOLD LENGTH |  |
| `BW` | FOLD WIDTH | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 491 · FOLD WIDTH |  |
| `Q` | DART LENGTH | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | ♻️ àlies sobre POM existent | 397 · DART LENGTH | LOS |
| `QP` | DART PLACEMENT | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | ♻️ àlies sobre POM existent | 396 · DART LOCATION | LOS |
| `QT` | PLEAT WIDTH | FIXED | 0 · 0 · 0 · 0 | 🆕 ENCUNYAR (D4) | — |  |
| `QTP` | PLEAT PLACEMENT | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | ♻️ àlies sobre POM existent | 566 · PLEAT LOCATION | LOS |
| `V` | RUFFLE HEIGHT | FIXED | 0 · 0 · 0 · 0 | UPDATE existent | 492 · RUFFLE HEIGHT | LOS |
| `VR` | RUFFLE LENGTH | PENDENT | — | UPDATE existent | 493 · RUFFLE LENGTH |  |
| `U4` | FLOUNCE HEIGHT | FIXED | 0 · 0 · 0 · 0 | ♻️ àlies sobre POM existent | 578 · FLOUNCE HEIGHT | LOS |
| `SLT` | SLIT | FIXED | 0 · 0 · 0 · 0 | 🆕 ENCUNYAR (D4) | — |  |
| `JTA` | SLEEVE STRAP | PENDENT | — | UPDATE existent | 494 · SLEEVE STRAP / SLEEVE STRAP |  |
| `IC` | ELBOW PATCH PLACEMENT | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | UPDATE existent | 495 · ELBOW POSITION |  |
| `IC1` | ELBOW PATCH WIDTH | LINEAR+BREAK | 0.2 · 0.3 · 0.3 · 0.3 | UPDATE existent · 🔴COL·LISIÓ | 296 · Sleeve width at elbow | LOS |
| `IC2` | ELBOW PATCH LENGTH | LINEAR+BREAK | 0.2 · 0.3 · 0.3 · 0.3 | UPDATE existent | 497 · ELBOW LENGTH | LOS |
| `N` | MOTIVE PLACEMENT | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | 🆕 ENCUNYAR (D4) | — |  |
| `NF` | MOTIVE WIDTH | FIXED | 0 · 0 · 0 · 0 | 🆕 ENCUNYAR (D4) | — |  |
| `NL` | MOTIVE HEIGHT | FIXED | 0 · 0 · 0 · 0 | 🆕 ENCUNYAR (D4) | — |  |
| `W` | ELASTIC WIDTH | FIXED | 0 · 0 · 0 · 0 | 🆕 ENCUNYAR (D4) | — |  |
| `WP` | ELASTIC PLACEMENT | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | ♻️ àlies sobre POM existent | 416 · Elastic location |  |
| `X` | STITCHING WIDTH | FIXED | 0 · 0 · 0 · 0 | 🆕 ENCUNYAR (D4) | — |  |
| `XP` | STITCHING PLACEMENT | LINEAR+BREAK | 0.3 · 0.5 · 0.5 · 0.5 | 🆕 ENCUNYAR (D4) | — |  |
| `XV` | JETTING WIDTH | FIXED | 0 · 0 · 0 · 0 | ♻️ àlies sobre POM existent | 513 · JETTING WIDTH | LOS |

---

# NOTA PER A LA SESSIÓ D'UI · el diccionari d'instàncies ja és a BD, el front encara no el llegeix

**Pertoca a:** la peça d'UI (C5-UI / gest de crear germana). **NO és feina de backend** — F2 ja
va deixar la dada; això és el consum.

## El problema, en una línia

`frontend/src/utils/capaInstancia.js:31` té el vocabulari d'instàncies **cablejat a mà**:

```js
export const INSTANCIES = ['left', 'right', 'relaxed', 'extended']
```

El diccionari real existeix des de F2 (`pom.MeasurementInstance`, sembrat a `public`, `fhort`
i `los`) i té **10 files: 8 POSICIONS + 2 ESTATS**. El front només en coneix 4.

**Conseqüència concreta:** el gest de crear una germana ofereix **4 de les 8 posicions reals**.
Les altres 6 existeixen a BD, es poden desar a la columna `instancia`, i la UI no les sap ni
proposar ni escriure bé — un slug desconegut cau al camí `cru()` i es pinta «Cf», «Waistband
seam» en comptes del literal traduït.

## Què falta, exactament

**1. Els 6 slugs que hi falten** (els 4 que hi ha són correctes i no es toquen):

| slug | eix | sufix | EN | CA | ES |
|---|---|---|---|---|---|
| `top` | POSICIÓ | `T` | Top | Superior | Superior |
| `bottom` | POSICIÓ | `B` | Bottom | Inferior | Inferior |
| `cf` | POSICIÓ | `CF` | CF | CF | CF |
| `cb` | POSICIÓ | `CB` | CB | CB | CB |
| `side` | POSICIÓ | `S` | Side seam | Costura lateral | Costura lateral |
| `waistband_seam` | POSICIÓ | *(cap)* | Waistband seam | Costura de cinturilla | Costura de pretina |

⚠️ **`cf` i `cb` NO es tradueixen**: són acrònims del sector, com HPS. Escriure'ls «Centre
davant» a la fitxa catalana els faria irreconeixibles per al fabricant.

**2. Les claus i18n** als tres idiomes. Avui el bloc `instancia` en té 4 de 4:
- `frontend/src/i18n/ca.json:4273`
- `frontend/src/i18n/en.json` · `frontend/src/i18n/es.json` (mateix bloc `instancia`)

**3. Els DOS EIXOS, que el front encara no distingeix.** `MeasurementInstance.eix` separa
POSICIÓ (on es mesura) d'ESTAT (com es mesura), i es componen amb guió (`left-relaxed`) —
`etiquetaInstancia()` ja ho desmunta bé. El selector del gest hauria d'oferir-los com a dues
tries, no com una llista de 10 barrejades.

**4. El SUFIX de composició** (`MeasurementInstance.sufix`), que avui no té consumidor. És el
que permet PROPOSAR el codi de la germana: `B` + posició `top` → `BT`, `FS` + `cf` → `FSCF`
(concatenació directa, estil Brownie, sense guió). L'ESTAT no en porta, i `waistband_seam`
tampoc perquè és un DATUM: es diu a la descripció, no al codi.
La proposta **no és l'obligació** — `instancia_exigeix_nom` segueix manant, i el `nom_fitxa`
és lliure i editable pel patronista.

## Decisió pendent, no mecànica

El propi `capaInstancia.js:15-20` explica per què les capes van quedar cablejades: a PROD
`MeasurementLayer` és BUIDA i no hi ha endpoint que la publiqui, i una pantalla que en
depengués sortiria sense etiquetes el dia del desplegament. **`MeasurementInstance` té
exactament el mateix problema**: sembrada a staging, cap endpoint la publica.

Per tant hi ha dos camins, i és decisió d'Agus:
- **(a) constant al front**, com les capes avui — ràpid, i deixa la BD com a font sense lector;
- **(b) endpoint + lector**, que és el TODO que ja hi ha escrit a `capaInstancia.js:20`
  (`TODO(backend): sembrar MeasurementLayer a PROD + publicar-lo`), i que resoldria les DUES
  taules d'una sola vegada.

Si es tria (b), la sembra a PROD també cal: `seed_measurement_layers` i
`seed_measurement_instances` són idempotents i van a `public` + tots els tenants.
