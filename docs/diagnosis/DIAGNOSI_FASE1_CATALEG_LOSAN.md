# FASE 1 · Completar catàleg LOSAN — Verificació (Patró A) + GATE

> Read-only. Staging · BD `ftt_staging` · schema `fhort` · branca `dev`. Data: 2026-07-18.
> **RESULTAT DEL GATE: ATURAT abans de FASE B.** A5 no té via neta → decisió d'Agus.
> Tot per clau natural (codi/slug). Cap escriptura executada.

---

## Veredicte

- A1, A2, A3, A4, A6 → **verds**, cap contradicció amb el pla.
- **A5 → BLOCADOR.** La identitat del contenidor de grading és
  `(customer + size_system + garment_type_item + fit_type)` — el **gènere no hi és**.
  Els dos únics casos de col·lisió del BLOC B3 (youth `t_shirt` i youth `trousers`,
  noi vs noia sobre el mateix run) **no es poden separar per cap via neta**.
- Regla del brief: *"Si tot és verd i A5 té resposta neta → FASE B. Altrament informe i stop."*
  → **Stop.** No s'ha tocat res. FASE B (B1/B2/B3) queda en espera de la decisió d'Agus.

---

## A1 — Catàleg vigent (coincideix amb CATALEG_PECES_TENANT.md)

| mètrica | valor |
|---|---|
| GarmentGroup | 11 |
| GarmentType | 19 (17 actius · 2 inactius) |
| GarmentTypeItem | 57 |

**Types fantasma (sense items):**

| id | codi | nom | grup | actiu |
|---|---|---|---|---|
| 42 | DRESS | Dress | DRESSES | **False (ja desactivat)** |
| 24 | T_SHIRT | T-shirt | TOPS | **False (ja desactivat)** |

> Nota per a B1.7: DRESS i T_SHIRT **ja estan `actiu=False`**. El pas de desactivar-los
> ja està fet; només quedarien BABY_SEPARATES i BABY_ONEPIECES un cop buidats pel move.

## A2 — Models penjats

- Els **8 items `baby_*`**: **0 models** cadascun. El move de B1.3 és segur (no arrossega models).
- Types fantasma **DRESS** i **T_SHIRT**: **0 items** (per tant 0 models). Segurs.
- (FK real trobat: `Model.garment_type_item`.)

## A3 — TaskTimeEstimate per a un item NOU

**Auto-create sota demanda (lazy `get_or_create`).** No hi ha signal ni seed:

- `fhort/tasks/signals.py` — buit de receivers (retirats a Sprint 0); no crea cel·les.
- Les cel·les neixen a `views_b.py:1070` i `services_i.py:31` amb
  `TaskTimeEstimate.objects.get_or_create(garment_type_item, task_type)` al **primer ús**,
  amb `estimated_minutes = NULL`.

→ **Els 5 items nous (booties, bag, hat_cap, scarf, socks) no necessiten cap sembra de temps.**
Les cel·les apareixeran soles quan s'usin. Cap camp nou, cap migració.

## A4 — SizeSystem / SizeDefinition

**Estructura `SizeSystem`:** `codi` (unique), `nom`, `descripcio`, `actiu`, `targets` (M2M),
`base_unit` (ALPHA/NUMERIC_EU/NUMERIC_US/CM_HEIGHT/MONTHS/AGE_YEARS), `norma_ref`,
`parent` (self-FK), `customer_codi` (3 chars).
**Estructura `SizeDefinition`:** `size_system` (FK), `etiqueta`, `ordre`, `valor_numeric`,
+ camps cos ISO (body_*), age_months_*. Unique `(size_system, etiqueta)`; ordering per `ordre`.

> **No existeix cap camp de "talla base/sample"** ni a SizeSystem ni a SizeDefinition.
> La nota del brief ("deixa-la sense marcar si el model ho permet") es compleix per absència:
> no hi ha res a marcar. La talla base viu, si de cas, a `GarmentTypeItem.base_size_definition`
> (capa item), no a la size library.

**Contingut literal actual dels dos que B2 vol RECTIFICAR — ja són correctes:**

`GIRL_LOS_01` ('LOS Grading Kid Girl 2Y - 12Y', AGE_YEARS, cust=LOS, target GIRL):
`2 · 3 · 4 · 5 · 6 · 7 · 8 · 9/10 · 11/12` (9) → **coincideix exactament amb B2. Cap canvi.**

`MAN_LOS_01` ('Home ALPHA — LOSAN IBERIA SA Run 01', ALPHA, cust=LOS, target MAN):
`S · M · L · XL · 2XL · 3XL · 4XL · 5XL · 6XL` (9, 2XL canònic) → **coincideix exactament amb B2. Cap canvi.**

> ⚠️ **Troballa fora d'abast (LOS size systems extra):** hi ha **3** systems `GIRL_LOS_*`,
> no un: `GIRL_LOS_01` (Girl 2-12), `GIRL_LOS_02` ('LOS Kids 01 … Knit Regular'),
> `GIRL_LOS_03` ('Nena AGE_YEARS … Run 03'), tots AGE_YEARS/cust=LOS/9 talles. La proposta
> de rename `GIRL_LOS_01 → KIDS_LOS_01` s'ha de decidir tenint present que hi ha germans
> `_02`/`_03` (evitar col·lisió de nomenclatura). Es deixa intacte.

## A5 — Identitat del contenidor de grading · **QÜESTIÓ CLAU** ⛔

**Estructura.** `GradingRuleSet` té: `nom`, `size_system`, `garment_group`, `garment_type_item`,
`fit_type`, `customer`, `origen` (CANONICAL/CLIENT_RUN/IMPORT/NULL), `target` (FK legacy),
`targets` (M2M), `construction`, `parent_version`, `version_number`, `codi_sistema`.
`GradingRule`: `rule_set`, `pom`, `talla_base`, `logica`, `increment`, `increment_base/break`,
`talla_break_label/pos`, `actiu`.

**La constraint d'identitat** (`pom/models.py:614`, migració 0039):
```
UniqueConstraint(fields=['customer','size_system','garment_type_item','fit_type'],
                 condition=Q(origen='CLIENT_RUN'), name='uniq_client_container_identity')
```

**Per què bloqueja.** Els dos contenidors en conflicte del BLOC B3 comparteixen els TRES
primers eixos i només poden divergir pel quart:

| # | size_system | item | gènere | forma | customer |
|---|---|---|---|---|---|
| a | YOUTH_LOS_01 | t_shirt | **noi** | LINEAR pur | LOS |
| b | YOUTH_LOS_01 | t_shirt | **noia** | LINEAR break 14 | LOS |
| c | YOUTH_LOS_01 | trousers | **noia** | LINEAR break 14 | LOS |
| d | YOUTH_LOS_01 | trousers | **noi** | LINEAR pur | LOS |

(a)/(b) i (c)/(d) tenen idèntics `(customer, size_system, garment_type_item)`. La forma
(linear vs break-14) és una propietat de les **regles per-POM**, NO de la identitat del
contenidor. L'únic eix d'identitat que queda lliure és **`fit_type`**.

**Vies avaluades:**

| via | a l'identitat? | veredicte |
|---|---|---|
| `target` / `targets` (M2M) | **NO** | No separa: dos CLIENT_RUN amb mateix (cust,system,item,fit) col·lidirien. **Inviable.** |
| `fit_type` | **SÍ** | Semànticament és el *fit* (Slim/Regular/Oversized…), **no** el gènere. Els dos youth són tots dos regular-jersey: no difereixen de fit. Codificar-hi el gènere = abús semàntic + contamina el picker de fit. **No neta.** |
| `size_system` per gènere | (sí, però) | El brief imposa **mateix run** YOUTH_LOS_01 per als dos. Contradiu el brief. **Inviable.** |
| `RuleSetScopeNode` | — | És *disponibilitat* per al matching, **no** identitat. No separa dos contenidors. |

**Conclusió A5: NO existeix cap via neta.** El model d'identitat del contenidor es va
dissenyar deliberadament **gènere-agnòstic** (`customer + size_system + item + fit`). Afegir
el gènere a la identitat és una decisió d'arquitectura → **d'Agus**.

**Opcions per a Agus (cap executada):**
1. **Afegir el gènere a la identitat** (camp `target`/gènere a la constraint). Requereix
   **migració d'esquema** (canviar `uniq_client_container_identity`) → FORA de Fase 1
   ("cap migració"). Decisió estructural.
2. **Usar `fit_type` com a portador del gènere** (p.ex. inventar valors o reutilitzar
   CUSTOM). Sense migració, però **abús semàntic** del fit; embruta pickers i matching.
3. **Un run/size_system per gènere** a youth (YOUTH_LOS_G / YOUTH_LOS_B). Contradiu la
   premissa "mateix run" del brief; caldria confirmar-ho amb Montse.
4. **Deixar els 2 parells de youth per a més endavant** i fer B3 només per als 13 contenidors
   sense col·lisió de gènere (tots els altres items apareixen una sola vegada per system).

## A6 — Rulesets LOS existents (ids 104 i 111) — REVISAR, no duplicar

| id | nom | size_system | item | fit | origen | target | customer | grup | n_regles |
|---|---|---|---|---|---|---|---|---|---|
| 104 | LOS Kids Knit Regular 2Y - 12Y | **GIRL_LOS_03** | None | None | **None** | GIRL | LOS | — | 19 |
| 111 | EU ALPHA LOS TOP KNIT REGULAR V01 | **MAN_LOS_01** | None | None | **None** | MAN | LOS | — | 16 |

**Observacions (no tocades):**
- Tots dos tenen **`origen=None`** (no `CLIENT_RUN`) i **`garment_type_item=None`** → NO són
  encara contenidors sota la llei d'identitat nova; la constraint parcial no els cobreix.
- **104** penja de `GIRL_LOS_03`, **no** de `GIRL_LOS_01`; item buit. Per encaixar-lo amb una
  fila de B3 (kids) caldria assignar-li item + fit + `origen=CLIENT_RUN` + potser canviar de
  size_system. No encaixa net amb cap fila tal com està → **es deixa intacte, s'informa**.
- **111** penja de `MAN_LOS_01`; item buit, target MAN. La fila B3 més propera (`MAN_LOS_01 ·
  polo · home`) requeriria assignar item=polo + fit + origen. Tampoc encaixa net → **intacte**.

**Altres CLIENT_RUN reals a BD (context):** id=115 (BRW·blouse·ALPHA_EU_W, item=blouse,
fit=REGULAR) i id=124 (BRW, item=None). Cap precedent de dos contenidors mateix-item
gènere-diferent → confirma que el cas youth és nou i sense patró previ.

---

## Cens de suport (per a la futura FASE B)

- **Customers:** `BRW` (Brownie), `FTT` (self), **`LOS` (LOSAN IBERIA SA)** ✓ existeix.
- **FitType a BD:** REGULAR, SLIM, RELAXED, OVERSIZED, FLARED, TAPERED, STRAIGHT, BODYCON,
  ATHLETIC, CUSTOM. (Cap valor de gènere — confirma A5.)
- **Target a BD:** WOMAN, MAN, UNISEX_ADULT, BABY_GIRL, BABY_BOY, BABY_UNISEX, TODDLER_GIRL,
  TODDLER_BOY, GIRL, BOY, TEEN_GIRL, TEEN_BOY, MATERNITY.
- **GarmentGroup ACCESSORIES** existeix (per a B1.5). **NEWBORN no existeix** (B1.1 el crearà).

## Propostes pendents d'OK d'Agus
1. **[BLOCADOR] Resposta A5** (opcions 1–4 de dalt) abans de tocar B3.
2. **Rename `GIRL_LOS_01 → KIDS_LOS_01`**: viable però hi ha `GIRL_LOS_02`/`_03` germans;
   decidir si es renomenen tots o es consolida. No executat.
3. **Sort dels rulesets 104/111**: no encaixen net amb cap fila B3; confirmar destí.
