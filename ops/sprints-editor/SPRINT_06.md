# SPRINT 06 — Vectorial 1: fill per subpath (Ruta B) + forats evenodd a l'import
FRONTEND only. Depèn de S0. Referència: DIAGNOSI Bloc 5 (§17-22).

## Fets verificats (no re-descobrir)
- Cada subpath ja es renderitza com a Konva.Path fill propi dins el Group; el JSON ja
  porta fill/fillRule per entrada de paths[]; live==export via pathChildProps.
- El clic als fills bombolleja al Group (selecció sempre objecte sencer).
- Els forats es perden a l'IMPORT (legacySketchSvgToPath/getItems aplana els fills de
  CompoundPath com a germans sòlids) — el render és innocent.

## Abast
1. SELECCIÓ DE SUBPATH: amb un path seleccionat, segon clic (o doble clic modificador
   Alt) sobre una peça = subpath actiu (índex); realç visual (vora gold). Escape/clic
   fora = tornar a objecte sencer.
2. FILL PER PEÇA: amb subpath actiu, el panell fill/stroke i el ColorPicker apliquen a
   paths[i].fill (no a l'objecte). Sense subpath actiu = comportament actual (tot).
   Història: cada canvi = entrada.
3. FORATS: al pas d'import (legacySketchSvgToPath / recorregut getItems), NO aplanar
   els CompoundPath: agrupar exterior+interiors en UNA entrada de paths[] amb
   fillRule:'evenodd' i subpaths concatenats al data del Konva.Path (el render ja
   respecta fillRule — verificat §19). Els paths simples queden com ara.
4. Retrocompatibilitat: flats ja importats (438 subpaths germans) no canvien.

## Porta verda
Importar SVG de prova amb 3 peces i 1 forat (crear-lo al sprint com a fixture):
cada peça es pinta d'un color diferent per clic; el forat es veu buit (live i PDF).
Roundtrip pel PaperFlatEditor conserva fills i forat. Build net.

## Commits: 1. selecció subpath + fill dirigit · 2. import CompoundPath/evenodd.
