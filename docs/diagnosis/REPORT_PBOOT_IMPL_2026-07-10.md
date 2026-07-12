# REPORT — P-BOOT-IMPL: `bootstrap_tenant`, un tenant nou neix VIU

Data: 2026-07-10 · **Patró B (IMPLEMENTACIÓ)** · staging `/var/www/ftt-staging`, branca `dev`
Base: `docs/diagnosis/DIAGNOSI_PBOOT_CENS_COPIA.md` · Decisions DC-1..DC-6

**2 commits, sense push. Cap migració.** Regla del verd a cada peça. Tenant de prova `demo`
provisionat, verificat i **netejat**: staging queda amb `fhort` + `public`.

| Peça | Commit | Estat |
|---|---|---|
| P1 — `bootstrap_tenant` (+ P3 dins) | `bae36c7` | ✅ VERD |
| P2 — `create_tenant_admin` | `b08baaf` | ✅ VERD |

> **Desviació del pla de commits (assumida):** P3 (tancament `onboarding→actiu` + D7) va entrar
> **dins** el fitxer de P1, no com a commit separat. Motiu: separar-lo hauria significat
> commitejar un `bootstrap_tenant` que deixa tots els tenants en `onboarding` — un estat
> intermedi que no és verd en el sentit de «fa el que diu». No hi ha res de P3 pendent.

---

## Guardes de concurrència

- `git fetch` + `git log -10`: la línia C de la sessió de plataforma és a `36ad886` (C3.2).
  Els meus commits de P-PROV (`ec0b551`, `c1dfba6`, `26736b1`) hi són.
- `git status` sobre `tasks/`, `pom/`, `backoffice/` → **buit** abans de començar.
- **Migració: cap.** `Client.estat` ja té `default='onboarding'` (verificat viu) i el camp
  `onboarding_complet` ja existeix → P3 no en necessita. `showmigrations` → **0 pendents**;
  `makemigrations --check` → `No changes detected`. **No s'ha cridat `migrate_schemas`.**

---

## Decisió: on viu la comanda

**`backend/fhort/tasks/management/commands/`**, per dependències:

- `tasks` **ja depèn de `pom`** (`GarmentTypeItem.garment_type → pom.GarmentType`) i **d'`accounts`**
  (`TimeSeed.updated_by → accounts.UserProfile`). Una comanda aquí no crea cap import nou.
- A `pom` hauria calgut importar `tasks` (direcció contrària a la ja establerta).
- **Mai a `backoffice`**: és app SHARED (public) i no ha de conèixer el detall del catàleg d'un
  tenant. Per coherència, `create_tenant_admin` viu al mateix lloc (i `tasks` ja arrossega
  `accounts`).

---

## 🔴 Cinc coses que el cens no deia (mesurades, no assumides)

El brief prohibia assumir el comportament dels catàlegs-fulla. Vaig **provisionar un tenant verge
i mirar-hi dins** abans d'escriure una sola línia de còpia. El que va sortir:

1. **Els 7 catàlegs-fulla també neixen buits.** `POMCategory` (28), `SizeSystem` (20),
   `SizeDefinition` (120), `GarmentGroup` (11), `Target` (13), `FitType` (10),
   `ConstructionType` (4) → **tots a 0** en un tenant nou. Cap migració els sembra (els 3 `RunPython`
   de `pom` que els toquen són transformacions). **El cens real són 19 peces de còpia, no 13.**
   Sense això, `GarmentType`, `POMMaster` i `GradingRuleSet` no haurien tingut on enganxar les FK.

2. **`POMMaster` NO és 1:1 amb `POMGlobal`.** La diagnosi ho donava per «1:1 *de facto*». La dada:
   **126 valors distints de `pom_global` per a 170 files**. Com a clau natural hauria produït
   col·lisions silencioses. La clau bona és **`codi_client` (170/170 distints)**.

3. **Tres M2M i un tercer auto-FK que el cens no llistava:** `SizeSystem.targets`,
   `GarmentType.targets_recomanats`, `GradingRuleSet.targets`, i `SizeSystem.parent`.

4. **`SizingProfile.modified_by_id` no és una FK declarada** — és un `IntegerField` amb l'id d'un
   `UserProfile` de fhort. El tractament genèric de «FK d'entitat» **no l'hauria capturat**: viatjava
   com un enter qualsevol. Hi ha **1 fila real** afectada. Ara porta guard explícit i es compta.

5. **El provisioning triga ~14 s, no «desenes de segons»** (la diagnosi B4 ho estimava en 30-90 s
   per recompte de migracions, marcat com a estimació). `Client.save()` amb `auto_create_schema` va
   trigar **14,1 s** mesurats. La còpia sencera, **12,8 s**.

Claus naturals verificades empíricament per als 4 models «sense clau»:
`GarmentType.codi_client` 19/19 · `POMMaster.codi_client` 170/170 · `GradingRuleSet.nom` 25/25 ·
`SizingProfile(target, garment_type, construction, fit_type, size_system, version)` 26/26.

---

## P1 — `bootstrap_tenant <schema> --from fhort [--dry-run]`

Còpia tenant→tenant per `schema_context`, en ordre topològic. Lleis aplicades:

- **Idempotent-additiva:** `update_or_create` per clau natural. **Mai `delete`.**
- **Remapeig de FK per clau natural**, via mapa `pk_origen → pk_destí` per model. Mai per pk
  (el patró de `clone_model_for_qa` reusa FK per valor i **només val intra-schema**).
- **FK a entitat no viatgen** i es **compten**: `customer`, `updated_by`, `modified_by_id`.
- **`TaskType` no es copia** (neix sol); `TaskTimeEstimate.task_type` es re-resol **per `code`**
  (llei G9). `TimeSeed.key` ja és un string amb el code.
- **Welford net:** només viatja `estimated_minutes`; `n`/`mean_minutes`/`m2` neixen a 0.
- **Auto-FK en 2 passades**; **M2M** després de la 1a passada.
- Si una fila no pot remapejar una FK → **es salta amb avís**, la comanda acaba != 0 i el tenant
  **es queda en `onboarding`** (re-executable, perquè és idempotent).

### Comptatges demo vs fhort (1a passada real)

| Peça | fhort | demo | | Peça | fhort | demo |
|---|---:|---:|---|---|---:|---:|
| POMCategory | 28 | 28 | | GarmentType | 19 | 19 |
| GarmentGroup | 11 | 11 | | POMMaster | 170 | 170 |
| Target | 13 | 13 | | GradingRuleSet | 25 | 25 |
| FitType | 10 | 10 | | GarmentTypeItem | 57 | 57 |
| ConstructionType | 4 | 4 | | GarmentPOMMap | 1529 | 1529 |
| SizeSystem | 20 | 20 | | GradingRule | 707 | 707 |
| SizeDefinition | 120 | 120 | | GradingException | 0 | 0 |
| POMGlobal | 125 | 125 | | SizingProfile | 26 | 26 |
| GarmentTypeGlobal | 59 | 59 | | TaskTimeEstimate | 460 | 460 |
| BodyMeasurementISO | 0 | 0 | | TimeSeed | 8 | 8 |

**Total: 3391 creats, 0 saltats.** Comptatges **idèntics peça a peça**.

### Els NULL de FK d'entitat (3, tots esperats)

| Camp | Files | Per què |
|---|---:|---|
| `GradingRuleSet.customer` | **2** | Els dos rulesets amb customer a fhort (104 i 111, tots dos **LOS**) |
| `SizingProfile.modified_by_id` | **1** | Id d'un `UserProfile` de fhort (la fuita del punt 4) |
| `TimeSeed.updated_by` | 0 | Les 8 files ja el tenien NULL a fhort |

Verificat al destí: `GradingRuleSet.customer` no-NULL = **0**; `SizingProfile.modified_by_id`
no-NULL = **0**.

### Idempotència i integritat

- **2a passada: 0 creats, 3391 actualitzats.** Cap duplicat.
- `--dry-run`: mateixos recomptes, `transaction.set_rollback(True)`, res escrit.
- `TaskType` a demo = **14** (neix sol, **no duplicat** per la còpia).
- **Welford:** demo té **0** files amb `n≠0` (fhort en té 18), i la **suma d'`estimated_minutes` és
  440 als dos**. La definició viatja, la història d'ús no.
- Auto-FK: 2 resoltes a la 2a passada; `GradingRuleSet` amb `parent_version` = 1 a tots dos.
- M2M: 23 rulesets amb `targets` a tots dos.

---

## P2 — `create_tenant_admin <schema> --email … [--password …]`

Resol el cap-i-cua censat a B4: la porta HTTP exigeix estar **ja** dins el schema **i** tenir
`MANAGE_USERS`; un tenant nou no té cap usuari. La comanda entra pel costat amb
`schema_context(schema)`: allà `connection.schema_name != 'public'`, la guarda del signal
(`accounts/signals.py:24-25`) no salta i el `UserProfile` es crea sol — però amb
`rol_nom='technician'` (`capabilities.py:28`), que **no té `MANAGE_USERS`**. Per això es **força
`rol_nom='admin'` després del signal**.

- Idempotent: 2a crida → *"ja existeix amb rol 'admin'. Res a fer."*
- Guarda: `create_tenant_admin public` → `CommandError` (allà mana `create_backoffice_admin`).
- Contrasenya per `--password` o generada amb `secrets`, impresa un sol cop.
- **DIFERIT AMB NOM:** forçar canvi de contrasenya al primer login (exigiria frontend de tenant).

---

## P3 — Tancament `onboarding → actiu` (dins P1)

En verd: propaga **D7** (`Customer.codi_global = codi_tenant` al self-Customer) i escriu
`onboarding_complet=True` + `estat='actiu'`. En vermell: deixa `onboarding`, reporta i surt != 0.

Verificat a demo: `estat=actiu`, `onboarding_complet=True`, self-Customer `codi='DEM'`,
`codi_global='DEM'`.

---

## Verificació end-to-end (real, no simulada)

1. `Client(schema_name='demo', codi_tenant='DEM').save()` → `CREATE SCHEMA` + migracions (**14,1 s**).
2. `bootstrap_tenant demo --from fhort --dry-run` → 3391, res escrit.
3. `bootstrap_tenant demo --from fhort` → 3391 creats (**12,8 s**), estat `actiu`.
4. `bootstrap_tenant demo --from fhort` (2a) → 0 creats / 3391 actualitzats.
5. `create_tenant_admin demo --email test@demo.local` → admin creat; 2a crida no duplica.
6. **Login real:** `POST http://127.0.0.1:8001/api/token/` amb `Host: demo.fhorttextile.tech` →
   **HTTP 200** amb `access`/`refresh`.
7. **Lectures autenticades amb el token del tenant demo:**
   `garment-type-items/` → 200 · **57** · `sizing-profiles/` → 200 · **26** ·
   `task-types/` → 200 · **14**.

> El pas 7 és el que demostra la tesi de la peça: el tenant no només té files a la BD, **serveix el
> catàleg per l'API a un usuari que abans no podia existir**.

### Neteja (feta)

`Domain` i `Client` de demo esborrats; `DROP SCHEMA demo CASCADE` executat explícitament perquè
`auto_drop_schema = False` (`tenants/models.py:172`) fa que esborrar el Client **no** dropegi el schema.

Estat final: `clients = [public, fhort]` · `schemes = [fhort, public]`.
**`fhort` intacte**, comprovat després: 25 rulesets (25 amb `origen` NULL), 1529 maps, 18 files amb
Welford `n≠0`, 1 `SizingProfile.modified_by_id` — tot com abans.

---

## Anotacions fora d'scope (vistes, no tocades)

1. **Ha aparegut un `Domain` per `stagingbackoffice.fhorttextile.tech`** a `tenants_domain`, que a la
   `DIAGNOSI_BACKOFFICE_POSTREFACTOR` **no existia**. Algú l'ha afegit entremig. No l'he tocat.
   Convé revisar si va acompanyat del vhost i el certificat (les altres tres peces de B4).
2. **`GradingRuleSet.pendents_vincular`** (codis d'un run no vinculats) i
   **`GradingRule.talla_break_pos`** (cache del run) **viatgen** amb la còpia. Són residu d'ús, no
   definició. DC-1 deia «copiar el grading SENCER», així que els he deixat. 💡 **PROPOSTA (a validar):**
   netejar-los al destí quan el backfill d'`origen` estigui fet.
3. **Els 25 rulesets segueixen amb `origen NULL`** (P-PROV encara no s'ha backfillat). Per això
   `bootstrap_tenant` avui copia **tot** el grading, tal com mana DC-1. Quan `origen` estigui poblat,
   afegir-hi un filtre `origen != CLIENT_RUN` és una línia — i és el que la llei RUN-CLIENT demana.
   **Avui, un `bootstrap_tenant` copiaria els runs de client (107, 110, 111…) al tenant nou.**
   Cap risc a staging; **sí que n'hi hauria a producció**.
4. **`BodyMeasurementISO` és buit als dos schemes.** La peça hi és per completesa de l'ordre
   topològic (`POMGlobal.body_measure_iso`), però avui no copia res.

---

## Què ha de fer el CTO

1. Revisar: `git show bae36c7`, `git show b08baaf`.
2. **Push des de SSH** (cap agent ha fet push).
3. **Abans de fer servir `bootstrap_tenant` en producció:** completar el backfill d'`origen`
   (`manage.py set_grading_origen --list`) i afegir el filtre `origen != CLIENT_RUN` a la còpia de
   `GradingRuleSet`. Vegeu anotació 3 — **és el forat viu més important**.
4. Decidir sobre l'anotació 2 (residu de run que viatja).
5. Revisar l'anotació 1 (Domain de stagingbackoffice sense la resta de l'entorn).
