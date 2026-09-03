# CENS DE L'EIX D'INSTÀNCIA · staging · 2026-08-25

> **READ-ONLY ABSOLUT.** Cap escriptura, cap migració, cap suite. Cap suite en marxa en
> començar (`ps` net a les 11:44 UTC, load 0.16) → no s'ha trepitjat el gate de nit.
> Base: `/var/www/ftt-staging`, branca `dev`, `55e76c5d`. BD: `ftt_staging` a
> **127.0.0.1:5433** (`postgresql@18-main`), schemes `public` · `fhort` · `los`.

---

# I1 · VOCABULARI I FONT DE VERITAT

## FET

La font de veritat és **una taula, no una constant**: `pom.MeasurementInstance`
([pom/models.py:282](backend/fhort/pom/models.py#L282)). Bessona de `MeasurementLayer` i, com
ella, replicada a `public` **i** a cada tenant (`fhort.pom` viu a SHARED i TENANT alhora,
[settings.py:53-55](backend/fhort/settings.py#L53-L55)).

**El vocabulari viu, mesurat als tres schemes — 12 files, IDÈNTIQUES a `public`, `fhort` i `los`:**

| eix | slugs (per `display_order`) |
|---|---|
| `POSICIO` (10) | `left`(L) · `right`(R) · `top`(T) · `bottom`(**BM**) · `cf`(CF) · `cb`(CB) · `side`(S) · `waistband_seam`(—) · `front`(F) · `back`(B) |
| `ESTAT` (2) | `relaxed`(—) · `extended`(—) |

Totes `is_system=t`, `origen=SEED`, `pendent_revisio=f`. La instància ÚNICA **no és una fila**:
és `''` (`MeasurementInstance.SLUG_UNICA`, [pom/models.py:347](backend/fhort/pom/models.py#L347)).

**Sembra:** [seed_measurement_instances.py:38](backend/fhort/pom/management/commands/seed_measurement_instances.py#L38)
(`POSICIONS`) i [:64](backend/fhort/pom/management/commands/seed_measurement_instances.py#L64)
(`ESTATS`) — `update_or_create` per `slug`, **mai `delete`**. La BD i la sembra coincideixen fila per fila.

**Els dos sub-eixos de la POSICIÓ** són una CONSTANT de servidor, a posta:
`MeasurementInstance.SUBEIXOS` ([pom/models.py:368](backend/fhort/pom/models.py#L368)) —
`CARA`=(front,back) · `LATERAL`=(left,right). L'acta diu per què no és columna: és GEOMETRIA de
la peça, no dada que un tenant informi; una columna la faria divergir entre schemes. **L'ordre de
la tupla és l'ordre del SUFIX** (`BL`, mai `LB`), que no és el `display_order`.

**Arriba al frontend per ENDPOINT, no per constant:**
`GET /api/v1/mesures/diccionari/` → [pom/urls.py:117](backend/fhort/pom/urls.py#L117) →
[pom/identity_views.py:55](backend/fhort/pom/identity_views.py#L55). Emet `capes`, `eixos`
(amb nom trilingüe), `instancies` agrupades per eix amb `sufix` **i `subeix` per fila**, i `regles`.
El front el llegeix per `utils/diccionariMesuresFont.js`.

## ¿HI HA DUES FONTS? — SÍ, i està DECLARADA i ACOTADA

[frontend/src/utils/capaInstancia.js:63](frontend/src/utils/capaInstancia.js#L63) exporta
`NOM_INSTANCIA`, un mapa de **12 slugs → literal anglès**. La capçalera del fitxer diu
explícitament què duplica i què no: **duplica els LITERALS** (per poder etiquetar una fila abans
que torni cap petició) i **NO duplica l'ESTRUCTURA** (de quin eix és cada slug, quin sufix
composa, quin sub-eix, en quin ordre s'ofereixen) — això només viu al backend.

**Verificat:** les 12 claus de `NOM_INSTANCIA` són exactament els 12 slugs de la BD. Zero divergència de contingut.

### 🚩 Divergència real trobada (menor, de DOC no de dada)

La capçalera de [capaInstancia.js:18-19](frontend/src/utils/capaInstancia.js#L18-L19) diu
«`pom.MeasurementInstance`, **10 files**, verificat el 05/08» i
[:75](frontend/src/utils/capaInstancia.js#L75) «**vuit posicions** i dos estats».
**Avui són 12 files i deu posicions** (`front`/`back` van entrar el 22-23/08). El MAPA sí que
les té; el COMENTARI que diu quantes n'hi ha, no. La llista canònica de slugs (`INSTANCIES`) ja
es va retirar del front a F2.2 i no s'ha tornat a escriure: la duplicació que quedava era la
xifra del comentari, no una enumeració viva.

## LECTURA

La llei de la casa («cap enumeració de domini al client») **es compleix**. El mirall de literals
és una excepció declarada, amb motiu escrit i abast acotat, i el seu contingut coincideix amb la
BD. L'única cosa desalineada és una xifra en un comentari.

---

# I2 · LES TAULES DE L'EIX D'IDENTITAT

## FET · NO SÓN 7: SÓN **12** (mesurat a `information_schema`)

`SELECT ... WHERE column_name='instancia'` dona **12 taules per tenant** (`fhort` i `los`
idèntics) i 4 a `public` (les de catàleg replicat). **Totes `character varying` i totes
`NOT NULL`** — la llei del sentinella `''` mai NULL es compleix a l'esquema, sense excepció,
igual que la del `garment`.

⚠️ Cap té `column_default` a Postgres (el default viu a Django). Efecte lateral **bo**: un
`INSERT` cru per `psql` que ometi `instancia` PETA en comptes de fabricar una fila ambigua.

| # | Taula (model) | UNIQUE real a BD | conté `instancia`? | conté `garment`? |
|---|---|---|---|---|
| 1 | `models_app_basemeasurement` ([models.py:684](backend/fhort/models_app/models.py#L684)) | `model, pom, capa, instancia, garment` | ✅ | ✅ |
| 2 | `models_app_modelgradingoverride` ([:1108](backend/fhort/models_app/models.py#L1108)) | `model, pom, size_label, capa, instancia, garment` | ✅ | ✅ |
| 3 | `models_app_sizecheckline` ([:1520](backend/fhort/models_app/models.py#L1520)) | `size_check, pom, capa, instancia, garment` | ✅ | ✅ |
| 4 | `models_app_pomplacement` ([:1693](backend/fhort/models_app/models.py#L1693)) | `item_fitxer, pom, view_slot, capa, instancia` | ✅ | ❌ |
| 5 | `models_app_measurementchangelog` ([:1002](backend/fhort/models_app/models.py#L1002)) | **cap** (append-only) | ✅ | ✅ |
| 6 | `fitting_gradedspec` ([fitting/models.py:200](backend/fhort/fitting/models.py#L200)) | `grading_version, pom, size_label, capa, instancia, garment` | ✅ | ✅ |
| 7 | `fitting_piecefittingline` ([:426](backend/fhort/fitting/models.py#L426)) | `piece_fitting, pom, size_label, capa, instancia, garment` | ✅ | ✅ |
| 8 | `fitting_pomalert` ([:116](backend/fhort/fitting/models.py#L116)) | **cap** | ✅ | ❌ |
| 9 | `pom_garmentpommap` ([pom/models.py:1016](backend/fhort/pom/models.py#L1016)) | `garment_type_item, pom, capa, instancia` | ✅ | ❌ |
| 10 | `pom_garmenttypepommap` ([:1145](backend/fhort/pom/models.py#L1145)) | `garment_type, pom, capa, instancia` | ✅ | ❌ |
| 11 | `pom_garmentgrouppommap` ([:1164](backend/fhort/pom/models.py#L1164)) | `garment_group, pom, capa, instancia` | ✅ | ❌ |
| 12 | `pom_itembasemeasurement` ([:1378](backend/fhort/pom/models.py#L1378)) | `base_set, pom, capa, instancia` | ✅ | ❌ |
| — | **`models_app_modelgradingrule`** ([:1188](backend/fhort/models_app/models.py#L1188)) | `model, pom, garment` | **❌ A POSTA** | ✅ |

**La 13a és l'excepció declarada.** `ModelGradingRule` **no travessa cap eix de germanor**:
acta de la Montse a [models_app/models.py:1208-1214](backend/fhort/models_app/models.py#L1208-L1214)
(«la sisa dreta i l'esquerra **gradúen igual**») i la distinció en una línia a
[:1230](backend/fhort/models_app/models.py#L1230): `capa`/`instancia` són **eixos de GERMANOR**
(una sola llei d'increments); `garment` és una **FRONTERA** (dues lleis possibles). Ho vigila un
pin que itera `EIXOS_DE_GERMANOR` ([services_derivacio.py:61](backend/fhort/models_app/services_derivacio.py#L61))
en comptes de comprovar noms literals: [models_app/test_instancia_comporta_cins.py:211](backend/fhort/models_app/test_instancia_comporta_cins.py#L211).
El mateix val per a `pom.GradingRule`, que **no es reobre**.

## FET · LES DUES COMPORTES JA NO HI SÓN

- Comporta d'instància (`CHECK instancia=''`): **RETIRADA** per la migració `0076` (04/08).
- Comporta de garment: **RETIRADA** per la migració `0084` (12/08).
- **Sobreviu una sola llei de domini**, i és a la BD:
  `models_app_basemeasurement_instancia_exigeix_nom` = `~Q(instancia__gt='', nom_fitxa='')`
  ([models_app/models.py:963](backend/fhort/models_app/models.py#L963)). **Present a `fhort` i a `los`.**

### 🚩 Aquesta llei viu en UNA taula de dotze

Mesurat a `pg_constraint`: el CHECK existeix **només** a `models_app_basemeasurement`.
`pom_itembasemeasurement` també té `nom_fitxa` i pot rebre germanes, i no el porta. Avui no
mossega (aquella taula té 0 files), però la llei D1 —«una germana sense nom de fitxa és un
duplicat amb aparença de dada bona»— no hi és imposada.

## ⚠️ EL PUNT CRÍTIC · AUDITORIA DELS ESCRIPTORS

Els **20 `get/get_or_create/update_or_create`** vius sobre aquestes taules (exclosos tests i
migracions), amb el lookup real:

| # | fitxer:línia | taula | lookup | unique | veredicte |
|---|---|---|---|---|---|
| 1 | [fitting/services.py:751](backend/fhort/fitting/services.py#L751) | BaseMeasurement | model, pom, capa, **instancia**, garment | 5 col | **COHERENT** |
| 2 | [models_app/services_size_check.py:238](backend/fhort/models_app/services_size_check.py#L238) | BaseMeasurement | model, pom, capa, **instancia**, garment | 5 col | **COHERENT** |
| 3 | [models_app/extraction_views.py:3372](backend/fhort/models_app/extraction_views.py#L3372) | BaseMeasurement | model, pom, capa, **instancia**, garment | 5 col | **COHERENT** |
| 4 | [models_app/views.py:3895](backend/fhort/models_app/views.py#L3895) | BaseMeasurement | model, pom, capa, **instancia**, garment | 5 col | **COHERENT** |
| 5 | [pom/wizard_views.py:459](backend/fhort/pom/wizard_views.py#L459) | BaseMeasurement | …, `instancia=''`, `garment=''` literals | 5 col | **COHERENT** (literal declarat) |
| 6 | [models_app/tech_sheet_views.py:367](backend/fhort/models_app/tech_sheet_views.py#L367) | BaseMeasurement | …, `instancia=''`, `garment=''` literals | 5 col | **COHERENT** (literal declarat) |
| 7 | [sembra_banc_paritat.py:166](backend/fhort/models_app/management/commands/sembra_banc_paritat.py#L166) | BaseMeasurement | …, `instancia=''`, `garment=''` | 5 col | **COHERENT** |
| 8 | [pom/services.py:1393](backend/fhort/pom/services.py#L1393) | GradedSpec | gv, pom, size_label, capa, **instancia**, garment | 6 col | **COHERENT** |
| 9 | [models_app/views.py:3601](backend/fhort/models_app/views.py#L3601) | ModelGradingOverride | model, pom, size_label, capa, **instancia**, **garment** | 6 col | **COHERENT** |
| 10 | [models_app/extraction_views.py:3544](backend/fhort/models_app/extraction_views.py#L3544) | ModelGradingOverride | …, `instancia=''`, **garment** | 6 col | **COHERENT** |
| 11 | [qa_set2_forats.py:143](backend/fhort/models_app/management/commands/qa_set2_forats.py#L143) | ModelGradingOverride | …, **instancia**, **garment** | 6 col | **COHERENT** |
| 12 | **[models_app/views.py:3376](backend/fhort/models_app/views.py#L3376)** | **ModelGradingOverride** | model, pom, size_label, capa, instancia — **SENSE `garment`** | **6 col** | 🚨 **BLOQUEJA GERMANES** |
| 13 | [models_app/pom_placement_views.py:173](backend/fhort/models_app/pom_placement_views.py#L173) | POMPlacement | item, pom, view_slot, capa, `instancia=''` | 5 col | **COHERENT** (literal declarat) |
| 14 | [pom/views.py:703](backend/fhort/pom/views.py#L703) | ItemBaseMeasurement | base_set, pom, capa, `instancia=''` | 4 col | **COHERENT** però CEGA (v. I3) |
| 15 | [models_app/views.py:5002](backend/fhort/models_app/views.py#L5002) | ItemBaseMeasurement | base_set, pom, capa, **instancia** | 4 col | **COHERENT** |
| 16 | [models_app/views.py:4983](backend/fhort/models_app/views.py#L4983) | GarmentPOMMap | item, pom, capa, **instancia** | 4 col | **COHERENT** |
| 17 | [load_map_inline.py:150](backend/fhort/pom/management/commands/load_map_inline.py#L150) | GarmentPOMMap | item, pom, capa, `instancia=''` | 4 col | **COHERENT** |
| 18 | [consolidate_pom_catalog.py:216](backend/fhort/pom/management/commands/consolidate_pom_catalog.py#L216) | GarmentPOMMap | item, pom, capa, `instancia=''` | 4 col | **COHERENT** |
| 19 | [pom/s10_views.py:156](backend/fhort/pom/s10_views.py#L156) | POMAlert | model, pom, capa, **instancia**, size_fitting | **cap** | **COHERENT** |
| 20 | [pom/s11_views.py:213](backend/fhort/pom/s11_views.py#L213) | POMAlert | model, pom, capa, `instancia=''` | **cap** | **AMBIGUA** (v. sota) |

### 🚨 EL FORAT · `set_size_override_view`

[models_app/views.py:3306](backend/fhort/models_app/views.py#L3306) —
`POST /api/v1/models/<id>/set-size-override/`. El seu docstring encara diu
«Idempotent per `(model, pom, size_label)`»: llenguatge d'abans dels eixos.

- La `unique` real de `ModelGradingOverride` són **6 columnes** (verificat a
  `pg_index`: `models_app_modelgradingo_model_id_pom_id_size_lab_3f92d58b_uniq`).
- El lookup en diu **5**: hi falta `garment` — tant a la lectura de `prev`
  ([:3372](backend/fhort/models_app/views.py#L3372)) com a l'`update_or_create`
  ([:3376](backend/fhort/models_app/views.py#L3376)).
- El payload acceptat és `{pom_id, size_label, valor}`: **`garment` no hi és ni pot arribar-hi**.
- El germà [:3601](backend/fhort/models_app/views.py#L3601) (ruta d'Escalat) **sí** que el passa.

`fhort` ja té **3 parells `(model, pom)` amb mesura a DUES peces**: `(1320, 904)`,
`(1379, 962)`, `(1380, 962)` — la població que exposa el defecte existeix.

---

## ⚠️ CORRECCIÓ (25/08, tram FIX F2) — AQUESTA FILA DEIA DUES COSES FALSES

Construint el banc del fix (`docs/ordres/FIX_F2_GARMENT_OVERRIDE_2026-08-25.md`) van sortir
dos errors d'aquesta secció. Tots dos mesurats; el text d'abans queda substituït per aquest.

### (a) LA RUTA ÉS JUBILADA · el defecte NO és abastable per HTTP

`set-size-override/` **no té ruta** des de D5 (21/07):
[models_app/urls.py:238](backend/fhort/models_app/urls.py#L238) la declara retirada i
[fitting/test_e1_r2_estructural.py](backend/fhort/fitting/test_e1_r2_estructural.py) és un
**guardià de frontera** que comprova que segueix sense resoldre (5 tests, verds). El gest que
aquest cens descrivia —«torna a la taula propagada i edita la mateixa talla»— **no existeix**:
aquella columna va canviar de porta a E1/B4 i ara anota una PRESA.

I el **pas 1** tampoc: `escalat/ajustar-talla/` **també** és jubilada, i és a la mateixa llista
del guardià. Cap dels dos camins del «cas concret» és viu.

La vista sobreviu com a **vehicle de bancs** ([pom/test_g6_segell.py:117](backend/fhort/pom/test_g6_segell.py#L117)),
i avui els seus únics cridadors són tests. **És la lliçó de `ftt-acta-al-codi-pot-mentir`
aplicada a aquest mateix cens: no se'n va verificar la ruta.**

### (b) EL SÍMPTOMA NO ÉS EL 500 · és mut, i n'hi ha tres

Mesurat amb el lookup revertit, el que passa de debò —per ordre de probabilitat:

| # | Condició prèvia | Sense el fix | Observat |
|---|---|---|---|
| 1 | la mare té fila, s'escriu a la **02** | `update_or_create` casa la fila de la MARE i **li reescriu el valor**. Una fila, cap error, **200 OK** | `1 != 2` |
| 2 | només la **02** té fila, s'escriu a la **mare** | li fa UPDATE **a la fila de la 02**: la mare no arriba a tenir fila | `_ovr(MARE)` és `None` |
| 3 | les **DUES** files ja escrites | `get() returned more than one ModelGradingOverride -- it returned 2!` | `MultipleObjectsReturned` |

**El 500 és el cas 3 i és el menys assolible**: aquesta porta tota sola **no pot fabricar mai**
la segona fila (el cas 1 s'hi avança). O sigui que la conseqüència real és **corrupció
silenciosa creuant peces**, no una caiguda — que és el mode de fallada dolent.

### ✅ REPARAT

Commit `48088b27` (branca `f2-garment-override`, **sense push**): el `garment` entra als quatre
punts del camí (lookup, `prev`, `MeasurementChangeLog` i la lectura de retorn del `GradedSpec`,
que amb 3 columnes de 6 també podia servir el valor d'una altra peça amb un 200 OK). Banc
`models_app/test_f2_garment_override.py`, 13 tests, verificat VERMELL sense el fix. Gate: 111
tests OK. **La fila 10 (`MeasurementBaseGrid`) segueix oberta i intacta.**

### AMBIGUA · `s11_views.py:213`

`POMAlert` **no té cap unique**. L'`update_or_create` amb `instancia=''` literal no pot petar
per clau, però tampoc pot alertar d'una germana: sempre escriurà a la fila de la instància única.
El propi codi ho declara obert amb 🚩 a [pom/s11_views.py:211](backend/fhort/pom/s11_views.py#L211).
El germà `s10_views.py:156` sí que copia els eixos de la línia. Sense unique, si mai hi hagués
dues files coincidents, `update_or_create` peta amb `MultipleObjectsReturned` — no és el cas avui
(0 files a tots dos tenants).

---

# I3 · LES PORTES D'ASSIGNACIÓ

## FET · La porta d'API: `GarmentPOMMapViewSet`

[pom/views.py:473](backend/fhort/pom/views.py#L473). Lectura `IsAuthenticated`, escriptura gated
`CONFIGURE`.

**¿Quina consulta valida la duplicitat?** No n'hi ha cap d'escrita a mà: la fa el
`UniqueTogetherValidator` que **DRF munta sol** sobre la clau de 4 columnes
`(garment_type_item, pom, capa, instancia)` — i només la munta perquè el serializer declara
`capa` i `instancia` amb `default` explícit:
[pom/serializers.py:662-663](backend/fhort/pom/serializers.py#L662-L663), amb l'acta de per què
el `default` no és decoratiu a [:653-661](backend/fhort/pom/serializers.py#L653-L661).
Tots dos són a `Meta.fields` ([:744](backend/fhort/pom/serializers.py#L744)).

**⇒ Filtra per `instancia`. NO filtra només per `(pom, garment_type_item)`.**

### ¿Es pot assignar `left` i `right` del mateix POM al mateix item?

**SÍ per l'API.** La consulta que ho demostra és la `unique` real, mesurada a `pg_index`:

```
pom_garmentpommap_garment_type_item_id_pom_e89888d8_uniq
  → garment_type_item_id, pom_id, capa, instancia
```

`('item-7','POM-3','exterior','left')` i `('item-7','POM-3','exterior','right')` són dues claus
distintes: el validador de DRF no en veu cap col·lisió i les dues altes tornen **201**.

Hi ha, a més, una **segona porta de llei** que sí que jutja el valor:
`validate_instancia` ([pom/serializers.py:747](backend/fhort/pom/serializers.py#L747)) crida
`MeasurementInstance.error_de_combinacio` ([pom/models.py:386](backend/fhort/pom/models.py#L386)):
fins a UNA etiqueta per eix, i a la POSICIÓ fins a una per SUB-EIX. `left-relaxed` passa;
`front-back` i `left-right` es rebutgen amb un missatge que diu **quines dues etiquetes es
barallen**. Un slug que el diccionari no conté **no es jutja** (un tenant pot crear-se la seva).

## FET · Les portes de PANTALLA — n'hi ha dues vives, i NO es comporten igual

`grep` dels consumidors de `garmentPomMaps` ([frontend/src/api/endpoints.js:782](frontend/src/api/endpoints.js#L782)):

### ✅ SANA — `TaulaPOMsCataleg.jsx` (la porta de la formació)

Renderitzada per [pages/CatalegPecesItem.jsx:210](frontend/src/pages/CatalegPecesItem.jsx#L210).

- `afegeix(pom, eixos)` ([TaulaPOMsCataleg.jsx:162](frontend/src/components/cataleg/TaulaPOMsCataleg.jsx#L162))
  accepta `capa` i `instancia`.
- **Dedup per la identitat SENCERA**: `if (prev.some(r => clau(r) === clau(nova)))`
  ([:170](frontend/src/components/cataleg/TaulaPOMsCataleg.jsx#L170)) — no per `pom_id`.
- El desat envia els dos eixos:
  [:187-188](frontend/src/components/cataleg/TaulaPOMsCataleg.jsx#L187-L188).
- Ordre del desat pensat: **les baixes primer**, perquè una identitat que se'n va alliberi la
  clau abans que una altra la reclami ([:184](frontend/src/components/cataleg/TaulaPOMsCataleg.jsx#L184)).
- Tecles: `L` germana de capa · `I` grups d'instància ([:204](frontend/src/components/cataleg/TaulaPOMsCataleg.jsx#L204)).

**Les germanes conviuen a la mateixa vista**: una fila per identitat, i el llistat de l'API va
ordenat per `('garment_type_item','ordre')` ([pom/views.py:501](backend/fhort/pom/views.py#L501)),
que no barreja res.

### 🚨 LIMITA GERMANES — `MeasurementBaseGrid.jsx`

Renderitzada per [pages/ItemAuthoring.jsx](frontend/src/pages/ItemAuthoring.jsx) i
[components/BaseSetPanel/BaseSetPanel.jsx:316](frontend/src/components/BaseSetPanel/BaseSetPanel.jsx#L316).

Tres defectes encadenats, tots per **indexar per `pom` pelat**:

1. **[MeasurementBaseGrid.jsx:66-67](frontend/src/components/MeasurementBaseGrid/MeasurementBaseGrid.jsx#L66-L67)**
   ```js
   const valByPom = {}
   vals.forEach(v => { valByPom[v.pom] = v })
   ```
   Les files es pinten des de `GarmentPOMMap` (que **sí** distingeix germanes), però el valor
   es lliga per `pom` sol. Amb `left` i `right` vius, **l'últim iterat guanya**: les dues files
   ensenyen el MATEIX valor i el MATEIX `ibmId`, i el de l'altra germana no es veu enlloc.
2. **[:164](frontend/src/components/MeasurementBaseGrid/MeasurementBaseGrid.jsx#L164)** — l'alta
   de pertinença envia només `{garment_type_item, pom, ordre}`: cau als `default` del serializer
   (`'exterior'`, `''`). **Aquesta graella no pot crear una germana.**
3. **[:170](frontend/src/components/MeasurementBaseGrid/MeasurementBaseGrid.jsx#L170)** —
   `itemBaseMeasurements.upsert` tampoc envia eixos, i el backend
   ([pom/views.py:703](backend/fhort/pom/views.py#L703)) **hardcodeja `instancia=''`**. Les dues
   files desen sobre la fila `''`, que no és cap de les dues.

**I el pitjor és l'esborrat**: `if (r.ibmId) await itemBaseMeasurements.remove(r.ibmId)`
([:158](frontend/src/components/MeasurementBaseGrid/MeasurementBaseGrid.jsx#L158)) — com que les
dues germanes comparteixen `ibmId`, **treure la dreta esborra el valor de l'esquerra**.

### ⚪ POMBrowser ASSIGN — el defecte hi és, la porta NO

[POMBrowser.jsx:138](frontend/src/components/POMBrowser/POMBrowser.jsx#L138)
`const mappedPomIds = new Set(poms.map(p => p.pom_id))` i
[:318](frontend/src/components/POMBrowser/POMBrowser.jsx#L318) `const already = mappedPomIds.has(res.id)`:
amb una germana ja assignada, el POM surt **esmorteït i no clicable**
([:320](frontend/src/components/POMBrowser/POMBrowser.jsx#L320)) — i `assignAdd`
([:156](frontend/src/components/POMBrowser/POMBrowser.jsx#L156)) tampoc envia eixos.

**Però és codi mort.** [POMCataleg.jsx:298-303](frontend/src/components/POMCataleg/POMCataleg.jsx#L298-L303)
ho sentencia i ho justifica: U1 (07/08) li va treure la pestanya, `/poms` renderitza una altra
pantalla, i **del seu `export default` no en queda cap importador** — verificat amb `grep`, només
en surten dos exports amb nom cap a `POMCatalogue`. ⚠️ L'acta de
[pages/POMs.jsx:6](frontend/src/pages/POMs.jsx#L6) encara diu «el consumeixen 5 pantalles més»
i és FALS.

## FET · Els seeders P1–P5 (només lectura de com resolen `instancia`)

Cap executat. Tots tres resolen la instància **amb literal declarat, no implícit**:
`load_map_inline.py:150`, `consolidate_pom_catalog.py:216` i `sembra_banc_paritat.py:166`
escriuen `instancia=''` amb el comentari que ho declara. **Cap sembrador fabrica germanes**,
i cap n'esborra (llei de catàleg: `update_or_create`, mai `delete`).

---

# I4 · SUPERFÍCIES DE MESURA I GRADING

## FET · La clau de cel·la porta `instancia` a TOTES les superfícies de valor

| superfície | clau | ¿@left i @right a la mateixa taula? |
|---|---|---|
| `BaseMeasurement` | `model, pom, capa, instancia, garment` | **SÍ** — dues files |
| `ModelGradingOverride` | +`size_label` | **SÍ** |
| `GradedSpec` (sortida del motor) | `grading_version, pom, size_label, capa, instancia, garment` | **SÍ** |
| `PieceFittingLine` | `piece_fitting, pom, size_label, capa, instancia, garment` | **SÍ** |
| `SizeCheckLine` | `size_check, pom, capa, instancia, garment` | **SÍ** |
| `MeasurementChangeLog` | append-only, però **copia els 3 eixos** | **SÍ** |

**La clau de sortida del motor PORTA `instancia`** (I4, 3a pregunta): sí — `GradedSpec`, i
l'escriptor [pom/services.py:1393](backend/fhort/pom/services.py#L1393) la posa **al lookup**,
no als defaults, amb l'acta de per què ([:1397-1400](backend/fhort/pom/services.py#L1397-L1400)).

El `MeasurementChangeLog` **copia i no endevina**: [models_app/signals.py:283](backend/fhort/models_app/signals.py#L283)
i [:341](backend/fhort/models_app/signals.py#L341) prenen `capa`/`instancia`/`garment` de la
`instance`, amb l'argument escrit que en una taula append-only sense unicitat una fila mal
atribuïda **no es pot corregir després**.

La derivació entre germanes és coherent amb la llei: `germanes_de`
([services_derivacio.py](backend/fhort/models_app/services_derivacio.py)) filtra per
`(model, pom, GARMENT)` iguals i **exactament un eix de germanor diferent** — el `garment` a la
igualtat, mai a la `Q` dels eixos.

## 🚨 FET · SÍ que hi ha una ruta de grading que resol SENSE `instancia`

[pom/services.py:882](backend/fhort/pom/services.py#L882) `_load_grading_rules_per_garment`
→ `{(pom_id, garment): regla}`, i
[pom/services.py:951](backend/fhort/pom/services.py#L951) `_regla_de(rules, pom_id, garment)`,
cridada des de [:255](backend/fhort/pom/services.py#L255) i [:511](backend/fhort/pom/services.py#L511).

El comentari de [:883-888](backend/fhort/pom/services.py#L883-L888) ho declara i diu que està
**verificat contra `information_schema`**: cap de les dues taules de regla té les columnes.
Ho he re-mesurat avui: `models_app_modelgradingrule` UNIQUE = `(model_id, pom_id, garment)`, i no
té columna `instancia`. **Confirmat: el motor busca la regla amb el `pom_id` EXTRET de la
identitat, no amb la identitat sencera.**

**Això NO és un bug: és la decisió de la Montse** (les germanes gradúen igual). Però és
exactament el mecanisme pel qual una corba es podria barrejar si algú posés al *segon* eix una
cosa que no hi va.

## 🚩 I aquí el brief i el codi no diuen el mateix · @girth

**El brief diu:** «@girth (llei: contorn = **instància** pròpia quan hi ha ½ ample; mai es
gradua amb la corba del base)».

**El codi diu una altra cosa:** `@girth` **no és una instància**. No hi ha cap slug `girth` al
diccionari (12 files, cap). Els contorns són **POMs propis del catàleg v5**:
[sembra_cataleg_sistema.py:20-23](backend/fhort/pom/management/commands/sembra_cataleg_sistema.py#L20-L23)
— els 4 INACTIU (`A1` chest girth, `A2` underbust, `C2` hip, `D11` leg opening), que entren com a
vocabulari **i sense cap regla de graduació**.

**On s'imposa la llei:** enlloc, com a guard. S'imposa **per absència i es MESURA**:
`LleiGirthTest` ([pom/test_sembra_v5.py:531](backend/fhort/pom/test_sembra_v5.py#L531)) corre el
tram sencer i comprova que `GradingRule` **no es mou ni una fila**; a l'assaig sobre PROD el hash
del bloc `regles` va sortir idèntic abans i després (`e176e5e343783fc5…`,
[SEMBRA_V5_FASE_A_2026-08-23.md:178](docs/ordres/SEMBRA_V5_FASE_A_2026-08-23.md#L178)).

**La conseqüència, i és la resposta a la pregunta del brief:**
avui **el contorn NO pot barrejar la seva corba amb la del base**, però *no perquè el motor el
protegeixi*: perquè és un POM diferent, i `(pom_id, garment)` ja els separa. El dia que algú
modeli un contorn com a **instància** del POM de ½ ample —que és el que el brief descriu i que
el vocabulari, obert a instàncies de tenant, **permetria**— `_regla_de` li donaria **la regla del
base**, en silenci i sense cap log. La llei @girth viu al CATÀLEG; el motor no en sap res.

---

# I5 · DADES VIVES (staging)

## FET · Recompte per taula · `instancia <> ''`

| taula | files (fhort) | amb instància | slugs distints | files (los) |
|---|---|---|---|---|
| `fitting_gradedspec` | 1 622 | **159** | 9 | 0 |
| `fitting_piecefittingline` | 864 | **169** | 9 | 0 |
| `models_app_measurementchangelog` | 575 | **33** | 9 | 0 |
| `models_app_basemeasurement` | 556 | **21** | 9 | 0 |
| `models_app_sizecheckline` | 28 | **5** | 4 | 0 |
| `models_app_modelgradingoverride` | 2 | **2** | 1 | 0 |
| `fitting_pomalert` | 0 | 0 | — | 0 |
| `models_app_pomplacement` | 0 | 0 | — | 0 |
| **`pom_garmentpommap`** | **0** | **0** | — | 0 |
| **`pom_garmenttypepommap`** | **0** | **0** | — | 0 |
| **`pom_garmentgrouppommap`** | **0** | **0** | — | 0 |
| **`pom_itembasemeasurement`** | **0** | **0** | — | 0 |

`public`: les 4 taules de pertinença també a **0**.

### 🚨 El fet que més importa per a demà

**Les QUATRE taules de PERTINENÇA estan BUIDES als tres schemes.** L'eix d'instància està
exercitat de debò a la cadena de MESURA (159 + 169 + 33 + 21 files), i **no ho està gens a la
cadena d'ASSIGNACIÓ**, que és justament el gest de la formació. Tot el que diu I3 sobre les
portes d'assignació és lectura de codi contra **població zero**.

## FET · Slugs realment en ús (`fhort`) — cap `left`, cap `right`

`BaseMeasurement`: `relaxed` 5 · `extended` 4 · `top` 3 · `bottom` 3 · `waistband_seam` 2 ·
`cf` 1 · `cb` 1 · `front` 1 · `back` 1.
`GradedSpec`: `relaxed` 46 · `extended` 31 · `bottom` 25 · `top` 25 · `waistband_seam` 10 ·
`front` 6 · `back` 6 · `cf` 5 · `cb` 5.

**El sub-eix LATERAL (`left`/`right`) no té ni una sola fila viva.** El sub-eix CARA
(`front`/`back`) sí, però amb 1 fila base. I **cap slug compost** (cap amb guió): la
composició `left-relaxed` que el sistema sap escriure i desmuntar **no s'ha exercit mai amb dades**.

## FET · Germanes reals (grup = clau única MENYS `instancia`)

| taula | grups amb germanes | màx. germanes en un grup |
|---|---|---|
| `fitting_gradedspec` | **56** | 3 |
| `fitting_piecefittingline` | **56** | 3 |
| `models_app_basemeasurement` | **7** | 3 |
| `models_app_sizecheckline` | **2** | 2 |
| `models_app_modelgradingoverride` | 0 | 1 |

## FET · ÒRFENES: **ZERO**

Descomposats tots els valors per guions i creuats amb `pom_measurementinstance`: els **9** trams
en ús són tots vocabulari canònic. Cap òrfena, cap slug inventat, cap residu.

## FET · L'eix GARMENT (context del forat d'I2)

`models_app_basemeasurement` a `fhort`: `garment=''` → 547 files · `garment='02'` → **9 files**.
**3 parells `(model, pom)` viuen a dues peces**: `(1320, 904)` · `(1379, 962)` · `(1380, 962)`.
Tots amb `instancia=''` — els dos eixos encara no s'han creuat en dades.

## LES CONSULTES, PER CÓRRER-LES TAL QUAL A PROD (pas 1-bis, read-only)

```sql
-- ═══ 0 · VOCABULARI VIU (esperat: 12 files idèntiques a cada schema) ═══
SELECT slug, eix, sufix, is_system, origen, display_order
FROM pom_measurementinstance ORDER BY eix, display_order;   -- amb search_path al schema

-- ═══ 1 · EL CENS D'ESQUEMA: quines taules porten l'eix (esperat: 12/tenant) ═══
SELECT table_schema, table_name, is_nullable, column_default
FROM information_schema.columns WHERE column_name = 'instancia'
ORDER BY table_schema, table_name;

-- ═══ 2 · LES UNIQUE REALS (¿inclouen instancia? ¿i garment?) ═══
SELECT c.relname AS taula, i.relname AS index,
       (SELECT string_agg(a.attname, ', ' ORDER BY k.ord)
          FROM unnest(ix.indkey) WITH ORDINALITY AS k(attnum, ord)
          JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum) AS columnes
FROM pg_index ix
JOIN pg_class c ON c.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = :schema AND ix.indisunique
  AND c.relname IN ('fitting_gradedspec','fitting_piecefittingline','fitting_pomalert',
    'models_app_basemeasurement','models_app_measurementchangelog','models_app_modelgradingoverride',
    'models_app_pomplacement','models_app_sizecheckline','pom_garmentgrouppommap',
    'pom_garmentpommap','pom_garmenttypepommap','pom_itembasemeasurement','models_app_modelgradingrule')
ORDER BY c.relname, i.relname;

-- ═══ 3 · RECOMPTE amb instancia <> '' (repetir el bloc per cada schema) ═══
SELECT 'models_app_basemeasurement' AS taula, count(*) AS files,
       count(*) FILTER (WHERE instancia <> '') AS amb_instancia,
       count(DISTINCT instancia) FILTER (WHERE instancia <> '') AS slugs
FROM fhort.models_app_basemeasurement
UNION ALL SELECT 'fitting_gradedspec', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.fitting_gradedspec
UNION ALL SELECT 'fitting_piecefittingline', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.fitting_piecefittingline
UNION ALL SELECT 'models_app_measurementchangelog', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.models_app_measurementchangelog
UNION ALL SELECT 'models_app_modelgradingoverride', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.models_app_modelgradingoverride
UNION ALL SELECT 'models_app_sizecheckline', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.models_app_sizecheckline
UNION ALL SELECT 'models_app_pomplacement', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.models_app_pomplacement
UNION ALL SELECT 'fitting_pomalert', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.fitting_pomalert
UNION ALL SELECT 'pom_garmentpommap', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.pom_garmentpommap
UNION ALL SELECT 'pom_garmenttypepommap', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.pom_garmenttypepommap
UNION ALL SELECT 'pom_garmentgrouppommap', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.pom_garmentgrouppommap
UNION ALL SELECT 'pom_itembasemeasurement', count(*), count(*) FILTER (WHERE instancia<>''),
       count(DISTINCT instancia) FILTER (WHERE instancia<>'') FROM fhort.pom_itembasemeasurement
ORDER BY 1;

-- ═══ 4 · PARELLES GERMANES REALS (grup = clau única MENYS instancia) ═══
WITH g AS (
  SELECT 'models_app_basemeasurement' t, count(DISTINCT instancia) n
    FROM fhort.models_app_basemeasurement GROUP BY model_id, pom_id, capa, garment
  UNION ALL SELECT 'models_app_modelgradingoverride', count(DISTINCT instancia)
    FROM fhort.models_app_modelgradingoverride GROUP BY model_id, pom_id, size_label, capa, garment
  UNION ALL SELECT 'models_app_sizecheckline', count(DISTINCT instancia)
    FROM fhort.models_app_sizecheckline GROUP BY size_check_id, pom_id, capa, garment
  UNION ALL SELECT 'fitting_gradedspec', count(DISTINCT instancia)
    FROM fhort.fitting_gradedspec GROUP BY grading_version_id, pom_id, size_label, capa, garment
  UNION ALL SELECT 'fitting_piecefittingline', count(DISTINCT instancia)
    FROM fhort.fitting_piecefittingline GROUP BY piece_fitting_id, pom_id, size_label, capa, garment
  UNION ALL SELECT 'pom_garmentpommap', count(DISTINCT instancia)
    FROM fhort.pom_garmentpommap GROUP BY garment_type_item_id, pom_id, capa
  UNION ALL SELECT 'pom_itembasemeasurement', count(DISTINCT instancia)
    FROM fhort.pom_itembasemeasurement GROUP BY base_set_id, pom_id, capa
)
SELECT t AS taula, count(*) FILTER (WHERE n > 1) AS grups_amb_germanes,
       max(n) AS max_germanes_en_un_grup
FROM g GROUP BY t ORDER BY 1;

-- ═══ 5 · ÒRFENES: trams FORA del vocabulari (esperat: cap fila amb al_vocabulari = f) ═══
WITH usos AS (
  SELECT instancia FROM fhort.models_app_basemeasurement      WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.fitting_gradedspec              WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.fitting_piecefittingline        WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.fitting_pomalert                WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.models_app_modelgradingoverride WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.models_app_sizecheckline        WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.models_app_measurementchangelog WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.models_app_pomplacement         WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.pom_garmentpommap               WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.pom_garmenttypepommap           WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.pom_garmentgrouppommap          WHERE instancia <> ''
  UNION ALL SELECT instancia FROM fhort.pom_itembasemeasurement         WHERE instancia <> ''
), trams AS (SELECT DISTINCT unnest(string_to_array(instancia, '-')) AS tram FROM usos)
SELECT tram, (tram IN (SELECT slug FROM fhort.pom_measurementinstance)) AS al_vocabulari
FROM trams ORDER BY 2, 1;

-- ═══ 6 · L'EXPOSICIÓ DEL FORAT DE `set_size_override_view` ═══
--  (a) parells (model,pom) que ja viuen a dues peces — el banc del defecte
SELECT model_id, pom_id, string_agg(DISTINCT '['||garment||']', ' ') AS garments
FROM fhort.models_app_basemeasurement GROUP BY 1,2 HAVING count(DISTINCT garment) > 1;
--  (b) el defecte ARMAT: si torna una sola fila, l'endpoint ja pot donar 500
SELECT model_id, pom_id, size_label, count(DISTINCT garment) AS n_garments
FROM fhort.models_app_modelgradingoverride
GROUP BY 1,2,3 HAVING count(DISTINCT garment) > 1;

-- ═══ 7 · LA LLEI D1 (instància sense nom de fitxa) — esperat: 0 files ═══
SELECT count(*) FROM fhort.models_app_basemeasurement
WHERE instancia <> '' AND nom_fitxa = '';
SELECT n.nspname, c.relname, con.conname FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE con.contype = 'c' AND con.conname LIKE '%instancia%' ORDER BY 1, 2;
```

---

# I6 · VEREDICTE

| # | Regla / camí | Veredicte | El cas concret |
|---|---|---|---|
| 1 | Vocabulari `MeasurementInstance` + `/mesures/diccionari/` | **SANA** | 12 files idèntiques als 3 schemes; l'estructura no es duplica al front |
| 2 | Mirall de literals `NOM_INSTANCIA` | **SANA** | 12 claus = 12 slugs. Només el COMENTARI diu «10 files / vuit posicions» |
| 3 | `''` mai NULL, als 12 `NOT NULL` | **SANA** | `information_schema`: 12/12 `NOT NULL`, cap default a BD |
| 4 | `ModelGradingRule` sense `capa`/`instancia` | **SANA** (decisió) | Acta Montse + pin que itera `EIXOS_DE_GERMANOR` |
| 5 | Els 7 escriptors de `BaseMeasurement` | **SANA** | Tots porten `instancia` al lookup; els literals van declarats |
| 6 | `GradedSpec` / `PieceFittingLine` / `SizeCheckLine` / changelog | **SANA** | Clau de 6 columnes al lookup; el log copia i no endevina |
| 7 | `GarmentPOMMapViewSet` + `validate_instancia` | **SANA** | `left` i `right` al mateix item = dues claus → 201 i 201 |
| 8 | `TaulaPOMsCataleg.jsx` | **SANA** | Dedup per identitat sencera; envia els dos eixos; baixes abans que altes |
| 9 | **`set_size_override_view` ([views.py:3376](backend/fhort/models_app/views.py#L3376))** | ✅ **REPARAT** (`48088b27`) — era **LIMITA GERMANES** (eix GARMENT) | Lookup de 5 col. contra unique de 6. ⚠️ **La ruta és JUBILADA**: no era abastable per HTTP, i el símptoma no era el 500 sinó una trepitjada MUDA que creua peces — v. la correcció a §I2 |
| 10 | **`MeasurementBaseGrid.jsx` + `upsert` de `pom/views.py:703`** | 🚨 **LIMITA GERMANES** (eix INSTÀNCIA) | `valByPom[v.pom]` ignora els eixos: amb `left`+`right` les dues files ensenyen el mateix valor i el mateix `ibmId`; desar-les les col·lapsa a la fila `''`, i **treure'n una esborra el valor de l'altra** |
| 11 | `_regla_de` / `@girth` | **AMBIGUA** | El motor resol per `(pom, garment)`. Avui el contorn és un POM propi i no es barreja; modelat com a INSTÀNCIA —que és com el brief el descriu i que el vocabulari permetria— heretaria la corba del base **en silenci** |
| 12 | `POMAlert` via `s11_views.py:213` | **AMBIGUA** | Literal `instancia=''`: no pot alertar d'una germana. 🚩 ja declarat al codi. 0 files vives |
| 13 | `instancia_exigeix_nom` en 1 taula de 12 | **AMBIGUA** | `pom_itembasemeasurement` té `nom_fitxa` i pot rebre germanes sense que la llei D1 hi mossegui (0 files avui) |
| 14 | `POMBrowser` ASSIGN | **⚪ NO APLICA** | El defecte hi és (`already` per `pom_id` sol) però és **codi mort**: cap importador del `export default` |

## 🚩 NO S'HA REPARAT RES

Cap dels dos **LIMITA GERMANES** s'ha tocat: el tren de demà surt amb el codi del gate, i la
reparació es decideix amb l'Agus.

## Per a la formació de demà — el gest que cal esquivar

1. **Assignar POMs (inclosos `left`/`right`): fer-ho des del catàleg de peces**
   (`CatalegPecesItem` → `TaulaPOMsCataleg`). Aquesta porta és sana de dalt a baix.
2. **NO fer-ho des de la graella de l'ItemAuthoring / BaseSetPanel** (`MeasurementBaseGrid`)
   si hi ha germanes: no en sap crear cap, i esborrar-hi una fila s'endú el valor de l'altra.
3. **No editar una talla no-base per la taula propagada en un model amb dues peces**
   (els tres parells d'I5) — és l'única manera coneguda d'arribar al 500.
4. Tenir present que a PROD **la pertinença pot no estar buida** com aquí: el pas 1-bis
   (consultes de dalt) s'ha de córrer **abans** de la formació, no després.
