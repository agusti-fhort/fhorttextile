# REPORT F2.2 · CODA + FINAL · les enumeracions de domini, tancades fins on es podia — 🛑 STOP

**Data:** 08/08/2026 · **CAP PUSH** · Base `11c204eb`

> **El titular:** el cens final **dona zero dins del perímetre acordat**. Cauen les 11 còpies amb
> endpoint viu (`gradingAxes.js` inclòs, que era la més grossa) i, de propina, sis més que el cens
> anterior no havia vist. **Queden dos BLOQUEJATS de veritat** —`GARMENT_GROUPS` i les caselles del
> full imprès— i tots dos ho estan per la mateixa raó: **la taula no té el que la còpia dona**.
> Un no és un descuit: és una migració que toca C6, que està aturat.

---

## A · F2.2-CODA (backend)

### A.1 · L'autorabilitat la marca el backend

`GET /api/v1/vocabulari/` → `regims_graduacio[]` porta ara **`autorable`**.

| Règim | `autorable` | Per què |
|---|---|---|
| LINEAR · STEP · FIXED | ✅ | Els tres que el detector produeix i que un tècnic escriu |
| **ZERO** | ❌ | 🛑 v. sota |
| **EXCEPTION** | ❌ | Petja que ESCRIU EL MOTOR (`pom/services.py:259,266,768`) des d'un `ModelGradingOverride`. Cap camí d'autoria l'escriu ni el pot escriure |

**La marca va DINS de l'element, no en una llista paral·lela** (`regims_autorables: [...]`): una
llista paral·lela es pot desincronitzar de la principal; un booleà al costat del codi, no.

### 🛑 A.2 · ZERO: el codi es contradeia i he pres partit — DECISIÓ TEVA

L'ordre deia «si del codi es desprèn que algun altre tampoc és d'autoria, marca'l i reporta-ho».
Amb ZERO **el codi no parla amb una sola veu**, i això s'ha de dir:

* `GraduacioSuperficie.jsx:81` (la superfície d'autoria de graduació) **el descartava
  explícitament i amb motiu escrit**: «ZERO i EXCEPTION NO s'ofereixen com a tria nova; ZERO =
  nínxol "sempre 0"». És **l'única raó escrita a tot el projecte** sobre ZERO.
* `SizeMapSetup.jsx:21` (el wizard de derivació) **sí que l'oferia**, sense cap raó escrita.

Tres fets que he verificat i que decanten:

1. **El detector no el pot produir mai.** `pom/grading_utils.py:245-256` només surt amb LINEAR,
   STEP o FIXED. El select de `SizeMapSetup` és per SOBREESCRIURE la detecció, o sigui que ZERO
   només hi podia entrar a mà.
2. **Cap dada viva el porta.** A `fhort`: **1.034 LINEAR + 233 FIXED = 1.267**. Zero ZERO, zero
   STEP, zero EXCEPTION.
3. **«Sempre 0» ja és FIXED amb base 0** i en surt exactament el mateix full.

**He marcat ZERO com a NO autorable.** Efecte real: `SizeMapSetup` perd ZERO del desplegable
(`GraduacioSuperficie` no canvia gens). Cap regla existent s'amaga enlloc — la marca diu si es pot
ESCRIURE, no si existeix.
**Si ho vols a l'inrevés és UNA LÍNIA:** treure `LOGICA_ZERO` de `REGIMS_NO_AUTORABLES`
(`vocabulari_views.py`). No cal tocar cap pantalla.

### A.3 · Fase A: dues enumeracions més, i una marca més

| Clau nova | Font | Marca |
|---|---|---|
| `estats_sessio_fitting` | `FittingSession.ESTAT_CHOICES` (Programada · Oberta · Tancada · Anullada) | **`segellat`** |
| `veredictes_fitting` | `PieceFittingLine.DECISIO_CHOICES` (ACCEPTED · ADJUSTED · REJECTED) | — |

**`segellat` no és una llista nova: és el MATEIX `SEALED_SESSION_ESTATS`** de
`fitting/services.py`, importat i no copiat — el mateix que `fitting_line_is_locked` fa complir a
l'escriptura. El client en tenia **dues** còpies (`FittingDetail:164`,
`FittingConvocatoriaSheet:69`) i totes dues es deien «mirall del backend», que és el nom que rep un
duplicat que encara no ha divergit.

**`veredictes_fitting` NO porta el buit, i és a posta.** `''` és l'ABSÈNCIA de veredicte, no un
quart membre. Emetre'l faria que qualsevol select el pintés com una quarta opció triable i
ensorraria la distinció que `PieceFittingLine` defensa amb el `default=''`: **una cel·la que ningú
no ha mirat no és una cel·la acceptada.**

### ✅ A.4 · Unitats i normes: COMPROVAT, i NO s'exposen

L'ordre les condicionava a que les pantalles de Mesures/Fitting **les pintessin**. **No les
pinten.** El selector de `CM`/`INCH` i el d'`ISO_8559`/`ASTM_D13` viuen només a
`GeneralConfig.jsx:13,14` (mòdul Sistema) i a `OnboardingWizard.jsx:110` (alta). Mesures i Fitting
només **consumeixen** el valor que el tenant ja ha triat (`fittingShared.jsx:9-13` el llegeix de
`/tenant-config/` per formatar) — i consumir un valor no és duplicar una enumeració.
→ **CENSAT-PENDENT amb la resta del mòdul Sistema.**

### A.5 · `construction-types/` serveix `nom_es`

Peça petita i necessària: `ConstructionTypeSerializer` emetia `nom_en` i `nom_cat` **però no
`nom_es`**, i era **l'única raó** per la qual el client s'havia d'inventar «Tejido plano».
Exactament el mateix cas que F2.1b va arreglar per a `FitType`. Les 4 files el tenen informat
(verificat: 0 sense `nom_cat`/`nom_es` a Target, ConstructionType i FitType).

---

## B · F2.2-FINAL (frontend) — el que cau

### B.1 · Les 11 còpies que l'ordre nomenava

| Enumeració | Còpies mortes | D'on surt ara |
|---|---|---|
| **Fases del model** | **7** — `Dashboard:35` · `DashboardGovPanel:15` · `InformesPanel:15` · `ActionsMenu:9` (**exportada**, la importava `Models.jsx`) · `AddModelToGroupModal:16` · `FittingSessionList:14` · `ProjectGantt:28` | `fases_model` |
| **Fases de tasca** | 1 — `TaskTree:24` | `fases_tasca` |
| **Règims** | 2 — `SizeMapSetup:21` · `GraduacioSuperficie:85` | `regims_graduacio` + `autorable` |
| **Eixos de grading** | `gradingAxes.js` — TARGETS (13) · CONSTRUCTIONS (4) · FITS (10), amb els noms en TRES idiomes escrits a mà | `/targets/` · `/construction-types/` · `/fit-types/` |

### B.2 · Sis més que el cens anterior no havia vist

| On | Què era | Ara |
|---|---|---|
| `SizeMapSetup:20` `BASE_UNITS` | **Literalment una llista de reserva**: `lookups.base_units?.length ? … : BASE_UNITS`. L'endpoint ja les servia | `lookups.base_units` sec |
| `FittingSessionList:15` `ESTATS` | Estats de sessió | `estats_sessio_fitting` |
| `FittingDetail:164` · `FittingConvocatoriaSheet:69` | Dues còpies de la llista de segellats | `useSessioSegellada()` |
| `CheckMeasureEditor:353` `RECOMPTES` | Enumeració i colors FUSIONATS en una llista | `veredictes_fitting` + `RECOMPTE_COL` |
| `SizingProfileSelector:84` | Dues peticions pròpies a `/construction-types/` i `/fit-types/` | `useEixos()` (**−2 peticions**) |
| `ActionsMenu:17,18` · `DashboardGovPanel:16` | `nextPhase`/`prevPhase` **duplicats** | `codiSeguent`/`codiAnterior`, un sol lloc |

### B.3 · Infraestructura nova

* **`components/grading/eixosFont.js`** — tercera germana de `diccionariMesuresFont` i
  `vocabulariDominiFont`. Les tres peticions van en paral·lel i es resolen com una; cache de mòdul
  i promesa compartida; **cap llista de reserva**. Tradueix `nom_cat` → `nom_ca` un sol cop, aquí,
  perquè cap pantalla hagi de saber que hi ha dos noms per a la mateixa cosa.
* **`vocabulariDominiFont.js`** guanya `elementsDe`/`useElements` (calen quan l'element porta
  MARQUES, que no es dedueixen del codi), `codiSeguent`/`codiAnterior` i `useSessioSegellada()`.

### B.4 · On el dubte NO és neutre — tres llocs on he triat el costat

La llei diu «sense vocabulari, no oferir». En tres punts **no oferir no bastava**, perquè el `null`
també es podia llegir com una AFIRMACIÓ:

1. **`DashboardGovPanel`** — «no sé quina fase ve després» i «no en ve cap» tenen la mateixa forma
   (`null`) i conseqüències oposades: la segona diu que el model és a TOP. Sense vocabulari la
   columna pinta `—`, **no** «al final del cicle».
2. **`useSessioSegellada()`** — sense vocabulari, o amb un estat desconegut, torna **`true`**.
   Equivocar-se cap a lectura costa una pantalla que no deixa editar; cap a escriptura costa una
   sessió tancada que es toca.
3. **`RecomptesFitting`** — sense vocabulari **tot són pendents**, no «zero acceptades».

### B.5 · El que ES QUEDA amb motiu (i no és el mateix duplicat)

Mapes **indexats pel codi** que aporten alguna cosa que l'endpoint no té: `VERDICTE_TO` i
`VERDICTE_COL` i `RECOMPTE_COL` (color) · `FASE_COLORS` (paleta de data-viz) · `TECLA_VERDICTE`
(**keybinding** a/j/r — no hi ha cap camp `tecla` a cap taula) · `PHASE_I18N` i `FASE_KEY`
(**traducció a tres idiomes**; l'endpoint emet UNA etiqueta, i traduir els codis és decisió teva i
lloc de taula, no d'aquest endpoint) · `STATUS_VARIANT`. Cap declara el vocabulari: si arriba un
membre nou, surt **sense color** però surt.

---

## 🛑 C · ELS DOS BLOQUEJATS (i no per prudència)

### C.1 · `GARMENT_GROUPS` — la taula no té el que la còpia dona

`pom.GarmentGroup` té `codi`, `nom`, `descripcio`, `actiu`. **Cap `nom_en`/`nom_ca`/`nom_es`, cap
`display_order`.** Buidar la constant faria pintar els grups amb el `nom` anglès de BD en els tres
idiomes i en ordre alfabètic per codi.

I la còpia **ja és curta**, cosa que confirma el diagnòstic: a `fhort` hi ha **12 grups a la BD** i
la constant en declara **7**. Els cinc que falten (`DRESSES-FULL`, `KNITWEAR`, `NEWBORN`,
`TOPS-KNIT`, `TOPS-WOVEN`) ja cauen al fallback de `garmentCatalog.js:normGroup` — surten amb el
`nom` de BD i al final de l'ordre. **Mitja taula ja viu sense aquesta llista.**

**Per desbloquejar:** migració que afegeixi `nom_en`/`nom_ca`/`nom_es` + `display_order` a
`GarmentGroup`, i backfill.
⚠️ **Topa amb C6 pas 1, que està aturat:** el tenant `los` té `GarmentGroup` **BUIDA** (v. el
comentari de `GarmentType.grup` a `pom/models.py`), o sigui que allà no hi ha res a backfillar.

### C.2 · `FittingPrintSheet:31` `CASELLES = ['AC','AD','RJ']`

Les abreviatures del paper — **el que el fabricant marca**. Són domini, però **cap model les
declara**: no hi ha camp `abreviatura` a `PieceFittingLine`. Inventar-lo al serializer seria
fabricar dada al backend, que és pitjor que la còpia. Per matar-lo, l'abreviatura ha de ser
primer DADA del model (decisió teva).

---

## D · CENSAT-PENDENT (Fase B — les constants del client VIUEN fins llavors)

Comercial: `Orders:18` · `OrderDetail:21` · `Quotes:21` · `DeliveryNotes:18` · `WorkOrders:18,19`
(kinds + estats) · `Products:145` (natures) · `CustomerForm:7,8` (règim fiscal, pagament).
Sistema: `UsersRoles:11,13` (capabilities + rols) · `GeneralConfig:13,14` (unitats + normes) ·
**`OnboardingWizard:110`** (`['CM','INCH']` inline — 🆕 no era al cens anterior).
Altres: `TechSheetEditor:54` (tipus de geometria) · `EditableTable:1883` (nivells de proximitat) ·
**`ModelsFilterPanel:105`** (`['Pending','Paused','InProgress','Done']`, estats de tasca — 🆕 no
era al cens anterior).

**Cens final dins del perímetre:** `grep` d'enumeracions de domini fora d'aquesta llista, de
`KONVA_COL`/`PALETTE`/`QUICK_COLORS` (excepció Konva ja amb acta) i dels dos bloquejats de §C →
**zero**.

---

## E · Verificació

| Control | Resultat |
|---|---|
| `manage.py check` | ✅ net |
| `python manage.py test fhort.models_app fhort.fitting` | ✅ **671/671 · OK** (44 min) |
| Tests nous (`test_vocabulari_marques.py`) | ✅ **9/9** — inclou un GUARDIÀ que peta el dia que algú afegeixi un règim sense decidir-ne l'autorabilitat |
| Servei viu, post-`systemctl restart ftt-staging` | ✅ 200 amb les **sis** claus, `autorable` i `segellat` correctes, `veredictes_fitting` sense el buit · `/construction-types/` amb `nom_es` |
| `npm run build` | ✅ verd |
| **`eslint`** | ✅ **1253** vs 1254 de base (**delta −1**) · **0 errors dins de `src/`** (els 991 «errors» són tots a `dist-tenants/`, bundle construït, com a la base) |
| `node --test` | ✅ **218/218** |
| i18n | ✅ **cap clau nova, cap clau retirada** |

## F · Captures (`ops/qa/captures/f22_*.png`)

`ops/qa/qa_f22_vocabulari_captures.py`. **Aquí l'API NO va mockada, i és tota la gràcia:** la
resta de scripts d'aquesta carpeta serveixen `/api/` des de fixtures perquè volen aïllar el CSS;
això s'ha de veure contra el gunicorn DESPLEGAT, perquè amb fixtures la foto sortiria bé fins i
tot amb el backend vell — que és exactament el mode de fallada que la llei d'infra descriu.

| Captura | Què demostra |
|---|---|
| `01_models_filtre_fase` | El select «Totes les fases» de la llista de models |
| `02_fitting_sessions` | **Dues** files de píndoles: Fase (6 de `fases_model`) i Estat (4 de `estats_sessio_fitting`) — i l'Estat ara va en l'ordre del MODEL (Programada abans que Oberta), no en el que la constant del client havia escrit |
| `03_grading_rule_sets` | Els **13 targets** de la BD, en `display_order`, en català i amb la franja d'edat; els no disponibles atenuats |
| `04_size_library` | Els **tres eixos** encadenats: 13 targets → 4 construccions (`nom_cat`) → 10 fits. Aquesta pantalla fa ara **dues peticions menys** |
| `05_model_wizard` | Pas 2: TARGET (13) · FIT (10) · CONSTRUCCIÓ (4), tots del catàleg |

⚠️ Dues pantalles amaguen darrere d'una porta justament el que el tram toca (els chips de
construcció/fit no existeixen sense target; el pas 2 del wizard està bloquejat sense client i
temporada). El guió les obre: fotografiar-les tancades donaria cinc captures verdes que no
ensenyen res.

**No hi ha captura de `GraduacioSuperficie` ni de `SizeMapSetup`** (els dos selects de règim, que
és on es veu `autorable`): `fhort` té **1 model** i el wizard de `SizeMapSetup` només s'obre des
d'un calaix de Size Library amb una taula de client carregada. La marca queda verificada per
l'endpoint viu i pels 9 tests; a pantalla, quan hi hagi dades.

## 🛑 STOP

Fet tot el perímetre. **Una decisió t'espera** (§A.2, ZERO) i **dos bloquejos** volen la teva
(§C.1 migració de `GarmentGroup` lligada a C6 · §C.2 l'abreviatura del paper com a dada).

**Nota de maquetes:** a `ops/maquetes/` hi ha `maqueta_fitting_v4.html`,
`maqueta_grading_rules_v4.html` i `maqueta_size_library_v3.html` amb data d'avui, **però
`CANVIS_S38.md` no hi és** (ni enlloc del repo). Per a A2/A3 faré servir aquestes versions com a
font; si el resum de canvis existeix, encara no ha arribat a la màquina.
