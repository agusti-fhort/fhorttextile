# DIAGNOSI GRADING v3 — investigació profunda del domini (Patró A, read-only)

> Staging · `fhort` · dev. Data: 2026-07-18. **Read-only: cap canvi a BD ni codi.**
> Fonament per al PLA v3. La sembra v1/v2 (18 GradingRuleSet per system×item) està
> REBUTJADA per Agus; aquí NOMÉS es diagnostica per què i com hauria de ser.
> Cada afirmació ancorada a `fitxer:línia` o SELECT. Rutes: backend a
> `/var/www/ftt-staging/backend`, frontend a `/var/www/ftt-staging/frontend`.

## TL;DR — la hipòtesi es confirma (amb matís)

Hi ha **TRES subsistemes desacoblats** que "trien grading", i els 18 rulesets sembrats
només són visibles per a UN d'ells:

1. **Matcher del contenidor (import de fitxa)** — `cerca_contenidor_client(customer,
   size_system, garment_type_item, fit_type)` [grading_utils.py:535](backend/fhort/pom/grading_utils.py#L535).
   Filtra NOMÉS per `origen=CLIENT_RUN·customer·size_system·garment_type_item·fit_type`.
   **Els 18 LOS SÍ hi són abastables** (tenen aquests camps bé). Ignora target/construcció/grup.
2. **Suggeridor de perfil (wizard de model)** — `sizing_profiles_view`
   [s2_views.py:62](backend/fhort/pom/s2_views.py#L62). Filtra `SizingProfile` per
   `(target, construction, fit_type, garment_type)` i rankeja. **Els 18 LOS són INVISIBLES:
   tenen 0 SizingProfile** (SELECT: cap dels 18 té perfil).
3. **Picker del wizard (frontend, estricte)** — `matchingRuleSetsStrict`
   [gradingAxes.js:144](frontend/src/components/grading/gradingAxes.js#L144). Exigeix
   `targets` no-buits + `construction`/`fit` exactes + scope/grup + `size_system`. **Els 18
   LOS els fallen tots** (targets buits, construction NULL, grup NULL, 0 scope-nodes).

→ El disseny original és el de la hipòtesi: **rulesets AMPLIS (diccionari cumulatiu per
target+construcció+fit), exposats via SizingProfile; l'Item selecciona els POMs via
GarmentPOMMap; el grading és la intersecció.** La sembra per (system×item) trenca aquest
model: granularitat excessiva, sense perfils, sense metadada de wizard, i penjant de POMs
fantasma (sense traducció ni GarmentPOMMap).

---

## N1 — GradingRuleSet: model complet

Font: [pom/models.py:506-622](backend/fhort/pom/models.py#L506).

| camp | línia | tipus / notes |
|---|---|---|
| `origen` | :528 | Char choices: `CANONICAL`/`CLIENT_RUN`/`IMPORT` + NULL (:520-527). NULL = "no classificat". |
| `nom` | :532 | Char |
| `garment_group` | :533 | FK→GarmentGroup, PROTECT, nullable |
| `size_system` | :540 | FK→SizeSystem, PROTECT, nullable |
| `garment_type_item` | :548 | FK→tasks.GarmentTypeItem, SET_NULL, **nullable**, db_constraint=False. Node fi de la identitat del contenidor (llei CONTENIDOR). |
| `actiu` | :552 | Bool |
| `customer` | :556 | FK→tasks.Customer, SET_NULL, nullable, db_constraint=False |
| `pendents_vincular` | :561 | JSON (codis doc no vinculats) |
| `target` | :570 | FK→Target **legacy** (related_name *_legacy) |
| `targets` | :575 | **M2M→Target (autoritatiu)**. Un ruleset pot aplicar a molts targets. |
| `construction` | :582 | FK→ConstructionType, nullable |
| `fit_type` | :587 | FK→FitType, nullable |
| `is_system_default` | :592 | Bool. True = ve del seed ISO. |
| `parent_version` | :594 | self-FK (versions de client) |
| `version_number` | :600 | Int |
| `codi_sistema` | :601 | Char (ref, ex EU_WOVEN_WOMAN_REGULAR) |

**Choices literals (BD):** ConstructionType = `WOVEN·KNIT·STRETCH_KNIT·TECHNICAL`.
FitType = `REGULAR·SLIM·RELAXED·OVERSIZED·FLARED·TAPERED·STRAIGHT·BODYCON·ATHLETIC·CUSTOM`.
Target = `WOMAN·MAN·UNISEX_ADULT·BABY_GIRL/BOY/UNISEX·TODDLER_GIRL/BOY·GIRL·BOY·TEEN_GIRL/BOY·MATERNITY`.

**Scope/àmbit** = model separat `RuleSetScopeNode`
[pom/models.py:625-678](backend/fhort/pom/models.py#L625): arbre multi-node
Grup→Família→Item de DISPONIBILITAT (no identitat). `node_type` GROUP/TYPE/ITEM + exactament
un FK. **SELECT: els 44 rulesets del tenant tenen 0 scope-nodes** (cap backfillat).

**Constraint parcial CLIENT_RUN** [pom/models.py:614-618](backend/fhort/pom/models.py#L614),
migració 0039: `UniqueConstraint(customer, size_system, garment_type_item, fit_type)` amb
`condition=Q(origen='CLIENT_RUN')`. Com que Postgres tracta NULLS DISTINCT, **NO dedupe
mentre `garment_type_item` sigui NULL** (:611-613) → per això 104/111 (item NULL) poden
conviure i el matcher fa `order_by('id').first()`.

---

## N2 — El WIZARD de Grading Rules: component + endpoint + query EXACTA

**Frontend.** Llista + cards: [GradingRuleSets.jsx:36](frontend/src/pages/GradingRuleSets.jsx#L36)
(estats `selectedTarget/Construction/Fit/GarmentGroup/FamilyId/ItemId` :44-49; carrega tot amb
`GET /api/v1/grading-rule-sets/?page_size=200` :64). Wizard "Nou run de client":
[SizeAuthoringDrawer.jsx](frontend/src/components/SizeAuthoringDrawer.jsx) → `Wizard` de
[SizeMapSetup.jsx:191](frontend/src/pages/SizeMapSetup.jsx#L191) (aquest **CREA** un run, no
filtra). La cascada target→construcció+fit→grup→família→item viu a
[AxesSelector.jsx](frontend/src/components/grading/AxesSelector.jsx) + la lògica de matching a
[gradingAxes.js](frontend/src/components/grading/gradingAxes.js).

**Backend endpoint** [pom/views.py:154-166](backend/fhort/pom/views.py#L154):
`GradingRuleSetViewSet`, `filterset_fields = ['actiu','garment_group','size_system','customer']`
(:164). **NO filtra per target/construction/fit/item/origen al servidor.** El serializer
[serializers.py:181](backend/fhort/pom/serializers.py#L181) exposa els camps que el matching
del client llegeix: `targets_codis` (:210), `construction_codi` (:217), `fit_type_codi` (:220),
`garment_group`, `applies_to` (scope, :201-208), `size_system`, `origen`, `regles_count`.

**La QUERY real** (client-side, sobre la llista sencera). Estricta (wizard/ModelWizard),
[gradingAxes.js:144-154](frontend/src/components/grading/gradingAxes.js#L144):
```
rs.actiu !== false
&& rs.targets_codis?.length && targets_codis.includes(target)   // targets NO buits
&& rs.construction_codi === construction                        // exacte, NULL no fa comodí
&& rs.fit_type_codi === fit                                     // exacte
&& scopeApplies(strict): applies_to buit → EXIGEIX garment_group == grup triat
&& rs.size_system === sizeSystemId
```
Lenient (CRUD/ItemAuthoring), :128-137: eix NULL = **comodí**.

**Per què els 18 LOS NO responen** (SELECT del cens N5): tenen `targets` M2M **buits** (→
falla `targets_codis.length` estricte), `construction` **NULL** (→ falla `=== construction`),
`garment_group` **NULL** i **0 scope-nodes** (→ `scopeApplies` estricte falla). En lenient,
en canvi, targets-buit + construction-NULL + grup-NULL actuen de **comodí** → apareixen a
QUALSEVOL combinació amb fit=REGULAR (soroll / falsos positius).

---

## N3 — SizingProfile: model, is_default, i el camí model→grading

**Model** [pom/models.py:916-956](backend/fhort/pom/models.py#L916): claus d'identitat
`target·garment_type·construction·fit_type` (tots FK PROTECT) → resol a `size_system` +
`grading_rule_set` (FK PROTECT, **NO nullable**). `customer` SET_NULL nullable (NULL =
perfil genèric del tenant; informat = de client). `is_default` **default True** ("el sistema
suggereix aquest perfil"). Versions de client via `parent_profile`+`version` (clonar).

**El suggeridor viu** = `sizing_profiles_view`
[s2_views.py:62-128](backend/fhort/pom/s2_views.py#L62): `GET /api/v1/sizing-profiles/?target
&construction&fit_type&garment_type`. Filtra per aquests 4 eixos (:96-105), **rankeja**
(`_grup` :107-115): grup 0 = perfil propi del client · **grup 1 = `is_default and customer is
None`** (canònic genèric) · grup 2 = altres. El wizard escriu després el `grading_rule_set`
del perfil triat al Model.

**CAMÍ del grading d'un Model (troballa clau: NO passa per SizingProfile en runtime).**
`grep SizingProfile` a `models_app/` = 1 comentari
[extraction_views.py:1596](backend/fhort/models_app/extraction_views.py#L1596). El Model té
`grading_rule_set` FK SET_NULL [models_app/models.py:193](backend/fhort/models_app/models.py#L193).
Motor [pom/services.py:104](backend/fhort/pom/services.py#L104) `generate_graded_specs`: carrega
regles per `_load_grading_rules` (:539-563) → **prioritza `ModelGradingRule` residents; fallback
`GradingRule.filter(rule_set_id=model.grading_rule_set_id)`**. `Model.grading_rule_set` s'escriu
NOMÉS: (a) payload del wizard [models_app/views.py:418-422](backend/fhort/models_app/views.py#L418);
(b) import W5 via contenidor [extraction_views.py:1916/1950](backend/fhort/models_app/extraction_views.py#L1916);
(c) **cap signal** ([models_app/signals.py](backend/fhort/models_app/signals.py) no toca grading).
El SizingProfile és el catàleg que el **wizard** consulta per SUGGERIR; l'assignació és
desacoblada (el front escull i POSTeja `grading_rule_set_id`).

**Els 4 defaults sobre 104/GIRL_LOS_03**: són `SWEATSHIRTS_MIDLAYERS × {TODDLER_GIRL,
TODDLER_BOY, GIRL, BOY}`, `is_default=True`, `customer=None`. Qui els consulta en viu:
NOMÉS `sizing_profiles_view` (grup 1, canònic genèric, [s2_views.py:113](backend/fhort/pom/s2_views.py#L113)),
quan el wizard demana un model d'aquesta classificació. Cap codi els auto-assigna server-side.

---

## N4 — MATCHING de la sembra/càrrega (quin contenidor s'escull)

**Matcher viu** = `cerca_contenidor_client`
[grading_utils.py:535-549](backend/fhort/pom/grading_utils.py#L535):
```
GradingRuleSet.filter(origen=CLIENT_RUN, actiu=True, customer=, size_system=,
                      garment_type_item=, fit_type=).order_by('id').first()
```
Cridat a l'import de fitxa [extraction_views.py:1837](backend/fhort/models_app/extraction_views.py#L1837)
i al pre-check del Size-Map [size_map_views.py:731](backend/fhort/pom/size_map_views.py#L731).
**Ordre de preferència: cap.** Filtra dur `origen=CLIENT_RUN` → el **canònic mai entra** al
matching de contenidor (no és que es prefereixi CLIENT_RUN; el canònic és estructuralment
invisible aquí). Ignora `target/targets`, `construction`, `garment_group`.

**`cerca_canonic_equivalent`** [grading_utils.py:84-116](backend/fhort/pom/grading_utils.py#L84)
(filtra is_system_default+size_system+construction+fit+targets) **NO té cap cridador** (codi
mort). **`derive_grading_rule_set`** [grading_utils.py:251](backend/fhort/pom/grading_utils.py#L251)
és **JUBILAT** (:425-433). Cap dels dos participa en el matching viu.

**item=NULL al matching:** un ruleset amb `garment_type_item=NULL` (104/111) NOMÉS entra si el
Model importat també té `garment_type_item=NULL` (Django rendereix `IS NULL`). Si el model
porta item concret, 104/111 **no** són seleccionables. El target de 104/111 és irrellevant.

**Import** [extraction_views.py:1814-1965](backend/fhort/models_app/extraction_views.py#L1814):
detecta regles (`derive_rules_from_fitxa` :1829) → `cerca_contenidor_client` (:1837) → si None i
sense elecció, **409 `container_absent`+rollback** (:1847) → crea NOMÉS si `container_choice=='create'`
(:1897, identitat `customer+size_system+garment_type_item+fit_type`) → si existeix, SEMBRA/AMPLIA/
CONFLICTE. **`Model.grading_rule_set` mai s'assigna automàticament en crear un model** (només
payload wizard o import).

**Implicació per als 18 LOS:** SÍ són abastables pel matcher d'import (tenen customer/size_system/
item/fit·CLIENT_RUN correctes). El problema no és la reachability d'import, sinó que (a) són
invisibles al suggeridor de perfil i al wizard, (b) 7 són buits, (c) pengen de POMs fantasma.

---

## N5 — Cens dels 44 rulesets / 908 regles (SELECT)

Per origen: **CANONICAL 11 (332 regles) · CLIENT_RUN 20 (217) · IMPORT 0 · NULL 13 (359)**.

**El PATRÓ dels que responen bé** (ISO/canònics + BRW 115). Tots tenen: `targets` M2M plens,
`fit_type` set, `construction` set, `size_system` set, `is_system_default=1` (els ISO),
`garment_type_item=NULL`/`garment_group=NULL` (amplis) — EXCEPTE el client BRW 115 que a més
porta `garment_group=TOPS` + `item=blouse`. Exemples: `EU Knit Woman Regular` (79, KNIT/WOMAN/
ALPHA_EU_W, 40 regles), `EU Woven Woman Regular` (75, 61 regles).

**El PATRÓ dels que NO responen** (els 18 LOS + 104): `targets` M2M **buits**, `construction`
**NULL**, `garment_group` **NULL**, `target` FK **buit**; només `size_system`+`item`+`fit`
plens. Recomptes de mancances (SELECT): **targets M2M buits: 20 · construction NULL: 21 ·
garment_group NULL: 41 · garment_type_item NULL: 25 · size_system NULL: 7**.

**7 contenidors LOS BUITS (0 regles)** = els "buits visibles": Newborn baby_leggings/
baby_sleepsuit/baby_dress/booties, Baby baby_dress, Youth Boy t_shirt, Youth Girl t_shirt.

**SizingProfiles (27 total, 24 is_default, 26 customer NULL):** apunten a canònics + 104
(4 profiles) + BRW 115 (1). **Cap dels 18 LOS SS27 té cap SizingProfile** (SELECT: 0).

---

## N6 — POMMaster: duplicats semàntics (dimensionar PAS 4)

Total POMMaster = **335 · amb `pom_global` (traducció): 125 · sense: 210**. El costat "prim"
(codi tipus `T.1`, sense pom_global) és un duplicat sense traducció i **sense GarmentPOMMap**;
el costat canònic té traducció + molts maps + base_measurements.

| parell A (prim) ↔ B (canònic) | A: glob/regles/maps | B: glob/regles/maps |
|---|---|---|
| `T.1`(434) ↔ `RI FR`(321) | NO / 7 / **0** | SÍ (Rise front) / 17 / **17** |
| `L.4`(422) ↔ `NK DR FR`(302) | NO / 5 / 0 | SÍ / 10 / **34** |
| `L.5`(421) ↔ `NK DR BK`(303) | NO / 5 / 0 | SÍ / 5 / **31** |
| `K.2`(431) ↔ `AC SH`(278) | NO / 6 / 0 | SÍ (Across shoulder) / 7 / **31** |
| `H`(423) ↔ `BIC`(295) | NO / 3 / 0 | SÍ (Bicep) / 16 / **34** |
| `M-M79`(389) ↔ `DR L HPS`(325) | NO / 11 / 0 | SÍ (Dress length) / 7 / **10** |

**Parells addicionals (mateix nom_client):** `A.2`(420)↔`A2`(517) (tots dos sense glob, 4/4
regles) · `T.1-M79`(387)↔`T.1`(434) · `T.2-M79`(388)↔`T.2`(435) · `JJ`(468)↔`IC1`(496) (ELBOW
WIDTH) · `SL`(292, canònic Sleeve length, 36 maps)↔`I`(503, prim). Nota: `A.2` i `A2` són
tots dos prims (la sembra n'ha fet servir tots dos!).

**Dimensió de la contaminació:** de les **181 regles de rulesets LOS**, **127 pengen de POMs
SENSE `pom_global`** (fantasma/prims, sense GarmentPOMMap) i només **54 de POMs canònics
traduïts**. Els prims més usats: `M-M79`(10), `T.1`(6), `T.2`(6), `A.1`(5), `D.11-M79`(5),
`D`(5), `D22`(5), `A2`(4), `K.2`(4), `L.4`(4), `L.5`(4), `BJ`(4), `H`(4). → PAS 4 (consolidació)
ha de mapar aquests prims als canònics ABANS de re-sembrar, o les regles no intersequen amb els
POMs que l'Item selecciona (GarmentPOMMap).

---

## N7 — UX final: quants rulesets veu un tècnic

**Cas típic: nena toddler + punt + tops.**

- **Camí real (suggeridor de perfil, `sizing_profiles_view`).** SELECT `TODDLER_GIRL+KNIT` →
  **2 SizingProfiles**: `SWEATSHIRTS_MIDLAYERS→104/GIRL_LOS_03` (default) i `T_SHIRT→EU Knit
  Toddler Regular/TODDLER_EU` (default). **Cap dels 18 LOS SS27 hi surt** (0 perfils). El
  tècnic veu 1-2 perfils genèrics, mai la graduació LOS SS27 específica.
- **Camí picker estricte (ModelWizard, `matchingRuleSetsStrict`).** Els 18 LOS: targets buits →
  **exclosos**. Els canònics: grup NULL + 0 scope → `scopeApplies` estricte falla → també
  exclosos si el wizard passa un grup concret. Resultat pràctic: **~0** rulesets LOS oferts.
- **Camí llista lenient (CRUD).** Els 18 LOS (comodins) apareixen a moltes combinacions amb
  fit=REGULAR encara que siguin bikini/trousers per a un cas de "tops" → **soroll i falsos
  positius**, més 7 cards buides.

**Amb l'estructura v3 (objectiu):** UN sol ruleset cumulatiu per (target, construcció, fit,
size_system) amb metadada plena + 1 SizingProfile → el tècnic veuria **exactament 1** perfil/
ruleset correcte per al cas, com passa avui amb els ISO/BRW.

---

## ESPEC DE RULESET BEN POBLAT (per a la v3)

Perquè un GradingRuleSet sigui trobable pel WIZARD (estricte i lenient), pel SUGGERIDOR DE
PERFIL i pel MATCHER D'IMPORT alhora — com els ISO/BRW — ha d'omplir:

**Identitat i abast**
- `origen` = `CLIENT_RUN` (client) · `customer` = FK real (ex LOS) · `actiu=True`.
- `size_system` = FK (obligatori per al matching estricte i el suggeridor).
- `garment_type_item`: **NUL·L per als contenidors amplis** (un per target×construcció×fit),
  NO un per item. La granularitat per-item és el que es rebutja.

**Metadada de wizard (el que els 18 LOS no tenien)**
- `targets` **M2M** amb el/s target/s reals (ex TODDLER_GIRL) — imprescindible per
  `matchingRuleSetsStrict` i per `availableTargetCodes`.
- `construction` = FK (WOVEN/KNIT/STRETCH_KNIT/TECHNICAL) — imprescindible (exacte, no comodí).
- `fit_type` = FK — imprescindible (exacte).
- `target` FK legacy = mateix valor (encara el llegeixen superfícies velles).
- **Abast**: o bé `garment_group` = FK del grup, o bé `RuleSetScopeNode` (GROUP/TYPE/ITEM) — un
  dels dos perquè `scopeApplies` estricte no falli (avui **0 rulesets** en tenen cap).

**Exposició (perquè el model rebi el grading)**
- Un **`SizingProfile`** per (target, garment_type, construction, fit) → aquest ruleset +
  size_system, amb `is_default=True`/`customer` segons calgui. Sense perfil, el suggeridor
  del wizard **mai** l'ofereix.

**Contingut de regles net (PAS 4 previ)**
- Les `GradingRule` han de penjar de POMs **canònics amb `pom_global`** (traduïts) i amb
  `GarmentPOMMap`, no dels duplicats prims (T.1/K.2/L.4/L.5/H/M-M79/A2…), o la intersecció
  Item↔grading queda buida. Consolidar els parells de N6 abans de re-sembrar.

**Resum del contrast**
| eix | ISO/BRW (bo) | 18 LOS (rebutjat) |
|---|---|---|
| targets M2M | plens | **buits** |
| construction | set | **NULL** |
| fit_type | set | set (REGULAR) |
| abast (group/scope) | group o (BRW) | **cap** |
| size_system | set | set |
| granularitat | ampli (item NULL) | **1 per item (×18)** |
| SizingProfile | sí | **cap** |
| POMs de les regles | canònics+maps | **127/181 fantasma** |

*Cap canvi aplicat. Aquest document és l'única sortida d'aquest pas.*
