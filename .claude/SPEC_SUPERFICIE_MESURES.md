# SPEC — La superfície de treball del tècnic (Mesures) · v2 ancorada

> **Esborrany per corregir (Agus / Patró C).** Un cop validat, es congela al cervell com el
> **destí de l'sprint**. Reescrit després de rellegir DISSENY_MODEL_VIU, TAXONOMIA_FLUX_MODEL,
> DIAGNOSI_FASE_B (D-1..D-15) i PLA_DE_TREBALL. Data: 2026-06-23.

---

## 0. Què és Mesures (ancoratge)

Mesures és **el llenç de treball del tècnic** (DISSENY_MODEL_VIU §1ter): el tècnic no entra a un
mòdul, obre un model i hi treballa. En termes de la diagnosi, Mesures és **el "menú del llenç"
(DIAGNOSI_FASE_B D-5)** aplicat a la realitat mesurada i graduada del model — la capa que avui no
existeix com a tal i que projecta les eines/accions disponibles. **Des d'aquí el tècnic ho fa tot i
ho deriva tot.**

Relació amb el dashboard del model (ja parcialment construït: Pla de treball · On sóc · Què tinc
fet · Timeline): el **dashboard és la casa** (reprendre/entendre); **Mesures és l'eina de treball**
que s'obre des d'una tasca del Pla de treball. Mesures ha de ser una superfície **completa**, no una
taula morta.

---

## 1. Què ha de poder fer el tècnic — la llista, classificada

> Llegenda: ✅ **JA EXISTEIX** · 🔧 **UI/lectura barata** · 🔌 **té backend → cablejar** ·
> 🆕 **construcció nova (D-x)**.

### 1.1 Sortir net + botó de tornar — 🔧 / 🔌
- Es pot **entrar, consultar i sortir sense canviar res ni descartar**. Sortir de l'eina → torna al
  dashboard i la tasca queda **Pausada** (PLA_DE_TREBALL §4); **no** es força cap presa ni descart.
  Done és gest humà explícit (Stop), mai automàtic. Si s'ha entrat per tasca i no es toca res en uns
  segons, no passa res rellevant.
- **Botó de tornar sempre present** (transversal a tot el sistema; avui s'arriba a pàgines sense
  retorn). Peça pròpia immediata.

### 1.2 Registrar presa TIPADA per origen — ✅ (model) / 🔌 (UI de tipus)
- Cada presa = **columna nova** amb `origen` marcat: `BaseMeasurement.origen` ja distingeix
  CHECKED / FITTED / MANUAL / IMPORTED… (DIAGNOSI_FASE_B §3.2). Estadis **diferenciats** (llei
  vigent). La columna activa es **sembra** amb l'última mesura; només es persisteix el que es toca.
- El que cal: que la UI deixi **identificar de què és la presa** (proto/taller vs sessió de fitting)
  en registrar-la, no només inferir-ho del trigger.

### 1.3 Propagar escalat cap a Grading — 🆕 lligat a **D-10 / D-OBERTA-1**
- La **sembra passa a la taula de grading** i a dalt s'informa **quin ruleset la genera** (TAXONOMIA
  T4). El motor de re-escalat ja funciona (`generate_graded_specs`); el que la diagnosi reserva és
  **QUI/QUAN decideix propagar** = la **decisió conscient de la tècnica**, que viu al **tancament
  assistit (D-10)**, no com a efecte automàtic d'acceptar.
- 🔶 **Frontera:** aquí s'**invoca i es mostra** la propagació + el ruleset; la lògica de generar/
  segellar grading és G6/D-1 (guard de segellat) i el moment conscient és D-10.

### 1.4 Canviar nomenclatura (autoria a nivell model) — 🔌 (endpoint existeix)
- El tècnic **renomena** un POM quan fa patrons/fitxa; la canònica només sembra (llei de sobirania).
  L'endpoint `poms/<id>/nomenclatura/` ja existeix (DIAGNOSI_FASE_B §6.2). Cal cablejar-lo a Mesures.

### 1.5 Veure els números amb precisió de unitat — 🔧
- **1 decimal en cm, 2 en inch** a TOTS els números (DISSENY_MODEL_VIU §6). Arrodonir a
  **presentació, no a emmagatzematge** (desar canònic + precisió completa; evitar round-trip drift
  que contaminaria `MeasurementChangeLog` append-only).

### 1.6 Veure l'arbre de dependència — 🔧 (lectura a Mesures) / 🔌 (editable a edició de model)
- Mostrar la llinatge garment type → garment item → model. **A Mesures = lectura**; a **edició de
  model = canviable** (decisió Agus). El **ruleset** ha de ser **visible i canviable** perquè d'ell
  se'n desprèn la sembra del grading (decisió Agus; el camp `grading_rule_set` ja viu al Model).

### 1.7 Watchpoints — 🆕 **D-12** (entitat nova)
- Botó per **escriure watchpoints**: camps **lliures de comentari** que **mantenen referència a la
  tasca/ronda** on s'han creat (TAXONOMIA §3.4: origen = quina ronda). **Travessen gates** (es creen
  a Proto, segueixen visibles fins a Producció). **No** van a la fitxa tècnica, **sí** lligats a
  l'historial perquè un altre tècnic entengui les advertències. `Watchpoint` **no existeix avui**
  (D-12, DELTA total) → construcció nova.

### 1.8 Programar dates al calendari — ⏸ **diferit (calendari es refà)**
- **Assignar/reagendar dates** de tasca. El calendari **es refarà amb un altre aspecte** (decisió
  Agus) → la programació de dates des de Mesures **depèn del calendari nou**, no d'aquest sprint.
  Es deixa el **seam** (l'acció de "programar represa" existeix com a concepte; la materialització
  espera el calendari nou).

### 1.9 Enviar mida a producció (proto o mostra) — 🆕 **handoff lleuger bidireccional amb data**
- El tècnic **envia** (botó/acció del menú) avisant el **PM** que **model + mides estan llestos** per
  a producció. El PM, quan ho té, **informa la data d'arribada**; el sistema aleshores **avisa el
  tècnic** per fer la tasca que correspongui (mesurar el proto/mostra que arribarà).
- És el **handoff lleuger** de TAXONOMIA §5.1 amb cicle complet: surt (tècnic→PM, "llest"),
  torna (PM→tècnic, "arriba el dia X → fes la tasca"). Encaixa amb les arribades de §4 (T4/T6: "avís
  d'arribada de prenda"). Estat pendent/resolt; afecta calendari i tasques posteriors.

---

## 2. Per què aquesta llista no és un sol sprint (l'honestedat que faltava)

Els punts es reparteixen en **tres ritmes**, no un:
- **Ara, barat:** 1.1 (tornar+sortir), 1.4 (nomenclatura, cablejat), 1.5 (unitats), 1.6 (arbre
  lectura + ruleset visible) — UI/lectura + endpoints existents. + la paritat d'editor pendent (P5
  fitting, color/capçalera ja fets).
- **Construcció nova, seqüenciada a la seva D-x:** 1.7 watchpoints (D-12), 1.3 propagar-conscient
  (D-10), 1.9 enviar a producció (handoff lleuger bidireccional).
- **Diferit a una altra peça:** 1.8 dates (calendari es refà) · jubilació de la pantalla Kanban
  actual (quan Pla de treball + dashboard del tècnic la cobreixin).
- **Ja viu, només exposar:** 1.2 presa tipada (origen ja existeix).

Tractar-ho com un sol bloc és el que ens encallava. La spec defineix el **destí**; el cens i el pla
el **seqüencien**.

### FET — Sprint TANCAMENT MESURES+FITTING (2026-06-23, commits `9a370c1..b12b36b`, dev, sense push)
El **ritme barat** + la **paritat plena** estan FETS sobre l'editor únic `MeasureGrid`:
- ✅ **1.1 tornar+sortir** → P0 (`BackButton` reusable + `EditorHeader.onBack`).
- ✅ **1.5 unitats** (1 decimal cm / 2 inch, arrodonir a presentació) → P6 (`fmtMeasure`+`useUnit`).
- ✅ **1.6 arbre de dependència (lectura) + ruleset visible** → P8 (`DependencyPanel` + `grading_rule_set_nom`).
- ✅ **1.2 presa tipada per origen** (exposar) → P9 (`stageAccent` tipa cada origen a columna/historial).
- ✅ **Paritat d'editor** → P5: el FITTING convergeix a `MeasureGrid` (nom 2 línies, color només-activa,
  règim editable, propagació germanes, capçalera unificada). `MeasureTable` només queda per a l'Escalat
  (jubilació = peça pròpia Escalat→MeasureGrid). [Validació en viu pendent.]
- 🛑 **1.4 nomenclatura editable a nivell model** → P7 BLOQUEJAT: l'endpoint nomenat
  (`poms/<id>/nomenclatura/`) edita el POM **del tenant compartit**, no el model → violaria sobirania.
  Autoria de model = `BaseMeasurement.nom_fitxa` (exigeix `bm_id` al serializer + decisió de domini) →
  peça pròpia. Vegeu `DIAGNOSI_P7_NOMENCLATURA.md`.

Pendents (fronteres, no aquest sprint): 1.3 propagar-conscient (D-10), 1.7 watchpoints (D-12), 1.8
calendari, 1.9 enviar a producció (handoff). Vegeu DECISIONS §4.

### FET — Tancament 2a tanda (2026-06-23, commits `90ed4fa..f3300f1`, dev, sense push)
- ✅ **Editor únic = check + fitting + ESCALAT.** PropagatedEditor (Escalat) convergit a `MeasureGrid`
  (mode model: Base vigent + override; talla base read-only). **`MeasureTable.jsx` JUBILAT** (+ codi mort
  `MeasurementTable.jsx`). Motor `setSizeOverride`/`generate_graded_specs` INTACTE.
- ✅ **Sortir de l'eina → tasca Pausada** (1.1 cicle): ModelMeasurements pausa en sortir si s'hi entra per
  tasca → desbloqueja el Play-per-reobrir.
- ✅ **Coma decimal** a l'input (60,5 == 60.5) a tota la superfície MeasureGrid.
- ✅ **"Editar" del model** mogut a la pestanya Resum (no a la capçalera global).
- 🔶 Es mantenen fora: propagar/generar grading conscient (D-10/G6), anti-fragmentació plena de
  ModelMeasurements (entrada-per-POM + grading), watchpoints/handoff/calendari, cicle de tasca complet.

### FET — Sprint Cadena de Treball (2026-06-23, commits `ba14b7e..8048e77`, dev, sense push)
La cadena del tècnic és construïble **end-to-end des del menú del model**:
- ✅ **1.1 obrir tasca on-demand** (P1): porta-menú `open-task` (crea-si-falta + auto-assign + En curs).
- ✅ **1.4 nomenclatura editable a nivell model** (P4): autoria a `BaseMeasurement.nom_fitxa` (sobirania) →
  **desbloqueja P7** (ja no s'edita el POM tenant compartit).
- ✅ **1.6 ruleset canviable** (P3): `RuleSetCard` al model (a més de visible per P8).
- ✅ **1.7 Watchpoints (D-12)** (P5): entitat + endpoints + panell a l'editor (v1).
- ✅ **Convocar fitting des del llenç** (P2) · **jubilació import vell** (P6, servei viu mantingut).
- 🔶 **1.3 propagar-conscient (D-10)** = única frontera pendent, SUPERVISADA amb l'Agus (toca el motor).

### FET — Sprint Sobirania de la regla (2026-06-23, commits `5ded3d4..ad10e4a`, dev, sense push)
La regla (deltes+breaks) és patrimoni VIU i editable del model; l'import calcula però no reté el propagat:
- ✅ **P1 — import reté base+deltes+breaks, NO el grading propagat:** deixa de persistir `GradingVersion`/
  `GradedSpec` (col·lisionaven amb el sembrat del motor); manté extracció + `detect_grading` (breaks!) +
  derivació de `ModelGradingRule`. El SF queda com a contenidor; la projecció és conscient (D-10).
- ✅ **P2 — conflicte conscient regla importada vs retinguda:** snapshot abans del wipe + `grading_rules_match`
  (per forma, motor intacte) → 409 + rollback (patró Size Library) → el tècnic tria; la triada esdevé la
  regla del model. Cap sobreescriptura en silenci.
- ✅ **P3 — delta + break editables a la talla base (Mesures):** `set_pom_regim_view` estès per desar
  `increment_base/increment_break/talla_break_label` a `ModelGradingRule` (origen MANUAL); el motor els
  llegeix via `_load_grading_rules→_apply_rule` (CÀLCUL intacte). Desplegable "a partir de" = run del model.
- ✅ **P5 — poda del grading propagat a la superfície d'estructura** + botó "Tornar al model".
- ✅ **P6 — "Fer comentari" (Watchpoint) al menú del model**, ancorat a la tasca en curs (o al model).
- 🔶 **P1-frontera (D-1/D-10):** estat/segellat del `SizeFitting`/`GradingVersion` a l'import = SUPERVISAT.
- ⏸ **P4 (jubilar 4/5 → fusió a CheckMeasureEditor) DIFERIT:** fusió de l'editor d'estructura (base+POM) dins
  el llenç de check = decisió de disseny + funció gran, marcada per a validació en viu; P5 ja n'ha tret la
  col·lisió de propagat. Pendent amb l'Agus.

---

## 3. Anti-fragmentació (la causa de les sorpreses)

Avui hi ha funcions repartides en pantalles que haurien de derivar del llenç: l'entrada per POM
(amb "Generar grading automàtic" = propagar + afegir/ordenar POM), l'Escalat, el fitting editor.
Això és la **mateixa fragmentació** que ja vam unificar amb check+fitting, i és el que el cens (§5)
ha de mapejar d'un sol cop — **quina pantalla fa què, què duplica, què és la canònica** — perquè no
les anem descobrint per captura.

---

## 4. Entrada — des del Pla de treball del model (NO des d'un kanban)

El model kanban antic **està trencat per disseny** (TAXONOMIA §8.4, PLA_DE_TREBALL): els seus
components s'han repartit en dues escales i **la pantalla de Kanban actual es jubilarà** quan les
peces noves la cobreixin.
- **Zoom-in (el model):** el **Pla de treball** del model és des d'on s'obre / pausa / tanca cada
  tasca. **Mesures s'obre des d'aquí** (Play sobre la tasca de mesura → obre l'eina, mode treball).
- **Zoom-out (el tècnic):** el **dashboard del tècnic** = la cua de models per tècnic. **Encara no
  construït.**

Modes de Mesures:
- **Mode treball** — obert des de la tasca (Play al Pla de treball). En sortir de l'eina → torna al
  dashboard, tasca **Pausada** (Done és Stop explícit).
- **Mode consulta** — des de la fitxa del model, read-only.

Capçalera unificada (identitat de model + franja contextual) als dos editors i dos modes. *(ja fet
a la B-bis: EditorHeader.)*

> La **pantalla de Kanban actual** és **jubilació pendent** (no aquest sprint): es retira quan el Pla
> de treball (zoom-in, parcialment viu) + el dashboard del tècnic (zoom-out, per construir) la
> cobreixin, d'una passada conscient confirmada a pantalla (PLA_DE_TREBALL §8.4 disciplina).

---

## 5. Com es tanca l'sprint (mètode corregit)
1. **Congelar aquesta spec** (corregida) al `DECISIONS.md` com a destí.
2. **Un sol cens ampli** (no comparació): tota superfície del frontend que (a) pren/edita mesures,
   (b) propaga/genera grading, o (c) edita estructura de POMs (afegir/ordenar/anomenar) — component,
   endpoint, i si duplica. Que **trobi els germans**, no per illa. Creuat amb les D-x i les superfícies
   ja existents.
3. **Pla tancat:** mapeig de cada punt de §1 a fet/cablejar/construir, seqüenciat per ritme (§2).
4. **Acabat = Mesures fa el que diu l'spec.** Final definit.

---

## 6. Fronteres (què NO és aquest sprint)
- 🔶 **G6 / D-1:** lògica de generar/segellar grading, guard de segellat `GradingVersion`, col·lisions
  de grading, rename de nomenclatura backend. Aquí s'invoca i es mostra; no s'autora.
- **D-10 tancament assistit:** la propagació-conscient hi viu; aquest sprint l'**invoca**, no construeix
  el qüestionari binari sencer (decisió pròpia).
- **Calaix de DADES:** poblar `pom_global` (POMMaster sense canònic), rule set/tol de models buits.
- **D-13 temps per model / cost:** dimensió d'esforç del patrimoni, lectura per profunditats. Fora.
- **G9:** congelació de TaskType (fitting = sessió de calendari, no TaskType).

---

## 7. Decisions de domini ja resoltes per l'Agus (2026-06-23) — registrades, no es re-pregunten
- **Enviar a producció:** és acció amb conseqüència (afecta calendari i tasques posteriors) =
  handoff lleuger. *(No es pregunta si "genera tasca": evidentment sí.)*
- **Arbre de dependència:** lectura a Mesures, **canviable a edició de model**.
- **Ruleset:** visible **i canviable** (d'ell se'n desprèn la sembra del grading).
- **Propagar:** la sembra passa a la taula de grading i informa a dalt quin ruleset la genera. *(No
  hi ha "pàgina de proto" separada a conservar/jubilar; la propagació viu al llenç.)*
- **Watchpoints:** camps lliures de comentari amb referència a la tasca de creació; visibles a
  l'historial per a altres tècnics; **no** a la fitxa tècnica.
- **Sortir sense canviar:** lliure; si s'ha entrat per tasca, la sessió d'edició es tanca (tasca
  pausada); uns segons sense fer res no generen res.
- **Entrada:** NO "tres portes / kanban". El kanban antic està trencat per disseny i es **jubilarà**;
  l'entrada a Mesures és des del **Pla de treball del model** (zoom-in). El dashboard del tècnic
  (zoom-out) encara no està construït.
- **Calendari:** es **refà amb un altre aspecte** → la programació de dates des de Mesures hi depèn;
  diferida.
- **Enviar a producció:** botó/acció del menú; cicle complet tècnic→PM ("llest") → PM informa data
  d'arribada → sistema avisa el tècnic per fer la tasca que toqui.
