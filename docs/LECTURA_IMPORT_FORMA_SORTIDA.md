# LECTURA QUIRÚRGICA — Forma de sortida del Wizard d'Import

> **Naturalesa:** lectura quirúrgica READ-ONLY (Patró A acotat). NO és la diagnosi sencera de
> l'import; només mapa la **forma de la seva sortida** per dissenyar la pàgina d'autoria d'ITEM
> perquè l'aculli sense col·lisionar amb l'autoria manual.
> **Estat:** res tocat. `git status` net (només documents de treball untracked, com mana el mètode).
> **Convenció:** `FET` = afirmació amb referència `fitxer:línia`. `💡 PROPOSTA (a validar)` = suggeriment de disseny, decisió humana (Patró C).
> Tots els paths són relatius a `/var/www/ftt-staging/backend/`.

---

## 0 · Resum executiu (per decidir la pàgina d'item)

1. **L'import escriu AVUI a taules de MODEL, no d'ITEM.** En confirmar materialitza
   `BaseMeasurement` (model), `SizeFitting`+`GradingVersion`+`GradedSpec` (model) i re-apunta
   `model.grading_rule_set`. **No toca cap taula d'item** (`GarmentPOMMap`, `ItemBaseMeasurement`,
   `GarmentTypeItem`). FET: `extraction_views.py:1802-1984`.

2. **L'ITEM ja viatja a la sessió** com a `tipologia_confirmada` (FK→`GarmentTypeItem`), però
   **pot ser null** i avui **no s'usa al confirm**. És l'àncora del destí-catàleg que falta connectar.
   FET: `models.py:409`, fixat a `extraction_views.py:866`, absent de tot el bloc `confirmar` (1708-2000).

3. **La sortida és PARCIALMENT redirigible cap a item, però la seva FORMA assumeix MODEL.** El nucli
   de dades (`valors {pom_id: {talla: valor}}`, amb FK ja resolta a `pom_master_id`) és prou
   desacoblat; però el wizard llegeix i escriu `model.*` arreu i materialitza artefactes que NOMÉS
   tenen sentit a capa model (GradedSpec per talla, SizeFitting instància). Veredicte detallat a §5.

4. **Forat crític d'ancoratge:** l'import deriva/crea un `GradingRuleSet` i el lliga al **model**;
   l'ITEM **encara no té** FK `grading_rule_set` (`tasks/models.py:365` ho declara explícitament
   inexistent — «vegeu DIAGNOSI T1»). Si l'import ha d'ancorar grading a l'item, falta aquesta FK. §6.

5. **Pont Item→Model JA dissenyat (i és la clau anti-col·lisió):** `ItemBaseMeasurement` documenta
   que la sembra (P5) **copia** els valors base de l'item al `BaseMeasurement` del model amb
   `origen='ITEM_STANDARD'` («copy-at-the-moment; a partir d'aquí el Model és sobirà»).
   FET: `pom/models.py:448-468`. Els dos camins (autoria item + import) **no col·lisionen avui**
   perquè escriuen capes diferents; la convergència real és al model, via `origen`. §7.

---

## 1 · La FORMA del resultat de l'import en confirmar

### 1.1 · `ImportSession` — inventari de camps en arribar al confirm

FET — `models.py:385-421`:

| Camp | Tipus | Què porta al confirm | Línia |
|---|---|---|---|
| `token` | UUID | identificador de sessió | `models.py:394` |
| `estat` | char (choices) | flux; al confirm passa a `'CONFIRMAT'` | `models.py:400`, escrit a `:1983` |
| `document` | FileField | PDF/Excel/imatge origen | `models.py:402` |
| `model` | FK→`Model` (null) | **model destí** (creat abans del confirm) | `models.py:405` |
| `model_detectat` | JSON dict | cribratge cru (no usat al confirm) | `models.py:408` |
| **`tipologia_confirmada`** | **FK→`tasks.GarmentTypeItem` (null)** | **l'ITEM destí-catàleg** | `models.py:409` |
| `run_conciliat` | JSON dict | reconciliació de talles (no usat al confirm) | `models.py:411` |
| `poms_extrets` | JSON **list** | **els POMs candidats** (§1.2) | `models.py:412` |
| `resultat` | JSON **dict** | **mesures + extracció + mode + teixit** (§1.3) | `models.py:413` |
| `historia_xat` | JSON list | xat (no usat al confirm) | `models.py:414` |
| `avisos` | JSON list | warnings (el confirm hi AFEGEIX) | `models.py:415` |

**Observació clau:** la "sortida" materialitzable en confirmar viu a **dos** JSONFields:
`poms_extrets` (què) i `resultat` (valors + context). FK ja resolta dins `poms_extrets`.

### 1.2 · Esquema EXACTE de `poms_extrets` (list de dicts)

FET — construït idèntic a les 3 vies (Excel `:1245-1256`, PDF/IA `:1379-1390`, alta manual W2 `:1498-1509`):

```
{
  'codi_fitxa':    str,            # codi del POM tal com surt a la fitxa  → esdevé nom_fitxa
  'descripcio':    str,            # descripció del POM a la fitxa          → esdevé notes
  'pom_master_id': int | None,     # FK JA RESOLTA a pom.POMMaster
  'pom_codi':      str | None,     # POMMaster.codi_client (eco)
  'pom_nom':       str | None,     # POMMaster.nom_client (eco)
  'match_type':    str,            # 'excel'|'pdf'|'tenant_only'|'manual'
  'confidence':    str,            # 'HIGH'|'LOW'|'TENANT_ONLY'
  'values':        dict,           # {talla_label: valor}  (valors inline per talla)
  'actiu':         bool,           # filtre de confirmació
  'ordre':         int,            # índex
}
```

FET — el confirm només llegeix `actiu`, `pom_master_id`, `codi_fitxa`, `descripcio` d'aquest dict
(`extraction_views.py:1742`, `:1807`, `:1816`, `:1820`).
**No hi ha** `is_key`, ni `tolerancia_*`, ni `nivell`, ni `nom_fitxa` a `poms_extrets`. (Forat per a item, §3.)

### 1.3 · Esquema EXACTE de `resultat` (dict)

FET — acumulat pas a pas pel wizard:

| Clau | Forma | Escrit a |
|---|---|---|
| `cribratge` | dict cribratge IA (no usat al confirm) | `extraction_views.py:918` |
| `extraccio` | `{via, header, sizes:[str], base_size:str}` | `:1264`, `:1397` |
| `grading_status` | `{status, detail}` (no usat al confirm) | `:1265`, `:1398` |
| **`mesures`** | **list de `{pom_master_id:int, talla_label:str, valor:float}`** | `:1586-1588` |
| `valors_mode` | `'absoluts'` \| `'deltes'` | `:1592` |
| `teixit` | dict camps `_TEIXIT_FIELDS` (fabric/shrinkage…) | `:1700` |

FET — el confirm reconstrueix `valors = {pom_master_id: {talla_label: valor}}` des de `resultat['mesures']`
(`extraction_views.py:1746-1753`). Aquesta és **la matriu nuclear de sortida**: FK resolta + talla + valor.

### 1.4 · L'esquema real, en una frase

> La sortida materialitzable és: **una llista de POMs amb FK ja resolta** (`poms_extrets`) **+ una matriu
> `{pom_id → {talla → valor}}`** (`resultat.mesures`) **+ talla base i run** (`resultat.extraccio` /
> `model.*` reconciliat) **+ mode (absoluts/deltes)**. Tot són dades planes (dicts/lists) amb FK a
> `POMMaster` ja resolta; **no** són files de cap taula concreta fins al confirm. → Això la fa
> redirigible (la forma de dades), però el confirm les ancla a model (la forma de destí). §5.

---

## 2 · Punt de materialització i destí actual (`import_session_confirmar_view`)

FET — `extraction_views.py:1708-2000`. Dins una sola `transaction.atomic()` (`:1755`), en aquest ordre:

| # | Acció | Taula tocada | `origen`/detalls | Línia |
|---|---|---|---|---|
| 0c | Reconcilia size_system/base/run | `Model` (update_fields) | només si match perfecte | `:1756-1782` |
| 1a | Esborra files buides de plantilla | `BaseMeasurement` (DELETE) | `base_value_cm IS NULL` | `:1802` |
| 1b | Crea/actualitza POMs confirmats | `BaseMeasurement` (update_or_create per `(model,pom)`) | **`origen='IMPORTED'`**, `nom_fitxa=codi_fitxa`, `notes=descripcio`, `ordre=i`, `is_active=True` | `:1812-1822` |
| 2 | Crea contenidor de grading | `SizeFitting` (`IMP-{model.id}-{n}`, `Tancat`, `base_tancada=True`) | cap FittingSession | `:1834-1838` |
| 2 | Crea versió de grading | `GradingVersion` v1 (`aprovada`, `is_active`) | — | `:1839-1843` |
| 3 | Materialitza grading per talla | `GradedSpec` (update_or_create per `(version,pom,size_label)`) | `grading_type_applied` FIXED/LINEAR | `:1864-1868` |
| 3b | Deriva i re-apunta ruleset | `GradingRuleSet` (+`model.grading_rule_set`) | savepoint propi; degradació gràcil | `:1877-1940` |
| 3b | Materialitza regles residents | regles del model | `origen='IMPORTED'` | `:1904-1906` |
| 4 | Desa document versionat | `ModelFitxer` (categoria `Document`) | re-import → `versio_anterior` | `:1945-1970` |
| 5 | Aplica teixit | `Model` (camps `_TEIXIT_FIELDS`) | si informat | `:1972-1980` |
| 6 | Tanca sessió | `ImportSession.estat='CONFIRMAT'` | — | `:1983-1984` |

**FET — totes les escriptures són a capa MODEL.** Cap toca `GarmentPOMMap`, `ItemBaseMeasurement`
ni `GarmentTypeItem`. Resposta final retorna comptadors (`extraction_views.py:1986-2000`).

### 2.1 · `tipologia_confirmada` (l'àncora del destí-catàleg)

FET:
- És FK→`tasks.GarmentTypeItem`, **null/blank** (`models.py:409-410`).
- Es fixa abans del confirm, en crear el model des de la sessió: `item = GarmentTypeItem.objects.filter(code=item_code).first()` i s'assigna a `tipologia_confirmada=item` (`extraction_views.py:856`, `:866`).
- **Pot ser null** (depèn que `item_code` matchegi via `.first()`).
- **No es llegeix enlloc del bloc `confirmar`** (1708-2000): l'item viatja a la sessió però el confirm l'ignora. → És el fil per estirar per connectar el destí-catàleg.

---

## 3 · Mapatge sortida-import ↔ taules d'item

Esquemes d'item verificats: `GarmentTypeItem` (`tasks/models.py:347-379`), `GarmentPOMMap`
(`pom/models.py:414-445`), `ItemBaseMeasurement` (`pom/models.py:448-478`), `GradingRuleSet`
(`pom/models.py:481-539`).

| Peça que l'import produeix | Origen (FET) | Taula d'ITEM destí | Encaix |
|---|---|---|---|
| POM (pertinença) `pom_master_id` | `poms_extrets[*].pom_master_id` | `GarmentPOMMap(garment_type_item, pom)` `pom/models.py:421-424` | ✅ **NET** (clau (item,pom) ja existeix) |
| `ordre` | `poms_extrets[*].ordre` | `GarmentPOMMap.ordre` `:433` | ✅ net |
| Valor base (cel·la talla base) | `valors[pid][base_size]` | `ItemBaseMeasurement.base_value_cm` `pom/models.py:464` | ✅ net (només la cel·la base) |
| Talla base | `model.base_size_label` (label str) | `GarmentTypeItem.base_size_definition` (FK→SizeDefinition) `tasks/models.py:366` | ⚠️ cal resoldre **label → SizeDefinition** |
| `nom_fitxa` (nomenclatura fletxa) | `poms_extrets[*].codi_fitxa` | — | ❌ **FORAT**: ni `GarmentPOMMap` ni `ItemBaseMeasurement` tenen `nom_fitxa` (viu només a `BaseMeasurement.nom_fitxa`, `models.py:515`) |
| Tolerància ± | l'import **no la produeix** | `ItemBaseMeasurement.tol_minus/tol_plus` `:467-468` | ⚪ destí existeix, **font buida** |
| `is_key` / nivell | l'import **no el produeix** (no és a `poms_extrets`) | `GarmentPOMMap.is_key`/`nivell` `:426-432` | ⚪ destí existeix, **font buida** |
| Grading rule set (derivat) | `derive_grading_rule_set→GradingRuleSet` `:1885` | FK `Item→GradingRuleSet` | ❌ **FORAT GROS**: la FK a l'item **no existeix** (`tasks/models.py:365`) |
| Valors de grading per talla | `GradedSpec` per `(version,pom,talla)` `:1864` | — | ❌ **sense destí item**: a capa item el grading és per **regla** (ruleset), no per cel·la. És artefacte d'instància (model) |
| SizeFitting/GradingVersion | instàncies de model `:1834-1843` | — | ❌ artefactes d'instància; no van a item |
| Teixit / shrinkage | `resultat.teixit` `:1973` | — (camps de model) | ❌ no és capa item |

**Síntesi:** encaixen net **POM-membership, ordre, valor base i (amb resolució) talla base**. Tenen
**destí però sense font**: tolerància i is_key. **No tenen destí a item**: `nom_fitxa`, els valors de
grading per talla, SizeFitting/GradingVersion, teixit — perquè són o bé d'instància-model o bé un atribut
que la capa item no modela.

---

## 4 · Grading: el que l'import dedueix vs la FK Item→ruleset (col·lisió a vigilar)

### 4.1 · Com l'import resol/crea el ruleset avui
FET — `pom/grading_utils.py`:
- `derive_grading_rule_set(...)` (`:226-228`) detecta grading per POM, dedup, anti-proliferació 1D,
  i **decideix reutilitzar vs crear**: filtra candidats per `(size_system, garment_group, target,
  construction, fit_type)` **sense `order_by`** (`:308-315`), compara dimensions i **es queda el
  primer que encaixa** (`:337-339`); si cap, en crea un de nou amb sufix únic determinista
  (`:348-386`). Retorna `GradingRuleSet` o `None`.
- Comparació amb el canònic (només informa): `cerca_canonic_equivalent(model)` →
  `GradingRuleSet.objects.filter(is_system_default=True, …).distinct().first()` **sense `order_by`**
  (`grading_utils.py:108-113`).

### 4.2 · El risc de `.first()` no-determinista per a l'ancoratge de l'item
FET — `GradingRuleSet.Meta` **no defineix ordering** (`pom/models.py`, classe a `:481`). Per tant
tant `cerca_canonic_equivalent().first()` (`:113`) com el filtratge de candidats de `derive_*`
(`:308`) depenen de l'ordre arbitrari de BD quan més d'una fila encaixa.

> 💡 PROPOSTA (a validar — Fase C, NO resoldre aquí): si la futura FK `Item→GradingRuleSet`
> s'alimenta de la derivació de l'import, el `.first()` sobre queryset no ordenat és un risc
> d'ancoratge no-determinista (dos imports equivalents podrien apuntar a rulesets diferents).
> Caldria ordering explícit o un upsert idempotent. Reportat, **no tocat**.

---

## 5 · Veredicte de desacoblament: ¿redirigible o model-bound?

**VEREDICTE: la FORMA de les DADES és redirigible; la FORMA del DESTÍ és model-bound.** (FET)

A favor de redirigible:
- La matriu nuclear `valors {pom_id:{talla:valor}}` té la **FK ja resolta** a `POMMaster` i és un
  dict pla, independent de cap taula (`extraction_views.py:1746-1753`).
- `derive_grading_rule_set` és **pura de model** per disseny (comentari `:1871-1876`: «perquè la Size
  Library la pugui cridar amb dades del fitxer») — el re-apuntat a model es fa **a fora**. → la
  derivació de grading és reutilitzable des d'un context d'item.

En contra (assumpcions de model en la forma):
- El confirm llegeix/escriu `model.*` arreu: `model.base_size_label`, `model.size_system`,
  `model.target`, `model.size_run_model`, `model.grading_rule_set` (`:1763-1901`).
- Materialitza artefactes que **només existeixen a capa model**: `GradedSpec` per talla, `SizeFitting`
  instància, `GradingVersion` (`:1834-1868`). La capa item **no** modela valors de grading per cel·la
  (només la regla via ruleset).
- L'escriptura base és `BaseMeasurement(model,pom)` amb tot el **run** de talles, no només la cel·la
  base; l'item només vol el **valor base** (`ItemBaseMeasurement.base_value_cm`, una cel·la).

> 💡 PROPOSTA (a validar): un **selector de destí** al confirm (model vs item-catàleg) és viable per a
> la part de dades (POM-membership + valor base + derivació de ruleset), però NO és un simple "redirigir
> l'escriptura": cal **projectar** la sortida (quedar-se la cel·la base, descartar el run per talla a
> capa item, mapar `nom_fitxa`→on?, decidir l'ancoratge de ruleset). El motor d'extracció no cal tocar-lo.

---

## 6 · Forat d'ancoratge: FK Item→GradingRuleSet (inexistent)

FET — `GarmentTypeItem` **no té** FK a `GradingRuleSet`; el comentari del codi ho diu literalment:
«es constrenyirà al run quan existeixi el lligam Item→GradingRuleSet (**avui inexistent**; vegeu
DIAGNOSI T1)» (`tasks/models.py:364-365`). `base_size_definition` (FK→SizeDefinition) ja existeix i
és «lliure» fins que existeixi aquell lligam (`:366-370`).

> 💡 PROPOSTA (a validar): perquè l'import "aterri a l'item" amb grading ancorat, la pàgina d'item
> necessita primer la FK `Item→GradingRuleSet` (la mateixa que la futura A3 esmentada al brief).
> Sense ella, l'import només pot abocar a l'item POM-membership + valor base; el grading es quedaria
> a capa model. Decisió de Fase C.

---

## 7 · Anti-col·lisió: ¿els dos camins desemboquen al mateix lloc?

FET — **avui NO escriuen les mateixes taules**, per tant **no col·lisionen directament**:
- **Autoria item** (futura pàgina) → `ItemBaseMeasurement` via `POST .../item-base-measurements/upsert/`,
  `update_or_create` per `(garment_type_item, pom)` (`pom/views.py:295-319`, url `pom/urls.py:27`).
  També `GarmentPOMMap` per la pertinença.
- **Import** → `BaseMeasurement` per `(model, pom)`, `origen='IMPORTED'` (`extraction_views.py:1812`).

**On SÍ poden trobar-se (capa model):** `BaseMeasurement(model,pom)` és `unique_together`
(`models.py:528`) i el toquen **quatre** escriptors amb `update_or_create`/`get_or_create`,
diferenciats per `origen`:

| Camí | `origen` | base_value | Escrit a |
|---|---|---|---|
| Plantilla | `'TEMPLATE'` | `None` | `views.py:444` (`materialize_poms_view`) |
| Manual | `'MANUAL'` | valor usuari + `tolerancia_*` del catàleg | `views.py:656` (`set_measurements_view`) |
| Import | `'IMPORTED'` | valor fitxa, **sense** `tolerancia_*` | `extraction_views.py:1812` |
| Sembra d'item (P5) | `'ITEM_STANDARD'` | còpia d'`ItemBaseMeasurement` | dissenyat a `pom/models.py:453-454` |

FET — el pont **dissenyat** item→model és la **sembra (P5)**: `ItemBaseMeasurement` →
`BaseMeasurement(origen='ITEM_STANDARD')`, «copy-at-the-moment… a partir d'aquí el Model és sobirà»
(`pom/models.py:448-468`). Aquest és el punt de convergència previst dels dos mons.

**Assumpcions de l'import que farien divergir els camins (a vigilar en dissenyar la pàgina):**
1. L'import escriu el `BaseMeasurement` del model amb tot el run i `origen='IMPORTED'` i **no posa
   `tolerancia_*`** (`:1812-1822`); l'upsert d'item SÍ modela `tol_minus/tol_plus`
   (`pom/models.py:467-468`). → en redirigir l'import a item, la tolerància quedaria buida.
2. L'import porta `nom_fitxa` (de `codi_fitxa`) que **no té casella a capa item** (§3). Si la pàgina
   d'item assumís que tota mesura té `nom_fitxa`, l'import-a-item el perdria (o caldria afegir el camp).
3. L'import crea `SizeFitting`/`GradingVersion`/`GradedSpec` (instància-model); l'autoria d'item **no**
   crea instàncies. Si la pàgina d'item esperés que "confirmar import" deixés un SizeFitting, no
   passaria a capa item (és correcte: l'item és catàleg, no instància).
4. `update_or_create` de l'import **sobreescriu** qualsevol fila `(model,pom)` prèvia (manual/template)
   sense mirar `origen` (`:1812`). A capa model això és intencional ("mana el document", `:1713`); però
   confirma que **import i autoria manual a capa MODEL SÍ col·lisionen** (l'import guanya). La separació
   neta s'aconsegueix precisament mantenint l'autoria a capa **item** i deixant la convergència per a la
   sembra amb `origen` distingible.

> 💡 PROPOSTA (a validar): dissenyar la pàgina d'item de manera que escrigui SEMPRE a capa item
> (`ItemBaseMeasurement`/`GarmentPOMMap`) i que el destí-catàleg de l'import (si s'activa) escrigui
> a les MATEIXES taules item via el mateix upsert idempotent per `(garment_type_item, pom)`. Així els
> dos camins convergeixen a una única clau d'item, i la sembra a model (amb `origen` distingible)
> resol qui mana a capa instància. Decisió de Fase C.

---

## 8 · Criteri d'èxit (checklist d'aquesta lectura)

- [x] Esquema real de la sortida documentat amb `fitxer:línia` (§1: `poms_extrets`, `resultat`, `valors`).
- [x] Punt de materialització i ordre d'escriptures (§2, taula amb línia per escriptura).
- [x] `tipologia_confirmada` confirmat com a àncora present-però-no-usada (§2.1).
- [x] Taula de mapatge sortida↔taules d'item, amb encaixos ✅ i forats ❌/⚪ (§3).
- [x] Veredicte de desacoblament: dades redirigibles, destí model-bound (§5).
- [x] Risc del `.first()` no-determinista per a l'ancoratge de ruleset (§4, marcat com a Fase C).
- [x] Punts de col·lisió manual↔import identificats (§7).
- [x] Import NO redissenyat, res tocat, `git status` net.

---

*Lectura quirúrgica · Patró A acotat · 2026-06-22 · READ-ONLY · staging `dev`.*
