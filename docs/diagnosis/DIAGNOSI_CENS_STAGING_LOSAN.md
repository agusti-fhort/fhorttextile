# DIAGNOSI — cens BD de STAGING (mirall de PROD per a l'assaig onboarding LOSAN)

Data: 2026-07-17 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

Retrat equivalent al de `DIAGNOSI_CAPACITAT_ONBOARDING_LOSAN.md` (que es va córrer per error sobre
PROD), per saber si staging és mirall prou fidel per a l'assaig. **Cens BD només** (no els 6
investigadors). Convenció: `fitxer:línia` o el SELECT/ORM que ha donat el fet; "NO EXISTEIX" =
confirmat absent.

> **READ-ONLY absolut**: totes les dades surten de SELECT/ORM dins `schema_context('fhort')` o de la
> introspecció de `pg_namespace`/`information_schema`. Cap escriptura, cap migració, cap restart.

---

## §0 — Verificació d'entorn i divergències

| Comprovació | Esperat (brief) | Real staging | ✓/✗ |
|---|---|---|---|
| Servidor | 178.105.48.204 | `178.105.48.204` (hostname -I) | ✓ |
| Tree | /var/www/ftt-staging/backend | `/var/www/ftt-staging/backend` | ✓ |
| Branca | dev | `dev` | ✓ |
| Servei | ftt-staging.service :8001 | `active`, `bind 127.0.0.1:8001` | ✓ |
| PostgreSQL | PG18 a 5433 | server_version `180004`, PORT `5433`, HOST `127.0.0.1` | ✓ |
| BD | ftt_staging | `ftt_staging` | ✓ |
| Venv | …/venv/bin/python | usat per a tot el cens | ✓ |

**Divergències anotades:**

- **D-1 · Schema de tenant.** `pg_namespace` retorna només **`['fhort', 'public']`**. Staging té UN
  sol schema de tenant (`fhort`), no un per-tenant ni cap `los_*`. El dubte "tenant id=6 vs schema
  fhort" es resol així: **id=6 és el `Customer` LOS dins del schema `fhort`** (`tasks_customer`), NO
  un tenant/schema. El tenant és `Client id=2 · codi FTT · schema fhort` (`tenants_client`, public).
  Tot el negoci de LOSAN a staging viu com a **Customer del tenant FTT**, no com a tenant propi.
- **D-2 · git.** Les comissions de facturació (F-FACT-B1 + F-RECUR, el que el brief anomena "B1-B5")
  són **TOTES LOCALS, cap pushed**: `origin/dev..dev` = **16 commits**, `dev..origin/dev` = buit. Si
  PROD desplega des d'`origin/dev`, res d'aquest treball hi és. Arbre **brut** però només de fitxers
  d'estat fora de git (`DECISIONS.md` modificat) i diagnosis noves sense afegir — cap codi de producte
  descuidat.

---

## Cens — staging vs PROD, columna a columna

> Els valors de PROD són els que dóna el brief (de la diagnosi corrreguda per error sobre PROD). On el
> brief no en dóna, s'indica "no censat a PROD" — no s'ha llegit PROD en aquesta sessió.

### 1 · git

| | staging | PROD |
|---|---|---|
| branca actual | `dev` | (main, per la diagnosi PROD) |
| commits facturació | **16 locals, 0 pushed** (`origin/dev..dev`) | no censat a PROD |
| net/brut | brut: `DECISIONS.md` (fitxer d'estat, no-git) + diagnosis noves | — |

### 2 · Customer LOS (`tasks/models.py:194`)

| | staging | PROD |
|---|---|---|
| Customer LOS id | **6** (codi `LOS`, "LOSAN IBERIA SA") | no censat (brief no el dóna) |

Altres Customers a fhort: id=1 FTT, id=7 BRW.

### 3 · SizeSystem + SizeDefinition (`fhort.pom.SizeSystem`, camp `customer_codi` = text, no FK)

| | staging | PROD |
|---|---|---|
| SizeSystem total | **21** (16 canònics `customer_codi=''`, 4 LOS, 1 BRW) | no total al brief |
| GIRL_LOS_01 | **ss=48** (`customer_codi=LOS`, target GIRL) | ss=**44** |
| MAN_LOS_01 | **ss=51** (`customer_codi=LOS`, target MAN) | ss=**45** |
| altres LOS | ss=49 GIRL_LOS_02, ss=50 GIRL_LOS_03 (tots `LOS`, target GIRL) | no censat |
| SizeDefinition total | **125** (16 sistemes amb defs; ss LOS 48/49/50 = 9 c/u, 51 = 9) | no censat |

**⚠️ Els ids LOS de staging NO coincideixen amb PROD** (48/51 vs 44/45). Els sistemes hi són i tenen
el mateix `codi` i target, però la pk difereix → qualsevol referència per pk entre entorns falla.

Canònics presents (mostra): ALPHA_EU_W (29), ALPHA_EU_M (30), NUMERIC_EU_W (32), BABY/TODDLER/KIDS/TEEN
(35/36/37/38), US (39/40). `base_size`/`talla_base`/`run` **NO EXISTEIXEN** com a camps de SizeSystem
(el model té `codi/nom/descripcio/actiu/base_unit/norma_ref/parent/customer_codi/targets`); la talla
base i el run viuen a un altre nivell (SizeDefinition/model).

### 4 · GarmentType / GarmentTypeItem / GarmentPOMMap / ItemBaseMeasurement

| | staging | PROD |
|---|---|---|
| GarmentType | **19** (BOTTOMS 3, DRESSES 4, OUTERWEAR 2, SWIMWEAR 1, TOPS 7, UNDERWEAR 2) | no censat |
| ACCESSORIES (tipus) | **cap GarmentType** amb grup ACCESSORIES | brief pregunta → **no n'hi ha** |
| GarmentGroup (catàleg) | 11 grups, ACCESSORIES **sí** existeix com a grup buit | — |
| GarmentTypeItem | **57** | no censat |
| items amb 0 POMs | **2** (55 amb ≥1) | no censat |
| GarmentPOMMap | **1529** | no censat |
| **ItemBaseMeasurement** | **37** | **0** |

**⚠️ Divergència forta:** ItemBaseMeasurement **staging=37 vs PROD=0**. Staging té valors base d'item
sembrats que PROD no té. `grup` de GarmentType és un **CharField** (no FK a GarmentGroup): el grup
ACCESSORIES existeix al catàleg però cap tipus l'usa.

### 5 · GradingRuleSet (`fhort.pom.GradingRuleSet`)

| | staging | PROD |
|---|---|---|
| total | **27** (11 CANONICAL, 2 CLIENT_RUN, 14 origen NULL) | no total al brief |
| contenidors LOS | **grs=104 i grs=111** (ambdós `customer=6`, `origen=NULL`) | **95 / 96 / 99 / 101** origen NULL |

**⚠️ Divergència forta:** a staging hi ha **2** contenidors LOS (104 KidsKnit ss=50, 111 TopKnit ss=51);
a PROD n'hi ha **4** (95/96/99/101). Ni el nombre ni les pks coincideixen. Els 14 NULL de staging
inclouen els 2 LOS + IMPORTs + variants canòniques sense classificar (vegeu
`DIAGNOSI_GATE_SEMBRA_BYPASS_2026-07-17.md`).

### 6 · BaseMeasurement (`fhort.models_app.BaseMeasurement`)

| | staging | PROD |
|---|---|---|
| files | **535** | **299** |
| models afectats | **18** | **12** |

**⚠️ Staging té MÉS mesures que PROD** (535/18 vs 299/12): és un entorn més treballat, no un subconjunt.

### 7 · Usuaris del tenant (`auth_user` + `accounts_userprofile`, camp rol = `rol_nom`)

| id | email | rol_nom | actiu | PROD |
|---|---|---|---|---|
| 1 | a.devant@fhort.cat | admin | ✓ | no censat |
| 13 | m.bohils@fhort.cat | manager | ✓ | no censat |
| 14 | s.devant@fhort.cat | admin | ✓ | no censat |
| 15 | marta.clotet@fhorttextile.tech | technician | ✓ | no censat |

4 usuaris, 4 UserProfile, tots actius.

### 8 · TaskType i ModelTask

| | staging | PROD |
|---|---|---|
| TaskType | **14** | no censat |
| ModelTask | **97** | no censat |
| ModelTask amb work_order | **7** | no censat |

---

## Què li falta sembrar a staging per igualar-se a PROD

La pregunta del brief és si staging és **mirall prou fidel** per a l'assaig d'onboarding LOSAN. La
resposta curta: **NO és mirall 1:1** — i les divergències van gairebé totes en direcció "staging té MÉS
o DIFERENT", no "staging té menys". Per a un assaig d'onboarding *net* de LOSAN, el problema no és què
falta sembrar sinó **què sobra i què no casa**:

1. **Els contenidors de grading LOS no casen** (staging 104/111 vs PROD 95/96/99/101). Staging en té
   2, PROD 4. Un assaig que assumeixi les pks de PROD fallarà. **Acció**: decidir si l'assaig treballa
   amb les pks de staging (i ignorar les de PROD) o si es re-sembren els 4 contenidors de PROD.
2. **Els ids de SizeSystem LOS no casen** (48/51 vs 44/45). Mateix codi i target, pk diferent.
3. **ItemBaseMeasurement: staging=37, PROD=0.** Si l'assaig vol reproduir el camí de PROD (base d'item
   buida → sembra en onboarding), staging **ja té dades** que emmascararien aquest pas. **Acció**:
   l'assaig ha de partir d'un LOS *net*, no de l'estat actual.
4. **BaseMeasurement: staging=535/18, PROD=299/12.** Staging és més ple. No fa mal a un assaig de LOSAN
   (són d'altres models), però confirma que **no és una còpia de PROD**.
5. **Schema únic `fhort`.** A staging LOSAN és Customer del tenant FTT, no un tenant propi. Si PROD
   preveu LOSAN com a **tenant** (schema propi via `bootstrap_tenant`), l'assaig a staging **no exercita
   la frontera de tenant** — només la de Customer dins fhort. Aquesta és la divergència de fons.
6. **git no viatjat (D-2).** Tot el motor de facturació és local a staging. Si l'assaig d'onboarding
   toca facturació (contracte LOSAN → factura), a PROD **no hi és** fins que l'Agus faci push + deploy.

**Veredicte:** staging serveix per assajar la *mecànica* de l'onboarding (crear Customer LOS, sistemes,
grading, mesures) però **no és un mirall fidel de l'estat de dades de PROD**: les pks divergeixen, té
ItemBaseMeasurement que PROD no té, i modela LOSAN com a Customer i no com a tenant. Per a un assaig
que hagi de predir el comportament exacte a PROD, cal partir d'un LOS net i no confiar en cap pk
compartida entre entorns.
