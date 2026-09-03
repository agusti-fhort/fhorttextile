# DIAGNOSI PRE-SEMBRA V4 — catàleg, elements i esquema definitiu

**Data:** 2026-08-07 · **Protocol:** PROTOCOL_FASE_B (director + 7 investigadors + documentador)
**Mode:** LECTURA PURA. Cap escriptura a cap BD viva, cap migració, cap `manage.py` que no sigui shell de consulta o `showmigrations`.
**Entorn:** staging `178.105.48.204`, `/var/www/ftt-staging`, BD `127.0.0.1:5433`.
**Abast:** els 12 punts del brief (A1-A5, B1-B5, C1-C2). Tots respostos.

> Aquest document és la **síntesi autoritativa**. Les definicions de model enganxades senceres,
> els fragments de codi i els censos exhaustius viuen als set informes de bloc (§ Annexos).
> Cap recomanació d'implementació: només terreny. Les decisions són del Patró C.

---

## 0 · LÍMITS GLOBALS D'AQUESTA DIAGNOSI

Llegir-los abans que res: acoten què val i què no d'aquest document.

1. **Els documents del vault NO són en aquesta màquina.** `CATALEG_CANONIC_BROWNIE_V4.md` i
   `GRADING_ENTRADA_MODELS_BROWNIE.md` no existeixen a cap path de staging (cercat a `/root`,
   `/home`, `/var/www`). Només `DIAGNOSI_MULTIPECA_DALIA.md` és al repo.
   **Conseqüència dura:** la pregunta d'A1 «¿els 21 POMs no confirmats són nous o duplicats?»
   es respon aquí com a **terreny** (què hi ha al catàleg, amb el CSV complet) i **no com a
   contrast** (què hi falta respecte del v4). El contrast l'ha de fer qui tingui el v4 al davant.
2. **`element` no existeix enlloc del codi** — ni entitat, ni camp, ni migració. Tot el
   dimensionament del bloc B assumeix «hi haurà un tercer/quart eix» i és per tant una
   projecció sobre l'esquema actual, no una mesura.
3. **PROD no s'ha llegit.** Sense SSH. Tots els números són de staging o del dump del 06/08.
4. **El frontend s'ha censat per grep** a B3; llegit de debò a A5, B1, B2/B5 i B4.

---

## 1 · ELS SET FETS QUE CANVIEN EL TERRENY

Ordenats per quant reescriuen el pla, no per bloc.

### 1.1 🚨 `pom.0073_u2_acumulacio_poms` NO està aplicada — i hi ha DUES `0073`

Verificat tres vegades independentment (A1, B4, i directament).

| app | última aplicada | estat |
|---|---|---|
| `pom` | `0072_cat22_sembra_garmentgroup` | **`0073_u2_acumulacio_poms` pendent** |
| `models_app` | `0079_m3_derivat_de_rule_set` | totes aplicades |

**Compte amb la confusió, que és cara:** `models_app.0073_instancia_mesures` **sí** està
aplicada; `pom.0073_u2_acumulacio_poms` **no**. El 🚩 de la memòria és el de `pom`.

Conseqüència: `GarmentTypePOMMap` i `GarmentGroupPOMMap` existeixen **només com a Python**.
Les taules **no existeixen a cap dels tres schemes**. Per tant, avui:

- `acumula_poms_de_item()` **peta amb `ProgrammingError`** contra qualsevol item (tots tenen família).
- L'endpoint `/acumulacio/` és un **500 segur**.
- Qualsevol codi que recorri `POMMaster._meta.related_objects` i toqui els accessors
  **peta** — inclòs `_cens_relacions` a `cataleg_views.py:37`.
- Als CSV d'A1, les columnes d'aquestes dues taules surten **`ERR`**, no `0`.

El brief demanava distingir «0» de «no res». Aquí **no és 0: és que la taula no hi és**.

### 1.2 🚨 `POMMaster` no té cap unicitat sobre `codi_client` — i ja hi ha 12 duplicats

Sense constraint. A `fhort.pom_pommaster`: **12 `codi_client` duplicats (24 files)**, dos amb
col·lisió semàntica real (`BJ`, `H`). Sembrar 25 POMs nous del v4 contra aquesta taula **no
té cap xarxa**: un codi repetit entra sense queixar-se.

Relacionat i pitjor per al v4: **`S` i `S2` no són un POM cadascun — n'hi ha DOS de cada**
(457/581 i 458/583). Tota la càrrega viu als 457/458; els «COLLAR» bessons tenen 1 fila entre
tots dos. Qualsevol creuament del v4 per etiqueta `S`/`S2` és ambigu d'entrada.

### 1.3 🚨 El catàleg de POMs no té gate d'escriptura

`POMMasterViewSet` (`backend/fhort/pom/views.py:54`) és un **`ModelViewSet` complet amb només
`IsAuthenticated`**: POST / PUT / PATCH / **DELETE** oberts. El seu germà `SizeSystemViewSet`
(`:88`) **sí** té `get_permissions → _ConfigureWrite`. El catàleg de POMs no.
El seu `destroy` **no té guard de dependències**, i esborrar un POMMaster **s'enduu els seus
`CustomerPOMAlias` per CASCADE** (2 de les 16 relacions són CASCADE, les altres 14 PROTECT).

Segon camí d'esborrat massiu: `reseed_tenant_fhort.py:236` fa `.all().delete()` **sense dry-run**.

### 1.4 🔑 La resposta d'A2 és NO, i la d'A4 és ZERO

- **A2:** cap dels 13 camps de `CustomerPOMAlias` proposa capa, instància ni terna. Cap JSON,
  cap `meta`, cap `default_*`, cap FK a `MeasurementLayer`/`MeasurementInstance`. L'únic que
  hi frega és `es_instancia` (booleà, `models.py:533`) i **el comentari del codi declara que
  deliberadament no desa QUINA instància és**.
- **A4/A5:** **cap fila de cap taula porta slug compost**, ni viu ni al dump. Les 29 files amb
  instància a tot `fhort` són **totes simples** (`left`, `right`, `cb`). El format compost és
  una capacitat construïda que **encara no ha produït ni una fila**.

Això vol dir que **moure `waistband_seam` d'eix i introduir DATUM són 0 files a migrar**.

### 1.5 🔑 Multipeça: la màquina existeix, però ningú l'ha engegada mai

| | `fhort` | `los` |
|---|---|---|
| `GarmentSet` | 0 | 0 |
| `Model` TOTAL | **0** (wipe) | 51 |
| `GarmentTypeItem` | 62 | 1 |
| **`is_set=True`** | **0** | **0** |
| **`GarmentTypeItemPart`** | **0** | **0** |

L'avís del brief queda **refutat en un sentit útil**: el 0 de `GarmentSet` a `fhort` no diu res
(wipe), però **el 0 de `is_set` i `GarmentTypeItemPart` viu al CATÀLEG i no depèn del wipe**.
Cap tenant ha declarat mai un item-conjunt, i per tant l'única màquina que crea `GarmentSet`
no s'ha engegat mai. **Absorbir o jubilar multipeça no té cap cost de dades.**

El forat que ho explica: `PUT /api/v1/garment-type-items/<id>/parts/` existeix
(`tasks/views_b.py:1020-1078`) però `ItemAuthoring.jsx` no en té cap hit i `endpoints.js` no
l'exposa. **El wizard sap fer conjunts; no hi ha manera de declarar-ne un al catàleg.**

### 1.6 🚨 La FK `element` nullable trenca la unicitat en SILENCI

El precedent C1/C1-ins («mateixes columnes + una → estrictament més permissiva») **NO s'aplica**.
`capa` i `instancia` són `NOT NULL` amb default no-nul. Un `element_id` **NULL** fa que Postgres
tracti els NULLs com a **distints** dins l'índex UNIQUE → **la unicitat del contenidor implícit
desapareix sense que res peti**.

Terreny disponible: PG **18.4** + Django **6.0.5** → `nulls_distinct=False` existeix, però
`unique_together` no ho sap expressar (cal `UniqueConstraint`). **`POMPlacement` ja té feta
aquesta conversió** des de la `0071`; `BaseMeasurement` i `ModelGradingRule` no.

### 1.7 🚨 La constraint de `ModelGradingRule` no té pin, i el cens del brief es quedava curt

`tests_sembra_grading.py`: 2.038 línies, 13 classes, **106 tests**, i **un sol** toca la clau
com a clau — i hi entra per la preservació, no per la constraint. **No hi ha cap
`assertRaises(IntegrityError)` a tot el projecte** per a un `(model, pom)` duplicat.
`capa` i `instancia` sí que tenen pins d'`information_schema`. La clau d'aquesta taula, no.

El brief deia 6 `materialize_*` + 2 deletes crus. **Els 6+2 són exactes**, però n'hi ha més
que cap grep pel nom veu (§ 3.3).

---

## 2 · BLOC A — CATÀLEG

### A1 · Bolcat complet de `POMMaster` [W14]

**Consultat:** `POMMaster` (`fhort/pom/models.py`), els tres schemes via `SET search_path`,
cens de relacions amb `_meta.related_objects`.

**Resultat:**

| schema | files POMMaster |
|---|---|
| `public` | **0** (la taula hi és — app SHARED+TENANT — però buida) |
| `fhort` | **396** |
| `los` | **0** |

**LOSAN no té catàleg propi: viu dins de `fhort` com a `Customer` `LOS`.** Confirmat per dos
investigadors independentment. `los` sí té 51 models vius.

Camps: **l'únic camp de nom propi és `nom_client`**. **No existeix `nom_fitxa` a `POMMaster`**
(el `nom_fitxa` de les notes antigues és de `BaseMeasurement`). El multilingüe només arriba per
la FK `pom_global` → **122 de 396 (31 %) la tenen NULL**.

Salut del catàleg: **254/396 (64 %) amb `pendent_revisio=True`** · 219 sense `categoria`.

**Orfes — el 93 de la sessió anterior explicat:** els orfes són **106**, dels quals **93 amb
`actiu=True`** i 13 desactivats. No és creixement: són **dos talls diferents del mateix conjunt**.
37 d'ells no tenen **cap** relació viva. A més, **230 sense cap `GarmentPOMMap`** i 58 doblement orfes.

**Cens de relacions:** 16 models apunten a `POMMaster`. Dos detalls que un cens per
`information_schema` hauria perdut:
- **`ModelGradingRule` amb `db_constraint=False`** — invisible a `information_schema`.
- **`patterns.PatternPOM` usa el camp `pom_master`, no `pom`** — un cens per nom de camp el perd.

**CSVs:** `A1_pommaster_fhort.csv` (396 files + capçalera, 33 columnes),
`A1_pommaster_public.csv` i `A1_pommaster_los.csv` (només capçalera).
Columnes `n_GarmentTypePOMMap` i `n_GarmentGroupPOMMap` = **`ERR`** per § 1.1.

**No determinat:** si els 21 POMs no confirmats del v4 són nous o duplicats — **cal el document
del vault** (§ 0.1). El CSV és l'insum per fer-ho; el creuament no.

### A2 · `CustomerPOMAlias` — definició literal [W15]

**Consultat:** `fhort/pom/models.py` (model complet), `serializers.py:632-646`,
`seed_brownie_germans.py`, recomptes als tres schemes.

**Resultat — la pregunta concreta té resposta NO, rotund.** 13 camps, cap dels quals proposa
capa, instància ni terna. Prova per enumeració completa a `_A_cataleg_bd.md`.
L'únic camp veí és `es_instancia` (BooleanField, `models.py:533`), i el comentari del codi
declara **deliberadament** que no desa quina instància és.

L'escriu **un sol lloc**: `seed_brownie_germans.py:129`. El serializer **no l'exposa** →
per API no s'hi pot escriure. Files amb `es_instancia`: **16 a `fhort`, totes de BRW; ZERO a LOS**.

**Àlies per schema i customer:** `fhort` **390** (LOS 240 · BRW 148 · FTT 2) · `public` 0 · `los` 0.
Per origen: DICCIONARI 337 · IMPORT 48 · MODEL 3 · MIGRACIO 2 · **MANUAL 0**.

### A3 · Cens de lectors i escriptors de `POMMaster` [W16]

**Consultat:** grep ample (`POMMaster`, `POMGlobal`, `pom_pommaster`, `pom_pomglobal`,
`pom_master`), `_meta.related_objects`, `backend/fhort/*/management/commands/`, `scripts_tmp/`.

**Correcció de nomenclatura al brief:** `POMMaster._meta.db_table` és **`pom_pommaster`**.
`pom_pomglobal` és la taula de **`POMGlobal`**. La nota de memòria «el FK de POMMaster va a
`fhort.pom_pomglobal`» és **correcta** i es refereix a la FK `POMMaster.pom_global` (nullable) —
no al nom de la taula de `POMMaster`. Verificat directament.

**Resultat — la llista de «4 portes» torna a quedar-se curta, com el precedent avisava.**

**Lectors: ~110 camins.** Només **13** filtren per àlies, i gairebé tots pengen de dos punts
(`pom/nomenclatura.py:33` i `:85`). **Els ~97 restants llegeixen el catàleg del tenant sense
saber de quin client parlen** — inclosos `POMMasterViewSet` (que serveix el catàleg sencer a la
UI), les 6 estratègies de `find_pom_master`, `federation_service._resol_pom_al_desti`, i el camí
on la IA proposa un codi (`views.py:2733`).

**Escriptors: 11, no 4.** Els que `POMMaster.objects.create` no veu:
- **`POMMasterViewSet` (`pom/views.py:54`)** — § 1.3.
- **`wizard_views.py:722`** (`edit_pom_nomenclature_view`) — **muta `codi_client`/`nom_client`**
  sense validació d'unicitat ni guard de POM compartit. Amb § 1.2 (cap unicitat), això és el
  camí curt cap a un 13è duplicat.

**Esborrat:** 2 camins, tots dos arrosseguen `CustomerPOMAlias` per CASCADE (§ 1.3).

**Còpia public→tenant: CAP.** Els 3 camins que toquen `public` hi escriuen **`POMGlobal`**, no
`POMMaster`. L'única còpia és **tenant→tenant** (`bootstrap_tenant.py`), per **clau natural
`codi_client`** — coherent amb la llei «els ids no valen entre schemes».

**Resposta a la pregunta del brief:** sembrar el v4 **no és una operació aïllada**. No pel costat
de la còpia entre schemes (que no existeix), sinó perquè **~97 lectors sense noció de client**
veuran els POMs nous immediatament, i perquè el catàleg no té ni unicitat ni gate d'escriptura.

### A4 · `MeasurementInstance` — estat exacte

**Consultat:** `pom/models.py:294-316`, `identity_views.py`, `seed_measurement_instances.py`,
recomptes als tres schemes, i escombrada de les 12 columnes `instancia`.

**Resultat:** **10 files idèntiques als tres schemes** (8 POSICIO + 2 ESTAT), totes `SEED`/`is_system`.
Les comportes CHECK ja no hi són (`0057` aplicada).

**I zero consumidors:** totes les columnes `instancia` de totes les taules dels tres schemes són
`''` (1748 `GarmentPOMMap`, 37 `ItemBaseMeasurement`, 2 `POMPlacement`).
→ **Moure `waistband_seam` de POSICIÓ a DATUM són 0 files a migrar.**

| què | cost |
|---|---|
| `EIX_CHOICES` | `backend/fhort/pom/models.py:294-297` |
| `EIX_NOMS` | `:303-306` |
| camp `eix` | `:316` — `max_length=8`, **`DATUM` hi cap** |
| afegir OPCIONS | **no toca esquema**, però **no és dada 100 % pura**: l'endpoint és read-only (`identity_views.py:55`), no hi ha serializer ni viewset. L'única porta és `seed_measurement_instances.py:37-63`, **hardcodejada** |
| afegir un EIX | `AlterField(choices)` obligatori per Django però **noop a la BD** (no hi ha CHECK) + `EIX_NOMS` (si no, la columna surt sense capçalera) + `seed_...py:66` i `:124-130` |

**🚨 Bandera nova (A4.6):** `composaInstancia` (`frontend/src/utils/diccionariMesures.js:109`)
ordena els trams per `Object.keys(dicc.instancies)`, que el backend emet **alfabèticament**
(`['ESTAT','POSICIO']`), mentre `dicc.eixos` va en ordre **declarat** (`['POSICIO','ESTAT']`).
Verificat contra la BD viva: **el mateix payload porta les dues llistes en ordre invers** →
compondria `relaxed-left` en lloc de `left-relaxed`, **contra el seu propi docstring**.
Inert avui (cap fila té instància), **armat** per al dia que n'hi hagi.

**I una conseqüència de disseny:** `eixPrincipal` = «el primer eix declarat» és el que es gira
en partir un POM. **On es col·loqui `DATUM` dins de `EIX_CHOICES` és una decisió de comportament,
no d'ordre visual.**

### A5 · Format d'instància [W13]

**Consultat:** `diccionariMesures.js`, `capaInstancia.js`, `identity_views.py`, `pom/identitat.py`,
i el dump del 06/08 llegit **sense restaurar** (`pg_restore --data-only --table=… -f fitxer`,
extracció del bloc `COPY` a disc).

**Resultat: zero.** Cap fila de cap taula del dump porta slug compost. Escombrades les 12 taules
amb columna `instancia`: **29 files amb instància a tot `fhort`, totes SIMPLES**. A BD viva: **0**.

**Generació: un sol lloc, i és al FRONT** (`diccionariMesures.js:106`). El backend **no compon
slugs**: només emet el separador com a dada (`identity_views.py:98`) i tracta la instància com a
**text opac** arreu (`pom/identitat.py` no la desmunta mai). **Cap CHECK de BD restringeix el
valor**; l'única invariant és `instancia_exigeix_nom`.

**⚠️ El separador viu duplicat al front, amb dues fonts:** `diccionariMesures.js:104` el llegeix
del backend; **`capaInstancia.js:70` el té hardcodejat i no consulta mai el diccionari.**
Canviar només el backend trencaria l'etiquetatge.

**Sobre «migrar al format de la llei» — la premissa s'ha de revisar:** hi ha **dos separadors i
la llei només parla d'un**.

| | separador | on |
|---|---|---|
| **CODI** (`nom_fitxa`) | concatenat (`sufix_separador: ''`) | això és D-31.26 |
| **SLUG** | guionet (`instancia_separador: '-'`) | `models.py:260`, i **els tests l'afirmen**: `diccionariMesures.test.js:55` assegura literalment que `AHL ≠ AH-L` |

**No s'ha trobat cap font que digui que el SLUG hagi d'anar concatenat.**

Cost de dades: **0 files en tots dos escenaris** (BD buida o dump restaurat — un slug simple és
idèntic en tots dos formats). **El bloqueig real no és de dades: és que `tramsInstancia` deixaria
de ser invertible** — desmuntar `leftrelaxed` exigeix un prefix-match contra un diccionari que
té slugs amb `_` (`waistband_seam`) i que és **extensible pel tenant**.

---

## 3 · BLOC B — ELEMENTS

### B1 · Multipeça viva [P1]

**Consultat:** `models_app/views.py:788-1032`, `docs/diagnosis/DIAGNOSI_MULTIPECA_DALIA.md`,
grep ample, recomptes als tres schemes.

**Ubicació:** `create_model_wizard` és a **`backend/fhort/models_app/views.py:788-1032`**,
**no** a `pom/wizard_views.py`.

**🔑 La branca NO la tria el payload: la tria `GarmentTypeItem.is_set`** (`views.py:841-878`,
comentari literal «EL GTI MANA»). `is_multipiece`/`num_pieces` són només redundància verificable
→ 4 codis de 400 si contradiuen el catàleg.

| branca | línies | crea | transacció |
|---|---|---|---|
| Peça única | `:913-953` | 1 `Model` → `models_app_model` + `models_app_modelgradingrule` (només si hi ha ruleset). Resposta `{id, codi_intern}` | **el `create` és FORA de transacció** |
| Conjunt | `:955-1032` | 1 `GarmentSet` + N `Model` amb `piece_number` + **N tandes de regles, una per peça amb el ruleset de la peça**. Resposta `{garment_set_id, codi_base, num_pieces, pieces[]}` — **sense `id`** | tot dins d'un sol `atomic()` |

Clau: `views.py:967-973` — cada peça **reescriu** `garment_type_item_id`, `grading_rule_set_id`
i `base_size` amb els del seu `part_item` abans de passar per `_resolve_garment_def`.

**🚨 `DIAGNOSI_MULTIPECA_DALIA.md` (27/07 matí) va quedar superada el mateix dia a la tarda**
pel sprint SET-1 (5 commits: `f3200dcc`, `20804146`, `607e15f7`, `31009911`, deploy `1758199c`).
Tres punts on ja no descriu el codi:

1. «Frontend NO EXISTEIX» → **n'hi ha 3 superfícies** (wizard, fitxa, llista) + i18n als 3 idiomes.
2. «El bloqueig és la clau `(model,pom)`» → la clau real és **`('model','pom','capa','instancia')`**
   (`models_app/models.py:769`), i **les comportes CHECK de C1 ja no hi són** (C4 les va retirar;
   només queda `instancia_exigeix_nom`). **El comentari de `models.py:669-674` que DALIA cita és
   stale i contradiu la seva pròpia Meta 100 línies avall.**
3. «Secció es perd a l'extracció» → `BaseMeasurement.seccio` existeix (`:675`), sense cap
   consumidor estructural.

També nou des de DALIA: **meritació de conjunt SÍ existeix** (`_meritar_conjunt`,
`tasks/services_c.py:191-239`, SET = 1 mèrit).

**Cens:** 2 models nous, 8 camps apuntadors (2 amb CheckConstraint XOR), 4 migracions, 11 punts
de vista, 6 serializers, 6 management commands, 5 fitxers de test, 3 superfícies de frontend.
**`GarmentTypeInstance` → 0 hits al repo. `es_multipeca` → 0 hits.**

**Recomptes i la seva lectura:** § 1.5. **Absorbir o jubilar multipeça no té cap cost de dades.**

**Proposta de nom (proposta, no decisió):**

**🚨 La col·lisió greu no és «set»: és `GTI`.** El brief l'usa com a *garment type **instance***,
però **al repo `GTI` ja vol dir `GarmentTypeItem` a 20+ llocs** (`commerce/models.py:54,190-209`,
`accounts/models.py:44`, `pom/models.py:978`…). `GarmentTypeInstance` faria l'acrònim ambigu a
tot el codi ja escrit.

| candidat | col·lisió (grepejada) |
|---|---|
| **`ModelElement`** | **0 hits. `Element` lliure al 100 %** — l'única sense col·lisió real |
| `ModelPiece` | `Piece` és triple: `PatternPiece`, `PieceFitting`, `piece_number` |
| `ModelComponent` | lliure al backend, però `prod.components` ja existeix al frontend comercial |
| `ModelPart` | `parts` ja és related_name viu de `GarmentTypeItem` |
| `GarmentInstance` | seria el 25è `Garment*` |

**Nota que va amb la proposta:** hi ha **dues** entitats absorbibles i **no són intercanviables** —
`GarmentSet` (contenidor comercial, **instància**) i `GarmentTypeItemPart` (composició de
**catàleg**, plantilla). L'ELEMENT ocupa la posició de la instància. Si la plantilla també
s'absorbeix és decisió del Patró C.

### B2 · `BaseMeasurement` — la quaterna [P2]

**Consultat:** `models_app/models.py:588-836` (Meta a `:755-832`), `serializers.py:425,465-492`,
constraints reals llegides de la BD, `pom/identitat.py`, `TechSheetEditor.jsx`.

**Constraints REALS a BD (7):** PK · `UNIQUE (model_id, pom_id, capa, instancia)` ·
CHECK `instancia_exigeix_nom` · CHECK `ordre >= 0` (**no és a la Meta**: el genera
`PositiveIntegerField`) · 3 FK.
**Fills: només `MeasurementChangeLog.base_measurement`, amb `SET_NULL`.**

**FK `element` nullable — § 1.6. El trencament és UN constraint i és silenciós.**
El CHECK `instancia_exigeix_nom` **no** es trenca (és per fila), però **la seva raó queda
incompleta**: dues files «pit» que només difereixin per `element_id` són igual d'indistingibles
per a un humà, i el CHECK no vigila aquest eix.

**El cost real no és a les constraints.** És a:
- **`pom/identitat.py:38`** — `clau_mesura` → `{pom}|{capa}|{inst}`, que **prohibeix ometre trams**;
- el seu **mirall escrit a mà** a `TechSheetEditor.jsx:321-322`;
- **~20 lectors** indexats per la terna i **9 escriptors**.

**Serializer:** `serializers.py:425`, `validate` a `:465-492`. Fa preflight de la clau amb
`filter().exists()` (**no hi ha `UniqueTogetherValidator` de DRF**) + espill del CHECK.
Per a la quaterna: **el patró `... or ''` no serveix per a un FK nullable**, i si l'índex queda
nulls-distinct **aquest `validate()` passa a ser l'ÚNIC guard** — fora de transacció (cursa) i
invisible als 9 escriptors.

**`instancia` sense `blank=True`: CONFIRMAT** (`models.py:749-753`; només es va pedaçar el
serializer, `:442`). **El desajust és un sol camp repetit a 12 taules** — sempre `instancia`,
mai cap altre. De les 4 exposades per `ModelSerializer`, **3 encara tenen `allow_blank=False`**:
`POMAlertSerializer`, **`GarmentTypePOMMapSerializer`** i **`GarmentGroupPOMMapSerializer`**
→ el mateix 400 que Q1 va arreglar **segueix viu**, i dos dels tres són els serializers de
l'acumulació creats ahir. Asimetria menor a `capa`: el codi normalitza `'' → 'exterior'` però
l'API el rebutja amb 400.

**Recompte:** `public` **la taula no existeix** (`models_app` és tenant-only) · `fhort` **0** ·
`los` **0** · **dump pre-wipe ≈693**.

### B3 · `ModelGradingRule` — el canvi de clau [P3]

**Consultat:** `models_app/models.py:994-1100`, `_meta` viu, grep ample, `related_objects`,
`services.py`, `tests_sembra_grading.py`, i el dump.

**Definició i clau:** la `Meta` són **tres línies**: `verbose_name`, `verbose_name_plural` i
**`unique_together = [('model','pom')]`**. Confirmat contra `_meta` viu: `constraints: []`,
`indexes: []`, **cap `ordering`** (la germana `ModelGradingOverride` sí que en té).
FK: `model`→CASCADE (constraint real) · `pom`→PROTECT `db_constraint=False` ·
`derivat_de_rule_set`→SET_NULL `db_constraint=False`.

**`related_objects` = buit. `ModelGradingRule` no té cap fill: el canvi de clau no arrossega cap
taula avall.**

**Cens.** El 6+2 del brief **és exacte**: `views.py:943`, `:1016`, `:1161`, `:1716`,
`extraction_views.py:2748`, `migra_brownie_ruleset.py:194`; deletes crus a `views.py:1118` i
`extraction_views.py:2712`. **Però n'hi ha més que un grep pel nom no veu:**

- 🚨 **`consolidate_pom_catalog.py:117` fa `update(pom=dest)` — un UPDATE CRU D'UNA COLUMNA DE LA
  CLAU**, i la seva detecció de col·lisions és literalment `except IntegrityError: coll += 1`.
  **Canviar la constraint canvia què compta com a col·lisió sense tocar aquest fitxer.**
- **`consolidate_pom_catalog.py:257` és un TERCER delete cru**, invisible perquè la relació és
  una cadena dins `FUSIO_MOVE_RELS` (`seed_data/consolidate_pom_los.py:31`).
- **`clone_model_for_qa.py:102`: `r.pk = None; r.model = clone; r.save()`** — copia tots els
  altres camps sense mirar-los. **És el germà exacte del «CLONAR amb 500» de C4.**
- 5 escriptures més a `scripts_tmp/` contra dades vives.

**El punt de col·lapse és un de sol:** `_load_grading_rules` (`pom/services.py:749`) retorna
**`{pom_id: rule}`**, i penja de **8 consumidors** (motor, preview, escalat, `ajustar-talla`,
fitting ×3, Size Check). El comentari de `services.py:234-238` documenta que **les dues fallades
possibles són a un caràcter de distància**: amb `pom_id` una regla desapareix **en silenci**;
amb la tupla el motor queda **mut i no emet cap cel·la**. **Cap de les dues peta.**

**Els dos escriptors de pantalla** (`gravar_pom` `views.py:2364` i `set_pom_regim_view`
`views.py:4803`) fan `filter(model, pom_id).first()` sobre una taula **sense `ordering`** →
**editarien l'element arbitrari**. La URL és de dos segments (`urls.py:240`) i el front la crida
des de 3 helpers.

**Senyals: cap** (els 8 receivers de `signals.py` surten tots pel `sender`).
**Serializers: cap** — les regles s'exposen a mà com a dicts.

**`poms_manual_a_preservar`** (`services.py:273-303`) retorna un `set` de **`pom_id` pelats**:
amb la clau nova, preservar un POM en un element el preservaria a **tots**, i el filtre de
`services.py:347` faria caure regles legítimes d'altres elements **sense `IntegrityError`** —
silenci, no error.

**Tests: § 1.7.**

**Recompte:** `public` **no té la taula** (app tenant-only) · `fhort` 0 (0 models, wipe) ·
`los` **0 amb 51 models vius**. I `los` també té `pom_gradingrule = 0` →
🚨 **cap dels 51 models de `los` pot graduar per cap branca.**

**Dump pre-wipe:** **4.783 files · 45 models · 152 POMs · 0 duplicats · 24 MANUAL / 35 CANONICAL
/ 4.724 CLIENT_RUN**. El `COPY` **no porta `derivat_de_rule_set_id`** → `0079` no estava aplicada
el 06/08 (i **avui sí** que ho està: verificat).

### B4 · Plantilla d'elements a l'item [P6+P7]

**Consultat:** `pom/models.py:938,957` (`GarmentTypePOMMap`, `GarmentGroupPOMMap`), `_POMMapBase`,
`pom/acumulacio.py` sencer, `cataleg_views.py`, `tasks/models.py:428,483-544`, `endpoints.js`.

**El bloquejant primer és § 1.1: les taules no existeixen.**

**L'acumulació són TRES taules, no dues.** (`acumulacio.py:3-6`.) Les **noves** són dues; la
vella **`GarmentPOMMap` és el nivell ITEM**. La part «UNIÓ A LA LECTURA» del disseny d'ahir sí
que queda **confirmada literalment**.

Dos detalls del mecanisme que no són a cap docstring:
- **La precedència és POSICIONAL, no de dades**: l'ordre de `trams.append(...)` és la llei.
- **La substitució és TOTAL, sense merge d'atributs**: si el grup diu `obligatori=True` i l'item
  `False`, guanya `False` i **l'obligatorietat del grup desapareix**.

**Consumidors:** 5 punts de backend, tots dins `cataleg_views.py` + `urls.py`. Al frontend,
**`endpoints.js:522` està declarat i CAP component el crida** → confirma que **la pantalla d'U2
no està feta**.

**`ItemBaseSet`:** a `fhort` **1 fila** (amb 62 items i 1.748 `GarmentPOMMap`). És satèl·lit de
catàleg — cap wipe de models el tocaria → **la via V2 pràcticament no s'ha exercitat**.

**`_POMMapBase` no declara cap FK**, ni tan sols `pom`: cada filla declara la seva àncora i el
seu `pom`. **Cap de les dues germanes declara `constraints`, només `unique_together`** (i per
tant hereten el problema de § 1.6 si mai els cau un camp nullable a la clau).

**🔑 Ja existeix un mecanisme d'«item que sembra 2+ peces», i està a zero:**
`GarmentTypeItem.is_set` + `tasks.GarmentTypeItemPart` (`tasks/models.py:428`, `:483-544`,
sprint SET-1 del 27/07), amb `ordre` i `nom_peca`. **Però és una semàntica DIFERENT de la del
brief:** allà la peça **ÉS un altre `GarmentTypeItem`** amb catàleg propi (i per tant **no cal cap
mapa POM→element**), mentre que un «element sembrat dins del model» **no té catàleg propi**.
Quina de les dues vol el Patró C és una **decisió**, no una lectura.

**🚩 El bloquejant real de P7 no és a la BD: és a `acumulacio.py` i a la sembra.**
- **`_clau()` (`acumulacio.py:28-30`) és `(pom_id, capa, instancia)`**: dos elements que reclamin
  el mateix POM **col·lapsen en silenci**, sense error i **amb el recompte mentint**.
- **`materialize_poms_view` (`models_app/views.py:1412-1456`) escriu `BaseMeasurement` amb clau
  `(model, pom, capa, instancia)`** — **no hi ha cap eix d'element al costat del model**, o sigui
  que **l'element no sobreviu la sembra**.

**Proposta (només text; no s'ha creat res):** dues peces, no una —
`GarmentTypeItemElement` (catàleg d'elements, a `pom`, amb `db_constraint=False` cap a `tasks`)
+ `GarmentElementPOMMap(_POMMapBase)` amb `element` CASCADE i `pom` **PROTECT**. El PROTECT no és
cosmètic: fa que `_cens_relacions` (`cataleg_views.py:37`, que recorre `related_objects`) la
vegi **sola** com a bloquejant d'esborrat — **la lliçó TGIRL s'hereta gratis**.
Documentat a l'informe **per què no pot anar**: ni a `GarmentPOMMap` (columna nullable →
l'`unique_together` deixa de protegir, exactament el que U2 va rebutjar el 07/08), ni a
`ItemBaseSet` (el seu eix és el MÓN, i la llei diu «l'item MAI es parteix»), ni reaprofitant
`instancia` (que significa «el mateix POM dues vegades a la mateixa capa» — **eix ortogonal**;
col·lapsar-los trencaria `_clau()` de manera invisible).

**Comprovació que B4 va deixar oberta i que s'ha tancat aquí:** famílies amb `grup_ref` NULL,
que saltarien el nivell grup en silenci (`acumulacio.py:67`) →
**`public` 0 tipus · `fhort` 21, cap NULL · `los` 1, cap NULL.** **El camí existeix però NO està
armat amb les dades d'avui.** C6 pas 2 segueix obert, però no bloqueja la sembra.

### B5 · `POMPlacement` i la traçadora [P4]

**Consultat:** `models_app/models.py:1424-1521`, `pom_placement_views.py`, `TechSheetEditor.jsx`,
`docs/diagnosis/arxiu/POC_PAPER_KONVA.md`, recomptes + dump.

**UNA SOLA definició.** La «PoC» del repo és de l'editor Konva i **el fitxer que cita ja no
existeix**; no hi ha segona definició enlloc.

**p1/p2:** són **4 escalars plans `NOT NULL` sense default** → **la cardinalitat 2 està cuita a
l'esquema**.

**Absència de sentit: TRIPLE.** Cap camp de direcció · el render posa **punta als dos extrems**
(`:397`) · **`cotaLabelOffset` (`:377-384`) plega el signe A POSTA** → A→B i B→A donen el mateix
resultat. **La BD conserva un ordre que ningú no llegeix** → no està normalitzat.

**`view_slot` és denormalitzat:** `SlugField` a la fila (dins la clau única), `slugify()` a
l'escriptura, query-param obligatori a la lectura — però **l'autoritat és l'objecte sketch del
`.ftt`** (`o.viewSlot`), **input de text lliure** a `:7510`.

**Els dos canvis:** **separables a la BD** (cap constraint els relaciona) però **acoblats a
l'endpoint** — els dos reescriuen les mateixes ~50 línies de `pom_placement_views.py` i els
mateixos 3 blocs de `TechSheetEditor.jsx` → **dues onades = dues rondes de contracte HTTP**.

Dos descobriments que reenmarquen la pregunta:
1. **La clau de 5 columnes JA AVUI es col·lapsa a `pom_id` a la vora del payload, a posta**
   (`:5640-5644`: «una col·locació de catàleg no sap res de capes») → **afegir element hi reobre
   una decisió de PRODUCTE, no una columna.**
2. **La cota viva del `.ftt` JA és una polilínia** (`buildLiveCota` fa un `path` amb `segments[]`
   Bézier; `cotaHandleEnds:433` diu literalment «`cotaEndsMm` assumeix recte, **per al
   precedent**») → **(b) no és ensenyar polilínies al sistema: és deixar de perdre-les en desar.**

**🚨 `POMPlacement` penja del CATÀLEG, no del Model.** Una FK a un element-de-model **xoca amb
D1**, i `DIAGNOSI_FEDERACIO_INTERACTIVITAT.md:754` **ja marca aquest punt com a OBERT**.

**Recompte:** `public` n/a · `fhort` **2** (ids 1 i 3 — **falta el 2**) · `los` 0 ·
dump pre-wipe **≈4**, amb **3 `ItemFitxer`** (avui 1).
→ **El wipe se'n va endur 2 per la via `ItemFitxer` CASCADE, no pel Model** — confirmació
empírica del precedent «un CASCADE no bloqueja: s'enduu files».

---

## 4 · BLOC C — FRONTERA I VOLUM

### C1 · El dump com a línia base

**Restaurable: SÍ**, amb dues advertències operatives:

1. **`pg_restore` del PATH FALLA.** `/usr/bin/pg_restore` és **PG 16.14** i el dump el va escriure
   **pg_dump 18.4** → `unsupported version (1.16) in file header`.
   **Cal `/usr/lib/postgresql/18/bin/pg_restore`.** (Tres investigadors hi van topar per separat.)
2. 🚨 **El dump conté NOMÉS l'schema `fhort`** — 124 taules, 124 TABLE DATA, **cap entrada de
   `public` ni de `los`**. Com a línia base de «GradedSpec idèntic» **serveix**; per a qualsevol
   cosa de **`public`** (el catàleg compartit de talles) **NO serveix**.

**Restaurat a `ftt_tmp_diag_v4`** (127.0.0.1:5433, owner `ftt_staging`, **26 MB**, **DEIXADA
CREADA** per reaprofitar). 1 sol error ignorat: el FK cap a `public.tenants_client`, absent del
dump. Credencials de `backend/.env`, injectades via `PGPASSWORD` — mai en clar.

| taula | dump | viu (`fhort`) |
|---|---|---|
| models | 46 | **0** |
| BaseMeasurement | 691 | 0 |
| MeasurementChangeLog | 228 | 0 |
| **GradedSpec** | **1787** | 0 |
| SizeFitting | 48 | 0 |
| POMMaster / àlies / GarmentPOMMap | 396 / 390 / 1748 | **396 / 390 / 1748** (intacte) |

L'única diferència de catàleg és l'esborrat **net i coherent** del ruleset de prova 124 amb les
seves 21 regles + 2 sistemes de talla + 10 talles.

**🔑 Empremta de línia base de `GradedSpec`, ancorada a `codi_intern`+`codi_client` (no a ids,
que es regeneraran):**

> **1787 files · md5 `e7de6f09b5bc04e7974e3afcf8e5a6e6`**

La consulta literal que la reprodueix és a `_C_dump_inconsistencies.md`.

**POM `S` i `S2`: § 1.2** — n'hi ha **dos de cada**.

### C2 · Inconsistències — només reportades, cap reparada

**Les 4 sospites de sessions anteriors, verificades:**

| sospita | veredicte |
|---|---|
| `public.TODDLER_EU` corrupte | **CONFIRMAT, i pitjor**: waist/hip 20-25 cm avall vs `fhort`, i **es contradiu DINS del mateix `public`** — a 116 cm, `KIDS_EU 6Y` diu 54/64 i `TODDLER_EU 116` diu 34/40. A més `public` té 5 talles i `fhort` 6 (falta la 86, **tot l'`ordre` desplaçat**) |
| 93 POMs orfes | **Ara 106** (93 actius + 13 desactivats). I **230 sense `GarmentPOMMap`**, 58 doblement orfes |
| 9 POMs amb `nom_fitxa` buit | **Era una mesura de PROD i el número real és molt pitjor**: al dump, **558 de 691 BaseMeasurement (81 %)** amb `nom_fitxa` buit, i **39 POMs reclamats per més d'un nom alhora**. A `pom_itembasemeasurement` viu: **37/37 buits** |
| duplicats de `SizeFitting` a 182/185 | **NO existeixen** (1 SF cadascun al dump). **El duplicat real era `SizeCheck`** i hi era intacte: model 182 amb 4 checks i el `Pendent` **congelat a `valor_teoric=41.7`** mentre la base vigent al mateix dump és **42.6** |

**Troballes noves:**

- 🚨 **125 `GradingRule` de 4 rulesets tenen `talla_base_label='128'`, etiqueta que NO existeix al
  sistema de talles del seu propi ruleset** (el `talla_base_id` penja de `TGIRL-EU-HEIGHT`).
  **Això quantifica la nota «TGIRL: àncora de N regles».**
- 🚨 **`los`: 51 models i 51 SizeFitting, però 0 POMMaster, 0 BaseMeasurement, 0 GradedSpec,
  0 GradingRule**, i 2 sistemes de talla amb **0 talles**.
- **`public`: 14 rulesets amb 0 regles** (13 amb `size_system_id` NULL) i **4 sistemes de talla
  actius sense cap talla**.
- **12 `codi_client` duplicats a `fhort.pom_pommaster`** (24 files, sense constraint), dos amb
  col·lisió semàntica real (`BJ`, `H`). *(A1 n'assenyalava `D` i `H`; el tall exacte difereix
  segons si es compta la parella sencera — el CSV és l'autoritat.)*
- **Un `codi_client` és literalment `0`** (fila `pk=506`, «Back opening length»).
- **`pendent_revisio` massiu: 254/396 (64 %).**
- **Cap dada òrfena del wipe:** els 12 FK lògics `db_constraint=False` donen **tots 0**.
  (Un fals positiu inicial — 20 òrfenes a `pom_clientmesuraperfil` — era artefacte de NULLs: les
  20 files tenen `client_id IS NULL`.)

---

## 5 · QUÈ NO S'HA POGUT DETERMINAR EN LECTURA

| # | pregunta oberta | camí per tancar-la |
|---|---|---|
| 1 | **Si els 21 POMs no confirmats del v4 són nous o duplicats** | Cal `CATALEG_CANONIC_BROWNIE_V4.md` (no és a la màquina). L'insum és `A1_pommaster_fhort.csv` |
| 2 | **Si el 0 de `GarmentTypeItemPart` a `fhort` és «mai usat» o «esborrat»** | No hi ha `created_at`. El de `los` sí que és net per construcció |
| 3 | **Si `instancia` serveix per a ELEMENTS** | Els docstrings la descriuen com repeticions **dins** d'una peça (sisa dreta/esquerra), no **entre** peces. És pregunta de **disseny**, no de lectura |
| 4 | **Recomptes a PROD** | Sense SSH. El camí és el backup diari (§ `ftt-prod-estat-via-dump`), i **la posició de la columna `instancia` al `COPY` s'ha de re-verificar a cada dump** |
| 5 | **Si el SLUG ha d'anar concatenat** | No s'ha trobat **cap** font que ho digui; els tests afirmen el contrari (`AHL ≠ AH-L`). D-31.26 parla del **CODI**. Cal decisió del Patró C |
| 6 | **Tot l'impacte d'`element` al bloc B** | `element` no existeix al codi: és projecció, no mesura |
| 7 | **El front de B3** | Escanejat per grep (9 fitxers), cap llegit sencer |

---

## 6 · ANNEXOS — fitxers generats (working dir, NO al vault)

| fitxer | contingut |
|---|---|
| `A1_pommaster_fhort.csv` | **396 files**, 33 columnes, amb recomptes de relacions entrants i marca `ORFE_sense_alias` |
| `A1_pommaster_public.csv` | només capçalera (0 files) |
| `A1_pommaster_los.csv` | només capçalera (0 files) |
| `_A_cataleg_bd.md` | A1 · A2 · A4 — definicions enganxades senceres |
| `_A_cens_lectors.md` | A3 · A5 — els ~110 lectors i els 11 escriptors, amb fitxer:línia |
| `_B1_multipeca.md` | B1 — les dues branques, contrast amb DALIA, cens, noms |
| `_B2_B5_superficies.md` | B2 · B5 — definicions literals i anàlisi constraint a constraint |
| `_B3_modelgradingrule.md` | B3 — cens complet, els 8 consumidors, els 106 tests |
| `_B4_plantilla_elements.md` | B4 — `acumulacio.py` sencer explicat + la proposta de taula germana |
| `_C_dump_inconsistencies.md` | C1 · C2 — empremta md5, consulta literal, inconsistències |

**BD temporal deixada creada:** `ftt_tmp_diag_v4` (127.0.0.1:5433, 26 MB) — restauració del dump
del 06/08, només schema `fhort`. Reaprofitable per una sessió futura.
