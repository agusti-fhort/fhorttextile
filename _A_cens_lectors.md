# A3 + A5 · Cens de lectors/escriptors de `POMMaster` i format d'instància

> **Mode:** lectura pura. Cap escriptura de dades, cap migració, cap `--apply`, cap restauració de dump.
> **Data:** 2026-08-07 · **Repo:** `/var/www/ftt-staging` · rama `HEAD` (neta).
> Tots els camins són **absoluts**. Cap recomanació d'implementació: només terreny.

---

## 0 · Terreny comú verificat abans de res (fets de BD, lectura pura)

Comanda: `backend/venv/bin/python manage.py shell -c "…"` sobre `schema_context` + `to_regclass`.

| schema | `pom_pommaster` | `pom_pomglobal` | `pom_customerpomalias` | `pom_measurementinstance` | `pom_measurementlayer` |
|---|---|---|---|---|---|
| `public` | **0** | 125 | 0 | 10 | 6 |
| `fhort`  | **396** | 274 | 390 | 10 | 6 |
| `los`    | **0** | **0** | 0 | 10 | 6 |

**Conseqüències immediates per a la pregunta «sembrar el catàleg v4 és aïllat?»:**

1. `POMMaster` **no viu mai a `public`** malgrat que la taula hi existeix (l'app `pom` és SHARED+TENANT i crea la taula als tres schemes). El catàleg real és **per tenant**. `public.pom_pommaster` = 0 files avui.
2. `los` **no té ni un POMMaster ni un POMGlobal** (confirma la nota de memòria «`los` sense POMMaster»), però **sí** té 51 models vius (`los.models_app_model` = 51).
3. `fhort` té **0 models i 0 BaseMeasurement vius** (`v4_neteja_models.py` ja s'ha aplicat), però **conserva els 396 POMMaster i els 390 àlies**.
4. `POMMaster._meta.db_table` = **`pom_pommaster`**, no `pom_pomglobal`. `pom_pomglobal` és la taula de `POMGlobal` (el catàleg canònic de la casa). El brief deia el contrari; el codi diu això.
   ```
   POMMaster._meta.db_table  → 'pom_pommaster'
   POMGlobal → 'pom_pomglobal'   (FK: pom_pommaster.pom_global_id → pom_pomglobal.id)
   ```
5. Les taules `pom_garmenttypepommap` i `pom_garmentgrouppommap` **no existeixen a cap dels tres schemes**: la migració `0073` de U2 no s'ha aplicat (`darreres pom` a `public.django_migrations` = `0072_cat22_sembra_garmentgroup`).

---

# A3 · Cens de lectors i escriptors de `POMMaster`

## A3.0 · La superfície de dependència: `POMMaster._meta.related_objects`

Consulta literal (`manage.py shell`, sortida enganxada):

| model relacionat | camp | `on_delete` | taula |
|---|---|---|---|
| `pom.POMEstadisticaTenant` | `pom` | **CASCADE** | `pom_pomestadisticatenant` |
| `pom.CustomerPOMAlias` | `pom` | **CASCADE** | `pom_customerpomalias` |
| `pom.GarmentPOMMap` | `pom` | PROTECT | `pom_garmentpommap` |
| `pom.GarmentTypePOMMap` | `pom` | PROTECT | `pom_garmenttypepommap` *(taula inexistent a BD)* |
| `pom.GarmentGroupPOMMap` | `pom` | PROTECT | `pom_garmentgrouppommap` *(taula inexistent a BD)* |
| `pom.ItemBaseMeasurement` | `pom` | PROTECT | `pom_itembasemeasurement` |
| `pom.GradingRule` | `pom` | PROTECT | `pom_gradingrule` |
| `pom.ClientMesuraPerfil` | `pom` | PROTECT | `pom_clientmesuraperfil` |
| `models_app.BaseMeasurement` | `pom` | PROTECT | `models_app_basemeasurement` |
| `models_app.MeasurementChangeLog` | `pom` | PROTECT | `models_app_measurementchangelog` |
| `models_app.ModelGradingOverride` | `pom` | PROTECT | `models_app_modelgradingoverride` |
| `models_app.ModelGradingRule` | `pom` | PROTECT | `models_app_modelgradingrule` |
| `models_app.POMPlacement` | `pom` | PROTECT | `models_app_pomplacement` |
| `fitting.POMAlert` | `pom` | PROTECT | `fitting_pomalert` |
| `fitting.GradedSpec` | `pom` | PROTECT | `fitting_gradedspec` |
| `patterns.PatternPOM` | **`pom_master`** | PROTECT | `patterns_patternpom` |

⚠️ **Dues CASCADE**: `CustomerPOMAlias` i `POMEstadisticaTenant`. Esborrar un `POMMaster` **s'emporta el catàleg del client** sense avís. Totes les altres 14 són PROTECT.
⚠️ El camp de `patterns.PatternPOM` **no es diu `pom` sinó `pom_master`** — qualsevol cens que enumeri per nom de camp `pom` el perd.

`/var/www/ftt-staging/backend/fhort/pom/cataleg_views.py:33-40` ja fa aquest recorregut per `_meta.related_objects`, i el seu comentari diu explícitament que «el dia que algú afegeixi una FK cap a `POMMaster`, aquest cens la veurà». És l'únic lloc del codi que no enumera a mà.

---

## A3.a · Camins que **LLEGEIXEN** `POMMaster` (exclòs `search_poms_view`)

`search_poms_view` és a `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:114` (lectures a `:165` amb àlies, `:168` sense) — **exclòs per demanda**.

**Convenció de la columna «àlies»**
- **sí** = la consulta passa per `CustomerPOMAlias` o filtra per `customer`.
- **no ▸ catàleg** = escaneja el catàleg SENCER del tenant, sense acotar-lo a cap client.
- **no ▸ PK** = només llegeix files ja referenciades per `id`/`pk` (no escaneja, però tampoc acota).
- **no ▸ join** = hi arriba per FK des d'una taula ja acotada (model / item / ruleset / spec).

| fitxer:línia | funció / vista | àlies? | què en fa |
|---|---|---|---|
| `/var/www/ftt-staging/backend/data/import_master.py:228` | `_imp_pom_master` | no ▸ catàleg | resol/crea per `codi_client` en importar el catàleg des de JSON |
| `/var/www/ftt-staging/backend/data/import_master.py:267` | `_imp_grading_rule` | no ▸ catàleg | resol el codi `pom` del JSON per penjar-hi la `GradingRule` |
| `/var/www/ftt-staging/backend/data/import_master.py:361` | mòdul (resum) | no ▸ catàleg | compta files del catàleg |
| `/var/www/ftt-staging/backend/fhort/fitting/graded_spec_views.py:54` | `GradedSpecTableView.get` | no ▸ join | `select_related('pom__pom_global')` sobre `GradedSpec` |
| `/var/www/ftt-staging/backend/fhort/fitting/graded_spec_views.py:72` | `GradedSpecTableView.get` | no ▸ join | serialitza codi/noms EN-CA/categoria/unitat de cada POM |
| `/var/www/ftt-staging/backend/fhort/fitting/repas_views.py:202` | `FittingRepasView.get` | no ▸ join | `PieceFittingLine.select_related('pom','pom__pom_global')` |
| `/var/www/ftt-staging/backend/fhort/fitting/repas_views.py:340` | `FittingRepasView.get` | no ▸ PK (`id__in`) | resol nomenclatura dels POMs d'etapa sense sessió, per pintar la graella de repàs |
| `/var/www/ftt-staging/backend/fhort/fitting/serializers.py:301` | `PieceFittingGridSerializer.get_lines` | no ▸ join | carrega `pom`+`pom_global` de cada línia |
| `/var/www/ftt-staging/backend/fhort/fitting/serializers.py:377` | `PieceFittingGridSerializer.get_lines` | no ▸ join | serialitza `pom_code`/`name_en`/`name_cat`/`is_key` |
| `/var/www/ftt-staging/backend/fhort/fitting/services.py:329` | `create_piece_fitting` | no ▸ join | POM de cada `GradedSpec` en crear el fitting de peça |
| `/var/www/ftt-staging/backend/fhort/fitting/services.py:487` | `consolidate_base_from_fitting` | no ▸ join | POM de cada línia en consolidar base |
| `/var/www/ftt-staging/backend/fhort/fitting/staleness.py:112` | `estalitud` | no ▸ join | POM de cada spec per calcular obsolescència |
| `/var/www/ftt-staging/backend/fhort/fitting/views.py:651` | `PieceFittingLineViewSet.propagar._resp` | no ▸ join | POM de les línies retornades |
| `/var/www/ftt-staging/backend/fhort/models_app/comprovacio_views.py:115` | `_seccio_descartades` | no ▸ join | POM de les línies de size check descartades |
| `/var/www/ftt-staging/backend/fhort/models_app/comprovacio_views.py:223` | `comprovacio_view` | no ▸ join | POM de les línies serialitzades |
| `/var/www/ftt-staging/backend/fhort/models_app/extraction_views.py:1032` | `find_pom_master` (estratègia a) | **sí** | resol codi/descripció del document via àlies del client → HIGH |
| `…/extraction_views.py:1044` | `find_pom_master` (sinònim) | no ▸ catàleg | itera **TOT** el catàleg actiu buscant `nom_client` |
| `…/extraction_views.py:1048` | `find_pom_master` (sinònim global) | no ▸ catàleg | itera tot el catàleg amb `pom_global` per casar `nom_en` |
| `…/extraction_views.py:1056` | `find_pom_master` (estratègia 3) | no ▸ catàleg | itera tot el catàleg per casar la descripció |
| `…/extraction_views.py:1065` | `find_pom_master` (estratègia 4) | no ▸ catàleg | itera tot el catàleg per `POMGlobal.nom_en`/`abbreviation` |
| `…/extraction_views.py:1083` | `find_pom_master` (codi numèric) | no ▸ catàleg | itera tot el catàleg buscant «lining» |
| `…/extraction_views.py:1100` | `find_pom_master` (fallback d) | no ▸ catàleg | `codi_client__iexact` al catàleg sencer → LOW |
| `…/extraction_views.py:1112` | `find_pom_master` (fallback d, arrel) | no ▸ catàleg | arrel de lletres del codi al catàleg sencer → LOW |
| `…/extraction_views.py:1711` | `_candidats_de_codi` | no ▸ catàleg (per codi) | **serialitza a la UI** els POMs que es disputen un codi (payload del 409) |
| `…/extraction_views.py:1749` | `_pla_de_resolucions` | no ▸ PK | valida que el POM triat per l'humà existeix i és actiu |
| `…/extraction_views.py:1765` | `_pla_de_resolucions` | no ▸ catàleg (per codi) | valida que el codi a crear no existeixi ja |
| `…/extraction_views.py:1840` | `import_session_poms_view` | no ▸ catàleg (per codi) | **compta** POMs tenant-only duplicats → porta 409 |
| `…/extraction_views.py:1899` | `import_session_poms_view` | no ▸ catàleg (per codi) | reutilitza el POMMaster tenant-only si n'hi ha exactament un |
| `…/extraction_views.py:1921` | `import_session_poms_view` | no ▸ PK | resol POMs confirmats afegits manualment |
| `…/extraction_views.py:2082` | `import_session_library_prefill_view` | no ▸ PK (`id__in`) | mapa `pom_id → codi_client` per al prefill de la Size Library |
| `…/extraction_views.py:2321` | `import_session_confirmar_view` | no ▸ PK | resol els POMs confirmats abans d'escriure `BaseMeasurement` |
| `…/extraction_views.py:2344` / `:2380` | `import_session_confirmar_view` | no ▸ join | POM de les `BaseMeasurement` (pre-flight de soroll / resultat) |
| `/var/www/ftt-staging/backend/fhort/models_app/pom_placement_views.py:51` | `_cascada` | no ▸ join | POM de cada `POMPlacement` |
| `/var/www/ftt-staging/backend/fhort/models_app/pom_placement_views.py:145` | `_desar_precedent` | no ▸ PK | **valida** que el `pom_id` existeix abans de desar la cota |
| `/var/www/ftt-staging/backend/fhort/models_app/serializers.py:433` | `BaseMeasurementSerializer` | no ▸ join | **serialitza a la UI** el fallback tenant-only (`pom_codi_client`/`pom_nom_client`) |
| `/var/www/ftt-staging/backend/fhort/models_app/serializers_size_check.py:104` | `SizeCheckGridSerializer.get_lines` | no ▸ join | serialitza el POM de cada línia |
| `/var/www/ftt-staging/backend/fhort/models_app/services_size_check.py:58` / `:224` | `_materialize_lines` / `resolve_size_check` | no ▸ join | POM de cada spec/línia |
| `/var/www/ftt-staging/backend/fhort/models_app/tech_sheet_views.py:348` | `TechSheetCreateModelView.post` | no ▸ catàleg (`pom_global__codi`) | resol el codi POM global extret al POMMaster del tenant per crear `BaseMeasurement` |
| `/var/www/ftt-staging/backend/fhort/models_app/views.py:506` | `BaseMeasurementViewSet.queryset` | no ▸ join | CRUD de mesures amb POM precarregat |
| `…/models_app/views.py:1269` | `suggested_poms_view` | no ▸ join **+ `alies_per_pom(model.customer_id)` a :1275 → sí** | POMs suggerits de l'item amb nomenclatura del client |
| `…/models_app/views.py:1350` | `materialize_poms_view` | no ▸ join | POM de les mesures a materialitzar |
| `…/models_app/views.py:1581` | `copiar_de_model_view` | no ▸ join | POM de les mesures del model origen |
| `…/models_app/views.py:1898` | `measurements_table_view` | no ▸ join | serialitza la taula de mesures |
| `…/models_app/views.py:2137` | `set_measurements_view` | no ▸ PK | valida el `pom_id` i el fixa a la `BaseMeasurement` |
| `…/models_app/views.py:2309` | `gravar_pom_view` | no ▸ PK | valida el `pom_id` de cada fila del payload |
| `…/models_app/views.py:2552` | `ai_analysis_view` | no ▸ join | codi/nom del POM com a context per a la IA |
| `…/models_app/views.py:2667` | `measurements_chat_view` | no ▸ join | context (`bm.pom.codi_client`) per al xat |
| `…/models_app/views.py:2733` | `measurements_chat_view` (AFEGIR) | no ▸ catàleg (`codi_client__iexact`) | resol un codi **proposat per la IA** contra el catàleg sencer |
| `…/models_app/views.py:2783` | `measurements_chat_view` | no ▸ join | re-serialitza les mesures |
| `…/models_app/views.py:2957` | `generate_grading_view` | no ▸ join | POM de les `BaseMeasurement` d'entrada del motor |
| `…/models_app/views.py:3061` | `set_size_override_view` | no ▸ PK | valida el POM abans de crear `ModelGradingOverride` |
| `…/models_app/views.py:3191` | `escalat_ajustar_talla_view` | no ▸ PK | valida el POM abans d'ajustar la talla |
| `…/models_app/views.py:3635` / `:3657` | `base_stages_view` | no ▸ join | POM de les mesures i del `MeasurementChangeLog` |
| `…/models_app/views.py:3992` / `:4049` | `model_dashboard_view` / `model_timeline_view` | no ▸ join | POM per al dashboard i el timeline |
| `…/models_app/views.py:4287` / `:4411` | `promoure_a_item_view` | no ▸ join | POM de les mesures a promocionar; ordena per `pom__codi_client` |
| `…/models_app/views.py:4584` | `acte_canonic_base_set_view` | no ▸ join | POM dels `ItemBaseMeasurement` |
| `…/models_app/views.py:4686` | `desactivar_pom_view` | no ▸ join | POM de la mesura desactivada |
| `/var/www/ftt-staging/backend/fhort/patterns/adapters.py:486` | `DjangoGradingSource.snapshot` | no ▸ join | POM dels specs per al snapshot de graduació |
| `/var/www/ftt-staging/backend/fhort/patterns/annotation_views.py:56` / `:59` / `:522` | `PatternPOMSerializer` / ViewSet | no ▸ join | serialitza `pom_master.codi_client`/`nom_client`; `select_related('pom_master')` |
| `/var/www/ftt-staging/backend/fhort/patterns/views.py:151` | `_alies_unics_del_customer` | **sí** | codi del client de cada POM per a la llista de treball del taller |
| `/var/www/ftt-staging/backend/fhort/patterns/views.py:585` / `:614` / `:645` | `PatternFileViewSet.model_poms` | no ▸ join | serialitza `codi_client`/`nom_client` + `alias_client` |
| `/var/www/ftt-staging/backend/fhort/pom/acumulacio.py:69` / `:71` / `:73` | `acumula_poms_de_item` | no ▸ join | POM dels tres mapes (grup / família / item) |
| `/var/www/ftt-staging/backend/fhort/pom/cataleg_views.py:37` | `_cens_relacions` | no ▸ PK | recorre `related_objects` i **compta** files per accessor → decideix si el POM és esborrable |
| `/var/www/ftt-staging/backend/fhort/pom/cataleg_views.py:123` | `pom_us_view` | no ▸ PK | serialitza la fitxa d'ús del POM |
| `/var/www/ftt-staging/backend/fhort/pom/cataleg_views.py:184` | `item_acumulacio_view` | no ▸ PK (`id__in`) | enriqueix l'acumulació d'un item |
| `/var/www/ftt-staging/backend/fhort/pom/dictionary_service.py:133` | `build_preview` | **sí** | àlies existents del client per al DIFF de la previsualització |
| `/var/www/ftt-staging/backend/fhort/pom/dictionary_service.py:135` | `build_preview` | no ▸ catàleg | cache de **TOT** el catàleg per comptar candidats de descripció |
| `/var/www/ftt-staging/backend/fhort/pom/dictionary_views.py:97` | `dictionary_commit_view` | **sí** | àlies existents → guard anti-sobreescriptura de feina MANUAL |
| `/var/www/ftt-staging/backend/fhort/pom/dictionary_views.py:156` | `dictionary_commit_view` | no ▸ PK | resol el POM validat per l'humà |
| `/var/www/ftt-staging/backend/fhort/pom/grading_utils.py:551` | `derive_rules_from_fitxa` | no ▸ PK | `codi_client` als bloqueigs/avisos de derivació |
| `/var/www/ftt-staging/backend/fhort/pom/grading_views.py:143` / `:176` | `measurements_table_view` | no ▸ join | POM+categoria dels specs i regles |
| `/var/www/ftt-staging/backend/fhort/pom/nomenclatura.py:33` | `alies_per_pom` | **sí** | mapa `pom_id → {client_code, …}` — **el punt únic** de nomenclatura de client |
| `/var/www/ftt-staging/backend/fhort/pom/nomenclatura.py:85` | `pom_del_codi` / `colisio_de_codi` | **sí** | resolutor invers codi-del-client → POMMaster |
| `/var/www/ftt-staging/backend/fhort/pom/s2_serializers.py:183` | `SizingProfileSerializer.get_grading_rules_preview` | no ▸ join | preview de 5 regles |
| `/var/www/ftt-staging/backend/fhort/pom/s2_views.py:158` / `:285` / `:313` | perfil / desempat / update de regla | no ▸ join | POM de les regles; desempata per `pom__pom_global__codi` |
| `/var/www/ftt-staging/backend/fhort/pom/s4_views.py:63` / `:215` | update amb història / regles amb unitats | no ▸ join | localitza i serialitza regles pel POM |
| `/var/www/ftt-staging/backend/fhort/pom/s6_views.py:39` | `pom_htm_view` | no ▸ PK | serialitza les instruccions de mesura (HTM) d'un POM |
| `/var/www/ftt-staging/backend/fhort/pom/s6_views.py:96` / `:183` | mesures/specs amb unitats | no ▸ join | POM de les files convertides |
| `/var/www/ftt-staging/backend/fhort/pom/s8_views.py:63` / `:112` / `:177` | exports CSV (grading / size set / fitting) | no ▸ join | POM de les files exportades |
| `/var/www/ftt-staging/backend/fhort/pom/s9_views.py:31,33,34` | `onboarding_status_view` | no ▸ catàleg | **compta** POMs actius (`>=10`) i el total |
| `/var/www/ftt-staging/backend/fhort/pom/s10_views.py:91` | `fitting_vs_spec_view` | no ▸ join | POM per creuar fitting vs spec |
| `/var/www/ftt-staging/backend/fhort/pom/s11_views.py:42` / `:57` / `:127` | resum i llista d'alertes | no ▸ join | POM de les `POMAlert`; agrega per `pom__codi_client` |
| `/var/www/ftt-staging/backend/fhort/pom/s11_views.py:188` | `check_tolerances_view` | no ▸ PK | resol el POM de cada mesura per valorar l'alerta |
| `/var/www/ftt-staging/backend/fhort/pom/size_map_views.py:683` | `size_map_create_view` | no ▸ PK | serialitza el POM en col·lisió per al 400 |
| `/var/www/ftt-staging/backend/fhort/pom/size_map_views.py:984` | `size_map_create_view` | no ▸ PK | resol el POM de cada regla abans de `update_or_create` de `GradingRule` |
| `/var/www/ftt-staging/backend/fhort/pom/views.py:57` | `POMMasterViewSet.queryset` | no ▸ catàleg | **serveix el catàleg SENCER a la UI** (list/detail/search) |
| `/var/www/ftt-staging/backend/fhort/pom/views.py:239,314,318,386,430,441,513` | ViewSets de regles i mapes | no ▸ join | POM precarregat; cerca per `pom__codi_client` |
| `/var/www/ftt-staging/backend/fhort/pom/views.py:563` | `ItemBaseMeasurementViewSet.upsert` | no ▸ PK | **valida** que el `pom` existeix (400 net) |
| `/var/www/ftt-staging/backend/fhort/pom/views.py:627` | `CustomerPOMAliasViewSet.queryset` | **sí** | CRUD d'àlies amb POM precarregat |
| `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:81` | `suggested_poms_view` | no ▸ join | POMs suggerits via `GarmentPOMMap` |
| `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:319` | `save_base_size_view` | no ▸ PK | llegeix `tolerancia_default_minus/plus` del catàleg per copiar-los a la `BaseMeasurement` |
| `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:453` | `base_measurements_view` | no ▸ join (+ `alies_per_pom` a `:460` → **sí**) | serialitza mesures amb POM i nomenclatura de client |
| `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:572` | `create_tenant_pom_view` | no ▸ catàleg | valida que `codi_client` no existeixi ja |
| `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:658` | `create_model_pom_view` | no ▸ catàleg (`__iexact`) | valida el codi de la CASA; la col·lisió del CLIENT la fa `colisio_de_codi` (**sí**) |
| `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:722` | `edit_pom_nomenclature_view` | no ▸ PK | llegeix el POM per editar-lo *(vegeu A3.b — és ESCRIPTOR)* |
| `/var/www/ftt-staging/backend/fhort/tenants/federation_service.py:627` / `:629` | `_resol_pom_al_desti` | no ▸ catàleg (`actiu=True`) | resol la clau natural per `pom_global__codi`, fallback `codi_client`, al catàleg del **destí** |
| `/var/www/ftt-staging/backend/fhort/tenants/federation_service.py:660` / `:673` | `_llegeix_patrimoni` | no ▸ join | POM de les `BaseMeasurement` i specs que viatgen |
| `…/pom/management/commands/audit_lost_breaks.py:52` | `handle` | no ▸ join | POM de les regles auditades |
| `…/pom/management/commands/author_baby_pom_maps.py:132` | `handle` | no ▸ PK (`pk__in`) | **valida** que tots els POMs del set existeixen i són actius; si no, avorta |
| `…/pom/management/commands/export_losan_package.py:147` / `:196` | `handle` | **sí** (`customer=LOS`) | `pom_id` reclamats pels àlies de LOS |
| `…/pom/management/commands/export_losan_package.py:153,253,261,331` | `handle` | no ▸ PK / join | serialitza al paquet POMMaster ∪ item bases ∪ maps ∪ regles |
| `…/pom/management/commands/load_map_inline.py:102` | `handle` | no ▸ catàleg | mapa `pom_global.codi → POMMaster` per resoldre el CSV |
| `…/pom/management/commands/seed_baby_months_grading.py:93` | `_run` | no ▸ catàleg | resol el `codi_client` de cada regla; si no hi és, la salta |
| `…/pom/management/commands/seed_losan_master_delta.py:95` / `:97` | `_lvl_candidates` | **sí** a `:95`, **no ▸ catàleg** a `:97` | candidats via àlies LOS + fallback per `codi_client` directe |
| `…/pom/management/commands/seed_losan_rules.py:132` | `_seed_contenidor` | no ▸ catàleg | resol el codi POM; inexistent → regla no creada |
| `…/pom/management/commands/sembra_ai_report.py:98` / `:103` | `Catalog.__init__` | **sí** a `:98`, **no ▸ catàleg** a `:103` | índexs d'àlies LOS + índex `codi_client → POMs` de TOT el catàleg (en deriva els duplicats) |
| `…/pom/management/commands/validate_los_maps.py:46` / `:54` / `:59` | `resolve_pom` | **sí** a `:46`, **no ▸ catàleg** a `:54,:59` | resolució per àlies i, si falla, codi exacte/variants al catàleg |
| `/var/www/ftt-staging/backend/scripts_tmp/extract_grading_catalog.py:64` / `:65` | secció 7 | **sí** / **no ▸ catàleg** | compara quin dels dos camins de resolució guanya |
| `/var/www/ftt-staging/backend/scripts_tmp/neteja_codis_duplicats.py:65,69,84` | mòdul | no ▸ catàleg (creua amb àlies) | compta `codi_client` repetits; llista POMs actius **sense cap àlies** (orfes) |
| `/var/www/ftt-staging/backend/scripts_tmp/onada1_dump_superficies.py:189` | `_claus_naturals` | no ▸ catàleg (primers 40) | bolca claus naturals de federació |
| `/var/www/ftt-staging/backend/scripts_tmp/p05e_cens_duplicats.py:6` / `:10` | mòdul | no ▸ catàleg | compta duplicats i n'imprimeix àlies i mesures |
| `/var/www/ftt-staging/backend/scripts_tmp/p05e_verifica.py:12,40,56` | mòdul | no ▸ catàleg / PK | control de residu abans/després |

**Falsos positius del grep, verificats un a un (NO són lectures):**
- Comentaris/docstrings: `graded_spec_views.py:101`, `:146`; `patterns/views.py:559`.
- Només `import` del símbol, sense query a la línia: `extraction_views.py:2168`, `tech_sheet_views.py:262`, `dictionary_views.py:88`, `grading_utils.py:499`, `size_map_views.py:627`.
- **`/var/www/ftt-staging/backend/fhort/patterns/annotation_views.py:19` importa `POMMaster` i no l'usa enlloc del fitxer** (import mort).

### Els números que importen d'A3.a

- **Camins de lectura totals censats: ~110.**
- **Camins que filtren per àlies (`CustomerPOMAlias` / `customer`): 13.** I gairebé tots pengen de **dos** punts: `/var/www/ftt-staging/backend/fhort/pom/nomenclatura.py:33` (`alies_per_pom`) i `:85` (`pom_del_codi`/`colisio_de_codi`).
- **Tota la resta (~97) llegeix el catàleg del tenant sense saber de quin client parla.** En particular, **cap** d'aquests el filtra:
  `POMMasterViewSet` (`pom/views.py:57`, el catàleg sencer a la UI), `find_pom_master` estratègies b/c/d (`extraction_views.py:1044-1112`), `_candidats_de_codi` (`:1711`), `onboarding_status_view` (`s9_views.py:31-34`), `federation_service._resol_pom_al_desti` (`:627,:629`), `measurements_chat_view` (`views.py:2733`), `tech_sheet_views.py:348`, `dictionary_service.py:135`, `wizard_views.py:572` i `:658`.

---

## A3.b · Camins que **ESCRIUEN o COPIEN** files de `POMMaster`

### B1 · Superfície HTTP (l'app viva)

| fitxer:línia | camí | schema | què fa |
|---|---|---|---|
| `/var/www/ftt-staging/backend/fhort/pom/views.py:54-63` | **`POMMasterViewSet`** → `/api/v1/poms/` (registrat a `/var/www/ftt-staging/backend/fhort/pom/urls.py:22`) | **el del tenant de la petició** (django-tenants pel host) | **`ModelViewSet` complet amb `permission_classes = [IsAuthenticated]` i cap `get_permissions`.** POST / PUT / PATCH / **DELETE** sobre el catàleg estan oberts a qualsevol usuari autenticat. Compareu amb `SizeSystemViewSet` (`views.py:88-91`) i `SizeDefinitionViewSet`, que sí que tenen `get_permissions` → `_ConfigureWrite` (capability `CONFIGURE`). **El catàleg de POMs no té aquest gate.** El `destroy` tampoc té guard de dependències (`SizeSystemViewSet.destroy` a `:93-100` sí que en té un) → un `DELETE /api/v1/poms/<id>/` s'emporta per **CASCADE** tots els `CustomerPOMAlias` i `POMEstadisticaTenant` d'aquell POM, o peta amb `ProtectedError` si hi ha res de les 14 relacions PROTECT. |
| `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:575` | `create_tenant_pom_view` → `POST /api/v1/poms/crear-tenant/` | tenant de la petició | `POMMaster.objects.create(codi_client, nom_client, categoria_id, notes, actiu=True)`. `pom_global` queda a `None` (tenant-only). Guard previ a `:572` (codi ja existent → 400). **No posa `pendent_revisio`.** |
| `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:664` | `create_model_pom_view` («POM del model») | tenant de la petició | `create(...)` amb `pendent_revisio=True` i `origen_import=f'model:{codi_intern}'`. **Encunya el `codi_casa`**: si `codi_client__iexact` ja existeix, el qualifica amb el codi del customer (`:657-661`). Crea també el `CustomerPOMAlias` amb `origen='MODEL'` (`:688+`), dins d'un `transaction.atomic()`. |
| `/var/www/ftt-staging/backend/fhort/pom/wizard_views.py:722-729` | `edit_pom_nomenclature_view` → `PATCH /api/v1/poms/<id>/nomenclatura/` | tenant de la petició | **MUTA** `codi_client` i `nom_client` d'un POM existent amb `save(update_fields=[...])`. Cap validació d'unicitat, cap guard de POM compartit, cap gate de capability. |
| `/var/www/ftt-staging/backend/fhort/models_app/extraction_views.py:1872` | `import_session_poms_view` (resolucions del pas 2, `accio='crea'`) | tenant de la petició | `create(pom_global=None, pendent_revisio=True, origen_import=str(session.token), notes='Creat des del pas 2 de l\'import…')`, dins l'`atomic` de `:1863`. |
| `/var/www/ftt-staging/backend/fhort/models_app/extraction_views.py:1901` | `import_session_poms_view` (POMs sense match) | tenant de la petició | Mateix `create`, `notes='Creat automàticament per import…'`. **Reutilitza** si ja n'hi ha exactament un (`:1899`); el cas `>1` surt abans pel 409 de `:1840`. |
| `/var/www/ftt-staging/backend/fhort/pom/dictionary_views.py:146` | `dictionary_commit_view` (commit del diccionari del client) | tenant de la petició | `create(pom_global=None, pendent_revisio=True, origen_import=f"diccionari:{customer.codi}:{today}")`. Comentari literal a `:145`: **«POM tenant-only nou (sense gate — fase beta)»**. |

### B2 · Management commands

| fitxer:línia | com decideix l'schema | escriu a `public`? | escriu a tenant? | operació |
|---|---|---|---|---|
| `…/pom/management/commands/replace_pom_catalog.py:733,748,753` | `--schema`, **default `public`** | **SÍ (default)** | només si li passes `--schema <tenant>` | **`POMGlobal.objects.all().delete()`** i `bulk_create` de 106. **No toca `POMMaster`** (no l'importa). Sense dry-run: escriu sempre. |
| `…/pom/management/commands/extend_pom_catalog.py:167-207` | `--schema` (default `fhort`); `schemas_global = ['public'] + [tenant]` | **SÍ** (`POMGlobal` a `:177`) | **SÍ** (`POMMaster` a `:195`) | `update_or_create` de `POMGlobal` per `codi` a **public I tenant**; després `POMMaster.update_or_create(pom_global=pg, …)` **només al tenant**. Mai delete. Sense dry-run. |
| `…/pom/management/commands/seed_baby_poms.py:30,179,250-268` | `ALL_SCHEMAS = ['public','fhort']`, `--schema` (default `all`) | **SÍ** (`POMGlobal`) | **SÍ** (`POMMaster`, guardat per `if is_tenant`) | `update_or_create` als dos. **Dry-run per defecte**; cal `--no-dry-run`. |
| `…/pom/management/commands/reseed_tenant_fhort.py:209,221-238,258-266` | `--tenant` (default `fhort`) | no | **SÍ** | ⚠️ **`POMMaster.objects.all().delete()`** al Pas 0 (`:236`, dins la llista amb `GradingRule`, `SizingProfile`, `GradingRuleSet`, `ClientMesuraPerfil`, `GarmentPOMMap`) i després `bulk_create` d'un POMMaster **per cada `POMGlobal`** del tenant. **El delete s'emporta per CASCADE tots els `CustomerPOMAlias`** — el catàleg del client. **Cap dry-run.** |
| `…/pom/management/commands/consolidate_pom_catalog.py:46,54,129,236` | `--schema` (default `CFG.TENANT`) | no | **SÍ** | Fase `fusio`: `POMMaster.objects.filter(pk=prim.pk).update(actiu=False)` (`:129`) + `.all().delete()` de relacions (`:122-125`, `:250-255`). Fase `translate`: `_create_los_pom` crea `POMMaster` **i** un `POMGlobal` sintètic `LOSPOM-<id>` (`:236-241`) + àlies. Dry-run per defecte (`--no-dry-run`), tot dins `transaction.atomic()`. |
| `…/pom/management/commands/seed_master_delta_catalog.py:50,57,78-86` | `--schema` (default `CFG.TENANT`) | no | **SÍ** | `get_or_create(codi_client=…, defaults={pendent_revisio:True, origen_import:ORIGEN})` + `POMGlobal.create(codi=f'LOSPOM-{pom.id}')` + àlies. Dry-run per defecte, `atomic`. |
| `…/pom/management/commands/seed_brownie_cataleg.py:94,112,135,175` | `--schema` (default `TENANT`) | no | **SÍ** | `get_or_create(codi_client=CODI_CATALEG.get(codi,codi), nom_client=nom, defaults={pendent_revisio:True, origen_import:'BRW-CATALEG-v3'})` — **només amb `--encunyar`**; a més **MUTA `pom.nom_client`** (`:175`) quan el POM no és compartit (llei D2, guard `compartits`). Dry-run per defecte. |
| `…/pom/management/commands/load_losan_package.py:61-64,166,258-266` | **`--schema-target` OBLIGATORI** | no | **SÍ** (el destí) | `_upsert(POMMaster, lookup, …)` o `POMMaster(...).save()`. Lookup en 3 nivells: `_resolve_pom(key)` → `(pom_global__codi, codi_client)` → create per `codi_client`. També upserta `POMGlobal` (`:235`). **Dry-run per defecte, `--apply` per escriure**, tot dins `atomic`. |
| `…/pom/management/commands/reconcile_tenant_poms.py:29,42-51,57` | **`SCHEMA` constant al fitxer** (no és argument) | no | **SÍ (`fhort`)** | MUTA `actiu=False` i `pendent_revisio=False` sobre **llistes d'ids literals**. Dry-run per defecte. |
| `/var/www/ftt-staging/backend/fhort/tasks/management/commands/bootstrap_tenant.py:61,154,416-477` | `bootstrap_tenant <schema> --from <origen>` (default origen `fhort`) | no | **SÍ (destí)** — **copia de tenant a tenant, mai de public** | `POMMaster` és al bloc `'pom_masters'` (`:61`), amb **clau natural `('codi_client',)`** (`:154`) i comentari explícit: «CORRECCIÓ AL CENS: `pom_global` NO és 1:1 (126 distints / 170 files). La clau és `codi_client`». Arrossega `GarmentPOMMap`. Dependències de selecció: `pom_masters` → `{base, garments}` → `POMGlobal`, `POMCategory`, `GarmentType`… `--dry-run` i `--additive` disponibles. |
| `/var/www/ftt-staging/backend/data/import_master.py:228` | **cap** — script d'import que corre a l'schema actiu del shell | segons context | segons context | `get_or_create(codi_client=codi, defaults={nom_client, categoria, notes, actiu})`. |

**Commands que NO toquen `POMMaster`** (verificat per grep dirigit): `repair_customer_aliases.py` (només `CustomerPOMAlias.delete()` a `:173`,`:192`), `delete_master_delta_seed.py`, `cleanup_losan_old.py`, `seed_losan_ss27.py`, `seed_losan_grading_v3.py` (només import), `seed_brownie_germans.py` (només comentaris), `author_baby_pom_maps.py` (només valida), `validate_los_maps.py`, `sembra_ai_report.py`, `load_map_inline.py`, `seed_losan_rules*.py`, `export_losan_package.py`, `audit_lost_breaks.py`.

### B3 · `scripts_tmp/`

Cap escriu `POMMaster`. Tots són cens/verificació de lectura (`extract_grading_catalog.py`, `neteja_codis_duplicats.py`, `onada1_dump_superficies.py`, `p05e_cens_duplicats.py`, `p05e_verifica.py`), i `v4_neteja_models.py` diu literalment a la capçalera (`:16-18`): «NO TOCA MAI … el CATÀLEG (`POMMaster`, `CustomerPOMAlias`, …) ni res del tenant `los`. El schema `public` tampoc.»

### B4 · Migracions

`grep -l` sobre `fhort/*/migrations/*.py` dona 7 fitxers que anomenen `POMMaster`/`POMGlobal`:
`pom/0001_initial.py`, `pom/0031_migrate_brownie_synonyms_to_aliases.py`, `pom/0032_migrate_dotted_codi_client_to_aliases.py`, `pom/0034_fix_a1_remove_a2_customerpomalias.py`, `pom/0038_delete_gradingexception.py`, `models_app/0011_…`, `models_app/0069_…`. Les de `0031`/`0032` migren dades **cap a `CustomerPOMAlias`**, no creen POMMaster.

### B5 · El resum d'A3.b, sense adorns

**11 camins escriuen `POMMaster`, no 4:** 5 per HTTP (`POMMasterViewSet` CRUD complet, `create_tenant_pom_view`, `create_model_pom_view`, `edit_pom_nomenclature_view`, els dos `create` d'`extraction_views`, més `dictionary_commit_view`) i 8 per command/script.

**Dos camins ESBORREN files de `POMMaster`:**
1. `reseed_tenant_fhort.py:236` — `POMMaster.objects.all().delete()` sense dry-run.
2. `POMMasterViewSet` `DELETE` — obert a `IsAuthenticated`, sense guard de dependències.
Tots dos arrosseguen **`CustomerPOMAlias` per CASCADE**.

**Cap camí copia de `public` a tenant.** Els que toquen `public` (`replace_pom_catalog`, `extend_pom_catalog`, `seed_baby_poms`) hi escriuen **`POMGlobal`**, no `POMMaster`, i el POMMaster el creen **directament al tenant** llegint el `POMGlobal` local del tenant (no el de public). L'única còpia tenant→tenant és `bootstrap_tenant.py`, per clau natural `codi_client`.

---

# A5 · Format d'instància

## A5.1 · On es GENERA el slug compost

**Es genera en UN SOL LLOC, i és al FRONTEND.**

- `/var/www/ftt-staging/frontend/src/utils/diccionariMesures.js:106-116` — `composaInstancia(dicc, trams)`:
  ```js
  const sepInst = (dicc) => dicc?.regles?.instancia_separador ?? '-'
  export function composaInstancia(dicc, trams) {
    const eixos = Object.keys(dicc?.instancies || {})
    const pes = (s) => { const e = eixDe(dicc, s); const i = eixos.indexOf(e); return i < 0 ? 99 : i }
    return [...new Set(trams.filter(Boolean))].sort((a, b) => pes(a) - pes(b)).join(sepInst(dicc))
  }
  ```
  L'ordre no és de clic: es reordena pel **pes de l'eix** (posició abans que estat) perquè `left-relaxed` i `relaxed-left` no siguin dues claus.

- **El separador el mana el backend com a DADA**: `/var/www/ftt-staging/backend/fhort/pom/identity_views.py:98` →
  ```py
  'instancia_separador': '-',
  ```
  emès dins `regles` per `GET /api/v1/mesures/diccionari/`. **És l'ÚNIC lloc del backend on el guionet és una decisió.** El backend no compon mai un slug compost per si sol.

- **El backend NO GENERA slugs**: `grep -rn "instancia.*split\|SEP_INSTANCIA\|instancia_separador" --include=*.py` dona exactament 4 hits, i cap és de generació:
  - `identity_views.py:98` (l'emissió de la regla),
  - `scripts_tmp/fix_sufix_instancia_guio.py:47,52,67` (el desmuntatge, script one-shot).

- **Punts on el slug compost ENTRA a la BD** (els escriptors del front que criden `composaInstancia`):
  - `/var/www/ftt-staging/frontend/src/components/EditableTable/EditableTable.jsx:502` — partir un POM (crea la fila triada i la germana).
  - `/var/www/ftt-staging/frontend/src/components/EditableTable/EditableTable.jsx:610` — **treure** un tram (recompon la resta).
  - `/var/www/ftt-staging/frontend/src/components/EditableTable/EditableTable.jsx:1446,1455,1458` — el modal de crear germana (guard de duplicat + proposta de codi).

## A5.2 · On es CONSUMEIX el slug compost

### Backend

| fitxer:línia | què fa |
|---|---|
| `/var/www/ftt-staging/backend/fhort/pom/identity_views.py:98` | **emet la regla** `instancia_separador: '-'` |
| `/var/www/ftt-staging/backend/fhort/pom/identitat.py:41-52` | `clau_mesura(pom_id, capa, instancia)` → **`{pom_id}\|{capa}\|{instancia}`**. **Tracta la instància com a TEXT OPAC**: no la desmunta mai. Separador `\|` triat per no xocar amb `{pom_id}:{talla}` |
| `/var/www/ftt-staging/backend/scripts_tmp/fix_sufix_instancia_guio.py:47,52,67` | ÚNIC desmuntatge del backend: `sufix_esperat()` fa `instancia.split('-')` i concatena els sufixos del diccionari. **Toca `nom_fitxa`, no `instancia`** |
| `…/models_app/serializers.py:476,488` | `BaseMeasurementSerializer`: passa `instancia` tal qual i aplica el guard `instancia_exigeix_nom` |
| `…/models_app/views.py:3397` | `(m.get('capa') or SLUG_DEFECTE, m.get('instancia') or '')` — text opac |
| `…/pom/s10_views.py:160`, `…/fitting/services.py:344,444,500`, `…/models_app/services_derivacio.py:77,115`, `…/pom/services.py:307,1124`, `…/pom/views.py:613`, `…/pom/wizard_views.py:292,311,332`, `…/models_app/extraction_views.py:2577,2724`, `…/models_app/tech_sheet_views.py:371`, `…/pom/management/commands/reseed_tenant_fhort.py:314` | copien/fixen `instancia` com a **text opac** (la immensa majoria amb `instancia=''` literal) |
| `…/tasks/management/commands/bootstrap_tenant.py:167` | clau natural de `GarmentPOMMap` = `('garment_type_item','pom','capa','instancia')` |

**Cap CHECK de BD restringeix el valor.** Verificat contra `pg_constraint` als tres schemes: l'única restricció semàntica és
`models_app_basemeasurement_instancia_exigeix_nom` → `CHECK (NOT (instancia > '' AND nom_fitxa = ''))`.
La resta són `NOT NULL` i les 8 `UNIQUE` de 4-5 columnes que inclouen `instancia`. **Un slug amb qualsevol forma hi entra.** Longituds: `models_app.BaseMeasurement.instancia` `max_length=60`; `pom.MeasurementInstance.slug` `max_length=30`.

### Frontend

| fitxer:línia | què fa |
|---|---|
| `/var/www/ftt-staging/frontend/src/utils/diccionariMesures.js:104` | `sepInst(dicc)` — **el separador, llegit de `regles.instancia_separador`** |
| `…/diccionariMesures.js:98` | `tramsInstancia(dicc, slug)` = `slug.split(sepInst(dicc)).filter(Boolean)` |
| `…/diccionariMesures.js:106` | `composaInstancia` (v. A5.1) |
| `…/diccionariMesures.js:130-137` | `codiProposat` — usa **`regles.sufix_separador`** (`''`), NO el d'instància |
| `…/diccionariMesures.js:~145+` | `codiBase` — treu els sufixos concatenats del `nom_fitxa` |
| `/var/www/ftt-staging/frontend/src/utils/capaInstancia.js:70` | `const SEP_INSTANCIA = '-'` — **SEGONA DEFINICIÓ, LITERAL I INDEPENDENT DEL DICCIONARI** |
| `…/capaInstancia.js:88-93` | `etiquetaInstancia(slug, dicc)` = `String(slug).split(SEP_INSTANCIA).map(...).join(' · ')` |
| `…/capaInstancia.js:~150` | `sufixIdentitat(fila, t, dicc)` — el sufix d'una línia per a superfícies d'una sola línia |
| `/var/www/ftt-staging/frontend/src/utils/identitatMesura.js:23-25` | `identitatMesura(fila)` = `` `${pom_id}\|${capa}\|${instancia}` `` — clau de `Map` interna, **text opac** |
| `/var/www/ftt-staging/frontend/src/components/EditableTable/EditableTable.jsx:317,466,471,495,499,502,506,587,599,606,608,610,611,986,1201,1366,1371,1439,1446,1453-1458,1500,1509,1999,2038` | l'únic component que **desmunta i recompon** |
| `/var/www/ftt-staging/frontend/src/components/model/ComprovacioPanel.jsx:100,315` · `MeasureGrid.jsx:229` · `CheckMeasureEditor.jsx:634,637,656` | etiqueten (`etiquetaInstancia`) / escriuen la instància |
| `/var/www/ftt-staging/frontend/src/components/grading/GraduacioSuperficie.jsx:234` · `pages/FittingDetail.jsx:396,398` · `pages/FittingPrintSheet.jsx:211` · `pages/TechSheetEditor.jsx:344,6911` | només etiqueten |

⚠️ **El separador viu a DOS llocs al front amb dues fonts diferents:** `diccionariMesures.js:104` el llegeix de la resposta del backend (`?? '-'` de fallback); `capaInstancia.js:70` el té **hardcodejat** i no consulta el diccionari mai. `capaInstancia.js` documenta la separació de responsabilitats (lectura vs escriptura), però el separador és estructura, no literal, i està duplicat.

### El diccionari sembrat (`seed_measurement_instances.py:38-64`)
8 posicions (`left`/L, `right`/R, `top`/T, `bottom`/B, `cf`/CF, `cb`/CB, `side`/S, `waistband_seam`/**cap sufix**) + 2 estats (`relaxed`, `extended`, **tots dos sense sufix**). 10 files a cada schema (verificat: `public`, `fhort`, `los` = 10 i 10 i 10).

## A5.3 · Quantes files porten slug compost al dump del 06/08

**Mètode escollit — CAP restauració, cap BD tocada.** El `pg_restore` del sistema (v16) rebutja el fitxer (*«unsupported version (1.16) in file header»*, dumped by pg_dump 18.4), però hi ha **`/usr/lib/postgresql/18/bin/pg_restore`**, i amb `--data-only --table=<T> -f <fitxer>` s'extreu el bloc `COPY` **a un fitxer de scratchpad**: és lectura pura del `.dump`, no toca cap servidor ni cap base de dades.

Comandes exactes executades:
```
/usr/lib/postgresql/18/bin/pg_restore --list \
    /root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump
/usr/lib/postgresql/18/bin/pg_restore --data-only --schema=fhort --table=<TAULA> \
    -f <scratchpad>/t_<TAULA>.sql /root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump
# després: awk sobre el bloc COPY, columna `instancia` localitzada a la capçalera del COPY
```

El dump conté **només l'schema `fhort`** (1346 entrades de TOC; el primer és `SCHEMA - fhort`). No hi ha `public` ni `los`.

### RESULTAT LITERAL — `fhort.models_app_basemeasurement`, 691 files

```
--- distribucio instancia (col 20) ---
    688  (buida)
      1  right
      1  left
      1  cb
--- amb GUIONET a instancia ---
0
--- distribucio capa (col 19) ---
    690  exterior
      1  folre
```

### Escombrada de TOTES les taules amb columna `instancia` del dump

| taula (schema `fhort`) | files | `instancia` no buida | **amb guionet** | valors |
|---|---|---|---|---|
| `models_app_basemeasurement` | 691 | 3 | **0** | left, right, cb |
| `pom_garmentpommap` | 1748 | 0 | **0** | — |
| `pom_itembasemeasurement` | 37 | 0 | **0** | — |
| `models_app_measurementchangelog` | 228 | 3 | **0** | left, right, cb |
| `models_app_sizecheckline` | 107 | 2 | **0** | left, right |
| `models_app_pomplacement` | 2 | 0 | **0** | — |
| `models_app_modelgradingoverride` | 0 | 0 | **0** | — |
| `fitting_gradedspec` | 1787 | 13 | **0** | cb×5, left×4, right×4 |
| `fitting_piecefittingline` | 295 | 8 | **0** | left×4, right×4 |
| `fitting_pomalert` | 0 | 0 | **0** | — |
| `pom_garmenttypepommap` / `pom_garmentgrouppommap` | *sense dades al dump* | — | — | *taules inexistents* |
| `pom_measurementinstance` | 10 | *(sense columna)* | — | el diccionari |

> ### **RESPOSTA: ZERO. Cap fila de cap taula del dump del 06/08 porta un slug compost.**
> A tot `fhort` hi havia **29 files** amb instància no buida, i **totes són slugs SIMPLES** d'un sol eix (`left`, `right`, `cb`). El slug compost és **una capacitat construïda que encara no ha produït ni una fila**.

**Contrast amb `nom_fitxa`** (la superfície que sí que va tenir el problema del guió, D-31.26): al dump només hi ha **2** `nom_fitxa` amb guionet, i **cap dels dos és el patró que `fix_sufix_instancia_guio.py` busca**:
```
1  G2s-M76CB   | inst=cb     ← el sufix CB va CONCATENAT; el guió és del codi base
1  A-FOL       | inst=(buida) ← «FOL» no és sufix d'instància
```
El `-<sufix>` de què parla la capçalera del script (`AH-L`, `AH-R`) **ja no és a les dades del 06/08**.

### Estat VIU (07/08), per contrast

| | `fhort` | `los` |
|---|---|---|
| `models_app_model` | **0** | 51 |
| `models_app_basemeasurement` | **0** | **0** |
| `pom_itembasemeasurement` | 37 (inst. no buida: 0) | 0 |
| `pom_garmentpommap` | 1748 (inst. no buida: 0) | 0 |
| `models_app_pomplacement` | 2 (inst. no buida: 0) | 0 |

**Avui no hi ha CAP fila amb instància no buida a cap schema viu.** Les 29 del dump van desaparèixer amb `v4_neteja_models.py`.

## A5.4 · Què costaria migrar al format de la llei

> **Precisió necessària abans de res.** Al sistema hi ha **DUES composicions amb DOS separadors, i la «llei» només parla d'una:**
> - **El CODI** (`nom_fitxa`, el que llegeix el fabricant): **concatenat, sense separador** — `regles.sufix_separador = ''`. `AH`+`L` → `AHL`. Això és D-31.26, i és el que `fix_sufix_instancia_guio.py` va anar a corregir a les dades.
> - **El SLUG d'instància** (la columna `instancia`): **compost amb guionet** — `regles.instancia_separador = '-'`. `left`+`relaxed` → `left-relaxed`. És el que declaren `pom/models.py:260`, `identity_views.py:97-98` i tots els `help_text`.
>
> Els dos són **decisions vives i coherents** avui, i els dos tests del front les separen explícitament (`diccionariMesures.test.js:47` declara `{sufix_separador:'', instancia_separador:'-'}`; `:55` afirma literalment `assert.notEqual(codiProposat(D,'AH',['left']), 'AH-L')`). **No he trobat cap document ni cap codi que digui que el SLUG hagi d'anar concatenat.** El que segueix és, doncs, el terreny per si la decisió és unificar els dos separadors — no la constatació que hi hagi un incompliment.

### Punts de codi que caldria tocar (NO tocats)

**Backend — 1 punt d'estructura + N de documentació:**

| # | fitxer:línia | què és |
|---|---|---|
| 1 | `/var/www/ftt-staging/backend/fhort/pom/identity_views.py:98` | **`'instancia_separador': '-'`** — l'ÚNIC punt d'estructura. Canviar-lo aquí ja canvia tot el que llegeix el diccionari |
| 2 | `/var/www/ftt-staging/backend/scripts_tmp/fix_sufix_instancia_guio.py:47,52` | `SEP_INSTANCIA = '-'` + el `split()`. Script one-shot |
| 3 | `/var/www/ftt-staging/backend/fhort/pom/models.py:260` | docstring: «es componen amb guió al slug que es desa (`'left-relaxed'`)» |
| 4 | `pom/models.py:847`, `:1240`; `models_app/models.py:741,751,892,969,1298,1483`; `fitting/models.py:240,451` | **11 `help_text`** amb l'exemple `'left-relaxed'` |
| 5 | `pom/migrations/0056_instancia_cins.py:48,53`; `fitting/migrations/0020_instancia_cins.py:42,47`; `models_app/migrations/0073_instancia_mesures.py:31` | **5 `help_text` congelats a migracions** (només text) |

⚠️ **La resta del backend NO s'ha de tocar:** és tot text opac. `pom/identitat.py` no desmunta mai la instància; les 8 `UNIQUE` de BD i els ~40 punts de còpia la tracten com a cadena. **`max_length=60` (BaseMeasurement) contra `max_length=30` (MeasurementInstance.slug)**: concatenar dos slugs pot arribar a 60 caràcters, i el camp hi cap; no cal migració d'esquema.

**Frontend — 2 punts d'estructura:**

| # | fitxer:línia | què és |
|---|---|---|
| 6 | `/var/www/ftt-staging/frontend/src/utils/diccionariMesures.js:104` | `const sepInst = (dicc) => dicc?.regles?.instancia_separador ?? '-'` — el **fallback literal** s'ha de moure amb el backend |
| 7 | `/var/www/ftt-staging/frontend/src/utils/capaInstancia.js:70` | `const SEP_INSTANCIA = '-'` — **hardcodejat, no llegeix el diccionari**. És el que trencaria si només es canviés el backend |
| 8 | `capaInstancia.js:32,85` · `diccionariMesures.js:98,104` | comentaris amb l'exemple `'left-relaxed'` |
| 9 | `/var/www/ftt-staging/frontend/src/utils/capaInstancia.test.js:46,54` · `/var/www/ftt-staging/frontend/src/utils/diccionariMesures.test.js:47,71,72,79` | **6 assercions** que codifiquen el guionet |

🔴 **El bloqueig real d'una concatenació sense separador no és cap d'aquests punts: és que `tramsInstancia` DEIXA DE SER INVERTIBLE.** Amb `-`, `'left-relaxed'.split('-')` torna els dos trams. Sense separador, `'leftrelaxed'` només es pot desmuntar contra el diccionari, per prefix, i el diccionari **té slugs amb `_` a dins (`waistband_seam`) i és extensible pel tenant** — `pom/models.py` diu explícitament que un tenant pot crear-se la seva instància. Un desmuntatge per prefix contra un catàleg obert és ambigu per construcció. Els punts a tocar serien els mateixos 9, però `tramsInstancia` (`diccionariMesures.js:98`) i `etiquetaInstancia` (`capaInstancia.js:88`) haurien de canviar d'**algorisme**, no de constant.

### El cost de dades: **BD BUIDA vs AMB DADES és, avui, la mateixa cosa**

| escenari | files a migrar |
|---|---|
| **BD viva (07/08)** | **0** — cap fila amb instància no buida a `fhort` ni `los` |
| **Dump del 06/08 restaurat** | **29** files amb instància, **totes simples** → **0 a reescriure** (un slug simple és idèntic en tots dos formats) |
| **`public`** | no aplica: `models_app`/`fitting` són apps de tenant, les taules no hi existeixen |

**Cap migració de dades és necessària en cap dels dos escenaris.** El que la fa cara no és el volum sinó **la invertibilitat**: el dia que existeixi la primera fila composta, cap script podrà desmuntar-la sense el diccionari **d'aquell moment**, i el diccionari és mutable per tenant.

---

## Què NO he pogut determinar en lectura

1. **La forma real de les dades de PROD.** Tot A5.3 parla de `staging`, schema `fhort`, dump del 06/08. Sense SSH a PROD (v. `ftt-prod-estat-via-dump`) no puc dir quantes files compostes hi ha allà. El camí per fer-ho més tard, **sense tocar cap BD**:
   ```bash
   /usr/lib/postgresql/18/bin/pg_restore --data-only --schema=<SCHEMA> \
       --table=models_app_basemeasurement -f /tmp/bm.sql <DUMP_PROD>
   awk '/^COPY .*models_app_basemeasurement/{f=1;next} /^\\\.$/{f=0} f' /tmp/bm.sql \
     | awk -F'\t' '$20 ~ /-/' | wc -l     # col 20 = `instancia`; VERIFICAR-HO a la capçalera COPY
   ```
   **Cal recomptar la posició de la columna a la capçalera `COPY … (…) FROM stdin;`** de cada dump: no és estable entre versions d'esquema.
   *(Per si la restauració es vol fer igualment: `createdb -T template0 tmp_v4 && pg_restore -d tmp_v4 --no-owner --no-privileges <dump>` a la instància PG18. **NO ho he fet i no ho recomano com a pas necessari:** l'extracció a fitxer ja dona la resposta i no toca cap servidor.)*

2. **Si `POMMasterViewSet` és realment accessible sense gate a producció.** He llegit que `permission_classes = [IsAuthenticated]` i que no hi ha `get_permissions`, però **no he executat cap petició HTTP**. Un middleware, un `DEFAULT_PERMISSION_CLASSES` o un router de nivell superior podrien afegir-hi una comporta que la lectura del fitxer no veu.

3. **Si els 396 `POMMaster` de `fhort` es corresponen 1:1 amb els 274 `POMGlobal`.** El comentari de `bootstrap_tenant.py:154` diu «126 distints / 170 files», que és d'una foto anterior. Els números vius (396 vs 274) diuen que hi ha **almenys 122 POMMaster tenant-only o duplicats**, però no he fet el `GROUP BY pom_global_id` per confirmar-ne la distribució: era fora del brief i és una consulta que val la pena fer explícitament.

4. **Quin percentatge de les ~110 lectures «no ▸ join» és realment sensible al contingut del catàleg.** Un `select_related('pom')` sobre línies que ja existeixen no es veu afectat per una sembra nova; un `find_pom_master` que itera tot el catàleg, sí. He classificat el mecanisme d'accés, no l'impacte funcional d'un catàleg v4.

5. **Si la sembra v4 pretén tocar `POMGlobal`, `POMMaster` o els dos.** Tota la lectura d'A3.b canvia de pes segons quina: `replace_pom_catalog.py` (l'únic que fa `.all().delete()` de `POMGlobal`) corre per defecte sobre **`public`**, on avui hi ha 125 `POMGlobal` i **0 `POMMaster`** — o sigui que un reseed de `public` no toca cap POMMaster de ningú. Un reseed del **tenant** és una altra conversa.

6. **Si `pom_garmenttypepommap`/`pom_garmentgrouppommap` (U2) han d'existir abans de la sembra.** Són a `POMMaster._meta.related_objects` (Django les coneix) però **no existeixen a BD a cap dels tres schemes**. Qualsevol codi que recorri `related_objects` i toqui l'accessor —com `cataleg_views._cens_relacions:37`— **peta amb `ProgrammingError`** en trobar-les. No ho he provat.
