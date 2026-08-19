# REPORT · la nit de les capes · 2026-08-06 (N1-N6)

> **Data** 2026-08-06 nit · **règim nocturn, sense l'Agus** · staging `/var/www/ftt-staging`,
> branca `dev`. **Cap push** (el fa ell).
> **Base:** `origin/dev` = `dev` = `3a0123a3` (el seu push del vespre, ~21:15) → **6 commits
> nous** (82 · 83 · 84 · 85 · 86 + aquest). El HEAD final és el commit que porta aquest report.
> Diagnosi que acompanya la nit: [`DIAGNOSI_VOCABULARIS.md`](DIAGNOSI_VOCABULARIS.md).
> Arquitectura actualitzada: [`ARQUITECTURA_2026-08-06.md`](ARQUITECTURA_2026-08-06.md).

---

## 0 · RESUM

| tram | què | commit | verd |
|---|---|---|---|
| **N1** | el run de talles es descriu a si mateix: `tipus_escala` + les 4 capes de restricció | `d040e5bb` | `check` net · **10 tests nous** · 27/30 runs classificats · 12 FK de client lligades |
| **N2** | la Size Library ensenya el RUN, no la graduació | `9fdd2fab` | `build` net · eslint **0 errors, 4 warnings = baseline** · paritat i18n ca/en/es |
| **N3** | el pas 3 del wizard llegeix les 4 capes del run | `adaed65a` | `node --test` **218/218** (14 nous) · `build` net · eslint = baseline exacte |
| **N5** | Patró A: els 4 vocabularis, POM System desvinculat i el cens de la biblioteca | `979135bb` | read-only · cap línia implementada |
| **N4** | decisió 6.1: el wipe deixa de matar l'autoria del tècnic | `f8dd7eb7` | `check` net · **132/132** (94 de `tests_sembra_grading` + 3 suites veïnes) |
| **N6** | fum propi read-only + arquitectura al dia + aquest report | *(aquest commit)* | v. §6 |

*(N5 va entrar abans que N4 perquè la diagnosi no depèn de cap verd de test i N4 sí.)*

### El titular

**Un run de talles ja no és una escala muda.** Fins aquesta nit, qui deia per a qui servia un
run era el `SizingProfile` —la combinació target × família × construcció × fit— i això obligava
a **inventar-se un perfil, i amb ell una graduació, només per declarar que un run existeix per
a un àmbit**. Ara el run porta les seves pròpies etiquetes, la Size Library les ensenya, i el
pas 3 del wizard hi ordena. Cap capa nova lliga amb cap altra: zero camps de graduació, zero
FK a POMs.

**I la bomba de la graduació ja no està armada a tres de les quatre portes.** La decisió 6.1
fa que el wipe preservi les regles `origen='MANUAL'` quan es pot demostrar que són autoria.

---

## 1 · N1 · EL RUN DE TALLES (additiu, `pom/0062` + `pom/0063`)

### Què s'ha afegit a `SizeSystem` (`backend/fhort/pom/models.py:556`)

| camp | tipus | nota |
|---|---|---|
| `tipus_escala` | CharField amb 4 choices: `ALPHA` · `NUM` · `MESOS` · `ALTURA` | deduït de les ETIQUETES |
| `construccions` | M2M → `ConstructionType` | la capa `targets` ja hi era des de `pom/0021` |
| `fits` | M2M → `FitType` | |
| `grups` | M2M → **`GarmentGroup`** | el vocabulari de GRUP surt de **Garment Types**, no de POM System |
| `customer` | FK nullable → `tasks.Customer`, `db_constraint=False`, `SET_NULL` | patró de `SizingProfile.customer` (`pom` és SHARED+TENANT, `tasks` és tenant-only) |

**Cap camp de graduació. Cap FK a POMs. Res que lligui capes.** El patró és el que la casa ja
feia servir per a `targets`: M2M al vocabulari + `SlugRelatedField(slug_field='codi')`. Zero
vocabularis nous (v. `DIAGNOSI_VOCABULARIS.md` §T1.2).

### L'etiqueta MANA sobre `base_unit` — i per què

`TODDLER_EU` porta `base_unit='AGE_YEARS'` i unes etiquetes que són **alçades en cm** (86-116,
pas de 6, amb `body_height_cm == etiqueta` a les 6 talles). **El camp mentia; les etiquetes
no.** L'algorisme (`pom/size_labels.py:dedueix_tipus_escala`) llegeix primer les etiquetes i
només cau a `base_unit` quan callen. `base_unit` **NO s'ha tocat**: es queda com està, i el
conflicte s'anota (`conflicte_tipus_escala`).

El desempat difícil és **NUM vs ALTURA** (tots dos numèrics purs, i es solapen en rang: 48 vs
50). El que els separa és **el pas**: l'escalat EU d'alçada infantil va de 6 en 6 sense
excepció, i el numèric EU adult de 2 en 2. Als 30 runs reals separa el 100 % dels casos.

### Resultat de la classificació (data migration idempotent, NOMÉS-OMPLE)

**27 de 30 runs classificats** (`fhort` 26/28 · `public` 14/14 · `los` 0/2), **12 FK de client
lligades** (11 LOS + 1 BRW). Els **3 que es queden BUITS** són exactament els que no tenen ni
etiquetes ni `base_unit`:

| tenant · id | codi | per què no es dedueix |
|---|---|---|
| `fhort` · 26 | `MEN-SHIRT-NUM` | 0 talles · `base_unit` buit · cap senyal |
| `los` · 1 | `ALPHA_EU_W` | 0 talles · `base_unit` buit |
| `los` · 2 | `SYS-ONLY-LOS` | 0 talles · `base_unit` buit · nom d'artefacte de test |

**No se'ls inventa cap escala.** I no és casualitat que siguin els mateixos tres que el cens
classifica com a brossa/inclassificable: *run sense talles ∧ sense `base_unit` ⇒ candidat a
brossa* és una regla de depuració que surt sola d'aquest exercici.

### Verificació de la migració

`migrate_schemas` verd als **tres schemes**. Columnes auditades **directament a la BD**
(`information_schema`, com mana `CLAUDE.md`): `tipus_escala` i `customer_id` a `public`,
`fhort` i `los`, i les 4 taules M2M (`pom_sizesystem_{targets,construccions,fits,grups}`) a
cadascun.

🔑 **Una trampa que val la pena saber:** la data migration comprovava la taula de `Customer` amb
un `try/except ProgrammingError`. **No serveix**: la consulta que peta avorta la transacció de
la migració sencera i llavors ni el `return` la salva. La comprovació ha de ser per
**introspecció** (`schema_editor.connection.introspection.table_names()`).

---

## 2 · N2 · LA SIZE LIBRARY, DEPURADA

**Fora el bloc d'increments de POM de les targetes.** La graduació ja no viu en aquesta
pantalla: aquí es tria una ESCALA, i el que la targeta ha de dir és **a qui s'assembla**, no
quant creix cada mesura.

Al seu lloc:
- **Tags de restricció** de les 4 capes, **només les informades**. Una capa buida vol dir NO
  DECLARADA, i pintar-la buida seria afirmar que el run no serveix per a res.
- **Badge de tipus d'escala** (ALPHA/NUM/MESOS/ALTURA) i **badge de client**, tots dos del RUN.
- **Filtres de capçalera** per escala i per grup, que llegeixen els mateixos vocabularis.
  Client-side pel mateix motiu que el filtre de Fit: filtrar-los al servidor trencaria el
  faceting i faria desaparèixer els altres chips. **Només surten quan hi ha més d'un valor**:
  una fila de filtres amb una sola opció no filtra res i és soroll.
- **`Estàndard/Personalitzat` es manté com estava. «Detall» i «Clonar», intactes.**

**Res estrena layout** (ordre d'Agus): tag, chip i badge són els de la casa, i les etiquetes
surten de les **mateixes claus i18n** que ja resolen aquests vocabularis a la resta del sistema
(`model_wizard.target_*` i germans) i de `groupLabel`. **Cap còpia nova de vocabulari.**

🔑 `grading_rules_preview` **NO s'ha retirat del payload**: `SizeSetDetail.jsx:101` encara el
pinta, i el brief demanava el detall intacte.

🔑 El filtre triat és **DERIVAT**, no un `setState` dins d'un efecte. El primer intent seguia el
patró que el fitxer ja tenia (reset en efecte) i **afegia un warning d'eslint** i un render en
cascada. Amb la derivació, el fitxer es queda als **4 warnings de base exactes**.

---

## 3 · N3 · EL PAS 3 DEL WIZARD

**Mateixa proximitat, mateixa llei — ORDENA, MAI AMAGA (D-31.3).** Font nova: les etiquetes que
N1 va donar al run, contra els 4 eixos del model en curs. Construcció i fit ja estan triats al
pas 2; el grup el mana l'item (arbre únic) i no es re-tria mai.

**L'ordre de les claus no és arbitrari:**

```
1r TARGET · 2n DE QUI ÉS EL RUN · 3r construcció · 4t fit · 5è grup · nom (estabilitat)
```

L'origen es queda **2n a posta** i les tres capes noves són **desempats**. El parany del model
174 és oferir el run d'un altre client com si fos teu: **un canònic que encaixa amb les tres
capes NO ha de passar davant del run del client del model.** Hi ha test que ho fixa.

**Avui cap run té les 3 capes noves informades, i per tant l'ordre que la tècnica veu NO es
mou.** El mecanisme hi és, la dada encara no. Hi ha test que fixa aquesta no-regressió — que és
la garantia que la nit no ha canviat el que ningú ha demanat que canviï.

Extret a `frontend/src/utils/proximitatRun.js` (el patró de `derivaTarget.js`) per poder-lo
provar sense muntar el wizard sencer.

⚠️ **Un TDZ evitat de poc:** `garmentGroupCodi` entrava a la llista de dependències d'un efecte
—i una llista de dependències **s'avalua durant el render**— però estava declarat 130 línies
més avall. Hauria estat un `ReferenceError` en obrir el wizard. La declaració puja, amb el
motiu escrit al costat.

---

## 4 · N4 · DECISIÓ 6.1 — EL WIPE DEIXA DE MATAR L'AUTORIA

### El defecte

`materialize_model_grading_rules` feia `model.grading_rules.all().delete()` **sense cap
filtre**, i s'enduia les `origen='MANUAL'` — el que la pantalla de Graduació escriu quan un
tècnic afina una mesura a mà. Al dump de PROD del 04/08: **660 MANUAL en 25 models**.

### La llei implementada, i per què és ESTRICTA

`origen='MANUAL'` **no sempre vol dir autoria**: `origen_mgr_des_de_ruleset` estampa MANUAL a
les residents que surten d'un `GradingRuleSet` amb `origen` NULL, i **`ModelGradingRule` no
guarda de quin joc ve cada fila** (verificat: 13 camps, cap de traçabilitat). Amb la informació
disponible al moment del wipe, la distinció només es pot fer per l'estat del **joc anterior**.

Es preserva **NOMÉS** si el joc del qual venien les residents estava **classificat**. La resta
manté el comportament d'abans i **s'ANOTA** amb un codi curt (`motiu_no_preserva`):

| motiu | què vol dir | preserva? |
|---|---|---|
| `no_informat` | el caller no ha adoptat 6.1 | ❌ (compatibilitat cap enrere) |
| `sense_joc` | el model no tenia cap joc | ❌ 🚩 **v. §7, decisió d'Agus** |
| `joc_sense_classificar` | el parany conegut | ❌ (a posta) |
| *(cap)* | joc CANONICAL / CLIENT_RUN / IMPORT | ✅ |

### El risc que la preservació obria, i com s'ha tancat

`ModelGradingRule` té `unique_together('model','pom')` i la materialització fa `bulk_create`
**sense conflict-handling**. Una MANUAL preservada sobre un POM que el joc nou també porta
hauria estat un **`IntegrityError`** — i és el **cas normal**, no el rar: el tècnic retoca el
pit del model i després li canvien el joc de catàleg. **La regla: la MANUAL preservada MANA
sobre la del joc, i la del joc no s'escriu.** Hi ha test amb el mateix `pom_id`.

### Les portes, una per una

| porta | on | estat |
|---|---|---|
| **1 · canvi de joc confirmat** (`update-step2`) | `views.py:1128` | ✅ tancada · compta, demana permís, deixa rastre |
| **2 · `copiar_de_model`** | `views.py:1699` | ✅ tancada · era **MUDA** (no compta, no demana permís, no deixa Watchpoint): ara la preservació hi val doble, i afegeix un `warning` a la resposta |
| **3 · reimport W5** (`_from_specs`) | `extraction_views.py:2737` | ✅ tancada la branca de residents |
| **3-bis · W5 amb contenidor INTOCABLE** | `extraction_views.py:2701` | 🔴 **OBERTA A POSTA** — v. sota |
| **4 · `migra_brownie_ruleset`** | el command | ✅ tancada · + fix d'idempotència |
| *(la 5a que el brief no comptava)* · **«Sense graduació»** | `views.py:1091` | 🔴 **fora de 6.1 a posta** — v. sota |

🔴 **Per què dues es queden fora, i és correcte:** `_load_grading_rules` és **all-or-nothing**
(amb UNA resident viva, el joc extern deixa de graduar tots els altres POMs). A la branca del
contenidor INTOCABLE, salvar una MANUAL **desactivaria el contenidor sencer en silenci**. I
«Sense graduació» diu literalment que el model es queda SENSE graduar: deixar-hi residents el
faria graduar igual, que és el contrari del que l'usuari ha demanat. Totes dues estan anotades
al codi, amb el motiu.

### El permís i la destrucció miren el mateix — en els dos sentits

La llei que l'Agus va posar al vespre (F1-bis) diu que no es pot destruir més del que es demana
permís. **També val al revés:** demanar permís per esborrar 4 regles que no s'esborraran és la
mateixa mentida amb el signe canviat. Per això el 409 ara resta les preservades, i **si no queda
res a destruir NO es demana res**. Claus noves i **additives** al payload i al Watchpoint
(`preservades`, `esborrades`, `residents_preservades`): el front que no les conegui segueix
llegint `residents` i `per_origen` com sempre → **zero canvis de frontend, zero i18n**.

### El fix d'idempotència que la preservació exigia

`cal_materialitzar` (`migra_brownie_ruleset.py:84`) comparava **conjunts iguals** de POMs, i el
seu docstring citava literalment la invariant «el set resultant és EXACTAMENT source_rules».
Amb una MANUAL preservada que el joc no porta, la comanda hauria trobat feina a fer **a cada
passada, per sempre** — i la seva capçalera promet ser idempotent. La pregunta correcta és
**«FALTA cap POM del joc?»**. Hi ha test.

### Tres rastres que la preservació hauria fet mentir, i que s'han corregit

La preservació trenca una equivalència que fins ara era invisible perquè les dues xifres eren
sempre la mateixa: **«quantes residents hi havia» ≠ «quantes n'han caigut»**. Tres llocs ho
donaven per fet:

1. **El Watchpoint es creava `if n_residents:`** — o sigui, encara que no s'hagués destruït res.
   Un Watchpoint existeix per respondre *«on han anat les meves regles»*; si no n'ha anat cap
   enlloc, no hi ha res a respondre. Ara la condició mira les **esborrades**.
2. **El log de «0 materialitzades»** deia *«el model queda SENSE regles residents»*. Amb 6.1,
   «0 materialitzades» pot voler dir exactament el contrari: que **totes** les del joc queien
   sobre POMs que el tècnic havia escrit a mà, i que per tant hi manen. El text ara distingeix
   els dos casos. (Ho va destapar la sortida del test del `IntegrityError`.)
3. **El dry-run del command** imprimia el recompte del validador sense les preservades. Aquesta
   comanda es llegeix **per decidir**: un preview que infla el que es perdrà és tan dolent com
   un que ho amaga.

### Els 2 tests que s'han REESCRIT (i per què no és un accident)

`test_canviar_de_joc_amb_MANUAL_vives_avisa_amb_recompte` i
`test_canvi_de_joc_confirmat_esborra_i_deixa_watchpoint` fixaven que la MANUAL **moria**. Això
és exactament el que 6.1 canvia, i el brief ho demanava («canvi de joc amb MANUAL autèntica →
sobreviu»). Els dos jocs d'aquella classe porten `origen=CLIENT_RUN` explícit, o sigui que hi
són **el cas net**. Els 5 tests de `EsborratResidentsD314Test` **no s'han tocat**: el seu model
no té joc anterior (`sense_joc`) i, amb la lectura estricta, es comporten exactament com abans.

---

## 5 · N5 · PATRÓ A — l'entregable de demà

A [`DIAGNOSI_VOCABULARIS.md`](DIAGNOSI_VOCABULARIS.md), amb T1 (fonts dels 4 vocabularis), T2
(POM System desvinculat: com està lligat, què vol dir soltar-lo, cost per lector, pla per
passos) i T3 (cens de la biblioteca).

🛑 **Cap pas de T2 s'ha executat.** Per ordre expressa, la desvinculació de POM System és
NOMÉS Patró A aquesta nit.

**El titular de T2:** «POM System» **no és un model** — no existeix cap classe `POMSystem`, cap
camp, cap taula. És el rètol d'una pantalla, i la cosa real a sota és `GarmentPOMMap` per
`GarmentTypeItem`, que **no té cap FK a `GarmentGroup`, ni a `SizeSystem`, ni a
`SizeDefinition`**. **El model ja està desenganxat; el que està enganxat és l'edifici.**

---

## 6 · N6 · ELS VERDS

| control | resultat |
|---|---|
| `python manage.py check` | **net** (0 silenced) |
| `migrate_schemas` | **verd als 3 schemes** · columnes auditades a `information_schema` |
| `fhort.models_app.tests_sembra_grading` **+ els 3 consumidors veïns** de `materialize_*` (`test_copia_model_a_model`, `test_g1_graduacio`, `test_set1_creacio`) **+ `pom.test_n1_tipus_escala`** | **132/132 OK** · dels quals `tests_sembra_grading` **94/94** (12 nous + 2 reescrits) |
| `node --test` (frontend) | **218/218** (14 nous) |
| `npm run build` | **net** |
| `eslint` (fitxers tocats) | **0 errors** · warnings = **el baseline exacte** de cada fitxer |
| paritat i18n ca/en/es | **verda** (6 claus noves × 3) |
| **fum propi read-only** `ops/qa/qa_n_capes_run.py` | **VERD, cap escriptura** |

### El fum de la nit

Els fums de navegador **no es poden córrer**: `fhort` té **0 models** des de V4, i els de cicle
(`qa_w2_cicle_model.py`) a més **creen i destrueixen** un model — i aquesta nit no es destrueix
res, ni el que un mateix ha creat. En comptes d'això, `ops/qa/qa_n_capes_run.py` verifica N1-N3
**sense escriure ni una fila**: el model de dades, el contracte de l'API (incloent-hi els
filtres nous) i **la funció d'ordre del pas 3 contra els runs REALS**, amb un mirall Python de
`proximitatRun.js` — si el JS i el fum divergeixen, un dels dos menteix.

Sortida real:

```
N1a · 28 runs · classificats 27 · sense classificar 1 ['MEN-SHIRT-NUM']
N1b · GET size-systems/ 200 · 28 files · capes exposades OK
N1b · filtre tipus_escala=ALPHA → 8 runs, tots ALPHA
N1b · filtre tipus_escala=ALTURA → 3 runs, tots ALTURA
N2 · GET sizing-profiles/?target=WOMAN 200 · 11 perfils · el run hi porta les seves capes
N3 · ordre amb client BRW · target WOMAN: WOMAN_BRW_01 › ALPHA_EU_W › NUMERIC_EU_W › ALPHA_EU_M › BABY_EU_CM
N3 · ordre sense client       · target WOMAN: ALPHA_EU_W › NUMERIC_EU_W › WOMAN_BRW_01 › ALPHA_EU_M › BABY_EU_CM
  🟡 ANOTAT · TODDLER_EU: base_unit=AGE_YEARS contradiu les etiquetes (tipus_escala=ALTURA)
✅ FUM VERD · cap escriptura feta
```

### Re-lectura del propi diff (capes que hagin quedat lligades sense voler)

- ✅ `SizeSystem` no guanya **cap** camp de graduació ni **cap** FK a POMs. Les 4 capes són M2M
  a vocabularis i prou.
- ✅ El pas 3 segueix llistant **`SizeSystem` purs** (`sizeSystems.list`), no perfils: N3 canvia
  l'ORDRE, no la font.
- ✅ N4 no toca el motor de graduació (`generate_graded_specs`, `_load_grading_rules`): canvia
  **què s'esborra**, no com es gradua.
- 🟡 **Un acoblament nou que s'anota i no es resol:** `SizeSystem` té ara **dos eixos de
  client**, `customer_codi` (CharField(3), el heretat, que és el que el wizard i el
  `sizing_profiles_view` llegeixen) i `customer` (FK, nou). La FK s'ha **backfillat** des del
  codi i el codi **no s'ha tocat**. Convergir-los és feina d'un altre dia; fer-ho aquesta nit
  hauria estat tocar el camí crític del wizard sense necessitat.
- 🟡 El fum té un **mirall** de `proximitatRun.js` en Python. És duplicació deliberada (serveix
  de contrast creuat), però és duplicació: si l'ordre canvia, s'han de tocar els dos.

---

## 7 · EL QUE ESPERA DECISIÓ D'AGUS

### 7.1 · Cens de depuració de la biblioteca de talles — **cap esborrat fet**

Detall complet a [`DIAGNOSI_VOCABULARIS.md`](DIAGNOSI_VOCABULARIS.md) §T3. El resum:

**Esborrables sense discussió (risc zero):** `fhort`·26 `MEN-SHIRT-NUM` i `fhort`·6
`TGIRL-EU-HEIGHT`. Són **els únics dos de `fhort` que no existeixen a `public`** (el
discriminador dur és la pertinença al catàleg de la casa, no el nom) i **tots dos tenen les 6
FKs entrants a zero**: cap perfil, cap ruleset, cap baseset, cap model. **Cap `SizingProfile`
apunta a cap dels dos.**

**No tocar (22):** els 12 canònics —**inclosos els 4 «buits»** (31, 33, 39, 40), que no són
brossa sinó places reservades del catàleg `public`— i els 10 runs de client LOS amb ús real.

**6 que necessiten la teva paraula:**

| # | run | la pregunta |
|---|---|---|
| **D1** | `fhort`·50 `GIRL_LOS_03` | Duplicat funcional de `GIRL_LOS_01` (48): mateixes 9 etiquetes, mateix target, mateix client. Però té ús propi (G104 + P521). **Fusionar 50→48 o mantenir-ne dos?** El forat d'id 49 diu que un `GIRL_LOS_02` ja es va esborrar sense deixar rastre. |
| **D2** | `fhort`·53 `WOMAN_BRW_01` | És el «BRW Run 01». Client real, 5 talles vàlides, **0 SizingProfile**, i el seu únic ús és un ruleset que es diu **«Prova BRW ALPHA UE»**. Mentrestant el grading BRW de debò (G115, G219) penja del canònic 29. **És el run real de Brownie o la resta d'un experiment?** |
| **D3** | `fhort`·36 `TODDLER_EU` | **Tres defectes alhora**: `base_unit='AGE_YEARS'` amb etiquetes en cm · `ordre` trencat (86 i 92 tots dos amb `ordre=1` → el run es llegeix desordenat) · la talla 116 amb `waist=34/hip=40`, físicament impossible. **Reparar, no esborrar** (és del catàleg `public`). |
| **D4** | `fhort`·34 `BABY_MONTHS` | **Dos runs barrejats en un** (joc puntual + joc de rangs) amb 5 parells d'`ordre` duplicats i `age_months_*` desplaçats (`24M` → 96-144 mesos). El joc de rangs duplica exactament `BABY_MONTHS_COM` (42), que sí que s'usa. 0 usos, però existeix a `public.6`. |
| **D5** | `los`·1 `ALPHA_EU_W` | **0 talles i 20 Models penjats.** Aquests 20 models **no poden graduar**. **Són reals o fixtures?** No esborris el run sol. |
| **D6** | `los`·2 `SYS-ONLY-LOS` | Nom d'artefacte de test, apareix com a fixture a `VERIFICACIO_BOOTSTRAP_DESTI_POBLAT.md:128`. 0 talles, **10 Models**. Esborrat en bloc o res. |

⚠️ **Els ids NO són els mateixos entre schemes.** `ALPHA_EU_W` és **29** a `fhort`, **1** a
`public` i **1** a `los`. Qualsevol creuament ha d'anar **per `codi`**.

### 7.2 · La política fina de les MANUAL — els dos casos que 6.1 deixa oberts

**El primer és el que més models toca.** `motiu_no_preserva == 'sense_joc'`: un model **sense
cap joc** amb regles MANUAL. Aquestes **probablement SÍ que són autoria** —sense joc no hi ha
joc-sense-classificar del qual puguin sortir, i «Sense graduació» ja esborra TOTES les
residents, o sigui que el que hi hagi després s'ha escrit a mà. **Jo no ho he eixamplat perquè
és política, no deducció**, i el brief deia «NOMÉS si el joc d'origen està classificat».
👉 **La pregunta:** *volem que un model sense joc també conservi les seves MANUAL en assignar-li
un joc per primera vegada?* Si sí, és **una línia** a `motiu_no_preserva`.

**El segon és el parany conegut.** `motiu_no_preserva == 'joc_sense_classificar'`. La sortida
neta no és tocar el filtre: és **córrer `manage.py set_grading_origen`** (el backfill que
`pom/models.py:1088-1091` ja declara com a decisió humana) perquè deixin d'existir jocs sense
classificar. Llavors aquest cas s'extingeix sol.

**I un tercer, que no és política sinó traçabilitat.** L'arrel de tot plegat és que
`ModelGradingRule` **no guarda de quin joc ve cada fila**. Un camp `derivat_de_rule_set`
(nullable, additiu) faria que la pregunta «això és autoria?» deixés de ser una inferència.
💡 *(a validar)* — no s'ha fet: és disseny de domini.

### 7.3 · La implementació de la desvinculació de POM System

Les tres decisions, a `DIAGNOSI_VOCABULARIS.md` §2.6:
1. **Qui és l'amo del vocabulari de grup, la BD o el codi?** (en depèn tota la resta)
2. **Es parteix l'app `fhort.pom`?** (recordar que és l'**única** app SHARED+TENANT)
3. **`GarmentType.grup` passa de string a FK?** (l'únic pas destructiu de veritat)

### 7.4 · El deute que el cens ha destapat (disseny, no depuració)

1. `parent`/`derived_systems` de `SizeSystem` és **codi mort en dades**: NULL a les 30 files, 0
   derivats. **Mai s'ha estrenat.** O s'usa o es jubila.
2. `SizingProfile` **no té `unique_together`**: sense clau natural, la proliferació no té fre.
3. `base_unit` **no està validat** contra les etiquetes. N1 hi ha posat l'algorisme
   (`conflicte_tipus_escala`); **falta el check al `save()`/serializer**.
4. `SizeDefinition.ordre` **no és únic per `size_system`**: dos runs es llegeixen desordenats, i
   **un run desordenat és un grading incorrecte**.
5. **7 runs de 30 no tenen cap `SizeDefinition`**, i dos d'ells tenen **30 Models a sobre**.

---

## 8 · SORPRESES

1. 🔴 **La llista de 4 portes del brief era incompleta: n'hi ha 6 crides a `materialize_*` i 2
   deletes crus independents.** Les dues que el brief no comptava són `views.py:1091`
   («Sense graduació», que no passa per `materialize_*` — un fix aplicat només a `services.py`
   no l'hauria cobert **mai**) i `extraction_views.py:2701` (W5 amb contenidor INTOCABLE).
   Les dues creacions (`create_model_wizard`, peça única i multi-peça) també hi criden, però són
   inofensives: el model acaba de néixer.

2. 🔴 **La preservació hauria petat amb `IntegrityError` al cas NORMAL, no al rar.**
   `unique_together('model','pom')` + `bulk_create` sense conflict-handling. El cas és: el
   tècnic edita el pit del model (`set_pom_regim_view` fa UPSERT i estampa MANUAL sobre la
   regla que **ja venia del joc**) i després li canvien el joc de catàleg. Sense el salt de
   POMs, la decisió 6.1 hauria trencat producció el primer dia.

3. 🔴 **`origen='MANUAL'` tampoc garanteix que el CONTINGUT sigui autoria.** Els dos escriptors
   (`views.py:4779` i `:2319`) estampen MANUAL **encara que la regla sigui una còpia literal de
   la del joc**: n'hi ha prou que algú hagi passat per la pantalla i hagi desat. O sigui que el
   camp diu «algú hi ha tocat», no «aquest valor és seu».

4. 🟡 **`cal_materialitzar` citava la invariant al seu docstring.** Un docstring que cita una
   garantia d'un altre mòdul és una dependència real, i quan la garantia canvia, la comanda
   deixa de ser idempotent en silenci. La va salvar que el docstring la citava **literalment**
   i es podia buscar.

5. 🟡 **Un `try/except ProgrammingError` dins d'una data migration no protegeix de res.** La
   consulta que peta avorta la transacció sencera; el `return` del `except` ja arriba tard i el
   `migrate_schemas` mor amb `InFailedSqlTransaction`. Cal **introspecció**, no excepcions.

6. 🟡 **`FitType.CODI_CHOICES` és codi mort desactualitzat.** Declara 5 codis i inclou `LOOSE`,
   que **no existeix a cap BD**; la BD en té 10. **Un `full_clean()` sobre un `FitType` real
   petaria.** La constant JS coincideix amb la BD, no amb els choices.

7. 🟡 **`NEWBORN` té 162 POM Systems vius i el frontend no el coneix**: es pinta amb el nom cru
   de BD i **l'últim de la fila de pills**, perquè `gradingAxes.js:49-57` només en té 7 dels 12.
   La factura de tenir dues fonts de veritat ja s'està pagant, i es veu a pantalla.

8. 🟡 **`POMCategory` a `fhort` està bruta**: 28 files per a ~15 conceptes, amb duplicats del
   tipus `codi='CAT-UB'` i `codi='Upper body'` per a la mateixa cosa.

9. 🟡 **Hi havia dues corregudes de tests concurrents d'una altra sessió** (`fhort.models_app` a
   les 19:26 i `fhort.tasks fhort.fitting` després). No s'ha tocat la seva test-DB: la nit ha
   corregut sobre una de pròpia (`test_n4_nit_capes`, via un `settings` del scratchpad que
   **només** canvia el nom de la test-DB). `DECISIONS.md` té 1.130 línies sense commitar d'una
   altra sessió: **no s'ha tocat** (i CLAUDE.md diu que no es commita mai).

11. 🔴 **HI HA DOS COMMITS NUMERATS «86».** Mentre corria aquesta nit, l'altra sessió va commitar
    `8dd6d9f3` («86 · el segell del tram V») **entre** el meu 85 i el meu 86 (`f8dd7eb7`). El
    numerador de commits és un comptador compartit i no hi ha manera de coordinar-lo entre
    sessions concurrents. **No he renumerat res**: reescriure història d'una branca on hi
    treballa algú altre costa més del que val un número. El seu commit toca **només**
    `REPORT_VESPRE_FORATS.md` — **zero codi** —, o sigui que els verds d'aquesta nit no en
    depenen. Si l'Agus vol la sèrie neta, la manera barata és renumerar en fred demà.

12. 🟢 **I una confirmació independent que va caure sola.** Aquell segell del tram V va córrer
    les suites senceres (**1.100 verds**, `fhort.pom` 218 inclòs) sobre un disc que **ja portava
    N1-N3**, i el seu propi missatge ho diu: *«Django prova el DISC, no el HEAD»*. O sigui que
    N1 i N3 tenen, a més dels seus tests, una passada d'app sencera feta per una altra mà. El
    que aquella passada **no** cobreix és N4: és de les 20:39 i N4 es va escriure després.

13. 🟡 **Un `until ! pgrep -f "settings_n4"` per esperar-se es bloqueja a si mateix**: la pròpia
    línia de comanda del bucle conté `settings_n4` i, per tant, `pgrep` sempre s'hi troba. Dos
    esperadors encadenats es van quedar penjats mirant-se. No té conseqüències al repo, però és
    una trampa que val la pena no repetir.

10. 🟢 **El `--keepdb` de la nit deixa `test_n4_nit_capes` viva.** No s'ha esborrat perquè el
    règim diu que no s'esborra res; si molesta, cau amb un `DROP DATABASE`.

---

## 9 · LES VETES, UNA PER UNA

| veta | complerta? |
|---|---|
| CAP esborrat de dades (runs, presets, perfils, res) | ✅ **cap `DELETE`, cap `UPDATE` sobre dades existents**. El cens és proposta; la data migration NOMÉS OMPLE camps buits nous. |
| CAP migració destructiva — només additives | ✅ `pom/0062` afegeix 5 camps · `pom/0063` és `RunPython` que només omple. Cap camp existent tocat (`base_unit` i `customer_codi` intactes, encara que menteixin). |
| CAP canvi al GTI ni a les seves propostes | ✅ `GarmentTypeItem` i `proposta_promocio` no s'han tocat. |
| La desvinculació de POM System: NOMÉS Patró A | ✅ zero línies implementades; tot a `DIAGNOSI_VOCABULARIS.md` §T2. |
| Cap push | ✅ 4 commits locals, cap push. |
| Restart per bloc backend | ✅ v. §10. |

---

## 10 · PER A DEMÀ AL MATÍ

1. **`systemctl restart ftt-staging`** després de fer el `git pull` — el backend **no es
   desplega sol**: el gunicorn serveix el codi de quan va arrencar. (Si un endpoint nou dona 404
   amb el codi correcte al disc, és això.)
   ✅ **Ja fet aquesta nit**, i verificat amb el test dels 5 segons: sense credencial,
   `/api/v1/size-systems/?tipus_escala=ALPHA` i `/api/v1/sizing-profiles/?target=WOMAN` tornen
   **401** (ruta viva) i una ruta inventada torna **404** (el control). El procés desplegat té
   el codi nou.
2. El **frontend ja està construït** (`frontend/dist`): a staging, construir ÉS desplegar.
3. Res a instal·lar: **cap dependència nova**.
4. Si vols desfer N4 sense tocar res més: `joc_anterior` té valor per defecte, o sigui que
   **treure'l dels 4 callers restaura el comportament exacte d'abans** sense tocar el servei.
