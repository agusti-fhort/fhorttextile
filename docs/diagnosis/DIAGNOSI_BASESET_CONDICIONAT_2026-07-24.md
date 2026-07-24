# DIAGNOSI — BaseSet condicionat (mesures base, DXF i sketches dins un GTI únic)

**Data:** 2026-07-24 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
(HEAD `b1c63b8`) · BD `ftt_staging` @ `:5433`, tenant `fhort`.

**Abast.** Dimensionar el disseny d'un «BaseSet condicionat»: mesures base (i, en horitzó
posterior, patrons DXF base i sketches) que viuen DINS d'un GTI únic per peça, condicionades pels
MATEIXOS eixos que ja identifiquen un `GradingRuleSet` (customer × size_system × target(s) ×
construction × fit) i resoltes pel MATEIX matcher unificat. La pregunta que aquest document ha de
contestar és **si el mecanisme existent s'hi pot enganxar tal qual o necessita peces pròpies**.

**Convenció.** `fitxer:línia` sempre relatiu a `backend/fhort/` (backend) o `frontend/src/`
(frontend), tret que es digui el contrari. **«NO EXISTEIX» = confirmat absent al codi**, no
especulat. Les propostes van marcades `💡 PROPOSTA (a validar)` i **no** són decisions: el disseny
final es tanca en sessió amb l'Agus (Patró C).

**Cap escriptura.** Aquesta sessió no ha tocat codi, ni schema, ni dades. Tota la lectura de BD és
`SELECT`. L'única escriptura és aquest fitxer.

---

## Resum executiu

1. **La premissa que bloqueja la sembra multi-món està confirmada, i el seu cost és mesurable.**
   `GarmentTypeItem.base_size_definition` és **un FK simple** (`tasks/models.py:316-320`), i
   `ItemBaseMeasurement` té `unique_together = [('garment_type_item', 'pom')]`
   (`pom/models.py:520`): **un GTI = una talla base = un joc de valors**. Però a `fhort` els 15 GTI
   multi-món tenen **entre 2 i 6 talles base distintes** entre els seus models. Triant la millor
   talla possible per a cada GTI, **501 dels 1.025 models amb GTI (48,9%) no poden rebre CAP valor
   de plantilla** — el guard P1 (`models_app/views.py:1050-1069`) els refusa amb «TALLES
   DIVERGENTS». No és una qüestió d'ergonomia: és una **impossibilitat estructural** que el guard
   del 22/07 va fer visible i blocant en comptes de silenciosa.

2. **El matcher unificat existeix i és sòlid, però està acoblat a `GradingRuleSet` com a model
   concret, no a un domini abstracte.** `resolve_grading_container`
   (`pom/grading_utils.py:635-711`) implementa exactament N1→N2→N3 amb guarda d'ambigüitat, però
   **17 de les seves ~45 línies executables nomenen `GradingRuleSet` o camps seus**
   (`origen=CLIENT_RUN`, `actiu`, `targets__codi`, `construction__codi`, `fit_type__codi`,
   `garment_type_item`, `scope_nodes`). **NO és parametritzable per domini avui**; caldria
   extreure'n el predicat. L'extracció és mecànica, no conceptual: la LLEI ja està escrita i
   provada.

3. **`RuleSetScopeNode` és generalitzable a cost baix, però avui està poc poblat.**
   `pom/models.py:642-696`: FK dur a `GradingRuleSet` + 3 FK d'eix + 3 constraints parcials.
   Generalitzar-lo (`content_type` genèric) trencaria les 3 `UniqueConstraint` parcials, que són el
   que sosté la seva integritat. A BD: **11 nodes sobre 5 rulesets dels 45** — la font única del
   ventall (D-CONS, `DECISIONS.md:239-240`) encara està **buida al 89%**. Qualsevol disseny que hi
   penji un segon domini hereta aquest deute.

4. **Els TRES actius tenen ancoratge pla, i el buit no és igual de gran.** `ItemBaseMeasurement`
   (37 files, 1 GTI de 62), `PatternFile` (5 files, **totes de model, 0 d'item**,
   `patterns/models.py:42-50`) i `ItemFitxer` (**0 files**, `models_app/models.py:497`). Cap dels
   tres té CAP eix (`grep` d'eixos a `patterns/models.py` = **0 resultats**). Els tres pateixen la
   mateixa limitació; només un d'ells (bases) té dades reals que ho demostrin.

5. **La pregunta «una taula o tres» té una resposta empírica clara, però NO la que es podria
   esperar.** Un `PatternFile` **no porta talla**: adquireix el seu context de talla al moment de
   la projecció, llegint-lo del **Model** (`patterns/adapters.py:450-476`). Una
   `ItemBaseMeasurement` **és** un valor expressat en UNA talla declarada. Són naturaleses
   diferents, no dos camps del mateix registre. **Ara bé, l'eix `fit` NO es pot argumentar amb
   dades: els 1.056 models de `fhort` tenen `fit_type='Regular'`, tots.** L'exemple «un DXF
   compartit entre WOMAN REGULAR i WOMAN OVERSIZE» **no té ni un sol cas real al sistema**.

6. **Welford queda FORA de l'abast del BaseSet, i el problema que va motivar la separació del 18/07
   segueix viu — però amb volum ínfim.** La cel·la és `(garment_type_item, task_type)`
   (`tasks/models.py:372`) i el domini és TEMPS, no MESURES: cap disseny de BaseSet la toca. La
   barreja **ja passa avui** (les 3 `ModelTask` de `t_shirt × pom` vénen de 3 mons diferents), però
   **cap cel·la amb `n ≥ 5` (el llindar, `tasks/services_i.py:10`) està contaminada**: només 4
   cel·les creuen el llindar i totes tres de món únic. **Pot esperar; el BaseSet no.**

---

## BLOC 1 — L'esquema actual d'`ItemBaseMeasurement`

### 1.1 · Camps complets (`pom/models.py:465-524`)

| Camp | Tipus | Nota |
|---|---|---|
| `garment_type_item` | FK → `tasks.GarmentTypeItem`, CASCADE, **`db_constraint=False`** | `:477-478`. Cross-schema: `pom` és SHARED (taula també a `public`), un constraint real cap a `tasks` petaria a `public`. FK lògic (ORM); el CASCADE l'emula el collector de Django. |
| `pom` | FK → `POMMaster`, **PROTECT** | `:479` |
| `base_value_cm` | Decimal(7,2) nullable | `:481`. NULL = POM de l'item sense valor estàndard encara. |
| `tol_minus` / `tol_plus` | Decimal(5,2) nullable | `:484-485`. NULL → els consumidors cauen a `POMMaster.tolerancia_default_*`. |
| `nom_fitxa` | Char(20), blank | `:490`. Còpia literal de `BaseMeasurement.nom_fitxa`. |
| `origen` | Char(20), choices **MANUAL / PROMOTED / IMPORTED**, default MANUAL | `:499-507` |
| `created_at` | DateTime `auto_now_add`, **nullable** | `:508` |
| `updated_at` | DateTime `auto_now`, **nullable** | `:509` |
| `updated_by` | FK → `AUTH_USER_MODEL`, **SET_NULL** | `:511-514` |

**FET — els camps P9 del 22/07 HI SÓN.** `origen` + `created_at` + `updated_at` + `updated_by`
existeixen al model (`:492-514`) i a la migració `pom/0044_p9_itembasemeasurement_provinenca.py`.
`origen` és **read_only al serializer** i el determina el CAMÍ d'escriptura, no el body
(`pom/views.py:405-409`).

**FET — NO EXISTEIX cap camp d'eix a `ItemBaseMeasurement`:** ni `size_definition`, ni `customer`,
ni `target`, ni `construction`, ni `fit_type`, ni `size_system`. El model no té cap noció de món.

### 1.2 · Constraint d'unicitat exacte

**FET — `pom/models.py:520`:**

```python
unique_together = [('garment_type_item', 'pom')]
```

Res més. **Una fila per (item, POM) a tot el sistema.** Aquesta és la línia exacta que impedeix
que un mateix GTI porti dos jocs de valors.

### 1.3 · La premissa `base_size_definition` — CONFIRMADA llegint el model

**FET — `tasks/models.py:316-320`:**

```python
base_size_definition = models.ForeignKey(
    'pom.SizeDefinition', on_delete=models.SET_NULL,
    null=True, blank=True, related_name='base_for_items', ...)
```

**FK simple, nullable, SET_NULL. Un GTI = UNA talla base. NO és per eix, ni per res.** La
docstring de `ItemBaseMeasurement` ho declara explícitament (`pom/models.py:473`): «La talla a la
qual s'expressen aquests valors és `GarmentTypeItem.base_size_definition` (P1)».

L'única validació associada és `GarmentTypeItem.clean()` (`tasks/models.py:341-353`): la talla base
ha de pertànyer al `size_system` del `grading_rule_set` de l'item — **amb skip si algun dels dos és
NULL**, i **no és constraint de BD**.

**Cens a `fhort` (SELECT, 2026-07-24):** 62 GTI · **3 amb `base_size_definition`** · 4 amb
`grading_rule_set`.

### 1.4 · Qui escriu i qui llegeix `ItemBaseMeasurement`

**ESCRIPTORS (4 camins vius, tots gated CONFIGURE tret del loader):**

| Camí | Fitxer:línia | `origen` |
|---|---|---|
| CRUD pla del ViewSet (POST/PATCH) | `pom/views.py:379,382` | MANUAL |
| Acció `upsert` (la que fa servir la UI) | `pom/views.py:410-413` | MANUAL |
| **Promoció model→item** (P0/P2/P3, 22/07) | `models_app/views.py:3073-3081` | **PROMOTED** |
| Loader de paquet | `pom/management/commands/load_losan_package.py:356` | IMPORTED |

**FET — `derive_grading_rule_set` NO EXISTEIX.** `grep -rn "def derive_grading_rule_set"` = **0
resultats**. La funció està esborrada, no morta: només en queda una menció a una docstring
(`pom/grading_utils.py:472`). L'**equivalent viu per a bases SÍ existeix**: l'endpoint
`POST /api/v1/models/<id>/promoure-a-item/` (`models_app/views.py:2952-3090`), amb gate CONFIGURE
propi, dry-run per defecte i diff nous/canvien/iguals/sobrarien. Els «sobrarien» **mai s'esborren**
(`:2952-2955`: `ItemBaseMeasurement` no té `is_active`).

**Nota lateral (no és d'aquest abast):** `cerca_client_equivalent` (`pom/grading_utils.py:153`) SÍ
segueix existint amb **0 callers** — codi mort real. `cerca_contenidor_client`
(`pom/grading_utils.py:593`) està marcada DEPRECADA i li queda **1 caller**
(`pom/size_map_views.py:750`); és la tasca G5, ja amb nom.

**LECTORS — el call site de sembra:**

`materialize_poms_view` (`models_app/views.py:985-1100+`), l'acte «sembrar item→model». Llegeix les
IBM a `:1046-1047` i aplica el **GUARD DE TALLA P1** a `:1050-1069`:

- `base_size_definition` **NULL** → sembra + avís «talla de plantilla NO VERIFICADA» (`:1053-1056`).
- Model sense talla base → **cap VALOR**, sí la pertinença (`:1057-1062`).
- **Talles DIVERGENTS** → **cap VALOR**, sí la pertinença, avís explícit (`:1063-1069`):
  *«Un valor en una talla que no és la del model és una mesura falsa.»*

**Superfície d'autoria:** `MeasurementBaseGrid.jsx` (485 línies), muntada al pas 2 del wizard
d'item (`pages/ItemAuthoring.jsx:400`), i `components/model/MeasuresEntryPanel.jsx`. API a
`api/endpoints.js:568-571`.

### 1.5 · Recompte real avui (SELECT a `fhort`, 2026-07-24)

| Mètrica | Valor |
|---|---|
| GTI totals | **62** |
| GTI amb alguna `ItemBaseMeasurement` | **1** |
| Files `ItemBaseMeasurement` | **37** |
| Files amb `base_value_cm` NOT NULL | **2** |
| GTI amb `base_size_definition` | **3** |

**El cens 1/62 del 24/07 SEGUEIX IGUAL** després de tota la feina de la jornada (els 11 commits de
P7/P8 són superfície de federació Brand/Studio, no toquen la capa de plantilla).

> **Veredicte BLOC 1: llest.** L'esquema és net, provinençat i gated, però **pla**: `unique_together
> (item, pom)` + `base_size_definition` FK simple són les dues línies exactes que fan impossible la
> plantilla multi-món. El cost de dades de canviar-ho és **pràcticament nul avui** (37 files, 2 amb
> valor) — la finestra per fer-ho barat és ara.

---

## BLOC 2 — El matcher de grading com a patró a replicar

### 2.1 · El matcher unificat real

**FET — `pom/grading_utils.py:635-711`:**

```python
def resolve_grading_container(customer, size_system, target, construction, fit_type,
                              garment_group, garment_type_item=None):
```

Posicional (no keyword-only). **Retorna** `{'container': GradingRuleSet|None, 'motiu': str,
'candidats': list}` amb `motiu ∈ {'exact','ampli','none','ambiguous'}` (`:662-663`).

**Els tres nivells, tal com estan implementats:**

- **NIVELL 1 — identitat dura** (`:672-681`). Només s'avalua si hi ha item. Filtra
  `origen=CLIENT_RUN, actiu=True, customer, size_system, garment_type_item, fit_type`. **NO passa
  pel predicat d'eixos/abast**: és identitat, no disponibilitat. Sosté la constraint parcial
  `uniq_client_container_identity` (`pom/models.py:631-635`).
- **NIVELL 2 — ampli** (`:684-707`). `garment_type_item__isnull=True`, **del MATEIX client**
  (RUN-CLIENT: mai d'un altre), amb el predicat d'eixos (`targets__codi`, `construction__codi`,
  `fit_type__codi`) i el d'abast (`_scope_matches`). **Si falta target, construction o fit →
  retorna `none` immediatament** (`:693,697,701`): els tres són obligatoris al N2.
- **NIVELL 3** — cap → `None` (`:710`).
- **GUARDA D'AMBIGÜITAT** (`:678-679`, `:704-705`): >1 candidat a qualsevol nivell → `motiu
  ='ambiguous'` + la llista. **Mai el primer arbitràriament.**

**Com resol l'scope** — `_scope_matches` (`pom/grading_utils.py:613-632`): sense `scope_nodes` →
fallback al `garment_group` FK per CODI; amb nodes → casa si algun node ITEM/TYPE/GROUP coincideix.
És el **mirall exacte** de `scopeApplies(strict)` del frontend
(`components/grading/gradingAxes.js:88-102`), i el docstring ho declara com a contracte.

**Call site real:** `models_app/extraction_views.py:2149-2151` (confirmar import de fitxa). El fit
es resol allà amb `FitType.objects.filter(codi__iexact=model.fit_type).first()` (`:2146`) — el
`iexact` és el que salva la divergència de vocabulari `Model.fit_type='Regular'` vs
`FitType.codi='REGULAR'`.

### 2.2 · Grau d'acoblament REAL a `GradingRuleSet`

**FET — NO és parametritzable per domini avui.** Comptat sobre el cos executable (`:665-711`, ~45
línies):

| Línia | Acoblament |
|---|---|
| `:665` | `from fhort.pom.models import GradingRuleSet` |
| `:674` | `GradingRuleSet.objects.filter(...)` (N1) |
| `:675` | `origen=GradingRuleSet.ORIGEN_CLIENT_RUN, actiu=True` |
| `:676-677` | `customer=`, `size_system=`, `garment_type_item=`, `fit_type=` (camps del model) |
| `:686` | `GradingRuleSet.objects.filter(...)` (N2) |
| `:687-689` | `origen=…CLIENT_RUN, actiu=True`, `garment_type_item__isnull=True` |
| `:692` | `targets__codi=target` (M2M propi de GradingRuleSet) |
| `:696` | `construction__codi=construction` |
| `:700` | `fit_type__codi=fit_codi` |
| `:703` | `prefetch_related('scope_nodes', 'targets')` |
| `:615,617,625-626` (dins `_scope_matches`) | `rs.scope_nodes.all()`, `rs.garment_group_id`, `rs.garment_group.codi` |

**≈17 línies de 45 nomenen el model concret o camps seus.** L'acoblament NO és conceptual (la llei
N1/N2/N3 + guarda d'ambigüitat és domini-agnòstica) sinó **lèxic**: noms de model, noms de camp i
noms de relació incrustats.

**El que SÍ és reutilitzable tal qual, sense tocar res:**
- La **LLEI** (N1 identitat → N2 ampli → N3 cap, guarda d'ambigüitat, mai el primer).
- El **contracte de retorn** (`{container, motiu, candidats}`) i els 4 `motiu`.
- La **paritat frontend↔backend** ja establerta i documentada (`gradingAxes.js` ↔ `_scope_matches`).
- El **vocabulari d'eixos**: `pom_target` (13 codis), `pom_fittype` (10 codis),
  `pom_constructiontype` (4 codis) — catàlegs compartits, no cal duplicar-los.

**El que NO és reutilitzable sense refactor:** el cos de la funció.

> 💡 **PROPOSTA (a validar):** extreure `_resol_per_nivells(qs_base, eixos, scope_fn)` amb el
> queryset i el resolutor d'scope injectats, i deixar `resolve_grading_container` com a wrapper de
> 6 línies. El risc del refactor és **contingut i mesurable**: `resolve_grading_container` té **1
> sol caller** (`extraction_views.py:2149`) i el predicat d'scope té test de paritat al frontend
> (`components/grading/gradingAxes.test.js`).

### 2.3 · `RuleSetScopeNode` — reutilitzable, duplicable o generalitzable?

**FET — `pom/models.py:642-696`.** Estructura: FK dur `rule_set → GradingRuleSet` CASCADE (`:657`)
+ `node_type` (GROUP/TYPE/ITEM) + **3 FK d'eix mútuament exclusius** (`:658-666`, l'item amb
`db_constraint=False` per la mateixa raó cross-schema).

**El que sosté la seva integritat són 3 `UniqueConstraint` PARCIALS** (`:671-680`):

```python
UniqueConstraint(fields=['rule_set','garment_group'], condition=Q(node_type='GROUP'), name='uniq_scope_group')
UniqueConstraint(fields=['rule_set','garment_type'],  condition=Q(node_type='TYPE'),  name='uniq_scope_type')
UniqueConstraint(fields=['rule_set','garment_type_item'], condition=Q(node_type='ITEM'), name='uniq_scope_item')
```

més `clean()` (`:682-688`), que exigeix EXACTAMENT el FK del seu `node_type`.

**NO és reutilitzable tal qual** per a un segon domini: `rule_set` és un FK dur a `GradingRuleSet`,
i les 3 constraints hi estan ancorades pel nom del camp.

**Cost real de cada via, mesurat:**

| Via | Què costa | Què arrisca |
|---|---|---|
| **Generalitzar** amb `content_type`+`object_id` | 1 migració (AddField ×2, RemoveField ×1, RunPython de backfill dels 11 nodes) + reescriure les 3 constraints amb `content_type` al `fields` + reescriure `clean()` + tocar els **6 punts de codi** que fan `rule_set=` o `rs.scope_nodes` (`grading_utils.py:552-580,615`, `backfill_ruleset_scope.py:65`, `seed_scope_nodes_proposals.py:144`, `seed_losan_grading_v3.py:176`, `export/load_losan_package.py`) | **Les constraints parcials són el que impedeix duplicats que una composta amb NULLs deixaria passar** (`:671-673`, comentari explícit). Reescriure-les amb un `content_type` al mig és el punt fràgil. Tota la cadena de paquet LOSAN (export+load) passa a haver de resoldre ContentType — cross-schema amb `pom` SHARED. |
| **Duplicar** com a `BaseSetScopeNode` | 1 migració (CreateModel), ~55 línies calcades, +1 model, +1 mirror de `_scope_matches` | Dos llocs on canviar la llei d'abast quan canviï. La **paritat frontend** (`gradingAxes.js`) es duplica també, o es parametritza per camp. |

**Cens a BD (2026-07-24):** 11 nodes (9 ITEM · 1 TYPE · 1 GROUP) sobre **5 rulesets dels 45**.
Rulesets: 22 CLIENT_RUN · 19 CANONICAL · 22 amb customer · **1 amb `garment_type_item`**.

**Aquest és el fet incòmode del bloc:** D-CONS (`DECISIONS.md:239-240`) va declarar `RuleSetScopeNode`
**font única del ventall**, i l'ordre inamovible P4-abans-de-P5 hi és precisament perquè
«6/45 rulesets tenen nodes». Avui són **5/45**. **La font única encara no és font de res al 89%**, i
P4 està declarat com a **criteri de domini** (sessió de treball amb la Montse), no com a tasca
d'agent. Penjar-hi un segon domini abans de poblar-la multiplica un buit, no una capacitat.

> **Veredicte BLOC 2: cal decidir.** La llei del matcher és **reutilitzable i provada**; el cos de
> la funció **no**, però l'extracció és mecànica i té 1 sol caller. `RuleSetScopeNode` **no és
> reutilitzable tal qual**, i les seves 3 constraints parcials fan la generalització genuïnament més
> cara que la duplicació. **Bandera de precedència:** P4 (poblar l'àmbit) és previ a qualsevol
> disseny que en depengui.

---

## BLOC 3 — La matriu real de necessitat (LOSAN com a cas de prova)

### 3.0 · Reconciliació del cens del 24/07 (els «85 parells»)

**FET, i quadra exactament.** El nombre depèn del filtre:

| Universo | Parells (GTI × size_system) |
|---|---|
| Només sistemes de talles LOSAN (`codi LIKE '%LOS%'`) | **85** ← el del cens |
| Models del customer LOSAN IBERIA SA | 87 |
| **Tots els models de `fhort`, tots dos camps NOT NULL** | **97** |

La diferència són els sistemes genèrics `ALPHA_EU_W` / `ALPHA_EU_M` (no LOSAN). Els **15 GTI-món ⭐**
i els **6 mono-sistema** del cens coincideixen **exactament** amb el que dona la BD avui — mateix
univers, només un filtre distint al comptador. Models a `fhort`: **1.056** (1.013 LOSAN · 41
Brownie · 2 FHORT), **1.025 amb GTI**, 27 GTI distints amb models.

### 3.1 · La col·lisió NO és hipotètica: està mesurada

La pregunta del brief era comptar «candidats a col·lisió real». **Es pot contestar amb una dada més
dura que el target: la TALLA BASE.** Una `ItemBaseMeasurement` està expressada en UNA talla
(`GarmentTypeItem.base_size_definition`, `pom/models.py:473`). Si dos models del mateix GTI tenen
talles base distintes, **els seus valors base no poden compartir fila, per definició** — abans i
tot d'entrar a debatre si el patró és el mateix.

**FET (SELECT) — talles base distintes per GTI, dels 15 ⭐:**

| GTI | n size_systems | n talles base | Talles base observades |
|---|---|---|---|
| trousers | 9 | **6** | 2, 8, 38, 42, M, S |
| shorts | 9 | **6** | 2, 8, 38, 42, M, S |
| casual_jacket | 7 | 5 | 03/06, 2, 8, M, S |
| skirt_straight | 5 | 5 | 03/06, 2, 8, 38, S |
| jeans | 7 | 5 | 2, 8, 38, 42, M |
| polo | 6 | 5 | 03/06, 2, 8, M, S |
| shirt_woven | 6 | 5 | 03/06, 2, 8, L, M |
| hoodie | 7 | 5 | 00/01, 03/06, 2, 8, M |
| sweater | 6 | 5 | 00/01, 03/06, 2, 8, S |
| t_shirt | 7 | 4 | 2, 8, M, S |
| blouse | 5 | 4 | 03/06, 2, 8, S |
| swim_shorts | 3 | 3 | 2, 8, M |
| swimsuit | 3 | 3 | 2, 8, S |
| dress_simple | 3 | 3 | 2, 8, S |
| baby_dress | 2 | 2 | 00/01, 03/06 |

**Els 15 ⭐ tenen TOTS ≥2 talles base. Cap dels 15 pot compartir plantilla. Zero excepcions.**
La resposta de l'Agus del 24/07 («com a mesures base és diferent») queda **confirmada per la
estructura de les dades, no per intuïció**: no cal ni discutir si un `shorts YOUTH_BOY` i un
`shorts YOUTH_GIRL` porten el mateix patró — l'un es mesura a la talla `8` i l'altre a una altra, i
un valor expressat en la talla equivocada és, en paraules del propi guard P1
(`models_app/views.py:1068`), **«una mesura falsa»**.

**El cas que ho fa més evident**, i que el target NO capta: `shorts` i `trousers` tenen
`MAN_LOS_01` i `MAN_NUM_LOS_01` — **mateix target `MAN`, dos sistemes de talles** (alfa i numèric),
talles base `M` i `42`. **Mateixa peça, mateix públic, valors base necessàriament distints.** Això
demostra que **l'eix que força la separació és `size_system`, no `target`** — i el disseny del
BaseSet ho ha de respectar.

**Cost mesurat de NO tenir BaseSet condicionat** (triant per a cada GTI la talla base que cobreix
més models — el millor cas possible):

| GTI | Models amb talla base | Coberts (millor tria) | **Refusats pel guard P1** | % |
|---|---|---|---|---|
| t_shirt | 208 | 65 | **143** | 68,8% |
| shorts | 105 | 42 | **63** | 60,0% |
| jeans | 71 | 26 | **45** | 63,4% |
| trousers | 62 | 18 | **44** | 71,0% |
| dress_simple | 69 | 32 | **37** | 53,6% |
| swimsuit | 48 | 22 | 26 | 54,2% |
| swim_shorts | 51 | 25 | 26 | 51,0% |
| baby_dress | 49 | 25 | 24 | 49,0% |
| casual_jacket | 30 | 10 | 20 | 66,7% |
| shirt_woven | 69 | 53 | 16 | 23,2% |
| sweater | 21 | 6 | 15 | 71,4% |
| hoodie | 22 | 8 | 14 | 63,6% |
| polo | 23 | 13 | 10 | 43,5% |
| blouse | 42 | 32 | 10 | 23,8% |
| skirt_straight | 13 | 5 | 8 | 61,5% |
| *(els 12 mono-talla)* | 141 | 141 | **0** | 0% |
| **TOTAL** | **1.025** | **524** | **501** | **48,9%** |

**Titular: en el millor escenari possible sense BaseSet condicionat, la meitat del catàleg no pot
rebre plantilla.** I no falla en silenci: falla amb el missatge «TALLES DIVERGENTS» del guard P1.
La **urgència màxima** és `t_shirt` (143 models refusats, 68,8%), seguida de `shorts` (63) i `jeans`
(45).

### 3.2 · Ordre de magnitud del BaseSet (quantes files calen)

**FET (SELECT):**

| Granularitat de la clau | Files de BaseSet |
|---|---|
| (GTI × talla base) | **78** |
| (GTI × size_system × talla base) | **98** |
| (GTI × size_system) — el «85» del cens en univers LOS | 97 |

**La resposta a «un per parell o se'n poden compartir»:** amb clau (GTI × size_system) calen **97**
files de capçalera; si s'agrupa per talla base efectiva, **78** — és a dir, **19 parells
comparteixen talla base amb un altre parell del mateix GTI**. Aquests 19 són **exactament els
candidats a compartir**, i **cap d'ells és compartible sense mirar-s'ho un a un**: compartir talla
base no implica compartir valors (`MAN_LOS_01` i `WOMAN_LOS_01` poden coincidir a `M` i tenir
pitral molt diferent).

**Estimació de volum de dades:** amb ~10-25 POMs per item (les 37 files actuals són d'1 sol GTI),
78-98 capçaleres × ~15 POMs ≈ **1.200-1.500 files de valor** al catàleg complet. Ordre de magnitud
**petit**: cap consideració de rendiment.

> **Veredicte BLOC 3: llest.** Els 15 ⭐ necessiten **tots** condicionament; queda demostrat per
> talla base, no per intuïció. El cost de no fer-ho és **501 models (48,9%) sense plantilla
> possible**. La dimensió del BaseSet és **78-98 capçaleres**, i **cap compartició és segura sense
> revisió humana**. L'eix discriminant és **`size_system`**, no `target`.

---

## BLOC 4 — Els altres dos actius: patrons DXF i sketches

### 4.1 · `PatternFile` — ancoratge dual XOR, **zero eixos**

**FET — `patterns/models.py:33-135`.** Ancoratge: **XOR real a BD**
(`CheckConstraint patternfile_xor_model_item`, `:108-115`) entre `model` (`:42-45`) i
`garment_type_item` (`:46-50`), més `source_asset → ItemFitxer` (`:53-56`), cadena de versions
(`:59-64`), bytes DXF+RUL (`:67-76`), empremta CAD (`:79-95`) i `UniqueConstraint` anti-bifurcació
(`:121-124`).

**FET — `grep -n "size_system\|target\|customer\|fit_type\|construction" patterns/models.py` = **0
resultats**.** `PatternFile` **NO té CAP eix**. Ancora **només** a l'item (branca XOR) o al model.

**CONFIRMAT: pateix EXACTAMENT la mateixa limitació que `ItemBaseMeasurement`.** Un GTI únic amb 6
mons no pot portar 6 DXF base diferenciats: els portaria tots barrejats sota el mateix ancoratge,
sense res que digui quin és de quin món. **El disseny condicionat els ha de cobrir tots dos.**

**Cens a BD:** **5 `PatternFile`, totes de MODEL (174, 186×3, 163), zero d'item.** Els 5 models són
`base_size_label='S'`, `fit_type='Regular'`, `target='WOMAN'` — **una sola cel·la de la matriu**.
La branca item del XOR és **codi viu amb zero exercici** (té test a `patterns/tests.py:937-957`,
però cap fila real).

**Nota positiva verificada:** el Risc #1 de la diagnosi del 21/07 (`adapters.py` retornant 0
costures en silenci per a patrons d'item) **està tancat**: `patterns/adapters.py:585-604` ara
declara explícitament el problema a la llista de `problemes` (`:596-604`) amb docstring que ho
eleva a llei (`:592-595`).

### 4.2 · `ItemFitxer` (sketches) — mateix check, mateix resultat

**FET — `models_app/models.py:485-522`.** Camps: `garment_type_item` FK CASCADE (`:497-498`),
`nom_fitxer`, `tipus` (reusa `ModelFitxer.TIPUS_CHOICES`, `:500-501`, que inclou `SKETCH_FLETXES`,
`SKETCH_NET`, `SKETCH_SVG`, `PATRO`, `ESCALAT`, `RUL` — `models_app/models.py:376-388`), cadena de
versions, autoria, bytes.

**FET — cap eix.** L'ancoratge és **`garment_type_item` i prou**. La docstring (`:492-496`) declara
que camps es van ometre deliberadament («S'afegiran si algun dia hi ha un cas, no per simetria»).

**Cens a BD: `ItemFitxer` té ZERO files.** No hi ha ni un sketch de catàleg al sistema. El ViewSet
és complet (`models_app/item_fitxer_views.py:28-85`, gated CONFIGURE, amb `usar_al_model`,
`download_signed`, versions) — **superfície construïda, mai exercida**.

### 4.3 · Una taula («GTIVariant») o tres paral·leles?

**La pregunta demanava respondre AMB DADES. La dada més important és incòmoda: l'eix `fit` no es
pot argumentar, perquè no té variància.**

**FET (SELECT sobre 1.056 models de `fhort`):**

| Eix | Valors observats |
|---|---|
| `fit_type` | **`Regular` × 1.056. UN SOL VALOR.** (el catàleg `pom_fittype` en té 10: REGULAR, SLIM, RELAXED, OVERSIZED, FLARED, TAPERED, STRAIGHT, BODYCON, ATHLETIC, CUSTOM) |
| `construction` | KNIT 452 · WOVEN 433 · STRETCH_KNIT 119 · buit 52 |
| `target` | WOMAN 198 · MAN 146 · GIRL 139 · TEEN_GIRL 114 · BOY 104 · TEEN_BOY 92 · TODDLER_GIRL 88 · TODDLER_BOY 78 · buit 51 · BABY_GIRL 26 · BABY_BOY 19 · **`Woman` 1** |

**Conseqüència directa:** l'exemple del brief — «un DXF compartit entre WOMAN REGULAR i WOMAN
OVERSIZE mentre les mesures base sí difereixen» — **no té ni un sol cas real al sistema**. Hi ha 5
PatternFile, totes del mateix (WOMAN, Regular, S). **Aquesta hipòtesi NO es pot ni confirmar ni
refutar amb les dades de `fhort` avui.**

**L'evidència que SÍ existeix, i que apunta en la mateixa direcció per un camí diferent:**

**FET — un patró NO porta talla; l'adquireix del MODEL al moment de projectar.**
`patterns/adapters.py:450-476`, docstring C1 literal:

> «el context ve del MODEL, recorrent `grading_version.size_fitting.model`. `GradingVersion` NO té
> FK a `Model`, i `GradedSpec` no sap quina és la talla base […] Es llegeix declarada de
> `Model.base_size_label`, i el size run de `Model.size_run_model`.»

Contrasta-ho amb `ItemBaseMeasurement`, on la talla **és** part de la definició del valor
(`pom/models.py:473`).

**Són naturaleses distintes, no dos camps del mateix registre:**

| | `ItemBaseMeasurement` | `PatternFile` (DXF) | `ItemFitxer` (sketch) |
|---|---|---|---|
| Porta talla pròpia? | **SÍ** (via `base_size_definition`) | **NO** — la rep del model en projectar (`adapters.py:475-476`) | **NO** — és un dibuix |
| Unitat | valor numèric per POM | geometria + empremta CAD | bytes |
| Versionat | **NO** (`update_or_create`) | **SÍ** (cadena `versio_anterior`, `patterns/models.py:59-64`) | **SÍ** (`models_app/models.py:502-507`) |
| Cardinalitat per ancoratge | 1 per (item, pom) | N (cadena de versions) | N (cadena, per `tipus`) |
| Exercici real avui | 37 files, 1 GTI | 5 files, **0 d'item** | **0 files** |

**Argument estructural (independent de les dades de fit):** fusionar-los en un `GTIVariant` únic
imposaria una **cardinalitat comuna** a tres coses que ja NO la tenen — una taula amb versionat de
fitxers i valors sense versionat al mateix registre. I obligaria a crear una fila de variant per a
un sketch encara que les mesures base d'aquell món no existeixin (avui: 0 sketches, 0 DXF d'item, i
mesures base en 1 GTI de 62). **Els tres dominis tenen ritmes d'ompliment radicalment diferents.**

> 💡 **PROPOSTA (a validar):** l'evidència disponible afavoreix **eixos compartits, taules
> separades** — un mateix VOCABULARI d'eixos (els mateixos 5 del `GradingRuleSet`) i un mateix
> matcher, però **tres ancoratges independents**. Cadascun pot condicionar-se pel subconjunt d'eixos
> que la seva naturalesa demana (les bases segur que per `size_system`; el DXF potser només per
> `target`+`construction`), i cadascun s'omple al seu ritme. **Reserva honesta:** amb `fit` constant
> a tot el catàleg, la variància independent DXF-vs-bases **no està demostrada empíricament** — és
> un argument d'estructura i de ritme d'ompliment, no de dades observades. Si l'Agus té el cas real
> al cap (dos fits amb el mateix patró base), val més la seva evidència de domini que aquest cens.

> **Veredicte BLOC 4: cal decidir, amb una dada que falta.** Confirmat que `PatternFile` i
> `ItemFitxer` pateixen **exactament** la mateixa limitació que `ItemBaseMeasurement` (ancoratge pla,
> zero eixos) i que el disseny condicionat els ha de cobrir tots tres. **La pregunta «una taula o
> tres» NO es pot tancar amb les dades de `fhort`**: l'eix `fit` té un sol valor a 1.056 models. Ho
> ha de tancar el criteri de domini.

---

## BLOC 5 — Welford (la raó original de separar per món, 18/07)

### 5.1 · La clau és `(item, task_type)` i el BaseSet NO la toca

**FET — `tasks/models.py:359-377`:**

```python
class TaskTimeEstimate(models.Model):
    garment_type_item = FK(GarmentTypeItem, ...)
    task_type = FK(TaskType, ...)
    estimated_minutes / n / mean_minutes / m2
    class Meta:
        unique_together = [('garment_type_item', 'task_type')]   # :372
```

**FET — l'alimentació** (`tasks/services_i.py:19-45`): `record_actual_time` obté la cel·la amb
`get_or_create(garment_type_item_id=item_id, task_type=...)` (`:31-32`) — **cap eix de món**. El
llindar seed→estadística és **`WELFORD_MIN_SAMPLES = 5`** (`:10`), aplicat a `effective_minutes`
(`:53`).

**FET — el sistema ja té consciència del límit d'aquesta clau.** `tasks/views_b.py:1208-1210`
documenta explícitament que «L'eix tècnic (`TaskTimeEstimate`, `garment_type_item × task_type`) NO
té dimensió model».

**Conclusió del brief CONFIRMADA:** si el GTI es queda únic per peça, la cel·la de temps **segueix
barrejant** «cosir un t_shirt de nadó» amb «cosir un t_shirt d'home». El BaseSet condicionat és
domini de **MESURES**; **no resol ni toca** el problema que va motivar la separació NEWBORN del
18/07. **Són dos problemes independents que comparteixen causa.**

### 5.2 · Volum real — la recomanació, amb dades

**FET (SELECT) — cel·les Welford:** 460 files · **20 amb `n > 0`** · 14 amb `estimated_minutes` ·
57 GTI distints.

**Les 4 úniques cel·les que creuen el llindar `n ≥ 5`** (les úniques que el planificador realment
fa servir):

| GTI × task_type | n | mean_minutes | Mons dels seus models |
|---|---|---|---|
| tracksuit_pant × pom | 17 | 562,29 | ALPHA_EU_W / WOMAN — **1 sol món** |
| shirt_woven × size_check | 7 | 784,71 | ALPHA_EU_M / MAN — **1 sol món** |
| blouse × pom | 5 | 4,40 | ALPHA_EU_W / WOMAN — **1 sol món** |
| dress_fancy × size_check | 5 | 255,00 | ALPHA_EU_W / WOMAN — **1 sol món** |

**CAP de les 4 cel·les efectives està contaminada avui.**

**Però la contaminació ja està passant, i és observable.** FET — les `ModelTask` de `t_shirt × pom`
vénen de **3 mons diferents**:

| GTI × task | size_system | target | n ModelTask |
|---|---|---|---|
| t_shirt × pom | ALPHA_EU_W | WOMAN | 1 |
| t_shirt × pom | WOMAN_LOS_01 | WOMAN | 1 |
| t_shirt × pom | YOUTH_BOY_LOS_01 | **TEEN_BOY** | 1 |

Les tres alimentarien **la mateixa cel·la** `(t_shirt, pom)` en completar-se. **Encara no ho han
fet** (`t_shirt` no apareix entre les 20 cel·les amb `n > 0`: les tasques existeixen però no han
consolidat temps real). El mateix passa a `shirt_woven` (ALPHA_EU_M/MAN + ALPHA_EU_W/sense target).

**Volum total de tasques:** només **16 parells (GTI × size_system)** tenen alguna `ModelTask`; el
més gros és `blouse × ALPHA_EU_W` amb 50 tasques, i **només 3 GTI tenen tasques en més d'un món**
(t_shirt, shirt_woven, i marginalment sweater/skirt_straight via BABY_LOS_01).

### 5.3 · Recomanació

> 💡 **PROPOSTA (a validar): Welford POT ESPERAR; el BaseSet NO.**
>
> - **El BaseSet és urgent i quantificat:** 501 models (48,9%) no poden rebre plantilla avui, i el
>   guard P1 els refusa **ara mateix**, no en el futur.
> - **Welford és latent:** la barreja és estructuralment certa (3 mons a `t_shirt × pom`), però
>   **0 de les 4 cel·les efectives** està contaminada, i el volum total (16 parells amb tasques, 3
>   amb multi-món) és **massa petit per distorsionar cap mitjana** que el planificador faci servir.
> - **Quan deixarà de poder esperar:** quan la segona temporada real entri i les cel·les multi-món
>   creuin `n ≥ 5` amb mostres de mons diferents. El senyal de vigilància concret és
>   **`t_shirt × pom`**: 208 models, 7 sistemes de talles, 3 mons ja amb tasques obertes.
> - **Cost d'esperar:** afegir l'eix a `TaskTimeEstimate` més tard és **una migració amb backfill
>   ambigu** (no se sabrà de quin món venia cada mostra històrica un cop acumulada a `mean_minutes`
>   / `m2` — Welford és irreversible). Fer-ho abans que les cel·les acumulin és barat; després,
>   significa **descartar l'històric**. Amb 20 cel·les amb `n>0` i 4 efectives, **l'històric que es
>   perdria avui és negligible**. La finestra barata és ampla però no eterna.

**Anomalia anotada, no investigada:** `tracksuit_pant × pom` té `n=17` però només existeix **1
`ModelTask`** d'aquell GTI. El comptador no es reconcilia amb el cens de tasques actual.
`TaskTimeEstimateViewSet` és un `ModelViewSet` complet (`tasks/views_b.py:970-972`), o sigui que
`n` és **escrivible per API** — probablement l'origen. Fora d'abast; s'anota.

> **Veredicte BLOC 5: llest.** La clau Welford **NO queda resolta** pel BaseSet (domini distint), la
> barreja **ja passa** però **encara no distorsiona res**, i la recomanació és **diferir-ho amb un
> senyal de vigilància** (`t_shirt × pom`), sabent que el cost de diferir creix amb l'acumulació.

---

## BLOC 6 — Taula de decisió (dimensionament, NO decisió)

Les 4 opcions del brief són **dues preguntes ortogonals**: A-vs-B és *com es modela l'abast*;
C-vs-D és *quantes taules d'actiu*. Es poden combinar (A+C, A+D, B+C, B+D).

### Pregunta 1 — Com es modela l'abast

| Opció | Cost estimat (migracions + model + matcher + UI) | Risc | Reutilitza |
|---|---|---|---|
| **A · Generalitzar `RuleSetScopeNode` amb `content_type`** | **Migracions:** 1 (AddField `content_type`+`object_id`, RemoveField `rule_set`, RunPython backfill dels 11 nodes) · **Model:** reescriure 3 `UniqueConstraint` parcials + `clean()` (`pom/models.py:671-688`) · **Matcher:** `_scope_matches` passa a rebre la relació per paràmetre (`grading_utils.py:613-632`) · **Callers a tocar: 6** (`grading_utils.py:552-580`, `backfill_ruleset_scope.py:65`, `seed_scope_nodes_proposals.py:144`, `seed_losan_grading_v3.py:176`, `export_losan_package.py:299`, `load_losan_package.py:391`) · **UI:** `GradingRuleSets.jsx:748-751,808,899` (l'editor ja reusa `CascadeSelector` multi — **cap component nou**) | **MITJÀ-ALT.** Les 3 constraints parcials són la garantia d'integritat i el comentari del codi ho declara explícitament (`:671-673`); reescriure-les amb `content_type` al mig és el punt fràgil. **Bandera cross-schema:** `pom` és SHARED i tota la cadena de paquet LOSAN (export+load) hauria de resoldre ContentType — el mateix motiu pel qual `garment_type_item` va amb `db_constraint=False` (`:665`) | **Alt.** 1 sol model d'abast, 1 sola llei, 1 sol punt on canviar-la. El `CascadeSelector` i la paritat frontend serveixen els dos dominis |
| **B · Duplicar-lo com a `BaseSetScopeNode`** | **Migracions:** 1 (CreateModel) · **Model:** ~55 línies calcades de `pom/models.py:642-696` · **Matcher:** un mirall de `_scope_matches` (~20 línies) o parametritzar-lo per nom de relació · **Callers a tocar: 0** (els 6 existents no es toquen) · **UI:** `CascadeSelector` es reusa tal qual | **BAIX.** No toca res existent. Cap migració de dades. El grading segueix exactament igual | **Mitjà.** Reusa la LLEI, el `CascadeSelector` i el vocabulari d'eixos, **no** el model. **Deute:** dos llocs on canviar la llei d'abast quan canviï, i la paritat frontend es duplica |

**Bandera comuna a A i B (bloquejant per a totes dues):** `RuleSetScopeNode` té **11 nodes sobre 5
rulesets dels 45** — la «font única del ventall» de D-CONS (`DECISIONS.md:239-240`) està buida al
89%, i el propi D-CONS declara **«ORDRE INAMOVIBLE: P4 (poblar scope-nodes) ABANS de P5»**, amb P4
com a **criteri de domini** (sessió amb la Montse), no tasca d'agent. Penjar-hi un segon domini
abans de P4 multiplica un buit.

### Pregunta 2 — Quantes taules d'actiu

| Opció | Cost estimat | Risc | Reutilitza |
|---|---|---|---|
| **C · Una taula `GTIVariant` (bases + DXF + sketch junts)** | **Migracions:** 2-3 (CreateModel `GTIVariant`; AlterUniqueTogether a `ItemBaseMeasurement` `(item,pom)`→`(variant,pom)` + AddField + RunPython de les 37 files; AddField a `PatternFile` i `ItemFitxer`) · **Model:** 1 nou + 3 alterats · **Matcher:** 1 resolutor · **UI:** `MeasurementBaseGrid.jsx` (485 l.) i `ItemAuthoring.jsx` (426 l.) passen a tenir selector de variant; 1 CRUD nou de variants | **ALT.** Imposa **cardinalitat comuna** a tres coses que no la tenen: les bases fan `update_or_create` sense versionat; DXF i sketch tenen **cadena de versions** amb `UniqueConstraint` anti-bifurcació (`patterns/models.py:121-124`) i `is_current`. Obliga a crear variant per a un sketch encara que no hi hagi mesures d'aquell món. **Ritmes d'ompliment incompatibles:** 37 files / 5 files (0 d'item) / **0 files** | **Alt en concepte** (1 sol lloc on viuen els eixos, 1 sol matcher, 1 sol CRUD), **baix en codi existent** (les 3 taules s'han de re-ancorar) |
| **D · Tres taules paral·leles amb el mateix patró d'eixos** | **Migracions:** 3 independents i **seqüenciables** (bases primer, DXF i sketch quan toqui) · **Model:** 3 capçaleres amb el mateix joc d'eixos · **Matcher:** 1 resolutor genèric amb 3 crides · **UI:** només `MeasurementBaseGrid`+`ItemAuthoring` a la 1a onada; DXF i sketch **no es toquen fins que calgui** | **BAIX-MITJÀ.** Cada domini es pot fer i validar sol. El risc real és **divergència** entre les 3 definicions d'eix si no s'extreu una base comuna (mixin abstracte). **Cost de dades avui: gairebé nul** (37 + 5 + 0 files) | **Alt.** Cada taula manté la seva cardinalitat i el seu versionat intactes. `PatternFile` i `ItemFitxer` **no es toquen** fins que hi hagi un cas real (avui: 0 DXF d'item, 0 sketches) |

### Combinacions i el que cadascuna implica

| Combinació | Perfil |
|---|---|
| **B + D** | Cost total més baix i **entregable per fases**. Zero risc sobre el grading viu. Deute: 2 llocs on viu la llei d'abast |
| **A + D** | Cost mitjà, arquitectura més neta a llarg termini. **Bloquejada de facto per P4** |
| **A + C** | Cost màxim, disseny més «pur». El pitjor moment per fer-ho: 0 dades a 2 dels 3 dominis |
| **B + C** | Combinació incoherent (duplica l'abast però fusiona els actius) |

### Dada que fa de contrapès a tot el dimensionament

**El cost de DADES és avui pràcticament nul en els tres dominis** — 37 files d'`ItemBaseMeasurement`
(2 amb valor), 5 `PatternFile` (cap d'item), 0 `ItemFitxer`. **Sigui quina sigui l'opció, mai serà
tan barat com ara.** El que **no** és barat és el context de codi ja construït al voltant (matcher,
constraints, paritat frontend, cadena de paquet LOSAN).

---

## Taula final de riscos i banderes per al CTO

| # | Fet | Estat | Impacte |
|---|---|---|---|
| R1 | **501 de 1.025 models (48,9%) no poden rebre valor de plantilla**, ni triant la millor talla base per GTI. El guard P1 (`models_app/views.py:1063-1069`) els refusa amb «TALLES DIVERGENTS» | **VIU, mesurat avui** | **Alt** — és la justificació sencera del BaseSet |
| R2 | `RuleSetScopeNode`: **11 nodes / 5 rulesets dels 45**. La «font única del ventall» (D-CONS, `DECISIONS.md:239-240`) està buida al 89%, i P4 és criteri de domini, no tasca d'agent | **VIU** | **Alt — bloquejant de precedència.** Cap disseny que en depengui hauria d'anar abans de P4 |
| R3 | `resolve_grading_container` (`grading_utils.py:635-711`) NO accepta un domini com a paràmetre: **~17 de 45 línies nomenen `GradingRuleSet`**. Cal extreure'n el predicat | **VIU** | **Mitjà** — mecànic, i té **1 sol caller** (`extraction_views.py:2149`) |
| R4 | `PatternFile` (`patterns/models.py:33-135`) i `ItemFitxer` (`models_app/models.py:485-522`) tenen **ZERO camps d'eix**: ancoren només a l'item. **Mateixa limitació exacta que les bases** | **VIU, confirmat per `grep`** | **Mitjà** — cap urgència de dades (0 files d'item als dos) |
| R5 | **`fit_type = 'Regular'` a 1.056 de 1.056 models.** L'eix `fit` no té variància al sistema: la hipòtesi «DXF compartit entre REGULAR i OVERSIZE» **no es pot verificar amb dades** | **VIU** | **Alt per a la decisió C-vs-D** — la resposta l'ha de donar el criteri de domini |
| R6 | La cel·la Welford `(item, task_type)` (`tasks/models.py:372`) **ja barreja mons**: 3 `ModelTask` de `t_shirt × pom` de 3 sistemes de talles. **Cap de les 4 cel·les amb `n ≥ 5` està contaminada encara** | **LATENT** | **Baix avui, creixent.** Welford és **irreversible**: el backfill posterior implicaria descartar l'històric |
| R7 | 1 model amb `target='Woman'` (vs `'WOMAN'`). El matcher filtra `targets__codi=target` **exacte** (`grading_utils.py:692`), sense `iexact` — a diferència del fit, que sí el porta (`extraction_views.py:2146`) | **VIU** | **Baix** — 1 model, però el mateix patró es repetiria a qualsevol BaseSet que copiï el predicat |
| R8 | `TaskTimeEstimate.n = 17` a `tracksuit_pant × pom` amb **1 sola `ModelTask`** viva d'aquell GTI. `TaskTimeEstimateViewSet` és `ModelViewSet` complet (`tasks/views_b.py:970-972`) → `n` escrivible per API | **ANOTAT, no investigat** | **Baix** — fora d'abast |
| R9 | `cerca_client_equivalent` (`grading_utils.py:153`) té **0 callers** (codi mort real). `cerca_contenidor_client` (`:593`) en té **1** (`size_map_views.py:750`) — la tasca G5 | **ANOTAT** | **Baix** — higiene, ja amb nom |
| R10 | Risc #1 de la diagnosi del 21/07 (`adapters.py`, 0 costures en silenci per a patrons d'item) **TANCAT**: ara es declara explícitament (`patterns/adapters.py:596-604`) | **RESOLT** | — |

---

## Preguntes obertes per a la sessió amb l'Agus (Patró C)

1. **Quins eixos condiciona cada actiu?** Les dades diuen que les bases es condicionen **com a
   mínim per `size_system`** (BLOC 3.1: `MAN_LOS_01` vs `MAN_NUM_LOS_01`, mateix target, talles base
   `M` i `42`). Per al DXF i el sketch **no hi ha dades**: cal criteri.
2. **Una taula o tres?** (BLOC 4.3). L'evidència d'estructura i de ritme d'ompliment afavoreix
   tres; l'evidència de fit **no existeix**. Si l'Agus té el cas real al cap, mana el seu criteri.
3. **P4 abans o alhora?** (R2). Poblar `RuleSetScopeNode` és previ per D-CONS. ¿El BaseSet espera P4,
   o neix amb el seu propi abast per no quedar-hi encadenat?
4. **Welford ara o després?** (BLOC 5.3). Recomanació dimensionada: després — amb el senyal de
   vigilància `t_shirt × pom` i sabent que el cost creix amb l'acumulació.
5. **Els 19 parells que comparteixen talla base** (BLOC 3.2) — ¿es fusionen per defecte o es
   mantenen separats i que el tècnic decideixi? Compartir talla base **no** implica compartir valors.

---

*Diagnosi Patró A. Res tocat: cap codi, cap schema, cap dada. L'única escriptura de la sessió és
aquest fitxer (la resta de modificats/untracked del `git status` són previs a la sessió).*
