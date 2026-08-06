# ARQUITECTURA — estat real del sistema · 2026-08-06 (tarda)

> **Data** 2026-08-06 · **Patró A (READ-ONLY)** per als blocs B i C · **Patró B** només per als
> 7 micro-fixos aprovats del bloc A · staging `/var/www/ftt-staging`, branca `dev`.
> **Base:** `origin/dev` = `dev` = `6d46fa92` (push d'Agus, 12:18 UTC). **Cap push fet.**
>
> **Convenció:** cada afirmació porta `fitxer:línia`. **«NO EXISTEIX» = confirmat absent al codi**,
> no especulat. Les propostes van marcades `💡 (a validar)` i separades dels fets.
> Els números de BD són `SELECT` read-only sobre staging (schemes `fhort` i `los`), avui.
>
> **Equip:** director + 5 investigadors read-only en paral·lel (import · wizards · cicle de tasca ·
> graduació · penjats) + implementador/verificador per al bloc A.

---

## 0 · EL TITULAR

**Hi ha una bomba armada i és de la pantalla que es va estrenar ahir.** La superfície nova de
Graduació escriu regles `origen='MANUAL'`, i **qualsevol `PATCH update-step2` sobre un model amb
joc assignat les esborra totes** — sense 409, sense Watchpoint i sense que l'usuari hagi parlat de
graduació. Ja hi ha **24 regles MANUAL vives a `fhort`, i les 24 estan armades**; 4 d'elles al
MILEY (1308), escrites avui a les 11:08 UTC. Detall a §2.1.

La resta del dia: el bloc A ha entrat sencer (4 commits nous + 2 verificacions), i l'auditoria ha
tornat **3 forats nous que cap document tenia** (F1-bis de graduació, el relleu de tasca sense
exclusió, i `DerivaTarget` derivant `KID_BOY` per a famílies d'adult).

---

## 1 · MAPA DE NODES PENJATS

«Construït però no connectat» o «promès però no fet». Mida `💡 (a validar)`.

### 1.1 · Construït i no connectat

| # | Node | Àncora | Mida | Estat |
|---|---|---|---|---|
| N1 | **`PromoteToItemButton`** — 135 línies, gate CONFIGURE, dry-run + apply | `components/model/PromoteToItemButton.jsx:41` · zero importadors a tot `frontend/src` | **S** | Desconnectat **a posta** (Agus, 06/08). L'acta i el candidat de destí, a `CheckMeasureEditor.jsx:669-680` (`ItemAuthoring`). **Cal decisió d'Agus.** |
| N2 | **`pomAlerts`** — endpoint declarat al client, cap consumidor | `api/endpoints.js:755-757`; `grep pomAlerts frontend/src --include=*.jsx` → **0** | **M** | El model `POMAlert` (`fitting/models.py:116-175`) té `tipus='conflicte'` i `estat='Pendent'` però és el veredicte d'**una mesura**: no té camp per a un codi de client. **No és destí utilitzable per al «pendent» de l'import** (v. §2.3). |
| N3 | **`FittingTab.jsx`** — component definit, cap importador | `components/model/FittingTab.jsx:12` (únic hit del grep) | **S** | — |
| N4 | **Motor de planificació de campanya** — `compute/preview/apply/snapshots` amb backend complet | `api/endpoints.js:426…`; callers → **0** | **L** | El flux viu és `assign-batch` + `reorder`. |
| N5 | **`resol_proposta_graduacio`** — cap vista la crida | `models_app/services.py:218`; únic consumidor `scripts_tmp/g1_probe_proposta.py` | **M** | Codi mort. La pantalla nova **tampoc** l'ha adoptada. |
| N6 | **«Entrada manual» del contenidor de graduació** — botó sí, endpoint sí, **intenció no persistida** | `GraduacioContenidor.jsx:84-104` → `ModelSheet.jsx:1246-1250` | **XS o S** | Al domini **NO EXISTEIX** cap camp «aquest model es gradua a mà». Un F5 la perd fins que s'escriu la primera regla. **Decisió d'Agus** literal a `REPORT_P0_MATI.md:449-460`. |
| N7 | **`ModelFabric.jsx:120` → `/tasques/kanban`** — ruta esborrada | `App.jsx:362-364` (jubilació) · catch-all `App.jsx:417` | **XS** | Enllaç mort. Censat el 04/08 i el 05/08; **segueix viu**. |
| N8 | **4 `TaskType` visibles amb eina i sense pantalla** — `sample_check`, `marking`, `pattern_review`, `scaling` | `destiTasca.js:28-40` (6 parells) vs 15 TaskType al catàleg | **L** | És el contracte declarat (`destiTasca.js:13-16`), no un defecte: 4 targetes que no mouen ningú. |
| N9 | **`ModelGradingOverride`** — model viu, 0 files, efímer per disseny | `models_app/models.py:926` | **S** | Cua de G4. |
| N10 | **`FittingDurationStat`** — declarat mort i **encara s'hi escriu** | `fitting/models.py:498-513` · escriptures a `fitting/services.py:840,857-858` | **S** | Cua de G5. |
| N11 | **`TaskTree.jsx:101-108` avisa per `console.warn`** dels TaskType amb eina i sense ruta | idem | **XS** | Un `console.warn` no és un canal. |

### 1.2 · Promès i no fet

| # | Promesa | Àncora | Mida | Realitat |
|---|---|---|---|---|
| P1 | **El run-label mismatch bloqueja l'import** | `extraction_views.py:906` (`ready`) · `:942-956` | **S** | **HTTP 200 SEMPRE.** Qui bloqueja és el front (`ImportWizard.jsx:424-425`). I `import_session_confirmar_view` **no mira `session.estat` enlloc** → una crida directa a `/confirmar/` amb la sessió a `PENDENT` passa. |
| P2 | **El matcher de l'import valida contra el catàleg del client** | `extraction_views.py:1765` i `:1899` | **M** | Miren **`POMMaster.codi_client`** (el codi de la CASA), global al tenant. `colisio_de_codi`/`pom_del_codi` (`pom/nomenclatura.py:71,90`) **no els crida ningú de l'import**. |
| P3 | **Els POMs neixen amb el seu àlies** | `extraction_views.py:1872` i `:1901` · `pom/wizard_views.py:575` | **S** | **Tres creadors de `POMMaster` sense `CustomerPOMAlias`.** És la fàbrica dels orfes. |
| P4 | **La comprovació prèvia mira el que el motor preguntarà** | `comprovacio_views.py:230-234` | **S** | Mira `ModelGradingRule` a seques — **ni `actiu`** —, no la pregunta de `_load_grading_rules` (`pom/services.py:751`). |
| P5 | **`set_pom_regim_view` és innocu sobre el grading persistent** | `views.py:4609` | — | És un **docstring**, no codi executable. |
| P6 | **El relleu de tasca manté l'exclusió** | `services_c.py:357-365` | **S** | `traspassa_tram` crida `_open_timer`, que només tanca els trams **de la tasca**. El bucle d'exclusió viu a `transition_task:248-260` i **el relleu no hi passa**. |
| P7 | **La cron del guard de tasca oblidada** | command a `tasks/management/commands/pausa_tasques_oblidades.py` | **XS** | `crontab -l` només té la línia de F3.3. **Sense instal·lar** (D-9). |
| P8 | **`reconcile_consumption` programat** | `crontab -l` | **XS** | Mai programat: el backfill dels forats de meritació és manual. |
| P9 | **El paquet LOSAN** | `export_losan_package.py:298,308` · `load_losan_package.py:419,422` | **XS** + **M** | Trencat les **dues bandes** pel FK `GradingRuleSet.target` (retirat a `pom/0043`; avui és M2M `targets`). `find / -name 08_rulesets.json` → **0 resultats**: mai s'ha exportat des del canvi. |
| P10 | **TimeSeed com a graó 3 de l'estimació** | `services_g.py:39-45` | **S** | `fhort` 8 seeds / 15 TaskType · **`los` ZERO**. Els 7 sense seed cauen al graó 4 = `None`. La precondició **no és al runbook** (`grep -c TimeSeed RUNBOOK_PROD_CICLE_TASCA.md` → 0). |
| P11 | **Credencials QA** | — | **S** + **M** | `fhort` té **1 sol `UserProfile`**. Els 12 fums corren amb l'API **estubada** i `localStorage.access_token='qa'`. **La prova de 2 tècnics no es pot córrer avui.** |
| P12 | **`sample_check` amb i18n** | `frontend/src/utils/taskType.js:6` | **XS** | Falta `tasktype.sample_check` als 3 idiomes; cau al `defaultValue` («Sample check», idèntic als 3). **Deliberat**: el nom depèn de la pantalla aparcada. |
| P13 | **El retorn del modal (`tabDeRetornRef`) verificat** | `ModelSheet.jsx:305,369,553-554,690` | **S** | ❌ **NO verificat a pantalla**, i el seu autor ho deixa escrit al commit `c5e130de`. A més **no és observable per URL** (`activeTab` no s'hi escriu, `:178`): qualsevol fum futur ha d'assertir sobre el tab actiu al DOM. |
| P14 | **`destiTasca` com a resolutor únic** | `destiTasca.js` | **L** | **2 consumidors de ~20 camins** (`TaskTree.jsx`, `WorkPlan.jsx`). V. §2.6. |

---

## 2 · RISCOS VIUS — ordenats per «pot mossegar demà al matí»

### 2.1 · 🔴🔴 EL WIPE DE GRADUACIÓ ESBORRA LES REGLES MANUAL — **el primer de la llista**

**Veredicte: SÍ.** `materialize_model_grading_rules` fa `model.grading_rules.all().delete()` **sense
cap filtre** (`models_app/services.py:266`; bessó a `:294`), i la pantalla nova escriu
`rule.origen='MANUAL'` incondicionalment (`models_app/views.py:4694`).

**Prova formal ja al repo:** `models_app/tests_sembra_grading.py:1332-1345` — 1 MANUAL + 1 IMPORTED
→ després del 200, `residents_esborrades: 2`.

**Dades vives (`fhort`, avui):** 4.783 `ModelGradingRule` · **24 amb `origen='MANUAL'`** · i **les 24
viuen en models amb joc assignat**, o sigui **totes armades**. Model 186 → 20 MANUAL (el 100 % de
les seves residents). **Model 1308 (MILEY) → 4 MANUAL** (v. §4.1).

**🔴 F1-bis — el forat nou, que ningú havia censat:** el consentiment i la destrucció miren coses
diferents.

| | predicat | on |
|---|---|---|
| el 409 que demana permís | `d.get('grading_rule_set_id')` — **el PAYLOAD** | `views.py:1049` |
| la re-materialització que esborra | `model.grading_rule_set_id` — **l'ESTAT DEL MODEL** | `views.py:1071` |

El destructiu és el **més ampli**. Conseqüència: **qualsevol `PATCH update-step2` sobre un model amb
joc — encara que no parli de graduació — reescriu les residents i mata les MANUAL en silenci.**

**Camí mut, reproduïble sense tocar el contenidor de jocs:**
1. `?mode=graduacio` → editar un delta → Gravar (`GraduacioSuperficie.jsx:201`) → resident MANUAL.
2. «Editar model» (`ModelSheet.jsx:1233`) → tocar qualsevol eix fins que el joc hidratat deixi de
   ser `strictMatch` → `ModelWizard.jsx:405` fa `setGradingRuleSetId(null)`.
3. `skeletonPayload()` (`:412`) retorna `grading_rule_set_id: undefined` → **la clau desapareix del
   JSON** → `views.py:1049` fals (**cap 409, cap Watchpoint**) però `views.py:1071` cert → **wipe**.

Variant equivalent: marcar «Sense graduació» → `views.py:1041-1043` esborra-ho tot, 200 OK, mut.

**Cap dels dos guards que caldrien existeix:** ni filtre d'`origen` al delete, ni guard de segell a
l'escriptura de regla (editar la regla d'un model amb `GradingVersion.aprovada=True` retorna **200**
i la deixa divergint del segell).

### 2.2 · 🔴 EL BLUR DE LA REGLA FABRICAVA AUTORIA HUMANA — **tancat avui (commit 67)**

`RegleEditCell` (`CheckMeasureEditor.jsx:142`) desava a **cada `onBlur`**, canviés el valor o no. I
`set_pom_regim_view` no és un update innocu: si la resident no existeix la **materialitza des del
fallback del catàleg** i li estampa `origen='MANUAL'` (`views.py:4639-4695`). **Tabular per la
columna de Règim convertia patrimoni heretat en autoria humana, fila per fila** — i a més forçava
`logica:'LINEAR'` sobre files que n'heretaven una altra.

> **Aquesta és, amb tota probabilitat, l'explicació de les 4 MANUAL del MILEY** (§4.1). Arreglat al
> commit `61f938cf`; **el dany a dades ja fet NO s'ha tocat** (règim de tarda: read-only a dades).

### 2.3 · 🔴 EL CAMÍ D'IMPORT ESCRIU AL CATÀLEG SENSE MIRAR EL CATÀLEG DEL CLIENT

- **Quatre resolutors codi→POM independents** al backend: `find_pom_master`
  (`extraction_views.py:986`), `pom_del_codi` (`nomenclatura.py:71`), el del xat IA
  (`views.py:2589`) i el de la fitxa de proveïdor (`tech_sheet_views.py:348`, per `pom_global__codi`).
- **Tres creadors de `POMMaster` sense àlies** (P3) i, a més, `maybe_learn_customer_alias`
  (`pom/services.py:618`) té un guard **de l'eix invers**: mira si el POM ja el reclama un altre
  codi, no si el codi ja és d'un altre POM. Quan xoca, **no bloqueja**: neix `pendent_revisio=True`.
  I a `:673-679`, si l'àlies existeix apuntant a un altre POM, **el reapunta en silenci**.
- **`set_measurements_view:2014` escriu `nom_fitxa` sense `colisio_de_codi`** — el forat que ja
  anotava `REPORT_POMS_CATALEG_CLIENT.md:127-128`.
- **Dimensionament de connectar-hi el resolutor** `💡 (a validar)`: 2 fitxers de backend + 1 de
  frontend + i18n, **~65-90 línies** (repartiment detallat a l'informe B1).
- **⚠️ `D-31.27` NO EXISTEIX al repo.** `grep -rn "D-31\.2[0-9]"` troba D-31.21, D-31.22 i D-31.26.
  La llei que el brief cita no té text versionat contra el qual contrastar la implementació.
- **Forats de la connexió, per ordre de gravetat:**
  1. **On desar el «pendent» no està resolt.** L'estat de conflicte del pas 2 viu dins
     `ImportSession.poms_extrets` (`extraction_views.py:1184-1193`) i **mor amb la sessió**.
     `POMAlert` no serveix (v. N2); `Watchpoint` és de model, no de catàleg.
  2. **La descripció no té resolutor invers.** `pom_del_codi` només mira `client_code`; les
     descripcions viuen a `CustomerPOMAlias.description_en/local` (`pom/models.py:511-513`) i no les
     consulta cap resolutor. **Falta la meitat «descripció» del parell** que la llei demana.
  3. `find_pom_master` estratègia (a) ja compara la **descripció contra el camp de CODI**
     (`:1029`): convergir sense adonar-se'n canviaria semàntica.
  4. `es_instancia` (`pom/models.py:531-537`) **no la llegeix cap matcher**: connectar el resolutor
     sense implementar-la faria que germanes auto-vinculessin al pit.

### 2.4 · 🔴 EL PLA DELS 93 ORFES NO ÉS EXECUTABLE TAL QUAL

`backend/scripts_tmp/neteja_codis_duplicats.py` (140 línies, dry-run per defecte, `APLICA=1` dins
`atomic`). Validat contra **7 casos llegits a mà**. És **operativament segur** (no esborra, no
fusiona, no reapunta `pom_id`) i **semànticament fals**:

| xifra | avui | al report del matí |
|---|---|---|
| orfes | **93** | 93 ✅ |
| reparables | **37** | 32 🔴 |
| sense amo | **56** | 61 🔴 |

- **El pla no és estable en el temps**: la partició depèn de `BaseMeasurement(is_active=True)`, i 5
  orfes han guanyat mesures vives des del matí. **La mateixa comanda dona un pla diferent segons
  quan es corre.**
- **La premissa del capçal és falsa per a 76 de 93.** L'script diu (`:21`) que els va crear
  `extraction_views.py:1901`; **només 17 tenen `origen_import`**, i 74 tenen `pom_global` (són
  catàleg canònic sembrat que mai ha rebut nomenclatura de client).
- **6 reparacions inventen un codi que el client no fa servir.** POMs 440/436/439/441/442/443, tots
  BRW, tots del **mateix token d'import** `4e79eb3f-…`: el pla els proposa `U1-2`, `D-2`, `U-2`,
  `P-2`, `P1-2`, `LZ-2` quan **el document de Brownie diu `U1`, `D`, `U`…**. La contradicció real
  queda enterrada sota un sufix. **És UN incident, no sis.**
- **31 de les 37 reparacions declaren que el codi de la CASA és el codi del CLIENT** — exactament la
  confusió que el tram del 06/08 existeix per matar. Exemple llegit: POM 281 `BL HPS`, 11 mesures
  BRW, sense `origen_import` → el pla crearia un àlies dient que **Brownie n'hi diu «BL HPS»**.
- Forats tècnics: `codi_lliure` pot retornar `(None, xoc)` i el dry-run imprimeix
  `client_code='None'` mentre l'aplicació el salta en silenci (`:53-57,113,133-134`);
  `colisio_de_codi` filtra `pom__isnull=False` però la constraint no (`pom/models.py:543-546`) → un
  àlies amb `pom=NULL` faria caure **el lot sencer** per `IntegrityError` dins l'`atomic` (avui hi ha
  0 àlies així: latent); `origen='MODEL'` i `description_en=p.nom_client` per a tots (`:137`).

### 2.5 · 🟠 EL RELLEU DE TASCA DEIXA UN TÈCNIC A DOS LLOCS ALHORA (forat nou)

L'exclusió mútua **ja no està trencada** com deia la memòria: `fd633753` (05/08) la va tancar per la
porta de `transition_task` (`services_c.py:248-260`), amb l'eix correcte (`TimerEntrada.tecnic`, no
`assignee`). **Però el relleu no hi passa**: `claim_task_view` (`views_b.py:523`) i la branca `elif`
d'`open-task` (`views_b.py:598-608`) criden `traspassa_tram` **sense transició**, i `_open_timer`
(`:22-30`) només tanca els trams **de la tasca**. Un tècnic amb feina oberta que claima la tasca
d'un altre acaba amb **dos trams oberts** → el temps torna a ser imputable a dos llocs alhora i
contamina el Welford. `test_exclusio_handoff.py` no ho cobreix (els 5 tests de handoff parteixen
sempre de B **sense** trams propis). **No verificat per execució: falta el 2n tècnic.**

El **guió executable de la prova de 2 tècnics** (5 blocs + neteja, per HTTP contra el gunicorn viu,
amb l'esperat i el «què significa un fallit» a cada pas) està escrit sencer a l'informe B3 d'aquesta
sessió. Precondició: crear un 2n `UserProfile` amb `execute_tasks` (escriptura → Agus).

### 2.6 · 🟠 EL DESTÍ DE TASCA: 2 CAMINS DE ~20 PASSEN PEL RESOLUTOR

Tres famílies de bypass:
1. **La ruta de `fitxa/document` no és la que `SUPERFICIES` diu.** El resolutor retorna
   `/models/:id/fitxa?task_id=` (`destiTasca.js:35`), però la pantalla real és
   `/models/:id/ftt/:fitxerId` — `/fitxa` és un **resolver** (`App.jsx:132-205`). **Quatre** llocs
   construeixen la ruta final a mà: `App.jsx:153,174,202` i `ModelSheet.jsx:432`.
2. **El tab Mesures té el seu propi mapa `tab→code`** (`ModelSheet.jsx:1043-1133` cablejat +
   `CODE_PER_TAB` a `:608`). Un TaskType nou amb pantalla s'ha de donar d'alta **als dos llocs**.
3. `ModelFabric.jsx:120` navega a una ruta morta (N7).

### 2.7 · 🟠 EL WIZARD DERIVA `KID_BOY` PER A FAMÍLIES D'ADULT (forat nou)

`DerivaTarget` (`ModelWizard.jsx:737,1037-1053`) agafa el primer perfil de
`sizing-profiles/?garment_type=` **sense `customer_codi`**, amb l'ordre de `pom/s2_views.py:112-118`.
Simulat amb dades vives:

| família | items | perfils | **target derivat en silenci** | targets que la família serveix |
|---|---|---|---|---|
| `JERSEY_TOPS` | 4 | 6 | 🔴 **`KID_BOY`** | KID_BOY, KID_GIRL, **MAN**, TEEN_BOY, TEEN_GIRL, **WOMAN** |
| `TAILORED_PANTS` | 6 | 5 | 🔴 **`KID_BOY`** | KID_BOY, **MAN**, TEEN_BOY, TEEN_GIRL, **WOMAN** |

→ triar una samarreta o uns pantalons de sastre **sense marcar target** dona `KID_BOY`, i llavors el
pas 3 preselecciona `KIDS_AGE_COM` (base **7**, BRW) o `BOY_LOS_01` (base **6**, LOS). **És el camí
exacte del model 1307.** El wizard no va inventar el target: **el va derivar del catàleg.**

Al costat, la preselecció del pas 3 (`ModelWizard.jsx:268,307-308,912-929`): `PROP_TARGET.SENSE = 1`
posa un sistema **sense cap target declarat** per davant dels que en declaren d'altres, i
`TGIRL-EU-HEIGHT` (targets buits, 8 etiquetes d'alçada de nena) guanya per a **MATERNITY** i
**UNISEX_ADULT** → base derivada **152**. **Armat però no disparable pel flux normal**: aquests dos
targets tenen **0 items visibles** al pas 2. Sí ho és per URL directa a `?block=3` o editant un
model importat.

### 2.8 · 🟠 `los` ÉS UN TENANT SENSE EIXOS

0 `Target` · 0 `GarmentGroup` · 0 `SizingProfile` · 0 `GradingRuleSet` · 1 família · 1 item · i els 2
`SizeSystem` actius **amb 0 `SizeDefinition`**. Conseqüències verificades: el pas 3 filtra
`talles.length > 0` (`ModelWizard.jsx:265`) → **la llista surt sempre buida**; i
`nextBlocat` (`:512`) **no bloqueja mai** → s'hi pot crear un model sense sistema, sense run i sense
base. Els 51 models existents porten `target NULL` i run `S·M·L·XL` amb un sistema que no coneix cap
d'aquestes etiquetes: **van entrar per sembra, no pel wizard** (la porta única S24b,
`models_app/views.py:747-764`, els hauria rebutjat).

### 2.9 · 🟠 9 `SizingProfile` amb el target FORA dels targets del seu sistema

3 d'ells en una família **ACTIVA**: `SWEATSHIRTS_MIDLAYERS` declara `BABY_GIRL`/`BABY_BOY`/`KID_BOY`
sobre `GIRL_LOS_03`, que només diu `KID_GIRL` (perfils 519, 520, 522). **NO EXISTEIX cap validació
creuada**: `SizingProfile` no té `clean()` ni constraint (`pom/models.py:1480-1533`).

### 2.10 · 🟠 Dues portes de criteri OPOSAT per al mateix acte d'escriptura

`GraduacioPanel` (estricte: exigeix `size_system` i FIT, `:114-131`) i `GraduacioContenidor`
(eliminatiu: ordena i no exclou res, `:8-27`) fan tots dos el mateix `PATCH update-step2
{grading_rule_set_id}`. **No és un bug: és una bifurcació de doctrina** (el segon la documenta com a
decisió d'Agus del 06/08) que cap document recull.

---

## 3 · LA LLISTA DE DEMÀ

### 3.1 · Es pot tocar sense esperar ningú (ordre d'execució)

| # | Peça | Àncora | Mida | Per què primer |
|---|---|---|---|---|
| 1 | **Filtrar el delete de residents per `origen`** — i **alhora** alinear el predicat de `views.py:1071` amb el de `:1049` | `services.py:266` i `:294` · `views.py:1071` | **S** | §2.1. Són **dos** predicats, no un: tocar només el filtre deixa F1-bis viu. |
| 2 | **Esc al modal de confirmació de desfer** — el germà del que es va arreglar al commit 57, nascut després | `EditableTable.jsx:959` (vel `fixed inset:0` sense handler) | **XS** | La llei del commit 57 diu «cap modal de la casa pot ser un cul-de-sac de teclat»; aquest ho és. |
| 3 | **L'enllaç mort `/tasques/kanban`** | `ModelFabric.jsx:120` | **XS** | Censat dos dies seguits. |
| 4 | **Instal·lar la cron de `pausa_tasques_oblidades`** | `crontab` | **XS** | D-9. Avui 0 trams oberts: sense zombis, però sense xarxa. |
| 5 | **LOSAN: treure les 4 referències al FK `target`** | `export_losan_package.py:298,308` · `load_losan_package.py:419,422` | **XS** | Desbloqueja l'export; la re-verificació del paquet és **M** a part. |
| 6 | **`Δ break` / `Delta break` d'`es.json`** (i el `Talla break` que queda al **ca**) | `es.json:2592,3271,3273` · `ca.json:2593,3272,3274` | **XS** | Avui s'ha fet «Talla break» → «Talla de ruptura» (A5); el mateix anglicisme queda al delta i al català, que ja té «trencament» a `:2262`. |
| 7 | **Guió de la prova de 2 tècnics → fitxer executable** a `ops/qa/` | informe B3 | **S** | Ja està escrit; només falta bolcar-lo (i les credencials, que són d'Agus). |
| 8 | **`comprovacio_views.py:230-234`: preguntar el que preguntarà el motor** (i filtrar `actiu`) | idem vs `pom/services.py:751` | **S** | Latent avui (0 models en fallback pur), incorrecte sempre. |

### 3.2 · Necessita decisió d'Agus abans de tocar res

| # | Decisió | Per què no la pot prendre un agent | Àncora |
|---|---|---|---|
| D1 | **Què fem amb les 24 regles MANUAL vives** — i en particular **amb les 4 del MILEY escrites avui a les 11:08** (§4.1): es reverteixen, es donen per bones, o es congelen? | És dany a dades sobre el model que l'Agus està entrant. **No s'hi ha tocat.** | §4.1 |
| D2 | **Wipe de graduació: quina de les tres** — deixar-lo, protegir les MANUAL, o no materialitzar (decisió 6.1 de `DIAGNOSI_REGLES_DEL_MODEL.md`, oberta) | Canvia el contracte del canvi de joc. | §2.1 |
| D3 | **Els 93 orfes**: el pla actual **no es pot córrer**. Cal decidir si (a) es repara només l'incident real del token `4e79eb3f-…` (6 POMs, 1 import), (b) què es fa amb els 31 que només tenen el codi de la casa, i (c) si un POM canònic sense cap client ha de ser trobable (els 56 «sense amo»). | Són 3 preguntes de domini, no de codi. | §2.4 |
| D4 | **`D-31.27`**: la llei no existeix versionada. Cal escriure-la abans d'implementar-la. | — | §2.3 |
| D5 | **Credencials QA**: dues contrasenyes (o `bootstrap_tenant --password`) per a 2 identitats amb `execute_tasks`. `Marta` i `qa.loginunic@fhort.test` ja existeixen a `fhort`. | Escriptura d'usuaris. | §2.5 |
| D6 | **TimeSeed**: quins minuts. Els seeds vius menteixen (`pom` 35 vs 72,4 mesurats ×2,1 · `tech_sheet` 45 vs 553,5 ×12,3) i falten 7 a `fhort` i 15 a `los`. | Números de negoci. | P10 |
| D7 | **`Paused→Done`** segueix prohibida (`services_c.py:13-15`), decisió del 28/07 amb un intent revertit. | — | — |
| D8 | **El guard pausa per DURADA, no per inactivitat** (`GuardTascaOblidada.jsx:27-29`, 30+3 min a producció). | Decisió Patró C ja presa; cal confirmar que segueix valent. | — |
| D9 | **`PromoteToItemButton`**: `ItemAuthoring` o acció de menú del model. | — | N1 |
| D10 | **«Entrada manual»**: camp nou + migració (i restart), o acceptar que comença amb la primera regla. | Literal a `REPORT_P0_MATI.md:460`: «És decisió teva». | N6 |
| D11 | **`los`**: els 51 models amb `target NULL` i run que el seu sistema no coneix són runa d'assaig o dades bones? | — | §2.8 |
| D12 | **Les dues doctrines de tria de joc** (estricte vs eliminatiu) conviuen o convergeixen? | — | §2.10 |

### 3.3 · Diagnosis a segellar

- `DIAGNOSI_G6_DUAL_PATH.md` (13/07) viu a l'arrel com a vigent i té afirmacions ja superades (p.ex.
  el gate del punter, avui tancat per `_te_regles`, `pom/services.py:712-719`). **Candidata a
  `arxiu/`.**
- `DIAGNOSI_TAXONOMIA.md`: **acabat** (7 blocs + R1-R14 + 12 decisions), amb **3 forats declarats** i
  **5 correccions** trobades avui — v. §4.3.

---

## 4 · SORPRESES

### 4.1 · 🚨 El MILEY té 4 regles MANUAL escrites AVUI a les 11:08:05 UTC

El model **1308** ha passat de 114 a **117 residents**. Tres files són noves (ids 12106-12108, POMs
744/745/746, `created_at` = `updated_at` = 11:08:05) i una (id 11919, POM 326) va néixer
`CLIENT_RUN` a la materialització de les 09:39:21 i **es va convertir a MANUAL** a les 11:08:05.

**No ve d'aquesta sessió** (l'auditoria és read-only i el bloc A no ha escrit a cap model). El
candidat més probable és el defecte de §2.2 — `RegleEditCell` desant a cada `onBlur` —, arreglat
avui. L'altre candidat és una sessió concurrent. **No s'hi ha tocat res: el MILEY és intocable i què
se'n fa és D1.**

### 4.2 · L'exclusió mútua per tècnic ja NO estava trencada — i el forat és a l'altra porta

La memòria del projecte deia «està trencada». `fd633753` la va tancar el 05/08. **El que està obert
és el relleu** (§2.5), que és un camí diferent i que cap document tenia. La premissa antiga hauria
fet buscar al lloc equivocat.

### 4.3 · Cinc correccions al `DIAGNOSI_TAXONOMIA.md` d'aquest matí

| # | El doc deia | El codi d'avui diu |
|---|---|---|
| C1 | `CascadeFinder` és **excloent per defecte** (`compat=null`) | **L'únic consumidor viu passa `compat={{construction, fit}}`** (`ModelWizard.jsx:619`), un objecte mai null → **el pas 2 corre en mode ANOTAT**. El default excloent és codi mort. |
| C2 | **31 items** invisibles | **30.** La pròpia llista del doc suma 30. |
| C3 | 31 items invisibles **al pas 2** | **Al pas 2 no en desapareix cap** (per C1). El filtre excloent bita a `ModelWizard.jsx:166`, `ItemAuthoring.jsx:307` i `GradingRuleSets.jsx:232`. **El dany real és un altre:** 4 targets de 13 (MATERNITY, UNISEX_ADULT, NEWBORN_BOY, NEWBORN_UNISEX) deixen el catàleg **BUIT**. |
| C4 | `:307` substitueix el run en silenci | Des de F1.2 hi ha guard (`:306`) i confirmació (`:317-323`) en **canviar** de sistema. **La preselecció inicial (`:268`) i la derivació de la base (`:308`) segueixen sent silencioses.** |
| C5 | cens de superfícies | **2 superfícies noves** que TAX no podia veure: `GraduacioContenidor.jsx` i `GraduacioSuperficie.jsx`. |

**La predicció de TAX §5.1 era correcta:** la simulació sobre el bundle d'avui dona
`KIDS_AGE_COM`/11 talles/base **7** per a BRW i `BOY_LOS_01`/9/base **6** per a LOS.

### 4.4 · El billing «parkejat» no està a mig fer: corre amb dades vives

45 `ModelConsumptionEvent` i 3 `Invoice` a `public`; 23 models meritats a `fhort`. L'aparcament és
una línia de `DECISIONS.md:834`, no un tros de codi inacabat. **Hi ha 45 events per a 23 models
meritats**: `clone_model_for_qa.py:83` despulla `consumption_started_at` sense esborrar l'event de
`public`, i el receiver només és idempotent per `opaque_ref`.

### 4.5 · El «pendent» que la llei d'import demana no té on viure

Tres candidats i cap encaixa: la sessió (mor amb ella), `POMAlert` (és el veredicte d'una mesura, i
**no té UI**), `Watchpoint` (és de model, no de catàleg). **Implementar la llei D-31.27 vol dir
decidir abans on es desa un conflicte de nomenclatura que ha de sobreviure la sessió.**

### 4.6 · El pas 3 no bloqueja mai a `los`, i la porta única l'hauria rebutjat

Els 30-51 models de `los` porten un run que el seu propi sistema no reconeix. **No van entrar pel
wizard.** La porta única S24b existeix i funciona; el forat és que la sembra no hi passa.

### 4.7 · Els 6 «duplicats» de POM són **un** incident

Els 6 xocs del pla de neteja vénen **tots** del mateix token d'import `4e79eb3f-…`, tots de Brownie,
tots amb 1 mesura viva. El pla els tracta com sis reparacions independents; **són un import mal
resolt**. Revisar aquell import és més barat i més honest que inventar sis codis.

---

## 5 · QUÈ S'HA TOCAT AVUI (bloc A) — 4 commits nous

| commit | peça | verd |
|---|---|---|
| `61f938cf` | **A2** · el blur de la regla no és una intenció de desar: sense canvi, cap escriptura; i cap règim per defecte | eslint 0 errors (mateix perfil d'alertes que HEAD) · build net |
| `ae906ef9` | **A5** · `es.json`: «Talla break» → «Talla de ruptura» (la casa ja en diu ruptura a `:2262`) | `json.load` net · build net |
| `993c5a70` | **A6** · `MeasureGrid` i `ComprovacioPanel` al hook `useEstatDiccionari`; l'avís es unifica a `components/ui/AvisDiccionari.jsx` (3 superfícies, 1 avís) | eslint 0 errors · build net · fums **P0.2 verd** (inclòs el cas «diccionari CAIGUT»), **P0.7 verd**, **P0.1 verd** |
| `43f8bd91` | **A7** · l'AFEGIR del xat de mesures passa per `_procedencia_de_mesura`: tres portes, una sola llei | `manage.py check` net · `test_origen_no_es_efecte_secundari` 5/5 · 33/33 a les 3 suites veïnes |

**A1 · QA2 ja estava tancat** pels commits 58-66 d'Agus (toggle píndola `1ce624f8`+`6d46fa92` ·
família Graduació `deda3953`+`cba542b9` · reconciliació de la presa `8c50246b` · acta neta
`2d5adc89`), amb paritat i18n ca/en/es verificada.
**A3 i A4 ja estaven fets** al commit `50532594` (57) — **verificats a pantalla** amb
`qa_p08_pom_propi.py`: `↓`+`Enter` i Esc verds als **3 idiomes**.

**Backend reiniciat** (`systemctl restart ftt-staging`) perquè el bloc A hi va tocar; les dues rutes
afectades responen **401 sense credencial = vives**.

**Cap push.** **Cap escriptura a dades.** **El MILEY no s'ha tocat.**

---

## 6 · TAULA FINAL DE RISCOS

| risc | pot mossegar demà? | mida del fix | bloquejat per |
|---|---|---|---|
| Wipe esborra les MANUAL (+ F1-bis) | 🔴 **SÍ, avui mateix** | S (2 predicats) | D2 |
| Dany ja fet al MILEY (4 MANUAL) | 🔴 **ja mossegat** | — | D1 |
| Blur de la regla fabricant MANUAL | ✅ **tancat avui** | fet | — |
| Import escrivint al catàleg sense catàleg de client | 🔴 sí, a cada import | M (~65-90 línies) | D4 + on desar el «pendent» |
| Pla dels 93 orfes | 🟠 només si algú el corre | — | D3 |
| Relleu de tasca sense exclusió | 🟠 sí, amb 2 tècnics | S | D5 (per provar-ho) |
| `DerivaTarget` → KID_BOY en adults | 🟠 sí, a cada model nou sense target | S | — |
| `TGIRL-EU-HEIGHT` (base 152) | 🔵 armat, no disparable pel flux normal | S | — |
| `los` sense eixos | 🟠 sí, si algú hi crea un model | M | D11 |
| 9 `SizingProfile` incoherents | 🟠 3 en família activa | S + validació | — |
| LOSAN trencat | 🔵 no mossega, bloqueja | XS + M | — |
| TimeSeed incomplet | 🟠 el dia del deploy | S | D6 |
| Cron del guard sense instal·lar | 🟠 sí, amb un tram oblidat | XS | — |
| `tabDeRetornRef` no verificat | 🔵 baix | S (fum al DOM) | — |
| `destiTasca` amb 2 de ~20 camins | 🔵 deute, no risc | L | — |
