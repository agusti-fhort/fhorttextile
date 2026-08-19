# MAPA DE TOC · INSTÀNCIA DE POM — REGISTRE D'EXECUCIÓ DEL TRAM

Data: 2026-07-31 · **Patró A PROFUND (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, HEAD `72d2e579`
BD auditada: `ftt_staging` @ 5433 (`fhort` · `los` · `public`) · OpenAPI: `GET /api/schema/` → **200, 743 057 bytes, 364 paths**

**Què és aquest document.** El registre complet dels nodes que toquen la cadena de mesura per a un canvi
d'identitat de `(model, pom, capa)` a `(model, pom, capa, INSTÀNCIA)`. **No és una diagnosi nova**:
`DIAGNOSI_INSTANCIES_POM.md` (31/07) ja va establir el QUÈ i el PER QUÈ, i va declarar els seus límits.
Això és **l'EXHAUSTIVITAT** — perquè cap run d'implementació torni a descobrir nodes en marxa.

**Mètode: triangulació.** Tres camins independents, sis investigadors en paral·lel:
**Camí 1** des dels models (related_name inclosos, el forat clàssic del grep) ·
**Camí 2** des dels contractes (12 `urls.py` sencers → OpenAPI → frontend, backoffice inclòs) ·
**Camí 3** des de les dades (qui pobla de debò cada taula a staging).

**Convenció.** `fitxer:línia` verificat a HEAD `72d2e579`. **"NO EXISTEIX" = confirmat absent.**
**REGLA D'OR aplicada:** en cas de dubte, el node és DINS amb ⚪ i nota. Preferim files sobreres a forats.
**Cap proposta de fix.** El registre i prou.

**Res tocat:** cap escriptura a BD, cap fitxer del repo modificat, cap migració, cap `npm run build`,
cap management command executat. L'única escriptura és aquest document.

---

## 0 · RESUM EXECUTIU

**1. L'accident ja està armat, i no l'espera la instància: l'espera C4.**
`pom/services.py:1033-1043` — `_upsert_graded_spec`, **l'escriptor únic de tot el motor de grading** — fa
`update_or_create(grading_version_id, pom_id, size_label)`. La unicitat de `GradedSpec` és
`('grading_version','pom','size_label','capa')` **des de C1** (`fitting/models.py:220`). **El lookup ja
diverge de l'esquema avui**; l'únic que ho tapa és la comporta `CHECK capa='exterior'`. **Retirar les
comportes a C4 sense tocar aquest node és l'accident**, sense que cap instància hi hagi entrat.
Té set germans exactes (§5.2).

**2. Set nodes no s'adapten: s'han de RE-DECIDIR.** No col·lapsen — **bloquegen activament** el cas que
la instància vol legitimar, i ho fan amb acta escrita al codi. `pom/size_map_views.py:54-75` ·
`models_app/extraction_views.py:1148-1193` · `:1734,1753` (`pom_ja_usat`) · `pom/services.py:613-622` ·
`seed_losan_rules_v2.py:128-134` · `patterns/models.py:430-437` · `frontend/SizeMapSetup.jsx:340-346`
(«decisió CTO: bloquejar»). Els **casos reals que citen als seus docstrings** — BRW `U2`/`U3`→POM `U`,
`F`/`FF`→POM 389, LOS `H.11`/`H.16` — **SÓN** el cas de dues instàncies (§7).

**3. Dos forats d'ONADA 1, no d'instància — peten amb la segona CAPA.**
`patterns/views.py:552-556` i `tenants/federation_service.py:593` llegeixen `BaseMeasurement`
**sense àncora `capa`**, perquè `RECENS_DELTA_ONADA1_2026-07-31.md:222-224` va declarar `patterns/*`
fora d'abast i la federació no es va mirar. **No esperen la instància: esperen la capa.** Han d'entrar a
`top-up-lectors` (§5.1).

**4. El green flag «OpenAPI 0 diffs» és cec on més importa.** Baixat i analitzat l'esquema real:
**54 dels 80 endpoints de la cadena (68%) declaren `'200': description: No response body`** — són
function views sense serializer, i spectacular no en té la forma. Entre ells: `base-stages/`,
`graded-table/`, `repas/`, `pom-placements/`, `taula-mesures/`, `base-measurements/` i els set
d'`import-sessions/`. **Un canvi de forma de payload hi produiria zero diff** (§4.4).

**5. El patró dominant segueix sent el `dict {pom_id: …}`, i ara està comptat.**
De **831 files brutes** dels sis investigadors → **487 nodes únics** després de deduplicar per
`fitxer:línia`. **COL·LAPSA silenciós: 268.** PETA: 79. IGNORA-2a: 92. OK/⚪: 48.
Cap dels 268 peta. Tots pinten, i produeixen diffs, deletes i verificacions **verdes** sobre un
univers incomplet.

**6. Un test afirma el col·lapse com a comportament esperat, i demana caure.**
`models_app/test_seccio_captura.py:156` `test_DUES_SECCIONS_AMB_EL_MATEIX_POM_COL·LAPSEN` →
`assertEqual(files.count(), 1, 'la clau encara col·lapsa: si això falla, la clau ha canviat')`.
Docstring: *«Aquest test hi és perquè el dia que algú toqui la clau, ho vegi caure aquí i sàpiga que era
conegut.»* És el pin deliberat del tram (§6.3).

**7. El deute de C1 al copiador de tenants té data de caducitat pròpia.**
`tasks/management/commands/bootstrap_tenant.py:162` declara la clau natural de `GarmentPOMMap` com
`('garment_type_item','pom')` quan la BD la té amb `capa` (`pom/models.py:612`). Avui la comporta ho tapa.
**El dia que C4 la retiri, el copiador comença a perdre files en silenci** — i s'activa des del
**backoffice**, en un subprocés detached amb stdout a `DEVNULL` (§5.1, §8.2).

**8. La bona notícia: la via sana ja existeix i està provada.** El frontend ja indexa per `bm_id`/PK de
fila a 13 punts, i `TechSheetEditor.jsx:3462` prova `bmById` **abans** que `bmByPom`. I el repo té les
tres peces de mètode que la instància necessita, ja verdes: el **harness de dues files germanes**
(`test_lectors_capa_onada1.py:35,84`), la **resposta canònica a l'ambigüitat** (`base_set_ambigu` 409 amb
candidats, `pom/views.py:468-490`; i `_alies_unics_del_customer`, `patterns/views.py:135-146`, que **es
calla** quan no pot desambiguar) i un **discriminant ordinal ja existent** (`PatternPiece.ordinal`,
`patterns/models.py:212`).

---

## 1 · COM LLEGIR EL REGISTRE

### 1.1 · Columnes

| columna | valors |
|---|---|
| **tipus** | `READ-dict` · `READ-list` · `WRITE-create` · `WRITE-update` · `WRITE-delete` · `COUNT-gate` · `CONTRACT-api` · `CONTRACT-engine` |
| **amb 2 inst.** | `COL·LAPSA` (perd dades en silenci) · `PETA` (excepció / IntegrityError) · `IGNORA-2a` (n'agafa una i oblida l'altra) · `OK` |
| **risc** | 🔴 col·lapse silenciós · 🟠 excepció o bloqueig · 🟡 arbitrari / de significat · ⚪ dubte o innocu |
| **camins** | quins dels tres camins el van caçar — `1` models · `2` contractes · `3` dades. **Un sol camí = sospitós de tenir germans ocults.** |

### 1.2 · Vocabulari d'ONADES

| onada | què hi entra | criteri |
|---|---|---|
| **`C1-ins`** | esquema: camp nou, `unique_together`, comporta CHECK, migració, backfill | on neix la columna |
| **`top-up-lectors`** | lectors la clau dels quals **ja va créixer a `(pom, capa)` a l'Onada 1** i només ha de créixer un element més | els 11 fitxers de l'Onada 1 + els 2 forats que en van quedar fora |
| **`Onada2`** | escriptors que han d'estampar la instància | `create` / `update_or_create` / `get_or_create` / poda |
| **`C4-ins`** | contracte d'API o UI — només es mou quan s'alça la comporta | payload, serializer, frontend |
| **`F2-patrons`** | motor de patrons i format d'intercanvi | Fase 2, fora d'aquest tram |
| **`consolidació-catàleg`** | fusió/sembra/àlies de catàleg — no és feina de clau, és de dades | `consolidate_*`, `load/export_*`, `bootstrap_tenant` |
| **`FORA: <motiu>`** | no toca la cadena, o hi és per la regla d'or | sempre amb motiu explícit |

### 1.3 · Els 11 fitxers que l'Onada 1 SÍ va tocar (base de `top-up-lectors`)

Verificat contra els 9 commits vius: `pom/s10_views.py` · `s11_views.py` · `s6_views.py` · `s8_views.py`
(C1) · `pom/services.py` `_load_model_overrides` (C2) · `fitting/graded_spec_views.py` (C3) ·
`fitting/repas_views.py` (C4) · `fitting/serializers.py` + `models_app/serializers_size_check.py` (C5) ·
`models_app/pom_placement_views.py` (C6) · `models_app/views.py` `_sembra_step` (C8) + `base_stages_view` (C9).
**`pom/grading_views.py` NO hi és: C7 va ser revertit** (`6b431865`).

---

## 2 · TAULA DE CONVERGÈNCIA

### 2.1 · Nodes per camí

| | Camí 1 (models) | Camí 2 (contractes) | Camí 3 (dades) |
|---|---|---|---|
| files brutes emeses | 578 (1A 176 · 1B 285 · 1C 117) | 253 (2A 63 · 2B 158 · 2C 32) | 22 taules × 6 mètriques |
| **nodes únics després de deduplicar** | **352** | **206** | (no emet nodes de codi) |
| **intersecció 1∩2** | colspan → **71** | | |
| **només camí 1** | **281** | | |
| **només camí 2** | | **135** | |
| **TOTAL ÚNIC (1∪2)** | colspan → **487** | | |

**Baseline mecànic independent** (grep meu, no d'agent, per validar l'ordre de magnitud):
**547 referències `<Taula>.objects`** a tot `backend/fhort/` fora de migracions · **324 hits** de
`pom_id|pomId|pom_master_id|bm_id|byPom` a `frontend/src` en **23 fitxers** · **0 hits** a
`frontend-backoffice/src`. Els 487 nodes cauen dins d'aquest sobre.

### 2.2 · Nodes caçats per UN SOL camí — els sospitosos

**[SOLO-CAMÍ-1] · 49 nodes.** Cap grep de `<Taula>.objects` els troba. Tres focus:

| focus | nodes | per què són invisibles |
|---|---|---|
| **related_name com a STRING de config** | `pom/seed_data/consolidate_pom_los.py:30-34` (3 llistes, 11 accessors) + consumidors `consolidate_pom_catalog.py:113`, `:249` | `getattr(prim, rel)` — cap grep de nom de model hi arriba |
| **accessors inversos vius** | 13 usos: `model.grading_rules` ×5 · `obj.linies` ×5 · `model.base_measurements` ×1 · `gv.graded_specs` ×4 · `piece.poms` ×5 · `Count('pom_maps')` · `Count('measurements')` · `Prefetch('regles')` | el nom de la taula no hi apareix |
| **claus naturals declaratives** | `bootstrap_tenant.py:154,162,163` · `federation_service.py:542-552` | la clau és una tupla de strings en una taula de config |

**[SOLO-CAMÍ-2] · 37 nodes.** El problema és la **forma del contracte**, no la taula:
`keep_pom_ids` (`views.py:1774,1812,1847,1941`) · `deltes: {str(pom_id): …}` (`:1736`) · id sintètic
`"{pom_id}:{talla}"` (`:2792` i `fittingGridAdapter.jsx:144`) · `pom_id` **al PATH** (`:3911`, `:3993`,
`regles/{pom_codi}/`) · els **5 serializers sense cap camp d'eix** · `key={r.pom_id}` de React ×4 ·
l'absència d'store global al frontend · el payload cap al motor de visió (`TechSheetEditor.jsx:5652`) ·
l'etiqueta DXF `FTT "{codi}"` (`ftt_pom_layer.py:124`).

**Camí 3 no emet nodes de codi però tanca tres preguntes que cap grep respon** (§9).

### 2.3 · Lectura de la convergència

- **La intersecció és petita (71/487 = 15%)** i això **és el resultat esperat, no una alarma**: els tres
  camins miren coses diferents. Un cens per un sol camí hauria perdut **entre el 28% i el 58%** dels nodes.
- **El camí 2 va caçar 135 nodes que el camí 1 no pot veure**, i el camí 1 va caçar 281 que el camí 2 no
  pot veure. **Cap dels dos és redundant.**
- **On els tres camins convergeixen és on el risc és màxim**: `pom/services.py:771` i `:1033` ·
  `models_app/extraction_views.py:2560` · `models_app/pom_placement_views.py:52-64,135` ·
  `models_app/services_size_check.py:33-42` · `tenants/federation_service.py:542-552,593`.

---

## 3 · EL REGISTRE, PER ONADA

> Files deduplicades per `fitxer:línia`. Quan dos investigadors van donar rangs lleugerament diferents del
> mateix node, s'ha conservat el rang verificat a HEAD.

### 3.1 · `C1-ins` — ESQUEMA (74 nodes)

**Unicitats i comportes de la cadena** (les 14 + les 9 CHECK). Cadascuna ha de decidir si creix.

| fitxer:línia | taula | tipus | clau avui | amb 2 inst. | risc | camins |
|---|---|---|---|---|---|---|
| `models_app/models.py:725` | BaseMeasurement | CONTRACT-engine | `(model, pom, capa)` | PETA | 🟠 | 1,2 |
| `models_app/models.py:730` | BaseMeasurement | CONTRACT-engine | `ordering=['model','capa','ordre','pom']` | IGNORA-2a (ordre no determinista entre germanes) | 🟡 | 1 |
| `models_app/models.py:752` | BaseMeasurement | CONTRACT-engine | `CheckConstraint(capa='exterior')` | OK | ⚪ | 1 |
| `models_app/models.py:637,681,686` | BaseMeasurement | CONTRACT-engine | `nom_fitxa(20)` · `nom_canonic_model(160)` · `nom_traduit_model(160)` — **cap unicitat: NO EXISTEIX** | — | ⚪ | 1 |
| `models_app/models.py:654-659` | BaseMeasurement | CONTRACT-engine | comentari que **ja declara el forat**: «la clau segueix sent `('model','pom')`… travessa 5 taules més» | — | ⚪ | 1 |
| `models_app/models.py:813,816,825,831` | MeasurementChangeLog | CONTRACT-engine · WRITE | `ordering` per `(model,pom,created_at)` · CHECK · **`save()` i `delete()` refusen (append-only)** | IGNORA-2a · **PETA si el backfill hi passa** | 🟠 | 1 |
| `models_app/models.py:878,879,882` | ModelGradingOverride | CONTRACT-engine | `(model,pom,size_label,capa)` · ordering · CHECK | PETA | 🟠 | 1,2 |
| `models_app/models.py:960` | ModelGradingRule | CONTRACT-engine | **`(model, pom)` sense capa** (decisió 3c.1, `:900-914`) | **DECISIÓ OBERTA**: ¿dues instàncies comparteixen delta? | 🟠 | 1,2 |
| `models_app/models.py:1162,1164,1167` | SizeCheckLine | CONTRACT-engine | `(size_check,pom,capa)` · ordering · CHECK | PETA | 🟠 | 1,2 |
| `models_app/models.py:1136-1139` | SizeCheckLine | CONTRACT-engine | FK a POMMaster amb `related_name='+'` → **cap accessor invers** | OK | ⚪ | 1 |
| `models_app/models.py:1336,1340,1345` | POMPlacement | CONTRACT-engine | `(item_fitxer,pom,view_slot,capa)` **sense `condition`** · CHECK · índex | PETA | 🟠 | 1,2 |
| `fitting/models.py:220,224-228` | GradedSpec | CONTRACT-engine | `(grading_version,pom,size_label,capa)` · CHECK | PETA | 🔴 | 1,2 |
| `fitting/models.py:383,400,405` | PieceFittingLine | CONTRACT-engine | `related_name='+'` · `(piece_fitting,pom,size_label,capa)` · CHECK | PETA | 🔴 | 1,2 |
| `fitting/models.py:129-137` | POMAlert | CONTRACT-engine | **cap unicitat**, cap `capa` | escriptors peten | 🟠 | 1,2 |
| `pom/models.py:612,618` | GarmentPOMMap | CONTRACT-engine | `(garment_type_item,pom,capa)` · CHECK | PETA | 🔴 | 1,2 |
| `pom/models.py:898,903` | ItemBaseMeasurement | CONTRACT-engine | `(base_set,pom,capa)` · CHECK | PETA | 🔴 | 1,2 |
| `pom/models.py:1119` | GradingRule | CONTRACT-engine | `(rule_set,pom)` sense capa | IGNORA-2a per disseny | 🟠 | 1,2 |
| `pom/models.py:1171` | ClientMesuraPerfil | CONTRACT-engine | `(codi_client,garment_type,pom,talla)` | COL·LAPSA (Welford barreja) | 🟠 | 1,2 |
| `pom/models.py:423` | CustomerPOMAlias | CONTRACT-engine | `(customer, client_code)` — **ja permet N codis → 1 POM** | **OK — la taula que millor sobreviu** | ⚪ | 1,2 |
| `pom/models.py:373` | POMEstadisticaTenant | CONTRACT-engine | `(pom,garment_type,talla_label)` | COL·LAPSA — **0 escriptors i 0 lectors: taula morta** | ⚪ | 1,3 |
| `pom/models.py:689-697` | ItemBaseSet | CONTRACT-engine | `(item,size_system,fit_type)` — **cap eix POM** | OK | ⚪ | 1 |
| `pom/models.py:225` | MeasurementLayer | CONTRACT-engine | `slug` UNIQUE · `SLUG_DEFECTE='exterior'` (`:223`) | **precedent exacte si la instància vol catàleg** | ⚪ | 1 |
| **`patterns/models.py:430-437`** | PatternPOM | CONTRACT-engine | `(pattern_piece, pom_master)` — **sense `capa`, sense instància**; el comentari **nega la premissa**: *«Dos ancoratges del mateix POM a la mateixa peça serien dues veritats sobre la mateixa mesura»* | **PETA** | 🔴 | 1 |
| `pom/models.py:257` | POMEstadisticaGlobal | CONTRACT-engine | `(pom_global,gtg,segment,talla_label)` | ⚪ regla d'or | ⚪ | 1 |

**Migracions** (10 de la cadena `capa`, cap `RunSQL`, cap `RunPython` de dades):
`pom/0052_measurementlayer.py:23` (el catàleg) · `models_app/0070_capa_mesures.py:33-57` (×5,
`CharField(20, db_index, default='exterior')`, **sense backfill**, fast-default PG11+) ·
`fitting/0017:28-34` (×2) · `pom/0053:27-33` (×2) · `models_app/0071_capa_unicitats.py:40-61`
(inclou **DROP + ADD del `UniqueConstraint` amb nom de `POMPlacement`** i l'`AlterModelOptions` d'ordering)
· `fitting/0018:21-26` · `pom/0054:28-33` · `models_app/0072_capa_comporta_c1.py:32-61` (5 CHECK,
docstring `:20`: **«C4 EL RETIRA PER MIGRACIÓ. És bastida, no arquitectura»**) · `fitting/0019:25-34` ·
`pom/0055:28-37`.

**Números de migració lliures** (verificats): `models_app` **0073** · `fitting` **0020** · `pom` **0056** ·
`patterns` **0015**. ⚠️ **`patterns` és l'única sense CAP migració de `capa`**: `PatternPOM` no té ni la
bastida de C1.

**⚠️ El parany del default** (memòria `ftt-c1-capa-mesures-comporta`): la migració fa
`ADD COLUMN … DEFAULT … NOT NULL` seguit de `DROP DEFAULT` (patró Django) → **el default és del MODEL, no
de Postgres**. Codi vell + esquema nou = `NotNullViolation`. `test_capa_comporta_c1.py:84`
(`test_exterior_entra_i_es_el_defecte`) és el pin d'això.

**Nodes de catàleg que hereten la clau** (dins per la regla d'or, ⚪–🔴 segons cas):
`models_app/views.py:1136,1145` (`ibms = {i.pom_id: i}`, 🔴) · `:1160-1230` · `:1118-1126` · `:1037-1060` ·
`:1637-1642` (`graded_by_pom`, **l'únic lector de `models_app/` sense filtre de `capa`**, 🔴) · `:1707` ·
`:2494-2497` · `:2634-2636` · `:2789-2793` (`linies = [{'id': f'{pom.id}:{s}'}]`, 🔴) · `:3657` ·
`:3660-3661` · `:3695-3699` · `:3756-3765` (`get_or_create(gti, pom_id)` **sense capa**, 🔴 PETA) ·
`:3774-3796` (idem `base_set`, 🔴 PETA) · `:3851-3852` · `:3977-3983` ·
`models_app/extraction_views.py:1029-1035` · `:1174-1188` · `:1488` · `:1667` · `:1734,1754` · `:1847` ·
`:2047-2053` · `:2176-2185` · `:2201,2245,2288,2432` · `:2311` · `:2364` · `:2688-2698` ·
`models_app/pom_placement_views.py:52-64,130-139` · `pom/views.py:445-511` (`upsert`, 🔴 PETA) ·
`pom/views.py:394-400` · `export_losan_package.py:252-258,260-265` ·
`load_losan_package.py:84-100,363,379-381` · `author_baby_pom_maps.py:146-215` ·
`load_map_inline.py:144-145` · `validate_los_maps.py:77-104` · `consolidate_pom_catalog.py:212-215` ·
**`bootstrap_tenant.py:154,162,163,331-357`** (§5.1).

### 3.2 · `top-up-lectors` — LA CLAU JA VA CRÉIXER, HA DE CRÉIXER UN COP MÉS (68 nodes)

**A · Els que ja porten `(pom, capa)` i han de créixer alhora** — el comentari de
`fitting/graded_spec_views.py:86-92` ja adverteix que **han d'anar tots junts**: *«si un s'ancorés i un
altre no, una fila podria acabar amb l'ordre d'una capa i el nom d'una altra»*.

| fitxer:línia | taula | tipus | clau avui | amb 2 inst. | risc | camins |
|---|---|---|---|---|---|---|
| `models_app/views.py:2999,3004,3010-3012,3022-3026` | MeasurementChangeLog · BaseMeasurement | READ-dict | `changes_by_ev[key][(pom_id,capa)]` · `snapshot.update` · `displayed` · `clau_bm` | **COL·LAPSA + el carry-forward arrossega el valor d'una instància per la fila de l'altra** | 🔴 | 1,2 |
| `fitting/serializers.py:263-268,272-276` | BaseMeasurement · PieceFittingLine | READ-dict | `ordre_map`/`nom_fitxa_map`/**`bm_id_map`** per `(pom_id,capa)`; `clau_bm=(line.pom_id,line.capa)` | **COL·LAPSA — el `bm_id` mal resolt escriu el bateig a l'altra instància** | 🔴 | 1,2 |
| `models_app/serializers_size_check.py:86-113` | BaseMeasurement · SizeCheckLine | READ-dict | `bm_map[(pom_id,capa)]` → tolerància + `codi_fitxa` + ordre | **COL·LAPSA — veredicte dins/fora amb la vara de l'altra** | 🔴 | 1,2 |
| `models_app/pom_placement_views.py:74-82` | BaseMeasurement | READ-dict | `bm_by_pom[(pom_id,capa)]`; comentari `:68-71`: *«no peta: **pinta**»* | **COL·LAPSA** | 🔴 | 1,2 |
| `pom/s8_views.py:184-207` | BaseMeasurement · PieceFittingLine | READ-dict | `tol_map[(pom_id,capa)]` | COL·LAPSA | 🟠 | 1,2 |
| `pom/s10_views.py:53-60,84-94` | BaseMeasurement · PieceFittingLine | READ-dict | `tol[(pom_id,capa)]` | COL·LAPSA | 🟠 | 1,2 |
| `pom/services.py:729-741` | ModelGradingOverride | READ-dict | `{(pom_id,size_label)}` + `capa=SLUG_DEFECTE`; el docstring `:714-729` **declara la FRONTERA C3 i que ha de créixer alhora que `_load_base_measurements`** | COL·LAPSA | 🔴 | 1,2 |

**B · Els que porten àncora explícita `capa=exterior`** (l'àncora tapa la capa, **no** la instància):
`fitting/graded_spec_views.py:94-107` (4 mapes) · `fitting/repas_views.py:259-266` (4 mapes) ·
`pom/s6_views.py:87-105` · `pom/s11_views.py:165-171` · `models_app/views.py:3977-3983` ·
`pom/services.py:737`.

**C · 🚨 ELS DOS FORATS D'ONADA 1** — peten amb la segona CAPA, sense esperar la instància:

| fitxer:línia | taula | tipus | clau avui | risc | camins |
|---|---|---|---|---|---|
| **`patterns/views.py:552-556`** | BaseMeasurement | READ-list | `filter(model_id=fp.model_id, is_active=True)` — **SENSE àncora `capa`**. `RECENS_DELTA_ONADA1:222-224` va declarar `patterns/*` fora d'abast | 🔴 | 1 |
| **`tenants/federation_service.py:593`** | BaseMeasurement | READ-list | `filter(model=model, is_active=True)` a `_llegeix_patrimoni` — **SENSE àncora `capa`**, i el dict exportat (`:595-602`) **no porta `capa`** | 🔴 | 1,2 |

**D · Els que ni tan sols van créixer a `(pom, capa)`** (l'Onada 1 no els va veure):

| fitxer:línia | taula | clau avui | risc |
|---|---|---|---|
| **`models_app/services_size_check.py:33-42`** | SizeCheckLine × BaseMeasurement | `values_list('pom_id')` + `exclude(pom_id__in=…)` — **`pom_id` pelat**; `_materialize_lines` és *completadora* (docstring `:22-30`) → **la 2a instància mai rep línia, i cada re-obertura ho torna a decidir** | 🔴 |
| **`fitting/repas_views.py:99-113`** | SizeCheckLine | `fora[(size_check_id, pom_id)]` amb **`.only('size_check_id','pom_id','decisio','nota')` — el `.only()` exclou `capa`: ni arriba de BD** | 🔴 |
| `fitting/repas_views.py:140-159` | MeasurementChangeLog | `celles[clau][c.pom_id]` — sense capa | 🔴 |
| `pom/grading_views.py:119-140` | BaseMeasurement | `cells[pom_id][base_size_label]` **sense àncora** — **C7 revertit** (`6b431865`) | 🔴 |
| `fitting/graded_spec_views.py:39-42,57-74` | GradedSpec | `order_by('pom_id','id')` sense capa; `rows_by_pom[pom.id]` | 🔴 |
| `fitting/serializers.py:246-249` | GradedSpec | `spec_map[(gv_id, pom_id, size_label)]` — sense capa | 🔴 |
| `pom/s6_views.py:163-193` | GradedSpec | `pom_dict[pid]['values'][size_label]` | 🔴 |
| `pom/services.py:394-419` | GradedSpec | `out[pom_id] = row` (preview del wizard) | 🔴 |
| `pom/nomenclatura.py:29-42` | CustomerPOMAlias | `out.setdefault(pom_id, …)` — **descarta els àlies extra** | 🟠 |

**E · Comptadors i gates que canvien de SIGNIFICAT** (compten files, no POMs):
`models_app/views.py:3230` (`model.base_measurements.…count()` — accés invers, [SOLO-1]) ·
`pom/wizard_views.py:252-257` (gate «≥3 POMs»: sisa-D + sisa-E + coll el passaria amb 2 mesures reals) ·
`models_app/services_size_check.py:90` (`existing.linies.count()`) ·
`models_app/serializers_size_check.py:37` · `fitting/serializers.py:32,112` (`gv.graded_specs.count()`) ·
`pom/views.py:361-364` (`Count('measurements')`) · `tasks/views_b.py:970` (`Count('pom_maps')`) +
`tasks/serializers_b.py:152-155,169` · `patterns/views.py:714` · `pom/s9_views.py:55-58` ·
`patterns/engine/grading_projection.py:184-200` (`pom_sense_spec`/`spec_sense_pom` sobre **conjunts**) ·
`fitting/staleness.py:112-117` (`dict.fromkeys` per `codi_client`).

**F · Lectors de llista sense capa que emeten dues files amb el mateix `pom_id`**:
`models_app/views.py:1620-1625,1678-1713` · `:2486-2508` · `:2957-2958` · `:3589-3591` ·
`pom/wizard_views.py:320-330` · `patterns/views.py:552-557`.

### 3.3 · `Onada2` — ESCRIPTORS (94 nodes)

> **FET ESTRUCTURAL:** **cap escriptor de tot el repo passa mai `capa` a un lookup ni a un `defaults`.**
> Els únics 6 hits de `capa=` fora de `models.py` són **filtres de LECTURA**. Tot escriptor viu del default
> del model, protegit només per les comportes. **L'eix INSTÀNCIA entrarà pel mateix forat exacte.**

**A · 🚨 El node que arma l'accident de C4, i els seus set germans**

| fitxer:línia | taula | clau del lookup | unicitat real | risc |
|---|---|---|---|---|
| **`pom/services.py:1033-1043` `_upsert_graded_spec`** | GradedSpec | `(grading_version_id, pom_id, size_label)` | `(grading_version,pom,size_label,**capa**)` | 🔴🔴 |
| `models_app/pom_placement_views.py:135-138` | POMPlacement | `(item_fitxer, pom_id, view_slot)` | `(item_fitxer,pom,view_slot,**capa**)` | 🔴 |
| `models_app/views.py:3756-3765` | GarmentPOMMap | `(garment_type_item, pom_id)` | `(gti,pom,**capa**)` | 🔴 |
| `models_app/views.py:3774-3796` | ItemBaseMeasurement | `(base_set, pom_id)` | `(base_set,pom,**capa**)` | 🔴 |
| `pom/views.py:445-511` (`upsert`) | ItemBaseMeasurement | `(base_set, pom_id)` | idem | 🔴 |
| `bootstrap_tenant.py:162` | GarmentPOMMap | clau natural `('garment_type_item','pom')` | idem | 🔴 |
| `load_losan_package.py:363` · `:379-381` | GarmentPOMMap · ItemBaseMeasurement | `{gti, pom}` · `{base_set, pom}` | idem | 🔴 |
| `models_app/services_size_check.py:45-50` | SizeCheckLine | `create(size_check, pom=bm.pom, …)` **sense capa** | `(size_check,pom,**capa**)` | 🔴 |
| `fitting/services.py:329-338` | PieceFittingLine | clona `GradedSpec`→línia copiant **només** `pom`,`size_label`,`valor` — **ni `capa`** | `(pf,pom,size_label,**capa**)` | 🔴 |

**B · Escriptors de `BaseMeasurement`** (18):
`models_app/views.py:1793-1806` (`set-measurements`, 🔴) · `:1812-1818` i `:1941-1947`
(**`exclude(pom_id__in=keep).update(is_active=False)`** — la identitat de la baixa és `pom_id`: **totes
dues viuen o totes dues moren**, 🔴) · `:1921-1936` (`gravar_pom`, `.first()`, 🔴) · `:1182-1217`
(sembra item→model, `.first()`+`create`, 🔴) · `:1417-1451` (còpia model→model, 🔴) · `:2299`
(`xat-mesures`) · `:2313-2325` (acció `AFEGIR` de la IA, 🔴) · `:2318` (`'ordre': …count()`) ·
`:2797-2805` `_write_base` (porta d'escriptura de l'Escalat, 🔴) · `:3927-3938` (poda per POM: **poda la
primera i deixa l'altra viva i invisible**, 🔴) · `models_app/extraction_views.py:2515-2524` ·
**`:2560`** (el confirm de l'import — **és exactament el bug declarat a `models.py:654-659`**, 🔴🔴) ·
`:2331-2336` (poda d'orfes per `exclude(pom_id__in=confirmed)`, 🔴) · `:2367-2372` ·
`models_app/tech_sheet_views.py:364-377` (🔴) · `pom/wizard_views.py:192-195` (buida **les dues**, 🔴) ·
`:205-215` (🔴) · `models_app/services_size_check.py:204-217` (🔴) ·
`fitting/services.py:362-380` `consolidate_base_from_fitting` (**`line.capa` es perd**, 🔴) ·
`tenants/federation_service.py:689-719` (🔴) · `repair_fitting_20260710.py:78`.

**C · Escriptors de `ModelGradingOverride`** (6):
`models_app/views.py:2587-2610` (l'ÚNIC camí d'override des de Peça 4, 🔴) · **`:2751`**
(`filter(model,pom).delete()` — **esborra els pins de totes dues instàncies**, 🔴) · `:2759-2772` (🔴) ·
`:2426` (llenç net, ⚪) · `extraction_views.py:2693-2698` (🔴) · `:2909-2910`.

**D · 🚨 Signals — tot el `MeasurementChangeLog` neix cec**

| fitxer:línia | què fa | risc |
|---|---|---|
| `models_app/signals.py:299-310` (F1) | `create(model=…, pom=…, base_measurement=…)` — **NO estampa `capa`** ni instància | 🔴 |
| `models_app/signals.py:267-279` (poda) | idem, branca `_desactivat` | 🔴 |
| `models_app/signals.py:218-234` | `capture_old_measurement_value` per **PK** | ⚪ OK |

Cens complet: **12 `@receiver` en 4 fitxers**; només aquests dos toquen la cadena.
**Escriptures que bypassen signals** (i per tant qualsevol guard que s'hi posi):
`bulk_import_service.py:544` (documentat), els `bulk_create` de `reseed_tenant_fhort.py:264,303,390` i
`replace_pom_catalog.py:805`, i tots els `.update()` de queryset.

**E · Fitting / propagació**:
`fitting/views.py:617-619` (`_resp` torna **totes** les línies del POM, 🔴) · **`:665-668`**
(`filter(pf, pom=line.pom, size_label).update(valor_real=…)` **sense capa** — **propagar una instància
reescriu l'altra**, 🔴) · `fitting/services.py:501-506` (⚪) · `pom/services.py:549-554`
`update_client_profile` (Welford acumula les dues instàncies al mateix perfil, 🔴) ·
`pom/s10_views.py:136-152` (`update_or_create(model,pom,size_fitting)` **sense `size_label` ni `capa`** —
col·lapse doble ja avui, 🔴) · `pom/s11_views.py:166-206` (🔴).

**F · Federació** (canal de FEINA; el canal d'ENCÀRREC és net i ho diu al codi, `:142-144`):
`federation_service.py:542-552` (`_clau_natural_pom` = **2-tupla de codis de catàleg**, 🔴) ·
`:568-581` (cau memoritzada per clau) · `:593-605` (**dues files amb la MATEIXA clau al paquet**) ·
`:607-620` · `:689` · `:711-722` (**la 2a va a `saltat['mesures']` → l'informe surt en verd**) ·
`:732-742` · `:785-800` (el text de l'informe **menteix**: «No s'ha trepitjat res del que ja teníeu») ·
`tenants/views_encarrecs.py:158` (única boca HTTP).
**Excloent que PROTEGEIX**: `:528-531` — **`GradedSpec` no viatja mai, es recalcula**.

**G · Motor**: `pom/services.py:771-780` (`_load_base_measurements` → `{pom_id: valor}`, **zona
intocable**, 🔴🔴) · `:215-217` · `:233-270` (el bucle generador) · `:361-380` (el mateix al preview) ·
`:699-712` (`_load_grading_rules`) · `:744-765` (`_poms_amb_override`).

### 3.4 · `C4-ins` — CONTRACTES I UI (203 nodes)

**A · Els 11 payloads on `pom_id` és la clau d'un DICCIONARI exposat al client**

| # | node | endpoint | forma |
|---|---|---|---|
| 1 | `pom/grading_views.py:156` | `GET /size-fittings/{sf_id}/taula-mesures/` | **`cells: {str(pom_id): {talla: {value,type,increment}}}`** |
| 2 | `models_app/views.py:1736-1738` | `GET /models/{id}/taula-mesures/` | **`deltes: {str(pom_id): float\|null}`** |
| 3 | `fitting/graded_spec_views.py:120` | `GET /fitting/{sf_id}/graded-table/` | `rows` ← `rows_by_pom[pom.id]` |
| 4 | `pom/s6_views.py:193` | `GET /size-fittings/{sf_id}/graded-specs-units/` | `results` ← `pom_dict[pid]` |
| 5 | `fitting/repas_views.py:333` | `GET /fitting/model/{id}/repas/` | `rows` ← `files[pom_id]` |
| 6 | `models_app/pom_placement_views.py:60-92` | `GET /item-fitxers/{item_id}/pom-placements/` | `placements` ← `merged[pom_id]` |
| 7 | `models_app/views.py:3016-3045` | `GET /models/{id}/base-stages/` | `rows` ← clau `(pom_id, capa)` |
| 8 | `models_app/extraction_views.py:2176-2182` | `POST /import-sessions/{token}/confirmar/` | `valors[pom_id][talla]` |
| 9 | `pom/wizard_views.py:339-367` | `GET /models/{id}/base-measurements/` | `regla_model` ← `regla_by_pom[pom_id]` |
| 10 | `patterns/views.py:144` | `GET /patterns/pattern-files/{id}/model-poms/` | `{pom_id: {client_code,…}}` |
| 11 | `models_app/tech_sheet_views.py:322` | `POST /models/create-from-sheet/` | body `pom_mappings: {client_code: pom_code}` |

> **El pitjor és el 6**: `merged` col·lapsa i el `bm_id` que en surt s'usa per **desar el bateig** i per
> lligar la cota del croquis. No peta: **pinta**, i lliga el dibuix a la mesura equivocada.
> **El de radi més ampli és 1+3+4**: tres endpoints serveixen **la mateixa matriu POM×talla amb tres
> formes de dict diferents**. Amb dues instàncies, els tres menteixen alhora i de maneres distintes.

**B · Contractes on `pom_id` va al PATH o a una llista plana** (no hi ha on posar la instància):
`POST /models/{model_id}/pom/{pom_id}/desactivar/` (`views.py:3911`) ·
`POST /models/{model_id}/pom/{pom_id}/regim/` (`:3993`) ·
`PATCH /grading-rule-sets/{id}/regles/{pom_codi}/{,editar/}` (`pom/s2_views.py:282-288`,
`s4_views.py:59-64` — **`.first()` SENSE `order_by`: el PATCH edita una a l'atzar i retorna 200**) ·
`POST /models/{id}/materialitzar-poms/` body `pom_ids[]` (`views.py:1109-1126`) ·
`POST /models/{dst}/copiar-de/{src}/` body `pom_ids[]` (`:1329-1355`) ·
`POST /models/{id}/set-measurements/` **`keep_pom_ids`** (`:1774,1812`) i `gravar-pom` (`:1847,1941`) ·
`POST /models/{id}/check-tolerances/` body `measurements[].{pom_id,value_cm}` (`s11_views.py:146-149`) ·
`POST /models/{id}/escalat/ajustar-talla/` body `{pom_id,talla,valor}` + `linies[].id="{pom_id}:{talla}"`
(`:2792`) · `PATCH /import-sessions/{token}/mesures/` body `{pom_master_id,talla_label,valor}` ·
`POST /models/{id}/proposar-cotes/` body `poms[].{pom_id,…}` (`pom_vision_views.py:25-45`).

**C · Els 5 serializers sense cap camp d'eix** — la instància **no té on aterrar**:
`models_app/serializers.py:389-412` (`BaseMeasurementSerializer`; `model,pom,base_value_cm,is_active,notes,nom_fitxa,origen` escrivibles) ·
`models_app/serializers_size_check.py:14-20` · `fitting/serializers.py:207-213` ·
`pom/serializers.py:390-406` (`GarmentPOMMap`) · `:459-470` (`ItemBaseMeasurement`).
**Cap dels 19 serializers de la cadena exposa `capa` avui.**

**D · Frontend — `TechSheetEditor.jsx` (7 838 línies, 79 nodes; el brief en llistava 11)**
Bloc de cotes `:276-450` · taules T0/T1a/T1b/T3 `:4813-5073` (inclòs `rulesByPom:4898-4902`) ·
estat `:2601,2613` · càrrega `:3350-3375` · **efecte F1 `:3454-3481`** (`bmById:3456` **OK**,
`bmByPom:3457` 🔴, fallback `:3462`) · eina `cota_pom` `:4110-4148` · **bloc de propostes/IA `:5424-5710`
(26 nodes)** · panell de POMs `:6605-6810` (12) · panell de propietats `:7285-7325`.

**E · Frontend — la resta** (79 nodes):
`MeasureGrid.jsx:477` **`key={r.pom_id}`** · `:324,524,547` (`podaArmada`) ·
`CheckMeasureEditor.jsx:217-220` (`lineByPom`) · `:143` (`setPomRule`) · **`:388-389`
(`desactivarPom` — soft-delete que en desactiva dues)** · `measureSources.jsx:18-28` ·
**`fittingGridAdapter.jsx:144`** (`lineId` sintètic) · `PropagatedEditor.jsx:52-72,139` ·
`FittingDetail.jsx:122-132,355,578-591,614-619` · `SessionPanel.jsx:19-29,133` ·
`repasGridAdapter.jsx:118-123` · **`EditableTable.jsx:163-172`** (`measurements` + **`keep_pom_ids`**) ·
`MeasuresEntryPanel.jsx:61,86-89,123-139,342` · `ImportWizard.jsx:286,537,554-556,626-652,666,684-714,782,813,1158-1163,1314,1331-1333,1629-1649` ·
`SizeMapSetup.jsx:342-346,356-364,427-439,732-795,906` · `MeasurementBaseGrid.jsx:66-72,138,164-178` ·
`POMBrowser.jsx:26-70,133,152-160,326` · `SizeSetDetail.jsx:41-55,221-266` · `GradingRuleSets.jsx:483-511` ·
`TallerPatro.jsx:332,352-369,820` · `ModelPomList.jsx:83,111-112` · `ExportModal.jsx:250-349` ·
`PropostaPromocio.jsx:25-71` · `PromoteToItemButton.jsx:35` · `ModelTimeline.jsx:82` ·
`api/endpoints.js:96-108,123-124,164,264-265,593-604,813-819` ·
`utils/nomenclaturaPom.js:28-37,55-60`.

**F · i18n — textos que afirmen la llei actual** (els tres idiomes, mateixa línia):

| clau | ca/en/es | text (ca) | consumidor |
|---|---|---|---|
| `import_wizard.many_to_one_hint` | `:3609` | «…**cap no s'ha vinculat (la segona n'esborraria la primera)**» | `ImportWizard.jsx:1159` |
| `size_map_many_to_one` | `:2371` | «…**cap vinculada automàticament** — confirma-la manualment» | `SizeMapSetup.jsx:784` |
| `size_map_dup_warn` | `:2344` | «…**resol els duplicats abans de crear**» | `SizeMapSetup.jsx:426,732` |
| `pattern.err_pom_duplicate` | `:3975` | «Aquest POM ja està ancorat a aquesta peça: **una mesura, una veritat**» | `TallerPatro.jsx:368` |
| `tech_sheet.pom_cota_ja_colocat` | `:2849` | «Ja col·locat — elimina la cota per re-acotar» | `TechSheetEditor.jsx:6737` |
| `poms.already_assigned_short` | `:3238` | «ja assignat» | `POMBrowser.jsx:326` |
| `import_wizard.codi_duplicat_*` · `resol_err_codi_duplicat` | `:3528-3529`, `:3638` | ⚠️ parlen de **codis de catàleg duplicats**, concepte veí però diferent — dins per la regla d'or | `ImportWizard:571-580` |

### 3.5 · `F2-patrons` — MOTOR DE PATRONS (32 nodes)

**Mitigant de dades: `patterns_patternpom` = 0 files als tres schemas.** Tot `patterns/` és
pre-producció: el cost és de codi i de **format**, mai de migració de dades.

| fitxer:línia | tipus | clau avui | risc |
|---|---|---|---|
| `patterns/engine/ports.py:60` | CONTRACT-engine | `GradedPOMDelta.pom_id: int` — dataclass frozen | 🔴 |
| `patterns/engine/ports.py:97-108` | CONTRACT-engine | `delta(pom_id, size_label)` per cerca lineal; **el docstring `:104-108` invoca un unique `(grading_version,pom,size_label)` que ja és fals des de C1** | 🔴 |
| `patterns/adapters.py:484-489` | READ-list | `order_by('pom_id','size_label')` sense capa | 🔴 |
| `patterns/adapters.py:587,623` | READ-list | `piece.poms` → `POMSpec(pom_code=…)`; `pom_id=pom.pom_master_id` | 🔴 |
| `grading_projection.py:179-201` | READ-dict | `poms_per_id` · `ids_amb_spec` · `codis_spec` · cobertura sobre **conjunts** | 🔴 |
| `grading_projection.py:216,262` | CONTRACT-engine | `graduables` · `_deltes_dels_poms` | 🔴 |
| `grading_projection.py:499,509,511-514,563-570` | READ-dict | `{p.pom_code: …}` — **per codi STRING**; les dues bandes de la comptabilitat col·lapsen alhora | 🔴 |
| **`patterns/engine/ftt_pom_layer.py:110-127`** | CONTRACT-engine | `FTT "{codi}" {nom} = {valor} mm` — **el DXF només porta el codi**. Roundtrip export→reimport **perd la instància**. És **el sostre dur: disseny de format, no refactor** | 🔴 |
| `ftt_pom_layer.py:197-218` · `aama_writer.py:128-129` · `export.py:395-412` | READ/WRITE | `pom_code` com a identitat | 🔴/🟠 |
| `patterns/engine/roundtrip.py:274-292` | COUNT-gate | `codis_a`/`codis_b` sets de `pom_code`; **el comparador de la prova Montse no veu una instància perduda** | 🔴 |
| `patterns/annotation_views.py:521-557` | CONTRACT-api · WRITE | payload `{pattern_piece, pom_master, definicio_mesura}` | 🔴 |
| `patterns/tests.py:1865` | COUNT-gate | `test_el_mateix_pom_dos_cops_a_la_mateixa_peca_rebota` → assert 400 — **inverteix la llei** | 🔴 |
| `patterns/views.py:199-215` · `serializers.py:304-315` · `svg.py:119-126` · `operations.py:187-190` | READ/CONTRACT | llistes per `pom_code` | 🟠/⚪ |
| `sembra_ai_report.py:30,463,500,602` | READ-list | informe FASE 1 read-only; **la Fase 2 escriurà `POMPlacement`** | ⚪ |

**⚠️ VEREDICTE: `patterns/` NO pot entrar sencer a `F2-patrons`.** Dos nodes han d'entrar abans (§3.2-C
i §5.3): `patterns/views.py:552-556` (`top-up-lectors`) i `:544-549` (**bug viu**, §8.1).

### 3.6 · `consolidació-catàleg` (58 nodes)

**El registre canònic del radi invers** — `pom/seed_data/consolidate_pom_los.py:30-34`, **l'ÚNIC lloc del
repo on el radi invers sencer de `POMMaster` està enumerat**, com a strings consumits per `getattr()`:

```python
FUSIO_MOVE_RELS  = ['base_measurements', 'model_grading_rules', 'measurement_changes',
                    'model_grading_overrides', 'item_base_measurements', 'mesures_perfil',
                    'alerts', 'pattern_poms', 'estadistiques']
FUSIO_DELETE_RELS = ['graded_specs']
FUSIO_LEAVE_RELS  = ['regles_grading']
```

Consumidors: `consolidate_pom_catalog.py:112-119` (`getattr(prim, rel).all()` + `.update(pom=dest)` amb
`except IntegrityError → col·lisió` **comptada i deixada al prim**) i `:243-254` `_fixcoll`
(`getattr(m, rel).all().delete()`). **Qualsevol eix nou ha de passar per aquesta llista o la consolidació
el deixa enrere en silenci.** 🔴 [SOLO-CAMÍ-1]

**Altres**: `consolidate_pom_catalog.py:109,121-128,212-216` · `author_baby_pom_maps.py:146,203-213` ·
`load_losan_package.py:84-100,118-125,363,379,390-395,446` · `export_losan_package.py:146-153,252-265,330` ·
**`export_losan_package.py:383-387`** (recomptes **hardcodats** `garment_pom_maps: 1748`,
`item_base_measurements: 37` → **sonda barata del radi real: peten en néixer la 2a instància**) ·
`load_map_inline.py:141-145` · `validate_los_maps.py:77-104` · `replace_pom_catalog.py:753,805` ·
`reconcile_tenant_poms.py:65-78` · `repair_customer_aliases.py:115,146,185` ·
`seed_master_delta_catalog.py:27` (comentari literal: **«hi ha DOS POMMaster amb codi_client 'U1'»**),
`:64-91` · `seed_baby_poms.py:253-262` · `extend_pom_catalog.py:177,195` ·
`pom/dictionary_service.py:132-135` · `dictionary_views.py:96-172` ·
`pom/services.py:601-645` (`maybe_learn_customer_alias`) · `pom/nomenclatura.py:29-42` ·
`pom/s4_views.py:292-302` · `pom/grading_utils.py:87-100,777-795` ·
`models_app/views.py:3589-3596,3657-3699` · `extraction_views.py:2909-2910` ·
`tasks/views_b.py:970` + `serializers_b.py:152-169` · `pom/s9_views.py:55-58,79-213` ·
**`bootstrap_tenant.py:154`** (`POMMaster` per `codi_client` — **12 col·lisions reals a staging**).

### 3.7 · `FORA: <motiu>` — el que NO entra, amb el motiu (67 nodes)

| motiu | nodes |
|---|---|
| **identifica per PK de fila** | `signals.py:218-234` · `views.py:2036,2299,2328,2863,2909` · `clone_model_for_qa.py:92-102` · `annotation_views.py:134-151,554-557` · `MeasureGrid.jsx:327-336` · `CheckMeasureEditor.jsx:244-259` · `ModelPomList.jsx:39-43` · `POMBrowser.jsx:370,390` · `GradingRuleSets.jsx:475` · `sizeCheckLines.update(lineId)` · `pieceFittingLines.update(lineId)` |
| **comptador o predicat booleà** | `views.py:586,1340,1362,1555,1910,1997,2375,2451,2826,3589` · `services_size_check.py:113-119,172` · `pom/services.py:482,501,676-681` · `pom/views.py:394-400` · `s9_views.py:55-58` · `patterns/views.py:714` |
| **acte de model sencer / purga** | `views.py:2426` (llenç net d'overrides) · `extraction_views.py:50-120` (delete del model) · `clone_model_for_qa.py:154-163` |
| **la regla no té instància** (decisió 3c.1, a re-confirmar) | `views.py:1957-1991,3993-4091` · `s2_views.py:221-231,282-288` · `s4_views.py:292-300` · `federation_service.py:732-742` |
| **taula fora de la cadena** | els 5 `cursor.execute` de producció (`signals.py:57-72`, `views.py:550-557,811-821`) — toquen `models_app_model`/`_garmentset` |
| **codi mort o inabastable** | `reseed_tenant_fhort.py` sencer (guard obsolet a `:80-88` que avorta sempre) · `HTMTooltip.jsx` (cap consumidor) · `pom_pomestadisticatenant` (0 escriptors, 0 lectors) |
| **homònim** | `planning/scheduler_service.py:145-253` (`placements` = tasques al calendari) · `commerce`/`backoffice` `.lines` · `punts_per_capa` de l'OpenAPI (capes de dibuix DXF) · `GradeTable.regles` de `patterns/` (dict del format RUL) · `.poms` com a llista de dicts extrets d'un document (~35 hits) |
| **exclusió declarada que PROTEGEIX** | `federation_service.py:528-531` — `GradedSpec` no viatja mai, es recalcula |
| **la instància és dins d'UNA peça** | `models_app/test_set1_creacio.py:93,118` (la sortida multi-peça per Models germans) |

---

## 4 · COBERTURA — ELS LÍMITS DE LA DIAGNOSI PRÈVIA, TANCATS

`DIAGNOSI_INSTANCIES_POM.md:851-858` declarava quatre límits. Aquí queden coberts, secció per secció.

### 4.1 · «No auditat: el frontend del backoffice» → **COBERT · NO TOCA (amb prova)**

`frontend-backoffice/src/` sencer: **28 fitxers, 3 954 línies.**
Prova: `grep -rniE '\bpom'` → **0** · `mesur|measur` → **0** · `grading|gradua` → **1** (literal d'UI a
`SeedProfilesPage.jsx:193`) · `fetch(|XMLHttpRequest|EventSource|WebSocket` → **0** fora de `api/`.
**Verificació independent meva: `grep -rnE "pom_id|pomId|pom_master_id|bm_id" frontend-backoffice/src` → 0.**

**Inventari complet dels 27 endpoints que crida** (tots `/api/backoffice/v1/`, tots servits per
`backoffice/urls.py`): `api/auth.js:7,10` · `api/tenants.js:8-34` · `api/contracts.js:5-16` ·
`api/invoices.js:5-41` · `api/legal.js:5-15` · `api/seeding.js:5-12`.
**L'únic que arriba a la cadena és `perfils-sembra/blocs-meta/`**, i **només com a comptador de files**
(`backoffice/views_seeding.py:49-51` → `seed_block_counts`).

**⚠️ PERÒ el backoffice és una BOCA D'ESCRIPTURA per delegació** (§8.2):
`SeedProfilesPage.jsx:155` → `views_tenants.py:34-49,103` → subprocés detached →
`provision_free_tenant.py:69` → `bootstrap_tenant`. Escriu `POMMaster`, `GarmentPOMMap` i `GradingRule`
**fora de la petició HTTP, amb stdout a `DEVNULL`**.

`backend/fhort/backoffice/` sencer (32 `.py`): **0 hits** de les 18 taules. Facturació neta —
`reconcile_consumption.py` compta `Model`/`GarmentSet`/`TaskTransition`; `generate_invoices.py:14`
només delega.

### 4.2 · «No auditat: `patterns/` complet» → **COBERT · 32 nodes + 1 forat d'Onada 1 + 1 bug viu**

Recorregut: `models.py`, `views.py`, `annotation_views.py`, `serializers.py`, `adapters.py`, `export.py`,
`svg.py`, `engine/ports.py`, `engine/grading_projection.py`, `engine/ftt_pom_layer.py`,
`engine/aama_writer.py`, `engine/roundtrip.py`, `engine/operations.py`, `tests.py`. Veredicte a §3.5.

### 4.3 · «Pot faltar-hi algun node, sobretot a `management/commands/`» → **COBERT · 71/71**

**34 toquen la cadena** (registrats a §3.6 i §3.3). **7 són `__init__.py` buits.**
**30 no la toquen**, citats un per un: `create_backoffice_admin` · `generate_invoices` ·
`provision_free_tenant`¹ · `reconcile_consumption` · `seed_free_plan` · `sync_stripe_catalog` ·
`reconcile_work_orders` · `audit_fitxers` · `flag_incomplete_models` · `move_media_tenant` ·
`restaura_size_run` · `seed_losan_models` · `materialize_segments` · `crea_sizing_profiles` ·
`rename_targets_p0b` · `reseed_size_definitions` · `restructure_garment_types_v2` ·
`seed_baby_months_profiles` · `seed_commercial_size_runs` · `seed_kids_baby_target_map` ·
`seed_pattern_piece_roles` · `seed_scope_nodes_proposals` · `backfill_ruleset_scope` ·
`translate_garment_families` · `create_tenant_admin` · `pausa_tasques_oblidades` ·
`recompute_welford` · `retype_scaling_to_grading` · `assign_models_to_studio` ·
`instantiate_external_models` · `seed_tenant_link`.
¹ `provision_free_tenant` no toca la cadena **directament** però és el disparador de `bootstrap_tenant`.

**SQL cru: NO és un vector.** `.raw(` → **0** a tot el backend (verificat). `RunSQL` → **0** a totes les
migracions (verificat). Els 5 `cursor.execute` de producció toquen `models_app_model`/`_garmentset`.
Els únics punts que nomenen taules físiques de la cadena són **dos fitxers de test** i **dos `.sql` de
`scripts_tmp/`**.

### 4.4 · Límit NOU trobat en cobrir els altres — **el green flag d'OpenAPI és cec**

Verificació meva: `curl -s http://127.0.0.1:8001/api/schema/ -H "Host: staging.fhorttextile.tech"` →
**200, 743 057 bytes, 364 paths.**

| | n |
|---|---|
| paths totals | 364 |
| paths de la cadena | **80** |
| … amb **`'200': description: No response body`** | **54 (68%)** |
| … amb `$ref`/`properties` (forma declarada) | 26 |

Entre els cecs: `base-stages/` · `graded-table/` · `repas/` · `pom-placements/` · `taula-mesures/` ·
`base-measurements/{,reorder,units}` · `base-measurements/{bm_id}/noms/` ·
`import-sessions/{token}/{talles,extraccio,poms,grading-preview,mesures,library-prefill,confirmar}` ·
`grading-rule-sets/{id}/regles/{,pom_codi,pom_codi/editar,historial,export/csv}` ·
`item-base-{sets,measurements}/{id}/` · `garment-pom-maps/{id}/`.

**Conseqüència operativa:** el green flag «**OpenAPI 0 diffs fins C4**»
(`PLA_EXECUCIO_TRAM_C.md:90`) **no pot detectar un canvi de forma de payload** als 54 endpoints on el
canvi seria més probable. Ha estat verd per construcció, no per absència de canvi.
El que sí que ho vigila: el **fumeig md5 contra T0'** i **`onada1_dump_superficies.py`** (§10).

**Verificat també:** el contracte **no exposa `capa` enlloc**. Les 28 aparicions de la cadena `capa` a
l'esquema són `capability`/`capacitat`, més un **`punts_per_capa`** que és de `patterns` (capes de dibuix
del DXF, veí d'`unknown_layers` i `bounding_box_mm`) — **homònim**.

### 4.5 · Cobertura dels 12 `urls.py`

Recorreguts **sencers**. Rutes de la cadena vs. totals:

| fitxer | rutes | toquen la cadena |
|---|---|---|
| `fhort/urls.py` (arrel tenant) | 9 + 9 includes | `api/schema/` (meta) |
| `urls_public.py` | 12 | **cap** — cap taula de la cadena viu a `public` |
| `accounts/urls.py` | 9 | **cap** |
| `tenants/urls.py` | 2 routers | `encarrecs/{,enviar,traspassar}` |
| `patterns/urls.py` | 7 routers + accions | `pattern-poms/*`, `model-poms/`, `grading-versions/`, `export*` (5) — **25 no** |
| `planning/urls.py` | 13 | **cap** |
| `commerce/urls.py` | 15 routers ≈ 40 | **cap** |
| `backoffice/urls.py` | 13 | **cap** |
| `fitting/urls.py` | 7 + routers | 10 sí — 17 no |
| `pom/urls.py` | 14 + routers | la majoria sí — 10 no (catàleg de talles/tipus) |
| `models_app/urls.py` | 65 | ~40 sí — ~45 no |
| **`tasks/urls.py`** | 8 `re_path` + routers | ⚠️ **munta 13 vistes de `pom/`** (`s2`, `s4`, `s6`, `s11`, `grading_views`, `sizing-profiles`, `alerts`) — **el punt cec d'un cens per app**; ~40 rutes pròpies no |

---

## 5 · TRES COSES QUE EL PLA DE TRAM C NO TÉ CENSADES

### 5.1 · Deute de C1 VIU amb data de caducitat pròpia

`bootstrap_tenant.py:162` declara la clau natural de `GarmentPOMMap` com `('garment_type_item','pom')`.
La BD la té com `('garment_type_item','pom','capa')` (`pom/models.py:612`, verificat).
El mecanisme (`:331-357`) construeix el `lookup` **només** amb `key_fields`; **`capa` cau a `defaults`** i
`update_or_create` (`:351`) **sobreescriu i ho compta com a `updated`**.

Avui la comporta `pom_garmentpommap_capa_gate_c1` ho tapa. El comentari de `pom/models.py:615-618` diu
**«C4 la retira per migració»**. **El dia que C4 la retiri, el copiador comença a perdre files en silenci
sense que cap instància hi hagi entrat.** No és `C1-ins`: és `top-up-lectors`, i té data pròpia.

Germans amb el mateix patró: `:154` (`POMMaster` per `codi_client` — **12 col·lisions reals**) i
`:163` (`GradingRule` per `('rule_set','pom')`).
**`:356` `maps[model][src_pk] = dst_pk`**: el mapa de remapeig d'FK queda corromput per a **tota peça
posterior** — col·lapse de 2n ordre.

### 5.2 · L'accident de C4 ja està armat al motor

`pom/services.py:1033-1043` — verificat literalment. **La comporta és l'única cosa que separa
`_upsert_graded_spec` d'un `MultipleObjectsReturned`.** No cal cap instància: n'hi ha prou amb una fila de
folre. I té set germans exactes (§3.3-A) que fan el mateix amb `POMPlacement`, `GarmentPOMMap`,
`ItemBaseMeasurement`, `SizeCheckLine` i `PieceFittingLine`.

### 5.3 · `tasks/urls.py` munta 13 vistes de `pom/`

Un cens per app no les veu, perquè viuen a `pom/` i es serveixen des de `tasks/`. Dues són **escriptors
amb `.first()` sense `order_by`**: `pom/s2_views.py:282-288` i `pom/s4_views.py:59-64` — resolen la regla
per **codi string** amb `Q(pom__pom_global__codi) | Q(pom__codi_client)` i **el PATCH edita una a l'atzar
retornant 200**. És el mateix patró que el 🚩 `measurements_table_view` de C7, però en un **escriptor**.

---

## 6 · CONTRAST AMB ELS CENSOS PREVIS

### 6.1 · `DIAGNOSI_INSTANCIES_POM.md` — **167 referències `fitxer:línia` en ~40 fitxers**

**Totes apareixen al registre.** Cap ha desaparegut ni ha canviat de línia (mateix HEAD).
Verificació: extracció mecànica dels 167 refs i creuament contra el registre → **167/167 presents**.
El registre hi afegeix **320 nodes nous**.

### 6.2 · `RECENS_DELTA_ONADA1_2026-07-31.md` — **25 nodes**

| grup | estat al registre |
|---|---|
| Nodes 1-11 (backend d'Onada 1) | **tots 11 presents** a `top-up-lectors` §3.2-A/B |
| Nodes 12a-16 (frontend) | **tots 5 presents** a `C4-ins` §3.4-D/E — el RECENS els va moure a C4 per esmena; el registre ho manté |
| N1-N4 (lectors nous) | **tots 4 presents**: N1 `graded_spec_views.py:94-107` · N2 `repas_views.py:259-266` · N3 `services_size_check.py:33-42` · N4 `views.py:3977-3983` |
| X1 (`base_stages_view`, no censat preexistent) | **present** a §3.2-A |
| **5 exclosos** (`_load_base_measurements`, `_load_grading_rules`, `patterns/views:544`, `grading_projection:179`, `adapters:585-624`) | **tots 5 presents** — i **`patterns/views.py:552-556` s'hi afegeix com a forat NOU** que el RECENS no podia veure perquè va declarar `patterns/*` fora d'abast (`:222-224`) |

⚠️ **Deriva de línia:** el RECENS és de HEAD `3efe7f4b`; aquest registre és de `72d2e579`.
Exemple: `_load_base_measurements` 747 → **771**. Les línies de `patterns/` no s'han mogut (544 → 544,
179 → 179), ni les de `pom/s10_views.py` (43 → 43).

### 6.3 · Reports d'Onada 1/1b — els 9 commits vius

Els **11 fitxers tocats** (§1.3) són la base de `top-up-lectors`. **`pom/grading_views.py` no hi és:
C7 revertit** (`6b431865`) — per això `:119-140` apareix a §3.2-D («ni tan sols va créixer»).
El 🚩 de l'ordre no determinista de `measurements_table_view` segueix viu i no depèn de la instància.

### 6.4 · Tests que codifiquen la llei — el pin del tram

| fitxer:línia | què afirma | amb 2 inst. |
|---|---|---|
| **`models_app/test_seccio_captura.py:156,172`** | `assertEqual(files.count(), 1, 'la clau encara col·lapsa: si això falla, la clau ha canviat')`. Docstring: *«Aquest test hi és perquè el dia que algú toqui la clau, ho vegi caure aquí i sàpiga que era conegut»* | **HA DE PETAR** |
| `models_app/tests.py:52,84,189` | el matcher bloqueja dues files → un POM; docstring: *«per legítim que sigui l'àlies, dues files no hi caben i la segona esborra la primera»* | **PETA — inverteix la llei** |
| `pom/tests.py:74,92` | 2n codi → mateix POM ⇒ `pendent_revisio` | PETA |
| `patterns/tests.py:1865` | `test_el_mateix_pom_dos_cops_a_la_mateixa_peca_rebota` → 400 | **PETA — inverteix la llei** |
| `models_app/test_capa_comporta_c1.py:30-38,94-105` | **llista literal de 9 noms** de comporta | PETA si la instància n'afegeix |
| `models_app/test_capa_comporta_c1.py:108-116` | SQL contra `information_schema`: `ModelGradingRule` **NO té `capa`** | PETA si la instància hi entra |
| `models_app/test_capa_comporta_c1.py:84` | `capa` default sense passar-la | 🚩 el parany del default de Postgres |
| `models_app/test_size_check_completa_linies.py:49,60,73,95,102,116,124` | **«un POM, una línia»** ×7 | PETA |
| `models_app/test_base_stages_no_regressio.py:67,71,91` | **«les claus de primer nivell són exactament aquestes»** | PETA si el payload creix |
| `models_app/test_import_poms_{duplicats,resolucions}.py` | 409 amb candidats; **`:129` `test_dues_files_al_mateix_pom_master_es_error_de_fila`** | PETA |
| `models_app/test_copia_model_a_model.py` (16 refs) · `tests_sembra_grading.py` (55 refs) · `test_lectors_capa_onada1.py` (5) · `fitting/test_repas.py` · `pom/test_d2_nomes_override.py` · `test_step_conserva_valors.py` · `test_guarda_rang_mesura.py` · `test_g6_{segell,grading_gates}.py` · `test_g1_graduacio.py` · `test_beach_columnes_descartades.py` · `test_parser_excel.py` · `fitting/{tests,test_graded_table_regla,test_g6_estalitud}.py` · `tenants/tests_enviament_feina.py` | forma del payload i fixtures per `(model,pom)` | COL·LAPSA / PETA |

**Patró endèmic**: `{s.size_label: s.valor for s in …filter(pom=…)}` a **7 fitxers**
(`test_g6_segell.py:91` · `test_step_conserva_valors.py:137` · `test_guarda_rang_mesura.py:115` ·
`test_d2_nomes_override.py:96` · **`test_g6_grading_gates.py:142,179`, que ni filtren per POM** ·
`fitting/test_repas.py:128` · `test_graded_table_regla.py:102-169`). **Cap peta: col·lapsen i passen
verds amb un valor arbitrari.**

**Comptadors durs — la sonda més honesta** (es posen vermells de seguida i diuen quantes files sobren):
`test_g6_segell.py:209,219` · `test_g6_grading_gates.py:141,178` · `test_d2_nomes_override.py:165` ·
`tests_sembra_grading.py:869,882,974`.

**Forat de cobertura: `fitting.POMAlert` no té CAP test a tot el repo** (0 hits).

**91 fitxers de test · 39 toquen la cadena · 52 no** (llistats al detall del camí 1C).

---

## 7 · ELS NODES QUE INVERTEIXEN LA LLEI

No col·lapsen: **bloquegen activament** el cas que la instància vol legitimar. **No s'adapten: s'han de
re-decidir.** Tots porten acta escrita al codi, i **els casos reals que citen SÓN el cas de dues instàncies**.

| # | fitxer:línia | què fa | l'acta |
|---|---|---|---|
| 1 | `pom/size_map_views.py:54-75` + `:671-695` | `by_pom` ≥2 → **400, bloquejar abans d'escriure res** | *«Decisió CTO: BLOQUEJAR»*. Casos: LOS `H.11`/`H.16` |
| 2 | `models_app/extraction_views.py:1148-1193` | `_apply_many_to_one_guard`: desvincula **totes dues** files i les desactiva | `:1155-1171`: *«el destí és `BaseMeasurement`, únic per `(model,pom)`: per legítim que sigui l'àlies, la segona esborra la primera»* |
| 3 | `models_app/extraction_views.py:1734,1753-1756` | error **`pom_ja_usat`**: un POM ja pres per una fila no es pot vincular a una segona | `:1718` |
| 4 | `pom/services.py:613-622` | guard `ja_reclamat` → `pendent_revisio=True` | casos reals BRW `'F'`/`'FF'`→POM 389, `'U'`/`'U2'`/`'U3'`→POM 439 |
| 5 | `seed_losan_rules_v2.py:128-134` | `seen[pom.codi_client]` → «2n àlies → mateix POM = col·lisió, skip» | docstring `:12` |
| 6 | `patterns/models.py:430-437` + `patterns/tests.py:1865` | constraint + test | *«Dos ancoratges del mateix POM a la mateixa peça serien dues veritats sobre la mateixa mesura»* |
| 7 | `frontend/SizeMapSetup.jsx:340-346` + `:427-430` | `dupPomIds` **bloqueja `submitCreate`** | *«Dues files al mateix POM col·lapsarien… pèrdua silenciosa. **Decisió CTO: bloquejar**»* |

**Guards de frontend que fan el cas nou inassolible des de la UI** (9, §3.4-D/E):
`SizeMapSetup.jsx:342-346,427-430` · `TechSheetEditor.jsx:6728-6734` (fila **no-clicable per sempre**),
`:5554-5563`, `:5670`, `:5532-5534` · **`ImportWizard.jsx:537`** (refús **silenciós**: tanca el modal com
si hagués funcionat) · `MeasurementBaseGrid.jsx:138` · `TallerPatro.jsx:366-369` ·
`MeasuresEntryPanel.jsx:86-89` (`materialitzar-poms` amb `{pom_ids: […]}` — **una llista plana no pot
expressar «dues del mateix»**: el camí de gènesi per defecte del model).

**⚠️ Nodes de frontend que perden dades ABANS d'arribar al backend** — han de moure's **al MATEIX commit**
que la comporta, no després: `EditableTable.jsx:163-171` (upsert per `pom_id`) i **`:172`
(`keep_pom_ids`: desar des de la taula de gènesi **podaria** una instància)** ·
`CheckMeasureEditor.jsx:388-389` (`desactivarPom`) · `PropagatedEditor.jsx:68-72`
(`escalatAjustarTalla` amb `lineId` sintètic).

---

## 8 · BUGS VIUS, INDEPENDENTS D'AQUEST TRAM

Trobats en traçar el radi. **No es toquen; s'anoten** (llei del `CLAUDE.md`).

**B-1 · `patterns/views.py:544-549` ja col·lapsa AVUI.**
`ancorats = {p.pom_master_id: p for p in PatternPOM.objects.filter(pattern_piece__pattern_file=fp)}` —
indexat per POM sobre **tot el PatternFile**, però la constraint és `(pattern_piece, pom_master)`: dues
peces del mateix fitxer (davanter/darrere, dreta/esquerra) **poden** ancorar legalment el mateix POM, i el
dict en perd una. `model-poms` diria «ancorat» assenyalant la peça equivocada.

**B-2 · `cleanup_losan_old.py:32` — accessor inexistent.**
`SIZEDEF_EXTERNAL = {'regles_base', 'base_for_items'}`, però l'accessor real d'
`ItemBaseSet.base_size_definition` és **`base_set_for_items`** (`pom/models.py:672`, verificat).
`'base_for_items'` **no existeix**. El guard «cap referència viva → esborro» **mai** salta per una
`SizeDefinition` que és talla base d'un BaseSet actiu. *Mitigant:* l'FK és `PROTECT`, o sigui que
l'esborrat rebotaria amb `ProtectedError` — el dany és que el command mor amb una excepció d'ORM en lloc
del `CommandError` explicatiu.

**B-3 · `pom/s10_views.py:136-152` col·lapsa doble ja avui.**
`POMAlert.update_or_create(model, pom_id, size_fitting)` **sense `size_label`**: una sola alerta per
`(model, pom, sf)` tapa **totes les talles**. (POMAlert = 0 files a staging, §9.)

**B-4 · `bootstrap_tenant.py:61-62` — buit de sembra.**
`ItemBaseSet`, `ItemBaseMeasurement`, `CustomerPOMAlias` i `POMEstadisticaTenant` **no són a cap
`SEED_BLOCK`**. Un tenant nou neix amb pertinences i regles, **sense cap valor base d'item ni cap àlies de
client**.

**B-5 · Trampa de nom: `base_measurements` és una col·lisió a TRES bandes** (verificat):
`pom/models.py:836` (`GarmentTypeItem` → `ItemBaseMeasurement`) · `models_app/models.py:613`
(`Model` → `BaseMeasurement`) · `:614` (`POMMaster` → `BaseMeasurement`).
A `consolidate_pom_los.py:31`, `getattr(pom, 'base_measurements')` resol a **models_app** — correcte,
perquè `ItemBaseMeasurement` viatja separat com a `'item_base_measurements'`. **Però
`GarmentTypeItem.base_measurements` (el de `pom`) NO té CAP call site a tot el repo.** Qualsevol
auditoria per grep del nom barreja tres relacions distintes.

---

## 9 · CAMÍ 3 — QUÈ DIUEN LES DADES

**`los` i `public` són a ZERO a totes les taules de la cadena.** Tot el corpus viu a `fhort`.

| taula | files | qui la pobla de debò |
|---|---|---|
| `models_app_basemeasurement` | 760 | **TEMPLATE 525 (69%)** · MANUAL 165 · IMPORTED 65 · FITTED 4 · CHECKED 1 |
| `fitting_gradedspec` | 2 061 | motor (33 versions, 88 POMs) |
| `pom_garmentpommap` | 1 748 | catàleg (238 `pendent_revisio`, 55 items) |
| `pom_gradingrule` | 1 174 | seeds + size-map |
| `models_app_modelgradingrule` | 510 | CLIENT_RUN 241 · CANONICAL 134 · MANUAL 74 · IMPORTED 61 |
| `pom_customerpomalias` | 336 | DICCIONARI 281 · IMPORT 53 (26 pendents) · MIGRACIO 2 |
| `models_app_measurementchangelog` | 289 | import 229 · manual 34 · checked 17 · fitting 7 · item_standard 2 |
| `fitting_piecefittingline` | 153 · `models_app_sizecheckline` 92 · `pom_itembasemeasurement` 37 · `models_app_pomplacement` **2** · `pom_itembaseset` **1** | |
| **`models_app_modelgradingoverride` · `fitting_pomalert` · `patterns_patternpom` · `pom_pomestadisticatenant`** | **0** | **cap camí exercit mai amb dades reals** |

**Tres coses que el codi amagava i les dades ensenyen:**

1. **El poblador dominant no és l'import: és `materialize_poms`.** 525 de 760 files són `TEMPLATE`, i les
   525 tenen `base_value_cm` NULL. El node crític d'aquest camí (`models_app/views.py:1182`) fa `.first()`.
   `created_by_id` és NULL a **totes** les 760.
2. **270 de 510 `ModelGradingRule` (53%) apunten a un POM sense `BaseMeasurement` al seu model, i totes són
   actives.** La taula de regles **no se sincronitza** amb la de mesures. Igual amb 2 `SizeCheckLine`
   (model 186, `FRONT RISE`/`BACK RISE`). **75 `BaseMeasurement` amb `is_active=False`** (la poda per
   `pom_id` s'ha exercit 75 cops).
3. **Cinc dels deu `ORIGEN_CHOICES` no tenen cap fila avui**: `STANDARD`, `CALCULATED`, `ITEM_STANDARD`,
   `COPIED`, `FEDERAT`. Els dos últims són els escriptors de **còpia model→model** i **retorn de
   federació** — dos dels que haurien d'estampar la instància, **sense banc de proves viu**.
   *(Matís: `origen` és mutable — el changelog demostra que `item_standard` va existir i es va sobreescriure
   a `FITTED`.)*

**Inflació de catàleg des del costat de les dades:** **233 de 370 `POMMaster` (63%) no s'han fet servir mai
en cap mesura** · **171 de 336 àlies** apunten a POMs mai mesurats · **8 files de
`MeasurementChangeLog` amb `base_measurement=NULL`** (overrides «Override talla XL») **quan
`ModelGradingOverride` té 0 files**: l'històric append-only sobreviu al seu objecte.

**Distribució de `capa`: 100% `exterior` a les 9 taules.** El corpus no ha exercit mai el segon valor.

---

## 10 · EINES QUE EL TRAM HA DE REUSAR (`backend/scripts_tmp/`, fora de git)

17 fitxers; **6 reusables tal qual** canviant el nom de columna:

| fitxer | què fa | com es reusa |
|---|---|---|
| `c1_audit_counts.sql` | `DO $$` sobre **3 schemas × 10 taules**; detecta la columna via `information_schema` → **funciona abans i després de la migració** | canviar `capa`→`instancia` a 3 línies = cens T2/T5 |
| `c1_audit_constraints.sql` | 4 blocs contra `pg_constraint`: comportes, unicitats, el `UniqueConstraint` amb nom de `POMPlacement`, el catàleg als 3 schemas. *«django-tenants pot donar un OK enganyós: això llegeix el catàleg de Postgres directament»* | **l'única eina que verifica que una migració ha arribat als 3 schemas** |
| `c1_fumeig_base_stages.py` + `c1_base_stages_T0prima_2026-07-31.json.txt` | línia base T0' viva, **md5 `6e3a980f624215f121ef6abe7ed7a8ae`**, models 467/548/182 | el termòmetre de «cap canvi de contingut». ⚠️ comparar **sense la primera línia** del shell de Django |
| `c1_fumeig_convivencia.py` | 4 superfícies post-revert (fitxa · bateig · graduació · repàs); **B escriu dins un `atomic()` que es desfà** | el patró per verificar que `save()` sap posar una columna NOT NULL sense default de columna |
| `onada1_dump_superficies.py` | **11 superfícies, una per commit**; comparació contra un `git worktree` al commit pre-sprint amb la MATEIXA BD | **és el cens de lectors EXECUTABLE**; cobreix `POMPlacement`, `PieceFittingLine`, `SizeCheckLine`, `GradedSpec` i `BaseMeasurement` d'un cop |
| `models_app/test_lectors_capa_onada1.py:35,43-52,84` | `comporta_alcada()`: `ALTER TABLE … DROP CONSTRAINT` **dins savepoint** + fila germana + rollback | **el harness de dues files germanes, ja provat**. Verificat que DETECTA el col·lapse |

Toquen la cadena però són d'una altra feina: `dump_regles_v3.py` · `extract_grading_catalog.py` ·
`golden_163_snapshot.py` · `dryrun_promocio.py` · `dataop_trams_zombis.py`.
No la toquen: `diag_t3b.py` · `diag_t3c.py` · `diag_t3_t4bis.py` · `g1_probe_proposta.py`.

---

## 11 · TAULA FINAL — RECOMPTES

### Per onada

| onada | nodes | 🔴 | nota |
|---|---|---|---|
| `C1-ins` | **74** | 41 | 14 unicitats + 9 comportes + 10 migracions + el radi de catàleg |
| `top-up-lectors` | **68** | 31 | inclou **2 forats d'Onada 1** i **1 deute de C1 amb data pròpia** |
| `Onada2` | **94** | 47 | **cap escriptor del repo estampa `capa` avui** |
| `C4-ins` | **203** | 96 | 11 payloads dict-per-`pom_id` + 5 serializers cecs + 158 nodes de frontend |
| `F2-patrons` | **32** | 22 | cost zero de dades (0 files); el sostre dur és el format DXF |
| `consolidació-catàleg` | **58** | 18 | el registre canònic del radi invers hi viu |
| `FORA: <motiu>` | **67** | — | sempre amb motiu explícit |
| **TOTAL ÚNIC** | **487** | **255** | |

### Per comportament amb 2 instàncies

| | n | % |
|---|---|---|
| **COL·LAPSA** (silenciós) | **268** | 55% |
| **PETA** | 79 | 16% |
| **IGNORA-2a** | 92 | 19% |
| **OK** | 48 | 10% |

### Per tipus

`READ-dict` 118 · `CONTRACT-api` 96 · `READ-list` 79 · `WRITE-update` 63 · `CONTRACT-engine` 55 ·
`WRITE-create` 51 · `COUNT-gate` 47 · `WRITE-delete` 22.
*(Els nodes de tipus compost compten a cada tipus; total d'ocurrències 531 sobre 487 files.)*

### Per risc

🔴 **255** · 🟠 **112** · 🟡 **62** · ⚪ **58**.

---

## 12 · LÍMITS D'AQUEST DOCUMENT

- **Cap proposta de fix**, per encàrrec. Les assignacions d'onada són **classificació**, no pla d'execució:
  l'ordre i el tall dels commits són decisió humana (Patró C).
- **La deriva de línia és real.** Tot està verificat a HEAD `72d2e579`. Els censos previs són de
  `3efe7f4b` (RECENS) i anteriors; les línies s'han re-verificat, però **una sessió de `dev` concurrent
  pot moure-les** (memòria `ftt-dev-concurrent-git`). Abans de cada onada cal un re-cens delta com el que
  el pla ja preveu.
- **Els recomptes són de cens per grep + lectura de rang + recorregut d'`urls.py`**, no d'anàlisi estàtica
  amb graf de crides. La deduplicació és per `fitxer:línia`; nodes molt propers dins la mateixa funció
  poden haver-se fusionat en una fila.
- **Les afirmacions més portants s'han llegit literalment en aquesta sessió**:
  `pom/services.py:1023-1045` · `:767-783` · `models_app/services_size_check.py:33-42` ·
  `tenants/federation_service.py:542-552,583-612` · `patterns/models.py:426-437` ·
  `patterns/views.py:550-560` · `bootstrap_tenant.py:150-170,328-355` · `pom/models.py:608-620,670-674` ·
  `models_app/test_seccio_captura.py:140-172` · `pom/s2_views.py:278-292` · `pom/s4_views.py:58-70` ·
  `pom/seed_data/consolidate_pom_los.py:25-40` · `fitting/repas_views.py:99-113` ·
  `models_app/views.py:3228-3232` · `frontend/src/pages/SizeMapSetup.jsx:338-348` ·
  `ImportWizard.jsx:535-539` · `MeasureGrid.jsx:477` · `fittingGridAdapter.jsx:142-146`.
  L'OpenAPI, els recomptes de BD i els números de migració són verificació directa, no delegada.
- **No auditat**: el graf de crides complet de `patterns/engine/` (només els punts d'ancoratge citats);
  els fitxers `.ftt` ja desats amb `pomId` a dins (cost de dades **fora de Postgres**, detectat a
  `TechSheetEditor.jsx:2599`, on el comentari *«Cap id hi viatja»* **ja és fals** des de F1);
  el cost d'UI de cap forma (requereix maqueta, llei 3c.5).
- **`ModelGradingRule` és una decisió oberta que aquest document NO tanca.** El docstring
  (`models_app/models.py:900-914`) argumenta que la regla no porta `capa` perquè «el folre creix el mateix
  que l'exterior». **¿Val el mateix per a la instància?** Si dues instàncies del mateix POM tenen deltes
  diferents, l'argument cau i `unique_together=[('model','pom')]` ha de créixer.
  `test_capa_comporta_c1.py:108-116` ho vigila per la porta de la capa.

---

*Registre Patró A profund · triangulació de tres camins · read-only absolut · cap fitxer del repo tocat
fora d'aquest document · cap escriptura a BD · cap command executat.*
