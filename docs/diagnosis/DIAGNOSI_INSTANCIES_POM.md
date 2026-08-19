# DIAGNOSI — INSTÀNCIES DE POM + COLLITA DE DICCIONARI

Data: 2026-07-31 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` (HEAD `72d2e579`)
BD auditada: `ftt_staging` @ 5433, schemas `fhort` · `los` · `public`.

**Abast.** Mesurar l'ona expansiva de passar la identitat d'una mesura de `(model, pom[, capa])` a
`(model, pom, capa, INSTÀNCIA)`, comparar el cost de les tres formes candidates, i **collir del corpus
real** el diccionari inicial de termes. Executada després de l'Onada 1b del Tram C
(`docs/diagnosis/PLA_EXECUCIO_TRAM_C.md` §PROPOSTA EN DEBAT).

**Marc donat (Agus, no es qüestiona):** identitat = POM + capa + INSTÀNCIA (columna estructural,
contingut lliure per model) · qualitats descriptives = tags, mai en clau · nomenclatura d'instància
obligada diferent dins del model · escala casa→client→model · anglès com a llengua pivot · diccionari
únic de casa collit del corpus · aprenentatge directe del wizard al diccionari.

**Convenció.** Cada afirmació porta `fitxer:línia` o la consulta SQL que la sosté.
**"NO EXISTEIX" = confirmat absent** (grep exhaustiu o `SELECT` amb resultat 0), mai especulat.
Les xifres de BD són d'aquesta sessió. Propostes marcades `💡 PROPOSTA (a validar)` i separades dels
fets. **CAP proposta de fix** — les decisions són humanes (Patró C).

**Res tocat:** cap escriptura a BD, cap fitxer del repo modificat, cap migració, cap restart.
L'única escriptura és aquest document.

---

## RESUM EXECUTIU

**1. La instància ja existeix a producció — disfressada de catàleg.**
El sistema no sap dir «dues instàncies del mateix POM», i el que fa en canvi és **encunyar un POM nou
al catàleg amb el qualificador enganxat al nom**. A `fhort`: **43 `POMMaster` i 27 `POMGlobal`** porten
`RELAXED`/`EXTENDED`/`STRETCHED` al nom, agrupats en **25 troncs** (§C2). El model **396 LOS-SS27-0122
EXPLORER** té avui `WAIST WIDTH` dues vegades (21 / 26,5 cm) i `LEG OPENING` dues vegades (7,5 / 9,5 cm)
— quatre `BaseMeasurement` sobre quatre POMs diferents que semànticament són dos (§D1). **Aquest és el
workaround viu, i té cost: 120 `GradedSpec` i 20 `ModelGradingRule` duplicats només en dos models.**

**2. L'ona expansiva no són les constraints: és el `dict {pom_id: …}`.**
Cens: **14 constraints UNIQUE amb `pom_id`** (9 amb capa, 5 sense) + **9 comportes CHECK `*_capa_gate_c1`**
+ **~45 escriptors/lectors**, dels quals **28 són 🔴 col·lapse silenciós**. Les constraints peten i es veuen;
els **24 diccionaris `{pom_id: …}` en memòria** no peten: **pinten** — el nom exacte ja és al codi a
`models_app/pom_placement_views.py:71`. Tres fitxers decideixen la viabilitat (§A6).

**3. El terreny de la nomenclatura és net avui, però té vuit portes sense pany.**
`nom_fitxa` és l'únic candidat real a nom d'instància (`CharField(20)`, del model, curt). Sobre 760 files:
**206 informades, 0 parells `(model, nom_fitxa)` duplicats** — una constraint d'unicitat per model passaria
avui sense arreglar cap fila. Però `nom_fitxa` té **8 escriptors, cap amb `strip()` ni guard de col·lisió**,
i el concepte té **5 cascades de precedència diferents** al sistema (§A3).

**4. La política vigent diu exactament el contrari del que INSTÀNCIA vol.**
`pom/size_map_views.py:671-695` — decisió CTO escrita al codi: dos codis que reclamen el mateix POM →
**400, bloquejar abans d'escriure res**. `pom/services.py:613-622` — el mateix cas resolt amb
`pendent_revisio=True`. Els dos guards tracten com a **anomalia** el que INSTÀNCIA vol **legitimar**. Si
la instància entra i aquests guards no creixen amb ella, **bloquejaran precisament el cas nou**.

**5. Aquest terreny ja es va trepitjar, amb un altre nom.**
`docs/diagnosis/DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md` (21/07) va arribar a la **mateixa clau** dient-li
`component`; `DIAGNOSI_MULTIPECA_DALIA.md` §Q2 hi va tornar des del multi-peça; i el codi mateix porta la
decisió ajornada escrita: `models_app/models.py:654-659` («separar-les de debò vol tocar la clau, que
travessa 5 taules més, i és decisió d'arquitectura (Patró C)»). **El delta d'avui és C1: el motlle existeix**
(§B4). *Nota:* la sortida barata que aquella diagnosi recomanava validar primer —modelar-ho com a Models
germans dins un `GarmentSet`— **no és viable amb les dades d'avui**: `GarmentSet` = **0 files**, Models amb
`garment_set` = **0**, amb `piece_number>0` = **0** (SQL d'aquesta sessió; respon el seu «pendent de verificar»).

**6. El cas del brief NO EXISTEIX a staging, i el corpus explica per què.**
`LEFT` i `RIGHT`: **0 ocurrències** a tot el corpus nuclear (1 374 textos). `GATHERED`/`SHIRRED`: **0**.
El top asimètric amb sisa dreta ≠ esquerra **no hi és** (§D3). El que sí que hi és, i massivament, és
l'eix **estat de la peça** (RELAXED/EXTENDED/STRETCHED, **122 ocurrències**) i l'eix **panell**
(FRONT/BACK, 304). El diccionari inicial ha de néixer del que la casa diu de debò, no del cas d'exemple.

**7. El bateig del model encara no s'ha estrenat.**
`nom_canonic_model` i `nom_traduit_model`: **0 files informades de 760**. `seccio`: **0 de 760**. El sprint
NOMS-POM (30/07) va lliurar els camps i ningú els ha fet servir encara — el terreny és verge, i qualsevol
decisió sobre com el nom d'instància s'hi relaciona **no ha d'arreglar dades històriques**.

---

## FASE A · L'ONA EXPANSIVA

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

### A2 · Escriptors cecs — els que perden dades sense avisar

Semàntica de la classificació: `update_or_create(model=X, pom=Y)` sense instància a la clau té dues cares —
(a) mentre només hi hagi una fila mai podrà **crear** la segona instància, sempre reescriurà la primera → 🔴;
(b) si la segona hi arriba per un altre camí, el `get()` intern llança `MultipleObjectsReturned` → 🟠.
S'hi marca la cara dominant.

**`BaseMeasurement` — el nucli (15 escriptors)**

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
| `tenants/federation_service.py:689` | `.filter(model=twin, pom=pom).first()` | `(model, pom)` | 🔴 v. §A5 |
| `fitting/management/commands/repair_fitting_20260710.py:78` | `.first()` | `(model, pom)` | 🟡 comanda històrica |

**`ModelGradingOverride`**: `models_app/views.py:2590` (🔴, body `{pom_id, size_label, valor}`) · `:2587-2589`
(🟡 el `prev` del log és arbitrari) · `:2762` (🔴 escalat) · **`:2751` `.filter(model, pom).delete()`**
(🔴 esborra els overrides de **totes dues** instàncies) · `extraction_views.py:2693` (🔴 import W5).

**Motor**: **`pom/services.py:1033` `_upsert_graded_spec`** — `update_or_create(grading_version, pom_id,
size_label)`; rep `pom_id: int` per signatura (`:1009`): **no hi ha lloc per a la instància ni al paràmetre**.
`fitting/services.py:332` clona `GradedSpec`→`PieceFittingLine` copiant **només** `pom`, `size_label` i
`graded_value_cm` — **ni `capa` s'hi copia** → dos specs germans donarien dues línies indistingibles (🟠).

**`SizeCheckLine` — el pitjor cas del cens** (verificat literalment, `models_app/services_size_check.py:33-42`):

```python
ja_hi_son = set(SizeCheckLine.objects.filter(size_check=size_check).values_list('pom_id', flat=True))
bms = (BaseMeasurement.objects.filter(model=model, is_active=True, base_value_cm__isnull=False)
       .exclude(pom_id__in=ja_hi_son).select_related('pom'))
```

Clau d'aparellament: **`pom_id` pelat, ni tan sols `capa`**. La segona instància **mai rep línia de check**
— el seu `pom_id` ja consta com a «ja hi és». No peta, no avisa, i com que `_materialize_lines` és
*completadora* (docstring `:22-30`), **cada re-obertura del check torna a decidir el mateix**. 🔴

**Catàleg i seeds**: `models_app/views.py:3760` · `:3774` · **`:3770`** (`next(b for b in fonts if
b.pom_id == fila['pom_id'])` → agafa la primera del generador, valor promogut arbitrari, 🟡) ·
`pom/views.py:508` · `load_map_inline.py:144` · `consolidate_pom_catalog.py:212` ·
`author_baby_pom_maps.py:146` · les 5 comandes `seed_losan_*`.

**Recomptes i cobertures que desquadrarien** (una instància extra compta com un POM):

| Fitxer:línia | Què compta | Efecte |
|---|---|---|
| **`pom/wizard_views.py:252-257`** | `n_poms = BaseMeasurement.filter(model, is_active).count()`, gate `< 3` | 🔴 sisa-D + sisa-E + coll **passaria** un gate que exigeix 3 POMs amb 2 mesures reals (verificat literalment) |
| `patterns/engine/grading_projection.py:179-200` | `pom_sense_spec` / `spec_sense_pom` calculats sobre **conjunts de `pom_id`** | 🔴 declararia cobert un POM cobert a mitges |
| `pom/views.py:361-364` · `tasks/views_b.py:970` | `Count('measurements')` / `Count('pom_maps')` | 🟡 columnes «#mesures» inflades |
| `models_app/views.py:2318` | `'ordre': base_measurements.count()` | 🟡 ordre duplicat entre instàncies |

### A3 · NOMS-POM — on penjaria la constraint «nom d'instància diferent»

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
**358 `codi_client` distints → 12 codis duplicats** amb significats sense relació
(`U1` → *Height sequins piece (CF)* i *JETTING WIDTH* · `D` → *1/2 bottom width relaxed* i *HIP WIDTH* ·
`J1` → *SHOULDER DROP LOCATION* i *Sleeve opening relaxed*…). I hi ha lectors que hi fan `.first()`:
`models_app/views.py:2313-2314` i `tenants/federation_service.py:579`.
L'únic guard de duplicat de tot el sistema és `pom/wizard_views.py:431-432` (400, sense `iexact`);
`edit_pom_nomenclature_view:465` reescriu `codi_client` **sense cap guard** — és la porta per on entren.

**Veredicte A3:** el nom d'instància té un candidat clar (`nom_fitxa`) i terreny net, però la constraint
sola no bastaria: **vuit portes d'escriptura sense normalitzar i cinc cascades de lectura divergents**.

### A4 · POMPlacement — pot ancorar dues instàncies al croquis?

**NO. I ho impedeixen QUATRE punts independents** — o sigui que obrir-ho no és tocar un lloc:

| # | On | Fitxer:línia | Què fa exactament |
|---|---|---|---|
| 1 | **BD — la clau** | `models_app/models.py:1336-1338` | `(item_fitxer, pom, view_slot, capa)`, **sense `condition`**. En teoria hi caben dues files del mateix POM si tenen `capa` diferent |
| 2 | **BD — la comporta** | `models_app/models.py:1340-1343` | `CheckConstraint(capa='exterior')` → la clau EFECTIVA d'avui és `(item_fitxer, pom, view_slot)`. **És el CHECK, no la clau, el que ho tanca** |
| 3 | **Vista — escriptura** | `models_app/pom_placement_views.py:135-138` | `update_or_create(item_fitxer, pom_id, view_slot)` — **`capa` no entra ni a la clau ni als defaults**. Encara que C4 retirés el CHECK, **aquest upsert seguiria col·lapsant** |
| 4 | **Frontend — guard explícit** | `TechSheetEditor.jsx:5426-5435`, `:6703`, `:6729-6734` | `cotesColocades` és un **`Set` de `pomId`**; comentari literal `C3 · GUARD DE DUPLICATS: un POM amb cota viva al document no es pot re-acotar`. Reforçat a `:5533`, `:5558`, `:5633`, `:5670` |

**Lectura**: `pom_placement_views.py:52-64` — `exacte = {p.pom_id: p}`, `germana.setdefault(p.pom_id, p)`,
`merged[pom_id] = …`: **la cascada de precedents col·lapsa per `pom_id` ABANS del lookup de capa**.
El lookup del `bm_id` sí que ja és clau composta `(pom_id, capa)` (`:72-86`), i el comentari `:68-71` ja
té el nom del dany: *«el pitjor cas d'aquesta vista, perquè no peta: **pinta**»*. Amb instàncies passa
idènticament: la cota de la sisa esquerra rebria el `bm_id` de la dreta.

**No existeix cap DELETE de placement** a tot el sistema: un precedent només es pot sobreescriure.

**L'identificador que la cota porta al `.ftt`** és el parell `(pomId, bmId)` (`TechSheetEditor.jsx:4145`,
`:344`), amb **`bmId` preferent en LECTURA** (`:3462`: `bmById.get(o.bmId) || bmByPom.get(o.pomId)`) però
**`pomId` com a únic eix d'unicitat**. I el body que desa el precedent
(`construirPrecedentCota:5598-5605`) **no hi porta ni `bmId` ni `capa`**: en desar es perd tota informació
d'instància.

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
descriu el dany per capa —*«s'escriuria el nom a la mesura de l'altra capa»*. **Amb instàncies, batejar la
sisa dreta escriuria el nom sobre l'esquerra.** `rules.get(line.pom_id)` (`:287`) col·lapsa igual, i `:304`
declara que **el front el llegeix per `pom_id`**: el contracte cap al frontend és `pom_id`.
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
`(pom_id, capa)` i el seu comentari `:2991-2998` descriu el dany exacte — *«el carry-forward arrossega el
valor d'una capa cap endavant per la fila d'una altra»*— i declara que **el payload de sortida segueix
portant `pom_id` sol** (`:2997-2998`, `:3028`). `fitting/repas_views.py:156-159`: `celles[clau][c.pom_id]`,
**sense ni capa**. 🔴

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

### A6 · Wizard i import — com es resol avui el duplicat

**`many_to_one` no és una entitat: és una bandera booleana per FILA** dins del JSON
`ImportSession.poms_extrets` (`models_app/models.py:572`). Hi ha **DUES implementacions germanes i
deliberadament divergents**:

| | Camí IMPORT de mesures | Camí SIZE-MAP / grading |
|---|---|---|
| On | `models_app/extraction_views.py:1148-1193` | `pom/size_map_views.py:54-75` (crides `:362`, `:604`) |
| Compta per | `pom_master_id` (`:1175-1179`) | `pom_id` |
| Acció | mou el match a `weak_suggestion`, **buida `pom_master_id` i posa `actiu=False`** (`:1183-1192`) | idem |
| Exempció d'àlies | **CAP** — docstring `:1155-1171`: destí `BaseMeasurement`, únic per `(model,pom)`, «per legítim que sigui l'àlies, la segona esborra la primera» | **SÍ**: `match_type == 'alias_match'` no dispara (`:64`, `:70`), perquè «un client pot etiquetar legítimament el mateix POM amb dos codis (Losan H.11 / H.16)» |

> **FET clau:** el guard **no detecta nomenclatura duplicada — detecta destí duplicat**. Dues files amb el
> mateix `codi_fitxa` només es veuen si totes dues resolen al mateix `pom_master_id`.
> **NO EXISTEIX enlloc cap comprovació de `codi_fitxa` repetit dins d'un document.**

**El parser NO dedupica**: `_parse_excel_poms` (`extraction_views.py:233`) emet una fila per fila de document
(`:437-478`), i la via Opus igual (`:1631-1634`). L'única col·lisió per codi és
`by_codi.setdefault(p['codi_fitxa'], p)` (`:1417-1419`), i només per dirigir les correccions de Sonnet: **la
segona fila amb el mateix codi no rep mai correcció però sobreviu.**

**La resolució actual no descarta ni fusiona: BLOQUEJA i delega a l'humà** — però l'única sortida oferta és
1 fila ↔ 1 POM distint. L'avís (`:1268-1273`) diu literalment: *«dues mesures no poden compartir un POM: la
segona esborraria la primera. Resol-los un per un»*.

**Els 409 del pas 2** (`extraction_views.py`): `codi_duplicat` (`:1844-1845`, amb `candidats` de
`_candidats_de_codi:1693-1710`) · `resolucions_invalides` (`:1856-1858`) → **`pom_ja_usat` (`:1753-1756`)
és el punt dur**: «no el pot tenir ja una altra fila activa» (`:1718`) · `codi_existent` (`:1764-1766`) ·
`codi_repetit` (`:1768-1771`).

**`CustomerPOMAlias` demostra que el sistema JA sap conviure amb l'ambigüitat, un nivell més amunt.**
Docstring `pom/models.py:382-383`: *«Un client pot tenir DIVERSOS codis per al mateix POM → unicitat
(customer, client_code), NO (customer, pom)»*. `maybe_learn_customer_alias`
(`pom/services.py:578-640`) **no falla ni descarta**: crea l'àlies amb `pendent_revisio=ja_reclamat`
(`:630`, `:637`). El consumidor el degrada a LOW (`extraction_views.py:1026-1037`, `:1092-1093`).
→ **L'ambigüitat és legítima a nivell d'ÀLIES; es converteix en error a nivell de MESURA.**

**El wizard no té ni guard ni 409 per al duplicat**: `save_base_size_view` (`pom/wizard_views.py:155-227`)
rep `poms: [{pom_id, valor_cm}]` — la identitat és `pom_id`, no una fila — i `update_or_create` a `:205-215`
**fusiona en silenci si el payload porta dues entrades del mateix POM**. Cap codi d'error de duplicat a tot
el fitxer.

**Sembra i plantilles**: `materialize_poms` (`models_app/views.py:1104-1220`) llegeix la plantilla com a
dicts per `pom_id` (`:1136`, `:1145`) i fa `.first()` a `:1182` → amb dues instàncies veuria una d'arbitrària
i tractaria l'altra com a inexistent → `IntegrityError` o `skipped` silenciós (`:1217`).
`_sembra_step_des_dels_specs` (`:3949-3988`) fa `dict(...values_list('size_label','graded_value_cm'))`
(`:3977-3980`) → l'última guanya, **sense rastre**.

**Frontend — NO EXISTEIX cap UI per declarar «dues instàncies legítimes»**, i hi ha **tres barreres actives**:
`ImportWizard.jsx:536-537` (`addPomManual` prohibeix afegir dos cops el mateix POM) ·
**`:626-637` `buildTaula` → `t[p.pom_master_id] = row`: la graella del pas 3 és UNA FILA PER POM** — dues
instàncies es fondrien abans d'arribar al backend · `:639-645` (`setCell`, `emptyCols`) igual.
El `ResolPanel` (`:1194-1208`) té **exactament dues accions**: `vincula` | `crea`.

**Els ~32 punts de decisió que canviarien** si el duplicat pogués ser instància legítima estan enumerats a
l'annex del cens (identitat/esquema ×10 · detecció ×5 · confirmació ×4 · escriptura ×6 · alta manual ×2 ·
sembra ×3 · nomenclatura ×3 · frontend ×6), més els tests que codifiquen la llei actual
(`models_app/tests.py:105-126`, `:180-204`; `test_import_poms_duplicats.py`; `test_import_poms_resolucions.py`;
`test_parser_excel.py:514`, `:542`).

### A7 · Els tres fitxers que decideixen si el canvi és viable

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

## FASE B · COST COMPARAT DE LES TRES FORMES

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
| **Riscos de col·lapse residuals** | Els **16 dicts encara per `pom_id` pelat** (`repas_views.py:156`, `graded_spec_views.py:59-74`/`:102-106`, `grading_views.py:96-114`, `patterns/views.py:544`, `grading_projection.py:179-200`…): si un creix i el veí no, la fila surt **amb l'ordre d'una instància i el nom de l'altra** — el mode de fallada que `graded_spec_views.py:86-92` ja descriu | **Tots els de F1** + col·lapse per **normalització de JSON**: `{"lat":"R"}` i `{"lat":"r"}` són claus distintes i mesures iguals. **NO hi ha cap índex GIN al schema `fhort` (0)** ni cap precedent de JSONB en clau (§B2) | **Els de F1.** Els tags no poden col·lapsar res perquè no entren a cap clau |
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
  `MeasurementLayer` **per slug, mai per FK** (llei G9, `pom/models.py:225` i comentari a
  `models_app/models.py` §capa).

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
| Cas real viu | cap trobat | **model 396 EXPLORER, 2 parells d'instàncies** (§D1) |

---

## FASE C · COLLITA DEL DICCIONARI

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
`exterior`/Shell · `folre`/Lining · `entretela`/Interfacing · `farciment`/Padding · `reforc`/Underlining ·
`fornitura`/Trim.

### C2 · La troballa central: el qualificador viu al NOM del catàleg

**43 `POMMaster` i 27 `POMGlobal`** porten `RELAXED`/`EXTENDED`/`STRETCHED` al nom. Agrupats per tronc
(nom sense el qualificador), **25 troncs**, dels quals **10 tenen 2 o més variants**:

| Tronc | Variants al catàleg de tenant (`POMMaster`) |
|---|---|
| **LEG OPENING** | STRETCHED#407 · RELAXED#532 · EXTENDED#533 · **RELAXED#687** · **EXTENDED#688** |
| **CHEST WIDTH** | RELAXED#331 · STRETCHED#332 · RELAXED#518 · EXTENDED#519 |
| **WAIST WIDTH** | RELAXED#523 · EXTENDED#524 · **RELAXED#685** · **EXTENDED#686** |
| HIP WIDTH | RELAXED#405 · STRETCHED#406 · STRETCHED#471 |
| SLEEVE OPENING | STRETCHED#298 · RELAXED#460 · EXTENDED#554 |
| 1/2 BOTTOM WIDTH · BOTTOM WIDTH · ELASTIC · HOOD LENGTH · WAISTBAND WIDTH | 2 cadascun |

I **el canònic fa el mateix**: `POM-080` *Chest width (relaxed)* / `POM-081` *Chest width (stretched)* ·
`LOSPOM-532` / `LOSPOM-533` *LEG OPENING RELAXED/EXTENDED* · `POM-050`/`POM-051` *Waistband width
(relaxed)/(stretched)*…

**Conseqüència mesurada — fragmentació del catàleg:** **15 `nom_client` duplicats** a `POMMaster`
(`BACK RISE` ×3, `FRONT RISE` ×3, `LEG OPENING RELAXED` ×2, `WAIST WIDTH EXTENDED` ×2…). El mateix concepte
existeix dues vegades perquè hi va arribar per dos camins (`origen_import = 'diccionari:LOS:2026-07-18'` vs
un UUID de sessió d'import), i **l'unicitat `(customer, client_code)` de `CustomerPOMAlias` ho permet perquè
`"C4" ≠ "C.4"`**: LOSAN té àlies per als quatre POMs de *WAIST WIDTH RELAXED/EXTENDED*, dos per cada
concepte.

> **FET, no interpretació:** avui **la instància ja té una implementació — encunyar catàleg**. El seu cost
> és fragmentació del diccionari de casa, àlies duplicats per client, i graduació duplicada (§D1).

### C3 · Taula de freqüències amb classificació

Recompte al corpus nuclear (1 168 textos), amb frontera de paraula (`\y`). La columna «Dimensió» és
`💡 PROPOSTA (a validar)` — **la classificació és decisió de la Montse**; el recompte és FET.

**Termes amb ocurrències > 0**

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
| CENTER / CENTRE | 13+2 | 7+2 | 3+7 | **23+11** | TAG · punt de referència (**variant ortogràfica**) |
| POSITION | 14 | 5 | 4 | **23** | TAG · eix de mesura (sinònim de LOCATION) |
| HPS / HSP | 10+0 | 0+2 | 12+9 | **22+11** | TAG · punt de referència (**HSP és variant/error d'HPS**) |
| TOTAL | 8 | 9 | 5 | **22** | TAG |
| GIRTH | 18 | 0 | 0 | **18** | TAG · eix de mesura |
| CB / CF | 9+9 | 1+0 | 5+4 | **15+13** | TAG · punt de referència |
| ACROSS | 10 | 0 | 4 | **14** | TAG · mètode |
| DART · PLEAT · FLOUNCE · FRILL · RUFFLE | — | — | — | **12·11·12·5·4** | TAG · element de peça |
| ALONG | 3 | 0 | 8 | **11** | **SOROLL** (mètode implícit) |
| **LINING** | 5 | 1 | 4 | **10** | **CAPA** → `folre` ⭐ |
| DEPTH | 6 | 1 | 3 | **10** | TAG · eix de mesura |
| PLACEMENT · CIRCUMFERENCE · SPACING | 8·8·8 | 0 | 0 | **8·8·8** | TAG · eix de mesura |
| INCL / EXCL | 1/2 | 3/2 | 4/2 | **8/6** | TAG · mètode |
| MEASURED | 3 | 3 | 2 | **8** | **SOROLL** |
| W/FLAP | 5 | 3 | 0 | **8** | TAG · variant constructiva |
| SWIMWEAR · KNITWEAR | 6·2 | 0 | 0 | **6·2** | TAG · segment de producte |
| HALF | 2 | 2 | 1 | **5** | TAG · mètode (sinònim d'`1/2`) |
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
(cridada des de `extraction_views.py:2540-2542` i `:2567-2569`), i marca `pendent_revisio=True` quan detecta
col·lisió (`:613-622`). El que **NO EXISTEIX** és un equivalent que aprengui **termes de dimensió**
(qualificadors, capes, tags) — només aprèn el parell `(client_code → pom)`.

---

## FASE D · CAS DE PROVA

### D1 · El cas real trobat: model 396 · LOS-SS27-0122 · EXPLORER

**Dos parells d'instàncies vives**, tots dos `origen = IMPORTED`, tots dos a `capa = exterior`:

| bm | pom | `codi_client` | `nom_client` | `nom_fitxa` | valor | ordre |
|---|---|---|---|---|---|---|
| **1665** | **685** | C.4 | WAIST WIDTH **RELAXED** | `C.4` | **21,0** cm | 0 |
| **1666** | **686** | C.1 | WAIST WIDTH **EXTENDED** | `C.1` | **26,5** cm | 1 |
| **1675** | **687** | F.5 | LEG OPENING **RELAXED** | `F.5` | **7,5** cm | 10 |
| **1676** | **688** | F.6 | LEG OPENING **EXTENDED** | `F.6` | **9,5** cm | 11 |

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
4. **LOSAN va acabar amb quatre àlies per a dos conceptes**: `C.4`→685, `C.1`→686 (origen `IMPORT`) i
   `C4`→523, `C1`→524 (origen `DICCIONARI`). **L'unicitat `(customer, client_code)` ho permet i ho fa
   invisible**, perquè `pom/nomenclatura.py:32-41` només en mostra un per POM.
5. **El cost aigües avall és real i mesurat**: models 396+170 tenen **120 `GradedSpec`**, **20
   `ModelGradingRule`** i **20 `MeasurementChangeLog`**. Cada instància gradua per separat, amb regla pròpia,
   i **`ModelGradingRule` no té `capa`** (`models_app/models.py:960`) — o sigui que amb la instància com a
   columna aquesta taula també hauria de decidir.

### D2 · Segon i tercer cas

- **Model 170 · BRW-FW26-0008 · Short BERLIN Rayas**: `WAISTBAND WIDTH` **RELAXED** (bm 1119, pom 318) +
  **STRETCHED** (bm 1120, pom 319). Tots dos amb `base_value_cm = NULL` — materialitzats, sense valor.
  Aquests dos POMs **sí** tenen canònic (`POM-050`/`POM-051`), o sigui que **la duplicació ve del catàleg de
  la casa, no de l'import.**
- **Models 163, 174, 268, 269**: `Front armhole along seam` (pom 457) + `Back armhole along seam` (pom 458),
  amb `nom_fitxa` `S` i `S2`. **Aquest és el cas més proper al del brief**: la mateixa mesura (sisa al llarg
  de la costura) presa sobre **dos panells**, resolta amb dos POMs i dues nomenclatures. Valors reals al 163:
  21,5 / 24,0 cm.
- **Model 162 / 182 (OLIVIA DRESS)**: `Lining Length at Center Back` (383), `Lining Bottom Width Along Hem`
  (384), `Lining Length at Center Front` (429) — **la CAPA també encunyada com a POM**, exactament el mateix
  patró que C1 va venir a resoldre.

### D3 · El cas del brief: NO EXISTEIX

Cerca exhaustiva a `fhort` i `los`:

| Cerca | Resultat |
|---|---|
| `LEFT`/`RIGHT`/`LH`/`RH`/`DX`/`SX` a tot el corpus | **0** |
| `GATHERED`/`SHIRRED`/`FRUNZ` | **0** |
| POMs amb sufix de secció al codi (`(`, `)`, `_TOP`, `_PANT`, `PANTIE`) | **0** |
| `models_app_basemeasurement.seccio` informada | **0 de 760** |
| Models amb `nom_fitxa` duplicat dins el model | **0** |

**Tops i candidats propers:** model **169 · BRW-FW26-0007 · Top AMELIA** (29 mesures) — cens complet
consultat: té `Armhole depth` (284) i `Armhole circumference` (285) **una sola vegada cadascun**, sense cap
rastre de lateralitat. Model **1062 · LOS-SS27-0788 · HALTER** existeix però **té 0 `BaseMeasurement`**.
Els models `CRUZADO` (596), `DALIA` (545, 1109) i `AMARANTA` (1108) — els del cas bikini TOP/PANTIE ajornat a
`INFORME_FASE1_TANCAMENT_LOSAN.md:58` — **tenen tots 0 mesures**: la decisió es va ajornar i **segueix sense
implementar** (ja constatat a `DIAGNOSI_MULTIPECA_DALIA.md` §Q2, i re-verificat avui).

**Només 26 models de 1 055 tenen mesures** (760 files, màx. 48 per model). El corpus de mesures és petit i
concentrat: qualsevol conclusió sobre freqüència d'instàncies **té aquesta base**.

> **Veredicte FASE D:** el cas d'exemple del brief no existeix a staging i el corpus no en té ni vocabulari.
> **El cas real i mesurable és l'eix ESTAT (relaxed/extended/stretched)**, amb 3 models vius, 43 POMs de
> catàleg i graduació duplicada. **Qualsevol prova d'acceptació hauria d'anar sobre el model 396**, no sobre
> un top asimètric hipotètic.

---

## TAULA FINAL — RISCOS PER AL CTO

| # | Peça | Estat | Ancoratge | Risc |
|---|---|---|---|---|
| 1 | Columna d'instància a qualsevol taula | **NO EXISTEIX** | cap camp `instancia`/`instance`/`variant`/`component` als 3 `models.py` de domini (les ocurrències del grep són `isinstance` i docstrings) | — |
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

## LÍMITS D'AQUESTA DIAGNOSI

- **Cap proposta de fix**, per encàrrec. Les tres formes de la FASE B es comparen, **no es recomana cap**.
- El corpus és **petit i concentrat**: 760 `BaseMeasurement` en **26 models de 1 055**, i tot a `fhort`
  (`los` en té 0). Les freqüències de la FASE C són sòlides per al **catàleg** (370 + 274 noms) i més febles
  per a l'**ús real en models** (207 `notes` + 206 `nom_fitxa`).
- La classificació de termes (§C3, §C5) és `💡 PROPOSTA`: els **recomptes** són FET, la **dimensió** és
  decisió de la Montse. Les tres ambigüitats de §C4 no es poden resoldre automàticament.
- Les afirmacions de codi porten `fitxer:línia` verificat en aquesta sessió. Els cinc punts més portants
  s'han llegit literalment: `pom/services.py:767-783` · `models_app/services_size_check.py:33-42` ·
  `tenants/federation_service.py:542-552` · `patterns/models.py:426-436` · `pom/wizard_views.py:248-260`.
- **No auditat**: el frontend del backoffice; les superfícies de `patterns/` més enllà dels punts d'ancoratge
  citats; el cost d'UI de qualsevol de les tres formes (requereix maqueta, llei 3c.5).
- El comptador «~45 escriptors/lectors» és de cens per grep + lectura de rang, no d'anàlisi estàtica
  exhaustiva: **pot faltar-hi algun node**, sobretot a `management/commands/`.

---

*Diagnosi Patró A · read-only absolut · cap fitxer del repo tocat fora d'aquest document · cap escriptura a BD.*
