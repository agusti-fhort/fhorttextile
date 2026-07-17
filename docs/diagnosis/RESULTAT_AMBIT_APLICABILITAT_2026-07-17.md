# RESULTAT — Àmbit d'aplicabilitat del contenidor · higiene d'entrada · arbre complet a Grading Rules

Data: **2026-07-17** · staging `dev`, tenant `fhort` · **SENSE push, SENSE deploy** (els fa l'Agus).
Diagnosi germana: `DIAGNOSI_AMBIT_APLICABILITAT_2026-07-17.md`. Backup: `ops/backups/PRE-AMBIT_20260717.dump`
(pg_dump -Fc, capçalera verificada amb pg_restore v18).

Mètode: Patró A (diagnosi) → **GATE (Agus)** → Patró B. **9 commits**, tots verds (`manage.py check` +
`npm run build` + 38 tests). Motor `generate_graded_specs` **INTOCAT**.

## GATE — el que va decidir l'Agus

1. **Identitat: opció (c)** — `garment_type_item` + constraint `uniq_client_container_identity`
   (migració 0039) **INTACTES** com a IDENTITAT; l'àmbit multi-node és **NOMÉS DISPONIBILITAT**.
   → migració **additiva pura**, **risc 0 a PROD**, reconciliació de sembra **sense canvis**.
2. **Unificar el fork** de la cascada de Grading Rules en estendre-la.

## Commits

| # | Hash | Peça |
|---|---|---|
| B.1 | `7c2ba9e` | `RuleSetScopeNode` (àmbit multi-node) + migració 0040 additiva |
| B.3-be | `4d99049` | `applies_to`/`garment_type_item` al serializer + `apply_scope_nodes` + multi-target al create |
| B.4-m | `174233d` | matching per àmbit (node o ancestre) + fallback legacy |
| B.4-c | `4279dc3` | cascada única grup→família→item · **FORK TANCAT** (−304 línies de còpia) |
| C | `6e4c350` | `backfill_ruleset_scope` (àmbit ← gti), idempotent, dry-run per defecte |
| B.2 | `8ad6b29` | «Nou run de client» = autoria amb ÀMBIT + higiene d'entrada (1/2/3/5) |
| B.3 | `265e52e` | el botó d'autoria passa de Size Library → **Grading Rules** |

## La llei, implementada

- **`RuleSetScopeNode`** (`pom/models.py`): un node = un dels tres FKs (grup/família/item) segons
  `node_type` (validat a `clean()`), 3 unique parcials contra duplicats, FK a `tasks` amb
  `db_constraint=False` (patró cross-app). Migració **0040 additiva pura** (CreateModel), índexs auditats.
- **Disponibilitat** (`gradingAxes.scopeApplies`): un contenidor amb àmbit aplica a un node si el seu
  àmbit conté **aquell node o un ANCESTRE** (item → família → grup). Marcar un GRUP → disponible per a
  tots els seus garments; baixar a ITEM → només aquell.
- **Fallback explícit**: un ruleset **sense** àmbit (canònics i contenidors no backfillats) es casa pel
  seu `garment_group`, **exactament com avui** → cap regressió.
- **Identitat preservada**: si l'àmbit és **exactament un item**, el payload porta `garment_type_item_id`
  → el contenidor manté la identitat fina i la guarda d'unicitat (0039 + 409 avís-i-confirma). Àmbits
  amples → `gti` NULL, sense guarda, **a posta**.
- **Multi-target**: ja estava modelat (`targets` M2M); només calia cablar-lo (`target_codis`).

## Higiene d'entrada («Nou run de client»)

| # | Abans | Ara |
|---|---|---|
| 1 | codi client = `<input>` text 3 car. | **`CustomerSelector`** (el selector dona id → es resol el codi que espera el backend) |
| 2 | run = `<textarea>` d'etiquetes | **`SizeSystemSelector`** (NOU) → run + talla base surten del sistema; base per pills |
| 3 | construcció/fit = `<select>` | **pills** (mateix llenguatge visual) |
| 4 | garment = `<select>` únic, sovint buit | **`ScopeSelector`** — àmbit jeràrquic acumulatiu multi-node, **obligatori (≥1)** |
| 5 | només `cursor:wait` | **Spinner** viu mentre la IA extreu |

## Verificació — **16/16 E2E verd** (endpoints/ORM reals, tot amb rollback)

- **Àmbit GRUP** (TOPS) → aplica a la blusa **i** a `shirt_woven` (tot el grup) ✓
- **Àmbit ITEM** (5) → aplica a la blusa, **NO** a `shirt_woven` ✓
- **Multi-node** (grup+item) persistit ✓ · **Multi-target** (WOMAN+TEEN_GIRL) ✓ · **Família** ✓
- **Identitat INTACTA**: `gti=5` sobreviu als canvis d'àmbit i `cerca_contenidor_client` (sembra)
  segueix trobant el 115 ✓ (opció (c) honrada)
- **No-regressió**: el 115 sense àmbit segueix visible per fallback `garment_group`; el 124 viu; cens
  CLIENT_RUN intacte (2); **0 nodes residuals** (rollback net) ✓
- Reparació del matí **intacta** (`backfill_model_taxonomy` 35 · `flag_incomplete_models` 14/20/9) ✓
- `manage.py check` net · **38 tests OK** · `npm run build` net.

## CHECKLIST VISUAL per a l'Agus (staging)

- [ ] **Grading Rules**: hi ha el botó **«Nou run de client»** (abans a Size Library). La Size Library
      ja no el té (però el deep-link de l'ImportWizard hi segueix funcionant).
- [ ] **«Nou run de client»**: el client es **tria** (no es tecleja); el **run es tria** d'un sistema de
      talles (no es tecleja) i la talla base surt en pills; **construcció i fit són botons**; en pujar la
      fitxa apareix una **rodeta** mentre la IA treballa.
- [ ] **Àmbit**: marca *grup Parts superiors* **+** *item Blusa* (multi-node) i **Dona + Adolescent nena**
      (multi-target) → el pas no deixa continuar amb l'àmbit buit; el contenidor es crea amb l'àmbit.
- [ ] **Grading Rules · cascada**: baixa target → construcció/fit → grup → **família → item** (nous).
      Un contenidor d'àmbit-**grup** apareix per a **tots** els items del grup; un d'àmbit-**item**, només
      per al seu.
- [ ] **Wizard de model** (pas 4): una blusa de dona veu el contenidor marcat a nivell **grup** superior.
- [ ] **No-regressió**: els contenidors existents (115) segueixen visibles i sembrant igual.

## RUNBOOK DE DEPLOY (l'executa l'Agus; cap pas d'agent a PROD)

1. **Backup PROD** (`pg_dump -Fc` → `/srv/fhort-prod-backups/`), verificar amb
   `/usr/lib/postgresql/18/bin/pg_restore -l <dump>`.
2. **fetch/merge** de `dev` + verificacions habituals (`git show <hash>` de la cadena).
3. **Migració**: `migrate_schemas` (mai `--schema`) → aplica **0040** (CreateModel additiu; **no toca la
   0039 ni cap columna existent**). Auditar a la BD:
   `SELECT count(*) FROM pom_rulesetscopenode;` (0 en fresc) i que els índexs `uniq_scope_*` hi són.
4. **Build front** (`npm run build`) + **restart**.
5. **`backfill_ruleset_scope`** — dry-run, revisar, després `--commit`:
   ```
   python manage.py backfill_ruleset_scope --schema fhort            # dry-run: revisar
   python manage.py backfill_ruleset_scope --schema fhort --commit   # escriure
   ```
   Migra els contenidors amb `garment_type_item` → àmbit `ITEM` equivalent. Els que no en tenen es
   deixen **sense àmbit a posta** (fallback `garment_group` = comportament d'avui) i es **llisten** per
   completar-los a mà des de la UI.
6. **Verificació**: obrir Grading Rules (cascada fins a item), crear un run de prova amb àmbit, i
   comprovar que els contenidors existents segueixen visibles i sembrant.

> `backfill_ruleset_scope` és **idempotent** (salta els que ja tenen àmbit). Els passos 5-6 són
> POST-deploy del codi.

## Anotacions (fora d'scope, no tocades)

- **Watchpoint de contenidor sense àmbit: NO representable.** `Watchpoint.model` és un FK **obligatori**
  a un *Model*; no hi ha ancoratge per a un *GradingRuleSet*. Per això els contenidors sense àmbit
  derivable es reporten al command (i aquí), en comptes d'inventar un watchpoint sobre un model aliè.
  Si es vol un avís persistent a nivell de contenidor, cal decidir-ne el model (fora d'aquest sprint).
- Els `perfils` (SizingProfile) segueixen enviant `garment_type_id` (ara sempre null, com quan el
  `<select>` es deixava buit): l'àmbit el porta ara `applies_to`. Anotat, no tocat.
- L'enllaç grup↔família segueix sent un **string** (`GarmentType.grup`), no un FK — la resolució
  d'ancestres hi depèn. Deute conegut, no tocat.
