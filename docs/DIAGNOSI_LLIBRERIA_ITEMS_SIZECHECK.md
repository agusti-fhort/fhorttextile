# DIAGNOSI PROFUNDA — Llibreria d'Items / "Size Check de l'Item"

> **Tipus:** diagnosi READ-ONLY (Patró A). Cap canvi de codi, cap migració, cap commit, cap restart.
> `git status` net. DB només SELECT (PG18:5433, `ftt_staging`, schema `fhort`). Staging intacte.
> **Mètode:** director + 4 investigadors paral·lels (EIX 1–4) + transversal sintetitzat; citacions
> `fitxer:línia`, les bloquejants verificades pel director directament al codi.
> **Convenció:** **FET** = comprovat · **💡 PROPOSTA** = a validar (decisió = Agus, Patró C).
> **Per què:** la UI de valors base es va construir a la pantalla equivocada (POM Navegador, revertida).
> El disseny correcte (Agus): l'autoria de l'item-base ÉS un "Size Check a nivell d'ITEM" — el mateix
> component, apuntant a l'item + `ItemBaseMeasurement` en comptes del model + `BaseMeasurement`.
> **Objectiu:** deixar el terreny perquè el redisseny sigui REPLICACIÓ de mecanismes existents.

---

## 0. Resum executiu

### 🔑 Resposta BLOQUEJANT (EIX 2) — el camp de nomenclatura a replicar
- **Camp de model:** **`BaseMeasurement.nom_fitxa`** — `CharField(max_length=20, blank=True, default='')` ([models_app/models.py:515-519](../backend/fhort/models_app/models.py#L515)).
- **Pinta la columna del Size Check:** `codi_fitxa = (bm.nom_fitxa …) or pom.pom_code` ([serializers_size_check.py:100](../backend/fhort/models_app/serializers_size_check.py#L100)).
- **Sembrat (avui):** del codi importat ([extraction_views.py:372](../backend/fhort/models_app/extraction_views.py#L372)); per defecte documentat = `POMGlobal.abbreviation` ([pom/models.py:42](../backend/fhort/pom/models.py#L42)).
- **Editat:** xat de mesures ([views.py:985-986](../backend/fhort/models_app/views.py#L985)).
- **→ Replicar a l'item:** afegir **`ItemBaseMeasurement.nom_fitxa CharField(max_length=20, blank=True, default='')`** (mateixa definició exacta). És **còpia, no invenció**. (Reobre P2/P3.)

### Veredictes per eix
| EIX | Pregunta | Veredicte |
|---|---|---|
| 1 | El component Size Check és partible? | **Partible amb REFACTOR mitjà.** El bloc base (POM/nom/Teòric/Tolerància) és genèric i read-only; el bloc fitting (Real/Decisió/Nota) i tot el backend (`open/resolve`) són **model-bound**. Reutilització: extreure un nucli de graella base + capa fitting només-model. |
| 2 | Nomenclatura: mecanisme existent | **CONFIRMAT** el principi de l'Agus (importa de dalt, edita, viu al nivell). Camp = `nom_fitxa` (vegeu dalt). |
| 3 | FK Item→GradingRuleSet | **Cost BAIX** (1 FK nullable, sense backfill destructiu). Avui el ruleset es tria al **Model** (explícit al wizard). Existeix un matcher per eixos (`cerca_canonic_equivalent`) usat NOMÉS a import. P1 (`base_size_definition`) **s'hauria de constrènyer ARA** al `size_system` del ruleset. |
| 4 | On viu la pantalla | Editor d'item = modal a **GarmentTypes.jsx** (matriu de temps). Opcions d'ubicació del "Size Check de l'item": modal-tabs / **drawer** / pàgina full-screen. `POMBrowser mode=assign` és **encastable** (ja pren l'item per prop). |

---

## EIX 1 — El component Size Check per dins (desacoblament model→item)

### 1.1 Frontend — columnes (FET)
[SizeCheckTab.jsx](../frontend/src/components/model/SizeCheckTab.jsx) + [SizeCheckCell.jsx](../frontend/src/components/model/SizeCheckCell.jsx). Props: `model` (.id, .base_size_label), `onFeedback`, `editable` (treball Kanban vs consulta). Crida `sizeChecks.open/list/get/resolve` + `sizeCheckLines.update` (autosave 800ms).

| Columna | Font (línia) | Editable? | Desa |
|---|---|---|---|
| **POM / codi_fitxa** | `line.codi_fitxa` ← `BaseMeasurement.nom_fitxa` (fallback `pom.pom_code`) [serializers_size_check.py:100] | No | — |
| **Nomenclatura (nom)** | `line.nom` ← `pom.name_cat` [serializers_size_check.py:106] | No | — |
| **Teòric** | `line.valor_teoric` ← snapshot de `BaseMeasurement.base_value_cm` | No | — |
| **Tolerància** | `line.tol_minus/plus` ← `BaseMeasurement.tolerancia_minus/plus` (fallback TOL_DEFAULT 0.6) [89-90] | No | — |
| **Real (proto)** | `line.valor_real` | **SÍ** | `PATCH size-check-lines/{id}/` |
| **Decisió** | `line.decisio` (null / tolerancia_acceptada / valor_descartat) | **SÍ** | idem |
| **Nota** | `line.nota` | **SÍ** | idem |

**Classificació:** BASE/genèric = POM·nomenclatura·Teòric·Tolerància (read-only). FITTING/model = Real·Decisió·Nota (el cor del proto→base).

### 1.2 Backend (FET) — [services_size_check.py](../backend/fhort/models_app/services_size_check.py)
- `_materialize_lines(size_check, model)` [16-38]: una `SizeCheckLine` per `BaseMeasurement` VIGENT (is_active, base_value_cm no null); `valor_teoric`=snapshot. **Model-scoped.**
- `open_size_check(model_id)` [41-78]: `Model.objects.get(pk=model_id)`, reusa Pendent o crea. **Sense variant d'item.**
- `resolve_size_check(...)`: lògica de propagació **completament model-bound** — escriu `BaseMeasurement(origen='CHECKED')`, crea `GradingVersion` + `generate_graded_specs` si `model_te_deltes(model)`, i tanca el `ModelTask` size_check. `SizeCheck` FK→Model PROTECT; `SizeCheckLine` FK→POMMaster (db_constraint=False), unique (size_check, pom). **Cap FK a BaseMeasurement** (lookup a serialitzar).

### 1.3 VEREDICTE (FET + 💡)
**FET:** el Size Check de l'ITEM necessita NOMÉS el bloc base (POM/nom/Teòric=valor base de l'item/Tolerància), **sense** el bloc fitting (no hi ha proto a nivell d'item; no hi ha propagació/GradingVersion/ModelTask). El backend `open/resolve` és **100% model-bound** → no reutilitzable tal qual.

**💡 PROPOSTA (partibilitat):** el component és partible amb **REFACTOR mitjà**:
- Extreure un nucli `<MeasurementBaseGrid lines disabled />` (columnes 1-4, read-only) — ~100% reutilitzable.
- `SizeCheckTab` queda com a wrapper model (fitting + Kanban).
- Un `ItemSizeCheckTab` nou: mateix nucli base + edició lleugera (valor + nomenclatura + tolerància editables contra `item-base-measurements/upsert/`), SENSE Real/Decisió/Nota.
- Backend: **NO reutilitzar** `services_size_check`; l'item escriu directament a `ItemBaseMeasurement` (l'API P3 ja existeix). Cost: extreure graella (~150-200 LOC) + tab d'item (~100 LOC). Duplicar tot el component seria pitjor (manteniment divergent).

---

## EIX 2 — Nomenclatura editable: el mecanisme EXISTENT (bloquejant)

### 2.1 A POM (FET)
**`POMGlobal.abbreviation`** `CharField(max_length=40, blank=True)` ([pom/models.py:42](../backend/fhort/pom/models.py#L42)) — l'abreviatura canònica ("CH CIRC","SH DR","CH","WA"), al catàleg GLOBAL (schema public). *Inferit:* exposada read-only per API de tenant (s'edita per seed/admin global, no per-tenant). El codi de POM **per-tenant** és `POMMaster.codi_client` (p.ex. "WA","D1") — cosa distinta de l'abreviatura.

### 2.2 A MODEL (FET) — la dada EXACTA que pinta la columna
`codi_fitxa = (bm.nom_fitxa if bm and bm.nom_fitxa else '') or (pom.pom_code if pom else '')` ([serializers_size_check.py:98-100](../backend/fhort/models_app/serializers_size_check.py#L98)). Comentari del codi: *"SC-4: codi de fitxa = BaseMeasurement.nom_fitxa (com la taula Mesures, gold mono)"*.
→ **La nomenclatura editable de model = `BaseMeasurement.nom_fitxa`** ([models_app/models.py:515](../backend/fhort/models_app/models.py#L515), help_text: *"Nomenclatura de la fletxa al croquis (ex: A, 1, CH). Per defecte: abbreviation del POMGlobal."*). Cap taula d'àlies separada; viu a la fila de `BaseMeasurement`. També exposat a `BaseMeasurementSerializer` ([serializers.py:136]) i a la taula Mesures.

### 2.3 La cadena de sembra (FET) — CONFIRMA el principi de l'Agus
- **Còpia (sembra):** avui `nom_fitxa` es sembra des de l'**import** (`codi_fitxa` extret → [extraction_views.py:372](../backend/fhort/models_app/extraction_views.py#L372); també tech_sheet [tech_sheet_views.py:363]). **`materialitzar-poms` (plantilla d'item→model) NO sembra `nom_fitxa`** (verificat: cap assignació dins la funció) → quan ve de plantilla, `nom_fitxa` queda buit i la columna cau a `pom_code`.
- **Edició:** xat de mesures [views.py:985-986](../backend/fhort/models_app/views.py#L985) (`bm.nom_fitxa = accio['nom_fitxa']`).
- **Veredicte principi:** ✅ **CONFIRMAT** — la nomenclatura "importa de dalt (abbreviation/codi importat), es pot editar (xat), i viu al nivell actual (`BaseMeasurement`)". El **forat** és que la baula **POM→model via plantilla d'item NO està cablejada** (només via import) — exactament el que el redisseny (P5 + reobrir P2/P3) ha de tancar.

### 2.4 VEREDICTE (bloquejant) — camp a replicar
Afegir a `ItemBaseMeasurement` **el mateix camp del model**, exacte:
```python
nom_fitxa = models.CharField(max_length=20, blank=True, default='',
    help_text="Nomenclatura de la fletxa al croquis (ex: A, 1, CH). Per defecte: abbreviation del POMGlobal.")
```
Sembrat des de `POMGlobal.abbreviation` quan es crea la fila d'item; editable a la graella del Size Check de l'item; copiat a `BaseMeasurement.nom_fitxa` a la materialització (P5). Reobrir **P2** (model + migració additiva) i **P3** (serializer + upsert: afegir `nom_fitxa` als camps i als `defaults`).

### 2.5 NOTA motor DXF (FET, sense investigar geometria)
Aquest camp tindrà un **consumidor futur a la banda geometria** (àncora POM↔patró, Agus) → modelar-lo pensant en això (és l'identificador estable que lligarà la mesura amb el punt del patró). No s'investiga aquí.

---

## EIX 3 — FK Item→GradingRuleSet (entra en aquest sprint)

### 3.1 Resolució actual del ruleset (FET)
**Confirmat:** cap FK `GarmentTypeItem→GradingRuleSet` ([tasks/models.py:347-379]). El ruleset es resol al **Model**:
- `create_model_wizard` ([models_app/views.py:223-371]): `grading_rule_set_id` ve del **payload** (tria explícita); `_resolve_garment_def` [205-209] el resol; PG-2 Cas B [314-323] materialitza a `ModelGradingRule` (origen CANONICAL). Guarda: `base_size` sense `grading_rule_set_id` → 400 [241-243].
- **Matcher automàtic per eixos:** `cerca_canonic_equivalent(model)` ([grading_utils.py:81-113]) busca `GradingRuleSet(is_system_default=True, size_system, construction, fit_type, targets M2M)` — **usat NOMÉS a import/techpack** ([extraction_views.py:1913-1914]), **no al wizard**. Pot haver-hi **>1 candidat** → `.first()` (no determinista, sense desambiguació explícita). *(inferit: risc de no-determinisme si hi ha duplicats system-default.)*

### 3.2 Cost de pujar la FK a l'Item (FET + 💡)
**💡 Ubicació:** `GarmentTypeItem.grading_rule_set → pom.GradingRuleSet` (nullable, SET_NULL). **Cost BAIX:** 1 FK additiva, sense backfill destructiu; items existents queden NULL transitori.
**FET — la constricció de P1:** `GarmentTypeItem.base_size_definition` ([tasks/models.py]) ja documenta al help_text *"Lliure ara; es constrenyirà al run quan existeixi Item→GradingRuleSet"*. La relació: `GradingRuleSet.size_system` ([pom/models.py:457]) ↔ `SizeDefinition.size_system` ([pom/models.py:322]) — tots dos apunten a `SizeSystem`. → **💡 quan s'afegeixi la FK, `base_size_definition` s'HA de constrènyer** al `size_system` del ruleset (validació a `save()`/ORM; un CHECK de BD creuaria taules). FK vives afectades: `Model.grading_rule_set` podria **derivar** de l'item; `ItemBaseMeasurement.garment_type_item` hereta el context transitivament.

### 3.3 El ruleset basta per pintar la graella base sense Model? (FET)
- El **ruleset NO porta valor base** (P0 va eliminar `valor_base`); `GradingRule` aporta `talla_base` + `logica` + `increment`/`increment_base/break` + `valors_step` (estructura/deltes), no valors.
- **Valors base** viuen a `ItemBaseMeasurement.base_value_cm` (plantilla). **Toleràncies** per a la graella: `POMMaster.tolerancia_default_minus/plus` ([pom/models.py:203-204]) o `ItemBaseMeasurement.tol_minus/plus` (P2).
- **Veredicte:** `GradingRuleSet` (estructura) **+** `ItemBaseMeasurement` (valor + nomenclatura + tolerància) **+** `GarmentTypeItem.base_size_definition` (talla base) → **basten per pintar la graella base del Size Check de l'item SENSE cap Model**. El ruleset sol dóna l'esquelet (talla base + deltes); l'`ItemBaseMeasurement` el completa amb les dades. *(Res més falta per a la columna base; el bloc fitting no aplica a l'item.)*

---

## EIX 4 — On viu la pantalla: l'editor d'Item

### 4.1 Editor actual (FET)
Pantalla **Garment Types** ([GarmentTypes.jsx](../frontend/src/pages/GarmentTypes.jsx)), layout master-detall: tipus (esquerra) → matriu items×task_types (dreta, `estimated_minutes`). Edició d'item via **`ItemModal`** [369-408]: `code` (read-only en editar), `name`, `complexity_order`, `active`. Endpoints `garment-type-items/` (CRUD, gated CONFIGURE a `GarmentTypeItemViewSet`).
⚠️ **NOTA SEPARADA (no aquest sprint):** la **matriu de TEMPS per tasca** que viu aquí està marcada per **migrar a Planificació** — només anotat, no investigat.

### 4.2 On cabria el "Size Check de l'item" (💡 OPCIONS, no decisió)
La pantalla és modal+matriu (sense tabs avui). Opcions:
- **A · modal-tabs** dins `ItemModal` ([Config][Mesures base][POMs]). Contingut: pot quedar atapeït.
- **B · drawer** lateral full-height (patró existent: `POMDetailPanel` 340px). ItemModal queda prim; les 3 seccions s'apilen. *(equilibri recomanat pels investigadors, no decisió.)*
- **C · pàgina full-screen** `/garment-types/{type}/items/{item}` amb tabs (patró `ModelSheet` 10 tabs). Màxim espai; trenca el gest modal actual.

Integraria: (a) pertinença POMs, (b) FK grading rule set, (c) graella nomenclatura+valor+tolerància — "un sol gest".

### 4.3 Pertinença de POMs (FET + 💡)
Avui es posa/treu POM d'un item amb **`POMBrowser mode='assign'`** ([POMBrowser.jsx]): `assignAdd` POST / `assignRemove` DELETE `garment-pom-maps/`, drag-ordre, toggle KEY. **És encastable** (pren `selectedItem` per prop, carrega per `?garment_type_item=`). → **💡 opció 1:** encastar `<POMBrowser mode=assign>` a la secció POMs de l'editor d'item (reús directe, zero duplicació). Opció 3 (taula inline pròpia) duplicaria la lògica. Pertinença i valors **poden conviure a una sola pantalla d'item** (POMBrowser per pertinença + graella Size Check per valors/nomenclatura), o integrar-se si la graella també gestiona alta/baixa.

---

## EIX TRANSVERSAL — Inventari de la cadena de sembra POM→item→model

| Camp | POM (canònic) | ITEM (plantilla) | MODEL (instància) | Sembra (còpia) | Edició |
|---|---|---|---|---|---|
| **Valor base** | — (el POM no porta valor) | `ItemBaseMeasurement.base_value_cm` (P2) | `BaseMeasurement.base_value_cm` | item→model: `materialitzar-poms` (avui crea fila buida; **P5 ha de copiar el valor**, origen `ITEM_STANDARD`) | `set-measurements` / xat |
| **Nomenclatura** | `POMGlobal.abbreviation` [pom/models.py:42] | **`ItemBaseMeasurement.nom_fitxa`** (A AFEGIR — bloquejant) | `BaseMeasurement.nom_fitxa` [models_app:515] | POM→model avui **NOMÉS via import** [extraction:372]; `materialitzar-poms` **NO el sembra** (forat) | xat [views.py:985-986] |
| **Tolerància** | `POMMaster.tolerancia_default_minus/plus` [pom/models.py:203-204] | `ItemBaseMeasurement.tol_minus/tol_plus` (P2) | `BaseMeasurement.tolerancia_minus/plus` | copy-at-pour (`set-measurements`/import) | `set-measurements` |
| **Pertinença/ordre/KEY** | (catàleg POMMaster) | `GarmentPOMMap(is_key, ordre, nivell)` | (implícit a `BaseMeasurement.is_key/ordre`) | `materialitzar-poms` copia is_key/ordre | POMBrowser assign |
| **Talla base** | — | `GarmentTypeItem.base_size_definition` (P1) | `Model.base_size_label` / `grading_rule_set` | wizard (tria al model) | editor item/model |
| **Grading (estructura)** | `GradingRuleSet`/`GradingRule` (canònic) | *(falta FK — EIX 3)* | `ModelGradingRule` (resident) | `materialize_model_grading_rules` | regim per POM |

**Lectura:** la cadena ja és real i homogènia per **valor** i **tolerància** (POMMaster→Item→Model via copy-at-the-moment). La **nomenclatura** té la baula POM→Model viva (import) però la baula **item→model NO** (materialitzar-poms no toca nom_fitxa) → el redisseny l'ha de tancar afegint `ItemBaseMeasurement.nom_fitxa` + copiar-lo a la materialització. El **grading** és l'única peça que encara viu al Model i ha de pujar a l'Item (EIX 3).

---

## 💡 PROPOSTA consolidada (a validar — Agus, Patró C)

1. **💡 Reobrir P2/P3:** afegir `ItemBaseMeasurement.nom_fitxa` (còpia exacta del camp de model) + exposar-lo al serializer/upsert. *(bloquejant resolt; és còpia.)*
2. **💡 P5 (sembra):** `materialitzar-poms` copia `base_value_cm` **i** `nom_fitxa` (i tol) d'`ItemBaseMeasurement`→`BaseMeasurement` (origen `ITEM_STANDARD`), preservant orígens més específics. Tanca el forat de nomenclatura item→model.
3. **💡 EIX 3:** FK `GarmentTypeItem.grading_rule_set` (nullable) + constrènyer `base_size_definition` al `size_system` del ruleset (validació ORM). Model pot derivar el ruleset de l'item.
4. **💡 Component:** extreure `<MeasurementBaseGrid>` (nucli base read-only) de SizeCheckTab; nou `ItemSizeCheckTab` (valor+nomenclatura+tolerància editables contra `item-base-measurements/upsert/`), sense bloc fitting. Backend de l'item NO reusa `services_size_check`.
5. **💡 Pantalla:** editor d'item amb drawer/tab que integra pertinença (`POMBrowser assign` encastat) + FK ruleset + graella base. La matriu de temps NO es toca (migra a Planificació, fora d'abast).

---

## Tancament
- 4 eixos + transversal documentats; FET separat de 💡 PROPOSTA.
- **Bloquejant EIX 2 resolt:** camp = `BaseMeasurement.nom_fitxa` → replicar `ItemBaseMeasurement.nom_fitxa` (verificat al codi, no assumit).
- EIX 1: veredicte de partibilitat (refactor mitjà: nucli base reutilitzable + capa fitting model-only).
- EIX 3: cost FK baix + `base_size_definition` s'ha de constrènyer ara.
- EIX 4: ubicació candidata (drawer/tab a GarmentTypes) + `POMBrowser` encastable.
- Taula transversal de la cadena de sembra completa (valor/nomenclatura/tolerància/pertinença/talla/grading).
- READ-ONLY respectat: `git status` net (doc untracked com els altres DIAGNOSI_*), cap codi tocat, DB només SELECT.

*Alimenta una decisió de disseny (Patró C). Aquí NO es decideix arquitectura.*
