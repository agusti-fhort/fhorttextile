# DIAGNOSI — Components múltiples de mesures dins un mateix model

Data: 2026-07-21 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` (HEAD llegit: `a71b95c`)

**Abast.** Un model pot necessitar dos "components" de mesures diferenciats (ex. samarreta + calceta d'un nadó). Es diagnostica: si el model de dades ho permet avui (P1), què costaria afegir-ho (P2), si existeix parcialment (P3), i si el picker de la taula de fitxa tècnica seria reutilitzable (P4).

**Convenció.** Cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**, no especulat. Propostes marcades 💡 i separades dels fets — **les decisions són humanes (Patró C)**.

**Concurrència.** Sessió Patró B en paral·lel sobre `frontend/src/pages/TechSheetEditor.jsx` i taules. Domini disjunt; aquesta sessió **no ha escrit res ni ha fet cap `pull`**. Les línies de `TechSheetEditor.jsx` són les de `a71b95c` i **poden haver-se desplaçat**.

---

## Resum executiu

1. **NO EXISTEIX cap dimensió de component.** Ni a `BaseMeasurement` (`models_app/models.py:547-604`) ni a `SizeFitting` (`fitting/models.py:7-55`). Grep de `component` als tres `models.py` del domini: **zero coincidències**.

2. **El bloqueig no és "falta un camp": és una clau.** `BaseMeasurement.unique_together = [('model','pom')]` (`models_app/models.py:598`) fa que **un POM només pugui existir un cop per model**. Dos components que comparteixin qualsevol POM (llarg, amplada…) no són "indistingibles" — són **impossibles d'inserir**.

3. **La clau `pom` sense component travessa TOTA la cadena.** `SizeCheckLine('size_check','pom')` (`models_app/models.py:924`), `GradedSpec('grading_version','pom','size_label')` (`fitting/models.py:209`), `PieceFittingLine` (`fitting/models.py:374`), `ModelGradingRule('model','pom')` (`models_app/models.py:746`), `ModelGradingOverride` (`models_app/models.py:689`). Són **5 taules més** que heretarien el forat.

4. **El domini JA resol el multi-peça, un nivell més amunt.** `GarmentSet` (`models_app/models.py:43`) + `Model.garment_set` (`:173`) + `Model.piece_number` (`:180`): producte multi-peça on **cada peça és un Model independent** (`codi_base + '-NN'`). Avui "samarreta + calceta" es modela com **dos Models**, no com dues particions d'un.

5. **El punt de fallada silenciosa és el motor de grading.** `_load_base_measurements` (`pom/services.py:592-606`) retorna `{pom_id: base_value_cm}`: dos components amb el mateix POM **col·lapsarien sense error**. És l'entrada de `generate_graded_specs` i **zona intocable** segons el `CLAUDE.md`.

6. **P4: l'enganxall NO és uniforme.** El patró "1 → auto, N → modal" existeix i està provat, però **només a la fitxa tècnica** (`TechSheetEditor.jsx:3520-3526`). I les dues variants difereixen: **T1b** usa el `sfId` per a les dades; **T1a NO** — fetcha les mesures model-wide i el `sfId` només l'estampa a la traçabilitat.

7. **Anotats de passada: dos forats VIUS avui**, sense necessitat de cap dimensió nova (§Anotacions).

---

## BLOC P1 — Existeix avui alguna dimensió? (FET pur)

- **`BaseMeasurement`** (`models_app/models.py:547-604`). Camps: `model`, `pom`, `base_value_cm`, `is_key`, `is_active`, `notes`, `updated_at`, `created_at`, `created_by`, `tolerancia_minus/plus`, `nom_fitxa`, `origen`, `ordre`. → **NO EXISTEIX** cap `component`/`part_code`/`subtipus`/`piece`.
- **Constraint**: `unique_together = [('model','pom')]` (`:598`), `ordering = ['model','ordre','pom']` (`:599`).
- **`SizeFitting`** (`fitting/models.py:7-55`). Camps: `model`, `numero`, `codi`, `tipus`, `sf_pare`, `estat`, dates, `creat_per`, `notes`, `base_tancada`. → **NO EXISTEIX** cap dimensió de component.
  - `tipus` (Proto/Fit/SizeSet/PP/TOP, `:8-14`) és **etapa**, no component. `sf_pare` (`:26`) és **llinatge**, no component.
  - `unique_together = [('model','numero')]` (`:54`) → **un model SÍ pot tenir N SizeFittings**.
- **Grep de `component`** a `pom/models.py`, `models_app/models.py`, `fitting/models.py`: **zero**. L'únic `ProductComponent` (`commerce/models.py:160`) és composició comercial de packs, **sense cap relació amb POMs ni mesures**.

> **Veredicte P1: NO EXISTEIX.** I el problema és més dur que una absència de camp: la clau `('model','pom')` fa **impossible** repetir un POM dins un model.

---

## BLOC P3 — Existeix parcialment? On, i per què no s'ha usat

Hi ha **tres** candidats propers. Cap serveix, i per raons diferents:

### P3.1 · `garment_type_item` — existeix, però és FK singular i modela una altra cosa
- `GarmentTypeItem` (`tasks/models.py:286`), docstring `:286`: *"Variant d'un GarmentType per grau de complexitat… Pantaló → xandall < chino < sastre"*. És **complexitat/variant**, no component físic.
- **`Model.garment_type_item` és una ForeignKey simple** (`models_app/models.py:161-167`), `null=True`, `on_delete=SET_NULL`. **Un Model té com a MÀXIM UN item.** NO EXISTEIX cap M2M ni taula intermèdia.
- La pertinença POM↔item viu a `GarmentPOMMap` (`pom/models.py:430`, clau `('garment_type_item','pom')` a `:457`) i els valors plantilla a `ItemBaseMeasurement` (`pom/models.py:464`, clau `('garment_type_item','pom')` a `:498`).
- La sembra és `materialize_poms_view` (`models_app/views.py:766-842`): llegeix `GarmentPOMMap.filter(garment_type_item=model.garment_type_item)` (`:792-794`) — **un sol item, singular** — i escriu `BaseMeasurement.objects.create(model=…, pom=…)` (`:808`, `:818`) amb `origen='ITEM_STANDARD'`.
- **Per què no s'ha usat per a components:** perquè no ho pot fer. La cardinalitat és 1, i la semàntica és complexitat.

### P3.2 · `GarmentSet` + `piece_number` — **aquest SÍ resol el cas, però a nivell de Model**
- `GarmentSet` (`models_app/models.py:43`), docstring `:43-58`: producte comercial multi-peça (twin set, vestit+cinturó) on **cada peça és un Model independent** amb `codi_intern = codi_base + '-NN'`.
- `Model.garment_set` FK (`:173`) i `Model.piece_number` (`:180`).
- **Aquesta és la resposta actual del domini a "dos grups de mesures"**: dos Models germans dins un set. Cada Model manté la seva clau `('model','pom')` intacta i tota la cadena funciona sense canvis.
- **PENDENT DE VERIFICAR:** quants `GarmentSet` hi ha a staging i si s'usa en producció — requeriria consulta a BD, **no feta** (read-only estricte).

### P3.3 · `PatternPiece` / `PatternPOM` — la peça existeix, però no arriba a les mesures
- `PatternPiece` (`patterns/models.py:150`, *"Una peça = un BLOCK del DXF"*) i `PatternPOM` (`:303`) ancoren un POM a la geometria d'una peça concreta.
- **Aquesta dimensió NO arriba mai a `BaseMeasurement`**: el consumidor (`patterns/views.py:470-492`) fa el join a la inversa — indexa `PatternPOM` per `pom_master_id` i llegeix `BaseMeasurement.filter(model_id=…, is_active=True)` **plana**.

> **Veredicte P3: existeix parcialment, però desplaçat.** La noció de "peça" existeix a dalt (`GarmentSet`, com a Models separats) i a baix (`PatternPiece`, geometria). **Al mig — la capa de mesures — no hi és**, i la clau `('model','pom')` impedeix que hi sigui.

---

## BLOC P2 — Què costaria afegir-ho

**No és "un camp + una migració".** És un canvi de clau que es propaga per sis taules i ~40 consumidors.

### P2.1 · Canvi estructural mínim
- `BaseMeasurement`: camp nou + **canvi de `unique_together` a `('model','pom','component')`** (`models_app/models.py:598`) + migració amb `default` per a les files existents.
- I, per coherència de cadena (§Resum 3): `SizeCheckLine` (`models_app/models.py:924`), `GradedSpec` (`fitting/models.py:209`), `PieceFittingLine` (`fitting/models.py:374`), `ModelGradingRule` (`models_app/models.py:746`), `ModelGradingOverride` (`models_app/models.py:689`). **Sense propagar-hi la dimensió, la cadena base→grading→fitting→check trenca a cinc taules.**
  - Cas concret ja identificat: `SizeCheckLine.unique_together = ('size_check','pom')` → dos components amb el mateix POM **violarien la constraint** en materialitzar les línies (`services_size_check.py:24-37`).

### P2.2 · Consumidors que TRENCARIEN — col·lapse silenciós a `{pom_id: …}`
Aquests indexen per `pom_id`: dues files amb el mateix POM **se sobreescriuen sense error**.

| # | Ancoratge | Què és |
|---|---|---|
| 1 | **`pom/services.py:592-606`** | **`_load_base_measurements` → entrada del motor de grading** (`generate_graded_specs`, `:104`, `:160`). **Zona intocable (`CLAUDE.md`) — anotat, no tocat.** |
| 2 | `pom/s10_views.py:49-55` | `_tolerance_map` |
| 3 | `pom/s8_views.py:180-184` | `tol_map` (CSV fitting) |
| 4 | `pom/s11_views.py:161-165` | `base_map` (POMAlert) |
| 5 | `fitting/graded_spec_views.py:82-91` | `ordre_map`/`nom_fitxa_map` (payload de la fitxa) |
| 6 | `fitting/serializers.py:248-252` | `ordre_map`/`nom_fitxa_map`/`bm_id_map` |
| 7 | `models_app/serializers_size_check.py:81-84` | toleràncies del Size Check |

### P2.3 · Consumidors que TRENCARIEN — escriptura per `(model,pom)`
`update_or_create`/`get_or_create`/lookup que assumeixen 0-o-1 fila i **no sabrien a quin component escriure**:
- `pom/wizard_views.py:205` i `:192` (el `.update()` tocaria **totes** les files del POM)
- `models_app/views.py:1068` · `:1182` · `:1556` · `:2022-2030` (`_write_base`)
- `models_app/extraction_views.py:1967`; i **`:1948` `.delete()` massiu** esborraria les files buides de **tots** els components
- `models_app/tech_sheet_views.py:358`
- `fitting/services.py:369-378` (consolidació de fitting) · `models_app/services_size_check.py:172-185`
- Lookups `.first()`/`.get()`: `models_app/views.py:804`, `:1182`; `repair_fitting_20260710.py:78`; `fitting/test_g6_estalitud.py:50`, `:161`, `:181`

### P2.4 · Consumidors que trencarien SEMÀNTICAMENT
- **Soft-delete global**: `models_app/views.py:1089`, `:1204`, `:1580` — `exclude(pom_id__in=keep).update(is_active=False)`: una llista `keep` d'un component **desactivaria** les files de l'altre.
- **Ordre global**: `models_app/views.py:2069-2085`, docstring literal *"ordre ÚNIC i global del model"*. Caldria ordre per grup — i això toca la fitxa tècnica (§P2.6).

### P2.5 · Frontend — totes les superfícies són llistes planes model-scoped
- **Font única del tab Mesures**: `GET /api/v1/models/<id>/taula-mesures/` (`ModelSheet.jsx:130`, `:147`), servit per `models_app/views.py:911-1034` → `BaseMeasurement.filter(model=…, is_active=True).order_by('ordre','pom__codi_client')` (`:925-928`), **una fila per POM, sense cap discriminant**.
- **`MeasureGrid.jsx`** (l'editor únic): `rows.map((r,i) => <tr key={r.pom_id}>…)` (`:322-368`) — files planes, clau `pom_id`, **sense agrupament ni encapçalaments**. No fa fetch: rep `rows`/`groups` per props.
- `CheckMeasureEditor.jsx:210-232` (`buildRows`, un sol grup `'base'`), `MeasuresEntryPanel.jsx:63`, `:104`, `ImportWizard.jsx:393`, `PropagatedEditor.jsx:28` (comentari `:13`: *"UNA taula vigent"*), `fittingGridAdapter.jsx:109`, `:135` (**`lineId = ${pom_id}:${size}` — la identitat d'una cel·la és (POM, talla): no hi cap una tercera dimensió**).
- `base-stages` (`models_app/views.py:2092-2107`) — igualment pla i model-scoped.
- **Cap dels dos endpoints font (`taula-mesures`, `base-stages`) accepta cap `sf_id` ni cap discriminant.**

### P2.6 · On enganxaria visualment (fet, no proposta)
- **NO EXISTEIX agrupament de FILES** a `MeasureGrid`: grep de `categoria|groupBy|section` → **0 hits**; l'únic ritme visual és el zebrat (`:323`).
- El `groups` de `MeasureGrid` **NO és agrupament de files: és de COLUMNES** (docstring `:5-8`; `<th colSpan>` a `:299-320`). És la dimensió que el component ja sap dibuixar (talla, estadi).
- La dimensió `categoria` **ja existeix al backend amb `display_order`** i tres endpoints de grading hi ordenen (`pom/s6_views.py:161-163`, `pom/grading_views.py:96`, `fitting/graded_spec_views.py:69`) — **però `taula-mesures` i `base-stages` no la retornen**. És el precedent més proper d'una dimensió d'agrupament que existeix a baix i no puja.

> **Veredicte P2: cost ALT i transversal.** ~7 punts de col·lapse silenciós, ~12 punts d'escriptura, 6 taules de clau, 2 endpoints font i 6 superfícies de frontend, amb el motor de grading (intocable) al centre. **No és un sprint de camp nou.**

💡 **PROPOSTA P2-A (a validar) — la sortida barata: no tocar la capa de mesures.** Modelar el segon component com un **Model germà dins un `GarmentSet`** (`models_app/models.py:43`, `:173`, `:180`), que és el que el domini ja preveu. Cost ≈ 0 al motor: cada Model manté `('model','pom')` i tota la cadena intacta. El que caldria és **UI de set** (crear/navegar germans) i decidir com es presenten junts a la fitxa. **Recomanada per a validar primer**, perquè converteix un canvi de clau en un canvi de navegació.

💡 **PROPOSTA P2-B (a validar) — si es vol la dimensió de debò.** Ha de néixer **a la clau, no a la vora**: `('model','component','pom')` propagada alhora a les 6 taules, amb `component` NOT NULL i un valor per defecte (`'PRINCIPAL'`) per a tot l'existent. Qualsevol variant que deixi `component` nullable o només a `BaseMeasurement` reprodueix el col·lapse silenciós del punt 1 de P2.2.

💡 **PROPOSTA P2-C (a validar) — ordre de treball si es tria B.** Primer els 7 punts de col·lapse (P2.2), que són els que perden dades sense avisar; després les escriptures (P2.3); l'UI l'última. I **abans de res**, decidir si `_load_base_measurements` (zona intocable) s'obre — perquè si no s'obre, B no és viable.

---

## BLOC P4 — Reutilitzable el picker de la fitxa tècnica?

### P4.1 · El patró existent (i és l'únic del sistema)
- Càrrega: `GET /api/v1/size-fittings/?model=${id}` → `setSizeFittings` (`TechSheetEditor.jsx:2294-2295`).
- **La regla, literal** (`onPickTableVariant`, `:3517-3523`): `if (!sizeFittings.length) return` · `if (sizeFittings.length === 1) { runTableVariant(variant, sizeFittings[0].id); return }` · `setTablePicker({ variant })`.
- Modal (`:5236-5243`): un botó per SF, etiqueta `sf.codi || sf.nom || sf.talla_base || '#'+sf.id` + `sf.tipus ? ' · '+sf.tipus : ''`. **L'etiqueta ja composa una segona dimensió.**
- i18n completa ca/en/es (`i18n/*.json:2609` `pick_size_fitting`, `:2527` `no_size_fitting`).
- **NO EXISTEIX cap altre picker d'SF al sistema**: cap a `frontend/src/components/model/` (0 hits), cap pàgina de fitting que llisti SFs. `App.jsx:291` diu literalment que *"l'antiga SizeFitting es va jubilar"* — l'SF és infraestructura invisible per a l'usuari.

### P4.2 · L'enganxall NO és uniforme entre les dues variants
- **T1b (`insertTableT1b`, `:3431`) SÍ usa el `sfId` per a les dades**: `GET /api/v1/fitting/${sfId}/graded-table/` (`:3435`) + snapshot (`:3467`).
- **T1a (`insertTableT1a`, `:3381`) NO**: fetcha `GET /api/v1/models/${model.id}/base-measurements/` (`:3386`) — **model-wide** — i el `sfId` **només** l'estampa a `snapshot.size_fitting_id` (`:3424`). **La tria del picker no filtra cap dada a T1a.**
- Signatura: `runTableVariant(variant, sfId)` (`:3513`) → `insertTableT1a(sfId)` / `insertTableT1b(sfId)`. **Un sol id escalar** travessa tot el camí.

### P4.3 · Resposta (FET, sense dissenyar)
- **Si "component" fos un atribut de `SizeFitting`** → l'enganxall és **net**: el picker ja llista SFs, l'etiqueta ja composa una segona dimensió (`:5242`) i T1b ja va per `sfId`. Canvi mínim.
- **Si "component" visqués a `BaseMeasurement`** (que és on el domini el demana, §P3) → l'enganxall **NO és net**: (a) `insertTableT1a` necessitaria un **segon paràmetre** i la signatura escalar de `runTableVariant` hauria de canviar; (b) l'endpoint `models/<id>/base-measurements/` **no accepta cap discriminant** (`pom/wizard_views.py:301-335`) i n'hauria de rebre un de nou; (c) el picker hauria de resoldre **dues** dimensions ortogonals (quin SF **i** quin component), que és un gest diferent del "tria'n un d'aquesta llista" actual.

> **Veredicte P4: reutilitzable tal qual NOMÉS si el component penja de `SizeFitting`.** Si penja de `BaseMeasurement`, el patró de selecció serveix d'inspiració però **no s'enganxa**: T1a avui no filtra res amb la tria, i cap dels dos endpoints font accepta la dimensió.

---

## Anotacions — forats VIUS avui (fora de l'encàrrec, no tocats)

Trobats en traçar el radi; **no depenen de cap dimensió nova** i ja són reals a `dev`:

- **A1 · Un import guiat deixa el tab Mesures en només-lectura per sempre.** L'import crea un SF **contenidor** `estat='Tancat'` (`models_app/extraction_views.py:1979-1985`, `:2103-2109`), i `models_app/views.py:1015-1019` fa `SizeFitting.objects.filter(model=model, estat='Tancat').exists()` → `tancat=True` per al model sencer, encara que l'SF de treball segueixi obert.
- **A2 · `generar-grading` no ordena en resoldre l'SF.** `models_app/views.py:1623` fa `.filter(model=model).first()` **sense `order_by`** → ordre indeterminat de BD. Amb l'SF-contenidor de l'import present, **pot graduar un SF diferent** del que llegeixen `taula-mesures`/`graded-table`.
- **A3 · Cinc criteris distints per a "quin és l'SF d'aquest model"**: `fitting/services.py:511-520` (preferència per versió activa) · `pom/services.py:293-337` (`order_by('numero').first()`) · `models_app/views.py:1623` (`.first()` sense ordre) · `pom/wizard_views.py:175`, `:243` (`numero=1` cablat) · `models_app/views.py:1019` (`.exists()`).
- **A4 · Dos SFs del mateix model graduarien la MATEIXA base.** `generate_graded_specs` entra per `sf_id` (`pom/services.py:122`) però llegeix la base per `model.pk` (`:160`); `measurements_version` també és del Model (`:708-711`).
- **A5 · `pom/grading_views.py:76-78`** manté criteri propi de versió (`.filter(is_active=True).last()`) en lloc de `vigent_grading_version` — el mateix defecte que es va corregir a `s6_views.py:146`; aquest lector es va quedar fora.
- **A6 · `_ORIGEN_TO_CONTEXT`** (`models_app/signals.py:197-203`) no conté `ITEM_STANDARD`, `TEMPLATE` ni `CHECKED`: cauen al fallback `origen.lower()` (`:273`).

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT

| # | Peça | Estat | Ancoratge | Risc |
|---|---|---|---|---|
| 1 | Camp de component a `BaseMeasurement` | **NO EXISTEIX** | `models_app/models.py:547-604` | — |
| 2 | Camp de component a `SizeFitting` | **NO EXISTEIX** | `fitting/models.py:7-55` | — |
| 3 | Clau `('model','pom')` | **EXISTEIX i bloqueja** | `models_app/models.py:598` | **ALT** — repetir un POM és impossible |
| 4 | Dimensió a la resta de la cadena | **FALTA** ×5 | `models.py:924`, `:746`, `:689`; `fitting/models.py:209`, `:374` | **ALT** |
| 5 | N items per Model | **NO EXISTEIX** (FK singular) | `models_app/models.py:161-167` | — |
| 6 | Multi-peça a nivell de Model | **EXISTEIX** | `GarmentSet` `:43`, `:173`, `:180` | Cap — és la sortida barata |
| 7 | Noció de peça a patró | **EXISTEIX, no puja** | `patterns/models.py:150`, `:303` | Baix |
| 8 | Entrada del motor de grading | **EXISTEIX, col·lapsa** | `pom/services.py:592-606` | **CRÍTIC** — pèrdua silenciosa; zona intocable |
| 9 | Altres dicts per `pom_id` | **EXISTEIXEN** ×6 | P2.2 #2-#7 | ALT |
| 10 | Escriptures per `(model,pom)` | **EXISTEIXEN** ×12 | P2.3 | ALT |
| 11 | Soft-delete i ordre globals | **DIFERENT** | `views.py:1089`, `:1204`, `:1580`, `:2069` | Mitjà |
| 12 | Endpoints font amb discriminant | **FALTA** | `taula-mesures` `:911`; `base-stages` `:2092` | ALT |
| 13 | Agrupament de files a `MeasureGrid` | **NO EXISTEIX** | `MeasureGrid.jsx:322-368` | — |
| 14 | Agrupament de columnes (`groups`) | **EXISTEIX** | `MeasureGrid.jsx:5-8`, `:299-320` | Cap — dimensió ja dibuixable |
| 15 | `categoria` com a precedent | **EXISTEIX a baix, no puja** | `s6_views.py:161`, `grading_views.py:96` | Baix |
| 16 | Picker "1→auto, N→modal" | **EXISTEIX** (només fitxa) | `TechSheetEditor.jsx:3517-3523`, `:5236-5243` | Cap |
| 17 | T1a filtra per la tria | **NO** | `:3386` model-wide; `sfId` només a `:3424` | Mitjà — la tria és decorativa a T1a |
| 18 | T1b filtra per la tria | **SÍ** | `:3435` | Cap |
| 19 | Picker d'SF fora de la fitxa | **NO EXISTEIX** | 0 hits a `components/model/` | — |
| 20 | Import guiat → model read-only | **FORAT VIU** | `extraction_views.py:2103` + `views.py:1019` | **ALT** (independent d'aquesta feina) |
| 21 | `generar-grading` sense `order_by` | **FORAT VIU** | `models_app/views.py:1623` | **ALT** (independent) |

---

### Obert / pendent de verificar

- **Quants `GarmentSet` i quants Models amb `piece_number` hi ha a staging** — decisiu per a la 💡P2-A. Requeriria consulta a BD: **no feta** (read-only estricte).
- Quants Models tenen avui >1 `SizeFitting` (l'import guiat n'hi afegeix a cada passada) — mateixa raó.
- `frontend/src/components/EditableTable/` no auditat fila a fila (grep de `categoria` → 0 hits, però no descarta agrupaments amb un altre nom).
- No s'ha auditat el frontend per al concepte item→mesures més enllà de `MeasuresEntryPanel.jsx:14`, `:68`.
