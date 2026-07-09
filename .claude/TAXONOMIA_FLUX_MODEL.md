# TAXONOMIA_FLUX_MODEL — la realitat del treball sobre un model

> **Estatus: validat però viu.** Cap disseny és immutable; aquest s'obre a noves files
> quan un escenari futur ho demani. No és implementació ni diagnosi: és la lectura del
> flux real que precedeix el disseny del **dashboard del model** (Patró C).
> FHORT Textile Tech · sessió de disseny Agus (CTO/decisió) + Claude (CTO tècnic) + PPx (crítica externa).
> Origen: seqüència de treball real T1–T7 aportada per l'Agus, estressada amb 7 escenaris de falsació.
> Brúixola: `DISSENY_MODEL_VIU.md`. Fonts de codi: `DIAGNOSI_FASE_B.md` + `MAPA_SISTEMA.md`.

---

## 0. Per a què serveix aquest document

El dashboard del model és la primera peça frontend del "model viu". Abans de dibuixar-lo
calia separar amb duresa **les naturaleses distintes de feina** que conviuen al treball real,
perquè si no la pantalla acaba sent un calaix de sastre que barreja log tècnic, inbox humana,
checklist i memòria (crítica del PPx, acceptada).

La lectura es fa amb el **codi real al davant**: cada acció s'etiqueta no només amb la seva
naturalesa (capa) sinó amb **si la seva font ja existeix** o no. La taxonomia sense el mapa de
fonts seria teoria; amb el mapa, és el contracte del dashboard.

**El dashboard del model (zoom-in, aquest model seleccionat) NO és el dashboard general de
plataforma (zoom-out, tots els models, vista PM/planificació).** Són les dues escales del
`DISSENY_MODEL_VIU.md` §1.2. Aquest document tracta NOMÉS el del model. El "des d'on i com
s'hi arriba" es deixa obert deliberadament.

---

## 1. Les cinc capes (naturalesa de cada acció)

| # | Capa | Què és | On alimenta |
|---|---|---|---|
| ① | **Tasca executable** | feina que el tècnic fa o ha de fer | checklist saltable, assignació, estat, bloquejos |
| ② | **Esdeveniment del model** | cosa que PASSA al model i canvia el context (no és feina en si) | timeline ("què ha canviat") |
| ③ | **Canvi de patrimoni (coneixement)** | acció que crea coneixement/artefacte del model | mesures, versions, specs, maduresa |
| ④ | **Coordinació / handoff** | instrucció dirigida a algú o convocatòria entre persones | atenció humana + acció |
| ⑤ | **Consum de temps / cost** | la petjada temporal de qualsevol feina | esforç del patrimoni + planning |

Una mateixa acció pot caure a diverses capes alhora (p. ex. un size check és ①+③+⑤).

## 2. Les tres lectures del temps (capa ⑤ llegida a tres profunditats)

El **mateix** `TimerEntrada` es llegeix de tres maneres (frase fundacional 3). Col·lapsar-les
contamina el Welford o falseja el cost.

| Lectura | Què | Granularitat | Regla clau |
|---|---|---|---|
| **A** — Aprenentatge | Welford ajusta durada esperada | cel·la `task_type × garment_type_item` | **NOMÉS feina estructurada i repetible.** La tasca externa lliure NO hi entra (soroll no comparable). |
| **O** — Ocupació | hores que mengen la cua del tècnic | per usuari | **TOT** compta (estructurat o no, sessió, extern). El planner no pot sobre-assignar. |
| **M** — Imputació-model | cost del model | suma `TimerEntrada` per `model_task__model` | **TOT** el que va contra el model, **agnòstic a qui** ho fa. |

**La tasca externa lliure toca O + M, mai A.** Aquesta és la distinció que fa funcionar
l'estimador convergent (§6, D-6).

---

## 3. Les fonts (existeix o no la dada?)

| Codi | Font | Significat |
|---|---|---|
| `a` | **viu estructurat** | l'eina interna ja deixa rastre estructurat de franc (import→`MeasurementChangeLog`, size check→`BaseMeasurement` CHECKED, propagació→`GradingVersion` v+1, fitxa→versió, gates→`GateEvent`, tasques→`TaskTransition`). |
| `b` | **retorn d'artefacte** | l'eina externa només deixa rastre quan l'artefacte torna al sistema (pujar DXF/RUL, importar sketch, adjuntar foto, generar PDF). El moment de retorn = quan el coneixement entra al model. |
| `c` | **no existeix encara** | cal construir-ho (o ja està diferit a una decisió coneguda). |

**Regla d'or (PPx, acceptada):** la frontera no és *intern vs extern*, sinó **quan el
coneixement (③) entra al model**. Les 2h de Polipattern són cost real (⑤ O·M) encara que no
hagis pujat el DXF; però no són coneixement del model (③) fins que l'artefacte torna (`b`).
Esforç i coneixement avancen a ritmes diferents; el timeline no els ha de col·lapsar.

---

## 4. La taula T1–T7 (la seqüència real etiquetada)

> Llegenda: capes ①–⑤ · font `a/b/c` · temps **A**/**O**/**M**.

### T1 — Freeze + assignació + patró base
| Acció | Capes | Font | Temps |
|---|---|---|---|
| PM fa el freeze i assigna tasques (patró, POMs, escalat, fitxa, fitting, revisió) | ④① | freeze `c` (D-7) · assignació `a` | — |
| Obro model → entro al dashboard → veig les tasques assignades | ① | `a` (by_model) · **dashboard `c`** | — |
| Patró 2h a Polipattern (extern) | ①⑤ | tasca externa lliure `c` · timer+exclusió `a` (reusat) | **O·M** |
| Pujo DXF + RUL; el sistema parseja peces | ②③ | `b` | — |
| Pregunta si guardo el run de talles → NO | ③ | `a` (decisió-com-event) | — |

### T2 — Torna a les 3h: import + comparador
| Acció | Capes | Font | Temps |
|---|---|---|---|
| Una companya m'ha passat una taula de creixements d'un model semblant | ④ | `c` (handoff entrant) | — |
| Wizard import: pujo fitxa, detecta talles/POMs/deltes amb regles, OK | ①③⑤ | `a` · `b` (puja) | **A·O·M** |
| Comparador import↔patró: ajustos i discrepàncies | ③ | `c` (motor patrons, D-14) | — |
| 2 POMs els canvio a la taula | ③⑤ | `a` | **O·M** |
| 2 POMs els canvio al patró (Polipattern) | ①⑤ | extern `c` · timer `a` | **O·M** |

### T3 — Fitxa proto + handoff al PM
| Acció | Capes | Font | Temps |
|---|---|---|---|
| Edito fitxa: sketch, foto fornitures, taula base, fletxes, text de fabricació, sketches peça | ①③⑤ | `a` (TechSheet) · `b` (imports) | **O·M** |
| Tanco fitxa → versió + PDF | ②③ | `a` · `b` (PDF) | — |
| Envio la fitxa al PM | ④ | `c` (handoff sortint) | — |
| PM diu OK → l'envia a producció | ④② | `c` (resolució handoff) | — |

### T4 — 3 dies: 10 protos, size check, error fabricant, rectifico
| Acció | Capes | Font | Temps |
|---|---|---|---|
| Arriben 10 protos per mesurar | ② | `c` (arribada) | — |
| Size check sobre talla base, rectifico mesures reals per POM | ①③⑤ | `a` (SizeCheck, CHECKED) | **A·O·M** |
| El fabricant no ha informat bé els encongiments | ④ | `c` (incidència/handoff) | — |
| Aplico nous valors → propagació | ③ | grading `a` · geometria `c` | — |
| Fitxa: pàgina nova, taula nova, foto proto + fletxa + text d'error | ②③ | `a` (versió) · `b` (foto) | — |
| Guardo PDF, l'envio per mail al fabricant + patró rectificat | ④ | `c` (handoff sortint) | — |

### T5 — 3 dies: sessió de fitting (persones) → canvis → fitxa producció
| Acció | Capes | Font | Temps |
|---|---|---|---|
| Sessió convocada (visual, sense mides) | ②④ | `a` (FittingSession + group_*) | — |
| Confirmo assistents reals (desclic dels absents) | ④⑤ | `c` (confirmació presència) | **O** a tots els presents |
| Fem la sessió sobre la fitxa; escot +1, màniga +1 endarrere, +3cm davant/darrere | ①③ | `a` (anotació mesures+observacions) | **M** responsable |
| Anoto canvis i fotos | ③ | `a` · `b` (fotos) | — |
| A la meva taula: repasso, faig rectificar patrons (auto / Polipattern) | ①③⑤ | grading `a` · extern `c` | **O·M** |
| Fitxa producció: **totes** les talles + creixements propagats | ③ | `a` (versió producció) | — |
| Passo patrons nous; demano al proveïdor un nou proto | ②④ | DXF `b` · request `c` | — |

### T6 — 2 dies: arribada, break XL, regenero, avís al PM
| Acció | Capes | Font | Temps |
|---|---|---|---|
| Avís d'arribada de prenda (2 talles, sense fitting) | ② | `c` (arribada) | — |
| Repasso últimes mesures; les dues bé | ①③ | `a` | **O·M** |
| Decideixo break a XL: escot +2cm | ③ | `a` (GradingRule break canònic) | — |
| Registro, regenero taula, refaig patrons, escalats auto, DXF, RUL, fitxa final | ②③ | grading `a` · DXF `b` · geometria `c` | — |
| Deixo un avís perquè el PM ho enviï ell aquest cop | ④ | `c` (handoff lleuger dirigit, pendent) | — |

### T7 — 10 dies: tancat
| Acció | Capes | Font | Temps |
|---|---|---|---|
| El model està tancat | ② | `a` (estat→Tancat, D-3 TOP terminal) | — |
| Entro: producció bé, PM i proveïdor satisfets | ④ | `c` (resolució) | — |
| Cap tasca més | ① | `a` (tasques Done) | — |

---

## 5. Output 1 — Inventari de capa `c` (què és construcció nova)

Tot el que sembla molt es col·lapsa. La columna `c` es reparteix en:

### 5.1 El handoff lleuger — UNA sola primitiva nova de coordinació
Tots aquests són **el mateix objecte**: "companya m'ha passat taula", "envio fitxa al PM",
"PM OK→producció", "fabricant no ha informat bé", "envio al fabricant", "demano proto al
proveïdor", "deixo avís al PM", i les arribades ("10 protos", "avís d'arribada").

> **Handoff lleuger = esdeveniment dirigit:** emissor → destinatari, opcionalment ancorat a
> una tasca, amb estat **pendent/resolt**. Les arribades són el mateix amb origen
> extern/sistema. Viu al model; el PM hi pot operar per model independentment.
>
> **No es promou a entitat-amb-maquinària encara** (frase fundacional 4: la decisió/coordinació
> és un esdeveniment amb rastre, no necessàriament una entitat). Si és un camp sobre l'event o
> una mini-entitat amb cicle pendent→resolt, ho dirà el disseny dels endpoints. Comencem prim.

### 5.2 La convocatòria (data + convidats) — JA EXISTEIX, no es construeix
"Data + convidats" + "convocar/desconvocar un model independentment" = `FittingSession` +
`group_attendees` / `group_add_model` / `group_remove_model` / `group_reschedule`. La
independència PM per-model ja és cablejada. Al dashboard del model = **projecció read** d'una
sessió on aquest model hi és. **Tres conceptes distints, no es barregen:**
- **Convocatòria** = la reunió (qui/quan/quins models). Ocupació de temps **a tots els
  assistents** (és cost de sessió). `FittingSession` viu.
- **Feina de fitting** = el responsable entra al model, obre l'eina, veu mesures per POM de
  talla base, anota, tanca. La registra **el responsable**, imputa **M** al model. `ModelTask`
  + `SizeCheck`/`PieceFitting` vius. **No depèn que hi hagi convocatòria** (T4 i T6 no en tenen).
- **Presència real** = es confirma a l'anotació; el responsable **desclica** els absents.
  Motiu: no som a la reunió, la veritat de qui hi ha l'ha de confirmar qui hi és (mateix patró
  que "el size fitting a casa del client": registrem el fet, no orquestrem el procés). `c` lleuger.

### 5.3 La tasca externa lliure — registrar ara, motor de valoració DIFERIT
- Es registra **lliurement** (text obert: "vaig a ajudar la companya amb el patró"). Captura la
  veritat sense fricció en comptes d'obligar a encaixar en un catàleg tancat.
- Timer + popup-rellotge persistent; l'**exclusió un-InProgress-per-tècnic ja existeix**
  (`transition_task`) → el popup només la fa visible i dura. Atura manual → tanca timer →
  imputa **O·M** al model (mai **A**).
- **Naturalesa: sense classificar.** El camp queda buit.
- **El motor de valoració/reclassificació IA NO es construeix ara.** És un procés que un
  responsable **llença a demanda** per validar les tasques externes d'un període o d'una
  persona (mineria de procés: detectar feina recurrent fora de catàleg → senyal de quan el
  catàleg s'ha de fer créixer). La dada es captura ara en forma que **un dia** alimenti aquella
  valoració sense re-registrar (text + temps + responsable + model + període). Dipòsit ara,
  motor futur explícit.
- **Assistència IA, no veritat automàtica** (quan es construeixi): proposa, l'humà valida.

### 5.4 Resta de `c` — ja diferida a decisions conegudes (el dashboard NO les construeix)
- **Freeze 2 senyals + PM + mortalitat** → D-7.
- **Comparador import↔patró / geometria / motor de patrons** → D-14.
- **Canvi tardà post-segell** → necessita **flux de reobertura amb rastre** (el guard D-1 ja
  tanca la porta via `allow_reopen_sealed` no exposat; el flux que el justifica encara no està
  dissenyat). El dashboard **llegeix el pany**, no el força.
- **Sortida esperada / convergència** → D-6 (§6).

### 5.5 Construcció nova mínima PER AL DASHBOARD
1. La **superfície frontend** (landing del model — estrena guardians i18n + UI).
2. El **merge del timeline** sobre fonts `a` (+ `b`, + events `c` de handoff/arribada quan existeixin).
3. La **primitiva de handoff lleuger** (§5.1).
4. L'**entrada de tasca externa lliure** amb popup-rellotge (§5.3).

La resta el dashboard la **llegeix** (fonts `a`/`b` vives) o la **deixa per quan existeixi**.

---

## 6. Output 2 — La convergència estadística ↔ maduresa (principi, columna de D-6)

L'estimació d'un model **no és estàtica**: es barreja amb la realitat a mesura que madura.

```
previsió_sortida = real_acumulat + estimació_del_pendent
   on el pes de l'estimació cau amb la maduresa:
   0%   → estadística pura (Welford de la cel·la task_type × garment_type_item)
   50%  → 50% temps real executat + 50% estadística sobre el que queda
   100% → real pur; aquell real RE-ALIMENTA Welford → cel·la més afinada pel pròxim model
```

És un estimador que **es desinfla a mesura que el real el substitueix**, i el bucle es tanca
sol: cada model tancat fa la BD més encertada pel següent. Això és la **planificació honesta**
del disseny (§1.3): la data no és una promesa vella, és real + el millor que sabem del pendent,
**recalculada cada cop que la maduresa es mou**.

**Ancoratge correcte: compleció de TASQUES, no volum de coneixement** (troballa E5, el clon):
un re-order té coneixement alt però esforç baix; ha de predir **poc temps restant** perquè
queden poques tasques. La maduresa que governa la convergència és la de tasques completades.

**Estat del bucle avui (diagnosi):**
- **D-13:** `record_actual_time` perd la FK al model i descarta la mostra si no hi ha
  `garment_type_item`. Cost-per-model es resol sumant `TimerEntrada`; aprenentatge descarta bé
  la tasca lliure, però descartar una tasca *estructurada* per falta de `garment_type_item` és
  un tall a revisar.
- **D-6:** `estimated_minutes` congelat en crear; recompute mai per maduresa. La seqüència real
  és tota canvis tardans (T5, T6) → cal la costura maduresa→recompute perquè el pla respiri.

**Disciplina:** D-6 i D-13 són **sprints propis, posteriors al dashboard**. El dashboard
**llegeix** l'esforç real acumulat (⑤ M) i deixa **un lloc previst** per a la "sortida
esperada" quan D-6 la calculi. No construeix l'estimador.

---

## 7. Output 3 — La forma del dashboard (4 preguntes en DOS plans)

No és timeline al centre (correcció acceptada del PPx). El cor és l'**estat de treball actual +
el següent pas possible**. El timeline n'és el suport (pregunta 2). Les capes cauen sobre les
4 preguntes de l'Agus, jerarquia mantinguda, en dos plans:

### Pla de treballar ara (test 9:12 — entendre i actuar en 10 segons)
- **Q1 · On sóc / què bloqueja** ← ① + ③ llegits com a ESTAT (no història): fase/gate · què
  bloqueja · **últims artefactes vigents** (DXF vN, fitxa vN, taula base vigent).
- **Q3 · Què requereix atenció** ← **dues coses que NO es barregen**: alertes tècniques
  (toleràncies / `pom-alerts`, backend viu marcat per ressuscitar) **+ handoffs dirigits a MI,
  pendents** (④ entrant: "avisa el PM", "esperant proveïdor").
- **Q4 · Què puc fer ara** ← ① tasques executables saltables + acció següent + **handoffs que
  JO he d'emetre** (④ sortint).

### Pla de memòria
- **Q2 · Què ha canviat** ← ② timeline d'esdeveniments, alimentat sol per `a`/`b` (+ events `c`
  de handoff/arribada quan existeixin).

> El **handoff es reparteix net** entre Q3 (el que espera de mi) i Q4 (el que he d'emetre) —
> per això necessitava forma pròpia i no podia viure ni als watchpoints ni al timeline.

### Decisió Q2 — "des de l'última visita" → **v1 = "últims canvis"**
**No es construeix el last-seen per-usuari-per-model.** Motiu (Agus): ningú s'anota "vaig
arribar aquí"; la gent treballa de memòria. Una pantalla que digui "això és el que ha passat
darrerament en aquest model" ja retorna el fil sense que el sistema sàpiga quan vas mirar-lo.
Evita una taula nova i la lògica vist/no-vist. Si algun dia algú demana el "des que JO vaig
entrar", el last-seen es guanyarà existir. Ara no. (`darrera_activitat` és per-model, no
per-usuari, i així es queda.)

---

## 8. Notes obertes (el document és viu)

1. **El dashboard té dos abasts, no un** (troballa E2/E4/interferència). Memòria (timeline +
   esforç) = **abast model**, compartit (mostra la feina de tothom qui hi ha passat).
   Treballar-ara (Q1 bloquejos, Q4 accions, handoffs dirigits a mi) = **abast espectador**
   ("què faig JO"). El `models/<id>/dashboard/` és **en part relatiu a qui pregunta**. No és un
   problema; és una propietat que el disseny dels endpoints ha de respectar.

2. **GarmentSet rollup.** El dashboard és per-model = per-peça. Un conjunt (vestit+jaqueta, cada
   peça un Model) es treballa de vegades com a unitat. La taxonomia no es trenca, però apareix
   una pregunta de **navegació**: cal una vista de rollup de conjunt? Coherent amb "model =
   centre de navegació, no propietari" tractar el set com agrupació de navegació sense ser amo
   de dades. Aresta coneguda, no resolta ara.

3. **Peces `c` diferides** que el dashboard llegeix/espera però no construeix: freeze+mortalitat
   (D-7) · comparador/motor de patrons (D-14) · flux de reobertura post-segell (lligat al guard
   D-1) · convergència sortida esperada (D-6) · temps-com-a-patrimoni FK model (D-13).

4. **El model cognitiu desplaça el kanban (direcció de disseny contrastada, no investigada).**
   Hem passat d'un model de treball SEQÜENCIAL (kanban global de columnes d'estat, tasques fluint
   per fases com una cinta) a un model COGNITIU (el model al llarg del temps és la unitat de veritat).
   Conseqüència sobre les tasques:
   - **L'estat de tasca viu al MODEL** (Q4 crescut: de llista saltable a columnes d'estat
     Pending/InProgress/Paused/Done dins el dashboard del model). Les columnes d'estat del model
     SÓN la checklist d'instruccions que el PM informa sobre aquell model (`ModelTask`).
   - **L'entrada de treball és una CUA DE MODELS per tècnic** (no de tasques soltes): el que entra
     a la cua és el model amb la seva TASCA CAPDAVANTERA, no la tasca despullada del seu model.
     És la "fulla de planificació" (zoom-out): quins models a la cua, maduresa, tasca pendent,
     data informada, etiqueta de risc/urgència, i diff "t'han avançat un model a la llista".
   - **Una sola font (`ModelTask` informat pel PM), llegida a dues escales:** zoom-in (estat dins
     el model) i zoom-out (cua de models per tècnic). Aplicació de la llei de sobirania del model
     a les tasques: la tasca viu al model; la cua és una PROJECCIÓ ordenada, no una entitat que
     posseeix tasques. La "primera columna" del kanban actual (backlog/entrada) és l'únic tros que
     sobreviu, evolucionat de "tasques soltes" a "models amb tasca capdavantera".
   - **Disciplina d'execució:** construir el nou (kanban-del-model + fulla de planificació) AL COSTAT
     del kanban global, sense tocar-lo. Es jubila NOMÉS quan les peces noves el cobreixin del tot i
     l'Agus ho confirmi a pantalla — d'una passada conscient, no a trossos.
   - **Quan s'executi, primera peça = diagnosi read-only** (què fa el kanban global, qui en depèn,
     què ja existeix de cua per tècnic a Planificació/`TechnicianQueueOrder`/D-6). D'aquí sortirà si
     la fulla de planificació és **D-6 amb cara nova o construcció fresca**. Reordena D-4 (catàleg de
     tasques), D-6 (planificació per maduresa) i el sprint "cicle de vida tasques Kanban".

---

## 9. Registre de falsació (per què confiem en el model)

7 escenaris dissenyats per **trencar** la taxonomia (no per confirmar-la). Cap va forçar un
concepte nou; tot va caure a ①–⑤ amb font a/b/c o a una peça ja diferida.

| # | Escenari | Estressa | Veredicte |
|---|---|---|---|
| E1 | Model que mor (BOM inviable, mai freeze) | mortalitat / estat terminal amb causa | Aguanta. "No madurat" ja al disseny (D-7). Dashboard llegeix l'estat. |
| E2 | Ajudar la companya (B treballa al model d'A) | atribució de cost multi-persona | Aguanta. Cost agnòstic a qui (⑤ M). **Destapa el doble abast** (nota 1). |
| E3 | Fitting que fa regressar un gate | reversibilitat | Aguanta. `regress_phase`+`GateEvent` vius. Timeline pinta regrés. |
| E4 | 3 dies sols a Polipattern, multi-model | esforç vs coneixement; atribució neta | Aguanta. Confirma esforç≠coneixement i que **l'exclusió és estructural** (fa honesta l'atribució). |
| E5 | Re-order (clon de model anterior) | maduresa coneixement alta, esforç baix | Aguanta. **Afila D-6**: convergència s'ancora a compleció de TASQUES, no a coneixement. |
| E6 | Canvi tardà post-segell (TOP) | guard D-1 vs canvi tardà del disseny | Aguanta (tensió intencionada). Cal flux de reobertura amb rastre (`c`). Dashboard llegeix el pany. |
| E7 | Intercanvi de tasques entre usuaris | interferència / propietat | Aguanta sense res nou. Entrada lliure ja existeix + cost agnòstic a qui. Confirma doble abast. |

**Decisions anteriors confirmades com a PORTANTS** (no decoratives) pel repte: separació
esforç/coneixement (E4) · exclusió un-InProgress com a garantia d'atribució (E4) · handoff
lleuger únic que absorbeix tota la coordinació `c` (forma idèntica a tots els escenaris).

---

*Document viu. La realitat sempre porta una fila que no havies previst. S'amplia o es
reescriu quan un escenari nou ho demani. Següent passa des d'aquí: contracte dels endpoints
(`models/<id>/dashboard/` + `models/<id>/timeline/`) i trossejat en peces, després d'una
lectura quirúrgica read-only de les formes serialitzades reals (by_model,
consumption_delivery_view, pom-alerts, MeasurementChangeLog).*
