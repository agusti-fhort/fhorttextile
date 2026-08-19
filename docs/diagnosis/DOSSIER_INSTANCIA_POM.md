# DOSSIER COMPLET — IDENTITAT D'INSTÀNCIA DE POM

**Data:** 2026-07-31 (investigació) · 2026-08-01 (consolidació) · **Patró A (READ-ONLY absolut)**
**Entorn:** staging `/var/www/ftt-staging`, branca `dev`, HEAD `72d2e579`
**BD auditada:** `ftt_staging` @ 5433 — schemas `fhort` · `los` · `public`
**OpenAPI:** `GET /api/schema/` → **200 · 743 057 bytes · 364 paths**

---

## QUÈ ÉS AQUEST DOCUMENT

Consolidació **íntegra** de les dues investigacions encadenades sobre el pas d'identitat
`(model, pom, capa)` → `(model, pom, capa, INSTÀNCIA)`. Recull, sense escatimar cap taula ni cap fila:

- **PART I** — la diagnosi Patró A (brief 1): ona expansiva, cost comparat de tres formes, collita del
  diccionari des del corpus real, i el cas de prova. *(Font: `DIAGNOSI_INSTANCIES_POM.md`.)*
- **PART II** — el registre d'execució exhaustiu (brief 2): triangulació per tres camins independents amb
  les **sis taules de node senceres**, la convergència, el contrast amb censos previs i la cobertura dels
  límits declarats. *(Font: `MAPA_TOC_INSTANCIA.md`, aquí **ampliat** amb les taules completes dels sis
  investigadors, que al mapa anaven condensades.)*

**Convenció.** Cada afirmació porta `fitxer:línia` verificat a HEAD `72d2e579`.
**"NO EXISTEIX" = confirmat absent** (grep exhaustiu o `SELECT` amb resultat 0), mai especulat.
Propostes marcades `💡 PROPOSTA (a validar)` i separades dels fets. **Cap proposta de fix.**
**REGLA D'OR:** en cas de dubte, el node és DINS amb ⚪ i nota. Preferim files sobreres a forats.

**Res tocat:** cap escriptura a BD, cap fitxer de codi modificat, cap migració, cap `npm run build`,
cap management command executat. Les úniques escriptures del treball són els documents de `docs/diagnosis/`.

---

## ÍNDEX

**PART I · DIAGNOSI**
- [I.0 · Resum executiu de la diagnosi](#i0--resum-executiu-de-la-diagnosi)
- [I.A · Fase A — l'ona expansiva](#ia--fase-a--lona-expansiva)
  - [A1 · Unicitats](#a1--les-unicitats-que-assumeixen-model-pom-capa-únic) · [A2 · Escriptors cecs](#a2--escriptors-cecs) · [A3 · NOMS-POM](#a3--noms-pom) · [A4 · POMPlacement](#a4--pomplacement) · [A5 · Joins](#a5--joins-on-pom_id-fa-de-representant-únic) · [A6 · Wizard/import](#a6--wizard-i-import--com-es-resol-avui-el-duplicat) · [A7 · Els tres fitxers](#a7--els-tres-fitxers-que-decideixen-la-viabilitat)
- [I.B · Fase B — cost comparat de les tres formes](#ib--fase-b--cost-comparat-de-les-tres-formes)
- [I.C · Fase C — collita del diccionari](#ic--fase-c--collita-del-diccionari)
- [I.D · Fase D — cas de prova](#id--fase-d--cas-de-prova)
- [I.E · Taula final de riscos (34 files)](#ie--taula-final-de-riscos)

**PART II · REGISTRE D'EXECUCIÓ**
- [II.0 · Resum executiu del registre](#ii0--resum-executiu-del-registre)
- [II.1 · Com llegir el registre](#ii1--com-llegir-el-registre)
- [II.2 · Taula de convergència](#ii2--taula-de-convergència)
- [II.3 · CAMÍ 1A — `models_app` (176 files)](#ii3--camí-1a--models_app)
- [II.4 · CAMÍ 1B — `fitting` · `pom` · `patterns` (285 files)](#ii4--camí-1b--fitting--pom--patterns)
- [II.5 · CAMÍ 1C — commands · signals · SQL · migracions · tests · scripts (117 files)](#ii5--camí-1c--commands--signals--sql--migracions--tests--scripts)
- [II.6 · CAMÍ 2A — contractes · urls · OpenAPI · serializers (63 files)](#ii6--camí-2a--contractes--urls--openapi--serializers)
- [II.7 · CAMÍ 2B — frontend principal (158 files)](#ii7--camí-2b--frontend-principal)
- [II.8 · CAMÍ 2C — backoffice i zones frontereres (32 files)](#ii8--camí-2c--backoffice-i-zones-frontereres)
- [II.9 · CAMÍ 3 — des de les dades](#ii9--camí-3--des-de-les-dades)
- [II.10 · Registre consolidat per ONADA](#ii10--registre-consolidat-per-onada)
- [II.11 · Contrast amb els censos previs](#ii11--contrast-amb-els-censos-previs)
- [II.12 · Cobertura dels límits declarats](#ii12--cobertura-dels-límits-declarats)
- [II.13 · Els nodes que inverteixen la llei](#ii13--els-nodes-que-inverteixen-la-llei)
- [II.14 · Bugs vius, independents del tram](#ii14--bugs-vius-independents-del-tram)
- [II.15 · Eines que el tram ha de reusar](#ii15--eines-que-el-tram-ha-de-reusar)
- [II.16 · Recomptes finals](#ii16--recomptes-finals)
- [II.17 · Límits d'aquest dossier](#ii17--límits-daquest-dossier)

---
---

# PART I · DIAGNOSI

**Marc donat (Agus, no es qüestiona):** identitat = POM + capa + INSTÀNCIA (columna estructural,
contingut lliure per model) · qualitats descriptives = tags, mai en clau · nomenclatura d'instància
obligada diferent dins del model · escala casa→client→model · anglès com a llengua pivot · diccionari
únic de casa collit del corpus · aprenentatge directe del wizard al diccionari.

---

## I.0 · RESUM EXECUTIU DE LA DIAGNOSI

**1. La instància ja existeix a producció — disfressada de catàleg.**
El sistema no sap dir «dues instàncies del mateix POM», i el que fa en canvi és **encunyar un POM nou
al catàleg amb el qualificador enganxat al nom**. A `fhort`: **43 `POMMaster` i 27 `POMGlobal`** porten
`RELAXED`/`EXTENDED`/`STRETCHED` al nom, agrupats en **25 troncs**. El model **396 LOS-SS27-0122
EXPLORER** té avui `WAIST WIDTH` dues vegades (21 / 26,5 cm) i `LEG OPENING` dues vegades (7,5 / 9,5 cm)
— quatre `BaseMeasurement` sobre quatre POMs diferents que semànticament són dos. **Aquest és el
workaround viu, i té cost: 120 `GradedSpec` i 20 `ModelGradingRule` duplicats només en dos models.**

**2. L'ona expansiva no són les constraints: és el `dict {pom_id: …}`.**
Cens: **14 constraints UNIQUE amb `pom_id`** (9 amb capa, 5 sense) + **9 comportes CHECK `*_capa_gate_c1`**
+ **~45 escriptors/lectors**, dels quals **28 són 🔴 col·lapse silenciós**. Les constraints peten i es veuen;
els **24 diccionaris `{pom_id: …}` en memòria** no peten: **pinten** — el nom exacte ja és al codi a
`models_app/pom_placement_views.py:71`.

**3. El terreny de la nomenclatura és net avui, però té vuit portes sense pany.**
`nom_fitxa` és l'únic candidat real a nom d'instància (`CharField(20)`, del model, curt). Sobre 760 files:
**206 informades, 0 parells `(model, nom_fitxa)` duplicats** — una constraint d'unicitat per model passaria
avui sense arreglar cap fila. Però `nom_fitxa` té **8 escriptors, cap amb `strip()` ni guard de col·lisió**,
i el concepte té **5 cascades de precedència diferents** al sistema.

**4. La política vigent diu exactament el contrari del que INSTÀNCIA vol.**
`pom/size_map_views.py:671-695` — decisió CTO escrita al codi: dos codis que reclamen el mateix POM →
**400, bloquejar abans d'escriure res**. `pom/services.py:613-622` — el mateix cas resolt amb
`pendent_revisio=True`. Els dos guards tracten com a **anomalia** el que INSTÀNCIA vol **legitimar**.

**5. Aquest terreny ja es va trepitjar, amb un altre nom.**
`docs/diagnosis/DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md` (21/07) va arribar a la **mateixa clau** dient-li
`component`; `DIAGNOSI_MULTIPECA_DALIA.md` §Q2 hi va tornar des del multi-peça; i el codi mateix porta la
decisió ajornada escrita: `models_app/models.py:654-659`. **El delta d'avui és C1: el motlle existeix.**
*Nota:* la sortida barata que aquella diagnosi recomanava validar primer —modelar-ho com a Models
germans dins un `GarmentSet`— **no és viable amb les dades d'avui**: `GarmentSet` = **0 files**, Models amb
`garment_set` = **0**, amb `piece_number>0` = **0**.

**6. El cas del brief NO EXISTEIX a staging, i el corpus explica per què.**
`LEFT` i `RIGHT`: **0 ocurrències** a tot el corpus nuclear (1 168 textos). `GATHERED`/`SHIRRED`: **0**.
El top asimètric amb sisa dreta ≠ esquerra **no hi és**. El que sí que hi és, i massivament, és
l'eix **estat de la peça** (RELAXED/EXTENDED/STRETCHED, **122 ocurrències**) i l'eix **panell**
(FRONT/BACK, 304).

**7. El bateig del model encara no s'ha estrenat.**
`nom_canonic_model` i `nom_traduit_model`: **0 files informades de 760**. `seccio`: **0 de 760**. El sprint
NOMS-POM (30/07) va lliurar els camps i ningú els ha fet servir encara.

---

## I.A · FASE A — L'ONA EXPANSIVA

### A1 · Les unicitats que assumeixen (model, pom[, capa]) únic

Verificat contra `pg_constraint` del schema `fhort` **i** contra els `models.py`. **Són 14, no 9**: el cens
de l'Onada 2 del pla n'omet 5 i una taula sencera.

| # | Taula | Fitxer:línia | Tuple | Capa? |
|---|---|---|---|---|
| 1 | `models_app.BaseMeasurement` | `models_app/models.py:725` | `(model, pom, capa)` | ✅ |
| 2 | `models_app.ModelGradingOverride` | `models_app/models.py:878` | `(model, pom, size_label, capa)` | ✅ |
| 3 | `models_app.SizeCheckLine` | `models_app/models.py:1164` | `(size_check, pom, capa)` | ✅ |
| 4 | `models_app.POMPlacement` | `models_app/models.py:1336` | `(item_fitxer, pom, view_slot, capa)` — `uniq_pomplacement_item_pom_view_capa`, **sense `condition`** | ✅ |
| 5 | `fitting.GradedSpec` | `fitting/models.py:220` | `(grading_version, pom, size_label, capa)` | ✅ |
| 6 | `fitting.PieceFittingLine` | `fitting/models.py:400` | `(piece_fitting, pom, size_label, capa)` | ✅ |
| 7 | `pom.GarmentPOMMap` | `pom/models.py:612` | `(garment_type_item, pom, capa)` | ✅ |
| 8 | `pom.ItemBaseMeasurement` | `pom/models.py:898` | `(base_set, pom, capa)` | ✅ |
| 9 | `models_app.ModelGradingRule` | `models_app/models.py:960` | `(model, pom)` | ❌ (decisió 3c.1) |
| 10 | `pom.GradingRule` | `pom/models.py:1119` | `(rule_set, pom)` | ❌ |
| 11 | `pom.ClientMesuraPerfil` | `pom/models.py:1171` | `(codi_client, garment_type, pom, talla)` | ❌ |
| 12 | **`patterns.PatternPOM`** | `patterns/models.py:432` | `(pattern_piece, pom_master)` — `patternpom_un_ancoratge_per_peca` | ❌ **FORA DEL CENS DEL PLA** |
| 13 | `pom.POMEstadisticaTenant` | `pom/models.py:373` | `(pom, garment_type, talla_label)` | ❌ |
| 14 | `pom.POMEstadisticaGlobal` | `pom/models.py:257` | `(pom_global, garment_type_global, segment, talla_label)` | ❌ |

**`patterns.PatternPOM` és el cas semànticament més tens del cens.** El comentari de la seva constraint
(`patterns/models.py:430-431`, verificat literalment) diu:

> *«Un POM es mesura UNA vegada per peça. Dos ancoratges del mateix POM a la mateixa peça serien dues
> veritats sobre la mateixa mesura.»*

Que és **exactament la premissa que INSTÀNCIA nega**. La sisa dreta i l'esquerra viurien a `PatternPiece`
diferents (la constraint aguantaria), però **`RELAXED` i `EXTENDED` del mateix POM viuen a la MATEIXA peça**
— i allà la constraint bloqueja. Aquesta taula no és al pla d'Onada 2 i hauria de ser-hi.

`pom.CustomerPOMAlias` (`pom/models.py:423`) **no** té unicitat amb `pom`: la seva clau és
`(customer, client_code)`. `models_app.MeasurementChangeLog` no en té cap (append-only).

**Les 9 comportes CHECK `*_capa_gate_c1`** (`condition=Q(capa='exterior')`), totes vives a la BD:
`models_app/models.py:754` · `:818` · `:884` · `:1342` · `:1169` · `fitting/models.py:227` · `:405` ·
`pom/models.py:618` · `:903`. Migracions `models_app/0072_capa_comporta_c1.py:36-60` ·
`fitting/0019_capa_comporta_c1.py:28-34` · `pom/0055_capa_comporta_c1.py:31-37`.
El pin que les compta és una **llista literal de 9 noms** a `models_app/test_capa_comporta_c1.py:30-38`
(i `test_lectors_capa_onada1.py:37-47` les alça dins d'un savepoint) → **qualsevol columna nova haurà de
decidir si aquest pin hi creix**.

### A2 · Escriptors cecs

Semàntica de la classificació: `update_or_create(model=X, pom=Y)` sense instància a la clau té dues cares —
(a) mentre només hi hagi una fila mai podrà **crear** la segona instància, sempre reescriurà la primera → 🔴;
(b) si la segona hi arriba per un altre camí, el `get()` intern llança `MultipleObjectsReturned` → 🟠.

#### `BaseMeasurement` — el nucli (15 escriptors)

| Fitxer:línia | Operació | Clau | Risc |
|---|---|---|---|
| `models_app/views.py:1793` | `update_or_create` | `(model, pom)` | 🔴 endpoint manual; el body és `{pom_id, base_value_cm}` — **el contracte no té on posar la instància** |
| `models_app/views.py:2313` | `update_or_create` | `(model, pom)` | 🔴 acció `AFEGIR` de l'assistent IA |
| `models_app/views.py:2800` `_write_base` | `get_or_create` | `(model, pom)` | 🟠 escriptor de base de l'Escalat |
| `models_app/views.py:1921` | `.filter(model, pom).first()` | `(model, pom)` | 🟡+🔴 `gravar_pom` escriu el valor d'una instància sobre l'altra |
| `models_app/views.py:1182` | `.filter(model, pom).first()` | `(model, pom)` | 🟡 sembra item→model: una instància queda sense sembrar |
| `models_app/views.py:1417` | `.filter(model, pom_id).first()` | `(model, pom)` | 🟡 còpia model→model mal aparellada |
| **`models_app/views.py:1943-1946`** | `.exclude(pom_id__in=keep).update(is_active=False)` | **`pom_id` sol** | 🔴 **la identitat de la baixa és `pom_id`**: no es pot desactivar UNA instància. Totes dues viuen o totes dues moren |
| `models_app/extraction_views.py:2560` | `update_or_create` | `(model, pom)` | 🔴 import de fitxa — **aquí es consuma la fusió silenciosa** |
| `models_app/tech_sheet_views.py:364` | `get_or_create` | `(model, pom)` | 🔴/🟠 import IA |
| `models_app/services_size_check.py:204` | `get_or_create` | `(model, line.pom)` | 🟠 en resoldre un size check |
| `fitting/services.py:369` | `get_or_create` | `(model, line.pom)` | 🟠 `consolidate_base_from_fitting` peta en tancar peça |
| `pom/wizard_views.py:205` | `update_or_create` | `(model, pom_id)` | 🔴 wizard de mesures |
| `pom/wizard_views.py:192-194` | `.filter(model, pom_id).update(base_value_cm=None)` | `(model, pom)` | 🔴 buidar «una» mesura buida **totes dues** |
| `tenants/federation_service.py:689` | `.filter(model=twin, pom=pom).first()` | `(model, pom)` | 🔴 v. §A5.5 |
| `fitting/management/commands/repair_fitting_20260710.py:78` | `.first()` | `(model, pom)` | 🟡 comanda històrica |

#### `ModelGradingOverride`

`models_app/views.py:2590` (🔴, body `{pom_id, size_label, valor}`) · `:2587-2589` (🟡 el `prev` del log és
arbitrari) · `:2762` (🔴 escalat) · **`:2751` `.filter(model, pom).delete()`** (🔴 esborra els overrides de
**totes dues** instàncies) · `extraction_views.py:2693` (🔴 import W5).

#### Motor

**`pom/services.py:1033` `_upsert_graded_spec`** — `update_or_create(grading_version, pom_id, size_label)`;
rep `pom_id: int` per signatura (`:1009`): **no hi ha lloc per a la instància ni al paràmetre**.
`fitting/services.py:332` clona `GradedSpec`→`PieceFittingLine` copiant **només** `pom`, `size_label` i
`graded_value_cm` — **ni `capa` s'hi copia** → dos specs germans donarien dues línies indistingibles (🟠).

#### `SizeCheckLine` — el pitjor cas del cens

Verificat literalment, `models_app/services_size_check.py:33-42`:

```python
ja_hi_son = set(SizeCheckLine.objects.filter(size_check=size_check).values_list('pom_id', flat=True))
bms = (BaseMeasurement.objects.filter(model=model, is_active=True, base_value_cm__isnull=False)
       .exclude(pom_id__in=ja_hi_son).select_related('pom'))
```

Clau d'aparellament: **`pom_id` pelat, ni tan sols `capa`**. La segona instància **mai rep línia de check**
— el seu `pom_id` ja consta com a «ja hi és». No peta, no avisa, i com que `_materialize_lines` és
*completadora* (docstring `:22-30`), **cada re-obertura del check torna a decidir el mateix**. 🔴

#### Catàleg i seeds

`models_app/views.py:3760` · `:3774` · **`:3770`** (`next(b for b in fonts if b.pom_id == fila['pom_id'])`
→ agafa la primera del generador, valor promogut arbitrari, 🟡) · `pom/views.py:508` ·
`load_map_inline.py:144` · `consolidate_pom_catalog.py:212` · `author_baby_pom_maps.py:146` ·
les 5 comandes `seed_losan_*`.

#### Recomptes i cobertures que desquadrarien

| Fitxer:línia | Què compta | Efecte |
|---|---|---|
| **`pom/wizard_views.py:252-257`** | `n_poms = BaseMeasurement.filter(model, is_active).count()`, gate `< 3` | 🔴 sisa-D + sisa-E + coll **passaria** un gate que exigeix 3 POMs amb 2 mesures reals (verificat literalment) |
| `patterns/engine/grading_projection.py:179-200` | `pom_sense_spec` / `spec_sense_pom` calculats sobre **conjunts de `pom_id`** | 🔴 declararia cobert un POM cobert a mitges |
| `pom/views.py:361-364` · `tasks/views_b.py:970` | `Count('measurements')` / `Count('pom_maps')` | 🟡 columnes «#mesures» inflades |
| `models_app/views.py:2318` | `'ordre': base_measurements.count()` | 🟡 ordre duplicat entre instàncies |

### A3 · NOMS-POM

**Els tres camps de `BaseMeasurement`** (classe a `models_app/models.py:588`):

| camp | línia | tipus | default | unicitat |
|---|---|---|---|---|
| `nom_fitxa` | `:637` | `CharField(20)` | `''` | **NO EXISTEIX** |
| `nom_canonic_model` | `:681` | `CharField(160)` | `''` | **NO EXISTEIX** |
| `nom_traduit_model` | `:686` | `CharField(160)` | `''` | **NO EXISTEIX** |

Confirmat contra Postgres: els únics constraints de la taula són PK, FKs, els NOT NULL, el CHECK de capa,
`models_app_basemeasurement_ordre_check` i l'UNIQUE `(model_id, pom_id, capa)`. **Cap índex toca cap dels
tres noms.**

**El terreny és net (SQL d'aquesta sessió, `fhort`):**
- 760 files · **206 amb `nom_fitxa <> ''`** · **0 parells `(model_id, nom_fitxa)` duplicats**.
- `nom_canonic_model` i `nom_traduit_model`: **0 files informades** — el bateig de NOMS-POM (30/07) encara
  no s'ha estrenat.
- `seccio`: **0 de 760** informades.

→ Una constraint `UNIQUE(model, <nom d'instància>) WHERE nom <> ''` sobre `nom_fitxa` **passaria avui sense
arreglar cap fila**.

**Però `nom_fitxa` té vuit escriptors i cap porta:** `extraction_views.py:2544-2560` (import, `codi_fitxa`
cru) · `models_app/views.py:1929` (gravar POM) · `:1189`/`:1208` (materialitzar plantilla) · `:1426`/`:1444`
(còpia model→model) · **`:2303` (assistent IA: text generat per LLM escrit cru)** · `:3792` (promoció a item)
· `tenants/federation_service.py:698`/`:714` · `tech_sheet_views.py:369`. També el serializer genèric
l'exposa **escrivible** (`models_app/serializers.py:409`). **Cap fa `strip()`, cap comprova col·lisió dins
el model**, i tres porten text d'origen extern (import, IA, federació).

**L'únic escriptor del bateig** és `base_measurement_noms_view` (`models_app/views.py:2882`,
`PATCH /api/v1/base-measurements/<bm_id>/noms/`): fa `strip()` (`:2921`) i límit 160 (`:2922-2925`), i
**cap validació d'unicitat — NO EXISTEIX**. La còpia model→model, la federació, l'import i `materialize_poms`
**no** copien el bateig: un model copiat neix sense.

**Hi ha CINC cascades de precedència per al mateix concepte** — cap seria neutral davant un nom d'instància:

| Lloc | Cascada |
|---|---|
| `frontend/src/utils/nomenclaturaPom.js:28-37` (el resolutor «oficial») | `nom_fitxa \|\| client_alias \|\| pom_code_global \|\| codi_client \|\| pom_abbreviation \|\| abbreviation \|\| pom_code \|\| codi` |
| `frontend/src/pages/TechSheetEditor.jsx:276` `cotaLabelDe` | `nom_fitxa \|\| codi_client \|\| pom_code_global` — **codi_client per davant del canònic** |
| `fitting/serializers.py:293` | `nom_fitxa_map.get((pom,capa)) or pom.pom_code` |
| `fitting/graded_spec_views.py:123` | `nom_fitxa_map.get(pom_id) or row['abbreviation']` — **per `pom_id` sol** |
| `models_app/serializers_size_check.py:112` | `bm.nom_fitxa or pom.pom_code` — **no serveix el bateig** |

El propi capçal de `nomenclaturaPom.js:19-22` admet que `cotaLabelDe` té un ordre diferent i que la
convergència està «EN CURS».

**Catàleg — què és únic i què no:**

| Camp | Fitxer:línia | Unicitat |
|---|---|---|
| `POMGlobal.codi` | `pom/models.py:32` | **UNIQUE** (dins del schema) |
| `POMGlobal.nom_en` / `nom_ca` | `pom/models.py:33-34` | **NO EXISTEIX** |
| `POMMaster.codi_client` | `pom/models.py:302` | **NO EXISTEIX** |
| `POMMaster.nom_client` | `pom/models.py:303` | **NO EXISTEIX** |
| `CustomerPOMAlias` | `pom/models.py:422-424` | `(customer, client_code)` — **mai `(customer, pom)`** |
| `MeasurementLayer.slug` | `pom/models.py:225` | **UNIQUE** |

**`codi_client` no pot ser cap component d'identitat, i és FET, no risc teòric:** 370 `POMMaster`,
**358 `codi_client` distints → 12 codis duplicats** amb significats sense relació:

```
U1 → 440:Height sequins piece (CF) | 513:JETTING WIDTH
D  → 436:1/2 bottom width relaxed  | 528:HIP WIDTH
J1 → 507:SHOULDER DROP LOCATION    | 460:Sleeve opening relaxed
BJ, C1, L1, S2, E4, H, U, E7, S    (12 en total)
```

I hi ha lectors que hi fan `.first()`: `models_app/views.py:2313-2314` i
`tenants/federation_service.py:579`. L'únic guard de duplicat de tot el sistema és
`pom/wizard_views.py:431-432` (400, sense `iexact`); `edit_pom_nomenclature_view:465` reescriu
`codi_client` **sense cap guard** — és la porta per on entren. `load_losan_package.py:120-130` ja ho detecta
i **salta** el POM ambigu.

**Veredicte A3:** el nom d'instància té un candidat clar (`nom_fitxa`) i terreny net, però la constraint
sola no bastaria: **vuit portes d'escriptura sense normalitzar i cinc cascades de lectura divergents**.

### A4 · POMPlacement

**Camps i constraint** (`models_app/models.py:1274-1350`):

| camp | línia | declaració |
|---|---|---|
| `SOURCE_VECTOR` / `SOURCE_RASTER` / `SOURCE_KIND_CHOICES` | `:1290-1292` | `'vector'` / `'raster'` |
| `item_fitxer` | `:1296-1297` | `FK(ItemFitxer, CASCADE, related_name='pom_placements')` |
| `pom` | `:1298-1299` | `FK('pom.POMMaster', PROTECT, related_name='placements')` |
| `view_slot` | `:1302` | `SlugField(max_length=40)` — vocabulari obert (`front`/`back`/`detail-coll`), NO enum |
| `x1,y1,x2,y2` | `:1304-1307` | `FloatField()` — extrems A→B normalitzats 0..1 sobre la bbox del sketch |
| `label_dx`, `label_dy` | `:1310-1311` | `FloatField(default=0)` |
| `source_kind` | `:1314-1315` | `CharField(8, choices, default=SOURCE_VECTOR)` |
| `creat_per` | `:1316-1318` | `FK('accounts.UserProfile', SET_NULL, null, blank)` |
| `creat_el` / `actualitzat_el` | `:1319-1320` | `auto_now_add` / `auto_now` |
| `capa` | `:1323-1327` | `CharField(20, default='exterior', db_index=True)` — slug, mai FK |

Meta: `UniqueConstraint(['item_fitxer','pom','view_slot','capa'], name='uniq_pomplacement_item_pom_view_capa')`
(`:1336-1338`, **sense `condition`**) · `CheckConstraint(capa='exterior')` (`:1340-1343`) ·
`Index(['item_fitxer','view_slot'])` (`:1345-1347`).
Verificat a Postgres: constraint i CHECK vius. **La taula té 2 files al tenant `fhort`.**

**PREGUNTA CLAU: pot ancorar dues cotes del mateix POM al mateix croquis? NO. I ho impedeixen QUATRE punts
independents** — o sigui que obrir-ho no és tocar un lloc:

| # | On | Fitxer:línia | Què fa exactament |
|---|---|---|---|
| 1 | **BD — la clau** | `models_app/models.py:1336-1338` | `(item_fitxer, pom, view_slot, capa)`, **sense `condition`**. En teoria hi caben dues files del mateix POM si tenen `capa` diferent |
| 2 | **BD — la comporta** | `models_app/models.py:1340-1343` | `CheckConstraint(capa='exterior')` → la clau EFECTIVA d'avui és `(item_fitxer, pom, view_slot)`. **És el CHECK, no la clau, el que ho tanca** |
| 3 | **Vista — escriptura** | `models_app/pom_placement_views.py:135-138` | `update_or_create(item_fitxer, pom_id, view_slot)` — **`capa` no entra ni a la clau ni als defaults**. Encara que C4 retirés el CHECK, **aquest upsert seguiria col·lapsant** |
| 4 | **Frontend — guard explícit** | `TechSheetEditor.jsx:5426-5435`, `:6703`, `:6729-6734` | `cotesColocades` és un **`Set` de `pomId`**; comentari literal `C3 · GUARD DE DUPLICATS: un POM amb cota viva al document no es pot re-acotar`. Reforçat a `:5533`, `:5558`, `:5633`, `:5670` |

**Lectura**: `pom_placement_views.py:52-64` — `exacte = {p.pom_id: p}`, `germana.setdefault(p.pom_id, p)`,
`merged[pom_id] = …`: **la cascada de precedents col·lapsa per `pom_id` ABANS del lookup de capa**.
El lookup del `bm_id` sí que ja és clau composta `(pom_id, capa)` (`:72-86`), i el comentari `:68-71` ja
té el nom del dany: *«una cota col·locada sobre el folre rebria el `bm_id` de l'exterior i el dibuix
quedaria lligat a una altra mesura — el pitjor cas d'aquesta vista, perquè no peta: **pinta**»*.

**Escriptura** (`_desar_precedent`, `:102-143`): gate `CONFIGURE` (`:105-109`, 403) · parseig estricte
(`:112-119`, 400) · `view_slot = slugify(...)` (`:121`) · `source_kind` cau a `vector` si no és dels dos
choices (`:125-127`) · validació que el POM existeix **sense escriure-hi res** (`:129-132`, frontera G1) ·
`update_or_create` (`:135-138`).
**No existeix cap DELETE de placement** a tot el sistema: un precedent només es pot sobreescriure.

**L'identificador que la cota porta al `.ftt`** és el parell `(pomId, bmId)`
(`TechSheetEditor.jsx:4145`, `:344`), amb **`bmId` preferent en LECTURA**
(`:3462`: `bmById.get(o.bmId) || bmByPom.get(o.pomId)`) però **`pomId` com a únic eix d'unicitat**.
I el body que desa el precedent (`construirPrecedentCota:5598-5605`) **no hi porta ni `bmId` ni `capa`**:
en desar es perd tota informació d'instància.

> 💡 **PROPOSTA (a validar):** `bmId` ja identifica avui `(model, pom, capa)` i seria el discriminant natural
> al croquis. El que caldria retirar és la primacia del `pomId` als quatre punts, i afegir el discriminant
> al body de `:5598`. **No és recomanació d'implementació — és l'anotació del punt exacte.**

### A5 · Joins on `pom_id` fa de representant únic

**A5.1 · Motor ↔ BaseMeasurement — el punt zero.** `pom/services.py:767-783` (verificat literalment):

```python
def _load_base_measurements(model_id: int) -> dict:
    """Return {pom_id: base_value_cm}."""
    return {bm.pom_id: bm.base_value_cm for bm in BaseMeasurement.objects.filter(...).order_by('ordre')}
```

Amb dues instàncies el dict conserva **la darrera per `ordre`**; l'altra desapareix. Cap excepció, cap log:
**el motor gradua N-1 files.** Hereten el forat: `pom/services.py:233` (bucle de `generate_graded_specs`),
`:366` (preview del wizard), `:284-287` (`_upsert_graded_spec`).
Germans: `_load_grading_rules:700-708` → `{r.pom_id: r}` (les dues instàncies compartirien forçosament la
mateixa regla) · `_poms_amb_override:744-764` → `{pom_id …}` (veredicte compartit).
`_load_model_overrides:711-741` ja té la clau `(pom_id, size_label)` i **el seu propi docstring `:714-729`
diu que ha de créixer alhora que `_load_base_measurements`: «van junts, i per això queden dits al mateix
lloc»**. La instància és exactament el mateix moviment.

**A5.2 · SizeCheck ↔ BaseMeasurement.** §A2 (`services_size_check.py:33-42`, 🔴) + `:204-207`
(`get_or_create(model, line.pom)`, 🟠) + `fitting/repas_views.py:103-111`
(`fora[(size_check_id, pom_id)]` → les notes es trepitgen).

**A5.3 · POMPlacement ↔ BaseMeasurement.** §A4.

**A5.4 · PieceFittingLine ↔ BaseMeasurement.** `fitting/serializers.py:263-297` és el join més ric i el més
exposat: `ordre_map`, `nom_fitxa_map`, `bm_id_map` ja per `(pom_id, capa)`, i el comentari `:259-262` ja
descriu el dany per capa —*«Per POM sol, el folre i l'exterior d'un mateix pit es disputarien el `nom_fitxa`
i —pitjor— el `bm_id`, que és per on aquesta superfície desa el bateig: s'escriuria el nom a la mesura de
l'altra capa»*. **Amb instàncies, batejar la sisa dreta escriuria el nom sobre l'esquerra.**
`rules.get(line.pom_id)` (`:287`) col·lapsa igual, i `:304` declara que **el front el llegeix per `pom_id`**.
Welford: `fitting/services.py:438-444` escriu `ClientMesuraPerfil` amb clau
`(codi_client, garment_type, pom, talla)` → les dues instàncies **barregen estadística de client**.

**A5.5 · Federació — la clau natural.** `tenants/federation_service.py:542-552` (verificat literalment):

```python
return ((pom.pom_global.codi if pom.pom_global_id else None), pom.codi_client)
```

**Dos codis de CATÀLEG, sense cap component de model, capa ni instància.** Amb dues instàncies les dues
files produeixen **literalment la mateixa clau**:
- `:594-604` el paquet porta dues entrades amb `'clau'` idèntica, indistingibles.
- `:568-581` `_resol_pom_al_desti` retorna un únic `POMMaster` per clau (cachejat).
- `:689` `filter(model=twin, pom=pom).first()` → la 1a crea; la 2a troba la 1a com a «existent» i, com que
  no serà TEMPLATE buit (`:711`), va a `saltat['mesures'] += 1` (`:722`).
- `:732` idem per a `ModelGradingRule` → `saltat['regles']`.

🔴 **La segona instància es reporta com a «saltada»: l'informe de federació surt en verd i mitja fitxa no
haurà viatjat.** El docstring `:545-550` diu que la clau és deliberadament estricta *«perquè endevinar seria
posar una mesura sobre el POM equivocat sense que ningú se n'assabentés»* — amb instàncies, això passa
igualment, però per defecte d'expressivitat, no per endevinar.

**A5.6 · MeasurementChangeLog.** L'ESCRIPTURA sobreviuria: `models_app/signals.py:299-310` porta FK directa
(`base_measurement=instance`), aparellament exacte. Però **`capa` no s'hi passa** → la fila del log neix amb
el default `'exterior'` encara que la mesura sigui d'una altra capa (forat ja anotat com a Onada 2 del pla);
amb la instància es repetiria idènticament si no s'hi afegeix explícitament.
Els **LECTORS** sí que aparellen per POM: `base_stages_view` (`models_app/views.py:2978-3024`) usa
`(pom_id, capa)` i el seu comentari `:2991-2998` descriu el dany exacte — *«el perill aquí no és perdre una
fila: és que el carry-forward arrossegui el valor d'una capa cap endavant per la fila d'una altra —una base
que aquella capa no ha tingut mai»* — i declara que **el payload de sortida segueix portant `pom_id` sol**
(`:2997-2998`, `:3028`). `fitting/repas_views.py:156-159`: `celles[clau][c.pom_id]`, **sense ni capa**. 🔴

**A5.7 · CustomerPOMAlias.** `pom/nomenclatura.py:21-42` → `{pom_id: {client_code…}}` amb `setdefault`:
de N àlies del mateix POM **només se'n mostra UN**. Consumit a `models_app/views.py:1674-1687` i
`pom/wizard_views.py:339-340`, `:398`. Les dues instàncies compartirien obligatòriament el mateix codi de
client. I `pom/services.py:613-622` ja tracta com a **anomalia a revisar** que dos codis apuntin al mateix
POM, amb casos reals documentats (BRW `'F'`/`'FF'` → POM 389; `'U'`/`'U2'`/`'U3'` → POM 439) — **aquests dos
casos SÓN demanda d'instància disfressada de conflicte de nomenclatura.**

**A5.8 · Taules de sortida on dues instàncies es fondrien en UNA fila** (mostra dels 24 dicts):

| Fitxer:línia | Estructura | Efecte |
|---|---|---|
| `fitting/graded_spec_views.py:59-74` | `rows_by_pom[pom.id] = {…}` | 🔴 **la T1b de la fitxa imprimiria UNA fila** on n'hi hauria d'haver dues; els valors per talla se sobreescriuen cel·la a cel·la |
| `fitting/graded_spec_views.py:102-106` | `ordre_map`, `nom_fitxa_map`, `seccio_map`, **`bateig_map`** ×4 per `pom_id` | 🔴 el bateig de NOMS-POM s'aparella per `pom_id`; el comentari `:86-92` ja diu que *«han d'anar-hi tots quatre alhora»* |
| `pom/grading_views.py:96-114` | contracte declarat `cells: {pom_id: {talla: value}}` (`:62`) | 🔴 **el format del payload és un dict indexat per `pom_id`** — no admet dues instàncies sense trencar el contracte |
| `models_app/views.py:1625-1643` | `graded_by_pom[pom_id][size_label]` | 🔴 la taula d'entrada de Mesures fusiona les dues graduacions |
| `pom/s10_views.py:43-60` `_tolerance_map` | `{(pom_id, capa): tols}` | 🔴 la tolerància d'una instància jutjaria l'altra |
| `pom/s11_views.py:166-171`, `:185` | `base_map = {bm.pom_id: valor}`; body `{pom_id, value_cm}` | 🔴 contracte sense instància |
| `pom/grading_utils.py:87-100`, `:777-795` | `set(m_by) - set(c_by)`; classificació SEMBRA/AMPLIA/CONFLICTE | 🔴 dues instàncies divergents es classificarien com una |
| `models_app/extraction_views.py:2176-2182` | `valors.setdefault(pid, {})[talla] = valor` | 🔴 **l'import indexa les mesures per `pom_master_id`**: dues files del document cap al mateix POM **ja es fonen avui** |
| **`patterns/engine/ports.py:60, 97`** | `pom_id: int` a `GradedPOMDelta`; `delta(self, pom_id, size_label)` | 🔴 **el port entre motor de grading i motor de patrons està tipat amb `pom_id` sol** — canvi de contracte d'engine |
| `patterns/views.py:544-549` | `ancorats = {p.pom_master_id: p}` sobre **tot el PatternFile** | 🔴 dues peces (dreta/esquerra) amb el mateix POM **ja col·lapsen avui** |
| `models_app/views.py:1674-1687` | `rules_by_pom.get(pom.id)` + `camps_de(alias_by_pom, pom.id)` | 🔴 nomenclatura i regla compartides |
| `pom/wizard_views.py:339-340, 352-353, 367, 398` | `alias_by_pom`, `regla_by_pom` per `bm.pom_id` | 🔴 wizard + nomenclatura |
| `models_app/views.py:2500-2508` | files de resposta amb `'pom_id': pom.id` | contracte |
| `models_app/views.py:1178` | `ibms = {i.pom_id: i}` (`:1145`) → `ibms.get(m.pom_id)` — sembra item→model | 🔴 |

### A6 · Wizard i import — com es resol avui el duplicat

**`many_to_one` no és una entitat: és una bandera booleana per FILA** dins del JSON
`ImportSession.poms_extrets` (`models_app/models.py:572`). Hi ha **DUES implementacions germanes i
deliberadament divergents**:

| | Camí IMPORT de mesures | Camí SIZE-MAP / grading |
|---|---|---|
| On | `models_app/extraction_views.py:1148-1193` | `pom/size_map_views.py:54-75` (crides `:362`, `:604`) |
| Compta per | `pom_master_id` (`:1175-1179`) | `pom_id` |
| Acció | mou el match a `weak_suggestion`/`weak_suggestion_codi`, **buida `pom_master_id`/`pom_codi`/`pom_nom` i posa `actiu=False`** (`:1183-1192`) | idem |
| Exempció d'àlies | **CAP** — docstring `:1155-1171`: destí `BaseMeasurement`, únic per `(model,pom)`, «per legítim que sigui l'àlies, la segona esborra la primera» | **SÍ**: `match_type == 'alias_match'` no dispara (`:64`, `:70`), perquè «un client pot etiquetar legítimament el mateix POM amb dos codis (Losan H.11 sleeve opening / H.16 cuff opening)» |

Emès des de `_match_rows` (`:1196`, crida a `:1249`), que és la **font única de matching dels dos camins
d'extracció** (parser Excel i visió Opus). Camp inicialitzat a `False` a `:1246`; comptador
`n_many_to_one` a `:1250-1252`; avís de text a `:1268-1273`. Consumit al backend només com a dada de sessió
(`:1476`, `:1657`).

**Consumidors de frontend** (només pintat, cap acció pròpia): `ImportWizard.jsx:1116`
(`pendent = noMatch && !!p.weak_suggestion`), `:1158-1161` (`import_wizard.many_to_one_hint`) ·
`SizeMapSetup.jsx:780-785` (`size_map_many_to_one`) · textos `i18n/ca.json:2371` i `:3609` ·
tests `models_app/tests.py:111-113`, `:185-204`.

> **FET clau:** el guard **no detecta nomenclatura duplicada — detecta destí duplicat**. Dues files amb el
> mateix `codi_fitxa` només es veuen si totes dues resolen al mateix `pom_master_id`.
> **NO EXISTEIX enlloc cap comprovació de `codi_fitxa` repetit dins d'un document.**

**El parser NO dedupica**: `_parse_excel_poms` (`extraction_views.py:233`) emet una fila per fila de document
(bucle `:437-478`, `poms.append`), i la via Opus igual (`:1631-1634`). L'única col·lisió per codi és
`by_codi.setdefault(p['codi_fitxa'], p)` (`:1417-1419`), i només per dirigir les correccions de Sonnet: **la
segona fila amb el mateix codi no rep mai correcció però sobreviu.**

**Camí de codi exacte del duplicat:**
1. `_match_rows` (`:1216-1247`) → cada fila crida `find_pom_master(codi, descripcio, customer)` (`:985`)
   → totes dues cauen al mateix POM.
2. `_apply_match_threshold` (`:1137-1145`) — LOW no auto-vincula.
3. `_apply_many_to_one_guard` (`:1249`) → **desvincula TOTES DUES** i les deixa `actiu=False`.
4. Avís textual `:1268-1273`: «cap no s'ha vinculat automàticament (dues mesures no poden compartir un POM:
   la segona esborraria la primera). **Resol-los un per un**.»

**La resolució actual no descarta ni fusiona: BLOQUEJA i delega a l'humà** — però l'única sortida oferta és
1 fila ↔ 1 POM distint. Si l'humà les vincula totes dues al mateix POM, el sistema ho impedeix, i si hi
arribés, `update_or_create` a `:2560` les fusionaria: **la segona sobreescriu la primera en silenci**.

**Punts on el duplicat es col·lapsa silenciosament aigües avall**, tots per clau `pom_master_id`:
`import_session_poms_view:1848-1850` (`actiu` s'assigna per **pom_master_id**, no per fila/ordre) ·
`import_session_mesures_view:2002-2015` · `import_session_confirmar_view:2176-2182`
(`valors.setdefault(pid, {})[talla] = valor` → l'última fila mana) · `:2530` · `:2560`.
Límit ja documentat al codi: `models_app/models.py:654-659`.

**Els 409 del pas 2** (`extraction_views.py`):

| codi | línia | significat |
|---|---|---|
| `codi_duplicat` | `:1844-1845` | el CATÀLEG té 2+ `POMMaster` tenant-only amb el mateix `codi_client` (`:1837-1840`). Porta `candidats` (`_candidats_de_codi:1693-1710`) |
| `resolucions_invalides` | `:1856-1858` | contenidor d'errors per fila de `_pla_de_resolucions` (`:1713-1777`) |
| ↳ **`pom_ja_usat`** | `:1753-1756` | **el punt dur**: «no el pot tenir ja una altra fila activa» (`:1718`) |
| ↳ `codi_existent` | `:1764-1766` | crear tenant-only amb un codi ja present al catàleg |
| ↳ `codi_repetit` | `:1768-1771` | dues resolucions 'crea' amb el mateix codi dins la mateixa tramesa |
| ↳ `pom_no_valid` / `fila_no_trobada` / `accio_desconeguda` | `:1751`, `:1744`, `:1776` | — |

`pendent_revisio=True` s'escriu als POMMaster nascuts al pas 2 (`:1877`, `:1906`).

**`CustomerPOMAlias` demostra que el sistema JA sap conviure amb l'ambigüitat, un nivell més amunt.**
Docstring `pom/models.py:382-383`: *«Un client pot tenir DIVERSOS codis per al mateix POM → unicitat
(customer, client_code), NO (customer, pom)»*. `pom` és nullable (`:395-402`): vocabulari del client encara
sense mapar és un **estat legítim**. `maybe_learn_customer_alias` (`pom/services.py:578-640`) **no falla ni
descarta**: el guard `:613-622` calcula `ja_reclamat` i crea l'àlies amb `pendent_revisio=ja_reclamat`
(`:630`, `:637`), amb el comentari *«o el codi nou és un sinònim del vell (i sobra), o són DUES mesures
distintes i una de les dues quedarà sobre el POM equivocat… en comptes d'aprendre'l en silenci, es crea
PENDENT DE REVISIÓ perquè una persona el miri»*. El consumidor el degrada a LOW
(`extraction_views.py:1026-1037`, `:1092-1093`, `match_type='alias_pendent_revisio'`).
**Presentació:** `pom/nomenclatura.py:21-42` — `out.setdefault(pom_id, …)` amb
`order_by('pendent_revisio','client_code')`: de N àlies del mateix POM **només se'n mostra UN**.
→ **L'ambigüitat és legítima a nivell d'ÀLIES; es converteix en error a nivell de MESURA.**

**El wizard no té ni guard ni 409 per al duplicat**: `save_base_size_view` (`pom/wizard_views.py:155-227`)
rep `poms: [{pom_id, valor_cm, …}]` — la identitat és `pom_id`, no una fila — i:
- `:192-194`: valor 0/None → `filter(model, pom_id).update(base_value_cm=None)`, actua sobre **totes** les
  files d'aquell POM.
- `:205-215`: `update_or_create(model, pom_id, defaults=…)` — **cap 409, cap avís**: dues entrades amb el
  mateix `pom_id` al mateix payload es fusionen i guanya l'última.
- `confirm_base_size_view:232-298` només compta files (`:252`).
- `create_tenant_pom_view:431-432` → **400** «Ja existeix un POM amb codi {code}» (unicitat de CATÀLEG).
- `edit_pom_nomenclature_view:455-478` — **cap comprovació d'unicitat**: pot crear codis duplicats.

**Sembra i plantilles**: `materialize_poms` (`models_app/views.py:1104-1220`) llegeix la plantilla com a
dicts per `pom_id` (`:1136`, `:1145`) i fa `.first()` a `:1182` → amb dues instàncies veuria una d'arbitrària
(ordre `['model','capa','ordre','pom']`) i tractaria l'altra com a inexistent → `IntegrityError` o `skipped`
silenciós (`:1217`). Sobirania `:1204-1215`: només escriu sobre `TEMPLATE` buit.
`_sembra_step_des_dels_specs` (`:3949-3988`) fa `dict(...values_list('size_label','graded_value_cm'))`
(`:3977-3980`) → l'última guanya, **sense rastre** (és el mateix mode de fallada que el filtre de `capa` va
tapar per a les capes, comentari `:3970-3975`).

**Frontend — NO EXISTEIX cap UI per declarar «dues instàncies legítimes»**, i hi ha **tres barreres actives**:
`ImportWizard.jsx:536-537` (`addPomManual` prohibeix afegir dos cops el mateix POM) ·
**`:626-637` `buildTaula` → `t[p.pom_master_id] = row`: la graella del pas 3 és UNA FILA PER POM** — dues
instàncies es fondrien abans d'arribar al backend · `:639-645` (`setCell`, `emptyCols`) igual.
El `ResolPanel` (`:1194-1208`) té **exactament dues accions**: `vincula` | `crea` (`posaResolucio:511-517`).
Gestió del 409 `codi_duplicat` (`:565-577`) i `resolucions_invalides` (`:579-593`) → `marcaConflictes`
(`:526-534`).

**Els ~32 punts de decisió que canviarien** si el duplicat pogués ser instància legítima:

**Identitat / esquema (l'arrel):** `models_app/models.py:725` · `:654-659` (el LÍMIT ja escrit) · les claus
germanes en cascada: `:878`, `:960`, `:1164`, `:1330-1340`, `fitting/models.py:220`, `:400`,
`pom/models.py:612`, `:898`, `:1119`.
**Detecció (de "error" a "pregunta"):** `extraction_views.py:1148-1193` · `:1183-1192` · `:1268-1273` ·
`pom/size_map_views.py:54-75` · *(cap punt detecta `codi_fitxa` repetit — caldria que existís)*.
**Confirmació del pas 2:** `extraction_views.py:1848-1850` (`poms_confirmats` és **una llista de POM ids**,
estructuralment incapaç de distingir dues files del mateix POM) · `:1734-1736` (`presos`) ·
**`:1753-1756` (`pom_ja_usat` — el punt exacte que hauria de passar de "error" a "pregunta")** · `:1919-1934`.
**Escriptura (W5):** `:2176-2182` · `:2308-2315` · `:2330-2335` · `:2364-2369` · `:2530`, `:2534` ·
**`:2560`** (on la fusió silenciosa es consuma).
**Alta manual:** `pom/wizard_views.py:192-194` · `:205-215`.
**Sembra i plantilles:** `models_app/views.py:1136`, `:1145` · `:1182` · `:3977-3980`.
**Nomenclatura / àlies:** `pom/services.py:613-622` · `extraction_views.py:1026-1037`, `:1092-1093` ·
`pom/nomenclatura.py:32-41`.
**Frontend:** `ImportWizard.jsx:536-537` · `:626-637`, `:639-640`, `:643-645` · `:548-557` · `:1194-1208` ·
`:1116`, `:1158-1161` + `i18n/{ca,en,es}.json:3609` i `:2371` · `SizeMapSetup.jsx:780-785`.
**Tests que codifiquen la llei actual:** `models_app/tests.py:105-126` i `:180-204` ·
`test_import_poms_duplicats.py` · `test_import_poms_resolucions.py` · `test_parser_excel.py:514`, `:542`.

### A7 · Els tres fitxers que decideixen la viabilitat

Per ordre de radi:

1. **`pom/services.py:767-783`** — `_load_base_measurements` → `{pom_id: valor}`. Tot el motor (generació i
   preview) hi penja. **Zona intocable segons `CLAUDE.md`**; el pla ja la té a C3 amb decisió humana. El seu
   veí `:714-729` ja està escrit sabent que aquesta clau ha de créixer, **i marca que ha de créixer alhora**.
2. **`models_app/services_size_check.py:33-42`** — l'`exclude(pom_id__in=…)` fa que la segona instància no
   rebi mai línia de validació, silenciosament i **de forma repetible a cada re-obertura**.
3. **`tenants/federation_service.py:542-552`** — la clau natural és una tupla de codis de catàleg; dues
   instàncies són literalment el mateix element i **la segona es reporta com a "saltada" amb l'informe en verd**.

**Comptador brut del cens:** 14 UNIQUE amb `pom_id` + 9 CHECK + **1 taula fora del cens del pla**
(`patterns.PatternPOM`) + ~45 escriptors/lectors classificats → **28 🔴 · 7 🟠 · 9 🟡**.
**24 dicts `{pom_id: …}` distints** en memòria. Cap peta. Tots pinten.

> **Veredicte FASE A:** l'ona és **més ampla que la de C1** (capa) en dos sentits mesurables: toca 5 taules
> més (les que no van rebre `capa` per decisió) i, sobretot, **travessa contractes d'API i de motor**
> (`grading_views.py:62`, `s11_views.py:161-164`, `patterns/engine/ports.py:60`) que la capa no va tocar
> perquè C1 va poder quedar-se darrere la comporta. **La instància no té equivalent de comporta per als
> contractes.**

---

## I.B · FASE B — COST COMPARAT DE LES TRES FORMES

Taula de cost, **sense recomanar**. Les xifres «vs Onada 1/1b» compten nodes ADDICIONALS als que el Tram C
ja té censats i/o fets.

| Eix | **F1 · columna slug `instancia`** (default `''` + comporta, motlle C1) | **F2 · tags JSONB en identitat** | **F3 · híbrid** (identitat = columna, JSONB només semàntic) |
|---|---|---|---|
| **# unicitats a tocar** | **9** (les de §A1 #1-8 + `POMPlacement`) + decisió sobre les 5 sense capa (#9-11, 13-14) + **`PatternPOM` #12** | **9 igual** — un JSONB dins un `unique_together` obliga a un índex d'expressió (`(tags->>'instancia')`) i **Django no ho suporta declarativament**: caldria `RunSQL` a mà a cada taula | **9 igual que F1** (la identitat és columna) |
| **# escriptors** | **~45** (§A2), dels quals **28 🔴** han d'estampar el valor o el default | **~45 igual** + tots han de saber **construir el JSON** en lloc d'assignar un escalar; els `update_or_create` no poden filtrar per clau JSONB sense `__contains` | **~45 igual que F1** + els que vulguin tags, per separat |
| **# lectors extra vs Onada 1/1b** | **~24 dicts `{pom_id:…}`** → la clau passa a 3 elements. **8 ja són `(pom, capa)`** i només creixen; **16 són `pom_id` pelat** | **~24 igual** + cada lookup ha de normalitzar el JSON (ordre de claus, `None` vs absent) abans de fer-lo clau de dict → **font nova de bugs no determinista** | **~24 igual que F1** |
| **Contractes d'API/engine** | **5 nous** que la capa no va tocar: `grading_views.py:62` (`cells: {pom_id: …}`) · `s11_views.py:161-164` · `pom_placement_views.py:113` · `views.py:1793` (body de mesures) · `patterns/engine/ports.py:60,97` | **igual + pitjor**: el JSON viatja al payload i el frontend l'ha de saber comparar | **igual que F1** |
| **Impacte federació** | `_clau_natural_pom:542-552` passa de 2-tupla a 3-tupla. **Canvi de format del paquet** → els paquets ja exportats deixen de casar; cal decidir versionat | **3-tupla amb un JSON dins** → la clau natural deixa de ser comparable per igualtat estricta; contradiu el docstring `:545-550` («deliberadament més estricta») | **igual que F1** |
| **Aplicabilitat del motlle C1** | **ALTA i directa.** Mateixa forma exacta: `CharField` + `default` + `db_index` + **9 comportes CHECK** + backfill a `''` + retirada al final del tram. Les eines de verificació de C1 (`c1_audit_counts.sql`, `c1_audit_constraints.sql`, harness 2-capes de `test_lectors_capa_onada1.py`) **es reutilitzen canviant el nom de columna** | **NUL·LA.** No hi ha comporta CHECK possible sobre «el JSON no porta instància» que sigui barata; el pin de 9 noms literals (`test_capa_comporta_c1.py:30-38`) no hi aplica | **ALTA per a la columna** · nul·la per als tags (però els tags **no necessiten comporta**: no són identitat) |
| **Riscos de col·lapse residuals** | Els **16 dicts encara per `pom_id` pelat** (`repas_views.py:156`, `graded_spec_views.py:59-74`/`:102-106`, `grading_views.py:96-114`, `patterns/views.py:544`, `grading_projection.py:179-200`…): si un creix i el veí no, la fila surt **amb l'ordre d'una instància i el nom de l'altra** — el mode de fallada que `graded_spec_views.py:86-92` ja descriu | **Tots els de F1** + col·lapse per **normalització de JSON**: `{"lat":"R"}` i `{"lat":"r"}` són claus distintes i mesures iguals. **NO hi ha cap índex GIN al schema `fhort` (0)** ni cap precedent de JSONB en clau | **Els de F1.** Els tags no poden col·lapsar res perquè no entren a cap clau |
| **Precedent al repo** | **C1 sencer** (viu a `3efe7f4b`, 9 taules migrades, 20 comportes) | **NO EXISTEIX.** 20 `JSONField` al repo, **cap en cap clau ni unicitat**: `patterns` (12, geometria/metadata), `accounts` (2), `backoffice` (2), `tenants` (2), `planning` (2). **0 índexs GIN a `fhort`** | Combinació dels dos: columna amb precedent, tags sense |

### B2 · Fets que sostenen la taula

- **JSONB al repo**: 20 `JSONField` declarats, **cap dins un `unique_together`, `UniqueConstraint`,
  `db_index` ni `ordering`**. Grep exhaustiu sobre `--include=models.py`. Els de `patterns/models.py:91-178`
  (`empremta`, `contorns`, `raw_entities`…) són **càrrega geomètrica**, mai identitat.
- **Índexs GIN al schema `fhort`: 0** (`SELECT count(*) FROM pg_indexes WHERE schemaname='fhort' AND
  indexdef ILIKE '%gin%'`). Adoptar JSONB en clau significaria estrenar el patró d'indexació a la taula més
  llegida del sistema.
- **El motlle C1 és mesurable**: 9 taules amb `capa`, **20 comportes** (`9 fhort + 9 los + 2 public`, perquè
  `pom` és SHARED+TENANT), **100% `'exterior'`**. La migració fa `ADD COLUMN … DEFAULT … NOT NULL` seguit de
  `DROP DEFAULT` (patró Django) → **el default és del MODEL, no de Postgres**: un INSERT en SQL cru que no
  digui la columna peta, i **codi vell + esquema nou = NOT NULL violation** (va caldre
  `systemctl restart ftt-staging.service`). **Qualsevol de les tres formes hereta aquest requisit de desplegament.**
- **Contingut lliure per model** (marc donat) encaixa amb `CharField` sense `choices`: el catàleg de valors
  viuria al diccionari de casa, no a la constraint — exactament com `capa` referencia
  `MeasurementLayer` **per slug, mai per FK** (llei G9, `pom/models.py:225`).

### B3 · El que cap de les tres formes resol sola

1. **`_load_base_measurements`** (`pom/services.py:767-783`) és zona intocable i **cap forma la travessa
   sense decisió humana**. Si no s'obre, cap de les tres és viable end-to-end (mateixa conclusió que
   `DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md` §P2-C).
2. **Els dos guards de política** (`size_map_views.py:671-695` → 400; `services.py:613-622` →
   `pendent_revisio`) bloquejarien el cas nou en qualsevol de les tres formes si no creixen amb ella.
3. **`ImportWizard.jsx:626-637`** — la graella del pas 3 és una fila per `pom_master_id`: **el duplicat mor
   al frontend abans d'arribar a cap clau de BD**, sigui columna o JSONB.
4. **La nomenclatura obligada diferent** (marc donat) no la dona cap de les tres formes: cal una constraint
   pròpia sobre el nom (§A3), i **vuit escriptors sense `strip()` la farien saltar per espais**.

### B4 · Delta respecte de la diagnosi de components (21/07)

`DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md` va arribar a la mateixa clau amb el nom `component` i va concloure
«cost ALT i transversal, no és un sprint de camp nou». **Què ha canviat des d'aleshores:**

| | 21/07 | Avui |
|---|---|---|
| Motlle de migració multi-taula | inexistent | **C1 fet i auditat** (9 taules, 20 comportes, backfill, pin, harness 2-capes) |
| Lectors per `(pom, capa)` | 0 | **8** (Onada 1, 9 commits vius) — la meitat de la feina de re-clau **ja està feta** |
| Sortida barata (`GarmentSet`) | «pendent de verificar» | **descartada per dades: 0 GarmentSet, 0 models amb `garment_set`, 0 amb `piece_number`** |
| Cens de la cadena | 5 taules | **14 unicitats + `PatternPOM` + 5 contractes d'API/engine** |
| Cas real viu | cap trobat | **model 396 EXPLORER, 2 parells d'instàncies** (§I.D) |

---
## I.C · FASE C — COLLITA DEL DICCIONARI

### C1 · El corpus real

**`los` i `public` no aporten res**: `los.models_app_basemeasurement` = 0, `los.pom_pommaster` = 0,
`los.pom_customerpomalias` = 0, `public.pom_pommaster` = 0, `public.pom_customerpomalias` = 0.
**Tot el corpus viu a `fhort`.**

| Font | Files no buides | Paper |
|---|---|---|
| `pom_pommaster.nom_client` | **370** | nom local del POM del tenant |
| `pom_pomglobal.nom_en` | **274** (125 `POM-*` + 149 `LOSPOM-*`) | canònic EN de la casa |
| `pom_customerpomalias.description_en` | **262** | descripció EN del client |
| `pom_customerpomalias.description_local` | **260** | descripció en la llengua del client |
| `models_app_basemeasurement.notes` | **207** | text original del document importat |
| `models_app_basemeasurement.nom_fitxa` | **206** | nomenclatura curta del croquis |
| `pom_pomglobal.descripcio_en` / `abbreviation` | **125** / **125** | definició i abreviatura canòniques |
| `pom_customerpomalias.client_description` | **55** | — |
| **`nom_canonic_model` / `nom_traduit_model` / `seccio`** | **0 / 0 / 0** | **el bateig NO s'ha estrenat** |

*Nota metodològica:* el «corpus nuclear» de les freqüències següents = `nom_client` + `nom_en` +
`client_description` + `description_en` + `bm.notes` (**1 168 textos**). `descripcio_en` i `abbreviation` es
compten a part perquè són **definició**, no nomenclatura.

**Àlies per client:** LOSAN IBERIA SA **240** (24 `pendent_revisio`) · Textiles y Confecciones Brownie SL
**94** (2 pendents) · FHORT Textile Tech **2**. Cap àlies orfe (`pom_id IS NULL` = 0).

**Catàleg de capes ja sembrat** (`fhort.pom_measurementlayer`, 6, totes `is_system`):

| slug | nom_en | nom_ca | nom_es | ordre |
|---|---|---|---|---|
| `exterior` | Shell | Exterior | Exterior | 1 |
| `folre` | Lining | Folre | Forro | 2 |
| `entretela` | Interfacing | Entretela | Entretela | 3 |
| `farciment` | Padding | Farciment | Relleno | 4 |
| `reforc` | Underlining | Reforç | Refuerzo | 5 |
| `fornitura` | Trim | Fornitura | Fornitura | 6 |

### C2 · La troballa central: el qualificador viu al NOM del catàleg

**43 `POMMaster` i 27 `POMGlobal`** porten `RELAXED`/`EXTENDED`/`STRETCHED` al nom. Agrupats per tronc
(nom sense el qualificador), **25 troncs**. Taula completa dels troncs a nivell de `POMMaster`:

| Tronc | # variants | Variants (qualificador#id) |
|---|---|---|
| **LEG OPENING** | 5 | STRETCHED#407 · RELAXED#532 · EXTENDED#533 · **RELAXED#687** · **EXTENDED#688** |
| **CHEST WIDTH** | 4 | RELAXED#331 · STRETCHED#332 · RELAXED#518 · EXTENDED#519 |
| **WAIST WIDTH** | 4 | RELAXED#523 · EXTENDED#524 · **RELAXED#685** · **EXTENDED#686** |
| HIP WIDTH | 3 | RELAXED#405 · STRETCHED#406 · STRETCHED#471 |
| SLEEVE OPENING | 3 | STRETCHED#298 · RELAXED#460 · EXTENDED#554 |
| 1/2 BOTTOM WIDTH | 2 | RELAXED#436 · EXTENDED#500 |
| BOTTOM WIDTH | 2 | RELAXED#534 · EXTENDED#535 |
| ELASTIC | 2 | RELAXED#414 · EXTENDED#415 |
| HOOD LENGTH | 2 | RELAXED#612 · EXTENDED#613 |
| WAISTBAND WIDTH | 2 | RELAXED#318 · STRETCHED#319 |
| ACROSS BACK | 1 | STRETCHED#404 |
| ACROSS FRONT | 1 | STRETCHED#403 |
| BACK WAIST | 1 | EXTENDED#527 |
| BACK WAIST WIDTH | 1 | RELAXED#526 |
| BODY LENGTH (KNITWEAR,…) | 1 | RELAXED#333 |
| COLLAR OPENING | 1 | EXTENDED#511 |
| ELASTIC WAIST | 1 | STRETCHED#408 |
| ELASTIC WAIST WIDTH | 1 | RELAXED#350 |
| FLOUNCE | 1 | EXTENDED#401 |
| FRONT WAIST WIDTH | 1 | RELAXED#525 |
| LEG OPENING (BODYSUIT,…) | 1 | RELAXED#360 |
| NECKBAND CIRCUMFERENCE | 1 | RELAXED#307 |
| PIECE WIDTH | 1 | EXTENDED#570 |
| RIB HEM WIDTH | 1 | STRETCHED#330 |
| WIDTH BEFORE CUFF | 1 | EXTENDED#555 |

**I el canònic fa el mateix** (`fhort.pom_pomglobal`, 274 files):

| Tronc | Variants canòniques |
|---|---|
| SLEEVE OPENING | RELAXED `LOSPOM-460` · EXTENDED `LOSPOM-554` · STRETCHED `POM-026` |
| LEG OPENING | RELAXED `LOSPOM-532` · EXTENDED `LOSPOM-533` · STRETCHED `POM-144` |
| CHEST WIDTH | RELAXED `POM-080` · STRETCHED `POM-081` |
| BOTTOM WIDTH | RELAXED `LOSPOM-534` · EXTENDED `LOSPOM-535` |
| HIP WIDTH | RELAXED `POM-142` · STRETCHED `POM-143` |
| WAISTBAND WIDTH | RELAXED `POM-050` · STRETCHED `POM-051` |
| WAIST WIDTH | RELAXED `LOSPOM-523` · EXTENDED `LOSPOM-524` |
| HOOD LENGTH | RELAXED `LOSPOM-612` · EXTENDED `LOSPOM-613` |
| ELASTIC | RELAXED `POM-151` · EXTENDED `POM-152` |
| FRONT POCKET WIDTH · FRONT WAIST WIDTH · LEG OPENING (BODYSUIT) · NECKBAND CIRCUMFERENCE · PIECE WIDTH · RIB HEM WIDTH · ACROSS BACK · WIDTH BEFORE CUFF · ACROSS FRONT · BACK WAIST · BACK WAIST WIDTH · BODY LENGTH (KNITWEAR) · COLLAR OPENING · ELASTIC WAIST · ELASTIC WAIST WIDTH · FLOUNCE | 1 cadascun |

**Mapeig canònic dels POMs variants** (verificat contra `fhort.pom_pomglobal`, **no** `public`):

| POMMaster | codi_client | nom_client | POMGlobal |
|---|---|---|---|
| 535 | E4 | BOTTOM WIDTH EXTENDED | `LOSPOM-535` |
| 534 | E3 | BOTTOM WIDTH RELAXED | `LOSPOM-534` |
| 519 | B2 | CHEST WIDTH EXTENDED | **(sense pom_global)** |
| 331 | CH RLX | Chest width (relaxed) | `POM-080` |
| 518 | B1 | CHEST WIDTH RELAXED | **(sense pom_global)** |
| 332 | CH STR | Chest width (stretched) | `POM-081` |
| 415 | EL EXT | Elastic extended | `POM-152` |
| 414 | EL RLX | Elastic relaxed | `POM-151` |
| 405 | HI RLX | Hip width (relaxed) | `POM-142` |
| 406 | HI STR | Hip width (stretched) | `POM-143` |
| 613 | S55 | HOOD LENGTH EXTENDED | `LOSPOM-613` |
| 612 | S54 | HOOD LENGTH RELAXED | `LOSPOM-612` |
| 533 | F6 | LEG OPENING EXTENDED | `LOSPOM-533` |
| **688** | **F.6** | LEG OPENING EXTENDED | **(sense pom_global)** |
| 532 | F5 | LEG OPENING RELAXED | `LOSPOM-532` |
| **687** | **F.5** | LEG OPENING RELAXED | **(sense pom_global)** |
| 407 | LEG OP STR | Leg opening (stretched) | `POM-144` |
| 554 | H14 | SLEEVE OPENING EXTENDED | `LOSPOM-554` |
| 460 | J1 | Sleeve opening relaxed | `LOSPOM-460` |
| 298 | SL OP STR | Sleeve opening stretched | `POM-026` |
| 471 | C1 | STRETCHED HIP WIDTH | **(sense pom_global)** |
| 318 | WB RLX | Waistband width (relaxed) | `POM-050` |
| 319 | WB STR | Waistband width (stretched) | `POM-051` |
| **686** | **C.1** | WAIST WIDTH EXTENDED | **(sense pom_global)** |
| 524 | C1 | WAIST WIDTH EXTENDED | `LOSPOM-524` |
| **685** | **C.4** | WAIST WIDTH RELAXED | **(sense pom_global)** |
| 523 | C4 | WAIST WIDTH RELAXED | `LOSPOM-523` |

> ⚠️ **Nota metodològica important**: `POMMaster.pom_global` és FK a **`fhort.pom_pomglobal` (274 files)**,
> **no** a `public.pom_pomglobal` (125). Un join contra `public` dona **resultats falsos** (mapeigs
> aparentment aleatoris). Verificat amb `pg_constraint`:
> `pom_pommaster_pom_global_id_915e99d6_fk_pom_pomglobal_id FOREIGN KEY (pom_global_id) REFERENCES fhort.pom_pomglobal(id)`.

**Conseqüència mesurada — fragmentació del catàleg:** **15 `nom_client` duplicats** a `POMMaster`:

| nom_client | n | ids:codi_client |
|---|---|---|
| BACK RISE | 3 | 388:T.2-M79 · 435:T.2 · 694:T.21 |
| FRONT RISE | 3 | 387:T.1-M79 · 434:T.1 · 693:T.11 |
| FOOT WIDTH | 2 | 411:FT W · 649:S.20 |
| FRONT FOOT LENGTH | 2 | 409:FT FR L · 651:S.40 |
| LEG OPENING RELAXED | 2 | 687:F.5 · 532:F5 |
| FRONT BOTTOM WIDTH | 2 | 536:E5 · 653:E.1 |
| WAIST WIDTH RELAXED | 2 | 685:C.4 · 523:C4 |
| FOOT LENGTH | 2 | 410:FT L · 648:S.19 |
| ELBOW WIDTH | 2 | 496:IC1 · 468:JJ |
| WAIST WIDTH EXTENDED | 2 | 686:C.1 · 524:C1 |
| ELASTIC LOCATION | 2 | 416:EL POS · 672:V.9 |
| LEG OPENING EXTENDED | 2 | 688:F.6 · 533:F6 |
| FOOT WIDTH LOCATION | 2 | 412:FT W POS · 650:S.39 |
| SLEEVE LENGTH | 2 | 292:SL · 503:I |
| BACK WIDTH | 2 | 420:A.2 · 517:A2 |

El mateix concepte existeix dues vegades perquè hi va arribar per dos camins
(`origen_import = 'diccionari:LOS:2026-07-18'` vs un UUID de sessió d'import), i **l'unicitat
`(customer, client_code)` de `CustomerPOMAlias` ho permet perquè `"C4" ≠ "C.4"`**:

| pom_id | client_code | client_description | description_en | origen | client |
|---|---|---|---|---|---|
| 685 | C.4 | WAIST WIDTH RELAXED | — | IMPORT | LOSAN IBERIA SA |
| 686 | C.1 | WAIST WIDTH EXTENDED | — | IMPORT | LOSAN IBERIA SA |
| 523 | C4 | — | WAIST WIDTH RELAXED | DICCIONARI | LOSAN IBERIA SA |
| 524 | C1 | — | WAIST WIDTH EXTENDED | DICCIONARI | LOSAN IBERIA SA |
| 687 | F.5 | LEG OPENING RELAXED | — | IMPORT | LOSAN IBERIA SA |
| 688 | F.6 | LEG OPENING EXTENDED | — | IMPORT | LOSAN IBERIA SA |
| 532 | F5 | — | LEG OPENING RELAXED | DICCIONARI | LOSAN IBERIA SA |
| 533 | F6 | — | LEG OPENING EXTENDED | DICCIONARI | LOSAN IBERIA SA |

> **FET, no interpretació:** avui **la instància ja té una implementació — encunyar catàleg**. El seu cost
> és fragmentació del diccionari de casa, àlies duplicats per client, i graduació duplicada.

### C3 · Taula de freqüències amb classificació

Recompte al corpus nuclear (1 168 textos), amb frontera de paraula (`\y`). La columna «Dimensió» és
`💡 PROPOSTA (a validar)` — **la classificació és decisió de la Montse**; el recompte és FET.

| Terme | Catàleg | Àlies | Model | **Total** | Dimensió proposada |
|---|---|---|---|---|---|
| WIDTH | 191 | 94 | 65 | **350** | TAG · eix de mesura |
| LENGTH | 139 | 69 | 37 | **245** | TAG · eix de mesura |
| **FRONT** | 87 | 45 | 31 | **163** | **INSTÀNCIA o POM** ⚠️ ambigu (§C4) |
| POCKET | — | — | — | **151** | TAG · element de peça |
| **BACK** | 70 | 39 | 32 | **141** | **INSTÀNCIA o POM** ⚠️ ambigu (§C4) |
| LOCATION | 69 | 38 | 17 | **124** | TAG · eix de mesura |
| HEIGHT | 54 | 27 | 17 | **98** | TAG · eix de mesura |
| OPENING | 56 | 22 | 13 | **91** | TAG · eix de mesura |
| **RELAXED** | 34 | 11 | 7 | **52** | **QUALIFICADOR D'INSTÀNCIA** ⭐ |
| BOTTOM | 26 | 9 | 13 | **48** | TAG · posició (part del POM) |
| **EXTENDED** | 27 | 15 | 5 | **47** | **QUALIFICADOR D'INSTÀNCIA** ⭐ |
| SIDE | 22 | 17 | 8 | **47** | TAG · posició |
| DROP | 13 | 11 | 15 | **39** | TAG · eix de mesura |
| SEAM | 10 | 6 | 23 | **39** | TAG · punt de referència |
| FROM | 9 | 5 | 24 | **38** | **SOROLL** |
| **1/2** | 4 | 1 | 24 | **29** | TAG · **mètode** (mitja mesura vs contorn) |
| RISE | 12 | 10 | 6 | **28** | TAG · eix de mesura |
| **INNER** | 16 | 9 | 1 | **26** | **CAPA o INSTÀNCIA** ⚠️ ambigu (§C4) |
| **STRETCHED** | 19 | 3 | 1 | **23** | **QUALIFICADOR D'INSTÀNCIA** ⭐ |
| CENTER | 13 | 7 | 3 | **23** | TAG · punt de referència |
| POSITION | 14 | 5 | 4 | **23** | TAG · eix de mesura (sinònim de LOCATION) |
| HPS | 10 | 0 | 12 | **22** | TAG · punt de referència |
| TOTAL | 8 | 9 | 5 | **22** | TAG |
| GIRTH | 18 | 0 | 0 | **18** | TAG · eix de mesura |
| CB | 9 | 1 | 5 | **15** | TAG · punt de referència |
| ACROSS | 10 | 0 | 4 | **14** | TAG · mètode |
| CF | 9 | 0 | 4 | **13** | TAG · punt de referència |
| DART | 4 | 4 | 4 | **12** | TAG · element de peça |
| FLOUNCE | 8 | 4 | 0 | **12** | TAG · element de peça |
| TOP | 9 | 2 | 1 | **12** | TAG · posició |
| ALONG | 3 | 0 | 8 | **11** | **SOROLL** (mètode implícit) |
| CENTRE | 2 | 2 | 7 | **11** | TAG · **variant ortogràfica de CENTER** |
| HSP | 0 | 2 | 9 | **11** | TAG · **variant/error tipogràfic d'HPS** |
| PLEAT | 6 | 3 | 2 | **11** | TAG · element de peça |
| **LINING** | 5 | 1 | 4 | **10** | **CAPA** → `folre` ⭐ |
| DEPTH | 6 | 1 | 3 | **10** | TAG · eix de mesura |
| PLACEMENT | 8 | 0 | 0 | **8** | TAG · eix de mesura |
| CIRCUMFERENCE | 8 | 0 | 0 | **8** | TAG · eix de mesura |
| SPACING | 8 | 0 | 0 | **8** | TAG · eix de mesura |
| INCL | 1 | 3 | 4 | **8** | TAG · mètode |
| MEASURED | 3 | 3 | 2 | **8** | **SOROLL** |
| W/FLAP | 5 | 3 | 0 | **8** | TAG · variant constructiva |
| EXCL | 2 | 2 | 2 | **6** | TAG · mètode |
| SWIMWEAR | 6 | 0 | 0 | **6** | TAG · segment de producte |
| FRILL | 4 | 1 | 0 | **5** | TAG · element de peça |
| HALF | 2 | 2 | 1 | **5** | TAG · mètode (sinònim d'`1/2`) |
| RUFFLE | 2 | 2 | 0 | **4** | TAG · element de peça |
| SWEEP | 2 | 0 | 2 | **4** | TAG · eix de mesura |
| KNITWEAR | 2 | 0 | 0 | **2** | TAG · segment de producte |
| UPPER | 2 | 0 | 0 | **2** | INSTÀNCIA (posicional) — **massa escàs per decidir** |
| FOLDED | 1 | 0 | 0 | **1** | QUALIFICADOR D'INSTÀNCIA — **massa escàs** |
| AT · TO · IN · THE · ON · OVER · BEFORE | — | — | — | **35·26·9·6·3·3·3** | **SOROLL** |

**Termes del brief amb ZERO ocurrències al corpus nuclear** (`NO EXISTEIX`, confirmat per `SELECT`):

`LEFT` · `RIGHT` · `LH` · `RH` · `DX` · `SX` · `GATHERED` · `SHIRRED` · `LOWER` · `OUTER` · `SHELL` ·
`INTERFACING` · `FUSING` · `PADDING` · `TRIM` · `UNDERLINING` · `LINED` · `CONTRAST` · `SELF` · `BINDING` ·
`DOUBLE` · `SINGLE` · `OPEN` (aïllat; les 91 ocurrències són `OPENING`) · `CLOSED` · `FLAT` · `ELASTICATED`.

*Al corpus de DEFINICIÓ (`pomglobal.descripcio_en`/`notes`, 125 textos) sí que hi surten:* `FLAT` 52 ·
`OUTER` 5 · `WITH` 3 · `ELASTICATED` 2 · `CLOSED` 1 · `WITHOUT` 1. **Són text de mètode de mesura, no
nomenclatura** — no candidats a identitat.

**Abreviatures canòniques** (`pomglobal.abbreviation`, 125): `RLX` ×7 · `STR` ×8 · `EXT` ×2 · `L` ×17 ·
`R` ×3. **Ja existeix un vocabulari abreujat de qualificadors al catàleg de la casa** — és el candidat
natural a valors curts d'instància, i **`nom_fitxa` només té 20 caràcters**.

**Termes amb frontera de paraula, contrastats font a font** (corpus ampliat amb `descripcio_en` i
`abbreviation`):

| Terme | n | Fonts on apareix |
|---|---|---|
| FRONT | 183 | alias.client_description · alias.description_en · bm.notes · pomglobal.body_section · pomglobal.descripcio_en · pomglobal.nom_en · pommaster.nom_client |
| BACK | 160 | (les mateixes 7) |
| BOTTOM | 62 | 6 fonts |
| RELAXED | 60 | 6 fonts |
| FLAT | 52 | **només** pomglobal.descripcio_en |
| TOP | 39 | 7 fonts |
| EXTENDED | 39 | 6 fonts |
| STRETCHED | 36 | 5 fonts |
| INNER | 18 | 4 fonts |
| LINING | 9 | alias.description_en · bm.notes · pommaster.nom_client |
| OUTER | 5 | pomglobal.descripcio_en · pomglobal.notes |
| UPPER | 4 | 3 fonts |
| WITH | 3 | pomglobal.descripcio_en · pomglobal.notes |
| ELASTICATED | 2 | pomglobal.descripcio_en · pomglobal.notes |
| CLOSED · FOLDED · FORRO · WITHOUT | 1 c/u | (FORRO només a alias.description_local) |
| HPS | 46 | bm.notes · pomglobal.abbreviation · descripcio_en · nom_en · pommaster.nom_client |
| 1/2 | 29 | alias.client_description · bm.notes · pommaster.nom_client |
| CB | 18 | 5 fonts |
| L (aïllat) | 17 | bm.nom_fitxa · pomglobal.abbreviation |
| CF | 16 | 4 fonts |
| HSP | 11 | alias.client_description · bm.notes |
| STR | 8 | **només** pomglobal.abbreviation |
| HALF | 7 | 6 fonts |
| RLX | 7 | **només** pomglobal.abbreviation |
| R (aïllat) | 3 | **només** bm.nom_fitxa |
| EXT | 2 | **només** pomglobal.abbreviation |

**Qualificadors als àlies de client** (`pom_customerpomalias`, 336 files, tots els camps de text):

| Terme | n |
|---|---|
| FRONT | 43 · BACK 38 · OPEN 22 · EXTENDED 15 · RELAXED 11 · BOTTOM 9 · INNER 9 · STRETCHED 3 · TOP 2 · HALF 2 · LINING 1 · 1/2 1 |

**Els `nom_fitxa` amb `L`/`R` aïllats** (per descartar la hipòtesi de lateralitat):

| nom_fitxa | n | POM apuntat |
|---|---|---|
| `R` | 2 | Neck width |
| `L.3` | 1 | Neck width |
| `L.4` | 1 | FRONT NECK DROP |
| `L.5` | 1 | BACK NECK DROP |
| `R.10` | 1 | FALSE FLY |

→ **`L` i `R` aquí NO són lateralitat**: són prefixos de nomenclatura de secció del client.

### C4 · Les tres ambigüitats que la Montse ha de resoldre

**⚠️ FRONT / BACK (304 ocurrències) — el terme més freqüent i el més ambigu.**
Hi ha **dos usos incompatibles al mateix corpus**:
- `FRONT RISE` (POM 434) i `BACK RISE` (POM 435) → **mesures DIFERENTS**. `FRONT`/`BACK` és part del POM.
- `Front armhole along seam` (POM 457) i `Back armhole along seam` (POM 458) → **la MATEIXA mesura sobre dos
  panells**. Viuen junts als models 163, 174, 268, 269 (verificat). Això **és** instància.

Cap regla automàtica els distingeix. **Decisió humana, POM a POM.**

**⚠️ INNER (26) — capa o posició?**
- `CUFF HEIGHT INNER`, `CUFF OPENING INNER` → l'interior del puny: **candidat a capa `folre`**.
- `INNER POCKET LENGTH/WIDTH/LOCATION/FLAP HEIGHT`, `INNER ELASTIC WAIST LOCATION` → **butxaca interior**:
  és un ELEMENT diferent, no una capa. Model 396 en té una (`C.12`).

**⚠️ 1/2 i HALF (34) — mètode, no instància.**
`1/2 chest width (armpit to armpit)`, `HIP WIDTH (1/2)`, `1/2 Bicep width`, `1/2 bottom width relaxed`.
Diu **com** es mesura (mig contorn sobre pla), no **quina** de dues. Si passés a instància, `HIP WIDTH` i
`HIP WIDTH (1/2)` serien dues instàncies del mateix POM amb valors que no es poden comparar.
💡 **PROPOSTA (a validar):** és el cas de manual per a «tag descriptiu que MAI entra en clau».

### C5 · Esborrany de diccionari inicial

`💡 PROPOSTA (a validar) — llest perquè la Montse el beneeixi UNA vegada.` Anglès com a llengua pivot.
Cada entrada: terme canònic → dimensió → valor → variants observades al corpus (amb recompte).

**DIMENSIÓ `capa`** *(ja existeix com a columna; el catàleg de 6 està sembrat)*

| Terme EN | Valor (slug) | Variants observades | n |
|---|---|---|---|
| LINING | `folre` | `LINING` (10), `FORRO` (1, `description_local`) | 11 |
| SHELL / OUTER | `exterior` | `OUTER` (5, només a definicions) | 5 |
| INTERFACING · PADDING · UNDERLINING · TRIM | `entretela`·`farciment`·`reforc`·`fornitura` | **cap ocurrència al corpus** | 0 |

**DIMENSIÓ `instancia` — eix ESTAT DE LA PEÇA** ⭐ *(el més sòlid: 122 ocurrències, 25 troncs, 3 casos vius)*

| Terme EN | Valor proposat | Variants observades | n |
|---|---|---|---|
| RELAXED | `relaxed` | `RELAXED` (52), `RLX` (7, `abbreviation`), `(relaxed)` en parèntesi | 59 |
| EXTENDED | `extended` | `EXTENDED` (47), `EXT` (2) | 49 |
| STRETCHED | `stretched` | `STRETCHED` (23), `STR` (8) | 31 |
| FOLDED | `folded` | `FOLDED` (1) | 1 |

⚠️ `EXTENDED` i `STRETCHED` **conviuen al mateix tronc**: `LEG OPENING` en té les tres, `SLEEVE OPENING`
també, `CHEST WIDTH` en té RELAXED+STRETCHED **i** RELAXED+EXTENDED per camins diferents.
**Són sinònims o dos estats distints? Decisió de la Montse** — i determina si el diccionari en té 3 valors o 2.

**DIMENSIÓ `instancia` — eix PANELL** ⚠️ *(pendent de §C4)*

| Terme EN | Valor proposat | Variants | n |
|---|---|---|---|
| FRONT | `front` | `FRONT` (163), `CF` (13), `FR` (5, `nom_fitxa`) | 181 |
| BACK | `back` | `BACK` (141), `CB` (15), `BK` (5, `nom_fitxa`) | 161 |

**DIMENSIÓ `instancia` — eix LATERALITAT** 🔴 *(el cas del brief)*

| Terme EN | Valor proposat | Variants | n |
|---|---|---|---|
| LEFT | `left` | — | **0** |
| RIGHT | `right` | — | **0** |

**NO EXISTEIX al corpus.** El vocabulari s'hauria d'introduir de zero. `pomglobal.abbreviation` sí que porta
`L` (17) i `R` (3) — **però són abreviatures de *Length* i altres, no de laterality** (verificat: els
`nom_fitxa` amb `R` aïllat apunten a *Neck width*). **Cap suport del corpus per a l'eix del cas d'exemple.**

**DIMENSIÓ `tag` — descriptius que MAI entren en clau**

| Grup | Termes (n) |
|---|---|
| Eix de mesura | WIDTH (350) · LENGTH (245) · LOCATION (124) · HEIGHT (98) · OPENING (91) · DROP (39) · RISE (28) · POSITION (23) · GIRTH (18) · DEPTH (10) · CIRCUMFERENCE (8) · PLACEMENT (8) · SPACING (8) · SWEEP (4) |
| Punt de referència | SEAM (39) · CENTER/CENTRE (34) · HPS/HSP (33) · CB (15) · CF (13) |
| Mètode | 1/2 (29) · ACROSS (14) · INCL (8) · EXCL (6) · HALF (5) |
| Element de peça | POCKET (151) · COLLAR (46) · CUFF (37) · FLAP (29) · YOKE (23) · DART (12) · FLOUNCE (12) · PLEAT (11) · FRILL (5) · RUFFLE (4) · W/FLAP (8) |
| Posició | BOTTOM (48) · SIDE (47) · TOP (12) · UPPER (2) |
| Segment | SWIMWEAR (6) · KNITWEAR (2) |

**SOROLL — mai al diccionari:** `FROM` (38) · `AT` (35) · `TO` (26) · `ALONG` (11) · `MEASURED` (8) ·
`IN` (9) · `THE` (6) · `ON`/`OVER`/`BEFORE` (3 c/u) · `/` (18).

**Normalitzacions que el diccionari hauria de portar de sèrie** *(FETS del corpus)*:
`CENTER` ≡ `CENTRE` (23 vs 11) · `HPS` ≡ `HSP` (22 vs 11 — **`HSP` sembla error tipogràfic propagat**) ·
`LOCATION` ≡ `POSITION` (124 vs 23) · `1/2` ≡ `HALF` (29 vs 5) · caixa **no** normalitzada al corpus
(conviuen `Chest width (relaxed)` i `CHEST WIDTH RELAXED` com a **POMs diferents**: 331/518).

### C6 · Aprenentatge del wizard al diccionari — el camí ja existeix

El marc parla d'«aprenentatge directe del wizard al diccionari». **Ja hi ha la maquinària**:
`maybe_learn_customer_alias` (`pom/services.py:578-640`) aprèn àlies del client en confirmar l'import
(cridada des de `extraction_views.py:2540-2542` i `:2567-2569`, amb `nomes_si_manual=False`), i marca
`pendent_revisio=True` quan detecta col·lisió (`:613-622`). El que **NO EXISTEIX** és un equivalent que
aprengui **termes de dimensió** (qualificadors, capes, tags) — només aprèn el parell `(client_code → pom)`.

---

## I.D · FASE D — CAS DE PROVA

### D1 · El cas real trobat: model 396 · LOS-SS27-0122 · EXPLORER

**Dos parells d'instàncies vives**, tots dos `origen = IMPORTED`, tots dos a `capa = exterior`.
Volcat complet de les 20 mesures del model:

| bm | pom | codi_client | nom_client | nom_fitxa | valor | ordre | origen | capa |
|---|---|---|---|---|---|---|---|---|
| **1665** | **685** | C.4 | **WAIST WIDTH RELAXED** | `C.4` | **21,0** | 0 | IMPORTED | exterior |
| **1666** | **686** | C.1 | **WAIST WIDTH EXTENDED** | `C.1` | **26,5** | 1 | IMPORTED | exterior |
| 1667 | 386 | D.11-M79 | HIP LOCATION | D.11 | 11 | 2 | IMPORTED | exterior |
| 1668 | 308 | HI PA | Hip width (pants) | D | 26,5 | 3 | IMPORTED | exterior |
| 1669 | 434 | T.1 | FRONT RISE | T.1 | 15,8 | 4 | IMPORTED | exterior |
| 1670 | 435 | T.2 | BACK RISE | T.2 | 20,3 | 5 | IMPORTED | exterior |
| 1671 | 389 | M-M79 | TOTAL LENGTH | M | 35 | 6 | IMPORTED | exterior |
| 1672 | 309 | THI | Thigh width | D.1 | 14,2 | 7 | IMPORTED | exterior |
| 1673 | 529 | D22 | KNEE LOCATION | D.22 | 23 | 8 | IMPORTED | exterior |
| 1674 | 310 | KNE | Knee width | D.2 | 11,4 | 9 | IMPORTED | exterior |
| **1675** | **687** | F.5 | **LEG OPENING RELAXED** | `F.5` | **7,5** | 10 | IMPORTED | exterior |
| **1676** | **688** | F.6 | **LEG OPENING EXTENDED** | `F.6` | **9,5** | 11 | IMPORTED | exterior |
| 1677 | 299 | CUF H | Cuff height | S.5 | 1,5 | 12 | IMPORTED | exterior |
| 1678 | 320 | WB H | Waistband height | C.11 | 3 | 13 | IMPORTED | exterior |
| 1679 | 543 | R10 | FALSE FLY | R.10 | 11,1 | 14 | IMPORTED | exterior |
| 1680 | 617 | C12 | INNER ELASTIC WAIST LOCATION | C.12 | 4 | 15 | IMPORTED | exterior |
| 1681 | 602 | O41 | SIDE POCKET LOCATION | O.41 | 17 | 16 | IMPORTED | exterior |
| 1682 | 478 | EL | FLAP WIDTH | O.36 | 3 | 17 | IMPORTED | exterior |
| 1683 | 349 | PKT W | Pocket width | O.38 | 8,5 | 18 | IMPORTED | exterior |
| 1684 | 600 | O39 | SIDE POCKET LENGTH | O.39 | 8,5 | 19 | IMPORTED | exterior |

**Com estan gravades avui — el workaround, pas a pas:**

1. **El document ho va dir bé.** Les dues files portaven nomenclatures diferents (`C.4` / `C.1`) → el guard
   `_apply_many_to_one_guard` **no va disparar** (només mira destí duplicat, §A6). Si el document hagués
   posat `C.1` a les dues, l'import les hauria desactivades totes dues.
2. **L'import va encunyar dos POMs nous al catàleg**: 685/686 i 687/688, amb
   `origen_import = '20de40e7-f86b-472f-a514-c0f7637509d0'` (UUID de sessió), `pendent_revisio = TRUE` i
   **`pom_global_id = NULL`** — és a dir, **fora del diccionari canònic de la casa**.
3. **El catàleg ja tenia el mateix concepte**: `LOSPOM-523/524` *WAIST WIDTH RELAXED/EXTENDED* (POMs 523/524,
   `codi_client` `C4`/`C1`) i `LOSPOM-532/533` per a LEG OPENING (`F5`/`F6`), sembrats el 18/07 pel
   diccionari LOS. **Els nous no s'hi van fusionar perquè `"C.4" ≠ "C4"`.**
4. **LOSAN va acabar amb quatre àlies per a dos conceptes** (taula a §C2). **L'unicitat
   `(customer, client_code)` ho permet i ho fa invisible**, perquè `pom/nomenclatura.py:32-41` només en
   mostra un per POM.
5. **El cost aigües avall és real i mesurat**: models 396+170 tenen **120 `GradedSpec`**, **20
   `ModelGradingRule`** i **20 `MeasurementChangeLog`**. Cada instància gradua per separat, amb regla pròpia,
   i **`ModelGradingRule` no té `capa`** (`models_app/models.py:960`) — o sigui que amb la instància com a
   columna aquesta taula també hauria de decidir.

### D2 · Segon i tercer cas

**Models amb 2+ variants del mateix tronc coexistint** (SQL exhaustiu sobre tot `fhort`):

| model | codi_intern | tronc | # inst. | detall |
|---|---|---|---|---|
| 170 | BRW-FW26-0008 | WAISTBAND WIDTH | 2 | RELAXED (bm 1119, pom 318, **NULL** cm) · STRETCHED (bm 1120, pom 319, **NULL** cm) |
| 396 | LOS-SS27-0122 | LEG OPENING | 2 | EXTENDED (bm 1676, pom 688, 9,5) · RELAXED (bm 1675, pom 687, 7,5) |
| 396 | LOS-SS27-0122 | WAIST WIDTH | 2 | EXTENDED (bm 1666, pom 686, 26,5) · RELAXED (bm 1665, pom 685, 21) |

- **Model 170 · BRW-FW26-0008 · Short BERLIN Rayas**: tots dos POMs **sí** tenen canònic
  (`POM-050`/`POM-051`), o sigui que **la duplicació ve del catàleg de la casa, no de l'import.**
- **Models 163, 174, 268, 269** — el cas més proper al del brief: la mateixa mesura (sisa al llarg de la
  costura) presa sobre **dos panells**, resolta amb dos POMs i dues nomenclatures:

| model | codi_intern | bm | pom | nom_client | valor | nom_fitxa |
|---|---|---|---|---|---|---|
| 163 | BRW-FW26-0001 | 1385 | 457 | Front armhole along seam | 21,5 | S |
| 163 | BRW-FW26-0001 | 1386 | 458 | Back armhole along seam | 24 | S2 |
| 174 | BRW-FW26-0012 | 1770 | 457 | Front armhole along seam | 23 | S |
| 174 | BRW-FW26-0012 | 1771 | 458 | Back armhole along seam | 24 | S2 |
| 268 | BRW-FW27-0001 | 1475 | 457 | Front armhole along seam | 23 | (buit) |
| 268 | BRW-FW27-0001 | 1476 | 458 | Back armhole along seam | 24 | (buit) |
| 269 | BRW-FW27-0002 | 1531 | 457 | Front armhole along seam | 23 | S |
| 269 | BRW-FW27-0002 | 1532 | 458 | Back armhole along seam | 24 | S2 |

- **Model 162 / 182 (OLIVIA DRESS)** — **la CAPA també encunyada com a POM**, exactament el patró que C1
  va venir a resoldre:

| model | codi_intern | bm | pom | nom_client | valor | nom_fitxa |
|---|---|---|---|---|---|---|
| 162 | BRW-SS26-0001 | 637 | 383 | Lining Length at Center Back | 61 | 2 |
| 162 | BRW-SS26-0001 | 638 | 384 | Lining Bottom Width Along Hem | 78 | F1 |
| 162 | BRW-SS26-0001 | 640 | 429 | Lining Length at Center Front | — | (buit) |
| 182 | BRW-26-SS-0002 | 922 | 383 | Lining Length at Center Back | 61 | 2 |
| 182 | BRW-26-SS-0002 | 923 | 384 | Lining Bottom Width Along Hem | 78 | F1 |
| 182 | BRW-26-SS-0002 | 921 | 429 | Lining Length at Center Front | — | (buit) |
| 396 | LOS-SS27-0122 | 1680 | 617 | INNER ELASTIC WAIST LOCATION | 4 | C.12 |

### D3 · El cas del brief: NO EXISTEIX

Cerca exhaustiva a `fhort` i `los`:

| Cerca | Resultat |
|---|---|
| `LEFT`/`RIGHT`/`LH`/`RH`/`DX`/`SX` a tot el corpus | **0** |
| `GATHERED`/`SHIRRED`/`FRUNZ` | **0** |
| POMs amb sufix de secció al codi (`(`, `)`, `_TOP`, `_PANT`, `PANTIE`) | **0** |
| `models_app_basemeasurement.seccio` informada | **0 de 760** |
| Models amb `nom_fitxa` duplicat dins el model | **0** |

**Tops i candidats propers.** Model **169 · BRW-FW26-0007 · Top AMELIA** (29 mesures) — cens complet
consultat: té `Armhole depth` (284) i `Armhole circumference` (285) **una sola vegada cadascun**, sense cap
rastre de lateralitat. Volcat complet:

| bm | pom | codi_client | nom_client |
|---|---|---|---|
| 1084 | 273 | CH | Chest width |
| 1085 | 275 | WA | Waist width |
| 1086 | 276 | HI | Hip width (top) |
| 1087 | 277 | SH | Shoulder width |
| 1088 | 278 | AC SH | Across shoulder (back) |
| 1089 | 279 | AC FR | Across front |
| 1090 | 280 | AC BK | Across back |
| 1091 | 281 | BL HPS | Body length (HPS front) |
| 1092 | 282 | BL CB | Body length (CB) |
| 1093 | 283 | SS | Side seam length |
| 1094 | 284 | AH DEP | **Armhole depth** |
| 1095 | 285 | AH CIRC | **Armhole circumference** |
| 1096 | 286 | SH DR | Shoulder drop |
| 1097 | 292 | SL | Sleeve length |
| 1098 | 293 | SL UA | Sleeve length (underarm) |
| 1099 | 295 | BIC | Sleeve width at bicep |
| 1100 | 296 | ELB | Sleeve width at elbow |
| 1101 | 297 | SL OP | Sleeve opening / Cuff width |
| 1102 | 301 | NK W | Neck width |
| 1103 | 302 | NK DR FR | Neck drop front |
| 1104 | 303 | NK DR BK | Neck drop back |
| 1105 | 307 | NK CIRC RLX | Neckband circumference (relaxed) |
| 1106 | 327 | HEM W | Bottom hem width |
| 1107 | 328 | HEM ALL | Hem allowance |
| 1108 | 341 | ZIP L | Zipper length |
| 1109 | 348 | PKT OP | Side pocket opening |
| 1110 | 349 | PKT W | Pocket width |
| 1111 | 355 | LBL CF | Label placement (CF distance) |
| 1112 | 356 | LOGO HPS | Logo / print placement (from HPS) |

Model **1062 · LOS-SS27-0788 · HALTER** existeix però **té 0 `BaseMeasurement`**.
Els models `CRUZADO` (596), `DALIA` (545, 1109) i `AMARANTA` (1108) — els del cas bikini TOP/PANTIE ajornat a
`INFORME_FASE1_TANCAMENT_LOSAN.md:58` — **tenen tots 0 mesures**: la decisió es va ajornar i **segueix sense
implementar** (ja constatat a `DIAGNOSI_MULTIPECA_DALIA.md` §Q2, i re-verificat).

**POMs d'ARMHOLE/SHOULDER/STRAP en ús a tots els models:**

| nom_client | # models | models |
|---|---|---|
| Armhole depth | 21 | 1255,1302,162,163,164,165,166,167,168,169,174,175,182,185,247,267,268,269,294,467,548 |
| Shoulder drop | 19 | 1255,1302,163,…,548 |
| Shoulder width | 19 | 1255,1302,163,…,548 |
| Across shoulder (back) | 18 | 1255,1302,163,…,467 |
| Armhole circumference | 14 | 1255,1302,164,…,294 |
| **Front armhole along seam** | **4** | **163,174,268,269** |
| **Back armhole along seam** | **4** | **163,174,268,269** |
| Shoulder Forward | 4 | 163,174,268,269 |
| SHOULDER MOVE FORWARD | 2 | 1255,1302 |
| SHOULDER TO SHOULDER | 1 | 548 |
| Last button measured from armhole seam | 1 | 163 |
| Sleeve length from CB over shoulderpoint (incl cuff) | 1 | 269 |

**Els 26 models amb mesures** (de 1 055 a `fhort`):

| model | codi_intern | nom_prenda | #bm |
|---|---|---|---|
| 268 | BRW-FW27-0001 | Blusa POP | 48 |
| 1302 | FTT-SS26-0001 | Test Agus | 47 |
| 1255 | LOS-ASSAIG-0007 | Assaig 7 | 46 |
| 164 | BRW-FW26-0002 | Blusa CLIMENTA Estampado | 37 |
| 185 | FTT-FW27-0001 | Test camisa | 37 |
| 175 | BRW-FW26-0013 | Blusa LLOYD | 37 |
| 166 | BRW-FW26-0004 | Blusa MEREDITH | 37 |
| 165 | BRW-FW26-0003 | Blusa RUFUS STARS | 37 |
| 167 | BRW-FW26-0005 | Blusa OWEN | 37 |
| 267 | BRW-26-FW-0036 | [QA-S10] Blusa RUFUS STARS | 37 |
| 168 | BRW-FW26-0006 | Vestido LEXI | 35 |
| 294 | LOS-SS27-0020 | AZKENA | 34 |
| 169 | BRW-FW26-0007 | Top AMELIA | 29 |
| 247 | BRW-FW26-0016 | TWIST | 29 |
| 548 | LOS-SS27-0274 | VEGA | 26 |
| 269 | BRW-FW27-0002 | POP | 25 |
| 163 | BRW-FW26-0001 | Blusa TATE Crudo | 25 |
| 170 | BRW-FW26-0008 | Short BERLIN Rayas | 22 |
| 174 | BRW-FW26-0012 | Blusa CALLIE | 21 |
| 1256 | LOS-ASSAIG-0008 | Assaig 8 | 20 |
| 396 | LOS-SS27-0122 | EXPLORER | 20 |
| 186 | FTT-CO27-0001 | Test pantaló | 20 |
| 162 | BRW-SS26-0001 | OLIVIA DRESS | 16 |
| 182 | BRW-26-SS-0002 | [QA-SC] OLIVIA DRESS | 16 |
| 467 | LOS-SS27-0193 | PETALIA | 12 |
| 188 | BRW-SS27-0001 | ROSALIA | 10 |

**Només 26 models de 1 055 tenen mesures** (760 files, màx. 48 per model). El corpus de mesures és petit i
concentrat: qualsevol conclusió sobre freqüència d'instàncies **té aquesta base**.

> **Veredicte FASE D:** el cas d'exemple del brief no existeix a staging i el corpus no en té ni vocabulari.
> **El cas real i mesurable és l'eix ESTAT (relaxed/extended/stretched)**, amb 3 models vius, 43 POMs de
> catàleg i graduació duplicada. **Qualsevol prova d'acceptació hauria d'anar sobre el model 396**, no sobre
> un top asimètric hipotètic.

---

## I.E · TAULA FINAL DE RISCOS

| # | Peça | Estat | Ancoratge | Risc |
|---|---|---|---|---|
| 1 | Columna d'instància a qualsevol taula | **NO EXISTEIX** | cap camp `instancia`/`instance`/`variant`/`component` als 3 `models.py` de domini (l'únic `component` és `commerce/models.py:166`, sense relació amb POMs) | — |
| 2 | Clau `(model, pom, capa)` | **EXISTEIX i bloqueja** | `models_app/models.py:725` | **ALT** |
| 3 | Unicitats amb `pom_id` a la cadena | **14** (9 amb capa, 5 sense) | §A1 | **ALT** |
| 4 | `patterns.PatternPOM` fora del cens del pla | **EXISTEIX, contradiu la premissa** | `patterns/models.py:430-432` | **ALT** — el comentari nega explícitament la instància |
| 5 | `_load_base_measurements` → `{pom_id: valor}` | **EXISTEIX, col·lapsa** | `pom/services.py:767-783` | **CRÍTIC** — zona intocable, decisió humana |
| 6 | `_materialize_lines` `exclude(pom_id__in=…)` | **EXISTEIX, col·lapsa repetidament** | `models_app/services_size_check.py:33-42` | **CRÍTIC** — la 2a instància no rep mai validació |
| 7 | Clau natural de federació 2-tupla | **EXISTEIX, col·lapsa** | `tenants/federation_service.py:542-552`, `:689`, `:722` | **CRÍTIC** — informe verd amb mitja fitxa perduda |
| 8 | Dicts `{pom_id: …}` en memòria | **24** | §A5.8 | **ALT** — no peten: pinten |
| 9 | Escriptors cecs classificats | **~45** (28 🔴 · 7 🟠 · 9 🟡) | §A2 | **ALT** |
| 10 | Soft-delete per `pom_id` sol | **EXISTEIX** | `models_app/views.py:1943-1946` | **ALT** — no es pot desactivar una instància |
| 11 | Gate «≥3 POMs» del wizard | **EXISTEIX, comptaria malament** | `pom/wizard_views.py:252-257` | Mitjà |
| 12 | Contractes d'API amb `pom_id` com a clau de dict | **5** | `grading_views.py:62`; `s11_views.py:161`; `pom_placement_views.py:113`; `views.py:1793`; `patterns/engine/ports.py:60` | **ALT** — la comporta C1 no els protegeix |
| 13 | POMPlacement: dues cotes del mateix POM | **IMPOSSIBLE ×4** | `models.py:1340`; `pom_placement_views.py:135`, `:52-64`; `TechSheetEditor.jsx:6729-6734` | **ALT** |
| 14 | Unicitat sobre els noms del model | **NO EXISTEIX** | `models_app/models.py:637`, `:681`, `:686` | — (terreny net: 0 duplicats) |
| 15 | Escriptors de `nom_fitxa` sense `strip()` ni guard | **8** | §A3 | **ALT** — 3 amb text extern |
| 16 | Cascades de precedència del nom | **5 divergents** | §A3 | Mitjà |
| 17 | `codi_client` duplicat al catàleg | **12 col·lisions reals** | SQL; `pom/wizard_views.py:465` sense guard | **ALT** — no pot ser component d'identitat |
| 18 | Guard `many_to_one` (import) | **EXISTEIX, bloqueja el cas nou** | `extraction_views.py:1148-1193`, `:1268-1273` | **ALT** |
| 19 | Guard de col·lisió R1 (size-map) | **EXISTEIX, 400** | `pom/size_map_views.py:671-695` | **ALT** — decisió CTO contrària |
| 20 | Guard d'àlies `pendent_revisio` | **EXISTEIX** | `pom/services.py:613-622` | Mitjà — casos reals BRW `F`/`FF`, `U`/`U2`/`U3` |
| 21 | Graella del pas 3 per `pom_master_id` | **EXISTEIX, fusiona al front** | `ImportWizard.jsx:626-637`, `:536-537` | **ALT** |
| 22 | UI per declarar «dues instàncies legítimes» | **NO EXISTEIX** | `ResolPanel` `ImportWizard.jsx:1194-1208` (2 accions) | — |
| 23 | JSONB en clau/unicitat al repo | **NO EXISTEIX** (20 `JSONField`, cap en clau) | grep `--include=models.py` | — precedent nul per a F2 |
| 24 | Índexs GIN al schema `fhort` | **0** | `pg_indexes` | — precedent nul per a F2 |
| 25 | Motlle C1 reutilitzable | **EXISTEIX i auditat** | 9 taules · 20 comportes · pin `test_capa_comporta_c1.py:30-38` | Baix — actiu a favor de F1/F3 |
| 26 | Instància encunyada com a POM de catàleg | **EXISTEIX ×43 POMMaster / 27 POMGlobal** | §C2 | **ALT** — fragmenta el diccionari de casa |
| 27 | `nom_client` duplicat a `POMMaster` | **15** | §C2 | Mitjà |
| 28 | Cas viu d'instància | **EXISTEIX** (models 396, 170, 163/174/268/269) | §D1-D2 | — és el banc de proves |
| 29 | Cas del brief (top asimètric L/R) | **NO EXISTEIX** · vocabulari 0 | §D3 | — cal introduir el terme de zero |
| 30 | Bateig del model (`nom_canonic_model`/`nom_traduit_model`) | **0 files informades de 760** | SQL | — terreny verge |
| 31 | `seccio` informada | **0 de 760** | SQL | — el tag de secció tampoc s'ha estrenat |
| 32 | Sortida barata `GarmentSet` | **DESCARTADA per dades** (0/0/0) | SQL | — tanca el «pendent de verificar» del 21/07 |
| 33 | `MeasurementChangeLog` sense `capa` estampada | **FORAT VIU** | `models_app/signals.py:299-310` | Mitjà — ja anotat a Onada 2; la instància el repetiria |
| 34 | `PieceFittingLine` clonada sense `capa` | **FORAT VIU** | `fitting/services.py:329-338` | Mitjà — anotat, fora d'aquest encàrrec |

---
---
# PART II · REGISTRE D'EXECUCIÓ

**Mètode: triangulació.** Tres camins independents, sis investigadors en paral·lel:
**Camí 1** des dels models (related_name inclosos, el forat clàssic del grep) ·
**Camí 2** des dels contractes (12 `urls.py` sencers → OpenAPI → frontend, backoffice inclòs) ·
**Camí 3** des de les dades (qui pobla de debò cada taula a staging).

---

## II.0 · RESUM EXECUTIU DEL REGISTRE

**1. L'accident ja està armat, i no l'espera la instància: l'espera C4.**
`pom/services.py:1033-1043` — `_upsert_graded_spec`, **l'escriptor únic de tot el motor de grading** — fa
`update_or_create(grading_version_id, pom_id, size_label)`. La unicitat de `GradedSpec` és
`('grading_version','pom','size_label','capa')` **des de C1** (`fitting/models.py:220`). **El lookup ja
diverge de l'esquema avui**; l'únic que ho tapa és la comporta `CHECK capa='exterior'`. **Retirar les
comportes a C4 sense tocar aquest node és l'accident**, sense que cap instància hi hagi entrat.
Té set germans exactes (§II.10).

**2. Set nodes no s'adapten: s'han de RE-DECIDIR.** No col·lapsen — **bloquegen activament** el cas que
la instància vol legitimar, i ho fan amb acta escrita al codi (§II.13).

**3. Dos forats d'ONADA 1, no d'instància — peten amb la segona CAPA.**
`patterns/views.py:552-556` i `tenants/federation_service.py:593` llegeixen `BaseMeasurement`
**sense àncora `capa`**, perquè `RECENS_DELTA_ONADA1_2026-07-31.md:222-224` va declarar `patterns/*`
fora d'abast i la federació no es va mirar. **No esperen la instància: esperen la capa.**

**4. El green flag «OpenAPI 0 diffs» és cec on més importa.**
**54 dels 80 endpoints de la cadena (68%) declaren `'200': description: No response body`** (§II.12.4).

**5. El patró dominant segueix sent el `dict {pom_id: …}`, i ara està comptat.**
De **831 files brutes** dels sis investigadors → **487 nodes únics** després de deduplicar per
`fitxer:línia`. **COL·LAPSA silenciós: 268.** PETA: 79. IGNORA-2a: 92. OK/⚪: 48.

**6. Un test afirma el col·lapse com a comportament esperat, i demana caure.**
`models_app/test_seccio_captura.py:156` (§II.11.4).

**7. El deute de C1 al copiador de tenants té data de caducitat pròpia.**
`tasks/management/commands/bootstrap_tenant.py:162` (§II.8, §II.10).

**8. La bona notícia: la via sana ja existeix i està provada.** El frontend ja indexa per `bm_id`/PK de
fila a 13 punts, i `TechSheetEditor.jsx:3462` prova `bmById` **abans** que `bmByPom`. I el repo té les
tres peces de mètode que la instància necessita, ja verdes (§II.15).

---

## II.1 · COM LLEGIR EL REGISTRE

### Columnes

| columna | valors |
|---|---|
| **tipus** | `READ-dict` · `READ-list` · `WRITE-create` · `WRITE-update` · `WRITE-delete` · `COUNT-gate` · `CONTRACT-api` · `CONTRACT-engine` |
| **amb 2 inst.** | `COL·LAPSA` (perd dades en silenci) · `PETA` (excepció / IntegrityError) · `IGNORA-2a` (n'agafa una i oblida l'altra) · `OK` |
| **risc** | 🔴 col·lapse silenciós · 🟠 excepció o bloqueig · 🟡 arbitrari / de significat · ⚪ dubte o innocu |

### Vocabulari d'ONADES

| onada | què hi entra | criteri |
|---|---|---|
| **`C1-ins`** | esquema: camp nou, `unique_together`, comporta CHECK, migració, backfill | on neix la columna |
| **`top-up-lectors`** | lectors la clau dels quals **ja va créixer a `(pom, capa)` a l'Onada 1** i només ha de créixer un element més | els 11 fitxers de l'Onada 1 + els 2 forats que en van quedar fora |
| **`Onada2`** | escriptors que han d'estampar la instància | `create` / `update_or_create` / `get_or_create` / poda |
| **`C4-ins`** | contracte d'API o UI — només es mou quan s'alça la comporta | payload, serializer, frontend |
| **`F2-patrons`** | motor de patrons i format d'intercanvi | Fase 2, fora d'aquest tram |
| **`consolidació-catàleg`** | fusió/sembra/àlies de catàleg — no és feina de clau, és de dades | `consolidate_*`, `load/export_*`, `bootstrap_tenant` |
| **`FORA: <motiu>`** | no toca la cadena, o hi és per la regla d'or | sempre amb motiu explícit |

### Els 11 fitxers que l'Onada 1 SÍ va tocar (base de `top-up-lectors`)

Verificat contra els 9 commits vius:

| commit | missatge | fitxers |
|---|---|---|
| `bac914f0` | Onada 1/C1 · les toleràncies i la base de `pom` saben de quina capa parlen | `pom/s10_views.py` · `s11_views.py` · `s6_views.py` · `s8_views.py` |
| `d33b3b67` | Onada 1/C2 · un override de folre no es pot colar a la cel·la de l'exterior | `pom/services.py` |
| `c6bd23a2` | Onada 1/C3 · els quatre mapes de la taula graduada ancoren a l'exterior | `fitting/graded_spec_views.py` |
| `1f0e94cc` | Onada 1/C4 · el Repàs ancora els seus quatre mapes a l'exterior | `fitting/repas_views.py` |
| `0f702096` | Onada 1/C5 · els dos serializers de línia demanen la mesura de la SEVA capa | `fitting/serializers.py` · `models_app/serializers_size_check.py` |
| `33be85a0` | Onada 1/C6 · la cota es materialitza contra la mesura de la seva capa | `models_app/pom_placement_views.py` |
| `5a6e6ac3` | Onada 1/C8 · la sembra de valors STEP té una àncora, no una barreja | `models_app/views.py` |
| `e394c851` | Onada 1/C9 · el carry-forward dels estadis no travessa capes | `models_app/views.py` |
| `362a2134` | Onada 1/C10 · harness de dues capes | `models_app/test_lectors_capa_onada1.py` (nou, 250 línies) |
| `6b431865` | **Revert** "Onada 1/C7 · la taula de mesures ancora les seves DUES fonts a l'exterior" | `pom/grading_views.py` |

**`pom/grading_views.py` NO forma part de `top-up-lectors`: C7 va ser revertit.**

---

## II.2 · TAULA DE CONVERGÈNCIA

### Nodes per camí

| | Camí 1 (models) | Camí 2 (contractes) | Camí 3 (dades) |
|---|---|---|---|
| files brutes emeses | **578** (1A 176 · 1B 285 · 1C 117) | **253** (2A 63 · 2B 158 · 2C 32) | 22 taules × 6 mètriques |
| nodes únics després de deduplicar | **352** | **206** | (no emet nodes de codi) |
| **intersecció 1∩2** | **71** | | |
| **només camí 1** | **281** | | |
| **només camí 2** | | **135** | |
| **TOTAL ÚNIC (1∪2)** | **487** | | |

**Baseline mecànic independent** (grep de verificació, no d'agent):

| mesura | valor |
|---|---|
| referències `<Taula>.objects` a `backend/fhort/` fora de migracions | **547** |
| … `BaseMeasurement` 192 · `GradingRule` 58 · `CustomerPOMAlias` 46 · `ModelGradingRule` 45 · `ItemBaseMeasurement` 39 · `GradedSpec` 37 · `GarmentPOMMap` 33 · `MeasurementChangeLog` 31 · `SizeCheckLine` 21 · `PieceFittingLine` 21 · `ModelGradingOverride` 19 · `ItemBaseSet` 12 · `PatternPOM` 9 · `POMAlert` 8 · `POMPlacement` 3 · `ClientMesuraPerfil` 3 | |
| hits `pom_id\|pomId\|pom_master_id\|bm_id\|byPom` a `frontend/src` | **324** en **23 fitxers** |
| mateixos hits a `frontend-backoffice/src` | **0** |
| `.raw(` a tot el backend | **0** |
| `RunSQL` a totes les migracions | **0** |

Els 487 nodes cauen dins d'aquest sobre.

### Nodes caçats per UN SOL camí — els sospitosos

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

### Lectura de la convergència

- **La intersecció és petita (71/487 = 15%)** i això **és el resultat esperat, no una alarma**: els tres
  camins miren coses diferents. Un cens per un sol camí hauria perdut **entre el 28% i el 58%** dels nodes.
- **El camí 2 va caçar 135 nodes que el camí 1 no pot veure**, i el camí 1 va caçar 281 que el camí 2 no
  pot veure. **Cap dels dos és redundant.**
- **On els tres camins convergeixen és on el risc és màxim**: `pom/services.py:771` i `:1033` ·
  `models_app/extraction_views.py:2560` · `models_app/pom_placement_views.py:52-64,135` ·
  `models_app/services_size_check.py:33-42` · `tenants/federation_service.py:542-552,593`.

---

## II.3 · CAMÍ 1A — `models_app`

**Abast:** `BaseMeasurement` · `MeasurementChangeLog` · `ModelGradingOverride` · `SizeCheckLine` ·
`POMPlacement` · `ModelGradingRule`. **176 files.**

### Tres descobertes que canvien l'abast

**1. Els related_name des de `Model` NO són els que sembla.** Els que el brief donava eren els de
`POMMaster`; els de `Model` són uns altres i tenen ús real:

| model | des de `POMMaster` | **des de `Model`** | línia |
|---|---|---|---|
| `ModelGradingOverride` | `model_grading_overrides` (`:851`) | **`grading_overrides`** | `models_app/models.py:850` |
| `ModelGradingRule` | `model_grading_rules` (`:934`) | **`grading_rules`** | `models_app/models.py:928` |
| `MeasurementChangeLog` | `measurement_changes` (`:774`) | des de `BaseMeasurement`: **`change_log`** | `models_app/models.py:777` |
| `SizeCheckLine` | `'+'` (cap accessor) | des de `SizeCheck`: **`linies`** | `models_app/models.py:1133` |

`model.grading_rules.all().delete()` apareix **5 cops** i és l'única porta de wipe de regles residents.
**Un grep de `model_grading_rules` no en troba cap.**
*(Hi ha un tercer `grading_overrides` a `models_app/models.py:857`, des de `fitting.PieceFitting` —
**0 call sites**.)*

**2. `pom/seed_data/consolidate_pom_los.py:30-34`** porta els related_name com a **STRINGS EN LLISTES DE
CONFIG**, consumides per `getattr(prim, rel)`. Cap grep de codi Django el troba. És el node més invisible
de tot el cens.

**3. `pom/services.py:771` (`_load_base_measurements`)** retorna `{pom_id: base_value_cm}` — sense capa i
sense instància. És el cor del motor i el col·lapse silenciós més gran de tot el camí.

### A · Esquema (`models_app/models.py`)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `models_app/models.py:613` | BaseMeasurement | CONTRACT-engine | FK Model, `related_name='base_measurements'` | OK | ⚪ | C1-ins |
| `models_app/models.py:614` | BaseMeasurement | CONTRACT-engine | FK POMMaster, `related_name='base_measurements'` | OK | ⚪ | C1-ins |
| `models_app/models.py:655` | BaseMeasurement | CONTRACT-engine | comentari que JA declara el forat: «la clau segueix sent `('model','pom')` … separar-les vol tocar la clau, que travessa 5 taules més» | OK (text) | ⚪ | C1-ins |
| `models_app/models.py:725` | BaseMeasurement | CONTRACT-engine | `unique_together=[('model','pom','capa')]` | **PETA** (IntegrityError al 2n insert) | 🟠 | C1-ins |
| `models_app/models.py:730` | BaseMeasurement | CONTRACT-engine | `ordering=['model','capa','ordre','pom']` | IGNORA-2a (ordre no determinista entre instàncies germanes) | 🟡 | C1-ins |
| `models_app/models.py:752` | BaseMeasurement | CONTRACT-engine | `CheckConstraint capa='exterior'` (comporta C1) | OK (ortogonal a la instància) | ⚪ | C1-ins |
| `models_app/models.py:773,774` | MeasurementChangeLog | CONTRACT-engine | FK model/pom `related_name='measurement_changes'` | OK | ⚪ | C1-ins |
| `models_app/models.py:786-788` | MeasurementChangeLog | CONTRACT-engine | FK `base_measurement` SET_NULL, `related_name='change_log'` | OK (però una fila orfe perd la instància si el BM mor) | ⚪ | C1-ins |
| `models_app/models.py:813` | MeasurementChangeLog | CONTRACT-engine | `ordering=['model','pom','created_at']` | IGNORA-2a (barreja històries de dues instàncies) | 🟡 | C1-ins |
| `models_app/models.py:816` | MeasurementChangeLog | CONTRACT-engine | CheckConstraint capa | OK | ⚪ | C1-ins |
| `models_app/models.py:825` | MeasurementChangeLog | WRITE-update | `save()` refusa tot UPDATE (append-only) | **PETA** si el backfill de la instància passa per `save()` | 🟠 | C1-ins |
| `models_app/models.py:831` | MeasurementChangeLog | WRITE-delete | `delete()` refusa (append-only) | **PETA** si el backfill vol re-escriure | 🟠 | C1-ins |
| `models_app/models.py:850` | ModelGradingOverride | CONTRACT-engine | FK Model `related_name='grading_overrides'` **[SOLO-1]** | OK | ⚪ | C1-ins |
| `models_app/models.py:851` | ModelGradingOverride | CONTRACT-engine | FK POMMaster `related_name='model_grading_overrides'` | OK | ⚪ | C1-ins |
| `models_app/models.py:878` | ModelGradingOverride | CONTRACT-engine | `unique_together=[('model','pom','size_label','capa')]` | **PETA** | 🟠 | C1-ins |
| `models_app/models.py:879` | ModelGradingOverride | CONTRACT-engine | `ordering=['model','pom','size_label']` | IGNORA-2a | 🟡 | C1-ins |
| `models_app/models.py:882` | ModelGradingOverride | CONTRACT-engine | CheckConstraint capa | OK | ⚪ | C1-ins |
| `models_app/models.py:900-914` | ModelGradingRule | CONTRACT-engine | docstring: «SENSE `capa`, PER DECISIÓ DE DOMINI (§3c)» | **DECISIÓ OBERTA** | 🟠 | C1-ins |
| `models_app/models.py:933` | ModelGradingRule | CONTRACT-engine | FK Model `related_name='grading_rules'` **[SOLO-1]** | OK | ⚪ | C1-ins |
| `models_app/models.py:934` | ModelGradingRule | CONTRACT-engine | FK POMMaster `related_name='model_grading_rules'`, `db_constraint=False` | OK | ⚪ | C1-ins |
| `models_app/models.py:960` | ModelGradingRule | CONTRACT-engine | `unique_together=[('model','pom')]` | **PETA** si es decideix que la regla és per instància; OK si no | 🟠 | C1-ins |
| `models_app/models.py:1136-1139` | SizeCheckLine | CONTRACT-engine | FK POMMaster amb `related_name='+'` → **cap accessor invers** | OK | ⚪ | C1-ins |
| `models_app/models.py:1162` | SizeCheckLine | CONTRACT-engine | `ordering=['size_check','pom']` | IGNORA-2a | 🟡 | C1-ins |
| `models_app/models.py:1164` | SizeCheckLine | CONTRACT-engine | `unique_together=[('size_check','pom','capa')]` | **PETA** | 🟠 | C1-ins |
| `models_app/models.py:1167` | SizeCheckLine | CONTRACT-engine | CheckConstraint capa | OK | ⚪ | C1-ins |
| `models_app/models.py:1297` | POMPlacement | CONTRACT-engine | FK ItemFitxer `related_name='pom_placements'` | OK | ⚪ | C1-ins |
| `models_app/models.py:1299` | POMPlacement | CONTRACT-engine | FK POMMaster `related_name='placements'` | OK | ⚪ | C1-ins |
| `models_app/models.py:1336` | POMPlacement | CONTRACT-engine | `UniqueConstraint(['item_fitxer','pom','view_slot','capa'])` | **PETA** | 🟠 | C1-ins |
| `models_app/models.py:1340` | POMPlacement | CONTRACT-engine | CheckConstraint capa | OK | ⚪ | C1-ins |
| `models_app/models.py:1345` | POMPlacement | CONTRACT-engine | `Index(['item_fitxer','view_slot'])` | OK | ⚪ | C1-ins |

### B · Signals (`models_app/signals.py`)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `models_app/signals.py:219-234` | BaseMeasurement | READ-dict | `pre_save`: llegeix `_old_value` per `pk` | OK (per pk) | ⚪ | FORA: ancorat a pk |
| `models_app/signals.py:267-278` | MeasurementChangeLog | WRITE-create | `post_save` de la PODA: crea log amb `model`+`pom`; **NO estampa `capa` ni instància** | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/signals.py:299-310` | MeasurementChangeLog | WRITE-create | `post_save` F1: crea log amb `model`+`pom`; **NO estampa `capa` ni instància** | **COL·LAPSA** — dues històries fusionades | 🔴 | Onada2 |

### C · `models_app/views.py`

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `models_app/views.py:500-507` | BaseMeasurement | READ-list | `BaseMeasurementViewSet.queryset`, `ordering=['model','id']` | OK | ⚪ | C4-ins |
| `models_app/views.py:504` | BaseMeasurement | CONTRACT-api | `filterset_fields=['model','pom','is_active','origen']` — `?pom=` promet 1 fila | IGNORA-2a al consumidor | 🟡 | C4-ins |
| `models_app/views.py:512` | BaseMeasurement | READ-list | `.none()` a schema public | OK | ⚪ | FORA: guard de schema |
| `models_app/views.py:516-523` | BaseMeasurement | WRITE-create/update | `perform_create`/`perform_update` via serializer sense camp instància | COL·LAPSA (el POST xoca contra unique) | 🟠 | Onada2 |
| `models_app/views.py:1182` | BaseMeasurement | READ-dict | `filter(model=model, pom=m.pom).first()` — sembra item→model | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/views.py:1186,1196` | BaseMeasurement | WRITE-create | `create(model, pom=m.pom, …)` sense instància | COL·LAPSA | 🔴 | Onada2 |
| `models_app/views.py:1340` | BaseMeasurement | READ-list | `src_mesures` de la còpia model→model, `order_by('ordre','pom_id')` | OK a l'origen | 🟡 | Onada2 |
| `models_app/views.py:1362` | BaseMeasurement | COUNT-gate | `filter(model=dst).exists()` | OK | ⚪ | FORA: booleà |
| `models_app/views.py:1412` | BaseMeasurement | READ-dict | `aggregate(Max('ordre'))` | OK | ⚪ | FORA |
| `models_app/views.py:1417` | BaseMeasurement | READ-dict | `filter(model=dst, pom_id=bm.pom_id).first()` | **COL·LAPSA** — copiar 2 instàncies en crea 1 | 🔴 | Onada2 |
| `models_app/views.py:1425-1445` | BaseMeasurement | WRITE-create | `BaseMeasurement(model=dst, pom_id=…)` sense instància | COL·LAPSA | 🔴 | Onada2 |
| `models_app/views.py:1555` | BaseMeasurement | COUNT-gate | `exists()` abans de tancar taula | OK | ⚪ | FORA: booleà |
| `models_app/views.py:1620-1625` | BaseMeasurement | READ-list | `taula-mesures`: qs `order_by('ordre','pom__codi_client')` | OK a BD; el payload surt amb dos `pom_id` iguals | 🔴 | top-up-lectors + C4-ins |
| `models_app/views.py:1793-1805` | BaseMeasurement | WRITE-update | `update_or_create(model=model, pom=pom, …)` — `set-measurements` | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/views.py:1814-1818` | BaseMeasurement | WRITE-update | `exclude(pom_id__in=keep).update(is_active=False)` | **COL·LAPSA** — poda per POM mata TOTES les instàncies | 🔴 | Onada2 |
| `models_app/views.py:1910` | BaseMeasurement | COUNT-gate | `exists()` had_base_before | OK | ⚪ | FORA |
| `models_app/views.py:1921` | BaseMeasurement | READ-dict | `filter(model, pom).first()` — `gravar_pom` | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/views.py:1943-1947` | BaseMeasurement | WRITE-update | `exclude(pom_id__in=keep).update(is_active=False)` | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/views.py:1960` | ModelGradingRule | READ-dict | `filter(model, pom_id).first()` | OK si la regla és compartida | ⚪ | C1-ins |
| `models_app/views.py:1997` | BaseMeasurement | COUNT-gate | `exists()` | OK | ⚪ | FORA |
| `models_app/views.py:2036` | BaseMeasurement | WRITE-update | `filter(id=bm_id, model).update(ordre=i)` | OK (per id) | ⚪ | FORA: ancorat a pk |
| `models_app/views.py:2126-2134` | BaseMeasurement | READ-list | prompt IA `- {codi}: {valor}cm` | IGNORA-2a (dues línies idèntiques) | 🟡 | C4-ins |
| `models_app/views.py:2241-2249` | BaseMeasurement | READ-list | context xat IA `ID:{id} CODI:{codi}` | IGNORA-2a | 🟡 | C4-ins |
| `models_app/views.py:2299` | BaseMeasurement | READ-dict | `get(id=bm_id, model)` | OK (per id) | ⚪ | FORA |
| `models_app/views.py:2313-2325` | BaseMeasurement | WRITE-update | `update_or_create(model, pom)` — acció AFEGIR de la IA | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/views.py:2318` | BaseMeasurement | COUNT-gate | `'ordre': base_measurements.count()` | IGNORA-2a | 🟡 | Onada2 |
| `models_app/views.py:2328` | BaseMeasurement | WRITE-update | `get(id=…)` + `is_active=False` | OK (per id) | ⚪ | FORA |
| `models_app/views.py:2337-2341` | BaseMeasurement | READ-list | `.values('id','pom__codi_client',…)` retornat al front | IGNORA-2a | 🟡 | C4-ins |
| `models_app/views.py:2375-2377` | BaseMeasurement | COUNT-gate | `exists()` abans de generar grading | OK | ⚪ | FORA |
| `models_app/views.py:2426` | ModelGradingOverride | WRITE-delete | `filter(model=model).delete()` — llenç net | OK | ⚪ | FORA: escombra sencera |
| `models_app/views.py:2487-2500` | BaseMeasurement | READ-list | taula propagada; files amb `'pom_id': pom.id` | **COL·LAPSA** al consumidor | 🔴 | top-up-lectors + C4-ins |
| `models_app/views.py:2587-2589` | ModelGradingOverride | READ-dict | `filter(model,pom,size_label).values_list.first()` — sense `capa` ni instància | **COL·LAPSA** | 🔴 | top-up-lectors |
| `models_app/views.py:2590-2598` | ModelGradingOverride | WRITE-update | `update_or_create(model,pom,size_label)` — ÚNIC camí d'override des de Peça 4 | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/views.py:2603-2610` | MeasurementChangeLog | WRITE-create | `create(model,pom,base_measurement=None,…)` | COL·LAPSA | 🔴 | Onada2 |
| `models_app/views.py:2751` | ModelGradingOverride | WRITE-delete | `filter(model,pom).delete()` — neteja pins en propagar per regla | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/views.py:2759-2761` | ModelGradingOverride | READ-dict | `filter(model,pom,size_label).values_list.first()` | **COL·LAPSA** | 🔴 | top-up-lectors |
| `models_app/views.py:2762-2766` | ModelGradingOverride | WRITE-update | `update_or_create(model,pom,size_label)` — Escalat | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/views.py:2768-2772` | MeasurementChangeLog | WRITE-create | `create(...)` Escalat talla | COL·LAPSA | 🔴 | Onada2 |
| `models_app/views.py:2797-2805` | BaseMeasurement | WRITE-update | `_write_base()`: `get_or_create(model, pom, …)` — **LA PORTA D'ESCRIPTURA DE BASE DE L'ESCALAT** | **COL·LAPSA** | 🔴 | Onada2 |
| `models_app/views.py:2863` | BaseMeasurement | READ-dict | `{bm.id: bm for … id__in=ids}` reorder | OK (per id) | ⚪ | FORA |
| `models_app/views.py:2909` | BaseMeasurement | READ-dict | `get(id=bm_id)` — bateig NOMS-POM | OK (per id) | ⚪ | FORA |
| `models_app/views.py:2957-2958` | BaseMeasurement | READ-list | `base_stages_view`: bms `order_by('ordre','pom__codi_client')` | dues files germanes | 🔴 | top-up-lectors |
| `models_app/views.py:2978-2981` | MeasurementChangeLog | READ-list | logs `filter(model, base_measurement__isnull=False)` | OK a BD | ⚪ | top-up-lectors |
| `models_app/views.py:2999` | MeasurementChangeLog | READ-dict | `changes_by_ev[key][(c.pom_id, c.capa)]` — clau que ja va créixer a l'Onada 1 | **COL·LAPSA**: el carry-forward arrossega el valor d'una instància per la fila de l'altra | 🔴 | top-up-lectors |
| `models_app/views.py:3004` | — | READ-dict | `snapshot.update(...)` — mateix espai de claus | COL·LAPSA | 🔴 | top-up-lectors |
| `models_app/views.py:3010` | BaseMeasurement | READ-dict | `displayed = {(bm.pom_id, bm.capa) for bm in bms}` | COL·LAPSA | 🔴 | top-up-lectors |
| `models_app/views.py:3017+` | BaseMeasurement | CONTRACT-api | files del payload amb `pom_id` sol | COL·LAPSA al front | 🔴 | C4-ins |
| `models_app/views.py:3230-3232` | BaseMeasurement | COUNT-gate | **`model.base_measurements.filter(is_active=True, base_value_cm__isnull=False).count()`** — accés invers pur **[SOLO-1]** | IGNORA-2a (el gate del model menteix) | 🟡 | top-up-lectors |
| `models_app/views.py:3351-3368` | MeasurementChangeLog | READ-list | timeline: payload `'pom_id': c.pom_id` | IGNORA-2a | 🟡 | C4-ins |
| `models_app/views.py:3589-3591` | BaseMeasurement | READ-list | `fonts` de la promoció a ItemBaseSet | **COL·LAPSA** — dues fonts per un sol `ItemBaseMeasurement` | 🔴 | consolidació-catàleg |
| `models_app/views.py:3927-3930` | BaseMeasurement | WRITE-update | poda per POM: `filter(model_id, pom_id, is_active).first()` + `is_active=False` | **IGNORA-2a** (només poda una; l'altra queda viva i invisible) | 🔴 | Onada2 |
| `models_app/views.py:3978-3985` | ModelGradingRule | WRITE-update | `_sembra_step_des_dels_specs` amb àncora `capa=exterior` sobre `GradedSpec` | IGNORA-2a | 🟡 | top-up-lectors |
| `models_app/views.py:4036-4050` | ModelGradingRule | WRITE-update | `filter(model, pom_id).first()` + upsert de la regla resident | OK si la regla és compartida | ⚪ | C1-ins |

### D · `models_app/extraction_views.py` (el camí d'IMPORT)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `extraction_views.py:2331-2336` | BaseMeasurement | READ-list | `orfes`: `exclude(pom_id__in=confirmed_pom_ids)` — pre-flight de poda | **COL·LAPSA** — la 2a instància d'un POM confirmat mai és òrfena | 🔴 | Onada2 |
| `extraction_views.py:2367-2372` | BaseMeasurement | READ-list | `manuals`: `filter(origen='MANUAL', pom_id__in=_doc_pom_ids)` | IGNORA-2a (guard `preserve_manual` per POM) | 🟡 | top-up-lectors |
| `extraction_views.py:2515` | BaseMeasurement | READ-list | `_buides = filter(model, base_value_cm__isnull=True)` | OK (itera totes) | ⚪ | top-up-lectors |
| `extraction_views.py:2516` | BaseMeasurement | WRITE-delete | `.filter(origen__in=TEMPLATE).delete()` — DELETE dur | IGNORA-2a | 🟡 | Onada2 |
| `extraction_views.py:2518-2524` | BaseMeasurement | WRITE-update | soft-delete + `_desactivat` per fila | OK (per objecte) | ⚪ | Onada2 |
| **`extraction_views.py:2560`** | BaseMeasurement | WRITE-update | **`update_or_create(model=model, pom=pm, defaults=_defaults)`** — el confirm de l'import; `_defaults` inclou `seccio` | **COL·LAPSA — ÉS EXACTAMENT EL BUG DECLARAT A `models.py:655`** | 🔴🔴 | Onada2 |
| `extraction_views.py:2683` | ModelGradingRule | WRITE-delete | **`model.grading_rules.all().delete()`** — accés invers **[SOLO-1]** | OK | ⚪ | Onada2 |
| `extraction_views.py:2693-2698` | ModelGradingOverride | WRITE-update | `update_or_create(model, pom_id, size_label)` — import W5 divergències | **COL·LAPSA** | 🔴 | Onada2 |
| `extraction_views.py:2725` | ModelGradingRule | COUNT-gate | **`model.grading_rules.count()`** — accés invers **[SOLO-1]** | OK | ⚪ | FORA: comptador |
| `extraction_views.py:2909-2910` | ModelGradingOverride | WRITE-delete | `filter(model_id, pom_id__in=a_promocionar).delete()` | IGNORA-2a | 🟡 | consolidació-catàleg |
| `extraction_views.py:2813-2814` | — | CONTRACT-api | payload `'base_measurements': n_bm` (comptador) | IGNORA-2a | ⚪ | C4-ins |

### E · `models_app/services*.py`, `views_size_check.py`, serializers

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `models_app/services.py:266` | ModelGradingRule | WRITE-delete | **`model.grading_rules.all().delete()`** **[SOLO-1]** | OK | ⚪ | Onada2 |
| `models_app/services.py:268-282` | ModelGradingRule | WRITE-create | `bulk_create` de `ModelGradingRule(model, pom_id=r.pom_id, …)` | OK si compartida; **PETA** si es dona instància a la regla | 🟠 | C1-ins |
| `models_app/services.py:294` | ModelGradingRule | WRITE-delete | **`model.grading_rules.all().delete()`** **[SOLO-1]** | OK | ⚪ | Onada2 |
| `models_app/services.py:296-308` | ModelGradingRule | WRITE-create | `bulk_create` des d'SPECS (`s['pom_id']`) | idem | 🟠 | C1-ins |
| **`services_size_check.py:34-36`** | SizeCheckLine | READ-dict | **`values_list('pom_id', flat=True)`** — `ja_hi_son`. **Ni capa ni instància** | **IGNORA-2a** — la 2a instància mai rep línia de check | 🔴 | top-up-lectors |
| `services_size_check.py:37-42` | BaseMeasurement | READ-list | `.exclude(pom_id__in=ja_hi_son)` | **IGNORA-2a** | 🔴 | top-up-lectors |
| `services_size_check.py:45-50` | SizeCheckLine | WRITE-create | `create(size_check, pom=bm.pom, valor_teoric=…)` — **no estampa `capa` ni instància** | COL·LAPSA | 🔴 | Onada2 |
| `services_size_check.py:90` | SizeCheckLine | COUNT-gate | **`existing.linies.count()`** — accés invers **[SOLO-1]** | IGNORA-2a | 🟡 | top-up-lectors |
| `services_size_check.py:112-119` | ModelGradingRule | COUNT-gate | `filter(model, actiu=True).exists()` — `model_te_deltes` | OK | ⚪ | FORA: booleà |
| `services_size_check.py:172` | SizeCheckLine | COUNT-gate | `filter(size_check, decisio='valor_descartat').count()` | OK | ⚪ | FORA |
| `services_size_check.py:191-193` | SizeCheckLine | WRITE-update | `filter(size_check, decisio__isnull=True).update(...)` | OK (per size_check) | ⚪ | FORA |
| `services_size_check.py:196-199` | SizeCheckLine | READ-list | `filter(size_check, decisio='tolerancia_acceptada')` | OK | ⚪ | top-up-lectors |
| **`services_size_check.py:204-207`** | BaseMeasurement | WRITE-update | **`get_or_create(model=model, pom=line.pom, …)`** — consolidació CHECKED | **COL·LAPSA** | 🔴 | Onada2 |
| `views_size_check.py:83` | SizeCheckLine | CONTRACT-api | `SizeCheckLineViewSet.queryset = .all()` (PATCH per pk) | OK | ⚪ | C4-ins |
| `views_size_check.py:87` | SizeCheckLine | READ-list | `.none()` schema public | OK | ⚪ | FORA |
| `serializers_size_check.py:18-20` | SizeCheckLine | CONTRACT-api | `fields=['id','size_check','pom','valor_teoric',…]` — sense capa ni instància | IGNORA-2a al front | 🟡 | C4-ins |
| `serializers_size_check.py:36-37` | SizeCheckLine | COUNT-gate | **`obj.linies.count()`** — accés invers **[SOLO-1]** | IGNORA-2a | 🟡 | C4-ins |
| `serializers_size_check.py:86-90` | BaseMeasurement | READ-dict | `bm_map[(bm.pom_id, bm.capa)]` — clau d'Onada 1 | **COL·LAPSA** | 🔴 | top-up-lectors |
| `serializers_size_check.py:98-100` | SizeCheckLine | READ-list | **`obj.linies.select_related(...)`** + `bm_map.get((line.pom_id, line.capa))` **[SOLO-1 en part]** | **COL·LAPSA** | 🔴 | top-up-lectors |
| `serializers_size_check.py:116-121` | SizeCheckLine | CONTRACT-api | files amb `'pom_id'` sol | COL·LAPSA al front | 🔴 | C4-ins |
| `serializers_size_check.py:136` | BaseMeasurement | READ-dict | ordena per `ordre` de la fitxa | IGNORA-2a | 🟡 | top-up-lectors |
| `models_app/serializers.py:389-411` | BaseMeasurement | CONTRACT-api | `BaseMeasurementSerializer.fields` — cap camp de capa ni instància | IGNORA-2a | 🟡 | C4-ins |

### F · `models_app/pom_placement_views.py` (POMPlacement — l'únic consumidor viu)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `pom_placement_views.py:48-49` | POMPlacement | READ-list | `filter(view_slot=…)` | OK | ⚪ | top-up-lectors |
| **`pom_placement_views.py:52`** | POMPlacement | READ-dict | **`exacte = {p.pom_id: p for p in qs.filter(item_fitxer=item)}` — per POM SOL, ni capa** | **COL·LAPSA** | 🔴 | top-up-lectors |
| `pom_placement_views.py:56-58` | POMPlacement | READ-dict | `germana.setdefault(p.pom_id, p)` — per POM sol | **COL·LAPSA** | 🔴 | top-up-lectors |
| `pom_placement_views.py:60-64` | POMPlacement | READ-dict | `merged[pom_id] = (p, derivat)` — per POM sol | **COL·LAPSA** | 🔴 | top-up-lectors |
| `pom_placement_views.py:74-77` | BaseMeasurement | READ-dict | `bm_by_pom[(pom_id, capa)]` — clau d'Onada 1 | **COL·LAPSA** | 🔴 | top-up-lectors |
| `pom_placement_views.py:82` | — | READ-dict | `bm_by_pom.get((pom_id, p.capa))` — la cota s'enganxa a un `bm_id` arbitrari | **COL·LAPSA silenciós: no peta, PINTA** (comentari `:68-71`) | 🔴 | top-up-lectors |
| `pom_placement_views.py:87-92` | POMPlacement | CONTRACT-api | payload `{'pom_id','bm_id','codi', x1..y2, …}` | COL·LAPSA al front | 🔴 | C4-ins |
| **`pom_placement_views.py:135-138`** | POMPlacement | WRITE-update | **`update_or_create(item_fitxer, pom_id, view_slot)` — NI CAPA** (l'unique en té 4 camps; l'upsert n'usa 3) | **COL·LAPSA** — desar un precedent trepitja el de l'altra instància (i ja avui, el de l'altra capa) | 🔴 | Onada2 |

### G · `tech_sheet_views.py` i `management/commands/`

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `tech_sheet_views.py:364-377` | BaseMeasurement | WRITE-create | `get_or_create(model, pom=pom_master, defaults=…)` — create-from-sheet | **COL·LAPSA** | 🔴 | Onada2 |
| `tech_sheet_views.py:384` | — | CONTRACT-api | `'base_measurements_created': created_bm` | IGNORA-2a | ⚪ | C4-ins |
| `clone_model_for_qa.py:92-96` | BaseMeasurement | WRITE-create | clona `pk=None; save()` per fila | OK (copia totes) | ⚪ | Onada2 |
| `clone_model_for_qa.py:100-102` | ModelGradingRule | WRITE-create | clona per fila | OK | ⚪ | Onada2 |
| `clone_model_for_qa.py:154` | SizeCheckLine | WRITE-delete | `filter(size_check__model=model).delete()` | OK | ⚪ | FORA: purga de clon QA |
| `clone_model_for_qa.py:161` | MeasurementChangeLog | WRITE-delete | `filter(model).delete()` (esquiva l'append-only per queryset) | OK | ⚪ | FORA: purga |
| `clone_model_for_qa.py:162` | BaseMeasurement | WRITE-delete | `filter(model).delete()` | OK | ⚪ | FORA: purga |
| `repair_fitting_20260710.py:78` | BaseMeasurement | READ-dict | `filter(model_id=MODEL_ID, pom_id=pid).first()` | COL·LAPSA | 🟡 | FORA: script d'un sol ús |

### H · `pom/` — el motor i les superfícies (des del camí 1A)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`pom/services.py:771-780`** | BaseMeasurement | READ-dict | **`_load_base_measurements` → `{bm.pom_id: bm.base_value_cm}`** — entrada del motor. Docstring veí: «zona intocable, C3 amb decisió humana» | **COL·LAPSA** — l'últim `order_by('ordre')` guanya | 🔴🔴 | top-up-lectors |
| `pom/services.py:215-217` | BaseMeasurement | READ-dict | `base_measurements = _load_base_measurements(model.pk)` a `generate_graded_specs` | COL·LAPSA | 🔴 | top-up-lectors |
| `pom/services.py:233-270` | BaseMeasurement | CONTRACT-engine | **`for pom_id, base_val in base_measurements.items()`** — el bucle generador | COL·LAPSA | 🔴 | top-up-lectors |
| `pom/services.py:361-380` | BaseMeasurement | CONTRACT-engine | mateix bucle al PREVIEW del wizard | COL·LAPSA | 🔴 | top-up-lectors |
| `pom/services.py:699-708` | ModelGradingRule | READ-dict | `_load_grading_rules → {r.pom_id: r}` | OK si compartida | 🟡 | C1-ins |
| **`pom/services.py:732-739`** | ModelGradingOverride | READ-dict | `_load_model_overrides → {(pom_id, size_label): value}` amb filtre `capa=SLUG_DEFECTE` | **COL·LAPSA** | 🔴 | top-up-lectors |
| `pom/services.py:765` | ModelGradingOverride | READ-dict | `_poms_amb_override` → `{pom_id …}` | COL·LAPSA | 🔴 | top-up-lectors |
| `pom/services.py:671-673` | ModelGradingRule | COUNT-gate | `_te_regles`: `filter(model_id, actiu=True).exists()` | OK | ⚪ | FORA: booleà |
| `pom/wizard_views.py:192-195` | BaseMeasurement | WRITE-update | `filter(model, pom_id).update(base_value_cm=None)` | **COL·LAPSA** — buida les dues | 🔴 | Onada2 |
| `pom/wizard_views.py:205-215` | BaseMeasurement | WRITE-update | `update_or_create(model, pom_id, defaults=…)` | **COL·LAPSA** | 🔴 | Onada2 |
| `pom/wizard_views.py:252-256` | BaseMeasurement | COUNT-gate | `count()` < 3 → error «cal 3 POMs» | IGNORA-2a | 🟡 | top-up-lectors |
| `pom/wizard_views.py:326-330` | BaseMeasurement | READ-list | `base_measurements_view` qs `order_by('categoria','codi_client')` | OK a BD | 🔴 | top-up-lectors |
| `pom/wizard_views.py:351-361` | ModelGradingRule | READ-dict | `regla_by_pom = {r.pom_id: {...}}` | OK (regla compartida) | 🟡 | top-up-lectors |
| `pom/wizard_views.py:363-390` | BaseMeasurement | CONTRACT-api | files amb `'pom_id'`, `'regla_model': regla_by_pom.get(bm.pom_id)` | COL·LAPSA al front | 🔴 | C4-ins |
| `pom/s6_views.py:88-94` | BaseMeasurement | READ-list | àncora `capa=SLUG_DEFECTE` + llista plana per `pom_id`; el comentari `:84-88` diu **«dos elements portarien el mateix `pom_id` i el consumidor en perdria un en silenci»** | **COL·LAPSA** | 🔴 | top-up-lectors + C4-ins |
| `pom/s8_views.py:183-187` | BaseMeasurement | READ-dict | `tol_map[(bm.pom_id, bm.capa)]` — export CSV de fitting | **COL·LAPSA** (PASS/FAIL amb la vara equivocada) | 🔴 | top-up-lectors |
| `pom/s10_views.py:54-60` | BaseMeasurement | READ-dict | `_tolerance_map → {(pom_id, capa): (tol_minus, tol_plus)}` | **COL·LAPSA** | 🔴 | top-up-lectors |
| `pom/s11_views.py:165-171` | BaseMeasurement | READ-dict | `base_map = {bm.pom_id: valor}` amb àncora; body `{pom_id, value_cm}` | **COL·LAPSA** | 🔴 | top-up-lectors + C4-ins |
| `pom/grading_views.py:119-140` | BaseMeasurement | READ-dict | `cells[pom_id][base_size_label]` quan no hi ha grading | **COL·LAPSA** | 🔴 | top-up-lectors |
| **`pom/seed_data/consolidate_pom_los.py:31-33`** | BM, MCL, MGO, MGR | CONTRACT-engine | **`FUSIO_MOVE_RELS = ['base_measurements','model_grading_rules','measurement_changes','model_grading_overrides', …]`** — els related_name com a **strings de config** **[SOLO-1]** | OK com a llista; el consumidor col·lapsa | 🔴 | consolidació-catàleg |
| `consolidate_pom_catalog.py:112-119` | les 4 anteriors | WRITE-update | **`for obj in list(getattr(prim, rel).all()): type(obj).objects.filter(pk=obj.pk).update(pom=dest)`** + `except IntegrityError → col·lisió` **[SOLO-1]** | més col·lisions silencioses | 🔴 | consolidació-catàleg |
| `consolidate_pom_catalog.py:121-125` | — | WRITE-delete | `FUSIO_DELETE_RELS` (`graded_specs`) | OK | ⚪ | FORA: taula d'altri |
| `consolidate_pom_catalog.py:249-254` | les 4 anteriors | WRITE-delete | `_fixcoll`: **`getattr(m, rel).all().delete()`** **[SOLO-1]** | IGNORA-2a | 🔴 | consolidació-catàleg |
| `sembra_ai_report.py:463,500,602` | POMPlacement | READ-list | informe FASE 1, **cap escriptura** | OK avui | ⚪ | F2-patrons |

### I · `fitting/` (des del camí 1A)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`fitting/services.py:369-376`** | BaseMeasurement | WRITE-update | `consolidate_base_from_fitting`: **`get_or_create(model=model, pom=line.pom, …)`** | **COL·LAPSA** | 🔴 | Onada2 |
| `fitting/serializers.py:263-268` | BaseMeasurement | READ-dict | `ordre_map`/`nom_fitxa_map`/`bm_id_map` per `(pom_id, capa)` | **COL·LAPSA** | 🔴 | top-up-lectors |
| `fitting/serializers.py:272-276` | — | READ-list | `for line in obj.linies…` + `clau_bm = (line.pom_id, line.capa)` **[SOLO-1: `obj.linies`]** | COL·LAPSA | 🔴 | top-up-lectors |
| `fitting/serializers.py:294-298` | BaseMeasurement | CONTRACT-api | `'nom_fitxa'`, **`'bm_id'`** al payload — per aquí s'escriu el bateig | **COL·LAPSA**: s'escriuria el nom a la mesura de l'altra instància | 🔴 | C4-ins |
| `fitting/serializers.py:310-315` | BaseMeasurement | READ-list | ordena per `ordres` paral·lel | IGNORA-2a | 🟡 | top-up-lectors |
| `fitting/serializers.py:112` | SizeCheckLine | COUNT-gate | **`obj.linies.count()`** **[SOLO-1]** | IGNORA-2a | 🟡 | C4-ins |
| `fitting/graded_spec_views.py:94-106` | BaseMeasurement | READ-dict | **4 mapes** (`ordre_map`, `nom_fitxa_map`, `seccio_map`, `bateig_map`) per `pom_id` amb àncora | **COL·LAPSA els quatre alhora** | 🔴 | top-up-lectors |
| `fitting/graded_spec_views.py:137` | BaseMeasurement | READ-list | `rows.sort(key=ordre_map.get(pom_id, 1e9))` | IGNORA-2a | 🟡 | top-up-lectors |
| **`fitting/repas_views.py:99-113`** | SizeCheckLine | READ-dict | `fora[(l.size_check_id, l.pom_id)]` via **`.only('size_check_id','pom_id','decisio','nota')` — el `.only()` exclou `capa`** | **COL·LAPSA** | 🔴 | top-up-lectors |
| `fitting/repas_views.py:140-158` | MeasurementChangeLog | READ-dict | `celles[clau][c.pom_id] = {valor_real, nota}` — sense capa | **COL·LAPSA** | 🔴 | top-up-lectors |
| `fitting/repas_views.py:259-266` | BaseMeasurement | READ-dict | 4 mapes per `pom_id` amb àncora `capa=SLUG_DEFECTE` | **COL·LAPSA els quatre** | 🔴 | top-up-lectors |
| `fitting/repas_views.py:273+` | — | CONTRACT-api | `_fila(pom_id, pom)` — `files` indexat per `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `fitting/staleness.py:109-124` | MeasurementChangeLog | READ-list | `filter(model_id, created_at__gt=…)` + `dict.fromkeys(codi_client)` | OK (dedupica codis) | ⚪ | top-up-lectors |

### J · `patterns/` i `tenants/` (des del camí 1A)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `patterns/views.py:552-557` | BaseMeasurement | READ-list | `base` qs `order_by('ordre','pom__codi_client')` | OK a BD | 🟡 | top-up-lectors |
| `patterns/views.py:558` | — | READ-dict | `_alies_unics_del_customer(fp.model_id, [bm.pom_id for bm in base])` | IGNORA-2a | ⚪ | top-up-lectors |
| `patterns/views.py:560-575` | BaseMeasurement | CONTRACT-api | files `{'base_measurement': bm.id, 'pom_master': bm.pom_id, …}`; `ancorats` per `pom_master_id` | **COL·LAPSA** | 🔴 | C4-ins |
| `tenants/federation_service.py:594-605` | BaseMeasurement | READ-list | export del patrimoni; cada fila amb `'clau': _clau_natural_pom(bm.pom)` | **COL·LAPSA** — dues files amb la MATEIXA clau natural | 🔴 | Onada2 |
| `tenants/federation_service.py:607-620` | ModelGradingRule | READ-list | export de regles per clau natural | OK (regla compartida) | ⚪ | Onada2 |
| **`tenants/federation_service.py:689`** | BaseMeasurement | READ-dict | `existent = filter(model=twin, pom=pom).first()` — sobirania al destí | **COL·LAPSA** | 🔴 | Onada2 |
| `tenants/federation_service.py:692-706` | BaseMeasurement | WRITE-create | `create(model=twin, pom=pom, …)` sense instància | COL·LAPSA | 🔴 | Onada2 |
| `tenants/federation_service.py:711-719` | BaseMeasurement | WRITE-update | `existent.save(update_fields=[…])` si TEMPLATE buit | COL·LAPSA | 🔴 | Onada2 |
| `tenants/federation_service.py:732-734` | ModelGradingRule | COUNT-gate | `filter(model=twin, pom=pom).exists()` | OK | ⚪ | Onada2 |
| `tenants/federation_service.py:735-742` | ModelGradingRule | WRITE-create | `create(model=twin, pom=pom, …)` | OK | ⚪ | Onada2 |

### K · Frontend (contracte que viatja) — des del camí 1A

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `TechSheetEditor.jsx:5477-5488` | POMPlacement | READ-dict | `const acc = new Map() // pom_id → {p, derivat, hostId}` | **COL·LAPSA** al navegador | 🔴 | C4-ins |
| `TechSheetEditor.jsx:5512` | POMPlacement | CONTRACT-api | `buildLiveCota({ pomId, bmId: p.bm_id, … })` | COL·LAPSA | 🔴 | C4-ins |
| `TechSheetEditor.jsx:5611-5613` | POMPlacement | WRITE-create | `POST .../pom-placements/` amb body sense capa ni instància | COL·LAPSA | 🔴 | C4-ins |
| `TechSheetEditor.jsx:5622-5623` | POMPlacement | WRITE-create | `escriurePrecedentSilent` — mateix POST | COL·LAPSA | 🔴 | C4-ins |
| `TechSheetEditor.jsx:5633-5638` | BaseMeasurement | READ-list | `pomRows.filter(...)` + `cotesColocades.has(bm.pom_id)` | COL·LAPSA | 🔴 | C4-ins |
| `TechSheetEditor.jsx:5668-5671` | BaseMeasurement | READ-dict | `bmByPom = new Map(pomRows.map(bm => [bm.pom_id, bm]))` | **COL·LAPSA** | 🔴 | C4-ins |
| `MeasureGrid.jsx:333` | BaseMeasurement | WRITE-update | `const ids = rows.map(r => r.bm_id)` → reorder | OK (per `bm_id`) | ⚪ | FORA: ancorat a pk |
| `MeasureGrid.jsx:482,489` | BaseMeasurement | CONTRACT-api | `CodiCell`/`NomCell` amb `bmId={r.bm_id}` (bateig) | OK (per pk) | ⚪ | C4-ins |
| `measureSources.jsx:22` · `fittingGridAdapter.jsx:53` · `repasGridAdapter.jsx:119` · `CheckMeasureEditor.jsx:229` · `FittingDetail.jsx:583` | BaseMeasurement | CONTRACT-api | tots propaguen `bm_id` des del payload | OK (per pk), però la fila ve d'un mapa col·lapsat | ⚪ | C4-ins |
| `ModelPomList.jsx:39-43` | BaseMeasurement | CONTRACT-api | `key={f.base_measurement}` — key de React per pk | OK | ⚪ | C4-ins |

### L · Tests que codifiquen la llei (des del camí 1A)

| fitxer:línia | taula | tipus | què afirma | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `test_capa_comporta_c1.py:63` `test_una_mesura_base_de_folre_no_entra` | BaseMeasurement | COUNT-gate | la comporta CHECK barra `capa≠'exterior'` | OK | ⚪ | C1-ins |
| `test_capa_comporta_c1.py:68` `test_una_linia_de_size_check_de_folre_no_entra` | SizeCheckLine | COUNT-gate | idem | OK | ⚪ | C1-ins |
| `test_capa_comporta_c1.py:74` `test_tampoc_hi_entra_per_update_massiu` | BaseMeasurement | WRITE-update | `queryset.update(capa='folre')` peta | OK | ⚪ | C1-ins |
| `test_capa_comporta_c1.py:84` `test_exterior_entra_i_es_el_default` | BaseMeasurement | WRITE-create | `create(model, pom, valor)` **sense capa** → 'exterior' | **PETA** si el camp instància no té default a Postgres | 🟠 | C1-ins |
| `test_capa_comporta_c1.py:94` `test_les_nou_comportes_existeixen_a_la_bd` | totes | COUNT-gate | cens exacte de 9 CHECKs `%_capa_gate_c1` | PETA si C1-ins n'afegeix | 🟡 | C1-ins |
| `test_capa_comporta_c1.py:108` `test_la_regla_de_grading_no_te_ni_capa_ni_comporta` | ModelGradingRule | COUNT-gate | **`information_schema`: `models_app_modelgradingrule` NO té columna `capa`** | **PETA** si la instància hi entra | 🟠 | C1-ins |
| `test_lectors_capa_onada1.py:100` `test_c1_…tolerancies` | BaseMeasurement | READ-dict | `_tolerance_map` per `(pom, capa)` | seguirà verd i el col·lapse passarà per sota | 🟡 | top-up-lectors |
| `test_lectors_capa_onada1.py:115` `test_c5_…linia_de_check` | SizeCheckLine, BM | READ-dict | clau `(pom, capa)` al serializer | idem | 🟡 | top-up-lectors |
| `test_lectors_capa_onada1.py:155` `test_c8_…sembra_step` | ModelGradingRule | WRITE-update | àncora exterior de la sembra STEP | idem | 🟡 | top-up-lectors |
| `test_lectors_capa_onada1.py:193` `test_c9_…carry_forward` | MCL, BM | READ-dict | carry-forward per `(pom, capa)` | idem | 🟡 | top-up-lectors |
| `test_lectors_capa_onada1.py:237` `test_la_comporta_torna_a_estar_viva` | BaseMeasurement | COUNT-gate | la comporta es reposa | OK | ⚪ | C1-ins |
| `test_size_check_completa_linies.py:49` `test_un_pom_nascut_despres_rep_linia` | SizeCheckLine | WRITE-create | **«un POM, una línia»** | **PETA/canvia** | 🟠 | top-up-lectors |
| `test_size_check_completa_linies.py:60,73,95,102,116,124` | SizeCheckLine, BM | WRITE-create/COUNT | idempotència per `pom_id`; POM sense valor no genera línia; POM desactivat no reapareix | PETA | 🟠 | top-up-lectors |
| `test_base_stages_no_regressio.py:67,71,91` | BM, MCL | CONTRACT-api | **«les claus de primer nivell són exactament aquestes»** | **PETA** si C4 afegeix camp | 🟠 | C4-ins |
| `test_base_stages_no_regressio.py:105,128,143,180,257,263,272,280` | MCL, MGO | READ-dict/list | agrupació d'estadis · carry-forward · poda · amagar POM · overrides no pinten columna | 🟡–🟠 | 🟠 | top-up-lectors |
| `test_copia_model_a_model.py` (16 refs) | BM, MGR | WRITE-create | còpia model→model, un POM una fila | **PETA** | 🟠 | Onada2 |
| `tests_sembra_grading.py` (44+8+3 refs) | BM, MCL, MGR | WRITE-create | sembra i materialització; `:424` `model.grading_rules.values_list('pom__codi_client','logica')` → **dict per codi** **[SOLO-1]** | COL·LAPSA | 🟠 | Onada2 |
| `test_seccio_captura.py` (7 refs) | BaseMeasurement | WRITE-create | captura de `seccio` a l'import | 🟠 | 🟠 | Onada2 |
| `test_lectors_capa_onada1.py` + `test_capa_comporta_c1.py` (`comporta_alcada`, `connection.cursor`) | totes | WRITE-update | helper que ALÇA la comporta CHECK per SQL cru dins el test | **patró reutilitzable** | ⚪ | C1-ins |
| `pom/test_d2_nomes_override.py` (6+6+2) | BM, MGO, MGR | CONTRACT-engine | llei D2 «POM només-override» | 🟠 | 🟠 | top-up-lectors |
| `test_d1_proposta_promocio.py` (5) | ModelGradingOverride | WRITE-delete | promoció al contenidor per `pom_id` | 🟡 | 🟡 | consolidació-catàleg |
| `fitting/test_repas.py` (6+9+3) | BM, MCL, SizeCheckLine | READ-dict | forma del Repàs per `pom_id` | 🟠 | 🟠 | top-up-lectors |
| `fitting/test_g6_estalitud.py` (6+2) | BM, SizeCheckLine | READ-list | estalitud via MCL | ⚪ | ⚪ | top-up-lectors |
| `fitting/test_graded_table_regla.py:60` | BaseMeasurement | WRITE-create | `create(model, pom, ordre=1, base_value_cm=47)` | 🟠 | 🟠 | Onada2 |
| `tenants/tests_enviament_feina.py` (14+9) | BM, MGR | WRITE-create | federació: patrimoni per clau natural | **PETA** | 🟠 | Onada2 |
| `patterns/tests.py:3287-3379` | BaseMeasurement | WRITE-update | `bm_a`/`bm_b` per pk | OK | ⚪ | FORA: pk |
| `pom/test_guarda_rang_mesura.py`, `test_g6_grading_gates.py`, `test_step_conserva_valors.py`, `test_g6_segell.py`, `test_g1_graduacio.py`, `test_set1_creacio.py`, `test_parser_excel.py`, `fitting/tests.py`, `pom/test_propaga.py` | BM, MGR, MGO | WRITE-create | tots creen 1 fila per `(model, pom)` | 🟡 | 🟡 | Onada2 |

### Accessos inversos — el forat clàssic, tancat (camí 1A)

**Per `related_name` en codi Django** (13 usos vius a tot el backend, verificats un a un):

| fitxer:línia | accessor | des de | taula real | què fa |
|---|---|---|---|---|
| `models_app/views.py:3230` | `.base_measurements` | `Model` | BaseMeasurement | `.filter(is_active=True, base_value_cm__isnull=False).count()` → `n_active` del panell d'artefactes |
| `models_app/views.py:974` | `.grading_rules` | `Model` | **ModelGradingRule** | `.all().delete()` — buidatge del pas 4 «Sense graduació» |
| `models_app/services.py:266` | `.grading_rules` | `Model` | ModelGradingRule | wipe de `materialize_model_grading_rules` |
| `models_app/services.py:294` | `.grading_rules` | `Model` | ModelGradingRule | wipe de `…_from_specs` |
| `models_app/extraction_views.py:2683` | `.grading_rules` | `Model` | ModelGradingRule | neteja de residents rancis |
| `models_app/extraction_views.py:2725` | `.grading_rules` | `Model` | ModelGradingRule | `n_rules = model.grading_rules.count()` |
| `models_app/tests_sembra_grading.py:424` | `.grading_rules` | `Model` | ModelGradingRule | `dict(…values_list('pom__codi_client','logica'))` |
| `models_app/services_size_check.py:90` | `.linies` | `SizeCheck` | SizeCheckLine | `existing.linies.count()` |
| `models_app/serializers_size_check.py:37` | `.linies` | `SizeCheck` | SizeCheckLine | `obj.linies.count()` → `n_linies` |
| `models_app/serializers_size_check.py:98` | `.linies` | `SizeCheck` | SizeCheckLine | `obj.linies.select_related('pom','pom__pom_global').all()` |
| `fitting/serializers.py:112` | `.linies` | `SizeCheck`/`PieceFitting` | SizeCheckLine | `obj.linies.count()` |
| `fitting/serializers.py:272` | `.linies` | `PieceFitting` | PieceFittingLine | `obj.linies.select_related(...)` |

⚠️ **Cap ús viu de `.measurement_changes`, `.model_grading_overrides`, `.grading_overrides`, `.change_log`,
`.pom_placements` ni `.placements` en codi Django** — la seva única aparició és per string.

**Per STRING dins una llista de config (el més invisible de tots):**

| fitxer:línia | strings | consumidor |
|---|---|---|
| **`pom/seed_data/consolidate_pom_los.py:30-34`** | `'base_measurements'`, `'model_grading_rules'`, `'measurement_changes'`, `'model_grading_overrides'`, `'item_base_measurements'`, `'mesures_perfil'`, `'alerts'`, `'pattern_poms'`, `'estadistiques'` (+ `FUSIO_DELETE_RELS = ['graded_specs']`, `FUSIO_LEAVE_RELS = ['regles_grading']`) | `consolidate_pom_catalog.py:112` (`getattr(prim, rel).all()` + `.update(pom=dest)`), `:249` (`getattr(m, rel).all().delete()`) |

### Recompte camí 1A

**Total: 176 files.**

| tipus | n | | onada | n | | risc | n |
|---|---|---|---|---|---|---|---|
| CONTRACT-engine | 24 | | `C1-ins` | 31 | | 🔴 | 74 |
| CONTRACT-api | 26 | | `top-up-lectors` | 52 | | 🟠 | 30 |
| READ-dict | 34 | | `Onada2` | 44 | | 🟡 | 41 |
| READ-list | 29 | | `C4-ins` | 28 | | ⚪ | 31 |
| WRITE-create | 21 | | `F2-patrons` | 1 | | | |
| WRITE-update | 26 | | `consolidació-catàleg` | 6 | | | |
| WRITE-delete | 13 | | `FORA: <motiu>` | 14 | | | |
| COUNT-gate | 23 | | | | | | |

### Els 7 nodes que tanquen el forat de la diagnosi prèvia (camí 1A)

1. **`pom/services.py:771` `_load_base_measurements`** → `{pom_id: valor}`. Cap grep de `unique_together` ho ensenya.
2. **`models_app/extraction_views.py:2560`** `update_or_create(model, pom)` — el bug de multipeça JA DECLARAT a `models.py:655` i mai reparat.
3. **`models_app/services_size_check.py:34-45`** — l'únic lector de `SizeCheckLine` que **ni tan sols va créixer a `(pom,capa)`**; a més el `create` no estampa `capa`.
4. **`models_app/pom_placement_views.py:135`** — l'upsert usa **3 camps** quan el `UniqueConstraint` en té **4**.
5. **`pom/seed_data/consolidate_pom_los.py:31` + `consolidate_pom_catalog.py:112,249`** — els related_name com a strings.
6. **`models_app/signals.py:267,299`** — el signal F1 no estampa capa i tampoc estamparà instància.
7. **`fitting/repas_views.py:99-113`** — el `.only()` exclou `capa` explícitament: ni el camp arriba de BD.

---
## II.4 · CAMÍ 1B — `fitting` · `pom` · `patterns`

**Abast:** `GradedSpec` · `PieceFittingLine` · `POMAlert` · `GarmentPOMMap` · `ItemBaseMeasurement` ·
`ItemBaseSet` · `GradingRule` · `ClientMesuraPerfil` · `CustomerPOMAlias` · `POMEstadisticaTenant` ·
`PatternPOM`. **285 files.**

### FET ESTRUCTURAL 0 — val per a tot el cens

**Cap escriptor de tot el repo passa mai `capa` a un lookup ni a un `defaults`.** Els únics 6 hits de
`capa=` fora de `models.py` són **filtres de lectura** (àncores exterior):
`fitting/graded_spec_views.py:95` · `fitting/repas_views.py:260` · `pom/s6_views.py:92` ·
`pom/s11_views.py:169` · `pom/services.py:737` · `models_app/views.py:3979`.
Tot escriptor viu del default `'exterior'`, protegit només per les comportes `CHECK capa='exterior'`.

**L'eix INSTÀNCIA entrarà pel mateix forat exacte.** No cal descobrir res per capa: ja està tot trencat de
la mateixa manera, en silenci.

### Dades a staging (SELECT read-only, 3 schemas)

| taula | files `fhort` | `capa` distinta | té columna `capa`? |
|---|---|---|---|
| `fitting_gradedspec` | 2 061 | `exterior` (100 %) | ✅ |
| `fitting_piecefittingline` | 153 | `exterior` (100 %) | ✅ |
| `pom_garmentpommap` | 1 748 | `exterior` (100 %) | ✅ |
| `pom_itembasemeasurement` | 37 | `exterior` (100 %) | ✅ |
| `pom_gradingrule` | 1 174 | — | ❌ |
| `pom_customerpomalias` | 336 | — | ❌ |
| `pom_clientmesuraperfil` | 17 | — | ❌ |
| `pom_itembaseset` | 1 | — | ❌ (sense eix POM) |
| `fitting_pomalert` | **0** | — | ❌ |
| `pom_pomestadisticatenant` | **0** | — | ❌ |
| **`patterns_patternpom`** | **0** (`los` 0) | — | ❌ |

`los` i `public` són a zero a totes. **`patterns` no té columna `capa` enlloc: C1 no hi va passar.**

### A · `patterns/` SENCER — el forat que es tanca

#### A.1 · La constraint que NEGA la instància

`patterns/models.py:432-437`:
```python
models.UniqueConstraint(
    fields=['pattern_piece', 'pom_master'],
    name='patternpom_un_ancoratge_per_peca',
)
```
amb el comentari (`:430-431`): *«Un POM es mesura UNA vegada per peça. Dos ancoratges del mateix POM a la
mateixa peça serien dues veritats sobre la mateixa mesura.»*

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `patterns/models.py:432-437` | PatternPOM | CONTRACT-engine | `(pattern_piece, pom_master)` — **sense `capa`, sense instància**; el comentari **nega la premissa** | **PETA** | 🔴 | F2-patrons |
| `patterns/tests.py:1865` `test_el_mateix_pom_dos_cops_a_la_mateixa_peca_rebota` | PatternPOM | COUNT-gate | assert `status_code == 400` | **PETA — inverteix la llei** | 🔴 | F2-patrons |
| `frontend/src/pages/TallerPatro.jsx:352-354` | PatternPOM | CONTRACT-api | `non_field_errors[0]` → `t('pattern.err_pom_duplicate')` | PETA (la UI ja té el missatge d'error del cas legítim) | 🔴 | C4-ins |

#### A.2 · El port entre motors — tipat amb `pom_id` sol

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `patterns/engine/ports.py:60` | GradedSpec | CONTRACT-engine | `GradedPOMDelta.pom_id: int` — dataclass frozen | COL·LAPSA (el tipus no pot portar la instància) | 🔴 | F2-patrons |
| `patterns/engine/ports.py:97-101` | GradedSpec | CONTRACT-engine | `def delta(self, pom_id, size_label)` — cerca lineal `d.pom_id == pom_id and d.size_label == size_label` | **IGNORA-2a** (retorna el primer que troba) | 🔴 | F2-patrons |
| `patterns/engine/ports.py:104-108` | GradedSpec | CONTRACT-engine | docstring: *«lectura determinista, garantida per l'unique `(grading_version, pom, size_label)`»* — **el contracte escrit ja és FALS des de C1** (l'unique real porta `capa`) | COL·LAPSA + document ranci | 🔴 | F2-patrons |
| `patterns/adapters.py:484-489` | GradedSpec | READ-list | `filter(grading_version_id, is_active=True).order_by('pom_id','size_label')` — **sense `capa`** | COL·LAPSA: el snapshot porta N deltes amb el mateix `pom_id` i `delta()` en tria una | 🔴 | F2-patrons |
| `patterns/adapters.py:587` `pom_specs()` | PatternPOM | READ-list **[SOLO-1]** (`piece.poms`) | `for pom in piece.poms.all()` → `POMSpec(pom_code=pom.pom_master.pom_code, …)` | COL·LAPSA: l'identitat que en surt és el **codi string** | 🔴 | F2-patrons |
| `patterns/adapters.py:623` | GradedSpec | CONTRACT-engine | `pom_id=pom.pom_master_id` | COL·LAPSA | 🔴 | F2-patrons |

#### A.3 · La projecció — cinc dicts, tots per `pom_id` o `pom_code`

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `patterns/engine/grading_projection.py:179` | PatternPOM | READ-dict | **`poms_per_id = {p.pom_id: p for p in poms …}`** | **COL·LAPSA** — la 2a instància desapareix del motor sencer | 🔴 | F2-patrons |
| `grading_projection.py:180` | GradedSpec | READ-list | `ids_amb_spec = {d.pom_id for d in snapshot.deltas}` | COL·LAPSA (set) | 🔴 | F2-patrons |
| `grading_projection.py:181` | GradedSpec | READ-dict | `codis_spec = {d.pom_id: d.pom_code …}` | COL·LAPSA | 🔴 | F2-patrons |
| `grading_projection.py:184-200` | PatternPOM ↔ GradedSpec | READ-list | `pom_sense_spec` / `spec_sense_pom` sobre **conjunts de `pom_id`** | **COL·LAPSA**: declararia cobert un POM cobert a mitges | 🔴 | F2-patrons |
| `grading_projection.py:216` | PatternPOM | READ-dict | `graduables = {i: s for i, s in poms_per_id.items() …}` | COL·LAPSA (hereta) | 🔴 | F2-patrons |
| `grading_projection.py:262` `_deltes_dels_poms` | PatternPOM | CONTRACT-engine | `for pom_id, spec in sorted(poms_per_id.items())` → `_acumular(ordres, spec.ref_a/ref_b, …)` | COL·LAPSA: només una instància mou geometria | 🔴 | F2-patrons |
| `grading_projection.py:499` + `:563-570` `_valors_dels_poms` | PatternPOM | READ-dict | **`{p.pom_code: p.valor_cm …}`** — per **codi string** | COL·LAPSA | 🔴 | F2-patrons |
| `grading_projection.py:509` | PatternPOM | READ-dict | **`lectures = {p.pom_code: p for p in res.informe.poms}`** | COL·LAPSA | 🔴 | F2-patrons |
| `grading_projection.py:511-514` | GradedSpec | READ-dict | `lectures.get(spec.pom_code)` + `snapshot.delta(spec.pom_id, talla)` | COL·LAPSA (les dues bandes de la comptabilitat de doble entrada col·lapsen alhora) | 🔴 | F2-patrons |

#### A.4 · El format d'intercanvi — el sostre dur

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `patterns/engine/ftt_pom_layer.py:124-127` `format_pom_text` | PatternPOM | CONTRACT-engine | `FTT "{codi}" {nom} = {valor} mm` — **el DXF només porta el codi** | **COL·LAPSA irreversible**: el roundtrip export→reimport perd la instància | 🔴 | F2-patrons |
| `ftt_pom_layer.py:110-116` `_RE_POM` | PatternPOM | CONTRACT-engine | regex que captura `codi` + `nom` + `valor` | COL·LAPSA | 🔴 | F2-patrons |
| `ftt_pom_layer.py:197-218` `build_poms` | PatternPOM | READ-list | `POMAnchorData(pom_code=…)` + `_mesura_mes_propera(tx,ty,…)` | COL·LAPSA | 🔴 | F2-patrons |
| `patterns/engine/aama_writer.py:128-129` | PatternPOM | WRITE-create | `pom_writer.write_piece_poms(block, piece.poms, …)` | COL·LAPSA (dues línies amb la mateixa etiqueta) | 🟠 | F2-patrons |
| `patterns/engine/roundtrip.py:274-292` `_compare_poms` | PatternPOM | COUNT-gate | **`codis_a`/`codis_b` = sets de `pom_code`; `per_codi = {p.pom_code: p …}`** | COL·LAPSA: **el comparador de la prova Montse no veu una instància perduda** | 🔴 | F2-patrons |
| `patterns/export.py:395-398` `_amb_capa_pom` | PatternPOM | READ-dict | `valors = {p.pom_code: p.valor_cm …}` | COL·LAPSA | 🔴 | F2-patrons |
| `patterns/export.py:410-412` | PatternPOM | WRITE-create | `valor_cm = valors.get(spec.pom_code)` → `POMAnchorData(pom_code=…)` | COL·LAPSA | 🔴 | F2-patrons |
| `patterns/engine/operations.py:187-190` | PatternPOM | READ-list | `for p in self.poms: f'POM {p.pom_code} = …'` (resum) | IGNORA-2a (informe) | 🟡 | F2-patrons |
| `patterns/svg.py:119-126` | PatternPOM | READ-list | `for pom in piece.poms: … punts_ancora` | OK (dibuixa cadascun) | ⚪ | F2-patrons |

#### A.5 · L'API i la UI de `patterns`

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`patterns/views.py:544-549`** | PatternPOM | READ-dict | **`ancorats = {p.pom_master_id: p for p in PatternPOM.objects.filter(pattern_piece__pattern_file=fp)}`** — sobre **TOT** el PatternFile | **COL·LAPSA — i ja avui**: dues peces (dreta/esquerra) amb el mateix POM ja es trepitgen | 🔴 | F2-patrons |
| **`patterns/views.py:552-557`** | BaseMeasurement | READ-list | **`filter(model_id=fp.model_id, is_active=True)` — SENSE àncora `capa`** | **COL·LAPSA — forat d'Onada 1 no censat**: `RECENS_DELTA_ONADA1:201` declara `patterns/*` fora d'abast | 🔴 | **top-up-lectors** |
| `patterns/views.py:558` + `:135-146` `_alies_unics_del_customer` | CustomerPOMAlias | READ-dict | `per_pom.setdefault(a.pom_id, []).append(a)` → **només emet si `len(llista)==1`** | **OK** — l'únic node del repo que ja tolera N i **es calla** quan no pot desambiguar. **Precedent de mètode.** | ⚪ | F2-patrons |
| `patterns/views.py:559-600` | PatternPOM ↔ BaseMeasurement | CONTRACT-api | fila = `{'pom_master': bm.pom_id, 'ancorat': anc is not None, …}` — 1 fila per POM | COL·LAPSA (payload sense discriminant) | 🔴 | C4-ins |
| `patterns/views.py:199-215` | PatternPOM | CONTRACT-api | `'poms': [{'pom_code': p.pom_code, …} for p in sp.poms]` (modal d'export) | COL·LAPSA | 🟠 | C4-ins |
| `patterns/views.py:714` | GradedSpec | COUNT-gate **[SOLO-1]** (`gv.graded_specs`) | `gv.graded_specs.filter(is_active=True).count()` | IGNORA-2a (el número canvia de significat) | 🟡 | top-up-lectors |
| `patterns/serializers.py:304-315` | PatternPOM | CONTRACT-api **[SOLO-1]** (`piece.poms`) | `'poms': [{'id','pom_master','pom_code',…} for p in piece.poms.all()]` | OK (llista, porta `id`) | ⚪ | C4-ins |
| `patterns/views.py:312` | PatternPOM | READ-list **[SOLO-1]** | `prefetch_related('pieces__poms__pom_master')` | OK | ⚪ | F2-patrons |
| `patterns/annotation_views.py:521-528` | PatternPOM | READ-list | `filterset_fields = ['pattern_piece','pattern_piece__pattern_file','pom_master']` | IGNORA-2a (filtre per POM torna N) | 🟡 | C4-ins |
| `patterns/annotation_views.py:530-546` | PatternPOM | WRITE-create/update | `serializer.save()` + `_recalcular` — payload `{pattern_piece, pom_master, definicio_mesura}` | PETA (IntegrityError per la constraint) | 🔴 | C4-ins |
| `patterns/annotation_views.py:134-151` `_mesurar` | PatternPOM | CONTRACT-engine | resol per `pom.definicio_mesura` + `pom.pattern_piece` (per PK) | **OK** — l'única part del motor que no depèn del codi | ⚪ | F2-patrons |
| `patterns/annotation_views.py:554-557` `_esborra_un` | PatternPOM | WRITE-delete | `pom.delete()` per PK | OK | ⚪ | F2-patrons |
| `frontend/src/api/endpoints.js:813-824` | PatternPOM | CONTRACT-api | CRUD `/pattern-poms/` per `id` | OK | ⚪ | C4-ins |
| `frontend/src/pages/TallerPatro.jsx:332,356,820` | PatternPOM | CONTRACT-api | `pomActiu?.pom_master ?? ombra?.pomMaster` → `create({pattern_piece, pom_master, …})` | PETA | 🔴 | C4-ins |

#### VEREDICTE `patterns/`

**`patterns/` NO pot entrar sencer a `F2-patrons`.** Hi ha **dos nodes que han d'entrar abans**:

1. 🚨 **`patterns/views.py:552-557` és `top-up-lectors`, no `F2-patrons`.** És un lector de `BaseMeasurement`
   **sense àncora `capa`** — l'únic que va quedar fora quan Onada 1 va ancorar tots els altres, perquè
   `RECENS_DELTA_ONADA1_2026-07-31.md:201` declara `patterns/*` fora d'abast. **El dia que neixi la segona
   capa, `model-poms` emet dues files indistingibles per al mateix POM i `ancorats.get(bm.pom_id)` marca
   totes dues com a ancorades.** No espera la instància: espera la capa.
2. 🚨 **`patterns/views.py:544-549` ja col·lapsa AVUI, sense cap eix nou.** `ancorats` s'indexa per
   `pom_master_id` sobre **tot el PatternFile**, no per peça. La constraint és `(pattern_piece, pom_master)`
   — dues peces del mateix fitxer poden ancorar legalment el mateix POM, i el dict en perd una.

La resta (`ports.py`, `grading_projection.py`, `ftt_pom_layer.py`, `roundtrip.py`, `export.py`,
`adapters.py`) **sí** pot anar a `F2-patrons` en bloc — amb la condició que **`ftt_pom_layer.py` és el
sostre dur**: mentre l'etiqueta del DXF sigui `FTT "{codi}" {nom} = {valor} mm`, cap instància sobreviu un
roundtrip. Això és **disseny de format, no refactor**.

**Mitigant real:** `patterns_patternpom` té **0 files** als tres schemas. Tot `patterns/` és pre-producció.
El cost del canvi és de codi i de format, **mai de migració de dades**.

### B · `fitting/`

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `fitting/models.py:220` | GradedSpec | CONTRACT-engine | `unique_together = [('grading_version','pom','size_label','capa')]` | PETA (cal 5è camp) | 🔴 | C1-ins |
| `fitting/models.py:224-228` | GradedSpec | CONTRACT-engine | `CheckConstraint(capa='exterior')` `fitting_gradedspec_capa_gate_c1` | OK (comporta) | ⚪ | C4-ins |
| `fitting/models.py:400` | PieceFittingLine | CONTRACT-engine | `unique_together = [('piece_fitting','pom','size_label','capa')]` | PETA | 🔴 | C1-ins |
| `fitting/models.py:383` | PieceFittingLine | CONTRACT-engine | FK a POMMaster amb **`related_name='+'`** → **cap accessor invers** | OK, però invisible a tota auditoria per related_name | ⚪ | C1-ins |
| `fitting/models.py:129-137` | POMAlert | CONTRACT-engine | **cap `unique_together`**; FK `model`→`pom_alerts`, `size_fitting`→`pom_alerts`, `pom`→`alerts`. **Sense `capa`** | OK estructural / els escriptors sí peten | 🟠 | Onada2 |
| `fitting/graded_spec_views.py:39-42` | GradedSpec | READ-list | `filter(gv, is_active=True).order_by('pom_id','id')` — **sense `capa`** | COL·LAPSA | 🔴 | top-up-lectors |
| `fitting/graded_spec_views.py:57-74` | GradedSpec | READ-dict | **`rows_by_pom[pom.id] = {…'valors':{},'deltas':{}}`** + `rows_by_pom[pom.id]['valors'][s.size_label]` | **COL·LAPSA** (last-write-wins per talla) | 🔴 | top-up-lectors |
| `fitting/graded_spec_views.py:94-107` | BaseMeasurement | READ-dict | 4 mapes `{bm['pom_id']: …}` amb àncora `capa=SLUG_DEFECTE` | IGNORA-2a (l'àncora tapa la capa, no la instància) | 🟠 | top-up-lectors |
| `fitting/graded_spec_views.py:113` | GradingRule | READ-dict | `_load_grading_rules(model)` → `{pom_id: rule}` | IGNORA-2a | 🟡 | Onada2 |
| `fitting/serializers.py:32` | GradedSpec | COUNT-gate **[SOLO-1]** (`gv.graded_specs`) | `gv.graded_specs.count()` → `n_graded_specs` | IGNORA-2a (canvia de significat) | 🟡 | top-up-lectors |
| `fitting/serializers.py:246-249` | GradedSpec | READ-dict | **`spec_map[(gv_id, pom_id, size_label)]`** — sense `capa` | **COL·LAPSA** | 🔴 | top-up-lectors |
| `fitting/serializers.py:263-268` | BaseMeasurement | READ-dict | `ordre_map`/`nom_fitxa_map`/`bm_id_map` per **`(pom_id, capa)`** — ja composta a Onada 1 | OK avui, ha de créixer | 🟠 | top-up-lectors |
| `fitting/serializers.py:273` | PieceFittingLine | READ-dict | `clau_bm = (line.pom_id, line.capa)` | OK, ha de créixer | 🟠 | top-up-lectors |
| `fitting/serializers.py:286-315` | PieceFittingLine | CONTRACT-api | `out[]` amb `'pom_id'` + `'bm_id'` — la fila del payload **no porta capa** (comentari `:271`) | COL·LAPSA al contracte | 🔴 | C4-ins |
| `fitting/serializers.py:211-214` | PieceFittingLine | CONTRACT-api | `fields=['id','piece_fitting','pom','size_label',…]` — **`capa` no hi és** | COL·LAPSA | 🟠 | C4-ins |
| `fitting/serializers.py:68-71` | POMAlert | CONTRACT-api | `fields='__all__'` + `pom_codi` | OK (`__all__` absorbeix camps nous) | ⚪ | C4-ins |
| **`fitting/services.py:329-338` `create_piece_fitting`** | GradedSpec → PieceFittingLine | WRITE-create | `for spec in GradedSpec.objects.filter(gv, is_active=True): PieceFittingLine.objects.create(pom=spec.pom, size_label=…)` — **`capa` no es propaga** | **PETA** (IntegrityError: dues specs → mateixa línia) | 🔴 | **Onada2** |
| **`fitting/services.py:362-380` `consolidate_base_from_fitting`** | PieceFittingLine | WRITE-update | `BaseMeasurement.get_or_create(model=model, pom=line.pom)` — **`line.capa` es perd** | **PETA/COL·LAPSA**: la línia porta capa, el destí no la rep | 🔴 | **Onada2** |
| `fitting/services.py:501-506` `discard_piece_fitting` | PieceFittingLine | WRITE-update | `filter(piece_fitting_id).update(valor_real=F('valor_teoric'))` | OK (massiu) | ⚪ | Onada2 |
| `fitting/views.py:129-138` | POMAlert | READ-list | `filterset_fields=['estat','tipus','model','pom']` | IGNORA-2a | 🟠 | C4-ins |
| `fitting/views.py:568-570` | PieceFittingLine | READ-list | queryset `select_related('pom', …)`, autosave per PK | OK | ⚪ | C1-ins |
| **`fitting/views.py:617-619`** | PieceFittingLine | READ-list | `filter(piece_fitting=pf, pom=line.pom)` — **`_resp` torna TOTES les línies del POM** | **COL·LAPSA**: la resposta barreja les dues instàncies | 🔴 | C1-ins |
| **`fitting/views.py:665-668`** | PieceFittingLine | WRITE-update | `filter(piece_fitting=pf, pom=line.pom, size_label=sl).update(valor_real=val)` — **sense `capa`** | **COL·LAPSA destructiu**: propagar una instància reescriu l'altra | 🔴 | **Onada2** |
| `fitting/views.py:641` | GradingRule | READ-dict | `_load_grading_rules(pf.model).get(line.pom_id)` | IGNORA-2a | 🟡 | Onada2 |
| `fitting/repas_views.py:182-186` | PieceFittingLine | READ-list | `filter(piece_fitting__in=peces).select_related('pom', …)` | OK (llista) | ⚪ | top-up-lectors |
| `fitting/repas_views.py:259-264` | BaseMeasurement | READ-dict | 4 mapes `{p: …}` per `pom_id` sol, amb àncora `capa=SLUG_DEFECTE` | IGNORA-2a | 🟠 | top-up-lectors |
| `fitting/repas_views.py:274-287` | PieceFittingLine | READ-dict | **`files[pom_id]`** — la fila del Repàs és per POM | **COL·LAPSA** | 🔴 | top-up-lectors |
| `fitting/staleness.py:179-183` | GradedSpec | READ-list **[SOLO-1]** (`gv.graded_specs`) | `gv.graded_specs.values_list('generated_from_version')` → `min()` | OK (agregat) | ⚪ | top-up-lectors |
| `repair_fitting_20260710.py:76-84` | GradedSpec | READ-dict | `filter(gv__…, pom_id, size_label).first()` — **`capa` absent tot i ser a l'unique** | COL·LAPSA silenciós | 🔴 | Onada2 |
| `repair_fitting_20260710.py:97-119` | GradedSpec | READ-dict | `_differ(base, graded)` per `pom_id` sol | COL·LAPSA | 🔴 | Onada2 |
| `repair_fitting_20260710.py:123-136` | ClientMesuraPerfil | READ-list + WRITE-update | `(garment_type_id, talla, pom_id__in)` — **omet `codi_client`**, 1r camp de l'unique | IGNORA-2a (**bug preexistent**, agreujat) | 🔴 | Onada2 |

### C · `pom/` — app code

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `pom/models.py:612` | GarmentPOMMap | CONTRACT-engine | `unique_together=[('garment_type_item','pom','capa')]` | PETA | 🔴 | C1-ins |
| `pom/models.py:898` | ItemBaseMeasurement | CONTRACT-engine | `unique_together=[('base_set','pom','capa')]` | PETA | 🔴 | C1-ins |
| `pom/models.py:1119` | GradingRule | CONTRACT-engine | `unique_together=[('rule_set','pom')]` — **sense capa, per decisió C1 §3c** | IGNORA-2a per disseny; si una instància ha de graduar diferent, **no hi cap** | 🟠 | Onada2 |
| `pom/models.py:1171` | ClientMesuraPerfil | CONTRACT-engine | `[('codi_client','garment_type','pom','talla')]` — sense capa | COL·LAPSA (Welford barreja instàncies) | 🟠 | Onada2 |
| `pom/models.py:423` | CustomerPOMAlias | CONTRACT-engine | `(customer, client_code)` — **ja permet N codis → 1 POM** | **OK** — la taula que millor sobreviu; és on el cas U2/U3 viu legítimament | ⚪ | consolidació-catàleg |
| `pom/models.py:373` | POMEstadisticaTenant | CONTRACT-engine | `[('pom','garment_type','talla_label')]` | COL·LAPSA — **però 0 escriptors i 0 lectors a tot el repo (taula morta)** | ⚪ | consolidació-catàleg |
| `pom/models.py:689-697` | ItemBaseSet | CONTRACT-engine | `(item, size_system, fit_type)` + parcial no-fit — **cap eix POM** | OK | ⚪ | FORA: sense eix POM |
| **`pom/services.py:1023-1044` `_upsert_graded_spec`** | GradedSpec | WRITE-create/update | **`update_or_create(grading_version_id, pom_id, size_label)` — `capa` ABSENT del lookup** tot i ser a l'unique | **PETA** (`MultipleObjectsReturned`) — **l'escriptor únic del motor; és LA porta d'Onada 2** | 🔴 | **Onada2** |
| `pom/services.py:280-296` | GradedSpec | WRITE-create | bucle `for pom_id, base_val in base_measurements.items(): for size_label in size_run: _upsert_graded_spec(pom_id=…)` | COL·LAPSA aigües amunt | 🔴 | Onada2 |
| `pom/services.py:702-712` `_load_grading_rules` | GradingRule | READ-dict | **`{r.pom_id: r}`** (resident → fallback ruleset) | IGNORA-2a — consumit per 7 superfícies | 🟠 | Onada2 |
| `pom/services.py:729-741` `_load_model_overrides` | ModelGradingOverride | READ-dict | `{(pom_id, size_label): v}` amb `capa=SLUG_DEFECTE`; el docstring declara **FRONTERA C3** | IGNORA-2a | 🟠 | Onada2 |
| `pom/services.py:676-681` `_te_regles` | GradingRule | COUNT-gate | `filter(rule_set_id, actiu=True).exists()` | OK | ⚪ | Onada2 |
| `pom/services.py:394-419` `preview_graded_specs` | GradedSpec | READ-dict | **`out[pom_id] = row`** → `{pom_id: {talla: valor}}` | COL·LAPSA (preview del wizard) | 🔴 | top-up-lectors |
| `pom/services.py:482,501` | GradedSpec | COUNT-gate | `filter(grading_version__size_fitting=sf).count()/.exists()` | OK (agregat) | ⚪ | Onada2 |
| `pom/services.py:549-554` `update_client_profile` | ClientMesuraPerfil | WRITE-create/update | `get_or_create(codi_client, garment_type_id, pom_id, talla)` | **COL·LAPSA**: Welford acumula les dues instàncies al mateix perfil | 🔴 | Onada2 |
| `pom/services.py:601-630` `maybe_learn_customer_alias` | CustomerPOMAlias | WRITE-create/update | `get_or_create(customer, client_code)` + guard `ja_reclamat` → `pendent_revisio=True` | **PETA el cas legítim**: el guard marca com a sospitós exactament el que la instància legitima | 🔴 | consolidació-catàleg |
| `pom/nomenclatura.py:29-42` `alies_per_pom` | CustomerPOMAlias | READ-dict | **`out.setdefault(pom_id, {…})`** — el `setdefault` **descarta** els àlies extra | COL·LAPSA (consumit per `models_app/views.py:1044,1059,1675,1687`) | 🟠 | top-up-lectors |
| **`pom/size_map_views.py:54-70` `_apply_many_to_one_guard`** | GradingRule | COUNT-gate | **`counts[r['pom_id']] += 1`; ≥2 → `many_to_one`, desvincula totes dues**. Exempció explícita per `alias_match` | **PETA el cas legítim** — node que **canvia de significat** | 🔴 | C4-ins |
| `pom/size_map_views.py:955-975` | GradingRule | WRITE-create/update | `update_or_create(rule_set=rule_set, pom=pom, defaults=…)` | OK avui / PETA amb l'eix | 🟠 | C4-ins |
| `pom/size_map_views.py:756` | GradingRule | COUNT-gate **[SOLO-1]** | `_cont.regles.count()` (409 `container_exists`) | IGNORA-2a | 🟡 | C4-ins |
| `pom/size_map_views.py:1024` | GradingRule | CONTRACT-api **[SOLO-1]** | `'rules_count': rule_set.regles.count()` | IGNORA-2a | 🟡 | C4-ins |
| `pom/grading_views.py:90-114` `taula_mesures_view` | GradedSpec | READ-dict | **`cells[pom_id][spec.size_label]`** + `poms_seen` set per `pom_id` | **COL·LAPSA** | 🔴 | top-up-lectors |
| `pom/grading_views.py:155` | GradedSpec | CONTRACT-api | **`'cells': {str(k): v …}`** — el payload s'indexa per `pom_id` string | COL·LAPSA al contracte | 🔴 | C4-ins |
| `pom/grading_views.py:120-140` | BaseMeasurement | READ-dict | fallback sense grading: `cells[pom_id][base_size_label]`, **sense àncora `capa`** | COL·LAPSA (**i forat d'Onada 1: C7 revertit**) | 🔴 | top-up-lectors |
| `pom/s6_views.py:163-193` | GradedSpec | READ-dict | **`pom_dict[pid]['values'][spec.size_label]`** — sense `capa` | COL·LAPSA | 🔴 | top-up-lectors |
| `pom/s8_views.py:61-67`, `:110-116` | GradingRule | READ-list | `filter(rule_set, actiu=True).order_by('pom__categoria__display_order','pom__codi_client')` (CSV) | IGNORA-2a (dues files idèntiques al CSV) | 🟡 | C4-ins |
| `pom/s8_views.py:175-183` | PieceFittingLine | READ-list | `filter(piece_fitting=pf).order_by('pom__codi_client','size_label')` | OK (llista) | ⚪ | top-up-lectors |
| `pom/s8_views.py:184-207` | PieceFittingLine | READ-dict | `tol_map[(bm.pom_id, bm.capa)]` ← `tol_map.get((line.pom_id, line.capa))` | OK avui, **ha de créixer** | 🟠 | top-up-lectors |
| `pom/s10_views.py:53-60` `_tolerance_map` | BaseMeasurement | READ-dict | `tol[(bm.pom_id, bm.capa)]` | OK avui, ha de créixer | 🟠 | top-up-lectors |
| `pom/s10_views.py:84-94` | PieceFittingLine | READ-list + dict | `filter(piece_fitting=pf)` + `tol_map.get((line.pom_id, line.capa))` | OK avui, ha de créixer | 🟠 | top-up-lectors |
| **`pom/s10_views.py:136-152`** | POMAlert | WRITE-create/update | **`update_or_create(model=model, pom_id=…, size_fitting=sf, defaults=…)`** — sense `capa`, **sense `size_label`** | **COL·LAPSA doble**: ja avui una sola alerta per (model,pom,sf) tapa totes les talles | 🔴 | Onada2 |
| `pom/s10_views.py:99-121` | PieceFittingLine | CONTRACT-api | `resultats[] = {'pom_id': line.pom_id, 'talla': …}` — sense capa ni instància | COL·LAPSA | 🔴 | C4-ins |
| `pom/s11_views.py:39-63` | POMAlert | READ-list | `values('pom__codi_client','pom__nom_client').annotate(n=Count('id'))` — top-poms agrupat per codi | COL·LAPSA (el rànquing suma instàncies) | 🟠 | top-up-lectors |
| `pom/s11_views.py:95-107` | POMAlert | WRITE-update | `get(pk=alert_id)` — per PK | OK | ⚪ | Onada2 |
| `pom/s11_views.py:122-140` | POMAlert | READ-list | `filter(model_id).select_related('pom')` → `a.pom.codi_client` | COL·LAPSA a la lectura (files idèntiques) | 🟠 | top-up-lectors |
| **`pom/s11_views.py:166-206`** | POMAlert | WRITE-create/update | **`base_map = {bm.pom_id: …}`** amb àncora; després `update_or_create(model=model, pom=pom, …)` | **COL·LAPSA**; el body `{pom_id, value_cm}` ja no pot dir de què parla (comentari `:161-164`) | 🔴 | C4-ins |
| `pom/s4_views.py:59-64`, `:210-216` | GradingRule | READ-dict | **`filter(rule_set).filter(Q(pom__pom_global__codi=pom_codi) \| Q(pom__codi_client=pom_codi)).first()`** — resol per **CODI STRING** sense `order_by` | **IGNORA-2a** (`.first()` arbitrari) | 🔴 | C4-ins |
| `pom/s4_views.py:292-300` | GradingRule | READ-dict + WRITE-update | **`original_rules = {r.pom_id: r …}`** → `custom_rules` per `rule.pom_id` | COL·LAPSA (restaurar perfil) | 🟠 | consolidació-catàleg |
| `pom/s2_views.py:149-155` | GradingRule | READ-list | `filter(rule_set_id, actiu=True).order_by('pom__codi_client')` | IGNORA-2a | 🟡 | C4-ins |
| `pom/s2_views.py:221-231` | GradingRule | WRITE-create | `for rule in filter(rule_set=original_rs): create(rule_set=nou_rs, pom=rule.pom, …)` (clonar perfil) | OK (còpia fila a fila) | ⚪ | consolidació-catàleg |
| `pom/s2_views.py:282-288` | GradingRule | READ-dict + WRITE-update | `Q(pom__pom_global__codi) \| Q(pom__codi_client)` → `.first()` **sense `order_by`** | IGNORA-2a | 🔴 | C4-ins |
| `pom/s2_serializers.py:156-160` | GradingRule | READ-list | `filter(rule_set, actiu).order_by('pom__codi_client')[:5]` (preview) | IGNORA-2a | 🟡 | C4-ins |
| `pom/views.py:207-212` | GradingRule | READ-list **[SOLO-1]** | `Prefetch('regles', queryset=…)` — **`'regles'` com a STRING** | OK | ⚪ | C4-ins |
| `pom/views.py:232` | GradingRule | COUNT-gate **[SOLO-1]** | `annotate(n_regles=Count('regles')).filter(n_regles__gt=0)` | OK (predicat >0) | ⚪ | C4-ins |
| `pom/views.py:284-291` | GradingRule | READ-list | `search_fields=['pom__codi_client','pom__nom_client']`, `ordering=['rule_set','pom__codi_client']` | IGNORA-2a (ordre no determinista) | 🟠 | C4-ins |
| `pom/views.py:318-340` | GarmentPOMMap | READ-list | `filterset_fields={'garment_type_item':['exact'],'pom':['exact']}` — **`capa` no filtrable** | COL·LAPSA a la UI | 🟠 | C4-ins |
| `pom/views.py:356-368` | ItemBaseSet | COUNT-gate **[SOLO-1]** | `annotate(mesures_count=Count('measurements', distinct=True), mesures_amb_valor=…)` | IGNORA-2a: **compta FILES, no POMs** | 🟠 | C4-ins |
| `pom/views.py:394-400` | ItemBaseMeasurement | COUNT-gate **[SOLO-1]** | `instance.measurements.exists()/.count()` (guard de destroy) | OK (predicat >0) | ⚪ | C1-ins |
| `pom/views.py:411-441` | ItemBaseMeasurement | WRITE-create/update | CRUD pla, `ordering=['garment_type_item','pom']` | IGNORA-2a (ordre no determinista) | 🟠 | C4-ins |
| **`pom/views.py:445-511` `upsert`** | ItemBaseMeasurement | WRITE-create/update | **`update_or_create(base_set=base_set, pom_id=pom_id, defaults=…)`** — body `{garment_type_item, pom, base_set?}`, **`capa` absent** | **PETA** (`MultipleObjectsReturned`) | 🔴 | C1-ins |
| `pom/views.py:468-490` | ItemBaseSet | COUNT-gate | **`base_set_ambigu` 409 amb candidats** quan hi ha 2+ sets | **OK — precedent exacte per a `instancia_ambigua`** | ⚪ | consolidació-catàleg |
| `pom/views.py:519-533` | CustomerPOMAlias | READ-list | `filterset_fields=['customer','pom','pendent_revisio','origen']`, `order_by('client_code','id')` | OK (ja tolera N) | ⚪ | consolidació-catàleg |
| `pom/serializers.py:390-405` | GarmentPOMMap | CONTRACT-api | `fields=(…'pom', 'pom_code',…)` — **`capa` no exposada** | COL·LAPSA | 🟠 | C4-ins |
| `pom/serializers.py:459-470` | ItemBaseMeasurement | CONTRACT-api | `fields=(…'base_set','pom',…)` — **`capa` no exposada** | COL·LAPSA | 🟠 | C4-ins |
| `pom/serializers.py:425-440` | ItemBaseSet | CONTRACT-api | `mesures_count`/`mesures_amb_valor` | IGNORA-2a | 🟡 | C4-ins |
| `pom/serializers.py:189-200` | GradingRule | CONTRACT-api | `fields=(…'pom','pom_codi',…)`, `read_only=('rule_set',)` | IGNORA-2a | 🟡 | C4-ins |
| `pom/serializers.py:514-525` | CustomerPOMAlias | CONTRACT-api | `fields=(…'pom','client_code',…)` | OK | ⚪ | consolidació-catàleg |
| `pom/serializers.py:282-287` | GradingRule | COUNT-gate **[SOLO-1]** | `inst.regles.exists()/.count()` (guard de canvi de `size_system`) | OK | ⚪ | C4-ins |
| `pom/grading_utils.py:777-790` `classifica_fitxa_vs_contenidor` | GradingRule | READ-dict **[SOLO-1]** | **`cont_by = {r.pom_id: r for r in container.regles.all()}`** → `cont_by.get(s['pom_id'])` | **COL·LAPSA**: sembra/amplia/conflicte mal classificats | 🔴 | consolidació-catàleg |
| `pom/wizard_views.py:77-101` `suggested_poms_view` | GarmentPOMMap | READ-list | `filter(garment_type_item_id).order_by('-is_key','ordre')` → `data[] = {'id': pom.id, …}` | COL·LAPSA (dues entrades amb el mateix `id`) | 🔴 | C4-ins |
| `pom/wizard_views.py:252-255` | BaseMeasurement | COUNT-gate | `n_poms = filter(model, is_active=True).count()`; gate `< 3` | IGNORA-2a: el gate compta files, no POMs | 🟠 | Onada2 |
| `pom/dictionary_service.py:132-135` | CustomerPOMAlias | READ-dict | `existing = {client_code.lower(): a}` | OK (clau = codi) | ⚪ | consolidació-catàleg |
| `pom/dictionary_views.py:96-99`, `:163-172` | CustomerPOMAlias | WRITE-create/update | `update_or_create(customer, client_code, defaults={'pom': pom, …})` | OK | ⚪ | consolidació-catàleg |
| `pom/s9_views.py:55-58` | GarmentPOMMap | COUNT-gate | `count() >= 10` («N relacions POM-prenda») | IGNORA-2a: el text menteix amb instàncies | 🟡 | consolidació-catàleg |

### D · Frontend — el nom que viatja al payload (des del camí 1B)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `POMBrowser.jsx:26-70` | GarmentPOMMap | CONTRACT-api | `normalizePOMs` → `{map_id, pom_id, …}` (1 fila per POM) | COL·LAPSA visual | 🟠 | C4-ins |
| `POMBrowser.jsx:133` | GarmentPOMMap | CONTRACT-api | **`mappedPomIds = new Set(poms.map(p => p.pom_id))`** | **COL·LAPSA**: «ja assignat» dispara sobre la 2a instància | 🔴 | C4-ins |
| `POMBrowser.jsx:152-160` | GarmentPOMMap | WRITE-create | `POST {garment_type_item, pom, is_key, ordre}` — **sense `capa`** | PETA (400 `already_assigned`) | 🔴 | C4-ins |
| `api/endpoints.js:265` | GradingRule | CONTRACT-api | **`PATCH /grading-rule-sets/{setId}/regles/{pom}/editar/`** — **la URL identifica per CODI DE POM** | **IGNORA-2a** | 🔴 | C4-ins |
| `ImportWizard.jsx:286,634,644-652,666` | (import) | CONTRACT-api | **`taula[pom_master_id][talla]`** + `base_values[p.pom_master_id]` + `grading[String(p.pom_master_id)]` | **COL·LAPSA**: l'estat central del wizard | 🔴 | C4-ins |
| `TechSheetEditor.jsx:5355,7702,7712` | GradedSpec | CONTRACT-api | `sf.n_graded_specs` (recompte) | IGNORA-2a | 🟡 | C4-ins |
| `api/endpoints.js:593-614,717-718,333-336,813-824` | GarmentPOMMap, ItemBaseMeasurement, ItemBaseSet, POMAlert, CustomerPOMAlias, PatternPOM | CONTRACT-api | CRUD per `id` de fila | OK | ⚪ | C4-ins |

### E · `models_app/` · `tenants/` · `tasks/` — nodes que toquen les taules del camí 1B

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`models_app/views.py:1136`** | ItemBaseMeasurement | READ-dict | **`ibms = {i.pom_id: i for i in …filter(base_set=base_set)}`** | **COL·LAPSA** | 🔴 | C1-ins |
| **`models_app/views.py:1145-1146`** | ItemBaseMeasurement | READ-dict | **`ibms = {i.pom_id: i …filter(garment_type_item=item)}`** (camí llegat) | **COL·LAPSA** | 🔴 | C1-ins |
| `models_app/views.py:1160-1230` | ItemBaseMeasurement | READ-dict | `ibm = ibms.get(m.pom_id)` — el map porta capa, el lookup no | COL·LAPSA | 🔴 | C1-ins |
| `models_app/views.py:1118-1126` | GarmentPOMMap | READ-list | `filter(pom_id__in=subconjunt)`; `desconeguts = subconjunt - {m.pom_id …}` | COL·LAPSA | 🔴 | C1-ins |
| `models_app/views.py:1037-1060` | GarmentPOMMap | READ-list | `filter(garment_type_item)` → payload amb `pom_id` sol | COL·LAPSA | 🟠 | C1-ins |
| `models_app/views.py:1044,1059` | CustomerPOMAlias | READ-dict | `camps_de(alias_by_pom, pom.id)` | COL·LAPSA | 🟠 | top-up-lectors |
| **`models_app/views.py:1637-1642`** | GradedSpec | READ-dict | **`graded_by_pom[pom_id][spec.size_label]` — l'ÚNIC lector de `models_app/` sense filtre de `capa`** | **COL·LAPSA (ja avui)** | 🔴 | C1-ins |
| `models_app/views.py:1707` | GradedSpec | CONTRACT-api | `'graded': graded_by_pom.get(pom.id, {})` | COL·LAPSA | 🔴 | C1-ins |
| `models_app/views.py:2494-2497` | GradedSpec | READ-dict | `graded[spec.size_label]` dins `filter(gv, pom=pom)` | COL·LAPSA | 🔴 | C1-ins |
| `models_app/views.py:2634-2636` | GradedSpec | READ-list | `filter(gv, pom, size_label).values_list().first()` | PETA en silenci | 🔴 | C1-ins |
| **`models_app/views.py:2789-2793`** | GradedSpec | READ-dict + CONTRACT-api | `graded[spec.size_label]` → **`linies = [{'id': f'{pom.id}:{s}'}]`** | **COL·LAPSA**: dues instàncies → el mateix `id` de línia | 🔴 | C1-ins |
| `models_app/views.py:3977-3983` | GradedSpec | READ-dict | `dict(…filter(gv, pom_id, capa=SLUG_DEFECTE).values_list('size_label','graded_value_cm'))` | COL·LAPSA (capa resolta, instància no) | 🔴 | C1-ins |
| **`models_app/views.py:3657`** | ItemBaseMeasurement | READ-dict | **`actuals = {i.pom_id: i …filter(base_set=base_set)}`** (diff de promoció) | **COL·LAPSA** | 🔴 | C1-ins |
| **`models_app/views.py:3660-3661`** | GarmentPOMMap | READ-list | **`poms_item = set(…values_list('pom_id'))`**; `if bm.pom_id not in poms_item → ampliaria_item` | **COL·LAPSA**: una instància nova mai es detecta com a ampliació | 🔴 | C1-ins |
| `models_app/views.py:3695-3699` | ItemBaseMeasurement | READ-list | `.exclude(pom_id__in=poms_model)` («sobrarien») | COL·LAPSA | 🟠 | C1-ins |
| **`models_app/views.py:3756-3765`** | GarmentPOMMap | WRITE-create | **`get_or_create(garment_type_item=item, pom_id=…)` — sense `capa`** | **PETA** | 🔴 | C1-ins |
| **`models_app/views.py:3774-3796`** | ItemBaseMeasurement | WRITE-create/update | **`get_or_create(base_set=base_set, pom_id=bm.pom_id, defaults=…)` — sense `capa`** | **PETA** | 🔴 | C1-ins |
| `models_app/views.py:3851-3852` | ItemBaseMeasurement | READ + WRITE-update | `filter(base_set, pom_id).first()` (acte canònic) | PETA en silenci | 🔴 | C1-ins |
| `models_app/views.py:3288-3298` | POMAlert | READ-list | `filter(model_id).exclude(estat__in=RESOLVED)` → `a.pom.codi_client` | COL·LAPSA a la lectura | 🟠 | top-up-lectors |
| `models_app/views.py:857,930,1001,1465` | GradingRule | CONTRACT-engine **[SOLO-1]** (`.regles`) | `…grading_rule_set.regles.all()` → `materialize_model_grading_rules` | IGNORA-2a | 🟡 | Onada2 |
| `models_app/views.py:586` | GradingRule | COUNT-gate | `filter(rule_set_id, actiu=True).count()==0` → `ruleset_buit` | OK | ⚪ | FORA: gate de volum |
| `models_app/views.py:1957-1959`, `:4039-4041` | GradingRule | READ (sembra) | `filter(rule_set_id, pom_id).first()` | IGNORA-2a | 🟡 | Onada2 |
| `models_app/views.py:2451`, `:2826` | GradedSpec | COUNT-gate | `.count()` / `.exists()` | OK | ⚪ | FORA: agregat |
| **`models_app/extraction_views.py:1174-1188`** | CustomerPOMAlias (efecte) | COUNT-gate | **`counts[r['pom_master_id']] += 1`; >1 → desvincula totes dues** | **PETA el cas legítim — node que INVERTEIX la llei** | 🔴 | C1-ins |
| **`models_app/extraction_views.py:1734,1754`** | (wizard) | COUNT-gate | **`presos = {p['pom_master_id']: ordre}` + error `pom_ja_usat`** | **PETA el cas legítim** | 🔴 | C1-ins |
| **`models_app/extraction_views.py:2176-2185`** | (import W5) | READ-dict | **`valors.setdefault(pid, {})[talla] = valor`** — el dict central de tot l'import | **COL·LAPSA**: font única de BaseMeasurement + regles + overrides | 🔴 | C1-ins |
| `models_app/extraction_views.py:2047-2053` | (import W2) | READ-dict | `valors.setdefault(pid, {})[talla] = valor` | COL·LAPSA | 🔴 | C1-ins |
| `models_app/extraction_views.py:2201,2245,2288,2432` | (import) | READ-dict | remaps que arrosseguen `pid` sol | COL·LAPSA | 🟠 | C1-ins |
| `models_app/extraction_views.py:1029-1035` | CustomerPOMAlias | READ | `filter(customer, client_code__iexact, pom__isnull=False).first()` | COL·LAPSA (retorna POM sense instància) | 🔴 | C1-ins |
| `models_app/extraction_views.py:1488,1667,1847,2311,2364` | (contractes) | READ-dict/list | `{p['pom_master_id']: …}` / llistes de `pom_master_id` | COL·LAPSA | 🟠 | C1-ins |
| `models_app/extraction_views.py:2688-2698` | (overrides) | WRITE-create | `for pom_id in pom_divergents: for label, val in valors.get(pom_id)…` | COL·LAPSA aigües amunt | 🟠 | C1-ins |
| `models_app/extraction_views.py:901`, `:2657,2664` | GradingRule | READ/COUNT **[SOLO-1]** (`.regles`) | `…regles.values_list(…).first()` / `container.regles.exists()` | IGNORA-2a | 🟡 | Onada2 |
| `models_app/services.py:264-308`, `:390-405` | GradingRule | CONTRACT-engine + WRITE | `r.pom_id` / `update_or_create(rule_set=container, pom_id=s['pom_id'])` | IGNORA-2a | 🟡 | Onada2 |
| `models_app/services.py:340-360` | (promoció) | CONTRACT-api | `items[].pom_id` | COL·LAPSA | 🟠 | top-up-lectors |
| `models_app/services_size_check.py:113-119` | GradingRule | COUNT-gate | `.exists()` | OK | ⚪ | FORA: gate booleà |
| `models_app/serializers_size_check.py:93-100` | GradingRule | READ-dict | `_load_grading_rules(obj.model)` → `{pom_id: rule}`, **al costat d'un `bm_map` per `(pom_id, capa)`** | IGNORA-2a — **on la incoherència es veu millor** | 🟠 | Onada2 |
| `models_app/pom_placement_views.py:52-64` | POMPlacement | READ-dict | `exacte`/`germana`/`merged` — **3 dicts per `pom_id` sol sobre taula que JA porta `capa`** | COL·LAPSA (forat viu de C2) | 🔴 | C1-ins |
| `models_app/pom_placement_views.py:130-139` | POMPlacement | WRITE-create/update | `update_or_create(item_fitxer, pom_id, view_slot)` — sense `capa` | PETA/trepitja | 🔴 | C1-ins |
| `models_app/signals.py` (sencer, 373 línies) | — | — | **CAP receiver escriu GradedSpec / PieceFittingLine / POMAlert / ClientMesuraPerfil** (verificat línia a línia) | — | ⚪ | FORA: registre net |
| **`tenants/federation_service.py:572-580` `_clau_natural_pom`** | POMMaster | CONTRACT-api | **`(POMGlobal.codi, POMMaster.codi_client)`** — cap eix de capa ni instància | **COL·LAPSA el pont entre cases**; node de més radi | 🔴 | Onada2 |
| `tenants/federation_service.py:598-618` | GradingRule (forma) | CONTRACT-api | `regles[] = {'clau': _clau_natural_pom(r.pom), …}` | COL·LAPSA (l'última guanya al destí) | 🟠 | Onada2 |
| `tenants/federation_service.py:722-742` | GradingRule (destí) | WRITE-create | `if ModelGradingRule.filter(model=twin, pom=pom).exists(): saltat` | IGNORA-2a: la 2a instància no viatja mai | 🟠 | Onada2 |
| `tenants/federation_service.py:528-531` | GradedSpec | CONTRACT-engine | doctrina: **`GradedSpec` no viatja mai, es recalcula** | **OK — l'exclusió que PROTEGEIX la federació** | ⚪ | FORA: exclusió declarada |
| **`tenants/federation_service.py:585-590` `_llegeix_patrimoni`** | BaseMeasurement | READ-list | `filter(model, is_active=True)` — **sense àncora `capa`** | COL·LAPSA (**forat d'Onada 1**) | 🔴 | top-up-lectors |
| **`tasks/views_b.py:970`** | GarmentPOMMap | COUNT-gate **[SOLO-1]** (`pom_maps`) | **`poms_count=Count('pom_maps', distinct=True)`** | COL·LAPSA de significat: compta FILES, no POMs | 🟠 | consolidació-catàleg |
| `tasks/serializers_b.py:153-154` | GarmentPOMMap | CONTRACT-api **[SOLO-1]** | `poms_count = IntegerField(default=0)` | COL·LAPSA (hereta) | 🟠 | consolidació-catàleg |
| `tasks/models.py:340-372` | SizeDefinition, GradingRuleSet | CONTRACT-engine | FK declaratives; `ItemBaseSet`/`GarmentPOMMap` hi apunten `db_constraint=False` | OK | ⚪ | FORA: sense eix POM |
| `planning/`, `commerce/`, `backoffice/`, `accounts/` | — | — | **cap consumidor** (grep exhaustiu). `commerce`/`backoffice` `.lines` són homònims aliens | — | ⚪ | FORA: cap consumidor |

### F · `management/commands/` i `seed_data/` — els 🔴 del camí 1B

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `export_losan_package.py:252-258` | GarmentPOMMap | READ-list | `(gti_key, pom_key)` — **la fila JSON no porta `capa`** | COL·LAPSA (2 files → el loader n'escriu 1) | 🔴 | C1-ins |
| `export_losan_package.py:260-265` | ItemBaseMeasurement | READ-list | `(gti_key, pom_key)` — **ni `capa` ni `base_set`** | COL·LAPSA | 🔴 | C1-ins |
| `load_losan_package.py:84-100` `_upsert` | (genèric) | CONTRACT-engine | `filter(**lookup).first()` + save | **COL·LAPSA silenciós — no peta mai** | 🔴 | C1-ins |
| `load_losan_package.py:363` | GarmentPOMMap | WRITE-create/update | `{'garment_type_item': gti, 'pom': pom}` | COL·LAPSA | 🔴 | C1-ins |
| `load_losan_package.py:379-381` | ItemBaseMeasurement | WRITE-create/update | `{'base_set': base_set, 'pom': pom}` | COL·LAPSA | 🔴 | C1-ins |
| `author_baby_pom_maps.py:146-215` | GarmentPOMMap | READ-dict + WRITE-delete | **`{m.pom_id: m}`** → `deletes` per `pid` | **COL·LAPSA**: la instància invisible queda òrfena i mai s'esborra | 🔴 | C1-ins |
| `load_map_inline.py:144-145` | GarmentPOMMap | WRITE-update | `update_or_create(garment_type_item, pom, defaults={'ordre': i})` | **PETA** — i `ordre=i` és justament l'ordinal de cel·la d'on naixeria la 2a instància | 🔴 | C1-ins |
| `validate_los_maps.py:77-104` | GarmentPOMMap | READ-dict + WRITE | `pairs = set((item.id, pom.id))`, `{(gti_id, pom_id): m}` | COL·LAPSA (el CSV no pot expressar 2 instàncies) | 🔴 | C1-ins |
| `consolidate_pom_catalog.py:212-215` | GarmentPOMMap | WRITE-create | `get_or_create(garment_type_item, pom)` | COL·LAPSA | 🔴 | C1-ins |
| `consolidate_pom_catalog.py:113-119` | ItemBaseMeasurement, ClientMesuraPerfil, POMAlert, POMEstadisticaTenant | WRITE-update **[SOLO-1]** | `getattr(prim, rel).all()` → `.update(pom=dest)` amb `except IntegrityError → coll` | PETA-controlat (silenci comptat) | 🔴 | consolidació-catàleg |
| `seed_losan_rules_v2.py:128-134` | GradingRule | COUNT-gate | **`seen[pom.codi_client]` → «2n àlies → mateix POM = col·lisió, skip»** | **COL·LAPSA — el node conceptual del Patró A** | 🔴 | C4-ins |
| `seed_losan_grading_v3.py:185-196` | GradingRule | WRITE-create/update | `update_or_create(rule_set, pom)` **sense desduplicació d'àlies** (a diferència de v2) | COL·LAPSA silenciós | 🔴 | C4-ins |
| **`bootstrap_tenant.py:162`** | GarmentPOMMap | CONTRACT-engine | **clau natural `('garment_type_item','pom')` — `capa` ja hi falta AVUI** | COL·LAPSA (`--additive`) / **PETA** (`update_or_create`) | 🔴 | C1-ins |
| `bootstrap_tenant.py:332-357` | GarmentPOMMap, GradingRule | CONTRACT-engine + WRITE | `lookup[att] = values.pop(att)`; la resta (inclòs `capa`) cau a `defaults` | COL·LAPSA | 🔴 | C1-ins |
| `bootstrap_tenant.py:356` | GarmentPOMMap, GradingRule | CONTRACT-engine | **`maps[model][src_pk] = dst_pk`** | **COL·LAPSA de 2n ordre**: el mapa de remapeig FK queda corromput per a tota peça posterior | 🔴 | C1-ins |
| `clone_model_for_qa.py:127-141` | GradedSpec | READ-dict + COUNT-gate | **`specmap = {(pom_id, size_label): valor}`** sense `capa` | COL·LAPSA: fals verd/vermell a la verificació del clon QA | 🔴 | Onada2 |
| `reseed_tenant_fhort.py:303`, `:390` | GarmentPOMMap, GradingRule | WRITE-create | **`bulk_create(…, ignore_conflicts=True)`** | COL·LAPSA **MUT** | 🔴 | FORA: mort pel guard d'obsolet (`:80-88`) |

**Verds i buits notables:**
- `bootstrap_tenant.py:61-62` — **`ItemBaseSet`, `ItemBaseMeasurement`, `CustomerPOMAlias` i
  `POMEstadisticaTenant` no són a cap `SEED_BLOCK`**: un tenant nou neix amb pertinences i regles, però
  **sense cap valor base d'item ni cap àlies de client**. 🟠 `C1-ins`.
- `export_losan_package.py:383-387` — recomptes literals **hardcodats** (`garment_pom_maps: 1748`,
  `item_base_measurements: 37`) que **PETEN en néixer la 2a instància**. **Sonda barata del radi real.** 🟠.

### G · Tests que codifiquen la llei (des del camí 1B)

#### G.1 · Els que NO peten: afirmen el contrari

| fitxer:línia | taula | tipus | què afirma | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`models_app/tests.py:52-55`** | CustomerPOMAlias → BaseMeasurement | CONTRACT-api | docstring literal: *«El cas U2/U3 del Brownie… `BaseMeasurement` és únic per (model, pom): la segona esborrava la primera **sense dir res**»* | **PETA — inverteix la llei.** El cas real citat **ÉS** el de dues instàncies | 🔴 | consolidació-catàleg |
| **`models_app/tests.py:84-93`** | CustomerPOMAlias | CONTRACT-api | *«La divergència deliberada amb `size_map_views.py:53`… el destí és `BaseMeasurement`, únic per (model,pom): dues files no hi caben»*; cas real BRW `F`/`FF` | **PETA — la raó desapareix** | 🔴 | consolidació-catàleg |
| `models_app/tests.py:189` | CustomerPOMAlias | CONTRACT-api | `_apply_many_to_one_guard`: 2 files → mateix `pom_master_id` = col·lisió | PETA | 🔴 | consolidació-catàleg |
| **`patterns/tests.py:1865`** | PatternPOM | COUNT-gate | `test_el_mateix_pom_dos_cops_a_la_mateixa_peca_rebota` → assert 400 | **PETA — inverteix la llei** | 🔴 | F2-patrons |
| `pom/tests.py:74` (+`:64`,`:92`,`:104`) | CustomerPOMAlias | CONTRACT-api | «un POM que un altre codi ja reclama» = sospitós (4 mètodes) | PETA | 🔴 | consolidació-catàleg |
| `models_app/tests.py:317` | CustomerPOMAlias | WRITE-create | 2n codi → mateix POM ⇒ `pendent_revisio=True` | PETA (legítim amb instàncies) | 🔴 | consolidació-catàleg |

#### G.2 · El patró endèmic `{s.size_label: s.valor for s in …filter(pom=…)}`

**Set fitxers, mateix nom (`_specs()` / `_taula()`), tots 🔴 `top-up-lectors`, cap peta: col·lapsen i passen
verds amb un valor arbitrari:**

`pom/test_g6_segell.py:91` · `pom/test_step_conserva_valors.py:137` · `pom/test_guarda_rang_mesura.py:115` ·
`pom/test_d2_nomes_override.py:96` · **`pom/test_g6_grading_gates.py:142` i `:179` (ni tan sols filtren per
POM: la clau és només la talla sobre tot el SizeFitting)** · `fitting/test_repas.py:128` ·
`fitting/test_graded_table_regla.py:102-169`.

#### G.3 · Comptadors durs — la sonda més honesta

`pom/test_g6_segell.py:209` (`==9`) · `:219` · `pom/test_g6_grading_gates.py:141` (`==3`) · `:178` ·
`pom/test_d2_nomes_override.py:165` (`n==5`) · `models_app/tests_sembra_grading.py:869` (el `resum` sencer) ·
`:882`, `:974`. **Es posen vermells de seguida i diuen quantes files sobren.**

#### G.4 · Escriptures de fixture que PETEN (IntegrityError)

`models_app/tests_sembra_grading.py:126` GarmentPOMMap (5 reps) · `:136` ItemBaseMeasurement (~11 reps) ·
`:895` `.get(base_set, pom)` (~8 reps) · `:1160` `.get(garment_type_item, pom)` — **ni porta `base_set`**
(~5 reps) · `fitting/tests.py:73` PieceFittingLine · `fitting/test_repas.py:69` (~30 crides) ·
`patterns/tests.py:2223` PatternPOM (3 reps) · `pom/test_d2_nomes_override.py:116` `.get(gv, pom, size_label)`.

#### G.5 · Forat de cobertura

**`fitting.POMAlert` no té CAP test a tot el repo** (`grep -rn "POMAlert" --include=test*.py` → **0 hits**).
🟠 `Onada2`.

### Accessos inversos (camí 1B) — taula completa

**Registre canònic:** `pom/seed_data/consolidate_pom_los.py:31-35` és **l'ÚNIC lloc del repo on el radi
invers sencer de `POMMaster` està enumerat**, com a strings consumits per `getattr()` a
`consolidate_pom_catalog.py:113` i `:249`:

```python
FUSIO_MOVE_RELS  = ['base_measurements', 'model_grading_rules', 'measurement_changes',
                    'model_grading_overrides', 'item_base_measurements', 'mesures_perfil',
                    'alerts', 'pattern_poms', 'estadistiques']
FUSIO_DELETE_RELS = ['graded_specs']
FUSIO_LEAVE_RELS  = ['regles_grading']
```

**11 dels 11 accessors** hi són. Qualsevol eix nou de la cadena de mesura ha de passar per aquesta llista o
la consolidació el deixa enrere en silenci. 🔴 `consolidació-catàleg`.

**⚠️ TRAMPA: `base_measurements` és una col·lisió de nom a TRES bandes**

| declaració | de → a |
|---|---|
| `pom/models.py:836` | `GarmentTypeItem` → `ItemBaseMeasurement` |
| `models_app/models.py:613` | `Model` → `BaseMeasurement` |
| `models_app/models.py:614` | `POMMaster` → `BaseMeasurement` |

A `consolidate_pom_los.py:31`, `getattr(pom, 'base_measurements')` resol a **models_app** (`:614`), no a
`pom` — correcte, perquè `ItemBaseMeasurement` viatja separat com a `'item_base_measurements'` (`:844`).
**Però `GarmentTypeItem.base_measurements` (el de `pom`) NO té CAP call site a tot el repo.**

**Taula completa d'accessors i call sites:**

| accessor | declaració | call sites (fora de `models.py`) |
|---|---|---|
| `graded_specs` | `fitting/models.py:191,193` | `patterns/views.py:714` · `fitting/staleness.py:180` · `fitting/serializers.py:32` · `consolidate_pom_los.py:34` |
| `alerts` | `fitting/models.py:137` | **només** `consolidate_pom_los.py:33` (via `getattr`) |
| `pom_alerts` | `fitting/models.py:129,135` | **cap** (0 call sites) |
| `pom_maps` | `pom/models.py:581` | `tasks/views_b.py:970` (`Count('pom_maps')`) · `tasks/serializers_b.py:153` · `seed_losan_ss27.py:77` · `load/export_losan_package.py` |
| `garment_maps` | `pom/models.py:583` | `consolidate_pom_catalog.py:88`, `:91` |
| `base_measurements` (**pom**) | `pom/models.py:836` | **cap** — v. trampa |
| `measurements` | `pom/models.py:843` | `pom/views.py:361` (`Count('measurements')`), `:363`, `:395`, `:399` |
| `item_base_measurements` | `pom/models.py:844` | `consolidate_pom_los.py:32` · `export/load_losan_package.py` |
| `base_sets` | `pom/models.py:660` | `pom/views.py:491` (payload `base_set_ambigu`) · `tests_sembra_grading.py:1201` |
| `item_base_sets` | `pom/models.py:662,667` | **cap** |
| `base_set_for_items` | `pom/models.py:672` | **cap** — 🔴 v. bug B-2 |
| `regles` | `pom/models.py:1097` | `pom/views.py:209` (`Prefetch` string), `:232` · `pom/serializers.py:282,286,320,324` · `size_map_views.py:756,1024` · `grading_utils.py:777` · `models_app/views.py:857,930,1001,1465` · `extraction_views.py:901,2657` · 6 commands |
| `regles_grading` | `pom/models.py:1098` | `consolidate_pom_los.py:35` · `consolidate_pom_catalog.py:127` |
| `mesures_perfil` | `pom/models.py:1155,1159,1160` | **només** `consolidate_pom_los.py:32` (via `getattr`) |
| `pom_aliases` | `pom/models.py:393` | `export/load_losan_package.py` |
| `client_aliases` | `pom/models.py:401` | **cap** |
| `estadistiques` | `pom/models.py:363` | **només** `consolidate_pom_los.py:33` (via `getattr`) |
| `poms` (PatternPiece) | `patterns/models.py:395` | `patterns/adapters.py:587` · `patterns/serializers.py:314` · `patterns/views.py:312` · `patterns/svg.py:119` · `aama_writer.py:128` |
| `pattern_poms` | `patterns/models.py:400` | **només** `consolidate_pom_los.py:33` (via `getattr`) |

**Falsos positius descartats (i per què):**
- **`.regles`** — 12 hits a `patterns/` (`export.py:345-346`, `adapters.py:131,152`,
  `roundtrip.py:366-371`, `grading_projection.py:145,505`, `rul_writer.py:55-56`, `rul_reader.py:190,197`,
  `tests.py`) són **`GradeTable.regles`**, un `dict[int, GradeRuleData]` del format RUL/AAMA. **FORA.**
- **`.poms`** — ~35 hits a `models_app/test_parser_excel.py`, `test_seccio_captura.py`, `chat_views.py`,
  `extraction_*.py`, `pom_vision_views.py`, `wizard_views.py`, `grading_views.py`, `size_map_views.py` són
  **llistes de dicts extrets d'un document**, no l'accessor invers. `pom/urls.py:20` és un basename. **FORA.**
- **`.measurements`** — `pom/test_guarda_rang_mesura.py:110`, `models_app/views.py:1770,1845`,
  `pom/s11_views.py:151`, `extraction_*.py`, `tech_sheet_views.py` són **claus de payload JSON**. **FORA**
  (però `s11_views.py:151` entra al cens com a CONTRACT-api per una altra raó).
- **`.alerts`** — `pom/s11_views.py:212` és una clau de resposta. **FORA.**
- **`.lines`** a `commerce/`/`backoffice/` — línies de factura/pressupost. **FORA.**

### Recompte camí 1B

**Total: 285 files.**

| tipus | n | | «amb 2 inst.» | n | | risc | n | | onada | n | 🔴 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| READ-dict | 61 | | **COL·LAPSA** | **118** | | 🔴 | 97 | | `C1-ins` | 74 | 41 |
| READ-list | 44 | | **PETA** | **41** | | 🟠 | 71 | | `top-up-lectors` | 48 | 19 |
| WRITE-create | 33 | | IGNORA-2a | 62 | | 🟡 | 41 | | `Onada2` | 46 | 14 |
| WRITE-update | 25 | | OK | 64 | | ⚪ | 76 | | `C4-ins` | 55 | 15 |
| WRITE-delete | 11 | | | | | | | | `F2-patrons` | 32 | 22 |
| COUNT-gate | 38 | | | | | | | | `consolidació-catàleg` | 38 | 11 |
| CONTRACT-api | 42 | | | | | | | | `FORA:` | 27 | — |
| CONTRACT-engine | 31 | | | | | | | | | | |

**[SOLO-CAMÍ-1] al camí 1B: 41 nodes.** Els concentra `consolidate_pom_los.py:31-35` i
`consolidate_pom_catalog.py:113,249`. Altres focus: `.regles` com a string dins `Prefetch(...)`/`Count(...)`
(`pom/views.py:209,232`), `Count('pom_maps')` (`tasks/views_b.py:970`), `Count('measurements')`
(`pom/views.py:361`), `gv.graded_specs` (4 fitxers), `piece.poms` (5 fitxers de `patterns/`),
`patterns/engine/ports.py:98-102` (`snapshot.delta()` retorna el **primer** delta que casa).

### Els sis fets que manen (camí 1B)

1. **🚨 `pom/services.py:1023-1044` `_upsert_graded_spec` és LA porta d'Onada 2.**
   `update_or_create(grading_version_id, pom_id, size_label)` — **`capa` absent del lookup tot i ser a
   l'unique des de C1**. És l'escriptor únic de tot el motor de grading. **Ja diverge de l'esquema avui;
   només el tapa la comporta.** **Retirar la comporta a C4 sense tocar aquest node és l'accident.**
   Germans: `bootstrap_tenant.py:162`, `load_losan_package.py:363` i `:379`, `models_app/views.py:3756` i
   `:3774`, `pom/views.py:508`.
2. **🚨 Set nodes INVERTEIXEN la llei — no s'adapten, es re-decideixen.** `pom/size_map_views.py:54` ·
   `models_app/extraction_views.py:1174` · `:1734` (`pom_ja_usat`) · `pom/services.py:619` ·
   `seed_losan_rules_v2.py:128` · `patterns/models.py:432` · `patterns/tests.py:1865`.
   Els casos reals dels seus docstrings (BRW `U2`/`U3`→POM `U`, `F`/`FF`→POM 389; LOS `H.11`/`H.16`)
   **són** el cas de dues instàncies.
3. **🚨 `patterns/views.py:552-557` i `tenants/federation_service.py:585-590` són forats d'ONADA 1.**
   Peten amb la segona CAPA, sense esperar la instància.
4. **El patró dominant és el dict per `pom_id`, i sempre COL·LAPSA en silenci** (118 nodes). Els onze que
   parteixen el sistema pel mig: `ibms` (`views.py:1136`,`:1145`) · `graded_by_pom` (`:1637`) · `graded`
   (`:2494`,`:2789`) · `actuals` (`:3657`) · `poms_item` (`:3660`) · `valors` (`extraction_views.py:2047`,
   `2176`) · `counts` (`:1177`) · `presos` (`:1734`) · `alias_by_pom` (`pom/nomenclatura.py:29`) ·
   `poms_per_id` (`grading_projection.py:179`) · `specmap` (`clone_model_for_qa.py:127`).
5. **El repo ja té les tres peces de mètode que la instància necessita, i estan provades.**
   (a) **Harness de dues files germanes**: `models_app/test_lectors_capa_onada1.py:84` + `comporta_alcada()`
   a `:35`. (b) **Resposta canònica a l'ambigüitat**: `base_set_ambigu` 409 amb candidats
   (`pom/views.py:468-490`, provat a `tests_sembra_grading.py:1194`) i `_alies_unics_del_customer`
   (`patterns/views.py:135-146`), que **es calla** quan no pot desambiguar. (c) **Discriminant ordinal ja
   existent**: `PatternPiece.ordinal` (`patterns/models.py:212`, nullable, provat a `patterns/tests.py:4795`).
   **Calcar-les, no inventar-ne una quarta.**
6. **`patterns` i `POMAlert` són cost zero de dades.** `patterns_patternpom` = 0 files als tres schemas;
   `fitting_pomalert` = 0; `pom_pomestadisticatenant` = 0 **i sense cap escriptor ni lector a tot el repo**
   (taula morta). El cost real de dades és `pom_garmentpommap` (1 748), `pom_gradingrule` (1 174) i
   `fitting_gradedspec` (2 061).

---
## II.5 · CAMÍ 1C — commands · signals · SQL · migracions · tests · scripts

**Abast:** el límit declarat de la diagnosi prèvia (*«el comptador ~45 és de cens per grep, pot faltar-hi
algun node, sobretot a `management/commands/`»*), cobert sencer. **117 files.**

### Resum del recens

**1. Els commands amaguen la instància en tres formes que un cens de `views.py` no veu.**
La més greu és `pom/seed_data/consolidate_pom_los.py:31-35`: una **llista de 9 strings** amb els noms dels
accessors inversos, que `consolidate_pom_catalog.py:112-119` recorre amb `getattr(prim, rel)` i mou amb
`.update(pom=dest)`. **Cap grep de `.objects` la troba, cap grep de noms de model la troba.**

**2. Hi ha un dict `{pom_id: …}` dins d'un management command** — el mateix patró que la diagnosi prèvia va
identificar com el vector real de col·lapse, i és al bloc que declarava no haver cobert:
`pom/management/commands/author_baby_pom_maps.py:146`.

**3. El signal F1 no estampa `capa` — confirmat literalment, dos punts.**
`models_app/signals.py:267-279` i `:299-310` creen `MeasurementChangeLog` amb `model=` i `pom=` i **cap
`capa=`**. Grep sobre tot `*/management/` i `*/signals.py` amb el patró `capa=` → **0 resultats a tot el
backend fora de `pom/models.py`, les migracions i els tests.**

**4. El SQL cru NO és un vector.** Els 5 punts de `connection.cursor()` en codi de producció toquen
`models_app_model` i `models_app_garmentset` — **cap taula de la cadena**. `.raw(` : **0** ocurrències a tot
el backend. `RunSQL`: **0** ocurrències a totes les migracions de totes les apps.

**5. Un test codifica el col·lapse com a comportament ESPERAT, amb assert i tot.**
`models_app/test_seccio_captura.py:156` — `test_DUES_SECCIONS_AMB_EL_MATEIX_POM_COL·LAPSEN`, amb
`assertEqual(files.count(), 1, 'la clau encara col·lapsa: si això falla, la clau ha canviat')`. Docstring
verificat literalment: *«Aquest test hi és perquè el dia que algú toqui la clau, ho vegi caure aquí i sàpiga
que era conegut.»* **Aquest test HA de caure quan entri la instància.**

**6. Dos tests més codifiquen la llei al revés i són guards de PRODUCCIÓ, no de test.**
`models_app/tests.py:52` i `:84`; `pom/tests.py:74`.

**7. Números lliures de migració: `models_app` → 0073 · `fitting` → 0020 · `pom` → 0056 · `patterns` → 0015.**
`patterns` és l'única de les quatre **sense cap migració de `capa`**.

### BLOC 1 · MANAGEMENT COMMANDS — 71/71

#### 1A · Els que toquen la cadena (34 nodes en 30 fitxers)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `pom/seed_data/consolidate_pom_los.py:31-35` | 8 taules alhora | CONTRACT-engine | llista de STRINGS d'accessors inversos, sense cap noció de clau | IGNORA-2a | 🔴 | consolidació-catàleg **[SOLO-1]** |
| `pom/management/commands/consolidate_pom_catalog.py:112-119` | totes les de `FUSIO_MOVE_RELS` | WRITE-update | `.update(pom=dest)` per fila; `IntegrityError` = «col·lisió» comptada i **deixada al prim** | PETA (i compta la petada com a normal) | 🔴 | consolidació-catàleg **[SOLO-1]** |
| `…/consolidate_pom_catalog.py:109` | CustomerPOMAlias | WRITE-update | `.filter(pom=prim).update(pom=dest)` | OK (clau és `(customer, client_code)`) | 🟡 | consolidació-catàleg |
| `…/consolidate_pom_catalog.py:121-125` | GradedSpec | WRITE-delete | `getattr(prim,'graded_specs').all().delete()` — per `pom` sencer | COL·LAPSA (mata les dues instàncies) | 🔴 | consolidació-catàleg |
| `…/consolidate_pom_catalog.py:243-254` `_fixcoll` | 8 taules | WRITE-delete | esborra les «òrfenes de col·lisió» **per accessor sencer** | COL·LAPSA | 🔴 | consolidació-catàleg |
| `…/consolidate_pom_catalog.py:212-216` | GarmentPOMMap | WRITE-create | `get_or_create(garment_type_item, pom)` | COL·LAPSA | 🟠 | consolidació-catàleg |
| `…/consolidate_pom_catalog.py:128` | POMMaster | WRITE-update | `actiu=False` per POM | OK | ⚪ | consolidació-catàleg |
| `pom/management/commands/author_baby_pom_maps.py:146` | GarmentPOMMap | READ-dict | **`{m.pom_id: m for m in GarmentPOMMap.objects.filter(garment_type_item=item)}`** | COL·LAPSA | 🔴 | consolidació-catàleg **[SOLO-1]** |
| `…/author_baby_pom_maps.py:203-213` | GarmentPOMMap | WRITE-create/delete | `create(garment_type_item, pom)` i `m.delete()` derivats del dict de dalt | IGNORA-2a | 🔴 | consolidació-catàleg |
| `pom/management/commands/load_losan_package.py:363` | GarmentPOMMap | WRITE-create | `_upsert(GarmentPOMMap, {'garment_type_item': gti, 'pom': pom})` | COL·LAPSA | 🔴 | consolidació-catàleg |
| `…/load_losan_package.py:379` | ItemBaseMeasurement | WRITE-create | `_upsert(…, {'base_set': base_set, 'pom': pom})` | COL·LAPSA | 🔴 | consolidació-catàleg |
| `…/load_losan_package.py:446` | GradingRule | WRITE-create | `_upsert(GradingRule, {'rule_set': rs, 'pom': pom})` | COL·LAPSA | 🟠 | C4-ins |
| `…/load_losan_package.py:118-125` | POMMaster | READ-list | resol POM per `pom_global__codi` / `codi_client` | IGNORA-2a | 🟡 | consolidació-catàleg |
| `…/load_losan_package.py:390-395` | ItemBaseSet | WRITE-create | `get_or_create` del base_set | OK | ⚪ | consolidació-catàleg |
| `pom/management/commands/export_losan_package.py:146-153` | 4 taules | READ-list | **`set()` de `pom_id`** unides amb `\|` → el conjunt exportat és per POM, no per instància | COL·LAPSA | 🟠 | consolidació-catàleg |
| `…/export_losan_package.py:252-262` | GarmentPOMMap · ItemBaseMeasurement | READ-list | `order_by('garment_type_item_id','pom_id')` — ordre **no determinista** amb 2 files iguals | IGNORA-2a | 🟡 | consolidació-catàleg |
| `…/export_losan_package.py:330` | GradingRule | READ-list | per `rule_set` | OK | ⚪ | C4-ins |
| `tasks/management/commands/bootstrap_tenant.py:162` | GarmentPOMMap | CONTRACT-engine | **clau natural declarada `('garment_type_item','pom')`** | COL·LAPSA | 🔴 | consolidació-catàleg **[SOLO-1]** |
| `…/bootstrap_tenant.py:163` | GradingRule | CONTRACT-engine | clau natural `('rule_set','pom')` | COL·LAPSA | 🟠 | C4-ins |
| `…/bootstrap_tenant.py:154` | POMMaster | CONTRACT-engine | clau natural `('codi_client',)` | PETA amb dos POMs del mateix codi (cas real, `seed_master_delta_catalog.py:27`) | 🟠 | consolidació-catàleg |
| `…/bootstrap_tenant.py:339-351` | totes | WRITE-create/update | `update_or_create(**lookup)` amb el lookup del mapa | COL·LAPSA | 🔴 | consolidació-catàleg |
| `models_app/management/commands/clone_model_for_qa.py:92-96` | BaseMeasurement | WRITE-create | `bm.pk=None; bm.model=clone; bm.save()` — copia fila a fila | **OK** (no passa per la clau) | ⚪ | FORA: la còpia per fila sobreviu a la clau nova |
| `…/clone_model_for_qa.py:101-102` | ModelGradingRule | WRITE-create | ídem | OK | ⚪ | FORA: mateix motiu |
| `…/clone_model_for_qa.py:154-163` | 6 taules | WRITE-delete | purga per `model=` | OK | ⚪ | FORA: la purga és per model |
| `pom/management/commands/seed_losan_grading_v3.py:187-190` | GradingRule | WRITE-create | `update_or_create(rule_set=rs, pom=pom)` | COL·LAPSA | 🟠 | C4-ins |
| `…/seed_losan_grading_v3.py:80` | GradingRule | WRITE-delete | `qs.delete()` (CASCADE des del ruleset) | OK | ⚪ | C4-ins |
| `…/seed_losan_grading_v3.py:140` | CustomerPOMAlias | READ-dict | `.filter(customer, client_code).first()` → un POM per àlies | IGNORA-2a | 🟡 | Onada2 |
| `pom/management/commands/seed_losan_rules.py:151` | GradingRule | WRITE-create | `update_or_create(rule_set, pom)` | COL·LAPSA | 🟠 | C4-ins |
| `…/seed_losan_rules.py:132` | POMMaster | READ-dict | `.filter(codi_client=code).first()` | IGNORA-2a | 🟡 | consolidació-catàleg |
| `pom/management/commands/seed_losan_rules_v2.py:155` | GradingRule | WRITE-create | `update_or_create(rule_set, pom)` — el docstring `:12` ja avisa del guard «dos àlies del MATEIX contenidor» | COL·LAPSA | 🟠 | C4-ins |
| `pom/management/commands/seed_losan_master_delta.py:179-181` | GradingRule | WRITE-create | `get_or_create(rule_set, pom)` | COL·LAPSA | 🟠 | C4-ins |
| `…/seed_losan_master_delta.py:94-97` | CustomerPOMAlias · POMMaster | READ-list | resol una **llista** de POMs per codi i itera | OK-ish | 🟡 | consolidació-catàleg |
| `pom/management/commands/seed_baby_months_grading.py:99` | GradingRule | WRITE-create | `update_or_create(rule_set, pom)` | COL·LAPSA | 🟠 | C4-ins |
| `pom/management/commands/load_map_inline.py:141-144` | GarmentPOMMap | WRITE-create | `update_or_create(garment_type_item, pom)` | COL·LAPSA | 🔴 | consolidació-catàleg |
| `pom/management/commands/validate_los_maps.py:83-100` | GarmentPOMMap | WRITE-update | `.filter(garment_type_item, pom)` → `.update(pendent_revisio=False)` en bloc | COL·LAPSA (valida les dues d'un cop) | 🟠 | consolidació-catàleg |
| `pom/management/commands/seed_measurement_layers.py:30-37,51` | MeasurementLayer | WRITE-create | **el catàleg de CAPES**: 6 slugs, `update_or_create(slug=…)` | OK | 🟡 | `C1-ins` — **si la instància vol catàleg, aquest és el precedent exacte** |
| `pom/management/commands/seed_baby_poms.py:253-262` | POMGlobal · POMMaster | WRITE-create | `update_or_create` per `codi` / `pom_global` | OK | ⚪ | consolidació-catàleg |
| `pom/management/commands/extend_pom_catalog.py:177,195` | POMGlobal · POMMaster | WRITE-create | `update_or_create` per `codi` / `pom_global` | OK | ⚪ | consolidació-catàleg |
| `pom/management/commands/seed_master_delta_catalog.py:27` | POMMaster | READ-dict | comentari literal: **«hi ha DOS POMMaster amb codi_client 'U1'»** — la instància disfressada, documentada | IGNORA-2a | 🟠 | consolidació-catàleg |
| `…/seed_master_delta_catalog.py:64-91` | POMMaster · POMGlobal · CustomerPOMAlias | WRITE-create | `get_or_create` per `codi_client` / `client_code` | PETA amb el duplicat de `:27` | 🟠 | consolidació-catàleg |
| `pom/management/commands/replace_pom_catalog.py:753,805` | POMGlobal | WRITE-delete + create | **`POMGlobal.objects.all().delete()`** + `bulk_create` sobre `public` | COL·LAPSA el catàleg sencer | 🔴 | consolidació-catàleg |
| `pom/management/commands/reconcile_tenant_poms.py:65-78` | POMMaster | WRITE-update | flags `actiu` / `pendent_revisio` per PK | OK | ⚪ | consolidació-catàleg |
| `pom/management/commands/repair_customer_aliases.py:115,146,185` | CustomerPOMAlias | WRITE-update | clau `(customer, client_code)` — **no té `pom` a la clau** | OK | 🟡 | Onada2 |
| `pom/management/commands/backfill_grading_break.py:52` | GradingRule | WRITE-update | itera totes les regles, desa la forma canònica de break | OK | ⚪ | C4-ins |
| `pom/management/commands/audit_lost_breaks.py:52` | GradingRule | READ-list | auditoria read-only per ruleset | OK | ⚪ | C4-ins |
| `pom/management/commands/fix_adult_talla_base.py:69` | GradingRule | WRITE-update | `.filter(id__in=…).update(talla_base=…)` | OK | ⚪ | C4-ins |
| `pom/management/commands/cleanup_losan_old.py:76-96` | GradingRule | WRITE-delete | CASCADE des de `GradingRuleSet` | OK | ⚪ | C4-ins |
| `pom/management/commands/delete_master_delta_seed.py:70-79` | GradingRule | WRITE-delete | CASCADE des del ruleset | OK | ⚪ | C4-ins |
| `fitting/management/commands/repair_fitting_20260710.py:78` | BaseMeasurement | READ-dict | `.filter(model_id, pom_id).first()` | IGNORA-2a | 🟡 | top-up-lectors |
| `…/repair_fitting_20260710.py:79-90` | GradedSpec | READ-dict | spec de la talla base per `pom` | IGNORA-2a | 🟡 | top-up-lectors |
| `…/repair_fitting_20260710.py:123-132` | ClientMesuraPerfil | WRITE-update | `filter(garment_type, talla, pom_id__in)` — corregeix el comptador Welford | IGNORA-2a | 🟡 | Onada2 |
| `pom/management/commands/sembra_ai_report.py:92-115` | POMMaster · CustomerPOMAlias | READ-dict | índex `norm → POM` amb **`norm_collision`** explícit; READ-ONLY avui | IGNORA-2a | 🟠 | `F2-patrons` — **la Fase 2 escriu `POMPlacement`** (`:30`, `:602`) |
| `pom/management/commands/reseed_tenant_fhort.py:80-85` | — | COUNT-gate | **guard OBSOLET que avorta sempre** (usa l'eix `garment_type` eliminat a `pom/0016`) | n/a | ⚪ | FORA: mort, avorta abans d'escriure |
| `…/reseed_tenant_fhort.py:234,276,296-303,312,381-390` | POMMaster · GarmentPOMMap · GradingRule | WRITE-delete + create | `.all().delete()` + `bulk_create(ignore_conflicts=True)` | COL·LAPSA (`ignore_conflicts` empassa la 2a) | 🟡 | FORA: inabastable pel guard `:80` — *si algú el ressuscita, torna a 🔴* |
| `pom/management/commands/set_grading_origen.py:89-95` | GradingRuleSet | WRITE-update | només `origen`; cap `pom` | OK | ⚪ | FORA: la provinença no és per POM (dins per regla d'or) |
| `models_app/management/commands/backfill_model_taxonomy.py` | — | WRITE-update | canvia `garment_type_item`, que **és l'eix de `GarmentPOMMap` i `ItemBaseSet`** | OK | ⚪ | FORA: toca l'eix, no la clau (dins amb ⚪) |
| `pom/management/commands/backfill_model_items.py` | — | WRITE-update | ídem: `garment_type_item` als models legacy | OK | ⚪ | FORA: toca l'eix, no la clau (dins amb ⚪) |
| `models_app/management/commands/normalitza_size_run.py:107` | GradedSpec | READ-dict | només un **avís de text** que els specs no es regeneren | OK | ⚪ | FORA: no escriu specs |

#### 1B · Prova de cobertura — els altres 37 fitxers

**7 són `__init__.py` buits** (`backoffice`, `commerce`, `fitting`, `patterns`, `pom`, `tasks`, `tenants` —
nota: `models_app/management/commands/` **no en té cap**, i tot i així Django el carrega perquè
`management/` sí que en té).

**No toquen la cadena (30, comprovats un per un amb el grep de les 19 classes + els 21 accessors inversos
→ 0 encerts estructurals):**

`backoffice/create_backoffice_admin.py` · `backoffice/generate_invoices.py` ·
`backoffice/provision_free_tenant.py` · `backoffice/reconcile_consumption.py` ·
`backoffice/seed_free_plan.py` · `backoffice/sync_stripe_catalog.py` ·
`commerce/reconcile_work_orders.py` · `models_app/audit_fitxers.py` ·
`models_app/flag_incomplete_models.py` *(l'únic encert era la paraula catalana «regles» a `:51`)* ·
`models_app/move_media_tenant.py` · `models_app/restaura_size_run.py` ·
`models_app/seed_losan_models.py` *(només llegeix `GradingRuleSet` a `:90`)* ·
`patterns/materialize_segments.py` *(crea `PatternSegment`, mai `PatternPOM`; 0 ocurrències de `pom`)* ·
`pom/crea_sizing_profiles.py` · `pom/rename_targets_p0b.py` *(rename de `Target`)* ·
`pom/reseed_size_definitions.py` · `pom/restructure_garment_types_v2.py` ·
`pom/seed_baby_months_profiles.py` *(només busca el ruleset per nom, `:48`)* ·
`pom/seed_commercial_size_runs.py` · `pom/seed_kids_baby_target_map.py` ·
`pom/seed_pattern_piece_roles.py` · `pom/seed_scope_nodes_proposals.py` *(`RuleSetScopeNode`, `:144`)* ·
`pom/backfill_ruleset_scope.py` *(ídem, `:40-79`)* · `pom/translate_garment_families.py` ·
`tasks/create_tenant_admin.py` · `tasks/pausa_tasques_oblidades.py` · `tasks/recompute_welford.py` ·
`tasks/retype_scaling_to_grading.py` · `tenants/assign_models_to_studio.py` ·
`tenants/instantiate_external_models.py` · `tenants/seed_tenant_link.py`.

**Recompte Bloc 1: 71 fitxers citats = 7 `__init__` + 34 nodes a la taula + 30 fora.**

### BLOC 2 · SIGNALS

Cens complet de `@receiver` a tot `backend/fhort/`: **12 receptors** en 4 fitxers, registrats per `ready()`
a `commerce/apps.py:8`, `accounts/apps.py:8`, `backoffice/apps.py:8`, `models_app/apps.py:8`.

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `models_app/signals.py:299-310` `log_measurement_change` | MeasurementChangeLog | WRITE-create | `create(model=…, pom=…, base_measurement=…)` — **sense `capa`, sense instància** | COL·LAPSA: el log de la 2a instància queda indistingible | 🔴 | `Onada2` **[SOLO-1]** |
| `models_app/signals.py:267-279` (branca `_desactivat`) | MeasurementChangeLog | WRITE-create | ídem: la **poda** també registra sense `capa` ni instància | COL·LAPSA | 🔴 | `Onada2` **[SOLO-1]** |
| `models_app/signals.py:218-234` `capture_old_measurement_value` | BaseMeasurement | READ-dict | `filter(pk=instance.pk)` — **per PK** | **OK** | ⚪ | FORA: la PK sobreviu a qualsevol clau natural |
| `models_app/signals.py:16-83` `generate_model_code` | `models_app_model` | WRITE-update | SQL cru per `customer_id/any/temporada` | OK | ⚪ | FORA: no és de la cadena |
| `models_app/signals.py:86-142` `sync_size_fitting` | SizeFitting | WRITE-create | per `model` | OK | ⚪ | FORA |
| `models_app/signals.py:145-174` `recompute_import_watchpoint` | Watchpoint | WRITE-update | per `model_id` | OK | ⚪ | FORA |
| `models_app/signals.py:177-192` `update_last_activity` | Model | WRITE-update | per `pk` | OK | ⚪ | FORA |
| `models_app/signals.py:333-348` `_snapshot_encarrec` | Model | READ-dict | per `pk` | OK | ⚪ | FORA |
| `models_app/signals.py:351-373` `sync_encarrec_a_l_estudi` | federació | WRITE-update | per `model` | OK | ⚪ | FORA |
| `accounts/signals.py:19` `post_save(User)` | UserProfile | WRITE-create | per user | OK | ⚪ | FORA |
| `commerce/signals.py:19,24,37,42` (×4) | Quote · DeliveryNote | WRITE-update | recàlcul de totals | OK | ⚪ | FORA |
| `backoffice/receivers.py:7` `model_consumption_started` | consum | WRITE-create | senyal custom, no ORM | OK | ⚪ | FORA |

**Consumidor del signal, no signal, però és el mateix forat i cap grep de `@receiver` el troba:**

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `fitting/staleness.py:116-117` | MeasurementChangeLog | READ-list | `dict.fromkeys(c.pom.codi_client for c in canvis)` — **dedup per `codi_client`** | COL·LAPSA: l'avís d'estalitud diria un sol nom per a dues instàncies | 🟠 | `top-up-lectors` **[SOLO-1]** |

**Escriptures que bypassen signals** (i que per tant no passaran per cap guard que s'hi posi):
`models_app/bulk_import_service.py:544` ho documenta explícitament (`bulk_create` bypassa signals) — i el
mateix val per als **`bulk_create` de `reseed_tenant_fhort.py:264,303,390` i `replace_pom_catalog.py:805`**
i per a tots els `.update()` de queryset. ⚪ `Onada2`.

### BLOC 3 · SQL CRU I CURSOR

`grep -rn "cursor\|\.raw(\|RunSQL\|connection\."` sobre tot `backend/fhort/`: **≈70 encerts**, dels quals la
immensa majoria són `connection.schema_name` / `connection.set_tenant()` de django-tenants.

**`.raw(` → 0 ocurrències a tot el backend. `RunSQL` → 0 ocurrències a TOTES les migracions de totes les
apps** (`grep -rln "RunSQL" */migrations/` → buit). *(Verificat independentment.)*

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `models_app/signals.py:57-72` | `models_app_model` | READ-dict | `SELECT MAX(sequencial) … WHERE customer_id/any/temporada` | OK | ⚪ | FORA: taula fora de la cadena |
| `models_app/views.py:550-557` | `models_app_model` | READ-list | `SELECT codi_intern … LIKE` | OK | ⚪ | FORA: taula fora de la cadena |
| `models_app/views.py:811-821` | `models_app_model` · `models_app_garmentset` | READ-list | `SELECT … ~ regex` | OK | ⚪ | FORA: taula fora de la cadena |
| `models_app/test_capa_comporta_c1.py:97-105` | `pg_constraint` | COUNT-gate | compara amb una **llista literal de 9 noms** (`:30-38`) | PETA si la instància afegeix comportes | 🟠 | C1-ins |
| `models_app/test_capa_comporta_c1.py:111-116` | `models_app_modelgradingrule` | COUNT-gate | assert que **NO** té ni columna `capa` ni comporta | PETA si la instància entra a `ModelGradingRule` | 🟠 | C1-ins |
| `models_app/test_lectors_capa_onada1.py:43-52` | 9 taules físiques | CONTRACT-engine | `ALTER TABLE "{schema}"."{taula}" DROP CONSTRAINT` dins savepoint — **el harness que alça les comportes** | reusable tal qual per a la instància | ⚪ | C1-ins (eina) |
| `models_app/test_lectors_capa_onada1.py:243-248` | `pg_constraint` | COUNT-gate | verifica que el savepoint ha tornat les comportes | OK | ⚪ | C1-ins |
| `planning/scheduler_service.py:80-230` | — | — | `cursor` és una **variable de temps**, no un cursor de BD | n/a | ⚪ | FORA: fals positiu del grep |

**Conclusió del Bloc 3: el SQL cru NO és un vector per a la instància.** Cap sentència de producció nomena
cap de les 13 taules físiques de la cadena. Els únics punts que sí les nomenen són **dos fitxers de test**
i **dos `.sql` de `scripts_tmp/`**.

### BLOC 4 · MIGRACIONS

#### 4A · La cadena de `capa` (10 migracions, cap `RunPython`)

| fitxer:línia | taula | tipus | què hi va fer | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `pom/migrations/0052_measurementlayer.py:23` | MeasurementLayer | WRITE-create | crea el **catàleg de capes** | precedent exacte per a un catàleg d'instància | ⚪ | C1-ins |
| `models_app/migrations/0070_capa_mesures.py:33-57` | 5 taules | CONTRACT-engine | `AddField capa` `CharField(20, db_index, default='exterior')` × 5. Docstring `:15-18`: **cap backfill**, fast-default de PG11+ | model exacte a copiar per a `instancia` | ⚪ | C1-ins |
| `fitting/migrations/0017_capa_mesures.py:28-34` | GradedSpec · PieceFittingLine | CONTRACT-engine | ídem × 2 | ídem | ⚪ | C1-ins |
| `pom/migrations/0053_capa_mesures.py:27-33` | GarmentPOMMap · ItemBaseMeasurement | CONTRACT-engine | ídem × 2 | ídem | ⚪ | C1-ins |
| `models_app/migrations/0071_capa_unicitats.py:40-61` | 4 taules | CONTRACT-engine | `unique_together` +`capa` × 3 · **`POMPlacement`: DROP `uniq_pomplacement_item_pom_view` + ADD `…_view_capa`** (`:52-61`); `AlterModelOptions` `ordering=['model','capa','ordre','pom']` (`:32-39`) | l'`ordering` haurà de decidir on va la instància | 🟡 | C1-ins |
| `fitting/migrations/0018_capa_unicitats.py:21-26` | GradedSpec · PieceFittingLine | CONTRACT-engine | `('grading_version','pom','size_label','capa')` · `('piece_fitting','pom','size_label','capa')` | ídem | ⚪ | C1-ins |
| `pom/migrations/0054_capa_unicitats.py:28-33` | GarmentPOMMap · ItemBaseMeasurement | CONTRACT-engine | `('garment_type_item','pom','capa')` · `('base_set','pom','capa')` | ídem | ⚪ | C1-ins |
| `models_app/migrations/0072_capa_comporta_c1.py:32-61` | 5 taules | COUNT-gate | 5 `CheckConstraint(Q(capa='exterior'))`. Docstring `:20`: **«C4 EL RETIRA PER MIGRACIÓ. És bastida, no arquitectura»** | la instància no té equivalent de comporta (contingut lliure) | 🟠 | C1-ins |
| `fitting/migrations/0019_capa_comporta_c1.py:25-34` | GradedSpec · PieceFittingLine | COUNT-gate | 2 comportes | ídem | 🟠 | C1-ins |
| `pom/migrations/0055_capa_comporta_c1.py:28-37` | GarmentPOMMap · ItemBaseMeasurement | COUNT-gate | 2 comportes | ídem | 🟠 | C1-ins |

**`ModelGradingRule` és EXCLOSA de les tres cadenes, i és decisió de domini escrita, no oblit:**
`models_app/0070:7-8` («la regla de graduació es comparteix entre capes — mateixos deltes»), repetit a
`0071:19-20` i pinat a `test_capa_comporta_c1.py:108-116`. **Cal decidir explícitament si la instància hi
entra o no.**

**`patterns` NO té cap migració de `capa`.** `PatternPOM` viu amb `(pattern_piece, pom_master)` a
`patterns/models.py:430-437` i sense columna de capa. **Ni tan sols té la bastida de C1.** 🔴 `C1-ins`.

#### 4B · Números lliures per a la migració d'instància (verificats)

| app | última | **lliure següent** |
|---|---|---|
| `models_app` | `0072_capa_comporta_c1` | **`0073`** |
| `fitting` | `0019_capa_comporta_c1` | **`0020`** |
| `pom` | `0055_capa_comporta_c1` | **`0056`** |
| `patterns` | `0014_alter_patternpiece_rol_origen` | **`0015`** (avui sense cap precedent de capa) |
| *(context)* `tasks` `0043` · `tenants` `0007` | | |

#### 4C · `RunPython` que han tocat DADES de la cadena (9)

| fitxer | taules | què va fer |
|---|---|---|
| `pom/0048_itembaseset_backfill.py` | ItemBaseSet · ItemBaseMeasurement | crea els base_sets i hi reapunta les mesures d'item |
| `pom/0044_p9_itembasemeasurement_provinenca.py` | ItemBaseMeasurement · BaseMeasurement | backfill de provinença |
| `pom/0042_linear_zero_to_fixed.py` | GradingRule · ModelGradingRule | LINEAR+0 → FIXED (les dues taules de regla) |
| `pom/0043_retire_gradingruleset_target_fk.py` | GradingRule | retirada de l'FK `target` |
| `pom/0030_backfill_gradingruleset_customer.py` | GradingRule | backfill del customer |
| `pom/0023_complete_pom91_numeric_size_system.py` | GradingRule | completa POM-091 |
| `pom/0031_migrate_brownie_synonyms_to_aliases.py` | CustomerPOMAlias · POMMaster | sinònims → àlies |
| `pom/0032_migrate_dotted_codi_client_to_aliases.py` | CustomerPOMAlias · POMMaster | codis amb punt → àlies |
| `pom/0034_fix_a1_remove_a2_customerpomalias.py` · `pom/0035_customerpomalias_dictionary_fields.py` | CustomerPOMAlias | correcció A1/A2 + camps de diccionari |

Sense encerts a la cadena: `models_app/0027`, `models_app/0045`, `models_app/0050`, `pom/0021`,
`patterns/0012`.

### BLOC 5 · TESTS QUE CODIFIQUEN LA LLEI ACTUAL

**91 fitxers de test a tot `backend/fhort/`; 39 toquen la cadena.**

| fitxer:línia | taula | tipus | què afirma exactament | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`models_app/test_seccio_captura.py:156,172`** | BaseMeasurement | COUNT-gate | **`assertEqual(files.count(), 1, 'la clau encara col·lapsa: si això falla, la clau ha canviat')`** + la fila que queda és la 2a (`seccio='02.- KNICKERS'`, `17.0`). Docstring: pin deliberat, cita `DIAGNOSI_MULTIPECA_DALIA §Q2` | **PETA — i ha de petar** | 🔴 | C1-ins |
| **`models_app/tests.py:52`** `test_dues_files_amb_la_mateixa_arrel_no_collapsen_sobre_un_pom` | BaseMeasurement (via matcher) | COUNT-gate | dues files U2/U3 cap al POM 'U' → **cap de les dues vincula**; docstring: *«la segona esborrava la primera sense dir res»* | PETA (el cas nou seria legítim) | 🔴 | C1-ins |
| **`models_app/tests.py:84`** `test_lalias_NO_queda_exempt_del_guard` | BaseMeasurement | COUNT-gate | F/FF, dos àlies HIGH cap al mateix POM → `many_to_one=True`, `n_many_to_one=2`, cap vincle | PETA | 🔴 | C1-ins |
| `models_app/tests.py:189` `test_el_guard_desvincula_TOTES_les_files_en_collisio` | BaseMeasurement | COUNT-gate | el guard desvincula **totes** les files en col·lisió | PETA | 🔴 | C1-ins |
| `pom/tests.py:74` `test_segon_codi_cap_al_mateix_pom_cau_a_pendent` | CustomerPOMAlias | COUNT-gate | `maybe_learn_customer_alias`: el 2n codi cap al mateix POM → `pendent_revisio=True` | PETA | 🟠 | Onada2 |
| `pom/tests.py:92` `test_un_pom_lliure_no_queda_contaminat_pel_guard` | CustomerPOMAlias | COUNT-gate | el guard mira el POM de destí, no el client | OK | 🟡 | Onada2 |
| `models_app/test_capa_comporta_c1.py:30-38,94-105` | 9 taules | COUNT-gate | **llista literal de 9 noms de comporta**; `assertEqual(trobades, set(COMPORTES))` | PETA si la instància n'hi afegeix | 🟠 | C1-ins |
| `models_app/test_capa_comporta_c1.py:108` | ModelGradingRule | COUNT-gate | SQL contra `information_schema`: `assertIsNone` — **la regla NO té `capa`** | PETA si la instància hi entra | 🟠 | C1-ins |
| `models_app/test_capa_comporta_c1.py:63,68,74` | BaseMeasurement · SizeCheckLine | COUNT-gate | `IntegrityError` en escriure `capa='folre'`, també per `update()` massiu | OK | ⚪ | C1-ins |
| `models_app/test_capa_comporta_c1.py:84` `test_exterior_entra_i_es_el_defecte` | BaseMeasurement | CONTRACT-api | `bm.capa == 'exterior'` sense passar-lo | *(la instància hauria de decidir el seu default anàleg)* | 🟡 | C1-ins |
| `models_app/test_lectors_capa_onada1.py:100` `test_c1_…tolerancies` | BaseMeasurement | READ-dict | **el harness de dues capes**: `_tolerance_map` per POM sol es quedava amb l'última llegida | reusable tal qual per a dues instàncies | ⚪ | C1-ins (patró) |
| `models_app/test_lectors_capa_onada1.py:115` `test_c5` | SizeCheckLine | READ-dict | cada línia es jutja amb la tolerància de la SEVA capa | ídem | ⚪ | C1-ins (patró) |
| `models_app/test_lectors_capa_onada1.py:155` `test_c8` | GradedSpec | READ-dict | la clau del dict de `_sembra_step_des_dels_specs` és la TALLA, no el POM | ídem | ⚪ | C1-ins (patró) |
| `models_app/test_lectors_capa_onada1.py:193` `test_c9` | MeasurementChangeLog | READ-list | un estadi de folre no arrossega valor a la fila de l'exterior | ídem | ⚪ | C1-ins (patró) |
| `models_app/test_lectors_capa_onada1.py:237` | `pg_constraint` | COUNT-gate | el savepoint retorna les comportes | OK | ⚪ | C1-ins |
| `models_app/test_base_stages_no_regressio.py:67,71,91` | MCL · BM | CONTRACT-api | **la forma EXACTA de cada fila i cada estadi** (claus de primer nivell, forma de fila, forma d'estadi) | PETA si la fila creix un camp `instancia` | 🔴 | top-up-lectors |
| `models_app/test_base_stages_no_regressio.py:99` | — | CONTRACT-api | tolerància per defecte = 0.6 | OK | ⚪ | top-up-lectors |
| `models_app/test_base_stages_no_regressio.py:105,128,143,180` | MCL | READ-list | agrupació per context+segon · carry-forward · poda capdavantera · amagar un POM | IGNORA-2a | 🟠 | top-up-lectors |
| `models_app/test_base_stages_no_regressio.py:257,263,272,280` | ModelGradingOverride | READ-list | només preses de talla base pinten columna | IGNORA-2a | 🟡 | top-up-lectors |
| `models_app/test_size_check_completa_linies.py:49,60,73,116,124` | SizeCheckLine · BM | COUNT-gate | `assertEqual(n, 1)` — **una línia per POM**; `:124` un POM desactivat no reapareix | COL·LAPSA / PETA | 🔴 | top-up-lectors |
| `models_app/tests_sembra_grading.py:144-231` (`MaterialitzarPomsTest`, 9 tests) | BaseMeasurement | WRITE-create | sembra item→model per `pom_ids`; `:162` idempotència; `:171` sobirania manual | COL·LAPSA | 🔴 | top-up-lectors |
| `models_app/tests_sembra_grading.py:450-479` (`PodaSoftTest`, 5) | BM · MCL | WRITE-update | la poda és soft i registra al log; `:474` poda repetida no re-registra | COL·LAPSA | 🔴 | top-up-lectors |
| `models_app/tests_sembra_grading.py:532-610` (`ImportSorollTest`, 8) | BaseMeasurement | WRITE-update | orfes es proposen; conservar/sobreescriure/respectar-manual | COL·LAPSA | 🔴 | top-up-lectors |
| `models_app/tests_sembra_grading.py:871,929,1039` | GarmentPOMMap · ItemBaseMeasurement | READ-list | **`{f['pom_id'] for f in …}`** — sets de `pom_id` | COL·LAPSA | 🟠 | consolidació-catàleg |
| `models_app/test_copia_model_a_model.py:105-208` (13 tests) | BaseMeasurement | WRITE-create | còpia model→model per `pom_ids`; `:157` sobirania manual; `:198` pertinença sense valor | COL·LAPSA | 🔴 | top-up-lectors |
| `models_app/test_copia_model_a_model.py:213,232` | ModelGradingRule | WRITE-create | còpia de ruleset + materialització de regles | COL·LAPSA | 🟠 | C4-ins |
| `fitting/test_repas.py:106,128,286-288` | MCL · SizeCheckLine | READ-dict | **`{r['pom_id']: r for r in rows}`** + `assertNotIn(pom_b.id, per_pom, 'un POM que ningú va mesurar no fa fila')` | COL·LAPSA | 🔴 | top-up-lectors |
| `fitting/tests.py:225` `test_grid_exposa_regim_per_pom` | PieceFittingLine | READ-dict | `next(l for l in data['lines'] if l['pom_id'] == self.pom.id)` — **el primer que trobi** | IGNORA-2a | 🟠 | top-up-lectors |
| `fitting/tests.py:187` `test_regim_update_no_duplica` | ModelGradingRule | COUNT-gate | la creació de règim no duplica la regla resident | PETA | 🟠 | C4-ins |
| `fitting/test_graded_table_regla.py:97-165` (7) | GradedSpec · GradingRule | CONTRACT-api | forma exacta del payload de la taula graduada, `increment_applied_cm` inclòs | COL·LAPSA | 🟠 | top-up-lectors |
| `pom/test_d2_nomes_override.py:105-160` (7) | MGO · GradedSpec | CONTRACT-engine | un POM només-override gradua el run sencer; el preview diu el mateix que el generador | COL·LAPSA | 🟠 | top-up-lectors |
| `pom/test_step_conserva_valors.py:132,149-221` | GradedSpec · MGO | WRITE-update | `{'pom_id':…, 'talla':…, 'valor':…}` — **el contracte del PATCH no té on posar la instància** | COL·LAPSA | 🔴 | top-up-lectors |
| `pom/test_guarda_rang_mesura.py:101,110` | BM · MGO | CONTRACT-api | body `{'pom_id','talla','valor'}` i `{'measurements': [{'pom_id','base_value_cm'}]}` | COL·LAPSA | 🔴 | top-up-lectors |
| `pom/test_g6_segell.py:114,123,176` | MGO · GradedSpec | CONTRACT-api | els 6 camins del segell, tots amb body `{'pom_id', …}` | COL·LAPSA | 🟠 | top-up-lectors |
| `pom/test_g6_grading_gates.py:135,147,154,168` | ModelGradingRule | CONTRACT-engine | un model amb regles residents gradua sense ruleset; preview == generador | COL·LAPSA | 🟠 | C4-ins |
| `models_app/test_g1_graduacio.py:163` | BaseMeasurement | CONTRACT-api | `{'measurements': [{'pom_id','base_value_cm'}]}` | COL·LAPSA | 🔴 | top-up-lectors |
| `models_app/test_d1_proposta_promocio.py:177` | MGR · GradingRule | READ-dict | **`{i['pom_id']: i['estat'] for i in r.data['items']}`** | COL·LAPSA | 🟠 | C4-ins |
| `models_app/test_d1_proposta_promocio.py:157` | ModelGradingOverride | WRITE-delete | promocionar **esborra els overrides** perquè el model hereti | COL·LAPSA | 🟠 | C4-ins |
| `models_app/test_beach_columnes_descartades.py:34,52-90` | BaseMeasurement | CONTRACT-api | **`{pom_id: {etiqueta: cm}}`** + `confirmed_pom_ids=[…]` | COL·LAPSA | 🔴 | top-up-lectors |
| `models_app/test_import_poms_duplicats.py:84-175` (6) | POMMaster | COUNT-gate | **dos `POMMaster` amb el mateix `codi_client` → 409 amb candidats**; `:96` atomicitat; `:130` reporta TOTS els codis | *el 409 és exactament el cas que la instància vol legitimar* | 🔴 | C1-ins |
| `models_app/test_import_poms_resolucions.py:66-184` (10) | POMMaster · BM | WRITE-create | resolució a la fila; **`:129` `test_dues_files_al_mateix_pom_master_es_error_de_fila`** | PETA | 🔴 | C1-ins |
| `models_app/test_parser_excel.py:90,140` | — | READ-dict | `assertEqual(len(self.poms), 26)` i `{p['codi_fitxa']: p['values'].get('S')}` — **dict per codi de fitxa** | COL·LAPSA al test | 🟡 | C1-ins |
| `patterns/tests.py:2223,2301,2626` | PatternPOM | WRITE-create | tres bancs que ancoren POMs a peces; `:2299` `test_un_pom_ancorat_sense_spec_es_diu_i_no_es_mou` fa **`next(p for p in sp.poms if p.pom_code == 'SLEEVE')`** | IGNORA-2a | 🟠 | F2-patrons |
| `patterns/tests.py:2213-2219` | GradedSpec | WRITE-create | banc: un `GradedSpec` per `(pom, talla)` | COL·LAPSA | 🟠 | F2-patrons |
| `patterns/tests.py:4811` | PatternPOM | CONTRACT-engine | *«Mateixa llei que `PatternPOM.pom_master`»* — la llei del PROTECT, citada com a precedent | OK | ⚪ | F2-patrons |
| `pom/tests.py:224-268` `SembraCapesDeMesuraTest` (4) | MeasurementLayer | WRITE-create | la sembra de capes no duplica ni esborra; `:259` **exterior és la primera i el defecte** | *precedent exacte si la instància vol catàleg* | ⚪ | C1-ins |
| `fitting/test_g6_estalitud.py:57-190` | MCL · GradedSpec | READ-list | l'estalitud i els `poms_afectats` (el dedup de `staleness.py:116`) | COL·LAPSA el nom | 🟠 | top-up-lectors |
| `pom/test_qa_s24_meredith.py:125` | GradedSpec | READ-dict | `{'pom_id': x['pom_id'], 'codi': x['pom_codi_client']}` | COL·LAPSA | 🟡 | top-up-lectors |
| `models_app/test_set1_creacio.py:93,118` | ModelGradingRule | CONTRACT-engine | un GTI compost genera dues peces amb item distint — **la sortida «barata» del multi-peça** | OK | 🟡 | FORA: la instància és dins d'UNA peça |
| `pom/test_p7_target_fk.py:48-87` · `pom/test_p4_scope_proposals.py` · `pom/test_p0b_rename_targets.py` · `pom/test_arestes_tea205.py` · `pom/test_espai_de_sistema.py` · `pom/test_propaga.py` · `models_app/tests_model_filters.py` · `tasks/tests_bootstrap_additive.py` | GradingRuleSet · Target | — | només toquen l'eix de contenidor/target, mai `(…, pom)` | OK | ⚪ | FORA: eix de contenidor, no de POM |

**52 fitxers de test no toquen la cadena** (0 encerts): tot `tenants/tests_*` (13) · `commerce/test_*` (4) ·
`accounts/tests.py` · `backoffice/tests_actor_schema.py` · `planning/tests.py` · `tasks/*` (9) ·
`models_app/test_ftt_*` (5) · `models_app/test_upload_*` (2) · `models_app/tests_ftt.py` ·
`models_app/tests_bulk_import.py` · `models_app/tests_garment_counts.py` ·
`models_app/tests_origen_extern.py` · `models_app/test_porta_run_*` (2) ·
`models_app/test_ia_routing_i_cost.py` · `models_app/test_gate_mesures_pom_task.py` ·
`models_app/test_error_logging.py` · `fitting/test_universal_sf.py` · `fitting/test_foto_embut.py` ·
`pom/test_size_map_import.py` · `pom/test_run_del_*` (2) · `pom/test_d3_*` (2).

### BLOC 6 · `backend/scripts_tmp/` — 17 fitxers, fora de git

Confirmat `?? backend/scripts_tmp/` a `git status`. **No té `.gitignore` propi ni README d'inventari.**

#### 6A · Eines de C1 / Onada 1 — REUSABLES tal qual per a la instància (6)

| fitxer | què fa | com es reusa per a la instància |
|---|---|---|
| `c1_audit_counts.sql` | `DO $$` que recorre **`public`+`fhort`+`los`** × **10 taules físiques** (les 9 + `models_app_modelgradingrule` marcada «EXCLOSA … ha de sortir sense capa») i escup files / té_capa / `capa='exterior'`. Detecta la columna via `information_schema` → **funciona abans i després de la migració** | canviar `capa` per `instancia` a les 3 línies i és el cens T2/T5 d'instància, schema per schema |
| `c1_audit_constraints.sql` | 4 blocs contra `pg_constraint`: comportes `%_capa_gate_c1` (**«han de ser 9 per schema de tenant, 2 a public»**) · unicitats amb `capa` a 7 taules · el `UniqueConstraint` amb nom de `POMPlacement` · el catàleg `pom_measurementlayer` als 3 schemes. Comentari clau: *«Django-tenants pot donar un OK enganyós: això llegeix el catàleg de Postgres directament»* | **l'única eina que verifica de debò que una migració ha arribat als 3 schemas** |
| `c1_fumeig_base_stages.py` | crida `base_stages_view` real contra `fhort` per als 3 models amb més `MeasurementChangeLog` i escup JSON canonicalitzat (`sort_keys`, `indent=2`). **T0 i T5 han de ser byte-idèntics** | el termòmetre de «cap canvi de contingut» |
| `c1_base_stages_T0prima_2026-07-31.json.txt` + `.README` | **la línia base T0' viva**: md5 **`6e3a980f624215f121ef6abe7ed7a8ae`**, models 467 / 548 / 182 | és la referència; **no s'ha de regenerar sense entendre-ho** |
| `c1_fumeig_convivencia.py` | 4 superfícies nascudes DESPRÉS del revert de C1: **A** fitxa (`FttDocumentDetailView`) · **B** bateig (`base_measurement_noms_view` PATCH) · **C** graduació (`grading_status_view` + `GradedSpecTableView`) · **D** repàs (`FittingRepasView`). **B escriu dins un `atomic()` que es desfà sempre** | el patró exacte per verificar que `BaseMeasurement.save()` sap posar una columna nova NOT NULL sense default de columna |
| `onada1_dump_superficies.py` | **una superfície per commit de l'Onada 1**: `GradedSpecTableView`, `FittingRepasView`, `PieceFittingGridSerializer`, `item_fitxer_pom_placements_view`, `SizeCheckGridSerializer`, `measurements_table_view`, `fitting_vs_spec_view`, `base_measurements_with_units_view`, `graded_specs_with_units_view`. Sortida byte-idèntica entre arbres | **és el cens de lectors EXECUTABLE** — cobreix `POMPlacement`, `PieceFittingLine`, `SizeCheckLine`, `GradedSpec` i `BaseMeasurement` d'un sol cop. ⚠️ `measurements_table_view` hi és, i és el node del 🚩 «ordre no determinista» de C7 |

#### 6B · Toquen la cadena però són d'una altra feina (5)

`dump_regles_v3.py` (bolcat de `GradingRule` v3) · `extract_grading_catalog.py` (catàleg de grading) ·
`golden_163_snapshot.py` (petja del model 163) · `dryrun_promocio.py` (D1) ·
`dataop_trams_zombis.py` (trams, `patterns`).

#### 6C · No toquen la cadena (3+1)

`diag_t3b.py` · `diag_t3c.py` · `diag_t3_t4bis.py` (diagnòstics de trams/patrons del 31/07) ·
`g1_probe_proposta.py` (proposta G1).

### Recompte camí 1C

| bloc | univers | toquen la cadena | 🔴 | 🟠 | 🟡 | ⚪ |
|---|---|---|---|---|---|---|
| 1 · commands | 71 fitxers (7 `__init__` + 64 reals) | **34 nodes en 30 fitxers** | 8 | 12 | 8 | 6 |
| 2 · signals | 12 `@receiver` + 1 consumidor | **3 nodes** | 2 | 1 | 0 | 0 |
| 3 · SQL cru | ~70 encerts de grep; 5 `cursor` de producció, 0 `.raw(`, 0 `RunSQL` | **4 nodes** (tots de test/eina) | 0 | 2 | 0 | 2 |
| 4 · migracions | 10 de `capa` + 9 `RunPython` de dades | **20 nodes** | 1 | 4 | 1 | 14 |
| 5 · tests | 91 fitxers; 39 toquen la cadena | **45 nodes en 33 fitxers** | 15 | 17 | 6 | 7 |
| 6 · `scripts_tmp` | 17 fitxers | **11** (6 reusables) | 0 | 0 | 0 | 11 |
| **TOTAL** | | **117 nodes** | **26** | **36** | **15** | **40** |

**Per onada:**

| onada | nodes | detall |
|---|---|---|
| `C1-ins` | **28** | les 10 migracions de capa + els 5 pins de comporta + els 7 tests de llei + el catàleg `MeasurementLayer` (model+sembra+tests) + `PatternPOM` sense bastida |
| `top-up-lectors` | **24** | 21 tests de contracte/lector + `staleness.py:116` + `repair_fitting_20260710.py:78,79` |
| `consolidació-catàleg` | **26** | `consolidate_pom_catalog` (6) · `author_baby_pom_maps` (2) · `load_losan_package` (4) · `export_losan_package` (3) · `bootstrap_tenant` (4) · `load_map_inline` · `validate_los_maps` · `replace_pom_catalog` · `seed_master_delta_catalog` (2) · `seed_baby_poms` · `extend_pom_catalog` · `reconcile_tenant_poms` |
| `C4-ins` | **17** | tot el que passa per `(rule_set, pom)` i `(model, pom)` de regla: 8 seeds de `GradingRule` + 5 backfills/deletes + 4 tests de regla resident |
| `Onada2` | **8** | el signal F1 ×2, `bulk_create` bypass, `CustomerPOMAlias` (`repair_customer_aliases`, `seed_losan_grading_v3:140`, `pom/tests.py:74,92`), `ClientMesuraPerfil` |
| `F2-patrons` | **5** | `sembra_ai_report` (Fase 2 escriu `POMPlacement`) + 4 nodes de `patterns` |
| `FORA: <motiu>` | **9** | 3 SQL crus de `models_app_model`/`garmentset`, `reseed_tenant_fhort` (guard mort), `clone_model_for_qa` ×3 (còpia per fila), `normalitza_size_run`, `test_set1_creacio` |

**[SOLO-CAMÍ-1] al camí 1C: 8 nodes.**
`pom/seed_data/consolidate_pom_los.py:31-35` · `consolidate_pom_catalog.py:112-119` (`getattr(prim, rel)`) ·
`author_baby_pom_maps.py:146` (dict per `pom_id`) · `bootstrap_tenant.py:162` (clau natural declarada) ·
`models_app/signals.py:267-279` i `:299-310` (`create()` dins d'un `@receiver` genèric sense `sender=`) ·
`fitting/staleness.py:116-117` (`dict.fromkeys` per `codi_client`) ·
`patterns/engine/ports.py:98-102` (`snapshot.delta()` retorna el **primer** delta que casa).

**Bonus del Bloc 5** — tres punts de `patterns/engine/` que no són ORM i que col·lapsen per construcció:
`grading_projection.py:179` `poms_per_id = {p.pom_id: p for p in poms}` 🔴 ·
`:181` `codis_spec = {d.pom_id: d.pom_code …}` 🟠 ·
`:509` `lectures = {p.pom_code: p …}` i `:564-566` `_valors_dels_poms` → `dict[str,float]` per
`pom_code` 🔴. Onada `F2-patrons`.

---
## II.6 · CAMÍ 2A — contractes · urls · OpenAPI · serializers

**63 files.** Recorregut sencer dels 12 `urls.py` + OpenAPI real + els 19 serializers.

### Estat de partida verificat a l'esquema

**Porten columna `capa`** (el que C1 ja va posar): `BaseMeasurement` (`models_app/models.py:710`, uk `:725`) ·
`MeasurementChangeLog` (`:804`, **sense uk**) · `ModelGradingOverride` (`:868`, uk `:878`) ·
`SizeCheckLine` (`:1153`, uk `:1164`) · `POMPlacement` (`:1323`, uk `:1336`) ·
`GradedSpec` (`fitting/models.py:210`, uk `:220`) · `PieceFittingLine` (`:389`, uk `:400`) ·
`GarmentPOMMap` (`pom/models.py:600`, uk `:612`) · `ItemBaseMeasurement` (`:882`, uk `:898`).

**NO en porten:** `ModelGradingRule` (uk `('model','pom')`, `models_app/models.py:960` — decisió de domini) ·
`GradingRule` (uk `('rule_set','pom')`, `pom/models.py:1119`) · `POMAlert` (cap uk) · `SizeCheck` ·
`PatternPOM` (uk `('pattern_piece','pom_master')`, `patterns/models.py:432`) · `CustomerPOMAlias` ·
`ClientMesuraPerfil` (uk `('codi_client','garment_type','pom','talla')`, `pom/models.py:1171`).

### BLOC A · Prova de cobertura dels 12 `urls.py`

#### A.1 · `backend/fhort/fhort/urls.py` (arrel de TENANT, 58 línies)

| ruta | vista | toca cadena |
|---|---|---|
| `admin/`, `api/token/`, `api/token/refresh/`, `api/token/verify/`, `api/auth/central/`, `api/auth/central/tria/`, `api/auth/bescanvi/`, `api/docs/`, `api/redoc/` (9 rutes) | admin · SimpleJWT · AuthCentral · AuthBescanvi · Spectacular | **NO** |
| `api/schema/` `:41` | `SpectacularAPIView` | **SÍ (meta)** — publica la forma de tots els payloads; canvia sol quan canviïn els serializers |
| `api/v1/` × 9 includes `:46-57` | accounts · models_app · pom · fitting · tasks · planning · commerce · patterns · tenants | (detall sota) |

#### A.2 · `backend/fhort/urls_public.py` (schema PUBLIC, 12 rutes)

`admin/`, `api/token/{,refresh,verify}/`, `api/discovery/`, `api/auth/central/{,tria}/`, `api/schema/`,
`api/docs/`, `api/redoc/`, `api/backoffice/v1/…` → **totes NO**. Cap taula de la cadena viu a `public`;
`backoffice/*` (tenants, plans, serveis, contractes, perfils-sembra, facturació ×6, legal ×5, pricing ×3,
auth ×2, health) no en toca cap (grep buit sobre `backoffice/`).

#### A.3 · `accounts/urls.py` (5 + router)

`me/`, `me/change-password/`, `legal/accept/`, `password-reset/validate/`, `password-reset/confirm/`,
`users/`, `users/{id}/`, `users/{id}/reset-link/`, `users/bulk/` → **totes NO**.

#### A.4 · `tenants/urls.py` (2 routers)

| ruta | vista | toca |
|---|---|---|
| `recursos/`, `recursos/{id}/{aturar,reactivar,revocar}/` | `RecursViewSet` | **NO** |
| `encarrecs/`, `encarrecs/enviar/`, `encarrecs/traspassar/` | `EncarrecViewSet` → `federation_service` | **SÍ** — `federation_service.py:591-618` i `:689-742` |

#### A.5 · `patterns/urls.py` (7 routers + accions)

| ruta | toca |
|---|---|
| `patterns/pattern-poms/`, `{id}/`, `bulk-delete/` | **SÍ** — `PatternPOM` |
| `patterns/pattern-files/{id}/model-poms/` (`views.py:519`) | **SÍ** — `BaseMeasurement` + `PatternPOM` + `CustomerPOMAlias` |
| `patterns/pattern-files/{id}/grading-versions/` (`:686`) | **SÍ** — `GradingVersion` + `GradedSpec` |
| `patterns/pattern-files/{id}/{export,export-preview,export-rul,download-rul,download-rul-signed}/` | **SÍ** — `GradedSpec` via `adapters.py:464` + `grading_projection.py` |
| `patterns/pattern-files/` `{id}/` `download/` `download-links/` `download-signed/` `geometry/` `identificar/` `identitat/` `render.svg/`, `piece-roles/{,id}`, `pattern-segments/{,id,bulk-delete}`, `sew-relations/` ×9, `sew-proposal-rejections/{,id}`, `sew-tolerance-acceptances/` (**25 rutes**) | **NO** |

#### A.6 · `planning/urls.py` (13 rutes)

`company-calendar/`, `users/{id}/jornada/`, `plan/{compute,preview,apply,snapshots,current,reorder,eligible-technicians,eligible-attendees,assign-batch,gantt}/`,
`calendar/events/`, `absencies/{,id}` → **totes NO** (grep de taules de cadena sobre `planning/` = buit).

#### A.7 · `commerce/urls.py` (15 routers ≈ 40 rutes)

`units`, `products`, `recipe-lines`, `product-suppliers`, `product-components`, `price-exceptions`,
`payment-terms`, `quotes`(+send/pdf/convert), `quote-lines`, `quote-line-intents`(+bulk), `orders`(+pdf),
`order-lines`(+allocation/assign-model/assign-models), `work-orders`(+close/review/reattach/unassign/orphaned),
`expenses`, `delivery-notes`(+generate/issue/pdf/…), `delivery-note-lines` → **totes NO** (grep buit).

#### A.8 · `backoffice/urls.py` — **totes NO** (v. A.2)

#### A.9 · `fitting/urls.py`

| ruta | vista | toca |
|---|---|---|
| `size-fittings/`, `{id}/` | `SizeFittingViewSet` | **SÍ** — SizeFitting (+`n_graded_specs`) |
| `grading-versions/`, `{id}/`, `{id}/approve/` | `GradingVersionViewSet` | **SÍ** |
| `pom-alerts/`, `{id}/` | `POMAlertViewSet` | **SÍ** — filtra per `pom` |
| `fitting-sessions/{id}/create-piece/` | `create_piece_fitting` | **SÍ** — clona GradedSpec → PieceFittingLine |
| `fitting-sessions/group/{uuid}/add-model/` | `add_model_to_group` → create_piece | **SÍ** (indirecte) |
| `piece-fittings/`, `{id}/`, `{id}/close/`, `{id}/discard/`, `{id}/set-gate/` | `PieceFittingViewSet` | **SÍ** |
| `piece-fitting-lines/{id}/`, `{id}/propagar/` | `PieceFittingLineViewSet` | **SÍ** |
| `fitting/{sf_id}/graded-table/` | `GradedSpecTableView` | **SÍ** |
| `fitting/model/{model_id}/repas/` | `FittingRepasView` | **SÍ** |
| `fitting-sessions/` `{id}/` `{id}/advance-phase/` `{id}/can-advance/` `{id}/discard/` `{id}/open/` `{id}/seal/` `schedule/` `schedule-bulk/` `schedule-now/`, `group/{uuid}/{,reschedule,attendees,remove-model/{id}}`, `fitting-photos/{,id}` (**17 rutes**) | | **NO** |

#### A.10 · `pom/urls.py`

| ruta | toca |
|---|---|
| `poms/suggerits/`, `poms/cerca/`, `poms/crear-tenant/`, `poms/{pom_id}/nomenclatura/` | **SÍ (catàleg)** |
| `size-map/{lookups,match,preview,grading-preview,grading-preview-file,create,systems}/` | **SÍ** |
| `pom/customers/{id}/dictionary/{template,preview,commit}/` | **SÍ** — CustomerPOMAlias |
| `poms/`, `{id}/` | **SÍ** — POMMaster |
| `pom-categories/`, `size-systems/`, `size-definitions/`, `garment-groups/`, `garment-types/` (10 rutes) | **NO** |
| `grading-rule-sets/{,id}`, `grading-rules/{,id}` | **SÍ** |
| `garment-pom-maps/{,id}` | **SÍ** |
| `item-base-measurements/{,id,upsert}` | **SÍ** |
| `item-base-sets/{,id}` | **SÍ** |
| `customer-pom-aliases/{,id}` | **SÍ** |

#### A.11 · `models_app/urls.py` (65 rutes)

**SÍ**: `item-fitxers/{item_id}/pom-placements/` · `models/{id}/{poms-suggerits,materialitzar-poms,copiar-de/{src},proposar-cotes,gravar-pom,tancar-taula,taula-mesures,set-measurements,reorder-measurements,analisi-ia,xat-mesures,generar-grading,escalat/ajustar-talla,grading-status,base-measurements/reorder,base-stages,promoure-a-item,dashboard,timeline,delete,promocionar-poms,aprovar-design-freeze,guardar-talla-base,base-measurements}/` ·
`base-measurements/{bm_id}/noms/` · `models/{id}/pom/{pom_id}/{regim,desactivar}/` ·
`item-base-sets/{id}/acte-canonic/` · `registre-activitat/` ·
`import-sessions/{cribratge,{token}/{talles,extraccio,poms,grading-preview,mesures,library-prefill,confirmar}}/` ·
`models/{extract-sheet,create-from-sheet}/` · `base-measurements/` + `{id}/` (router) ·
`size-checks/`+`{id}/`+`{id}/resolve/`+`open/` · `size-check-lines/{id}/`.

**NO**: `models/next-ref/`, `models/create-wizard/`¹, `models/{id}/update-step2/`¹, `upload-fitxer/`,
`update-fabric/`, `albara/`, `models/iso-shrinkage/`, `import-sessions/{token}/teixit/`,
`models/{chat-extraccio,iniciar-chat-extraccio}/`, `bulk-import/` ×5², `customers/{id}/tech-sheet-template/{,update}/`,
`ftt-documents/…` ×7 + `models/{id}/ftt-document/`, `models/`+`{id}/`+`fase-counts/`+`garment-counts/`+`assignar-recurs/`,
`model-fitxers/` ×6, `item-fitxers/` ×6, `watchpoints/` ×4, `document-templates/` ×2 (**≈ 45 rutes**).

¹ `create-wizard`/`update-step2` materialitzen `ModelGradingRule` des del ruleset → **⚪ SÍ-marginal**, inclòs
per la regla d'or. ² `bulk_import_service.py:536` crea `SizeFitting` en bloc → **⚪ SÍ-marginal**, inclòs.

#### A.12 · `tasks/urls.py`

**NO** (pròpies de tasks/planificació): `timers/` ×4, `task-types/` ×2, `model-task-items/` ×6,
`suppliers/` ×2, `productions/` ×3, `customers/` ×5, `garment-type-items/` ×3, `task-time-estimates/` ×2,
`models/{id}/{define-tasks,task-log,open-task,assign,unassign,gate,regress,request-production}/`,
`gates/{bulk,ready}/`, `time-analysis/` ×5 (**≈ 40 rutes**).

**SÍ (vistes de `pom/` muntades aquí — el punt cec típic d'un cens per app):**
`size-fittings/{sf_id}/taula-mesures/` (s3) · `sizing-profiles/{,id,id/clonar,id/versions,id/restaurar,id/export/csv}` ·
`grading-rule-sets/{id}/regles/{,pom_codi,pom_codi/editar,historial,export/csv}` · `tenant-config/` ·
`pom-global/cerca/` · `poms/{pom_id}/htm/` · `models/{id}/base-measurements-units/` ·
`size-fittings/{sf_id}/graded-specs-units/` · `fittings/peca/{pf_id}/{export/csv,vs-spec}/` ·
`onboarding/{status,setup-from-excel,config}/` · `alerts/{summary,{id}/resoldre}/` ·
`models/{id}/{alerts,check-tolerances}/`.
**NO** de `pom/` muntades aquí: `targets/`, `construction-types/`, `fit-types/`.

> **Total 364 paths d'OpenAPI · ~186 classificats NO en blocs · ~178 tocats a la taula o al seu grup.**

### BLOC B · OpenAPI — camps de payload nascuts d'aquestes taules

L'esquema confirma que **cap** dels camps següents té avui on posar la instància. Els crítics
(**dict indexat per `pom_id`**) van en **negreta**.

| endpoint | camp | forma |
|---|---|---|
| `GET /models/{id}/taula-mesures/` | `rows[].{id,pom_id,pom_code,nom_fitxa,nom_canonic_model,nom_traduit_model,base_value_cm,is_key,origen,notes,graded,logica,increment_base,increment_break,talla_break_label}` | llista |
| ” | `rows[].graded` | dict `{size_label: valor}` (per fila) |
| ” | **`deltes`** | **dict `{str(pom_id): float\|null}`** |
| `POST /models/{id}/set-measurements/` | `measurements[].{pom_id,base_value_cm,notes,nom_fitxa}` · **`keep_pom_ids`** | llista · **llista de `pom_id` que ÉS la clau de supervivència** |
| `POST /models/{id}/gravar-pom/` | `measurements[].{pom_id,…}` · `rules[].{pom_id,logica,increment_base,increment_break,talla_break_label}` · `keep_pom_ids` | llistes indexades per pom_id |
| `GET /fitting/{sf_id}/graded-table/` | `rows[].{pom_id,codi,abbreviation,nom_en,nom_ca,categoria,unitat,ref,seccio,nom_canonic_model,nom_traduit_model,increment_base,talla_break_label,logica}`, `rows[].valors`, `rows[].deltas` | llista + dicts per talla |
| `GET /size-fittings/{sf_id}/taula-mesures/` | **`cells`** | **dict `{str(pom_id): {talla: {value,type,increment}}}`** |
| `GET /size-fittings/{sf_id}/graded-specs-units/` | **`results`** ← `pom_dict` | **dict per `pom_id`** aplanat a llista |
| `GET /fitting/model/{id}/repas/` | `rows[].{pom_id,codi,pom_code,nom_en,nom_local,nom_canonic_model,nom_traduit_model,nom_fitxa,bm_id,is_key,valors,ultim_comentari}` | llista; **`files` intern és dict per `pom_id`** |
| `GET /models/{id}/base-stages/` | `rows[].{pom_id,pom_code,nom_fitxa,…,base_measurement_id,takes}`, `stages[]` | llista; **clau interna JA composta `(pom_id, capa)`** |
| `GET /models/{id}/base-measurements/` | `results[].{id,pom_id,regla_model,codi_client,…,client_alias}` | llista; **`alias_by_pom`/`regla_by_pom` dicts per `pom_id`** |
| `GET /models/{id}/base-measurements-units/` | `results[].pom_id` | llista (filtrada `capa=exterior`) |
| `GET /piece-fittings/{id}/` | `lines[].{id,pom_id,codi,nom,nom_en,nom_local,nom_fitxa,**bm_id**,is_key,size_label,valor_teoric,valor_real,nota,evolucio,logica,…}` | llista; `spec_map` clau `(gv,pom,size)` |
| `GET /size-checks/{id}/` | `lines[].{id,pom_id,codi,codi_fitxa,nom,nom_en,is_key,valor_teoric,valor_real,decisio,nota,tol_minus,tol_plus,fora_tolerancia,logica,…}` | llista; `bm_map` clau `(pom,capa)` |
| `GET/POST /item-fitxers/{item_id}/pom-placements/` | `placements[].{pom_id,**bm_id**,codi,x1..y2,label_dx,label_dy,source_kind,derivat}`, `no_al_model[].pom_id`; body `{pom_id,x1..y2,view_slot,source_kind}` | **dicts `exacte`/`germana`/`merged` per `pom_id`** |
| `POST /models/{id}/escalat/ajustar-talla/` | body `{pom_id,talla,valor}`; resposta `linies[].id = "{pom_id}:{talla}"` | escalar; **id sintètic sense instància** |
| `POST /models/{id}/set-size-override/` (jubilada, viva) | body `{pom_id,size_label,valor}` | escalar |
| `POST /models/{id}/materialitzar-poms/` | body `pom_ids[]`; resposta `pom_ids_desconeguts[]` | llista de pom_id |
| `POST /models/{dst}/copiar-de/{src}/` | body `pom_ids[]` + 4 flags | llista de pom_id |
| `POST /models/{id}/promoure-a-item/` | `forats[]`, `divergents[]`, `iguals[]`, `sobrarien[]`, `ampliaria_item[]` (tots `{pom_id,codi,nom,valor_model,valor_item,origen_item}`), `resum` | llistes; **`actuals` dict per `pom_id`** |
| `POST /item-base-sets/{id}/acte-canonic/` | body `{pom,base_value_cm,tol_minus,tol_plus,confirm}` | escalar |
| `POST /item-base-measurements/upsert/` | body `{garment_type_item,pom,base_set,base_value_cm,tol_minus,tol_plus,nom_fitxa}` | escalar (clau `(base_set,pom)`) |
| `PATCH /import-sessions/{token}/mesures/` | `mesures[].{pom_master_id,talla_label,valor}` | llista |
| `POST /import-sessions/{token}/confirmar/` | intern **`valors = {pom_id: {talla: valor}}`**; resposta `manuals[].pom_id`, `orfes[].pom_id` | **dict per pom_id** |
| `PATCH /import-sessions/{token}/poms/` | `poms_extrets[].{pom_master_id,codi_fitxa,descripcio,seccio,actiu,many_to_one,weak_suggestion}` | llista |
| `POST /models/{id}/check-tolerances/` | body `measurements[].{pom_id,value_cm}` | llista; **`base_map` dict per `pom_id`** |
| `POST /size-map/create/` | body `grading[].{pom_id,codi,logica,…}`; error `collisions[].{pom_id,codis_document}` | **guard `by_pom` dict** |
| `PATCH /grading-rule-sets/{id}/regles/{pom_codi}/`(+`/editar/`) | `pom_codi` **al PATH** | identitat del POM a la URL |
| `POST /models/{id}/pom/{pom_id}/regim/` · `/desactivar/` | `pom_id` **al PATH** | identitat del POM a la URL |
| `GET /poms/{pom_id}/htm/` | `pom_id` al PATH | — |
| `GET /models/{id}/dashboard/` · `/alerts/` · `/alerts/summary/` | `alertes[].{pom_codi,…}` | llista (POMAlert sense capa) |
| `GET /models/{id}/timeline/` · `/registre-activitat/` | `{pom_id,pom_codi}` | llista (MeasurementChangeLog) |
| `GET /patterns/pattern-files/{id}/model-poms/` | `files[].{base_measurement,pom_master,codi_client,nom_fitxa,…}` | llista; **`ancorats` dict per `pom_master_id`**, **`_alies_unics` dict per `pom_id`** |
| `POST /models/create-from-sheet/` | body `overrides.pom_mappings` | **dict `{client_code: pom_code}`** |
| `GET /base-measurements/` | filtres `?model&pom&is_active&origen` — **cap `capa`** | — |
| `GET /garment-pom-maps/`, `/item-base-measurements/` | camps exposats **sense `capa`** | — |

### BLOC C · Els 19 serializers que exposen la cadena

| serializer | fitxer:línia | camps exposats | escrivibles |
|---|---|---|---|
| `BaseMeasurementSerializer` | `models_app/serializers.py:389-412` | `id, model, pom, pom_code*, pom_name_en*, pom_name_cat*, pom_abbreviation*, pom_is_key*, pom_category*, pom_codi_client*, pom_nom_client*, base_value_cm, is_active, notes, nom_fitxa, origen, updated_at` | **`model, pom, base_value_cm, is_active, notes, nom_fitxa, origen`**. `*`=read-only. **`capa` NO hi és → ni es llegeix ni s'escriu; `instancia` tampoc hi cabria** |
| `SizeCheckLineSerializer` | `models_app/serializers_size_check.py:14-20` | `id, size_check, pom, valor_teoric, valor_real, decisio, nota` | `valor_real, decisio, nota`. **sense `capa`** |
| `SizeCheckSummarySerializer` | `:23-37` | `id, model, model_codi, estat, talla_base_label, missatge_fabricant, resolt_per_nom, resolt_at, created_at, n_linies` | cap (read) |
| `SizeCheckGridSerializer` | `:40-141` | `lines` (SerializerMethodField) | cap |
| `SizeFittingSerializer` | `fitting/serializers.py:18-37` | `__all__` + `model_codi, creat_per_nom, estat_display, n_graded_specs` | tots els del model menys `data_creacio` |
| `GradingVersionSerializer` | `:40-60` | `__all__` + `creat_per_nom, estalitud` | RO: `data, aprovada, aprovada_per, data_aprovacio, is_active` (viewset ReadOnly) |
| `POMAlertSerializer` | `:63-71` | `__all__` + `pom_codi, model_codi, resolt_per_nom` | **tots menys `data_creacio` — incloent `pom` i `model`** |
| `PieceFittingSummarySerializer` | `:97-112` | `id, model, …, grading_version, gate, gate_motiu, …, n_linies` | — |
| `PieceFittingLineSerializer` | `:207-213` | `id, piece_fitting, pom, size_label, valor_teoric, valor_real, nota` | **`valor_real, nota`**. **sense `capa`** |
| `PieceFittingGridSerializer` | `:216-316` | `lines` — usa `bm_data` amb clau `(pom_id, capa)` `:264-268` | cap |
| `GradingRuleSerializer` | `pom/serializers.py:151-199` | `id, rule_set*, pom, pom_codi*, pom_nom*, pom_nom_en*, pom_nom_ca*, pom_abbreviation*, pom_code_global*, pom_categoria*, talla_base, talla_base_etiqueta*, logica, increment, valors_step, actiu, increment_base, increment_break, talla_break_label, talla_break_pos` | **`pom, talla_base, logica, increment, valors_step, actiu, increment_*, talla_break_*`** |
| `GradingRuleSetSerializer` | `:202-324` | 22 camps + `regles` (niat) + `applies_to` | tot menys `is_system_default, regles, regles_count, origen`; guard dur `size_system` `:275-305` |
| `GarmentPOMMapSerializer` | `:327-406` | `id, garment_type_item, pom, pom_code*, name_en*, name_cat*, abbreviation*, categoria*, applies_*, 16 camps de POMGlobal*, is_key, obligatori, ordre, pendent_revisio` | **`garment_type_item, pom, is_key, obligatori, ordre, pendent_revisio`**. **`capa` NO exposada** |
| `ItemBaseSetSerializer` | `:409-448` | `id, garment_type_item, size_system(+codi*), fit_type(+codi*), base_size_definition(+label*), mesures_count*, mesures_amb_valor*, origen*, timestamps*` | `garment_type_item, size_system, fit_type, base_size_definition` |
| `ItemBaseMeasurementSerializer` | `:451-470` | `id, garment_type_item, base_set, pom, pom_codi*, pom_nom*, base_value_cm, tol_minus, tol_plus, nom_fitxa, origen*, updated_by*` | **`garment_type_item, base_set, pom, base_value_cm, tol_minus, tol_plus, nom_fitxa`**. **sense `capa`** |
| `CustomerPOMAliasSerializer` | `:473-528` | `id, customer, pom, pom_codi*, pom_nom*, pom_code_global*, pom_abbreviation*, pom_nom_en*, pom_nom_ca*, client_code, client_description, description_en, description_local, language, origen, pendent_revisio` | **`customer, pom, client_code, client_description, description_*, language, origen, pendent_revisio`** |
| `POMMasterSerializer` | `:34-95` | `__all__` + 24 camps derivats de POMGlobal (tots RO) | tots els del model |
| `PatternPOMSerializer` | `patterns/annotation_views.py:41-59` | `id, pattern_piece, peca*, pom_master, pom_code*, pom_nom*, definicio_mesura, metode, valor_mesurat_cm*, data_creacio*` | **`pattern_piece, pom_master, definicio_mesura, metode`** |
| `PatternFileSerializer` / `…Llista` | `patterns/serializers.py:319,363` | tots RO | cap |

> **Cap serializer de la cadena exposa `capa` avui. La instància, per tant, no té cap camp de contracte on
> aterrar en cap dels 19.**

### BLOC D · Taula de nodes del camí 2A

#### D.1 — 🔴 Contractes on `pom_id` és la clau d'un diccionari

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada | mètode+path |
|---|---|---|---|---|---|---|---|
| `pom/grading_views.py:85,108-110,137,156` | GradedSpec · BM | READ-dict | `cells[pom_id][size_label]`, serialitzat `{str(pom_id): …}` | **COL·LAPSA** | 🔴 | `C4-ins` | `GET /api/v1/size-fittings/{sf_id}/taula-mesures/` |
| `fitting/graded_spec_views.py:49,59-74,120` | GradedSpec | READ-dict | `rows_by_pom[pom.id]` + `valors`/`deltas` per talla | **COL·LAPSA** — dues instàncies fusionen les seves talles a una fila | 🔴 | `C4-ins` | `GET /api/v1/fitting/{sf_id}/graded-table/` |
| `fitting/graded_spec_views.py:94-106` | BaseMeasurement | READ-dict | 4 mapes `{bm['pom_id']: …}` sobre `.values()` filtrat `capa=exterior` | **COL·LAPSA en silenci** | 🔴 | `top-up-lectors` | ” |
| `fitting/repas_views.py:156` | MCL · SizeCheckLine | READ-dict | `celles[clau][c.pom_id]` | **COL·LAPSA** | 🔴 | `top-up-lectors` | `GET /api/v1/fitting/model/{model_id}/repas/` |
| `fitting/repas_views.py:263-266` | BaseMeasurement | READ-dict | 4 mapes per `pom_id` (`ordre`,`nom_fitxa`,**`bm_id`**,`bateig`) | **COL·LAPSA** — el `bm_id` és per on la UI desa el bateig | 🔴 | `top-up-lectors` | ” |
| `fitting/repas_views.py:272-292,305-318,333` | PieceFittingLine | READ-dict | `files[pom_id]` (una fila per POM) | **COL·LAPSA** | 🔴 | `C4-ins` | ” |
| `models_app/views.py:1625-1643` | GradedSpec | READ-dict | `graded_by_pom[pom_id][size_label]` | **COL·LAPSA** | 🔴 | `C4-ins` | `GET /api/v1/models/{model_id}/taula-mesures/` |
| `models_app/views.py:1730-1738` | BM+GradedSpec | READ-dict | **`deltas[str(pom_id)]`** — el payload `deltes` | **COL·LAPSA** | 🔴 | `C4-ins` | ” **[SOLO-2]** |
| `pom/s6_views.py:174-193` | GradedSpec | READ-dict | `pom_dict[pid]['values'][size_label]` | **COL·LAPSA** | 🔴 | `C4-ins` | `GET /api/v1/size-fittings/{sf_id}/graded-specs-units/` |
| `models_app/extraction_views.py:2175-2181` | (ImportSession→BM) | READ-dict | **`valors[pom_id][talla] = valor`** | **COL·LAPSA** | 🔴 | `C4-ins` | `POST /api/v1/import-sessions/{token}/confirmar/` |
| `models_app/pom_placement_views.py:52-64` | POMPlacement | READ-dict | `exacte`/`germana`/`merged` `{pom_id: placement}` | **COL·LAPSA** | 🔴 | `C4-ins` | `GET /api/v1/item-fitxers/{item_id}/pom-placements/` |
| `models_app/pom_placement_views.py:74-82` | BaseMeasurement | READ-dict | `bm_by_pom[(pom_id, capa)]` (**ja compost per capa**) | **COL·LAPSA** si no creix | 🔴 | `top-up-lectors` | ” |
| `pom/services.py:775-780` | BaseMeasurement | CONTRACT-engine | **`{pom_id: base_value_cm}`**, sense filtre de capa, `order_by('ordre')` | **COL·LAPSA MUT** | 🔴 | `C1-ins`+`Onada2` (zona intocable) | — |
| `pom/services.py:700-707` | MGR · GradingRule | CONTRACT-engine | `{pom_id: rule}` | **OK per disseny** però el lookup dels consumidors sí | 🟠 | `Onada2` | — |
| `pom/services.py:734-738` | ModelGradingOverride | CONTRACT-engine | `{(pom_id, size_label): v}` ancorat `capa=exterior` (frontera C3 a `:714-729`) | **COL·LAPSA** si l'àncora no creix | 🔴 | `C1-ins`+`Onada2` | — |
| `pom/services.py:401` | (preview) | CONTRACT-engine | `out[pom_id] = row` | **COL·LAPSA** | 🔴 | `Onada2` | `POST /api/v1/import-sessions/{token}/grading-preview/` |
| `patterns/views.py:134-146` | CustomerPOMAlias | READ-dict | `per_pom[a.pom_id]`, retorna `{pom_id: {client_code,…}}` | IGNORA-2a (l'àlies és de catàleg) | 🟡 | `consolidació-catàleg` | `GET /api/v1/patterns/pattern-files/{id}/model-poms/` |
| `patterns/views.py:544-561` | PatternPOM · BM | READ-dict | `ancorats[p.pom_master_id]` creuat amb `bm.pom_id` | **COL·LAPSA** | 🔴 | `F2-patrons` | ” |
| `patterns/engine/grading_projection.py:180-201` | GradedSpec | CONTRACT-engine | `poms_per_id` / `ids_amb_spec` / `codis_spec[pom_id]` | **COL·LAPSA** — la niada del CAD rep un sol delta per POM | 🔴 | `F2-patrons` | `POST /api/v1/patterns/pattern-files/{id}/export{,-preview,-rul}/` |
| `patterns/engine/ports.py:57-64` | GradedSpec | CONTRACT-engine | `GradedPOMDelta.pom_id` — **el port no té camp de capa ni d'instància** | **COL·LAPSA** al CAD | 🔴 | `F2-patrons` | — |
| `pom/wizard_views.py:339-341,352-360` | CustomerPOMAlias · MGR | READ-dict | `alias_by_pom[pom_id]`, `regla_by_pom[r.pom_id]` | IGNORA-2a (**potser correcte**, cal decisió) | ⚪ | `C4-ins` | `GET /api/v1/models/{model_id}/base-measurements/` |
| `models_app/views.py:1674-1675,1687` | CustomerPOMAlias | READ-dict | `alies_per_pom(customer_id)` → `{pom_id: …}` | IGNORA-2a | 🟡 | `consolidació-catàleg` | `GET /models/{id}/taula-mesures/` |
| `pom/s4_views.py:292-302` | GradingRule | READ-dict | `original_rules[rule.pom_id]` | OK (regla sense instància) | ⚪ | `FORA: la regla no té instància` | `POST /api/v1/sizing-profiles/{profile_id}/restaurar/` |
| `pom/size_map_views.py:674-694` | GradingRule | COUNT-gate | `by_pom[pid]` → guard de col·lisió | **OK avui**; amb instància **hauria de deixar passar** dos codis | 🟠 | `C4-ins` | `POST /api/v1/size-map/create/` **[SOLO-2]** |
| `models_app/extraction_views.py:1667-1673` | (preview) | READ-dict | `vals_per_pom` | COL·LAPSA | 🟠 | `Onada2` | `POST /api/v1/import-sessions/{token}/extraccio/` |
| `models_app/tech_sheet_views.py:322-330` | (BM) | CONTRACT-api | body `overrides.pom_mappings = {client_code: pom_code}` | **COL·LAPSA** | 🟠 | `C4-ins` | `POST /api/v1/models/create-from-sheet/` **[SOLO-2]** |

#### D.2 — Escriptors (la clau d'escriptura no porta instància)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada | mètode+path |
|---|---|---|---|---|---|---|---|
| `models_app/views.py:1793-1806` | BaseMeasurement | WRITE-update | `update_or_create(model, pom)` | **PETA** (`MultipleObjectsReturned`) | 🔴 | `Onada2` | `POST /models/{id}/set-measurements/` |
| `models_app/views.py:1812-1817` | BaseMeasurement | WRITE-delete | `exclude(pom_id__in=keep).update(is_active=False)` | **COL·LAPSA** | 🔴 | `C4-ins` | ” **[SOLO-2]** (`keep_pom_ids`) |
| `models_app/views.py:1921-1936` | BaseMeasurement | WRITE-update | `filter(model, pom).first()` | **IGNORA-2a** | 🔴 | `Onada2` | `POST /models/{id}/gravar-pom/` |
| `models_app/views.py:1941-1946` | BaseMeasurement | WRITE-delete | `keep_pom_ids` | **COL·LAPSA** | 🔴 | `C4-ins` | ” |
| `models_app/views.py:1957-1991` | MGR · GradingRule | WRITE-update | `filter(model, pom_id).first()` | OK | ⚪ | `FORA: la regla no té instància` | ” |
| `models_app/views.py:2800-2805` (`_write_base`) | BaseMeasurement | WRITE-create | `get_or_create(model, pom)` | **PETA** | 🔴 | `Onada2` | `POST /models/{id}/escalat/ajustar-talla/` |
| `models_app/views.py:2751` | MGO | WRITE-delete | `filter(model, pom).delete()` | **COL·LAPSA** | 🔴 | `Onada2` | ” |
| `models_app/views.py:2759-2771` | MGO · MCL | WRITE-update | `update_or_create(model, pom, size_label)` | **PETA** | 🔴 | `Onada2` | ” |
| `models_app/views.py:2792` | — | CONTRACT-api | `linies[].id = f'{pom.id}:{talla}'` | **COL·LAPSA** — id sintètic ambigu | 🟠 | `C4-ins` | ” **[SOLO-2]** |
| `models_app/views.py:2559-2578` | MGO · MCL | WRITE-update | `update_or_create(model, pom, size_label)` | **PETA** | 🟠 | `Onada2` | `POST /models/{id}/set-size-override/` |
| `models_app/views.py:1182-1217` | BaseMeasurement | WRITE-create | `filter(model, pom).first()` + `create(model, pom)` sense capa | **IGNORA-2a** / **PETA** | 🔴 | `Onada2` | `POST /models/{id}/materialitzar-poms/` |
| `models_app/views.py:1136,1145` | ItemBaseMeasurement | READ-dict | `{i.pom_id: i}` per `base_set` | **COL·LAPSA** | 🔴 | `consolidació-catàleg` | ” |
| `models_app/views.py:1417-1451` | BaseMeasurement | WRITE-create/update | `filter(model=dst, pom_id).first()` + `create` | **IGNORA-2a** / **PETA** | 🔴 | `Onada2` | `POST /models/{dst}/copiar-de/{src}/` |
| `models_app/views.py:1353-1355,1330-1337` | BaseMeasurement | CONTRACT-api | body `pom_ids[]` acota la còpia | **COL·LAPSA** | 🟠 | `C4-ins` | ” **[SOLO-2]** |
| `models_app/views.py:3927-3938` | BaseMeasurement | WRITE-update | `filter(model_id, pom_id, is_active=True).first()` | **IGNORA-2a** | 🔴 | `C4-ins` | `POST /models/{model_id}/pom/{pom_id}/desactivar/` **[SOLO-2]** |
| `models_app/views.py:3993-4091` | ModelGradingRule | WRITE-update | `pom_id` al PATH, `filter(model, pom_id)` | OK | ⚪ | `FORA: la regla no té instància`; la URL sí que és ambigua | `POST /models/{model_id}/pom/{pom_id}/regim/` |
| `models_app/views.py:3977-3980` | GradedSpec | READ-list | `filter(gv, pom_id, capa=exterior)` → `dict(size_label→valor)` | **COL·LAPSA** si l'àncora no creix | 🟠 | `Onada2` | ” (sembra STEP) |
| `models_app/views.py:2299` | BaseMeasurement | WRITE-update | `update_or_create(model, pom)` + `bm_id` explícit | **PETA** al camí sense `bm_id` | 🟠 | `Onada2` | `POST /models/{id}/xat-mesures/` |
| `models_app/views.py:2036` | BaseMeasurement | WRITE-update | `filter(id=bm_id, model)` | **OK** | ⚪ | `FORA: identifica per PK` | `POST /models/{id}/reorder-measurements/` |
| `models_app/views.py:2863-2869` | BaseMeasurement | WRITE-update | ids explícits | **OK** | ⚪ | `FORA: identifica per PK` | `POST /models/{id}/base-measurements/reorder/` |
| `models_app/views.py:2909-2931` | BaseMeasurement | WRITE-update | `get(id=bm_id)` | **OK** — el bateig ja és per instància si el `bm_id` arriba correcte | ⚪ | `FORA: identifica per PK` (depèn dels `bm_id_map` de D.1) | `PATCH /base-measurements/{bm_id}/noms/` |
| `models_app/views.py:496-524` | BaseMeasurement | WRITE-create/update | ViewSet CRUD, `filterset` `model,pom,is_active,origen` | **IGNORA-2a** / **PETA** | 🔴 | `C4-ins` | `GET/POST/PATCH/DELETE /api/v1/base-measurements/` **[SOLO-2]** |
| `models_app/views.py:3657,3666-3699,3770` | IBM · BM · GarmentPOMMap | WRITE-create | `actuals[i.pom_id]`, `get_or_create(base_set, pom_id)`, `next(b for b in fonts if b.pom_id==…)` | **COL·LAPSA** al diff i **PETA** al `next()` | 🔴 | `consolidació-catàleg` | `POST /models/{id}/promoure-a-item/` |
| `models_app/views.py:3851-3900` | ItemBaseMeasurement | WRITE-update | `filter(base_set, pom_id).first()` + body `{pom}` | **IGNORA-2a** | 🟠 | `consolidació-catàleg` | `POST /item-base-sets/{id}/acte-canonic/` |
| `models_app/views.py:3756-3765` | GarmentPOMMap | WRITE-create | `get_or_create(garment_type_item, pom_id)` sense capa | **PETA** | 🟠 | `consolidació-catàleg` | ” |
| `models_app/pom_placement_views.py:135-138` | POMPlacement | WRITE-update | `update_or_create(item_fitxer, pom_id, view_slot)` | **PETA** | 🔴 | `C4-ins` | `POST /item-fitxers/{item_id}/pom-placements/` **[SOLO-2]** |
| `models_app/signals.py:238-311` | MCL | WRITE-create | crea el log **sense copiar `instance.capa`** | **COL·LAPSA** — tot l'històric neix a la instància per defecte | 🔴 | `Onada2` (🚩 conegut) | — |
| `models_app/services_size_check.py:33-52` | SizeCheckLine · BM | WRITE-create · COUNT-gate | `values_list('pom_id')` + `exclude(pom_id__in=…)` + `create(size_check, pom)` sense capa | **IGNORA-2a** i **PETA** | 🔴 | `Onada2` | `POST /size-checks/open/` |
| `models_app/services_size_check.py:204-217` | BaseMeasurement | WRITE-create | `get_or_create(model, pom=line.pom)` | **PETA** | 🔴 | `Onada2` | `POST /size-checks/{id}/resolve/` |
| `pom/wizard_views.py:186-227` | BaseMeasurement | WRITE-update | `filter(model, pom_id).update(base_value_cm=None)` + `update_or_create(model, pom_id)` | **COL·LAPSA** / **PETA** | 🔴 | `Onada2` | `POST /models/{model_id}/guardar-talla-base/` |
| `pom/services.py:1032-1044` | GradedSpec | WRITE-update | `update_or_create(grading_version_id, pom_id, size_label)` | **PETA** (uk té `capa`) | 🔴 | `Onada2` | — (via `generar-grading`) |
| `pom/services.py:233-270` | BM→GradedSpec | CONTRACT-engine | `for pom_id, base_val in base_measurements.items()` | **COL·LAPSA** | 🔴 | `Onada2` | `POST /models/{id}/generar-grading/` |
| `fitting/services.py:330-340` | GradedSpec→PFL | WRITE-create | `create(piece_fitting, pom=spec.pom, size_label)` — **no copia `spec.capa`** | **PETA** | 🔴 | `Onada2` | `POST /fitting-sessions/{id}/create-piece/` |
| `fitting/services.py:361-380` | PFL→BM | WRITE-create | `get_or_create(model, pom=line.pom)` | **PETA** | 🔴 | `Onada2` | `POST /piece-fittings/{id}/close/` · `POST /models/{id}/generar-grading/` |
| `fitting/views.py:617-619,663-668` | PieceFittingLine | READ-list · WRITE-update | `filter(piece_fitting, pom=line.pom[, size_label])` — **cap filtre de capa** | **COL·LAPSA** | 🔴 | `Onada2` | `POST /piece-fitting-lines/{id}/propagar/` |
| `models_app/views.py:2426` | MGO | WRITE-delete | `filter(model=model).delete()` (llenç net) | **OK** | ⚪ | `FORA: acte de model sencer` | `POST /models/{id}/generar-grading/` |
| `models_app/views.py:2494` | GradedSpec | READ-list | `filter(grading_version=gv, pom=pom)` → `graded[size_label]` | **COL·LAPSA** | 🟠 | `C4-ins` | ” |
| `models_app/views.py:2789-2791` | GradedSpec | READ-list | ídem | **COL·LAPSA** | 🟠 | `C4-ins` | `POST /models/{id}/escalat/ajustar-talla/` |
| `pom/s10_views.py:139-151` | POMAlert | WRITE-update | `update_or_create(model, pom_id, size_fitting)` — POMAlert **no té `capa`** | **COL·LAPSA** | 🔴 | `C1-ins`+`Onada2` | `GET /fittings/peca/{pf_id}/vs-spec/` |
| `pom/s11_views.py:167-200` | BM · POMAlert | READ-dict · WRITE-update | `base_map[bm.pom_id]` (filtrat `capa=exterior`) + `update_or_create(model, pom)` | **COL·LAPSA** | 🔴 | `C1-ins`+`Onada2` | `POST /models/{model_id}/check-tolerances/` |
| `pom/s11_views.py:146-149` | — | CONTRACT-api | body `measurements[].{pom_id, value_cm}` — **cap slot de capa ni instància** (comentaris `:162-164`) | **COL·LAPSA** | 🔴 | `C4-ins` | ” **[SOLO-2]** |
| `pom/views.py:443-511` | ItemBaseMeasurement | WRITE-update | `update_or_create(base_set, pom_id)` sense capa | **PETA** | 🟠 | `consolidació-catàleg` | `POST /item-base-measurements/upsert/` |
| `pom/views.py:437-441` + `pom/serializers.py:451-470` | ItemBaseMeasurement | WRITE-create/update | CRUD sense `capa` al serializer | **PETA** | 🟠 | `consolidació-catàleg` | `POST/PATCH /item-base-measurements/{,id}/` **[SOLO-2]** |
| `pom/views.py:318-347` + `pom/serializers.py:391-406` | GarmentPOMMap | WRITE-create/update | CRUD sense `capa` al serializer | **PETA** | 🟠 | `consolidació-catàleg` | `POST/PATCH /garment-pom-maps/{,id}/` **[SOLO-2]** |
| `tenants/federation_service.py:591-605` | BaseMeasurement | READ-list | empaqueta per `_clau_natural_pom(bm.pom)` | **COL·LAPSA** al paquet | 🔴 | `C4-ins` | `POST /api/v1/encarrecs/enviar/` **[SOLO-2]** |
| `tenants/federation_service.py:689-706` | BaseMeasurement | WRITE-create | `filter(model=twin, pom=pom).first()` + `create(model, pom)` | **IGNORA-2a** / **PETA** | 🔴 | `Onada2` | ” |
| `tenants/federation_service.py:730-742` | ModelGradingRule | WRITE-create | `filter(model=twin, pom=pom).exists()` | OK | ⚪ | `FORA: la regla no té instància` | ” |
| `models_app/extraction_views.py:2560` | BaseMeasurement | WRITE-update | `update_or_create(model, pom=pm)` | **PETA** | 🔴 | `Onada2` | `POST /import-sessions/{token}/confirmar/` |
| `models_app/extraction_views.py:2331-2334, 2367-2371, 2515-2523` | BaseMeasurement | WRITE-delete · READ-list | `exclude(pom_id__in=confirmed_pom_ids)` i `filter(pom_id__in=_doc_pom_ids)` | **COL·LAPSA** — la instància B es poda per un document que parla de l'A | 🔴 | `Onada2` | ” |
| `models_app/extraction_views.py:2686-2696` | MGO | WRITE-update | `update_or_create(model, pom_id, size_label)` | **PETA** | 🔴 | `Onada2` | ” |
| `models_app/extraction_views.py:1148-1194` | BaseMeasurement | COUNT-gate | **`_apply_many_to_one_guard`** — «`BaseMeasurement` és únic per `(model, pom)`» (`:1151`) | **La premissa del guard cau**: avui **bloqueja el cas legítim** | 🔴 | `C4-ins` | ” **[SOLO-2]** |
| `models_app/views.py:3589-3596, 1340-1345, 1555-1557, 2375-2377, 1910-1912, 1997-1999` | BaseMeasurement | COUNT-gate | `.exists()` / `.count()` sobre `(model)` sense capa | **OK** | ⚪ | `FORA: comptador, no clau` | vàries |
| `models_app/bulk_import_service.py:536-540` | SizeFitting | WRITE-create | `bulk_create(SizeFitting(model, numero=1))` | **OK** | ⚪ | `FORA: SizeFitting és per model` | `POST /bulk-import/{id}/commit/` |
| `models_app/views.py:703-947`, `:950-1019` | ModelGradingRule | WRITE-create | per `(model, pom)` | OK | ⚪ | `FORA: la regla no té instància` | `POST /models/create-wizard/` · `PATCH /models/{id}/update-step2/` |

#### D.3 — Lectors que ja porten clau composta `(pom, capa)` i han de créixer alhora

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada | mètode+path |
|---|---|---|---|---|---|---|---|
| `models_app/views.py:2999,3004,3010-3012,3022-3026` | MCL · BM | READ-dict | `changes_by_ev[key][(pom_id, capa)]`, `snapshot`, `displayed`, `clau_bm` | **COL·LAPSA** i el **carry-forward** arrossega el valor d'una instància per la fila de l'altra | 🔴 | `top-up-lectors` | `GET /models/{model_id}/base-stages/` |
| `models_app/views.py:3027-3045` | BaseMeasurement | CONTRACT-api | `rows[].pom_id` (sense capa ni instància al payload) | **COL·LAPSA** al front | 🔴 | `C4-ins` | ” |
| `fitting/serializers.py:264-268, 273, 288-297` | BM · PFL | READ-dict | `ordre_map`/`nom_fitxa_map`/**`bm_id_map`** per `(pom_id, capa)` | **COL·LAPSA** — el `bm_id` mal resolt escriu el bateig a l'altra instància | 🔴 | `top-up-lectors` | `GET /piece-fittings/{id}/` |
| `models_app/serializers_size_check.py:86-113` | BM · SizeCheckLine | READ-dict | `bm_map[(pom_id, capa)]` → tolerància + `codi_fitxa` + `ordre` | **COL·LAPSA** — veredicte dins/fora amb la vara de l'altra | 🔴 | `top-up-lectors` | `GET /size-checks/{id}/` |
| `pom/s8_views.py:179-208` | BM · PFL | READ-dict | `tol_map[(pom_id, capa)]` | **COL·LAPSA** | 🟠 | `top-up-lectors` | `GET /fittings/peca/{pf_id}/export/csv/` |
| `pom/s10_views.py:43-60, 94` | BaseMeasurement | READ-dict | `tol[(pom_id, capa)]` | **COL·LAPSA** | 🟠 | `top-up-lectors` | `GET /fittings/peca/{pf_id}/vs-spec/` |
| `pom/s6_views.py:87-105` | BaseMeasurement | READ-list | filtrat `capa=exterior`; comentari `:87-89` declara que **el consumidor indexa per `pom_id`** | IGNORA-2a | 🟠 | `C4-ins` | `GET /models/{model_id}/base-measurements-units/` |
| `fitting/repas_views.py:99-112` | SizeCheckLine | READ-dict | `fora[(size_check_id, pom_id)]` | **COL·LAPSA** | 🟠 | `top-up-lectors` | `GET /fitting/model/{id}/repas/` |
| `fitting/staleness.py:112-117` | MCL | READ-list | `poms_afectats` per `codi_client` | IGNORA-2a | 🟡 | `top-up-lectors` | `GET /grading-versions/` · `/models/{id}/grading-status/` |
| `models_app/views.py:1620-1623, 1678-1713` | BaseMeasurement | READ-list | `filter(model, is_active)` **sense filtre de capa** + files per `pom_id` | **COL·LAPSA** al payload | 🔴 | `C4-ins` | `GET /models/{id}/taula-mesures/` |
| `models_app/views.py:2957-2958`, `2486-2508`, `3589-3591`, `patterns/views.py:553-557`, `pom/wizard_views.py:320-325` | BaseMeasurement | READ-list | `filter(model, is_active).order_by('ordre',…)` sense capa | **COL·LAPSA** al payload | 🟠 | `C4-ins` | vàries |

#### D.4 — Contractes de catàleg i altres

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada | mètode+path |
|---|---|---|---|---|---|---|---|
| `patterns/models.py:432` + `annotation_views.py:518-556` | PatternPOM | WRITE-create | uk `('pattern_piece','pom_master')` — «un POM es mesura UNA vegada per peça» | **PETA** | 🟠 | `F2-patrons` | `POST /patterns/pattern-poms/` |
| `patterns/adapters.py:484-510, 623` | GradedSpec · PatternPOM | CONTRACT-engine | `GradedPOMDelta(pom_id=…)`, `POMSpec(pom_id=pom.pom_master_id)` | **COL·LAPSA** | 🔴 | `F2-patrons` | — |
| `patterns/engine/ftt_pom_layer.py:41-58` | PatternPOM | CONTRACT-engine | etiqueta DXF `FTT "<codi>" <nom> = <valor> mm` — **el codi del POM és tota la identitat** | **COL·LAPSA** — el DXF no pot dir de quina instància parla | 🟠 | `F2-patrons` | `POST /patterns/pattern-files/{id}/export/` **[SOLO-2]** |
| `patterns/views.py:686-718` | GradingVersion · GradedSpec | READ-list | `specs = gv.graded_specs.filter(is_active).count()` | **OK** (comptador) | ⚪ | `FORA: comptador` | `GET /patterns/pattern-files/{id}/grading-versions/` |
| `pom/dictionary_views.py:97-170` | CustomerPOMAlias | WRITE-update | `update_or_create` per `(customer, client_code)` | OK | ⚪ | `consolidació-catàleg` | `POST /pom/customers/{id}/dictionary/commit/` |
| `pom/services.py:578-645` (`maybe_learn_customer_alias`) | CustomerPOMAlias | WRITE-create | `(customer, client_code) → pom` | IGNORA-2a | 🟡 | `consolidació-catàleg` | (via `confirmar/`) |
| `pom/s2_views.py:264-303` · `s4_views.py:36-118` | GradingRule | WRITE-update | **`pom_codi` al PATH** | OK (regla sense instància) | ⚪ | `FORA: la regla no té instància` | `PATCH /grading-rule-sets/{id}/regles/{pom_codi}/{,editar/}` |
| `pom/serializers.py:151-199` + `pom/views.py:281-316` | GradingRule | WRITE-create/update | `pom` escrivible, uk `(rule_set, pom)` | OK | ⚪ | `FORA: la regla no té instància` | `POST/PATCH /grading-rules/{,id}/` |
| `fitting/serializers.py:63-71` + `fitting/views.py:127-144` | POMAlert | WRITE-create/update | `__all__` amb `pom` escrivible, **cap `capa`** | **COL·LAPSA** | 🟠 | `C1-ins`+`C4-ins` | `POST/PATCH /pom-alerts/{,id}/` |
| `models_app/views.py:3176-3308` | POMAlert | READ-list | `alertes[].pom_codi` | **COL·LAPSA** | 🟡 | `C4-ins` | `GET /models/{id}/dashboard/` |
| `models_app/views.py:3311-3411` | MCL | READ-list | `{pom_id, pom_codi}` per event | IGNORA-2a | 🟡 | `C4-ins` | `GET /models/{id}/timeline/` |
| `models_app/views.py:3414-3494` | MCL | READ-list | ídem | IGNORA-2a | 🟡 | `C4-ins` | `GET /registre-activitat/` |
| `models_app/serializers.py:389-412` | BaseMeasurement | CONTRACT-api | `fields` **sense `capa`** | **el contracte no té on posar-la** | 🔴 | `C4-ins` | `GET/POST/PATCH /base-measurements/{,id}/` **[SOLO-2]** |
| `models_app/serializers_size_check.py:19` | SizeCheckLine | CONTRACT-api | `fields` sense `capa` | ídem | 🟠 | `C4-ins` | `PATCH /size-check-lines/{id}/` **[SOLO-2]** |
| `fitting/serializers.py:212` | PieceFittingLine | CONTRACT-api | `fields` sense `capa` | ídem | 🟠 | `C4-ins` | `PATCH /piece-fitting-lines/{id}/` **[SOLO-2]** |
| `pom/serializers.py:393-406`, `:462-469` | GarmentPOMMap · ItemBaseMeasurement | CONTRACT-api | `fields` sense `capa` | ídem | 🟠 | `consolidació-catàleg` | **[SOLO-2]** |
| `pom/models.py:1171` | ClientMesuraPerfil | WRITE-update | uk `('codi_client','garment_type','pom','talla')`, escrit per `update_client_profile` (`services.py:526`) | **COL·LAPSA** — el Welford barreja instàncies | 🟡 | `C1-ins` (⚪ si es decideix que l'estadística és per POM) | `POST /piece-fittings/{id}/close/` |
| `models_app/views.py:2115-2225` · `2227-2353` | BaseMeasurement | READ-list | context per a la IA per `bm.pom.codi_client` | IGNORA-2a | ⚪ | `C4-ins` | `POST /models/{id}/analisi-ia/` · `/xat-mesures/` |
| `models_app/pom_vision_views.py:25-45` | (POMPlacement, indirecte) | CONTRACT-api | body `poms[].{pom_id, code, canonical_name, client_alias, definition}` | **COL·LAPSA** — la proposta de cotes no distingeix instàncies | 🟠 | `C4-ins` | `POST /models/{id}/proposar-cotes/` **[SOLO-2]** |
| `models_app/extraction_views.py:50-120` | BM, SizeFitting, GradingVersion, GradedSpec | WRITE-delete | esborrat en cascada del model | **OK** | ⚪ | `FORA: esborra el model sencer` | `DELETE /models/{model_id}/delete/` |
| `models_app/extraction_views.py:1780-1944` | (poms_extrets) | CONTRACT-api | `poms_extrets[].pom_master_id` — una fila de document → un POM | **COL·LAPSA** | 🟠 | `C4-ins` | `PATCH /import-sessions/{token}/poms/` |
| `models_app/extraction_views.py:1987-2025` | (mesures) | CONTRACT-api | body `mesures[].{pom_master_id, talla_label, valor}` | **COL·LAPSA** | 🟠 | `C4-ins` | `PATCH /import-sessions/{token}/mesures/` **[SOLO-2]** |
| `models_app/extraction_views.py:2030-2110` | ItemBaseMeasurement | READ-list | prefill de biblioteca per POM | IGNORA-2a | ⚪ | `consolidació-catàleg` | `POST /import-sessions/{token}/library-prefill/` |
| `pom/s9_views.py:79-213` | POMMaster · GradingRuleSet · GradingRule | WRITE-create | sembra d'onboarding per codi | IGNORA-2a | ⚪ | `consolidació-catàleg` | `POST /onboarding/setup-from-excel/` |
| `pom/size_map_views.py` (`lookups/match/preview/grading-preview{,-file}/systems`) | POMMaster · GradingRule | READ-list | matching per codi de document | IGNORA-2a | ⚪ | `C4-ins` | 6 rutes `GET/POST /size-map/…` |
| `pom/views.py:49-59` + `wizard_views.py:410-480` | POMMaster · POMGlobal | WRITE-create/update | catàleg | **OK** | ⚪ | `FORA: catàleg` | `/poms/…` |
| `pom/services.py:104-164` (`escala_del_model`) | Model · SizeSystem | CONTRACT-engine | geometria del run | **OK** | ⚪ | `FORA: no toca POM` | — |
| `pom/services.py:460-524` (`close_base`) | GradedSpec | COUNT-gate | `.count()` / `.exists()` | **OK** | ⚪ | `FORA: comptador` | `POST /models/{id}/tancar-taula/` |
| `pom/services.py:786-822` (`_get_or_create_grading_version`) | GradingVersion | WRITE-create | per SizeFitting | **OK** | ⚪ | `FORA: no toca POM` | — |
| `fitting/views.py:99-125` (`approve`) | GradingVersion | WRITE-update | segell per versió | **OK** | ⚪ | `FORA: no toca POM` | `POST /grading-versions/{id}/approve/` |

### Recompte camí 2A

**63 files.**

| tipus | n | | «amb 2 inst.» | n | | risc | n | | onada | n |
|---|---|---|---|---|---|---|---|---|---|---|
| READ-dict | 20 | | COL·LAPSA | **34** | | 🔴 | 33 | | `C1-ins` | 5 |
| READ-list | 11 | | PETA | **17** | | 🟠 | 20 | | `top-up-lectors` | 12 |
| WRITE-create | 12 | | IGNORA-2a | 14 | | 🟡 | 6 | | `Onada2` | 26 |
| WRITE-update | 17 | | OK | 13 | | ⚪ | 20 | | `C4-ins` | 29 |
| WRITE-delete | 5 | | | | | | | | `F2-patrons` | 7 |
| COUNT-gate | 4 | | | | | | | | `consolidació-catàleg` | 13 |
| CONTRACT-api | 14 | | | | | | | | `FORA:` | 17 |
| CONTRACT-engine | 9 | | | | | | | | | |

*(les files amb tipus compost compten a cada tipus; total d'ocurrències 92 sobre 63 files)*

### Els 11 payloads «dict per `pom_id`» — llista destacada

Els payloads on `pom_id` és la clau d'un diccionari **exposat al client** (no un mapa intern):

1. `pom/grading_views.py:156` → **`cells: {str(pom_id): {talla: {value,type,increment}}}`** — `GET /size-fittings/{sf_id}/taula-mesures/`
2. `models_app/views.py:1736-1738` → **`deltes: {str(pom_id): float\|null}`** — `GET /models/{id}/taula-mesures/`
3. `fitting/graded_spec_views.py:120` → `rows` derivat de `rows_by_pom` — `GET /fitting/{sf_id}/graded-table/`
4. `pom/s6_views.py:193` → `results` derivat de `pom_dict[pid]` — `GET /size-fittings/{sf_id}/graded-specs-units/`
5. `fitting/repas_views.py:333` → `rows` derivat de `files[pom_id]` — `GET /fitting/model/{id}/repas/`
6. `models_app/pom_placement_views.py:60-92` → `placements` derivat de `merged[pom_id]` — `GET /item-fitxers/{item_id}/pom-placements/`
7. `models_app/views.py:3016-3045` → `rows` derivat de la clau `(pom_id, capa)` — `GET /models/{id}/base-stages/`
8. `models_app/extraction_views.py:2175-2181` → `valors[pom_id][talla]` — `POST /import-sessions/{token}/confirmar/`
9. `pom/wizard_views.py:339-367` → `regla_model` per `regla_by_pom[pom_id]` — `GET /models/{id}/base-measurements/`
10. `patterns/views.py:144` → `{pom_id: {client_code,…}}` — `GET /patterns/pattern-files/{id}/model-poms/`
11. `models_app/tech_sheet_views.py:322` → body `pom_mappings: {client_code: pom_code}` — `POST /models/create-from-sheet/`

> **El pitjor cas de tots és el 6**: `merged` col·lapsa, i el `bm_id` que en surt s'usa per **desar** el
> bateig i per lligar la cota del croquis. No peta: **pinta**, i lliga el dibuix a la mesura equivocada.
> **El de radi més ampli és el 1 + 3 + 4**: tres endpoints que serveixen la MATEIXA matriu POM×talla amb
> tres formes de dict diferents. Amb dues instàncies, **els tres menteixen alhora i de maneres diferents**.

### Nodes [SOLO-CAMÍ-2] del camí 2A (18)

Un cens que grepegi noms de taula **no** troba cap d'aquests, perquè el problema és la **forma del
contracte**, no la taula:

1. `models_app/views.py:1736` — `deltes: {str(pom_id): …}` (cap nom de taula a la vora)
2. `models_app/views.py:1774,1812` i `:1847,1941` — **`keep_pom_ids`**: una llista de `pom_id` que decideix quines files sobreviuen
3. `models_app/views.py:1329-1337,1352-1355` — body `pom_ids[]` de `copiar-de/`
4. `models_app/views.py:1109-1125` — body `pom_ids[]` de `materialitzar-poms/`
5. `models_app/views.py:2792` — id sintètic `"{pom_id}:{talla}"` a `linies[]`
6. `models_app/views.py:3911` — **`pom_id` al PATH** de `/models/{model_id}/pom/{pom_id}/desactivar/`
7. `models_app/views.py:3993` — **`pom_id` al PATH** de `…/regim/`
8. `models_app/serializers.py:403-411` — `BaseMeasurementSerializer.fields` **sense cap camp d'eix**
9. `models_app/serializers_size_check.py:19` — `SizeCheckLineSerializer.fields` ídem
10. `fitting/serializers.py:212` — `PieceFittingLineSerializer.fields` ídem
11. `pom/serializers.py:393-406` — `GarmentPOMMapSerializer.fields` ídem
12. `pom/serializers.py:462-469` — `ItemBaseMeasurementSerializer.fields` ídem
13. `models_app/pom_placement_views.py:113,135` — body i clau d'`update_or_create` de la cota
14. `models_app/extraction_views.py:1148-1194` — **`_apply_many_to_one_guard`**: un guard la premissa del qual deixa de ser certa
15. `models_app/extraction_views.py:2019-2022` — body `mesures[].{pom_master_id, talla_label, valor}`
16. `pom/s11_views.py:146-149` — body `measurements[].{pom_id, value_cm}`
17. `pom/size_map_views.py:674-694` — el guard `by_pom` que **bloquejaria** un cas que amb instàncies seria legítim
18. `tenants/federation_service.py:545-580,591` — `_clau_natural_pom` · i `patterns/engine/ftt_pom_layer.py:41` — l'etiqueta DXF que surt de casa

### Tres observacions per a la convergència amb el camí 1

- **La frontera C3 ja està escrita al codi.** `pom/services.py:714-729` diu literalment que
  `_load_model_overrides` es queda per POM **perquè `_load_base_measurements` (`:767`, zona intocable)
  encara indexa per POM sol**, i que *«el dia que C3 doni capa a `_load_base_measurements`, aquesta clau ha
  de créixer amb ella i el filtre se'n va: van junts»*. **Amb la instància passa exactament igual, i el punt
  de decisió és el mateix.**
- **Onada 1 ja va fer 6 lectors amb clau `(pom, capa)`** (`base_stages_view`, `PieceFittingGridSerializer`,
  `SizeCheckGridSerializer`, `s8`, `s10`, `pom_placement_views`) i **4 amb àncora explícita `capa=exterior`**
  (`graded_spec_views`, `repas_views`, `s6`, `s11`, `_sembra_step`, `_load_model_overrides`).
  **Tots deu han de créixer alhora amb la instància.**
- **Els dos forats que Onada 1 va deixar oberts es multipliquen.** `models_app/signals.py:238-311` (el senyal
  F1 **no estampa `capa`**) i `pom/services.py:767` (`_load_base_measurements` **sense filtre de capa**) són
  els dos únics punts on una escriptura/lectura de la cadena travessa l'eix sense declarar-lo. Són també,
  per construcció, **els dos que fan que tots els nodes `top-up-lectors` quedin condicionats**.

---
## II.7 · CAMÍ 2B — frontend principal

**`frontend/src`, 219 fitxers. 158 files.**

> **Mètode 3 (ESTAT) — resultat negatiu i important:** `frontend/src/store/` conté **només `auth.js`**
> (verificat independentment). **No hi ha cap store global** (Redux/Zustand/Context) que guardi mesures.
> **Tot l'estat de mesures és LOCAL per component**, de manera que el col·lapse no és a un punt sinó
> **replicat a ~12 llocs independents**. **[SOLO-CAMÍ-2]**

### A · `TechSheetEditor.jsx` — el límit declarat de la diagnosi prèvia

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `pages/TechSheetEditor.jsx:276` `cotaLabelDe` | BaseMeasurement | READ-dict | `bm` (nom_fitxa/codi_client/pom_code_global) | COL·LAPSA (dues instàncies → etiqueta idèntica al croquis) | 🟠 | C4-ins |
| `:283-298` `cotaEndsMm` | — (objecte .ftt) | READ-dict | `g.pomId != null` com a discriminant de "és cota" | OK (discriminant, no índex) | ⚪ | C4-ins |
| `:320-347` `buildLiveCota` | BaseMeasurement | WRITE-create (objecte .ftt) | escriu `{pomId, bmId, pomCanonical}` al grup | IGNORA-2a (no hi ha camp d'instància al grup) | 🔴 | **C4-ins — punt d'entrada del camp nou al .ftt** |
| `:352-374` `cotaHandleEnds` | — | READ-dict | `g.pomId != null` | OK | ⚪ | C4-ins |
| `:381-398` `autoPlaceCotaLabel` | — | READ-dict | `cota.pomId != null` | OK | ⚪ | C4-ins |
| `:739-800` `buildTablePrimitives` (bloc `graded_table` legacy) | GradedSpec | READ-list | `rows[]` amb `ref/codi`; sense clau d'instància | COL·LAPSA (dues files amb el mateix `ref`) | 🟠 | C4-ins |
| `:1716` `blocksTransform` | — | READ-dict | `obj.pomId != null` | OK | ⚪ | C4-ins |
| `:1772` `addObjectToLayer` (`esCota`) | — | READ-dict | `obj.pomId != null` | OK | ⚪ | C4-ins |
| `:2188` `KonvaObject cotaLabel` | — | READ-dict | `obj.pomId != null` | OK | ⚪ | C4-ins |
| `:2198` nanses de cota | — | READ-dict | `obj.pomId != null` | OK | ⚪ | C4-ins |
| `:2601` `useState pomRows` | BaseMeasurement | READ-list | llista plana; comentari `:2599` diu «cap id hi viatja» (**obsolet**) | IGNORA-2a | 🟠 | C4-ins |
| `:2613` `propostes` Map | POMPlacement | READ-dict | `pom_id → {p, derivat, hostId}` | COL·LAPSA | 🔴 | C4-ins |
| `:3157` `selDim esCota` | — | READ-dict | `obj.pomId != null` | OK | ⚪ | C4-ins |
| `:3350-3359` fetch `base-measurements/` | BaseMeasurement | CONTRACT-api | resposta plana `results[]` | IGNORA-2a | 🟠 | C4-ins |
| `:3366-3375` fetch `fitting/model/{id}/repas/` | FittingSession + BaseStage | CONTRACT-api | només compta sessions | OK | ⚪ | C4-ins |
| `:3436` fetch `fitting/{sf}/graded-table/` | GradedSpec | CONTRACT-api | `rows[]` sense instància | COL·LAPSA | 🟠 | C4-ins |
| `:3456` `bmById = Map(bm.id)` | BaseMeasurement | READ-dict | `bm.id` (PK de la fila) | **OK** — l'únic índex instància-segur del fitxer | ⚪ | — |
| `:3457` `bmByPom = Map(bm.pom_id)` | BaseMeasurement | READ-dict | `pom_id` | COL·LAPSA (l'última instància guanya) | 🔴 | C4-ins |
| `:3462` `bmById.get(o.bmId) \|\| bmByPom.get(o.pomId)` | BaseMeasurement | READ-dict | fallback per `pomId` | IGNORA-2a (cotes velles sense `bmId` es reancoren a la instància equivocada) | 🔴 | C4-ins |
| `:4110-4148` creació de cota amb l'eina `cota_pom` | BaseMeasurement | WRITE-create | `pom.pomId / pom.bmId` de `cotaPreset` | IGNORA-2a | 🔴 | C4-ins |
| `:4145` `...(pom?.pomId != null ? {pomId, bmId, pomCanonical} : {})` | — | WRITE-create | escalars al grup | IGNORA-2a | 🔴 | C4-ins |
| `:4817` T0 fetch `base-measurements/` | BaseMeasurement | CONTRACT-api | llista plana | IGNORA-2a | 🟠 | C4-ins |
| `:4847-4851` T0 `rows = bms.map(...)` | BaseMeasurement | READ-list | ordre de llista; `nomenclaturaDePom(bm)` | COL·LAPSA visualment (dues files idèntiques a la fitxa impresa) | 🟠 | C4-ins |
| `:4879` T1a fetch base-measurements + grading-rules | BM + GradingRule | CONTRACT-api | — | IGNORA-2a | 🟠 | C4-ins |
| `:4898-4902` `rulesByPom` | GradingRule + MGR | READ-dict | `r.pom` / `bm.pom_id` | **COL·LAPSA** — les dues instàncies comparteixen regla | 🔴 | C4-ins |
| `:4916` `rule = rulesByPom[bm.pom_id]` | GradingRule | READ-dict | `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `:4928-4931` `seccionsDeFiles(bms)` + partició | BaseMeasurement | READ-list | `bm.seccio` | OK (secció no és identitat) | ⚪ | C4-ins |
| `:4954` T1b fetch `graded-table/` | GradedSpec | CONTRACT-api | `data.rows[]` | COL·LAPSA | 🟠 | C4-ins |
| `:4981-4985` T1b `filesDe` | GradedSpec | READ-list | `row.ref \|\| row.abbreviation \|\| row.codi` | COL·LAPSA (dues files amb el mateix REF) | 🟠 | C4-ins |
| `:5022` T3 fetch `fitting/model/{id}/repas/` | BaseStage + PFL | CONTRACT-api | `data.rows[]` | COL·LAPSA | 🟠 | C4-ins |
| `:5054-5059` T3 `rows` | Repàs | READ-list | `row.codi \|\| row.pom_code` | COL·LAPSA | 🟠 | C4-ins |
| `:5350-5354` porta T1a (`t1aOk`) | BM + MGR | COUNT-gate | `pomRows.length` + `some(r => r.regla_model)` | OK (compta files, no POMs) | ⚪ | C4-ins |
| `:5362` porta T0 (`baseMeasuresOk`) | BaseMeasurement | COUNT-gate | `some(base_value_cm != null)` | OK | ⚪ | C4-ins |
| **`:5426-5435` `cotesColocades`** | objecte .ftt | READ-dict | `Set` de `o.pomId` | **COL·LAPSA — col·locar la cota de la instància A marca la B com a feta** | 🔴 | **C4-ins · GUARD** |
| `:5437-5443` `iaCotesByPom` | objecte .ftt | READ-dict | `Set` de `o.pomId` | COL·LAPSA | 🔴 | C4-ins |
| `:5445` `iaPropostesVives` | objecte .ftt | READ-list | filtra per `o.pomId != null` | OK (llista, no índex) | ⚪ | C4-ins |
| `:5477-5489` agregació de propostes | POMPlacement | READ-dict | `acc.set(p.pom_id, ...)` | **COL·LAPSA** — el precedent de la 2a instància trepitja el de la 1a | 🔴 | C4-ins |
| `:5481-5482` fetch `item-fitxers/{i}/pom-placements/` | POMPlacement | CONTRACT-api | `placements[].pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `:5506` `pomRows.find(r => r.pom_id === pomId)` | BaseMeasurement | READ-dict | primer match per `pom_id` | IGNORA-2a (sempre la 1a) | 🔴 | C4-ins |
| `:5512` `label: cotaLabelDe(bm) \|\| p.codi, pomId, bmId: p.bm_id` | POMPlacement | WRITE-create | `pom_id` + `bm_id` del precedent | IGNORA-2a | 🔴 | C4-ins |
| `:5521-5526` `posarProposta(pomId)` | POMPlacement | WRITE-create | `propostes.get(pomId)` | IGNORA-2a | 🔴 | C4-ins |
| **`:5532-5534` `pomsSenseCota`** | BaseMeasurement | READ-list | `!cotesColocades.has(bm.pom_id)` | **IGNORA-2a — la 2a instància desapareix de la llista d'auto-col·locació** | 🔴 | **C4-ins · GUARD** |
| `:5540-5549` `triats` / `alternaTriat` / `alternaTotsTriats` | — | READ-list | `Set` de `pomId` | COL·LAPSA (una casella marca les dues files) | 🔴 | C4-ins |
| **`:5554-5563` `colocarCotes(pomIds)`** | BM + POMPlacement | WRITE-create | `if (cotesColocades.has(pomId)) continue` | **IGNORA-2a** | 🔴 | **C4-ins · GUARD** |
| `:5565-5573` repartiment sense precedent (`bmByPom`) | BaseMeasurement | WRITE-create | `Map` per `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `:5586-5606` `construirPrecedentCota` | POMPlacement | WRITE-create | `body.pom_id = cota.pomId` | COL·LAPSA (el precedent no sap de quina instància és) | 🔴 | C4-ins |
| `:5607-5615` `desarUnaPrecedent` POST `pom-placements/` | POMPlacement | CONTRACT-api | payload sense instància | COL·LAPSA | 🔴 | C4-ins |
| `:5618-5625` `escriurePrecedentSilent` | POMPlacement | WRITE-create | ídem | COL·LAPSA | 🔴 | C4-ins |
| `:5632-5633` `pendents` (IA) | BaseMeasurement | READ-list | `!cotesColocades.has \|\| !iaCotesByPom.has` per `pom_id` | IGNORA-2a | 🔴 | C4-ins |
| `:5640` `netaObjs` (rasteritza sense cotes) | — | READ-list | `o.pomId != null` | OK | ⚪ | C4-ins |
| `:5652-5656` payload POMs cap a la IA | BaseMeasurement | CONTRACT-engine | `{pom_id, code, canonical_name, client_alias, definition}` | **COL·LAPSA — la IA rep dos POMs idèntics i no pot distingir-los** | 🔴 | C4-ins |
| `:5657-5659` POST `models/{id}/proposar-cotes/` | (motor visió) | CONTRACT-engine | `poms[].pom_id` com a clau de retorn | COL·LAPSA | 🔴 | C4-ins |
| `:5666` `bmByPom` (materialització IA) | BaseMeasurement | READ-dict | `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| **`:5670`** `if (!host \|\| cotesColocades.has(p.pom_id) \|\| iaCotesByPom.has(p.pom_id)) continue` | — | COUNT-gate | `pom_id` | **IGNORA-2a — la 2a proposta del mateix POM es descarta en silenci** | 🔴 | **C4-ins · GUARD** |
| `:5673-5682` construcció de la cota IA | BaseMeasurement | WRITE-create | `pomId: p.pom_id, bmId: bm?.id` | IGNORA-2a | 🔴 | C4-ins |
| `:5697-5700` `acceptarProposta` | POMPlacement | WRITE-create | escriu precedent per `pomId` | COL·LAPSA | 🔴 | C4-ins |
| `:6620-6627` capçalera del contenidor | BaseMeasurement | COUNT-gate | `pomRows.length` | OK | ⚪ | C4-ins |
| `:6636-6653` botó d'assignació automàtica | — | COUNT-gate | `pomsSenseCota.length` | IGNORA-2a (compta de menys) | 🟠 | C4-ins |
| `:6687` `pomRows.map(bm => ...)` | BaseMeasurement | READ-list | iteració | OK | ⚪ | C4-ins |
| `:6690-6702` etiqueta/noms de la fila | BaseMeasurement | READ-dict | `nom_fitxa`, `nom_canonic_model`, `nom_traduit_model` | COL·LAPSA visualment (dues files idèntiques, res les distingeix) | 🟠 | C4-ins |
| `:6703` `colocat = cotesColocades.has(bm.pom_id)` | — | READ-dict | `pom_id` | **COL·LAPSA** | 🔴 | **C4-ins · GUARD** |
| `:6704` `armat = cotaPreset?.bmId === bm.id` | BaseMeasurement | READ-dict | `bm.id` | **OK** — instància-segur | ⚪ | — |
| `:6706` `iaProp = iaCotesByPom.has(bm.pom_id)` | — | READ-dict | `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `:6709` `prop = propostes.get(bm.pom_id)` | POMPlacement | READ-dict | `pom_id` | COL·LAPSA (les dues files ensenyen el mateix badge) | 🔴 | C4-ins |
| `:6716` `key={bm.id}` | BaseMeasurement | READ-list | `bm.id` | **OK** — no hi ha xoc de claus React | ⚪ | — |
| `:6721-6726` casella de selecció (`propSel.has(bm.pom_id)`) | — | READ-dict | `pom_id` | COL·LAPSA (una casella controla dues files) | 🔴 | C4-ins |
| **`:6728-6734`** guard C3 de duplicats | — | COUNT-gate | `colocat ? undefined : setCotaPreset(...)` | **PETA el cas nou: la 2a instància queda NO-CLICABLE per sempre** | 🔴 | **C4-ins · GUARD DUR** |
| `:6736-6740` tooltip `pom_cota_ja_colocat` | i18n | READ-dict | — | text que afirma la llei vella | 🟠 | C4-ins |
| `:6796` `posarProposta(bm.pom_id)` | POMPlacement | WRITE-create | `pom_id` | IGNORA-2a | 🔴 | C4-ins |
| `:7295` panell revisió IA | — | READ-dict | `selObj.pomId != null` | OK | ⚪ | C4-ins |
| `:7312-7318` panell «desar precedent» | POMPlacement | WRITE-create | `selObj.pomId != null` | COL·LAPSA (via `construirPrecedentCota`) | 🔴 | C4-ins |

#### Cobertura de `TechSheetEditor.jsx` — **7 838 línies**

| # | secció | rang | nodes |
|---|---|---|---|
| 1 | Constants, colors, eines (`CROSSHAIR_TOOLS`, `PRESET_TOOLS`) | 1-262 | 0 d'identitat |
| 2 | **Primitives de cota** | 264-450 | 6 |
| 3 | Render de taules (`buildTablePrimitives`, `graded_table` legacy) | 736-830 | 1 |
| 4 | Render Konva / transformers / nanses | 1710-2200 | 4 (tots ⚪) |
| 5 | Estat del component | 2598-2620 | 2 |
| 6 | Selecció i dimensions | 3152-3160 | 1 (⚪) |
| 7 | **Càrrega de dades** | 3330-3400 | 3 |
| 8 | Hidratació + refetch de `data_block` | 3405-3445 | 1 |
| 9 | **Efecte F1 de re-derivació d'etiquetes** | 3454-3481 | 3 |
| 10 | Eina `cota_pom` (creació per dos clics) | 4108-4149 | 2 |
| 11 | Helpers de taula (`seccionsDeFiles`, `inserirTaules`, `escalonat`) | 4765-4793 | 1 (⚪) |
| 12 | **T0 · Mesures talla base** | 4813-4862 | 2 |
| 13 | **T1a · Fitxa de treball fitting** | 4874-4944 | 4 |
| 14 | **T1b · Taula graduada** | 4950-5002 | 2 |
| 15 | **T3 · Repàs de fittings** | 5018-5073 | 2 |
| 16 | T2 · BOM · taula custom | 5076-5110 | 0 (neixen buides) |
| 17 | Capçalera (`data_block kind:'header'`) | 5155 | 0 |
| 18 | Portes de les variants de taula | 5340-5400 | 3 (⚪) |
| 19 | **Cotes col·locades / IA / propostes F2-F3** | 5424-5710 | **26** |
| 20 | Inserció de peça de patró (`inserirPeca`) | 6098+ | 0 d'identitat |
| 21 | Ribbon / z-ordre | 6400-6420 | 0 |
| 22 | **Panell de POMs (contenidor dret)** | 6605-6810 | 12 |
| 23 | Panell de propietats (vista, revisió IA, precedent) | 7285-7325 | 3 |

**Sub-registre: 79 nodes** — 38 🔴, 14 🟠, 1 🟡, 26 ⚪.
**Punts NOUS que el brief no llistava: 68** (els ja coneguts eren 11). Entre ells: tot el bloc de taules
T0/T1a/T1b/T3, `buildTablePrimitives:739`, l'estat `propostes:2613` i `pomRows:2601`, la càrrega `:3353`,
`bmById:3456` (l'únic índex sa), el bloc sencer de propostes F2 `:5466-5526`, la selecció `:5540-5549`,
`colocarCotes:5554-5577`, tot el camí IA `:5631-5703`, el guard `:5670`, la barra de revisió `:6662-6684`,
i el panell de propietats `:7295-7318`. També `cotaHandleEnds:352` i `autoPlaceCotaLabel:381`, **que són
els que reposicionen l'etiqueta — amb dues instàncies superposades, dues etiquetes idèntiques cauran
exactament al mateix offset perpendicular**.

### B · Superfície MESURES (graella unificada)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `components/model/MeasureGrid.jsx:477` `<tr key={r.pom_id}>` | (qualsevol font) | READ-list | `pom_id` com a clau React | **PETA — dues `key` idèntiques: React col·lapsa/reordena files, els inputs perden focus i valors** | 🔴 | **C4-ins · PETA** |
| `MeasureGrid.jsx:324` `podaArmada` (estat) | — | READ-dict | `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `MeasureGrid.jsx:524` `podaArmada === r.pom_id` | — | READ-dict | `pom_id` | **COL·LAPSA — armar la poda a una fila arma les dues** | 🔴 | C4-ins |
| `MeasureGrid.jsx:547` `setPodaArmada(r.pom_id)` | — | WRITE-delete (arma) | `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `MeasureGrid.jsx:327-336` `onRowDrop` → `onReorder(bm_ids)` | BaseMeasurement | WRITE-update | `bm_id` | **OK** — reordena per PK de fila | ⚪ | — |
| `MeasureGrid.jsx:131/139-141` `active.lineId` | (línia de la font) | WRITE-update | `lineId` de la font | depèn de la font | 🟠 | C4-ins |
| `components/model/CheckMeasureEditor.jsx:217-218` `lineByPom[l.pom_id] = l` | SizeCheckLine | READ-dict | `pom_id` | **COL·LAPSA — l'última línia guanya; la 1a instància perd el seu valor real** | 🔴 | C4-ins |
| `CheckMeasureEditor.jsx:220` `line = lineByPom[r.pom_id]` | SizeCheckLine | READ-dict | `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `CheckMeasureEditor.jsx:222-239` `buildRows` | BaseStage + SizeCheckLine | READ-list | emet `pom_id` + `bm_id: r.base_measurement_id` | parcialment recuperable (`bm_id` hi és) | 🟠 | C4-ins |
| `CheckMeasureEditor.jsx:143` `models.setPomRule(modelId, row.pom_id, ...)` | ModelGradingRule | WRITE-update | `pom_id` a la URL | **COL·LAPSA — escriure la regla d'una instància l'escriu a totes dues** | 🔴 | C4-ins |
| `CheckMeasureEditor.jsx:244` `sizeCheckLines.update(lineId, ...)` | SizeCheckLine | WRITE-update | `lineId` (PK) | OK | ⚪ | — |
| `CheckMeasureEditor.jsx:248/255` `baseMeasurements.update/setNoms(bmId,...)` | BaseMeasurement | WRITE-update | `bmId` (PK) | **OK** | ⚪ | — |
| `CheckMeasureEditor.jsx:259` `baseMeasurements.reorder(model.id, orderedBmIds)` | BaseMeasurement | WRITE-update | `bm_id[]` | OK | ⚪ | — |
| **`CheckMeasureEditor.jsx:388-389`** `models.desactivarPom(model.id, row.pom_id)` | BaseMeasurement | WRITE-delete | `pom_id` a la URL | **PETA/COL·LAPSA — podar una instància desactiva LES DUES (soft-delete destructiu)** | 🔴 | **C4-ins · PÈRDUA DE DADES** |

### C · Fitting · Escalat · Repàs

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `components/model/measureSources.jsx:18-28` `deriveFitting` | PieceFittingLine | READ-dict | `pomMap` per `l.pom_id`; `cells[size_label]` | **COL·LAPSA — les línies de la 2a instància sobreescriuen les de la 1a cel·la a cel·la** | 🔴 | C4-ins |
| `measureSources.jsx:78-80` `lineRegimeMap` | PieceFittingLine | READ-dict | `l.id` (PK) | OK | ⚪ | — |
| `measureSources.jsx:85` `baseMeasurements.update(bmId, ...)` | BaseMeasurement | WRITE-update | `bmId` | OK | ⚪ | — |
| `components/model/fittingGridAdapter.jsx:36-58` `buildFittingRows` | PieceFittingLine | READ-list | propaga `row.pom_id` | IGNORA-2a (rep ja col·lapsat) | 🔴 | C4-ins |
| `fittingGridAdapter.jsx:51` `pom_id: row.pom_id` (identitat de fila) | — | READ-list | `pom_id` | alimenta el `key={r.pom_id}` que peta | 🔴 | C4-ins |
| `fittingGridAdapter.jsx:136-159` `buildEscalatRows` | GradedSpec / taula-mesures | READ-list | — | IGNORA-2a | 🔴 | C4-ins |
| **`fittingGridAdapter.jsx:144`** `lineId: \`${row.pom_id}:${s}\`` | GradedSpec | WRITE-update | **`pom_id:talla` com a identitat sintètica de cel·la** | **PETA — dues cel·les diferents amb el MATEIX lineId; el buffer de `vals`/`edited` de MeasureGrid les fusiona** | 🔴 | **C4-ins · PETA** |
| `fittingGridAdapter.jsx:150` `codi: row.nom_fitxa \|\| row.pom_code` | BaseMeasurement | READ-dict | nomenclatura | COL·LAPSA visualment | 🟠 | C4-ins |
| `fittingGridAdapter.jsx:201-206` `makeFittingOnSave` | PieceFittingLine | WRITE-update | `lineId` (PK real, camí fitting) | OK al fitting; PETA a Escalat (lineId sintètic) | 🟠 | C4-ins |
| `pages/PropagatedEditor.jsx:52-61` `perLinia` Map | GradedSpec | READ-dict | `a.lineId` (= `pom_id:talla`) | **COL·LAPSA — les guardes de plausibilitat llegeixen la fila equivocada** | 🔴 | C4-ins |
| **`PropagatedEditor.jsx:68-72`** `desa()` → parseja `lineId` i crida `escalatAjustarTalla(modelId, pomId, talla, value)` | GradedSpec + MGR | WRITE-update | **`pom_id` extret del string** | **PETA — escriure una talla d'una instància escriu a l'altra** | 🔴 | **C4-ins · PÈRDUA DE DADES** |
| `PropagatedEditor.jsx:139` `models.setPomRegim(modelId, row.pom_id, nova)` | ModelGradingRule | WRITE-update | `pom_id` a la URL | COL·LAPSA | 🔴 | C4-ins |
| `PropagatedEditor.jsx:130` `models.generarGrading(modelId, ...)` | GradingVersion | CONTRACT-engine | per model | OK | ⚪ | — |
| `pages/FittingDetail.jsx:122-125` `pomMap` (`changedRows`) | PieceFittingLine | READ-dict | `l.pom_id` | COL·LAPSA (files de canvis fusionades) | 🔴 | C4-ins |
| `FittingDetail.jsx:132` `rows = [...pomMap.values()]` | PieceFittingLine | READ-list | — | COL·LAPSA | 🔴 | C4-ins |
| `FittingDetail.jsx:355` `<tr key={row.pom_id}>` | PieceFittingLine | READ-list | clau React | PETA | 🔴 | C4-ins |
| `FittingDetail.jsx:578-591` `pomMap` de la matriu principal | PieceFittingLine | READ-dict | `l.pom_id`; `cells[size_label]` | **COL·LAPSA** | 🔴 | C4-ins |
| `FittingDetail.jsx:614` `models.setPomRegim(session.model, row.pom_id, nova)` | ModelGradingRule | WRITE-update | `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `FittingDetail.jsx:616-619` refresc in-place `l.pom_id === row.pom_id` | PieceFittingLine | READ-list | `pom_id` | COL·LAPSA (marca les línies de les dues) | 🔴 | C4-ins |
| `components/model/SessionPanel.jsx:19-22` `pomMap` | PieceFittingLine | READ-dict | `l.pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `SessionPanel.jsx:29` `rows` | PieceFittingLine | READ-list | — | COL·LAPSA | 🔴 | C4-ins |
| `SessionPanel.jsx:133` `<tr key={row.pom_id}>` | PieceFittingLine | READ-list | clau React | PETA | 🔴 | C4-ins |
| `components/model/repasGridAdapter.jsx:118` `pom_id: row.pom_id` | Repàs (BaseStage+PFL) | READ-list | `pom_id` | alimenta `key={r.pom_id}` → PETA | 🔴 | C4-ins |
| `repasGridAdapter.jsx:123` `lineId: \`repas:${row.pom_id}\`` | Repàs | READ-dict | `pom_id` (read-only) | COL·LAPSA (buffer compartit, però `readonly:true` limita el mal) | 🟠 | C4-ins |

### D · EditableTable · MeasuresEntryPanel (gènesi de mesures del model)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `components/EditableTable/EditableTable.jsx:123` `models.setPomRegla(modelId, row.pom_id, {...})` | ModelGradingRule | WRITE-update | `pom_id` a la URL | COL·LAPSA | 🔴 | C4-ins |
| `EditableTable.jsx:132-146` `handleAddRow(pom)` | BaseMeasurement | WRITE-create | `pom_id: pom.id`, `id: tmp-${Date.now()}` | (sense guard) — crearia dues files, però el desat les fusiona | 🟠 | C4-ins |
| `EditableTable.jsx:151` `deltes[row.pom_id]` | GradedSpec (deltes backend) | READ-dict | `pom_id` | COL·LAPSA (les dues files ensenyen el mateix Δ) | 🔴 | C4-ins |
| **`EditableTable.jsx:163-171`** `buildPayload().measurements` | BaseMeasurement | WRITE-update | **`[{pom_id, base_value_cm, notes, nom_fitxa}]` — upsert per `pom`** | **PETA — la 2a instància sobreescriu la 1a al servidor** | 🔴 | **C4-ins · PÈRDUA DE DADES** |
| **`EditableTable.jsx:172`** `keep_pom_ids = localRows.map(r => r.pom_id)` | BaseMeasurement | WRITE-delete | **llista de poda per `pom_id`** | **PETA — si el backend alça la comporta abans que això, desar des d'aquesta pantalla PODA una de les dues instàncies en silenci** | 🔴 | **C4-ins · HA DE MOURE'S ALHORA que el backend** |
| `components/model/MeasuresEntryPanel.jsx:61` `toggleIn` (`prev.includes(pom.pom_id)`) | POMMaster | READ-list | `pom_id` en array | COL·LAPSA (un xip controla dues instàncies) | 🟠 | C4-ins |
| **`MeasuresEntryPanel.jsx:86-89`** `materialitzar-poms` amb `{pom_ids}` | BaseMeasurement | CONTRACT-api | **llista plana de `pom_id`** — impossible demanar «dues del mateix» | **PETA el cas nou: no es pot sembrar una 2a instància** | 🔴 | **C4-ins · GUARD** |
| `MeasuresEntryPanel.jsx:123-127` `pickCopySource` (còpia model→model) | BaseMeasurement | READ-list | `pom_id` per fila | IGNORA-2a | 🟠 | C4-ins |
| `MeasuresEntryPanel.jsx:139` `confirmCopy` body `{pom_ids: copyPomIds}` | BaseMeasurement | CONTRACT-api | llista plana de `pom_id` | **IGNORA-2a — copiar un model amb dues instàncies en porta una** | 🔴 | C4-ins |
| `MeasuresEntryPanel.jsx:342` `<POMChipSuggerit key={p.pom_id}>` | POMMaster | READ-list | clau React | PETA si el catàleg en repeteix | 🟡 | C4-ins |
| `MeasuresEntryPanel.jsx:70-73` fetch `taula-mesures/` | GradedSpec + BM | CONTRACT-api | `rows[]` | IGNORA-2a | 🟠 | C4-ins |

### E · ImportWizard (origen probable de les dues instàncies)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`ImportWizard.jsx:537`** `addPomManual` | ImportSession/POMExtret | WRITE-create | `if (pomsExtrets.some(p => p.pom_master_id === pm.id)) return` | **PETA el cas nou — refusa afegir el mateix POM dues vegades, EN SILENCI (només tanca el modal)** | 🔴 | **C4-ins · GUARD DUR** |
| `ImportWizard.jsx:554` `ids = actius.filter(...).map(p => p.pom_master_id)` | POMMaster | CONTRACT-api | llista plana `poms_confirmats` | COL·LAPSA server-side | 🔴 | C4-ins |
| `ImportWizard.jsx:556` `tenantOnly` per `p.ordre` | ImportSession | CONTRACT-api | `ordre` (posició de fila) | **OK** — `ordre` SÍ és instància-segur | ⚪ | — |
| `ImportWizard.jsx:571-580` gestió 409 `codi_duplicat` | POMMaster | READ-dict | `nous[p.ordre]` per `ordre` | OK | ⚪ | C4-ins |
| **`ImportWizard.jsx:630-637`** `buildTaula` → `t[p.pom_master_id] = row` | ImportSession mesures | READ-dict | **`pom_master_id` com a clau de fila de taula** | **PETA — dues files del document col·lapsen en UNA sola fila d'edició** | 🔴 | **C4-ins · PETA** |
| `ImportWizard.jsx:639-640` `setCell(pid, talla, val)` | ImportSession mesures | WRITE-update | `pom_master_id` | PETA (les dues files comparteixen cel·les) | 🔴 | C4-ins |
| `ImportWizard.jsx:643-644` `emptyCols` | — | COUNT-gate | `taula[p.pom_master_id]` | COL·LAPSA | 🟠 | C4-ins |
| `ImportWizard.jsx:645` `baseTeValors` | — | COUNT-gate | `pom_master_id` | COL·LAPSA | 🟠 | C4-ins |
| `ImportWizard.jsx:649-652` `base_values[p.pom_master_id] = v` | grading-preview | CONTRACT-engine | `pom_master_id` | **COL·LAPSA — el preview de grading rep un sol valor per POM** | 🔴 | C4-ins |
| `ImportWizard.jsx:666-672` reompliment del grading | grading-preview | WRITE-update | `grading[String(p.pom_master_id)]` | COL·LAPSA | 🔴 | C4-ins |
| **`ImportWizard.jsx:684-688`** `handleContinueMesures` → `mesures.push({pom_master_id, talla_label, valor})` | ImportSession mesures | CONTRACT-api | **`(pom_master_id, talla)`** | **PETA — identitat de mesura sense instància** | 🔴 | **C4-ins · CONTRACTE CLAU** |
| `ImportWizard.jsx:710-714` `goCrearLibrary` (mateix payload) | ImportSession mesures | CONTRACT-api | `(pom_master_id, talla)` | PETA | 🔴 | C4-ins |
| `ImportWizard.jsx:782` comptador de cel·les plenes | — | COUNT-gate | `pom_master_id` | COL·LAPSA | 🟡 | C4-ins |
| `ImportWizard.jsx:813` `defaults[d.pom_id] = 'keep_catalog'` | GradingRule (divergències) | READ-dict | `pom_id` | COL·LAPSA | 🟠 | C4-ins |
| `ImportWizard.jsx:1158-1163` render `many_to_one_hint` | — | READ-dict | `p.many_to_one` + `weak_suggestion_codi` | **UI que ENSENYA la llei vella al tècnic** | 🟠 | C4-ins |
| `ImportWizard.jsx:1314` `<tr key={p.pom_master_id}>` | — | READ-list | clau React | PETA | 🔴 | C4-ins |
| `ImportWizard.jsx:1331-1333` input de cel·la | ImportSession mesures | WRITE-update | `taula[p.pom_master_id]?.[talla]` | PETA | 🔴 | C4-ins |
| `ImportWizard.jsx:1507 / :1548` `<li key={p.pom_id}>` | — | READ-list | clau React | PETA | 🟡 | C4-ins |
| `ImportWizard.jsx:1629 / :1641 / :1646 / :1649` `conflictChoices[d.pom_id]` | GradingRule | WRITE-update | `pom_id` | **COL·LAPSA — una decisió de conflicte per a dues instàncies** | 🔴 | C4-ins |
| `ImportWizard.jsx:150-235` `ResolPanel` | POMMaster | WRITE-create/update | opera per `fila.ordre` + `pm.id` | **OK a l'eix `ordre`** — el panell de resolució ja és per-FILA | ⚪ | — |

### F · SizeMapSetup (el guard més dur del frontend)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`pages/SizeMapSetup.jsx:342-346`** `dupPomIds` | GradingRule | COUNT-gate | **compta `g.pom_id` repetits i els marca com a error** | **PETA el cas nou per construcció** | 🔴 | **C4-ins · GUARD DUR** |
| **`SizeMapSetup.jsx:427-430`** `submitCreate` bloqueja si `dupPomIds.size > 0` | GradingRuleSet | COUNT-gate | `pom_id` repetit | **PETA — el wizard no deixa crear el run** | 🔴 | **C4-ins · GUARD DUR** |
| `SizeMapSetup.jsx:356-364` `buildPayload().grading` | GradingRule | WRITE-create | `{pom_id, codi, logica, ...}` | COL·LAPSA (backend `update_or_create` per `pom`) | 🔴 | C4-ins |
| `SizeMapSetup.jsx:409` `discarded_codes` | GradingRuleSet | WRITE-create | `!g.pom_id` | OK | ⚪ | C4-ins |
| `SizeMapSetup.jsx:432-439` avís de no-resolts (`window.confirm`) | — | COUNT-gate | `!g.pom_id` | OK | ⚪ | C4-ins |
| `SizeMapSetup.jsx:732` bàner `size_map_dup_warn` | i18n | READ-dict | `dupPomIds.size` | text que afirma la llei vella | 🟠 | C4-ins |
| `SizeMapSetup.jsx:753-755` fons vermell de fila `dupPomIds.has(g.pom_id)` | — | READ-dict | `pom_id` | marca com a ERROR el cas legítim nou | 🔴 | C4-ins |
| `SizeMapSetup.jsx:770-775` badge `size_map_dup_pom` | i18n | READ-dict | `pom_id` | ídem | 🟠 | C4-ins |
| `SizeMapSetup.jsx:783-786` `size_map_many_to_one` | i18n | READ-dict | `g.many_to_one` | text que afirma la llei vella | 🟠 | C4-ins |
| `SizeMapSetup.jsx:791-795` select de vinculació al catàleg | POMMaster | WRITE-update | `pom_id` per fila `i` (índex) | **OK a l'eix índex** — es poden vincular dues files al mateix POM, i és `dupPomIds` qui ho bloqueja després | ⚪ | C4-ins |
| `SizeMapSetup.jsx:906` resum `new Set(...).size` | — | COUNT-gate | `Set` de `pom_id` | COMPTA DE MENYS | 🟡 | C4-ins |

### G · Item / catàleg / patró / altres

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`components/MeasurementBaseGrid/MeasurementBaseGrid.jsx:138`** `if (prev.some(r => r.pom_id === pom.id)) return prev` | GarmentPOMMap | WRITE-create | `pom_id` | **PETA el cas nou — «ja hi és: no duplicar», en silenci** | 🔴 | **C4-ins · GUARD DUR** (capa ITEM) |
| `MeasurementBaseGrid.jsx:66-72` `valByPom[v.pom]` | ItemBaseMeasurement | READ-dict | `pom` | COL·LAPSA | 🔴 | C4-ins |
| `MeasurementBaseGrid.jsx:164-166` `garmentPomMaps.create({garment_type_item, pom, ordre})` | GarmentPOMMap | WRITE-create | `(gti, pom)` únic | PETA (constraint backend) | 🔴 | C4-ins |
| `MeasurementBaseGrid.jsx:171-178` `itemBaseMeasurements.upsert({gti, base_set, pom, ...})` | ItemBaseMeasurement | WRITE-update | **upsert keyed `(gti, base_set, pom)`** | **PETA** | 🔴 | C4-ins |
| `components/POMBrowser/POMBrowser.jsx:133` `mappedPomIds = new Set(poms.map(p => p.pom_id))` | GarmentPOMMap | READ-dict | `pom_id` | COL·LAPSA | 🟠 | C4-ins |
| `POMBrowser.jsx:326` badge `already_assigned_short` | i18n | READ-dict | `already` | text de llei vella | 🟡 | C4-ins |
| `POMBrowser.jsx:370/390` `key={pom.map_id}` / `map_id ?? pom_code` | GarmentPOMMap | READ-list | `map_id` | **OK** (PK del mapping) | ⚪ | — |
| `components/POMBrowser/POMCatalogue.jsx:141` `key={pom.pom_id}` + `selected?.pom_id === pom.pom_id` | POMMaster | READ-list | `pom_id` | OK (catàleg, no cadena de mesura) | ⚪ | — |
| `components/SizeSetDetail.jsx:41-55` `editing[pomCodi]` | GradingRule | WRITE-update | **`pom_codi` com a clau d'estat i d'URL** | COL·LAPSA | 🔴 | C4-ins |
| `SizeSetDetail.jsx:53` `gradingRuleSets.editRule(setId, pomCodi, {increment})` | GradingRule | CONTRACT-api | `pom` a la URL | **COL·LAPSA** | 🔴 | C4-ins |
| `SizeSetDetail.jsx:221-266` render/edició per `rule.pom_codi` | GradingRule | READ-list | `pom_codi` | COL·LAPSA | 🔴 | C4-ins |
| `pages/GradingRuleSets.jsx:475` `<tr key={r.id}>` | GradingRule | READ-list | `r.id` (PK) | **OK** | ⚪ | — |
| `GradingRuleSets.jsx:483-511` columnes de POM | GradingRule | READ-list | `pom_code_global`/`pom_abbreviation` | COL·LAPSA visualment | 🟡 | C4-ins |
| `pages/TallerPatro.jsx:354-358` `patterns.poms.create({pattern_piece, pom_master, ...})` | PatternPOM | WRITE-create | `(pattern_piece, pom_master)` únic | **PETA — 409/unique** | 🔴 | C4-ins |
| **`TallerPatro.jsx:366-369`** `err_pom_duplicate` | PatternPOM | COUNT-gate | `non_field_errors` de la constraint | **PETA el cas nou i ho DIU: «una mesura, una veritat»** | 🔴 | **C4-ins · GUARD DUR** |
| `TallerPatro.jsx:883-884` `pomsAncorats` | PatternPOM | READ-list | flatMap per peça | OK | ⚪ | — |
| `components/pattern/ModelPomList.jsx:39-43` `key={f.base_measurement}` | BaseMeasurement | READ-list | **`base_measurement` (PK de fila)** | **OK** — instància-segur | ⚪ | — |
| `ModelPomList.jsx:83/111-112` `colocat = f.ancorat` → `disabled` | PatternPOM | COUNT-gate | flag del backend `model-poms` | IGNORA-2a si `ancorat` es deriva per `pom_master` | 🟠 | C4-ins |
| `components/pattern/ExportModal.jsx:250/275/342-349` | PatternPOM/GradedSpec | READ-list | `p.pom_code` com a clau React i de columna | PETA (claus duplicades) | 🟠 | C4-ins |
| `components/pattern/PatternViewer.jsx:447` `key={\`pom-${pom.id}\`}` | PatternPOM | READ-list | `pom.id` (PK) | OK | ⚪ | — |
| `components/pattern/POMPicker.jsx:76` `key={pom.id}` | POMMaster | READ-list | catàleg | OK | ⚪ | — |
| `components/pattern/RelationsPanel.jsx:48/156-186` | PatternPOM | READ-list | `p.id` | OK | ⚪ | — |
| `components/model/PropostaPromocio.jsx:25-29` `tria[i.pom_id]` | Watchpoint + POMMaster | WRITE-update | `pom_id` | COL·LAPSA (una casella, dues instàncies) | 🔴 | C4-ins |
| `PropostaPromocio.jsx:34` `watchpoints.promocionarPoms(modelId, {promocions: triats})` | CustomerPOMAlias | CONTRACT-api | llista plana `pom_id` | COL·LAPSA | 🔴 | C4-ins |
| `PropostaPromocio.jsx:48/66-71` render + botons | — | READ-list | `key={i.pom_id}` | PETA | 🟠 | C4-ins |
| `components/model/PromoteToItemButton.jsx:35` `<li key={f.pom_id}>` | promoure-a-item diff | READ-list | clau React | PETA | 🟡 | C4-ins |
| `components/model/ModelTimeline.jsx:82` `p.pom_codi \|\| p.pom_id` | MeasurementLog | READ-list | etiqueta de log | COL·LAPSA visualment | 🟡 | C4-ins |
| `components/DictionaryWizard.jsx:59/81/100` `pom_master_id` per fila `row_num` | CustomerPOMAlias | WRITE-create | **fila per `row_num`, vincle per `pom_master_id`** | OK a l'eix fila; l'àlies és del POM, no de la instància | ⚪ | C4-ins |
| `pages/CustomerDetail.jsx:266-298` `new Set(aliases.map(a => a.pom))` | CustomerPOMAlias | COUNT-gate | `pom` | OK (àlies és per POM, correcte) | ⚪ | — |
| `components/HTMTooltip.jsx:8-16` `fetch /poms/{pomId}/` | POMMaster | CONTRACT-api | `pomId` | OK (fitxa de catàleg) — **a més és codi MORT: cap consumidor a tot `frontend/src`** | ⚪ | C4-ins |
| `api/endpoints.js:96` `setPomRegim(modelId, pomId, ...)` | ModelGradingRule | CONTRACT-api | `pom/{pomId}/regim/` | COL·LAPSA | 🔴 | C4-ins |
| `api/endpoints.js:101-102` `setPomRegla` | ModelGradingRule | CONTRACT-api | mateixa URL | COL·LAPSA | 🔴 | C4-ins |
| `api/endpoints.js:105` `setPomRule` | ModelGradingRule | CONTRACT-api | mateixa URL | COL·LAPSA | 🔴 | C4-ins |
| `api/endpoints.js:108` `desactivarPom(modelId, pomId, motiu)` | BaseMeasurement | CONTRACT-api | `pom/{pomId}/desactivar/` | **PETA (soft-delete de les dues)** | 🔴 | C4-ins |
| `api/endpoints.js:123-124` `escalatAjustarTalla` | GradedSpec | CONTRACT-api | body `{pom_id, talla, valor}` | PETA | 🔴 | C4-ins |
| `api/endpoints.js:164` `promocionarPoms` | CustomerPOMAlias | CONTRACT-api | llista `pom_id` | COL·LAPSA | 🟠 | C4-ins |
| `api/endpoints.js:264-265` `gradingRuleSets.editRule(setId, pom, ...)` | GradingRule | CONTRACT-api | `regles/{pom}/editar/` | COL·LAPSA | 🔴 | C4-ins |
| `api/endpoints.js:593-596` `garmentPomMaps` CRUD | GarmentPOMMap | CONTRACT-api | `?garment_type_item & pom` | PETA | 🟠 | C4-ins |
| `api/endpoints.js:600-604` `itemBaseMeasurements.upsert` | ItemBaseMeasurement | CONTRACT-api | **«upsert keyed (garment_type_item, pom)»** (comentari literal) | PETA | 🔴 | C4-ins |
| `api/endpoints.js:813-819` `patterns.poms` CRUD | PatternPOM | CONTRACT-api | `(pattern_piece, pom_master)` | PETA | 🟠 | C4-ins |
| `utils/nomenclaturaPom.js:28-37` `nomenclaturaDePom` | qualsevol | READ-dict | cadena de fallbacks; **cap noció d'instància** | COL·LAPSA (dues instàncies, mateixa etiqueta) | 🟠 | **C4-ins — és el lloc natural per afegir el desambiguador visible** |
| `utils/nomenclaturaPom.js:55-60` `nomsDePom` | qualsevol | READ-dict | ídem | COL·LAPSA | 🟠 | C4-ins |

### Guards del frontend que bloquegen el cas nou (9)

Punts que **no col·lapsen sinó que impedeixen activament** dues instàncies. **Cap és superable per dades:
cal tocar el codi.**

1. **`pages/SizeMapSetup.jsx:342-346` + `:427-430` — `dupPomIds`.** El més dur. Compta `pom_id` repetits als
   `gradingResults` i **bloqueja `submitCreate`**. Comentari literal (`:340-341`): *«Dues files al mateix POM
   col·lapsarien a una sola regla al backend (update_or_create) → pèrdua silenciosa. Es marquen visualment i
   el create es bloqueja (backend 400); **decisió CTO: bloquejar**.»* És una **decisió humana registrada**,
   no un descuit. Mentre visqui, **cap run de client amb dues instàncies es pot crear des del wizard**.
2. **`pages/TechSheetEditor.jsx:6728-6734` — guard C3 de duplicats.** Una fila `colocat` queda
   **no-clicable** (`onClick={colocat ? undefined : ...}`). Com que `colocat` es deriva de
   `cotesColocades.has(bm.pom_id)` (`:6703`), acotar la instància A deixa la B **permanentment inacotable**.
   Sense `disabled` (per conservar el tooltip), de manera que ni tan sols hi ha senyal d'estat desactivat.
3. **`TechSheetEditor.jsx:5554-5563` `colocarCotes`** — `if (cotesColocades.has(pomId)) continue`.
4. **`TechSheetEditor.jsx:5670`** — la materialització de propostes IA descarta en silenci la 2a col·locació.
5. **`TechSheetEditor.jsx:5532-5534` `pomsSenseCota`** — la 2a instància no arriba mai a la llista de pendents.
6. **`ImportWizard.jsx:537` `addPomManual`** — `if (pomsExtrets.some(p => p.pom_master_id === pm.id)) { setShowAddPom(false); return }`.
   **Refús totalment silenciós: tanca el modal com si hagués funcionat.** És el punt on un tècnic intentaria
   declarar la 2a instància a mà.
7. **`MeasurementBaseGrid.jsx:138`** — `// ja hi és: no duplicar`. Mateix patró, **capa ITEM**.
8. **`TallerPatro.jsx:366-369` `err_pom_duplicate`** — superfície frontend d'una constraint del backend.
   El text ca/en/es diu explícitament la llei: *«Aquest POM ja està ancorat a aquesta peça: una mesura, una
   veritat.»*
9. **`MeasuresEntryPanel.jsx:86-89`** — `materialitzar-poms` amb `{pom_ids: [...]}`. Una llista plana
   **no pot expressar «dues del mateix»**. És el **camí de gènesi per defecte del model**: sense tocar-lo, la
   2a instància no es pot ni sembrar.

### Nodes que perden dades ABANS d'arribar al backend

Han de moure's **alhora** amb la comporta, **no després** — si el backend guanya la dimensió mentre el
frontend segueix enviant `pom_id` pelat, **destrueixen dades silenciosament**:

- **`EditableTable.jsx:172` `keep_pom_ids`** — llista de poda per `pom_id`. Desar des de la taula de gènesi
  **podaria** una de les dues instàncies.
- **`EditableTable.jsx:163-171` `measurements`** — upsert per `pom_id`: la 2a sobreescriu la 1a.
- **`CheckMeasureEditor.jsx:388-389` `desactivarPom`** — soft-delete per `pom_id` a la URL.
- **`PropagatedEditor.jsx:68-72` `escalatAjustarTalla`** — el `lineId` sintètic `${pom_id}:${talla}` no pot
  expressar quina instància s'ajusta.

### i18n — textos que afirmen la llei actual

Els tres idiomes, amb clau completa. Totes les línies verificades a `frontend/src/i18n/{ca,en,es}.json`.

| clau | ca | en | es | text (ca) | consumidor |
|---|---|---|---|---|---|
| `import_wizard.many_to_one_hint` | `ca.json:3609` | `en.json:3609` | `es.json:3609` | «Dues files de la fitxa apuntaven a aquest mateix POM: **cap no s'ha vinculat (la segona n'esborraria la primera)**. Suggeriment:» | `ImportWizard.jsx:1159` |
| `size_map_many_to_one` | `:2371` | `:2371` | `:2371` | «Diverses files resolen al mateix POM ({{pom}}) per descripció; **cap vinculada automàticament** — confirma-la manualment.» | `SizeMapSetup.jsx:784` |
| `size_map_dup_warn` | `:2344` | `:2344` | `:2344` | «{{count}} POM(s) vinculats per més d'un codi: **resol els duplicats abans de crear**.» | `SizeMapSetup.jsx:426` i `:732` |
| `size_map_dup_pom` | (adjacent a `:2344`) | íd. | íd. | badge de fila en vermell | `SizeMapSetup.jsx:774` |
| `pattern.err_pom_duplicate` | `:3975` | `:3975` | `:3975` | «Aquest POM ja està ancorat a aquesta peça: **una mesura, una veritat**.» | `TallerPatro.jsx:368` |
| `tech_sheet.pom_cota_ja_colocat` | `:2849` | `:2849` | `:2849` | «Ja col·locat — elimina la cota per re-acotar» | `TechSheetEditor.jsx:6737` |
| `poms.already_assigned_short` | `:3238` | (mateix bloc) | (mateix bloc) | «ja assignat» | `POMBrowser.jsx:326` |
| `poms.already_assigned` | (bloc `poms`) | íd. | íd. | forma llarga | (només definida) |
| `import_wizard.codi_duplicat_title` | `:3528` | `:3528` | `:3528` | «Codi de POM duplicat al catàleg» | `ImportWizard` (via 409) |
| `import_wizard.codi_duplicat_body` | `:3529` | `:3529` | `:3529` | text de resolució una-a-una | `ImportWizard:571-580` |
| `import_wizard.resol_err_codi_duplicat` | `:3638` | `:3638` | `:3638` | «El catàleg té més d'un POM amb el codi «{{codi}}». **Tria quin és**…» | `ResolPanel` |

⚠️ **Nota de calibratge:** `codi_duplicat_*` i `resol_err_codi_duplicat` parlen de **codis de catàleg
duplicats**, no de dues instàncies del mateix POM en un model — són un problema veí però diferent.
S'inclouen perquè la resolució del 409 (`ImportWizard:571-580`) és **la superfície on més fàcilment es
confondrien els dos conceptes** un cop s'alci la comporta. *(Regla d'or: dins amb nota.)*

**Fora d'abast confirmat** (no afirmen la llei de la cadena de mesura): `model_sheet.fitting_dup_warn`,
`taskassign.already_assigned`, `*.menu_duplicate`, `err_holiday_dup`, `counter_duplicats`.

### Nodes ja instància-segurs — la bona notícia

Hi ha **una via paral·lela sana** que ja indexa per PK de fila i **no cal tocar**:

- `TechSheetEditor.jsx:3456` `bmById = Map(bm.id)` — i `:3462` el prova **PRIMER**
- `TechSheetEditor.jsx:6704` `cotaPreset?.bmId === bm.id`
- `TechSheetEditor.jsx:6716` `key={bm.id}`
- `buildLiveCota` ja escriu `bmId` al grup (`:344`)
- `CheckMeasureEditor.jsx:229` `bm_id: r.base_measurement_id` · `:248/:255/:259` escriuen per `bmId`
- `MeasureGrid.jsx:327-336` reordena per `bm_id`
- `ModelPomList.jsx:39-43` `key={f.base_measurement}`
- `ImportWizard` `ResolPanel` i `poms_tenant_only` operen per **`p.ordre`** (posició de fila del document)
- `POMBrowser.jsx:370/390` `key={pom.map_id}`
- `GradingRuleSets.jsx:475` `key={r.id}`
- `sizeCheckLines.update(lineId)` i `pieceFittingLines.update/propagar(lineId)` — PKs reals

> **La conclusió de disseny que se'n desprèn:** el frontend **ja té una identitat de fila** (`bm_id` /
> `base_measurement`) que travessa la meitat de la cadena. La feina de C4-ins és majoritàriament
> **substituir `pom_id` per `bm_id` allà on avui s'indexa per POM**, no inventar una clau nova — excepte a
> les 4 rutes d'API que porten `pom_id` a la URL (`pom/{pomId}/regim/`, `pom/{pomId}/desactivar/`,
> `regles/{pom}/editar/`, `escalat/ajustar-talla/`), a `POMPlacement` i a `ItemBaseMeasurement.upsert`,
> **on la dimensió sí s'ha d'afegir al contracte**.

### Nodes [SOLO-CAMÍ-2] del camí 2B (7)

1. **No hi ha store global de mesures.** Només `store/auth.js`. El col·lapse per `pom_id` està **replicat a
   12 llocs independents** (`FittingDetail` ×2, `SessionPanel`, `measureSources`, `CheckMeasureEditor`,
   `MeasurementBaseGrid`, `EditableTable`, `TechSheetEditor` ×3, `SizeMapSetup`, `ImportWizard`).
   **Cap backend hi pot arribar.**
2. **`key={r.pom_id}` de React** (`MeasureGrid.jsx:477`, `FittingDetail.jsx:355`, `SessionPanel.jsx:133`,
   `ImportWizard.jsx:1314`). Amb dues instàncies són claus duplicades: React **no peta però reconcilia
   malament** — inputs que perden el focus a mig teclejar, valors que salten de fila. **És un mode de
   fallada que cap test de backend veurà mai.**
3. **`fittingGridAdapter.jsx:144` `lineId = \`${pom_id}:${talla}\``** — identitat sintètica de cel·la
   **fabricada al client**. **No existeix a cap taula.** `PropagatedEditor.jsx:69-71` la torna a parsejar amb
   `lastIndexOf(':')`. Dues instàncies produeixen lineIds idèntics i el buffer `vals`/`edited` de
   `MeasureGrid:318` els fusiona.
4. **`TechSheetEditor.jsx:5652-5659`** — el payload que va al **motor de visió** porta
   `{pom_id, code, canonical_name, client_alias, definition}`. Amb dues instàncies la IA rep **dos objectes
   idèntics** i no té cap manera de retornar-ne col·locacions diferenciades. **És un contracte engine que
   només es veu llegint el frontend.**
5. **`TechSheetEditor.jsx:2599`** — el comentari diu *«FRONTERA G1: aquesta llista serveix per DECIDIR què
   s'escriu; el que arriba al document és només el string. Cap id hi viatja.»* **Ja és fals** des de F1:
   `:4145` i `:344` escriuen `pomId` i `bmId` al `.ftt`. Vol dir que **hi ha `.ftt` desats amb `pomId` a
   dins** que caldrà migrar o degradar quan la identitat canviï — **un cost de dades que no apareix a cap
   taula de Postgres**.
6. **`components/HTMTooltip.jsx` és codi mort** (cap consumidor a tot `frontend/src`). Anotat, no tocat.
7. **`utils/nomenclaturaPom.js`** és el resolutor únic de nomenclatura i **no té cap noció d'instància**. És
   l'únic punt on es pot afegir un desambiguador visible («CH ①» / «CH ②») sense tocar 20 superfícies — el
   mòdul ja declara al capdamunt (`:19-22`) que és «la casa on han d'acabar» totes les còpies en línia.

### Recompte camí 2B

**Total: 158 nodes.**

| tipus | n | | «amb 2 inst.» | n | | risc | n | | onada | n |
|---|---|---|---|---|---|---|---|---|---|---|
| READ-dict | 52 | | COL·LAPSA | 71 | | 🔴 | 77 | | **C4-ins** | **145** |
| READ-list | 35 | | PETA | 24 | | 🟠 | 39 | | sense onada (ja instància-segurs) | 13 |
| CONTRACT-api | 24 | | IGNORA-2a | 22 | | 🟡 | 9 | | | |
| WRITE-create | 17 | | OK | 41 | | ⚪ | 33 | | | |
| WRITE-update | 15 | | | | | | | | | |
| COUNT-gate | 12 | | | | | | | | | |
| CONTRACT-engine | 4 | | | | | | | | | |
| WRITE-delete | 3 | | | | | | | | | |

> Cap node de frontend requereix una onada *anterior* a C4-ins en el sentit d'independència del contracte —
> **però 13 d'ells han de moure's en el MATEIX commit que la comporta, no després**, perquè si el backend
> guanya la dimensió mentre el frontend segueix enviant `pom_id` pelat, **destrueixen dades**: els 4 de
> pèrdua de dades llistats a la secció de guards, més els 9 guards durs que fan el cas nou inassolible
> des de la UI.

---
## II.8 · CAMÍ 2C — backoffice i zones frontereres

**Cobreix el límit declarat de `DIAGNOSI_INSTANCIES_POM.md:854`** («No auditat: el frontend del backoffice»)
+ les tres zones frontereres. **32 files.**

### TITULAR

El backoffice **no llegeix ni escriu cap taula de la cadena directament** — **0 hits** a les 18 taules en tot
`frontend-backoffice/src/` i en tot `backend/fhort/backoffice/`. Però **té un únic pont, i el pont porta a
un forat que ningú havia mirat**: el perfil de sembra que l'operador edita al backoffice dispara
`bootstrap_tenant`, un copiador que remapeja `POMMaster`, `GarmentPOMMap` i `GradingRule` **per clau
natural** — i **aquestes claus naturals no inclouen ni `capa` ni instància**.

`GarmentPOMMap` té unicitat `(garment_type_item, pom, capa)` a la BD (`pom/models.py:611`) però el copiador
la busca per `(garment_type_item, pom)` (`bootstrap_tenant.py:162`). **Això ja col·lapsa AVUI amb C1, sense
esperar cap instància**: dues pertinences exterior/folre entren al `update_or_create` de
`bootstrap_tenant.py:351`, la segona sobreescriu la primera, i el comptador ho reporta com a `updated`, no
com a pèrdua. **C1 va migrar 9 taules i 20 comportes i ningú va fer el top-up del copiador.**

### Zona 1 · `frontend-backoffice/` (28 fitxers JS/JSX a `src/`, 3 954 línies)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `frontend-backoffice/src/pages/SeedProfilesPage.jsx:34-37` | POMMaster·GarmentPOMMap·GradingRule·POMGlobal (comptadors) | READ-dict | `{block: {total, models:{Nom:n}}}` per clau de bloc — **cap clau de POM** | OK — és un `.count()` brut de files de catàleg | ⚪ | `FORA: comptador de files, cap assumpció d'unicitat` |
| `SeedProfilesPage.jsx:196-199` | ídem (render) | READ-dict | `b.total` files + tooltip `b.models` per model | OK — la xifra creix, no menteix | ⚪ | `FORA: cosmètic` |
| `SeedProfilesPage.jsx:193-194` | — (etiqueta `grading`) | READ-dict | `b.key === 'grading'` → «només rulesets CANONICAL» | OK | ⚪ | `FORA: literal d'UI` |
| `SeedProfilesPage.jsx:155` | → `SeedProfile.seleccio` | WRITE-update | `{blocks:[…]}` — decideix **que POMs i grading es copiïn** | IGNORA-2a — la UI no sap res del que el copiador farà malbé | 🟡 | `C1-ins` **[SOLO-2]** |
| `SeedProfilesPage.jsx:13-23` (`closure`) | — | READ-dict | clausura de deps duplicada al front (`SEED_BLOCK_DEPS` al back) | OK | ⚪ | `FORA: lògica de selecció` |
| `pages/TenantDetailPage.jsx:99-100` | `ModelConsumptionEvent` (models, **no** mesures) | READ-list | `client__codi_tenant` + `periodes` | OK | ⚪ | `FORA: unitat = MODEL` |
| Els **27 fitxers restants** de `src/` | — | — | — | OK | ⚪ | `FORA: 0 hits` |

**Prova de cobertura de la Zona 1:**
`grep -rniE '\bpom'` a `src/` → **0** · `mesur|measur` → **0** · `grading|gradua` → **1** (literal d'UI a
`SeedProfilesPage.jsx:193`) · `\btalla|size_|sizes` → **1** (comentari a `index.css:15`) ·
`fetch(|XMLHttpRequest|EventSource|WebSocket` → **0** (cap crida fora de la capa `api/`).
*(Verificació independent: `grep -rnE "pom_id|pomId|pom_master_id|bm_id" frontend-backoffice/src` → **0**.)*

**Inventari complet dels 27 endpoints que crida** (tots sota `/api/backoffice/v1/`, tots servits per
`backend/fhort/backoffice/urls.py`, **cap** per `pom`/`models_app`/`fitting`/`patterns`):

| origen | endpoints | servits per |
|---|---|---|
| `api/auth.js:7,10` | `auth/login/`, `auth/me/` | `backoffice/urls.py:34-35` |
| `api/tenants.js:8,11,14,17,21,24,27,30,34` | `tenants/`, `tenants/{id}/`, `tenants/{id}/update_estat/`, `tenants/{codi}/contactes/[{id}/]`, `plans/` | `backoffice/urls.py:22-23` (`views_tenants.py`) |
| `api/contracts.js:5-16` | `serveis/[{id}/]`, `contractes/[{id}/]` | `backoffice/urls.py:24-25` (`views_contracts.py`) |
| `api/invoices.js:5-41` | `facturacio/series/`, `facturacio/tipus-iva/`, `facturacio/factures/[…/preview,emetre,rectificar,linia,pdf]`, `facturacio/tancament-periode/`, `facturacio/consum/{codi}/` | `backoffice/urls.py:27-29,41-42` (`views_invoices.py`) |
| `api/legal.js:5-15` | `legal/documents/`, `legal/versions/[…/publish]`, `legal/acceptances/` | `backoffice/urls.py:30-31,43-45` (`views_legal.py`) |
| `api/seeding.js:5-12` | `perfils-sembra/[{id}/]`, **`perfils-sembra/blocs-meta/`** | `backoffice/urls.py:26` (`views_seeding.py`) |

**L'únic que arriba a la cadena és `perfils-sembra/blocs-meta/`**, i hi arriba **només com a comptador de
files** (`views_seeding.py:49-51` → `seed_block_counts`). Cap `[pom_id]`, cap `byPom`, cap `pom_master_id`,
cap mètrica de mesures.

### Zona 2 · `backend/fhort/backoffice/` (32 `.py` fora de migracions)

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `backoffice/views_seeding.py:49-51` | POMMaster·GarmentPOMMap·GradingRule·POMGlobal | COUNT-gate | delega a `seed_block_counts('fhort')`; **únic import de tenant de tot el backoffice** | OK — comptador brut | ⚪ | `FORA: comptador` **[SOLO-2]** |
| `backoffice/views_tenants.py:34-49` + `:103` | (indirecte: tota la cadena de catàleg) | WRITE-create | dispara `provision_free_tenant` **en subprocés detached** en crear un tenant Free | **COL·LAPSA** — via `bootstrap_tenant` | 🔴 | `C1-ins` **[SOLO-2]** |
| `backoffice/management/commands/provision_free_tenant.py:69` | ídem | WRITE-create | `call_command('bootstrap_tenant', schema, '--profile', pk)` | **COL·LAPSA** | 🔴 | `C1-ins` **[SOLO-2]** |
| `backoffice/models.py:446-456` | — (vocabulari) | CONTRACT-api | `Bloc.choices` ha de coincidir amb `SEED_BLOCKS` (validat per `--check-blocks`) | OK — cap eix de POM | ⚪ | `FORA: vocabulari de producte` |
| `backoffice/serializers_seeding.py:24-36` | — | CONTRACT-api | valida claus contra `Bloc.values`, mai contra el catàleg | OK | ⚪ | `FORA` |
| `backoffice/management/commands/reconcile_consumption.py:64-65,155,186,219-235` | Model·GarmentSet·ConsumptionRecord·TaskTransition | READ-list + WRITE-create | consum = **MODEL meritat**, mai POM ni mesura | OK | ⚪ | `FORA: unitat = MODEL` |
| `backoffice/management/commands/generate_invoices.py:14` | — | WRITE-create | delega a `recurring_service`; 0 imports de tenant | OK | ⚪ | `FORA` |

**Prova:** `grep -rnE '<les 18 taules>' --include=*.py backend/fhort/backoffice/` → **0 hits**.
`grep -rniE '\bpom|mesur|grading|talla|size_system|fitting'` → **5 hits, tots strings d'etiqueta** a
`models.py:437,451,453,454,456`.

### Zona 3 · `backend/fhort/tasks/`

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| **`tasks/management/commands/bootstrap_tenant.py:162`** | GarmentPOMMap | WRITE-update | clau natural `('garment_type_item','pom')` — **falta `capa`**, que la BD SÍ té (`pom/models.py:611`) | **COL·LAPSA JA AVUI (C1)** i pitjor amb instància | 🔴 | `top-up-lectors` **[SOLO-2]** |
| `bootstrap_tenant.py:163` | GradingRule | WRITE-update | `('rule_set','pom')` — coincideix amb la uniq actual | **COL·LAPSA** amb instància | 🔴 | `C1-ins` **[SOLO-2]** |
| `bootstrap_tenant.py:154` | POMMaster | WRITE-update | `('codi_client',)` — el comentari admet «no hi ha constraint»; **12 col·lisions reals** | **COL·LAPSA** ja avui | 🔴 | `consolidació-catàleg` **[SOLO-2]** |
| `bootstrap_tenant.py:331-334` | totes les anteriors | WRITE-update | construeix `lookup` només amb `key_fields` | **COL·LAPSA** — mecanisme | 🔴 | `C1-ins` **[SOLO-2]** |
| `bootstrap_tenant.py:351` | ídem | WRITE-update | `update_or_create(**lookup, defaults=values)` → la 2a fila **sobreescriu** la 1a i compta com `updated` | **COL·LAPSA en silenci** | 🔴 | `C1-ins` **[SOLO-2]** |
| `bootstrap_tenant.py:341-349` | ídem | WRITE-create | `--additive`: `filter(**lookup)`; ≥2 → salta i reporta ambigu | **IGNORA-2a** — no crea la 2a mai | 🟠 | `C1-ins` **[SOLO-2]** |
| `bootstrap_tenant.py:104-126` | 4 taules de la cadena | COUNT-gate | `m.objects.count()` per bloc | OK | ⚪ | `FORA: comptador` |
| `bootstrap_tenant.py:56-65` · `:66-78` | — | CONTRACT-api | `SEED_BLOCKS` / `SEED_BLOCK_DEPS` | OK | ⚪ | `FORA` |
| `tasks/views_b.py:970` | GarmentPOMMap | COUNT-gate | `Count('pom_maps', distinct=True)` | **la columna «#POMs» s'infla** | 🟡 | `top-up-lectors` *(ja censat)* |
| `tasks/serializers_b.py:152-155` · `:169` | GarmentPOMMap | CONTRACT-api | exposa `poms_count` al contracte del GTI | **la xifra menteix** | 🟡 | `top-up-lectors` **[SOLO-2]** *(el back estava censat; el serializer no)* |
| `tasks/urls.py:168` → `pom/s2_views.py:282-286` | GradingRule | WRITE-update | URL `regles/<str:pom_codi>/`; `.filter(Q(pom__pom_global__codi)\|Q(pom__codi_client)).first()` **sense `order_by`** | **COL·LAPSA no determinista** — edita una instància a l'atzar i retorna 200 | 🔴 | `C4-ins` **[SOLO-2]** |
| `tasks/urls.py:188-189` → `pom/s4_views.py:62,66` | GradingRule | WRITE-update | ídem amb historial | **COL·LAPSA no determinista** | 🔴 | `C4-ins` **[SOLO-2]** |
| `tasks/urls.py:190-191` → `pom/s4_views.py:90,138` → `pom/models.py:1387` | `GradingRuleHistory.pom_codi` | WRITE-create | `CharField(20)` denormalitzat, append-only | **IGNORA-2a** — l'historial de les dues instàncies és indistingible | 🟡 | `C4-ins` **[SOLO-2]** |
| `tasks/urls.py:214` → `pom/s6_views.py:86-95,105` | BaseMeasurement | CONTRACT-api | llista plana on **cada element s'identifica per `pom_id`**; el codi ho documenta com a àncora C2/Onada-1 | **COL·LAPSA** — el consumidor n'indexa i en perd un | 🔴 | `C4-ins` **[SOLO-2]** |
| `tasks/urls.py:215` → `pom/s6_views.py:130-151` | GradedSpec | CONTRACT-api | «grouped by POM» | **COL·LAPSA** | 🔴 | `C4-ins` **[SOLO-2]** |
| `tasks/urls.py:213` → `pom/s6_views.py` | POMMaster (HTM) | READ-dict | `poms/<int:pom_id>/htm/` — POM de **catàleg** | OK — l'HTM és del catàleg, no de la instància | ⚪ | `FORA: eix de catàleg` |
| `tasks/urls.py:130` → `pom/grading_views.py` | GradedSpec | CONTRACT-api | `measurements_table_view` | **COL·LAPSA** | 🔴 | `C4-ins` *(ja censat)* |
| `tasks/urls.py:284-287` → `pom/s11_views.py` | POMAlert | CONTRACT-api | rutes d'alertes | **COL·LAPSA** | 🔴 | `C4-ins` *(ja censat)* |
| `tasks/views_b.py:619` → `models_app/services.py:122-130` | — | COUNT-gate | `model_config_missing` llegeix **només camps del Model** (`garment_type_item`, `base_size_label`, `size_run_model`, `size_system`, `grading_rule_set`) | OK — **cap comptador de mesures al gate de tasca** | ⚪ | `FORA: prova al peu` |
| `bootstrap_tenant.py:500` → `models_app/master_template.py` | — | WRITE-create | `seed_master_template()` — **0 hits de POM/mesura** al fitxer | OK | ⚪ | `FORA: prova al peu` |

### Zona 4 · `backend/fhort/tenants/`

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `tenants/federation_service.py:542-552` | POMMaster | CONTRACT-engine | `(POMGlobal.codi, POMMaster.codi_client)` | **COL·LAPSA** | 🔴 | `C1-ins` *(ja censat)* |
| `federation_service.py:594-604` | BaseMeasurement | READ-list | `order_by('ordre','pom_id')` → llista de dicts amb `clau` repetida | **COL·LAPSA a l'origen** | 🔴 | `C1-ins` **[SOLO-2]** *(el previ cita `:689`/`:722`, no el lector)* |
| `federation_service.py:607-618` | ModelGradingRule | READ-list | `order_by('pom_id')`, `clau` repetida | **COL·LAPSA** | 🔴 | `C1-ins` **[SOLO-2]** |
| `federation_service.py:568-581` | POMMaster | READ-dict | `cache[clau]` + `.filter(...).first()` | **COL·LAPSA** — cau memoritzada per clau | 🔴 | `C1-ins` *(`:579` censat; el cau no)* |
| `federation_service.py:689` · `:711-719` | BaseMeasurement | WRITE-create/update | `.filter(model=twin, pom=pom).first()` | **COL·LAPSA** | 🔴 | `C1-ins` *(ja censat)* |
| `federation_service.py:722` | BaseMeasurement | WRITE-update | la 2a instància cau a `saltat['mesures'] += 1` | **PÈRDUA REPORTADA COM A ÈXIT** | 🔴 | `C1-ins` *(ja censat)* |
| `federation_service.py:732-734` | ModelGradingRule | WRITE-create | `.filter(model=twin, pom=pom).exists()` → salta | **IGNORA-2a** | 🔴 | `C1-ins` **[SOLO-2]** |
| `federation_service.py:785-800` | — | CONTRACT-api | `_text_informe`: «No s'ha trepitjat res del que ja teníeu» | **MENTEIX** — la 2a instància perduda es narra com a sobirania respectada | 🔴 | `C1-ins` **[SOLO-2]** |
| `federation_service.py:142-144` · `:149-208` | — | READ-list | canal d'ENCÀRREC: «**No viatgen mesures, regles, fitxes, fittings ni tasques**» — verificat al codi | OK | ⚪ | `FORA: prova al peu` |
| `federation_service.py:190` | GradingRuleSet | READ-dict | per `nom` — eix de **ruleset**, no de POM | OK | ⚪ | `FORA` |
| `federation_service.py:285-325` (`safata_del_studio`) | — | COUNT-gate | `n_pendents`/`n_traspassats` compten **MODELS** | OK | ⚪ | `FORA: unitat = MODEL` |
| `tenants/views_encarrecs.py:158` | (indirecte) | CONTRACT-api | única boca HTTP d'`envia_a_la_marca` | **COL·LAPSA** via el servei | 🟠 | `C1-ins` **[SOLO-2]** |
| Resta de `tenants/` (`views.py`, `models.py`, `serializers_recursos.py`, `views_recursos.py`, `views_discovery.py`, `views_auth_central.py`, `views_bescanvi.py`, `discovery_service.py`, `auth_central_service.py`, `admin.py`, `urls.py`, 3 management commands) | — | — | — | OK | ⚪ | `FORA: 0 hits` |

### Zona 5 · `commerce/` · `planning/` · `accounts/` · `i18n_content/`

| fitxer:línia | taula | tipus | clau que assumeix avui | amb 2 inst. | risc | onada |
|---|---|---|---|---|---|---|
| `commerce/models.py:160-184` (`ProductComponent`) | — | — | `pack`→`Product`, `component`→`Product`, `qty` + uniq `(pack, component)` — **cap FK a POM, cap camp de mesura**. **VERIFICAT: la hipòtesi del brief es confirma.** | OK | ⚪ | `FORA: 0 relació amb POMs` |
| `commerce/models.py:187-206` (`ProductPriceGTI`) | — | — | FK a `tasks.GarmentTypeItem` — l'**ITEM**, no els seus POMs | OK | ⚪ | `FORA` |
| `commerce/models.py:11` · `:32` | — | — | disclaimers literals: «cap camp d'aquest mòdul toca el nucli tècnic (mesures/grading/fitting/tasques)» · «mesures POM — una altra cosa» | OK | ⚪ | `FORA` |
| `planning/scheduler_service.py:145,189,223,253` | — | — | `placements` = col·locació de **TASQUES** al calendari. **Fals positiu de `POMPlacement`** | OK | ⚪ | `FORA: homònim` |
| `accounts/capabilities.py:8` | — | — | `SCHEDULE_FITTINGS` és un nom de capability; cap capability discrimina POMs | OK | ⚪ | `FORA` |
| `i18n_content/models.py:44-55` | Translation | WRITE-update | clau `(content_type, object_id, field, language)` — `object_id` és el pk de la fila | OK avui (consumidors = només `commerce.Product` i `commerce.PaymentTerms`) | ⚪ | `FORA: cap consumidor de la cadena` — **nota**: si el nom d'instància ha de ser traduïble, aquesta taula és la casa natural i **no té eix d'instància** |

### Veredicte per zona (amb la prova)

| # | zona | veredicte | prova |
|---|---|---|---|
| 1 | `frontend-backoffice/` | **NO TOCA (directament)** | 28 fitxers, 3 954 línies. `\bpom` → 0 · `mesur\|measur` → 0 · `grading\|gradua` → 1 (literal d'UI) · `fetch(` fora d'`api/` → 0. Inventari complet dels 27 endpoints (taula a dalt). **L'únic que arriba a la cadena és `perfils-sembra/blocs-meta/`, i només com a comptador.** |
| 2 | `backoffice/` (backend) | **NO TOCA directament · TOCA per delegació** | 0 hits de les 18 taules. La delegació és **un sol import** (`views_seeding.py:49`, frontera SHARED documentada a `:2-4`) i **un sol subprocés** (`views_tenants.py:46` → `provision_free_tenant.py:69` → `bootstrap_tenant`). **Cap `Count` de POMs ni de mesures a tot el mòdul de facturació.** |
| 3 | `commerce/` | **NO TOCA** | 0 hits de les 18 taules. `\bpom` → 1 hit, el disclaimer de `models.py:32`. `ProductComponent` llegit sencer: dues FK a `Product` + `qty` + tres guards de `clean()`; **cap relació amb POMs — confirmat explícitament**. L'únic pont cap al nucli és `ProductPriceGTI.garment_type_item`, que és l'**Item**. |
| 4 | `tasks/` | **TOCA — la zona més carregada del camí 2** | `views_b.py:970` no és l'únic: hi ha **el copiador sencer** (`bootstrap_tenant.py`, 3 claus naturals + el mecanisme), **el serializer** que publica `poms_count` (`serializers_b.py:152-169`), i **7 rutes** que `tasks/urls.py` munta sobre vistes de `pom/` que la diagnosi prèvia no va citar (`s2_views`, `s4_views`, `s6_views`). **El gate de tasca, en canvi, és net**: `model_config_missing` no compta mesures ni POMs. |
| 5 | `tenants/` | **TOCA (ja sabut, però amb 5 nodes nous)** | El canal de **feina** (`envia_a_la_marca`) col·lapsa a 8 punts; el canal d'**encàrrec** (`traspassa`) és net i ho diu al codi (`:142-144`). La resta de l'app (21 fitxers) és neta: 0 hits fora de `federation_service.py` i `tests_enviament_feina.py`. |
| 6 | `planning/` | **NO TOCA** | 0 hits de les 18 taules. `\bpom` → 1 hit (`tests.py:18` importa `GarmentType`). Els `placements` de `scheduler_service.py` són **col·locacions de tasques — homònim de `POMPlacement`**. |
| 7 | `accounts/` | **NO TOCA** | 0 hits. `\bpom` → 2 hits, tots dos comentaris que citen `pom/s2_serializers.py` com a precedent (`models.py:41`, `views.py:57`). |
| 8 | `i18n_content/` | **NO TOCA** | 0 hits. `\bpom` → 0. Consumidors reals de `TranslatableMixin`: **només** `commerce.Product` (`commerce/models.py:47`) i `commerce.PaymentTerms` (`:397`). |

### Recompte camí 2C

**32 nodes amb risc ≥⚪ llistats; 21 amb onada operativa.**

| tipus | n | dels quals 🔴 | | «amb 2 inst.» | n | | risc | n |
|---|---|---|---|---|---|---|---|---|
| WRITE-update | 8 | 7 | | COL·LAPSA | **14** | | 🔴 | 18 |
| WRITE-create | 5 | 3 | | IGNORA-2a | 4 | | 🟠 | 2 |
| CONTRACT-api | 9 | 5 | | OK | 20 | | 🟡 | 4 |
| READ-list | 6 | 3 | | **PETA** | **0** | | ⚪ | 14 |
| READ-dict | 6 | 2 | | | | | | |
| COUNT-gate | 5 | 0 | | | | | | |
| CONTRACT-engine | 1 | 1 | | | | | | |

> **Cap node d'aquest camí peta: no hi ha ni una constraint de BD al camí 2C. Tot el que falla, falla en
> silenci** — és exactament el patró que la diagnosi prèvia va identificar com el dominant.

**Per onada:**

| onada | n | nodes |
|---|---|---|
| `C1-ins` | 12 | copiador `bootstrap_tenant` (5) · federació (6) · disparador backoffice (2) · `SeedProfilesPage:155` |
| `C4-ins` | 6 | `s2_views:282` · `s4_views:62` · `s4_views:90` (historial) · `s6_views:86-105` · `s6_views:130` · rutes ja censades |
| `top-up-lectors` | 3 | **`bootstrap_tenant:162` (deute C1 viu)** · `views_b:970` · `serializers_b:152-169` |
| `consolidació-catàleg` | 1 | `bootstrap_tenant:154` (`POMMaster` per `codi_client`, 12 col·lisions) |
| `Onada2` | 0 | — |
| `F2-patrons` | 0 | — cap node de patrons en aquest camí |
| `FORA` (amb motiu explícit) | 14 | vegeu columna |

**[SOLO-CAMÍ-2] — 19 nodes que només es veuen des d'aquest camí** (verificat extraient tots els
`fitxer.py:línia` citats a `DIAGNOSI_INSTANCIES_POM.md` — la seva llista **no conté** `bootstrap_tenant.py`,
`views_seeding.py`, `views_tenants.py`, `provision_free_tenant.py`, `serializers_b.py`, `s2_views.py`,
`s4_views.py`, `s6_views.py`, `views_encarrecs.py`):

> `bootstrap_tenant.py:154,162,163,331-334,341-349,351` · `backoffice/views_seeding.py:49-51` ·
> `backoffice/views_tenants.py:34-49,103` · `provision_free_tenant.py:69` ·
> `tasks/serializers_b.py:152-169` · `pom/s2_views.py:282-286` · `pom/s4_views.py:62,90` ·
> `pom/s6_views.py:86-105,130` · `federation_service.py:594-604,607-618,732-734,785-800` ·
> `tenants/views_encarrecs.py:158` · `SeedProfilesPage.jsx:155`

### Les tres coses que canvien el pla (camí 2C)

**A. El deute de C1 al copiador és viu i no és teòric** [SOLO-CAMÍ-2].
`bootstrap_tenant.py:162` busca `GarmentPOMMap` per `('garment_type_item','pom')` quan la BD la té per
`('garment_type_item','pom','capa')` (`pom/models.py:611`). Avui la comporta CHECK
`pom_garmentpommap_capa_gate_c1` (`pom/models.py:615-618`) força `capa='exterior'` i **tapa el forat**.
**El dia que C4 retiri la comporta** — i el comentari del codi diu literalment «C4 la retira per migració» —
**el copiador comença a perdre files en silenci sense que cap instància hi hagi entrat.** Això no és
`C1-ins`: és `top-up-lectors`, i **té data de caducitat pròpia**.

**B. El backoffice és una boca d'escriptura a la cadena, encara que no en conegui el nom.**
`views_tenants.py:103` → subprocés detached → `provision_free_tenant.py:69` → `bootstrap_tenant --profile`.
Un ADMIN que crea un tenant Free des de la SPA del backoffice **escriu `POMMaster`, `GarmentPOMMap` i
`GradingRule`** a un schema nou, per un camí que **respon 201 sense esperar** (`views_tenants.py:39-40`) i
on l'única traça és `BackofficeActionLog`. Qualsevol pèrdua per col·lapse de clau natural passa **fora de la
petició HTTP, en un procés sense stdout** (`:47` `DEVNULL`). **El backoffice és l'única superfície del
sistema amb aquesta forma.**

**C. Dues rutes d'escriptura de grading identifiquen la regla per un codi de POM dins la URL, i resolen amb
`.first()` sense ordre** [SOLO-CAMÍ-2]. `pom/s2_views.py:282-286` i `pom/s4_views.py:62` fan
`.filter(Q(pom__pom_global__codi=pom_codi) | Q(pom__codi_client=pom_codi)).first()`. Amb dues instàncies del
mateix POM dins un ruleset, **el PATCH edita una a l'atzar i retorna 200**. És el mateix patró que el 🚩 ja
anotat per `measurements_table_view` («l'ordre és no determinista»), però **en un escriptor**, no en un
lector — i **muntat des de `tasks/urls.py`, no des de `pom/urls.py`**, que és per què cap dels dos censos
anteriors el va veure.

### Límits del camí 2C

Auditat sencer: `frontend-backoffice/src/` (28 fitxers, 3 954 línies) · `backend/fhort/backoffice/` ·
greps exhaustius de `commerce/`, `tasks/`, `tenants/`, `planning/`, `accounts/`, `i18n_content/`.
**No auditat**: el cos complet de `pom/s2_views.py`, `s4_views.py` i `s6_views.py` més enllà dels punts
d'entrada citats (viuen a `pom/`, però `tasks/urls.py` els munta — per això hi entren); `frontend/` (camí
2B); els tests. Els `tests_*.py` s'han exclòs dels recomptes, però `tenants/tests_enviament_feina.py`
confirma per fixtures que el camí de federació escriu `BaseMeasurement` i `ModelGradingRule` amb clau
`(model, pom)`.

---

## II.9 · CAMÍ 3 — DES DE LES DADES

**`los` i `public` són a ZERO a totes les taules de la cadena.** Tot el corpus viu a `fhort`.

### Recomptes per taula i schema

| taula | `fhort` | `los` | `public` |
|---|---|---|---|
| `models_app_basemeasurement` | **760** | 0 | (taula no existeix) |
| `models_app_measurementchangelog` | **289** | 0 | (no existeix) |
| `models_app_modelgradingoverride` | **0** | 0 | (no existeix) |
| `models_app_sizecheckline` | **92** | 0 | (no existeix) |
| `models_app_sizecheck` | **12** | 0 | (no existeix) |
| `models_app_pomplacement` | **2** | 0 | (no existeix) |
| `models_app_modelgradingrule` | **510** | 0 | (no existeix) |
| `fitting_gradedspec` | **2 061** | 0 | (no existeix) |
| `fitting_piecefittingline` | **153** | 0 | (no existeix) |
| `fitting_pomalert` | **0** | 0 | (no existeix) |
| `pom_garmentpommap` | **1 748** | 0 | 0 |
| `pom_itembasemeasurement` | **37** | 0 | 0 |
| `pom_itembaseset` | **1** | 0 | 0 |
| `pom_gradingrule` | **1 174** | 0 | 0 |
| `pom_gradingruleset` | **46** | 0 | **14** |
| `pom_clientmesuraperfil` | **17** | 0 | 0 |
| `pom_customerpomalias` | **336** | 0 | 0 |
| `pom_pommaster` | **370** | 0 | 0 |
| `pom_pomglobal` | **274** | 0 | **125** |
| `pom_measurementlayer` | **6** | **6** | **6** |
| `patterns_patternpom` | **0** | 0 | (no existeix) |
| `pom_pomestadisticatenant` | **0** | 0 | 0 |

**Taules de la cadena SENSE CAP FILA a staging**: `ModelGradingOverride` · `POMAlert` · `PatternPOM` ·
`POMEstadisticaTenant`. **Cap camí que les toqui s'ha exercit mai amb dades reals.**

### Qui pobla de debò cada taula

| taula | distribució |
|---|---|
| **`BaseMeasurement.origen`** (760) | **TEMPLATE 525 (69%)** · MANUAL 165 · IMPORTED 65 · FITTED 4 · CHECKED 1. **`created_by_id` NULL a les 760** |
| **`MeasurementChangeLog.context`** (289) | import 229 · manual 34 · checked 17 · fitting 7 · item_standard 2. **8 files amb `base_measurement_id` NULL** (totes «Override talla XL») |
| **`ModelGradingRule.origen`** (510) | CLIENT_RUN 241 (9 models) · CANONICAL 134 (3) · MANUAL 74 (6) · IMPORTED 61 (3) |
| **`CustomerPOMAlias.origen`** (336) | DICCIONARI 281 (0 pendents) · IMPORT 53 (**26 pendents**) · MIGRACIO 2 |
| **`POMMaster.origen_import`** (370) | (buit) 127 (2 pendents, 2 sense canònic) · `diccionari:LOS:2026-07-18` 111 (111 pendents, 6 sense canònic) · **UUID de sessió d'import 96 (79 pendents, 55 sense canònic)** · `diccionari:BRW:2026-07-13` 36 (36 pendents, 33 sense canònic) |
| **`GarmentPOMMap`** (1 748) | 100% `capa=exterior` · **238 `pendent_revisio`** · 55 items |
| **`GradedSpec`** (2 061) | 100% `exterior` · 33 versions · 88 POMs · **0 amb `is_active=False`** |
| `SizeCheckLine` 92 · `PieceFittingLine` 153 · `POMPlacement` 2 · `ItemBaseMeasurement` 37 | tots 100% `exterior` |

**Distribució de `capa`: 100% `exterior` a les 9 taules. El corpus no ha exercit mai el segon valor.**

### Mesures per model i origen (els 26 models amb mesures)

| model | codi_intern | origen → n |
|---|---|---|
| 162 | BRW-SS26-0001 | IMPORTED 14 · TEMPLATE 2 |
| 163 | BRW-FW26-0001 | MANUAL 25 |
| 164 | BRW-FW26-0002 | TEMPLATE 37 |
| 165 | BRW-FW26-0003 | TEMPLATE 37 |
| 166 | BRW-FW26-0004 | TEMPLATE 37 |
| 167 | BRW-FW26-0005 | TEMPLATE 37 |
| 168 | BRW-FW26-0006 | TEMPLATE 35 |
| 169 | BRW-FW26-0007 | TEMPLATE 29 |
| 170 | BRW-FW26-0008 | TEMPLATE 22 |
| 174 | BRW-FW26-0012 | MANUAL 21 |
| 175 | BRW-FW26-0013 | TEMPLATE 37 |
| 182 | BRW-26-SS-0002 | CHECKED 1 · FITTED 2 · IMPORTED 11 · TEMPLATE 2 |
| 185 | FTT-FW27-0001 | FITTED 2 · TEMPLATE 35 |
| 186 | FTT-CO27-0001 | MANUAL 20 |
| 188 | BRW-SS27-0001 | MANUAL 10 |
| 247 | BRW-FW26-0016 | TEMPLATE 29 |
| 267 | BRW-26-FW-0036 | TEMPLATE 37 |
| 268 | BRW-FW27-0001 | MANUAL 20 · TEMPLATE 28 |
| 269 | BRW-FW27-0002 | MANUAL 25 |
| 294 | LOS-SS27-0020 | TEMPLATE 34 |
| **396** | **LOS-SS27-0122** | **IMPORTED 20** |
| 467 | LOS-SS27-0193 | MANUAL 12 |
| 548 | LOS-SS27-0274 | MANUAL 26 |
| 1255 | LOS-ASSAIG-0007 | TEMPLATE 46 |
| 1256 | LOS-ASSAIG-0008 | IMPORTED 20 |
| 1302 | FTT-SS26-0001 | MANUAL 6 · TEMPLATE 41 |

### Anàlisi d'orfes — els camins que les dades revelen

| consulta | resultat |
|---|---|
| `GradedSpec` sense BM al model | **0** |
| `SizeCheckLine` sense BM al model | **2** (model 186, POMs 434 `FRONT RISE` i 435 `BACK RISE`) |
| `PieceFittingLine` sense BM al model | **0** |
| **`ModelGradingRule` sense BM al model** | **270 de 510 (53%) — i TOTES actives** |
| `MeasurementChangeLog` sense BM al model | **0** |
| **`POMMaster` sense cap `BaseMeasurement`** | **233 de 370 (63%)** |
| `GarmentPOMMap` amb POMs sense cap BM | **88 POMs distints** |
| **Àlies cap a POM sense cap BM** | **171 de 336** |
| `BaseMeasurement` amb `is_active=False` | **75** (la poda per `pom_id` s'ha exercit 75 cops) |
| `BaseMeasurement` amb `base_value_cm` NULL | **525** (= exactament les 525 `TEMPLATE`) |
| `GradedSpec` amb `is_active=False` | **0** |

### Les 8 files de `MeasurementChangeLog` sense `base_measurement`

| id | model | pom | context | motiu | anterior | nou |
|---|---|---|---|---|---|---|
| 198 | 186 | 275 | manual | Override talla XL | — | 53.1 |
| 199 | 186 | 275 | manual | Override talla XL | 53.1 | 53.2 |
| 200 | 186 | 275 | manual | Override talla XL | 53.2 | 53.4 |
| 201 | 185 | 273 | manual | Override talla XL | — | 62.6 |
| 202 | 185 | 273 | manual | Override talla XL | 62.6 | 62.7 |
| 203 | 185 | 273 | manual | Override talla XL | 62.7 | 62.8 |
| 204 | 185 | 273 | manual | Override talla XL | 62.8 | 62.9 |
| 270 | 268 | 278 | manual | (buit) | — | 35 |

**`ModelGradingOverride` té 0 files avui** però l'històric append-only sobreviu al seu objecte.

### Detall de les 2 files de `POMPlacement`

| id | item_fitxer | pom | view_slot | source_kind | creat_per | capa |
|---|---|---|---|---|---|---|
| 1 | 14 | 284 | front | vector | 1 | exterior |
| 3 | 14 | 379 | front | vector | 1 | exterior |

**POMs diferents al mateix slot → la unicitat mai s'ha exercit.**

### Contextos del changelog vs origen actual del BM (mostra)

El `context` del log registra l'origen **AL MOMENT del canvi**; el `origen` del BM ha canviat des d'aleshores:

| log id | model | pom | context | motiu | `origen` ACTUAL del BM |
|---|---|---|---|---|---|
| 125 | 162 | 275 | checked | Size check · check 1 | IMPORTED |
| 165 | 182 | 283 | checked | Size check · check 16 | FITTED |
| 166 | 182 | 379 | checked | Size check · check 16 | CHECKED |
| 209-215 | 182 | 379 | checked | Escalat · ajust/base S i M | CHECKED |
| 174 | 185 | 273 | **item_standard** | (buit) | **FITTED** |
| 175 | 185 | 275 | **item_standard** | (buit) | **FITTED** |

### Les tres coses que el codi amagava i les dades ensenyen

**1. El poblador dominant no és l'import: és `materialize_poms`.**
525 de 760 files són `TEMPLATE` (69%), i les 525 tenen `base_value_cm` NULL. **El node crític d'aquest camí
(`models_app/views.py:1182`) fa `.first()`.** `created_by_id` és NULL a **totes** les 760.

**2. 270 de 510 `ModelGradingRule` (53%) apunten a un POM sense `BaseMeasurement` al seu model, i totes són
actives.** La taula de regles **no se sincronitza** amb la de mesures: **les regles sobreviuen a la baixa de
la mesura**. Igual amb 2 `SizeCheckLine` (model 186). **75 `BaseMeasurement` amb `is_active=False`.**

**3. Cinc dels deu `ORIGEN_CHOICES` no tenen cap fila avui.**
`ORIGEN_CHOICES` (`models_app/models.py:591-611`): `STANDARD`, `IMPORTED`, `MANUAL`, `FITTED`, `CALCULATED`,
`TEMPLATE`, `CHECKED`, `ITEM_STANDARD`, `COPIED`, `FEDERAT`. **Sense cap fila avui: `STANDARD`,
`CALCULATED`, `ITEM_STANDARD`, `COPIED`, `FEDERAT`.** Els dos últims són els escriptors de **còpia
model→model** i **retorn de federació** — **dos dels que haurien d'estampar la instància, sense banc de
proves viu.**
*(Matís: `origen` és mutable — el changelog demostra que `item_standard` va existir i es va sobreescriure a
`FITTED`. La formulació correcta és «cap fila el porta AVUI».)*

**Nota addicional:** `_ORIGEN_TO_CONTEXT` (`models_app/signals.py:200-210`) només mapeja `IMPORTED`,
`MANUAL`, `FITTED`, `CALCULATED`, `STANDARD` i `COPIED`. **Falten `TEMPLATE`, `CHECKED`, `ITEM_STANDARD` i
`FEDERAT`**, que cauen al fallback `origen.lower()` (`:275`) — i les dades ho confirmen: hi ha contextos
`checked` i `item_standard` al log que en surten.

### Inflació de catàleg des del costat de les dades

- **233 de 370 `POMMaster` (63%) no s'han fet servir mai en cap mesura.**
- **171 de 336 àlies** apunten a POMs mai mesurats.
- **238 de 1 748 `GarmentPOMMap`** amb `pendent_revisio`.
- **283 de 370 `POMMaster` amb `pendent_revisio`** (111 + 79 + 36 + 2 + resta segons `origen_import`).
- **96 POMMaster nascuts d'una sessió d'import**, dels quals **55 sense canònic**.

### Preguntes de diagnosis anteriors que el camí 3 tanca

| pregunta | font | resposta |
|---|---|---|
| Quants `GarmentSet` hi ha a staging? | `DIAGNOSI_COMPONENTS_MULTIPLES_MESURES` §Obert | **0** |
| Quants models amb `garment_set`? | ídem | **0** |
| Quants models amb `piece_number>0`? | ídem | **0** |
| Quants models tenen >1 `SizeFitting`? | ídem | **4** |
| El bikini CRUZADO/DALIA s'ha importat? | `DIAGNOSI_MULTIPECA_DALIA` §Q2 | **No**: models 596, 545, 1109, 1108 tenen **0 mesures** |
| Hi ha POMs amb sufix de secció al codi? | ídem | **0** |
| `seccio` informada? | sprint F3 | **0 de 760** |

---
## II.10 · REGISTRE CONSOLIDAT PER ONADA

Vista transversal dels **487 nodes únics**, agrupats per l'onada assignada. Els detalls fila a fila són a
les seccions II.3–II.8; aquí hi ha la síntesi operativa.

### `C1-ins` — ESQUEMA (74 nodes)

**Les 14 unicitats + les 9 comportes CHECK + les 10 migracions** (§I.A1, §II.3-A, §II.5-BLOC 4).

**⚠️ El parany del default** (memòria `ftt-c1-capa-mesures-comporta`): la migració fa
`ADD COLUMN … DEFAULT … NOT NULL` seguit de `DROP DEFAULT` (patró Django) → **el default és del MODEL, no
de Postgres**. Codi vell + esquema nou = `NotNullViolation`. `test_capa_comporta_c1.py:84` és el pin d'això.

**Números lliures**: `models_app` **0073** · `fitting` **0020** · `pom` **0056** · `patterns` **0015**.

**Nodes de catàleg que hereten la clau** (dins per la regla d'or):
`models_app/views.py:1136,1145,1160-1230,1118-1126,1037-1060,1637-1642,1707,2494-2497,2634-2636,2789-2793,3657,3660-3661,3695-3699,3756-3765,3774-3796,3851-3852,3977-3983` ·
`extraction_views.py:1029-1035,1174-1188,1488,1667,1734,1754,1847,2047-2053,2176-2185,2201,2245,2288,2311,2364,2432,2688-2698` ·
`pom_placement_views.py:52-64,130-139` · `pom/views.py:394-400,445-511` ·
`export_losan_package.py:252-258,260-265` · `load_losan_package.py:84-100,363,379-381` ·
`author_baby_pom_maps.py:146-215` · `load_map_inline.py:144-145` · `validate_los_maps.py:77-104` ·
`consolidate_pom_catalog.py:212-215` · **`bootstrap_tenant.py:154,162,163,331-357`**.

### `top-up-lectors` — LA CLAU JA VA CRÉIXER (68 nodes)

**A · Els que ja porten `(pom, capa)` i han de créixer alhora** (§II.3-C, §II.4-B/C, §II.6-D.3).
El comentari de `fitting/graded_spec_views.py:86-92` ja adverteix que **han d'anar tots junts**:
*«si un s'ancorés i un altre no, una fila podria acabar amb l'ordre d'una capa i el nom d'una altra»*.

Nodes: `models_app/views.py:2999,3004,3010-3012,3022-3026` · `fitting/serializers.py:263-276` ·
`models_app/serializers_size_check.py:86-113` · `models_app/pom_placement_views.py:74-82` ·
`pom/s8_views.py:184-207` · `pom/s10_views.py:53-60,84-94` · `pom/services.py:729-741`.

**B · Els que porten àncora explícita `capa=exterior`** (l'àncora tapa la capa, **no** la instància):
`fitting/graded_spec_views.py:94-107` (4 mapes) · `fitting/repas_views.py:259-266` (4 mapes) ·
`pom/s6_views.py:87-105` · `pom/s11_views.py:165-171` · `models_app/views.py:3977-3983` ·
`pom/services.py:737`.

**C · 🚨 ELS DOS FORATS D'ONADA 1** — **peten amb la segona CAPA, sense esperar la instància**:

| fitxer:línia | taula | clau avui | per què va quedar fora |
|---|---|---|---|
| **`patterns/views.py:552-556`** | BaseMeasurement | `filter(model_id=fp.model_id, is_active=True)` — **SENSE àncora `capa`** | `RECENS_DELTA_ONADA1_2026-07-31.md:222-224` va declarar `patterns/*` fora d'abast |
| **`tenants/federation_service.py:593`** | BaseMeasurement | `filter(model=model, is_active=True)` a `_llegeix_patrimoni` — **SENSE àncora**, i el dict exportat (`:595-602`) **no porta `capa`** | la federació no es va mirar |

**+ 1 deute de C1 amb data pròpia**: `bootstrap_tenant.py:162` (§II.8-A).

**D · Els que ni tan sols van créixer a `(pom, capa)`**:
**`models_app/services_size_check.py:33-42`** (`pom_id` pelat; `_materialize_lines` és *completadora*) ·
**`fitting/repas_views.py:99-113`** (el `.only()` **exclou `capa`: ni arriba de BD**) ·
`fitting/repas_views.py:140-159` · **`pom/grading_views.py:119-140`** (**C7 revertit**) ·
`fitting/graded_spec_views.py:39-42,57-74` · `fitting/serializers.py:246-249` · `pom/s6_views.py:163-193` ·
`pom/services.py:394-419` · `pom/nomenclatura.py:29-42`.

**E · Comptadors i gates que canvien de SIGNIFICAT** (compten files, no POMs):
`models_app/views.py:3230` · `pom/wizard_views.py:252-257` · `models_app/services_size_check.py:90` ·
`models_app/serializers_size_check.py:37` · `fitting/serializers.py:32,112` · `pom/views.py:361-364` ·
`tasks/views_b.py:970` + `tasks/serializers_b.py:152-169` · `patterns/views.py:714` · `pom/s9_views.py:55-58` ·
`patterns/engine/grading_projection.py:184-200` · `fitting/staleness.py:112-117`.

**F · Lectors de llista sense capa que emeten dues files amb el mateix `pom_id`**:
`models_app/views.py:1620-1625,1678-1713` · `:2486-2508` · `:2957-2958` · `:3589-3591` ·
`pom/wizard_views.py:320-330` · `patterns/views.py:552-557`.

### `Onada2` — ESCRIPTORS (94 nodes)

> **FET ESTRUCTURAL:** **cap escriptor de tot el repo passa mai `capa` a un lookup ni a un `defaults`.**
> Els únics 6 hits de `capa=` fora de `models.py` són **filtres de LECTURA**. Tot escriptor viu del default
> del model, protegit només per les comportes. **L'eix INSTÀNCIA entrarà pel mateix forat exacte.**

**A · 🚨 El node que arma l'accident de C4, i els seus set germans**

| fitxer:línia | taula | clau del lookup | unicitat real | risc |
|---|---|---|---|---|
| **`pom/services.py:1033-1043` `_upsert_graded_spec`** | GradedSpec | `(grading_version_id, pom_id, size_label)` | `(grading_version, pom, size_label, **capa**)` | 🔴🔴 |
| `models_app/pom_placement_views.py:135-138` | POMPlacement | `(item_fitxer, pom_id, view_slot)` | `(item_fitxer, pom, view_slot, **capa**)` | 🔴 |
| `models_app/views.py:3756-3765` | GarmentPOMMap | `(garment_type_item, pom_id)` | `(gti, pom, **capa**)` | 🔴 |
| `models_app/views.py:3774-3796` | ItemBaseMeasurement | `(base_set, pom_id)` | `(base_set, pom, **capa**)` | 🔴 |
| `pom/views.py:445-511` (`upsert`) | ItemBaseMeasurement | `(base_set, pom_id)` | ídem | 🔴 |
| `bootstrap_tenant.py:162` | GarmentPOMMap | clau natural `('garment_type_item','pom')` | ídem | 🔴 |
| `load_losan_package.py:363` · `:379-381` | GarmentPOMMap · ItemBaseMeasurement | `{gti, pom}` · `{base_set, pom}` | ídem | 🔴 |
| `models_app/services_size_check.py:45-50` | SizeCheckLine | `create(size_check, pom=bm.pom, …)` **sense capa** | `(size_check, pom, **capa**)` | 🔴 |
| `fitting/services.py:329-338` | PieceFittingLine | clona `GradedSpec`→línia copiant **només** `pom`, `size_label`, `valor` — **ni `capa`** | `(pf, pom, size_label, **capa**)` | 🔴 |

**B · Escriptors de `BaseMeasurement` (18)**, **C · Escriptors de `ModelGradingOverride` (6)**,
**D · Signals**, **E · Fitting/propagació**, **F · Federació**, **G · Motor** — detall complet a §II.3-C/D/E,
§II.4-B/C i §II.6-D.2.

**Federació — l'exclusió que PROTEGEIX**: `federation_service.py:528-531` — **`GradedSpec` no viatja mai,
es recalcula**.

### `C4-ins` — CONTRACTES I UI (203 nodes)

**A · Els 11 payloads on `pom_id` és la clau d'un DICCIONARI exposat al client** (llista completa a §II.6).
**B · Contractes on `pom_id` va al PATH o a una llista plana** (§II.6-D.2, §II.7).
**C · Els 5 serializers sense cap camp d'eix** (§II.6-BLOC C).
**D+E · Frontend: 158 nodes**, dels quals **79 a `TechSheetEditor.jsx`** (§II.7).
**F · i18n: 11 claus** que afirmen la llei actual, als tres idiomes (§II.7-i18n).

### `F2-patrons` — MOTOR DE PATRONS (32 nodes)

**Mitigant de dades: `patterns_patternpom` = 0 files als tres schemas.** Tot `patterns/` és pre-producció:
el cost és de codi i de **format**, mai de migració de dades.

**⚠️ VEREDICTE: `patterns/` NO pot entrar sencer.** Dos nodes han d'entrar abans:
`patterns/views.py:552-556` (`top-up-lectors`) i `:544-549` (**bug viu**, §II.14-B1).
**El sostre dur és `ftt_pom_layer.py:124-127`**: mentre l'etiqueta del DXF sigui
`FTT "{codi}" {nom} = {valor} mm`, **cap instància sobreviu un roundtrip**. És **disseny de format, no
refactor**.

### `consolidació-catàleg` (58 nodes)

**El registre canònic del radi invers** — `pom/seed_data/consolidate_pom_los.py:30-34`, l'ÚNIC lloc del repo
on el radi invers sencer de `POMMaster` està enumerat, com a **strings** consumits per `getattr()`.
**Qualsevol eix nou ha de passar per aquesta llista o la consolidació el deixa enrere en silenci.**

### `FORA: <motiu>` — el que NO entra, amb el motiu (67 nodes)

| motiu | nodes |
|---|---|
| **identifica per PK de fila** | `signals.py:218-234` · `views.py:2036,2299,2328,2863,2909` · `clone_model_for_qa.py:92-102` · `annotation_views.py:134-151,554-557` · `MeasureGrid.jsx:327-336` · `CheckMeasureEditor.jsx:244-259` · `ModelPomList.jsx:39-43` · `POMBrowser.jsx:370,390` · `GradingRuleSets.jsx:475` · `sizeCheckLines.update(lineId)` · `pieceFittingLines.update(lineId)` |
| **comptador o predicat booleà** | `views.py:586,1340,1362,1555,1910,1997,2375,2451,2826,3589` · `services_size_check.py:113-119,172` · `pom/services.py:482,501,676-681` · `pom/views.py:394-400` · `s9_views.py:55-58` · `patterns/views.py:714` |
| **acte de model sencer / purga** | `views.py:2426` · `extraction_views.py:50-120` · `clone_model_for_qa.py:154-163` |
| **la regla no té instància** (decisió 3c.1, a re-confirmar) | `views.py:1957-1991,3993-4091` · `s2_views.py:221-231,282-288` · `s4_views.py:292-300` · `federation_service.py:732-742` |
| **taula fora de la cadena** | els 5 `cursor.execute` de producció (`signals.py:57-72`, `views.py:550-557,811-821`) |
| **codi mort o inabastable** | `reseed_tenant_fhort.py` sencer (guard obsolet a `:80-88`) · `HTMTooltip.jsx` (cap consumidor) · `pom_pomestadisticatenant` (0 escriptors, 0 lectors) |
| **homònim** | `planning/scheduler_service.py:145-253` (`placements` = tasques) · `commerce`/`backoffice` `.lines` · `punts_per_capa` de l'OpenAPI (capes de dibuix DXF) · `GradeTable.regles` de `patterns/` (dict del format RUL) · `.poms` com a llista de dicts extrets d'un document (~35 hits) |
| **exclusió declarada que PROTEGEIX** | `federation_service.py:528-531` — `GradedSpec` no viatja mai |
| **la instància és dins d'UNA peça** | `models_app/test_set1_creacio.py:93,118` |

---

## II.11 · CONTRAST AMB ELS CENSOS PREVIS

### II.11.1 · `DIAGNOSI_INSTANCIES_POM.md` — 167 referències `fitxer:línia`

**Totes apareixen al registre.** Cap ha desaparegut ni ha canviat de línia (mateix HEAD).
Verificació: extracció mecànica dels 167 refs i creuament contra el registre → **167/167 presents**.
El registre hi afegeix **320 nodes nous**.

**Distribució dels 167 refs per fitxer** (extracció mecànica):

| fitxer | línies citades |
|---|---|
| `models_app/views.py` | 1104-1220 · 1182 · 1417 · 1625-1643 · 1674-1687 · 1793 · 1921 · 1929 · 1943-1946 · 2313 · 2313-2314 · 2318 · 2590 · 2800 · 2882 · 2978-3024 · 3760 |
| `pom/models.py` | 32 · 33-34 · 225 · 257 · 302 · 303 · 373 · 382-383 · 422-424 · 423 · 612 · 618 · 898 · 1119 · 1171 |
| `models_app/models.py` | 572 · 588 · 637 · 654-659 · 725 · 754 · 878 · 960 · 1164 · 1336 · 1336-1338 · 1340-1343 |
| `pom/services.py` | 233 · 578-640 · 613-622 · 767-783 · 1033 |
| `pom/wizard_views.py` | 155-227 · 192-194 · 205 · 248-260 · 252-257 · 339-340 · 431-432 · 465 |
| `tenants/federation_service.py` | 542-552 · 579 · 689 · 698 |
| `models_app/extraction_views.py` | 233 · 1026-1037 · 1148-1193 · 2176-2182 · 2540-2542 · 2544-2560 · 2560 · 2693 |
| `patterns/models.py` | 91-178 · 426-436 · 430-431 · 430-432 · 432 |
| `models_app/services_size_check.py` | 33-42 · 204 |
| `models_app/pom_placement_views.py` | 52-64 · 71 · 113 · 135 · 135-138 |
| `ImportWizard.jsx` | 536-537 · 626-637 · 1194-1208 |
| `pom/grading_views.py` | 62 · 96-114 |
| `fitting/services.py` | 329-338 · 332 · 369 · 438-444 |
| `TechSheetEditor.jsx` | 276 · 4145 · 5426-5435 · 6729-6734 |
| `pom/size_map_views.py` | 54-75 · 671-695 |
| `patterns/engine/ports.py` | 60 |
| `fitting/models.py` | 220 · 227 · 400 |
| `fitting/graded_spec_views.py` | 59-74 · 86-92 · 102-106 · 123 |
| `pom/views.py` | 361-364 · 508 |
| `pom/nomenclatura.py` | 21-42 · 32-41 |
| `patterns/views.py` | 544 · 544-549 |
| `models_app/signals.py` | 299-310 |
| `fitting/serializers.py` | 263-297 · 293 |
| `fitting/repas_views.py` | 103-111 · 156-159 |
| `patterns/engine/grading_projection.py` | 179-200 |
| `models_app/serializers.py` | 409 · `serializers_size_check.py:112` |
| `models_app/tech_sheet_views.py` | 364 · 369 |
| `tasks/views_b.py` | 970 |
| `pom/grading_utils.py` | 87-100 |
| `models_app/tests.py` | 105-126 · `test_parser_excel.py:514` · `test_import_poms_{duplicats,resolucions}.py` |
| `frontend/src/utils/nomenclaturaPom.js` | 19-22 · 28-37 |

### II.11.2 · `RECENS_DELTA_ONADA1_2026-07-31.md` — 25 nodes

| grup | estat al registre |
|---|---|
| Nodes 1-11 (backend d'Onada 1) | **tots 11 presents** a `top-up-lectors` §II.10-A/B |
| Nodes 12a-16 (frontend) | **tots 5 presents** a `C4-ins` §II.7 — el RECENS els va moure a C4 per esmena; el registre ho manté |
| N1-N4 (lectors nous) | **tots 4 presents**: N1 `graded_spec_views.py:94-107` · N2 `repas_views.py:259-266` · N3 `services_size_check.py:33-42` · N4 `views.py:3977-3983` |
| X1 (`base_stages_view`, no censat preexistent) | **present** a §II.10-A |
| **5 exclosos** (`_load_base_measurements`, `_load_grading_rules`, `patterns/views:544`, `grading_projection:179`, `adapters:585-624`) | **tots 5 presents** — i **`patterns/views.py:552-556` s'hi afegeix com a forat NOU** que el RECENS no podia veure perquè va declarar `patterns/*` fora d'abast (`:222-224`) |

**Taula 1:1 del RECENS (FASE D) contra el registre:**

| # RECENS | node | línia RECENS (`3efe7f4b`) | línia registre (`72d2e579`) | on és al registre |
|---|---|---|---|---|
| 1 | `pom/services.py` `_load_model_overrides` | 711 | **729-741** | §II.10-A |
| 2 | `pom/s10_views.py` `_tolerance_map` | 43-55 | **43-60** | §II.10-A |
| 3 | `pom/s8_views.py` `tol_map` | 179-183 | **184-207** | §II.10-A |
| 4 | `pom/s11_views.py` `base_map` | 161-165 | **165-171** | §II.10-B |
| 5 | `pom/s6_views.py` BaseMeasurement | 86-90 | **87-105** | §II.10-B |
| 6 | `fitting/graded_spec_views.py` payload fitxa | 85-98 | **94-107** | §II.10-B |
| 7 | `fitting/serializers.py` `bm_data` | 259-262 | **263-268** | §II.10-A |
| 8 | `serializers_size_check.py` `bm_map` | 81-84 | **86-113** | §II.10-A |
| 9 | `pom_placement_views.py` `bm_by_pom` | 68-71 | **74-82** | §II.10-A |
| 10 | `fitting/repas_views.py` `bm_data` | 253-259 | **259-266** | §II.10-B |
| 11 | `pom/grading_views.py` `cells` | 120-141 | **119-140** | §II.10-D (**C7 revertit**) |
| 12a | `TechSheetEditor.jsx` `bmByPom` | 3452 | **3457** | §II.7-A |
| 12b | ídem | 5513 | **5512** | §II.7-A |
| 12c | ídem | 5614 | **5666** | §II.7-A |
| 13 | `TechSheetEditor.jsx` `cotaLabelDe` | 276 | **276** | §II.7-A |
| 14 | `CheckMeasureEditor.jsx` `lineByPom` | 217-218 | **217-218** | §II.7-B |
| 15 | `measureSources.jsx` `pomMap` | 18-27 | **18-28** | §II.7-C |
| 16 | `fittingGridAdapter.jsx` `lineId` | 144 | **144** | §II.7-C |
| N1 | `graded_spec_views.py` `bateig_map` | 95-98 · 116-118 | **94-107** | §II.10-B |
| N2 | `repas_views.py` `bateig_map` | 259 · 276-277 | **259-266** | §II.10-B |
| N3 | `services_size_check.py` `ja_hi_son` | 35-40 | **33-42** | §II.10-D |
| N4 | `views.py` `_sembra_step_des_dels_specs` | 3962-3964 | **3977-3983** | §II.10-B |
| X1 | `views.py` `base_stages_view` | 2992 · 3000 · 3004 | **2999 · 3004 · 3010** | §II.10-A |
| E1 | `pom/services.py` `_load_base_measurements` | 747 | **767-783** | §II.10-G |
| E2 | `pom/services.py` `_load_grading_rules` | 682 | **699-712** | §II.10-G |
| E3 | `patterns/views.py` `ancorats` | 544-548 | **544-549** | §II.4-A.5 + §II.14-B1 |
| E4 | `grading_projection.py` `poms_per_id` | 179 | **179** | §II.4-A.3 |
| E5 | `patterns/adapters.py` | 585-624 | **587, 623** | §II.4-A.2 |

⚠️ **Deriva de línia:** el RECENS és de HEAD `3efe7f4b`; aquest registre és de `72d2e579`. La deriva màxima
observada és de **+20 línies** (`pom/services.py`). **Les línies de `patterns/` no s'han mogut** (544→544,
179→179), ni les de `pom/s10_views.py` (43→43).

### II.11.3 · Reports d'Onada 1/1b — els 9 commits vius

Els **11 fitxers tocats** (§II.1) són la base de `top-up-lectors`. **`pom/grading_views.py` no hi és:
C7 revertit** (`6b431865`) — per això `:119-140` apareix a §II.10-D («ni tan sols va créixer»).
El 🚩 de l'ordre no determinista de `measurements_table_view` **segueix viu i no depèn de la instància**.

### II.11.4 · Tests que codifiquen la llei — el pin del tram

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
| `test_copia_model_a_model.py` (16) · `tests_sembra_grading.py` (55) · `test_lectors_capa_onada1.py` (5) · `fitting/test_repas.py` · `pom/test_d2_nomes_override.py` · `test_step_conserva_valors.py` · `test_guarda_rang_mesura.py` · `test_g6_{segell,grading_gates}.py` · `test_g1_graduacio.py` · `test_beach_columnes_descartades.py` · `test_parser_excel.py` · `fitting/{tests,test_graded_table_regla,test_g6_estalitud}.py` · `tenants/tests_enviament_feina.py` | forma del payload i fixtures per `(model,pom)` | COL·LAPSA / PETA |

**Patró endèmic**: `{s.size_label: s.valor for s in …filter(pom=…)}` a **7 fitxers**
(`test_g6_segell.py:91` · `test_step_conserva_valors.py:137` · `test_guarda_rang_mesura.py:115` ·
`test_d2_nomes_override.py:96` · **`test_g6_grading_gates.py:142,179`, que ni filtren per POM** ·
`fitting/test_repas.py:128` · `test_graded_table_regla.py:102-169`). **Cap peta: col·lapsen i passen verds
amb un valor arbitrari.**

**Comptadors durs — la sonda més honesta** (es posen vermells de seguida i diuen quantes files sobren):
`test_g6_segell.py:209,219` · `test_g6_grading_gates.py:141,178` · `test_d2_nomes_override.py:165` ·
`tests_sembra_grading.py:869,882,974`.

**Forat de cobertura: `fitting.POMAlert` no té CAP test a tot el repo** (0 hits).
**91 fitxers de test · 39 toquen la cadena · 52 no.**

---

## II.12 · COBERTURA DELS LÍMITS DECLARATS

`DIAGNOSI_INSTANCIES_POM.md:851-858` declarava quatre límits. Aquí queden coberts, secció per secció.

### II.12.1 · «No auditat: el frontend del backoffice» → **COBERT · NO TOCA (amb prova)**

Vegeu **§II.8, Zona 1 i Zona 2**, amb l'inventari complet dels 27 endpoints i les proves de grep.
**⚠️ PERÒ el backoffice és una BOCA D'ESCRIPTURA per delegació** (§II.8-B).

### II.12.2 · «No auditat: `patterns/` complet» → **COBERT · 32 nodes + 1 forat d'Onada 1 + 1 bug viu**

Recorregut: `models.py`, `views.py`, `annotation_views.py`, `serializers.py`, `adapters.py`, `export.py`,
`svg.py`, `engine/ports.py`, `engine/grading_projection.py`, `engine/ftt_pom_layer.py`,
`engine/aama_writer.py`, `engine/roundtrip.py`, `engine/operations.py`, `tests.py`. Veredicte a §II.4-A.

### II.12.3 · «Pot faltar-hi algun node, sobretot a `management/commands/`» → **COBERT · 71/71**

Vegeu **§II.5-BLOC 1**: 34 toquen la cadena · 7 `__init__.py` buits · **30 citats un per un com a nets**.
**SQL cru: NO és un vector** — `.raw(` → 0, `RunSQL` → 0, els 5 `cursor.execute` de producció toquen
`models_app_model`/`_garmentset` (§II.5-BLOC 3).

### II.12.4 · Límit NOU trobat en cobrir els altres — **el green flag d'OpenAPI és cec**

Verificació directa: `curl -s http://127.0.0.1:8001/api/schema/ -H "Host: staging.fhorttextile.tech"` →
**200, 743 057 bytes, 364 paths.**

| | n |
|---|---|
| paths totals | **364** |
| paths de la cadena (heurística sobre el path) | **80** |
| … amb **`'200': description: No response body`** | **54 (68%)** |
| … amb `$ref`/`properties` (forma declarada) | **26** |
| … cap de les dues | **0** |

**Mostra dels 54 cecs:**
`/api/v1/base-measurements/{bm_id}/noms/` · `/api/v1/base-measurements/{id}/` ·
`/api/v1/fitting/model/{model_id}/repas/` · `/api/v1/fitting/{sf_id}/graded-table/` ·
`/api/v1/garment-pom-maps/{id}/` · `/api/v1/grading-rule-sets/{id}/` ·
`/api/v1/grading-rule-sets/{rule_set_id}/export/csv/` · `…/historial/` · `…/regles/` ·
`…/regles/{pom_codi}/` · `…/regles/{pom_codi}/editar/` · `/api/v1/grading-rules/{id}/` ·
`/api/v1/import-sessions/cribratge/` · `…/{token}/confirmar/` · `…/extraccio/` · `…/grading-preview/` ·
`…/library-prefill/` · `…/mesures/` · `…/poms/` · `…/talles/` · `…/teixit/` ·
`/api/v1/item-base-measurements/{id}/` · `/api/v1/item-base-sets/{base_set_id}/acte-canonic/` ·
`/api/v1/item-base-sets/{id}/` · `/api/v1/item-fitxers/{item_id}/pom-placements/` ·
`/api/v1/models/{model_id}/base-measurements-units/` · `/api/v1/models/{model_id}/base-measurements/` ·
`/api/v1/models/{model_id}/base-measurements/reorder/` · `/api/v1/models/{model_id}/base-stages/` ·
`/api/v1/models/{model_id}/taula-mesures/` … *(i 24 més)*.

**Comprovació literal** de `GET /models/{model_id}/base-stages/` a l'esquema:
```yaml
      responses:
        '200':
          description: No response body
```

> **Conseqüència operativa:** el green flag «**OpenAPI 0 diffs fins C4**» (`PLA_EXECUCIO_TRAM_C.md:90`)
> **no pot detectar un canvi de forma de payload** als 54 endpoints on el canvi seria més probable.
> **Ha estat verd per construcció, no per absència de canvi.**
> El que sí que ho vigila: el **fumeig md5 contra T0'** i **`onada1_dump_superficies.py`** (§II.15).

**Verificat també:** el contracte **no exposa `capa` enlloc**. Les **28** aparicions de la cadena `capa` a
l'esquema són `capability`/`capacitat`, més **un `punts_per_capa`** que és de `patterns` (capes de dibuix
del DXF, veí d'`unknown_layers` i `bounding_box_mm`) — **homònim**. Això **confirma que C1 va quedar
invisible al contracte, com el pla prometia**.

### II.12.5 · Cobertura dels 12 `urls.py`

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

## II.13 · ELS NODES QUE INVERTEIXEN LA LLEI

No col·lapsen: **bloquegen activament** el cas que la instància vol legitimar. **No s'adapten: s'han de
re-decidir.** Tots porten **acta escrita al codi**, i **els casos reals que citen SÓN el cas de dues
instàncies**.

| # | fitxer:línia | què fa | l'acta |
|---|---|---|---|
| 1 | `pom/size_map_views.py:54-75` + `:671-695` | `by_pom` ≥2 → **400, bloquejar abans d'escriure res** | *«Decisió CTO: BLOQUEJAR»*. Casos: LOS `H.11`/`H.16` |
| 2 | `models_app/extraction_views.py:1148-1193` | `_apply_many_to_one_guard`: desvincula **totes dues** files i les desactiva | `:1155-1171`: *«el destí és `BaseMeasurement`, únic per `(model,pom)`: per legítim que sigui l'àlies, la segona esborra la primera»* |
| 3 | `models_app/extraction_views.py:1734,1753-1756` | error **`pom_ja_usat`**: un POM ja pres per una fila no es pot vincular a una segona | `:1718` |
| 4 | `pom/services.py:613-622` | guard `ja_reclamat` → `pendent_revisio=True` | casos reals BRW `'F'`/`'FF'`→POM 389, `'U'`/`'U2'`/`'U3'`→POM 439 |
| 5 | `seed_losan_rules_v2.py:128-134` | `seen[pom.codi_client]` → «2n àlies → mateix POM = col·lisió, skip» | docstring `:12` |
| 6 | `patterns/models.py:430-437` + `patterns/tests.py:1865` | constraint + test | *«Dos ancoratges del mateix POM a la mateixa peça serien dues veritats sobre la mateixa mesura»* |
| 7 | `frontend/SizeMapSetup.jsx:340-346` + `:427-430` | `dupPomIds` **bloqueja `submitCreate`** | *«Dues files al mateix POM col·lapsarien… pèrdua silenciosa. **Decisió CTO: bloquejar**»* |

**Guards de frontend que fan el cas nou inassolible des de la UI (9)** — §II.7:
`SizeMapSetup.jsx:342-346,427-430` · `TechSheetEditor.jsx:6728-6734` (fila **no-clicable per sempre**),
`:5554-5563`, `:5670`, `:5532-5534` · **`ImportWizard.jsx:537`** (refús **silenciós**) ·
`MeasurementBaseGrid.jsx:138` · `TallerPatro.jsx:366-369` · `MeasuresEntryPanel.jsx:86-89`.

**⚠️ Nodes de frontend que perden dades ABANS d'arribar al backend** — han de moure's **al MATEIX commit**
que la comporta, no després: `EditableTable.jsx:163-171` i **`:172` (`keep_pom_ids`)** ·
`CheckMeasureEditor.jsx:388-389` (`desactivarPom`) · `PropagatedEditor.jsx:68-72` (`escalatAjustarTalla`).

**Tests que codifiquen la llei al revés** (§II.11.4): `models_app/tests.py:52,84,189,317` ·
`pom/tests.py:74,92,64,104` · `patterns/tests.py:1865` — **PETEN i han de petar**.

---

## II.14 · BUGS VIUS, INDEPENDENTS DEL TRAM

Trobats en traçar el radi. **No es toquen; s'anoten** (llei del `CLAUDE.md`, «Zones intocables»).

**B-1 · `patterns/views.py:544-549` ja col·lapsa AVUI.**
`ancorats = {p.pom_master_id: p for p in PatternPOM.objects.filter(pattern_piece__pattern_file=fp)}` —
indexat per POM sobre **tot el PatternFile**, però la constraint és `(pattern_piece, pom_master)`: dues
peces del mateix fitxer (davanter/darrere, dreta/esquerra) **poden** ancorar legalment el mateix POM, i el
dict en perd una. `model-poms` diria «ancorat» **assenyalant la peça equivocada**.

**B-2 · `cleanup_losan_old.py:32` — accessor inexistent.**
`SIZEDEF_EXTERNAL = {'regles_base', 'base_for_items'}`, però l'accessor real d'
`ItemBaseSet.base_size_definition` és **`base_set_for_items`** (`pom/models.py:672`, verificat).
`'base_for_items'` **no existeix**. El filtre de `:112` el descarta i el guard «cap referència viva →
esborro» **mai** salta per una `SizeDefinition` que és talla base d'un BaseSet actiu.
*Mitigant:* l'FK és `PROTECT`, o sigui que l'esborrat rebotaria amb `ProtectedError` — **el dany és que el
guard falla la seva funció** (aturar-se abans, amb un missatge clar) i el command mor amb una excepció d'ORM
en lloc del `CommandError` explicatiu.

**B-3 · `pom/s10_views.py:136-152` col·lapsa doble ja avui.**
`POMAlert.update_or_create(model, pom_id, size_fitting)` **sense `size_label`**: una sola alerta per
`(model, pom, sf)` **tapa totes les talles**. *(POMAlert = 0 files a staging, §II.9.)*

**B-4 · `bootstrap_tenant.py:61-62` — buit de sembra.**
`ItemBaseSet`, `ItemBaseMeasurement`, `CustomerPOMAlias` i `POMEstadisticaTenant` **no són a cap
`SEED_BLOCK`**. Un tenant nou neix amb pertinences i regles, **sense cap valor base d'item ni cap àlies de
client**.

**B-5 · Trampa de nom: `base_measurements` és una col·lisió a TRES bandes** (verificat):
`pom/models.py:836` (`GarmentTypeItem` → `ItemBaseMeasurement`) · `models_app/models.py:613`
(`Model` → `BaseMeasurement`) · `:614` (`POMMaster` → `BaseMeasurement`).
A `consolidate_pom_los.py:31`, `getattr(pom, 'base_measurements')` resol a **models_app** — correcte,
perquè `ItemBaseMeasurement` viatja separat com a `'item_base_measurements'`. **Però
`GarmentTypeItem.base_measurements` (el de `pom`) NO té CAP call site a tot el repo.** Qualsevol auditoria
per grep del nom **barreja tres relacions distintes**.

**B-6 · `repair_fitting_20260710.py:123-136` omet `codi_client`.**
`ClientMesuraPerfil` té unicitat `(codi_client, garment_type, pom, talla)`, i el filtre del command és
`(garment_type_id, talla, pom_id__in)` — **omet el 1r camp de l'unique**. Bug preexistent, agreujat per la
instància.

**B-7 · `_ORIGEN_TO_CONTEXT` incomplet** (`models_app/signals.py:200-210`).
Falten `TEMPLATE`, `CHECKED`, `ITEM_STANDARD` i `FEDERAT`; cauen al fallback `origen.lower()` (`:275`).
**Les dades ho confirmen**: hi ha contextos `checked` i `item_standard` al log que en surten (§II.9).

---

## II.15 · EINES QUE EL TRAM HA DE REUSAR

`backend/scripts_tmp/` (fora de git): 17 fitxers, **6 reusables tal qual** canviant el nom de columna.
Detall complet a §II.5-BLOC 6.

| fitxer | què fa | com es reusa |
|---|---|---|
| `c1_audit_counts.sql` | 3 schemas × 10 taules; detecta la columna via `information_schema` → **funciona abans i després de la migració** | canviar `capa`→`instancia` a 3 línies = cens T2/T5 |
| `c1_audit_constraints.sql` | 4 blocs contra `pg_constraint`. *«django-tenants pot donar un OK enganyós: això llegeix el catàleg de Postgres directament»* | **l'única eina que verifica que una migració ha arribat als 3 schemas** |
| `c1_fumeig_base_stages.py` + `c1_base_stages_T0prima_2026-07-31.json.txt` | línia base T0' viva, **md5 `6e3a980f624215f121ef6abe7ed7a8ae`**, models 467/548/182 | el termòmetre de «cap canvi de contingut». ⚠️ comparar **sense la primera línia** del shell de Django |
| `c1_fumeig_convivencia.py` | 4 superfícies post-revert; **B escriu dins un `atomic()` que es desfà** | el patró per verificar que `save()` sap posar una columna NOT NULL sense default de columna |
| `onada1_dump_superficies.py` | **11 superfícies, una per commit**; comparació contra un `git worktree` al commit pre-sprint amb la MATEIXA BD | **és el cens de lectors EXECUTABLE** |
| `models_app/test_lectors_capa_onada1.py:35,43-52,84` | `comporta_alcada()`: `ALTER TABLE … DROP CONSTRAINT` **dins savepoint** + fila germana + rollback | **el harness de dues files germanes, ja provat**. Verificat que DETECTA el col·lapse |

**Les tres peces de mètode que el repo ja té provades** (§II.4-fets):
(a) **Harness de dues files germanes** · (b) **Resposta canònica a l'ambigüitat** (`base_set_ambigu` 409 amb
candidats, `pom/views.py:468-490`; i `_alies_unics_del_customer`, `patterns/views.py:135-146`, que **es
calla** quan no pot desambiguar) · (c) **Discriminant ordinal ja existent** (`PatternPiece.ordinal`,
`patterns/models.py:212`, nullable, provat a `patterns/tests.py:4795`). **Calcar-les, no inventar-ne una
quarta.**

---

## II.16 · RECOMPTES FINALS

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

`READ-dict` **118** · `CONTRACT-api` **96** · `READ-list` **79** · `WRITE-update` **63** ·
`CONTRACT-engine` **55** · `WRITE-create` **51** · `COUNT-gate` **47** · `WRITE-delete` **22**.
*(Els nodes de tipus compost compten a cada tipus; total d'ocurrències 531 sobre 487 files.)*

### Per risc

🔴 **255** · 🟠 **112** · 🟡 **62** · ⚪ **58**.

### Per camí (aportació bruta i única)

| camí | investigador | files brutes | nodes únics | [SOLO] |
|---|---|---|---|---|
| 1A | `models_app` | 176 | — | 12 |
| 1B | `fitting` · `pom` · `patterns` | 285 | — | 41 |
| 1C | commands · signals · SQL · migracions · tests · scripts | 117 | — | 8 |
| **Camí 1 total** | | **578** | **352** | **49** |
| 2A | contractes · urls · OpenAPI · serializers | 63 | — | 18 |
| 2B | frontend principal | 158 | — | 7 |
| 2C | backoffice i frontereres | 32 | — | 19 |
| **Camí 2 total** | | **253** | **206** | **37** |
| 3 | dades | — | (no emet nodes de codi) | 3 fets exclusius |
| **TOTAL** | | **831** | **487** | **86** |

---

## II.17 · LÍMITS D'AQUEST DOSSIER

- **Cap proposta de fix**, per encàrrec. Les assignacions d'onada són **classificació**, no pla d'execució:
  l'ordre i el tall dels commits són **decisió humana (Patró C)**.
- **La deriva de línia és real.** Tot està verificat a HEAD `72d2e579`. Els censos previs són de `3efe7f4b`
  (RECENS) i anteriors; les línies s'han re-verificat (taula 1:1 a §II.11.2), però **una sessió de `dev`
  concurrent pot moure-les** (memòria `ftt-dev-concurrent-git`). **Abans de cada onada cal un re-cens delta**
  com el que el pla ja preveu.
- **Els recomptes són de cens per grep + lectura de rang + recorregut d'`urls.py`**, no d'anàlisi estàtica
  amb graf de crides. La deduplicació és per `fitxer:línia`; nodes molt propers dins la mateixa funció poden
  haver-se fusionat en una fila. Les xifres «487 únics» i «831 brutes» són **estimacions de consolidació**,
  no un recompte automàtic.
- **Les afirmacions més portants s'han llegit literalment** en aquesta investigació:
  `pom/services.py:1023-1045` · `:767-783` · `models_app/services_size_check.py:33-42` ·
  `tenants/federation_service.py:542-552,583-612` · `patterns/models.py:426-437` ·
  `patterns/views.py:550-560` · `bootstrap_tenant.py:150-170,328-355` · `pom/models.py:608-620,670-674` ·
  `models_app/test_seccio_captura.py:140-172` · `pom/s2_views.py:278-292` · `pom/s4_views.py:58-70` ·
  `pom/seed_data/consolidate_pom_los.py:25-40` · `fitting/repas_views.py:99-113` ·
  `models_app/views.py:3228-3232` · `models_app/models.py:588-700,845-860,925-940,1130-1140` ·
  `frontend/src/pages/SizeMapSetup.jsx:338-348` · `ImportWizard.jsx:535-539` · `MeasureGrid.jsx:477` ·
  `fittingGridAdapter.jsx:142-146` · `cleanup_losan_old.py:30-34`.
  **L'OpenAPI, els recomptes de BD, els números de migració i els comptadors mecànics de grep són
  verificació directa, no delegada.**
- **No auditat**: el graf de crides complet de `patterns/engine/` (només els punts d'ancoratge citats);
  els fitxers `.ftt` ja desats amb `pomId` a dins (**cost de dades fora de Postgres**, detectat a
  `TechSheetEditor.jsx:2599`, on el comentari *«Cap id hi viatja»* **ja és fals** des de F1); el cost d'UI de
  cap forma (requereix maqueta, **llei 3c.5**); el cos complet de `pom/s2_views.py`, `s4_views.py` i
  `s6_views.py` més enllà dels punts d'entrada citats.
- **La classificació de termes del diccionari (§I.C3, §I.C5) és `💡 PROPOSTA`**: els **recomptes** són FET,
  la **dimensió** és decisió de la Montse. Les tres ambigüitats de §I.C4 **no es poden resoldre
  automàticament**.
- **El corpus de la FASE C és petit i concentrat**: 760 `BaseMeasurement` en **26 models de 1 055**, i tot a
  `fhort` (`los` en té 0). Les freqüències són sòlides per al **catàleg** (370 + 274 noms) i més febles per
  a l'**ús real en models** (207 `notes` + 206 `nom_fitxa`).
- **`ModelGradingRule` és una decisió oberta que aquest dossier NO tanca.** El docstring
  (`models_app/models.py:900-914`) argumenta que la regla no porta `capa` perquè «el folre creix el mateix
  que l'exterior». **¿Val el mateix per a la instància?** Si dues instàncies del mateix POM tenen deltes
  diferents, l'argument cau i `unique_together=[('model','pom')]` ha de créixer.
  `test_capa_comporta_c1.py:108-116` ho vigila **per la porta de la capa**.

---

## DOCUMENTS RELACIONATS

| document | què hi ha |
|---|---|
| `docs/diagnosis/DIAGNOSI_INSTANCIES_POM.md` | la diagnosi original (font de la PART I) |
| `docs/diagnosis/MAPA_TOC_INSTANCIA.md` | el registre condensat (font de la PART II) |
| `docs/diagnosis/PLA_EXECUCIO_TRAM_C.md` | el pla del tram (C2 onades · C3 motor · C4 comporta) |
| `docs/diagnosis/RECENS_DELTA_ONADA1_2026-07-31.md` | els 25 nodes d'Onada 1, contrastats a §II.11.2 |
| `docs/diagnosis/DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md` | la mateixa clau amb el nom `component` (21/07) |
| `docs/diagnosis/DIAGNOSI_MULTIPECA_DALIA.md` §Q2 | el multi-peça i el límit ja declarat al codi |
| `docs/diagnosis/DIAGNOSI_NOMENCLATURA_POM_CAMPS` *(veg. memòria)* | semàntica de `codi_client` ≠ `client_alias` ≠ `pom_code_global` ≠ `nom_fitxa` |
| `ARQUITECTURA_FACETES_I_CAPES.md` §3b/3c/3d | les decisions de capa del 30/07 |

---

*Dossier complet · Patró A (diagnosi) + Patró A profund (registre) · triangulació de tres camins ·
read-only absolut · cap fitxer de codi tocat · cap escriptura a BD · cap command executat.*








