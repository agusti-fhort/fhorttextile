# INFORME DE DIVERGÈNCIES — màster NEWBORN vs BD · 2026-07-24

Generat en aplicar **P2 (fill-holes)** sobre els 3 contenidors New Born del tenant `los`.
Llei aplicada: **el màster omple forats, MAI sobreescriu.** Res del que hi ha en aquest informe
s'ha escrit a la base de dades.

## 1. Cel·les que DIVERGEIXEN (el màster diu una cosa, la BD ja en diu una altra)

La BD mana (ve de fitxa); el màster queda anotat. **11 casos.**

| contenidor | codi màster | POM real | màster | BD | Δ |
|---|---|---|---|---|---|
| New Born Tops | `K1` | `SH DR` | 0.2 | **0.0** | +0.2 |
| New Born Tops | `A1` | `AC FR` | 0.5 | **1.0** | −0.5 |
| New Born Tops | `A2` | `AC BK` | 0.5 | **1.0** | −0.5 |
| New Born Bottoms | `D1` | `THI` | 1.0 | **0.5** | +0.5 |
| New Born Onepieces | `K1` | `SH DR` | 0.2 | **0.0** | +0.2 |
| New Born Onepieces | `L4` | `NK DR FR` | 0.3 | **0.25** | +0.05 |
| New Born Onepieces | `A1` | `AC FR` | 0.5 | **0.9** | −0.4 |
| New Born Onepieces | `A2` | `AC BK` | 0.5 | **0.9** | −0.4 |
| New Born Onepieces | `H6` | `AH DEP` | 0.5 | **0.9** | −0.4 |
| New Born Onepieces | `GL` | `GL` | 1.5 | **1.6** | −0.1 |
| New Born Onepieces | `H` | `BIC` | 0.5 | **0.45** | +0.05 |

**Patró a mirar:** `K1`, `A1` i `A2` divergeixen als DOS contenidors de la mateixa manera, i
Onepieces divergeix molt més que Tops (7 vs 3). Sembla que Onepieces es va sembrar d'una font
diferent. **Cal la teva confirmació sobre quina mana.**

## 2. Casos NO aplicats per decisió del brief

### 2a. Subtaula T-SHIRT (item-específic)
El brief mana que **el general mani** per al ruleset ampli. La subtaula queda anotada, sense aplicar:

`B=1.0 · E=1.0 · MT=1.5 · L3=0.3 · L5=0.0 · L4=0.3 · U1=0.0 · K=0.4 (general 0.3) ·
K1=0.0 (general 0.2) · GS=0.3 · H=0.5 · H11S=0.5 (general buit) · T5=0.1 (POM nou) ·
S44=0.2 (general 0.3)`

Per aplicar-la caldria un contenidor propi amb àmbit ITEM sobre `t_shirt` — decisió teva.

### 2b. Sense codi POM al full
`HPS TO CHEST` i `CB TO WRIST` — **no sembrats**, tal com mana el màster.

### 2c. `S44` — retingut per un defecte conegut
`S44` (FRONT MOTIVE LOCATION, 0.3) resol al POMMaster **`S`**, que el cens va marcar com a
**mal cablejat**: hi pengen alhora `S22`=BELT HEIGHT i `S44`=FRONT MOTIVE LOCATION, i el POM es
diu *Front armhole along seam*. Sembrar-hi 0.3 donaria a l'armhole la graduació d'una localització
de motiu. **Retingut fins que es desfaci el cablejat.**

## 3. Codis del màster que NO existeixen al diccionari — veredicte de la condició d'entrada

El brief només autoritza crear-los si hi ha **conflicte real dins d'un sol contenidor**.

| codi | valor | conflicte dins d'un contenidor? | veredicte |
|---|---|---|---|
| `D11H` 0.0 / `D11W` 0.5 | TOP-DRESS | **SÍ** — dos valors D11 diferents al mateix full | ✅ **autoritzat a crear** |
| `T1W` 0.7 / `T1H` 1.5 | BOTTOM | **SÍ** — front rise waist vs HPS al mateix full | ✅ **autoritzat a crear** |
| `T2W` 0.7 / `T2H` 1.9 | BOTTOM | **SÍ** | ✅ **autoritzat a crear** |
| `ML` 3.7 / `MS` 1.5 / `MB` 2.5 / `MO` 3.5 | BOTTOM | **SÍ** — 4 longituds totals al mateix full | ✅ **autoritzat a crear** |
| `MT` 1.5 / `MD` 3.0 | TOP-DRESS | **NO** — es resolen per abast del contenidor | ⛔ no crear |
| `FL` 0.5 / `FS` 0.5 | BOTTOM | **NO** — mateix valor, el màster ja ho marca | ⛔ no crear, usar `LEG OP` |
| `GAL` 0.0 / `GAS` 0.1 | TOP-DRESS | **SÍ** — dos valors al mateix full | ⚠️ **contradiu una decisió teva** (vegeu sota) |

### ⚠️ `GAL`/`GAS` — decisió pendent
El 2026-07-24 vas decidir: *«GA — queda quiet. Discard GAL/GAS… si mai un model concret ho exigeix,
es crea llavors, no ara»* (llei del naixement mandrós). El màster NEWBORN **sí** que en dona dos
valors diferents dins d'un sol full (0.0 i 0.1) — o sigui que la condició s'ha complert.

**No els he creat**: la teva decisió era explícita i el disparador que hi posaves era «un model
concret ho exigeix», no «el màster ho llista». Cap model NEWBORN demana avui les dues mesures.
**Confirma si el màster compta com a disparador.**

### `MD` — un forat estructural
`MD` (total length dress, 3.0) es resol «per abast del contenidor», però **cap contenidor New Born
cobreix `baby_dress`**: els àmbits ITEM són `baby_top`+`baby_bodysuit` (Tops),
`baby_leggings`+`baby_bloomers` (Bottoms) i `baby_sleepsuit`+`baby_sleepbag`+`booties` (Onepieces).
`baby_dress` (49 models!) **no és a cap àmbit** — per això `MD` no té on anar. Vegeu §6.1 del cens.

## 4. Què SÍ s'ha aplicat

**15 regles noves, LINEAR pur, cap break**, totes sobre POMs que ja existien:

| contenidor | regles abans | després | noves |
|---|---|---|---|
| New Born Tops | 37 | **43** | 6 |
| New Born Bottoms | 20 | **22** | 2 |
| New Born Onepieces | 38 | **45** | 7 |

Invariant verificat: **creixement net, cap substitució**.
