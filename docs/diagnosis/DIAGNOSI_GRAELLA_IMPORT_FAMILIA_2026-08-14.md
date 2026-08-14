# DIAGNOSI — LA GRAELLA D'IMPORT I LA SEVA FAMÍLIA

**Data:** 2026-08-14 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
**Abast:** tot el que a la casa és «wizard/graella d'import» amb files que apunten a un POM —
el del MODEL (fitxa de mesures) i tots els parents que el cens ha destapat—, per decidir amb
cost real la peça de graella (clau de fila = `ordre`) demanada per l'Agus el 14/08.

> Convenció: cada afirmació porta `fitxer:línia`. **«NO EXISTEIX» = confirmat absent al codi**,
> mai especulat. Les propostes van marcades `💡 PROPOSTA (a validar)` i separades dels fets.
> Els números de línia del backend són els del `dev` amb l'Onada 3 backend ja aplicada (avui).

---

## 1 · RESUM EXECUTIU

1. **El wizard d'importació de mesures és ÚNIC a la casa.** `poms_extrets` —la taula de files
   del document— només la llegeix `models_app/extraction_views.py` (i els seus bancs); cap
   altra app hi toca. Al front, `ImportWizard.jsx` s'instancia **una sola vegada**
   (`components/model/MeasuresEntryPanel.jsx:564`) i no comparteix ni graella ni parser amb
   ningú: només importa `ui/Modal` i `ui/FileDropCard` (`ImportWizard.jsx:1-5`). **La peça de
   graella, doncs, NO en trenca cap altra.**
2. **Però la FAMÍLIA existeix i té 5 parents**, i cap d'ells comparteix codi amb el del model:
   són **còpies dialectals** de la mateixa idea («una fila del document → un POM»), cadascuna
   amb la seva llei. La més important: `_apply_many_to_one_guard` viu **DUES vegades**
   (`extraction_views.py:1247` i `pom/size_map_views.py:54`), amb semàntiques diferents.
3. **La fórmula d'identitat de fila JA ESTÀ RESOLTA en una altra graella de la casa**:
   `components/cataleg/TaulaPOMsCataleg.jsx:66` fa `clau = pom_id|capa|instancia`, amb duplicat
   de germana, píndoles d'instància i tecles L/I/N, i el vocabulari viu compartit a
   `utils/capaInstancia.js` (8 superfícies l'importen). **La peça de graella no ha d'inventar
   res: ha de COPIAR-HO** — i això és el que en baixa el cost.
4. **La graella del wizard indexa per `pom_master_id` en 12 punts** (no 7), i un d'ells és el
   pitjor possible: `key={p.pom_master_id}` (`ImportWizard.jsx:1310`). Amb dues files del
   mateix POM, React rep **claus duplicades** i la reconciliació pot barrejar cel·les i perdre
   el teclejat. Avui és inabastable per la UI (el pas 2 no ofereix instàncies), però la porta
   ja és oberta per API des de l'Onada 3.
5. **La cadena de mesures del backend ja parla per identitat sencera** (feta avui, guard de la
   Brumà verd), però **el dany a la pantalla NO està tancat**: mentre la graella col·lapsi per
   POM, la fitxa BRUMA/RUFFLES seguirà escrivint el mateix valor a les tres files. El backend
   és condició necessària i no suficient; el que tanca el forat és la peça 3.
6. **Dos forats de la mateixa família, censats i FORA d'aquesta peça** (acta a §6): el flag
   `actiu` del pas 2 és per POM i no per fila (`extraction_views.py:2086`), i
   `MeasurementBaseGrid.jsx:67` col·lapsa els valors de l'item per POM (`valByPom[v.pom]`).

---

## 2 · BLOC A — CENS DE PARENTS (la família sencera)

Criteri del cens: tota superfície que **llegeix un document/taula externa i n'ha de decidir,
fila a fila, a quin POM apunta**. Cerca: `request.FILES` a tot el backend, `import-sessions` i
`pom_master_id`/`pom_id` a tot el front, i tots els consumidors de `poms_extrets`.

| # | Parent | Front | Backend | Comparteix amb el del model? |
|---|--------|-------|---------|------------------------------|
| 1 | **MODEL · fitxa de mesures** | `components/ImportWizard/ImportWizard.jsx` (únic instanciat, `model/MeasuresEntryPanel.jsx:564`) | `models_app/extraction_views.py` | — (és l'original) |
| 2 | **RULESET · «Nou run de client»** | `pages/SizeMapSetup.jsx` (`Wizard`, també muntat en modal per `components/SizeAuthoringDrawer.jsx:8`) | `pom/size_map_views.py` | **NO · còpia dialectal** |
| 3 | **DICCIONARI del client** | `components/DictionaryWizard.jsx` | `pom/dictionary_views.py:52-90` | **NO · còpia dialectal** |
| 4 | **COL·LECCIÓ de models** | `pages/BulkImportWizard.jsx` + `components/BulkImportReconciliation.jsx` | `models_app/bulk_import_views.py` | **NO · i no és de la família** (les seves files són MODELS, no POMs: `bulk_import_service.py` només menciona «pom» 2 cops) |
| 5 | **ONBOARDING del tenant** | (setup) | `pom/s9_views.py:87` `setup_tenant_from_excel_view` | **NO · sembra de tenant**, no decisió per fila |

**GTI:** el cens **NO troba cap wizard d'import per a l'item**. El patrimoni del GTI s'edita amb
graelles CRUD, no amb un document: `components/BaseSetPanel/BaseSetPanel.jsx` (que munta
`MeasurementBaseGrid.jsx:5`) i `components/cataleg/TaulaPOMsCataleg.jsx`. Són família pel que
fa a la **identitat de fila**, no pel camí d'entrada — i per això entren al BLOC C i no aquí.

### Fets del parent 2 (RULESET) — el més proper i el més perillós
- Té **parser propi** d'Excel/CSV enganxat (capçalera POM | talles) i el seu propi wizard de
  5 pantalles: `pages/SizeMapSetup.jsx` (1.018 línies, `Wizard` exportat).
- Té **matcher propi per fila** amb picker manual: `SizeMapSetup.jsx:814-821` (`<select>` per
  fila que fixa `pom_id`), sobre `wiz.gradingResults` — **un array indexat per POSICIÓ**, no per
  `ordre` ni per POM (`SizeMapSetup.jsx:818` muta per índex `j === i`).
- Té **detector de col·lisió propi**: `SizeMapSetup.jsx:365-370` (`dupPomIds`) i, al backend,
  `_apply_many_to_one_guard` (`pom/size_map_views.py:54-74`), invocat a `:362` i `:604`.
- **Divergència de semàntica amb el del model, i és deliberada:** el del ruleset **anul·la** el
  vincle (`size_map_views.py:72` `r['pom_id'] = None`) perquè «`GradingRule` és únic per
  (rule_set, pom)» (`:57`); el del model fa el mateix a l'extracció (`extraction_views.py:1287`)
  però al pas 2 la col·lisió surt com a **409 `pom_ja_usat`** (`extraction_views.py:1898`), que
  és el que l'Onada 3 ha fet PRECÍS (ara compara identitat sencera, no POM pelat).

**Veredicte A:** la família té 5 parents, cap comparteix codi amb el del model, i només el
parent 2 té la mateixa forma (document → files → POM). El canvi de clau del model **no
n'arregla cap altre i no en trenca cap altre**.

---

## 3 · BLOC B — QUÈ IMPORTA CADA PARENT I QUINA IDENTITAT DE FILA NECESSITA

| Parent | Què importa | Identitat de fila que necessita | Estat |
|---|---|---|---|
| MODEL | **mesures** per talla | `(pom, capa, instancia)` + `garment` de la sessió | **backend fet avui** · graella pendent |
| RULESET | **regles** de graduació | `pom` i prou — `GradingRule` és únic per `(rule_set, pom)` (`size_map_views.py:57`) i el contenidor del client **no té eix de capa ni d'instància** | **correcte com està** |
| DICCIONARI | **àlies** codi-client → POM | la **fila del document** (`row_num`), ja implementada: `DictionaryWizard.jsx:199` `key={r.row_num}` | **ja resolt** |
| COL·LECCIÓ | **models** | codi de model | fora de família |
| ONBOARDING | catàleg sencer | — | fora de família |

**El fet que ho decideix tot:** la identitat d'una mesura a la casa són quatre eixos
(`models_app/models.py`, `unique_together = ('model','pom','capa','instancia','garment')`), i la
d'una REGLA no: el catàleg del client gradua per POM. Per això la peça de graella **és del
parent MODEL i de ningú més**, i per això el confirm, quan un POM es reparteix en germanes,
deriva la regla d'UNA sola i ho diu en un avís (`extraction_views.py:1895` `_valors_per_pom`).

**Veredicte B:** cap altre parent necessita capa/instància. Igualar-los seria fabricar
estructura que el seu domini no demana.

---

## 4 · BLOC C — ELS PUNTS COMPARTITS (i el que ja està resolt en una altra graella)

### C.1 · El que NO es comparteix (i per tant no cau amb la peça)
- `buildTaula` **NO EXISTEIX** fora d'`ImportWizard.jsx:608`. Cap altre fitxer del repo la
  menciona.
- La graella del pas 3 està **escrita en línia** dins `ImportWizard.jsx:1299-1341`: no és un
  component, no té props, no la reutilitza ningú.
- El detector de col·lisió del model (`_pla_de_resolucions`, `extraction_views.py:1866+`) només
  el crida `import_session_poms_view` (`:2018`).

### C.2 · El que SÍ que es comparteix — i que la peça ha de REUTILITZAR, no re-escriure
- **`utils/capaInstancia.js`** és la porta única de traducció dels dos eixos, i la importen 8
  superfícies (`EditableTable.jsx:13`, `model/MeasureGrid.jsx:6`, `cataleg/TaulaPOMsCataleg.jsx:8`,
  `grading/GraduacioSuperficie.jsx:5`, `model/ComprovacioPanel.jsx:5`, `pages/FittingDetail.jsx:14`,
  `pages/FittingPrintSheet.jsx:7`, `pages/TechSheetEditor.jsx:36`). **L'ImportWizard NO l'importa
  encara** — és l'única superfície de mesures que no sap escriure «Folre»/«Left».
- **L'ESTRUCTURA dels eixos no es duplica al client**: la publica el backend
  (`GET /api/v1/mesures/diccionari/`) i el front la llegeix per `utils/diccionariMesuresFont.js`
  (capçalera de `utils/capaInstancia.js`). Qualsevol selector d'instància nou ha de sortir
  d'aquí, mai d'una llista escrita a l'ImportWizard.
- **La fórmula d'identitat de fila ja existeix i funciona**: `cataleg/TaulaPOMsCataleg.jsx:66`
  `const clau = (r) => \`${r.pom_id}|${r.capa||'exterior'}|${r.instancia||''}\``, amb duplicació
  de germana de capa (`:136-148`, que busca la següent capa **LLIURE** perquè la clau única és
  `(item, pom, capa, instancia)`) i navegació L/I/N (`:203`).

**Veredicte C:** la peça de graella toca UN sol camí (el del model) i té model a seguir dins
de casa. El risc no és el radi: és la reconciliació de React dins del propi fitxer (§5.4).

---

## 5 · BLOC D — LA GRAELLA DEL MODEL PER DINS

### 5.1 · `buildTaula`: d'on neix, què transforma, on desemboca
- **Neix** a `ImportWizard.jsx:608-618`. Font: `pomsExtrets` filtrat per `actiu`
  (`src || pomsExtrets`).
- **Transforma**: per cada fila i cada talla de `tallesSel` (les **etiquetes del DOCUMENT**, no
  les del model) llegeix `p.values[talla]` i el converteix a `String` (`''` si absent).
- **Desemboca** a `setTaula(t)` amb `t[p.pom_master_id] = row` — **aquí és on tres files del
  mateix POM es fonen en una**.
- **Se la crida UNA sola vegada**: `:583`, just després que el pas 2 desi (i amb la resposta del
  backend, no amb l'estat local). Efecte lateral conegut i preexistent: **tornar al pas 2 i
  tornar a desar RECONSTRUEIX la taula i perd tot el que s'hagi teclejat al pas 3.**
- `setTaula` només té 3 escriptors: `:618` (buildTaula), `:622` (`setCell`) i `:645` (l'ompliment
  del grading).

### 5.2 · Els punts d'indexació per `pom_master_id` — **12, no 7**

| # | Línia | Qui | Rol |
|---|-------|-----|-----|
| 1 | `:265` | `useState({})` — `{pom_master_id: {talla: valor}}` | **el contenidor** |
| 2 | `:616` | `buildTaula` `t[p.pom_master_id] = row` | **construcció** |
| 3 | `:622` | `setCell(pid, talla, val)` | **escriptura** (la de cada tecla) |
| 4 | `:626` | `emptyCols` | lectura (columnes buides → ofereix grading) |
| 5 | `:627` | `baseTeValors` | lectura (habilita el botó de grading) |
| 6 | `:633-634` | `handleGenerarGrading` → `base_values[p.pom_master_id]` | **payload sortint** |
| 7 | `:648-654` | ompliment del grading (`grading[String(pom_master_id)]` → `next[pid]`) | **lectura + escriptura** |
| 8 | `:667-669` | `handleContinueMesures` | **desat A** |
| 9 | `:693-695` | `goCrearLibrary` | **desat B** |
| 10 | `:764` | `nValors` (resum del pas 5) | lectura |
| 11 | `:1310` | `key={p.pom_master_id}` | **clau de React** ⚠️ |
| 12 | `:1327-1328` | `value=` + `onChange` de la cel·la | lectura + escriptura |

A més, **fora de la graella** i de la mateixa família: `:519` (`addPomManual` refusa afegir un
POM que ja hi sigui — la llei «un POM una fila» escrita al front) i `:536` (`poms_confirmats` és
una llista d'IDs de POM, no d'`ordre`).

### 5.3 · ELS DOS CAMINS DE DESAT — i emeten EXACTAMENT el mateix

| | Camí A · continuar | Camí B · Size Library |
|---|---|---|
| Funció | `handleContinueMesures` `:661-682` | `goCrearLibrary` `:686-712` |
| Bucle | `for p of pomsTaula { for talla of tallesSel }` | **idèntic, línia a línia** |
| Filtre | `v !== undefined && v !== ''` | idèntic |
| Payload | `{pom_master_id, talla_label, valor: parseFloat(v)}` | idèntic |
| Endpoint | `PATCH .../mesures/` amb `{mesures, valors_mode}` | **el mateix PATCH**, i tot seguit `POST .../library-prefill/` |
| Després | `loadIso()` + `setStep(4)` | `navigate('/size-library?prefill=…')` |

**Tots dos acaben al mateix punt del backend** (`import_session_mesures_view:2285`), o sigui que
els dos passen per la porta que avui ja sap heretar els eixos. El camí B, a més, llegeix
`import_session_library_prefill_view:2351`, que **col·lapsa per POM a posta**: el prefill de la
Library viatja per `pom_codi` i la Library no té eix de capa ni d'instància.

### 5.4 · Estat local i re-render — **on viu el risc de regressió**
- `taula` és **UN sol objecte** per a tota la graella i `setCell` (`:620-622`) en crea un de nou
  a cada tecla → **tota la taula es re-renderitza a cada pulsació**. Ja és així avui.
- Les cel·les són **inputs controlats** (`value={taula[pid]?.[talla] ?? ''}`, `:1327`).
- ⚠️ **El dany més visible possible és exactament el que l'Agus va anticipar**: canviar la clau
  de fila canvia `key={}` (`:1310`). Si la clau nova no és **estable entre renders**, React
  desmunta i remunta els `<input>`, i el que s'estigui teclejant es perd (a més del focus).
  `ordre` **és** estable: el fixa el backend a l'extracció (`extraction_views.py:1342`), el
  conserva el pas 2 i els POMs afegits a mà en reben un (`extraction_views.py:2176` i
  `ImportWizard.jsx:523`). **Cap fila viva del pipeline es queda sense `ordre`.**
- Avui, amb dues files del mateix POM, `key={p.pom_master_id}` seria **duplicada** — React ho
  avisa per consola i la reconciliació és indefinida. És el guany net del canvi, no un cost.

### 5.5 · CONTRACTE LITERAL DEL PAYLOAD DE MESURES (per al guard de no-regressió)

```
PATCH /api/v1/import-sessions/<token>/mesures/
{
  "mesures": [ { "pom_master_id": 123, "talla_label": "M", "valor": 100.5 }, … ],
  "valors_mode": "absoluts" | "deltes"
}
→ 200 { "ok": true, "estat": "MESURES_OK", "n_valors": <int> }
```
- `talla_label` és **l'etiqueta del DOCUMENT** (`tallesSel`), no la del model: el confirm la
  tradueix amb `run_conciliat['talla_mapping']` (`extraction_views.py:2557-2563`).
- Les cel·les buides **no s'envien** (mai `null`).
- `valor` és `parseFloat` al client i `normalitza_cm` al servidor (la porta del camí enganxat).
- **L'import d'un-POM-per-fila ha d'emetre EXACTAMENT això després de la peça.** El banc que ho
  fixa ja existeix i és verd: `test_import_cadena_mesures_bruma.py::CadenaNoRegressioTest`
  (3 casos, inclòs el de la sessió a mig fer amb el front vell).

---

## 6 · BLOC E — QUÈ QUEDA OBERT AL BACKEND DESPRÉS DE L'ONADA 3 (censat, amb acta)

1. **🚩 El flag `actiu` del pas 2 és PER POM, no per fila** (`extraction_views.py:2086`:
   `p['actiu'] = p['pom_master_id'] in confirmats_set`, sobre `poms_confirmats`, que és una
   llista d'IDs — `ImportWizard.jsx:536`). Amb tres germanes, desmarcar-ne una les desmarca
   **totes tres**. No és regressió (avui la UI no pot crear germanes), però **entra a la peça 3**:
   el contracte del pas 2 ha de passar a parlar d'`ordre`.
2. **🚩 La poda i el pre-flight de MANUAL segueixen sent PER POM.** `orfes` exclou per
   `pom_id__in=confirmed_pom_ids` (`extraction_views.py:2712`) i les respostes 409
   (`poms_no_mencionats`, `manual_trepitjat`) porten `pom_id` sense capa/instància
   (`:2718-2726`, `:2762-2770`) → amb germanes vives, la UI en pintaria dues d'iguals. Acotar
   la poda a la identitat és **decisió de producte** (voldrà l'Agus que un import que només
   parla de la instància `bottom` proposi podar l'exterior?), i per això queda **FORA** fins que
   ell ho decideixi. Datat 14/08.
3. **`ModelGradingOverride` s'escriu sempre a la identitat canònica** (`extraction_views.py:3160`,
   `capa=SLUG_DEFECTE, instancia=''`), coherent amb el fet que el catàleg gradua per POM (§3).
   Ho diu ara un avís del confirm quan un POM es reparteix (`_valors_per_pom`, `:1895`).
4. **`MeasurementBaseGrid.jsx:67` — `valByPom[v.pom] = v`**: la graella de l'ITEM col·lapsa els
   `ItemBaseMeasurement` per POM tot i que la clau del món de l'item és
   `(garment_type_item, pom, capa, instancia)` (`tasks/management/commands/bootstrap_tenant.py:167`).
   És **el mateix forat, una superfície més enllà**, i NO és d'aquesta peça. Censat 14/08.

---

## 7 · PLA DE LA PEÇA DE GRAELLA — cost real

> `💡 PROPOSTA (a validar)` — la decisió és de l'Agus (Patró C). Cost en talls de commit; tot
> el que segueix és **frontend + contracte de pas 2**, perquè el backend ja hi és.

**P1 · La graella parla per fila (mecànic, sense UI nova).** Els 12 punts de §5.2 passen
d'`p.pom_master_id` a `p.ordre`; `key={p.ordre}`; `base_values` passa a la forma llista
`[{ordre, valor}]` i l'ompliment llegeix `data.clau === 'ordre'`; els dos camins de desat
afegeixen `ordre` a cada mesura. **Cost: 1 tall, ~40 línies tocades d'un sol fitxer.**
Guard: cap banc de front (no hi ha vitest; només `node --test`, memòria S37) → el guard és el
backend ja verd + QA a la pantalla amb la fitxa de la Brumà.

**P2 · El pas 2 guanya el columnat d'identitat.** Selector d'instància (i capa) per fila,
alimentat per `GET /api/v1/mesures/diccionari/` via `utils/diccionariMesuresFont.js`, escrit per
`posaResolucio` (`ImportWizard.jsx:493`, cridada des del panell a `:1196-1204`) → viatja com a `capa`/`instancia` de la resolució,
que el backend ja sap llegir (`_pla_de_resolucions`). Cal **retirar la llei «un POM una fila»
del front** (`:519`) i canviar `poms_confirmats` d'IDs a `ordre` (§6.1, backend + front).
**Cost: 1-2 talls · i18n ca/en/es obligatori (llei del repo).**

**P3 · La columna d'identitat visible al pas 3**, amb `etiquetaCapa`/`etiquetaInstancia` de
`utils/capaInstancia.js` (importació nova a l'ImportWizard) i el mateix rètol que la fitxa.
**Cost: 1 tall petit.**

**Ordre recomanat: P1 → P3 → P2.** P1 i P3 no obren cap porta nova (només fan la graella capaç);
P2 és la que deixa la persona crear germanes, i és la que exigeix el canvi de contracte de
`poms_confirmats`. Fer P2 abans que §6.1 estigui tancat deixaria un desmarcatge que menteix.

---

## 8 · TAULA FINAL DE RISCOS

| Risc | Gravetat | Estat |
|---|---|---|
| `key={pom_master_id}` duplicada amb germanes → cel·les barrejades | **Alta** | Tancada per P1 (`ordre` és estable: `extraction_views.py:1342`) |
| Perdre el teclejat en canviar la clau de fila | Alta | Mitigada: la clau nova ve del backend i no canvia entre renders |
| Regressió del payload d'un-POM-per-fila | Alta | **Ja guardada i verda** (`test_import_cadena_mesures_bruma.py`) |
| Desmarcar una germana en desmarca tres | Mitjana | §6.1 — entra a P2 |
| Poda/MANUAL parlen per POM amb germanes vives | Mitjana | §6.2 — **fora d'abast, decisió de producte**, datat 14/08 |
| Tocar el parent RULESET per «igualar-lo» | Mitjana | **NO fer-ho**: el seu domini no té capa/instància (§3) |
| `MeasurementBaseGrid` col·lapsa valors d'item per POM | Baixa (avui) | §6.4 — censat, peça pròpia |
| Tornar al pas 2 esborra el teclejat del pas 3 | Baixa | **Preexistent**, no el toca aquesta peça |
