# DIAGNOSI — Neteja del catàleg de POMs (esborrat total + constraint + sembra de prova)

**Data:** 2026-08-08 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
**Abast:** dependències reals de `POMMaster` i `POMGlobal` als tres schemes, el model de prova
d'Agus, i l'ordre de buidat segur. **Cap escriptura, cap migració, cap restart.**

> **Convenció:** cada afirmació porta `fitxer:línia` o una consulta a la BD viva.
> **«NO EXISTEIX» = confirmat absent al codi**, no especulat.

---

## Resum executiu

1. 🛑 **El catàleg de POMs NO és una fulla, i el radi de l'esborrat és molt més gran que
   «el catàleg».** Els POMs de `fhort` sostenen **1.267 regles de graduació repartides en 45 dels
   46 `GradingRuleSet`** i **1.748 mapes de POM System sobre 55 ítems de peça**. Esborrar els POMs
   se'ls emporta tots. Això no és un efecte secundari a gestionar: **és la meitat del patrimoni
   tècnic del tenant**, i la decisió d'incloure-ho o no és d'Agus, no d'aquest tram.

2. ✅ **`los` i `public` estan NETS: no cal tocar-los.** `pom_pommaster` té **0 files** als dos.
   L'esborrat és, en dades, **un sol schema: `fhort`**. (La migració de la constraint sí que ha
   d'anar als tres, però això és estructura, no dades.)

3. 🔑 **`POMGlobal` viu DUES vegades i les dues còpies no diuen el mateix.** `public` en té **125**
   i `fhort` en té **274**, i **la FK del tenant apunta a la seva pròpia còpia**, no a la de
   `public` (`fhort.pom_pommaster.pom_global_id → fhort.pom_pomglobal`, verificat a
   `pg_constraint`). «Esborrar el catàleg global» i «esborrar el catàleg del tenant» són dues
   ordres diferents i cal dir quina és.

4. 🚨 **Dues dependències són INVISIBLES a una auditoria normal.** `models_app.SizeCheckLine.pom`
   i `fitting.PieceFittingLine.pom` són `PROTECT` amb `related_name='+'`: **no surten a
   `_meta.get_fields()`** i cal `include_hidden=True` per veure-les. Avui totes dues tenen 0 files,
   però un pla escrit a partir del mapa visible les hauria deixat fora.

5. ✅ **El model de prova d'Agus és `FTT-SS26-0001` (id 1319) i CONFIRMO que no té cap mesura**
   (`base_measurements = 0`). No bloqueja res. **No és ell qui reté POMs:** els 2 `POMPlacement`
   vius pengen d'un **esbós del catàleg** (`ItemFitxer` 14 → `garment_type_item` 30), no del model.

6. 🔑 **La constraint del camí 4 ja existeix… al codi, no a la BD.** `create_model_pom_view`
   (`fhort/pom/wizard_views.py:658`) ja fa `codi_client__iexact` i requalifica en cas de xoc: la
   semàntica demanada està escrita i provada, i la migració només l'ha de fer complir a la BD.

---

## BLOC 1 — El mapa de dependències de `POMMaster`

`POMMaster` es declara a `fhort/pom/models.py:379`; `codi_client` a `:394` — `max_length=30`,
**sense `unique`**. `POMMaster._meta.constraints` és `[]` i `unique_together` és `()` (verificat
per introspecció). **NO EXISTEIX cap unicitat de `codi_client` avui.**

`fhort.pom` viu **alhora a `SHARED_APPS` (`fhort/settings.py:55`) i a `TENANT_APPS` (`:68`)**: les
taules `pom_*` existeixen a **tots** els schemes, i cada FK és **local al seu schema** (verificat a
`pg_constraint`; cap FK creua schemes).

### 1.1 · Les 18 taules que referencien `POMMaster`, amb files a `fhort`

| # | Taula | `on_delete` | `public` | `fhort` | `los` |
|---|---|---|---:|---:|---:|
| 1 | `pom_garmentpommap` | **PROTECT** | 0 | **1.748** | 0 |
| 2 | `pom_gradingrule` | **PROTECT** | 0 | **1.267** | 0 |
| 3 | `pom_customerpomalias` | CASCADE | 0 | **390** | 0 |
| 4 | `pom_itembasemeasurement` | **PROTECT** | 0 | **37** | 0 |
| 5 | `pom_clientmesuraperfil` | **PROTECT** | 0 | **20** | 0 |
| 6 | `models_app_pomplacement` | **PROTECT** | — | **2** | 0 |
| 7 | `pom_pomestadisticatenant` | CASCADE | 0 | 0 | 0 |
| 8 | `pom_garmenttypepommap` | **PROTECT** | 0 | 0 | 0 |
| 9 | `pom_garmentgrouppommap` | **PROTECT** | 0 | 0 | 0 |
| 10 | `models_app_basemeasurement` | **PROTECT** | — | 0 | 0 |
| 11 | `models_app_measurementchangelog` | **PROTECT** | — | 0 | 0 |
| 12 | `models_app_modelgradingoverride` | **PROTECT** | — | 0 | 0 |
| 13 | `models_app_modelgradingrule` | **PROTECT** | — | 0 | 0 |
| 14 | 🚨 `models_app_sizecheckline` | **PROTECT** · `related_name='+'` | — | 0 | 0 |
| 15 | `fitting_pomalert` | **PROTECT** | — | 0 | 0 |
| 16 | `fitting_gradedspec` | **PROTECT** | — | 0 | 0 |
| 17 | 🚨 `fitting_piecefittingline` | **PROTECT** · `related_name='+'` | — | 0 | 0 |
| 18 | `patterns_patternpom` | **PROTECT** | — | 0 | 0 |

`—` = la taula **no existeix** en aquell schema (`models_app`, `fitting` i `patterns` són
TENANT-only). Les files són recompte real a la BD d'avui.

🚨 **Les files 14 i 17 no surten a `_meta.get_fields()`.** `models_app/models.py:1266`
(`SizeCheckLine`) i `fitting/models.py:402` (`PieceFittingLine`) declaren el FK amb
`related_name='+'`, que amaga la relació inversa. Només apareixen amb
`_meta.get_fields(include_hidden=True)`. **Django les fa complir igualment** (`PROTECT` és del
col·lector, no de l'accessor): amb una sola fila, el `delete()` peta amb `ProtectedError` i el
missatge no dirà d'on ve si no s'ha censat abans.

### 1.2 · `POMGlobal` — només 3 dependents, i cap és bloquejant

`fhort/pom/models.py:9`. Referenciada per `pom_pomestadisticaglobal` (CASCADE, **0 files** als 3),
`pom_pommaster.pom_global` (**SET_NULL**, `:380`) i `pom_gradingrulehistory.pom` (**SET_NULL**,
`:1819`; **0 files** als 3).

🔑 **Cap `PROTECT`:** esborrar `POMGlobal` no es bloqueja mai — **buida els `pom_global_id` en
silenci**. Si l'ordre de buidat el posés abans que `POMMaster`, els POMs es quedarien vius i
desvinculats sense que res avisés.

### 1.3 · Una divergència estructural a `public` (inert, però anotada)

`public.pom_gradingrule.pom_id` apunta a **`public.pom_pomglobal`**, mentre a `fhort` i `los`
apunta a **`pom_pommaster`**. Les dues taules de `public` tenen 0 files, o sigui que avui no fa
mal, però és una asimetria real entre schemes que una migració futura sobre `pom_gradingrule`
hauria de tenir present.

**Veredicte BLOC 1: llest.** El mapa és complet i verificat contra `pg_constraint`, no contra el
codi sol.

---

## BLOC 2 — Què cau de veritat quan cauen els POMs

Les 6 taules amb files (§1.1) no són «residus del catàleg». Són això:

| Què | Files | Traducció |
|---|---:|---|
| `GarmentPOMMap` (`pom/models.py:809`) | **1.748** | **Els POM Systems sencers** — 55 ítems de peça, en 4 nivells (O=785 · M=424 · D=314 · K=225). Recordatori: «POM System» és el rètol de pantalla sobre aquesta taula |
| `GradingRule` (`:1445`) | **1.267** | **La llibreria de graduació** — **45 dels 46 `GradingRuleSet` es queden sense cap regla** |
| `CustomerPOMAlias` (`:471`) | **390** | Els catàlegs **de client** (CASCADE: cauen sols, sense avisar) |
| `ItemBaseMeasurement` (`:1171`) | **37** | Les mesures base plantilla d'**1** `ItemBaseSet` |
| `ClientMesuraPerfil` (`:1533`) | **20** | L'acumulat estadístic per client/peça/POM/talla (Welford) |
| `POMPlacement` (`models_app/models.py:1424`) | **2** | **Cotes dibuixades** sobre `ItemFitxer` 14 (`garment_type_item` 30) |

🛑 **Aquesta és la troballa que cal decidir abans de tocar res.** El brief diu «el catàleg actual
és brut i condemnat — es re-entrarà depurat més endavant». Això és cert del catàleg; **no és cert
de les 1.267 regles ni dels 1.748 mapes**, que no són bruts i no hi ha cap pla de re-entrada.

**💡 PROPOSTA (a validar) — tres abasts possibles, i el preu de cadascun:**

* **A · Terra cremada** — cau tot el de la taula. El catàleg queda net de debò i les pantalles de
  Fase A es validen contra 12 POMs perfectes. **Preu:** la llibreria de graduació i els POM Systems
  desapareixen; F2.3 i qualsevol QA de graduació es queden sense substrat.
* **B · Catàleg net, patrimoni conservat** — es conserven els POMs que sostenen regles o mapes
  (`pom_id` present a `GradingRule` o `GarmentPOMMap`) i es purga la resta. **Preu:** el catàleg
  NO queda net —conviuen ZZ-TEST i supervivents— i els 12 duplicats podrien sobreviure, cosa que
  bloquejaria la constraint del punt 3.
* **C · Terra cremada + re-sembra del patrimoni** — A, més tornar a sembrar regles i mapes sobre
  els ZZ-TEST. **Preu:** és un tram sencer de feina, no una coda.

Aquest document no en tria cap: és decisió d'Agus (Patró C).

**Veredicte BLOC 2: cal decisió d'abast abans de la Fase 2.**

---

## BLOC 3 — El model de prova d'Agus

**`FTT-SS26-0001` · «Pantalo test» · id 1319** — l'**únic** `Model` de `fhort` (`Model.objects
.count() == 1`). Fase `Pending`, client id 1.

* ✅ **`base_measurements` = 0** — **CONFIRMAT: no té mesures.** El brief demanava confirmar-ho i
  reportar si en tenia. No en té.
* `size_fittings` = 1 (el `SizeFitting` que el signal de creació del model dispara). No referencia
  cap POM: `SizeFitting` no surt a la taula de §1.1.
* **No reté cap POM.** Cap de les 18 taules dependents té files lligades a aquest model.

🔑 **Els 2 `POMPlacement` NO són seus.** Pengen d'`ItemFitxer` **14**, que és de
`garment_type_item` **30** — un esbós del **catàleg de peces**. Els POMs que retenen són
**`D1-M76`** (id 379) i **`AH DEP`** (id 284). Són cotes de catàleg, i el brief no les esmenta.

**Veredicte BLOC 3: llest.** El model de prova és segur i no cal tocar-lo.

---

## BLOC 4 — Estat de brutícia (línia base abans/després)

Verificat sobre `fhort` avui:

| Mesura | Valor |
|---|---|
| `POMMaster` totals · actius | **396** · 380 |
| **Codis duplicats** (case-insensitive) | **12 claus × 2 files = 24 files** — `U1 D J1 BJ C1 L1 S2 E4 H U E7 S` |
| Sense `pom_global` (**«no lligat»**) | **122** |
| Amb `pom_global` però descripcions BUIDES (**«lligat sense informar»**) | **149** |
| Amb `pom_global` i text (**«dada»**) | **125** |
| → **sense «com es mesura»** | **271 / 396 = 68,4 %** ✅ coincideix amb el 68 % del brief |
| `POMCategory` | **28**, de les quals **7 noms duplicats** (14 files): TANCAMENT/DETALL, ESPECÍFIC DE PUNT, COLL/ESCOT, MÀNIGA, PART SUPERIOR DEL COS, ESPECÍFIC DE BANY, PART INFERIOR DEL COS |
| POMs **sense categoria** | **219 / 396 = 55 %** |
| `CustomerPOMAlias` | **390** |

🔑 **Els 125 «amb text» són exactament les 125 files de `public.pom_pomglobal`.** Coincidència
que val la pena confirmar a la Fase 2: suggereix que el «com es mesura» ple només existeix on la
còpia del tenant reflecteix el catàleg canònic, i que les altres 149 són còpies locals buides.

**Veredicte BLOC 4: llest.** Els tres estats de la fitxa (dada / no lligat / lligat sense
informar) són exercitables avui i tenen població suficient per contrastar la sembra.

---

## BLOC 5 — La constraint (punt 3 del brief)

**La semàntica demanada ja està escrita al camí 4.** `create_model_pom_view`
(`fhort/pom/wizard_views.py:596`) fa, a `:658`:

```python
if POMMaster.objects.filter(codi_client__iexact=codi_casa).exists():
    codi_casa = f'{cust}-{codi}'[:30] if cust else f'M{model_id}-{codi}'[:30]
```

…i el seu propi comentari diu que copiar el codi del client «és exactament el que va fabricar els
12 duplicats de `POMMaster.codi_client` que hi ha avui». O sigui: **case-insensitive, per schema
(= per tenant)**, que és el que el brief demana.

**💡 PROPOSTA (a validar)** — `UniqueConstraint(Upper(Trim('codi_client')), name='uniq_pommaster_codi_client_ci')`
a `pom/migrations/0075_*` (l'última és `0074_fittype_choices_al_dia.py`). Notes:

* L'expressió amb `Upper()` crea un **índex funcional**; PostgreSQL 16.14 la suporta.
* ⚠️ `Trim` només si es decideix que l'espai sobrant no distingeix. `codi_client` **no té
  `blank=True`** però tampoc `unique`: cal decidir si `''` compta com a valor (si n'hi ha dos de
  buits, la constraint els rebutja). Avui no n'hi ha cap de buit, però la sembra i l'import
  podrien crear-ne.
* L'ordre correcte és **esborrar primer i afegir la constraint després**: amb les 24 files
  duplicades vives la migració fallaria.
* La constraint va **als tres schemes** amb `migrate_schemas` (mai `--schema`, CLAUDE.md), i
  s'audita amb SQL directe a la BD — `migrate_schemas` pot donar un OK enganyós.

**Segona troballa, fora d'abast però anotada:** `CustomerPOMAlias` ja té
`UniqueConstraint(customer, client_code)` (`uniq_customer_client_code`) però és
**case-SENSITIVE** — `u1` i `U1` hi poden conviure per al mateix client. És la mateixa classe de
forat que el brief tanca per a `POMMaster`. No el toco.

**Veredicte BLOC 5: llest per implementar**, amb dues decisions petites obertes (`Trim` sí/no,
buits sí/no).

---

## BLOC 6 — Ordre de buidat segur

**Regla:** primer els `CASCADE`/`SET_NULL` amagats, després els `PROTECT` de baix a dalt, i
`POMMaster` **abans** que `POMGlobal` (perquè el `SET_NULL` de `:380` no desvinculi en silenci).

**Només a `fhort`** (a `public` i `los` no hi ha res a esborrar; només hi va la migració).

| Ordre | Taula | Files | Nota |
|---|---|---:|---|
| 1 | `models_app_pomplacement` | 2 | PROTECT. Cotes de l'`ItemFitxer` 14 — **fora d'abast del brief**, cal vistiplau |
| 2 | `pom_clientmesuraperfil` | 20 | PROTECT. Acumulat estadístic |
| 3 | `pom_itembasemeasurement` | 37 | PROTECT. Deixa 1 `ItemBaseSet` buit (el set **no** s'esborra) |
| 4 | `pom_gradingrule` | 1.267 | PROTECT. **Deixa 45/46 `GradingRuleSet` buits** (els sets **no** s'esborren) |
| 5 | `pom_garmentpommap` | 1.748 | PROTECT. **Buida els POM Systems de 55 ítems** |
| 6 | `pom_garmenttypepommap` · `pom_garmentgrouppommap` | 0 | PROTECT, buides — s'inclouen per completesa |
| 7 | `pom_customerpomalias` | 390 | CASCADE — cauria sol; **millor esborrar-lo explícitament** i comptar-lo |
| 8 | `pom_pomestadisticatenant` | 0 | CASCADE |
| 9 | **`pom_pommaster`** | **396** | El catàleg |
| 10 | `pom_pomglobal` (fhort) | 274 | ⚠️ **Només si l'abast inclou la còpia del tenant.** V. §6.2 |
| 11 | `pom_pomcategory` | 28 | SET_NULL des de POMMaster; segur un cop no hi ha POMs |

Les 8 taules restants de §1.1 (`basemeasurement`, `measurementchangelog`, `modelgradingoverride`,
`modelgradingrule`, `sizecheckline`, `pomalert`, `gradedspec`, `piecefittingline`,
`patterns_patternpom`) tenen **0 files**: no cal esborrar-les, però **el guió n'ha de comptar les
files abans i després** — són les que farien saltar un `ProtectedError` si algú crea dades entre
la diagnosi i l'execució.

### 6.1 · QUÈ NO S'ESBORRA

* ✅ **El model `FTT-SS26-0001` (1319) i el seu `SizeFitting`.**
* ✅ **Els 46 `GradingRuleSet`** — es queden buits, no s'esborren (són la definició dels jocs:
  nom, eixos, `size_system`).
* ✅ **L'`ItemBaseSet`** — es queda buit.
* ✅ **`GarmentType` / `GarmentTypeItem` / `GarmentGroup`** — el catàleg de peces no es toca; només
  els seus mapes de POM.
* ✅ **`public.pom_pomglobal` (125 files)** — és el catàleg canònic de la casa i el brief no el
  condemna. **Ni `los` ni `public` es toquen en dades.**
* ✅ `SizeSystem`, `SizeDefinition`, `Target`/`ConstructionType`/`FitType`, `MeasurementLayer`,
  `Customer` — cap referencia POMs.

### 6.2 · La pregunta que el brief no respon

**`fhort.pom_pomglobal` (274 files): cau o es queda?**

* **Si cau:** el catàleg del tenant queda net del tot, i la sembra ha de crear també els POMGlobal
  dels ZZ-TEST (amb el «com es mesura» ple) perquè els tres estats siguin exercitables.
* **Si es queda:** els 396 POMMaster desapareixen però queden **274 POMGlobal orfes** al tenant,
  dels quals 149 amb les descripcions buides — soroll dins de la mateixa pantalla que s'està
  netejant.

**💡 PROPOSTA (a validar):** que caigui, i que la sembra creï els seus propis POMGlobal. És
l'única lectura coherent amb «les pantalles es validen contra dades NETES i mínimes».

**Veredicte BLOC 6: llest**, condicionat a §6.2 i a l'abast de §BLOC 2.

---

## BLOC 7 — Preparatius de la Fase 2 (verificats, no executats)

* `pg_dump` **16.14** disponible a `/usr/bin/pg_dump`. Directori de la casa:
  `ops/backups/` (3 dumps previs, patró `PRE-<TRAM>_<DATA>.dump`).
* **Disc: 15 G lliures de 75 G (80 % ocupat).** Els dumps previs fan 0,9–1,6 MB: sense risc.
* Última migració de `pom`: **`0074_fittype_choices_al_dia.py`** → la nova seria `0075`.
* ⚠️ **`migrate_schemas --list` PROHIBIT** en diagnosi (no és read-only en aquesta versió).
* ⚠️ Recordatori de la casa: esborrar i fer `ALTER TABLE` **a la mateixa transacció** dona
  *pending trigger events* — la constraint ha d'anar en una migració **separada** de l'esborrat.

---

## TAULA FINAL — riscos per al CTO

| # | Risc | Gravetat | Estat |
|---|---|---|---|
| 1 | **1.267 regles i 1.748 mapes cauen amb els POMs**; 45/46 rulesets queden buits | 🔴 **BLOQUEJANT** | Decisió d'abast (BLOC 2) |
| 2 | **`fhort.pom_pomglobal` (274)**: el brief no diu si cau | 🟠 Alt | Decisió (§6.2) |
| 3 | **2 `POMPlacement`** (cotes de catàleg, no del model de prova) s'han d'esborrar per desbloquejar 2 POMs | 🟠 Alt | Fora d'abast del brief; cal vistiplau |
| 4 | **2 dependències `PROTECT` invisibles** (`SizeCheckLine`, `PieceFittingLine`) | 🟡 Mitjà | Censades; 0 files avui. Re-comprovar just abans d'executar |
| 5 | 20 `ClientMesuraPerfil` (acumulat Welford) es perden | 🟡 Mitjà | Anotat |
| 6 | `CustomerPOMAlias` cau per **CASCADE**, sense avís | 🟡 Mitjà | Esborrar-lo explícitament per poder-lo comptar |
| 7 | Divergència de FK a `public.pom_gradingrule` (→ `pom_pomglobal`) | 🟢 Baix | Inert (0 files). Anotat |
| 8 | `CustomerPOMAlias.uniq_customer_client_code` és **case-sensitive** | 🟢 Baix | Fora d'abast. Anotat |
| 9 | Disc al 80 % | 🟢 Baix | 15 G lliures; dumps de ~1,5 MB |

---

## 🛑 STOP — Cap escriptura feta

**Tres respostes desbloquegen la Fase 2:**

1. **Abast (BLOC 2):** A (terra cremada, s'emporta graduació i POM Systems) · B (conservar el que
   sosté patrimoni) · C (terra cremada + re-sembra del patrimoni)?
2. **`fhort.pom_pomglobal` (274 files):** cau o es queda?
3. **Els 2 `POMPlacement`** de l'esbós del catàleg: autoritzats a caure?
