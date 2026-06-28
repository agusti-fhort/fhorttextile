# MICROPROVA F4 - SVG real CALLIE al PoC Paper.js

Data: 2026-06-28

Àmbit: només PoC aïllat `frontend/src/pages/PaperKonvaPoc.jsx`. No s'ha tocat `TechSheetEditor` ni el flux `.ftt`.

## Estat

Bloquejada per absència del fitxer real de prova.

S'ha buscat `CALLIE.svg` / `*callie*.svg` sota `/var/www/ftt-staging` i no existeix. També `/var/www/ftt-staging/media/` no existeix en aquest workspace.

S'ha afegit al PoC una opció de càrrega real per `project.importSVG`:

- Botó `Carregar CALLIE`, que intenta carregar `/media/CALLIE.svg`.
- Selector `Triar SVG`, per carregar manualment un `.svg` i importar-ne el text amb `project.importSVG`.
- Panell de mètriques amb recompte d'entrada, temps d'import, elements Paper, mostra de colors, temps d'edició, temps d'export i validesa de l'export.
- Botó `Moure node prova`, que mou el primer node del path seleccionat i marca el path com `callie-poc-edited` per comprovar que el canvi arriba a l'export.

Build verificat: `npm run build` verd.

## 1. Càrrega

No executada sobre CALLIE real.

Fet constatable: el PoC ja té camí de càrrega per `project.importSVG`, però el fitxer `/var/www/ftt-staging/media/CALLIE.svg` no és present, així que no hi ha temps d'import real ni comprovació visual honesta sobre els aproximadament 970 elements esperats.

## 2. Estils CSS

No executat sobre CALLIE real.

La instrumentació compta classes `.st*` al text original i mostra una mostra de `fillColor`/`strokeColor` dels primers paths importats per confirmar si Paper resol els colors del `<style>` intern o si queden negres/sense fill. Sense el fitxer real no es pot concloure si cal sanejament de CSS.

## 3. clipPath + image

No executat sobre CALLIE real.

La instrumentació compta `<clipPath>` i `<image>` a l'entrada i a l'export, i valida que l'export sigui SVG parsejable. Sense el fitxer real no es pot confirmar si els 14 `clipPath` i les 3 imatges sobreviuen import -> export.

## 4. Edició

No executada sobre CALLIE real.

El PoC inclou el botó `Moure node prova` per moure un node d'un path seleccionat i mesurar la durada amb l'escena carregada. Sense CALLIE no es pot respondre la pregunta de rendiment amb aproximadament 970 elements a escena.

## 5. Export

No executat sobre CALLIE real.

El PoC exporta el layer Paper, valida l'SVG amb `DOMParser`, recompte `<path>`, `<polygon>`, `<image>` i `<clipPath>`, i comprova que aparegui `callie-poc-edited` quan s'ha fet la prova de moviment de node. Sense CALLIE no es pot confirmar que el resultat real sigui vàlid ni que contingui el canvi.

## Conclusió

No hi ha green gate de viabilitat encara perquè falta l'input real. El PoC està preparat per fer la microprova quan `CALLIE.svg` estigui disponible; cal repetir-la amb el fitxer real i substituir aquest document pels resultats mesurats.
