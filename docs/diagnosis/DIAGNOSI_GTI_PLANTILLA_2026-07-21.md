# DIAGNOSI — GTI-PLANTILLA (el `GarmentTypeItem` com a unitat completa de motor de patrons)

> **Data:** 2026-07-21 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Abast:** si un `GarmentTypeItem` ben informat pot portar la seva plantilla completa —sketch(s),
> patró base amb DXF/RUL, i mesures de talla base— de manera que sembrar un model nou sigui
> *triar item → triar run de talles → triar/aplicar `GradingRuleSet` → el sistema ho instancia*.
> Tres fils amb peces vives que avui no es parlen entre si.
>
> **Convenció:** tota afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**
> (verificat per grep exhaustiu, no especulat). Les propostes van marcades `💡 PROPOSTA (a validar)`
> i **no** són decisions: les decisions són humanes (Patró C).
>
> **Guardes complertes:** cap escriptura de codi, cap commit, cap migració, cap restart · BD només
> `SELECT` (schemes `fhort` i `los`) · `migrate_schemas --list` no usat · únic fitxer creat: aquest.
> No s'ha tocat res del radi de la Sessió A paral·lela (wizard, grading services).
>
> **⚠️ Cens viu, no congelat:** durant la sessió ha entrat un `PatternFile` nou (id 12, model 174,
> `CALLIE-…dxf`) d'una sessió concurrent. Les xifres del motor d'aquest document són les de la
> **darrera lectura** (§B5.4); les intermèdies difereixen en 1 fitxer / 16 peces.

---

## RESUM EXECUTIU

1. **Això no és domini nou: és domini construït i no endollat.** De les quatre peces de la visió,
   tres ja existeixen al codi, desplegades i amb tests: la plantilla de valors base
   (`ItemBaseMeasurement`, `pom/models.py:464`), la biblioteca de fitxers d'item (`ItemFitxer`,
   `models_app/models.py:464`) i **l'ancoratge del patró a l'item** (`PatternFile.garment_type_item`
   amb `CheckConstraint` XOR viu a BD des de la migració inicial, `patterns/models.py:46,109-115`).
   El que falta no són els maons: és el pegament, i **una decisió de domini** (§B4).

2. **`GarmentTypeItemAsset` NO EXISTEIX ni ha existit mai** — `git log -S` no en troba cap commit, i
   el codi mateix ho documenta (`patterns/models.py:51-53`). El disseny del 29/06 (D6) va ser
   **substituït** per `ItemFitxer` + XOR cap a `tasks.GarmentTypeItem`, decisió registrada a
   `PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:440-441`. Qualsevol brief que encara el nomeni parla d'una
   entitat inexistent.

3. **L'horitzó D7 està, de facto, tancat — i en la seva meitat cara.** `MOTOR_DE_PATRONS_V2.md:69`
   demanava "FK opcionals a item": **complert i superat** (no són opcionals, són XOR obligatori). La
   seva altra meitat —"base paramètrica", grading a nivell d'item— la tanca la decisió d'Agus
   *"les bases de biblioteca viuen i s'exporten EN TALLA BASE — la biblioteca ven forma, el model ven
   mides"* (`PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:1107-1109`). **Amb aquesta llei, la peça cara no cal.**

4. **El patró d'item ja s'hi pot pujar; el que hi ha darrere encara pregunta `model_id`** — en ~26
   punts (§B5.2). D'aquests, **un menteix en silenci**: `adapters.py:594-595` retorna zero costures
   per a un patró d'item sense cap avís, cosa que contradiu la llei escrita tres fitxers més enllà
   (*"OMISSIONS: MAI EN SILENCI"*, `engine/grading_projection.py:51-56`). És el defecte més barat de
   tancar i el més car de deixar viu.

5. **La col·lisió import-fitxa ↔ sembra-item ja està legislada a mitges, i és asimètrica.** L'import
   declara *"NORMES INAMOVIBLES: 1. Mana el document"* (`extraction_views.py:1722-1725`): esborra
   totes les files sense valor i sobreescriu **sense mirar l'`origen`**. La sembra, en canvi, respecta
   l'import — però **per accident** d'una condició escrita per a un altre motiu
   (`models_app/views.py:827`). **NO EXISTEIX cap taula de precedència d'orígens** a tot el repo.

6. **LA decisió (§B4) té ancoratge empíric, i apunta a "no cal l'eix".** 5 dels 27 GTI amb models a
   `fhort` **ja serveixen més d'un client** (466 dels 1005 models). Però el lloc on el client
   diferencia les seves mides **ja existeix i és sobirà**: `BaseMeasurement` del Model, amb
   `ITEM_STANDARD` documentat com a **"copy-at-the-moment"** (`models_app/models.py:558`). L'eix de
   client a `ItemBaseMeasurement` només cal si es vol **evitar re-teclejar** per client, no per
   correcció. Tres opcions a §B4.3, sense decidir.

---

## BLOC B1 — Estat real d'`ItemBaseMeasurement`

### B1.1 El model (`pom/models.py:464-501`)

| Camp | Tipus | Nota | `ruta:línia` |
|---|---|---|---|
| `garment_type_item` | FK `tasks.GarmentTypeItem`, CASCADE, NOT NULL | **`db_constraint=False`** (pom és SHARED, tasks tenant-only) | `pom/models.py:477-478` |
| `pom` | FK `POMMaster`, PROTECT | constraint REAL a BD | `pom/models.py:479` |
| `base_value_cm` | `DecimalField(7,2)` null | NULL = POM sense valor estàndard | `pom/models.py:481` |
| `tol_minus` / `tol_plus` | `DecimalField(5,2)` null | fallback al default del `POMMaster` | `pom/models.py:484-485` |
| `nom_fitxa` | `CharField(20)` blank | | `pom/models.py:490` |
| unicitat | `unique_together ('garment_type_item','pom')` | | `pom/models.py:495` |

- **Eix `customer`: NO EXISTEIX.** Ni al model, ni indirectament: `GarmentTypeItem` tampoc en té
  (`tasks/models.py:288-320`; DDL verificat).
- **Eix `size_label`: NO EXISTEIX.** És base d'**UNA sola talla**, com `BaseMeasurement`. La talla és
  implícita i viu al pare: `GarmentTypeItem.base_size_definition` (`tasks/models.py:307`), explicitat
  al docstring `pom/models.py:472`.

**Paritat amb `BaseMeasurement`** (`models_app/models.py:547-602`): **mateix contracte de dades amb
l'àncora canviada**, però *empobrit*. Coincideixen `pom`, valor, toleràncies i `nom_fitxa` (amb noms
diferents a les toleràncies: `tol_minus` vs `tolerancia_minus`). A `ItemBaseMeasurement` **NO
EXISTEIXEN**: `is_key`, `ordre`, `origen`, `is_active`, `notes`, `created_at`/`updated_at` ni
`created_by` — **la plantilla no té ni timestamps ni autoria**. Divergència de tipus a vigilar:
`Decimal(7,2)` a la plantilla vs **`FloatField`** al model (`models_app/models.py:565`).

### B1.2 Files reals a BD

| schema | total | amb `base_value_cm` | amb tolerància | amb `nom_fitxa` |
|---|---|---|---|---|
| `fhort` | **37** | **2** | 2 | **0** |
| `los` | **0** | 0 | 0 | 0 |

Les 37 pengen **d'un sol item**: `gti=4` `shirt_woven` "Shirt Man Regular". Les 2 amb valor són
`pom 273` i `pom 275`, totes dues `60.00`. Les altres 35 són pertinença duplicada sense valor.

> **Lectura:** l'estat d'`ItemBaseMeasurement` és **construït i pràcticament no usat**. El GTI-5
> (`blouse`, el del model 163/Tate) en té **0** — coherent amb `DIAGNOSI_S10_GRADING_BROWNIE.md:305`.

### B1.3 Lectors i escriptors (grep exhaustiu)

| `ruta:línia` | Operació | Superfície / gate |
|---|---|---|
| `pom/views.py:304-322` | `ItemBaseMeasurementViewSet` CRUD complet | `/api/v1/item-base-measurements/` |
| `pom/views.py:315-321` | `get_permissions` | list/retrieve `IsAuthenticated`; **la resta `CONFIGURE`** |
| `pom/views.py:332-360` | acció `upsert` → `update_or_create` per `(item, pom)` | `CONFIGURE` |
| `pom/serializers.py:385-397` | serializer | — |
| `models_app/views.py:789,796` | **LECTURA** dins `materialize_poms_view` | §B1.4 |
| `export_losan_package.py:245-254` | export → `06_pom_maps.json` | ⚠️ **no exporta toleràncies** |
| `load_losan_package.py:350-357` | `_upsert` | ⚠️ **no importa toleràncies** |
| `seed_data/consolidate_pom_los.py:32` | re-apunta `pom_id` en fusionar POMs | — |
| `MeasurementBaseGrid.jsx:56,152,164-171` | **UI real d'autoria** (list / remove / upsert) | — |
| `MeasuresEntryPanel.jsx:125-131` | lectura per decidir si oferir la sembra | — |
| **Tests** | **NO EXISTEIX cap test** del model ni de l'endpoint | — |

**SÍ hi ha UI on un humà introdueixi aquests valors:** `MeasurementBaseGrid` (graella amb valor base,
tol−, tol+, `nom_fitxa`), muntada al **PAS 2 "Construcció"** del wizard d'autoria d'item
(`ItemAuthoring.jsx:328`; rutes `App.jsx:302-303`). Escriu simultàniament `GarmentPOMMap` (pertinença)
i `ItemBaseMeasurement` (valors) — `MeasurementBaseGrid.jsx:148-175`.

### B1.4 Com viatgen els valors a un model nou

`materialize_poms_view` — `models_app/views.py:766-843`, ruta `models_app/urls.py:195`
(`POST /api/v1/models/<id>/materialitzar-poms/`, gate només `IsAuthenticated`).

- **CÒPIA, no referència.** `BaseMeasurement` no té cap FK cap a `ItemBaseMeasurement`. Un cop
  copiat, el model és sobirà — exactament la llei §2 de `DECISIONS.md`, i l'enum ho diu amb totes les
  lletres: `('ITEM_STANDARD', "Sembrat de l'estàndard de l'item (copy-at-the-moment)")`
  (`models_app/models.py:558`).
- **Camps copiats** (`views.py:808-813`): `base_value_cm`, `nom_fitxa`, `tol_minus→tolerancia_minus`,
  `tol_plus→tolerancia_plus`. `is_key` i `ordre` vénen del **`GarmentPOMMap`**, no de la plantilla.
- **Sense `ItemBaseMeasurement`** (o amb valor NULL): fila buida `origen='TEMPLATE'`,
  `base_value_cm=None` (`views.py:815-820`).
- **Idempotent i respectuós** (`views.py:825-836`): només reomple si
  `origen=='TEMPLATE' and base_value_cm is None`; qualsevol altre cas → `skipped`. Tot dins
  `transaction.atomic()`.
- **Conduït pel `GarmentPOMMap`** (`views.py:791-794`): un POM amb valor a la plantilla però **sense**
  `GarmentPOMMap` **no es materialitza mai**.

**Veredicte B1: la peça EXISTEIX sencera i és sana** (model + API + UI d'autoria + sembra idempotent
+ sobirania correcta). Els seus dos problemes són **de dades** (37 files, 1 item, 2 valors) i **de
cobertura** (zero tests). Dos deutes menors anotats: toleràncies que no viatgen al paquet LOSAN, i
conversió implícita Decimal→float a `views.py:809`.

---

## BLOC B2 — Estat real dels actius d'item (sketch + DXF/RUL)

### B2.1 `ItemFitxer` (`models_app/models.py:464`)

Mirall d'`ModelFitxer` amb la mateixa invariant de cadena (`versio`/`is_current`/`versio_anterior`,
`:481-486`), FK **NOT NULL** a `tasks.GarmentTypeItem` (`:476-477`), migració `0054_itemfitxer.py`.
Reusa `ModelFitxer.TIPUS_CHOICES` (`:479-480`) — **no en té de propis**, exactament com deia DA-23.

`TIPUS_CHOICES` reals (`models_app/models.py:355-367`): `ALTRES`, `DOCUMENT`, `TECHSHEET`, `EXPORT`,
**`PATRO`**, `ESCALAT`, **`SKETCH_FLETXES`**, **`SKETCH_NET`**, **`SKETCH_SVG`**, `MARCADA`, **`RUL`**.
→ sketch = els tres `SKETCH_*`; patró = `PATRO`/`ESCALAT`; regles CAD = `RUL`.

**Estat a BD: `models_app_itemfitxer` és BUIDA a `fhort` i a `los` (0 files).**
→ El **GTI-5 (`blouse`)** no té cap `ItemFitxer`. El **model 163** penja d'aquest mateix GTI-5
(`garment_type_item_id=5`), per tant tampoc. **La biblioteca de fitxers d'item existeix i mai s'ha
estrenat.**

### B2.2 `GarmentTypeItemAsset`

> **NO EXISTEIX** — confirmat. Zero hits en codi i en migracions; `git log --all -S` → **cap commit**.

El codi mateix ho documenta i n'anomena el substitut:

```
#: D'on ve aquesta còpia, si es va sembrar des del catàleg. `GarmentTypeItemAsset` NO
#: existeix (S0-B2): qui fa de biblioteca d'actius d'ítem és `ItemFitxer`.
```
— `patterns/models.py:51-53`

Què en proposava el document del 29/06: `MOTOR_DE_PATRONS_V2.md:68` (D6, "sketch base + DXF amb POMs
per item, *catàleg sembra, Model posseeix*"), `:168` i `:189-193`. **Abast real avui:** el rol es
reparteix entre `ItemFitxer` (fitxers genèrics d'item) i `PatternFile.garment_type_item` (patró CAD),
amb `PatternFile.source_asset` → `ItemFitxer` per a la traçabilitat. La substitució està segellada a
`PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:440-441`.

### B2.3 `PatternFile`: l'equivalent d'item **SÍ existeix** (matís al punt 7 del brief)

La premissa del brief ("PatternFile és per MODEL, confirmar que no hi ha equivalent a nivell item")
**queda refutada, i a favor nostre**:

| Aspecte | Fet | `ruta:línia` |
|---|---|---|
| `model` FK → `models_app.Model` | **null=True, blank=True** | `patterns/models.py:42-45` |
| `garment_type_item` FK → `tasks.GarmentTypeItem` | **null=True**, `help_text` "Patró de biblioteca (base de catàleg)" | `patterns/models.py:46-50` |
| `source_asset` FK → `models_app.ItemFitxer` | null, SET_NULL | `patterns/models.py:53-56` |
| **XOR a BD** | `CheckConstraint patternfile_xor_model_item` | `patterns/models.py:106-113` + `migrations/0001_initial.py:114` |
| Anti-bifurcació | `UniqueConstraint(['versio_anterior'])` | `patterns/models.py:114-121` |

La migració va ser **auditada per exercici** (inserts reals en transacció revertida) segons el
dietari `PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:530-536`. I l'upload ancorat a item **té tests**:
`patterns/tests.py:937-957` (puja i verifica `fp.garment_type_item_id`) i `tests.py:3105-3113` (la
frontera es diu, no es fingeix: un patró d'item retorna 400 a `model-poms`).

La resta de l'app `patterns` **no** té cap FK a `GarmentTypeItem`: `PatternPiece`/`Point`/`Segment`
pengen del `pattern_file` (`models.py:153,215,278`), `PatternPOM` de `pattern_piece`+`pom_master`
(`:322,327`), i **quatre taules pengen de `Model` amb FK NOT NULL** — `SewRelation` (`:447`),
`SewProposalRejection` (`:517`), `DartProposalRejection` (`:566`), `SewToleranceAcceptance` (`:728`).

**A BD: 5 `PatternFile`, tots ancorats a model. `garment_type_item_id` NULL a tots.** La branca
d'item del XOR és **codi viu amb zero exercici real**.

### B2.4 El cicle DA-23/DA-27 **no basta** per a un DXF de patró

`usar-al-model` (`models_app/item_fitxer_views.py:130-190`) fa exactament el que DA-27 diu: no toca
l'origen, crea un `ModelFitxer` nou amb cadena pròpia, **copia els bytes** (reobre el fitxer i
recalcula checksum/mida/mimetype via `save_model_file`, `services_fitxers.py:90`) i marca la
procedència amb `derivat_de_item` (`:181`). El `.ftt` és l'única excepció: passa per
`font_per_al_model` (descongelat/rebinding, `:171`).

**Però crear un `ModelFitxer` amb un `.dxf` NO dispara cap parseig.** Són dos camins separats:

| | Cicle `ItemFitxer` (DA-23/27) | Camí del motor |
|---|---|---|
| Entrada | `POST /api/v1/item-fitxers/` → `usar-al-model` | `POST /api/v1/patterns/pattern-files/` |
| Què fa | desa bytes + checksum | `AAMAReader().read()` + `RULReader()` + `coherencia_dxf_rul` (`patterns/views.py:322-345`) |
| Què crea | una fila de fitxer | `PatternPiece` / `PatternPoint` / `PatternSegment` + empremta + `grade_table` (`adapters.py:207,289`) |
| Errors | 400 | **422 estructurat**, mai 500 |

Evidència creuada a BD: hi ha **0 `ModelFitxer` de tipus `PATRO`/`RUL`** a `fhort`, mentre que la
geometria real viu tota a `patterns_*`. Els dos mons no s'han tocat mai.

> 💡 **PROPOSTA (a validar):** `save_pattern_file` **ja accepta `source_asset`**
> (`patterns/services.py:39,73`) però **cap caller li'l passa mai** (grep: només la definició), i
> `_resoldre_propietari` (`patterns/views.py:374-393`) no llegeix cap paràmetre de sembra item→model.
> Un "usar al model" per a patrons exigiria **re-parsejar** (la geometria penja del `pattern_file`,
> no és compartible entre files) o **copiar la geometria** — no és el mateix gest que un `ModelFitxer`.

**Veredicte B2: la porta d'entrada del patró d'item està construïda i provada; la biblioteca de
fitxers d'item existeix i és verge; l'entitat que els briefs encara nomenen no existeix.** El cicle
d'`ItemFitxer` serveix per a sketches tal com és, i **no** serveix per a DXF sense una peça nova.

---

## BLOC B3 — Camí de sembra: qui mana quan tots dos porten bases

### B3.1 Inventari d'escriptures a `BaseMeasurement`

| # | Camí | `ruta:línia` | `origen` | Crea/sobreescriu | Guard |
|---|---|---|---|---|---|
| 1 | materialitzar-poms (buida) | `models_app/views.py:818` | `TEMPLATE` | crea si no existeix | `existing is None` |
| 2 | materialitzar-poms (amb valor) | `models_app/views.py:808` | `ITEM_STANDARD` | crea si no existeix | idem |
| 3 | materialitzar-poms (reompliment) | `models_app/views.py:829-836` | `ITEM_STANDARD` | update in-place | ✅ **l'ÚNIC guard de sobirania del repo** (`:827`) |
| 4 | **import fitxa — esborrat previ** | `extraction_views.py:1948` | — | **DELETE dur** de tot el que no té valor | ❌ **cap** |
| 5 | **import fitxa — escriptura** | `extraction_views.py:1967` | `IMPORTED` | `update_or_create`, **sobreescriu incondicionalment** | ❌ **cap guard d'origen** |
| 6 | `set-measurements` | `models_app/views.py:1068` | `MANUAL` | sobreescriu + reactiva | ❌ |
| 6b | `set-measurements` soft-delete | `models_app/views.py:1088-1092` | — | `is_active=False` per omissió | `keep_pom_ids is None` |
| 7 | `gravar-pom` | `models_app/views.py:1184-1198` | `MANUAL` | sobreescriu tot | ❌ (sí gates de negoci) |
| 9 | xat IA de mesures | `models_app/views.py:1541,1556,1577` | `MANUAL` | l'LLM decideix | ❌ |
| 10 | **CRUD REST directe (inclou DELETE dur)** | `models_app/views.py:414`, `urls.py:45` | el que enviï el client | qualsevol | ❌ només `IsAuthenticated` |
| 11 | wizard POM talla base | `pom/wizard_views.py:205` | no toca `origen` | sobreescriu | ❌ |
| 12 | fitting — consolidació | `fitting/services.py:369-378` | `FITTED` | sobreescriu | només base + valor canviat |
| 13 | size check — acceptació | `services_size_check.py:172-184` | `CHECKED` | sobreescriu si delta ≥1e-6 | guarda de canvi nul |
| 14 | escalat — ajustar talla base | `models_app/views.py:2021` | `STANDARD` | sobreescriu | ❌ |
| 15 | import "tech sheet" (antic) | `tech_sheet_views.py:358` | `IMPORTED` | ✅ **`get_or_create` pur** | l'`get_or_create` |
| 16 | clonatge QA | `clone_model_for_qa.py:92-95` | copia l'origen | clon nou | — |

**No escriuen `BaseMeasurement`** (verificat): `load_losan_package` (escriu la capa *item*,
`:350-357`), `export_losan_package`, i **cap comanda `seed_*`**.

⚠️ **Auditoria cega a la sembra buida:** `signals.py:248` no registra res si `base_value_cm is None`
→ tota la materialització `TEMPLATE` és **invisible** al `MeasurementChangeLog`.

### B3.2 Com escriu bases l'import de fitxa (la seqüència)

`POST /api/v1/import-sessions/<token>/confirmar/` — `extraction_views.py:1718`. (`extraction_service.py`
**no toca `BaseMeasurement`**: només crida l'API d'extracció, `:129`.)

Cribratge (`:480`) → talles (`:606`) → extracció (`:1277`) → matching amb `find_pom_master` +
`CustomerPOMAlias` + guard many-to-one (`:1012,953,964`) → confirmació humana de POMs (`:1443`) →
**`confirmar/`** dins `transaction.atomic`, amb tots els 409/422 resolts **abans** de tocar res
(`:1863` `base_size_absent`, `:1908`/`:1922` contenidor de grading). Llavors:

```python
# ── 1. Mana el document: neteja files buides de plantilla i crea NOMÉS els confirmats.
BaseMeasurement.objects.filter(model=model, base_value_cm__isnull=True).delete()
```
— `extraction_views.py:1947-1948`

…i tot seguit `update_or_create` amb `origen='IMPORTED'` (`:1953-1967`).

La política és **explícita i etiquetada com a llei**, no és un accident:

> **NORMES INAMOVIBLES:** 1. Mana el document: crea NOMÉS `BaseMeasurement` dels POMs confirmats. NO
> materialitza la plantilla de l'item (no crida `materialize_poms_view`) i elimina les files buides de
> plantilla preexistents (`base_value_cm=None`).
> — `extraction_views.py:1722-1725`

### B3.3 La col·lisió, exposada (sense decidir)

**Precedència d'orígens: NO EXISTEIX.** `ORIGEN_CHOICES` és una llista **plana** de 8 valors
(`models_app/models.py:550-559`); no hi ha constants, ni enum, ni mapa de prioritat. **L'única
comparació d'`origen` de tot el repo** és `models_app/views.py:827` (`== 'TEMPLATE'`). El patró de
guard per origen **sí existeix** en un altre domini: `dictionary_service.py:158`
(`preserve_manual = (ex.origen == 'MANUAL')`).

**Ordre A — sembra primer, import després** (el flux normal):

| Cas | Post-sembra | Acció de l'import | Resultat |
|---|---|---|---|
| A l'item **amb** valor, i al document | `ITEM_STANDARD` | `update_or_create` (`:1967`) | **el document trepitja l'item**, en silenci |
| A l'item **amb** valor, **no** al document | `ITEM_STANDARD` | cap | **sobreviu actiu** → la fitxa importada queda "contaminada" amb POMs que el client no demanava |
| A l'item **sense** valor (`TEMPLATE`) | `TEMPLATE` | `delete()` (`:1948`) | esborrat dur, **sense log** (`signals.py:248`) |

**Ordre B — import primer, sembra després:** una fila `IMPORTED` amb valor → `skipped` ✅ (l'import
queda protegit). **Però** els POMs del `GarmentPOMMap` que el document no portava es creen com a
`TEMPLATE` nous (`views.py:818`) → **la fitxa importada s'omple de files buides**, que un segon
import tornarà a esborrar. Cicle sorollós.

> **L'asimetria és emergent, no dissenyada:** la sembra respecta l'import per accident de la condició
> `TEMPLATE`+`None`; l'import no respecta la sembra perquè cap línia mira l'`origen` previ.

**Punts de codi on caldria resoldre-ho** (§B6 en dimensiona el cost):

| Punt | `ruta:línia` | Què hi manca |
|---|---|---|
| import — esborrat previ | `extraction_views.py:1948` | filtrar per `origen` |
| import — escriptura | `extraction_views.py:1967` | cap comprovació d'origen/valor previ |
| import — POMs orfes | `extraction_views.py:1948-1975` | ni desactivació ni avís dels vius no mencionats |
| sembra — guard existent | `models_app/views.py:827` | l'únic amb noció de sobirania: ampliar-hi la taula |
| sembra — creació `TEMPLATE` | `models_app/views.py:818` | no mira si el model ja té taula importada |
| definició d'orígens | `models_app/models.py:550-559` | llista plana, sense ordre |
| patró de referència | `pom/dictionary_service.py:158` | l'únic guard per origen del repo |

### B3.4 Superfície de poda: **NO EXISTEIX** on caldria

| Mecanisme | `ruta:línia` | Exposat a UI? |
|---|---|---|
| **DELETE REST dur** | `models_app/views.py:414`, `urls.py:45` | ❌ **NO** — `endpoints.js:107-111` només té `update` i `reorder`; cap `delete` a tot `frontend/src` |
| soft-delete per omissió (`keep_pom_ids`) | `models_app/views.py:1088-1092`, `:1203-1207` | ✅ indirectament |
| soft-delete via xat IA | `models_app/views.py:1577` | ✅ per llenguatge natural |
| buidar valor (fila viva) | `pom/wizard_views.py:192` | ✅ wizard POM |

L'única X per fila del frontend és `EditableTable.jsx:361-366` → `handleDeleteRow` (`:83`, només
estat local) → `keep_pom_ids` (`:119`) → el backend desactiva en desar. **Però `EditableTable` només
es renderitza des de `MeasuresEntryPanel.jsx:317`, que és el flux de GÈNESI** (si el model ja té
valors i no és `entryMode`, el panell surt cap a la consulta, `:113-116`).

**La superfície de treball real —`CheckMeasureEditor.jsx:379` → `MeasureGrid.jsx`— no té cap botó de
suprimir** (grep `delete|remove|ti-x|ti-trash`: 0 resultats).

> **Confirmat: NO EXISTEIX cap UI on el tècnic esculli "d'aquests POMs sembrats, en trec X".** La
> poda existeix només com a efecte col·lateral del desat complet de la taula, i només al flux de
> gènesi. **Lloc natural:** `MeasureGrid.jsx` (ja rep `editable`, ja llista els POMs del model des de
> `CheckMeasureEditor.jsx:214` via `measureSources.jsx`) — hi cabria una columna d'acció per fila.
> L'endpoint dur existeix però és orfe de client.

**⚠️ Dos defectes vius trobats de passada (fora d'abast, anotats, no tocats):**

1. **La sembra s'executa sense confirmació humana.** `MeasuresEntryPanel.jsx:136`: dins l'`useEffect`
   de muntatge, si la taula és buida i l'item no té valors, es fa `POST materialitzar-poms` **sol**.
   Entrar al tab Mesures escriu a BD sense cap gest del tècnic.
2. **`confirmSeed` ignora `selectedPomIds`.** Els chips `POMChipSuggerit` (`:302,310`) semblen triar
   quins POMs se sembren, però `confirmSeed` (`:68-78`) crida `materialitzar-poms`, que sembra **tot**
   el `GarmentPOMMap` (`views.py:791-802`). **La selecció visible no té cap efecte sobre la sembra.**

**Veredicte B3: la col·lisió és real, asimètrica i mig legislada.** La llei "Mana el document" ja
existeix i és conscient; el que no existeix és la **contrapartida** (què passa amb el patrimoni de
plantilla que el document no menciona) ni cap noció de precedència. La poda, que és la vàlvula
natural d'aquest conflicte, **no té superfície**.

---

## BLOC B4 — L'eix de client (LA decisió de domini)

### B4.1 Avui el catàleg d'item no coneix el client

`GarmentTypeItem` (`tasks/models.py:286-347`) **no té cap camp ni FK cap a `Customer`**. Unicitat
`('garment_type','code')` (`:327`) — **cap eix de client a la identitat**: dos items amb el mateix
codi no poden coexistir per a dos clients.

```
GarmentTypeItem (tasks/models.py:286)
  ├─ TaskTimeEstimate            tasks/models.py:353       → customer? NO
  ├─ ProductPriceGTI             commerce/models.py:197    → customer? NO
  ├─ GarmentPOMMap               pom/models.py:437         → customer? NO
  ├─ ItemBaseMeasurement         pom/models.py:476         → customer? NO
  ├─ ItemFitxer                  models_app/models.py:476  → customer? NO
  ├─ PatternFile (branca XOR)    patterns/models.py:46     → customer? NO
  ├─ GradingRuleSet              pom/models.py:544         → customer? SÍ ★ (pom/models.py:552)
  ├─ RuleSetScopeNode            pom/models.py:644         → INDIRECTE (via rule_set)
  ├─ Model                       models_app/models.py:161  → customer? SÍ ★ (models_app/models.py:125)
  └─ (invers) .grading_rule_set  tasks/models.py:319       → SÍ ★ (pointer, no identitat)
```

> **L'eix de client existeix a la capa d'INSTÀNCIA (`Model.customer`) i a la de GRADING
> (`GradingRuleSet.customer`). A la capa de CATÀLEG D'ITEM —POMs, valors base, fitxers, preus— NO
> EXISTEIX.**

### B4.2 El pressupost de referència: què va caldre per a `GradingRuleSet.customer`

| Peça | `ruta:línia` |
|---|---|
| Camp `customer` FK, SET_NULL, `db_constraint=False` | `pom/models.py:552-554` |
| Migració AddField (+ `CustomerPOMAlias` al mateix pas) | `pom/migrations/0029_…py:15-18` |
| **Data-migration de backfill** des de `SizeSystem.customer_codi`, amb guarda per al schema `public` | `pom/migrations/0030_backfill_…py:1-30` |
| Camp `garment_type_item` (node fi de la identitat) | `pom/models.py:544-547` + migració `0039` |
| Camp `origen` (CANONICAL/CLIENT_RUN/IMPORT) — el que fa **parcial** la constraint | `pom/models.py:517-531` |
| **Constraint del contenidor únic**, parcial a `origen='CLIENT_RUN'` | `pom/models.py:610-614` |
| Filtres i display | `pom/views.py:177`, `pom/serializers.py:189-190`, `pom/s2_serializers.py:108-118` |
| **Resolutor de 2 nivells + guarda d'ambigüitat** | `pom/grading_utils.py:577-655` |
| Paritat back/front del predicat d'eixos | `pom/grading_utils.py:558-575` ↔ `gradingAxes.js:88-102,151-162` |
| UI | `CustomerDetail.jsx:183,170`, `RuleSetPicker.jsx`, `ModelWizard.jsx:207,234-247` |
| Germà `CustomerPOMAlias`, unicitat `(customer, client_code)` | `pom/models.py:236-289` (`:279-282`) |

La lliçó operativa d'aquest pressupost: el car **no és el camp**, són el **backfill**, la **constraint
parcial** (Postgres tracta NULLS DISTINCT → `unique_together` sol no serveix) i el **resolutor amb
guarda d'ambigüitat**.

### B4.3 Si calgués l'eix a `ItemBaseMeasurement`: què tocaria

| Àrea | `ruta:línia` | Implicació |
|---|---|---|
| Model — camp nou | `pom/models.py:476` | FK `customer` nullable, **`db_constraint=False` obligat** (pom SHARED ↔ tasks tenant) |
| **Unicitat** | `pom/models.py:495` | `('garment_type_item','pom')` avui. Amb customer nullable cal el patró de `GradingRuleSet`: **dues `UniqueConstraint` parcials** (o `nulls_distinct=False`). `unique_together` sol **no** ho resol |
| Migració | patró de `pom/0026` | AddField additiu; **sense font de backfill** (la fila no té `customer_codi`) → NULL = genèric |
| Serializer / ViewSet / filtres | `pom/serializers.py:385-397`, `pom/views.py:304-334` | additiu |
| **Acció `upsert`** | `pom/views.py:354-355` | la clau passa a `(item, pom, customer)` + validació d'existència (FK sense constraint) |
| **Camí de sembra** | `models_app/views.py:796-797` | avui carrega per item sol; caldria resoldre per `model.customer` **amb fallback al genèric** (paral·lel NIVELL1/NIVELL2 de `grading_utils.py:577-655`) i decidir què fer si `model.customer` és NULL |
| Paquet LOSAN export/load | `export_losan_package.py:244-254`, `load_losan_package.py:350-357` | clau d'upsert i scope |
| Frontend | `MeasurementBaseGrid.jsx:56,150-170`, `MeasuresEntryPanel.jsx:125`, `endpoints.js:533-538`, `ItemAuthoring.jsx` (avui **sense** cap selector de client) | |
| Tests | **NO EXISTEIX** cap test del model ni del camí de sembra | caldria crear-los de zero |

Peces del pressupost de §B4.2 **sense equivalent** i a crear de zero: **resolutor**, **guarda
d'ambigüitat** i **UI de tria de client a la capa d'item**.

### B4.4 Les dades: el conflicte no és teòric

| Schema | GTI amb models | **GTI multi-customer** | Models |
|---|---|---|---|
| `fhort` | 27 | **5** | 1005 |
| `los` | 0 | 0 | 0 |

| GTI | code | clients | models |
|---|---|---|---|
| 8 | `t_shirt` | BRW, LOS | 208 |
| 21 | `shorts` | BRW, LOS | 105 |
| 18 | `trousers` | BRW, LOS | 62 |
| 4 | `shirt_woven` | FTT, LOS | 49 |
| 5 | `blouse` | BRW, LOS | 42 |

**466 dels 1005 models pengen d'un GTI compartit entre clients.** En canvi, `ItemBaseMeasurement`
té 37 files en 1 sol GTI → **el cost de migració de dades d'un eix de client, avui, és pràcticament
nul**. La finestra és ara.

(Nota de context: 45 `GradingRuleSet` a `fhort`, 22 amb `customer` però **només 1 amb
`garment_type_item`** → el backfill del contenidor encara no s'ha fet i la constraint parcial amb
prou feines mossega.)

### B4.5 Consistència amb la sobirania (punt 13 del brief)

**Sí, és consistent, i no calen dades noves — només flux.** §2 de `DECISIONS.md` diu *"la plantilla
(`GarmentTypeItem`) sembra; el model POSSEEIX"*, i el codi ho implementa literalment: la sembra és
**còpia** amb `origen='ITEM_STANDARD'` documentat com a **"copy-at-the-moment"**
(`models_app/models.py:558`), sense cap FK de retorn. Que la fitxa del client sobreescrigui després
**és la sobirania funcionant**, no una violació.

> **El corol·lari incòmode:** si el model posseeix i el document mana, aleshores **un eix de client a
> la plantilla no és necessari per a la CORRECCIÓ** — el client ja diferencia les seves mides al seu
> `BaseMeasurement`. L'eix només compra **estalvi de re-teclejat** (que el segon model del mateix
> client neixi ja amb les mides d'aquell client). És una decisió d'**ergonomia i escala**, no
> d'integritat.

### B4.6 LA DECISIÓ, amb opcions (Patró C — **no decidida aquí**)

| Opció | Què implica | Cost | Risc |
|---|---|---|---|
| **1. Cap eix.** La plantilla és sempre del taller (genèrica). El client viu al model. | Zero codi. Cal assumir re-teclejat per client, o que la 1a fitxa importada faci de plantilla de facto | **Nul** | El valor de "sembrar un model nou en 3 clics" es dilueix per als clients recurrents |
| **2. Eix `customer` nullable a `ItemBaseMeasurement`**, precedència `customer > NULL` a la sembra | El pressupost sencer de §B4.3 (constraint parcial + resolutor + UI) | **Gran** | Duplica a la capa d'item la complexitat que ja va costar cara a `GradingRuleSet` |
| **3. Contenidor separat** (p.ex. `CustomerItemBaseMeasurement`) | Deixa `ItemBaseMeasurement` intacte (constraint, export/load, UI d'autoria) a canvi d'una taula més i un resolutor de 2 nivells | **Mitjà** | Dues taules per al mateix concepte: risc de divergència a llarg termini |

> 💡 Anotació per a la decisió, no decisió: l'opció 2 col·lideix frontalment amb la llei d'Agus del
> 14/07 *"la biblioteca ven forma, el model ven mides"*
> (`PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:1107-1109`). Si aquesta llei es manté, **l'opció 1 és la
> coherent** i el problema del re-teclejat es resol al camí de sembra (mirant el model germà del
> mateix client), no a l'esquema.

**Veredicte B4: l'eix NO EXISTEIX enlloc del catàleg d'item, el conflicte és empíricament real (5
GTI / 466 models), el cost de dades és avui nul, i la decisió és de producte — no de correcció.**

---

## BLOC B5 — Encaix amb el motor de patrons

### B5.1 El motor és **pur**; l'acoblament viu a l'adaptador

`engine/grading_projection.py` (612 línies) **no conté cap `model_id` i no fa cap query**. Rep
`project(doc, snapshot, poms, sews)` (`:150`) i torna un `ProjectionResult` **en memòria** (`:118`).

- **El model Django `GradeRule` NO EXISTEIX**: la projecció **no escriu res a BD**. Els bytes surten
  per `AAMAWriter`/`RULWriter` a `export.py:143+`; l'únic rastre persistit és `ExportAcknowledgement`.
- **La clau de creuament és `POMMaster`, no `Model`**: `pom_id = pom.pom_master_id`
  (`adapters.py:578`) contra `GradedSpec.pom_id` (`adapters.py:499`). La frontissa amb la geometria
  és `PatternPOM.pom_master` (`patterns/models.py:327`). **Això és el que fa el motor portable a
  l'item.**
- Guards durs (`grading_projection.py:161-174`): `approved` · `size_run` no buit · `base_size_label`
  dins el run. Els tres surten del **Model** via `adapters.py:474-476`.
- Cadena real: `views.py:598/619/670` → `export.py:143 build_export` → `adapters.py:459 snapshot()` →
  `project()`.

### B5.2 Què es trencaria amb un patró ancorat a ITEM (llista tancada)

**La pregunta 14 del brief conté una hipòtesi ja superada:** *"fer `model_id` nullable + `item_id`
opcional"* **ja està fet** (§B2.3). El que segueix és el que hi ha **darrere**.

**A · Estructural (FK NOT NULL → cal migració)**

| `ruta:línia` | Trencament |
|---|---|
| `patterns/models.py:447` `SewRelation.model` | **impossible declarar cap costura en un patró d'item** → mata PAT-1 a la branca item |
| `patterns/models.py:517` `SewProposalRejection.model` | impossible rebutjar propostes |
| `patterns/models.py:566` `DartProposalRejection.model` | impossible rebutjar pinces |
| `patterns/models.py:728` `SewToleranceAcceptance.model` | impossible acceptar toleràncies |

**B · Silenciós (el pitjor)**

| `ruta:línia` | Trencament |
|---|---|
| `adapters.py:594-595` | `sew_specs` fa `if pattern_file.model_id is None: return ()` → **l'export d'un patró d'item no validaria CAP costura i el fitxer sortiria per la porta com si tot casés**. Contradiu la llei *"OMISSIONS: MAI EN SILENCI"* de `grading_projection.py:51-56` |

**C · Funcional declarat (fallen dient-ho, no menteixen)**

| `ruta:línia` | Trencament |
|---|---|
| `patterns/views.py:468-475` | `model-poms` → 400. La font correcta per a item seria `GarmentPOMMap` + `ItemBaseMeasurement` |
| `patterns/views.py:572-573` | `grading-versions` → `[]` → **cap export possible** |
| `adapters.py:459-476` | tot el pipeline: `GradingVersion` neix de `SizeFitting.model`; no hi ha equivalent d'item |
| `export.py:422-426` | `_codi_model` → `''` a la meta FTT del DXF |

**D · Propostes semàntiques (~26 punts)** — `seam_proposals.py:30,41,47,55,91,151,155,171,174,177,191,197,236,260`
· `dart_proposals.py:27,39,63,67,81,82,138` · `annotation_views.py:175,185,240,380,610-613,643,665-670,737,768,811,976`.
Tots parteixen de `fp.model_id` per saber què ja està declarat.

**E · Frontend: cap camí d'entrada.** `endpoints.js:664` (`patterns.list` només accepta `{model}`) ·
`PatternTab.jsx:30,62,125` (`fd.append('model', modelId)`) · `TallerPatro.jsx` (**8 llocs** envien
`model`; la ruta és `/models/:id/patro/taller`). Grep `garment_type_item` als components de patró:
**0 hits — NO EXISTEIX cap UI d'item**.

**F · Un bug menor destapat:** `patterns/views.py:406-409` valida "mateix amo" amb un `or` que no
discrimina la branca → un GTI amb el mateix id numèric que el model anterior passaria el check.

### B5.3 D7: on estava i què ha canviat

> `MOTOR_DE_PATRONS_V2.md:69` — «**`ItemBaseMeasurement`** (item amb valors base) | Futur: patró
> d'item + valors base d'item = base paramètrica instanciable a models. No és v1, però el disseny
> d'entitats ho ha de permetre (FK opcionals a item). | **➕ Horitzó**»

**Fase del pla: cap.** D7 és l'**únic** de D1..D14 marcat `➕ Horitzó`; no entra a la seqüència
PAT-0a→PAT-4. El seu únic requisit operatiu era §4.3 (`V2:187-196`, "v1 el deixa NULL sempre"), que va
ser **substituït el mateix dia** per E4 (`V2:233-241`): els 2 FK passen a **ACTIUS des de la primera
migració, amb constraint XOR**.

| Premissa de D7 | Estat avui | Evidència |
|---|---|---|
| `ItemBaseMeasurement` existeix | ✅ **complerta** | `pom/models.py:464-501`, API, UI, 37 files |
| "FK opcionals a item" | ✅ **complerta i superada** | no són opcionals: **XOR obligatori** (`patterns/models.py:109-115`) |
| `GarmentTypeItemAsset` com a vehicle (D6) | ❌ **invalidada** | mai ha existit; vehicle real = `ItemFitxer` (`patterns/models.py:53`) |
| "instanciable a models" (sembra del patró) | 🟡 **parcial** | `source_asset` existeix amb **0 usos escrits**; cap camí item→model per a patrons |
| "base paramètrica" (grading a nivell d'item) | ❌ **NO EXISTEIX i està tancada per decisió** | tot el pipeline neix de `GradingVersion→SizeFitting→Model` (`adapters.py:474`); `ItemBaseMeasurement` és **una sola talla**. Decisió: *"les bases de biblioteca viuen i s'exporten EN TALLA BASE"* (`PLA:1107-1109`) |

**Què ha canviat des del 08/07 que ho fa MÉS BARAT:** el XOR construït i auditat (S3), l'upload d'item
amb tests, la geometria desacoblada del model, el matcher `CustomerPOMAlias` viu, i **la decisió que
elimina la meitat cara** (grading d'item). **Què ho fa MÉS CAR:** el motor semàntic (costures, pinces,
propostes) ha crescut des del 08/07 sobre `model_id` — les ~26 dependències de §B5.2-D **no existien**
quan D7 es va escriure.

### B5.4 Estat viu del motor a BD

**Schema `los`: 0 files a totes les taules `patterns_*`.** El motor és exclusiu de `fhort`.

| Taula (`fhort`) | Files |
|---|---|
| `patternfile` | **5** (tots amb `garment_type_item_id` NULL) |
| `patternpiece` | 38 |
| `patternpoint` | 4.655 |
| `patternsegment` | 572 |
| `patternpom` | 6 |
| `sewrelation` | 10 |
| `sewproposalrejection` | 13 · `sewtoleranceacceptance` 2 · `dartproposalrejection` 0 |

| id | amo | fitxer | versió | current |
|---|---|---|---|---|
| 8, 9 | model 186 | AMELIA AZUL prova.dxf | 1, 2 | no |
| 10 | model 186 | niada.dxf | 3 | sí |
| 11 | **model 163** | TATE.DXF (sense RUL) | 1 | sí |
| 12 | model 174 | CALLIE-…dxf | 1 | sí |

**Model 163:** `BRW-FW26-0001`, base `S`, run `XS·S·M·L`, 25 `BaseMeasurement` actives · PatternFile 11
amb 10 peces / 219 segments / 2 `PatternPOM` · 8 `SewRelation` (5 casat, 2 pinça, 1 frunzit) · **cap
`GradingVersion` aprovada** (79 i 80, totes dues `aprovada=f`) → `views.py:577` retorna `[]` i la
projecció llançaria `GradingNotApproved`. **El Tate no és exportable avui, i el motiu és de dades
(grading sense segellar), no de codi.**

**Veredicte B5: el motor no s'oposa a l'item — el seu nucli ja és agnòstic (creua per `POMMaster`, no
per Model).** L'acoblament és perifèric però ample (~26 punts + 4 FK NOT NULL) i conté **una mentida
silenciosa** que és el primer que caldria tancar, abans de cap migració.

---

## BLOC B6 — Cost i abast

### B6.1 Dimensió per peça

| # | Peça | Dimensió | Per què |
|---|---|---|---|
| **(a)** | **Eix `customer` a `ItemBaseMeasurement`** | **GRAN** (opció 2) · **MITJÀ** (opció 3) · **NUL** (opció 1) | El car no és el camp: és la constraint parcial (NULLS DISTINCT), el **resolutor de 2 nivells amb guarda d'ambigüitat** que no existeix, i la UI de tria de client a la capa d'item que tampoc. Cost de **dades** nul (37 files). Pressupost complet a §B4.3 |
| **(b)** | **Superfície de poda de POMs sembrats** | **PETIT** | El backend ja hi és per dues vies (`keep_pom_ids` soft-delete `views.py:1088-1092`; DELETE dur orfe `urls.py:45`). És una columna d'acció a `MeasureGrid.jsx` + i18n×3. L'única decisió: **soft (`is_active=False`) o dur** — la primera preserva el `MeasurementChangeLog` |
| **(c)** | **Col·lisió import ↔ sembra** | **PETIT de codi, MITJÀ de decisió** | 3 punts d'escriptura (`extraction_views.py:1948`, `:1967`, `models_app/views.py:827`) + un mapa de precedència a `models.py:559`. El patró ja existeix (`dictionary_service.py:158`). El cost real és **decidir la política**, no escriure-la. Inclou els 2 defectes vius de §B3.4 |
| **(d)** | **`PatternFile` a item** | **JA FET (esquema)** + **GRAN (la cua)** | L'ancoratge, el XOR, la migració auditada i els tests **ja existeixen**. La cua: 4 `AlterField`+4 constraints XOR (0 backfill: 10+13+2 files), ~26 punts de query, el guard mut de `sew_specs`, permisos (avui `IsAuthenticated` amb la premissa *"l'escriptura va al MODEL, no a un catàleg"* — `patterns/views.py:282-288` — que **el XOR ja ha invalidat**), i tot el frontend |

> ⚠️ **La lliçó de W6, vàlida aquí:** *"el XOR és mecànicament barat i epistemològicament car… mig XOR
> és pitjor que cap"* (`DIAGNOSI_W6_I_FITXA.md:291-293`). La peça (d) es fa **sencera o gens**.

### B6.2 Ordre de dependència proposat

```
  (c0) 3 línies · sew_specs deixa de mentir          ← independent, gratis, abans de tot
        └─ adapters.py:594-595 → problemes.append(), com fa pom_specs a :547,556

  (c) col·lisió import↔sembra  ──┐   (b) poda de POMs  ──┐
      + els 2 defectes de §B3.4  │       (MeasureGrid)    │
                                 ├───────────────────────┤
                                 ▼                       ▼
                        LA SEMBRA ÉS DE FIAR (el tècnic controla què entra i què surt)
                                 │
                                 ▼
                        (a) DECISIÓ B4 — eix de client  ← Patró C, bloqueja el disseny de (a)
                                 │
                                 ▼
                        (d) PatternFile a item, sencer  ← el més car; demana (c)+(b) fetes
```

**Justificació de l'ordre:**

1. **(c0) primer i sol.** Tancar el silenci de `sew_specs` no depèn de res, són 3 línies, i **mentre
   visqui, qualsevol avenç cap a la branca d'item construeix sobre una mentida**.
2. **(c) i (b) són germanes i van juntes.** Totes dues responen la mateixa pregunta —*qui mana sobre
   la taula de mesures del model*— i comparteixen superfície. Fer (c) sense (b) deixa el tècnic amb
   una llei nova i cap eina per aplicar-la.
3. **(a) després de (b)+(c), i només si la decisió B4 ho demana.** Amb la poda i la precedència al
   lloc, l'estalvi que compra l'eix de client baixa molt: potser la resposta és l'opció 1.
4. **(d) al final.** És el més car, demana `CONFIGURE` a la porta (decisió ja presa,
   `PLA:1104-1106`), i la seva llista de treball (el 2n contenidor del Taller) **s'alimenta de la
   plantilla de POMs de l'item** — o sigui que necessita (b) i (c) resoltes per no heretar-ne
   l'ambigüitat.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT

| Peça | Estat | Evidència |
|---|---|---|
| `ItemBaseMeasurement` (model + API + UI d'autoria) | **EXISTEIX** | `pom/models.py:464-501`, `pom/views.py:304-360`, `MeasurementBaseGrid.jsx` |
| Eix `customer` a `ItemBaseMeasurement` / `GarmentTypeItem` | **NO EXISTEIX** | verificat model + DDL (`tasks/models.py:288-320`) |
| Eix `size_label` a `ItemBaseMeasurement` (multi-talla) | **NO EXISTEIX** (és 1 talla) | `pom/models.py:464-501`, talla al pare `tasks/models.py:307` |
| Sembra item→model amb sobirania | **EXISTEIX** i és idempotent | `models_app/views.py:766-843` (guard a `:827`) |
| Tests d'`ItemBaseMeasurement` / de la sembra | **NO EXISTEIX** | grep sobre tots els `test*.py`: 0 hits |
| `ItemFitxer` (biblioteca de fitxers d'item) | **EXISTEIX**, **0 files** | `models_app/models.py:464`, BD `fhort`/`los` = 0 |
| `GarmentTypeItemAsset` | **NO EXISTEIX NI HA EXISTIT** | `git log -S` = 0 commits; `patterns/models.py:51-53` |
| `PatternFile` ancorat a item (XOR + constraint BD) | **EXISTEIX**, auditat, amb tests, **0 files** | `patterns/models.py:42-56,106-121`; `tests.py:937-957` |
| `PatternFile.source_asset` cablat | **DIFERENT** — el camp hi és, **cap caller l'escriu** | `patterns/services.py:39,73` |
| Camí de sembra del PATRÓ item→model | **NO EXISTEIX** | cap anàleg d'`usar-al-model` per a `PatternFile` |
| Parseig automàtic en pujar un DXF com a `ModelFitxer` | **NO EXISTEIX** (camins separats) | `services_fitxers.py:90` vs `patterns/views.py:322-345` |
| Precedència d'orígens a `BaseMeasurement` | **NO EXISTEIX** | única comparació: `models_app/views.py:827` |
| Llei "Mana el document" a l'import | **EXISTEIX** i és explícita | `extraction_views.py:1722-1725,1947-1948` |
| Contrapartida (què passa amb el patrimoni de plantilla no mencionat) | **NO EXISTEIX** | `extraction_views.py:1948-1975` |
| Superfície de poda de POMs sembrats (treball) | **NO EXISTEIX** | `MeasureGrid.jsx` sense accions; `endpoints.js:107-111` sense `delete` |
| Costures / pinces / propostes en patró d'item | **NO EXISTEIX** (4 FK NOT NULL) | `patterns/models.py:447,517,566,728` |
| Avís en exportar un patró d'item sense costures | **DIFERENT — menteix en silenci** | `adapters.py:594-595` vs llei a `grading_projection.py:51-56` |
| UI de patró d'item | **NO EXISTEIX** | grep `garment_type_item` a components de patró: 0 hits |
| Motor de projecció acoblat a `Model` | **NO** — és pur, creua per `POMMaster` | `engine/grading_projection.py` (0 `model_id`) |

### Riscos per al CTO

| # | Risc | `ruta:línia` | Gravetat |
|---|---|---|---|
| 1 | **Export d'un patró d'item sense cap costura, en silenci** | `adapters.py:594-595` | **ALTA** — un lliurable industrial surt "validat" sense haver-se validat |
| 2 | **La sembra escriu a BD sense cap gest del tècnic** en entrar al tab Mesures | `MeasuresEntryPanel.jsx:136` | **MITJANA** |
| 3 | **La selecció de POMs de la UI no té efecte sobre la sembra** | `MeasuresEntryPanel.jsx:68-78` vs `:302-319` | **MITJANA** — la UI promet un control que no exerceix |
| 4 | L'import esborra files buides **de qualsevol origen**, sense log (`signals.py:248` ignora els NULL) | `extraction_views.py:1948` | **MITJANA** |
| 5 | Escriptura a `PatternFile` d'un item **sense gate `CONFIGURE`**, amb la premissa contrària escrita al codi | `patterns/views.py:282-288` | **MITJANA** (ja detectat a W6 §D.1) |
| 6 | `DELETE` dur de `BaseMeasurement` obert a qualsevol autenticat, orfe de client | `models_app/views.py:414`, `urls.py:45` | **BAIXA** (latent) |
| 7 | Toleràncies d'item que no viatgen al paquet LOSAN | `export_losan_package.py:245-251` | **BAIXA** |
| 8 | Guard "mateix amo" que no discrimina branca del XOR | `patterns/views.py:406-409` | **BAIXA** (latent fins que hi hagi patrons d'item) |
| 9 | `ItemBaseMeasurement` sense timestamps ni autoria — un valor de plantilla no diu qui ni quan | `pom/models.py:464-501` | **BAIXA** |

---

## LA DECISIÓ (Patró C — per a l'Agus, no decidida aquí)

**B4 · L'eix de client a la plantilla d'item.** Les tres opcions són a §B4.6 amb el seu cost. El que
la diagnosi hi aporta:

- **el conflicte és real** (5 GTI / 466 models comparteixen item entre clients),
- **el cost de dades és avui nul** (37 files) — la finestra per decidir barat és ara,
- **no és una decisió de correcció sinó d'ergonomia**: el client ja diferencia les seves mides al
  `BaseMeasurement` sobirà del model,
- i **col·lideix amb una llei ja dictada** (*"la biblioteca ven forma, el model ven mides"*,
  `PLA:1107-1109`), que si es manté fa coherent l'opció 1.

**Decisió germana, més urgent que l'anterior (§B3.3):** *quan un item porta bases i el tècnic importa
una fitxa de client, què passa amb els POMs de plantilla que el document NO menciona?* Avui
**sobreviuen actius i silenciosos**, i contaminen la fitxa importada. Les respostes possibles
—desactivar-los, avisar-ne, o deixar-los i donar al tècnic l'eina de poda (§B6.1-b)— tenen costos
molt diferents i **cap requereix dades noves**.

---

*Diagnosi Patró A. Cap línia de codi tocada. Les propostes marcades `💡` no són decisions.*
