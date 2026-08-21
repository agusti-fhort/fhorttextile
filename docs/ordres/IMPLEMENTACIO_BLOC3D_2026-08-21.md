# IMPLEMENTACIÓ · BLOC 3+D — gating de presa · pickers de joc · UI · alta de POM

> **Data:** 2026-08-21 · **Patró B** · staging `/var/www/ftt-staging`, branca `dev`
> **Substrat:** `docs/ordres/DIAGNOSI_BUGS_PROD_837_2026-08-21.md` §B · §C · §G · §D
> **7 commits locals. CAP PUSH.** El model sembrat `TRV-SS27-0001` (1383) no s'ha tocat:
> tota la seva QA és de LECTURA i cap `ModelGradingRule` s'ha modificat.
> `pom/services.py` i `TechSheetEditor.jsx` no s'han obert.

---

## RESUM EN SET LÍNIES

1. **B tancat, i sense la decisió que la diagnosi donava per bloquejant.** §B.5 deixava el fix
   aturat esperant l'Agus («d'on surt `valor_teoric` si no hi ha `GradedSpec`?»). La resposta ja
   estava construïda: `reconcilia_linies` cau a la talla base tot sol. Cap migració.
2. **C tancat, i amb una excepció que va aparèixer MESURANT, no llegint**: el 1383 és de TRV i
   porta un joc de BRW. Sense `?inclou=`, el sedàs de client li hauria amagat el seu propi joc.
3. **G tancat, G5 inclòs** — i G5 anava a DUES superfícies, no a una.
4. **D tancat, però NO on deia el cens**: `POMBrowser` **ja no té ruta** des d'U1 (07/08).
5. Tres defectes trobats pel camí i tancats: el 500 del duplicat de POM per caixa, el segell
   sobre una versió buida, i l'acta falsa de `POMs.jsx`.
6. **QA per HTTP real feta**, els dos costats de cada guard, més 8 captures de pantalla.
7. **Bancs nous: 39 proves** (11 B + 18 C + 10 D), totes verdes, més les 12 d'E1 com a control.

---

## COMMITS

| # | Hash | Tram | Fitxers |
|---|---|---|---|
| 1 | `1e5449c7` | **B** backend | `fitting/services.py` · `fitting/test_s45_b_presa_sense_propagat.py` |
| 2 | `308b7506` | **B** frontend | `utils/motiuPasPresa.js` · `.test.js` · `pages/ModelSheet.jsx` |
| 3 | `b0066c3c` | **G** (G1·G2·G3·G4·G5) | `grading/GraduacioSuperficie.jsx` · `EditableTable/EditableTable.jsx` · `model/MeasureGrid.jsx` · `model/measureSources.jsx` · `pages/FittingDetail.jsx` · `docs/diagnosis/CENS_PODA_PLATAFORMA.md` |
| 4 | `7bbe27c3` | **C** backend | `pom/views.py` · `pom/test_s45_c_sedas_jocs.py` |
| 5 | `94e9d478` | **C** frontend | `grading/RuleSetPicker.jsx` · `index.css` · `grading/GraduacioContenidor.jsx` · `grading/GraduacioPanel.jsx` · `model/ResumWizardPartit.jsx` · `pages/ItemAuthoring.jsx` · `pages/ModelWizard.jsx` · `grading/JocsDeRegles.jsx` · `pages/CustomerDetail.jsx` |
| 6 | `de4dbc77` | **D** | `pom/wizard_views.py` · `pom/test_s45_d_alta_pom_cataleg.py` · `POMCataleg/POMCataleg.jsx` · `i18n/{ca,en,es}.json` |
| 7 | `bc9f81aa` | QA | `ops/qa/qa_s45_captures.py` |

Porta del verd a cada commit: `manage.py check` net · `npm run build` net · `npx eslint` **0
errors**. `git add` de paths explícits sempre; cap `-A`, cap commit sense pathspec.

---

<a id="b"></a>
## TRAM B — GATING «MESURAR PRENDA»

### El que la diagnosi donava per bloquejant, i per què no ho era

§B.5 posava **«Decisió d'Agus. Bloquejant»** a la primera fila: *«D'on surt `valor_teoric` d'una
línia si no hi ha `GradedSpec`? Avui la línia **és** una còpia de l'spec. Cap opció és neutra.»*
I §B.4 sentenciava: *«Sense `GradedSpec` no hi ha línies i no hi ha on anotar. Aquesta és la
dependència estructural, no un `if` que es pugui afluixar.»*

🚨 **És fals, i el terreny ho desmenteix sol.** `reconcilia_linies`
([fitting/services.py:640-660](../../backend/fhort/fitting/services.py#L640)) ja sap néixer sense
spec, i ho diu amb aquestes paraules:

> *«El teòric d'una mesura nova: l'spec de la versió activa si n'hi ha (llavors la línia neix
> amb totes les seves talles, com les seves germanes) i, si no, **la base del model a la talla
> base** — que és l'única talla que la presa i el full pinten.»*

L'opció (a) de §B.5 —«línies només de talla base des de `BaseMeasurement`»— **ja estava
construïda**, i `create_piece_fitting` la crida tres línies després del guard que estudiàvem.
La decisió que semblava pendent ja s'havia pres el 06/08, al tram Q3.

### El guard es parteix per CAMÍ (llei S43), i queden dos

| Camí | Predicat ABANS | Predicat ARA | On |
|---|---|---|---|
| **Propagar** | `_te_regles(model)` → 400 | **igual, cap canvi** | `models_app/views.py:3013-3015` |
| **Mesurar prenda** (backend) | `GradingVersion` activa → `ValueError` | materialitza una versió BUIDA | `fitting/services.py:503` |
| **Mesurar prenda** (front, pas ③) | `te_taula` (= propagat) | `te_mesures` | `utils/motiuPasPresa.js` |
| **Mesurar set** (Escalat) | `te_taula` | **`te_taula`, cap canvi** | `motiuPasMesurarSet` |

**Per què la versió es materialitza i no es fa nul·lable el FK:**
`PieceFitting.grading_version` és NOT NULL ([fitting/models.py:395](../../backend/fhort/fitting/models.py#L395))
i hi pengen `consolidate_base_from_fitting:685` i `close_piece_fitting:765`. El contenidor buit
els deixa vius **sense migració i sense tocar-ne cap**, i és el mateix camí lliure que aquesta
funció ja fa amb el `SizeFitting` vint línies amunt.

**⚠️ El SET no es relaxa, i és deliberat.** E3b havia agermanat les dues portes («la MATEIXA
dependència que el ③») i era cert mentre totes dues esperaven la taula. El full de presa del set
ÉS la corba propagada: `desa_presa_escalat` busca la línia de (POM, talla) i alça
`PresaSenseLiniaError` si no hi és ([fitting/services.py:135-138](../../backend/fhort/fitting/services.py#L135)).
Sense `GradedSpec` només existeix la talla base. Compartir el predicat, ara, seria obrir una
graella on no es pot anotar res.

### 🚨 Un forat que s'obria amb el fix, i s'ha tancat al mateix commit

Amb versions buides fàcils d'existir, `seal_model_grading` n'hauria pogut segellar una. El dany
no és cosmètic: `bump_grading_version_and_generate` refusa amb el guard D-1 si l'activa està
aprovada ([pom/services.py:1091-1095](../../backend/fhort/pom/services.py#L1091)) → **un segell
sobre el buit BLOQUEJARIA la primera propagació de debò** d'aquell model. Ara una versió sense
cap `GradedSpec` activa no es segella i torna `None`, que és el senyal que el cridador ja sap
llegir (`tasks/services_d.py:61`): avançar de fase segueix funcionant.

### QA per HTTP real — model **1378 (BANC-27)**, sense cap `GradingVersion`

Estat de partida: `te_mesures: true` · `te_regles: false` · `te_taula: false` · `version_number: null`.

```
COSTAT TANCAT · POST /api/v1/models/1378/generar-grading/
  → [HTTP 400] {"error":"El model no té regles de grading (ni residents ni de rule set)"}

COSTAT OBERT  · POST /api/v1/fitting-sessions/160/create-piece/  {"model_id":1378}
  → [HTTP 201]  n_linies: 22 · grading_version: 130 (v1)
     talles de les línies: ['S']          ← NOMÉS la base, tretes de BaseMeasurement
     A/S/50.0 · B/S/45.5 · D/S/49.0 · E2/S/34.5

⚠️ I OBRIR LA PRESA NO ÉS PROPAGAR — GET grading-status/ després:
     te_taula: false · te_propagacio: false · segellada: false · version_number: 1

I PROPAGAR SEGUEIX TANCAT amb la versió buida ja creada:
  → [HTTP 400] mateix error   ← el guard està partit de debò, no desplaçat
```

**Abans del canvi, la segona crida era un 400.** Els dos costats exercitats per HTTP, com
demanava l'ordre.

**Banc:** `fitting/test_s45_b_presa_sense_propagat.py` — 11 proves. Vermell previ documentat al
docstring. Regressió: `fhort.fitting` + `fhort.tasks` sencers, **453 proves**.

---

<a id="c"></a>
## TRAM C — ELS QUATRE PICKERS DE JOC

### Backend: un sedàs, quatre paràmetres i una excepció

`GradingRuleSetViewSet.get_queryset` ([pom/views.py:253](../../backend/fhort/pom/views.py#L253)).
El sedàs es construeix com **una sola `Q`** i no com una cadena de `.filter()`, perquè al final
s'hi ha d'aplicar una excepció: un cop has filtrat, el que has tret ja no torna.

| Paràmetre | Què fa |
|---|---|
| *(defecte)* | `actiu=True`. **JUBILAR ≠ AMAGAR** |
| `?include_inactive=1` | els torna. El demanen Gestió de jocs i la fitxa de client |
| `?actiu=<x>` | **EXPLÍCIT, mana sobre el defecte** — si no, `?actiu=false` tornaria sempre buit |
| `?per_client=<id\|cap>` | els del client **MÉS** els de catàleg. A PROD, el que treu els 24 jocs LOS |
| `?per_size_system=<id>` | el del model **MÉS** els que no en declaren cap (el NULL és COMODÍ) |
| `?inclou=<id[,id…]>` | **travessa el sedàs sencer** — v. sota |

### 🚨 `?inclou=` — l'excepció que va aparèixer MESURANT, no llegint

Provant el sedàs contra staging amb el model del brief:

```
GET grading-rule-sets/?amb_regles=1&per_client=13        → count 0   []
GET grading-rule-sets/?amb_regles=1&per_client=13&inclou=219 → count 1 [(219,'BRW')]
```

El model **1383 (TRV-SS27-0001) és del client TRV (13) i té assignat el joc 219, que és de
BRW**. Amb el sedàs de client, el picker s'obria **buit** —«No hi ha cap RuleSet per a aquesta
combinació»— sobre un model que en porta un de posat. Ni a la llista, ni ressaltat, ni enlloc:
la pantalla deia que el model no té joc quan en té un.

És la mateixa llei que `include_inactive` girada a l'altre eix: **el que està EN ÚS no s'amaga
mai.** Un joc d'un altre client pot ser una anomalia a corregir —o una decisió deliberada—, però
mentre hi sigui s'ha de veure: amagar-lo no el desassigna, només fa que ningú el pugui canviar.
El banc ho fixa amb el cas del jubilat en ús i el de l'esquelet en ús, pel mateix argument.

### Frontend: el sostre viu al component, no a les quatre pantalles

`RuleSetPicker.jsx:96` guanya `maxHeight: var(--llista-tria-max-h)` + `overflowY: auto` + filet i
radi. **El toc arriba als quatre pickers de cop**, que és el que l'ordre demanava («mateixa
solució als 4 — cap picker amb comportament propi»).

Token nou a `index.css`: **`--llista-tria-max-h: 420px`**, de ROL i no de pantalla. Cap px màgic
fora de token. El sostre **no contradiu la llei C5** («ordena i no amaga»): el que s'acota és el
CONTENIDOR, no el conjunt — desplaçar-se no és ocultar (D-31.3).

**Cap dels quatre pickers tenia cercador** (comprovat un per un), o sigui que no n'hi havia cap
de conservar.

Params per punt:

| Punt | `per_client` | `per_size_system` | `inclou` |
|---|---|---|---|
| Graduació del model | `model.customer` | — | `gradingRuleSetId` |
| Resum partit | `model.customer` | — | `model.grading_rule_set` |
| Wizard, pas 4 | `customerId` (prop nova) | `sizing.size_system_id` | `gradingRuleSetId` |
| Autoria d'ítem | — *(no hi ha model)* | — | — *(el joc arriba després)* |

### QA per HTTP real i visual

Magnitud a staging: **1 sol `GradingRuleSet`** (219, BRW, actiu) — la neteja de `fhort` el va
deixar així. Els 51/18/24 de la diagnosi són **de PROD**, i aquí no es poden reproduir; per això
el banc en construeix un fixture de la mateixa forma (actius · jubilats · d'altri · esquelets).

```
?page_size=200                                  → 1 · actius 1 · jubilats 0
?include_inactive=1                             → 1
?include_inactive=1&actiu=false                 → 0     ← l'explícit mana
?per_client=cap                                 → 0     ← l'únic joc té client
?per_client=13 (TRV)                            → 0
?per_client=13&inclou=219                       → 1     ← el que està en ús hi torna
?per_client=7  (BRW)                            → 1
?inclou=patata                                  → 1     ← param brossa: s'ignora, no peta
```

**Captura:** `ops/qa/captures/s45/c_picker_jocs.png` — «Canviar» de Graduació al 1383, llista
d'**una** targeta (el joc assignat, amb el seu filet d'or i «✓ Usar aquest joc»), scroll
contingut. **NO s'ha canviat el joc.**

**Banc:** `pom/test_s45_c_sedas_jocs.py` — 18 proves.

---

<a id="g"></a>
## TRAM G — UI DE GRADUACIÓ I MESURES

Tot amb tokens CSS (llei G8). **Cap hex nou, cap px màgic.**

### G1 · El pes de la columna de talla base

`GraduacioSuperficie` pintava `--gold-pale` a la capçalera i a la cel·la; la taula germana
(`EditableTable`) porta `--sel`. El propi comentari del codi ja deia *«(`--sel` acotat pels dos
costats)»* mentre pintava una altra cosa: la Graduació havia pujat un graó pel seu compte.

**No és una tria d'aquest sprint: el sistema ja ho tenia escrit.** Vint línies avall, la
capçalera del carril d'`EditableTable` diu literalment *«`--gold-pale` està ELIMINAT del sistema
(§1)»*. Graduació torna a `--sel`.

### G2 · CRITERI TRIAT (documentat, com demanava l'ordre)

> **Tot valor numèric va CENTRAT i amb `fontVariantNumeric: tabular-nums`**, a les tres taules
> de la superfície de mesures. Els INPUTS hi van al pas.

Hi havia **tres respostes per a la mateixa pregunta** —`center` a Mesures, `right` a Graduació,
`right` a `MeasureGrid`— i les tres taules es miren de costat. El que fa que una columna de
xifres es pugui escombrar amunt i avall és `tabular-nums` (amplada fixa del dígit), que es queda
a tot arreu; **la vora on s'arrambin** és la part que ha de ser igual, i ara ho és.

Els inputs van al pas per una raó concreta: amb l'input a la dreta i la cel·la centrada, **la
xifra SALTAVA en clicar-hi** — la mateixa dada no pot canviar de lloc segons si es mira o es toca.

Cobert: `EditableTable` (base vigent · columnes de regla · el número de dins del carril) ·
`GraduacioSuperficie` (talla base · Δ · Δ break · inputs) · `MeasureGrid` (cel·la de valor ·
input · subcapçalera).

**⚠️ Això supera una acta.** «CODA · retoc 1» deixava el número de dins del carril a la dreta a
posta. L'ordre d'Agus de «valors centrats» és posterior i mana; **si no era la intenció, es
reverteix amb una línia** (`EditableTable.jsx`, `CarrilInput` → `textAlign`).

**Divergència que NO s'ha tocat** (no és numèrica, i l'ordre parlava de numèrics): la columna de
NOM va `right` a `EditableTable:860` i `left` a `MeasureGrid:562`. Anotada com a deute.

### G3 · La columna «Ve de», retirada

Deia «del joc» / «del model» per fila: una etiqueta que **no canvia cap decisió** —la regla es
toca igual vingui d'on vingui— i que es menjava 90px. Retirada per PRESENTACIÓ.

- `regla_origen` i `regla_es_resident` **es queden al payload** (`models_app/views.py:2163-2164`):
  són additius i tenen altres lectors potencials. Retirar-los seria un segon tram.
- El `const delJoc` cau amb ella (`no-unused-vars` és **error** en aquest repo) i **el que aquell
  càlcul sabia queda escrit al seu lloc**, comentat: mentia si es mirava `regla_origen` tot sol.
- **i18n: NO s'ha podat en calent.** Les 3 claus × 3 idiomes s'anoten al cens G8
  (`docs/diagnosis/CENS_PODA_PLATAFORMA.md`, addenda S45/G3) amb l'avís de no confondre-les amb
  les seves **homònimes VIVES** `grading.jocs.col_origen` i `comprovacio.col_origen`.

**ⓘ Troballa que contradiu §G.3:** avisava de revisar `AMPLADES` perquè *«la taula és
`width:100%` amb totes les columnes fixades menys `#`»*. **Ja no ho és** — Q2 la va passar a
amplada de contingut dins d'un `overflowX:auto`, i el comentari d'allà ho documenta. Treure una
columna només l'estreny; no cal repartir res.

### G4 · Taula de Mesures — color més suau

`--sel` (#f7f5f2) ja era el fons de la columna base, i **per sota no hi ha cap token**: el que
cridava massa era **la banda de dimensions**, l'únic `--gold-pale` que quedava a la taula
(`EditableTable.jsx:843`), més fort que el carril de la talla base, que és on va l'ull. Baixa a
`--sel`; la lletra es queda en `--gold`, perquè el que la banda ha de dir és QUÈ agrupa i això
ho diu la tinta.

**Estrenar un token per sota de `--sel` és decisió de disseny i no s'ha fet** —§G.4 ho advertia—:
la interpretació triada resol «més suau» sense estrenar-ne cap i queda alineada amb G1 i amb la
norma §1. **Si el que volies era una altra cosa, és una línia.**

### G5 · La columna RÈGIM surt de la graella de fitting

**Va a DUES superfícies, no a una**, i això només es va veure obrint-la de debò:
`/fittings/:id` **redirigeix** a la superfície Mesures per a tota sessió VIVA des de la
dissolució de l'Sprint Y ([FittingDetail.jsx:629](../../frontend/src/pages/FittingDetail.jsx#L629));
a `FittingDetail` hi queden només les **segellades**. Les dues han perdut la columna:

- `model/measureSources.jsx` — `fittingSource.buildLeadCols()` → `[]` (sessió VIVA)
- `pages/FittingDetail.jsx` — `leadCols` fora (sessió SEGELLADA)

Hi anava en **read-only** (3r argument de `regimeLeadCol` a `true`: *«en mode sessió els deltes
s'editen a Escalat, no en presa»*), o sigui una columna de 118px que ocupava **carril sticky**, no
es podia tocar, i deia una dada que ja té dues cases pròpies.

**NOMÉS en aquest mode:** `escalatRuleLeadCols` (Escalat) i les columnes de regla d'`EditableTable`
(Mesures) **no es toquen** — allà la columna ÉS la feina. `regimeLeadCol` es queda sencer i
exportat. Cap lògica canviada.

Cauen amb ella `onRegimChange` i `regimErr` de `FittingDetail`, que n'eren els únics consumidors.
`regimErr` **ja era mig mort**: es desava (`const [, setRegimErr]`) i no es pintava enlloc, o sigui
que l'avís «discret» era, de fet, un silenci. `POST set-pom-regim` **segueix viu**: el criden
Mesures i Escalat.

### QA visual — 8 captures a `ops/qa/captures/s45/`

| Fitxer | Què mesura |
|---|---|
| `g1g2g3_graduacio.png` | base en `--sel`, valors centrats, **cap columna «Ve de»** |
| `g2g4_mesures.png` | Mesures en consulta, valors centrats |
| `g5_fitting_viva.png` | sessió viva del 1383 — **cap columna RÈGIM** |
| `g5_fitting_segellada.png` | sessió segellada (155) — **cap columna RÈGIM** |
| `g5_escalat.png` | **control**: Escalat manté RÈGIM · Δ · Δ BREAK · TALLA BREAK |
| `c_picker_jocs.png` | picker curt amb el joc assignat |
| `d_cataleg_poms.png` · `d_form_nou_pom.png` | catàleg + formulari d'alta |

Banc read-only i reexecutable: `ops/qa/qa_s45_captures.py`. Zero errors de pàgina a les 8.

**🚩 Sense «abans».** Staging serveix `frontend/dist` i `npm run build` **és** desplegar; el build
calia per passar la porta del verd, i `git stash` està prohibit. Decidit contigo: només «després»,
amb el diff de codi com a testimoni del canvi. La banda de dimensions de G4 tampoc surt a cap
captura: només es pinta en mode EDICIÓ (`!readOnly`), i entrar-hi és un gest que escriu.

---

<a id="d"></a>
## TRAM D — CREAR POM AL CATÀLEG

### 🚨 El cens apuntava a una pantalla morta

§D.2 deia: *«Només falta la UI del POMBrowser»*. **El `POMBrowser` ja no té ruta.** U1
(2026-08-07) li va treure la pestanya i `/poms` renderitza `POMCataleg`
([pages/POMs.jsx:9](../../frontend/src/pages/POMs.jsx#L9)).

L'acta d'aquell fitxer encara diu *«el `POMBrowser` NO s'esborra ni es toca: el consumeixen 5
pantalles més (TechSheetEditor, POMPicker de patrons, POMCatalogue, TargetLabel)»* — i és
**FALS**. Del seu `export default` **no en queda cap importador**; l'únic `import` que el toca
n'agafa dos exports amb nom (`PomNamePair`, `POMDetailPanel`) cap a `POMCatalogue`. És el mateix
patró que el cens ja havia detectat amb `ItemAuthoring`: pantalla substituïda, acta no
actualitzada.

Posar-hi el botó hauria estat **enviar-lo a una pantalla que ningú obre**. Va al catàleg VIU.
El primer intent (fet a `POMBrowser` seguint el cens al peu de la lletra) s'ha revertit sencer.

### El backend ja hi era, i tenia un 500 amagat

Es fa servir la porta 2 del cens, `POST /api/v1/poms/crear-tenant/`, que és la feta per a això i
que **no la cridava ningú** (`endpoints.js:254`, zero cridadors). Cap règim de permisos nou:
`IsAuthenticated`, el mateix que editar un POM pel ViewSet.

🚨 **DEFECTE TROBAT EN OBRIR-LA:** el guard de duplicats mirava `filter(codi_client=code)`
—**exacte**— i la constraint de la BD és **CASE-INSENSITIVE**
(`uniq_pommaster_codi_client_ci`, [pom/models.py:421](../../backend/fhort/pom/models.py#L421)).
Amb «CF» al catàleg, crear «cf» passava el guard, petava contra la constraint, queia a
l'`except Exception` de sota i sortia com un **500 amb el text cru del driver**. Un guard que no
mira el que mira la BD no és un guard: és un 500 amb passos previs. Ara és `__iexact` → 400 net.

### El POM neix SOL

`actiu=True` · `pom_global=None` (catàleg de tenant; el pont amb els 290 canònics de `public` és
de backoffice) · `origen_import='cataleg'` per traça · **cap `CustomerPOMAlias`, cap
`GarmentPOMMap`, cap sembra**. Vincular-lo a una peça és el flux ASSIGN existent, i són dos
gestos a posta.

**`pendent_revisio=False`**, a diferència de la porta del model: aquella el posa a `True` perquè
*«l'ha creat un tècnic amb un model al davant, no el responsable del catàleg»*. Aquí qui el crea
**és** a la pantalla del catàleg.

### El formulari, i els tres camps que l'ordre demanava i no existeixen

L'ordre deia «categoria, nomenclatura, capes, instàncies, unitat». **§D.3 del mateix substrat les
desmenteix**, i el model també:

| Camp | Hi és? |
|---|---|
| **nomenclatura** (`codi_client`) | ✅ obligatori, únic insensible a la caixa |
| **nom** (`nom_client`) | ✅ obligatori |
| **categoria** | ✅ **opcional** al model (319 de 645 POMs de `fhort` la tenen a NULL). S'ofereix perquè és el que fa TROBABLE el POM en una pantalla que agrupa per categoria |
| **capes · instàncies** | ❌ **el POM no en porta.** Viatgen amb la MESURA (`BaseMeasurement.capa/instancia/garment`, unicitat de 5 camps): el mateix «CF» és el del folre i el de l'exterior alhora |
| **unitat** | ❌ no és un camp de `POMMaster`; ve del `POMGlobal`, i un POM de tenant no en té |

Demanar-les en néixer hauria estat inventar un eix que el domini no té i que després ningú
llegiria. **Les toleràncies** tampoc hi surten: neixen a 0.6 i es copien a la mesura en abocar-la.

i18n **ca/en/es** complet sota `poms.cat.*`, claus en anglès, paritat verificada als tres fitxers.

### QA per HTTP real i visual

```
POST poms/crear-tenant/ {"codi_client":"ZZS45D","nom_client":"Mesura de prova S45/D"}
  → 201 {"id":1051,"codi_client":"ZZS45D",…}
POST … mateix codi                          → 400 «Ja existeix un POM amb codi ZZS45D»
POST … "zzs45d"  (abans: 500 del driver)    → 400 «Ja existeix un POM amb codi zzs45d»
POST … nom buit                             → 400 «codi_client i nom_client són obligatoris»

GET poms/1051/     → actiu:True · pom_global:None · pendent_revisio:False · origen_import:'cataleg'
GET poms/1051/us/  → items 0 · families 0 · grups 0 · models 0 · rules 0
                     «Sense cap ús: es pot esborrar.»      ← NO apareix a cap model
```

**Captura:** `d_form_nou_pom.png` — el formulari obert al catàleg viu (144 POMs), amb la fitxa
sencera a la dreta intacta.

**Banc:** `pom/test_s45_d_alta_pom_cataleg.py` — 10 proves, tres de les quals fixen que el POM
neix **sol** (si algú «millora» la porta afegint-hi l'àlies per comoditat, es posa vermell).

---

## TROBALLES QUE CONTRADIUEN LA DIAGNOSI

| # | On deia | Què és realment |
|---|---|---|
| 1 | §B.4 · *«Sense `GradedSpec` no hi ha línies i no hi ha on anotar. Dependència estructural»* | **Fals.** `reconcilia_linies:640-660` cau a la talla base. L'opció (a) de §B.5 ja estava construïda des de Q3 (06/08) |
| 2 | §B.5 · *«Decisió d'Agus. Bloquejant»* | **No calia cap decisió de domini ni cap migració.** El FK no s'ha tocat |
| 3 | §D.2 · *«Només falta la UI del POMBrowser»* | **`POMBrowser` no té ruta des d'U1 (07/08).** `/poms` → `POMCataleg` |
| 4 | `POMs.jsx:6` · *«el consumeixen 5 pantalles més»* | **Acta falsa.** Zero importadors del `export default` |
| 5 | §G.3 · *«la taula és `width:100%`… cal revisar `AMPLADES`»* | **Ja no ho és**: Q2 la va passar a amplada de contingut. Res a repartir |
| 6 | §C.2 · Graduació *«ORDENA pel client del model»* | **Inert al llistat**: `customer_codi` no surt del serializer de llista (sí del detall). El sedàs de servidor ho supera |
| 7 | §C.3 · 51 targetes · 18 jubilats · 24 LOS | **Són de PROD.** A staging `fhort` hi ha **1 sol** `GradingRuleSet`. El símptoma no es pot reproduir aquí; per això el banc en fa el fixture |
| 8 | (nou) | El **1383 és de TRV i porta un joc de BRW** — el cas que va obrir `?inclou=` |

---

## DEUTES NOUS I COSES QUE HAS DE SABER

### 🚩 Pendents

1. **`ops/qa/captures/` és `.gitignore`.** Les 8 captures viuen al servidor i no entren a git.
2. **Alineació de la columna de NOM**: `right` a `EditableTable:860` vs `left` a
   `MeasureGrid:562`. No és numèrica i l'ordre parlava de numèrics; queda oberta.
3. **3 claus i18n òrfenes** de G3, anotades al cens G8 i **no podades**. La poda va amb el lot
   de les 89 que el cens ja porta.
4. **`--llista-tria-max-h: 420px`** és un valor triat per raonament (targetes de tres línies), no
   mesurat contra una maqueta. Si el disseny en té un altre, és una línia d'`index.css`.
5. **G2 supera «CODA · retoc 1»** (v. §G2). Reversible amb una línia si no era la intenció.
6. **G5 a `POMBrowser`**: no aplica — la pantalla no té ruta. Si algun dia se li'n dona una,
   hereta el `RuleSetPicker` però no el G5.

### ⚠️ Escriptures que ha fet aquesta sessió a staging

Cap al model sembrat 1383 ni a cap `ModelGradingRule`. Les que sí:

| Què | On | Per què |
|---|---|---|
| `POMMaster` **1051** (`ZZS45D`) | catàleg `fhort` | QA de D, com autoritzava l'ordre. 0 usos: es pot esborrar |
| `FittingSession` **160** (Programada) + peça amb 22 línies | model **1378 BANC-27** | QA de B per HTTP real. Model de banc, no de producció |
| `GradingVersion` **130** (buida, v1) | model 1378 | conseqüència del camí lliure; és el que la QA havia de mesurar |
| Tasca de mesures del 1383 | — | ⚠️ La captura de G5 va entrar a `/fittings/159`, que **redirigeix** a `?fitting_session=159` i **materialitza la tasca en muntar**. No s'hi va teclejar res ni s'hi va prémer cap botó, però la visita no és neutra. Consta |
| `frontend/dist` | staging | `npm run build` **és** desplegar en aquesta màquina |

### ⓘ Un fitxer que ha entrat a git sense ser meu

`docs/diagnosis/CENS_PODA_PLATAFORMA.md` (17/08) era **untracked**. L'addenda de G3 hi va, i
`CLAUDE.md` diu que les diagnosis SÍ es commiten (arrel = vigents), o sigui que el commit `b0066c3c`
l'ha portat sencer a git. **Si el vols en un commit propi, es parteix.**

### 🔒 Mètode — dues coses que han costat temps

1. **El gunicorn serveix el codi de quan va arrencar.** `?inclou=` va donar `count 0` per HTTP
   amb el codi bo al disc: hi faltava un `systemctl restart ftt-staging`. La llei ja hi era;
   torna a passar.
2. **Emetre un JWT de QA està bloquejat pel classificador de permisos** d'aquesta sessió (dos
   intents). El token el vas haver de passar tu. Si vols que futures sessions facin la QA
   visual soles, cal una regla de permís de Bash per a l'script d'emissió.
3. **Un `goto` directe a `https://staging…` amb Playwright torna el 401 d'nginx** (`auth_basic`)
   i la captura surt en blanc. El patró bo —bundle del disc + proxy de l'API a `127.0.0.1:8001`
   amb el Host del tenant— queda escrit al capdamunt de `ops/qa/qa_s45_captures.py`.

---

## PORTA DEL VERD

```
manage.py check                          System check identified no issues (0 silenced)
npm run build                            ✓ built
npx eslint (tots els fitxers tocats)     0 errors
node --test motiuPasPresa.test.js        10/10
manage.py test  s45_b + s45_c + s45_d + e1_guard_partit   49/49  OK
manage.py test  fhort.fitting fhort.tasks                 453 proves (regressió de B)
```

**Cap push.** Els 7 commits són locals a `dev`.
