# DIAGNOSI — Integració del dibuix vectorial al llenç (Opció B2)

> Patró A, **READ-ONLY absolut**. Cap canvi, cap commit, cap push. `/var/www/ftt-staging/frontend`.
> FETS amb `fitxer:línia`. Idees com `💡`. Decisions = de l'Agus (`⚖️`). Data: 2026-06-28.

**Decisió de fons (ja presa, no es reobre):** Konva segueix sent el LLENÇ (conserva tot el que
funciona: render, text, formes, data_blocks vius, round-trip .ftt de F1–F3). Paper.js és l'EINA
d'edició de traços vectorials sobre el mateix pla, no un mode-caixa a part. Sensació objectiu = B1
(llibertat total tipus Illustrator). Arquitectura = B2 (no trencar res). Aquí **es mapeja com
fer-ho i a quin cost**; no es decideix.

---

## RESUM EXECUTIu

- El `sketch_svg` **ja és ciutadà de primera al MODEL** (mateix array `objects`, mateix nucli
  `id/type/layer/x/y/width/height`, mateixa selecció/multiselecció, round-trip .ftt net). El que el
  fa sentir "caixa a part" és el **RENDER** (es rasteritza a `KonvaImage`, no és vector natiu) i,
  sobretot, l'**edició MODAL** (overlay Paper a pantalla completa, `zIndex:20`, que amaga l'objecte
  del llenç).
- El **bug de sortida** ("cou": l'element s'encongeix) és real i té causa concreta: asimetria entre
  l'escala d'entrada (fit uniforme `Math.min`) i la sortida (`exportSVG bounds:'content'`), més el
  fet que en confirmar **no es recalculen `width/height`** de l'objecte. És un bug **acumulatiu**
  (encongeix una mica més a cada cicle editar→sortir).
- Ja existeix la primitiva per a vectors editables de primera classe: el tipus **`line` amb
  `points[]`** (sense caixa, geometria als punts). El camí net és estendre aquest patró a corbes.
- Ja existeix un **PoC de capa Paper persistent sobre Konva** (`PaperKonvaPoc.jsx`, ruta
  `/disseny/poc-paper`) amb commutació d'ownership d'events — base de la via C.

---

# 1) ESTAT ACTUAL del `sketch_svg` com a objecte-caixa

## 1.1 Creació
Dues vies, mateixa estructura:
- **Flat buit** (`insertFlatSketch`, [TechSheetEditor.jsx:1319-1328](../../frontend/src/pages/TechSheetEditor.jsx#L1319-L1328)):
  `{ id, type:'sketch_svg', layer:'free', x:54, y:44, width:90, height:60, svg: EMPTY_FLAT_SVG }`
  i entra immediatament al mode Paper (`setEditingFlatId(obj.id)` `:1327`).
- **Import d'un SVG** (`importFlatSvgText`, `:1329-1354`): deriva `width/height` de l'aspect-ratio
  del SVG encaixant en 110×78 mm (`:1343-1351`). Si el seleccionat ja és `sketch_svg`, només
  substitueix `svg` (`:1336-1342`).
- `EMPTY_FLAT_SVG` és un `<svg viewBox="0 0 180 120">…` (`:65`).

**FET clau:** l'objecte guarda la geometria en **dos llocs independents** — el rectangle
(`width/height` en mm) i el **string `svg` opac** (amb el seu propi sistema de coordenades intern).
NO desa `viewBox`, `scale` ni bounding box propi. Aquesta dualitat és l'arrel del bug (§6).

## 1.2 Render Konva (mode normal, sense Paper)
`ObjectNode` despatxa a `SketchSvgObj` ([:713-715](../../frontend/src/pages/TechSheetEditor.jsx#L713-L715)).
`SketchSvgObj` (`:646-656`):
- Rasteritza el string SVG a data-URL (`svgDataUrl` `:67-69`) i el pinta com a **`<KonvaImage>`**
  (NO `Konva.Path`), dimensionat per `imageProps(obj)` = `toPx(obj.width) × toPx(obj.height)`
  (`:501-506`). → el SVG **s'estira a la caixa**, no es pinten els vectors natius.
- Placeholder de càrrega: un `<Rect>` `dash=[4,4]` amb les mateixes mides (`:649-652`).
- Export PDF/miniatures: mateixa via offscreen (`addObjectToLayer:593-598`).

## 1.3 Entrada/sortida del mode Paper
- Estat: `editingFlatId` (`:768`); derivat `editingFlat` (`:1520`).
- **Entrades:** crear flat (`:1327`), importar (`:1340`/`:1353`), i el botó "editar flat" de la
  propietat lateral → `editSelectedFlat` → `setEditingFlatId` (`:1362-1367`, botó a `:1905`).
  💡 **No hi ha doble-clic** per entrar a editar; cal el botó.
- **Muntatge:** quan `editingFlat` és truthy es renderitza `<PaperFlatEditor>` dins `<Suspense>`
  (`:1714-1727`), i l'objecte **s'amaga del llenç** (`.map` filtra `o.id !== editingFlatId`, `:1682`).
- **Sortides:** confirmar → `commitFlatEdit(svg)` (`:1368-1372`, **només** `updateObject(id, {svg})`);
  cancel·lar → `setEditingFlatId(null)` (`:1724`).

## 1.4 Què genera la percepció de "caixa amb manilles dins la qual s'entra"
Dues coses distintes:
- **Mode normal:** el `sketch_svg` rep el **Transformer de Konva** (`trRef`, `:1698-1699`, lligat a
  `:1116-1136`) → 8 manilles + rotació, idèntic a una imatge. (És ciutadà de primera per a
  transform-com-a-caixa; **no** està a l'exclusió `blocksTransform` `:517-519`.)
- **Mode Paper (el "entrar dins"):** un **overlay MODAL** `div { position:absolute, inset:0,
  zIndex:20 }` ([PaperFlatEditor.jsx:183](../../frontend/src/pages/PaperFlatEditor.jsx#L183)) amb un
  `<canvas>` propi a tota la pàgina que **substitueix el llenç interactiu**; les manilles són
  cercles Paper.js (`refreshHandles` `:54-88`).

→ **FET:** la sensació "objecte-caixa dins la qual s'entra a editar" la produeix l'**edició modal
de Paper** (overlay que tapa el llenç i amaga l'objecte), no pas un contenidor de dades. El model
no encapsula res; és pura interacció.

---

# 2) COHABITACIÓ DELS DOS MOTORS (avui)

| Aspecte | Konva (llenç) | Paper (editor) |
|---|---|---|
| DOM | `<canvas>` dins `wrapRef` (`:1674-1701`) | `<canvas>` propi (`PaperFlatEditor.jsx:184`) — **separat** |
| Scope | react-konva | `new paper.PaperScope()` aïllat (`:32`) — no toca el `paper` global |
| Coordenades | px-base (`toPx`, sense zoom) | px-de-vista (`toViewPx = toPx*zoom`, `:108`) |
| Zoom | CSS `transform: scale(zoom)` sobre `wrapRef` (`:1675`) | re-dimensiona el bitmap + re-escala la capa (`:156-173`, `canvas.width=pageW*zoom` `:167`) |
| Events | desactivats si `editingFlatId` (`:1121,1141,1209,1237,1252`) | **ownership total** mentre edita (overlay opac `zIndex:20`) |
| Vida | persistent | **efímer**: només existeix mentre `editingFlat` (`:1714`) |

**Sincronització:** Paper **reprodueix** la caixa del flat (no la comparteix): agafa
`imported.bounds`, calcula `targetW/H` des de `flat.width/height` via `toViewPx`
(`PaperFlatEditor.jsx:109-110`), escala l'SVG (`:111-112`) i el centra a
`(toViewPx(flat.x)+targetW/2, …)` (`:113-116`) — exactament a sobre d'on Konva pinta la imatge.

💡 **Dues estratègies de zoom divergents** (CSS transform vs. re-escala de raster) que han de
coincidir visualment: és fràgil i contribueix al bug (§6) si el zoom canvia durant l'edició.
💡 **Dos factors mm→px diferents al codi:** `MM_TO_PX = 2.4` ([:25](../../frontend/src/pages/TechSheetEditor.jsx#L25))
vs. el PoC `96/25.4 ≈ 3.78` (`PaperKonvaPoc.jsx:6`). Qualsevol via que reusi el PoC ha d'unificar-ho.

---

# 3) EL MODEL DE DADES

**Nucli comú:** `id`, `type`, `layer`, i posició (`x,y,rotation,scaleX,scaleY` opcionals) — `base`
a `:1257`, tractat per `ObjectNode` (`:659-667`). Tipus existents i camps:

| type | def. | camps |
|---|---|---|
| `text` | `:850,1219` | `text,width,height,fontSize,…`, opc. `bgFill`(text_box) |
| `rect`/`ellipse` | `:867/859` | `width,height` / `rx,ry`, stroke/fill |
| `line` | `:1267,1272` | **`points:[x1,y1,…]`** (polilínia nativa, x/y=0) |
| `arrow` | `:851,1270` | `x,y,x2,y2` |
| `image` | `:1298,1317` | `src,width,height`, opc. `kind:'logo'` |
| `sketch_svg` | `:1322,1348` | `width,height,svg`(string opac) |
| `data_block` | `:1407,1430` | `kind,size_fitting_id,scale,width,height` |
| `group` | `:845,905` | `children:[]` |

**Render unificat:** dispatcher únic `ObjectNode` (`:658-733`) + un **segon dispatcher paral·lel**
per export/miniatures `addObjectToLayer` (`:527-599`) que cal mantenir en paritat manual.

**Round-trip .ftt:** `serializeObject` (`:99-102`) només treu `src` dels `data_block`; el
`sketch_svg` es desa **tal qual amb el seu `svg` inline**. `documentToV2`/`v2ToDocument` (`:197/:216`)
només toquen objectes amb `src` que comenci per `assets/` → el `sketch_svg` passa **intacte** en
ambdós sentits. **Round-trip net i simètric.**

**Selecció/multiselecció (F3-1):** `selectedIds` array (`:753`); multiselecció heterogènia funciona
(text+vector+forma alhora, `handleSelectObject` `:837-840`, Shift=toggle). El Transformer s'aplica
filtrant `blocksTransform` (`:517-519`, exclou `line`/`arrow`/text-amb-bgFill); `sketch_svg` SÍ el rep.

**Z-order/capes:** `LAYER_ORDER = {template:0, data:1, free:2}` (`:53`). `data_block` neix a
`layer:'data'` (sempre darrere dels `free`); vectors/imatges a `free`. **No hi ha reordenament fi
per objecte** (z = `layer` + ordre d'array).

### 💡 RESPOSTA a l'objectiu 3
**Sí**, `document.json` pot representar un traç vectorial editable com a element de PRIMERA CLASSE
al mateix pla, **sense encapsular-lo com a caixa** — i de fet ja ho fa amb `line`/`points[]`
(geometria nativa, sense caixa, editable per punts via `localizeObject`/`globalizeObject`/
`objectBounds` `:104-191`). El que ho impedeix avui per als traços lliures és que `sketch_svg` va
escollir **string SVG opac + rasterització** en lloc de geometria estructurada. Canvi mínim: un
`type` nou (p.ex. `'path'`) amb `paths:[{segments:[{x,y,inX,inY,outX,outY}],closed,stroke,fill}]`.
La (de)serialització i el round-trip **ja ho acollirien sense canvis** (`serializeObject`/
`mapObjectTree` són agnòstics al tipus).

---

# 4) LES TRES VIES DE B2 (mapejades, NO triades)

### Via (a) — `sketch_svg` "in-place": treure caixa/Transformer, editar amb l'eina de nodes
**Què toca:**
- Excloure `sketch_svg` de `blocksTransform` quan està en mode-edició, o no lligar-hi el Transformer
  (`:1116-1136`); afegir un handler de doble-clic / eina-nodes que activi l'edició sense overlay
  modal a pantalla completa.
- Que `PaperFlatEditor` no es renderitzi com a overlay `inset:0` opac (`PaperFlatEditor.jsx:183`)
  sinó **acotat a la caixa de l'objecte** i sense amagar la resta del llenç (`:1682`).
- **Arreglar el bug §6** (obligatori aquí): recalcular `width/height` en confirmar i unificar
  fit↔export.

**Conserva de F1–F3:** TOT (model, round-trip, render Konva, data_blocks). Cap canvi de dades.
**Risc:** BAIX (cosmètic + interacció). El motor segueix sent el mateix overlay Paper efímer.
**Fidelitat a B1:** MITJANA-BAIXA. Continua sent "entrar a editar UN objecte"; no és selecció/moviment
conjunt de vectors lliures amb la resta. Treu la sensació de modal però no la d'"objecte a part".

### Via (b) — Vectors com a objectes del document al mateix nivell; Paper com a editor sota demanda
**Què toca:**
- **Model:** nou `type:'path'` amb `paths/segments` estructurats (§3). Branca nova a `ObjectNode`
  (`:713`-style) que pinti amb **`Konva.Path`/`Konva.Line` natius**, i la branca paral·lela a
  `addObjectToLayer` (`:559`-style) per a export.
- Estendre `localizeObject`/`translateObject`/`globalizeObject`/`objectBounds` (`:104-191`) per al
  nou tipus (anàleg a `line`, amb tangents Bézier).
- Paper passa a ser un **editor de nodes sota demanda** que llegeix/escriu `paths` estructurats (no
  string SVG): import → editar segments → escriure `paths` de tornada (no `exportSVG` opac).
- Migració/compat: `sketch_svg` existents (string SVG) es poden mantenir com a tipus llegat o
  convertir a `path` en obrir-los.

**Conserva de F1–F3:** model d'objectes, capes, selecció/multiselecció, round-trip (un camp `paths`
array passa net per `serializeObject`/`mapObjectTree` sense canvis). El render Konva es **millora**
(vectors natius en lloc de raster).
**Risc:** MITJÀ (canvi de model + dos dispatchers + geometria per-node). Acotat i reversible.
**Fidelitat a B1:** ALTA. El vector és un objecte més: se selecciona, mou, combina, capa i
multiselecciona com text/forma/imatge; Paper només apareix per editar nodes fins.

### Via (c) — Capa Paper PERSISTENT sota/sobre el llenç Konva (vectors sempre editables)
**Què toca:**
- Una capa Paper que viu permanentment sobre el Stage Konva, amb commutació d'ownership d'events.
  **Ja prototipat** a `PaperKonvaPoc.jsx` (ruta `/disseny/poc-paper`, `App.jsx:38,220`): underlay
  Konva + `<canvas>` Paper `position:absolute,inset:0` (`:427-439`), toggle `paperActive`
  (`:371`) amb `pointerEvents: auto/none` (`:436`), modes add/delete/select de nodes
  (`:86-90,160-179,374-382`).
- Sincronització contínua de zoom/pan/coordenades entre els dos canvas (avui ja divergents, §2),
  unificació de `MM_TO_PX` (2.4 vs 3.78 del PoC, `PaperKonvaPoc.jsx:6`).
- Reescriure la selecció/transform perquè operi cross-engine (un vector Paper i un text Konva
  seleccionats alhora) — no trivial.

**Conserva de F1–F3:** el render Konva i el round-trip es poden conservar, però la **selecció
unificada i el z-order** s'han de repensar (dos motors, dos plans de pintura).
**Risc:** ALT (events, rendiment de dos canvas sincronitzats, sincronia de coordenades, z-order
mixt). El PoC mitiga la incertesa però la integració a producció és gran.
**Fidelitat a B1:** MOLT ALTA (vectors sempre vius), però amb el cost arquitectònic i de risc més alt.

---

# 5) ELEMENTS FUTURS AL MATEIX PLA — confirmació

**FET:** text, fletxes, cercles, imatges, SVG de vora (com `sketch_svg`) i `data_block` (taules
vives) **ja conviuen avui al mateix array `objects`** amb:
- **Events:** un sol dispatcher `ObjectNode` (`:658-733`); selecció heterogènia per `selectedIds`
  (`:753`) amb multiselecció (`:837-840`).
- **Z-order/capes:** `LAYER_ORDER` (`:53`); però els `data_block` queden fixats a `layer:'data'`
  (darrere els `free`) i **no hi ha bring-to-front/send-back per objecte**.
- **Transformer:** uniforme excepte exclusions `blocksTransform` (`:517-519`).

**Conflictes a vigilar (💡):**
- **Z-order rígid:** si es vol intercalar lliurement un vector entre dos data_blocks o portar una
  taula al davant, cal un z per objecte (avui el dicta `layer`+ordre d'array). Limitació de F3-0,
  no del vector en si.
- **Vies (a)/(b):** com que el vector segueix sent Konva (raster a (a), `Konva.Path` natiu a (b)),
  events/z-order/multiselecció **es mantenen coherents** amb la resta sense fricció.
- **Via (c):** el vector viu en un canvas Paper SEPARAT → la multiselecció conjunta vector+text i el
  z-order mixt són el punt dur (dos plans de pintura). És el principal risc de conflicte.

---

# 6) EL "COU" I EL BUG DE SORTIDA (l'element s'encongeix en sortir)

## 6.1 FET — la cadena que el provoca
1. **Entrada** (`PaperFlatEditor.jsx:107-116`): `scale = Math.min(targetW/bounds.width,
   targetH/bounds.height)` (`:111`) — **fit UNIFORME** (preserva ratio). Si l'aspect del SVG ≠ aspect
   de la caixa, el dibuix queda **més petit que la caixa** en un dels eixos (deixa marge).
   `targetW/H` inclouen `zoom` via `toViewPx` (`:108`).
2. **Sortida** (`PaperFlatEditor.jsx:178`): `exportSVG({ asString:true, bounds:'content' })` — el
   viewBox del SVG resultant es **cenyeix al contingut REAL** (la versió ja escalada/encongida), no
   a la caixa original.
3. **Confirmar** (`commitFlatEdit`, `:1368-1372`): fa **només** `updateObject(id, { svg })` —
   **NO recalcula `width/height/x/y`** (a diferència d'`importFlatSvgText` `:1343-1346`, que SÍ deriva
   width/height de l'aspect-ratio).
4. **Re-render** (`SketchSvgObj` via `imageProps`, `:501-506`): el nou SVG es torna a **estirar** a
   `toPx(width)×toPx(height)` (la caixa original sense canviar).

→ Resultat: el contingut (que `bounds:'content'` ja havia retallat a la versió encongida) es torna a
encaixar en una caixa amb una **referència de bounding box que ja no coincideix** → es percep
"reduït"/deformat. I com que la caixa no s'actualitza, **l'error s'ACUMULA** a cada cicle editar→sortir.
Agreujant: si el `zoom` de commit ≠ zoom d'entrada, l'escala absoluta queda descompensada (l'entrada
incorpora zoom `:108`; la re-escala de zoom durant l'edició és a `:156-173`).

**Punts sospitosos concrets:**
- `PaperFlatEditor.jsx:111` — fit `Math.min` (genera el marge).
- `PaperFlatEditor.jsx:178` — `exportSVG({ bounds:'content' })` (retalla al contingut escalat).
- `TechSheetEditor.jsx:1370` — `updateObject(id, {svg})` **sense re-derivar width/height**.

## 6.2 Com cada via ho evita/resol
- **Via (a):** l'ha de RESOLDRE explícitament (és el mateix motor). Correcció natural: en
  `commitFlatEdit` re-derivar `width/height` de l'aspect del SVG exportat (com fa `importFlatSvgText`
  `:1343-1346`) i unificar fit↔export (o exportar amb la caixa original, no `bounds:'content'`).
- **Via (b):** l'**elimina d'arrel** — no hi ha string SVG opac ni rasterització ni doble referència
  de bounding box: els `paths` estructurats es desen en coordenades del document i es pinten natius;
  no hi ha cicle fit→export→stretch.
- **Via (c):** també l'elimina (els vectors viuen sempre en coordenades Paper persistents, no
  s'importen/exporten per editar), però a canvi del cost arquitectònic de §4c.

---

# 💡 PROPOSTA (la via recomanada)

**Recomanació: Via (b)** — vectors com a objectes `type:'path'` de primera classe amb `paths/segments`
estructurats, Paper com a editor de nodes sota demanda.

**Per què (cost/risc/fidelitat):**
- **Fidelitat B1 ALTA** amb **risc MITJÀ**: el vector esdevé un objecte més (selecció, moviment,
  combinació, capes i multiselecció conjunts amb text/forma/imatge), que és exactament la sensació
  Illustrator desitjada — sense el salt arquitectònic ni el risc d'events/rendiment de la via (c).
- **Conserva F1–F3 sencer:** model d'objectes, capes, round-trip .ftt (un camp `paths` array passa
  net per la serialització agnòstica) i els data_blocks vius. A més **millora** el render (vectors
  natius en lloc de raster) i **elimina el bug §6 d'arrel**.
- **Aprofita el que ja hi ha:** el patró `line`/`points[]` (`:1267`,`:104-191`) és la prova que el
  llenç ja sap pintar i editar geometria nativa sense caixa; (b) l'estén a corbes Bézier.

**Seqüència suggerida si s'escull (b):**
1. Arreglar primer el bug §6 a la via (a) com a **pegat ràpid** (re-derivar width/height al commit) —
   atura el "cou" mentre es construeix (b). Baix risc, valor immediat.
2. Introduir `type:'path'` + branca `ObjectNode`/`addObjectToLayer` amb `Konva.Path`.
3. Reconvertir `PaperFlatEditor` perquè editi `paths` estructurats (no string SVG) i, en una segona
   fase, desacotar-lo de l'overlay modal (editar in-place dins la caixa de l'objecte).
4. Compat: `sketch_svg` llegat → conversió a `path` en obrir-lo.

La via (c) queda com a horitzó si es vol "tot sempre editable sense cap commit"; el PoC
(`/disseny/poc-paper`) ja en valida la viabilitat tècnica si l'Agus hi vol invertir més endavant.

---

# ⚖️ PER DECIDIR (Agus)

1. **Quina via:** (a) pegat cosmètic mínim · (b) vectors de primera classe `type:'path'`
   (recomanada) · (c) capa Paper persistent (màxima fidelitat, màxim risc). No excloents: (a) com a
   pegat immediat + (b) com a objectiu és un camí natural.
2. **Tocar el model de `document.json`?** (b) i (c) introdueixen un `type:'path'` amb `paths/segments`
   estructurats (substituint o coexistint amb `sketch_svg` string-SVG). Decisió: nou tipus net vs.
   evolucionar `sketch_svg` a portar `paths` a banda del `svg`.
3. **Compatibilitat dels `sketch_svg` existents:** convertir-los a `path` en obrir (lossy de l'SVG
   ric?) o mantenir `sketch_svg` com a tipus llegat de només-lectura/raster.
4. **Z-order per objecte (F3-0):** introduir bring-to-front/send-back per objecte (avui el z el dicta
   `layer`+ordre d'array, amb `data_block` fix a `data`)? És ortogonal a la via però necessari per a
   la sensació "tot al mateix pla, reordenable".
5. **Pegat del bug §6 ja:** aplicar el fix ràpid (re-derivar `width/height` al `commitFlatEdit` +
   unificar fit↔export) independentment de la via final, per aturar el "cou" ara.

---

*Diagnosi read-only. Cap fitxer de codi tocat. Cap commit, cap push.*
