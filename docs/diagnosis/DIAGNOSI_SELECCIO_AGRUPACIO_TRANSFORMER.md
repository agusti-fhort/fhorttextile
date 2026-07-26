# DIAGNOSI — Selecció múltiple, agrupació, Transformer, sortida de mode i etiqueta de cota

Data: 2026-07-21 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` · **HEAD = `0f0d6d6`** (inclou les 7 fases del sprint Patró B d'avui)

**Abast.** Verificar l'estat REAL de cinc comportaments que el smoke d'Agus posa en dubte després de la Fase 6, abans de redactar cap brief: marquesina de selecció (P1), agrupar/desagrupar (P2), Transformer (P3), sortida de mode (P4) i mida de l'etiqueta de la cota de POM (P5).

**Convenció.** Cada afirmació porta `fitxer:línia`, re-ancorada contra HEAD `0f0d6d6`. **"NO EXISTEIX" = confirmat absent al codi** (verificat amb grep), no especulat. **No s'ha donat per bo cap informe anterior**: tot s'ha rellegit. Les propostes van marcades 💡 i estan separades dels fets — **les decisions són humanes (Patró C)**.

Camins relatius a `frontend/src/`. `TSE` = `pages/TechSheetEditor.jsx` · `PFE` = `pages/PaperFlatEditor.jsx`.

---

## Resum executiu

1. **La marquesina d'objectes EXISTEIX i és completa** (`TSE:3017-3022`, `:3075-3083`, `:3106-3129`), amb shift acumulatiu i llindar de 3×3 px per distingir clic de marc. La de **nodes també existeix** (`PFE:666`, `:672-675`, `:748-755`). La que **NO EXISTEIX és la de FORMES** (fletxa negra): el mode `shape` no en té ni una línia (`PFE:594-618`) — allà el clic al buit deselecciona i prou.

2. **El botó Agrupar funciona i el gest d'Agus hauria de completar-se.** `groupSelection` (`TSE:2149-2169`) és sòlid. Té un `return` silenciós (`:2152`) si després de filtrar plantilla queden <2 objectes, però **aquest camí és inabastable per UI avui**: els objectes de capa `template` no són seleccionables al llenç (`TSE:4645`) i el marquee només agafa `free` (`TSE:3119`). Si el gest falla per a l'Agus, **no és aquí** — la causa candidata és P4 (no es pot deseleccionar / sortir del mode per clic).

3. **A nivell VECTORIAL no existeix cap agrupació, i probablement no cal.** La multi-selecció de formes (`PFE:609-611`) mou juntes sense agrupar, i **NO EXISTEIX res més**: cap `group` a tot `PFE` (0 coincidències). El motiu és estructural: **un objecte `path` JA és un compound** — `obj.paths[]` és la llista de subpaths (`TSE:1037`, `:1067`). "Agrupar formes" ja està fet per construcció; el que falta és el pont invers entre objectes i subpaths, i els dos primitius hi són (`booleanOp` unite `TSE:3932-3942` · `extractActiveSubpath` `TSE:3946-3961`).

4. **El Transformer SÍ apareix sobre paths — i això és el problema, no la mancança.** `blocksTransform` (`TSE:1192-1194`) només exclou `line`, `arrow`, `field` i `text` amb fons: **`path`, `group`, `rect`, `ellipse`, `image`, `data_block` i `table` tenen handles**. Però per a `path` i `group` el `transformEnd` **absorbeix l'escala com a `obj.scaleX/scaleY`** (`TSE:2868-2871`, `:2864-2867`) en lloc de reescriure geometria. Els handles ja hi són; el que **NO EXISTEIX és el bake**.

5. **Els primitius per al bake hi són tots i són purs** (`scaleSubpath` `paperOps.js:96-103` · `rotateSubpath` `:106-116` · `mirrorSubpath` `:86-93`), i **el pont ja existeix i funciona** — però només dins la sessió de nodes i disparat per input numèric (`PFE` `opsRef.scaleShapes`/`rotateShapes` → `transformShapes` → `markDirty` → `emit` → `onCommit`). **NO EXISTEIX** cap camí que vagi d'un drag de handle Konva a `paperOps`.

6. **La sortida de mode per clic NO EXISTEIX, en cap dels dos modes.** L'ÚNICA sortida d'`editingFlatId` és **Escape** (`TSE:2645-2656`). Els botons Fet/Cancel·lar van caure a la Fase 6a i **el comentari del handler encara diu «equivalent al botó Cancel·lar»** (`TSE:2644`), que ja no existeix. A més, el canvas de Paper cobreix la pàgina sencera (`PFE:856-857`) i **fora de la pàgina no hi ha cap handler de clic**: `onViewportMouseDown` surt d'hora si no s'està fent pan (`TSE:3195-3196`). Clicar al gris no fa absolutament res.

7. **L'etiqueta de la cota és d'amplada FIXA de 24 mm, decidida a la inserció** (`TSE:2973`, `:2976`), i el fons se'n deriva (`textBoxParts` `TSE:969-982`). No es mesura el text enlloc: **NO EXISTEIX cap `measureSize`/`getTextWidth` a tot el fitxer**. Per això «1/2 CHEST WIDTH» i «A» ocupen exactament el mateix.

---

## BLOC P1 — Marquesina de selecció

### P1.1 · Nivell OBJECTES (Stage Konva) — **EXISTEIX, completa**

Estat: `marquee` per pintar (`TSE:1907`) + `marqueeStart` amb el gest en curs (`TSE:1908`).

| Fase | Ancoratge | Què fa |
|---|---|---|
| Inici | `TSE:3014-3023` | Només amb `tool === 'select'` **i** `e.target === e.target.getStage()` (tela buida). Guarda `{x, y, shift, rect}` i, de passada, **surt del grup entrat** (`:3019`) |
| Arrossegament | `TSE:3075-3083` | Normalitza el rectangle (min/abs) i el puja a l'estat |
| Tancament | `TSE:3106-3129` | Llindar: `w<=3 && h<=3` → **es tracta com a clic simple** i deselecciona tret que hi hagi shift (`:3112-3115`) |
| Hit-test | `TSE:3119-3125` | Només objectes `layer === 'free'`, no `locked`, no invisibles. Intersecció de rectangles amb `node.getClientRect({relativeTo: node.getLayer()})` — **solapament, no contenció** |
| Acumulació | `TSE:3127` | Amb shift, unió amb la selecció prèvia |
| Pintura | `TSE:4692` | `Rect` gold al 15% amb `dash [4,4]` i `listening={false}` |

**Gates d'entrada del handler**: `onStageMouseDown` surt d'hora si `!konvaOwnsPointer` (`TSE:2960`, la comprovació de mode de la Fase 6b), si l'eina és `pan` o hi ha espai premut, i si el document no està `locked`.

> **Fet clau per a P4**: `konvaOwnsPointer` és `pointerMode === 'objecte'` (`TSE:3336`), i `pointerMode` és `'objecte'` només si **no** hi ha `editingFlatId`. Per tant, **dins l'edició de nodes/formes, la marquesina d'objectes està desconnectada per disseny**.

### P1.2 · Nivell NODES (dins `PaperFlatEditor`) — **EXISTEIX**

Va entrar; **no va quedar en shift+clic**. Conviuen els dos.

- Ref: `marqueeRef` (`PFE:34`), netejat al cleanup del scope (`PFE:80`).
- Inici: `PFE:666` — **només si `active === 'select'`** (fletxa blanca) i no s'ha encertat cap path; sense shift, buida primer la selecció de nodes.
- Arrossegament: `PFE:672-675` → `drawMarquee` (`PFE:878-889`), rectangle discontinu `[3,3]` a la capa UI.
- Tancament: `PFE:748-755` — `scope.Rectangle.contains(s.point)`, és a dir **contenció del node, no solapament** (criteri diferent del d'objectes, §P1.1).
- **Limitació**: itera `path?.segments` — **només els nodes de la subpath ACTIVA**. Una marquesina que travessi dues formes no agafa els nodes de la segona.
- Shift+clic sobre node també existeix (`PFE:635`), amb toggle.

### P1.3 · Nivell FORMES (fletxa negra) — **marquesina NO EXISTEIX**

Tot el mode `shape` és `PFE:594-618`:

- Shift+clic **SÍ** (`PFE:609`): `sel.has(idx) ? sel.delete(idx) : sel.add(idx)`, toggle amb re-fixació del primari.
- Doble-clic sobre forma → entra a selecció directa (`PFE:601-606`, finestra de 350 ms).
- **Clic al buit** (`PFE:614-617`): `setShapeSelection([])` — deselecciona, i **NO obre cap marquesina**. La branca de marquesina (`PFE:666`) és a l'altre camí del `if`, gated a `active === 'select'`, i el mode forma ha fet `return` a `:618` molt abans.

> **Veredicte P1: cal X, i és una sola cosa.** Dels tres nivells, dos tenen marquesina i un no. El forat és **exactament el mode forma**, i el patró a copiar és el de nodes (mateix fitxer, mateixes coordenades de view px, mateix `drawMarquee`).

💡 **PROPOSTA P1-A (a validar).** Obrir marquesina a `PFE:614-617` quan el clic al buit és en mode forma, i resoldre-la a `PFE:748` seleccionant les formes el `bounds` de les quals intersequi el rectangle (`allPaths()` en lloc de `path?.segments`). Decisió pendent: **contenció o solapament** — avui el codi fa servir els dos criteris (nodes: contenció `PFE:753` · objectes: solapament `TSE:3123`).

💡 **PROPOSTA P1-B (a validar).** Si es toca la marquesina de nodes, aprofitar per fer-la travessar formes (`allPaths()`), avui limitada a la subpath activa (`PFE:753`).

---

## BLOC P2 — Agrupar / desagrupar

### P2.1 · Els botons del ribbon Organitzar

| Botó | Ancoratge | Handler | Gate del botó |
|---|---|---|---|
| Agrupar | `TSE:4391` | `groupSelection` (`TSE:2149`) | `nodeMode \|\| selectedObjects.length < 2` |
| Desagrupar | `TSE:4392` | `ungroupObject(selObj.id)` (`TSE:2170`) | `nodeMode \|\| selObj?.type !== 'group'` |

**`groupSelection` (`TSE:2149-2169`), pas a pas:**
1. Filtra la selecció excloent `layer === 'template'` (`:2151`).
2. **`if (selected.length < 2) return`** (`:2152`) — l'únic camí de fallada silenciosa.
3. Origen del grup = cantonada superior-esquerra del bbox conjunt (`:2153-2154`).
4. Crea `{type:'group', layer:'free', x, y, rotation:0, children}` amb els fills passats a coordenades locals per `localizeObject` (`:2158`, def. `TSE:200-208`).
5. **Insereix el grup a la posició del PRIMER seleccionat** en z-order (`:2161-2165`), no al capdamunt.
6. `setSelectedIds([groupId])` (`:2167`).

**`ungroupObject` (`TSE:2170-2179`):** exigeix `type === 'group'` (`:2171`, si no `return` silenciós), globalitza els fills amb `globalizeObject` (`:2173`, def. `TSE:232-...`, que **compon rotació, escala i posició del pare**, inclosos `width/height/rx/ry/scale` a `:236-242`), els substitueix in-place (`:2175`) i els deixa seleccionats (`:2177`).

**Sobre la fallada silenciosa (`:2152`):** perquè es doni, cal 2+ ids seleccionats amb almenys un de capa `template`. **Avui és inabastable per UI**: al llenç, `selectable` exclou `layer === 'template'` (`TSE:4645`); el marquee només agafa `free` (`TSE:3119`); i la fila del panell Capes fa `selectOnly(o.id)` (`TSE:4851`) — **un sol id**, així que el botó ja estaria deshabilitat per `< 2`. **El botó, doncs, o està deshabilitat o funciona.**

### P2.2 · El gest d'Agus: seleccionar 2+ objectes → Agrupar

Traçat complet contra HEAD, el resultat esperat és:

1. Selecció per shift+clic (`TSE:2031` → `toggleSelection` `:2023`) o per marquesina (`TSE:3127`).
2. Botó habilitat (`selectedObjects` = `curObjs.filter(selectedSet.has)`, `TSE:3829`).
3. Es crea el grup i queda seleccionat ell sol.
4. El grup **és seleccionable** (`layer:'free'`, no `locked` → `TSE:4645`) i **arrossegable** (`TSE:4646`).
5. **Mostra handles**: `blocksTransform(group)` és fals (`TSE:1192-1194`) → el Transformer s'hi enganxa (`TSE:2546-2551`).
6. Doble-clic hi entra (`onDblGroup`, `TSE:4657` → `setActiveGroup`), i llavors els fills es poden seleccionar i moure (`TSE:1564-1567`).

> **Si el gest no es completa per a l'Agus, la causa NO és `groupSelection`.** El sospitós, per ordre: (a) no aconseguir tenir 2 objectes seleccionats alhora — que enllaça amb P1.3 i P4; (b) `nodeMode` actiu sense saber-ho, que deshabilita el botó (`TSE:4391`) i que **avui només se surt amb Escape** (§P4). **PENDENT DE VERIFICAR amb l'Agus**: quin dels dos és, perquè el codi no permet distingir-ho des d'aquí.

### P2.3 · Agrupació a nivell VECTORIAL — **NO EXISTEIX, i el model explica per què**

- **Cap concepte de grup a `PaperFlatEditor`**: `grep -c group PFE` → **0**.
- La multi-selecció de formes (`selectedShapesRef`, `PFE:609-611`) **les mou juntes sense agrupar-les**: el drag itera el conjunt i translada cada path (`PFE:684-686`). Confirmat que **no hi ha res més**.
- **El motiu estructural**: un objecte `path` ja ÉS un compound. `obj.paths[]` és la llista de subpaths, i el render els concatena en un sol `d` amb `fillRule:'evenodd'` (`TSE:1067`, lectura a `:1037`). Les "formes" de la fletxa negra **són** els membres d'aquest compound.

**Primitius disponibles si es volgués UI d'agrupació vectorial** (no es dissenya aquí):

| Gest | Primitiu que ja existeix | Ancoratge | Abast |
|---|---|---|---|
| Fusionar N objectes `path` en un | `booleanOp(objects,'unite',…)` via `applyPathfinder` | `TSE:3932-3942`; motor `paperbool.js:159` | Objectes → 1 objecte. **Fusiona geometria**, no només agrupa |
| Treure una forma del compound | `extractActiveSubpath` | `TSE:3946-3961` | Subpath → objecte `path` nou de primer nivell |
| Combinar N subpaths dins l'objecte | `booleanSubpaths(subpaths, op)` | `paperOps.js:122-134` | Retorna `[{segments,closed},…]`; **pot tornar més d'un subpath** |
| Moure'n una sense agrupar | `translateSubpath` | `paperOps.js:78-84` | Pur |

**Fet a tenir present**: `booleanOp`/`booleanSubpaths` **fusionen** (uneixen contorns), que no és el mateix que **agrupar** (mantenir identitats). Un "agrupa aquestes formes" que conservi les formes **no té primitiu**: seria afegir-les al mateix `obj.paths[]` sense operació booleana — reordenació d'arrays, no geometria.

> **Veredicte P2: llest a nivell d'objectes, i a nivell vectorial la pregunta està mal plantejada.** Els objectes s'agrupen i es desagrupen correctament. Al canvas vectorial, "agrupar" ja és el que hi ha (un objecte = un compound); el que podria faltar és **moure subpaths entre objectes**, i els dos primitius del pont existeixen.

---

## BLOC P3 — Transformer (handles d'escalar/rotar)

### P3.1 · Quins tipus mostren handles

Configuració única: `<Transformer>` a `TSE:4707-4711`; ancoratge a `TSE:2534-2554`.

Filtre exacte (`TSE:2548`): `selectedSet.has(o.id) && o.layer !== 'template' && !blocksTransform(o) && !o.locked && o.visible !== false`.

`blocksTransform` (`TSE:1192-1194`) — **l'única llista d'exclusió**:
```js
obj.type === 'line' || obj.type === 'arrow' || obj.type === 'field' || (obj.type === 'text' && obj.bgFill)
```

| Tipus | Handles? | Nota |
|---|---|---|
| `rect`, `ellipse`, `image`, `text` (sense fons) | **SÍ** | `transformEnd` escriu `width/height` (o `rx/ry`) reals (`TSE:2879-2888`) |
| `data_block`, `table`, `pattern_piece` | **SÍ** | `keepRatio` forçat (`TSE:4707`); l'escala es baka a `obj.scale` (`TSE:2875-2878`) |
| **`path`** | **SÍ** | ⚠️ l'escala es desa com a `scaleX/scaleY` (`TSE:2868-2871`) |
| **`group`** | **SÍ** | ⚠️ ídem (`TSE:2864-2867`) |
| `line`, `arrow` | **NO** | Tenen nanses d'extrem pròpies (`EndpointHandles`, `TSE:1423`) |
| `field` | **NO** | Xip de plantilla |
| `text` amb `bgFill` | **NO** | És un `Group` amb `Rect` darrere (`TSE:1512-1520`) — **inclou l'etiqueta de la cota de POM** |
| Qualsevol de capa `template` | **NO** | `TSE:2548` |

**Configuració condicional**: `rotateEnabled` és **incondicional** (`TSE:4707`); `keepRatio` sí que és condicional (shift, o tipus `data_block`/`table`/`pattern_piece`). **`enabledAnchors` NO EXISTEIX** — cap punt del fitxer el fixa, així que tots els tipus transformables mostren els 8 anchors.

**Guard de mode**: amb `editingFlatId` actiu, `tr.nodes([])` (`TSE:2539-2543`) — el Transformer desapareix del tot durant l'edició de nodes.

### P3.2 · Per als paths: què passa avui i què faltaria per al bake

**Camí d'escalar/rotar amb handles: EXISTEIX** (§P3.1) — però **no aplica a geometria**. `handleTransformEnd` (`TSE:2856-2889`) reseteja el node Konva (`:2863`) i, per a `path`, desa `{x, y, rotation, scaleX: sx, scaleY: sy}` (`:2869`). La geometria de `obj.paths[].segments` **queda intacta**; el que canvia és la transformació de l'objecte.

**Conseqüència ja documentada al codi**: `PaperFlatEditor` ha de **desfer** aquesta transformació a l'entrada (`PFE:436-452`) i tornar-la a aplicar a la sortida (`PFE:818-830`), precisament perquè no està bakejada.

**Camí numèric alternatiu**, que sí que bakeja: dins l'edició de nodes, `rotateShapes`/`scaleShapes` (`PFE` `opsRef`) → `transformShapes` → `rotateSubpath`/`scaleSubpath` → `markDirty` → `emit` → `onCommit` → model. S'hi arriba pels camps `°` i `%` de la tab Editar (`TSE:4360-4371`).

**Estat de les tres peces que caldrien per a handles-que-bakejen:**

| Peça | Estat | Ancoratge |
|---|---|---|
| Primitius purs de bake | **EXISTEIXEN** | `scaleSubpath` `paperOps.js:96-103` · `rotateSubpath` `:106-116` · `mirrorSubpath` `:86-93`. Purs, sense Paper ni DOM |
| Pont "acció → paperOps → escriptura al document" | **EXISTEIX i és viu** | `PFE` `opsRef` → `transformShapes` → `markDirty` (`PFE:245-249`) → `emit` (`PFE:800`) → `onCommit` → `commitFlatEdit` (`TSE:3392`) |
| Pont "drag de handle Konva → paperOps" | **NO EXISTEIX** | `handleTransformEnd` (`TSE:2856`) no importa res de `paperOps`; `grep paperOps TSE` → només `booleanOp` de `paperbool` (`TSE:16`) |

**Matís d'espai, crític si algú ho implementa**: `paperOps` és invariant d'escala però **el cridador decideix l'espai**. `PaperFlatEditor` el crida en **px de view** (`PFE:768-775`); un bake des de `handleTransformEnd` treballaria en **mm de model**. El centre de rotació també difereix: `objectBounds` (mm) vs `p.bounds` (view px).

> **Veredicte P3: cal X, i és petit i acotat.** Els handles ja hi són i ja s'apliquen; el que falta és **una branca a `handleTransformEnd`** que, per a `path`, en lloc de desar `scaleX/scaleY`, passi els segments per `scaleSubpath`+`rotateSubpath` en mm i escrigui `paths` amb `scaleX/scaleY/rotation` neutres.

💡 **PROPOSTA P3-A (a validar) — bake al `transformEnd`, no durant el drag.** Deixar que Konva faci el feedback visual amb `scale` viu (és el que ja fa) i bakejar **només en deixar anar**, a `TSE:2868-2871`. No cal tocar el Transformer, ni Paper, ni el render. Cost estimat: una funció.

💡 **PROPOSTA P3-B (a validar) — decidir què passa amb `group`.** Un grup bakejat hauria de repartir la transformació entre els fills (`globalizeObject` `TSE:232` ja sap compondre-la). És més car que el cas `path` i **pot esperar**: convé decidir si entra al mateix brief o no.

💡 **PROPOSTA P3-C (a validar) — `enabledAnchors` per tipus.** Avui tots els tipus transformables mostren 8 anchors. Un `text` sense fons, per exemple, només té sentit que s'estiri en amplada (`transformEnd` ja ignora l'alçada del text, `TSE:2887`). És cosmètic i independent del bake.

---

## BLOC P4 — Sortida de mode

### P4.1 · Per què clicar fora no deselecciona ni surt (mode fletxa negra)

**Tres fets encadenats, cap d'ells un bug aïllat:**

1. **El clic al buit dins la pàgina SÍ deselecciona les formes** (`PFE:614-617`: `setShapeSelection([])`). Per tant "no deselecciona" és, estrictament, **fals** — el que no fa és **sortir**.
2. **NO EXISTEIX cap camí de sortida per clic.** L'únic punt que fa `setEditingFlatId(null)` per acció de l'usuari és el handler d'**Escape** (`TSE:2645-2656`). Els altres dos són col·laterals: esborrar l'objecte editat (`TSE:1941`) i la neteja quan l'id ja és null (`TSE:3346-3350`).
   ⚠️ **El comentari del handler menteix des de la Fase 6a**: `TSE:2644` diu *«Escape cancel·la l'edició de nodes (equivalent al botó Cancel·lar)»*, i **el botó Cancel·lar ja no existeix** — va caure amb la transacció. Escape ja no cancel·la res (no hi ha res a revertir: tot està escrit); **només surt**.
3. **Fora de la pàgina no hi ha ningú escoltant.** El canvas de Paper cobreix exactament `pageW*zoom × pageH*zoom` (`PFE:856-857`) amb `pointerEvents:'auto'` mentre s'edita. Més enllà del paper hi ha el viewport, i `onViewportMouseDown` (`TSE:3195-3196`) **surt d'hora si no s'està fent pan**. Clicar al gris de treball, doncs, **no dispara absolutament res**.

**On s'enganxaria, segons el que el codi ja suggereix:**

- El precedent més proper és el del llenç d'objectes: `TSE:3017-3019`, on el clic en tela buida **surt del grup entrat** (`setActiveGroup(null)`). És literalment el mateix patró semàntic (sortir d'un context d'edició en clicar fora) i ja està escrit.
- El punt natural per al primer nivell és `PFE:614-617` (mode forma) i `PFE:666` (mode nodes) — els dos ja detecten "clic sense hit". Faria falta un callback nou al pare (al costat d'`onEnterDirect`, `PFE:23`) perquè el fill pugui demanar la sortida; el fill **no coneix `editingFlatId`** ni ha de conèixer-lo.
- Per al clic **fora de la pàgina**, el punt és `onViewportMouseDown` (`TSE:3195`), afegint-hi una branca abans del guard de pan.

### P4.2 · El mateix per al mode nodes

Clic fora del path en edició, mode fletxa blanca (`PFE:662-666`):
1. Si s'ha encertat una **altra** subpath → hi canvia (`selectPath(hitPath)`, `PFE:665`) i **no surt**.
2. Si no s'ha encertat res i l'eina és `select` → **obre marquesina** i buida la selecció de nodes (`PFE:666`).

Per tant: **deselecciona nodes, no surt del mode**. Idèntic diagnòstic que §P4.1.

> **Veredicte P4: cal X, i és la troballa que probablement explica el smoke.** No hi ha cap sortida de mode que no sigui Escape. Un usuari que no premi Escape es queda dins l'edició indefinidament — i amb `nodeMode` actiu **el botó Agrupar està deshabilitat** (`TSE:4391`), cosa que faria que el gest de P2 sembli trencat sense estar-ho.

💡 **PROPOSTA P4-A (a validar) — el patró de dos temps.** Primer clic al buit = deseleccionar (ja ho fa); segon clic al buit **sense selecció prèvia** = sortir del mode. És el que demana el brief i el que fa Illustrator. Requereix un callback nou fill→pare i un `if` a cada branca de clic-al-buit (`PFE:614-617`, `PFE:666`).

💡 **PROPOSTA P4-B (a validar) — clic fora de la pàgina = sortir, directament.** Al gris de treball no hi ha res a deseleccionar, així que el primer temps no aplica. Un `if` a `TSE:3195` abans del guard de pan.

💡 **PROPOSTA P4-C (a validar) — corregir el comentari de `TSE:2644`.** Diu que Escape és «equivalent al botó Cancel·lar»; no ho és des de la Fase 6a. Deute de documentació, cost zero, però enganya qui llegeixi el codi.

---

## BLOC P5 — Etiqueta de la cota (mida)

### P5.1 · On es decideix la mida, avui

**La mida NO es deriva del text. És un literal fixat a la inserció.**

- Inserció (`TSE:2966-2979`): `const TW = 24` (`:2973`) i el fill de text es crea amb `width: TW, height: 10, fontSize: 9, bgFill: KONVA_COL.pom, bgPadding: 2, align: 'center'` (`:2976`). Els **24 mm són constants** per a qualsevol `nom_fitxa`.
- Render del fons (`textBoxParts`, `TSE:969-982`), l'únic lloc on es calcula la caixa:
  ```js
  const pad = obj.bgPadding || 4          // :970
  const fs  = obj.fontSize || 11          // :971
  const w   = toPx(obj.width || 120)      // :972  ← de obj.width, no del text
  bg: { x:-pad, y:-pad, width: w + pad*2, height: fs*1.6 + pad*2, … }   // :975
  ```
- **Aquest descriptor és compartit entre pantalla i PDF**: live a `TSE:1513-1520` i export offscreen a `TSE:1217-1225`. Qualsevol canvi de mida hi ha de passar, o pantalla i PDF divergeixen.
- **`obj.height` no s'usa mai** per al fons: l'alçada surt de `fs * 1.6`, que assumeix **una sola línia**.
- ⚠️ **Incoherència d'unitats a `:975`**: l'amplada és `toPx(mm)` i l'alçada és `fontSize` en unitats de font, sumant-hi el mateix `pad` als dos eixos. Existeix des d'abans d'aquest sprint; **s'anota, no s'ha tocat**.

### P5.2 · Què caldria per a auto-mida

- **Konva sap mesurar**: `Konva` està importat al fitxer (`TSE:9`) i ja s'instancien `Konva.Text` offscreen per a l'export (`TSE:899`, `:1222`, `:1226`). **`measureSize` i `getTextWidth` NO apareixen enlloc** (0 coincidències) — la capacitat hi és, l'ús no.
- La restricció dura és la llei live=PDF: `textBoxParts` és una **funció pura de l'objecte**, i tots dos camins la criden. Mesurar dins d'ella significaria fer-hi una crida a Konva en temps de render.

💡 **PROPOSTA P5-A (a validar) — mesurar a la INSERCIÓ i desar `width`.** A `finishTwoClick` (`TSE:2976`), crear un `Konva.Text` temporal amb la mateixa família/mida/estil, llegir-ne l'amplada, i desar `width = ampladaMm + 2*padding` en lloc del `TW = 24`. **Avantatge**: `textBoxParts` no es toca, la puresa es manté i live=PDF segueix garantit per construcció. **Límit conegut**: si després s'edita el text des del panell (`updateText`, `TSE:3808`), l'amplada **no es recalcula**.

💡 **PROPOSTA P5-B (a validar) — mesurar dins `textBoxParts`.** Auto-mida sempre correcta, també després d'editar el text. **Cost**: una instància de `Konva.Text` per render de cada text amb fons; convindria memoïtzar per `(text, fontSize, fontFamily, fontStyle)`. És la que respecta millor el principi, i la més cara.

💡 **PROPOSTA P5-C (a validar) — recalcular a l'edició de text.** Complement de P5-A: cridar el mateix mesurador des d'`updateText` quan canvia `obj.text` i l'objecte té `bgFill`. Cobreix el forat de P5-A sense el cost per render de P5-B.

> **Veredicte P5: cal X, i hi ha tres camins clarament ordenats per cost.** Cap requereix tocar el render ni l'export si es mesura fora de `textBoxParts` (P5-A / P5-C).

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT

| # | Peça | Estat | Ancoratge | Risc |
|---|---|---|---|---|
| 1 | Marquesina d'OBJECTES | **EXISTEIX**, completa | `TSE:3017-3022`, `:3075-3083`, `:3106-3129` | Cap |
| 2 | Marquesina de NODES | **EXISTEIX** | `PFE:666`, `:672-675`, `:748-755` | Baix — limitada a la subpath activa (`PFE:753`) |
| 3 | Marquesina de FORMES | **NO EXISTEIX** | `PFE:594-618` (clic al buit només deselecciona) | — |
| 4 | Criteri de hit de marquesina | **DIFERENT** | Objectes = solapament (`TSE:3123`) · Nodes = contenció (`PFE:753`) | Baix, però es propagarà si no es fixa |
| 5 | Shift+clic de formes | **EXISTEIX** | `PFE:609` | Cap |
| 6 | Agrupar objectes | **EXISTEIX** i funciona | `TSE:2149-2169`, botó `:4391` | Cap |
| 7 | Desagrupar objectes | **EXISTEIX** | `TSE:2170-2179`, botó `:4392` | Cap |
| 8 | Fallada silenciosa de `groupSelection` | **EXISTEIX al codi, INABASTABLE per UI** | `TSE:2152` vs `:4645`, `:3119`, `:4851` | Baix |
| 9 | Agrupació VECTORIAL de formes | **NO EXISTEIX** | `grep group PFE` → 0 | — (el compound ja ho és: `TSE:1037`, `:1067`) |
| 10 | Primitiu "fusionar subpaths" | **EXISTEIX** | `booleanSubpaths` `paperOps.js:122` | Fusiona, **no** agrupa |
| 11 | Primitiu "treure un subpath" | **EXISTEIX** | `extractActiveSubpath` `TSE:3946` | Cap |
| 12 | Transformer sobre `path` | **EXISTEIX** | `blocksTransform` `TSE:1192` no l'exclou | — |
| 13 | Bake de l'escala a geometria (`path`) | **NO EXISTEIX** | `TSE:2868-2871` desa `scaleX/scaleY` | Mitjà — obliga PFE a desfer-ho (`PFE:436-452`) |
| 14 | Primitius de bake | **EXISTEIXEN i són purs** | `paperOps.js:96`, `:106`, `:86` | Cap |
| 15 | Pont acció→paperOps→document | **EXISTEIX** (numèric, dins nodes) | `PFE` opsRef → `markDirty` `:245` → `emit` `:800` | Cap |
| 16 | Pont drag-de-handle→paperOps | **NO EXISTEIX** | `TSE:2856` no importa `paperOps` | — |
| 17 | `enabledAnchors` per tipus | **NO EXISTEIX** | `TSE:4707` | Baix |
| 18 | Sortida de mode per clic (formes) | **NO EXISTEIX** | única sortida: Escape `TSE:2645-2656` | **ALT** — pot explicar el smoke sencer |
| 19 | Sortida de mode per clic (nodes) | **NO EXISTEIX** | `PFE:662-666` | **ALT** |
| 20 | Clic fora de la pàgina | **NO FA RES** | `TSE:3195-3196` surt d'hora | Mitjà |
| 21 | Comentari «equivalent al botó Cancel·lar» | **OBSOLET** | `TSE:2644` (el botó va caure a F6a) | Baix (documental) |
| 22 | Amplada de l'etiqueta de cota | **FIXA 24 mm** | `TSE:2973`, `:2976` | — |
| 23 | Mesura de text | **NO EXISTEIX** | 0 `measureSize`/`getTextWidth` a `TSE` | — |
| 24 | Alçada del fons de text | **DIFERENT** | `fs*1.6+pad*2` (`TSE:975`), 1 línia assumida, unitats barrejades | Baix, preexistent |
| 25 | Etiqueta de cota sense Transformer | **EXISTEIX (per disseny)** | `blocksTransform` exclou `text` amb `bgFill` (`TSE:1193`) | Cap |

---

### Obert / pendent de verificar

- **Quin dels dos camins de P2.2 falla realment per a l'Agus** (no tenir 2 objectes seleccionats vs. `nodeMode` actiu sense saber-ho). El codi permet els dos; **només ho pot dir qui ha fet el smoke**.
- Si l'Agus percep "no deselecciona" **dins** la pàgina o **fora**: són dos comportaments diferents (§P4.1 punts 1 i 3) i porten a dues correccions diferents.
- Comportament real de la marquesina d'objectes sobre un `group` (`getClientRect` d'un Group amb fills rotats): **no verificat al navegador**, només llegit (`TSE:3122`).
- No s'ha mesurat res al navegador: tots els valors són literals del codi.
