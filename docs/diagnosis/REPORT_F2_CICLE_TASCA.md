# REPORT F2 · LA UI DEL CICLE DE TASCA

Data: **2026-08-05** · **Patró B** · staging `/var/www/ftt-staging`, branca `dev`
Base: `733024f8` → **HEAD `bddfb297`** · **9 commits · CAP PUSH**
Anteriors: `docs/diagnosis/REPORT_F1_CICLE_TASCA.md` · `DIAGNOSI_PREF1_CICLE_TASCA.md`

**Verificació:** estreta per fitxer, mai cap suite. **137 tests de frontend** (`node --test`) +
**55 tests de backend** en 3 fitxers concrets, tots verds. `npm run build` net abans de cada
commit de frontend; `manage.py check` net abans de cada commit de backend.

---

## 0 · DUES PREMISSES DEL BRIEF ERAN FALSES

Es diuen primer perquè condicionen com s'ha de llegir la resta.

| El brief deia | El terreny deia |
|---|---|
| «Base: HEAD després del **push** de F1» | **F1 no s'ha pushat.** `origin/dev` és a `3692db68`; el local anava **28 commits per davant**. No hi havia res a re-pullar: el local ÉS l'estat més nou. |
| «41b875e0 **+ micro-commit S-13**» | **El micro-commit no existia.** `services_scheduling.py` encara resolia amb `.exclude(status='Done').order_by('-id').first()`. |

**Decisió presa:** com que S-13 és una línia que el report de F1 ja havia diagnosticat i que F2
assumeix feta, s'ha fet **com a primer commit del tram** (`f1edfbb3`) per deixar la base tal com
el brief la descrivia. La resta del tram surt d'aquí.

El `git fetch` es va fer igualment i es va comprovar que el territori compartit
(`ModelSheet.jsx`, `App.jsx`, `index.css`) **no tenia canvis d'altri**: només dos fitxers de
settings temporals sense committar.

---

## 1 · ELS NOU COMMITS

| Fase | Commit | Títol |
|---|---|---|
| — | `f1edfbb3` | S-13 · el quart resolutor divergent, al resolutor únic |
| F2.0 | `a1ca59b2` | el contracte que F1 va construir i no va exposar |
| F2.1 | `bed64468` | el modal de tres cares, i la regla d'or que el manté callat |
| F2.2 | `e00efeea` | Previsualitzar i Modificar deixen de ser el mateix botó |
| F2.3 | `ae0a5c2a` | el gest d'acabar, visible i separat de desar |
| F2.4 | `53f9f19d` | el rellotge segueix el tècnic quan canvia d'eina |
| F2.5 | `8d7c815a` | les hores del patró a mà deixen de no existir |
| F2.6 | `788034f1` | /temps deixa d'ensenyar zero a qui ha treballat vuit hores |
| F2.7 | `bddfb297` | el PM veu quins models ja han lliurat |

---

## 2 · F2.0 · EL CONTRACTE DE DADES

**Auditoria primer.** F1 va crear la genealogia, la paret d'albarà, el batec i l'exclusió per
trams — i `ModelTaskSerializer` seguia sent el de Sprint B: **no n'exposava res**.

| Necessitat de F2 | Hi era? | Solució |
|---|---|---|
| tasca vigent per superfície | ❌ | `es_vigent` (resolt amb `tasca_vigent`, mai al client) |
| ronda oberta (seq) | ❌ | `ronda_seq` a la tasca · `ronda_oberta` al model |
| tasca albaranada | ❌ | `albaranada` (precalculat, no només el 409) |
| qui la té oberta ara | ❌ | `obert_per` / `obert_per_nom` — **del TRAM, no de l'`assignee`** |
| `es_lliurable` + estat de la ronda | ❌ | `es_lliurable` a la tasca · `lliurable_ronda_n` al model |
| admet temps declarat | ❌ | `tipus_extern` |

**Cap endpoint nou:** tot camps derivats read-only sobre el que ja hi havia.

**Àncores finals:** [tasks/serializers_b.py:15-120](../../backend/fhort/tasks/serializers_b.py#L15) ·
[models_app/serializers.py](../../backend/fhort/models_app/serializers.py) (`ronda_oberta` al
detall, `lliurable_ronda_n` al detall **i a la llista**).

**Verificació:** `tasks/test_contracte_f2.py` (14). El test que més importa és
`test_obert_per_diu_qui_hi_es_DE_DEBO_no_qui_la_te_assignada`: si el contracte digués `assignee`,
el modal acusaria la persona equivocada — és la lliçó de F1.5 convertida en garantia.

---

## 3 · F2.1 · EL MODAL DE TRES CARES

**Una peça, tres cares** (`ObrirTascaDialog.jsx`), i la decisió pura a
[utils/caraObrirTasca.js](../../frontend/src/utils/caraObrirTasca.js) — **15 tests**.

**REGLA D'OR, i és el primer que el fitxer de test fixa:** el modal **no surt** quan qui obre és
qui la té assignada (o no la té ningú), la tasca no és Done i no és albaranada. Zero fricció,
zero clics.

**Precedència no arbitrària:** `ALBARANADA > LLIURADA > CONFLICTE`. Una tasca albaranada amb algú
a sobre segueix sent, primer de tot, intocable — oferir «treballar-hi jo» seria oferir una porta
que el backend tancarà amb un 409.

**A les tres cares «Només consultar» és la PRIMÀRIA.** La lectura no té conseqüències i la resta
sí; el defecte d'un diàleg és el que passa quan algú prem Enter sense llegir. Cada opció
secundària porta la seva conseqüència escrita a sota, en text petit.

**Dues entrades, una sortida:** l'estat precalculat de F2.0 obre la cara **abans** que l'usuari
piqui contra la porta, i `caraDeError` la obre igualment si aquell estat anava ranci.

### La porta que faltava

`POST /api/v1/models/<id>/obrir-ronda/` ([views_b.py](../../backend/fhort/tasks/views_b.py) ·
[urls.py:65](../../backend/fhort/tasks/urls.py#L65)). **El servei `obrir_ronda` existia des de
F1.1 sense manera d'invocar-lo**: la sortida de D-5 vivia només al backend i el model 188 seguia
tapiat a la pràctica. Guard d'allow-list igual que `open-task`: no es crea feina que un mateix no
pot fer.

### `profile_id` a l'store

[store/auth.js](../../frontend/src/store/auth.js) — `MeSerializer` ja l'exposava i l'store el
llençava. `assignee` i `obert_per` són FK a `UserProfile`; comparar-los amb `User.id` seria
comparar dos espais d'ids diferents.

---

## 4 · F2.2 · MODIFICAR vs PREVISUALITZAR

**Aquest era el forat original de tota la investigació.** Els dos botons feien EXACTAMENT el
mateix `navigate` i cap comptava temps, mentre l'editor autodesava cada 2 s.

| Gest | Ara |
|---|---|
| **Previsualitzar** | `?mode=consulta`. Sense `task_id` l'editor no demana lock i l'autosave no dispara: ni batec ni sessió. **Visible**, amb icona i tooltip: és la sortida digna de qui només ve a mirar. |
| **Modificar** | Obre sessió sobre la tasca vigent `tech_sheet` i propaga `?task_id=`, passant pel modal només si cal. |

**I les tres portes que la diagnosi no havia censat com a portes d'edició:**

- «Crear fitxa» → crear-la **és** treballar-hi: obre sessió.
- «Editar» del panell de detall de Fitxers → obre sessió (via `onEditFitxa`).
- Clic a la fila de la llista de fitxers → és **mirar**: consulta explícita.

**Cap porta d'edició queda sense passar per la mateixa entrada.**

**M-8 tancat:** `tech_sheet.tab_hint` remetia a un Kanban jubilat feia mesos. Ara explica la
diferència real entre els dos botons, als tres idiomes.

---

## 5 · F2.3 · EL GEST D'ACABAR

`components/SessioActiva.jsx`, muntat a [App.jsx:99](../../frontend/src/App.jsx#L99) al costat de
`GuardTascaOblidada` i `AvisSessio`. **UN component per a tota l'app**: el tècnic salta de Mesures
a Fitxa a Escalat i la sessió és la mateixa cosa a totes. Un Stop per pantalla serien cinc llocs
on el gest que factura pot divergir.

Ensenya **què** hi ha obert, de **quin model** i **des de quan**, amb el Stop al costat. La
confirmació és **una frase**, no un modal pesat: acabar és normal i el diàleg ha de pesar el que
pesa el gest.

**UN TRAM OBERT NO ÉS PROVA QUE LA TASCA ESTIGUI EN CURS.** La font de veritat és l'estat de la
TASCA; el tram només hi posa el rellotge. És la lliçó que `GuardTascaOblidada` va aprendre a base
de 282 POSTs en minuts, **heretada en comptes de repetida** — i el test que la fixa és el que
comprova que l'indicador **NO** surt.

**Etiquetes auditades.** `model_measurements.unsaved_pom_hint` deia *«Grava POM per tancar la
tasca»* — prometia el que F1.2 va treure. Reescrita als tres idiomes. Les dues de
`fitting.save.*` que parlen de tancar es refereixen a la **sessió de fitting**, no a la tasca: són
correctes i s'han deixat.

---

## 6 · F2.4 · TRANSICIÓ ENTRE SUPERFÍCIES

Qui passa de Mesures a Escalat no ha canviat de feina: ha canviat d'eina. Fins avui, canviar de
pestanya **pausava** la tasca i no n'obria cap altra.

`saltDeSuperficie` ([utils/sessioActiva.js](../../frontend/src/utils/sessioActiva.js)) és
**silenciós per contracte**: si el salt no es pot fer net —conflicte, albarà, tasca inexistent—
retorna `null` i **no es pregunta res**. L'usuari ha canviat de pestanya, no ha demanat obrir res.
L'única pista visible és l'indicador de F2.3, que canvia de nom de tasca tot sol.

**«Fitxa tècnica» NO és al mapa de superfícies**, i és deliberat: aquell tab és una **llista** de
fitxes i entrar-hi és navegar. Obrir-hi sessió imputaria temps a qui només passa a veure quantes
n'hi ha; la sessió de la fitxa l'obre «Modificar».

El context entrant explícit (`?task_id=` / `?fitting_session=`) **mana** sobre el salt.

### Comprovació manual (per a QA de navegador)

1. Obre un model → tab **Mesures** → «Editar mides». L'indicador surt a baix a la dreta amb
   «Definició POM» i el rellotge a `0m`.
2. Canvia a **Escalat** sense tocar res més. L'indicador ha de canviar a «Escalat» **sense cap
   modal** i el rellotge tornar a començar.
3. Canvia a **Fitxers**. L'indicador ha de desaparèixer (la sessió s'ha pausat i no n'hi ha cap
   de nova).
4. Torna a **Mesures** amb una tasca que tingui un altre tècnic a sobre: **no** ha de saltar sol
   ni obrir cap diàleg.

---

## 7 · F2.5 · TEMPS DECLARAT

Validació pura a [utils/tempsDeclarat.js](../../frontend/src/utils/tempsDeclarat.js) — **14
tests**. Retorna **claus d'i18n, mai text**: qui pinta decideix l'idioma.

Dues modalitats **excloents** i el XOR es respecta fins al cos de la petició: o `{minuts}` o bé
`{inici, fi}`, mai els dos.

Valida abans d'enviar per no fer esperar un 400 a qui s'ha deixat un camp, **sense substituir** el
guard dur del backend. S'hi afegeix una regla que el backend no té perquè allà no tindria sentit:
**declarar feina del futur** és equivocar-se de camp, no declarar.

**El botó va al peu de la targeta del pla de treball**, al costat del transport, i no dins d'un
menú: si estigués amagat ningú no el faria servir i les hores del patró a mà seguirien sense
existir. Les tasques internes **no el veuen mai**.

---

## 8 · F2.6 · /temps

`data_inici`, `data_fi` i `created_at` **no existeixen**. El serializer emet `inici`, `fi`,
`minuts`, `actiu`, `last_heartbeat`, `origen`; `created_at` no és ni una columna de la taula. Com
que `''` mai és igual a la data d'avui, **la llista del dia i el gràfic de set dies eren buits
sempre**.

Fins i tot l'`ordering: '-data_inici'` era mut: el camp no era a `ordering_fields` i DRF l'ignorava
en silenci, cosa que **amagava** que el nom no existia.

L'agregació passa a [utils/agregaTrams.js](../../frontend/src/utils/agregaTrams.js) — **14
tests** — i hereta les tres lleis del backend:

1. **El dia és el de l'INICI del tram** (un tram que creua mitjanit compta al dia que va començar).
2. **`minuts` del servidor mana quan hi és** — recalcular-lo donaria una xifra que no quadraria
   amb l'albarà.
3. **Els trams desbocats no es compten** (mateix sostre que `MAX_MINUTS_TRAM`).

El **primer test del fitxer és el bug**: si algú torna a llegir camps inexistents, cau.

**D-2 · el temps DECLARAT es distingeix del MESURAT a simple vista.** Són la mateixa moneda per al
Welford i per a l'albarà, però no la mateixa evidència.

El botó de tancar **no torna**: un tram es tanca amb el Stop o amb la pausa per inactivitat.
Aquesta pàgina **mira, no toca** — i ara ho diu.

---

## 9 · F2.7 · L'AVÍS DE LLIURABLE

`rondes_lliurables` passa a dir **seq, motiu i data**. Sense data, un badge que digui «lliurable»
no diu si va passar avui o al març.

Tres llocs, una peça (`BadgeLliurable.jsx`):

- **Capçalera de la fitxa**, al costat de la identitat del model.
- **Pastilla compacta a la llista de models** — el PM ho ha de veure sense entrar model a model.
- **Històric de voltes lliurades** a la fitxa: la genealogia de F1 feta visible. Amb dues voltes o
  més, saber només l'última no explica res.

Es pinta **només si n'hi ha**: una llista de 200 files no pot portar 200 pastilles que diguin
«encara no».

**Només el FET.** Notificar activament (correu, push) és una decisió a part que aquest sprint no
pren.

---

## 10 · CHECKLIST i18n (5 punts, executat)

| # | Punt | Resultat |
|---|---|---|
| 1 | **Paritat ca/en/es dels blocs nous** | `obrir_tasca` 17·17·17 · `sessio` 4·4·4 · `temps_declarat` 21·21·21 · `lliurable` 6·6·6 → **OK** |
| 2 | **Paritat global del fitxer** | ca **3970** · en **3970** · es **3970** · falten 0 · sobren 0 → **OK** |
| 3 | **Claus noves sense consumidor** | **CAP** |
| 4 | **Claus usades que no existeixen** | 1 trobada: `tech_sheet.image_uploading` → **corregida** |
| 5 | **Guàrdies de presentació als fitxers nous** | hex al codi: **0** · icones `-filled`: **0** · `localStorage`: **0** · strings cablejades: **0** |

**Sobre el punt 4:** `tech_sheet.image_uploading` era **deute preexistent**, no d'aquest sprint —
`git log -L` el situa a `9de87a1e` («l'editor puja la imatge en col·locar-la»). S'ha afegit als
tres idiomes **tocant només els JSON**, mai `TechSheetEditor.jsx` (frontera respectada). S'hi han
posat les tres formes (`image_uploading`, `_one`, `_other`) perquè el consumidor usa `count`.

**Claus retirades:** `time_tracking.pause`, `.stop`, `.stopping`, `.min_value` als tres idiomes —
òrfenes des que F1.7 va jubilar l'endpoint `tancar`.

### Excepcions conscients declarades

1. **`rgba(0,0,0,…)` a les ombres** de `SessioActiva.jsx`. No és un color de marca sinó una ombra,
   i és la convenció ja vigent a la casa (`WorkPlan.jsx` fa `rgba(0,0,0,0.18)`, `Modal`/`overlay`
   igual). Cap token CSS d'ombra existeix; inventar-ne un aquí seria fer-ho a mitges.
2. **`TimeTracking.jsx` no declara `IBM Plex Mono`**: hereta la tipografia del shell, com feia
   abans. Els números porten `fontVariantNumeric: tabular-nums`, que és el que aquella pàgina
   necessitava.
3. **`i18n/*.json` reindentats a 2 espais** pel volcat programàtic. El diff és gran però és
   format, no contingut: la paritat de 3970 claus als tres fitxers ho verifica.

---

## 11 · SORPRESES

### 🚨 S-17 · El brief donava per fet un push que no s'ha produït

`origin/dev` és a `3692db68` i el local va **28 commits per davant**. Tot F1 (i ara F2) viu
**només en local**. No és un problema d'aquest tram —l'agent no pusha mai— però sí una premissa
que caldrà tancar abans de qualsevol desplegament: **el que hi ha a staging desplegat NO és el que
hi ha al repo local**.

### 🚨 S-18 · `SessioActiva` i `GuardTascaOblidada` sondegen el mateix endpoint

Dos `setInterval` sobre `timers.list({actiu:'true'})`, cadascun amb el seu estat. Són **preguntes
diferents** —el guard vigila la INACTIVITAT per auto-pausar; l'indicador mostra la PRESÈNCIA— i
tenen modes de fallada diferents, però la font és la mateixa.

**No s'han convergit a posta:** el guard té lògica guanyada a pols (trams rendits, anomalies de
dades, àncora de `last_heartbeat`) i refactoritzar-lo dins d'un sprint d'UI hauria estat el pedaç
que CLAUDE.md prohibeix. **És feina de F3**, i el comentari del component ho diu.

### ⚠️ S-19 · La cara CONFLICTE es pot disparar sense conflicte real

`caraObrirTasca` marca conflicte quan `assignee != jo` **encara que ningú hi tingui el rellotge**.
És el comportament que el brief demana («la tasca la té oberta altri, **o assignada a altri**»),
però a la pràctica vol dir que un tècnic que agafi feina planificada per a un altre veurà el
diàleg cada cop. Si això molesta, la línia és una: treure la segona condició de
`caraObrirTasca` i deixar només `obert_per`.

### ⚠️ S-20 · «Correcció» i «ronda» van per la mateixa porta

El modal ofereix dues opcions distintes (cara B) però totes dues criden `obrir-ronda` amb un
`motiu` diferent: una correcció és, mecànicament, **una volta d'una sola tasca**. Funciona i la
genealogia queda bé, però el `seq` s'incrementa igual — la ronda 3 pot ser «la correcció de la
2», no «la tercera mostra». Si el PM espera que `seq` compti **mostres**, cal separar els dos
comptadors. **No s'ha decidit aquí.**

### ⚠️ S-21 · El nom de la tasca a `/temps` costa N peticions la primera vegada

`TimerEntrada` no porta el nom del tipus de tasca (només `model_task_codi`), de manera que la
pàgina demana `modelTasks.get` per cada tasca distinta i ho memoritza en un `Map` de mòdul. Amb
200 trams de 20 tasques són 20 peticions al primer render. **La solució neta és al serializer**
(`task_type_name` a `TimerEntradaSerializer`), no al client — anotat, no fet, perquè tocar aquell
serializer és territori de F1/F3.

### 🔵 S-22 · `ronda_lliurable` sobre el buit segueix retornant `False`

Es va decidir així a F1.6 (§S-12) i F2.7 hi construeix a sobre: el badge **no surt** per a models
sense cap tasca lliurable. Es reconfirma aquí perquè ara té conseqüència visible.

---

## 12 · EL QUE NO S'HA TOCAT (fronteres respectades)

- `TechSheetEditor.jsx` **serialització**: l'única cosa que s'hi va tocar a F1.3 va ser el batec;
  a F2 no s'hi ha tocat res (la clau i18n que faltava s'ha afegit als JSON).
- Motor de grading · G1 · G6 · billing · el Gantt de planificació.
- `GuardTascaOblidada.jsx`: no s'hi ha tocat ni una línia (v. S-18).

---

## 13 · PENDENT DECLARAT

- **F3**: `recompute_welford` amb semàntica nova + `--apply` a staging · cron D-9 al runbook ·
  neteja de corpus a PROD post-deploy · **convergència dels dos sondeigs** (S-18) ·
  `task_type_name` al `TimerEntradaSerializer` (S-21).
- **Gantt de planificació** (sprint propi, endpoint d'agregació independent).
- **Refresh en temps real entre usuaris** (deute D-8).
- **Decisions obertes:** S-19 (conflicte per `assignee`) i S-20 (`seq` de ronda vs mostres).

---

## 14 · ACCIONS DE DESPLEGAMENT

1. **Cap migració nova a F2.** Les quatre de F1 (`tasks/0044`→`0047`) segueixen sent les úniques.
2. **Cap push fet.** 37 commits locals a `dev` (28 previs + 9 d'aquest tram).
3. Esborrar `backend/fhort/settings_f1_tmp.py` (temporal de test, mai committat).

---

*Patró B · 9 commits locals · cap push · cap suite · 137 tests de frontend + 55 de backend, verds.*

---

# ADDENDA · 2026-08-05 · el full de model petava per React #310

## La causa, en una línia

`accioDialeg` —el `useCallback` que F2.1 (`bed64468`) va afegir per a les quatre sortides del
modal— va quedar declarat **per sota** del retorn primerenc `if (loading)` de `ModelSheet.jsx`.

Un hook per sota d'un `return` no és cosmètic: és un hook **condicional**.

- `loading` neix a `true` (`ModelSheet.jsx:142`) → el **primer** render surt per la porta de
  `loading` i munta N hooks, sense `accioDialeg`.
- Quan el `Promise.all` de la càrrega acaba, `setLoading(false)` → el **segon** render passa de
  llarg el retorn i crida el hook N+1 → React #310, *«Rendered more hooks than during the
  previous render»*.

O sigui: el crash no és de la recàrrega, és de la **transició loading→loaded**, i per tant
passava a **cada** càrrega del full. Verificat amb contraprova: amb el bundle d'abans del fix,
`/models/164` ensenya el fallback de l'`AppErrorBoundary` a la càrrega inicial i a les tres F5.
El 401/200 del backend i el 502 de permisos de log no hi tenien res a veure.

## El fix (commit únic)

Moure el bloc sencer d'`accioDialeg` **amunt**, davant del `if (loading)`. Cap altra línia
tocada: mateixes dependències, mateix cos, mateix ordre relatiu a la resta de hooks (ja era
l'últim). Hi queden dues marques de frontera al fitxer perquè no torni a passar:
`ÚLTIM HOOK del component` sobre `accioDialeg` i `A partir d'aquí, RETORNS. Cap hook per sota`
sobre el retorn de `loading`.

## Cens de la resta (cap altre cas)

Recorregut sencer de `ModelSheet.jsx` (9 components) i dels 5 components que F2 va crear o
tocar — `ObrirTascaDialog` (F2.1), `SessioActiva` (F2.3), `BadgeLliurable` (F2.7),
`TempsDeclaratForm` (F2.5), `WorkPlan` (F2.4): **cap** hook després d'un retorn primerenc, cap
hook dins d'`if`/`&&`/ternari/bucle, cap hook fora d'un component o custom hook, cap custom hook
nou. Els sis camps derivats de F2.0 (`ModelSheet.jsx:185-193`) són càlculs purs, no hooks.

## Verificació

- `npm run build` net · `node --test caraObrirTasca.test.js` → 15/15.
- **Navegador real** (bundle de `frontend/dist` + API viva de staging via `django.test.Client`):
  models **164**, **188 (ROSALIA, tasca `pom` albaranada)** i **174 (`pom` d'un altre tècnic)**;
  per a cadascun: càrrega + **3 recàrregues dures** + salt Mesures → Fitxa tècnica → Escalat.
  Zero errors de consola, zero `pageerror`, cap error boundary.
- El modal s'ha obert de debò i s'ha premut la primària: cara **ALBARANADA** al 188 i cara
  **CONFLICTE** al 174 → `accioDialeg` executat, sense #310. **Zero escriptures** a staging
  (només el camí `consultar`, que per contracte no toca res).

## 🚩 Trobat pel camí · NO tocat (fora de scope)

- **`models_app/serializers.py:314` i `:355` llegeixen `rs.target_id`**, un FK que la migració
  `0043` (P7, «un rol, un vincle») va **retirar**. La branca és el fallback per a un ruleset amb
  `targets` buit, i quan hi cau peta amb `AttributeError` → **`GET /api/v1/models/<id>/` respon
  500**. Reproduït a staging amb els models **163, 164, 182 i 188** (el 185 passa perquè té
  targets). Bug pre-existent, aliè a F2 (la línia és de `7b0fdfd9`, 27/07) i **no tocat**: per a
  la QA d'aquest fix s'ha esquivat només dins el harness. Cal decidir si el fallback s'esborra o
  es reescriu sobre `targets`.
- **Cap `Ronda` a staging** (`Ronda.objects.count() == 0`): la cara **LLIURADA** del modal no és
  provable amb dades reals. Queda coberta pels 15 tests unitaris de `caraObrirTasca`.

*Patró A + B · 1 commit · cap push · cap suite.*
