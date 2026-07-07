> ⚠️ SUPERADA 2026-07-07 — implementada (claus òrfenes kanban.*/estat esborrades, 56f53cc). Consulta només com a històric.

# DIAGNOSI G8-3 — i18n òrfenes + auditoria namespace `kanban.*`

**Protocol:** FASE B · READ-ONLY ABSOLUT · 0 codi · 0 push · branca `dev` (`/var/www/ftt-staging`).
**Data:** 2026-06-26.
**Locales:** `frontend/src/i18n/{ca,en,es}.json` (els 3 línia-idèntics a les zones afectades).
**Mètode:** director + 2 investigadors (Explore) + verificació directa de l'autor (estructura JSON via
Python, grep exhaustiu de tots els `t(\`…${…}\`)`). Els números de línia dels agents eren col·lapsats;
**els d'aquest doc estan verificats contra els JSON reals**.
**Llegenda:** `FET (fitxer:línia)` · 💡PROPOSTA (a validar) · OBERT (no determinable read-only).

> **Criteri d'èxit cobert:** una peça B pot esborrar les claus marcades MORTES SEGURES sense risc de
> trencar text dinàmic — la TRAMPA de claus dinàmiques (§A2) s'ha auditat exhaustivament.

---

## RESUM EXECUTIU

- **Namespace `kanban.*`:** 66 fulles, **paritat perfecta** ca/en/es. Només **8 fulles VIVES**
  (`kanban.temporades.*` + `kanban.estats.*`, totes per accés dinàmic); les **58 restants són MORTES**
  (residu del Kanban global jubilat, `KanbanTasks.jsx` esborrat al commit `fc98cab`). Zero ús literal de
  cap clau `kanban.*` a tot `frontend/src`.
- **2 candidates del brief:** `model.fields.estat` → **MORTA**; `kanban.filter_estat` → **MORTA** (ja dins
  el bloc mort de `kanban`).
- **Cap trampa dinàmica:** no existeix cap `t(\`model.fields.${…}\`)` ni cap `t(\`kanban.${…}\`)` genèric;
  els únics dinàmics que toquen `kanban.` són `kanban.temporades.${x}` i `kanban.estats.${…}` (les 8 vives).

---

## A1 — Candidates concretes

### `model.fields.estat` → **MORTA SEGURA**
- **FET** existeix als 3 locales, línia **1135**: `ca="Estat"` · `en="Status"` · `es="Estado"`.
- **FET** ús literal: **0** a `frontend/src` (`grep "model\.fields\.estat"` → cap; la fila que la
  consumia es va treure de `ModelSheet.jsx`, ara fa "superficiar fase en lloc d'estat").
- **FET** abast dinàmic: **0** — no existeix cap `t(\`model.fields.${…}\`)` a tot el codi (les altres
  `model.fields.*` s'usen literals una a una, p.ex. `model.fields.fit_type` a `ModelSheet.jsx:880`).
- ⚠️ **No confondre** amb el `"estat"` de línia **1209** = `fitting.session.estat` (VIU, namespace
  diferent). El candidat és NOMÉS el de línia 1135 (dins `model.fields`, que obre a 1127).

### `kanban.filter_estat` → **MORTA SEGURA** (subsumida pel bloc mort de `kanban`)
- **FET** existeix als 3 locales, línia **1108**: `ca="Estat"` · `en="Status"` · `es="Estado"`.
- **FET** ús literal: **0** (`KanbanTasks.jsx`, que la feia servir, esborrat al commit `fc98cab`).
- **FET** abast dinàmic: **0** — no hi ha `t(\`kanban.filter_${…}\`)` ni cap `t(\`kanban.${…}\`)` genèric.
- És dins el rang mort 1061-1112 (§A3), per tant l'escombra de `kanban.*` ja la cobreix.

---

## A2 — TRAMPA de claus dinàmiques (auditoria completa)

**FET — TOTS els `t(\`…${…}\`)` que toquen els prefixos rellevants** (grep exhaustiu de `frontend/src`):

| Template literal | Fitxer:línia | Namespace tocat | Abasta cap candidata? |
|---|---|---|---|
| `t(\`kanban.temporades.${x}\`)` | `pages/Dashboard.jsx:245` | `kanban.temporades.*` | NO (és VIVA, no candidata) |
| `t(\`kanban.estats.${onSoc.estat}\`)` | `components/model/DashboardTab.jsx:116` | `kanban.estats.*` | NO (és VIVA, no candidata) |
| `t(\`model_sheet.dashboard.phase.${…}\`)`, `model_wizard.*`, `planning.*`, `usersRoles.*`, etc. | (molts) | altres namespaces | NO |

- **FET** **no existeix cap** `t(\`model.fields.${…}\`)`, ni `t(\`model.${…}\`)` genèric, ni
  `t(\`kanban.filter_${…}\`)`, ni `t(\`kanban.${…}\`)` que no sigui `.temporades`/`.estats`.
- **FET — patró de referència (VIU, fora d'scope):** `model.estats.*` s'usa via `components/EstatBadge.jsx:32-38`
  (mapa de claus `'model.estats.Nou'`…`'model.estats.Tancat'`). És el namespace **`model`** (línia 1156),
  **NO** `kanban.estats` (línia 1114) → són dos blocs diferents; tots dos vius però per camins diferents.

**Conclusió A2:** cap de les dues candidates pot ser abastada dinàmicament → cap BANDERA per trampa dinàmica.

---

## A3 — Auditoria del namespace `kanban.*`

**FET — estructura real** (objecte `kanban` obre a línia **1060** als 3 locales; 66 fulles; paritat
ca==en==es **perfecta**, mateixes claus i mateixes línies).

**FET — les ÚNIQUES vives** (accés dinàmic, §A2), són les **2 últimes claus** del bloc:
| Subtree VIU | Línia (ca/en/es) | Fulles | Consumidor |
|---|---|---|---|
| `kanban.temporades.*` (SS/FW/CO/SP) | **1113** | 4 | `Dashboard.jsx:245` (filtre de temporada del board per-model) |
| `kanban.estats.*` (Nou/EnCurs/EnRevisio/Tancat) | **1114** | 4 | `DashboardTab.jsx:116` (etiqueta d'estat del Dashboard del model) |

**FET — les MORTES:** totes les altres **58 fulles** del namespace, que ocupen les línies **1061-1112**
(contigües, abans de temporades/estats). Inclou les claus de capçalera/columnes/accions/ordenació/filtres
del Kanban global jubilat. Cap té ús literal ni dinàmic. Top-level morts (amb els objectes niats):

`title, subtitle, loading, empty_col, status{·6}, action{·…}, toast_paused, not_allowed, transition_error,
rect, search_ph, col_models, my_models, priority_a, select_model, load_more, no_models, phase, tasks_n,
gate_validate, gate_confirm, gate_done, gate_error, confirm, cancel, sort_by, sort_default, sort_asc,
sort_desc, sort{·…}, filter_temporada, filter_estat, filter_responsable, resp_me, resp_all, resp_hint,
resp_tech_placeholder, more_filters, clear_filters, filter_garment_type, filter_any, filter_prioritat,
results_n` → **0 consumidors vius** (residu de `KanbanTasks.jsx`, esborrat al commit `fc98cab`
"Jubilar la pàgina Kanban global"; el namespace `kanban.*` no es va netejar llavors).

### Cas `kanban.tasks_n` vs `dashboard.board.tasks_n`
- **FET** `kanban.tasks_n` (línia **1093**, dins el bloc mort) — **0 usos** → **MORTA**.
- **FET** `dashboard.board.tasks_n` (línia **1805**) — **VIVA**: `Dashboard.jsx:92`
  (`t('dashboard.board.tasks_n', { n: total })`, KPI "Tauler de models").
- Mateix valor (`"{{n}} tasques/tasks/tareas"`) → la **viva és la del board** (`dashboard.board.tasks_n`);
  la de `kanban` és duplicat mort (ja cobert per l'escombra 1061-1112). `dashboard.board.tasks_n` **NO es toca**.

---

## A4 — Veredicte (FET) + abast d'escombra

### MORTES SEGURES (0 literal + 0 dinàmic) — esborrar ×3 locales
| Què | Línies (idèntiques ca/en/es) | Fulles |
|---|---|---|
| Bloc mort de `kanban.*` (tot menys temporades/estats) | **1061-1112** | 58 |
| `model.fields.estat` | **1135** (línia individual) | 1 |

### VIVES a preservar (NO tocar)
| Clau | Línia | Consumidor |
|---|---|---|
| `kanban.temporades.*` | 1113 | `Dashboard.jsx:245` |
| `kanban.estats.*` | 1114 | `DashboardTab.jsx:116` |
| `model.estats.*` | 1156 | `EstatBadge.jsx:32-38` (namespace `model`, no kanban) |
| `dashboard.board.tasks_n` | 1805 | `Dashboard.jsx:92` |
| `fitting.session.estat` | 1209 | (no és model.fields.estat — namespace `fitting`) |

### Paritat
- **FET** totes les claus afectades tenen **paritat perfecta** als 3 locales i a les **mateixes línies**
  → l'escombra és simètrica (les mateixes línies a `ca.json`, `en.json`, `es.json`).

### 💡 PROPOSTA — abast exacte per a la peça B (esborrat)
1. A cada `{ca,en,es}.json`: eliminar **línies 1061-1112** (queda `"kanban": {` a 1060 seguit directament
   de `temporades` 1113 i `estats` 1114 → JSON vàlid; `results_n` a 1112 era l'últim mort amb coma).
2. A cada `{ca,en,es}.json`: eliminar la **línia 1135** (`"estat"` dins `model.fields`) — **NO** la 1209.
3. ⚠️ **Ordre / mètode:** `model.fields.estat` (1135) és DESPRÉS del bloc kanban (1061-1112); si s'esborra
   kanban primer, la 1135 es desplaça ~52 línies amunt. Recomanat: esborrar **per coincidència de
   cadena única** (Edit), o bé esborrar la 1135 **abans** del bloc kanban, o re-greppar després de cada
   edició. Verd: `npm run build` net + `python -m json.tool` vàlid als 3 locales.
4. Total a eliminar: **59 fulles × 3 locales** (58 kanban + 1 model.fields.estat).

### OBERT / fora-d'scope (anotar, no tocar en aquesta peça)
- **`model.estats` (1156) i `model.temporades` (1168):** `model.estats.*` és VIU (EstatBadge). `model.temporades.*`
  no ha aparegut en cap grep d'aquesta auditoria — **possible duplicat mort** de `kanban.temporades`, però
  queda **FORA de l'scope** d'aquest G8-3 (auditoria limitada a `kanban.*` + les 2 candidates). Marcat com a
  deute a verificar en una auditoria pròpia de `model.*`, no esborrar aquí. **OBERT.**
