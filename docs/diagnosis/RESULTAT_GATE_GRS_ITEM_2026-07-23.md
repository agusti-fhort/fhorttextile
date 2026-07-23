# RESULTAT — L'item viu sense graduació · perfils sense ruleset obligat · fit al wizard · LLEI C5

**Data:** 2026-07-23 · **Patró B (IMPLEMENTACIÓ)** · staging `/var/www/ftt-staging`, branca `dev`
· base `0fd3f2c` · **6 commits, cap push** (el push el fa l'Agus des de SSH).

Diagnosi de partida: [`DIAGNOSI_GATE_GRS_ITEM_2026-07-23.md`](DIAGNOSI_GATE_GRS_ITEM_2026-07-23.md)
— **NO se segella**: aquest sprint n'implementa els talls (a), (b), (c) i el canvi de font del
suggeriment, però (d) —la retirada del camp `GarmentTypeItem.grading_rule_set`— i la reversió del
dany a PROD queden a la cua. Segueix vigent com a mapa.

---

## Els commits

| # | hash | focus |
|---|---|---|
| 1 | `078d322` | **C3 · `SizingProfile.grading_rule_set` NULLABLE** (migració `pom/0045`) + les 4 superfícies que el llegien passen a tolerar-lo absent i a dir-ho |
| 2 | `516d5db` | **Comanda `crea_sizing_profiles`** (àmbit de catàleg, idempotent, dry-run per defecte) + perfil de la dessuadora aplicat a staging |
| 3 | `5120236` | **Tall (a) · l'item viu sense graduació**: cau el gate, neix del nom, «Sense graduació» triable, termòmetre honest, talla base opcional, eixos com a filtre |
| 4 | `532dd55` | **El suggeriment ve del catàleg** (`SizingProfile`), no de l'item — mor R2 |
| 5 | `fd76bf6` | **Fit al pas Peça + LLEI C5 al catàleg**: el backend informa (`compat`), el frontend atenua |
| 6 | `32df1b1` | Higiene: fora el FK `target` legacy del payload d'edició de rulesets |

*(La peça d'i18n que el brief numerava com a commit 6 no existeix per separat: la llei del repo
és paritat ca/en/es **dins del commit que introdueix la UI**, i així s'ha fet — 9 claus noves al
commit 3 i 2 al commit 5.)*

---

## Litúrgia de la migració (commit 1)

```
pom/0045_sizingprofile_grading_nullable.py
  AlterField sizingprofile.grading_rule_set → ForeignKey(blank=True, null=True,
      on_delete=PROTECT, related_name='sizing_profiles', to='pom.gradingruleset')
```

Ensenyada abans d'aplicar · `migrate_schemas` (mai `--schema`) → OK als 3 schemas ·
**auditoria directa a la BD** (no el que diu Django):

| schema | `grading_rule_set_id` | `size_system_id` |
|---|---|---|
| `fhort` | **YES** (nullable) | NO (NOT NULL) |
| `los` | **YES** | NO |
| `public` | **YES** | NO |

L'àmbit sí que declara escala; el que deixa de ser obligatori és la graduació.

---

## QA

| # | Prova | Resultat |
|---|---|---|
| **Q1** | Item nou de zero **sense tocar cap ruleset** | ✅ `POST /garment-type-items/` → **201**, `grading_rule_set: null`, `base_size_definition: null`. La card de Garment Types ja no ho compta com a mancança (termòmetre de 2 punts: POMs · talla base) i el pas 2 és accessible per carregar-hi POMs |
| **Q2** | Item amb ruleset previ → «Sense graduació» | ✅ `PATCH {grading_rule_set: null}` → **200**; l'item 4 (`shirt_woven`) passa de `grs 84` a `None` **amb la talla base intacta** (88). Catàleg de staging restaurat després de la prova |
| **Q3** | Wizard de model · Dona + Punt + Regular | ✅ `garment-types` en mode anotat retorna **17 files sempre** (res exclòs): `SWEATSHIRTS_MIDLAYERS` → `{ok: true}` (perfil nou), `TAILORED_PANTS` → `{ok: false, motiu: 'construction'}`, `KNIT_SWEATERS` → `{ok: false, motiu: 'target'}`. Amb `WOVEN` el veredicte s'inverteix on toca. Fit seleccionable al pas Peça |
| **Q4** | Suggeriment des del perfil | ✅ perfil **amb** graduació → suggereix `186 · LOS Woman Knit — Tops`; perfil **sense** (àmbit pur, el nou 577) → **cap suggeriment, 200, cap error**; combinació **sense cap perfil** → 0 perfils, 200 |
| **Q5** | Regressió + test NULL de la promoció | Vegeu sota |

### Q5 en detall

```
python manage.py test fhort.pom fhort.models_app.tests_sembra_grading
Ran 187 tests in 463.150s
FAILED (errors=24)
```

**Els 24 són EXACTAMENT els vermells preexistents documentats** a
[`RESULTAT_IMPORT_SENSE_PERDUES_2026-07-22.md` §Q4](RESULTAT_IMPORT_SENSE_PERDUES_2026-07-22.md):
mateixos mòduls (`pom.test_g6_segell` **17** + `pom.test_g6_grading_gates` **7** = 24), mateixa
signatura única (`IntegrityError` a `fitting_sizefitting_model_id_numero_6dc01a35_uniq`, dins del
`setUp`, pel fixture compartit que crea un `SizeFitting` a sobre del que ja sembra el signal).
**Aquest sprint no n'afegeix ni un.**

`fhort.models_app.tests_sembra_grading` — **0 errors, 0 failures**, i amb ell el test del camí NULL
de la promoció (`test_item_sense_ruleset_promou_valors_pero_no_toca_la_talla`, R1): **verd**.

*Lliçó heretada i repetida: el primer intent d'aquest Q5 es va perdre per un `| tail -40` que es va
menjar el resum. Repetit amb captura sencera a fitxer, que és el que hi ha aquí dalt.*

Frontend: `node --test src/components/grading/gradingAxes.test.js` → **11/11 verds** (5 del
suggeriment + **6 nous de la llei C5**). `npx eslint` sobre els 7 fitxers tocats: **0 errors**
(17 warnings, tots del patró `set-state-in-effect` que ja hi era).

---

## Guió per a PROD (per a l'Agus — **res d'això s'ha executat**)

**1 · Codi.** Merge `dev`→`main` amb els 6 commits, `git pull` a PROD, `npm run build`,
`systemctl restart`.

**2 · Migració.** Al deploy hi va **una migració nova**:

```bash
python manage.py migrate_schemas          # mai --schema
# auditoria directa (django-tenants pot donar un OK enganyós):
psql -c "select table_schema, column_name, is_nullable
         from information_schema.columns
         where table_name='pom_sizingprofile'
           and column_name in ('grading_rule_set_id','size_system_id');"
# esperat: grading_rule_set_id = YES · size_system_id = NO, a tots els schemas
```

**3 · Perfil de la dessuadora.** A PROD **no hi ha cap `SizingProfile` per a
`SWEATSHIRTS_MIDLAYERS`** (33 perfils, 8 famílies): sense això la família segueix invisible
encara que caigui el gate.

```bash
# dry-run primer (és el comportament per defecte)
python manage.py crea_sizing_profiles --target WOMAN --familia SWEATSHIRTS_MIDLAYERS \
    --construccio KNIT --fit REGULAR --size-system ALPHA_EU_W
python manage.py crea_sizing_profiles --target WOMAN --familia SWEATSHIRTS_MIDLAYERS \
    --construccio KNIT --fit REGULAR --size-system ALPHA_EU_W --apply
```
⚠️ Comprovar abans que `ALPHA_EU_W` és també a PROD el sistema dels perfils WOMAN canònics
(a staging ho és). La comanda és idempotent: tornar-la a executar no duplica res.

**4 · Reversió del dany al `hoodie`** (§3.3 de la diagnosi; el backup del 2026-07-23 02:30
diu que la línia base de les 57 files és NULL a les dues columnes i que **cap dels 52 models
apunta a l'item 16**):

```sql
-- 1) constatar què s'ha tocat
SELECT id, code, grading_rule_set_id, base_size_definition_id
FROM   tasks_garmenttypeitem
WHERE  grading_rule_set_id IS NOT NULL OR base_size_definition_id IS NOT NULL;
-- 2) revertir
BEGIN;
UPDATE tasks_garmenttypeitem
SET    grading_rule_set_id = NULL, base_size_definition_id = NULL
WHERE  id = 16;
COMMIT;
```
Amb el codi nou això també es pot fer **per UI** (botó «Sense graduació» al pas Context), que
és precisament el camí que abans no existia.

---

## Anotat, no tocat

| # | Cosa | On |
|---|---|---|
| 1 | **Retirada del camp `GarmentTypeItem.grading_rule_set`** (onades D2/D3). Amb el commit 4, els seus dos lectors reals ja no en depenen: R1 (promoció) només l'usa per resoldre l'escala de la talla i té camí NULL amb test; R2 (suggeriment) ha canviat de font. Falta la guarda del «backfill fantasma» item↔contenidor (`pom/models.py:566-568`) | fora d'abast (cua amb nom) |
| 2 | **Escampar C5 a la resta de wizards.** Avui viu a: picker de rulesets de l'item (`eliminatiu`), catàleg del pas Peça (`compat`) i selector de fit del pas 4. La resta de cascades segueixen amb el filtre excloent `?target` | fora d'abast |
| 3 | **CRUD de `SizingProfile`**: segueix sense endpoint de creació; la comanda tapa el forat però no és una superfície de producte | fora d'abast |
| 4 | El **fit no es persisteix** al model des del pas Peça. `Model.fit_type` existeix però amb un vocabulari divergent (`Regular/Slim/...` vs `REGULAR/SLIM/...` del catàleg `FitType`) i el backend no espera cap `fit` a `_resolve_garment_def`. Escriure-hi hauria estat inventar una conversió silenciosa; el fit segueix viatjant per la graduació, com fins ara | `models_app/models.py:103-109,204` |
| 5 | La dependència dura `sizing_profiles → grading` de `bootstrap_tenant` es manté tot i que el camp ja és nullable: sembrar perfils amb la graduació buidada en silenci seria una pèrdua muda. Comentari actualitzat perquè digui la veritat | `bootstrap_tenant.py:71-74` |
| 6 | El commit 6 (higiene) es va commitar **abans** de córrer el `npm run build` (un `cd` perdut). Build verificat immediatament després: **net**. Cap altre commit té aquesta esquerda | — |

---

## Sorolls de sessions concurrents

`git status` d'entrada: `DECISIONS.md` modificat (fitxer d'estat, mai es commiteja) i ~30
fitxers sense seguiment, la majoria **diagnosis d'altres sessions** que no s'han commitat mai
(`docs/diagnosis/` sí que és territori de git: 133 fitxers seguits). No s'ha tocat res que no
fos d'aquest sprint. `HEAD == origin/dev` en començar.

*Fi del sprint. `git show <hash>` per revisar cada peça; el push, des de SSH.*
