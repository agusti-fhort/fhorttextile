# DIAGNOSI — Resolució de codis sense match al run de client: matching vs creació de POM

**Data:** 2026-07-08 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
**Equip:** 1 sessió orquestra · investigació a BD (fhort) + lectura de codi + 1 agent read-only (frontend POMBrowser). Cap escriptura de codi, cap migració, cap restart.
**Substrat:** `DIAGNOSI_RUN_CLIENT_VINCULACIO_2026-07-08.md` (vigent, BLOC 7) · cas real BERG.pdf.
**Objectiu:** decidir el camí de resolució dels codis sense match (cercar existent vs crear tenant POM) **sense contaminar el catàleg**.

> Convenció: `fitxer:línia` relatiu a l'arrel del repo. **"NO EXISTEIX" = confirmat absent al codi** (no especulat).
> Rutes backend relatives a `backend/`. Cas: codis de document J.2 / H.6 / H.16 / G.3.

---

## 0. Resum executiu (director)

1. **El problema és MATCHING, no absència de POM.** Els quatre codis del cas tenen equivalent
   canònic JA present al catàleg fhort (BLOC 1): Armhole → `AH DEP`/`AH CIRC`; Cuff opening →
   `SL OP`; Sleeve length → `SL`/`SL UA`/`SL CB`; Shoulder → `SH`/`SS SLOPE`/`SOW`. Crear-los
   seria **duplicar** mesures que ja existeixen.
2. **Causa arrel de "H.6 → Sleeve muscle": la Strategy 0 (root-prefix) s'executa ABANS del
   match per descripció** i col·lapsa `H.6`/`H.16` a l'arrel de lletres `H`; i `codi_client='H'`
   (id=423) = "SLEEVE MUSCLE (1/2)". La descripció ("Armhole"/"Cuff opening") que resoldria bé
   **mai s'arriba a llegir** (`extraction_views.py:541-549` guanya `:571-591`).
3. **La nomenclatura `LLETRA.NÚMERO` del document és una AGRUPACIÓ, no un codi de mesura;** però
   `find_pom_master` la trosseja i la fa xocar amb POMMaster d'una sola lletra. `G.3`/`J.2` es
   salven de l'arrel només perquè no hi ha POMMaster `G` ni `J` (cauen a descripció); `H.*` no.
4. **La creació de POM viu FRAGMENTADA en 3 camins amb dedup i marcatge incoherents** (BLOC 3/4):
   `POMMasterViewSet` (CRUD genèric, `IsAuthenticated`, **cap dedup, cap marca**),
   `create_tenant_pom_view` (dedup per `codi_client`, **cap marca** — ignora `pendent_revisio`),
   i l'import (`get_or_create` amb `pendent_revisio=True`+`origen_import`). **Cap dedup per NOM ni
   per mesura canònica** → duplicació de catàleg trivial.
5. **`POMMaster` NO té `is_system`/`read_only`** (confirmat el veredicte del substrat) però **SÍ té
   `pendent_revisio` + `origen_import`** (`pom/models.py:169-180`): ja existeix el vocabulari per
   marcar origen-tenant i reconciliar després. Falta **usar-lo consistentment**.
6. **El wizard només enllaça (`<select>` a existents); la creació de tenant POM NO és accessible
   des del run-client** (BLOC 5). El camí `crear-tenant` existeix però penja de l'editor de mesures
   del model (`EditableTable.jsx:452`), i el POMBrowser ASSIGN de `/poms` és **assign-only**.

**Recomanació de rumb (💡, a validar):** **matching-fix PRIMER** (desbloqueja els 4 codis del cas
sense escriure res al catàleg); la creació és un camí **secundari i governat**, només per a codis
genuïnament nous, canalitzat per la cua `pendents_vincular` cap a una superfície d'autoria única.

---

## BLOC 1 — Existeix el POM canònic? (matching vs absència) [Q1]

Consulta a BD (fhort, read-only). **Tots quatre tenen candidat canònic ja al catàleg:**

| Codi doc (cas) | Mesura | Candidats POMMaster fhort (codi · nom · global) | POMGlobal (SHARED) |
|---|---|---|---|
| **J.2** Shoulder move fwd | espatlla | `SH` Shoulder width (g94) · `SS SLOPE` Shoulder slope/pitch (g104) · `SOW` Shoulder opening width (g170) · `AC SH` Across shoulder back (g95) | POM-005/014/019/006/122 |
| **H.6** Armhole | sisa | `AH DEP` Armhole depth (g101) · `AH CIRC` Armhole circumference (g102) | POM-012/013 |
| **H.16** Cuff opening | canó | `SL OP` Sleeve opening / Cuff width (g123) | POM-025 |
| **G.3** Sleeve short length | màniga | `SL` Sleeve length (g118) · `SL UA` underarm (g119) · `SL CB` (g120) | POM-020/021/022 |

- Els candidats surten de `POMMaster.objects.filter(nom_client__icontains=…)` a fhort (168 POMMaster
  actius; 43 amb `pom_global=NULL`; 28 `pendent_revisio=True`).
- **"Shoulder move fwd" (J.2) és l'únic no-trivial:** "move forward" és un ajust de construcció
  (pitch/forward shoulder), no una amplada. Candidat més proper = `SS SLOPE` (Shoulder slope/pitch)
  o un POM de forward-shoulder que **PENDENT DE VERIFICAR** si existeix (cap `nom_client` conté
  "forward" al llistat retornat). Els altres tres són match net.

**Veredicte BLOC 1: MATCHING (no absència).** ≥3 de 4 codis tenen canònic exacte al catàleg; crear-los
contaminaria. El fix prioritari és de matching. (J.2 pot ser l'excepció que justifiqui el camí de
creació — a validar amb la Montse quina mesura és "move fwd".)

---

## BLOC 2 — Com casa `find_pom_master` i per què H.6 → Sleeve muscle [Q2]

`find_pom_master(code, description)` ([extraction_views.py:525-604](../../backend/fhort/models_app/extraction_views.py#L525))
**NO usa embeddings ni fuzzy real**; és una cascada determinista de 6 estratègies:

| Ordre | Estratègia | Clau | Confiança | Línia |
|---|---|---|---|---|
| 1 | exacte `codi_client__iexact` | codi | HIGH | `:536-539` |
| **0** | **root de lletres inicials** `^([A-Za-z]+)` | codi | **MEDIUM** | **`:543-549`** |
| 2 | taula sinònims `_POM_SYNONYMS` | descripció | HIGH | `:557-569` |
| 3 | `nom_client` exacte/conté | descripció | HIGH/MEDIUM | `:571-578` |
| 4 | `POMGlobal.nom_en`/abbrev | descripció/codi | HIGH/MEDIUM | `:580-593` |
| 5 | numèric pur → lining | codi | MEDIUM | `:595-602` |

- **La causa arrel:** l'ordre. L'estratègia **root-prefix (0) va abans de tota la resolució per
  descripció (2/3/4)**. Per `H.6`: exacte falla; `^([A-Za-z]+)` → `H`; `codi_client='H'` existeix
  (id=423, "SLEEVE MUSCLE (1/2)", `pom_global=NULL`) → **retorna Sleeve muscle, MEDIUM**, i la
  descripció "Armhole" **no es llegeix mai**. `H.16` (Cuff opening) cau **igual** a `H` → Sleeve muscle.
- **`G.3`/`J.2` escapen de l'arrel per casualitat:** no hi ha POMMaster `G` ni `J` → l'estratègia 0
  no retorna → cauen a descripció (3/4) i **poden** resoldre (Sleeve length / Shoulder). L'error
  només mossega quan l'arrel d'una lletra coincideix amb un POMMaster real (cas `H`).
- **La taula de sinònims és minsa:** `_POM_SYNONYMS` té **23 entrades** i **cap** per shoulder /
  armhole / cuff / sleeve-move (només `'front armhole curve'`, a més **duplicada** com a clau al
  literal, `:495+`). No cobreix el cas.
- **Diferència paste vs fitxer:** el paste no porta descripció (`parseTable` retorna només
  `{pom_codi_client, valors}`, [SizeMapSetup.jsx:76](../../frontend/src/pages/SizeMapSetup.jsx#L76)),
  així que al paste el match és **només per codi** → `H.*` cau sempre a l'arrel. Al fitxer la
  descripció hi és (`size_map_views.py:435`) però l'ordre la deixa inservible per `H.*`.

**Veredicte BLOC 2: cal X (matching-fix).** El detector és determinista i sense llindar; el marge de
millora és **reordenar/condicionar l'estratègia 0** (no rootejar quan el codi és `LLETRA.NÚMERO`, o
provar descripció abans i acceptar el root només com a últim recurs) i **enriquir sinònims**. 💡 Fix
mínim proposat a §Veredicte final.

---

## BLOC 3 — `create_tenant_pom_view`: què crea, gating, origen [Q3]

`POST /api/v1/poms/crear-tenant/` ([wizard_views.py:334-372](../../backend/fhort/pom/wizard_views.py#L334),
ruta [urls.py:42](../../backend/fhort/pom/urls.py#L42)):

- **Cos:** `codi_client`, `nom_client`, `categoria_id`, `notes` (opt). `descripcio` es documenta al
  docstring però **NO s'usa** (`:360` només llegeix `notes`).
- **Crea:** `POMMaster(codi_client, nom_client, categoria_id, notes, actiu=True)` (`:356-362`).
  **NO** posa `pom_global` (queda `NULL`), **NO** posa `pendent_revisio` (queda `False` per defecte),
  **NO** posa `origen_import`. → El POM neix **sense marca d'origen-tenant ni de revisió**.
- **Gating:** `@permission_classes([IsAuthenticated])` (`:333`) — **NO CONFIGURE**. Qualsevol usuari
  autenticat pot crear.
- **`is_system`/`read_only` a POMMaster: NO EXISTEIX** (confirmat, llista completa de camps a
  [pom/models.py:144-180](../../backend/fhort/pom/models.py#L144)). El que SÍ existeix per distingir
  origen: **`pendent_revisio`** (bool, "creat automàticament des d'importació, requereix revisió")
  i **`origen_import`** (string, referència del model/fitxa d'origen) — `:169-180`.
- **Gap de marca:** el frontend que crida aquest endpoint (`EditableTable.jsx:452`) envia
  `pendent_revisio:true`, però el backend **l'ignora** (no és als camps llegits) → la marca es perd.

**Veredicte BLOC 3: cal X (governança).** L'endpoint crea POM **sense pom_global, sense marca i amb
gating dèbil**. El vocabulari per marcar origen ja existeix (`pendent_revisio`+`origen_import`); no
s'aplica en aquest camí.

---

## BLOC 4 — Risc de duplicació: unicitat a POMMaster [Q4]

- **`POMMaster` NO té unicitat de BD** sobre `codi_client` ni `nom_client`: la `Meta` només defineix
  `verbose_name` ([pom/models.py:182-184](../../backend/fhort/pom/models.py#L182)). L'únic
  `unique_together` proper (migració `0012:35`) és de **`ClientMesuraPerfil`**, no de POMMaster.
- **Tres camins de creació, dedup incoherent i mai per nom:**

| Camí | Fitxer:línia | Gating | Dedup | Marca origen |
|---|---|---|---|---|
| `POMMasterViewSet.create` (`POST /api/v1/poms/`) | [views.py:44-53](../../backend/fhort/pom/views.py#L44) | `IsAuthenticated` | **CAP** | cap |
| `create_tenant_pom_view` (`/poms/crear-tenant/`) | wizard_views.py:353 | `IsAuthenticated` | `filter(codi_client=code)` (case-sensitive, app-level) | cap (backend) |
| import (`get_or_create`) | extraction_views.py:948 | (flux import) | `(pom_global=NULL, codi_client)` | `pendent_revisio`+`origen_import` ✓ |

- **`POMMasterViewSet` és un `ModelViewSet` complet gated només `IsAuthenticated`, SENSE
  `get_permissions` per exigir CONFIGURE a l'escriptura** — a diferència de `SizeSystemViewSet`
  (`views.py:65-68`) i `GarmentTypeViewSet` (`:102`), que sí exigeixen `_ConfigureWrite`. → Forat de
  governança: el catàleg de POMs és escrivible per CRUD genèric sense gate de configuració.
- **Cap camí dedup per NOM ni per mesura canònica.** Crear "Armhole" amb codi `H.6` i un altre
  "Armhole" amb codi `AH2` produeix **dos** POMMaster "Armhole". I crear els codis del cas seria
  duplicar mesures que **ja existeixen canònicament** (BLOC 1) sota un altre `codi_client`.

**Veredicte BLOC 4: cal X (dedup + gating).** Zero unicitat de BD; dedup app-level només per codi i
només en un dels tres camins; escriptura de catàleg sense CONFIGURE al ViewSet genèric.

---

## BLOC 5 — Lligam amb POMBrowser ASSIGN (/poms): on ha de viure la creació [Q5]

Facts del frontend (agent read-only, àncores a `frontend/src`):

- **`/poms`** = `pages/POMs.jsx` (route `App.jsx:261`): 2 pestanyes — **Browser** →
  `<POMBrowser mode="assign" />` (`POMs.jsx:45`) i **Catalogue** → `<POMCatalogue />` (`:46`).
- **POMBrowser ASSIGN = assign-only:** trieu família → ITEM i gestioneu la pertinença de POMs de
  l'item via `garment-pom-maps/` (`POMBrowser.jsx:158-173`). **Cap creació de POM** aquí. `MOCK_POMS`
  **NO EXISTEIX** (confirmat). `POMCatalogue` és **read-only** ("ni desar, ni crear, ni esborrar",
  `POMCatalogue.jsx:13`).
- **La creació de tenant POM (`crear-tenant`) SÍ existeix al frontend, però penja de l'editor de
  mesures del MODEL** (`EditableTable.jsx:452`, muntat a `MeasuresEntryPanel.jsx:317`), **no de
  `/poms` ni del wizard.** `poms.crearTenant` és a `endpoints.js:93`.
- **El wizard run-client només enllaça:** `<select>` a `catalegPoms` (de `poms.list`,
  `SizeMapSetup.jsx:275`, render `:706-714`). **Cap afordança de crear POM** (confirmat).

**Veredicte BLOC 5: decisió de producte.** Avui NO hi ha una **casa d'autoria de catàleg** única: la
creació viu incrustada a l'editor de mesures del model; el POMBrowser (que semànticament seria la casa)
és assign-only. El wizard, correctament, no crea. → La cua `pendents_vincular` (ja persistida, sprint
run-client) és el pont natural cap a on hauria de viure la resolució.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al CTO)

| # | Element | Estat | Evidència |
|---|---|---|---|
| A | POM canònic per als 4 codis del cas | **EXISTEIX** (≥3/4 net) | BLOC 1 (BD) |
| B | Matching per descripció abans del root-prefix | **DIFERENT** (ordre invertit) | `extraction_views.py:541-591` |
| C | `POMMaster.is_system` / `read_only` | **FALTA** (NO EXISTEIX) | `pom/models.py:144-180` |
| D | Marca origen-tenant (`pendent_revisio`+`origen_import`) | **EXISTEIX** (però no s'aplica a `crear-tenant`) | `models.py:169-180` · `wizard_views.py:356` |
| E | Unicitat BD a POMMaster (codi/nom) | **FALTA** | `models.py:182-184` |
| F | Dedup per nom / per mesura canònica | **FALTA** (cap camí) | BLOC 4 |
| G | Gating CONFIGURE a l'escriptura de catàleg | **FALTA** al `POMMasterViewSet` + `crear-tenant` | `views.py:44-53` · `wizard_views.py:333` |
| H | Creació de POM des del wizard run-client | **NO EXISTEIX** (només `<select>`) | `SizeMapSetup.jsx:706-714` |
| I | Casa d'autoria única de catàleg | **DIFERENT** (creació a EditableTable, no a /poms) | BLOC 5 |

---

## VEREDICTE FINAL — matching-fix vs creació (💡 PROPOSTA, a validar; decisions humanes)

### 1. Prioritat: MATCHING-FIX (desbloqueja el cas sense tocar catàleg)
💡 **PROPOSTA (a validar)** — canvis mínims a `find_pom_master`, cap escriptura de dades:
- **(a) Condicionar/retardar l'estratègia 0 (root-prefix):** quan el codi és `LLETRA.NÚMERO`
  (nomenclatura d'AGRUPACIÓ), **no rootejar a la lletra**; provar primer la descripció (2/3/4) i
  acceptar el root només com a **últim recurs** i amb confiança **baixa** (LOW), no MEDIUM.
- **(b) Enriquir `_POM_SYNONYMS`** amb els termes del cas (armhole→AH, cuff opening→SL OP, sleeve
  length→SL, shoulder…) — taula curada, cost baix, HIGH-confidence.
- **(c) NO auto-vincular per sota d'un llindar:** un match root/contains ha d'anar a la **cua de
  no-resolts** (la superfície de paritat R7 ja el fa visible), no vincular-se en silenci a MEDIUM.
  Això converteix "H.6→Sleeve muscle silenciós" en "H.6 pendent, revisa'l".

### 2. Creació: camí SECUNDARI i GOVERNAT (només codis genuïnament nous, p.ex. potser J.2)
💡 **PROPOSTA (a validar)** — coherent amb la llei ja registrada (DECISIONS 2026-07-08: *no creació
de POM des del wizard; no-resolts = cua persistent*):
- **El wizard NO crea.** Els no-resolts van a `pendents_vincular` (ja implementat).
- **La resolució viu a una casa d'autoria única** — el candidat natural és **POMBrowser/Catalogue
  (`/poms`)**, avui assign-only: afegir-hi el camí de **crear tenant POM** (convergir amb el de
  `EditableTable`, no un tercer pedaç) que llegeixi la cua `pendents_vincular` del run.
- **Tota creació neix marcada** `pendent_revisio=True` + `origen_import=<token del run>` (arreglar el
  gap del BLOC 3: `crear-tenant` ha de persistir aquestes marques) → **reconciliable** després per la
  patronista (vincular a `pom_global` canònic o confirmar tenant-only).

### 3. Governança anti-contaminació (transversal)
💡 **PROPOSTA (a validar):**
- **Gating CONFIGURE** a l'escriptura del catàleg: `get_permissions` a `POMMasterViewSet` (write →
  `_ConfigureWrite`, com SizeSystem/GarmentType) i a `create_tenant_pom_view`.
- **Dedup abans de crear:** avisar si ja existeix un POMMaster amb `nom_client` equivalent o un
  `pom_global` que casa la mesura → **oferir vincular en comptes de crear** (evita el segon "Armhole").
- **Unicitat de BD** a `codi_client` (per tenant) — decisió a prendre (constraint dura vs avís), atès
  que avui 168 POMMaster conviuen sense ella.

### Decisions a elevar (CTO)
1. **Ordre matching:** acceptem retardar el root-prefix i baixar-lo a LOW/últim recurs? (desbloqueja `H.*`).
2. **Casa de creació:** convergim la creació de tenant POM a `/poms` (POMBrowser) llegint
   `pendents_vincular`, o mantenim la d'`EditableTable` i el wizard només hi enllaça?
3. **J.2 "Shoulder move fwd":** és una mesura nova real o un àlies d'un POM existent? (única possible
   justificació de creació al cas).
4. **Gating/unicitat:** tanquem el forat `POMMasterViewSet` (CONFIGURE) i afegim unicitat/dedup?

## Obert / dubtós
- **J.2 "move fwd":** no s'ha trobat cap POMMaster amb "forward" al `nom_client`; **PENDENT DE
  VERIFICAR** amb domini si és mesura nova o àlies (determina si el cas necessita gens de creació).
- **Camí paste sense descripció:** el paste no porta descripció (`parseTable`), així que el
  matching-fix per descripció **no ajuda el paste** — el paste dependrà de codi + sinònims. Si el
  run-client per paste ha de resoldre bé, cal decidir si s'hi captura descripció.
- No s'ha auditat si algun altre consumidor de `find_pom_master` (import de fitxa, `:700`/`:847`)
  depèn del comportament actual del root-prefix — **verificar radi** abans de reordenar.
