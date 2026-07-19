# PAS 3 — Re-sembra grading v3 LOSAN (informe final)

> Staging · `fhort` · dev. Data: 2026-07-19. Dades només, dry-run primer, motor NO tocat.
> NO push. Command `seed_losan_grading_v3 --phase {delete,rename,seed}`. Config
> `losan_grading_v3.py` + `grading_rules_v3_delta.json` + JSON v1/v2 (repo).
> Tanca el PLA v3 (PAS 1 diagnosi · PAS 2 gate · PAS 4 catàleg net · PAS 3 grading definitiu).

## Resum

| fase | resultat |
|---|---|
| 3.0 esborrat | 18 GradingRuleSet LOS SS27 (v1/v2 rebutjats) + 162 GradingRule esborrats · ISO/BRW intactes |
| 3.1 rename | 10 size systems LOS renombrats (noms EN; codis/talles/targets intactes) |
| 3.2 re-sembra | **14 rulesets · 300 regles · 14 SizingProfiles · 0 buits** |
| 3.3 verificació | **la prova del cotó PASSA** (1 resultat estricte per cas) |

## 3.0 — Esborrat

`GradingRuleSet` amb `customer=LOS · origen=CLIENT_RUN · nom acaba en 'SS27'` = 18 → esborrats
amb les seves `GradingRule` (162, CASCADE). `Model.grading_rule_set` SET_NULL (0 models de
prova). 0 SizingProfiles/scope_nodes penjaven. ISO/BRW: intactes (11 is_system_default). Rulesets
totals: 44 → 26.

## 3.1 — Rename (codis intactes)

`NEWBORN_LOS_01→"LOS New Born 0-24M"` · `BABY_LOS_01→"LOS Baby 3-36M"` ·
`GIRL_LOS_01→"LOS Kids Girl 2-12Y"` · `BOY_LOS_01→"LOS Kids Boy 2-12Y"` ·
`YOUTH_GIRL_LOS_01→"LOS Teen Girl 8-16Y"` · `YOUTH_BOY_LOS_01→"LOS Teen Boy 8-16Y"` ·
`WOMAN_LOS_01→"LOS Woman Alpha XS-3XL"` · `MAN_LOS_01→"LOS Man Alpha S-6XL"` ·
`WOMAN_NUM_LOS_01→"LOS Woman Numeric 36-52"` · `MAN_NUM_LOS_01→"LOS Man Numeric 38-58"`.

## 3.2 — Re-sembra v3 (14 cel·les)

Cada ruleset compleix l'ESPEC de DIAGNOSI_GRADING_V3: `origen=CLIENT_RUN` · `customer=LOS` ·
`size_system` · **`targets` M2M plens** · **`construction` FK** · `fit=REGULAR` ·
**`garment_type_item=NULL`** · ABAST (`garment_group` per grup / `RuleSetScopeNode` ITEM per als
newborn) · **1 `SizingProfile`** (is_default=False, customer=LOS). Regles via àlies LOS→POM
consolidat (PAS 4); noms SENSE temporada.

| # | ruleset | system | targets | constr | abast | break | regles |
|---|---|---|---|---|---|---|---|
| 1 | LOS New Born Knit — Tops | New Born | BABY_G/B/UNI | KNIT | items baby_top,baby_bodysuit | — | 37 |
| 2 | LOS New Born Knit — Bottoms | New Born | id | KNIT | items baby_leggings,baby_bloomers | — | 20 |
| 3 | LOS New Born Knit — Onepieces | New Born | id | KNIT | items baby_sleepsuit,baby_sleepbag,booties | — | 38 |
| 4 | LOS Baby Knit — Tops | Baby | TODDLER_G/B | KNIT | items baby_top,baby_bodysuit | — | 16 |
| 5 | LOS Kids Girl — Dresses | Kids Girl | GIRL | KNIT | group DRESSES | 9/10 | 18 |
| 6 | LOS Kids Boy Woven — Bottoms | Kids Boy | BOY | WOVEN | group BOTTOMS | 9/10 | 25 |
| 7 | LOS Teen Boy Knit — Tops | Teen Boy | TEEN_BOY | KNIT | group TOPS | — | 18 |
| 8 | LOS Teen Boy Woven — Shirts | Teen Boy | TEEN_BOY | WOVEN | group TOPS | — | 22 |
| 9 | LOS Teen Boy Woven — Bottoms | Teen Boy | TEEN_BOY | WOVEN | group BOTTOMS | — | 19 |
| 10 | LOS Teen Girl — Bottoms | Teen Girl | TEEN_GIRL | WOVEN | group BOTTOMS | 14 | 12 |
| 11 | LOS Teen Girl Stretch — Swimwear | Teen Girl | TEEN_GIRL | STRETCH_KNIT | group SWIMWEAR | — | 11 |
| 12 | LOS Woman Knit — Tops | Woman Alpha | WOMAN | KNIT | group TOPS | — | 17 |
| 13 | LOS Woman Woven — Bottoms | Woman Numeric | WOMAN | WOVEN | group BOTTOMS | — | 24 |
| 14 | LOS Man Woven — Bottoms | Man Numeric | MAN | WOVEN | group BOTTOMS | — | 23 |

**TOTAL: 300 regles.** Fonts: delta (cel·les 1,2,3,7,8) · v1 BOW/CRUZADO (5,11) · v2 GLACIAR/
TARRAGONA/JEREMY/GALA/DANIELA/BUDAPEST/ENRIC (4,6,9,10,12,13,14). La WA parcial de GALA (v1)
NO re-sembrada (retirada). Excepcions anotades al delta (LUZ G=0.5, SAFARI pant llarg) NO
sembrades (aniran a ModelGradingOverride).

**1 àlies omès:** `AW` (CHEST MOTIVE LOCATION) a New Born Tops — no té àlies LOS al catàleg
consolidat (motive-location, inc 0.3). Llistat, no inventat. (37 regles en lloc de 38.)

## 3.3 — Verificació ESTRICTA (la prova del rebuig d'Agus)

**1. `matchingRuleSetsStrict` (frontend, replicat en Python) — EXACTAMENT 1 per cas:**
- (a) nena toddler + punt + tops (item baby_top, ss BABY_LOS_01) → **`LOS Baby Knit — Tops`** ✓
- (b) teen boy + woven + bottoms (ss YOUTH_BOY_LOS_01) → **`LOS Teen Boy Woven — Bottoms`** ✓
- (c) teen girl + elàstic + swimwear (ss YOUTH_GIRL_LOS_01) → **`LOS Teen Girl Stretch — Swimwear`** ✓

**2. Suggeridor de perfils (`sizing_profiles_view`)** — cada cel·la retorna EL SEU profile
(customer LOS, is_default=False), grup 0 del rànquing: (a)→Baby Knit Tops · (b)→Teen Boy Woven
Bottoms · (c)→Teen Girl Stretch Swimwear. 14 SizingProfiles.

**3. `cerca_contenidor_client` (item=NULL) — comportament (només lectura, motor intacte):**
- `(LOS, YOUTH_BOY, item=NULL, REGULAR)` → retorna un ruleset (el de menor id entre els que
  comparteixen customer+system+fit amb item=NULL).
- `(LOS, YOUTH_BOY, item=trousers, REGULAR)` → **None**: un model amb item CONCRET NO casa amb
  els rulesets v3 (item=NULL). **Coexistència documentada:** el v3 s'assigna via wizard →
  SizingProfile → `Model.grading_rule_set` (payload), NO via el matcher d'import de fitxa (que
  crea contenidors per-(customer,system,item)). Si algun dia l'import ha de reutilitzar els
  rulesets amplis, caldria un fallback item=NULL al matcher — decisió de motor, FORA d'aquest pas.

**4. Counts:** 14 rulesets · **0 buits** · 300 regles · **0 regles a POM desactivat** ·
14 SizingProfiles. `manage.py check` net · servei reiniciat.

## Estat final
El grading LOS és **definitiu i respon als filtres del wizard** (a diferència dels 18-per-item
rebutjats). Pendent menor: 2 cel·les del gate sense font (Home Knit/BERG, Teen Girl Knit/ONA)
NO creades fins que arribi la fitxa · l'àlies AW · la coexistència item=NULL amb l'import.
