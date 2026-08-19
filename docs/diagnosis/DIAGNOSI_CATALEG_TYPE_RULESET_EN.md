# DIAGNOSI — Catàleg de POMs al Garment Type · Alliberament del RuleSet · Anglès únic

Data: **2026-08-02** · **Patró A (READ-ONLY ABSOLUT)** · staging `/var/www/ftt-staging`, branca `dev`
HEAD verificat: **`277cb9e0d96f440a92e6b36e2dfcfe16809c5206`**
BD: `ftt_staging` @5433 · schemas `public` · `fhort` · `los`
Contrast PROD: `/srv/fhort-prod-backups/incoming/fhort_textile_20260801_023001.dump` (01/08/2026, 3,5 MB),
llegit **només** amb `pg_restore -l` i `pg_restore -a` (cap restauració). Cal `pg_restore` de PG **18**
(`/usr/lib/postgresql/18/bin/pg_restore`): el del sistema és 16.14 i el dump és format 1.16 → «unsupported version».

**Convenció:** cada afirmació porta `fitxer:línia` verificat. **«NO EXISTEIX» = confirmat absent al codi**, no especulat.
Les propostes van marcades `💡 PROPOSTA (a validar)` i **cap d'elles és un fix**: aquesta diagnosi no proposa arreglar res.

**Escriptura feta:** només aquest document (working tree, **NO commitejat**). Cap BD, cap migració, cap fitxer del repo,
cap management command, cap build, cap commit, cap push.

---

## RESUM EXECUTIU

1. **Avui NO existeix cap pertinença POM↔GarmentType.** La pertinença viu **només** a
   `GarmentPOMMap.garment_type_item` (`pom/models.py:580`); el FK legacy `garment_type` es va **eliminar** a la migració
   `pom/0016` (`pom/migrations/0016_alter_garmentpommap_options_and_more.py:24`). Sí que hi ha **tres** relacions
   POM↔Type vives, però totes **estadístiques**, cap de pertinença: `POMEstadisticaGlobal` (`pom/models.py:245`),
   `POMEstadisticaTenant` (`pom/models.py:362`) i `ClientMesuraPerfil` (`pom/models.py:1201`, **17 files a `fhort`**).

2. **La cascada item→Type és canvi de RESOLUCIÓ, no d'esquema** — sempre que el catàleg del Type es derivi de la
   unió dels seus items. `GarmentPOMMap.garment_type_item` és **nullable** (`pom/models.py:581`) i
   `GarmentTypeItem.garment_type` és un FK CASCADE viu (`tasks/models.py:329`): la volta item→type ja es pot fer amb
   un JOIN. Hi ha **6 punts de lookup** a tocar (§B2). Si en canvi el Type ha de poder tenir POMs **propis** (sense
   cap item que els porti), llavors **sí** cal esquema nou (columna `garment_type` o taula pròpia) perquè la unicitat
   actual `(garment_type_item, pom, capa, instancia)` (`pom/models.py:623`) no admet `garment_type_item=NULL` amb
   sentit — i el `__str__` peta amb `'?'` (`pom/models.py:640`).

3. **L'encunyament accidental de POMs ja està consumit i és massiu.** 370 POMMaster a `fhort`, dels quals **228
   `pendent_revisio=True`** i **243 amb `origen_import` informat** (§B8). Hi ha **12 codis duplicats** (24 files) i
   **15 noms duplicats** perquè `POMMaster` **no té cap constraint d'unicitat** a BD (verificat a
   `pg_index`: només la PK). I hi ha **18 parelles exactes base+qualificador** (p.ex. `CH «Chest width»` vs
   `B1 «CHEST WIDTH RELAXED»`, `H11 «SLEEVE OPENING»` vs `SL OP STR «Sleeve opening stretched»`) — encunyament ja
   pagat que la capa/instància hauria d'haver absorbit.

4. **La porta de creació de POM està OBERTA sense gate.** `POMMasterViewSet` és un `ModelViewSet` complet amb
   `permission_classes = [IsAuthenticated]` i **cap** `get_permissions()` (`pom/views.py:50-59`): qualsevol usuari
   autenticat pot fer `POST /api/v1/poms/`. El seu germà explícit `create_tenant_pom_view` també és només
   `IsAuthenticated` (`pom/wizard_views.py:415-416`). En canvi TOTS els altres viewsets del mòdul (GarmentPOMMap,
   ItemBaseSet, ItemBaseMeasurement, GradingRuleSet, CustomerPOMAlias, SizeSystem…) **sí** tenen gate `CONFIGURE`.

5. **El ruleset està encorsetat en 9 nodes de decisió** (§B5), però **el motor de mesures NO n'és cap**. El motor
   itera sobre les mesures del model i busca la regla per `pom_id` (`pom/services.py:233-234`,
   `pom/services.py:682-708`): la **intersecció ja hi és**. El que NO intersecta és la **materialització** de regles
   residents (`models_app/services.py:256-283`), que copia **totes** les regles del ruleset al model.

6. **L'anglès únic al catàleg és quasi tot additiu i té precedent viu al repo.** `i18n_content.TranslatableMixin`
   (`i18n_content/models.py:63`) ja implementa exactament «EN canònic a la columna + traduccions al costat», i
   `commerce.Product`/`PaymentTerms` ja l'usen (`commerce/models.py:47,397`). El que es trencaria és la **segona
   línia** de les taules impreses de la fitxa (`nom_ca` com a subtítol, `TechSheetEditor.jsx:4849,4921,4983`) i
   **dos tests** que exigeixen els tres idiomes sembrats (`pom/tests.py:204,257`). El bateig per model
   (`nom_canonic_model`/`nom_traduit_model`) i l'i18n d'interfície queden **intactes**.

---

## B1 · On viu avui l'ancoratge de POMs

### B1.1 · Les taules

| Taula | Fitxer:línia | Àncora | Unicitat a BD (verificada a `pg_index`) |
|---|---|---|---|
| `GarmentPOMMap` | `pom/models.py:573` | `garment_type_item` (nullable) | `(garment_type_item_id, pom_id, capa, instancia)` |
| `ItemBaseSet` | `pom/models.py:644` | `garment_type_item` | `(item, size_system, fit_type)` + parcial `WHERE fit_type IS NULL` |
| `ItemBaseMeasurement` | `pom/models.py:840` | `base_set` (+ `garment_type_item` denormalitzat) | `(base_set_id, pom_id, capa, instancia)` |
| `POMEstadisticaGlobal` | `pom/models.py:245` | **`garment_type_global`** (FK) | `(pom_global, garment_type_global, segment, talla_label)` |
| `POMEstadisticaTenant` | `pom/models.py:362` | **`garment_type`** (CharField, no FK) | `(pom, garment_type, talla_label)` |
| `ClientMesuraPerfil` | `pom/models.py:1201` | **`garment_type`** (FK a `GarmentType`) | cap declarada |
| `GradingRule` | `pom/models.py:1116` | `rule_set` + `pom` | `(rule_set_id, pom_id)` |
| `CustomerPOMAlias` | `pom/models.py:379` | `customer` + `client_code` | `(customer_id, client_code)` |

`GarmentPOMMap.capa` i `.instancia` porten **comportes CHECK actives** que només deixen passar `'exterior'` i `''`
(`pom/models.py:627-637`); el mateix a `ItemBaseMeasurement` (`pom/models.py:928-937`). Es retiren a C4 / C4-ins
(pendents, vegeu la memòria de Tram C).

### B1.2 · Lectors i escriptors de `GarmentPOMMap`

**Lectors (aplicació):**
- `models_app/views.py:1038` — `suggested_poms_view` (POMs suggerits d'un MODEL, via el seu item).
- `models_app/views.py:1119` — `materialize_poms_view` (la sembra item→model).
- `models_app/views.py:3745` — el superset de l'item al diff de promoció model→item (LLEI 6).
- `pom/wizard_views.py:78` — `GET /api/v1/poms/suggerits/?garment_type_item=X`.
- `pom/views.py:319-348` — `GarmentPOMMapViewSet` (CRUD; `filterset_fields` només `garment_type_item`, `pom`,
  `is_key`, `obligatori`, `pendent_revisio` — **el filtre `?garment_type=` es va retirar** amb la 0016,
  `pom/views.py:336-337`).
- `pom/s9_views.py:55-58` — comptador de salut d'onboarding.

**Escriptors (aplicació):**
- `models_app/views.py:3865` — `get_or_create` dins del **confirm** de la promoció model→item (LLEI 6: només amb
  confirmació humana i gate CONFIGURE).
- `pom/views.py:319` — el `ModelViewSet` (POST/DELETE des del **mode ASSIGN** del POMBrowser,
  `frontend/src/components/POMBrowser/POMBrowser.jsx:148,163`).

**Escriptors (comandes):** `load_losan_package.py:369` · `load_map_inline.py:150` · `consolidate_pom_catalog.py:216`
· `author_baby_pom_maps.py:218` · `reseed_tenant_fhort.py:278,312,320` (**OBSOLET i autoguardat**:
`reseed_tenant_fhort.py:82-88` aixeca error perquè usa l'eix `garment_type` eliminat) ·
`validate_los_maps.py:83,99` (només toca `pendent_revisio`) · `export_losan_package.py:252` (lectura d'export) ·
`reconcile_tenant_poms.py` (posa `actiu=False`, mai esborra).

### B1.3 · Existeix avui alguna relació GarmentType↔POM?

**SÍ, tres — i cap és de pertinença.** Prova:

- `POMEstadisticaGlobal.garment_type_global` — FK real a `GarmentTypeGlobal` (`pom/models.py:247`). **0 files** als
  tres schemas de staging i **0** a PROD.
- `POMEstadisticaTenant.garment_type` — **CharField de 80**, no FK (`pom/models.py:364`). **0 files**.
- `ClientMesuraPerfil.garment_type` — FK real a `GarmentType` (`pom/models.py:1201`), amb `pom` FK a `POMMaster`
  (`pom/models.py:1202`). **17 files a `fhort`**, 0 a `los`. És estadística Welford per
  `(codi_client, garment_type, POM, talla)`.

**NO EXISTEIX** cap taula, cap FK ni cap `related_name` que declari «aquest POM pertany a aquest GarmentType».
Verificat per grep exhaustiu de `GarmentType` a `pom/models.py`: els únics consumidors del model són
`GarmentTypeItem.garment_type` (`tasks/models.py:329`), `RuleSetScopeNode.garment_type` (`pom/models.py:1079`),
`SizingProfile.garment_type` (`pom/models.py:1373`) i `ClientMesuraPerfil.garment_type`.

**Veredicte B1:** l'univers de POMs d'un Type **és avui derivable** (unió dels seus items) però **no és declarable**.

---

## B2 · Cost real de la cascada item→Type

### B2.1 · Esquema o resolució?

**Depèn de quina de les dues lectures del punt 1 del context s'implementi:**

- **Lectura A — «el Type és la unió dels seus items».** **Cap canvi d'esquema.** El JOIN ja és possible:
  `GarmentPOMMap.objects.filter(garment_type_item__garment_type_id=X)`. El FK `GarmentTypeItem.garment_type` és
  CASCADE i obligatori (`tasks/models.py:329-330`); `GarmentType.items` és el `related_name` viu, i ja s'hi
  compta a `pom/views.py:117` (`annotate(items_count=Count('items'))`).
- **Lectura B — «el Type pot tenir POMs propis, sense item».** **SÍ cal esquema.** Tres obstacles concrets:
  1. La unicitat és `(garment_type_item, pom, capa, instancia)` (`pom/models.py:623`). Amb `garment_type_item=NULL`
     Postgres tracta els NULL com a distints → **dues files idèntiques del mateix POM del mateix Type serien legals**.
  2. `GarmentPOMMap.__str__` fa `self.garment_type_item.code if ... else '?'` (`pom/models.py:640`): funciona però
     ja declara per escrit que el NULL és un cas degradat.
  3. `ItemBaseSet` i `ItemBaseMeasurement` pengen **estrictament** de l'item (`pom/models.py:676,852`): un POM del
     Type sense item **no tindria on portar valor base**.

### B2.2 · Els punts de lookup afectats (6)

| # | Node | Fitxer:línia | Què fa avui si no troba res |
|---|---|---|---|
| 1 | `materialize_poms_view` (sembra item→model) | `models_app/views.py:1119-1121` | `total_template=0`, cap BaseMeasurement, resposta 200 muda |
| 2 | `suggested_poms_view` (per model) | `models_app/views.py:1038-1040` | `{'poms': [], 'total': 0}` |
| 3 | `suggested_poms_view` (per item, wizard) | `pom/wizard_views.py:78-81` | `warning: 'Cap POM mapejat per a aquest item'` — **amb acta escrita** contra el fallback (§B9) |
| 4 | `GarmentPOMMapViewSet` list | `pom/views.py:319-348` | llista buida (mode ASSIGN del POMBrowser) |
| 5 | Diff de promoció model→item (LLEI 6) | `models_app/views.py:3745-3746` | tot el que el model té surt com a «ampliaria el superset» |
| 6 | Guard `pom_ids` de la sembra | `models_app/views.py:1124-1126,1266` | els POMs fora del mapa es reporten a `pom_ids_desconeguts` + `warning` |

Els nodes 1, 5 i 6 són **escriptors o guards d'escriptura**: una cascada que hi entri canvia **què s'escriu**, no
només què es mostra. Els nodes 2, 3 i 4 són **lectura pura**.

### B2.3 · El cas «el tècnic informa el Type però no l'item»

Avui **no arriba ni al lookup**: els tres camins tallen abans.
- `models_app/views.py:1032-1033` — `if not model.garment_type_item_id: return {'poms': [], 'warning': 'Garment type item no definit'}`.
- `models_app/views.py:1100-1102` — la sembra retorna `materialized: 0` amb el mateix avís.
- `pom/wizard_views.py:73-75` — `if not item_id: warning: 'garment_type_item requerit'`.

A més, el **wizard de model exigeix l'item** al frontend: `ModelWizard.jsx:398-400` bloqueja la creació amb
`if (!item) { setError(t('model_wizard.gti_required')); setBlock(2) }`, amb l'acta «B4b — GTI obligatori: és la
baula del motor de temps (matriu item×task_type)». Servir des del Type sense item **no és avui un forat**:
és una porta tancada amb acta.

**Veredicte B2:** lectura A = 6 punts de resolució, 0 migracions. Lectura B = 6 punts + 1 migració d'unicitat +
decisió oberta sobre on viu el valor base d'un POM del Type.

---

## B3 · Sembra i consum

### B3.1 · `materialize_poms_view` — la sembra item→model
`models_app/views.py:1066-1268`. Cadena real:
1. Exigeix `garment_type_item` (`:1100`).
2. Llegeix el mapa de l'item (`:1119`), opcionalment acotat per `pom_ids` (`:1110-1126`).
3. Resol el **món**: `resolve_item_base_set(item, model.size_system_id, model.fit_type)` (`:1133`, definit a
   `pom/models.py:788`). Lookup **directe**, cap cascada (llei declarada a `pom/models.py:653-654`).
4. Camí llegat si el món no té set i l'item té ≤1 set (`:1150-1157`).
5. **Guard de talla P1** (`:1159-1180`): talles divergents → pertinença sí, valor **no**.
6. **Sobirania del model** (`:1215-1228`): només omple un `TEMPLATE` buit.
La clau de sembra és **completa** `(pom_id, capa, instancia)` (`:1142,1186`).

### B3.2 · Wizard de POMs
- Backend: `pom/wizard_views.py:59-108` (`poms/suggerits/`), `:111-...` (`poms/cerca/`), `:415` (`poms/crear-tenant/`),
  `:458` (`poms/<id>/nomenclatura/`). Registrats **abans** del router per no col·lidir amb el detail
  (`pom/urls.py:33-50`).
- Frontend: `ModelWizard.jsx` (pas graduació, `:331`), `POMBrowser.jsx` (mode `assign`).

### B3.3 · Mode ASSIGN
`frontend/src/components/POMBrowser/POMBrowser.jsx:131-170`: `assignAdd` fa `POST /api/v1/garment-pom-maps/` i
`assignRemove` fa `DELETE`. **Sempre ancorat a un `garment_type_item`** (`:101-110`). La resposta 400 es tradueix a
«ja assignat» (`:157`) — o sigui que la unicitat de BD és el que sosté la UX.

### B3.4 · Comandes de seed
| Comanda | Escriu | Estat |
|---|---|---|
| `extend_pom_catalog.py:177,195` | POMGlobal + POMMaster (`update_or_create` per `codi` / `pom_global`) | viva, idempotent |
| `seed_baby_poms.py:253,260` | POMGlobal + POMMaster | viva, idempotent |
| `seed_master_delta_catalog.py:71,78,83,91` | CustomerPOMAlias + POMMaster + POMGlobal | viva |
| `consolidate_pom_catalog.py:156,216,236,238,241` | POMGlobal + POMMaster + GarmentPOMMap + Alias | viva |
| `load_map_inline.py:146-150` | GarmentPOMMap | viva |
| `author_baby_pom_maps.py:218` | GarmentPOMMap | viva, dry-run per defecte (`:107`) |
| `load_losan_package.py:265,369,387,400` | POMMaster, GarmentPOMMap, ItemBaseMeasurement, **ItemBaseSet** | viva |
| **`reseed_tenant_fhort.py`** | GarmentPOMMap amb l'eix `garment_type` | **OBSOLET amb guard dur** (`:82-88`): «usa l'eix `garment_type` de GarmentPOMMap, eliminat a la migració 0016». Faria `GarmentPOMMap.objects.all().delete()` (`:278`) |
| `crea_sizing_profiles.py` | SizingProfile (eixos vells: target×família×construcció×fit×escala) | **viva i és l'única via de creació**: «no hi ha endpoint de creació de `SizingProfile`» (docstring `:8-10`) |
| `seed_scope_nodes_proposals.py` | RuleSetScopeNode | viva, dry-run per defecte |

**Comandes que encara apunten a eixos vells:** `reseed_tenant_fhort.py` (eix `garment_type` de GarmentPOMMap, ja
guardat) i tota la família `crea_sizing_profiles` / `seed_baby_months_profiles` / `seed_kids_baby_target_map` /
`seed_losan_*`, que treballen sobre els **cinc eixos** de SizingProfile — que és exactament el que el punt 2 del
context vol tornar informatiu.

### B3.5 · `bootstrap_tenant` i les seves claus naturals
`tasks/management/commands/bootstrap_tenant.py:126-190`. Claus naturals rellevants:

| Model | Clau natural | Nota |
|---|---|---|
| `POMGlobal` | `('codi',)` | `:143` |
| `POMMaster` | `('codi_client',)` | `:148` — **i el codi NO és únic a BD** (12 duplicats a `fhort`, §B8). Amb `--additive` això cau a l'«ambigu» de `Piece.ambigus` (`:196`) |
| `GarmentType` | `('codi_client',)` | `:146` — sense constraint |
| `GarmentTypeItem` | `('garment_type', 'code')` | `:151` — sí té constraint |
| `GarmentPOMMap` | `('garment_type_item', 'pom', 'capa', 'instancia')` | `:167` — **ja ampliada a C1-ins** |
| `GradingRuleSet` | **`('nom',)`** | `:150`, amb `customer: NULL` i `parent_version: DEFER` |
| `GradingRule` | `('rule_set', 'pom')` | `:168` |
| `SizingProfile` | `('target','garment_type','construction','fit_type','size_system','version')` | `:170-173` — **els cinc eixos són la identitat de sembra** |

**El que `bootstrap_tenant` NO copia:** `ItemBaseSet`, `ItemBaseMeasurement`, `RuleSetScopeNode`,
`MeasurementLayer`, `PatternPieceRole`, `CustomerPOMAlias`, `POMCategory` sí (`:141`) però els satèl·lits de valor
i d'àmbit **no**. Verificat: no apareixen a `_spec()` (`:126-176`).

**Fet clau per al punt 2:** la clau natural del ruleset **ja és el nom** — o sigui que la identitat «nom lliure del
client» que el context demana **ja és la que la federació assumeix**. El que xoca és la constraint
`uniq_client_container_identity` (§B5).

**Veredicte B3:** la sembra ja parla la clau completa; la cotilla no és a la sembra, és al matching.

---

## B4 · La porta de creació de POM

### B4.1 · Cens complet dels punts de creació

| # | Node | Fitxer:línia | Gate | Tipus |
|---|---|---|---|---|
| 1 | `POMMasterViewSet` (POST `/api/v1/poms/`) | `pom/views.py:50-59` | **CAP** (`IsAuthenticated`, sense `get_permissions`) | 🔴 **SILENCIÓS** |
| 2 | `create_tenant_pom_view` (`poms/crear-tenant/`) | `pom/wizard_views.py:415-455` | `IsAuthenticated` (sense CONFIGURE) | 🟡 deliberat (formulari), gate feble |
| 3 | Import pas 2 · `resolucions` → `accio='crea'` | `models_app/extraction_views.py:1869-1881` | tria de fila explícita + `IsAuthenticated` | 🟢 **HUMÀ** (el tècnic dona codi i nom) |
| 4 | Import pas 2 · `poms_tenant_only` | `models_app/extraction_views.py:1893-1917` | 409 previ per codi duplicat (`:1838-1846`) | 🟡 **semi-automàtic**: pren `codi_fitxa` a cegues; nota literal «Creat automàticament per import» (`:1909`) |
| 5 | Diccionari del client · `action='create'` | `pom/dictionary_views.py:137-154` | `_Configure` (CONFIGURE) `:82` | 🟡 comentari propi: **«POM tenant-only nou (sense gate — fase beta)»** (`:145`) |
| 6 | `maybe_learn_customer_alias` | `pom/services.py:624-640` | cap (efecte lateral de l'import) | 🟡 crea **ÀLIES**, no POM; amb guard anti-col·lisió → `pendent_revisio` (`:613-630`) |
| 7 | `setup_tenant_from_excel_view` → POMGlobal | `pom/s9_views.py:179-193` | `IsAuthenticated` | ⚫ **MORT**: escriu `codi_intern`, `nom_cat`, `htm_metode_en`, `is_key_measure` — **cap existeix a `POMGlobal`** (`pom/models.py:32-59`), i el bloc va dins d'un `try/except Exception: pass` (`:193-194`). L'endpoint sí està wired (`tasks/urls.py:253`) |
| 8..14 | Comandes de seed (§B3.4) | — | CLI (root/ssh) | 🟢 acte conscient |

### B4.2 · Per què el 409 de l'import existeix
`models_app/extraction_views.py:1798-1801` ho declara: «el catàleg de tenant **NO té cap constraint d'unicitat**
sobre (pom_global, codi_client) … Dos POMMaster tenant-only amb el mateix codi són, doncs, un estat **LEGAL** de la
BD». Verificat a `pg_index`: `pom_pommaster` només té `pom_pommaster_pkey`. El 409 porta els candidats
(`_candidats_de_codi`, `:1694-1712`) perquè la decisió es prengui a la fila.

### B4.3 · Recompte real d'encunyament ja consumit

**Staging `fhort`** (370 POMMaster · 274 POMGlobal · 336 àlies):

| Senyal | Valor |
|---|---|
| POMMaster **tenant-only** (`pom_global IS NULL`) | **96** |
| POMMaster **`pendent_revisio=True`** | **228** (61,6 %) |
| POMMaster amb `origen_import` informat | **243** |
| POMMaster **sense cap `GarmentPOMMap`** | **204** (55 %) |
| Codis `codi_client` duplicats | **12** codis / 24 files |
| Noms `nom_client` duplicats (case-insensitive) | **15** |

Desglossament d'`origen_import` (top): `diccionari:LOS:2026-07-18` **111** · `diccionari:BRW:2026-07-13` **36** ·
`LOS diccionari 4B-bis` **20** · `SS26 TROUSERS TWILL (14-26-SS-0002)` **13** · 6 tokens d'UUID de sessió d'import
(10+9+8+7+4+4…) · `LOS màster delta v1` **5**.
👉 **Els dos camins que més han encunyat són el DICCIONARI (167 files, node #5) i l'IMPORT (node #4)** — precisament
els dos que el §B4.1 marca com a semi-automàtics.

**POMs amb qualificador enganxat al nom** (staging `fhort`, per aparició del token com a paraula):

| Qualificador | POMMaster | POMGlobal fhort | POMGlobal public |
|---|---|---|---|
| RELAXED | 19 | 15 | 8 |
| STRETCHED | 10 | 9 | 9 |
| EXTENDED | 15 | 12 | 2 |
| FRONT | 50 | 36 | 9 |
| BACK | 42 | 27 | 7 |
| INNER | 8 | 8 | 0 |
| LINING | 4 | 1 | 0 |
| TOTAL / HALF / UPPER | 4 / 1 / 1 | 4 / 1 / 1 | 1 / 1 / 1 |
| **LEFT / RIGHT / OUTER / FOLRE / FLAT / ON BODY** | **0** | **0** | **0** |

POMs el nom dels quals **acaba** en RELAXED/STRETCHED/EXTENDED/LINING/INNER/OUTER: **30**.

**Parelles exactes base ↔ base+qualificador (18)** — l'encunyament que la capa/instància hauria absorbit:

```
CH      Chest width       →  B1 CHEST WIDTH RELAXED · B2 CHEST WIDTH EXTENDED
WA      Waist width       →  C4/C.4 WAIST WIDTH RELAXED · C1/C.1 WAIST WIDTH EXTENDED
LEG OP  Leg opening       →  F5/F.5 LEG OPENING RELAXED · F6/F.6 LEG OPENING EXTENDED
H11     SLEEVE OPENING    →  J1 Sleeve opening relaxed · H14 SLEEVE OPENING EXTENDED · SL OP STR Sleeve opening stretched
S.10    HOOD LENGTH       →  S54 HOOD LENGTH RELAXED · S55 HOOD LENGTH EXTENDED
V4      PIECE WIDTH       →  V5 PIECE WIDTH EXTENDED
CUF H   Cuff height       →  GN CUFF HEIGHT INNER
H16     CUFF OPENING      →  GL CUFF OPENING INNER
```

Noteu els **dobles**: `C4` i `C.4` són la MATEIXA mesura amb dos codis — l'encunyament s'ha duplicat sobre si mateix.

`FRONT`/`BACK` (92 files) són cas a part: `POMGlobal.body_section` ja té el vocabulari
(`FRONT/BACK/SIDE/SLEEVE/BOTH/HEAD`, `pom/models.py:27-30`) i el nom el repeteix igualment.

**Veredicte B4:** hi ha **una** porta veritablement silenciosa (`POMMasterViewSet`) i **dues** semi-automàtiques
(import tenant-only, diccionari), amb l'acta de la segona escrita al propi codi («sense gate — fase beta»).
El catàleg ja porta ≥30 POMs d'encunyament per qualificador i 12 codis duplicats.

---

## B5 · La cotilla del ruleset — cens complet

### B5.1 · Identitat actual de `GradingRuleSet` (`pom/models.py:945-1057`)

| Camp | Línia | Paper avui |
|---|---|---|
| `nom` | `:971` | display; **clau natural de federació** (`bootstrap_tenant.py:150`); **no únic** |
| `origen` (CANONICAL/CLIENT_RUN/IMPORT/NULL) | `:967` | condiciona la constraint parcial i la confidencialitat |
| `garment_group` FK | `:972` | eix d'abast **bast**; fallback de `_scope_matches` |
| `size_system` FK | `:979` | **DECIDEIX** (identitat + bloqueig dur d'assignació) |
| `garment_type_item` FK | `:987` | **DECIDEIX** — «node fi de la identitat» |
| `customer` FK | `:995` | **DECIDEIX** (RUN-CLIENT) |
| `targets` M2M | `:1010` | **DECIDEIX** (el FK `target` es va retirar a `pom/0043`) |
| `construction` FK | `:1017` | **DECIDEIX** |
| `fit_type` FK | `:1022` | **DECIDEIX** (identitat + matching) |
| `is_system_default` | `:1027` | bloqueja delete (`pom/views.py:243`) i update de regles (`:311`) |
| `parent_version` / `version_number` / `codi_sistema` | `:1029-1037` | versionat; no decideix |
| `pendents_vincular` (JSON) | `:1000` | traça |

**Unicitat a BD:** `uniq_client_container_identity` — `UNIQUE (customer_id, size_system_id, garment_type_item_id,
fit_type_id) WHERE origen='CLIENT_RUN'` (`pom/models.py:1049-1053`, verificada a `pg_index`).

### B5.2 · Els 9 nodes que fan DECIDIR els eixos

| # | Node | Fitxer:línia | Què fa avui | Què queda sense feina si els eixos passen a informatius |
|---|---|---|---|---|
| 1 | `uniq_client_container_identity` | `pom/models.py:1049` | impedeix 2 contenidors del mateix client per `(system,item,fit)` | **Tota la constraint.** Cal migració per retirar-la o la creació lliure petarà amb IntegrityError |
| 2 | `resolve_grading_container` NIVELL 1 | `pom/grading_utils.py:698-708` | identitat dura `customer+system+item+fit` | El nivell sencer. Queda la guarda d'ambigüitat, però sense predicat no té què desempatar |
| 3 | `resolve_grading_container` NIVELL 2 | `pom/grading_utils.py:710-735` | `targets__codi` + `construction__codi` + `fit_type__codi` + `_scope_matches`; **retorna `none` si falta QUALSEVOL dels tres** (`:720,724,728`) | Els 3 `else: return none` i els 3 `filter()`. Queda `customer` + `size_system` + abast |
| 4 | `_scope_matches` | `pom/grading_utils.py:641-658` | mirall exacte de `scopeApplies(strict)` | Es manté si l'abast (`RuleSetScopeNode`) segueix sent aplicabilitat; **no** és un eix del punt 2 |
| 5 | `cerca_contenidor_client` | `pom/grading_utils.py:619-638` | **DEPRECADA** amb acta («G5 = migrar aquell caller i esborrar-la», `:623`) | Tota. L'únic caller és `pom/size_map_views.py:750` (pre-check 409 `container_exists`, `:745-759`) |
| 6 | `matchingRuleSetsStrict` (frontend) | `gradingAxes.js:201-212` | `targets_codis` no-buit **i** inclou target · `construction_codi ===` · `fit_type_codi ===` · `scopeApplies(strict)` · `size_system ===` | Els 4 primers predicats. Queda `actiu` + `size_system` (si es conserva) |
| 7 | `availableFitsStrict` | `gradingAxes.js:216-230` | omple el selector de FIT **només** amb fits que porten a graduació real | Tota la funció: sense eix `fit` decisori, el selector no té criteri |
| 8 | `matchingRuleSets` / `classifyRuleSets` (lenient) | `gradingAxes.js:156-165` / `:181-194` | filtre i classificació amb comodí NULL; `classifyRuleSets` **no elimina, atenua** (LLEI DELS WIZARDS ELIMINATIUS, C5, `:167-180`) | `matchingRuleSets` queda buit de feina. `classifyRuleSets` **sobreviu**: és exactament la forma «etiquetes informatives» que el punt 2 demana |
| 9 | `_validar_ruleset_assignable` | `models_app/views.py:568-622` | 3 portes: **0 regles → 400 dur** · **`size_system` divergent → 400 dur** (`:598-608`) · **`customer` divergent → 409 confirmable** (`:610-620`) | La porta de `size_system` és la que xoca de front amb «els eixos no decideixen». Les altres dues **no** són eixos (una és integritat, l'altra confidencialitat) |

**Nodes annexos que consumeixen els eixos sense decidir el contenidor:**
- **Autoselecció al wizard: JA RETIRADA.** `ModelWizard.jsx:337-344` porta l'acta sencera: «B1 — autoselecció
  RETIRADA (31/07) … el model neix NET i la graduació s'incorpora pel gest». El que hi queda és una **neteja
  defensiva** (`:346-357`): si el ruleset hidratat deixa de casar amb `strictMatches`, es posa a `null`.
  👉 **Aquest `useEffect` és el node que, amb eixos informatius, deixaria de tenir criteri per netejar.**
- `orderWithSuggestedFirst` (`gradingAxes.js:235-239`) — només ORDRE. Ja compleix «suggerir ≠ arrossegar».
- `pom/views.py:227-234` — `?amb_regles=1` amaga contenidors esquelet. No és eix.

### B5.3 · Relació amb `SizingProfile`

**No és 1:1 amb el ruleset; és 1:0..1 i el ruleset és el costat opcional.**
- `SizingProfile.grading_rule_set` és **nullable des de C3** (`pom/models.py:1391-1393`), amb `on_delete=PROTECT`.
  L'acta (`:1382-1390`): «Un SizingProfile és, abans que res, una declaració d'ÀMBIT … La graduació és un
  SUGGERIMENT que el perfil pot portar, no la seva raó de ser».
- La identitat real del perfil són **els cinc eixos** `(target, garment_type, construction, fit_type, size_system)`
  (`pom/models.py:1371-1381`) — i **no hi ha cap constraint d'unicitat a BD** (verificat: `pom_sizingprofile` només
  té la PK). La unicitat només viu a `crea_sizing_profiles` (idempotència per comanda) i a `bootstrap_tenant.py:170`.
- **On DECIDEIX:** `pom/views.py:124-155` — `GarmentTypeViewSet.get_queryset()`. Amb `?target=<codi>` **exclou**
  famílies sense perfil (`:138-143`); amb `?compat_target=` només **anota** (mode C5, `:144-155`). O sigui:
  **una família sense SizingProfile pot desaparèixer del pas Peça del wizard**.
- Recompte: **46 SizingProfile a `fhort`** vs **21 GarmentType** (52 i 21 a PROD·fhort; 25 i 21 a PROD·los).

### B5.4 · Llista NOMINAL de tests que cauen

**Backend (cauen o canvien de veredicte):**
1. `models_app/tests_sembra_grading.py::UpdateStep2GradingTest::test_size_system_creuat_bloqueja` (`:275`) — **cau
   directament**: afirma que un `size_system` divergent bloqueja amb 400.
2. `models_app/tests_sembra_grading.py::UpdateStep2GradingTest::test_canvi_de_size_system_al_mateix_patch_es_valida_contra_el_nou` (`:312`) — mateixa llei.
3. `models_app/tests_sembra_grading.py::UpdateStep2GradingTest::test_customer_creuat_avisa_i_despres_desa_amb_provinenca_real` (`:283`) — sobreviu si es conserva la porta de client (que **no** és un eix del punt 2), però la revisió l'ha de tocar.
4. `models_app/tests_sembra_grading.py::UpdateStep2GradingTest::test_ruleset_buit_bloqueja` (`:267`) — **no cau** (integritat, no eix). Es llista perquè viu al mateix gate.
5. `pom/test_p7_target_fk.py` — **5 tests** (`:48,53,61,77,87`): tot el fitxer defensa que `targets` (M2M) és la
   font única del ventall i que **es fa servir per TROBAR** (`test_ruleset_amb_un_target_el_conserva_i_es_troba`,
   `:61`). Amb targets informatius, «es troba» deixa de voler dir el mateix.
6. `pom/test_p4_scope_proposals.py` — **7 tests** (`:76-156`). Defensen `RuleSetScopeNode` (aplicabilitat). **No
   cauen pel punt 2** si l'abast es manté com a disponibilitat; entren a la llista perquè comparteixen el matcher.
7. `models_app/test_d1_proposta_promocio.py::test_res_entra_al_contenidor_sense_demanar_ho` (`:144`) — depèn de
   `resolve_grading_container` retornant un contenidor concret.

**Frontend:** `frontend/src/components/grading/gradingAxes.test.js` — **11 tests** amb el runner natiu de Node
(`node --test`, capçalera `:1-8`; el projecte **no té vitest ni jest**). Els 5 de `classifyRuleSets` (`:62,69,77,83,89`)
són els que consagren l'aritmètica d'eixos; els 6 d'`orderWithSuggestedFirst` (`:20-52`) **no cauen**.
⚠️ **`matchingRuleSetsStrict` i `availableFitsStrict` NO tenen cap test.** Els nodes 6 i 7 de §B5.2 es podrien
alliberar sense que cap prova ho digués.

**Veredicte B5:** 9 nodes, 1 constraint de BD, ~14 tests backend i 5 frontend en el radi. El node més dur és el
**#1 (la constraint parcial)**: és l'únic que no es pot canviar sense migració.

---

## B6 · Import de fitxa i graduació

### B6.1 · On es decideix avui el contenidor
`models_app/extraction_views.py:2392-2499` — bloc **PRE-FLIGHT GRADING (D1)**, tot **abans** de qualsevol escriptura
de grading.
1. `derive_rules_from_fitxa` (pur, `:2421-2425`) → `fitxa_specs`.
2. **422 `grading_taula_incompleta`** (`:2440-2458`) amb `transaction.set_rollback(True)`: cap regla d'una taula
   incompleta (el forat del bug 166).
3. `resolve_grading_container(customer, size_system, target, construction, fit, garment_group, item)` (`:2466-2468`).
4. **409 `container_ambigu`** (`:2476-2483`) — més d'un candidat, mai el primer arbitràriament.
5. **409 `container_absent`** (`:2484-2495`) — si no hi ha contenidor i el tècnic no ha dit `container_choice`
   (`'create'` | `'no_container'`, `:2470`).

### B6.2 · Les tres branques d'escriptura (`:2624-2727`)
- **Sense contenidor + `no_container`** (`:2628-2637`): `model.grading_rule_set = None` i **regles residents pròpies**
  (`resident_specs = fitxa_specs`).
- **Sense contenidor + `create`** (`:2638-2665`): crea un `GradingRuleSet` **AMPLI** (`garment_type_item=None`,
  `:2650-2656`), `origen=CLIENT_RUN`, amb `targets.add(rs_target)` (`:2657`); l'omple i l'assigna.
- **Contenidor esquelet (0 regles)** (`:2666-2678`): sembrar-lo des de la fitxa és legítim.
- **Contenidor AMB regles → INTOCABLE (llei M3)** (`:2679-2721`): el catàleg del client **no es toca**; les
  divergències van a `ModelGradingOverride` per-talla (`:2701-2708`) + un **Watchpoint estructurat**
  (`proposta_promocio` → `Watchpoint.objects.create(..., dades=proposta)`, `:2713-2718`), i les residents s'esborren
  (`:2696`).

Tot dins d'un savepoint amb **degradació amb gràcia**: si peta, es restaura `prev_grs_id` i s'avisa (`:2722-2727`).

### B6.3 · «Ruleset importat sembrat al model» — existeix el mecanisme?

**SÍ, i el precedent el calca exactament.** `ModelGradingRule` (`models_app/models.py:982`) és la graduació
**RESIDENT al model**, i el seu vocabulari d'`origen` **ja inclou `'IMPORTED'`** amb l'etiqueta literal
«Importat de fitxa externa» (`models_app/models.py:1016`). La sembra la fa
`materialize_model_grading_rules_from_specs(model, resident_specs, origen='IMPORTED')`
(`models_app/services.py:286-309`, cridada a `extraction_views.py:2723-2725`).

**Dades vives a `fhort`:** 510 `ModelGradingRule` — `CLIENT_RUN` 241 · `CANONICAL` 134 · `MANUAL` 74 ·
**`IMPORTED` 61**. O sigui: **61 regles residents ja són "ruleset importat sembrat al model"**. El mecanisme no
s'ha d'inventar; ja corre.

El motor el llegeix **amb prioritat** sobre el ruleset extern: `_load_grading_rules` retorna les residents si
n'hi ha, i només cau al `GradingRuleSet` si el model no en té cap (`pom/services.py:699-708`).

### B6.4 · On aniria l'avís de sobreescriptura
El punt exacte és `models_app/views.py:980-989` (`update_model_step2`) → `_validar_ruleset_assignable`
(`:568-622`). És **l'única porta** per on un model canvia de ruleset per UI, i **ja té el patró de l'avís
confirmable**: `409 {'tipus': 'ruleset_altre_client', 'codi': 'GRADING_CUSTOMER_MISMATCH'}` que es desbloqueja amb
`confirmar_altre_client` (`:610-620`). El frontend ja el sap tractar: `ModelWizard.jsx:389-395` té
`confirmaAltreClient()` amb `window.confirm`.

El fet dur que fa l'avís **necessari**: assignar un ruleset dispara **wipe-and-recreate** —
`model.grading_rules.all().delete()` és la primera línia de `materialize_model_grading_rules`
(`models_app/services.py:266`) i de `..._from_specs` (`:294`). **Les 61 regles `IMPORTED` desapareixen sense
preguntar** el dia que algú assigni un ruleset a aquell model. Avui **cap** de les tres portes de
`_validar_ruleset_assignable` mira l'origen de les residents.

### B6.5 · Estat dels overrides d'import i dels seus watchpoints
- `ModelGradingOverride` a `fhort`: **0 files**. La branca INTOCABLE (`:2679-2721`) mai s'ha executat en aquest
  schema, o els seus overrides s'han netejat.
- `Watchpoint` a `fhort`: **779 files**, **771 amb `dades` no-nul** (o sigui, estructurats i accionables, no text
  lliure). El canal existeix i s'usa.
- La llei BEACH (columnes fora del sistema de talles) també deixa Watchpoint + avís (`extraction_views.py:2431-2435`
  i el bloc de `columnes_descartades`, cap a `:2758`).

**Veredicte B6:** l'import ja té pre-flight complet, dos 409 de contenidor, un 422 d'integritat i el mecanisme de
«ruleset importat resident» **viu amb 61 files**. El forat és que el **wipe-and-recreate no distingeix l'origen**.

---

## B7 · Idioma al catàleg

### B7.1 · Cens de camps d'idioma a les entitats de catàleg

| Entitat | Schema | Camps | Fitxer:línia |
|---|---|---|---|
| `POMGlobal` | public+tenant | `nom_en`, `nom_ca`, `nom_es`, `descripcio_en`, `descripcio_ca` | `pom/models.py:33-38` |
| `GarmentTypeGlobal` | public+tenant | `nom_en`, `nom_ca`, `nom_es` | `pom/models.py:82-84` |
| `PatternPieceRole` | public+tenant | `nom_en`, `nom_ca`, `nom_es` | `pom/models.py:156-158` |
| `MeasurementLayer` | public+tenant | `nom_en`, `nom_ca`, `nom_es` | `pom/models.py:226-228` |
| `POMCategory` | tenant | `nom_en`, `nom_ca` (**sense `nom_es`**) | `pom/models.py:271-272` |
| `GarmentType` | tenant | `nom_client` + `nom_en`, `nom_ca`, `nom_es` | `pom/models.py:544,549-551` |
| `FitType` | public | `nom_en`, **`nom_cat`**, `nom_es`, `descripcio_en` | `pom/models.py:1236-1239` |
| `Target` | public | `nom_en`, **`nom_cat`**, `nom_es` | `pom/models.py:1283-1285` |
| `ConstructionType` | public | `nom_en`, **`nom_cat`**, `nom_es` | `pom/models.py:1315-1317` |
| `BodyMeasurementISO` | public | `nom_en`, **`nom_cat`**, `nom_es`, `htm_en` | `pom/models.py:1346-1352` |
| `POMMaster` | tenant | **`nom_client` (UN sol nom, sense idioma)** | `pom/models.py:303` |
| `GarmentTypeItem` | tenant | **`name` (UN sol nom)** | `tasks/models.py:332` |
| `GarmentGroup` | tenant | **`nom` (UN sol nom)** | `pom/models.py:522` |
| `SizeSystem` / `SizeDefinition` | tenant | **`nom` / `etiqueta` (un sol nom)** | `pom/models.py:437`, `:508` |

⚠️ **Dues convencions conviuen**: `nom_ca` (pom/tenant, sprints nous) i `nom_cat` (public, sprints S1).
`POMBrowser.jsx:20,45` ja hi fa de traductor defensiu (`t.nom_ca || t.nom_cat || …`).

### B7.2 · Volum real de traducció (staging)

| Entitat | files | amb `ca` | amb `es` | amb `descripcio_ca` |
|---|---|---|---|---|
| `POMGlobal` (fhort) | 274 | **269** | **0** | 125 |
| `POMGlobal` (public) | 125 | **125** | **0** | 125 |
| `POMCategory` (fhort) | 28 | 28 | — | — |
| `GarmentTypeGlobal` (public) | 59 | 59 | 59 | — |
| `GarmentType` (fhort) | 21 | 19 | 19 | — |
| `PatternPieceRole` (public) | 30 | 30 | 30 | — |
| `MeasurementLayer` (public) | 6 | 6 | 6 | — |
| `FitType` / `Target` / `ConstructionType` (public) | 10 / 13 / 4 | 10 / 13 / 4 | 10 / 13 / 4 | — |
| `BodyMeasurementISO` (public) | 0 | 0 | 0 | — |

👉 **`POMGlobal.nom_es` és 0 a tot arreu.** El castellà del catàleg de POMs **mai s'ha omplert**: la paritat de tres
idiomes al POM és una promesa d'esquema, no un fet de dades. **~394 `nom_ca` de POMGlobal** + 125 `descripcio_ca` són
el gruix del que quedaria òrfe.

### B7.3 · Seeds que sembren ×3 idiomes
`seed_measurement_layers.py:26,54` (tupla `(slug, nom_en, nom_ca, nom_es)`) · `seed_pattern_piece_roles.py` ·
`seed_baby_poms.py` (10 hits) · `extend_pom_catalog.py` (12) · `replace_pom_catalog.py` (7) ·
`translate_garment_families.py` (8) · `restructure_garment_types_v2.py` (4) · `consolidate_pom_catalog.py` (4) ·
`rename_targets_p0b.py` (3) · `reseed_tenant_fhort.py` (2, obsolet) · `load_losan_package.py` / `export_losan_package.py`.

### B7.4 · Serializers que emeten noms ×3
`pom/serializers.py`: `pom_global_nom` (`:36`) · `get_nom_en`/`get_nom_ca` de POMMaster (`:76,80`) ·
`get_categoria_nom` (`:91`) · `pom_nom_en`/`pom_nom_ca` de GarmentPOMMap (`:154-171,193`) · els mateixos a
ItemBaseMeasurement (`:374,378,389,486-519`) · `global_nom` de GarmentType (`:125`).
També `models_app/views.py` (12 hits), `pom/wizard_views.py:90-91` (`nom_global_ca`/`nom_global_en`),
`fitting/graded_spec_views.py` (5), `pom/s2_serializers.py` (5), `pom/s4_views.py`/`s6_views.py` (4 c/u).

### B7.5 · Consumidors al frontend (21 fitxers, 101 hits a `frontend/src`)
`utils/nomenclaturaPom.js:57-62` — **el resolutor únic**: `nomsDePom()` retorna `{canonic, local}` amb
`local = nom_traduit_model || nom_ca || nom_local || nom_client` i `canonic = nom_canonic_model || nom_en || local`.
👉 **Ja té el fallback correcte**: sense `nom_ca`, `local` cau a `nom_client` i, si diu el mateix que `canonic`,
`local` torna buit (`:61`) — la segona línia desapareix sola, sense pintar buits.

Altres: `POMBrowser.jsx:20,45,325` · `gradingAxes.js:60-63` (`nomLocal`) + `TARGETS`/`CONSTRUCTIONS`/`FITS`/
`GARMENT_GROUPS` **hardcoded ×3 idiomes** (`:13-57`) · `GarmentTypes.jsx` · `CascadeSelector.jsx` ·
`MeasurementBaseGrid.jsx` · `MeasureGrid.jsx` · `MeasuresEntryPanel.jsx` · `CheckMeasureEditor.jsx` ·
`ModelPomList.jsx` · `PieceIdentityList.jsx` · `SizeSystemDrawer.jsx` · `filterOptions.js` ·
`fittingGridAdapter.jsx` · `EditableTable.jsx` · `TallerPatro.jsx` · `GradingRuleSets.jsx`.
El **backoffice** (`frontend-backoffice/src`) **NO té cap consumidor** de `nom_ca`/`nom_cat`/`nom_es`.

### B7.6 · Impressió / fitxa
`TechSheetEditor.jsx` imprimeix **dues línies per fila**: `nom_en` a dalt i `nom_ca` com a subtítol en cursiva.
- Constants de tipografia dedicades: `T_FONT_CA` (`:679`), `T_ROW_H = T_FONT + T_FONT_CA + …` (`:687`).
- Primitiu de dibuix: `if (row.nom_ca) prims.push({... text: row.nom_ca, italic: true ...})` (`:779`).
- Quatre taules: `:4849`, `:4921`, `:4983` (`sub: bm.nom_ca`) i `:5056` (`sub: row.nom_local`).
- El bateig ja mana on s'ha convergit: `:6700` — `bm.nom_traduit_model || bm.nom_ca || bm.nom_client`.

**L'idioma de la FITXA ja és del DOCUMENT, no del catàleg** — acta a `TechSheetEditor.jsx:73-78` i implementació
B7 a `:2491-2518`, `:3309-3311`, `:3513-3515`. El comentari `:2517-2518` diu literalment que **els noms de catàleg
«tenen nom a cada idioma i s'han de dir en el de la fitxa»** → aquest és el node que canvia de sentit amb EN únic.

### B7.7 · Què es trencaria i què és purament additiu

**ES TRENCARIA (o canvia de veredicte):**
1. `pom/tests.py:197-205` — `test_els_rols_sembrats_son_de_sistema_i_amb_els_tres_idiomes`:
   `assertTrue(rol.nom_en and rol.nom_ca and rol.nom_es)`.
2. `pom/tests.py:250-257` — `test_les_capes_sembrades_son_de_sistema_i_amb_els_tres_idiomes`: idèntic per a
   `MeasurementLayer`.
3. `patterns/tests.py:4936` — contracte de serializer: assereix que hi són `'nom_en','nom_ca','nom_es'`.
4. `models_app/test_base_stages_no_regressio.py:79` — **contracte de payload congelat**: la llista de claus de fila
   inclou `'nom_ca'` i el test diu «Ni una clau més ni una menys» (`:68`). Treure el camp del payload **el trenca**;
   deixar-lo buit **no**.
5. `TechSheetEditor.jsx:687` — l'alçada de fila (`T_ROW_H`) **reserva** l'espai del subtítol encara que sigui buit.
   Les taules impreses quedarien amb un carrer mort de ~7 px per fila.

**ÉS PURAMENT ADDITIU (no es trenca res):**
- `nomenclaturaPom.js:57-62` — el fallback ja hi és.
- `POMBrowser.jsx:20` — cadena de fallback ja hi és.
- Els seeds: `update_or_create` amb `defaults` que ja porten els tres → escriure'n un de sol és una passada més.
- La sembra `bootstrap_tenant`: `_concrete()` copia camps, no els interpreta.
- `gradingAxes.js:13-57` — TARGETS/CONSTRUCTIONS/FITS/GARMENT_GROUPS són **constants de frontend**, no catàleg de BD.

### B7.8 · El precedent que ja existeix al repo
`fhort.i18n_content` (`settings.py:74`) implementa **exactament** el patró demanat:
- `Translation` (`i18n_content/models.py:37-57`) — sidecar genèric per `(content_type, object_id, field, language)`,
  amb l'acta literal: «**L'EN NO es desa aquí (viu a la columna original)**» (`:41-42`).
- `TranslatableMixin.translated(field, language)` (`:75-81`) — retorna la traducció o **cau al valor canònic EN**.
- Consumidors vius: `commerce.Product` (`commerce/models.py:47,77`) i `commerce.PaymentTerms` (`:397,402`), amb
  `TranslationsSerializerMixin` (`commerce/serializers.py:9`) i el PDF ja passant l'idioma (`commerce/pdf_service.py:463`).

**Veredicte B7:** l'anglès únic al catàleg **no és estructural**: el mecanisme substitut ja viu al repo i el
resolutor de frontend ja té els fallbacks. El radi real són **4 tests**, **1 contracte de payload congelat**,
**1 constant de tipografia** i **~394 `nom_ca` de POMGlobal + 125 descripcions** que quedarien òrfenes.
**El bateig per model NO s'hi toca** (`nom_canonic_model`/`nom_traduit_model`, `models_app/models.py:681`, i
`MeasureGrid.jsx:209-214`), i **l'i18n d'interfície tampoc** (`frontend/src/i18n/{ca,en,es}.json`, gate del CLAUDE.md).

---

## B8 · Dades

### B8.1 · Staging (`ftt_staging` @5433, 02/08/2026)

| Taula | `public` | `fhort` | `los` |
|---|---|---|---|
| `pom_pomglobal` | 125 | **274** | 0 |
| `pom_pommaster` | 0 | **370** | 0 |
| `pom_customerpomalias` | 0 | **336** | 0 |
| `pom_garmentpommap` | 0 | **1.748** | 0 |
| `pom_itembaseset` | 0 | **1** | 0 |
| `pom_itembasemeasurement` | 0 | **37** | 0 |
| `pom_gradingruleset` | 14 | **46** | 0 |
| `pom_gradingrule` | 0 | **1.174** | 0 |
| `pom_rulesetscopenode` | 0 | **11** | 0 |
| `pom_sizingprofile` | 0 | **46** | 0 |
| `pom_garmenttype` | 0 | **21** | 1 |
| `pom_garmenttypeglobal` | 59 | 59 | 0 |
| `tasks_garmenttypeitem` | — (taula inexistent a `public`) | **62** | 1 |
| `pom_pomcategory` | 15 | 28 | 0 |
| `pom_measurementlayer` | 6 | 6 | 6 |
| `pom_patternpiecerole` | 30 | 30 | 30 |
| `pom_clientmesuraperfil` | — | **17** | 0 |
| `pom_pomestadisticaglobal` / `tenant` | 0 | 0 | 0 |

### B8.2 · PROD (dump `20260801_023001`, llegit amb `pg_restore -a`)

| Taula | `public` | `fhort` | `los` |
|---|---|---|---|
| `pom_pomglobal` | 125 | **290** | **261** |
| `pom_pommaster` | 0 | **520** | **277** |
| `pom_customerpomalias` | 0 | **336** | **212** |
| `pom_garmentpommap` | 0 | **1.881** | **1.748** |
| `pom_itembaseset` | 0 | 0 | **1** |
| `pom_itembasemeasurement` | 0 | 0 | **37** |
| `pom_gradingruleset` | 14 | **51** | **20** |
| `pom_gradingrule` | 0 | **1.447** | **460** |
| `pom_rulesetscopenode` | 0 | **14** | **10** |
| `pom_sizingprofile` | 0 | **52** | **25** |
| `pom_garmenttype` | 0 | 21 | 21 |
| `pom_garmenttypeglobal` | 59 | 59 | 0 |
| `tasks_garmenttypeitem` | 0 | **71** | **64** |
| `pom_pomcategory` | 15 | 28 | 0 |
| `pom_measurementlayer` | **0** | **0** | **0** |
| `pom_patternpiecerole` | **0** | **0** | **0** |

🚩 **Dues divergències staging↔PROD que qualsevol onada ha de tenir a la vista:**
- **`MeasurementLayer` i `PatternPieceRole` són 0 a PROD als tres schemas.** Els catàlegs de C1 i del motor de
  patrons **no hi han arribat** (ni les taules tenen dades, encara que la migració hi sigui).
- **El contingut viu de POMs de staging-`fhort` és, a PROD, el de `los`** (1.748 `garmentpommap` idèntics; 37
  `itembasemeasurement` idèntics; 1 `itembaseset`). PROD-`fhort` és més gran (520 POMMaster, 1.881 maps) i té
  **0 ItemBaseSet/ItemBaseMeasurement**. Staging **no és una còpia recent de PROD-`fhort`**.

### B8.3 · Items amb POMs propis vs heretables del seu Type (`fhort`)

**62 items en 21 GarmentType.** Els Type amb items:

| Type | items | items **amb** POMs propis | POMs distints del Type (unió) |
|---|---|---|---|
| NEWBORN | 9 | **8** | **82** |
| TAILORED_PANTS | 6 | 6 | 57 |
| UNDERWEAR | 6 | **3** | 46 |
| BUTTONED_TOPS | 4 | 4 | 47 |
| JERSEY_TOPS | 4 | 4 | 36 |
| DRESSES | 4 | 4 | 42 |
| HEAVY_OUTERWEAR | 4 | 4 | 46 |
| ADULT_JUMPSUITS | 3 | 3 | 46 |
| BRA_SHAPEWEAR | 3 | 3 | 6 |
| SWIMWEAR | 3 | 3 | 29 |
| STRUCTURED_JACKETS | 3 | 3 | 44 |
| **ACCESSORIES** | 3 | **0** | **0** |
| KNIT_SWEATERS / KNIT_CARDIGANS / SWEATSHIRTS / LEGGINGS / SKIRTS | 2 c/u | 2 c/u | 33/32/39/26/16 |
| T_SHIRT · DRESS · BABY_ONEPIECES · BABY_SEPARATES | **0** | 0 | 0 |

**Resum:** **58 dels 62 items (93,5 %) ja tenen POMs propis**; **4 no en tenen cap** (3 d'ACCESSORIES + 1 d'UNDERWEAR
+ 1 de NEWBORN — 5 comptant l'aritmètica per Type). **4 GarmentType no tenen cap item** (T_SHIRT, DRESS,
BABY_ONEPIECES, BABY_SEPARATES) i **1 Type té items però cap POM** (ACCESSORIES).
👉 **La cascada Type-first beneficiaria avui exactament 4 items** (els que no tenen mapa però el seu Type sí) i
**no serviria de res** als 3 d'ACCESSORIES (el seu Type tampoc no en té).
👉 Els Type ja acumulen entre **6 i 82 POMs** per unió d'items — el «un Type pot acabar tenint 100 POMs» del
context ja és pràcticament el cas a NEWBORN (82).

**204 dels 370 POMMaster (55 %) no són a cap `GarmentPOMMap`**: catàleg encunyat que cap plantilla reclama.

### B8.4 · Traducció que quedaria òrfena
Vegeu §B7.2. En síntesi: **394 `nom_ca` de POMGlobal** (269 fhort + 125 public), **250 `descripcio_ca`**,
**0 `nom_es` de POMGlobal** (mai omplert), 28 `nom_ca` de POMCategory, 19+59 `nom_ca`/`nom_es` de GarmentType(Global),
30 de PatternPieceRole, 6 de MeasurementLayer, 27 dels tres catàlegs d'eixos (`nom_cat`).

---

## B9 · Nodes que inverteixen la llei

Nodes que **afirmen com a correcte** allò que les decisions del context volen legitimar (o al revés), amb la seva
acta quan en tenen.

### B9.1 · Contra el CATÀLEG TYPE-FIRST

| Node | Fitxer:línia | Acta escrita al codi |
|---|---|---|
| `suggested_poms_view` sense fallback | `pom/wizard_views.py:66` | **«No GarmentPOMMap for the item → empty + warning (NO 'all active POMs' fallback: it masked gaps)»**. És literalment la llei contrària: *el buit és la resposta correcta perquè un fallback amagaria forats*. |
| Guard `pom_ids` fora del mapa | `models_app/views.py:1125-1126, 1266-1267` | «Els ids que no són del mapa de l'item no es sembren en silenci: es reporten». |
| Test que consagra el guard | `models_app/tests_sembra_grading.py:220-225` (`test_pom_ids_desconegut_es_reporta`) | comentari inline: «aliè = existeix, però **no és al GarmentPOMMap de l'item**». |
| LLEI 6 · ampliació del superset | `models_app/views.py:3624-3625` i `:3857` | «l'ampliació del superset … només entra AMB CONFIRMACIÓ, mai en silenci» + test `test_l_ampliacio_del_superset_va_en_seccio_propia_i_només_amb_confirm` (`tests_sembra_grading.py:927`). |
| Migració família→item completada | `pom/models.py:574-576` + `pom/migrations/0016_…:24` | «la pertinença POM viu **únicament** a garment_type_item. El FK legacy garment_type i el seu unique_together s'han eliminat». |
| GTI obligatori al wizard | `ModelWizard.jsx:398-400` | «B4b — GTI obligatori: és la baula del motor de temps». |

### B9.2 · Contra el RULESET LLIURE

| Node | Fitxer:línia | Acta |
|---|---|---|
| Constraint parcial d'identitat | `pom/models.py:1044-1053` | «CONTENIDOR ÚNIC (llei 2026-07-16): **un sol contenidor de client** per combinació … **Guarda dura** de la unicitat, no només a l'aplicació». |
| Bloqueig dur per `size_system` | `models_app/views.py:598-608` | «Graduar amb un run que no és el del model **no vol dir res**». |
| Matching estricte del wizard | `gradingAxes.js:196-200` | «**cap eix NULL fa de comodí** — un ruleset s'exclou si no declara explícitament target/construction/fit/grup/system … cap arrossegament implícit ni fals positiu». |
| Paritat backend↔frontend | `pom/grading_utils.py:665-668` i `:642-644` | «La semàntica de MATCHING d'eixos és **IDÈNTICA** a matchingRuleSetsStrict del frontend». Alliberar una banda i no l'altra trenca una paritat declarada per escrit. |
| Compatibilitat família↔target | `pom/views.py:124-127` | «La compatibilitat target↔família viu a SizingProfile». |
| `test_p7_target_fk.py:61` | `pom/test_p7_target_fk.py:61` | `test_ruleset_amb_un_target_el_conserva_i_es_troba` — el target **és criteri de cerca**. |

### B9.3 · A FAVOR de les decisions (nodes que ja les anticipen)

| Node | Fitxer:línia | Per què compta |
|---|---|---|
| Autoselecció retirada | `ModelWizard.jsx:337-344` | «el model neix NET i la graduació s'incorpora pel gest … amb acceptació explícita». **Ja és la decisió del punt 2.** |
| `SizingProfile.grading_rule_set` nullable | `pom/models.py:1382-1390` | «La graduació és un SUGGERIMENT que el perfil pot portar, **no la seva raó de ser**». |
| LLEI DELS WIZARDS ELIMINATIUS (C5) | `gradingAxes.js:167-180` | «seleccionar **ATENUA I REORDENA** … MAI amaga … un eix no seleccionat no descarta ningú — el filtre és opcional, no un gate». **És exactament «etiquetes informatives».** |
| `orderWithSuggestedFirst` | `gradingAxes.js:232-239` | «Suggerir ≠ arrossegar — cap crida d'aquesta funció assigna res». |
| Mode ANOTAT de GarmentType | `pom/views.py:134-140` | «el backend **INFORMA i no exclou**; el frontend atenua». Ja hi ha el precedent d'un eix informatiu. |
| Intersecció al motor | `pom/services.py:233-234` + `:386-388` | el motor itera les mesures **del model**; «regla absent → cel·la absent». Un ruleset de 80 regles no afegeix ni una cel·la. |
| `CustomerPOMAlias` sense POM | `pom/models.py:395-399` | «un àlies **SENSE pom** és vocabulari del client encara PENDENT DE MAPAR. És un **estat legítim del domini**». Precedent de «pendent» com a estat, no com a error. |
| D-1 «el tenant PROPOSA» | `pom/models.py:111-121` i `:192-199` | «crear el seu rol … serveix per treballar des del primer dia; convertir-lo en canònic és una **decisió humana**, amb el seu gate, i **mai un efecte secundari d'una importació**». **És literalment el punt 1 del context, ja escrit per a `PatternPieceRole` i `MeasurementLayer` — però NO per a `POMMaster`.** |

### B9.4 · Contra l'ANGLÈS ÚNIC
- `pom/tests.py:197-205` i `:250-257` — els dos tests dels «tres idiomes» (§B7.7).
- `patterns/tests.py:4936` — contracte de serializer amb els tres.
- `models_app/test_base_stages_no_regressio.py:67-83` — «Ni una clau més ni una menys», amb `nom_ca` a la llista.
- `pom/models.py:124-125` (PatternPieceRole) i `:205-206` (MeasurementLayer) — acta idèntica a totes dues:
  «els noms … **van en tres idiomes des del primer dia, com `POMGlobal`**, perquè afegir-los després vol dir
  repassar files a mà».
- `TechSheetEditor.jsx:2517-2518` — «CATÀLEG: tenen nom a cada idioma i **s'han de dir en el de la fitxa**».

---

## B10 · Onades (mesura de l'ona, no pla d'implementació)

**Total de nodes censats: 71.** Agrupació per naturalesa i dependència.

| Onada | Nodes | Contingut | Depèn de |
|---|---|---|---|
| **O0 · Higiene de la porta** | **4** | `POMMasterViewSet` sense gate (`pom/views.py:50`) · `create_tenant_pom_view` sense CONFIGURE (`wizard_views.py:415`) · diccionari «sense gate — fase beta» (`dictionary_views.py:145`) · escriptor mort de `POMGlobal` (`s9_views.py:179`) | — (independent de tot) |
| **O1 · Resolució Type-first (lectura)** | **6** | Els 6 punts de lookup de §B2.2 | O0 (perquè servir més POMs sense porta amplifica l'encunyament) |
| **O1b · Esquema Type-first** *(només si Lectura B)* | **3** | unicitat de `GarmentPOMMap` amb item NULL · `__str__` · on viu el valor base d'un POM del Type | O1 |
| **O2 · Cens i sanejament d'encunyament** | **~7 famílies de dades** | 12 codis duplicats · 15 noms duplicats · 18 parelles base+qualificador · 30 POMs amb sufix · 204 POMs sense mapa · 228 `pendent_revisio` · 96 tenant-only | O0. **Bloquejada de facto per C4/C4-ins**: les 18 parelles són el que la capa/instància han d'absorbir, i les comportes CHECK encara hi són (`pom/models.py:627,633,928,934`) |
| **O3 · Alliberament del ruleset · aplicació** | **8** | Nodes 2,3,5,6,7,8,9 de §B5.2 + l'`useEffect` de neteja de `ModelWizard.jsx:346-357` | — (independent d'O1) |
| **O3b · Alliberament del ruleset · BD** | **1** | `uniq_client_container_identity` (migració) | O3 (l'aplicació ha de deixar de dependre'n abans) |
| **O4 · Tests del ruleset** | **~19** | 7 backend nominats (§B5.4) + 5 frontend de `classifyRuleSets` + **2 forats sense test** (`matchingRuleSetsStrict`, `availableFitsStrict`) + 5 de `test_p7_target_fk` | O3+O3b |
| **O5 · Import: ruleset importat + avís** | **3** | marca del ruleset importat (el mecanisme **ja hi és**: `ModelGradingRule.origen='IMPORTED'`, 61 files) · avís de sobreescriptura a `_validar_ruleset_assignable` (`models_app/views.py:568`) · el wipe-and-recreate cec (`models_app/services.py:266,294`) | O3 (l'avís parla del contenidor) |
| **O6 · EN únic · backend** | **14** | Els 14 models de §B7.1 + els seeds de §B7.3 + els serializers de §B7.4 | — (independent d'O1 i O3) |
| **O7 · EN únic · frontend + fitxa** | **~21** | Els 21 fitxers de §B7.5 + `T_ROW_H`/`T_FONT_CA` (`TechSheetEditor.jsx:679,687`) + les 4 taules impreses | O6 |
| **O8 · Tests de l'idioma** | **4** | `pom/tests.py:204,257` · `patterns/tests.py:4936` · `test_base_stages_no_regressio.py:79` | O6+O7 |

**Dependències entre onades:** `O0 → O1 → (O1b)` · `O0 → O2` (i O2 espera C4/C4-ins) · `O3 → O3b → O4` ·
`O3 → O5` · `O6 → O7 → O8`. **Les tres columnes (Type-first · Ruleset · Idioma) són independents entre si**:
cap node apareix a dues columnes alhora. L'únic punt de contacte és `SizingProfile`, que toca O1 (via
`GarmentTypeViewSet.get_queryset`) i O3 (via els cinc eixos) — **1 node compartit de 71**.

---

## REGISTRE DE NODES

Tipus: `M`=model/esquema · `C`=constraint BD · `V`=vista/endpoint · `S`=servei/lògica · `F`=frontend · `T`=test ·
`K`=comanda. Risc: 🔴 alt · 🟡 mitjà · 🟢 baix.

| Fitxer:línia | Tipus | Efecte del canvi | Risc | Onada |
|---|---|---|---|---|
| `pom/views.py:50-59` | V | POST `/api/v1/poms/` sense gate → porta silenciosa d'encunyament | 🔴 | O0 |
| `pom/wizard_views.py:415-455` | V | creació deliberada però sense CONFIGURE; guard només per codi exacte (`:436`) | 🟡 | O0 |
| `pom/dictionary_views.py:137-154` | V | crea POMMaster des del diccionari; 167 files ja encunyades així | 🟡 | O0 |
| `pom/s9_views.py:179-193` | V | escriptor de POMGlobal **mort** (camps inexistents, `except: pass`) | 🟢 | O0 |
| `models_app/extraction_views.py:1893-1917` | V | crea POMMaster amb `codi_fitxa` a cegues (count==0) | 🟡 | O0/O2 |
| `models_app/extraction_views.py:1869-1881` | V | crea POMMaster amb codi i nom **donats pel tècnic** (porta humana) | 🟢 | — |
| `pom/services.py:624-640` | S | crea/actualitza àlies com a efecte lateral de l'import | 🟡 | O0 |
| `pom/models.py:573-641` | M | l'única taula de pertinença POM; àncora `garment_type_item` nullable | 🔴 | O1/O1b |
| `pom/models.py:623` | C | unicitat `(item, pom, capa, instancia)` — no cobreix item NULL | 🔴 | O1b |
| `pom/models.py:627-637` | C | comportes CHECK `capa='exterior'` i `instancia=''` (C4/C4-ins pendents) | 🔴 | O2 |
| `models_app/views.py:1119-1121` | V | sembra item→model: el lookup que decideix què s'escriu | 🔴 | O1 |
| `models_app/views.py:1038-1040` | V | POMs suggerits per model | 🟢 | O1 |
| `pom/wizard_views.py:78-81` | V | POMs suggerits per item; acta anti-fallback (`:66`) | 🟡 | O1 |
| `pom/views.py:319-348` | V | CRUD del mapa (mode ASSIGN); filtre `?garment_type=` retirat | 🟡 | O1 |
| `models_app/views.py:3745-3746` | V | superset de l'item al diff de promoció (LLEI 6) | 🟡 | O1 |
| `models_app/views.py:1124-1126,1266` | V | guard `pom_ids` fora del mapa | 🟡 | O1 |
| `models_app/views.py:3865-3871` | V | escriptura del mapa dins del confirm (porta humana + CONFIGURE) | 🟢 | — |
| `tasks/models.py:329-330` | M | `GarmentTypeItem.garment_type` — el JOIN que fa possible la cascada | 🟢 | O1 |
| `pom/models.py:1201-1202` | M | `ClientMesuraPerfil`: **l'única relació GarmentType↔POM viva (17 files)** | 🟢 | — |
| `pom/models.py:1044-1053` | C | `uniq_client_container_identity` — la cotilla dura | 🔴 | O3b |
| `pom/grading_utils.py:698-708` | S | NIVELL 1: identitat dura per `(customer,system,item,fit)` | 🔴 | O3 |
| `pom/grading_utils.py:710-735` | S | NIVELL 2: 3 `return none` per eix absent + `_scope_matches` | 🔴 | O3 |
| `pom/grading_utils.py:619-638` | S | `cerca_contenidor_client` **deprecada**; 1 caller viu | 🟡 | O3 |
| `pom/size_map_views.py:745-759` | V | pre-check 409 `container_exists` (l'únic caller de la deprecada) | 🟡 | O3 |
| `models_app/views.py:598-608` | S | bloqueig dur `size_system` divergent | 🔴 | O3 |
| `models_app/views.py:610-620` | S | 409 confirmable per client divergent (**patró de l'avís d'O5**) | 🟢 | O5 |
| `gradingAxes.js:201-212` | F | `matchingRuleSetsStrict` — **sense cap test** | 🔴 | O3/O4 |
| `gradingAxes.js:216-230` | F | `availableFitsStrict` — **sense cap test** | 🟡 | O3/O4 |
| `gradingAxes.js:156-165` | F | `matchingRuleSets` (lenient) | 🟡 | O3 |
| `gradingAxes.js:181-194` | F | `classifyRuleSets` — **ja és la forma «informativa»** | 🟢 | — |
| `ModelWizard.jsx:331-335` | F | `strictMatches` (consumidor únic del matcher estricte) | 🟡 | O3 |
| `ModelWizard.jsx:346-357` | F | neteja defensiva del ruleset hidratat que deixa de casar | 🟡 | O3 |
| `ModelWizard.jsx:337-344` | F | autoselecció **ja retirada** (acta 31/07) | 🟢 | — |
| `pom/models.py:1382-1393` | M | `SizingProfile.grading_rule_set` nullable (acta C3) | 🟢 | — |
| `pom/views.py:124-155` | V | famílies filtrades per SizingProfile (`?target=` exclou · `?compat_*` anota) | 🟡 | O1+O3 |
| `pom/management/commands/crea_sizing_profiles.py` | K | **única via de creació de SizingProfile** (no hi ha endpoint) | 🟡 | O3 |
| `models_app/services.py:256-283` | S | wipe-and-recreate: copia **totes** les regles, sense intersecció | 🔴 | O5 |
| `models_app/services.py:286-309` | S | idem des d'specs; el camí de l'import | 🔴 | O5 |
| `pom/services.py:233-234, 386-388` | S | **intersecció real al motor**: regla absent → cel·la absent | 🟢 | — |
| `pom/services.py:699-708` | S | residents manen sobre el ruleset extern | 🟢 | O5 |
| `models_app/models.py:1015-1023` | M | `ModelGradingRule.origen` **ja té `IMPORTED`** (61 files) | 🟢 | O5 |
| `models_app/extraction_views.py:2466-2495` | V | pre-flight: 409 ambigu + 409 absent | 🟡 | O5 |
| `models_app/extraction_views.py:2650-2665` | V | crea contenidor AMPLI (item NULL) amb `container_choice='create'` | 🟡 | O3/O5 |
| `models_app/extraction_views.py:2679-2721` | V | llei M3 INTOCABLE → overrides + Watchpoint (**0 overrides a fhort**) | 🟡 | O5 |
| `tasks/management/commands/bootstrap_tenant.py:150` | K | clau natural del ruleset = **`nom`** (ja lliure) | 🟢 | — |
| `tasks/management/commands/bootstrap_tenant.py:148` | K | clau natural POMMaster = `codi_client` (**12 duplicats**) | 🔴 | O2 |
| `tasks/management/commands/bootstrap_tenant.py:126-176` | K | `_spec()` **no copia** ItemBaseSet/ItemBaseMeasurement/ScopeNode/Layer/Role | 🟡 | O1/O2 |
| `pom/management/commands/reseed_tenant_fhort.py:82-88` | K | obsolet amb guard dur (eix `garment_type` de la 0016) | 🟢 | — |
| `pom/models.py:33-38` | M | `POMGlobal` ×3 idiomes; **`nom_es`=0 a tot arreu** | 🟡 | O6 |
| `pom/models.py:1236-1352` | M | `nom_cat` (convenció divergent) a FitType/Target/Construction/ISO | 🟡 | O6 |
| `i18n_content/models.py:37-81` | M | **el precedent viu** d'EN canònic + sidecar | 🟢 | O6 |
| `commerce/models.py:47,397` | M | els dos únics consumidors actuals de `TranslatableMixin` | 🟢 | O6 |
| `utils/nomenclaturaPom.js:57-62` | F | resolutor únic; **el fallback ja hi és** | 🟢 | O7 |
| `TechSheetEditor.jsx:679,687,779` | F | tipografia i alçada de fila **reserven** el subtítol `nom_ca` | 🟡 | O7 |
| `TechSheetEditor.jsx:4849,4921,4983,5056` | F | les 4 taules impreses amb `sub: nom_ca`/`nom_local` | 🟡 | O7 |
| `TechSheetEditor.jsx:73-78, 2491-2518` | F | l'idioma **ja és del DOCUMENT**; el catàleg s'hi adapta | 🟡 | O7 |
| `models_app/models.py:681` + `MeasureGrid.jsx:209-214` | M/F | bateig per model — **NO afectat**, sobirà | 🟢 | — |
| `pom/tests.py:197-205` | T | exigeix els 3 idiomes a `PatternPieceRole` | 🟡 | O8 |
| `pom/tests.py:250-257` | T | exigeix els 3 idiomes a `MeasurementLayer` | 🟡 | O8 |
| `patterns/tests.py:4936` | T | contracte de serializer amb `nom_ca`/`nom_es` | 🟡 | O8 |
| `models_app/test_base_stages_no_regressio.py:67-83` | T | contracte de payload congelat («ni una clau més ni una menys») amb `nom_ca` | 🔴 | O8 |
| `models_app/tests_sembra_grading.py:275,312` | T | consagren el bloqueig dur per `size_system` | 🔴 | O4 |
| `models_app/tests_sembra_grading.py:220-225` | T | consagra que un POM fora del mapa de l'item és «desconegut» | 🟡 | O4/O1 |
| `models_app/tests_sembra_grading.py:927` | T | l'ampliació del superset només amb confirm | 🟡 | O1 |
| `pom/test_p7_target_fk.py:48-92` | T | 5 tests: el target **és criteri de cerca** | 🟡 | O4 |
| `pom/test_p4_scope_proposals.py:76-156` | T | 7 tests d'aplicabilitat multi-node | 🟢 | O4 |
| `models_app/test_d1_proposta_promocio.py:144` | T | depèn del contenidor resolt | 🟡 | O4 |
| `gradingAxes.test.js:62-92` | T | 5 tests de `classifyRuleSets` (runner natiu de Node) | 🟡 | O4 |
| `gradingAxes.test.js:20-56` | T | 6 tests d'`orderWithSuggestedFirst` — **no cauen** | 🟢 | — |

---

## LÍMITS DECLARATS

1. **No he executat cap test.** Els «tests que cauen» de §B5.4 i §B9.4 són **lectura del que asserteixen**, no
   execució. La regla del verd (CLAUDE.md) prohibeix córrer suites que puguin tocar estat, i la memòria del projecte
   registra que **la BD de test no es pot construir des de zero** en aquest entorn.
2. **PROD només per dump.** Els recomptes de §B8.2 surten de `pg_restore -a` + comptatge de línies del bloc `COPY`.
   És fiable per a files sense salts de línia dins de camps de text; per a taules amb text lliure multi-línia
   (`notes`, `descripcio`) el nombre podria ser **lleugerament alt**. Les taules de §B8.2 són majoritàriament de
   claus i números; `pom_pommaster` i `pom_gradingruleset` porten `notes`/`nom` i són les úniques amb risc real.
3. **`GarmentPOMMap` amb `capa`/`instancia` diferents del default no existeix avui** (comportes CHECK actives). Tot
   el que digui aquesta diagnosi sobre la cascada Type-first assumeix una sola capa i una sola instància; **C4 i
   C4-ins la poden canviar sota els peus**.
4. **No he auditat el frontend-backoffice** més enllà de confirmar que **no consumeix** cap camp `nom_ca`/`nom_cat`/
   `nom_es`. Si hi ha superfícies de catàleg allà, no hi són per aquests camps.
5. **No he obert `docs/diagnosis/arxiu/`** (prohibit com a font de veritat pel CLAUDE.md). Les diagnosis vigents de
   l'arrel que toquen aquest radi (`DIAGNOSI_CATALEG_POM_STAGING_PROD.md`, `DIAGNOSI_INSTANCIES_POM.md`,
   `MAPA_TOC_INSTANCIA.md`) **no s'han fet servir com a font**: tot el que hi ha aquí està reverificat contra el codi
   i la BD d'avui.
6. **`suggested_poms_view` existeix DUPLICAT** amb el mateix nom a `models_app/views.py:1022` (per model) i
   `pom/wizard_views.py:59` (per item). Són funcions diferents amb rutes diferents
   (`models/<id>/poms-suggerits/` a `models_app/urls.py:209` · `poms/suggerits/` a `pom/urls.py:44`). Ho anoto per
   evitar confusió de lectura, no com a problema.
7. **La cascada «Lectura A vs Lectura B»** del §B2 és una **bifurcació de disseny que no he resolt**: el brief diu
   «si es treballa sobre un item i falta un POM, el sistema el busca al catàleg del Type», que és compatible amb les
   dues. La resposta a «cal esquema?» depèn d'aquesta decisió humana.

---

## LES DUES PREGUNTES DIRECTES

### (a) El canvi Type-first, toca el motor de mesures? — **NO**

**Prova, en tres baules:**

1. **El motor no coneix ni `GarmentPOMMap` ni `GarmentType` ni `GarmentTypeItem`.** `pom/services.py` (el fitxer de
   `generate_graded_specs`, `:166`) **no importa ni menciona cap dels tres**. Les seves entrades són:
   `SizeFitting` (`:182-188`), `escala_del_model` (`:206`), `_load_grading_rules(model)` (`:209`),
   `_load_model_overrides(model.pk)` (`:211`) i `_load_base_measurements(model.pk)` (`:215`).
2. **La font de POMs del motor és `BaseMeasurement` del MODEL, no la plantilla de l'item.** El bucle és
   `for pom_id, base_val in base_measurements.items()` (`pom/services.py:233`), i el preview fa el mateix
   (`:366`). Un POM que no ha arribat a `BaseMeasurement` del model **no existeix per al motor**.
3. **El punt de contacte és anterior i està aïllat: `materialize_poms_view`** (`models_app/views.py:1066-1268`), que
   és qui converteix la pertinença de l'item en `BaseMeasurement`. Canviar d'on surt aquella pertinença (item → item
   ∪ Type) canvia **quantes files** entren a `BaseMeasurement`; **no canvia ni una línia** de com el motor les
   gradua. Corol·lari: **la zona intocable del CLAUDE.md («no tocar POMs / grading engine / motor de patrons»)
   NO cal travessar-la** per fer Type-first.

*Matís honest:* el motor **sí** es veuria afectat **indirectament** si el Type aportés POMs amb `capa`/`instancia`
noves — però això no és el canvi Type-first, és C4/C4-ins, que ja té les seves comportes
(`pom/models.py:627-637`) i el seu propi radi.

### (b) Es pot alliberar el ruleset sense tocar el catàleg, o van junts? — **ES POT ALLIBERAR SOL**

**Prova, en quatre baules:**

1. **Cap dels 9 nodes de la cotilla toca el catàleg de POMs.** Repassats un a un a §B5.2: els seus operands són
   `customer`, `size_system`, `targets`, `construction`, `fit_type`, `garment_group`, `garment_type_item` i
   `RuleSetScopeNode`. **Cap** llegeix `POMMaster`, `POMGlobal`, `CustomerPOMAlias` ni `GarmentPOMMap`.
2. **El denominador comú ja és el POM, i la unicitat que ho sosté ja hi és.** `GradingRule` té
   `unique_together = ('rule_set', 'pom')` (`pom/models.py:1161`) i **cap eix**: sense `capa` i sense `instancia`,
   amb acta explícita («una regla és una llei d'INCREMENTS, no un valor», `pom/models.py:1152-1160`). La regla ja
   parla només de POMs.
3. **La intersecció que fa inofensiu un ruleset de 80 regles ja funciona** (§B9.3, `pom/services.py:233,386-388`).
   ⚠️ **Amb una excepció verificada:** `materialize_model_grading_rules` **no** intersecta — copia les 80 regles com
   a 80 `ModelGradingRule` (`models_app/services.py:266-282`). Això **no altera cap valor graduat** (el motor les
   ignora si el POM no té base), però sí el volum de dades residents. **És el node d'O5, no un blocador d'O3.**
4. **La identitat lliure ja és la que la federació assumeix**: la clau natural de `GradingRuleSet` a
   `bootstrap_tenant` **és `('nom',)`** (`tasks/management/commands/bootstrap_tenant.py:150`), no els eixos.

**Però hi ha UN node compartit i cal dir-lo:** `SizingProfile`. Els seus cinc eixos són alhora
(i) la identitat de sembra del ruleset-suggeriment (`bootstrap_tenant.py:170-173`) i (ii) **el filtre que decideix
quines famílies de catàleg es veuen al wizard** (`pom/views.py:138-143`). Alliberar el ruleset **no** obliga a
tocar-lo — el mode ANOTAT ja existeix (`pom/views.py:144-155`) — però **qualsevol onada que el toqui està tocant
les dues columnes alhora**. És **1 node de 71**.

**Conclusió:** les tres columnes (Type-first · Ruleset lliure · Anglès únic) es poden moure **per separat i en
qualsevol ordre**. L'única precedència real interna és `O3 → O3b → O4` (l'aplicació abans que la constraint, i els
tests al final) i `O6 → O7 → O8`.

---

*Fi de la diagnosi. Cap fitxer del repo modificat, cap escriptura a BD, cap commit.*
