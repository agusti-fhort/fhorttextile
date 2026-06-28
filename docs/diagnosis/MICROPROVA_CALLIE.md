# MICROPROVA F4 - SVG real CALLIE al PoC Paper.js

Data: 2026-06-28

Àmbit: només PoC aïllat `frontend/src/pages/PaperKonvaPoc.jsx`. No s'ha tocat `TechSheetEditor` ni el flux `.ftt`.

Fitxer provat: `/var/www/ftt-staging/frontend/public/CALLIE.svg`, servit al PoC com `/CALLIE.svg`.

Build verificat: `npm run build` verd.

Nota de prova: l'entorn no tenia navegador headless instal·lat. S'ha intentat instal·lar Chromium via Playwright temporal a `/tmp`, però la instal·lació ha quedat encallada i s'ha aturat. Les dades següents venen d'una prova programàtica amb la mateixa llibreria `paper` del frontend, més `jsdom/canvas` temporal a `/tmp`, executant `project.importSVG`, edició d'un segment i `exportSVG`. Això valida import/export de Paper, però no substitueix una inspecció visual de browser.

## Fitxer d'entrada

- Mida: 310.437 bytes.
- `viewBox`: `0 0 841.9 595.3`.
- `<path>`: 699.
- `<polygon>`: 269.
- `<image>`: 3.
- `<clipPath>`: 14.
- Classes `.st*` detectades al `<style>` intern: 79 aparicions.
- Les 3 imatges són referències externes: `CALLIE-1.png`, `CALLIE-2.png`, `CALLIE-3.png`.
- Aquests 3 PNG no són presents a `frontend/public/`; el SVG no és autònom.

## 1. Càrrega

Resultat Paper:

- `project.importSVG` no peta.
- Temps d'import mesurat: 642,7 ms.
- Items Paper després de la importació:
  - `Path`: 975.
  - `CompoundPath`: 10.
  - `Group`: 13.
  - `Shape`: 1.
  - `Raster`: 0.
- Els 699 paths + 269 polygons entren convertits majoritàriament a paths Paper.

Conclusió: la càrrega és viable a nivell de Paper i no es congela indefinidament; és una operació síncrona d'uns 0,6 s en aquesta prova. Falta confirmació visual en navegador per afirmar "tots els elements apareixen" amb seguretat.

## 2. Estils CSS

Resultat Paper:

- Mostra dels primers 20 paths importats: `fill: #000000`, `stroke: #000000` en tots els casos.
- Les classes `.st0...` del `<style>` intern no queden preservades a l'export.
- L'export resultant té `styleClasses: 0`.

Conclusió: els colors CSS no es conserven en aquesta prova. Cal considerar sanejament previ del SVG, expandint classes CSS a atributs inline (`fill`, `stroke`, `clip-path`, etc.) abans d'importar-lo a Paper.

## 3. clipPath + image

Entrada:

- `clipPath`: 14.
- `image`: 3.

Resultat Paper/export:

- `Raster`: 0 després d'importar.
- Export SVG vàlid, però:
  - `<image>` exportats: 0.
  - `<clipPath>` exportats: 1.
- Els PNG referenciats (`CALLIE-1.png`, `CALLIE-2.png`, `CALLIE-3.png`) no existeixen al `public`, per tant la prova confirma fricció real amb imatges externes.

Conclusió: els 14 `clipPath` i les 3 imatges no sobreviuen import -> export tal com està el fitxer. No trenca Paper, però es perd informació. Això és sanejament necessari abans d'integrar.

## 4. Edició

Prova feta:

- Seleccionat un path editable importat.
- Path seleccionat: 7 segments.
- Mogut el primer node amb `segment.point.add(new Point(8, -6))`.
- Temps d'edició + `view.update()`: 28 ms.

Conclusió: amb aproximadament 975 paths Paper a escena, una edició puntual de node és fluida en aquesta prova. La pregunta de rendiment central surt positiva a nivell Paper: no va a batzegades en el moviment mesurat.

## 5. Export

Resultat:

- Temps d'export: 512,3 ms.
- SVG exportat parsejable amb `DOMParser`: sí.
- Mida exportada: 244.564 bytes.
- El marcador del path editat (`callie-poc-edited`) apareix a l'export: sí.
- Recompte exportat:
  - `<path>`: 964.
  - `<polygon>`: 0, perquè Paper exporta polygons convertits a paths.
  - `<image>`: 0.
  - `<clipPath>`: 1.

Conclusió: l'export és vàlid i conté el canvi geomètric, però no és fidel al SVG original: es perden imatges, gairebé tots els clipPath i les classes CSS.

## Veredicte de viabilitat

Paper.js pot carregar, editar un node i exportar CALLIE sense petar. El rendiment de l'edició puntual és acceptable en la prova mesurada.

La fricció real no és el volum de paths; són fidelitat i sanejament:

- CSS intern amb classes `.st*` no resolt/preservat.
- Imatges externes no disponibles i no exportades.
- `clipPath` no preservats de forma fidel.
- Export estructuralment vàlid però simplificat i no equivalent a l'original.

Recomanació: no integrar encara al flux `.ftt`. Si es vol continuar, el següent pas ha de ser una fase de sanejament SVG abans de Paper: assets d'imatge resolts o incrustats, CSS inline, i decisió explícita sobre si `clipPath` és imprescindible o acceptablement degradable.
