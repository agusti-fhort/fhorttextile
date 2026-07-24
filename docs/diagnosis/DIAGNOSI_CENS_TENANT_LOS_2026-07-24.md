# CENS ESTRUCTURAL DEL TENANT LOS — 2026-07-24

**Patró A · READ-ONLY estricte.** Tot el cens s'ha executat amb `manage.py shell` sota
`schema_context('los')` (i `'fhort'` només per a §5), amb un **guard actiu** que bloqueja qualsevol
escriptura (`Model.save/delete`, `QuerySet.update/delete/create/bulk_create/get_or_create` →
`RuntimeError`). Cap migració, cap restart, cap fitxer fora de `/var/www/fhort-textile`.

Els scripts que han produït cada xifra viuen a `scratchpad/cens/p0..p8_*.py` de la sessió; cada
secció porta la query ORM al costat. **Cap pk s'ha de considerar estable**: sempre hi ha la clau
natural (codi/etiqueta/nom) al costat.

> **Nota d'abast:** els 961 models apareixen NOMÉS en agregat (§6.3). No hi ha cap llistat model a model.

---

## 0. ENTORN

```python
# schemes
SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname<>'information_schema'
```

| | |
|---|---|
| Schemes a la BD | `fhort`, `los`, `public` |
| **Client id=5** | `schema_name='los'` · `nom='LOSAN'` · `codi_tenant='LOS'` · **`tipologia='marca'`** · `plan=Brand` · `actiu=True` · `estat='actiu'` · `onboarding_complet=True` · `data_alta=2026-07-19` |
| Fiscal | `rao_social='LOSAN IBERIA, SL'` · `nif='B22598536'` · Terrassa · `regim_vat='espanyol'` |
| Domini | `losan.fhorttextile.tech` (`is_primary=True`, únic per al tenant 5) |
| HEAD de `main` | `4e32fe3` · 2026-07-24 07:07:44 +0000 · *merge: self customer visible en tenants Marca (4f34e7c..6c5ab64)* — és també l'últim merge |
| Migracions | **0 pendents** al schema `los` (`MigrationExecutor.migration_plan(leaf_nodes)`), 239 registrades |

Els altres tenants, per context: `public` (id=1, SYS, estudi) i `fhort` (id=2, FTT, estudi).

---

## 1. CATÀLEG DE PECES (schema `los`)

### 1.1 GarmentGroup — 12, tots `actiu=True`

`GarmentGroup.objects.all()` + `GarmentType.objects.filter(grup=g.codi)` + `GarmentTypeItem.objects.filter(garment_type__grup=…)`

| codi | nom | types (actius) | items |
|---|---|---|---|
| ACCESSORIES | Accessories | 1 (1) | 3 |
| BOTTOMS | Bottoms | 3 (3) | 10 |
| DRESSES | Dresses & Jumpsuits | 4 (2) | 7 |
| **DRESSES-FULL** | Dresses & Full Length | **0** | **0** |
| **KNITWEAR** | Knitwear | **0** | **0** |
| NEWBORN | Newborn | 1 (1) | 9 |
| OUTERWEAR | Outerwear | 2 (2) | 7 |
| SWIMWEAR | Swimwear | 1 (1) | 3 |
| TOPS | Tops | 7 (5) | 14 |
| **TOPS-KNIT** | Tops — Knitwear | **0** | **0** |
| **TOPS-WOVEN** | Tops — Woven | **0** | **0** |
| UNDERWEAR | Underwear & Lingerie | 2 (2) | 9 |

**4 grups completament buits** (0 famílies, 0 items, 0 rulesets que hi apuntin) i tot i així `actiu=True`:
`DRESSES-FULL`, `KNITWEAR`, `TOPS-KNIT`, `TOPS-WOVEN`. Vegeu §7.

### 1.2 GarmentType — 21 (17 actius · 4 inactius)

| codi_client | nom | grup | actiu | is_system | items |
|---|---|---|---|---|---|
| ACCESSORIES | Accessories | ACCESSORIES | ✔ | False | 3 |
| LEGGINGS_TIGHTS | Leggings & Tights | BOTTOMS | ✔ | True | 2 |
| SKIRTS | Skirts | BOTTOMS | ✔ | True | 2 |
| TAILORED_PANTS | Tailored & Rigid Pants | BOTTOMS | ✔ | True | 6 |
| ADULT_JUMPSUITS | Adult Jumpsuits & Overalls | DRESSES | ✔ | True | 3 |
| **BABY_ONEPIECES** | Baby & Kids One-Pieces | DRESSES | **✘** | True | 0 |
| **DRESS** | Dress | DRESSES | **✘** | True | 0 |
| DRESSES | Dresses | DRESSES | ✔ | True | 4 |
| NEWBORN | Newborn | NEWBORN | ✔ | False | 9 |
| HEAVY_OUTERWEAR | Heavy Outerwear | OUTERWEAR | ✔ | True | 4 |
| STRUCTURED_JACKETS | Structured Jackets | OUTERWEAR | ✔ | True | 3 |
| SWIMWEAR | Swimwear | SWIMWEAR | ✔ | True | 3 |
| **BABY_SEPARATES** | Baby & Kids Separates | TOPS | **✘** | True | 0 |
| BUTTONED_TOPS | Buttoned Tops | TOPS | ✔ | True | 4 |
| JERSEY_TOPS | Jersey Tops | TOPS | ✔ | True | 4 |
| KNIT_CARDIGANS | Knit Cardigans | TOPS | ✔ | True | 2 |
| KNIT_SWEATERS | Knit Sweaters | TOPS | ✔ | True | 2 |
| SWEATSHIRTS_MIDLAYERS | Sweatshirts & Midlayers | TOPS | ✔ | True | 2 |
| **T_SHIRT** | T-shirt | TOPS | **✘** | True | 0 |
| BRA_SHAPEWEAR | Bra & Shapewear | UNDERWEAR | ✔ | True | 3 |
| UNDERWEAR | Underwear | UNDERWEAR | ✔ | True | 6 |

Cap `GarmentType` té `garment_type_global` informat (**21/21 amb `global=None`**).

### 1.3 GarmentTypeItem — **62 confirmats**, tots `active=True`

`GarmentTypeItem.objects.annotate(n_map=Count('pom_maps'), n_map_rev=Count('pom_maps', filter=Q(pom_maps__pendent_revisio=True)))`

| xifra | valor |
|---|---|
| TOTAL items | **62** (62 actius · 0 inactius) — coincideix amb l'esperat |
| amb `base_size_definition` informada | **1 / 62** (`top_sleeveless` → `M@WOMAN_LOS_01`) |
| amb `grading_rule_set` (V1 suggerit) | **1 / 62** (`top_sleeveless` → *LOS Woman Knit — Tops*) |
| amb 0 `GarmentPOMMap` | **7** (§7 Z3) |
| TOTAL `GarmentPOMMap` | **1.748** · `pendent_revisio=True`: **238** (13,6%) |

El bolcat complet dels 62 items (code · família · grup · complexity · maps · maps pendents) és a
l'**Annex A**. Distribució de maps pendents de revisió per grup:

| grup | maps | pendent_revisio |
|---|---|---|
| TOPS | 517 | 73 |
| BOTTOMS | 296 | 57 |
| OUTERWEAR | 292 | 24 |
| DRESSES | 281 | 36 |
| NEWBORN | 162 | 19 |
| UNDERWEAR | 122 | 12 |
| SWIMWEAR | 78 | 17 |

### 1.4 Fantasmes / inactius residuals

Els 4 `GarmentType` inactius són **fantasmes nets**: 0 items, 0 models, cap referència viva.
`DRESS` i `T_SHIRT` (els que preguntaves) hi són tots dos, inactius i buits, junt amb
`BABY_ONEPIECES` i `BABY_SEPARATES`. Cap `GarmentTypeItem` inactiu.

---

## 2. TALLES

### 2.1 SizeSystem — **11** (esperats 10 LOS + residus), tots `actiu=True`, tots `customer_codi='LOS'`

Cap té `base_unit` ni `norma_ref` informats; cap té `parent`. Gènere via `targets` (llei A5).

| codi | nom | targets | #talles | seqüència completa (per `ordre`) |
|---|---|---|---|---|
| `BABY_LOS_01` | LOS Baby 3-36M | TODDLER_BOY, TODDLER_GIRL | 6 | 03/06 · 06/09 · 09/12 · 12/18 · 18/24 · 24/36 |
| `BOY_LOS_01` | LOS Kids Boy 2-12Y | BOY | 9 | 2 · 3 · 4 · 5 · 6 · 7 · 8 · 9/10 · 11/12 |
| `GIRL_LOS_01` | LOS Kids Girl 2-12Y | GIRL | 9 | 2 · 3 · 4 · 5 · 6 · 7 · 8 · 9/10 · 11/12 |
| **`GIRL_LOS_03`** | Nena AGE_YEARS — LOSAN IBERIA SA Run 03 | GIRL | 9 | 2 · 3 · 4 · 5 · 6 · 7 · 8 · 9/10 · 11/12 |
| `MAN_LOS_01` | LOS Man Alpha S-6XL | MAN | 9 | S · M · L · XL · 2XL · 3XL · 4XL · 5XL · 6XL |
| `MAN_NUM_LOS_01` | LOS Man Numeric 38-58 | MAN | 11 | 38 · 40 · 42 · 44 · 46 · 48 · 50 · 52 · 54 · 56 · 58 |
| `NEWBORN_LOS_01` | LOS New Born 0-24M | BABY_BOY, BABY_GIRL, BABY_UNISEX | 7 | 00/01 · 01/03 · 03/06 · 06/09 · 09/12 · 12/18 · 18/24 |
| `WOMAN_LOS_01` | LOS Woman Alpha XS-3XL | WOMAN | 7 | XS · S · M · L · XL · 2XL · 3XL |
| `WOMAN_NUM_LOS_01` | LOS Woman Numeric 36-52 | WOMAN | 9 | 36 · 38 · 40 · 42 · 44 · 46 · 48 · 50 · 52 |
| `YOUTH_BOY_LOS_01` | LOS Teen Boy 8-16Y | TEEN_BOY | 5 | 8 · 10 · 12 · 14 · 16 |
| `YOUTH_GIRL_LOS_01` | LOS Teen Girl 8-16Y | TEEN_GIRL | 5 | 8 · 10 · 12 · 14 · 16 |

**El residu és `GIRL_LOS_03`**: mateixa seqüència exacta de 9 etiquetes que `GIRL_LOS_01`, mateix
target, i **0 rulesets · 0 profiles · 0 models** l'utilitzen. `GIRL_LOS_01` en canvi té 2 rulesets,
2 profiles i 139 models. Vegeu §7.

Cap `SizeSystem` sense talles ni sense targets. **86 `SizeDefinition`** al tenant. Cap `ordre` duplicat
dins d'un sistema. Cap `valor_numeric` informat (tots `None`).

### 2.2 Etiquetes compostes — 19 files, tal com viuen a BD

`SizeDefinition.objects.filter(etiqueta__contains='/')`

- `BABY_LOS_01` (6): `03/06` `06/09` `09/12` `12/18` `18/24` `24/36`
- `NEWBORN_LOS_01` (7): `00/01` `01/03` `03/06` `06/09` `09/12` `12/18` `18/24`
- `BOY_LOS_01` · `GIRL_LOS_01` · `GIRL_LOS_03` (2 cadascun): `9/10` `11/12`

`03/06`, `06/09`, `09/12`, `12/18` i `18/24` **existeixen als DOS sistemes de bebè**
(`BABY_LOS_01` i `NEWBORN_LOS_01`) com a files diferents — la desambiguació és pel `size_system`,
mai per l'etiqueta sola. Les compostes de nen/nena (`9/10`, `11/12`) es repeteixen als tres
sistemes GIRL/BOY.

---

## 3. GRADING

### 3.1 Recomptes globals — **desviació respecte de l'esperat**

| | esperat | **real** | desviació |
|---|---|---|---|
| GradingRuleSet `CLIENT_RUN` | 18 | **19** | **+1** |
| GradingRule | 390 | **402** | **+12** |
| SizingProfile | 18 | **18** | ✔ |

`GradingRuleSet.objects.count()` · `Counter(values_list('origen'))` · `GradingRule.objects.count()`

**Els dos excedents són el mateix objecte.** Tot el desviament s'explica per un contenidor de més:

> **`LOSAN IBERIA SA · Newborn · LOS Baby 3-36M`** (id=55) — 12 regles.
> `19 − 1 = 18` rulesets · `402 − 12 = 390` regles → **exactament les xifres de referència**.

Té nom amb el patró antic (raó social + grup + sistema), `size_system=BABY_LOS_01`,
`garment_group=NEWBORN`, `targets={TODDLER_GIRL}` (un de sol, mentre els seus germans en porten 2-3),
**cap `scope_node`**, **cap `SizingProfile` que l'exposi** i **1 model** enganxat. Vegeu §3.6 i §7.

Tots 19 rulesets: `origen='CLIENT_RUN'`, `actiu=True`, `version_number=1`, `codi_sistema=''`,
`customer=LOS`, `pendents_vincular=[]`. Només **1** té `is_system_default=True` (*LOS Baby Knit — Tops*).

### 3.2 Fitxa per contenidor

| ruleset (id) | size_system | garment_group | constr. | fit | targets | àmbit | regles | profiles |
|---|---|---|---|---|---|---|---|---|
| LOS Baby Knit — Tops (37) ★ | BABY_LOS_01 | — | KNIT | REGULAR | TODDLER_BOY, TODDLER_GIRL | ITEM: baby_top, baby_bodysuit | 16 | 1 |
| LOS Kids Boy Knit — Tops (38) | BOY_LOS_01 | TOPS | KNIT | REGULAR | BOY | *fallback grup* | 17 | 1 |
| LOS Kids Boy Woven — Bottoms (39) | BOY_LOS_01 | BOTTOMS | WOVEN | REGULAR | BOY | *fallback grup* | 25 | 1 |
| LOS Kids Girl — Dresses (40) | GIRL_LOS_01 | DRESSES | KNIT | REGULAR | GIRL | *fallback grup* | 18 | 1 |
| LOS Kids Girl Knit — Tops (41) | GIRL_LOS_01 | TOPS | KNIT | REGULAR | GIRL | *fallback grup* | 17 | 1 |
| LOS Man Knit — Tops (42) | MAN_LOS_01 | TOPS | KNIT | REGULAR | MAN | *fallback grup* | 34 | 1 |
| LOS Man Woven — Bottoms (43) | MAN_NUM_LOS_01 | BOTTOMS | WOVEN | REGULAR | MAN | *fallback grup* | 23 | 1 |
| LOS New Born Knit — Bottoms (44) | NEWBORN_LOS_01 | — | KNIT | REGULAR | BABY_BOY/GIRL/UNISEX | ITEM: baby_leggings, baby_bloomers | 20 | 1 |
| LOS New Born Knit — Onepieces (45) | NEWBORN_LOS_01 | — | KNIT | REGULAR | BABY_BOY/GIRL/UNISEX | ITEM: baby_sleepsuit, baby_sleepbag, booties | 38 | 1 |
| LOS New Born Knit — Tops (46) | NEWBORN_LOS_01 | — | KNIT | REGULAR | BABY_BOY/GIRL/UNISEX | ITEM: baby_top, baby_bodysuit | 37 | 1 |
| LOS Teen Boy Knit — Tops (47) | YOUTH_BOY_LOS_01 | TOPS | KNIT | REGULAR | TEEN_BOY | *fallback grup* | 18 | 1 |
| LOS Teen Boy Woven — Bottoms (48) | YOUTH_BOY_LOS_01 | BOTTOMS | WOVEN | REGULAR | TEEN_BOY | *fallback grup* | 19 | 1 |
| LOS Teen Boy Woven — Shirts (49) | YOUTH_BOY_LOS_01 | TOPS | WOVEN | REGULAR | TEEN_BOY | *fallback grup* | 22 | 1 |
| LOS Teen Girl — Bottoms (50) | YOUTH_GIRL_LOS_01 | BOTTOMS | WOVEN | REGULAR | TEEN_GIRL | *fallback grup* | 12 | 1 |
| LOS Teen Girl Knit — Tops (51) | YOUTH_GIRL_LOS_01 | TOPS | KNIT | REGULAR | TEEN_GIRL | *fallback grup* | 22 | 1 |
| LOS Teen Girl Stretch — Swimwear (52) | YOUTH_GIRL_LOS_01 | SWIMWEAR | STRETCH_KNIT | REGULAR | TEEN_GIRL | *fallback grup* | 11 | 1 |
| LOS Woman Knit — Tops (53) | WOMAN_LOS_01 | TOPS | KNIT | REGULAR | WOMAN | *fallback grup* | 17 | 1 |
| LOS Woman Woven — Bottoms (54) | WOMAN_NUM_LOS_01 | BOTTOMS | WOVEN | REGULAR | WOMAN | *fallback grup* | 24 | 1 |
| **LOSAN IBERIA SA · Newborn · LOS Baby 3-36M (55)** | BABY_LOS_01 | NEWBORN | KNIT | REGULAR | TODDLER_GIRL | *fallback grup* | **12** | **0** |

★ = `is_system_default=True`. **Cap ruleset porta `garment_type_item` d'identitat** (tots a `None`);
els 4 que tenen àmbit el porten via `scope_nodes` de tipus ITEM. Els altres 15 cauen al **fallback
per `garment_group`**. `fit_type=REGULAR` a tots 19 — **no hi ha cap altre fit al tenant**.

### 3.3 Lògiques per contenidor

| ruleset | LINEAR | FIXED | amb break | LINEAR pures |
|---|---|---|---|---|
| LOS Baby Knit — Tops | 13 | 3 | 0 | 13 |
| LOS Kids Boy Knit — Tops | 17 | 0 | **17** | 0 |
| LOS Kids Boy Woven — Bottoms | 25 | 0 | **25** | 0 |
| LOS Kids Girl — Dresses | 18 | 0 | **18** | 0 |
| LOS Kids Girl Knit — Tops | 17 | 0 | **17** | 0 |
| LOS Man Knit — Tops | 21 | 13 | 0 | 21 |
| LOS Man Woven — Bottoms | 18 | 5 | 0 | 18 |
| LOS New Born Knit — Bottoms | 14 | 6 | 0 | 14 |
| LOS New Born Knit — Onepieces | 31 | 7 | 0 | 31 |
| LOS New Born Knit — Tops | 29 | 8 | 0 | 29 |
| LOS Teen Boy Knit — Tops | 14 | 4 | 0 | 14 |
| LOS Teen Boy Woven — Bottoms | 14 | 5 | 0 | 14 |
| LOS Teen Boy Woven — Shirts | 14 | 8 | 0 | 14 |
| LOS Teen Girl — Bottoms | 12 | 0 | **12** | 0 |
| LOS Teen Girl Knit — Tops | 22 | 0 | **22** | 0 |
| LOS Teen Girl Stretch — Swimwear | 11 | 0 | 0 | 11 |
| LOS Woman Knit — Tops | 15 | 2 | 0 | 15 |
| LOS Woman Woven — Bottoms | 18 | 6 | 0 | 18 |
| LOSAN IBERIA SA · Newborn · LOS Baby 3-36M | 9 | 3 | 0 | 9 |
| **TOTAL** | **332** | **70** | **111** | **221** |

**Cap regla `STEP`, `ZERO` ni `EXCEPTION` a tot el tenant**: només LINEAR i FIXED.
El break (`talla_break_label` informat) viu **només a 6 contenidors**, tots de nen/nena/teen
(Kids Boy ×2, Kids Girl ×2, Teen Girl ×2) — i quan hi és, hi és al **100%** de les regles d'aquell
contenidor. Els adults i els nadons no en tenen cap.

El bolcat regla a regla (pom + actiu + global + lògica + increment/base/break + talla_base +
break_label) és a l'**Annex B**.

### 3.4 Invariants — tots nets

| invariant | esperat | real |
|---|---|---|
| regles a POM `actiu=False` | 0 | **0** ✔ |
| regles amb POM sense `pom_global` | — | **0** ✔ |
| regles amb `talla_base` fora del `size_system` del seu ruleset | 0 | **0** ✔ |
| regles `actiu=False` | — | 0 |
| rulesets esquelet (0 regles) | — | 0 |
| rulesets sense `size_system` / sense `targets` | — | 0 / 0 |

### 3.5 SizingProfile — 18, cap sense ruleset

Tots amb `customer=LOS`, `version=1`, **`is_default=False`** (cap perfil marcat com a suggerit del
sistema), `fit_type=REGULAR`.

| target | família | constr. | size_system | ruleset |
|---|---|---|---|---|
| WOMAN | JERSEY_TOPS | KNIT | WOMAN_LOS_01 | LOS Woman Knit — Tops |
| WOMAN | TAILORED_PANTS | WOVEN | WOMAN_NUM_LOS_01 | LOS Woman Woven — Bottoms |
| MAN | JERSEY_TOPS | KNIT | MAN_LOS_01 | LOS Man Knit — Tops |
| MAN | TAILORED_PANTS | WOVEN | MAN_NUM_LOS_01 | LOS Man Woven — Bottoms |
| **BABY_GIRL** | **NEWBORN** | **KNIT** | **NEWBORN_LOS_01** | **LOS New Born Knit — Tops** |
| **BABY_GIRL** | **NEWBORN** | **KNIT** | **NEWBORN_LOS_01** | **LOS New Born Knit — Onepieces** |
| **BABY_GIRL** | **NEWBORN** | **KNIT** | **NEWBORN_LOS_01** | **LOS New Born Knit — Bottoms** |
| TODDLER_GIRL | NEWBORN | KNIT | BABY_LOS_01 | LOS Baby Knit — Tops |
| GIRL | DRESSES | KNIT | GIRL_LOS_01 | LOS Kids Girl — Dresses |
| GIRL | JERSEY_TOPS | KNIT | GIRL_LOS_01 | LOS Kids Girl Knit — Tops |
| BOY | JERSEY_TOPS | KNIT | BOY_LOS_01 | LOS Kids Boy Knit — Tops |
| BOY | TAILORED_PANTS | WOVEN | BOY_LOS_01 | LOS Kids Boy Woven — Bottoms |
| TEEN_GIRL | JERSEY_TOPS | KNIT | YOUTH_GIRL_LOS_01 | LOS Teen Girl Knit — Tops |
| TEEN_GIRL | SWIMWEAR | STRETCH_KNIT | YOUTH_GIRL_LOS_01 | LOS Teen Girl Stretch — Swimwear |
| TEEN_GIRL | TAILORED_PANTS | WOVEN | YOUTH_GIRL_LOS_01 | LOS Teen Girl — Bottoms |
| TEEN_BOY | BUTTONED_TOPS | WOVEN | YOUTH_BOY_LOS_01 | LOS Teen Boy Woven — Shirts |
| TEEN_BOY | JERSEY_TOPS | KNIT | YOUTH_BOY_LOS_01 | LOS Teen Boy Knit — Tops |
| TEEN_BOY | TAILORED_PANTS | WOVEN | YOUTH_BOY_LOS_01 | LOS Teen Boy Woven — Bottoms |

- **profiles sense ruleset: 0.**
- **Rulesets SENSE cap profile que els exposi: 1** — `LOSAN IBERIA SA · Newborn · LOS Baby 3-36M`
  (12 regles). És l'única graduació del tenant **invisible des dels eixos del wizard**.
- **Les 3 files en negreta comparteixen els QUATRE eixos** (BABY_GIRL · NEWBORN · KNIT · REGULAR) i
  el mateix `size_system`, i apunten a **tres rulesets diferents**. Això és intencional però només
  funciona gràcies a l'àmbit per ITEM (§3.6 i §6.2).
- Cobertura per target: **no hi ha cap perfil per a `BABY_BOY` ni `BABY_UNISEX`**, tot i que els tres
  rulesets New Born sí que declaren aquests targets.

### 3.6 CAS NEWBORN — com es desambiguen

Al **grup `NEWBORN`** (1 família, 9 items) hi conviuen **quatre** contenidors, no tres, en dos
sistemes de talla diferents:

| contenidor | size_system | targets | desambiguació | regles |
|---|---|---|---|---|
| LOS New Born Knit — **Tops** | NEWBORN_LOS_01 | BABY_BOY/GIRL/UNISEX | **scope ITEM**: `baby_top`, `baby_bodysuit` | 37 |
| LOS New Born Knit — **Onepieces** | NEWBORN_LOS_01 | BABY_BOY/GIRL/UNISEX | **scope ITEM**: `baby_sleepsuit`, `baby_sleepbag`, `booties` | 38 |
| LOS New Born Knit — **Bottoms** | NEWBORN_LOS_01 | BABY_BOY/GIRL/UNISEX | **scope ITEM**: `baby_leggings`, `baby_bloomers` | 20 |
| LOS **Baby** Knit — Tops | BABY_LOS_01 | TODDLER_BOY/GIRL | **scope ITEM**: `baby_top`, `baby_bodysuit` | 16 |
| *(residual)* LOSAN IBERIA SA · Newborn · LOS Baby 3-36M | BABY_LOS_01 | TODDLER_GIRL | **cap scope** → fallback `garment_group=NEWBORN` | 12 |

**La desambiguació real és per `scope_nodes` de tipus ITEM**, i funciona: els tres contenidors
New Born reparteixen 7 dels 9 items del grup sense solapament. Els items `baby_top`/`baby_bodysuit`
apareixen a **dos** contenidors (New Born Tops i Baby Knit Tops), però aquests es distingeixen pel
`size_system` + `targets` (nadó vs. 3-36 mesos), no per l'àmbit.

**El cinquè és el problema**: el residual no té scope, cau al fallback per grup i per tant "aplica" a
**tots 9 els items** del grup NEWBORN — inclosos els que ja tenen amo. Ara mateix això no fa mal
perquè cap `SizingProfile` l'exposa (no arriba al wizard), però **2 items del seu abast tenen
intersecció buida amb les seves regles** (§6.1) i té **1 model** enganxat.

Items del grup NEWBORN **sense cap contenidor amb àmbit**: `baby_dress`, `baby_swimwear`
(no surten a cap `scope_node`; només els cobreix el residual per fallback).

---

## 4. DICCIONARI / POMs (schema `los`)

### 4.1 Customer self

`Customer.objects.filter(is_self=True)` → **una sola fila a tot el schema**:

| pk | codi | nom | is_self | active | codi_global | tipologia del tenant |
|---|---|---|---|---|---|---|
| 1 | `LOS` | LOSAN IBERIA SA | **True** | True | `LOS` | **marca** (Client id=5) |

No hi ha cap altre `Customer` al schema `los`.

### 4.2 CustomerPOMAlias del self — **196 exactes** ✔

`CustomerPOMAlias.objects.filter(customer=<self>).count()` → **196**, i són **el 100% dels àlies del
schema** (196 totals). Tots amb `origen='DICCIONARI'` i **`pendent_revisio=False`**.

El bolcat complet `client_code → POMMaster.codi_client · pom_global.codi · actiu · descripció` és a
l'**Annex C** (196 files).

### 4.3 POMMaster

| xifra | valor |
|---|---|
| TOTAL | **246** |
| actius / inactius | **246 / 0** |
| amb `pom_global` | **245** · sense: **1** |
| LOS-local (`pom_global.codi` = `LOSPOM-*`) | **149** |
| `pendent_revisio=True` | **139** (56%) |
| sense cap àlies del self | **58** |
| amb `nom_client` buit | 0 |

Per `origen_import`: `diccionari:LOS:2026-07-18` 105 · *(buit)* 96 · `LOS diccionari 4B-bis` 20 ·
`SS26 TROUSERS TWILL (14-26-SS-0002)` 10 · `LOS màster delta v1` 5 · `diccionari:BRW:2026-07-13` 3 ·
3 UUIDs d'importació (2+2+2) · `Olivia Dress (REPRIS-26-SS-0001)` 1.

**Duplicats de `codi_client` — 2 parells** (`values('codi_client').annotate(n=Count('id')).filter(n__gt=1)`):

| codi_client | pk | pom_global | nom_client | àlies | maps | regles |
|---|---|---|---|---|---|---|
| **`J1`** | 589 | LOSPOM-507 | SHOULDER DROP LOCATION | 1 | 0 | 0 |
| | 733 | LOSPOM-460 | Sleeve opening relaxed | 1 | 0 | 0 |
| **`S`** | 655 | LOSPOM-581 | COLLAR HEIGHT ON TOP | 1 | 0 | 0 |
| | 734 | LOSPOM-457 | Front armhole along seam | 2 | 1 | 1 |

Són homònims **reals** (mesures diferents amb el mateix codi curt), no duplicats per error: cada un
té el seu `pom_global` propi i àlies propis. `codi_client` **no és únic** al model, i aquí es veu.

**Els 58 POMMaster sense àlies del self**: 55 amb `origen_import` buit, 2 de `LOS diccionari 4B-bis`,
1 d'un UUID d'import. **Tots 58 tenen `GarmentPOMMap` (>0) i cap té regles de grading** — és a dir,
són POMs del catàleg de maps que el diccionari LOS no anomena.

**L'únic POMMaster sense `pom_global`**: pk=497, `codi_client='AW'`, *ARTWORK POSITION*, actiu,
`origen_import='28fb6e93-…'`, **0 àlies**, 1 map, 0 regles.

### 4.4 Homònims i POMs concrets

Cerca feta **per `codi_client` i per `client_code` d'àlies** (no per pk):

| buscat | resultat al schema `los` |
|---|---|
| `U1` | **existeix** com a POMMaster `U1` (pk=707) → `LOSPOM-513` *JETTING WIDTH*, actiu, 6 maps, 4 regles. Hi apunten **dos àlies**: `U1` i `U.1`. Cap rastre dels pks 513/440 (eren de `fhort`). |
| `A.2` | **no existeix** cap POMMaster ni àlies amb aquest codi. L'àlies `A2` → `AC BK` (`POM-008`, *Across back*), 28 maps, 12 regles. **No hi ha orfe.** |
| `T.5` | **no existeix**. L'àlies `T5` → `HM L` (`POM-154`, *Half moon length*), 3 maps, 2 regles. |
| `A.1` | no existeix; `A1` → `AC FR` (`POM-007`, *Across front*), 27 maps, 12 regles. |
| `L.4` | no existeix; `L4` → `NK DR FR` (`POM-031`, *Neck drop front*), 34 maps, 12 regles. |
| `L.5` | no existeix; `L5` → `NK DR BK` (`POM-032`, *Neck drop back*), 31 maps, 12 regles. |
| **EARS** | **cap POMMaster, cap àlies i cap descripció** conté "ear" a tot el schema `los`. |

Els "prims" A.1/L.4/L.5 i el T.5 **no viuen en aquest schema amb notació de punt**: el diccionari LOS
els té amb notació sense punt (`A1`, `L4`, `L5`, `T5`) i tots resolen a POMs globals canònics
(`POM-*`), amb maps i regles. La notació amb punt sí que existeix per a **altres** codis
(`G.3`, `H.12`, `O.8`, `E.9`, `S.42`, `C.13`…), o sigui que la barreja de notacions és real.

#### G.3 i H.12 — estat (context futurs GS / H11S)

| | `G.3` | `H.12` |
|---|---|---|
| POMMaster | pk=565 | pk=572 |
| `pom_global` | `LOSPOM-680` | `LOSPOM-681` |
| nom | SLEEVE SHORT LENGTH | SLEEVE SHORT OPENING |
| actiu | **True** | **True** |
| àlies que hi apunten | `G.3` | `H.12` **i** `H12` |
| `GarmentPOMMap` | **0** | **0** |
| GradingRule | **2** | **2** |

**Tots dos existeixen, actius, amb 2 regles de grading cadascun i CAP map de peça.** Són mesures
graduades que no estan assignades a cap item del catàleg. Els codis `GS`, `G3` i `H11S` **no
existeixen** (ni com a POMMaster ni com a àlies) — la porta per al diccionari v3 està lliure.

**Aquest patró no és exclusiu seu**: hi ha **15 POMMaster amb regles però 0 maps**:
`A`, `A3`, `C3`, `E.9`, `G.3`, `H.12`, `H8`, `H9`, `N4`, `O11`, `O12`, `O14`, `O.8`, `O9`, `S.42`.

---

## 5. DIVERGÈNCIA DE DICCIONARI `los` ↔ `fhort`

### 5.0 Context imprescindible abans de llegir cap diff

Al schema `fhort`, el `Customer` LOS és **pk=6, `codi='LOS'`, `is_self=False`**, amb **183 àlies** ✔
(coincideix amb l'esperat). Però:

| | `los` | `fhort` |
|---|---|---|
| POMMaster totals | 246 | 401 |
| amb `pom_global` | 245 (99,6%) | **162 (40%)** |
| POMMaster referenciats pels àlies de LOS | 196 → tots amb global | 181 → **només 27 amb global** |

**Conseqüència metodològica:** comparar per `pom_global.codi` als dos costats dona **147 "divergents"
de 171 comuns**, però això és un **artefacte**: al costat `fhort` el camp és `None` en 154 dels 171
casos. La comparació semànticament vàlida és **per descripció normalitzada** (upper, sense
puntuació), i és la que reporto com a bona.

### 5.1 DIFF per `client_code`

`set(los) − set(fhort)` i viceversa sobre `client_code`:

| | recompte |
|---|---|
| àlies a `los` (self) | **196** |
| àlies a `fhort` (Customer LOS) | **183** |
| comuns | **171** |
| **només a `los`** | **25** |
| **només a `fhort`** | **12** |

`196 = 171 + 25` i `183 = 171 + 12`. L'estimació de "~13 extres de los" es queda curta: **són 25**.

**Els 25 només a `los`** (tots amb `pom_global` LOSPOM-* propi):
`B4` (BACK CHEST WIDTH) · `C.13` (BUTTONHOLE LOCATION) · `CB` (FRONT CUT LOCATION) ·
`E.1` (FRONT BOTTOM WIDTH) · `E.2` (BACK BOTTOM WIDTH) · `E.9` (BOTTOM MOTIVE LOCATION) ·
`G.3` (SLEEVE SHORT LENGTH) · `H.12` + `H12` (SLEEVE SHORT OPENING — **dos àlies al mateix POM**) ·
`M.1` (FRONT LENGTH CENTER) · `O.8` (CHEST POCKET OPENING) · `R.1` (STRAP LENGTH) ·
`R.3` (STRAP LOCATION) · `S.19` (FOOT LENGTH) · `S.20` (FOOT WIDTH) · `S.35` (COLLAR PIECE WIDTH) ·
`S.39` (FOOT WIDTH LOCATION) · `S.40` (FRONT FOOT LENGTH) · `S.42` (FRONT VENT WIDTH) ·
`S.R6` (LOOP LENGTH) · `S.R7` (LOOP WIDTH) · `U.1` (JETTING WIDTH — **segon àlies de `U1`**) ·
`V.2` (→ POM `S.35`, COLLAR PIECE WIDTH) · `V.9` (ELASTIC LOCATION) · `Z` (FRILL LENGTH).

> Observació: **21 dels 25 porten notació amb punt**. Molts són el mateix concepte que a `fhort`
> viu sense punt: `S.R6`/`SR6`, `S.R7`/`SR7`, `E.9`/`E9`, `C.13`/`C13`. **No són mesures noves: són
> la mateixa mesura escrita d'una altra manera** — i per això apareixen als DOS costats de la diff.

**Els 12 només a `fhort`**: `B9` (CHEST MOTIVE LOCATION) · `C13` · `E9` · `ES` (MOTIVE LOCATION) ·
`SR11` (BOW LOCATION) · `SR6` · `SR7` · `SR8` (STRAP LOCATION) · `Y11` (CONTOUR HAT INSIDE ROUND) ·
`Y12` (HAT HEIGHT) · `Y36` (BAG WIDTH) · `Y37` (BAG LENGTH).

> `SR6` i `SR7` de `fhort` apunten als **mateixos POMMaster** que `S.R6`/`S.R7` de `los`
> (`LOOP LENGTH`/`LOOP WIDTH`): pura divergència de notació. Els `Y*` (barret, bossa) són el
> vocabulari d'accessoris que `los` encara no ha rebut — coherent amb els 3 items d'ACCESSORIES
> sense cap map (§7 Z3).

### 5.2 Mateix `client_code`, POM diferent

> **⚠️ CORRECCIÓ (2026-07-24, durant el dry-run del delta v3).** La primera redacció d'aquesta secció
> deia «cap divergència semàntica real, 0 de 171». **Era massa forta i s'ha de llegir amb el matís de
> sota.** La comparació es va fer sobre la **descripció de l'àlies** (`description_en`), que és
> idèntica als dos schemas perquè ve del mateix diccionari d'origen — però **no** sobre el POM que
> l'àlies resol. Comparant el POM, sí que hi ha divergències, i n'hi ha de materials.

Els 171 `client_code` comuns, comparats a **tres nivells diferents**:

| nivell de comparació | divergents | lectura |
|---|---|---|
| **descripció de l'àlies** (`description_en`) | **1 / 171** | els dos diccionaris diuen el mateix |
| **nom del POMMaster que l'àlies resol** | **33 / 171** | inclou sinònims (*Across front* ↔ *FRONT WIDTH*) i errors reals |
| **`pom_global`** (només on `fhort` en té) | **4 / 171** | divergència dura, confirmada |

**Els 4 de divergència dura** (mateix codi, mesura realment diferent, tots dos amb `pom_global`):

| client_code | a `los` | a `fhort` |
|---|---|---|
| `D` | `HI PA` · POM-040 · Hip width (**pants**) | `HI` · POM-004 · Hip width (**top**) |
| `GA` | `GA` · LOSPOM-550 · **SLEEVE** INSEAM LENGTH | `INS` · POM-044 · Inseam length (**cama**) |
| `J1` | `J1` · LOSPOM-507 · SHOULDER DROP **LOCATION** | `SH DR` · POM-014 · Shoulder drop (**valor**) |
| `S28` | `S28` · LOSPOM-562 · FRONT YOKE LENGTH | `YK L` · POM-029 · Front yoke length (center) |

**I un defecte que el cens no havia vist: àlies mal cablejats.** Hi ha POMMaster amb 2+ àlies que
diuen coses **contradictòries entre elles**, o sigui mesures diferents col·lapsades en un sol POM:

| schema | POMMaster | maps | regles | àlies que hi pengen |
|---|---|---|---|---|
| `los` | `V` — *RUFFLE HEIGHT* | 1 | 1 | `V`=STITCHING WIDTH · `V3`=STITCHING LOCATION · `V18`=BUTTON LOCATION |
| `los` | `S` — *Front armhole along seam* | 1 | 1 | `S22`=BELT HEIGHT · `S44`=FRONT MOTIVE LOCATION |
| `los` | `BIC` — *Sleeve width at bicep* | **34** | **10** | `H`=SLEEVE MUSCLE ✔ · `H19`=SLEEVE MOTIVE LOCATION ✘ |
| `los` | `ELB` — *Sleeve width at elbow* | **31** | 0 | `H4`=ELBOW WIDTH ✔ · `SR9`=BOW WIDTH ✘ |
| `los` | `U1` — *JETTING WIDTH* | 6 | 4 | `U1`=JETTING WIDTH · `U.1`=(buit) — benigne |
| `fhort` | `H` — *SLEEVE MUSCLE (1/2)* | 0 | 3 | `H`=SLEEVE MUSCLE ✔ · `H7`=ARMHOLE POINT LOCATION ✘ |
| `fhort` | `SH DR` — *Shoulder drop* | **31** | **23** | `K1`=SHOULDER DROP ✔ · `J1`=SHOULDER DROP LOCATION ✘ |

En aquests casos **una localització i una amplada comparteixen POM** — i per tant comparteixen regla
de graduació. `BIC` (34 maps, 10 regles) i `ELB` (31 maps) són els que toquen més dades.

La divergència entre els dos diccionaris és, doncs, de **tres** menes, no de dues:
1. **cobertura**: `los` té 25 codis que `fhort` no té, `fhort` en té 12 que `los` no té;
2. **vinculació**: `fhort` no té `pom_global` en 155 dels 183 POMMaster dels seus àlies LOS;
3. **significat**: 4 divergències dures + 9 codis més on el POM de destí contradiu la descripció
   de l'àlies (`H7`, `H19`, `SR9`, `SR10`, `S22`, `S44`, `V`, `V3`, `V18`).

---

## 6. RELACIONS CREUADES

### 6.1 Intersecció regles × `GarmentPOMMap` per item de l'abast

Per a cada ruleset: `set(regles.pom_id) ∩ set(GarmentPOMMap.filter(item).pom_id)`, sobre els items
del seu abast (`scope_nodes` si en té; si no, fallback pel `garment_group`).

| ruleset | abast | items | **items amb ∩ BUIDA** |
|---|---|---|---|
| LOS Baby Knit — Tops | ITEM ×2 | 2 | 0 |
| LOS Kids Boy Knit — Tops | grup TOPS | 14 | 0 |
| LOS Kids Boy Woven — Bottoms | grup BOTTOMS | 10 | 0 |
| LOS Kids Girl — Dresses | grup DRESSES | 7 | 0 |
| LOS Kids Girl Knit — Tops | grup TOPS | 14 | 0 |
| LOS Man Knit — Tops | grup TOPS | 14 | 0 |
| LOS Man Woven — Bottoms | grup BOTTOMS | 10 | 0 |
| LOS New Born Knit — Bottoms | ITEM ×2 | 2 | 0 |
| **LOS New Born Knit — Onepieces** | ITEM ×3 | 3 | **1** (`booties`, 0 maps) |
| LOS New Born Knit — Tops | ITEM ×2 | 2 | 0 |
| LOS Teen Boy Knit — Tops | grup TOPS | 14 | 0 |
| LOS Teen Boy Woven — Bottoms | grup BOTTOMS | 10 | 0 |
| LOS Teen Boy Woven — Shirts | grup TOPS | 14 | 0 |
| **LOS Teen Girl — Bottoms** | grup BOTTOMS | 10 | **2** (`skirt_straight`, `skirt_volume` — 16 maps cadascun) |
| LOS Teen Girl Knit — Tops | grup TOPS | 14 | 0 |
| LOS Teen Girl Stretch — Swimwear | grup SWIMWEAR | 3 | 0 |
| LOS Woman Knit — Tops | grup TOPS | 14 | 0 |
| LOS Woman Woven — Bottoms | grup BOTTOMS | 10 | 0 |
| **LOSAN IBERIA SA · Newborn · LOS Baby 3-36M** | grup NEWBORN | 9 | **2** (`baby_bloomers` 12 maps, `booties` 0 maps) |

**La protecció per intersecció funciona a 16 dels 19 contenidors sense cap forat.** Els 3 casos amb
intersecció buida:

- `booties` (×2 contenidors): **té 0 `GarmentPOMMap`** — no és un problema de graduació sinó un item
  sense fitxa de mesures. Vegeu §7 Z3.
- `skirt_straight` / `skirt_volume` amb *LOS Teen Girl — Bottoms*: tenen 16 maps cadascun i **cap**
  coincideix amb les 12 regles del contenidor. Les faldilles queden dins l'abast (fallback pel grup
  BOTTOMS) però la graduació de pantalons no les toca en cap POM. **Cap graduació errònia s'hi pot
  aplicar** — la intersecció fa de llei, tal com estava previst — però el contenidor apareix com a
  candidat al picker per a un item que no pot graduar.
- `baby_bloomers` amb el contenidor residual: mateix patró, agreujat perquè aquell contenidor no
  hauria de tenir aquest abast (§3.6).

El detall item a item de tots 19 contenidors és a l'**Annex D**.

### 6.2 PROVA DEL COTÓ — matching estricte del wizard

Rèplica en Python de `frontend/src/components/grading/gradingAxes.js:180` (`matchingRuleSetsStrict`):
`actiu` ∧ `target ∈ targets` ∧ `construction ==` ∧ `fit ==` ∧ `scopeApplies(strict)` ∧ `size_system ==`.
El `size_system` surt del `SizingProfile` que casa amb els eixos, com fa el wizard.

| combo | profiles que casen | size_system | **rulesets retornats** | |
|---|---|---|---|---|
| Teen Girl + KNIT + REGULAR + Tops · `t_shirt` | 1 | YOUTH_GIRL_LOS_01 | **1** — LOS Teen Girl Knit — Tops (22 regles) | ✔ |
| Woman + WOVEN + REGULAR + Bottoms · `trousers` | 1 | WOMAN_NUM_LOS_01 | **1** — LOS Woman Woven — Bottoms (24 regles) | ✔ |
| Baby Girl + KNIT + REGULAR + Newborn · `baby_top` | **3** | NEWBORN_LOS_01 | **1** — LOS New Born Knit — Tops (37 regles) | ✔ |
| Baby Girl + KNIT + REGULAR + Newborn · `baby_leggings` | **3** | NEWBORN_LOS_01 | **1** — LOS New Born Knit — Bottoms (20 regles) | ✔ |
| Baby Girl + KNIT + REGULAR + Newborn · `baby_sleepsuit` | **3** | NEWBORN_LOS_01 | **1** — LOS New Born Knit — Onepieces (38 regles) | ✔ |

**Els 5 combos retornen exactament 1 ruleset.** El cas Newborn és el que ho demostra millor: els
**tres** `SizingProfile` casen amb els mateixos quatre eixos (l'ambigüitat existeix a nivell de
perfil), però l'`scope_node` de tipus ITEM la resol i el wizard només ofereix la graduació correcta
per a cada item. **L'àmbit per ITEM és el que fa que el grup NEWBORN funcioni.**

### 6.3 MODELS — només agregat

`Model.objects.count()` = **961**

| | |
|---|---|
| amb `garment_type_item` | **961 / 961** (0 sense) |
| amb `size_system` | **961 / 961** (0 sense) |
| amb `grading_rule_set` | **580** · **SENSE: 381 (39,6%)** |

**Per `size_system`:**

| size_system | models |
|---|---|
| BABY_LOS_01 | 166 |
| GIRL_LOS_01 | 139 |
| WOMAN_LOS_01 | 136 |
| MAN_LOS_01 | 121 |
| YOUTH_GIRL_LOS_01 | 115 |
| BOY_LOS_01 | 104 |
| YOUTH_BOY_LOS_01 | 92 |
| NEWBORN_LOS_01 | 45 |
| MAN_NUM_LOS_01 | 24 |
| WOMAN_NUM_LOS_01 | 19 |
| **GIRL_LOS_03** | **0** |

**Per `grading_rule_set`:**

| ruleset | models |
|---|---|
| *(cap)* | **381** |
| LOS Baby Knit — Tops | 53 |
| LOS Woman Woven — Bottoms | 49 |
| LOS Man Knit — Tops | 48 |
| LOS Teen Girl — Bottoms | 45 |
| LOS Teen Boy Knit — Tops | 42 |
| LOS Kids Boy Knit — Tops | 41 |
| LOS Woman Knit — Tops | 40 |
| LOS Kids Boy Woven — Bottoms | 40 |
| LOS Teen Girl Knit — Tops | 40 |
| LOS Kids Girl Knit — Tops | 38 |
| LOS Man Woven — Bottoms | 35 |
| LOS Kids Girl — Dresses | 32 |
| LOS Teen Boy Woven — Bottoms | 30 |
| LOS New Born Knit — Onepieces | 24 |
| LOS Teen Girl Stretch — Swimwear | 13 |
| LOS New Born Knit — Tops | 5 |
| LOS Teen Boy Woven — Shirts | 4 |
| **LOSAN IBERIA SA · Newborn · LOS Baby 3-36M** | **1** |
| **LOS New Born Knit — Bottoms** | **0** |

**Per grup de peça** (via `garment_type_item`): TOPS 336 · BOTTOMS 248 · NEWBORN 179 · SWIMWEAR 99 ·
DRESSES 69 · OUTERWEAR 30. (0 a ACCESSORIES i UNDERWEAR.)

### 6.4 MATRIU item × size_system — sostre de GTI-món (LLEI GTI-MÓN, decisió D1)

`Model.objects.values('garment_type_item__code','size_system__codi','grading_rule_set__nom').annotate(n=Count('id'))`
sota `schema_context('los')`. Read-only.

**Només 21 dels 62 items tenen algun model** (41 items del catàleg no en tenen cap). Els 10
`size_system` amb models són tots menys `GIRL_LOS_03` (l'orfe de §7 Z2).

#### Taula creuada (files = item, columnes = size_system, cel·la = models)

⭐ = l'item serveix **2+ sistemes de talla** → és un **GTI-món a fer néixer**.

| item | família | grup | BABY | BOY | GIRL | MAN | MAN_NUM | NEWBORN | WOMAN | WOMAN_NUM | YOUTH_BOY | YOUTH_GIRL | TOTAL | #sys |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `skirt_straight` ⭐ | SKIRTS | BOTTOMS | 2 | · | 1 | · | · | · | 5 | 2 | · | 3 | **13** | 5 |
| `jeans` ⭐ | TAILORED_PANTS | BOTTOMS | · | 11 | 15 | 1 | 11 | · | · | 8 | 7 | 18 | **71** | 7 |
| `shorts` ⭐ | TAILORED_PANTS | BOTTOMS | · | 23 | 19 | 7 | 7 | · | 13 | 5 | 15 | 15 | **104** | 8 |
| `trousers` ⭐ | TAILORED_PANTS | BOTTOMS | · | 6 | 12 | 3 | 6 | · | 12 | 4 | 8 | 9 | **60** | 8 |
| `dress_simple` ⭐ | DRESSES | DRESSES | · | · | 32 | · | · | · | 26 | · | · | 11 | **69** | 3 |
| `baby_bloomers` | NEWBORN | NEWBORN | 32 | · | · | · | · | · | · | · | · | · | **32** | 1 |
| `baby_bodysuit` | NEWBORN | NEWBORN | · | · | · | · | · | 5 | · | · | · | · | **5** | 1 |
| `baby_dress` ⭐ | NEWBORN | NEWBORN | 25 | · | · | · | · | 24 | · | · | · | · | **49** | 2 |
| `baby_leggings` | NEWBORN | NEWBORN | 19 | · | · | · | · | · | · | · | · | · | **19** | 1 |
| `baby_sleepsuit` | NEWBORN | NEWBORN | · | · | · | · | · | 11 | · | · | · | · | **11** | 1 |
| `baby_swimwear` | NEWBORN | NEWBORN | 20 | · | · | · | · | · | · | · | · | · | **20** | 1 |
| `baby_top` | NEWBORN | NEWBORN | 43 | · | · | · | · | · | · | · | · | · | **43** | 1 |
| `casual_jacket` ⭐ | STRUCTURED_JACKETS | OUTERWEAR | 8 | 5 | 5 | 4 | · | · | 4 | · | 2 | 2 | **30** | 7 |
| `swim_shorts` ⭐ | SWIMWEAR | SWIMWEAR | · | 12 | · | 25 | · | · | · | · | 14 | · | **51** | 3 |
| `swimsuit` ⭐ | SWIMWEAR | SWIMWEAR | · | · | 13 | · | · | · | 22 | · | · | 13 | **48** | 3 |
| `blouse` ⭐ | BUTTONED_TOPS | TOPS | 2 | · | 4 | · | · | · | 14 | · | · | 4 | **24** | 4 |
| `shirt_woven` ⭐ | BUTTONED_TOPS | TOPS | 5 | 6 | · | 33 | · | · | · | · | 4 | · | **48** | 4 |
| `polo` ⭐ | JERSEY_TOPS | TOPS | 2 | 2 | · | 13 | · | · | 1 | · | 4 | 1 | **23** | 6 |
| `t_shirt` ⭐ | JERSEY_TOPS | TOPS | · | 34 | 31 | 34 | · | · | 33 | · | 33 | 33 | **198** | 6 |
| `sweater` ⭐ | KNIT_SWEATERS | TOPS | 4 | 1 | 3 | · | · | 4 | 6 | · | · | 3 | **21** | 6 |
| `hoodie` ⭐ | SWEATSHIRTS_MIDLAYERS | TOPS | 4 | 4 | 4 | 1 | · | 1 | · | · | 5 | 3 | **22** | 7 |
| **TOTAL** | | | 166 | 104 | 139 | 121 | 24 | 45 | 136 | 19 | 92 | 115 | **961** | |


#### Els 15 GTI-món (⭐) — items que serveixen 2+ sistemes

| item | família | #systems | models | repartiment |
|---|---|---|---|---|
| `shorts` | TAILORED_PANTS | **8** | 104 | BOY 23 · GIRL 19 · YOUTH_BOY 15 · YOUTH_GIRL 15 · WOMAN 13 · MAN 7 · MAN_NUM 7 · WOMAN_NUM 5 |
| `trousers` | TAILORED_PANTS | **8** | 60 | GIRL 12 · WOMAN 12 · YOUTH_GIRL 9 · YOUTH_BOY 8 · BOY 6 · MAN_NUM 6 · WOMAN_NUM 4 · MAN 3 |
| `jeans` | TAILORED_PANTS | 7 | 71 | YOUTH_GIRL 18 · GIRL 15 · BOY 11 · MAN_NUM 11 · WOMAN_NUM 8 · YOUTH_BOY 7 · MAN 1 |
| `casual_jacket` | STRUCTURED_JACKETS | 7 | 30 | BABY 8 · BOY 5 · GIRL 5 · MAN 4 · WOMAN 4 · YOUTH_BOY 2 · YOUTH_GIRL 2 |
| `hoodie` | SWEATSHIRTS_MIDLAYERS | 7 | 22 | YOUTH_BOY 5 · BABY 4 · BOY 4 · GIRL 4 · YOUTH_GIRL 3 · MAN 1 · NEWBORN 1 |
| `t_shirt` | JERSEY_TOPS | 6 | **198** | BOY 34 · MAN 34 · WOMAN 33 · YOUTH_BOY 33 · YOUTH_GIRL 33 · GIRL 31 |
| `polo` | JERSEY_TOPS | 6 | 23 | MAN 13 · YOUTH_BOY 4 · BABY 2 · BOY 2 · WOMAN 1 · YOUTH_GIRL 1 |
| `sweater` | KNIT_SWEATERS | 6 | 21 | WOMAN 6 · BABY 4 · NEWBORN 4 · GIRL 3 · YOUTH_GIRL 3 · BOY 1 |
| `skirt_straight` | SKIRTS | 5 | 13 | WOMAN 5 · YOUTH_GIRL 3 · BABY 2 · WOMAN_NUM 2 · GIRL 1 |
| `blouse` | BUTTONED_TOPS | 4 | 24 | WOMAN 14 · GIRL 4 · YOUTH_GIRL 4 · BABY 2 |
| `shirt_woven` | BUTTONED_TOPS | 4 | 48 | MAN 33 · BOY 6 · BABY 5 · YOUTH_BOY 4 |
| `dress_simple` | DRESSES | 3 | 69 | GIRL 32 · WOMAN 26 · YOUTH_GIRL 11 |
| `swim_shorts` | SWIMWEAR | 3 | 51 | MAN 25 · YOUTH_BOY 14 · BOY 12 |
| `swimsuit` | SWIMWEAR | 3 | 48 | WOMAN 22 · GIRL 13 · YOUTH_GIRL 13 |
| `baby_dress` | NEWBORN | 2 | 49 | BABY 25 · NEWBORN 24 |

Els 6 items **mono-sistema** (no són GTI-món) són tots del grup NEWBORN: `baby_top` (43),
`baby_bloomers` (32), `baby_swimwear` (20), `baby_leggings` (19), `baby_sleepsuit` (11),
`baby_bodysuit` (5). Tots viuen en un únic sistema (`BABY_LOS_01` o `NEWBORN_LOS_01`).

> **Lectura:** els items de roba adulta/infantil "normal" (pantalons, samarretes, vestits, banyadors)
> són transversals per naturalesa — el mateix item serveix de nadó a home. Els items específics de
> nadó, en canvi, ja neixen acotats a un sol sistema. El sostre de GTI-món viu al primer grup.

#### Parells (item × system) amb models: **85**

**Aquest 85 és el sostre teòric de GTI-món de LOSAN** (nombre de combinacions item×sistema que avui
tenen almenys un model, i que per tant caldria materialitzar com a GTI-món distints).

Repartiment dels 85 parells segons el grading que porten els seus models:

| categoria | parells | models |
|---|---|---|
| **A** — 1 sol ruleset, tots els models graduats | **53** | 579 |
| **B** — mixt (part dels models sense grading) | **1** | 25 |
| **C** — 100% sense `grading_rule_set` | **31** | 357 |
| **D** — **2+ rulesets no nuls al mateix parell (ANOMALIA)** | **0** | — |

#### Anomalies: cap

**Cap parell (item × system) té els seus models repartits entre dos `grading_rule_set` diferents.**
Allà on hi ha graduació, és una i només una per combinació item×sistema — la premissa de la decisió
D1 es compleix a la BD, sense excepcions.

L'únic parell **mixt** és `baby_dress × BABY_LOS_01`: 24 models sense graduació i **1 sol model**
enganxat a `LOSAN IBERIA SA · Newborn · LOS Baby 3-36M` — el contenidor residual de §7 Z7. És
l'únic lloc de tot el tenant on aquell ruleset toca dades reals.

Els 31 parells de la categoria C (357 models, el 37% del catàleg) són combinacions item×sistema
**sense cap graduació assignada**. Els més grossos: `shirt_woven × MAN` (33), `baby_bloomers × BABY`
(32), `dress_simple × WOMAN` (26), `swim_shorts × MAN` (25), `swimsuit × WOMAN` (22),
`baby_swimwear × BABY` (20), `shorts × GIRL` (19), `baby_leggings × BABY` (19). El llistat complet
dels 85 parells amb el(s) seu(s) ruleset(s) és a l'**Annex F**.

---

## 7. ZOO I SORPRESES

Res d'això s'ha tocat. Ordenat pel que em sembla més accionable.

**Z1 · Els 62 `GarmentTypeItem` tenen `name` BUIT.**
`GarmentTypeItem.objects.filter(name='').count()` → **62 / 62**. La UI només té el `code`
(`baby_sleepsuit`, `top_sleeveless`…) per anomenar-los. És el camp de nom humà de l'item i no
l'omple ningú.

**Z2 · `SizeSystem GIRL_LOS_03` és un bessó exacte i orfe de `GIRL_LOS_01`.**
Mateixes 9 etiquetes i mateix target `GIRL`; **0 rulesets, 0 profiles, 0 models**. El seu nom
(`Nena AGE_YEARS — LOSAN IBERIA SA Run 03`) delata un run d'import antic. És el residu que fa que
n'hi hagi 11 en comptes de 10.

**Z3 · 7 items sense cap `GarmentPOMMap`** (i 0 models):
`booties` (NEWBORN) · `briefs_man`, `briefs_woman`, `socks` (UNDERWEAR) · `bag`, `hat_cap`, `scarf`
(ACCESSORIES). Els 3 d'ACCESSORIES quadren amb els codis `Y*` (barret/bossa) que hi ha a `fhort` i
no a `los` (§5.1) — **el vocabulari d'accessoris encara no ha arribat a aquest tenant**.
`booties` és el que provoca les 2 interseccions buides de §6.1.

**Z4 · 4 `GarmentGroup` completament buits i actius**: `DRESSES-FULL`, `KNITWEAR`, `TOPS-KNIT`,
`TOPS-WOVEN`. 0 famílies, 0 items, 0 rulesets. Semblen d'una taxonomia anterior (`TOPS-KNIT`/
`TOPS-WOVEN` han quedat substituïts per `TOPS` + l'eix `construction`).

**Z5 · 41 models tenen `size_system` DIFERENT del `size_system` del seu propi `grading_rule_set`.**

| model.size_system | ruleset | ruleset.size_system | models |
|---|---|---|---|
| `WOMAN_LOS_01` (alpha XS-3XL) | LOS Woman Woven — Bottoms | `WOMAN_NUM_LOS_01` (36-52) | **30** |
| `MAN_LOS_01` (alpha S-6XL) | LOS Man Woven — Bottoms | `MAN_NUM_LOS_01` (38-58) | **11** |

És sempre el mateix patró: **peça de baix en talla alfabètica, però graduada amb un contenidor
numèric**. Les etiquetes de talla del model (`S`,`M`,`L`…) no existeixen al sistema del ruleset
(`38`,`40`,`42`…). No he mirat què fa el motor en aquest cas — ho deixo apuntat perquè és
exactament el tipus de desalineació que la `talla_base` no pot resoldre.

**Z6 · Els homònims `J1` i `S` de `POMMaster`** (§4.3): `codi_client` no és únic i hi ha dos parells
amb el mateix codi i mesures diferents. El de `S` és el més viu (el segon té 2 àlies, 1 map i 1 regla).

**Z7 · El contenidor residual `LOSAN IBERIA SA · Newborn · LOS Baby 3-36M`** (§3.1, §3.6, §6.1):
únic ruleset sense `SizingProfile`, únic amb nom del patró antic, únic amb un sol target del seu
grup, sense `scope_nodes`, amb 2 interseccions buides i **1 model** enganxat. Explica per si sol
tota la desviació 19≠18 i 402≠390.

**Z8 · `139 / 246` POMMaster amb `pendent_revisio=True`** (56%) i **238 / 1.748 `GarmentPOMMap`**
(13,6%). Els àlies del diccionari, en canvi, estan tots revisats (0 de 196 pendents).

**Z9 · Cobertura de targets incompleta**: hi ha `SizingProfile` per a `BABY_GIRL` però **cap per a
`BABY_BOY` ni `BABY_UNISEX`**, tot i que els tres rulesets New Born declaren aquests tres targets.
Un model de nadó nen no trobaria perfil per la via del wizard.

**Z10 · `fit_type=REGULAR` a 19/19 rulesets i 18/18 profiles**, i **`is_default=False` a tots els
perfils**. L'eix `fit` existeix a l'estructura però al tenant `los` és constant: avui no discrimina res.

---

## ANNEXOS (bolcats complets)

### Annex A — GarmentTypeItem (62)

```
  code                       name                           type                 grup       cx  act   base_size        ruleset                            maps  rev 
  hat_cap                                                   ACCESSORIES          ACCESSORIE 1   True  —                —                                  0     0   
  scarf                                                     ACCESSORIES          ACCESSORIE 1   True  —                —                                  0     0   
  bag                                                       ACCESSORIES          ACCESSORIE 2   True  —                —                                  0     0   
  leggings                                                  LEGGINGS_TIGHTS      BOTTOMS    1   True  —                —                                  26    0   
  culotte_cycling                                           LEGGINGS_TIGHTS      BOTTOMS    2   True  —                —                                  26    11  
  skirt_straight                                            SKIRTS               BOTTOMS    1   True  —                —                                  16    0   
  skirt_volume                                              SKIRTS               BOTTOMS    2   True  —                —                                  16    0   
  chino                                                     TAILORED_PANTS       BOTTOMS    1   True  —                —                                  23    11  
  jeans                                                     TAILORED_PANTS       BOTTOMS    1   True  —                —                                  44    8   
  trousers                                                  TAILORED_PANTS       BOTTOMS    1   True  —                —                                  52    0   
  shorts                                                    TAILORED_PANTS       BOTTOMS    2   True  —                —                                  32    8   
  tracksuit_pant                                            TAILORED_PANTS       BOTTOMS    2   True  —                —                                  38    8   
  workwear_pant                                             TAILORED_PANTS       BOTTOMS    2   True  —                —                                  23    11  
  jumpsuit                                                  ADULT_JUMPSUITS      DRESSES    1   True  —                —                                  46    0   
  dungarees                                                 ADULT_JUMPSUITS      DRESSES    2   True  —                —                                  46    0   
  playsuit                                                  ADULT_JUMPSUITS      DRESSES    2   True  —                —                                  46    0   
  dress_simple                                              DRESSES              DRESSES    1   True  —                —                                  40    0   
  dress_fancy                                               DRESSES              DRESSES    2   True  —                —                                  35    12  
  shirt_dress                                               DRESSES              DRESSES    2   True  —                —                                  33    12  
  dress_structured                                          DRESSES              DRESSES    3   True  —                —                                  35    12  
  baby_bodysuit                                             NEWBORN              NEWBORN    1   True  —                —                                  23    0   
  baby_dress                                                NEWBORN              NEWBORN    1   True  —                —                                  10    8   
  baby_leggings                                             NEWBORN              NEWBORN    1   True  —                —                                  29    0   
  baby_swimwear                                             NEWBORN              NEWBORN    1   True  —                —                                  9     4   
  baby_top                                                  NEWBORN              NEWBORN    1   True  —                —                                  25    7   
  booties                                                   NEWBORN              NEWBORN    1   True  —                —                                  0     0   
  baby_bloomers                                             NEWBORN              NEWBORN    2   True  —                —                                  12    0   
  baby_sleepbag                                             NEWBORN              NEWBORN    2   True  —                —                                  12    0   
  baby_sleepsuit                                            NEWBORN              NEWBORN    3   True  —                —                                  42    0   
  coat                                                      HEAVY_OUTERWEAR      OUTERWEAR  1   True  —                —                                  43    0   
  trench                                                    HEAVY_OUTERWEAR      OUTERWEAR  2   True  —                —                                  43    0   
  leather_garment                                           HEAVY_OUTERWEAR      OUTERWEAR  3   True  —                —                                  41    0   
  parka                                                     HEAVY_OUTERWEAR      OUTERWEAR  3   True  —                —                                  42    0   
  blazer                                                    STRUCTURED_JACKETS   OUTERWEAR  1   True  —                —                                  44    0   
  gilet                                                     STRUCTURED_JACKETS   OUTERWEAR  1   True  —                —                                  35    12  
  casual_jacket                                             STRUCTURED_JACKETS   OUTERWEAR  2   True  —                —                                  44    12  
  swimsuit                                                  SWIMWEAR             SWIMWEAR   1   True  —                —                                  29    0   
  bikini                                                    SWIMWEAR             SWIMWEAR   2   True  —                —                                  29    8   
  swim_shorts                                               SWIMWEAR             SWIMWEAR   3   True  —                —                                  20    9   
  shirt_woven                                               BUTTONED_TOPS        TOPS       1   True  —                —                                  46    13  
  blouse                                                    BUTTONED_TOPS        TOPS       2   True  —                —                                  47    0   
  overshirt                                                 BUTTONED_TOPS        TOPS       3   True  —                —                                  46    13  
  uniform_shirt                                             BUTTONED_TOPS        TOPS       4   True  —                —                                  44    14  
  t_shirt                                                   JERSEY_TOPS          TOPS       1   True  —                —                                  34    0   
  polo                                                      JERSEY_TOPS          TOPS       2   True  —                —                                  32    11  
  top_sleeveless                                            JERSEY_TOPS          TOPS       3   True  M@WOMAN_LOS_01   LOS Woman Knit — Tops              31    11  
  vest_top                                                  JERSEY_TOPS          TOPS       3   True  —                —                                  35    11  
  cardigan                                                  KNIT_CARDIGANS       TOPS       1   True  —                —                                  32    0   
  knit_gilet                                                KNIT_CARDIGANS       TOPS       2   True  —                —                                  32    0   
  sweater                                                   KNIT_SWEATERS        TOPS       1   True  —                —                                  33    0   
  twinset                                                   KNIT_SWEATERS        TOPS       2   True  —                —                                  31    0   
  hoodie                                                    SWEATSHIRTS_MIDLAYER TOPS       1   True  —                —                                  39    0   
  fleece_jacket                                             SWEATSHIRTS_MIDLAYER TOPS       2   True  —                —                                  35    0   
  bra                                                       BRA_SHAPEWEAR        UNDERWEAR  1   True  —                —                                  6     0   
  shapewear                                                 BRA_SHAPEWEAR        UNDERWEAR  2   True  —                —                                  6     6   
  corset                                                    BRA_SHAPEWEAR        UNDERWEAR  3   True  —                —                                  6     6   
  briefs_man                                                UNDERWEAR            UNDERWEAR  1   True  —                —                                  0     0   
  socks                                                     UNDERWEAR            UNDERWEAR  1   True  —                —                                  0     0   
  briefs_woman                                              UNDERWEAR            UNDERWEAR  2   True  —                —                                  0     0   
  pyjama_set                                                UNDERWEAR            UNDERWEAR  2   True  —                —                                  46    0   
  bodysuit                                                  UNDERWEAR            UNDERWEAR  3   True  —                —                                  29    0   
  thermal_top                                               UNDERWEAR            UNDERWEAR  4   True  —                —                                  29    0   
  TOTAL items: 62 | actius: 62 | inactius: 0
  amb base_size_definition: 1
  amb grading_rule_set (V1 suggerit): 1
  amb 0 GarmentPOMMap: 7
  TOTAL GarmentPOMMap: 1748 | pendent_revisio: 238

```

### Annex B — GradingRule, bolcat per contenidor (402 regles)

```

  ▸ LOSAN IBERIA SA · Newborn · LOS Baby 3-36M (id=55) — 12 regles
    AC SH      act=True  glob=POM-006                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    C3         act=True  glob=LOSPOM-521             LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    CH         act=True  glob=POM-001                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   2.00 base=  2.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    NK DR BK   act=True  glob=POM-032                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    SH         act=True  glob=POM-005                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    SH DR      act=True  glob=POM-014                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    SK SW      act=True  glob=POM-062                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    WA         act=True  glob=POM-003                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—

  ▸ LOS Baby Knit — Tops (id=37) — 16 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    AC FR      act=True  glob=POM-007                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    BIC        act=True  glob=POM-023                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.20 base=  0.20 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    CH         act=True  glob=POM-001                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   2.00 base=  2.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    NK DR BK   act=True  glob=POM-032                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    SH         act=True  glob=POM-005                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    SH DR      act=True  glob=POM-014                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    SK SW      act=True  glob=POM-062                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    SL         act=True  glob=POM-020                LINEAR    inc=   1.50 base=  1.50 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    SL OP      act=True  glob=POM-025                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—
    U          act=True  glob=LOSPOM-512             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 03/06@BABY_LOS_01      break_label=—

  ▸ LOS Kids Boy Knit — Tops (id=38) — 17 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   0.80 base=  0.80 break=  1.60 talla_base=     2@BOY_LOS_01       break_label=9/10
    AC FR      act=True  glob=POM-007                LINEAR    inc=   0.80 base=  0.80 break=  1.60 talla_base=     2@BOY_LOS_01       break_label=9/10
    AC SH      act=True  glob=POM-006                LINEAR    inc=   1.00 base=  1.00 break=  2.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   0.50 base=  0.50 break=  1.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    BIC        act=True  glob=POM-023                LINEAR    inc=   0.50 base=  0.50 break=  1.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.30 base=  0.30 break=  0.50 talla_base=     2@BOY_LOS_01       break_label=9/10
    CH         act=True  glob=POM-001                LINEAR    inc=   0.70 base=  0.70 break=  1.50 talla_base=     2@BOY_LOS_01       break_label=9/10
    HI PA      act=True  glob=POM-040                LINEAR    inc=   0.70 base=  0.70 break=  1.50 talla_base=     2@BOY_LOS_01       break_label=9/10
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   2.20 base=  2.20 break=  3.30 talla_base=     2@BOY_LOS_01       break_label=9/10
    NK DR BK   act=True  glob=POM-032                LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.20 base=  0.20 break=  0.40 talla_base=     2@BOY_LOS_01       break_label=9/10
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.30 base=  0.30 break=  0.60 talla_base=     2@BOY_LOS_01       break_label=9/10
    SH         act=True  glob=POM-005                LINEAR    inc=   0.40 base=  0.40 break=  0.80 talla_base=     2@BOY_LOS_01       break_label=9/10
    SH DR      act=True  glob=POM-014                LINEAR    inc=   0.20 base=  0.20 break=  0.40 talla_base=     2@BOY_LOS_01       break_label=9/10
    SK SW      act=True  glob=POM-062                LINEAR    inc=   0.70 base=  0.70 break=  1.50 talla_base=     2@BOY_LOS_01       break_label=9/10
    SL OP      act=True  glob=POM-025                LINEAR    inc=   0.30 base=  0.30 break=  0.20 talla_base=     2@BOY_LOS_01       break_label=9/10
    WA         act=True  glob=POM-003                LINEAR    inc=   0.70 base=  0.70 break=  1.50 talla_base=     2@BOY_LOS_01       break_label=9/10

  ▸ LOS Kids Boy Woven — Bottoms (id=39) — 25 regles
    C1         act=True  glob=LOSPOM-524             LINEAR    inc=   1.20 base=  1.20 break=  2.40 talla_base=     2@BOY_LOS_01       break_label=9/10
    C12        act=True  glob=LOSPOM-617             LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    C.13       act=True  glob=LOSPOM-669             LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    C4         act=True  glob=LOSPOM-523             LINEAR    inc=   0.80 base=  0.80 break=  1.60 talla_base=     2@BOY_LOS_01       break_label=9/10
    D.11-M79   act=True  glob=LOSPOM-386             LINEAR    inc=   0.40 base=  0.40 break=  0.80 talla_base=     2@BOY_LOS_01       break_label=9/10
    D22        act=True  glob=LOSPOM-529             LINEAR    inc=   2.50 base=  2.50 break=  4.50 talla_base=     2@BOY_LOS_01       break_label=9/10
    HI PA      act=True  glob=POM-040                LINEAR    inc=   1.20 base=  1.20 break=  2.40 talla_base=     2@BOY_LOS_01       break_label=9/10
    KNE        act=True  glob=POM-042                LINEAR    inc=   0.40 base=  0.40 break=  0.80 talla_base=     2@BOY_LOS_01       break_label=9/10
    LEG OP     act=True  glob=POM-043                LINEAR    inc=   0.20 base=  0.20 break=  0.40 talla_base=     2@BOY_LOS_01       break_label=9/10
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   5.00 base=  5.00 break=  5.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    O19        act=True  glob=LOSPOM-593             LINEAR    inc=   0.20 base=  0.20 break=  0.40 talla_base=     2@BOY_LOS_01       break_label=9/10
    O.21-M79   act=True  glob=LOSPOM-390             LINEAR    inc=   0.40 base=  0.40 break=  0.80 talla_base=     2@BOY_LOS_01       break_label=9/10
    O29        act=True  glob=LOSPOM-603             LINEAR    inc=   0.30 base=  0.30 break=  0.60 talla_base=     2@BOY_LOS_01       break_label=9/10
    O30        act=True  glob=LOSPOM-604             LINEAR    inc=   0.30 base=  0.30 break=  0.60 talla_base=     2@BOY_LOS_01       break_label=9/10
    O.32-M79   act=True  glob=LOSPOM-395             LINEAR    inc=   0.30 base=  0.30 break=  0.60 talla_base=     2@BOY_LOS_01       break_label=9/10
    R10        act=True  glob=LOSPOM-543             LINEAR    inc=   0.30 base=  0.30 break=  0.50 talla_base=     2@BOY_LOS_01       break_label=9/10
    RI BK      act=True  glob=POM-056                LINEAR    inc=   0.80 base=  0.80 break=  1.60 talla_base=     2@BOY_LOS_01       break_label=9/10
    RI FR      act=True  glob=POM-055                LINEAR    inc=   0.50 base=  0.50 break=  1.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    S13        act=True  glob=LOSPOM-564             LINEAR    inc=   0.10 base=  0.10 break=  0.20 talla_base=     2@BOY_LOS_01       break_label=9/10
    S25        act=True  glob=LOSPOM-565             LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    S.R1-M79   act=True  glob=LOSPOM-392             LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    S.R6       act=True  glob=LOSPOM-670             LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    S.R7       act=True  glob=LOSPOM-671             LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@BOY_LOS_01       break_label=9/10
    THI        act=True  glob=POM-041                LINEAR    inc=   0.70 base=  0.70 break=  1.40 talla_base=     2@BOY_LOS_01       break_label=9/10
    WB H       act=True  glob=POM-052                LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@BOY_LOS_01       break_label=9/10

  ▸ LOS Kids Girl — Dresses (id=40) — 18 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   0.90 base=  0.90 break=  1.60 talla_base=     2@GIRL_LOS_01      break_label=9/10
    AC FR      act=True  glob=POM-007                LINEAR    inc=   0.90 base=  0.90 break=  1.60 talla_base=     2@GIRL_LOS_01      break_label=9/10
    AC SH      act=True  glob=POM-006                LINEAR    inc=   0.80 base=  0.80 break=  1.20 talla_base=     2@GIRL_LOS_01      break_label=9/10
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   0.50 base=  0.50 break=  1.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    BIC        act=True  glob=POM-023                LINEAR    inc=   0.40 base=  0.40 break=  0.80 talla_base=     2@GIRL_LOS_01      break_label=9/10
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.20 base=  0.20 break=  0.40 talla_base=     2@GIRL_LOS_01      break_label=9/10
    CH         act=True  glob=POM-001                LINEAR    inc=   1.10 base=  1.10 break=  2.20 talla_base=     2@GIRL_LOS_01      break_label=9/10
    M4         act=True  glob=LOSPOM-568             LINEAR    inc=   1.50 base=  1.50 break=  3.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   3.50 base=  3.50 break=  6.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    NK DR BK   act=True  glob=POM-032                LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.20 base=  0.20 break=  0.40 talla_base=     2@GIRL_LOS_01      break_label=9/10
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.30 base=  0.30 break=  0.60 talla_base=     2@GIRL_LOS_01      break_label=9/10
    SH         act=True  glob=POM-005                LINEAR    inc=   0.40 base=  0.40 break=  0.60 talla_base=     2@GIRL_LOS_01      break_label=9/10
    SH DR      act=True  glob=POM-014                LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    SK SW      act=True  glob=POM-062                LINEAR    inc=   1.10 base=  1.10 break=  2.20 talla_base=     2@GIRL_LOS_01      break_label=9/10
    SL         act=True  glob=POM-020                LINEAR    inc=   2.50 base=  2.50 break=  4.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    SL OP      act=True  glob=POM-025                LINEAR    inc=   0.20 base=  0.20 break=  0.30 talla_base=     2@GIRL_LOS_01      break_label=9/10
    U1         act=True  glob=LOSPOM-513             LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@GIRL_LOS_01      break_label=9/10

  ▸ LOS Kids Girl Knit — Tops (id=41) — 17 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   0.80 base=  0.80 break=  1.60 talla_base=     2@GIRL_LOS_01      break_label=9/10
    AC FR      act=True  glob=POM-007                LINEAR    inc=   0.80 base=  0.80 break=  1.60 talla_base=     2@GIRL_LOS_01      break_label=9/10
    AC SH      act=True  glob=POM-006                LINEAR    inc=   1.00 base=  1.00 break=  2.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   0.50 base=  0.50 break=  1.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    BIC        act=True  glob=POM-023                LINEAR    inc=   0.50 base=  0.50 break=  1.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.30 base=  0.30 break=  0.50 talla_base=     2@GIRL_LOS_01      break_label=9/10
    CH         act=True  glob=POM-001                LINEAR    inc=   0.70 base=  0.70 break=  1.50 talla_base=     2@GIRL_LOS_01      break_label=9/10
    HI PA      act=True  glob=POM-040                LINEAR    inc=   0.70 base=  0.70 break=  1.50 talla_base=     2@GIRL_LOS_01      break_label=9/10
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   2.20 base=  2.20 break=  3.30 talla_base=     2@GIRL_LOS_01      break_label=9/10
    NK DR BK   act=True  glob=POM-032                LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     2@GIRL_LOS_01      break_label=9/10
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.20 base=  0.20 break=  0.40 talla_base=     2@GIRL_LOS_01      break_label=9/10
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.30 base=  0.30 break=  0.60 talla_base=     2@GIRL_LOS_01      break_label=9/10
    SH         act=True  glob=POM-005                LINEAR    inc=   0.40 base=  0.40 break=  0.80 talla_base=     2@GIRL_LOS_01      break_label=9/10
    SH DR      act=True  glob=POM-014                LINEAR    inc=   0.20 base=  0.20 break=  0.40 talla_base=     2@GIRL_LOS_01      break_label=9/10
    SK SW      act=True  glob=POM-062                LINEAR    inc=   0.70 base=  0.70 break=  1.50 talla_base=     2@GIRL_LOS_01      break_label=9/10
    SL OP      act=True  glob=POM-025                LINEAR    inc=   0.30 base=  0.30 break=  0.20 talla_base=     2@GIRL_LOS_01      break_label=9/10
    WA         act=True  glob=POM-003                LINEAR    inc=   0.70 base=  0.70 break=  1.50 talla_base=     2@GIRL_LOS_01      break_label=9/10

  ▸ LOS Man Knit — Tops (id=42) — 34 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   2.00 base=  2.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    AC FR      act=True  glob=POM-007                LINEAR    inc=   2.00 base=  2.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    CH         act=True  glob=POM-001                LINEAR    inc=   3.00 base=  3.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    CUF H      act=True  glob=POM-027                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    E.9        act=True  glob=LOSPOM-683             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    G.3        act=True  glob=LOSPOM-680             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    GA         act=True  glob=LOSPOM-550             LINEAR    inc=   0.10 base=  0.10 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    H.12       act=True  glob=LOSPOM-681             LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    H16        act=True  glob=LOSPOM-556             LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    HM L       act=True  glob=POM-154                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    J2         act=True  glob=LOSPOM-508             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   1.50 base=  1.50 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    N4         act=True  glob=LOSPOM-576             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    NK DR BK   act=True  glob=POM-032                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    O11        act=True  glob=LOSPOM-586             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    O12        act=True  glob=LOSPOM-587             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    O14        act=True  glob=LOSPOM-589             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    O.8        act=True  glob=LOSPOM-682             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    O9         act=True  glob=LOSPOM-585             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    PLCK W     act=True  glob=POM-092                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    S1-M76     act=True  glob=LOSPOM-382             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    S3         act=True  glob=LOSPOM-577             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    S.35       act=True  glob=LOSPOM-668             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    S37        act=True  glob=LOSPOM-582             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    S.42       act=True  glob=LOSPOM-684             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    SH         act=True  glob=POM-005                LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    SH DR      act=True  glob=POM-014                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    SK SW      act=True  glob=POM-062                LINEAR    inc=   3.00 base=  3.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    U          act=True  glob=LOSPOM-512             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—
    U1         act=True  glob=LOSPOM-513             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     M@MAN_LOS_01       break_label=—

  ▸ LOS Man Woven — Bottoms (id=43) — 23 regles
    BR         act=True  glob=LOSPOM-487             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    D.11-M79   act=True  glob=LOSPOM-386             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    D22        act=True  glob=LOSPOM-529             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    HI PA      act=True  glob=POM-040                LINEAR    inc=   2.00 base=  2.00 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    KNE        act=True  glob=POM-042                LINEAR    inc=   0.70 base=  0.70 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    LEG OP     act=True  glob=POM-043                LINEAR    inc=   0.60 base=  0.60 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    O20        act=True  glob=LOSPOM-594             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    O.21-M79   act=True  glob=LOSPOM-390             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    O25        act=True  glob=LOSPOM-596             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    O29        act=True  glob=LOSPOM-603             LINEAR    inc=   0.20 base=  0.20 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    O30        act=True  glob=LOSPOM-604             LINEAR    inc=   0.20 base=  0.20 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    O.32-M79   act=True  glob=LOSPOM-395             LINEAR    inc=   0.20 base=  0.20 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    R9         act=True  glob=LOSPOM-542             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    RI BK      act=True  glob=POM-056                LINEAR    inc=   1.30 base=  1.30 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    RI FR      act=True  glob=POM-055                LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    S13        act=True  glob=LOSPOM-564             LINEAR    inc=   0.10 base=  0.10 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    S25        act=True  glob=LOSPOM-565             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    S.R6       act=True  glob=LOSPOM-670             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    S.R7       act=True  glob=LOSPOM-671             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    THI        act=True  glob=POM-041                LINEAR    inc=   1.20 base=  1.20 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    WA         act=True  glob=POM-003                LINEAR    inc=   2.00 base=  2.00 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—
    WB H       act=True  glob=POM-052                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    42@MAN_NUM_LOS_01   break_label=—

  ▸ LOS New Born Knit — Bottoms (id=44) — 20 regles
    C1         act=True  glob=LOSPOM-524             LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    C12        act=True  glob=LOSPOM-617             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    C.13       act=True  glob=LOSPOM-669             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    C4         act=True  glob=LOSPOM-523             LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    D.11-M79   act=True  glob=LOSPOM-386             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    D22        act=True  glob=LOSPOM-529             LINEAR    inc=   1.70 base=  1.70 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    EL EXT     act=True  glob=POM-152                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    EL RLX     act=True  glob=POM-151                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    EV         act=True  glob=LOSPOM-674             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    H16        act=True  glob=LOSPOM-556             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    HI PA      act=True  glob=POM-040                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    KNE        act=True  glob=POM-042                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   2.00 base=  2.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    RI BK      act=True  glob=POM-056                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    RI FR      act=True  glob=POM-055                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.R1-M79   act=True  glob=LOSPOM-392             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    THI        act=True  glob=POM-041                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    V12        act=True  glob=LOSPOM-580             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    V.9        act=True  glob=LOSPOM-672             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    WB H       act=True  glob=POM-052                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—

  ▸ LOS New Born Knit — Onepieces (id=45) — 38 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   0.90 base=  0.90 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    AC FR      act=True  glob=POM-007                LINEAR    inc=   0.90 base=  0.90 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   0.90 base=  0.90 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    BIC        act=True  glob=POM-023                LINEAR    inc=   0.45 base=  0.45 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.20 base=  0.20 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    CH         act=True  glob=POM-001                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    CR L       act=True  glob=POM-150                LINEAR    inc=   2.00 base=  2.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    CUF H      act=True  glob=POM-027                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    D.11-M79   act=True  glob=LOSPOM-386             LINEAR    inc=   1.90 base=  1.90 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    H15        act=True  glob=LOSPOM-555             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    H16        act=True  glob=LOSPOM-556             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    HD W       act=True  glob=POM-096                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    HI PA      act=True  glob=POM-040                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   4.20 base=  4.20 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    NK DR BK   act=True  glob=POM-032                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.25 base=  0.25 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    O16        act=True  glob=LOSPOM-590             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    O20        act=True  glob=LOSPOM-594             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    O.21-M79   act=True  glob=LOSPOM-390             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    O23        act=True  glob=LOSPOM-595             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    RI FR      act=True  glob=POM-055                LINEAR    inc=   1.50 base=  1.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.10       act=True  glob=LOSPOM-425             LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.19       act=True  glob=LOSPOM-648             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.20       act=True  glob=LOSPOM-649             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S3         act=True  glob=LOSPOM-577             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.35       act=True  glob=LOSPOM-668             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.39       act=True  glob=LOSPOM-650             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.40       act=True  glob=LOSPOM-651             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S53        act=True  glob=LOSPOM-614             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.56       act=True  glob=LOSPOM-426             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SH         act=True  glob=POM-005                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SH DR      act=True  glob=POM-014                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SL         act=True  glob=POM-020                LINEAR    inc=   1.60 base=  1.60 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SL OP      act=True  glob=POM-025                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    STRAP W SW act=True  glob=POM-087                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    THI        act=True  glob=POM-041                LINEAR    inc=   0.60 base=  0.60 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    V12        act=True  glob=LOSPOM-580             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—

  ▸ LOS New Born Knit — Tops (id=46) — 37 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    AC FR      act=True  glob=POM-007                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    BIC        act=True  glob=POM-023                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.20 base=  0.20 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    CB         act=True  glob=LOSPOM-673             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    CH         act=True  glob=POM-001                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    CUF H      act=True  glob=POM-027                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    D18        act=True  glob=LOSPOM-538             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    D19        act=True  glob=LOSPOM-540             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    D6         act=True  glob=LOSPOM-539             LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    D7         act=True  glob=LOSPOM-541             LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    H15        act=True  glob=LOSPOM-555             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    H16        act=True  glob=LOSPOM-556             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    H8         act=True  glob=LOSPOM-548             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    H9         act=True  glob=LOSPOM-549             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    HD W       act=True  glob=POM-096                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    HI PA      act=True  glob=POM-040                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    HM L       act=True  glob=POM-154                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    M19        act=True  glob=LOSPOM-544             LINEAR    inc=   2.00 base=  2.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    M20        act=True  glob=LOSPOM-545             LINEAR    inc=   2.00 base=  2.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   2.00 base=  2.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    NK DR BK   act=True  glob=POM-032                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S          act=True  glob=LOSPOM-457             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.10       act=True  glob=LOSPOM-425             LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S.35       act=True  glob=LOSPOM-668             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    S53        act=True  glob=LOSPOM-614             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SH         act=True  glob=POM-005                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SH DR      act=True  glob=POM-014                FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SK SW      act=True  glob=POM-062                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SL         act=True  glob=POM-020                LINEAR    inc=   1.50 base=  1.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SL OP      act=True  glob=POM-025                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    SS         act=True  glob=POM-011                LINEAR    inc=   1.50 base=  1.50 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    U          act=True  glob=LOSPOM-512             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—
    U1         act=True  glob=LOSPOM-513             FIXED     inc=   0.00 base=  0.00 break=     — talla_base= 00/01@NEWBORN_LOS_01   break_label=—

  ▸ LOS Teen Boy Knit — Tops (id=47) — 18 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   1.80 base=  1.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    AC FR      act=True  glob=POM-007                LINEAR    inc=   1.80 base=  1.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    BIC        act=True  glob=POM-023                LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    CH         act=True  glob=POM-001                LINEAR    inc=   2.40 base=  2.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   3.40 base=  3.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    NK DR BK   act=True  glob=POM-032                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.60 base=  0.60 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    O16        act=True  glob=LOSPOM-590             LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    O18        act=True  glob=LOSPOM-592             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    S1-M76     act=True  glob=LOSPOM-382             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    SH         act=True  glob=POM-005                LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    SH DR      act=True  glob=POM-014                LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    SK SW      act=True  glob=POM-062                LINEAR    inc=   2.40 base=  2.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    SL         act=True  glob=POM-020                LINEAR    inc=   3.00 base=  3.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    U1         act=True  glob=LOSPOM-513             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—

  ▸ LOS Teen Boy Woven — Bottoms (id=48) — 19 regles
    C1         act=True  glob=LOSPOM-524             LINEAR    inc=   2.20 base=  2.20 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    C12        act=True  glob=LOSPOM-617             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    C.13       act=True  glob=LOSPOM-669             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    C4         act=True  glob=LOSPOM-523             LINEAR    inc=   1.60 base=  1.60 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    CUF H      act=True  glob=POM-027                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    D.11-M79   act=True  glob=LOSPOM-386             LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    D22        act=True  glob=LOSPOM-529             LINEAR    inc=   4.50 base=  4.50 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    F5         act=True  glob=LOSPOM-532             LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    F6         act=True  glob=LOSPOM-533             LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    HI PA      act=True  glob=POM-040                LINEAR    inc=   2.20 base=  2.20 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    KNE        act=True  glob=POM-042                LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   5.00 base=  5.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    O16        act=True  glob=LOSPOM-590             LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    O23        act=True  glob=LOSPOM-595             LINEAR    inc=   0.20 base=  0.20 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    RI BK      act=True  glob=POM-056                LINEAR    inc=   1.60 base=  1.60 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    RI FR      act=True  glob=POM-055                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    S.R1-M79   act=True  glob=LOSPOM-392             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    THI        act=True  glob=POM-041                LINEAR    inc=   1.50 base=  1.50 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    WB H       act=True  glob=POM-052                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—

  ▸ LOS Teen Boy Woven — Shirts (id=49) — 22 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   2.20 base=  2.20 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    AC FR      act=True  glob=POM-007                LINEAR    inc=   2.20 base=  2.20 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    BIC        act=True  glob=POM-023                LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    CH         act=True  glob=POM-001                LINEAR    inc=   2.40 base=  2.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    CUF H      act=True  glob=POM-027                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    E.8        act=True  glob=LOSPOM-430             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    H17        act=True  glob=LOSPOM-557             LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    J2         act=True  glob=LOSPOM-508             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    L1         act=True  glob=LOSPOM-510             LINEAR    inc=   1.60 base=  1.60 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   3.40 base=  3.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    NK DR BK   act=True  glob=POM-032                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    PLCK W     act=True  glob=POM-092                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    S1-M76     act=True  glob=LOSPOM-382             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    S2         act=True  glob=LOSPOM-583             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    S37        act=True  glob=LOSPOM-582             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    SH         act=True  glob=POM-005                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    SH DR      act=True  glob=POM-014                LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    SK SW      act=True  glob=POM-062                LINEAR    inc=   2.40 base=  2.40 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—
    SL         act=True  glob=POM-020                LINEAR    inc=   3.70 base=  3.70 break=     — talla_base=     8@YOUTH_BOY_LOS_01 break_label=—

  ▸ LOS Teen Girl — Bottoms (id=50) — 12 regles
    C1         act=True  glob=LOSPOM-524             LINEAR    inc=   1.50 base=  1.50 break=  2.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    C4         act=True  glob=LOSPOM-523             LINEAR    inc=   1.50 base=  1.50 break=  2.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    D.11-M79   act=True  glob=LOSPOM-386             LINEAR    inc=   1.00 base=  1.00 break=  1.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    D22        act=True  glob=LOSPOM-529             LINEAR    inc=   2.50 base=  2.50 break=  2.50 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    HI PA      act=True  glob=POM-040                LINEAR    inc=   1.50 base=  1.50 break=  2.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    KNE        act=True  glob=POM-042                LINEAR    inc=   0.50 base=  0.50 break=  0.70 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    LEG OP     act=True  glob=POM-043                LINEAR    inc=   0.50 base=  0.50 break=  0.70 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   5.00 base=  5.00 break=  5.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    RI BK      act=True  glob=POM-056                LINEAR    inc=   1.30 base=  1.30 break=  1.50 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    RI FR      act=True  glob=POM-055                LINEAR    inc=   1.30 base=  1.30 break=  1.30 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    THI        act=True  glob=POM-041                LINEAR    inc=   1.00 base=  1.00 break=  1.40 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    V          act=True  glob=LOSPOM-492             LINEAR    inc=   0.00 base=  0.00 break=  0.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14

  ▸ LOS Teen Girl Knit — Tops (id=51) — 22 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   0.80 base=  0.80 break=  1.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    AC FR      act=True  glob=POM-007                LINEAR    inc=   0.80 base=  0.80 break=  1.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    AC SH      act=True  glob=POM-006                LINEAR    inc=   1.10 base=  1.10 break=  1.10 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   0.50 base=  0.50 break=  1.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    BIC        act=True  glob=POM-023                LINEAR    inc=   0.50 base=  0.50 break=  1.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.30 base=  0.30 break=  0.50 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    C3         act=True  glob=LOSPOM-521             LINEAR    inc=   2.00 base=  2.00 break=  2.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    CH         act=True  glob=POM-001                LINEAR    inc=   1.50 base=  1.50 break=  2.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    D.11-M79   act=True  glob=LOSPOM-386             LINEAR    inc=   1.00 base=  1.00 break=  1.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    G.3        act=True  glob=LOSPOM-680             LINEAR    inc=   0.80 base=  0.80 break=  1.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    H.12       act=True  glob=LOSPOM-681             LINEAR    inc=   0.50 base=  0.50 break=  1.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    HI PA      act=True  glob=POM-040                LINEAR    inc=   1.50 base=  1.50 break=  2.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   3.00 base=  3.00 break=  3.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    NK DR BK   act=True  glob=POM-032                LINEAR    inc=   0.00 base=  0.00 break=  0.50 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.50 base=  0.50 break=  0.50 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.50 base=  0.50 break=  0.50 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    SH         act=True  glob=POM-005                LINEAR    inc=   0.40 base=  0.40 break=  0.40 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    SH DR      act=True  glob=POM-014                LINEAR    inc=   0.30 base=  0.30 break=  0.30 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    SK SW      act=True  glob=POM-062                LINEAR    inc=   1.50 base=  1.50 break=  2.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    SL         act=True  glob=POM-020                LINEAR    inc=   3.40 base=  3.40 break=  1.30 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    SL OP      act=True  glob=POM-025                LINEAR    inc=   0.50 base=  0.50 break=  0.50 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14
    WA         act=True  glob=POM-003                LINEAR    inc=   1.50 base=  1.50 break=  2.00 talla_base=     8@YOUTH_GIRL_LOS_01 break_label=14

  ▸ LOS Teen Girl Stretch — Swimwear (id=52) — 11 regles
    A          act=True  glob=LOSPOM-515             LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    A3         act=True  glob=LOSPOM-516             LINEAR    inc=   0.60 base=  0.60 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    AC BK      act=True  glob=POM-008                LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    AC FR      act=True  glob=POM-007                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    B3         act=True  glob=LOSPOM-520             LINEAR    inc=   1.60 base=  1.60 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    H8         act=True  glob=LOSPOM-548             LINEAR    inc=   0.60 base=  0.60 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    M19        act=True  glob=LOSPOM-544             LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    RI BK      act=True  glob=POM-056                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    RI FR      act=True  glob=POM-055                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    SS         act=True  glob=POM-011                LINEAR    inc=   0.40 base=  0.40 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—
    WA         act=True  glob=POM-003                LINEAR    inc=   1.60 base=  1.60 break=     — talla_base=     8@YOUTH_GIRL_LOS_01 break_label=—

  ▸ LOS Woman Knit — Tops (id=53) — 17 regles
    AC BK      act=True  glob=POM-008                LINEAR    inc=   1.60 base=  1.60 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    AC FR      act=True  glob=POM-007                LINEAR    inc=   1.60 base=  1.60 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    AC SH      act=True  glob=POM-006                LINEAR    inc=   2.00 base=  2.00 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    AH DEP     act=True  glob=POM-012                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    BIC        act=True  glob=POM-023                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    BJ         act=True  glob=LOSPOM-514             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    CH         act=True  glob=POM-001                LINEAR    inc=   3.00 base=  3.00 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   1.30 base=  1.30 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    NK DR BK   act=True  glob=POM-032                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    NK DR FR   act=True  glob=POM-031                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    NK W       act=True  glob=POM-030                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    S1-M76     act=True  glob=LOSPOM-382             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    SH         act=True  glob=POM-005                LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    SH DR      act=True  glob=POM-014                LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    SK SW      act=True  glob=POM-062                LINEAR    inc=   3.00 base=  3.00 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    SL         act=True  glob=POM-020                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—
    SL OP      act=True  glob=POM-025                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=     S@WOMAN_LOS_01     break_label=—

  ▸ LOS Woman Woven — Bottoms (id=54) — 24 regles
    BR         act=True  glob=LOSPOM-487             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    CL         act=True  glob=LOSPOM-522             LINEAR    inc=   2.00 base=  2.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    D.11-M79   act=True  glob=LOSPOM-386             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    D22        act=True  glob=LOSPOM-529             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    HI PA      act=True  glob=POM-040                LINEAR    inc=   2.00 base=  2.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    KNE        act=True  glob=POM-042                LINEAR    inc=   0.70 base=  0.70 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    LEG OP     act=True  glob=POM-043                LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    M-M79      act=True  glob=LOSPOM-389             LINEAR    inc=   0.50 base=  0.50 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    O20        act=True  glob=LOSPOM-594             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    O.21-M79   act=True  glob=LOSPOM-390             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    O25        act=True  glob=LOSPOM-596             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    O29        act=True  glob=LOSPOM-603             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    O30        act=True  glob=LOSPOM-604             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    O.32-M79   act=True  glob=LOSPOM-395             LINEAR    inc=   0.20 base=  0.20 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    R9         act=True  glob=LOSPOM-542             LINEAR    inc=   0.30 base=  0.30 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    RI BK      act=True  glob=POM-056                LINEAR    inc=   1.30 base=  1.30 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    RI FR      act=True  glob=POM-055                LINEAR    inc=   0.80 base=  0.80 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    S13        act=True  glob=LOSPOM-564             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    S25        act=True  glob=LOSPOM-565             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    S.R6       act=True  glob=LOSPOM-670             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    S.R7       act=True  glob=LOSPOM-671             FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    THI        act=True  glob=POM-041                LINEAR    inc=   1.00 base=  1.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    WA         act=True  glob=POM-003                LINEAR    inc=   2.00 base=  2.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—
    WB H       act=True  glob=POM-052                FIXED     inc=   0.00 base=  0.00 break=     — talla_base=    38@WOMAN_NUM_LOS_01 break_label=—

```

### Annex C — CustomerPOMAlias del self LOS (196)

```
  BOLCAT client_code → POM
  client_code    POMMaster.codi_client  pom_global.codi  actiu  client_description
  A              A                      LOSPOM-515       True   FRONT WIDTH LOCATION
  A1             AC FR                  POM-007          True   FRONT WIDTH
  A2             AC BK                  POM-008          True   BACK WIDTH
  A3             A3                     LOSPOM-516       True   BACK WIDTH LOCATION
  AB             AB                     LOSPOM-584       True   CONTOUR COLLAR TOTAL
  AJ             S1-M76                 LOSPOM-382       True   COLLAR WIDTH
  B              CH                     POM-001          True   CHEST WIDTH
  B1             CH RLX                 POM-080          True   CHEST WIDTH RELAXED
  B2             CH STR                 POM-081          True   CHEST WIDTH EXTENDED
  B3             B3                     LOSPOM-520       True   FRONT CHEST WIDTH
  B4             B4                     LOSPOM-652       True   BACK CHEST WIDTH
  BJ             BJ                     LOSPOM-514       True   FRONT&BACK WIDTH LOCATION
  C              WA                     POM-003          True   WAIST WIDTH
  C1             C1                     LOSPOM-524       True   WAIST WIDTH EXTENDED
  C11            WB H                   POM-052          True   WAISTBAND HEIGHT
  C12            C12                    LOSPOM-617       True   INNER ELASTIC WAIST LOCATION
  C.13           C.13                   LOSPOM-669       True   BUTTONHOLE LOCATION
  C14            C.14-M79               LOSPOM-385       True   EYELET LOCATION
  C2             C2                     LOSPOM-525       True   FRONT WAIST WIDTH RELAXED
  C3             C3                     LOSPOM-521       True   WAIST LOCATION
  C4             C4                     LOSPOM-523       True   WAIST WIDTH RELAXED
  C5             C5                     LOSPOM-526       True   BACK WAIST WIDTH RELAXED
  C6             C6                     LOSPOM-527       True   BACK WAIST EXTENDED
  CB             CB                     LOSPOM-673       True   FRONT CUT LOCATION
  CL             CL                     LOSPOM-522       True   WAIST JOIN
  D              HI PA                  POM-040          True   HIP WIDTH
  D1             THI                    POM-041          True   THIGH WIDTH
  D11            D.11-M79               LOSPOM-386       True   HIP LOCATION
  D18            D18                    LOSPOM-538       True   FRONT CROTCH WIDTH LOCATION
  D19            D19                    LOSPOM-540       True   BACK CROTCH WIDTH LOCATION
  D2             KNE                    POM-042          True   KNEE WIDTH
  D20            CR L                   POM-150          True   CROTCH LENGTH
  D22            D22                    LOSPOM-529       True   KNEE LOCATION
  D6             D6                     LOSPOM-539       True   FRONT CROTCH WIDTH
  D7             D7                     LOSPOM-541       True   BACK CROTCH WIDTH
  E              SK SW                  POM-062          True   BOTTOM WIDTH
  E.1            E.1                    LOSPOM-653       True   FRONT BOTTOM WIDTH
  E.2            E.2                    LOSPOM-654       True   BACK BOTTOM WIDTH
  E3             E3                     LOSPOM-534       True   BOTTOM WIDTH RELAXED
  E4             E4                     LOSPOM-535       True   BOTTOM WIDTH EXTENDED
  E5             E5                     LOSPOM-536       True   FRONT BOTTOM WIDTH
  E7             E7                     LOSPOM-537       True   BOTTOM HEIGHT
  E8             E.8                    LOSPOM-430       True   BOTTOM DIFFERENCE
  E.9            E.9                    LOSPOM-683       True   BOTTOM MOTIVE LOCATION
  EV             EV                     LOSPOM-674       True   WAIST HEIGHT STITCHING
  F              LEG OP                 POM-043          True   LEG OPENING
  F1             F1                     LOSPOM-530       True   FRONT LEG OPENING
  F2             F2                     LOSPOM-531       True   BACK LEG OPENING
  F5             F5                     LOSPOM-532       True   LEG OPENING RELAXED
  F6             F6                     LOSPOM-533       True   LEG OPENING EXTENDED
  FP             FP                     LOSPOM-509       True   SHOULDER PIECE WIDTH
  G              SL                     POM-020          True   SLEEVE LENGTH
  G.3            G.3                    LOSPOM-680       True   SLEEVE SHORT LENGTH
  G5             G5                     LOSPOM-552       True   ELBOW LOCATION
  GA             GA                     LOSPOM-550       True   SLEEVE INSEAM LENGTH
  GL             GL                     LOSPOM-558       True   CUFF OPENING INNER
  GM             GM                     LOSPOM-560       True   CUFF DIFFERENCE
  GN             GN                     LOSPOM-559       True   CUFF HEIGHT INNER
  H              BIC                    POM-023          True   SLEEVE MUSCLE
  H11            SL OP                  POM-025          True   SLEEVE OPENING
  H.12           H.12                   LOSPOM-681       True   SLEEVE SHORT OPENING
  H12            H.12                   LOSPOM-681       True   SLEEVE SHORT OPENING
  H13            J1                     LOSPOM-460       True   SLEEVE OPENING RELAXED
  H14            H14                    LOSPOM-554       True   SLEEVE OPENING EXTENDED
  H15            H15                    LOSPOM-555       True   WIDTH BEFORE CUFF EXTENDED
  H16            H16                    LOSPOM-556       True   CUFF OPENING
  H17            H17                    LOSPOM-557       True   CUFF LENGTH
  H19            BIC                    POM-023          True   SLEEVE MOTIVE LOCATION
  H4             ELB                    POM-024          True   ELBOW WIDTH
  H6             AH DEP                 POM-012          True   ARMHOLE
  H7             H7                     LOSPOM-547       True   ARMHOLE POINT LOCATION
  H8             H8                     LOSPOM-548       True   FRONT ARMHOLE
  H9             H9                     LOSPOM-549       True   BACK ARMHOLE
  J1             J1                     LOSPOM-507       True   SHOULDER DROP LOCATION
  J2             J2                     LOSPOM-508       True   SHOULDER MOVE FORWARD
  JC             JC                     LOSPOM-574       True   TAPE WIDTH
  K              SH                     POM-005          True   SHOULDER
  K1             SH DR                  POM-014          True   SHOULDER DROP
  K2             AC SH                  POM-006          True   SHOULDER TO SHOULDER
  L1             L1                     LOSPOM-510       True   NECK TOTAL
  L3             NK W                   POM-030          True   NECK WIDTH (SEAM TO SEAM)
  L4             NK DR FR               POM-031          True   FRONT NECK DROP
  L5             NK DR BK               POM-032          True   BACK NECK DROP
  M              M-M79                  LOSPOM-389       True   TOTAL LENGTH
  M.1            M.1                    LOSPOM-655       True   FRONT LENGTH CENTER
  M19            M19                    LOSPOM-544       True   FRONT LENGTH
  M20            M20                    LOSPOM-545       True   BACK LENGTH
  M4             M4                     LOSPOM-568       True   CUT LOCATION
  M8             SS                     POM-011          True   SIDE LENGTH
  MF             MF                     LOSPOM-546       True   SIDE SEAM MOVED FORWARD
  N4             N4                     LOSPOM-576       True   SIDE OPENING
  O11            O11                    LOSPOM-586       True   CHEST POCKET WIDTH
  O12            O12                    LOSPOM-587       True   CHEST POCKET LENGTH
  O13            O13                    LOSPOM-588       True   CHEST POCKET LENGTH W/FLAP
  O14            O14                    LOSPOM-589       True   CHEST POCKET LOCATION
  O16            O16                    LOSPOM-590       True   FRONT POCKET OPENING
  O17            O17                    LOSPOM-591       True   FRONT POCKET FLAP HEIGHT
  O18            O18                    LOSPOM-592       True   FRONT POCKET FLAP WIDTH
  O19            O19                    LOSPOM-593       True   FRONT POCKET LENGTH W/FLAP
  O20            O20                    LOSPOM-594       True   FRONT POCKET WIDTH
  O21            O.21-M79               LOSPOM-390       True   FRONT POCKET LENGTH
  O23            O23                    LOSPOM-595       True   FRONT POCKET LOCATION
  O25            O25                    LOSPOM-596       True   FRONT LINING LENGTH
  O26            O.26-M79               LOSPOM-393       True   BACK POCKET OPENING
  O27            O.27-M79               LOSPOM-394       True   BACK POCKET FLAP HEIGHT
  O28            O28                    LOSPOM-597       True   BACK POCKET FLAP WIDTH
  O29            O29                    LOSPOM-603       True   BACK POCKET WIDTH
  O30            O30                    LOSPOM-604       True   BACK POCKET LENGTH
  O32            O.32-M79               LOSPOM-395       True   BACK POCKET LOCATION
  O33            O33                    LOSPOM-605       True   COIN POCKET WIDTH
  O34            O34                    LOSPOM-606       True   COIN POCKET LENGTH
  O35            PKT OP                 POM-097          True   SIDE POCKET OPENING
  O36            O36                    LOSPOM-598       True   SIDE POCKET FLAP HEIGHT
  O38            O38                    LOSPOM-599       True   SIDE POCKET WIDTH
  O39            O39                    LOSPOM-600       True   SIDE POCKET LENGTH
  O40            O40                    LOSPOM-601       True   SIDE POCKET W/FLAP
  O41            O41                    LOSPOM-602       True   SIDE POCKET LOCATION
  O.8            O.8                    LOSPOM-682       True   CHEST POCKET OPENING
  O9             O9                     LOSPOM-585       True   CHEST POCKET FLAP HEIGHT
  R              ZIP L                  POM-090          True   ZIPPER LENGTH
  R.1            R.1                    LOSPOM-656       True   STRAP LENGTH
  R1             STRAP LF               POM-126          True   STRAP LENGTH
  R10            R10                    LOSPOM-543       True   FALSE FLY
  R2             STRAP W SW             POM-087          True   STRAP WIDTH
  R.3            R.3                    LOSPOM-657       True   STRAP LOCATION
  R8             BR                     LOSPOM-487       True   FLY WIDTH
  R9             R9                     LOSPOM-542       True   FLY OPENING
  S              S                      LOSPOM-581       True   COLLAR HEIGHT ON TOP
  S10            S.10                   LOSPOM-425       True   HOOD LENGTH
  S11            HD W                   POM-096          True   HOOD WIDTH
  S13            S13                    LOSPOM-564       True   BACK YOKE CENTER LENGTH
  S.19           S.19                   LOSPOM-648       True   FOOT LENGTH
  S2             S2                     LOSPOM-583       True   COLLAR BAND HEIGHT
  S.20           S.20                   LOSPOM-649       True   FOOT WIDTH
  S21            BELT L                 POM-123          True   BELT LENGTH
  S22            S                      LOSPOM-457       True   BELT HEIGHT
  S25            S25                    LOSPOM-565       True   SIDE YOKE LENGTH
  S27            S27                    LOSPOM-561       True   FRONT YOKE CENTER LENGTH
  S28            S28                    LOSPOM-562       True   FRONT YOKE LENGTH
  S3             S3                     LOSPOM-577       True   PLACKET LENGTH
  S30            S30                    LOSPOM-563       True   BACK YOKE LENGTH
  S34            S34                    LOSPOM-573       True   FRONT COVER WIDTH
  S.35           S.35                   LOSPOM-668       True   COLLAR PIECE WIDTH
  S37            S37                    LOSPOM-582       True   COLLAR PEAK
  S.39           S.39                   LOSPOM-650       True   FOOT WIDTH LOCATION
  S4             PLCK W                 POM-092          True   PLACKET WIDTH
  S.40           S.40                   LOSPOM-651       True   FRONT FOOT LENGTH
  S.42           S.42                   LOSPOM-684       True   FRONT VENT WIDTH
  S44            S                      LOSPOM-457       True   FRONT MOTIVE LOCATION
  S45            S45                    LOSPOM-575       True   BACK OPENING
  S5             CUF H                  POM-027          True   CUFF HEIGHT
  S53            S53                    LOSPOM-614       True   HOOD WIDTH LOCATION
  S54            S54                    LOSPOM-612       True   HOOD LENGTH RELAXED
  S55            S55                    LOSPOM-613       True   HOOD LENGTH EXTENDED
  S56            S.56                   LOSPOM-426       True   HOOD PIECE WIDTH
  S8             S8                     LOSPOM-511       True   COLLAR OPENING EXTENDED
  SR1            S.R1-M79               LOSPOM-392       True   CORD LENGTH IN OUTSIDE
  SR10           IC2                    LOSPOM-497       True   BOW LENGTH
  SR2            SR2                    LOSPOM-615       True   DRAWSTRING LENGTH MEASURED AT POINT WHERE TIES
  SR3            SR3                    LOSPOM-616       True   DRAWSTRING CHANNEL
  S.R6           S.R6                   LOSPOM-670       True   LOOP LENGTH
  S.R7           S.R7                   LOSPOM-671       True   LOOP WIDTH
  SR9            ELB                    POM-024          True   BOW WIDTH
  T1             RI FR                  POM-055          True   FRONT RISE
  T13            T13                    LOSPOM-566       True   PLEAT LOCATION
  T14            T14                    LOSPOM-567       True   PLEAT
  T2             RI BK                  POM-056          True   BACK RISE
  T5             HM L                   POM-154          True   HALF MOON LENGTH
  U              U                      LOSPOM-512       True   RIB WIDTH
  U.1            U1                     LOSPOM-513       True   JETTING WIDTH
  U1             U1                     LOSPOM-513       True   JETTING WIDTH
  U3             FLO W                  POM-074          True   FLOUNCE WIDTH
  U4             U4                     LOSPOM-578       True   FLOUNCE HEIGHT
  U5             FLO POS                POM-076          True   FLOUNCE LOCATION
  U6             FLO EXT                POM-075          True   FLOUNCE EXTENDED
  U7             U7                     LOSPOM-579       True   FRILL HEIGHT
  V              V                      LOSPOM-492       True   STITCHING WIDTH
  V10            EL RLX                 POM-151          True   ELASTIC RELAXED
  V11            EL EXT                 POM-152          True   ELASTIC EXTENDED
  V12            V12                    LOSPOM-580       True   FOLD
  V13            V.13-M79               LOSPOM-397       True   DART LENGTH
  V14            V.14-M79               LOSPOM-396       True   DART LOCATION
  V18            V                      LOSPOM-492       True   BUTTON LOCATION
  V.2            S.35                   LOSPOM-668       True   COLLAR PIECE WIDTH
  V3             V                      LOSPOM-492       True   STITCHING LOCATION
  V4             V4                     LOSPOM-569       True   PIECE WIDTH
  V5             V5                     LOSPOM-570       True   PIECE WIDTH EXTENDED
  V6             V6                     LOSPOM-571       True   PIECE LENGTH
  V7             V7                     LOSPOM-572       True   PIECE LOCATION
  V.9            V.9                    LOSPOM-672       True   ELASTIC LOCATION
  W4             W4                     LOSPOM-607       True   INNER POCKET OPENING
  W5             W5                     LOSPOM-608       True   INNER POCKET FLAP HEIGHT
  W6             W6                     LOSPOM-609       True   INNER POCKET WIDTH
  W7             W7                     LOSPOM-610       True   INNER POCKET LENGTH
  W9             W9                     LOSPOM-611       True   INNER POCKET LOCATION
  Z              Z                      LOSPOM-658       True   FRILL LENGTH

```

### Annex D — Intersecció regles×maps, item a item (19 contenidors)

```

  ▸ LOSAN IBERIA SA · Newborn · LOS Baby 3-36M — 12 regles · fallback garment_group=NEWBORN · items a l'abast=9
      baby_bloomers        maps=12   ∩regles=0    ← BUIDA
      baby_bodysuit        maps=23   ∩regles=3    
      baby_dress           maps=10   ∩regles=3    
      baby_leggings        maps=29   ∩regles=1    
      baby_sleepbag        maps=12   ∩regles=2    
      baby_sleepsuit       maps=42   ∩regles=3    
      baby_swimwear        maps=9    ∩regles=2    
      baby_top             maps=25   ∩regles=5    
      booties              maps=0    ∩regles=0    ← BUIDA
      >>> items amb intersecció BUIDA: 2/9

  ▸ LOS Baby Knit — Tops — 16 regles · scope_nodes: ITEM:163 + ITEM:157 · items a l'abast=2
      baby_bodysuit        maps=23   ∩regles=6    
      baby_top             maps=25   ∩regles=11   
      >>> items amb intersecció BUIDA: 0/2

  ▸ LOS Kids Boy Knit — Tops — 17 regles · fallback garment_group=TOPS · items a l'abast=14
      blouse               maps=47   ∩regles=15   
      overshirt            maps=46   ∩regles=15   
      shirt_woven          maps=46   ∩regles=15   
      uniform_shirt        maps=44   ∩regles=13   
      polo                 maps=32   ∩regles=15   
      top_sleeveless       maps=31   ∩regles=14   
      t_shirt              maps=34   ∩regles=15   
      vest_top             maps=35   ∩regles=15   
      cardigan             maps=32   ∩regles=9    
      knit_gilet           maps=32   ∩regles=9    
      sweater              maps=33   ∩regles=10   
      twinset              maps=31   ∩regles=9    
      fleece_jacket        maps=35   ∩regles=13   
      hoodie               maps=39   ∩regles=14   
      >>> items amb intersecció BUIDA: 0/14

  ▸ LOS Kids Boy Woven — Bottoms — 25 regles · fallback garment_group=BOTTOMS · items a l'abast=10
      culotte_cycling      maps=26   ∩regles=7    
      leggings             maps=26   ∩regles=7    
      skirt_straight       maps=16   ∩regles=1    
      skirt_volume         maps=16   ∩regles=1    
      chino                maps=23   ∩regles=7    
      jeans                maps=44   ∩regles=24   
      shorts               maps=32   ∩regles=15   
      tracksuit_pant       maps=38   ∩regles=15   
      trousers             maps=52   ∩regles=23   
      workwear_pant        maps=23   ∩regles=7    
      >>> items amb intersecció BUIDA: 0/10

  ▸ LOS Kids Girl — Dresses — 18 regles · fallback garment_group=DRESSES · items a l'abast=7
      dungarees            maps=46   ∩regles=13   
      jumpsuit             maps=46   ∩regles=13   
      playsuit             maps=46   ∩regles=13   
      dress_fancy          maps=35   ∩regles=14   
      dress_simple         maps=40   ∩regles=18   
      dress_structured     maps=35   ∩regles=14   
      shirt_dress          maps=33   ∩regles=14   
      >>> items amb intersecció BUIDA: 0/7

  ▸ LOS Kids Girl Knit — Tops — 17 regles · fallback garment_group=TOPS · items a l'abast=14
      blouse               maps=47   ∩regles=15   
      overshirt            maps=46   ∩regles=15   
      shirt_woven          maps=46   ∩regles=15   
      uniform_shirt        maps=44   ∩regles=13   
      polo                 maps=32   ∩regles=15   
      top_sleeveless       maps=31   ∩regles=14   
      t_shirt              maps=34   ∩regles=15   
      vest_top             maps=35   ∩regles=15   
      cardigan             maps=32   ∩regles=9    
      knit_gilet           maps=32   ∩regles=9    
      sweater              maps=33   ∩regles=10   
      twinset              maps=31   ∩regles=9    
      fleece_jacket        maps=35   ∩regles=13   
      hoodie               maps=39   ∩regles=14   
      >>> items amb intersecció BUIDA: 0/14

  ▸ LOS Man Knit — Tops — 34 regles · fallback garment_group=TOPS · items a l'abast=14
      blouse               maps=47   ∩regles=17   
      overshirt            maps=46   ∩regles=16   
      shirt_woven          maps=46   ∩regles=16   
      uniform_shirt        maps=44   ∩regles=14   
      polo                 maps=32   ∩regles=12   
      top_sleeveless       maps=31   ∩regles=11   
      t_shirt              maps=34   ∩regles=14   
      vest_top             maps=35   ∩regles=13   
      cardigan             maps=32   ∩regles=6    
      knit_gilet           maps=32   ∩regles=6    
      sweater              maps=33   ∩regles=8    
      twinset              maps=31   ∩regles=6    
      fleece_jacket        maps=35   ∩regles=9    
      hoodie               maps=39   ∩regles=10   
      >>> items amb intersecció BUIDA: 0/14

  ▸ LOS Man Woven — Bottoms — 23 regles · fallback garment_group=BOTTOMS · items a l'abast=10
      culotte_cycling      maps=26   ∩regles=7    
      leggings             maps=26   ∩regles=7    
      skirt_straight       maps=16   ∩regles=1    
      skirt_volume         maps=16   ∩regles=1    
      chino                maps=23   ∩regles=7    
      jeans                maps=44   ∩regles=22   
      shorts               maps=32   ∩regles=10   
      tracksuit_pant       maps=38   ∩regles=10   
      trousers             maps=52   ∩regles=23   
      workwear_pant        maps=23   ∩regles=7    
      >>> items amb intersecció BUIDA: 0/10

  ▸ LOS New Born Knit — Bottoms — 20 regles · scope_nodes: ITEM:159 + ITEM:156 · items a l'abast=2
      baby_bloomers        maps=12   ∩regles=6    
      baby_leggings        maps=29   ∩regles=20   
      >>> items amb intersecció BUIDA: 0/2

  ▸ LOS New Born Knit — Onepieces — 38 regles · scope_nodes: ITEM:161 + ITEM:160 + ITEM:164 · items a l'abast=3
      baby_sleepbag        maps=12   ∩regles=4    
      baby_sleepsuit       maps=42   ∩regles=29   
      booties              maps=0    ∩regles=0    ← BUIDA
      >>> items amb intersecció BUIDA: 1/3

  ▸ LOS New Born Knit — Tops — 37 regles · scope_nodes: ITEM:163 + ITEM:157 · items a l'abast=2
      baby_bodysuit        maps=23   ∩regles=15   
      baby_top             maps=25   ∩regles=21   
      >>> items amb intersecció BUIDA: 0/2

  ▸ LOS Teen Boy Knit — Tops — 18 regles · fallback garment_group=TOPS · items a l'abast=14
      blouse               maps=47   ∩regles=14   
      overshirt            maps=46   ∩regles=14   
      shirt_woven          maps=46   ∩regles=14   
      uniform_shirt        maps=44   ∩regles=12   
      polo                 maps=32   ∩regles=14   
      top_sleeveless       maps=31   ∩regles=13   
      t_shirt              maps=34   ∩regles=15   
      vest_top             maps=35   ∩regles=17   
      cardigan             maps=32   ∩regles=8    
      knit_gilet           maps=32   ∩regles=8    
      sweater              maps=33   ∩regles=9    
      twinset              maps=31   ∩regles=8    
      fleece_jacket        maps=35   ∩regles=11   
      hoodie               maps=39   ∩regles=12   
      >>> items amb intersecció BUIDA: 0/14

  ▸ LOS Teen Boy Woven — Bottoms — 19 regles · fallback garment_group=BOTTOMS · items a l'abast=10
      culotte_cycling      maps=26   ∩regles=6    
      leggings             maps=26   ∩regles=6    
      skirt_straight       maps=16   ∩regles=1    
      skirt_volume         maps=16   ∩regles=1    
      chino                maps=23   ∩regles=6    
      jeans                maps=44   ∩regles=15   
      shorts               maps=32   ∩regles=16   
      tracksuit_pant       maps=38   ∩regles=19   
      trousers             maps=52   ∩regles=19   
      workwear_pant        maps=23   ∩regles=6    
      >>> items amb intersecció BUIDA: 0/10

  ▸ LOS Teen Boy Woven — Shirts — 22 regles · fallback garment_group=TOPS · items a l'abast=14
      blouse               maps=47   ∩regles=21   
      overshirt            maps=46   ∩regles=21   
      shirt_woven          maps=46   ∩regles=21   
      uniform_shirt        maps=44   ∩regles=19   
      polo                 maps=32   ∩regles=13   
      top_sleeveless       maps=31   ∩regles=11   
      t_shirt              maps=34   ∩regles=13   
      vest_top             maps=35   ∩regles=13   
      cardigan             maps=32   ∩regles=7    
      knit_gilet           maps=32   ∩regles=7    
      sweater              maps=33   ∩regles=8    
      twinset              maps=31   ∩regles=7    
      fleece_jacket        maps=35   ∩regles=10   
      hoodie               maps=39   ∩regles=11   
      >>> items amb intersecció BUIDA: 0/14

  ▸ LOS Teen Girl — Bottoms — 12 regles · fallback garment_group=BOTTOMS · items a l'abast=10
      culotte_cycling      maps=26   ∩regles=6    
      leggings             maps=26   ∩regles=6    
      skirt_straight       maps=16   ∩regles=0    ← BUIDA
      skirt_volume         maps=16   ∩regles=0    ← BUIDA
      chino                maps=23   ∩regles=6    
      jeans                maps=44   ∩regles=11   
      shorts               maps=32   ∩regles=11   
      tracksuit_pant       maps=38   ∩regles=11   
      trousers             maps=52   ∩regles=12   
      workwear_pant        maps=23   ∩regles=6    
      >>> items amb intersecció BUIDA: 2/10

  ▸ LOS Teen Girl Knit — Tops — 22 regles · fallback garment_group=TOPS · items a l'abast=14
      blouse               maps=47   ∩regles=16   
      overshirt            maps=46   ∩regles=16   
      shirt_woven          maps=46   ∩regles=16   
      uniform_shirt        maps=44   ∩regles=14   
      polo                 maps=32   ∩regles=16   
      top_sleeveless       maps=31   ∩regles=15   
      t_shirt              maps=34   ∩regles=16   
      vest_top             maps=35   ∩regles=16   
      cardigan             maps=32   ∩regles=10   
      knit_gilet           maps=32   ∩regles=10   
      sweater              maps=33   ∩regles=11   
      twinset              maps=31   ∩regles=10   
      fleece_jacket        maps=35   ∩regles=14   
      hoodie               maps=39   ∩regles=15   
      >>> items amb intersecció BUIDA: 0/14

  ▸ LOS Teen Girl Stretch — Swimwear — 11 regles · fallback garment_group=SWIMWEAR · items a l'abast=3
      bikini               maps=29   ∩regles=6    
      swim_shorts          maps=20   ∩regles=3    
      swimsuit             maps=29   ∩regles=6    
      >>> items amb intersecció BUIDA: 0/3

  ▸ LOS Woman Knit — Tops — 17 regles · fallback garment_group=TOPS · items a l'abast=14
      blouse               maps=47   ∩regles=16   
      overshirt            maps=46   ∩regles=16   
      shirt_woven          maps=46   ∩regles=16   
      uniform_shirt        maps=44   ∩regles=14   
      polo                 maps=32   ∩regles=16   
      top_sleeveless       maps=31   ∩regles=14   
      t_shirt              maps=34   ∩regles=16   
      vest_top             maps=35   ∩regles=16   
      cardigan             maps=32   ∩regles=10   
      knit_gilet           maps=32   ∩regles=10   
      sweater              maps=33   ∩regles=11   
      twinset              maps=31   ∩regles=10   
      fleece_jacket        maps=35   ∩regles=13   
      hoodie               maps=39   ∩regles=14   
      >>> items amb intersecció BUIDA: 0/14

  ▸ LOS Woman Woven — Bottoms — 24 regles · fallback garment_group=BOTTOMS · items a l'abast=10
      culotte_cycling      maps=26   ∩regles=7    
      leggings             maps=26   ∩regles=7    
      skirt_straight       maps=16   ∩regles=1    
      skirt_volume         maps=16   ∩regles=1    
      chino                maps=23   ∩regles=7    
      jeans                maps=44   ∩regles=22   
      shorts               maps=32   ∩regles=10   
      tracksuit_pant       maps=38   ∩regles=10   
      trousers             maps=52   ∩regles=24   
      workwear_pant        maps=23   ∩regles=7    
      >>> items amb intersecció BUIDA: 0/10


```

### Annex E — CustomerPOMAlias del Customer LOS al schema `fhort` (183)

```
  client_code    POMMaster              pom_global       nom_client
  A              A                      None             FRONT WIDTH LOCATION
  A1             A.1                    None             FRONT WIDTH
  A2             A2                     None             BACK WIDTH
  A3             A3                     None             BACK WIDTH LOCATION
  AB             AB                     None             CONTOUR COLLAR TOTAL
  AJ             S1-M76                 None             Collar Width (Neck Tie Length)
  B              CH                     POM-001          Chest width
  B1             B1                     None             CHEST WIDTH RELAXED
  B2             B2                     None             CHEST WIDTH EXTENDED
  B3             B3                     None             FRONT CHEST WIDTH
  B9             B9                     None             CHEST MOTIVE LOCATION
  BJ             BJ                     None             FRONT&BACK WIDTH LOCATION
  C              WA                     POM-003          Waist width
  C1             C1                     None             WAIST WIDTH EXTENDED
  C11            WB H                   POM-052          Waistband height
  C12            C.12                   None             INNER ELASTIC WAIST LOCATION
  C13            C13                    None             BUTTONHOLE LOCATION
  C14            C.14-M79               None             EYELET LOCATION
  C2             C2                     None             FRONT WAIST WIDTH RELAXED
  C3             C3                     None             WAIST LOCATION
  C4             C4                     None             WAIST WIDTH RELAXED
  C5             C5                     None             BACK WAIST WIDTH RELAXED
  C6             C6                     None             BACK WAIST EXTENDED
  CL             CL                     None             WAIST JOIN
  D              HI                     POM-004          Hip width (top)
  D1             THI                    POM-041          Thigh width
  D11            D.11-M79               None             HIP LOCATION
  D18            D18                    None             FRONT CROTCH WIDTH LOCATION
  D19            D19                    None             BACK CROTCH WIDTH LOCATION
  D2             KNE                    POM-042          Knee width
  D20            CR L                   POM-150          Crotch length
  D22            D.22                   None             KNEE LOCATION
  D6             D6                     None             FRONT CROTCH WIDTH
  D7             D7                     None             BACK CROTCH WIDTH
  E              E                      None             BOTTOM WIDTH
  E3             E3                     None             BOTTOM WIDTH RELAXED
  E4             E4                     None             BOTTOM WIDTH EXTENDED
  E5             E5                     None             FRONT BOTTOM WIDTH
  E7             M1                     None             Bottom height (leg hem)
  E8             E8                     None             BOTTOM DIFFERENCE
  E9             E9                     None             BOTTOM MOTIVE LOCATION
  ES             ES                     None             MOTIVE LOCATION
  EV             EV                     None             WAIST HEIGHT STITCHING
  F              LEG OP                 POM-043          Leg opening
  F1             F1                     None             FRONT LEG OPENING
  F2             F2                     None             BACK LEG OPENING
  F5             F5                     None             LEG OPENING RELAXED
  F6             F6                     None             LEG OPENING EXTENDED
  FP             FP                     None             SHOULDER PIECE WIDTH
  G              SL                     POM-020          Sleeve length
  G5             G5                     None             ELBOW LOCATION
  GA             INS                    POM-044          Inseam length
  GL             GL                     None             CUFF OPENING INNER
  GM             GM                     None             CUFF DIFFERENCE
  GN             GN                     None             CUFF HEIGHT INNER
  H              H                      None             SLEEVE MUSCLE (1/2)
  H11            H11                    None             SLEEVE OPENING
  H13            H13                    None             SLEEVE OPENING RELAXED
  H14            H14                    None             SLEEVE OPENING EXTENDED
  H15            H15                    None             WIDTH BEFORE CUFF EXTENDED
  H16            H16                    None             CUFF OPENING
  H17            H17                    None             CUFF LENGTH
  H19            H19                    None             SLEEVE MOTIVE LOCATION
  H4             JJ                     None             ELBOW WIDTH
  H6             AH DEP                 POM-012          Armhole depth
  H7             H                      None             SLEEVE MUSCLE (1/2)
  H8             S                      None             FRONT ARMHOLE
  H9             S2                     None             BACK ARMHOLE
  J1             SH DR                  POM-014          Shoulder drop
  J2             J.2                    None             SHOULDER MOVE FORWARD
  JC             JC                     None             TAPE WIDTH
  K              SH                     POM-005          Shoulder width
  K1             SH DR                  POM-014          Shoulder drop
  K2             E                      None             SHOULDER TO SHOULDER
  L1             L1                     None             NECK TOTAL
  L3             NK W                   POM-030          Neck width
  L4             L.4                    None             FRONT NECK DROP
  L5             L.5                    None             BACK NECK DROP
  M              M-M79                  None             TOTAL LENGTH
  M19            F                      None             Centre front length at CF
  M20            FF                     None             Centre back length at CB
  M4             M4                     None             CUT LOCATION
  M8             F2                     None             TOTAL SIDE LENGTH
  MF             MF                     None             SIDE SEAM MOVED FORWARD
  N4             N4                     None             SIDE OPENING
  O11            O11                    None             CHEST POCKET WIDTH
  O12            O12                    None             CHEST POCKET LENGTH
  O13            O13                    None             CHEST POCKET LENGTH W/FLAP
  O14            O14                    None             CHEST POCKET LOCATION
  O16            O16                    None             FRONT POCKET OPENING
  O17            O17                    None             FRONT POCKET FLAP HEIGHT
  O18            O18                    None             FRONT POCKET FLAP WIDTH
  O19            O19                    None             FRONT POCKET LENGTH W/FLAP
  O20            O20                    None             FRONT POCKET WIDTH
  O21            O.21-M79               None             FRONT POCKET LENGTH
  O23            O23                    None             FRONT POCKET LOCATION
  O25            O25                    None             FRONT LINING LENGTH
  O26            O.26-M79               None             BACK POCKET OPENING
  O27            O.27-M79               None             BACK POCKET FLAP HEIGHT
  O28            O28                    None             BACK POCKET FLAP WIDTH
  O29            O29                    None             BACK POCKET WIDTH
  O30            O.30                   None             BACK POCKET LENGTH
  O32            O.32-M79               None             BACK POCKET LOCATION
  O33            O33                    None             COIN POCKET WIDTH
  O34            O34                    None             COIN POCKET LENGTH
  O35            PKT OP                 POM-097          Side pocket opening
  O36            O36                    None             SIDE POCKET FLAP HEIGHT
  O38            O38                    None             SIDE POCKET WIDTH
  O39            O39                    None             SIDE POCKET LENGTH
  O40            O40                    None             SIDE POCKET W/FLAP
  O41            O41                    None             SIDE POCKET LOCATION
  O9             O9                     None             CHEST POCKET FLAP HEIGHT
  R              ZIP L                  POM-090          Zipper length
  R1             R1                     None             STRAP LENGTH
  R10            R10                    None             FALSE FLY
  R2             R2                     None             STRAP WIDTH
  R8             BR                     None             FLY WIDTH
  R9             R.9                    None             FLY OPENING
  S              S                      None             COLLAR HEIGHT ON TOP
  S10            S.10                   None             HOOD LENGTH
  S11            HD W                   POM-096          Hood width
  S13            S13                    None             BACK YOKE CENTER LENGTH
  S2             S2                     None             COLLAR BAND HEIGHT
  S21            BELT L                 POM-123          Belt length
  S22            S22                    None             BELT HEIGHT
  S25            S.25                   None             SIDE YOKE
  S27            S27                    None             FRONT YOKE CENTER LENGTH
  S28            YK L                   POM-029          Front yoke length (center)
  S3             S3                     None             PLACKET LENGTH
  S30            S.13                   None             BACK YOKE LENGTH
  S34            S34                    None             FRONT COVER WIDTH
  S37            S.37                   None             COLLAR PEAK
  S4             PLCK W                 POM-092          Placket width
  S44            S44                    None             FRONT MOTIVE LOCATION
  S45            S45                    None             BACK OPENING
  S5             CUF H                  POM-027          Cuff height
  S53            S53                    None             HOOD WIDTH LOCATION
  S54            S54                    None             HOOD LENGTH RELAXED
  S55            S55                    None             HOOD LENGTH EXTENDED
  S56            S.56                   None             HOOD PIECE WIDTH
  S8             S8                     None             COLLAR OPENING EXTENDED
  SR1            S.R1-M79               None             CORD LENGTH IN OUTSIDE
  SR10           LZ1                    None             BOW LENGTH
  SR11           SR11                   None             BOW LOCATION
  SR2            SR2                    None             DRAWSTRING LENGTH MEASURED AT POINT WHERE TI
  SR3            SR3                    None             DRAWSTRING CHANNEL
  SR6            S.R6                   None             LOOP LENGTH
  SR7            S.R7                   None             LOOP WIDTH
  SR8            SR8                    None             STRAP LOCATION
  SR9            SR9                    None             BOW WIDTH
  T1             T.1                    None             FRONT RISE
  T13            T13                    None             PLEAT LOCATION
  T14            T14                    None             PLEAT
  T2             T.2                    None             BACK RISE
  T5             HM L                   POM-154          Half moon length
  U              U                      None             RIB WIDTH
  U1             U1                     None             JETTING WIDTH
  U3             FLO W                  POM-074          Flounce width
  U4             U4                     None             FLOUNCE HEIGHT
  U5             FLO POS                POM-076          Flounce location
  U6             FLO EXT                POM-075          Flounce extended
  U7             U7                     None             FRILL HEIGHT
  V              V                      None             STITCHING WIDTH
  V10            EL RLX                 POM-151          Elastic relaxed
  V11            EL EXT                 POM-152          Elastic extended
  V12            V.12                   None             FOLDED
  V13            V.13-M79               None             DART LENGTH
  V14            V.14-M79               None             DART LOCATION
  V18            V18                    None             BUTTON LOCATION
  V3             V3                     None             STITCHING LOCATION
  V4             V4                     None             PIECE WIDTH
  V5             V5                     None             PIECE WIDTH EXTENDED
  V6             V6                     None             PIECE LENGTH
  V7             V7                     None             PIECE LOCATION
  W4             W4                     None             INNER POCKET OPENING
  W5             W5                     None             INNER POCKET FLAP HEIGHT
  W6             W6                     None             INNER POCKET WIDTH
  W7             W7                     None             INNER POCKET LENGTH
  W9             W9                     None             INNER POCKET LOCATION
  Y11            Y11                    None             CONTOUR HAT INSIDE ROUND
  Y12            Y12                    None             HAT HEIGHT
  Y36            Y36                    None             BAG WIDTH
  Y37            Y37                    None             BAG LENGTH

```

### Annex F — Els 85 parells (item × size_system) amb models i el seu grading

```
  jeans                × BOY_LOS_01           models=11  
      LOS Kids Boy Woven — Bottoms                   11
  jeans                × GIRL_LOS_01          models=15  
      (cap ruleset)                                  15
  jeans                × MAN_LOS_01           models=1   
      LOS Man Woven — Bottoms                        1
  jeans                × MAN_NUM_LOS_01       models=11  
      LOS Man Woven — Bottoms                        11
  jeans                × WOMAN_NUM_LOS_01     models=8   
      LOS Woman Woven — Bottoms                      8
  jeans                × YOUTH_BOY_LOS_01     models=7   
      LOS Teen Boy Woven — Bottoms                   7
  jeans                × YOUTH_GIRL_LOS_01    models=18  
      LOS Teen Girl — Bottoms                        18
  shorts               × BOY_LOS_01           models=23  
      LOS Kids Boy Woven — Bottoms                   23
  shorts               × GIRL_LOS_01          models=19  
      (cap ruleset)                                  19
  shorts               × MAN_LOS_01           models=7   
      LOS Man Woven — Bottoms                        7
  shorts               × MAN_NUM_LOS_01       models=7   
      LOS Man Woven — Bottoms                        7
  shorts               × WOMAN_LOS_01         models=13  
      LOS Woman Woven — Bottoms                      13
  shorts               × WOMAN_NUM_LOS_01     models=5   
      LOS Woman Woven — Bottoms                      5
  shorts               × YOUTH_BOY_LOS_01     models=15  
      LOS Teen Boy Woven — Bottoms                   15
  shorts               × YOUTH_GIRL_LOS_01    models=15  
      LOS Teen Girl — Bottoms                        15
  skirt_straight       × BABY_LOS_01          models=2   
      (cap ruleset)                                  2
  skirt_straight       × GIRL_LOS_01          models=1   
      (cap ruleset)                                  1
  skirt_straight       × WOMAN_LOS_01         models=5   
      LOS Woman Woven — Bottoms                      5
  skirt_straight       × WOMAN_NUM_LOS_01     models=2   
      LOS Woman Woven — Bottoms                      2
  skirt_straight       × YOUTH_GIRL_LOS_01    models=3   
      LOS Teen Girl — Bottoms                        3
  trousers             × BOY_LOS_01           models=6   
      LOS Kids Boy Woven — Bottoms                   6
  trousers             × GIRL_LOS_01          models=12  
      (cap ruleset)                                  12
  trousers             × MAN_LOS_01           models=3   
      LOS Man Woven — Bottoms                        3
  trousers             × MAN_NUM_LOS_01       models=6   
      LOS Man Woven — Bottoms                        6
  trousers             × WOMAN_LOS_01         models=12  
      LOS Woman Woven — Bottoms                      12
  trousers             × WOMAN_NUM_LOS_01     models=4   
      LOS Woman Woven — Bottoms                      4
  trousers             × YOUTH_BOY_LOS_01     models=8   
      LOS Teen Boy Woven — Bottoms                   8
  trousers             × YOUTH_GIRL_LOS_01    models=9   
      LOS Teen Girl — Bottoms                        9
  dress_simple         × GIRL_LOS_01          models=32  
      LOS Kids Girl — Dresses                        32
  dress_simple         × WOMAN_LOS_01         models=26  
      (cap ruleset)                                  26
  dress_simple         × YOUTH_GIRL_LOS_01    models=11  
      (cap ruleset)                                  11
  baby_bloomers        × BABY_LOS_01          models=32  
      (cap ruleset)                                  32
  baby_bodysuit        × NEWBORN_LOS_01       models=5   
      (cap ruleset)                                  5
  baby_dress           × BABY_LOS_01          models=25  
      (cap ruleset)                                  24
      LOSAN IBERIA SA · Newborn · LOS Baby 3-36M     1
  baby_dress           × NEWBORN_LOS_01       models=24  
      LOS New Born Knit — Onepieces                  24
  baby_leggings        × BABY_LOS_01          models=19  
      (cap ruleset)                                  19
  baby_sleepsuit       × NEWBORN_LOS_01       models=11  
      (cap ruleset)                                  11
  baby_swimwear        × BABY_LOS_01          models=20  
      (cap ruleset)                                  20
  baby_top             × BABY_LOS_01          models=43  
      LOS Baby Knit — Tops                           43
  casual_jacket        × BABY_LOS_01          models=8   
      (cap ruleset)                                  8
  casual_jacket        × BOY_LOS_01           models=5   
      (cap ruleset)                                  5
  casual_jacket        × GIRL_LOS_01          models=5   
      (cap ruleset)                                  5
  casual_jacket        × MAN_LOS_01           models=4   
      (cap ruleset)                                  4
  casual_jacket        × WOMAN_LOS_01         models=4   
      (cap ruleset)                                  4
  casual_jacket        × YOUTH_BOY_LOS_01     models=2   
      (cap ruleset)                                  2
  casual_jacket        × YOUTH_GIRL_LOS_01    models=2   
      (cap ruleset)                                  2
  swim_shorts          × BOY_LOS_01           models=12  
      (cap ruleset)                                  12
  swim_shorts          × MAN_LOS_01           models=25  
      (cap ruleset)                                  25
  swim_shorts          × YOUTH_BOY_LOS_01     models=14  
      (cap ruleset)                                  14
  swimsuit             × GIRL_LOS_01          models=13  
      (cap ruleset)                                  13
  swimsuit             × WOMAN_LOS_01         models=22  
      (cap ruleset)                                  22
  swimsuit             × YOUTH_GIRL_LOS_01    models=13  
      LOS Teen Girl Stretch — Swimwear               13
  blouse               × BABY_LOS_01          models=2   
      (cap ruleset)                                  2
  blouse               × GIRL_LOS_01          models=4   
      (cap ruleset)                                  4
  blouse               × WOMAN_LOS_01         models=14  
      (cap ruleset)                                  14
  blouse               × YOUTH_GIRL_LOS_01    models=4   
      (cap ruleset)                                  4
  hoodie               × BABY_LOS_01          models=4   
      LOS Baby Knit — Tops                           4
  hoodie               × BOY_LOS_01           models=4   
      LOS Kids Boy Knit — Tops                       4
  hoodie               × GIRL_LOS_01          models=4   
      LOS Kids Girl Knit — Tops                      4
  hoodie               × MAN_LOS_01           models=1   
      LOS Man Knit — Tops                            1
  hoodie               × NEWBORN_LOS_01       models=1   
      LOS New Born Knit — Tops                       1
  hoodie               × YOUTH_BOY_LOS_01     models=5   
      LOS Teen Boy Knit — Tops                       5
  hoodie               × YOUTH_GIRL_LOS_01    models=3   
      LOS Teen Girl Knit — Tops                      3
  polo                 × BABY_LOS_01          models=2   
      LOS Baby Knit — Tops                           2
  polo                 × BOY_LOS_01           models=2   
      LOS Kids Boy Knit — Tops                       2
  polo                 × MAN_LOS_01           models=13  
      LOS Man Knit — Tops                            13
  polo                 × WOMAN_LOS_01         models=1   
      LOS Woman Knit — Tops                          1
  polo                 × YOUTH_BOY_LOS_01     models=4   
      LOS Teen Boy Knit — Tops                       4
  polo                 × YOUTH_GIRL_LOS_01    models=1   
      LOS Teen Girl Knit — Tops                      1
  shirt_woven          × BABY_LOS_01          models=5   
      (cap ruleset)                                  5
  shirt_woven          × BOY_LOS_01           models=6   
      (cap ruleset)                                  6
  shirt_woven          × MAN_LOS_01           models=33  
      (cap ruleset)                                  33
  shirt_woven          × YOUTH_BOY_LOS_01     models=4   
      LOS Teen Boy Woven — Shirts                    4
  sweater              × BABY_LOS_01          models=4   
      LOS Baby Knit — Tops                           4
  sweater              × BOY_LOS_01           models=1   
      LOS Kids Boy Knit — Tops                       1
  sweater              × GIRL_LOS_01          models=3   
      LOS Kids Girl Knit — Tops                      3
  sweater              × NEWBORN_LOS_01       models=4   
      LOS New Born Knit — Tops                       4
  sweater              × WOMAN_LOS_01         models=6   
      LOS Woman Knit — Tops                          6
  sweater              × YOUTH_GIRL_LOS_01    models=3   
      LOS Teen Girl Knit — Tops                      3
  t_shirt              × BOY_LOS_01           models=34  
      LOS Kids Boy Knit — Tops                       34
  t_shirt              × GIRL_LOS_01          models=31  
      LOS Kids Girl Knit — Tops                      31
  t_shirt              × MAN_LOS_01           models=34  
      LOS Man Knit — Tops                            34
  t_shirt              × WOMAN_LOS_01         models=33  
      LOS Woman Knit — Tops                          33
  t_shirt              × YOUTH_BOY_LOS_01     models=33  
      LOS Teen Boy Knit — Tops                       33
  t_shirt              × YOUTH_GIRL_LOS_01    models=33  
      LOS Teen Girl Knit — Tops                      33
```

---

# P0 — DELTA DICCIONARI v3 · **EXECUTAT** 2026-07-24

> Aquesta secció conserva l'informe del dry-run (sota) i afegeix al final el bloc
> **«P0 EXECUTAT»** amb les xifres reals després de l'apply.

Script: `/root/diagnosi_losan/delta_diccionari_v3.py`.
`DELTA_APPLY=0` (defecte) executa el **mateix camí de codi** que l'apply dins `transaction.atomic()`
i fa **ROLLBACK** al final — no és una simulació, és l'operació real desfeta.
`manage.py check` → *System check identified no issues*. **Cap escriptura persistida a la BD.**

## Estat: ATURAT a la comporta del pas 2, tal com demana el brief

| pas | estat | efecte mesurat |
|---|---|---|
| 1 · Rebatejos `GC*` | ✅ **llest per aplicar** | 3 UPDATE a `los`, risc nul |
| 2 · Altes noves v3 | ⛔ **BLOQUEJAT** | 0 creacions — ambigüitat real (sota) |
| 3 · Col·lapsar notació punt | ✅ llest (dins del pas 4) | 4 parells, tots verificats |
| 4 · `pom_global` a `fhort` | ⚠️ **parcial** | **118 segurs** · 29 a revisió · 4 conflictes |
| 5 · Accessoris | ⏸ ajornat | deute anotat, res sembrat |

## Pas 1 — rebatejos: net, ancorat al `pom_global` (no al pk)

| `pom_global` | POMMaster pk | codi_client | àlies | maps | regles |
|---|---|---|---|---|---|
| LOSPOM-558 (Cuff Inner) | 568 | `GL` → **`GCI`** | `GL` → `GCI` | 0 | 0 |
| LOSPOM-559 (Cuff Height) | 570 | `GN` → **`GCH`** | `GN` → `GCH` | 0 | 0 |
| LOSPOM-560 (Cuff Difference) | 569 | `GM` → **`GCD`** | `GM` → `GCD` | 0 | 0 |

Els tres tenen **0 maps i 0 regles**: cap FK es mou, cap graduació se n'assabenta. A `fhort` aquests
tres `pom_global` **no existeixen** → el pas 1 és exclusiu de `los`. Idempotent: si ja estan
rebatejats, el script els salta.

## Pas 2 — per què està bloquejat

### 2a · GA long/short — ambigüitat real (el STOP que demanava el brief)

- A `los`, `GA` és **un sol POMMaster** (pk=567, LOSPOM-550, *SLEEVE INSEAM LENGTH*) amb **1 àlies**,
  **2 maps** (`blouse`, `t_shirt`) i **1 regla**: `LOS Man Knit — Tops`, LINEAR 0.10, `talla_base=M@MAN_LOS_01`.
- **No hi ha cap context NEWBORN per a `GA` a la BD**: cap regla, cap map, cap àlies en un ruleset de
  nadó. Les dues files «G.A long/short» del full TOP-DRESS viuen **només al màster**, no a la BD.
- Per tant **no hi ha res a rebatejar**: `GAL`/`GAS` serien **altes noves**, no un UPDATE. I no puc
  decidir des de la BD si un sol POM basta, perquè **no hi ha cap model NEWBORN que avui demani les
  dues mesures alhora** — la pregunta només la respon el màster.
- **Agreujant descobert:** a `fhort` l'àlies `GA` del Customer LOS apunta a `INS` (POM-044,
  *Inseam length* = **entrecuix de cama**), mentre que a `los` apunta a *SLEEVE INSEAM LENGTH*
  (**màniga**). El mateix codi significa dues coses diferents als dos schemas.

### 2b · 6 dels 7 grups d'altes duplicarien mesures que ja existeixen amb regles vives

El brief deia «codis lliures verificats pel cens — cap col·lisió». Els **codis** sí que estan
lliures; les **mesures**, no. Crear-los trencaria la llei del fil que el mateix brief invoca:

| alta proposada | ja existeix com a | maps | regles | veredicte |
|---|---|---|---|---|
| `GS` (sleeve length short) | **`G.3`** LOSPOM-680 *SLEEVE SHORT LENGTH* | 0 | **2** | → **REBATEIG**, no alta |
| `H11S` (sleeve opening short) | **`H.12`** LOSPOM-681 *SLEEVE SHORT OPENING* | 0 | **2** | → **REBATEIG**, no alta |
| `GL` nou (sleeve length long) | `SL` POM-020 *Sleeve length* (àlies `G`) | 36 | 8 | duplicat |
| `H11L` (sleeve opening long) | `SL OP` POM-025 (àlies `H11`) | 33 | 8 | duplicat |
| `FL`/`FS` (leg opening) | `LEG OP` POM-043 (àlies `F`) + F1/F2/F5/F6 | 15 | 4 | duplicat (i `FS` ja ocupat a `fhort` → `SK L`) |
| `MT`/`MD`/`ML`/`MS`/`MB`/`MO` | `M-M79` LOSPOM-389 *TOTAL LENGTH* (àlies `M`) | 16 | **18** | fragmentaria el POM més graduat del tenant |
| `T1W`/`T1H`/`T2W`/`T2H` | `RI FR` POM-055 (`T1`) · `RI BK` POM-056 (`T2`) | 17+17 | 8+7 | eix nou real (punt de referència), però cap ruleset el demana avui |
| `D11H`/`D11W` | `D.11-M79` LOSPOM-386 *HIP LOCATION* (àlies `D11`) | 7 | **8** | **la premissa no es compleix** (sota) |
| `D11RH`/`D11RM`/`D11RL` | — (cap equivalent) | — | — | únic grup sense duplicat |

**`D11` — la premissa del brief no es compleix.** El brief autoritzava crear `D11H`/`D11W` «només si
el ruleset que els necessita (Woman Knit—Tops) exigeix dos valors simultanis». He bolcat les 17
regles de `LOS Woman Knit — Tops`: **`D11` no hi és**. `D.11-M79` té 8 regles, però totes en altres
contenidors (Kids Boy/Man/New Born ×2/Teen Boy/Teen Girl ×2/Woman **Woven** — Bottoms). Cap ruleset
del tenant demana avui dos valors de D11 alhora.

### 2c · El motiu de fons: hi ha àlies mal cablejats que una alta no arregla

Vegeu §5.2 (corregida). A `los`, `BIC` (34 maps, 10 regles) porta penjat `H19`=SLEEVE MOTIVE
LOCATION, i `ELB` (31 maps) porta `SR9`=BOW WIDTH. Sembrar codis nous **al costat** d'aquests POM
deixaria el defecte intacte i afegiria un tercer nom per a la mateixa cosa.

## Passos 3+4 — `pom_global` a `fhort`: 118 de 155, amb comporta

Xifres reals mesurades (el brief deia 154; el número exacte és **155** sense `pom_global`, dels quals
**151** tenen equivalent a `los`):

| categoria | n | acció |
|---|---|---|
| ✅ nom del POM **idèntic** als dos schemas | **118** | reparats (copiar `pom_global.codi` de `los`) |
| ═ ja coincidien | 24 | res |
| ⚠️ nom **diferent** → comporta activada | **29** | **NO tocats**, a revisió humana |
| ⛔ `fhort` ja té un global **diferent** | 4 | **NO tocats** (`D`, `GA`, `J1`, `S28`) |

Els **4 parells de notació** del pas 3 (`C13`↔`C.13`, `E9`↔`E.9`, `SR6`↔`S.R6`, `SR7`↔`S.R7`) estan
tots **dins dels 118**: mateixa descripció, `POMGlobal` destí ja existent a `fhort`, cap altre
customer els comparteix. **No cal crear cap duplicat a `fhort`.**

**Cap `POMGlobal` s'ha de crear**: els 118 destins ja existeixen al schema `fhort`.
**Cap dels 220 POMMaster de `fhort` aliens a LOS es toca.**

### Per què la comporta de noms no estava al brief i l'he afegida

El brief autoritzava copiar el `pom_global` dels 154 «verificat 0 divergències semàntiques». Aquella
verificació era meva i **era incompleta** (§5.2, correcció). Sense la comporta, el delta hauria
estampat el `pom_global` de `los` sobre POMMaster de `fhort` que són una **altra** mesura — per
exemple `SR10` (a `fhort` *BOW LENGTH*, a `los` *ELBOW LENGTH*) o `V3` (*STITCHING LOCATION* vs
*RUFFLE HEIGHT*). Són 9 casos de contradicció real dins dels 29 retinguts; els altres 20 són
sinònims (*Across front* ↔ *FRONT WIDTH*) que probablement es poden alliberar a mà.

## Pas 5 — accessoris: deute anotat

`Y11`/`Y12`/`Y36`/`Y37` (barret, bossa) segueixen només a `fhort`. A `los` els 3 items d'ACCESSORIES
(`bag`, `hat_cap`, `scarf`) tenen **0 maps i 0 models** (§7 Z3): sembrar-los avui seria vocabulari
sense consumidor. **No s'ha tocat res.**

## Auditoria SQL (post-rollback, confirma que no s'ha escrit)

```
los   · POMMaster dels 3 rebatejos: [('LOSPOM-558','GL',568), ('LOSPOM-559','GN',570), ('LOSPOM-560','GM',569)]
los   · àlies dels 3 rebatejos:     [('GL','GL'), ('GM','GM'), ('GN','GN')]
fhort · àlies LOS: amb global=28 · SENSE global=155 · total=183
fhort · POMMaster sense global a tot el schema: 239
```

Estat idèntic al d'abans del dry-run. ✔


---

# P0 EXECUTAT — 2026-07-24 (apply amb vistiplau d'Agus)

`manage.py check` verd abans de l'apply · `DELTA_APPLY=1` · un sol `transaction.atomic()` ·
auditoria per SELECT directe després · **re-execució en dry-run = 0 escriptures** (idempotència
verificada).

## Pas 1 — 7 rebatejos (schema `los`), cap FK moguda

| pom_global | pk | codi_client | àlies resultants | maps | regles |
|---|---|---|---|---|---|
| LOSPOM-558 | 568 | `GL` → **`GCI`** | `GCI` | 0 | 0 |
| LOSPOM-559 | 570 | `GN` → **`GCH`** | `GCH` | 0 | 0 |
| LOSPOM-560 | 569 | `GM` → **`GCD`** | `GCD` | 0 | 0 |
| LOSPOM-680 | 565 | `G.3` → **`GS`** | `GS` | 0 | **2 conservades** |
| LOSPOM-681 | 572 | `H.12` → **`H11S`** | `H11S` + `H12` (sinònim) | 0 | **2 conservades** |
| POM-020 | 683 | `SL` → **`GL`** | `GL` (era `G`) | **36** | **8 conservades** |
| POM-025 | 685 | `SL OP` → **`H11L`** | `H11L` (era `H11`) | **33** | **8 conservades** |

Ordre respectat: `GL`→`GCI` abans de `SL`→`GL`. Tots els pk i totes les FK intactes.

> **Decisió presa sobre la marxa:** `H.12` tenia **dos** àlies (`H.12` i `H12`) i la constraint
> `uniq_customer_client_code` no permet que tots dos passin a ser `H11S`. S'ha rebatejat el canònic
> (`H.12` → `H11S`) i s'ha **deixat viu `H12`** com a sinònim legacy apuntant al mateix POM: cap
> pèrdua, els dos codis segueixen resolent.

## Pas 2 — 3 altes netes (D11R*), la resta descartada

| codi | pk | pom_global | nom | àlies |
|---|---|---|---|---|
| `D11RH` | 735 | **LOSPOM-685** | HIGH RISE | `D11RH` |
| `D11RM` | 736 | **LOSPOM-686** | MID RISE | `D11RM` |
| `D11RL` | 737 | **LOSPOM-687** | LOW RISE | `D11RL` |

`actiu=True`, `pendent_revisio=False` (validats per Montse), `origen_import='diccionari v3 P0 2026-07-24'`.
Descartats: `GAL/GAS`, `FL/FS`, `MT/MD/ML/MS/MB/MO`, `D11H/D11W` (→ condició d'entrada de **P2**),
i `GL/GS/H11L/H11S` (resolts com a rebateig).

## Passos 3+4 — `pom_global` a `fhort`

| | abans | després |
|---|---|---|
| POMMaster dels àlies LOS **amb** `pom_global` | 28 | **146** |
| POMMaster dels àlies LOS **sense** | 155 | **37** |
| POMMaster sense `pom_global` a **tot** el schema `fhort` | 239 | **121** |

**118 reparats** exactes (146−28 = 239−121 = 118). Retinguts per la comporta: **29 a revisió**
(nom diferent) + **4 conflictes** (`D`, `GA`, `J1`, `S28`). Cap `POMGlobal` creat; cap dels 220
POMMaster de `fhort` aliens a LOS tocat.

## Xifres finals del tenant `los`

| | abans | després | Δ |
|---|---|---|---|
| POMMaster | 246 | **249** | +3 |
| POMGlobal `LOSPOM-*` | 149 | **152** | +3 |
| CustomerPOMAlias (self) | 196 | **199** | +3 |
| **GradingRule** | 402 | **402** | **0** ✔ |
| GradingRuleSet | 19 | **19** | 0 |
| GarmentPOMMap | 1.748 | **1.748** | 0 |

**Cap regla, cap map i cap ruleset s'ha mogut.** Els rebatejos només han canviat noms; les 20 regles
que pengen dels 7 POM rebatejats (2+2+8+8) segueixen totes al seu lloc.

## Deute anotat (no fet avui)

1. **29 codis a revisió** a `fhort` (`pom_global` retingut per nom diferent): 9 són contradiccions
   reals (`H7`, `H19`, `SR9`, `SR10`, `S22`, `S44`, `V`, `V3`, `V18`), ~20 són sinònims.
2. **4 conflictes durs** (`D`, `GA`, `J1`, `S28`) — decisió humana.
3. **Àlies mal cablejats a `los`** (§5.2): `BIC`+`H19`, `ELB`+`SR9`, `V`+`V3`+`V18`, `S`+`S22`+`S44`.
4. **Accessoris** (`Y11`/`Y12`/`Y36`/`Y37`) no sembrats a `los`.
5. **`D11H`/`D11W`** — condició d'entrada de P2: crear-los només si el fill-holes topa amb les dues
   files D11 (HPS i waist) dins d'un sol contenidor.

---

# P0b — RENAME DE TARGETS · **CENS PREVI (Patró A). NO EXECUTAT.**

Read-only. **Cap escriptura.** Tres condicions de STOP del brief s'han disparat; la tercera és
bloquejant per si sola.

## 1. Cens: on viu el codi de target

### 1a. A la BD — `Target` existeix als TRES schemas, amb les mateixes pk

| lloc | com hi viu | conseqüència del rename |
|---|---|---|
| `pom.Target.codi` | **valor literal**, 13 files **per schema** (`public`, `fhort`, `los`) | és l'únic UPDATE real |
| `SizeSystem.targets` (M2M) | per **`target_id`** | ✔ segueix sol, no cal tocar-la |
| `GradingRuleSet.targets` (M2M) | per **`target_id`** | ✔ segueix sol |
| `SizingProfile.target` (FK) | per **`target_id`** | ✔ segueix sol |
| **`models_app.Model.target`** | **`CharField(max_length=30)` amb el codi literal, sense `choices`** | ✘ **cal UPDATE de cadena** |

### 1b. Ús per target i per schema

| codi | `los`: SS / RS / Prof / **Model.target** | `fhort`: SS / RS / Prof / **Model.target** | `public`: SS / RS |
|---|---|---|---|
| WOMAN | 2 / 2 / 2 / **155** | 8 / 16 / 14 / **50** | 4 / 8 |
| MAN | 2 / 2 / 2 / **145** | 4 / 8 / 4 / **1** | 2 / 2 |
| GIRL → `KID_GIRL` | 2 / 2 / 2 / **139** | 3 / 5 / 4 / **1** | 1 / 1 |
| BOY → `KID_BOY` | 1 / 2 / 2 / **104** | 1 / 3 / 4 / 0 | 0 / 0 |
| TEEN_GIRL | 1 / 3 / 3 / **115** | 2 / 7 / 5 / 0 | 1 / 1 |
| TEEN_BOY | 1 / 3 / 3 / **92** | 1 / 4 / 5 / 0 | 0 / 0 |
| TODDLER_GIRL → `BABY_GIRL` | 1 / 2 / 1 / **88** | 2 / 3 / 3 / 0 | 1 / 1 |
| TODDLER_BOY → `BABY_BOY` | 1 / 1 / 0 / **78** | 1 / 2 / 2 / 0 | 0 / 0 |
| BABY_GIRL → `NEWBORN_GIRL` | 1 / 3 / 3 / **26** | 3 / 4 / 3 / 0 | 2 / 1 |
| BABY_BOY → `NEWBORN_BOY` | 1 / 3 / 0 / **19** | 1 / 4 / 2 / 0 | 0 / 0 |
| **BABY_UNISEX** → ? | 1 / 3 / **0** / **0** | 1 / 4 / **3** / 0 | 0 / 0 |
| *UNISEX_ADULT* (fora del mapeig) | 0 / 0 / 0 / 0 | 1 / 0 / 0 / 0 | 1 / 0 |
| *MATERNITY* (fora del mapeig) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 |

**Total de referències a targets a `los` que el rename ha de conservar:**
`Target` 10 files · `SizeSystem.targets` 12 · `GradingRuleSet.targets` 26 · `SizingProfile.target` 18 ·
**`Model.target` 961 cadenes**.

Cap valor de `Model.target` a `los` cau fora del mapeig (els 10 codis, ni un `BABY_UNISEX`).
A `fhort` n'hi ha 52 (`WOMAN` 50, `GIRL` 1, `MAN` 1). **Cap STOP per valor desconegut.**

### 1c. Al CODI — vocabulari hardcoded

| fitxer | què hi ha |
|---|---|
| `backend/fhort/pom/models.py:836-848` | **`Target.CODI_CHOICES`** — els 13 codis literals |
| `frontend/src/components/grading/gradingAxes.js:10-23` | **`TARGETS`** — l'enum del wizard |
| `frontend/src/i18n/{ca,en,es}.json:930-942` | claus `target_<CODI>` ×13 ×3 idiomes |
| `backend/.../seed_data/losan_ss27.py`, `losan_grading_v3.py` | llavors amb codis literals |
| `backend/.../management/commands/seed_kids_baby_target_map.py`, `seed_baby_months_profiles.py` | llavors |
| `backend/fhort/pom/migrations/0004`, `0009` | històric — **no s'han de tocar** |

**Bona notícia sobre Onada 1/2:** el vocabulari del frontend **està unificat**. `TARGETS` viu
NOMÉS a `gradingAxes.js` i el consumeixen `ModelWizard`, `GradingRuleSets` (TargetPills),
`SizingProfileSelector` i `CascadeSelector` per import, sense cap còpia privada. **No s'ha trobat cap
superfície amb vocabulari propi** — el forat del 2026-07-19 segueix tapat. L'única còpia paral·lela
són les claus i18n, que són etiquetes, no enums.

## 2. BABY_UNISEX — dades per decidir (STOP del brief, sense decidir)

| | `los` | `fhort` |
|---|---|---|
| `SizeSystem` que el declaren | 1 (`NEWBORN_LOS_01`) | 1 |
| `GradingRuleSet` que el declaren | **3** (els tres New Born) | 4 |
| **`SizingProfile` que l'usen** | **0** | **3** |
| **`Model.target`** amb aquest valor | **0** | 0 |

A `los` **cap model i cap perfil** el fan servir: viu només com a declaració als 3 contenidors New
Born i al sistema de talles. És vocabulari **declarat però no consumit**.

- **(a) repartir-lo** en `NEWBORN_BOY` + `NEWBORN_GIRL`: a `los` no perd res (0 perfils, 0 models);
  els 3 rulesets passarien de 3 targets a 2, tots dos ja declarats. **A `fhort` sí que costa**: 3
  SizingProfiles l'usen com a FK i caldria duplicar-los o reassignar-los.
- **(b) mantenir `NEWBORN_UNISEX`**: conserva l'expressivitat de «peça de nadó sense gènere», que és
  un cas real de producte, i no toca res a `fhort`. Contra: LOSAN diu que parla 10 targets, i això en
  faria 11.

**No decidit.** Cal la teva paraula.

## 3. STOP bloquejant — el rename de BD sol trencaria el wizard

`Target.codi` té `choices=CODI_CHOICES` **al codi**, i el frontend itera la constant `TARGETS`
**hardcoded**. Si la BD passa a dir `KID_BOY` i el codi segueix dient `BOY`:

- els selectors de target (`TARGETS.map(...)`) **no pintarien cap opció** per als 8 codis renombrats
  — `TargetPills`, la cascada del wizard i `SizingProfileSelector` es quedarien sense aquests targets;
- `availableTargetCodes()` retornaria codis que no són a `TARGETS` → cap pill s'encendria;
- el matching per eixos (`matchesTarget`) compara `targets_codis` amb el valor del selector: sense
  opció seleccionable, **cap ruleset casaria** (avui la prova del cotó dona 1 de 1, §6.2);
- `Target.CODI_CHOICES` quedaria mentint (no bloqueja `.update()`, però sí `full_clean()`/DRF).

`Model.target` **no** té `choices`, així que aquell UPDATE no toparia amb validació — però tampoc
protegeix de res.

**Conclusió:** el rename **no és una operació de dades**, és un canvi de codi + dades que ha d'anar
junt. L'ordre correcte és: *codi a `dev` → merge → deploy → rename de BD dins la mateixa finestra*.
Fer només la BD, avui, a PROD amb la Montse treballant, deixaria el wizard sense targets.

## 4. Tercer STOP — abast: `fhort` no és de LOSAN

`Target` té files pròpies **a cada schema**, i `fhort` en fa un ús intens **per a les seves pròpies
dades** (14 perfils WOMAN, 16 rulesets, 52 models amb literal). Renombrar-hi `GIRL`→`KID_GIRL` i
`BABY_*`→`NEWBORN_*` imposa el vocabulari de LOSAN al tenant de FHORT.

Però renombrar **només a `los`** trenca la premissa d'un enum únic: el frontend té UNA constant
`TARGETS` per a tots els tenants, i llavors o bé `los` o bé `fhort` quedaria amb codis fora de
l'enum — exactament la classe de bug del 2026-07-19.

**No hi ha opció «només `los`» que no reobri aquell forat.** O es renombra a tot arreu (i FHORT
adopta el vocabulari de LOSAN), o no es renombra.

## 5. Què cal per desbloquejar

1. **Decisió BABY_UNISEX** (a) o (b).
2. **Decisió d'abast**: renombrar als 3 schemas (i assumir que FHORT canvia de vocabulari) o parar.
3. **Canvi de codi a `dev`** (fora de l'abast d'aquest brief i impossible des de PROD):
   `Target.CODI_CHOICES`, `gradingAxes.js:TARGETS`, les 39 claus i18n, i les 4 llavors.
   Amb això desplegat, el rename de BD és 10 UPDATE de `Target.codi` + 961 de `Model.target` a `los`
   (+52 a `fhort`), amb la taula intermèdia `_TMP_*` de l'ordre A→B→C→D del brief.

El script d'execució (amb l'ordre A→B→C→D i l'auditoria SQL) es pot escriure en 20 minuts un cop
resoltes 1 i 2; no l'escric abans perquè l'ordre depèn de la decisió d'abast.

---

# P0b — DECISIONS PRESES, EXECUCIÓ AJORNADA (2026-07-24)

## Decisions

| tema | decisió |
|---|---|
| **`BABY_UNISEX`** | **opció (b)** — es manté un target unisex propi de nadó, renombrat a **`NEWBORN_UNISEX`**. No es reparteix. `fhort` conserva els seus 3 SizingProfiles sense tocar-los. |
| **Abast** | **rename als TRES schemas** (`public`, `fhort`, `los`), tractant `Target` com el **catàleg compartit** que és. FHORT adopta el vocabulari de LOSAN. |

Vocabulari final: 11 targets vius (els 10 de LOSAN + `NEWBORN_UNISEX`) i 2 que no es toquen
(`UNISEX_ADULT`, `MATERNITY`).

## Motiu de l'ajornament

El rename **no és una operació de dades**. El vocabulari també viu hardcoded a
`Target.CODI_CHOICES`, `gradingAxes.js:TARGETS`, les 39 claus i18n (`ca`/`en`/`es`) i 4 llavors.
Amb la BD renombrada i el codi sense desplegar, el wizard es queda **sense targets seleccionables**
(§P0b.3).

Aquest canvi de codi ha de seguir el camí normal — **`dev` → staging → validació visual → merge →
deploy fet per l'Agus** (llei de push). El **rename de BD s'executa a la MATEIXA finestra que el
deploy**, en sessió pròpia i amb l'Agus present.

## Estat de la BD

**Cap escriptura feta en aquesta fase.** Zero canvis respecte de l'últim estat verd (el commit de
P0). Verificat: els 13 `Target.codi` segueixen amb el vocabulari antic als tres schemas.

## Volum previst del rename (quan toqui)

| taula | `public` | `fhort` | `los` |
|---|---|---|---|
| `Target.codi` | 10 files | 10 files | 10 files |
| `Model.target` (literal) | *(sense taula)* | 52 | **961** |
| M2M i FK (`SizeSystem`/`GradingRuleSet`/`SizingProfile`) | — | — | — *(per `target_id`, segueixen soles)* |

## Script — **escrit i llest, NO executat**

`/root/diagnosi_losan/rename_targets_p0b.py` · sintaxi validada · `manage.py check` verd.

- Ordre **A→B→C→D** amb temporals `_TMP_*`, tal com es va definir. `BABY_UNISEX` també passa pel
  temporal tot i no col·lisionar: la família nadó es mou sencera amb el mateix patró (una excepció
  «perquè aquesta no cal» és on s'esmuny un error).
- Un sol `transaction.atomic()` **per als tres schemas**: o hi entren tots o cap.
- **Guards que aturen l'execució** (`SystemExit`, dins l'atòmic → rollback):
  1. qualsevol valor de target fora del mapeig → STOP, mai inventar-ne cap;
  2. temporals `_TMP_*` residuals d'una execució avortada → STOP;
  3. el recompte de referències per taula ha de ser **idèntic abans i després** → si divergeix, STOP.
- Idempotent (si el codi vell ja no hi és i el nou sí, salta) i amb **auditoria SQL directa** final.
- `DELTA_APPLY=0` (defecte) executa el mateix camí i fa ROLLBACK.

Recordatori escrit al capdamunt del propi script: **no executar-lo abans que el codi estigui
desplegat.**

## Checklist per a la sessió d'execució

1. Codi a `main` i desplegat (backend + `npm run build` + reload) — **fet per l'Agus**.
2. `manage.py check` verd.
3. `DELTA_APPLY=0` → revisar la foto prèvia/posterior i l'auditoria.
4. `DELTA_APPLY=1` → apply.
5. Re-executar en dry-run: ha de dir «ja fet» a tot.
6. Verificació visual als 4 consumidors de `TARGETS`: **ModelWizard**, **GradingRuleSets**
   (TargetPills), **SizingProfileSelector**, **CascadeSelector** — que hi surtin els 10 targets i
   que cap mostri `BOY`/`GIRL`/`TODDLER_*`/`BABY_*` amb el significat antic.
7. Prova del cotó de §6.2: els combos han de seguir retornant **exactament 1** ruleset.

---

# P1→P6 · ESTAT D'EXECUCIÓ (2026-07-24)

## P3 PAS 0 — el gate dur: RESOLT, el motor SÍ suporta el sostre

Verificat executant `pom/services.py::_apply_rule` sobre runs de prova (no per lectura). Fet complet
i taules a `DECISIONS.md`. Resum:

- `increment_break=0` **explícit** dona sostre real: la línia `brk = float(increment_break) if
  increment_break is not None else ib` distingeix **0** de **None**.
- **⚠️ off-by-one**: `talla_break_label` és la **primera talla ja plana**, no l'última que creix.
  L'especificació de P3 («D22 i M(long) plans a partir de M → `talla_break_label='M'`») faria que la
  **M valgués igual que la base S**. Per «creix fins a M i després pla» cal `'L'`.
  **A confirmar amb la Montse abans d'aplicar cap FORM.**
- El break s'ancora per etiqueta contra el run del **model**; si l'etiqueta no hi és, degrada a
  lineal pura **en silenci**.

Per la regla del brief, el gate passa i P3 continuaria — però el CONTINGUT de P3 (els valors del
màster WOMAN) no és accessible (§blocador 1).

## P4 — EXECUTAT (5 operacions, totes soft, idempotent verificat)

| # | operació | resultat |
|---|---|---|
| 1 | Ruleset residual (pk=55) | model pk=192 → `grading_rule_set=NULL` + Watchpoint `GRADING_PENDENT`; ruleset → `actiu=False` (les 12 regles es conserven) |
| 2 | `SizeSystem GIRL_LOS_03` | → `actiu=False` (0 rulesets/profiles/models confirmat abans de tocar) |
| 3 | `GarmentTypeItem.name` | **62 → 0** buits. Títol pla del `code`; única excepció `t_shirt` → «T-Shirt» |
| 4 | SizingProfile BABY_BOY + BABY_UNISEX | **+6** (2 targets × 3 rulesets New Born), mirall exacte dels de BABY_GIRL |
| 5 | GarmentGroup buits | 4 → `actiu=False` (`DRESSES-FULL`, `KNITWEAR`, `TOPS-KNIT`, `TOPS-WOVEN`) |

Auditoria SQL: RuleSets 18 actius + 1 inactiu · SizeSystem 10 + 1 · GarmentGroup 8 + 4 ·
items sense nom 0 · SizingProfile 24 · models sense grading 382 · Watchpoints `GRADING_PENDENT` 1.

## P6 — QA parcial, tot verd

| invariant | esperat | real |
|---|---|---|
| regles a POM `actiu=False` | 0 | **0** ✔ |
| regles sense `pom_global` | 0 | **0** ✔ |
| `talla_base` fora del `size_system` del ruleset | 0 | **0** ✔ |
| **SizeSystem actius** | **10** | **10** ✔ |
| `GarmentTypeItem` sense nom | 0 | **0** ✔ |
| parells (item×system) amb 2+ rulesets no nuls | 0 | **0** ✔ (53 parells amb grading) |

Models amb/sense grading: **579 / 382** (baseline 580/381 → delta −1/+1, exactament el model del
ruleset residual).

**Prova del cotó** (rèplica de `gradingAxes.js:180`) — i ara també per a `BABY_BOY`, que abans no
tenia perfil:

| combo | profiles | rulesets |
|---|---|---|
| BABY_GIRL + KNIT + NEWBORN · `baby_top` | 3 | **1** ✔ |
| BABY_GIRL + KNIT + NEWBORN · `baby_leggings` | 3 | **1** ✔ |
| **BABY_BOY** + KNIT + NEWBORN · `baby_top` | 3 | **1** ✔ *(nou, gràcies a P4.4)* |

El combo Woman+WOVEN+Bottoms Alpha no es pot provar: P1 no s'ha executat.

## BLOCADOR 1 — P1, P2 i P3-FORM: els documents font no existeixen

| document | citat a | estat al servidor |
|---|---|---|
| `GRADING_SOURCES_LOSAN.md` (§TANDA 10, 11) | P1, P2, P3 | **NO EXISTEIX** (cercat a tot el disc) |
| `FIL_NOMENCLATURA_GRADING_LOSAN.md` | P2 | **NO EXISTEIX** |
| `DELTA_GRADING_MASTER_LOSAN.md` | P2, P4 | **NO EXISTEIX** |

Sense els màsters no hi ha els increments (`C=3/3`, `D1=2.1/2.6`, les taules TOP-DRESS/BOTTOM…).
El propi brief ho prohibeix: «Aplicar 1-a-1 contra la taula del màster, **mai per inferència**».
Inventar-los posaria mesures falses en un PLM viu. **P1, P2, P3-FORM i P5 queden sense executar.**

Conseqüències anotades:
- El **watchpoint `MAN_ALPHA_BOTTOMS_SENSE_FONT`** (11 models) era part de P1 → **no creat**.
- L'**invariant de sortida de P1** (0 models amb size_system alfa i ruleset numèric, excepte els 11)
  **no es compleix**: segueixen els 41 de Z5 (30 dona + 11 home).
- `INFORME_DIVERGENCIES_NEWBORN_MONTSE.md` (P2) **no s'ha generat**.
- **P5** no té càrrega: no hi ha res nou de P1/P2 per replicar a `fhort`.

## BLOCADOR 2 — git: `dev` local és estantís

`dev` local és de **2026-07-14**, **1.351 commits enrere** de main, i té **1 commit propi no
fusionat** (`61d2724`, seed Brownie FW26). `origin/dev` (2026-07-24, `5231dac`) sí que és al dia i
ja està contingut a main.

**No s'ha tocat `dev` local** (perdria aquell commit). El treball va a la branca
**`losan/p0-p4-onboarding`**, creada sobre `origin/dev` en un **worktree separat** (`/root/dev-work`)
perquè l'arbre de PROD no es mogui. **Commit `88ebf08`. Cap push.**

## NOTA — `main` s'ha mogut durant la sessió

L'Agus ha fusionat `origin/dev` a `main` a les **08:48** (13 commits, P7 federació):
`4e32fe3` → `5a0e097`. Deploy verificat sa: **0 migracions pendents** als 3 schemas, `fhort.service`
actiu, `dist` reconstruït a les 08:48 — i losan el rep automàticament gràcies al canvi de vhost
d'aquest matí. Cap interferència amb el treball de dades d'aquesta sessió.

---

# P1/P2/P3 amb els màsters a disc — 2026-07-24 (2a tanda)

Els tres màsters ja viuen al repo (`docs/diagnosis/GRADING_SOURCES_LOSAN.md`,
`DELTA_GRADING_MASTER_LOSAN.md`, `FIL_NOMENCLATURA_GRADING_LOSAN.md`).

## P2 — EXECUTAT (part additiva)

**15 regles noves, LINEAR pur.** Regles del tenant: **402 → 417**.

| contenidor | abans | després |
|---|---|---|
| New Born Tops | 37 | **43** |
| New Born Bottoms | 20 | **22** |
| New Born Onepieces | 38 | **45** |

Invariant de P2 verificat: **creixement net, cap substitució** (assert dins l'atòmic).
11 divergències **no escrites** + subtaula T-SHIRT + `S44` retingut →
`INFORME_DIVERGENCIES_NEWBORN_MONTSE.md`.

**Validació prèvia del mapeig** (abans d'escriure res): dels codis del màster que resolen a un POM
real, **25 coincidien exactament** amb la BD (13 Tops + 5 Bottoms + 7 Onepieces). Això és el que em
va donar confiança per sembrar; sense aquesta coincidència no hauria escrit.

### Condició d'entrada — veredictes
`D11H`/`D11W`, `T1W`/`T1H`, `T2W`/`T2H`, `ML`/`MS`/`MB`/`MO`: **conflicte real confirmat** dins d'un
sol full → autoritzats. **No creats encara**: són POMs nous i el brief deia «reporta la decisió
presa». `MT`/`MD` i `FL`/`FS`: sense conflicte → no crear.
`GAL`/`GAS`: conflicte al màster **però contradiu la decisió explícita de naixement mandrós** → no creats.

## P1 — ⛔ ATURAT (STOP definit pel propi brief) + validació fallida

### STOP 1 · dos valors simultanis sobre un sol POM
El brief deia: *«si calen dos valors simultanis pel mateix model, STOP i reportar»*. A BOTTOM ALFA:

| màster | valor | POM únic disponible |
|---|---|---|
| `F(long)` | 0.5/0.5 | `LEG OP` |
| `F(short)` | **2.1/2.6** | `LEG OP` ← **el mateix** |
| `M(long)` | 0.5→pla | `M-M79` |
| `M(short)` | **1/1** | `M-M79` ← **el mateix** |

`GradingRule` té `unique_together=(rule_set, pom)`: **és físicament impossible** encabir els dos
valors. `FL`/`FS`/`ML`/`MS` no existeixen (discard a P0).

### STOP 2 · el mapeig NO valida contra el ruleset germà
Contrastant **BOTTOM NUMÈRIC** del màster amb el ruleset numèric que ja existeix (id=54,
`WOMAN_NUM_LOS_01`, base 38) — el seu equivalent directe:

| màster | POM | esperat | a la BD | |
|---|---|---|---|---|
| `C` | `WA` | 2 | 2.00 | ✔ |
| `D` | `HI PA` | 2 | 2.00 | ✔ |
| `D22` | `D22` | 0.5 | 0.50 | ✔ |
| `D2` | `KNE` | 0.7 | 0.70 | ✔ |
| `F(long)` | `LEG OP` | 0.5 | 0.50 | ✔ |
| `M(long)` | `M-M79` | 0.5 | 0.50 | ✔ |
| **`D1`** | `THI` | **1.3** | **1.00** | ✘ |
| **`T1`** | `RI FR` | **0.7** | **0.80** | ✘ |
| **`T2`** | `RI BK` | **0.9** | **1.30** | ✘ |

**6 de 9 quadren, 3 no.** O el meu mapeig de `D1`/`T1`/`T2` és erroni, o el ruleset numèric viu
divergeix del màster. En qualsevol cas **no puc sembrar l'Alpha amb aquests tres valors** sense
saber quin mana — i `T1`/`T2` són justament dos dels que P1 em demanava sembrar.

### STOP 3 · repuntar els 30 models seria una regressió
El ruleset numèric id=54 té **24 regles**; el màster BOTTOM ALFA només menciona **10 POMs**. Els 15
POMs que el màster no menciona (`BR`, `CL`, `D.11-M79`, `O20`, `O25`, `O29`, `O30`, `O.21-M79`,
`O.32-M79`, `R9`, `S.R6`, `S.R7`, `S13`, `S25`, `WB H`) **desapareixerien** per als 30 models
repuntats. Repuntar-los a un contenidor més pobre és perdre graduació.

**No s'ha creat cap ruleset, cap regla, cap perfil, i no s'ha repuntat cap model.**
El watchpoint `MAN_ALPHA_BOTTOMS_SENSE_FONT` tampoc: era el pas final de P1.

## P3 — FORM ajornat

El **gate** (PAS 0) ja estava resolt i ara està corregit a `DECISIONS.md` amb la teva confirmació
(`label='L'`, no `'M'`). Però:

- El **FORM de Woman Bottoms Alpha** depèn del ruleset que P1 no ha pogut crear.
- El **FORM de Woman Knit — Tops** (id=53) sí que és executable en principi, però el màster
  WOMAN TOP/DRESS REGULAR té `G(long)=1/0`, `L3=0.5/0`, `L4=0.5/0`, `K1=0.2/0`, `L5=0.2/0` — cinc
  POMs amb **segona columna 0**, o sigui **sostres**. I el màster diu «break a 2XL». Amb la
  semàntica verificada, `talla_break_label='2XL'` vol dir que **la 2XL ja és plana** (=XL). Si la
  intenció és «creix fins a 2XL i després pla», el label ha de ser `'3XL'`.
  **Exactament l'ambigüitat que acabes de corregir per a Bottoms, sense resoldre per a Tops.**

## STOP SEPARAT — l'off-by-one retroactiu dels 6 contenidors amb break

Patró A read-only. **Res tocat.**

| contenidor | run | break | posició | 2a columna |
|---|---|---|---|---|
| Kids Boy Knit — Tops | 2…11/12 | `9/10` | 7/8 | 15 `>base` · **1 = 0** · 1 `<base` |
| Kids Boy Woven — Bottoms | 2…11/12 | `9/10` | 7/8 | 17 `>base` · **7 = 0** · 1 igual |
| Kids Girl — Dresses | 2…11/12 | `9/10` | 7/8 | 15 `>base` · **3 = 0** |
| Kids Girl Knit — Tops | 2…11/12 | `9/10` | 7/8 | 15 `>base` · **1 = 0** · 1 `<base` |
| Teen Girl — Bottoms | 8…16 | `14` | 3/4 | 7 `>base` · 4 iguals · **1 = 0** |
| Teen Girl Knit — Tops | 8…16 | `14` | 3/4 | 12 `>base` · 9 iguals · 1 `<base` |

**Conclusió: NO és un bug generalitzat.** Per a la gran majoria (81 regles amb `break > base`) el
label és **correcte**: les talles compostes (`9/10`, `11/12`) creixen el doble, i el pas que hi
**arriba** ha de fer servir el segon valor. Coincideix amb el màster KIDS (`0.7/1.5` ≈ ×2).

**Però hi ha 13 regles amb `increment_break = 0`** (sostre) repartides en 5 dels 6 contenidors. En
aquestes, i només en aquestes, l'off-by-one **sí** que aplica: el creixement s'atura una talla abans
del que una lectura natural de «break a 9/10» faria esperar.

**Pendent de la Montse**, com vas dir. No barrejat amb el FORM de Woman.

## P4 / P5 / P6

- **P4** ja executat a la tanda anterior.
- **P5** (mirall a `fhort`): les 15 regles noves de P2 són replicables, però **P1 no ha produït res**
  i el gruix del mirall depenia d'ell. Ajornat fins que P1 es desbloquegi, per no fer dos passos.
- **P6** recalculat sota.

## P6 — invariants recalculats DESPRÉS de P2

| invariant | esperat | real |
|---|---|---|
| regles a POM `actiu=False` | 0 | **0** ✔ |
| regles sense `pom_global` | 0 | **0** ✔ |
| `talla_base` fora del `size_system` del ruleset | 0 | **0** ✔ |
| SizeSystem actius | 10 | **10** ✔ |
| `GarmentTypeItem` sense nom | 0 | **0** ✔ |
| parells (item×system) amb 2+ rulesets no nuls | 0 | **0** ✔ (53 parells) |

Models amb/sense grading: **579 / 382** (sense canvi: P2 és additiu sobre contenidors existents,
no reassigna cap model). Prova del cotó: **1 ruleset exacte** als 3 combos NEWBORN.

---

# P1 · P2b · P3-FORM — EXECUTATS (3a tanda, 2026-07-24)

## Altes autoritzades — 13 POMs nous (`LOSPOM-688…700`)

`D11H` `D11W` · `T1W` `T1H` `T2W` `T2H` · `ML` `MS` `MB` `MO` · `FL` `FS` · `MD`
Tots amb POMGlobal + POMMaster + àlies del self. **`GAL`/`GAS` NO creats** (la llei és «un model
concret ho exigeix», no el màster en abstracte).

## P2b — sembra als contenidors NEWBORN (+14 regles)

| contenidor | abans | després | afegits |
|---|---|---|---|
| New Born Tops | 43 | **45** | `D11H` `D11W` |
| New Born Onepieces | 45 | **48** | `D11H` `D11W` `MD` |
| New Born Bottoms | 22 | **31** | `D11W` `T1W` `T2W` `T1H` `T2H` `ML` `MS` `MB` `MO` |

**`baby_dress` entra a l'àmbit d'Onepieces** (scope ITEM). `MD`=3.0 es justifica sol: Onepieces ja
té `M-M79`=4.20 (llargada de pelele), que no és la d'un vestit.

## P1 — `LOS Woman Woven — Bottoms (Alpha)` creat

**29 regles**: 14 del màster BOTTOM ALFA + **15 heretades** del numèric id=54.
`SizingProfile` creat · **30 models repuntats** (pks 739…776: `shorts` 13, `trousers` 12,
`skirt_straight` 5) · **30 Watchpoints** `BOTTOMS_ALPHA_POMS_SENSE_FONT_PROPIA` amb la llista dels
15 POMs prestats · **11 Watchpoints** `MAN_ALPHA_BOTTOMS_SENSE_FONT` (grading MAN **no** tocat).

### ⚠️ El mecanisme de provinença demanat no existeix
`GradingRuleSet.origen` té **choices tancats** (`CANONICAL`/`CLIENT_RUN`/`IMPORT`): afegir-hi
`HERETAT_NUMERIC` és canvi de codi, impossible des de PROD. `GradingRule` **no té cap camp** de
provinença. `Watchpoint` **exigeix FK a Model** — no es pot penjar d'un ruleset.
**Adoptat**: ruleset amb `origen='CLIENT_RUN'` (que és cert) i el préstec visible als **30
Watchpoints dels models**, amb els 15 codis a `dades`. És l'únic ancoratge que el model de dades
permet avui. Si es vol al ruleset, cal afegir el choice a `dev`.

## P3-FORM — 12 regles, distinció POM a POM

| ruleset | regles amb break |
|---|---|
| LOS Woman Knit — Tops | **7** |
| LOS Woman Woven — Bottoms (Alpha) | **5** |

- **Ritme nou** (`2a col ≠ 0` → `label='2XL'`): `BJ` `B` `E` `H6` `H`.
- **Sostre** (`2a col = 0` → `label='3XL'`): `L3` `L4`.
- **Alpha** (creix fins a M, pla després → `label='L'`): `D22` `ML` `D11RH` `D11RM` `D11RL`.

### 9 regles saltades: la 1a columna del màster no quadra amb la BD
No s'ha tocat el seu `increment_base` (llei d'omplir forats) i, en conseqüència, **tampoc se'ls ha
posat break**: queden LINEAR pures.

| codi | POM | màster | BD |
|---|---|---|---|
| `K2` | `AC SH` | 1.2 | 2.0 |
| `K` | `SH` | 0.4 | 0.8 |
| `K1` | `SH DR` | 0.2 | 0.3 |
| `L5` | `NK DR BK` | 0.2 | 0.0 |
| `A1` | `AC FR` | 0.8 | 1.6 |
| `A2` | `AC BK` | 0.8 | 1.6 |
| `GL` | `GL` | 1.0 | 0.5 |
| `H11L` | `H11L` | 0.3 | 0.5 |
| `M` | `M-M79` | 1.5 | 1.3 |

**Patró:** `A1`/`A2`/`K`/`K2` són exactament el DOBLE a la BD. Fa pensar en mesura sencera vs mitja
(el `⚠️` del màster sobre `H=SLEEVE MUSCLE (1/2)` apunta al mateix). **Per a la Montse.**

## P6 — invariants recalculats (post P1/P2b/P3)

| invariant | esperat | real |
|---|---|---|
| regles a POM `actiu=False` | 0 | **0** ✔ |
| regles sense `pom_global` | 0 | **0** ✔ |
| `talla_base` fora del `size_system` | 0 | **0** ✔ |
| SizeSystem actius | 10 | **10** ✔ |
| items sense nom | 0 | **0** ✔ |
| **parells (item×system) amb 2+ rulesets** | 0 | **0** ✔ (53 parells) |

**Prova del cotó, els dos costats de Woman Bottoms:**

| combo | profiles | rulesets |
|---|---|---|
| WOMAN+WOVEN+BOTTOMS · `trousers` · **WOMAN_LOS_01** | 1 | **1** ✔ `…(Alpha)` |
| WOMAN+WOVEN+BOTTOMS · `trousers` · **WOMAN_NUM_LOS_01** | 1 | **1** ✔ `…Bottoms` |

L'alfa i el numèric conviuen sense ambigüitat: **el `size_system` els separa**.

## Xifres finals del tenant `los`

| | inici de sessió | final |
|---|---|---|
| POMMaster | 246 | **262** |
| POMGlobal `LOSPOM-*` | 149 | **165** |
| CustomerPOMAlias | 196 | **212** |
| **GradingRule** | 402 | **460** |
| GradingRuleSet actius | 19 | **19** *(+1 Alpha, −1 residual)* |
| SizingProfile | 18 | **25** |
| Models amb/sense grading | 580/381 | **579/382** |
| Watchpoints oberts | 750 | **791** *(+30 Alpha, +11 MAN)* |

---

# P5 — MIRALL A `fhort` · EXECUTAT (2026-07-24)

`manage.py bootstrap_tenant fhort --from los --additive` (dry-run primer, després apply).

## Els 4 invariants

| # | invariant | resultat |
|---|---|---|
| 1 | **additiu pur** | **189 creats · 0 ACTUALITZATS · 2.811 intactes · 0 saltats** ✔ |
| 2 | **`ambigus_al_desti` reportat, mai triat** | **12 claus** amb ≥2 files al destí, totes **saltades intactes** ✔ |
| 3 | **pk pròpies a `fhort`** | ruleset Alpha: pk **56** a `los` / pk **145** a `fhort`. POMs nous: 738→744, 739→745, 740→746… ✔ |
| 4 | **xifres coincidents** | Alpha 29/29 ✔ · New Born Bottoms 31/31 ✔ · els 23 POMs nous i rebatejats, **23/23 presents** ✔ |

Els 12 ambigus són tots `POMMaster` per `codi_client` duplicat al destí (`A3`, `BJ`, `C1`, `E4`,
`F1`, `F2`, `S`×2, `S2`, `U`, `U1`, `V`) — **deute preexistent de `fhort`**, no creat avui.

`destí actiu: onboarding i template intactes` — l'onboarding de `fhort` no s'ha tocat.

## ⚠️ Conseqüència no prevista: 3 POMMaster duplicats a `fhort`

Dos contenidors New Born surten amb **2 regles de més a `fhort`** (Tops 47 vs 45, Onepieces 50 vs 48).
Investigat: les extres són `SL` i `SL OP` — **els noms VELLS dels POMs que P0 va rebatejar només a
`los`**. Com que `bootstrap_tenant` aparella `POMMaster` per `codi_client`, en copiar el `GL` de
`los` no va trobar cap `GL`… i **en va crear un de nou**, al costat del que ja existia amb l'altre nom.

| `pom_global` | a `fhort` ara | |
|---|---|---|
| `POM-025` | `SL OP` (pk 297, 25 regles, 35 maps) **+** `H11L` (pk 740, 8 regles, 33 maps) | ⚠️ duplicat |
| `LOSPOM-681` | `H.12` (pk 686, 2 regles) **+** `H11S` (pk 739, 2 regles) | ⚠️ duplicat |
| `LOSPOM-558` | `GL` (pk 563, 8 regles, 36 maps) **+** `GCI` (pk 736, 0/0) | ⚠️ duplicat |
| `POM-020` | només `SL` (pk 292) | ✔ |
| `LOSPOM-680` | només `GS` (pk 735) | ✔ |

**Compleix la lletra del guard** (additiu, 0 sobreescriptures) **però duplica la semàntica**: la
mateixa mesura viu sota dos `codi_client` al mateix schema. L'arrel és que **el rebateig de P0 va ser
només de `los`** i el mirall aparella per nom, no per `pom_global`.

**No ho toco.** Dues sortides possibles, totes dues decisió d'Agus:
1. **Rebatejar els homòlegs a `fhort`** (`SL OP`→`H11L`, `H.12`→`H11S`, `GL`→`GCI`) i fusionar les
   regles — el mateix patró de P0, ara al segon schema.
2. **Deixar-ho** i acceptar que `fhort` parla el vocabulari vell mentre `los` parla el nou.

L'opció 1 és coherent amb «un sol vocabulari» i es pot fer amb el mateix script de P0 apuntat a
`fhort`. **Pendent de decisió.**

---

# P5-FIX — ANÀLISI DE LA FUSIÓ A `fhort` · **NO EXECUTAT** (STOP)

Patró A read-only sobre `fhort`. Foto prèvia: `GradingRule`=1.272 · `GarmentPOMMap`=1.914 ·
`POMMaster`=423. **Cap escriptura.**

## El STOP s'ha disparat — però totes les col·lisions són IDÈNTIQUES

| cas | sobreviu | desapareix | col·lisions regles | col·lisions maps |
|---|---|---|---|---|
| `POM-025` | pk=297 `SL OP` (25r+35m) | pk=740 `H11L` (8r+33m) | **8 de 8** | **33 de 33** |
| `LOSPOM-681` | pk=686 `H.12` (2r) | pk=739 `H11S` (2r) | **2 de 2** | 0 |
| `LOSPOM-558` | pk=563 `GL` (8r+36m) | pk=736 `GCI` (0r+0m) | **0** | **0** |

**Les 10 col·lisions de regla són byte a byte iguals** (mateixa `logica`, `increment_base`,
`increment_break` i `talla_break_label`). Exemples:

```
LOS Kids Boy Knit — Tops : guanyador LINEAR base=0.30 brk=0.20 lbl=9/10
                           perdedor  LINEAR base=0.30 brk=0.20 lbl=9/10   (IDÈNTIQUES)
LOS Teen Girl Knit — Tops: guanyador LINEAR base=0.50 brk=1.00 lbl=14
                           perdedor  LINEAR base=0.50 brk=1.00 lbl=14     (IDÈNTIQUES)
```

El motiu del teu STOP era *«no hi ha manera automàtica segura de triar quina regla guanya»*. **Aquí no
hi ha res a triar**: les dues diuen exactament el mateix. Però la conseqüència operativa canvia el
mètode que havies escrit, i per això m'aturo.

## Per què el mètode del brief no es pot aplicar tal com està

El brief diu: *«Reassignar TOTES les GradingRule i GarmentPOMMap del perdedor cap al que sobreviu»* i
després *«esborrar (actiu=False, mai DELETE dur) el perdedor un cop buit de referències»*.

Amb **100% de col·lisió**, reassignar és **impossible**: `unique_together(rule_set, pom)` ho impedeix,
i el mateix per als maps. El perdedor no es pot buidar movent; només **esborrant** les seves 8 regles
i 33 maps (cas 1) i 2 regles (cas 2).

I si es desactiva el perdedor **sense** buidar-lo, es trenca l'invariant de P6
**«0 regles a POM `actiu=False`»** — que avui és verd als dos schemas.

**Les files a esborrar són exactament les que `bootstrap_tenant` va crear avui**: esborrar-les torna
`fhort` a l'estat pre-P5 per a aquests POMs. És defensable, però **és un DELETE dur a PROD** i no és
el que autoritzava el brief. Per això m'aturo i t'ho pregunto.

## Cas 3 — aquest sí que és net

`LOSPOM-558`: el perdedor `GCI` (pk=736) té **0 regles i 0 maps**. No hi ha res a moure ni a
esborrar: n'hi ha prou amb rebatejar `GL`→`GCI` (pk=563, conservant 8r+36m) i posar el buit a
`actiu=False`. **És exactament el patró net de P0** i es pot fer ara mateix sense cap decisió nova.

## Opcions

| | què implica | risc |
|---|---|---|
| **A** · només el cas 3 | rebateig net `GL`→`GCI`, desactivar el buit | cap (patró P0 ja provat) |
| **B** · els 3, esborrant els duplicats exactes | + esborrar 10 regles i 33 maps creats avui per P5 | DELETE dur a PROD, però només de files redundants d'avui |
| **C** · els 3, sense esborrar | deixar el perdedor **actiu** amb el codi vell | no resol la duplicació; només la fa més confusa |
| **D** · cap | acceptar dos vocabularis a `fhort` | el que hi ha ara |

**Recomanació: A ara** (gratis i sense decisions), i **B en una segona passada** si confirmes que es
poden esborrar les files que P5 va crear avui. La C no la recomano: deixa el pitjor dels dos mons.

**No s'ha tocat res.**

---

# P5-FIX · FOTO PRÈVIA (abans de l'apply) — 2026-07-24

Condicions verificades en read-only abans de tocar res:

- **Condició 1 · timestamp**: ⚠️ `GradingRule`, `GarmentPOMMap` i `POMMaster` **no tenen cap camp de
  data** al model. La verificació per timestamp és **impossible**; substituïda per **bloc de pk**:
  P5 va crear els 78 últims `GradingRule` (pk≥1846) i els 69 últims `GarmentPOMMap` (pk≥3253).
  **Totes** les files a esborrar hi cauen: 8/8, 33/33 i 2/2. ✔
- **Condició 2 · bessona exacta**: cada fila té una bessona amb la **tupla completa** idèntica al
  supervivent — regles 8/8 i 2/2, maps 33/33. ✔ (l'assert es repeteix DINS l'atòmic).

## Bolcat complet de les files que s'esborraran

```


### POMMaster perdedor pk=740 · codi_client='H11L' · pom_global=POM-025 · nom='Sleeve opening / Cuff width'
REGLES:
     pk rule_set                               logica      inc   base  break    lbl talla_base act
   1847 LOS Baby Knit — Tops                   LINEAR     0.30   0.30   None   None      03/06 True
   1848 LOS Kids Boy Knit — Tops               LINEAR     0.30   0.30   0.20   9/10          2 True
   1850 LOS Kids Girl — Dresses                LINEAR     0.20   0.20   0.30   9/10          2 True
   1851 LOS Kids Girl Knit — Tops              LINEAR     0.30   0.30   0.20   9/10          2 True
   1855 LOS New Born Knit — Onepieces          LINEAR     0.30   0.30   None   None      00/01 True
   1857 LOS New Born Knit — Tops               LINEAR     0.30   0.30   None   None      00/01 True
   1863 LOS Teen Girl Knit — Tops              LINEAR     0.50   0.50   0.50     14          8 True
   1865 LOS Woman Knit — Tops                  LINEAR     0.50   0.50   None   None          S True
MAPS:
     pk item                   oblig  key    nivell   ordre pend_rev
   3254 shirt_woven            True   False  M           19 True
   3256 blouse                 True   False  M           19 False
   3258 overshirt              True   False  M           19 True
   3260 uniform_shirt          True   False  M           19 True
   3262 t_shirt                True   False  M           18 False
   3264 polo                   True   False  M           18 True
   3266 top_sleeveless         True   False  M           18 True
   3268 vest_top               True   False  M           18 True
   3270 sweater                True   False  M           14 False
   3272 twinset                True   False  M           14 False
   3274 cardigan               True   False  M           14 False
   3276 knit_gilet             True   False  M           14 False
   3278 hoodie                 True   False  M           18 False
   3280 fleece_jacket          True   False  M           18 False
   3282 dress_simple           True   False  M           18 False
   3284 shirt_dress            True   False  M           18 False
   3286 dress_fancy            True   False  M           18 False
   3288 dress_structured       True   False  M           18 False
   3290 jumpsuit               True   False  M           18 False
   3292 dungarees              True   False  M           18 False
   3294 playsuit               True   False  M           18 False
   3296 bodysuit               True   False  M           18 False
   3298 thermal_top            True   False  M           18 False
   3300 pyjama_set             True   False  M           18 False
   3302 blazer                 True   False  M           19 False
   3304 casual_jacket          True   False  M           19 True
   3306 gilet                  True   False  M           18 True
   3308 coat                   True   False  M           19 False
   3310 trench                 True   False  M           19 False
   3312 parka                  True   False  M           19 False
   3314 leather_garment        True   False  M           19 False
   3316 baby_sleepsuit         False  False  O            7 False
   3320 baby_top               False  False  O           10 False

### POMMaster perdedor pk=739 · codi_client='H11S' · pom_global=LOSPOM-681 · nom='SLEEVE SHORT OPENING'
REGLES:
     pk rule_set                               logica      inc   base  break    lbl talla_base act
   1853 LOS Man Knit — Tops                    LINEAR     0.80   0.80   None   None          M True
   1861 LOS Teen Girl Knit — Tops              LINEAR     0.50   0.50   1.00     14          8 True
```
