# DIAGNOSI — Biblioteca tècnica del Customer (nomenclatures POM pròpies + grading per client + toleràncies)

Data: **2026-07-08** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
Abast: terreny real per a una "biblioteca tècnica del Customer" com a **font de sembra addicional per client** (canònic → item → biblioteca client → model), projecte paral·lel al mòdul Comercial, dins el nucli tècnic (`pom/` + `tasks.Customer`). NO és una capa d'àlies global.
Convenció: `fitxer:línia` (relatiu a `backend/fhort/`, tret dels blocs UI que són relatius a l'arrel del repo). `"NO EXISTEIX"` = confirmat absent al codi, no especulat. `💡 PROPOSTA (a validar)` = disseny, decisió humana (Patró C).
Germans vigents consultats: `DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08.md`, `DIAGNOSI_RUN_CLIENT_VINCULACIO_2026-07-08.md`, `DIAGNOSI_IMPORT_RUN_CLIENT_2026-07-07.md`.

---

## Resum executiu (les 7 conclusions que desbloquegen la decisió)

1. **La "biblioteca del client" JA té esquelet al codi: `CustomerPOMAlias`** (`pom/models.py:236`). És un model **per-customer** amb unicitat `(customer, client_code)` → `POMMaster`, i **el matcher JA el consumeix** com a estratègia (a) de prioritat HIGH (`models_app/extraction_views.py:543-549`). Però **l'import MAI l'escriu**: els únics writes són backfills de migració (`0031`, `0032`). És una taula de sembra **de només-lectura a runtime**. Aquest és el forat central de la biblioteca proposada.

2. **`ClientMesuraPerfil` NO és aquesta capa** (`pom/models.py:624`). És estadística Welford online (`n_mostres/mitjana/m2_acum/desviacio`) escrita al tancar fitting; **viva per escriptura, fòssil per lectura** (cap serializer/view/frontend la consumeix). No reaprofitable com a biblioteca de nomenclatura; sí com a precedent del patró clau-per-`codi_client`-string.

3. **La nomenclatura del client viu en TRES llocs, no un.** Fila del model `BaseMeasurement.nom_fitxa` (codi cru literal, `models_app/models.py:499`), catàleg `POMMaster.codi_client`/`nom_client` (`pom/models.py:159-160`), i `CustomerPOMAlias`. La premissa "viu al model i prou" és **parcialment certa**: el `nom_fitxa` hi viu, però el mapping resolt reutilitzable hauria de viure a `CustomerPOMAlias`, que l'import no alimenta.

4. **Els "ganxos customer" de grading estan a mitges i NO són de juny.** `GradingRuleSet.customer` **EXISTEIX** (`pom/models.py:502`) però afegit **avui 2026-07-08** (migració `0029`, commit `debf903`) com a FK d'**atribució de nomenclatura**, NO com a eix de graduació: no entra a cap `unique_together` ni a cap match (`pom/grading_utils.py:108-113`, `308-315` no el llegeixen). **`SizingProfile.customer` NO EXISTEIX** (només acord de xat).

5. **El precedent de FK cross-app `pom → tasks.Customer` ja està establert** amb patró `db_constraint=False` (SHARED `pom` → tenant-only `tasks.Customer`): `CustomerPOMAlias.customer` (`pom/models.py:248`) i `GradingRuleSet.customer` (`pom/models.py:502`). No cal inventar direcció; la biblioteca s'ancora en aquest patró.

6. **Toleràncies = copy-at-the-moment `POMMaster.tolerancia_default_*` → `BaseMeasurement.tolerancia_*`, sense cap eix customer** (`pom/models.py:167-168` → `models_app/models.py:495-496`). Una capa per-customer s'insereix als mateixos ~5 punts de còpia, sense trencar el patró snapshot.

7. **UI: pas modal → fitxa és curt i té precedent.** `Customers.jsx` és llista+modal amb **2 tabs locals** (`dades`/`comercial`) i **sense ruta `:id`**; `ModelSheet` és fitxa-per-ruta amb `?tab=` i 8 tabs. El precedent fitxa-per-ruta també viu a Comercial. La migració a fitxa amb 3 tabs (Dades/Tècnic/Comercial) reaprofita els camps de M2 tal qual; l'únic tab nou de contingut és **Tècnic**.

> ⚠️ **Avís transversal de comentaris obsolets:** TRES llocs afirmen "el matcher encara NO llegeix els àlies (N3)" (`pom/models.py:241`, `models_app/extraction_views.py:514`, `pom/migrations/0031_...py:6`) però el codi SÍ els llegeix (`extraction_views.py:543-549`). Qualsevol treball sobre la biblioteca ha de partir del comportament real, no d'aquests comentaris.

---

## BLOC 1 — `pom.ClientMesuraPerfil`: VIU o FÒSSIL? (Pregunta 1)

**Definició** — `pom/models.py:624`, docstring "Online Welford statistic per (codi_client, garment_type, POM, size)". Camps:

| Camp | Línia | Tipus | Nota |
|---|---|---|---|
| `client` | 636 | FK `tenants.Client` (null, CASCADE) | legacy, nivell tenant |
| `codi_client` | 640 | CharField(80) default='' | clau real Sprint 5B.3 (de `Model.codi_client`) |
| `garment_type` | 641 | FK `GarmentType` | |
| `pom` | 642 | FK `POMMaster` (PROTECT) | |
| `talla` | 643 | CharField(20) | |
| `n_mostres` / `mitjana` / `m2_acum` / `desviacio` | 644-647 | Int/Float | acumuladors Welford |
| `darrera_actualitzacio` | 648 | auto_now | |

`unique_together = ('codi_client','garment_type','pom','talla')` (`pom/models.py:650`).
**No té FK a `tasks.Customer` ni a `models_app.Model`** — clau per `codi_client` string (còpia de `Model.codi_client`), FK a `POMMaster` sí.

**Escriptura (viva):** `pom/services.py:304` `update_client_profile(...)` fa `get_or_create` (`:327`) + Welford (`:343-356`). **Únic caller:** `fitting/services.py:427-435`, dins el **tancament de fitting** (bucle sobre línies consolidades, `:421-435`), en try/except que no trenca el flux (`:436`).

**Lectura (fòssil):** grep complet → **cap lector a runtime**. No hi ha serializer/view/url/admin de `pom` que l'exposi (NO EXISTEIX), ni referència al frontend (NO EXISTEIX). `reseed_tenant_fhort.py:226,233` només l'importa per **esborrar-la**. `fitting/models.py:390` i `tasks/services_i.py:33` només la citen com a *patró* replicat, no la consumeixen.

**Migracions:** creada a `0003_sprint3_4_grading_models.py:16` (2026-05-25); re-clau a `codi_client` a `0012_...` (2026-05-30). Cap migració posterior la toca.

> **Veredicte 1: FÒSSIL FUNCIONAL — semi-viva.** És una capa d'**estadística Welford**, no de nomenclatura. Té camí d'escriptura actiu (fitting) però **zero lectors**: les dades s'acumulen i mai es llegeixen. **No reaprofitable** com a biblioteca del client. Aprofitable NOMÉS com a *precedent de patró* (clau per `codi_client`-string + FK a `POMMaster`). La nomenclatura del client la porta un altre model: `CustomerPOMAlias`.

---

## BLOC 2 — Nomenclatura del client al model AVUI + cadena de sembra + què es perd (Pregunta 2)

**Camp exacte al model:** `BaseMeasurement.nom_fitxa` — `models_app/models.py:499-503`, `CharField(max_length=20, blank, default='')`, help_text "Nomenclatura de la fletxa al croquis (ex: A, 1, CH)". És **la "nomenclatura editable de la sessió 2026-06-24"**, afegida a `models_app/migrations/0011_basemeasurement_nom_fitxa_...py:15`. Editable des de la UI (`models_app/views.py:1299-1300`, serialitzat a `models_app/serializers.py:139`).
**NO EXISTEIXEN** a `BaseMeasurement`: `codi_client`, `nom_original`, `label`, `codi_pom_client`. La nomenclatura de *codi/descripció* del client viu al catàleg: `POMMaster.codi_client` (`pom/models.py:159`) i `nom_client` (`pom/models.py:160`); `BaseMeasurement` hi apunta per FK `pom` (`models_app/models.py:476`) i **no en copia el codi** (només copia `nom_fitxa`).

**Cadena de sembra a l'import** (codi cru del client = `codi_fitxa`):
1. `models_app/extraction_views.py:714` / `:862` — `import_customer = session.model.customer`.
2. `:717` / `:868` — `find_pom_master(codi_fitxa, descripcio, customer=import_customer)`.
3. Persistència W5 — `:1337` `BaseMeasurement.objects.update_or_create(model, pom=pm, defaults=...)` amb `nom_fitxa = codi_fitxa` (`:1325`, **el codi cru "B"/"CHEST" es persisteix literalment**) i FK `pom = pm` (POMMaster resolt).
4. Si no hi ha POM al catàleg: `:969-971` `POMMaster.get_or_create(codi_client=codi_fitxa, ...)` crea un POM el `codi_client` del qual és el codi cru.

**Què es PERD:** existeix la taula reutilitzable per-client `CustomerPOMAlias` (`pom/models.py:236`), **però l'import NO l'escriu mai** — els únics writes a tot el backend són backfills de migració (`pom/migrations/0031_...py:52`, `0032_...py:58`); no hi ha cap `CustomerPOMAlias.objects.create/get_or_create` a cap view/service (confirmat per absència). Per tant un mapping resolt per descripció/sinònim/fallback (p.ex. "B"→CHEST) **NO es persisteix com a àlies reutilitzable**. El que queda és local al model: `BaseMeasurement.nom_fitxa` + FK `pom`. **La propera importació del mateix client es re-resol des de zero.** No hi ha auto-aprenentatge d'àlies.

**Capa d'àlies global:** **NO EXISTEIX** cap capa tenant-wide. L'únic model d'àlies és `CustomerPOMAlias`, sempre scoped a `tasks.Customer` (per-client, no global). La premissa "CAP capa d'àlies global viva" és **correcta**; el matís és que SÍ hi ha una capa **per-client** viva i consumida en lectura.

> **Veredicte 2: cal tancar el llaç d'escriptura.** La nomenclatura del client viu (a) al model (`nom_fitxa`, editable) i (b) al catàleg (`POMMaster.codi_client/nom_client`), però el mapping **resolt** no es capitalitza. La "biblioteca del client" com a **font de sembra reutilitzable** ja té contenidor (`CustomerPOMAlias`); li falta el camí d'escriptura des de l'import. 💡 PROPOSTA (a validar): a W5, després de resoldre `find_pom_master` amb confiança HIGH/MEDIUM, fer `CustomerPOMAlias.get_or_create(customer, client_code=codi_fitxa, defaults={pom, client_description, origen='IMPORT'})` per auto-aprendre l'àlies i que la propera importació resolgui per estratègia (a).

---

## BLOC 3 — `GradingRuleSet` + `SizingProfile`: eixos i ganxos customer (Pregunta 3)

**`GradingRuleSet`** (`pom/models.py:488-556`). Eixos de discriminació vius: `targets` M2M (`:521`, autoritatiu; `target` FK és legacy `:516`) + `garment_group` (`:490`) + `size_system` (`:497`) + `construction` (`:528`) + `fit_type` (`:533`). Versionat: `parent_version`/`version_number` (`:540-546`). **`Meta` sense cap `unique_together`/constraint** (`:551-553`).
Ganxo customer: **`customer` FK `tasks.Customer` SÍ EXISTEIX** — `pom/models.py:502-504` (null, `SET_NULL`, `db_constraint=False`). Comentari `:499-501`: "N1 — client propietari de la graduació (àlies de nomenclatura). FK REAL a Customer (decisió CTO), nullable i additiu." **Afegit avui 2026-07-08** (migració `0029_gradingruleset_customer_customerpomalias.py:15-19`, commit `debf903`; backfill `0030`).

**`SizingProfile`** (`pom/models.py:798-831`). Eixos: `target` (`:803`) + `garment_type` (`:805`) + `construction` (`:807`) + `fit_type` (`:809`) + `size_system` (`:811`); FK directa a `GradingRuleSet` (`:813`). `unique_together = ('size_system','target','construction','fit_type')` (`pom/migrations/0019_...py:15`). Ganxo customer: **NO EXISTEIX** (cap camp/FK/migració/comentari).

**Resolució avui (cega al customer):** via canònica `cerca_canonic_equivalent` (`pom/grading_utils.py:81`, match `:108-113`: `is_system_default + size_system + construction + fit_type + targets`); via custom `derive_grading_rule_set` (`:226`, candidat `:308-315`: `size_system + garment_group + target + construction + fit_type`). El ViewSet filtra per `['actiu','garment_group','size_system']` (`pom/views.py:149`). **Cap via llegeix `customer`** (confirmat: grep customer als fitxers de resolució → cap match rellevant).

> **Veredicte 3: ganxo mig-fet + acord no implementat.** `GradingRuleSet.customer` existeix com a **esquema d'atribució de nomenclatura**, NO com a eix de graduació (no discrimina cap match, no és a cap `unique_together`). `SizingProfile.customer` és **només acord de xat — NO EXISTEIX**. La precondició "grading rule set és per Customer" **no està implementada com a eix**; on ancorar l'eix customer (si es vol) seria dins `cerca_canonic_equivalent`/`derive_grading_rule_set` + `unique_together`, decisió pendent (Patró C).

---

## BLOC 4 — `Customer` (tasks): relacions, `codi_global`, precedent FK cross-app (Pregunta 4)

**`Customer`** — `tasks/models.py:176`. Camps clau: `codi` `CharField(max_length=3, unique=True)` (`:182`, **codi canònic únic**, font del prefix del `codi_intern` dels models), `nom` (`:183`), `active` (`:184`), `is_self` (`:185`), `codi_global` (`:189`), `logo` (`:191`); bloc comercial B1 (`:196-209`) i fiscal B3a (`:225-229`). **Única FK sortint:** `payment_terms → commerce.PaymentTerms` (`:229`). Customer **no** té FK cap a `pom` ni `models_app`.

**`codi_global`:** `CharField(max_length=3, null=True, blank=True)` (`:189`), **NO unique**. **Generació: NO EXISTEIX** — placeholder declarat al propi codi (`:187-188`: "Ganxo per al registre global de codis del backoffice futur… Placeholder sense lògica en aquest sprint"). Cap escriptura fora de la migració `0019_customer.py`.

**Qui apunta a `tasks.Customer` (FK inverses existents):**

| Origen (app) | fitxer:línia | related_name | on_delete |
|---|---|---|---|
| `commerce` | `commerce/models_base.py:42` | — | PROTECT |
| **`pom.CustomerPOMAlias`** | `pom/models.py:248` | `pom_aliases` | PROTECT, `db_constraint=False` |
| **`pom.GradingRuleSet`** | `pom/models.py:502` | `grading_rule_sets` | SET_NULL, `db_constraint=False` |
| `models_app.Model` | `models_app/models.py:125` | (customer) | PROTECT |
| `models_app` (comptador seq.) | `models_app/models.py:670` | — | PROTECT |
| `models_app.BulkImport` | `models_app/models.py:696` | — | PROTECT |

**Precedent cross-app `pom → tasks`: EXISTEIX i és el patró establert.** Justificació al codi (`pom/models.py:245-246`): "`pom` és SHARED+TENANT però `tasks.Customer` és tenant-only → la FK creua schemas; PROTECT a nivell ORM, sense constraint de BD" → totes dues usen `db_constraint=False`. Hi ha acoblament bidireccional consolidat (també `tasks → pom.GarmentType` `tasks/models.py:272`; `pom → tasks.GarmentTypeItem` `pom/models.py:423,462`) i dependències declarades als migrations en ambdós sentits (p.ex. `pom/migrations/0029_...py:11 → ('tasks','0034_...')`).
El **Model** ja té FK real a Customer (`models_app/models.py:125`, PROTECT; camp denormalitzat deprecat `codi_client = customer.codi` a `:120`).

> **Veredicte 4: terreny llest.** La biblioteca no necessita inventar direcció de FK: **`pom → tasks.Customer` amb `db_constraint=False`** és el patró viu, ja usat dues vegades (àlies + grading). `codi_global` és un ganxo buit disponible. No cal tocar `Customer` per a la biblioteca; sí caldria (si es vol registre global) implementar la generació de `codi_global`, avui inexistent.

---

## BLOC 5 — Matching a l'import: `find_pom_master` + `_POM_SYNONYMS` (Pregunta 5)

**Una sola implementació:** `models_app/extraction_views.py:518` `find_pom_master(code, description, customer=None)`. `pom/size_map_views.py` **la importa** i la crida (`:273→303`, `:446→539`), no la duplica.

**Ordre EXACTE de resolució:**
1. `:543-549` **(a) ÀLIES per client** — `CustomerPOMAlias.filter(customer, client_code__iexact)` vs `code` i `desc` → `alias_match` **HIGH**. *Requereix `customer is not None`; si None, se salta tota la capa.*
2. `:553-558` sinònim → `POMMaster.nom_client` → `synonym_match` HIGH.
3. `:559-564` sinònim → `POMGlobal.nom_en` → `synonym_global_match` HIGH.
4. `:567-573` descripció vs `nom_client` → `exact_description` HIGH / `description_match` MEDIUM.
5. `:576-586` descripció vs `POMGlobal.nom_en` → `global_exact` HIGH / `global_name_match` MEDIUM.
6. `:587-588` `code == abbreviation` → `abbreviation_match` HIGH.
7. `:591-597` numèric pur + 'lining' → `numeric_lining_match` MEDIUM.
8. `:602-605` **FALLBACK** `codi_client__iexact` → `legacy_code_match` **LOW** (degradat des de 1a estratègia, `:599-601`).
9. `:611-617` **FALLBACK** root de lletres inicials (D1→D), exclou `LLETRA.NÚMERO` → `root_code_match` **LOW**.
10. `:619` `no_match`.
Umbral d'auto-vinculació: `pom/size_map_views.py:26` `_POM_AUTOLINK_CONF=('HIGH','MEDIUM')` → **LOW (8,9) mai auto-vincula**.

**`_POM_SYNONYMS`** — `models_app/extraction_views.py:495-515`. `dict` literal a nivell de mòdul, **hardcoded tenant-wide** (mateix objecte Python per a tots els clients i schemas), ~14 entrades. NO es carrega de BD.

**Migració `0031`** — migra `BROWNIE_ALIASES` (8 entrades) de `_POM_SYNONYMS` cap a `CustomerPOMAlias`, atribuïts al customer `codi='BRW'`, `origen='MIGRACIO'` (`0031_...py:16-26,36,55`). Docstring: "era nomenclatura de CLIENT disfressada de sinònim canònic". `0032` migra codis `LLETRA.NÚMERO` de `POMMaster.codi_client` cap a `CustomerPOMAlias` resolent el customer via `origen_import`.

**Tenant-wide vs per-customer (evidència de col·lisió):** el mateix codi cru resol a POMs diferents segons context:
- `'collar width'`: `_POM_SYNONYMS:505`→`collar width` (genèric) vs BRW `0031:21`→`neck tie length`.
- `'front armhole curve'`: `:502`→`armhole curve` vs BRW `0031:20`→`armhole`.
- Col·lisió intra-client documentada: Losan `H.11 sleeve opening` vs `H.16 cuff opening` (`pom/models.py:239-240`) → raó de la unicitat `(customer, client_code)`.

> **Veredicte 5: la frontera ja està traçada, però mig-migrada.** Els **canònics universals** (renaming semàntic estàndard) han de romandre a `_POM_SYNONYMS` tenant-wide; la **nomenclatura de client** (col·lisions posicionals/semàntiques) pertany a `CustomerPOMAlias` per-customer, i l'estratègia (a) ja la prioritza. La migració d'aquesta frontera està **iniciada** (BRW + dotted-codes) però **incompleta** per a la resta de clients, i el llaç d'auto-escriptura des de l'import segueix obert (vegeu Bloc 2). Els comentaris "matcher NO llegeix àlies (N3)" són **obsolets** (3 llocs).

---

## BLOC 6 — Toleràncies: copy-at-the-moment (Pregunta 6)

**Origen** (`POMMaster`, `pom/models.py`): `tolerancia_default_minus` (`:167`, default 0.6), `tolerancia_default_plus` (`:168`). Comentari `:165-166`: "Copied onto BaseMeasurement… copy-at-the-moment, like base_value_cm — **not a live reference**."
**Destí** (`BaseMeasurement`, `models_app/models.py`): `tolerancia_minus` (`:495`), `tolerancia_plus` (`:496`), nullable; comentari `:492-493`: "copied from the catalogue POM at pour time. NULL for pre-existing; consumers fall back to 0.6".

**Punts de còpia (snapshot per-valor):** `models_app/views.py:837-838`, `:952-953`, `:1317-1318`; `models_app/tech_sheet_views.py:368-369`; fallback al wizard `pom/wizard_views.py:200-202`. Via import és asimètrica: `models_app/extraction_views.py:1334-1336` només escriu si el document en porta, si no → NULL → fallback catàleg.
**Consumidors amb fallback** (lectura): `pom/s10_views.py:52-53`, `pom/s8_views.py:181-182`, `models_app/serializers_size_check.py:95-96`, `models_app/views.py:1836-1837` (fallback a `pom.tolerancia_default_*`). Un canvi posterior a `POMMaster.tolerancia_default_*` **no es propaga** a BaseMeasurement ja abocades (no hi ha signal ni re-lectura).
**Eix customer a toleràncies: NO EXISTEIX** — s'esbiaixen per POM (catàleg), per Model (BaseMeasurement) i per `FabricType` (`pom/models.py:752-753`), mai per Customer. `ItemBaseMeasurement.tol_minus/plus` (`pom/models.py:469-470`) també cauen al mateix default del catàleg.

> **Veredicte 6: patró snapshot net, punt d'inserció clar.** Una capa de toleràncies per-customer no trencaria la còpia si s'insereix **abans** del pour: 💡 PROPOSTA (a validar) — resoldre `tol_minus/plus` amb prioritat `customer-override → POMMaster.tolerancia_default_*` als mateixos ~5 call-sites (o al wizard `:200-202`, que ja és el punt de fallback centralitzat), mantenint el snapshot cap a `BaseMeasurement`. El contenidor natural de l'override seria un camp a `CustomerPOMAlias` o una taula germana `(customer, pom) → tol_*`; decisió pendent (Patró C).

---

## BLOC 7 — UI: modal → fitxa amb 3 tabs (Pregunta 7)

**Estat actual** (rutes relatives a l'arrel del repo):
- `frontend/src/pages/Customers.jsx` = **llista (Table) + modal**, sense fitxa. Modal via `useState(null)` (`:29`), obert amb `{mode:'edit'|'create'}` (`:110,125`). Llista `customers.list({page_size:500})` (`:54`). Upload de logo fora del modal (`:42`). **NO existeix ruta `/clients/:id`** (`App.jsx:258` és només la llista).
- `frontend/src/components/CustomerModal.jsx` = **JA té 2 tabs locals** (post-M2): `tab` per `useState('dades')` (`:18`), `TabBar` intern (`:160-172`), tabs `dades` (`:75-86`: `codi`, `nom`, `active`) i `comercial`/fiscal (`:88-155`: `nif`, adreça, `email_facturacio`, `tax_regime`, `vat_number`, `payment_method`, `payment_terms`, `condicions_pagament`, `descompte_pct`, `persona/telefon_contacte`). Submit PATCH/POST a `/api/v1/customers/` (`:60`). Components reutilitzables `Field`/`Row`/`TabBar`.
- `frontend/src/pages/ModelSheet.jsx` = **fitxa-per-ruta** de referència. Layout capçalera + barra de tabs + cos (`:337,343-366,376-532`). Tabs = **estat local sincronitzat amb `?tab=`** (`:92,95,101`; clic fa `setActiveTab` sense reescriure URL, `:350`). 8 tabs (`:23`). Càrrega **mixta**: base eager (`Promise.all`, `:132-147`) + tabs pesats lazy (component propi que carrega en renderitzar-se). Ruta `models/:id` (`App.jsx:233`) + variants `defaultTab`.
- **Precedent fitxa-per-ruta també a Comercial:** `comercial/productes/:id` `ProductDetail`, `ofertes/:id` `QuoteDetail`, `comandes/:id` `OrderDetail` (`App.jsx:261,264,269`).

**Reaprofitament de M2 per a fitxa Dades/Tècnic/Comercial:**
- **Tab Dades**: `codi`, `nom`, `active` (`CustomerModal.jsx:75-86`) + identitat/fiscalitat `nif`, adreça, `email_facturacio` (`:89-114`). Reaprofitable tal qual.
- **Tab Comercial**: ja existeix com a tab `comercial` (`:116-154`), inclosa la càrrega de `paymentTerms` (`:41-45`). Reaprofitable tal qual.
- **Tab Tècnic = NOU de contingut**: el modal **no té cap camp tècnic** (NO EXISTEIX). Font natural: endpoint ja definit `techSheetTemplate` → `/api/v1/customers/${id}/tech-sheet-template/` (`endpoints.js:220-222`, TS-3), avui **no consumit** des del modal. Aquí també aniria la biblioteca del client (àlies `CustomerPOMAlias` + toleràncies/grading per-customer si es materialitzen) i el logo (avui acció de llista, `Customers.jsx:42`).

> **Veredicte 7: pas curt, ben pautat.** El contingut de M2 (tabs `dades` + `comercial`) es transporta gairebé literal a una fitxa; només cal (i) crear ruta `/clients/:id` (precedent a Comercial i ModelSheet), (ii) adoptar la mecànica de tabs de ModelSheet (`?tab=` + càrrega lazy per tab), (iii) **omplir de zero el tab Tècnic**, que és on viu la biblioteca. 💡 PROPOSTA (a validar): reusar `Field`/`Row` del CustomerModal i el patró `ModelSheetHeader`+barra de tabs; dimensionar el tab Tècnic com el veritable nou desenvolupament.

---

## TAULA FINAL de riscos i estat (per al CTO)

| # | Element | Estat | Risc / nota |
|---|---|---|---|
| R1 | `CustomerPOMAlias` (contenidor biblioteca) | **EXISTEIX**, llegit pel matcher (HIGH) | **Import no l'escriu** (només backfill migració) → sembra no s'autoalimenta; forat central |
| R2 | `ClientMesuraPerfil` | Semi-viu (escriu fitting, **cap lector**) | No és biblioteca de nomenclatura; risc de confondre'l amb la capa objectiu |
| R3 | Nomenclatura del client | Dispersa: `nom_fitxa` (model) + `POMMaster.codi_client/nom_client` (catàleg) + `CustomerPOMAlias` | Mapping resolt es perd en acabar import; re-resolució des de zero |
| R4 | `GradingRuleSet.customer` | **EXISTEIX** (avui, additiu) però **no és eix de match** | Atribució ≠ graduació per client; premissa "grading per Customer" no implementada com a eix |
| R5 | `SizingProfile.customer` | **NO EXISTEIX** | Només acord de xat; cal decisió si es vol eix customer al perfil |
| R6 | FK cross-app `pom→tasks.Customer` | **EXISTEIX** (patró `db_constraint=False`) | Terreny llest; sense constraint de BD (integritat a nivell ORM/PROTECT) |
| R7 | `Customer.codi_global` | Camp EXISTEIX, **generació NO EXISTEIX** | Ganxo buit; registre global futur sense lògica |
| R8 | `_POM_SYNONYMS` | Hardcoded tenant-wide (~14) | Frontera universal↔per-client mig-migrada (BRW+dotted fets, resta no); col·lisions reals documentades |
| R9 | Toleràncies | Copy-at-the-moment, **sense eix customer** | Inserció d'override per-customer viable als ~5 punts de còpia sense trencar snapshot |
| R10 | Comentaris "N3: matcher no llegeix àlies" | **OBSOLETS** (3 llocs) contradiuen el codi | Risc de decidir sobre premissa falsa; el matcher SÍ llegeix àlies |
| R11 | UI Customers | Llista+modal, 2 tabs locals, **sense ruta `:id`** | Pas a fitxa curt (precedent ModelSheet + Comercial); tab Tècnic és l'únic contingut nou |

---

### Nota de mètode
Diagnosi Patró A, read-only estricte: cap escriptura de codi, cap migració, cap comanda d'estat. Totes les afirmacions ancorades a `fitxer:línia` verificat; els blocs marcats `💡 PROPOSTA (a validar)` i la darrera columna de risc són material per a la decisió humana (Patró C), no conclusions de fet.
