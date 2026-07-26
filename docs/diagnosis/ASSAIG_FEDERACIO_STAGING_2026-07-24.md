# ASSAIG INTEGRAL — Federació v2 a staging (pre-runbook PROD)

Data d'execució: 2026-07-23 · Entorn: STAGING (`/var/www/ftt-staging`, branca `dev` ≡ `origin/dev`).
Tipus: **verificació end-to-end**, cap canvi de codi. Les 4 peces (P1 TenantLink · P2 Model.origen ·
P3 instanciació EXTERN · P4 actor a la meritació) ja són a `origin/dev` (HEAD ≡ origin/dev, 0/0).

> Convenció: cada pas porta la comanda i la sortida REAL. `codi_intern` de l'assaig = namespace
> `LOS-ASSAIG-*` (sintètic, anotat, no cal netejar). Veredicte final: **GO / NO-GO** per a PROD.

---

## Context previ que condiciona l'assaig (llegir abans)

- El brief demanava poblar el Brand `los` amb `seed_losan_models --schema los`. **`los` no té catàleg**
  (0 GarmentType / GTI / SizeSystem / GradingRuleSet; només el self-Customer LOS) → el seed real no hi
  resol config.
- A més, els **962 models LOSAN ja viuen a `fhort`** (el Studio), no a `los` (Bandera 8 de la diagnosi).
  El CSV de `seed_losan_models` (SS27, `LOS-SS27-*`) **col·lisionaria** amb aquests 962 → la instanciació
  els saltaria tots i no provaria la CREACIÓ.
- **Decisió d'assaig (documentada):** seed SINTÈTIC controlat de 50 models a `los`, namespace
  `LOS-ASSAIG-*` (sense col·lisió), amb catàleg mirall i 3 cubells de config per exercir totes les
  branques. És l'"equivalent" que el brief autoritzava. A PROD, `los` SÍ tindrà catàleg i models propis:
  la cadena provada aquí és idèntica; només canvia l'origen de les dades.

---

## Pas 1 — POBLAR EL BRAND (los)

Seed sintètic (script `shell`): catàleg mirall a `los` + 50 models `LOS-ASSAIG-0001..0050`, customer LOS,
SS/2027, sequencial 5001-5050. Tres cubells de config:
- **A (20)** — `size_system=ALPHA_EU_W` + `garment_type_item=BUTTONED_TOPS/shirt_woven`: claus naturals
  que **existeixen a fhort** → han de RESOLDRE a la instanciació.
- **B (10)** — `size_system=SYS-ONLY-LOS`: clau natural que **NO existeix a fhort** → unmatched (NULL).
- **C (20)** — sense config.

```
LOS catalog: gt/gti/ss_match/ss_only ok
models creats: 50 · total ASSAIG: 50
  bucket A (config fhort): 20
  bucket B (config only-LOS): 10
  bucket C (sense config): 20
```
**Veredicte pas 1: OK** — Brand poblat amb config parcial (mirall de PROD 381/961).

---

## Pas 2 — DRY-RUN

```
manage.py instantiate_external_models --brand LOS --studio FTT

[DRY-RUN] instantiate_external_models LOS → FTT
  llegits del Brand : 50
  a crear          : 50
  saltats (ja hi són): 0
  config NO aparellada: 10 referència/es (el model es crea amb el camp NULL)
    · size_system: 1 → SYS-ONLY-LOS
  (DRY-RUN: no s'ha escrit res. Afegeix --commit per crear.)
```
**Veredicte pas 2: OK** — 50 a crear, 10 unmatched (el codi concret `SYS-ONLY-LOS`), 0 escrits.

---

## Pas 3 — COMMIT + auditoria

```
manage.py instantiate_external_models --brand LOS --studio FTT --commit
  llegits del Brand : 50 · creats: 50 · saltats: 0 · config NO aparellada: 10 (SYS-ONLY-LOS)
  Fet: 50 models EXTERN creats al Studio FTT.
```

**Terra de seqüència LOS a fhort — ABANS i DESPRÉS del bolcat:**
```
BASELINE _real_max_seq(LOS,2027,SS) = 962
DESPRÉS  _real_max_seq(LOS,2027,SS) = 962   ← INTACTE
```

**Auditoria a BD (fhort):**
```
n_extern=50 · custs=1 (LOS) · minseq=5001 · maxseq=5050
amb_config(size_system)=20 · sense_config=30      (30 = 10 unmatched B + 20 sense config C)
sfs_creades=50                                     (SizeFitting per cada EXTERN — signal disparat)
LOS-ASSAIG-0001 EXTERN LOS 5001 ALPHA_EU_W         (bucket A: config resolta contra el catàleg de fhort)
```
**Veredicte pas 3: OK** — 50 EXTERN (customer=LOS, codi i sequencial conservats, origen=EXTERN), 20 amb
config resolta per clau natural, 30 amb NULL, 50 SizeFitting. **El terra local no es mou (962→962).**

---

## Pas 4 — IDEMPOTÈNCIA

```
manage.py instantiate_external_models --brand LOS --studio FTT --commit
  llegits del Brand : 50 · creats: 0 · saltats (ja hi són): 50 · config NO aparellada: 0
  Fet: 0 models EXTERN creats al Studio FTT.
total LOS-ASSAIG a fhort = 50
```
**Veredicte pas 4: OK** — segona passada: 0 creats, 50 saltats, cap duplicat.

---

## Pas 5 — TASCA SOBRE UN EXTERN (meritació amb ACTOR)

`transition_task(task, 'InProgress', profile)` sobre una ModelTask nova de `LOS-ASSAIG-0001` (fhort):
```
model origen: EXTERN · customer: LOS · consumption_started_at (abans): None
--- DESPRÉS de transition_task → InProgress ---
a. model.consumption_started_at: 2026-07-23 07:23:29+00:00        ✔
b. ConsumptionRecord a fhort: True · opaque_ref: 019e4a2f-d0ce-…   ✔
c. Event a public: True · codi_client: LOS · actor_schema: fhort · period: 2026-07   ✔
```
**Veredicte pas 5: OK** — la triple escriptura funciona sobre un EXTERN. **La signatura de la federació
és exacta: `codi_client=LOS` (de qui és el model) però `actor_schema=fhort` (qui l'ha meritat).** L'actor
divergeix del client, que és tot el sentit de P4.

---

## Pas 6 — TOKEN (el pont es governa, la feina no)

```
6.a  link.aturar() → estat: ATURAT
     manage.py instantiate_external_models --brand LOS --studio FTT
     CommandError: El TenantLink LOS↔FTT no és ACTIU (estat=ATURAT). El pont està tancat.   ✔

6.b  (vincle encara ATURAT) feina local a fhort sobre la tasca del pas 5:
     estat tasca abans: InProgress → Paused → InProgress                                     ✔
     OK: la feina local no depèn del pont

     link.reactivar() → estat: ACTIU · aturat_at: None · token intacte: True
     events LOS a public (total): 10   ← +1 respecte dels 9 històrics; el pause/resume NO re-merita
```
**Veredicte pas 6: OK** — amb el pont ATURAT la instanciació falla en dur, però l'Studio segueix
treballant amb la tasca sense cap error i **sense re-meritar** (guard `consumption_started_at`). Token
intacte en reactivar.

---

## Pas 7 — UI SMOKE + integritat de seqüència

```
curl /api/schema/            → 200   (servei viu)
curl /api/v1/models/         → 401   (existeix, protegit)
curl /api/auth/central/ (GET)→ 405   (existeix, POST-only: login únic)
```

**Seqüència — el wizard/bulk NO es contamina pels EXTERN:**
```
FTT: sequence_floor(2027,SS)=0   → proper INTERN via bulk = 1     (FTT no té EXTERN: net)
LOS: sequence_floor(2027,SS)=962 → proper INTERN via bulk = 963   (els 50 EXTERN 5001-5050 EXCLOSOS)
```
**Veredicte pas 7: OK per al camí bulk** — el `reserve_sequence_range`/`sequence_floor` (P2) ignora els
EXTERN: un nou INTERN de LOS a fhort seria 963, no 5051.

> ⚠️ **RESIDUAL CONEGUT (P2) — el camí del SIGNAL no exclou EXTERN:**
> ```
> LOS raw MAX signal (inclou EXTERN)=5050 · MAX exclòs EXTERN=962
> ```
> El signal `generate_model_code` (`models_app/signals.py:60-66`) fa `MAX(sequencial)` cru **sense
> excloure EXTERN** — el brief de P2 va manar explícitament no tocar-lo. Un model INTERN creat pel camí
> d'UN de sol (wizard sense codi imposat) per al **mateix customer** que té EXTERN agafaria 5051.
> **Abast real:** només afecta crear un INTERN nou per a un customer-Brand DES DEL Studio; al flux normal
> de federació l'Studio NO encunya els models INTERN d'un Brand (el Brand encunya els seus). Latent, no
> actiu — però és una vora del runbook.

---

## VEREDICTE GLOBAL: **GO** (amb 1 guardrail)

| Pas | Resultat |
|---|---|
| 1 Poblar Brand | ✅ (seed sintètic documentat) |
| 2 Dry-run | ✅ |
| 3 Commit + terra intacte | ✅ 962→962 |
| 4 Idempotència | ✅ 0/50 |
| 5 Meritació amb actor | ✅ actor=fhort ≠ client=LOS |
| 6 Token governa el pont | ✅ error dur + feina local intacta |
| 7 UI + seqüència bulk | ✅ / ⚠️ residual signal |

**GO per a PROD divendres**, amb el guardrail següent al runbook:

1. **No encunyar models INTERN d'un customer-Brand des del Studio pel camí d'un-de-sol (wizard)** mentre
   existeixin EXTERN d'aquell customer, o el `sequencial` saltaria a l'espai del Brand (residual del
   signal, pas 7). El camí bulk és net. Fix futur trivial si es vol tancar: afegir `AND origen<>'EXTERN'`
   a les dues queries de `signals.py:60-66` (fora de l'abast de P1-P4 per decisió del brief de P2).

### Sorpreses / desviacions respecte al brief
- **El Brand `los` era buit** (no els "962 sintètics" del brief): confirma la diagnosi (Bandera 8), no la
  contradiu. Es va seed-ejar sintèticament amb namespace propi per no col·lisionar amb els 962 de fhort.
- **GradingRuleSet no s'inclou als cubells de config** (creació amb molts camps obligatoris, fràgil per a
  un assaig): la resolució de GRS comparteix el mateix mecanisme de clau natural que `size_system`
  (provat als tests unitaris de P3) — `size_system` fa de representant aquí.

### Estat en què queda staging (conegut)
- **Vincle `TenantLink` LOS↔FTT: ACTIU** (token intacte).
- Dades sintètiques d'assaig (anotades, no cal netejar): 50 `LOS-ASSAIG-*` a `los` (INTERN) i els seus 50
  EXTERN a `fhort` + 50 SizeFitting; 1 ModelTask InProgress + 1 ConsumptionRecord a `fhort`; 1
  ModelConsumptionEvent nou a `public` (`codi_client=LOS`, `actor_schema=fhort`); catàleg mirall a `los`
  (`ALPHA_EU_W`, `SYS-ONLY-LOS`, `BUTTONED_TOPS/shirt_woven`).
- Els 962 models LOSAN reals segueixen a `fhort`; res d'històric tocat.
