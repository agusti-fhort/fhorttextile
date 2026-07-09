# DIAGNOSI_EDITOR_ESTAT — mapa REAL de l'editor de fitxa (dev)

> PATRÓ A — diagnosi read-only. Cap canvi de codi, cap commit. Equip PROTOCOL_FASE_B
> (director-investigacio + investigador-codi ×3 + documentador), tot en Sonnet.
> Objectiu: verificar contra el disseny del vault (CATALEG_EINES_EDITOR / MAPA_PALETA_EINES /
> PLA_MESTRE) què hi ha implementat AVUI, perquè el catàleg cita un "motor" (F3/F4) no
> verificat després del refactor. Referències en format `fitxer:línia`.

---

## 0. Resum executiu (director)

- **El "motor" no és un motor únic.** L'editor viu tot dins un sol fitxer gegant
  ([TechSheetEditor.jsx](../../frontend/src/pages/TechSheetEditor.jsx), 2825 línies): estat,
  paleta, canvas, panells i export inline. No hi ha satèl·lits de toolbar/hooks en fitxers apart.
- **Dos motors vectorials coexisteixen:** Konva/react-konva per al llenç general; Paper.js
  NOMÉS dins el sub-editor de nodes bezier ([PaperFlatEditor.jsx](../../frontend/src/pages/PaperFlatEditor.jsx)),
  que s'obre en doble-clic sobre un objecte `path`.
- **El model de dades del refactor ja és el nou:** l'antic `TechSheet` (O2O per model) està
  **eliminat** (migració `0050`). El document editable avui és un `ModelFitxer` tipus
  `TECHSHEET` amb extensió `.ftt` (zip: manifest + document.json + assets). Esquema **v2**
  amb clau `pages`.
- **Les eines "F3-7" (callout/detail/legend) NO són tipus d'objecte:** són *presets* que
  insereixen un `group` de primitives. **"Ploma" (F?) i "selecció de nodes" al toolbar
  principal són placeholders deshabilitats (`soon:true`).**
- **Deutes que toquen l'editor:** PDF antic (reportlab) viu però orfe d'UI; chunk
  `TechSheetEditor` = 596 kB (supera el llindar per defecte de Vite, sense `manualChunks`);
  gap residual del lock cooperatiu (sense heartbeat independent de l'autosave).

---

## BLOC 1 — El motor d'edició existent

### 1.1 On viu l'editor
| Peça | fitxer:línia | Nota |
|---|---|---|
| Motor principal | `frontend/src/pages/TechSheetEditor.jsx:1` | 2825 línies; tot inline (paleta, ribbon, panell props, capes, export) |
| Components exportats/reutilitzats | `TechSheetEditor.jsx:767` (`ObjectNode`), `:2807` (`ColorPicker`), `:2820-2825` (`SectionTitle`/`propLabel`/`propInput`) | + helpers `MM_TO_PX`, `serializePages`, `renderPageToDataURL`, `buildHeaderPrimitives`, `uid`, `toMm` |
| Editor de plantilla (Customer) | `frontend/src/pages/TechSheetTemplateEditor.jsx:1` | NO és motor propi: reimporta els components de TechSheetEditor (`:9-14`) |
| Sub-editor de nodes/bezier | `frontend/src/pages/PaperFlatEditor.jsx:44` | Paper.js; lazy import a `TechSheetEditor.jsx:9`, muntat `:2443`; s'obre en editar un `path`/`sketch_svg` |
| POC aïllada | `frontend/src/pages/PaperKonvaPoc.jsx` | ruta `disseny/poc-paper` (`App.jsx:220`), FORA del flux de producció |

**Rutes** (`frontend/src/App.jsx`): `/models/:id/fitxa` → `FttResolver` (`:156-160`, resol/crea el `.ftt` i redirigeix, ja no munta l'editor); `/models/:id/ftt/:fitxerId` → `TechSheetEditor` (`:162-166`); `/clients/:id/plantilla` → `TechSheetTemplateEditor` (`:168-172`).

**Model de dades (estat post-refactor):**
| Entitat | Estat | fitxer:línia |
|---|---|---|
| `TechSheet` (O2O per model) | **ESBORRAT** | `migrations/0050_delete_techsheet.py:38-40` (`DeleteModel`) |
| `TechSheetTemplate` (O2O per Customer) | Existeix, **DEPRECAT**, 0 files a BD | `tech_sheet_models.py:13-37` |
| `TechSheetDocument` (model dedicat) | **NO EXISTEIX** | — |
| Document editable real | `ModelFitxer` `tipus='TECHSHEET'`, ext `.ftt` (zip) | `models.py:328,348,350`; empaquetat a `services_ftt.py:1-50` |
| `DocumentTemplate` (plantilles del tenant, substitut previst) | Existeix | `ftt_models.py:36-64`; vistes a `ftt_document_views.py`, `urls.py:171-176` |
| `FttDocumentLock` (lock cooperatiu) | Existeix | `ftt_models.py:11-33` |

### 1.2 Inventari REAL vs catàleg d'eines
| EINA (catàleg ✅/🟢) | ESTAT | fitxer:línia | Nota |
|---|---|---|---|
| Selecció d'objecte | **EXISTEIX** | `TechSheetEditor.jsx:1136-1142` | click + shift-click (`toggleSelection`); **sense rubber-band (marc de drag)** |
| Selecció de nodes (punts) | **EXISTEIX DIFERENT** | toolbar `:2062` (`soon:true`) vs `PaperFlatEditor.jsx:49-165` | El botó del toolbar principal és placeholder deshabilitat; l'edició de nodes real només dins el sub-editor Paper.js (doble-clic sobre `path`) |
| Transform (moure/escalar/rotar) | **EXISTEIX** | `:2422` (`Transformer rotateEnabled`), `:1568-1620` | Konva Transformer natiu; `canResize=false` per line/arrow |
| Mirror | **EXISTEIX** | `:1143` (`mirrorObjects`), `:2252-2253` | mirror-h / mirror-v |
| Alinear / distribuir | **EXISTEIX** | `:1242` (`alignSelection`), `:1266` (`distributeSelection`), `:2242-2249` | l/c/r/t/m/b + distribute h/v |
| Z-order | **EXISTEIX** | `:1206`, `:2254`, `:2257` | només dins la capa `free` (LAYER_ORDER `:76`: template<data<free) |
| Formes (rect/el·lipse/polígon) | **EXISTEIX DIFERENT** | `:81` (`RECT_TOOLS`), `:1683-1699` | rect, rect_round, ellipse OK; **POLÍGON (N costats) NO EXISTEIX** |
| Línia / fletxa | **EXISTEIX** | `:82` (`LINE_TOOLS`), `:1700-1706` | line, line_dot, arrow, arrow2 |
| Text | **EXISTEIX** | `:1639-1641`, `:2083-2085` | text i text_box; align/decoration `:2647-2679` |
| Callout / detail / legend (F3-7) | **EXISTEIX DIFERENT** | `:85` (`PRESET_TOOLS`), `:1148-1172`, `:2092-2094` | **NO són tipus d'objecte:** *presets* que insereixen un `group` de primitives (text+arrow, ellipse+line, rect+text×3) |
| Zoom (F4) | **EXISTEIX** | `:77-79`, `:1118-1126` (`fitZoomToViewport`), `:2221-2224` | escala el Stage (scaleX/Y), no CSS |
| `type:'path'` al model | **EXISTEIX** | `:956`, `:1773-1792` | `paths:[{segments:[{x,y,inX,inY,outX,outY}]}]` (bezier amb handles) |
| Ploma (pen tool) | **NO EXISTEIX** | `:2067` (`k:'pen', soon:true`) | placeholder deshabilitat, sense handler cablejat |
| Fill / stroke | **EXISTEIX** | `:2688-2704` | panell props per rect/ellipse/line/arrow/path |
| ColorPicker | **EXISTEIX** | `:2807-2818` | component inline: swatches + `<input type=color>` |

### 1.3 Paper.js
Sí, dependència declarada: `frontend/package.json:25` (`"paper": "^0.12.18"`). Ús real:
`PaperFlatEditor.jsx:1` (producció, sub-editor de nodes) i `PaperKonvaPoc.jsx:4` (POC aïllada).
L'editor principal (`TechSheetEditor.jsx`) és **100% react-konva**; Paper.js entra només en
obrir el sub-editor de nodes bezier d'un `path` concret. → **dos motors coexistents.**

---

## BLOC 2 — El document i el render

### 2.1 Estructura real de `template_json`
Esquema **v2 amb clau `pages`** (no v1 pla). Dos contenidors:
- `TechSheetTemplate.template_json` (`tech_sheet_models.py:27`) — DEPRECAT, **0 files a BD** (verificat `count()==0`). Serializer llegeix `tj.get('pages')` (`tech_sheet_serializers.py:22-29`).
- Document `.ftt` per model (`ModelFitxer` TECHSHEET, via `services_ftt.py`): `document.json` intern = `{ftt_schema, metadata, pageFormat, pages:[{id, objects:[]}]}` (`services_ftt.py:40-51`). El front converteix amb `document_to_v2`/`v2_to_document` (`services_ftt.py:124-176`) → `{version:2, pageFormat, pages:[...]}`, que és el que consumeix el TechSheetEditor (comentari `TechSheetEditor.jsx:13`).

**Exemple real** (BD staging, schema `fhort`, `ModelFitxer` id=156, TECHSHEET is_current, desempaquetat read-only amb `services_ftt.unpack`):
```json
{
  "ftt_schema": 1,
  "pageFormat": "A4L",
  "pages": [{
    "id": "...",
    "objects": [
      { "type": "data_block", "kind": "graded_table", "layer": "data",
        "size_fitting_id": 52, "x": -74.66, "y": 42.84,
        "width": 150, "height": 145.8, "scale": 1, "scaleY": 1 },
      { "type": "path", "layer": "free", "fill": "#ca8a04",
        "paths": [{"closed": false, "fill": "#fafafa", "fillRule": "nonzero",
                   "segments": [{"inX":0,"inY":0,"outX":0,"outY":0,"x":49.97,"y":48.13}]}] },
      { "type": "arrow", "layer": "free", "fill": "#1d1d1b", "stroke": "#1d1d1b",
        "strokeWidth": 1.5, "x": 150.89, "y": 39.13, "x2": 211.89, "y2": 24.84 },
      { "type": "line", "layer": "free", "x": 0, "y": 0,
        "points": [92.57, 30.20, 157.14, 30.79], "stroke": "#1d1d1b", "strokeWidth": 1 }
    ]
  }]
}
```

### 2.2 Pipeline de render
- `renderPageToDataURL` existeix a `TechSheetEditor.jsx:701-718` — **imperatiu, offscreen** (crea un `Konva.Stage` fora del DOM, hi afegeix objectes amb `addObjectToLayer` `:612-696`, `stage.toDataURL()`).
- **Live vs export = DOS camins:** live = arbre declaratiu react-konva (`ObjectNode` `:767`) al `<Stage>` real; export/miniatures = funció imperativa `addObjectToLayer` sobre `Konva.Stage` separat. Comparteixen helpers de geometria (`dataBlockGroupProps`, `imageProps`, `textProps`, `rectProps`, `buildHeaderPrimitives`, `buildTablePrimitives`) per no divergir, però són **dues implementacions**.
- **Export PDF = client-side amb `pdf-lib`** (`TechSheetEditor.jsx:6`), funció `onExport` `:1954-1991`: per pàgina `renderPageToDataURL(p, 3.5, ctx)` → PNG → `embedPng` → `drawImage` a mida completa. És **rasterització de tota la pàgina** → cobreix TOT (capçalera, taula de mesures, imatges, sketches, text, formes). **No hi ha pdf-lib al backend**; el backend només rep el PDF ja fet via `FttDocumentExportView` (`ftt_document_views.py:137-160`) i el desa com `ModelFitxer` tipus `EXPORT`.

### 2.3 Element 'legend'/'table' col·locable (§3.3 pla mestre)
**NO existeix un element taula genèric (rows/columns) col·locable lliurement.** El més proper:
- `preset_legend` (`TechSheetEditor.jsx:1166-1174`, `PRESET_TOOLS:85`): `type:'group'` amb fills **estàtics** (rect + 3 text fixos), sense estructura tabular.
- `data_block` kind=`graded_table` (`:1896-1919`, botó ribbon `:2231`): és **la taula de mesures fixa** (la que el catàleg demana ignorar); col·locable/escalable però sempre lligada a un `size_fitting_id` i amb dades de grading en viu.
→ **Cap taula/llegenda estructurada de contingut arbitrari avui.**

### 2.4 Lock / edició cooperativa (timer-gap)
- Model `FttDocumentLock` (`ftt_models.py:11-35`): `document_root` (O2O a l'arrel de la cadena de versions), `locked_by`, `locked_at`. Identitat = arrel `versio_anterior` (v1), estable en avançar de versió.
- Lògica `services_ftt_document.py`: `FTT_LOCK_TTL = 30 min` (`:21`); `acquire_lock` (`:32-54`, force-if-stale); `release_lock` (`:57-69`); `renew_lock` (`:77-83`) cridat des de `FttDocumentDetailView.patch` (`ftt_document_views.py:98-99`) **a cada desat**.
- **Gap resolt:** amb autosave (debounce 2s, `TechSheetEditor.jsx:1481-1501`) el lock es renova i no caduca.
- **Gap residual (no cobert):** no hi ha heartbeat/`setInterval` independent de l'edició; si el document està obert però **sense canvis >30 min**, el lock esdevé stale i un altre usuari el pot prendre; el propietari original rep `403` al proper autosave, sense avís previ. Tampoc `beforeunload`: l'`unlock` només al cleanup de l'`useEffect` (`:1427-1438`, `keepalive:true`) → tancament brusc de pestanya només protegit pel TTL de 30 min.

---

## BLOC 3 — Fronteres i deutes que toquen l'editor

### 3.1 Antic TechSheet: què queda viu
- Model `TechSheet` (O2O) **totalment eliminat**: `migrations/0049_remove_techsheet_estat.py` + `0050_delete_techsheet.py` (`DeleteModel`, amb data-migration `migrate_remaining_techsheets` v2→.ftt via `services_ftt.v2_to_document` + `services_ftt_document.create_document`, `0050:6-27`). **Cap `import TechSheet` viu** (només comentaris de jubilació).
- `s8_views.py` a `models_app` **no existeix**. `tech_sheet_views.py` **existeix però és una altra cosa**: vista d'extracció IA "Sprint S17" (`TechSheetExtractView`, `TechSheetCreateModelView`, `:51-386`) que crea `Model`+`BaseMeasurement`; **no referencia** el model esborrat (cap import mort).
- **Viu i actiu del subsistema:** `TechSheetTemplate` (per Customer, deprecat, 0 files) `tech_sheet_models.py:13-38`; servit per `tech_sheet_serializers.py` + `tech_sheet_editor_views.py`, wired `urls.py:147-155`, consumit per `TechSheetTemplateEditor.jsx:7` i `api/endpoints.js:213-215`.
- **PDF antic (reportlab) viu però ORFE d'UI:** `export_model_spec_pdf_view` a `backend/fhort/pom/s8_views.py:229-347`, wired `tasks/urls.py:220-238` (`models/<id>/export/pdf/`), component `ExportModelPDF` a `frontend/src/components/ExportButton.jsx:100-108` — **però `ExportModelPDF` no té cap consumidor muntat** (`SizeSetDetail.jsx:7` només importa CSV). Endpoint + component vius, sense botó.
- **Escriptors de `Model.estat` pendents:** `tech_sheet_views.py:305` (`estat='Nou'` en import IA) i `pom/wizard_views.py:37-38` (`Nou`→`En curs`). Cap escriptor lligat a l'antic `TechSheet`.

### 3.2 KONVA_COL
Definició literal, `frontend/src/pages/TechSheetEditor.jsx:74`:
```js
const KONVA_COL = { white: '#ffffff', gold: '#c27a2a', border: '#e0d5c5', textMain: '#1d1d1b', textMuted: '#868685' }
```
5 claus: `white`, `gold`, `border`, `textMain`, `textMuted`. Motiu (`:70-73`): Konva pinta sobre `<canvas>` via `ctx.fillStyle` i no resol CSS custom properties. **Constant local, no exportada**, ~50 usos dins el mateix fitxer (taula grading `TBL:322-323`, header/paper `:407-426`, defaults per-node `:496-539`, layer base `:708`, previews de drag `:1694-1780`,`:2404-2425`, `ColorPicker`/`QUICK_COLORS` `:2806`). Cap consumidor extern.

### 3.3 Finder — `save_model_file` / `ModelFitxer`
Signatura literal, `backend/fhort/models_app/services_fitxers.py:36-86`:
```python
@transaction.atomic
def save_model_file(model, file, *, versio_anterior=None, categoria=None,
                    tipus=None, origen='upload', nom=None):
```
Gestió de `is_current` (retallat):
```python
if versio_anterior is not None:
    versio = (versio_anterior.versio or 0) + 1
    if categoria is None: categoria = versio_anterior.categoria
    if tipus is None:     tipus = versio_anterior.tipus
else:
    versio = 1
fitxer = ModelFitxer(model=model, ..., categoria=categoria or '',
                     tipus=tipus or 'ALTRES', versio=versio, is_current=True,
                     versio_anterior=versio_anterior, ...)
fitxer.fitxer.save(nom_fitxer, file, save=False)
fitxer.path_servidor = fitxer.fitxer.name
fitxer.save()
if versio_anterior is not None and versio_anterior.is_current:
    versio_anterior.is_current = False
    versio_anterior.save(update_fields=['is_current'])
return fitxer
```
**Invariant (correcció respecte a la hipòtesi):** `is_current` **NO** és "un per categoria/tipus". És **per cadena `versio_anterior`** (llista enllaçada): només es desmarca l'`is_current` del `versio_anterior` explícit passat; sense `versio_anterior` es crea una cadena nova independent (`versio=1`), sense tocar res més. → **depèn del crider passar el `versio_anterior` correcte**; si no, poden coexistir múltiples cadenes TECHSHEET `is_current=True`. Constants a `models.py:328`: `TIPUS_TECHSHEET='TECHSHEET'` (document `.ftt`), `TIPUS_EXPORT='EXPORT'` (PDF generat), i camp `generat_des_de` (FK a self) per enllaçar l'export amb la versió origen sense afectar-ne la cadena.

### 3.4 Versions instal·lades i chunk
`frontend/package.json`: `konva ^10.3.0`, `react-konva ^19.2.5`, `paper ^0.12.18`.
`frontend/vite.config.js` (18 línies): **sense `manualChunks` ni `chunkSizeWarningLimit`** → llindar per defecte 500 kB.
Build: `frontend/dist/assets/TechSheetEditor-rYa9dq-C.js` = **596 307 bytes (~582 KiB)** → **supera el llindar de 500 kB**; en build real Vite emetria l'avís de chunk gran (no hi ha res que el trossegi).

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT vs catàleg d'eines (documentador)

| Eina catàleg | Veredicte | Evidència |
|---|---|---|
| Selecció d'objecte | ✅ EXISTEIX | `TechSheetEditor.jsx:1136-1142` (sense rubber-band) |
| Selecció de nodes | ⚠️ DIFERENT | toolbar placeholder `:2062 soon:true`; real només a `PaperFlatEditor.jsx:49-165` |
| Transform (moure/escalar/rotar) | ✅ EXISTEIX | `:2422`, `:1568-1620` |
| Mirror | ✅ EXISTEIX | `:1143`, `:2252-2253` |
| Alinear / distribuir | ✅ EXISTEIX | `:1242`, `:1266`, `:2242-2249` |
| Z-order | ✅ EXISTEIX | `:1206`, `:2254`, `:2257` (només capa `free`) |
| Formes | ⚠️ DIFERENT | rect/rect_round/ellipse OK `:81`; **polígon FALTA** |
| Línia / fletxa | ✅ EXISTEIX | `:82`, `:1700-1706` |
| Text | ✅ EXISTEIX | `:1639-1641`, `:2083-2085` |
| Callout / detail / legend (F3-7) | ⚠️ DIFERENT | presets de `group`, no tipus d'objecte `:85`,`:1148-1172` |
| Zoom (F4) | ✅ EXISTEIX | `:77-79`, `:1118-1126` |
| `type:'path'` | ✅ EXISTEIX | `:956`, `:1773-1792` |
| Ploma (pen) | ❌ FALTA | placeholder `:2067 soon:true`, sense handler |
| Fill / stroke | ✅ EXISTEIX | `:2688-2704` |
| ColorPicker | ✅ EXISTEIX | `:2807-2818` |
| Taula/llegenda col·locable estructurada (§3.3) | ❌ FALTA | només `preset_legend` estàtic `:1166-1174` i `graded_table` fixa `:1896-1919` |

**Llegenda:** ✅ EXISTEIX (compleix el catàleg) · ⚠️ DIFERENT (existeix però amb forma o abast distint del citat) · ❌ FALTA (no implementat avui).

---

## BLOC 4 — Fonts de dades per a taules snapshot (ADDENDUM)

> Context: les taules col·locables congelaran (hardcode) el valor de la dada del model en el
> moment de col·locar-les. Mapa de la font de veritat per a cada tipus.

### 4.1 (12) MESURES — taula "POM variant fitting" a talla base
- **Model:** `BaseMeasurement` `models.py:461-516`. Camps: `model` (FK), `pom` (FK `pom.POMMaster`), `base_value_cm` (Float, NULL si fila plantilla sense valor), `is_key`, `is_active`, `nom_fitxa` (nomenclatura/fletxa croquis), `origen` (STANDARD/IMPORTED/MANUAL/FITTED/CALCULATED/TEMPLATE/CHECKED/ITEM_STANDARD), `tolerancia_minus/plus`, `ordre`. `unique_together=(model,pom)`.
- **Serializer:** `BaseMeasurementSerializer` `serializers.py:119-142` → retorna `id, model, pom, pom_code, pom_name_en, pom_name_cat, pom_abbreviation, pom_is_key, pom_category, pom_codi_client, pom_nom_client, base_value_cm, is_active, notes, nom_fitxa, origen, updated_at`. **Unitat implícita cm** (no camp explícit; ve de `base_value_cm`).
- **Endpoint:** `GET /api/v1/models/<model_id>/base-measurements/` → `base_measurements_view` (`urls.py:101`, `views.py:678` i variants ordenades `:1123/:1238/:1367`); CRUD genèric `BaseMeasurementViewSet` (`views.py:186`, router `base-measurements` `urls.py:42`).

### 4.2 (13) GRADING — run graduat, deltes i breaks
- **Run persistit:** `GradedSpec` `fitting/models.py:163-195` (FK `GradingVersion`, `pom`, `size_label`, `graded_value_cm`, `grading_type_applied`, `increment_applied_cm`, `is_active`, `generated_from_version`; `unique_together=(grading_version,pom,size_label)`).
- **Generació (servei intern):** `generate_graded_specs(size_fitting_id)` `pom/services.py:18`; motor `_apply_rule(...)` `pom/services.py:548-600` (LINEAR/STEP/FIXED/ZERO/EXCEPTION + forma canònica amb break). Dispar: `POST /api/v1/size-fittings/{id}/regenerar-talles/` → `regenerate_sizes_view` `pom/grading_views.py:27`.
- **Endpoint que RETORNA el run sencer per pintar:** `GET /api/v1/size-fittings/{id}/taula-mesures/` → `measurements_table_view` `pom/grading_views.py:44-153`. Retorna `{poms, talles, cells:{pom_id:{talla:{value,type,increment}}}}`; fallback a `BaseMeasurement` (només talla base) si no hi ha `GradingVersion` actiu.
- **BREAKS (LINEAR-with-break):** camps normalitzats a `GradingRule` `pom/models.py:547-586`: `increment_base`, `increment_break`, `talla_break_label`, `talla_break_pos` (pos = cache opcional; el break es resol per **etiqueta** contra `size_run` del model, no per posició — comentari `services.py:571-585`). Derivació: `derive_break_fields(...)` `pom/grading_utils.py:198`. Exposats directament (sense recalcular) via router `grading-rules` → `GradingRuleSerializer` `pom/serializers.py:156-166` (`increment_base, increment_break, talla_break_label, talla_break_pos`).
- **Conclusió:** SÍ hi ha endpoint del run sencer (`taula-mesures`); els breaks són camps de BD consultables via `grading-rules`, no cal recalcular al front.

### 4.3 (14) MATERIALS/TEIXIT — on es desa i estat del BOM
- **W4** `import_session_teixit_view` `extraction_views.py:1126-1145`: desa NOMÉS a `session.resultat['teixit']` (JSON dins `ImportSession.resultat`), camps `_TEIXIT_FIELDS` (`:1121-1122`): `fabric_main, fabric_composition, shrinkage_type, shrinkage_warp, shrinkage_weft, shrinkage_pct, shrinkage_iso_key, fabric_notes`. **No toca `Model` encara.**
- **W5** (confirmar) `extraction_views.py:1434-1440`: llegeix `session.resultat['teixit']` i `setattr(model, f, ...)` per camp no buit → escriptura final al `Model`.
- **Destí al `Model`** `models.py:292-314`: `fabric_main`, `fabric_composition` (CharField text lliure), `shrinkage_type` (choices), `shrinkage_warp/weft/pct` (Float), `shrinkage_iso_key`, `fabric_notes` (Text).
- **BOM:** **no existeix res estructurat.** Cap proveïdor de teixit, cap consum en metres, cap composició estructurada (només `fabric_composition` CharField). L'únic `Supplier` (`tasks/models.py:144`: `name`, `type` workshop/factory, `active`) és per a **Producció** (tallers), no teixit. `ConsumptionRecord` (`models_app/models.py:743-758`) és consum de **TEMPS de màquina**, no metres. → **Una taula BOM naixeria avui amb dades NOMÉS manuals.**

### 4.4 (15) CAPÇALERA DEL MODEL — placeholders disponibles
- **Serializer:** `ModelDetailSerializer` `serializers.py:88-114` (`fields='__all__'` sobre `Model` `models.py:75-314`) + derivats de lectura: `fitxers` (nested), `garment_type_nom`, `garment_group_nom`, `responsable_nom`, `created_by_nom`, `customer_nom`, `garment_type_item_nom`, `garment_type_item_code`, `size_system_codi`, `size_system_nom`, `grading_rule_set_nom`, `customer_logo` (URL absoluta del logo del Customer).
- **Camps natius útils:** `codi_intern`, `codi_client`, `codi_tenant`, `customer` (=client), `any`, `temporada` (SS/FW/CO/SP), `sequencial`, `nom_prenda`, `descripcio`, `color_referencia`, `collection`, `garment_type/group/item`, `fit_type`, `target`, `construction`, `size_system`, `grading_rule_set`, `estat`, `fase_actual`, `responsable` (FK UserProfile), `prioritat`, `data_entrada`, `created_by`, `created_at`, `data_objectiu`, `data_tancament`, `predicted_start/end`, `contracte`, `versio`, `size_run_model`, `base_size_label`, `fabric_*`, `observacions`.
- **Buits vs disseny:** **NO** hi ha camp dedicat "marca" (només `customer`/`customer_nom` + `customer_logo`), ni "dissenyador", ni "patronista" (només `responsable` genèric i `created_by`).

### 4.5 (16) metadata_json / metadata_schema
- `metadata_json`: **NO existeix enlloc** (grep sobre `backend/fhort` → 0 resultats).
- `metadata_schema`: existeix com a `JSONField(default=dict, blank=True)` a `DocumentTemplate` `ftt_models.py:53` (migració `0046_documenttemplate.py:20`; comentari `:52`: "esquema dels camps de metadata que la plantilla espera"). **Cap codi el llegeix ni el resol avui** (cap ús a `tech_sheet_editor_views.py`, `ftt_document_views.py`, `services_ftt_document.py`).
- El `.ftt` té una clau genèrica `"metadata"` dins el JSON (`services_ftt.py:40-48` `new_empty_document`, `:124-149` `v2_to_document`), però **es crea sempre buida** en producció: l'únic cridador (`services_ftt_document.py:94`) invoca `new_empty_document()` sense `metadata`. **Cap punt del codi omple aquest dict amb camps del `Model`** per resoldre placeholders de capçalera (confirmat per absència de `metadata[...] = model.` als serveis/vistes `.ftt`).

### Resum BLOC 4 — disponibilitat de font per a taula snapshot
| Taula snapshot | Font existent? | Endpoint per pintar | Nota |
|---|---|---|---|
| Mesures (POM base) | ✅ SÍ | `models/<id>/base-measurements/` | valor `base_value_cm`, cm implícit |
| Grading (run + deltes + breaks) | ✅ SÍ | `size-fittings/{id}/taula-mesures/` (+ `grading-rules` per breaks) | breaks ja a BD, no recalcular |
| Materials/teixit | ⚠️ PARCIAL | camps al `Model` (`fabric_*`) via `ModelDetailSerializer` | text lliure; sense BOM estructurat |
| BOM (avios/proveïdor/consum) | ❌ NO | — | naixeria amb dades només manuals |
| Capçalera model | ✅ SÍ | `ModelDetailSerializer` | sense "marca"/"dissenyador"/"patronista" dedicats |
| Resolució metadata a capçalera | ❌ NO | — | `metadata_schema` declarat però no resolt; `metadata` del `.ftt` sempre buida |

---

## BLOC 5 — Import vectorial (SVG) i subpaths (ADDENDUM)

> Punts 17-22. Font: investigador Sonnet + consulta read-only a BD staging
> (`ModelFitxer id=156`, model_id=162, `services_ftt.unpack`, sense escriptura).

### 5.1 (17) Import d'SVG: existeix?
**SÍ, existeix import d'SVG extern**, cablejat a `TechSheetEditor.jsx`:
- Botó ribbon "Importar pla" → `ribbonTool({key:'import-flat', onClick:()=>openImport('garment')})` `:2233`; input ocult `accept=".svg,image/svg+xml"` `:2570`; panell drag&drop `:2509` (accepta `.svg,.dxf`).
- Handler: `handleFlatSvgFile` `:1830` → `FileReader.readAsText` → `importFlatSvgText` `:1796` → `convertLegacySketchSvgObject` `:991` → `legacySketchSvgToPath` `:927` que fa **`scope.project.importSVG(..., {insert:true, expandShapes:true})` de Paper.js** (no parser propi, no regex).
- **DXF detectat però NO suportat** (`import_dxf_soon` flash `:2133`).
- **(b)** El sub-editor `PaperFlatEditor.jsx` edita paths ja existents (pot re-importar via `importSVG` un `sketch_svg` llegat, `:228`).
- **(c)** `images_to_extract` (`extraction_prompt.py:222`) són **rasters** del pipeline IA, sense relació amb l'import vectorial. `ModelSheet.jsx:1389,1561` accepta `.svg` només com a **pujada de ModelFitxer genèric**, no al llenç.

### 5.2 (18) Modelat + `sketch_svg` vs `path`
**Un únic `type:'path'` amb MOLTS subpaths dins `paths:[...]`** (no un objecte per subpath, no raster). `legacySketchSvgToPath` (`:922-965`) fa `imported.getItems({class: scope.Path})` i mapeja **cada `Path` → una entrada de `paths[]`**, després reassigna `type:'path'` a l'objecte pare.

| | `sketch_svg` (llegat/transitori) | `path` (definitiu) |
|---|---|---|
| Camps | `svg` (string cru), `width`, `height` | `paths:[{closed,fill,fillRule,stroke,strokeWidth,segments}]` + fallbacks obj-level |
| Render live | `SketchSvgObj` → `useImage(svgDataUrl)` → **rasteritzat a `Konva.Image`** `:743-753` | `PathObj` → `Konva.Path` per subpath `:755-765` (vectorial) |
| Render PDF | `addObjectToLayer` sketch_svg → `Konva.Image` (raster) `:690-694` | `addObjectToLayer` path → `Konva.Path` per subpath `:652-663` |
| Editable nodes | No (cal convertir; migració `convertLegacySketchSvgs` `:967-989`, a càrrega `:1454`) | Sí (`PaperFlatEditor`) |

**Exemple real staging** (`type:'path'`, **438 entrades a `paths[]`**), retall:
```json
{ "closed": false, "fill": null, "fillRule": "nonzero",
  "segments": [
    {"inX":0,"inY":0,"outX":0,"outY":0,"x":49.976,"y":48.134},
    {"inX":-0.196,"inY":1.685,"outX":0.209,"outY":-1.764,"x":50.969,"y":46.253}
  ],
  "stroke": null, "strokeWidth": 0.2 }
```
Stats de les 438 entrades: `fillRule` sempre `'nonzero'` (**0 `'evenodd'`**); `closed` mixt; `fill` divers (`null`, `#fafafa`, `#1d1d1b`…).

### 5.3 (19) Fill per subpath — el render el respecta?
- **Desat:** `fillRule` per subpath via `normalizeFillRule` `:865-867` (default `'nonzero'`).
- **LIVE:** `pathChildProps` passa `fillRule` a cada `<Path>` react-konva `:572-584`,`:760-761`.
- **PDF:** `addObjectToLayer` `:652-663` construeix `Konva.Path` amb **el MATEIX `pathChildProps`** → **idèntic al live, sense divergència** (mateixa font/mateix Konva; `konva/lib/Shape.js:23-37` fa `context.fill(fillRule)` natiu a dibuix i hit).
- **Conclusió parcial:** live i PDF pinten **igual** perquè comparteixen `pathChildProps`.

### 5.4 (20) Winding / forats — ⚠️ descobriment
**Els forats (evenodd) NO sobreviuen a la importació d'SVG.** Encadenat:
- Paper.js crea un `CompoundPath` quan el `d` té >1 `M`/`Z` (`paper-core.js:8106-8114`).
- L'estil evenodd s'aplica al `CompoundPath`, però `Style.js:12481-12509` **exclou el `CompoundPath` de propagar `fill/fillRule` als fills** → exterior i forat queden amb `fillRule` propi buit (default `'nonzero'`).
- `getItems({class: scope.Path})` és **recursiu** (`paper-core.js:4186`) → **extreu els fills del compound com a entrades independents de `paths[]`**, perdent l'agrupació.
- Resultat: exterior i forat esdevenen **dos subpaths germans sòlids** (el forat es tapa amb el mateix color), no un forat real. `fillRule` es desa fidelment però és **moot**: mai hi ha >1 subpath dins un mateix `Konva.Path.data`, condició necessària perquè `evenodd` retalli. Coherent amb l'exemple real (0 `evenodd` en 438 entrades) i amb `docs/diagnosis/MICROPROVA_CALLIE.md:33` (10 `CompoundPath` detectats en import real).
- **Live vs PDF:** pinten **igual entre ells** (mateix bug compartit), però **cap dels dos mostra el forat**.

### 5.5 (21) Hit-test
Selecció **a nivell d'objecte Konva sencer**; el hit geomètric és per subpath però la selecció bombolleja al pare:
- `PathObj` `:755-765`: `<Group onDblClick=onDblVector>` amb un `<Path key={i} hitStrokeWidth={10}/>` **per entrada de `paths[]`** — cap `sceneFunc` custom; `Konva.Path` estàndard amb `data` (`pathToData` `:545-570`).
- Hit individual de cada `<Path>`: default Konva — **per fill** (amb `fillRule`) o **per stroke amb `hitStrokeWidth=10`** (molts subpaths són `fill:null`, només contorn).
- **La selecció sempre és el pare:** `onClick` només al `Group` extern (`ObjectNode` `:767-776`, `onSelect` `:2411` amb `o.id` top-level); els `<Path>` fills no tenen `onClick` → bubbling. `selectedIds` sempre d'objectes sencers `:1135-1142`.
- Granularitat per subpath/segment **només al `PaperFlatEditor`** (`sketchLayer.hitTest(...)` `:260`), fora de Konva. Al render PDF no hi ha hit (stage destruït `:701-717`).

### 5.6 (22) PaperFlatEditor roundtrip
Funció `commit` `PaperFlatEditor.jsx:309-346` (exposada via `useImperativeHandle` `:353`):
- `type:'path'`: `sketchLayer.getItems({class: scope.Path}).map((path, index) => ({...source, closed: path.closed, segments:[...]}))`, on `source = flat.paths?.[path.data?.index ?? index] || {}` `:332-344`.
- **CONSERVA els subpaths:** cada `paper.Path` viu (`path.data.index`, assignat a l'import `:216`) es re-mapa a la **mateixa posició** de `flat.paths[index]` — **no aplana ni fusiona**. Nombre d'entrades es manté (tret que l'usuari afegeixi/elimini nodes, avui majoria `disabled` `TechSheetEditor.jsx:2186-2189`).
- **`closed` es recalcula** des de Paper viu; **`fill/fillRule/stroke/strokeWidth` es preserven** via `...source` (Paper no els edita: sense UI de color/fillRule al node-editor).
- `onCommit({paths})` `:345` → `commitFlatEdit` `TechSheetEditor.jsx:1852-1858` → `updateObject(editingFlatId, {paths})` (substitueix `paths[]` 1:1). Si l'objecte encara és `sketch_svg`, `commit` fa `exportSVG({asString:true})` `:348` → branca `else` `:1859-1869` (actualitza `svg/width/height`).

### Resum BLOC 5
| Aspecte | Estat | Nota |
|---|---|---|
| Import SVG extern | ✅ EXISTEIX | Paper.js `importSVG`, ribbon "Importar pla" `:2233` |
| Import DXF | ❌ FALTA | detectat, "soon" |
| Modelat SVG | 1× `type:'path'` amb N subpaths a `paths[]` | 438 en exemple real |
| `sketch_svg` vs `path` | Dos tipus; sketch_svg = raster llegat, path = vectorial editable | migració automàtica a càrrega |
| Fill/fillRule per subpath | ✅ respectat idènticament live i PDF | comparteixen `pathChildProps` |
| Forats (evenodd) | ❌ **NO sobreviuen a l'import** | compound aplanat a subpaths germans sòlids; `fillRule` desat però moot |
| Hit-test | objecte sencer (bubbling al pare) | subpath-level només al PaperFlatEditor |
| Roundtrip Paper→JSON | ✅ conserva subpaths (no aplana) | preserva fill/fillRule, recalcula `closed` |

---

## BLOC 6 — Reflexos d'edició + plantilles (ADDENDUM FINAL)

> Punts 23-32. Reflexos = `TechSheetEditor.jsx`. Plantilles = backend `.ftt`.

### 6.1 (23) Undo/redo
**NO EXISTEIX.** Cap pila d'història, cap `useRef` d'snapshots, cap `past/future`, cap listener `Ctrl/Cmd+Z`. L'únic `ti-history` (ribbon `:2211`) és el nº de versió del model, `disabled:true`. Cada acció crida `updateObject`/`updatePageObjects` que muta `pages` **sense estat previ recuperable**.

### 6.2 (24) Teclat — inventari complet
| Tecla | Acció | Guàrdies | fitxer:línia |
|---|---|---|---|
| `Delete`/`Backspace` | Esborra seleccionats **només si `layer==='free'`** | inactiu si `editingFlatId`, `editingText`, focus en INPUT/TEXTAREA/SELECT, `!locked` o `!selectedIds.length` | `:1540-1555` |
| `Space` (down/up) | Pan temporal (`spaceHeld`) | inactiu si `!locked`, `editingText` o `typing()` | `:1557-1566` |
| `Enter` (dins textarea) | Confirma text (`commitTextEdit`) si no és Shift+Enter | només al textarea overlay | `:2436` |
| `Shift+Enter` (textarea) | Salt de línia | — | `:2436` |
| `Escape` (textarea) | Tanca edició sense desar | **cap Escape global** (no deselecciona ni tanca PaperFlatEditor) | `:2436` |
| Fletxes ↑↓←→ | **CAP acció** (sense nudge) | — | absent |
| `Ctrl/Cmd`+tecla | **CAP** (l'únic `ctrl/metaKey` és Ctrl+roda = zoom `:1723-1728`, no keydown) | — | `:1723-1728` |
| `Shift`+clic objecte | Multi-selecció (`toggleSelection`) | — | `:1139-1142` |

Cap altre `keydown/keyup`/`onKeyDown` al fitxer.

### 6.3 (25) Copiar / enganxar / duplicar
**NO EXISTEIX cap mecanisme** (grep `clipboard|duplicate|copy|paste|Cmd+D` sense hits rellevants). Sense `cloneObject`, `navigator.clipboard`, ni handlers `Ctrl/Cmd+C/V/D`.

### 6.4 (26) Grups
- **Agrupar/desagrupar selecció arbitrària SÍ:** `groupSelection()` `:1211-1231` (mín. 2, exclou `template`, crea `type:'group'` amb `children`), `ungroupObject()` `:1232-1241` (`globalizeObject` + reinsereix pla). Botons ribbon `group`/`ungroup` `:2250-2251`.
- **Mateix mecanisme que els preset groups** (`createPreset` `:1146-1175`): idèntica estructura `type:'group'`+`children`; sense distinció de dades entre grup d'usuari i preset.
- **Doble clic sobre un `group`: NO FA RES** (`ObjectNode` group `:828-843` no passa `onDblClick`, fills amb `selectable/draggable=false`). El grup només es manipula sencer o es desfà. (Text/path SÍ tenen dbl-click → edició inline / PaperFlatEditor.)

### 6.5 (27) Panell de capes / lock-hide per objecte
- **Panell de capes SÍ existeix** com a tab del dock (`layers`, `ti-stack-2` `:2529`): llista `[...ordered].reverse()` `:2541-2567`, clic → `selectOnly(o.id)`; per fila en capa `free` amb lock: botons forward/backward (`moveSelectionInFreeLayer`) `:2555-2562`.
- **NO hi ha `locked`/`visible`/`hidden` per objecte** al `template_json` respectats per la UI: `ti-eye` és l'estat global readonly-overlay `:2204,2391`; `ti-lock` és `ratioLocked` (proporció W/H) `:2620`. **Cap toggle d'ocultar/bloquejar objecte individual.**

### 6.6 (28) Snapping
**NO EXISTEIX** (grep `snap|guide|grid|magnet` sense codi; l'únic "guide" és icona d'una eina `note` `soon:true` `:2090`). Sense imant a graella/objectes/marges ni guies intel·ligents.

### 6.7 (29) Shift durant dibuix/transform
- `shiftKey` només a: (1) multi-selecció shift-clic `:1140`; (2) Enter vs salt de línia al textarea `:2436`.
- **Dibuixar amb Shift NO restringeix** a quadrat/cercle ni 45°/ortogonal (cap `shiftKey` als handlers de dibuix ~`:1600-1710`).
- **`Transformer keepRatio` és FIX**, no per Shift: `keepRatio={selectedObjects.length===1 && selObj?.type==='data_block'}` `:2422`. Només `data_block` manté proporció; la resta `false`, sense consulta de `shiftKey` (qualsevol comportament Shift als anchors seria el default natiu de Konva).

### 6.8 (30) Contracte de creació de document `.ftt`
- **Endpoint:** `POST /api/v1/models/<model_id>/ftt-document/` → `FttDocumentCreateView` `ftt_document_views.py:44-54` (`urls.py:171`). El paràmetre `template_id` és **només un comentari "reservat per a B5"**: mai es llegeix del request, `document_json` sempre `None` → **sempre crea buit** via `services_ftt.new_empty_document()`.
- **Servei:** `create_document(model, *, document_json=None, assets=None, preview=None, nom=None)` `services_ftt_document.py:91-103` → `pack` + `save_model_file(tipus=TIPUS_TECHSHEET, categoria="Document")`.
- **"Crear des de DocumentTemplate": NO EXISTEIX** (cap còpia de pages/objects d'una plantilla).
- **Bloc `urls.py:171-176` = "Documents .ftt sobre el Finder"**, NO CRUD de plantilles:

| Ruta | Mètode | Vista |
|---|---|---|
| `models/<id>/ftt-document/` | POST | `FttDocumentCreateView` |
| `ftt-documents/<id>/` | GET/PATCH | `FttDocumentDetailView` |
| `ftt-documents/<id>/lock/` | POST | `FttDocumentLockView` |
| `ftt-documents/<id>/unlock/` | POST | `FttDocumentUnlockView` |
| `ftt-documents/<id>/export/` | POST | `FttDocumentExportView` |
| `ftt-documents/<id>/asset/<name>/` | GET | `FttDocumentAssetView` |

- **`DocumentTemplate` (`ftt_models.py:38-65`) NO té CAP vista/serializer/ruta/admin.** Únic ús = import `noqa` a `models.py:879`. És un model **declarat però mort** (sense superfície).

### 6.9 (31) TechSheetTemplateEditor — què edita i accés UI
- **Edita el `TechSheetTemplate` DEPRECAT** (per Customer, 0 files), **no** `DocumentTemplate`. API `techSheetTemplate` `endpoints.js:213-215` → `customers/<id>/tech-sheet-template/` (GET) i `.../update/` (PATCH) `urls.py:154-155`; backend `get_or_create_template`/`update_template` `tech_sheet_editor_views.py:22-54` escriuen `TechSheetTemplate.template_json`.
- **NO és orfe:** botó per fila a la llista de clients (`Customers.jsx:112`, icona `ti-layout`, gated `canEdit`) → `navigate('/clients/:id/plantilla')`; ruta a `App.jsx:168-171`.

### 6.10 (32) Manifest del `.ftt` — discriminador de tipus?
- **manifest.json** (`pack` `services_ftt.py:74-79`): `magic="FTT"`, `schema_version=1`, `app_version`, `checksums{path→sha256}`.
- **document.json** (`new_empty_document` `:40-51`): `ftt_schema=1`, `metadata={}`, `pageFormat="A4L"`, `pages=[{id,objects:[]}]`.
- **NO hi ha cap camp `kind`/`doc_type`/`is_template`** ni al manifest ni al document.json. `unpack` `:200-210` valida `magic` estrictament contra `FTT_MAGIC` → un `.fttpt` hauria de **reutilitzar el mateix magic** i, per distingir "document" de "plantilla", **caldria afegir un camp nou** (a `metadata` o al manifest); avui **no hi ha discriminador de tipus**. Zip: `manifest.json` + `document.json` + `assets/<nom>` + `preview.png` (opcional).

### Resum BLOC 6
| Reflex | Estat | Nota |
|---|---|---|
| Undo/redo | ❌ FALTA | mutació directa sense història |
| Teclat | ⚠️ MÍNIM | només Delete (capa free), Space (pan), Enter/Esc (dins textarea); sense fletxes ni Cmd+X |
| Copy/paste/duplicate | ❌ FALTA | cap mecanisme |
| Agrupar/desagrupar | ✅ EXISTEIX | però doble-clic al grup no hi entra |
| Panell de capes | ✅ EXISTEIX | sense lock/hide per objecte |
| Snapping | ❌ FALTA | cap imant/guia |
| Shift (dibuix/transform) | ❌ FALTA | no restringeix; keepRatio fix només data_block |
| Crear document `.ftt` | ✅ (buit) | `template_id` reservat, sense "crear des de plantilla" |
| DocumentTemplate | ⚠️ MORT | model declarat, 0 superfície (sense vista/ruta/admin) |
| TechSheetTemplateEditor | ⚠️ DEPRECAT-viu | edita TechSheetTemplate (0 files); accés UI actiu des de Clients |
| Discriminador tipus al `.ftt` | ❌ FALTA | sense `kind`/`is_template`; caldria camp nou |

---

*Sense opinió de disseny ni proposta. Diagnosi read-only; cap fitxer de codi modificat, cap commit. BLOCs 1-3: investigadors 1-3 (Sonnet). BLOCs 4-6: investigadors addendum (Sonnet). Síntesi: documentador. Diagnosi TANCADA.*
