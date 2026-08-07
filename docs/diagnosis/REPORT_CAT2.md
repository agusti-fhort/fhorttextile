# REPORT · CAT2 — 2026-08-07

> Staging `dev`. **Cap push.** Commits locals 101→106. Base: `REPORT_CATALEG_TALLES.md` i la
> revisió independent `REVISIO_C1C6_2026-08-07.md`, que va entrar mentre aquest tram començava
> i que ha canviat dues peces.
> Cens complet a [`CENS_CAT20_RELACIONS.md`](CENS_CAT20_RELACIONS.md).

---

## 0 · TITULAR

| bloc | estat |
|---|---|
| **CAT2.0** cens preguntant als models | ✅ fet · cap sorpresa que obligués a aturar |
| **CAT2.1(a)** talla base per etiqueta | ✅ fet · **backfill 100%**, 1.267 regles |
| **CAT2.1(b)** retirar la FK | 🛑 **NO FET** — ~20 fitxers, tram propi |
| **CAT2.2** sembrar grups a `los` | ✅ fet · **backfill de C6 al 100% als 3 schemes** |
| **CAT2.2** pas 2 de C6 (retirar el string) | 🛑 **NO FET** — ~18 punts + 26 fixtures |
| **CAT2.3** duplicats i clau | ✅ fet · 37→34 perfils · constraint als 3 schemes |
| regressió de C4 (revisió) | ✅ **arreglada** — dos camins escrivien `ordre` |
| `24M` → `24-36` (revisió) | ✅ **corregit** |

🔑 **La troballa que redimensiona tot el tram: el motor ja treballava per etiqueta.** CAT2.1
resulta ser molt més petita del que la seva pròpia premissa deia, i CAT2.1(b) molt més gran.

---

## 1 · CAT2.0 · EL CENS, BEN FET

Preguntat a `_meta.related_objects` (no a `information_schema`) i **baixant un nivell pels
fills que cauen per CASCADE**. Als 3 schemes.

- ✅ **Cap relació amb `db_constraint=False` apunta a les 5 entitats del tram.** Les que
  n'hi ha (`GarmentPOMMap`, `ItemBaseSet`, `ItemBaseMeasurement`, `GradingRuleSet`,
  `RuleSetScopeNode` → `garment_type_item`) viuen **un nivell més avall**, i el cens només les
  veu perquè baixa pels fills. Sense aquesta passada, esborrar un `GarmentType` semblaria
  costar 62 files i en costa **2.259**.
- 🔑 **`GradingRule.talla_base` = 1.267 regles** a `fhort`, no 350. Els 350 eren només el tros
  ancorat a `TGIRL-EU-HEIGHT`.
- 🔑 **`SizingProfile` té UNA relació entrant i és ella mateixa** (`parent_profile`, 1 fila).
  Això va canviar CAT2.3 sencer — v. §4.
- ✅ Cap relació que el cens de la nit donés per zero ha aparegut: **no calia aturar-se**.

---

## 2 · CAT2.1 · GRADING PER ETIQUETA

### (a) ✅ Fet i auditat — `GradingRule.talla_base_label`

| schema | regles | amb etiqueta | divergències etiqueta≠FK |
|---|---|---|---|
| `public` | 0 | 0 | 0 |
| `fhort` | **1.267** | **1.267 (100%)** | **0** |
| `los` | 0 | 0 | 0 |

Repartiment a `fhort`: `128` ×350 (justament les de l'àncora TGIRL) · `M` ×265 · `S` ×247 ·
`2` ×122 · `8` ×104 · `00/01` ×95. El backfill **avorta** si no arriba al 100%.

### 🔑 El diagnòstic del brief era mig correcte, i la meitat que fallava importa

> **El motor JA resolia per etiqueta.**

`_apply_rule` ancora a `model.base_size_label` sobre el run del **model**, i
`grading_utils.py:72` ja ho deia en veu alta des d'abans: `rule.talla_base` és **«mer metadata
del seed»**. La FK no calculava res.

El dany, doncs, **no era de càlcul sinó d'ACOBLAMENT**: una FK `PROTECT` a una fila d'un run
concret és el que va lligar 1.267 regles a runs que no són seus i el que va fer impossible
esborrar «Alpha EU — Grading Reference». Corregir-ho segueix valent la pena — però la peça no
és «canviar el motor», és «treure una àncora que no calculava».

I el patró ja era a casa: el germà `talla_break_label` **de la mateixa taula** ja és etiqueta
(«*break ancorat per ETIQUETA*»), i `ModelGradingRule.talla_base_label` també. Només el catàleg
conservava la FK.

### (b) 🛑 NO FET — i per què

No per (a), que és net. **Per mida.** Retirar la FK toca ~20 fitxers:

`pom/serializers.py` · `pom/views.py` · `pom/s2_views.py` · `pom/size_map_views.py` ·
`pom/grading_utils.py` · `models_app/services.py` · `models_app/views.py` ·
`models_app/extraction_views.py` · `models_app/bulk_import_service.py` · `models_app/matching.py` ·
`tasks/management/commands/bootstrap_tenant.py` · i **8 commands de seed/paquet**
(`seed_losan_rules`, `_v2`, `seed_losan_grading_v3`, `seed_losan_master_delta`,
`seed_brownie_ruleset`, `seed_baby_months_grading`, `export_losan_package`,
`load_losan_package`, `reseed_tenant_fhort`, `cleanup_losan_old`, `fix_adult_talla_base`,
`fix_brownie_talla_base`).

És un tram propi amb la seva correguda de tests, no una cua d'aquest. **El test que el brief
demana** —un mateix ruleset aplicat a un model amb run ALPHA i a un altre amb run AGRUPAT— és
la peça de valor i s'ha d'escriure allà, perquè és el que demostra que el desacoblament serveix
per a alguna cosa. 🚩 Nota: com que el motor ja treballa per etiqueta, **aquest test hauria de
passar JA**; escriure'l abans de (b) és barat i seria una bona primera peça d'aquell tram.

⚠️ **Comportament d'etiqueta inexistent al run del model**: el brief demana «regla no aplica +
avís, MAI silenci». El motor **ja ho fa** per al camí de STEP (`_apply_rule` deixa la cel·la
ABSENT i emet warning, mai zero ni fallback). No s'ha tocat res.

---

## 3 · CAT2.2 · `los` I EL TANCAMENT DE C6

### ✅ Sembra feta

La fila òrfena mai va ser un problema de dades: **ningú havia creat els grups en aquell
tenant**. La sembra no s'inventa cap catàleg — surt dels **codis que els propis `GarmentType`
del mateix schema ja citen**. Ni un de més ni un de menys; on el vocabulari ja era complet, és
un no-op exacte.

| schema | `GarmentGroup` | `GarmentType` amb grup i **sense** FK |
|---|---|---|
| `public` | 8 | 0 |
| `fhort` | 12 | 0 |
| `los` | **1 (`TOPS`, nou)** | **0** (abans 1) |

**El backfill de C6 tanca al 100% als tres schemes.** La migració avorta si en queda cap.

### 🛑 El pas 2 (retirar el string) segueix sense fer

Ja **no per dades** —el blocador que el va aturar ahir ha desaparegut— sinó per mida: ~18 punts
de codi no-test + 26 fixtures. Els tres deutes que el cens va destapar continuen oberts i són
els que s'han de pagar primer:

1. 🚩 `pom/serializers.py:169` · `GarmentTypeSerializer` és `fields='__all__'` → camps
   explícits + `SlugRelatedField(slug_field='codi')`.
2. 🚩 `pom/views.py:127` · `filterset_fields=['actiu','grup']` → FilterSet amb `grup__codi`.
3. 🚩 3 tests citen codis inexistents: `tasks/tests.py:39` i `patterns/tests.py:901`
   (`'tops'`, minúscules) · `models_app/test_g1_graduacio.py:72` (`'TOP'`, singular).

⚠️ I el que fa por de debò: `proximitatRun.js:50,56` **falla EN SILENCI** si el contracte passa
d'un codi a un id — ordena malament i no llança res. Cap test d'integració ho detecta.

---

## 4 · CAT2.3 · `SizingProfile` — i la pregunta que el cens va obligar a fer

El cens va ensenyar que **els 2 grups NO eren el mateix cas**:

| grup | ids | què eren |
|---|---|---|
| **A** | 539 · 540 · 541 | duplicats accidentals de debò: cap `parent_profile`, tots v1, rulesets 175/176/177 |
| **B** | 288 · 510 | **NO era un duplicat**: 510 té `parent_profile=288` — és una **VERSIÓ** |

El grup B posava una pregunta estructural que no era meva: tots dos amb `customer=NULL`, i per
tant amb la mateixa clau natural. Posar la constraint **inutilitza el versionat per
`parent_profile` sempre que la versió no canviï cap dels 6 camps de la clau** — que és
exactament aquest cas.

**Decisió d'Agus (07/08): esborrar 510 i posar la clau.** El seu ruleset (98) és bessó **byte a
byte** del canònic 81, que és el del 288: la versió no aportava res.
⚠️ **Conseqüència assumida i escrita al `Meta` del model**: una versió del mateix àmbit ja no és
possible sense canviar `customer`.

**Resultat:** `fhort` 37 → **34** perfils · constraint `UNIQUE` als **3** schemes · **0** grups
duplicats. Del grup A es queda **539** (criteri del brief: empaten en «ruleset viu» → el més
antic).

Dos detalls que el delete no dona per fets: torna a comprovar la clau natural de cada fila
abans de tocar-la (avorta si no casa amb el cens) i **reassigna els fills de `parent_profile`
al que es queda**, en comptes de deixar un NULL mut.

---

## 5 · EL QUE LA REVISIÓ INDEPENDENT VA TROBAR, VERIFICAT I TANCAT

Les tres afirmacions materials les he comprovat abans de tocar res. **Les tres eren certes.**

### ✅ Arreglat · la regressió que C4 va deixar viva (dos camins, tots dos meus)
- **CLONAR/CREAR** (`size_map_views.py:803`) renumerava `ordre` **in-place** dins d'un
  `update_or_create` en bucle → amb la constraint nova, IntegrityError dins l'`atomic` →
  **500 i rollback del desat sencer del wizard**. Ara: aparcar a la banda 10.000+ i després
  escriure, igual que van haver de fer `0064`/`0065`. Les talles que no venien a l'input reben
  una cua contigua en comptes de quedar-se amb un ordre inventat.
- **«Afegir talla»** (`SizeSystemDrawer.jsx`) enviava `ordre = definitions.length + 1` i
  **fallava en silenci**. Dos errors en un: comptar files dona un número que ja existeix en
  qualsevol run amb forat —i **els forats a `ordre` són legítims**— i el 400 es perdia sencer.
  Ara el següent surt del **màxim** i el rebuig s'ensenya. i18n ×3.

### ✅ Corregit · `24M` → `24-36`
La revisió va portar la prova que em faltava, i no és una opinió sinó **dues sèries de la
casa**: `BABY_EU_CM` fa servir `24-36` per a la banda que segueix `18-24`, i la **primera**
banda de `TODDLER_EU` és també `24-36` — encaixa exactament amb el final de `BABY_MONTHS`. El
`30` obria un forat de 6 mesos que a les dades no hi és.

### 🚩 CONFIRMAT i NO tancat · el «fre» de `SizingProfile` era codi mort
Verificat: **cap `full_clean()` a `fhort/`** fora de `tenants/`, `pom/admin.py` **sense cap
`register`**, i **DRF no crida `Model.clean()`** (només els `validate_<camp>`). El comentari de
C4 deia «el fre viu a `clean()`» i **el fre no vivia enlloc**.
Ara ja no importa per a la unicitat —la constraint de BD la fa complir de debò (§4)— però
**el `clean()` segueix sent inert** com a cinturó, tal com el brief el volia. 🚩 Si el vols viu,
el lloc és un `validate()` al serializer d'escriptura de perfils.

### 🚨 CONFIRMAT i NO tancat · `public.TODDLER_EU` continua corrupte
La meva C1 el va classificar «sèrie monòtona → intacte». **Una corrupció uniforme és
monòtona**, i la revisió té raó. La prova, creuant amb una sèrie independent **al mateix cos**:

| run (`public`) | talla | alçada | bust | edat | **waist** | **hip** |
|---|---|---|---|---|---|---|
| `KIDS_EU` | 6Y | 116 | 60 | 72-84 | **54** | **64** |
| `TODDLER_EU` | 116 | 116 | 60 | 72-84 | **34** | **40** |

Mateixa alçada, mateix bust, **mateixa franja d'edat**, i 20 cm de diferència. No és només la
fila 116: **tota la columna waist/hip de `public.TODDLER_EU`** (26·28·30·32·34 / 32·34·36·38·40)
està ~20 cm avall.

🚩 **NO l'he tocada, i és deliberat.** Reparar-la vol dir escriure 10 valors corporals nous a un
run del catàleg **`public`, que és el que sembra els tenants nous** i que viatja al paquet
LOSAN. Els valors els ha de dir la Montse, no un algorisme meu — el mateix criteri que em va fer
no tocar el `body_bust_cm` de `fhort`. **És la decisió #1 de la llista de sota.**

---

## 6 · VERIFICACIÓ

| control | resultat |
|---|---|
| `manage.py check` | ✅ net a cada pas |
| `migrate_schemas` (mai `--schema`) | ✅ `0069`→`0072` als 3 schemes |
| auditoria directa a la BD | ✅ a cada peça (constraints a `pg_constraint`, dades per schema) |
| `npm run build` | ✅ `built in 865ms` |
| lint dels fitxers tocats | ✅ 0 errors |
| i18n ca/en/es | ✅ paritat verificada |
| **suite** `fhort.pom` + `fhort.models_app` | ⏳ una sola correguda, **sense `--keepdb`**, amb el codi de sortida capturat de debò |
| fum `qa_n_capes_run.py` | ⏳ |
| restart de `ftt-staging` | ⏳ |

🔵 **El parany del codi de sortida, pagat:** a la sessió anterior vaig llegir `exit 0` d'una
correguda que anava per un pipe (`… | tail`), i **el codi que arriba és el del `tail`, no el de
la suite**. Aquí la sortida va a fitxer i `$?` es llegeix directament.

---

## 7 · EL QUE ESPERA LA TEVA PARAULA

| # | on | la pregunta |
|---|---|---|
| **1** | §5 | 🚨 **`public.TODDLER_EU`**: 10 valors de waist/hip ~20 cm avall, en un run que **sembra els tenants nous**. Prenem els de `KIDS_EU`/`fhort` com a referència, o els dona la Montse? |
| 2 | §2 | `body_bust_cm` de la talla 116 de `fhort` (60, li tocaria 63) — segueix pendent des d'ahir. |
| 3 | §2b | CAT2.1(b) com a tram propi: l'obrim amb el test dels dos mons primer? |
| 4 | §3 | El pas 2 de C6 com a tram propi, amb els 3 deutes del serializer/filterset/tests. |
| 5 | §5 | El `clean()` de `SizingProfile`: el deixem inert o el movem a un `validate()` viu? |

---

## 8 · SORPRESES

1. 🔴 **La premissa de la peça de fons era mig falsa.** CAT2.1 es va escriure creient que el
   motor depenia de `talla_base`; el codi ja deia el contrari **al comentari d'una funció**
   (`grading_utils.py:72`). La feina segueix valent la pena, però per una altra raó.
2. 🔵 **Un parany de Postgres que `public` hauria amagat**: esborrar i fer `ALTER TABLE` a la
   mateixa transacció deixa «pending trigger events». A `public` no s'esborra res → passava, i
   el problema només sortia a `fhort`. `SET CONSTRAINTS ALL IMMEDIATE` abans de l'ALTER.
3. 🔵 **Una constraint nova no és una peça acabada.** Les dues regressions de §5 no eren de la
   constraint: eren del **codi de sempre vivint sota una regla nova**. La lliçó és que un
   `AlterUniqueTogether` obliga a censar els ESCRIPTORS del camp, igual que un delete obliga a
   censar els lectors.
4. 🟡 **La col·lisió de numeració de commits ha passat a ser de hashos**: `24fdd6a5` (revisió) i
   `c44bd274` (CAT2.0) porten tots dos el número `101`.
