# DIAGNOSI — PAQUET LOSAN: cens de l'àmbit LOS + disseny d'export/loader (FASE A)

Data: 2026-07-19 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

Abast: fotografiar TOT l'àmbit LOS del tenant `fhort` per dissenyar (a) un paquet de fitxers
versionats per clau natural i (b) un loader idempotent parametritzat per tenant destí (sandbox
`losan` a staging → PROD). Aquesta és la FASE A del brief PAQUET LOSAN: **inventari + disseny +
resolució de D-A**. Reportar i aturar al GATE. Cap escriptura fora d'aquest doc.

Convenció: `fitxer:línia` o el SELECT/ORM que ha donat el fet · "NO EXISTEIX" = confirmat absent
al codi (no especulat) · `💡 PROPOSTA (a validar)` = disseny per decidir al gate (decisió humana).
Tots els recomptes surten de SELECT/ORM dins `schema_context('fhort')` (o `('public')` on s'indica),
staging, 2026-07-19.

---

## Resum executiu (el que desbloqueja el gate)

1. **Tres premisses del brief cauen amb dades i cal decidir-les al gate:**
   - **POMGlobal LOSPOM-* NO viuen a `public`.** `public` té 125 POMGlobal base i **0 LOSPOM**;
     el schema `fhort` en té 274, dels quals **149 `LOSPOM-*`** (tots actius). Els `LOSPOM-680..684`
     són `codi` de POMGlobal **al tenant**, no a public. → **Res de la capa POM viatja "de franc"
     per ser SHARED; TOT s'ha de re-sembrar per `codi` al schema destí.** (Bo per a PROD: no toquem
     el public compartit.)
   - **Els recomptes reals difereixen dels del brief:** **19** GradingRuleSet LOS (no 22), **409**
     GradingRule (no 390), **196** àlies (no ~190). Els 18 SizingProfile de customer=6 són correctes,
     PERÒ hi ha **4 SizingProfile més amb `customer=NULL`** penjats de la capa LOS (§A1.7).
   - **`POMMaster.codi_client` ja existeix però NO és clau natural única:** **12 codis duplicats**
     dins el tenant (§A1.2). Plegar-hi els àlies (D-A·b) hi afegiria col·lisions i **perd informació**
     en 7 POMs amb >1 àlies (§A4.2). Cal decisió.

2. **D-A (tenant-native, customer=NULL) és un blocador de CODI, no de dades.** Els camps aguanten
   NULL, però `resolve_grading_container` **aborta sense customer** i filtra `origen=CLIENT_RUN,
   customer=<no-null>`; i **11 commands** LOSAN cablen `codi='LOS'` sense mode tenant-native. Res
   d'això es resol al paquet: són **adaptacions de motor a fer a la FASE C abans de l'assaig** (§A4).

3. **`bootstrap_tenant` copia el catàleg SENCER del tenant origen** (per defecte `fhort`) via
   `update_or_create` per clau natural, sense esborrar. **NO crea Customer** i força `customer=NULL`
   als GradingRuleSet i SizingProfile. Amb `--profile` grading només viatgen rulesets `CANONICAL`.
   El loader ha de ser **create-if-missing sobre EXACTAMENT les mateixes claus naturals** (§A2, §A3).

4. **Anomalies de fidelitat que el QA final ha de conèixer** (D-C: viatgen tal qual, però es
   reporten): **5 GradingRule sobre POM inactiu** (grs 104) i **1 clau de wizard ambigua** (3
   SizingProfile → 3 rulesets per BABY_GIRL/NEWBORN/KNIT/REGULAR). El "0 regles a POM inactiu" i
   "cada cas → 1 ruleset" del brief **no es compleixen avui a l'origen** (§A1.6, §A1.7).

5. **Disseny del paquet:** el de 10 fitxers del brief és viable amb dos matisos — cal un fitxer
   **`02b_pom_globals` que inclogui els 149 LOSPOM-*** (no és shared), i **decidir si la capçalera
   LOSAN (DocumentTemplate + logo) entra** (avui viu fora dels 10 fitxers; §A1.8, §A3).

---

## §A1 — CENS de l'àmbit LOS (fhort, 2026-07-19)

### A1.0 · Customer LOS + query invertida (què penja de LOS)

`fhort.tasks.Customer` id=**6**, `codi='LOS'`, "LOSAN IBERIA SA", `is_self=False`, `logo=<present>`,
`default_document_template=None` (ORM). Escaneig invertit dels `related_objects` que apunten a
Customer 6:

| Model.camp | files customer=6 | dins paquet? |
|---|---|---|
| `pom.CustomerPOMAlias.customer` | **196** | SÍ (nomenclatura nativa, §A4.2) |
| `pom.GradingRuleSet.customer` | **19** | SÍ |
| `pom.SizingProfile.customer` | **18** | SÍ (+4 NULL, §A1.7) |
| `models_app.Model.customer` | **962** | **NO** — models via CSV + `seed_losan_models` (brief) |
| `models_app.ModelSequence.customer` | **1** | **NO** — comptador de codi-gen; D-B renumera → arrenca de zero |
| `commerce.WorkOrder.customer` | **1** | **NO** — facturació/comercial aparcada (brief) |

**FET:** no apareix res inesperat penjat de Customer 6 (ni TaskType, ni plantilles, ni fitxers
propis amb FK a customer). `Model=962` (no 961): +1 respecte al seed; probablement un clon QA — no
afecta el paquet perquè els models no s'exporten. `ModelSequence=1` confirma que el codi-gen del
tenant nou ha d'arrencar net (coherent amb D-B).

### A1.1 · CustomerPOMAlias (customer=6)

- Total: **196** · `pendent_revisio=True`: **0** · sense `pom` (pendent de mapar): **0** ·
  POMMaster distints referenciats: **188**.
- Model a **TENANT** (`pom/models.py:236`, FK `tasks.Customer` `db_constraint=False` `:249`).
  Unicitat `(customer, client_code)` (`pom/models.py:279-282`) — pensada per N codis → 1 POM.
- Camps que viatgen (D-C): `client_code`, `description_en`, `description_local`, `language`,
  `origen`, `pendent_revisio` (`pom/models.py:260-272`).

**Veredicte A1.1:** capa neta (0 pendents, 0 orfes). El problema no és l'estat sinó **on aterra**
la nomenclatura al tenant-native (§A4.2).

### A1.2 · POMMaster (tenant-wide)

- Total: **360** · actius: **344** · `pendent_revisio=True`: **218** · amb `pom_global`: **274** ·
  `codi_client` no buit: **360** (tots).
- **Unió referenciada** (àlies LOS ∪ regles LOS ∪ TOTS els GarmentPOMMap ∪ ItemBaseMeasurement):
  **254** distints. Unió (àlies LOS ∪ regles LOS): **197**. Referenciats i **inactius**: **5**.
- Model a **TENANT** (`Meta verbose_name='POM (tenant)'` `pom/models.py:183`; a `public` la taula és
  buida). `codi_client` = `CharField(30)` NOT NULL `pom/models.py:159`. `actiu` `:162`,
  `pendent_revisio` `:169`, `origen_import` `:174`, `pom_global` FK `:145`.
- **`descripcio_local` NO EXISTEIX** i **`traduccions` NO EXISTEIX** a POMMaster (el brief els cita):
  el text és `codi_client`/`nom_client`/`notes` (`:159-161`) i les traduccions viuen a
  `POMGlobal.nom_en/ca/es` (`@property name_cat/name_en` `pom/models.py:197-206`).

**⚠️ FET clau — `codi_client` NO és clau natural única:** **12 codis duplicats** dins el tenant.
Tots són parelles "POMMaster antic (fhort intern, `pom_global=None`) + POMMaster LOSAN nou
(`pom_global=LOSPOM-*`)":

| codi_client | (pk, actiu, ref.LOS, pom_global) × 2 |
|---|---|
| BJ | (418,T,SÍ,—) · (514,T,SÍ,LOSPOM-514) |
| C1 | (471,T,no,—) · (524,T,SÍ,LOSPOM-524) |
| D | (436,T,no,—) · (528,**F**,no,—) |
| E4 | (455,T,no,—) · (535,T,SÍ,LOSPOM-535) |
| E7 | (475,T,no,—) · (537,T,SÍ,LOSPOM-537) |
| H | (423,**F**,SÍ,—) · (551,**F**,no,—) |
| J1 | (507,T,SÍ,LOSPOM-507) · (460,T,SÍ,LOSPOM-460) |
| L1 | (505,T,no,—) · (510,T,SÍ,LOSPOM-510) |
| S | (457,T,SÍ,LOSPOM-457) · (581,T,SÍ,LOSPOM-581) |
| S2 | (458,T,no,—) · (583,T,SÍ,LOSPOM-583) |
| U | (439,T,no,—) · (512,T,SÍ,LOSPOM-512) |
| U1 | (440,T,no,—) · (513,T,SÍ,LOSPOM-513) |

**Veredicte A1.2:** la clau natural del POM per al paquet **no pot ser només `codi_client`**
(bootstrap l'usa igualment, però sense constraint DB → duplicaria). 💡 PROPOSTA: clau natural del
POMMaster al paquet = **`pom_global.codi` quan existeix (LOSPOM-*/canònic), i `codi_client` només
com a desambiguador** per als 86 sense `pom_global`. A validar al gate (§A3, D-A·b).

### A1.3 · POMGlobal — **CORRECCIÓ de premissa del brief**

- `schema_context('public')`: POMGlobal total **125** · `LIKE 'LOSPOM-%'` = **0**.
- `schema_context('fhort')`: POMGlobal total **274** · `LIKE 'LOSPOM-%'` = **149** (tots `actiu=True`).
- `LOSPOM-680..684` = pk 401-405 a fhort (SLEEVE SHORT LENGTH/OPENING, CHEST POCKET OPENING, BOTTOM
  MOTIVE LOCATION, FRONT VENT WIDTH). Són `codi` de POMGlobal **al tenant**, no PKs de POMMaster.

**Veredicte A1.3:** els 149 LOSPOM-* **es van sembrar només al schema `fhort`**, no al public
compartit. **Han d'entrar al paquet i re-sembrar-se per `codi` al tenant destí.** El `pom_global_id`
dels POMMaster és local al schema → la reconciliació POMMaster→POMGlobal ha d'anar **per `codi`**,
mai per pk. (Efecte lateral positiu: no cal tocar el `public` de PROD.)

### A1.4 · Catàleg (tenant-wide, no filtrat per customer)

| Model | recompte | notes |
|---|---|---|
| GarmentGroup | **12** (12 actius) | clau natural `codi` |
| GarmentType | **21** (17 actius) | clau natural `codi_client` (sense unique DB); `grup`=CharField |
| GarmentTypeItem | **62** | clau `(garment_type, code)` unique_together `tasks/models.py:327` |
| — amb `base_size_definition` | 2 | `tasks/models.py:306` |
| — amb `grading_rule_set` default | 3 | `tasks/models.py:319` |
| GarmentPOMMap | **1748** (238 `pendent_revisio`) | clau `(garment_type_item, pom)`; `pendent_revisio` `pom/models.py:451` |
| ItemBaseMeasurement | **37** | clau `(garment_type_item, pom)` `pom/models.py:495` |

**FET:** el catàleg NO és customer-scoped (cap FK a Customer). El "catàleg LOS" = el catàleg sencer
del tenant. Coincideix amb el catàleg que `bootstrap_tenant` ja sembra → **col·lisió massiva
esperada** que el loader ha de resoldre create-if-missing (§A2).

### A1.5 · SizeSystem LOS (`customer_codi='LOS'`) + SizeDefinition

**11 sistemes, tots actius** (SizeDefinition LOS = **86**):

| pk | codi | targets | defs |
|---|---|---|---|
| 63 | BABY_LOS_01 | TODDLER_GIRL, TODDLER_BOY | 6 |
| 64 | BOY_LOS_01 | BOY | 9 |
| 48 | GIRL_LOS_01 | GIRL | 9 |
| 50 | GIRL_LOS_03 | GIRL | 9 |
| 51 | MAN_LOS_01 | MAN | 9 |
| 69 | MAN_NUM_LOS_01 | MAN | 11 |
| 62 | NEWBORN_LOS_01 | BABY_GIRL, BABY_BOY, BABY_UNISEX | 7 |
| 67 | WOMAN_LOS_01 | WOMAN | 7 |
| 68 | WOMAN_NUM_LOS_01 | WOMAN | 9 |
| 66 | YOUTH_BOY_LOS_01 | TEEN_BOY | 5 |
| 65 | YOUTH_GIRL_LOS_01 | TEEN_GIRL | 5 |

Clau natural `codi` (unique `pom/models.py:293`). `customer_codi` és **text de 3 chars**, no FK
(`pom/models.py:328`) → al tenant-native es manté el text `'LOS'` o es buida? (💡 decisió menor,
§A3). Targets via M2M (`pom/models.py:301`).

### A1.6 · GradingRuleSet + GradingRule LOS (customer=6)

- **GradingRuleSet: 19** (tots `actiu=True`, tots sobre size_system LOS, cap sobre size_system no-LOS).
  Origen: **`CLIENT_RUN`=18 + `None`=1**. El de `None` és **grs 104 "LOS Kids Knit Regular 2Y-12Y"**
  (ss=50 GIRL_LOS_03, 19 regles) — el contenidor LOS antic.
- **Contenidor (`garment_type_item`): 0 rulesets** el porten al camp directe. L'aplicabilitat viu a
  **9 `RuleSetScopeNode`** de tipus ITEM, només als rulesets **175/176/177/178** (els "àmbit" nous):
  175→gti{56,57}, 176→gti{55,59}, 177→gti{53,54,72}, 178→gti{56,57}.
- `fit_type`: 18 · `construction`: 18 · `size_system`: 19 (grs 104 és l'únic sense fit/construction).
- **GradingRule: 409** (totes actives). **⚠️ 5 regles sobre POM inactiu**, totes a **grs 104**:
  pom 419 `A.1`, 421 `L.5`, 422 `L.4`, 431 `K.2`, 423 `H` (tots `actiu=False`).
- Camps que viatgen (D-C): `pom` (per CODI/àlies), `talla_base` (etiqueta), `logica`,
  `increment_base`, `increment_break`, `talla_break_label`, `actiu`, `valors_step`
  (`pom/models.py:677-708`). Clau natural GradingRule `(rule_set, pom)` `pom/models.py:...`.
  Clau natural GradingRuleSet = **`nom`** (el que usa bootstrap; no inclou customer ni origen).

**⚠️ Veredicte A1.6:** el QA "0 regles a POM inactiu" del brief **NO es compleix a l'origen** (n'hi
ha 5, totes al contenidor antic 104). Per D-C viatgen tal qual; el QA de fidelitat ha d'esperar
**5, no 0**, o el gate decideix depurar-les abans (fora de D-C).

### A1.7 · SizingProfile

- **customer=6: 18.** **⚠️ + 4 amb `customer=NULL`** que apunten a rulesets LOS → **22 sobre
  size_system LOS**. Els 4 NULL són **sp 519/520/521/522**, tots sobre **grs 104 / ss 50**
  (SWEATSHIRTS_MIDLAYERS · KNIT · REGULAR, targets TODDLER_GIRL/TODDLER_BOY/GIRL/BOY). Coincideix
  amb el blocador conegut "4 SizingProfile default sobre ruleset 104/GIRL_LOS_03"
  (memòria `ftt-fase1-losan-cataleg`).
- **⚠️ 1 clau de wizard ambigua:** `(BABY_GIRL, NEWBORN, KNIT, REGULAR)` té **3 SizingProfile**
  (sp 539/540/541, customer=6, ss 62) apuntant a **3 rulesets diferents** (grs 175/176/177). Amb la
  clau natural de bootstrap `(target, garment_type, construction, fit_type, size_system, version)`
  aquests 3 col·lisionarien (mateixa tupla) → el paquet ha de decidir quin guanya o si la clau
  necessita més eixos.

**⚠️ Veredicte A1.7:** el QA "cada cas wizard → 1 ruleset" **NO es compleix a l'origen** per aquest
cas NEWBORN (3 rulesets per la mateixa tupla). I els **4 SizingProfile NULL** són capa LOS de facto:
cal decidir si viatgen (i com, en tenant-native ja són customer=NULL → hi encaixen).

### A1.8 · Fora de la llista del brief però penja de LOS

- **Logo LOSAN:** `Customer(6).logo` present. En tenant-native (D-A, sense Customer) el logo perd la
  seva casa. Memòria `ftt-fitxa-tecnica-motor`: la capçalera LOSAN es va entregar com a
  **DocumentTemplate id=2 + logo cablat via `Customer.logo`**. `Customer(6).default_document_template`
  és NULL, i el DocumentTemplate id=2 és **tenant-wide (sense FK customer)**.
- **DocumentTemplate:** `bootstrap_tenant` genera "Template FTT" genèric (`nom='Template FTT'`); la
  **capçalera LOSAN NO és als 10 fitxers** del brief.

**💡 PROPOSTA A1.8 (gate):** afegir la capçalera LOSAN al paquet (fitxer nou `11_document_template`
+ asset logo com a base64/fitxer adjunt) o declarar-la fora d'abast i entregar-la a mà com a la
resta d'entorns. En tenant-native el logo no pot penjar de Customer → hauria de penjar del
DocumentTemplate o d'un Customer self del tenant.

---

## §A2 — Què fa `bootstrap_tenant` (col·lisions per al loader)

Fitxer: `fhort/tasks/management/commands/bootstrap_tenant.py`. Model mental
(`:6-9`): un schema nou neix amb **taules** però catàleg buit; només `TaskType` (migració
`tasks/0025`, 14 files) i el **self-`Customer`** (migració `tasks/0020`) hi neixen per migració.
`bootstrap_tenant` **copia la resta del catàleg des d'un tenant origen viu** (`--from`, default
`fhort`) via `schema_context` + `update_or_create` per clau natural (`:198,:312`), **remapejant FK
per clau natural entre schemes, mai per pk** (`:20-22`), **additiu, MAI delete** (`:19`).

**Ordre topològic i claus naturals** (`_spec()` `:127-164`):

| Model | clau natural | notes |
|---|---|---|
| BodyMeasurementISO | `codi_intern` | |
| POMCategory | `codi` | |
| GarmentGroup | `codi` | |
| Target / FitType / ConstructionType | `codi` | |
| SizeSystem | `codi` | `parent` DEFER (2a passada); M2M `targets` |
| SizeDefinition | `(size_system, etiqueta)` | |
| POMGlobal | `codi` | **copia del tenant origen** → si origen=fhort, arrossega els 149 LOSPOM |
| GarmentTypeGlobal | `codi` | |
| GarmentType | `codi_client` | **sense unique DB** → risc de duplicat silenciós |
| POMMaster | `codi_client` | **sense unique DB** + 12 duplicats (§A1.2) → risc |
| GradingRuleSet | `nom` | força `customer=NULL`; amb `--profile` grading només `origen=CANONICAL` |
| GarmentTypeItem | `(garment_type, code)` | unique_together real |
| GarmentPOMMap | `(garment_type_item, pom)` | |
| GradingRule | `(rule_set, pom)` | amb perfil, només rules de rulesets CANONICAL |
| SizingProfile | `(target, garment_type, construction, fit_type, size_system, version)` | força `customer=NULL` |
| TaskTimeEstimate | `(garment_type_item, task_type)` | welford a 0 |
| TimeSeed | `(scope, key)` | |

- **NO crea Customer** (`bootstrap_tenant`); llegeix el self-Customer (`is_self=True`) creat per
  migració i li propaga `codi_global` (`:348-356`). Força `customer=NULL` a GradingRuleSet i
  SizingProfile (`:152,:159`).
- **DocumentTemplate "Template FTT"** es **genera** per codi (`seed_master_template()` `:439-440`,
  `get_or_create(nom='Template FTT')`), no es copia.
- **TaskType NO es copia** (neix per migració 0025); `GradingException` jubilada (0 files); **cap
  signal de domini** connectat als models sembrats (grep buit).
- Amb `--profile` (perfil de blocs `SeedProfile`, public/SHARED): si el bloc `grading` hi és,
  **només viatgen rulesets `origen=CANONICAL`** (`:393-404`); sense `--profile`, copia **tots** els
  rulesets de l'origen.

**Col·lisions que el loader trobarà** (bootstrap fa `update_or_create` → SOBREESCRIU defaults en
col·lisió, mai delete):

| Objecte | clau on xoca | risc per al loader |
|---|---|---|
| GradingRuleSet canònic | `nom` | clau NO inclou customer/origen → un CLIENT_RUN LOSAN amb `nom` coincident amb un CANONICAL de fhort col·lisiona. Els noms LOS ("LOS Kids Knit…") són distints → risc baix a la pràctica, però el loader ha d'usar `get_or_create` propi. |
| POMMaster | `codi_client` | sense unique DB + 12 duplicats → si el loader crea sense mirar la parella exacta, **duplica**. |
| GarmentType | `codi_client` | sense unique DB → mateix risc de duplicat. |
| GarmentTypeItem | `(garment_type, code)` | unique DB real → força update, no duplicat. OK si el loader respecta la parella. |
| SizeSystem/SizeDefinition/Target/FitType | `codi`/tupla | reusar `codi` idèntic per no duplicar. |
| DocumentTemplate "Template FTT" | `nom` | si LOSAN reusa aquest `nom`, bootstrap el regenera a `origen='sistema'`. Usar un `nom` propi. |

**Regla operativa del loader (llei "el paquet MANA sobre l'estat, sense esborrar res que no sigui
seu"):** create-if-missing sobre **exactament** aquestes claus naturals; en trobar l'objecte, el
paquet pot **actualitzar els seus camps** (mana sobre l'estat) però **mai fer delete**. ⚠️ Cal saber
que **si bootstrap torna a córrer** després del loader, **actualitzarà** (no saltarà) qualsevol
objecte de clau coincident, forçant `customer=NULL` als rulesets → el loader s'ha d'executar
**després** del bootstrap, no abans, i el disseny ha d'assumir que bootstrap ja ha posat el catàleg
canònic.

---

## §A3 — Disseny del paquet (💡 PROPOSTA a validar)

Directori: `fhort/pom/seed_data/losan_package/`. Tot per **clau natural** (codis, mai pk). Ordre de
càrrega = ordre numèric.

```
manifest.json          ← recomptes esperats/capa + sha256 per fitxer + commit d'origen
01_customer.json       ← (⚠️ D-A: en tenant-native NO hi ha Customer → veure nota)
02_pom_globals.json    ← 149 LOSPOM-* (per `codi`) — NO són shared (§A1.3)
03_pom_masters.json    ← POMMaster referenciats; clau = pom_global.codi | codi_client (§A1.2)
04_pom_aliases.json    ← 196 àlies (⚠️ D-A·b: com aterren al tenant-native, §A4.2)
05_garment_catalog.json← GarmentGroup(12) + GarmentType(21) + GarmentTypeItem(62)
06_pom_maps.json       ← 1748 GarmentPOMMap + 37 ItemBaseMeasurement
07_size_systems.json   ← 11 SizeSystem LOS + 86 SizeDefinition + targets M2M
08_rulesets.json       ← 19 GradingRuleSet + 9 RuleSetScopeNode
09_rules.json          ← 409 GradingRule (per CODI/àlies de POM, talla per etiqueta)
10_profiles.json       ← 18 SizingProfile customer=6 (+? 4 NULL, §A1.7)
11_document_template.json (💡 opcional, §A1.8) ← capçalera LOSAN + logo
```

Matisos respecte al brief:
- **`02_pom_globals` és imprescindible** (el brief l'incloïa; confirmat: NO és shared).
- **Clau natural del POMMaster**: `pom_global.codi` quan n'hi ha, `codi_client` de reserva (§A1.2).
- **`01_customer` en tenant-native (D-A):** o bé no s'emet, o bé porta només metadada (logo) per a
  un self-Customer del tenant. Decisió al gate.
- **manifest**: recompte esperat per capa (els d'aquest doc), sha256 de cada fitxer, i el commit
  d'origen del paquet (config versionada).

**Verificació d'export (FASE B):** recomptes del manifest == cens d'aquesta FASE A (taula §A5).

---

## §A4 — D-A · Tenant-native, sense Customer (customer=NULL): resolució AMB DADES

### A4.a · Nul·labilitat i matcher

- `GradingRuleSet.customer` `null=True, blank=True, db_constraint=False` (`pom/models.py:552-554`).
- `SizingProfile.customer` `null=True, blank=True` (`pom/models.py:933-935`); semàntica explícita
  `:929`: **NULL = perfil genèric del tenant**. Els 4 NULL de §A1.7 ja hi encaixen.
- **⚠️ El matcher NO funciona amb customer=NULL** (blocador de CODI, no de dades):
  `resolve_grading_container` (`pom/grading_utils.py:577-651`) té guarda d'entrada
  `if not (customer and size_system): return {'container': None, ...}` (`:608-609`) → **aborta sense
  customer**. A més filtra `customer=customer` (`:618,:630`) i `origen=ORIGEN_CLIENT_RUN`
  (`:617,:629`); i CLIENT_RUN "MAI viatja a tenant nou" (`pom/models.py:511-514`). Els germans
  `cerca_client_equivalent` (`:132`) i `cerca_contenidor_client` (`:548`) comparteixen la guarda.
- El bessó de frontend és `matchingRuleSetsStrict` (`gradingAxes.js:151-162`); `matching_rule_sets_strict`
  a Python **NO EXISTEIX** (la paritat la fa `resolve_grading_container` + `_scope_matches`).

**Conseqüència D-A·a:** perquè el motor confiï en contenidors tenant-native cal, com a mínim,
(i) que el context d'import aporti customer o que la guarda accepti tenant-native, i (ii) que el
matcher consumeixi contenidors amb `customer=NULL` (avui exclosos per la llei RUN-CLIENT). **Són
canvis de motor a fer a la FASE C**, no dades del paquet.

### A4.b · La nomenclatura com a nativa (plegar àlies a `codi_client`)

**⚠️ La proposta del brief xoca amb les dades:**
- `POMMaster.codi_client` **ja té 12 duplicats** (§A1.2) → no és clau única; plegar-hi els àlies
  n'hi afegiria més.
- **7 POMMaster tenen >1 àlies LOS** — no tots són variants de puntuació:

| POMMaster | codi_client | àlies LOS | tipus |
|---|---|---|---|
| 513 | U1 | `U1`, `U.1` | puntuació pura |
| 681 | H.12 | `H.12`, `H12` | puntuació pura |
| 295 | BIC | `H`, `H19` | **semàntic** (2 codis reals) |
| 296 | ELB | `H4`, `SR9` | **semàntic** |
| 457 | S | `S22`, `S44` | **semàntic** |
| 492 | V | `V18`, `V`, `V3` | **semàntic** (3) |
| 668 | S.35 | `S.35`, `V.2` | **semàntic** |

- **NO EXISTEIX normalitzador de puntuació** d'àlies: tota la comparació de `client_code` és literal
  o `iexact` (`extraction_views.py:773`, `services.py:471,492`, `repair_customer_aliases.py:147,186`);
  la migració 0032 detecta el patró punteijat però **conserva el punt**. → `H.12` i `H12` són àlies
  DISTINTS i no col·lapsen sols.
- **La llei de POM** (`find_pom_master`, `extraction_views.py:728-857`) **salta tota l'estratègia
  d'àlies quan customer=NULL** (`if customer is not None:` `:770`) → en tenant-native sense customer,
  la resolució per àlies **no s'activa**; queda descripció + `codi_client` legacy.

**💡 PROPOSTA A4.b (decisió d'Agus al gate, no en silenci):** plegar els àlies **d'1 sol codi** a
`codi_client` és viable (previ normalitzat de puntuació per als 2 casos U.1/H.12), però els **5 POMs
amb àlies semànticament distints** (295/296/457/492/668) **no** poden reduir-se a un sol codi sense
perdre codis reals. Opcions:
  - **(O1)** Mantenir `CustomerPOMAlias` com a taula al paquet (viatja tal qual), amb un `customer`
    self del tenant o customer=NULL — però `find_pom_master` no la consulta sense customer (cal
    tocar `:770`).
  - **(O2)** Plegar a `codi_client` només els univocs i **conservar àlies** per als 7 multi-àlies.
  - **(O3)** Model híbrid: `codi_client` = codi LOS primari; la resta de codis com a àlies natius.
  Cap sense decisió d'Agus.

### A4.c · Commands que resolen per `customer='LOS'` (cap té mode tenant-native)

Font única del codi: `CUSTOMER_CODI='LOS'` (`seed_data/losan_ss27.py:142`, `losan_grading_v3.py:17`,
`consolidate_pom_los.py:45`). **Cap resol per id=6; cap té `--tenant-native` ni customer opcional**
(grep buit). Llista completa (l'adaptació es fa a la FASE C):

| Command | resolució LOS | guarda si falta LOS |
|---|---|---|
| `seed_losan_models.py:79` | `Customer.filter(codi='LOS').first()` | `CommandError` `:81` |
| `seed_losan_ss27.py:136` | `filter(codi=CUSTOMER_CODI)` | — |
| `seed_losan_grading_v3.py:57` | `Customer.get(codi=CUSTOMER_CODI)` | `get()` peta |
| `seed_losan_rules.py:69` | `filter(codi=CUSTOMER_CODI)` | — |
| `seed_losan_rules_v2.py:68` | resol POM via `CustomerPOMAlias(customer=LOS, client_code=…)` | — |
| `seed_losan_master_delta.py:70` | `filter(codi=CUSTOMER_CODI)` | — |
| `seed_master_delta_catalog.py:58` | sembra àlies `customer=los` | `CommandError` `:60` |
| `delete_master_delta_seed.py:48` | assercions dures `customer=los` | `CommandError` `:50` |
| `consolidate_pom_catalog.py:54` | tot el motor `customer=self.los` | `get()` peta |
| `cleanup_losan_old.py:76` | `filter(customer__codi=CUSTOMER_CODI)` | skip |
| `validate_los_maps.py:41` | `Customer.get(codi=CUSTOMER_CODI)` | `get()` peta |

**El més crític:** `seed_losan_models.py` (B2, el que carrega els 961 models al final de la FASE C)
**aborta sense Customer LOS** i escriu `customer=los` a tot. En tenant-native cal, o bé un
**self-Customer** al tenant amb `codi='LOS'`, o bé un **mode `--tenant-native`** que accepti
customer opcional i escrigui NULL. Coherent amb A4.a i A4.b, això obliga a **decidir la política de
customer del tenant abans de l'assaig** (FASE C, pas 0).

### A4.d · Origen dels rulesets

Avui 18/19 rulesets LOS són `CLIENT_RUN` (1 és `None`, grs 104). La llei del motor tracta CLIENT_RUN
com "MAI viatja a tenant nou" (`pom/models.py:511-514`) i el matcher només consulta CLIENT_RUN amb
customer no-null. **💡 PROPOSTA (gate):** en un tenant propi té més sentit **origen `CANONICAL`**
(perquè el matcher tenant-native els trobi i perquè bootstrap els respecti), conservant la
provinença històrica en un camp de nota. Cap canvi sense decisió d'Agus (D-A·d).

---

## §A5 — TAULA de cens per al manifest + QA de fidelitat (per codi_client, D-B)

| Capa | recompte staging (fhort) | clau natural |
|---|---|---|
| CustomerPOMAlias (customer 6) | **196** | `(customer, client_code)` |
| POMGlobal LOSPOM-* (fhort) | **149** | `codi` |
| POMMaster referenciats (àlies∪rules) | **197** (unió amb maps/itembase: 254) | `pom_global.codi`\|`codi_client` |
| GarmentGroup / GarmentType / GarmentTypeItem | **12 / 21 (17 act) / 62** | `codi` / `codi_client` / `(gt,code)` |
| GarmentPOMMap / ItemBaseMeasurement | **1748 / 37** | `(gti, pom)` |
| SizeSystem LOS / SizeDefinition | **11 / 86** | `codi` / `(ss, etiqueta)` |
| GradingRuleSet LOS / RuleSetScopeNode | **19 / 9** | `nom` |
| GradingRule LOS | **409** | `(rule_set, pom)` |
| SizingProfile customer 6 (+NULL sobre LOS) | **18 (+4)** | tupla de 6 |
| Models (NO al paquet; via CSV) | 962 | — |

## TAULA FINAL de riscos / decisions per al CTO

| # | Tema | Estat | Decisió que cal (gate) |
|---|---|---|---|
| R1 | POMGlobal LOSPOM-* **no són shared** (0 a public, 149 a fhort) | FET | Confirmar `02_pom_globals` al paquet, reconciliació per `codi` |
| R2 | `POMMaster.codi_client` **no és clau única** (12 duplicats) | FET | D-A·b: clau natural = `pom_global.codi`\|`codi_client`? |
| R3 | **7 POMs amb >1 àlies** (5 semàntics) | FET | D-A·b: O1/O2/O3 — no plegar en silenci |
| R4 | **customer=NULL bloqueja el matcher** (guarda + origen CLIENT_RUN) | FET | D-A·a/d: tocar `grading_utils.py` a FASE C + origen CANONICAL? |
| R5 | **11 commands cablen `customer='LOS'`**, cap tenant-native | FET | D-A·c: self-Customer LOS al tenant **o** flag `--tenant-native` |
| R6 | **5 GradingRule sobre POM inactiu** (grs 104) | FET | D-C: viatgen (QA espera 5, no 0) **o** depurar? |
| R7 | **1 clau wizard ambigua** (3 profiles NEWBORN→3 rulesets) | FET | "cada cas→1 ruleset" no es compleix: resoldre o acceptar |
| R8 | **4 SizingProfile customer=NULL** sobre grs 104 | FET | viatgen al paquet? (en tenant-native ja hi encaixen) |
| R9 | **Capçalera LOSAN (DocumentTemplate + logo)** fora dels 10 fitxers | FET | dins paquet (`11_*`) o entrega manual? logo sense Customer? |
| R10 | Numeració FTT interna renumera (D-B); `ModelSequence` arrenca de zero | FET | cap acció; QA compara per `codi_client` |

---

*FASE A completa. Read-only: cap escriptura fora d'aquest doc. **GATE** — esperant que l'Agus validi
cens + col·lisions bootstrap + disseny + decisions D-A·b/c/d i R6/R7/R8/R9 abans de la FASE B (export).*
