# REPORT DE BLOC B · A5 · A6 · A7 · A8 · A9 · A10 — el camí del model

> 08/08/2026 · commits **182 → 189** (cap push) · build **desplegat** (`frontend/dist` és el que
> staging serveix) · backend **reiniciat** després de tocar el serializer.
> Les dues condicions de tancament, al §8. El que queda obert, al §7.

---

## 1 · Un resum per pantalla

### A5 · `/models` — la llista canònica (commits 182 · 183)
La graella de targetes de dues files **se'n va d'aquesta ruta**. Al seu lloc, la §8e sencera:
menú de pantalla (`←` · «Models en curs» · «Models acabats» · sep · Nou model ▾ · Accions ▾ ·
Filtres), comptador **«X/N» amb la cerca i els selects ràpids a la mateixa línia**, i una taula
amb capçaleres ordenables, amplades per contingut i `ellipsis + title`.

La §8e **no descriu la pantalla Models**: descriu *tota* llista del producte. Per això les
mecàniques viuen a **`components/ui/TaulaLlista.jsx`** (nou, compartit) i no dins de la pàgina.

**Tres coses que cal dir en veu alta:**
- **FASE passa a text pla** (el badge daurat era marca pintant una dada) i **ESTAT és el
  COMERCIAL**, que encara no existeix: la columna hi és, buida, amb el motiu escrit sota la
  taula. `Model.estat` (Nou/EnCurs/EnRevisio/Tancat) **no és aquest**, i pintar-lo hauria estat
  dir una cosa per una altra.
- **«Models acabats» no endevina cap criteri** (🚩 PROVISIONAL-DOMINI, §7).
- **Tècnic, Recurs i les tres dates de cicle deixen de tenir columna** (§8e: «Tècnic assignat
  FORA de les llistes de models»). Cens complet al §6.

### A6 · Dashboard del model (commit 184) — **només pell**
Cap component del dashboard es mou, es treu ni canvia de lògica. El que canvia és el crom:
- la banda de pestanyes amb l'activa en **daurat ple** passa a ser el **menú de pantalla**
  (`←` + 9 seccions + Watchpoints com a porta a la dreta);
- la **identitat baixa sobre el fons**, sense contenidor: codi en caption, nom a 22/500 (i com a
  `h1`: aquí la pantalla parla d'*una* entitat), badge de fase **neutre**;
- els estats buits deixen de ser caixes cremes i passen a `--text-faint` cursiva (§8c).

**EL MOLLA PASSA A QUATRE SEGMENTS AQUÍ** — `Tenant › Models › {NOM} › {Secció}`.
`/models/1319` i `/models/1319?tab=Mesures` són la **mateixa ruta** per al router: ni el nom ni
la secció es poden deduir d'allà. Els publica la pantalla (`store/molla.js`, nou) i **el segment
de GRUP els cedeix el lloc** — cinc segments no són un molla de pa, i l'ordre en nomena quatre.

### A7 · Resum + **wizard partit** (commit 185) — **el tram gros, i l'únic que no és pell**
Per canviar la talla base d'un model calia **sortir de la fitxa**, recórrer el wizard sencer i
tornar. Ara: contenidor **esquerre «Informació»** = pas 1, amb «Editar» obrint el formulari **al
mateix lloc on després es llegeix**; contenidor **dret «Definició del model»** amb els passos
**2 · Peça, 3 · Talles i 4 · Graduació com a subespais**, amb els tres estats del stepper —
**FET** (verd, eleccions **fixades i visibles** en xips d'inclusió + «Canviar» secundari) ·
**ACTUAL** (`--sel` + filet d'or, el formulari a dins, **el seu desar és l'únic blau**) ·
**BLOQUEJAT** (tènue **amb el motiu escrit**).

**CAP BACKEND NOU, i val la pena dir per què.** `PATCH /models/<id>/update-step2/` ja resol camp
a camp: `_resolve_garment_def` (views.py:720) **només escriu el que ve al payload**, i un PATCH
que no parla de graduació no toca cap regla — el predicat `canvia_joc` demana que el joc entri
al payload **i** que sigui un altre. Partir el desat no demanava endpoint nou: **demanava enviar
menys**. Verificat, no suposat: v. §4.

**Germana de presentació, no còpia.** `labelsOf`/`runCapDins`/`ordenaPelSistema` pugen a
`utils/talles.js` i **el wizard les importa d'allà** (moviment pur, cap comportament seu canvia);
el navegador de peces és el **mateix `CascadeFinder`**; l'ordenació per proximitat és el mateix
`utils/proximitatRun`. **El wizard vell ni es toca ni es trenca**: segueix sent la vàlvula
d'escapament, i la porta de graduació hi porta —al seu pas 4— perquè és allà on el canvi de joc
ja demana confirmació amb el recompte de regles al davant (D-31.4).

### A8 · Mesures (commit 186) — **només pell**
Cap gest, tecla ni atall canvia.
- **§8b-bis**: Taula · Repàs · Comprovació eren **píndoles amb l'activa en daurat ple**, al
  costat mateix del menú de pantalla — dos patrons de navegació al mateix nivell, que és
  exactament el que la norma prohibeix. Ara són **tabs de secció amb subratllat d'or**.
- **§8c**: l'estat buit («Mesures encara no disponibles») anava sobre fons crema amb filet
  discontinu deprecat i semblava un avís. Ara `--panel` + filet de la casa + frase tènue cursiva.
- **§5.4**: les quatre vies d'entrada (Editar POM · Graduació · Mesurar prenda · Propagar)
  deixen de ser **ghosts daurats** — la norma els jubila com a botó. Són **portes**.
- **§2**: dos `9px` escrits a mà pugen al terra del sistema, i una `ti-star-filled` passa a
  outline (llei de la casa).

### A9 · Fitting (commit 187) — **només pell**
**El veredicte torna a la §7.** El botó triat s'omplia del fons del semàfor i **competia amb la
xifra que havia de manar**. Ara: controls **neutres** en repòs; el triat, `--sel` + **subratllat
del color** del veredicte; i **el color ple el porta el RESULTAT** — el número, amb la seva
tinta, el seu pes i el ratllat del rebuig (que ja hi era).

**L'ajustat es parteix en dos tokens** (§1b(d)): `--warn-state` per a la marca i `--warn-ink`
per a la **tinta**. `#ff9942` com a text sobre el seu fons dona **1.86:1** — inadmissible, i
contrari al vet de C5. Corregit a les dues bandes: el botó i el número.

El subratllat va per `box-shadow` i no per `border-bottom` a posta: **la fila d'una graella no
pot saltar dos píxels cada cop que algú decideix**.

🔒 **EL PDF NO ES TOCA.** `FittingPrintSheet` és món paper, va en `pt` amb `@page`/`@media print`
i la norma de pantalla no hi aplica.

### A10 · Comprovació (commit 188) — **només pell**
**Consulta pura = zero blaus** (§8c), i verificat amb la mesura: cap `--accio` a la superfície.
Les seccions plegables i les famílies es queden **exactament** com estan (són domini). Canvia la
pell: radi de targeta 12 (el 9 no és cap dels tres radis del sistema), `th` a 10px amb tracking
.08em com a tota llista de la casa, filet intern `--line-soft`, xips a mida de caption — i el
**`▼` de la secció plegable passa a ser una icona Tabler de 16px**: un caràcter tipogràfic no té
ni la mida ni el traç del sistema.

---

## 2 · Cens dada → endpoint

### A5 · `/models`
| Què es pinta | D'on surt |
|---|---|
| Files de la llista | `GET /api/v1/models/?ordering=…&page=…&page_size=25` (+ tots els filtres de `FILTER_KEYS`) |
| Denominador del comptador («/N») | `GET /api/v1/models/?page_size=1` → `count` (el cens sencer no es dedueix d'una pàgina) |
| Ref interna · Ref client · Model · Col·lecció · Temp. | `codi_intern` · `codi_client` · `nom_prenda` · `collection` · `temporada`+`any` |
| **Entrada** | **`data_entrada`** (afegit al `ModelListSerializer` en aquest bloc) |
| Deadline | `data_objectiu` |
| Fase | `fase_actual` → `t('model_sheet.dashboard.phase.*')` |
| **Estat** | 🚩 **cap**: el Kanban comercial no existeix (§7) |
| Marques de la fila (SET · maduresa · lliurable) | `garment_set`/`piece_number` · `federacio_estat` · `lliurable_ronda_n` |
| Ordenació | `ordering` (ampliat al ViewSet; «Temp.» ordena per `any,temporada`) |
| Fases del select | `GET /api/v1/vocabulari/` → `fases_model` · comptadors: `models/fase-counts/` |
| Filtres avançats | `models/garment-counts/` + els catàlegs de `useFilterOptions()` |
| Esborrar fila | `DELETE /api/v1/models/{id}/` |

### A7 · Resum · wizard partit
| Què es pinta / es desa | D'on surt |
|---|---|
| Fitxa d'identificació | `GET /api/v1/models/{id}/` (detall) |
| **Desar el pas 1** | `PATCH /api/v1/models/{id}/` (`customer` · `codi_client` · `collection` · `nom_prenda` · `descripcio` · `data_objectiu`) |
| Estat dels 3 subespais | `garment_type_item` · (`size_system`+`size_run_model`+`base_size_label`) · `grading_rule_set` |
| Eixos triables (Target · Construcció · Fit) | `useEixos()` → `/targets/` · `/construction-types/` · `/fit-types/` |
| Navegador de peces | `CascadeFinder` → `/garment-types/` + `/garment-type-items/` |
| **Desar el pas 2** | `PATCH /models/{id}/update-step2/` amb `target` · `construction` · `garment_type_item_id` |
| Sistemes de talles (ordenats per proximitat) | `GET /api/v1/size-systems/?actiu=true` + `customers/{id}/` (el codi del client) |
| **Desar el pas 3** | `PATCH /models/{id}/update-step2/` amb `size_system_id` · `size_run` · `base_size` |
| Joc de graduació (lectura) | `GET /api/v1/grading-rule-sets/{id}/` |
| **Definir / veure graduació** | porta al pas 4 del wizard (`/models/{id}/editar?block=4`) |

**Cap enumeració de domini escrita al client.** Cap endpoint nou a tot el bloc.

---

## 3 · Verificació — les dues eines, i una tercera

| Eina | Resultat |
|---|---|
| `ops/qa/qa_auditoria_computats.py` (6 pantalles) | ✅ **0 incompliments** |
| `ops/qa/qa_bidireccional.py` (A1·A2·A3·A5·A6·A7, **49 casos mesurats**) | ✅ **0 desviacions** |
| `ops/qa/qa_a7_funcional.py` (NOU) | ✅ **13/13** — v. §4 |
| `npx eslint src` | ✅ **0 errors** |
| `node --test "src/**/*.test.js"` | ✅ **218 · 0 fallides** |

**La bidireccional torna a ZERO a TOT el producte conformat**, i no només al bloc B: les tres
desviacions que el bloc A va deixar obertes (§9e/§10.2 del seu report) estaven **decidides i no
executades a la font**. S'han executat aquí, a la maqueta, amb acta escrita al costat:

| Maqueta | Què deia | Decisió que ja hi havia |
|---|---|---|
| `maqueta_grading_rules_v4` | `.shead .t` 15px | bloc A §10.2 — **mana el token** (`--fs-h3` 14px) |
| `maqueta_grading_rules_v4` | `.tg` 11px | bloc A §9e — 11 **no és a l'escala** (10·12·14·18·22·32) |
| `maqueta_size_library_v3` | `.kv .v.buit` 12px | bloc A §9b·#2 — l'estat buit va a **10px** |

I quatre esmenes noves, del mateix tipus (**la maqueta ha de dir el que pinta**):
`NORMA_LLISTA_canonica` — la cerca, la fletxa i la paperera **no declaraven ni color ni mida** i
es quedaven amb els de l'agent d'usuari (negre, 13.33px): un valor que ningú havia decidit, i que
la comparació donava com a desviació de la pantalla quan el defecte era de la maqueta.
`PROPOSTA_resum_wizard_partit` — tres mides fora d'escala (15 · 11 · 11) i un radi de 8px que no
és cap dels tres del sistema. **Zero canvi de píxel a cap de les cinc maquetes.**

---

## 4 · La prova funcional d'A7 (el que el brief demanava, i no és una foto)

`ops/qa/qa_a7_funcional.py`, sobre `FTT-SS26-0001` (model 1319, ítem 19 amb GarmentPOMMap
ZZ-TEST), contra el servei viu. Estat de partida: peça=19 · sistema=30 · run=`XS·S·M·L·XL·XXL·3XL`
· base=`L` · joc=cap.

```
1 · EL RESUM OBERT                        ✓ els dos contenidors · ✓ el blau és del pas PENDENT
2 · «CANVIAR» AL SUBESPAI TALLES          ✓ --sel · ✓ filet d'or · ✓ «Desar talles»
                                          ✓ EL SEU DESAR ÉS L'ÚNIC BLAU de la columna
3 · CANVI DE TALLA BASE (L → XS) I DESAR
4 · PERSISTÈNCIA (API viva)               ✓ base=XS · ✓ el run intacte
                                          ✓ LA PEÇA NO S'HA MOGUT · ✓ LA GRADUACIÓ TAMPOC
5 · REOBRIR                               ✓ xip «XS · base» en --ok-bg/--ok · ✓ torna «Canviar»
                                          ✓ el blau ha tornat al pas pendent
6 · RESTAURACIÓ                           ✓ la talla base torna a ser L
──────── 0 comprovacions fallides ────────
```

El punt 4 és el que fa segur partir el desat: **un PATCH de talles no toca ni la peça ni el joc**,
i per tant els tres subespais poden desar sols sense que cap trepitgi els altres.

---

## 5 · Conducta afegida i decisions de pell (per si les vols vetar)

1. **`ui/Badge` canvia per a tot el producte** (21 fitxers el munten). La §1 no admet excepcions:
   fons suau + tinta + **vora fina**, píndola sempre. `gold` deixa de pintar dades amb el color
   del logo (passa a la forma «de la casa»: `--sel` + `--gold-border`) i `warn` es parteix segons
   la §1b(d). Mateix cas que el `GroupPills` del bloc A.
2. **La secundària de la casa** passa a `padding 8×16` i pes 500 (§5.2) — abans 7×14 i pes 600,
   que és el pes d'un primari. Afecta `ActionsMenu` i la fitxa del model.
3. **Deshabilitat al menú**: la §5.7 diu «baixa el fons, no la tinta», però **a la barra blanca
   no hi ha fons que baixar** — donar-li `--bg-page` el deixa a un pas de `--sel`, que allà vol
   dir el contrari (píndola activa). Al menú mana la §1: `--text-faint` és «només deshabilitat».
4. **Les marques condicionals de la fila** (SET · maduresa · lliurable) van **dins de la cel·la
   del nom**, no en columnes pròpies: la graella canònica no els en dona, i una columna per a una
   marca que gairebé cap fila porta seria una columna buida.
5. **El nom del model és un `h1`** a la fitxa (i **no** a la llista, §8e). Aquí la pantalla parla
   d'una entitat; allà, de moltes.
6. **La llista de sistemes del pas 3 té `maxHeight` amb scroll**: hi són tots (D-31.3 «ordena,
   mai amaga»), i desplaçar-se no és ocultar — però vint runs no es poden menjar la pàgina.
7. **Dos blaus a la vegada al Resum** quan la definició és incompleta: «Editar» (esquerra) i el
   pas pendent (dreta). És la §8f literal —«passos paral·lels d'un mateix camí en contenidors
   separats poden portar un blau per pas pendent»— i l'ordre del brief («blau segons estat del
   conjunt»). Dins de la columna dreta **mai n'hi ha dos**: està mesurat al §4.
8. **`_resolve_garment_def` no es toca.** El desat partit funciona perquè el backend ja resolia
   camp a camp; l'única cosa que canvia és què s'hi envia.

---

## 6 · Cens del que deixa d'estar muntat (res esborrat)

| Què | On era | On és ara |
|---|---|---|
| `TabSummary` (graella de camps + **panell de VIABILITAT** + bloc de **TEIXIT**) | tab Resum | **exportat** a `ModelSheet.jsx`, sense muntar. 🚩 §7 |
| `RuleSetCard` | tab Resum | fitxer intacte; la graduació és el **subespai 4** |
| Columnes **Tècnic · Recurs · Entrada prod. · Arribada proto · Fitting prev.** | llista de models | fitxa del model i Planificació (§8e ho mana) |
| Badge **«amb comanda / directe»** (`has_order`) | llista de models | 🚩 sense superfície pròpia (§7) |
| `TabSummary`, `sizesAmbDades` | — | el *setter* es conserva: `reloadTaula` l'escriu |

---

## 7 · Pendents anotats

### 🚩 PROVISIONAL-DOMINI · «Models acabats»
El criteri de «model acabat» **no existeix**: l'estat comercial el mana el Kanban i el Kanban no
hi és. La vista **no endevina res** — no demana res al backend i ho diu escrit a la pantalla.
Inventar-hi un criteri (fase `TOP`? `estat='Tancat'`? `data_tancament`?) hauria estat prendre una
decisió de domini dins d'un tram de pell, **i hauria amputat la llista de «en curs»** sense que
ningú ho hagués decidit. Les tres opcions són al codi, escrites, esperant.

### 🚩 PROVISIONAL-DOMINI · la columna **ESTAT**
Mateixa causa. La columna hi és amb «—» i el motiu escrit sota la taula. **`Model.estat` no és
aquest estat**: és l'intern (Nou/EnCurs/EnRevisio/Tancat) i els seus valors no són els que la
§8e nomena (Començat neutre · En curs taronja · Acabat verd).

### 🚩 On van la **VIABILITAT** i el **TEIXIT**
La maqueta del wizard partit no els cobreix, i deixar-los al Resum hauria duplicat l'editor
d'identitat que la §8f acaba de posar a la columna esquerra. `TabSummary` queda **exportat i
sencer**: tornar-lo a muntar on es decideixi és una línia. El teixit, a més, ja té pantalla
pròpia (`/models/:id/teixit`).

### 🚩 `has_order` sense superfície
El badge «amb comanda / directe» era a **totes** les files i la graella canònica no li dona
columna. No és filtrable per URL. **Anotat, no resolt.**

### 🚩 A9 · `FittingDetail` conserva el seu `EditorHeader`
No hi entra el `PageMenu` del §8b: aquesta pantalla és una **superfície d'editor a pantalla
completa** i la seva capçalera és **compartida amb l'editor de check**. Substituir-la és tocar
estructura de dues pantalles, i A9 és **només pell**. Anotat per al tram que unifiqui els dos
editors.

### 🚩 A8 · el **stepper de flux** de Mesures
La §6 vol la seqüència `POM → Graduació → Mesurar prenda → Propagar` com a **contenidors amb
estat**. Les quatre accions ja hi són **en aquest ordre exacte** (ratificat per Agus el 06/08) i
ara parlen el llenguatge de porta. **El que no s'ha fet és assignar-los estats FET/ACTUAL**,
perquè la §6 diu explícitament que **«la seqüència exacta de cada superfície és DOMINI (Montse),
no estil»** i que el contingut de cada flux **es valida abans de construir**. Derivar «Mesurar
prenda: fet» de les dades hauria estat inventar domini. La forma entra quan els estats es validin.

### ⚠️ El crom del sistema
Segueixen els **3 colors fora de paleta** de la top bar i el menú lateral (`#e4e4e2`, `#e8e8e8`,
`#e0d5c5`) que el bloc A ja va anotar. §8b: el menú lateral no es toca i la top bar està pendent
de foto pròpia. **I un de nou**: el `<main>` de `Shell.jsx` pinta el fons de pàgina amb
`--gray-l` (#f0f0f0) i la §1 diu `--bg-page` (#fbfaf8). És **una línia**, però és el fons de
**totes** les pantalles alhora —també les que encara no han passat conformitat—, i la política
del §1b és progressiva. **Decisió d'Agus.**

---

## 8 · Les dues condicions de tancament

### (1) A5..A10 amb build desplegat — ✅
`npm run build` fet; `frontend/dist` és el que staging serveix. Backend **reiniciat** (es va
tocar `ModelListSerializer`: sense reinici el `gunicorn` hauria seguit servint el codi vell —
llei d'infra). `npx eslint src` → **0 errors**. Auditoria de computats a les 6 pantalles →
**0 incompliments**. Bidireccional → **0 desviacions**.

### (2) La suite — ⏳ **v. la nota**
S'ha tocat **`ModelListSerializer`** (un camp read-only afegit) i **`ordering_fields`** del
ViewSet, o sigui que la condició aplica. La correguda de tancament és
`python manage.py test fhort.pom fhort.models_app fhort.fitting` (la **mateixa selecció d'apps**
que el bloc A, per poder comparar el número). `node --test` → **218 · 0 fallides**.

> ⚠️ **Sobre `--keepdb`**: una correguda amb `--keepdb` va donar 73 errors i **cap era real** —
> tots eren `UniqueViolation` sobre `tenants_client.schema_name='test'`, deixat per una correguda
> anterior interrompuda. Amb BD fresca desapareixen. **Anotat perquè no torni a espantar ningú.**

---

## 9 · Captures (contra el servei VIU, un estat per captura · `ops/qa/captures/`)

| Tram | Captures |
|---|---|
| A5 | `a5_01_llista` · `a5_02_ordenada` · `a5_03_cerca_buit` · `a5_04_acabats` · `a5_05_nou_model` · `a5_06_filtres` |
| A5 (tenant `los`, **51 models**) | `a5los_01…06` — la graella **plena**, que és on es veuen l'ellipsis i l'ordenació de debò |
| A6 | `a6_01_dashboard` · `a6_02_molla_4_segments` · `a6_03_accions` |
| A7 | `a7_01_resum` · `a7_02_info_editant` · `a7_03_talles_obert` · `a7_04_peca_obert` |
| A7 · funcional | `a7_f1_talles_actual` · `a7_f2_talles_fet_nou` |
| A8 · A10 | `a8_01_mesures` · `a10_01_comprovacio` · `a10_02_repas` |

⚠️ **Les icones surten buides a les captures i no és un defecte de la pantalla**: Tabler entra per
webfont des d'un CDN i l'arnès intercepta `**/*`. Al navegador de debò hi són.

### 🛑 LÍMIT DECLARAT d'A8 · A9 · A10 — i és més ample del que el brief preveia
El brief ja avisava que aquests tres es validarien «amb poques dades». La realitat del banc:

- **`FTT-SS26-0001` no té cap mesura**, i el tab Mesures s'atura al seu **gate** («Mesures encara
  no disponibles»). La taula de mesures, el carril, les instàncies en verd i el panell de
  Comprovació **no són assolibles** amb les dades vives d'aquest model.
- **No hi ha CAP sessió de fitting a cap dels dos tenants** (`fhort` i `los`, comptat per API):
  la pantalla d'A9 **no es pot fotografiar**.

**Què SÍ que està verificat en aquests tres trams:** els **estats buits** (que era el criteri de
validació que el brief demanava), la migració de tokens mesurada amb **0 incompliments**, el
build i el lint verds, i els 218 tests de node. **Què NO:** la pell de la graella plena, dels
veredictes pintats i de les seccions de Comprovació amb dades — que és exactament l'exercici
ple que arribarà amb models reals. **No està amagat: està dit.**

---

## 10 · Els fitxers nous d'aquest bloc

| Fitxer | Què és |
|---|---|
| `frontend/src/components/ui/TaulaLlista.jsx` | **la graella de llista de la casa** (§8e), per a qualsevol llista del producte |
| `frontend/src/components/model/ResumWizardPartit.jsx` | el Resum amb el wizard partit (§8f) |
| `frontend/src/store/molla.js` | la cua del molla de pa (el 3r i 4t segment) |
| `frontend/src/utils/talles.js` | les tres funcions pures del run, compartides amb el wizard |
| `ops/qa/qa_blocb_captures.py` | un sol arnès per als sis trams |
| `ops/qa/qa_a7_funcional.py` | la prova funcional del wizard partit |
