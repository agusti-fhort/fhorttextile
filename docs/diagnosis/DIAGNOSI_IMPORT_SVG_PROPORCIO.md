# DIAGNOSI — IMPORT SVG: PROPORCIÓ + EDITABILITAT

> **Patró A quirúrgic (read-only).** Cap canvi de codi. Cas de prova real:
> `L27WKG0612_VEGA-3.svg` (LOSAN), a
> `backend/media/fhort/model_fitxers/2026/07/L27WKG0612_VEGA-3.svg`.
> **Data:** 2026-07-26. **Fitxer:** `viewBox="0 0 777.14 416.84"` SENSE `width`/`height`
> (export Illustrator responsive), 806 `<path>`, 1 `<clipPath>`, 4 `<linearGradient>`,
> 1 bloc `<style>` CSS, transforms, `stroke-dasharray`. 92.876 bytes.

---

## RESUM EXECUTIU

**La proporció es trenca per un ESCALAT NO UNIFORME.** La mida de la caixa de l'objecte
es calcula amb la ràtio del **viewBox** (1,864), però el contingut s'hi encaixa amb
`scaleX`/`scaleY` **independents** derivats de la bounding-box del **contingut real**
(`imported.bounds`, ràtio 2,326 en aquest fitxer, perquè el dibuix ocupa només el 80%
vertical del viewBox). Resultat: el croquis s'estira verticalment ×1,247 (o s'aprima
horitzontalment al 80%). No és raster ni està locked: és un **únic objecte `path`
monolític** amb ~806 subpaths, amb els degradats i el clip aplanats.

---

## Q1 — PROPORCIÓ (el crític)

### Cadena traçada (fitxer:línia)

1. **`svgAspectRatio(svgText)`** — `TechSheetEditor.jsx:205-217`. Llegeix el `viewBox`
   PRIMER (`:210-212`): `777.14 / 416.84 = 1,8644`. ✅ La ràtio d'origen és CORRECTA (usa el
   viewBox; el `width`/`height` absents no importen).
2. **`importFlatSvgText(svgText)`** — `TechSheetEditor.jsx:3620-3651`. Dimensiona la caixa de
   l'objecte dins un marc `maxW=110 · maxH=78` (`:3627-3630`):
   `ratio(1,864) ≥ maxW/maxH(1,410)` → `width = 110`, `height = 110/1,864 = 59,0`.
   → **caixa objecte = 110 × 59,0 mm, ràtio 1,864** (= viewBox). Fins aquí, correcte.
3. **`legacySketchSvgToPath(obj, scope)`** — `TechSheetEditor.jsx:1798-1869`. AQUÍ es trenca:
   - `bounds = imported.bounds` (`:1807`) = extensió del **contingut real** importat, NO el
     viewBox.
   - `scaleX = width / bounds.width` · `scaleY = height / bounds.height` (`:1811-1812`) →
     **dos factors independents**.
   - `mapSegs` aplica `(x·scaleX, y·scaleY)` (`:1814-1821`) i resta `bounds.x/bounds.y` (retalla
     el marge buit del viewBox).

### Reproducció amb el fitxer (mesures reals)

Render determinista del SVG a escala viewBox (cairosvg → PIL `getbbox`, còpia del que fa
`imported.bounds`):

| Magnitud | Valor | Ràtio |
|---|---|---|
| viewBox | 777,14 × 416,84 | **1,864** |
| **Contingut real** (bbox no-transparent) | 777 × **334** | **2,326** |
| Caixa objecte (pas 2) | 110 × 59,0 | 1,864 |
| `scaleX` | 110/777 = **0,1416** | — |
| `scaleY` | 59/334 = **0,1766** | — |

**Distorsió = `scaleY / scaleX` = 1,247** → el croquis s'estira **verticalment un 24,7%**
(equivalent: horitzontal comprimit al 80,1%). El dibuix ocupa tot l'ample del viewBox però
només el 80% de l'alçada (hi ha ~83 px de marge inferior buit a l'artboard d'Illustrator);
aquest marge fa que `bounds` (2,326) divergeixi del viewBox (1,864), i l'escalat no uniforme
converteix aquesta divergència en deformació.

**Hi ha fit-a-marc que escala eixos per separat?** SÍ: `legacySketchSvgToPath:1811-1812`.
És exactament el `scaleX ≠ scaleY`. La caixa es dimensiona amb el viewBox però el contingut
s'hi encaixa amb la bbox pròpia → sempre que el contingut no ompli el viewBox, deformació.

---

## Q2 — CAMÍ D'IMPORT

- **Camí VECTORIAL (no raster).** `importFlatSvgText` crea un `sketch_svg` transitori
  (`:3645-3649`) i el converteix immediatament amb `convertLegacySketchSvgObject` →
  `legacySketchSvgToPath`, que retorna `type: 'path'` (`:1858-1868`). El tipus legacy
  `sketch_svg` (que SÍ rasteritza, `SketchSvgObj`) **no** és el resultat final: només és
  l'embolcall transitori. Per tant **entra pel camí path vectorial**.
- **806 `<path>` → 1 SOL objecte `path` monolític.** `collect` (`:1823-1830`) recorre l'arbre
  Paper i acumula cada `Path`/`CompoundPath` en un array `paths[]` d'UN sol objecte
  (`:1831-1856`). `expandShapes:true` (`:1803`) converteix qualsevol `<rect>`/`<circle>` a
  path. Els ~806 traços sobreviuen com a subpaths, però **tots dins un únic objecte**.
- **`clipPath` (1): semàntica PERDUDA.** Paper importa el clip com un grup amb màscara; el
  `collect` recull la Path-màscara com un traç normal més (artefacte), i el render Konva
  (`paths[]`) **no aplica cap clip** → el que el clip amagava pot fer-se visible, o apareix la
  forma de la màscara com un rectangle sobrer.
- **`linearGradient` (4): fills PERDUTS.** `paperColorToCss(color, fallback)` (`:1737-1743`)
  fa `color.toCSS(true)` dins un `try/catch`; per a un fillColor de tipus gradient, `toCSS`
  llança o no aplica → retorna `fallback = null`. Els traços amb ompliment degradat queden
  **sense fill** (`:1839`, `:1851`). Aplanament visual.
- **`transforms` (4): APLICATS.** `importSVG` els cou dins les coordenades dels punts en
  importar → es respecten (bé).
- **`stroke-dasharray`: PERDUT.** La conversió no llegeix cap `dash` de l'SVG; els traços
  discontinus surten continus. Menor.
- **Estils `<style>` CSS (classes `.cls-*`):** `inlineSvgClassStyles` (`:1759`) els inlina als
  atributs abans d'importar (Paper no resol classes CSS) → els `fill:none`/`stroke:#1e1e1c`
  per classe SÍ arriben. Bé.
- **Temps d'import / mida objecte:** no mesurat a navegador (Konva/Paper són browser-only; el
  repro headless de Paper falla per manca de `DOMParser`/jsdom, no és un problema real de
  l'app). Qualitativament: 806 subpaths en un objecte = càrrega d'import notable però única;
  l'objecte resultant és 1 `path` amb `paths.length ≈ 806`.

---

## Q3 — EDITABILITAT (diagnòstic, sense arreglar)

Què percep l'usuari com a "restringit":

- **NO és locked** (`layer: 'free'`, com qualsevol objecte importat).
- **NO és raster** — és vectorial (`type: 'path'` amb 806 subpaths bézier).
- **ÉS un únic objecte `path` monolític.** Seleccionar-lo selecciona els 806 traços de cop;
  no es poden agafar/moure/esborrar/repintar peces individuals del croquis com a objectes
  separats. L'edició de nodes (`PaperFlatEditor`, mode fletxa blanca) treballa un subpath
  alhora (`activeSubpath`), però tot segueix sent **un sol objecte** → sensació de "bloc únic".
- **Fidelitat visual degradada** (reforça la percepció d'import dolent): degradats desapareguts
  (Q2), possible artefacte/clip perdut, dasharray perdut. Sumat a la **deformació** de Q1, el
  resultat "no s'assembla" a l'SVG original.

Resum: la "restricció" percebuda = **monolitisme** (1 objecte per 806 traços) + **deformació**
(Q1) + **aplanament** de degradats/clip. Cap gate de `locked`/`layer` ni raster ho causa.

---

## RECOMANACIÓ DE FIX MÍNIM — PROPORCIÓ (separada de l'editabilitat)

L'arrel és l'escalat no uniforme referit a `imported.bounds` en comptes del **viewBox**.
Dues variants; la deformació es cura en totes dues fent l'escalat **uniforme**.

### Opció A (RECOMANADA) — escalar pel viewBox, marc preservat → ràtio 1,864 (l'esperada)
A `legacySketchSvgToPath` (`:1807-1821`), usar el **viewBox** com a referència d'escala i
d'origen, no la bbox del contingut:
- Passar el viewBox (ja disponible: `importFlatSvgText` té l'`svgText`; parsejar-lo amb el
  mateix `DOMParser` de `svgAspectRatio`, o reutilitzar-ne els 4 nombres).
- `scale = width / viewBox.w` (== `height / viewBox.h`, perquè la caixa ja té la ràtio del
  viewBox) → **un sol factor, uniforme**.
- Restar `viewBox.x / viewBox.y` (no `bounds.x/bounds.y`) → conserva la posició del contingut
  dins el marc (el marge inferior es manté, com es veu l'SVG a un navegador).
- `strokeScale = scale`.

Resultat per al fitxer: objecte **110 × 59** (ràtio **1,864**), croquis SENSE deformar,
ocupant el 80% superior + marge inferior — idèntic a com renderitza l'SVG. Coincideix amb
l'"esperada: ràtio 1,864".

### Opció B (mínima absoluta, distorsió-only) — escalat uniforme a contingut → ràtio 2,326
Canviar només `:1811-1813`:
```
const scale = Math.min(width / bounds.width, height / bounds.height)
const scaleX = scale, scaleY = scale       // + strokeScale = scale
```
Cura la deformació sense parsejar el viewBox, però **retalla el marge** i l'objecte queda amb
la ràtio del CONTINGUT (2,326), no la del viewBox (1,864). Més senzill, però NO coincideix amb
l'"esperada 1,864".

### 🚩 PREGUNTA PATRÓ C (decisió de producte, no de codi)
**Retallar al contingut (Opció B, 2,326) o preservar el marc del viewBox (Opció A, 1,864)?**
La primera és més compacta a la fitxa; la segona respecta l'enquadrament de l'Illustrator i la
ràtio que l'usuari espera. Totes dues eliminen la deformació. Recomanació: **A**.

> ⚠️ Ambdues variants afecten TOTS els imports SVG, no només aquest fitxer. Per a SVG on el
> contingut JA omple el viewBox (`bounds ≈ viewBox`), el resultat és idèntic a l'actual (cap
> regressió). La millora només actua quan hi ha marge — que és el cas dels exports Illustrator
> responsive com aquest.

**Editabilitat (Q3) — FORA d'aquest fix mínim.** Trencar el monolit en N objectes (un per
`<g>`/peça) o preservar degradats/clip és una millora separada, més gran, que NO s'ha de barrejar
amb la correcció de proporció. S'anota, no es dimensiona aquí.

---

*Diagnosi read-only. Cap codi tocat. Números de línia del HEAD `aa99a74` (branca `dev`) el
2026-07-26. Mesures de contingut via render cairosvg+PIL (determinista, còpia de `imported.bounds`).*
