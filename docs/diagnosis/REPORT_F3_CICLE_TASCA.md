# REPORT F3 · EL CORPUS, LA CRON I EL RUNBOOK

> Staging `/var/www/ftt-staging`, branca `dev`. Cap push. Cap suite.
> **Estat: F3.1 ATURAT AL PUNT DE PARADA.** El dry-run és a sota; **no s'ha corregut `--apply`**
> i no es correrà fins que Agus ho digui. F3.2 → F3.5, pendents.

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

## F3.2 · PENDENT — i una nota que ha de constar

Els dos sondeigs de `timers.list` (S-18) segueixen sense convergir. **Nota d'Agus per a qui ho
faci**: `temps_consumit_min` i `sessio_inici` es van afegir al `ModelTaskSerializer` a T4
justament per NO obrir un tercer sondeig. Quan hi hagi font compartida, són **candidats a
servir-se'n** en comptes del serializer — o a quedar-s'hi, si resulta més net. Que ho decideixi
qui hi sigui, amb això sobre la taula.

També cal comprovar-hi que els dos mapes bessons de destí (`TaskTree` / `WorkPlan`) han quedat
convergits a `destiTasca.js` després de T2 — ho van quedar, però val la pena verificar-ho amb
ulls nous.

## F3.3 · PENDENT (depèn de T3, que ja és verd)

L'exclusió de `origen='declarat'` del guard **ja hi és** (T3a, amb contraprova). La cron es pot
instal·lar sense por de matar cronos declarats.

## F3.5 · DEUTE ANOTAT, NO RESOLT

`sample_check` **no té clau i18n**: 14 claus `tasktype.*` per a 15 tipus, i cau al `defaultValue`
(«Sample check», igual als tres idiomes). **No es resol ara**: el nom definitiu depèn de la
pantalla aparcada. Queda escrit com a pendent explícit, no com a excepció silenciosa.

---

## SORPRESES

### 🔑 S-F1 · La llei nova no ha necessitat cap cas especial
Rondes i correccions surten soles de «una tasca, una mostra» perquè són `ModelTask` diferents. El
codi del corpus ha quedat **més curt** que el vell: ha desaparegut el bucle sobre transicions i la
reconstrucció de «què veia `Sum()` en aquell instant».

### 🚩 S-F2 · El criteri vell també PERDIA feina, no només en duplicava
El cas d'item=5. Ningú ho havia vist perquè només es mirava el costat de la inflació.

### 🔴 S-F3 · El corpus real és molt més petit del que semblava
43 mostres de `pom` eren **13** peces fetes. De les 4 cel·les que governen el planificador, en
queda **1**. El sistema portava mesos planificant amb una estadística que era, en bona part, el
recompte de vegades que s'havia premut un botó.

### 🔵 S-F4 · `los` no té res a recomputar
0 cel·les, 0 duplicats, 0 orfes. Tota la qüestió és de `fhort`.
