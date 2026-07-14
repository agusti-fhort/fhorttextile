> ⚠️ SUPERADA 2026-07-14 — implementada per l'Sprint F3 P-FREE-SEED (veure REPORT_F3_FREESEED_2026-07-14.md). Consulta només com a històric.

# DIAGNOSI F3 · P-FREE-SEED — sembra automàtica del Free, seleccionable des del backoffice

> Patró A (read-only). Font de veritat: el codi de staging `dev`. Base de brief: peça F3,
> decisió D-P4 (l'alta d'un tenant Free sembra sola; QUÈ se sembra ho defineix un perfil
> gestionat al backoffice). **STOP a Agus abans de qualsevol codi (Patró B).**

## 0. Territori i guardes (estat a l'inici)
- Branca `dev`. `git fetch` OK (`origin/main` avançat, aliè).
- **Canvis en vol de F1 al working tree, NO tocats:** `M tenants/models.py`,
  `?? tenants/migrations/0004_plan_stripe_lookup_*.py`. Territori F1 (Plan/tenants/pricing).
- Últims commits = F1 P-PRICE P1/P2. Cap toca el meu territori (SeedProfile · bootstrap_tenant
  · hook d'alta · pantalla de perfils).
- **Docs de disseny referenciats pel brief que NO són al repo de staging:**
  `PLA_IMPLEMENTACIO_BACKOFFICE.md` i `REGLES_FREE_TIERS_GMJ_TMA.md`. Procedeixo amb el codi
  com a font de veritat (llei "llegir el projecte sencer"). ⚠️ Si aquests docs contenen
  decisions vinculants, cal posar-los a l'abast abans de B.

---

## A1 · Estat real de `bootstrap_tenant`
[tasks/management/commands/bootstrap_tenant.py](../../backend/fhort/tasks/management/commands/bootstrap_tenant.py) (333 l., commits `bae36c7`/`b08baaf`).

- **19 peces** en ordre topològic, declarades a `_spec()` com a tuples
  `(model, clau_natural, {fk: estratègia}, m2m, transform)`. (El brief deia "19 peces de còpia";
  confirmat: `_spec()` retorna 19 entrades.)
- **4 estratègies de FK:** `MAP` (remapeig pk→pk per clau natural), `NULL` (FK a entitat de
  l'origen no viatja: `customer`, `updated_by`, `modified_by_id`), `DEFER` (auto-FK en 2a
  passada: `SizeSystem.parent`, `GradingRuleSet.parent_version`, `SizingProfile.parent_profile`),
  `NATURAL` (`TaskTimeEstimate.task_type` es re-resol per `code` — `TaskType` no es copia, neix sol).
- **Idempotència:** `update_or_create` per clau natural, mai `delete`. Re-executable.
- **M2M** (`SizeSystem.targets`, `GarmentType.targets_recomanats`, `GradingRuleSet.targets`) es
  copien després de la 1a passada; auto-FK a la 2a (`_resolve_deferred`).
- **Tancament d'estat:** en acabar verd, `_close_onboarding()` (propaga `codi_global` al
  self-Customer, D7) + `client.estat='actiu'`, `onboarding_complet=True` (DC-6). Si una peça
  se salta → `ok=False`, tenant queda `onboarding`, surt amb codi != 0. **⇒ el bootstrap JA
  tanca onboarding→actiu; el hook de B3 no ha de fer-ho a part.**

**On tallar per introduir selecció (B2):** el loop de `handle()` itera sobre `_spec()`
(línia 287). El tall net és **filtrar la llista de `_spec()`** segons la selecció del perfil,
abans del loop. Res del motor de còpia canvia; només quines peces entren. Sense `--profile`:
`_spec()` sencer (comportament actual intacte).

## A2 · Granularitat de selecció + graf de dependències

Recompte real a `fhort` (per dimensionar les dues opcions i alimentar els comptadors de B4):

| Peça (`_spec`)        | files fhort | depèn de (selecció arrossega) |
|-----------------------|------------:|-------------------------------|
| BodyMeasurementISO    |     0 | — (buit a fhort) |
| POMCategory           |    28 | — |
| GarmentGroup          |    11 | — |
| Target                |    13 | — |
| FitType               |    10 | — |
| ConstructionType      |     4 | — |
| POMGlobal             |   125 | — |
| GarmentTypeGlobal     |    59 | — |
| SizeSystem            |    20 | Target (M2M) |
| SizeDefinition        |   120 | SizeSystem |
| GarmentType           |    19 | GarmentGroup, Target (M2M) |
| POMMaster             |   217 | POMGlobal |
| GarmentTypeItem       |    57 | GarmentType |
| GarmentPOMMap         | 1.529 | GarmentTypeItem, POMMaster |
| GradingRuleSet ⚠️     |    25 | GarmentGroup, SizeSystem, Target |
| GradingRule ⚠️        |   707 | GradingRuleSet, POM |
| SizingProfile         |    26 | Target, GarmentType, ConstructionType, FitType, SizeSystem |
| TaskTimeEstimate      |   460 | GarmentTypeItem, (TaskType natural) |
| TimeSeed              |     8 | — (`updated_by`→NULL) |

**Graf de dependències DE SELECCIÓ** (agrupant per blocs coherents; una casella arrossega les de
sota seu):

```
[Catàlegs base]  BodyMeasurementISO · POMCategory · GarmentGroup · Target · FitType ·
                 ConstructionType · POMGlobal · GarmentTypeGlobal      (fulla, barats, fonament)
      │
      ├─[Size systems]     SizeSystem → SizeDefinition          (arrossega Target)
      ├─[Garments]         GarmentType → GarmentTypeItem         (arrossega GarmentGroup, Target)
      ├─[POM masters]      POMMaster → GarmentPOMMap             (arrossega POMGlobal, GarmentTypeItem)
      ├─[Sizing profiles]  SizingProfile                        (arrossega Garments + Size systems + fulla)
      ├─[Time seeds]       TaskTimeEstimate · TimeSeed          (arrossega GarmentTypeItem)
      └─[Grading] ⚠️       GradingRuleSet → GradingRule         (arrossega GarmentGroup, SizeSystem, POM)
                           GATED per A3 (origen classificat)
```

**Opció (a) — per TIPUS d'entitat (blocs).** ~7 caselles. UI simple; consistència garantida pel
graf (marcar "POM masters" força "Catàlegs base"; marcar "Grading" força tot el que penja).
Cost d'implementació baix: filtrar `_spec()` + un mapa bloc→peces amb clausura transitiva.

**Opció (b) — per REGISTRE concret** (aquest GarmentType sí, aquell no). Cost d'UI alt (57 items,
217 POMMasters, 1.529 maps…) i **risc de consistència**: seleccionar un `GarmentTypeItem` sense la
seva família `GarmentType`, o un `GarmentPOMMap` sense el seu `POMMaster`, trenca FKs. Exigiria
validació de subconjunt registre a registre — molt més motor.

**Recomanació (NO decideixo):** opció (a) per blocs. El Free canònic (REGLES §4: GTI, size systems
ISO, grading estàndard, POMs bàsics) és una tria de *què* de catàleg, no de *quins registres*. La
granularitat per registre és producte d'un altre sprint si mai cal. ⇒ **decisió d'Agus.**

## A3 · Grading al flux automàtic (llei RUN-CLIENT)
- `GradingRuleSet.origen` ∈ {`CANONICAL` (viatja), `CLIENT_RUN` (MAI viatja), `IMPORT`, `NULL`=no
  classificat}. El backfill és `manage.py set_grading_origen` (decisió humana).
- **BD real a `fhort`: 25/25 rulesets amb `origen = NULL`.** Cap classificat.
- **`bootstrap_tenant` ACTUAL copia GradingRuleSet/GradingRule SENSE cap filtre d'`origen`** →
  avui una còpia arrossegaria els 25 NULL (i qualsevol CLIENT_RUN futur) a un tercer. Amb el
  tenant fhort intern no és fuga, però com a **hook automàtic cap a tercers és una violació
  RUN-CLIENT latent.**
- **Condició d'activació del grading al flux Free (a escriure a B2):** el perfil només sembra
  grading si (1) el perfil ho demana **I** (2) hi ha rulesets amb `origen='CANONICAL'`; filtre
  `origen != CLIENT_RUN` (i mai NULL). Si el perfil demana grading i tot és NULL → **error clar,
  0 rulesets copiats** (mai còpia silenciosa). **Avui, amb 25 NULL, el Free NO pot dur grading
  fins que Agus corri `set_grading_origen`.**

## A4 · Hook d'alta
[backoffice/views_tenants.py:56](../../backend/fhort/backoffice/views_tenants.py#L56) `ClientViewSet.create`:
- Avui: `serializer.save()` (provisiona schema, FORA de `transaction.atomic` — patró django-tenants)
  → crea `Domain` → `BackofficeActionLog(accio='client.create')` → 201. **Cap sembra, cap admin.**
- **Com sap que és Free:** `Client.plan` és FK a `Plan` (`null=True, blank=True`).
  **⚠️ BLOCADOR DE COORDINACIÓ (F1):**
  - **No existeix cap `Plan` a la BD** (0 files; F1 encara no ha sembrat el catàleg).
  - **`Plan.NOM_CHOICES` = Solo/Studio/Brand/Enterprise — NO hi ha "Free".** El "Free" viu avui
    només com a `FREE_TIER` hardcoded a
    [pricing_service.py:30](../../backend/fhort/backoffice/pricing_service.py#L30), no com a entitat `Plan`.
  - `ClientCreateSerializer` té **`plan: required=True`** → avui l'alta ni tan sols es pot fer
    sense un Plan, que no existeix.
  - ⇒ **Cal decidir amb F1/Agus com es marca un tenant com a Free** (afegir `Plan` "Free" preu 0 /
    un flag `is_free` a Plan / conveni `plan IS NULL`=Free). `plan` és de F1: **STOP si cal tocar-lo.**
- **On penjar el llançament:** després de crear el `Domain` (el schema ja existeix i el host ja
  resol). Post-Domain, dins `create()`.
- **Report d'errors de sembra:** `BackofficeActionLog` (SHARED/public, ja usat per aquest ViewSet)
  és el Registre d'activitat. Cada pas (bootstrap, admin) hi escriu `accio='client.seed.*'` amb
  èxit/error a `detall`.

## A5 · `create_tenant_admin` + email de l'admin Free
[create_tenant_admin.py](../../backend/fhort/tasks/management/commands/create_tenant_admin.py) (99 l., `b08baaf`):
- Estat: **fet i verificat** (login real contra demo). `schema_context` des de public, força
  `rol_nom='admin'` post-signal, idempotent, aborta si schema=='public'. Contrasenya `--password`
  o generada amb `secrets`.
- **Email de l'admin (font a la fitxa del client):** candidats reals —
  - `Client.email_facturacio` (EmailField, es fixa a l'alta; `required=False` al serializer).
  - `TenantContacte.email` amb `principal=True` (però els contactes s'afegeixen DESPRÉS de l'alta,
    via acció separada `contactes` → **al moment del `create()` encara no n'hi ha cap**).
  - ⇒ **Recomanació (NO decideixo):** usar `email_facturacio` (present a l'alta); si buit →
    deixar l'admin per a un segon pas re-executable i registrar-ho, NO inventar email.
    **Decisió d'Agus (A5).**

---

## ⛔ STOP — decisions que necessito d'Agus abans de Patró B

1. **[A2] Granularitat de selecció:** per BLOCS de tipus (recomanat) o per registre concret?
2. **[A5] Email de l'admin Free:** `email_facturacio` de la fitxa (recomanat) o un altre camp?
3. **[A4 · BLOCADOR F1] Com es marca "Free":** avui no hi ha cap `Plan`, ni "Free" a `NOM_CHOICES`,
   i `plan` és territori F1. Cal el conveni (Plan "Free" preu 0 / flag / `plan IS NULL`) i, si
   toca `tenants`, coordinació amb F1 sobre l'ordre de migracions (la seva `0004` de tenants ja
   està al working tree, sense aplicar).
4. **[A3] Confirmació:** al Free, el grading NOMÉS s'activa amb `origen='CANONICAL'`; avui 25/25
   NULL ⇒ perfil de prova sense grading fins a `set_grading_origen`. ✅ o matís?

## Estat per al vault
- F3 P-FREE-SEED · Patró A COMPLET · STOP obert (4 decisions dalt). Cap fitxer escrit fora
  d'aquesta diagnosi. Territori F1 intacte.
- Fets durs: bootstrap=19 peces idempotents, ja tanca onboarding→actiu; grading 25/25 NULL
  (gate dur); **no hi ha Plan a la BD ni "Free" a NOM_CHOICES** (blocador de coordinació F1);
  admin email → `email_facturacio`.
