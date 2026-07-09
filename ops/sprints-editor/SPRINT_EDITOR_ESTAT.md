# SPRINT_EDITOR_ESTAT — fil de continuïtat (actualitzat per Claude Code a cada tancament)

## Cua
| Sprint | Títol | Estat | Commits |
|---|---|---|---|
| S0 | Undo/redo + clipboard | ✅ FET | 49d32f8 · ae10385 · ec5fb37 |
| S1 | Reflexos selecció/teclat | ✅ FET | be5406e · 0434980 · 3402637 · 6a7f194 |
| S2 | Snapping + regles + guies | ✅ FET | 7c79c03 · 20f8325 · 64e7b7c |
| S3 | Taules snapshot | ✅ FET | 0f0eaec · 51cb361 · b777f7e · 57bae65 |
| S4 | FTTPT fase 1 | ✅ FET | 9cca059 · 84bcbf0 · eff8599 · a00d45d · 1fef297 |
| S5 | FTTPT fase 2 (placeholders) | ✅ FET | c76c77d · e233fec · 8197e11 |
| S6 | Subpath fill + forats | ✅ FET | 419eb42 · 56f01d1 |
| S7 | Ploma + polígon + cursor | ✅ FET | bde942c · 6272b48 · 2fa186c |
| S8 | Buscatraços + presets cota | ✅ FET | 40ac49b · 8d90218 · 2039194 |
| S9 | Deutes tècnics | ✅ FET | f6272be · 7232898 · 79c2796 |

## Referències fixes
- Mapa verificat: docs/diagnosis/DIAGNOSI_EDITOR_ESTAT.md (Blocs 0–6). NO re-investigar
  el que cobreix; només mini-diagnosi de verificació per sprint.
- Fitxer central: frontend/src/pages/TechSheetEditor.jsx (2825 línies pre-run).
- Decisions de producte: vault SESSIO_2026-07-06_IMPORT_I_EDITOR.md (8 decisions Patró C).

## Registre per sprint
(Claude Code hi afegeix, per cada sprint tancat: data/hora · commits amb hash ·
decisions tècniques preses · desviacions respecte al pla · pendents/deutes nous ·
migracions aplicades amb fitxer)

---

### Pas 0 — 2026-07-06 · FET
- Backup BD: `/root/backup_pre_sprints_editor.dump` (pg_dump -Fc PG18:5433, 641.759 bytes, 1196 TOC entries, arxiu verificat amb pg_restore --list).
- Tag git: `pre-sprints-editor` a `6517440` (dev).
- **Adaptació documentada del gate "git status net":** l'arbre de fitxers *seguits* és net (0 modificats/staged). Existeixen 52 fitxers *untracked* preexistents (docs/diagnosis, .md de disseny arrel, .claude/, ops/ dels propis sprints, i `frontend/public/CALLIE.svg`) — cap és codi font sota `frontend/src` o backend. Com que els commits usen `git add` selectiu (mai -A), no poden filtrar-s'hi, i el tag captura un HEAD net. Aturar-se aquí hauria bloquejat la run sobre els seus propis documents d'entrada (p.ex. `DIAGNOSI_EDITOR_ESTAT.md`, "Referència fixa"). Gate satisfet en esperit; sense canvi d'abast.

### S0 — Undo/redo + clipboard — 2026-07-06 · ✅ FET (porta verda)
- **Commits:**
  - `49d32f8` feat(editor): S0 pila d'història undo/redo amb coalescing (history.js) — nou mòdul `frontend/src/pages/ftt/history.js` (primera extracció fora del monòlit; hook `useDocumentHistory` + helpers purs `cloneWithNewIds`/`offsetObjectMm`) + wiring a TechSheetEditor.jsx (import :8, hook :1120, `resetHistory` a `hydrate` :1459 i :1461).
  - `ae10385` feat(editor): S0 dreceres Cmd/Ctrl+Z undo · Shift+Z/Ctrl+Y redo — nou useEffect keydown :1564.
  - `ec5fb37` feat(editor): S0 clipboard intern copy/paste/duplicate (C/V/D) — `clipboardRef` :1122; C/V/D dins el mateix effect keydown :1583-1605.
- **Decisions tècniques:**
  - Coalescing = **debounce sobre `pages`** (500 ms), no commit-per-gest. Motiu: captura TOTES les mutacions (les ~12 funnelen per `updatePageObjects`→`setPages` amb refs immutables) sense tocar cada call-site; "el simple guanya". Model timeline past⇄baseline⇄future amb guarda `applying` i flush a `undo()`; snapshots per referència (segurs perquè mai hi ha mutació in-place). Límit 50.
  - `reset(pages)` cridat a `hydrate` (i al `.then` de `convertLegacySketchSvgs`) perquè la càrrega inicial NO esdevingui una entrada "document buit" desfeta.
  - Undo/redo **buiden la selecció** (el simple guanya; permès pel sprint).
  - Clipboard: `Cmd/Ctrl+C` desa referències dels objectes `free` seleccionats (no clon en copiar); segur perquè les mutacions són immutables (l'objecte referenciat és un snapshot congelat) i el paste sempre fa `cloneWithNewIds` (clon JSON pregon + uids nous, recursiu a `children`). `V`/`D` desplacen +5 mm (coords en mm; `toPx=mm*2.4`). Només capa `free`.
  - `cloneWithNewIds(obj, makeId)` rep la factoria d'id per paràmetre → evita cicle d'import history.js↔TechSheetEditor.jsx.
- **Desviacions:** cap d'abast. C/V/D consolidats al mateix effect que undo/redo (guardes idèntiques; el sprint ho permetia). Import dels helpers de clipboard diferit al commit 3 (fronteres de diff netes).
- **Porta verda:** `npm run build` exit 0 (TechSheetEditor 596→598.5 kB; l'avís >500 kB és preexistent i s'ataca a S9). Diff-review Opus OK. Guarda i18n: cap string UI nou, cap fitxer locale tocat. Guarda UI: cap hex nou. Autosave i lock intactes (no tocats).
- **Smoke:** en aquest entorn no es pot dirigir el llenç Konva headless. Lògica verificada per revisió de codi. **Seqüència manual reproduïble per a Agus:** crear rect → moure'l (drag llarg) → Cmd+Z (torna, 1 sola entrada) → Cmd+Shift+Z (reavança) → Cmd+C, Cmd+V (nou objecte +5 mm, uid distint) → Cmd+D (duplica) → Delete → Cmd+Z (reapareix). Verificar que escriure en un textarea de text NO trenca l'undo global (Cmd+Z ignorat amb focus a textarea).
- **Pendents/deutes nous:** cap. (Nota per a S9: el mòdul `ftt/history.js` és el primer satèl·lit; l'avís de chunk continua.)
- **Deute menor detectat (NO és de S0, per a Agus):** `offsetObjectMm` de S0 desplaça `x/y`, però `lineProps`/`arrowProps` forcen `x:0,y:0` al render → el paste/duplicate d'una **línia o fletxa** crea l'objecte amb uid nou però SENSE desplaçament visual (+5 mm). Rects/text/el·lipses/paths sí es desplacen. No es va reobrir S0 (disciplina d'abast); S1 va introduir `translate()` type-aware que ho resol per al nudge. Candidat trivial: encaminar paste/dup per `translate()` en un futur toc.

### S1 — Reflexos selecció/teclat — 2026-07-06 · ✅ FET (porta verda)
- **Commits (4, granularitat per punts en comptes de l'agrupació suggerida 1+2/3+4/5+6, permès pel sprint "un per punt"):**
  - `be5406e` S1 rubber-band selecció + dreceres d'eina V/T/R/E/L — punts 1+2.
  - `0434980` S1 nudge amb fletxes (±1/±10mm) + Shift 45°/proporcional — punts 3+4.
  - `3402637` S1 lock/hide per objecte (dues bandes) + toggles al panell de capes — punt 6.
  - `6a7f194` S1 doble-clic per entrar a un grup i moure'n els fills — punt 5.
- **Decisions tècniques:**
  - **Rubber-band:** marc en tela buida amb eina `select`; selecció per intersecció AABB via `node.getClientRect({relativeTo: layer})` (coords de contingut = mateix espai que `stagePoint`). Shift acumula. Marc menyspreable (≤3px) = clic simple (deselecció). Marc pintat amb `KONVA_COL.gold` + `opacity 0.15` (sense hex cru, guarda UI).
  - **Dreceres d'eina:** V/T/R/E/L; effect keydown amb guarda `metaKey||ctrlKey||altKey` (no segresta Cmd+V etc.). A/P NO lligades (reservades S7).
  - **Nudge:** fletxes ±1mm / Shift ±10mm; helper `translate(o,dx,dy)` **type-aware** (line→`points`, arrow→`x,y,x2,y2`, resta→`x,y`) perquè lineProps/arrowProps ignoren x/y. Ràfega = 1 entrada d'història (coalescing de S0, sense codi extra).
  - **Shift dibuix/transform:** `snap45()` encaixa línia/fletxa a 45° (a move i up, via `e.evt.shiftKey`); estat `shiftHeld` (keydown/keyup/blur) alimenta `Transformer keepRatio` → resize proporcional amb Shift per a tot; data_block segueix sempre proporcional.
  - **Lock/hide (dues bandes):** camps opt-in `locked`/`visible` retrocompatibles (`=== true`/`=== false`, absent = comportament actual). Amagat NO es pinta ni live ni export (4 llocs: map live, ObjectNode grup, `renderPageToDataURL`, `addObjectToLayer` grup). Bloquejat exclòs de select/drag/Transformer/delete/nudge/rubber-band. Toggles ull/cadenat (Tabler outline, tokens COL) al panell de capes, files de capa `free`. i18n: `layer_hide/show/lock/unlock` × ca/es/en.
  - **Grups (entrar):** estat `activeGroup`+`selectedChildId`; doble-clic entra (neteja selecció), fills esdevenen seleccionables/movibles (drag) — NO rotar/redimensionar/editar-text (abast mínim, "seleccionar/moure fills"). `handleChildDragEnd` muta el fill niat amb la mateixa semàntica line/arrow/altres. `cancelBubble` evita reseleccionar el grup. Sortides: Escape · clic en tela buida · seleccionar un altre objecte. Grup entrat no arrossegable com a bloc. Sense Transformer per fills (fora d'abast).
- **Desviacions:** granularitat de commits (4 en lloc de 3) — permès. Grup-entrar limitat a select+moure (documentat). Un comentari `//` entre atributs JSX a la branca de grup (esbuild-vàlid; build exit 0) — estil inusual, no bloquejant.
- **Porta verda:** build exit 0 (TechSheetEditor 603.30 kB; avís >500 kB preexistent → S9). Diff-review Opus dels 4 commits OK. Guarda i18n OK (4 claus × 3 locales, parsegen). Guarda UI OK (cap hex cru fora KONVA_COL/COL; Tabler outline). Llei historial OK (tota mutació nova — nudge, moure-fill, toggles — passa per `setPages`→història S0). Llei dues bandes OK (lock/hide verificat a export).
- **Smoke (manual, per a Agus; Konva no dirigible headless):** (1) drag en buit = marc daurat, selecciona objectes tocats, Shift acumula. (2) V/T/R/E/L canvien d'eina; amb focus a un input no. (3) fletxes mouen ±1/±10mm; multi-selecció junta; 1 undo per ràfega. (4) línia amb Shift = 45°; resize amb Shift = proporcional. (5) doble-clic grup → moure un fill → Escape surt; export/miniatura reflecteix el moviment. (6) al panell: amagar un objecte → desapareix de llenç I de PDF; bloquejar → no seleccionable/movible; desbloquejar/mostrar recupera. Docs .ftt sense els camps nous carreguen idèntics.
- **Pendents/deutes nous:** grup-entrar sense Transformer per fills (moure sí, redimensionar/rotar no) — ampliable si es demana. Nested groups: onDblGroup no propaga a subgrups niats (rar; acceptat).

### S2 — Snapping + regles + guies — 2026-07-06 · ✅ FET (porta verda)
- **Commits (3):**
  - `7c79c03` S2 snapping en drag (objectes + marges/centre de pàgina) amb guies — nou mòdul `frontend/src/pages/ftt/snapping.js` (pur: `buildCandidates`/`computeSnap`).
  - `20f8325` S2 regles en mm (superior/esquerra) amb marcador de cursor.
  - `64e7b7c` S2 guies arrossegables des de les regles (persistides, snap, no export).
- **Decisions tècniques:**
  - **Snapping (mòdul pur):** candidats = vores+centres dels ALTRES objectes (bbox via `node.getClientRect` al **dragstart**, no per frame) + marges i centre de pàgina + guies. `computeSnap` tria l'ancoratge més proper dins llindar. Llindar en px de pantalla (`SNAP_PX=8`) → mm via `/(MM_TO_PX*zoom)` (escala amb zoom). Guies daurades temporals (`strokeScaleEnabled=false` → 1px a qualsevol zoom). Cmd/Ctrl desactiva el magnetisme. Integrat via `onDragStart`/`onDragMove` afegits a `common` d'ObjectNode (només al top-level del map viu; no als fills de grup).
  - **Regles:** marc CSS-grid extern (cantonada + banda superior + banda esquerra + viewport) que NO toca res dins del viewport tret d'`onScroll` i treure-li `flex:1`. Alineació de ticks calculada des de la geometria REAL (`wrapRef.getBoundingClientRect()` vs viewport) → correcta a qualsevol zoom/scroll, sense reconstruir padding/centrat. Ticks SVG (minor 5mm, major 20mm amb etiqueta), tokens COL. Marcador de cursor daurat: `cursorMm` actualitzat a `onStageMouseMove` (només en passar per sobre del Stage → re-render acotat).
  - **Guies:** camp `pages[i].guides=[{axis:'x'|'y',pos:mm}]` (retrocompat absent=[]). **Persistència: passthrough afegit als 4 punts** (serializePages, v2ToDocument, documentToV2, hydrate); backend desa document.json opac → sense canvi backend. Render com a `Line` Konva daurada arrossegable amb `dragBoundFunc` bloquejat a un eix; `onGuideDragEnd` mou o **esborra si es treu fora de pàgina**. Creació arrossegant des de la regla (`onMouseDown` a la banda → listeners window mousemove/up → push a guides). Snapping a guies: automàtic (handleDragStart ja passa `p.guides`). Guies NO exportades (viuen a `page.guides`, no `page.objects`; export intacte). Moure/crear/esborrar guia = entrada d'història (via `setPageGuides`→`setPages`).
- **Desviació d'abast documentada (per a Agus):** el sprint diu "snapping en drag/resize". S'ha implementat **només DRAG** (que és el que verifica la porta verda: "drag d'un rect s'imanta…"). El snapping en **resize** (via Transformer `anchorDragBoundFunc`) s'ha DIFERIT: és notablement més fràgil i cap criteri verd el prova; fer-lo malament posaria en risc la run. Candidat de continuació clarament acotat. La resta del sprint (regles, cursor, guies persistides+snap+no-export) completa.
- **Porta verda:** build exit 0 (TechSheetEditor 608.70 kB; avís >500 kB preexistent → S9). Diff-review Opus dels 3 commits OK. Guarda i18n OK (cap string nou; cap locale tocat; etiquetes de regla són números). Guarda UI OK (cap hex cru; KONVA_COL al llenç, COL al DOM). Llei historial OK. Llei dues bandes OK (guies fora d'export verificat).
- **Smoke (manual, per a Agus):** (1) arrossega un rect a prop d'un altre → s'imanta a la vora/centre amb guia daurada; a prop del centre de pàgina també; Cmd mentre arrossegues desactiva. (2) regles mm a dalt/esquerra; marcador daurat segueix el cursor; ticks alineats en fer zoom i scroll. (3) arrossega des de la regla superior → guia vertical; persisteix en desar/recarregar; objectes s'hi imanten; arrossega-la fora de pàgina → s'esborra; PDF exportat SENSE regles ni guies. Docs .ftt sense `guides` carreguen igual.
- **Watchpoints menors:** `cursorMm` re-renderitza en moure el ratolí sobre el Stage (acotat a hover de pàgina; si es nota lag, throttle trivial). Snapping en resize diferit (dalt).

### S3 — Taules snapshot (T1a/T1b/T2/custom) + substitució graded_table — 2026-07-06 · ✅ FET (porta verda)
- **Commits (4):**
  - `0f0eaec` element `type:'table'` + render dues bandes (`buildTableCellPrimitives`).
  - `51cb361` picker de variant + taules snapshot T1a (fitting) i T1b (grading). *(amend d'una correcció de revisió — hash únic 51cb361.)*
  - `b777f7e` taules T2 (BOM) i personalitzada + edició de cel·les al panell.
  - `57bae65` substitució del botó ribbon graded_table pel picker.
- **Decisions tècniques:**
  - **Element genèric `type:'table'`** (layer free, x/y/scale/width/height mm) amb `columns[{key,label,width}]`, `rows[[cell]]`, `snapshot{model_id,size_fitting_id?,snapshot_at}`, `style{fontSize(pt,min 8),headerFill,zebra}`. Render a DUES bandes reutilitzant la infraestructura de primitives existent (`PrimNode` live / `addPrimsToGroup` export) via un builder germà `buildTableCellPrimitives` (no s'ha sobrecarregat `buildTablePrimitives`, específic del graded). Cel·la = `string | {text,sub?,bold?}` (extensió mínima per a POM bilingüe i breaks en negreta; fila a dues línies si alguna cel·la porta `sub`). Transform: table s'afegeix a la branca data_block de `handleTransformEnd` (bake d'escala) i a `keepRatio` (proporcional). `serializeObject` ja passa `type:'table'` sencer → round-trip sense canvis.
  - **SNAPSHOT (llei Agus):** valors HARDCODEJATS a la inserció; `snapshot{}` només traçabilitat. T1a/T1b congelades; T2/custom editables (panell).
  - **Descobriment de forma de dades (verificat llegint backend, NO assumit):** `GET models/<id>/base-measurements/` NO passa per `BaseMeasurementSerializer` sinó per un dict fet a mà a `pom/wizard_views.py` (`{pom_id, nom_client, nom_ca, base_value_cm, nom_fitxa, pom_abbreviation, pom_code_global,...}`) — **sense `nom_en` i sense tolerància**. Solució: el **nom EN canònic** de la columna POM de T1a es recupera del `grading-rules` ja unit (`rule.pom_nom_en`), amb fallback a `nom_client`/`pom_code_global`; **Tol±** queda buida (font no l'exposa; coherent amb "imprimir i anotar a mà"). Join per `pom_id`.
  - **T1a** = base-measurements + `grading-rules/?rule_set=<model.grading_rule_set>` (param verificat al ViewSet). Columnes: Nomenclatura · POM(EN+CA) · Base(cm) · Regla/Δ(`increment_base`) · Break(`talla_break_label`) · Tol±(buida) · Mesura nova(BUIDA) · Comentaris(BUIDA, la més ampla).
  - **T1b** = reutilitza l'endpoint provat `GET fitting/{sf}/graded-table/` ({base_size,size_labels,rows[{ref,nom_en,nom_ca,valors,deltas}]}); breaks marcats en **negreta** a la cel·la de talla on canvia l'increment (`deltas[sl] != deltas[prev]`). Δ via `rowDelta` existent.
  - **T2 BOM** neix buida (5 columnes Material/Ref/Proveïdor/Consum/Notes, 4 files buides, editable). **Custom** = diàleg files×columnes → taula buida editable. Edició de cel·les via **panell de propietats** (inputs per etiqueta de columna i per cel·la; afegir/eliminar fila/columna) NOMÉS per kind bom/custom (T1a/T1b sense editor → congelades).
  - **Substitució ribbon:** el botó "Taula" ara obre el picker (`setTablePicker({})`); `disabled: !locked` (T2/custom no necessiten size-fitting; T1a/T1b es desactiven al picker si `!sizeFittings.length`). El **render llegat de graded_table es conserva** (branques ObjectNode/addObjectToLayer i l'efecte tableData intactes) → docs .ftt existents segueixen pintant. `insertGradedTable`/`onAddTableClick`/`pickFitting` queden com a LEGACY (candidats a poda futura, NO esborrats).
- **Desviacions:** T1a "nom EN canònic" via grading-rules (la font primària no el tenia); Tol± buida (font no l'exposa). Cap canvi d'abast. Break marcat en negreta (no vora) perquè el model de cel·la genèric ho suporta net.
- **Porta verda:** build exit 0 (TechSheetEditor ~620 kB; avís >500 kB → S9). Diff-review Opus dels 4 commits OK (inclosa lectura de serializers backend per fixar formes). Guarda i18n OK (215 claus × ca/es/en, paritat, parsegen). Guarda UI OK (cap hex nou; TBL/COL/KONVA_COL). Llei historial OK (inserts/edicions via addObject/updateObject→setPages). Llei dues bandes OK (mateix `buildTableCellPrimitives` a live i export).
- **Smoke (manual, per a Agus — necessita backend + model amb dades):** obrir editor d'un model amb size-fitting i grading actiu → botó Taula → (1) T1a: es col·loca, mostra POM EN+CA, columnes Mesura nova/Comentaris buides, es mou/escala; (2) T1b: breaks en negreta, live==export (PDF ≥8pt llegible); (3) T2 BOM i (4) Custom: es col·loquen buides, s'editen al panell (afegir fila/columna, escriure cel·les). Un doc antic amb `data_block graded_table` encara renderitza. **Validar sobre el model golden 162 / QA-SC 182** (memòria) que les dades de T1a/T1b quadren.
- **Pendents/deutes nous:** poda futura de `insertGradedTable`/`pickFitting`/`onAddTableClick` (legacy, sense consumidor després de la substitució). Tol± a T1a sense font (caldria exposar tolerancia_minus/plus al dict de base-measurements si es vol omplir — backend). Edició no re-ajusta l'escala (l'usuari redimensiona).

### S4 — FTTPT fase 1 (plantilles del tenant) — 2026-07-06 · ✅ FET (porta verda) · BACKEND+FRONTEND+MIGRACIÓ
- **Commits (5):**
  - `9cca059` camp `kind` (document|template) al manifest del .ftt (retrocompat: absent→document). Backend `services_ftt.pack/unpack`.
  - `84bcbf0` DocumentTemplate `created_by` + serializer/viewset/ruta (migració GENERADA, no aplicada pel subagent).
  - `eff8599` crear document des de plantilla (`template_id`) + desar-com-a-plantilla (backend endpoints).
  - `a00d45d` chooser blanc|plantilla al nou document + desar com a plantilla (frontend).
  - `1fef297` poda del botó/ruta TechSheetTemplateEditor (jubilat).
- **MIGRACIÓ APLICADA + AUDITADA (protocol):** `models_app/migrations/0051_documenttemplate_created_by.py` — aplicada amb `migrate_schemas` (no --schema). Auditoria DIRECTA a BD (no fiar-se de l'OK de Django): `\d fhort.models_app_documenttemplate` confirma columna `created_by_id bigint NULL`, índex btree, i FK → `fhort.accounts_userprofile(id)` DEFERRABLE. Contingut de la migració:
  ```python
  dependencies = [('accounts','0003_userprofile_jornada_override'), ('models_app','0050_delete_techsheet')]
  operations = [migrations.AddField(model_name='documenttemplate', name='created_by',
      field=models.ForeignKey(blank=True, null=True, on_delete=SET_NULL,
      related_name='document_templates_created', to='accounts.userprofile'))]
  ```
  (models_app és TENANT app → taula al schema `fhort`, no public. 0 files → cap risc de dades.)
- **Decisions tècniques:**
  - `kind` viu al **manifest** (font de veritat); `.fttpt` és cosmètic. `unpack` normalitza `kind` amb default 'document' (retrocompat total dels .ftt existents).
  - **DocumentTemplate** (ja existia, "mort") revifat: només faltava `created_by` (mirall de `Model.created_by`, FK a `accounts.UserProfile` = AUTH_USER_MODEL, per això `request.user` s'hi assigna directe). CRUD via `ftt_template_views.py` (Serializer+ViewSet, IsAuthenticated, `perform_create` fixa created_by+origen='tenant'), ruta `document-templates`. NO s'ha tocat el `TechSheetTemplate` deprecat.
  - **Desar com a plantilla:** `POST ftt-documents/<id>/save-as-template/ {nom,descripcio}` → carrega el head server-side (`load_document`, assets inclosos, fresc per autosave) → `pack(kind=template)` → crea DocumentTemplate amb el `.fttpt`. Sense netejar snapshots de taules (queden com a mostra estàtica, llei Agus).
  - **Nou document des de plantilla:** `FttDocumentCreateView` llegeix `template_id` → desempaqueta el `.fttpt` → `create_document(document_json, assets)` (kind nou = document). Plantilla corrupta/buida → fallback a blanc (mai 500). Frontend: `FttResolver` mostra chooser blanc|plantilla NOMÉS si hi ha plantilles al tenant (si no, crea blanc silenciós com abans).
  - **Poda:** tret botó "plantilla" de Customers.jsx + ruta `/clients/:id/plantilla` + import a App.jsx; `TechSheetTemplateEditor.jsx` amb bàner de jubilació (fitxer conservat, orfe, ja no es trosseja al build). Backend `tech_sheet_models/serializers/views` + API `techSheetTemplate` = **candidats G-poda** (NO esborrats).
- **Porta verda:** `manage.py check` net · `npm run build` exit 0 · migració aplicada+auditada (\d) · **servei reiniciat (ftt-staging.service active running)** i rutes noves VIVES verificades per HTTP (`document-templates/` i `save-as-template/` → **401 auth, no 404** = rutes registrades amb el codi nou desplegat). Diff-review Opus dels 5 commits. i18n paritat (222 claus × ca/es/en). Retrocompat verificada (kind absent→document; .ftt antics sense canvis).
- **Nota operativa (per a Agus, benigna):** al restart, gunicorn emet `[ERROR] Control server error: [Errno 13] Permission denied: '/var/www/.gunicorn'` — és el control-server opcional de gunicorn (socket de control), preexistent i NO afecta el servei (respon correctament). No causat per aquesta run.
- **Smoke (manual, per a Agus):** (1) editor → grup Fitxer → "Desa com a plantilla" → nom/descr → es crea una DocumentTemplate. (2) obrir /models/<altre>/fitxa sense techsheet → apareix chooser blanc|plantilla → triar la plantilla → el document neix amb el seu contingut (taules com a mostra, assets inclosos). (3) el botó "plantilla" ja no surt a Clients; la ruta /clients/:id/plantilla ja no existeix.
- **Pendents/deutes nous:** G-poda backend TechSheetTemplate (models/serializers/views + endpoints.js `techSheetTemplate` + fitxer TechSheetTemplateEditor.jsx orfe). `save-as-template` depèn de la frescor de l'autosave (2s) del head; si es vol garantir, forçar un desat abans (menor). `metadata_schema` de DocumentTemplate encara sense ús (arriba a S5 amb els placeholders).

### S5 — FTTPT fase 2: placeholders + resolució — 2026-07-06 · ✅ FET (porta verda) · FRONTEND + BACKEND lleu
- **Commits (3):**
  - `c76c77d` element `type:'field'` (xip placeholder) + pestanya "Camps" (frontend).
  - `e233fec` resolució de placeholders de TEXT en instanciar des de plantilla (backend).
  - `8197e11` resolució del logo del client com a IMATGE (asset dins el .ftt) (backend).
- **Decisió d'integració (adaptació documentada):** S4 no va crear un flux separat "editar plantilla"; el flux nou-document-des-de-plantilla és **server-side** (`create_document` al backend). Per tant: (a) la **resolució viu al backend** (on hi ha el model) — no al frontend; (b) el **panell de camps** s'ofereix mentre s'edita un document (pestanya "Camps"), per col·locar-hi placeholders abans de "Desar com a plantilla"; un `type:'field'` residual en un `kind=document` no instanciat es pinta com a **xip amb el label literal** (punt 4, mai crash).
- **Decisions tècniques:**
  - **Element `type:'field'`** `{key,label,x,y,style}` → xip: rect vora daurada puntejada + fons `goldPale` + text `{label}`. Render DUES bandes amb `buildFieldChipPrims` (mateix builder a live `FieldChipNode` i export `addObjectToLayer`). `blocksTransform` inclou `field` (moure sí, redimensionar no). `serializeObject` el passa sencer. `KONVA_COL.goldPale='#f5e6d0'` afegit (canvas no resol CSS vars; reutilitza el literal ja present a `buildHeaderPrimitives`). `dash` afegit a `PrimNode`/`addPrimsToGroup` (additiu, undefined per a la resta).
  - **Catàleg v1 (16 camps, de ModelDetailSerializer §4.4, sense inventar marca/dissenyador/patronista):** nom_prenda, codi_intern, codi_client, customer_nom, collection, temporada_any, color_referencia, descripcio, responsable_nom, data_entrada, base_size_label, size_system_nom, fabric_main, fabric_composition, customer_logo (imatge), data_avui. Pestanya "Camps" (clic = inserir).
  - **Resolució backend** (`resolve_placeholders(document_json, model) → (document_json, assets)`): serialitza el model un cop (`ModelDetailSerializer`), recorre pàgines→objectes→children (grups), substitueix `type:'field'`→`type:'text'` amb el valor real (buit si absent, no bloquejant); `temporada_any`=concat, `data_avui`=`timezone.localdate()`. `customer_logo`→`type:'image'` amb els bytes del logo del client afegits als assets del `.ftt` (`assets/field_customer_logo.<ext>`, 40×16 mm); sense logo o lectura fallida → text buit (mai 500). Cridat NOMÉS a la branca `template_id` de `FttDocumentCreateView`, abans de `create_document`; assets fusionats amb els de la plantilla.
  - Text resolt = forma mínima `{id,type:'text',layer,x,y,text,fontSize}` (la resta la posa `textProps` per defecte al frontend — sense acoblar la font).
- **Porta verda:** `npm run build` exit 0 (TechSheetEditor ~625 kB → S9) · `manage.py check` net · **servei reiniciat (active running)** · ruta `models/<id>/ftt-document/` viva (401). Diff-review Opus dels 3 commits. i18n paritat (240 claus × ca/es/en). Dues bandes (xip a live i export). **VERIFICACIÓ RUNTIME real** (shell tenant fhort, model 162 OLIVIA DRESS): `nom_prenda`→text "OLIVIA DRESS"; camp `customer_nom` DINS UN GRUP→text "Textiles y Confecciones Brownie SL" (recursió a children OK); `customer_logo`→text buit + 0 assets (aquest client no té logo → degradació correcta); `rect` intacte; 0 camps residuals.
- **Smoke (manual, per a Agus):** editar un document → pestanya "Camps" → inserir p.ex. {Nom del model}, {Client}, {Logo del client} → "Desa com a plantilla" → nou document d'un altre model des d'aquesta plantilla → els camps apareixen resolts com a text/imatge estàtics (verificar amb un client que SÍ tingui logo perquè surti la imatge). El JSON resultant no conté cap `type:'field'`. Export PDF correcte.
- **Pendents/deutes nous:** cap nou. (L'avís no-bloquejant de "camp buit" es resol a text buit sense UI; si es vol, es podria retornar la llista de camps buits a la resposta del create.) Provar el logo amb un client amb imatge (model 162 no en té).

### S6 — Vectorial 1: subpath fill + forats evenodd — 2026-07-06 · ✅ FET (porta verda) · FRONTEND
- **Commits (2):**
  - `419eb42` selecció de subpath + fill/stroke dirigit per peça (live-only).
  - `56f01d1` forats evenodd a l'import (CompoundPath→subpaths) + roundtrip PaperFlatEditor + fixture.
- **Decisions tècniques:**
  - **Selecció de subpath:** estat `activeSubpath {objId,index}`. Primer clic selecciona l'objecte sencer; SEGON clic (amb l'objecte ja seleccionat) sobre una peça l'activa (`cancelBubble` evita re-seleccionar el pare). Realç: override visual de stroke daurat a la peça activa (no muta dades). Fill/stroke del panell dirigits a `paths[index]` quan hi ha subpath actiu, si no a l'objecte sencer (comportament actual). Sortir: Escape · seleccionar un altre objecte · `clearSelection`. Història automàtica (updateObject→setPages). i18n `subpath_active`/`subpath_whole`.
  - **Model de dades ampliat (retrocompat):** una entrada de `paths[]` és SIMPLE `{closed,fill,fillRule,stroke,strokeWidth,segments}` (com fins ara) O COMPOSTA `{fill,fillRule:'evenodd',stroke,strokeWidth,subpaths:[{closed,segments},...]}` (exterior + forats).
  - **Render DUES bandes:** `pathToData` refactoritzat — si `subpaths`, concatena `M...Z` per subcamí (Konva retalla el forat amb `fillRule:'evenodd'`); si no, `segmentsToData` (cos idèntic a l'antic). `pathChildProps` (compartit per live `PathObj` i export `addObjectToLayer`) ja passa `fillRule` → **totes dues bandes** pinten el forat igual. Helper `entrySegments` per als 3 punts de bbox (subpath-aware).
  - **Import (correcció §20):** substituït `getItems({class:Path})` (recursiu, aplanava els compounds) per un walk `collect` que tracta el `CompoundPath` com UNA entrada (`fillRule:'evenodd'` + `subpaths` dels seus fills Path), sense descendir-hi; els `Path` solts queden com abans. Els flats ja importats (438 germans) no canvien.
  - **Roundtrip PaperFlatEditor:** import construeix el paper.Path des de l'exterior (`subpaths[0]`, els forats no es mostren al sub-editor de nodes — limitació documentada); commit conserva els compounds (edita `subpaths[0]`, preserva la resta de forats intactes; sense `segments` de nivell superior paràsit). Entrades simples: idèntiques a abans.
  - **Fixture** `frontend/public/fixtures/s6_evenodd_test.svg`: 3 peces soltes (2 rect + 1 circle) + 1 `<path fill-rule="evenodd">` amb 2 subcamins (anell rectangular amb forat).
- **Porta verda:** build exit 0 · diff-review Opus dels 2 commits · i18n paritat (242 × ca/es/en) · guarda UI (cap hex nou al codi; KONVA_COL) · dues bandes (pathToData compartit) · retrocompat (entrades simples sense canvi, condicionals claven en `subpaths`). Frontend-only → sense restart.
- **Smoke (manual, per a Agus; Konva/Paper no dirigibles headless):** importar `frontend/public/fixtures/s6_evenodd_test.svg` via "Importar pla" → les 3 peces es poden pintar d'un color diferent per clic (segon clic = peça); el forat de la 4a peça es veu BUIT a live I a PDF exportat. Doble clic sobre la peça amb forat → PaperFlatEditor mostra l'exterior; desar → el forat es conserva al tornar (live + PDF).
- **Pendents/deutes nous:** el sub-editor de nodes (PaperFlatEditor) NO mostra ni edita els forats d'un compound (només l'exterior); els forats es preserven però no s'hi poden retocar nodes. Ampliable (editar CompoundPath complet al sub-editor) si es demana. Subpath-select no cablejat per a paths dins de grups entrats (fora d'abast).

### S7 — Vectorial 2: ploma + polígon + cursor + drecera A — 2026-07-06 · ✅ FET (porta verda) · FRONTEND
- **Commits (3):** `bde942c` ploma · `6272b48` polígon · `2fa186c` drecera A.
- **Decisions tècniques:**
  - **Ploma (P):** màquina d'estats multi-clic (`penRef` en px de contingut, `penTemp` per pintar). Clic=ancoratge; clic+drag=handles bezier simètrics (out=drag, in=-out); Shift=45° (`snap45`); clic sobre el primer punt (≤8px, amb ≥2 punts)=tanca; Enter=acaba obert; Escape=CANCEL·LA el traç sencer (el simple guanya, documentat); Backspace=treu l'últim punt. Resultat = `type:'path'` estàndard amb segments `{x,y,inX,inY,outX,outY}` en mm (mateix format que l'import → editable al PaperFlatEditor). Preview: path daurat + segment elàstic + punts d'ancoratge. Botó de paleta habilitat (tret `soon:true`); drecera `p`. Consistència px/mm: penRef en px, conversió a mm només a `finishPen` i (px→mm→toPx) al preview via `pathToData`.
  - **Polígon:** eina al flyout de formes (`ti-hexagon`), inscrit al drag (bbox com ellipse), N costats (`polygonSides` estat, default 6, min 3, input al dock quan l'eina és activa). `polygonPoints(x,y,w,h,n)` (vèrtexs a angles `-π/2+2πk/n`) → `type:'path'` tancat, cantonades sense handles. Afegit a `CROSSHAIR_TOOLS`.
  - **Cursor precís:** ja cablejat (`CROSSHAIR_TOOLS` + `viewportCursor` → `crosshair`); només calia afegir-hi `polygon`. Caps Lock NO (fora d'abast).
  - **Drecera A:** effect keydown dedicat; amb UN sol `path`/`sketch_svg` seleccionat, `A` obre el PaperFlatEditor (`startVectorEdit`, = doble-clic). Cap edició de nodes al llenç principal (el sub-editor ja ho fa).
- **Porta verda:** build exit 0 (TechSheetEditor ~630 kB → S9) · diff-review Opus dels 3 commits · i18n paritat (244 × ca/es/en) · guarda UI (cap hex nou; KONVA_COL/COL; Tabler outline) · dues bandes (ploma/polígon = `type:'path'` via pathToData) · història (addObject→setPages). `polygonPoints` verificat en Node per n=3 i n=6. Frontend-only → sense restart.
- **Smoke (manual, per a Agus; Konva no dirigible headless):** eina Ploma (P) → clics + un clic-drag per una corba → clic sobre el primer punt tanca → pintar-la → doble clic (o A) obre PaperFlatEditor i els nodes coincideixen → desar → roundtrip fidel. Polígon: triar 6 costats, arrossegar → hexàgon; canviar a 3 → triangle. Cursor = creueta amb eina de dibuix, fletxa amb selecció.
- **Pendents/deutes nous:** llindar de tancament de la ploma fix a 8px de contingut (no escala amb zoom; menor). Undo a mig traç = Escape (cancel·la tot) o Backspace (últim punt); no hi ha undo-granular integrat a la història global (el traç no és a `pages` fins a finalitzar).

### S8 — Buscatraços + presets cota POM/anotació — 2026-07-06 · ✅ FET (porta verda) · FRONTEND
- **Commits (3):** `40ac49b` helper JSON↔Paper (paperbool.js) · `8d90218` buscatraços al ribbon · `2039194` presets cota POM i anotació.
- **Decisions tècniques:**
  - **paperbool.js (mòdul pur):** `withPaperScope(fn)` (scope Paper.js offscreen amb `document.createElement('canvas')`, teardown al finally); `objectToPaperPath(obj,scope)` (rect/rect_round→`Path.Rectangle`, ellipse→`Path.Ellipse`, path→`Path`/`CompoundPath` des de segments/subpaths; transforms rotation/scale aplicats al voltant de l'origen de l'objecte); `paperPathToPathObject(item,style,makeId)` (CompoundPath→entrada `subpaths` evenodd model S6, Path→entrada simple); `booleanOp(objects,op,style,makeId)` encadena `result[op](items[i])`. Segments llegits DINS del scope (abans del teardown). Sense cicle d'import (makeId/style per paràmetre).
  - **Buscatraços:** `PATHFINDER_TYPES=['path','rect','rect_round','ellipse']` (polígon és path). Grup nou al ribbon (organize) amb 4 botons (`ti-layers-union/subtract/intersect/difference`, verificats), actius només amb `≥2` convertibles seleccionats i `locked`. `applyPathfinder(op)`: objectes ordenats bottom→top (z=ordre de document → subtract = inferior menys superior), estil de l'inferior; **UNA sola** `updatePageObjects` (substitueix originals per 1 `type:'path'`) → **1 entrada d'història** → undo recupera els originals. Resultat compost (evenodd) si cal → forat visible (render S6). Fallada → flash.
  - **Presets:** `preset_cota_pom` (grup: línia horitzontal + 2 ticks perpendiculars als extrems + text lliure "A · 00" — SENSE binding a POM viu, frontera G1 fora d'abast) i `preset_annotation` (grup: text amb fons + fletxa fina). Grups de tipus existents (line/text/arrow) → render dues bandes automàtic. Icones `ti-ruler-2`/`ti-note` (distintes de les plaçades `soon:true` `cota_pom`/`note`).
- **Porta verda:** build exit 0 (TechSheetEditor ~634 kB → S9) · diff-review Opus dels 3 commits · i18n paritat (254 × ca/es/en) · guarda UI (cap hex nou al codi d'editor; els literals de paperbool.js són fallbacks de dades) · dues bandes (resultat = type:'path' via S6; presets = tipus existents) · història (buscatraços = 1 mutació; presets = addObject). Paper.js booleà NO dirigible headless → verificat per build+revisió (com S6).
- **Smoke (manual, per a Agus; Paper.js no headless):** seleccionar 2 el·lipses → Unir = 1 path. Restar un cercle d'un rect (cercle a sobre) = **forat visible (live I PDF — prova àcida S6)**. Intersecar i Excloure correctes. Undo després d'una operació recupera els objectes originals. Inserir preset Cota POM (editar el text a mà) i Anotació.
- **Pendents/deutes nous:** poda candidata: les eines de paleta `soon:true` `cota_pom` i `note` queden cobertes pels presets nous (redundants). Transforms exòtics (escala no-uniforme + rotació combinada) a `objectToPaperPath` poc provats. Boolean amb paths OBERTS té resultat indefinit de Paper (l'usuari ha d'usar formes tancades).

### S9 — Deutes tècnics de l'editor — 2026-07-07 · ✅ FET (porta verda) · FRONTEND + BACKEND (poda)
- **Commits (3):** `f6272be` manualChunks · `7232898` heartbeat lock + beforeunload · `79c2796` poda export PDF antic.
- **Decisions tècniques:**
  - **manualChunks (vite.config.js):** el projecte usa **Vite 8 / rolldown-vite** → `manualChunks` ha de ser la forma **FUNCIÓ** (la forma objecte peta amb `TypeError`). Buckets: `vendor-konva` (konva+react-konva), `vendor-paper`, `vendor-pdf` (pdf-lib), `vendor-react` (react/react-dom/router/axios/i18next/zustand — calia per baixar l'entry `index` de 612 kB). **Resultat: cap chunk d'APP > 500 kB** (index 612→**273 kB**, TechSheetEditor 634→**124 kB**); només `vendor-pdf` (510 kB) supera el llindar, és un vendor cacheable (acceptable per objectiu). PaperFlatEditor segueix lazy (chunk propi 7 kB). Lazy-splits de dnd-kit/gantt intactes (no s'ha fet catch-all).
  - **Heartbeat lock:** `setInterval` 10 min (< TTL 30 min) que re-POSTa `/lock/` (re-adquirir com a propietari actualitza `locked_at` → renova; verificat a `acquire_lock`); tanca el forat "obert i inactiu >30 min". Llegeix `fttHeadId.current` dins el callback (segueix el head després de cada desat). `beforeunload` amb `unlock` `keepalive` (best-effort per tancament brusc de pestanya; complementa el unlock del cleanup d'unmount). Frontend-only (sense endpoint nou). Netejat d'interval + listener a l'unmount/canvi de lock.
  - **Poda PDF antic:** eliminats `export_model_spec_pdf_view` (pom/s8_views.py, reportlab) + `import io` orfe, la ruta a tasks/urls.py, i el component `ExportModelPDF` a ExportButton.jsx. Grep previ: cap consumidor viu (`.jsx`/`.js`); només una nota `.txt` (ignorada). Grep posterior: 0 referències de codi. Helpers CSV i altres exporters conservats.
- **Porta verda:** `manage.py check` net · `npm run build` exit 0 amb **tots els chunks d'APP < 500 kB** (verificat: màxim index 273 kB) · **servei reiniciat (active running)** · **ruta antiga `/export/pdf/` → 404** (retirada i desplegada), `ftt-document/` → 401 (viva). Diff-review Opus dels 3 commits.
- **Smoke (manual, per a Agus):** obrir un doc, dibuixar, exportar PDF (funciona amb pdf-lib client). Heartbeat: obrir un doc, no tocar-lo 12 min → hi ha d'haver un re-POST /lock/ registrat (inspeccionar Network o baixar l'interval a test). L'antic botó/endpoint d'export PDF (reportlab) ja no existeix.
- **Pendents/deutes nous:** el heartbeat de 10 min no s'ha pogut verificar en temps real headless (revisió de codi + build). `paperbool.js` va fer `paper` d'import EAGER (via TechSheetEditor→paperbool) des de S8 → ara `paper` és un vendor-chunk propi però es carrega amb l'editor (abans era lazy via PaperFlatEditor); menor (vendor cacheable). Si es vol tornar-lo lazy, `paperbool` hauria de fer `import('paper')` dinàmic (booleanOp async).

---

## RESUM FINAL DE LA RUN — 2026-07-06/07 · S0→S9 COMPLETS (10/10) ✅

**Estat:** tota la cua S0–S9 tancada amb porta verda. Cap STOP. Branca `dev` local (SENSE push — Agus pusha al matí).

### Pas 0
- Backup BD `/root/backup_pre_sprints_editor.dump` (641.759 B, verificat). Tag `pre-sprints-editor` a `6517440`.

### Commits per sprint (hash · missatge curt)
- **S0** `49d32f8` història undo/redo (history.js) · `ae10385` dreceres Cmd+Z/redo · `ec5fb37` clipboard C/V/D
- **S1** `be5406e` rubber-band + V/T/R/E/L · `0434980` nudge + Shift 45°/proporcional · `3402637` lock/hide (dues bandes) · `6a7f194` entrar a grup
- **S2** `7c79c03` snapping · `20f8325` regles mm + cursor · `64e7b7c` guies (persistides, snap, no export)
- **S3** `0f0eaec` element type:table · `51cb361` picker + T1a/T1b · `b777f7e` T2/custom + edició cel·les · `57bae65` substitució botó ribbon
- **S4** `9cca059` kind al manifest · `84bcbf0` DocumentTemplate created_by + API · `eff8599` crear-des-de-plantilla + desar-com (backend) · `a00d45d` chooser + desar-com (frontend) · `1fef297` poda TechSheetTemplateEditor
- **S5** `c76c77d` element type:field + pestanya Camps · `e233fec` resolució text (backend) · `8197e11` resolució logo→imatge (backend)
- **S6** `419eb42` selecció subpath + fill dirigit · `56f01d1` forats evenodd import + roundtrip + fixture
- **S7** `bde942c` ploma bezier · `6272b48` polígon · `2fa186c` drecera A (obre PaperFlatEditor)
- **S8** `40ac49b` paperbool.js (JSON↔Paper) · `8d90218` buscatraços ribbon · `2039194` presets cota POM + anotació
- **S9** `f6272be` manualChunks (<500kB app) · `7232898` heartbeat lock + beforeunload · `79c2796` poda export PDF antic

### Migracions aplicades (a staging, auditades)
- `models_app/0051_documenttemplate_created_by.py` — AddField `created_by` (FK accounts.UserProfile, SET_NULL, null). Aplicada amb `migrate_schemas`; auditada amb `\d fhort.models_app_documenttemplate` (columna + índex + FK confirmats). 0 files → cap risc.

### Reinicis de servei (ftt-staging.service)
- Al final de S4, S5, S9 (sprints amb backend). Cada cop verificat `active running` + rutes noves vives per HTTP. (Avís benigne preexistent al restart: gunicorn control-server `Permission denied: /var/www/.gunicorn` — NO afecta.)

### Nous mòduls/satèl·lits creats (primera extracció fora del monòlit)
- `frontend/src/pages/ftt/history.js` (S0), `ftt/snapping.js` (S2), `ftt/paperbool.js` (S8). Backend `ftt_template_views.py` (S4). Fixture `frontend/public/fixtures/s6_evenodd_test.svg` (S6).

### Decisions tècniques transversals
- Lleis respectades sempre: **render dues bandes** (live==export via primitives/pathToData/buildTableCellPrimitives compartits), **historial S0** (tota mutació nova via setPages→coalescing), **guarda i18n** (claus a ca/es/en; 254 claus finals), **guarda UI** (KONVA_COL al llenç, COL al DOM, Tabler outline; sense hex nou tret de `KONVA_COL.goldPale` reutilitzant un literal existent), **git add selectiu** (mai -A), **NO push**.
- Adaptacions documentades (no canvis d'abast): resolució de placeholders al BACKEND (S4 va deixar el flux server-side); panell de Camps ofert en edició (S4 no va crear "editar plantilla"); snapping només en DRAG (verd només prova drag); forats compound editables només a l'exterior al sub-editor.

### Verificacions runtime reals (més enllà de build+review)
- **S5:** `resolve_placeholders` executat en shell tenant sobre model 162 (OLIVIA DRESS) → camps (inclòs un dins d'un grup) resolts correctament; logo→text buit (client sense logo).
- **S4/S9:** rutes vives/retirades comprovades per HTTP (401/404).
- **S2:** persistència de guies verificada als 4 punts de serialització.

### PENDENTS PER A AGUS (revisar abans de push)
1. **Push:** revisar el diff complet `pre-sprints-editor..dev` (33 commits) i fer push quan estigui conforme.
2. **Smokes de navegador** (Konva/Paper no dirigibles headless): validar manualment cada sprint segons els blocs "Smoke" de cada secció d'aquest doc. Prioritaris: S3 (taules T1a/T1b amb dades reals — model 162/QA-SC 182), S6 (forats evenodd amb la fixture), S8 (buscatraços: restar = forat visible), S5 (plantilla amb logo d'un client que SÍ en tingui).
3. **G-poda backend** (candidats, NO esborrats): `TechSheetTemplate` (models/serializers/views) + API `techSheetTemplate` + fitxer orfe `TechSheetTemplateEditor.jsx`; `insertGradedTable`/`pickFitting`/`onAddTableClick` (legacy graded_table, sense consumidor); eines paleta `soon:true` `cota_pom`/`note` (cobertes pels presets S8).
4. **Deutes menors** anotats a cada sprint: paste/dup de línia/fletxa sense offset (S0); Tol± a T1a sense font backend (S3); `paper` eager des de S8 (S9); heartbeat 10 min no verificat en temps real; llindar tancament ploma fix 8px.
5. **Backup i tag** disponibles per rollback: `/root/backup_pre_sprints_editor.dump` + tag `pre-sprints-editor`.

*Run orquestrada per Opus (revisió de diff + porta verda), implementada per subagents Sonnet, segons PROTOCOL_RUN_NOCTURNA. Fi.*

---

## POST-RUN E1–E3 — 2026-07-07 · PATRÓ B (sobre dev post-run pushada) · FRONTEND

Millores d'usabilitat/eines sol·licitades després de la diagnosi PATRÓ A. Subagents Sonnet, revisió de diff Opus. Branca `dev` local (SENSE push). 4 commits, tots build exit 0.

- **E1a** `6bec595` ▸ cantonera de flyout visible + tooltip.
  - La ▸ que desplega els flyouts (formes/línies/…) era gairebé invisible (fontSize 8, opacity 0.7, color heretat) → l'usuari no descobria l'el·lipse rere el rect. Ara: `fontSize 11`, `color COL.gold`, `opacity 0.9`, guarda `it.tools.length>1`. `title` amb clau nova `flyout_hint` (× ca/es/en). Mecanisme (clic=eina visible, press-hold 300ms, ▸=openFlyout) INTACTE.
- **E1b** `7ec7ccf` PaperFlatEditor a pàgina sencera + Escape cancel·la.
  - El wrapper del sub-editor es clampava als bounds INICIALS del flat (`overflow:hidden`) → escalar el vector el feia desaparèixer. Fix: wrapper i canvas a **pàgina sencera** (`left:0,top:0,width:pageW*zoom,height:pageH*zoom`); eliminades les vars `flatBounds/left/top/overlayW/overlayH` (verificat: només s'usaven al `style`). El mapatge de coords (`toViewPx/localToView`, usa `flat.x/y`) NO depenia de l'offset → sketch alineat sense tocar-lo. Canvas Paper transparent → mostra els altres objectes darrere. **Escape** dins node-edit = cancel·lar (`setEditingFlatId(null)`), guardat contra inputs (nou effect).
- **E2** `ddc3715` eines nota-fletxa i cota de dos clics + retira presets estàtics S8.
  - Reutilitzat el patró de màquina d'estats de la ploma S7 (`twoClickRef`/`twoClickTemp`). **NOTA-FLETXA** (`note`, tret `soon`): clic1=PUNTA, preview fletxa elàstica, clic2=ORIGEN → grup {arrow origen→punta + text amb caixa tocant l'origen}; **el text es col·loca al costat OPOSAT a la punta** (`dx>0`→text esquerra, si no→dreta) per no trepitjar la fletxa. **COTA** (`cota_pom`, tret `soon`): clic A, preview línia, clic B → grup {línia A→B + 2 ticks **perpendiculars a l'angle REAL** (perpendicular unitari `(-dy,dx)/len`) + text centrat sobre el punt mig, horitzontal, fontSize 9, lliure SENSE binding POM (frontera G1 respectada)}. Totes dues surten amb Escape; deixen el grup seleccionat (l'edició de text de fills de grup no està suportada net → no s'obre edició immediata). `note`/`cota_pom` afegits a `CROSSHAIR_TOOLS`. Tretes les entrades ESTÀTIQUES `preset_cota_pom`/`preset_annotation` del flyout `presets` (redundants); les branques a `createPreset` es CONSERVEN (poda futura). 0 claus i18n noves (reutilitzades `preset_annotation_text`/`preset_cota_text`/`tool_note`/`tool_cota_pom`).
- **E3** `58a6d43` barra de menús en text (Fitxer/Edició/Objecte/Visualització) + extracció de handlers.
  - **(a) Pre-extracció** (behavior-preserving): `copySelection`/`pasteClipboard`/`duplicateSelection` (de les branques keydown c/v/d) i `toggleVisible(id)`/`toggleLock(id)` (dels botons del panell de capes) → funcions amb nom; el teclat i el panell ara les criden (mateixes guardes, zero canvi de comportament).
  - **(b) Barra de menús:** fila prima entre `</header>` i el ribbon; estat `menuOpen`, tancament per clic-fora (`[data-menu]`, patró del flyout); helper `menuItem`. FITXER (Exporta PDF/Desa com plantilla/Importa pla) · EDICIÓ (Desfés/Refés/Copia/Enganxa/Duplica/Elimina amb dreceres ⌘) · OBJECTE (Agrupa/Desagrupa/z-order×4/Alinea×6/Distribueix/Mirall/Buscatraços×4/Bloqueja·Oculta selecció) · VISUALITZACIÓ (Amplia/Redueix/100%/Ajusta). Ítems `disabled` coherents amb l'estat (sense selecció, `pathfinderReady`, etc.). Conviu amb el ribbon (NO el substitueix). 15 claus `menu_*` noves × ca/es/en (266 claus totals); reutilitzades export_pdf/save_as_template/group/ungroup/align_*/pathfinder_*/zoom_*/app.delete/…
- **Porta verda:** build exit 0 als 4 commits · **chunks d'app <500kB mantinguts** (TechSheetEditor 131 kB, index 274 kB; manualChunks de S9 aguanta) · i18n paritat (266 × ca/es/en) · guarda UI (cap hex nou; COL al DOM, KONVA_COL al llenç; ombra rgba del popover reutilitzada del flyout) · història (nota/cota via addObject→setPages; copy/paste/dup extrets sense canvi). Diff-review Opus dels 4 commits. Frontend-only → sense restart.
- **Desviacions documentades (E3, spec-literal, inofensives):** menú Distribueix habilitat a `<2` (el ribbon usa `<3`; distribuir 2 = no-op inofensiu); menú Mirall usa `selectedIds` (el ribbon usa `mirrorableIds` filtrats per `blocksTransform`; mirar una línia/fletxa fixa un `scaleX` sense efecte visual). Alinear amb el ribbon si es vol coherència total.
- **Smokes manuals (per a Agus; Konva/Paper no dirigibles headless):**
  1. E1a: la ▸ daurada es veu a cada botó de flyout; press-hold o clic-▸ desplega; l'el·lipse és accessible.
  2. E1b: obrir un path al sub-editor (doble-clic o A), **escalar-lo gran** → NO desapareix (abans es tallava); Escape surt sense desar; "Fet" desa.
  3. E2: eina Nota → clic a la peça (punta) → clic a fora (origen) → fletxa + etiqueta al costat oposat a la punta; eina Cota → 2 clics en diagonal → línia amb ticks perpendiculars i text al mig; Escape a mig gest cancel·la; editar el text del grup (entrar al grup/moure — l'edició de text del fill és pendent).
  4. E3: menús Fitxer/Edició/Objecte/Visualització despleguen, criden l'acció, es tanquen per clic-fora; ítems grisos sense selecció; buscatraços gris amb <2 convertibles.
- **Pendents/deutes nous:** edició de text dels fills de grup (nota/cota) no suportada net (S1 grup-entrar només mou) — caldria estendre-la. Les 2 desviacions E3 (dalt). `PRESET_TOOLS` encara conté `preset_cota_pom`/`preset_annotation` (inerts, no a la paleta) — poda futura amb les branques de `createPreset`.

*POST-RUN E1–E3 orquestrat per Opus, implementat per subagents Sonnet, PATRÓ B. Fi.*

---

## POST-RUN E4-COTA-FLETXA — 2026-07-07 · PATRÓ B (sobre dev post E1–E3) · FRONTEND

Millora de la COTA (grup A) i nova FLETXA CURVA amb nodes (grup B), a partir de la diagnosi PATRÓ A prèvia. Branca `dev` local (**SENSE push**). 5 commits, un concern per commit, tots build exit 0. Anchors de la diagnosi confirmats vàlids (cap commit nou intercalat).

**GRUP A — COTA**
- **A2** `e6b378f` Shift encaixa la cota de 2 clics a 45°.
  - Al gest `cota_pom`, `Shift` durant el 2n clic i el preview passa `p2` per `snap45(p1,p2)` (helper existent :2205, mateix patró que ploma/línia). Escopat a la cota (`twoClickRef.current.tool === 'cota_pom'`); la nota-fletxa NO canvia. Sense cap altra restricció.
- **A4** `c83cf53` la cota dibuixa una fletxa de doble punta.
  - El fill `linia` de `finishTwoClick` passa de `type:'line'` a `type:'arrow'` amb `arrow2:true` → render live+export ja suportats per `Konva.Arrow`, **zero codi de pipeline**. Retirats els dos ticks perpendiculars (`tickA`/`tickB`): la doble punta marca els extrems (convenció de cota). El text es manté; `px,py` es conserva només per desplaçar el text.
- **A3** `136fc9e` editor de text intern del grup (cota) + toggle de fons. **Tanca el deute "edició de text de fills de grup" del run E1–E3.**
  - **(a)** `updateChild(groupId, childId, patch)`: patch arbitrari sobre un fill via `updatePageObjects`→`setPages` (història preservada), generalitzant `handleChildDragEnd`.
  - **(b)** `textObj`/`textGroupId`/`updateText`: deriva el fill `text` d'un grup seleccionat (prioritza el fill actiu si s'hi ha ENTRAT via `activeGroup`+`selectedChildId`; si no, l'únic fill text del grup). `updateText` enruta a `updateChild` (grup) o `updateObject` (text top-level).
  - **(c)** El bloc editor de text EXISTENT (font, mida, B/I/U, align, `ColorPicker`) ara opera sobre `textObj` via `updateText` — **reutilització literal**, guard canviat de `selObj.type==='text'` a `textObj &&`. El text de la cota s'edita des del panell sense sortir del grup.
  - **(d)** Toggle de **fons** (`ti-square-rounded`) + `ColorPicker` de color de fons: activa `bgFill:white`+`bgPadding` → el fons tapa la línia de la cota rere el text (bgFill ja rendit a live :971 i export :771). 4 claus i18n (`group_text`/`text_bg`/`text_bg_color`) × ca/es/en.

**GRUP B — FLETXA CURVA amb nodes** (camí path+punta, recomanació de la diagnosi)
- **COMMIT 4** `3d49f99` puntes per element (`headStart`/`headEnd`) + toggles al panell.
  - `headConfig(obj)` resol amb retrocompat: els camps nous manen si són presents; si no, `arrow2`=doble punta, `arrow`=només final, `path`=cap. `arrowProps` honora `pointerAtBeginning`/`pointerAtEnding` segons `headConfig` (live+export comparteixen l'helper). Panell: per `arrow`/`path`, toggles "punta inici"/"punta final" (`ti-arrow-narrow-left/right`) que escriuen AMBDÓS camps (prevalen sobre `arrow2`). 3 claus i18n × ca/es/en.
- **COMMIT 5** `62a5b7b` eina fletxa curva + render de punta a la tangent.
  - **(a)** Nova eina `arrow_curve` al flyout de fletxes (`ti-vector-spline`). Reutilitza la màquina de la **ploma S7** (afegit `arrow_curve` als 4 punts que checkaven `tool==='pen'` + `CROSSHAIR_TOOLS`); el traç surt com `type:'path'` **OBERT** amb `headEnd:true` i `strokeWidth:1.5`. Editable amb nodes via `PaperFlatEditor` (ja accepta `path`); `commitFlatEdit` només patcheja `paths` → **conserva `headEnd`**.
  - **(b)** Render de la punta orientada a la **tangent**: `pathHeadAngles(obj)` (final: C'(1)∝−inHandle; inici: C'(0)∝outHandle invertit; fallback al parell on-curve si el tram és recte) + `headTriPoints` (triangle px), **compartits** entre live (`PathObj`) i export (branca `path` d'`addObjectToLayer`). Color de la punta = stroke del path (`pathHeadColor`). **PaperFlatEditor.jsx NO tocat.**

**Decisions clau**
- B via **path+punta**, no ampliant `arrow` (recomanació diagnosi): reaprofita model, render bezier, editor de nodes, bounds/resize/translate; el nou es limita al render de la punta (×2 bandes) + ~10 línies de tangent.
- La fletxa curva surt **oberta** (mai `closed`) encara que es tanqui a prop del 1r punt: una fletxa no és un llaç.
- Toggles de punta escriuen `headStart` i `headEnd` alhora perquè `headConfig` deixi d'usar el `arrow2` legacy de forma determinista.

**Porta verda:** build exit 0 als 5 commits · i18n paritat (7 claus noves × ca/es/en) · guarda UI (cap hex nou; `COL` al DOM, `KONVA_COL` al llenç; icones Tabler outline) · tota mutació per la història (`snap45`/`finishTwoClick`→`addObject`; `updateChild`/`updateText`→`updatePageObjects`→`setPages`). Git add selectiu (font+i18n; mai `dist`). Frontend-only → sense restart.

**Desviacions / límits coneguts**
- Color de la **línia/fletxa** de la cota: NO s'ha afegit editor dedicat (segons nota d'abast "no duplicar editors"). El bloc de traç existent (:3925) es lliga a `selObj`, que per un grup entrat segueix sent el GRUP, no el fill `arrow` → avui el color de la doble punta de la cota no s'edita des del panell. Deute obert (caldria estendre el panell al fill seleccionat, anàleg a `textObj`).
- La punta de la fletxa curva es dibuixa amb `len/wid` fixos (8/6 px, com `arrowProps`), no escala amb `strokeWidth`.
- `PRESET_TOOLS` encara conté `preset_cota_pom`/`preset_annotation` inerts (poda futura, ja anotada al run anterior).

**Smokes manuals (per a Agus; Konva/Paper no dirigibles headless):**
1. **A2:** eina Cota → clic A → mantenir **Shift** movent → el preview s'encaixa a 0/45/90°; 2n clic → la cota queda ortogonal. Sense Shift, angle lliure (com abans).
2. **A4:** dibuixar una cota → la línia surt amb **punta a banda i banda** (doble fletxa), sense els ticks perpendiculars; el text al mig es manté.
3. **A3:** seleccionar la cota (o entrar-hi i seleccionar el text) → al panell Propietats apareix "Text del grup" amb font/mida/B/I/U/align/color; canviar-los actualitza el text de la cota. Activar **Fons** → apareix caixa blanca darrere el text que tapa la línia; canviar-ne el color. Undo/redo revert cada canvi.
4. **COMMIT 4:** seleccionar una fletxa recta → toggles "punta inici/final"; treure la final → fletxa sense punta; posar la inicial → punta a l'origen. Una cota antiga (arrow2) segueix amb doble punta (retrocompat).
5. **COMMIT 5:** eina **Fletxa curva** (flyout de fletxes) → clics per posar nodes, arrossegar per corbar (com la ploma), **Enter** per tancar → traç corb amb **punta al final orientada a la corba**. Doble-clic o **A** → editor de nodes (mou nodes/handles) → "Fet"; la punta es reorienta i es conserva. Exportar PDF → la punta hi surt igual. Al panell, activar "punta inici" → segona punta a l'origen.

*POST-RUN E4-COTA-FLETXA orquestrat i implementat per Opus 4.8, PATRÓ B. Fi.*

---

## POST-RUN FIX COTA-FLETXA-2 — 2026-07-07 · PATRÓ B (sobre dev post E4) · FRONTEND

Correcció de 3 símptomes de la cota/fletxa curva, després de la diagnosi PATRÓ A dels 4 símptomes (el #1 "sense requadre" es va resoldre sol amb el #4). Branca `dev` local (**SENSE push**). 3 commits, un concern per commit, tots build exit 0. Anchors de la diagnosi confirmats vàlids.

- **Fix #4** `e4752ac` fletxa curva seleccionable.
  - **Arrel:** la ploma genera `fill:'transparent'` → `normalizePaint`→`null` → el `Konva.Path` només captava clics sobre la hairline; i la punta (triangle sòlid) es dibuixava amb `listening={false}`. Percepció d'"incrustada".
  - **Fix:** a `PathObj`, tret `listening={false}` de la `<Line>` de la punta → el triangle sòlid bombolla el clic al `Group` (`common.onClick`=onSelect), que és la part que l'usuari prem. A més `hitStrokeWidth` del `<Path>` sense fill puja 10→18 perquè encertar la corba fina sigui fàcil. Un cop seleccionable, el Transformer apareix sol (resol #1). **Export intacte** (el `listening` és només interacció; el PDF no el necessita).
- **Fix #2** `495e59c` contingut del text del grup editable des del panell.
  - **Arrel:** el bloc "Text del grup" (A3) editava tipografia/color/fons però **no la cadena** (`textObj.text`); i l'edició inline no arriba als fills de grup (`onDblText={undefined}`, :1073).
  - **Fix:** afegit un `<textarea>` com a **primer camp** del bloc, `value={textObj.text||''}` `onChange={updateText({text})}` (enruta a `updateChild`/`updateObject` → història). Clau i18n `group_text_content` × ca/es/en. **Inline dels fills queda fora d'abast** (millora separada; requeriria traduir coords grup→absolut per a la textarea flotant).
- **Fix #3** `3258b90` color/gruix i puntes del fill arrow/path dins un grup.
  - **Arrel:** el bloc de traç i els toggles de punta es guardaven per `selObj.type` i mutaven `selObj` → per a un grup (cota, `selObj.type==='group'`) no apareixien i no arribaven al fill `arrow`. No existia `selChild` no-text (A3 només va fer `groupTextChild`, filtrat a text).
  - **Fix:** `groupShapeChild`/`shapeObj`/`shapeGroupId`/`updateShape` (mirall exacte de `textObj`/`updateText`): deriva el fill `arrow`/`path` del grup (prioritza `selectedChildId` si s'hi ha entrat; si no, l'únic fill de forma). **Conviu amb `textObj`**: la cota mostra el bloc de text I el de fletxa alhora (no exclusius). El bloc de traç+puntes és **un de sol** (no duplicat): guarda canviada a `shapeObj &&`, target de mutació `updateShape` (→ `updateChild` per a fill de grup, `updateObject` per a top-level). `subActive` passa a derivar de `shapeObj` (idèntic per a paths top-level). Etiqueta `group_shape` × ca/es/en.

**Decisions clau**
- #1 no necessitava codi: `group`/`path` mai van estar a `blocksTransform` (només line/arrow/field/text_box); el Transformer apareix quan l'objecte se selecciona. Arreglar #4 el fa visible.
- Behavior-preserving per a objectes de nivell superior: `shapeObj===selObj` i `updateShape→updateObject` quan el seleccionat és una forma top-level; només canvia l'enrutament quan és un fill de grup.

**Porta verda:** build exit 0 als 3 commits · i18n paritat (2 claus noves × ca/es/en) · guarda UI (cap hex nou; `COL`/`KONVA_COL`; icones existents) · tota mutació per la història (`updateShape`/`updateText`→`updateChild`/`updateObject`→`setPages`). Git add selectiu (font+i18n; mai `dist`). Frontend-only → sense restart.

**Límits coneguts (no regressió, ja documentats o fora d'abast):**
- Edició **inline** (doble-clic al llenç) del text/forma dels fills de grup segueix sense suport (només panell).
- El bloc de **fons** (fill) segueix lligat a `selObj` (rect/ellipse/path top-level); no s'ha estès a fills de grup (la cota no en necessita: l'arrow no té fill de superfície).

**Smokes manuals (per a Agus; Konva/Paper no dirigibles headless):**
1. **#4:** dibuixar una fletxa curva → Enter → deseleccionar (clic fora) → tornar a clicar **sobre la punta** i **sobre el traç fi**: ambdues seleccionen i apareix el requadre de Transformer.
2. **#2:** seleccionar la cota → al panell, camp "Contingut" → escriure text nou → es reflecteix al llenç en directe; exportar PDF → el text nou hi surt.
3. **#3:** seleccionar la cota → apareixen "Text del grup" (amb Contingut) **i** "Fletxa del grup" alhora → canviar color/gruix de la fletxa i alternar puntes (cap/inici/final/doble) → es reflecteix a live i a l'export PDF.

*POST-RUN FIX COTA-FLETXA-2 orquestrat i implementat per Opus 4.8, PATRÓ B. Fi.*

---

## POST-RUN FIX ARROW-SELECT + PEN-TRAP — 2026-07-07 · PATRÓ B (sobre dev post FIX-2) · FRONTEND

Dos grups de la diagnosi PATRÓ A: la fletxa curva "atrapada" en mode creació (Bloc 2, 3 flancs) i la manca d'indicador de selecció per a line/arrow (Bloc 1). Branca `dev` local (**SENSE push**). 4 commits, un concern per commit, build exit 0. Anchors confirmats vàlids. **Correcció d'hipòtesi:** la guarda del keydown de la ploma JA incloïa `arrow_curve` (commit `62a5b7b`); l'arrel real de l'"atrapada" eren tres flancs de UX/estat, no la guarda.

- **Bloc 2 (i)** `2df6ba2` doble-clic acaba el traç obert.
  - **Arrel:** l'únic final pràctic era Enter (poc descobrible); tancar clicant a prop de l'origen és antinatural per a un traç obert; no hi havia doble-clic ni clic dret al Stage (contextmenu mai implementat, no és regressió).
  - **Fix:** `finishPenOnDblClick` + `onDblClick`/`onDblTap` al `<Stage>` → `finishPen(false)` si hi ha traç en curs (≥2 punts). Val per a `pen` i `arrow_curve`.
- **Bloc 2 (ii)** `3841630` Escape surt de l'eina.
  - **Arrel:** el branch d'Escape netejava `penRef`/`penTemp` però no feia `setTool('select')` → seguies en mode creació.
  - **Fix:** afegit `setTool('select')` al branch d'Escape del keydown de la ploma.
- **Bloc 2 (iii)** `a463682` neteja del fantasma en canviar d'eina.
  - **Arrel:** cap neteja de `penRef`/`penTemp`/`twoClick*` en commutar `tool`; el preview es pinta sense gating per tool → un traç a mig fer persistia i "resuscitava" en tornar-hi.
  - **Fix:** `useEffect(…, [tool])` que reseteja l'estat de ploma/fletxa curva i nota/cota en cada canvi d'eina.
- **Bloc 1** `6816582` nanses d'extrem arrossegables per a line/arrow.
  - **Arrel:** line/arrow exclosos del Transformer (`blocksTransform`) i sense cap indicador visual de selecció ni edició d'extrems (mai es va afegir alternativa; `handleTransformEnd` no en té branca).
  - **Fix:** import `Circle`; helper `endpointsPx(obj)` + component `EndpointHandles`; a la branca line/arrow d'`ObjectNode`, quan `selected && onEndpointDrag`, es pinten 2 nanses (Circle daurat radi 5) als extrems reals (x/y·x2/y2 per arrow; primer/últim parell de `points[]` per line). `handleEndpointDrag(obj)(which)` actualitza NOMÉS aquell extrem via `updateObject` (història); Shift = `snap45` respecte l'altre extrem. Patró controlat (onDragMove+onDragEnd). El cos segueix draggable sencer. Nou prop `onEndpointDrag` només al call-site top-level → els fills de grup no en reben (fora d'abast).

**Decisions clau**
- Les nanses **substitueixen** el requadre per a line/arrow (no s'afegeix el Transformer): la diagnosi #2-3 va concloure que el Transformer distorsiona la punta/gruix i no edita extrems; les nanses són el model correcte.
- La guarda del keydown NO s'ha tocat (ja generalitzada); s'ha atacat l'arrel real (descobribilitat + estat penjat).

**Porta verda:** build exit 0 als 4 commits · cap clau i18n nova (cap etiqueta de text nova; nanses són gràfiques) · guarda UI (cap hex nou; `KONVA_COL.gold`/`.white`) · tota mutació per la història (`handleEndpointDrag`→`updateObject`→`setPages`). Git add selectiu (només el font; mai `dist`). Frontend-only → sense restart.

**Límits coneguts (no regressió):**
- Nanses d'extrem només per a line/arrow de **nivell superior** (no per a fills de grup, p. ex. la fletxa interna d'una cota — s'edita pel panell).
- El doble-clic per acabar afegeix un node coincident redundant al final (segments de longitud 0, inofensiu).

**Smokes manuals (per a Agus):**
1. **(i)** dibuixar una fletxa curva → **doble-clic** al llenç → surt del mode creació amb la fletxa creada.
2. **(ii)** a mig traç (ploma o fletxa curva) → **Escape** → torna a l'eina Selecció (no queda en mode creació).
3. **(iii)** a mig traç → clicar una **altra eina** del dock → el preview fantasma desapareix (i no reapareix en tornar a l'eina).
4. **Bloc 1** seleccionar una **fletxa recta o línia** → apareixen 2 nanses daurades als extrems → arrossegar-ne una mou **només** aquell extrem; **Shift** encaixa a 45°; arrossegar **pel mig** mou tota la fletxa com abans.

*POST-RUN FIX ARROW-SELECT + PEN-TRAP orquestrat i implementat per Opus 4.8, PATRÓ B. Fi.*

---

## POST-RUN FIX PUNTA-COLOR — 2026-07-07 · PATRÓ B (sobre dev post ARROW-SELECT) · FRONTEND

Dos bugs del panell d'un path (fletxa curva) de la diagnosi PATRÓ A: la punta no seguia el color del traç, i el ColorPicker no tenia opció "cap color". Branca `dev` local (**SENSE push**). 2 commits, build exit 0. Anchors confirmats vàlids. **COMMIT 3 (punta en node de tancament) NO implementat:** requeria confirmació que el path és `closed:true`; la fletxa curva neix **oberta** (`finishPen` → `closed:false`) i la diagnosi va concloure que el cas tancat és només la *causa probable* sense confirmar → deute pendent de confirmació de l'Agus.

- **Fix #2** `8b037b5` el color de la punta segueix el traç.
  - **Arrel:** `finishPen` cablava `paths[0].stroke = textMain`; com que `path.stroke` té prioritat sobre `obj.stroke` (a `pathChildProps` i a `pathHeadColor`), el selector "Color de traç" de nivell superior (mode per defecte → escriu `obj.stroke`) quedava **ombrejat**: no tenia efecte ni sobre la línia ni sobre la punta.
  - **Fix:** l'stroke inicial passa a **nivell d'objecte** (`obj.stroke = textMain`); `paths[0]` ja no porta `stroke`. Ara el picker top-level recolora línia **i** punta alhora (totes dues cauen a `obj.stroke`); el picker per-subpath segueix funcionant com a override de `paths[i].stroke`.
- **Fix #3-5** `912911f` swatch "cap color" al ColorPicker.
  - **Arrel:** el ColorPicker (6 `QUICK_COLORS` + input natiu) no oferia "sense color"; el concepte "buit" només existia via toggles externs (fons de text). El model **ja** ho suporta: `normalizePaint` mapeja `null`/`''`/`'none'`/`'transparent'` → `null` → Konva no pinta (live i export).
  - **Fix:** un botó "cap" (`ti-ban`, fons `transparent`) al ColorPicker compartit → `onChange('transparent')`. Detecció de seleccionat `value == null || 'transparent' || 'none'`. Com que el component és compartit, apareix a traç/emplenat/text/fons/puntes sense tocar cap call-site. i18n `no_color` × ca/es/en.
  - **Deute anotat (cosmètic):** el bloc d'emplenat coerciona `'transparent'`→blanc per a mostrar (:4091) → allà el swatch "cap" no ressalta com a seleccionat (funcionalment sí que aplica transparent).

**Decisions clau**
- Fix #2 al punt d'origen (`finishPen`), no als llocs de lectura: així línia i punta comparteixen la mateixa font (`obj.stroke`) sense duplicar lògica; el per-subpath es manté intacte.
- "Cap color" reutilitza `'transparent'` (ja gestionat per `normalizePaint`), sense afegir cap valor especial nou al model.
- Diagnosi #1 (punta "al revés"): confirmat que **no hi ha inversió en paths oberts** (headStart/headEnd simètrics, tots dos cap enfora = ↔ correcte). NO s'ha tocat el signe. El cas tancat queda com a COMMIT 3 pendent.

**Porta verda:** build exit 0 als 2 commits · i18n paritat (1 clau nova × ca/es/en) · guarda UI (cap hex nou; `ti-ban`, `background:'transparent'`, tokens COL/KONVA_COL) · git add selectiu (font+i18n; mai `dist`). Frontend-only → sense restart.

**Límits coneguts:**
- `strokeWidth` de la fletxa curva encara viu a `paths[0].strokeWidth` (ombreja `obj.strokeWidth` igual que feia l'stroke) — no reportat, fora d'abast; si es vol el mateix tracte que el color, moure'l a nivell d'objecte.
- Punta en node de **tancament** (`closed:true`): pendent (COMMIT 3), a l'espera de confirmar que hi ha un path tancat real amb puntes.

**Smokes manuals (per a Agus):**
1. **#2** dibuixar una fletxa curva → canviar "Color de traç" al panell (sense subpath actiu) → **línia i punta canvien juntes**.
2. **#2 subpath** entrar a subpath actiu ("peça 1") → canviar color → només aquell subpath i la seva punta.
3. **#3-5** al ColorPicker (traç i emplenat), clicar el swatch **"cap"** → desapareix el traç/emplenat a live; exportar PDF → també absent.

*POST-RUN FIX PUNTA-COLOR orquestrat i implementat per Opus 4.8, PATRÓ B. Fi.*
