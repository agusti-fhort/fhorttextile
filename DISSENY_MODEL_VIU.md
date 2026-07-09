# DISSENY_MODEL_VIU — el model com a subjecte de la plataforma

> Estat de disseny **congelat** (sessió 2026-06-18/19). FHORT Textile Tech.
> No és implementació ni diagnosi. És el punt de partida per a la **Fase A.2** (redacció del
> document de domini) de la propera sessió.
> Continua i reenquadra `FLUX_FITTING_SIZECHECK.md` (Fase A) després de la crítica del PPx, de
> validar el model contra un cas real (Olivia Dress, Brownie), i d'ampliar-lo amb les capes
> (producció / patrimoni / governança), l'entorn d'usabilitat, la capa de disseny i l'economia
> del treball.
> Participants del disseny: Agus (CTO/decisió), Claude, i PPx (revisió externa).
> Abast del reenquadrament: model · tasques · planificació · disseny · economia del treball.

---

## MISSIÓ DEL SISTEMA

> **Preservar el context de treball d'un model al llarg del temps, de manera que qualsevol tècnic
> pugui reprendre'l, entendre'l i continuar-lo sense haver de reconstruir mentalment la seva
> història.**

No és una frase de visió ni de màrqueting. És una **propietat emergent** que el disseny ha
descobert: gairebé totes les decisions importants de la conversa convergeixen aquí, i cap té
sentit si l'objectiu fos només gestionar dades de patronatge (model com a centre de navegació ·
dissenyar per reprendre · diff temporal · watchpoints persistents · traçabilitat de decisions ·
tests 9:12 i 11:47 · dashboard d'atenció i acció). Totes tenen sentit si l'objectiu és
**preservar context**.

Els tres verbs són els que han aparegut una vegada i una altra:
- **reprendre** (test 9:12),
- **entendre** (estat · canvis · atenció),
- **continuar** (acció · test 11:47).

**Disciplina (la missió elimina opcions, no les justifica):** tota funcionalitat futura es jutja
per una sola pregunta — *ajuda a reprendre, entendre o continuar un model?* Si sí, entra. Si no,
és soroll. Una nova alerta que augmenta el soroll sense augmentar la comprensió del context, no
entra. Una missió val perquè permet **dir que no**.

> Qualsevol PLM pot guardar dades. Pocs sistemes conserven el **context**. No estem construint un
> repositori de dades tècniques; estem construint una plataforma que **preserva el fil de treball
> d'un model en el temps** — substituint correus, Excels, PDFs, converses disperses i memòria
> humana, no guardant-ho, sinó conservant-ne la continuïtat cognitiva.

---

## Frases fundacionals

Si algú només llegeix aquestes cinc, ja té el model mental correcte. Tota la resta del document
n'és conseqüència.

1. **El model és el subjecte.** Una entitat viva que acumula coneixement tècnic fins a producció.
2. **El model és el centre de navegació, no el propietari universal de les dades.** Watchpoints,
   tasques, versions i fittings són entitats fortes amb vida pròpia; el model és el punt d'entrada
   a totes, no el seu contenidor. "Tot passa a través del model" és una afirmació sobre navegació
   i UX, no sobre propietat de dades ni estructura de BD. *(Vacuna contra el "Déu objecte".)*
3. **Les profunditats.** Una mateixa realitat pot existir o no segons la profunditat des de la
   qual s'observa el sistema (usuari / estudi / client). No tot el que existeix al domini ha
   d'existir a totes les profunditats.
4. **La decisió tècnica és un esdeveniment amb rastre, no una entitat.** Es captura al moment de
   tancament; genera múltiples resultats; es registra origen→resultats. Promoció a entitat
   diferida fins que hi hagi evidència.
5. **Es dissenya per reprendre, no per executar.** El software industrial es pensa per executar
   (fes això, després això); aquest es pensa per reprendre (fa tres dies que no toco això, on
   era?). El diff temporal —"què ha canviat"— no és una secció del dashboard; n'és la raó de ser.

---

## 0. El gir de perspectiva

Aquest document **no** és un redisseny del fitting. És un **reenquadrament del centre de
gravetat de la plataforma**, que toca alhora **model, tasques i planificació**.

El gir, en una frase:

> **El centre del sistema no és la mesura, ni el fitting, ni el Kanban. És el MODEL.**

Tota la resta —fittings, tasques, grading, fitxa, watchpoints, decisions— són **mecanismes**:
formes que pren la vida del model. El subjecte és el model; els mecanismes són com viu.

Conseqüència metodològica (criteri rector de tota la resta del disseny):

> **Els gates són una escala de maduresa (ordenada però reversible); l'estat del model és la seva
> realitat actual.** El recorregut Proto→Producció dona direcció, però **no és un workflow que
> s'executa** (no és una cinta de passos obligatoris): és una progressió que el model assoleix —i
> pot desfer (un canvi tardà reescriu el grading)— mentre el seu estat evoluciona lliurement a
> dins. El document de domini comença per *"Què és un model?"*, no per Kanban/Fitting/Grading.

---

## 1. Els tres canvis de perspectiva (què es reordena)

### 1.1 Model — de contenidor de dades a subjecte viu

Abans el tractàvem (implícitament) com l'entitat on pengen dades. Ara és **el subjecte**: el
lloc on s'acumula el coneixement tècnic de com fer una peça, fins que aquell saber és prou
complet i validat (producció).

- El tècnic no entra a "el mòdul de fitting" i després "el Kanban"; **entra a un model i hi
  treballa**. "Entro a l'Olivia, treballo el que toca, surto."
- *(Alineació amb el sistema real, segons `MAPA_SISTEMA`: `Model ⭐` ja és l'entitat central;
  `fase_actual` ja viu al Model; `SizeFitting`, `ModelTask`, `TechSheet`, consum — tot penja del
  Model. L'arquitectura ja és model-cèntrica; el que falta és que el procés que el tècnic viu ho
  reflecteixi.)*

### 1.2 Tasques / Kanban — de centre a escala

El Kanban **no és el centre del sistema; és una porta** i una **vista a escala**. La mateixa
dada (tasques per model) es veu a dues distàncies:

- **Escala plataforma (zoom out):** "els kanbans de tots els models", ordenats per prioritat.
  És la vista de cap de taller / planificació: quins models tenen feina, què bloqueja.
- **Escala model (zoom in):** el kanban *d'aquest* model, dins el seu dashboard, al costat dels
  seus resultats.

El Kanban global **no és un sistema separat**; és **l'agregació dels processos dels models**.
Per això és "porta" (a escala model) i "centre útil" (a escala plataforma) alhora: depèn del
zoom.

### 1.3 Planificació — segueix, però model-cèntrica

El planificador consumeix tasques amb durada + dependències = exactament el que el nou model
produeix. **Reaprofitament, no reescriptura** *(`scheduler_service`, `recompute_for_technicians`)*.
El gir de perspectiva: la planificació també es llegeix **per model** (què té pendent cada
model, quan arriba la propera fita) a més de per tècnic.

**La planificació com a dashboard del PM en temps real.** Si la data de fi es **recalcula segons
la maduresa real** del model (no és una data fixa que algú manté a mà), la planificació deixa de
ser un pla i passa a ser un **instrument viu**: el product manager no mira "el pla de fa tres
setmanes", mira l'estat real del departament i la col·lecció **ara**, i pot decidir sobre dades
vives (un model rejoveneix per un rebuig → la col·lecció s'endarrereix → reassigno capacitat /
canvio prioritats). Planificació **honesta** (llegeix la maduresa, no la imposa) — cosa que cap
eina de gestió de moda fa, perquè totes planifiquen amb dates que menteixen. *(Reaprofita
`recompute_for_technicians`; els gates com a escala de maduresa donen la senyal.)*

---

## 1bis. Les tres capes i el patrimoni del model

El sistema té **tres capes ortogonals** que abans barrejàvem. Separar-les és el que permet
connectar el domini tècnic amb l'econòmic **sense contaminar-los**.

| Capa | Què és | Conté | On es llegeix |
|---|---|---|---|
| **Producció** | les **eines** (activitats productives) | fitting · size set · patrons · fitxa · motor | consumeix hores, recursos, cost |
| **Patrimoni** | el que el model **acumula** | coneixement + esforç (vegeu sota) | el valor i la inversió desats |
| **Governança** | el **rerefons** que observa i coordina | regles · IA · toleràncies · agenda · alertes · planificació | regula i avisa |

### El model creix en DUES dimensions (no una)

Fins ara dèiem "el model acumula coneixement". Incomplet. El model acumula **patrimoni**, que té
dues cares:

- **Coneixement acumulat** — mesures · decisions · versions · watchpoints · historial. *Què
  sabem del model.*
- **Esforç acumulat** — hores invertides · cost consumit · rondes executades · temps extern.
  *Quant ens ha costat arribar-hi.*

Des del negoci, totes dues importen igual. L'Olivia no és només "què en sabem"; és també "quant
ens ha costat". La combinació permet saber si un **model**, un **client**, una **metodologia** o
una **eina** són rendibles — traçabilitat que els PLM tradicionals no tenen.

### La cadena correcta: Eina → Temps → Cost → Decisió → Coneixement

Ni "eines → contingut" (oblida la decisió) ni "decisions → coneixement" (oblida que la decisió no
cau del cel). La cadena completa:

> Les eines són el **mecanisme de producció**. Les decisions transformen aquest treball en
> **coneixement**. I cada ús d'una eina deixa una **petjada de temps** (i, a profunditat d'estudi,
> de cost) que també passa a formar part de la vida del model.

Abans de decidir "el maluc passa a 47", algú ha obert un fitting, ha comparat toleràncies, ha
editat un patró — hores de tècnic que són cost i temps imputable. **Sense aplicar eines no es
crea coneixement nou** (Agus); i aplicar eines **sempre** consumeix temps. Les dues coses són
inseparables.

### Lectura per profunditats (frase fundacional 3 aplicada de dalt a baix)

La **mateixa petjada** d'una eina es llegeix diferent segons la profunditat:

- **Tècnic** (profunditat d'usuari): veu **temps** (l'imputa; ja ho fa avui). Mai veu euros
  mentre treballa — el contaminaria i no és la seva feina.
- **Product manager** (estudi): veu **maduresa i capacitat** → planifica.
- **Direcció** (estudi): veu **cost i rendibilitat** → assignació de costos per **departament ·
  tècnic · model · col·lecció**. Comptabilitat analítica del procés creatiu, que avui viu en la
  boira d'Excels i intuïció.

*(Reaprofitament: el sistema de temps existent —Welford, `TaskTimeEstimate`, registre
d'activitat— ja captura les hores. El que faltava no era la dada, sinó veure-la com a **dimensió
del patrimoni del model**, no com a comptador aïllat.)*

---

## 1ter. L'entorn d'usabilitat: el model com a llenç

La metàfora que uneix l'arquitectura amb la usabilitat: el model és un **document obert** (com un
Word/Excel), i l'experiència té quatre elements.

- **El llenç:** el model obert. El tècnic no entra a mòduls; obre un model i hi treballa.
- **El menú d'eines (a demanda):** fitxa tècnica · size set · fitting · POMs · disseny de patrons
  · motor. **Capacitats que invoques quan les necessites**, no destinacions. El contingut del
  model creix a mesura que les apliques. Una eina pot executar-se **internament** (tècnic FHORT)
  o **externament** (subcontractada) — mateixa eina, atribut intern/extern a la tasca; per a la
  planificació importa (el temps extern és anada-i-tornada que no controles).
- **El rerefons viu (automàtic, no invocat):** analitza · comprova toleràncies · aplica regles ·
  proposa decisions · recalcula · agenda · avisa (arribada de mostra, agenda de fitting sobre N
  models). No és al menú; passa mentre treballes **o mentre no hi ets**. És el que alimenta el
  dashboard i el "què ha canviat" → fa possible "dissenyar per reprendre". (≈ Word amb eines vs
  Google Docs viu: vosaltres feu el segon.)
- **La planificació (entra des de fora):** cataloga els models a fer, prioritza, assigna; la data
  de fi **es recalcula en temps real segons la maduresa**.

Distinció clau: les **eines** són accions humanes (menú); el **rerefons** és ambient (el sistema
actua i et parla). Són dues capes d'interfície diferents, com avisos vs tasques.

**Per què això és "must have":** la competència té les eines com a **mòduls separats** (entres,
surts, entres a un altre) i el context **el guardes tu** (Excels, correus, memòria). FHORT
inverteix les dues coses: eines **dins del model**, context **mantingut pel sistema**. El "must
have" no és el que el sistema fa (fitxa/fitting/grading: tothom les té); és el que **no
t'obliga a fer**: reconstruir el context cada vegada.

---

## 2. La pantalla central: el dashboard del model

Si el model és el subjecte, **el dashboard del model és la pantalla més important del SaaS.**
És on el tècnic viu. Té dues meitats (acció + memòria):

### 2.1 Meitat PROCÉS (acció) — el kanban del model

Què s'ha de fer ara, en quina fase (gate) està. És el que la planificació/Kanban ja saben
gestionar.

### 2.2 Meitat RESULTATS (coneixement) — la part NOVA a construir

El coneixement tècnic que el model ha acumulat. És literalment la definició del model feta
pantalla, i és **la part que aquest redisseny ha de construir bé** (la de procés ja existeix).

El dashboard és un **mapa d'atenció i acció**, no un quadre de mètriques. Un dashboard tradicional
diu "quantes tasques / quants fittings / quants dies". Aquest respon **quatre preguntes humanes**:

1. **On sóc?** — en quina fase/gate i **què bloqueja**. ("Proto · esperant correcció patró coll")
2. **Què ha canviat?** — el *diff* des de l'última visita. El model viu encara que el tècnic no
   hi sigui (mostra arribada, company que ha tancat un patró, urgència del comercial); en tornar
   necessita reorientar-se. És **memòria tècnica amb consciència del temps** — i la funcionalitat
   **més diferenciadora** del producte.
3. **Què requereix la meva atenció?** — els avisos (vegeu §3.9: watchpoints + toleràncies + IA,
   units en presentació).
4. **Què puc fer ara?** — el **context d'acció**. No "Olivia bloquejada perquè Javier ha de
   corregir el coll" (propietat del model) sinó "no pots avançar fins que Javier acabi" (acció).
   Sense aquesta quarta pregunta el dashboard **informa però no habilita**: una pantalla pot
   informar molt bé i seguir sense ajudar a treballar.

Sota d'aquestes quatre, plegat i accessible: l'**estat tècnic** (mesures, versions de fitxa,
historial). Hi és, no domina. El dashboard és un **punt de represa**, no un expedient.

**Continuïtat cognitiva (el que unifica tot):** les preguntes 1-2 (reprendre) i les del test
11:47 (entendre l'impacte) són la mateixa pregunta de fons — *puc mantenir el fil mental del
model sense reconstruir-lo cada vegada?* El dashboard té dues cares temporals: l'**entrada**
(reprendre: què m'he trobat) i la **sortida** (tancar: què deixo).

**Prova contra l'Olivia (flueix):**

```
Olivia · Proto
  On sóc:    esperant correcció patró coll (Javier) — bloquejat
  Canvis:    mostra taronja rebuda · hip propagat a +2 (E=47)
  Atenció:   deformació escot · J1 sensible a producció
  Puc fer:   revisar fit de la mostra · anotar nous comentaris
  (estat tècnic: 13 POMs · fitxa v2 · base S) — plegat
```

---

## 3. Conceptes congelats (mecanismes, subordinats al model)

Tot el que segueix són **mecanismes** de la vida del model. Vocabulari mínim de cara a l'usuari;
la resta, intern.

### 3.0 La capa de disseny — l'inici real de la vida del model

Abans del desenvolupament tècnic hi ha una fase que avui cau **fora de tot càlcul**: la
dissenyadora treballa sense control explícit. Si la fem **iniciar el procés dins el sistema**,
guanyem la traçabilitat des de zero i tanquem el forat pel davant del patrimoni (l'esforç
començava massa tard).

- **Naturalesa:** tasca/control, **sense eines internes**. No construïm un editor de disseny ni
  competim amb el que la dissenyadora ja fa servir (Illustrator/CLO…). Mateixa frontera dura que
  el motor de patrons: control sí, eines internes no.
- **Mínima fricció (condició de viabilitat):** la dissenyadora ja fa una fitxa de disseny; l'únic
  que canvia és que **inicia el procés al sistema** i **puja aquell document que ja existeix**.
  Cap feina nova; el treball que ja fa deixa rastre. Cost d'adopció ~0, valor alt.
- **Què aporta:** cost de disseny (avui invisible) entra al patrimoni · primer coneixement
  acumulat (la fitxa de disseny) · l'inici real del rellotge del model.

### 3.0bis Design freeze — el primer gate, condicionat i decidit pel PM

El **design freeze** és el moment exacte en què el disseny es congela i es traspassa a
patronatge. Avui passa però és invisible; registrar-lo és or per a planificació, comptabilitat i
traçabilitat. És un **gate condicionat per dues senyals externes registrables**:

1. **Acceptació de disseny** — el disseny està aprovat com a tal (encaix a col·lecció, validació
   comercial / els comercials el compren).
2. **OK de compres** — el departament de compres ha validat el **BOM** (materials, costos,
   proveïdors viables).

Comportament:

- Les dues senyals són **events externs que es registren** (qui, quan), no tasques que el sistema
  orquestra. Registrem el **senyal**, no el procés que el genera (mateix patró que el size fitting
  "a casa del client").
- Les dues senyals **habiliten** però **no disparen soles**. **Qui decideix el freeze és el
  product manager (PM).** Manual assistit (com el tancament de fase): el sistema diu "ja pots",
  l'humà decideix.
- En prémer el freeze, el **PM** en un sol acte: **planifica** la tasca tècnica del model ·
  **assigna** la feina → **llum verda al tècnic**, amb dimensió de tasques a executar. El rellotge
  del model arrenca de debò aquí. És el **punt de transferència** disseny→desenvolupament, i el PM
  qui el governa.
- Si falta alguna senyal, el model **no avança** (les senyals bloquegen, com els avisos §3.9).

**Anàlisi de mortalitat de models (valor de negoci):** avui, un model que es para abans del freeze
**es tanca sense més** i el seu cost de disseny desapareix sense rastre ni causa. Registrant les
dues senyals, el cost consumit per un model que mor queda marcat com a **"no madurat"** amb la
causa (disseny no acceptat / BOM inviable). Això habilita, a profunditat d'estudi/direcció, saber
**quant esforç s'inverteix en models que no arriben a producció i per què** — cost que avui es
llença invisible. *(El patrimoni d'un model mort no és zero: és el que va costar fins que va
morir.)*

La cadena completa de la vida del model:

```
DISSENY (dissenyadora: tasca + fitxa de disseny)
   ├─ senyal 1: acceptació de disseny ─┐
   │                                    ├─► [el PM decideix el FREEZE] → planifica + assigna
   └─ senyal 2: OK de compres (BOM) ───┘                                  → llum verda al tècnic
                                                                                    │
DESENVOLUPAMENT (tècnic) → PROTO → Size Set → PP Sample → PRODUCCIÓ ◄────────────────┘
```

### 3.1 Gates — la progressió del model (QUATRE, per evidència Olivia)

```
Proto → Size Set → PP Sample → Producció
```

Evidència documental: l'Olivia té Size Set i PP Sample com a fites separades amb dates pròpies.
**No són tres (Proto/Sample/Producció)** — posar "Sample" genèric faria que l'usuari preguntés
"i el Size Set on és?" i es perdria credibilitat. *(El sistema ja té gates via
`Model.fase_actual` + `GateEvent` + `advance_phase`/`regress`; cal alinear-los a quatre.)*

El gate **no és estrictament forward-only a nivell de dades:** un canvi tardà (a l'Olivia, +4 cm
de llargada aprovats a producció) reescriu el grading. Ho absorbeix `GradingVersion` v+1.

### 3.2 Size Fitting vs Grading Fitting

- **Size Fitting** — sobre **talla base**. Decisió per POM, anotacions, fotos. No propaga, no
  escala. *(≈ `SizeCheck`/`SizeCheckLine` + `resolve_size_check`, accept/reject ja existeix.)*
- **Grading Fitting** — **totes les talles**: propaga, escala, regles STEP/LINEAR, fitxa
  completa. *(≈ `GradingVersion` + grading engine + `PieceFitting`.)*

> ⚠️ **Col·lisió de nom a resoldre a Fase B:** ja existeix `fitting.SizeFitting` que sembla el
> contenidor del grading per gate, no el "Size Fitting de talla base". Decisió de mapeig pendent.
> No fixar codi fins resoldre-ho.

### 3.3 Els quatre tipus de correcció (output del fitting)

De l'anàlisi de l'Olivia:

1. **Correcció de patró** — p. ex. neckline +5 cm, reduir volum frontal. *(no canvia mida)*
2. **Correcció dimensional** — p. ex. hip +2 cm, tie −40 cm.
3. **Correcció constructiva** — p. ex. punts interns al waistband, reforç, seqüència de
   confecció. **Viatja a la mostra següent.** *(forat detectat: avui no té casa al model.)*
4. **Observació de control** → **no és correcció, és watchpoint** (§3.4).

Un sol comentari de fit pot generar **diversos outputs simultanis** (a l'Olivia, el hip genera
dimensional + patró alhora).

### 3.4 Watchpoint — comportament sòlid, classificació oberta

"Vigilar E", "J1 sensible", "controlar costura" **no demanen feina; deixen memòria tècnica.**
Més semblant a una nota mèdica que a una ordre de treball. **No és una tasca i no és un tercer
botó del tancament** (neixeria petit i acabaria sent una segona tasca).

És la peça **més consolidada** de tot el disseny: té necessitat real, cicle de vida propi i genera
consultes de negoci reals (passa el test de "quina consulta voldrà fer la Montse d'aquí un any?").
De fet la valida **dues vegades** ara (vegeu §3.10: també el desbordament d'abast comercial té el
mateix comportament). És l'entitat que més probablement existirà al producte.

- **Comportament (congelat):** origen (quina ronda l'ha creat), text, fotos opcionals, severitat,
  estat (actiu/resolt).
- **Travessa gates:** una tasca viu *dins* d'un gate; un watchpoint viu *entre* gates. Es crea a
  Proto, segueix visible a Size Set i PP Sample, es valida/resol a Producció.

> ⚠️ **Classificació NO congelada (correcció PPx):** afirmar "el watchpoint és X i el comercial és
> Y" pressuposa una taxonomia que encara no sabem. Watchpoint / tolerància / suggeriment IA /
> avís comercial podrien formar una família més gran d'aquí uns mesos. Per tant **es congela el
> comportament** (avisa / persisteix o no / bloqueja o no / requereix acció o no) i **es deixa
> oberta la classificació**. Vegeu §3.9.

### 3.5 La decisió tècnica — principi rector, NO entitat (en aquesta fase)

Descoberta central de l'Olivia: **el sistema gira al voltant de la decisió tècnica, no de la
mesura.** El valor no és registrar que el maluc passa de 45 a 47; és registrar que **algú ha
decidit** que passi, **per què**, i **què genera** la decisió.

Però la decisió **no es modela com a entitat de primer ordre** en aquesta fase. Formulació
congelada (literal):

- La decisió tècnica és la **unitat conceptual** del procés.
- Es **captura en el moment de tancament** d'una observació (el tancament assistit).
- Pot generar **múltiples resultats simultanis** (patró, dimensional, constructiu, watchpoint).
- Es registra amb **traçabilitat origen → resultats**.
- **No es modela com a entitat** de primer ordre ara.
- La seva promoció a entitat persistent queda **explícitament diferida** fins que Fase B/C aporti
  evidència que genera consultes, estats o comportaments propis.

Raó: les sis preguntes que descarten el watchpoint-com-a-tasca (té estat? es reobre? es
versiona? dependències? qui la tanca? qui l'aprova?) s'apliquen igual a una hipotètica
"Decision" → construiria un sistema paral·lel al de tasques. La decisió és un **moment/acte/
causa**, no un objecte de treball.

### 3.6 Tancament assistit — binari, amb watchpoints a part

En completar una fase, el sistema fa **preguntes dirigides** i el tècnic decideix (manual
assistit, no automàtic):

- *Modificar patrons?* · *Propagar?* · *Fer fitxa tècnica?* (sense "Cal" al davant)
- **Sí** → genera tasca (cua per prioritat, o per data si "ho faré demà"); reassignable a
  naturalesa o a un company.
- **No** → **es registra com a resolt** (constància; cap cap solt).
- La creació de **watchpoints** és una acció **a part**, no un tercer botó (§3.4).

**L'arbre de dependències** (què pot disparar què) viu **al codi** (§4.1), no és configurable per
tenant. És de **suggeriment, no d'automatització**: diu què és possible; l'humà decideix què
s'activa. Màquina d'estats event-driven amb assistència, no workflow rígid.

### 3.7 Joc de POMs — estable, propietat del patronista

El joc de POMs el **fixa el patronista** i **rarament** canvia. Afegir-ne un de nou (a l'Olivia,
el folre que apareix al grading de producció) és un **esdeveniment rar i explícit**, no el flux
normal. Les rondes treballen sobre un joc de POMs **donat i estable** — no gestionen aparició
dinàmica. *(Corregeix una sobre-modelització: no obrir la porta a POMs que creixen lliurement.)*

### 3.8 Tasca de llarga vida — es tanca + ronda nova vinculada

Una tasca **es tanca**; la reobertura **crea una ronda nova vinculada** (no una entitat
immortal). Historial consultable, no monstruós. *(S'alinea amb `TaskTransition`, que registra
transicions sense reescriure la tasca.)* Completar una fase **≠** tancar la tasca/model: el
tancament real és l'**OK final autoritzat** (capacitat específica, p. ex. Montse).

### 3.9 Avisos — comportament unificat, taxonomia oberta

El dashboard rep avisos de (com a mínim) tres orígens, i un quart futur:

1. **Watchpoint** — memòria tècnica que un humà ha deixat conscientment ("vigilar J1").
   Persisteix, travessa gates.
2. **Tolerància de dades** — el sistema detecta que una mesura surt de rang i avisa. **Efímer i
   recalculable** (si la dada torna a rang, desapareix; no és memòria, és estat actual).
3. **Suggeriment IA** — proposta d'una API d'IA. **Descartable** (el tècnic l'accepta o l'ignora;
   no és veritat, és proposta).
4. *(futur)* **Avís comercial** — desbordament d'abast (§3.10).

**Comportament congelat / taxonomia oberta:** els tres tenen naturaleses i cicles de vida
diferents (humà-persistent / detecció-efímera / suggeriment-descartable) i **no s'han de
col·lapsar en model**. El que es congela és el **comportament observable**: *avisa / persisteix o
no / bloqueja o no / requereix acció o no*. Si formen una família ("Senyal") o segueixen sent
entitats separades és **pregunta oberta** — la decideix Fase B/C/ús real, no l'elegància.

**"Senyal" = vista de presentació, no entitat (proposta PPx).** El tècnic no vol saber si una
cosa ve d'una regla, d'una IA o d'una persona; vol saber *he de mirar això o no?* Per tant a la
**capa de presentació** del dashboard ("què requereix la meva atenció") tots els avisos es
mostren units com a coses que reclamen atenció (amb origen / severitat / persistència / acció).
**A sota** continuen sent `Watchpoint`, `ToleranceAlert`, `AISuggestion` separats. La unificació
és d'experiència, no de model.

> Nota inventari Fase B: confirmar quins d'aquests existeixen avui (viu/stub) vs futurs. La
> redacció és vàlida tant si n'hi ha un com quatre — es descriuen pel comportament, no per
> l'existència.

### 3.10 Profunditats i capa comercial (identificar, no desenvolupar)

El SaaS té **dues profunditats**:

- **Profunditat d'usuari** (tenant client, ús intern de patronatge): **sense capa comercial**. La
  Montse veu el procés tècnic, no facturació.
- **Profunditat d'estudi** (FHORT i futurs tenants que reven el servei): **amb capa comercial**
  (contracte, abast, facturació, desbordament).

Principi (frase fundacional 3): una realitat existeix o no segons la profunditat. El client
contracta un abast (p. ex. fitxa + X sessions + modificació de patrons); una correcció pot
**desbordar l'abast** → ampliar facturació + **aturar el desenvolupament fins acceptació del
client**. És un control de negoci.

**Decisió:** la capa comercial **s'identifica i es modela conceptualment, no es desenvolupa.** El
model tècnic NO porta camps ni lògica de facturació (contaminaria el subjecte tècnic amb una
preocupació d'una altra profunditat). El que sí es deixa és el **seam**: l'esdeveniment del model
tècnic que, quan la capa comercial s'activi, dispararà l'avís comercial — una correcció que el
tancament assistit marca com a **extensa**. Identifiquem el punt d'enganxall; no construïm el que
en penja. *(Viu a la profunditat d'estudi / `backoffice`.)*

El **desbordament d'abast comparteix comportament** amb els altres avisos (avisa/persisteix/
bloqueja/requereix acció), cosa que reforça §3.9: no és ni "tipus de watchpoint" ni entitat
decidida — la família està per determinar.

---

## 3bis. Tests d'acceptació — la vara de mesura

Dos tests, formulats com a preguntes verificables (no "serà intuïtiu" ni "experiència fluïda" —
fum no validable). Junts són **la mateixa pregunta**: *pot el tècnic mantenir el fil mental del
model sense reconstruir-lo cada vegada?* (= continuïtat cognitiva = la missió).

**Test 9:12 — reprendre** (la Montse entra al model després de dies sense tocar-lo). En <10 s sap:
- On és el model?
- Què ha canviat (mentre no hi era)?
- Què requereix la seva atenció?
- Què la bloqueja?
- Què pot fer ara?

**Test 11:47 — treballar** (ha estat dues hores treballant; ara tanca o fa una pausa). Sap:
- Què ha avançat?
- Què ha provocat? *(els outputs de les seves decisions — el rastre origen→resultats, §3.5)*
- Qui depèn ara de la seva feina? *(les tasques que ha generat per a altres)*
- Què queda pendent?

El test 11:47 és el que **paga** la decisió de no fer la decisió una entitat: la traçabilitat com
a **conseqüència visible**, no com a taula, és el que respon "què he provocat / qui depèn de mi".

> ⚠️ **Disciplina (correcció PPx): dos nivells, no confondre'ls.**
> - **Criteri de suficiència del model conceptual (A.2, validable sobre paper):** el model conté
>   la informació necessària per **poder** respondre les nou preguntes? (p. ex. hi ha rastre
>   origen→resultats per respondre "qui depèn de mi?"). Això sí es valida al document.
> - **Tests d'usabilitat de producte (diferits a després de Fase C):** una **Montse real** davant
>   d'una pantalla fa el que descriuen. **Només aquí es resolen de debò.**
>
> Risc a evitar: creure'ls resolts perquè estan ben escrits. Un document pot descriure 9:12
> impecablement i el producte fallar-lo. "Ben escrit" ≠ "resolt".

---

## 4. Principis d'arquitectura

### 4.1 El procés viu al codi, no és configurable per tenant

Tipus de tasca, naturaleses, gates i **arbre de dependències** = **el procés de negoci de
FHORT** (el producte que es compra), no dades de client. Van **al codi** (constants/enums/
estructura), iguals per a tots els tenants. Per-tenant són les **instàncies** (models, rondes,
temps).

> ⚠️ **Contradicció a resoldre (Fase B):** `tasks.TaskType` és TENANT i la pantalla "Catàleg de
> tipus de tasca" és editable. La decisió és **migrar el catàleg a codi** (o global no-editable).
> Confirmar abast a Fase B; `get_allowed_task_types` (allow-list de capacitats) es pot conservar.

### 4.2 Hexagonal — DIFERIT fins a tenir evidència

L'arquitectura hexagonal (domini pur + ports + adaptadors) **no resol cap problema real avui**.
Amb equip petit i flux encara no validat, invertir-hi mesos abans de validar el flux és
over-engineering. **Seqüència:** Fase B → Fase C → **sprint funcional real** → *només llavors*
decidir si val la pena extreure un domini, amb dades. L'hexagonal passa de "principi" a "decisió
futura condicionada a evidència". (El procés sobreviu als frameworks; l'arquitectura n'és una
implementació substituïble.)

### 4.3 El motor de patrons DXF encaixa a les tres capes (validació del model)

El motor de patrons (`MOTOR_DE_PATRONS.md`, disseny tancat, cap codi) és una peça pensada **abans**
d'aquest reenquadrament, i hi encaixa **sense forçar res** — la millor prova que el model és
correcte. Encaixa a les tres capes alhora:

- **Producció:** és **una eina més del menú** del llenç. El propi document diu que *"tecnifica
  tasques existents, no n'inventa de noves"*; les `TaskType` `pattern_*` ja modelen aquestes
  feines com a treball humà → consumeix temps de tècnic (dimensió d'esforç).
- **Patrimoni:** el patró és la **4a representació de la mateixa espinada semàntica**
  (`fitxa → POM → GradedSpec → PATRÓ`). No és coneixement aïllat; és la veritat de mesures
  projectada sobre la geometria. El patró rectificat fa **créixer el coneixement** del model.
- **Governança:** el cercle `fitting → deltes → rectificació propagada → DXF` (PAT-3, "el que val
  milions") és el **rerefons** aplicat a la geometria: el sistema calcula i proposa, la persona
  valida. La columna d'advertències = avisos del graf de costures.

Coherència arquitectònica: el motor és l'**únic** lloc on s'aplica hexagonal (*"hexagonal NOMÉS al
motor de patrons"*). Encaixa amb §4.2: no fem hexagonal a tot el sistema, però al motor —domini
geomètric estable i nostre, amb frontera dura (no dibuixa topologia nova)— sí té sentit. Valida la
regla "hexagonal només on hi ha evidència de domini estable".

---

## 5. L'Olivia Dress com a fil i prova

El cas real de Brownie (PDF de 14 pàgines, Proto→Producció) és **el fil narratiu** del document
de domini, no una secció de validació. El document A.2 s'explica recorrent **la vida de
l'Olivia**, i els conceptes emergeixen del cas (no es presenten abans com a teoria). Regla:
si narrar l'Olivia obliga a introduir un concepte que no surt natural del cas, aquell concepte és
sospitós de sobre-modelització.

Flux real de l'Olivia (resum):

```
PROTO (taronja, talla S) → Size Fitting → Fit Comments (5 pàgines: patró, dimensional,
  constructiu, watchpoints) → correccions
SIZE SET (XXS–XL, 30/03) → grading → mostra mesurada → punts de control + canvi tardà +4cm
PP SAMPLE (16/04) → NEW GRADING OK PRODUCTION (apareix folre: POMs 1/2/F1) → verificada a mà
PRODUCCIÓ (ref. BR W27-0618-021-700)
```

La frase dels 30 segons, des del model: *"Cada model té una vida pròpia dins la plataforma. Les
tasques, els fittings, les correccions, els watchpoints, les versions i la fitxa són estats
d'aquesta vida."*

---

## 6. Sprint previ independent (no part del redisseny)

**Arrodoniment per unitat + revisió de conversió:** **1 decimal en mm, 2 decimals en inch**
(0,01" ≈ 0,25 mm ≈ precisió comparable a 1 decimal mm; 0,1" ≈ 2,5 mm massa groller). Principi:
arrodonir **a presentació, no a emmagatzematge**; desar en unitat canònica i precisió completa.
Risc: **round-trip drift** (mm→inch→mm acumula error) si la conversió arrodoneix en desar →
contamina l'auditoria (`MeasurementChangeLog` append-only). Revisar on es converteix avui abans
de fixar la regla. Previ i aïllat.

---

## 7. Impacte de plataforma (a confirmar a Fase B/C)

Aquest reenquadrament toca, com a mínim:

- **`models_app` (Model):** el Model com a subjecte; el dashboard del model com a pantalla nova
  central (mapa d'atenció + acció); la meitat "Resultats" (coneixement acumulat) és superfície
  nova; el Model creix en dues dimensions (coneixement + esforç = **patrimoni**).
- **`tasks` (Kanban/TaskType/ModelTask):** Kanban com a escala (model vs plataforma); arbre de
  dependències al codi; catàleg de tipus a codi; tancament assistit; rondes vinculades; atribut
  intern/extern a la tasca.
- **`fitting` (SizeFitting/GradingVersion):** col·lisió de nom Size/Grading Fitting; els quatre
  gates; activar el hook `brain.on_fitting_measurement_changed` (stub previst per a
  reobertura/staleness).
- **`planning`:** lectura per model a més de per tècnic; **dashboard del PM en temps real** amb
  data recalculada per maduresa; consumeix l'arbre de dependències; reaprofitament del scheduler.
- **Temps/economia** *(reaprofitament: Welford / `TaskTimeEstimate`)*: la petjada de temps passa
  a ser **dimensió d'esforç del patrimoni**; lectura de **cost/rendibilitat** per departament ·
  tècnic · model · col·lecció a profunditat d'estudi/direcció.
- **Capa de disseny (nova fase prèvia):** tasca de disseny + fitxa de disseny; **design freeze**
  com a primer gate condicionat (2 senyals: acceptació de disseny + OK de compres/BOM), decidit
  pel **PM**, que planifica i assigna; **anàlisi de mortalitat** (cost no madurat + causa).
- **Entitat nova:** **Watchpoint** (travessa gates) — comportament congelat, classificació oberta.
- **Categoria nova:** correcció **constructiva** (avui sense casa).
- **Motor de patrons** *(`MOTOR_DE_PATRONS.md`)*: encaixa com a eina (producció) + 4a
  representació (patrimoni) + cercle fitting→DXF (governança). Validació, no impacte nou.

---

## 8. Pla de fases (actualitzat)

| Fase | Què | Estat |
|---|---|---|
| A | `FLUX_FITTING_SIZECHECK.md` — primer disseny conceptual | fet |
| **A.2** | Document de **domini**: "Què és un model" → vida de l'Olivia → dashboard → mecanismes → principis. Reposat. | **propera sessió** |
| B | Diagnosi quirúrgica read-only. Resol: col·lisió `SizeFitting`, `TaskType` per-tenant?, relació `SizeCheck`/`PieceFitting`/gates/`brain` stub, abast real. | pendent |
| C | Impacte + jubilacions. Reaprofita/estén/jubila. Risc PROD. | pendent |
| D | (condicional) Domini hexagonal + model de dades + migracions. | diferit |
| E | Sprints additius. | pendent |

---

## 9. PUNT DE REPRESA per a la propera sessió

Començar la **Fase A.2**: redactar el document de domini amb aquesta estructura. **Criteri de
qualitat de tot el document: respondre la pregunta de la missió** — el model conté el que cal
perquè un tècnic pugui reprendre, entendre i continuar sense reconstruir la història?

1. **Missió + frases fundacionals** (preservar context; les cinc frases). Governen tota la resta.
2. **Què és un model** (entitat viva que acumula **patrimoni** —coneixement + esforç— fins a
   producció; centre de navegació, no propietari de dades).
3. **La vida d'un model d'extrem a extrem:** disseny (dissenyadora + fitxa) → **design freeze**
   (2 senyals, decidit pel PM → planifica i assigna) → desenvolupament (Proto → Size Set → PP
   Sample → Producció).
4. **Com hi entra i hi viu el tècnic** (portes → model com a **llenç** → **dashboard del model**
   com a mapa d'atenció **i acció**: on sóc · què ha canviat · què requereix atenció · què puc fer
   ara; estat tècnic plegat). El **menú d'eines** a demanda + el **rerefons viu** automàtic.
5. **La vida de l'Olivia** (com a il·lustració concreta, no com a procés narrat).
6. **Les tres capes** (producció / patrimoni / governança) i l'**economia del treball** (Eina →
   Temps → Cost → Decisió → Coneixement; lectures per profunditat: tècnic/PM/direcció).
7. **Mecanismes que emergeixen** (gates ×4 com a escala reversible, Size/Grading Fitting,
   correccions ×4, watchpoint, avisos com a comportament, decisió-com-a-esdeveniment, profunditats).
8. **Principis i el que es difereix** (procés al codi, hexagonal diferit —excepte motor de
   patrons—, POMs estables, tasca tanca+ronda, sprint 0 decimals, capa comercial i comptabilitat
   identificades-no-desenvolupades).
9. **Tests d'acceptació** (9:12 reprendre + 11:47 treballar) com a **criteri de suficiència del
   model conceptual** — marcant explícitament que els tests d'usabilitat reals són de producte,
   diferits a després de Fase C.

Tot el vocabulari nou neix amb claus `t()` ca/en/es (i18n-gate des del primer sprint).

**Recordatori de criteri de validació de qualsevol funcionalitat futura** (la missió elimina
opcions): *ajuda a reprendre, entendre o continuar un model?* Si no, és soroll.

---

*Fi de l'estat de disseny congelat. Res tocat a codi, staging ni PROD. Següent: Fase A.2.*
*Disseny a tres bandes: Agus (CTO/decisió) · Claude · PPx (revisió externa).*
