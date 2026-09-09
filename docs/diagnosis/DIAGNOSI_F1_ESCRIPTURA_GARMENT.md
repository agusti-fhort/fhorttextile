# DIAGNOSI F1 — L'ESCRIPTURA PER GARMENT

> **Patró A · read-only.** Cap escriptura a cap BD, cap fitxer de codi modificat.
> Data: 2026-08-17 · Branca `dev` (`4e9e3bbf`) · Tenant de referència: `fhort`.
> Model viu de referència: **1379 «RUFFLES» (BRW-FW26-0002)** — NO s'hi ha sembrat res.
> Totes les afirmacions porten `fitxer:línia`. Les xifres de BD surten de `SELECT` purs.

---

## 0 · VEREDICTE EN UNA LÍNIA

L'eix `garment` **ja viu a totes les taules i el serveixen totes les lectures**. El que falla
és la **JUNTA**: la fila el porta, i es perd al lloc de la crida. Hi ha **6 write-paths** que
el deixen caure, i **un d'ells (el serializer de `BaseMeasurement`) no el pot rebre ni que
s'enviés** — la creació d'una fila per peça és, avui, impossible per API.

**Cap migració és necessària.** Les 4 taules de destí tenen la columna i la clau única.

---

## 0-bis · PREMISSES DEL BRIEF QUE CAL CONTRADIR

| Premissa del brief | Estat | Evidència |
|---|---|---|
| «Sospita front: `onNova`/`onParteix`/`onDesfaInstancia` a `CheckMeasureEditor.jsx:646`» | ⚠️ **línies mogudes** | `onParteix` és a [:632](../../frontend/src/components/model/CheckMeasureEditor.jsx#L632), `onDesfaInstancia` a [:649](../../frontend/src/components/model/CheckMeasureEditor.jsx#L649), `onNova` a [:654](../../frontend/src/components/model/CheckMeasureEditor.jsx#L654). La :646 és comentari. |
| «Sospita backend: `endpoints.js:152` → `views.py:3346`» | ⚠️ **desplaçat** | `escalatAjustarTalla` és a [endpoints.js:156-158](../../frontend/src/api/endpoints.js#L156-L158); `views.py:3346` és correcte però **NO és on peta**. |
| «El 500 de l'Escalat ve de `CheckMeasureEditor`» | ❌ **FALS** | `escalatAjustarTalla` té **un sol cridador** i no és aquell component: [`PropagatedEditor.jsx:82`](../../frontend/src/pages/PropagatedEditor.jsx#L82) (`grep -rn "escalatAjustarTalla" frontend/src` → 1 crida). L'Escalat i Mesures són **dues pantalles**, i per tant **dos censos**. |
| «F1 és l'ESCRIPTURA de creació/desfeta» | ⚠️ **abast més gran** | La creació i la desfeta hi són, però el 500 mesurat és a l'**ajust de valor** (`_write_base`), que no és cap de les dues. |

---

## Q1 · CENS D'ESCRIPTURES

### Q1.a — Pantalla MESURES (`CheckMeasureEditor` + `EditableTable`)

Files servides per `base-stages`, que **sí** emet l'eix ([views.py:4016](../../backend/fhort/models_app/views.py#L4016)),
i repartides per contenidor amb `filesDeLaPeca` ([CheckMeasureEditor.jsx:721-722](../../frontend/src/components/model/CheckMeasureEditor.jsx#L721-L722)).

| # | Handler | Origen del gest | Endpoint | `garment`? |
|---|---|---|---|---|
| 1 | `presaPortes.onNova` [:654-660](../../frontend/src/components/model/CheckMeasureEditor.jsx#L654-L660) | `handleAddRow` [EditableTable.jsx:362](../../frontend/src/components/EditableTable/EditableTable.jsx#L362) · `germanaCapaRapida` [:482-484](../../frontend/src/components/EditableTable/EditableTable.jsx#L482-L484) | `POST /api/v1/base-measurements/` | 🔴 **NO** |
| 2 | `presaPortes.onParteix` — germana nova [:635-639](../../frontend/src/components/model/CheckMeasureEditor.jsx#L635-L639) | `aplicaInstancia` [EditableTable.jsx:595](../../frontend/src/components/EditableTable/EditableTable.jsx#L595) | `POST /api/v1/base-measurements/` | 🔴 **NO** |
| 3 | `presaPortes.onParteix` — mare reescrita [:634](../../frontend/src/components/model/CheckMeasureEditor.jsx#L634) | idem | `PATCH base-measurements/<id>/` | ✅ per PK |
| 4 | `presaPortes.onDesfaInstancia` — **poda de germanes** [:649-651](../../frontend/src/components/model/CheckMeasureEditor.jsx#L649-L651) | `aplicaDesfer` [EditableTable.jsx:687](../../frontend/src/components/EditableTable/EditableTable.jsx#L687) | `POST models/<id>/pom/<pom>/desactivar/` | 🔴 **NO — literal de 2 eixos · DESTRUCTIU** |
| 5 | `presaPortes.onDesfaInstancia` — mare [:652](../../frontend/src/components/model/CheckMeasureEditor.jsx#L652) | idem | `PATCH base-measurements/<id>/` | ✅ per PK |
| 6 | `presaPortes.onTreu` → `onPodar` [:661](../../frontend/src/components/model/CheckMeasureEditor.jsx#L661) → [:571-583](../../frontend/src/components/model/CheckMeasureEditor.jsx#L571-L583) | ✕ de fila | `desactivar/` | ✅ **SÍ** (`eixosDeLaFila`, F5+) |
| 7 | `onPodar` des de `MeasureGrid` [:580](../../frontend/src/components/model/CheckMeasureEditor.jsx#L580) | ✕ de la graella | `desactivar/` | ✅ **SÍ** |
| 8 | `presaPortes.onIdentitat` [:627](../../frontend/src/components/model/CheckMeasureEditor.jsx#L627) | `handleCapa` [:420](../../frontend/src/components/EditableTable/EditableTable.jsx#L420) · cel·la [:256](../../frontend/src/components/EditableTable/EditableTable.jsx#L256) | `PATCH base-measurements/<id>/` | ✅ per PK |
| 9 | `presaPortes.onValor` [:626](../../frontend/src/components/model/CheckMeasureEditor.jsx#L626) | carril de valors | `PATCH size-check-lines/<id>/` | ✅ per PK |
| 10 | `onReordena` [:662](../../frontend/src/components/model/CheckMeasureEditor.jsx#L662) · `onReorder` [:342-344](../../frontend/src/components/model/CheckMeasureEditor.jsx#L342-L344) | drag | `POST base-measurements/reorder/` | ✅ `ids` explícits |
| 11 | `checkSource.makeOnSave` [:328](../../frontend/src/components/model/CheckMeasureEditor.jsx#L328) | cel·la Real | `PATCH size-check-lines/<id>/` | ✅ per PK |
| 12 | `onNomSave` / `onNomsSave` [:331-340](../../frontend/src/components/model/CheckMeasureEditor.jsx#L331-L340) · `handleBateig` [EditableTable.jsx:341](../../frontend/src/components/EditableTable/EditableTable.jsx#L341) | bateig | `PATCH base-measurements/<id>[/noms/]` | ✅ per PK |
| 13 | `DecisioNotaCell` [:69-79](../../frontend/src/components/model/CheckMeasureEditor.jsx#L69-L79) | decisió/nota | `PATCH size-check-lines/<id>/` | ✅ per PK |
| 14 | `RegleEditCell.save` → `models.setPomRule` [:191](../../frontend/src/components/model/CheckMeasureEditor.jsx#L191) | Δ / break | `POST models/<id>/pom/<pom>/regim/` | 🔴 **NO** (acta pròpia a [:184-190](../../frontend/src/components/model/CheckMeasureEditor.jsx#L184-L190)) |
| 15 | `doResolve` → `sizeChecks.resolve` [:528](../../frontend/src/components/model/CheckMeasureEditor.jsx#L528) | Desar el check | `POST size-checks/<id>/resolve/` | ✅ backend garment-aware ([services_size_check.py:238-242](../../backend/fhort/models_app/services_size_check.py#L238-L242)) |

### Q1.b — Pantalla ESCALAT (`PropagatedEditor`), on viu el 500

| # | Handler | Fitxer:línia | Endpoint | `garment`? |
|---|---|---|---|---|
| 16 | `desa` → `escalatAjustarTalla` | [PropagatedEditor.jsx:82-83](../../frontend/src/pages/PropagatedEditor.jsx#L82-L83) | `POST models/<id>/escalat/ajustar-talla/` | 🔴 **NO — i el té a la mà** |
| 17 | `onRegimChange` → `setPomRegim` | [PropagatedEditor.jsx:150](../../frontend/src/pages/PropagatedEditor.jsx#L150) | `POST models/<id>/pom/<pom>/regim/` | 🔴 **NO** |
| 18 | `onCrearNovaVersio` → `generarGrading` | [PropagatedEditor.jsx:141](../../frontend/src/pages/PropagatedEditor.jsx#L141) | `POST models/<id>/generar-grading/` | ✅ N/A (acte de model sencer) |

### 🚨 LA TROBALLA DE FORMA DEL CENS

La #16 és la **junta pura**: `perLinia` **SÍ que carrega l'eix** —
`garment: r.garment` a [PropagatedEditor.jsx:62](../../frontend/src/pages/PropagatedEditor.jsx#L62) — i la
crida de 20 línies més avall n'envia **dos de tres**. La dada hi és; la porta no la passa.

La #4 és el **calc del bug F5+ que ja es va tancar**. El comentari de `onPodar` diu, literalment,
que els tres eixos «surten d'un sol lloc (`eixosDeLaFila`), **no d'un literal escrit aquí**»
([:579](../../frontend/src/components/model/CheckMeasureEditor.jsx#L579)) — i **70 línies més avall
hi ha exactament aquest literal** ([:651](../../frontend/src/components/model/CheckMeasureEditor.jsx#L651)):
`{ capa: g.capa, instancia: g.instancia }`. Desfer una partició des del contenidor de la 02 **poda
la fila de la MARE**. És el mateix mode de fallada, a la porta germana, i el guard que el va tancar
no hi arriba perquè no és el mateix `.then()`.

---

## Q2 · EL 500 A L'ESCALAT — CADENA EXACTA

### La cadena, verificada baula a baula

```
PropagatedEditor.jsx:82   models.escalatAjustarTalla(modelId, info.pom_id, info.talla, value,
                                                     { capa, instancia })      ← garment CAU (el té a :62)
        ↓
endpoints.js:156-158      client.post('…/escalat/ajustar-talla/',
                            { pom_id, talla, valor, capa, instancia })         ← la signatura NO l'accepta
        ↓
urls.py:236               → escalat_ajustar_talla_view
        ↓
views.py:3346             capa, instancia, garment = _identitat_de_mesura(data)
                                                     ↑ garment = '' (cos mut) i NO s'usa en cap escriptura
        ↓
views.py:3413 / 3427      _write_base(model, pom, …, capa=capa, instancia=instancia)   ← 2 eixos de 3
        ↓
views.py:3714-3717        BaseMeasurement.objects.get_or_create(
                              model=model, pom=pom, capa=…, instancia=…)   💥 MultipleObjectsReturned
```

### La query que col·lapsa

[views.py:3714-3717](../../backend/fhort/models_app/views.py#L3714-L3717):

```python
bm, _created = BaseMeasurement.objects.get_or_create(
    model=model, pom=pom,
    capa=capa or MeasurementLayer.SLUG_DEFECTE, instancia=instancia or '',
    defaults={'base_value_cm': valor, 'origen': 'STANDARD'})
```

**La clau NO inclou `garment`.** Amb dues files vives que només difereixen per l'eix, `get_or_create`
crida `.get()` sobre un queryset de 2 → `MultipleObjectsReturned` → 500.

**El propi docstring ja ho tenia escrit** ([:3699-3703](../../backend/fhort/models_app/views.py#L3699-L3703)):
«amb el lookup curt, un `get_or_create(model, pom)` sobre una família de dues germanes o bé n'agafa
una a l'atzar o bé **peta amb `MultipleObjectsReturned`**». La frase es va escriure per `capa`/`instancia`
i és paraula per paraula el que passa avui amb `garment`. **Tercer cop del patró.**

### Les files d'avui — POM 962 al 1379 (SELECT read-only)

```sql
SELECT id, pom_id, capa, instancia, garment, base_value_cm, origen, is_active
  FROM fhort.models_app_basemeasurement WHERE model_id=1379 AND pom_id=962;
```

| id | pom_id | capa | instancia | garment | base_value_cm | origen | is_active |
|---|---|---|---|---|---|---|---|
| 3344 | 962 | exterior | *(buit)* | *(buit)* | 0.50 | IMPORTED | t |
| 3354 | 962 | exterior | *(buit)* | **02** | 0.50 | IMPORTED | t |

**2 files.** Idèntiques en els dos eixos que el lookup mira. El 500 és determinista, no una cursa.

### És el LECTOR o l'ESCRIPTOR? → **TOTS DOS, i en tres punts**

| Rol | Punt | Diagnòstic |
|---|---|---|
| **Escriptor** | `_write_base` [:3714](../../backend/fhort/models_app/views.py#L3714) | 🔴 **Ni grava ni resol** l'eix. **Aquest és el 500.** |
| **Escriptor** | `ModelGradingOverride` — poda [:3421-3423](../../backend/fhort/models_app/views.py#L3421-L3423), upsert [:3437-3442](../../backend/fhort/models_app/views.py#L3437-L3442), `prev` [:3433-3436](../../backend/fhort/models_app/views.py#L3433-L3436) | 🔴 Sense l'eix. `unique_together` **sí** el porta ([models.py:1089](../../backend/fhort/models_app/models.py#L1089)) → l'`update_or_create` naixeria sempre a la mare i el `.delete()` s'enduria els overrides de l'altra peça. |
| **Escriptor** | `MeasurementChangeLog` [:3444-3448](../../backend/fhort/models_app/views.py#L3444-L3448) | 🔴 Sense l'eix, i és **append-only**: una atribució falsa aquí no es corregeix mai. |
| **Lector de la resposta** | `GradedSpec.filter(…, garment='')` [:3491-3493](../../backend/fhort/models_app/views.py#L3491-L3493) + `clau_mesura(…, '')` [:3496](../../backend/fhort/models_app/views.py#L3496) | ⚠️ **`''` cuit a posta.** L'acta ③ [:3478-3486](../../backend/fhort/models_app/views.py#L3478-L3486) ho declara i diu que obrir-ho «és un tram propi». **Aquest tram és aquest.** |
| **Lector de la llei** | `_load_grading_rules(model).get(pom.id)` [:3388](../../backend/fhort/models_app/views.py#L3388) | ⚠️ Llei de la MARE → v. **Q4**. |

L'acta ③ diu «el cos de la petició no en diu res» — i és **exactament** el que aquest tram ha de canviar.
El default explícit era honest mentre el contracte era mut; **ara la pantalla el sap dir i no el diu**.

### Radi de dany (tot el tenant `fhort`)

Claus `(model, pom, capa, instancia)` amb més d'una fila — les úniques que poden col·lapsar:

| model_id | codi | claus que col·lapsen | garments |
|---|---|---|---|
| 1320 | BRW-FW26-0001 «Blusa KAYCE» | 1 (POM 904) | `''` + `02` |
| **1379** | **BRW-FW26-0002 «RUFFLES»** | **1 (POM 962)** | `''` + `02` |

Al 1379 **només** aquesta clau col·lapsa: els POM 906 i 958 tenen 3 files cadascun però es
distingeixen per `instancia` (`top`/`bottom`/`extended`, `cf`/`cb`/`waistband_seam`), que el
lookup **sí** mira. **Per això el símptoma és el POM 962 i cap altre.**

> 🚨 **El 1320 també peta, i la seva fila `02` està INACTIVA** (id 2297, `is_active=false`).
> `_write_base` **no filtra `is_active`**, o sigui que una fila podada segueix col·lapsant el
> `get_or_create`. Una poda **no** és un remei per aquest 500.

Estat de l'eix a les altres taules: `models_app_modelgradingoverride` → **0 files** amb
`garment <> ''` · `models_app_modelgradingrule` → **0 de 359**. L'eix mai no s'hi ha escrit,
cosa coherent amb un write-path que no el recull.

---

## Q3 · DESTÍ D'ESCRIPTURA — ON HAURIA D'ANAR L'EIX

**Cap migració és necessària.** Les 4 taules ja tenen la columna i la clau:

| Taula | Columna | Clau única | Migració? |
|---|---|---|---|
| `BaseMeasurement` | [models.py:799](../../backend/fhort/models_app/models.py#L799) | `(model, pom, capa, instancia, garment)` [:825](../../backend/fhort/models_app/models.py#L825) | ✅ ja hi és |
| `ModelGradingOverride` | [models.py:1077](../../backend/fhort/models_app/models.py#L1077) | `(model, pom, size_label, capa, instancia, garment)` [:1089](../../backend/fhort/models_app/models.py#L1089) | ✅ ja hi és |
| `MeasurementChangeLog` | [models.py:985](../../backend/fhort/models_app/models.py#L985) | *(append-only, sense clau)* | ✅ ja hi és |
| `ModelGradingRule` | [models.py:1241](../../backend/fhort/models_app/models.py#L1241) | `(model, pom, garment)` [:1253](../../backend/fhort/models_app/models.py#L1253) | ✅ ja hi és |
| `GradedSpec` | [fitting/models.py:249](../../backend/fhort/fitting/models.py#L249) | — | ✅ ja hi és |

### 🚨 TROBALLA DURA — el serializer NO POT REBRE L'EIX

Les portes #1 i #2 del cens (`POST /api/v1/base-measurements/`) passen per
`BaseMeasurementSerializer`. El seu `Meta.fields` ([serializers.py:452-468](../../backend/fhort/models_app/serializers.py#L452-L468))
declara `'capa', 'instancia'` i **NO `'garment'`** (verificat extraient la tupla i comprovant
`"'garment'" in fields` → **False**).

Conseqüència **doble**, i totes dues silencioses:

1. **La fila neix a la MARE.** Encara que el front enviés `garment: '02'`, DRF descarta el camp
   (no és a `fields`) i el model aplica el `default=''`.
2. **El guard dona un 400 FALS.** `validate()` **sí** que consulta l'eix
   ([:490](../../backend/fhort/models_app/serializers.py#L490)) — però via
   `attrs.get('garment', getattr(inst, 'garment', '') or '')`, i en una **creació** `attrs` no el
   porta mai (camp no escrivible) i `inst` és `None` → sempre `''`. Amb la fila de la mare viva,
   crear la germana de la 02 rep **«Aquesta mesura ja té una fila en aquesta capa, instància i peça»**.

> El comentari de `validate()` ([:484-490](../../backend/fhort/models_app/serializers.py#L484-L490))
> afirma que «el tercer eix entra al filtre de germanes». **L'expressió hi és; el valor no hi pot
> arribar mai.** És el patró dels docstrings certs-a-mitges de S42: la línia és correcta i la
> premissa que la fa funcionar (que el camp sigui escrivible) no s'ha construït.
> **`front sol` NO n'hi ha prou per a #1 i #2.**

### Portes ja llestes al backend (només cal que el front parli)

| Endpoint | Vista | Estat |
|---|---|---|
| `pom/<pom>/desactivar/` | [views.py:4963-4968](../../backend/fhort/models_app/views.py#L4963-L4968) | ✅ resol per **4 eixos** |
| `pom/<pom>/regim/` | [views.py:5089-5092](../../backend/fhort/models_app/views.py#L5089-L5092) | ✅ llegeix `garment` i escriu la resident amb l'eix |
| `size-checks/<id>/resolve/` | [services_size_check.py:238-242](../../backend/fhort/models_app/services_size_check.py#L238-L242) | ✅ `garment=line.garment` |
| `set-measurements` / `gravar_pom` | [views.py:2225](../../backend/fhort/models_app/views.py#L2225), [:2365](../../backend/fhort/models_app/views.py#L2365), poda [:3580](../../backend/fhort/models_app/views.py#L3580) | ✅ clau de 4 (T7-B7) |

---

## Q4 · FRONTERA AMB Q1-bis (`_load_grading_rules`)

**Toquen la MATEIXA vista, i no són el mateix tram. Es poden fer per separat; no s'HAURIEN de.**

`escalat_ajustar_talla_view` conté **les dues coses**:

- **F1** = *sobre quina fila s'escriu* → `_write_base` [:3413](../../backend/fhort/models_app/views.py#L3413)/[:3427](../../backend/fhort/models_app/views.py#L3427), els 3 punts d'`Override` [:3421-3442](../../backend/fhort/models_app/views.py#L3421-L3442), el `ChangeLog` [:3444](../../backend/fhort/models_app/views.py#L3444), i el filtre de resposta [:3491-3496](../../backend/fhort/models_app/views.py#L3491-L3496).
- **Q1-bis** = *quina LLEI s'aplica* → `_load_grading_rules(model).get(pom.id)` [:3388](../../backend/fhort/models_app/views.py#L3388), que serveix **la regla de la mare** per contracte declarat ([pom/services.py:774-792](../../backend/fhort/pom/services.py#L774-L792)).

Són **independents en mecanisme**: arreglar F1 no toca la :3388, i arreglar la :3388 no evita el
`MultipleObjectsReturned`. Però estan **acoblats en resultat**:

> 🚩 **Tancar F1 sol deixa la vista escrivint a la fila CORRECTA amb la llei EQUIVOCADA.**
> Ara mateix el 500 protegeix de l'error silenciós; en treure'l, la 02 es propaga amb el Δ de la
> mare i **ningú no ho canta**. F1 no és menys urgent per això — és que el seu fix **converteix un
> 500 sorollós en un valor mal calculat i mut** si la :3388 no va al mateix commit.
> Aquesta és la llei S42 «obrir una lectura ARMA les escriptures» girada: **tancar una escriptura
> arma un lector**.

Les **altres dues** superfícies de Q1-bis són **independents de F1** (presentació pura, cap escriptura):
- [fitting/serializers.py:267-268](../../backend/fhort/fitting/serializers.py#L267-L268) — règim del desplegable.
- `reglaPerPom` [CheckMeasureEditor.jsx:597-601](../../frontend/src/components/model/CheckMeasureEditor.jsx#L597-L601) — indexa per `pom_id` pelat; el banc `clauRegla` ([identitatMesura.js:115-116](../../frontend/src/utils/identitatMesura.js#L115-L116)) ja existeix i no s'hi fa servir.

L'acta de `_load_grading_rules` ja diu que la línia divisòria entre els 6 consumidors és
**«si escriuen»** ([pom/services.py:798-806](../../backend/fhort/pom/services.py#L798-L806)) — i n'anomena
`fitting/views.py` com l'únic adaptat *perquè decideix una escriptura*. **`views.py:3388` decideix una
escriptura i està al costat dels no-adaptats.** El cens d'aquella acta el va classificar com a
presentació; no ho és.

---

## Q5 · SUPERFÍCIE DE RESPONSE LITERAL

`grep` dels `Response(` dins `escalat_ajustar_talla_view` (3306-3499) → **13 literals**. Cap serializer
en tota la vista.

| Línia | Contingut | Torna dades de fila? |
|---|---|---|
| 3336, 3350, 3354, 3357, 3361, 3365, 3378, 3407, 3412, 3460 | `{'error': …}` | ❌ no |
| 3386 | `{'error': fora, 'codi': CODI_MESURA_FORA_RANG}` | ❌ no |
| 3457 | `e.payload` (409 segell) | ❌ no |
| **3498-3499** | `{'ok', 'propagat', 'motiu', 'grading_version_id', 'linies'}` | 🔴 **SÍ** |

**El 3498 és la troballa de Q5.** `linies` es construeix **inline**, sense serializer
([:3487-3497](../../backend/fhort/models_app/views.py#L3487-L3497)), i la identitat de cada fila la
compon a mà amb **l'eix cuit a `''`**:

```python
for spec in GradedSpec.objects.filter(grading_version=gv, pom=pom,
                                      capa=capa, instancia=instancia,
                                      garment=''):        # ← literal
    ...
clau = clau_mesura(pom.id, capa, instancia, '')            # ← literal
```

`MeasureGrid` indexa el seu buffer per aquest `id`. Amb l'eix cuit, **el refresc d'una fila de la 02
no arribaria mai a la seva cel·la** — el mateix mode de fallada mut que l'acta ② descriu per al
`lineId` ([:3470-3476](../../backend/fhort/models_app/views.py#L3470-L3476)), un eix més tard. La llei
de mètode es compleix: **el forat era al PAYLOAD, no al menú.**

**Segona superfície literal** — `desactivar_pom_view` ([views.py:4977-4990](../../backend/fhort/models_app/views.py#L4977-L4990)):
el filtre **sí** porta els 4 eixos, però el `Response` literal emet `'capa'` i `'instancia'` i
**no `'garment'`**. El comentari de la mateixa resposta diu que existeix perquè «el client ha de poder
confirmar que la que ha marxat és la que ell mirava» — i amb dues peces vives **no ho pot confirmar**.

---

## LLISTA ORDENADA DE WRITE-PATHS A REPARAR

Ordenada per **dany**, no per esforç. Res implementat.

| # | Write-path | Dany | Mínim canvi |
|---|---|---|---|
| **1** | `_write_base` [views.py:3689-3721](../../backend/fhort/models_app/views.py#L3689-L3721) + les 2 crides [:3413](../../backend/fhort/models_app/views.py#L3413)/[:3427](../../backend/fhort/models_app/views.py#L3427) | 🔴 **500 viu.** L'Escalat no desa res al POM 962 (1379) ni al 904 (1320) | **backend sol** — 3r paràmetre `garment=''` a la signatura i al `get_or_create`. 2 cridadors, tots dos en aquesta vista. |
| **2** | `escalatAjustarTalla` [endpoints.js:156-158](../../frontend/src/api/endpoints.js#L156-L158) + [PropagatedEditor.jsx:83](../../frontend/src/pages/PropagatedEditor.jsx#L83) | 🔴 Sense això, l'#1 rep `''` i el 500 es converteix en **escriure a la mare en silenci** | **front sol** — afegir `garment: eixos.garment` al cos i `info.garment` a la crida. El valor **ja hi és** a [:62](../../frontend/src/pages/PropagatedEditor.jsx#L62). |
| **3** | `onDesfaInstancia` [CheckMeasureEditor.jsx:649-651](../../frontend/src/components/model/CheckMeasureEditor.jsx#L649-L651) | 🔴 **DESTRUCTIU** — desfer una partició a la 02 **poda la fila de la MARE**. Backend ja llest | **front sol** — canviar el literal `{capa, instancia}` per `eixosDeLaFila(g)`, ja importat a [:3](../../frontend/src/components/model/CheckMeasureEditor.jsx#L3) |
| **4** | `ModelGradingOverride` × 3 + `MeasurementChangeLog` [views.py:3421-3448](../../backend/fhort/models_app/views.py#L3421-L3448) | 🔴 `.delete()` s'endú els overrides de l'altra peça; el `ChangeLog` és **append-only** i la falsa atribució és irreversible | **backend sol** — `garment=garment` als 4 punts. La variable ja està desempaquetada a [:3346](../../backend/fhort/models_app/views.py#L3346). |
| **5** | `BaseMeasurementSerializer.Meta.fields` [serializers.py:452-468](../../backend/fhort/models_app/serializers.py#L452-L468) | 🔴 **Crear una fila per peça és impossible per API**: o neix a la mare, o rep un **400 fals** | **backend sol** (⚠️ **NO front sol**) — afegir `'garment'` a `fields`. Sense això, #6 i #7 no poden funcionar per molt que el front l'enviï. |
| **6** | `presaPortes.onNova` [CheckMeasureEditor.jsx:654-660](../../frontend/src/components/model/CheckMeasureEditor.jsx#L654-L660) + `handleAddRow` [EditableTable.jsx:357-362](../../frontend/src/components/EditableTable/EditableTable.jsx#L357-L362) i `germanaCapaRapida` [:482-484](../../frontend/src/components/EditableTable/EditableTable.jsx#L482-L484) | 🔴 Tota fila nova neix a la mare | **front + backend (#5)** — `EditableTable` **ja rep** el prop `garment` ([:148](../../frontend/src/components/EditableTable/EditableTable.jsx#L148)) però `CheckMeasureEditor` **no l'hi passa** ([:736-744](../../frontend/src/components/model/CheckMeasureEditor.jsx#L736-L744)); el contenidor el sap (`eixPeca` [:720](../../frontend/src/components/model/CheckMeasureEditor.jsx#L720)). **La junta és aquesta línia.** |
| **7** | `presaPortes.onParteix` [CheckMeasureEditor.jsx:635-639](../../frontend/src/components/model/CheckMeasureEditor.jsx#L635-L639) | 🔴 Partir un POM de la 02 crea la germana a la mare | **front + backend (#5)** — `garment: row.garment \|\| ''` (la fila el porta, [filesDePresa.js:61](../../frontend/src/utils/filesDePresa.js#L61)) |
| **8** | `Response` literal [views.py:3487-3499](../../backend/fhort/models_app/views.py#L3487-L3499) | 🟠 El refresc de cel·la **no arriba** a les files de la 02 (mut) | **backend sol** — treure els dos `''` cuits ([:3493](../../backend/fhort/models_app/views.py#L3493), [:3496](../../backend/fhort/models_app/views.py#L3496)) |
| **9** | `_load_grading_rules` [views.py:3388](../../backend/fhort/models_app/views.py#L3388) | 🟠 **Q1-bis** — la 02 es propaga amb la llei de la mare. Avui el tapa el 500; en obrir l'#1 queda **mut** | **backend sol** — `_regla_de(_load_grading_rules_per_garment(model), pom.id, garment)`, com [fitting/views.py:680](../../backend/fhort/fitting/views.py#L680). **Va al MATEIX commit que #1** (v. Q4) |
| **10** | `setPomRule` [CheckMeasureEditor.jsx:191](../../frontend/src/components/model/CheckMeasureEditor.jsx#L191) · `setPomRegim` [PropagatedEditor.jsx:150](../../frontend/src/pages/PropagatedEditor.jsx#L150) | 🟠 Editar la Δ des del contenidor de la 02 reescriu la regla de la mare. Backend ja llest ([views.py:5089](../../backend/fhort/models_app/views.py#L5089)) | **front sol** — `garment` al payload. L'acta de [:184-190](../../frontend/src/components/model/CheckMeasureEditor.jsx#L184-L190) preveia exactament aquest dia |
| **11** | `Response` literal de `desactivar_pom_view` [views.py:4977-4990](../../backend/fhort/models_app/views.py#L4977-L4990) | 🟡 La resposta no diu de quina peça era la fila podada | **backend sol** — afegir `'garment': bm.garment` |

**Cap element demana migració.** Els #1+#9 i els #5+#6+#7 formen **dos paquets indivisibles**.

---

## LÍMITS DECLARATS (comportes, no notes al peu)

1. **NO he executat cap escriptura ni cap test.** Tot el veredicte és lectura de codi + `SELECT`.
   El 500 està **inferit de la query i de les dades**, no reproduït. La inferència és forta (2 files
   idèntiques en els 2 camps del lookup, `get_or_create` → `.get()`), però **una sonda a la vora
   confirmaria l'excepció exacta** — i la llei de S42 diu que la sonda va a la cel·la, no al codi.
   Reproduir-lo **escriuria**, i això és fora de Patró A.

2. **No he auditat els altres 4 consumidors de `_load_grading_rules`**
   ([graded_spec_views.py:171](../../backend/fhort/fitting/graded_spec_views.py#L171),
   [views.py:2042](../../backend/fhort/models_app/views.py#L2042),
   [serializers_size_check.py:97](../../backend/fhort/models_app/serializers_size_check.py#L97),
   [fitting/serializers.py:268](../../backend/fhort/fitting/serializers.py#L268)). Q4 només demanava
   la frontera. **⚠️ `views.py:2042` és dins `measurements_table_view`, que ALIMENTA l'Escalat** —
   pot ser una cinquena boca de la família i **no s'ha censat**.

3. **El cens és de `CheckMeasureEditor` + `PropagatedEditor` + `EditableTable`.** `fittingSource`
   ([measureSources.jsx](../../frontend/src/components/model/measureSources.jsx)) és una font
   alternativa del mateix component i **les seves portes no s'han censat**. `FittingDetail`
   (`/fittings/:id`) queda fora.

4. **`germanesDeLEix`** ([EditableTable.jsx:658-665](../../frontend/src/components/EditableTable/EditableTable.jsx#L658-L665)),
   `capesLliuresDe` [:410-416](../../frontend/src/components/EditableTable/EditableTable.jsx#L410-L416) i
   `germanaCapaRapida` [:473-479](../../frontend/src/components/EditableTable/EditableTable.jsx#L473-L479)
   filtren `localRows` per `pom_id` + `capa` **sense mirar `garment`**. Avui **no és un bug** perquè
   `localRows` ja arriba partit per contenidor (`presaDelContenidor`,
   [CheckMeasureEditor.jsx:722](../../frontend/src/components/model/CheckMeasureEditor.jsx#L722)).
   És un **acoblament latent**: aquests tres predicats són correctes **per una propietat del cridador,
   no per la seva pròpia condició**. Són **la FAMÍLIA DE TRES dins d'`EditableTable`** i el dia que
   una taula rebi dues peces alhora, els tres fallen junts i en silenci.
   🚩 **No s'ha decidit què fer-hi. Queda OBERT.**

5. **`origen` de la germana nova.** `onParteix` hereta `row.origen || 'TEMPLATE'`
   ([:638](../../frontend/src/components/model/CheckMeasureEditor.jsx#L638)) i `onNova` força
   `'TEMPLATE'` ([:659](../../frontend/src/components/model/CheckMeasureEditor.jsx#L659)). **No he
   verificat** si això és coherent amb la política de `_procedencia_de_mesura`
   ([views.py:3645](../../backend/fhort/models_app/views.py#L3645)), perquè aquell punt no és al camí
   del serializer. Fora d'abast, **anotat**.

6. **Tenant únic.** Tots els `SELECT` són sobre `fhort` a **staging**. `los` no té model 1379 i
   **no s'ha auditat**. L'estat de PROD **no s'ha mirat** (sense SSH; caldria el dump diari).

7. **Un canvi al `serializer` de `BaseMeasurement` (#5) obre `garment` a TOTS els seus clients**,
   no només a la presa. `filterset_fields` ja l'exposa en lectura
   ([views.py:524](../../backend/fhort/models_app/views.py#L524)); fer-lo **escrivible** és una
   superfície nova. **No he censat qui més fa `POST`/`PATCH` a `/api/v1/base-measurements/`** —
   això és feina d'obrir la porta, no d'aquesta diagnosi.
