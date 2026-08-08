# REVISIÓ D'ORIGEN DE DADES · FASE A i T0/T0-bis — 🛑 FASE 1 (read-only)

**Data:** 08/08/2026 · **Cap commit de codi.** Revisió contra la llei 1-4 d'Agus (08/08).
**HEAD revisat:** `dd77a237`

> **Veredicte curt:** la llei destapa **tres problemes de mida diferent**. El pitjor no és una
> maqueta: és que **la fitxa d'A1 pinta 9 camps que l'API no serveix** i porta així des que es
> va escriure. El segon és que **el frontend declara enumeracions de domini a 20+ llocs**, i una
> ja ha derivat de la BD. El tercer és que **només existeix UN endpoint de vocabulari**.

---

## T1 · Dades pintades → endpoint/camp real

### A1 · Catàleg de POMs (`components/POMCataleg/POMCataleg.jsx`)

Contrastat contra la resposta REAL de `GET /api/v1/poms/` (fixture de 396 POMs de `fhort`).

**Llista — tot correcte:**

| Pintat | Origen | ✓ |
|---|---|---|
| `pom_code` · `codi_client` · `name_en` · `name_cat` · `nom_client` · `abbreviation` · `categoria_nom` · `categoria` · `actiu` · `id` | `GET /api/v1/poms/` | ✅ tots servits |
| nom de categoria | `GET /api/v1/pom-categories/` → `codi`/`nom_ca`/`nom_en` | ✅ |

**Fitxa — ⚠️ SIS FILES MORTES.** La secció «Com es mesura» sencera i la «Unitat» llegeixen camps
que `GET /api/v1/poms/` **no retorna**:

| Pintat | On viu de debò | Veredicte |
|---|---|---|
| `unitat` | `POMGlobal.unitat` (`pom/models.py:39`) | ⚠️ **no és a la resposta** |
| `start_point` | `POMGlobal.start_point` (`:44`) | ⚠️ **no és a la resposta** |
| `end_point` | `POMGlobal.end_point` (`:45`) | ⚠️ **no és a la resposta** |
| `reference_point` | `POMGlobal.reference_point` (`:46`) | ⚠️ **no és a la resposta** |
| `scope` · `orientation` · `state` · `line` | `POMGlobal` (`:47-49`…) | ⚠️ **no són a la resposta** |
| `body_section` | `POMGlobal` | ⚠️ **no és a la resposta** |

**Per què.** Aquests camps són del catàleg canònic **`POMGlobal`**, no de `POMMaster` (el POM del
tenant). El serializer de `/poms/` exposa `pom_global` **només com a id**, i a més és **`null` a
74 dels 200** POMs de la primera pàgina. La pantalla fa `sel.start_point` i sempre rep `undefined`.

**Conseqüència:** aquestes sis files han mostrat **«—» sempre, des del primer dia**. Es veu a
`ops/qa/captures/a1_poms_despres.png`: UNITAT, DES D'ON, FINS ON, REFERÈNCIA, SCOPE i ZONA DEL
COS, totes buides. **Jo tenia la captura al davant i no ho vaig qüestionar** — vaig llegir els
guions com a «dades incompletes» quan eren camps inexistents.

**El que SÍ funciona de la fitxa** (`GET /api/v1/poms/{id}/us/`, verificat camp a camp):
`de_sistema` · `us.{items,families,grups,models,rules}` · `observat.{capes,instancies}` ·
`cascada` · `pot_esborrar` · `motiu`. I els àlies, de `GET /api/v1/customer-pom-aliases/?pom=`.

🔎 L'endpoint `us/` també retorna **`observat.declarat`**, que la pantalla no llegeix. És
exactament el senyal que discutíem a B1 del report d'A1 (declarat vs observat).

### T0.2 · `PageMenu` · T0.3 · breadcrumb

| Peça | Origen de dades | Veredicte |
|---|---|---|
| `PageMenu` | Cap. Etiquetes i destins arriben per props, ja traduïts | ✅ **cap literal de domini** |
| Breadcrumb | `navGroups.js` (rutes i claus `nav.*`) + `store.tenant.nom` | ✅ navegació, no domini |
| `index.css` · `buttons.js` | Tokens visuals | ✅ sense domini |

---

## T2 · Enumeracions → choices reals vs el que declara el frontend

| Enumeració | Frontend (fitxer:línia) | Backend real | Endpoint que l'exposa | Veredicte |
|---|---|---|---|---|
| **Règims de graduació** | `SizeMapSetup.jsx:21` — `['LINEAR','STEP','FIXED','ZERO']` (**4**) | `LOGICA_CHOICES` `pom/models.py:1451-1457` — LINEAR · STEP · FIXED · ZERO · **EXCEPTION** (**5**) | ❌ **CAP** | 🔴 **JA HA DERIVAT: hi falta `EXCEPTION`.** És la trampa que va disparar la llei |
| **Capes** | `utils/capaInstancia.js:38` — 6 slugs | **`MeasurementLayer`, que és una TAULA** (`pom/models.py:176`), sembrada amb slug + nom_en/ca/es + ordre | ✅ **`GET /api/v1/mesures/diccionari/` → `capes`** | 🟠 duplicat **innecessari**: l'endpoint ja el serveix, amb traduccions i ordre |
| **Instàncies** (posició/estat) | `capaInstancia.js` — mapa `NOM_INSTANCIA` | `MeasurementInstance` (taula) | ✅ mateix diccionari → `instancies`, `eixos` | 🟠 duplicat; el fitxer ho documenta com a **fallback abans que arribi el diccionari** |
| **Fases del model** | `ActionsMenu.jsx:9` · `Dashboard.jsx:35` · `PhaseStepper.jsx:5` (**tres còpies**) | `FASE_CHOICES` `models_app/models.py:99-106` | ❌ **CAP** | 🟠 en sincronia avui, però triplicat |
| **Fits · construccions · targets** | v. T3 | `FIT_CHOICES` `models_app/models.py:108`… | ❌ **CAP** | 🟠 |
| **Estats comercials** (comandes, ofertes, albarans, encàrrecs) | v. T3 | choices als models de `commerce` | ❌ **CAP** | 🟠 |

**Fet estructural:** l'ÚNIC endpoint de vocabulari de tot el backend és
`path('mesures/diccionari/', …)` (`fhort/pom/urls.py:112`), i només serveix **capes, eixos,
instàncies i regles de composició**. Per a la resta d'enumeracions **no hi ha per on llegir-les**:
complir la llei 1 exigeix exposar-les. Per ordre, això **es diu i s'espera** — no s'inventa cap
fallback al client.

---

## T3 · Literals de domini al frontend (cens)

Tots trobats amb `grep` de constants declarades. **Cap s'ha tocat.**

| Fitxer:línia | Constant | Domini |
|---|---|---|
| `pages/SizeMapSetup.jsx:21` | `LOGICA` | 🔴 règims de graduació (derivat) |
| `utils/capaInstancia.js:38` | `CAPES` | 🟠 capes (taula) |
| `utils/capaInstancia.js` | `NOM_INSTANCIA` | 🟠 instàncies (taula) |
| `components/model/ActionsMenu.jsx:9` | `PHASES` | 🟠 fases |
| `pages/Dashboard.jsx:35` | `PHASES` | 🟠 fases (2a còpia) |
| `components/PhaseStepper.jsx:5` | `FASES` | 🟠 fases (3a còpia) |
| `pages/Dashboard.jsx:36` · `pages/Models.jsx:14` | `TEMPORADES` / `SEASONS` | 🟠 temporades (2 còpies) |
| `pages/SizeMapSetup.jsx:20` | `BASE_UNITS` | 🟠 tipus d'escala |
| `pages/GeneralConfig.jsx:13-14` | `UNITS` · `NORMS` | 🟠 unitats i normes |
| `pages/Orders.jsx:18` · `pages/OrderDetail.jsx:21` | `STATUSES` | 🟠 estats de comanda (2 còpies) |
| `pages/Quotes.jsx:21` | `STATUSES` | 🟠 estats d'oferta |
| `pages/DeliveryNotes.jsx:18` | `STATUSES` | 🟠 estats d'albarà |
| `pages/WorkOrders.jsx:18-19` | `KINDS` · `STATUSES` | 🟠 encàrrecs |
| `pages/Products.jsx:145` | `NATURES` | 🟠 natures de producte |
| `pages/UsersRoles.jsx:11-13` | `CAPS` · `ROLES` | 🟠 capabilities i rols |
| `pages/FittingDetail.jsx:164` | `SEALED_ESTATS` | 🟠 estats de sessió |
| `pages/FittingPrintSheet.jsx:30` | `CASELLES` | 🟠 veredictes A/AD/RJ |
| `pages/ItemAuthoring.jsx:28` | `STEPS` | 🟠 passos |
| `pages/TechSheetEditor.jsx:53` | `TIPUS_GEOMETRIA` | 🟠 geometries |

**≈20 punts en 17 fitxers.** Cap és de codi que jo hagi escrit en aquests trams, però
`ActionsMenu.jsx` **sí que és un fitxer que vaig tocar a T0-bis.4** i porta `PHASES` exportat des
d'abans: la llei nova el converteix en veto i s'ha de dir.

---

## Estat de les preguntes que ja hi havia

- **A1/B1** (la maqueta declara «Instàncies admeses» i «Capes on té sentit»): la revisió **el
  confirma i l'endureix**. No només `POMMaster` no té els camps: la pantalla ja llegeix
  `observat.capes`/`observat.instancies` del backend, que és **exactament el que la llei mana**.
  La maqueta demana declarar el que el sistema observa.
- **A1 §4(1)** (200 de 396 POMs): segueix obert i ara es veu més greu — la paginació silenciada
  amaga 196 files.

## Cens de maquetes no implementades · A8 · A9 · A10

Fet per investigador; **les quatre afirmacions que més pesen s'han tornat a verificar a mà** i
totes quatre són exactes.

### 🔴 El titular: la casa JA havia caçat aquesta trampa, i ho va deixar escrit

`frontend/src/utils/capaInstancia.js:9-13`, literal:

> ⚠️ EL VOCABULARI ÉS D-31.22 I NO EL DE LES MAQUETES. Les maquetes aprovades diuen
> «Interlining», «Binding», «Knit» i «Reinforcement» en llocs: **són ERRONIS i no s'han copiat**.

I `maqueta_fitting_v4.html:333-334` **encara els porta**:
`{'Exterior':'Shell','Folre':'Lining','Entretela':'Interlining','Vores':'Binding','Punt':'Knit','Reforç':'Reinforcement'}`
— **4 noms falsos, 2 capes inventades (`Vores`, `Punt`), 2 capes reals absents** (`farciment`,
`fornitura`). La v4 no ha incorporat una correcció que ja era al codi.

Segon precedent, al backend: `models_app/comprovacio_views.py:12-17` es nega a inventar el
«buit declarat» de la maqueta i ho retorna com a limitació explícita
(`'limitacions': ['buit_declarat_amb_motiu']`, `:260`). **La llei 1-4 ja s'estava practicant.**

### T2 · Enumeracions (A8/A9/A10)

| Maqueta | Enumeració | Backend real | Endpoint | Veredicte |
|---|---|---|---|---|
| fitting v4 `:333` · mesures v9 `:341` | mapa de CAPES | `MeasurementLayer` (taula) | ✅ `mesures/diccionari/` | 🔴 vocabulari fals (v. dalt) |
| mesures v9 `:342` | sufixos `RE`/`EX` per als estats | els ESTATS **no componen sufix, per decisió** (`pom/models.py:265-270`) | ✅ mateix | 🔴 **inventat** |
| mesures v9 `:344`,`:304` | eix «Laterality» amb 2 valors | l'eix és **`Position`** i té **8** valors; `EIX_NOMS` existeix perquè el front no se'ls escrigui (`pom/models.py:298-306`) | ✅ mateix | 🔴 nom i cardinalitat falsos |
| mesures v9 `:343` | `COMP` parelles complementàries | cap concepte | ❌ | 🔴 **inventat** |
| mesures v9 `:360` | regla de composició del codi | ja viatja com a DADA (`regles{}`) | ✅ mateix | 🟠 duplicat |
| comprovació v3 `:254`… | `kind: Dimensió/Col·locació` | cap choices, cap camp | ❌ | 🔴 **taxonomia inventada** |
| comprovació v3 `:261-276` | instàncies `Back`, `Upper` | reals: `cb`, `top` | ✅ diccionari | 🔴 inventades |
| fitting v4 `:361-363` | `ACCEPTED/ADJUSTED/REJECTED` | `PieceFittingLine.DECISIO_CHOICES` (`fitting/models.py:427`) | ✅ | ✅ **exacte**, inclòs que `''` ≠ ACCEPTED |
| comprovació v3 (estructura) | 4 seccions + famílies + motius | `comprovacio_view` | ✅ `/models/{id}/comprovacio/` | ✅ **calca 1:1** |

### T1 · Camps que NO existeixen (A8/A9/A10)

| Maqueta | Camp | Realitat |
|---|---|---|
| fitting v4 `:322` | **`folg` = folgança com a propietat de la fila** | ⚠️ **no existeix.** `services_derivacio.py:5-7`: «no hi ha cap norma de folgança enlloc del sistema i **no se n'inventa cap**. La folgança és, sempre, la RESTA entre dues files». La maqueta la declara com a dada: és el contrari del domini |
| comprovació v3 `:263,:272` | **buit declarat amb motiu** (`gap`+`why`) | ⚠️ **no existeix**; el backend ja ho diu i ho retorna com a limitació |
| mesures v9 `:387` | `r.layer` hi desa el **nom** | el model vol el **slug** (`models_app/models.py:725`) |
| mesures v9 `:375` | `r.inst` hi desa `['Left','Relaxed']` | el model vol `'left-relaxed'` (`:749`) |
| comprovació v3 `:246` | tolerància **simètrica** `±0,6` | és **asimètrica**: `tolerancia_minus`/`tolerancia_plus` (`:648-649`) |

**Segon endpoint de vocabulari trobat per l'investigador:** `GET /api/v1/poms/cerca/?q=&model=`
serveix els nivells `item`/`type`/`cataleg` (`pom/wizard_views.py:114-230`). O sigui que en són
**dos**, no un — però cap dels dos cobreix règims, fases, fits ni estats comercials.

**No verificat:** si «Plana» (`fitting v4:242`) és un valor real de `pom.ConstructionType`.

## Cens de maquetes no implementades · A2 · A3

Fet per investigador; les tres afirmacions decisives, **reverificades a mà**.

### 🔴 `LINEAR+BREAK`: l'enumeració que va disparar l'ordre, i és pitjor que un rètol

`maqueta_grading_rules_v4.html:368` → `const REGIMS=['LINEAR','LINEAR+BREAK','STEP','FIXED']`
i `:416` el pinta com a **`<select>` editable**: no és una etiqueta, és un **control que escriu**.

- `LOGICA_CHOICES` reals (`pom/models.py:1451`): `LINEAR · STEP · FIXED · ZERO · EXCEPTION`.
- **`LINEAR+BREAK` no existeix i no pot existir.** El break és una **propietat** de la regla
  (`talla_break_label:1492`, `increment_break:1491`), no un règim. La doctrina és explícita a
  `pom/grading_regime.py`: *«El break és SAGRAT… la regla és LINEAR encara que el delta base
  sigui 0»*.
- Falten `ZERO` i `EXCEPTION`. **Desar des d'aquest select produiria un valor invàlid.**
- Dades reals de `fhort`: `LINEAR` 1034 · `FIXED` 233 · cap altre.
- El front ja el duplica **tres cops i divergents**: `SizeMapSetup.jsx:21` (4 valors),
  `GraduacioSuperficie.jsx:84` (3), `fittingGridAdapter.jsx:272`.

### 🔴 Cardinalitat falsa: multi-selecció sobre camps d'un sol valor

La maqueta de grading pinta Construcció, Fit i Grup com a **multi-selecció** (`toggle()` L430).
Al model, de `GradingRuleSet`: `targets` **sí** és M2M (`:1339`), però **`construction`
(`:1346`) i `fit_type` (`:1351`) són ForeignKey** — un sol valor — i el grup és FK (`:1301`)
o `RuleSetScopeNode`, mai un M2M. **Verificat.**

### T2 · Enumeracions (A2/A3)

| Enumeració | Maqueta | Backend | Endpoint | Veredicte |
|---|---|---|---|---|
| `REGIMS` | `LINEAR+BREAK` inclòs | 5 choices reals | ❌ CAP | 🔴 valor impossible, en un select que escriu |
| `TARGETS` | 13 valors CA hardcoded | `Target.CODI_CHOICES` (13) | ✅ `/api/v1/targets/` | 🟠 coincideixen 13/13 però **hi ha endpoint** |
| `CONSTR` | `Punt` | real: **`Teixit de punt`** | ✅ `/api/v1/construction-types/` | 🟠 duplicat + etiqueta reescrita |
| `FITS` | 10 valors EN retallats | 10 files reals | ✅ `/api/v1/fit-types/` | 🟠 3 etiquetes truncades |
| `GRUPS` | 8 etiquetes CA | `GarmentGroup` **sense cap camp de traducció**; `fhort` en té **12**, en anglès | ✅ `/api/v1/garment-groups/` | 🔴 **INVENTAT**: cap de les 8 existeix, ni la cardinalitat |
| `ESCN` | 4 tipus d'escala | codis correctes 4/4 | ❌ CAP choices | 🟠 duplicat sense font |
| `ORG` | 3 orígens | 3/3 correctes | ❌ CAP choices | 🟠 etiquetes reescrites |
| `N` (POM→nom) | 22 entrades hardcoded | — | ✅ el serializer ja porta `pom_nom*` | 🔴 **fals**: 7 dels 22 codis no són a `pom_pommaster`, i `A` real és `FRONT WIDTH LOCATION`, no `1/2 chest width` |

### T1 · Camps que NO existeixen (A2/A3)

| Maqueta | Camp | Realitat |
|---|---|---|
| size library | `sys` → badge «CANÒNIC DE LA CASA» | ⚠️ `SizeSystem` **no té `is_system`**; només derivable de `customer` buit |
| size library | `us.items` · `us.models` · `us.rules` · `us.anchor` | ⚠️ cap endpoint «on s'usa» per a runs (l'únic germà és `/poms/{id}/us/`) |
| size library | ordre de talla | ⚠️ pinta l'**índex de l'array**, no el camp `ordre` — justament el que C4 va fer únic |
| grading | `s.c` = «codi del joc» | ⚠️ el camp és `codi_sistema` (`:1365`); els valors reals són `EU_WOVEN_WOMAN_REGULAR`, no `BRW-CATALEG-v4` |
| grading | `s.brk` = **break del JOC** | 🔴 **no existeix a nivell de joc**: viu **per regla** (`:1492`), i **530 regles de `fhort` en tenen un** que no ha de ser el mateix |
| grading | columna «#» d'ordre | 🔴 `GradingRule` **no té camp `ordre`** ni `Meta.ordering` |
| grading | `nou` → «EN CONSTRUCCIÓ» | 🔴 cap camp |

### Dues contradiccions de LLEI, no de camp

1. Totes dues maquetes diuen **«Cap seleccionada = serveix a tothom»** (size lib L210/L323,
   grading L290/L445). El backend diu el contrari **per escrit**: `pom/models.py:617` («buit NO
   vol dir universal») i `serializers.py:126` («buit NO és universal, és no declarat»).
2. La maqueta de grading afirma **«Un joc no depèn de cap run»** (L222/L268). Però
   `GradingRuleSet.size_system` és FK real (`:1308`) amb **guard d'immutabilitat** quan el joc
   té regles, i **39 de 46** rulesets de `fhort` la tenen poblada — i la maqueta pinta les
   talles precisament d'aquesta FK.

### 🚩 Tres bugs de backend trobats de retruc (fora d'encàrrec)

1. **`FitType.CODI_CHOICES` (`:1575`) està ranci**: declara 5 codis i inclou `LOOSE` (0 files),
   mentre la taula en té **10**. Els choices de Django no són DDL: model i BD divergeixen en silenci.
2. `FitTypeSerializer` (`s2_serializers.py:31`) **no exposa `nom_cat`/`nom_es`** —els altres dos
   vocabularis sí—, i per això qualsevol UI catalana de fits s'ha d'inventar les etiquetes. És
   literalment el que fa la maqueta.
3. `pom_pommaster` té `codi_client` **duplicats** (`D, S, S2, J1, U1` ×2) — coherent amb el
   problema d'unicitat del catàleg que ja teníem obert.

---

## 🛑 STOP · Fase 1 tancada

No s'ha corregit res. Per a la Fase 2 caldrà decidir, com a mínim:

1. **A1 · els 9 camps morts:** ¿el serializer de `/poms/` incorpora els camps de `POMGlobal`
   (nidificats o aplanats), o la fitxa deixa de pintar «Com es mesura» fins que hi siguin? Amb
   `pom_global` null a 74 de 200, cal decidir també què es diu quan no n'hi ha.
2. **Règims:** cal exposar `LOGICA_CHOICES` per endpoint (i afegir `EXCEPTION` allà on avui falta).
3. **Capes i instàncies:** es poden arreglar **avui** llegint `mesures/diccionari/`, sense
   backend nou. ¿S'entra ara o va a la conformitat de cada pantalla?
4. **La resta d'enumeracions:** demanen endpoint de vocabulari. ¿Un de sol tipus
   `/api/v1/vocabulari/` o un per domini?
