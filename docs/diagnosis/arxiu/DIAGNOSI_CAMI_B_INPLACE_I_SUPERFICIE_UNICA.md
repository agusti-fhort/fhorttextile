> ⚠️ SUPERADA 2026-07-21 — implementada pel sprint Patró B end-to-end (fases 1-7, commits
> 73babdb→254eaa8). Consulta només com a històric.

# DIAGNOSI — Camí B: edició in-place i superfície d'eines única

Data: 2026-07-21 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` (HEAD `b40ef43`)

**Abast.** Dimensionar (no implementar) la decisió d'Agus: jubilar el "sub-editor modal" a favor
d'edició IN-PLACE al llenç, i fusionar les TRES superfícies d'eines actuals en una arquitectura
única amb menú/pestanya "Editar". S'hi afegeix el bug/mancança de la capçalera ("desvincular" no
deixa editar els fills).

**Convenció.** Cada afirmació porta `fitxer:línia`. `"NO EXISTEIX"` = confirmat absent al codi,
no especulat. Les propostes van al final, marcades `💡 PROPOSTA (a validar)`, separades dels fets.
Els camins són relatius a `/var/www/ftt-staging/`.

---

## Resum executiu

1. **El sub-editor modal NO EXISTEIX.** `PaperFlatEditor` ja és in-place: es munta com a **germà del
   `<Stage>`** dins el mateix contenidor de pàgina (`frontend/src/pages/TechSheetEditor.jsx:4614-4631`,
   dins el div de `:4515`), amb arrel `position:absolute; left:0; top:0; width:pageW*zoom;
   height:pageH*zoom; zIndex:20` (`frontend/src/pages/PaperFlatEditor.jsx:855-857`). **No hi ha
   overlay, ni títol, ni diàleg, ni barra d'eines pròpia** — tot el JSX del component són dues
   línies: un div i un canvas (`PaperFlatEditor.jsx:851-859`). El brief parteix d'una premissa
   que el codi desmenteix: **la feina no és "treure el modal", és treure les QUATRE separacions
   que queden** (§P5.5, veredicte P5).

2. **Les quatre separacions reals** que fan que "sembli" un modal:
   (a) un **segon canvas amb PaperScope propi** (`PaperFlatEditor.jsx:59-65`);
   (b) l'objecte editat **s'esborra del Konva** mentre dura la sessió (`TechSheetEditor.jsx:4527`);
   (c) una **història d'undo paral·lela** que mor al tancar (`PaperFlatEditor.jsx:238-266`);
   (d) el guard `nodeMode` que **apaga tota la UI d'objecte** (`TechSheetEditor.jsx:3223`, `:4152`,
   `:4111-4133`).

3. **La sincronització Konva↔Paper ja està resolta i és aritmèticament trivial.** No cal cap
   matriu de vista: el pan **no mou el Stage** (és `scrollLeft/scrollTop` d'un div,
   `TechSheetEditor.jsx:3097-3113`) i el canvas de Paper, per ser germà del Stage, **es mou sol**.
   Els únics valors compartits són `pageW`, `pageH`, `zoom`, `toPx` (`TechSheetEditor.jsx:1795-1796`,
   `:1771`, `:124`). El PoC `PaperKonvaPoc.jsx` és precedent de **coexistència de píxels i
   arbitratge de punter** (`PaperKonvaPoc.jsx:436`), **no** de sincronia de coordenades (§P1.5).

4. **La duplicació no és de botons, és de MOTOR.** Alinear, distribuir, mirall, escalar, rotar,
   z-ordre i booleanes tenen **dues implementacions independents que no comparteixen ni una línia**:
   la d'objectes al model (`TechSheetEditor.jsx:2001`, `:2055`, `:2078`, `:2121`, `:2145`, `:3745`)
   i la de formes al canvas (`PaperFlatEditor.jsx:342-433` + `frontend/src/pages/ftt/paperOps.js`).
   A més cada acció apareix a **3 o 4 superfícies** (§P3.4, §P3.6). El total inventariat: **7
   superfícies competint per les mateixes accions**, no 3.

5. **La capçalera no té fills que es puguin editar — no existeixen com a dades.** És **un objecte
   atòmic** `data_block kind:'header'` amb només `{id,type,kind,layer,locked,x,y,width,height,config}`
   (`TechSheetEditor.jsx:3536-3539`); els texts, línies i colors es **generen per codi a cada render**
   (`buildMasterHeaderPrimitives`, `TechSheetEditor.jsx:712-772`) i van tots amb `listening={false}`
   (`TechSheetEditor.jsx:846`, `:848`). El botó "desvincular" **només canvia tres flags**
   (`layer`, `locked`, `detached` — `TechSheetEditor.jsx:3569-3577`). No és un bug de permisos: és
   que **no hi ha res a seleccionar a dins** (§P4).

6. **Render i export no es toquen.** El live (`PathObj`, `TechSheetEditor.jsx:1393-1420`) i el PDF
   (`addObjectToLayer`, `:1204-1220`) criden **literalment la mateixa funció** `pathChildProps`
   (`:1064-1076`) sobre `segmentsToData` (`:998-1023`). L'únic contracte de l'edició amb el render
   és escriure `obj.paths[]`. **CONFIRMAT: canviar la superfície d'edició no afecta res del render
   ni de l'export** (§P6).

---

## BLOC P1 — Anatomia del pont Konva↔Paper

### P1.1 — Com s'obre la sessió

L'estat que la governa és **un sol id**, no un objecte: `TechSheetEditor.jsx:1763`
`const [editingFlatId, setEditingFlatId] = useState(null)`.

El `flat` **es deriva, no es construeix** — `TechSheetEditor.jsx:3737`:
`curObjs.find(o => o.id === editingFlatId && ['sketch_svg','path'].includes(o.type))`. És
**literalment l'objecte del model, per referència**. NO EXISTEIX cap capa de normalització entre
model i sub-editor.

Cinc portes d'entrada, totes cap a `startVectorEdit` o equivalent:
`TechSheetEditor.jsx:3162` (crear path de mostra) · `:3186`/`:3196` (import SVG) · `:3207-3212`
(`editSelectedFlat`, botó del panell `:5031`) · `:3213-3219` (`startVectorEdit`, doble-clic `:4543`
i eina `node` `:4535-4536`) · `:3259-3277` (tecla `A`).

Sortides: Escape (`:2568-2580`), botó "Cancel·lar" (`:4056`), botó "Fet" (`:4052` →
`paperFlatRef.current?.commit()`).

Props (`TechSheetEditor.jsx:4614-4631`, component `lazy` a `:18`):

| prop | valor | origen |
|---|---|---|
| `flat` | `editingFlat` | `:3737` (objecte del model per referència) |
| `pageW`/`pageH` | `Math.round(fmt.w * MM_TO_PX)` | `:1795-1796` |
| `zoom` | state | `:1771`, clamp `:1898-1900` |
| `toPx` | `mm => mm * 2.4` | `:124` (`MM_TO_PX` a `:42`) |
| `nodeTool` | state | `:1766`, reset a `'shape'` a `:3226` |
| `onNodeState` | `setNodeSel` | `:1767` |
| `onCommit` | `commitFlatEdit` | `:3292-3316` |
| `onSplitObject` | `handleSplitObject` | `:3280-3291` |
| `onCanCommitChange` | `setFlatCanCommit` | `:1768` |
| `onEnterDirect` | `() => setNodeTool('select')` | inline `:4628` |

### P1.2 — Sistemes de coordenades

Tres espais, cadena trivial (cap matriu de vista):

1. **mm de model** — `pages[].objects[]`: `obj.x/y`, `segments[].{x,y,inX,inY,outX,outY}`
   (`ftt/paperOps.js:5`).
2. **px de pàgina** — `mm * MM_TO_PX` amb `MM_TO_PX = 2.4` (`TechSheetEditor.jsx:42`), `toPx` `:124`,
   `toMm` `:125`.
3. **px de view** — `px de pàgina × zoom`.

**Konva**: rep px de pàgina i el zoom l'aplica el Stage — `TechSheetEditor.jsx:4520`
`<Stage width={pageW*zoom} height={pageH*zoom} scaleX={zoom} scaleY={zoom}>` (comentari a
`:4518-4519`: "el zoom el fa Konva… ja no s'escala el bitmap per CSS").

**Paper**: el zoom es **cou dins la geometria**, no a la vista — `PaperFlatEditor.jsx:435`
`toViewPx = mm => toPx(mm) * zoomRef.current`; `localToView`/`handleToView` a `:445-452`; segments
afegits ja transformats a `:467`. **Paper no aplica cap `view.zoom` ni `view.matrix`** (identitat).
Tot el que passa dins de Paper, incloses les crides a `paperOps`, és en **px de view**
(`PaperFlatEditor.jsx:772-779`).

Canvi de zoom en calent: re-dimensiona canvas + `view.viewSize` i **re-escala la capa viva** amb
`sketchLayer.scale(ratio, Point(0,0))` (`PaperFlatEditor.jsx:786-801`) — muta geometria, no és una
matriu reversible.

**Retorn (`onCommit`)**, dos formats:
- `type:'path'` → `commit()` (`PaperFlatEditor.jsx:806-842`) inverteix la cadena amb `fromViewMm`
  (`:813`) i desfà rotació/escala (`:814-822`); torna `{paths}` (`:841`) conservant l'entrada
  d'origen i sobreescrivint només geometria i pintura (`:839`).
- `sketch_svg` → `exportSVG({asString:true, bounds:'content'})` → `onCommit(svg)` (`:844-845`).

Reintegració: `commitFlatEdit` (`TechSheetEditor.jsx:3292-3316`) fa **un sol** `updateObject`
(`:3295` o `:3313`) → `updatePageObjects` → `setPages` → entra a la història del document
(`ftt/history.js:13`).

### P1.3 — Transformacions d'objecte

S'apliquen a l'entrada i **es desfan simètricament** a la sortida; res es congela ni es perd:
`PaperFlatEditor.jsx:436-452` (escala primer, rotació després; l'offset `flat.x/y` només al punt,
`:447`, no als handles, `:451`) i la inversa a `:810-822`. `flat.rotation/scaleX/scaleY`
**mai s'escriuen** des del sub-editor.

**Skew: NO EXISTEIX** a cap punt del model ni del render. El `Transformer`
(`TechSheetEditor.jsx:4595`) només ofereix rotació i escala.

**Asimetria real**: la branca `sketch_svg` **ignora** `rotation`/`scaleX`/`scaleY`
(`PaperFlatEditor.jsx:479-483`) i el commit hi retorna una cadena, no geometria (`:844`).

`ftt/paperbool.js:53-100` (`objectToPaperPath`) **sí** aplica rotació i escala (`:63-67`, `:76-80`,
`:90-95`), amb origen `(obj.x, obj.y)`, **no** el centre de bounds.

### P1.4 — Pan/zoom del Stage

- **Zoom**: state React (`:1771`), sempre via `setZoomClamped` (`:1898-1900`); wheel només amb
  Ctrl/Cmd (`onViewportWheel`, `:3091-3096`, enganxat al viewport `:4507`, **no** al Stage).
- **Pan: NO és del Stage.** `stage.x()/y()` **no s'usen enlloc**. És scroll d'un div `overflow:auto`
  (`:3097-3113`, `:4509`), actiu amb eina `pan` o barra espaiadora.
- Refs: `stageRef` `:1798` (només per trobar nodes per id `:2716` i pel Transformer, **mai** per
  moure la vista), `viewportRef` `:1800`, `wrapRef` `:1801`.

**Conseqüència directa per al Camí B**: per sincronitzar un canvas superposat només calen
`pageW`, `pageH`, `zoom`, `toPx`. **No calen offsets de pan.** És exactament el que ja fa
`PaperFlatEditor.jsx:855-857`.

### P1.5 — Inventari de `PaperKonvaPoc.jsx`

- Ruta `/disseny/poc-paper` (`frontend/src/App.jsx:341`, lazy `:54`). **Cap enllaç de navegació hi
  apunta** (grep de `poc-paper` → només `App.jsx`); només accessible per URL.
- **Sí es compila i s'envia al build**: `frontend/dist/assets/PaperKonvaPoc-BJ8cNQup.js` (11 261 B).
  i18n complet ca/en/es (`i18n/ca.json:3294` `"poc_paper"`).
- Git: darrers commits `3f6dcef`, `869a8fd`, `5e85d6f` ("Documenta coexistencia Paper Konva").
  **Cap commit posterior** — és anterior a tota la línia F/G del sub-editor.

Què demostra (llegit sencer, 486 línies):
1. **Coexistència física**: `<Stage width={760} height={360}>` (`:414-426`) i, germà seu, un
   `<canvas>` `position:absolute; inset:0` (`:427-439`) dins un contenidor `position:relative`
   (`:402-413`).
2. **Arbitratge d'entrada per `pointerEvents`**: `pointerEvents: paperActive ? 'auto' : 'none'`
   (`:436`), commutat per un botó (`:371`), amb un comptador `konvaClicks` (`:80`, `:417`) com a
   prova instrumentada.
3. Edició de nodes amb Paper: `importSVG` (`:106`), `refreshHandles` (`:116-150`), `scope.Tool`
   (`:181-219`), modes select/add/delete (`:186-192`).
4. Mesura de rendiment amb el cas real `/CALLIE.svg` (`:299-307`) i panell de mètriques (`:445-464`).
5. Round-trip SVG amb validació per `DOMParser` (`:235-252`).

**Com sincronitza: NO SINCRONITZA RES.** Konva i Paper hi són dos mons que només comparteixen
píxels: el Konva dibuixa un decorat estàtic amb el seu propi `MM_TO_PX = 96/25.4` (`:6-8`) — **que
no és el `2.4` de l'editor real** (`TechSheetEditor.jsx:42`) — i el Paper centra el seu SVG a
`scope.view.center` (`:107`). **No hi ha zoom, ni pan, ni pàgina, ni cap valor compartit.**

**Veredicte del PoC**: precedent vàlid per a **coexistència espacial i arbitratge de punter**; **no**
per a sincronia de coordenades (això ho fa, i millor, `PaperFlatEditor.jsx:435-452`). Estat: **viu al
build, orfe de navegació, no evolucionat des de la seva diagnosi**.

### P1.6 — `paperOps.js` / `paperbool.js`: puresa

17 exports a `ftt/paperOps.js`; **11 de 17 són manipulació pura d'arrays sense Paper**
(`removeNode:32`, `toCorner:41`, `mirrorHandle:72`, `translateSubpath:78`, `mirrorSubpath:86`,
`scaleSubpath:96`, `rotateSubpath:106`, `closeSegments:139`, `openAtNode:145`, `splitAtNode:155`,
`isStraightSegment:168`, `moveSegment:179`, `deleteSegment:197`). Les 4 que necessiten bezier usen
`withPaperScope` (`:50`, `:61`, `:123`, `:213`).

- **Únic import**: `withPaperScope` de `./paperbool` (`paperOps.js:6`). Cap React, cap JSX, cap
  `document`, `window` ni `canvas`.
- **L'única dependència de DOM de tota la cadena** és `paperbool.js:15`:
  `scope.setup(document.createElement('canvas'))` — un canvas **offscreen mai adjuntat al DOM**
  (documentat a `:9-10`), destruït al `finally` (`:17-23`).
- **NO EXISTEIX** cap ús de `paper.setup()` global, `paper.install(window)` ni `PaperScope.get()`.
- **Ja hi ha dos consumidors independents**: `PaperFlatEditor.jsx:3` (paperOps) i
  `TechSheetEditor.jsx:16` (`booleanOp` de paperbool, per al pathfinder d'objectes) — la prova que
  la capa és reutilitzable.

**Matís d'unitat**: `paperOps` opera en **px de view** quan el crida `PaperFlatEditor`
(`:773-779`) i en **mm** quan el crida `TechSheetEditor`. Les funcions són invariants d'escala, però
**el cridador ha de decidir l'espai**.

**Veredicte P1: llest.** El pont ja existeix, és exacte i simètric, i no requereix cap valor que no
estigui ja disponible. El PoC és història, no plataforma.

---

## BLOC P2 — Conflictes d'interacció al llenç compartit

### P2.1 — Listeners actuals

**Nivell viewport (DOM)**: `onWheel` (`:4507`, només Ctrl/Cmd `:3091-3096`), `onScroll={syncRuler}`
(`:4507`), `onMouseDown/Move/Up/Leave` de pan (`:4508`, `:3099-3113`), `onDrop`/`onDragOver`
(`:4516`, `:3128`), i les regles `startGuideCreate('x'|'y')` (`:4498`, `:4503`) que **registren
`mousemove`/`mouseup` a `window`** durant el gest (`:1964-1965`).

**Nivell Stage**: només **quatre** — `onMouseDown` (`:4521` → `:2884`), `onMouseMove` (`:4521` →
`:2949`), `onMouseUp` (`:4521` → `:3001`), `onDblClick/onDblTap` (`:4522` → `finishPenOnDblClick`
`:2855`). Els tres primers surten d'hora amb `if (editingFlatId) return` (`:2885`, `:2950`, `:3002`);
**el doble-clic NO té aquest guard**.
**NO EXISTEIX** cap `onWheel`, `onContextMenu`, `onDragStart/Move/End` ni `onTouch*` al `<Stage>` ni
al `<Layer>` (`:4525` no té cap handler).

**Nivell node fill** (`common`, `:1422-1432`): `onClick/onTap` només si `selectable` (`:1426-1427`,
`selectable` definit a `:4533`), `onDragStart/Move/End` (`:1428-1430` → `:2722`, `:2730`, `:2742`),
`onTransformEnd` (`:1431` → `:2778`). Per tipus: `onContextMenu` del header (`:1438`, `:4531`),
doble-clic de text (`:1475`, `:1482`), `PathObj` amb doble-clic al Group (`:1396`) **i** `subClick`
per `<Path>` fill amb `e.cancelBubble = true` (`:1403`, `:1408`), `EndpointHandles` (`:1383-1391`),
grups amb fills recursius només si `entered` (`:1517`, `:1525-1528`), guies (`:4586-4587`).
Tots els previews porten `listening={false}` (`:4555-4580`, `:4592-4593`).

**Nivell Paper**: NO EXISTEIX cap listener DOM propi. Són handlers d'un `scope.Tool()`
(`PaperFlatEditor.jsx:594`): `onMouseDown` (`:595-677`), `onMouseDrag` (`:679-720`), `onMouseMove`
(`:723-756`), `onMouseUp` (`:758-769`). El teclat viu **al pare** (`:781-782`).

### P2.2 — Selecció rectangular

**Objectes**: estat `marquee` (`:1852`) + `marqueeStart` (`:1853`); s'activa **només si
`tool==='select'` I `e.target === e.target.getStage()`** (`:2917-2925`); es dimensiona a `:2978-2986`
i es resol a `:3009-3031` (marc ≤3×3 px = clic simple `:3015-3018`; hit-test per `getClientRect`
`:3022-3028`; shift acumula `:3030`). Inhibidors: `editingFlatId`, `tool!=='select'`,
`spaceHeld`/pan (`:2886`), `!locked` (`:2887`), target ≠ Stage.

**Nodes**: marquesina pròpia i independent — `marqueeRef` (`PaperFlatEditor.jsx:34`), s'inicia només
si `active==='select'` i cap hit (`:676`), es resol seleccionant **segments** (`:759-766`). En mode
`shape` no n'hi ha (`return` a `:628`).

### P2.3 — Transformer

Instanciat un sol cop (`:4595-4599`, ref `trRef` `:1799`), dins l'única `<Layer>`. Ancoratge a
`:2458-2478`: `tr.nodes(nodes)` (`:2475`) amb filtre `selectedIds` ∩ `layer!=='template'` ∩
`!blocksTransform(o)` ∩ `!o.locked` ∩ `visible!==false` (`:2470-2474`).
`blocksTransform` (`:1151-1153`) exclou `line`, `arrow`, `field` i `text` amb `bgFill`.
**Guard de mode node**: `if (editingFlatId) { tr.nodes([]); return }` (`:2463-2467`).

`transformend` → `handleTransformEnd` (`:2778-2811`), penjat de cada node (`:1431`), no del
Transformer: **reseteja `node.scaleX(1)/scaleY(1)`** (`:2785`) i escriu segons tipus. Per a `group`
(`:2786`) i **`path` (`:2790`) l'escala queda ABSORBIDA al model** com a `scaleX/scaleY` — és
exactament l'escala que `PaperFlatEditor` ha de desfer a mà (`:441-452`, `:810-821`).

### P2.4 — Drag d'objectes

Un únic punt: `draggable={locked && tool==='select' && !panActive && o.layer!=='template' &&
!o.locked && activeGroup!==o.id}` (`:4534` → `common.draggable` `:1425`).
**Cap guard per `editingFlatId`**: el que treu els objectes de circulació és (a) que l'objecte en
edició no es renderitza (`:4527`) i (b) que el canvas de Paper el tapa (`zIndex:20`).
Fills de grup: `draggable={!!entered}` (`:1524`). Magnetisme calculat un cop a `handleDragStart`
(`:2722-2728`), aplicat per frame a `handleDragMove` i **desactivat amb Ctrl/Cmd** (`:2732`).

### P2.5 — Teclat (tot a `window`, cap al canvas)

Dotze `useEffect` amb `addEventListener('keydown')` al pare: `:2506`, `:2549`, `:2563`, `:2577`,
`:2597`, `:2624`, `:2650`, `:2661`, `:2671`, `:2708`, `:3256`, `:3274`. Zero al sub-editor
(documentat a `PaperFlatEditor.jsx:781-782`).

Col·lisions **ja resoltes per exclusió mútua `editingFlatId`**: `A` (`:3252` vs `:3267`),
`V` (`:2591` vs `:3252`), Delete/Backspace (`:2488` vs `:3236`), fletxes (`:2698` vs `:3246`),
`⌘Z` (`:2521` vs `:3240`), Escape (`:2557` vs `:2571`).

Tecles **SENSE** exclusió (es disparen també amb el sub-editor obert): `Shift` (`:2668`, sense cap
guard), `Space` (`:2659` — canvia `panActive` i el cursor), bloc de la ploma (`:2604`, inert si
`penRef` és null), bloc de nota/cota (`:2639`, inert si `twoClickRef` és null).

Anomalia: `TOOL_SHORTCUT` (`:109`) declara `node:'A'`, però el mapa de dreceres d'eina (`:2591`)
**no conté `a`**; la tecla la consumeix el listener d'obrir l'editor (`:3267`). El tooltip de la
paleta (`:4436`) anuncia una drecera que no fixa aquella eina.

### P2.6 — Modes: dues màquines d'estats, no una

1. **`tool`** (`:1738`) — paleta `PALETTE` (`:3850-3894`): `select`, `node`, `subpath`, `draw`, `pen`,
   `rect`, `rect_round`, `ellipse`, `polygon`, `line`, `line_dot`, `arrow`, `arrow2`, `arrow_curve`,
   `text`, `text_box`, `cota_pom`, `note`, `preset_*`, `pan`. Auto-retorn a `'select'` després de
   crear (`:2851`, `:2904`, `:2937`, `:2941`, `:3077`) i en entrar al sub-editor (`:3185`, `:3210`,
   `:3216`).
   - **`tool==='node'` NO és un mode d'edició: és una porta que obre el sub-editor** (`:4535-4536`).
   - **`tool==='subpath'` sí que és selecció fina in-place al Stage de Konva** (`:1403`, `:4550-4551`
     → estat `activeSubpath` `:1789`). **És l'únic gest de granularitat sub-objecte que ja viu al
     Konva.**
2. **`editingFlatId` / `nodeTool` / `nodeSel`** — `editingFlatId` (`:1763`) és la porta;
   `nodeMode = !!editingFlatId` (`:3223`) apaga tota la UI d'objecte (`:4111-4133`, `:4152`, `:5050`).
   `nodeTool` (`:1766`): `shape` | `select` | `add` | `remove` | `convert` | `scissors`
   (`:5318-5327`). `nodeSel` (`:1767`) puja per `onNodeState` amb
   `{mode, shapeCount, selCount, seg, fill, stroke, strokeWidth}` (`PaperFlatEditor.jsx:182-195`).
   Els DOS MODES viuen al `onMouseDown` de Paper: branca `shape` a `:604-629`, selecció directa a
   `:631-677`.

Estats auxiliars: `activeGroup`/`selectedChildId` (`:1787-1788`), `activeSubpath` (`:1789`),
`editingText` (`:1762`), `spaceHeld`/`panning` (`:1769-1770`).

### P2.7 — API imperativa

`useImperativeHandle` (`PaperFlatEditor.jsx:848`) exposa exactament **dos** membres: `commit`
(`:803-846`) i `run(name, ...args)` → `opsRef.current` (`:550-592`, **19 accions**): `close`, `open`,
`split`, `removeSelection`, `booleanShapes`, `alignShapes`, `distributeShapes`, `mirrorShapes`,
`scaleShapes`, `rotateShapes`, `reorderShape`, `setFill`, `setStroke`, `setStrokeWidth`, `selectAll`,
`nudge`, `undo`, `redo`. Diverses són sensibles al mode via `isShapeMode()` (`:566-569`, `:572-588`,
`:533-547`, `:212-223`). Consumidors al pare: `runNode` (`:3221`), botó Fet (`:4052`), tota la barra
contextual (`:4301-4380`), teclat (`:3236`, `:3240`, `:3241`, `:3249`).

### P2.8 — Punts de col·lisió si l'edició fos in-place sobre el Stage

Avui les superfícies estan separades per **tres barreres**: (a) `zIndex:20` del canvas de Paper
(`PaperFlatEditor.jsx:855`); (b) l'objecte editat no es renderitza (`TechSheetEditor.jsx:4527`);
(c) els tres handlers del Stage surten amb `editingFlatId`. Sense aquestes barreres, aquests parells
competirien pel mateix event i target:

| # | Event | Handler d'objecte | Handler de node |
|---|---|---|---|
| 1 | clic sobre `<Path>` fill | `subClick` `:1408` amb `cancelBubble` `:1403` vs `common.onClick` `:1426` → `:4535` | (ja hi ha dos consumidors del mateix píxel avui) |
| 2 | hit sobre traç | `hitStrokeWidth={fill ? 10 : 18}` `:1408` | `tolerance: 8` de Paper (`PaperFlatEditor.jsx:605`, `:656`, `:673`, `:742`) |
| 3 | mousedown en buit, `tool==='select'` | marquee d'objectes `:2917-2925` | marquesina de nodes `PaperFlatEditor.jsx:676` |
| 4 | drag sobre selecció | `draggable` `:4534` + magnetisme `:2730` | `dragRef={kind:'shape'}` `PaperFlatEditor.jsx:623`, `:689-697` |
| 5 | Alt+drag | **cap lectura d'`altKey`** als drags d'objecte (`:2730-2757`) | duplicar-en-arrossegar `PaperFlatEditor.jsx:623`, `:690-694` |
| 6 | doble-clic sobre path | `onDblVector` `:1396` → obre el mode `:4543` | doble-clic → entrar a directa `PaperFlatEditor.jsx:611-616` |
| 7 | doble-clic al Stage | `finishPenOnDblClick` `:4522` (**sense guard `editingFlatId`**) | ídem `:611` |
| 8 | selecció | Transformer `:2470-2475` (buidat avui a `:2463-2467`); `transformend` absorbeix escala al `path` `:2790-2792` | `PaperFlatEditor` la desfà a `:441-452`, `:810-821` |
| 9 | nanses | `EndpointHandles` = `Circle draggable` amb `cancelBubble` (`:1383-1391`) | àncores = `Path.Rectangle` + hit-rect 18px (`PaperFlatEditor.jsx:107-112`) |
| 10 | zoom/pan | wheel al viewport `:4507`; `Space` sense guard `:2659` | `dragRef` no consulta `spaceHeld` |
| 11 | guies | `startGuideCreate` registra a `window` (`:1964-1965`) — **per damunt de tot** | — |

**La selecció està triplicada i no comparteix estat**: `selectedIds` (`:1737`), `selectedChildId` +
`activeGroup` (`:1787-1788`), `activeSubpath` (`:1789`) al pare; `selectedShapesRef`,
`selectedSegsRef`, `selectedSegRef`, `selectedPathRef` (`PaperFlatEditor.jsx:28-31`) al fill.
**L'únic pont és el DTO de només-lectura `nodeSel`** (`:189-194` → `:4624`).

**Veredicte P2: cal una màquina d'estats de mode explícita i un arbitratge de punter.** Els 11 punts
de col·lisió són tots concentrats en 4 handlers del Stage + 4 del Tool de Paper; el problema no és el
volum sinó que **no hi ha cap contracte de qui captura què** — avui es resol per exclusió total
(`editingFlatId`), que és precisament el que el Camí B vol eliminar.

---

## BLOC P3 — Les tres superfícies d'eines (inventari per fusionar)

**Fet previ**: NO EXISTEIX cap component auxiliar de barra d'eines. Tota la UI de les tres
superfícies viu **inline dins `TechSheetEditor.jsx`**. `PaperFlatEditor.jsx:851-859` declara
explícitament "cap UI pròpia: només el canvas".

### P3.1 — Localització

| # | Superfície | Rang JSX | Condició |
|---|---|---|---|
| a | Barra contextual mode nodes | `:4277-4382` | `{editingFlatId && …}` (`:4278`) |
| a′ | Fila del ribbon en mode nodes (només Fet/Cancel·lar) | `renderNodeEditTools()` `:4049-4062`, injectada a `:4067` | `editingFlatId` |
| b | Ribbon "Organitzar" | `:4110-4134` | tab `ribbonGroup==='organize'` (`:4010-4015`) |
| c | Panell dret Propietats | `:4765-5057` (sense selecció `:4767-4778` · multi `:4779-4811` · única `:4812-5057`) | `dockTab==='properties'` + `locked` |

### P3.2/P3.3 — Enumeració i abast (resum; el detall és a la matriu §P3.6)

**a) Barra contextual (33 controls + 2 de la fila a′)**: indicador de mode (`:4281-4286`), 2 cursors
(`:4289-4293`, def. `:5319-5320`), 4 sub-eines add/remove/convert/scissors (`:4295-4299`,
`:5324-5327`), close/open/split (`:4301-4303`), 4 booleanes (`:4309-4317`, gate `shapeCount>=2`
`:4307`), 6 alinear (`:4325-4335`, gate `>=2` `:4323`), 2 distribuir (`:4336-4339`, `disabled <3`),
2 mirall (`:4347-4348`), rotar `°` (`:4349-4351`), escalar `%` (`:4352-4354`), 4 z-ordre
(`:4362-4365`), fill/stroke/strokeWidth (`:4370-4380`). Fila a′: Fet (`:4052-4055`,
`disabled={!flatCanCommit}`) i Cancel·lar (`:4056-4059`).

**b) Ribbon Organitzar (21 controls, tots d'abast OBJECTE)**: 6 alinear (`:4111-4116` →
`alignSelection` `:2121`), 2 distribuir (`:4117-4118` → `:2145`), agrupar (`:4119` → `:2090`),
desagrupar (`:4120` → `:2111`), 2 mirall (`:4121-4122` → `mirrorObjects` `:2001`), 4 z-ordre
(`:4123-4126` → `:2055`/`:2078`), eliminar (`:4127` → `:3739`), 4 booleanes (`:4130-4133` →
`applyPathfinder` `:3745` → `booleanOp` `ftt/paperbool.js:159`). Gate uniforme `nodeMode ||`.

**c) Panell Propietats (42 controls)**: multi (stroke `:4782-4788`, fill `:4789-4795`, X/Y
`:4796-4809`); única — ratio (`:4819-4822`), W/H (`:4825-4836` → `resizeObjectAxis` `:2251`), X/Y
(`:4837-4844` → `moveObjectTo` `:2185`), text (contingut `:4863-4866`, família `:4867-4871`, mida
`:4872-4875`, B/I/U `:4878-4880`, alineació `:4885-4887`, color `:4890-4892`, fons `:4894-4906`),
subpath (sortir `:4917-4920`, tancar `:4926-4927`, extreure `:4928-4929`, esborrar `:4930-4931`),
traç (`:4935-4945`), puntes (`:4954-4955`), fill (`:4962-4969`), escala `data_block` (`:4971-4976`),
taula (`:4977-5028`), **editar nodes (`:5031-5034`)**, reemplaçar SVG (`:5036-5039`), rotació
absoluta (`:5044-5047`), eliminar (`:5050-5054`), costats de polígon (`:4770-4776`).

**Fet crític de gating**: **el panell de Propietats NO està gated en mode nodes**, excepte el botó
Eliminar (`:5050`). W/H/X/Y (`:4825-4844`), rotació (`:5044`), fill (`:4962`), traç (`:4935`) i gruix
(`:4942`) **segueixen escrivint al model mentre el sub-editor treballa sobre una còpia viva del
mateix objecte** (l'objecte surt de l'escena Konva a `:4527` però continua a `selectedIds`).

### P3.4 — Altres superfícies trobades (les que el brief no comptava)

Més enllà de les tres, l'inventari en troba **quatre més amb accions duplicades** i vuit auxiliars:

1. **Barra de menús en text (E3)** — `:4260-4275`; Fitxer `:4153-4157`, Edició `:4164-4172`,
   **Objecte `:4173-4206` (26 entrades: agrupar, z-ordre, alinear, distribuir, mirall, booleanes,
   bloquejar/amagar, capçalera)**, Visualització `:4207-4212`. Gate `objDisabled` (`:4152`).
2. **Paleta vertical (PAL-1)** — `:4426-4491`, dades `PALETTE` `:3850-3894`, flyouts amb
   press-and-hold `:3906-3909`. Peu: botó imatge `:4477`; `PALETTE_SWATCHES` (`:3896-3900`)
   renderitzats **sempre `disabled`** (`:4484-4489`).
3. **Panell Capes** — `:4728-4759`: seleccionar, visibilitat (`:4743`), bloqueig (`:4746`),
   **z-ordre per fila (`:4749-4752`)**.
4. **Menú contextual de la capçalera** — `:5099-5114` (esborrar / desancorar).
5. Auxiliars: topbar (`:4232-4258`), ribbon Fitxer/Pàgina/Inserir (`:4068-4109`), tab Camps
   (`:5060-5079`), mode Importació (`:4638-4712`), tira de pàgines (`:5080-5097`), barra d'estat
   (`:5116-5146`), regles com a superfície d'acció (`:4498`, `:4503`, `:4584-4589`).
6. **Superfícies invisibles**: teclat d'objecte (`:2481-2711`), teclat de node (`:3230-3258`), gestos
   al canvas Paper (`PaperFlatEditor.jsx:595-769`), gestos al canvas Konva (`:4522`, `:4542-4551`).

### P3.5 — Duplicitats (el nucli del problema)

| Eina | Versió OBJECTE | Versió FORMA | Altres còpies | Diferència real |
|---|---|---|---|---|
| Alinear ×6 | ribbon `:4111-4116` → `alignSelection` `:2121` | barra nodes `:4325-4335` → `alignShapes` `PaperFlatEditor.jsx:370` | menú `:4182-4187` | **mateixa matemàtica escrita dues vegades**: `objectBounds` (mm, model) vs `p.bounds` (view px, viu) |
| Distribuir ×2 | ribbon `:4117-4118` → `:2145` | barra nodes `:4336-4339` → `:391` | menú `:4188-4189` **gated a `<2`** | el menú s'habilita amb 2 però `distributeSelection` retorna a `<3` (`:2148`) → **clic silenciós sense efecte** |
| Mirall H/V | ribbon `:4121-4122` → `mirrorObjects` `:2001` (**inverteix signe de `scaleX/scaleY`**) | barra nodes `:4347-4348` → `mirrorSubpath` (**reescriu segments**) | menú `:4191-4192` | ribbon filtra per `mirrorableIds` (`:3709`); el menú passa `selectedIds` cru → **mateixa acció, abast diferent** |
| Z-ordre ×4 | ribbon `:4123-4126` → `:2055`/`:2078` | barra nodes `:4362-4365` → `reorderShape` `:422` | menú `:4177-4180`; Capes `:4749-4752` | **4 implementacions** |
| Booleanes ×4 | ribbon `:4130-4133` → `booleanOp` (esborra N objectes, crea 1) | barra nodes `:4309-4317` → `booleanSubpaths` (in-place, l'objecte segueix sent un) | menú `:4194-4197` | **dos motors**; i18n divergent: `pathfinder_subtract` vs `pathfinder_subtract_hint` (`:4311`) |
| Eliminar | ribbon `:4127`; menú `:4171`; panell `:5050`; teclat `:2488-2504` | teclat `:3236` → `removeSelection` `:533-547`; panell mini `:4930` (subpath) | — | **5 camins** |
| Duplicar | menú `:4170` + `⌘D` `:2543` → `:3803` | Alt+arrossegar `PaperFlatEditor.jsx:690-694` | — | la versió forma **no té botó** |
| Rotar | panell `:5044-5047` (**absolut** 0-360) | barra nodes `:4349-4351` (**delta relatiu**) | — | **semàntica oposada** |
| Escalar | panell W/H `:4825-4836` + `scale_pct` `:4972` | barra nodes `%` `:4352-4354` | — | **3 unitats** (mm, %, % relatiu) |
| Fill / Traç | panell `:4962-4969` / `:4935-4941` (escriu al MODEL) | barra nodes `:4370-4377` (pinta el CANVAS, fusiona al commit `PaperFlatEditor.jsx:830-839`) | multi `:4782-4795` | **destinació diferent** |
| Gruix de traç | panell `:4942-4945` (**0.5–5**) | barra nodes `:4378-4380` (**0–∞, step 0.1**) | — | **rangs incompatibles** |
| Tancar/obrir | panell mini `:4926-4927` (commuta flag al model) | barra nodes `:4301-4302` (reescriu segments) | — | dos mecanismes |
| Partir/extreure | panell mini `:4928-4929` (`extractActiveSubpath` `:3759`) | barra nodes `:4303` (`splitAtNode`→`splitInTwo`) | — | **mateixa icona `ti-arrows-split`**, entrades diferents |
| Undo/Redo | menú `:4165-4166` + `⌘Z` `:2521` (història del MODEL) | teclat `:3240` → història INTERNA `PaperFlatEditor.jsx:590-591` | — | **dues històries; la interna no té cap botó** |
| Nudge | teclat `:2688-2711` (**mm**) | teclat `:3246-3250` (**px de view**) | — | **unitats diferents → depèn del zoom** |
| Entrar a edició de nodes | — | — | panell `:5031`; dbl-clic `:4543`; eina `node` `:4535`; tecla `A` `:3267` | **4 portes al mateix `startVectorEdit`** |
| Seleccionar-ho tot | **NO EXISTEIX** botó ni menú | `⌘A` `:3241` → `selectAll` `:566` | — | només dins mode nodes |
| Alineació (homònim) | ribbon `:4111-4113` = posició d'objectes | — | panell `:4885-4887` = alineació **de text** | **col·lisió semàntica a la mateixa pantalla** |

Altres duplicats de comandament fora del nucli: Exportar PDF ×3 (`:4252`, `:4070`, `:4154`), zoom ×3
(`:4083-4086`, `:4207-4212`, `:5134-5144`), afegir/esborrar pàgina ×2 (`:4078-4079`, `:5089`/`:5095`),
inserir imatge ×2 (`:4104`, `:4477`), importar SVG ×3 (`:4101`, `:4156`, `:5036`).

**Superfícies mortes/placeholder**: `PALETTE_SWATCHES` sempre `disabled` (`:4484-4489`),
`import-measures` sense handler (`:4103`), `autosave`/`version` com a botons informatius `disabled`
(`:4072-4073`). El comentari `:4044-4048` documenta que **ja es va retirar** una fila redundant del
ribbon en mode nodes — hi ha precedent de la neteja.

### P3.6 — Matriu `eina × superfície × abast`

Llegenda: **a**=barra contextual nodes · **b**=ribbon Organitzar · **c**=panell Propietats ·
M=menú text · P=paleta · L=Capes · K=teclat · G=gestos canvas.

#### T1 · Geometria i transformació

| Eina | a | b | c | Altres | Abast | Handler(s) | Dup? |
|---|---|---|---|---|---|---|---|
| Moure X/Y numèric | ✗ | ✗ | `:4837-4844`, multi `:4796-4809` | K `:2688-2711`; G drag | objecte, multi | `moveObjectTo` `:2185` | SÍ ×3 |
| Moure forma | ✗ | ✗ | ✗ | K `:3246-3250`; G `:689-697` | forma | `nudge` `:572`; `translateSubpath` | SÍ (unitats) |
| Moure node/segment | ✗ | ✗ | ✗ | K `:3246-3250`; G `:699-717` | node, segment | `moveSegment` `paperOps.js:179` | — |
| Redimensionar W/H | ✗ | ✗ | `:4825-4836` | G Transformer `:2458-2479` | objecte | `resizeObjectAxis` `:2251` | SÍ |
| Escalar % | `:4352-4354` | ✗ | `:4972` (`data_block`) | — | forma / objecte | `scaleShapes` `:559` | SÍ |
| Rotar | `:4349-4351` (rel.) | ✗ | `:5044-5047` (abs.) | — | forma / objecte | `rotateShapes` `:560` | **SÍ, semàntica divergent** |
| Mirall H | `:4347` | `:4121` | ✗ | M `:4191` | forma / objecte | `mirrorShapes` `:558`; `mirrorObjects` `:2001` | **SÍ ×3** |
| Mirall V | `:4348` | `:4122` | ✗ | M `:4192` | forma / objecte | ídem | **SÍ ×3** |
| Bloqueig proporció | ✗ | ✗ | `:4819-4822` | — | objecte | `setRatioLocked` | NO |
| Guies | ✗ | ✗ | ✗ | regles `:4498`,`:4503`,`:4584-4589` | pàgina | `startGuideCreate` `:1945` | NO |

#### T2 · Aparença

| Eina | a | b | c | Altres | Abast | Handler(s) | Dup? |
|---|---|---|---|---|---|---|---|
| Emplenat | `:4370-4373` | ✗ | `:4962-4969`, multi `:4789-4794` | P swatch `:4484` (disabled) | forma/subpath · objecte · multi | `setFill` `:562`; `updateObject` | **SÍ ×3** |
| Color de traç | `:4374-4377` | ✗ | `:4935-4941`, multi `:4782-4788` | ídem | ídem | `setStroke` `:563`; `updateShape` `:3703` | **SÍ ×3** |
| Gruix de traç | `:4378-4380` | ✗ | `:4942-4945` | — | forma / objecte | `setStrokeWidth` `:564` | **SÍ, rangs incompatibles** |
| Puntes de fletxa | ✗ | ✗ | `:4954-4955` | — | `arrow`/`path` | `updateShape` | NO |
| Tipus de línia (dash) | **NO EXISTEIX** com a control — només eines de creació `line_dot` (`:3867`) i `arrow_curve` (`:3872`) | | | | | | — |
| Tipografia | ✗ | ✗ | `:4867-4881` | — | text / fill de grup | `updateText` `:3687` | NO |
| Alineació de text | ✗ | ✗ | `:4885-4887` | — | text | `updateText({align})` | homònim de b1-b3 |
| Color / fons de text | ✗ | ✗ | `:4890-4906` | — | text | `updateText` | NO |
| Contingut de text | ✗ | ✗ | `:4863-4866` | G dbl-clic `:4542` + overlay `:4605-4611` | text | `commitTextEdit` `:3086` | SÍ |

#### T3 · Estructura i organització

| Eina | a | b | c | Altres | Abast | Handler(s) | Dup? |
|---|---|---|---|---|---|---|---|
| Alinear ×6 | `:4325-4335` | `:4111-4116` | ✗ | M `:4182-4187` | formes 2+ / objectes 2+ | `alignShapes` `:370`; `alignSelection` `:2121` | **SÍ ×3** |
| Distribuir H/V | `:4336-4339` | `:4117-4118` | ✗ | M `:4188-4189` | formes 3+ / objectes 3+ | `distributeShapes` `:391`; `:2145` | **SÍ ×3 + gate incoherent** |
| Agrupar | ✗ | `:4119` | ✗ | M `:4174` | objectes 2+ | `groupSelection` `:2090` | SÍ ×2 |
| Desagrupar | ✗ | `:4120` | ✗ | M `:4175` | grup | `ungroupObject` `:2111` | SÍ ×2 |
| Entrar/sortir de grup | ✗ | ✗ | ✗ | G `:4545`; K Escape `:2555-2566` | grup | `setActiveGroup` | NO |
| Z-ordre ×4 | `:4362-4365` | `:4123-4126` | ✗ | M `:4177-4180`; L `:4749-4752` | forma / objectes free | `reorderShape` `:422`; `:2055`/`:2078` | **SÍ ×4** |
| Booleanes ×4 | `:4309-4317` | `:4130-4133` | ✗ | M `:4194-4197` | formes 2+ / objectes 2+ | `booleanSubpaths` `paperOps.js:122`; `booleanOp` `paperbool.js:159` | **SÍ ×3, motors diferents** |
| Eliminar | K `:3236` | `:4127` | `:5050-5054`, subpath `:4930` | M `:4171`; K `:2488-2504` | node/segment/forma · subpath · objecte · multi | `removeSelection` `:533`; `deleteSelection` `:3739` | **SÍ ×5** |
| Duplicar | G Alt-drag `:690` | ✗ | ✗ | M `:4170`; K `:2543` | forma / objectes | `duplicateSelectedShapes` `:316`; `:3803` | SÍ ×2 |
| Copiar/Enganxar | ✗ | ✗ | ✗ | M `:4168-4169`; K `:2531-2542` | objectes free | `:3792`/`:3797` | SÍ ×2 |
| Bloquejar / Amagar | ✗ | ✗ | ✗ | M `:4199-4200`; L `:4743`,`:4746` | objecte | `toggleLock` `:3816`; `toggleVisible` `:3811` | SÍ ×2 |
| Desfés/Refés | K `:3240` (hist. interna) | ✗ | ✗ | M `:4165-4166`; K `:2521-2530` (hist. document) | document · sessió | `ftt/history.js:49,64`; `:590-591` | **SÍ, dues històries** |
| Seleccionar-ho tot | K `:3241` | ✗ | ✗ | ✗ | formes o nodes | `selectAll` `:566` | NO |

#### T4 · Edició de nodes i formes

| Eina | a | b | c | Altres | Abast | Handler(s) | Dup? |
|---|---|---|---|---|---|---|---|
| Cursor forma (fletxa negra) | `:4289-4293` (`:5319`) | ✗ | ✗ | K `V` `:3252` | mode | `setNodeTool('shape')` | SÍ |
| Cursor directe (fletxa blanca) | `:4289-4293` (`:5320`) | ✗ | ✗ | K `A` `:3252`; G dbl-clic `:611-616` | mode | `setNodeTool('select')`; `onEnterDirect` `:4628` | SÍ ×3 |
| Afegir node | `:4295-4299` (`:5324`) | ✗ | ✗ | K `+` | node (traç) | `addNodeAt` `paperOps.js:60` | SÍ |
| Treure node | `:5325` | ✗ | ✗ | K `-` | node | `removeNode` `paperOps.js:32` | SÍ |
| Convertir node | `:5326` | ✗ | ✗ | K `B` | node | `toCorner`/`toSmooth` `:41`/`:49` | SÍ |
| Tisores | `:5327` | ✗ | ✗ | K `C` | segment (punt arbitrari) | `splitAtLocation` `paperOps.js:212` | SÍ |
| Tancar traç | `:4301` | ✗ | `:4926-4927` | — | forma | `closeSegments` `:139`; `toggleActiveSubpathClosed` `:3776` | **SÍ ×2** |
| Obrir traç | `:4302` | ✗ | `:4926-4927` | — | node / forma | `openAtNode` `:145` | **SÍ ×2** |
| Partir / extreure | `:4303` | ✗ | `:4928-4929` | — | node / subpath | `splitAtNode` `:155`; `extractActiveSubpath` `:3759` | **SÍ ×2, mateixa icona** |
| Seleccionar subpath | ✗ | ✗ | `:4917-4920` (sortir) | P eina `subpath` `:3854`; G `:4550-4551` | subpath | `setActiveSubpath` `:1789` | NO |
| Entrar a edició de nodes | ✗ | ✗ | `:5031-5034` | G `:4543`; P `:4535`; K `A` `:3267` | `path`/`sketch_svg` | `editSelectedFlat` `:3207` | **SÍ ×4** |
| Fet (commit) | `:4052-4055` | — | ✗ | — | objecte | `commit` `:803` | NO |
| Cancel·lar | `:4056-4059` | — | ✗ | K Escape `:2569-2580` | sessió | `setEditingFlatId(null)` | SÍ ×2 |
| Nanses (trencar simetria) | ✗ | ✗ | ✗ | G `:707-717` | nansa | `mirrorHandle` `paperOps.js:72` | NO |
| Marquesina de nodes | ✗ | ✗ | ✗ | G `:676`, `:759-766` | nodes | inline | NO |

**Veredicte P3: cal X — la fusió és el bloc gros i és de MOTOR, no de UI.** Fusionar botons sense
unificar les dues implementacions d'alinear/distribuir/mirall/z-ordre/booleanes deixaria una barra
única servint dos comportaments diferents segons el mode. A més hi ha **7 superfícies**, no 3.

---

## BLOC P4 — Capçalera: desvincular i editar

### P4.1 — Com està modelada

**No és un grup, ni una plantilla viva: és UN objecte atòmic** la geometria del qual es genera per
codi. Inserció literal — `TechSheetEditor.jsx:3536-3539`:

```js
addObject({
  id: uid(), type: 'data_block', kind: 'header', layer: 'template', locked: true,
  ...MASTER_HEADER_GEOM, config: { layout: 'masterFtt' },
})
```

- `MASTER_HEADER_GEOM` (x/y/w/h en mm) — `:682-687`, derivat de `HDR_M` (pt de l'SVG canònic
  `docs/spec/plantilla_capcalera_ftt.svg`) — `:668-674`.
- Bessó al backend amb els **mateixos valors**: `backend/fhort/models_app/master_template.py:33-43`
  (`_HEADER_OBJ`).
- **Camps de l'objecte: només `id/type/kind/layer/locked/x/y/width/height/config`.** `config` només
  porta `{layout}` (`'masterFtt'` | `'blocks4'` | absent = legacy) — `:801-807`.
  **NO EXISTEIX `children`, ni cap array de texts/caixes/colors.**

Render: `HeaderBlock` (`:903-923`) és **un únic `<Group>` Konva** que pinta una llista de primitives
calculades en render per `buildMasterHeaderPrimitives` (`:712-772`): 1 rect de marc + 2 línies + ~20
texts, amb els valors llegits **en viu** de `modelData` (`m?.codi_intern`, `m?.nom_prenda`,
`m?.size_run_model`, `_hdrDate(new Date())` — `:740-773`). Cada primitiva es pinta amb `PrimNode`
(`:838-851`): **texts i línies amb `listening={false}`** (`:846`, `:848`); els rects només escolten
si tenen `fill`. El logo és un `KonvaImage` a part, també `listening={false}` (`:920`,
`headerMasterLogoRect` `:694-707`). Mateix camí per a l'export (`:1221-1252`, `addPrimsToGroup`
`:853-860`).

### P4.2 — Què fa exactament "desvincular"

Dos punts d'entrada, **un sol handler**: menú contextual (`:5100-5114`, entrada `header_detach`
`:5104`, obert des de `onHeaderContextMenu` `:4531`, que **no s'obre si ja està `detached`**) i menú
Objecte `mo-hdr-detach` (`:4205`, habilitat només amb `headerAnchored` `:4163`).

`detachHeaderOnPage` — `TechSheetEditor.jsx:3569-3577`:

```js
updatePageObjects(pageIdx, objs => objs.map(o => (
  (o.type === 'data_block' && o.kind === 'header')
    ? { ...o, layer: 'free', locked: false, detached: true }
    : o
)))
```

Pas a pas: (1) guard de lock del document; (2) **tres flags i res més** — `layer: template→free`,
`locked: true→false`, `detached: true`; (3) toast.

**Per què els fills no són editables: perquè NO N'HI HA CAP.** El detach només aixeca els guards de
*selecció d'objecte* (`selectable` `:4533`, `draggable` `:4534`, esborrat `:2503`, Transformer
`:2472`). Un cop `free`+`!locked`, el bloc **es pot seleccionar, arrossegar, escalar i esborrar com
un tot**, però:

- El contingut segueix sent `prims` regenerats a cada render, **tots amb `listening={false}`** →
  **cap clic hi arriba mai**.
- No hi ha camí d'entrada dins el bloc: `onDblGroup`/`activeGroup` només amb `o.type === 'group'`
  (`:4545`); l'edició vectorial només amb `['sketch_svg','path']` (`:3208`, `:3214`).
- **`detached: true` no canvia el render** — no es llegeix al renderer; només a `masterHeaderInstance`
  (`:3549`), `headerAnchored` (`:4163`) i `onHeaderContextMenu` (`:4531`).
- **Cap superfície escriu `obj.config` d'un header**: `config.blocks`/`heightMm`/`logoMaxMm` es
  llegeixen (`:556-557`, `:576-577`, `:634`) però **NO EXISTEIX cap UI que els escrigui**, ni cap
  panell de propietats de capçalera.

### P4.3 — Sistema de plantilles

**Existeix, i és de document sencer, no de "capçalera de pàgina".**

- `DocumentTemplate` — `backend/fhort/models_app/ftt_models.py:38-70` (`nom`, `descripcio`,
  `fitxer_template` amb el `.fttpt`, `metadata_schema`, `is_sample`, `origen`, `actiu`).
  **No té cap FK a documents instanciats.**
- CRUD: `backend/fhort/models_app/ftt_template_views.py:13-35`; rutes `document-templates`
  (`backend/fhort/models_app/urls.py:49`).
- La plantilla mestra de capçalera es genera per codi:
  `backend/fhort/models_app/master_template.py:46-53` (`build_master_header_document`) i `:56-88`
  (`seed_master_template`, idempotent, sembrat per `bootstrap_tenant`).
- Frontend: `frontend/src/App.jsx:152` (llistar), `:171` (diàleg de tria), `createDoc(tpl.id)`.
- Instanciació: `backend/fhort/models_app/ftt_document_views.py:48-77` → `services_ftt.unpack` +
  `resolve_placeholders`.

**La instància és una CÒPIA, no una referència viva** —
`backend/fhort/models_app/services_ftt_document.py:189-199` i `_resolve_obj:167-183`: els objectes
`type:'field'` es **congelen** a `type:'text'` amb el valor real, amb marca `field_key`
(`services_ftt_document.py:116`) per poder descongelar. **El `data_block kind:'header'` NO passa per
aquí**: es copia tal qual i els seus valors es resolen en viu a cada render. Un cop copiat **no queda
cap punter a la `DocumentTemplate`** → **el "desvincular" no trenca cap enllaç real: només canvia
flags locals.**

Camí invers: `FttSaveAsTemplateView` (`ftt_document_views.py:188-208`), disparat des de
`TechSheetEditor.jsx:3630`. Dins d'un document sí hi ha re-instanciació: `masterHeaderInstance()`
(`:3546-3553`) clona el primer header `masterFtt` **no `detached`** a cada pàgina nova (`:3554-3558`).

### P4.4 — Què caldria per a "desvincular = desagrupar"

**Desagrupar genèric SÍ EXISTEIX** — `ungroupObject` (`:2111-2121`): agafa `group.children`, els
passa per `globalizeObject` (`:219…`, que compon rotació/escala/posició del pare) i els substitueix a
la pàgina. Exposat al ribbon (`:4120`) i al menú (`:4175`), **sempre amb el guard
`selObj?.type !== 'group'`**. El contrari, `groupSelection` (`:2090-2109`), **exclou explícitament
`o.layer !== 'template'`** (`:2092`).

**Serviria? Només si abans algú converteix el header en un `type:'group'` amb `children`. Avui
`ungroupObject` sobre un header retorna sense fer res.**

Els sis obstacles concrets, en fets:

1. El bloc **no té `children`** (`:3538`); els elements visibles neixen a
   `buildMasterHeaderPrimitives` (`:712-772`) i **moren a cada render**.
2. Les primitives (`{t:'r'|'l'|'t', x,y,w,h,text,fill,size,bold,underline}`, `:838-851`) **no són
   objectes de l'editor**: no tenen `id`, ni `type` d'objecte, ni `layer`. Cap és consumible per
   `ObjectNode` sense traducció (`r`→`rect`, `l`→`line`, `t`→`text`).
3. Les coordenades de les prims són **relatives al bloc i en pt** (`gx()`/`_hdrP()`, `:668-676`,
   `:718`), no en mm globals → caldria la composició que fa `globalizeObject`.
4. Els texts són **valors del model resolts en viu** (`:740-773`). Desagrupar-los a `text` els
   **congelaria**. **El mecanisme per no perdre el binding JA EXISTEIX al sistema i el header no
   l'usa**: `type:'field'` + `FieldChipNode` (`:1467-1469`) + congelació `field`→`text` amb marca
   `field_key` (`services_ftt_document.py:167-183`, `:116`).
5. El logo no és una prim sinó un `KonvaImage` calculat (`:920`, `:694-707`); l'equivalent d'objecte
   és `type:'field' key:'customer_logo'` (`services_ftt_document.py:169-174`) o
   `type:'image' kind:'logo'` (`:202-212`).
6. Els dos guards que un canvi de model tocaria: `groupSelection` a `layer !== 'template'` (`:2092`)
   i "màxim 1 header per pàgina" (`:3533`).

**Veredicte P4: cal X — no és un bug de permisos, és un canvi de model de dades.** El detach ja fa
tot el que pot fer amb el model actual. Convertir la capçalera en editable exigeix materialitzar les
primitives com a objectes de primer nivell (amb `type:'field'` per als valors del model), cosa que
avui NO EXISTEIX. Punt únic d'edició de la semàntica: `TechSheetEditor.jsx:3569`.

---

## BLOC P5 — Què mor i què es conserva

### P5.1 — La premissa del brief, corregida

**PaperFlatEditor NO és un modal.** Tot el seu JSX (`PaperFlatEditor.jsx:851-859`) és un `<div>`
absolut i un `<canvas>`. NO EXISTEIXEN: overlay, títol, diàleg, barra d'eines pròpia (decisió F1,
documentada a `:20-22`), teclat propi (`:781-782`), zoom/pan propis.
Els botons Fet/Cancel·lar **són del pare** (`TechSheetEditor.jsx:4052`, `:4056`) i es conserven.

### P5.2 — Inventari del que fa (i si és reproduïble)

| # | Peça | Àncora | Reproduïble in-place? |
|---|---|---|---|
| 1 | Sessió d'edició (`setEditingFlatId`) | `:3207-3219`, `:3260-3277` | **ja ho és** |
| 2 | Muntatge lazy + Suspense | `:18`, `:4613-4630` | sí |
| 3 | **L'objecte editat s'amaga del Konva** | `:4527` | **lligat al patró "dos canvas"** |
| 4 | PaperScope propi + 2 capes (`flat-sketch`, `flat-ui`) | `PaperFlatEditor.jsx:59-65` | **lligat al canvas propi** |
| 5 | Import de geometria (`path` per entrada amb `data.index`; `sketch_svg` per `importSVG`) | `:463-491` | sí |
| 6 | Índex estable de forma per subpath | `:496` | sí |
| 7 | Estat local en **refs, no React** (7 refs) | `:28-35` | sí |
| 8 | Dos modes Illustrator + doble-clic per entrar a directa | `:150`, `:611-636` | sí |
| 9 | **Render dels handles**: àncores 7px + hit-areas 18px + nanses 6px + línies discontínues; `drawCurveHighlight`, `drawShapeBox` | `:89-148`, `:160-178`, `:870-881` | **lligat a la capa UI de Paper** — caldria reimplementar en Konva si es canvia de motor |
| 10 | Marquesina de nodes | `:683`, `:766-773`, `:884-895` | sí |
| 11 | **Undo intern propi** — NO usa `ftt/history.js`; `historyRef={past,future}` amb snapshot full-scene en **view px**, límit 100, 1 snapshot per gest | `:238-266`, `:248`, `:695` | **lligat a la sessió: mor amb el component** |
| 12 | Commit (view px → mm local, fusió de `paintRef`) | `:810-853` | sí |
| 13 | `onCanCommitChange` — només diu "el setup ha anat bé" (`true` a `:492`, `false` a `:57`) | `:44`, `:57`, `:492`; consum `:4052` | sí |
| 14 | Cancel·lació: **cap handler propi**; el pare fa `setEditingFlatId(null)` i el cleanup destrueix el scope | `:66-81`; `:4056`, `:2568-2579` | sí |
| 15 | `onSplitObject` — **l'únic camí que escriu al model abans del commit** | `:528-535`, `:517-526`; pare `:3280-3291` | sí |
| 16 | API `run(name,…)` amb 19 accions | `:557-599`; `runNode` `:3222` | sí |
| 17 | Pintura per mode (`applyPaint`, valors a `paintRef` fins al commit) | `:205-230` | sí |
| 18 | `onNodeState`/`pushState` per a la barra contextual | `:189-202`; `:4624`, `:4278-4383` | sí |
| 19 | `onEnterDirect` | `:621`; `:4628` | sí |
| 20 | Sincronia de zoom (redimensiona canvas + `view.viewSize` + escala la capa) | `:793-808` | **lligat al canvas propi** |
| 21 | Cursors per eina | `:859-860` | sí |
| 22 | **SNAPPING: NO EXISTEIX al sub-editor** — `ftt/snapping.js` no s'importa mai des d'aquí (només l'usa el drag d'objectes) | grep sense hits | n/a |
| 23 | Teclat: **ja viu al pare** | `:3231-3258`; `PaperFlatEditor.jsx:788-789` | **ja ho és** |

**Limitació estructural que qualsevol in-place hereta si no es toca**: `PaperFlatEditor` només carrega
`subpaths[0]` d'una entrada composta (`:466`) i al commit només reescriu `si === 0` (`:837`). **Els
forats (subpaths 1..n) no es veuen ni s'editen, però sí es conserven al model i sí es pinten** al
Konva i al PDF (`pathToData`, `TechSheetEditor.jsx:1026`).

### P5.3 — Dependències ocultes: DESMENTIT

**Cap funció de `paperOps.js` ni de `paperbool.js` depèn del modal, del DOM de la pàgina ni del scope
Paper del sub-editor.** Vegeu §P1.6. `withPaperScope` (`paperbool.js:12-24`) fabrica el seu **propi
canvas detached** (`:14-15`), mai inserit al DOM, destruït al `finally`. **Res a desfer per jubilar
la superfície actual.**

### P5.4 — Undo/redo: dos rellotges

- **Document**: `useDocumentHistory` (`ftt/history.js:13-88`, importat a `TechSheetEditor.jsx:14`).
  Snapshots **per referència de l'array `pages`** (segur perquè `updatePageObjects` sempre crea
  referència nova, `history.js:5-7`), **coalescing per debounce de 500 ms** (`:11`, `:36-46`), límit
  50 (`:10`). `undo`/`redo` **buiden la selecció** (`:58`, `:68`). ⌘Z **surt d'hora si
  `editingFlatId`** (`TechSheetEditor.jsx:2514`).
- **Sessió**: `historyRef` full-scene en view px, límit 100 (`PaperFlatEditor.jsx:238-266`), exposat
  **només per teclat** (`:3241-3244` → `:597-598`), **sense cap botó**.

Convivència actual: mai simultanis. En fer "Fet", `commitFlatEdit` fa **una sola** `updateObject`
(`:3293-3316`) → **una sola entrada** a la història del document; tot l'undo intern es perd amb el
cleanup (`:66-81`). **Excepció documentada**: `handleSplitObject` (`:3280-3291`) fa `addObject`
**durant** la sessió → això SÍ entra a la història del document abans del commit, i el `historyRef`
intern **no el pot desfer** (comentari explícit a `PaperFlatEditor.jsx:235-237`). Cancel·lar no
revoca res al model **excepte l'objecte creat per un split, que queda**.

**Veredicte P5: llest per al diagnòstic, però el "commit únic" és una decisió a reobrir.** El que mor
és poc (un canvas i un scope); el que costa és (a) reimplementar el render de handles si es canvia de
motor, i (b) decidir si l'edició de nodes segueix sent una transacció (Fet/Cancel·lar) o passa a ser
edició contínua amb l'undo del document — cosa que faria desaparèixer `commit`, `onCanCommitChange`,
`historyRef` i els botons Fet/Cancel·lar sencers.

---

## BLOC P6 — Render i export

**CONFIRMAT: l'edició in-place no canvia res del render unificat live=PDF.**

- **Live**: un `path` es pinta amb `<Path data={…}>` de react-konva, un per entrada de `obj.paths[]`
  — `PathObj` (`TechSheetEditor.jsx:1393-1420`, `<Path>` a `:1414`). **No és `Shape` amb `sceneFunc`
  ni `Line`.** Props des de `pathChildProps` (`:1064-1076`) sobre `pathToData` (`:1025-1028`) →
  `segmentsToData` (`:998-1023`, `d` SVG en px de pàgina). Compostos = subpaths concatenats en un sol
  `d` amb `fillRule:'evenodd'` per als forats (`:1024`). Puntes: `pathHeadAngles` (`:1032-1057`) +
  `headTriPoints` (`:1059-1063`) → `<Line closed>` (`:1416-1419`).
- **Export**: `onExport` (`:3587-3629`) fa `renderPageToDataURL(page, 3.5, ctx)` (`:1298-1319`) sobre
  un `Konva.Stage` **offscreen** (`:1303`) amb `addObjectToLayer` (`:1155…`); la branca `path`
  (`:1204-1220`) crea `new Konva.Path(pathChildProps(obj, path))` (`:1211-1213`).

**Identitat ancorada**: `pathChildProps` cridada pel live a `:1400` i per l'export a `:1211`;
`pathToData`/`segmentsToData` són l'únic productor de geometria dels dos camins; puntes idèntiques
(`:1416` vs `:1216-1218`). El comentari `:1409-1410` ho declara ("mateix builder que l'export"), i el
principi és explícit a `:1128-1133` ("es construeix amb PRIMS… pintar-lo en un i no en l'altre és,
per construcció, impossible") i `:1295-1297`.

**Únic contracte**: escriure `obj.paths[]` amb la forma
`{closed, segments:[{x,y,inX,inY,outX,outY}], fill, stroke, strokeWidth, fillRule}` o `{subpaths:[…]}`.
Ni `renderPageToDataURL` ni `PathObj` saben res de `PaperFlatEditor`.

**Dues anotacions fora d'abast** (s'anoten, no es toquen):
- `sketch_svg` **no és vectorial al canvas**: es pinta com a `KonvaImage` d'un dataURL
  (`:1363-1373`, export `:1288-1292`). Hi ha via de conversió a `path` (`legacySketchSvgToPath`
  `:1611-1679`, aplicada en carregar `:1681+`).
- **El PDF és ràster a 3.5×** (`:1314` + `:3593-3596`), no vectorial, tot i que tota la geometria
  intermèdia és `d` SVG.

**Veredicte P6: llest. No cal tocar res del render ni de l'export.**

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT

| # | Peça | Estat | Àncora |
|---|---|---|---|
| 1 | Modal del sub-editor a jubilar | **NO EXISTEIX** — ja és in-place | `PaperFlatEditor.jsx:851-859`, `TechSheetEditor.jsx:4614-4631` |
| 2 | Sincronia de coordenades Konva↔Paper | **EXISTEIX i és exacta** (simètrica, sense skew) | `PaperFlatEditor.jsx:435-452` ↔ `:810-822` |
| 3 | Pan del Stage a sincronitzar | **NO EXISTEIX** — el pan és scroll d'un div; el canvas es mou sol | `TechSheetEditor.jsx:3097-3113`, `:4509` |
| 4 | PaperKonvaPoc com a plataforma | **DIFERENT** — precedent de `pointerEvents`, no de coordenades; orfe però al build | `PaperKonvaPoc.jsx:436`, `:6-8`; `App.jsx:341` |
| 5 | Arbitratge de punter Konva/Paper | **NO EXISTEIX** — avui és exclusió total per `editingFlatId` | `:2885`, `:2950`, `:3002`, `:4527` |
| 6 | Màquina d'estats de mode unificada | **NO EXISTEIX** — dues màquines (`tool` i `editingFlatId`+`nodeTool`) | `:1738` vs `:1763`, `:1766` |
| 7 | Estat de selecció compartit | **NO EXISTEIX** — triplicat al pare + 4 refs al fill; pont només de lectura (`nodeSel`) | `:1737`, `:1787-1789`; `PaperFlatEditor.jsx:28-31` |
| 8 | Motor únic d'alinear/distribuir/mirall/z-ordre/booleanes | **NO EXISTEIX** — **dues implementacions sense una línia en comú** | `:2001`,`:2055`,`:2078`,`:2121`,`:2145`,`:3745` vs `PaperFlatEditor.jsx:342-433` |
| 9 | Nombre real de superfícies d'eines | **DIFERENT: 7, no 3** (+ 8 auxiliars + 4 invisibles) | §P3.4 |
| 10 | Gate del panell dret en mode nodes | **FALTA** — només el botó Eliminar està gated; W/H/X/Y/rotació/fill/traç escriuen al model durant la sessió | `:5050` vs `:4825-4844`, `:4935-4969`, `:5044` |
| 11 | Gate coherent de "distribuir" al menú | **DIFERENT** — menú `<2`, handler `<3` → clic silenciós sense efecte | `:4188-4189` vs `:2148` |
| 12 | Unitats coherents (nudge, gruix de traç) | **DIFERENT** — mm vs px de view; 0.5–5 vs 0–∞ | `:2696-2706` vs `:3247-3249`; `:4943` vs `:4378` |
| 13 | Semàntica coherent de rotar | **DIFERENT** — absolut (panell) vs relatiu (barra nodes) | `:5044-5047` vs `:4349-4351` |
| 14 | Fills editables de la capçalera | **NO EXISTEIXEN com a dades** — es generen per codi, `listening={false}` | `:3536-3539`, `:712-772`, `:846`, `:848` |
| 15 | Enllaç viu capçalera↔plantilla | **NO EXISTEIX** — la instància és una còpia sense punter | `services_ftt_document.py:189-199` |
| 16 | Mecanisme de binding valor-de-model reutilitzable | **EXISTEIX i no s'usa al header**: `type:'field'` + `field_key` | `:1467-1469`; `services_ftt_document.py:167-183`, `:116` |
| 17 | Desagrupar genèric | **EXISTEIX** però exigeix `type==='group'` amb `children` | `:2111-2121` |
| 18 | Puresa de `paperOps`/`paperbool` | **EXISTEIX** — 11/17 pures; única dep. de DOM = canvas offscreen; **ja té 2 consumidors** | `paperOps.js:6`; `paperbool.js:15`; `TechSheetEditor.jsx:16` |
| 19 | Snapping al sub-editor | **NO EXISTEIX** | `ftt/snapping.js` sense import des de `PaperFlatEditor` |
| 20 | Edició de forats (subpaths 1..n) | **NO EXISTEIX** — només `subpaths[0]`; el model i el render sí els conserven | `PaperFlatEditor.jsx:466`, `:837` vs `TechSheetEditor.jsx:1026` |
| 21 | Undo unificat | **NO EXISTEIX** — dues històries; forat conegut al split | `history.js:13-88` vs `PaperFlatEditor.jsx:238-266`, `:235-237` |
| 22 | Render/export afectats pel canvi | **NO** — mateixa funció per a live i PDF | `:1064-1076` cridada a `:1400` i `:1211` |
| 23 | Superfícies mortes al build | **EXISTEIXEN**: swatches sempre `disabled`, `import-measures` sense handler, PoC orfe | `:4484-4489`, `:4103`, `App.jsx:341` |
| 24 | Tecles sense guard `editingFlatId` | **DIFERENT** — `Shift`, `Space`, ploma, nota/cota | `:2668`, `:2659`, `:2604`, `:2639` |
| 25 | Drecera `A` de la paleta | **DIFERENT** — `TOOL_SHORTCUT` la declara però el mapa no la fixa | `:109` vs `:2591`, `:3267` |

---

## 💡 PROPOSTA (a validar) — camins d'implementació

> Tot el que segueix és proposta, no fet. Les decisions són humanes (Patró C).

### Camí 1 — "Convergir el que ja hi ha" (Paper es queda, l'exclusió cau)

Mantenir els dos motors, però substituir l'exclusió total per un **arbitratge explícit de punter**
(el patró que el PoC ja demostra: `pointerEvents` commutat, `PaperKonvaPoc.jsx:436`), deixar
l'objecte editat **visible** al Konva (deixar de filtrar-lo a `:4527`) i pintar-hi Paper només els
handles per damunt. Cau la sensació de "sortir a un altre lloc".

| Bloc | Cost |
|---|---|
| B1 · Màquina d'estats de mode explícita (objecte / forma / node) amb taula de captura | **M** |
| B2 · Arbitratge de punter + treure el filtre `:4527` + reconciliar les 11 col·lisions de §P2.8 | **M** |
| B3 · Gate del panell dret en mode nodes (forat #10) | **S** |
| B4 · Superfície única "Editar" que reindexi els 33+21+42 controls per abast | **M** |
| B5 · Motor únic d'alinear/distribuir/mirall/z-ordre/booleanes | **L** |
| B6 · Undo unificat (o decisió explícita de mantenir la transacció) | **M** |

**Total ≈ M·4 + L·1 + S·1.** Risc baix a P1/P6 (no es toca el pont ni el render). Risc alt a B5.

### Camí 2 — "Konva pur" (Paper només com a calculadora)

Els handles de node passen a ser **shapes Konva** (Circle/Rect/Line dins la mateixa `<Layer>`),
alimentats per `paperOps` en mm. Paper queda reduït a `withPaperScope` per a les 4 operacions que
necessiten bezier (`paperOps.js:50`, `:61`, `:123`, `:213`) i `booleanOp`. Desapareix el segon canvas,
el segon PaperScope, la sincronia de zoom (`:793-808`) i tota la conversió a view px.

| Bloc | Cost |
|---|---|
| C1 · Reimplementar el render de handles en Konva (§P5.2 #9: àncores, hit-areas, nanses, ressalts) | **L** |
| C2 · Reimplementar els gestos de node/segment/nansa com a handlers Konva (`PaperFlatEditor.jsx:595-769`) | **L** |
| C3 · Portar `paperOps` a mm (el cridador decideix l'espai — §P1.6) | **S** |
| C4 · Un sol Transformer i una sola selecció; `activeSubpath` (`:1789`) com a base ja existent | **M** |
| C5 · Undo únic (desapareix `historyRef`, `commit`, `onCanCommitChange`, Fet/Cancel·lar) | **M** |
| C6 · Motor únic d'organització (com B5) | **L** |

**Total ≈ L·3 + M·2 + S·1.** El més car i el més net: un motor, un canvas, una selecció, un undo.
Beneficis col·laterals: el nudge deixa de dependre del zoom (#12), el zoom deixa de mutar geometria
(`:798`), i s'obre la porta a editar forats (#20).

### Camí 3 — "Híbrid per fases" (Camí 1 ara, Camí 2 després)

B1+B2+B3+B4 primer (la UX que Agus vol veure), amb el motor doble intacte; C1+C2 més tard quan la
màquina d'estats i la superfície única ja estiguin validades. **Cost total superior** (part de B2 es
llença en arribar a C2), **risc per pas molt menor**, i permet validar el disseny **veient**, que és
la llei del vault.

### Graf de dependències

```
        ┌──────────────────────────────────────────────┐
        │ B1 màquina d'estats de mode (objecte/forma/node)
        └───┬──────────────────────────┬────────────────┘
            │                          │
   ┌────────▼────────┐        ┌────────▼─────────┐
   │ B2 arbitratge   │        │ B4 superfície    │
   │    de punter    │        │  única "Editar"  │
   └────────┬────────┘        └────────┬─────────┘
            │                          │
            │                 ┌────────▼─────────┐
            │                 │ B3 gate panell   │  (independent, es pot fer ja)
            │                 └──────────────────┘
   ┌────────▼─────────────────────────────────────┐
   │ B5/C6 motor únic d'organització              │  ← el bloc gros; desbloqueja
   └────────┬─────────────────────────────────────┘     que la barra única no menteixi
            │
   ┌────────▼─────────┐        ┌──────────────────┐
   │ B6/C5 undo únic  │        │ C1+C2 handles i  │  (només Camí 2)
   └──────────────────┘        │  gestos en Konva │
                               └──────────────────┘

   P4 capçalera ── independent de tot l'anterior ──┐
   (canvi de model de dades: prims → objectes      │
    de primer nivell amb type:'field')             │
```

**P4 no depèn de cap dels camins** i es pot atacar en paral·lel. La forma proposada:
`detachHeaderOnPage` deixaria de posar 3 flags i passaria a **materialitzar** `buildMasterHeaderPrimitives`
en objectes reals (`rect`/`line`/`text` per a la decoració, **`type:'field'` per als valors del model**
i `type:'image' kind:'logo'` per al logo), embolcallats en un `type:'group'` → el `ungroupObject` que
**ja existeix** (`:2111`) fa la resta, i el binding no es perd perquè `field_key` ja té el mecanisme
de congelació/descongelació (`services_ftt_document.py:167-183`).

### Preguntes de disseny per a Agus (a validar VEIENT)

1. **Transacció o continu?** L'edició de nodes segueix sent un compromís Fet/Cancel·lar (avui:
   `:4052`, `:4056`, undo intern que mor) o passa a ser **edició contínua amb l'undo del document**?
   És la pregunta que més codi mou (B6/C5) i la que decideix si els botons Fet/Cancel·lar
   desapareixen. *Cal veure-ho: dues maquetes de la barra, amb i sense Fet/Cancel·lar.*
2. **Un sol motor o dos?** Camí 1 (Paper es queda per als handles) o Camí 2 (tot Konva). Afecta el
   cost en un factor ~2 i la qualitat del resultat a llarg termini.
3. **On viu "Editar"?** Pestanya del ribbon al costat d'Organitzar/Inserir/Pàgina, o barra contextual
   que apareix per selecció? El codi admet totes dues (les tabs són dades a `:4010-4015`).
   *Cal veure-ho: dos mockups del ribbon.*
4. **Què passa amb les 4 superfícies "extra"** (menú de text `:4173-4206`, paleta `:4426-4491`,
   Capes `:4749-4752`, menú contextual `:5099-5114`)? Es conserven com a accés alternatiu o
   s'esporguen? Avui dupliquen fins a 4 cops la mateixa acció.
5. **Semàntica única de mirall / rotar / escalar**: quan tinc una forma seleccionada dins un objecte,
   el mirall ha de **reescriure la geometria** (com fa la versió forma) o **invertir `scaleX`** (com
   fa la versió objecte)? Avui són comportaments diferents amb la mateixa icona.
6. **Els forats (subpaths 1..n)**: entren a l'abast? Avui NO EXISTEIX manera d'editar-los
   (`PaperFlatEditor.jsx:466`, `:837`) tot i que es pinten. Si el Camí B els ha de cobrir, això
   creix el bloc de motor.
7. **Capçalera desagrupada: reversible?** Un cop materialitzada en objectes, hi ha "tornar a
   vincular" o és de sentit únic? Afecta si cal guardar el `layout` d'origen al grup.
8. **PaperKonvaPoc**: es jubila (esborrar ruta `App.jsx:341` + fitxer + i18n) o es conserva com a
   banc de proves? Avui és pes mort al build.
