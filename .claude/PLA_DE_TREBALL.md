# PLA DE TREBALL — el contenidor de tasques del model (Q4 crescut)

> **Estatus: validat però viu.** Disseny acordat Agus (CTO/decisió) + Claude (CTO tècnic),
> Patró C (humans amb el codi al davant). No és implementació: és el disseny que precedeix el
> trossejat. S'amplia o reescriu quan un escenari nou ho demani.
> FHORT Textile Tech · zoom-in sobre el model. Brúixola: `DISSENY_MODEL_VIU.md` (§3.8 tancament
> de tasca). Realitat: `TAXONOMIA_FLUX_MODEL.md` (§8.4 model cognitiu). Substrat confirmat:
> `DIAGNOSI_KANBAN_PLANIFICACIO.md` (l'exclusió i la màquina d'estats viuen al servei
> `transition_task`, no al kanban → reutilitzables).

---

## 0. Què és i per què

El **Pla de treball** és l'encàrrec del model: les `ModelTask` que el PM ha informat, vistes
com a procés. És el cor del zoom-in sobre el model i **absorbeix Q4** ("què puc fer ara") del
dashboard: la llista plana de tasques que F1 va fer puja aquí, feta bé.

Neix del trànsit d'un model **seqüencial** a un de **cognitiu** (`TAXONOMIA §8.4`): l'estat de
tasca viu al model; el tècnic hi entra per on vol; la represa és central. El Pla de treball és
el briefing que reps en obrir i el quadern de bord de la feina assignada.

**Criteri de qualitat (la prova de l'Agus):** *aquesta pantalla ajuda a treballar el model
avui, o només a entendre'l?* Cada targeta ha de poder respondre-la: operes la tasca, no només
la consultes.

---

## 1. El contenidor

- **Ubicació:** sota el menú de pestanyes de `ModelSheet`, **ample total** (les dues columnes),
  fons transparent. Per sobre del pla de treballar-ara (esquerra) i el de memòria (dreta).
- **Títol:** "Pla de treball" (diu exactament què has de fer).
- **Contingut:** les tasques de l'encàrrec en **fila, ordre de producció esquerra→dreta**.
- **Peu:** barra de progrés (% de tasques Fetes sobre el total) + **temps real acumulat sobre
  el model**.

---

## 2. Anatomia d'una targeta de tasca

(Referència visual: mockup `pla_de_treball_task_cards`.)

- **Capçalera:** icona + **nom** de la tasca (Patró CAD, POM, Fitxa tècnica, Escalat…).
- **Cos:** **temps consumit** acumulat + **nº de vegades obertes** (obertures).
- **Peu:** **tres botons de transport** + **badge d'estat**.
  - `▶ Play` — iniciar / reprendre (i, en una tasca Feta, **reobrir**).
  - `⏸ Pause` — pausar.
  - `⏹ Stop` — donar per bona (Done, 100%).
- **Estat visual** comunica on és sense text (vegeu §3): pendent / en curs (viu) / feta /
  d'altri (fade) / fora d'encàrrec (filet grana).

**Requisits d'UI (de la revisió del mockup):**
- Les **etiquetes d'estat NO han de desbordar** la targeta (truncar o embolcallar; mai trencar
  la caixa). Aplica a totes, especialment "fora d'encàrrec" i "en curs".
- La targeta externa porta nom fix **"Tasca externa"**; el text lliure que escriu el tècnic va
  **a dins**, no al nom.

---

## 3. Estats i transport (mapejats a `transition_task`, que JA EXISTEIX)

La metàfora de transport (play/pause/stop) tanca la semàntica que necessitàvem: en un
reproductor **stop ≠ pause** — pause guarda la posició, stop acaba.

| Acció UI | Transició | Significat |
|---|---|---|
| **Play** (no començada / pausada) | Pending→InProgress · Paused→InProgress | Iniciar / reprendre + obre eina + arrenca crono |
| **Pause** | InProgress→Paused | Pauso, no he acabat; registra temps |
| **Stop** | InProgress→Done | **Decisió humana**: feta, 100%. MAI automàtic |
| **Play** (sobre una Feta) | Done→InProgress | **Reobrir = ronda nova vinculada** (§3.8), log a `TaskTransition` |

**Tancar tasca ≠ tancar model** (§3.8): el tancament real del model és l'**OK autoritzat**
(capacitat específica, p. ex. Montse) via gate (D-3). El Stop d'una targeta és tancament a
**nivell de tasca**, no de model. Quan el model es tanca, les tasques obertes es donen per
tancades amb el model (marcades així, no com a "fetes pel tècnic" — preserva la informació de
què va quedar sense fer).

**Exclusió un-InProgress-per-tècnic:** ja viu a `transition_task` (`services_c.py:54-63`);
arrencar una tasca pausa l'altra en curs del mateix tècnic. El Pla de treball la fa visible, no
la reimplementa.

---

## 4. Cablejat eina ↔ timer (l'automatisme)

- **Play obre l'eina associada** a la tasca + arrenca el cronòmetre.
- **En sortir de l'eina → torno al dashboard** + la tasca queda **Pausada** (no Feta).
- **Stop** (donar per bona) és gest humà explícit; **no** surt de tancar l'eina.
- **Excepció: tasca externa** — sense eina associada; transport manual (Play arrenca crono
  sense obrir res; el tècnic atura a mà).
- **v1:** el control des de DINS l'eina (contenidor de transport incrustat a l'eina) **NO entra
  ara** — es farà quan toquem les eines. Però el Pla de treball **ja mostra que el crono d'una
  tasca està en marxa** (estat "en curs" de la targeta amb indicador viu).

---

## 5. Tres rendings de la targeta (relatiu a qui mira — doble abast)

La condició **informativa vs executiva NO és un camp** sobre la tasca: és `task.assignee == jo`.
La mateixa tasca és executiva per a qui la té i informativa per a la resta. Coherent amb el
doble abast del dashboard (`TAXONOMIA §8.1`).

1. **Meva** (executiva): nítida, transport operable.
2. **D'altri** (informativa): **en fade** + **nom de l'assignat** ("Escalat · Montse"), transport
   apagat. Motius (de l'Agus): (a) veure l'encàrrec real i complet, que viu al model; (b) saber
   amb qui parlar abans/després.
3. **Fora d'encàrrec:** **filet grana** + etiqueta "(fora d'encàrrec)". Tasca no informada pel PM
   (externa lliure, o feina sense `ModelTask`). El PM decideix després (incloure / avisar /
   preguntar). **Senyal de facturació:** informades = encàrrec facturat; fora d'encàrrec = a
   revisar. El menú d'eines segueix mostrant-se **tot** al model.

---

## 6. Handoff de reassignació (la 3a via — agafar una tasca d'altri)

Quan premo **Play sobre una tasca d'altri**, el sistema **em pregunta si la reassigno**, i la
reassignació és **condició obligada per entrar-hi** (no pots treballar una tasca aliena sense
fer-la teva primer). Acord natural entre tècnics; **el PM no l'ha de validar** (és planificació;
el PM ho pot fer lliurement, però la gent s'ajuda i parla — ha de ser natural). El traspàs queda
al **timeline** com a event.

- **Cascada ja viva:** la reassignació de tasca dispara `recompute_for_technicians`
  (`tasks/views_b.py:253`) → la cua es recalcula per als dos tècnics. **No es construeix; es
  dispara.**
- **Temps immutable:** el temps ja consumit per l'altre tècnic **queda registrat com a seu** i
  **suma al model** (cost agnòstic a qui). La reassignació canvia **qui la té d'ara endavant**,
  **no reescriu el passat**. La història és honesta (es veu el traspàs).

---

## 7. Reestructuració del dashboard (conseqüència)

El Pla de treball **absorbeix Q4**. Tres zones:

- **Dalt, ample total:** Pla de treball (Q4 crescut = l'encàrrec).
- **Esquerra:** **On sóc** (Q1: fase, bloquejos) + **Què tinc fet** (l'antic "artefactes
  vigents", renomenat — lliga amb "On sóc" / "Què puc fer" com a preguntes en 1a persona).
- **Dreta:** **Timeline** (Q2: què ha canviat).

El cercle es tanca: treballes una tasca (dalt) → genera events al timeline (dreta) → el que ha
canviat alimenta la decisió de què fer després (dalt). La llista plana de Q4 que va fer F1 **es
retira** quan neix el Pla de treball (no es manté en paral·lel).

---

## 8. Trossejat proposat (ja NO és tot read-only — hi ha escriptura)

> El cor (exclusió, timer, Welford, transicions) ja és viu a `transition_task`. Construïm
> sobretot **la cara** i el **cablejat eina↔tasca**.

- **P0 (read, lectura quirúrgica):** confirmar el camp d'**ordre canònic** a `TaskType` (existeix?
  cal posar-lo?) + verificar el cablejat real de `transition_task` des de frontend (com s'invoca
  avui al kanban, per reusar-lo net). Sense commit.
- **P1 (backend, read):** servir l'**encàrrec** al compositor `model_dashboard_view` — tasques
  ordenades (ordre canònic) + temps consumit + obertures + estat + assignee. Additiu.
- **P2 (frontend):** el **contenidor Pla de treball** amb les targetes i el transport,
  **absorbint Q4** (retirant la llista vella). Estrena la reestructuració de 3 zones + el
  renomenat "Què tinc fet". Guardians i18n/UI.
- **P3 (escriptura):** cablejar **transport → `transition_task`** (Play/Pause/Stop) +
  l'automatisme **eina↔timer** + tornar al dashboard en sortir de l'eina.
- **P4:** **fora d'encàrrec** + **tasca externa lliure** (component fix, nom "Tasca externa",
  text a dins) + el **handoff de reassignació** (diàleg en Play sobre tasca d'altri →
  `recompute_for_technicians`).
- **P5:** **barra de progrés** + **temps real** al peu del contenidor.

**Disciplina:** un commit per peça; escriptura aïllada (P3/P4) de la lectura (P1) i la cara (P2);
`manage.py check` / `npm run build` verds; guardians actius a les peces frontend; mai push (Agus
des de SSH).

---

## 9. Notes obertes (viu)

- **Ordre canònic:** assumit propietat de `TaskType` (universal, segons la lògica de producció:
  Freeze → Tech Pack → PP → TOP). Si un dia el PM ha de poder reordenar per model, és afegitó
  (camp d'ordre per-model). P0 confirma si el camp existeix.
- **Detecció de "feina sense `ModelTask`"** (cas (b) del fora d'encàrrec): a v1 el fora d'encàrrec
  = tasca externa lliure declarada. Detectar feina feta en una eina sense tasca assignada
  (generar registre automàtic) és més potent per a facturació però més complex → diferit.
- **Contenidor de transport dins l'eina** (§4 v1 fora): quan toquem les eines.
- **Mortalitat / tasques que queden sense fer al tancar model:** marcar-les com a
  tancades-amb-model, no fetes. Detall d'implementació de P3.

---

*Document viu. Referència visual: mockup `pla_de_treball_task_cards`. Següent passa des d'aquí:
P0 (lectura quirúrgica read-only de l'ordre canònic de `TaskType` i el cablejat de
`transition_task`) abans de construir P1.*
