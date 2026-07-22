# DIAGNOSI — Refer el wizard «Nou run de client»: eliminar la poda de talles i validar contra el run del DOCUMENT

> Patró A (read-only) · 2026-07-22 · staging `/var/www/ftt-staging`, branca `dev`, commit `fa252d0`.
> Decisió de disseny JA PRESA (Patró C, Agus, 2026-07-22): aquí només se'n dimensiona l'abast tècnic.
> **Cap escriptura de codi, cap commit, cap migració.**

---

## 0. Sincronia vault ↔ servidor

| Fet | Estat al `DECISIONS.md` del servidor (mtime 2026-07-22 06:32) |
|---|---|
| §INTEGRITAT DE GRADUACIÓ (2026-07-08) | ✅ PRESENT — `DECISIONS.md:1041-1046` |
| §RUN-CLIENT (2026-07-08) | ✅ PRESENT — `DECISIONS.md:1002-1020` |
| Decisió d'avui (eliminar la graella / referent = run del document) | ❌ **ABSENT** |
| Cas Meredith / BRW XXS-L | ❌ **ABSENT** (hi ha BRW a `DECISIONS.md:36,791-800`, però d'un altre cas) |

**🚩 DESINCRONIA VAULT↔SERVIDOR.** La decisió del Patró C de 2026-07-22 sobre la graella i el canvi de
referent del guard **no és al `DECISIONS.md` del servidor**. Cal abocar-la abans que un Patró B hi
construeixi a sobre (és el mateix incident de circuit ja anotat a `DECISIONS.md:181`).

Text literal de la llei vigent que aquesta diagnosi modifica (`DECISIONS.md:1041-1043`):

> **[INTEGRITAT DE GRADUACIÓ] Cap regla es deriva d'una taula incompleta.** Talla del run sense
> valor = fila incompleta = **BLOQUEIG de creació (400)** […] Normalització d'etiquetes: **pont únic
> `canonical_size_label`**.

La decisió d'avui **no la deroga**: en canvia el *referent* («el run») de *run del SizeSystem* a
*run del DOCUMENT*, i en conserva la protecció (coherència interna, break no ambigu, STEP explícit).

---

## 1. Mapa del wizard «Nou run de client»

### 1.1 Muntatge i portes d'entrada

| Peça | Fitxer:línia |
|---|---|
| Modal contenidor (títol «Nou run de client») | [SizeAuthoringDrawer.jsx:8-62](frontend/src/components/SizeAuthoringDrawer.jsx#L8-L62) |
| Component real del wizard | [SizeMapSetup.jsx:191-913](frontend/src/pages/SizeMapSetup.jsx#L191-L913) (`export function Wizard`) |
| Muntatge des de la pàgina de jocs de regles | [GradingRuleSets.jsx:208](frontend/src/pages/GradingRuleSets.jsx#L208) |
| Muntatge des de Size Library | `frontend/src/pages/SizeLibrary.jsx` (mateix drawer) |
| Pàgina standalone + `?prefill=` (des del W1) | [SizeMapSetup.jsx:59-160](frontend/src/pages/SizeMapSetup.jsx#L59-L160), `readPrefill()` a `:50` |
| Backend (tot el flux, gated `CONFIGURE`) | [backend/fhort/pom/size_map_views.py](backend/fhort/pom/size_map_views.py) (1005 línies) |

### 1.2 Els 5 `step` interns → 2 pantalles visibles

El `Stepper` col·lapsa els 5 estats interns en **2 pantalles**: `screen = step <= 3 ? 1 : 2`
([SizeMapSetup.jsx:479](frontend/src/pages/SizeMapSetup.jsx#L479)). Per això l'usuari veu
«Configuració → Importació i confirmació» però el codi navega amb `setStep(1..5)`.

| step | Pantalla | Contingut | Fitxer:línia | Endpoint que el tanca |
|---|---|---|---|---|
| 1 | Configuració | target · unitat · client · **tria de SizeSystem (run)** · talla base · construcció · fit · àmbit | `:483-555` | `POST size-map/match/` (`goMatch`, `:262-276`) |
| 2 | Configuració | REUTILITZAR / CLONAR / **CREAR sistema nou** (radios de candidats + score) | `:558-595` | `POST size-map/preview/` (`goPreview`, `:279-294`) |
| 3 | Configuració | **GRAELLA DE TALLES EDITABLE** (etiqueta/ordre/numèric/mesos/alçada + 🗑 esborrar fila + ➕ afegir) | `:598-647` | cap (només `setStep(4)`) |
| 4 | Importació | upload Excel/PDF/imatge + taula de POMs derivats + **avisos d'integritat** | `:650-813` | `POST size-map/grading-preview-file/` (`calcGradingFromFile`, `:309-321`) |
| 5 (`step>=4`) | Confirmació | destí · targets de perfil · nom/variant · resum · panell 409 · **Crear** | `:816-910` | `POST size-map/create/` (`submitCreate`, `:394-426`) |

> Nota: els blocs 4 i 5 es rendereixen tots dos amb `step >= 4`; no hi ha un `step 5` real. El «Back»
> del bloc de confirmació torna a `setStep(3)` — és a dir, **a la graella** (`:904`).

### 1.3 Sub-passos del pas 1, un a un

| Sub-pas | Component | Fitxer:línia |
|---|---|---|
| Target | `<select>` de `lookups.targets` | `:485-490` |
| Unitat base (ALPHA/EU/…) | `<select>` | `:491-496` |
| Codi de client | `CustomerSelector` (id → es resol `customer_codi`) | `:499-505` |
| **Tria d'etiqueta de run** | `SizeSystemSelector` — el run **es TRIA, no es tecleja** | `:508-516` + [SizeSystemSelector.jsx:13-60](frontend/src/components/SizeSystem/SizeSystemSelector.jsx#L13-L60) |
| Talla base (ETIQUETA) | `Pill` sobre `labels()` | `:517-525` |
| Construcció / Fit | `Pill` sobre `lookups.constructions` / `fit_types` | `:527-546` |
| Àmbit d'aplicabilitat | `CascadeSelector mode="multi"` | `:549` |

Gate del botó «Següent»: `!target_codi || labels().length===0 || !base_size || applies_to.length===0`
(`:552`).

**Efecte lateral rellevant de `SizeSystemSelector`** (`:510-515`): en triar un sistema, sembra
`labelsText` amb **totes** les etiquetes del sistema i posa `base_size` a la **talla del mig**
(`labs[Math.floor(labs.length/2)]`). Aquest `labelsText` és el que després viatja a `match` i
`preview`, i és l'origen del `run` de 8 talles del cas Meredith.

---

## 2. Veredicte sobre la graella de talles (tasca A2)

### 2.1 Què escriu EXACTAMENT a cada camí

L'estat de la graella és `wiz.talles` (`SizeMapSetup.jsx:206`), poblat per `goPreview` des de
`size_map_preview_view` (`:284-289`), editable a `:616` i **podable** a `:629-630`
(`talles.filter((_,j) => j !== i)`).

Al `create`, `talles` es persisteix **només** dins d'aquest guard:

```python
# backend/fhort/pom/size_map_views.py:780-794
if accio in ('CLONAR', 'CREAR'):
    for idx, t in enumerate(talles):
        SizeDefinition.objects.update_or_create(size_system=ss, etiqueta=et, defaults={...})
```

| Camí | Què fa la poda | Veredicte |
|---|---|---|
| **REUTILITZAR** | `accio == 'REUTILITZAR'` → `ss = SizeSystem.objects.get(pk=src_ssid)` (`:745-746`) i el bloc `:780` **no s'executa** | ✅ **NO modifica el canònic. NO crea sistema derivat. És estat local que es DESCARTA.** |
| **CLONAR** | Copia les talles del pare (`:761-766`) i després fa merge amb `talles` (`:780-794`) | Legítim (defineix el run del sistema derivat) |
| **CREAR sistema nou** | `talles` és **l'única font** de `SizeDefinition` del sistema nou (`:767-794`) | ✅ **Legítim i imprescindible: únic lloc on cal conservar la graella.** |

### 2.2 La troballa forta: al camí REUTILITZAR la graella **tampoc valida res**

`calcGradingFromFile` (`SizeMapSetup.jsx:309-321`) envia al backend **només** `file`,
`size_system_id`, `base_size` i `customer_codi`. **`wiz.talles` no viatja mai al preview.**

I al backend, el referent del guard és el run **del SizeSystem sencer**, llegit de la BD:

```python
# size_map_views.py:437-440
tenant_run = []
if ssid:
    tenant_run = list(SizeDefinition.objects.filter(size_system_id=ssid)
                      .order_by('ordre').values_list('etiqueta', flat=True))
# size_map_views.py:505
run = list(tenant_run)
# size_map_views.py:538  ← EL GUARD
missing = [s for s in run if values.get(s) is None] if run else []
```

**Conseqüència:** al camí REUTILITZAR, esborrar files de la graella **no desbloqueja res** — el
bloqueig es recalcula sempre contra les 8 talles d'`ALPHA_EU_W` a la BD. La graella hi és, convida a
podar, la poda no serveix de res i es llença. És simultàniament **inútil i enganyosa**. Això
reforça la decisió: al camí REUTILITZAR **s'elimina sencera**, sense cap pèrdua funcional.

Residus a netejar si s'elimina: el gate `disabled={wiz.talles.length === 0}` (`:644`), el «Back» de
confirmació que apunta a `setStep(3)` (`:904`), i el comptador del resum `size_map_sum_talles`
(`:861`).

### 2.3 Talla base (tasca A3)

- **Es demana al pas 1 com a ETIQUETA pura**, per botons `Pill` (`SizeMapSetup.jsx:517-525`) →
  `wiz.base_size` és un `string`. Viatja al payload com `base_size` (`:364`).
- **Es persisteix a `GradingRule.talla_base`** (FK a `SizeDefinition`, NOT NULL), resolta al backend:
  ```python
  # size_map_views.py:796-802
  base_def = SizeDefinition.objects.filter(size_system=ss, etiqueta__iexact=base_size).first()
  if base_def is None:
      base_def = SizeDefinition.objects.filter(size_system=ss).order_by('ordre').first()
  ```
  i escrita a `:898` (`'talla_base': base_def`).
- ✅ **Compatible amb la decisió**: el backend ja espera **només l'etiqueta**. Cap valor base viatja
  (coherent amb `DECISIONS.md:1013-1015`, «Valor base NO viu al run»).
- 🚩 **Bandera menor (fora d'abast, s'anota):** el fallback de `:801-802` agafa **la primera talla del
  sistema** si l'etiqueta no resol. És una fabricació silenciosa de talla base. Candidata a 400 explícit.

---

## 3. El guard d'integritat i el seu referent (tasques B1-B3)

### 3.1 On viu, avui

| Capa | Fitxer:línia | Què fa |
|---|---|---|
| Backend · preview per **fitxer** (camí real) | `size_map_views.py:535-554` | marca `incompleta: True` + `missing_sizes` |
| Backend · preview per **paste** | `size_map_views.py:309-325` | ídem |
| Backend · **create** (bloqueig 400) | `size_map_views.py:637-650` | 400 `'Hi ha files amb talles absents (taula incompleta)…'` |
| Frontend · missatge vermell | `SizeMapSetup.jsx:681-687` (`size_map_incompleta_warn`) + badge per fila `:797-802` | |
| Frontend · pre-guard abans d'enviar | `SizeMapSetup.jsx:334` (`incompletes`) i `:396-400` | torna a `setStep(3)` |

### 3.2 Flux de dades del referent (B2)

```
SizeSystemSelector (tria de sistema)      → wiz.src_system_id / labelsText
        ↓ (només l'id viatja)
calcGradingFromFile  ──FormData{file, size_system_id, base_size, customer_codi}──►
        ↓
size_map_grading_preview_file_view
        ├─ tenant_run = SizeDefinition(size_system=ssid).order_by('ordre')   ← :437-440
        ├─ wiz_ctx['size_run'] = tenant_run  → passat a la IA com a AJUDA    ← :446-451
        ├─ canon_to_tenant = {canonical_size_label(e): e for e in tenant_run} ← :516
        ├─ values re-clavats a etiquetes del tenant                           ← :526
        ├─ run = list(tenant_run)                                             ← :505
        └─ missing = [s for s in run if values.get(s) is None]  ★ EL GUARD    ← :538
```

**Resposta a B2: es compara contra el run del SIZESYSTEM SENCER llegit de la BD.** Ni contra el run
podat de la graella (que no viatja), ni contra el document.

**Cas Meredith reproduït en fred:** sistema `ALPHA_EU_W` = 8 talles; document BRW = XXS-L (5).
`missing = [XL, XXL, 3XL]` per a **cadascuna** de les 26 files → 26 files vermelles i `create`
bloquejat amb 400. El document és perfectament coherent; el que és incorrecte és el **referent**.

### 3.3 Segon efecte, més greu que el bloqueig: el motor de detecció també usa el run equivocat

`detect_grading` rep el **mateix** `run` (`size_map_views.py:557`), i calcula els deltes entre
**veïns de la llista que rep** ([grading_utils.py:172-188](backend/fhort/pom/grading_utils.py#L172-L188)).
Amb un run més ample que el document, els forats generen `warning` i el delta se **salta**
(`:183-186`) — la degradació silenciosa que la llei del 2026-07-08 volia matar. Amb un run **més
estret** que el document, els deltes es **col·lapsen** (veure §6, bug 166).

👉 **El canvi de referent no és només al guard: `run` és el mateix objecte que alimenta
`detect_grading` i `derive_break_fields`.** Canviar-lo als tres llocs alhora és el nucli de la peça.

### 3.4 Disseny del guard nou (referent = run del document)

**Construcció del referent** (substitueix `size_map_views.py:504-510`):

```
doc_labels  = unió de claus de values de totes les files, re-clavades amb canonical_size_label
doc_run     = doc_labels ordenades per SizeDefinition.ordre del sistema triat
```

L'ordenació pel `ordre` del sistema fa doble feina: dona l'ordre (que el document no garanteix) **i**
és el mecanisme del check (d).

| Check | Regla | Implementació proposada | Estat avui |
|---|---|---|---|
| **(a) Cap forat intern** | Totes les talles de `doc_run` tenen valor a **cada** fila | `missing = [s for s in doc_run if values.get(s) is None]` — **mateixa línia `:538`, un sol nom canviat** | Existeix, mal referenciat |
| **(b) Break derivable sense ambigüitat** | LINEAR-amb-break = exactament **1** transició de delta; ≥2 → STEP | **Ja el garanteix** `detect_grading` (`grading_utils.py:195-211`: `nb==0` LINEAR, `nb==1` LINEAR+break, `nb>=2` STEP) i `derive_break_fields` (`:237-243`) agafa la **primera** transició. Amb (a) satisfet no hi ha ambigüitat possible | ✅ ja cobert, **només si (a) és sobre el mateix run que la detecció** |
| **(c) STEP: valor explícit per CADA talla del document** | Idem (a) — per STEP, (a) ja és la condició | Cobert per (a). **La segona meitat** (el run del model no pot excedir les talles amb valor) **NO viu al wizard**: viu al motor, `pom/services.py:857-872` | ⚠️ parcial — veure §5 C2 |
| **(d) Sanity: talles del document ⊆ run del sistema** | Una etiqueta del document que el sistema no coneix = **error real (400)** | **NOU.** Avui `canon_to_tenant.get(canonical_size_label(k), k)` (`:526`) deixa passar la clau sense mapar i després `run` simplement no la conté → **s'ignora en silenci** | ❌ **no existeix** |

**Què es CONSERVA del 2026-07-08:** el bloqueig 400 abans d'escriure res (`:645-650`), la llista de
files afectades al payload d'error, el pont únic `canonical_size_label` (`:422,516,526`), i el
principi que el `size_run` del prompt de la IA és **ajuda, mai garantia** (`:446-451`).

**Què es PERD i cal decidir-ho conscientment:** avui, un document que porta menys talles que el
sistema es bloqueja; demà passa i genera una regla que el motor **extrapolarà** a les talles no
documentades (§5, cas C1b). Això és **comportament esperat per decisió**, però hauria de deixar
traça: veure bandera 🚩-2 a §8.

---

## 4. Cens de superfícies (tasca B4)

`grep -rn "incompleta\|missing_sizes"` sobre `backend/fhort` + `frontend/src`: **els únics encerts de
grading són `size_map_views.py` i `SizeMapSetup.jsx`.** No hi ha còpies literals del check.

| # | Superfície | Fitxer:línia | Deriva regles d'una taula? | L'afecta el canvi? | Té el seu propi check? |
|---|---|---|---|---|---|
| 1 | **Wizard run-client · preview per fitxer** | `size_map_views.py:437-440,505,538` | Sí | ✅ **SÍ — nucli de la peça** | Sí (l'original) |
| 2 | **Wizard run-client · preview per paste** | `size_map_views.py:281-295,310` | Sí | ✅ **SÍ — mateixa cirurgia** (aquí el `run` ja és la unió de claus del paste + ordre del sistema: **ja és gairebé el disseny nou**) | Sí (bessó de #1) |
| 3 | **Wizard run-client · create** | `size_map_views.py:637-650` i `run_ordenat` a `:883-885` | Sí | ✅ **SÍ** — `run_ordenat` per a `derive_break_fields` es llegeix del **SizeSystem sencer**; ha de passar a ser el run del document | Sí (bloqueig 400) |
| 4 | **ImportWizard · fitxa de model** | `extraction_views.py:1971-1974` → `derive_rules_from_fitxa` a [grading_utils.py:275-315](backend/fhort/pom/grading_utils.py#L275-L315) | Sí | ⚠️ **SÍ, i és el forat** — referent = `model.size_run_model` (`:285-286`) | ❌ **CAP guard d'integritat.** Només avisos (`:307-311`) i el guard de talla base C1c (`extraction_views.py:1857-1872`) |
| 5 | Wizard run-client · frontend | `SizeMapSetup.jsx:334,396-400,681-687,797-802` | — | ✅ SÍ (mirall de #1) | Mirall, no còpia |
| 6 | Size-map · `preview`/`match` | `size_map_views.py:157-260` | No (només etiquetes) | ❌ No | — |
| 7 | Motor | `pom/services.py:104,262,785` | No (aplica, no deriva) | ❌ No (verificat, §5) | Sí, propi (STEP) |
| 8 | Seeds LOSAN, `backfill_grading_break`, `load_losan_package` | veure §6 | Sí, però des de JSON curat | ❌ No | — |

### Veredicte helper únic

**Sí, cal.** No perquè hi hagi còpies del check (no n'hi ha), sinó perquè hi ha **dues definicions
divergents del referent** (#1/#3 = run del SizeSystem · #4 = run del model) i **cap** és el run del
document. Proposta: un únic helper pur a `pom/grading_utils.py`, al costat de `detect_grading`:

```python
def run_del_document(values_per_fila, size_system, *, canonical=True) -> tuple[list[str], list[str]]:
    """Retorna (doc_run ordenat pel SizeSystem, etiquetes_desconegudes).
    doc_run alimenta ALHORA el guard (a), detect_grading i derive_break_fields.
    etiquetes_desconegudes != [] → check (d) → 400."""
```

Amb ell, #1, #2, #3 i #4 comparteixen **una sola** noció de referent i el bug 166 mor amb el mateix bisturí.

---

## 5. Verificació del motor (tasques C1/C2) — cap canvi necessari

Motor: [backend/fhort/pom/services.py](backend/fhort/pom/services.py). `generate_graded_specs` `:104`,
`preview_graded_specs` `:262`, `_apply_rule` `:785`, `_norm_label` `:770`.

### C1 — Quin run llegeix el motor

**El run del MODEL**, no el del ruleset. Confirmat i declarat al propi codi:

- `services.py:147` — `size_run = [...] model.size_run_model.replace(';','·').split('·') [...]`
- `services.py:148,155` — base = `model.base_size_label`, `base_idx = size_run.index(base_size)`
- `services.py:199-202` / `:299-302` — `size_run=size_run` a `_apply_rule`
- `services.py:806-809` (comentari literal): *«El llindar es resol per ETIQUETA contra el RUN DE
  GRADUACIÓ (size_run del model), no contra el run del ruleset […] Label absent al run → cap break»*

Aplicació del break: `services.py:812-829`. `break_idx` només es fixa si `talla_break_label ∈ run`
(`:818-823`); acumulació aresta a aresta amb `brk` si `j >= break_idx`, si no `ib` (`:824-829`).
`talla_break_pos` **el motor no el llegeix mai** (només `talla_break_label`).

Regla LINEAR-amb-break derivada d'un document XXS-L (break a L, `ib=+2`, `ibrk=+3`, base M):

| Cas | Resultat | Justificació |
|---|---|---|
| **(a) model run XXS-L (idèntic)** | ✅ Propaga correctament. L = base+3 | `break_idx=4` (`:822`); `path=[4]`, `4>=4` → `brk` (`:828`) |
| **(b) model run XXS-3XL (extrapolació amunt)** | ✅ No peta. XL=+6, XXL=+9, 3XL=+12 | `:824-829`. La regla és **fórmula viva**: extrapola el break indefinidament sense evidència documental. És el comportament esperat per la decisió, però **sense cap avís ni marca de cel·la extrapolada** |
| **(c) model run XS-M (subconjunt)** | ⚠️ No peta; **degrada en silenci** | `'L' ∉ run` → `break_idx=None` (`:818`, sense `else`) → tot amb `ib`. Aquí el número final és correcte (cap talla arriba a L), però **el camí és el mateix** que falla quan el label no casa per forma (`XXL` vs `2XL`: `_norm_label` a `:770-772` només fa strip+upper, **no** canonicalitza) → propagació plana amb 200 OK |

**Veredicte C1: cap dels tres casos peta ni cal tocar el motor.** El risc (c) és preexistent i queda
**anotat**, no tocat (zona intocable, `CLAUDE.md §Zones intocables`).

### C2 — STEP amb talles sense valor

Branca STEP: `services.py:837-874`. Per cada aresta busca `deltas.get(_norm_label(size_run[j]))`; si
en falta una → `_add_warning("falta delta per a la talla X")` i **`return None, 'STEP'`**
(`:868-872`). El cridador fa `if graded_val is None: continue` (`services.py:203-206`, comentari
*«leave it uncomputed»*; preview a `:307-309`).

✅ **Compleix la llei «regla sense base = cel·la absent»: cel·la ABSENT, ni zero ni excepció.**

Dos matisos anotats:
- El `return` és dins del bucle del camí (`:868-872`) → es perd la talla del forat **i totes les de
  més enllà** en aquella direcció.
- Si cap cel·la no es genera per a cap POM → `ValueError` (`services.py:224-235`), no un 200 buit. Bé.

**On viu la segona comprovació de B3(c)** («el run del model no pot excedir les talles amb valor»):
**al motor, `services.py:857-872`** — i ja hi és, en forma de cel·la absent + warning agregat
(`:246-251`). **No cal replicar-la al wizard.**

---

## 6. Vincle amb el bug del model 166 (tasca D1) — mecanisme identificat

### 6.1 Estat real a la BD (staging, schema `fhort`, consulta read-only)

```
Model 166 = BRW-FW26-0004 · Blusa MEREDITH
  size_run_model = 'XS·S·L'      (3 talles!)
  base_size_label = 'S'
  size_system = ALPHA_EU_W
  grading_rule_set = None
  ModelGradingRule.objects.filter(model=166).count() == 0
  BaseMeasurement: 37 files
```

**Cap regla persistida.** Els valors «Delta break = 2×Delta · Talla break = L» que es van veure són
d'una superfície de **derivació/preview**, no de la BD.

### 6.2 El mecanisme, exacte

`derive_rules_from_fitxa` (`grading_utils.py:275-315`) deriva amb
`run_ordenat = model.size_run_model` = **`[XS, S, L]`** (`:285-286`), mentre el document Meredith
porta el run dens **XXS, XS, S, M, L**.

`detect_grading` calcula el delta de cada talla **contra el seu veí dins la llista rebuda**
(`grading_utils.py:172-188`). Amb base `S`:

| Talla | Veí segons `run_ordenat=[XS,S,L]` | Delta calculat | Delta real del document |
|---|---|---|---|
| XS | S | `v_S − v_XS` = **d** | d (XS i S són veïns de veritat) |
| L | S | `v_L − v_S` = **2d** (salta M!) | d |

→ `vals = [d, 2d]` → `nb == 1` → **`logica='LINEAR'`, `valors_step={XS:d, L:2d}`**
(`grading_utils.py:206-209`) → `derive_break_fields` (`:237-243`) pren `ib = d` (primer) i la primera
transició com a break → **`talla_break_label='L'`, `increment_break = 2d = 2×ib`**.

**«Delta break = 2×Delta, Talla break = L» reproduït exactament.** No és una fabricació arbitrària:
és el **col·lapse de dos salts en un** quan el run de referència és més **estret** que el del
document — la imatge especular del bloqueig del wizard, on el run és més **ample**.

### 6.3 Resposta a D1

- **Via:** l'**import de fitxa de model** (`extraction_views.py:1971-1974` → `derive_rules_from_fitxa`),
  **no** aquest wizard ni entrada manual.
- **Per què esquiva el bloqueig:** aquest camí **no té guard d'integritat** (§4, fila 4). Només
  avisa (`grading_utils.py:307-311`) i persisteix igualment via
  `materialize_model_grading_rules_from_specs` (`models_app/services.py:198-221`) i
  `afegeix_regles_al_contenidor` (`:224-241`).
- **És la mateixa cirurgia:** ✅ **SÍ.** Els dos bugs són el mateix defecte —
  *el referent de derivació no és el run del document*— amb el signe canviat. L'helper únic de §4
  els tanca tots dos.

### 6.4 Altres escriptors de break (context, no abast)

Camins que poden materialitzar un break **sense evidència documental** (anotats, no tocats):

| Camí | Fitxer:línia | Risc |
|---|---|---|
| Edició manual `gravar_pom` | `models_app/views.py:1433-1438` (`_break_pos` a `:1333-1337`) | Accepta qualsevol numèric i qualsevol etiqueta; `talla_break_pos=None` si no és al run, **però desa el label igual**. Únic guard: `es_linear_degenerada` (`:1441-1445`) |
| `set_pom_regim_view` | `models_app/views.py:3111-3125` | Idem |
| `backfill_grading_break`, branca `above_xl` | `pom/management/commands/backfill_grading_break.py:73-85` | **Inventa** el label: talla següent a `XL` al run del ruleset; si no n'hi ha, **hardcodeja `'XXL'`** |
| Seeds LOSAN | `seed_losan_grading_v3.py:186-195` (+ `seed_losan_rules{,_v2}.py`) | `talla_break_label` **constant per cel·la** del JSON, no derivat per regla |
| Materialització / clon QA | `models_app/services.py:168-195`; `clone_model_for_qa.py:100-103` | No fabriquen; **propaguen** un break ja fabricat |

Cap camí automàtic calcula `2×increment_base` explícitament — **el 2× del 166 és emergent**, tal com
descriu §6.2.

---

## 7. Nota sobre D2 (wizard GTI «Grup de peça només Bottoms»)

**Sí, comparteixen component.** `CascadeSelector` és el mateix a:

- `SizeMapSetup.jsx:8,549` — aquest wizard (`mode="multi"`, àmbit d'aplicabilitat)
- `ModelWizard.jsx:5,539` — wizard GTI (`mode="single"`, picker de peça)
- `GradingRuleSets.jsx:4,231,897` — cascada de filtres + àmbit
- `ItemAuthoring.jsx:7,256` — (`maxLevel="group"`)

**No comparteixen el catàleg d'entrada ni la lògica de guard.** Es registra el solapament perquè un
canvi al `CascadeSelector` tocaria les quatre superfícies; **els abasts no es barregen** en aquesta peça.

---

## 8. Banderes per al CTO

1. 🚩 **Desincronia vault↔servidor** (§0): la decisió d'avui no és al `DECISIONS.md` del servidor.
2. 🚩 **Extrapolació silenciosa** (§5, cas C1b): amb el referent nou, una regla derivada de XXS-L
   s'aplicarà a XL/XXL/3XL sense cap marca. **Decisió necessària:** ho deixem mut, ho anotem al
   `warnings` del create, o ho marquem a la cel·la de `GradedSpec`? (La llei de PROVINENÇA,
   `DECISIONS.md:1047-1050`, empeny cap a deixar-ne traça.)
3. 🚩 **Fallback silenciós de talla base** (§2.3): `size_map_views.py:801-802` agafa la primera talla
   del sistema si l'etiqueta no resol. Candidat a 400 explícit — fora d'abast, s'anota.
4. 🚩 **`_norm_label` del motor no canonicalitza `XXL`↔`2XL`** (`services.py:770-772`): break perdut
   en silenci amb 200 OK (§5, cas C1c). Zona intocable — **anotat, no tocat**.
5. 🚩 **`derive_rules_from_fitxa` sense cap guard d'integritat** (§4 fila 4): el forat que va produir
   el bug 166. La peça 4 de §9 el tanca; si es decideix ajornar-la, el bug 166 **torna**.

---

## 9. Proposta de talls d'implementació (Patró B) — un focus per commit

> **No implementat.** Ordre pensat perquè cada commit sigui verd i verificable tot sol.

| # | Focus | Fitxers | Verificació |
|---|---|---|---|
| **1** | **Helper únic `run_del_document(values, size_system)`** — pur, retorna `(doc_run ordenat, etiquetes_desconegudes)`. Cap cridador encara. | `backend/fhort/pom/grading_utils.py` (nou, al costat de `detect_grading`) | `manage.py check` + test unitari nou del helper |
| **2** | **Referent del preview = run del document** — els dos previews passen a `doc_run` per al guard **i** per a `detect_grading`/`derive_break_fields`; check (d) → 400 amb `etiquetes_desconegudes` | `size_map_views.py:281-295,310` (paste) i `:504-510,538,557,563` (fitxer) | Excel Meredith XXS-L sobre `ALPHA_EU_W`: 0 files incompletes, 26 regles derivades |
| **3** | **Referent del create = run del document** — `run_ordenat` de `:883-885` deixa de ser el SizeSystem sencer; el guard `:637-650` es manté (ara sobre el referent correcte) | `size_map_views.py:637-650,876-908` | `create` del cas Meredith persisteix 26 `GradingRule` amb break coherent |
| **4** | **Tancar el forat de l'import de fitxa (bug 166)** — `derive_rules_from_fitxa` passa a derivar contra el run del **document** via el helper, i el forat intern passa d'avís a **bloqueig** | `pom/grading_utils.py:275-315`; `models_app/extraction_views.py:1971-1974` | Re-import de la fitxa Meredith al model 166: `increment_break` deixa de ser `2×ib`; `talla_break_label` desapareix (LINEAR pur) |
| **5** | **Eliminar la graella al camí REUTILITZAR** — pas 3 només es renderitza si `decision ∈ {CREAR, CLONAR}`; `goPreview` no demana `size_definitions` a REUTILITZAR; netejar `disabled={talles.length===0}` (`:644`), el «Back» de `:904` i el comptador de `:861`. Backend: `talles` ja s'ignora a REUTILITZAR (`:780`) — **no cal tocar-lo** | `SizeMapSetup.jsx:598-647,644,861,904` | `npm run build` net + e2e: REUTILITZAR passa de pas 2 a pantalla d'importació; CREAR conserva la graella intacta |
| **6** | **i18n-gate + missatges nous** — clau nova per al check (d) (`size_map_unknown_sizes`), retirada de `size_map_sum_talles` al camí REUTILITZAR, paritat `ca/en/es` | `frontend/src/i18n/{ca,en,es}.json` | `npm run build` + inspecció de les 3 claus |
| **7** *(opcional, segons bandera 🚩-2)* | **Traça de l'extrapolació** — el create afegeix un `warning` quan `doc_run ⊊ run del sistema` | `size_map_views.py:950-961` | Resposta del create porta el warning al cas Meredith |

**Dependències:** 1 → 2 → 3; 4 depèn de 1 (independent de 2/3, es pot paral·lelitzar); 5 i 6
depenen de 2 (per no deixar el pas 3 orfe abans que el guard funcioni); 7 depèn de 3.

**Mínim viable per desbloquejar el cas Meredith:** commits **1 + 2 + 3**.
**Mínim per tancar també el bug 166:** afegir **4**.

---

*Diagnosi Patró A. Cap fitxer de codi modificat. El brief de Patró B es farà sobre aquest document.*
