# Catàleg de peces del tenant (bolcat literal)

> Bolcat READ-ONLY del catàleg de peces del tenant `fhort` per a la validació de
> classificació de Montse (1.043 models LOSAN SS27).
> Entorn: staging · BD `ftt_staging` · schema `fhort` · branca `dev`. Data: 2026-07-18.
> Sense interpretació: només dades. Font: ORM (`SELECT`/`.count()`), cap escriptura.

**Recomptes:** GarmentGroup = 11 · GarmentType = 19 · GarmentTypeItem = 57 · items amb 0 POMs = 2.

---

## 1. GarmentGroup

> Nota: el model `GarmentGroup` **no té camp `ordre`**; l'ordenació natural és per `codi`.
> La columna `ordre` mostra la `pk` (id de fila) com a únic ordinal disponible.

| codi | nom | ordre (pk) |
|---|---|---|
| ACCESSORIES | Accessories | 11 |
| BOTTOMS | Bottoms | 4 |
| DRESSES | Dresses & Jumpsuits | 8 |
| DRESSES-FULL | Dresses & Full Length | 3 |
| KNITWEAR | Knitwear | 10 |
| OUTERWEAR | Outerwear | 2 |
| SWIMWEAR | Swimwear | 1 |
| TOPS | Tops | 7 |
| TOPS-KNIT | Tops — Knitwear | 6 |
| TOPS-WOVEN | Tops — Woven | 5 |
| UNDERWEAR | Underwear & Lingerie | 9 |

Total GarmentGroup: **11**

---

## 2. GarmentType (tenant)

| id | codi_client | nom_client | grup |
|---|---|---|---|
| 69 | LEGGINGS_TIGHTS | Leggings & Tights | BOTTOMS |
| 70 | SKIRTS | Skirts | BOTTOMS |
| 68 | TAILORED_PANTS | Tailored & Rigid Pants | BOTTOMS |
| 72 | ADULT_JUMPSUITS | Adult Jumpsuits & Overalls | DRESSES |
| 78 | BABY_ONEPIECES | Baby & Kids One-Pieces | DRESSES |
| 42 | DRESS | Dress | DRESSES |
| 71 | DRESSES | Dresses | DRESSES |
| 77 | HEAVY_OUTERWEAR | Heavy Outerwear | OUTERWEAR |
| 76 | STRUCTURED_JACKETS | Structured Jackets | OUTERWEAR |
| 75 | SWIMWEAR | Swimwear | SWIMWEAR |
| 79 | BABY_SEPARATES | Baby & Kids Separates | TOPS |
| 63 | BUTTONED_TOPS | Buttoned Tops | TOPS |
| 64 | JERSEY_TOPS | Jersey Tops | TOPS |
| 66 | KNIT_CARDIGANS | Knit Cardigans | TOPS |
| 65 | KNIT_SWEATERS | Knit Sweaters | TOPS |
| 67 | SWEATSHIRTS_MIDLAYERS | Sweatshirts & Midlayers | TOPS |
| 24 | T_SHIRT | T-shirt | TOPS |
| 74 | BRA_SHAPEWEAR | Bra & Shapewear | UNDERWEAR |
| 73 | UNDERWEAR | Underwear | UNDERWEAR |

Total GarmentType: **19**

---

## 3. GarmentTypeItem (catàleg pla, ordenat grup → type → item)

Ordenació: `grup` → `codi_client` del type → `complexity_order` → `code`.
`n_POMs` = nombre de `GarmentPOMMap`. `n_IBM` = nombre d'`ItemBaseMeasurement`.

| grup | type_codi | type_nom | item_id | item_code | item_nom | compl. | n_POMs | 0 POMs | grading_rule_set | base_size_definition | n_IBM |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BOTTOMS | LEGGINGS_TIGHTS | Leggings & Tights | 24 | leggings | Malla / legging | 1 | 26 |  | no | no | 0 |
| BOTTOMS | LEGGINGS_TIGHTS | Leggings & Tights | 25 | culotte_cycling | Culotte (amb badana) | 2 | 26 |  | no | no | 0 |
| BOTTOMS | SKIRTS | Skirts | 26 | skirt_straight | Faldilla recta / tub | 1 | 16 |  | no | no | 0 |
| BOTTOMS | SKIRTS | Skirts | 27 | skirt_volume | Faldilla volumètrica | 2 | 16 |  | no | no | 0 |
| BOTTOMS | TAILORED_PANTS | Tailored & Rigid Pants | 19 | chino | Chino | 1 | 23 |  | no | no | 0 |
| BOTTOMS | TAILORED_PANTS | Tailored & Rigid Pants | 20 | jeans | Jeans (denim) | 1 | 21 |  | no | no | 0 |
| BOTTOMS | TAILORED_PANTS | Tailored & Rigid Pants | 18 | trousers | Pantaló estructurat | 1 | 26 |  | no | no | 0 |
| BOTTOMS | TAILORED_PANTS | Tailored & Rigid Pants | 21 | shorts | Pantaló curt / bermuda | 2 | 22 |  | no | no | 0 |
| BOTTOMS | TAILORED_PANTS | Tailored & Rigid Pants | 22 | tracksuit_pant | Xandall | 2 | 25 |  | no | no | 0 |
| BOTTOMS | TAILORED_PANTS | Tailored & Rigid Pants | 23 | workwear_pant | Treball / uniforme | 2 | 23 |  | no | no | 0 |
| DRESSES | ADULT_JUMPSUITS | Adult Jumpsuits & Overalls | 32 | jumpsuit | Mono (vestir, mecànic o EPI) | 1 | 46 |  | no | no | 0 |
| DRESSES | ADULT_JUMPSUITS | Adult Jumpsuits & Overalls | 33 | dungarees | Peto (amb pitet i tirants) | 2 | 46 |  | no | no | 0 |
| DRESSES | ADULT_JUMPSUITS | Adult Jumpsuits & Overalls | 34 | playsuit | Playsuit / romper adult | 2 | 46 |  | no | no | 0 |
| DRESSES | BABY_ONEPIECES | Baby & Kids One-Pieces | 53 | baby_sleepsuit | Pelele / pijama sencer | 1 | 19 |  | no | no | 0 |
| DRESSES | BABY_ONEPIECES | Baby & Kids One-Pieces | 54 | baby_sleepbag | Sac de dormir de nadó | 2 | 12 |  | no | no | 0 |
| DRESSES | BABY_ONEPIECES | Baby & Kids One-Pieces | 55 | baby_bloomers | Ranita (pantaló bombat) | 3 | 12 |  | no | no | 0 |
| DRESSES | DRESSES | Dresses | 28 | dress_simple | Vestit pla simple | 1 | 33 |  | no | no | 0 |
| DRESSES | DRESSES | Dresses | 30 | dress_fancy | Vestit fantasia | 2 | 35 |  | no | no | 0 |
| DRESSES | DRESSES | Dresses | 29 | shirt_dress | Vestit camiser | 2 | 33 |  | no | no | 0 |
| DRESSES | DRESSES | Dresses | 31 | dress_structured | Vestit estructurat | 3 | 35 |  | no | no | 0 |
| OUTERWEAR | HEAVY_OUTERWEAR | Heavy Outerwear | 49 | coat | Abric de llana | 1 | 43 |  | no | no | 0 |
| OUTERWEAR | HEAVY_OUTERWEAR | Heavy Outerwear | 50 | trench | Gavardina / trench | 2 | 43 |  | no | no | 0 |
| OUTERWEAR | HEAVY_OUTERWEAR | Heavy Outerwear | 52 | leather_garment | Peça de pell / cuir | 3 | 41 |  | no | no | 0 |
| OUTERWEAR | HEAVY_OUTERWEAR | Heavy Outerwear | 51 | parka | Anorac / parca encoixinada | 3 | 42 |  | no | no | 0 |
| OUTERWEAR | STRUCTURED_JACKETS | Structured Jackets | 46 | blazer | Americana / blazer | 1 | 44 |  | no | no | 0 |
| OUTERWEAR | STRUCTURED_JACKETS | Structured Jackets | 48 | gilet | Gilet / armilla | 1 | 35 |  | no | no | 0 |
| OUTERWEAR | STRUCTURED_JACKETS | Structured Jackets | 47 | casual_jacket | Caçadora (denim/biker/bomber) | 2 | 44 |  | no | no | 0 |
| SWIMWEAR | SWIMWEAR | Swimwear | 43 | swimsuit | Banyador d'una peça | 1 | 20 |  | no | no | 0 |
| SWIMWEAR | SWIMWEAR | Swimwear | 44 | bikini | Bikini (combo top+bragueta) | 2 | 20 |  | no | no | 0 |
| SWIMWEAR | SWIMWEAR | Swimwear | 45 | swim_shorts | Bàixador d'home | 3 | 20 |  | no | no | 0 |
| TOPS | BABY_SEPARATES | Baby & Kids Separates | 56 | baby_bodysuit | Body de nadó | 1 | 12 |  | no | no | 0 |
| TOPS | BABY_SEPARATES | Baby & Kids Separates | 57 | baby_top | Top / samarreta de nadó | 1 | 11 |  | no | no | 0 |
| TOPS | BABY_SEPARATES | Baby & Kids Separates | 58 | baby_dress | Vestit de nadó | 2 | 10 |  | no | no | 0 |
| TOPS | BABY_SEPARATES | Baby & Kids Separates | 59 | baby_leggings | Leggings / pantalons de nadó | 2 | 12 |  | no | no | 0 |
| TOPS | BABY_SEPARATES | Baby & Kids Separates | 60 | baby_swimwear | Bany de nadó | 2 | 9 |  | no | no | 0 |
| TOPS | BUTTONED_TOPS | Buttoned Tops | 4 | shirt_woven | Shirt Man Regular | 1 | 37 |  | sí · EU Woven Man Regular | sí · L | 37 |
| TOPS | BUTTONED_TOPS | Buttoned Tops | 5 | blouse | Blusa | 2 | 37 |  | sí · BRW · Blusa · ALPHA_EU_W | no | 0 |
| TOPS | BUTTONED_TOPS | Buttoned Tops | 6 | overshirt | Sobrecamisa | 3 | 37 |  | no | no | 0 |
| TOPS | BUTTONED_TOPS | Buttoned Tops | 7 | uniform_shirt | Camisola d'uniforme | 4 | 37 |  | no | no | 0 |
| TOPS | JERSEY_TOPS | Jersey Tops | 8 | t_shirt | Samarreta / T-shirt | 1 | 29 |  | no | no | 0 |
| TOPS | JERSEY_TOPS | Jersey Tops | 9 | polo | Polo | 2 | 29 |  | no | no | 0 |
| TOPS | JERSEY_TOPS | Jersey Tops | 10 | top_sleeveless | Top de tirants | 3 | 29 |  | no | no | 0 |
| TOPS | JERSEY_TOPS | Jersey Tops | 11 | vest_top | Vest / Tank top | 3 | 29 |  | no | no | 0 |
| TOPS | KNIT_CARDIGANS | Knit Cardigans | 14 | cardigan | Càrdigan / jaqueta de punt | 1 | 32 |  | no | no | 0 |
| TOPS | KNIT_CARDIGANS | Knit Cardigans | 15 | knit_gilet | Armilla de punt | 2 | 32 |  | no | no | 0 |
| TOPS | KNIT_SWEATERS | Knit Sweaters | 12 | sweater | Jersei (coll alt, rodó o en V) | 1 | 31 |  | no | no | 0 |
| TOPS | KNIT_SWEATERS | Knit Sweaters | 13 | twinset | Twin-set (jersei + top) | 2 | 31 |  | no | no | 0 |
| TOPS | SWEATSHIRTS_MIDLAYERS | Sweatshirts & Midlayers | 16 | hoodie | Dessuadora (amb/sense caputxa) | 1 | 35 |  | no | no | 0 |
| TOPS | SWEATSHIRTS_MIDLAYERS | Sweatshirts & Midlayers | 17 | fleece_jacket | Jaqueta polar d'abric | 2 | 35 |  | no | no | 0 |
| UNDERWEAR | BRA_SHAPEWEAR | Bra & Shapewear | 40 | bra | Sostenidor | 1 | 6 |  | no | no | 0 |
| UNDERWEAR | BRA_SHAPEWEAR | Bra & Shapewear | 41 | shapewear | Faixa modeladora | 2 | 6 |  | no | no | 0 |
| UNDERWEAR | BRA_SHAPEWEAR | Bra & Shapewear | 42 | corset | Corset estructural | 3 | 6 |  | no | no | 0 |
| UNDERWEAR | UNDERWEAR | Underwear | 35 | briefs_man | Calçotets (slip/boxer) | 1 | 0 | ⚠️ 0 POMs | no | no | 0 |
| UNDERWEAR | UNDERWEAR | Underwear | 36 | briefs_woman | Braguetes (culotte/tanga) | 2 | 0 | ⚠️ 0 POMs | no | no | 0 |
| UNDERWEAR | UNDERWEAR | Underwear | 39 | pyjama_set | Pijama (conjunt) | 2 | 46 |  | no | no | 0 |
| UNDERWEAR | UNDERWEAR | Underwear | 37 | bodysuit | Body interior | 3 | 29 |  | no | no | 0 |
| UNDERWEAR | UNDERWEAR | Underwear | 38 | thermal_top | Samarreta interior tèrmica | 4 | 29 |  | no | no | 0 |

Total GarmentTypeItem: **57**

---

## 4. Items amb 0 POMs (marcats explícitament)

| type_codi | item_code | item_nom |
|---|---|---|
| UNDERWEAR | briefs_man | Calçotets (slip/boxer) |
| UNDERWEAR | briefs_woman | Braguetes (culotte/tanga) |

Total items amb 0 POMs: **2**
