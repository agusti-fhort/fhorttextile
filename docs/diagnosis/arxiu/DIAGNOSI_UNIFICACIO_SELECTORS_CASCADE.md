> ⚠️ SUPERADA 2026-07-20 — implementada pel Sprint UNIFICACIÓ SELECTORS (Patró B): CascadeSelector
> (component únic dos modes), endpoint garment-counts + ModelFilter ampliat, els 6 consumidors
> migrats i els 3 selectors vells + GarmentPOMMapEditor jubilats. Consulta només com a històric.

# DIAGNOSI — unificació dels selectors de cascada (AxesSelector · GarmentTypeSelector · ScopeSelector)

Data: 2026-07-20 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.

**Abast:** inventari FI dels 3 selectors de cascada de vestit per dimensionar la unificació
en UN sol component (decisió presa: `AxesSelector` com a base, els altres en són subconjunts).
Cobreix anatomia dels 3, el hook `useGarmentCatalog`, el patró backend de comptadors i la
matriu de migració (contracte de props del component unificat). No decideix res: les
decisions són humanes (Patró C).

**Convenció:** cada afirmació sobre el codi porta `fitxer:línia`. `"NO EXISTEIX"` =
confirmat absent al codi (no especulat). Les propostes van al bloc `💡` final, mai barrejades
amb els fets. Context previ: `DIAGNOSI_COMMERCE_ASSIGNACIO_I_CASCADE_GT.md` Bloc B (B1-B3)
ja mapeja els 3 selectors a alt nivell; aquesta diagnosi és l'inventari fi.

---

## Resum executiu (les 6 conclusions que desbloquegen la unificació)

1. **Els 3 selectors ja beuen de la MATEIXA font única** `useGarmentCatalog` per als nivells
   grup→família (`AxesSelector.jsx:33`, `GarmentTypeSelector.jsx:29`, `ScopeSelector.jsx:37`),
   i tots tres carreguen els ítems FORA del hook amb la MATEIXA crida
   (`garmentTypeItems.list({ garment_type, active:'true', page_size:200 })` a `AxesSelector.jsx:41`,
   `GarmentTypeSelector.jsx:51`, `ScopeSelector.jsx:52`). La convergència de dades ja està feta;
   el que divergeix és **l'estat, la forma del valor emès i el mode de parada**.

2. **AxesSelector és el superconjunt correcte com a base.** Té els 6 nivells
   (target→construction→fit→grup→família→ítem, `AxesSelector.jsx:53-154`); és totalment
   **controlat** (`value`/`onChange`, sense estat de selecció propi, `AxesSelector.jsx:20,23-26`);
   emet un `value` pla de 6 camps (`AxesSelector.jsx:48-49`); i família/ítem ja són
   **opcionals amb toggle** (`AxesSelector.jsx:132,149`). GarmentTypeSelector i la part de
   navegació de ScopeSelector en són subconjunts de nivells.

3. **El que ScopeSelector aporta i AxesSelector NO té és el mode FILTRE amb parada lliure
   multi-node**: selecció acumulativa `[{node_type:'GROUP'|'TYPE'|'ITEM', …}]`
   (`ScopeSelector.jsx:14,58-59`), navegar i marcar com a accions ortogonals a cada nivell
   (`ScopeSelector.jsx:87-92,109-110,131-138`). Això és exactament el "mode filtre amb parada
   lliure" que el component unificat necessita, i és el pilar del contracte de props unificat.

4. **Els consumidors reals són 6, sobre 5 pàgines** (re-grep verificat, §Verificació):
   AxesSelector → `GradingRuleSets.jsx:231` + `ItemAuthoring.jsx:256`; GarmentTypeSelector →
   `ModelWizard.jsx:411` + `POMBrowser.jsx:217`; ScopeSelector → `GradingRuleSets.jsx:895` +
   `SizeMapSetup.jsx:549`. **`GradingRuleSets` consumeix DOS selectors alhora** (AxesSelector
   per als eixos de match + ScopeSelector per a `applies_to`). **`ItemAuthoring` només usa 4
   nivells** (target→garmentGroup, `ItemAuthoring.jsx:59`), no família ni ítem.

5. **`GarmentPOMMapEditor` (marcat per jubilar G4) NO consumeix cap selector compartit**: té
   un widget propi d'un sol nivell (`GarmentPOMMapEditor.jsx:126-150`) i és codi mort no
   enrutat (`App.jsx:36-38`). No aporta cap requisit a la unificació — descartable.

6. **El backend de comptadors és barat i té patró canònic**: `fase_counts`
   (`models_app/views.py:122-144`) fa 1 query GROUP BY reusant el `ModelFilter` C1 via
   `filter_queryset`. Un `garment-counts` a dos nivells = **2 queries** (`values('garment_type')`
   + `values('garment_type_item')`), però **`ModelFilter` encara no exposa `garment_type_item`**
   (`views.py:46-49`) — caldria ampliar el FilterSet canònic, no crear-ne un de paral·lel.

---

## BLOC P1 · AxesSelector.jsx — anatomia completa

Fitxer: `frontend/src/components/grading/AxesSelector.jsx` (237 línies). Component per defecte +
3 subcomponents locals (`StepSection` `:171`, `TargetCard` `:185`, `SelectionButton` `:213`) +
helper `famLabel` (`:160-164`).

### Props
Signatura: `export default function AxesSelector({ ruleSets = [], value, onChange })` (`AxesSelector.jsx:20`).
- **`ruleSets`** — array, no obligatòria, default `[]` (`:20`). Font de disponibilitat dels eixos
  superiors: alimenta `availableTargetCodes/Constructions/Fits` (`:28-30`).
- **`value`** — objecte de selecció, sense default a la signatura; es protegeix amb `value || {}`
  en desestructurar (`:23-26`). Forma:
  `{ target, construction, fit, garmentGroup, garmentTypeId, garmentTypeItemId }`, tots default
  `null` (`:24-25`). Contracte comentat a `:14`.
- **`onChange`** — callback, no obligatòria (cridat amb `onChange?.(...)`, `:48`). **Signatura de
  crida: UN sol objecte SEMPRE complet amb els 6 eixos** = estat actual escampat + `patch`:
  `onChange?.({ target, construction, fit, garmentGroup, garmentTypeId, garmentTypeItemId, ...patch })`
  (`:48-49`). Mai un delta.

### Estat intern
- `const [items, setItems] = useState([])` (`:35`) — únic `useState`; ítems de la família triada.
- `useReducer`: **NO EXISTEIX**.
- 3 `useMemo`: `targetCodes` (`:28`, deps `[ruleSets]`), `constructions` (`:29`, deps
  `[ruleSets, target]`), `fits` (`:30`, deps `[ruleSets, target, construction]`).
- 1 `useEffect` (`:38-45`, deps `[garmentTypeId]`) — carrega ítems.
- El component **NO manté còpia interna de la selecció** (excepte `items`): és **controlat**
  pel pare via `value`/`onChange`.

### Càrrega de nivells (cascada de 6)
Ordre: **Target → Construction + Fit → Garment Group → Família → Item** (comentari `:10`).
- **Target** (`:53-66`): font estàtica `TARGETS` de `./gradingAxes` (`:4`); disponibilitat
  `targetCodes.has(tg.codi)` (`:61`).
- **Construction + Fit** (`:68-102`): fonts `constructions`/`fits` (memos de `gradingAxes`).
- **Garment Group** (`:104-119`): font `groups` de `useGarmentCatalog(target)` (`:33`).
- **Família** (OPCIONAL, `:121-137`): font `families = familiesOf(garmentGroup)` (`:34`).
- **Item** (OPCIONAL, `:139-154`): font `items` (estat local, carregat via
  `garmentTypeItems.list(...)` a `:41`, import de `../../api/endpoints` `:8`).

Els ítems **NO** venen del hook: només grup+família en venen; l'ítem es carrega a part.

### Propagació amunt
Funció única `pick(patch)` (`:48-49`) crida `onChange?.` amb l'objecte sencer + patch. Punts de
crida: target `:62`, construction `:80`, fit `:94`, group `:114`, família `:131-132`, item `:149`.

### Neteja en canviar nivell superior
La neteja va **explícita dins de cada `patch`**, posant a `null` tots els nivells inferiors
(no per efecte separat): triar target reseteja els 5 de sota (`:62`), construction els 4 (`:80`),
fit els 3 (`:94`), group els 2 (`:114`), família reseteja `garmentTypeItemId` (`:131-132`).
Comentari `:47`. L'efecte `:38-45` buida `items` quan `garmentTypeId` és falsy (`:39`).

### Dependències
`react` (`:1`), `react-i18next` (`:2`), de `./gradingAxes` (`:3-6`): `TARGETS`, `nomLocal`,
`availableTargetCodes`, `availableConstructions`, `availableFits`; `useGarmentCatalog` de
`./garmentCatalog` (`:7`); `garmentTypeItems` de `../../api/endpoints` (`:8`). Cap component UI
extern (tots locals).

### Comportaments especials
- **Target no és una prop**: es deriva de `value.target` i s'entrega a `useGarmentCatalog(target)`
  (`:33`). Si `target` és null → catàleg complet (comentari `:15-18`).
- **NEWBORN / filtre per target**: **NO EXISTEIX** codi específic dins d'AxesSelector; es delega
  al backend via el param `target` del hook (comentari `:16-17`).
- **Disabled**: només `TargetCard` té estat `available`/disabled (`:61,189-198`); els altres
  nivells (`SelectionButton`) sempre clicables.
- **Toggle (deseleccionar)**: només a família (`:132`) i ítem (`:149`); nivells 1-3 no.
- **Preselecció / default de selecció**: **NO EXISTEIX** (tot arrenca de `value` o `null`).
- **Gating de visibilitat** dels passos: `:69,85,105,122,140` (cada pas es mostra si el superior
  té valor i hi ha opcions).
- **Desviació de llei anotada** (fora scope): hex literals `#fdf6ee`/`#f8f8f8`/`#a06622`
  (`:197,220,230`) en comptes de tokens CSS. S'ANOTA, no es toca.

**Veredicte P1:** AxesSelector és el component més complet i el més "net" arquitectònicament
(controlat pur, valor pla, toggle ja present). És la base correcta.

---

## BLOC P2 · GarmentTypeSelector.jsx — inventari i diferències

Fitxer: `frontend/src/components/GarmentTypeSelector/GarmentTypeSelector.jsx` (129 línies).

### Anatomia
- **Props** (`:24`): `onSelect` (callback, signatura **`onSelect({ family, item })`** cridat només
  en triar l'ítem, `:106`); `selectedItemId` (default `null`, només marca visual, `:104`);
  `target` (default `null`, alimenta `useGarmentCatalog(target)`, `:29`). **`lang` NO és una prop
  declarada** (tot i que POMBrowser l'hi passa — no té efecte; i18n via `i18n.language` `:25-26`).
- **Estat intern** (`:30-34`): `grupActiu`, `family` (`null`=nivell famílies, no-null=nivell ítems),
  `items`, `loadingItems`, `err`. `useCallback` per `openFamily` (`:49`). Sense `useMemo`.
- **Font/nivells**: `useGarmentCatalog(target)` (`:29`) → `{ groups, familiesOf, loading }`; ítems
  peresosos per família (`:51`). Exposa **DOS nivells**: família (dins grup via `GroupPills` `:65`)
  i ítem. NO exposa target/construction/fit (rep `target` resolt de fora).
- **Neteja**: canvi de target via `useEffect` (`:38-44`); canvi de grup (`:65`) i `backToFamilies`
  (`:57`) fan `setFamily(null); setItems([])`.
- **Comportaments**: default `grupActiu`=primer grup (`:41`); marca selecció amb `var(--warn)`
  (`:125-127`); sense `disabled`.

### Diferències EXACTES vs AxesSelector
Comparteixen la font (`useGarmentCatalog(target)`) i la càrrega d'ítems idèntica.
- **GarmentTypeSelector fa el que AxesSelector NO fa:**
  - És **controlat internament** (estat propi grup/família/ítems, `:30-34`); AxesSelector és
    controlat de fora (`:20,23-26`).
  - Usa **`GroupPills`** per al grup (`:65`); AxesSelector renderitza grups com a `SelectionButton`
    plans (`AxesSelector.jsx:108-116`).
  - Navegació en **dos panells amb "← Back"** (famílies↔ítems, `:57,89`); AxesSelector és una pila
    vertical de 5 StepSections sempre visibles (`AxesSelector.jsx:54-154`).
  - Emet **`{ family, item }`** només en triar ítem (`:106`).
- **AxesSelector fa el que GarmentTypeSelector NO fa:** els 3 eixos superiors (target/construction/
  fit), coneix `ruleSets`/disponibilitat, toggle de família/ítem, valor pla de 6 camps, `TargetCard`
  amb disabled.

### Consumidors (2 reals)
- **ModelWizard** — import `ModelWizard.jsx:5`, ús `:411-415`. Props: `target={target}`,
  `selectedItemId={item?.id}`, `onSelect={({family:fam,item:it})=>{ setFamily(fam); setItem(it);
  setPicking(false); resetGrading() }}`. Únic consumidor que passa `target` i `selectedItemId`.
- **POMBrowser** — import `POMBrowser.jsx:13`, ús `:217-220`. Props: `lang={lang}` (no-op),
  `onSelect={(sel)=>{ setSelectedFamily(sel.family); setSelectedItem(sel.item) }}`. **NO** passa
  `target` ni `selectedItemId`.

### GarmentPOMMapEditor (G4, per jubilar)
**NO importa ni usa GarmentTypeSelector** (absent del grep de consumidors). Té un selector inline
divergent d'un sol nivell (`GarmentPOMMapEditor.jsx:126-150`, endpoint `garment-types/full/` `:26`).
Res únic; és un subconjunt més pobre. A més, tot el fitxer és codi mort declarat a `App.jsx:36-38`
(endpoints fantasma `pom-map/*` → 404, sense `<Route>`). **Prescindible per a la unificació.**

**Veredicte P2:** GarmentTypeSelector = subconjunt de nivells 4-6 d'AxesSelector amb UI de dos
panells i estat intern. La diferència real a preservar és **`selectedItemId` (marca visual)** i el
patró **"triar ítem tanca i emet"** de ModelWizard.

---

## BLOC P3 · ScopeSelector.jsx — el mode filtre amb parada lliure

Fitxer: `frontend/src/components/grading/ScopeSelector.jsx` (151 línies). Capçalera-llei
`:7-15`: "ÀMBIT D'APLICABILITAT del contenidor de grading de client… selecció JERÀRQUICA i
ACUMULATIVA sobre l'arbre únic. «aplica a» = «està disponible per a»".

### Props
`export default function ScopeSelector({ value = [], onChange })` (`:31`).
- **`value`**: array de nodes, default `[]`. Forma (contracte `:14`):
  `[{ node_type:'GROUP'|'TYPE'|'ITEM', group_codi?, garment_type_id?, garment_type_item_id?, label }]`.
- **`onChange`**: signatura **`onChange(nodes)`** amb el nou array complet (`:59`, `onChange?.`).
  El pare l'envia tal qual a `applies_to` (comentari `:15`).

### Estat intern
`grup` (codi grup actiu, `:38`), `familyId` (família oberta, `:39`), `items` (`:40`). La selecció
acumulada **NO és estat propi**: viu al pare (component controlat). `families = familiesOf(grup)`
derivat (`:41`). Sense `useMemo`/`useReducer`.

### Càrrega de nivells
Font: **`useGarmentCatalog(null)`** (`:37`) — el `null` és deliberat, "NO filtrem per target (no
bloquejant per defecte)" (`:35-36`). Nivell 1 GRUP → `GroupPills` (`:88`); nivell 2 FAMÍLIA →
`familiesOf(grup)` (`:95-120`); nivell 3 ITEM → càrrega pròpia via `garmentTypeItems.list(...)`
(`:49-56,123-143`).

### Concepte GROUP/TYPE/ITEM — parada lliure (EL PILAR de la unificació)
**No hi ha cap camp "stopLevel".** El mecanisme: **navegar i marcar són accions independents a
cada nivell**, i el `node_type` del node afegit a `value` codifica la profunditat de la parada.
- **Parada a GRUP**: checkbox independent del pill de navegació. `grupNode = {node_type:'GROUP',
  group_codi:grup, label}` (`:61-62`); checkbox `:89-92` (`checked={has(grupNode)}` /
  `onChange={()=>toggle(grupNode)}`). Comentari `:87`: "GRUP: navega i, alhora, es pot marcar
  sencer". Navegar (canviar `grup`) i marcar són botons diferents.
- **Parada a FAMÍLIA (TYPE)**: dos controls per família — **checkbox** (marcar, `:109`) i **botó
  de text** (baixar/navegar, `:110`, `setFamilyId(open?null:f.id)`, NO marca). Node
  `{node_type:'TYPE', garment_type_id:f.id, label}` (`:100`).
- **Parada a ITEM**: etiqueta sencera clicable com a checkbox (`:131-138`). Node
  `{node_type:'ITEM', garment_type_item_id:it.id, label}` (`:128`).
- **Marca "seleccionat"**: `has(n)=value.some(v=>sameNode(v,n))` (`:58`); identitat via `sameNode`
  (`:19-23`, compara `node_type` + els 3 ids amb `?? null`).
- **Retorn al pare**: `toggle(n)` (`:59`) afegeix/treu i crida `onChange(nouArray)`. Multi-node
  acumulatiu: GROUP + TYPE + ITEM poden coexistir a `value`.

### Propagació i neteja
Única via `toggle`→`onChange` (`:59`). La neteja de navegació (`:44-47` reancoratge, `:88` canvi
de grup, `:49-56` canvi de família) **NO toca `value`**: navegació i selecció són ortogonals — els
nodes marcats persisteixen encara que surtis de la branca.

### Dependències i comportaments
`react` (`:1`), `react-i18next` (`:2`), `garmentTypeItems` (`:3`), `GroupPills` de
`../GarmentTypeSelector/GroupPills` (`:4`), `useGarmentCatalog` (`:5`). Chips retirables per node
(`:72-84`); sense `disabled` ni preselecció; obligatorietat (≥1) la imposa el pare (P6).

### Consumidors (2 reals)
- **GradingRuleSets** — import `:5`, ús `:895` (`value={scope} onChange={nodes=>{ setScope(nodes);
  setScopeTouched(true) }}`), dins bloc `axesEditable` (`:890`). Lectura dual D1: `initialScope`
  llegeix `rs.applies_to` o converteix el FK `garment_group_codi` a node GROUP (`:746-748`); només
  s'envia si `scopeTouched` (`:740-743`).
- **SizeMapSetup** — import `:8`, ús `:549` (`value={wiz.applies_to} onChange={(nodes)=>set({
  applies_to:nodes })}`). **Obligatori ≥1** imposat pel pare: botó següent `disabled` si
  `wiz.applies_to.length===0` (`:552`, comentari `:547`).

**Veredicte P3:** el mode filtre/parada-lliure multi-node de ScopeSelector és l'única capacitat
que AxesSelector no té i que el component unificat ha d'absorbir. És un patró d'"emissió" diferent
(array de nodes acumulatiu vs objecte pla d'un sol camí), no de nivells: els nivells són els
mateixos que AxesSelector 4-6.

---

## BLOC P4 · useGarmentCatalog — contracte del hook + ganxo per a comptadors

Definició única: `frontend/src/components/grading/garmentCatalog.js:25`. El mateix fitxer exporta
`useGarmentGroups` (`:71`), hook germà (registre pur de grups) que consumeix `GarmentTypes.jsx:13`
— NO és `useGarmentCatalog`. Consumidors de `useGarmentCatalog` (3, verificat): `AxesSelector.jsx:33`
i `GarmentTypeSelector.jsx:29` amb `target`; `ScopeSelector.jsx:37` amb `null`.

### Què retorna
`return { groups, familiesOf, families, loading }` (`garmentCatalog.js:64`):
- **`groups`** — array normalitzat `{ codi, nom_en, nom_ca, nom_es }` (via `normGroup`
  `:21-23,51-60`), derivat dels `f.grup` distints presents a `families` ∩ grups actius del
  registre, ordre canònic (`:52-59`).
- **`familiesOf`** — `(grupCodi) => families.filter(f => f.grup === grupCodi)` (`:62`).
- **`families`** — array pla de `GarmentType` serialitzats (`GarmentTypeSerializer`,
  `pom/serializers.py:124-126`, `fields='__all__'` + `global_codi`/`global_nom` `:118-119` +
  `items_count` `:122` anotat via `Count('items')` a `pom/views.py:110`).
- **`loading`** — bool, **només cobreix famílies** (`:28,42,46`), NO el `registry`.
- **NO retorna `error`** (els `.catch` cauen a `set…([])` en silenci, `:35,45`). NO retorna
  `registry` en cru.

L'arbre NO és imbricat: dues llistes planes + funció de filtre. La cascada s'arma als consumidors:
`target→construction→fit→GRUP(groups[])→FAMÍLIA(familiesOf)→ITEM`. Els nivells target/construction/
fit venen de `gradingAxes` (`AxesSelector.jsx:28-30`), NO del hook. L'ITEM es carrega fora del hook.

### Cache
**No hi ha react-query, `useRef`, ni cache a nivell de mòdul.** Només `useMemo` per a `groups`
(`:51`, deps `[families, registry]`). `registry` via `useEffect` deps `[]` (`:31-37`, un cop per
muntatge); `families` via `useEffect` deps `[target]` (`:40-48`, **refetch a cada canvi de target**).
**NO es comparteix entre consumidors**: cada component muntat fa la seva ronda de crides. Guardes
anti-race amb flag `alive` (`:32,41,36,47`).

### Param `target`
`useGarmentCatalog(target)` (`:25`); s'afegeix condicionalment a l'API de famílies:
`...(target ? { target } : {})` (`:43`). Falsy → sense param → catàleg complet. El `registry` no
depèn de target (`:37`). Backend: `GarmentTypeViewSet.get_queryset` llegeix `?target=<codi>`
(`pom/views.py:117-128`); amb target filtra a `GarmentType` amb `SizingProfile.target__codi==target`
(`:123-127`).

### Endpoints
- `GET /api/v1/garment-groups/?page_size=200` (`garmentCatalog.js:33`, def `endpoints.js:154-155`).
- `GET /api/v1/garment-types/?actiu=true&page_size=500[&target]` (`garmentCatalog.js:43`, def
  `endpoints.js:146-147`).
- (fora del hook) `GET /api/v1/garment-type-items/?garment_type=<id>&active=true&page_size=200`
  (`endpoints.js:372-373`). Parseig uniforme `r.data?.results ?? r.data ?? []` (`:34,44`).

### Superfície que un comptador NO pot trencar
Cap consumidor fa spread ni `Object.keys` del retorn ni dels elements → **afegir claus noves és
segur**: `AxesSelector.jsx:33` usa `{ groups, familiesOf }`; `GarmentTypeSelector.jsx:29` usa
`{ groups, familiesOf, loading }`; `ScopeSelector.jsx:37` usa `{ groups, familiesOf }`. Els
elements `group`/`family` es llegeixen per camps concrets (`.codi`, `.nom_*`, `.id`, `.grup`,
`.codi_client`) — afegir `count` a cada objecte és segur (el patró ja existeix: `items_count` ja hi
és sense trencar ningú). Els ítems, carregats fora del hook, necessitarien tocar l'endpoint o cada
consumidor. **Font del compte**: el hook actual NO té accés al conjunt de models/filtres actius.

**Veredicte P4:** el contracte és ampliable per addició sense trencar consumidors. El que falta per
a comptadors "per node donat un filtre actiu" és (a) una entrada de filtres al hook i (b) un
endpoint agregat backend (P5). Sense cache compartida, cal vigilar el cost si es munten diversos
selectors alhora.

---

## BLOC P5 · Backend per als comptadors — patró `fase-counts` i cost d'un `garment-counts`

### Patró de referència: `fase_counts`
Fitxer `backend/fhort/models_app/views.py`. Acció `:122-123`
(`@action(url_path='fase-counts')` → `GET /api/v1/models/fase-counts/`).
- **Filtra reusant C1**: `qs = self.filter_queryset(self.get_queryset()).order_by()` (`:141`) —
  aplica `filterset_class = ModelFilter` + `SearchFilter` + `OrderingFilter` (`:70`). Font única, no
  re-implementa filtres.
- **Neteja l'order_by** amb `.order_by()` buit (`:141`, doc `:134-136`): l'`ordering=['-prioritat']`
  (`:74`) injectaria columnes al GROUP BY i el trencaria.
- **Agrupa** `qs.values('fase_actual').annotate(n=Count('id'))` (`:142`) = **1 query** GROUP BY.
- **Forma JSON** `{ 'counts': {<fase>:n}, 'total': sum }` (`:143-144`).
- **Sense N+1**: comptat a la BD sense carregar files; per `fase-counts` (≠`list`) `get_queryset`
  retorna el qs pla sense anotacions de cicle (`:90-91` vs `:100-115`).

### FilterSet canònic C1 — `ModelFilter`
`views.py:27` (única definició; docstring C1 `:28-41`: font única de Model list + fase-counts +
board `by_model`). Camps:
- `Meta.fields` (`:46-49`): `fase_actual, garment_type, responsable, temporada, any, estat,
  prioritat, customer, collection, data_objectiu` (`customer`, `responsable`, `garment_type` són FK).
- Custom: `collection` `CharFilter icontains` (`:42`), `data_objectiu` `DateFromToRangeFilter`
  (`:43`), `assignee` `CharFilter(method='filter_assignee')` (`:44,51-65`).
- **NO EXISTEIX** camp `garment_type_item`, `garment_group`, `fit`, ni `ss` literal. `garment_type`
  sí (`:48`); "ss" existeix com a `temporada`+`any`.

### Model — relacions
`backend/fhort/models_app/models.py`: `garment_type` FK→`pom.GarmentType`, `related_name='models'`
(`:146-152`); `garment_group` FK→`pom.GarmentGroup` (`:153-159`); `garment_type_item`
FK→`tasks.GarmentTypeItem` (`:161-167`). Jerarquia dades: `pom.GarmentType` (família,
`pom/models.py:392`) **1—N** `tasks.GarmentTypeItem` (variant, FK `garment_type` CASCADE
`related_name='items'`, `tasks/models.py:290-291`). `Model` apunta **independentment** als dos FK
(`garment_type` i `garment_type_item`) — no deriva l'un de l'altre.

### Cost d'un `garment-counts` a dos nivells
FET (patró ancorat a `views.py:142`): counts per **dos eixos independents** amb subtotals separats
per eix = **2 queries**:
```
qs.values('garment_type').annotate(n=Count('pk'))          # query 1
qs.values('garment_type_item').annotate(n=Count('pk'))     # query 2
```
Un únic `qs.values('garment_type','garment_type_item').annotate(Count('pk'))` **NO equival**: dona 1
query però amb el GROUP BY del **parell** (files (type,item)), no dos totals per nivell. Cada query
ha de portar `.order_by()` buit abans del `values()` (patró `:141`). Ambdues sobre el mateix
`self.filter_queryset(self.get_queryset()).order_by()`. Sense N+1.

**Veredicte P5:** un `garment-counts` és barat (2 queries) i té patró canònic a copiar
(`fase_counts`). El blocador és que **`ModelFilter` no exposa `garment_type_item`** (`:46-49`): per
filtrar-hi cal **ampliar el FilterSet C1**, no crear-ne un de paral·lel (llei "unificar el ja
construït"). El camp del model ja existeix (`models.py:161`).

---

## BLOC P6 · MATRIU DE MIGRACIÓ — contracte de props del component unificat

Re-grep de consumidors verificat (§Verificació). Sis usos vius sobre cinc pàgines. **Un component
unificat ha de cobrir totes aquestes columnes.**

| Consumidor (`fitxer:línia`) | Selector actual | Nivells usats | Mode | Parada | `target` | Valor emès (avui) |
|---|---|---|---|---|---|---|
| `GradingRuleSets.jsx:231` (eixos match) | AxesSelector | target→construction→fit→grup→**família→ítem** (6) | selecció (1 camí) | lliure fins ítem (toggle) | derivat de `value.target` | objecte pla 6 camps → `onAxesChange` reparteix a 6 setters (`:100-104`) |
| `ItemAuthoring.jsx:256` | AxesSelector | target→construction→fit→**grup** (4) | selecció (1 camí) | s'atura a grup (mai llegeix família/ítem) | derivat de `value.target` | objecte pla; només llegeix 4 camps (`:59,96-101`) |
| `ModelWizard.jsx:411` | GarmentTypeSelector | grup→família→**ítem** (3) | selecció (1 camí) | **obligada a ítem** (emet en triar ítem) | **passat** (`target={target}`) | `{ family, item }` → desa i tanca picker + `resetGrading()` (`:411-415`) |
| `POMBrowser.jsx:217` | GarmentTypeSelector | grup→família→**ítem** (3) | selecció (1 camí) | obligada a ítem | **no passat** (catàleg complet) | `{ family, item }` → fixa família+ítem (`:217-220`) |
| `GradingRuleSets.jsx:895` (`applies_to`) | ScopeSelector | grup→família→ítem (3) | **filtre multi-node** | **lliure** (GROUP/TYPE/ITEM) | **null** (no bloquejant) | array de nodes acumulatiu → `setScope` + `scopeTouched` (`:895`) |
| `SizeMapSetup.jsx:549` | ScopeSelector | grup→família→ítem (3) | **filtre multi-node** | **lliure**, **obligatori ≥1** | null | array de nodes → `set({applies_to})`; obligatorietat al pare (`:552`) |

### Eixos de variació que el contracte unificat ha de parametritzar (derivats de la matriu)
1. **Profunditat màxima / nivell d'inici** — ItemAuthoring vol tallar a `grup` (4); ModelWizard/
   POMBrowser comencen a `grup` (no tenen target/construction/fit); GradingRuleSets(axes) vol els 6.
   → cal poder **acotar quins nivells es mostren** (nivell superior i inferior).
2. **Mode d'emissió** — objecte pla d'1 camí (AxesSelector) **vs** array de nodes acumulatiu
   (ScopeSelector). → prop `mode: 'single' | 'multi'` (o equivalent). En `single` emet `value` pla;
   en `multi` emet `nodes[]`.
3. **Parada lliure vs obligada a ítem** — ScopeSelector i AxesSelector permeten parar a qualsevol
   nivell; GarmentTypeSelector (ModelWizard/POMBrowser) **només emet en triar ítem i tanca**. → prop
   de política de parada + callback de "confirmació" (tancar picker).
4. **`target`** — passat (ModelWizard) / derivat del valor (AxesSelector) / null forçat
   (ScopeSelector). → prop `target` explícita, opcional.
5. **Marca visual d'ítem seleccionat** — `selectedItemId` (GarmentTypeSelector) i el ressaltat de
   nodes (ScopeSelector). → derivable del `value`/`nodes`.
6. **`ruleSets` / disponibilitat** — només GradingRuleSets(axes) i ItemAuthoring passen `ruleSets`
   per gating dels eixos superiors; els altres no en tenen. → prop `ruleSets` opcional (default `[]`).
7. **Obligatorietat (≥1)** — la imposa el pare avui (`SizeMapSetup.jsx:552`), no el selector. →
   pot quedar al pare; NO cal que el component unificat la implementi.

**Veredicte P6:** el component unificat = AxesSelector (nivells + valor pla + toggle) + capacitat
`multi`/parada-lliure de ScopeSelector + política "emet-i-tanca a l'ítem" de GarmentTypeSelector,
tot governat per ~6 props (`mode`, acotació de nivells, `target`, `ruleSets`, política de parada,
callback de confirmació). Els dos modes de valor (pla vs nodes[]) són la decisió d'arquitectura més
gran a validar.

---

## Verificació del documentador (re-grep dels consumidors reals)

`grep -rn "<Selector>" frontend/src --include=*.jsx --include=*.js` (imports+usos, exclosos
comentaris i el propi fitxer):

- **AxesSelector**: `pages/GradingRuleSets.jsx:4,231` · `pages/ItemAuthoring.jsx:7,256`. (Els altres
  matches són comentaris a `gradingAxes.js:3-5`, `ScopeSelector.jsx:34`, `garmentCatalog.js:8`,
  `GarmentTypeSelector.jsx:13`.) → **2 consumidors** (P1 no els havia mapejat; corregit aquí).
- **GarmentTypeSelector**: `pages/ModelWizard.jsx:5,411` · `components/POMBrowser/POMBrowser.jsx:13,217`.
  → **2 consumidors**. `GarmentPOMMapEditor` NO hi surt (confirma §P2: no el consumeix).
- **ScopeSelector**: `pages/GradingRuleSets.jsx:5,895` · `pages/SizeMapSetup.jsx:8,549`.
  → **2 consumidors**.
- **useGarmentCatalog**: `AxesSelector.jsx:33` · `ScopeSelector.jsx:37` · `GarmentTypeSelector.jsx:29`.
  → **3 consumidors** (coincideix amb P4).

**Total: 6 usos de selector sobre 5 pàgines** (GradingRuleSets en té 2: axes + scope).

---

## TAULA FINAL de riscos / EXISTEIX-FALTA-DIFERENT (per al CTO)

| Tema | Estat | Àncora | Nota per a la decisió |
|---|---|---|---|
| Font de dades grup→família | **EXISTEIX i ja unificada** | `useGarmentCatalog` a `AxesSelector.jsx:33`, `GarmentTypeSelector.jsx:29`, `ScopeSelector.jsx:37` | La convergència de dades ja està feta; unificar és de UI/estat/valor. |
| Càrrega d'ítems | **EXISTEIX, idèntica x3** | `AxesSelector.jsx:41`, `GarmentTypeSelector.jsx:51`, `ScopeSelector.jsx:52` | Fora del hook; mateix endpoint i params. |
| Mode filtre multi-node / parada lliure | **EXISTEIX només a ScopeSelector** | `ScopeSelector.jsx:14,58-59,87-110` | És la capacitat que AxesSelector NO té; pilar del contracte unificat. |
| Valor pla 6 camps amb toggle | **EXISTEIX només a AxesSelector** | `AxesSelector.jsx:48-49,132,149` | Base del component; el mode `single`. |
| "Emet-i-tanca a l'ítem" | **EXISTEIX només a GarmentTypeSelector** | `ModelWizard.jsx:411-415`, `GarmentTypeSelector.jsx:106` | Política de parada obligada; cal preservar-la per al wizard. |
| `target` passat vs derivat vs null | **DIFERENT per consumidor** | `ModelWizard.jsx:411` (passat) · `AxesSelector.jsx:33` (derivat) · `ScopeSelector.jsx:37` (null) | Cal prop `target` explícita opcional. |
| Acotació de nivells (profunditat) | **DIFERENT** (4 vs 3 vs 6) | `ItemAuthoring.jsx:59` (4) · `ModelWizard.jsx:411` (3) · `GradingRuleSets.jsx:231` (6) | Cal parametritzar nivell superior i inferior visibles. |
| `ruleSets` / disponibilitat eixos | **EXISTEIX parcial** (2/6 consumidors) | `GradingRuleSets.jsx:231`, `ItemAuthoring.jsx:256` | Prop opcional default `[]`; els altres no en tenen. |
| Comptadors per node al hook | **FALTA** (ampliable sense trencar) | `garmentCatalog.js:64`; patró `items_count` a `serializers.py:122` | Afegir claus és segur; falta font del compte (filtres + endpoint). |
| Backend `garment-counts` | **FALTA** (patró clar) | `views.py:122-144` (fase-counts) | 2 queries; copiar el patró. |
| `ModelFilter` exposa `garment_type_item` | **FALTA** (blocador del compte per ítem) | `views.py:46-49` (no hi és); camp model a `models.py:161` | Ampliar el FilterSet C1, NO crear-ne un de paral·lel. |
| Cache compartida del hook | **NO EXISTEIX** | `garmentCatalog.js` (sense react-query/module cache) | Cada selector muntat refetcha; vigilar si el compte és car. |
| `GarmentPOMMapEditor` (G4) | **CODI MORT, descartable** | `App.jsx:36-38`; widget propi `GarmentPOMMapEditor.jsx:126-150` | No consumeix cap selector; no aporta requisits. |
| Desviació tokens CSS (hex) a AxesSelector | **ANOTAT** (fora scope) | `AxesSelector.jsx:197,220,230` | `#fdf6ee`/`#f8f8f8`/`#a06622`; netejar en passada futura. |

---

## 💡 PROPOSTES (a validar — decisió humana, Patró C)

> Res d'això està decidit; són hipòtesis de disseny derivades dels fets de dalt.

1. **💡 Component unificat `CascadeSelector` basat en AxesSelector**, amb prop `mode`:
   - `mode='single'` → valor pla `{ target, construction, fit, garmentGroup, garmentTypeId,
     garmentTypeItemId }` (comportament AxesSelector actual, cobreix GradingRuleSets-axes,
     ItemAuthoring, ModelWizard, POMBrowser).
   - `mode='multi'` → array de nodes `[{ node_type, …, label }]` (comportament ScopeSelector,
     cobreix GradingRuleSets-scope, SizeMapSetup).
   Els dos modes comparteixen la mateixa cascada visual i la mateixa font de dades; només difereix
   l'emissió i el marcatge. **Decisió gran a validar: un component amb dos modes vs dos components
   amb un nucli compartit.**

2. **💡 Props del contracte unificat** (derivades de la matriu P6):
   `{ mode, value|nodes, onChange, target?, ruleSets?=[], minLevel?, maxLevel?, stopPolicy?:
   'free'|'require-item', onConfirm? }`. `minLevel/maxLevel` cobreixen l'acotació (ItemAuthoring
   talla a grup; ModelWizard comença a grup). `stopPolicy='require-item'` + `onConfirm` reprodueixen
   el "emet-i-tanca" de ModelWizard.

3. **💡 Comptadors per node**: afegir `count` a cada `group`/`family` del retorn de
   `useGarmentCatalog` (segur per addició, P4) alimentat per un nou endpoint
   `GET /api/v1/models/garment-counts/` que copiï `fase_counts` (2 queries, P5). Requereix **ampliar
   `ModelFilter.Meta.fields` amb `garment_type_item`** (`views.py:48`) abans, o els counts per ítem
   no seran filtrables per la mateixa font C1.

4. **💡 Cache compartida abans dels comptadors**: si el component unificat i els comptadors es
   munten sovint junts, considerar promoure `useGarmentCatalog` a react-query o a un provider
   (avui refetcha per consumidor, `garmentCatalog.js:40-48`). És canvi d'arquitectura, no
   d'ampliació de contracte — validar cost/benefici.

5. **💡 En migrar, jubilar formalment `GarmentPOMMapEditor`** (ja codi mort, `App.jsx:36-38`) per no
   arrossegar el seu widget d'un sol nivell com a "quart selector".
