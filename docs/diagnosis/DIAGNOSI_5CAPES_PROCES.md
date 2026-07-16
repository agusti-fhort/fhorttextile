# DIAGNOSI — Realineació del PROCÉS del model a la llei de les 5 capes

> **Data:** 2026-07-16 (nocturn) · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, `dev`, tenant `fhort`
> **Abast:** tornar la seqüència de decisió del model a l'original — pas Talles = ESCALA PURA (sistema/run/base,
> capa 3), graduació com a pas propi (capa 4, on el fit discrimina), SizingProfile fora de la selecció del model
> (preset de biblioteca), runs mínims sense clons per-fit. **El motor NO es toca** (refactor de procés i superfícies).
> **Convenció:** cada fet amb `fitxer:línia` o `SELECT` real. Propostes marcades `💡`.
>
> **⚠️ Nota normativa:** la «LLEI D'ARQUITECTURA DE DADES — les 5 capes» que el brief cita com a `DECISIONS.md §2`
> **NO existeix a `DECISIONS.md` ni al repo** (l'únic doc de "5 capes" és `.claude/TAXONOMIA_FLUX_MODEL.md`, que
> tracta les 5 capes del *dashboard*, un tema diferent). El text del brief és, doncs, la font normativa d'aquest
> sprint. → **DECISIONS PENDENT:** escriure la llei de les 5 capes de dades a `DECISIONS.md §2`.

---

## RESUM EXECUTIU

1. **La contaminació és de SUPERFÍCIE, no de model de dades.** `SizeSystem` (capa 3) és **PUR**: no té cap camp de
   fit/construction (`pom/models.py:292-338`). El fit viu correctament a `SizingProfile` (preset/selecció) i a
   `GradingRuleSet` (capa 4). → **Fase C és BUIDA** (cap camp a migrar).

2. **El pas «3. Talles» del wizard VIOLA la llei:** llista **SizingProfiles** (que porten fit) com si fossin runs
   (`ModelWizard.jsx:337-411` → `sizing-profiles/` → `s2_views.py:64`), i **arrossega la graduació** implícitament
   (`sizingResult` deriva `grading_rule_set_id` del perfil, `ModelWizard.jsx:75`). Barreja capa 3 i capa 4.

3. **La graduació JA es tria bé i per separat a la fitxa** (`ModelSheet.jsx:451` → `RuleSetCard` → AxesSelector +
   RuleSetPicker → `PATCH update-step2`). CONFORME capa 4, ja construït. → **el canvi mínim és NOMÉS depurar el pas
   Talles; no cal cap picker nou** (dimensionament honest d'A.4).

4. **Els SizingProfiles NO són duplicats redundants:** els 27 tenen **0 referències entrants** (cap model els FK;
   el Model estampa `size_system`/`grading_rule_set` com a columnes pròpies), però cada perfil mapeja un
   (fit,construction) → un **grading_rule_set distint**. Consolidar-los perdria el mapatge fit→ruleset. Són la
   **biblioteca de presets** legítima. → **D.2 gairebé buida** (res a esborrar amb seguretat).

5. **El cas «Numeric mal apuntat» (D.1) està INVERTIT respecte al brief:** el ruleset 91 té `size_system=32`
   (NUMERIC_EU_W) **correcte** pel seu nom; el que està desalineat és la `talla_base` de les seves regles (ancorada
   a ss=6, etiqueta '128', una referència d'alçada). I això és **metadata cosmètica que el motor IGNORA** (ancora a
   `model.base_size_label`, no a `rule.talla_base` — `grading_utils.py:37`). Re-alinear-ho és tocar dades de 61+
   regles per cap guany funcional. → **D.1 → DECISIONS PENDENTS** (la premissa del brief no es compleix).

6. **El canvi de fons (SizingProfile com a preset, no com a selector; consolidació de systems clon per-fit) és un
   sprint a part.** Aquesta nit: depurar superfícies (Fase B) + reetiquetar la Size Library; NO esborrar dades.

---

## A.1 — CENS DE SUPERFÍCIES

| # | Superfície | Front | Endpoint | Backend | Entitat | Veredicte |
|---|---|---|---|---|---|---|
| a | Wizard «3. Talles» (edició) | `ModelWizard.jsx:337-411` (fetch `:137`) | `GET sizing-profiles/` | `s2_views.py:64` (itera `SizingProfile` `:77`) | **SizingProfile** | **VIOLA** · capa 4 contamina capa 3 |
| b | Create-wizard pas Talles | mateix component (`ModelWizard.jsx`, `isEditMode` `:33`) | idem (a) | idem | **SizingProfile** | **VIOLA** |
| c1 | Size Library «SIZE SETS DISPONIBLES» | `SizingProfileSelector.jsx:268-310` (fetch `:115`, filtre Fit `:226-266`) | `GET sizing-profiles/` | `s2_views.py:64` | **SizingProfile** | **VIOLA** · el fit discrimina la "selecció d'escala" |
| c2 | SizeMapSetup taula systems | `SizeMapSetup.jsx:152` | `GET size-map/systems/` | `size_map_views.py:977` (itera `SizeSystem`) | **SizeSystem** | **CONFORME** (però gated `_Configure`) |
| d | RuleSetPicker/AxesSelector (model+item) | `RuleSetPicker.jsx`, `RuleSetCard.jsx:55-67` | `GET grading-rule-sets/` | `gradingAxes.js:103` `matchingRuleSets` | **GradingRuleSet** | **CONFORME** (referència capa 4) |
| e | Grading Rules CRUD | `GradingRuleSets.jsx:81` | `grading-rule-sets/` | `GradingRuleSetViewSet` | **GradingRuleSet** | **CONFORME** (referència) |

**A.1.f — consumidors de `SizingProfile`:** LLEGEIXEN `sizing-profiles/` (`s2_views.py:64`): `ModelWizard.jsx:137`
(VIOLA), `SizingProfileSelector.jsx:115` (VIOLA), **`CustomerDetail.jsx:184`** (3a superfície, fora de a-e — mostra
perfils del client com a inventari; mateixa contaminació, ANOTADA no-tocar). CREEN: `size_map_create_view`
(`size_map_views.py:920-952`, **aquí neixen els clons per-fit**), `clone_sizing_profile_view` (`s2_views.py:162`).
MOSTREN: `SizeSetCard.jsx`, `SizeSetDetail.jsx`. Serializer `SizingProfileSerializer` (`s2_serializers.py:91`)
arrossega `fit_type_codi/nom`.

## A.2 — MODEL DE DADES: on viu el fit

| Entitat | Camps de fit? | Capa | Veredicte |
|---|---|---|---|
| **SizeSystem** (`pom/models.py:292-338`) | **CAP** (codi/nom/base_unit/targets M2M/parent/customer_codi) | 3 (escala) | **PUR** ✓ |
| SizingProfile (`pom/models.py:860-900`) | target/construction/fit_type/garment_type/grading_rule_set/size_system/customer | JOIN (preset) | aquí viu el fit a nivell de SELECCIÓ |
| GradingRuleSet (`pom/models.py:506-622`) | fit_type/construction/garment_type_item/targets/size_system | 4 (graduació) | el fit discrimina aquí ✓ |
| Model (`models_app/models.py`) | `fit_type/target/construction` (char, capa 4) · `size_system/size_run_model/base_size_label` (capa 3) · `grading_rule_set` (FK, capa 4) | 3+4 | estampa columnes pròpies |

**VEREDICTE A.2: contaminació de SUPERFÍCIE.** `SizeSystem` pur → **cap camp a moure. Fase C BUIDA.**

## A.3.i — Cens SizingProfiles (27, tots 0-ref)
Cap model FK cap a SizingProfile (el Model estampa columnes). "Duplicats funcionals" (mateix system+target+garment,
difereix el fit): **grup ss29/WOMAN/T-shirt = {264,276,288,485,510}** (5, cada un → ruleset distint 75/79/81/76/98)
· **grup ss30/MAN/T-shirt = {335,347}** (2 → 84/86). **Difereixen en `grading_rule_set` → NO són redundants: són
presets fit→ruleset.** Consolidar-los perdria informació. → D.2 PENDENTS.

## A.3.ii — Cens SizeSystems (20)
Referenciats per models: **29 (42 models), 30 (1)**; la resta 0. Clons per-fit / redundàncies (candidats a
consolidar, **només llistar** D.3): **LOS Girl 48/49/50** (mateix run 2Y-12Y; el **49 `GIRL_LOS_02` porta "Knit
Regular" al nom** = fit dins la identitat de l'escala; 48/49 = 0-ref, 50 és la destinació amb 4 profiles+1 ruleset)
· shells buits 0-talles/0-ref: **31,33,39,40,26** · variants "Commercial" 41 (Kids), 42 (Baby).

## A.3.iii/iv — Audit ruleset.size_system vs run de les regles
**11 rulesets mal alineats** (`grs_ss ≠ rule_ss`); **10/11 tenen la `talla_base` a ss=6** (`TGIRL-EU-HEIGHT`,
referència d'alçada, etiqueta '128'):
- **Amb size_system declarat però talla_base a ss6:** 87 (BABY, 4 profiles), 88 (TODDLER, 2), 89 (KIDS, 2), **91
  (NUMERIC, 0 deps)**.
- **size_system NULL, talla_base a ss6:** 77,78,80,82,85,92 (0 deps). · **98** (Custom Alpha, talla_base a ss29, 1 profile).
- Dependents: **0 models, 0 GTI, 0 versions** per a tots 11. Només SizingProfiles (87/88/89/98) en pengen.

**Clau:** el ruleset **91 té `size_system=32` CORRECTE** (NUMERIC_EU_W); el desajust és a la `talla_base` de les
regles (ss6 '128'), que el motor **IGNORA** (`_apply_rule` ancora a `model.base_size_label`, no a `rule.talla_base`;
`grading_utils.py:32-39`). Re-alinear = tocar 61+ regles per cap guany funcional, amb risc als profiles de 87/88/89/98.
→ **La premissa de D.1 (re-apuntar size_system) no es compleix** (el size_system ja és correcte; el problema és
metadata cosmètica de la regla). **D.1 → DECISIONS PENDENTS.**

## A.4 — Seqüència del wizard + disseny objectiu
**Flux actual** (`ModelWizard.jsx`, 3 blocs, mateix component create+edit): 1·Identificació (`:254`) → 2·Peça
(target/GTI/construction `:292`) → 3·Talles (targeta=SizingProfile `:347` → run `:387` → base `:397`). Persistència
via `_resolve_garment_def` (`views.py:387`): `size_system`(:414)/`size_run_model`(:428)/`base_size_label`(:430)/`grading_rule_set`(:419).

**La graduació es tria DOS cops:** (i) IMPLÍCIT i dolent al pas Talles (`sizingResult` deriva `grading_rule_set_id`
del perfil, `:75`; enviat a `skeletonPayload:178`); (ii) EXPLÍCIT i bo a la fitxa (`RuleSetCard`→`update-step2`).

**💡 DISSENY OBJECTIU (canvi mínim, només `ModelWizard.jsx` + 1 relaxació backend):**
- Pas Talles → llistar **`SizeSystem` PURS** (dedupe natural) via `GET size-systems/` (ja existeix,
  `SizeSystemViewSet` `pom/views.py:59`; cal afegir-hi filtre `targets` — additiu) + run/base. Treure el fit i la graduació del pas.
- Treure `grading_rule_set_id` de `sizingResult`(`:75`) i `skeletonPayload`(`:178`).
- La graduació es queda a `RuleSetCard` (secció pròpia, ja construïda). Cap picker nou.
- **Relaxar el guard de create** (`views.py:454-456`): avui 400 si `base_size` sense `grading_rule_set_id`; sota la
  llei la base és escala pura i s'ha de poder desar sense graduació (`update_model_step2` ja ho permet).

**Watchpoints:** (1) el guard `views.py:454-456` bloqueja el canvi mínim → relaxar. (2) materialització acoblada al
ruleset (`views.py:538-543,616-621`) — compatible: la graduació entra després via `update-step2` que re-materialitza.
(3) `CustomerDetail.jsx:184` 3a superfície contaminada → fora d'abast, anotada. (4) l'origen dels clons per-fit és
`size_map_create_view` → reforma de fons de SizingProfile = sprint a part.

---

## GATE AUTOMÀTIC (criteris objectius) — classificació

**Criteri:** procedir només si (no toca motor · no esborra dades fora de la llista D · migracions additives ·
reutilitza components existents, cap de zero).

| Punt | Decisió | Motiu |
|---|---|---|
| **B.1** depurar pas Talles (llistar systems purs; treure fit+graduació) + relaxar guard create + filtre `targets` a `SizeSystemViewSet` | **PROCEDIR** | reutilitza `size-systems/` + components; backend additiu; cap motor; cap dada esborrada |
| **B.2** graduació com a pas/secció propi | **PROCEDIR** (mínim) | ja viu a `RuleSetCard`; B.1 en treu l'arrossegament implícit → queda separada |
| **B.3** Size Library: separar "preset de graduació" de "selector de runs" | **PROCEDIR (reetiquetatge)** | reframe/labels + i18n reutilitzant la UI existent; NO consolidar dades (presets legítims) |
| **B.4** i18n ca/en/es del text nou | **PROCEDIR** | guardians |
| **Fase C** (camps de fit a capa 3) | **BUIDA** | `SizeSystem` pur (A.2) |
| **D.1** re-apuntar ruleset Numeric | **DECISIONS PENDENTS** | premissa inverteix (size_system ja correcte; és metadata de regla cosmètica que el motor ignora) |
| **D.2** consolidar profiles 0-ref | **DECISIONS PENDENTS** | no són duplicats reals (fit→ruleset distint = biblioteca de presets); consolidar perdria info |
| **D.3** systems clons per-fit | **LLISTAR** (cap escriptura) | afecten decisió d'Agus; A.3.ii ja els llista |

---

*Fase A tancada. Read-only respectat. RESULTAT de Fase B/E i DECISIONS PENDENTS s'annexen al final.*
