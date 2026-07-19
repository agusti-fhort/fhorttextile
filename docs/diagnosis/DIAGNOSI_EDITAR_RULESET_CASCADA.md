# DIAGNOSI — «Editar RuleSet» ha de ser la cascada del wizard (reclassificació)

> Data: 2026-07-19 · **Patró A (READ-ONLY)** · staging `dev` · schema `fhort`. Cap escriptura.
> Abast: mapa camp-a-camp del modal d'edició vs el wizard de creació vs el serializer, i veredicte
> del bug M2M `targets`. Convenció: `fitxer:línia`; "NO EXISTEIX" = confirmat absent al codi.

## Resum executiu
1. **BUG CONFIRMAT (pèrdua de dades silenciosa).** El modal d'edició envia `targets: [1 sol id]` i el
   serializer té `targets` M2M escrivible → **substitueix** el conjunt. Editar un ruleset multi-target
   (fins i tot canviant NOMÉS el nom) el col·lapsa a 1 target.
2. El modal és **pla i incomplet**: només nom · codi_sistema · target(SINGLE) · construction · fit · actiu.
   **NO EXISTEIXEN** al modal: multi-target, grup/abast, família/item, size_system.
3. El bug és **AÏLLAT a `targets`**: la resta de camps (scope, garment_group, size_system, item) NO
   s'envien → el PATCH parcial els deixa intactes; i `applies_to` és **read-only** al serializer.
4. El **contracte de creació** (size-map) sí expressa la riquesa v3: multi-target + `applies_to`
   (scope multi-node) + construction/fit/size_system/item. L'edició no en cobreix res tret dels FK simples.
5. **Abast desat de 2 maneres** als 14 v3: `garment_group` FK (9) vs `scope_nodes` (5 baby/newborn).
   Decisió de disseny per a Fase B.

## BLOC 1 — Modal d'edició (frontend)
- Component: `RuleSetModal` a [GradingRuleSets.jsx:670](../../frontend/src/pages/GradingRuleSets.jsx#L670).
  S'obre per **editar** ([:232](../../frontend/src/pages/GradingRuleSets.jsx#L232) `onEdit`) i per **clonar**
  ([:224](../../frontend/src/pages/GradingRuleSets.jsx#L224) `onClone`, `id:null` → POST). El «+ Nou run de
  client» NO obre aquest modal: obre `SizeAuthoringDrawer` ([:189](../../frontend/src/pages/GradingRuleSets.jsx#L189)).
- Camps (F() selects/inputs, [:800-804](../../frontend/src/pages/GradingRuleSets.jsx#L800)): `nom`,
  `codi_sistema`, `target_codi_form` (SINGLE), `construction_codi_form` (SINGLE), `fit_type_codi_form`
  (SINGLE), `actiu`. Opcions de `TARGETS/CONSTRUCTIONS/FITS` **del vocabulari compartit `gradingAxes`**
  (importat) → **cap còpia de vocabulari pròpia** (sweep Onades net, confirmat). Però **NO** usa
  `garmentCatalog` ni els components de cascada.
- Payload ([:716-730](../../frontend/src/pages/GradingRuleSets.jsx#L716)): `nom, codi_sistema, actiu`
  sempre; `target` + **`targets: [tId]`** + `construction` + `fit_type` si l'eix té selecció.
  `target_codi_form` es preomple de `rs.target_codi` = **el PRIMER target** del M2M → per a un ruleset
  de 3 targets, es mostra 1 i es desa `[1]`.

**Veredicte Bloc 1:** modal pla; el payload de `targets` és d'1 element. No toca scope/grup/item/system.

## BLOC 2 — Serializer + viewset (backend)
- `GradingRuleSetViewSet` ([views.py:167](../../backend/fhort/pom/views.py#L167)): `ModelViewSet`,
  PATCH **per pk** `/grading-rule-sets/{id}/`. Escriptura gated `configure`.
- `GradingRuleSetSerializer` ([serializers.py:181](../../backend/fhort/pom/serializers.py#L181)):
  - **Escrivibles**: `nom, codi_sistema, targets (M2M), construction, fit_type, garment_group,
    garment_type_item, size_system, customer, actiu`.
  - **`targets` M2M escrivible** → `PATCH {targets:[id]}` fa **replace complet** (update per defecte de
    DRF). ← **causa del bug.**
  - **`applies_to` és `SerializerMethodField` READ-ONLY** ([:199-208](../../backend/fhort/pom/serializers.py#L199)):
    llegeix `scope_nodes`; **no s'escriu**. `target_codi` = primer target ([:213](../../backend/fhort/pom/serializers.py#L213)).
  - Read-only: `is_system_default, regles, regles_count, origen`. Guard dur: un `is_system_default` no
    pot canviar d'eixos ([:223-239](../../backend/fhort/pom/serializers.py#L223)).

**Veredicte Bloc 2:** el serializer accepta gairebé tot el contracte MENYS `applies_to` (scope), que és
read-only → **cal ampliar-lo** a Fase B perquè l'edició pugui reclassificar l'abast multi-node.

## BLOC 3 — Contracte de creació (wizard «Nou run de client»)
- `SizeAuthoringDrawer` (62 línies) embolcalla el wizard de size-map; la creació del ruleset viu al
  backend a [size_map_views.py:856](../../backend/fhort/pom/size_map_views.py#L856):
  `GradingRuleSet.objects.create(nom, size_system, target, construction, fit_type, garment_type_item,
  origen=CLIENT_RUN, customer)` + **`targets.add(target)` i `target_codis` (MULTI)** ([:862-869](../../backend/fhort/pom/size_map_views.py#L862))
  + **`apply_scope_nodes(rule_set, applies_to)`** ([:872](../../backend/fhort/pom/size_map_views.py#L872)).
- `apply_scope_nodes` ([grading_utils.py:493](../../backend/fhort/pom/grading_utils.py#L493)):
  wipe&recreate de `scope_nodes` des de `[{node_type, group_codi|garment_type_id|garment_type_item_id}]`.
- **Identificació**: creació per **clau natural** `(size_system, nom)` ([:847](../../backend/fhort/pom/size_map_views.py#L847));
  l'edició UI va per **pk** (row concret) — coherent per a reclassificar UNA fila.

**Veredicte Bloc 3:** el contracte v3 = multi-target + `applies_to` + construction/fit/size_system/item.

## BLOC 4 — Casos frontera (dades reals)
- **`item=NULL` és la forma v3**: els **14/14** rulesets v3 tenen `garment_type_item=None` (contenidor
  ampli). L'edició NO pot forçar item.
- **Abast desat de 2 maneres**: `garment_group` FK (9: Woman/Man/Teen/Kids…) vs `scope_nodes` (5:
  Baby/New Born, p.ex. **Onepieces = 3 scope_nodes**, grp=None). El matching (`scopeApplies`) cau al
  `garment_group` si no hi ha scope. → **decisió Fase B**: en editar, llegir tots dos i escriure de
  forma consistent (proposta: unificar a `applies_to`, o preservar la forma existent).
- **Seeds ISO** (`is_system_default=True`): eixos bloquejats (guard dur al serializer) — l'edició els ha
  de mostrar read-only, com ara.

## TAULA — paritat camp a camp
| camp | serializer escriu? | creació (size-map) | modal edició avui | Fase B |
|---|---|---|---|---|
| nom | ✅ | ✅ | ✅ | ✅ |
| codi_sistema | ✅ | (—) | ✅ | ✅ |
| **targets (M2M)** | ✅ (replace) | ✅ MULTI | ⚠️ **`[1]` → bug** | pills MULTI |
| construction | ✅ | ✅ | ✅ single | ✅ (cascada) |
| fit_type | ✅ | ✅ | ✅ single | ✅ (cascada) |
| garment_group | ✅ | (via scope) | ❌ | grup/abast |
| garment_type_item | ✅ | ✅ | ❌ | família/item (opcional) |
| size_system | ✅ | ✅ | ❌ | size system |
| **applies_to (scope)** | ❌ **read-only** | ✅ | ❌ | **ampliar serializer** |
| actiu | ✅ | ✅ | ✅ | ✅ |
| origen / is_system_default | ❌ | fixat | (read-only) | (igual) |

## ⚠️ Veredicte del bug M2M
**CONFIRMAT i AÏLLAT a `targets`.** [GradingRuleSets.jsx:727](../../frontend/src/pages/GradingRuleSets.jsx#L727)
`payload.targets = [tId]` + M2M escrivible → editar un ruleset multi-target el redueix a 1 target, fins
i tot en una edició només-de-nom (perquè `target_codi_form` es preomple i sempre es reenvia). **Repro:**
`LOS New Born Knit — Onepieces` (targets = BABY_BOY+BABY_GIRL+BABY_UNISEX). L'abast (`scope_nodes`) i la
resta de camps SOBREVIUEN (no s'envien / read-only); només els `targets` es perden. **Peça més urgent.**

## 💡 PROPOSTA (a validar al gate — Fase B)
1. Substituir el cos pla del modal per la **cascada compartida** (targets pills MULTI · construcció · fit ·
   grup/abast via `ScopeSelector` · família/item opcional · size system), tot via `garmentCatalog`,
   **prefilled** des de `rs` (`targets_codis`, `construction_codi`, `fit_type_codi`, `applies_to`/
   `garment_group`, `size_system`, `garment_type_item`). Reutilitzar, no reimplementar.
2. **Backend**: fer `applies_to` escrivible al serializer (update → `apply_scope_nodes`), i acceptar
   `targets` MULTI amb paritat exacta amb la creació. **Cap canvi d'esquema esperat**; si en calgués, ATURAR.
3. **Fix del bug** `targets` (pills multi) — commit separat, prioritari.
4. **Guard de coherència** no bloquejant en desar (avís si `matchingRuleSetsStrict` del cas editat passa a
   0 o >1), com a SizingProfile. Control humà.
5. Decidir la política d'abast (⚠️ Bloc 4): unificar a `applies_to` o preservar `garment_group` FK.

**GATE:** Agus valida l'abast abans de Fase B. Res tocat.
