# DIAGNOSI — Cascada del wizard de grading: no filtra per target + grup NEWBORN absent

> Staging · `fhort` · dev. Data: 2026-07-19. **Patró A (read-only). STOP al gate d'Agus — cap
> implementació.** Abast ampliat a transversal (§4-§6) per addendum d'Agus del 19/07.
> Símptomes reportats amb captura: target «Nadó nena» triat i (a) passos 3-5 mostren el catàleg
> sencer, (b) el grup NEWBORN (Fase 1) no apareix al pas 3.

---

## §1 · Símptomes

Amb **target «Nadó nena»** (codi `BABY_GIRL`) seleccionat al wizard de Grading Rules:

- **(a)** Els passos **3 (Grup)**, **4 (Família)** i **5 (Item)** mostren el **catàleg SENCER**
  (p.ex. items «Shirt Man Regular», família «Blusa») en lloc de filtrar en cascada pel target.
- **(b)** El grup **NEWBORN** (creat a Fase 1, amb un `GarmentType` i 9 items) **no apareix** al pas 3.

La superfície de la captura és el component compartit
[`AxesSelector.jsx`](../../frontend/src/components/grading/AxesSelector.jsx), muntat a la pàgina
Grading Rules ([`GradingRuleSets.jsx:211`](../../frontend/src/pages/GradingRuleSets.jsx#L211)).

---

## §2 · Causa exacta

### (a) La cascada NO propaga el target avall del grup

Un cop triat el grup, família i item es carreguen **només per grup/família**, sense cap
paràmetre de target:

| Pas | Codi | Font de la llista | Filtre aplicat |
|---|---|---|---|
| 3 Grup | [`AxesSelector.jsx:112`](../../frontend/src/components/grading/AxesSelector.jsx#L112) | constant **hardcoded** `GARMENT_GROUPS` ([`gradingAxes.js:46`](../../frontend/src/components/grading/gradingAxes.js#L46)) | cap (llista fixa) |
| 4 Família | [`AxesSelector.jsx:35`](../../frontend/src/components/grading/AxesSelector.jsx#L35) | `garmentTypes.list({ grup, actiu })` | **només grup** |
| 5 Item | [`AxesSelector.jsx:45`](../../frontend/src/components/grading/AxesSelector.jsx#L45) | `garmentTypeItems.list({ garment_type })` | **només família** |

El `target` triat al pas 1 només alimenta el **matching de rule-sets**
(`availableTargetCodes`/`matchingRuleSets`, [`gradingAxes.js:98,128`](../../frontend/src/components/grading/gradingAxes.js#L98))
i el filtre de construccions/fits — **mai** el catàleg de peça. Per això amb `BABY_GIRL`
apareixen famílies i items de qualsevol demografia.

### (b) El pas 3 pinta una constant, no la BD

El pas 3 itera `GARMENT_GROUPS`, una **llista fixa de 7 grups** de peça
(TOPS/BOTTOMS/DRESSES/OUTERWEAR/UNDERWEAR/SWIMWEAR/ACCESSORIES). El grup **NEWBORN viu a la BD**
(model [`GarmentGroup`, `pom/models.py:375`](../../backend/fhort/pom/models.py#L375)) i **ja té
endpoint** `/api/v1/garment-groups/`
([`GarmentGroupViewSet`, `pom/views.py:99`](../../backend/fhort/pom/views.py#L99)). GradingRuleSets
fins i tot el crida ([`GradingRuleSets.jsx:75`](../../frontend/src/pages/GradingRuleSets.jsx#L75))
**però només per construir un map codi→id de matching**, no per renderitzar el pas 3. Un grup
creat a BD després del hardcode **mai apareix**.

> ⚠️ **Nota conceptual a validar amb Agus:** «Nadó nena» és un **target** (`BABY_GIRL`,
> [`gradingAxes.js:14`](../../frontend/src/components/grading/gradingAxes.js#L14)), mentre NEWBORN
> s'ha creat com a **grup de peça** (al costat de TOPS). Semànticament NEWBORN és un eix
> demogràfic, no de categoria de peça. Cal confirmar si Fase 1 volia un grup de peça nou o si el
> concepte hauria d'anar per l'eix target/size-library (com la resta de baby/kids).

### La relació item↔target SÍ existeix al backend (i està servida)

- `GarmentType.targets_recomanats` (M2M) — [`pom/models.py:413`](../../backend/fhort/pom/models.py#L413).
- `GarmentTypeItem` (a `tasks`) **no** té target propi; l'hereta via la seva família
  ([`tasks/models.py:286`](../../backend/fhort/tasks/models.py#L286)). Filtrar items per target =
  filtrar per família (que ja porta el target).
- Ja existeix endpoint **`garment-types-by-target/`**
  ([`pom/s2_views.py:379`](../../backend/fhort/pom/s2_views.py#L379), filtra per
  `targets_recomanats__codi`) — però **cap punt del frontend el crida** (0 hits al grep).

**Conclusió §2:** les dades hi són; el defecte és pur frontend (la cascada no passa el target al
catàleg) + un hardcode (el pas 3 no llegeix la BD de grups).

---

## §3 · Dimensionat mínim de l'arreglada aïllada (es refina a §6)

- **(b) incloure NEWBORN:** substituir la constant al pas 3 per `garmentGroups.list({actiu})`.
  **Mida S.** Risc: el matching codi↔id de GradingRuleSets ja usa aquest endpoint — verificar
  que el vocabulari de matching (que segueix sent `GARMENT_GROUPS`) no divergeixi de la BD.
- **(a) cascada per target:** encadenar el target al pas 4/5. El backend ja té la M2M i
  l'endpoint `garment-types-by-target/`; falta afegir el filtre de target a `garmentTypes.list`
  (o cridar l'endpoint dedicat) i propagar-lo. **Mida S-M** si es fa només a `AxesSelector`;
  **M-L** si s'unifica a totes les pantalles (vegeu §4-§6).

---

## §4 · Inventari transversal de punts d'ús

Vuit superfícies toquen algun tram de l'eix `target · construcció/fit · grup · família · item`.
El **catàleg de peça (grup/família/item) NO es filtra per target en CAP d'elles.**

| # | Superfície / fitxer | Eixos que ofereix | Component | Endpoints del catàleg | Filtra catàleg per target? |
|---|---|---|---|---|---|
| 1 | **Grading Rules** «Nou run de client» · [`GradingRuleSets.jsx`](../../frontend/src/pages/GradingRuleSets.jsx) | target·constr·fit·grup·família·item | **`AxesSelector`** (compartit) | `garment-groups/` (només map id↔codi) + interns d'AxesSelector | **No** |
| 2 | **Editor d'item · Pas 1 Context** · [`ItemAuthoring.jsx`](../../frontend/src/pages/ItemAuthoring.jsx) | idem (5 passos) + `RuleSetPicker` | **`AxesSelector`** + `RuleSetPicker` (compartits) | interns d'AxesSelector | **No** |
| 3 | **Wizard de Model** «Nou model» · [`ModelWizard.jsx`](../../frontend/src/pages/ModelWizard.jsx) | target · família·item · constr · fit · ruleset (grup **derivat** de l'item) | **`GarmentTypeSelector`** (fam/item) + còpia pròpia de TARGETS/CONSTRUCTIONS | `garmentTypes.list`/`garmentTypeItems.list` via GarmentTypeSelector | **No** (target només filtra SizeSystems, [`ModelWizard.jsx:163`](../../frontend/src/pages/ModelWizard.jsx#L163)) |
| 4 | **Garment Types** (catàleg) · [`GarmentTypes.jsx`](../../frontend/src/pages/GarmentTypes.jsx) | grup→família→item | `GroupPills` (compartit); grup del modal = **text lliure** | `garmentTypes.list` (catàleg sencer) | sense eix target |
| 5 | **Selector peça reusable** · [`GarmentTypeSelector.jsx`](../../frontend/src/components/GarmentTypeSelector/GarmentTypeSelector.jsx) | grup→família→item | `GroupPills` (compartit) | `garmentTypes.list({grup})` + `garmentTypeItems.list({garment_type})` | **No** (motor comú de #3 i #7) |
| 6 | **«Nou run» size wizard** · [`SizeMapSetup.jsx`](../../frontend/src/pages/SizeMapSetup.jsx) + `SizeAuthoringDrawer` | target·constr·fit + **àmbit** grup/família/item (`applies_to`) | **`ScopeSelector`** (compartit); target/constr/fit d'API `sizeMap.lookups()` | `garmentTypes.list({grup})` via ScopeSelector | **No** (target del wizard NO s'aplica a l'àmbit) |
| 7 | **POMBrowser / assignar POMs** · [`POMBrowser.jsx`](../../frontend/src/components/POMBrowser/POMBrowser.jsx) | grup→família→item | `GarmentTypeSelector` (compartit) | via GarmentTypeSelector + `garment-pom-maps/` | **No** |
| 8 | **SizingProfileSelector** · [`SizingProfileSelector.jsx`](../../frontend/src/components/SizingProfileSelector.jsx) | target·constr·fit (sense catàleg) | còpia pròpia (`TARGET_ORDER` + API) | — (sizing profiles) | filtra **profiles** per target, no catàleg |

**Sense cascada (consumidors de catàleg sencer):** `AssetNavigator`, `ProductDetail`,
`BulkImportWizard`, `ImportWizard` (deriva `target` del model pare, [`ImportWizard.jsx:182`](../../frontend/src/components/ImportWizard/ImportWizard.jsx#L182), sense selector),
`GarmentPOMMapEditor`, `TallerPatro`, `ModelPomList`, `POMPicker`.
**`frontend-backoffice/`: zero ús de la cascada.**

---

## §5 · Font de veritat i divergències

**Sí que hi ha mòdul comú:** [`gradingAxes.js`](../../frontend/src/components/grading/gradingAxes.js)
(vocabulari `TARGETS/CONSTRUCTIONS/FITS/GARMENT_GROUPS` + helpers de matching) i els components
`AxesSelector` · `ScopeSelector` · `GroupPills` · `GarmentTypeSelector` · `RuleSetPicker`. Però
la cobertura és **parcial i divergent**:

**Divergència A — filtratge per target del catàleg:** **cap superfície** filtra grup/família/item
pel target. Tots carreguen per grup o catàleg sencer. La capacitat backend
(`garment-types-by-target/`) **no es crida enlloc**. El cas més agut és el **Wizard de Model
(#3)**: l'usuari tria target i tot seguit veu tot el catàleg (pot triar target=MAN i famílies
només-WOMAN).

**Divergència B — vocabulari compartit vs còpies pròpies:**
- **Còpies divergents:** `ModelWizard.jsx:23-30` (**`TARGETS` de 13 codes + `CONSTRUCTIONS`
  hardcoded propis**, no importa `gradingAxes` — risc de deriva del vocabulari canònic);
  `SizingProfileSelector` (`TARGET_ORDER` propi); `SizeMapSetup` (target/constr/fit d'API
  `sizeMap.lookups()`); `GarmentTypes.jsx:336` (grup com a **text lliure**, salta `GARMENT_GROUPS`).
- **Taules privades funcionals:** `GradingRuleSets.jsx:20-28` (`GROUP_POM_CATEGORIES`).

**Divergència C — grups: constant vs BD.** El vocabulari `GARMENT_GROUPS` (7 grups hardcoded) i
la taula BD `GarmentGroup` **poden divergir** (NEWBORN n'és la prova: existeix a BD, no a la
constant). Avui conviuen tres representacions del «grup»: la constant, l'endpoint
`garment-groups/`, i el `GarmentType.grup` (CharField de text lliure).

---

## §6 · Proposta unificada (dissenyada, no implementada)

**Regla d'Agus:** cap correcció que arregli una pantalla i deixi les altres divergents. Per tant
la solució és **una font compartida** que serveixi la cascada filtrada per target i inclogui tots
els grups actius, consumida per tots els punts d'ús.

### Peça 1 — Grups des de la BD (tanca (b) a tot arreu)
Fer que **`GroupPills`/`gradingAxes` serveixin els grups actius de `garment-groups/`** (amb la
constant `GARMENT_GROUPS` només com a *fallback*/ordre). Així NEWBORN i qualsevol grup futur
apareixen a #1, #2, #4, #5, #6, #7 alhora. **Mida S-M.**
_Prerequisit conceptual:_ resoldre la nota de §2 (NEWBORN ha de ser grup de peça?). Si NO ho ha
de ser, la peça és netejar Fase 1, no exposar-lo.

### Peça 2 — Catàleg filtrable per target (tanca (a) a tot arreu)
Un **únic canal de dades** filtrable per target, consumit per `AxesSelector`, `GarmentTypeSelector`
i `ScopeSelector`:
- **Backend:** afegir `targets_recomanats` al `filterset_fields` de
  [`GarmentTypeViewSet`](../../backend/fhort/pom/views.py#L99) (o un filtre per codi de target),
  de manera que `garmentTypes.list({ grup, actiu, target })` filtri famílies per la M2M. Items
  hereten (filtrar per família ja triada n'hi ha prou). L'endpoint dedicat `garment-types-by-target/`
  queda **redundant** (candidat a jubilar). **Mida S.**
- **Frontend:** els tres components accepten una prop `target` opcional i la passen al `list`.
  On el target sigui obligatori (wizards) es filtra; on no n'hi hagi (Garment Types #4, catàleg
  pur) es manté el comportament ample. **Mida M.**

### Peça 3 — Un sol vocabulari d'eixos
Fer que `ModelWizard` i `SizingProfileSelector` **consumeixin `gradingAxes`** en lloc de les
seves còpies de `TARGETS/CONSTRUCTIONS`. Elimina la deriva (Divergència B). **Mida S.**

### Unificar vs pedaçar
- **Pedaçar** (tocar només `AxesSelector` per al cas de la captura): arregla #1 i #2, deixa #3
  (el més agut), #5, #6, #7 divergents. **Viola la regla d'Agus.** Descartat com a solució final.
- **Unificar** (peces 1-3): un canal de dades + un vocabulari, tocant els 3 components
  compartits (`AxesSelector`, `GarmentTypeSelector`, `ScopeSelector`) i el backend un cop.
  **Mida global M-L.** Punts d'ús a tocar: #1, #2, #3, #4(grups), #5, #6, #7.

### Riscos de regressió per pantalla
- **#3 ModelWizard:** el grup és **derivat de l'item** (`family.grup`), no triat. Si el catàleg
  es filtra per target, cal garantir que el target triat i l'item derivat siguin coherents (avui
  pot triar-se un item de target contradictori). Millora funcional però canvia el flux → validar UX.
- **#4 Garment Types:** és el CRUD del catàleg; **no ha de filtrar-se per target** (s'hi
  administra tot). El grup de text lliure del modal ha de convergir a `garment-groups/` amb cura
  (dades existents amb `grup` no-canònic).
- **#6 «Nou run»:** l'àmbit `applies_to` és **multi-node acumulatiu** (llei ÀMBIT); filtrar-lo per
  target pot amagar nodes que un contenidor multi-target vol incloure — decidir si el filtre és
  dur o només suggeriment.
- **#1/#2:** el matching codi↔id de grup i els helpers `scopeApplies` depenen del vocabulari;
  passar de constant a BD exigeix que `garmentGroupCodiById` cobreixi els grups nous.
- **Transversal:** `GarmentTypeSelector` és el motor de #3 i #7 alhora — un canvi hi impacta els dos.

**SORTIDA:** aquesta diagnosi. **STOP al gate d'Agus.** Cap línia de codi tocada.
