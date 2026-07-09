# LECTURA QUIRÚRGICA — Components a reutilitzar per a la pàgina d'autoria d'Item

> **Naturalesa:** lectura quirúrgica READ-ONLY (Patró A acotat). Mapem 3 components existents per
> reutilitzar-los a la pàgina d'item (Fase B); NO els redissenyem.
> **Estat:** res tocat, `git status` net. `FET` = `fitxer:línia`; `💡 PROPOSTA (a validar)` = decisió Fase B/C.
> Paths relatius a `/var/www/ftt-staging/`. Frontend: React + Vite (`frontend/src`).

---

## 0 · Resum executiu (els 3 veredictes)

| Component | Fitxer principal | Encastable tal qual? | Veredicte |
|---|---|---|---|
| **A · Wizard+Llistat Grading Rules** (passos 1-2) | `frontend/src/pages/GradingRuleSets.jsx` | **No** (monòlit de pàgina) | **Extreure** AxesSelector + RuleSetList i **parametritzar l'acció final** (explorar→assignar FK). Filtre **client-side**. |
| **B · Garment Types** (contenidor) | `frontend/src/pages/GarmentTypes.jsx` | **Sí, s'estén net** | Master-detail ja existent; `ItemModal` creix (camps/wizard). Serveix obrir-existent **i** crear-nou. |
| **C · Graella de mesures** (pas 4) | `frontend/src/components/EditableTable/EditableTable.jsx` | **No** (acoblada a sizeRun+graded) | **Cal `MeasurementBaseGrid` nou (B1)** reutilitzant reorder + add/remove + cel·les editables. |

Punt transversal crític: **el pas 2 "cap ruleset → crear" NO té camí a Grading Rules** (la creació viu a Size Library). S'ha de resoldre (§A.4).

---

## A · WIZARD + LLISTAT de Grading Rules (passos 1 i 2)

Fitxer: `frontend/src/pages/GradingRuleSets.jsx` (pantalla CONFIGURACIÓ TÈCNICA → "Grading Rules").

### A.1 · El selector d'eixos (target → construcció/fit → grup)
FET:
- Estat: 4 variables string independents — `selectedTarget`, `selectedConstruction`, `selectedFit`,
  `selectedGarmentGroup` (`GradingRuleSets.jsx:85-91`). **Emet CODIS** (string, p.ex. `'WOMAN'`), no instàncies.
- Enums font hardcodats al fitxer: `TARGETS`/`CONSTRUCTIONS`/`FITS`/`GARMENT_GROUPS` (`:10-54`).
- UI en cascada: target (`:279-296`) → construcció+fit (`:299-347`) → grup (`:350-364`); triar un
  eix amunt **reseteja** els de sota (`:289-291`, `:317`, `:338`).

### A.2 · El llistat de rulesets filtrat pels eixos
FET:
- Endpoint: `GET /api/v1/grading-rule-sets/?page_size=200` — **una sola càrrega** (`:104`).
- Filtratge **client-side** (no query params per eixos): `matchingRuleSets` filtra en local per
  target/construction/fit/grup (`:184-193`); retorna buit fins que els 4 eixos estan triats (`:185`).
- Backend: `GradingRuleSetViewSet` (`backend/fhort/pom/views.py:139-151`); `filterset_fields` =
  `['actiu','garment_group','size_system']` (NO target/construction/fit → per això el filtre fi és client).
- Per ruleset retorna (serializer `backend/fhort/pom/serializers.py:170-206`): `id`, `nom`,
  `codi_sistema`, `targets_codis[]`, `construction_codi`, `fit_type_codi`, `garment_group(+nom)`,
  `size_system(+nom)`, `is_system_default`, `actiu`, `regles_count`, `regles[]`.

### A.3 · Desacoblament i acció final
FET:
- És un **component de pàgina monolític** (export únic, tot l'estat a nivell de pàgina `:85-91`); sub-
  components de presentació locals (TargetCard, SelectionButton, RuleSetCard, RuleSetModal).
- **Acció final en triar un ruleset = obrir modal d'edició**: `onEdit={() => { setEditTarget(rs);
  setShowModal(true) }}` (`:385`), modal a `:904-1041` que fa PATCH/POST a `/api/v1/grading-rule-sets/`.
- A la pàgina d'item l'acció seria **"ASSIGNAR aquest ruleset a l'item"** → cridar l'upsert de l'item
  amb la FK `grading_rule_set` (A3) i continuar.

> 💡 PROPOSTA (a validar): extreure dues peces reutilitzables —
> **(1) `<AxesSelector>`** (la cascada `:279-364` + l'estat/memos `:85-193`) que emeti els 4 codis;
> **(2) `<RuleSetList>`** (la càrrega `:104` + filtre `:184-193` + RuleSetCard) amb un prop
> `onPick(ruleset)` i `actionLabel`. La pàgina d'item passa `onPick = assignar FK`; la pàgina Grading
> Rules passa `onPick = obrir modal`. **Cost: moderat** (extracció de 2 components + 1 hook de filtre).
> Alternativa duplicar = més deute. Recomanació: extreure, perquè el filtre client-side i els enums ja
> són autònoms (no depenen de res de la pàgina). Decisió Fase B.

### A.4 · ¿Pot tornar buit? ¿Hi ha camí "crear nou"?
FET:
- **Sí pot tornar buit**: estat buit explícit quan cap ruleset encaixa amb els 4 eixos (`:393-403`,
  missatge `grading.no_match` + `grading.create_from_library`).
- **NO hi ha camí "crear ruleset" en aquesta pantalla**: comentari `:261` — «Creació centralitzada a
  la **Size Library**; aquí només consulta/edita/esborra». Accions disponibles: clonar (`:376-383`),
  editar (`:385`), esborrar (`:386`). Cap "crear nou des d'aquests eixos".

> 💡 PROPOSTA (a validar — clau per al pas 2): el flux d'item «triar → si cap, crear» necessita un
> camí de creació que avui viu fora (Size Library, `frontend/src/pages/SizeLibrary.jsx`, sobre el
> motor `derive_grading_rule_set` ja documentat a `docs/LECTURA_RULESET_MATCHING.md`). Opcions: (a) des
> de l'estat buit del pas 2, enllaçar/encastar el flux de creació de Size Library i tornar amb el
> ruleset nou per assignar-lo; (b) un botó "crear ruleset" que cridi el mecanisme amb els eixos ja
> triats. Recordatori del veredicte previ: el motor fa "find-exact-or-create", **no "ampliar"**.
> Decisió Fase B/C; depèn de QUÈ és "assignar ruleset" (triar de catàleg vs derivar).

**VEREDICTE A:** no encastable tal qual (monòlit), però **extraïble net** (AxesSelector + RuleSetList +
acció parametritzada). El forat real no és el component sinó el **camí de creació** absent (§A.4).

---

## B · Pàgina GARMENT TYPES (contenidor + llista d'items)

Fitxer: `frontend/src/pages/GarmentTypes.jsx` (CONFIGURACIÓ TÈCNICA → "Garment Types").

### B.1 · Estructura
FET — master-detail responsiu:
- **Esquerra (mestre):** llista de garment types amb cerca/filtre/actiu (`:178-206`); `selectedId`
  marca el seleccionat (`:40`).
- **Dreta (detall):** capçalera del tipus (`:212-230`) + botó "Nou item" (`:235-237`) + **matriu de
  temps** (`:240-293`).
- Càrrega del detall: `loadDetail()` (`:70-89`) en canviar `selectedId` (`:91`), via
  `garmentTypeItems.list({garment_type})` + `taskTimeEstimates.list()`. Items a `items` (`:41`),
  pintats com a files (`:254-289`).

### B.2 · La matriu de temps (TaskTimeEstimate) — només localitzada
FET (⚠️ marcada per MIGRAR a Planificació; NO investigada la migració):
- Viu al panell dret (`:240-293`); estat `cells[itemId][taskTypeId]` (`:43`).
- Desa per fila (`saveRow()` `:129-157`) contra `/api/v1/task-time-estimates/` (create/update/remove).
- **És el que ocupa avui l'àrea de config de l'item** → quan migri, deixa lloc a la config nova d'item.

### B.3 · L'acció "Editar" d'un item
FET:
- Botó editar (`:264`) → `setItemModal({mode:'edit', item:it})`; modal renderitzat a `:306-311`
  sobre `components/ui/Modal.jsx` (contenidor genèric, scrollable, `maxHeight 85vh`).
- **`ItemModal` (`:369-408`) camps actuals:** `code` (read-only en edició `:395`), `name` (`:398`),
  `complexity_order` (`:400`), `active` (`:404`). Payload: edició `{name,complexity_order,active}`
  (`:381`), creació `{garment_type,code,name,complexity_order,active}` (`:382`) →
  `garmentTypeItems.update/create` (`:383`).
- **NO toca** `grading_rule_set` ni `base_size_definition` (els nous camps A3) — confirmat (cap estat
  ni payload a `:369-408`).
- Extensible: el modal creix en vertical sense fre arquitectònic; afegir-hi selects és directe.

### B.4 · Llista, obrir-existent i crear-nou
FET:
- Els items existents es llisten (`:254-289`); compte mostrat (`:234`). Els 57 esquelets hi surten en
  seleccionar el seu garment type.
- **"Nou item" ja existeix**: botó (`:235-237`) → `setItemModal({mode:'create'})`. Crea via
  `garmentTypeItems.create` amb `{garment_type,code,name,complexity_order,active}` (`:382`).
- El mateix `ItemModal` serveix **obrir-existent (edit) i crear-nou (create)** segons `mode`/`isEdit`
  (`:370`). El punt d'entrada (a) decidit (obrir des de la llista) ja hi és.

> 💡 PROPOSTA (a validar): estendre `ItemModal` cap al **flux complet d'autoria**. Dues vies:
> (1) **el modal creix** amb seccions (bàsic → grading ruleset → talla base → graella), o (2)
> **wizard multi-pas** dins el modal/ruta. Recomanació: atès que el flux té 4 passos amb dependències
> (eixos→ruleset→talla base→graella) i la graella és pesada, un **wizard** (potser ruta pròpia, no
> modal de 460px) encaixa millor que inflar el modal. Decisió de disseny visual Fase B (B2), amb el CTO.

**VEREDICTE B:** el contenidor s'estén net; master-detail + ItemModal ja cobreixen obrir/crear. El que
falta és inflar el flux d'autoria (camps A3 + graella) — sense bloqueig arquitectònic.

---

## C · GRAELLA DE MESURES de la creació de model (pas 4)

Fitxer canònic: `frontend/src/components/EditableTable/EditableTable.jsx`.

### C.1 · Quin component és
FET:
- `EditableTable.jsx` és LA graella editable de mesures de model: POM + nomenclatura editable
  (`nom_fitxa`) + valor + add/remove + reorder. (Distingir de `components/MeasurementTable/
  MeasurementTable.jsx`, que és **read-only** base+grading.)

### C.2 · Reordenació
FET:
- **Drag-and-drop amb `@dnd-kit`** (`EditableTable.jsx:4-10` imports; `:173` DndContext; `:201`
  SortableContext; `:204-213` SortableRow).
- Escriu el camp **`ordre`** (`:58`, `arrayMove(...).map((r,i)=>({...r, ordre:i}))`).
- Persisteix a `POST /api/v1/models/{id}/reorder-measurements/` (frontend `:139-142`; backend
  `models_app/views.py:721-739`, `update(ordre=i)`).
- Mateix patró que POMBrowser (`components/POMBrowser/POMBrowser.jsx:204-222`, dnd-kit, PATCH
  `garment-pom-maps/{id}` amb `ordre`).

### C.3 · Posar/treure POMs
FET:
- **Afegir:** `AddPOMInline` (`:370-484`); cerca catàleg `GET /api/v1/poms/cerca/?q=` (`:382-386`),
  crea POM-tenant si cal `POST /api/v1/poms/crear-tenant/` (`:395-415`); afegeix fila local (`:81-95`).
- **Treure:** filtra fila local i recalcula `ordre` (`:76-79`); en desar envia `keep_pom_ids`
  (`:128-143`); backend soft-delete (`is_active=False`) dels no inclosos (`models_app/views.py:703-708`).
- Desament global: `POST /api/v1/models/{id}/set-measurements/` (`:119-126` payload →
  `update_or_create(model,pom)` `views.py:685-697`). Escriu a **`BaseMeasurement(model)`**.

### C.4 · Desacoblament (item vs model)
FET — punts d'acoblament a model:
- **sizeRun + columnes de grading (l'acoblament fatal):** `colCount = (readOnly?0:2)+4+sizeRun.length+1`
  (`EditableTable.jsx:154`); bucle de columnes per talla (`:188-196`), cel·les `graded.${size}`
  (`:290-299`), parse `graded.` (`:66-68`). **L'item NO té columnes de grading** (només valor base +
  tol + nomenclatura) — confirmat per `ItemBaseMeasurement` (`pom/models.py:448-478`, sense graded).
- **Columna Δ** calculada del grading (`:97-110`) → sense sentit per a l'item.
- **Toleràncies:** l'item les vol editables (`tol_minus/tol_plus`, upsert A2/P3); la graella de model
  no les pinta com a columnes (el model les copia del catàleg al backend).
- **Impedància de dades:** l'estat de fila porta `{nom_ca, nom_en, graded, ...}`; l'item no té
  `nom_ca/nom_en` ni `graded`, i sí `garment_type_item` + `tol_*`.
- **Destí d'escriptura:** model → `set-measurements` (`BaseMeasurement`); item → `POST /api/v1/
  item-base-measurements/upsert/` (`garment_type_item, pom, base_value_cm, tol_minus, tol_plus,
  nom_fitxa`) (ja existent, A2/P3).

Lliga amb el veredicte de partibilitat previ (Size Check base vs fitting,
`docs/DIAGNOSI_LLIBRERIA_ITEMS_SIZECHECK.md`): la capa **base** és comuna; el bloc **grading/fitting**
és el que sobra per a l'item.

> 💡 PROPOSTA (a validar — peça B1): construir **`MeasurementBaseGrid`** (versió pelada) que reusi de
> `EditableTable` la lògica **reutilitzable**: drag-reorder (`ordre`), add/remove (`AddPOMInline` +
> patró keep_ids), cel·les editables (`nom_fitxa`, valor). Columnes per a l'item: `[drag, #, nom_fitxa,
> descripció, base_value_cm, tol_minus, tol_plus, delete]` (sense sizeRun, sense Δ, sense graded).
> Destí: l'upsert d'item. Dues vies d'implementació: (a) extreure les parts comunes a un component base
> compartit i fer-ne dues vistes (model/item); (b) component nou que copiï només la lògica comuna.
> Recomanació: (a) si es vol evitar duplicar add/remove+reorder; (b) si es prioritza no tocar la
> graella de model (risc zero sobre el camí de model en producció). Decisió Fase B.

**VEREDICTE C:** **no reutilitzable pelada via props** — l'acoblament a `sizeRun`/`graded` és
estructural (colCount hardcodat, estat de fila amb `graded`). Cal **`MeasurementBaseGrid` nou (B1)**
que reculli la lògica comuna (reorder + add/remove + cel·les) i descarti el bloc grading/fitting.

---

## D · Criteri d'èxit (checklist)

- [x] 3 components localitzats amb `fitxer:línia` i veredicte de desacoblament (§A/§B/§C, taula §0).
- [x] A: cost de parametritzar l'acció final (explorar→assignar) + el forat "cap ruleset → crear" (§A.3, §A.4).
- [x] B: com s'estén l'editor d'item (modal creix vs wizard) + confirmació obrir-existent i crear-nou (§B.3, §B.4).
- [x] C: veredicte graella pelada vs `MeasurementBaseGrid` nou, amb punts d'acoblament (§C.4).
- [x] Res tocat. `git status` net.

---

*Lectura quirúrgica · Patró A acotat · 2026-06-22 · READ-ONLY · staging `dev`.*
