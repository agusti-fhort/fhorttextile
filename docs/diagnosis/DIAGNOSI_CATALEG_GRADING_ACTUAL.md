131 objects imported automatically (use -v 2 for details).

# DIAGNOSI CATÀLEG GRADING — STAGING (read-only) — 2026-07-19

> Patró A · staging `dev` · schema `fhort` · IP 178.105.48.204 · git `4630464`. Cap escriptura de dades.
> Extracció amb `scripts_tmp/extract_grading_catalog.py` (NO commitejat). Camps adaptats: vegeu §Adaptacions.

## ⚠️ CONTRAST AMB L'ESPERAT (llegir primer)

| esperat (brief) | real | veredicte |
|---|---|---|
| 14 rulesets v3 · 300 regles | **14 CLIENT_RUN LOS = exactament 300 regles** | ✅ CONFIRMAT |
| 14 SizingProfiles LOS | **14** (customer=LOS) | ✅ CONFIRMAT |
| 10 systems LOS | **11** | ⚠️ +1 |
| 0 regles a POMs morts | **14 a POM inactiu + 57 a POM sense pom_global** | ⚠️ CONTRADIT (global) |

**⚠️-1 · Systems LOS = 11, no 10.** L'extra és **`MAN_LOS_01`** ('LOS Man Alpha S-6XL') — **cap ruleset
l'usa** (el ruleset Man va per `MAN_NUM_LOS_01`). Sistema definit i orfe.

**⚠️-2 · Regles a POMs "morts" ≠ 0 globalment, però els 14 v3 estan NETS.** Les 14+57 regles brutes
NO són a cap dels 14 CLIENT_RUN v3 (aquests: 0 POM mort). Es concentren en:
· **`LOS Kids Knit Regular 2Y - 12Y`** (l'únic LOS afectat: 5 POM inactiu + 9 sense pom_global) — vegeu ⚠️-3.
· No-LOS: `EU Knit Baby Months` (canònic), i rulesets de prova/demo `BRW · Blusa`, `Prova BRW ALPHA UE`,
  `Importació fitxa · FTT-CO27-0001`, `Importació fitxa · BRW-SS27-0001`.

**⚠️-3 · 15è ruleset LOS "legacy" fora del patró v3.** `LOS Kids Knit Regular 2Y - 12Y` té **origen=None**
(no CLIENT_RUN), **construction=None · fit=None**, system `GIRL_LOS_03`, 19 regles, i és l'ÚNIC LOS amb
POMs morts. No encaixa amb el patró dels 14 v3 (que tenen origen/constr/fit i POMs nets). Candidat a revisió.

**⚠️-4 · Fals positiu a la §5.** `'Man Knit'` casa amb `'LOS Woman Knit — Tops'` perquè "wo**man knit**" el
conté. **NO existeix cap ruleset 'Man Knit'** real. Confirmat: les 2 cel·les noves (**Man Knit Tops** i
**Teen Girl Knit Tops**) **NO existeixen** encara → es poden crear netes.

**✅ Resolució d'àlies (§7): 29/29 codis dels màsters resolen via ALIAS a POMs ACTIUS.** Cap "NO RESOLT".

---

## Customer LOS: (6, 'LOSAN IBERIA SA')

## 1. GradingRuleSet (TOTS, agrupats per origen)
- [CANONICAL] 'EU Knit Baby Regular' | customer=None | system=BABY_EU_CM | targets=['BABY_BOY', 'BABY_GIRL', 'BABY_UNISEX'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=25 | talla_base(regles)=['128']
- [CANONICAL] 'EU Knit Kids Regular' | customer=None | system=KIDS_EU | targets=['BOY', 'GIRL'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=20 | talla_base(regles)=['128']
- [CANONICAL] 'EU Knit Man Regular' | customer=None | system=ALPHA_EU_M | targets=['MAN'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=16 | talla_base(regles)=['M']
- [CANONICAL] 'EU Knit Teen Regular' | customer=None | system=TEEN_ALPHA | targets=['TEEN_BOY', 'TEEN_GIRL'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=18 | talla_base(regles)=['M']
- [CANONICAL] 'EU Knit Toddler Regular' | customer=None | system=TODDLER_EU | targets=['TODDLER_BOY', 'TODDLER_GIRL'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=19 | talla_base(regles)=['128']
- [CANONICAL] 'EU Knit Woman Regular' | customer=None | system=ALPHA_EU_W | targets=['WOMAN'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=40 | talla_base(regles)=['M']
- [CANONICAL] 'EU Stretch Woman Slim' | customer=None | system=ALPHA_EU_W | targets=['WOMAN'] | constr=STRETCH_KNIT | fit=SLIM | item=None | grup/abast=None | actiu=True | n_regles=19 | talla_base(regles)=['S']
- [CANONICAL] 'EU Stretch Woman Swim' | customer=None | system=ALPHA_EU_W | targets=['WOMAN'] | constr=STRETCH_KNIT | fit=SLIM | item=None | grup/abast=None | actiu=True | n_regles=18 | talla_base(regles)=['S']
- [CANONICAL] 'EU Woven Man Regular' | customer=None | system=ALPHA_EU_M | targets=['MAN'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=35 | talla_base(regles)=['M']
- [CANONICAL] 'EU Woven Woman Numeric' | customer=None | system=NUMERIC_EU_W | targets=['WOMAN'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=61 | talla_base(regles)=['128']
- [CANONICAL] 'EU Woven Woman Regular' | customer=None | system=ALPHA_EU_W | targets=['WOMAN'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=61 | talla_base(regles)=['M']
- [CLIENT_RUN] 'BRW · Blusa · ALPHA_EU_W' | customer=BRW | system=ALPHA_EU_W | targets=['WOMAN'] | constr=WOVEN | fit=REGULAR | item=blouse | grup/abast=TOPS | actiu=True | n_regles=34 | talla_base(regles)=['S']
- [CLIENT_RUN] 'LOS Baby Knit — Tops' | customer=LOS | system=BABY_LOS_01 | targets=['TODDLER_BOY', 'TODDLER_GIRL'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=16 | talla_base(regles)=['03/06']
- [CLIENT_RUN] 'LOS Kids Boy Woven — Bottoms' | customer=LOS | system=BOY_LOS_01 | targets=['BOY'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=BOTTOMS | actiu=True | n_regles=25 | talla_base(regles)=['2']
- [CLIENT_RUN] 'LOS Kids Girl — Dresses' | customer=LOS | system=GIRL_LOS_01 | targets=['GIRL'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=DRESSES | actiu=True | n_regles=18 | talla_base(regles)=['2']
- [CLIENT_RUN] 'LOS Man Woven — Bottoms' | customer=LOS | system=MAN_NUM_LOS_01 | targets=['MAN'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=BOTTOMS | actiu=True | n_regles=23 | talla_base(regles)=['42']
- [CLIENT_RUN] 'LOS New Born Knit — Bottoms' | customer=LOS | system=NEWBORN_LOS_01 | targets=['BABY_BOY', 'BABY_GIRL', 'BABY_UNISEX'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=20 | talla_base(regles)=['00/01']
- [CLIENT_RUN] 'LOS New Born Knit — Onepieces' | customer=LOS | system=NEWBORN_LOS_01 | targets=['BABY_BOY', 'BABY_GIRL', 'BABY_UNISEX'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=38 | talla_base(regles)=['00/01']
- [CLIENT_RUN] 'LOS New Born Knit — Tops' | customer=LOS | system=NEWBORN_LOS_01 | targets=['BABY_BOY', 'BABY_GIRL', 'BABY_UNISEX'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=37 | talla_base(regles)=['00/01']
- [CLIENT_RUN] 'LOS Teen Boy Knit — Tops' | customer=LOS | system=YOUTH_BOY_LOS_01 | targets=['TEEN_BOY'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=TOPS | actiu=True | n_regles=18 | talla_base(regles)=['8']
- [CLIENT_RUN] 'LOS Teen Boy Woven — Bottoms' | customer=LOS | system=YOUTH_BOY_LOS_01 | targets=['TEEN_BOY'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=BOTTOMS | actiu=True | n_regles=19 | talla_base(regles)=['8']
- [CLIENT_RUN] 'LOS Teen Boy Woven — Shirts' | customer=LOS | system=YOUTH_BOY_LOS_01 | targets=['TEEN_BOY'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=TOPS | actiu=True | n_regles=22 | talla_base(regles)=['8']
- [CLIENT_RUN] 'LOS Teen Girl — Bottoms' | customer=LOS | system=YOUTH_GIRL_LOS_01 | targets=['TEEN_GIRL'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=BOTTOMS | actiu=True | n_regles=12 | talla_base(regles)=['8']
- [CLIENT_RUN] 'LOS Teen Girl Stretch — Swimwear' | customer=LOS | system=YOUTH_GIRL_LOS_01 | targets=['TEEN_GIRL'] | constr=STRETCH_KNIT | fit=REGULAR | item=None | grup/abast=SWIMWEAR | actiu=True | n_regles=11 | talla_base(regles)=['8']
- [CLIENT_RUN] 'LOS Woman Knit — Tops' | customer=LOS | system=WOMAN_LOS_01 | targets=['WOMAN'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=TOPS | actiu=True | n_regles=17 | talla_base(regles)=['S']
- [CLIENT_RUN] 'LOS Woman Woven — Bottoms' | customer=LOS | system=WOMAN_NUM_LOS_01 | targets=['WOMAN'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=BOTTOMS | actiu=True | n_regles=24 | talla_base(regles)=['38']
- [CLIENT_RUN] 'Prova BRW ALPHA UE' | customer=BRW | system=WOMAN_BRW_01 | targets=['WOMAN'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=21 | talla_base(regles)=['S']
- [None] 'Custom Alpha EU — Women' | customer=None | system=None | targets=[] | constr=STRETCH_KNIT | fit=SLIM | item=None | grup/abast=None | actiu=True | n_regles=19 | talla_base(regles)=['S']
- [None] 'EU Knit Baby Months' | customer=None | system=BABY_MONTHS_COM | targets=['BABY_UNISEX'] | constr=WOVEN | fit=REGULAR | item=None | grup/abast=None | actiu=True | n_regles=9 | talla_base(regles)=['0M-1M']
- [None] 'EU Knit Woman Slim' | customer=None | system=None | targets=['WOMAN'] | constr=KNIT | fit=SLIM | item=None | grup/abast=None | actiu=True | n_regles=40 | talla_base(regles)=['128']
- [None] 'EU Stretch Woman Bodycon' | customer=None | system=None | targets=['WOMAN'] | constr=STRETCH_KNIT | fit=BODYCON | item=None | grup/abast=None | actiu=True | n_regles=19 | talla_base(regles)=['128']
- [None] 'EU Woven Dress Flared' | customer=None | system=None | targets=['WOMAN'] | constr=WOVEN | fit=FLARED | item=None | grup/abast=None | actiu=True | n_regles=9 | talla_base(regles)=['128']
- [None] 'EU Woven Man Slim' | customer=None | system=None | targets=['MAN'] | constr=WOVEN | fit=SLIM | item=None | grup/abast=None | actiu=True | n_regles=35 | talla_base(regles)=['128']
- [None] 'EU Woven Woman Oversized' | customer=None | system=None | targets=['WOMAN'] | constr=WOVEN | fit=OVERSIZED | item=None | grup/abast=None | actiu=True | n_regles=61 | talla_base(regles)=['128']
- [None] 'EU Woven Woman Relaxed' | customer=None | system=None | targets=['WOMAN'] | constr=WOVEN | fit=RELAXED | item=None | grup/abast=None | actiu=True | n_regles=61 | talla_base(regles)=['128']
- [None] 'EU Woven Woman Slim' | customer=None | system=ALPHA_EU_W | targets=['WOMAN'] | constr=WOVEN | fit=SLIM | item=None | grup/abast=None | actiu=True | n_regles=61 | talla_base(regles)=['M']
- [None] 'Importació fitxa · BRW-SS27-0001' | customer=None | system=ALPHA_EU_W | targets=['WOMAN'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=TOPS | actiu=True | n_regles=6 | talla_base(regles)=['S']
- [None] 'Importació fitxa · FTT-CO27-0001' | customer=None | system=ALPHA_EU_W | targets=['WOMAN'] | constr=KNIT | fit=REGULAR | item=None | grup/abast=BOTTOMS | actiu=True | n_regles=20 | talla_base(regles)=['S']
- [None] 'LOS Kids Knit Regular 2Y - 12Y' | customer=LOS | system=GIRL_LOS_03 | targets=['GIRL'] | constr=None | fit=None | item=None | grup/abast=None | actiu=True | n_regles=19 | talla_base(regles)=['2']
- [None] 'Mango EU woven woman regular - only dress' | customer=None | system=ALPHA_EU_W | targets=['WOMAN'] | constr=None | fit=None | item=None | grup/abast=None | actiu=True | n_regles=0 | talla_base(regles)=[]

## 2. SizeSystems LOS (codi, talles ordenades, targets)
- BABY_LOS_01 'LOS Baby 3-36M' | targets=['TODDLER_BOY', 'TODDLER_GIRL'] | talles=['03/06', '06/09', '09/12', '12/18', '18/24', '24/36']
- BOY_LOS_01 'LOS Kids Boy 2-12Y' | targets=['BOY'] | talles=['2', '3', '4', '5', '6', '7', '8', '9/10', '11/12']
- GIRL_LOS_01 'LOS Kids Girl 2-12Y' | targets=['GIRL'] | talles=['2', '3', '4', '5', '6', '7', '8', '9/10', '11/12']
- GIRL_LOS_03 'Nena AGE_YEARS — LOSAN IBERIA SA Run 03' | targets=['GIRL'] | talles=['2', '3', '4', '5', '6', '7', '8', '9/10', '11/12']
- MAN_LOS_01 'LOS Man Alpha S-6XL' | targets=['MAN'] | talles=['S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL', '6XL']
- MAN_NUM_LOS_01 'LOS Man Numeric 38-58' | targets=['MAN'] | talles=['38', '40', '42', '44', '46', '48', '50', '52', '54', '56', '58']
- NEWBORN_LOS_01 'LOS New Born 0-24M' | targets=['BABY_BOY', 'BABY_GIRL', 'BABY_UNISEX'] | talles=['00/01', '01/03', '03/06', '06/09', '09/12', '12/18', '18/24']
- WOMAN_LOS_01 'LOS Woman Alpha XS-3XL' | targets=['WOMAN'] | talles=['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL']
- WOMAN_NUM_LOS_01 'LOS Woman Numeric 36-52' | targets=['WOMAN'] | talles=['36', '38', '40', '42', '44', '46', '48', '50', '52']
- YOUTH_BOY_LOS_01 'LOS Teen Boy 8-16Y' | targets=['TEEN_BOY'] | talles=['8', '10', '12', '14', '16']
- YOUTH_GIRL_LOS_01 'LOS Teen Girl 8-16Y' | targets=['TEEN_GIRL'] | talles=['8', '10', '12', '14', '16']

## 3. SizingProfiles (target, construction, fit, system, ruleset, is_default, customer)
- target=WOMAN constr=WOVEN fit=REGULAR system=ALPHA_EU_W ruleset='BRW · Blusa · ALPHA_EU_W' default=True customer=BRW
- target=WOMAN constr=WOVEN fit=FLARED system=ALPHA_EU_W ruleset='EU Woven Woman Regular' default=False customer=None
- target=WOMAN constr=WOVEN fit=REGULAR system=ALPHA_EU_W ruleset='Mango EU woven woman regular - only dress' default=True customer=None
- target=WOMAN constr=WOVEN fit=REGULAR system=WOMAN_NUM_LOS_01 ruleset='LOS Woman Woven — Bottoms' default=False customer=LOS
- target=WOMAN constr=WOVEN fit=REGULAR system=ALPHA_EU_W ruleset='EU Woven Woman Regular' default=True customer=None
- target=WOMAN constr=WOVEN fit=SLIM system=ALPHA_EU_W ruleset='EU Woven Woman Slim' default=False customer=None
- target=WOMAN constr=KNIT fit=REGULAR system=WOMAN_LOS_01 ruleset='LOS Woman Knit — Tops' default=False customer=LOS
- target=WOMAN constr=KNIT fit=REGULAR system=ALPHA_EU_W ruleset='EU Knit Woman Regular' default=True customer=None
- target=WOMAN constr=STRETCH_KNIT fit=SLIM system=ALPHA_EU_W ruleset='Custom Alpha EU — Women' default=False customer=None
- target=WOMAN constr=STRETCH_KNIT fit=SLIM system=ALPHA_EU_W ruleset='EU Stretch Woman Slim' default=True customer=None
- target=MAN constr=WOVEN fit=REGULAR system=MAN_NUM_LOS_01 ruleset='LOS Man Woven — Bottoms' default=False customer=LOS
- target=MAN constr=WOVEN fit=REGULAR system=ALPHA_EU_M ruleset='EU Woven Man Regular' default=True customer=None
- target=MAN constr=KNIT fit=REGULAR system=ALPHA_EU_M ruleset='EU Knit Man Regular' default=True customer=None
- target=BABY_GIRL constr=KNIT fit=REGULAR system=BABY_MONTHS_COM ruleset='EU Knit Baby Months' default=True customer=None
- target=BABY_GIRL constr=KNIT fit=REGULAR system=BABY_EU_CM ruleset='EU Knit Baby Regular' default=True customer=None
- target=BABY_GIRL constr=KNIT fit=REGULAR system=NEWBORN_LOS_01 ruleset='LOS New Born Knit — Tops' default=False customer=LOS
- target=BABY_GIRL constr=KNIT fit=REGULAR system=NEWBORN_LOS_01 ruleset='LOS New Born Knit — Bottoms' default=False customer=LOS
- target=BABY_GIRL constr=KNIT fit=REGULAR system=NEWBORN_LOS_01 ruleset='LOS New Born Knit — Onepieces' default=False customer=LOS
- target=BABY_BOY constr=KNIT fit=REGULAR system=BABY_EU_CM ruleset='EU Knit Baby Regular' default=True customer=None
- target=BABY_BOY constr=KNIT fit=REGULAR system=BABY_MONTHS_COM ruleset='EU Knit Baby Months' default=True customer=None
- target=BABY_UNISEX constr=KNIT fit=REGULAR system=BABY_MONTHS_COM ruleset='EU Knit Baby Months' default=True customer=None
- target=BABY_UNISEX constr=KNIT fit=REGULAR system=BABY_MONTHS ruleset='EU Knit Baby Regular' default=True customer=None
- target=BABY_UNISEX constr=KNIT fit=REGULAR system=BABY_EU_CM ruleset='EU Knit Baby Regular' default=True customer=None
- target=TODDLER_GIRL constr=KNIT fit=REGULAR system=BABY_LOS_01 ruleset='LOS Baby Knit — Tops' default=False customer=LOS
- target=TODDLER_GIRL constr=KNIT fit=REGULAR system=TODDLER_EU ruleset='EU Knit Toddler Regular' default=True customer=None
- target=TODDLER_GIRL constr=KNIT fit=REGULAR system=GIRL_LOS_03 ruleset='LOS Kids Knit Regular 2Y - 12Y' default=True customer=None
- target=TODDLER_BOY constr=KNIT fit=REGULAR system=TODDLER_EU ruleset='EU Knit Toddler Regular' default=True customer=None
- target=TODDLER_BOY constr=KNIT fit=REGULAR system=GIRL_LOS_03 ruleset='LOS Kids Knit Regular 2Y - 12Y' default=True customer=None
- target=GIRL constr=KNIT fit=REGULAR system=KIDS_EU ruleset='EU Knit Kids Regular' default=True customer=None
- target=GIRL constr=KNIT fit=REGULAR system=GIRL_LOS_03 ruleset='LOS Kids Knit Regular 2Y - 12Y' default=True customer=None
- target=GIRL constr=KNIT fit=REGULAR system=GIRL_LOS_01 ruleset='LOS Kids Girl — Dresses' default=False customer=LOS
- target=BOY constr=WOVEN fit=REGULAR system=BOY_LOS_01 ruleset='LOS Kids Boy Woven — Bottoms' default=False customer=LOS
- target=BOY constr=KNIT fit=REGULAR system=KIDS_EU ruleset='EU Knit Kids Regular' default=True customer=None
- target=BOY constr=KNIT fit=REGULAR system=GIRL_LOS_03 ruleset='LOS Kids Knit Regular 2Y - 12Y' default=True customer=None
- target=TEEN_GIRL constr=WOVEN fit=REGULAR system=YOUTH_GIRL_LOS_01 ruleset='LOS Teen Girl — Bottoms' default=False customer=LOS
- target=TEEN_GIRL constr=KNIT fit=REGULAR system=TEEN_ALPHA ruleset='EU Knit Teen Regular' default=True customer=None
- target=TEEN_GIRL constr=STRETCH_KNIT fit=REGULAR system=YOUTH_GIRL_LOS_01 ruleset='LOS Teen Girl Stretch — Swimwear' default=False customer=LOS
- target=TEEN_BOY constr=WOVEN fit=REGULAR system=YOUTH_BOY_LOS_01 ruleset='LOS Teen Boy Woven — Bottoms' default=False customer=LOS
- target=TEEN_BOY constr=WOVEN fit=REGULAR system=YOUTH_BOY_LOS_01 ruleset='LOS Teen Boy Woven — Shirts' default=False customer=LOS
- target=TEEN_BOY constr=KNIT fit=REGULAR system=TEEN_ALPHA ruleset='EU Knit Teen Regular' default=True customer=None
- target=TEEN_BOY constr=KNIT fit=REGULAR system=YOUTH_BOY_LOS_01 ruleset='LOS Teen Boy Knit — Tops' default=False customer=LOS

## 4. Regles a POMs desactivats o sense pom_global
- regles a POM inactiu: 14 | regles a POM sense pom_global: 57

## 5. Cerca de cel·les 'Man Knit Tops' i 'Teen Girl Knit Tops'
- 'Man Knit': ['LOS Woman Knit — Tops']
- 'Teen Girl Knit': CAP

## 6. Fit types al sistema
['ATHLETIC', 'BODYCON', 'CUSTOM', 'FLARED', 'OVERSIZED', 'REGULAR', 'RELAXED', 'SLIM', 'STRAIGHT', 'TAPERED']

## 7. Codis dels màsters → POMMaster (via àlies LOS o codi directe)
- B: ALIAS → CH 'Chest width' actiu=True
- C: ALIAS → WA 'Waist width' actiu=True
- C3: ALIAS → C3 'WAIST LOCATION' actiu=True
- D: ALIAS → HI PA 'Hip width (pants)' actiu=True
- D1: ALIAS → THI 'Thigh width' actiu=True
- D2: ALIAS → KNE 'Knee width' actiu=True
- D11: ALIAS → D.11-M79 'HIP LOCATION' actiu=True
- D22: ALIAS → D22 'KNEE LOCATION' actiu=True
- E: ALIAS → SK SW 'Skirt sweep (bottom width)' actiu=True
- F: ALIAS → LEG OP 'Leg opening' actiu=True
- T1: ALIAS → RI FR 'Rise (front)' actiu=True
- T2: ALIAS → RI BK 'Rise (back)' actiu=True
- M: ALIAS → M-M79 'TOTAL LENGTH' actiu=True
- K: ALIAS → SH 'Shoulder width' actiu=True
- K1: ALIAS → SH DR 'Shoulder drop' actiu=True
- K2: ALIAS → AC SH 'Across shoulder (back)' actiu=True
- L3: ALIAS → NK W 'Neck width' actiu=True
- L4: ALIAS → NK DR FR 'Neck drop front' actiu=True
- L5: ALIAS → NK DR BK 'Neck drop back' actiu=True
- BJ: ALIAS → BJ 'FRONT&BACK WIDTH LOCATION' actiu=True
- A1: ALIAS → AC FR 'Across front' actiu=True
- A2: ALIAS → AC BK 'Across back' actiu=True
- H: ALIAS → BIC 'Sleeve width at bicep' actiu=True
- H4: ALIAS → ELB 'Sleeve width at elbow' actiu=True
- H6: ALIAS → AH DEP 'Armhole depth' actiu=True
- H11: ALIAS → SL OP 'Sleeve opening / Cuff width' actiu=True
- G: ALIAS → SL 'Sleeve length' actiu=True
- G5: ALIAS → G5 'ELBOW LOCATION' actiu=True
- GA: ALIAS → GA 'SLEEVE INSEAM LENGTH' actiu=True

## Adaptacions (camps reals verificats amb els models)
- Customer viu a `fhort.tasks.models`, NO a `fhort.models_app.models`.
- SizeSystem: el codi és `.codi` (NO `.code`) — a rulesets/systems/profiles i a l'order_by.
- POMMaster: `.codi_client` (NO `.codi`) i `.nom_client` (NO `.descripcio_local`/`.descripcio`).
- CustomerPOMAlias: `.client_code` (NO `.alias`); filtre `client_code__iexact`.
- FitType SÍ és taula (`fhort.pom.models.FitType`, camp `.codi`).
- GradingRuleSet.construction/fit_type/garment_group/target/customer són FK → es bolca `.codi`.
- garment_type_item no té `.codi`: es bolca `.code`.

# FI — read-only, cap escriptura feta
