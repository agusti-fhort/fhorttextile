# REPORT · QA del modal de sortida d'una superfície de treball

> **Data:** 2026-08-06 · staging `dev` · **cap push · cap suite** · `git add` selectiu.
> **Símptoma d'origen** (captura d'Agus, model `BRW-SS26-0002`, sortint de «Mesurar prenda»):
> el modal deia **«Transició no permesa: Paused → Paused»** i **«Aquesta sessió: 0h 00m · total
> de la tasca: 0h 00m»**.

## 0 · Els commits

| # | commit | què |
|---|---|---|
| 11 | `c03f13be` | escriure no reobre una tasca acabada, i la paret d'albarà passa a tenir un sol lloc |
| 12 | `6ffdf4e8` | el modal de sortida decideix amb l'estat FRESC, i per això ja no menteix ni peta |

**Gate:** `manage.py check` net · `npm run build` net · els tres fitxers de test tocats,
**20 OK**. La correguda completa de `fhort.tasks` (237 tests) va servir per trobar dues
regressions meves; totes dues corregides (v. §5).

---

## 1 · Q1 · «Transició no permesa: Paused → Paused»

### El mecanisme, reproduït

1. S'entra a «Mesurar prenda» → `open-task` deixa la tasca `InProgress` i obre tram.
2. **Als 30 minuts el guard de tasca oblidada la pausa sol** (`auto='guard_30min'`), i tanca el
   tram. La persona segueix a la pantalla: res no li diu que la tasca ja no està oberta.
3. En sortir, el modal ofereix «La pauso» → `POST transition {to_status:'Paused'}` sobre una
   tasca que ja és `Paused` → `400` → **el text cru de la nostra màquina d'estats a la cara de
   qui només volia plegar**.

Traça real de la tasca `342` (la de la captura): dues de les seves quatre pauses porten
`auto='guard_30min'`, i els seus trams duren **33,1** i **33,0** minuts (30 + 3 de gràcia).

### La decisió, i el motiu

**No es toca la màquina d'estats. El modal no s'obre si no hi ha res a decidir.**

`ModelSheet.exitEdit` demana la tasca **fresca** i només obre el modal si segueix `InProgress`,
que és **l'únic estat des del qual les dues opcions del modal són legals**. Si el guard (o un
altre gest) ja l'ha tancada, sortir és sortir.

Es va descartar el «no-op silenciós» com a *única* mesura: hauria tapat el símptoma deixant el
modal preguntant sobre una tasca que ja no està oberta —el temps que hi ensenya ja no és el de
ningú—. I es va descartar obrir `Paused → Paused` a `ALLOWED`: no és una transició, és una
petició que ja no té sentit.

**Segona barrera, per a la cursa real:** el guard pot pausar entre que es llegeix l'estat i es
prem el botó (són segons, però existeixen). Si passa, el rebuig es tracta com el que és —*l'estat
que la persona demanava ja hi és*— i el modal **es tanca com un èxit, sense dir res**. La resta
d'errors (xarxa, permisos) es diuen amb el missatge de la casa, **mai amb el text cru del
servidor**.

### Verificat al navegador (dist real, A/B)

| bundle | modal | resultat de prémer «La pauso» |
|---|---|---|
| **abans** (`c03f13be`) | surt | `400` · **«Transició no permesa: Paused → Paused»** · modal encallat obert |
| **després** (`6ffdf4e8`) | **no surt** | cap `POST transition`; sortida neta, consola neta |

---

## 2 · 🔴 Q2 · Per què el total era «0h 00m»

### La hipòtesi del brief no es confirma — i és important

> *«Comprovar si entrar a la superfície d'una tasca PAUSADA la reobre. Si no ho fa, el batec de
> F1.3 no cobreix el cas Paused i TOTA la feina sobre tasques pausades no es compta.»*

**Sí que la reobre, per les dues portes**, i està mesurat:

- **navegació:** el log de transicions de la tasca 342 té tres `Paused → InProgress` (`698`,
  `702`, `704`), una per cada entrada a la superfície. `open-task` obre tram.
- **escriptura:** `batec_escriptura` fa `Paused → InProgress` i obre tram amb `last_heartbeat`
  estampat. Fixat ara amb test, també **per la porta HTTP real de la pantalla**
  (`PATCH /size-check-lines/<id>/`).

Cens del camí sencer: `navegació → tasca_vigent → transició → tram` — **cap graó trencat**.

### La causa real: **el modal decidia amb una FOTO**

`ModelSheet` passava al modal la fila de `modelTaskRows`, que és la llista carregada **en obrir
la pàgina**. Ni el camí `?task_id=` ni el pas del temps la refresquen. O sigui que el modal
ensenyava el temps del moment d'ENTRAR, no el de SORTIR:

- `minutsSessio` ← `sessio_inici` de la foto → `null` en entrar → **0h 00m**;
- `minutsTotal` ← `temps_consumit_min` de la foto → el que hi havia **abans** de la sessió. A la
  tasca de la captura, l'únic tram anterior durava 0,7 min i `_close_open_timer` fa `//60` →
  **0 minuts acumulats** → «total de la tasca: 0h 00m».

El modal no mentia sobre el rellotge del servidor: **llegia un altre moment.**

### Verificat al navegador (A/B, amb el servidor dient 34 min durant la sessió)

| bundle | què ensenya el modal |
|---|---|
| **abans** | `sessió: 0h 00m · total de la tasca: **0h 02m**` ← la foto |
| **després** | `sessió: 0h 00m · total de la tasca: **0h 34m**` ← el servidor |

### El test que ho fixa

`backend/fhort/tasks/test_batec_sobre_pausada.py` (6 casos): escriure sobre una `Paused` la
reobre i obre tram · el tram neix amb segell · escriure sobre una `InProgress` renova i no
n'obre un segon · **el camí sencer per la porta HTTP de la presa** · una `Done` no es reobre ·
i que `ALLOWED['Paused']` no conté ni `Paused` ni `Done` (que és el fet del qual depèn el
criteri del modal).

### 🚩 Una troballa del cens que NO és un defecte, però que has de saber

    TRAMS totals: 240 · amb `last_heartbeat`: 3 · SENSE: 237

El batec gairebé no ha marcat mai res. **No és que estigui trencat** — ho he comprovat sobre les
dues finestres de 33 minuts de la captura: **0 canvis de mesura**. Ningú no hi va escriure; la
pantalla era oberta i prou.

La conseqüència sí que val la pena mirar-la, perquè és el que va disparar tot això: **el guard
s'ancora a `last_heartbeat` o, si no n'hi ha cap, a `inici`**, i el seu disparador és *la durada
des de l'obertura, no la inactivitat* (decisió escrita a la capçalera de
`GuardTascaOblidada.jsx`). Amb aquesta regla, **qui llegeix o pensa mitja hora sense teclejar
queda pausat igual que qui ha marxat a dinar**. És una decisió teva, no un defecte, i la deixo
anotada perquè és el mecanisme que va produir el símptoma.

---

## 3 · Q3 · El modal no surt si no hi ha hagut sessió

Abans n'hi havia prou d'entrar per `?task_id=` —que registra la tasca però **no obre res**— i
tornar a sortir sense tocar res: el modal sortia igual. `exitEdit` només mirava que
`activeTaskRef` no fos buit. El comentari del codi ja prometia el contrari («sense tram viu no
hi ha res a decidir»); **el codi no ho feia**.

Ara el criteri és **què hi ha obert AL SERVIDOR en sortir**, no el que el front recordi.

> ⚠️ **El criteri NO és la durada.** «No hi ha hagut sessió» ≠ «la sessió va durar poc»: una
> sessió de dos minuts amb la tasca oberta ensenya el modal exactament igual que una de dues
> hores (decisió d'Agus). El que el fa callar és que **no hi hagi res obert**.

---

## 4 · Q4 · La taula de tots els estats en sortir

Cada fila **oberta al navegador amb el `dist` real**, model `188`, sortint de la superfície de
treball. Consola neta a tots els casos.

| estat en sortir | modal | què ofereix | transició demanada | comprovat |
|---|---|---|---|---|
| **Pending** | **no surt** | — | cap | ✅ no hi ha res obert: no hi ha res a tancar |
| **InProgress** | **surt** | «L'he acabat» (premarcat) · «La pauso» | `Done` / `Paused`, **totes dues legals** | ✅ confirmar → `200`, modal es tanca, cap error |
| **Paused** | **no surt** | — | cap | ✅ el guard (o un altre gest) ja ha decidit; era el cas de la captura |
| **Done** | **no surt** | — | cap | ✅ una tasca feta no es torna a preguntar |
| **Done + albaranada** (tasca `256`) | **no surt** | — | cap | ✅ i, a més, escriure-hi ja no la pot reobrir (§5) |

**Temps que ensenya el modal**, quan surt: `sessio_inici` i `temps_consumit_min` **frescos del
servidor**, no de la llista.

---

## 5 · El que la suite em va ensenyar (dues regressions meves, corregides)

Córrer `fhort.tasks` sencer (237 tests) va tombar dues coses:

1. 🔴 **Havia obert `Paused → Done` a `ALLOWED`.** `test_stop_encadenat` ho va aturar i el seu
   encapçalament diu per què: **«DECISIÓ Patró C (Agus, 28/07): la màquina d'estats NO es toca.
   `Paused → Done` segueix PROHIBIDA»** — el Stop sobre una tasca pausada és **play+stop
   encadenat**. **Revertit.** No em calia: amb el modal obrint-se només sobre `InProgress`, aquella
   transició no es demana mai.
2. **La paret d'albarà perdia el seu codi.** El meu tall per a `Done` al batec passava per davant
   i tornava `acabada` on `test_batec_escriptura` esperava `refusada` + `tasca_albaranada`.
   Corregit **sense duplicar el criteri**: s'ha extret a `te_paret_albara()`, punt únic que
   comparteixen `transition_task` i el batec.

### I una troballa pròpia de Q4, que era un defecte de veritat

Mesurant el cas «Done → sortir» va sortir que **un `PATCH` sobre una cel·la d'una tasca ja
tancada la reobria**: `ALLOWED` permet `Done → InProgress` perquè la reobertura existeix com a
acte humà (rectificació), i el batec se n'aprofitava sense voler — obria tram i reiniciava el
rellotge, **en silenci**. Només se'n salvaven les ja **facturades**, que topaven amb la paret
d'albarà; totes les altres queien.

La capçalera del propi mòdul ja declarava el contracte —«tasca `Pending`/`Paused` →
`InProgress`»— i `Done` no hi era. **Ara el codi diu el mateix que el comentari.**

---

## 6 · Verificació

- **Banc:** `frontend/dist` REAL servit per un servidor propi que dona l'API des del `Client` de
  test de Django amb `force_login`. **Cap escriptura a staging**: les transicions es **jutgen**
  amb un mirall de `services_c.ALLOWED` i es responen sense escriure res.
- **A/B** contra el bundle anterior (`git worktree` al commit pare) per demostrar els dos
  símptomes i la seva desaparició.
- L'estat de la tasca es força al banc (`QA_TASCA=305:Paused`) per recórrer tots els casos de Q4
  sense tocar la BD.
- **Consola neta a totes les passades.**
- ⚠️ Model `BRW-SS26-0002` **no s'ha tocat**: Agus hi estava treballant en viu mentre es
  diagnosticava (la seva tasca `342` va passar a `Done` entre dues consultes). Tota la
  verificació s'ha fet sobre el model `188`.

## 7 · La cua oberta

| # | què |
|---|---|
| 🚩 1 | **El guard pausa per DURADA, no per inactivitat** (decisió escrita). Qui llegeix mitja hora sense teclejar queda pausat. És el mecanisme que va produir el símptoma: val la pena decidir si es manté. |
| 🚩 2 | Una tasca pausada pel guard **no ho diu a la pantalla**: la persona segueix treballant sense saber que el rellotge s'ha aturat. |
| 🚩 3 | `_close_open_timer` fa `//60`: un tram de 0,7 min val **0 minuts**. Amb sessions curtes, el total pot seguir dient 0 sense que res estigui trencat. |
