# DIAGNOSI — Encaix de la identitat de peces (PieceRole) al motor de patrons real

> **PATRÓ A · NOMÉS LECTURA.** Cap fitxer de codi creat ni modificat, cap migració, cap seed,
> cap escriptura a BD. L'únic fitxer escrit és aquesta diagnosi.
> Entorn: `/var/www/ftt-staging`, branca `dev`, HEAD `c01f8ac5`. BD `ftt_staging` (PG18:5433), schema `fhort`.
> Data: 2026-07-30.
> Tota afirmació porta `fitxer:línia` o la consulta ORM literal + resultat.
> **NO VERIFICAT** = no s'ha pogut respondre amb el codi/BD davant.

---

## D1 — CENS DEL DOMINI `patterns/`

### D1.0 · On viu i en quin schema

El motor viu a `backend/fhort/patterns/` — 16.125 línies de Python (sense migracions), amb
`engine/` pur (sense Django) i la resta com a projecció ORM.

`fhort.patterns` és **TENANT-ONLY**: apareix a `TENANT_APPS` (`backend/fhort/settings.py:73`)
i **NO** a `SHARED_APPS` (`settings.py:36-59`). Verificat contra la BD, no contra la paraula de Django:

```sql
select table_schema, count(*) from information_schema.tables where table_name like 'patterns_%' group by 1;
-- [('fhort', 13), ('los', 13)]          -- cap fila a 'public'
select table_schema, count(*) from information_schema.tables where table_name = 'pom_pomglobal' group by 1;
-- [('fhort', 1), ('los', 1), ('public', 1)]
select table_schema, count(*) from information_schema.tables where table_name = 'tasks_tasktype' group by 1;
-- [('fhort', 1), ('los', 1)]            -- TaskType també és tenant-only
```

**Conseqüència directa per al disseny:** un `PieceRole` declarat *dins* de `patterns/models.py`
**no pot viure mai al schema `public`** sense afegir `fhort.patterns` a `SHARED_APPS` — cosa que
replicaria les 13 taules de geometria a `public`. Vegeu D3.1.

### D1.1 · Models existents (noms reals, tal com són)

Deu models a `patterns/models.py` (783 línies) + 10 migracions (`0001`–`0010`).

| Model | Línia | Propietari / FKs | Constraints |
|---|---|---|---|
| `PatternFile` | `:33` | `model` (models_app.Model, null) · `garment_type_item` (tasks.GarmentTypeItem, null) · `source_asset` (models_app.ItemFitxer, SET_NULL) · `versio_anterior` (self) · `pujat_per` | `CheckConstraint` XOR model/item `:109-115` · `UniqueConstraint(versio_anterior)` anti-bifurcació `:119-122` |
| `PatternPiece` | `:150` | `pattern_file` (CASCADE) | `UniqueConstraint(pattern_file, nom_block)` `:185-188` |
| `PatternPoint` | `:195` | `piece` (CASCADE) | cap · index `(piece, boundary_index, ordre)` `:235` |
| `PatternSegment` | `:242` | `piece` (CASCADE) | **cap constraint** |
| `PatternPOM` | `:303` | `pattern_piece` (CASCADE) · `pom_master` (**PROTECT**) | `UniqueConstraint(pattern_piece, pom_master)` `:360-363` |
| `SewRelation` | `:427` | `model` (CASCADE) · M2M `segments_a`/`segments_b` → PatternSegment | cap |
| `ExportAcknowledgement` | `:370` | `pattern_file` · `grading_version` (PROTECT) | cap |
| `SewProposalRejection` | `:494` | `model` · `segment_a` · `segment_b` | `UniqueConstraint(segment_a, segment_b)` `:541-543` |
| `DartProposalRejection` | `:551` | `model` · 3 FK a `PatternPoint` | `UniqueConstraint(punt_a, punt_vertex, punt_b)` `:592-594` |
| `SegmentPreference` | `:603` | `apres_de` · `apres_a` (SET_NULL) — **`rol` és CharField, NO FK** `:646` | `UniqueConstraint(rol, accio, t_inici, t_fi)` `:677-681` |
| `SewToleranceAcceptance` | `:701` | `model` · `sew_relation` (SET_NULL) | append-only per codi (`:775-783`) |

**Camps exactes de `PatternPiece`** (el model que la capa d'identitat ha de tocar):

```
pattern_file (FK) · nom_block CharField(120) · rol CharField(120, blank)
contorns JSON[]  · grain JSON|null · metadata JSON{} · raw_entities JSON[]
doblec_original JSON|null · insert_at JSON[] · has_sew bool · has_fold bool · unknown_layers JSON[]
```

`Meta.ordering = ['id']` (`models.py:183`) → **l'ordre de les peces és l'ordre d'inserció = l'ordre
dels BLOCK al DXF.** No hi ha camp d'ordre editable.

### D1.2 · CRÍTIC — què conserva `PatternPiece` avui

L'importador és `patterns/engine/aama_reader.py` (849 l.), cridat des de `patterns/views.py:326`
(`AAMAReader().read(dxf.read())`); qui persisteix és `patterns/adapters.py:207-287`
(`DjangoGeometryStore._save_piece`).

**(a) El block name del DXF → SÍ.** `PieceData.nom_block = block.name` (`aama_reader.py:372`)
→ `PatternPiece.nom_block` (`adapters.py:210`). És, a més, la clau d'unicitat dins el fitxer.

**(b) Els TEXT interns del bloc → SÍ, PARCIALMENT.** `aama_reader.py:311-318` recull els `TEXT`
de la **capa 1** i els passa per `_piece_metadata` (`:453-463`), que mapa quatre claus fixes
(`piece name`, `size`, `quantity`, `material`) i aboca la resta a `extra`. Es desa a
`PatternPiece.metadata` (`adapters.py:226-233`).

> ⚠️ `_parse_key_values` **descarta tota línia sense `:`** (`aama_reader.py:801-802`). Un TEXT nu
> (`FRONT`, sense `Piece Name:`) es perd sense deixar rastre — no va ni a `extra` ni a `raw_entities`.

Evidència a BD (ORM sobre `PatternFile` 10/11/12, camp `metadata`):

```
piece#9  block='BACK'  rol='BACK'  piece_name='BACK' size='M' qty=1.0 mat='SHL' extra={}
piece#23 block='1'     rol='BACK'  piece_name='BACK' size='S' qty=1.0 mat='SHL'
         extra={'category': 'CUT  - 1', 'annotation': 'BROWNIE- BRIJESH'}
piece#38 block='16'    rol='Undefined_1' piece_name='Undefined_1' size='S' mat=''
```

**(c) La capa de cada entitat → SÍ, en tres llocs distints:**

- `PatternPiece.contorns[].layer` (per vora) — `adapters.py:212-220`
- `PatternPoint.rastre` = `{dxftype, layer, handle, extra}` (per punt) — `adapters.py:272` + `models.py:228`
- `PatternFile.empremta.capes_presents` / `capes_desconegudes` (per fitxer) — `adapters.py:63-64`

Evidència: `empremta.capes_presents` del pf#12 (Tuka) = `['1','2','3','4','6','7','8','11','13','14']`,
`capes_desconegudes` = `['11','13']`.

**(d) El grain (L7) → SÍ.** `LINE` de capa 7 → `GrainLineData` (`aama_reader.py:308-310`) →
`PatternPiece.grain = {x1,y1,x2,y2}` (`adapters.py:221-225`). Les 38 peces de la BD tenen `grain` no-nul.

**(e) L6 mirall → es DETECTA i es desa; la simetria NO es materialitza mai.**

`_detect_fold` (`aama_reader.py:470-533`) llegeix la capa 6 si hi és i, si no, dedueix l'eix per
geometria. Es desa a `doblec_original` amb `materialitzat` i `costat` (`adapters.py:244-254`).

Però `unfold_piece` (`aama_reader.py:554`) **no el crida ningú fora dels tests**:

```
grep -rn "unfold_piece|fold_piece" --include=*.py fhort/  (excloent 'def ')
→ només fhort/patterns/tests.py:33,397,414,712,713,730,735
```

Confirmat a BD — 8 de 38 peces amb doblec, **totes** amb `materialitzat=False`:

```
piece#23 '1'/'BACK'  materialitzat=False costat=-1   piece#25 '3'/'FRT AER TOP YOKE' False -1
piece#29 '7'/'C FRT YOKE' False -1                   piece#30 '8'/'WAIST LACE' False -1
piece#33 '11'/'SLV MID LACE' False -1                piece#35 '13'/'SLV CUFF SMOKING RDY' False -1
piece#36 '14'/'SLV CUFF SMOKING BLOCK' False -1      piece#38 '16'/'Undefined_1' False -1
```

**La geometria persistida d'una peça al doblec és MITJA PEÇA.** El docstring del motor diu «el motor
treballa sempre amb la peça sencera» (`aama_reader.py:559-561`); al camí d'importació això no passa.

**Què DESCARTA l'importador** (rellevant per a la identitat):

- Entitats de **capa coneguda** amb un `dxftype` no contemplat: el bucle `aama_reader.py:282-318`
  només tracta `POLYLINE`, `POINT`, `LINE` (capa 7) i `TEXT`. **No hi ha `else`**: un `LWPOLYLINE`,
  `MTEXT`, `ATTRIB` o `SPLINE` sobre la capa 1 **desapareix en silenci** (ni a `raw_entities`, que
  només recull capes desconegudes — `:294-297`). Verificat: `grep "LWPOLYLINE|MTEXT|ATTRIB"` a
  `engine/` → cap resultat.
- Els POMs de la capa `FTT-POM` es **llegeixen** (`aama_reader.py:368`) però **no es persisteixen**:
  `_save_piece` no crea cap `PatternPOM`, i `_load_piece` (`adapters.py:351-398`) no reconstrueix
  `PieceData.poms`. Demostrat en viu sobre el pf#10 (la niada reimportada):

```
AAMAReader().read(pf10.fitxer_dxf.read()):
  BACK:  poms llegits = [('M-M79', 668.354), ('HI RLX', 576.162)]
  FRONT: poms llegits = [('LEG OP', 561.787), ('D.11-M79', 679.296)]
PatternPOM.objects.filter(pattern_piece__pattern_file_id=10).count() → 0
```

### D1.3 · El RUL

**Sí que es llegeix.** `patterns/engine/rul_reader.py` (211 l.), cridat a `patterns/views.py:335`
només si arriba `fitxer_rul` al multipart.

- **On es guarda:** `PatternFile.grade_table` (JSONField, `models.py:95`), serialitzat per
  `adapters.py:112-128`. Estructura:
  `{nom, talles[], talla_base, unitats, unitats_factor_mm, aama_version, autor, regles:{"<num>": {deltes: {talla: [dx,dy]}}}}`.
- **Deltes per punt:** NO existeixen. El RUL guarda deltes **per número de regla**; el lligam amb la
  geometria és `PatternPoint.grade_rule_num` (`models.py:227`), llegit del TEXT `# n` que seu sobre
  el punt (`aama_reader.py:423-450`).
- **Control de coherència DXF↔RUL:** `coherencia_dxf_rul` (`rul_reader.py:159-204`) → avisos no
  bloquejants al 201 (`avisos_coherencia`, `views.py:370-372`).
- A BD: només els 3 `PatternFile` d'AMELIA porten RUL; TATE i CALLIE tenen `grade_table = NULL`.

---

## D2 — ESTAT REAL DE LA TRAÇADORA

### D2.1 · S8 NO s'ha executat

`git log --all -- backend/fhort/patterns` (57 commits) mostra la sèrie `S1…S7` i, després,
`W1…W5`, `W4b`, `A1/A2`, `G6`, `QA-TALLER A–H`, `F1/F2`. **Cap commit `S8:`.** El que hi ha
etiquetat "QA-S8" és un sprint **d'un altre domini** (parser d'import Excel):
`e52d5a1f QA-S8: FIX C — el parser deixa de buscar el codi a una columna que és buida`.

El pla ho corrobora (`PLA_IMPLEMENTACIO_MOTOR_PATRONS.md:762-766`):

> **⏸️ S8 — TRAM FINAL EN PAUSA PER MATERIAL (2026-07-13):** el Tate només té talla base
> (spec RECTI 1, sense deltes) → no es pot generar grading real. […] **S8 es tanca quan arribin.**

I la condició de gate (`:671`): *«Estat de la traçadora: S0–S7 ✅ mecànicament. S8 BLOQUEJAT
esperant l'Agus.»*

**Estat verificat: S0–S7 tancats · Taller W1–W5 + W4b + QA-TALLER A–H tancats · S8 obert.**

### D2.2 · Sobre quin model viu l'AMELIA — i els `PatternFile` reals

`PatternFile.objects.count()` → **5**:

| id | fitxer | v | is_current | propietari | font_cad | peces | RUL | grade_table |
|---|---|---|---|---|---|---|---|---|
| 8 | `AMELIA AZUL prova.dxf` | 1 | **False** | model 186 | polypattern | 4 | sí | sí |
| 9 | `AMELIA AZUL prova.dxf` | 2 | **False** | model 186 | polypattern | 4 | sí | sí |
| 10 | `niada.dxf` | 3 | **True** | model 186 | polypattern | 4 | sí | sí |
| 11 | `TATE.DXF` | 1 | True | model 163 | polypattern | 10 | no | no |
| 12 | `CALLIE-…-3rd FIT-08-07-2026.dxf` | 1 | True | model 174 | **tuka** | 16 | no | no |

Totals: `PatternPiece` 38 · `PatternPoint` 4.655 · `PatternSegment` 580 (auto 381 / natural 169 /
declarat 30) · `PatternPOM` 6 · `SewRelation` 12 · `SegmentPreference` 22.

Identitat dels models (ORM sobre `models_app.Model`):

```
163 BRW-FW26-0001 · "Blusa TATE Crudo"  · Textiles y Confecciones Brownie SL · base S · XS·S·M·L
174 BRW-FW26-0012 · "Blusa CALLIE"      · Textiles y Confecciones Brownie SL · base S · XS·S·M·L
186 FTT-CO27-0001 · "Test pantaló"      · FHORT Textile Tech · base S · S·M·L·XL·XXL
```

**L'AMELIA (un top) segueix muntada sobre el model 186 "Test pantaló"** — la incoherència semàntica
que el pla marcava com a **condició per a S8** (`PLA:614-616`) NO s'ha resolt.

**Dos housekeepings de S7 no executats** (`PLA:665-666`: *«esborrar pf#10 … i VERIFICAR que pf#9
recupera is_current=True»*): el pf#10 hi és i és `is_current`, i el pf#9 continua amb
`is_current=False`. Conseqüència viva: **els 4 `PatternPOM` de l'AMELIA pengen del pf#9 (versió
superada); el patró VIGENT del model 186 no té cap POM ancorat.**

```
pom#13 HI RLX @ 'BACK'  (file 9) = 57.62   pom#14 M-M79    @ 'BACK'  (file 9) = 66.84
pom#15 LEG OP @ 'FRONT' (file 9) = 56.18   pom#16 D.11-M79 @ 'FRONT' (file 9) = 67.93
pom#24 CH     @ 'TATE_FRONT'     (file 11) = 45.13
pom#25 EK2    @ 'TATE_NECK_BAND' (file 11) =  4.77
```

### D2.3 · La UI: on es renderitza el patró i d'on surt el nom de peça

Dues superfícies, amb frontera declarada (`PLA:790-795`: al tab, el FITXER; al Taller, el CONTINGUT):

| Superfície | Ruta / muntatge | Component |
|---|---|---|
| **Taller de Patró** (S4/S5 + W2) | `/models/:id/patro/taller` — `frontend/src/App.jsx:313` | `frontend/src/pages/TallerPatro.jsx` (1.539 l.) + `components/pattern/PatternViewer.jsx` (995 l., Konva) |
| **Tab «Patró»** (la porta) | `ModelSheet` tab — `frontend/src/pages/ModelSheet.jsx:642` | `components/pattern/PatternTab.jsx` (648 l.) |

Dades: `GET /patterns/pattern-files/<id>/geometry/` (`patterns/views.py:425-434`) →
`PatternGeometrySerializer` (`patterns/serializers.py:101-265`), que **sí** serveix `rol` (`:224`)
i `metadata` (`:225`).

**D'on treu el nom la UI: del `nom_block`, sempre. `rol` no es pinta enlloc.**

- `PieceList.jsx:36` → `<strong>{p.nom_block}</strong>` (el docstring de la línia 4 diu «nom, rol»
  però el `rol` no s'hi renderitza)
- `PatternViewer.jsx:990` → `t('pattern.selected_piece', { peca: peca.nom_block, … })`
- `PatternViewer.jsx:430-439` → selecció, focus i imantació, totes per `nom_block`
- `TallerPatro.jsx:883,896,1039` → l'etiqueta `peca:` de POMs i relacions, per `nom_block`

`grep -n "nom_block|\.rol\b|piece_name"` sobre TallerPatro + PatternViewer + PatternTab +
RelationsPanel + ModelPomList → **10 usos de `nom_block`, 0 de `rol`**.

> **Efecte visible avui:** al model 174 (CALLIE, Tuka) la llista de peces del Taller diu
> `1, 2, 3, … 16`. El nom llegible (`BACK`, `NK PIPING`, `MID SLEEVE`…) està a la BD, a `rol` i a
> `metadata.piece_name`, i la UI no el mostra.

### D2.4 · El mode «Marcar POM» (S6)

- **Ancora a PUNTS, no a segments.** `PatternPOM.definicio_mesura` (`models.py:335`) és
  `{"mode":"points","a":<PatternPoint.id>,"b":<PatternPoint.id>}`. Confirmat a BD: els 6 POMs vius
  tenen `mode='points'` amb ids de punt. El mode `landmark` es persisteix i es resol però la UI no
  l'ofereix (`models.py:318-320`).
- **L'entitat de destí és la PEÇA**, no el fitxer: FK `pattern_piece` +
  `UniqueConstraint(pattern_piece, pom_master)` (`models.py:322-324, 360-363`).
- **API:** `PatternPOMViewSet` (`patterns/annotation_views.py:518-557`); la mesura es recalcula al
  servidor i `valor_mesurat_cm` mai s'accepta del client (`:536-542` + `models.py:337-339`).
- **Picker: dues fonts, i la primària no és un cercador.**
  1. **Primària (W3)** — la llista de treball: `GET /patterns/pattern-files/<id>/model-poms/`
     (`patterns/views.py:453-561`), que creua `BaseMeasurement` del model amb els ancoratges.
     Frontissa = `POMMaster`; hi entren `POMGlobal` (nom canònic ×3 idiomes, mini-fitxa) i
     `CustomerPOMAlias` (àlies del client, **només si n'hi ha exactament un** — `views.py:115-143`).
     Renderitzat per `components/pattern/ModelPomList.jsx`.
  2. **Secundària** — `components/pattern/POMPicker.jsx`, que crida `poms.cerca` (endpoint
     `poms/cerca/`), explícitament **no** el `POMBrowser` (`POMPicker.jsx:6-14`).

---

## D3 — PUNTS D'ENCAIX PER A LA CAPA D'IDENTITAT

### D3.1 · On cauria `PieceRole` com a catàleg de SISTEMA

**No existeix res anomenat PieceRole:** `grep -rn "PieceRole|piece_role|rol_peca|RolPeca"` sobre
`backend/` i `frontend/src` → **cap resultat**.

Hi ha **tres precedents distints**, i no són intercanviables:

**(A) `POMGlobal` — canònic a `public` REPLICAT al tenant** (`pom/models.py:9-77`).

- Clau: `codi = CharField(80, unique=True)` (**no** SlugField). Multilingüe natiu:
  `nom_en`/`nom_ca`/`nom_es`; descripció només `_en`/`_ca` (advertit a `patterns/views.py:79-83`).
- L'app `fhort.pom` és a SHARED **i** TENANT (`settings.py:53-55`), i per això la taula existeix als
  tres schemas (verificat per SQL a D1.0).
- **Com se sembra** — `pom/management/commands/extend_pom_catalog.py`, mètode `handle`:

```python
schemas_global = ['public'] + ([tenant] if tenant != 'public' else [])
for sch in schemas_global:
    with schema_context(sch):
        POMGlobal.objects.update_or_create(codi=row['codi'], defaults=…)   # mai .delete()
with schema_context(tenant):
    POMMaster.objects.update_or_create(pom_global=pg, defaults={…})        # 1:1 al tenant
```

  Llei explícita al docstring (`:4-12`): *«NON-DESTRUCTIVE and idempotent … the app resolves
  POMGlobal from the tenant copy»*.
- **`POMMaster` és la còpia tenant editable** (`pom/models.py:145-217`) amb `pom_global`
  **nullable** — un `POMMaster` sense global és vocabulari tenant-only encara no canònic, i porta
  `pendent_revisio` + `origen_import` (`:170-181`). **Aquest és exactament el patró «rol de peça del
  client encara no promogut».**

**(B) `GarmentTypeGlobal` — canònic amb flag `is_system`** (`pom/models.py:80-100`):
`is_system=True` = «catàleg canònic, no esborrable», amb el guard al viewset (`pom/views.py:164-170`,
403 a `destroy`) i escriptura sota capability `CONFIGURE` (`:158-161`). Porta també `display_order`.

**(C) `TaskType` — canònic TENANT amb slug, sembrat per MIGRACIÓ DE DADES** (`tasks/models.py:30-66`):
`code = SlugField(50, unique=True)`, sembra a `tasks/migrations/0025_seed_canonical_task_types.py`
amb `update_or_create(code=…)` i `unseed = noop` (*«revertir l'esquema no ha de destruir dades del
catàleg»*). Docstring del model: *«propietat del sistema; el tenant no l'edita»* — tot i viure al
schema del tenant.

> **La tria és arquitectònica, no estètica.** Si `PieceRole` ha de ser **públic**, el patró a calcar
> és (A) i **el model no pot viure a `patterns/`** (tenant-only, D1.0): hauria d'anar a una app ja
> SHARED+TENANT (`fhort.pom` n'és l'única precedent viva) o obligar a canviar `SHARED_APPS`. Si es
> decideix que és canònic **per tenant**, el patró exacte és (C): `SlugField` únic + migració de
> dades idempotent, zero infraestructura nova.

### D3.2 · `CustomerPOMAlias` — mecànica exacta per calcar

`pom/models.py:237-290`. És el precedent més proper a `PieceRoleAlias`:

| Peça | Detall | Evidència |
|---|---|---|
| Eix | `customer` (FK a `tasks.Customer`, **`db_constraint=False`** perquè la FK creua schemas: `pom` és SHARED+TENANT i `Customer` és tenant-only) | `:250-252` |
| Destí | `pom` → `POMMaster`, **NULLABLE**: un àlies sense destí és «vocabulari del client pendent de mapar», estat legítim del domini | `:253-260` |
| Unicitat | `(customer, client_code)` — **mai** `(customer, pom)`: un client pot tenir N codis per al mateix concepte | `:280-283` |
| Text | `description_en` + `description_local` + `language` (ISO-639-1). `client_description` és **obsolet** (no escriure-hi) | `:261-271` |
| Procedència | `origen ∈ {IMPORT, MANUAL, MIGRACIO, DICCIONARI}` + `pendent_revisio` | `:244-247, 272-273` |
| Consum | `find_pom_master(code, description, customer)` — l'àlies és l'estratègia **(a)**, la de màxima prioritat → `HIGH` | `models_app/extraction_views.py:985-1035` |
| **La porta** | un àlies `pendent_revisio=True` **NO auto-vincula mai**: es degrada a suggeriment `LOW` i la cerca continua | `extraction_views.py:1023-1032` |
| Lectura defensiva | amb 2+ àlies per al mateix POM, el consumidor **calla** en comptes d'inventar una regla de desempat | `patterns/views.py:115-143` |
| Alta massiva | `update_or_create(customer, client_code)` idempotent, reutilitzant el POM tenant-only previ per no acumular orfes | `pom/dictionary_views.py:136-173` |

**Promoció àlies → global: NO EXISTEIX.** `grep -rni "promo"` a `pom/` + `models_app/` no retorna cap
camí àlies→`POMGlobal`. El que hi ha és:

- El substitut de facto: `POMMaster` tenant-only (`pom_global=None`, `pendent_revisio=True`) creat des
  del diccionari (`pom/dictionary_views.py:145-153`).
- **L'ACTE de promoció, com a forma a calcar**: `promoure_a_item_view`
  (`models_app/views.py:3373-3417`) — gate `CONFIGURE` propi, **dry-run per defecte** que retorna el
  diff sencer i no escriu res, `confirm=true` que aplica dins d'una transacció, i la llei *«omple
  forats exclusivament; modificar un valor existent és un acte canònic SEPARAT»*. És el motlle exacte
  per a «promoure un rol de client a rol de sistema».

### D3.3 · On s'insereix la identificació sense tocar el parser

Flux actual de `POST /api/v1/patterns/pattern-files/` (`patterns/views.py:297-373`):

```
1. FILES: fitxer_dxf (obligatori) + fitxer_rul (opcional)      :303-306
2. _resoldre_propietari (XOR model/item)                        :308-310, 375-394
3. _resoldre_versio_anterior (anti-bifurcació, 409)             :312-313, 396-422
4. validate_upload (whitelist compartida)                       :316-322
5. AAMAReader().read()  ── PARSER ──  422 amb detall si falla   :325-330
6. RULReader().read() + coherencia_dxf_rul → avisos             :332-348
7. save_pattern_file()  (fila + bytes + invariant de cadena)    :350-358
8. DjangoGeometryStore().save()  (peces, punts, segments)       :366
9. 201 amb el serializer complet (+ avisos_coherencia)          :368-373
```

**El punt d'encaix net és entre el 8 i el 9**: el `PatternDocument` ja és a la mà, les peces ja tenen
`id` de BD, i el parser no s'ha de tocar. Alternativa igual de neta: **fora del `create`**, com a
endpoint propi (`POST …/pattern-files/<id>/identificar/`) sobre el fitxer ja desat — cap acoblament
amb el parser, i la pantalla de confirmació pot ser reentrant.

**Estat `draft`/`confirmed`: NO EXISTEIX.** Cap camp d'estat a `PatternFile` (`models.py:33-147`) ni a
`PatternPiece` (`:150-192`). L'únic estat de fitxer és `is_current`/`versio` (cadena de versions), i
l'únic gate humà del mòdul és `ExportAcknowledgement`, que és **de sortida** i **precondició dura**
(`:370-385`) — precedent excel·lent de «gate humà append-only amb el text literal desat», però a
l'altre extrem del flux.

**Superfície d'escriptura per a la identitat: avui NO n'hi ha cap.** `PatternPieceSerializer` és
`read_only_fields = fields` (`serializers.py:77`), no hi ha `PatternPieceViewSet` a `patterns/urls.py`
(6 routers: pattern-files, pattern-poms, pattern-segments, sew-relations, sew-proposal-rejections,
sew-tolerance-acceptances), i `PatternPiece.rol` només l'escriu l'adaptador (`adapters.py:211`).
**Ningú no pot corregir avui el nom d'una peça per API.**

### D3.4 · `view_slots`

Existeixen **només** a `POMPlacement`, i **no tenen cap relació amb les peces de patró**:

- Model: `models_app/models.py:1122-1184`; camp `view_slot = models.SlugField(max_length=40)` `:1150`.
- **NO és un enum tancat**, per decisió explícita (`:1148-1149`): *«Slug de vista dins la pàgina:
  canònics 'front'/'back'/'detail', sufix lliure ('detail-coll'). NO és un enum tancat (D4): el
  vocabulari de vistes el fixa el producte.»*
- Unicitat: `(item_fitxer, pom, view_slot)` `:1173-1177` → **ja és 1:N per vista**, que és la
  cardinalitat que el disseny peça→vistes vol.
- Validació al servidor: només `slugify()` (`models_app/pom_placement_views.py:115-117`); obligatori a
  la lectura (`:43-45`).
- Vocabulari suggerit al client: un `<datalist>` amb tres opcions — `frontend/src/pages/TechSheetEditor.jsx:6935`:
  `<option value="front"/><option value="back"/><option value="detail"/>`. Assignació: `:5167`.
- L'àncora és l'objecte sketch del fitxer de catàleg (`sourceItemFitxer` + `viewSlot`,
  `TechSheetEditor.jsx:5174-5177`), **no** una `PatternPiece`.

**No hi ha avui cap taula que relacioni una peça de patró amb una vista.** El mapatge peça→vistes 1:N
és territori verge; el patró de clau a calcar és `(contenidor, entitat, view_slot)` amb slug obert.

---

## D4 — CONTRADICCIONS I RISCOS

### D4.1 · Supòsits del codi que xoquen amb el corpus

> ⚠️ `TAXONOMIA_PECES_PATRO.md` **no és accessible des d'aquesta sessió** (viu al vault; a
> `docs/diagnosis/` només hi ha `CATALEG_PECES_TENANT.md`, que és el catàleg de **prendes**
> GarmentTypeItem, no de peces de patró). Els números F només es poden tractar segons el que el brief
> n'enuncia. Tot el que segueix és evidència de codi/BD, no lectura del corpus.

**(1) `Piece Name` com a TEXT sempre (F34, Gerber) — supòsit CONFIRMAT al codi, però amb un fallback
que ja el salva a mitges.**

`aama_reader.py:376`: `rol = metadata.piece_name or block.name`. Hi ha degradació ordenada, però tres
forats reals:

- El TEXT ha de ser `dxftype()=='TEXT'` **i** de la capa `'1'` **i** contenir `':'` (`:311-318` +
  `:801-802`). `MTEXT`/`ATTRIB` → **descartats en silenci** (D1.2).
- La clau ha de ser literalment `piece name` en anglès (`:456`). **Sí, s'assumeix un sol idioma**: un
  CAD que escrigui `Nom peça:` o `Nom de la pièce:` cau a `metadata.extra` i el `rol` es queda amb el
  `block.name`. El material real ho tolera (`extra={'category':…, 'annotation':…}` al Tuka) però és
  tolerància, no disseny.
- **Quan el fallback s'activa, el resultat és inservible per a la identitat.** Al Tuka els noms de
  bloc són ordinals: `PatternPiece.nom_block ∈ {'1'…'16'}`. Si el TEXT no hi fos, tota la identitat
  del CALLIE seria `1..16` — i és **exactament aquest camp** el que la UI pinta (D2.3).

**(2) Una peça per nom (F21/F35, talles materialitzades) — el supòsit existeix i es reparteix en TRES
nivells amb comportaments diferents:**

- `UniqueConstraint(pattern_file, nom_block)` (`models.py:185-188`) → **sobreviu**: en un DXF de
  talles materialitzades els blocs es diuen diferent (`FRONT_S`, `FRONT_M`).
- `PatternDocument.piece(nom_block)` (`engine/geometry.py:352-356`) i tot el motor de projecció, que
  indexa per `nom_block` (`PointRef(peca.nom_block, …)` a `engine/grading_projection.py:379,409,420`;
  `fora[(peca.nom_block, i, j)]` a `export.py:362-365`) → **sobreviu**, però tractaria N talles com N
  peces independents.
- **`SegmentPreference.rol` NO sobreviu.** És un CharField amb
  `UniqueConstraint(rol, accio, t_inici, t_fi)` (`models.py:646, 677-681`) i `rol_de_peca()` retorna
  `(piece.rol or piece.nom_block).upper()` (`patterns/preferences.py:32-42`). Amb talles
  materialitzades, les 5 talles del mateix davanter **col·lapsen en una sola clau** i les preferències
  s'hi barregen. A BD ja hi ha 22 files agrupades per aquest `rol` (`MID SLEEVE` 4, `TATE_BACK` 3,
  `BACK` 4…). **Aquest és el punt exacte on `PieceRole` xoca amb el que ja hi ha:
  `SegmentPreference.rol` ÉS un proto-PieceRole informal, sense catàleg i sense FK.**

**(3) L14 (capa de cosit) present (F5) — el supòsit està EXPLÍCITAMENT descartat al codi.**

`aama_reader.py:21-22`: *«Res del que no hi és s'assumeix: si no hi ha línia de cosit (capa 14),
`has_sew` és False»*. Es constata a `has_sew` (`:365`) i `PatternDocument.te_cosit`
(`engine/geometry.py:362-365`); el serializer fa `SEW si n'hi ha, si no CUT`
(`serializers.py:15-26`). A BD conviuen els dos mons: AMELIA `has_sew=False` a les 4 peces, TATE 8/10
amb capa 14, CALLIE 13/16. **Aquí NO hi ha contradicció.**

**(4) Un sol idioma — SÍ, assumit en dos llocs.** Les claus de metadades del DXF (punt 1) i, a la
banda de sortida, `_metadata_texts` (`engine/aama_writer.py:255-268`) que reescriu literalment
`Piece Name:`, `Size:`, `Quantity:`, `Material:` i fa `clau.title()` per als `extra`. Una capa
d'identitat que reanomeni la peça i vulgui que el nom torni al DXF exportat haurà de decidir **què**
s'escriu a `Piece Name:` — avui hi va `metadata.piece_name`, mai `rol`.

**(5) Col·lisió de vocabulari (no de codi, però mata diagnosis).** Al domini FTT, **«peça» ja vol dir
prenda**: `GarmentTypeItem` = «Peça de roba» (57 items a `docs/diagnosis/CATALEG_PECES_TENANT.md`),
mentre que `PatternPiece.verbose_name = 'Peça de patró'` (`models.py:181`). El nom del catàleg nou
hauria de desambiguar-ho des del primer dia.

### D4.2 · Codi mort o a mig fer de S0–S8

| Què | Evidència | Veredicte per a la capa d'identitat |
|---|---|---|
| `unfold_piece` / `fold_piece` | només cridats als tests (D1.2e) | **A MIG FER.** La simetria mai es materialitza; les 8 peces amb doblec de la BD són mitges peces. La lateralitat del disseny hi topa de cara. |
| `PieceData.poms` al viatge de tornada | `_save_piece` no crea `PatternPOM`; `_load_piece` no reconstrueix `poms` (`adapters.py:351-398`). Demostrat: pf#10 llegeix 4 POMs de la capa FTT-POM, en persisteix **0** | **FORAT REAL.** Trenca la promesa `load(save(doc)) ≡ doc` del port (`adapters.py:167-169`) quan el DXF porta la nostra pròpia capa. Els POMs es reinjecten només a l'export (`export.py:404`). |
| `PatternPOM.MODE_LANDMARK` | persistit i resolt, sense camí d'UI (`models.py:318-320`); `pom_specs` l'exclou de la niada amb avís (`adapters.py:555-560`) | **VIU però inert.** No cal tocar-lo. |
| `PatternPiece.rol` | l'escriu només l'adaptador; cap serializer escrivible, cap viewset, la UI no el pinta | **EL PUNT D'ENTRADA NATURAL de la capa nova** — avui és un camp mort a la pràctica. |
| `SegmentPreference.rol` | 22 files vives, clau de text sense catàleg | **A REUTILITZAR o migrar**, no a duplicar (v. D4.1.2). |
| `POMMaster.is_key_measure` | retorna `False` fix, «no tenim camp equivalent» (`pom/models.py:213-217`) | Fora d'abast, anotat. |
| `CustomerPOMAlias.client_description` | marcat OBSOLET, no escriure-hi (`pom/models.py:262-265`) | **Si es calca el model, NO calcar aquest camp.** |
| Housekeeping de S7 no executat | pf#10 viu i `is_current`; pf#9 amb els POMs però superat | **PUNT CALENT DE DADES** (D2.2). |

---

## PUNTS D'ENCAIX NETS

*(on la capa nova entra sense fregament)*

1. **`PatternPiece.rol` com a receptacle del rol resolt.** Camp que ja existeix (`models.py:157`),
   l'escriu un sol lloc (`adapters.py:211`), no el llegeix cap UI i no té constraint. Afegir-hi al
   costat una FK (`piece_role`) i un origen (`llegit`/`confirmat`/`corregit`) no trenca res que
   estigui en ús.
2. **El pas post-parse a `views.create` (entre `:366` i `:368`)**, o millor, un endpoint propi sobre
   el fitxer ja desat. El parser no s'ha de tocar en cap dels dos casos: el `PatternDocument` ja és a
   la mà i les peces ja tenen `id`.
3. **`PieceRoleAlias` per-tenant calcant `CustomerPOMAlias`**: eix `customer`, destí **nullable**,
   unicitat `(customer, client_code)` mai `(customer, rol)`, `origen` + `pendent_revisio`, i **la
   porta**: un àlies pendent no auto-vincula mai (`extraction_views.py:1023-1032`). Tot el pes de la
   lliçó QA-S8 ja està pagat i escrit.
4. **La forma del catàleg canònic**: `TaskType` (`tasks/models.py:30-66`) + migració de dades
   idempotent `update_or_create(code=…)` amb `unseed = noop`
   (`tasks/migrations/0025_seed_canonical_task_types.py`). Si el catàleg és per tenant, això és
   copiar-enganxar.
5. **La forma de la promoció**: `promoure_a_item_view` (`models_app/views.py:3373-3417`) — gate
   `CONFIGURE`, dry-run per defecte amb diff sencer, `confirm=true` transaccional, «omple forats, mai
   sobreescriu».
6. **La forma del gate humà**: `ExportAcknowledgement` (`models.py:370-424`) i
   `SewToleranceAcceptance` (`:701-783`) — append-only, snapshot congelat, text literal desat. Si la
   pantalla de confirmació ha de deixar rastre auditable, el motlle ja existeix **dins del mateix
   mòdul**.
7. **`view_slot` com a slug obert amb unicitat composta** (`models_app/models.py:1150, 1173-1177`): la
   cardinalitat 1:N per vista ja està resolta i validada per `slugify`. Un `PieceViewSlot` en calcaria
   la clau sense inventar res.
8. **`PatternSegment.nom` i `SewRelation.nom`** (`models.py:291, 466-469`) ja consagren la llei «el
   bateig humà mana i es conserva; el generat no es desa». La identitat de peça hauria de dir el
   mateix i pot citar el precedent.

---

## PUNTS CALENTS

*(on caldrà decisió humana o refactor petit)*

**PC-1 · `PieceRole` públic vs per-tenant — decisió d'arquitectura, no de gust.** `patterns` és
tenant-only (SQL a D1.0). Un catàleg a `public` obliga a posar l'app a `SHARED_APPS` (replicaria 13
taules de geometria a `public`) o a allotjar el model fora de `patterns/`. **Decisió d'Agus abans
d'escriure la primera línia.**

**PC-2 · `SegmentPreference.rol` ja és un proto-PieceRole.** 22 files vives amb clau de text i
`UniqueConstraint(rol, accio, t_inici, t_fi)`. Si neix `PieceRole` i `SegmentPreference` continua amb
el seu CharField, hi haurà **dues nocions de rol** al mateix mòdul. Migrar-lo és petit (backfill per
`rol_de_peca`); ignorar-lo és car.

**PC-3 · La UI pinta `nom_block`, mai `rol` (10 usos vs 0).** El model 174 (Tuka) ensenya `1..16`
avui. El canvi és mecànic però toca 4 fitxers i la selecció/imantació del canvas
(`PatternViewer.jsx:430-439`), que **usa `nom_block` com a identificador funcional**, no com a
etiqueta: separar «id de peça» de «nom mostrat» és el refactor de veritat.

**PC-4 · Els POMs de la capa FTT-POM es llegeixen i no es persisteixen** (4 llegits / 0 desats al
pf#10). Qualsevol capa d'identitat que vulgui reimportar un fitxer nostre i «reconèixer» el que hi
havíem escrit topa amb això primer.

**PC-5 · La simetria no es materialitza mai** (8/38 peces mitges a BD, `unfold_piece` només als
tests). **Lateralitat i estat de peça no es poden dissenyar sense resoldre-ho**: una peça al doblec no
té costat esquerre/dret; en té mig.

**PC-6 · Entitats de capa coneguda amb dxftype no contemplat es perden en silenci** (`LWPOLYLINE`,
`MTEXT`, `ATTRIB`; `aama_reader.py:282-318`, sense `else`). Amb el material actual (2 CAD) no ha
explotat; amb Gerber/Optitex podria fer desaparèixer el nom de la peça i el contorn alhora, i **el
sistema no ho diria**.

**PC-7 · No hi ha cap `status` a `PatternFile`/`PatternPiece`.** La pantalla de confirmació n'exigeix
un (o un registre append-only equivalent). Decisió: ¿estat al fitxer, estat per peça, o esdeveniment
append-only calcant `SewToleranceAcceptance`? Recomanació: **no afegir un flag mutable a
`PatternPiece`** — el mòdul ja té dos precedents d'auditoria append-only i cap flag d'estat, i
trencar-ho seria la primera excepció.

**PC-8 · Dades d'staging brutes per a la QA de la capa nova.** L'AMELIA (top) segueix sobre el model
186 «Test pantaló»; el pf#10 (niada reimportada) és `is_current` i el pf#9 (que té els 4 POMs) no ho
és. Qualsevol prova d'identificació sobre el 186 partirà d'un cas semànticament fals. **Els dos
housekeepings de S7 continuen pendents i són d'execució humana.**

**PC-9 · Talles materialitzades.** Cap fitxer del material actual n'és (tots tenen `Size` únic: M, S,
S). El disseny hi ha de decidir si `PieceRole` és una propietat de la peça o del **grup de peces** que
comparteixen rol amb talla diferent — i `SegmentPreference` en depèn (PC-2).

**PC-10 · Cap superfície d'escriptura per a peces.** No hi ha `PatternPieceViewSet` ni serializer
escrivible (`patterns/urls.py`, `serializers.py:77`). La capa d'identitat n'ha d'obrir una — i aquest
mòdul té la llei explícita que **l'escriptura no passa pel serializer genèric** (`views.py:5-7`):
caldrà servei propi, com `save_pattern_file`.
