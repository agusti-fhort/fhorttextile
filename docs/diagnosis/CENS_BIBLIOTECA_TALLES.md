# CENS · LA BIBLIOTECA DE TALLES A STAGING · 2026-08-06 (nit)

> **Mode: READ-ONLY.** Cap `DELETE`, cap `UPDATE`, cap migració. Tot el que segueix és
> **PROPOSTA** i espera decisió de l'Agus.
> Acompanya [`DIAGNOSI_VOCABULARIS.md`](DIAGNOSI_VOCABULARIS.md) §T3 i
> [`REPORT_NIT_CAPES.md`](REPORT_NIT_CAPES.md) §7.1.
> Models: `backend/fhort/pom/models.py` → `SizeSystem:556` · `SizeDefinition:605` ·
> `SizingProfile:1489`.

---

## 0 · LES 6 FKs ENTRANTS A `SizeSystem`

Via `SizeSystem._meta.related_objects` — **són sis, no dues**, i **tres són `PROTECT`**:
qualsevol depuració hi xocarà.

| Model | camp | accessor | on_delete |
|---|---|---|---|
| `pom.SizeSystem` | `parent` | `derived_systems` | SET_NULL |
| `pom.SizeDefinition` | `size_system` | `talles` | CASCADE |
| `pom.ItemBaseSet` | `size_system` | `item_base_sets` | **PROTECT** |
| `pom.GradingRuleSet` | `size_system` | `grading_rule_sets` | **PROTECT** |
| `pom.SizingProfile` | `size_system` | `sizing_profiles` | **PROTECT** |
| `models_app.Model` | `size_system` | `models` | FK |

---

## A · ELS 28 RUNS DE `fhort`

`SP`=SizingProfile · `GRS`=GradingRuleSet · `IBS`=ItemBaseSet · `MOD`=Model · `DER`=derivats.
`tipus` és el `tipus_escala` que N1 hi ha classificat aquesta nit.

| id | codi | act | tipus | base_unit | cust | #t | etiquetes (per `ordre`) | SP | GRS | IBS | MOD | DER |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 | `TGIRL-EU-HEIGHT` | ✔ | **ALTURA** | *(buit)* | — | 8 | 128·134·140·146·152·158·164·170 | 0 | 0 | 0 | 0 | 0 |
| 26 | `MEN-SHIRT-NUM` | ✔ | **(BUIT)** | *(buit)* | — | **0** | *(cap)* | 0 | 0 | 0 | 0 | 0 |
| 29 | `ALPHA_EU_W` | ✔ | ALPHA | ALPHA | — | 8 | XXS·XS·S·M·L·XL·XXL·3XL | **9** | **10** | 0 | 0 | 0 |
| 30 | `ALPHA_EU_M` | ✔ | ALPHA | ALPHA | — | 7 | XS·S·M·L·XL·XXL·3XL | 2 | 2 | **1** | 0 | 0 |
| 31 | `ALPHA_EU_U` | ✔ | ALPHA | ALPHA | — | **0** | *(cap)* | 0 | 0 | 0 | 0 | 0 |
| 32 | `NUMERIC_EU_W` | ✔ | NUM | NUMERIC_EU | — | 8 | 34·36·38·40·42·44·46·48 | 0 | 1 | 0 | 0 | 0 |
| 33 | `NUMERIC_EU_M` | ✔ | NUM | NUMERIC_EU | — | **0** | *(cap)* | 0 | 0 | 0 | 0 | 0 |
| 34 | `BABY_MONTHS` | ✘ | MESOS | MONTHS | — | 14 | NB·0M-1M·0M·1M-3M·1M·3M-6M·3M·6M-9M·6M·9M-12M·9M·12M·18M·24M | 0 | 0 | 0 | 0 | 0 |
| 35 | `BABY_EU_CM` | ✔ | ALTURA | CM_HEIGHT | — | 8 | 50·56·62·68·74·80·86·92 | 1 | 1 | 0 | 0 | 0 |
| 36 | `TODDLER_EU` | ✘ | **ALTURA** | ⚠️ AGE_YEARS | — | 6 | 92·86·98·104·110·116 | 1 | 1 | 0 | 0 | 0 |
| 37 | `KIDS_EU` | ✘ | MESOS | AGE_YEARS | — | 4 | 6Y·8Y·10Y·12Y | 1 | 1 | 0 | 0 | 0 |
| 38 | `TEEN_ALPHA` | ✔ | ALPHA | ALPHA | — | 5 | XS·S·M·L·XL | 1 | 1 | 0 | 0 | 0 |
| 39 | `ALPHA_US_W` | ✔ | ALPHA | ALPHA | — | **0** | *(cap)* | 0 | 0 | 0 | 0 | 0 |
| 40 | `NUMERIC_US_W` | ✔ | NUM | NUMERIC_US | — | **0** | *(cap)* | 0 | 0 | 0 | 0 | 0 |
| 41 | `KIDS_AGE_COM` | ✔ | MESOS | AGE_YEARS | — | 11 | 2·3·4·5·6·7·8·9/10·11/12·13/14·15/16 | 0 | 0 | 0 | 0 | 0 |
| 42 | `BABY_MONTHS_COM` | ✔ | MESOS | MONTHS | — | 5 | 0M-1M·1M-3M·3M-6M·6M-9M·9M-12M | 3 | 1 | 0 | 0 | 0 |
| 48 | `GIRL_LOS_01` | ✔ | MESOS | AGE_YEARS | **LOS** | 9 | 2·3·4·5·6·7·8·9/10·11/12 | 2 | 3 | 0 | 0 | 0 |
| 50 | `GIRL_LOS_03` | ✔ | MESOS | AGE_YEARS | **LOS** | 9 | 2·3·4·5·6·7·8·9/10·11/12 | 1 | 1 | 0 | 0 | 0 |
| 51 | `MAN_LOS_01` | ✔ | ALPHA | ALPHA | **LOS** | 9 | S·M·L·XL·2XL·3XL·4XL·5XL·6XL | 1 | 1 | 0 | 0 | 0 |
| 53 | `WOMAN_BRW_01` | ✔ | ALPHA | ALPHA | **BRW** | 5 | XXS·XS·S·M·L | **0** | 1 | 0 | 0 | 0 |
| 62 | `NEWBORN_LOS_01` | ✔ | MESOS | MONTHS | **LOS** | 7 | 00/01·01/03·03/06·06/09·09/12·12/18·18/24 | 3 | 3 | 0 | 0 | 0 |
| 63 | `BABY_LOS_01` | ✔ | MESOS | MONTHS | **LOS** | 6 | 03/06·06/09·09/12·12/18·18/24·24/36 | 1 | 2 | 0 | 0 | 0 |
| 64 | `BOY_LOS_01` | ✔ | MESOS | AGE_YEARS | **LOS** | 9 | 2·3·4·5·6·7·8·9/10·11/12 | 2 | 2 | 0 | 0 | 0 |
| 65 | `YOUTH_GIRL_LOS_01` | ✔ | MESOS | AGE_YEARS | **LOS** | 5 | 8·10·12·14·16 | 3 | 3 | 0 | 0 | 0 |
| 66 | `YOUTH_BOY_LOS_01` | ✔ | MESOS | AGE_YEARS | **LOS** | 5 | 8·10·12·14·16 | 3 | 3 | 0 | 0 | 0 |
| 67 | `WOMAN_LOS_01` | ✔ | ALPHA | ALPHA | **LOS** | 7 | XS·S·M·L·XL·2XL·3XL | 1 | 1 | 0 | 0 | 0 |
| 68 | `WOMAN_NUM_LOS_01` | ✔ | NUM | NUMERIC_EU | **LOS** | 9 | 36·38·40·42·44·46·48·50·52 | 1 | 1 | 0 | 0 | 0 |
| 69 | `MAN_NUM_LOS_01` | ✔ | NUM | NUMERIC_EU | **LOS** | 11 | 38·40·42·44·46·48·50·52·54·56·58 | 1 | 1 | 0 | 0 | 0 |

**Totals `fhort`:** 28 SizeSystem · 175 SizeDefinition · 37 SizingProfile · 47 GradingRuleSet ·
1 ItemBaseSet · **0 Model**.

## A-bis · ELS 2 RUNS DE `los`

| id | codi | act | tipus | base_unit | #t | SP | GRS | IBS | **MOD** |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `ALPHA_EU_W` | ✔ | **(BUIT)** | *(buit)* | **0** | 0 | 0 | 0 | **20** |
| 2 | `SYS-ONLY-LOS` | ✔ | **(BUIT)** | *(buit)* | **0** | 0 | 0 | 0 | **10** |

**Totals `los`:** 2 SizeSystem · **0** SizeDefinition · 51 Models (30 amb run, 21 sense).

## A-ter · OBSERVACIONS ESTRUCTURALS

1. **El mecanisme `parent`/`derived_systems` és MORT en dades:** `parent_id = NULL` a les 30
   files, `derived_systems = 0` a totes. La derivació per client mai s'ha estrenat;
   `customer_codi` és l'únic eix client viu (12 files: 11 LOS + 1 BRW).
2. **Forats d'id a `fhort`:** 1-5, 7-25, 27-28, **43-47, 49, 52, 54-61**. El forat 49 —just
   entremig de `GIRL_LOS_01` i `GIRL_LOS_03`— diu que un `GIRL_LOS_02` ja es va esborrar.
   ⚠️ **Ja s'ha depurat abans sense deixar rastre documentat.**
3. 🔑 **`public` té 14 `SizeSystem` amb ids DIFERENTS dels de `fhort`.** Són exactament els 14
   codis de `fhort` sense `customer_codi`, **excepte dos**: `TGIRL-EU-HEIGHT` (6) i
   `MEN-SHIRT-NUM` (26) **NO existeixen a `public`**. **Aquest és el discriminador dur
   casa-vs-brossa.**
4. ⚠️ **Els ids NO són els mateixos entre schemes.** `ALPHA_EU_W` = **29** a `fhort`, **1** a
   `public`, **1** a `los`. Creuar **per `codi`**, mai per `id`.

---

## B · CLASSIFICACIÓ EN CUBELLS

### CANÒNIC — 12 files (totes presents a `public`)

| id | codi | evidència | veredicte |
|---|---|---|---|
| 29 | `ALPHA_EU_W` | 8 talles amb body-measures · **10 GRS · 9 SP** · el run més usat de staging · `public.1` | **nucli** |
| 30 | `ALPHA_EU_M` | 7 talles amb body-measures · 2 GRS · 2 SP · **l'únic amb ItemBaseSet** · `public.2` | **nucli** |
| 32 | `NUMERIC_EU_W` | 8 talles amb body-measures · 1 GRS · `public.4` | **nucli** |
| 35 | `BABY_EU_CM` | 8 talles amb `body_height_cm` + `age_months_*` complets · `public.7` | **nucli** |
| 38 | `TEEN_ALPHA` | 5 talles amb body-measures · 1 GRS · 1 SP · `public.10` | canònic |
| 42 | `BABY_MONTHS_COM` | 5 talles netes · **3 SP** · seed oficial · `public.14` | canònic |
| 37 | `KIDS_EU` | 4 talles amb body-measures · 1 GRS · 1 SP · `public.9` | canònic **inconsistent** (`actiu=False` amb ús viu) |
| 41 | `KIDS_AGE_COM` | 11 talles ben construïdes · seed oficial · `public.13` · **0 usos** | canònic **no estrenat** — NO tocar |
| 31 | `ALPHA_EU_U` | 0 talles, 0 usos, però `public.3` amb target i norma | canònic **buit** |
| 33 | `NUMERIC_EU_M` | 0 talles, 0 usos, `public.5` | canònic **buit** |
| 39 | `ALPHA_US_W` | 0 talles, 0 usos, `public.11` | canònic **buit** |
| 40 | `NUMERIC_US_W` | 0 talles, 0 usos, `public.12` | canònic **buit** |

> 🔑 Els 4 «buits» (31/33/39/40) **NO són brossa**: viuen al catàleg `public` amb target i
> norma. Són **places reservades del catàleg mai omplertes**. Esborrar-los desalinearia `fhort`
> de `public` i trencaria un futur bootstrap: seria mutilar el catàleg, no depurar-lo.

### CANÒNIC AMB DEFECTE — 2 files (→ Agus)

| id | codi | els defectes, concrets |
|---|---|---|
| **36** | `TODDLER_EU` | ① `base_unit='AGE_YEARS'` amb **etiquetes que són alçades en cm** (86-116, pas 6, `body_height_cm == etiqueta` a les 6 talles) → el `base_unit` MENT · ② **l'`ordre` està trencat**: `92` i `86` tots dos amb `ordre=1` → el run es llegeix `92·86·98·104·110·116`, **desordenat** · ③ la talla `116` té `waist=34 / hip=40`, **impossible** (les germanes fan 57/65). I amb tot això: 1 GRS + 1 SP vius. |
| **34** | `BABY_MONTHS` | `actiu=False`, **0 usos**, i **dos runs barrejats en un**: el joc puntual (`NB·0M·1M·3M·6M·9M·12M·18M·24M`) i el joc per rangs (`0M-1M`…`9M-12M`) → **5 parells d'`ordre` duplicats**. Els `age_months_*` del joc puntual estan desplaçats (`1M`→4-12 mesos, `24M`→**96-144 mesos**). El joc per rangs és **duplicat exacte** de `BABY_MONTHS_COM` (42), que sí que s'usa. Existeix a `public.6`. |

### DE CLIENT REAL — 10 files (totes LOS, totes amb ús viu)

`48 GIRL_LOS_01` (3 GRS · 2 SP) · `51 MAN_LOS_01` · `62 NEWBORN_LOS_01` (3 GRS · 3 SP) ·
`63 BABY_LOS_01` · `64 BOY_LOS_01` · `65 YOUTH_GIRL_LOS_01` (3 GRS · 3 SP) ·
`66 YOUTH_BOY_LOS_01` (3 GRS · 3 SP) · `67 WOMAN_LOS_01` · `68 WOMAN_NUM_LOS_01` ·
`69 MAN_NUM_LOS_01`.

**Les FK `PROTECT` els defensen soles.**

### DE CLIENT, DUBTÓS — 2 files (→ Agus)

| id | codi | el dubte |
|---|---|---|
| **50** | `GIRL_LOS_03` | **Duplicat funcional de `GIRL_LOS_01` (48)**: mateixes 9 etiquetes, mateix target, mateix `base_unit`, mateix client. Però té ús propi: G104 «LOS Kids Knit Regular 2Y-12Y» (19 regles) + P521. |
| **53** | `WOMAN_BRW_01` | 5 talles XXS-L · **0 SizingProfile** · l'ÚNIC ús és G124, que es diu literalment **«Prova BRW ALPHA UE»** (21 regles). El grading BRW de debò —G115 `BRW · Blusa · ALPHA_EU_W` (34 regles + P524) i G219 `BRW-CATALEG-v3` (114 regles)— penja del **canònic 29**, no d'aquest run. |

### BROSSA DE STAGING — 2 files

| id | codi | senyals acumulats |
|---|---|---|
| **26** | `MEN-SHIRT-NUM` | 0 talles · **les 6 FKs a zero** · 0 targets · `base_unit` buit · `norma_ref` buit · sense client · **NO és a `public`** · `descripcio='Neck circ. (cm)'` (un run de talles no mesura el coll). **7/7 senyals.** |
| **6** | `TGIRL-EU-HEIGHT` | **les 6 FKs a zero** · 0 targets · `base_unit`/`norma_ref` buits · sense client · **NO és a `public`** · id molt baix · **el nom contradiu el contingut** («Alpha EU — Grading Reference» amb 8 etiquetes que són alçades 128-170) · les 8 `SizeDefinition` tenen **tots** els camps de cos a NULL. **6/7 senyals.** ⚠️ Si algú vol un run TEEN GIRL per alçada, aquest és l'únic esquelet que hi ha. |

### INCLASSIFICABLE SOL — 2 files a `los` (→ Agus)

| id | codi | per què no es decideix sol |
|---|---|---|
| **los·1** | `ALPHA_EU_W` | **0 talles i 20 Models l'apunten.** Un run sense cap `SizeDefinition` amb 20 models penjats és una **incoherència activa**: aquests 20 models **no poden graduar**. |
| **los·2** | `SYS-ONLY-LOS` | 0 talles, **10 Models**, nom d'artefacte de test. Apareix literalment com a fixture a `VERIFICACIO_BOOTSTRAP_DESTI_POBLAT.md:128`. |

---

## C · L'ALGORISME DE DEDUCCIÓ (implementat a `pom/size_labels.py`)

Ordre estricte de precedència, sobre `label.strip().upper()`:

```
R0. Sense cap SizeDefinition                                        → cau a base_unit
R1. ≥1 etiqueta ^\d+M$ | ^\d+M[-/]\d+M$ | == 'NB'                   → MESOS
R2. ≥1 etiqueta ^\d+Y$                                              → MESOS (edat)
R3. ≥50% casen ^(\d+X|X*)(S|M|L)$                                   → ALPHA
R4. món numèric: V = primer número de cada etiqueta, ORDENAT
    STEP = mediana de les diferències consecutives
    R4a. ≥50% són \d\d[-/]\d\d  ∧  max(V) ≤ 36                      → MESOS
    R4b. STEP == 6  ∧  44 ≤ min(V)  ∧  max(V) ≤ 188                 → ALTURA
    R4c. STEP == 1  ∧  max(V) ≤ 18                                  → MESOS (edat)
    R4d. STEP == 2  ∧  min(V) ≥ 28                                  → NUM
    R4e. la resta                                                   → cau a base_unit
```

🔑 **El desempat NUM vs ALTURA és EL PAS, i és gratuït.** L'escalat EU d'alçada infantil va
**de 6 en 6** sense excepció (50·56·62…170); el numèric EU adult va **de 2 en 2** (34·36·38…).
A staging separa el **100 %** dels casos: zero falsos positius, zero falsos negatius. El rang
absolut **no** desempata: es solapen a la franja 44-62.

🔑 **Els valors s'ORDENEN abans de calcular el pas.** El pas és una propietat de l'ESCALA, no de
com està desada — i `TODDLER_EU` té l'`ordre` trencat.

🔑 **L'etiqueta guanya al `base_unit`.** Mesurat: **23 de 24 coincideixen**; l'única que xoca és
`TODDLER_EU` (36), i hi guanya l'etiqueta. Taxa d'error del camp: **~4 %**.

### Mapatge `base_unit` → `tipus_escala` (total, sense ambigüitat de forma)

| `base_unit` | → | files `fhort` |
|---|---|---|
| `ALPHA` | **ALPHA** | 8 |
| `NUMERIC_EU` · `NUMERIC_US` | **NUM** | 4 + 1 |
| `CM_HEIGHT` | **ALTURA** | 1 |
| `MONTHS` · `AGE_YEARS` | **MESOS** | 4 + 8 |
| *(buit)* | *(cal deduir)* | 2 |

### Resultat sobre les 30 files

**21 de 30 es dedueixen només amb etiquetes (70 %).** Amb `base_unit` com a xarxa: **27/30
(90 %)**.

**Els 3 irrecuperables** —`fhort`·26, `los`·1, `los`·2— són **exactament** els que el cens
classifica com a brossa/inclassificable. No és casualitat: *run sense talles ∧ sense `base_unit`
⇒ candidat a brossa*.

**El cas patològic que el `base_unit` salva:** `YOUTH_{GIRL,BOY}_LOS_01` (65, 66), `8·10·12·14·16`
amb STEP=2 i max=16. Podria ser edat en anys (i el nom diu «8-16Y»), NUM US (les talles 8-16 US
women existeixen de debò) o NUM infantil. **Sense `base_unit` és genuïnament indecidible.**

---

## D · ELS 37 `SizingProfile` DE `fhort`

| id | target | garment_type | constr | fit | size_system | grading_rule_set | cust |
|---|---|---|---|---|---|---|---|
| 264 | WOMAN | T_SHIRT | WOVEN | REGULAR | `ALPHA_EU_W` (29) | EU Woven Woman Regular (75) | — |
| 276 | WOMAN | T_SHIRT | KNIT | REGULAR | `ALPHA_EU_W` (29) | EU Knit Woman Regular (79) | — |
| 288 | WOMAN | T_SHIRT | STRETCH_KNIT | SLIM | `ALPHA_EU_W` (29) | EU Stretch Woman Slim (81) | — |
| 335 | MAN | T_SHIRT | WOVEN | REGULAR | `ALPHA_EU_M` (30) | EU Woven Man Regular (84) | — |
| 347 | MAN | T_SHIRT | KNIT | REGULAR | `ALPHA_EU_M` (30) | EU Knit Man Regular (86) | — |
| 365 | NEWBORN_GIRL | T_SHIRT | KNIT | REGULAR | `BABY_EU_CM` (35) | EU Knit Baby Regular (87) | — |
| 413 | BABY_GIRL | T_SHIRT | KNIT | REGULAR | **`TODDLER_EU` (36)** | EU Knit Toddler Regular (88) | — |
| 437 | KID_GIRL | T_SHIRT | KNIT | REGULAR | **`KIDS_EU` (37)** | EU Knit Kids Regular (89) | — |
| 461 | TEEN_GIRL | T_SHIRT | KNIT | REGULAR | `TEEN_ALPHA` (38) | EU Knit Teen Regular (90) | — |
| 485 | WOMAN | T_SHIRT | WOVEN | SLIM | `ALPHA_EU_W` (29) | EU Woven Woman Slim (76) | — |
| 497 | WOMAN | DRESS | WOVEN | FLARED | `ALPHA_EU_W` (29) | EU Woven Woman Regular (75) | — |
| 503-505 | NEWBORN_{GIRL,BOY,UNISEX} | BABY_ONEPIECES | KNIT | REGULAR | `BABY_MONTHS_COM` (42) | EU Knit Baby Months (93) | — |
| 510 | WOMAN | T_SHIRT | STRETCH_KNIT | SLIM | `ALPHA_EU_W` (29) | Custom Alpha EU — Women (98) | — *(parent 288, v2)* |
| 521 | KID_GIRL | SWEATSHIRTS_MIDLAYERS | KNIT | REGULAR | **`GIRL_LOS_03` (50)** | LOS Kids Knit Regular 2Y-12Y (104) | ⚠️ **NULL** |
| 523 | WOMAN | DRESSES | WOVEN | REGULAR | `ALPHA_EU_W` (29) | ⚠️ Mango … only dress (108) — **0 regles** | — |
| 524 | WOMAN | BUTTONED_TOPS | WOVEN | REGULAR | `ALPHA_EU_W` (29) | BRW · Blusa · ALPHA_EU_W (115) | **BRW** |
| 539-541 | NEWBORN_GIRL | NEWBORN | KNIT | REGULAR | `NEWBORN_LOS_01` (62) | LOS New Born Knit — Tops/Bottoms/Onepieces (175/176/177) | LOS |
| 542 | BABY_GIRL | NEWBORN | KNIT | REGULAR | `BABY_LOS_01` (63) | LOS Baby Knit — Tops (178) | LOS |
| 543 | KID_GIRL | DRESSES | KNIT | REGULAR | `GIRL_LOS_01` (48) | LOS Kids Girl — Dresses (179) | LOS |
| 544 | KID_BOY | TAILORED_PANTS | WOVEN | REGULAR | `BOY_LOS_01` (64) | LOS Kids Boy Woven — Bottoms (180) | LOS |
| 545-547 | TEEN_BOY | JERSEY_TOPS / BUTTONED_TOPS / TAILORED_PANTS | KNIT/WOVEN | REGULAR | `YOUTH_BOY_LOS_01` (66) | 181 / 182 / 183 | LOS |
| 548 | TEEN_GIRL | TAILORED_PANTS | WOVEN | REGULAR | `YOUTH_GIRL_LOS_01` (65) | LOS Teen Girl — Bottoms (184) | LOS |
| 549 | TEEN_GIRL | SWIMWEAR | STRETCH_KNIT | REGULAR | `YOUTH_GIRL_LOS_01` (65) | LOS Teen Girl Stretch — Swimwear (185) | LOS |
| 550 | WOMAN | JERSEY_TOPS | KNIT | REGULAR | `WOMAN_LOS_01` (67) | LOS Woman Knit — Tops (186) | LOS |
| 551 | WOMAN | TAILORED_PANTS | WOVEN | REGULAR | `WOMAN_NUM_LOS_01` (68) | LOS Woman Woven — Bottoms (187) | LOS |
| 552 | MAN | TAILORED_PANTS | WOVEN | REGULAR | `MAN_NUM_LOS_01` (69) | LOS Man Woven — Bottoms (188) | LOS |
| 573 | MAN | JERSEY_TOPS | KNIT | REGULAR | `MAN_LOS_01` (51) | LOS Man Knit — Tops (210) | LOS |
| 574 | TEEN_GIRL | JERSEY_TOPS | KNIT | REGULAR | `YOUTH_GIRL_LOS_01` (65) | LOS Teen Girl Knit — Tops (211) | LOS |
| 575 | KID_BOY | JERSEY_TOPS | KNIT | REGULAR | `BOY_LOS_01` (64) | LOS Kids Boy Knit — Tops (212) | LOS |
| 576 | KID_GIRL | JERSEY_TOPS | KNIT | REGULAR | `GIRL_LOS_01` (48) | LOS Kids Girl Knit — Tops (213) | LOS |
| 577 | WOMAN | SWEATSHIRTS_MIDLAYERS | KNIT | REGULAR | `ALPHA_EU_W` (29) | ⚠️ **NULL** (però `is_default=True`) | — |

### 🔑 **ZERO dels 37 perfils apunten a un run classificat com a BROSSA.**

Ni `TGIRL-EU-HEIGHT` (6) ni `MEN-SHIRT-NUM` (26) tenen cap `SizingProfile`. **Els dos runs que
es proposa esborrar no arrosseguen cap perfil.** L'únic perfil que toca la llista de decisions
és **P521 → `GIRL_LOS_03` (50)**.

### Anomalies col·laterals (no és l'encàrrec, però són al mateix cens)

- **P521** té run de LOS i ruleset amb `customer=LOS`, però el **`customer` del perfil és NULL**
  → perfil de client disfressat de genèric.
- **P523** penja d'un ruleset amb **0 regles** — perfil amb graduació buida.
- **P577** té `grading_rule_set=NULL` (legal des de C3) però `is_default=True`.
- **P539/540/541** comparteixen `(target, garment_type, construction, fit, size_system)` i només
  canvien de ruleset. **`SizingProfile` no té `unique_together`: la proliferació no té fre.**

---

## E · «BRW RUN 01» I «ELS 4 CANÒNICS»

### BRW Run 01

**No existeix cap objecte amb el nom literal «BRW Run 01».** L'únic candidat és inequívoc:

| tenant | id | codi | nom complet |
|---|---|---|---|
| `fhort` | **53** | `WOMAN_BRW_01` | `Dona ALPHA — Textiles y Confecciones Brownie SL Run 01` |

`customer_codi='BRW'` · `tipus_escala=ALPHA` · `actiu=True` · target `WOMAN` · 5 talles
(XXS·XS·S·M·L) · **1 GRS** (id 124, `Prova BRW ALPHA UE`, 21 regles) · **0 SizingProfile**.
Referenciat a `REPORT_W2_WIZARD.md:99,118` com a `WOMAN_BRW_01[BRW]`, primer de la proximitat.

⚠️ **Parany per a qualsevol verificació:** el grading de Brownie que sí que es fa servir **NO
penja del 53** — penja del canònic `ALPHA_EU_W` (29): G115 (34 regles, amb P524) i G219
`BRW-CATALEG-v3` (114 regles). Coincideix amb `DECISIONS.md:863` i `DIFF_RULESET_BRW.md:55`.

🔑 **Nomenclatura:** el 53 i el 50 (`GIRL_LOS_03`) són **els dos únics runs de tot staging amb
el patró «`<Target> <ESCALA> — <Raó social> Run NN`»** → surten del mateix generador (l'assistent
«Nou run de client»). Els altres 10 runs LOS segueixen el patró curt `LOS <X> <rang>`, d'un
altre origen (`seed_losan_ss27.py` / `ops/onboarding_losan/`).

### Els 4 canònics

**Cap document ni codi del repo anomena «els 4 canònics» ni n'enumera quatre.** El que hi ha:
`REPORT_W2_WIZARD.md:99` etiqueta **dos** com a `[canònic]` (`ALPHA_EU_W`, `NUMERIC_EU_W`), i
`DECISIONS.md:658-659` parla de **tres famílies** («alpha/numèric/edats»). El discriminador real
és `public`: **14 codis**.

Els 4 candidats forts per evidència de dades (els únics amb `SizeDefinition` completes **amb
mesures corporals** + ús viu + presència a `public`):

| # | id `fhort` | id `public` | codi | per què |
|---|---|---|---|---|
| 1 | **29** | 1 | `ALPHA_EU_W` | 10 GRS + 9 SP — el pilar |
| 2 | **30** | 2 | `ALPHA_EU_M` | 2 GRS + 2 SP + l'únic `ItemBaseSet` |
| 3 | **32** | 4 | `NUMERIC_EU_W` | etiquetat `[canònic]` al repo |
| 4 | **35** | 7 | `BABY_EU_CM` | l'únic infantil amb `body_height_cm` + `age_months_*` complets i coherents |

*Alternativa al 4t lloc si el criteri és «ús» i no «qualitat de dada»:* **42
`BABY_MONTHS_COM`** (3 SP, més usat que el 35).

---

## F · LA PROPOSTA — v. [`REPORT_NIT_CAPES.md`](REPORT_NIT_CAPES.md) §7.1

**Res d'això s'ha executat.** El resum: **2 esborrables sense discussió** (26, 6) · **22 a no
tocar** · **6 que necessiten la paraula de l'Agus** (D1-D6).
