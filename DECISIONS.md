# DECISIONS.md — Registre de lleis de disseny FTT

> **Cervell del projecte.** Lleis durables i decisions vives, perquè no es re-litigui ni es
> re-investigui el que ja s'ha decidit en xats anteriors.
>
> **Com es llegeix:** dos tipus d'entrada.
> - **Lleis** (mètode · domini · presentació) = estables, gairebé no canvien. Es consulten ABANS
>   de cada diagnosi.
> - **Decisions d'abast vives** = evolucionen sprint a sprint; s'actualitzen sovint.
>
> **Com es manté:** s'actualitza al final de cada sessió (servidor `/root/fhort-sessions/DECISIONS.md`
> + còpia manual al projecte). Quan una decisió viva es completa, baixa a "Històric" o es promou a llei.
>
> Última actualització: 2026-07-08

---

## 1. Lleis de mètode (no negociable)

- A Claude xat es DISSENYA i es fa ARQUITECTURA; un cop decidit, es generen instruccions per a
  Claude Code (blocs copiables) que l'Agus passa i executa. Primer investigar, després construir.
- **Patró A** (diagnosi read-only) → **Patró B** (implementació amb equip) → **Patró C** (decisió de
  disseny = Agus; Claude decideix detall tècnic només quan es delega explícitament).
- **Diagnosi abans de dimensionar — en ESPAI i en TEMPS.** Espai: llegir el codi real abans d'estimar.
  Temps: comprovar al registre + converses passades si la decisió JA existeix abans de re-obrir-la.
- **Llegir el projecte SENCER, no l'illa.** Comprovar què ja s'ha CONSTRUÏT abans de dir "no existeix"
  o "és estructural". (Lliçó 2026-06-23: el read-only del check va ignorar el fitting editor ja fet.)
- **No més pedaços: unificar el ja construït.** Si dues superfícies viuen del mateix UI/dades, no es
  peguen per separat — es convergeixen. Pegar dues vegades garanteix reprocés. (Llei transversal a tot
  el refactor, no només a G1.)
- Codi mínim · un focus per commit · `git add` explícit (mai `-A`) · regla del verd abans de cada
  commit (`manage.py check` + `npm run build` + verificador/guardians/revisor) · MAI push d'agents
  (l'Agus puja des de SSH) · i18n-gate ca/en/es a tota UI nova.
- Els agents corren amples i autònoms; **verd = continuen**. Només s'aturen per blocador dur,
  contradicció de paradigma, o verd trencat.
- **Mètode com a skills al repo (2026-07-07).** La litúrgia viu versionada: `CLAUDE.md` (lleis
  sempre-actives) + `.claude/skills/patro-a` (diagnosi) i `patro-b` (implementació) + 8 agents a
  `.claude/agents/`. Els prompts passen a ser briefs curts que invoquen les skills. **Diagnosis
  commitades:** l'arrel de `docs/diagnosis/` = vigents (font de veritat); `docs/diagnosis/arxiu/` =
  històric segellat (capçalera `⚠️ SUPERADA`), MAI font per a decisions. `ESTAT_*`/`DECISIONS.md`
  segueixen SENSE commitar.

## 2. Lleis de domini

- **L'última presa de mesura escrita és la veritat vigent** (precedència temporal, no d'origen).
- **Mesura manual i automàtica són el mateix procés d'entrada;** cada presa = una columna nova.
- **Fitting i size check són EL MATEIX ACTE** (mesurar → resoldre en columna nova) → mateixa
  superfície tècnica (Mesures), no dues pantalles. El **fitting com a PANTALLA convocada amb totes
  les talles propagades QUEDA JUBILAT**: es dissol en (1) presa de mesura dins Mesures (talla base,
  origen FITTED) i (2) tot el treball sobre totes les talles → funcionalitat de **Grading/Escalat**.
- **Mort del fitting → migració a Grading (CONDICIÓ BLOQUEJANT):** tota la maquinària que avui penja
  del fitting (càlcul, propagació, règim LINEAR/STEP, breaks, generate_graded_specs, GradingVersion,
  ModelGradingOverride, _apply_rule/derive_break_fields) ha d'existir i estar VERIFICADA viva i
  accessible a Grading ABANS de jubilar cap pantalla/funció de fitting. No es jubila res del fitting
  fins que el seu equivalent és viu a Grading — altrament es perd l'esforç de construcció.
- **Check = decisió de qualitat per línia** (accept dins tolerància / descarta discrepància), no una
  segona mesura. El veredicte de model (Acceptat/Rebutjat/Descartat) el deriva el motor.
- **Fitting amb model = més maduració** que el check a taller → els estadis es mostren DIFERENCIATS a
  la taula (`checked` vs `fitting`); el backend ja els distingeix (origen CHECKED vs FITTED).
- **Sobirania de dades:** la plantilla (`GarmentTypeItem`) sembra; el model POSSEEIX. L'autoria
  (valors, nomenclatura) viu a nivell de model.
- **Propagar grading sobre la realitat mesurada vàlida crea una columna nova.**
- **Propagar = ACTE CONSCIENT.** Propagar és aplicar deltes+breaks sobre les talles per omplir la
  taula de grading, i és SEMPRE decisió conscient de la tècnica. MAI automàtic: ni acceptar un size
  check ni "tancar un fitting" propaga. Flux: s'obre Mesures (mai fitting), es treballa la talla base
  tantes vegades com calgui; quan està bé es propaga; en propagar s'entra a Grading (totes les talles,
  règim, breaks, ajustos puntuals per talla sobre prendes reals). L'auto-propagació viva avui
  (resolve_size_check:230, close_piece_fitting:469) és codi a JUBILAR/RECONSTRUIR dins el zoom-out,
  NO a retocar ara (trencar-ho abans de tenir Grading-com-a-tasca estrandaria l'usuari).
- **On viu el Propagar conscient:** com a TASCA de Grading al Pla de treball intern del ModelSheet
  (zoom-in), reconstruïda durant el zoom-out. Mai acoblat al Kanban de menú (que es jubila).
- Els estadis de la taula base són un **llibre major** (lectura derivada de `MeasurementChangeLog`);
  l'escriptura de base la fan els motors (mesura/check/fitting), no la vista.
- **Welford pur, llindar 5 (2026-07-07).** `WELFORD_MIN_SAMPLES=5`. L'empíric (`TaskTimeEstimate`:
  n/mean/m2) només conté **mostres reals**; el seed teòric viu a `TimeSeed` com a **llavor de tenant**,
  MAI a `TaskTimeEstimate`. (Migració: les 442 cel·les teòriques n=0 destil·lades a llavors per-task.)
- **Cascada de resolució de temps (2026-07-07).** Ordre: empíric(item,task) si n≥5 → empíric global del
  tenant per task (mitjana de cel·les madures) → llavor `TimeSeed` (scope task, sinó fase) → **captura
  conscient del PM**. **Mai None en planificar, mai valor inventat.** El PM captura via `needs_estimate`
  (llavor origen=CAPTURA) i desbloqueja al moment. El snapshot (`ModelTask.estimated_minutes`) es
  **re-resol NOMÉS per a tasques Pending** als punts de recompute (convergència única
  `recompute_for_technicians`); InProgress/Paused/Done conserven el snapshot. Cap canvi d'estimació
  espontani fora de recompute; mai es clobbera un valor amb None.

## 3. Lleis de presentació (UI)

- **Nomenclatura POM a 2 línies:** nom EN canònic a dalt + nom en idioma usuari a sota (més petit,
  cursiva gris). Lligat a la dada `nom_client = nom_en`. Implementació de referència: POMBrowser
  (verificar el landing exacte abans de reusar).
- **Nomenclatura sempre editable a nivell model** (el tècnic la renomena al fer patrons/fitxa);
  la canònica només sembra. *(Implementació pendent — vegeu §5.)*
- **Amplada de columnes real** (no estirar a l'amplada de finestra); les columnes s'afegeixen cap a la
  dreta, amb scroll horitzontal en sobreeixir (i vertical per molts POMs).
- **Icones només outline** (mai `-filled`; webfont Tabler). **Colors via tokens CSS, mai hex**
  (excepció: `KONVA_COL` literal per a canvas, que no resol `var()`).
- **Fitxa tècnica:** cos de text mínim 8pt, ideal 9-10pt; mai per sota de 8pt.
- **Display de TaskType per code via i18n (2026-07-07).** El nom visible d'un tipus de tasca es resol
  pel namespace `tasktype.<code>` (ca/en/es); `TaskType.name` (BD) = **fallback** (base EN canònic),
  mai es persisteix ni es pinta en cru. Tot render-site passa pel helper `taskTypeLabel(t, code, name)`.

---

## 4. Decisions d'abast vives (s'actualitzen sprint a sprint)

### DUES FACTURACIONS SEPARADES (2026-07-07)
**backoffice→tenant** (ús de la plataforma; domini public existent; APARCAT) **≠ studio→tercers**
(mòdul comercial tenant-side). **No comparteixen entitats.** Cap barreja de models entre les dues.

### Model comercial Studio (2026-07-07, per implementar — T3)
- Entitats: **Comanda → LiniaComanda** (servei × `garment_type_item` × preu × qty) **→ Encàrrec**
  (model, línia) **→ `ModelTask.encarrec`** (FK nullable).
- **Tasca fora de recepta = extra facturable detectat.**
- **Preu = decisió comercial;** el sistema INFORMA el cost estàndard (Welford) i el marge, no el fixa.
- **Gate per tier:** Brand no veu el mòdul.
- Decisions OBERTES abans del brief T3: (a) cost intern pla vs per-perfil; (b) fitting per sessió vs
  per fase; (c) recepta oberta-amb-marca vs tancada. + `garment_type_item` obligatori al wizard.

### Mòdul Comercial Studio — disseny fundacional (2026-07-08)
Disseny complet a `DISSENY_MODUL_COMERCIAL.md`. Substitueix les 3 decisions obertes de l'entrada
T3 anterior. **Lleis del mòdul:**
- **Mestre Product amb 4 natures:** INTERNAL_SERVICE / EXTERNAL_SERVICE / GOODS / PACK.
- **Servei extern NO és tasca:** crea `Expense` + event de calendari (no entra al motor de tasques/Welford).
- **Preu = el sistema PROPOSA, l'humà FIXA.**
- **Snapshot de preu i recepta als documents** (congelat al moment d'emissió).
- **Delta bidireccional a l'entrega:** extres + regularització negativa (cas Brownie).
- **Factura legal FORA de l'abast:** el mòdul arriba fins a albarà + liquidació + marca `invoiced`.
- **Naming BD/codi en ANGLÈS.**
- **Multi-proveïdor amb preus per article.**
- **Cost intern v1 = tarifa plana** (`TenantConfig.hourly_rate`).
- **Fitting per sessió.**
- **Recepta oberta amb marca `off_recipe`.**
Inventari: 13 taules · 7 pàgines · 7 modals · 4 PDFs · 7 informes. Blocs B0–B5, ~8-10 sessions.
Oferta confirmada a v1 (dolor Brownie). Es desenvolupa en XAT PROPI amb el document com a substrat.
El document JA és al servidor (324 línies) amb l'Annex A = brief B0 llest per llançar.

### 2026-07-08 — Decisions §9 Comercial Studio (deferides / tancades post-B0)

- **#1 (estructura línies Quote/Order), #2 (numeració documents), #5 (estats WorkOrder)**:
  deferides conscientment a investigació pròpia de B2/B3. No bloquegen B1 (cap toca
  Product/Unit/satèl·lits).
- **#3 (tarifa de venda TIME_BASED)**: TANCADA — camp `sale_rate` a `Product`. El preu és
  Welford(task_code, GTI) × multiplicador, bifurcat en dos: `hourly_rate` (TenantConfig,
  cost) i `sale_rate` (Product, venda). El GTI és pes de complexitat dins la cascada, no un
  preu en si.
- **#4 (UX matriu preu×GTI)**: TANCADA — `ProductPriceGTI` reescopit com a taula
  d'EXCEPCIONS (no graella densa; no hi ha "57 items" com a mida fixa, cada tenant crea els
  GTI que vulgui). Rellevant només per: serveis `FIXED` (sense cascada) i correccions manuals
  puntuals sobre `TIME_BASED`. UX: llista filtrable + "afegir excepció" des de la fitxa del
  Product.
- **Naming `Product` ↔ `Production`**: no és col·lisió (B0 confirmat), és proximitat visual.
  Convenció: imports amb prefix de context explícit (`from commerce.models import Product`)
  + docstring a `Product` que remet a no confondre amb `tasks.Production`.
- **Dependència B5**: `feature_flags` no s'exposa a `/me` (`accounts/serializers.py:16-33`).
  Bloquejant per al gate de tier; primer pas del brief de B5.

### Federació Brand↔Studio (2026-07-07, disseny; pendent d'implementar rere prerequisits)
- El model té **UNA casa (Brand)**; l'**execució** (tasques, timers, Welford) viu a **QUI EXECUTA
  (Studio)**. Lliurables = **un binari, dues referències** (`DeliverableRegistry` a public, futur).
- Vincle **`TenantLink` a public** via clau (ancoratges reservats: `Customer.codi_global` al tenant /
  `Client.codi_tenant` a public). Al Studio, el model assignat s'instancia com a **Model local
  origen=EXTERN (opció B2)**.
- **Brand veu** planificació/maduresa/entrega/incidències; **MAI temps ni tècnics.**
- **Benchmark cross-tenant:** minuts, k≥5 tenants, **mai entra a la cascada** de planificació.
- **Prerequisits:** R5 (seed onboarding genèric), R9 (media per schema), R10 (primitiva cross-tenant).

### Refactor d'eines — pla de grups (post-aparcament de facturació)
- **APARCAT:** motor de facturació/backoffice + meritació → sprint futur, tier `estudi`. No es toca res.
- Premissa: el deploy sobreescriu PROD (versió antiga, sense clients reals) → els antics "riscos de
  dades a PROD" passen a ser, com a molt, correcció de lògica.
- Grups: **G1** (unificat, vegeu sota) · **G2** estat del model · **G3** import vell · **G4** POM-editor
  vell + òrfenes · **G5** codi mort transversal · **G6** grading (l'últim dels grossos) · **G7** bug
  calendari · **G8** higiene frontend. **G9** = lent transversal (TaskType governance), no grup en seqüència.

### G1 — redefinit a SUPERFÍCIE UNIFICADA de mesura resolta (2026-06-23)
- **Ja NO és "re-allotjar el size check"** sinó la superfície única on conviuen **check + fitting**
  (mateix editor, layout i contracte de dades). Decisió Agus: no més pedaços.
- L'**editor de fitting** (`/fittings/<id>`) ja fa història read-only + columna editable a UNA graella,
  oberta des de la tasca, expandint-se per columnes. **És la referència; no es reinventa.**
- El motor `resolve_size_check` queda INTACTE i passa a ser un cas d'ús d'aquesta superfície.
- Properes correccions de G1 que entren a la convergència (de la validació en viu 2026-06-23):
  - una sola superfície editable (no dues graelles separades);
  - consulta des de model · edició via tasca (avui `/mesures` SEMPRE edita — cal cablejar el gating);
  - botó "des de model" ha d'OBRIR/reclamar la tasca, no navegar sec;
  - purgar vocabulari mort "tasca de POM" (4 claus `model_sheet.*`); "POM" com a capçal de columna és
    legítim i es manté.

### Frontera G1-unificat ↔ G6 (grading)
- La unificació toca el que escriu grading propagat (`GradedSpec`/`GradingVersion`). La **diagnosi de
  convergència mesures+fitting ha de MARCAR la frontera amb G6**, no colar-s'hi. Guard de segellat
  `GradingVersion` i col·lisions de grading segueixen sent G6.

### Sprint TANCAMENT MESURES + FITTING — estat (2026-06-23)
**Mesures + Fitting tancats com a UNA superfície de treball sobre l'editor únic `MeasureGrid`**, en
ritme barat. Cadena de commits locals VERDS sobre B-bis (`9a370c1..b12b36b`, dev, SENSE push).
- **P0 — botó de tornar transversal:** `BackButton` reusable + slot `onBack` a `EditorHeader`; fix del
  back hardcoded (sense i18n) a `GarmentPOMMapEditor`. *(troballa: Mesures/Fitting/Escalat ja tenien
  back propi; el que faltava era el patró únic + el cas no-i18n).*
- **P5 (a-d) — CONVERGÈNCIA DEL FITTING a `MeasureGrid`:** `FittingDetail` ja no usa `MeasureTable`;
  paritat plena amb el check (nomenclatura 2 línies, color només-activa, règim editable al leadCol,
  propagació de germanes via `onSave`→`propagar`/`update`, capçalera `EditorHeader` amb franja
  contextual de sessió). Motor `close_piece_fitting` INTACTE (resolució a ReviewScreen). **`MeasureTable.jsx`
  NO jubilat:** `PropagatedEditor` (Escalat, mode-model `persistCell`) encara en depèn → la jubilació real
  és una peça pròpia **Escalat→MeasureGrid** (no en aquest sprint). [VALIDACIÓ EN VIU pendent: propagació
  runtime + capçalera.]
- **P6 — unitats a presentació:** `fmtMeasure`+`useUnit` (helper únic); 1 decimal cm / 2 inch a les
  cel·les de valor en lectura; l'input editable es desa canònic (cap round-trip drift).
- **P7 — nomenclatura editable a nivell model: 🛑 BLOQUEJAT.** L'endpoint `poms/<id>/nomenclatura/`
  edita `POMMaster.nom_client` (tenant-POM COMPARTIT) → violaria la sobirania (§2) i "la canònica només
  sembra" (§3), i ni es reflectiria a la cel·la (mostra `name_en`/`name_cat`). L'autoria de model viu a
  `BaseMeasurement.nom_fitxa`, que exigeix emetre `bm_id` als serializers + precedència de visualització +
  decisió de domini → peça pròpia. Diagnosi: `/root/fhort-sessions/DIAGNOSI_P7_NOMENCLATURA.md`.
- **P8 — arbre de dependència + ruleset (lectura a Mesures):** `DependencyPanel` (llinatge garment_type→
  item→model + `grading_rule_set` vigent); backend emet `grading_rule_set_nom` (read-only). SEAM visible,
  autoria a edició-de-model (no aquí).
- **P9 — presa tipada per origen:** `stageAccent` tipa CADA origen amb punt de color (fitting=verd,
  taller/proto=daurat, derivada/importada=gris) a la columna/historial del check.
- **Fronteres pendents (no tocades):** PROPAGAR-conscient (D-10), Watchpoints (D-12), Enviar a producció
  (handoff), Calendari/dates (es refà), G6 (rename/segellat grading), jubilació Kanban, Escalat→MeasureGrid.

### Sprint TANCAMENT (2a tanda) — Escalat + cicle de tasca + 2 bugs (2026-06-23)
Cadena VERDA sobre l'anterior (`90ed4fa..f3300f1`, dev, SENSE push). **L'editor únic `MeasureGrid` ara
serveix les TRES superfícies: check + fitting + escalat.**
- **P1 [VIU] — Escalat → MeasureGrid:** `PropagatedEditor` deixa `MeasureTable` i usa `MeasureGrid` en
  mode model (Base vigent read + Fit actual = override; talla base read-only via nou `active.readonly`),
  capçalera `EditorHeader` ("Escalat", no "grading propagat"). Motor INTACTE: segueix cridant
  `models.setSizeOverride` (mateix QUI/QUAN); l'interior (`generate_graded_specs`) no es toca; germanes
  es refresquen rellegint `taula-mesures`. **JUBILATS `MeasureTable.jsx` + `MeasurementTable.jsx`** (−806
  línies netes). Adapter `buildEscalatGroups/Rows` a `fittingGridAdapter`.
- **P2 [VIU] — sortir → Pausada:** `ModelMeasurements` pausa la tasca en desmuntar si s'hi va entrar per
  tasca (patró d'`EscalatTask`). Desbloqueja el Play-per-reobrir (InProgress no té Play). `transition_task`
  i l'exclusió un-InProgress NO tocats.
- **P3 — coma decimal:** input `type=text inputMode=decimal` + `toNum` (`,`→`.`) a MeasureGrid → 60,5 == 60.5
  (check/fitting/escalat). (La hipòtesi inicial "és P6" era falsa: `fmtMeasure` és display-only.)
- **P4 — botó "Editar" a Resum:** mogut de `ModelSheetHeader` a la pestanya Resum (edita el model, no la
  pantalla visible).
- **Editors a HEAD:** MeasureGrid (check · fitting · escalat) · EditableTable (entrada/estructura POM,
  superfície a part) · MeasurementBaseGrid (catàleg d'ítems). Els 2 grids legacy, jubilats.
- **Fronteres respectades:** generar/propagar grading conscient (D-10/G6), anti-fragmentació plena de
  ModelMeasurements, watchpoints/handoff/calendari, cicle de tasca complet (auto-tancar/sort+open).

### Sprint CADENA DE TREBALL — el tècnic fa tot el camí des del menú (2026-06-23)
Cadena VERDA (`ba14b7e..8048e77`, dev, SENSE push). **La cadena del tècnic és construïble end-to-end**;
única frontera pendent = propagar-conscient (D-10, supervisada). Cens base: DIAGNOSI_CADENA_TREBALL.md.
- **P1 [VIU] — porta-menú:** `open_model_task_view` (POST `models/<id>/open-task/ {code}`) CREA la
  ModelTask si falta + la posa En curs reusant `transition_task` (auto-assign+timer). ModelSheet treu
  el gate `hasPomTask`; "Editar mides"/"Editar escalat" obren la tasca encara que no existeixi.
- **P2 — convocar fitting des del menú:** `ActionsMenu` → `FittingSessionNew?model=` (prefill); el
  fitting es convoca des del llenç (abans standalone).
- **P3 — ruleset CANVIABLE al model:** `RuleSetCard` a Resum (reusa AxesSelector+RuleSetPicker) →
  PATCH `update-step2 {grading_rule_set_id}` (re-materialitza config; NO toca el motor de propagació).
  Tanca SPEC §1.6 (visible+canviable).
- **P4 [VIU] — nomenclatura per-model (desbloqueja P7):** autoria del nom al MODEL (`BaseMeasurement.
  nom_fitxa`, precedència sobre la canònica), NO al POM tenant. Serializers emeten `bm_id`+`nom_fitxa`;
  NomCell de MeasureGrid editable a check+fitting. *(Integració al wizard d'import = follow-up.)*
- **P5 [VIU] — Watchpoints (D-12):** entitat nova + migració `0042_watchpoint` (generada, NO aplicada)
  + endpoints (resolve/reopen) + `WatchpointsPanel` a l'editor de mesures. Text lliure ancorat al model
  + tasca d'origen, open→resolved, travessa gates, no a la fitxa. *(Timeline = follow-up.)*
- **P6 — jubilació import vell:** retirats els 2 endpoints d'onboarding morts (0 consumidors). El servei
  `extraction_service`/`EXTRACTION_PROMPT` es MANTÉ (viu: wizard nou + size-map) — frontera respectada.
- **Frontera pendent (supervisada, NO autònoma):** propagar-conscient D-10 (gate abans dels 3
  `generate_graded_specs`) + segellat D-1 → es fa amb l'Agus al davant.

### Sprint SOBIRANIA DE LA REGLA — import reté regla, no propagat; regla viva i editable (2026-06-23)
Cadena VERDA (`5ded3d4..ad10e4a`, dev, SENSE push). **Llei (Agus):** tot sembra el model però tot viu i
és modificable AL MODEL, inclosa la REGLA (deltes+breaks). L'import CALCULA tot però RETÉ només base +
deltes + breaks; NO reté el grading PROPAGAT (col·lisiona amb el sembrat del motor). base s'autora ·
deltes+breaks s'autoren · grading PROJECTA (conscient, D-10).
- **P1 [VIU] — import reté base+deltes+breaks, no el propagat:** `import_session_confirmar_view` deixa de
  persistir `GradingVersion`/`GradedSpec`; manté extracció + `detect_grading` (breaks) + `ModelGradingRule`
  (deltes+breaks). SF = contenidor; `generate_grading_view` projecta després (D-10).
- **P2 [VIU] — conflicte conscient importat vs retingut:** snapshot abans del wipe + `grading_rules_match`
  (per forma; motor intacte) → 409 + rollback (patró Size Library) → tècnic tria (`grading_choice`
  importats/heretats); la triada esdevé la regla del model. Cap overwrite silenciós.
- **P3 [VIU] — delta+break editables a la talla base (Mesures):** `set_pom_regim_view` estès per desar
  `increment_base/increment_break/talla_break_label` a `ModelGradingRule` (origen MANUAL). Motor de càlcul
  (`_apply_rule`/`generate_graded_specs`) INTACTE: només canvia QUINA regla llegeix (la viva) i COM s'edita.
- **P5 [VIU] — poda del propagat a la superfície d'estructura** (Generar grading/Veure escalat) + "Tornar al model".
- **P6 [VIU] — "Fer comentari" (Watchpoint) al menú del model**, ancorat a la tasca en curs o al model.
- **P4 DIFERIT:** jubilar pantalles 4/5 fusionant l'editor d'estructura dins CheckMeasureEditor = disseny +
  funció gran (validació en viu) → amb l'Agus. P5 ja ha tret la col·lisió de propagat d'aquelles pantalles.
- **Fronteres SUPERVISADES (NO tocades):** estat/segellat del SizeFitting + GradingVersion a l'import (D-1/D-10);
  propagar-conscient (D-10). El motor de patrons no s'ha tocat ("motor bé, tocar poc").

### G9 — TaskType governance (lent transversal, activa des d'ara)
- **Congelació viva:** cap escriptor/editabilitat nou de `TaskType` al tenant; referències noves
  sempre per `code`, mai per PK (el sistema ja s'hi ancora).
- **Tall futur:** definició de TaskType → sistema/public (patró POMGlobal); `TaskTimeEstimate` (Welford)
  queda al tenant com a FK cross-schema. Repensar `on_delete` (CASCADE/PROTECT no valen cross-schema).
- **Moviment físic = sprint futur bloquejat per** crear `stagingbackoffice.fhorttextile.tech`.

### Frontera del motor → REASSIGNADA al zoom-out (2026-06-24)
- La diagnosi docs/diagnosis/DIAGNOSI_MOTOR_FRONTERES.md va revelar que: (A) el guard de segellat JA
  existeix complet als dos camins (close_piece_fitting + resolve_size_check mirror) amb allow_reopen_sealed
  → és AUDIT, no forat (només cal netejar docstring stale a advance_phase:714-715). (B) el desacoblament
  de la propagació NO és "treure una línia": és la punta de la migració fitting→Grading, que pertany al zoom-out.
- DECISIÓ: el motor NO es toca en sessió pròpia abans del zoom-out. Es tanca DINS del zoom-out, perquè
  el destí (Grading-com-a-tasca) és part d'aquell. El següent gran salt és UN de sol: zoom-out + tasques
  + reconstrucció de Grading com a successor del fitting.
- PRIMERA TASCA del zoom-out = DIAGNOSI DE PARITAT fitting→Grading (inventari): per cada funció del motor
  que el fitting consumeix, on és, si Grading ja la crida, i què falta. BLOQUEJANT abans de jubilar res.

---

### RUN-CLIENT — La regla com a actiu core i secret industrial (2026-07-08)
> Diagnosi: `docs/diagnosis/DIAGNOSI_RUN_CLIENT_VINCULACIO_2026-07-08.md` · cadena Patró B `d324b22..8731d8d`.

- **[LLEI DE DOMINI] `GradingRuleSet` = ACTIU CORE i SECRET INDUSTRIAL del tenant** — la forma de
  fit per GTI × marca; el fit de cada marca és identitat de producte. Corol·laris:
  - (a) tota captura/import de regles exigeix una superfície de **PARITAT verificable** contra el
    document ABANS de persistir;
  - (b) a federació, les grading rules tenen **permís propi al vincle** (mai al paquet genèric) i el
    Studio les aplica **sense còpia de la forma**;
  - (c) el **benchmark cross-tenant EXCLOU per llei** tota forma de graduació;
  - (d) canvis al motor (G6) sempre amb **diagnosi de paritat**.
- **Valor base NO viu al run:** el run és actiu de **REGLES** (portable a un altre model); el valor
  base és dada de **MODEL** (`BaseMeasurement`/`ItemBaseMeasurement`). Confirmat: `GradingRule.valor_base`
  eliminat; `increment_base` sí poblat.
- **Import de regles (decisions vives):**
  - no-resolts = **cua persistent** (`pendents_vincular`), no creació de POM des del wizard;
  - **col·lisió de mapping = bloqueig 400** amb llista (mai `update_or_create` silenciós);
  - **toleràncies = mostrar**, persistència **diferida** al sprint POM-review amb col·lapse 2→1 ± (deute §5).

---

### NOMENCLATURA, MATCHER, INTEGRITAT DE GRADUACIÓ, PROVINENÇA (2026-07-08)
> Diagnosi: `docs/diagnosis/DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08.md` (vigent, no segellada; N3 n'implementa
> només la part del matcher) · cadena N3 `e90f39f · beadaaf · 513cb88`.

- **[NOMENCLATURA] El catàleg canònic (`POMMaster`/`POMGlobal`) NO conté nomenclatura de client.**
  Els àlies viuen a `CustomerPOMAlias (customer, pom, client_code, client_description)`, unicitat
  `(customer, client_code)` i **NO** `(customer, pom)` — un client pot tenir dos codis per al mateix
  POM (Losan H.11 sleeve opening / H.16 cuff opening). Autoria: **fitxa de Client** (àlies) vs
  **POMBrowser** (catàleg). `GradingRuleSet.customer` = **FK real** (backfill des de
  `SizeSystem.customer_codi`).
- **[MATCHER] Ordre canònic de `find_pom_master(code, description, customer)`:** (a) **àlies exacte
  del customer → HIGH** (client_code casa contra codi *i* descripció); (b) **descripció + sinònims
  canònics** → HIGH/MEDIUM; (c) **fuzzy → LOW → pendents** (mai auto-vincula, llindar c2b19bd);
  (d) **codi_client/root = fallback LOW transitori, a retirar** (abans anaven 1r amb HIGH). Si
  `customer=None`, se salta (a).
- **[MATCHER] Guard anti-many-to-one:** dues files del mateix document → mateix POM per
  descripció/fuzzy = **totes a pendents** (mai la 2a sobreescriu la regla de la 1a; `GradingRule`
  únic per `(rule_set, pom)`). **L'àlies exacte n'és EXEMPT** (repetició legítima de POM per client).
- **[INTEGRITAT DE GRADUACIÓ] Cap regla es deriva d'una taula incompleta.** Talla del run sense
  valor = fila incompleta = **BLOQUEIG de creació (400)**, mai derivació amb deltes parcials (un break
  perdut degradava a LINEAR en silenci). Normalització d'etiquetes: **pont únic `canonical_size_label`**;
  el prompt (`wizard_context` amb `size_run`) és **ajuda, mai garantia**. Deute: tres normalitzadors
  (`canonical_size_label` / `_norm` / `_norm_label`) → **convergir** (§5).
- **[PROVINENÇA] (llei nova, PENDENT d'implementar):** tot `GradingRuleSet` importat ha de guardar el
  **document d'origen + snapshot dels `values_by_size`** extrets i re-clavats. Un actiu de secret
  industrial ha de ser **auditable i regenerable contra la seva font**.

---

### MOTOR DE GRADUACIÓ — semàntica del SOSTRE (`increment_break=0`) · VERIFICAT 2026-07-24

Fet verificat empíricament contra `pom/services.py::_apply_rule` (branca canònica, la que s'activa
quan `increment_base` està poblat i `logica != 'STEP'`), executant el motor real sobre runs de prova.

**1. El motor SÍ suporta el sostre.** La línia clau és
`brk = float(rule.increment_break) if rule.increment_break is not None else ib`: distingeix **0** de
**None**. Amb `increment_break=0` explícit, tot pas a partir del break suma 0 → la mesura queda
**plana**. Amb `increment_break=None` no hi ha break i el pas és uniforme. Mesurat (base=100, ib=0.5,
run XS·S·M·L·XL·2XL·3XL, base S):

| `increment_break` | `talla_break_label` | XS | S | M | L | XL | 2XL | 3XL |
|---|---|---|---|---|---|---|---|---|
| `None` | 'M' | 99.5 | 100 | 100.5 | 101 | 101.5 | 102 | 102.5 |
| `0` | 'L' | 99.5 | 100 | **100.5** | 100.5 | 100.5 | 100.5 | 100.5 |
| `0` | 'M' | 99.5 | 100 | **100** | 100 | 100 | 100 | 100 |

**2. ⚠️ `talla_break_label` és la PRIMERA talla JA AFECTADA, no l'última que creix.**
El bucle fa `total += brk if j >= break_idx else ib`: el pas que **arriba** a la talla del break ja
usa `increment_break`.

> **Correcció d'una afirmació anterior (Agus, 2026-07-24).** L'especificació original deia que
> «pla a partir de M» s'escrivia `talla_break_label='M'`. **És incorrecte**: amb `'M'` la M val
> exactament el mateix que la base. La forma correcta, confirmada per l'Agus després de la
> verificació en viu del motor feta en aquesta sessió, és:
>
> | intenció | `talla_break_label` | `increment_break` |
> |---|---|---|
> | «creix fins a M, després pla» (base S) | **`'L'`** | `0` |
>
> Comprovat a la taula de dalt: amb `label='L'` → S=100, **M=100.5** (últim creixement),
> L=100.5 (pla). **Regla general: `talla_break_label` = la talla SEGÜENT a l'última que creix.**

⚠️ **Aquest off-by-one NO afecta el cas «canvi d'increment»**, només el cas «sostre». Quan el segon
valor no és 0 sinó un increment diferent (p.ex. talles compostes que creixen el doble), el label
**sí** que és la primera talla amb el nou increment, i això és el que es vol. Vegeu el STOP
retroactiu a `DIAGNOSI_CENS_TENANT_LOS_2026-07-24.md`.

**3. El break s'ancora per ETIQUETA contra el run del MODEL** (`size_run`), no contra el del ruleset.
Si l'etiqueta del break no és al run del model, `break_idx=None` i la regla degrada a **lineal pura,
en silenci**: un model amb run `XS·S·L·XL` i break `'M'` perd el sostre i segueix creixent. Mesurat.

---

## 5. Deutes i peces pròpies anotades (no ara)

- **Tolerància:** avui 2 valors; sempre simètrica ± → fusionar a 1 sola columna (p.ex. ±0.6). Sprint POMs.
- **Gating de `resolve`** = `IsAuthenticated` → revisar al grup de govern/gating.
- **Nomenclatura editable per-model:** autoria de nom a nivell model (avui `nom_fitxa` és per-POM
  compartit) → peça pròpia post-unificació.
- **Combo/multipeça:** `GarmentSet`, 2 graelles per peça identificades (presa simultània) → peça pròpia.
- **i18n nous idiomes** (fr/it/pt/de): infra-readiness fixa (un cop) vs traducció lineal; desacoblar
  "fer N-idiomes-ready" de "publicar traduccions"; eix car amagat = dades de domini (noms POM a BD).

---

## 6. Històric (decisions completades, per traçabilitat)

- *(buit — s'hi baixaran les decisions vives en completar-se)*
