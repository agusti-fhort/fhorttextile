# INFORME · EL CICLE DE TASCA DE FTT

### Diagnosi completa + fixos aplicats + decisions obertes

**Data:** 04–05/08/2026 · **Entorn:** staging (`/var/www/ftt-staging`, branca `dev`)
**Mètode:** Patró A (read-only) seguit d'una tanda de fixos mecànics · **Cap push.**
**Doc font (llarg, amb `fitxer:línia` a cada afirmació):** `docs/diagnosis/DIAGNOSI_CICLE_TASCA_COMPLET.md`

> Aquest informe és el **resum executiu autocontingut**: qui el llegeixi no necessita obrir el repo.
> Per a la implementació, la font és el doc llarg. Les xifres surten de consultes `SELECT` sobre
> `ftt_staging` (schema `fhort`) i dels access logs de nginx del 04/08.

---

## 0 · LA CONCLUSIÓ, EN UNA FRASE

El sistema de temps **funciona bé quan la porta és oberta i no mesura res quan no ho és** — i
resulta que les tres superfícies on més s'escriu sobre un model (editar la fitxa `.ftt`, pujar
fitxers, editar la graella de mides) **no obren cap porta**. El que sembla un bug de rellotge és
un forat de cobertura del cicle de tasca.

---

## 1 · COM FUNCIONA EL CICLE, AVUI

Hi ha **una sola màquina d'estats**, `transition_task` (`tasks/services_c.py:177`), i és neta:

```
Pending    → {InProgress}
Paused     → {InProgress}
InProgress → {Paused, Done}
Done       → {InProgress}   ← reobertura = "rectificació"
```

Entrar a `InProgress` obre un `TimerEntrada`; sortir-ne el tanca amb la seva durada. Tancar a
`Done` alimenta l'estadística Welford. Tot hi passa: kanban, guards i cron inclosos. **No hi ha
cap màquina paral·lela.** Això és sòlid i no s'ha de tocar.

Quatre portes HTTP hi arriben: `open-task` (crea-si-falta + obre), `transition` (transició
explícita), `claim` (reassigna sense tocar estat) i el `PATCH` de planificació.

---

## 2 · EL MAPA REAL DE PORTES — on es trenca

De **24 portes d'usuari censades, 11 no toquen `ModelTask` en absolut**.

**Sí que obren rellotge:** tab Mesures → «Editar mides» · tab Escalat → «Editar graduació» ·
menú lateral → Fitxa tècnica · Pla de treball → Play · tab Tasques → Iniciar · Taller de patró.

**No obren res (i és on hi ha el dolor):**

- 🔴 **Tab Fitxa tècnica → «Modificar»**, i també «Previsualitzar», «Crear fitxa» i «Nova fitxa»
- 🔴 **Tab Patró** (el Taller sí; la pestanya no)
- 🔴 **Editar cel·les de la taula de mides** (`PATCH base-measurements/`, `escalat/ajustar-talla/`)
- 🔴 **Pujar fitxers al model**
- 🔴 **Propagar a grading** (`generar-grading`)
- 🔴 **Editar model (wizard)** · llista de models · Dashboard · Planificació
- 🔴 **El Kanban — NO EXISTEIX.** No hi ha cap ruta `tasques/kanban`; `ModelFabric.jsx:120` hi
  navega i cau al catch-all. Això importa molt: vegeu §3.

---

## 3 · EL CAS QUE VA OBRIR LA INVESTIGACIÓ

> *«Obrir la fitxa tècnica des de modificar no reobre ni reassigna tasca.»*

**És exacte, és una línia, i no és una regressió.**

El botó «Modificar» (`ModelSheet.jsx:927`) navega a `/models/:id/ftt/:fitxerId` **sense
`task_id`**. L'editor llegeix `task_id` de la query (`TechSheetEditor.jsx:2566`), no en troba cap,
i per tant ni obre, ni reobre, ni reassigna, ni pausa — mentre **autodesa cada 2 segons**.

El punt clau per al disseny: **estava escrit i era deliberat.** El comentari del tab diu
literalment *«Consulta des del Model obre sense task_id → mode consulta (l'editor desa igual, però
no imputa temps). L'edició registrada es fa des del Kanban, que passa ?task_id=...»*

**La decisió tenia dues meitats i una s'ha jubilat.** El Kanban ja no existeix, així que
«Modificar» ha quedat com **l'única porta pràctica** a les fitxes d'un model — i és la que no
compta. Fins i tot el text d'ajuda de la UI segueix remetent el tècnic a un Kanban que no pot obrir.

Això és la **decisió D-1**: no és un fix, és recuperar la meitat que falta.

---

## 4 · EL PING-PONG, MESURAT

### 4.1 · Com és el bucle real

No és que «s'obri i es tanqui a cada desat». És més subtil i pitjor:

1. L'usuari entra a editar → la tasca passa a `InProgress`, s'obre el timer.
2. Prem **«Gravar POM»** → el backend la tanca a **`Done`** (`models_app/views.py:1615-1618`) →
   tanca el timer i injecta una mostra Welford.
3. El front surt del mode entrada i **no reobre res**.
4. **L'usuari segueix treballant a la taula — sense tasca i sense timer.**
5. Torna a prémer «Editar mides» → `Done → InProgress` = **rectificació**.

Cada volta deixa una rectificació al log, una mostra Welford duplicada, i **un tros de feina real
que no s'ha comptat**.

Hi ha també un obre-i-tanca **dins del mateix request** quan la tasca ve de Pending/Paused:
transicions registrades a **10 mil·lisegons** l'una de l'altra, amb el seu timer de 0 minuts.

### 4.2 · Les xifres del corpus viu

| Mesura | Valor |
|---|---|
| Transicions `→Done` | **49**, produïdes per només **21 tasques** |
| De les quals repeticions | **28 (57 %)** |
| Rectificacions `Done→InProgress` | **39** |
| Distribució de `→Done` per tasca | 15×1 · 2×2 · 2×3 · 1×**7** · 1×**17** |
| Trams amb `minuts = 0` | **100 de 217 (46 %)** |
| Timers zombis oberts / trams > 24 h | **0 / 0** ✅ (higiene antiga ja aplicada) |

**Una sola tasca (id 250, model 186, `pom`) ha generat 17 mostres Welford**, amb valors
204, 360, 361, 511, **511**, 536, **536**, 566, **566**, 574, 577, 606, 660, 711, 760, **760**,
**760**. Els duplicats estan separats per 10–38 segons. El valor real de la feina és 760 minuts;
la cel·la creu tenir 17 observacions independents.

### 4.3 · Quant temps queda registrat d'una hora de treball

Tres mesures, i la tercera és la que mana:

- **Dins d'un tram obert el rellotge és bo:** 60 sessions, 8 958 min de finestra,
  **8 684 registrats = 97 %**.
- **El truncament (`//60`) és irrellevant:** 75 min perduts sobre 9 852 = **0,8 %**.
- **La pèrdua és ENTRE trams:**

| Dia | Finestra | Registrat | % |
|---|---|---|---|
| 08/07 | 42 min | **0** | **0 %** |
| 27/07 | 37 min | **0** | **0 %** |
| 31/07 | 302 min | 29 | **10 %** |
| 26/06 | 356 min | 142 | 40 % |
| 24/06 | 679 min | 422 | 62 % |

**Resposta a la pregunta:** d'una hora real en surten entre **0 i 60 minuts**, i el que ho
decideix no és quant s'ha treballat sinó **si la porta va quedar oberta**.

---

## 5 · EL MOTOR DE TEMPS — ja mana i ja menteix

### 5.1 · El defecte estructural

`record_actual_time` injecta com a mostra **el total acumulat de la tasca**, no l'increment del
darrer tram. Combinat amb `Done→InProgress` permesa, cada reobertura-i-retancament injecta una
mostra nova gairebé idèntica a l'anterior.

No és una sospita: el propi command de recompute ho documenta com a fet verificat — *«`n` de cada
cel·la quadra amb el nombre de transicions →Done, no amb el de tasques Done.»*

### 5.2 · L'estat real, i per què ja és urgent

El llindar de maduresa és **n ≥ 5**. Un cop passat, l'empíric **substitueix** la llavor.

| item × task | seed | n | mitjana | Mana? |
|---|---|---|---|---|
| 22 × `pom` | 30 | **17** | **562 min** | ✅ — les 17 mostres surten d'**UNA** tasca |
| 5 × `pom` | 30 | **5** | **4 min** | ✅ — **substitueix el seed de 30** |
| 4 × `size_check` | — | 7 | 200 min | ✅ |
| 30 × `size_check` | — | 5 | 255 min | ✅ |

Les 5 mostres de la cel·la (5 × `pom`) són `2, 9, 3, 4, 2` minuts: **les engrunes entre obrir la
porta i prémer Gravar**. El planificador ara programa aquella tasca a 4 minuts.

**I menteix també cap amunt.** El graó 2 de la cascada fa la mitjana de les cel·les madures de
qualsevol item:

- **empíric global de `pom` = 283 min**, contra una `TimeSeed` de **35 min**. Vuit vegades més,
  derivat de dues cel·les de les quals una és el ping-pong de la tasca 250.
- **empíric global de `size_check` = 227 min.**

**Conclusió per al disseny:** el motor està sa; el que li donem de menjar no. I
`recompute_welford` **no és el remei** — reprodueix fidelment la contaminació, perquè la
contaminació *és* la semàntica actual.

---

## 6 · EL MODAL D'1 MINUT

No era un bug del guard: era **una clau de QA que va quedar encesa**.

El llindar es llegia de `localStorage` a la càrrega del mòdul, i el comentari deia *«per sessió de
navegador»* — cosa **falsa**: `localStorage` no caduca. Un `ftt_guard_llindar_min = 1` posat en un
QA el 27/07 seguia encès el 04/08.

**Mesurat a la BD:** els primers batecs arriben als **63 s** i **90 s** de l'obertura del tram
(amb el valor de producció serien 1 800 s). El 31/07 això va produir **sis auto-pauses sobre la
mateixa tasca en 75 minuts**, tres d'elles en 4 minuts — i aquell dia el model va registrar 29
minuts sobre 302. **El guard mal calibrat és una causa directa del forat de temps**, no només una
molèstia.

✅ **Ja arreglat** (§8).

⚠️ **Segueix pendent:** la xarxa de sota. El command `pausa_tasques_oblidades` és llest des del
27/07 però **la crontab no s'ha instal·lat mai** (decisió d'Agus al deploy). Ara no hi ha zombis,
però tampoc no hi ha xarxa.

---

## 7 · L'EXCLUSIÓ MÚTUA — la premissa estava invertida

La pregunta era *«avui és per model; hauria de ser per tècnic?»*.

**Avui ja és per tècnic, i per model no existeix cap mutex.** L'únic lock del sistema és el del
document `.ftt` (per document i per usuari, TTL 30 min), que no té res a veure amb les tasques.

**I l'exclusió per tècnic està trencada.** El motiu és precís i important per al disseny:

> L'exclusió mira **`assignee`** (camp de *planificació*), però el rellotge s'ancora a **`tecnic`**
> (qui hi és de debò). I `transition_task` només escriu `assignee` **si és `None`**. Per tant,
> sempre que **qui treballa ≠ qui la té assignada**, la invariant cau.

**Cas real a la BD:** el 24/06 el tècnic 1 va tenir **dos trams oberts alhora** (timers 116 i 117)
perquè la tasca 253 tenia `assignee = 13` mentre ell hi treballava. 122 minuts i 0 minuts
registrats en paral·lel.

**Conseqüències vives:**

- Dos tècnics poden treballar el mateix model alhora sense cap traça.
- Un **handoff** (claim o Play sobre tasca d'altri) reassigna la tasca **sense tancar el tram de
  l'anterior i sense escriure cap `TaskTransition`**: el rellotge segueix imputant a qui ja no hi
  és, i el nou treballa sense timer propi.
- No hi ha cap bloqueig de fila: dues transicions concurrents passen totes dues (cas real: dues
  `InProgress→Paused` idèntiques separades per **6 ms**).

---

## 8 · QUÈ S'HA ARREGLAT (3 commits, cap push)

| Commit | Fix |
|---|---|
| `fad10351` | **El 409 de reobertura diu la paret.** `TransitionError` guanya un `code`; el guard d'albarà l'omple (`tasca_albaranada`) i el front tria la frase. Abans arribava mut. |
| `55978598` | **L'override de QA del guard es consumeix en llegir-lo.** Ja no pot quedar encès; fora de rang s'ignora; només escurçar, mai allargar. |
| `89009858` | **El tram de temps deixa de ser escrivible pel client.** `TimerEntradaViewSet` era un `ModelViewSet` complet: `POST`/`PUT`/`PATCH`/`DELETE /api/v1/timers/` oberts amb només `IsAuthenticated` i `inici`+`model_task` escrivibles → **el temps facturable era inventable i esborrable des del navegador, per id**, sense cap transició ni rastre al log. Ara `ReadOnlyModelViewSet`. Cap consumidor perdut. |

**Verificació:** `fhort.tasks` → **88 tests · OK**.

---

## 9 · EL 409 DEL MODEL 188 — el cas que il·lustra la decisió més urgent

El mateix 04/08, entre les 16:21 i les 18:28, **set `POST open-task` van tornar 409** sobre el
model 188. Causa verificada: les tasques `pom` (256) i `pattern_cad` (272) són `Done` i tenen
línia a l'albarà 5, **EMÈS**. El guard de reobertura les bloqueja per sempre.

El toast ja diu el motiu (`fad10351`), però **la porta segueix tapiada**: tota la feina que es
faci a partir d'ara sobre aquell model **no pot tenir rellotge**. Afecta tots els models ja
albaranats. → **decisió D-5**.

---

## 10 · LES DECISIONS OBERTES (això és el que cal dissenyar)

**D-1 · Quin gest obre el rellotge de la fitxa tècnica?**
Avui «Modificar» i «Previsualitzar» fan exactament el mateix i cap compta.
(a) «Modificar» obre tasca i «Previsualitzar» és consulta de debò · (b) tots dos obren ·
(c) cap obre, però llavors **cal recuperar la porta que el Kanban feia**.

**D-2 · Què vol dir que una tasca està «en curs»?**
(a) la porta oberta (avui) · (b) la sessió de treball: s'obre en entrar al model i es tanca amb un
gest explícit; els desats intermedis no la tanquen · (c) l'escriptura: qualsevol escriptura
obre-si-cal i imputa fins a la inactivitat.
**(b) i (c) fan desaparèixer el ping-pong i bona part de la contaminació.**

**D-3 · Una mostra de temps = una tasca o un tancament?**
(a) una tasca = una mostra (la reobertura *actualitza*) · (b) un tram = una mostra (l'increment) ·
(c) es queda com és. Cal decidir també **si es passa `recompute_welford --apply`** — avui no neteja
res.

**D-4 · Hi ha d'haver llindar INFERIOR de mostra?**
Hi ha sostre (24 h) i cap terra. Amb `2, 9, 3, 4, 2` min una cel·la ja mana.

**D-5 · Es pot reobrir una tasca albaranada?**
(a) es manté i s'obre una tasca **ad-hoc nova** per a la feina posterior · (b) es manté i només es
comunica millor · (c) es permet i la rectificació genera línia al proper albarà.
**Sense això, el model 188 i tots els albaranats queden sense rellotge per sempre.**

**D-6 · L'exclusió s'ancora a `assignee` o a qui treballa?**
(a) mirar els trams oberts · (b) `transition_task` reassigna sempre · (c) es manté.

**D-7 · Un handoff, què fa amb el tram obert?**
(a) el tanca i n'obre un de nou marcat · (b) es prohibeix el claim sobre una tasca amb tram obert.

**D-8 · Dos tècnics poden treballar el mateix model alhora?**
Avui sí i sense traça. Cal dir si és funcionalitat o accident.

**D-9 · S'instal·la la cron del guard?**
Llesta des del 27/07.

**D-10 · Obrir una eina ha de meritar?**
Avui la primera `→InProgress` **factura el model** (`ConsumptionRecord` + event) i reancora el pla.
Tocar una porta 3 segons per error factura. Verificat: els 21 registres tenen
`merited_at == started_at`.

---

## 11 · FIXOS MECÀNICS DESCARTATS I PER QUÈ (per no reobrir-los per inèrcia)

| Fix descartat | Motiu |
|---|---|
| **Arreglar el mutex** | És D-6 amb tres opcions obertes. `assignee` és alhora camp de planificació: canviar qui l'escriu és política. |
| **Matar el ping-pong del desat** | Canvia *si desar marca la tasca com a feta* → D-2. |
| **`select_for_update` a les transicions** | El lock converteix un duplicat avui silenciós en un **400 visible** a l'usuari. Triar entre «error» i «no-op idempotent» és política. |
| **Filtrar els trams de 0 min del Welford** | 🔵 **Provat inert amb dades:** el càlcul *suma* minuts i un tram de 0 aporta 0 → canvia **0 de 49 mostres** (14 295 min a les dues bandes). Cap lectura els compta (totes `Sum`, mai `count`). I el guard «durada 0 no és mostra» ja existeix. La contaminació real són les 28 mostres duplicades → D-3. |

**Trobat construint, per a la llista:** l'acció `tancar` (viva a la pàgina de temps) tanca un tram
**sense passar per `transition_task`**, deixant la tasca En curs sense tram obert — l'anomalia
«orfes» que el cron compta i no toca.

---

## 12 · NOTA DE MÈTODE

El brief demanava reconstruir una sessió concreta sobre el **model 195**. **Aquell model no
existeix a staging** (45 models, ids 162–1307 amb el forat 189–246) i **no hi ha cap traça seva a
cap access log del servidor**. La reconstrucció es va fer amb el corpus viu (217 timers, 457
transicions) i amb la sessió real del model 188, que arriba a les mateixes conclusions amb proves.
Si el 195 era a PROD, no és observable des d'aquí i el backup del dia és anterior a la sessió.

---

*Patró A · el detall amb `fitxer:línia` i les consultes SQL viuen a
`docs/diagnosis/DIAGNOSI_CICLE_TASCA_COMPLET.md`.*
