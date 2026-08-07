# M-FI · Les tres peces que tanquen §7.2 del REPORT_NIT_CAPES

> **Data:** 2026-08-07 matí · **Branca:** `dev` (staging) · **Cap push.**
> **Base:** `origin/dev` = `c963bf71` (re-pull verificat: 0 darrere).
> **Context:** `REPORT_NIT_CAPES.md` §7.2 — els tres caps solts que la nit va deixar
> assenyalats i que l'Agus ha decidit el 07/08 al matí.
> **Commits:** `60b2307d` (M1) · `42932ce9` (M1-bis) · `f92b56cd` (M3). M2 no en té: **no ha
> escrit res, i el perquè és el cos d'aquest report.**

---

## 0 · El resum d'una llegida

| | Peça | Estat | Què ha canviat de debò |
|---|---|---|---|
| **M1** | `sense_joc` PRESERVA | ✅ fet | Un model **sense cap joc** ja no perd les seves `MANUAL` en rebre el primer. Una línia de predicat, 2 tests nous, i **4 proves veïnes que codificaven la llei vella** (M1-bis). |
| **M2** | `set_grading_origen` executat | ✅ cens fet · **0 aplicats** | El cens diu que **no hi ha cap joc real sense classificar**: els 2 de `fhort` no tenen cap model a sobre i **cap dels dos es pot classificar amb confiança**. S'anoten, es deixen NULL. Els 14 de `public` són **fora de l'abast del wipe per construcció**. |
| **M3** | `derivat_de_rule_set` | ✅ fet | FK additiva + migració `0079` auditada als 2 schemes. S'omple d'ara endavant a 4 camins amb criteris explícits. **Cap backfill. Cap canvi de política.** |

**El titular:** la peça que semblava més gran (M2, «el backfill») és la que no ha escrit res, i
és el resultat correcte. La peça que semblava més petita (M1, «una línia») ha mogut quatre
proves de guarda. I això és exactament el que un cens serveix per descobrir **abans** d'escriure.

---

## 1 · M2 · EL CENS (la peça central)

### 1.1 · L'univers sencer, pels tres schemes

```
manage.py set_grading_origen --list --tenant {fhort,los,public}
```

| Schema | Rulesets | Sense classificar | Models que hi pengen |
|---|---:|---:|---:|
| `fhort` | 47 | **2** | **0** |
| `los` | 0 | 0 | — |
| `public` | 14 | **14** | **no aplicable** (v. §1.4) |

Sortida literal de l'eina, per a `fhort`:

```
    id  origen      cust  codi_sistema                   regles  nom
  ----  ----------- ----- ------------------------------ ------  --------------------------------
    98  NULL        -     EU_STRETCH_WOMAN_SLIM_CUSTOM       19  Custom Alpha EU — Women
   108  NULL        -     -                                   0  Mango EU woven woman regular - only dres

  2 rulesets sense classificar (origen NULL).
```

### 1.2 · La troballa que canvia la pregunta

```
MODELS amb joc SENSE CLASSIFICAR : 0
MODELS amb joc                   : 0   (de 0 models totals a `fhort`)
ModelGradingRule                 : 0   ·   d'origen MANUAL: 0
```

**`joc_sense_classificar` no té avui cap instància viva, i no en pot tenir: `fhort` no té cap
model.** (És la conseqüència de V4 de la nit — els 46 models esborrats.) O sigui que M2 **no
podia curar res**: el seu valor és preventiu, i el cens és la peça que ho demostra en comptes
de suposar-ho.

Això no fa M2 inútil: els dos jocs NULL segueixen essent **assignables des de la pantalla**, i
el dia que algú n'assigni un a un model nou, les residents que en surtin naixeran etiquetades
`MANUAL` i el parany tornarà. Per això s'anoten en comptes de tancar-los en silenci.

### 1.3 · Els dos de `fhort`, un per un, amb l'evidència

#### `id=98` · «Custom Alpha EU — Women» · 19 regles · 0 models

| Senyal | Valor |
|---|---|
| `codi_sistema` | `EU_STRETCH_WOMAN_SLIM_CUSTOM` |
| `customer` (FK) | — |
| `size_system` | — |
| `garment_type_item` | — (llei CONTENIDOR: informat = contenidor de client) |
| `pendents_vincular` | 0 codis (cap rastre d'import de document) |
| construction / fit / target | Stretch Knit · Slim/Fitted · Woman |

**El fet dur:** és un **bessó byte a byte** de `id=81` «EU Stretch Woman Slim», que ja és
`CANONICAL`. Mateixos 19 POMs i **0 diferències** en `logica`, `increment`, `increment_base`,
`increment_break` i `talla_break_label` a totes 19. El seu codi és el del canònic amb `_CUSTOM`
enganxat.

**Per què NO es classifica.** L'evidència apunta a dues bandes i no en descarta cap:
- el nom (`Custom`, el sufix `_CUSTOM`) diu **clon per a una versió de client** — que és
  literalment l'exemple que el propi model posa per a `CLIENT_RUN` (`pom/models.py:1122-1125`);
- el contingut diu que **no s'hi ha customitzat res**: cap client, cap `size_system`, cap
  contenidor, cap model. Un clon que ningú va arribar a tocar.

Marcar-lo `CANONICAL` seria afirmar que és catàleg de la casa quan el seu nom diu que no ho és;
marcar-lo `CLIENT_RUN` seria afirmar un client que **no existeix enlloc de la fila**. Les dues
coses són inventar-se-la, i el brief ho prohibeix. 🚩 **Queda NULL.**

> 💡 **La pregunta per a l'Agus, amb tota l'evidència al davant:** és un duplicat teu del canònic
> Stretch Woman Slim (→ i llavors probablement el que vol no és classificar-lo sinó
> **esborrar-lo**, perquè duplica el catàleg amb un nom que confon), o és el començament d'una
> versió per a un client concret que no es va acabar (→ `CLIENT_RUN`)? Quan ho diguis, es tanca
> amb una línia:
> `manage.py set_grading_origen --map "98:CANONICAL"` *(o `CLIENT_RUN[:CODI]`)*.

#### `id=108` · «Mango EU woven woman regular - only dress» · **0 regles** · 0 models

| Senyal | Valor |
|---|---|
| `codi_sistema` | `''` (buit) |
| `customer` (FK) | — |
| `size_system` | `ALPHA_EU_W` · `customer_codi=''` |
| construction / fit | cap · cap |
| `pendents_vincular` | 0 codis |

**El fet dur:** té **zero regles**, i «Mango» **no és cap client d'aquesta casa** (els customers
de `fhort` són `BRW`, `FTT`, `LOS`).

**Per què NO es classifica.** No pot ser `CANONICAL` (no és catàleg de la casa: porta el nom
d'una marca externa i no té ni una regla), ni `CLIENT_RUN` (no hi ha cap client darrere), ni
`IMPORT` (no s'ha importat res: 0 regles, 0 `pendents_vincular`). És una **closca buida** d'una
prova. Classificar-la seria posar-li una etiqueta a una cosa que no és res. 🚩 **Queda NULL.**

> 🚨 **I a més és una mina.** Un `GradingRuleSet` amb 0 regles és el forat R1 —el que va buidar
> el model 163—: assignar-lo esborra les residents i torna 200. Avui la porta D1
> (`_validar_ruleset_assignable`, bloqueig dur amb `ruleset_buit`) ja el para, però la fila no
> hauria de ser ni oferible al desplegable. 💡 **Recomanació: esborrar-la, no classificar-la.**
> Decisió de l'Agus; esborrar dades és fora d'aquest abast.

### 1.4 · Els 14 de `public`: per què no entren a M2

Tots 14 tenen **0 regles** i els noms del catàleg de la casa (`EU Woven Woman Regular`,
`EU Knit Baby Regular`…), amb ids (2–15) que **no són els de `fhort`** (75–93). Són l'ombra
buida del catàleg al schema compartit.

**No són «jocs reals» i no poden ser-ho mai:** `models_app` i `tasks` són apps **tenant-only**,
o sigui que a `public` **no existeix `Model` ni `ModelGradingRule`**. Cap fila d'aquestes pot
ser el joc d'un model, i per tant **cap d'elles pot alimentar `joc_sense_classificar`**. Són
fora de l'abast del wipe per construcció, no per política.

**I classificar-les seria pitjor que deixar-les.** `bootstrap_tenant` copia els rulesets
`CANONICAL` de l'schema origen (`--from`, default `fhort`). Marcar aquestes 14 com a `CANONICAL`
les faria elegibles per viatjar si algú fes `bootstrap_tenant --from public`, i el que arribaria
al tenant nou serien **14 rulesets buits** — la mina R1, catorze vegades. Avui el gate
(`n_canon == 0` → error clar) ho impedeix precisament perquè són NULL. 🚩 **Queden NULL, i és
la resposta segura i l'honesta alhora.**

### 1.5 · 🚩 Un defecte de l'eina de M2, trobat pel camí (ANOTAT, no tocat)

```
$ manage.py set_grading_origen --list --tenant public
django.db.utils.ProgrammingError: relation "tasks_customer" does not exist
```

`_list` fa `select_related('customer')` (`set_grading_origen.py:71`), i `pom` és **l'única app
SHARED+TENANT**: a `public` hi ha les seves taules però **no** les de `tasks`. L'eina de
classificar, doncs, **no pot censar un dels tres schemes**. Fix d'una línia (fer el
`select_related` i la columna `cust` condicionals al schema). No s'ha tocat: l'abast és tancat i
no bloqueja M2 (el cens de `public` d'aquest report s'ha obtingut read-only per una altra via).

---

## 2 · M1 · `sense_joc` preserva

### 2.1 · El canvi

`services.py` · `motiu_no_preserva`: `joc_anterior is None` retornava `'sense_joc'` (→ el wipe
s'enduia les `MANUAL`); ara retorna `None` (→ les preserva). El codi `'sense_joc'` **deixa
d'existir**.

**L'argument, que ja era al report de la nit:** sense joc, una `MANUAL` només pot ser autoria. No
hi ha joc del qual pugui haver sortit com a còpia —que és tot el parany de 6.1— i «Sense
graduació», l'únic gest que deixa un model sense joc havent-ne tingut, **ja esborra totes les
residents abans**. El que hi hagi després s'ha escrit a mà. No es dedueix res de nou: es va
deixar sense aplicar perquè era **política**, i ara té acta.

### 2.2 · El radi

`poms_manual_a_preservar` és l'únic lector del predicat, i el llegeixen **les dues bandes de la
llei F1-bis** — el 409 que demana permís (`views.py:1078`) i la destrucció (`services.py`). El
permís i la destrucció segueixen mirant el mateix. Camins que hi guanyen: `update-step2` (primer
joc), `copiar_de_model` (destí sense joc) i W5. Els que passen `JOC_ANTERIOR_NO_INFORMAT` no
canvien de comportament.

### 2.3 · M1-bis · les 4 proves que codificaven la llei vella

`EsborratResidentsD314Test` munta un model **sense cap joc**, li penja residents i li assigna el
primer: exactament el cas que M1 canvia. Quatre expectatives havien de deixar de ser certes.

**Es manté intacte el que cada prova guarda:** l'avís 409 i que no s'escrigui res sense permís ·
`imported` a primer nivell · la separació dels dos flags · el Watchpoint i que el recompte es
prengui abans del `save()`.

**Canvia:** `residents`/`per_origen` del 409 compten només el que **cau** (llei F1-bis literal,
que `views.py:666-676` ja aplicava i que aquest cas no exercia) · `test_els_dos_flags…` passa la
seva única resident de `MANUAL` a `IMPORTED`, perquè amb una `MANUAL` ja no cauria res i la prova
es quedaria sense subjecte (el subjecte és la separació dels flags) · el test del Watchpoint
afirma `esborrades`/`preservades`.

### 2.4 · 🚩 El rastre que M1 fa visible (ANOTAT, no tocat)

El **text** del Watchpoint diu:

```
Assignat el joc «RES_CATALEG» (#1) esborrant 1 regles pròpies del model (1 IMPORTED · 1 MANUAL).
1 escrites a mà (MANUAL) s'han conservat.
```

El desglossament entre parèntesis surt del recompte **d'abans** i hi llista una regla que **no ha
caigut**. El 409 sí que la resta (`views.py:671-676`); el Watchpoint no (`views.py:1201`). És un
llegat de 6.1 —**M1 no el porta**— però M1 el converteix en el cas normal, perquè ara la
preservació és la norma i no l'excepció. El test ho diu i **no l'enshrineix**: afirma les dues
frases correctes i calla sobre el parèntesi. Fix d'una línia, fora d'aquest abast.

---

## 3 · M3 · `derivat_de_rule_set`

### 3.1 · El camp

FK nullable de `ModelGradingRule` a `pom.GradingRuleSet` · `SET_NULL` · `db_constraint=False`
—el patró de la casa per als creuaments cap a `pom`, que és SHARED (taula també a `public`)
mentre `ModelGradingRule` és tenant-only; mateix argument que el FK `pom` del costat. Esborrar
un joc del catàleg no s'ha d'endur la regla del model: només el rastre d'on va néixer.

**Per què cal:** `origen` diu «algú hi ha tocat», **no** «aquest valor és seu» (sorpresa #3 de la
nit). Amb això, autoria i còpia es deien igual i el wipe només podia **inferir** mirant l'estat
del joc anterior del model sencer. Ara ho diu la fila, i ho diu **qui ho sap**: el que la
materialitza.

### 3.2 · Qui l'omple, i amb quin criteri

El criteri és sempre **el que l'escriptor ja sap**, mai una deducció posterior:

| Camí | Què hi escriu | Per què |
|---|---|---|
| `materialize_model_grading_rules` | `r.rule_set_id` de cada `GradingRule` | La regla d'origen ho sap; ningú més ho tornarà a saber. |
| `..._from_specs` | `s['rule_set_id']`, via `grading_utils.rule_to_spec` | Únic punt del camí dels specs on encara se sap. |
| W5 (el mateix camí) | **mixt a posta** | El que ve del contenidor el porta; el que ve del **document del client** no, perquè no ve de cap joc. NULL hi és la resposta correcta, no una pèrdua. |
| Pantalla (`set_pom_regim_view`, `gravar_pom`) | **hereta** si la fila neix del fallback del catàleg; **NULL** si neix de zero; **no es toca** si ja existia | És literalment una còpia, i això és el que M3 desfà. El camp diu d'on va **néixer**, no qui l'ha tocada l'últim (això és `origen`). |
| Federació (`federation_service.py:813`) | NULL | El joc d'origen viu a l'altra casa; el seu id aquí no vol dir res. |

**Cap backfill de files velles**: d'on venien no es pot saber, i inventar-ho seria tornar a
mentir. (Avui, a més, no n'hi ha cap: `fhort` té 0 `ModelGradingRule`.)

### 3.3 · El que M3 **no** fa

**No canvia cap política.** 6.1 i M1 segueixen decidint per l'estat del joc anterior. El test
`test_el_wipe_amb_la_FK_informada_es_comporta_EXACTAMENT_com_ahir` ho fixa per les dues bandes:
amb la FK dient explícitament que la fila és còpia d'un joc sense classificar, **la política
segueix sense mirar-la**. Perquè el dia que això canviï sigui una decisió i no una deriva.

---

## 4 · VERIFICACIÓ

| Control | Resultat |
|---|---|
| `manage.py check` | **net** (0 issues) |
| `tests_sembra_grading` + `test_copia_model_a_model` + `test_g1_graduacio` + `test_set1_creacio` + `pom.test_n1_tipus_escala` | **141/141 OK** |
| dels quals `tests_sembra_grading` | **103/103** (eren 94 a N4: +2 M1, +7 M3) |
| reescrits | 4 (M1-bis) + el predicat aïllat |
| `migrate_schemas` (sense `--schema`) | 3 «Applying… OK» |
| **auditoria a `information_schema`** | v. §4.1 |
| `systemctl restart ftt-staging` | **active** · `ActiveEnterTimestamp 2026-08-07 05:36:03 UTC` |
| rutes vives (sense credencial → 401) | v. §4.2 |

### 4.1 · L'auditoria de BD (i per què no n'hi havia prou amb l'OK)

`migrate_schemas` va dir **tres** «Applying `0079`… OK». La columna existeix a **dos** schemes:

```
COLUMNA derivat_de_rule_set_id:   ('fhort', 'bigint', nullable=YES)
                                  ('los',   'bigint', nullable=YES)
schemes amb la taula:             ['fhort', 'los']
constraints de BD sobre la columna: []        ← db_constraint=False respectat
índexos:  fhort · los  (models_app_modelgradingrule_derivat_de_rule_set_id_16952121)
```

El tercer OK és el de `public`, que **no té la taula** perquè `models_app` és tenant-only. És
exactament l'«OK enganyós» que la llei del `CLAUDE.md` avisa, i per això l'auditoria és a
`information_schema` i no a la sortida de la comanda.

### 4.2 · Les rutes, després del restart

El restart **és** el desplegament del backend (llei d'infra: el gunicorn serveix el codi de quan
va arrencar). Test dels quatre camins que aquest sprint toca, **sense credencial** —401 = ruta
viva al procés; 404 = el procés no la té:

```
401  PATCH /api/v1/models/1/update-step2/        ← M1 (les dues bandes de F1-bis)
401  POST  /api/v1/models/1/pom/1/regim/         ← M3 (l'escriptor de pantalla)
401  POST  /api/v1/models/1/gravar-pom/          ← M3 (l'altre escriptor)
401  POST  /api/v1/models/1/copiar-de/2/         ← M1 (destí sense joc)
401  GET   /api/v1/models/
```

---

## 4.3 · El pas del `revisor-diff` (efectes col·laterals)

Sense blocadors. Els 6 punts de risc, comprovats un a un contra el codi real:

- ✅ **La clau nova de `rule_to_spec`** no trenca res: cap `**spec` al backend, cap comparació de
  dict sencer (`spec_forms_match` mira 3 claus per nom), i el que va a JSON són specs de fitxa
  que no la porten. 🔵 *Efecte lateral honest:* avui la branca `s.get('rule_set_id')` de
  `..._from_specs` **no s'exerceix en producció** — a W5 `resident_specs` són sempre specs de
  detecció; el «camí mixt» que documento a §3.2 existeix al codi i al test, però encara no té
  cap productor viu. Queda llest per al dia que `cls['sembra']` s'hi sembri.
- ✅ **`'sense_joc'`** no tenia cap consumidor a tot el repo, `frontend/` inclòs (l'únic hit és
  una clau i18n homònima, `graduacio.superficie.sense_joc`, que és el fallback del nom del joc).
- ✅ **Cap serialitzador de `ModelGradingRule`** (no n'hi ha cap), cap `.values()` sense arguments,
  i la federació llegeix camp a camp: la columna nova **no s'escapa** al paquet entre cases.
- ✅ **`_load_grading_rules` tot-o-res**: cap camí on preservar una regla deixi el model graduant
  a mitges — la preservació sempre va amb la materialització completa del joc nou.
- ✅ **La migració** és additiva de veritat, reversible, i `unique_together('model','pom')` queda
  intacte.

### 🚩 I dues coses que M1 fa aparèixer i s'han de dir

**(a) La premissa de M1 té una SEGONA PORTA que no vigila ningú.** M1 es justifica dient que
«Sense graduació» és l'única manera de quedar-se sense joc havent-ne tingut, i que aquell gest
ja esborra totes les residents (`views.py:1118`). **No és tota la veritat.** Esborrar el JOC des
del catàleg (`pom/views.py:283-287`) també deixa el model sense joc: `Model.grading_rule_set` és
`SET_NULL` (`models_app/models.py:234-238`) i **les residents es queden** —el propi codi ho diu
al comentari: `instance.delete()  # CASCADE: GradingRule; Model → SET_NULL`.

Conseqüència: si el joc esborrat **no estava classificat**, les seves residents duien `MANUAL`
estampat per `origen_mgr_des_de_ruleset`, i M1 les preservarà en assignar el joc següent —
saltant-se les regles del joc nou per a aquells POMs. **És el parany de 6.1 entrant per una
altra porta.** No destrueix res: fa graduar amb la còpia d'un joc mort, sense avís.

**Per què no invalida M1, i què el tanca de debò:** el forat necessita **un joc sense
classificar**, que és exactament el que M2 existeix per extingir. Exposició viva avui: **zero**
(0 models a `fhort`). I la porta ja demana confirmació explícita (409 «deixarà els models sense
grading derivat»). 👉 Decisió per a l'Agus: es dóna per tancat amb M2, o el gest d'esborrar un
joc ha d'esborrar també les residents que en venien (que és el que `derivat_de_rule_set` ara
permetria fer amb precisió… si no fos pel punt (b)).

**(b) `SET_NULL` esborra la traça de M3 justament quan més falta.** El moment en què s'esborra un
joc és exactament el moment en què «això és autoria o còpia?» esdevé irrespondible per sempre —
i és el moment en què `derivat_de_rule_set` es posa a NULL. `SET_NULL` és el que el brief
demanava i és coherent amb el patró de la casa (el patrimoni és del model), però si el camp ha
de ser **forense** hi ha una tensió real. Alternativa, si es vol: enter sense FK, o `SET_NULL`
amb fotografia del nom del joc al costat. **No s'ha tocat: era una instrucció explícita.**

🔵 *Menors anotats:* els dos escriptors de pantalla busquen el `src` del catàleg **sense filtrar
`actiu=True`** (`views.py:2361` i `:4806`) — preexistent per als valors, i ara M3 hi afegeix
també el segell de procedència · `poms_manual_a_preservar` no filtra `actiu` (avui inofensiu:
cap codi desactiva un `ModelGradingRule`, i `comptar_regles_residents` tampoc filtra, o sigui que
l'aritmètica del 409 queda consistent) · el retorn de `motiu_no_preserva` **no s'escriu enlloc**
—ni log, ni resposta, ni Watchpoint— contra el que promet la seva pròpia docstring.

---

## 5 · EL QUE QUEDA A LA TAULA DE L'AGUS

| # | Decisió | On |
|---|---|---|
| 🚩 1 | **`id=98`** «Custom Alpha EU — Women»: duplicat del canònic (→ esborrar?) o versió de client sense acabar (→ `CLIENT_RUN`)? | §1.3 |
| 🚩 2 | **`id=108`** «Mango…»: closca buida amb nom d'una marca externa. Recomanació: **esborrar**, no classificar. | §1.3 |
| 🚩 3 | Els **14 de `public`**: inerts i fora de l'abast del wipe. Es queden NULL o es netegen? | §1.4 |
| 🚩 4 | `set_grading_origen --list --tenant public` **peta**. Fix d'una línia. | §1.5 |
| 🚩 5 | El **text** del Watchpoint llista regles preservades dins del recompte d'esborrades. Fix d'una línia. | §2.4 |
| 🚩 6 | **La segona porta de M1**: esborrar el joc del catàleg deixa el model «sense joc» amb les residents vives. Es dóna per tancat amb M2, o l'esborrat del joc s'ha d'endur les seves residents? | §4.3a |
| 🚩 7 | **`SET_NULL` vs. traça forense** a `derivat_de_rule_set`: el camp s'esborra just quan la pregunta esdevé irrespondible. | §4.3b |
| 🚩 8 | **W5 preserva en silenci**: cap avís ni Watchpoint quan la `MANUAL` del tècnic descarta la regla del document. I el `manual_choice='sobreescriure'` del wizard **només governa les mesures**, no les regles — el tècnic respon una cosa i en passa una altra. | §4.3 |

---

## 6 · NOTES D'EXECUCIÓ

- **Col·lisió de numeració, un altre cop — i ara triple.** El numerador és un comptador compartit
  entre sessions i no es pot coordinar. Han quedat duplicats els números **90, 93 i 94**:

  | Nº | Aquesta sessió (M-FI, backend) | L'altra sessió |
  |---|---|---|
  | 90 | `42932ce9` M1-bis | `8f45fd6b` fix(clients), frontend |
  | 93 | `ae1b0f66` revisor-diff | `ea855527` C1 · TODDLER_EU |
  | 94 | `5b28f649` cronologia | `0c793378` C2 · BABY_MONTHS |

  Mateix criteri que el 88 de la nit: **no renumero**. Reescriure història d'una branca on hi
  treballa algú altre costa més del que val un número. **Els meus són `60b2307d`, `42932ce9`,
  `f92b56cd`, `2673b5ea`, `ae1b0f66`, `5b28f649`** — pels hashos no hi ha ambigüitat.
- **Cap push, cap deploy de frontend.** El `restart` del backend és meu i s'ha fet amb els meus
  tres commits ja a l'arbre.

- **⏱️ La cronologia amb la sessió concurrent, perquè el restart és un desplegament compartit.**
  L'he verificada amb `django_migrations` i els `mtime`, no de memòria:

  | UTC | Qui | Què |
  |---|---|---|
  | 05:15:57 | jo | `models_app.0079` aplicada |
  | **05:36:03** | **jo** | **`systemctl restart ftt-staging`** — el disc només portava els meus canvis |
  | 05:38:06 | l'altra sessió | `pom.0064` · `0065` · `0066` aplicades |
  | 05:43–05:44 | l'altra sessió | edita `pom/models.py`, `pom/serializers.py` · aplica `pom.0067` |

  **El meu restart no ha desplegat res seu** (els seus fitxers són 7 minuts posteriors), i les
  seves migracions no van entrar per la meva correguda. 🚩 **Però ara staging té un desfasament
  viu que no és meu de tancar:** el gunicorn en marxa és el de les 05:36 i **no coneix** els
  models de `pom.0064-0067`, que sí que estan aplicats a la BD. Es tanca sol quan aquella sessió
  faci el seu restart; ho deixo dit perquè el darrer restart el vaig fer jo i, si algú mira
  l'hora del procés, la conclusió fàcil seria equivocada.
