> ⚠️ SUPERADA 2026-07-07 — implementada (eines ploma/polígon/node/cota/buscatraços reals, S7-S8); substituïda per DIAGNOSI_EDITOR_ESTAT. Consulta només com a històric.

# RECOMPTE_EINES_EDITOR

Diagnosi read-only del que l'editor de fitxa sap fer avui. Abast principal:
`frontend/src/pages/TechSheetEditor.jsx`; components/connectors relacionats: `PaperFlatEditor.jsx`,
`TechSheetTemplateEditor.jsx`, endpoints `.ftt` i plantilles backend.

Llegenda d'estat:
- ✅ handler real: accionable avui.
- 🔵 preset: crea un conjunt/objecte predefinit.
- 🟡 feina: parcial, indirecte o implementat en una superfície incompleta.
- 🔴 placeholder: visible/marcat `soon` o reservat sense handler real.

## 1. Eines de dibuix/creació -> paleta esquerra

| Entrada | Estat | Què fa avui | Fitxer:línia | Proposta lloc |
|---|---:|---|---|---|
| Selecció `select` | ✅ | Mode per seleccionar/deseleccionar, arrossegar objectes i activar `Transformer`; shift afegeix/treu de multiselecció. | `frontend/src/pages/TechSheetEditor.jsx:1005-1006`, `:1100-1106`, `:1485-1487`, `:2124-2134` | Paleta esquerra |
| Selecció directa/nodes `node` | 🔴 | Apareix a `PALETTE` amb `soon: true`; no fa `setTool`. L'edició real de nodes existeix com a acció sobre flat/path, no com a eina de paleta. | `frontend/src/pages/TechSheetEditor.jsx:1887-1890`, `:2040-2042`, `:2377-2382` | Paleta esquerra, però cablejar a PaperFlatEditor |
| Subpath `subpath` | 🔴 | Placeholder `soon`, sense handler. | `frontend/src/pages/TechSheetEditor.jsx:1889-1890`, `:2040-2042` | Paleta esquerra |
| Dibuix lliure `draw` | ✅ | Arrossega punts i crea `type:'line'` polyline lliure. | `frontend/src/pages/TechSheetEditor.jsx:1505-1508`, `:1520-1523`, `:1555-1557` | Paleta esquerra |
| Ploma `pen` | 🔴 | Placeholder `soon`, sense handler. | `frontend/src/pages/TechSheetEditor.jsx:1892-1895`, `:2040-2042` | Paleta esquerra |
| Rectangle `rect` | ✅ | Drag/clic crea `type:'rect'`, contorn gold, fill transparent; clic petit crea mida per defecte. | `frontend/src/pages/TechSheetEditor.jsx:69-72`, `:1533-1546`, `:1895-1898` | Paleta esquerra |
| Rectangle arrodonit `rect_round` | ✅ | Mateix handler que rectangle, afegeix `cornerRadius:8`. | `frontend/src/pages/TechSheetEditor.jsx:69-72`, `:1533-1546`, `:1895-1898` | Paleta esquerra |
| El·lipse `ellipse` | ✅ | Drag crea `type:'ellipse'` amb rx/ry. No crea res si el drag és molt petit. | `frontend/src/pages/TechSheetEditor.jsx:69-72`, `:1547-1549`, `:1895-1899` | Paleta esquerra |
| Línia `line` | ✅ | Drag crea `type:'line'` amb dos punts. | `frontend/src/pages/TechSheetEditor.jsx:70-72`, `:1550-1551`, `:1900-1903` | Paleta esquerra |
| Línia de punts `line_dot` | ✅ | Mateix handler que línia, afegeix `dash:[4,4]`. | `frontend/src/pages/TechSheetEditor.jsx:70-72`, `:1550-1551`, `:1900-1903` | Paleta esquerra |
| Fletxa `arrow` | ✅ | Drag crea `type:'arrow'`; descarta distàncies <= 5px. | `frontend/src/pages/TechSheetEditor.jsx:70-72`, `:1552-1554`, `:1904-1907` | Paleta esquerra |
| Fletxa doble `arrow2` | ✅ | Mateix handler que fletxa, afegeix `arrow2:true` i `pointerAtBeginning`. | `frontend/src/pages/TechSheetEditor.jsx:70-72`, `:521-527`, `:1552-1554` | Paleta esquerra |
| Text `text` | ✅ | Clic crea text lliure; doble clic obre textarea inline. | `frontend/src/pages/TechSheetEditor.jsx:1489-1498`, `:1562-1572`, `:1910-1912`, `:2146-2154` | Paleta esquerra |
| Text-box `text_box` | ✅ | Clic crea text amb `bgFill:'transparent'` i `bgPadding`, renderitzat com a `Group` amb `Rect` darrere. | `frontend/src/pages/TechSheetEditor.jsx:474-486`, `:778-787`, `:1489-1498`, `:1910-1913` | Paleta esquerra |
| Imatge local | ✅ | Botó de paleta obre file input; també drag/drop d'imatge; crea `type:'image'` amb dataURL. | `frontend/src/pages/TechSheetEditor.jsx:1580-1596`, `:2090-2094`, `:2114-2115` | Paleta esquerra o Ribbon Inserció |
| Callout preset | 🔵 | Crea `group` amb text-box + fletxa. | `frontend/src/pages/TechSheetEditor.jsx:72`, `:1110-1119`, `:1500-1503`, `:1918-1921` | Paleta esquerra, grup anotació |
| Cercle detall preset | 🔵 | Crea `group` amb el·lipse + línia. | `frontend/src/pages/TechSheetEditor.jsx:72`, `:1121-1129`, `:1918-1921` | Paleta esquerra, grup anotació |
| Llegenda preset | 🔵 | Crea `group` amb rectangle + 3 textos. | `frontend/src/pages/TechSheetEditor.jsx:72`, `:1130-1138`, `:1918-1922` | Paleta esquerra, grup anotació |
| Flat vectorial nou | ✅ | Botó del dock insereix un `type:'path'` editable i entra en mode edició de nodes. | `frontend/src/pages/TechSheetEditor.jsx:1603-1628`, `:2221-2224` | Ribbon Inserció o paleta esquerra segons decisió |
| Importar flat SVG | ✅ | File input SVG, valida aspect ratio, converteix legacy SVG a `path` via Paper.js i obre edició de nodes. | `frontend/src/pages/TechSheetEditor.jsx:87-99`, `:907-985`, `:1629-1671`, `:2225-2230` | Ribbon Inserció |
| Editar nodes de flat/path | ✅ | Doble clic sobre `path` o botó propietats obre `PaperFlatEditor`; es poden seleccionar paths, arrossegar segments i handles, i comitar `paths`. | `frontend/src/pages/TechSheetEditor.jsx:740-747`, `:1672-1684`, `:2157-2169`, `:2377-2382`; `frontend/src/pages/PaperFlatEditor.jsx:99-175`, `:250-285`, `:309-350` | Dock dret per selecció + possible eina `node` |
| Cota POM | 🔴 | Placeholder `soon`; no hi ha objecte/handler. | `frontend/src/pages/TechSheetEditor.jsx:1915-1917` | Paleta esquerra o Ribbon Anotació |
| Nota | 🔴 | Placeholder `soon`; no hi ha objecte/handler més enllà del preset callout. | `frontend/src/pages/TechSheetEditor.jsx:1915-1917` | Paleta esquerra |
| Buscatraços/pathfinder | 🔴 | Flyout `soon`; union/subtract/intersect/difference no tenen handler. | `frontend/src/pages/TechSheetEditor.jsx:1924-1930`, `:2062-2079` | Paleta esquerra, grup modificar |
| Rotar com a eina | 🔴 | Placeholder `soon`; la rotació real viu al `Transformer`/propietats, no a una eina. | `frontend/src/pages/TechSheetEditor.jsx:1931-1932`, `:2428-2432` | Paleta esquerra placeholder; acció real al dock/ribbon |
| Escalar com a eina | 🔴 | Placeholder `soon`; l'escalat real és per `Transformer` o escala de `data_block`. | `frontend/src/pages/TechSheetEditor.jsx:1931-1932`, `:1435-1468`, `:2371-2375` | Paleta esquerra placeholder; propietats al dock |
| Mirall H/V a paleta | ✅ | Són `kind:'action'`, no eines; criden `mirrorObjects(...,'scaleX'/'scaleY')`. | `frontend/src/pages/TechSheetEditor.jsx:1107-1109`, `:1933-1934`, `:1953-1959`, `:2047-2055` | Ribbon Accions, no paleta |
| Crop | 🔴 | Placeholder `soon`, sense handler. | `frontend/src/pages/TechSheetEditor.jsx:1935-1936` | Paleta esquerra futura |
| Pan | 🔴 | Placeholder `soon`; el pan real és scroll del viewport, no eina. | `frontend/src/pages/TechSheetEditor.jsx:1937-1939`, `:2107` | Paleta esquerra/nav |
| Zoom fit a paleta | ✅ | Acció de paleta que crida `fitZoomToViewport`. | `frontend/src/pages/TechSheetEditor.jsx:1093-1098`, `:1937-1940`, `:1953-1957` | Ribbon/estat, no eina de dibuix |
| Cursor precís | 🔴 | Placeholder `soon`, sense handler. | `frontend/src/pages/TechSheetEditor.jsx:1937-1941` | Paleta esquerra futura |
| Swatches fill/stroke/swap | 🔴 | Botons deshabilitats; no hi ha color global d'eina. | `frontend/src/pages/TechSheetEditor.jsx:1943-1948`, `:2095-2102` | Dock dret/properties o peu de paleta si es crea estat global |

## 2. Accions sobre objectes -> ribbon

| Acció | Estat | On viu avui / handler | Fitxer:línia | Proposta lloc |
|---|---:|---|---|---|
| Alinear esquerra | ✅ | Barra contextual multi + dock multi; `alignSelection('left')`. | `frontend/src/pages/TechSheetEditor.jsx:1194-1217`, `:1995`, `:2257-2259` | Ribbon Accions |
| Alinear centre H | ✅ | Barra contextual multi + dock multi; `alignSelection('center')`. | `frontend/src/pages/TechSheetEditor.jsx:1208-1210`, `:1996`, `:2260-2262` | Ribbon Accions |
| Alinear dreta | ✅ | Barra contextual multi + dock multi; `alignSelection('right')`. | `frontend/src/pages/TechSheetEditor.jsx:1208-1211`, `:1997`, `:2263-2265` | Ribbon Accions |
| Alinear dalt | ✅ | Barra contextual multi + dock multi; `alignSelection('top')`. | `frontend/src/pages/TechSheetEditor.jsx:1211-1213`, `:1998`, `:2269-2271` | Ribbon Accions |
| Alinear mig V | ✅ | Barra contextual multi + dock multi; `alignSelection('middle')`. | `frontend/src/pages/TechSheetEditor.jsx:1211-1213`, `:1999`, `:2272-2274` | Ribbon Accions |
| Alinear baix | ✅ | Barra contextual multi + dock multi; `alignSelection('bottom')`. | `frontend/src/pages/TechSheetEditor.jsx:1211-1214`, `:2000`, `:2275-2277` | Ribbon Accions |
| Distribuir horitzontal | ✅ | Dock multi; requereix >=3 objectes; `distributeSelection('h')`. | `frontend/src/pages/TechSheetEditor.jsx:1218-1242`, `:2266-2268` | Ribbon Accions |
| Distribuir vertical | ✅ | Dock multi; requereix >=3 objectes; `distributeSelection('v')`. | `frontend/src/pages/TechSheetEditor.jsx:1218-1242`, `:2278-2280` | Ribbon Accions |
| Agrupar | ✅ | Dock multi; crea objecte `group` amb children localitzats i substitueix els objectes originals. | `frontend/src/pages/TechSheetEditor.jsx:1163-1183`, `:2251-2255` | Ribbon Accions |
| Desagrupar | ✅ | Dock selecció única `group`; globalitza children i elimina el group. | `frontend/src/pages/TechSheetEditor.jsx:1184-1193`, `:2434-2438` | Ribbon Accions |
| Mirall H/V | ✅ | Paleta `modify`, dock multi i dock objecte únic; alterna signe de `scaleX/scaleY`. Bloquejat per línies/fletxes/text-box. | `frontend/src/pages/TechSheetEditor.jsx:1107-1109`, `:1933-1934`, `:2282-2292`, `:2404-2414` | Ribbon Accions |
| Z-order endavant/enrere | ✅ | Capes + dock multi + dock únic; mou només dins capa `free`, un pas cada clic. | `frontend/src/pages/TechSheetEditor.jsx:1140-1162`, `:2177-2199`, `:2294-2304`, `:2416-2426` | Ribbon Accions o mini controls de capes |
| Z-order front/back absolut | 🔴 | No detectat: no hi ha "bring to front" ni "send to back", només forward/backward. | `frontend/src/pages/TechSheetEditor.jsx:1140-1162`, `:2194-2197` | Ribbon Accions, pendent |
| Rotació | ✅ | Via `Transformer` per objectes transformables i input numèric en dock únic; no per línia/fletxa/text-box. | `frontend/src/pages/TechSheetEditor.jsx:1435-1468`, `:2141-2142`, `:2428-2432` | Dock dret propietats + Ribbon Transformar |
| Escalat/redimensionat | ✅ | Via `Transformer`; per `data_block` escriu `scale`; per objectes geomètrics actualitza dimensions/radis. | `frontend/src/pages/TechSheetEditor.jsx:1435-1468`, `:2141-2142`, `:2371-2375` | Dock dret propietats + Ribbon Transformar |
| Eliminar | ✅ | Tecla Delete/Backspace per objectes `free`; botó al dock per `free` o `data_block`; multi elimina seleccionats `free`. | `frontend/src/pages/TechSheetEditor.jsx:1079-1088`, `:1401-1417`, `:2440-2444` | Ribbon Accions + tecla |

## 3. Inserció -> ribbon

| Inserció | Estat | Què fa avui | Fitxer:línia | Proposta lloc |
|---|---:|---|---|---|
| Capçalera model | ✅ | Insereix `data_block kind:'header'`; màxim 1 per pàgina; renderitza primitives de model i logo si existeix. | `frontend/src/pages/TechSheetEditor.jsx:386-417`, `:455-469`, `:1759-1770`, `:2206-2211` | Ribbon Inserció |
| Logo client | ✅ | Insereix logo del client com a imatge lliure si `model.customer_logo` existeix; avisa si no. | `frontend/src/pages/TechSheetEditor.jsx:1033`, `:1597-1602`, `:2212-2216` | Ribbon Inserció |
| Taula graduada `data_block` | ✅ | Llegeix `size-fittings`, demana `/fitting/<id>/graded-table/`, crea bloc natiu Konva amb autofit i cache `tableData`. | `frontend/src/pages/TechSheetEditor.jsx:292-384`, `:1323-1341`, `:1728-1757`, `:2217-2220`, `:2493-2505` | Ribbon Inserció |
| Flat sketch buit | ✅ | Insereix path vectorial inicial i obre editor de nodes. | `frontend/src/pages/TechSheetEditor.jsx:1603-1628`, `:2221-2224` | Ribbon Inserció |
| Importar flat SVG | ✅ | Llegeix SVG local, valida, converteix a `path`, substitueix selecció si era flat/path o crea nou objecte. | `frontend/src/pages/TechSheetEditor.jsx:1629-1671`, `:2225-2230` | Ribbon Inserció |
| Fitxers del model | ✅ | Llista `model-fitxers` actuals; cada botó baixa el fitxer i l'insereix com a imatge dataURL. | `frontend/src/pages/TechSheetEditor.jsx:1253-1255`, `:1710-1724`, `:2233-2246` | Ribbon Inserció o panell Assets |
| Imatge local/drop | ✅ | File input de paleta + drop al paper. | `frontend/src/pages/TechSheetEditor.jsx:1580-1596`, `:2090-2094`, `:2114-2115` | Ribbon Inserció o paleta |
| Presets d'anotació | 🔵 | Callout, detall i llegenda creen `group` preconfigurat. | `frontend/src/pages/TechSheetEditor.jsx:1110-1139`, `:1500-1503`, `:1918-1922` | Paleta esquerra o Ribbon Inserció > Presets |

## 4. Plantilles

| Element | Estat | Què fa avui | Fitxer:línia | Proposta lloc |
|---|---:|---|---|---|
| `TechSheetTemplate` per Customer | 🟡 | Model O2O `Customer`, deprecat però encara viu per editor de plantilla; desa `template_json` v2. Comentari diu 0 files BD. | `backend/fhort/models_app/tech_sheet_models.py:1-20`, `:21-30` | Gestió plantilles separada; Ribbon "Plantilles" si s'integra |
| Endpoints plantilla Customer | ✅ | GET get_or_create i PATCH gated `CONFIGURE`; PATCH exigeix `template_json`. | `backend/fhort/models_app/tech_sheet_editor_views.py:20-34`, `:37-54`; `backend/fhort/models_app/urls.py:151-155` | Admin/clients; no dock d'objecte |
| Serializer plantilla Customer | ✅ | Exposa `template_json`, `has_content`, `num_pages`. | `backend/fhort/models_app/tech_sheet_serializers.py:10-29` | Contracte backend |
| Front `TechSheetTemplateEditor` | 🟡 | Editor separat per `/clients/:id/plantilla`; reutilitza motor de `TechSheetEditor`, però amb eines reduïdes: select/text/rect/line/draw/image/header, sense taula graduada, fitxers model, lock ni formats de pàgina. | `frontend/src/pages/TechSheetTemplateEditor.jsx:8-24`, `:28-45`, `:288-317`, `:380-414` | Mantenir com a editor de plantilles o migrar a DocumentTemplate |
| Autosave plantilla | ✅ | Debounce 2s; fa `tmplApi.update(customerId,{template_json:{version:2,pages}})` si `canEdit`. No desa `pageFormat`. | `frontend/src/pages/TechSheetTemplateEditor.jsx:100-112`; `frontend/src/api/endpoints.js:212-215` | Global document |
| Export PDF plantilla | ✅ | Genera PDF local amb placeholders i logo customer. | `frontend/src/pages/TechSheetTemplateEditor.jsx:257-277`, `:299-301` | Ribbon Export |
| Header placeholder en plantilla | ✅ | `buildHeaderPrimitives(..., placeholderMode=true)` pinta `{model.codi}`, `{model.nom}`, etc. | `frontend/src/pages/TechSheetEditor.jsx:386-417`; `frontend/src/pages/TechSheetTemplateEditor.jsx:239-247`, `:355-356` | Inserció plantilla |
| `DocumentTemplate` | 🟡 | Model nou de plantilles `.ftt` reutilitzables amb `fitxer_template`, `metadata_schema`, `is_sample`, `origen`, `actiu`; no hi ha UI/endpoints de CRUD detectats per l'editor. | `backend/fhort/models_app/ftt_models.py:1-6`, `:38-65`; `backend/fhort/models_app/models.py:879` | Futura gestió plantilles document |
| Crear document des de plantilla | 🔴 | Endpoint de creació `.ftt` té `template_id` reservat, però avui crea document buit. | `backend/fhort/models_app/ftt_document_views.py:44-54` | Ribbon/flux crear fitxa, pendent |
| Aplicar/desar plantilla sobre `.ftt` | 🔴 | No detectat en `TechSheetEditor`: no hi ha acció d'aplicar plantilla ni desar document actual com a `DocumentTemplate`. | `frontend/src/pages/TechSheetEditor.jsx:1244-1275`, `:1343-1363`; `backend/fhort/models_app/ftt_models.py:38-65` | Ribbon Plantilles, pendent |

## 5. Propietats de selecció -> dock dret

| Tipus/selecció | Estat | Propietats editables avui | Fitxer:línia | Proposta lloc |
|---|---:|---|---|---|
| Derivació selecció | ✅ | `selectedObjects`, `selObj`, `multiSelected`, subconjunts multi stroke/fill/position/mirror/free. | `frontend/src/pages/TechSheetEditor.jsx:1855-1870` | Dock dret |
| Multi: agrupar | ✅ | Botó `groupSelection`. | `frontend/src/pages/TechSheetEditor.jsx:2251-2255` | Ribbon Accions |
| Multi: alineació/distribució | ✅ | 6 alineacions + 2 distribucions al dock. | `frontend/src/pages/TechSheetEditor.jsx:2256-2281` | Ribbon Accions |
| Multi: mirall H/V | ✅ | Visible si tots són mirrorables. | `frontend/src/pages/TechSheetEditor.jsx:2282-2292` | Ribbon Accions |
| Multi: z-order | ✅ | Endavant/enrere si hi ha seleccionats de capa `free`. | `frontend/src/pages/TechSheetEditor.jsx:2294-2304` | Ribbon Accions o capes |
| Multi: stroke | ✅ | Swatches + color natiu; aplica a rect/ellipse/line/arrow/path; arrow també actualitza `fill`. | `frontend/src/pages/TechSheetEditor.jsx:1861-1867`, `:2306-2311`, `:2513-2527` | Dock dret |
| Multi: fill/text color | ✅ | Aplica `fill` a text/rect/ellipse/path; mostra valor mixt. | `frontend/src/pages/TechSheetEditor.jsx:1862-1867`, `:2313-2318` | Dock dret |
| Multi: posició X/Y | ✅ | Edita `x/y` si tots els seleccionats tenen posició directa; exclou línies i fletxes. | `frontend/src/pages/TechSheetEditor.jsx:1863-1869`, `:2320-2332` | Dock dret |
| Text | ✅ | `fontSize`, bold via `fontStyle`, color de text (`fill`), X/Y, mirall, rotació, eliminar. Edició de contingut per doble clic. | `frontend/src/pages/TechSheetEditor.jsx:2339-2353`, `:2391-2402`, `:2404-2414`, `:2428-2432`; `:1562-1572` | Dock dret |
| Text-box | 🟡 | Render i edició de contingut existeixen, però `blocksTransform` li bloqueja `Transformer`/rotació; propietats de `bgFill` no tenen control explícit, només `fill` de text pel bloc `text`. | `frontend/src/pages/TechSheetEditor.jsx:474-486`, `:587-589`, `:778-787`, `:2339-2353` | Dock dret, afegir background explícit |
| Rect/ellipse | ✅ | Stroke, strokeWidth, fill, X/Y, mirall, z-order si free, rotació, eliminar. | `frontend/src/pages/TechSheetEditor.jsx:2355-2369`, `:2391-2426`, `:2428-2444` | Dock dret |
| Line/arrow | ✅ | Stroke, strokeWidth; drag mou punts; sense X/Y, sense rotació/mirall/Transformer per `blocksTransform`. Arrow sincronitza fill amb stroke. | `frontend/src/pages/TechSheetEditor.jsx:1420-1430`, `:2355-2364`, `:587-589` | Dock dret |
| Path/flat | ✅ | Stroke, strokeWidth, fill, editar nodes, substituir SVG si legacy, X/Y, mirall, z-order, rotació, eliminar. | `frontend/src/pages/TechSheetEditor.jsx:2355-2389`, `:2391-2444`; `frontend/src/pages/PaperFlatEditor.jsx:250-285`, `:309-350` | Dock dret |
| Image/logo/model file | 🟡 | X/Y, mirall, z-order, rotació, eliminar; dimensions/escala per `Transformer`, però no inputs numèrics width/height. | `frontend/src/pages/TechSheetEditor.jsx:571-575`, `:1435-1468`, `:2391-2444` | Dock dret |
| Data block header/taula | ✅ | Escala %, X/Y, rotació, eliminar; `Transformer` amb `keepRatio`; no color/contingut editable. | `frontend/src/pages/TechSheetEditor.jsx:578-585`, `:762-777`, `:1454-1456`, `:2141-2142`, `:2371-2375`, `:2391-2402`, `:2428-2444` | Dock dret |
| Group | ✅ | X/Y, mirall, z-order, rotació, desagrupar, eliminar; children no editables directament mentre agrupats. | `frontend/src/pages/TechSheetEditor.jsx:813-827`, `:1435-1445`, `:2404-2438` | Dock dret |
| Capes/lista objectes | ✅ | Selecció des de llista, icona per tipus, z-order pas a pas per objectes `free`. | `frontend/src/pages/TechSheetEditor.jsx:2174-2204` | Dock dret, subpanell Layers |

## 6. Accions globals de document -> ribbon/menú

| Acció global | Estat | Què fa avui | Fitxer:línia | Proposta lloc |
|---|---:|---|---|---|
| Export PDF | ✅ | Renderitza cada pàgina offscreen a PNG amb `pixelRatio 3.5`, crea PDF amb `pdf-lib`, puja EXPORT al Finder en mode `.ftt` i també descarrega localment. | `frontend/src/pages/TechSheetEditor.jsx:683-703`, `:1786-1824`; `backend/fhort/models_app/ftt_document_views.py:137-160`; `backend/fhort/models_app/services_ftt_document.py:135-153` | Ribbon superior, grup Export |
| Desar/autosave | ✅ | Debounce 2s amb lock; PATCH `.ftt`, crea nova versió i renova lock. No hi ha botó manual de desar. | `frontend/src/pages/TechSheetEditor.jsx:1343-1363`; `backend/fhort/models_app/ftt_document_views.py:79-100`; `backend/fhort/models_app/services_ftt_document.py:116-132` | Estat inferior + Ribbon Fitxer si cal |
| Lock/readonly/conflict | ✅ | Adquireix lock en obrir `.ftt`; unlock en unmount; badge/readonly/conflict a UI; backend TTL 30 min i renew en save. | `frontend/src/pages/TechSheetEditor.jsx:1007-1010`, `:1277-1300`, `:1827-1834`, `:2108-2111`; `backend/fhort/models_app/ftt_models.py:11-35`; `backend/fhort/models_app/services_ftt_document.py:20-83`; `backend/fhort/models_app/ftt_document_views.py:103-134` | Barra estat + menú document |
| Pàgines: navegar | ✅ | Miniatures clicables a tira inferior; canvia `currentPage` i neteja selecció. | `frontend/src/pages/TechSheetEditor.jsx:2452-2465` | Barra inferior o Ribbon Pàgina |
| Pàgines: afegir | ✅ | Afegeix pàgina buida si locked. | `frontend/src/pages/TechSheetEditor.jsx:1772-1777`, `:2466-2468` | Ribbon Pàgina |
| Pàgines: esborrar | ✅ | Confirma i elimina pàgina si n'hi ha més d'una. | `frontend/src/pages/TechSheetEditor.jsx:1778-1784`, `:2460-2463` | Ribbon Pàgina |
| Format de pàgina | ✅ | `A4L/A4P/A3L/A3P`; select contextual; es desa a `document_json.pageFormat`. | `frontend/src/pages/TechSheetEditor.jsx:34-40`, `:1022-1032`, `:2023-2027`, `:245-250` | Ribbon Pàgina |
| Zoom +/-/100/fit | ✅ | Estat `zoom`, clamp 25%-400%, ctrl/meta+wheel, botons barra inferior i acció de paleta `zoom_fit`. | `frontend/src/pages/TechSheetEditor.jsx:66-68`, `:83-85`, `:1090-1098`, `:1573-1578`, `:2478-2489` | Barra estat o Ribbon Vista |
| Undo/redo | 🔴 | No detectat a `TechSheetEditor.jsx`: cap stack d'historial ni handlers `undo/redo`. | Cerca `rg "undo|redo|history"`; resultats editor = cap stack, només version history a `ModelSheet`. | Ribbon/teclat, pendent |
| Versions `.ftt` | ✅ | Cada autosave genera nova versió `ModelFitxer`; footer mostra `v{sheet.versio}`; export s'enllaça a la versió origen. | `frontend/src/pages/TechSheetEditor.jsx:1352-1359`, `:1801-1813`, `:2473-2475`; `backend/fhort/models_app/services_ftt_document.py:8-9`, `:116-132` | Estat inferior + menú historial |
| Crear/carregar document `.ftt` | ✅ | Editor carrega `ftt-documents/<fitxerId>/`; backend té create/detail/asset endpoints. | `frontend/src/pages/TechSheetEditor.jsx:1261-1275`; `backend/fhort/models_app/ftt_document_views.py:44-77`, `:163-179`; `backend/fhort/models_app/urls.py:160-176` | Flux ModelSheet/Finder, no dock |
| Pausar tasca en sortir | ✅ | Si venia amb `task_id`, en cleanup transiciona tasca a `Paused`. | `frontend/src/pages/TechSheetEditor.jsx:1289-1297` | No és eina editor; flux task |

## 7. Duplicacions actuals

| Duplicació | Estat | Llocs duplicats | Fitxer:línia | Proposta |
|---|---:|---|---|---|
| Alineació multi | ✅ | Barra contextual superior i dock dret multi. | `frontend/src/pages/TechSheetEditor.jsx:1991-2001`, `:2256-2281` | Moure a Ribbon Accions; dock mostra només valors |
| Color stroke/fill selecció única | ✅ | Barra contextual i dock dret. | `frontend/src/pages/TechSheetEditor.jsx:2005-2016`, `:2355-2369` | Dock dret; ribbon pot tenir shortcuts compactes |
| Mirall H/V | ✅ | Paleta esquerra com `action`, dock multi i dock objecte únic. | `frontend/src/pages/TechSheetEditor.jsx:1933-1934`, `:2047-2055`, `:2282-2292`, `:2404-2414` | Ribbon Accions |
| Zoom fit | ✅ | Paleta esquerra nav i barra inferior. | `frontend/src/pages/TechSheetEditor.jsx:1937-1940`, `:1953-1957`, `:2487-2489` | Barra estat/Ribbon Vista |
| Z-order pas a pas | ✅ | Llista de capes, dock multi i dock objecte únic. | `frontend/src/pages/TechSheetEditor.jsx:2192-2199`, `:2294-2304`, `:2416-2426` | Ribbon Accions + opcional capes |
| Imatge local | ✅ | Paleta esquerra i drop al paper; inserció no és al bloc "Inserir". | `frontend/src/pages/TechSheetEditor.jsx:1580-1596`, `:2090-2094`, `:2114-2115` | Ribbon Inserció; conservar drop |
| Flat import | ✅ | Botó inserció i botó propietats "replace SVG" per legacy `sketch_svg`. | `frontend/src/pages/TechSheetEditor.jsx:2225-2230`, `:2383-2388` | Ribbon Inserció + dock només "Substituir" contextual |
| Eliminar | ✅ | Tecla Delete/Backspace i botó dock. | `frontend/src/pages/TechSheetEditor.jsx:1401-1417`, `:2440-2444` | Ribbon Accions + tecla; dock pot mantenir acció destructiva |
| Export PDF | ✅ | Topbar editor i topbar template editor. | `frontend/src/pages/TechSheetEditor.jsx:1974-1977`; `frontend/src/pages/TechSheetTemplateEditor.jsx:299-301` | Ribbon Fitxer/Export comú |
| Capçalera model | ✅ | Editor normal i editor plantilla tenen inserció de header, amb dades reals vs placeholders. | `frontend/src/pages/TechSheetEditor.jsx:1759-1770`, `:2206-2211`; `frontend/src/pages/TechSheetTemplateEditor.jsx:239-247`, `:383-386` | Ribbon Inserció compartit amb mode plantilla |
| Controls de pàgina | ✅ | Editor normal: tira inferior; template editor: columna esquerra. | `frontend/src/pages/TechSheetEditor.jsx:2452-2468`; `frontend/src/pages/TechSheetTemplateEditor.jsx:325-340` | Unificar en Ribbon/Pàgines o component compartit |

## 8. Pendents/placeholders marcats `soon`

| Placeholder | Estat | Confirmació | Fitxer:línia | Proposta lloc |
|---|---:|---|---|---|
| Ploma | 🔴 | `soon:true`; botó deshabilitat; no entra en `RECT_TOOLS`, `LINE_TOOLS`, `PRESET_TOOLS` ni handler stage. | `frontend/src/pages/TechSheetEditor.jsx:1893-1895`, `:2040-2042`, `:1505-1508` | Paleta esquerra |
| Buscatraços | 🔴 | Flyout sencer `soon`; eines internes sense handler. | `frontend/src/pages/TechSheetEditor.jsx:1924-1930`, `:2062-2079` | Paleta esquerra/modificar |
| Cota POM | 🔴 | `soon:true`; no hi ha objecte ni handler. | `frontend/src/pages/TechSheetEditor.jsx:1915-1917`, `:2040-2042` | Paleta esquerra/anotació |
| Nota | 🔴 | `soon:true`; només existeix preset callout com alternativa real. | `frontend/src/pages/TechSheetEditor.jsx:1915-1918`, `:1110-1119` | Paleta esquerra |
| Crop | 🔴 | `soon:true`; no hi ha handler per retallar imatges. | `frontend/src/pages/TechSheetEditor.jsx:1935-1936` | Paleta esquerra o dock imatge |
| Pan | 🔴 | `soon:true`; viewport és scrollable però no hi ha eina mà. | `frontend/src/pages/TechSheetEditor.jsx:1937-1939`, `:2107` | Paleta esquerra/nav |
| Cursor precís | 🔴 | `soon:true`; cap handler. | `frontend/src/pages/TechSheetEditor.jsx:1939-1941` | Paleta esquerra/nav |
| Subpath | 🔴 | `soon:true`; no hi ha selecció de subpath diferenciada a `PaperFlatEditor`. | `frontend/src/pages/TechSheetEditor.jsx:1889-1890`; `frontend/src/pages/PaperFlatEditor.jsx:178-183` | Paleta esquerra/node |
| Swatches fill/stroke/swap | 🔴 | Botons deshabilitats; no hi ha estat global de colors d'eina. | `frontend/src/pages/TechSheetEditor.jsx:1943-1948`, `:2095-2102` | Dock dret o peu de paleta |
| Rotate/resize com eines | 🔴 | Placeholder; transform real existeix via `Transformer`/inputs, però no com a mode d'eina. | `frontend/src/pages/TechSheetEditor.jsx:1931-1932`, `:1435-1468`, `:2428-2432` | Ribbon/dock, no paleta |

## Proposta inicial de repartiment en 3 llocs

### Paleta esquerra = dibuix/creació

Mantenir aquí: `select`, futur `node/subpath`, `draw`, futur `pen`, formes, línies, fletxes, text/text-box,
presets d'anotació, i eventualment cota POM/nota. Treure d'aquí les accions no-creatives: mirall H/V i zoom fit.
Decidir si `flat_insert` viu aquí com a eina vectorial o al Ribbon Inserció; avui és botó de dock però conceptualment
és creació vectorial.

### Ribbon superior = accions i inserció

Grups suggerits:
- Fitxer: export PDF, estat/desar, versions/historial quan existeixi.
- Pàgina: add/delete/navegar/format A4/A3 i zoom.
- Inserir: capçalera, logo client, taula graduada, imatge local, fitxers model, flat SVG, presets si no van a paleta.
- Organitzar: alinear, distribuir, agrupar/desagrupar, z-order, mirall, eliminar.
- Plantilles: aplicar/desar plantilla quan `DocumentTemplate` tingui UI real; avui només hi ha `TechSheetTemplateEditor` separat i `DocumentTemplate` backend parcial.

### Dock dret = propietats de selecció

Concentrar aquí valors editables: stroke/fill/text color, strokeWidth, fontSize/bold, X/Y, rotació, escala de
`data_block`, editar nodes/substituir SVG, desagrupar contextual i capes. Treure del dock les accions massives
duplicades (alinear/distribuir/mirall/z-order) o deixar-les només com a accessos contextuals secundaris.

## Notes de frontera

- No he trobat `TOOL_GROUPS` actiu: la configuració actual és `PALETTE` amb flyouts i `PALETTE_SWATCHES`.
- L'editor principal treballa sobre `.ftt` (`ModelFitxer TIPUS_TECHSHEET`) i ja no sobre `TechSheet` O2O; `TechSheetTemplate` queda només per plantilles Customer.
- `DocumentTemplate` existeix com a model, però no apareix cablejat a l'editor per aplicar/desar plantilles.
- La llista "alinear (8)" del context correspon avui a 6 alineacions + 2 distribucions; no hi ha align-to-page ni align-to-selection extra fora d'això.
