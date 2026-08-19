# DIAGNOSI — SET-2 MULTIPEÇA (la peça dins del model)

Data **2026-08-10** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
Abast: el radi complet d'introduir una peça DINS del model (`ModelPiece`), sota el marc de disseny
decidit per l'Agus (Patró C). Deu blocs d'investigació en paral·lel; cap escriptura de codi ni de BD.

> **Convenció d'aquest document**
> · Cada afirmació sobre el codi porta `fitxer:línia`. Rutes de backend relatives a `backend/fhort/`,
>   de frontend a `frontend/src/`.
> · **"NO EXISTEIX" = confirmat absent al codi** (grep fet), mai especulat.
> · **"PENDENT DE VERIFICAR"** = no s'ha pogut determinar amb certesa.
> · `💡 PROPOSTA (a validar)` = valor afegit per al CTO, **mai** una decisió presa.
> · El marc de disseny (peça dins del model, convenció mandrosa, override nullable, selector
>   d'import, clau estesa) **no es re-litiga**: s'investiga el seu radi.

---

## RESUM EXECUTIU

**1 · La premissa de partida del brief ja no descriu el sistema: la clau de mesura NO és `('model','pom')`.**
Des de la migració `0074` la clau és **`('model','pom','capa','instancia')`** (`models_app/models.py:769`).
Ja hi ha **dos** eixos qualificadors vius, amb dades reals a staging (29 files de `BaseMeasurement` a
`fhort` repartides en 5 combinacions de capa/instància). El brief demanava afegir el 3r eix a una clau
de 2; en realitat seria el **5è camp** d'una clau de 4. Això és bona notícia: **el camí ja s'ha recorregut
dues vegades i el seu procediment és llegible**.

**2 · 🔴 LA CONVENCIÓ MANDROSA («NULL a les claus = peça 01») CONTRADIU UNA LLEI ESCRITA DE LA CASA, TRES VEGADES.**
És l'única troballa que **bloqueja una decisió** i és el punt on el CTO ha de dir alguna cosa abans de res:
- `models_app/models.py:744-745` — «`''` (cadena buida, **MAI NULL**) és la instància ÚNICA […] **NULL voldria
  dir "no se sap", i aquí sempre se sap**.»
- `pom/models.py:917-919` — «A Postgres els NULL **no comparen iguals**, o sigui que un `unique_together`
  sobre una FK nullable deixaria de protegir […] **Un constraint que existeix i no protegeix és pitjor que cap.**»
- `pom/test_u2_acumulacio.py:7-10` — el mateix argument, com a raó de fer tres taules germanes.

Els dos eixos existents (`capa`, `instancia`) són **`NOT NULL` amb default no buit** (`models.py:725-726`,
`:749-750`; confirmat a BD: `is_nullable = NO`). **`nulls_distinct` NO EXISTEIX al codi** (grep sobre tot
`backend/fhort/`: 0 resultats), i `unique_together` no l'admet. Amb peça-NULL, **dues files amb la mateixa
`(model,pom,capa,instancia)` i `peca IS NULL` entrarien totes dues**: la clau deixaria de protegir
exactament el cas que ha de protegir.

**3 · El precedent d'afegir un eix existeix, està documentat pas a pas, i va costar 7 migracions sense un sol backfill.**
`0070`→`0078` (capa i instància). Patró literal: columna amb default no-NULL (fast-default de PG11+, zero
reescriptura de taula) → clau ampliada (mateixes columnes **+1**, «estrictament més permissiva») → comporta
CHECK a BD que congela l'eix mentre els consumidors s'adapten → tests de germanes → retirada de la comporta
per onades. Cap `RunPython`, cap `RunSQL` a les 7. **Aquest és el mapa de carreteres i ja està asfaltat.**

**4 · 🔴 LA MURALLA NO ÉS LA CLAU DE MESURA: ÉS `ModelGradingRule`.**
`unique_together = [('model','pom')]` (`models_app/models.py:1097`) és **l'única clau del sistema que s'ha
declarat explícitament que NO creixerà**, amb acta de domini datada (`models.py:1005-1020`: «una regla és una
llei d'INCREMENTS, no un valor […] la sisa dreta i l'esquerra **gradúen igual**») i **dos tests que la vigilen**
(`test_capa_comporta_c1.py:127`, `test_instancia_comporta_cins.py:203`). Conseqüència directa i mesurable:
- **Dues peces del mateix model que comparteixin un POM no poden tenir regles de graduació diferents.**
- I abans d'arribar-hi, **la sembra peta**: `materialize_model_grading_rules` esborra les regles de **tot el
  model** (`models_app/services.py:344-347`) i fa `bulk_create` indexat per `pom_id` sense deduplicar
  (`:368`, `:406`) → `IntegrityError` amb dues peces que comparteixin POM.
- ⚠️ **Els dos tests-pin NO ho aturarien**: comproven literalment `column_name = 'capa'` i `= 'instancia'`.
  Una columna `peca` hi passaria sense fer-los vermells. **El guardià protegeix dos noms, no el principi.**

**5 · «Peça» ja vol dir una altra cosa, en quatre apps, i el que hi ha desplegat està INERT.**
SET-1 (`GarmentSet` + `Model.garment_set` + `Model.piece_number`) està **implementat i migrat als dos schemes**
(`0019` i `0065`, aplicades 2026-07-27), amb tests de contracte vius i **federació que ja el propaga**
(`tenants/federation_service.py:116-119`, `:200-208`). Però **avui una «peça» ÉS un `Model` sencer**:
`PieceFitting` = un Model per sessió (`fitting/models.py:396`), `GarmentTypeItemPart.nom_peca` és catàleg
(`tasks/models.py:550`), `Model.piece_number` és el número de germà. **Cens de dades: 0 `GarmentSet`,
0 models amb `garment_set`, 0 `GarmentTypeItem` amb `is_set`, 0 `GarmentTypeItemPart` — als schemes `fhort`
i `los`.** Terra verge: la maquinària existeix i no s'ha executat mai sobre dades reals.

**6 · El radi no és uniforme: hi ha tres zones netes, tres cares i dues fuites silencioses.**
- **NETES** (cap cost o trivial): Kanban/tasques és **impermeable** (cens tancat, 2 punts i cap és lògica de
  tasques) · el paquet LOSAN i `bootstrap_tenant` no toquen `Model` · billing **aguanta** (5 escriptors, cap
  llegeix res sota el Model) · el `.ftt` **preserva camps desconeguts d'objecte** per opacitat, provat amb test.
- **CARES**: el motor de grading col·lapsa en memòria (`pom/services.py:838`) i **desempaqueta una 3-tupla
  rígida** (`:233`) que petaria · l'import col·lapsa **en silenci** i té un test que ho assereix a posta ·
  el Resum §8f és replicable però li falten les dades de les germanes.
- **🔴 FUITES SILENCIOSES, les dues noves d'aquesta diagnosi**:
  (a) **`germanes_de` creuaria les peces i ESCRIU** — `models_app/services_derivacio.py:72-78` filtra per
      `(model, pom)` + «un eix diferent»; dues peces amb la mateixa capa i instància passarien **les dues**
      branques de la `Q` → **corregir el pit de la peça 1 mouria el de la peça 2** (`aplica()` escriu a `:124`,
      invocada des del check a `services_size_check.py:255-257`).
  (b) **L'estalitud contaminaria entre peces** — `fitting/staleness.py:110-115` filtra per `model_id` i llegeix
      `model.measurements_version`, un comptador **únic per Model** (`models_app/models.py:325`). Tocar una
      mesura de la peça B marcaria ESTALA la versió segellada de la peça A, i l'avís arriba fins al patronista
      (`patterns/adapters.py:493-499`).

---

## BLOC 1 — La clau d'identitat de la mesura

### L'estat real, avui
| Taula | Clau | Línia |
|---|---|---|
| `BaseMeasurement` | `('model','pom','capa','instancia')` | `models_app/models.py:769` |
| `ModelGradingOverride` | `('model','pom','size_label','capa','instancia')` | `models_app/models.py:977` |
| `SizeCheckLine` | `('size_check','pom','capa','instancia')` | `models_app/models.py:1307` |
| `GradedSpec` | `('grading_version','pom','size_label','capa','instancia')` | `fitting/models.py:249` |
| `PieceFittingLine` | `('piece_fitting','pom','size_label','capa','instancia')` | `fitting/models.py:461` |
| **`ModelGradingRule`** | **`('model','pom')`** — sense eixos, per acta | `models_app/models.py:1097` |

Confirmat a BD (`fhort`): constraint `models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq`;
`capa` i `instancia` **NOT NULL**; l'únic CHECK viu és `..._instancia_exigeix_nom`. **Cap comporta de capa ni
d'instància sobreviu a BD.** Dades vives: `('exterior','')`=24, `('exterior','relaxed')`=2, `('exterior','top')`=1,
`('exterior','extended')`=1, `('exterior','bottom')`=1. **Les germanes ja són fet consumat, no hipòtesi.**

### La semàntica del «buit», que és el nus de la decisió
- `capa` — `CharField(max_length=20, default='exterior', db_index=True)`, `models.py:725-726`. **Sense `null=True`.**
- `instancia` — `CharField(max_length=60, default='', db_index=True)`, `models.py:749-750`. **Sense `null=True`.**
- `pom/identitat.py:23-26` — «no s'omet mai el tram buit […] **La instància única és el tram buit, no
  l'absència del tram.**»

### El precedent metodològic (`0070`→`0078`), en 7 passos observats
1. Columna a **cinc** taules amb `default` no-NULL — `0070_capa_mesures.py:33-57`. Fast-default PG11+, **cap
   backfill** (`:15-16`), i es declara que «res llegeix aquesta columna encara» (`:18`).
2. Es declara **quina taula NO travessa l'eix i per què** — `0070:7-8` (`ModelGradingRule`).
3. Clau ampliada = mateixes columnes **+1** → «estrictament més permissiva» (`models.py:758-763`);
   `0071_capa_unicitats.py:40-51`.
4. Constraint **amb nom** (`POMPlacement`) → Remove + Add, el nom creix amb els camps — `0071:52-60`.
5. **Comporta CHECK a BD**, no a l'aplicació — `0072_capa_comporta_c1.py:32-61`; motiu a `models.py:776-791`:
   «l'únic lloc on cap camí d'escriptura no la pot esquivar: ni un `bulk_create`, ni un `update()`, ni un
   loader, ni un `psql` a mà».
6. Onada d'instància: clau + comporta **en una sola migració** perquè «és una sola decisió»
   (`0074_instancia_unicitats_comportes.py:3-4`), amb auditoria SQL prèvia declarada (`:23-25`).
7. Retirada de comportes **només després** dels tests de germanes — `0076`/`0077`/`0078`, acta a `models.py:796-800`.

### Cens d'escriptors de `BaseMeasurement` — classificat
**PETA amb 2 peces (lookup sense l'eix → `MultipleObjectsReturned`) / COL·LAPSA abans:**
`extraction_views.py:2575-2578` (literals a `:2577`) · `tech_sheet_views.py:367-382` ·
`pom/wizard_views.py:451-463` · `fitting/services.py:499-502` (el seu propi comentari ho anticipa a `:498`) ·
`models_app/services_size_check.py:234-237`.
**COL·LAPSA silenciós:** `pom/wizard_views.py:413-416` (`.first()` amb un `Meta.ordering` que no cobreix
l'eix, `models.py:774`) · `models_app/views.py:1669-1688` (còpia model→model: la 2a germana cau a `skipped`
a `:1707-1708`) · `tenants/federation_service.py:787-803` (l'eix viatja dins `row['clau']`, format versionat a `:783-784`).
**SOBREVIU** (l'eix ja hi entra per paràmetre, no per literal): `models_app/views.py:3525-3532` (`_write_base`) ·
`:2154-2166` (`set_measurements_view`, via `_identitat_de_mesura` a `:3426-3449`) · `:2339-2350` (`gravar_pom_view`) ·
`clone_model_for_qa.py:92-96`.
**PETA amb 400 fals:** `models_app/serializers.py:432-499` + `views.py:510-527` — `germanes = …filter(**camps)`
(`:486`) sense l'eix casaria amb la germana d'una altra peça.

### Lectors: el punt de major dany silenciós
`models_app/views.py:3408-3417` (`_poda_mesures`) resol la clau **en Python** i **desactiva** (`is_active=False`)
tot el que no hi casi. Amb peça-NULL sobreviu; el dia de la materialització de la 02, una crida amb clau curta
la desactiva. Altres col·lapses: `pom/services.py:838` (motor) · `fitting/services.py:402-410` (a més **esborra**
línies) · `fitting/graded_spec_views.py:115-125` · `models_app/pom_placement_views.py:88-96` (el seu comentari
a `:80-84`: «el pitjor cas d'aquesta vista, perquè no peta: **pinta**»).

### Tests guardians
`test_c4_escriptura_germanes.py:431-442` fixa el contracte de retrocompatibilitat exacte del marc mandrós:
«sense eixos s'escriu a l'exterior i **no es tria cap germana**» — el default és **explícit i no depèn de les
dades** (`views.py:3439-3443`). · `test_seccio_captura.py:156-174` **assereix el col·lapse** i diu per què hi és
(`:165-166`): «el dia que algú toqui la clau, **ho vegi caure aquí** i sàpiga que era conegut».
· `pom/test_u2_r2_capa_instancia_api.py:9-16` documenta **la trampa DRF**: en completar-se la tupla,
`UniqueTogetherValidator` exigeix **tots** els camps de la clau al `create`, i un camp amb `default` de model
arriba a DRF només com a `required=False` → «tota crida que ja existeix passaria a rebre un 400».

> **Veredicte BLOC 1:** el camí tècnic és **conegut i asfaltat** (7 passos, zero backfill). **Cal una decisió
> del CTO sobre el «buit»** abans de tocar res: la convenció mandrosa amb NULL xoca amb tres actes escrites i
> amb el comportament de Postgres. Amb `''` (o un sentinella no-NULL) el precedent és directe i el cost, conegut.

---

## BLOC 2 — SET-1/GarmentSet desplegat, i el numerador de peça

**Desplegat i migrat**: `GarmentSet` (`models_app/models.py:43-77`, `codi_base` unique `:59`, `num_pieces` `:61`,
`consumption_started_at` `:69`) + `Model.garment_set` (`:214-220`, `related_name='peces'`) + `Model.piece_number`
(`:221`). Migracions `0019` i `0065_set1_meritacio_conjunt.py` **aplicades als schemes `fhort` i `los`**
(2026-07-27 12:40, verificat a `django_migrations`).

**Mèrit SET=1, resolt**: un sol `ConsumptionRecord` ancorat al `GarmentSet` (`tasks/services_c.py:225-231`),
germanes **estampades** (`:217-219`), guard idempotent al SET (`:211-214`). `ConsumptionRecord.model` segueix
OneToOne, ara nullable, amb XOR `consumptionrecord_model_xor_set` (`models_app/models.py:1209-1216`). El
reconcile comparteix criteri i **ordena els conjunts primer** (`reconcile_consumption.py:167-171`, `:187`).

**Federació: SÍ propaga el conjunt** — `set_codi_base`, `set_nom_comercial`, `set_num_pieces`, `piece_number`
(`tenants/federation_service.py:116-119`), `get_or_create` per clau natural a `:200-208`; `consumption_started_at`
**no viatja mai** (`:198-199`). Tests: `tenants/tests_traspas_conjunt.py:98-123`.

### El numerador de peça — resposta binària
> **NO EXISTEIX** cap spec ni codi que generi un sufix o referència de peça **DINS d'un mateix Model**.
> El `-01`/`-02` **només existeix com a codi de MODELS GERMANS** sota un `GarmentSet`.

Els tres únics generadors: `models_app/views.py:1000` · `bulk_import_service.py:524` i `:730`. L'origen del
número és `GarmentTypeItemPart.ordre`, amb help_text explícit «dona el sufix -01/-02/-03» (`tasks/models.py:548-549`).
Greps que ho tanquen: `ModelPiece` → **0 hits de codi** a tot el repo · `zfill(2)|:02d|%02d` → 12 hits, cap altre
de peça · a `docs/` cap spec de numerador intra-model. `_real_max_seq` (`models_app/services.py:75-86`) opera
sobre l'enter `sequencial` i **no té cap noció de peça** (les N peces d'un conjunt comparteixen `sequencial`,
`views.py:1005`).

**Cens de dades viu (SELECT, port 5433):** `GarmentSet` = **0** a `fhort` i `los` · Models amb `garment_set`
= **0** · `GarmentTypeItem` amb `is_set` = **0** · `GarmentTypeItemPart` = **0**. **Terra verge als dos costats.**

### SET-1 vs SET-2 — 12 punts de xoc, 8 de convivència (extracte)
**Xoquen:** el mot «peça» amb dos sentits al mateix camp semàntic (`models.py:221`) · `related_name='peces'`
ja pres (`:219`) · el sufix `-NN` del `codi_intern`, amb un parser que fa `split('-')[-1]` sense saber de qui és
el sufix (`views.py:578`) · la capçalera de la fitxa ja pinta «SET n/N» amb navegació a un ALTRE Model
(`ModelSheet.jsx:1678-1693`) · `SetBadge` a la llista (`Models.jsx:633-641`) · el bloc de composició del wizard
(`ModelWizard.jsx:715-740`) · la unitat de mèrit XOR (`models.py:1209-1216`) · `PieceFitting` (`fitting/models.py:356-370`)
i el XOR de `FittingSession` (`:281-292`) · l'import massiu amb columnes `es_conjunt`/`piece_number`
(`bulk_import_service.py:18`) · Planning (`planning/views.py:377`) · **i el catàleg prohibeix explícitament la
segona alçada**: `GarmentTypeItemPart.clean()` rebutja set-de-sets amb el motiu «una sola alçada […] sense aquest
guard la numeració de peces no tindria forma» (`tasks/models.py:571-575`).
**Conviuen:** alçades diferents per construcció (SET-1 per sobre del Model, SET-2 per sota) · `GarmentSet` no té
cap camp tècnic de mesura (`models.py:59-69`) · `garment_set` és read-only a l'API (`serializers.py:125`, `:284`) ·
camí de peça única intacte i testat (`test_set1_creacio.py:157-163`) · 0 dades vives.

> **Veredicte BLOC 2:** SET-1 **no bloqueja** SET-2 estructuralment (alçades distintes, 0 dades), però
> **la col·lisió de vocabulari és real i travessa 4 apps**. El numerador intern **no existeix**: s'hauria de
> crear de zero, i el guard anti-set-de-sets del catàleg (`tasks/models.py:571-575`) és la declaració més
> explícita que avui existeix contra la segona alçada.

---

## BLOC 3 — Grading, derivació i check

| Node | Què llegeix de la clau | Efecte d'un eix `peça` | Línia |
|---|---|---|---|
| `ModelGradingRule` | només `(model, pom)` | **COL·LAPSA per acta** | `models_app/models.py:1097` |
| Sembra de regles | wipe **per MODEL** + `bulk_create` per `pom_id` | **PETA** (`IntegrityError`) | `models_app/services.py:344-347`, `:368`, `:406` |
| `ModelGradingOverride` | 5 columnes amb capa+instància | COL·LAPSA | `models_app/models.py:977` |
| `GradedSpec` | 5 columnes | COL·LAPSA en silenci (`update_or_create`) | `fitting/models.py:249` |
| `_load_base_measurements` | `dict[(pom_id, capa, instancia)]` | **COL·LAPSA**: la perdedora **no perd una cel·la, perd la fila sencera, sense log** | `pom/services.py:838` |
| Bucle del motor | `for (pom_id, capa, instancia), … in …items()` | **PETA** (`ValueError: too many values to unpack`) | `pom/services.py:233`; bessó `:413` |
| `_load_grading_rules` | `{r.pom_id: r}` escalar | **TRANSPARENT A POSTA** — i mai podrà distingir la peça | `pom/services.py:749`, `:752`; frontera a `:722-728` |
| `_load_model_overrides` | tuples sense peça | COL·LAPSA | `pom/services.py:778`, `:812` |
| `_upsert_graded_spec` | eixos **com a paràmetres** | COL·LAPSA sense un paràmetre més (precedent obert) | `pom/services.py:1069-1078` |
| `propaga_ancoratges` | **res** de la clau (funció pura per fila) | TRANSPARENT | `pom/grading_utils.py:1051-1053` |
| `_materialize_lines` (check) | tupla de 3, filtre a Python | **COL·LAPSA**: la 1a peça bloqueja les altres → fila inerta a l'editor | `models_app/services_size_check.py:51-70` |
| `resolve_size_check` | `get_or_create` de 4 | COL·LAPSA: el veredicte aterra a l'altra peça | `models_app/services_size_check.py:234-237` |
| `MeasurementChangeLog` | **cap unicitat**; identitat per còpia de camps | TRANSPARENT a l'esquema; **irreversible al lector** si el signal no copia l'eix (append-only) | `models_app/models.py:896-911`; signal `signals.py:292-293`, `:334-335` |
| `_ORIGEN_TO_CONTEXT` | vocabulari de provinença, cap eix | TRANSPARENT | `models_app/signals.py:200-224` |
| `pom/acumulacio.py:_clau` | `(pom_id, capa, instancia)` de **pertinença de CATÀLEG** | **TRANSPARENT — altra dimensió**: cap fila hi porta `model`; el nivell d'ITEM ja és la unitat per-peça del catàleg | `pom/acumulacio.py:28-30`, docstring `:13-18` |

Consumidors d'`acumulacio`: **un de sol** — `pom/cataleg_views.py:25` i `:183`.

### L'asimetria de `ModelGradingRule`, amb la seva causa
Ho és **des de la creació** (`0037_modelgradingrule.py:36`), i les dues migracions que van ampliar les claus
**no la toquen** (`0071:42-50`, `0074:59-67`); `0079` només afegeix `derivat_de_rule_set` (`:15-19`).
La causa és acta de domini, no restricció tècnica: `models_app/models.py:1005-1020` i el bessó
`pom/models.py:1522-1533`. Efecte net: **els valors es parteixen per peça; la LLEI no.** «Cada peça gradua sola»
és cert com a *resultat* i fals com a *norma*.

> **Veredicte BLOC 3:** el motor **no s'ha de tocar** (zona intocable), però **dues línies seves decideixen el
> sprint**: `pom/services.py:233` (petaria) i `:838` (col·lapsaria en silenci). I `ModelGradingRule` és la
> paret: **cal decisió del CTO** sobre si dues peces del mateix model poden graduar diferent.

---

## BLOC 4 — Import: de `seccio` a peça

**El camí complet, amb línies d'avui:** parser `extraction_views.py:436` (reinici per full) → `:448-451` i `:456`
(dos criteris de detecció) → `:482` (cada POM s'emporta `seccio_vigent`). Camí IA: `extraction_prompt.py:132-135`
(camp `section`, **OPTIONAL**) → `extraction_views.py:1645-1648`. Confluència a `_match_rows` (`:1198`,
docstring `:1210-1212` «`seccio` travessa TAL QUAL», fila a `:1242`, `ordre` a `:1244`). Persistència
`:1477`/`:1658`. El pas W2 (`:1782-1943`) **no toca mai `seccio`**. Escriptura final:
**`extraction_views.py:2563`** (`'seccio': p.get('seccio') or ''`) dins l'`update_or_create` de **`:2575-2578`**.
Migració `0067_basemeasurement_seccio.py`; camp a `models_app/models.py:675`.

**Degradació sense seccions:** `None` a totes les etapes intermèdies → **`''` a BD, mai NULL**
(`:2563` + `models.py:675`). Fixat per `test_seccio_captura.py:149-153`. Al frontend, `agrupaPerSeccio`
(`ImportWizard.jsx:16-23`) retorna un sol grup i el render queda idèntic al d'abans (`:592`, `:597`).

**El col·lapse — línia exacta i silenci:** `extraction_views.py:2575-2578`. El confirm fixa `capa` i `instancia`
a constants (`:2577`), de manera que la clau ampliada **no separa** les dues seccions. **No hi ha cap avís ni
comptador**: `n_bm` compta iteracions, no files (`:2580`), i `grading_avisos` no cobreix el cas. Aigües amunt sí
que hi ha una porta que en tapa el cas majoritari — `_apply_many_to_one_guard` (`:1149`, aplicat a `:1250`,
desvincula **totes dues** files a `:1186-1193`), amb el docstring que ho diu (`:1152-1154`).
**Forat residual identificat:** la via **tenant-only** del pas 2 (`:1893-1901`) **no re-aplica el guard**:
dues files amb el mateix `codi_fitxa` reben el mateix `POMMaster`, queden actives i col·lapsen sense avís.

**Guard de run-label mismatch:** `extraction_views.py:2303-2314` («C1c (D2, guard DUR)»): construeix
`_val_labels` (`:2307-2309`), compara amb `model.base_size_label` re-traduïda (`:2281-2283`), i si no hi és →
`set_rollback` + **422 `base_size_absent`** (`:2311-2312`). Germans al mateix confirm: `poms_no_mencionats` 409
(`:2349`), `manual_trepitjat` 409 (`:2385`), `grading_taula_incompleta` 422 (`:2463`), `container_ambigu` 409
(`:2488`), `container_absent` 409 (`:2496`). Consum al front: `ImportWizard.jsx:797-801`.

**Punt d'inserció del selector (concret):** estat nou a `ImportWizard.jsx:249` (o als derivats `:588-597`);
**UI a `ImportWizard.jsx:1076-1080`** — la línia de resum del pas 2 (`poms_summary`, `:1078`), l'únic punt que
ja és una barra de meta-informació global i precedeix `grupsPoms.map` (`:1083`). Precedents visuals al mateix
wizard: tria-full (`:1032-1064`) i toggle `absoluts|deltes` (`:1239-1256`). Transport: `:539-540` (PATCH `/poms/`)
i/o `:770-771` (confirm).
**L'agrupació per secció JA HI ÉS** (F6): `:16-23`, `:588-589`, `:596`, capçaleres `:1085-1088` (pas 2) i
`:1290-1295` (pas 3).

**Cost de l'agrupació seccions→peces:** l'ordre es conserva en tres nivells (`:1244`, `:1925-1941`, `:2316-2324`).
El que **falta** al transport: `poms_extrets` no té cap camp de peça · `session.resultat['mesures']` té forma
`{pom_master_id, talla_label, valor}` (`:2003`) — **clau per POM sense peça, que ja col·lapsa abans de
l'`update_or_create`** · `ImportWizard.jsx:604` (`buildTaula`) i `:1296` (`<tr key={p.pom_master_id}>`) igual ·
avui **cap decisió humana viatja al confirm com a dada de fila**, només `*_choice` escalars (`:770-771`).

**Cens de consumidors de `seccio`: ja NO és zero — 9 punts en 5 fitxers.** Backend: escriu `:2563`; llegeixen
`pom/wizard_views.py:667` i `fitting/graded_spec_views.py:117`, `:129`, `:149`. Frontend: `ImportWizard.jsx`
(agrupació F6) i `TechSheetEditor.jsx:4938-4944`, `:5085-5093`, `:5146-5154`, `:5515`, `:7172-7180`.

> **Veredicte BLOC 4:** el selector té **punt d'inserció concret i barat** (`ImportWizard.jsx:1076-1080`), i
> l'agrupació visual ja existeix. El cost real **no és la UI: és el transport** — `session.resultat['mesures']`
> està indexat per POM i col·lapsa abans d'arribar a l'escriptura. I `test_seccio_captura.py:156-174`
> **es trencarà per disseny** el dia que la clau creixi: està escrit perquè així sigui.

---

## BLOC 5 — Portes del run/ruleset i l'override per peça

**Els helpers són purs i no coneixen ni `Model` ni peça:** `run_del_document` (`pom/grading_utils.py:265`,
cap I/O `:276`) i `run_del_model(etiquetes, size_system)` (`:344`, «cap escriptura, cap efecte» `:358`).

**La porta d'escriptura:** `_resolve_garment_def(d, model=None)` — `models_app/views.py:720`, llei declarada a
`:725-729`, crida al helper a `:779-781`, herència del sistema a `:778`.

**Cens complet dels escriptors de `Model.size_run_model` (11):** hi passen `create_model_wizard` mono
(`views.py:819`) i **multi, una crida per peça** (`:983`), `update_model_step2` (`:1070`), el CRUD genèric via
`serializers.py:404-406`, l'extraction (`extraction_views.py:2263-2267`, crida directa al helper),
`bulk_import` (`bulk_import_service.py:330-331`), `tech_sheet` (formalment sí, **nul a la pràctica**: passa
`size_system=None`, `tech_sheet_views.py:288`) i `normalitza_size_run.py:101`. **NO hi passen:**
`tenants/federation_service.py:222` (còpia literal) i `copiar_de_model_view` (`views.py:1620-1622`).
(`normalitza_size_run.py:3-5` parla de «les 9 vies»; el cens viu d'avui en dona 11.)

**Els quatre camps ja són nullable i viuen tots a `Model`:** `size_system` `:227-233`, `grading_rule_set`
`:234-240`, `size_run_model` `:310-313`, `base_size_label` `:314-317`.

### Veredicte ancorat sobre l'override
**Mentre la peça sigui una fila de `Model`, l'override ja hi cap i NO cal segona funció**: la porta ja s'invoca
per peça (`views.py:983`) amb el comentari que ho declara (`:957-962`: «cada peça resol el SEU món a través de
la mateixa porta única […] és això —i només això— el que fa que A6 surti gratis»), i el punt d'edició per peça
també existeix (`update_model_step2`, `views.py:1046-1048`).
**Si la peça deixa de ser un `Model`, el punt de trencament són tres línies concretes**, perquè el contracte de
la porta és «dict de **noms d'atribut de `Model`**»: `views.py:791` (les claus són atributs), `:1017`
(`**fields_part` al constructor) i `:1073-1074` (`setattr` cru). A més `:778` **no té la cadena de fallback
`peça.size_system or model.size_system`** que un override de sistema per peça requereix.

**`ModelDetailSerializer.validate()`** (`serializers.py:385-415`) valida **només** `size_run_model`, amb la via
tancada documentada a `:386-392` i pin de test (`test_porta_run_serializer.py:3`).
⚠️ **TROBALLA TRANSVERSAL:** **NO EXISTEIX** cap validació de `grading_rule_set` en aquest serializer, i no és
`read_only` (`:426-427`) → el CRUD genèric assigna joc **sense** `_validar_ruleset_assignable` (`views.py:601`)
i **sense** materialitzar residents (`services.py:326`). **Segona porta oberta, preexistent.**

**P3 · UI:** `RuleSetCard.jsx` **NO ES MUNTA ENLLOC** — confirmat per grep; `ModelSheet.jsx:17-18` i `:1100` ho
declaren («No s'esborren»). La superfície viva és el subespai 4 de `ResumWizardPartit.jsx:747`, que desa amb
`models.updateStep2` embolcallat per `useConfirmacioRuleset` (`:798-799`).
⚠️ **Cost real del hook amb N peces:** els flags es guarden en un objecte pla indexat **només pel tipus**
(`useConfirmacioRuleset.jsx:74`, `:85`) i el guard anti-bucle és `if (!flag || flags[flag]) throw e` (`:83`).
**Si dues peces provoquessin el mateix `tipus` de 409, la segona llançaria error en comptes de demanar la seva
confirmació.** I el payload del 409 porta `model_id` (`views.py:1115`) però **cap identificador de peça**: el
diàleg no pot dir de quina peça parla.

**`derivat_de_rule_set`** (`models.py:1084-1089`, migració `0079:17`): la materialització és **per MODEL**
(`services.py:326-327`, sense cap paràmetre de peça; wipe a `:344`/`:346`). Amb la peça com a `Model` ja funciona
(`views.py:1022-1027`); sense, dues peces amb jocs diferents produirien dues files amb el mateix `(model, pom)`
→ violació directa de `models.py:1097`.

> **Veredicte BLOC 5:** l'override **no obre cap segona via** si la peça és un `Model`. Si no ho és, el cost
> són **3 línies de contracte + 1 cadena d'herència que no existeix + el hook de confirmació**, que avui no sap
> parlar de peces.

---

## BLOC 6 — Fitting i check

**Àncora:** `FittingSession` XOR `garment_set`/`model`, amb `CheckConstraint` dura
(`fitting/models.py:281-292`, `:341-349`) i validació al servei (`services.py:147-148`). **Cap superfície de
frontend crea sessions amb `garment_set_id`** (grep: 0 resultats).
**`PieceFitting`**: clau `('session','model')` (`models.py:396`), gate propi (`:374-383`). **NO EXISTEIX** cap
camp de peça interna. **`PieceFittingLine`**: clau de 5 amb capa+instància (`:461`), **comportes retirades**
per `fitting/0023` (`:467`) — **els dos eixos ja són lliures**.

### La nota de la dissolució de `FittingDetail`: **VIGENT i CONSUMADA**
La línia que ho decideix: **`components/model/measureSources.jsx:49`** — `fittingSessions.createPiece(fittingSession.id, model.id)`,
on `model` és el de la ModelSheet (`CheckMeasureEditor.jsx:399`, `:471`) i `fittingSession` ve del paràmetre
d'URL (`ModelSheet.jsx:198`, `:723-732`): **dues fonts independents**. El camí vell ja és mort per al flux viu:
`FittingDetail.jsx:626-627` redirigeix tota sessió no segellada cap a `/models/<session.model>?tab=Mesures&…`.
⚠️ **TROBALLA TRANSVERSAL:** ni el servei (`services.py:292-357`) ni la vista (`views.py:186-207`) validen que
`model_id` pertanyi a l'àncora de la sessió. L'única barrera és `unique_together` (`models.py:396`), que
impedeix **duplicats** però no **incoherències**.

### La graella: agrupa per COLUMNES, no per files
`MeasureGrid.jsx:380` (contracte), `:565-574` i `:583-592` (cada `group` és un `<th colSpan>`), i el cos és
**`rows.map` pla** (`:596-612`). L'eix capa/instància **no s'agrupa**: es *desambigua* duplicant files amb
`rowKey` sencer (`utils/identitatMesura.js`, `fittingGridAdapter.jsx:155`, `repasGridAdapter.jsx:144-148`) i
pintant-ne una **columna de lectura** (`MeasureGrid.jsx:559`, `:613-618`, `:629`). L'acta de `:601-607` explica
per què: dues `<tr>` amb la mateixa clau feien que React reconciliés l'estat d'una germana amb l'altra.
→ **Portar la peça com a 3r component de la identitat de fila reusa el mecanisme existent** (i toca els 5
adaptadors). Portar-la com a **fila-secció seria mecanisme NOU**. Portar-la com a **columna** reusaria el
patró del repàs (`repasGridAdapter.jsx:111`).

**Veredicte de model:** `SizeCheck` penja del Model (`models_app/models.py:1240-1242`), sense unicitat
(historial repetible, `:1231-1232`). L'agregació és «una de podrida el tomba» (`services_size_check.py:201-205`).
El veredicte de Comprovació també és del model i **es compta per FILA, no per POM** (`comprovacio_views.py:340-345`,
acta a `:335-337`), amb la capçalera que ho argumenta (`:10`: «partir-ho voldria dir cinc rellotges per a una sola»).
**`CheckMeasureEditor` és el component ÚNIC de les dues superfícies** (`:399`, `:402`, `:471`): la convergència
ja està feta, i **l'entrada de tots dos camins és `model`, mai una peça**.

**El segellat:** `session_can_advance` (`services.py:801-811`) **compta files de `PieceFitting`**, no
`num_pieces`. La línia decisiva és **`services.py:820`** — l'únic punt on `garment_set_id` intervé, i només com
a **interruptor de règim**. Cens de lectures de `num_pieces` a `fitting/`: **una de sola**, i és per calcular la
durada per defecte (`services.py:155`). `advance_phase` ja itera peces i fa el pre-check **en bloc** abans de
mutar res (`services.py:897-913`).

> **Veredicte BLOC 6:** el mecanisme de N peces **és reutilitzable en la seva FORMA** (censa files, no un enter
> declarat) — el que hi falta no és la porta, **és l'eix**: la seva unitat de recorregut és el `Model`.
> La graella reusa mecanisme si la peça entra a la identitat de fila; obre mecanisme nou si entra com a grup.

---

## BLOC 7 — Definició del model (§8f): el Resum

**Estructura:** àtom `Subespai` (`ResumWizardPartit.jsx:178-217`) i **tres** subespais numerats 2/3/4:
**Peça** `PasPeca` (`:423-521`, muntat `:284-286`), **Talles** `PasTalles` (`:543-689`, `:287-288`),
**Graduació** `PasGraduacio` (`:738-867`, `:289-290`). La columna esquerra `Informacio` (`:299-421`) **no és un
subespai numerat** i escriu per una porta diferent (`models.update`, `:323`). Muntatge únic:
`ModelSheet.jsx:1105`. Predicats d'estat a `:228-244`.

**Fonts:** **cap** llegeix de context, Redux, URL ni `useParams` — tot ve de la prop `model` (`:219`). L'única
font compartida és `useEixos()` (`:221`), cache de mòdul amb dedup (`eixosFont.js:29-31`, `:48-51`).

**Portes d'escriptura:** `desa` compartit (`:250-269`) → `models.updateStep2` (`endpoints.js:72`).
Peça → `{target, construction, garment_type_item_id}` (`:452-456`) · Talles → `{size_system_id, size_run,
base_size}` (`:608`) · Graduació → `{grading_rule_set_id}` embolcallat pel 409 (`:798-799`).

**`update-step2` resol CAMP A CAMP — verificat**: `views.py:1046`, `_resolve_garment_def` (`:720-793`) és una
cadena de `if d.get('X')`, i `:1073-1074` fa `setattr` només del que hi ha. **Cap camp absent del payload es toca.**

⚠️ **TROBALLA TRANSVERSAL:** **el `fit` de la peça no s'escriu enlloc.** `PasPeca` té estat `fit` (`:428`),
l'ofereix amb una `EixFila` sencera (`:494-495`) i el pinta com a xip tancat (`:472`), però **el payload de
`:452-456` no l'inclou** i **`fit_type` NO EXISTEIX com a camp escrivible** ni a `_resolve_garment_def` ni a
`update_model_step2`. **Triar-lo i desar no canvia res.** (El wizard de creació ho documenta com a decisió,
`ModelWizard.jsx:428-429`; el Resum el pinta com si fos editable.)

**Cost de replicar-lo N vegades — a favor:** 100% parametritzat per props · **zero `id=`, `htmlFor`,
`getElementById`, `querySelector`** als 6 fitxers implicats (grep: 0 hits) → **cap col·lisió d'ids** · tot
l'estat és local per instància · `useEixos` no es multiplica · el `desa` tanca sobre `model?.id` (`:227`).
**Obstacles concrets (4):**
1. **2 crides de xarxa per instància en muntar-se, amb els subespais TANCATS**: `customers.get` (`:556-565`) i
   `gradingRuleSets.get` (`:750-755`), cap de les dues gated per `obert`. Amb 3 peces = 6 crides d'entrada.
   (Les crides cares **sí** estan gated: `:582`, `:761`, `:502`.)
2. **Falten les dades de les germanes**: `garment_set.peces` només porta `{id, codi_intern, piece_number,
   nom_prenda}` (`serializers.py:101-103`) i `ModelSheet` només carrega UN model (`:220-223`) → **N-1 fetches
   addicionals o un endpoint nou**.
3. **`onUpdated` és `reloadModel`** i rellegeix el model de la URL (`ModelSheet.jsx:220-223`): cada instància
   necessita el seu refrescador.
4. **Els tres `Pas*` no són exportats** (`export default` només a `:219`) → per muntar la definició sense
   `Informacio` caldria exportar-los.

**On es declara «aquest model té 2 peces» avui:** **és SET-1 i és LECTURA del catàleg.** El bloc del wizard
només apareix si `item?.is_set` (`ModelWizard.jsx:715`), itera `item.parts` (`:725`), i **l'únic editable és el
NOM** (`:733-738`); el comentari ho declara (`:711-714`: «és el catàleg qui la declara […] i el wizard no la
negocia»). El payload només porta `noms_peces` (`:475-476`) i el backend crea **1 `GarmentSet` + N `Model`**
(`views.py:957-1041`).

> **Veredicte BLOC 7:** **es pot muntar N vegades sense tocar el wizard de creació.** Els quatre obstacles són
> acotats i cap és estructural. El cost real és **portar les dades de les germanes**, no el component.

---

## BLOC 8 — Fitxa tècnica (.ftt)

### La pregunta clau, resposta binària
> **SÍ — un camp desconegut d'un OBJECTE es PRESERVA al round-trip complet (desar → BD → rellegir).**
> **La línia que ho decideix: `pages/TechSheetEditor.jsx:554`** — per a tot objecte que no sigui `data_block`,
> `serializeObject` retorna l'objecte **idèntic** (`base = obj`). No hi ha whitelist de claus per tipus enlloc
> del camí de persistència.

Cadena verificada: desat `:2061-2068` → `:553-556` → `mapObjectTree` `:307-311` → `:691-705` → PATCH `:3682-3684`
→ backend `ftt_document_views.py:225-244` → `services_ftt_document.save_document:503` →
`services_ftt.extract_document_assets:217-231` (docstring: «Preserva TOTA la resta del document […] claus
desconegudes») → `pack:90-123` (`json.dumps`). Relectura: `:202-211` → `documentToV2` `:670-685` → `hydrate`
`:3545-3563` → `paginesFtt.js:21`.
**Precedent PROVAT AMB TEST:** `models_app/test_ftt_peca_grup_roundtrip.py:46-49` («Byte a byte: el .ftt és JSON
sense whitelist de claus per tipus») i `:51-54` (`piece_name`/`pattern_file_id` sobreviuen).
**I ja hi ha tres ancoratges vius amb el mateix patró:** `pomId`/`bmId` (`:438`, `:4304-4305`),
`sourceItemFitxer` (`:4872`, `:6278`) i **`piece_name` + `pattern_file_id`** (`:6343`).

### ⚠️ L'asimetria: objecte OPAC / pàgina CAMP-A-CAMP
A nivell de **pàgina** la resposta és **NO**: quatre punts la reconstrueixen camp a camp —
`utils/paginesFtt.js:19-23`, `TechSheetEditor.jsx:2062-2067`, `:675-682`, `:695-702` — i
`paginesFtt.js:8-10` ho documenta («Cada cop que se n'ha escrit una de nova, la clau nova s'hi ha perdut en
silenci»). **`pieceId` a l'objecte = gratis. `pieceId` a la pàgina = 4 punts + `_amb_format` al backend.**

**`schema_version`: EXISTEIX** (dos: `ftt_schema:1` a `services_ftt.py:36` i `schema_version` al manifest `:105`),
però **cap dels dos es llegeix mai per decidir res**. I **NO EXISTEIX cap migració de documents**:
`services_ftt_document.py:511-513` i `TechSheetEditor.jsx:333` («ELS `.ftt` VIUS NO ES MIGREN»), amb el
precedent directe que `pomId` es va estendre amb capa/instància **sense migrar cap document** (`:337`).

**On agruparia l'arbre per peça:** desplegable de POMs, **`TechSheetEditor.jsx:7009`** (`pomRows.map`), avui una
llista **plana** d'un sol nivell; dades de `:3491` (`GET /models/<id>/base-measurements/`), servides per
`pom/wizard_views.py:565-676` — **el payload no porta cap referència de peça**; l'únic proxy és
`'seccio'` (`:667`), text lliure. Taules: **ja hi ha un nivell d'agrupació per secció**
(`TechSheetEditor.jsx:7170-7181`, `seccionsDeFiles` `:4938-4944`), amb el comentari que diu el que es vol
(`:4930-4932`: «Qui composa la fitxa vol una taula per peça al costat del seu croquis»).
**Nota:** el desplegable de Peces de patró (`:7205-7221`) ja té un `p.id` que és exactament el `pieceId`
candidat, i avui es **descarta** (`:6343` només desa el nom i el fitxer).

**Consumidors camp-a-camp (només 2, i cap és on aniria el `pieceId`):** `_resolve_obj`
(`services_ftt_document.py:186-191`) i `_unfreeze_mapper` (`:301-306`), tots dos **exclusivament per a
`type:'field'` de plantilla**. `TechSheetEntry.jsx` i `tech_sheet_views.py` **NO llegeixen el `.ftt` en absolut**.
`ModelFitxer.fitxer` és un `FileField` (`models.py:475`; confirmat a BD: `character varying`, **no JSONField**),
i el backend **no valida cap estructura** (`ftt_document_views.py:225-239`).

> **Veredicte BLOC 8:** ancorar `pieceId` **als objectes** és viable **sense tocar cap serialitzador i sense
> migració de documents**. El que **no té font de dades** avui és l'arbre de POMs per peça:
> `base_measurements_view` no serveix cap identificador de peça i `seccio` és text lliure, no una FK.

---

## BLOC 9 — Kanban i tasques: cens negatiu

**`ModelTask` ancora al MODEL**: `tasks/models.py:153` (`FK models_app.Model`, `related_name='model_tasks'`).
Unicitat `(model, task_type)` (`:207-211`). **Camps que apuntin a domini de mesura: CAP.**

**El contracte de frontera és `(model_id, slug de TaskType)`** — cens complet dels call-sites de
`batec_de_request`: `models_app/views_size_check.py:78`, `:98` · `models_app/views.py:541`, **`:3694`**
(← aquí `bm` és una `BaseMeasurement`, i **el que travessa és `bm.model_id`, no `bm`**) ·
`models_app/ftt_document_views.py:250` · `fitting/views.py:548`, `:572`, `:579`, `:618`.
**Cap `pom_id`, cap `capa`, cap `instancia`, cap `size_check_id` creua mai cap a `tasks/`.**
En sentit invers: `grep "ModelTask|model_tasks" fitting/` → **0 hits**.
**`fhort.pom.models` NO s'importa mai** al codi de producció de `tasks/`.

**Els 8 punts de creació de `ModelTask`** (`views_b.py:291`, `:351`, `:581`, `:1501`; `services_r.py:139`, `:194`;
`planning/plan_service.py:323`; `clone_model_for_qa.py:118`) **creen tots amb `model=` + `task_type=`** i cap
passa POM, capa, instància, `SizeCheck` ni `PieceFitting`.

**La unitat de la targeta del Kanban és el MODEL**: `views_b.py:157` (`values('model_id', …)`, `GROUP BY model`),
`Dashboard.jsx:107` (`ModelCard({ model })`), `:374-377` (`key={m.model_id}`), `:366` (el comptador és el nombre
de models). El router de tipus de tasca (`utils/destiTasca.js:28-40`, `:74-77`) porta **només `(modelId, taskId)`**.

**`advance_phase_gate`** (`services_d.py:39`) decideix sobre el MODEL i és **l'únic punt de `tasks/` que dispara
escriptura al domini de mesura**, amb granularitat model (`:63-66`, `seal_model_grading`).

**Punts de `tasks/` que SÍ entren en un canvi de la clau (llista tancada, 2, i cap és lògica de tasques):**
1. `tasks/management/commands/bootstrap_tenant.py:167` — la tupla `('garment_type_item','pom','capa','instancia')`
   escrita literalment (és el copiador de tenants, viu sota `tasks/` per accident d'ubicació).
2. `tasks/urls.py:129,157,187,214,221,232,253,271,284` — muntatge de vistes de `fhort.pom` (impacte només si
   canvia la forma de les rutes).

**Punts on el catàleg de tasques toca la PEÇA (SET-1), independents de la clau de mesura (4):**
`GarmentTypeItem.is_set` (`tasks/models.py:432`) · `GarmentTypeItemPart` (`:527-589`, anti-set-de-sets `:574`) ·
`TaskTimeEstimate` (`:591-597`) + `services_g.py:19` · meritació de conjunt (`services_c.py:209-231`).
Dades: **0 sets i 0 files de composició a staging.**

> **Veredicte BLOC 9: el món de tasques/Kanban és IMPERMEABLE a la clau de mesura. Queda FORA del radi de
> SET-2**, amb les dues excepcions llistades, cap de les quals és lògica de tasques.

---

## BLOC 10 — Fronteres

**Dues absències confirmades:** `ModelPiece` → **NO EXISTEIX** (0 ocurrències a `docs/`, `backend/fhort/`,
`frontend/src/`) · `SET-2` → **NO EXISTEIX** (0 ocurrències).

| # | Frontera | Aguanta | Punt de fuita |
|---|---|---|---|
| F1 | G6 · una sola versió vigent per SizeFitting | **SÍ** | constraint `fitting/models.py:105-109`; test `test_g6_estalitud.py:198-208` |
| F2 | G6 · cadena Model→SF→GV→GradedSpec | **NO** | `SizeFitting.unique_together=('model','numero')` (`fitting/models.py:56`) + signal `models_app/signals.py:129-139`. **Cap columna de peça a cap graó**; `numero` és la RONDA |
| F3 | G6 · clau `(pom_id, capa, instancia)` | **NO** | 3-tupla literal a `pom/services.py:233`, `:405`, `:441`. Moure-la desaparellada reprodueix el bug G6/0a (`test_g6_grading_gates.py:117-122`) |
| F4 | G6 · la REGLA no porta eixos | **SÍ, i és muralla** | `pom/services.py:722-729` + `models_app/models.py:1097` + `tenants/federation_service.py:592-598` |
| F5 | G6 · `_te_regles` és «té regles?» | **SÍ** | `pom/services.py:711-719` (àmbit MODEL) |
| F6 | G6-B · el segell no s'escriu per dins | **SÍ** | `pom/services.py:86-98`; `test_g6_segell.py:108-150`. **Una peça no pot tenir segell propi** |
| **F7** | **G6-B2 · ESTALITUD** | **🔴 NO — FUITA** | `fitting/staleness.py:110-115` filtra per `model_id`; `:106` llegeix `model.measurements_version`, **comptador únic per Model** (`models_app/models.py:325`). Tocar la peça B marca ESTALA la peça A; l'avís arriba al patronista (`patterns/adapters.py:493-499`, `patterns/views.py:210`) |
| F8 | BILLING no compta peces internes | **SÍ** | 5 escriptors (`tasks/services_c.py:181`, `:225`; `reconcile_consumption.py:121`, `:250`; `backoffice/receivers.py:15`). **Cap llegeix cap entitat subordinada al Model** |
| F9 | `Model.nom_prenda` — un sol nom | **NO** | `models_app/models.py:181`. Una peça sobreviuria però **sense nom enlloc** |
| F10 | `Model.garment_type_item` — un sol item | **🔴 NO — ESTRUCTURAL** | `models_app/models.py:202-208`. D'ella pengen `GarmentPOMMap` (`pom/models.py:885`), `ItemBaseMeasurement` (`:1282`), `RuleSetScopeNode` (`:1451`), la sembra item→model (`views.py:1307`) |
| F11 | `POMPlacement` | **PARCIAL** | `models_app/models.py:1424-1520`: àncora a `ItemFitxer` (**catàleg**, `:1445-1447`), clau `:1498-1500`. Dues peces comparteixen l'`ItemFitxer` del seu únic GTI i col·lidirien al mateix `view_slot`. Decisió declarada **OBERTA** al codi (`:1509-1512`) |
| F12 | `Watchpoint` | **SOBREVIU, cec** | `models_app/models.py:1327-1356`; `dades` JSONField (`:1341`) és l'única butxaca lliure |
| F13 | Paquet LOSAN | **SÍ, trivialment** | Cap dels dos toca `models_app.Model` (`export_losan_package.py:35`, `load_losan_package.py:35`). Ja transporta `is_set` (`export:229`) i `GarmentTypeItemPart` (`export:234`) |
| F14 | `bootstrap_tenant` | **SÍ, trivialment** | `_spec()` (`bootstrap_tenant.py:139-179`), 20 entitats de catàleg, cap `Model`. ⚠️ Deute documentat al fitxer (`:162-166`): tota taula nova no afegida a mà deixa el tenant nou coix |
| **F15** | `federation_service` | **🔴 NO — 3 FUITES SILENCIOSES** | `:96-131` (22 claus a mà) · `:211-238` (20 kwargs) · `:679-735` (3 llistes). El fitxer **ja documenta aquest mode de fallada** per a capa/instància a `:663-672` |
| F16 | `TechSheetEditor` read-only | **SÍ** | 2 escriptors (`ftt_document_views.py:185-188`, `:244`), tots dos reben el blob del client; l'única injecció del servidor són 13 claus escalars (`services_ftt_document.py:103-116`), cap de mesura |
| F17 | `FittingSession`/`PieceFitting` | **NO** | `fitting/models.py:341-349`, `:396`. **«Peça» ja vol dir «un Model sencer»** |

### Mecanismes de còpia que enumeren camps a mà (perdrien `ModelPiece` en silenci)
1. `tenants/federation_service.py:96-131` · 2. `:211-238` · 3. `:679-735` ·
4. `models_app/views.py:1518` (`copiar_de_model_view`; 4 blocs a `:1533-1541`, mesures a `:1671-1686`) ·
5. `clone_model_for_qa.py:73-84` i entitat per entitat (`:90`, `:99`, `:105-111`, `:118`) ·
6. `bulk_import_service.py:509-524`.
**Nota útil:** `copiar_de_model_view` **sí** copia `capa`/`instancia` de la fila d'origen
(`views.py:1665-1670`, comentari FASE_3/C1-ins: «la còpia COPIA: els eixos surten de la fila d'origen, no de cap
literal»). **El patró de fer créixer una clau i que la còpia la segueixi ja s'ha executat una vegada, i el
rastre és llegible.**

⚠️ **Efecte lateral que travessa la frontera del `.ftt`:** el PATCH del document dispara `batec_de_request`
(`ftt_document_views.py:250`) → `_meritar_si_cal` (`tasks/services_batec.py:137`, `:145`). **L'autodesat de
l'editor cada 2 s és un gallet de meritació SaaS** — però merita per Model o GarmentSet, mai per peça: F8 el conté.

> **Veredicte BLOC 10:** billing, paquet LOSAN, bootstrap i el `.ftt` **aguanten**. Les tres fuites reals són
> **F7 (estalitud), F10 (un sol GTI per Model) i F15 (federació)**, i cap de les tres és a la clau de mesura.

---

## TAULA FINAL DE RISCOS PER AL CTO

| # | Risc | Gravetat | Ancoratge | Què el desbloqueja |
|---|---|---|---|---|
| **R1** | **La convenció mandrosa amb NULL trencaria la protecció de la clau.** Dues files amb `peca IS NULL` i la resta igual entrarien totes dues | 🔴 **BLOQUEJANT** | `models.py:744-745` · `pom/models.py:917-919` · `nulls_distinct` **NO EXISTEIX** (0 hits) | **Decisió d'Agus**: sentinella no-NULL (`''` / `0`, com capa i instància) vs `UniqueConstraint(nulls_distinct=False)` vs NULL assumint la pèrdua |
| **R2** | **`ModelGradingRule('model','pom')` impedeix que dues peces amb el mateix POM gradúin diferent**; i la sembra **peta** abans (wipe per model + `bulk_create`) | 🔴 **BLOQUEJANT** | `models.py:1097` · acta `:1005-1020` · `services.py:344-347`, `:368` | **Decisió d'Agus**: la llei d'increments és del model o de la peça? Els 2 tests-pin **no ho aturarien** (miren noms de columna) |
| **R3** | **`germanes_de` creuaria les peces i ESCRIU**: corregir el pit de la peça 1 mouria el de la peça 2 | 🔴 **ALT** | `services_derivacio.py:72-78`, `aplica()` `:124`, invocat des de `services_size_check.py:255-257` | Afegir la peça al filtre; és canvi acotat però **cal fer-lo abans de materialitzar cap 02** |
| **R4** | **Estalitud contaminada entre peces**: tocar B marca ESTALA el segell d'A, i l'avís arriba al patronista | 🔴 **ALT** | `fitting/staleness.py:106`, `:110-115` · `models_app/models.py:325` | Decidir si `measurements_version` és per model o per peça |
| **R5** | **El motor peta i col·lapsa**: `for (pom_id, capa, instancia), … in items()` i `dict[3-tupla]` | 🟠 MITJÀ | `pom/services.py:233`, `:413`, `:838` | Zona intocable: **el sprint hi ha d'entrar amb permís explícit** |
| **R6** | **`_poda_mesures` desactiva files** que no casin amb la clau curta | 🟠 MITJÀ | `models_app/views.py:3408-3417` | Dany silenciós; entra al cens d'escriptors |
| **R7** | **Federació perd `ModelPiece` en silenci** (3 punts amb camps a mà) | 🟠 MITJÀ | `federation_service.py:96-131`, `:211-238`, `:679-735` (i `:663-672` ja ho documenta per capa/instància) | El format de paquet ja té versionat de clau: camí obert però **contracte extern** |
| **R8** | **El transport de l'import col·lapsa abans d'escriure**: `resultat['mesures']` indexat per POM | 🟠 MITJÀ | `extraction_views.py:2003`, `:2186-2190` · `ImportWizard.jsx:604`, `:1296` | El selector és barat; **el transport no** |
| **R9** | **Un model = un `garment_type_item`**: americana + pantaló són 2 GTI i el Model en guarda 1 | 🟠 MITJÀ | `models_app/models.py:202-208` | El catàleg ja sap dir-ho (`is_set`); el Model no |
| **R10** | **Col·lisió de vocabulari**: «peça» ja vol dir «un Model sencer» en 4 apps | 🟡 BAIX-MITJÀ | `fitting/models.py:396` · `models.py:221` · `tasks/models.py:550` | Nomenclatura; barat si es decideix aviat, car si es decideix tard |
| **R11** | **`useConfirmacioRuleset` no sap parlar de peces**: 2 peces amb el mateix `tipus` de 409 → la 2a **llança error** | 🟡 BAIX | `useConfirmacioRuleset.jsx:74`, `:83`, `:85` · payload sense id de peça (`views.py:1115`) | Acotat |
| **R12** | **DRF exigirà tots els camps de la clau al `create`** en completar-se la tupla | 🟡 BAIX | `pom/test_u2_r2_capa_instancia_api.py:9-16` | **Ja documentat i resolt una vegada**: el patró és reutilitzable |
| **R13** | `create-piece` accepta qualsevol `model_id` sobre qualsevol sessió | 🟡 BAIX (preexistent) | `fitting/views.py:186-207` · `services.py:292-357` | Fora d'abast; **es censa** |
| **R14** | El CRUD genèric assigna `grading_rule_set` sense validar ni materialitzar | 🟡 BAIX (preexistent) | `serializers.py:385-415`, `:426-427` | Fora d'abast; **es censa** |
| **R15** | El `fit` del Resum es pot triar i **no es desa enlloc** | 🟡 BAIX (preexistent) | `ResumWizardPartit.jsx:428`, `:452-456` · `views.py:740-793` | Fora d'abast; **es censa** |

### EXISTEIX / FALTA / DIFERENT

| Peça del marc | Estat |
|---|---|
| Entitat `ModelPiece` | **FALTA** — NO EXISTEIX (0 hits a tot el repo) |
| Numerador de peça intern (-01/-02 dins un model) | **FALTA** — NO EXISTEIX; el `-NN` és de Models germans |
| Eix qualificador a la clau de mesura | **EXISTEIX, ×2** (`capa`, `instancia`) — el 3r seria el 5è camp |
| Procediment d'afegir un eix | **EXISTEIX** — 7 migracions documentades, zero backfill |
| Convenció de «buit» a la clau | **DIFERENT** — la casa usa `''` NOT NULL, el marc proposa NULL |
| Multi-peça | **EXISTEIX, però A DALT** (SET-1: N Models germans) i **INERT** (0 files) |
| Porta única de run/ruleset per peça | **EXISTEIX** mentre la peça sigui un `Model` (`views.py:983`) |
| Override nullable de run/ruleset | **EXISTEIX de facto** (4 camps nullable per fila `Model`) |
| Mecanisme de N peces al fitting | **EXISTEIX** en forma (censa files, no `num_pieces`) — **DIFERENT** en unitat (Model) |
| Agrupació per files a la graella | **FALTA** — `MeasureGrid` agrupa columnes, no files |
| `pieceId` als objectes del `.ftt` | **EXISTEIX el mecanisme** (round-trip opac, provat amb test) |
| Font de dades de l'arbre de POMs per peça | **FALTA** — `base_measurements_view` no serveix cap id de peça |
| Kanban/tasques dins del radi | **FORA** — cens tancat |
| Billing dins del radi | **FORA** — 5 escriptors, cap sota el Model |

---

## 💡 PROPOSTES (a validar) — separades dels fets

> Cap d'aquestes és una decisió. Són camins que el codi permet, amb el seu preu llegit.

**💡 P1 — Sobre R1 (el «buit»).** El codi ofereix tres camins amb preus diferents: (a) **sentinella no-NULL**
(`peca=''` o `peca_id=0`), que reusa el precedent literal de capa/instància i manté la protecció de la clau, al
preu de no poder posar-hi una FK real; (b) **`UniqueConstraint(..., nulls_distinct=False)`**, que Django ≥5 i
PG15+ suporten i que recuperaria la protecció amb NULL, al preu d'abandonar `unique_together` (**NO EXISTEIX cap
ús al codi**: seria el primer); (c) **NULL amb `unique_together`**, que és el que el marc diu i el que les tres
actes desaconsellen. La convenció mandrosa (materialitzar la 01 en crear la 02) **funciona igual amb (a)**.

**💡 P2 — Sobre R2 (`ModelGradingRule`).** L'acta diu «la sisa dreta i l'esquerra gradúen igual» — un argument
sobre **germanes de la mateixa peça**. Que un top i una braga d'un bikini gradúin igual és una afirmació
diferent, i el codi no la conté. Si la resposta és «la peça sí que canvia la llei», cal `AlterUniqueTogether`
sobre `ModelGradingRule` **i** tocar el wipe de `services.py:344-347` **i** actualitzar els dos tests-pin perquè
vigilin el principi i no dos noms de columna.

**💡 P3 — Sobre l'ordre del sprint.** Els fets suggereixen que **R3 i R4 s'han de resoldre ABANS de materialitzar
cap peça 02**, perquè tots dos **escriuen o invaliden** i el seu dany és silenciós. La resta (transport
d'import, graella, Resum, `.ftt`) són additius i es poden encuar.

**💡 P4 — Sobre el vocabulari (R10).** El codi ja distingeix `GarmentSet` de `GarmentGroup` per docstring
(`models_app/models.py:49-53`): hi ha precedent de desambiguar dos «grups» amb noms diferents. Un nom que no
sigui `piece`/`peça` per a l'entitat nova estalviaria la col·lisió a `PieceFitting`, `Model.piece_number` i
`GarmentTypeItemPart.nom_peca`.

**💡 P5 — Sobre el `.ftt`.** Com que el round-trip d'objecte és opac i **no hi ha migració de documents**,
`pieceId` hi podria entrar **abans** que la resta del sprint, sense cost i sense risc de regressió — sempre que
vagi a l'**objecte** i mai a la **pàgina**.

---

## PENDENT DE VERIFICAR (no es va poder tancar en aquesta diagnosi)

1. **La suite d'app no s'ha pogut completar**: `manage.py test fhort.pom fhort.fitting fhort.models_app` es va
   aturar pel `timeout` de 50 min (exit 143) sense emetre resultats. **No hi ha xifra de verd per a aquest tram.**
2. `pom/identitat.py:38-46` (`clau_mesura`) és el **punt únic de la clau aplanada de payload** i el seu docstring
   diu que el frontend l'ha de desmuntar; **no s'ha obert en detall**. Un 4t tram toca backend i front alhora.
3. `GarmentSet.num_pieces` es declara «immutable després de la creació» (`models.py:62`) però **no s'ha trobat
   cap guard que ho imposi**.
4. `_generated_from()` de `fitting/staleness.py` no s'ha llegit: si també fos per Model, la fuita **F7** tindria
   dos camins en comptes d'un.
5. `darrera_peca_amb_contingut` (`fitting/esdeveniments.py`) tria **quina** `PieceFitting` alimenta la secció de
   tolerància del veredicte; amb N peces l'heurística importa i no s'ha censat.
6. `views_b.py:1037` (`poms_count=Count('pom_maps')`): amb la clau de 4 ja compta pertinences, no POMs distints.
   No s'ha verificat quin nombre espera la graella del Finder.
7. `SizeFitting.numero` — no s'ha determinat si el sistema tolera SFs paral·lels per al mateix model.
8. `DIAGNOSI_MULTIPECA_DALIA.md` (vigent) **no s'ha obert**; el codi hi remet des de `models_app/models.py:668-674`
   com a font del mateix problema, classificat allà com a **decisió d'arquitectura (Patró C), no d'sprint**.
9. `models_app/models.py:670` conté una afirmació **factualment falsa** avui («la clau segueix sent
   `('model','pom')`»): va néixer a `0067` i no s'ha actualitzat en travessar C1, C1-ins i C4. La resta del seu
   diagnòstic segueix vigent.
