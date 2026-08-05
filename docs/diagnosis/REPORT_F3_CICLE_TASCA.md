# REPORT F3 · EL CORPUS, LA CRON I EL RUNBOOK

> Staging `/var/www/ftt-staging`, branca `dev`. Cap push. Cap suite sencera.
> **Estat: F3.1 → F3.5 TANCATS** amb les decisions d'Agus del 05/08 al vespre. El dry-run de
> F3.1 es conserva a sota tal com estava (és el document sobre el qual es va decidir); **el que
> ha passat de debò, i la taula que mana, és a [F3.1b](#f31b--laplicació-i-la-seva-auditoria)**.
>
> ⚠️ **Un número del dry-run no ha sobreviscut a la lectura directa de la BD** i es corregeix a
> F3.1b: `pom` global no passa de 246,6 a 120,2 sinó a **72,36**. I el «283» que aquest report
> deia no saber d'on sortia **ha aparegut**: v. [S-F6](#-s-f6--el-283-no-era-cap-discrepància).

---

## T4b · LA FITXA TÈCNICA (micro-commit previ) · `fa0ebbce`

Frontera aixecada estretament i respectada: **només el camí de sortida**. Les dues portes que hi
havia —la fletxa de la topbar i el breadcrumb— passen per `sortirDeLaFitxa`; sense tasca navega
com sempre, amb tasca obre el modal. La fila del `ModelTask` es demana **en aquell moment i només
aquell** (una lectura, cap sondeig nou). **Res de serialització, render o lògica del `.ftt`.**

L'única línia que no és de sortida és el guard del cleanup: la pausa cega de desmuntatge ara
respecta el que el modal ja ha resolt. Sense això, sortir per «L'he acabat» deixaria un
`Done→Paused` il·legal darrere — un 400 per una feina ja feta.

**Verificat a mà** (model 163 · fitxa 575 · tasca 193): càrrega, **recàrrega**, sortida → «Has
acabat Fitxa tècnica?» amb el total real (14h 59m) → «La pauso» → torna al model amb la tasca
Pausada. Cap `pageerror`. Els errors de consola que hi surten són del harness de QA (els assets
del `.ftt` tenen URL absoluta a staging, que el servidor local no pot servir) i el 409 del lock
en obrir dues instàncies seguides. Staging net: esborrats el tram i les dues transicions de la
prova.

---

# F3.1 · EL DRY-RUN 🛑 **PUNT DE PARADA**

## La llei que s'ha implementat

**UNA TASCA = UNA MOSTRA** (D-3). El total és el d'**avui**, no el del moment de tancar-la.
Reobrir **actualitza** la mostra. Una tasca sense cap `→Done` no és mostra: és feina en curs.

Que cada **ronda** sigui una mostra independent i que cada **correcció** ho sigui també **no ha
calgut programar-ho**: són `ModelTask` diferents (F1.1 · S-20), i la llei ho dona sol. El temps
**declarat** compta igual que el mesurat.

## El delta, a `fhort`

**8 cel·les a corregir · 445 ja quadren · 0 sense fila.** A `los`: **res** (0 cel·les, 0 tasques
amb tancaments repetits, 0 orfes).

| tipus | cel·les | n | mitjana ponderada |
|---|---|---|---|
| `pom` | 5 | **29 → 11** | 340,3 → **97,5** ↓ |
| `size_check` | 2 | **12 → 3** | 222,8 → **388,0** ↑ |
| `tech_sheet` | 1 | 1 → 1 | 895,0 → **925,0** ↑ |

Cel·la a cel·la:

| cel·la | n | mitjana | m2 |
|---|---|---|---|
| item=4 `pom` | 1 → 1 | 150,0 → 199,0 | 0 → 0 |
| item=4 `size_check` | **7 → 1** | 199,9 → 510,0 | 303.141 → 0 |
| item=5 `pom` | **5 → 6** | 4,0 → **10,5** | 34 → 384 |
| item=10 `pom` | 3 → 1 | 41,7 → 42,0 | 1 → 0 |
| item=22 `pom` | **17 → 1** | 562,3 → **760,0** | 367.685 → 0 |
| item=30 `tech_sheet` | 1 → 1 | 895,0 → 925,0 | 0 → 0 |
| item=30 `pom` | 3 → 2 | 5,3 → 4,5 | 17 → 12 |
| item=30 `size_check` | 5 → 2 | 255,0 → 327,0 | 341.287 → 122.018 |

## Els tres números coneguts, contrastats

| el brief deia | el dry-run diu | ✓ |
|---|---|---|
| la tasca 250, tancada 17 cops → 1 mostra | `tasca 250 pom model 186 · 17 tancaments → 1 mostra · total 760 min`; la cel·la item=22 passa de **n=17** a **n=1** | ✅ |
| `pom` empíric 283 min contra TimeSeed 35 → ha de moure's | mitjana ponderada global de `pom`: **246,6 → 120,2 min** (n global 43 → 13) | ✅ es mou, i molt · ⚠️ el meu «abans» és **246,6**, no 283 |
| la cel·la que programa 4 min amb mostres 2,9,3,4,2 | és **item=5 `pom`** (n=5, mitjana 4,0 — les cinc mostres quadren exactament). Ara: **n=6, mitjana 10,5** | ✅ el 4 desapareix |

⚠️ **La discrepància del 283.** El meu càlcul del «abans» de `pom` dona **246,6 min** ponderats
(43 mostres). No sé d'on surt el 283 del brief —potser d'una altra data, d'una ponderació sense
ponderar, o incloent-hi cel·les de seed— i **no l'he forçat a quadrar**. El número que compta és
el de després: **120,2**.

## 🚩 Una cosa que sorprèn i que has de mirar: `n` PUJA a item=5

`n` baixa a tot arreu menys allà (5 → 6). No és un error, i el motiu importa: el criteri vell
comptava, per a cada `→Done`, **els trams tancats FINS a aquell instant**. Una tasca que es va
donar per feta i després s'hi va tornar tenia `x = 0` en aquell instant → mostra descartada. Ara
el total és el d'avui, i aquella feina **sí que hi entra**. Dit al revés: el criteri vell no
només duplicava les tasques reobertes, també **perdia** feina real de les que es van reobrir
just després de tancar-les.

## 🔴 LA CONSEQÜÈNCIA QUE MÉS PESA: qui MANA sobre el planificador

Amb `WELFORD_MIN_SAMPLES = 5`, avui només **quatre** cel·les governen. Després del recompute,
**una**:

| cel·la | n | mitjana | mana? |
|---|---|---|---|
| item=5 `pom` | 5 → **6** | 4,0 → **10,5** | SÍ → **SÍ** |
| item=22 `pom` | 17 → **1** | 562,3 → 760,0 | SÍ → **no** |
| item=4 `size_check` | 7 → **1** | 199,9 → 510,0 | SÍ → **no** |
| item=30 `size_check` | 5 → **2** | 255,0 → 327,0 | SÍ → **no** |

**Tres de les quatre cauen per sota del llindar i el planificador torna al TimeSeed.** És el
resultat honest de la llei nova sobre un corpus tan petit: la major part de les «mostres» que hi
havia eren re-tancaments de la mateixa peça. **La 562,3 deixa de manar**, que és exactament el
que es volia; el preu és que `size_check` també es queda sense estadística pròpia.

Això és decisió teva i no la prenc: **aplicar-ho** (el planificador torna a seeds fins que hi
hagi feina real) o **aplicar-ho i revisar el llindar** són dues coses diferents.

## 🚩 ELS RELLOTGES ORFES — decisió pendent

**4 trams · 1 minut** a `fhort`, tots dins d'higiene:

| tipus | trams | minuts |
|---|---|---|
| `design_review` | 2 | 1 |
| `design_clarify` | 1 | 0 |
| `pattern_hand` | 1 | 0 |

Un tram **mesurat** sobre una tasca **externa** només pot venir de la porta que obria rellotge
sense pantalla (arreglada a T2): la feina externa es fa fora de l'eina i no és observable.

**Simulació amb `--sense-orfes`**: passa de **8 a 9 cel·les** a corregir. La novena és
`design_review` amb **n=1 → n=0** i mitjana 1,0 → 0. **Excloure'ls costa gairebé res**, i el seu
pes al corpus és zero a efectes pràctics.

**La meva proposta: excloure'ls**, i no pel pes (que és nul) sinó perquè deixar-los hi és dir que
són temps mesurat quan sabem que no ho és. **La decisió és teva** — `--sense-orfes` no és un flag
de conveniència, és el número per prendre-la.

## Verificació

- **9 tests** nous (`test_recompute_d3`), un per frase de la llei + els tres dels orfes.
- **445 cel·les ja quadren** amb el càlcul nou i **no es toquen**: és el test de correcció de
  gratis que el command ja tenia i que segueix valent.
- **Cap escriptura.** `--apply` no s'ha corregut.

---


# F3.1b · L'APLICACIÓ I LA SEVA AUDITORIA

**Corregut:** `recompute_welford --sense-orfes --apply`, a staging, als dos tenants. A `fhort`:
**9 cel·les corregides · 0 creades · 444 intactes.** A `los`: res (0 cel·les, 0 duplicats, 0
orfes) — tota la qüestió era de `fhort`, com deia el dry-run.

**Les decisions d'Agus, aplicades tal com van arribar:** orfes **exclosos** · delta **aplicat** ·
llindar `n>=5` **sense tocar**.

## L'auditoria no se la fa el command

Un command que s'aprova a si mateix és una signatura, no una verificació.
`backend/scripts_tmp/f31b_snapshot_welford.py` llegeix `TaskTimeEstimate` **directament de la
BD** i s'ha corregut abans i després. El `diff` dona **exactament 9 files canviades** i cap més
— cap efecte col·lateral sobre les 444 que ja quadraven.

## LA TAULA DEFINITIVA · cel·la a cel·la (llegida de la BD)

| cel·la | n | mitjana (min) | m2 | manava? |
|---|---|---|---|---|
| item=4 `pom` | 1 → 1 | 150,00 → **199,00** | 0 → 0 | no → no |
| item=4 `size_check` | **7 → 1** | 199,86 → **510,00** | 303.140,79 → 0 | **SÍ → no** |
| item=5 `pom` | **5 → 6** | 4,00 → **10,50** | 34,00 → 383,50 | **SÍ → SÍ** |
| item=8 `design_review` | **1 → 0** | 1,00 → 0,00 | 0 → 0 | no → no |
| item=10 `pom` | 3 → 1 | 41,67 → 42,00 | 0,67 → 0 | no → no |
| item=22 `pom` | **17 → 1** | 562,29 → **760,00** | 367.685,14 → 0 | **SÍ → no** |
| item=30 `pom` | 3 → 2 | 5,33 → 4,50 | 16,67 → 12,50 | no → no |
| item=30 `size_check` | **5 → 2** | 255,00 → **327,00** | 341.287,35 → 122.018,00 | **SÍ → no** |
| item=30 `tech_sheet` | 1 → 1 | 895,00 → **925,00** | 0 → 0 | no → no |

**La novena és la dels orfes**: `item=8 design_review` només existia perquè un rellotge va córrer
sol sobre una tasca externa. Amb `--sense-orfes` cau a `n=0`, que és el que Agus va decidir que
havia de passar.

## LA TAULA DEFINITIVA · agregat per TaskType (tot `fhort`, no només les cel·les tocades)

| tipus | cel·les | n total | mitjana ponderada |
|---|---|---|---|
| `pom` | 57 | **43 → 25** | 246,65 → **72,36** ↓ |
| `size_check` | 2 | **12 → 3** | 222,84 → **388,00** ↑ |
| `tech_sheet` | 57 | 2 → 2 | 538,50 → **553,50** ↑ |
| `design_review` | 1 | **1 → 0** | 1,00 → 0,00 ↓ |
| `grading` | 2 | 2 → 2 | 186,50 → 186,50 = |
| (la resta: `bom`, `marking`, `pattern_*`, `scaling`) | 57 c/u | 0 → 0 | — |

**Cel·les que governen el planificador (`n>=5`): 4 → 1.** L'única supervivent és **item=5 `pom`**,
que a més és la que **puja**: n=5 → 6, mitjana 4,0 → 10,5 min.

---

# 🚩 SORPRESES DE F3.1b → F3.5

### 🔴 S-F5 · El «després» del dry-run estava mal comptat, i la correcció va A FAVOR

El dry-run deia: `pom` global **246,6 → 120,2** (n 43 → 13). La BD diu **246,65 → 72,36**
(n 43 → **25**).

La causa, localitzada: el «abans» era **global** i el «després** **no**. El 120,2 es va calcular
sobre n=13 = les 11 mostres de les cel·les tocades + les 2 cel·les sanes amb prova viva
(item=11 i item=18) — **excloent els 12 mostreigs que viuen a les 8 cel·les «sense cap tasca
supervivent»**, que el «abans» sí que comptava i que **no es toquen a posta** (esborrar una
`ModelTask` s'emporta timers i transicions en CASCADE: la cel·la és l'últim rastre d'aquella
feina). Comparar-los era comparar dues poblacions diferents.

**La conclusió no canvia de signe: es reforça.** La caiguda real és més gran, no més petita.

### 🔑 S-F6 · El «283» no era cap discrepància

El report de F3.1 deia no saber d'on sortia el 283 del brief i el va deixar anotat com a
discrepància d'abast. **Ha aparegut sol**, en traçar què serveix el planificador de debò
(`services_g.lookup_estimated_minutes`):

> **283 és el GRAÓ 2 de la cascada** — l'`empíric_global` del `task_type`: la mitjana **NO
> ponderada** de les mitjanes de les cel·les **madures** (`n>=5`).
> `(4,00 + 562,29) / 2 = 283,145` → **283**. Exacte.

No es contradeia amb el 246,6: **són dues quantitats diferents**. El 246,6 és la mitjana
ponderada de tot el corpus; el 283 és el que el planificador serveix a un model **que no té
cel·la pròpia madura**. El segon és el que es nota; el primer no el veu ningú.

I aquí és on el recompute pica de debò:

| `task_type` | graó 2 abans | graó 2 ara |
|---|---|---|
| `pom` | **283** | **10** |
| `size_check` | 227 | **cap dada** |
| `tech_sheet` | cap dada | cap dada |

*(No s'hi ha dedicat temps a posta —Agus va dir de no perseguir-ho— i no calia: va caure sol en
mirar la cascada per a la nota de F3.5.)*

### 🔴 S-F7 · «Les cel·les que cauen, cauen al TimeSeed» — `size_check` NO cau enlloc

La premissa amb què es va prendre la decisió era que les cel·les que baixessin de `n>=5`
tornarien al TimeSeed. **Per a `size_check` això no passa: no hi ha TimeSeed on caure.**

A `fhort` hi ha **8 `TimeSeed`, tots de `scope='task'`, i CAP de `scope='phase'`**. Set dels
quinze `TaskType` no en tenen ni per codi ni per fase:

> `audit` · `design_clarify` · `design_review` · `grading` · `pattern_review` · `sample_check` ·
> **`size_check`**

La cascada sencera per a `size_check`, ara: graó 1 cel·la pròpia → `n<5` i `estimated_minutes`
és NULL → res · graó 2 empíric global → cap cel·la madura → res · graó 3 TimeSeed → **no
existeix** · graó 4 → `None`. **El planificador es queda sense cap estimació per a `size_check`.**

Això **no invalida la decisió** («les cel·les que cauen, cauen» era exactament això), però en
canvia la conseqüència: no és «torna a un número pitjor», és «deixa de tenir número». Val la pena
saber-ho abans de córrer-ho a PROD.

---

# F3.2 · ELS DOS SONDEIGS DE `timers.list`, CONVERGITS · `42ba29ff`

**No s'ha perdut cap cas del guard.** Es va llegir la seva lògica abans de moure-la, i el que
s'ha convergit és **la LECTURA, no la política** — que és el que fa que no se'n perdi cap.

`GuardTascaOblidada` (vigila la INACTIVITAT) i `SessioActiva` (mostra la PRESÈNCIA) feien cadascú
el seu `timers.list({actiu:'true'})` + el seu `modelTasks.get`: **quatre peticions per minut** per
saber una sola cosa, amb dos rellotges desfasats — el guard podia pausar una tasca i la píndola
seguir dient que corria fins a un minut després. Ara tots dos escolten `api/tramObert`.

## El cas que una convergència distreta hauria perdut

| fet | el guard | la píndola |
|---|---|---|
| **la llista falla** (xarxa) | **es manté ARMAT** | s'amaga |
| no hi ha cap tram obert | neteja | s'amaga |
| tram obert, tasca no-`InProgress` | es rendeix i ho apunta | no pinta |
| la tasca no es pot llegir | neteja | s'amaga |

**Davant del mateix fet han de fer coses diferents.** Per això els modes de fallada són **estats
explícits** (`CAP` · `OBERT` · `ERR_LLISTA` · `ERR_TASCA`) i no un `null` per a tot: un `null`
únic hauria obligat tots dos a la mateixa reacció i **el guard s'hauria desarmat a cada GET
fallit**, justament quan hauria de comptar. Era el `.catch` buit d'abans, i és el cas que es
perd si es converge de memòria.

També s'han conservat, un per un: els trams `rendits` · l'anomalia dita **un sol cop** per
consola · la identitat del tram que evita rearmar `pausant` · i **el reposicionament del rellotge
en tornar el focus**, que **es queda al guard** (la lectura és compartida, però qui decideix és
`ara` contra els instants absoluts). El guard **escolta** la font en comptes de derivar-la,
perquè el que ensenya no és funció pura de l'última lectura.

**Un detall que no era obvi:** `refresca()` es crida just després d'una transició i pot avançar
una consulta periòdica ja en vol. Sense número de seqüència, la lenta reemetria el món d'**abans**
i el guard es rearmaria damunt del tram que s'acaba de tancar. Cada consulta porta número i només
emet si cap de posterior no ho ha fet ja.

**De regal** (no era l'objectiu): en pausar-se una tasca la píndola marxa a l'instant, i
`SessioActiva` guanya la re-lectura en tornar el focus que abans només tenia el guard.

Decisió pura a `tramObertCore.js` (cap import, `node --test`), cablatge a `tramObert.js` — el
mateix patró que `tascaActivaCore` i `sessioCore`. **12 tests nous**, un per cas que no es podia
perdre; **179 tests de front verds**; lint net als fitxers tocats; build verd.

## Les dues revisions de passada que demanava el brief

**(a) `TaskTree` / `WorkPlan` → `destiTasca.js`: CONVERGITS, verificat.** Tots dos importen el
resolutor i **no queda cap `case '` a cap dels dos fitxers**. Cap duplicació residual.

**(b) `temps_consumit_min` i `sessio_inici`: ES QUEDEN AL SERIALIZER.** Decisió, amb el motiu:
són **preguntes diferents de la que respon la font nova**. `tramObert` sap *quin tram tinc obert
JO, ara*; `temps_consumit_min` és l'**agregat de TOTS els trams d'una tasca** —de qualsevol
tècnic i de qualsevol sessió— i el modal de T4 el demana **d'una tasca concreta en el moment de
sortir-ne**, no en sondeig. Servir-lo des de la font compartida obligaria a una consulta nova per
tasca i donaria un número **més pobre** (només la meva sessió). `sessio_inici` sí que se solapa
amb el que `tramObert` sap, però separar-lo del seu germà per estalviar un camp de serializer
partiria en dos el que el modal llegeix d'un sol cop, sense guanyar-hi res.

---

# F3.3 · LA CRON DEL GUARD (D-9) · **INSTAL·LADA A STAGING**

## Execució manual, primer

Cens llegit de la BD (`backend/scripts_tmp/f33_cens_trams_oberts.py`), abans i després:

| | abans | després |
|---|---|---|
| trams oberts a `fhort` | 1 | **1** |
| dels quals amb **batec viu** | 1 (`timer=365`, 13,0 min) | 1 (`timer=365`, 16,4 min) |
| **declarats** vençuts | 0 | 0 |
| tasques En curs sense cap tram | 0 | 0 |
| **auto-pausades** | — | **0** |

`--dry-run` i execució real, tots dos: **0 auto-pausades**. **El tram amb batec viu segueix
obert i intacte** — que és la verificació explícita que demanava el brief.

## La contraprova positiva, que el corpus real no podia donar

Amb 0 candidats vençuts, l'execució real prova que **no toca el que no ha de tocar**, però no que
**sí que toca el que ha de tocar**. Per no baixar el llindar contra una tasca viva de debò —seria
escriure damunt de la feina d'algú per fer-ne una demo— la prova positiva surt dels dos tests que
ja existien:

- `test_el_guard_SI_pausa_un_tram_mesurat_vell` ✅
- `test_el_guard_no_pausa_un_crono_declarat` ✅

**34/34 OK** (`test_crono_declarat` + `test_guard_tasca_oblidada`). Mòduls concrets, no la suite.

## La crontab

```
*/5 * * * * cd /var/www/ftt-staging/backend && /var/www/ftt-staging/backend/venv/bin/python \
    manage.py pausa_tasques_oblidades >> /var/log/ftt/guard_tasques.log 2>&1
```

Verificada **executant la línia exacta sota un entorn mínim** (`env -i`, com fa cron): sortida 0
i log escrit. `cron` actiu i habilitat. El `cd` no és decoratiu — sense ell `manage.py` no es
troba, i es va comprovar veient-ho fallar.

### 🚩 UNA LECTURA MEVA QUE CAL QUE CONFIRMIS

El brief diu «instal·lar la crontab a STAGING **amb 30/3**». Ho he llegit com **els valors de
producció del guard del NAVEGADOR** (avís 30 min + 3 min de gràcia = `LLINDAR_PROD_MIN` /
`GRACIA_PROD_MIN`, que ja hi són i no s'han tocat), i he instal·lat la crontab **tal com està
documentada al capçal del command**: cada 5 min, llindar 40.

El motiu de no llegir-ho com a paràmetres de la cron: **el llindar del cron és 40 > 33 a posta**.
Si es baixés a 30, el cron pausaria **abans** que el modal hagi acabat de preguntar i el tècnic
es trobaria la tasca pausada amb el diàleg encara a la pantalla. Si volies una altra cadència,
és **una línia** de `crontab -e`.

---

# F3.4 · RUNBOOK · escrit, NO executat

`docs/diagnosis/RUNBOOK_PROD_CICLE_TASCA.md`. Cobreix, en ordre d'execució: el desplegament
(amb les dues trampes: auditar la BD després de `migrate_schemas`, i el `pip install` de la dep
HEIC) · `recompute_welford --sense-orfes --apply` **post-migració**, amb el perquè de l'ordre i
la verificació per `diff` contra la BD · la cron del guard i els seus tres números · el fix
`89009858` (i per què és l'únic punt del runbook que és **una porta oberta** i no un número
dolent: sense ell, `last_heartbeat` és escrivible per `PATCH` i el guard és opcional per a qui
sàpiga fer-ne un) · i que **staging no té pas de desplegament**.

---

# F3.5 · DEUTE ANOTAT, NO RESOLT

### `sample_check` sense clau i18n
**14 claus `tasktype.*` per a 15 tipus**, verificat als tres idiomes (`ca`/`en`/`es` en tenen 14
cadascun i cap té `sample_check`). Cau al `defaultValue` — «Sample check», igual als tres. **No
es resol ara**: el nom definitiu depèn de la pantalla aparcada. Queda escrit com a pendent
explícit, no com a excepció silenciosa.

### 🚩 TRAM PROPI · contrastar cada `TimeSeed` amb el corpus net

Anotat, **no fet**. I després de S-F7 és **més gros del que semblava**: no és només que els seeds
menteixin per sota — és que **més de la meitat dels `TaskType` no en tenen cap**.

Els números per començar-hi, ja mesurats:

| `task_type` | seed | n mesurat | mitjana neta | ràtio |
|---|---|---|---|---|
| `pom` | 35 | 25 | **72,4** | **×2,1** |
| `tech_sheet` | 45 | 2 | **553,5** | **×12,3** |
| `size_check` | **cap** | 3 | **388,0** | — |
| `bom` · `marking` · `pattern_cad` · `pattern_digit` · `pattern_hand` · `scaling` | 14–135 | 0 | sense mesura | — |

**Sense seeds i sense mesura, el planificador segueix mentint per defecte encara que el corpus
estigui net.** És més gros que qualsevol cel·la d'avui, i ara té dues cares: **actualitzar** els
seeds que existeixen i **crear** els set que no.

---

# EL QUE S'HA FET, EN UNA LÍNIA CADASCUN

| | |
|---|---|
| **F3.1b** | corpus net escrit a `fhort`, 9 cel·les, auditat contra la BD · `b526044e` |
| **F3.2** | una sola lectura de `timers.list`, política a cada banda, 12 tests · `42ba29ff` |
| **F3.3** | cron verificada a mà i **instal·lada** a staging (`*/5`, llindar 40) |
| **F3.4** | runbook de PROD escrit, no executat |
| **F3.5** | `sample_check` i el tram dels `TimeSeed`, anotats |

**CAP PUSH.** El push és d'Agus.
