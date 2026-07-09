> ⚠️ SUPERADA 2026-07-07 — implementada (multiselecció + grups, sprint S1); substituïda per DIAGNOSI_EDITOR_ESTAT. Consulta només com a històric.

# DIAGNOSI — Editor de fitxa: capa d'interacció

Data: 2026-06-27  
Abast: `/var/www/ftt-staging/frontend`, lectura de codi + documentació de diagnosi.  
Fitxer principal: `frontend/src/pages/TechSheetEditor.jsx`.

## 0. Resum curt

FET: L'editor és un canvas Konva multipàgina amb eines de selecció, text, imatge, formes, línies/dibuix i blocs de dades; ho declara el comentari de capçalera. `frontend/src/pages/TechSheetEditor.jsx:8-15`

FET: La interacció actual és monoselecció (`selectedId`) + eina activa (`tool`) + un `Konva.Transformer` associat al node seleccionat. `frontend/src/pages/TechSheetEditor.jsx:504-505`, `frontend/src/pages/TechSheetEditor.jsx:697-714`, `frontend/src/pages/TechSheetEditor.jsx:1148-1149`

FET: No s'ha trobat cap estat de multiselecció, cap ús de `shiftKey`/`ctrlKey`/`metaKey`, cap `children[]`, cap UI de z-order/capes ni cap control de rotació en `TechSheetEditor.jsx`. Cerca: `group|children|multi|shiftKey|ctrlKey|metaKey|bring|send|z-order|rotate|rotation`.

💡 PROPOSTA (a validar): Per Fase 3, el camí curt és ampliar el model actual en lloc de substituir-lo: mantenir `pages[].objects[]`, afegir `type: 'group'` com a objecte més, i fer que live/offscreen recorrin `children[]` amb el mateix render existent.

⚖️ DECISIÓ AGUS: confirmar si F3 vol "agrupar com a estructura persistent" (`group.children[]`) o "agrupar només com a operació d'edició" que després aplana objectes.

## 1. Selecció, moviment i transformació

FET: Els objectes live reben `id`, `x/y`, `draggable`, `onClick`, `onTap`, `onDragEnd` i `onTransformEnd` des d'un objecte `common` dins `ObjectNode`. `frontend/src/pages/TechSheetEditor.jsx:416-425`

FET: El clic/tap sobre un objecte seleccionable crida `setSelectedId(o.id)`. `frontend/src/pages/TechSheetEditor.jsx:1132-1141`

FET: El fons de l'Stage desselecciona quan l'eina activa és `select` i el target és el propi Stage. `frontend/src/pages/TechSheetEditor.jsx:777-783`

FET: Els objectes només són seleccionables si l'editor té lock i l'objecte no és de capa `template`. `frontend/src/pages/TechSheetEditor.jsx:1135-1137`

FET: Els objectes només són arrossegables si hi ha lock, l'eina és `select`, i la capa no és `template`. `frontend/src/pages/TechSheetEditor.jsx:1135-1139`

FET: El `Transformer` existeix i té `rotateEnabled={false}`; per tant no hi ha rotació via UI actual. `frontend/src/pages/TechSheetEditor.jsx:1148-1149`

FET: El `Transformer` es lliga a un sol node: `tr.nodes(node ? [node] : [])`. `frontend/src/pages/TechSheetEditor.jsx:706-710`

FET: No tots els objectes són redimensionables: línies, fletxes, text amb fons i template no entren al `Transformer`. `frontend/src/pages/TechSheetEditor.jsx:702-710`

FET: El moviment de línies actualitza tots els punts sumant el desplaçament i torna el node a posició 0,0. `frontend/src/pages/TechSheetEditor.jsx:733-740`

FET: El moviment de fletxes actualitza `x/y/x2/y2` amb el desplaçament i torna el node a 0,0. `frontend/src/pages/TechSheetEditor.jsx:741-745`

FET: El moviment de la resta d'objectes actualitza `x/y` en mm. `frontend/src/pages/TechSheetEditor.jsx:745-747`

FET: En transform, `data_block` desa escala a `obj.scale`; `ellipse` desa `rx/ry`; text/rect/image desen `width` i, excepte text, `height`. `frontend/src/pages/TechSheetEditor.jsx:749-769`

FET: Delete/Backspace només esborra si hi ha objecte seleccionat, lock, no s'està editant text, el focus no és input/textarea/select, i l'objecte és de capa `free`. `frontend/src/pages/TechSheetEditor.jsx:716-731`

Què NO hi ha:
- FET: No hi ha multiselecció.
- FET: No hi ha marc de selecció per arrossegar sobre una àrea.
- FET: No hi ha transformació de línies/fletxes per handles de punt.
- FET: No hi ha rotació.

## 2. Creació d'elements

FET: L'estat `tool` governa la creació; arrenca com `select`. `frontend/src/pages/TechSheetEditor.jsx:504-505`

FET: Les eines de formes són `rect`, `rect_round`, `ellipse`; les eines de línia/dibuix són `line`, `line_dot`, `arrow`, `arrow2`. `frontend/src/pages/TechSheetEditor.jsx:51-54`

FET: La topbar mostra la paleta d'eines només si `locked` és cert. `frontend/src/pages/TechSheetEditor.jsx:1048-1083`

FET: La paleta està agrupada en desplegables: Formes (`rect`, `rect_round`, `ellipse`), Dibuix (`line`, `line_dot`, `arrow`, `arrow2`, `draw`) i Text (`text`, `text_box`). `frontend/src/pages/TechSheetEditor.jsx:1009-1027`

FET: L'eina d'imatge és un botó separat que obre un `<input type="file" accept="image/*">`. `frontend/src/pages/TechSheetEditor.jsx:1077-1081`

FET: En clicar amb eina `text` o `text_box`, es crea un objecte `type: 'text'`, `layer: 'free'`, amb text inicial "Doble clic per editar", `fontSize: 11`, `fontFamily: FONT`; `text_box` afegeix `bgFill` i `bgPadding`. `frontend/src/pages/TechSheetEditor.jsx:785-792`

FET: Rectangles, el·lipses, línies, fletxes i dibuix lliure es creen amb mouse down/move/up i un preview temporal `drawTemp`. `frontend/src/pages/TechSheetEditor.jsx:794-837`, `frontend/src/pages/TechSheetEditor.jsx:1143-1147`

FET: `rect` i `rect_round` acaben com `type: 'rect'`; `rect_round` només afegeix `cornerRadius: 8`. `frontend/src/pages/TechSheetEditor.jsx:820-823`

FET: `line_dot` acaba com `type: 'line'` amb `dash: [4, 4]`. `frontend/src/pages/TechSheetEditor.jsx:827-828`

FET: `arrow2` acaba com `type: 'arrow'` amb `arrow2: true`. `frontend/src/pages/TechSheetEditor.jsx:829-831`

FET: `draw` acaba com `type: 'line'` amb una llista de punts. `frontend/src/pages/TechSheetEditor.jsx:832-833`

FET: Les imatges locals/drop es desen com `type: 'image'`, `layer: 'free'`, `src: dataURL`. `frontend/src/pages/TechSheetEditor.jsx:851-867`

FET: El logo del client s'insereix com `type: 'image'`, `kind: 'logo'`, `layer: 'free'`. `frontend/src/pages/TechSheetEditor.jsx:868-873`

FET: Els fitxers del model es poden inserir com imatge carregant el blob, convertint-lo a dataURL i cridant `addImageFromDataURL`. `frontend/src/pages/TechSheetEditor.jsx:874-887`, `frontend/src/pages/TechSheetEditor.jsx:1186-1199`

FET: Els blocs de dades s'insereixen des de l'aside dret: capçalera de model i taula graduada. `frontend/src/pages/TechSheetEditor.jsx:1166-1184`

FET: La taula graduada crea `type: 'data_block'`, `kind: 'graded_table'`, `layer: 'data'`, `size_fitting_id`, `x/y`, `scale`, `width/height`. `frontend/src/pages/TechSheetEditor.jsx:892-915`

FET: La capçalera crea `type: 'data_block'`, `kind: 'header'`, `layer: 'data'`; només se'n permet una per pàgina. `frontend/src/pages/TechSheetEditor.jsx:923-933`

💡 PROPOSTA (a validar): La barra d'eines F3 pot viure a la topbar actual (`TOOL_GROUPS`) per eines ràpides i a l'aside dret per insercions estructurades. Si calen "callout", "detail circle", "legenda", etc., es poden exposar com presets que creen objectes existents o grups d'objectes existents.

## 3. Propietats i edició

FET: El panell de propietats existeix a l'aside dret i només renderitza quan hi ha `selObj` i `locked`. `frontend/src/pages/TechSheetEditor.jsx:1201-1263`

FET: Per text, el panell permet `fontSize`, bold via `fontStyle`, i color de text via `fill`. `frontend/src/pages/TechSheetEditor.jsx:1205-1219`

FET: El text també té edició inline: doble clic/tap obre un `<textarea>` overlay, blur confirma, Enter confirma i Escape cancel·la. `frontend/src/pages/TechSheetEditor.jsx:839-849`, `frontend/src/pages/TechSheetEditor.jsx:1153-1161`

FET: Per `rect`, `ellipse`, `line` i `arrow`, el panell permet color de traç (`stroke`) i gruix (`strokeWidth`). En fletxes, canviar `stroke` també actualitza `fill`. `frontend/src/pages/TechSheetEditor.jsx:1221-1230`

FET: Per `rect` i `ellipse`, el panell permet `fill`. `frontend/src/pages/TechSheetEditor.jsx:1232-1235`

FET: Per `data_block`, el panell permet escala en percentatge. `frontend/src/pages/TechSheetEditor.jsx:1237-1242`

FET: Per objectes que no són `line` ni `arrow`, el panell permet posició `x/y` en mm. `frontend/src/pages/TechSheetEditor.jsx:1243-1255`

FET: El panell permet esborrar si l'objecte és `layer === 'free'` o `type === 'data_block'`. `frontend/src/pages/TechSheetEditor.jsx:1256-1260`

FET: `fontFamily` es fixa en crear text amb `FONT` i en render cau a `obj.fontFamily || FONT`; no hi ha selector de font al panell. `frontend/src/pages/TechSheetEditor.jsx:40`, `frontend/src/pages/TechSheetEditor.jsx:785-790`, `frontend/src/pages/TechSheetEditor.jsx:453-455`

FET: Els colors de canvas són literals perquè Konva no resol CSS variables; el codi ho documenta explícitament. `frontend/src/pages/TechSheetEditor.jsx:45-49`

FET: El `ColorPicker` ofereix swatches ràpids i `<input type="color">`; escriu directament a `obj.fill/stroke`. `frontend/src/pages/TechSheetEditor.jsx:1288-1301`

Què NO hi ha:
- FET: No hi ha panell de propietats per `width/height` genèrics, només transform visual i X/Y per alguns tipus.
- FET: No hi ha selector de `fontFamily`.
- FET: No hi ha controls de line cap/join, puntes de fletxa avançades, opacitat, bloqueig o visibilitat.

## 4. Z-order i capes

FET: Les capes lògiques són `template`, `data`, `free`, amb ordre `template:0`, `data:1`, `free:2`. `frontend/src/pages/TechSheetEditor.jsx:51`

FET: Tant l'export/thumbnail offscreen com el render live ordenen objectes per `LAYER_ORDER`. `frontend/src/pages/TechSheetEditor.jsx:320-322`, `frontend/src/pages/TechSheetEditor.jsx:1005-1007`

FET: El render live pinta tots els objectes ordenats dins una sola `<Layer>` de Konva; el comentari diu que Konva no agrupa per `layer`, sinó que s'ordena l'array. `frontend/src/pages/TechSheetEditor.jsx:1126-1133`

FET: Els objectes `template` no són seleccionables ni arrossegables. `frontend/src/pages/TechSheetEditor.jsx:1135-1137`

FET: Les insercions lliures (`text`, formes, línies, imatges locals/model/logo) usen `layer: 'free'`. `frontend/src/pages/TechSheetEditor.jsx:785-792`, `frontend/src/pages/TechSheetEditor.jsx:818-833`, `frontend/src/pages/TechSheetEditor.jsx:851-873`

FET: Les insercions estructurades de capçalera/taula usen `layer: 'data'`. `frontend/src/pages/TechSheetEditor.jsx:907-910`, `frontend/src/pages/TechSheetEditor.jsx:930-932`

FET: No hi ha cap UI de llista de capes, reordenació, "bring forward/back", bloqueig de capa o canvi de capa. Cerca: `bring|send|z-order|moveToTop|moveToBottom`.

💡 PROPOSTA (a validar): Si F3 necessita z-order dins d'una mateixa capa, cal decidir si l'ordre és l'ordre de `objects[]` després d'ordenar per capa, o si s'afegeix un camp explícit `z`. Avui dos objectes de la mateixa capa conserven l'ordre relatiu de l'array quan el sort és estable, però no hi ha cap UI per modificar-lo.

⚖️ DECISIÓ AGUS: definir si una UI de capes entra a F3 o si F3 només introdueix presets/grups sense exposar z-order.

## 5. On enganxar `group` perquè sobrevisqui i pinti als dos motors

FET: El document `.ftt` es converteix a v2 amb `documentToV2`; actualment només substitueix `src: 'assets/...'` per URL a nivell dels objectes de `pages[].objects[]`. `frontend/src/pages/TechSheetEditor.jsx:63-76`

FET: La inversa `v2ToDocument` només substitueix URLs per `assets/<nom>` a nivell dels objectes de `pages[].objects[]`. `frontend/src/pages/TechSheetEditor.jsx:82-95`

FET: `serializePages` retorna tots els objectes tal qual, excepte `data_block`, on elimina `src`. `frontend/src/pages/TechSheetEditor.jsx:392-401`

FET: El render offscreen és una if-chain dins `renderPageToDataURL`: `text`, `rect`, `ellipse`, `line`, `arrow`, `data_block`, `image`. No hi ha branca `group`. `frontend/src/pages/TechSheetEditor.jsx:312-390`

FET: El render live és una if-chain dins `ObjectNode`: `data_block`, `text`, `rect`, `ellipse`, `line`, `arrow`, `image`; si no encaixa, retorna `null`. No hi ha branca `group`. `frontend/src/pages/TechSheetEditor.jsx:416-484`

FET: L'autosave de `.ftt` desa `v2ToDocument(serializePages(pages), pageFormat, ...)` a `document_json`. `frontend/src/pages/TechSheetEditor.jsx:661-681`

Punts exactes a tocar per `group`:
- FET: Persistència pack/unpack: `documentToV2` i `v2ToDocument` haurien de recórrer `children[]` si els fills poden tenir `src` d'asset. `frontend/src/pages/TechSheetEditor.jsx:63-95`
- FET: Serialització: `serializePages` hauria de serialitzar recursivament `children[]` i aplicar la regla de `data_block` també dins de grups. `frontend/src/pages/TechSheetEditor.jsx:392-401`
- FET: Render offscreen: afegir branca `o.type === 'group'` a `renderPageToDataURL`, creant `Konva.Group` i renderitzant-hi fills amb transform local. `frontend/src/pages/TechSheetEditor.jsx:322-384`
- FET: Render live: afegir branca `obj.type === 'group'` a `ObjectNode`, retornant `<Group {...common}>...</Group>` amb children renderitzats. `frontend/src/pages/TechSheetEditor.jsx:416-484`
- FET: Interacció: decidir si un `group` és transformable pel `Transformer`; avui el filtre de no-resize només exclou line/arrow/text_box/template, així que un `group` no exclòs intentaria transformar-se si `ObjectNode` li posa `id` i dimensions útils. `frontend/src/pages/TechSheetEditor.jsx:697-714`, `frontend/src/pages/TechSheetEditor.jsx:1148-1149`
- FET: Propietats: el panell actual no té cas `group`; només rebria X/Y perquè no és line/arrow, i delete si `layer === 'free'`. `frontend/src/pages/TechSheetEditor.jsx:1201-1263`

💡 PROPOSTA (a validar): Implementar una funció interna compartida de render "objecte → Konva" per reduir drift entre `ObjectNode` i `renderPageToDataURL`. Avui són dues if-chains paral·leles, i `group` duplicaria aquesta lògica.

💡 PROPOSTA (a validar): Model JSON de grup mínim:

```json
{
  "id": "...",
  "type": "group",
  "layer": "free",
  "x": 10,
  "y": 20,
  "children": [
    { "id": "...", "type": "text", "x": 0, "y": 0, "text": "..." },
    { "id": "...", "type": "arrow", "x": 30, "y": 8, "x2": 60, "y2": 8 }
  ]
}
```

⚖️ DECISIÓ AGUS: si els fills del grup mantenen `id` seleccionable individualment o si el grup és una unitat tancada fins que hi hagi "desagrupar".

## 6. Mapatge de tipus "nous" sobre existents

FET: Ja existeix `text` i una variant `text_box` implementada com `type: 'text'` amb `bgFill/bgPadding`. `frontend/src/pages/TechSheetEditor.jsx:785-792`, `frontend/src/pages/TechSheetEditor.jsx:441-456`

FET: Ja existeixen `rect` i `rect_round`; `rect_round` és `type: 'rect'` amb `cornerRadius`. `frontend/src/pages/TechSheetEditor.jsx:820-823`

FET: Ja existeix `ellipse`. `frontend/src/pages/TechSheetEditor.jsx:824-826`, `frontend/src/pages/TechSheetEditor.jsx:463-466`

FET: Ja existeixen `line`, `line_dot`, `draw`; tots acaben com `type: 'line'`, amb `dash` o punts múltiples segons el cas. `frontend/src/pages/TechSheetEditor.jsx:827-833`, `frontend/src/pages/TechSheetEditor.jsx:468-471`

FET: Ja existeixen `arrow` i `arrow2`; tots acaben com `type: 'arrow'`, amb `arrow2: true` per doble punta. `frontend/src/pages/TechSheetEditor.jsx:829-831`, `frontend/src/pages/TechSheetEditor.jsx:473-478`

FET: Ja existeix `image` per upload/drop/model files/logo. `frontend/src/pages/TechSheetEditor.jsx:851-887`, `frontend/src/pages/TechSheetEditor.jsx:480-481`

FET: Ja existeix `data_block` amb `kind: 'header'` i `kind: 'graded_table'`. `frontend/src/pages/TechSheetEditor.jsx:357-373`, `frontend/src/pages/TechSheetEditor.jsx:426-439`, `frontend/src/pages/TechSheetEditor.jsx:892-933`

Mapatge proposat:
- 💡 `callout`: no cal tipus nou si és simple; pot ser un preset que crea `group` amb `text`/`text_box` + `arrow`. Sense `group`, es pot crear com dos objectes independents però no es mouran junts.
- 💡 `detail_circle`: no cal tipus nou; pot ser `ellipse` amb `fill: transparent` i stroke destacat.
- 💡 `label/etiqueta`: no cal tipus nou; pot ser `text_box`.
- 💡 `legend/llegenda`: pot ser `group` de `rect` + diversos `text`, o bé un nou `data_block kind: 'legend'` si ha de derivar de dades del model.
- 💡 `table/taula manual`: si és dades vives del model, encaixa millor com `data_block kind:*`; si és decorativa/manual, avui no hi ha taula editable genèrica i convindria decidir entre `group` de primitives o nou `data_block`.
- 💡 `measurement table`: ja existeix `data_block kind: 'graded_table'`.
- 💡 `header/cartutx`: ja existeix `data_block kind: 'header'`.

⚖️ DECISIÓ AGUS: separar "presets visuals" (combinacions d'objectes existents) de "blocs vius" (`data_block`) abans d'afegir tipus nous.

## 7. Llocs naturals per Fase 3

💡 Barra d'eines: ampliar `TOOL_GROUPS` per eines/presets ràpids. `frontend/src/pages/TechSheetEditor.jsx:1009-1027`

💡 Inserció estructurada: ampliar l'aside dret on ara viuen `insertHeader`, `insertLogo`, `onAddTableClick` i fitxers del model. `frontend/src/pages/TechSheetEditor.jsx:1166-1199`

💡 Propietats: ampliar el bloc `{selObj && locked && (...)}` amb casos per `group` i presets nous. `frontend/src/pages/TechSheetEditor.jsx:1201-1263`

💡 Capa d'interacció: `selectedId`, `handleDragEnd`, `handleTransformEnd`, `ObjectNode` i `Transformer` són el nucli a tocar per group/multiselecció. `frontend/src/pages/TechSheetEditor.jsx:504-505`, `frontend/src/pages/TechSheetEditor.jsx:697-769`, `frontend/src/pages/TechSheetEditor.jsx:1117-1150`

⚖️ DECISIÓ AGUS: prioritzar una d'aquestes tres opcions F3:
1. Presets sense group persistent: ràpid, però no resol moure/editar conjuntament.
2. `group` persistent monoselecció: bon equilibri; cal tocar persistència + dos renders + propietats.
3. Multiselecció + group/desgroup: més complet, però requereix canviar l'estat `selectedId` a una col·lecció i revisar Transformer/propietats.

