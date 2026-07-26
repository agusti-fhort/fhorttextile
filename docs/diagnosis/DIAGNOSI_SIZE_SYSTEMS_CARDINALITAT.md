# DIAGNOSI — CARDINALITAT DELS SIZE SYSTEMS (una escala, molts targets × fits × construccions)

> **Data:** 2026-07-26 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Pregunta de producte (Agus):** un size system ha de poder servir MÚLTIPLES `target × fit_type ×
> construction` — l'escala física és la mateixa. Avui el vincle es percep rígid. Cartografiar ON viu
> el vincle, ON és la rigidesa concreta, QUÈ toca el motor de grading (frontera G6) i QUANTS duplicats
> hi ha de facto. Cap codi tocat.
>
> **Convenció:** tota afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi.**
> Cens de dades = query live read-only contra la BD de staging (backups PROD restaurats).

---

## TL;DR (per al CTO)

1. **L'ESQUEMA JA ÉS FLEXIBLE.** `SizeSystem.targets` és un **M2M** des de la migració `0021` i el
   `SizeSystem` no porta ni `fit_type` ni `construction` — és **escala pura** (LLEI 5 CAPES, capa 3).
   **Cap model apunta al `SizeSystem` en 1-a-1**: `SizeDefinition`, `GradingRuleSet`, `Model` i
   `SizingProfile` hi apunten tots **N→1**. La cardinalitat que l'Agus demana ja hi és a nivell de BD.

2. **LA RIGIDESA ÉS DE DADES + UX, NO D'ESQUEMA.** Tres colls d'ampolla, tots FORA del motor:
   - (a) La migració `0021` va copiar l'**únic** target del FK antic a la M2M → cada sistema neix amb
     **1 sol target** i ningú no n'hi ha afegit cap més.
   - (b) La creació (Size Map Setup) **cus el target dins el `codi` i el `nom`** del sistema i n'hi
     afegeix **només un** (`size_map_views.py:788-796`). D'aquí "LOS Teen Girl 8-16Y".
   - (c) **No existeix cap camí d'escriptura del M2M `targets`**: `SizeSystemSerializer` l'exposa
     **read-only** (`serializers.py:108-115`) i **cap UI l'edita**. Un cop nascut mono-target, no es
     pot ampliar per producte.

3. **CONSEQÜÈNCIA MESURADA:** la mateixa escala es clona per target. `YOUTH_GIRL_LOS_01` (id 65) i
   `YOUTH_BOY_LOS_01` (id 66) són **la mateixa escala `8/10/12/14/16`** separada NOMÉS pel target;
   igual amb Kids `2..12Y` (ids 48/64/50). `fhort` té **28 sistemes** però el pes real recau en 8; ~10
   són buits o orfes.

4. **FRONTERA G6:** el motor (`generate_graded_specs`) llegeix **`model.size_system` (com a escala
   ordenada) + les regles**. **No llegeix mai `SizeSystem.targets` ni `SizingProfile`.** Per tant, tota
   la flexibilització de targets es pot fer **sense entrar al motor**.

5. **FIX MÍNIM (dins frontera G6):** obrir el M2M `targets` a escriptura (serializer + una UI d'edició)
   i deixar de coure el target dins codi/nom en crear. Res del motor. La consolidació de duplicats és
   una segona fase, separada i opt-in. Detall a §5.

---

## Q1 — ON VIU EL VINCLE (cardinalitats reals)

### El `SizeSystem` és escala pura, ja multi-target

`pom/models.py:293-339`:
- `codi` (unique), `nom`, `base_unit`, `norma_ref`, `parent` (derivació self-FK), `customer_codi` (3 ch).
- **`targets = ManyToManyField('Target')`** (`:302-305`) — **M2M**, migrat des del FK únic a `0021`.
- **NO té `fit_type`, NO té `construction`, NO té `garment_type`.** Un sistema NO sap res de fit ni
  construcció: és una escala ordenada de `SizeDefinition` (`:342-373`, `talles`, CASCADE).
- Confirmat per la LLEI 5 CAPES al codi: *"el pas «Talles» del wizard llista SizeSystems PURS (escala,
  capa 3)"* (`pom/views.py:70`); *"Escala pura: SENSE fit, SENSE construcció, SENSE graduació"*
  (`frontend/src/pages/ModelWizard.jsx:195`).

### Qui apunta cap al `SizeSystem` — TOTS N→1 (cap 1-a-1)

Sweep exhaustiu (`grep ForeignKey/M2M → SizeSystem`):

| Origen | Camp | Cardinalitat | on_delete | fitxer:línia |
|---|---|---|---|---|
| `pom.SizeDefinition` | `size_system` | N→1 | CASCADE | `pom/models.py:343` |
| `pom.SizingProfile` | `size_system` | N→1 | PROTECT | `pom/models.py:1160` |
| `pom.GradingRuleSet` | `size_system` | N→1 (nullable) | PROTECT | `pom/models.py:768` |
| `models_app.Model` | `size_system` | N→1 (nullable) | SET_NULL | `models_app/models.py:207` |
| `tasks.GarmentTypeItem` | `base_size_definition` → `SizeDefinition` → system | indirecte | SET_NULL | `tasks/models.py:316` |

**Cap relació és 1-a-1.** Un `SizeSystem` ja és, per construcció, compartible per molts models, rulesets
i perfils. La cardinalitat "un sistema, molts consumidors" existeix; el que NO s'exercita és "un sistema,
molts **targets**".

### El join real target×fit×construction: `SizingProfile`

`pom/models.py:1146-1197` — `SizingProfile` és la 5-tupla d'ÀMBIT:
`(target, garment_type, construction, fit_type, size_system)` + `customer` + `grading_rule_set` (nullable).
És **1 fila per combinació**, i totes apunten N→1 al mateix `size_system`. **Aquest és el mecanisme de
flexibilitat que ja existeix**: una escala serveix N combinacions posant N files de `SizingProfile`.
El seu `__str__` és `"target | garment_type | construction | fit_type"` (`:1196`).

### D'on surt cada peça de la capçalera de la fitxa (VEGA)

VEGA mostra `SIZE SYSTEM: LOS Teen Girl 8-16Y` + `Teen Girl | Regular | Knit`. **Dues fonts FK
INDEPENDENTS** (traçat complet):

- **`LOS Teen Girl 8-16Y`** = `Model.size_system.nom`, via `size_system_nom`
  (`models_app/serializers.py:186`, `source='size_system.nom'`). El **FK directe `Model.size_system`**
  (`models_app/models.py:207`). Render a `TechSheetEditor.jsx:1002-1003`. → El **target ("Teen Girl") i
  el rang ("8-16Y") estan cuits dins el `nom` del sistema.**
- **`Teen Girl | Regular | Knit`** = del **`Model.grading_rule_set`**, NO dels camps propis del model ni
  del `SizeSystem.targets` ni del `SizingProfile`:
  - `grading_target_nom` = `' / '.join(grs.targets.nom_en)` (`serializers.py:196-203`) — M2M del **ruleset**.
  - `grading_fit_nom` = `grs.fit_type.nom_en` (`:205-207`).
  - `grading_construction_nom` = `grs.construction.nom_en` (`:209-211`).
  - Render a `TechSheetEditor.jsx:1000-1001`.

> **🚩 BANDERA G1 (incoherència latent de capçalera).** El label de sistema surt de `Model.size_system`
> i el triplet de `Model.grading_rule_set` — **dos camins FK que ningú no garanteix coherents al render**.
> La superfície germana `ModelSheet.jsx:949-977` encara pinta el triplet des dels **CharFields propis**
> `model.target/fit_type/construction` (`:953-957`) → **dues superfícies, dues veritats**. No és el focus
> d'aquesta diagnosi (toca capçalera, no cardinalitat) però queda anotat.

---

## Q2 — ON ÉS LA RIGIDESA CONCRETA (i reproducció)

La rigidesa NO és a l'esquema (§Q1). Són **tres punts**, tots reproduïbles:

### (a) Naixement mono-target amb el target cosit a la identitat

Únic camí de creació d'una escala = **Size Map Setup** (`SizeMapSetup.jsx` → `sizeMap.create`
(`api/endpoints.js:227`) → `pom/size_map_views.py:size_map_create_view:618`). Al backend:

- **`CREAR`** (`size_map_views.py:786-796`): `codi = f"{target_codi}_{customer_codi}"` (`:788`),
  `nom = f"{target_nom} {base_unit} — {cust} Run NN"` (`:790`), i **`if target: ss.targets.add(target)`**
  (`:795-796`) — **un sol target, i cuit dins codi+nom.**
- **`CLONAR`** (`:766-785`): crea una fila NOVA, **copia físicament totes les `SizeDefinition` del pare**
  (`:780-785`) i n'hi posa 1 target (`:775-778`).
- El M2M multi-target real s'aplica al **`GradingRuleSet`**, no al sistema: `rule_set.targets.add(_t)`
  (`:883-886`); i es crea **un `SizingProfile` per target** (`:978-1010`).
- Al frontend Step 1 el target és un **`<select>` únic** (`SizeMapSetup.jsx:524-527`).

### (b) El M2M `targets` del sistema és READ-ONLY end-to-end

- `SizeSystemSerializer.target_codis` = `SerializerMethodField` **read-only** (`serializers.py:108-115`).
  Els `fields` NO inclouen cap camp escrivible de `targets` (`:112`).
- **Cap UI edita `SizeSystem.targets`.** `SizeSystemDrawer.jsx` només fa CRUD de `SizeDefinition` i
  esborrar el sistema; `SizeLibrary.jsx` opera sobre `SizingProfile`s, no sobre sistemes.
- Existeix escriptura del M2M NOMÉS dins `size_map_views.py` (`:775-778`, `:795-796`), i sempre **afegint
  1 target** al moment de crear. No hi ha "afegir target B a un sistema existent".

### (c) El wizard filtra l'escala per target → l'escala mono-target no apareix per a un altre target

- `ModelWizard.jsx:201-208`: `sizeSystems.list({actiu})` + filtre client-side
  `s.target_codis.length===0 || s.target_codis.includes(target)` (`:206`). Idèntic al selector reutilitzable
  `SizeSystemSelector.jsx:24-26`. El backend també ho suporta: `filterset_fields = ['actiu','targets']`
  (`pom/views.py:72`) → `GET size-systems/?targets=<id>`.
- **`target_codis == []` = universal** (apareix per a qualsevol target). Però com que el naixement (a)
  sempre posa 1 target, **cap escala real és universal**.

### Reproducció del cas (target/fit/construcció diferent)

> Vull reutilitzar l'escala `8/10/12/14/16` (avui `YOUTH_GIRL_LOS_01`, target TEEN_GIRL) per a un model
> **TEEN_BOY**:
> 1. Al **ModelWizard**, pas Talles: la llista es filtra per `target=TEEN_BOY` (`ModelWizard.jsx:206`).
>    `YOUTH_GIRL_LOS_01` porta `target_codis=['TEEN_GIRL']` → **NO apareix**. El wizard NO té botó de crear
>    (`:632` mostra `no_sizes`).
> 2. **No hi ha cap UI** per afegir `TEEN_BOY` al M2M del sistema existent (b). Callejó sense sortida al
>    wizard.
> 3. L'únic camí és **tornar a Size Map Setup** i, com que el match parcial recomana `CLONAR`/`CREAR`
>    (`size_map_match_view`, `size_map_views.py:160-197`), **es crea una 2a fila amb les mateixes
>    etiquetes/valors** → això és exactament `YOUTH_BOY_LOS_01` (id 66), duplicat de id 65.

**Matís important (què NO bloqueja):** el pas de grading del wizard NO obliga a crear `SizingProfile`.
Si l'escala hi és, un fit sense ruleset queda **atenuat amb tooltip** (`fit_sense_graduacio`,
`ModelWizard.jsx:746-755`) i es pot marcar **"Sense graduació"** (`:720-724`) i desar igual. La rigidesa
NO és "el flux obliga a graduar"; és **"no puc REUTILITZAR l'escala per a un altre target"**.

---

## Q3 — FRONTERA G6 (què toca el motor vs. què és taxonomia)

Traçat de `generate_graded_specs` (`pom/services.py:166-230+`) i de la classificació
(`pom/grading_utils.py`):

### El que el MOTOR llegeix (ZONA G6 — INTOCABLE)

- **`model.size_system`** com a **escala ordenada**: `escala_del_model` → `run_sistema_de` recorre
  `SizeSystem.talles.order_by('ordre')` (`grading_utils.py:326-344`). El motor consumeix la **geometria**
  (ordre + distància) del sistema, no el seu ventall de targets.
- **`model.grading_rule_set.regles`** (o `ModelGradingRule` residents) + `ModelGradingOverride` +
  `BaseMeasurement` (`services.py:186-224`).
- **Coherència d'escala** `base_size_definition.size_system == grading_rule_set.size_system`
  (`tasks/models.py:341-353` `clean()`; guard `GRADING_SIZE_SYSTEM_MISMATCH` a `models_app/views.py:595`).

**El motor NO llegeix `SizeSystem.targets`. El motor NO llegeix `SizingProfile`.** Confirmat: no hi ha cap
referència a `targets` ni a `SizingProfile` dins `services.py:generate_graded_specs` ni dins
`run_sistema_de`.

### El que és TAXONOMIA DE CATÀLEG (fora de G6 — flexibilitzable)

- **`SizeSystem.targets`** (M2M) — pur ventall d'aplicabilitat/filtre del picker.
- **`SizingProfile`** sencer — declaració d'ÀMBIT (disponibilitat), consumit pel filtre de compat del
  wizard i com a **suggeriment** de grading (`ModelWizard.jsx:301-312`, *"SUGGERIR ≠ ARROSSEGAR"* `:300`).
  El `grading_rule_set` del perfil és **nullable** des de C3 (`pom/models.py:1162-1173`).
- **Els eixos `targets`/`construction`/`fit_type` del `GradingRuleSet`** — s'usen per a **MATCHING /
  classificació** (`cerca_canonic_equivalent`, `grading_utils.py:120-150`, eixos = size_system + target +
  construction + fit), no per a la matemàtica de grading. La reutilització de ruleset de client es
  dispara per **`customer + size_system`** només (`cerca_client_equivalent:153-172`).

### LA LÍNIA

> **Es pot flexibilitzar el ventall de `targets` d'un `SizeSystem` (afegir-ne, editar-los, no coure'ls a
> la identitat) SENSE tocar `generate_graded_specs` ni cap regla.** El motor només veu el sistema com a
> escala i les regles; el target és metadada de catàleg que ell ignora. La coherència que SÍ importa és
> `base_size_definition.size_system == grading_rule_set.size_system` (identitat d'**escala**, no de target),
> i cap fix de targets la toca.

---

## Q4 — IMPACTE DE DADES (cens live, staging = backups PROD)

**Mètode:** `manage.py shell` + `schema_context`, SELECT-only. Schemes reals: `fhort`, `los`.

- **`fhort`: 28 `SizeSystem`** · **`los`: 2** (buides, sense cap `SizeDefinition`, però amb 30 Models
  penjant-ne → 🚩 flag d'integritat, veure sota).

### Els 8 que aguanten el pes (fhort, tots mono-target)

| id | codi | base_unit | target | talles | Models |
|---|---|---|---|---|---|
| 63 | BABY_LOS_01 | MONTHS | BABY_BOY/GIRL | 6 | **166** |
| 48 | GIRL_LOS_01 | AGE_YEARS | KID_GIRL | 9 | **140** |
| 67 | WOMAN_LOS_01 | ALPHA | WOMAN | 7 | **138** |
| 51 | MAN_LOS_01 | ALPHA | MAN | 9 | **121** |
| 65 | YOUTH_GIRL_LOS_01 | AGE_YEARS | TEEN_GIRL | 5 | **113** |
| 64 | BOY_LOS_01 | AGE_YEARS | KID_BOY | 9 | **104** |
| 66 | YOUTH_BOY_LOS_01 | AGE_YEARS | TEEN_BOY | 5 | **92** |
| 62 | NEWBORN_LOS_01 | MONTHS | NEWBORN_* | 7 | **45** |

### DUPLICATS DE FACTO (mateixa escala, difereixen NOMÉS pel target)

- **Escala Teen `8/10/12/14/16`** → **id 65 (TEEN_GIRL) + id 66 (TEEN_BOY)** = idèntica, 205 Models
  repartits. **Candidat net de consolidació** a 1 sistema amb `targets={TEEN_GIRL, TEEN_BOY}`.
- **Escala Kids `2..9/10..11/12`** → **id 48 (KID_GIRL) + id 64 (KID_BOY) + id 50 (GIRL_LOS_03, orfe,
  0 Models)**. 48+64 difereixen només pel target; 50 és redundant pur.
- (id 63 `BABY_LOS_01` ja porta BABY_BOY **i** GIRL al M2M → **precedent que la consolidació funciona**;
  algú ja hi va posar 2 targets a mà o via seed.)

### Soroll (candidats a neteja, no a consolidació)

- **Buits totals** (0 talles / 0 fan-in) a `fhort`: ids 26, 31, 33, 39, 40 → esborrables.
- **Orfes de Models** (0 Models): ids 32, 53, 6, 41, i inactius 34/36/37 → revisar.
- **`los`: ids 1 i 2 sense cap `SizeDefinition` però amb 20 i 10 Models** → 🚩 **flag: 30 Models penjats
  d'escales buides** (el motor petaria amb "no talles"). Fora d'aquesta diagnosi, però s'anota.

### Què implica consolidar (2 casos nets)

Fusionar id 66→65 i id 64→48 (+ eliminar 50): re-apuntar `Model.size_system`, `GradingRuleSet.size_system`
i `SizingProfile.size_system` dels ~196 Models afectats al sistema supervivent, afegir el target absent al
M2M, i renombrar el supervivent a un nom **sense target cuit** (p.ex. `YOUTH_LOS_01` "Teen 8-16Y"). **Toca
FKs de catàleg, cap regla.** Requereix el fix (c) de §Q2 (M2M escrivible) primer. És **Fase 2, opcional**.

---

## §5 — RECOMANACIÓ: FIX MÍNIM DINS LA FRONTERA Q3

**Principi:** l'esquema ja és correcte. El fix és **obrir el M2M `targets` a producte i deixar de coure el
target dins la identitat**. Zero motor, zero regles, additiu.

### Fase 1 — Desbloquejar la cardinalitat (mínim viable, sense migració de dades)

1. **`targets` escrivible al `SizeSystemSerializer`** — afegir un `PrimaryKeyRelatedField(many=True)` (o
   per codi) escrivible, mantenint `target_codis` read-only per compat (`serializers.py:108-115`). Guard:
   editar `targets` **NO** és canviar `size_system` d'un ruleset amb regles (aquell guard viu a
   `serializers.py:270-282` i **no** es toca; targets ≠ escala).
2. **UI mínima d'edició de targets** al `SizeSystemDrawer.jsx` (multi-select de Target amb i18n ca/en/es):
   un sistema passa a ser explícitament multi-target. Aquí es fa la consolidació manual "afegeix TEEN_BOY
   a l'escala Teen".
3. **Deixar de coure el target a codi/nom en `CREAR`** (`size_map_views.py:788-790`): que el `nom` no
   incorpori `target_nom` per defecte (o fer-ho opcional). El target viu al M2M, no al string.

> Amb la Fase 1, el cas de reproducció de §Q2 es resol: s'afegeix TEEN_BOY a id 65 des del Drawer i el
> wizard ja el llista per a models TEEN_BOY (`ModelWizard.jsx:206` ja respecta `target_codis`). **Cap
> escala nova, cap regla tocada.**

### Fase 2 — Consolidació de duplicats existents (opcional, command idempotent)

Management command read-then-write que fusioni els 2 parells nets (66→65, 64→48, drop 50), re-apunti els
FKs de catàleg i afegeixi el target absent. **Explícit i reversible-per-revisió, mai automàtic** (mateix
esperit que els seeds idempotents existents). Precedent: id 63 ja és multi-target.

### El que NO s'ha de fer

- **NO** afegir `fit_type`/`construction` al `SizeSystem`: trencaria "escala pura" (LLEI 5 CAPES) i
  duplicaria el paper del `SizingProfile`/`GradingRuleSet`. Fit i construcció ja viuen al seu lloc.
- **NO** tocar `generate_graded_specs`, `run_sistema_de`, ni la coherència
  `base_size_definition.size_system == grading_rule_set.size_system`.

---

## Preguntes Patró C (per a l'Agus, abans de dissenyar)

1. **Nom del sistema sense target cuit.** Si un sistema serveix TEEN_GIRL+TEEN_BOY, com l'anomenem a la
   capçalera de la fitxa? Avui el label ve de `Model.size_system.nom` (§Q1). Opcions: (a) nom neutre
   ("Teen 8-16Y") i el target ja el dóna el triplet del ruleset; (b) el label de sistema deixa de mostrar
   el target. **Decisió de producte sobre què llegeix el tècnic a la capçalera.**

2. **Universal (`targets=[]`) com a norma o com a excepció?** Un sistema sense targets aplica a tots. Per
   a escales agnòstiques (p.ex. NUMERIC_EU) ¿volem tractar `[]` com "universal" per defecte, o sempre
   exigir un ventall explícit? Avui `[]` = universal al filtre (`ModelWizard.jsx:206`) però mai s'usa.

3. **Consolidar els duplicats vius o només aturar la sagnia?** Fase 1 atura la creació de nous duplicats.
   La Fase 2 (fusionar id 65/66 i 48/64, ~196 Models re-apuntats) és cirurgia de dades sobre PROD. ¿Val la
   pena consolidar l'existent, o només evitar-ne de nous i deixar viure els actuals?

4. **La incoherència de capçalera (bandera G1)** — el label de sistema (`Model.size_system`) i el triplet
   (`Model.grading_rule_set`) són dos camins FK independents, i `ModelSheet.jsx` encara usa els CharFields
   propis. ¿Convergim les dues superfícies en una font única en aquest mateix front, o és un sprint a part?

5. **`los` amb 30 Models sobre escales buides** (ids 1/2, 0 `SizeDefinition`). ¿Bug d'integritat a atacar
   ara (bloquejaria el motor) o fora d'abast d'aquesta cardinalitat?

---

*Diagnosi vigent. Segueix la llei de `docs/diagnosis/`: quan un sprint la implementi o la superi, el
mateix sprint la segella i la mou a `arxiu/`.*
