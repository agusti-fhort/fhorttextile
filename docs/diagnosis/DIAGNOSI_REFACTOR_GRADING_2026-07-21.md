# DIAGNOSI — Refactor grading (G6) + símptoma viu al model TATE

Data 2026-07-21 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` @ `afdb5ef` · schemas `fhort` i `los`

**Abast.** Refer la foto del domini de grading —que ha canviat molt des de les diagnosis de paritat del 24/06 (dissolució de `FittingDetail`, tasca unificada `size_check`, S10, LOSAN v3)— **abans** de decidir res de G6, amb el símptoma viu del model TATE (163) com a fil conductor.

**Convenció.** Cada afirmació porta `fitxer:línia` o la query que la sosté. **"NO EXISTEIX" = confirmat absent al codi/BD, no especulat.** Les propostes van marcades `💡 PROPOSTA (a validar)` i estan separades dels fets; les decisions són humanes (Patró C).

**Cap escriptura.** Zero canvis a BD, zero canvis de codi, cap migració, cap restart. L'única escriptura d'aquesta sessió és aquest document.

---

## Resum executiu

1. **La causa del símptoma B0 és una sola i està confirmada per dues vies independents (codi i dades).** El `GradingRuleSet 108` que el model 163 té assignat és **l'únic ruleset buit del tenant** (0 `GradingRule` de 45 rulesets). Assignar-lo va **esborrar les 25 `ModelGradingRule` residents i crear-ne 0**, i el motor, davant d'un POM amb base però sense regla, **no falla: copia el valor base a totes les talles com a `FIXED`**. La propagació va córrer, va retornar 200 amb `graded_count=100`, i va propagar la fila base repetida.

2. **El silenci no és un bug puntual: és una cadena de quatre baules que no verifiquen res.** (a) `materialize_model_grading_rules` fa `delete()` abans de saber quantes regles crearà i **el seu retorn es descarta**; (b) el gate `_te_regles` dona OK **només perquè el punter existeix**, sense mirar si el ruleset té regles; (c) el motor tracta "sense regla" com a `FIXED` legítim; (d) `_load_grading_rules` empassa **qualsevol** excepció i retorna `{}`, que és exactament el mateix estat. Qualsevol de (b) o (d) tornaria a produir el símptoma encara que s'arreglés el ruleset buit.

3. **La regla correcta existeix i és a un pas del model — simplement no hi està cablada.** L'item del 163 (`GarmentTypeItem 5`) i el `SizingProfile` de client (524) apunten tots dos al `GradingRuleSet 115` (`BRW · Blusa · ALPHA_EU_W`, **34 regles**, `origen=CLIENT_RUN`, el contenidor validat a l'S10). El model apunta al 108. **`Model.grading_rule_set` és l'ÚNICA font que entra al motor**; `SizingProfile` i `GarmentTypeItem.grading_rule_set` són catàleg sense efecte. No és un problema de dual-path competint: és un **punter únic mal apuntat, sense cap validació de coherència**.

4. **La premissa "B1 paritat" del brief ha caigut: les peces ja es van implementar el 07/07.** `arxiu/DIAGNOSI_IMPL_PARITAT_GRADING.md:1` porta capçalera `⚠️ SUPERADA 2026-07-07 — implementada`. Peces 1/2/5 existeixen, **Peça 4 (eix de versions a Escalat) va ser REVOCADA per llei** (propagar = llenç net), i `generar-grading` **ja no és orfe**. El que sí segueix obert és la **contradicció llei↔codi**: `DECISIONS.md:80-86` declara l'auto-propagació "codi a JUBILAR" i segueix viva a `services_size_check.py:200` i `fitting/services.py:455`.

5. **El motor de patrons NO és el forat.** La projecció `GradedSpec`→CAD existeix, és completa i s'ha exercitat end-to-end en dry-run sobre el 163: DXF de 471.641 bytes, autovalidació a 0 µm. El gate d'exportació per segell és **real i bloqueja de veritat** (no és audit). El 163 no és avui golden path per **quatre forats encadenats, tots aigües amunt del motor**: ruleset buit → grading 100% `FIXED`/delta 0 → cap versió aprovada → **2 POMs ancorats de 25**.

6. **Dues troballes estructurals que el brief no demanava i que condicionen G6:** el schema **`los` és completament buit** (0 models, 0 rulesets — LOSAN opera com a `Customer id=6` dins `fhort`), i **dues `GradingVersion` estan `aprovada=True` amb `aprovada_per`/`data_aprovacio` NULL** (gv30 del model 162, gv53 del model 186) — impossibles via `seal_model_grading`, i **cegen l'audit d'estalitud**. gv53 és precisament la que va alimentar l'única exportació real del tenant.

---

## BLOC B0 — El símptoma viu (model 163 / TATE)

### B0.1 · Foto de l'estat a BD (schema `fhort`)

`Model 163` = `BRW-FW26-0001 · Blusa TATE Crudo`, customer **7 (BRW)**, `garment_type_item_id=5`, `size_run_model='XS·S·M·L'`, `base_size_label='S'`, `measurements_version=1`.

| Objecte | Estat real |
|---|---|
| `grading_rule_set_id` | **108** — `'Mango EU woven woman regular - only dress'`, `origen=None`, `customer=NULL`, `size_system=29`, **0 regles** |
| `ModelGradingRule` (model 163) | **0** (ni actives ni totals) |
| `GradingRule` (rule_set 108) | **0** — únic ruleset buit de 45 al tenant |
| `GradingVersion` | 2, totes del SF 53: **gv79** (v1, inactiva, `aprovada=False`, 15:41:24) i **gv80** (v2, **activa**, `aprovada=False`, 15:42:55) |
| `GradedSpec` | gv79: 125 specs · gv80: 100 specs — **100% `grading_type_applied='FIXED'`** en totes dues |
| Specs amb valor ≠ base | **0 / 125** i **0 / 100** |
| `generated_from_version` | `[1]` = `measurements_version` → **formalment NO són stale**: són fresquíssimes i buides de contingut |
| `SizeFitting` | 53 (`Proto`, **TallesGenerades**, de juny) i 79 (`IMP-163-2`, `SizeSet`, `Tancat`, de l'import del 13/07) |
| `BaseMeasurement` | **25 files, 25 amb valor**, totes `origen='MANUAL'`, creades 2026-07-13 08:13 |
| Regles amb base / bases sense regla | **0 amb regla · 25 bases sense regla** |
| `ModelGradingOverride` | **0** |
| `GradingRuleHistory` | **0 files a tot el tenant** — no hi ha auditoria de l'esborrat |

**El desajust d'identitat, en tres nivells:** el model és de client **BRW**, el seu `size_system` és el **67 (`WOMAN_LOS_01`, de LOS)**, i el seu ruleset declara `size_system=29`. Els tres discrepen.

### B0.2 · El camí del canvi de ruleset

| Baula | `fitxer:línia` |
|---|---|
| `RuleSetCard` — **ja no canvia res**, només navega | `frontend/src/components/model/RuleSetCard.jsx:26,37-41` |
| Wizard bloc 4, `RuleSetPicker` (**única UI que escriu el punter**) | `frontend/src/pages/ModelWizard.jsx:556-566` · payload `:266,275` |
| `PATCH /api/v1/models/:id/update-step2/` | `frontend/src/api/endpoints.js:57` → `models_app/urls.py:193` |
| View | `models_app/views.py:690-726` |
| Resolutor de FK | `models_app/views.py:516-520` |
| Materialització | `models_app/views.py:720-725` → `models_app/services.py:147-168` |

Cos de `materialize_model_grading_rules` (`models_app/services.py:147-168`):

```
:156   model.grading_rules.all().delete()      ← WIPE total, sense filtre, abans de saber res
:157-166  ModelGradingRule(... origen=origen, actiu=True)
:167   ModelGradingRule.objects.bulk_create(objs)
:168   return len(objs)                        ← el retorn es DESCARTA a views.py:724
```

**Què li passa a cada cosa en canviar el ruleset:**

| Objecte | Què passa | Evidència |
|---|---|---|
| `ModelGradingRule` existents | **Wipe-and-recreate.** Cap fusió. Qualsevol regla d'autoria `origen='MANUAL'` es perd sense avís | `services.py:156,163` |
| `GradedSpec` vives | **NO es toquen. Queden ràncies.** Cap delete, cap invalidació, cap flag | tot `views.py:690-726` no menciona `GradedSpec` |
| `GradingVersion` activa | **NO es bumpeja ni es toca** | ídem |
| `SizeFitting.estat` | **NO es reancora** — queda a `TallesGenerades` mentint | únic escriptor: `pom/services.py:219-221,385-389` |

La font passada és `model.grading_rule_set.regles.all()` (`views.py:725`) — **sense filtrar `actiu=True`**, mentre el motor sí el filtra (`pom/services.py:565`).

### B0.3 · Cens de superfícies de propagació

| # | Superfície | Component:línia | Endpoint | View:línia | Què llegeix | Òrfena / gate |
|---|---|---|---|---|---|---|
| 1 | Botó **«Propagar a grading»** (tab Mesures) | `ModelSheet.jsx:504-511` → `:333,344-355` (`new_version:true`) | `POST models/:id/generar-grading/` | `models_app/views.py:1651-1709` | MGR viva → fallback ruleset + `BaseMeasurement`; esborra overrides `:1669`. **Crea v+1** | No. Gate suau: modal 2 passos `:553-590` |
| 2 | Botó **«Crear nova versió»** (Escalat, només amb 409 `sealed`) | `PropagatedEditor.jsx:64-70` | mateix | `views.py:1651-1709` | ídem #1 | No, però **amagat rere gate** `:56` |
| 3 | Edició de cel·la a Escalat | `PropagatedEditor.jsx:45-60` | `POST models/:id/escalat/ajustar-talla/` | `views.py:1891`, motor `:1999` | regles + base/override. **Reutilitza versió vigent in-place** (`:1907` explícit) | No |
| 4 | Canvi de règim del POM | `PropagatedEditor.jsx:73-78` | `POST models/:id/pom/:pom/regim/` | `views.py:2614` | escriu MGR `origen='MANUAL'`; **NO regenera res** (`:2628`) | **Propagació aparent sense propagació real** |
| 5 | Tancar peça de fitting | `SessionActions.jsx:32` · `FittingDetail.jsx:203` | `POST piece-fittings/:id/close/` | `fitting/views.py:532-551` → `fitting/services.py:454-460` | base consolidada + MGR. **Bump v+1** | Gate: `if changed` `:449` |
| 6 | Resoldre Size Check | `CheckMeasureEditor.jsx:330` | `POST size-checks/:id/resolve/` | `views_size_check.py:63-75` → `services_size_check.py:191-205` | base + MGR. **Bump v+1** | **Doble gate silenciós** `if base_changed and te_deltes` `:191` |
| 7 | `regenerar-talles` | — | — | `pom/grading_views.py:35-53` | motor directe, in-place | **ÒRFENA** (0 hits a `frontend/src/`) |
| 8 | `set-size-override` | — | `endpoints.js:82` definit, **cap `.jsx` el crida** | `views.py:1769-1888` | overrides + motor in-place | **ÒRFENA** |
| 9 | `tancar-base` | — | — | `pom/grading_views.py:12-30` → `pom/services.py:340-399` | genera **només si no hi ha cap `GradedSpec`** `:381` | **ÒRFENA** + gate dur |
| 10 | `confirmar-talla-base` (wizard antic) | — | — | `pom/wizard_views.py:240-292` | `_te_regles` + motor `:273` | **ÒRFENA** |
| 11 | `clone_model_for_qa` | — | — | `management/commands/clone_model_for_qa.py:46,111` | — | CLI |

**Font única de canvi de ruleset:** només el Wizard bloc 4. Cap altra UI escriu `Model.grading_rule_set` (grep exhaustiu a `frontend/src/`).

### B0.4 · Punts de fallada silenciosa i causa arrel

**La cadena que produeix el símptoma, baula a baula:**

| # | Baula | `fitxer:línia` | Per què és silenciosa |
|---|---|---|---|
| 1 | Wipe incondicional abans del `bulk_create` | `models_app/services.py:156` | Esborra 25 sense saber que en crearà 0 |
| 2 | El retorn de la materialització es descarta | `models_app/views.py:724` + `services.py:168` | El 200 (`views.py:726`) no diu quantes regles s'han materialitzat |
| 3 | `_te_regles` accepta un punter a ruleset buit | `pom/services.py:527-550` (`return bool(model.grading_rule_set_id)`) | El gate dur de `views.py:1609` deixa passar |
| 4 | `_load_grading_rules` retorna `{}` | `pom/services.py:552-576` | Sense regles no llança: retorna diccionari buit |
| 5 | **El motor tracta "sense regla" com a `FIXED` legítim** | `pom/services.py:191-198` (`rule is None` → `graded_val = base_val`) | Cap warning, cap excepció. Genera taula plena i plana |
| 6 | L'endpoint reporta èxit | `views.py:1712` (`graded_count=100`) | L'usuari veu "propagat correctament" |

**Causa arrel (confirmada creuant traça i foto):** *l'assignació del `GradingRuleSet 108` —buit— va buidar les regles residents del model, i el motor va graduar les 25 bases a `FIXED` sobre totes les talles, retornant èxit.* Els candidats alternatius que la traça havia plantejat queden **descartats per dades**: no és desalineació parcial de `pom_id` (la intersecció és 0, no parcial); no és "va canviar el ruleset i no va propagar" (hi ha dues propagacions datades posteriors); no és el `pass` tolerant de `views.py:516-520` (el punter **sí** va canviar, a 108); no és divergència punter↔MGR residents (no queda cap MGR).

**Segona porta a la mateixa fallada, independent del ruleset buit:** `pom/services.py:574-576` — `_load_grading_rules` embolcalla la càrrega en un `except` que fa `logger.warning` + `return {}`. **Qualsevol error carregant regles gradua tot a `FIXED` amb un 200 OK.** Mateix símptoma exacte, causa diferent. Mentre això hi sigui, arreglar el 163 no tanca la classe de bug.

**Altres `except` que empassen al mateix camí:**

| `fitxer:línia` | Empassa | Efecte |
|---|---|---|
| `models_app/views.py:516-520` | `GradingRuleSet.DoesNotExist` → `pass` | Id inexistent = 200 OK amb ruleset intacte |
| `models_app/views.py:949-950` | `except Exception: pass` (càrrega de `GradedSpec` a `taula-mesures`) | **Escalat es dibuixa buit i retorna 200** |
| `models_app/views.py:958-959` | → `rules_by_pom = {}` | Columna de règim buida com si no hi hagués regla |
| `models_app/views.py:1020-1021` | → `tancat=False` | Mostra editable una taula tancada |
| `pom/services.py:587-589` | `_load_model_overrides` → `{}` | Overrides perduts en silenci |
| `pom/services.py:603-605` | `_load_base_measurements` → `{}` | 0 specs però `estat='TallesGenerades'` (`:219-221`) — **estat mentider** |

**`_get_or_create_grading_version` (`pom/services.py:608-643`)** — resposta a la pregunta del brief: **no** pot reutilitzar una versió segellada (`:626-628` llança), però **sí** reutilitza una versió activa **no segellada** amb `GradedSpec` vells, i `_upsert_graded_spec` (`:850-861`) fa `update_or_create` **sense `delete()` previ**. Les cel·les que el càlcul nou ja no produeix (talla fora del run nou, POM sense base, cel·la STEP saltada a `:200-202`) **sobreviuen com a specs fantasma** barrejades amb les noves, i el lector (`views.py:942`) no les distingeix. Afecta els camins in-place (#3, #7, #8, #9, #10), no els de bump. A més, crea versió **silenciosament** quan no n'hi ha cap (`:638-642`): sense `creat_per`, sense `nom`, sense guard, sense watchpoint.

**Anomalia col·lateral de selecció de SizeFitting:** `views.py:1623` tria amb `.first()` i `ordering=['model','numero']` → el grading del 163 sempre cau al **SF 53 (Proto, de juny)**, mai al **SF 79 (`SizeSet`, el de l'import del 13/07 que porta les 25 bases)**. Possiblement no és el que l'Agus creu estar mirant.

**Cronologia reconstruïda:**

| Moment (UTC) | Fet | Evidència |
|---|---|---|
| 2026-06-10 08:55 | Es crea el model 163 i el SF 53 (Proto) | `Model.created_at`, `SizeFitting.data_creacio` |
| 2026-07-13 08:13 | Import: es crea SF 79 i s'escriuen les 25 `BaseMeasurement` | `MeasurementChangeLog` (25 entrades, `context='import'`) |
| entre 07-13 i avui | El model tenia **25 MGR actives** i `grading_rule_set` **NULL** | testimoni a `pom/services.py:536` |
| **avui, abans de 15:41** | **Assignació de `grading_rule_set=108`** → wipe: esborra 25 MGR, crea 0 | `views.py:714-725` + `services.py:156`; MGR=0 |
| 2026-07-21 15:41:24 | 1a propagació → gv79, 125 specs, run amb XXS, **100% FIXED** | `GradingVersion 79` |
| entre 15:41 i 15:42 | Canvi de `size_run_model` (desapareix XXS) | talles gv79 vs gv80 |
| 2026-07-21 15:42:55 | 2a propagació → gv80 (activa), 100 specs, **100% FIXED** | `GradingVersion 80` |

> **Veredicte B0:** causa arrel identificada i confirmada per dues vies. **Cal decidir**, no cal investigar més. Nota de domini: la llei §2 diu *"regla sense base = cel·la ABSENT"*; el cas **simètric i invers** (base sense regla) **no té llei** i avui produeix una cel·la `FIXED` fabricada. És el forat semàntic exacte on viu el silenci.

---

## BLOC B1 — Paritat fitting↔grading (foto refeta)

**Premissa del brief invalidada:** `docs/diagnosis/arxiu/DIAGNOSI_IMPL_PARITAT_GRADING.md:1` porta capçalera **`⚠️ SUPERADA 2026-07-07 — implementada (6 peces paritat grading; helper bump_grading_version_and_generate; 66161e2/423853a/96e7fc8/b495442)`**. Les peces no són pendents: van entrar el 07/07.

### B1.1 · Estat de les peces dissenyades

| Peça | Estat | Àncora actual |
|---|---|---|
| **1** · helper `bump_grading_version_and_generate` | **EXISTEIX** (signatura ampliada) | `pom/services.py:646-714` |
| **2** · botó «Propagar» conscient | **EXISTEIX, DIFERENT DE LLOC** — viu a **Mesures**, no a `PropagatedEditor` | backend `views.py:1642,1651-1709`; front `ModelSheet.jsx:333-351,505-513,572-584` |
| **4** · eix de versions a Escalat | **NO EXISTEIX — REVOCADA PER LLEI** | `fittingGridAdapter.jsx:106` («propagar = llenç net, NO eix de versions»); `PropagatedEditor.jsx:13-14`. Correlat backend: `views.py:1665-1669` esborra overrides |
| **5** · watchpoint de reobertura | **EXISTEIX PARCIAL** — només al camí conscient | `views.py:1696-1709`. Els altres camins només fan `logger.warning` + nota (`pom/services.py:684-688`) |

**`generar-grading` JA NO ÉS ORFE:** dos consumidors reals — `ModelSheet.jsx:348` i `PropagatedEditor.jsx:66`.

**Orfes NOUS detectats** (view viva, cap consumidor a `frontend/src/`): `set-size-override` (`endpoints.js:81-82` declarat però mai cridat), `regenerar-talles`, `tancar-base`, `confirmar-talla-base`. **Tots quatre poden escriure `GradedSpec`**, i tres poden crear v1 silenciosa via `_get_or_create_grading_version`.

### B1.2 · Auto-propagació — la llei §2 NO s'ha executat

`DECISIONS.md:80-86` segueix dient que l'auto-propagació és *"codi a JUBILAR"*. **Les dues funcions existeixen i segueixen propagant** (el sprint del 07/07 les va **centralitzar** al helper, no jubilar):

| Funció | Línia ACTUAL (era) | Propaga? | Evidència |
|---|---|---|---|
| `resolve_size_check` | `models_app/services_size_check.py:98` (era `:230`) | **SÍ** | `:191-209` → helper a `:200`, `nom='Size check N'` |
| `close_piece_fitting` | `fitting/services.py:383` (era `:469`) | **SÍ** | `:449-463` → helper a `:455`, `nom='Fitting sessió N'` |

`close_piece_fitting` **no ha desaparegut** amb la dissolució de `FittingDetail`; la pàgina `FittingDetail.jsx` tampoc (ruta viva a `App.jsx:294`), i conviu amb la superfície nova `SessionActions.jsx:32`. Canvis reals respecte la foto vella: ara és **atòmic** (`:424`) i **ja no escriu talles no-base** (`:392-395`).

### B1.3 · Qui crea v+1 avui (taula 1B refrescada)

| Caller | Superfície | Bump? | Gates |
|---|---|---|---|
| `pom/services.py:713` (dins el helper) | — | **SÍ, v+1** (`:695`) | guard D-1 `:678-683` |
| `views.py:1712` (`new_version=False`) | cap consumidor front l'usa així | **NO — reutilitza l'activa** | `_te_regles` `:1609`; 409 sealed `:1713` |
| `views.py:1863` (`set_size_override_view`) | **orfe UI** | **NO** | 409 sealed + rollback `:1864-1870` |
| `views.py:1999` (`escalat_ajustar_talla_view`) | tab Escalat | **NO** (explícit `:1907`) | 409 sealed `:2000-2004` |
| `pom/grading_views.py:42` | **orfe** | **NO** | 409 sealed |
| `pom/services.py:382` (`close_base`) | **orfe** | **NO** (v1 implícita possible) | només si 0 specs `:381` |
| `pom/wizard_views.py:273` | **orfe** | **NO** | `_te_regles` + run + base `:269` |
| `fitting/services.py:455` (indirecte) | tancar peça | **SÍ, v+1** | `if changed` `:449` |
| `services_size_check.py:200` (indirecte) | resoldre check | **SÍ, v+1** | `base_changed and te_deltes` `:191` |

**Acoblament bump↔generació:** l'únic punt que crea v+1 és `pom/services.py:695`, sempre seguit de generació a `:713` → *bump sense generació no pot passar*. **Però la generació SÍ pot crear versió sense bump**, per la porta silenciosa `_get_or_create_grading_version:638-642`. L'invariant "una sola activa" el sostenen codi (`:691`) i BD (`fitting/migrations/0016_gradingversion_una_sola_activa.py`).

> **Veredicte B1:** la paritat està feta; el que queda obert no és construir peces sinó **resoldre una contradicció llei↔codi** (auto-propagació viva contra la llei §2) i **decidir el destí de 4 endpoints orfes amb capacitat d'escriptura**.

---

## BLOC B2 — Dual-path G6 (inventari estructural)

**`DIAGNOSI_G6_DUAL_PATH.md` (2026-07-13) queda PARCIALMENT OBSOLETA** — els sprints G6-A i G6-B l'han executada. Es marca a sota què ha caigut.

### B2.1 · Qui decideix quin ruleset mana (Q9)

| Camp | Lectors | Escriptors | Qui guanya |
|---|---|---|---|
| **`Model.grading_rule_set`** (`models_app/models.py:193-199`) | `pom/services.py:527-550,552-576`; `views.py:57-59,634-639,720-725,1219-1220,2659-2660`; `services.py:123-124`; `services_size_check.py:90-93`; `extraction_views.py:719-720,1550`; `serializers.py:184-207` | `views.py:516-518` (**payload**), `:712-713`; `extraction_views.py:1997-2093`; `seed_losan_models.py:211` | **AQUEST. L'únic que entra al motor** |
| `SizingProfile.grading_rule_set` (`pom/models.py:927`) | `pom/s2_views.py:141-148`; `s8_views.py:103-127`; `size_map_views.py:696-699,984` | `size_map_views.py:936,945-947`; `s2_views.py:227`; seeds | **Catàleg de tria. Zero efecte** — cap FK `Model→SizingProfile` |
| `GarmentTypeItem.grading_rule_set` (`tasks/models.py:319-324`) | `tasks/serializers_b.py:117-134`; `views_b.py:858`; `models.py:336-337` | `tasks/serializers_b.py` | **Fulla morta aigües avall** |

`_resolve_garment_def` (`views.py:485-524`) deriva `garment_type`/`garment_group` de l'item (`:496-504`) **però el ruleset només del payload** (`:516-518`). **NO EXISTEIX** propagació item→model. `SizingProfile` i `GarmentTypeItem` **no apareixen ni una vegada** a `pom/services.py`.

**Per al 163 concret, els tres camins divergeixen:**

```
Model 163          → rs 108 (Mango, customer NULL, size_system 29, 0 regles)
GarmentTypeItem 5  → rs 115 (BRW · Blusa · ALPHA_EU_W, 34 regles)
SizingProfile 524  → rs 115 (customer 7, is_default)
Model.size_system  = 67   ·   rs108.size_system = 29
```

**Font inequívoca: `Model.grading_rule_set = 108` — i és la buida.** Les 34 regles reals no arriben mai al motor.

**Divergència sistèmica, no aïllada:** model 188 (model rs=79 / item rs=186). Models **164-167, 173-177, 256-260**: item rs=115 amb **model rs NULL** (10+ models). Coincideixen: 185, 267, 268, 269.

### B2.2 · `GradingException` (Q10) — **JUBILADA, verificat**

- **Taula NO EXISTEIX** a cap schema (`information_schema.tables` → 0 files). Migració `pom/migrations/0038_delete_gradingexception.py` aplicada a `public`, `fhort` i `los` (2026-07-13 16:16).
- **Lectors al codi: CAP.** Només làpides documentals (`pom/models.py:724-729`, `pom/services.py:116,186-188`, `models_app/models.py:660-663`, i seeds).
- **Solapament amb `ModelGradingOverride`: era total i declarat.** `models_app/models.py:656-670` diu que existeix perquè `GradingException` vivia al ruleset compartit i *"would leak to every model using that set"*. Avui hi ha una sola branca (`pom/services.py:180-186`).
- `ModelGradingOverride`: **0 files a `fhort` i a `los`** — viu però efímer per disseny (dos esborradors el buiden a cada propagació: `views.py:1668-1669`, `:1975`).

### B2.3 · `GradingRuleSet.target` FK vs M2M `targets` (Q11)

Model: `pom/models.py:566-570` (FK) i `:571-577` (M2M, declarada **autoritativa** a `:563-565`).

**Sí hi ha codi VIU que depèn de la FK singular:** `pom/grading_utils.py:339`, dins `derive_grading_rule_set` — és el filtre anti-proliferació que decideix **si reutilitza o crea un ruleset nou**. És l'únic lector decisori, i el deute ja és al codi (`grading_utils.py:92-95`). La FK **NO és exposada** al serializer; la M2M sí i és escrivible (`pom/serializers.py:287`). **NO EXISTEIX** cap `RunPython` que copiï FK→M2M; `s2_views.py:195` copia la FK al clon i **no** la M2M.

**Dades (`fhort`, 45 rulesets):** FK ple 44 · M2M ple 44 · FK sense M2M **1** (id 98) · M2M sense FK **1** (id 93) · **10 files on FK i M2M no coincideixen**, de les quals **8 tenen M2M múltiple que la FK no pot representar** (87-90, 175-178). `los`: N/A.

### B2.4 · `GateEvent` i guard de segellat (Q12)

**Transicions reals (`fhort`, 16 events / 7 models; `los`: 0):** `Dev→Proto` 6 · `Proto→SizeSet` 3 · `SizeSet→PP` 2 · `PP→TOP` 2 · `PP→SizeSet` 1 · `TOP→PP` 1 · `SizeSet→Proto` 1. **Totes adjacents, cap salt, cap cicle.**

**Però les dades són lineals per costum, no per construcció.** `tasks/models.py:140-159`: `from_phase`/`to_phase` són `CharField` **sense `choices`**, `Meta` sense constraints. `advance_phase_gate` (`tasks/services_d.py:24-52`) valida només `to_phase ∈ FASE_CHOICES` (`:30-31`) i `frm != 'TOP'` (`:33-34`): **no comprova adjacència, ni direcció, ni self-loop**. Un `advance` cap enrere passa **i segella** (`:45-48`). `regress_phase` (`:55-69`) **no toca cap `GradingVersion`** → retrocedir la fase NO dessegella.

**El guard de segellat és REAL, no audit** (§B4 de la diagnosi vigent **ha caigut**):

1. **Porta d'escriptura** — `pom/services.py:626-628` llança `SealedGradingVersionError` (payload 409, `:32-84`). El `try/except` que abans se l'empassava **s'ha retirat**.
2. **Segona porta** — `_upsert_graded_spec` re-comprova i llança a `:847`.
3. **Guard del bump** — `:677-679`, amb `allow_reopen_sealed`.

Predicat únic: `sealed_active_version` (`:86-97`). **El forat REST està tancat:** `GradingVersionViewSet` (`fitting/views.py:76-100`) és ara `ReadOnlyModelViewSet` → escriptures 405; l'única és `POST .../approve/` amb capability `CLOSE_GATES` (`:98-100`). **Des-aprovar no existeix per API.**

Audit separat i correcte: `fitting/staleness.py:89`, exposat a cada lectura (`fitting/serializers.py:29-40`).

**🔴 Dades del segell (29 `GradingVersion` a `fhort`):** aprovades = 4. gv65 (model 185) i gv67 (model 182) tenen `aprovada_per` + `data_aprovacio` poblats. **gv30 (model 162) i gv53 (model 186) tenen `aprovada=True` amb `aprovada_per=NULL` i `data_aprovacio=NULL`** — `seal_model_grading` escriu sempre els tres camps, per tant **no les pot haver segellades**. A més **cegen l'audit**: `staleness.py:108` només compara canvis amb `created_at > gv.data_aprovacio`. **gv53 és la que va alimentar l'única exportació real del tenant.**

### B2.5 · `db_constraint=False` cross-schema (Q13)

Motiu estructural: `fhort.pom` és **SHARED *i* TENANT** (`settings.py:55,68`); `tasks`, `models_app`, `fitting` són només TENANT (`:67,69,70`).

**Direcció `pom→tasks` (7 ocurrències: `pom/models.py:247-251,434-439,473-477,543-547,551-554,642-645,930-934`): CONSISTENT.** 0 constraints reals de `pom_*` cap a `tasks_*` a `fhort`.

**Direcció `tenant→pom` (2 ocurrències: `models_app/models.py:716-722` `ModelGradingRule.pom`, `:902-907` `SizeCheckLine.pom`): INCONSISTENT.** Diuen que un constraint cap a `pom_pommaster` petaria a `public`, però **hi ha FKs idèntiques, del mateix schema, cap a la mateixa taula, amb constraint REAL**: `models_app_basemeasurement`, `models_app_measurementchangelog`, `models_app_modelgradingoverride`, `models_app_model` (×4), `tasks_garmenttypeitem` (×3).

**Cas testimoni:** `ModelGradingOverride.pom` (`models_app/models.py:672`, **amb** constraint) vs `ModelGradingRule.pom` (`:716-722`, **sense**, amb la justificació escrita al que no en té) — mateixa app, schema, taula destí i `on_delete=PROTECT`. **El criteri declarat és empíricament fals** i el trenca el ~78% de les FKs de la seva pròpia direcció. **Orfes reals avui: 0.**

> **Veredicte B2:** no hi ha "dual-path" competint. Hi ha **un únic path efectiu** (`Model.grading_rule_set`) i **dues fonts de catàleg decoratives** que ningú connecta — cosa que fa que un punter mal apuntat sigui indetectable. El que cal decidir és si l'item/perfil han de **derivar** el ruleset o només **suggerir-lo**.

---

## BLOC B3 — Dades

**Fet transversal:** el schema **`los` és BUIT** (0 `Model`, 0 `GradingRuleSet`, 0 `GradingRule`, 0 `SizingProfile`, 0 `POMMaster`, 0 `GradingVersion`). El tenant existeix (id 13, domini `los.fhorttextile.tech`) però **tot LOSAN viu dins de `fhort` com a `Customer id=6`**. `fhort`: 1005 models, 45 rulesets, 1148 `GradingRule`, 327 MGR, 29 `GradingVersion`, 1432 `GradedSpec`.

### B3.1 · `GradingRuleSet.origen` NULL (Q14)

`fhort`: 45 total = CANONICAL **11** · CLIENT_RUN **21** · IMPORT 0 · **NULL 13**. (`DECISIONS.md` deia 14; la xifra real avui és 13.)

| id | nom | customer | size_system | regles |
|---|---|---|---|---|
| 76 | EU Woven Woman Slim | — | 29 | 61 |
| 77 | EU Woven Woman Relaxed | — | **NULL** | 61 |
| 78 | EU Woven Woman Oversized | — | **NULL** | 61 |
| 80 | EU Knit Woman Slim | — | **NULL** | 40 |
| 82 | EU Stretch Woman Bodycon | — | **NULL** | 19 |
| 85 | EU Woven Man Slim | — | **NULL** | 35 |
| 92 | EU Woven Dress Flared | — | **NULL** | 9 |
| 93 | EU Knit Baby Months | — | 42 | 9 |
| 98 | Custom Alpha EU — Women | — | **NULL** | 19 |
| **104** | **LOS Kids Knit Regular 2Y-12Y** | **6 LOSAN** | 50 | 19 |
| 107 | Importació fitxa · FTT-CO27-0001 | — | 29 | 20 |
| **108** | **Mango EU woven woman regular** | — | 29 | **0** |
| 110 | Importació fitxa · BRW-SS27-0001 | — | 29 | 6 |

**Casos vermells:** **104** és de client (LOSAN) sense classificar → **viatjaria en una còpia a tenant nou, violant RUN-CLIENT**. **107** i **110** són literalment importacions de fitxa. **108** és el ruleset buit del símptoma B0.

### B3.2 · Bug de provinença (Q15) — **CONFIRMAT (codi + dades)**

`materialize_model_grading_rules` **no decideix res**: rep `origen` per paràmetre (`models_app/services.py:147`) i el copia (`:165`). **El bug són els tres call-sites del wizard, que passen la constant literal sense mirar mai `model.grading_rule_set.origen`:** `views.py:639` (alta simple), `:674` (alta multi-peça), `:724` (`update_model_step2`). L'únic camí honest és l'import: `extraction_views.py:2091` passa `origen='IMPORTED'`.

Creuament `ruleset.origen` × `MGR.origen` (327 MGR): **CLIENT_RUN → CANONICAL = 104 regles mentides**, sobre 4 models:

| model | codi | customer | ruleset font | origen real | MGR |
|---|---|---|---|---|---|
| 267 | BRW-26-FW-0036 | 7 BRW | 115 | CLIENT_RUN | 34 |
| 268 | BRW-FW27-0001 | 7 BRW | 115 | CLIENT_RUN | 34 |
| 292 | LOS-SS27-0018 | 6 LOSAN | 181 | CLIENT_RUN | 18 |
| 293 | LOS-SS27-0019 | 6 LOSAN | 181 | CLIENT_RUN | 18 |

Els dos models LOSAN confirmen el bug. Cap model amb ruleset `origen=NULL` ha rebut MGR CANONICAL → el dany avui és **exclusivament CLIENT_RUN→CANONICAL**. Impacte: nul al motor (llegeix per FK), **real a traçabilitat i a RUN-CLIENT**.

### B3.3 · Integritat LOSAN (Q16)

La xifra del context (14 rulesets / 300 regles / 14 SizingProfiles) **és exacta però només per al lot de la Fase 1** (rulesets 175-188, perfils 539-552). El footprint real és més gran:

| Mesura | Fase 1 | REAL |
|---|---|---|
| `GradingRuleSet` customer=6 | 14 | **20** (175-188 + 210-214 + llegat 104) |
| `GradingRule` | 300 | **421** |
| `SizingProfile` customer=6 | 14 | **18** (539-552 + 573-576) |

19/20 són `CLIENT_RUN`; **104 és NULL**. **Cap ruleset LOSAN té `garment_type_item` informat** (`gti=None` als 20) → la identitat del contenidor de la llei CONTENIDOR és **incompleta a tot LOSAN**.

**Regles a POM inactiu (invariant violat): 5, totes al ruleset 104** — rules 904/911/912/915/916 → POMs 419 `A.1`, 421 `L.5`, 422 `L.4`, 431 `K.2`, 423 `H`. Context global: **14** `GradingRule` a tot `fhort` apunten a POM inactiu, i **2 `ModelGradingRule`** (mgr 1739/1740, model 396 `LOS-SS27-0122`, POMs 434 `T.1` / 435 `T.2`). `POMMaster` inactius = 16.

**Cel·les incompletes.** `GradingRule` LOSAN (421): **netes** (0 `increment_base` NULL, 0 STEP sense valors, 123 breaks tots coherents amb el run). `GradingRule` totes (1148): `increment_base` NULL = **136** (97 amb `increment=0` també → regla sense delta útil); **15 amb `increment_break` sense `talla_break_label`** (break orfe, irresoluble); **148 regles amb break en rulesets SENSE `size_system`** (grs 77/78/80/82/85/98) — no validables contra cap run. Quan hi ha `size_system`, incoherències = **0**.

`ModelGradingRule` (327): `increment_base` NULL = 28 (totes FIXED → benigne); **1 STEP sense `valors_step`** (mgr 1047, model 182); **60 regles amb `talla_break_label` FORA del `size_run_model`**: model **182** (run `XS·S·M`, break `XXL`, 32 regles) i model **188** (run `XXS·XS·S·M`, break `XXL`, 28 regles).

**Rulesets/perfils orfes o ambigus:** ruleset **214** (`Newborn · LOS Baby 3-36M`, 12 regles) **sense cap `SizingProfile`** → inabastable per la cascada. **4 `SizingProfile` (519-522) sobre el ruleset LOSAN 104 amb `customer=None` i `is_default=True`** → perfils genèrics de tenant servint graduació de client: **la fuga que bloqueja la neteja del LOS antic**. Duplicats de clau de cascada: `(4,82,2,1,customer=6)` × **3** (sp 539/540/541 → rulesets Tops/Bottoms/Onepieces, **indesambiguables**) i `(1,24,3,2,customer=None)` × 2.

### B3.4 · Sessions residuals (Q17)

`FittingDetail` **NO EXISTEIX** (dissolt). Contenidors vius: `SizeFitting`, `FittingSession`→`PieceFitting`→`PieceFittingLine` (`fitting/models.py:7,220,309,355`), i `ModelTask` amb `task_type__code='size_check'` (id 20).

**Resultat directe: cap sessió oberta amb mesures no propagades.** Les **5 úniques** `PieceFitting` amb mesura real són de sessions **Tancades** i **totes tenen una `GradingVersion` posterior**. `GradedSpec` obsolets sobre versions actives: **0**.

El que sí queda residual:

- **A)** Dues `FittingSession` **Obertes buides i velles** (120 → model 165, oberta 06-17; 140 → model 168, oberta 07-10): 0 peces, 0 mesures. Soroll de tauler, no pèrdua.
- **B)** Tres `ModelTask size_check` **`Paused` amb rellotge obert i zero producte** (305 → model 188, 306 → model 166, 317 → model 169 des d'ahir): `started_at` informat, `finished_at` NULL, 0 mesures, cap GV.
- **C)** **Anomalia de vigència a `sf=52` (model 162):** l'activa és la **v3** (gv32, 06-08) tot i existir **v4 (gv40) i v5 (gv42)** posteriors (06-16), totes amb 42 specs. La constraint d'una sola activa es compleix, però **la vigent no és la darrera generada**. És l'únic cas del tenant.
- **D)** `gv73` (sf 157, model 267, v1) és **activa amb 0 `GradedSpec`** — versió vigent buida.
- **E)** Els 5 `PieceFitting` existents tenen `gate='Pendent'`, inclosos els de sessions Tancades.
- **F)** Models 292 i 293 tenen MGR però **cap `SizeFitting`**.

> **Veredicte B3:** no hi ha pèrdua de dades ni feina orfe de propagar. Hi ha **classificació incompleta** (13 origen NULL, dels quals 3 sensibles), **provinença mentida** (104 regles), i **higiene de catàleg LOSAN** (5 regles a POM inactiu, 4 perfils fuga, 3 perfils indesambiguables, 1 ruleset inabastable).

---

## BLOC B4 — Acoblament DXF (sobre el 163)

### B4.1 · Actius de patró del 163

El model de fitxers **no és `ModelFitxer`**: és **`PatternFile`** (`patterns/models.py:33`), amb DXF i RUL en dos `FileField` germans (`:67`, `:73`).

`patterns_patternfile` where `model_id=163` → **1 fila**: id 11, `TATE.DXF`, v1, `is_current=True`, `font_cad='polypattern'`, **332.260 bytes de DXF**, `nom_rul=''`, **0 bytes de RUL**, `grade_table=NULL`, data 2026-07-13. **El 163 té DXF, NO té RUL.** (Al tenant sencer només hi ha 4 `PatternFile`: 8/9/10 → model 186 AMELIA; 11 → 163.)

Geometria parsejada i resident: **10 peces**, 3.341 punts, 219 segments, totes `metadata.size='S'`. `SewRelation`: 8 files.

**Mecanisme d'ancoratge = `PatternPOM`** (`patterns/models.py:303`), recepta a `definicio_mesura` JSON. **Files del 163: 2 de 25** — id 24 (POM 273 `CH`, peça 15, 45.13 cm) i id 25 (POM 464 `EK2`, peça 18, 4.77 cm).

**`GradeRule` com a model de BD NO EXISTEIX:** és un dataclass efímer (`GradeRuleData` a `patterns/engine/geometry.py`), calculat a l'exportació i **no persistit**.

### B4.2 · La projecció `GradedSpec`→CAD **EXISTEIX i és completa**

| Baula | `fitxer:línia` |
|---|---|
| Port | `patterns/engine/ports.py:117` (`GradingSource`) |
| Adaptador real (llegeix `GradedSpec`) | `patterns/adapters.py:432` `DjangoGradingSource.snapshot()` · lectura `:479-483` · flag `:492` |
| Projecció | `patterns/engine/grading_projection.py:151 project()` |
| Llei documentada | `grading_projection.py:19-31` — **s'aplica `increment_applied_cm` (delta), mai `graded_value_cm`** |
| Ancoratge→engine | `adapters.py:538 pom_specs()` (`:578`), `:584 sew_specs()` |
| Consumidor | `patterns/export.py:144 build_export()` → `project()` a `:177` → escriptura DXF+RUL `:200-208` |
| Endpoints | `patterns/views.py:597`, `:618`, `:669` |

**Exercitada en dry-run sobre el 163** (funció pura, cap escriptura): amb les versions reals → `BLOCKED: la versió de grading NO està aprovada`. Forçant `approved=True` **només en memòria**, el pipeline **arriba fins al final**: DXF 471.641 bytes, RUL 128 bytes, autovalidació ✅ (3.341 punts, **0 µm de desviació**), 0 problemes de POM… **i `regles_actives = 0`**.

### B4.3 · Què li falta al 163

| Prerequisit | Estat | Evidència |
|---|---|---|
| DXF parsejat i resident | **OK** | PatternFile 11, 10 peces, 3.341 punts |
| RUL del client resident | **falta, NO bloqueja** | `nom_rul=''`, 0 bytes. El RUL de sortida el genera `RULWriter` (`export.py:208`) |
| Talla base patró == talla base grading | **OK** | peces `size='S'`; `base_size_label='S'`; run conté `S` |
| Projecció `GradedSpec`→regles | **OK** | `grading_projection.py:151`, exercitada end-to-end |
| POMs ancorats a geometria | **FALTA** | **2 `PatternPOM` de 25 POMs graduats** → 23 omissions `spec_sense_pom` |
| Grading aprovat | **FALTA — bloquejant dur** | gv79 i gv80: totes dues `aprovada=False` |
| Grading amb deltes reals | **FALTA — bloquejant de fons** | **totes** les specs són `FIXED` amb `increment_applied_cm = 0.0` |
| Regles al ruleset 108 | **FALTA — causa arrel** | 0 regles |

**Conclusió operativa:** el bloqueig visible és el segell, però **encara que algú segellés gv80 avui, l'escalat produiria una niada idèntica a totes les talles**. `grading_projection.py:90` assentaria `REGLA_ZERO` arreu. Els dos únics POMs ancorats (CH i EK2) són precisament dos dels FIXED a zero.

**Ordre real dels forats: (1) ruleset buit → (2) grading tot FIXED/0 → (3) cap versió aprovada → (4) 2 ancoratges de 25.** Els fitxers i la projecció **no són el problema**.

### B4.4 · Gate d'exportació per segell (Q19) — **EXISTEIX i BLOQUEJA**

Tres capes: **guard dur al motor** (`grading_projection.py:162-166`, `raise GradingNotApproved` abans de moure cap punt) → **traducció a bloqueig** (`export.py:177-180` → `ExportBlocked`; `build_export` és tot-o-res, `:150-153`) → **HTTP 422** (`patterns/views.py:614-615`, `:634-635`). A més, `views.py:563-579` només ofereix a la UI versions amb `aprovada=True`, i `:625-632` exigeix `acknowledged: true` amb 403 **abans** de fabricar cap byte. **No és un avís: és una precondició.** L'estalitud, en canvi, sí que és només avís i viatja al costat (`adapters.py:485-495`), deliberadament.

**Estat del 163: BLOQUEJAT.** gv79 i gv80 totes dues `aprovada=False`, `data_aprovacio=NULL`. L'endpoint `grading-versions` li retornaria **llista buida**: des de la UI ni tan sols es pot triar una versió per exportar. Contrast: l'única exportació del tenant (`ExportAcknowledgement` id=1) és del **186** amb gv53 `aprovada=True` → **el gate ha estat exercitat i es comporta com toca**.

> **Veredicte B4:** el motor i la projecció estan llestos. El 163 no és golden path per raons **totalment aigües amunt**: la regla, el segell i l'ancoratge. `DIAGNOSI_MOTOR_S0.md` §B3 ("l'únic fitxer que existeix és AMELIA") **ha quedat superada**: TATE.DXF va entrar el 2026-07-13.

---

## TAULA FINAL DE RISCOS (per al CTO)

| # | Risc / forat | Gravetat | Àncora | Estat |
|---|---|---|---|---|
| R1 | Wipe de MGR incondicional + retorn descartat → un ruleset buit buida el model en silenci | 🔴 **Crític** | `models_app/services.py:156,168` + `views.py:724` | **Causa del símptoma B0** |
| R2 | `_te_regles` valida el punter, no l'existència de regles | 🔴 Crític | `pom/services.py:527-550` | Gate que no gateja |
| R3 | Motor: "sense regla" → `FIXED` fabricat, sense llei que ho cobreixi | 🔴 Crític | `pom/services.py:191-198` | Forat semàntic invers a la llei §2 |
| R4 | `_load_grading_rules` empassa qualsevol excepció → tot `FIXED` amb 200 OK | 🔴 Crític | `pom/services.py:574-576` | **Segona porta al mateix símptoma** |
| R5 | Ruleset 108 buit assignat a un model de producció | 🔴 Crític | BD: 0 `GradingRule` | Dada viva |
| R6 | El ruleset correcte (115, 34 regles) existeix però no arriba: item i perfil són decoratius | 🟠 Alt | `views.py:516-518` | Sistèmic (188, 164-167, 173-177, 256-260) |
| R7 | 2 `GradingVersion` `aprovada=True` amb `aprovada_per`/`data_aprovacio` NULL; cegen l'audit d'estalitud | 🟠 Alt | gv30 (162), gv53 (186); `staleness.py:108` | **gv53 va alimentar l'única exportació real** |
| R8 | Provinença mentida: 104 MGR `CANONICAL` des de rulesets `CLIENT_RUN` | 🟠 Alt | `views.py:639,674,724` | Viola traçabilitat RUN-CLIENT |
| R9 | 13 `GradingRuleSet.origen` NULL; **104 és de client** → viatjaria a un tenant nou | 🟠 Alt | BD | Bloqueja `bootstrap_tenant` net |
| R10 | 4 `SizingProfile` (519-522) `customer=None, is_default=True` sobre ruleset LOSAN 104 | 🟠 Alt | BD | Fuga; bloqueja la neteja del LOS antic |
| R11 | `except Exception: pass` al lector d'Escalat → taula buida amb 200 | 🟠 Alt | `views.py:949-950,958-959,1020-1021` | Amaga l'estat real a la UI |
| R12 | Specs fantasma: `update_or_create` sense delete previ en camins in-place | 🟠 Alt | `pom/services.py:850-861` | Cel·les mortes barrejades amb vives |
| R13 | Auto-propagació viva contra la llei §2 (que la declara "a jubilar") | 🟠 Alt | `services_size_check.py:200`, `fitting/services.py:455` | **Contradicció llei↔codi sense revocar** |
| R14 | 4 endpoints orfes amb capacitat d'escriure `GradedSpec` i crear v1 silenciosa | 🟡 Mitjà | `grading_views.py`, `wizard_views.py:240`, `views.py:1769` | Superfície d'atac/accident |
| R15 | `_get_or_create_grading_version` crea versió sense `creat_per`/`nom`/guard/watchpoint | 🟡 Mitjà | `pom/services.py:638-642` | Versions anònimes |
| R16 | `GateEvent` sense `choices` ni constraint; `advance` enrere passa **i segella**; `regress` no dessegella | 🟡 Mitjà | `tasks/models.py:140-159`, `services_d.py:24-52,55-69` | Dades lineals per costum |
| R17 | SF triat amb `.first()` → el grading cau al Proto de juny, no al SizeSet de l'import | 🟡 Mitjà | `views.py:1623` | Confon l'operador |
| R18 | 60 MGR amb `talla_break_label` fora del run (models 182, 188) | 🟡 Mitjà | BD | Break irresoluble |
| R19 | 5 `GradingRule` a POM inactiu (ruleset 104) + 2 MGR (model 396); 14 al tenant | 🟡 Mitjà | BD | Invariant violat |
| R20 | 3 perfils LOSAN indesambiguables per la cascada; ruleset 214 sense cap perfil | 🟡 Mitjà | sp 539/540/541; grs 214 | Catàleg ambigu |
| R21 | FK `target` legacy encara decideix reutilitzar-vs-crear ruleset; 10 divergències FK↔M2M | 🟡 Mitjà | `pom/grading_utils.py:339` | 8 casos no representables per la FK |
| R22 | `db_constraint=False` amb criteri empíricament fals (cas testimoni `ModelGradingRule.pom`) | 🟢 Baix | `models_app/models.py:672` vs `:716-722` | 0 orfes avui |
| R23 | `sf=52`: activa la v3 tot i existir v4/v5 posteriors; `gv73` activa amb 0 specs | 🟢 Baix | BD | Anomalies aïllades |
| R24 | 2 `FittingSession` obertes buides + 3 `ModelTask size_check` `Paused` amb rellotge obert | 🟢 Baix | BD | Soroll, no pèrdua |
| R25 | Tenant `los` provisionat i completament buit | 🟢 Baix | BD | **Aclarir si és intencionat** |

---

## Veredicte final

### 1. Causa del símptoma B0

**El `GradingRuleSet 108` és buit.** Assignar-lo al model 163 va disparar el wipe-and-recreate de `materialize_model_grading_rules`, que va **esborrar les 25 `ModelGradingRule` residents i crear-ne zero** sense que ningú miri el retorn. Les dues propagacions posteriors (15:41 i 15:42) van travessar un gate que només comprova que el punter existeix, van carregar un diccionari de regles buit, i el motor —que davant d'un POM amb base i sense regla **copia el valor base a totes les talles com a `FIXED`**— va emetre 225 specs perfectament plans i va retornar èxit.

**La propagació sí que va funcionar. El que va propagar era la taula base repetida.** Cap peça del sistema estava obligada a dir-ho.

### 2. Què li falta al 163 per ser golden path de l'escalat DXF

Per ordre de dependència estricta — **cada pas és inútil sense l'anterior**:

1. **Una regla de veritat.** Decidir si el 163 ha d'apuntar al ruleset **115** (`BRW · Blusa · ALPHA_EU_W`, 34 regles, el contenidor validat a l'S10, on 24 dels seus 25 POMs amb base tenen regla) o a un contenidor propi. Avui apunta al 108, buit. *Cal decisió humana: quin és el contenidor correcte.*
2. **Coherència de `size_system`.** El model diu 67 (LOS), el ruleset 108 diu 29. El 115 diu 29. Cal que model i ruleset comparteixin sistema abans de graduar res.
3. **Re-propagar** i verificar que les specs deixen de ser `FIXED`/delta 0.
4. **Segellar** una `GradingVersion` (avui cap de les dues està aprovada — bloquejant dur i correcte).
5. **Ancorar els POMs restants:** 2 `PatternPOM` de 25. És feina de taller sobre geometria, la més cara de les cinc i la que no es pot automatitzar.

Els fitxers, el parseig, la projecció i el gate **ja hi són i funcionen** (verificat end-to-end en dry-run, 0 µm de desviació).

### 3. Què cal construir o decidir, per dependència

**Nivell 0 — decisions humanes que desbloquegen la resta (cap línia de codi):**
- D1 · Quin ruleset ha de manar el 163 (i els 10+ models amb `model rs NULL` / `item rs=115`).
- D2 · **La llei que falta:** què ha de passar quan hi ha base i **no** hi ha regla. Avui es fabrica un `FIXED`; la llei §2 només cobreix el cas invers ("regla sense base = cel·la absent"). Sense aquesta llei, R3 no és arreglable perquè no se sap què és correcte.
- D3 · L'item/perfil han de **derivar** el ruleset o només **suggerir-lo**? Determina si R6 és bug o disseny.
- D4 · Revocar o executar la llei §2 sobre auto-propagació (R13): el codi i la llei porten des del 23/06 dient coses diferents.
- D5 · Destí dels 4 endpoints orfes (R14): jubilar o cablar.

**Nivell 1 — tancar la classe de bug del silenci (depèn de D2):**
- Fer que `materialize_model_grading_rules` no esborri sense saber què crearà, i que el seu retorn arribi a la resposta (R1).
- `_te_regles` ha de comprovar regles, no punters (R2).
- Decidir si `_load_grading_rules` pot seguir tenint un `except` que retorna `{}` (R4) — és el mateix forat per una altra porta.

**Nivell 2 — integritat de dades (independent del nivell 1, es pot fer en paral·lel):**
- Classificar els 13 `origen` NULL, prioritzant el **104** abans de qualsevol `bootstrap_tenant` (R9).
- Corregir la provinença als tres call-sites del wizard (R8) i decidir si es reparen les 104 MGR ja escrites.
- Investigar **gv30 i gv53** (R7): com van quedar aprovades sense signatura, i què implica que gv53 hagi signat l'única exportació real.
- Higiene LOSAN: 5 regles a POM inactiu, 4 perfils fuga, 3 perfils ambigus, ruleset 214 inabastable (R10, R19, R20).

**Nivell 3 — deute estructural (no bloqueja res avui):**
- FK `target` legacy (R21), `db_constraint` asimètric (R22), `GateEvent` sense constraints (R16), specs fantasma (R12).

**Nivell 4 — el golden path del 163**, un cop resolts D1 i el nivell 1: els 5 passos de la secció 2.

---

### 💡 PROPOSTA (a validar) — no decidida, només registrada

- **Un invariant, no un pedaç:** *un `Model` no pot quedar amb 0 `ModelGradingRule` com a resultat d'una operació que en tenia*. Cobriria R1, R2 i R5 alhora, i és verificable a BD. Alternativa més fluixa: que `update-step2` retorni el compte materialitzat i la UI el mostri.
- **Fer parlar el motor:** que `generate_graded_specs` retorni (o registri) **quantes cel·les han sortit `FIXED` per absència de regla**, i que la UI d'Escalat ho pinti. Una taula 100% FIXED per absència no s'hauria de poder confondre amb una graduació.
- **`GradingRuleSet` buit = no assignable:** validació a l'assignació més que al consum.

*Cap d'aquestes tres és una decisió presa. Les decisions són humanes (Patró C).*

---

## Obert / dubtós (el que aquesta diagnosi NO ha pogut determinar)

1. **No es pot datar l'esborrat de les 25 MGR ni el canvi de ruleset del 163.** `GradingRuleHistory` està buit (0 files a tot el tenant) i ni `Model` ni `ModelGradingRule` tenen auditoria d'aquest camp. La imputació a `update_model_step2` és **per codi + estat resultant, no per registre**.
2. **No es pot provar que el ruleset anterior del 163 fos el 115.** És l'únic candidat coherent (BRW + gti=5 + 34 regles, 24/25 POMs amb base coberts), però no hi ha cap fila que ho digui.
3. **No se sap si el 108 va néixer buit o si algú li va buidar les regles.** L'única pista és que és l'únic buit del tenant i que penja d'un `SizingProfile` de sistema.
4. **Els `ModelGradingOverride` previs del 163 (si n'hi havia) són irrecuperables** — esborrats per la llei del "llenç net" (`views.py:1668`), sense log.
5. **Origen de gv30 i gv53** (`aprovada=True` sense signatura) desconegut.
6. **`GradingVersion` sense cap UNIQUE de "una sola aprovada per SF"** (no re-verificat): 2+ aprovades per `SizeFitting` semblen estructuralment possibles; `seal_model_grading` marca sense desmarcar l'anterior.
7. **Fork 4 de selecció de versió** (`pom/s6_views.py`) no re-verificat. El fork 3 sí està corregit (`pom/services.py:634-637`).
8. **`PieceFittingLine` no té timestamp propi** — la conclusió "tot propagat" de B3.4 és **per construcció (marges de minuts-hores), no per dada**.
9. **Tenant `los` buit**: no se sap si és intencionat (LOSAN operat com a customer dins `fhort`) o un tenant provisionat i mai sembrat.
10. **La discrepància patró↔fitxa a CH del 163** (patró 45,13 vs fitxa 45,00): sospitosament coincidents, cosa que NO és el cas normal descrit a `grading_projection.py:23`. No se sap si és casualitat o si algú va teclejar el valor del patró a la fitxa.
11. **Duplicat de cascada `(4,82,2,1,customer=6)` × 3**: no s'ha llegit el codi de resolució per confirmar si desempata per algun altre eix.
12. **Cap camí s'ha verificat en execució** fora del dry-run pur de `build_export` (B4). La resta és anàlisi estàtica + lectura de BD, per disciplina Patró A.

---

## Diagnosis afectades per aquesta foto

| Document | Estat proposat |
|---|---|
| `arxiu/DIAGNOSI_IMPL_PARITAT_GRADING.md` | Ja segellada (SUPERADA 07/07). Correcte |
| `arxiu/DIAGNOSI_PARITAT_FITTING_GRADING.md` | Ja a arxiu. Aquesta diagnosi la substitueix com a foto vigent |
| `DIAGNOSI_G6_DUAL_PATH.md` | **PARCIALMENT OBSOLETA** — §B2.3 (el 163 ja no té 25 MGR ni rs NULL) i §B4 (el guard de segellat **sí** és real) han caigut. *Candidata a segellar i arxivar quan el CTO validi* |
| `DIAGNOSI_MOTOR_S0.md` | §B3 **superada** — TATE.DXF existeix des del 2026-07-13. La resta del contracte B7 (forma de `GradedSpec`, pinçament per `grading_version_id`) segueix exacta |

*Aquesta diagnosi no segella ni mou cap document: segellar és acte d'un sprint d'implementació, no d'una diagnosi (CLAUDE.md, «Diagnosis»).*
