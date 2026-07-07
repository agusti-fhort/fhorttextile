> ⚠️ SUPERADA 2026-07-07 — implementada (closca PALETTE + ribbon E1-E3). Consulta només com a històric.

# DIAGNOSI — UI actual de l'editor de fitxa (per muntar la closca Illustrator)

> Patró A, **READ-ONLY absolut**. Cap canvi, cap commit, cap push. `/var/www/ftt-staging/frontend`.
> FETS amb `fitxer:línia`. Idees com `💡`. Decisions = de l'Agus (`⚖️`). Data: 2026-06-28.
> Fitxer: `src/pages/TechSheetEditor.jsx` (2324 línies). Tokens: `src/index.css`.

**Context:** muntar la closca d'eines estil Illustrator (paleta lateral, barra contextual, dock de
panells propietats/capes/alinear, barra superior amb logo, barra d'estat). El motor d'edició
(`type:'path'`, selecció, transform, nodes) **ja existeix**. Objectiu d'aquesta diagnosi: saber QUÈ
de la UI actual es **REEMPLAÇA** i QUÈ es **REAPROFITA**, per no duplicar UI.

---

## RESUM EXECUTIu

- Tota la lògica i l'estat (document `pages`, `selectedIds`, `tool`, `zoom`, `lockState`, handlers
  d'inserció/alineació/z-order/transform/export) són **REAPROFITABLES tal qual**. La closca nova
  només recablejarà JSX cap als mateixos handlers.
- El que es **REEMPLAÇA** és pura presentació: la barra d'eines (avui *dropdowns a la topbar* →
  paleta lateral esquerra), les barres de zoom/save/badge (→ barra d'estat inferior), i els
  objectes-estil inline (→ paleta dark).
- El **dock dret JA existeix** (l'`<aside>` de 180px amb propietats + alinear + z-order): es
  reaprofita com a base del dock de panells; només cal afegir-hi un panell "Capes".
- L'estilització és **100% inline** amb un punt de re-tema gairebé únic: l'objecte `COL`
  ([:43-46](../../frontend/src/pages/TechSheetEditor.jsx#L43-L46)) + els tokens `:root` d'`index.css`.
  El canvas Konva NO ha de seguir la paleta dark (pinta sobre paper blanc) → `KONVA_COL` es manté.
- **No existeix** ni paleta lateral d'eines, ni barra d'estat inferior, ni logo d'app: són afegits nous.

---

# 1) BARRA D'EINES actual

**`TOOL_GROUPS`** ([:1834-1856](../../frontend/src/pages/TechSheetEditor.jsx#L1834-L1856)) — 4 grups
`{ g, icon, label, tools:[...] }`:
- `shapes` (`ti-shape`): `rect`, `rect_round`, `ellipse` (`:1835-1839`).
- `draw` (`ti-pencil`): `line`, `line_dot`, `arrow`, `arrow2`, `draw` (`:1840-1846`).
- `text` (`ti-typography`): `text`, `text_box` (`:1847-1850`).
- `presets` (`ti-components`): `preset_callout`, `preset_detail_circle`, `preset_legend` (`:1851-1855`).

`activeTool(grp)` `:1857`. Famílies relacionades `RECT_TOOLS`/`LINE_TOOLS`/`PRESET_TOOLS` `:58-60`.
Estats: `tool/setTool` (`:994`, init `'select'`), `openGroup/setOpenGroup` (`:1011`, dropdown obert),
`toolbarRef` (`:1012`); efecte de tancar dropdown en clic-fora `:1299-1303`.

**On viu i com es pinta:** NO és un toolbar lateral — viu **dins la `<header>` topbar**, bloc
`{locked && (...)}` a [:1877-1912](../../frontend/src/pages/TechSheetEditor.jsx#L1877-L1912):
- Contenidor `<div ref={toolbarRef} style={{display:'flex',gap:4,marginLeft:16}}>` `:1879`.
- Botó fix **Select** (`ti-pointer`) `:1880-1883`.
- `TOOL_GROUPS.map`: cada grup = trigger d'icona + `ti-chevron-down` (`:1888-1892`) que obre un
  **menú desplegable absolut** (`position:absolute, top:100%, zIndex:50`) amb els `tools` com a
  botons `setTool(tl.k)` (`:1893-1902`).
- Botó **Imatge** (`ti-photo`) → `fileRef` + `<input type=file hidden>` `:1906-1910`.
- Tots amb estil `headerBtn` (`:1802-1806`).

💡 **A reemplaçar:** aquesta barra d'icones-amb-dropdowns a la topbar és exactament la "paleta
d'eines" del mockup, però en horitzontal. La closca la migraria a una **columna vertical esquerra**
(paleta), conservant `TOOL_GROUPS`/`setTool`/`tool` com a config i estat.

---

# 2) PANELL DE PROPIETATS actual

Viu a l'**`<aside>` dret** (180px, `:2035-2280`), dins un `<div>` scrollable `:2036`. Variables de
selecció derivades a [:1810-1821](../../frontend/src/pages/TechSheetEditor.jsx#L1810-L1821):
`selectedObjects` `:1810`, `selObj` `:1811`, `multiSelected` `:1812`, `multiStroke/Fill/Position`
`:1813-1815`, `mirrorableIds`/`freeSelectedIds` `:1816-1817`, valors comuns via `commonValue`
(`''` si mixtos) `:1818-1821`.

**Bloc MULTI-selecció** `{multiSelected && locked}` (`:2080-2166`):
- Agrupar `:2083` · grid alinear/distribuir 8 botons `:2087-2112` · mirall H/V `:2113-2124` ·
  z-order `:2125-2136` · color stroke `:2137-2143` · fill `:2144-2150` · pos X/Y `:2151-2164`.

**Bloc OBJECTE ÚNIC** `{selObj && locked}` (`:2167-2278`), tot via `updateObject(selObj.id, patch)`:

| Tipus | Controls | Línies |
|---|---|---|
| text | font-size, negreta (`fontStyle`), color (`fill`) | `:2170-2185` |
| rect/ellipse/line/arrow/path | color stroke (arrow també `fill`), `strokeWidth` | `:2186-2196` |
| rect/ellipse/path | fill | `:2197-2201` |
| data_block | escala % (`scale`) | `:2202-2207` |
| sketch_svg/path | "Editar nodes" → `editSelectedFlat`; (sketch_svg) "Reemplaçar SVG" | `:2208-2221` |
| tots menys line/arrow | Posició X/Y (mm) | `:2222-2234` |
| no `blocksTransform` | Mirall H/V | `:2235-2246` |
| layer free | Z-order | `:2247-2258` |
| no `blocksTransform` | Rotació | `:2259-2264` |
| group | Desagrupar | `:2265-2270` |
| free/data_block | Eliminar | `:2271-2276` |

`blocksTransform` = line/arrow/text-amb-bgFill (`:575-577`). Auxiliars: `ColorPicker` (6 pastilles
`QUICK_COLORS` + `<input type=color>`, `:2305-2318`), `SectionTitle` `:2320-2322`, `propLabel`
`:2323`, `propInput` `:2324`.

💡 **A reaprofitar gairebé sencer:** el contingut (controls + handlers) és exactament el dock de
propietats Illustrator. Es **conserva la lògica**; es reemplaça l'embolcall (amplada/posició/tema) i
s'hi afegeix un panell "Capes" i, opcionalment, separar "Alinear" en pestanya pròpia del dock.

---

# 3) INSERCIÓ d'elements

Botons a l'**aside dret**, secció "Inserir blocs de dades" (`SectionTitle` `:2038`), tots
`disabled={!locked}`:
- **insertHeader** `:2039-2042` (funció `:1725-1735`, data_block `header`, màx 1).
- **insertLogo** `:2043-2047` (funció `:1563-1567`, imatge del `customerLogoUrl`).
- **onAddTableClick** (taula graduada) `:2048-2051` (funció `:1718-1722`; modal si >1 fitting).
- **insertFlatSketch** `:2052-2055` (funció `:1568+`, insereix un `path` editable).
- **Importar flat SVG** `:2056-2061` → `flatFileRef` → `handleFlatSvgFile`/`importFlatSvgText` `:1594`.
- (Presets s'insereixen com a **eines** del grup `presets` de la toolbar, no aquí; construcció a
  `createPreset` `:1084` / `:1086-1110`.)
- A sota, "Fitxers del model" `:2065-2077` → `addModelFitxer(f)`.
- Modal selector de size-fitting `:2284-2298` (`pickFitting`).

💡 La inserció pot anar a una **barra contextual** (sota la topbar) o quedar-se al dock; els handlers
es reaprofiten.

---

# 4) LAYOUT general (arbre del `return`, des de `:1859`)

```
<div> :1860  width:100vw height:100vh, display:flex, flexDirection:column, background:#faf7f2
├─ <header> TOPBAR :1862  flex, gap:12, padding:0.7rem 1.2rem, borderBottom:1px #e3cfa3, bg:COL.sidebar
│   ├─ Back :1863 · EXPORT PDF :1866 (acció principal, bg gold) · Títol model :1870 · pàgina n/total :1873
│   ├─ saveLabel :1874 · notice :1875 · TOOLBAR eines {locked} :1877-1912 (§1)
│   ├─ <select> format pàgina :1914-1918 · controls ZOOM :1920-1940 (§5) · BADGE versió+lock :1942 (marginLeft:auto)
├─ <main> :1947  flex:1, display:flex, minHeight:0   (3 columnes)
│   ├─ [ESQ] PÀGINES :1949  width:96, flexShrink:0, bg:COL.bg, borderRight, overflowY:auto
│   │        (títol, afegir pàgina, thumbnails 84×60 + esborrar) :1950-1965
│   ├─ [CENTRE] viewport :1969 (ref viewportRef) flex:1, overflow:auto, position:relative, padding:24, onWheel
│   │        ├─ overlay readonly :1970-1974
│   │        └─ wrap zoom :1975 → <div ref=wrapRef :1976> transform:scale(zoom) → <Stage> :1978 → <Layer> :1982
│   │           (+ textarea inline edició text :2007, + PaperFlatEditor lazy :2019)
│   └─ [DRETA] <aside> :2035  width:180, flexShrink:0, borderLeft, bg:COL.bg, flexColumn
│            └─ <div scrollable> :2036  → Inserció (§3) · Fitxers · Propietats multi (§2) · Propietats únic (§2)
└─ (tanca </main> :2281) · modal pickFitting :2284-2298 · </div> :2299
```

Layout = **flexbox inline**: asides amb `width` fix + `flexShrink:0` (96 esq, 180 dreta), centre
`flex:1`. Cap CSS extern per al layout; `position` només per overlays/modals.

### 💡 On encaixa cada peça de la closca nova
- **Paleta lateral esquerra (eines):** NO existeix com a columna. La columna esquerra actual (`:1949`,
  96px) són les **miniatures de pàgines**. La paleta vertical d'eines s'inseriria com a **nova
  primera columna** dins `<main>` (`:1947`); les pàgines passarien a una segona columna o a un panell
  del dock.
- **Barra contextual (sota topbar):** afegir una franja entre `</header>` (`:1945`) i `<main>`
  (`:1947`) que mostri opcions de l'eina/objecte actiu (reusant els controls del dock).
- **Dock dret (propietats/capes/alinear):** **JA existeix** = l'`<aside>` `:2035`. S'amplia el `<div>`
  scrollable `:2036` amb un panell "Capes" (a partir de `pages[currentPage].objects` + z-order ja
  implementat `moveSelectionInFreeLayer` `:1114`).
- **Barra superior amb logo d'app:** la `<header>` `:1862` JA és la topbar però **no té logo d'app**
  (comença pel botó back). El logo aniria al principi (abans de `:1863`).
- **Barra d'estat inferior:** **NO existeix** (cap `<footer>`). Lloc natural: nou tercer fill del
  `<div>` arrel, just després de `</main>` (`:2281`). Hi migrarien zoom %, save, lock/versió, notice
  (avui a la topbar).

---

# 5) ZOOM i estat

**Zoom** (controls a la topbar, NO en barra inferior): constants `ZOOM_MIN=0.25`/`ZOOM_MAX=4`/
`ZOOM_STEP=0.1` (`:54-56`), `clampZoom` `:71-73`. Estat `zoom` `:1009`; `setZoomClamped` `:1064-1066`;
`fitZoomToViewport` `:1067-1072`; `onViewportWheel` (Ctrl+roda) `:1538-1543`; `zoomLabel` `:1800`.
JSX `:1920-1940`: botons − / % / + / 100% / fit (`ti-arrows-maximize`).

**Estat/badges** (tots a la topbar): `lockState` `:996` (`locked = ==='owned'` `:1014`), `saveState`
`:998`, `badge` (IIFE `{text,bg,fg}`) `:1793-1798`, `saveLabel` `:1799`. Pintat: `saveLabel` `:1874`,
`notice` `:1875`, **badge versió+lock** `:1942-1944` (`v{sheet?.versio} · {badge.text}`), overlay
readonly sobre canvas `:1970-1974`.

💡 **No hi ha barra d'estat inferior:** tots aquests indicadors són candidats a migrar a un
`<footer>` nou (zoom a la dreta, save/lock a l'esquerra, com Illustrator).

---

# 6) TOKENS / ESTILS

**Estilització = 100% inline `style={{}}`** (cap classe CSS pròpia; només icones Tabler `ti ti-*`).
Dos canals de paleta:
- **`COL`** (objecte JS DOM, `:43-46`): `sidebar:'#f0dfc0'`, `gold:'var(--gold)'`,
  `goldPale:'#f5e6d0'`, `border:'var(--border)'`, `textMain/textMuted:var(...)`, `bg:'#f5f0e8'` —
  mescla hex literals + CSS vars.
- **`KONVA_COL`** (canvas, `:51`): `white#ffffff, gold#c27a2a, border#e0d5c5, textMain#1d1d1b,
  textMuted#868685` — el canvas no resol `var()`, per això hex literals (comentari `:47-50`).

**Tokens `:root`** (`index.css:3-42`): colors `--gold:#c27a2a`, `--border:#e0d5c5`, `--text-main:
#1d1d1b`, `--text-muted:#868685`, `--bg-muted:#f5f0e8`, `--bg-sidebar:#f0dfc0`, etc.; tipografia
`--fs-caption:8px … --fs-display:32px` (`:35-41`); font global IBM Plex Mono (`index.css:44`,
`FONT` `:42`).

**Paleta actual = CLARA (beix/daurat):** fons app `#faf7f2` (`:1860`), topbar/sidebar `#f0dfc0`,
columnes/viewport `#f5f0e8`, accent daurat `#c27a2a`, `goldPale #f5e6d0` per estats actius, border
`#e0d5c5`, text `#1d1d1b`/muted `#868685`. Destructiu `#e74c3c` (`:2273`).

Objectes-estil "load-bearing": `headerBtn` `:1802-1806`, `propLabel` `:2323`, `propInput` `:2324`,
`SectionTitle` `:2320-2322`.

💡 **Re-tema dark:** com que tot és inline via `COL` + tokens `:root`, **redefinir `COL` (i, si cal,
els tokens `:root`)** propaga la paleta dark al DOM sense tocar el JSX. **`KONVA_COL` es manté
intacte** (el llenç segueix sent paper blanc). Els 4 objectes-estil són el segon punt a re-tematitzar.

---

# 7) MAPA — REAPROFITAR vs REEMPLAÇAR

### ✅ REAPROFITAR (lògica/estat/handlers — sense canvis)
| Què | fitxer:línia |
|---|---|
| Document i selecció: `pages`, `currentPage`, `selectedIds` | `:991,992,993` |
| Mutacions: `updatePageObjects/addObject/updateObject/updateObjects/deleteObject(s)` | `:1037-1058` |
| Selecció: `clearSelection/selectOnly/toggleSelection/handleSelectObject` | `:1063-1077` |
| Transform/canvas: `onStageMouseDown/Move/Up`, `handleDragEnd/TransformEnd` | `:1402-1521` |
| Alinear/distribuir/z-order/agrupar/mirall | `:1114-1206` |
| Inserció: `insertLogo/insertFlatSketch/insertHeader/onAddTableClick/addModelFitxer/createPreset` | `:1084,1563-1735` |
| Vector/text/flat: `editSelectedFlat/startVectorEdit/commitFlatEdit/startTextEdit/commitTextEdit` | `:1528-1650` |
| Zoom: `setZoomClamped/fitZoomToViewport/onViewportWheel` + constants | `:54-73,1064-1072,1538` |
| Estat de col·laboració: `lockState/locked/saveState`, autosave/lock/unlock | `:996,1014,998` |
| Export PDF: `onExport` | `:1752` |
| `tool/setTool` (estat d'eina) + `TOOL_GROUPS` (config) | `:994,1834` |
| Canvas Konva sencer (`ObjectNode`, render, `KONVA_COL`) | (intacte) |

### ♻️ REEMPLAÇAR (presentació)
| Què (avui) | On | Cap a |
|---|---|---|
| Toolbar dropdowns a la topbar | `:1877-1912` | Paleta lateral esquerra (vertical) |
| `openGroup` (estat del dropdown) | `:1011` | (eliminable amb la paleta) |
| Barra de zoom + badge + saveLabel/notice a la topbar | `:1874-1875,1920-1944` | Barra d'estat inferior nova |
| `<select>` format pàgina a la topbar | `:1914-1918` | Barra contextual o dock |
| `<aside>` dret (com a *layout*) | `:2035` | Dock dret re-tematitzat (+ panell Capes); **controls interns es conserven** |
| Columna de pàgines (96px) | `:1949` | Panell del dock o segona columna (cedeix lloc a la paleta d'eines) |
| Objectes-estil + paleta clara (`COL`, `headerBtn`, `propInput`...) | `:43-46,1802,2323-2324` | Tokens/paleta dark |
| `<header>` sense logo | `:1862` | Topbar amb logo d'app |
| (no existeix) | — | Barra d'estat inferior `<footer>` nova |

---

# 💡 PROPOSTA — com encaixar la closca del mockup

1. **Estructura del `return`:** evolucionar de `flex-column [header + main]` a
   `flex-column [topbar(logo) + contextbar? + flex-row(paleta-eines | (pàgines?) | viewport | dock) + statusbar]`.
   Concretament: afegir una **primera columna** dins `<main>` (`:1947`) per a la paleta d'eines, i un
   **`<footer>`** després de `</main>` (`:2281`) per a la barra d'estat.
2. **Paleta d'eines:** reaprofitar `TOOL_GROUPS` (`:1834`) i `setTool` (`:994`) però renderitzar-los
   en vertical (icones amb tooltip), eliminant els dropdowns (`openGroup` deixa de caldre).
3. **Dock dret:** mantenir l'`<aside>` (`:2035`) i els seus blocs de propietats/alinear/z-order tal
   qual; afegir un panell "Capes" alimentat per `ordered`/`pages[currentPage].objects` + el z-order
   existent (`moveSelectionInFreeLayer` `:1114`).
4. **Barra d'estat:** moure zoom (`:1920-1940`), `saveLabel`/`badge` (`:1874,1942`) i `notice` a un
   `<footer>` nou.
5. **Re-tema dark:** redefinir `COL` (`:43`) i, si cal, els tokens `:root` (`index.css`); deixar
   `KONVA_COL` (`:51`) intacte (paper blanc). Re-tematitzar `headerBtn`/`propInput`/`propLabel`/
   `SectionTitle`.
6. **Barra contextual (opcional):** una franja sota la topbar amb les opcions de l'eina/objecte
   actiu, reusant els mateixos controls del dock.

**Cost:** mitjà i de baix risc — és **recablejat de JSX + re-tema**, sense tocar el motor ni la
lògica. El risc viu a (a) reorganitzar les columnes de `<main>` sense trencar el càlcul de zoom/
viewport (`wrapRef`/`viewportRef` `:1021-1022`, `fitZoomToViewport` `:1067`), i (b) la paleta dark al
DOM coexistint amb el canvas blanc (resolt mantenint `KONVA_COL`).

---

# ⚖️ PER DECIDIR (Agus)

1. **Pàgines: on van?** Avui ocupen la columna esquerra (`:1949`). Amb la paleta d'eines a
   l'esquerra, les miniatures passen a (a) un panell del dock dret, (b) una tira inferior horitzontal,
   o (c) una segona columna. Afecta el layout de `<main>`.
2. **Barra contextual sí/no:** afegir la franja d'opcions per-eina sota la topbar, o deixar tots els
   controls al dock dret (menys canvi).
3. **Abast del re-tema dark:** només redefinir `COL`/objectes-estil (DOM dark, canvas blanc) — recomanat
   — o també repintar el "paper" del canvas (implicaria tocar `KONVA_COL` i la sensació de fitxa).
4. **Panell "Capes":** crear-lo ara (reusant z-order existent) o diferir-lo; i si introdueix z-order
   per objecte (avui el z el dicta `layer`+ordre d'array).
5. **Logo d'app a la topbar:** quin asset i si la topbar passa a fosca (coherència amb el dark).

---

*Diagnosi read-only. Cap fitxer de codi tocat. Cap commit, cap push.*
