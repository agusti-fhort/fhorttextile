# PoC Paper.js + Konva — Fase 4 gate

Data: 2026-06-27  
Abast: prova aillada a frontend, sense integrar a `TechSheetEditor.jsx` ni tocar el flux `.ftt`.

## Veredicte

**SI, AMB CONDICIONS.** Paper.js pot conviure amb l'editor Konva com a mode/capa d'edicio vectorial, pero la integracio real hauria de tractar explicitament coordenades responsive, ownership d'esdeveniments i el pas Paper.js -> SVG -> asset del `.ftt`.

## Fets de la PoC

- Dependencia instal·lada: `paper@0.12.18` a `frontend/package.json:25`.
- Pes observat:
  - paquet local `node_modules/paper`: ~13M.
  - chunk aillat final `PaperKonvaPoc`: 362.49 kB minificat / 122.96 kB gzip en `npm run build`.
  - el build tambe separa un chunk `ReactKonva`: 306.53 kB minificat / 93.27 kB gzip.
- Ruta aillada: `/disseny/poc-paper`, dins el Shell i sense entrada de menu (`frontend/src/App.jsx:38`, `frontend/src/App.jsx:220`).
- No s'ha tocat `TechSheetEditor.jsx`.
- La PoC importa un SVG simple intern amb `project.importSVG(...)` (`frontend/src/pages/PaperKonvaPoc.jsx:10`, `frontend/src/pages/PaperKonvaPoc.jsx:75`).
- L'edicio de nodes funciona sobre un `Path`: punts d'ancoratge i nanses Bezier es pinten en una capa UI separada (`frontend/src/pages/PaperKonvaPoc.jsx:85-119`).
- Afegir punt: `path.getNearestLocation(...)` + `path.insert(...)` (`frontend/src/pages/PaperKonvaPoc.jsx:127-137`).
- Esborrar punt: elimina segment si el path conserva minim 2 punts (`frontend/src/pages/PaperKonvaPoc.jsx:139-146`).
- Moure node/nansa: `Tool.onMouseDrag` modifica `segment.point`, `segment.handleIn` o `segment.handleOut` (`frontend/src/pages/PaperKonvaPoc.jsx:171-182`).
- Export SVG: s'exporta la capa de sketch, no la capa UI de handles (`frontend/src/pages/PaperKonvaPoc.jsx:200-205`).
- Coexistencia Konva/Paper: la PoC renderitza un `Stage` Konva sota el canvas Paper (`frontend/src/pages/PaperKonvaPoc.jsx:268-280`) i posa el canvas Paper com overlay absolut (`frontend/src/pages/PaperKonvaPoc.jsx:281-293`).
- Ownership d'esdeveniments: `pointerEvents: paperActive ? 'auto' : 'none'` permet alternar entre "Paper captura" i "Konva rep events" (`frontend/src/pages/PaperKonvaPoc.jsx:290`).
- Coordenades: s'ha usat la mateixa base `96 / 25.4` per mm<->px (`frontend/src/pages/PaperKonvaPoc.jsx:6-8`) i la UI mostra el punt Paper convertit a mm (`frontend/src/pages/PaperKonvaPoc.jsx:295-298`).

## Que funciona

- Paper.js carrega en Vite i queda en chunk lazy separat de la resta de l'app.
- Paper.js permet importar SVG, editar segments i handles, afegir/esborrar punts i exportar SVG modificat.
- El model overlay es viable: en mode Paper, Paper captura els events; en mode pass-through, Konva els rep.
- El z-index es simple si Paper viu com a overlay d'edicio temporal damunt Konva.

## Que frega

- Coordenades responsive: la PoC te canvas intern `760x360` i CSS fluid. Si el contenidor s'escala, caldria una capa formal de transformacio viewport<->paper<->mm, probablement amb `ResizeObserver`.
- Esdeveniments: no convé tenir Paper i Konva actius alhora sobre el mateix gest. La integracio hauria de ser un mode explicit: o edites vector amb Paper, o manipules objectes Konva.
- Export: el cami net es coure el resultat Paper.js a SVG i persistir-lo com asset/objecte image/vector dins el document `.ftt`; Paper no hauria de quedar com a runtime necessari per renderitzar fitxes normals.
- Handles UI: cal excloure sempre la capa UI de l'export. La PoC ho fa exportant nomes `sketchLayer`, pero la integracio haura de mantenir aquesta frontera.
- Sketch real: no s'ha trobat cap SVG real de sketch/patro al repo o media; hi ha un DXF (`backend/media/import_sessions/2026/06/AMELIA_AZUL_prova.DXF`), pero Paper.js no l'importa directament com SVG. Falta prova amb un SVG real de volum comparable.

## Decisio suggerida

**Go condicionat** per continuar F4 si Agus accepta aquestes condicions:

1. Paper.js entra nomes com a mode d'edicio vectorial, no com a substitut del renderer Konva de fitxa.
2. El resultat final del mode Paper es desa com SVG/asset del `.ftt`.
3. Abans d'integrar a `TechSheetEditor.jsx`, cal una microprova amb un SVG real exportat des de l'origen de sketch/DXF.
4. La integracio real ha de tenir una funcio unica de conversio mm<->px compartida amb l'editor.
