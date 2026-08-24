# M3 · CICLE DE VIDA DEL MODEL — tres estats, tancament, reobertura i board

> **Patró B · IMPLEMENTA.** Sprint acotat: `Model`, el seu cicle de vida i el board per-model.
> Cap fitxer de `patterns/**` tocat; cap gest sobre el model **1383**.
> **Deliverable únic**: aquest fitxer. **Cap push** — el fa l'Agus.

---

## 0 · CAPÇAL

| Fet | Valor |
|---|---|
| Worktree | **`/var/www/ftt-m3cv`**, branca **`m3-cicle-vida`**, creada de `dev` a `d6368482` |
| Per què worktree | `dev` a `/var/www/ftt-staging` té feina viva d'altres fils i **índex compartit** ([[ftt-commit-sense-pathspec-endu-el-stage-alie]]). ⚠️ El worktree `/var/www/ftt-m3cv` **NO és** el `/var/www/ftt-m3` que ja existia: aquell és la branca `dev-m3` d'un sprint DIFERENT (Gantt de projecte) i no s'ha tocat |
| HEAD d'arribada | **9 commits** (7 de feina + l'acta + el merge de `dev`), **cap push** |
| Base i `dev` | `dev` **va avançar durant l'sprint** (M2-codes, 5 commits). S'ha fet `git merge dev` al final: la branca ja porta la base que el brief demanava (`M2+codes`) i els solapaments de `WorkPlan.jsx` i i18n ja estan resolts aquí, no els hereta el merge d'Agus |
| `.env`, `venv`, `node_modules` | **enllaçats** al tree principal (`ln -s`), no copiats. No entren a git |
| Servei compartit | ⚠️ **`ftt-staging.service` NO reiniciat.** Els fums corren contra un **gunicorn propi** del worktree a `127.0.0.1:8131` |
| Migracions | **`models_app/0087_m3_cicle_vida_model`** (única). Aplicada a `public`, `fhort` i `los` amb `migrate_schemas` (mai `--schema`) |
| Model 1383 · golden 162 | **no tocats**. Els fums treballen només sobre el banc `[QA-M1]` |

### Els commits

```
ae993668 fix(board): un `?estat=` mal escrit no obre el board als models acabats
aae4199f docs(ordres): l'acta d'M3 — el cicle de vida del model
   (merge de `dev` · M2-codes)
609e3092 qa(m3): els dos fums del cicle de vida — HTTP (25 OK) i PANTALLA (20 OK, amb captures)
56445fea feat(cara): M3 · el cicle de vida a la pantalla — Accions, banner, vistes i xip de volta
8866a900 feat(board): FASE 4 · el board per-model, ronda-aware — i una ATURADA declarada
40119abd feat(model): FASE 2+3 · FIT-10/FIT-11 — tancar, reobrir i jubilar un model
0d4f913d feat(model): FASE 1 · FIT-9 — els TRES estats del model (nou/acabat/jubilat)
e0e091f6 test(m3): FASE 0b — el board per-model, fixat ABANS de tocar-lo
       + merge: dev (M2-codes)
```

---

## 1 · FASE 0 · EL CENS, ABANS D'ESCRIURE RES

### 0a · `Model.estat`: tots els lectors i escriptors

Totes les línies són **d'abans de l'sprint** (`d6368482`).

**ESCRIPTORS — tres, i tots tres de CREACIÓ amb el MATEIX valor:**

| Punt | Què escrivia |
|---|---|
| `models_app/models.py:242` | `default=ESTAT_NOU` del camp |
| `models_app/views.py:967` (`crear_model`) | `estat='Nou'` **literal** |
| `models_app/bulk_import_service.py:597` (`_build_model`) | `estat='Nou'` **literal** |
| `models_app/management/commands/sembra_model_837.py:581` | `estat=m['estat']` de l'export (que val `'Nou'`) |
| 🚨 `models_app/serializers.py:424` | **`fields = '__all__'` sense `estat` a `read_only_fields`** → el PATCH genèric de `/api/v1/models/<id>/` **podia escriure qualsevol estat**. Cap client ho feia (ni el front, ni el backoffice, ni cap test), però la porta hi era |

**LECTORS — cinc, i cap branca de codi que depengui del VALOR:**

| Punt | Què en fa |
|---|---|
| `tasks/views_b.py:97` | whitelist d'ordenació del board (`?ordering=estat`) |
| `tasks/views_b.py:160` · `:227` | el `values()` de l'agregació i el `shape()` de la fila: viatja **cru** |
| `models_app/views.py:85` (`ModelFilter.Meta.fields`) | filtre **exacte** `?estat=` |
| `models_app/views.py:4383` (`model_dashboard_view`) | `on_soc.estat`, cru cap a la fitxa |
| `models_app/models.py:367` | `Index(fields=['estat', 'fase_actual'])` |
| **Front** · `pages/Models.jsx:375` | la columna «Estat» **pinta un guió a posta** amb el motiu escrit |
| **Front** · `components/model/DashboardTab.jsx:137` | `t('kanban.estats.' + estat)` — **etiqueta**, no branca |
| **Front** · `components/EstatBadge.jsx` | mapa d'etiquetes… **d'un component que NO munta ningú** (0 importadors) |

> ✅ **VEREDICTE: cap lector depenia dels valors vells, i per això el repropòsit era segur.**
> A PROD tot estava a `'Nou'` (el cens ho deia) i a staging també: la migració va comptar
> **37 models a `fhort` i 51 a `los`**, i tots hi eren. El brief autoritzava aturar-se si el cens
> desaconsellava el repropòsit; **no ho desaconsellava**, i el motiu és aquest: era un vocabulari
> de quatre paraules que ningú no llegia.

🔑 **I per això el backfill pot ser «tot a `nou`» sense mapa de conversió.** Un mapa
(`Tancat→acabat`) hauria estat pitjor que inútil: hauria declarat **acabats** uns quants models
que ningú no ha tancat mai amb l'acte que FIT-10 exigeix. La migració ho porta escrit.

### 0b · `by_model` / `kanban_state`: condicions i consumidors

**El cens del 23/08 ho deia amb totes les lletres: `by_model` (133 línies) NO TÉ NI UN TEST.**
Abans de tocar-lo se n'han escrit **14** que fixen el comportament **d'avui** i que van passar
verds **contra el codi sense tocar** (commit `e0e091f6`):

| Condició d'avui (`tasks/views_b.py:194-208`) | Test que la fixa |
|---|---|
| `open` si `in_progress > 0` (mana sobre tot) | `test_in_progress_mana_sobre_tot` |
| `paused` si `paused > 0` i cap en curs | `test_paused_mana_sobre_pending` |
| `pending` si en queda alguna i res viu | `test_pending_quan_no_hi_ha_res_viu_ni_pausat` |
| `done` **només** si tot és Done | `test_done_nomes_quan_tot_es_done` |
| C4a: sense `planned_start` **el model no hi és** | `test_un_model_sense_cap_tasca_planificada_no_hi_es` |
| per defecte s'amaguen els tot-Done (`?all=true`) | `test_per_defecte_els_models_tot_done_no_es_llisten` |
| filtres: exacte per valor, **lenient** amb l'invàlid | `test_el_filtre_d_estat_del_model_es_exacte` · `test_un_valor_d_estat_invalid_s_ignora_i_no_filtra` |

**Consumidors**: només **un** (`frontend/src/pages/Dashboard.jsx:205` i `:506`, amb `all=true`).
`InformesPanel`/`TimeTree` consumeixen `time-analysis/by-model/`, que és **un altre endpoint**.

> 🚨 **EL PRIMER INTENT D'AQUESTS TESTS SORTIA BUIT AMB 200, I NO ERA EL BOARD: ERA `user.profile`.**
> El perfil el crea un **signal** en néixer l'usuari, i `UserProfile.objects.get_or_create(user=…)`
> en torna un objecte Python **diferent** del que `user.profile` ja té cachejat. El rol escrit a
> la còpia no arribava mai a la request, que seguia veient `technician` i reduïa el scope a «les
> meves tasques» → board buit, amb 200 i sense cap error. (Germà del cas
> [[ftt-j-consulta-no-es-treball]]: `user.profile` CACHEJA.)

---

## 2 · FASE 1 · ELS TRES ESTATS (FIT-9)

`Model.ESTAT_CHOICES` passa a **`nou` · `acabat` · `jubilat`** (`models_app/models.py:105`), i
el camp deixa de ser un vocabulari mort per passar a ser **el cicle de vida**:

- **`nou`** — al tauler. És el model viu.
- **`acabat`** — fora del tauler actiu, **consultable i reoblible**. Només s'hi entra per l'ACTE.
- **`jubilat`** — històric. Fora de les vistes normals, visible **només amb filtre explícit**.

### El que s'hi ha afegit, i per què

| Peça | Per què |
|---|---|
| `Model.motiu_tancament` (`acabat` \| `tret_de_cataleg`) | FIT-10: les dues vies **no són el mateix fet**. Una és decisió interna, l'altra un fet del client |
| `Model.data_tancament` | **Ja existia i NO l'escrivia ningú** (cens): un `DateField` mort que el board ja sabia ordenar. Ara és la data de l'acte — no calia inventar-ne cap de nova |
| `ModelEstatEsdeveniment` | El RASTRE: `de_estat`, `a_estat`, `motiu`, `per`, `quan` |
| 🔒 `estat`/`motiu_tancament`/`data_tancament` a `read_only_fields` | Tanca el forat del cens: el PATCH genèric podia deixar un model `acabat` **sense motiu, sense autor, sense rastre i sense el guard de la ronda oberta** |

**Per què un LOG i no un parell de camps a `Model`.** Tancar↔reobrir passa més d'un cop (el fum
de §7 en fa quatre seguits sobre el mateix model). Amb `tancat_per`/`reobert_per`, cada volta
n'esborraria l'anterior i la pregunta «quantes vegades s'ha reobert això, i qui ho va demanar»
no tindria resposta. És la mateixa forma que `TaskTransition` per a les tasques.

---

## 3 · FASE 2 · TANCAR UN MODEL (FIT-10)

`models_app/services_cicle.py` · `tancar_model(model, *, motiu, profile, confirmar_entrega=False,
destinatari='', descripcio='')`.

### 🚨 Amb ronda oberta, el sistema AVISA i no decideix

```
1a crida  →  CicleVidaError(code='ronda_oberta', dades={'ronda': {...}})  →  HTTP 409
2a crida  →  confirmar_entrega=True  →  UNA transacció:
             informar_entrega(...)  →  tancar_ronda (FIT-13)  →  feina viva tancada (FIT-6)
                                    →  estat='acabat' + motiu + data + rastre
```

🔑 **L'entrega NO es reimplementa: es crida la porta d'M1** (`services_r.informar_entrega`). Amb
això el tancament del model **hereta** FIT-13 (entregar tanca la volta) i FIT-6 (tancar la volta
tanca la seva feina, tasca per tasca i pel mecanisme únic) sense repetir-ne una línia. I per això
el diàleg demana `destinatari`: és el de l'acte d'entrega, i sense ell M1 refusa.

**L'atomicitat, mesurada** (`test_sense_destinatari_no_es_tanca_RES`): amb un rebuig de l'entrega,
la volta segueix viva, el model segueix obert i **no queda cap fila de rastre**. Si el tancament
del model visqués fora de la transacció, hi hauria quedat un model acabat amb la volta oberta a
dins — exactament l'estat que no ha d'existir.

### ✅ La capability: `CLOSE_GATES`, i **no** calia cap TODO

El brief demanava «la de gates/govern que FASE 0 trobi… si no n'hi ha, `_ExecuteTasks` + TODO,
com M1». **N'hi ha, i és inequívoca**: `CLOSE_GATES` és la capacitat de **govern** de la casa —

- `tasks/views_b.py:827` `gate_model_view`, `:853` `regress_model_view` (fase del model),
- `tasks/views_b.py:875` `gate_bulk_view` — *«accions de govern post-reunió»*,
- `fitting/views.py:75` — *«aprovar és un gate, i els gates són decisió humana i gated»*.

Acabar, jubilar i reobrir un model són exactament això. Per rol la tenen **`manager` i `admin`**;
**no** el `technician` ni el `product_manager` (`accounts/capabilities.py:28-36`). L'asimetria amb
l'entrega d'M1 (que va amb `EXECUTE_TASKS`, «qui pot treballar pot entregar») **és volguda**:
entregar una volta és feina; tancar el model tanca la feina viva **d'altri**.

### 🚩 PENDENT D'AGUS — `tret_de_cataleg` i l'entrega

El brief fixa el camí de la ronda oberta **per a les dues vies**, i així s'ha implementat. Però
val la pena dir-ho: **«el client diu que no es produirà» i «li hem entregat la volta» no són el
mateix fet**, i amb `tret_de_cataleg` aquest camí escriu igualment una `Entrega` amb destinatari.

| Lectura | Cost |
|---|---|
| **(A) La d'avui**: les dues vies confirmen entrega | 0 · ja hi és |
| **(B)** `tret_de_cataleg` tanca la volta **sense** entrega (`tancar_ronda(ronda, profile=…)`, que ja tanca la feina viva) | **3 línies** al servei + una frase al diàleg («es tancarà la volta sense declarar cap entrega») + 1 test |

---

## 4 · FASE 3 · REOBRIR I JUBILAR (FIT-11)

- `reobrir_model(model, *, profile, motiu='')` → `estat='nou'`, neteja motiu i data, deixa rastre.
  **No obre cap ronda, no reobre cap tasca i no toca la fase**: només torna el model al tauler.
  Serveix igual per a un `acabat` i per a un `jubilat` — **desjubilar és reobrir**, i partir-ho en
  dos gestos hauria inventat un estat intermedi que ningú no ha demanat.
- `jubilar_model(...)` → **només des d'`acabat`** (un model viu no salta a l'històric sense passar
  per l'acte que té motiu i autor) i **només a mà**: cap automatisme per temporada a la v1.

### 🔒 La paret d'FIT-11 — `hi_ha_volta_posterior` (`tasks/services_c.py`)

El guard viu a `transition_task`, **abans** del d'albarà i saltable amb `force` igual que ell.

> 🚨 **NO ES POT ESCRIURE AMB UN `seq__gt` I PROU**, i aquest és el descobriment de l'sprint.
> `ronda = NULL` són **dues coses ben diferents**: l'històric anterior a la primera volta (feina
> llegada, que la prohibició de backfill d'M1-bis deixa NULL a posta) i **la feina nascuda al BUIT
> entre dues voltes**, que encara no n'ha vist cap de posterior. Amb el predicat ingenu («el model
> té rondes → la tasca sense ronda queda enrere»), tota la feina del buit hauria quedat
> **tapiada**. El que les separa és el **TEMPS**, que és exactament el criteri que
> `services_r.tasques_del_buit` ja fa servir per adoptar-les: és posterior tota volta **oberta
> després que la tasca es creés**.

**FIT-2 segueix intacte i té test propi**: sobre la darrera volta, rectificar és legal i segueix
deixant la nota «reoberta després d'entrega de R{n}». I la paret **només toca la reobertura**:
una `Pending` llegada es pot començar encara que després s'hagi obert una volta — condemnar-la
hauria estat tapiar feina que ningú no ha fet mai.

---

## 5 · FASE 4 · EL BOARD — i una 🚩 ATURADA DECLARADA

### El que s'ha fet

1. **Els models `acabat` i `jubilat` SURTEN del board** — és el que volen dir els dos estats. No
   s'amaga cap dada: **`?estat=acabat` els torna a ensenyar**. L'exclusió és el DEFAULT, no una
   paret (mateix criteri que el `?inclou=` del catàleg: *el que està en ús no s'amaga mai*).
2. **Cada fila porta la darrera volta**: `ronda: {seq, estat}` amb les **tres** que la BD pot
   donar — `oberta` · `entregada` · `tancada` (sense entrega) — i `null` si el model no en té cap.
   Tres subqueries d'una fila: el board segueix sent **una sola consulta**.
3. La 4a columna es diu ara **«Entregats»** i cada targeta pinta el xip `R{n} · …`.

### 🚩 El que NO s'ha fet, i per què (el brief ho autoritza explícitament)

**La CLASSIFICACIÓ de les quatre columnes no s'ha tocat.** El brief demana que la 4a passi a
significar «ronda entregada / esperant retorn» (*darrera volta tancada i cap d'oberta*). Al camí
normal les dues frases descriuen **el mateix conjunt** —entregar tanca la volta (FIT-13) i
tancar-la tanca la seva feina (FIT-6)—, però **hi ha dos casos on no**, i cap dels dos és rar:

| Cas | Què és de veritat | Freqüència |
|---|---|---|
| **(a)** tot Done amb la volta encara **OBERTA** | «acabat, **pendent d'entregar**» | **Alta.** És l'estat de tota volta acabada de treballar. La captura `m3_d1_board.png` en té un a la columna «Entregats»: `QA-M1-0002`, amb el xip `R1 · volta oberta` |
| **(b)** tot Done **sense cap volta** | tot model **llegat** (backfill prohibit fins a M5) | **Molt alta** avui |

Les lectures possibles, amb cost:

| Lectura | Què implica | Cost |
|---|---|---|
| **(A) La d'avui** | 4 columnes; la 4a és «cap feina viva» i el **xip** distingeix els tres casos | 0 · ja hi és |
| **(B) Cinquena columna** «Llest per entregar» | (a) en surt i té columna pròpia; el board passa a 5 | Backend ~10 línies (`kanban_state` + un valor nou al contracte) · Front: columna nova, i **la decisió de què fa la 5a columna en una pantalla que en dibuixa 4** |
| **(C) La 4a estricta** (només amb volta tancada i cap oberta) | (a) i (b) **surten del board** o cauen a `pending` | 5 línies · ⚠️ (b) és la forma de **tot model llegat**: o desapareixen del tauler, o apareixen com a «pendents» sense tenir res pendent |

**No he triat**, que és el que el brief demanava. El que sí que s'ha fet és que la columna pugui
**dir la veritat sense inventar-se cap estat**: amb el xip, «R3 entregada» i «R3 oberta» ja no es
pinten igual.

---

## 6 · LA CARA

| Superfície | Què hi ha de nou |
|---|---|
| **Menú Accions** (fitxa i llista, **un sol model**) | «Tancar model» · «Jubilar model» · «Reobrir model», **excloents** entre si perquè els estats ho són, i gatejades amb `close_gates` — la mateixa que el servidor demana (no s'ensenya-i-403) |
| **El diàleg** | **UN diàleg amb DUES cares**: motiu → (409) → avís amb el número de la volta + destinatari + descripció, i el botó passa a «Confirmar l'entrega i tancar». Dos modals haurien partit en dues preguntes una decisió que és una de sola |
| **Fitxa d'un model acabat** | **Banner** d'estat (amb data, i amb el motiu **només quan diu alguna cosa**) · badge a la capçalera · el **transport** de les targetes i «+ Nova ronda» **se'n van** (no s'apaguen: el camí és reobrir) · la feina i les voltes segueixen **consultables** |
| **`/models`** | ✅ **La 🚩 PROVISIONAL-DOMINI queda RETIRADA.** Les tres vistes són filtres exactes: `curs=nou` · `acabats=acabat` · `jubilats=jubilat`. Per fi és cert que «els elements acabats no es llisten per defecte» |
| **Board** | 4a columna «Entregats» + xip de volta |
| **i18n** | ca/en/es, amb paritat. I **fora les 4 claus del vocabulari mort** (`EnCurs`, `EnRevisio`, `Tancat`, `Nou` velles) |

---

## 7 · EL GATE

### 7.1 · `manage.py check` — net després de **cada** commit.

### 7.2 · Bloc RONDA + els tests NOUS · **`Ran 236 tests` · `OK`** (correguda POST-merge)

```
venv/bin/python manage.py test \
    fhort.tasks.test_ronda fhort.tasks.test_tasca_vigent fhort.tasks.test_contracte_f2 \
    fhort.tasks.test_m1_entrega fhort.tasks.test_m1bis_fit4 \
    fhort.tasks.test_m3_fit11 fhort.tasks.test_m3_by_model fhort.models_app.test_m3_cicle_vida \
    --settings=fhort.settings_m3 --keepdb
```

### 7.3 · Bloc GATES (rutes del R13 per a `services_c` i els gates) · **`Ran 131 tests` · `OK (skipped=1)`**

```
venv/bin/python manage.py test \
    fhort.tasks.test_stop_encadenat fhort.tasks.test_j_consulta_treball \
    fhort.tasks.test_exclusio_handoff fhort.tasks.test_guard_tasca_oblidada \
    fhort.tasks.test_batec_escriptura fhort.tasks.test_batec_sobre_pausada \
    fhort.tasks.test_meritacio_batec fhort.tasks.test_recompute_welford \
    fhort.tasks.test_recompute_d3 fhort.models_app.test_gate_mesures_pom_task \
    fhort.tenants.tests_canal_estat fhort.pom.test_g6_grading_gates \
    --settings=fhort.settings_m3 --keepdb
```

Aquest bloc és el que el R13 marca com a **«assumeixen que `Done→InProgress` és legal»** (§b del
cens), que és exactament el que la paret d'FIT-11 podia trencar. **No en trenca cap**: el guard
només dispara quan existeix una volta POSTERIOR, i cap d'aquells tests en fabrica.

(La correguda de PRE-merge en donava 233; els 3 de diferència són els que M2-codes va afegir a
`test_ronda`. Després del darrer retoc del board s'han tornat a córrer els tres fitxers d'M3:
**`Ran 58 tests` · `OK`**.)

`settings_m3` només canvia el NOM de la BD de test (`test_ftt_m3_cicle`): `test_ftt_staging` és
compartida entre sessions concurrents i cadascuna destrueix la de l'altra.

### 7.4 · Fum HTTP · `ops/qa/qa_m3_cicle_http.py` · **25 OK · 0 FAIL**

```
BASE=http://127.0.0.1:8131 · Host=staging.fhorttextile.tech · banc [QA-M1-0001..0004]
  OK  sense token la porta contesta 401 · un motiu desconegut és 400 amb codi
  OK  la primera crida AVISA amb 409 i el número de la volta …i NO ha tocat res
  OK  en confirmar: 200 · model ACABAT · entrega informada · rastre amb qui i per què
  OK  la volta TANCADA (FIT-13) · cap feina viva a dins (FIT-6) · motiu i data persistits
  OK  tancar dues vegades es rebutja
  OK  un model ACABAT surt del board …però es pot demanar EXPLÍCITAMENT
  OK  reobrir torna el model a OBERT · amb el motiu al rastre · i torna al board
  OK  una tasca d'una volta ANTERIOR ja no es rectifica (409 volta_posterior)
  OK  …i la de la DARRERA volta sí (FIT-2 intacte)
  OK  un model OBERT no es jubila de cop · d'ACABAT a JUBILAT, 200 · surt del board
  OK  la història hi és SENCERA i acumulativa (4 actes)
```

> 🔑 **El fum va trobar que CAP model del banc entra al board**, i era el guard **C4a**
> (`plan_start_all__isnull=False`): el banc fabrica la feina pels **gestos de treball**, que no
> planifiquen res. Sense la fixture que hi posa `planned_start`, **tres mesures haurien sortit
> verdes sense mesurar res** — el mateix parany que
> [[ftt-f4quater-lectura-unificada]] («verd sense mesurar res»).

### 7.5 · Fum de PANTALLA · `ops/qa/qa_m3_cicle_pantalla.py` · **20 OK · 0 FAIL**

Bundle REAL de `frontend/dist` + backend REAL del worktree. **El flux estrella es prem de debò**:
Accions → Tancar model → 409 → l'avís «la R2 està oberta» → destinatari → confirmar.

Captures a `ops/qa/captures/` (gitignorades, al disc):

| Captura | Què hi surt |
|---|---|
| `m3_a1_menu_accions.png` | el menú amb «Tancar model» i **sense** Reobrir/Jubilar |
| `m3_a2_dialeg_motiu.png` | el diàleg amb les dues vies d'FIT-10 |
| **`m3_a3_avis_ronda_oberta.png`** | **el 409 pintat com una PREGUNTA**, amb el número de la volta i el camp de destinatari |
| `m3_a4_tancat.png` · `m3_b1_fitxa_acabada.png` | la fitxa acabada: banner, badge, «RONDA 2 · Entregada», la línia d'entrega i **cap transport** |
| `m3_b2_menu_acabat.png` | el menú, que ara ofereix Jubilar i Reobrir |
| `m3_c1_llista_acabats.png` · `m3_c2_llista_curs.png` | les vistes de `/models` |
| `m3_d1_board.png` | «Entregats» i els xips de volta |

> 🔑 **Dues coses que només es veuen MIRANT la captura**:
> ① el banner deia **«Acabat · Acabat (decisió interna)»** — redundant. Ara el motiu només es
> pinta quan diu alguna cosa (**regla del silenci**): el fet que canvia la lectura és «tret de
> catàleg». ② el fum mateix va mentir un cop comparant «Destinatari» contra un rètol que el CSS
> pinta en **MAJÚSCULES** i que `inner_text` torna transformat — el mateix parany d'M2.

### 7.6 · Front · `npm run build` net · `npx eslint src` → **0 errors** (274 warnings, els mateixos que a l'entrada)

---

## 8 · MIGRACIONS

**`backend/fhort/models_app/migrations/0087_m3_cicle_vida_model.py`** — l'única.

Numeració comprovada **al disc** i a **tots els worktrees vius** abans de generar-la
(`ftt-staging`, `ftt-m1`, `ftt-m3`, `ftt-t7`, `ftt-t9`, `ftt-fixmes`, `ftt-planning`, `ftt-tx`):
el màxim real de `models_app` era **0086** a tot arreu, i el de `tasks` **0052** (M3 no en porta
cap de `tasks`).

Operacions: `RunPython(tot_a_nou)` → `AddField(motiu_tancament)` → `AlterField(estat)` →
`CreateModel(ModelEstatEsdeveniment)`. El revers del backfill és un **no-op declarat**: els valors
vells s'han sobreescrit i no es poden reconstruir.

**Aplicada** (`migrate_schemas`, mai `--schema`) i **verificada amb tenant**:

```
$ venv/bin/python manage.py migrate_schemas
  Applying models_app.0087_m3_cicle_vida_model...
  [M3 · FIT-9] estat → 'nou': 37 model(s) a l'esquema "fhort"
  [M3 · FIT-9] estat → 'nou': 51 model(s) a l'esquema "los"

$ venv/bin/python manage.py tenant_command showmigrations --schema=fhort models_app
  [X] 0087_m3_cicle_vida_model
```

⚠️ També s'hi va aplicar **`patterns.0017_patternpom_cota_offset`**, que ja era a `dev` i estava
pendent a la BD: no és d'aquest sprint, però `migrate_schemas` no en fa tries i queda dit.

---

## 9 · ESTAT DEL BANC I DEL PROCÉS (per a qui hi torni)

- **Banc `[QA-M1]` a `fhort`**: els fums el **consumeixen** (l'entrega tanca la volta i no es pot
  desfer). L'últim estat és el que va deixar el fum de pantalla: **`QA-M1-0004` ACABAT**.
  Per tornar-hi: `cd backend && venv/bin/python ../ops/qa/banc_m1_rondes.py --remunta`.
- **Gunicorn del worktree** a `127.0.0.1:8131` — **aturat** en tancar l'sprint. Per rearrencar-lo:
  ```
  setsid nohup venv/bin/gunicorn fhort.wsgi:application \
      --chdir /var/www/ftt-m3cv/backend --bind 127.0.0.1:8131 --workers 2 --timeout 60 &
  ```
- **`ftt-staging.service` no s'ha reiniciat.** El servei compartit segueix servint `dev` sense M3:
  a la pantalla de staging, el cicle de vida **no es veurà** fins que l'Agus faci el merge i el
  reinici ([[ftt-backend-desplegat-vs-disc]]).

---

## 10 · RESUM DE 🚩 I DECISIONS PENDENTS

| # | Què | On |
|---|---|---|
| 🚩 1 | **La 4a columna del board**: què fa amb «tot Done amb volta oberta» i amb el model llegat. Tres lectures amb cost | §5 |
| 🚩 2 | **`tret_de_cataleg` + ronda oberta**: escriu una entrega. La sortida (B) són 3 línies | §3 |
| 🚩 3 | `frontend/src/components/EstatBadge.jsx` — **component sense cap importador** que el cens va trobar. Candidat a retirar; no s'ha tocat | §1 |
| 🚩 4 | La columna «Estat» de `/models` segueix pintant un guió. Ara que les VISTES filtren per estat, la columna és redundant: o pinta l'estat comercial del Kanban (quan hi sigui) o se'n va | §6 |
| ⚠️ 5 | El brief demanava base `dev` amb M2-codes; `dev` va avançar durant l'sprint i el merge ja s'ha fet **aquí** | §0 |
