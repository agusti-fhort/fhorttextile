> ⚠️ SUPERADA 2026-07-07 — implementada (fix zoom re-pinta Stage, commit eaf4e43). Consulta només com a històric.

# DIAGNOSI — Qualitat de render del canvas (pixelRatio) a l'editor de fitxa

> Patró A, **READ-ONLY absolut**. Cap canvi, cap commit, cap push. `/var/www/ftt-staging/frontend`.
> FETS amb `fitxer:línia`. Idees com `💡`. Decisions = de l'Agus (`⚖️`). Data: 2026-06-28.
> Fitxer: `src/pages/TechSheetEditor.jsx`.

**Símptoma (Agus, pantalla Retina/alta resolució):** el render del canvas es veu BRUT/baixa
resolució, com pixelat, tot i que la GEOMETRIA és correcta (l'export surt net i fidel). Problema
de PANTALLA, no de geometria.

---

## RESUM EXECUTIu

- **Causa principal CONFIRMADA: el zoom és un `transform: scale(zoom)` de CSS sobre el bitmap del
  canvas ja rasteritzat** ([:1972](../../frontend/src/pages/TechSheetEditor.jsx#L1972)), amb el
  `<Stage>` fixat a `pageW×pageH` ([:1973](../../frontend/src/pages/TechSheetEditor.jsx#L1973)).
  El canvas es pinta a la resolució de zoom=1 i, en ampliar amb CSS, s'estira el bitmap → borrós a
  >100%. Com més zoom, més brutícia.
- **NO és un `pixelRatio` fix a 1:** no hi ha cap `Konva.pixelRatio` global enlloc; el Stage viu usa
  el `devicePixelRatio` per defecte → a zoom=1 és nítid en Retina. La brutícia apareix en fer zoom.
- L'**export és nítid** perquè usa un stage offscreen amb `pixelRatio` explícit alt (3.5), no el CSS
  transform → coherent amb "l'export surt net".
- Els `path` natius (`Konva.Path`) es pinten vectorialment (nítids); el que perd nitidesa són els
  **rasters**: `image` (inherent) i qualsevol `sketch_svg` llegat encara rasteritzat.
- **Rectangle invisible** (símptoma secundari): el rect nou té **fill transparent + traç gold 1px**,
  i només es crea si el drag supera `w>3 && h>3` px; un clic/drag petit no crea res.

---

# 1) PIXELRATIO de Konva

- **Stage viu (interactiu):** `<Stage ref={stageRef} width={pageW} height={pageH} …>` —
  [:1973](../../frontend/src/pages/TechSheetEditor.jsx#L1973). **Cap `pixelRatio` ni `scale`
  explícits.** Konva, per defecte, crea el backing-store del canvas a
  `width × window.devicePixelRatio` → a zoom=1 el render és a resolució Retina (nítid).
- **Cap `Konva.pixelRatio` global** a tot `src/` (grep `pixelRatio`/`devicePixelRatio` només troba
  els usos d'export). → no s'ha forçat enlloc un pixelRatio=1.
- **Export/miniatures:** `renderPageToDataURL(page, pixelRatio, ctx)`
  ([:686](../../frontend/src/pages/TechSheetEditor.jsx#L686)) crea un stage **offscreen** i fa
  `stage.toDataURL({ pixelRatio, mimeType:'image/png' })` ([:700](../../frontend/src/pages/TechSheetEditor.jsx#L700)).
  Call-sites: export PDF a **pixelRatio 3.5** ([:1761](../../frontend/src/pages/TechSheetEditor.jsx#L1761)),
  miniatures a **0.18** ([:1355](../../frontend/src/pages/TechSheetEditor.jsx#L1355)). → l'export va a
  alta resolució (nítid), aliè al problema de pantalla.

**FET:** la qualitat del Stage viu NO està limitada per un pixelRatio fix; està limitada pel
**mecanisme de zoom** (punt 2).

---

# 2) EL ZOOM I LA RESOLUCIÓ — causa principal

- **El zoom és CSS, no re-render.** `wrapRef`:
  `style={{ width: pageW, height: pageH, transform: \`scale(${zoom})\`, transformOrigin: 'top left', … }}`
  — [:1972](../../frontend/src/pages/TechSheetEditor.jsx#L1972). El `<Stage>` interior es manté a
  `pageW×pageH` fix ([:1973](../../frontend/src/pages/TechSheetEditor.jsx#L1973)); **no rep
  `scaleX/scaleY` ni canvi de `width/height`** amb el zoom.
- **Conseqüència (FET de comportament):** el canvas es rasteritza una sola vegada a la resolució de
  zoom=1 (= `pageW × devicePixelRatio` device-px). El `transform: scale(zoom)` amplia aquest bitmap
  ja rasteritzat:
  - a **zoom = 1** → nítid (resolució Retina nativa).
  - a **zoom > 1** → el bitmap s'estira; el detall efectiu = `devicePixelRatio / zoom` device-px per
    CSS-px. A zoom 2 en pantalla 2x cau a ~1x (es perd el Retina); a zoom 3–4 es veu clarament
    pixelat/borrós. **Aquesta és la brutícia que reporta l'Agus.**
  - a **zoom < 1** → es redueix el bitmap (no es nota).
- El zoom es controla amb `setZoomClamped` (Ctrl+roda `onViewportWheel`
  [:1537+](../../frontend/src/pages/TechSheetEditor.jsx#L1537), botons +/−/fit a la barra d'estat) i
  s'aplica NOMÉS via aquest `transform`.

**💡 CONFIRMAT:** el zoom per CSS transform és la causa principal de la brutícia. No hi ha
re-pintat del canvas a la nova escala; s'escala el bitmap.

---

# 3) SKETCH / IMATGE rasteritzada

- **`path` (vector natiu, NÍTID):** `PathObj` pinta amb `<Path>` de Konva directament, sense `cache()`
  ni `toImage` — [:740-749](../../frontend/src/pages/TechSheetEditor.jsx#L740-L749). Es rasteritza al
  backing-store del Stage (a devicePixelRatio) → nítid a zoom=1; pateix el mateix CSS-scaling a
  zoom>1 (punt 2), però NO té cap pèrdua extra per rasterització intermèdia. Props de pintura:
  `pathChildProps` ([:187](../../frontend/src/pages/TechSheetEditor.jsx#L187), branca export
  [:637](../../frontend/src/pages/TechSheetEditor.jsx#L637)).
- **`sketch_svg` (LLEGAT, RASTERITZAT):** `SketchSvgObj` converteix el string SVG a data-URL i el
  pinta com a **`<KonvaImage>`** — [:728-736](../../frontend/src/pages/TechSheetEditor.jsx#L728-L736)
  (`useImage(svgDataUrl(obj.svg))`). Això **sí** perd nitidesa (bitmap a mida natural, després
  escalat). PERÒ és llegat: hi ha `convertLegacySketchSvgObject`
  ([:976](../../frontend/src/pages/TechSheetEditor.jsx#L976)) que el converteix a `type:'path'`
  ([:941](../../frontend/src/pages/TechSheetEditor.jsx#L941)) en obrir-lo; els flats nous neixen com
  a `path` ([:1573](../../frontend/src/pages/TechSheetEditor.jsx#L1573)).
- **`image` (raster inherent):** `ImageObj`/`imageProps` → `<KonvaImage>`
  ([:716-724](../../frontend/src/pages/TechSheetEditor.jsx#L716-L724),
  [:571](../../frontend/src/pages/TechSheetEditor.jsx#L571)). És un bitmap per naturalesa; la seva
  nitidesa depèn de la resolució de la font, no del motor.

**FET:** els vectors (`path`, `rect`, `ellipse`, `line`, `arrow`, `text`) són tots Konva natius
(nítids al backing-store). Els únics que perden detall per rasterització pròpia són `image`
(inherent) i `sketch_svg` llegat (no convertit). Cap d'aquests és la causa GENERAL de la brutícia
(que afecta tot el canvas) — la causa general és el punt 2.

---

# 4) RECTANGLE INVISIBLE (símptoma secundari)

- **Creació** (`onStageMouseUp`): un rect nou es crea NOMÉS si `w > 3 && h > 3` (px de stage), amb
  `fill: 'transparent', stroke: KONVA_COL.gold (#c27a2a), strokeWidth: 1` —
  [:1512](../../frontend/src/pages/TechSheetEditor.jsx#L1512). Un clic o drag ≤3px **no crea res**
  (i `setTool('select')` només es dispara si s'ha creat objecte → l'eina es queda a `rect`).
- **Render** (`rectProps`): `fill: obj.fill && obj.fill !== 'transparent' ? obj.fill : undefined`
  (transparent → SENSE emplenat), `stroke: obj.stroke || gold, strokeWidth: obj.strokeWidth || 1` —
  [:498-500](../../frontend/src/pages/TechSheetEditor.jsx#L498-L500). → el rect nou és un **contorn
  gold de 1px sense cos**.

**💡 HIPÒTESI (símptoma secundari):** el rect "no es veu" per la combinació de:
1. **Llindar `w>3 && h>3`** ([:1512](../../frontend/src/pages/TechSheetEditor.jsx#L1512)): un drag
   curt no crea res → l'usuari creu que ha dibuixat però no hi ha objecte. És la causa més probable
   de "no apareix".
2. **Fill transparent + traç 1px**: encara que es creï, és un contorn fi sense cos; a zoom<1 el traç
   d'1px pot quedar sub-píxel, i amb la brutícia del punt 2 es perd visualment. Un cop el render
   sigui nítid i/o el traç tingui més pes, es veu clarament.

---

# 💡 CAUSA PROBABLE + CORRECCIÓ MÍNIMA (per causa)

### Causa A (principal) — zoom per CSS transform escala el bitmap
**Correcció mínima recomanada:** que el zoom **re-pinti** el Stage a la nova escala en comptes
d'escalar el bitmap. Dues vies:
- **A1 (Konva-natiu, neteja màxima):** posar `scaleX={zoom} scaleY={zoom}` al `<Stage>` i
  `width={pageW*zoom} height={pageH*zoom}`, i **treure** el `transform: scale(zoom)` del `wrapRef`
  (dimensionar-lo a `pageW*zoom × pageH*zoom`). Konva re-rasteritza els vectors a la mida de zoom ×
  devicePixelRatio → **nítid a qualsevol zoom**.
  ⚠️ Cal ajustar el mapeig de coordenades del ratolí: amb el Stage escalat, `getPointerPosition()`
  retorna coords en l'espai escalat; el càlcul `toMm` (dibuix/hit) ha de dividir per `zoom`. És el
  punt de risc/feina d'aquesta via (avui el CSS transform ho amaga perquè Konva ja compensa el
  bounding-rect).
- **A2 (mínim risc, sense tocar coordenades):** mantenir el CSS transform per al layout però **pujar
  el pixelRatio del canvas viu** proporcionalment al zoom (p.ex. `devicePixelRatio * clamp(zoom,1,…)`)
  i re-dibuixar en canviar el zoom, perquè el bitmap tingui prou detall per a l'ampliació. No canvia
  el sistema de coordenades; cost de memòria creix amb el zoom (acotar el màxim). L'API exacta de
  Konva (pixelRatio per Layer/canvas) es concreta a la fase d'implementació.

💡 Recomanació: **A1** si es vol la solució correcta i duradora (vectors sempre nítids, com
Illustrator) assumint l'ajust de coordenades; **A2** com a pegat ràpid de baix risc si es vol
millorar la nitidesa sense tocar el mapeig de coordenades.

### Causa B — rasters (`image`, `sketch_svg` llegat)
**Correcció mínima:** assegurar la conversió de tot `sketch_svg` llegat a `path`
(`convertLegacySketchSvgObject` ja existeix [:976](../../frontend/src/pages/TechSheetEditor.jsx#L976));
verificar que s'aplica en carregar a tots els casos). Les `image` són raster per naturalesa (no hi
ha correcció de motor; depèn de la font). No és la causa general.

### Causa C — rectangle invisible
**Correcció mínima:** (i) reduir/eliminar el llindar `w>3 && h>3` o donar feedback quan el drag és
massa petit ([:1512](../../frontend/src/pages/TechSheetEditor.jsx#L1512)); i/o (ii) donar al rect nou
un valor per defecte més visible (p.ex. traç una mica més gruixut, o un emplenat subtil). Un cop
resolta la causa A, el contorn gold d'1px ja es veu nítid.

---

# ⚖️ PER DECIDIR (Agus)

1. **Via del zoom nítid:** A1 (Konva-natiu, vectors sempre nítids; cal ajustar el mapeig de
   coordenades ratolí→mm dividint per zoom) **vs** A2 (pujar pixelRatio amb el zoom; sense tocar
   coordenades; més memòria a zoom alt). A1 és la solució "de debò"; A2 és el pegat ràpid.
2. **Rectangle invisible:** ajustar només el llindar de creació, o també el valor per defecte del rect
   nou (traç/emplenat més visibles)?
3. **Rasters llegats:** forçar la conversió `sketch_svg → path` en carregar com a política (perquè cap
   document no es quedi amb el camí rasteritzat), o deixar-ho com està (els nous ja són `path`)?

---

*Diagnosi read-only. Cap fitxer de codi tocat. Cap commit, cap push.*
