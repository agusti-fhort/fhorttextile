# VERIFICACIÓ — `bootstrap_tenant` contra un destí POBLAT (pre-materialització PROD)

Data: 2026-07-23 · Entorn: STAGING (`/var/www/ftt-staging`, `dev` ≡ `origin/dev`).
Tipus: **verificació amb assaig**, cap canvi de codi. Convenció: `fitxer:línia` sobre
`fhort/tasks/management/commands/bootstrap_tenant.py` (477 línies).

> CONTEXT: a PROD, `instantiate_external_models LOS→FTT` (dry-run) dona **1458 refs no
> aparellades**: el catàleg v2 de LOSAN (62 GTI, 11 SizeSystems `LOS_*`, 19 rulesets "LOS …")
> viu NOMÉS a `los` i mai s'ha materialitzat a `fhort`. Cal materialitzar `los→fhort` ABANS
> d'instanciar. `bootstrap_tenant` es va dissenyar per sembrar tenants VERGES; el `fhort` de
> PROD està POBLAT (catàleg propi + BRW + feina). Aquesta és la pregunta.

---

## 1. LECTURA DE CODI — què fa si la clau natural JA EXISTEIX al destí

**LA RESPOSTA, en una línia:** cada entitat es materialitza amb
**`obj, created = model.objects.update_or_create(**lookup, defaults=values)`** —
`bootstrap_tenant.py:311`. `lookup` = la clau natural; `defaults` = **TOTS** els camps
concrets no-clau (`_concrete`, `:220`). Per tant, si la clau ja existeix al destí:

> **UPDATE cec de TOTS els camps no-clau amb els valors de l'origen.** No és `get_or_create`
> (no respecta el que ja hi ha), no és `create` cec (no duplica), no salta. **Sobreescriu.**
> Mai fa `delete` (`:23` "MAI delete"), i comptabilitza `created` vs `updated` (`:314-315`).

Això és **uniforme per a totes les 19 peces** de `_spec()` (`:135-162`): l'estratègia contra
col·lisió no depèn de l'entitat — sempre `update_or_create`. El que varia per entitat és NOMÉS
la **clau natural** (què compta com "ja existeix") i com es remapegen les seves FK:

| Entitat | Clau natural (lookup) | Línia |
|---|---|---|
| BodyMeasurementISO | `codi_intern` | :138 |
| POMCategory · GarmentGroup · Target · FitType · ConstructionType | `codi` | :139-143 |
| **SizeSystem** | `codi` | :145 |
| SizeDefinition | `(size_system, etiqueta)` | :146 |
| POMGlobal · GarmentTypeGlobal | `codi` | :147-148 |
| **GarmentType** | `codi_client` | :150 |
| **POMMaster** | `codi_client` | :152 |
| **GradingRuleSet** | `nom` | :153 |
| **GarmentTypeItem** | `(garment_type, code)` | :154 |
| GarmentPOMMap | `(garment_type_item, pom)` | :155 |
| GradingRule | `(rule_set, pom)` | :156 |
| SizingProfile | `(target, garment_type, construction, fit_type, size_system, version)` | :157-159 |
| TaskTimeEstimate | `(garment_type_item, task_type)` | :160 |
| TimeSeed | `(scope, key)` | :162 |

Les **estratègies de FK** (`MAP`/`NULL`/`DEFER`/`NATURAL`, `:46-49`) NO canvien això —
governen com es resol una FK, no la col·lisió de la fila:
- **MAP** (`:280-296`): remapa la FK via `maps[pk_origen→pk_destí]`. Si el relacionat no s'ha
  copiat i la FK és nullable → `NULL` + compta `nulled` (`:288-291`); si és obligatòria → `skip`.
- **NULL** (`:260-263`, `:238-243`): FK a entitat del tenant ORIGEN (`customer`, `updated_by`,
  `modified_by_id`) → no viatja, queda NULL.
- **DEFER** (`:264-267` + `_resolve_deferred :335-345`): auto-FK (`SizeSystem.parent`,
  `GradingRuleSet.parent_version`, `SizingProfile.parent_profile`) → NULL a la 1a passada,
  resolta a la 2a. La 2a passada fa `update(...)` sobre la fila ja creada/actualitzada.
- **NATURAL** (`:268-278`): el relacionat NO es copia; es re-resol per clau al destí
  (`TaskTimeEstimate.task_type` per `code`). Si no existeix al destí → `skip` dur (`:274-275`).
- **M2M** (`SizeSystem.targets`, `GradingRuleSet.targets`, `:321-329`): fa **`.set(new_rel)`** —
  **REEMPLAÇA** la relació existent al destí, no hi afegeix. Un altre vector de sobreescriptura.

**Conclusió 1:** contra un destí poblat, tota clau natural que COINCIDEIXI és una
**sobreescriptura** (camps + M2M) de la fila real de `fhort` amb la versió de `los`. És
additiu NOMÉS per a les claus que NO existeixen al destí.

---

## 2. DIRECCIÓ — accepta `source=los`, `target=fhort`?

**Sí, sense cap guarda que ho impedeixi.** `--from` fixa l'origen (default `fhort`, `:180`);
el `schema` posicional és el destí (`:179`). Les úniques guardes (`:362-372`):
- `schema != 'public'`; `schema != source`; el destí ha d'existir; l'origen ha d'existir.
- **Cap guarda sobre l'estat del destí** (no exigeix `onboarding`; no comprova si està poblat).

Per tant `bootstrap_tenant fhort --from los` s'executa. **Però el destí rep efectes secundaris**
pensats per a un tenant nou (només en execució real, no dry-run):
- `_close_onboarding(client)` (`:446`, def `:348-356`): reescriu el `codi_global` del
  self-Customer de `fhort` (ja és 'FTT' → inofensiu).
- `client.estat='actiu'` + `onboarding_complet=True` (`:449-451`): `fhort` ja és actiu → idempotent.
- `seed_master_template()` (`:441`): **REGENERA la Template FTT mestra a la media de `fhort`** —
  efecte real sobre el tenant productiu.

**Conclusió 2:** la direcció és lliure, però el command tracta el destí com un tenant en
onboarding (tanca onboarding + regenera template) — inadequat per a un `fhort` viu.

---

## 3. ABAST DELS BLOCS + el filtre CANONICAL

Els 3 tipus no aparellats del dry-run de PROD i el bloc que els cobreix (`SEED_BLOCKS :83-91`):

| Tipus no aparellat | Bloc | Deps (`SEED_BLOCK_DEPS :92-104`) |
|---|---|---|
| GTI de NEWBORN | `garments` (GarmentType, GarmentTypeItem) | `{base}` |
| SizeSystems `LOS_*` | `size_systems` (SizeSystem, SizeDefinition) | `{base}` |
| rulesets "LOS …" | `grading` (GradingRuleSet, GradingRule) | `{base, size_systems, pom_masters, garments}` |

Clausura per cobrir els 3 = **`{grading, garments, size_systems, pom_masters, base}`**
(`seed_block_closure :106-116`). **`base` sempre hi entra** (tots en depenen): és el vector de
sobreescriptura del catàleg compartit de `fhort` (POMCategory, GarmentGroup, Target, FitType,
ConstructionType, POMGlobal, GarmentTypeGlobal — vocabulari canònic, claus que molt probablement
COINCIDEIXEN amb les de `fhort`).

**El gate CANONICAL (`:397-405`) — crític, i NOMÉS actiu amb `--profile`:**
- Amb `--profile` que inclogui `grading`: `source_filters[GradingRuleSet] = {origen: CANONICAL}`
  (`:404`) → **només es copien els rulesets amb `origen=CANONICAL`**. Si els 19 "LOS …" de LOSAN
  són `CLIENT_RUN`/`IMPORT` → **NO es copien** → els 1458 refs de grading segueixen sense
  aparellar. Si CAP és CANONICAL → **error dur** (`:399-403`), no copia res.
- **Sense `--profile`: NO hi ha filtre d'origen** → es copia TOT el catàleg (els 19 rulesets
  entren sigui quin sigui l'origen) — però llavors també entra tot el vector de sobreescriptura
  de `base` i de tota clau coincident.

⚠️ **A verificar a PROD amb SQL** (staging `los` té el catàleg MIRALL sintètic de l'assaig, no el
real — 0 rulesets, 0 base): quin `origen` tenen els 19 rulesets "LOS …" reals a `los`?
```sql
-- a PROD, schema los:
SELECT origen, count(*) FROM los.pom_gradingruleset WHERE nom LIKE 'LOS %' GROUP BY origen;
```
Si no són CANONICAL, el flux `--profile` amb `grading` els EXCLOU (el gate era per al flux
automàtic Free, RUN-CLIENT A3) — i el flux SENSE `--profile` els inclou però arrossega la
sobreescriptura de base.

---

## 4. ASSAIG a staging (dry-run — l'execució real seria destructiva per a `fhort`)

Estat de partida: `fhort` poblat (21 GarmentType, 62 GTI, 28 SizeSystem, 45 GradingRuleSet,
28 POMCategory, 364 POMMaster). `los` = mirall sintètic de l'assaig anterior (1 GT
`BUTTONED_TOPS`, 1 GTI `shirt_woven`, 2 SizeSystem `ALPHA_EU_W`+`SYS-ONLY-LOS`, 0 base, 0 grading).

**No s'ha executat en real**: un `bootstrap_tenant fhort --from los` real sobreescriuria files
reals de `fhort` (vegeu sota) i en regeneraria la Template mestra. El **dry-run** (que fa
`transaction.set_rollback(True)`, `:456`) respon la pregunta sense tocar res.

```
manage.py bootstrap_tenant fhort --from los --dry-run

  SizeSystem                 1 creats      1 actualitzats
  GarmentType                0 creats      1 actualitzats
  GarmentTypeItem            0 creats      1 actualitzats
  (la resta: 0/0 — el mirall de los no té base/grading/pommasters)
  Total: 1 creats, 3 actualitzats, 0 FK d'entitat a NULL, 0 saltats.
```

**Interpretació:** `1 creat` = `SYS-ONLY-LOS` (clau nova → additiu, OK). **`3 actualitzats`** =
3 files REALS de `fhort` que una execució en real SOBREESCRIURIA:
- `SizeSystem codi=ALPHA_EU_W`, `GarmentType codi_client=BUTTONED_TOPS`, `GTI (BUTTONED_TOPS, shirt_woven)`.

**Que la sobreescriptura MUTA dades reals** (no és un no-op) — comparació origen↔destí:
```
fhort GarmentType BUTTONED_TOPS: nom_client = 'Buttoned Tops'   (majúscula T)
los   GarmentType BUTTONED_TOPS: nom_client = 'Buttoned tops'   (minúscula t)  ← guanyaria los
```
Un `bootstrap` real deixaria `fhort` amb `'Buttoned tops'`. Amb 3 col·lisions del mirall
sintètic mínim; amb el catàleg v2 REAL de LOSAN (que comparteix el vocabulari `base` canònic amb
`fhort`), les col·lisions serien MOLTES més.

**`fhort` intacte després del dry-run:** 21 GarmentType / 28 SizeSystem / 62 GTI (sense canvis) —
el rollback funciona.

---

## 5. VEREDICTE

**NO es pot executar `bootstrap_tenant los→fhort` tal qual a PROD.** Raons (per severitat):

1. 🔴 **Sobreescriptura del catàleg viu de `fhort`.** `update_or_create` (`:311`) + `.set()` de
   M2M (`:329`) fan que TOTA clau natural de `los` que coincideixi amb una de `fhort` SOBREESCRIGUI
   la fila real de l'estudi (camps + targets). El bloc `base` (vocabulari canònic compartit)
   entra SEMPRE per dependència → col·lisió massiva probable. A staging, el mirall mínim ja
   provoca **3 sobreescriptures**. Corromp el catàleg del qual pengen els 962 models LOS + BRW +
   la feina de `fhort`.
2. 🟠 **El gate CANONICAL pot excloure els rulesets de LOSAN.** Amb `--profile`+`grading`, només
   viatgen els `origen=CANONICAL` (`:404`); si els 19 "LOS …" no ho són → no es materialitzen i
   els 1458 refs segueixen oberts (o error dur si cap és CANONICAL). Sense `--profile` sí viatgen,
   però a canvi d'obrir la sobreescriptura de tot el catàleg.
3. 🟠 **Efectes secundaris de destí-verge sobre un `fhort` viu.** Regenera la Template FTT mestra
   (`:441`) i tanca onboarding (`:446-451`) — impropi d'un tenant productiu.

### El que caldria (FIX proposat)

Una **materialització quirúrgica ADDITIVA** (la "peça 5" del camí crític, diagnosi §8.1) — no
reutilitzar `bootstrap_tenant` tal qual. Opcions, de menys a més cost:

- **A (flag additiu a bootstrap, ~mig dia):** afegir `--additive` que (i) canviï `update_or_create`
  per **`get_or_create`** (crear si la clau és absent, **SALTAR si existeix** — mai sobreescriure;
  comptar `skipped`), (ii) canviï el `.set()` de M2M per `.add()` només-si-nova, (iii) ometi
  `_close_onboarding` + `seed_master_template` quan el destí ja és `actiu`. Amb això, `los→fhort`
  només CREA les claus noves de LOSAN i deixa intacte tot el que `fhort` ja té.
- **B (command nou `materialize_catalog`, ~1-2 dies):** dedicat, additiu per disseny, amb selecció
  de blocs SENSE forçar `base` quan el destí ja el té, i sense gate CANONICAL (o amb un
  `--include-client-rulesets` explícit per portar els "LOS …" que no són canònics).

**Recomanació:** **Opció A** — és el canvi mínim que tanca el risc #1 i #3 i, combinat amb
**executar SENSE `--profile`** (per no xocar amb el gate CANONICAL, risc #2) però amb el mode
additiu (per no sobreescriure base), materialitza el catàleg v2 de LOSAN a `fhort` de forma segura.

### Passos per a PROD (després del fix A)

1. **Verificar l'origen dels rulesets** a `los` (SQL de §3). Decidir si `--additive` sense
   `--profile` (tot additiu) o amb un profile que inclogui grading sense el gate CANONICAL.
2. **DRY-RUN** primer: `bootstrap_tenant fhort --from los --additive --dry-run` → confirmar
   **0 `actualitzats`** (tot additiu) i que els creats = les claus v2 de LOSAN esperades.
3. **Backup de `fhort`** abans de qualsevol escriptura real.
4. Execució real `--additive` (sense dry-run), auditar comptes de catàleg de `fhort`
   abans/després (els existents NO han de canviar; només sumar els nous de LOSAN).
5. Llavors sí: `instantiate_external_models LOS→FTT --commit` (els 1458 refs ara resolen).

### Comanda EXACTA que s'executaria a PROD

> **Amb l'estat actual del codi: CAP.** No hi ha cap invocació segura de `bootstrap_tenant`
> `los→fhort` contra un `fhort` poblat — sobreescriuria catàleg viu. Cal primer el **FIX A**
> (`--additive`, ~mig dia). Un cop fet:
> ```
> manage.py bootstrap_tenant fhort --from los --additive --dry-run   # esperar 0 actualitzats
> # backup de fhort
> manage.py bootstrap_tenant fhort --from los --additive             # additiu, no sobreescriu
> manage.py instantiate_external_models --brand LOS --studio FTT --commit
> ```

---

## Notes d'estat
- Cap escriptura a `fhort`/`los` en aquesta verificació (només un dry-run rollbackejat).
- Dades sintètiques de l'assaig anterior segueixen a staging (anotades al doc previ
  `ASSAIG_FEDERACIO_STAGING_2026-07-24.md`); no s'han tocat.
- Verificar a PROD amb SQL (marcat a §3): `origen` dels 19 rulesets "LOS …" de `los`.
