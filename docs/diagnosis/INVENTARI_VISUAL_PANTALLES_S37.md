# DIAGNOSI — Inventari visual de totes les pantalles

Data: 2026-08-07 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

**Abast:** fotografiar les divergències visuals entre les pantalles vives perquè l'Agus
pugui dictar la norma de layout. **Es CONSTATA, no es recomana**: aquest document no diu
quina versió és la bona, i no conté cap proposta de fix ni cap línia de codi.

**Convenció:** cada afirmació porta `fitxer:línia` (relatiu a `frontend/src/`).
**«NO EXISTEIX» = confirmat absent al codi**, no especulat.

---

## 0 · Cens de pantalles — la llista tancada

El router declara **58 rutes** (`App.jsx:295-425`). D'aquestes, la llista tancada
d'aquest inventari són les **31 pantalles de servei arribables sense paràmetre**:

`/` · `/models` · `/models/nou` · `/fitxa-tecnica` · `/fittings` · `/task-types` ·
`/garment-types` · `/cataleg-peces` · `/suppliers` · `/recursos` · `/encarrecs` ·
`/clients` · `/comercial/productes` · `/comercial/ofertes` ·
`/comercial/condicions-pagament` · `/comercial/comandes` · `/comercial/encarrecs` ·
`/comercial/orfes` · `/comercial/albarans` · `/planificacio` · `/planificacio/calendari` ·
`/temps` · `/poms` · `/poms/grading` · `/size-library` · `/disseny/documents` ·
`/configuracio/general` · `/configuracio/usuaris` · `/configuracio/calendari` ·
`/perfil` · `/onboarding`

**Excloses i per què:** les 27 restants són pantalles de detall amb `:id`
(`models/:id`, `clients/:id`, `comercial/*/:id`…), rutes fora del Shell
(`/login`, `/entrar`, `/reset-password/:uid/:token`, la fitxa, el `.ftt`, el taller de
patró, el fitting a pantalla completa) i redireccions (`MesuresRedirect`,
`SizeCheckRedirect`, `models/nou-des-de-fitxer`, `*`).

---

## 1 · Resum executiu

1. **NO EXISTEIX cap contenidor de pàgina compartit ni cap capçalera de pàgina
   compartida.** `ui/Contenidor.jsx` existeix però és un **plegable de panell lateral**
   amb capçalera fosca (`Contenidor.jsx:43-48`) i **cap de les 31 pantalles el
   consumeix** (només `TallerPatro.jsx:16` i `TechSheetEditor.jsx:17`, tots dos fora del
   Shell). **31/31 pantalles es pinten el seu `<h1>` inline.**
2. **El `<main>` del Shell ja aplica `padding: '1.5rem'`** (`Shell.jsx:36`) a totes les
   rutes de dins. **7 pantalles n'hi afegeixen un de propi a sobre** → el marge real que
   es veu és el doble en unes i simple en altres (§4).
3. **Hi ha QUATRE `primaryBtn` diferents amb el mateix nom**, i un té el **cos oposat**:
   `OrphanedWorkOrders.jsx:18` és `{...actBtn, borderColor:'var(--gold)', color:'var(--gold)'}`
   — un **ghost**, no un botó ple. Els altres tres: `ui/buttons.js:14` (el compartit),
   `ModelWizard.jsx:942` (funció, to `--warn`) i `GradingRuleSets.jsx:967` (`btnPrimary`).
4. **Només 11 de 31 pantalles consumeixen el `primaryBtn` compartit.** 5 el copien
   inline, 3 el redeclaren, 3 tenen un primari que no és daurat i 9 no en tenen.
5. **~110 colors literals vius** a les 31 pantalles, i el **73% es concentra en 4
   fitxers**: `GradingRuleSets` (46), `PlanningCalendar` (17), `OnboardingWizard` (17),
   `UsersRoles` (13). **21 pantalles en tenen zero.**
6. **12 pantalles declaren una factoria de chip/badge LOCAL** quan `ui/Badge.jsx` (7
   consumidors) i `grading/wizardUI.jsx` `Chip` ja existeixen. Sis d'aquestes factories
   són **el mateix cos literal**.
7. **La mesura confirma 10 eixos divergents**, i els dos extrems són clars: el **botó
   secundari té 12 `padding` distints en 15 pantalles** i el **badge empata 6px contra
   999px de radi (7 i 7)**. En canvi el **botó primari surt uniforme a 16/16** i el
   `<main>` a 31/31.
8. 🔶 **La pantalla de referència (`/models`) és MINORITÀRIA en 3 dels 10 eixos
   divergents** —títol 18px quan 19 pantalles fan 22px, radi de targeta 8px quan 22 en
   fan 12, i padding propi de 24px quan 24 pantalles no en posen— **i única en un quart**
   (radi de badge de 5px). Dada, no judici.
9. **Les llistes es capçalen de dues maneres incompatibles** segons si la pantalla fa
   servir `<table>` o `<div>`: `th` a **10px MAJÚSCULES** (13 pantalles) contra pseudo-
   capçalera a **12px caixa baixa** (5, entre elles `/models`). §3.5.

---

## 2 · La pantalla de REFERÈNCIA — `/models`

L'Agus la cita com a patró de mides. Els seus valors, per tenir-los a mà en llegir la
taula mestra:

| Propietat | Valor | Font |
|---|---|---|
| Contenidor | `padding:'24px'` · `maxWidth:1240` · `margin:'0 auto'` | `Models.jsx:230` |
| Títol de pàgina | `--fs-h2` (18px) · pes **500** · MONO | `Models.jsx:234` |
| Files | **NO és `<table>`**: columna flex de targetes | `Models.jsx:340` |
| Badge de fase | `--fs-body` (12px) · pes 600 · radi 12 | `Models.jsx:569` |
| Botó primari | daurat **inline**, sense importar `ui/buttons` | `Models.jsx:371-375` |
| 🚩 Colors literals | **4** (2 `rgba`, i `#C0392B`+`#FADBD8` al `delBtn`) | `Models.jsx:363,556,570` |

> ⚠️ **La referència NO consumeix el botó compartit** i té el seu propi `faseBadge`,
> `SetBadge()` i `delBtn`. Dada, no judici.

---

## 3 · BLOC A — Taula mestra de valors mesurats al navegador

**31/31 pantalles mesurades, 0 fallides.** Valors computats reals (`getComputedStyle`)
sobre el bundle `dist/` servit des de disc, viewport idèntic 1500×1000 @2×, idioma `ca`.

**Dades en brut** (la taula completa de **97 propietats × 31 pantalles** no cap aquí):
[`captures-inventari-visual-s37/taula_mestra.tsv`](captures-inventari-visual-s37/taula_mestra.tsv)
· [`inventari_mesures.json`](captures-inventari-visual-s37/inventari_mesures.json) (inclou
el selector usat per a cada fila) · 31 captures senceres al mateix directori.

> ⚠️ **Fidelitat de les captures:** les fonts venen de CDN i estaven bloquejades, o sigui
> que **les imatges dibuixen amb el fallback del sistema**. **Cap valor mesurat en depèn**
> (`fontFamily` reporta la família DECLARADA i `lineHeight` és del CSS construït), però
> el TIPUS de lletra de les captures no és el de producció. Les icones Tabler **sí** que
> són fidels (servides des de disc). El contingut és stubejat: 5 files per llista.

Format: **valor → nre. de pantalles**. La columna de referència `/models` va marcada 🔶.

### 3.1 · Tipografia

| Propietat | Valors mesurats | `/models` 🔶 |
|---|---|---|
| **Títol de pàgina** · `fontSize` | **22px ×19** · **18px ×11** · 16px ×1 (`/disseny/documents`) | **18px** — 🔶 **la MINORIA** |
| Títol · `fontWeight` | 500 ×29 · 600 ×1 (`/poms`) · 400 ×1 (`/disseny/documents`) | 500 |
| Títol · `fontFamily` | MONO **×31** (uniforme) | MONO |
| Títol · `color` | `rgb(29,29,27)` ×30 · daurat ×1 (`/onboarding`) | `rgb(29,29,27)` |
| **Subtítol** · `fontSize` | **12px ×29** · 10px ×1 (`/poms`) · 16px ×1 (`/onboarding`) | 12px |
| Subtítol · `color` | gris `rgb(134,134,133)` ×30 · negre ×1 (`/onboarding`) | gris |
| **Capçalera de SECCIÓ** (`h2`/`h3`) | **NO EXISTEIX ×28** · 14px/500 ×2 · 18px/500 ×1 (`/perfil`) | NO EXISTEIX |
| **Capçalera de PANELL** · `fontSize` | **10px ×14** · 12px ×7 · NO EXISTEIX ×7 · 16px ×1 · 14px ×1 · 22px ×1 | 10px |
| Capçalera de panell · `letterSpacing` | 1px ×10 · normal ×8 · 0.48px ×2 · 0.4px ×2 · 0.72px ×1 · 0.5px ×1 | 1px |
| **Capçalera de TAULA** (`th`) | existeix a **13/31** · `fontSize` **10px ×13** · uppercase ×13 · `color` gris ×13 | sense `<table>` |
| `th` · `fontWeight` | 400 ×11 · **600 ×2** (`/comercial/productes`, `/configuracio/usuaris`) | — |
| **Cel·la** (`td`) · `fontSize` | 12px ×13 (uniforme) · MONO ×13 · pes 400 ×12, 300 ×1 (`/fittings`) | — |
| **Etiqueta petita** (mínim de la pàgina) | 10px ×21 · **8px ×8** · 12px ×2 | 8px |

### 3.2 · Espaiat

| Propietat | Valors mesurats | `/models` 🔶 |
|---|---|---|
| `<main>` del Shell | `padding 24px` i fons `rgb(240,240,240)` a **31/31** (uniforme) | 24px |
| **Arrel de pàgina** (padding PROPI, a sobre del `<main>`) | **0px ×24** · 24px ×4 · 32px 16px ×1 · 32px 24px ×1 · 40px ×1 | **24px** → 🔶 **48px efectius** |
| **`th` · `padding`** | **11.2px 16px ×11** · 6px 10px ×1 (`/comercial/productes`) · 8px ×1 (`/configuracio/usuaris`) | — |
| **`td` · `padding`** | **12px 16px ×11** · 7px 10px ×1 · 8px 12px ×1 | — |
| **Separació entre panells** (`gap`) | 🚩 **10 valors distints en 14 pantalles**: 16px ×3 · 24px ×2 · 13px ×2 · `normal` ×2 · 8 · 26 · 19.2 · 12 · 22.4px ×1 c/u · NO EXISTEIX ×17 | — |
| Targeta · `padding` | 0px ×22 · 20px ×2 · 12px 16px ×1 · 19.2px 22.4px ×1 · 24px ×1 | 0px |

### 3.3 · Superfícies

| Propietat | Valors mesurats | `/models` 🔶 |
|---|---|---|
| Targeta · `background` | blanc ×26 · `rgb(250,250,250)` ×1 (`/poms`) · NO EXISTEIX ×4 | blanc |
| **Targeta · `border`** | 🚩 **3 vores distintes**: `1px solid rgb(240,240,240)` **×20** · `rgb(224,213,197)` ×4 (`/`, `/fitxa-tecnica`, `/comercial/productes`, `/poms`) · `rgb(228,228,226)` ×3 (`/fittings`, `/temps`, `/perfil`) | `rgb(240,240,240)` |
| **Targeta · `borderRadius`** | **12px ×22** · **8px ×3** (`/`, `/models`, `/fitxa-tecnica`) · 9px ×2 (`/cataleg-peces`, `/poms`) | **8px** — 🔶 **la MINORIA** |
| Targeta · `boxShadow` | **`none` a 27/27** — cap ombra a cap pantalla | none |
| Fons d'arrel de pàgina | transparent ×31 (uniforme) | transparent |

### 3.4 · Components

| Propietat | Valors mesurats | `/models` 🔶 |
|---|---|---|
| **Botó primari** (fons `--gold`) | present a **16/31** · `background`, `color` i `fontSize` **uniformes a 16/16** ✅ | present |
| Primari · `padding` | **7px 14px ×12** · 6px 14px ×1 · 6px 16px ×1 · 8px 18px ×1 · 10px 16px ×1 | 7px 14px |
| Primari · `borderRadius` | 6px ×14 · 5px ×1 (`/fitxa-tecnica`) · 8px ×1 (`/perfil`) | 6px |
| **Botó secundari** · `padding` | 🚩 **12 valors distints en 15 pantalles** | — |
| Secundari · `background` | blanc ×11 · `rgb(245,230,208)` ×3 · `rgb(245,240,232)` ×1 | — |
| Secundari · `borderRadius` | 6px ×8 · 8px ×3 · 0px ×2 · 4px ×2 | — |
| **Badge/chip · `borderRadius`** | 🚩 **6px ×7 vs 999px ×7** — **empat exacte** · 10px ×1 · 5px ×1 · NO EXISTEIX ×15 | **5px** (únic) |
| Badge · `fontSize` | 12px ×8 · 10px ×6 · 8px ×2 (`/models`, `/poms`) | 8px |
| Input/select · `padding` | 6px 10px ×10 + **5 valors únics** | 6px 10px |
| **Icones `-filled`** | **0 a 31/31** ✅ compleix la llei outline-only | 0 |
| Densitat d'icones | `/configuracio/usuaris` 46 · `/comercial/productes` 21 · `/models` 10 … **0 icones a 9 pantalles** | 10 |

### 3.5 · La divergència que la mesura destapa i el codi no deia

**Les llistes es capçalen de dues maneres incompatibles:**

| | Nre. | `fontSize` | `textTransform` |
|---|:-:|---|---|
| Amb `<table>` → `th` | **13** | **10px** | **uppercase** |
| Pseudo-taula sense `<table>` (`/models`, `/models/nou`, `/fittings`, `/planificacio`, `/poms`) | **5** | **12px** | **cap** |

O sigui que **la mateixa funció —dir què és cada columna— es pinta a 10px en majúscules
o a 12px en caixa baixa segons si la pantalla fa servir `<table>` o `<div>`.**

---

### 3.6 · Resum de les divergències, ordenades per dispersió

| # | Propietat | Valors | Majoritari | On és `/models` 🔶 |
|:-:|---|:-:|---|---|
| 1 | Botó secundari · `padding` | **12** en 15 pantalles | 7px 14px (×3) | — |
| 2 | Separació entre panells (`gap`) | **10** en 14 pantalles | 16px (×3) | — |
| 3 | Input/select · `padding` | **6** | 6px 10px (×10) | majoritari |
| 4 | Capçalera de panell · `fontSize` | **6** | 10px (×14) | majoritari |
| 5 | Arrel de pàgina · `padding` | **5** | 0px (×24) | **minoria** (24px) |
| 6 | Primari · `padding` | **5** | 7px 14px (×12) | majoritari |
| 7 | Badge · `borderRadius` | **4** | 🚩 **empat** 6px/999px (×7 i ×7) | **únic** (5px) |
| 8 | Targeta · `borderRadius` | **3** | 12px (×22) | **minoria** (8px) |
| 9 | Targeta · `border` | **3** | `rgb(240,240,240)` (×20) | majoritari |
| 10 | Títol de pàgina · `fontSize` | **3** | 22px (×19) | **minoria** (18px) |
| — | Botó primari (fons/tinta/mida) | **1** | uniforme a 16/16 ✅ | majoritari |
| — | `<main>` (padding i fons) | **1** | uniforme a 31/31 ✅ | majoritari |
| — | Icones `-filled` | **0** | cap ✅ | — |

🔶 **La pantalla de referència és MINORITÀRIA en 3 dels 10 eixos divergents** (mida de
títol, radi de targeta, padding d'arrel) i **única** en un quart (radi de badge). **Dada,
no judici.**

---

## 4 · BLOC B — Cens estàtic: d'on ve cada peça

### 4.1 · Eix CONTENIDOR de pàgina (31 pantalles)

| Variant | N | Pantalles |
|---|:-:|---|
| **`{minWidth:0, maxWidth:<n>}` sense padding propi** (viu del `1.5rem` del Shell) | **19** | TaskTypes, GarmentTypes, CatalegPeces, Suppliers, Recursos, Encarrecs, Customers, Products, Quotes, PaymentTerms, Orders, WorkOrders, OrphanedWorkOrders, DeliveryNotes, Planning, PlanningCalendar, GeneralConfig, UsersRoles, CompanyCalendar |
| `padding` + `maxWidth` + `margin:'0 auto'` (**padding PROPI sobre el del Shell**) | 5 | Dashboard `:450` · Models `:230` · ModelWizard `:527` · SizeLibrary `:48` · OnboardingWizard `:54` |
| `padding` + `maxWidth`, sense `margin` | 2 | TechSheetEntry `:71` · DissenyPlaceholder `:9` |
| `<div>` **nu**, cap propietat | 2 | FittingSessionList `:275` · TimeTracking `:92` |
| `maxWidth` sol, sense padding | 1 | UserProfilePage `:70` |
| `padding:'0'` + `fontFamily` propi | 1 | GradingRuleSets `:182` |
| Delegat al component fill | 1 | POMs → `POMCataleg.jsx:18` |
| **Via `ui/Contenidor.jsx`** | **0** | — |

**MAJORITÀRIA: 19/31.** Però dins d'aquest grup el `maxWidth` pren **9 valors distints**:
`560`, `720`, `900` (×2), `1000` (×8), `1100`, `1240`, `1520`, `1600`, `'100%'` (×4).

🚩 **Doble padding.** `Shell.jsx:36` ja dona `1.5rem` (24px). Les 7 pantalles amb padding
propi (Dashboard +24, Models +24, SizeLibrary +24, OnboardingWizard +40, ModelWizard
+2rem/1rem, TechSheetEntry +1.5rem, DissenyPlaceholder +32/24) **es veuran amb ~40-64px
de marge**; les altres 24, amb 24px.

### 4.2 · Eix BOTÓ PRIMARI (31 pantalles)

| Variant | N | Pantalles |
|---|:-:|---|
| **`primaryBtn` de `ui/buttons.js`** | **11** | GarmentTypes, Suppliers, Recursos, Encarrecs, Customers, Products, Quotes, PaymentTerms, DeliveryNotes, Planning, GeneralConfig |
| Cap primari a la pantalla | 9 | TaskTypes, CatalegPeces, Orders, WorkOrders, PlanningCalendar, TimeTracking, POMs, SizeLibrary, DissenyPlaceholder |
| Daurat **inline**, sense import | 5 | Models `:371` · Dashboard `:481` (és un `<span>`) · UsersRoles `:188,341,415,557,693` · CompanyCalendar `:218` · UserProfilePage `:124,160` |
| **Redeclarat amb el mateix nom** | 3 | ModelWizard `:942` · OrphanedWorkOrders `:18` · GradingRuleSets `:967` |
| Primari **no daurat** | 3 | FittingSessionList `--charcoal` `:285` · OnboardingWizard `#f5e6d0` outline `:93,122,170` · TechSheetEntry white/gold outline `:98` |

🚩 **Els quatre `primaryBtn` homònims** (verificats un per un):

| Font | Forma | Cos |
|---|---|---|
| `ui/buttons.js:14` | objecte exportat | **ple daurat** + `--text-main` |
| `ModelWizard.jsx:942` | **funció** `(disabled) => ({…})` | ple `--warn` + blanc |
| `GradingRuleSets.jsx:967` | objecte (`btnPrimary`) | ple daurat, `padding`/`radius` propis |
| `OrphanedWorkOrders.jsx:18` | objecte | 🚩 **GHOST** — `{...actBtn, borderColor:gold, color:gold}`: **cos oposat al del mateix nom** |

### 4.3 · Eix TAULA (31 pantalles)

| Variant | N | Pantalles |
|---|:-:|---|
| **`ui/Table.jsx`** | **10** | TaskTypes, Suppliers, Recursos, Customers, Quotes, PaymentTerms, Orders, WorkOrders, OrphanedWorkOrders, DeliveryNotes |
| Cap taula | 11 | ModelWizard, TechSheetEntry, Encarrecs, PlanningCalendar, TimeTracking, SizeLibrary, DissenyPlaceholder, GeneralConfig, CompanyCalendar, UserProfilePage, OnboardingWizard |
| **grid de `<div>`** | 5 | Dashboard, **Models**, GarmentTypes, CatalegPeces, POMs |
| 🚩 **`<table>` a pèl** | 4 | FittingSessionList `:338` · Planning `:292,358,421` · GradingRuleSets `:458` · UsersRoles `:225` |
| `commercial/LineTable.jsx` | 1 | Products `:131` |
| `EditableTable` | **0** | **NO EXISTEIX** a cap de les 31 |

**MAJORITÀRIA entre les 20 que en tenen: 10 = `ui/Table.jsx`.**
🚩 Hi ha **DUES taules compartides** amb `th`/`td` divergents: `ui/Table.jsx:24-31,50-54`
i `commercial/LineTable.jsx:16-17`.
🚩 **`FittingSessionList.jsx:50-56` és `ui/Table.jsx:24-31` i `:50-54` copiats** — mateixos
valors, mateix ordre de propietats.

### 4.4 · Eix CAPÇALERA de pàgina

**NO EXISTEIX cap component compartit. 31/31 es pinten el seu `<h1>` inline.**

| Variant | N |
|---|:-:|
| `<h1>` amb `--fs-h1` (22px) | 19 |
| `<h1>` amb `--fs-h2` (18px) | 11 |
| `<h1>` amb `--fs-title` | 1 (DissenyPlaceholder `:10`, únic ús) |
| amb `fontFamily: MONO` | 20 |
| **sense MONO** | 11 (Dashboard, TechSheetEntry, FittingSessionList, TimeTracking, GradingRuleSets, UsersRoles, UserProfilePage, SizeLibrary, DissenyPlaceholder, OnboardingWizard, POMCataleg) |

**El patró dominant existeix i és idèntic byte a byte a 12 pantalles** de llistat
comercial/catàleg: `<div flex space-between><div><h1><p subtítol></div>{primari}</div>`
— p.ex. `Quotes.jsx:97-107`, `Customers.jsx:172-182`, `GarmentTypes.jsx:160-168`,
`Products.jsx:109-118`. **La referència `/models` NO segueix aquest patró** (usa `--fs-h2`
i el botó inline).

### 4.5 · Eix CHIPS / BADGES

| Variant | N |
|---|:-:|
| 🚩 **Factoria/const LOCAL** | **12** — Models (×3), TaskTypes, Suppliers, Recursos, Encarrecs, Customers (×2), PaymentTerms, Planning, PlanningCalendar (×2), TimeTracking, GradingRuleSets, ModelWizard (×2 inline) |
| Cap chip/badge | 11 |
| `ui/Badge.jsx` | 7 — FittingSessionList, Products, Quotes, Orders, WorkOrders, OrphanedWorkOrders, DeliveryNotes |
| `grading/wizardUI.jsx` `Chip` | 1 — ModelWizard |
| `GroupPills` | 1 — GarmentTypes |
| `RunRestrictionTags` | **0 · NO EXISTEIX a cap de les 31** |

🚩 Les factories de `TaskTypes:38`, `Suppliers:75`, `Recursos:79`, `Customers:140` i
`PaymentTerms:81` són **el mateix cos literal**:
`fontSize:'var(--fs-label)', fontWeight:600, padding:'2px 8px', borderRadius:999, fontFamily:MONO`.

🚩 **Dos `Pill` amb contractes oposats:** `GradingRuleSets.jsx:672` `Pill({bg,color})`
**exigeix** que cada crida li passi el color (i les 4 crides li passen hex crus:
`:434,439,441,444`); `PlanningCalendar.jsx:440` `Pill` només rep `active` i resol per token.

### 4.6 · Eix ICONOGRAFIA

- ✅ **`ti-*-filled`: 0 coincidències** a les 31. La llei de `CLAUDE.md` es compleix.
- 🚩 **8 pantalles fan servir glifs de text com a icona**: ModelWizard (`✕ 🔒 ★ ← →`),
  Models (`✓ × ← →`), OnboardingWizard (`✓ ○ ✗ ⬆ →` — **i cap `ti-`**), GradingRuleSets
  (`▾ ▸ ×`), SizeLibrary (`×`), Planning (`⠿`), CompanyCalendar (`→`), Dashboard (`→`).
- **8 pantalles amb 0 icones `ti-`**: ModelWizard, CatalegPeces, TaskTypes, Orders,
  WorkOrders, SizeLibrary, OnboardingWizard, POMCataleg.
- L'únic **emoji** del cens: `🔒` a `ModelWizard.jsx:551`.

---

## 5 · 🚩 Colors no-token, per pantalla

| Pantalla | 🚩 | Nota |
|---|:-:|---|
| **GradingRuleSets** | **46** | tota la taula de regles i el `Pill` local |
| **PlanningCalendar** | **17** | 3 constants de paleta `:25-27` + 14 al CSS injectat |
| **OnboardingWizard** | **17** | `#f5e6d0` ×5 (**és `--gold-pale`**), `#c8b89a` sense token |
| **UsersRoles** | **13** | 11 vius + 2 en comentari |
| **SizeLibrary** | **7** | banner ok/err + `#fdf9f5` |
| **ModelWizard** | **5** | 3 vius (`errBox:931`) + 2 en comentari |
| **Models** (referència) | **4** | 2 `rgba` + `delBtn:570` (`#C0392B`, `#FADBD8`) |
| FittingSessionList | 2 | |
| Planning · OrphanedWorkOrders · DeliveryNotes | 1 c/u | |
| **Les 21 restants** | **0** | |

**Total viu: ~110 literals · el 73% en 4 fitxers.**

🚩 **Hexes repetits entre fitxers amb orígens independents:**
- `#f0f9f0`/`#3b6d11`/`#c0dd97` (ok) i `#fff0f0`/`#a32d2d`/`#f09595` (err) →
  **tres còpies del mateix banner**: `GradingRuleSets:221-223`, `SizeLibrary:68-70`,
  `OnboardingWizard:64-66` — quan `ui/Feedback.jsx:8-12` ja el fa amb tokens.
- `#e4e4e2` → `ui/Card.jsx:5,13` · `FittingSessionList:27` · `UsersRoles:43`.
- `#f5e6d0` (= `--gold-pale`) → `OnboardingWizard:93,113,122,143,170`.

> ⚠️ **El comptador és un MÍNIM, no un total.** `ui/Card.jsx:5` i `:13` porten `#e4e4e2`
> cru: tota pantalla que faci servir `Card` (FittingSessionList, TimeTracking,
> UserProfilePage) **hereta 2 colors no-token que el grep del seu fitxer no veu**.

---

## 6 · Troballes transversals

1. **Doble padding** (§4.1) — 7 pantalles sumen padding al del Shell.
2. **`ui/Contenidor.jsx` no és el contenidor de pàgina** — és un plegable de panell amb
   capçalera fosca; 0 consumidors entre les 31.
3. **`ui/Card.jsx` injecta 2 hex crus** a qui la consumeix (§5).
4. **`FittingSessionList` copia `ui/Table.jsx`** en comptes de consumir-la (§4.3).
5. **Dos `Pill` homònims amb contractes oposats** (§4.5).
6. 🚩 **`OnboardingWizard.jsx` no importa `react-i18next`** (0 coincidències): tot el text
   de cara a l'usuari és **literal en català** — `:59` «Configuració inicial», `:94`
   «Començar →», `:123` «Guardar i continuar →», `:154` «✓ Configuració completada!»,
   `:171` «Anar al Dashboard →». Incompleix l'i18n-gate de `CLAUDE.md`. **Constatació.**
7. **Dues pantalles fixen `fontFamily` al contenidor de pàgina**, cosa que la resta no fa:
   `GradingRuleSets.jsx:182` (`IBM Plex Sans`) i `SizeLibrary.jsx:48` (`IBM Plex Mono`).

---

## 7 · Límits d'aquest inventari (dits clarament)

- **POMs** (`/poms`) s'ha censat via `POMCataleg.jsx`, que és tot el que renderitza
  `POMs.jsx:10`. **No s'han auditat els subcomponents** que POMCataleg munti a dins.
- Dashboard, Planning i SizeLibrary **deleguen part de la superfície visible** a
  `ProjectGantt`, `DashboardGovPanel`, `InformesPanel`, `SizingProfileSelector` i
  `SizeSetDetail`. Els colors d'aquests fitxers **no compten** a la columna 🚩 (el cens
  era per fitxer de pantalla). Si la mesura al navegador hi troba hex, l'origen és allà.
- `GraduacioPanel` és **codi mort** (no arribable des de cap superfície viva; establert a
  `REPORT_C5_CHIP_S37.md §5.3`) i no s'ha censat.
- **Les captures no mostren la tipografia de producció**: les fonts són de CDN i estaven
  bloquejades, o sigui que dibuixen amb el fallback del sistema. Els **valors mesurats no
  en depenen** (§3), però no jutgeu el TIPUS de lletra per la imatge.
- El contingut és **stubejat** (5 files per llista). On un detall surt buit —p.ex. la
  llista esquerra de `/poms`— és límit de l'stub, no un fet d'UI.
- A 13 pantalles amb `<table>`, la fila «capçalera de targeta» resol al `<thead>`:
  **aquestes targetes no tenen banda de capçalera pròpia**, el primer element amb
  `border-bottom` és la fila de `th`.
- **No verificat:** el breadcrumb de la topbar mostra «Fhort Textile Tech › Fhort Textile
  Tech» a `/encarrecs`, `/cataleg-peces` i `/comercial/productes`, i «… · Models» a
  `/models`. **No s'ha comprovat si depèn de l'stub**; queda com a observació, no com a fet.
