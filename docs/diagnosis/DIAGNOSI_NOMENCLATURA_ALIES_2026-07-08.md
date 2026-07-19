# DIAGNOSI — Nomenclatura de client vs sinònim canònic: taula d'àlies i final del codi_client al matcher

**Data:** 2026-07-08 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
**Equip:** 1 sessió orquestra · BD (fhort) + lectura de codi + 2 agents read-only (radi de `codi_client` · commerce 404).
**Substrat:** `DIAGNOSI_POM_RESOLUCIO_RUN_2026-07-08.md` (vigent) · matcher ja reordenat (`40759b2`+`c2b19bd`).
**Decisions de disseny ja preses (Agus, Patró C):** (a) la taula d'àlies viu al CLIENT `(customer, pom, client_code, client_description)`; (b) el GradingRuleSet es queda on és, només hi afegim un camp de CLIENT propietari; (c) objectiu final: eliminar `codi_client` i el root-prefix del matcher.

> Convenció: `fitxer:línia` relatiu a l'arrel (backend a `backend/`). **"NO EXISTEIX" = confirmat absent al codi.**
> Evidència de domini: BERG (adult) i Kids de LOSAN (customer `LOS`). Nomenclatura estable per client; regla variable per target/GTI.

---

## 0. Resum executiu (director)

1. **Avui `POMMaster.codi_client` barreja tres coses en un sol camp:** (a) abreviatura canònica
   (`SH`, `AH DEP`, `SL OP`), (b) nomenclatura de client baked-in (24 codis `LLETRA.NÚMERO`:
   `A.1`, `E.8`, `K.2`, `L.4`, `S.10`, `*-M79`…), i (c) codis de mesura pròpiament dits. La
   confusió que arrossega el matcher neix aquí.
2. **La separació és VIABLE i de baix risc per a la identitat del catàleg:** 21 de 22 codis
   `LLETRA.NÚMERO` es resolen igual per la seva descripció (`nom_client`, `exact_description` HIGH)
   sense el codi; només `A.2 "BACK WIDTH"` esdevé ambigu (BLOC 5). El risc real NO és el catàleg
   sinó el **radi de consumidors** de `codi_client` (matcher + 3 CSV + propietat `pom_code` + molts
   serializers amb *fallback*), que cal cobrir amb un codi canònic alternatiu abans d'eliminar-lo.
3. **`_POM_SYNONYMS` JA és una taula d'àlies disfressada:** viu en CODI (dict a
   `extraction_views.py:495-522`), ~14 claus, i inclou un bloc explícit **"Brownie positional
   POMs"** — nomenclatura del customer `BRW` incrustada com si fos sinònim EN. És exactament el
   patró que el disseny vol treure del codi i portar a dades per-client.
4. **El client propietari ja existeix, però penjant i incomplet:** `SizeSystem.customer_codi`
   (`CharField(3)`, NO FK) el porten només **4 de 20** size systems (tots `LOS`); `GradingRuleSet`
   **NO té cap camp de client** (BLOC 3). "LOSAN IBERIA SA" surt de `Customer(codi='LOS').nom` via
   `_customer_label`. El `Customer` (codi 3 chars, unique) és l'àncora natural de `CustomerPOMAlias`.
5. **`pendents_vincular` (migració 0028) pot ser la safata del bucle d'aprenentatge**, però avui és
   una **llista plana de codis** (BLOC 6): cal enriquir-la a `{client_code, client_description,
   suggested_pom, confidence}` perquè "confirmar match → registrar àlies" tanqui el cercle.
6. **El bloqueig de col·lisió (`378df5f`) NO s'ha de relaxar** (BLOC 8): la seva feina —una sola
   `GradingRule` per `(rule_set, pom)`— segueix sent correcta. Els àlies **redueixen** les seves
   activacions perquè eliminen les col·lisions FALSES del *contains* many-to-one (l'origen de
   "H.6 ja vinculat per un altre codi", BLOC 9).

**Recomanació de rumb (💡):** és viable. Ordre: (1) `CustomerPOMAlias` + FK client al `GradingRuleSet`
· (2) matcher: àlies exacte `(customer, client_code)` primer, descripció després, `codi_client`/root
com a *fallback* transitori marcat LOW · (3) bucle d'aprenentatge sobre `pendents_vincular` enriquit ·
(4) migració de dades i, només al final, retirada de `codi_client` del matcher. Detall a §Veredicte.

---

## BLOC 1 — `POMMaster.codi_client`: dades, escriptors, lectors [Q1]

**Dades (fhort):** 170 POMMaster (168 actius) · **45 amb `pom_global=NULL`** · **28 `pendent_revisio`**
· **43 amb `origen_import`** · **24 codis `LLETRA.NÚMERO`** (`A.1 A.2 C.14-M79 D.11-M79 E.8 E.8-2 K.2
L.4 L.5 O.*-M79 S.10 S.56 T.1 T.2 T.5 V.12 V.13-M79 V.14-M79`) · **cap col·lisió case-insensitive
avui**. **`POMMaster` NO té cap FK a `Customer`**: `codi_client` és una cadena nua; l'origen només es
pot inferir per `origen_import` (token de sessió d'import).

**⚠️ Trampa de noms:** `codi_client` existeix en 5 models (`Model`, `GarmentType`, `ClientMesuraPerfil`,
`ModelConsumptionEvent`, `POMMaster`). Aquest bloc parla NOMÉS de `POMMaster.codi_client`
([pom/models.py:159](../../backend/fhort/pom/models.py#L159)).

**WRITE (8 punts):**
- `pom/wizard_views.py:356` — `crear-tenant/` (create) · `:386` — PATCH `nomenclatura/`.
- `models_app/extraction_views.py:952` — import `get_or_create(pom_global=None, codi_client=…)`.
- **`pom/views.py:44` — `POMMasterViewSet` (`ModelViewSet`, `fields='__all__'`, `IsAuthenticated`
  sense override d'escriptura) → `codi_client` és WRITABLE via REST POST/PUT/PATCH** (forat de
  governança, ja anotat a la diagnosi anterior).
- Seeds: `extend_pom_catalog.py:198` · `reseed_tenant_fhort.py:261` · `seed_baby_poms.py:263` (tots
  `codi_client = pg.abbreviation or pg.codi`).

**MATCH (lògica, no display):** `find_pom_master` S1 exacte (`extraction_views.py:541`) i S6 root
(`:604`); camí Library `:1121`; acció xat "AFEGIR" `models_app/views.py:1307`; OR-queries
`s2_views.py:246` i `s4_views.py:62`; cerca wizard `wizard_views.py:127` (`icontains`).

**EXPORT/PDF:** **3 CSV** el treuen via `_pom_codi()` (`pom/s8_views.py:30`, columnes a `:78/:143/:208`).
**El PDF `.ftt` (fitxa tècnica) NO usa `codi_client`** — usa el codi GLOBAL (`pom_code_global`,
`services_ftt_document.py:100-104`). **El PDF comercial NO referencia POMs** (NO EXISTEIX).
Molts serializers/JSON l'exposen com a *fallback* (`pom/serializers.py:69,81,120,145…`,
`models_app/serializers.py:128`, `fitting/serializers.py:39`, i dicts manuals a `models_app/views.py`).

**FRONTEND (display):** POMBrowser/POMCatalogue, MeasurementBaseGrid, EditableTable, editors de
model/fitting, SizeMapSetup, Grading, ImportWizard (àncores completes al radi; p.ex.
`POMBrowser.jsx:329`, `EditableTable.jsx:92`, `SizeMapSetup.jsx:687`).

**Veredicte BLOC 1: barreja confirmada + radi ampli.** `codi_client` és escrivible per 8 camins
(un d'ingovernable), participa en el matching per 2 estratègies + 4 punts, i té *fallbacks* a CSV i
molts serializers. Eliminar-lo exigeix un **codi canònic substitut** a tots aquests lectors.

---

## BLOC 2 — `_POM_SYNONYMS`: sinònim canònic o àlies disfressat? [Q2]

- **Viu en CODI**, no en dades: dict de mòdul a
  [extraction_views.py:495-522](../../backend/fhort/models_app/extraction_views.py#L495).
- **Forma:** `{descripció_EN_lower: descripció_objectiu_lower}` — mapeja una descripció extreta a una
  descripció canònica que després casa `nom_client`/`nom_en` (strategy 2 del matcher). ~14 claus
  úniques (amb claus duplicades on "l'última guanya", `:511-512`).
- **Barreja EN canònic + nomenclatura de client:** hi ha sinònims genèrics ("neckline width"→"neck
  width") **i** un bloc explícit **"Brownie positional POMs"** (`:511-521`) — descripcions del
  customer `BRW`. → **Àlies disfressats de sinònim:** tota la secció Brownie és nomenclatura de
  client incrustada al codi. Confirmat que `BRW` = customer "Textiles y Confecciones Brownie SL".

**Veredicte BLOC 2: és una proto-taula d'àlies mal ubicada.** El disseny nou l'ha d'absorbir: els
sinònims **semàntics EN** poden quedar com a taula de sinònims global; les entrades **per-client**
(Brownie) han de migrar a `CustomerPOMAlias`.

---

## BLOC 3 — Client propietari al GradingRuleSet i d'on surt "LOSAN" [Q3]

- **`GradingRuleSet` NO té cap FK ni camp de client** ([pom/models.py:450-501](../../backend/fhort/pom/models.py#L450)):
  té `size_system`, `targets` (M2M), `construction`, `fit_type`, versioning i `pendents_vincular` —
  **cap `customer`**.
- **La provinença de client és indirecta i escassa:** `SizeSystem.customer_codi`
  (`CharField(3)`, [pom/models.py:272](../../backend/fhort/pom/models.py#L272)) — **NO és FK**. A BD:
  **4 de 20** size systems el porten, tots `'LOS'`. "LOSAN IBERIA SA" surt de
  `_customer_label('LOS')` → `Customer.objects.filter(codi='LOS').first().nom`
  ([size_map_views.py:61-72](../../backend/fhort/pom/size_map_views.py#L61)).
- **25 GradingRuleSets** a fhort. 💡 **PROPOSTA:** afegir `GradingRuleSet.customer =
  ForeignKey('tasks.Customer', null=True)` (o `customer_codi` mirall de `SizeSystem` per coherència).
  **Backfill dels 25:** derivar de `rule_set.size_system.customer_codi` (només 4 → `LOS`; la resta
  `NULL`/self). Sense pèrdua: el camp és additiu i null.

**Veredicte BLOC 3: cal X (camp additiu).** El client propietari existeix penjant al `SizeSystem`;
cal materialitzar-lo al `GradingRuleSet` (FK a `Customer`) i backfillar-lo des del `size_system`.

---

## BLOC 4 — `Customer` i ancoratge de `CustomerPOMAlias` [Q4]

- **`Customer`** viu a [tasks/models.py:176](../../backend/fhort/tasks/models.py#L176): `codi`
  (`max_length=3`, **unique**), `nom`, `active`, `is_self`, `codi_global`, `logo` + camps fiscals
  (B1-P3: `rao_social`, `nif`, adreça, `descompte_pct`…). A BD: **`BRW`, `FTT` (is_self), `LOS`**.
- 💡 **PROPOSTA `CustomerPOMAlias`** (app `pom`):
  - `customer = FK('tasks.Customer', on_delete=PROTECT)`
  - `pom = FK('pom.POMMaster', on_delete=CASCADE, related_name='client_aliases')`
  - `client_code = CharField(max_length=30)` · `client_description = CharField(blank=True)`
  - opcionals de traçabilitat: `origen` (import/manual/après), `confidence`, `pendent_revisio`.
  - **Unicitat: `UniqueConstraint(customer, client_code)`** — un codi de client resol a UN POM.
  - **NO** `unique(customer, pom)` — un mateix POM pot tenir **diversos** codis del mateix client
    (evidència: LOSAN `H.11` sleeve opening vs `H.16` cuff opening són conceptes propers però codis
    distints; i un client pot reetiquetar la mateixa mesura amb dos codis).
  - **Índex** de cerca: `(customer, client_code)` (el que consulta el matcher).

**Veredicte BLOC 4: encaix net.** `Customer.codi` és àncora sòlida; la unicitat correcta és
`(customer, client_code)`. Cap obstacle estructural.

---

## BLOC 5 — Radi de `find_pom_master` i cost d'eliminar `codi_client`/root [Q5]

- **Consumidors de `find_pom_master`:** run-client paste ([size_map_views.py:249](../../backend/fhort/pom/size_map_views.py#L249))
  i fitxer (`:435`); **import de model** via Opus (`extraction_views.py:704`) i via `measurements`
  (`:851`, que ja llegeix `msr.get('client_code') or msr.get('code')` i ja compta `n_low`); camí
  Library (`:1121`); acció xat (`views.py:1307`). **Els dos camins d'import passen descripció** →
  no queden cecs si es treu el codi.
- **Simulació (BD): treure S1 exacte + S6 root → resolen igual per descripció?** Dels 22 codis
  `LLETRA.NÚMERO` actius, **21/22 es resolen a ells mateixos** per `nom_client` (majoria
  `exact_description` HIGH: `A.1 FRONT WIDTH`, `E.8 BOTTOM DIFFERENCE`, `K.2 SHOULDER TO SHOULDER`,
  `L.4 FRONT NECK DROP`, `S.10 HOOD LENGTH`, `T.1 FRONT RISE`, `*-M79`…). **Única pèrdua: `A.2 "BACK
  WIDTH"`** → cau a un altre POM de "width" (ambigu). → risc de catàleg **BAIX**.
- **El risc real són els LECTORS de `codi_client`, no el matcher:** 3 CSV (`s8_views.py`), la
  propietat `pom_code` ([models.py:192](../../backend/fhort/pom/models.py#L192), que **prioritza
  `codi_client`**) i els seus 3 consumidors (`fitting/serializers.py:256`, `grading_views.py:94/121`,
  `serializers_size_check.py:106/110`), i molts serializers amb *fallback* `… or codi_client`.
  ⚠️ **Divergència a vigilar:** `pom_code` (propietat) posa `codi_client` PRIMER; `get_pom_code`
  (serializer, `pom/serializers.py:67`) posa `pom_global.codi` primer — ordres oposats.

**Veredicte BLOC 5: viable amb transició.** Treure `codi_client` del MATCHING és de baix risc
(descripció cobreix 21/22). Treure el CAMP requereix primer donar un **codi canònic substitut**
(`pom_global.codi`) a CSV + `pom_code` + serializers. Recomanació: **fase 1 treure del matcher;
fase 2 (separada) retirar el camp** quan els lectors tinguin *fallback* canònic.

---

## BLOC 6 — `pendents_vincular` com a safata del bucle d'aprenentatge [Q6]

- **Estructura actual:** `GradingRuleSet.pendents_vincular = JSONField(default=list)`
  ([pom/models.py:463](../../backend/fhort/pom/models.py#L463)); s'omple amb `discarded_codes`
  (llista **plana de codis** string) a `size_map_views.py:682`; read-only al serializer
  (`s2_serializers.py:63`).
- **Per al bucle "confirmar match → registrar àlies" falta informació:** avui només hi ha el codi.
  💡 **PROPOSTA:** enriquir cada entrada a `{client_code, client_description, suggested_pom_id,
  confidence}` (el matcher ja retorna `weak_suggestion`+`confidence`). En confirmar (a la UI del run
  o al POMBrowser), amb el `customer` del `GradingRuleSet` (BLOC 3) es materialitza
  `CustomerPOMAlias(customer, pom, client_code, client_description)`. El següent run del mateix client
  ja resol per àlies exacte (HIGH) sense tornar a passar per la descripció.

**Veredicte BLOC 6: apta amb enriquiment.** És la safata natural del bucle; cal passar de llista de
codis a registres amb descripció + suggeriment + confiança, i un punt de "confirmar" que escrigui l'àlies.

---

## BLOC 7 — Noms EN canònic vs traduccions generades; casa d'autoria [Q7]

- **On viu el nom canònic:** `POMGlobal` (SHARED) porta `nom_en`/`nom_ca`/`nom_es`
  ([pom/models.py:32-34](../../backend/fhort/pom/models.py#L32)) — **però NO té `pendent_revisio`**.
  El `POMMaster` (tenant) porta `nom_client` + `pendent_revisio` + `origen_import` (`:169-180`).
- **Conseqüència:** avui el "nom autoritzat per humà" viu a `POMGlobal.nom_en`, però **les traduccions
  generades no tenen marca de revisió a nivell POMGlobal** (el `pendent_revisio` és al tenant POM, no
  a la traducció canònica). Gap si es volen generar `nom_ca`/`nom_es` per IA i marcar-los pendents.
- **Casa d'autoria:** `POMBrowser` és **assign-only** i `POMCatalogue` és **read-only** (confirmat a
  la diagnosi anterior). No hi ha superfície d'autoria de catàleg; la creació de tenant POM penja de
  `EditableTable` (mesures de model).

**Veredicte BLOC 7: decisió de producte.** 💡 El `client_description` de `CustomerPOMAlias` cobreix
"com ho diu el client"; el nom **canònic EN** roman a `POMGlobal.nom_en` (autoria humana). Si es volen
traduccions generades marcables, cal un `pendent_revisio` a nivell POMGlobal (o una taula de
traduccions). **POMBrowser** és el candidat natural de casa d'autoria (avui assign-only) — decisió a
elevar, fora d'aquest abast.

---

## BLOC 8 — Bloqueig de col·lisió vs àlies legítims [Q8]

- **El bloqueig** ([size_map_views.py:538-558](../../backend/fhort/pom/size_map_views.py#L538))
  agrupa el payload per `pom_id`; si un `pom_id` el reclamen ≥2 codis de document → **400** (perquè
  `GradingRule` és únic per `(rule_set, pom)` i la segona fila sobreescriuria la primera).
- **Amb àlies, dos codis d'un client poden apuntar legítimament al mateix POM** — però **NO dins d'un
  mateix document/run per a la mateixa mesura**: si dues files del run resolen al mateix POM, segueix
  havent-hi **una sola regla possible** → el bloqueig continua sent correcte (no es pot desar dues
  graduacions per a un POM en un ruleset).
- **La millora la fan els àlies aigües amunt:** avui el *contains* many-to-one fa que mesures
  DIFERENTS col·lapsin al mateix POM (col·lisió FALSA, BLOC 9). Amb `(customer, client_code)→pom`
  cada codi resol al SEU POM → **desapareixen les col·lisions falses**; les que quedin seran reals.

**Veredicte BLOC 8: NO relaxar.** El bloqueig es queda. Els àlies **redueixen** les seves
activacions (eliminen les falses); no cal distingir tipus de col·lisió al `create` — es distingeix
aigües amunt, al matcher.

---

## BLOC 9 — Fils oberts [Q9]

**(a) "H.6 ja vinculat per un altre codi" tot i resoldre a Armhole depth.**
- A fhort només **`AH DEP` (id 284)** i **`AH CIRC` (id 285)** contenen "armhole". Amb el matcher
  reordenat, `H.6 "Armhole"` → 284 per `description_match`. La badge "ja vinculat per un altre codi"
  (pre-check R1) salta perquè **una altra fila del run també resol a 284**. Mecanisme: el *contains*
  és **many-to-one** — descripcions diferents del document que continguin "armhole" cauen totes a
  `AH DEP` (la primera). **Culpable exacte: PENDENT DE VERIFICAR** amb el payload/log del run (les
  descripcions reals de BERG no es persisteixen). És **evidència directa a favor dels àlies**: amb
  `(LOS, H.6)→AH DEP` i cada altre codi al seu propi POM, la col·lisió falsa desapareix.

**(b) Consola staging: 404 a `/api/v1/commerce/{products,units,quotes}`.**
- **Codi complet i cablejat:** `commerce` a `TENANT_APPS` (`settings.py:72`); `commerce/urls.py`
  registra 8 viewsets (units `:11`, products `:12`, quotes `:18`); inclòs a `urls.py:34`
  (`api/v1/`). ViewSets a `commerce/views.py` (Unit `:37`, Product `:45`, Quote `:88` amb accions
  `send`/`pdf`). **Quotes B2 té backend complet** (model `Quote`/`QuoteLine`, serializers, migració
  `0004`, `pdf_service.py`) **i** frontend (`pages/Quotes.jsx`, `QuoteDetail.jsx`, rutes
  `App.jsx:259-260`). **NO és frontend sense backend.**
- **Causa del 404:** **gunicorn ranci.** El codi és de Jul 7 21:0x; el procés viu es va reiniciar
  Jul 8 05:20 → el `resolve()` en viu confirma que les 3 rutes ja carreguen. Els 404 eren del worker
  anterior. **Cap forat de codi; cap acció de restart presa** (read-only).

**(c) `AW "ARTWORK POSITION"`: files que NO són mesura de peça.**
- **NO EXISTEIX cap noció de tipus-de-fila** (artwork / `is_measure` / `row_type`) a
  `extraction_service.py` ni al flux de POM (grep buit). → `AW` **flueix com una mesura més**: passa
  per `find_pom_master` (probable `NO_MATCH` → pendents) i, si porta "valors", `detect_grading` els
  tracta com a mesura (soroll). No hi ha filtre de files no-mètriques.

**Veredicte BLOC 9:** (a) evidència pro-àlies, culpable a confirmar amb log; (b) **fals problema**
(restart, ja resolt); (c) mancança real menor: cal marcar/filtrar files no-mètriques (fora d'abast).

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT

| # | Element | Estat | Evidència |
|---|---|---|---|
| A | `codi_client` barreja canònic + nomenclatura client | **DIFERENT** (24 dotted) | BLOC 1 · BD |
| B | `_POM_SYNONYMS` com a dades per-client | **DIFERENT** (en codi, amb Brownie) | `extraction_views.py:495-522` |
| C | `GradingRuleSet.customer` | **FALTA** (NO EXISTEIX) | `pom/models.py:450-501` |
| D | Provinença de client (`SizeSystem.customer_codi`) | **EXISTEIX** (feble: 4/20, no FK) | `pom/models.py:272` |
| E | `Customer` com a àncora d'àlies | **EXISTEIX** (`codi` unique) | `tasks/models.py:176` |
| F | `CustomerPOMAlias` | **FALTA** (NO EXISTEIX) | — |
| G | Descripció disponible als imports (per matchar sense codi) | **EXISTEIX** | `extraction_views.py:704,851` |
| H | Lectors de `codi_client` amb *fallback* canònic | **FALTA** (CSV + `pom_code` prioritza codi_client) | `s8_views.py` · `models.py:192` |
| I | `pendents_vincular` enriquit (bucle d'aprenentatge) | **FALTA** (llista plana) | `pom/models.py:463` |
| J | Marca de revisió a traduccions canòniques (POMGlobal) | **FALTA** | `pom/models.py:32-34` |
| K | Filtre de files no-mètriques (AW) | **FALTA** (NO EXISTEIX) | BLOC 9c |
| L | Governança d'escriptura de catàleg (`POMMasterViewSet`) | **FALTA** (writable IsAuthenticated) | `pom/views.py:44` |

---

## VEREDICTE FINAL — viabilitat, disseny mínim, migració, riscos (💡 PROPOSTA, a validar)

### Viabilitat: ALTA
La separació és neta i de baix risc per al catàleg (BLOC 5: 21/22). El cost concentra en el **radi de
lectors** de `codi_client`, no en el matcher. Res irreversible.

### Disseny mínim
**1. Taules/camps (additius):**
- `CustomerPOMAlias(customer FK, pom FK, client_code, client_description, [origen, confidence,
  pendent_revisio])`, `unique(customer, client_code)`, índex `(customer, client_code)`. **NO**
  `unique(customer, pom)`.
- `GradingRuleSet.customer = FK('tasks.Customer', null=True)` (backfill des de
  `size_system.customer_codi`).

**2. Ordre nou del matcher** (funció resolució per `(customer, code, description)`):
1. **Àlies exacte `(customer, client_code)` → HIGH** (nova estratègia, primera).
2. Sinònim EN semàntic (taula depurada, sense entrades per-client).
3. `nom_client` / `POMGlobal.nom_en` per descripció (com ara).
4. *(transitori)* `codi_client` exacte → MEDIUM · root-prefix → LOW **amb bandera de deprecació**.
5. Res per sota del llindar → `pendents_vincular` (bucle).
   → A mitjà termini s'elimina el pas 4 (objectiu: matcher sense `codi_client`).

**3. Bucle d'aprenentatge:** `pendents_vincular` enriquit → "confirmar" (run o POMBrowser) escriu
`CustomerPOMAlias` amb el `customer` del ruleset → el proper run del client resol per àlies (HIGH).

### Pla de migració de `codi_client` existent → `CustomerPOMAlias`
1. **Atribució de customer:** els 24 codis `LLETRA.NÚMERO` i els `*-M79` vénen d'imports
   (`origen_import` = token) → traçar el model d'origen → el seu `Customer`. Els canònics (`SH`,
   `AH DEP`…) **NO** són àlies: es queden com a codi de catàleg (o migren a `POMGlobal.codi`).
   ⚠️ **Risc d'atribució:** alguns `codi_client` poden no tenir `origen_import` net → revisió humana.
2. **Backfill `GradingRuleSet.customer`** des de `size_system.customer_codi` (4 → `LOS`).
3. **Fase matcher:** afegir estratègia d'àlies + deixar `codi_client`/root com a *fallback* LOW
   (una peça, reversible). Re-verificar el **radi d'import**.
4. **Fase lectors:** donar *fallback* canònic (`pom_global.codi`) a CSV (`s8_views.py`), a la
   propietat `pom_code` i als serializers **abans** de retirar el camp.
5. **Retirada:** treure S1/S6 del matcher; a la fi, deprecar `codi_client` (o deixar-lo com a
   *display legacy* no-matching).

### Riscos (per severitat)
| Risc | Detall | Mitigació |
|---|---|---|
| **Radi d'import** | `find_pom_master` compartit amb import de model (`:704/:851`) | Els imports ja passen descripció; verificar cas a cas abans de treure S1/S6 |
| **Lectors amb fallback a `codi_client`** | 3 CSV + `pom_code` (prioritza codi_client) + molts serializers | Donar codi canònic substitut ABANS de retirar el camp (fase 4) |
| **Atribució de customer a la migració** | `codi_client` no té FK a client; només `origen_import` | Traçar per model; revisió humana dels ambigus |
| **`A.2 BACK WIDTH` ambigu sense codi** | 1/22 no resol net per descripció | Crear àlies explícit o afinar descripció |
| **Divergència `pom_code` vs `get_pom_code`** | ordres oposats (codi_client-first vs global-first) | Unificar l'ordre en el refactor |
| **Governança `POMMasterViewSet`** | `codi_client` writable sense CONFIGURE | Tancar gating al mateix sprint (o abans) |

### Decisions a elevar (CTO)
1. `GradingRuleSet.customer`: **FK a `Customer`** o `customer_codi` (mirall de `SizeSystem`)?
2. Casa d'autoria de catàleg + traduccions canòniques marcables: **POMBrowser**?
3. Migració: retirem `codi_client` del tot (fase 5) o el deixem com a *display legacy* no-matching?
4. Files no-mètriques (AW): les filtrem a l'extracció o les marquem?

## Obert / dubtós
- **Culpable de la col·lisió H.6** (BLOC 9a): cal el payload/log del run BERG per nomenar-lo (les
  descripcions extretes no es persisteixen; el log R4 `8731d8d` ho pot donar en re-executar).
- **Atribució customer** dels `codi_client` sense `origen_import` net: PENDENT DE VERIFICAR per model.
- No s'ha auditat si el camí Library (`extraction_views.py:1121`) i l'acció xat (`views.py:1307`)
  necessiten àlies o els basta el codi canònic — revisar en fase matcher.

---

## Watchpoints master_delta (2026-07-19 · sembra 4 cel·les Knit Tops)

Detectats en sembrar el delta (resolutor àlies-preferent + candidats enfosquits). Deute de catàleg, no bloquejant:

- **a) ⭐ PRIORITARI — parell duplicat ACTIU-ACTIU `BJ`:** DOS `POMMaster` actius amb `codi_client='BJ'` i
  el mateix nom (`FRONT & BACK WIDTH LOCATION`). Consolidate no els va fusionar. Pitjor que un orfe: pot
  rebre escriptures per les dues bandes. Cal fusionar/desambiguar.
- **b) `AJ → S1-M76 'Collar Width (Neck Tie Length)'`:** a OVIEDO/AVILA `AJ`=COLLAR WIDTH amb base 6 cm;
  "neck tie length" suggereix una altra mesura. Increment 0 → sense efecte a la graduació, però el concepte
  s'ha de revisar.
- **c) Noms canònics que despisten en context de tops:** `E → SK SW 'Skirt sweep'` i `D → HI PA 'Hip width
  (pants)'`. Coherents amb els 14 v3 (NO tocar el codi), però mereixen `descripcio_local` (ca) que no
  confongui el tècnic.
- **d) Col·lisions de `codi_client` (candidats enfosquits del seeder):** `U1` (pom 513 JETTING WIDTH via
  àlies vs 440 'Height sequins piece (CF)') · `A.1`/`A.2` (prims inactius + orfes vs canònics AC FR/AC BK) ·
  `T.5` (orfe 'EARS MEASUREMENT' vs HM L) · `D` ('1/2 bottom width relaxed' + inactiu) · `H` (2 prims
  inactius) · `H11` (inactiu) · `K.2` (inactiu) · `U` ('Width sequins piece' vs RIB WIDTH).
- **e) COBERTURA (no nomenclatura): `LOS Man Knit — Tops` sense regla de `G` (màniga llarga).** Les 6 fitxes
  d'home són de màniga curta. Afecta 1 model SWEATSHIRT dels 48 → resoldre amb `ModelGradingOverride` o una
  fitxa de dessuadora quan arribi.
