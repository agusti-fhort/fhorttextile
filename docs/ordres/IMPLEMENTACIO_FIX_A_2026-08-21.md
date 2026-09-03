# IMPLEMENTACIÓ · FIX A — UNA SOLA FONT DE VERITAT PER A LA REGLA

**Data:** 2026-08-21 · **Entorn:** staging `178.105.48.204`, `/var/www/ftt-staging`, branca `dev`
**Base:** `506716b1` (post bloc 3+D) → **HEAD `cc3c4204`** · **11 commits, cap push**
**Substrat:** `DIAGNOSI_PRE_SPRINTS_STAGING_2026-08-21.md` §1 · `DIAGNOSI_BUGS_PROD_837` §A
**Banc:** model **1383** (`TRV-SS27-0001`) · gate: `ops/qa/banc_paritat_1383.py`

---

## RESUM EN SET LÍNIES

1. El camp `increment` era una **segona veritat oculta**: el poblava la materialització des del
   joc i cap superfície d'edició no el tocava mai, o sigui que es **fossilitzava**.
2. El motor hi queia quan `increment_base` era NULL — i **hi queia des de DOS nodes**, no un.
3. **PAS 0:** el banc s'estén al segon camí (presa/ancoratges) i a una sonda de coherència.
   Sense això el fix podia fer divergir Escalat de la presa en silenci, amb el gate en verd.
4. **PAS 1:** les 4 portes que escrivien només el llegat passen als camps bons. Una d'elles
   —el clon de perfil— **perdia el break sencer**: bug propi, anterior al fix.
5. **PAS 2:** backfill amb guarda S44. 14 files a staging, totes del 1383, totes manuals.
6. **PAS 3:** els dos fallbacks fora **al mateix commit**. Regla incompleta = **cel·la absent**.
7. **PAS 4-5:** les superfícies que quedaven, i **la presa declara de quina graduació ve**.

🚨 **I la suite va sortir VERMELLA la primera vegada** (`1537 tests · 10 failures · 21 errors`).
No era soroll: hi havia **dos camins vius d'escriptura** que el cens del PAS 4 no podia veure
perquè buscava LECTORS. V. §PAS 1b — és el retorn més car d'aquest sprint.

**Verd:** banc `A=✔(105) B=✔(525) C=✔(4)` · `manage.py check` net · `npm run build` ✓ ·
`eslint` 0 errors · tests nous 38/38 · suite de regressió (v. §QA).

---

## COMMITS

| # | Hash | Peça |
|---|---|---|
| 0 | `c55815e6` | `test(grading)` · el banc cobreix els DOS camins del motor, no un |
| 1 | `95fc1e0d` | `fix(grading)` · les quatre portes que escrivien el camp que el motor no llegeix |
| 2 | `41edfe55` | `feat(grading)` · backfill del camp llegat, amb la guarda al davant (S44) |
| 3 | `cf7f6512` | `fix(grading)` · els DOS fallbacks al camp llegat, retirats al mateix commit |
| 4 | `048750fd` | `fix(grading)` · les superfícies que encara llegien el camp mort |
| 5 | `05ea6627` | `feat(escalat)` · la presa diu de quina graduació ve, i avisa quan no és la vigent |
| **4b** | `56ddeef9` | `fix(grading)` · **el MIRALL del guard, que el PAS 3 acabava de deixar mentint** |
| **4c** | `812ce193` | `fix(grading)` · al CSV, una FIXED no és una regla trencada |
| **1b** | `9c4f2541` | `fix(grading)` · 🚨 **les DUES aixetes que el cens de lectors no podia veure** |
| **1c** | `cc3c4204` | `test(grading)` · les fixtures que construïen la regla amb el camp mort |

```
21 fitxers · +1600 / −70
```

> **Quatre dels onze commits no eren al brief** (4b · 4c · 1b · 1c). Tres van sortir de mesurar
> —el cens final, el CSV contra el catàleg viu, i **la suite**— i un és la conseqüència
> necessària de l'anterior. Es reporten com el que són: **forats oberts pel propi fix**, no
> peces planificades.

> ### ⓘ SESSIÓ CONCURRENT — els commits van INTERCALATS
>
> Entre el `812ce193` (PAS 4c) i el `9c4f2541` (PAS 1b) hi ha **15 commits d'una altra sessió**
> (trams H-bis, J i J-bis). `git log 506716b1..HEAD` els mostra barrejats amb els d'aquest sprint.
>
> **Cap solapament de codi**: l'única intersecció de fitxers són els tres `i18n/*.json`, i les
> claus són disjuntes (verificat: `escalat` 15 claus amb paritat ca/en/es, les 4 del PAS 5 hi
> són, i `size_library.col_break` també). El `git commit <paths>` selectiu ha fet la seva feina.
>
> ⚠️ **Però la suite de regressió mesura els DOS sprints.** Si el resultat final porta vermells,
> l'atribució no és automàtica: cal mirar quin fitxer toca cadascun abans de dir de qui és.

---

## PAS 0 · EL GATE, ABANS DE TOCAR RES

`ops/qa/banc_paritat_1383.py` — read-only, `PGOPTIONS=-c default_transaction_read_only=on`,
exit 0 només amb els tres blocs verds **i** el hash del joc intacte.

**Per què tres blocs i no un.** El banc del 21/08 mesurava `GradedSpec` i prou. El fallback al
llegat vivia a **dos** nodes:

```
① pom/services.py       `_apply_rule`, branca LINEAR      → Escalat (GradedSpec)
② pom/grading_utils.py  `increment_de_l_aresta`           → `propaga_ancoratges`, i d'aquí
                                                            la PRESA i la derivació de base
```

② **no té el guard `increment_base is not None` a sobre** — el decideix el cridador. Un banc
que només mesurés ① hauria donat VERD amb Escalat i la presa dient coses diferents sobre la
mateixa regla.

| Bloc | Què mesura | Mida |
|---|---|---|
| **A** · GradedSpec | recàlcul en memòria contra la versió vigent | 105 cel·les |
| **B** · presa/ancoratges | `propaga_ancoratges` ancorada a **CADA** talla del run ha de reproduir la corba del motor (llei FIX-1). Predicat de propagació = mirall exacte de `fitting/views.py:705-707` | **525** comprovacions |
| **C** · coherència | sonda **pura** (cap BD) sobre LINEAR amb `increment_base` NULL. **No exigeix cap valor**: exigeix que ① i ② diguin el MATEIX, abans i després del fix | 4 casos |

> ⚠️ El banc és un **ESPILL** del bucle de `generate_graded_specs`, no una crida. Si aquell bucle
> canvia de forma, el banc s'ha de moure amb ell — **i que ho canti és la seva feina**.

---

## PAS 1 · ELS QUATRE ESCRIPTORS NOMÉS-LLEGAT

El motor gradua per `increment_base`. Quatre portes vives escrivien **només `increment`**:
desaven, tornaven 200 OK, ensenyaven el número nou, i **la corba no es movia**.

| # | Porta | Àncora | Què passava de debò |
|---|---|---|---|
| ① | `update_grading_rule_with_history_view` | `pom/s4_views.py:96-140` | A més de no moure res, **escrivia historial d'aquell no-canvi**: `valor_anterior`/`valor_nou` sortien del llegat, o sigui que la fila deia «1.50 → 4.50» sobre una graduació que seguia a 2.00 |
| ② | `update_grading_rule_view` | `pom/s2_views.py:364-395` | la germana sense historial |
| ③ | `restore_version_view` | `pom/s4_views.py:322-348` | **«Perfil restaurat a l'estàndard» era literalment fals.** El `!=` només mirava `increment`+`logica`: una regla amb el BREAK canviat es declarava IGUAL i no es restaurava mai; i quan sí que es restaurava, el break del client hi quedava — ni l'estàndard ni el que hi havia |
| ④ | `clone_sizing_profile_view` | `pom/s2_views.py:225-268` | 🚨 **bug propi.** El comentari deia «tots els camps reals» i en copiava SIS de deu |

> ### 🚨 CORRECCIÓ AL MEU PROPI CENS — cap de les quatre té pantalla viva
>
> La diagnosi pre-sprints (§1.5, bloc C) deia que ① era «**SÍ** · la crida `SizeSetDetail.jsx:63`».
> És cert com a codi i **fals com a camí d'usuari**: `SizeSetDetail.jsx` **no el munta ningú**.
> `SizeLibrary.jsx:8-18` el va desmuntar i deixa escrit que el component es queda al disc «sense
> cap consumidor». Verificat avui: zero imports i zero `<SizeSetDetail>` a tot `src/`.
>
> | Porta | Ruta d'API | Pantalla que la crida |
> |---|---|---|
> | ① `…/regles/<pom>/editar/` | **viva** (`tasks/urls.py:196`) | `SizeSetDetail.jsx:66` — **desmuntada** |
> | ② `…/regles/<pom>/` | **viva** (`tasks/urls.py:176`) | **cap** |
> | ③ `…/restaurar/` | **viva** | `SizeSetDetail.jsx:92` — **desmuntada** |
> | ④ `…/clonar/` | **viva** (`endpoints.js:355`) | **cap** |
>
> **Què vol dir i què no.** No vol dir que el fix sobri: són endpoints **routats i abastables**
> per API, i el bug del clon (④) corromp dades cada cop que s'usi. Sí que vol dir que **cap
> usuari hi estava caient avui**, i que la urgència era menor del que el cens deia. Ho corregeixo
> aquí perquè el cens del qual va sortir aquest sprint el vaig escriure jo aquest matí, i un
> cens que exagera la temperatura és tan mal cens com el que la rebaixa.
>
> Conseqüència pràctica: **no hi ha captura visual del PAS 1 ni del PAS 4b/`SizeSetDetail`** —
> la pantalla no és abastable. La cobertura és de test (38 proves), no de captura.

### ④ — el clon perdia el break, i ningú ho podia veure

Hi faltaven `increment_base`, `increment_break`, `talla_break_label`, `talla_break_pos` i
`talla_base_label`. Un joc amb break clonat sortia amb el break **esborrat** i el `increment`
llegat intacte per fer-ho semblar bo: **el clon graduava PLA on l'original tenia relleu**. Res
petava, res avisava — la corba simplement era una altra.

Els camps s'enumeren un a un a posta (no `pk=None; save()`): un camp nou al model ha
d'aparèixer aquí i **fer-se veure**, no colar-se per una còpia màgica que ningú revisa.

### El forat que s'obria amb el fix, tancat al mateix commit

Ara que ① i ② mouen la graduació de debò, també poden fabricar la mentida que **A3** va tancar
a les altres portes: una LINEAR amb delta 0 i sense trencament que es presenta com a graduada i
no gradua. Totes dues passen pel **mateix** `es_linear_degenerada` (punt únic de
`grading_regime.py`) i rebutgen amb **400 `LINEAR_INCREMENT_ZERO`**. I un `increment` no numèric
és 400, no el 500 de l'`except Exception` de sota.

### El mirall transitori

`rule.increment = <el mateix valor>` es manté a ① i ②, **marcat com a transitori**: fa que
`increment == increment_base` sigui cert durant la finestra fins al PAS 3, i és el que fa que la
**guarda del backfill sigui exacta**.

### El fixture del test no s'inventa

`fhort/pom/test_fix_a_p1_escriptors_llegat.py` (16 proves) transcriu les regles **A · C · D ·
BF · ZST del 1383** amb la seva incoherència viva (`increment` orfe que no casa amb
`increment_base`) — que és exactament el que aquestes portes havien de saber tractar. **Un
fixture net els hauria passat sense veure res.** La prova que compta és
`test_el_clon_gradua_IGUAL_que_l_original`: mesura amb el motor de veritat, cel·la a cel·la, no
comparant camps.

---

## PAS 1b · 🚨 LES DUES AIXETES QUE EL CENS DE LECTORS NO PODIA VEURE

**Trobades per la suite, no pel cens.** El cens del PAS 4 buscava **qui llegeix** el camp llegat.
Aquestes dues no llegeixen: **escriuen**.

| Camí | Àncora | Què hi feia |
|---|---|---|
| `reseed_tenant_fhort` | `pom/management/commands/reseed_tenant_fhort.py:398` | `bulk_create` amb `increment` i **`increment_base` a NULL** |
| `seed_baby_months_grading` | `pom/management/commands/seed_baby_months_grading.py:99` | `update_or_create` igual |

Mentre el motor queia al llegat, les regles que en sortien graduaven uniforme i ningú ho notava.
Des del PAS 3 no hi ha fallback: **córrer qualsevol dels dos hauria sembrat regles que no
gradúen** —cel·la absent per llei D2— fins que algú corregués `backfill_grading_break`. Un seed
que deixa el tenant amb la graduació muda és pitjor que un seed que peta.

El delta passa al camp que mana. **Cap corba es mou**: el valor és el mateix, només canvia el
camp on el motor el busca.

⚠️ **Al reseed, el break `above_xl` NO es deriva aquí, i és deliberat.** La forma ISO
(`valors_step={'above_xl': …}`) la resol la branca (b) de `backfill_grading_break`, que necessita
el run del ruleset per saber quina talla és «la de sobre de XL», i aquest bucle no el té a mà.
Copiar-hi el delta base sol reprodueix **exactament** la corba que el fallback llegat produïa
(uniforme, sense relleu). El segon pas del backfill segueix sent qui hi afegeix el relleu.

### El cens que s'havia d'haver fet abans: ESCRIPTORS, no lectors

Els **15** punts que CREEN una regla, verificats un a un:

```
✅ models_app/services.py ×3     ✅ models_app/views.py ×2      ✅ pom/s2_views.py
✅ pom/size_map_views.py         ✅ pom/grading_utils.py        ✅ tenants/federation_service.py
✅ sembra_model_837              ✅ seed_brownie_ruleset        ✅ seed_losan_grading_v3
✅ sembra_cataleg_v4 (**forma)   ✅ reseed_tenant_fhort ←nou    ✅ seed_baby_months ←nou
```

`sembra_cataleg_v4` i `seed_brownie_ruleset` deixen `increment_base` a `None` per a les **FIXED
a posta**, i està documentat allà: el motor entra a la branca canònica quan `increment_base` no
és None, i per a una mesura que no gradua es vol la branca FIXED.

> 🔑 **LLIÇÓ: un cens de LECTORS no tanca un camp; en fa falta un d'ESCRIPTORS.** Retirar un
> fallback no és una operació de lectura. El cens del matí (§1.5-1.6 de la diagnosi) tenia les
> dues meitats i jo només vaig tornar a passar la de lectura.

---

## PAS 1c · LES FIXTURES

29 dels 31 vermells eren fixtures que feien la LINEAR amb el camp llegat. **Dues categories, i
no es tracten igual:**

**① 26 proves** on `increment=` era només *una manera còmoda de fer una LINEAR* — el subjecte és
germanes de capa/instància, peces, herència mare↔filla, transacció de propagació, cadena
d'import. Fixture al camp que mana, **cap asserció tocada**: si alguna hagués canviat de valor,
el canvi no seria de fixture i caldria parar.

Una excepció, i és una asserció: `test_la_font_serveix_les_dues_lleis_alhora` comparava
`.increment` per saber **quina** regla tornava `_regla_de`. El delta hi és de discriminador, no
de subjecte; passa a `increment_base` perquè el llegat, amb la fixture nova, val el default del
model (`0.00`) i deixaria de distingir res.

**② 3 proves de `test_espai_de_sistema`** que assertaven **el règim llegat mateix**. Aquestes no
es canvien de fixture i prou: la geometria que protegien —**el SIGNE i la DISTÀNCIA en espai de
sistema (llei S24b)**— ja tenia bessona canònica al mateix fitxer. El règim retirat passa a tenir
prova **pròpia** (`ReglaIncompletaTest`): que no gradua, que ho diu amb un avís que nomena el
camp, i que amb delta base el llegat no mou ni una xifra — el control que garanteix que el
backfill del PAS 2 no podia canviar cap cel·la.

### 🚨 El test que no va petar, i hauria d'haver-ho fet

`test_linear_identic` **va passar** amb el fix. Comparava dues taules i **totes dues van passar a
estar plenes de `None` alhora**. Un test d'IGUALTAT no veu una RETIRADA — el mateix mode de
fallada que el golden que mesurava models inexistents i donava un md5 perfectament estable
(`README_BANC_PARITAT.md`). Ara compara **i** exigeix que hi hagi xifres. Igual per a
`test_step_identic`.

---

## PAS 2 · BACKFILL (mètode S44)

`backend/fhort/pom/management/commands/backfill_increment_llegat.py`

```bash
venv/bin/python manage.py backfill_increment_llegat --tots                    # dry-run
venv/bin/python manage.py backfill_increment_llegat --tots --esperades 14 --apply
```

**`--apply` EXIGEIX `--esperades <N>`** i s'atura sense escriure si no quadra. La xifra no es
dedueix mai: es passa. I després d'escriure **es RE-MESURA** — la idempotència es demostra, no
es promet.

### El que s'ha mogut a staging (OK d'Agus, dry-run llistat fila a fila abans)

```
fhort   14 files — TOTES del model 1383, TOTES origen=MANUAL
los      0 files — auditat igualment (aquest schema no té cap ModelGradingRule)
catàleg  0 files — les 98 GradingRule LINEAR de `fhort` ja quadraven
```

| POM | llegat → canònic | | POM | llegat → canònic |
|---|---|---|---|---|
| `F` | 1.00 → 0.00 | | `I` | 0.70 → 0.00 |
| `E1` | 0.25 → 0.00 | | `J` | 0.60 → 0.30 |
| `EK` | 0.50 → 0.00 | | `J1` | 0.30 → 0.25 |
| `EK1` | 0.25 → 0.00 | | `E7` | 0.15 → 0.00 |
| `E` | 1.00 → 0.00 | | `C` | 1.50 → 2.00 |
| `SF` | 0.70 → 0.00 | | **`D`** | **2.00 → 0.50** ← «la mina» de §A |
| `S` | 0.70 → 0.00 | | `S2` | 0.70 → 0.00 |

🔑 **Que les 14 siguin totes d'un sol model i totes manuals no és casualitat**: la divergència
no la fabrica la materialització (que copia els dos camps) sinó **l'edició manual**, l'única
porta que escrivia `increment_base` sense `increment` — que és el que el PAS 1 acaba de tancar.

### Què NO toca, i per què

- **No-LINEAR.** Les 39 FIXED del 1383 tenen `increment=0.00` i `increment_base=NULL`: en SQL cru
  `increment IS DISTINCT FROM increment_base` també les compta (**53** en comptes de 14), però
  `_apply_rule` no els agafa mai la branca canònica —cauen a `FIXED → return base_val`— i el
  llegat no s'hi llegeix. Guarda: `logica='LINEAR' AND increment_base IS NOT NULL`.
- **Inactives.** El motor filtra `actiu=True`.
- **`increment_base` NULL.** Aquí el llegat encara ÉS la veritat; copiar-hi al revés seria
  decidir-ne una. Les resol el PAS 3. Se n'informa el recompte, no es toquen. *(A staging: 0.)*
- `update_fields=['increment']` i prou: aquest command **no toca la llei**, només el mirall.

### PROD

El command queda al repo. **Allà cal cens propi**: la xifra de la diagnosi (137) és del 21/08 al
matí i pot haver crescut. Per això `--esperades` és obligatori.

### 🚩 Deute anotat (decisió d'Agus: reportar, no tocar)

**9 de les 14** queden amb `increment_base = 0.00` perquè el relleu el porta tot el break
(`F·E1·EK·EK1·E·SF·S·S2·E7`). Avui graduen bé i `es_linear_degenerada` no les rebutja perquè
tenen break. El dia que algú els tregui el break passen a **LINEAR+0** i deixen de graduar en
silenci: és el **defecte 4 de §A.5**, ja censat. No es toca aquí perquè el fix A no ha de moure
cap cel·la.

---

## PAS 3 · ELS DOS FALLBACKS, AL MATEIX COMMIT

### Què era, de debò, aquell «fallback»

`increment` el poblava la materialització des del joc i **cap** superfície d'edició no el tocava
mai (ni `set_pom_regim_view`, ni `gravar_pom_view`, ni el payload de `taula-mesures`, ni la UI):
es fossilitzava amb el valor del dia que la regla va néixer. Caure-hi no era «un pas uniforme
raonable», era **graduar amb la regla vella**. I s'hi arribava per la porta de casa: buidar el
camp «Δ base» a Graduació envia `increment_base: null` i **passa la validació si la regla té
break** → es desa amb 200 OK, la cel·la es veu buida, i el motor gradua amb el delta del joc antic.

### La llei ara

**La D2, la mateixa de sempre: regla incompleta = cel·la ABSENT.** Mai un delta fantasma, mai un
FIXED fabricat —que és el que va deixar el model 163 amb 225 specs a delta 0 i 200 OK—. La
LINEAR sense delta base entra al **mateix calaix** que la regla inexistent i el STEP sense
valors. **Cap rescat per la talla base**: una regla sense llei no en té ni a la seva pròpia talla.

### Per què ② alça en comptes de retornar un número

`increment_de_l_aresta` és una funció **pura** que torna un float. «Absent» no s'hi pot dir amb
un valor de retorn sense que el cridador el confongui amb un delta de zero — que és, exactament,
una corba plana inventada. Alça `ReglaSenseDeltaError`; qui la caça és `propaga_ancoratges`,
l'únic node d'aquell camí que sap dir «aquesta talla no té valor». **Els tres cridadors no
creixen cap `try`.**

### L'error clar que faltava

El senyal d'una regla que no gradua vivia **només** a `warnings` i la fila desapareixia sense
que el tècnic sabés per què (§E.1). Ara:

| Node | Àncora | Què diu |
|---|---|---|
| `generate_graded_specs` | `pom/services.py:237, 315, 377-381` | reté els POMs de regla **INCOMPLETA** a part dels que **no en tenen**: es reparen de maneres diferents (l'un mirant el joc assignat, l'altre editant la regla), i dir-los igual era enviar el tècnic al lloc equivocat |
| propagació totalment buida | `pom/services.py:349-358` | missatge propi, no el genèric que fa mirar el joc de regles |
| derivació de base | `models_app/views.py:3459-3470` | deixa de tornar «No s'ha pogut derivar la base des de la talla ancorada» —que fa buscar el defecte a la talla— i porta la frase exacta del motor amb `code: regla_sense_delta` |

### El gate ho va veure

```
BLOC C · «LINEAR · ib=NULL · llegat 2.00»
   abans   escalat  XS=98.0 S=100.0 M=102.0 L=104.0 XL=106.0     ← el delta fantasma
           presa    XS=98.0 S=100.0 M=102.0 L=104.0 XL=106.0
   després escalat  XS=None S=None M=None L=None XL=None
           presa    XS=None S=None M=None L=None XL=None          ← I SEGUEIX COHERENT
```

**A i B no es van moure** (105 · 525): cap cel·la real del banc depenia del llegat, que és
exactament el que havia de passar.

`fhort/pom/test_fix_a_p3_fallback_llegat.py` (22 proves). `ElsDosAlhoraTest` és el **bessó del
bloc C** i hi és per duplicat a posta: el banc mesura staging i corre a mà; el test corre a cada
suite. Si algú toca un node i no l'altre, un dels dos ho ha de veure.

---

## PAS 4 · LES SUPERFÍCIES SOBRE LA FONT ÚNICA

**Ja llegien els camps bons** (comprovat, no assumit): Mesures · Escalat · graella de fitting
(verificades per l'Agus en viu) · **fitxa Q8** (`taulesQ8.js:212-215` surt de `taula-mesures`) ·
**export PDF** (imprimeix el `snapshot` que Q8b hi va desar, cap camí propi) · **preview del
wizard** (`wizard_views.py:625-628`).

**Les que no:**

| # | Superfície | Àncora | Canvi |
|---|---|---|---|
| ① | **Els dos exports CSV** | `pom/s8_views.py:49-68`, `:94-113`, `:184-196` | La columna «Increment/talla» imprimia el llegat, **i un joc amb break s'exportava amb UNA sola columna**: el full que en sortia no es podia tornar a entrar. Ara Δ base · Δ break · talla de break, amb `(STEP)` i `—` quan la regla és incompleta |
| ② | `grading_rules_with_units_view` | `pom/s4_views.py:275-286` | `increment_cm` ve d'`increment_base`, amb `None` quan no n'hi ha (`float(None)` hauria petat amb 500; un `0` hauria semblat una regla que no gradua — que és una altra cosa). Hi entren `increment_break_cm` i `talla_break_label` |
| ③ | **`GradingRuleSerializer`** | `pom/serializers.py:305-323` | 🚨 **l'última porta d'escriptura del llegat, i no era al cens.** Un PATCH a `/api/v1/grading-rules/<id>/` amb `{increment: 5}` desava el camp mort i tornava 200. Passa a read-only + **400 que diu el nom del camp bo** (DRF descarta els read-only en silenci, i callar aquí seria el mateix defecte un pis més amunt) |
| ④ | `grading_rules_match` | `pom/grading_utils.py:68-130` | Comparava `logica`+`increment`+`valors_step`. Dues regles amb el mateix llegat i breaks **diferents** es declaraven iguals. **Sense cap cridador viu** — i es corregeix per això: una funció de comparació que menteix és pitjor morta que viva, perquè el dia que algú la cridi ho farà confiant en el docstring |

🔒 **La talla de break surt en convenció de MOTOR als CSV**, a posta: la volta a convenció de
DOCUMENT viu al front i necessita el run. Un CSV que se l'inventés mouria l'etiqueta **una talla
sencera**. Qui exporti i torni a importar troba la mateixa etiqueta que hi ha a la BD.

### ⛔ Cens final del camp llegat

```
grep sobre codi viu (tests i migracions fora)
```

| | Estat |
|---|---|
| **LECTORS al motor** | **ZERO** — `rule.increment` no apareix a `_apply_rule` ni a `increment_de_l_aresta` ni enlloc del camí de graduació. Només comentaris que expliquen què hi havia |
| **LECTORS a superfícies** | **ZERO** |
| **ESCRIPTORS** | 🚩 **hi queden, i cal dir-ho clar.** `materialize_*`, `federation_service`, els seeds i els paquets LOSAN el segueixen poblant **com a mirall** d'`increment_base` |

**Per què els escriptors es queden.** Retirar-los canvia el **contracte entre cases**
(`federation_service.py:741, 899`) i el **format del paquet LOSAN**
(`export_losan_package.py:336` ↔ `load_losan_package.py:452`). Són decisions pròpies, no
d'aquest sprint. **El camp queda escrit i mai llegit**; la retirada física de la columna és una
migració a part, com mana el brief. *No dic que el camp estigui mort del tot: dic que ja no mana
res.*

> El `increment` que apareix al **DETECTOR** (`grading_utils:188-259`, `size_map_views`) **no és
> aquest camp**: és la sortida del parser del document, i `backfill_grading_break` la converteix
> en forma canònica. Es queda.

---

## PAS 4b · EL MIRALL DEL GUARD — un forat obert pel propi fix

🚨 **Trobat fent el cens final del PAS 4, i tancat abans de tancar el sprint.**

`grading_regime.delta_base_efectiu` deia, **en el seu propi docstring**: «la forma canònica
(`increment_base`) si està poblada, si no **el fallback legacy (`increment`) que llegeix
`_apply_rule`**». Era cert fins al PAS 3. Des del PAS 3, `_apply_rule` **no el llegeix**, i
aquesta funció va quedar sent un mirall que reflectia una cosa que ja no hi és.

**No és cosmètic.** D'aquesta funció en penja `es_linear_degenerada`, el guard A3 que
comparteixen **les quatre portes d'autoria**. Una LINEAR amb `increment_base` a NULL i el llegat
poblat **passava el guard** —«té delta 2.0, és correcta»— i el motor després no n'emetia cap
cel·la. La pantalla hauria donat per bona una fila que no gradua: exactament la classe de
defecte que aquest sprint tanca, un pis més amunt.

El mirall del **front** (`frontend/src/utils/gradingRegime.js`, `deltaBase`) portava la mateixa
línia i canvia amb ell: són bessons declarats i no es poden separar.

### Conseqüència volguda, i val la pena dir-la

Una LINEAR **sense** delta base i **sense** break ara és **degenerada** i les portes d'autoria la
rebutgen amb 400. Abans es desava i graduava amb el delta fossilitzat del joc. **El bug queda
tancat també a l'ENTRADA**, no només a la propagació. Amb break, `te_break` segueix fent
curtcircuit i la regla es desa: allà el rebuig el dona la propagació amb el seu missatge propi.
A staging no es mou cap fila (0 LINEAR actives amb `ib` NULL).

### Dues superfícies més del cens

| Superfície | Àncora | Canvi |
|---|---|---|
| `GradingRuleLightSerializer` | `pom/s2_serializers.py:108-125` | la clau `increment` es conserva (la pinta `SizeSetDetail` i la torna a enviar en editar) però surt d'`increment_base`. Hi entren `increment_break` i `talla_break_label`: **una fila que ensenya mig delta d'una regla amb trencament és una fila que menteix a mitges** |
| `SizeSetDetail.jsx` | `:305-322`, `:326` | pinta **`—`** quan no hi ha delta, no `+0` (un zero semblaria una regla que no gradua — i la que no gradua és FIXED, que és una altra cosa). Ensenya el Δ del trencament al costat, amb la talla 🔒 en **convenció de DOCUMENT** (`aDocument`), com les altres cinc superfícies |

i18n: `size_library.col_break` × 3.

### El que NO s'ha tocat, i per què

`SizeMapSetup.jsx:332, 393` i `size_map_views.py:326-350, 561-589, 990-996` fan servir
`increment`, però **no és aquest camp**: és la sortida del **detector** del document del client.
Verificat que el `create` del wizard el converteix en forma canònica abans de desar
(`size_map_views.py:988-1002` → `derive_break_fields` → `increment_base`/`increment_break`/
`talla_break_label`). Es queda.

---

## PAS 5 · LA PRESA DECLARA VERSIÓ

**El cas que ho va obrir és de PROD i és al banc.** Les teòriques d'una presa són un **clon** dels
`GradedSpec` de la versió que hi havia quan es va crear (`create_piece_fitting`). Propagar en
crea una de **nova** i la presa es queda penjant de la vella. Al 1383 hi conviuen les dues, i la
pantalla les pintava **exactament igual**: qui mirava la graella comparava mesures reals contra
una corba que ja no era la del model, i res no ho deia.

**Backend — una lectura, cap camí nou.** `PieceFitting.grading_version` és FK directa
(`fitting/models.py:395`). Faltava al payload de `fitting/model/<id>/presa/`
(`fitting/escalat_presa_views.py:148-166`). Hi entren **totes dues** —la de la presa i la
vigent— i la comparació es fa al front: si això és un problema depèn del que la persona estigui
fent, i **això no ho pot decidir un endpoint**.

**Front** — `frontend/src/pages/PropagatedEditor.jsx:100-113` (predicat) i `:355-405` (racó + banda):

- **La versió es diu SEMPRE** que se sap, també quan tot va bé. Saber de quina corba parla la
  presa és part de saber de quina presa parles; i una etiqueta que només aparegués quan hi ha
  problema seria, el dia que aparegui, una etiqueta que ningú no sap llegir.
- **L'avís va dues vegades**: badge d'alerta al racó (marca **ON** és el problema) i banda sota
  els sub-tabs (diu **QUÈ** vol dir i què se'n pot fer). En un racó de 60px la frase no hi cap, i
  la frase és la meitat útil.
- **Banda i no toast**: no és un esdeveniment, és un **ESTAT** de la pantalla.
- Tokens de la casa (llei G8): `--warn-state` / `--warn-state-bg` / `--warn-ink`. **Cap hex.**
- i18n × 3 amb paritat verificada (15 claus a `escalat`). El text no diu «versió obsoleta» —no
  ho és, l'acta d'una presa és vàlida— sinó què passa: **les teòriques que compares són d'una
  corba anterior**.

---

## QA FINAL

### La seqüència del bug A, sencera, sobre el 1383

Per les **vistes reals** (`set_pom_regim_view` → `generate_grading_view`) amb
`APIRequestFactory` + `force_authenticate`.

```
① ABANS · vigent GV#129 v6
   regla D: ib=0.50 brk=0.50 break=M · llegat increment=0.50
   D graduat: XS=58.5  S=59.0  M=59.5  L=60.0  XL=60.5

② EDITAR (set_pom_regim_view) → 200
   regla D ara: ib=1.50 brk=3.00 break=M
   🔍 llegat `increment` = 0.50   ← la porta NO el toca, i ja no el llegeix ningú

③ PROPAGAR (generate_grading_view) → 200
   vigent ara: GV#131 v7 (specs=105)
   D graduat: XS=57.5  S=59.0  M=62.0  L=65.0  XL=68.0

④ VEREDICTE
   → la v7 porta el delta EDITAT: ✅ SÍ
   → cap rastre de la corba VELLA (v6): ✅ cap
   → versions totals: 7 · actives: 1
```

**El llegat es va quedar a 0.50 i ningú el va llegir.** Abans del fix, si `increment_base`
hagués estat NULL, la corba hauria sortit d'aquell 0.50.

### El PAS 5 va aparèixer tot sol

Propagar va crear la v7 i va deixar la presa viva (`PieceFitting` #53, nascuda de la v6) enrere
— **exactament el cas que el PAS 5 existeix per veure**, sense fabricar-lo:

```
PF#52  sessió 158 (Anullada)  GV#125 v2  ·  vigent GV#131 v7  →  RÀNCIA=True
PF#53  sessió 159 (Oberta)    GV#129 v6  ·  vigent GV#131 v7  →  RÀNCIA=True  ← la que es pinta
```

Payload real per HTTP (`Host: staging.fhorttextile.tech`, token amb claim `tenant_schema`):

```
grading_version        : {'id': 129, 'num': 6}
grading_version_vigent : {'id': 131, 'num': 7}
HTTP 200
```

### El banc, contra la v7

```
A=✔(105)  B=✔(525)  C=✔(4)  ·  joc 096990db…989f intacte
```

### Segells del hash de residents

| Moment | Hash | Per què s'ha mogut |
|---|---|---|
| abans del fix | `5715f4a2…144e` | — |
| després del **PAS 2** | `59b84241…c370` | el backfill (14 files) · **A/B/C idèntics** → va tocar el mirall, no la llei |
| després de la **QA** | `6e55bc13…b6b4` | la regla D editada per la QA del bug A |

### Captures

`ops/qa/captures/fixa/` (📁 `.gitignore`, viuen al servidor):

| Fitxer | Què mesura |
|---|---|
| `p5_escalat_presa_rancia.png` | **el PAS 5 viu**: badge `v6` en alerta al racó + banda amb la frase sencera · i la regla D amb Δ **+1,5** / Δ break **+3,0** (la seqüència del bug A aterrada) |
| `p4_mesures_regla.png` · `p4_graduacio.png` | control: les columnes de regla, intactes |

🚩 **Sense «abans».** Staging serveix `frontend/dist` i `npm run build` **és** desplegar; el
build calia per passar la porta del verd. Les d'abans són les que l'Agus ja té.

### Porta del verd

```
manage.py check                                   System check identified no issues (0 silenced)
npm run build                                     ✓ built
npx eslint (fitxers tocats)                       0 errors (2 warnings preexistents a
                                                  PropagatedEditor:83,85 · SizeSetDetail:51)
i18n ca/en/es                                     paritat verificada
test fhort.pom.test_fix_a_p1_escriptors_llegat    16/16 OK
test fhort.pom.test_fix_a_p3_fallback_llegat      22/22 OK
tanda dirigida (fitxers de fixture tocats)        39/39 OK
suite fhort.pom fhort.fitting fhort.tasks fhort.models_app   <PENDENT · contra cc3c4204>
```

### 🚨 La suite va sortir vermella, i és el retorn més valuós del sprint

**Primera correguda útil** (contra `56ddeef9`): `Ran 1537 tests · FAILED (failures=10, errors=21)`.

| | Quants | Què eren |
|---|---:|---|
| **Preexistents, no del sprint** | **2** | `test_parser_excel.ElCamiIAContinuaSentElFallbackTest` — el mock de `_match_rows` té aritat 2 i `extraction_views._extraccio_via_excel` el crida amb 3 des de **`4db5158d` (16/08, T8-ter)**. Vermell des d'aleshores. **No tocat**: no és d'aquest sprint i arreglar-lo a corre-cuita seria barrejar |
| **Fixtures** | **29** | v. §PAS 1c |
| **Contracte retirat a posta** | **1** | `test_propaga.test_regla_incompleta_warning_i_columna_plana`, v. sota |
| **De les quals van destapar codi real** | — | **les dues aixetes del §PAS 1b.** Sense la suite no les hauria trobades: el cens que vaig fer buscava lectors |

> ⚠️ **Vaig reportar «29 fixtures + 2 preexistents» i eren 28 + 2 + 1.** Vaig llegir la llista amb
> un `head` que en tallava una, i vaig donar la classificació per bona sense comptar-la. La que
> faltava és la del contracte retirat, i és la més important de les tres classes.

### El contracte que es retira: «columna plana»

`test_propaga.PropagaAncoratgesTest` documentava, en un comentari propi, que una regla sense cap
delta havia de donar **«propagació PLANA (totes = anchor_val) + un únic warning (degradació
gràcil)»**.

**Una columna plana ÉS un valor fabricat**: repeteix l'ancoratge a totes les talles i el presenta
com si fos graduació — exactament el FIXED inventat que la llei D2 prohibeix, i el que va deixar
el model 163 amb 225 specs a delta 0 tornant 200 OK. La «degradació gràcil» era graciosa amb
l'usuari i mentidera amb la dada.

Ara `propaga_ancoratges` torna **`None` a cada talla**, el warning es queda i segueix sent un de
sol. S'hi afegeixen dues proves:
· **ni la talla ANCORADA rep valor** — tornar-hi el número mesurat semblaria innocu (és una dada
  real) però la fila sortiria amb una xifra i tres buits, que es llegeix com «aquesta talla sí i
  les altres encara no» en comptes de «aquesta regla no gradua»;
· i el **control del backfill**: `increment` divergent no mou cap valor quan hi ha delta base.

⚠️ **Hi va haver una correguda ANTERIOR que no compta i no la reporto com a resultat.** La vaig
engegar abans del PAS 4b; Python ja tenia `grading_regime` importat i mesurava codi ranci. Es va
aturar i re-llançar. **Una suite engegada abans d'un canvi no mesura aquell canvi** — queda a
§Mètode.

---

## ESCRIPTURES A STAGING

| Què | On | Per què |
|---|---|---|
| **14 `ModelGradingRule.increment`** | model 1383 | el backfill del PAS 2, amb OK d'Agus. **Cap camp de la llei tocat** |
| **Regla D del 1383** (`ib` 0.50→1.50, `brk` 0.50→3.00) | model 1383 | la QA de la seqüència del bug A, que l'ordre demana explícitament |
| **`GradingVersion` v7 (GV#131)** + 105 specs | model 1383 | conseqüència de la propagació de la QA |
| `frontend/dist` | staging | `npm run build` **és** desplegar en aquesta màquina |
| `systemctl restart ftt-staging` | staging | ×2 (el gunicorn serveix el codi de quan va arrencar) |

> ⚠️ **El banc 1383 ja no és el de la sembra.** La regla D porta ara `ib=1.50 · brk=3.00` i el
> model té 7 versions. És l'estat que la QA demanava i queda documentat aquí; qui el vulgui
> tornar a la foto de PROD té la sembra (`sembra_model_837`) i aquest paràgraf.

---

## DEUTES I COSES QUE HAS DE SABER

### 🚩 Pendents

1. **Els escriptors del llegat es queden.** `materialize_*`, federació, seeds i paquets LOSAN
   segueixen poblant `increment` com a mirall. Retirar-los és una decisió de **contracte entre
   cases** i de **format de paquet**, no d'aquest sprint (v. §PAS 4).
2. **La retirada física de la columna** (`ModelGradingRule.increment` i `GradingRule.increment`)
   és una migració a part, com mana el brief. El sprint la deixa sense cap lector.
3. **9 regles amb `increment_base = 0.00`** al 1383 (v. §PAS 2). Deute anotat per decisió d'Agus.
4. **PROD necessita cens propi** abans del backfill. La xifra de 137 és del 21/08 al matí.
5. **`SizeSetDetail.jsx` i `SizingProfileSelector.jsx` segueixen sense muntar-se** (des que
   `SizeLibrary` els va retirar). Aquest sprint els ha tocat —el serializer que els alimenta i
   la fila que pinten— però **no es poden veure**. Si algun dia tornen a tenir ruta, hereten els
   canvis del PAS 4b; si es decideix esborrar-los, aquest treball se'n va amb ells. **Decisió
   d'abast pendent, no d'aquest sprint.**
6. **🚩 `test_parser_excel` segueix vermell** (2 proves), i **no és d'aquest sprint**: mock amb
   aritat vella des del 16/08 (`4db5158d`). Cal una sessió que hi passi.
7. **La decisió «matar el camp llegat» NO és a `DECISIONS.md`** — hi vaig buscar i no hi és.
   Viu només al brief d'aquesta sessió. No l'hi he afegida perquè `DECISIONS.md` està modificat
   per una sessió concurrent i no es commita mai. **Cal baixar-la-hi a mà.**

### ⚠️ Comportaments que canvien (no són regressions, són el fix)

| Porta | Abans | Ara |
|---|---|---|
| `PATCH .../regles/<pom>/editar/` amb `{increment: X}` | desava el llegat, 200 OK, corba intacta | mou la corba de debò · 400 si deixa la regla LINEAR+0 |
| `PATCH .../regles/<pom>/` | idem | idem |
| `POST /sizing-profiles/<id>/restaurar/` | restaurava dos camps de set | restaura la llei sencera → **pot restaurar més regles que abans** |
| `POST /sizing-profiles/<id>/clonar/` | perdia el break | clona la regla sencera |
| `PATCH /api/v1/grading-rules/<id>/` amb `increment` | 200 OK, camp mort desat | **400** amb el nom del camp bo |
| Els dos CSV d'export | 5 columnes, delta llegat | 7 columnes, delta canònic + break |
| LINEAR sense `increment_base` | graduava amb el delta del joc antic | **cap cel·la** + avís explícit |

### 🔒 Mètode

1. **El token de QA sí que es pot emetre** des d'aquesta sessió — el que faltava era el claim
   `tenant_schema` (`fhort/auth_jwt.py`). `RefreshToken.for_user()` sol dona un token que
   l'API rebutja amb `token_not_valid`, i la captura surt a la pantalla de login sense error.
   Deixo el patró escrit perquè la sessió que ve no hi perdi el temps:
   ```python
   with schema_context('fhort'):
       r = RefreshToken.for_user(u); r[TENANT_CLAIM] = 'fhort'; print(r.access_token)
   ```
2. **`manage.py test` sense `--noinput`** peta amb `EOFError` si hi ha una BD de test penjada
   d'una correguda anterior. Amb el wrapper de background que mata a 2 min, això passa sovint:
   `setsid nohup … --noinput` és el patró.
3. **Una suite engegada ABANS d'un canvi no mesura aquell canvi.** Python ja té el mòdul
   importat. Si es toca codi amb la suite corrent: aturar-la i re-llançar, o el verd no val.
   Em va passar amb `grading_regime` i vaig haver de descartar 40 minuts de correguda.
4. 🔑 **Un cens de LECTORS no tanca un camp; en fa falta un d'ESCRIPTORS.** Retirar un fallback
   no és una operació de lectura: el que et fa mal no és qui llegeix el camp mort, és qui el
   **segueix omplint sol**. Les dues aixetes del §PAS 1b eren seeds, i cap grep de lectura les
   podia trobar.
5. **Un test d'IGUALTAT no veu una RETIRADA.** `test_linear_identic` va donar verd amb les dues
   taules plenes de `None`. Qualsevol comparació A==B necessita, a més, una guarda que exigeixi
   que hi hagi contingut — la mateixa lliçó que el golden de models inexistents.
