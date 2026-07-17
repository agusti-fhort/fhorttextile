# DIAGNOSI — Àmbit d'aplicabilitat del contenidor de grading de client (multi-node + multi-target)

Data: **2026-07-17** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`, tenant `fhort`.
Abast: repensar la identitat/unicitat del `GradingRuleSet` de client sota un ÀMBIT multi-node (grup→família→item)
i multi-target; higiene d'entrada de «Nou run de client»; estendre la cascada de Grading Rules a família→item.
**Toca una migració ja a PROD (0039) → diagnosi obligatòria abans de decidir.**

> Convenció: `fitxer:línia` = fet verificat. `NO EXISTEIX` = confirmat absent (no especulat).
> `💡 PROPOSTA (a validar)` = disseny per al GATE; les decisions són humanes (Patró C).

---

## Resum executiu (per desbloquejar el GATE)

1. **Multi-TARGET ja està modelat**: `GradingRuleSet.targets` M2M existeix i està poblat (4 rulesets ja són
   multi-target a staging). La LLEI multi-target **no necessita migració** — només cablatge d'UI/creació.
   (`pom/models.py` M2M `targets`; el `target` FK singular és legacy.)
2. **Multi-NODE és el que falta**: avui la identitat del contenidor és **un item únic** (`garment_type_item` FK)
   + constraint parcial `uniq_client_container_identity` (customer, ss, **gti**, fit) — **migració 0039, JA A PROD**.
3. **Identitat i disponibilitat JA estan desacoblades avui**: la RECONCILIACIÓ (sembrar un model) casa per
   identitat exacta `cerca_contenidor_client(customer, ss, gti, fit)` (`grading_utils.py:493`); la DESCOBERTA
   (picker/cascada) casa per **`garment_group`**, mai per gti (`gradingAxes.js:69-72,129,144`). L'àmbit multi-node
   és fonamentalment una qüestió de DISPONIBILITAT — es pot afegir sense trencar la identitat.
4. **No hi ha entitat de node polimòrfica**: grup/família/item són tres models separats (§BLOC 2). Un àmbit
   multi-node es modela amb un through-model (3 FKs nul·lables + discriminador) o 3 M2M.
5. **La cascada de Grading Rules és un FORK inline** que s'atura al grup (`GradingRuleSets.jsx`), i el
   `garment_type_item` del model **NO s'exposa al serializer** — cal obrir-lo abans de matchar per família/item.
6. **«Nou run de client» té higiene d'entrada pobra** (text/textarea/selects, sense item, sense spinner) i la
   creació viu a Size Library, no a Grading Rules (§BLOC 4).

---

## BLOC 1 — IDENTITAT sota multi-node (A.1) · **el nucli del GATE**

### Estat actual (fet)
- **Migració 0039** (`pom/migrations/0039_gradingruleset_garment_type_item_and_more.py`, 2026-07-16, **A PROD**):
  `AddField garment_type_item` (FK→`tasks.GarmentTypeItem`, `db_constraint=False`, `SET_NULL`, null) +
  `AddConstraint uniq_client_container_identity` UNIQUE (customer, size_system, garment_type_item, fit_type)
  `WHERE origen='CLIENT_RUN'`.
- Model: `GradingRuleSet.garment_type_item` (`pom/models.py:548-551`), constraint (`pom/models.py:614-618`).
- Reconciliació: `cerca_contenidor_client(customer, ss, gti, fit)` (`grading_utils.py:493-509`) = **EL** contenidor
  per identitat completa; `.first()` (tolera múltiples). Creació size-map: `garment_type_item=rs_gti` (single)
  (`size_map_views.py:854`); pre-check 409 de duplicat via `cerca_contenidor_client` (`size_map_views.py:716-720`).
- **Cens staging**: 2 contenidors CLIENT_RUN — `115` (cust=7, ss=29, **gti=5**, REGULAR, gg=TOPS, WOMAN, 34 regles)
  i `124` (cust=7, ss=53, **gti=None**, REGULAR, 21 regles, incomplet). `116` NO EXISTEIX (mort). PROD: mateixa
  forma, cens **PENDENT DE VERIFICAR** (sense SSH; llegir del backup diari, [[ftt-prod-estat-via-dump]]).

### Opcions dimensionades (NO decidir — presentar al GATE)

**Opció (a) — M2M `applies_to` de nodes + gti únic conservat o retirat.**
- *Model*: through-model `RuleSetScope(rule_set, node_type∈{GROUP,TYPE,ITEM}, garment_group?, garment_type?, garment_type_item?)` (un node per fila, discriminador) — preferible a 3 M2M soltes perquè no hi ha base polimòrfica (§BLOC 2).
- *Constraint PROD*: la unicitat sobre gti **no pot** expressar un M2M. Cal decidir: conservar-la (gti passa a NULL als contenidors multi-node → NULLS DISTINCT la fa inofensiva, però no en guarda la unicitat) **o** retirar-la (`RemoveConstraint`, reversible, no destructiu).
- *Migració*: additiva (AddModel through + AddField M2M). El gti queda **deprecat en lloc** (no es fa drop de columna).
- *Reconciliació*: `cerca_contenidor_client` ha de passar a "contenidor l'`applies_to` del qual **inclou** el node del model (item → família → grup)". **AMBIGÜITAT NOVA**: diversos contenidors poden cobrir el mateix node a granularitats diferents → cal regla de precedència (item > família > grup) o guarda d'unicitat que ho impedeixi.
- *Reconciliació d'existents*: 115 (gti=5) → `applies_to=[ITEM:5]`; 124 (gti=None) → sense àmbit → watchpoint.

**Opció (b) — unicitat a (customer, ss, fit) + àmbit com a atribut no-únic.**
- *Model*: `RemoveConstraint uniq_client_container_identity` + `AddConstraint` UNIQUE (customer, ss, fit) `WHERE CLIENT_RUN`; àmbit = through/M2M no-únic.
- *Constraint PROD*: drop+add en **una** migració additiva (constraints, no columnes). **RISC**: les dades PROD han de SATISFER la nova unicitat abans d'aplicar-la — si dos contenidors comparteixen (customer, ss, fit) amb gti diferent, `migrate` **peta** (IntegrityError). Staging OK (115 i 124 tenen ss diferent). PROD: **auditar primer** al backup.
- *Semàntica*: **UN** contenidor per (customer, ss, fit), amb àmbit multi-node. Alinea amb "la precisió final l'aplica el tècnic en sembrar". **Cost**: dues peces del mateix (customer, ss, fit) amb graduació DIFERENT per POM **no poden coexistir** (col·lisionarien al mateix contenidor) — el GATE ho ha d'acceptar o rebutjar.
- *Reconciliació d'existents*: additiva; els existents ja compleixen si no col·lisionen.

**Opció (c) — desacoblar: gti = IDENTITAT (intacta), `applies_to` M2M = DISPONIBILITAT (nova).** `💡 PROPOSTA (a validar)` — **la de MENOR risc a PROD.**
- *Model*: **0039 i el gti INTACTES** (àncora d'identitat, back-compat). AFEGIR through/M2M `applies_to` **només per a disponibilitat** (matching).
- *Constraint PROD*: **NO es toca** (risc zero).
- *Migració*: **purament additiva** (AddModel through + M2M). Cap drop, cap canvi de constraint.
- *Reconciliació*: `cerca_contenidor_client` **sense canvis** (per gti). La sembra d'un model troba el contenidor per identitat exacta com avui.
- *Disponibilitat*: el picker/cascada mostra un contenidor si el node del model ∈ `applies_to` (grup/família/item). Un contenidor "de grup" té gti=NULL (no el guarda la constraint, correcte per ser ample); un "d'item" manté gti + `applies_to=[item]`.
- *Cost*: dos conceptes solapats (gti d'identitat + `applies_to` de disponibilitat). Respon a "repensar la unicitat": es manté sobre gti per als contenidors d'item; els amples (grup/família) relaxen la unicitat a posta.
- *Reconciliació d'existents*: 115 → `applies_to=[ITEM:5]` (derivat del gti); 124 → sense àmbit (watchpoint). Comanda idempotent dry-run (Fase C).

| Eix | (a) M2M + gti | (b) unicitat (cust,ss,fit) | (c) gti intacte + applies_to |
|---|---|---|---|
| Constraint 0039 PROD | conservar o retirar (decisió) | **drop+add** (risc IntegrityError) | **intacta** (risc 0) |
| Migració | additiva (+deprecació gti) | additiva (canvi de constraint) | **additiva pura** |
| Reconciliació (sembra) | **reescriure** (precedència node) | reescriure (per (cust,ss,fit)) | **sense canvis** |
| Semàntica | flexible; ambigüitat a resoldre | 1 contenidor/(cust,ss,fit) | identitat fina + disponibilitat ampla |
| Existents 115/124 | 115→[item5], 124→wp | additiu | 115→[item5], 124→wp |

**Veredicte BLOC 1:** cal decisió d'Agus (a/b/c). (c) és additiva pura i no toca PROD; (b) és la més neta si
s'accepta "1 contenidor per customer+ss+fit"; (a) és intermèdia amb ambigüitat de reconciliació a resoldre.

---

## BLOC 2 — Model de nodes (A.2)

- **NO existeix base polimòrfica** (`grep GenericForeignKey|ContentType` a `pom/models.py`+`tasks/models.py` = buit).
- Tres models: **`GarmentGroup`** (`pom/models.py:375`, `codi` unique) · **`GarmentType`** (`pom/models.py:392`,
  `grup` **CharField** :402 — **NO** FK a GarmentGroup; `garment_type_global` FK) · **`GarmentTypeItem`**
  (`tasks/models.py:286`, `garment_type` FK :290).
- **Enllaç grup↔família = per STRING** (`GarmentType.grup` == `GarmentGroup.codi`), no FK — feble (arrossegat de
  diagnosis prèvies). família↔item = FK real. Rellevant: la resolució d'àmbit (item→família→grup) depèn d'aquest
  string casant amb `GarmentGroup.codi`.
- `GradingRuleSet` ja té **`garment_group` FK** (`pom/models.py:533`) + **`garment_type_item` FK** (`:548`).

**Veredicte BLOC 2:** l'àmbit multi-node = through-model amb 3 FK nul·lables (group/type/item) + discriminador
(no hi ha polimorfisme reutilitzable). La fragilitat grup↔type (string) s'anota.

---

## BLOC 3 — Matching / disponibilitat (A.3)

- **Frontend matching = NOMÉS `garment_group`** (`gradingAxes.js:69-72` lenient, `:129`/`:144` strict). **CAP**
  referència a família/item — NO EXISTEIX. `RuleSetPicker` (`RuleSetPicker.jsx:27-34`) delega a aquestes funcions.
- El pas 4 del wizard (matcher strict que vaig cablar) casa per `garment_group` + `size_system`; un contenidor de
  grup TOPS ja apareix per a qualsevol model TOPS (115 casa per gg=TOPS, no per gti).
- Backend `GradingRuleSetViewSet.filterset_fields = ['actiu','garment_group','size_system','customer']`
  (`pom/views.py`) — sense gti/família.
- **TROBALLA TRANSVERSAL (serializer)**: `GradingRuleSetSerializer.Meta.fields` (`pom/serializers.py:231-242`)
  exposa `garment_group`/`_codi`/`_nom` però **NO `garment_type_item` ni `garment_type`**. El frontend **no rep**
  l'eix fi → estendre el matching a família/item exigeix **primer** exposar l'àmbit (`applies_to`) al serializer.

**Veredicte BLOC 3:** l'àmbit multi-node = afegir `applies_to` (grup/família/item) al matching. Un contenidor de
grup ha d'aparèixer per a tot el grup (ja passa via garment_group); baixar a família/item exigeix (1) exposar
l'àmbit al serializer i (2) estendre `matchingRuleSets*` amb el nou eix. Regla: **el node del model ∈ `applies_to`**.

---

## BLOC 4 — «Nou run de client»: higiene d'entrada + ubicació (A.4)

- El formulari és **`Wizard`** (export de `SizeMapSetup.jsx`), muntat via `SizeAuthoringDrawer`
  (`SizeAuthoringDrawer.jsx:2`) des de **`SizeLibrary.jsx:118`** (botó `:62-72`). `SizeMapSetup` (export default)
  **NO està routejat** (`App.jsx` sense ruta) → moure el botó = replicar el drawer a Grading Rules.
- Camps (tots al pas 1, `SizeMapSetup.jsx:467-514`):

  | Camp | Actual | fitxer:línia | Millora → objectiu |
  |---|---|---|---|
  | codi client | `<input>` text 3-car | :481-484 | **(1) `CustomerSelector`** (⚠ retorna `id`; payload usa `codi` :358 → mapeig) |
  | run de talles | `<textarea>` etiquetes | :485-488 | **(2) selector SizeSystem** (NO EXISTEIX cap `SizeSystemSelector`; `sizeMap.systems()` ja carregat) |
  | construcció | `<select>` | :493-498 | **(3) pills/botons** (`GroupPills`/patró) |
  | fit | `<select>` | :499-504 | **(3) pills/botons** |
  | garment | `<select>` únic; **sense `garment_type_item_id`** | :505-510 | **`GarmentTypeSelector`** (família→item) = l'ÀMBIT |
  | target(s) | `<select>` (pas1) + pills multi als perfils (:783-795) | :469-474 | ja pills (àmbit multi-target) |
  | base_size / base_unit | `<input>` / `<select>` | :489-491 / :475-480 | (2) SizeSystem |

- Payload `buildPayload` (`:335-376`) → `sizeMap.create` (`:402`); perfils envien target/construction/fit/**garment_type**
  (sense item, `:351-356`).
- **Pujada de fitxa**: `calcGradingFromFile`→`sizeMap.gradingPreviewFile` (`:306-318`, crida `:314`, lenta per IA).
  **Spinner NO EXISTEIX**: només `cursor:wait` + swap de text + `disabled` (`:619-624`) → millora (5).
- Components reutilitzables: `CustomerSelector` (`{value,onChange(id),allowCreate,onError}`), `GroupPills`
  (`{groups,value,onChange,allLabel}`), `GarmentTypeSelector` (`{onSelect({family,item}),selectedItemId}`).

**Veredicte BLOC 4:** les 5 millores són canvis de component acotats; l'àmbit (garment_type_item / multi-node) és
el camp nou de fons. `SizeSystemSelector` s'ha de crear (no existeix). El desajust `CustomerSelector` id↔codi
s'ha de reconciliar (mapeig o contracte backend).

---

## BLOC 5 — Cascada de Grading Rules (A.5)

- `GradingRuleSets.jsx` és un **FORK inline**: redefineix `TARGETS/CONSTRUCTIONS/FITS/GARMENT_GROUPS` (`:10-54`) i
  `matchingRuleSets`/`matchesGarmentGroup`/… (`:133-193`) — còpies de `gradingAxes.js`. **NO** importa
  `AxesSelector`/`RuleSetPicker`/`gradingAxes`. Cascada JSX `:277-363`, **s'atura al pas 3 (grup)** `:348-363`
  (pintat des de la constant local, no `GroupPills`). Sense estat família/item — NO EXISTEIX.
- **Cap botó de creació** a la pàgina (deliberadament: `GradingRuleSets.jsx:260` "Creació centralitzada a la Size
  Library; aquí només consulta/edita/esborra"). El POST existeix a `RuleSetModal.handleSubmit` (`:940-962`) però
  només s'obre via clone/edit. → moure-hi la creació de client crea un punt d'entrada nou.
- Extensió additiva: `AxesSelector` admet pas 4 (família) + pas 5 (item) via `StepSection` guardat + reset +
  `onChange` ampliat (`AxesSelector.jsx:27-93`); reutilitzar `GarmentTypeSelector`/`GroupPills` + endpoints
  `garmentTypes.list?grup=` / `garmentTypeItems.list?garment_type=`.
- **DEUTE de fork**: idealment unificar `GradingRuleSets.jsx` sobre `gradingAxes.js`+`AxesSelector` en fer-ho
  (evitar estendre la cascada a DUES còpies). Anotat (fora de l'scope mínim si el GATE no ho demana).

**Veredicte BLOC 5:** estendre a família→item és additiu però toca DUES cascades (el fork inline i
`AxesSelector`/`gradingAxes`); i requereix exposar l'àmbit al serializer (BLOC 3). Reutilitzables identificats.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT (per al GATE)

| Element | Estat | Nota |
|---|---|---|
| Multi-target (`targets` M2M) | **EXISTEIX** | poblat; cap migració; només UI |
| Identitat per gti únic + constraint 0039 | **EXISTEIX (PROD)** | el nucli a repensar (a/b/c) |
| Entitat de node polimòrfica | **NO EXISTEIX** | through-model 3 FK + discriminador |
| Àmbit `applies_to` multi-node | **FALTA** | model + migració additiva |
| Matching per família/item | **NO EXISTEIX** | avui només garment_group |
| `garment_type_item` al serializer | **FALTA** | gate backend previ al matching fi |
| `SizeSystemSelector` reutilitzable | **NO EXISTEIX** | crear (millora 2) |
| Spinner de pujada | **NO EXISTEIX** | millora 5 |
| Botó de creació a Grading Rules | **NO EXISTEIX** | moure des de Size Library |
| Reconciliació d'existents (115/124/PROD) | **FALTA** | comanda idempotent dry-run (Fase C) |
| Motor `generate_graded_specs` | **INTOCABLE** | l'àmbit no el toca |

---

## GATE (Agus ha de decidir, abans de Fase B)

1. **Model d'identitat/unicitat** sota àmbit multi-node: **(a)** M2M + gti, **(b)** unicitat (customer,ss,fit),
   **(c)** gti intacte + `applies_to` de disponibilitat. `💡 PROPOSTA`: **(c)** (additiva pura, risc 0 a PROD 0039);
   **(b)** si s'accepta "1 contenidor per customer+ss+fit".
2. **Estratègia de migració vs 0039**: (c) no la toca; (b) fa drop+add de constraint (auditar PROD abans); (a)
   conserva o retira la constraint.
3. **Reconciliació d'existents** (115 gti=5 → àmbit [item]; 124 sense àmbit → watchpoint; **PROD a auditar al backup**):
   comanda idempotent dry-run a Fase C, patró `backfill_model_taxonomy`.
4. **Abast de Fase B**: unificar o no el fork de `GradingRuleSets.jsx` en estendre la cascada (deute vs scope mínim).

**Res de Fase B fins que el GATE es resolgui.** Backup PRE-AMBIT (`pg_dump -Fc`) abans de la 1a escriptura.
