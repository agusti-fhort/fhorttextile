# IMPLEMENTACIÓ BaseSet condicionat — 2026-07-25

> Sprint nocturn sobre `dev` a `/var/www/ftt-staging`. **4 commits, cap push.**
> Cap operació a PROD. Regla del verd respectada a cada peça.

Font de la llei: Patró C (Agus, 2026-07-25), copiada literalment al brief de la sessió.
Precedent diagnòstic: [`DIAGNOSI_BASESET_CONDICIONAT`](DIAGNOSI_BASESET_CONDICIONAT_2026-07-24.md)
(commit `daa3769`).

---

## 0. Resum executiu

| Peça | Estat |
|---|---|
| S0 · integrar el dia a staging | ✅ (ja estava fet a origin) |
| S1 · cens `is_baby` | ✅ **0 callers de negoci** → P0b **LLEST PER DEPLOY, sense condicions** |
| B1 · esquema + migracions + repuntat | ✅ 4 migracions, 0 òrfenes |
| B2 · resolver + sembra + guard P1 | ✅ QA numèric sobre dades reals |
| B3 · promoció + ampliació + acte canònic | ✅ les 4 lleis amb test propi |
| B4 · UI + validació visual | ✅ 6 captures × 3 idiomes, 0 errors de consola |

**Tests:** 352 a `fhort.models_app` + `fhort.pom` · **328 verds** · 24 en error, **tots
preexistents i verificats** (§7).

---

## 1. S0 — Integrar el dia

`git fetch origin` mostra que **la feina ja estava integrada per l'Agus**: la branca
`losan/p0-p4-onboarding` (7 commits, fins a `8bd864f`) ja està mergejada a `dev` pel merge
`336e594`, i els 4 commits de P0b (`3993838`, `97a5e2d`, `b91cc83`, `fba2521`) hi són. El `dev`
local d'staging estava exactament a `origin/dev` (0 endavant, 0 endarrere).

El merge del punt S0.2 **no calia fer-lo** i no s'ha fet: hauria estat un no-op o un merge
duplicat. Cap migració pendent en arribar. `npm run build` net, servei reiniciat,
`/api/schema/` **200**.

---

## 2. S1 — Cens de `Target.is_baby` → **P0b SENSE CONDICIONS**

Cens complet del repo (tot tipus de fitxer, excloent `venv`/`node_modules`/`dist`):

| Caller | Fitxer:línia | Què decideix |
|---|---|---|
| la definició | `backend/fhort/pom/models.py:875` | — (`age_max_months <= 36`) |
| el serializer | `backend/fhort/pom/s2_serializers.py:18` | exposa el camp a `GET /api/v1/targets/` |

**Res més.** `is_kid` / `is_teen` / `is_newborn` **no existeixen**. `is_adult` té exactament la
mateixa forma (definició + serializer, cap consumidor). El frontend **mai** llegeix cap dels dos:
0 ocurrències a `frontend/` i `frontend-backoffice/`. Cap branca de codi del backend hi ramifica.

→ **P0b queda LLEST PER DEPLOY PROD dilluns, sense condicions.** El rename de targets no pot
donar cap resultat de negoci incorrecte per la via d'`is_baby`, perquè cap decisió hi passa.

### 🚩 Bandera CTO 1 — el nom `is_baby` ara menteix (no s'ha tocat)

Amb les dades d'avui, la propietat diu el contrari del que sembla:

| Target | age_max | `is_baby` |
|---|---|---|
| `NEWBORN_*` | 24 | **True** |
| `BABY_*` | 60 | **False** |

El llindar de 36 mesos és anterior al vocabulari nou. **Cap decisió en depèn**, per això és
deute semàntic i no un bug, i per això no l'he tocat (el brief demanava informe, no correcció).
Les dues sortides netes: esborrar la propietat i el camp del serializer (ningú els fa servir),
o reajustar el llindar a 24. **Decisió teva.**

---

## 3. B1 — L'esquema

### `ItemBaseSet` (`pom/models.py:465`)

FK `garment_type_item` (db_constraint=False, el patró cross-schema de `GarmentPOMMap`) · FK
`size_system` (PROTECT) · FK `fit_type` (PROTECT, nullable) · FK `base_size_definition`
(PROTECT, **obligatòria**) · `origen` (PROMOCIO/MASTER/MANUAL) · P9 complet (`created_at`,
`updated_at`, `updated_by`) · `clean()` que lliga la talla base al sistema del set.

**Dues decisions que el disseny obligava i que no eren òbvies:**

**(a) DUES constraints d'unicitat, no una.** A Postgres `NULL` no participa en un `UNIQUE`, o
sigui que `unique(item, system, fit)` deixaria conviure dos sets «sense fit» del mateix món. Hi
ha la normal i una **parcial** per `fit_type IS NULL`.

**(b) `normalize_fit_type()` com a font ÚNICA**, compartida per la creació i pel resolver. Si
només normalitzés una banda, un set creat sense fit i una cerca sense fit caurien en files
diferents. Tres subtileses hi viuen:

- `REGULAR` ≡ «cap fit»: **la mateixa branca**, no una de paral·lela. `Model.fit_type` val
  `'Regular'` per defecte (`models_app/models.py:204`), i sense això un schema sense `FitType`
  sembrat (avui **`los`**, i tots els schemas de test) crearia els sets amb `fit_type` NULL i
  després **no els trobaria mai**.
- Un fit fora de catàleg aixeca `FitTypeDesconegut` en comptes de degradar-se a `None`.
  Degradar-lo seria **pitjor que no trobar res**: cauria a l'slot REGULAR i el lookup tornaria
  el set d'un **altre món**.
- `Model.fit_type` parla un vocabulari propi en CamelCase que no és el de `FitType.codi`. El
  match és case-insensitive i hi ha pont explícit `Oversize→OVERSIZED`.

### La clau d'`ItemBaseMeasurement`: `(item, pom)` → `(base_set, pom)`

**No estava al brief i era imprescindible.** Amb la clau V1, un item amb DOS BaseSets no podria
tenir el mateix POM als dos — que és exactament el que la llei demana. Sense aquest canvi, B1
quedava correcte de forma i inservible de fons. El set ja porta l'item, així que no es perd
unicitat. `garment_type_item` es manté com a denormalització per als consumidors V1.

### Migracions (mostrades abans d'aplicar, auditades a BD després)

| # | Què fa |
|---|---|
| `0047_itembaseset` | crea el model + `base_set` nullable + les 2 constraints |
| `0048_itembaseset_backfill` | crea els sets i hi repunta les files V1 |
| `0049_..._base_set_notnull` | `base_set` → NOT NULL (escrita a mà: `makemigrations` demanava un default interactiu que no existeix) |
| `0050_..._key_base_set` | `unique_together` → `(base_set, pom)` |

**El size_system NO s'ha assumit, s'ha llegit de les dades:** `shirt_woven` (item 4, tenant
`fhort`) → **`ALPHA_EU_M`** (id 30), talla base **`L`** (id 88), que és la que el GTI ja tenia.
Set creat amb `origen=MANUAL`, coherent amb l'origen de les 37 files que hi pengen.

`0048` porta un guard que no era evident: `pom` és app **SHARED** i la migració corre **també a
`public`**, on `tasks` no té taules. Sense el guard, l'`ordering` del Meta d'`ItemBaseMeasurement`
(que fa JOIN cap a `tasks_garmenttypeitem`) petava amb `ProgrammingError` abans i tot de mirar si
hi havia files.

### Auditoria a BD (SELECT directe, els 3 schemas)

```
public  taula OK · 0 sets · mesures òrfenes/total = 0/0  · base_set_id NOT NULL ✓
fhort   taula OK · 1 set  · mesures òrfenes/total = 0/37 · base_set_id NOT NULL ✓
los     taula OK · 0 sets · mesures òrfenes/total = 0/0  · base_set_id NOT NULL ✓

set 1 = shirt_woven · ALPHA_EU_M · REGULAR @ L (origen MANUAL)
índex únic: pom_itembasemeasurement_base_set_id_pom_id_f72fe37a_uniq ✓
```

**0 òrfenes** → `0049` aplicada sense STOP.

`GarmentTypeItem.base_size_definition` i `grading_rule_set` **no s'han tocat** (llegat V1).

---

## 4. B2 — Resolver i sembra

`resolve_item_base_set(item, size_system, fit=None)` — lookup directe, cap heurística, cap
fuzzy, cap cascada. Retorna el set o `None`, i el `None` és **senyal**, mai error.

`materialize_poms_view` en pren els valors i la talla base. **El guard P1 queda reorientat:**
compara `model.base_size_label` amb la talla del **SET**, no amb la de l'item pelat — un item pot
vestir-se en diversos sistemes i cadascun té la SEVA talla base.

**Camí llegat conservat, però amb condició.** Només s'hi cau si el món del model no té set **i**
l'item és inequívoc (0 o 1 set). Amb 2+ sets i cap que casi, se sembra la pertinença i **cap
valor**: endevinar quin món val seria pitjor que no sembrar.

Quan no hi ha set, la resposta porta `code='base_set_absent'` amb el context (item, system, fit).
**El backend no crea mai el set sol.**

### QA numèric — dades REALS d'staging (transacció desfeta, 0 residu)

Punt de partida: item 4 `shirt_woven` · set 1 `ALPHA_EU_M · REGULAR @ L` · **37 mesures al set,
de les quals només 2 tenen valor** · superset de POMs de l'item = **46**.

| Cas | Resultat |
|---|---|
| **1 · model al món del set** (ALPHA_EU_M, base L) | 200 · `base_set` resolt (id 1) · **46 BaseMeasurement creades, 2 amb valor** (`seeded=2`, `materialized=44`) · `talla_item=L`, `talla_model=L`, **`talla_verificada=True`** |
| **2 · model en un altre món** (TGIRL-EU-HEIGHT) | 200 · `base_set=None` · **`base_set_absent` net** amb item 4 / system 6 / fit Regular · **46 files de pertinença, 0 amb valor** |

> ⚠️ **Correcció d'una xifra del brief.** El brief deia «les 37 bases arriben al model». La xifra
> real és **46 files de pertinença i 2 valors**: el set té 37 files però **només 2 amb valor**
> (les altres 35 són pertinença sense mesurar), i el superset de POMs de l'item en són 46. El
> comportament és el correcte; la xifra esperada no ho era.

---

## 5. B3 — Promoció, ampliació i acte canònic

Promoció reescrita sobre les lleis. **El canvi de fons:** abans feia `update_or_create`, i això
convertia qualsevol model en autoritat sobre l'estàndard del taller.

| Llei | Com queda al codi |
|---|---|
| **4** · només forats | els divergents **ni entren al bucle d'escriptura**. Una fila de pertinença sense valor SÍ és un forat: omplir un buit no modifica res |
| **5** · divergència = vida normal | es llisten amb els dos valors i s'hi queden. Cap watchpoint, cap alarma |
| **6** · ampliació amb confirmació | secció pròpia `ampliaria_item` al diff; el confirm els afegeix al `GarmentPOMMap` amb `pendent_revisio=False` (els signa un tècnic amb gate CONFIGURE, no un clon automàtic de germà) |
| **7** · naixement mandrós | el dry-run **proposa** el set amb la talla de la convenció Montse; el confirm el crea amb `origen=PROMOCIO`. Via canònica de naixement |
| **2** · convenció Montse | `suggerir_talla_base()`: la més petita, excepte `MAN`/`UNISEX_ADULT`→M/42 i `WOMAN`/`MATERNITY`→S/38. Cau a la més petita si el sistema no té l'etiqueta de convenció |

**Acte canònic** — `POST /api/v1/item-base-sets/<id>/acte-canonic/`, gate CONFIGURE, dry-run +
confirm, re-signa la fila a MANUAL perquè la provinença digui la veritat. **Refusa explícitament
els forats amb 422**: si compartís porta amb la promoció, la llei 4 seria una recomanació en
comptes d'una invariant.

La promoció **ja no escriu `GarmentTypeItem.base_size_definition`**: la talla base viu al set.

---

## 6. B4 — UI

`BaseSetPanel` (nou) al pas 2 d'`ItemAuthoring`: llista els mons (sistema · fit · talla base ·
*n amb valor de m*), en deixa néixer de nous i **escopa la graella al món seleccionat**.
`MeasurementBaseGrid` rep `baseSetId` opcional — amb ell llegeix/escriu només aquell món, sense
ell segueix el camí V1 (cap caller existent canvia).

Al wizard de model, `base_set_absent` pinta una **proposta no bloquejant i descartable**. No
ofereix crear el set allà: l'acte real és la promoció, i vol el model ja mesurat.

API: `ItemBaseSetViewSet` amb els comptes **anotats a la BD** (un `SerializerMethodField` hi
faria un N+1). Esborrar un set amb mesures → 400: el CASCADE se'n enduria el patrimoni en silenci.

`load_losan_package` adaptat: el format del paquet és anterior al BaseSet, així que el món es
dedueix del `base_size_definition` de l'item (mateix criteri que `0048`) amb `origen=MASTER`. Si
l'item no en té, **no s'inventa cap món**: s'avisa i se salta el valor.

i18n **ca/en/es** complet (25 claus noves + 2), paritat verificada. Icones Tabler outline, colors
per token CSS.

### Validació visual (Playwright · bundle de `frontend/dist` · `/api/` estubejat · CAP credencial)

Captures a `docs/diagnosis/captures-baseset/` — **6 × 3 idiomes, 0 errors de consola**:

| Checklist del brief | Resultat |
|---|---|
| Llistat de BaseSets de l'item | ✅ `ALPHA_EU_M · Regular · L · 2 de 37 amb valor` i `KIDS_CM · SLIM · 104 · 12 de 12` |
| Creació d'un set (system + fit + talla) | ✅ formulari amb les talles filtrades pel sistema; el món creat apareix i queda seleccionat |
| Graella de valors (reusada, no reinventada) | ✅ `MeasurementBaseGrid` amb `baseSetId` |
| Proposta de naixement al wizard | ✅ avís amb icona, descartable, la sembra continua |
| i18n als 3 idiomes | ✅ **verificat pel text pintat**, no només per la clau |

**La captura més il·lustrativa** és `es-4-creat.png`: el món acabat de crear surt seleccionat amb
**el mateix superset de POMs i tots els valors buits** — la llei sencera d'un cop d'ull (el
superset és de l'item, els valors són del món).

> Nota de mètode: la 1a passada va donar els 3 idiomes en **anglès** perquè jo escrivia
> `i18nextLng` i la clau real de detecció és **`fhort.lang`** (`i18n/index.js:26`). Corregit, i
> ara l'script **comprova el text realment pintat** en cada idioma perquè un EN disfressat de CA
> no pugui tornar a passar per bo.

---

## 7. Estat verd

- `manage.py check` net · `npm run build` net · `migrate_schemas` als 3 schemas · servei
  reiniciat · `/api/schema/` **200** · `/api/v1/item-base-sets/` **401 sense auth** (gate viu).
- **Tests: 352 (`fhort.models_app` + `fhort.pom`) · 328 verds · 24 en error.**
  Els 24 són **PREEXISTENTS i verificats**, no meus: `test_g6_segell` + `test_g6_grading_gates`,
  **tots 24** amb el mateix `IntegrityError: duplicate key ... fitting_sizefitting_model_id_numero_uniq`.
  És el mateix conjunt, amb el mateix comptador, que P0b ja va documentar ahir
  (`RESULTAT_P0B_VOCABULARI_TARGETS_2026-07-24.md` §6). Executats a part per confirmar-ho.
- El fitxer de la cadena de sembra passa de 58 a **70 tests**, tots verds.

---

## 8. Banderes CTO

**1. `is_baby` menteix** — §2. Cap decisió en depèn. Esborrar-la o reajustar el llindar a 24.

**2. `Tailored` no té equivalent a `FitType`** — `Model.FIT_CHOICES` té `Tailored`, el catàleg
`FitType` no. He posat el pont per `Oversize→OVERSIZED` i **he deixat `Tailored` fora a posta**:
inventar-li un equivalent és decidir producte, no codi. Conseqüència viva: un model amb fit
`Tailored` sempre dirà `base_set_absent`, que és honest però mai es resoldrà sol. Les sortides:
afegir `TAILORED` al catàleg de `FitType`, o mapar-lo a un existent.

**3. `los` no té cap `FitType` sembrat** — els sets que hi naixerien tindrien `fit_type` NULL.
Funciona (la constraint parcial i la normalització ho cobreixen), però és un catàleg incomplet
que caldrà sembrar abans de treballar-hi de veritat.

**4. La clau `(base_set, pom)` no estava al brief** — §3. L'he fet perquè sense ella la llei era
inexecutable. Val la pena que ho validis explícitament.

**5. El camí llegat de la sembra segueix viu** — mentre hi hagi items sense set. Es tanca quan
tots els mons en tinguin; llavors es pot jubilar `GarmentTypeItem.base_size_definition`.

---

## 9. Commits (a `dev`, **cap pushat**)

| Hash | Focus |
|---|---|
| `5353d1c` | `feat(baseset): ItemBaseSet — el món viu al satèl·lit, no partint l'item` (model + migracions 0047-0049) |
| `872799c` | `feat(baseset): la clau de la mesura base passa de l'item al set` (0050 + upsert + convenció Montse) |
| `3fac0fe` | `feat(baseset): B2+B3 — la sembra resol el món, i la promoció només omple forats` |
| `43e9d35` | `feat(baseset): B4 — el catàleg ensenya els mons de l'item i el wizard els proposa` |

---

## 10. El que queda per a l'Agus

1. **Revisar + push.** 4 commits a `dev` local d'staging. Atenció a les 5 banderes de §8,
   especialment la **4** (canvi de clau no previst al brief) i la **2** (`Tailored`).
2. **Validació visual pròpia a staging** amb dades reals i credencials — la meva és sobre el
   bundle amb `/api/` estubejat, que prova la superfície però no el circuit sencer. El cas viu:
   `shirt_woven` a `fhort` ja té el seu set (`ALPHA_EU_M · Regular · L`) amb les 37 files.
3. **Finestra PROD de dilluns, amb tu present:**
   - **P0b** — codi → `migrate_schemas` → `rename_targets_p0b` dry-run → apply, **seguits**.
     Queda **sense condicions** (§2).
   - **BaseSet** — migracions `0047`→`0050`. `0048` és idempotent i llegeix el sistema de les
     dades; **si a PROD algun item té mesures base sense `base_size_definition`, `0049` PETARÀ**,
     i això és el senyal correcte (no s'hi ha d'inventar cap món). Val la pena comptar-ho abans
     amb un SELECT sobre el backup diari.
   - **choice `HERETAT_NUMERIC`.**

---

*Sessió del 2026-07-24/25. Cap push, cap operació a PROD.*
