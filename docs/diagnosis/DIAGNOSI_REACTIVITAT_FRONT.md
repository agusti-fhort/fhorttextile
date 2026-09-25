# DIAGNOSI · REACTIVITAT DEL FRONT — «els canvis no es veuen fins al refresh»

**Patró A · READ-ONLY.** Protocol FASE_B. Cap escriptura, cap canvi de codi, cap commit.
**Codi mesurat:** `/var/www/ftt-staging`, branca `dev`, `git pull` → *Already up to date*, HEAD `935991db`.
**Àmbit:** `frontend/src` (339 fitxers `.js`/`.jsx`). El backend només s'ha llegit per **verificar contractes** de resposta (no s'hi proposa res).
**Data:** 09/09/2026.

> Tot el que hi ha aquí és **mesurat** amb `grep`/AST-lite sobre el codi del disc, amb `fitxer:línia`. On no ho he pogut mesurar, ho dic explícitament a §5 (Límits).

---

## 0. Resum en cinc línies

1. **No hi ha cap capa d'estat de servidor.** `@tanstack/react-query` és una dependència declarada des del primer commit de la SPA i **té 0 imports** al codi i **0 presència al `dist/` desplegat**.
2. El patró dominant és **`useEffect` + `fetch`/axios + `useState` local, un per component**: 85 fitxers llegeixen del servidor pel seu compte.
3. Per tant **no hi ha caché ni invalidació**: **43 dels 116 endpoints de lectura tenen més d'un component propietari**, cadascun amb la seva còpia i el seu cicle de refresc.
4. El defecte **no és «mutacions sense refetch»** — d'aquestes gairebé no n'hi ha (§3: 6 de 204, i les 6 són falsos positius). El defecte és **l'ABAST del refresc**: una mutació refresca la superfície que la dispara i deixa ràncies les germanes que tenen la mateixa dada.
5. El cas concret (§2) no és només «no es veu»: `agrupaPerRonda` **s'empassa la tasca en silenci** quan la llista de rondes va endarrerida. La tasca no apareix ni fora del contenidor.

---

## Q1 · PATRÓ D'ESTAT DEL SERVIDOR

### Q1.1 · Inventari de mecanismes

| Mecanisme | Instal·lat | Usat | Mesura |
|---|---|---|---|
| `@tanstack/react-query` | **sí** (`frontend/package.json:22`, `^5.100.14`) | **NO** | `grep -rl "@tanstack/react-query" src/` → **0 fitxers**. Cap `QueryClient`/`useQuery` al `frontend/dist/assets/*.js`. |
| SWR | no | — | absent del `package.json` |
| `zustand` | sí (`^5.0.13`) | sí, **però mai per a dades de servidor** | 2 fitxers: `store/auth.js` (sessió) i `store/molla.js` (cua del breadcrumb) |
| React Context | — | no per a dades de servidor | cap provider de dades |
| **`useEffect` + `fetch`/axios + `useState`** | — | **sí — és el patró** | **85 fitxers** llegeixen del servidor; **501** ocurrències de `useEffect` a `src/` |
| `CustomEvent('plan:changed')` | — | sí, **1 sol cas** | 2 emissors, 3 oients (§Q1.3) |

**Procedència de React Query:** entra al `package.json` al commit `0cd24539` (2026-05-25, *«feat: React SPA — login, dashboard, models, layout complet»*), o sigui **al bastiment inicial**. Està a `node_modules/@tanstack/` i mai s'ha importat. **No és una migració a mitges: és una dependència que no ha arribat a néixer.**

### Q1.2 · El patró dominant, transcrit

Cada component **posseeix** la seva dada, la carrega en muntar-se i la torna a carregar quan canvia una dep del seu `useEffect`/`useCallback`. No hi ha clau de caché, ni deduplicació, ni invalidació creuada.

**Exemple 1 — `components/model/DashboardTab.jsx:93-107`** (el del símptoma):

```js
const load = useCallback(() => {
  let alive = true
  setLoading(true); setError('')
  fetch(`${API}/api/v1/models/${modelId}/dashboard/`, { headers: {...} })
    .then(r => { if (!r.ok) throw new Error('http'); return r.json() })
    .then(d => { if (alive) setData(d) })
    ...
}, [modelId])                 // ← ÚNICA dep: només es recarrega si canvia el model
useEffect(() => load(), [load])
```

`load` no s'exporta ni es publica enlloc. L'únic que la rep és el fill: `<WorkPlan ... onRefresh={load} />` (`DashboardTab.jsx:183`). **El pare (`ModelSheet`) no en té cap nansa.**

**Exemple 2 — `components/model/WorkPlan.jsx:233-248`**, el mateix patró amb versió-comptador com a invalidació manual:

```js
const [versio, setVersio] = useState(0)
useEffect(() => {
  models.rondes(modelId).then(...)     // ← les VOLTES
  models.taskLog(modelId).then(...)
}, [modelId, versio])
const refrescaTot = () => { setVersio(v => v + 1); onRefresh?.() }
```

**Exemple 3 — `pages/ModelSheet.jsx:238-256`**, tres loaders germans i independents al mateix fitxer:

```js
const reloadModel  = useCallback(() => { fetch(`${API}/api/v1/models/${id}/`)... }, [id])
const reloadTaula  = useCallback(() => { fetch(`${API}/api/v1/models/${id}/taula-mesures/`)... }, [id])
const reloadTasks  = useCallback(() => { modelTasks.listByModel(id)... }, [id])
```

### Q1.3 · L'única invalidació creuada que existeix ja

`api/endpoints.js:7-10`:

```js
export const planChanged = (res) => {
  try { window.dispatchEvent(new CustomEvent('plan:changed')) } catch { }
  return res                                    // ← pass-through: no trenca cap .then()
}
```

* **Emissors (2):** `endpoints.js:101` (`models.openTask`) i `endpoints.js:583` (`plan.reorder`).
* **Oients (3):** `pages/Dashboard.jsx:291`, `pages/Planning.jsx:178`, `components/planning/ProjectGantt.jsx:84`.

**Aquest és el precedent que importa** (§Q4): el mecanisme existeix, funciona, és pass-through i no depèn de cap llibreria. El que li falta és cobertura.

### Q1.4 · La mesura que explica el símptoma general

De **116** endpoints de lectura distingibles, **43 tenen més d'un component propietari**. Els set primers:

| Còpies | Endpoint | Propietaris |
|---:|---|---|
| 7 | `/api/v1/size-systems/` | BaseSetPanel · RunsCataleg · SizeSystemSelector · JocsDeRegles · ResumWizardPartit · CatalegPecesItem · ModelWizard |
| 7 | `/api/v1/grading-rule-sets/` | GraduacioContenidor · GraduacioPanel · JocsDeRegles · ResumWizardPartit · CustomerDetail · ItemAuthoring · ModelWizard |
| 7 | `/api/v1/models/<id>/` | FittingPrintSheet · ModelFabric · ModelSheet · ModelWizard · PropagatedEditor · TallerPatro · TechSheetEditor |
| 7 | `/api/v1/garment-groups/` | RunRestrictionEditor · GraduacioContenidor · GraduacioPanel · garmentCatalog · ResumWizardPartit · ItemAuthoring · ModelWizard |
| 6 | `/api/v1/model-fitxers/` | App · AssetNavigator · FilePicker · FittingDetail · ModelSheet · TechSheetEditor |
| 6 | `/api/v1/piece-fittings/<id>/` | measureSources · FittingDetail · FittingPrintSheet · TechSheetEditor · taulaPresaPerTalla · taulesQ8 |
| 6 | `/api/v1/poms/cerca/` | EditableTable · ImportWizard · MeasurementBaseGrid · POMBrowser · TaulaPOMsCataleg · POMPicker |

I el tall que dona la forma del problema:

```
fitxers que LLEGEIXEN del servidor : 85
fitxers que ESCRIUEN al servidor   : 56
fitxers que fan les DUES coses     : 45
fitxers NOMÉS LECTORS              : 40   ← es queden ranci quan un altre escriu
```

**`components/model/DashboardTab.jsx` és a la llista dels 40 només-lectors.** No té cap manera de ser invalidat des de fora. Això no és una hipòtesi sobre el símptoma: és la seva causa estructural, mesurada.

---

## Q2 · CAS CONCRET — assignar una tasca a una ronda

### Q2.1 · Les dues fonts que han d'estar d'acord

El contenidor de volta del Pla de treball es dibuixa **creuant dos payloads que arriben per portes diferents**:

| | Endpoint | Qui el posseeix | Quan es refresca |
|---|---|---|---|
| **Tasques** (amb `ronda_seq`) | `GET /api/v1/models/<id>/dashboard/` | `DashboardTab.data` | `load()` — `DashboardTab.jsx:93` |
| **Voltes** (`seq`, `estat`, `entrega`, `oberta_el`) | `GET /api/v1/models/<id>/rondes/` | `WorkPlan.rondes` | `useEffect [modelId, versio]` — `WorkPlan.jsx:243` |

Verificat al backend: el compositor `model_dashboard_view` (`fhort/models_app/views.py:4507`) serveix `ronda`/`ronda_seq` **per tasca** (`views.py:4617-4618`) però **no serveix la llista de Rondes**. D'aquí el segon fetch. Les dues fonts es refresquen per canals **separats i no sincronitzats**.

### Q2.2 · El creuament, i on es perd la tasca

`utils/rondes.js:102-150`. Els blocs es construeixen **a partir de la llista de voltes**, no de les tasques:

```js
for (const f of llista) {
  if (f.ronda_seq == null) { orfes.push(f); continue }   // :117
  perSeq.get(f.ronda_seq).push(f)
}
...
const blocs = voltes.map(r => bloc(r, perSeq.get(r.seq) || []))   // :148
if (orfes.length) blocs.push(bloc(null, orfes))                   // :149
```

**🚨 Aquí hi ha el fet dur.** Una tasca amb `ronda_seq = N` on `N` **no és a `voltes`**:

* no entra a `orfes` (la guarda de `:117` és `ronda_seq == null`, i la seva no ho és);
* no té bloc a `:148` (cap volta amb aquell `seq`);
* → **desapareix del Pla de treball, sense error, sense buit, sense traça.**

No és «el contenidor no apareix i la tasca es veu solta». És **la tasca i el contenidor alhora**. Un `console` net i un 200 OK a la xarxa.

I hi ha un segon efecte al mateix creuament: `WorkPlan.jsx:274` fa `const perVoltes = rondes.length > 0`. Amb `rondes` ranci a `[]` — el cas del **primer** gest sobre un model, que és quan `open-task` fa **néixer la R1** — el Pla cau a la branca **plana** i **no pinta cap contenidor de volta ni el botó «+ Nova ronda»** (`WorkPlan.jsx:501`, condicionat a `perVoltes`).

Que `open-task` fa néixer la R1 està **provat al banc del backend**, no deduït — `fhort/tasks/test_m1bis_fit4.py:95-101`:

```python
def test_gest_open_task(self):
    resp = self._client().post(f'/api/v1/models/{self.model.pk}/open-task/', {'code': 'pom'}, ...)
    r1 = self._r1()
    self.assertIsNotNone(r1, 'open-task no ha fet néixer la R1')
    self.assertEqual(ModelTask.objects.get(model=self.model).ronda_id, r1.pk)
```

### Q2.3 · Els vuit gestos d'escriptura del Pla, i quin refresca què

**Dins de `WorkPlan` conviuen dos vocabularis de refresc** i la tria no segueix cap regla escrita:

| Gest | Línia | Crida | Refresca `tasques` | Refresca `rondes` |
|---|---:|---|:---:|:---:|
| `doTransition` (Pause) | 304-311 | `modelTasks.transition` | ✅ `onRefresh()` | ❌ |
| `playMine` sense eina | 316-344 | **`models.openTask`** | ✅ `onRefresh()` (`:334`) | ❌ |
| `confirmHandoff` | 356 | `modelTasks.claim` → `playMine` | ✅ (via playMine) | ❌ |
| `handleStop` | 387-404 | `transition` ×2 | ✅ `onRefresh()` (`:396`) | ❌ |
| `TempsDeclaratForm.onFet` | 523-531 | `tempsDeclarat` | ✅ `onRefresh()` (`:528`) | ❌ |
| **`obreVolta`** («+ Nova ronda») | 416-434 | `models.obrirRonda` | ✅ | ✅ `refrescaTot()` (`:431`) |
| **`EntregaDialog.onFet`** | 534-543 | `entregues.entrega` | ✅ | ✅ `refrescaTot()` (`:540`) |
| **`OkClientDialog.onFet`** | 545-554 | `rondes.okClient` | ✅ | ✅ `refrescaTot()` (`:550`) |

**5 gestos de 8 refresquen només meitat de la font.** I els tres que ho fan bé (`refrescaTot`, definit a `:248`) són precisament els **tres gestos de volta** — els que el tram M2 va escriure sabent que tocaven les dues coses. Els **cinc gestos de TASCA** van néixer abans (P3/P4a) amb `onRefresh?.()` i **ningú els va reobrir quan M2 va afegir la segona font**.

> 🚨 **La llei que se'n desprèn:** *afegir una segona font a una pantalla no actualitza els gestos que ja hi vivien.* El comentari de `:302` encara diu «després refresca **el dashboard**» — era exacte quan es va escriure i des d'M2 ja no ho és.

### Q2.4 · El camí des de `ModelSheet` — la mateixa forma, un nivell més amunt

`pages/ModelSheet.jsx:1106-1110` (sortida `ronda`/`correccio` del modal `ObrirTascaDialog`, que és **literalment «assignar aquesta tasca a una volta»**: `codes: [d.code]`):

```js
models.obrirRonda(parseInt(id), { motiu, codes: [d.code] })
  .then(() => {
    reloadTasks(); reloadModel()          // ← modelTaskRows + model. RES MÉS.
    if (d.fitxerId) obreFitxa(d.fitxerId)
    else obreDeDebo(d.tab, d.code, d.opts || {})
  })
```

`reloadTasks` omple `ModelSheet.modelTaskRows` i `reloadModel` omple `ModelSheet.model`. **Cap de les dues arriba a `DashboardTab.data` ni a `WorkPlan.rondes`**, que són les dues fonts que dibuixen el contenidor. `DashboardTab` es munta a `ModelSheet.jsx:1201-1206` amb quatre props:

```jsx
<DashboardTab modelId={parseInt(id)} onOpenTab={setActiveTab}
              navigate={navigate} wpVersion={wpVersion} />
```

`wpVersion` **sembla** una nansa d'invalidació i **no ho és**: dins de `DashboardTab` el seu únic ús és re-clavar un fill (`DashboardTab.jsx:336`, `key={`wp-${wpVersion}`}` sobre `WatchpointsPanel`). El `load()` del dashboard no en depèn.

### Q2.5 · ¿La resposta portava prou per repintar sense refetch? — **No**

Els dos endpoints del cas tornen **identificadors, no objectes**:

* `open-task` → `fhort/tasks/views_b.py:794`:
  `{'task_id', 'code', 'created', 'status', 'missing_config'}` — ni la tasca sencera ni la ronda.
* `obrir-ronda` → `fhort/tasks/views_b.py:1849-1858`:
  `{'ronda_id', 'seq', 'motiu', 'codes_replicats', 'codes_omesos', 'codes_adoptats', 'tasques': [ids]}` — **`tasques` és una llista d'ids**.

Per tant **una actualització optimista des de la resposta no és possible amb el contracte actual**. El refetch no és una comoditat: és l'única via que hi ha avui.

### Q2.6 · Veredicte de Q2

Les quatre causes que la pregunta proposava, resoltes:

| Hipòtesi | Veredicte |
|---|---|
| ¿No hi ha refetch? | **Parcialment.** N'hi ha, però només d'**una** de les dues fonts (`tasques` sí, `rondes` no) en 5 dels 8 gestos del Pla. |
| ¿Estat local no actualitzat des de la resposta? | **No aplica** — el disseny és refetch, no optimista. |
| ¿Caché no invalidada? | **No hi ha caché** que invalidar (§Q1). L'equivalent és `WorkPlan.versio`, i no es bumpa. |
| ¿La resposta no torna l'objecte creat? | **Correcte i verificat** (§Q2.5): torna ids. |

**Causa arrel:** *el contenidor de volta es dibuixa creuant dues fonts que es refresquen per canals separats; els gestos de tasca només refresquen la primera; i el creuador (`agrupaPerRonda:148`) **descarta en silenci** el que no quadra.*

---

## Q3 · CENS DE MUTACIONS

**Mètode.** S'han extret de `api/endpoints.js` els 69 objectes exportats i, del cos de cadascun, quins mètodes són `client.post/patch/put/delete`. Amb aquest mapa s'han localitzat les crides reals a `src/` (fora d'`api/`), més tot `fetch()` amb `method` de mutació. **204 punts d'escriptura a 56 fitxers.** De cada punt s'ha llegit la cadena `.then()` (finestra de 24 línies).

### Q3.1 · Recompte global

| Bucket | N | Què fa després de la mutació |
|---|---:|---|
| **A** | **88** | Refetch propi, bump de versió o `planChanged` |
| **B** | **55** | Delega al pare (`onSaved`/`onFet`/`onChanged`/`onRefresh`…) |
| **C** | **6** | Navega (la pantalla destí es munta de nou) |
| **D** | **49** | Només `setState` local |
| **E** | **6** | Res detectat |
| | **204** | |

### Q3.2 · El bucket E, verificat a mà — **cap és un defecte**

| Lloc | Veredicte |
|---|---|
| `pages/FittingDetail.jsx:21` | **(b)** — `useSessionField` **retorna** la promesa a `useDebouncedSave`; el camp és controlat |
| `components/model/CheckMeasureEditor.jsx:352` | **(b)** — adaptador, **retorna** la promesa; refresca qui la consumeix |
| `components/model/fittingGridAdapter.jsx:501` | **(b)** — factory `makeFittingOnSave`, **retorna** la promesa |
| `components/model/ResumWizardPartit.jsx:1326` | **(b)** — dins de `desa(...)`, que ja porta el refresc |
| `components/ImportWizard/ImportWizard.jsx:732` | **(b)** — passa de pas dins d'una cadena que sí refresca |
| `pages/ModelSheet.jsx:365` | **(b) deliberat** — `pauseActiveTask`, fire-and-forget **en desmuntar**; no queda ningú a repintar (documentat a `:355-362`) |

> **🔑 El front d'FTT no té mutacions «fire-and-forget». Zero de 204.** La higiene del `.then()` és bona i uniforme. **Buscar aquí el defecte de Salva és buscar-lo on no és.**

### Q3.3 · El defecte REAL, per pantalla

El criteri correcte no és *«refresca alguna cosa?»* sinó ***«refresca TOTES les superfícies que tenen aquesta dada?»***. Amb el mapa de propietat de §Q1.4, aquests són els punts on la mutació toca una dada **amb més d'un propietari** i **només s'avisa un**:

#### (a) MATEIX DEFECTE QUE Q2 — mesurats, amb la superfície òrfena identificada

| # | Pantalla · lloc | Mutació | Superfície que es queda rància |
|---:|---|---|---|
| 1 | `components/model/WorkPlan.jsx:334` | `models.openTask` | **`WorkPlan.rondes`** (pròpia, `versio` no bumpa) |
| 2 | `components/model/WorkPlan.jsx:306,309` | `modelTasks.transition` (Pause) | **`WorkPlan.rondes`** |
| 3 | `components/model/WorkPlan.jsx:396,402` | `transition` ×2 (Stop) | **`WorkPlan.rondes`** |
| 4 | `components/model/WorkPlan.jsx:528` | `modelTasks.tempsDeclarat` | **`WorkPlan.rondes`** |
| 5 | `pages/ModelSheet.jsx:1106` | `models.obrirRonda` | **`DashboardTab.data`** + **`WorkPlan.rondes`** |
| 6 | `pages/ModelSheet.jsx:525` | `models.openTask` (`tech_sheet`) | **`DashboardTab.data`** (i `RegistreActivitatTab`) |
| 7 | `pages/ModelSheet.jsx:811` | `models.openTask` (`size_check`) | **`DashboardTab.data`** |
| 8 | `pages/ModelSheet.jsx:483` | `models.openTask` (entrada genèrica) | **`DashboardTab.data`** |
| 9 | `pages/TallerPatro.jsx:336` | `models.openTask` (`pattern_digit`) | `DashboardTab.data` del mateix model |
| 10 | `pages/TallerPatro.jsx:165` | `modelTasks.transition` | idem |
| 11 | `pages/PropagatedEditor.jsx:220` | `models.openTask` (`size_check`) | idem |
| 12 | `pages/ModelSheet.jsx:409` | `fittingSessions.scheduleNow` | `FittingTab` · `FittingSessionList` (5 propietaris de `/fitting-sessions/`) |
| 13 | `pages/ModelSheet.jsx:1040` | `models.generarGrading` | 7 propietaris de `/grading-rule-sets/` |
| 14 | `pages/GeneralConfig.jsx:105,126` | `tenantConfig.update` | **`components/UnitToggle.jsx`** (unitats de tot el producte) |
| 15 | `pages/ItemAuthoring.jsx:148,164,183,196` | `garmentTypeItems.*` | 6 propietaris de `/garment-type-items/` |
| 16 | `pages/CatalegPecesItem.jsx:107` | `garmentTypeItems.update` | idem |
| 17 | `components/POMBrowser/POMBrowser.jsx:185,211` | PATCH POM | 6 propietaris de `/poms/cerca/` |
| 18 | `components/model/SessionPanel.jsx:39,74,79` | `fittingSessions.update`/`fittingPhotos.upload` | 5 propietaris de `/fitting-sessions/<id>/` |
| 19 | `components/model/measureSources.jsx:123` | `baseMeasurements.setNoms` | 6 propietaris de `/piece-fittings/<id>/` |
| 20 | `components/pattern/PatternTab.jsx:123,143` | `patterns.identificar` | `TallerPatro` sobre el mateix model |

**≈20 punts amb la forma exacta de Q2.** Els 4 primers són el cas de Salva, literalment.

#### (b) JA HO FAN BÉ (mostra representativa)

* `components/model/WorkPlan.jsx:431,540,550` — **`refrescaTot()`**: bumpa `versio` **i** crida `onRefresh`. És el patró correcte **i ja viu dins del fitxer del defecte**.
* `pages/Planning.jsx` · `pages/Dashboard.jsx` · `components/planning/ProjectGantt.jsx` — **subscrits a `plan:changed`**: es refresquen encara que qui escrigui sigui una altra pantalla. **L'únic lloc del producte amb reactivitat creuada real.**
* `components/model/WatchpointsPanel.jsx` (3 de 3), `components/POMCataleg/POMCataleg.jsx` (4 de 4), `components/MeasurementBaseGrid/` (3 de 3), `components/model/FilePicker.jsx` (3 de 3), `components/cataleg/TaulaPOMsCataleg.jsx` (2 de 2) — dada d'un sol propietari, refetch propi: **correcte i tancat**.
* `components/model/CheckMeasureEditor.jsx` — 15 de 16 punts amb refetch o `on*`. El millor fitxer del cens en volum.
* **Bucket C (6)** — navegació post-mutació: la pantalla destí es munta de zero. Correcte per construcció.

#### (c) DUBTÓS — cal el criteri de producte, no el meu

* `pages/Entrar.jsx:80,99` — login; no hi ha res a refrescar (pre-sessió). Probablement (b).
* `pages/SizeMapSetup.jsx:290,313,348` — `match`/`preview`/`gradingPreviewFile`: són **POST de càlcul, no d'escriptura**; el `setState` amb la resposta és el comportament correcte. `:466` (`sizeMap.create`) sí que és escriptura → mirar-lo amb `(a)`.
* `pages/BulkImportWizard.jsx:97,124` i `components/ImportWizard/*` — wizards amb estat de passa propi; el «després» és avançar de passa. Cal decidir si en **acabar** han d'invalidar el catàleg que acaben de moure.
* `components/DictionaryWizard.jsx:53` (`preview`) — mateix cas que els previews de SizeMap.
* `pages/TechSheetEditor.jsx` (5 punts D) — editor de llenç amb model propi; ràncies improbables però no verificades.
* `components/model/WorkPlan.jsx:360` (`claim`) — encadena `playMine`, que sí refresca. **Fals positiu del classificador; és (b).**

---

## Q4 · RECOMANACIÓ DE FORMA — el mapa, no la decisió

> **No decideixo.** Aquí hi ha les tres vies, el que costa cadascuna **mesurat en fitxers**, i el que cada una es deixa.

### Via 1 · Estendre el bus `plan:changed` a un bus de recursos

**Forma.** Generalitzar `endpoints.js:7` a `emet(recurs)` i afegir un `useInvalidacio(recurs, load)` a `utils/`. Els emissors s'estampen **una sola vegada, al mòdul d'endpoints**, com ja fa `openTask` a `:101`.

* **Fitxers tocats:** `api/endpoints.js` (1) + 1 hook nou + **els components que han de reaccionar**. Per tancar només els 20 de §Q3.3(a): **~14 fitxers**. Per cobrir els 40 només-lectors: **~40**.
* **A favor:** és **el patró que la casa ja té, ja provat i ja desplegat** — 2 emissors i 3 oients en producció. Zero dependències noves. Zero risc al `dist`. Es pot fer **per trams**, i el primer tram (WorkPlan + DashboardTab) tanca el cas de Salva amb **2 fitxers**.
* **Riscos:** un bus global sense clau fina **sobre-refresca** (cada emissió recarrega tots els oients d'aquell recurs); cal disciplina per no acabar amb 60 esdeveniments; les subscripcions són **invisibles al type-check i al lint** — un oient que s'oblidi no canta enlloc (mateixa família que la llei d'`ftt-camp-nou-de-forma-vol-getattr`).

### Via 2 · Activar React Query de debò

**Forma.** `QueryClientProvider` a `App.jsx`, `useQuery` per lectura, `useMutation` + `invalidateQueries` per escriptura.

* **Fitxers tocats:** **85 lectors + 56 escriptors = 101 fitxers distints**, més `App.jsx`. **Reescriu ~30 % del front.**
* **A favor:** resol de soca-rel la duplicació (43 endpoints amb propietari múltiple → una entrada de caché), la deduplicació de peticions i l'estat `loading`/`error`. La dependència ja és al `package.json` des del 25/05.
* **Riscos:** **és el més gran de tots.** Molts loaders porten lògica no trivial al `.then` (el patró `alive` de cancel·lació, creuaments com `tipusPerCode`, `taskListFromResponse`). Migrar-los a mitges deixa **dos règims d'estat convivint**, que és pitjor que un de dolent — i aquest repositori ja té la llei d'`ftt-lectura-que-arma-escriptures` sobre convivències. No hi ha manera de fer-ho «una pantalla per tram» sense duplicar la font durant setmanes.

### Via 3 · Pantalla a pantalla, sense mecanisme

**Forma.** A cada punt de §Q3.3(a), afegir la crida que falta (bumpar `versio`, passar un `onRefresh` més amunt, etc.).

* **Fitxers tocats:** **~14** per als 20 punts. **Per al cas de Salva: 2** — `WorkPlan.jsx` (canviar 5 `onRefresh?.()` per `refrescaTot()`) i `ModelSheet.jsx` (donar una nansa d'invalidació a `DashboardTab`).
* **A favor:** el més barat i el més verificable. `refrescaTot` **ja existeix** a `WorkPlan.jsx:248`: el canvi mínim del cas de Salva és **canviar el nom d'una funció en 5 llocs**.
* **Riscos:** **no impedeix la reincidència.** La causa d'aquest bug és que M2 va afegir una font i els gestos vells no es van reobrir; sense mecanisme, el proper tram que afegeixi una font repetirà el patró exactament igual. I `ModelSheet` → `DashboardTab` no té nansa: donar-n'hi una vol dir **un `key`/`version` més per prop-drilling**, que és el que ja va passar amb `wpVersion` (§Q2.4) — una prop que **sembla** invalidació i no ho és.

### Q4.4 · El que la mesura diu, sense decidir per ningú

| | V1 · bus | V2 · React Query | V3 · pantalla a pantalla |
|---|---|---|---|
| Fitxers (cas Salva) | 3 | ~4 + provider | **2** |
| Fitxers (els 20 de §Q3.3a) | ~14 | ~40 | ~14 |
| Fitxers (tancar-ho tot) | ~40 | **~101** | ~56 |
| Dependència nova | no | no (ja hi és) | no |
| Evita la reincidència | parcial | **sí** | **no** |
| Risc de regressió | baix | **alt** | baix |
| Precedent viu al repo | **sí** (`plan:changed`) | no | sí |

**Dues observacions que no són recomanacions:**

1. **V1 i V3 no són excloents en el temps.** El cas de Salva es tanca amb V3 en 2 fitxers; això no cremaria cap pont cap a V1, perquè V1 subscriuria les mateixes funcions `load`/`refrescaTot` que V3 deixa al seu lloc.
2. **Hi ha una quarta cosa, ortogonal a les tres, que caldria decidir igualment:** `agrupaPerRonda` (`utils/rondes.js:148`) **s'empassa en silenci** tota tasca amb `ronda_seq` desconegut. Amb qualsevol de les tres vies el bug es faria molt menys freqüent — **però seguiria sent silenciós quan passés**. Si aquesta funció caigués al bloc `orfes` en comptes de descartar, el símptoma de Salva hauria estat «la tasca surt al lloc equivocat» en comptes de «la tasca no hi és», que és **infinitament més diagnosticable**. És una decisió d'Agus, no meva.

---

## 5. LÍMITS D'AQUESTA DIAGNOSI

1. **No he reproduït el símptoma al navegador.** Diagnosi read-only: no s'ha fet login ni cap escriptura a staging. La cadena de §Q2 està traçada al codi i **verificada contra els contractes del backend** (`views_b.py:794`, `:1849`, `test_m1bis_fit4.py:95`), però **quin dels gestos va prémer Salva** no ho puc saber des del disc.
   **Per confirmar-ho en un minut i sense escriure res:** que digui si el contenidor que no apareixia era **el primer** del model (→ `perVoltes=false`, §Q2.2) o **un de nou sobre un model que ja en tenia** (→ tasca empassada per `rondes.js:148`). Les dues cauen del mateix mecanisme; el detall només afina el fum de regressió.
2. **Els buckets D i C de §Q3.1 no s'han verificat un per un** (55 punts). Els he classificats per lectura mecànica de la cadena `.then()` i he verificat a mà **només** el bucket E (6/6) i els 20 de §Q3.3(a). El classificador ja ha demostrat un fals positiu conegut (`WorkPlan.jsx:360`).
3. **`pages/TechSheetEditor.jsx` (14 punts) i els wizards d'importació queden poc auditats**: tenen model d'estat propi de llenç/passa i mereixen una passada pròpia.
4. La taula de §Q1.4 compta **propietaris estàtics** (el fitxer conté la crida). No mesura si dos propietaris estan **muntats alhora**; per a `DashboardTab`/`WorkPlan` sí que ho estan (§Q2.1), i per a la resta no s'ha comprovat.

---

## 6. ANNEX · Com reproduir cada mesura

```bash
cd /var/www/ftt-staging/frontend/src

# React Query: instal·lat, zero imports
grep -rl "@tanstack/react-query" .          # → buit
grep -rl "QueryClient\|useQuery" ../dist/assets/*.js   # → buit

# zustand: només auth + breadcrumb
grep -rl "zustand" .

# el bus que ja existeix
grep -rn "plan:changed\|planChanged" --include=*.jsx --include=*.js .

# els dos vocabularis de refresc dins de WorkPlan
grep -n "onRefresh?.()\|refrescaTot()" components/model/WorkPlan.jsx

# el creuador que descarta en silenci
sed -n '110,150p' utils/rondes.js
```

Els scripts del cens (mapa d'objectes d'`endpoints.js` → mutacions → classificació de la cadena `.then`, i el mapa de propietat per endpoint) són deterministes i es poden reconstruir des de `api/endpoints.js`; no s'ha deixat cap fitxer al repo.

---

*Diagnosi read-only. Cap fitxer de `frontend/src` s'ha modificat. Cap commit. `git status` de `frontend/` net.*
