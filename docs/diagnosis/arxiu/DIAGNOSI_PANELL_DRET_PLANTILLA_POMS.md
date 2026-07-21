> ⚠️ SUPERADA 2026-07-21 — implementada pel sprint Patró B end-to-end (fases 1-7, commits
> 73babdb→254eaa8). Consulta només com a històric.

# DIAGNOSI — Panell dret: mode plantilla, patró col·lapsable i contenidor de POMs

Data: 2026-07-21 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

**Abast.** Tres preguntes de desbloqueig per al panell dret de l'editor de fitxa tècnica: si el "mode plantilla" existeix formalment i què caldria per fer-lo explícit (P1); quin patró de contenidor col·lapsable ja existeix i com està el panell dret avui (P2); d'on surten els POMs, com és l'eina de cota i què caldria per pre-carregar text+estil des d'un POM (P3).

**Convenció.** Cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi** (verificat amb grep), no especulat. Les propostes van marcades 💡 i estan separades dels fets: **les decisions són humanes (Patró C)**.

**Diagnosis germanes vigents:** `DIAGNOSI_EDITOR_ESTAT.md`, `DIAGNOSI_W6_I_FITXA.md`, `DIAGNOSI_FTT_BIBLIOTECA.md`, `DIAGNOSI_CICLE_POM_MESURES_ESCALAT_2026-06-26.md`.

---

## Resum executiu

1. **El mode plantilla NO EXISTEIX formalment.** L'única ruta d'editor (`frontend/src/App.jsx:255`) sempre té un model host; una plantilla es fabrica per **convenció humana** (obrir un document, posar-hi xips `field`, desar-lo com a plantilla) i cap guard ho comprova — `TechSheetEditor.jsx:5060` és l'única condició propera i només mira `dockTab`+`locked`.

2. **La palanca per a (a) i (b) ja existeix i està morta.** `placeholderMode` està **cablat de dalt a baix** pel render (`TechSheetEditor.jsx:1421` → `:903`, `:573`, `:812`) però **mai s'activa al camí viu**: la crida real al canvas (`:4528-4531`) no el passa. Els únics tres punts que el posen a `true` (`TechSheetTemplateEditor.jsx:122`, `:266`, `:359`) són d'una pàgina **jubilada i sense ruta**. No cal inventar l'estat: cal l'interruptor.

3. **Forat crític col·lateral (bloquejant per a la plantilla, fora del brief).** `save-as-template` **NO descongela**: empaqueta el document tal qual (`ftt_document_views.py:200-203`). Una plantilla desada des d'un document instanciat s'emporta els valors del model host **com a text literal**. L'invers exacte ja existeix i no s'hi crida: `unfreeze_document` (`services_ftt_document.py:312`).

4. **NO EXISTEIX cap component col·lapsable compartit.** L'únic amb API real és `Contenidor` (`TallerPatro.jsx:1310`), local i amb 3 consumidors del mateix fitxer; hi ha **12 còpies inline** i **dues convencions de chevron contradictòries**. **Cap bloc del panell dret és col·lapsable avui** (cap chevron al rang `TechSheetEditor.jsx:4637-5077`).

5. **El contenidor de POMs a l'editor NO EXISTEIX**, però el **patró de presentació canònic sí**: `PomNamePair` (`POMBrowser.jsx:530-541`), amb la llei del sector escrita al codi (`:528`). L'endpoint que l'editor ja fa servir **no serveix**: `base-measurements` no retorna `nom_en` (`wizard_views.py:322`).

6. **FRONTERA G1 CONFIRMADA.** **NO EXISTEIX vincle viu cota↔POM/mesura**: l'objecte de cota no desa cap referència (`TechSheetEditor.jsx:2872-2882`). El patró vigent és el contrari del vincle — snapshot congelat, llei escrita al codi (`:3368-3369`). Res del disseny actual contradiu G1.

7. **NO EXISTEIX cap token vermell a `KONVA_COL`** de l'editor (`TechSheetEditor.jsx:90`): caldria definir-lo. Hi ha precedent de valor al mateix fitxer (`TBL.REF: '#dc2626'`, `:394`).

---

## BLOC P1 — Mode plantilla

### P1.1 · Existeix formalment? Com es crea una plantilla avui

- **NO EXISTEIX** cap flag, ruta ni estat de React que signifiqui "estic construint una plantilla". L'única ruta d'editor és `/models/:id/ftt/:fitxerId` (`App.jsx:255`): **sempre hi ha model host**.
- Dos models coexisteixen:
  - `TechSheetTemplate` (`tech_sheet_models.py:13`) — O2O amb Customer, **DEPRECAT a la seva pròpia docstring** (`:14-16`, "0 files a BD").
  - `DocumentTemplate` (`ftt_models.py:38`) — N plantilles del tenant; `fitxer_template` `.fttpt` (`:49`), `metadata_schema` (`:53`), `is_sample` (`:55`), `origen` sistema|tenant (`:41-44`), `actiu` (`:57`).
- **Camí VIU = `DocumentTemplate`**: `GET /api/v1/document-templates/` (`App.jsx:152`, view `ftt_template_views.py:25-38`), `POST …/save-as-template/` (`TechSheetEditor.jsx:3630`), `POST /api/v1/models/<id>/ftt-document/` amb `template_id` (`App.jsx:125`, `ftt_document_views.py:49-79`).
- **Camí DEPRECAT = `TechSheetTemplate`, mort al frontend**: els seus endpoints (`endpoints.js:284-286`) només els consumeix `TechSheetTemplateEditor.jsx:11`, marcat JUBILAT (`:1-4`) i **sense cap `<Route>`** a `App.jsx` → pàgina inabastable.
- Plantilla del sistema: `master_template.py:22`, `seed_master_template()` `:57-80`, `kind=FTT_KIND_TEMPLATE` (`:64`). El seu contingut és **un sol `data_block` header** (`:34-42`) — **cap camp `field`**.
- **NO EXISTEIX cap pantalla de gestió de plantilles** (llistar/editar/esborrar). El CRUD del backend existeix (`ftt_template_views.py:25`) però **sense consumidor d'UI**: l'única referència del frontend a `document-templates` és el chooser (`App.jsx:152`).

### P1.2 · El flux "Desar com a plantilla" i el seu forat

- Modal `saveAsTpl` (`TechSheetEditor.jsx:1761`), obert des de la cinta (`:4071`) i el menú (`:4155`); dos camps (`:5261`, `:5265`).
- Submit (`:3628-3636`): `POST …/save-as-template/` amb **només `{nom, descripcio}`** — el client **no envia el document**; el backend agafa el cap de cadena.
- Backend (`ftt_document_views.py:193-208`): `load_document` (`:200`) → `pack(..., kind=FTT_KIND_TEMPLATE)` (`:201-203`) → `DocumentTemplate(origen='tenant')` (`:204`).
- **FET CRÍTIC:** no s'hi crida `unfreeze_document` enlloc. Els `field` d'un document instanciat ja estan congelats a `text` (`services_ftt_document.py:178-183`), de manera que **desar-lo com a plantilla hi grava els valors del model host** (codi, client, logo, taules) com a text literal.
- **`kind='template'` és escriptura sense lector**: es fixa (`services_ftt.py:83`) i es retorna (`:281`), però **cap branca de codi el llegeix** per canviar comportament. No hi ha distinció funcional plantilla/document al motor.

### P1.3 · La pestanya "Camps"

- Catàleg tancat de 16 claus: `FIELD_CATALOG` (`TechSheetEditor.jsx:130-147`); comentari "únics vàlids" (`:127-129`). **No inclou cap camp de POM/mesura.**
- Tab definit a `:4715` (3r, `id:'fields'`, `ti-forms`); estat `dockTab` a `:1779` (default `'properties'`).
- **Condició de visibilitat EXACTA del contingut: `dockTab === 'fields' && locked`** (`:5060`), dins de `{!importMode && …}` (`:4712`). `locked = lockState === 'owned'` (`:1793`). **El BOTÓ de la pestanya es pinta sempre** (`:4715`): en lectura la pestanya existeix i el panell surt buit.
- **Acció exacta en clicar un camp** (`:5066`): `addObject({type:'field', key:f.key, label:t('tech_sheet.'+f.tk), layer:'free', x:20, y:20, style:{fontSize:11}})`. Sempre a (20,20) mm. **El `label` desat és el text traduït a l'idioma de qui l'insereix**, no la clau.
- Xip: `FieldChipNode` (`:891-899`) sobre `buildFieldChipPrims` (`:529-540`), text `'{' + label + '}'` (`:531`). **El mateix builder s'usa a l'export PDF** (`:1262-1264`) → un PDF amb camps sense resoldre imprimeix literalment `{Nom de la peça}`.
- **NO EXISTEIX panell de propietats per al tipus `field`**: cap branca `selObj.type === 'field'` a `properties`. Un cop inserit **no es pot canviar ni la `key` ni el `label`**; només moure'l/esborrar-lo (`:5049-5055`).

### P1.4 · Com es "resol" en crear document des de plantilla

- Punt d'entrada únic (`ftt_document_views.py:59-72`): amb `template_id` es desempaqueta el `.fttpt` (`:68`) i es crida `resolve_placeholders(document_json, model)` (`:69-71`). Sense `template_id` **no hi ha cap resolució**. Si la plantilla és il·legible, degrada a document buit (`:73-77`).
- `resolve_placeholders` (`services_ftt_document.py:189-199`): **només recorre el primer nivell de `pages[].objects`** (`:195-198`); `_resolve_obj` sí que baixa als `children` (`:184-185`).
- `_resolve_obj` (`:167-186`): `type:'field'` → `type:'text'` amb `text = vals[key]`, conservant geometria, i **afegint la marca `FIELD_MARK='field_key'`** (`:116`, `:182`) que fa **reversible** el congelat.
- Valors: `_placeholder_values` (`:100-108`); `data_avui` = `timezone.localdate()` (`:107`); `customer_logo` es resol a **imatge** (`_resolve_logo_obj`, `:136-164`, caixa fixa 40×16 a `:152`) i degrada a text buit si no n'hi ha (`:158-164`).
- **És un SNAPSHOT, no un binding viu** (docstring `:190-192`).

### P1.5 · Què hi ha avui que s'aproximi a "construint plantilla"

- **`placeholderMode` és l'únic concepte equivalent — i és codi mort al camí viu.** Es propaga per `ObjectNode` (`:1421`) fins a `HeaderBlock` (`:1440`, `:903`) i decideix `{model.codi}`/`{sizes}`/`{date}` vs valors reals (`:607`, `:625`, `:635`, `:724`, `:742-768`, `:812`, `:814-832`, `:1227`).
- **Mai s'activa**: la crida real al canvas (`:4528-4531`) no el passa → sempre `undefined`. Els únics `true` són de la pàgina jubilada (`TechSheetTemplateEditor.jsx:122`, `:266`, `:359`).
- Per tant l'aproximació operativa és **només convenció humana**. **NO EXISTEIX** cap comprovació que una plantilla desada contingui `field` ni que no contingui text congelat.

> **Veredicte P1: cal construir-ho, però el gruix ja hi és.** L'estat existeix com a mecanisme de render (`placeholderMode`) i li falten tres coses: interruptor, gate del tab Camps, i **descongelar en desar** (el forat de P1.2, que és el que avui fa que les plantilles neixin brutes).

💡 **PROPOSTA P1-A (a validar) — l'interruptor.** Un estat `templateMode` al `TechSheetEditor` que (1) es passi com a `placeholderMode` a la crida `ObjectNode` de `:4528-4531` (activa el mecanisme ja construït sense tocar-ne el render), i (2) gati el contingut del tab Camps canviant `:5060` de `dockTab==='fields' && locked` a `dockTab==='fields' && locked && templateMode`. Amb el mateix flag, **ocultar el botó del tab** (`:4715`) quan no s'hi és — resol (b) sencer.

💡 **PROPOSTA P1-B (a validar) — d'on surt el flag.** Tres opcions per decidir: (i) botó/toggle explícit a la cinta del grup "file" (al costat de `save_as_template`, `:4071`); (ii) derivar-lo del document (un camp al `document_json`, aprofitant que `kind='template'` ja viatja al manifest i **avui no el llegeix ningú** — `services_ftt.py:83`); (iii) derivar-lo de la ruta (una ruta d'edició de plantilla, que avui NO EXISTEIX). L'opció (ii) té l'avantatge que el flag sobreviu al desat i al reobrir; la (i) és la més barata.

💡 **PROPOSTA P1-C (a validar) — tapar el forat del desat.** Cridar `unfreeze_document` (`services_ftt_document.py:312`) dins `save-as-template` (`ftt_document_views.py:200`) abans del `pack`. És l'invers exacte i ja retorna `(document_json, assets, report)`; el `report` permetria avisar l'usuari de què s'ha desmaterialitzat. **Sense això, qualsevol millora d'UI del mode plantilla segueix produint plantilles amb dades del model host.**

---

## BLOC P2 — Patró col·lapsable i estat del panell dret

### P2.1 · El patró existent

- **NO EXISTEIX cap component reutilitzable transversal**: cap `Collapsible`/`Accordion`/`Colapsable` a `frontend/src` (0 coincidències). `components/ui/` no en té cap primitiva; `Card` (`components/ui/Card.jsx:1`) renderitza `children` incondicionalment (`:22`).
- **L'únic que encapsula el patró és `Contenidor`** (`TallerPatro.jsx:1310`), **local i no exportat**:
  - Props `{ titol, icona, pes = 1, children }` (`:1310`); estat `plegat` (`:1312`, obert per defecte).
  - Capçalera clicable amb `aria-expanded={!plegat}` (`:1323`); chevron `ti-chevron-down` plegat / `ti-chevron-up` obert (`:1336`) amb i18n `pattern.taller.expand|collapse` (`:1337`).
  - Cos condicional amb `overflowY:'auto'` (`:1340-1343`); plegat no creix (`flex: plegat ? '0 0 auto' : …`, `:1317`).
  - **3 consumidors, tots del mateix fitxer** (`:1100`, `:1109`, `:1124`).
- **12 implementacions ad-hoc** del mateix patró, cap compartida. Les més rellevants: `Sidebar.jsx:207`/`:344` (amb localStorage), `RelationsPanel.jsx:414`, `SessionPanel.jsx:62`, `DashboardTab.jsx:249`, `RegistreActivitatTab.jsx:113`, `TimeTree.jsx:60`, `Models.jsx:272` (botó Filtres·N), `OrderDetail.jsx:148`.
- **Dues convencions de chevron contradictòries**: `down`/`right` (Sidebar, DashboardTab, TimeTree, GarmentTypes, OrderDetail) vs `up`/`down` (RelationsPanel, SessionPanel, RegistreActivitat, Models). `Contenidor` fa `down`(plegat)/`up`(obert) — **l'invers de `SessionPanel.jsx:114`**.
- `aria-expanded` només existeix a **2 llocs**: `RelationsPanel.jsx:421` i `TallerPatro.jsx:1323`.

### P2.2 · Estat actual del panell dret

- És un `<aside>` de **270 px**: obertura `TechSheetEditor.jsx:4637`, tancament `:5077`. Estat `dockTab` (`:1779`) i `importMode` (`:1780`).
- **A) Panell d'IMPORTACIÓ** (`:4639`) — quan `importMode` és actiu **substitueix tot el dock** (la resta va sota `{!importMode && …}`, `:4712`). Els seus títols són `<div>` estàtics (`:4653`). **No col·lapsable.**
- **B) Tira de PESTANYES** (`:4713-4725`) — 3 tabs cablats en línia (`:4715`): `properties` · `layers` · `fields`. Comentari d'extensió per a un futur tab a `:4713`. No són seccions.
- **C) Cos scrollable** (`:4726`), blocs en ordre de render:

| # | Bloc | Condició | Col·lapsable |
|---|---|---|---|
| C1 | Llista de CAPES | `dockTab==='layers'` `:4728` | **NO** |
| C3 | Propietats · sense selecció | `!multiSelected && !selObj` `:4767` | **NO** |
| C4 | Propietats · multiselecció | `multiSelected && locked` `:4779` | **NO** |
| C5 | Propietats · objecte únic | `selObj && locked` `:4812` | **NO** |
| C5.a | Dimensions i posició | `selDim` `:4816` | **NO** |
| C5.b | Tipografia / text | `textObj` `:4848` | **NO** |
| C5.c | Traç i puntes | `shapeObj` `:4912` | **NO** |
| C5.d | Emplenat | `rect\|ellipse\|path` `:4962` | **NO** |
| C5.e | Escala % | `data_block` `:4971` | **NO** |
| C5.f | Edició de taula | `table` + `bom\|custom` `:4977` | **NO** |
| C5.g | Editar nodes / substituir SVG | `sketch_svg\|path` `:5029` | **NO** |
| C5.h | Rotació | `!blocksTransform` `:5043` | **NO** |
| C5.i | Esborrar | `free\|data_block` `:5049` | **NO** |
| C6 | Catàleg de CAMPS | `dockTab==='fields' && locked` `:5060` | **NO** |

- **CAP bloc és col·lapsable**: cap `ti-chevron-down|up|right` dins `4637-5077` (els chevrons del fitxer són de z-order `:4123`, `:4126`, `:4362`, `:4365` i un breadcrumb `:4244`).
- El separador de blocs és `SectionTitle` (`:5309-5311`): un `<div>` daurat **sense cap prop més enllà de `children`**, sense chevron ni `onClick`. `propLabel` és estil pur (`:5312`).
- `SectionTitle`/`propLabel` són **exportats i tenen 1 consumidor extern**: `TechSheetTemplateEditor.jsx:18` (`:387`, `:397`, `:399`, `:404`, `:409`).
- **Persistència: NO EXISTEIX** al panell dret — `dockTab` i `importMode` són `useState` en memòria. L'**únic** col·lapse persistit de tot el frontend és el Sidebar (clau `sidebarGroups`, `Sidebar.jsx:207-214`, `:296`; semàntica "clau absent = obert" a `:210`). Hi ha fins i tot una llei explícita en contra en un altre cas (`AssetNavigator.jsx:90`: "Mai localStorage — és context de sessió, no preferència d'usuari").

> **Veredicte P2: no hi ha res a reutilitzar tal qual; hi ha un candidat a promoure.** `Contenidor` és l'únic amb forma de component, però està tancat dins `TallerPatro.jsx` i el seu `flex`/`pes` està pensat per a una columna d'alçada repartida, no per a un panell scrollable.

💡 **PROPOSTA P2-A (a validar) — promoure, no clonar.** Extreure `Contenidor` (`TallerPatro.jsx:1310`) a `frontend/src/components/ui/` com a component compartit, afegint-hi `defaultOpen` i fent opcional el `pes` (el panell dret és scrollable, no de flex repartit). Migrar-hi després el panell dret i, si es vol, les 12 còpies. **Fixar una sola convenció de chevron** en fer-ho (avui n'hi ha dues) i mantenir `aria-expanded`.

💡 **PROPOSTA P2-B (a validar) — quins blocs mereixen col·lapse.** Els candidats naturals són els sub-blocs de C5 (Dimensions, Tipografia, Traç, Emplenat, Rotació): són els que fan scroll llarg quan hi ha un objecte seleccionat. C1/C6 són continguts de pestanya sencera, no seccions. Requereix convertir `SectionTitle` (`:5309`) en capçalera clicable **o** embolcallar-lo — decisió d'Agus, perquè `SectionTitle` és compartit amb `TechSheetTemplateEditor.jsx:18`.

💡 **PROPOSTA P2-C (a validar) — persistència.** Si es vol recordar l'estat obert/tancat, l'únic precedent del repo és `sidebarGroups` amb la semàntica "clau absent = obert" (`Sidebar.jsx:210`). Si es considera context de sessió i no preferència, seguir `AssetNavigator.jsx:90` i **no** persistir. Cal decisió explícita: el repo té les dues lleis escrites.

---

## BLOC P3 — Contenidor de POMs i eina de cota

### P3.1 · D'on surten els POMs (endpoint i shape)

- **Endpoint ric** (taller de patró): action `model-poms` a `patterns/views.py:444-552`; crida `endpoints.js:686`. Consumidors: **només** `TallerPatro.jsx:150` i `:447`.
  - Shape per fila (`views.py:493-527`) inclou `codi_client`, `nom_fitxa`, `nom_client`, `nom_canonic`, `codi_global`, **`nom` (dict per idioma)**, `descripcio` (dict), `fitxa_pom` (dict), `alias_client`, toleràncies, `is_key`, `ancorat`…
  - Nomenclatura per idioma: `_noms_del_global()` (`views.py:70-74`) → `{'en','ca','es'}`. Descripcions **només `en`/`ca`**: `POMGlobal` **NO té `descripcio_es`** (dit literalment a `:80-82`).
- **Endpoint que l'editor ja fa servir**: `GET /api/v1/models/{id}/base-measurements/` (`wizard_views.py:301-335`, ruta `models_app/urls.py:105`). Retorna `nom_client`, `nom_ca`, `nom_fitxa`, `pom_code_global`, `pom_abbreviation`, `pom_is_key`… **però NO retorna `nom_en`** (`:322`).
- **Serializer alternatiu que SÍ dona EN**: `/api/v1/base-measurements/` (`models_app/serializers.py:227-250`) amb `pom_code`, `pom_name_en`, `pom_name_cat`, `pom_abbreviation`, `pom_category`, `nom_fitxa`… (router `urls.py:45`).
- **Conseqüència ja visible al codi**: a `TechSheetEditor.jsx:3413` el nom EN de la taula T1a s'obté de la **GradingRule** (`rule?.pom_nom_en`) amb caiguda a `bm.nom_client || bm.pom_code_global` — **precisament perquè l'endpoint que fa servir no porta EN**.

### P3.2 · El patró de presentació canònic (ja existeix)

- **`PomNamePair`** — component exportat a `POMBrowser.jsx:530-541`, amb la llei del sector escrita al comentari `:528`: *"nom anglès primari (negre), nom localitzat al costat en cursiva gris. Si no hi ha EN → mostra el que hi hagi. Si EN i local coincideixen → només un."*
  ```
  primary   = en || local
  secondary = en && local && local !== en ? local : ''
  ```
- **Ordre complet de la fila** (`POMBrowser.jsx:429-436`): **codi** (gold, 600, `minWidth:64`) → `PomNamePair(en, local)` → pill `abbreviation` (mono) → pills W/K/S. Consumidors: `POMBrowser.jsx:431`, `POMCatalogue.jsx:153`.
- **Fitting/mesures**, mateixa llei (`MeasureGrid.jsx:119-123`): línia 1 = `nomEn || nomLocal`; línia 2 = **`nom_fitxa` amb precedència sobre el nom local** (`:140`, `:158`). La columna curta és `CodiCell` → `nom_fitxa || pom_code` (`:164-166`).
- **Taller** (`ModelPomList.jsx:92`): `f.nom?.en || f.nom_client || f.nom_canonic`; render `codi_client` → nom canònic → **badge amb `nom_fitxa`**, comentat com *"la nomenclatura de la fletxa al croquis"* (`:141-151`).

### P3.3 · L'eina de cota actual (`cota_pom`)

- Eina **viva** (sense `soon`): botó de cinta a `TechSheetEditor.jsx:3882` (`ti-ruler-measure`, categoria `annot`); i18n als 3 idiomes (`i18n/{ca,en,es}.json:2482`).
- **Gest de 2 clics**: estat `twoClickRef` (`:1848-1849`); 1r clic fixa `p1` (`:2892-2895`), 2n clic aplica `snap45` amb Shift (`:2899-2900`), crida `finishTwoClick` i torna a `select` (`:2901-2904`). Preview elàstic discontinu (`:4575-4578`); Escape cancel·la (`:2638`).
- **Objecte creat** (`finishTwoClick`, cas `cota_pom`, `:2872-2882`): un **grup** amb dos fills —
  - `arrow` amb `stroke/fill = KONVA_COL.textMain`, `strokeWidth:1`, `arrow2:true` (`:2878`);
  - `text` al punt mig desplaçat 3 mm perpendicular (`:2880`), `fontSize:9`, `align:'center'` (`:2881`).
- **D'on surt el TEXT avui**: d'una **clau i18n literal**, `t('tech_sheet.preset_cota_text')` = **`"A · 00"`** als tres idiomes (`i18n/{ca,en,es}.json:2512`). **No prové de cap dada de domini.**
- Preset bessó **inert**: `preset_cota_pom` (`:2024-2035`) segueix a `PRESET_TOOLS` (`:122`) però ja no és a cap flyout (`:3884-3888`) — deute anotat a `ops/sprints-editor/SPRINT_EDITOR_ESTAT.md:260`, `:298`.
- **Comentari explícit al codi** (`:2025`): *"Cota tècnica lliure (**sense binding POM, frontera G1 fora d'abast**)"*.

### P3.4 · Tokens de color

- `KONVA_COL` de l'editor (`TechSheetEditor.jsx:90`): `white, gold, goldPale, border, textMain, textMuted, labelGray`. → **NO EXISTEIX cap token vermell.**
- `KONVA_COL` del visor de patrons (fitxer diferent, **no importat** per l'editor, `PatternViewer.jsx:29-51`): `notch:'#a32d2d'` (`:37`), `pom:'#bf3989'` (`:43`, magenta).
- **Vermell saturat ja present a l'editor però fora de `KONVA_COL`**: `TBL.REF: '#dc2626'` (`:394`) — color de la columna de nomenclatura de les taules snapshot. És l'únic vermell saturat del fitxer.
- Design system (`index.css`): `--err:#a32d2d` (`:32`), `--err-bg:#fcebeb` (`:33`), `--grana:#8a1f3d` (`:14`), `--white:#ffffff` (`:25`). **No hi ha `--danger`/`--red`/`--alert`.**
- **Capacitats de render ja existents**: `fontStyle:'bold'` (`:937`, `:947`, `:2049`) i fons de text via `bgFill`/`bgPadding` (`:934`, `:1177`, `:1472`), **editable des del panell dret** (`:4897`, `:4903`).

### P3.5 · FRONTERA G1 — vincle viu

- **NO EXISTEIX vincle viu cota↔POM/mesura.** Proves:
  - L'objecte de cota (`:2872-2882`) només té `type/layer/x/y/rotation/children`; **cap camp `pom`, `pom_id`, `base_measurement`, `bm_id` ni `size_fitting_id`**.
  - `grep "pom"` sobre tot `TechSheetEditor.jsx` (excloent `cota_pom`) dona **només** línies de taules (`:3398`–`:3465`).
  - El text surt d'una clau i18n (`:2881`), no d'una dada.
- **La llei contrària ja és escrita al codi** (`:3368-3369`): *"taules snapshot (T1a/T1b) — valors CONGELATS a la inserció (llei de disseny: cap binding viu; `obj.snapshot` només serveix per traçabilitat)"*; `obj.snapshot = {model_id, size_fitting_id, snapshot_at}` (`:3424`, `:3467`, `:3488`, `:3505`).
- **Matís obligat (única excepció, i és LEGACY i d'un altre tipus d'objecte):** el `data_block` `kind:'graded_table'` desa `size_fitting_id` (`:3357`) i **es re-fetcha en carregar** (`:2399-2415`). Està marcat *"LEGACY: substituït pel picker de taules snapshot S3 … candidat a poda futura"* (`:3340-3341`, `:3366-3367`). És un vincle a una **SizeFitting sencera, mai a un POM individual**.
- Segon mecanisme de resolució viva, també fora d'abast: el header resol camps **del model** en render (`:804-805`, `:573-646`) — no toca mesures ni POMs.

> **Veredicte P3: G1 CONFIRMADA, sense contradiccions.** Res del disseny actual s'oposa que la cota neixi amb text resolt i estàtic; **és el patró vigent i explícitament preferit** (`:3368-3369`). Els dos precedents de resolució viva són d'altres tipus d'objecte i un està retirat.

💡 **PROPOSTA P3-A (a validar) — d'on llegeix el contenidor.** L'endpoint que l'editor ja usa (`base-measurements`, `wizard_views.py:301`) **no serveix** perquè no porta `nom_en` (`:322`), i el codi ja pateix aquesta manca (`TechSheetEditor.jsx:3413`). Dues sortides: (i) **afegir `nom_en`** a `wizard_views.py:317-331` (canvi mínim, un camp); (ii) consumir `/api/v1/base-measurements/` (`serializers.py:227-250`), que ja el dona. La (i) és la barata i no obre un segon consumidor.

💡 **PROPOSTA P3-B (a validar) — presentació.** No inventar format: reutilitzar **`PomNamePair`** (`POMBrowser.jsx:530`), que ja és exportat, i l'ordre canònic `codi → PomNamePair → nom_fitxa`. Ull a la llei de `MeasureGrid.jsx:119-123`: a la superfície de mesures **`nom_fitxa` té precedència sobre el nom local** — cal decidir quina de les dues variants és la bona per al contenidor de l'editor.

💡 **PROPOSTA P3-C (a validar) — què és el "text resolt" de la cota.** El candidat fort és **`nom_fitxa`**, perquè el codi ja el descriu com *"la nomenclatura de la fletxa al croquis"* (`ModelPomList.jsx:141-142`) — que és exactament aquest cas d'ús. Alternatives: `codi_client`, o `codi · nom_en`. **Decisió d'Agus**; sigui quina sigui, G1 exigeix que es copiï com a **string literal** al `text` del fill (`:2881`), sense cap id.

💡 **PROPOSTA P3-D (a validar) — estil vermell.** Cal **afegir tokens nous a `KONVA_COL`** (`TechSheetEditor.jsx:90`), perquè el canvas Konva no resol `var()` (llei del `CLAUDE.md`; comentari `PatternViewer.jsx:27-28`). Valor precedent al mateix fitxer: `#dc2626` (`:394`); alternativa de marca: `--err #a32d2d` (`index.css:32`). El render **no necessita codi nou**: `fontStyle:'bold'` i `bgFill`/`bgPadding` ja existeixen (`:934`, `:937`) i ja són editables des del panell dret (`:4897`).

💡 **PROPOSTA P3-E (a validar) — el gest.** L'eina viu ja en 2 clics (`:2890-2906`) i acaba a `finishTwoClick` (`:2872`). Pre-carregar text+estil és passar-li el POM seleccionat al contenidor: **no cal tocar la màquina d'estats**, només l'objecte que es construeix a `:2878-2882`. Si es vol arrossegar en comptes de clicar, això **sí** és mecanisme nou (no hi ha drag-and-drop cap al canvas al fitxer).

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT

| # | Peça | Estat | Ancoratge | Risc |
|---|---|---|---|---|
| 1 | Mode plantilla com a estat formal | **FALTA** | `App.jsx:255` (sempre model host) | — |
| 2 | Mecanisme de render de placeholders | **EXISTEIX, mort** | `TechSheetEditor.jsx:4528-4531` no passa `placeholderMode` | Baix: només cal cablar-lo |
| 3 | `save-as-template` descongela | **FALTA** | `ftt_document_views.py:200-203`; invers a `services_ftt_document.py:312` | **ALT** — les plantilles neixen amb dades del model host com a text literal |
| 4 | Gestió de plantilles (UI) | **FALTA** | CRUD a `ftt_template_views.py:25` sense consumidor | Mitjà: no es poden esborrar/desactivar |
| 5 | `kind='template'` amb lector | **FALTA** | `services_ftt.py:83` escriu, ningú llegeix | Baix, però és el lloc natural del flag |
| 6 | Editar `key`/`label` d'un `field` | **FALTA** | cap branca `type==='field'` a properties | Mitjà: xip inserit = irreversible sense esborrar |
| 7 | `label` del camp desat traduït | **DIFERENT** | `TechSheetEditor.jsx:5066` desa `t(...)`, no la clau | Mitjà: plantilla feta en ca mostra etiquetes ca a un usuari en |
| 8 | Component col·lapsable compartit | **FALTA** | únic candidat `TallerPatro.jsx:1310` (local) | Baix |
| 9 | Convenció única de chevron | **DIFERENT** | `down/right` vs `up/down`; 12 còpies | Baix, però es propaga si no es fixa ara |
| 10 | Col·lapse al panell dret | **FALTA** | cap chevron a `4637-5077` | — |
| 11 | Persistència d'obert/tancat | **FALTA** | únic precedent `Sidebar.jsx:207-214` | Baix — hi ha dues lleis contradictòries al repo (`AssetNavigator.jsx:90`) |
| 12 | Contenidor de POMs a l'editor | **FALTA** | cap estat de POMs a `TechSheetEditor.jsx` | — |
| 13 | Patró de presentació de POM | **EXISTEIX** | `PomNamePair` `POMBrowser.jsx:530` | Cap: reutilitzable |
| 14 | `nom_en` a l'endpoint de l'editor | **FALTA** | `wizard_views.py:322` | Mitjà: sense EN no hi ha parell canònic |
| 15 | `descripcio_es` a `POMGlobal` | **FALTA** | `patterns/views.py:80-82` | Baix (només si es mostra descripció) |
| 16 | Eina de cota 2 clics | **EXISTEIX** | `TechSheetEditor.jsx:2872-2906` | Cap |
| 17 | Text de la cota des d'un POM | **FALTA** | avui i18n literal `"A · 00"` (`i18n:2512`) | — |
| 18 | Token vermell a `KONVA_COL` | **FALTA** | `TechSheetEditor.jsx:90` | Baix: precedent `#dc2626` a `:394` |
| 19 | Render bold + fons de text | **EXISTEIX** | `:934`, `:937`, `:4897` | Cap |
| 20 | Vincle viu cota↔POM (G1) | **NO EXISTEIX** ✅ | `:2872-2882`; llei a `:3368-3369` | Cap — G1 confirmada |
| 21 | Camp de plantilla per a POM | **FALTA** | `FIELD_CATALOG:130-147` tancat, sense POMs | Obert: una cota en plantilla avui no té representació |
| 22 | Edició de text de fill de grup | **DIFERENT** | deute a `SPRINT_EDITOR_ESTAT.md:260`; ruta parcial `:3674`, `:4850` | Mitjà: la cota és un grup |

---

### Obert / pendent de verificar

- Nombre real de files de `DocumentTemplate` per tenant a staging (requeriria consulta a BD; **no feta**, lectura pura de codi).
- Si `nom_es` de `POMGlobal` està poblat a BD (**no verificat**, només codi).
- Camí complet grup→export PDF per a un grup de cota (`:847-858` és la via de primitives; **no confirmat** d'extrem a extrem).
- Declaració de l'estat `expanded` de `Planning.jsx:399` i cos de `blocksTransform` (`:5043`) — no traçats.
