# DIAGNOSI — Edició vectorial COMPLETA (estil Illustrator) sobre l'SVG de la fitxa tècnica

Data: 2026-07-20 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
Abast: auditar, fila a fila, la matriu de 17 capacitats d'edició vectorial que demana l'Agus, contra el
codi real de juliol (`TechSheetEditor.jsx` 5073 línies · `PaperFlatEditor.jsx` · `ftt/paperbool.js`) i
l'estat canònic `ops/sprints-editor/SPRINT_EDITOR_ESTAT.md`.
Convenció: cada afirmació porta `fitxer:línia`. `"NO EXISTEIX"` = confirmat absent al codi (grep), no
especulat. Rutes relatives a `frontend/src/pages/` tret que s'indiqui.

> **Nota de fonts.** El catàleg de disseny del juny (`CATALEG_EINES_EDITOR`) **NO és al repo** (viu al
> vault extern) — el mapa d'intencions no s'ha pogut obrir aquí; es contrasta contra la **realitat** de
> juliol: el codi + `SPRINT_EDITOR_ESTAT.md` (S0→S9 + 6 post-runs). `TallerPatro.jsx` **NO comparteix**
> cap peça d'aquesta edició vectorial (grep de `PaperFlatEditor`/`paperbool`/`node`/`subpath` = buit): és
> una superfície separada (motor de patrons), **fora d'abast** d'aquesta matriu.

---

## Resum executiu

1. **L'arquitectura és Konva (llenç viu) + Paper.js (dos rols).** El model d'objecte és `type:'path'` amb
   un array `paths[]`; cada entrada és SIMPLE (`segments`) o COMPOSTA (`subpaths[]` amb `fillRule:'evenodd'`,
   model S6, `TechSheetEditor.jsx:993-994,1022-1024`). Paper.js s'usa (a) offscreen per a les **booleanes**
   (`ftt/paperbool.js`) i (b) com a **sub-editor de nodes** modal (`PaperFlatEditor.jsx`).
2. **L'SVG importat entra com UN sol objecte monolític** `type:'path'` amb tots els traços a `paths[]`
   (`TechSheetEditor.jsx:1632-1678`). Els **subpaths es preserven** (compostos→`subpaths[]` evenodd). Aquesta
   granularitat (fila 17) és el que fa possibles les files de subpath (13,15) i el que bloqueja les de
   node/segment fins que hi hagi un editor de nodes complet.
3. **El gruix del que demana l'Agus (Illustrator complet) NO EXISTEIX.** De les 17 files: **5 EXISTEIXEN**
   (1 esborrar objecte · 4 ploma · 13 fill/stroke per subpath · 14 booleanes · 15 selecció de subpath),
   **3 PARCIALS** (7 moure node/nanses — només independents i d'un node alhora · 9 tancar — només en crear
   amb la ploma · 16 edició de nodes — només al sub-editor, mai in-place), i **9 NO EXISTEIXEN**
   (2,3,5,6,8,10,11,12 + l'in-place de 16).
4. **El #6 original de l'Agus ("no puc esborrar una línia") és, literalment, un handler absent + dues eines
   fantasma.** El Delete/Backspace (`TechSheetEditor.jsx:2473-2487`) esborra només l'OBJECTE sencer; no hi
   ha ni esborrat de subpath (fila 2) ni de segment (fila 3). A més la paleta **anuncia** dues eines
   "Selecció directa (nodes)" i "Selecció de subpath" que són **stubs inerts** (`soon:true`,
   `TechSheetEditor.jsx:3733-3734`) — l'usuari les veu però no fan res.
5. **La palanca de desbloqueig és una sola: un editor de nodes complet.** Paper.js ja porta natius TOTS els
   primitius que falten (`path.insert`/`removeSegment`/`divideAt`/`splitAt`/`segment.clearHandles`/`closed`).
   Les files 3,5,6,8,9,10,11,12 no són problemes algorísmics: són **interacció + mapatge al commit** sobre
   `PaperFlatEditor` (o sobre una capa in-place a Konva). La feina és d'UI, no de geometria.

---

## BLOC 0 — Arquitectura i model de dades (fila 17, fonament de tota la resta)

**Motor.** Llenç viu = Konva (`ObjectNode`/`PathObj`, `TechSheetEditor.jsx:1391-1498`). Paper.js entra per
dos camins EXCLUSIUS: booleanes offscreen (`ftt/paperbool.js:12-24`) i el sub-editor de nodes modal
(`PaperFlatEditor.jsx`, carregat lazy `TechSheetEditor.jsx:18`).

**Model d'objecte vectorial.** `type:'path'` amb `paths[]`. Cada entrada:
- SIMPLE: `{closed, fill, fillRule, stroke, strokeWidth, segments:[{x,y,inX,inY,outX,outY}]}`.
- COMPOSTA (forats): `{fill, fillRule:'evenodd', stroke, strokeWidth, subpaths:[{closed, segments}]}`.
  (S6, `TechSheetEditor.jsx:993-994`; render `pathToData` `:1022-1024`.) Coords en mm; handles relatius al node.

**Import SVG→model (fila 17).** `legacySketchSvgToPath`: Paper.js `importSVG`, després un walk `collect`
que **NO aplana** els compostos (`TechSheetEditor.jsx:1632-1638`); cada `CompoundPath`→entrada amb `subpaths`
(evenodd, `:1644-1656`), cada `Path` solt→entrada `segments` (`:1658-1665`); i **tot s'acobla en UN sol
objecte** `{type:'path', paths}` (`:1668-1678`). → **Un flat de N peces = 1 objecte amb N entrades a
`paths[]`; els subpaths es conserven, però no com a objectes independents.**

**Veredicte BLOC 0: llest com a fonament.** El model preserva subpaths (habilita 13/15) i és apte per a més
granularitat; el que falta no és el model sinó les operacions damunt seu.

---

## BLOC 1 — Esborrat: objecte · subpath · segment (files 1, 2, 3)

### Fila 1 — Esborrar una línia/path sencer seleccionat → **EXISTEIX**
- `deleteObjects(objIds)` filtra l'objecte fora de la pàgina (`TechSheetEditor.jsx:1881-1885`); `deleteObject`
  singular `:1876-1880`.
- Disparadors: **Delete/Backspace** (`:2473-2487`) — només objectes `layer==='free'`, no `locked`, amb el
  llenç desbloquejat (`locked` de pàgina); menú **Edició › Elimina** (E3, `SPRINT_EDITOR_ESTAT.md:252`).
- ⚠️ Matís: NO esborra si l'objecte està a una capa no-`free` o bloquejat (`:2483`).

### Fila 2 — Esborrar un SUBPATH dins un path compost (el #6 original) → **NO EXISTEIX**
- El handler de Delete opera sobre OBJECTES sencers (`:2482` `objectsOf(...).filter(...).map(o=>o.id)`); no
  mira `activeSubpath`.
- `activeSubpath` (`:1782`) només s'usa per DIRIGIR fill/stroke (`:4698,4726`) i per al REALÇ visual
  (`:1402`) — **mai per esborrar**. Grep de `removeSubpath`/`deleteSubpath`/`splice(...subpaths` = buit.
- L'eina de paleta "Selecció de subpath" que ho hauria de precedir és un **stub** `soon:true` (`:3734`).

### Fila 3 — Esborrar un segment entre dos nodes (obrir el path per allà) → **NO EXISTEIX**
- `PaperFlatEditor.jsx` (sub-editor de nodes) NOMÉS mou node/nanses (`:239-243`); no té esborrat de segment
  ni obertura. Grep de `removeSegment`/`splitAt`/`divideAt` a tot `pages/` = buit.

**Veredicte BLOC 1: cal 2 i 3.** L'1 és sòlid; el 2 depèn de la selecció de subpath (fila 15, que SÍ
existeix via segon clic) + un acte d'esborrat sobre `paths[index]`; el 3 depèn d'un editor de nodes amb
`path.removeSegment`/`splitAt` (Paper natiu).

---

## BLOC 2 — Ploma i creació de paths (fila 4)

### Fila 4 — Crear path nou (ploma) → **EXISTEIX** (ergonomia treballada als post-runs)
- Màquina d'estats `penRef` (`:1839-1840`); clic=ancoratge / clic+drag=handles bezier simètrics
  (`:2887-2896`, S7 `SPRINT_EDITOR_ESTAT.md:162`).
- **Tancament/final:** clic sobre el 1r punt (≤8px, ≥2 punts)→`finishPen(true)` tancat (`:2890`); **Enter**
  (`:2589-2591`); **doble-clic** (`:2835-2837`); **Escape** cancel·la tot el traç I surt de l'eina
  (`:2592-2594`, FIX PEN-TRAP `SPRINT_EDITOR_ESTAT.md:351-353`); **Backspace** treu l'últim ancoratge
  (`:2597-2601`).
- Sortida: `type:'path'` OBERT o TANCAT amb `stroke` a nivell d'objecte (`finishPen` `:2813-2831`), editable
  després al sub-editor.
- ⚠️ Deutes coneguts (S7/post-run): llindar de tancament 8px FIX (no escala amb zoom, `SPRINT_EDITOR_ESTAT.md:168`);
  el traç a mig fer no és a la història fins a finalitzar (undo = Escape/Backspace).

**Veredicte BLOC 2: llest.** La creació de paths és completa i robusta; el que li falta al "cicle Illustrator"
és tot AVALL (editar el path un cop creat: files 5-12).

---

## BLOC 3 — Edició de nodes: afegir · treure · moure · convertir (files 5, 6, 7, 8)

Tota l'edició de nodes viu al sub-editor `PaperFlatEditor.jsx` (modal), no al llenç viu.

### Fila 5 — Afegir node a un segment existent → **NO EXISTEIX**
- `PaperFlatEditor` no té inserció (llegit sencer `:216-250`: només hit-test + drag). Paper natiu
  `path.divideAt`/`curve.divide` NO s'usa (grep buit).

### Fila 6 — Treure node (i què passa amb la corba) → **NO EXISTEIX**
- Cap `removeSegment` al sub-editor. (Paper `path.removeSegment(i)` reconnecta la corba sol; no s'usa.)

### Fila 7 — Moure node · moure nanses · simètriques vs independents → **EXISTEIX PARCIAL**
- Moure NODE: `segment.point = point.add(delta)` (`PaperFlatEditor.jsx:239`).
- Moure NANSES: `handleIn`/`handleOut` per separat, cadascuna **INDEPENDENT** (`:240-243`) — arrossegar una
  no mou l'altra.
- ❌ NO hi ha mode SIMÈTRIC (nanses acoblades) ni "trencar simetria": sempre independents.
- ❌ Només s'editen les nanses **d'UN node alhora** (el `selectedIndex`, `:72-73`); la resta es mostren
  sense handles.

### Fila 8 — Convertir vèrtex ↔ corba (cantonada ↔ suau) → **NO EXISTEIX**
- Cap `clearHandles`/`smooth`/toggle cantonada. (Paper `segment.clearHandles()` / assignar `handleIn=-handleOut`
  ho farien; no s'usa.)

**Veredicte BLOC 3: cal 5, 6, 8, i completar 7.** Totes viuen a `PaperFlatEditor` i totes tenen primitiu
Paper natiu directe; la feina és interacció (dblclic sobre segment=afegir, tecla=treure, alt-drag=trencar
simetria) + escriure-ho al `segsOf`→commit (`PaperFlatEditor.jsx:298-315`).

---

## BLOC 4 — Topologia del path: tancar · obrir · separar · tallar (files 9, 10, 11, 12)

### Fila 9 — Tancar un path obert → **EXISTEIX PARCIAL**
- Només en CREACIÓ amb la ploma (clic al 1r punt, `:2890`). Per a un path **ja existent** NO hi ha "tancar":
  el sub-editor conserva `path.closed` al commit (`PaperFlatEditor.jsx:313`) però mai el commuta; cap botó/tecla.

### Fila 10 — Obrir un path tancat (tallar per un node) → **NO EXISTEIX**
- Cap acció posa `closed=false` ni `splitAt` en un node. Grep buit.

### Fila 11 — Separar (dividir un path en dos objectes · extreure un subpath com a objecte) → **NO EXISTEIX**
- Cap `split`/`divide`/`extractSubpath`. Les booleanes (fila 14) creen objectes nous però NO són "separar"
  (fusionen, no parteixen).

### Fila 12 — Tisores/ganivet: tallar per un punt arbitrari (no node) → **NO EXISTEIX**
- Cap eina de tall. (Paper `path.splitAt(location)` / `path.divideAt` ho cobririen.)

**Veredicte BLOC 4: cal 10, 11, 12, i completar 9.** Depenen d'un editor de nodes amb accés a
`path.closed`, `path.splitAt`, i (per a extreure subpath) de treballar sobre `paths[index]` sencer.

---

## BLOC 5 — Pintura, booleanes, selecció de subpath (files 13, 14, 15)

### Fila 13 — Fill/stroke per objecte · per SUBPATH → **EXISTEIX**
- Per objecte: `obj.stroke`/`obj.fill`.
- Per subpath: quan hi ha subpath actiu, el panell dirigeix a `paths[subActive].stroke`/`.fill`
  (`TechSheetEditor.jsx:3631` `subActive`, `:4698` stroke, `:4726` fill). Pinta una peça del flat sense tocar
  les altres. (S6, `SPRINT_EDITOR_ESTAT.md:149`.)

### Fila 14 — Booleanes: unite/subtract/intersect/exclude → **EXISTEIX** (Paper natiu + UI completa)
- Motor: `booleanOp(objects, op, style, makeId)` encadena `result[op](item)` offscreen i torna UN objecte
  `path` nou (compost si hi ha forats) (`ftt/paperbool.js:159-172`).
- Integració al model: `applyPathfinder(op)` (`TechSheetEditor.jsx:3672-3682`) — **substitueix** els inputs
  seleccionats pel resultat en una sola `updatePageObjects` (història coalescida).
- UI: ribbon 4 botons (`:4018-4021`) + menú **Objecte › Buscatraços×4** (`:4080-4083`); guard `pathfinderReady`
  = llenç desbloquejat + ≥2 objectes tots de `PATHFINDER_TYPES` (`:3671`, tipus a `:108`).
- ⚠️ Límit (S8, `SPRINT_EDITOR_ESTAT.md:178`): amb paths OBERTS el resultat de Paper és indefinit (cal formes
  tancades); transforms exòtics (escala no-uniforme+rotació) poc provats.

### Fila 15 — Selecció de subpath (prerequisit de 2 i 13) → **EXISTEIX** (però l'eina de paleta és fantasma)
- Mecanisme REAL: **segon clic** sobre una peça d'un objecte ja seleccionat l'activa (`PathObj`
  `TechSheetEditor.jsx:1391-1402`, `activeSubpath` `:1782`); realç de traç daurat (`:1402`); sortida amb
  Escape (`:2539`).
- ⚠️ L'eina de paleta "Selecció de subpath" (`:3734`) és un **stub `soon:true`**: no és el camí viu (que és
  el segon clic). Discrepància UI↔realitat a anotar.

**Veredicte BLOC 5: llest (13,14,15).** Les tres funcionen; la fila 15 té una **eina fantasma** que confon.

---

## BLOC 6 — Superfície d'edició: sub-editor vs in-place (fila 16)

### Fila 16 — Edició de nodes IN-PLACE al llenç vs sub-editor → **SUB-EDITOR només (in-place NO EXISTEIX)**
- L'edició de nodes és un **overlay modal** `PaperFlatEditor` (Paper.js sobre un `<canvas>` a pàgina sencera,
  `PaperFlatEditor.jsx:326-337`), fora del Konva viu.
- Entrada: **doble-clic** sobre el path (`onDblVector`→`startVectorEdit`, `TechSheetEditor.jsx:1394,3212-3218`);
  tecla **A** (`:3205-3223`); `editSelectedFlat` (`:3199`). Sortida: "Fet" (commit via ref) / Escape (`:2552-2555`).
- ❌ **In-place al llenç = NO EXISTEIX.** L'eina "Selecció directa (nodes)" de la paleta és un stub `soon:true`
  (`:3733`). Aquest és **exactament l'"estat de l'E4 pendent"** que menciona el brief: els nodes s'editen en
  una capa Paper separada, no directament sobre el flat al seu lloc.
- Cost de context: el sub-editor mostra només l'EXTERIOR d'un compost (`subpaths[0]`); els forats es preserven
  al commit però NO es veuen ni s'editen allà (`PaperFlatEditor.jsx:181-182,306-311` — limitació S6 documentada).

**Veredicte BLOC 6: decisió d'arquitectura oberta.** Tota l'edició fina de nodes (blocs 3-4) es pot fer
ESTENENT el sub-editor Paper (camí curt, ja té l'API Paper a mà) o construint una capa de nodes IN-PLACE
sobre Konva (camí llarg, paritat Illustrator real). És la bifurcació que decideix el cost de 5,6,8,9,10,11,12.

---

## TAULA FINAL — matriu de 17 capacitats per al CTO

| # | Capacitat | Estat | Àncora principal |
|---|---|---|---|
| 1 | Esborrar path/objecte sencer | **EXISTEIX** | `TechSheetEditor.jsx:1881,2473-2487` |
| 2 | Esborrar SUBPATH d'un compost | **NO EXISTEIX** | handler object-only `:2482`; stub `:3734` |
| 3 | Esborrar SEGMENT entre 2 nodes | **NO EXISTEIX** | `PaperFlatEditor.jsx:239-243` (només mou) |
| 4 | Ploma (crear path) | **EXISTEIX** | `:2887-2896,2813-2831` |
| 5 | Afegir node a un segment | **NO EXISTEIX** | `PaperFlatEditor` sense insert |
| 6 | Treure node | **NO EXISTEIX** | `PaperFlatEditor` sense removeSegment |
| 7 | Moure node/nanses (sim vs indep) | **PARCIAL** (indep · 1 node alhora · sense simètric) | `PaperFlatEditor.jsx:239-243,72` |
| 8 | Convertir vèrtex ↔ corba | **NO EXISTEIX** | cap `clearHandles`/toggle |
| 9 | Tancar path obert | **PARCIAL** (només en crear amb ploma) | `:2890`; commit `PaperFlatEditor.jsx:313` |
| 10 | Obrir path tancat | **NO EXISTEIX** | grep buit |
| 11 | Separar / extreure subpath | **NO EXISTEIX** | grep buit |
| 12 | Tisores/ganivet (punt arbitrari) | **NO EXISTEIX** | grep buit |
| 13 | Fill/stroke per objecte i per subpath | **EXISTEIX** | `:3631,4698,4726` |
| 14 | Booleanes unite/subtract/intersect/exclude | **EXISTEIX** (UI+motor) | `paperbool.js:159-172`; `TechSheetEditor.jsx:3672-3682,4018-4021` |
| 15 | Selecció de subpath | **EXISTEIX** (segon clic; eina paleta fantasma) | `:1391-1402,1782`; stub `:3734` |
| 16 | Edició de nodes in-place vs sub-editor | **SUB-EDITOR** (in-place NO EXISTEIX) | `PaperFlatEditor.jsx`; entrada `:3205-3223`; stub `:3733` |
| 17 | Com entra l'SVG importat | **1 objecte monolític, subpaths preservats** | `:1632-1678` |

---

## Graf de dependències (què desbloqueja què) — SENSE seqüenciar (decisió = Patró C)

```
Fila 17 (model, FET) ── preserva subpaths ──► habilita 13(FET) · 15(FET) · 2 · 11
                                             └► habilita, via paths[index], l'esborrat/extracció de peça

Fila 15 (selecció subpath, FET) ──prerequisit──► 2 (esborrar subpath) · 13 (pintar subpath, FET)

DECISIÓ D'ARQUITECTURA (fila 16): "editor de nodes complet"
   ├─ Camí A: ESTENDRE PaperFlatEditor (sub-editor Paper.js)  ── curt, API Paper a mà
   └─ Camí B: capa de nodes IN-PLACE sobre Konva              ── llarg, paritat Illustrator
        cadascun desbloqueja el MATEIX conjunt de node-ops:
        └─► 3 (esborrar segment) · 5 (afegir node) · 6 (treure node) ·
            7-simètric · 8 (convertir) · 9-existent (tancar) · 10 (obrir) ·
            11 (separar/split) · 12 (tisores)

Fila 4 (ploma, FET) i Fila 14 (booleanes, FET) són ILLES autònomes (no depenen de res del de dalt).
```

Nucli: **una sola palanca** (l'editor de nodes, fila 16) desbloqueja 8 de les 9 files que falten. La 2 penja
d'una branca curta i independent (esborrat sobre `paths[index]` amb la selecció de subpath ja existent).

---

## Estimació de mida per bloc (ordres de magnitud, SENSE seqüenciar ni prioritzar)

| Bloc | Files | Mida | Per què |
|---|---|---|---|
| Esborrar subpath | 2 | **S** | 1 handler que actua sobre `activeSubpath`→`paths.splice(index)` (o buida l'entrada); selecció ja feta (15). Independent de l'editor de nodes. |
| Node-ops al sub-editor | 3,5,6,7-sim,8,9,10 | **M** (com a bloc) · **S** cadascuna | Cada op = 1 primitiu Paper (`removeSegment`/`divideAt`/`clearHandles`/`closed`/`splitAt`) + gest + mapatge al `segsOf`→commit (`PaperFlatEditor.jsx:298-315`). El gruix és UI, no geometria. |
| Separar/extreure | 11 | **M** | `splitAt` + crear objecte(s) nou(s) a `pages` (patró d'`applyPathfinder`, que ja fa "reemplaça i crea"). |
| Tisores/ganivet | 12 | **M** | Eina de llenç (hit-test sobre corba→`getNearestLocation`→`splitAt`) + estat d'eina nou (patró ploma). |
| Edició IN-PLACE (Camí B) | 16 | **L** | Reimplementar handles de node sobre Konva (com `EndpointHandles` de line/arrow però per a bezier), + edició directa sobre `paths[]` sense modal. Substitueix o duplica el sub-editor. |
| Netejar eines fantasma | 2,15,16 | **XS** | Treure `soon:true` de `node`/`subpath` quan tinguin implementació, o retirar-les fins llavors (avui confonen). |

---

## 💡 PROPOSTA (a validar) — mapatge dels primitius Paper.js que cobririen cada forat

> Tot el que segueix és disseny a validar (Patró C decideix). Cap decisió d'arquitectura ni seqüència aquí.

- **Editor de nodes complet = ESTENDRE `PaperFlatEditor` (Camí A).** Ja té el `scope` Paper viu, el hit-test
  de segments/handles (`:217-232`) i el commit `paths` (`:298-315`). Els primitius natius encaixen 1:1:
  - Fila 3 esborrar segment → `path.removeSegment(i)` (reconnecta) o `path.splitAt` per "obrir per allà".
  - Fila 5 afegir node → hit-test sobre corba + `curve.divide(location)` / `path.divideAt`.
  - Fila 6 treure node → `path.removeSegment(i)`.
  - Fila 7 simètric → en arrossegar una nansa, escriure `handleOut = handleIn.multiply(-1)`; Alt = trencar.
  - Fila 8 convertir → `segment.clearHandles()` (cantonada) ↔ `segment.smooth()`/assignar handles (suau).
  - Fila 9/10 tancar/obrir → commutar `path.closed`; obrir per un node = `path.splitAt` en aquell segment.
  - Fila 11 separar → `path.splitAt` retorna dos paths → dos objectes; extreure subpath = moure `paths[index]`
    a un objecte nou (reusar el patró "reemplaça i crea" d'`applyPathfinder` `:3680`).
  - Fila 12 tisores → eina de llenç: `path.getNearestLocation(punt)` + `path.splitAt`.
- **Camí B (in-place a Konva)** dona la sensació Illustrator real (nodes sobre el flat al seu lloc, sense
  modal) però reimplementa a mà tota la matemàtica bezier que Paper ja regala al Camí A. És més car (L) i
  duplica el sub-editor tret que el jubili.
- **Forat de UX transversal:** les eines `node`/`subpath` de la paleta són `soon:true` (`:3733-3734`) i la
  selecció de subpath viu al segon clic (no a l'eina) — convindria alinear paleta i realitat quan es decideixi
  el camí, perquè avui l'usuari clica eines que no fan res (probable arrel de la percepció "no puc editar").
- **Booleanes amb paths oberts** (límit S8): si l'edició de nodes permet deixar paths oberts, caldria gate/aviso
  a `applyPathfinder` (avui `pathfinderReady` no distingeix obert/tancat, `:3671`).

---

## Verificació del documentador

- **Re-grep eines de la paleta actual:** `node` i `subpath` = `soon:true` inerts (`TechSheetEditor.jsx:3733-3734`);
  ploma/booleanes actives (`tool_pen`/`pathfinder_*` amb handlers reals `:2887,3672`). i18n confirma etiquetes
  "Selecció directa (nodes)"/"Selecció de subpath" existents però sense funció.
- **Re-grep handlers de teclat (Delete/Backspace especialment):** 11 blocs `keydown`
  (`grep -c addEventListener('keydown'` = 11). El de Delete/Backspace (`:2473-2487`) actua **només sobre
  objectes free** — confirma que el #6 de l'Agus és un handler d'abast object-level, sense branca de
  subpath/segment (files 2 i 3 = **NO EXISTEIX**, no és un bug amagat sinó capacitat absent).
- **Re-grep separar/tallar/afegir/treure node/convertir:** `split|divide|scissor|knife|addSegment|removeSegment|clearHandles|smooth`
  sobre `pages/` = **buit** → files 3,5,6,8,10,11,12 confirmades absents al codi (no especulat).
- **`PaperFlatEditor.jsx` llegit sencer:** l'única mutació és moure node (`:239`) i nanses independents
  (`:240-243`), un sol node amb handles alhora (`:72`) → fila 7 PARCIAL confirmada.
