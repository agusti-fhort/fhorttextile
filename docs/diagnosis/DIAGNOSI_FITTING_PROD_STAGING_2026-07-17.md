# DIAGNOSI — Desajust staging ↔ PROD al fitting (400 de create-piece + crash .map() de la sessió 95)

Data: **2026-07-17** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
Refs frescos (`git fetch`, només refs remots: cap canvi de codi, BD ni entorn). PROD interrogat pel
**dump diari** (`/srv/fhort-prod-backups/incoming/fhort_textile_20260717_023001.dump`, 02:30 d'avui),
que és l'oracle read-only documentat a [[ftt-prod-estat-via-dump]] — **no hi ha SSH a PROD**.

> `fitxer:línia` = fet verificat · `NO EXISTEIX` = confirmat absent · `PENDENT DE VERIFICAR` = no
> demostrable amb les fonts disponibles.

---

## Veredicte primer

**PROD NO està en estat incoherent. La hipòtesi no es sosté.** El fitting de `main` i el de `dev` és
**byte-idèntic**: no hi ha cap "adapter nou sobre backend vell".

> **La disjuntiva «completar deploy vs revertir» és FALSA**: cap de les dues toca el fitting, perquè
> no hi ha res desajustat. Ni desplegar `dev` canviaria un sol fitxer de fitting, ni revertir els
> "fitxers avançats" revertiria res (ja són els mateixos des del 2026-07-10).

**La causa real és de DADES, i el codi ja la diu**: el model de la sessió no té **cap GradingVersion
activa** → `create_piece_fitting` llança `ValueError` → **400 «Cal generar les talles primer»**. El
**crash `.map()` és una CONSEQÜÈNCIA** del 400 (l'única cosa que sí que és un bug de codi: la UI no
tolera el 400 i peta en comptes de mostrar el missatge). I és **reproduïble a staging**, perquè el codi
hi és idèntic.

---

## BLOC 1 — main vs dev: el fitting és IDÈNTIC (Q1)

| Ref | Hash | Data |
|---|---|---|
| `origin/main` | `7d8dc3a` | **2026-07-16 10:51** — "deploy: paquet Taller (naturals+A2+…)" |
| `origin/dev` | `43c87df` | 2026-07-17 08:10 |
| merge-base | `92f6d90` | 2026-07-16 10:16 |

- `origin/main..origin/dev` = **42 commits**; `origin/dev..origin/main` = 29 (l'espinada de merges/deploys).
- **Commits de FITTING a `dev` que no són a `main`: CAP.**
  `git log origin/main..origin/dev -- '*fitting*' '*Fitting*' '*fittingGrid*' backend/fhort/fitting/` → **buit**.
- **Diff de tot el radi de fitting entre `main` i `dev`: BUIT.**
  `git diff origin/main origin/dev -- backend/fhort/fitting/ frontend/src/components/model/fittingGridAdapter.jsx frontend/src/pages/FittingDetail.jsx frontend/src/pages/FittingSessionList.jsx frontend/src/components/model/measureSources.jsx` → **cap fitxer**.
- `views.py`/`services.py`/`serializers.py` de `fitting`: **idèntics**. `endpoints.js::createPiece`: **idèntic**.

**Veredicte BLOC 1:** no hi ha cap commit ni cap línia de fitting que `dev` tingui i `main` no.

---

## BLOC 2 — `fittingGridAdapter` no es va "avançar" (Q2)

- Existeix a `frontend/src/components/model/fittingGridAdapter.jsx` **a totes dues branques**.
- **Contingut idèntic** (`git diff origin/main origin/dev -- …/fittingGridAdapter.jsx` → buit).
- **L'últim commit que el toca és `77e3c2f` (2026-07-10)** — "fix(fitting): P1b — la graella de fitting
  pinta només la talla base" — i és **ancestre de `main` I de `dev`**. Va entrar a `main` fa una setmana,
  **amb el seu backend**, no avui.
- **El deploy d'avui no existeix a `main`**: l'últim commit de `origin/main` és d'**ahir 10:51**.

**Coherència adapter ↔ backend a `main`:** el `create_piece` de `main` és **el mateix** que el de `dev`
(§BLOC 1) i el mateix des d'abans del 2026-07-10. **Cap dels dos espera l'altre.**

**Veredicte BLOC 2:** cap fitxer compartit del camí fitting/create-piece es va avançar.

---

## BLOC 3 — Què corre PROD de debò (l'oracle del dump)

Migracions **aplicades a PROD** (dump d'avui 02:30, `django_migrations` amb dates):

- `fitting`: **0001…0016**. L'última, `0016_gradingversion_una_sola_activa`, aplicada **2026-07-14 04:58**.
- **El repo (main I dev) també topa a `0016`** → **l'esquema de fitting de PROD està AL DIA amb el codi**.
- Última onada de deploy a PROD: **2026-07-16 10:54** (`tenants` 0004/0005, `backoffice` 0005/0006,
  `patterns` 0008/0009/0010) — que **casa amb `origin/main` `7d8dc3a` (10:51)**. → **PROD == aquell `main`**.
- La `0016` **només AFEGEIX una constraint** (una sola activa per SizeFitting) i es va auditar sense
  duplicats (docstring de la migració): **no pot haver desactivat res** ni causar "zero actives".

**Veredicte BLOC 3:** PROD corre el `main` d'ahir, amb l'esquema de fitting complet. Cap barreja de versions.

---

## BLOC 4 — D'on surt el 400 (Q3): és una PRECONDICIÓ DE DADES, no un contracte canviat

`create_piece` (`backend/fhort/fitting/views.py:199-219`) només retorna **400** en tres casos:
1. `model_id` absent (`:202`);
2. **`ValueError`** de `services.create_piece_fitting` (`:208-210`).

I `create_piece_fitting` (`backend/fhort/fitting/services.py:319-345`) llança `ValueError` quan:
- `_resolve_working_size_fitting(model)` → None → *"El model X no té cap SizeFitting de treball."*
- `_active_grading_version(sf)` → None → ***"El model X no té cap GradingVersion activa. Cal generar les talles primer."***

**Cap camp nou obligatori, cap format nou**: el payload segueix sent `{model_id}` (`endpoints.js:525`),
idèntic a les dues branques. El validador **no ha canviat**.

**Les dades de PROD expliquen el 400** (dump d'avui):

| Taula | Files a PROD |
|---|---|
| `fitting_sizefitting` | **22** |
| `fitting_gradingversion` | **6** |
| `fitting_piecefitting` | 1 |
| `fitting_fittingsession` | **1** (id=**94**, model 178, Tancada) |

De les **6** GradingVersion, només **3 són actives**, i cobreixen **3 SizeFittings**: `sf=68` (model 169),
`sf=69` (model 178), `sf=71` (model 190). **Els altres 19 SizeFittings no tenen cap versió activa** — 15
estan en `estat=Pendent` (models 163-177) **sense cap GradingVersion**.

→ **Qualsevol sessió de fitting sobre un model d'aquests dona 400 «Cal generar les talles primer».**
Això és el codi dient la veritat, no un desajust.

`_resolve_working_size_fitting` (`services.py`) ja **PREFEREIX** el SizeFitting que tingui versió activa
(recorre'ls tots), així que els models amb SF duplicats (169, 190, 163) **no** cauen pel camí dolent.

**Sessió 95: PENDENT DE VERIFICAR.** El dump (02:30) arriba fins a la sessió **94** → la 95 es va crear
**després**, avui. Sense SSH no puc llegir-ne el model exacte; el mecanisme, però, està provat i la
distribució de dades (19/22 sense versió activa) el fa el candidat aclaparador.

**Veredicte BLOC 4:** el 400 és una precondició de dades documentada al propi missatge, idèntica a staging.

---

## BLOC 5 — El crash `.map()` és una CONSEQÜÈNCIA (i l'únic bug de codi real)

Cadena verificada:
1. `resolvePieceFitting` (`frontend/src/components/model/measureSources.jsx:37-56`) només tracta el
   **409** (`piece_exists`); qualsevol altre error —**inclòs el 400**— fa **`throw e`** (`:55`).
2. En petar la càrrega, el grid es pinta igualment amb dades no resoltes:
   `buildFittingGroups(raw.baseLabel, raw.versionNumbers, ctx.t)` (`measureSources.jsx:68`) i
   `buildFittingRows(raw.pomRows, …)` (`:72`).
3. L'adapter és defensiu a mitges: protegeix `(line?.evolucio || [])` (`fittingGridAdapter.jsx:37`) i
   `(rows || [])` (`:121`), però **NO** `versionNumbers.map` (`:23`), `pomRows.map` (`:33`) ni
   `sizeLabels.map` (`:109`) → **TypeError `.map()` de undefined**.

És un **buit de robustesa REAL**, però **no un artefacte de deploy**: el codi és idèntic a staging →
**reproduïble allà**. La pantalla blanca amaga el missatge que el backend ja dona.

**Veredicte BLOC 5:** el crash no diagnostica un desajust; amaga un 400 llegible.

---

## Q4 — Dimensionament de les dues sortides proposades (totes dues NO resolen res)

| Opció | Què faria de debò | Resol el 400/crash? | Risc |
|---|---|---|---|
| **Completar el deploy** (merge `dev`→`main`) | Portaria els **42 commits** dels sprints WIZARD/ÀMBIT + migracions (0040, …). **Zero fitxers de fitting** (§BLOC 1). | **NO** | El propi d'un deploy gran, i **sense relació amb el fitting**. Té el seu runbook als RESULTATs. |
| **Revertir els "fitxers avançats"** | **NO-OP**: `fittingGridAdapter` i tot el fitting són iguals a `main` i `dev` des del **2026-07-10** (`77e3c2f`). Revertir-los seria revertir-los a ells mateixos. | **NO** | Regressió gratuïta si es revertís al pre-`77e3c2f` (es perdria el fix P1b). |

**Cap de les dues.** El desajust que es vol arreglar **no existeix**.

## 💡 PROPOSTA (a validar) — el que sí que tancaria el cas

1. **Operatiu (el 400)**: **generar les talles** del model de la sessió 95 — és literalment el que
   demana el missatge. Afecta 19 dels 22 SizeFittings de PROD, així que reapareixerà a cada sessió
   sobre un model sense versió activa. *Decisió d'Agus: és un buit de dades o de procés (les sessions
   es convoquen abans de generar talles)?*
2. **Codi (el crash)** — peça petita i acotada, **desplegable per separat**: que `resolvePieceFitting`
   tracti el **400** com tracta el 409 (propagar el missatge del backend a la UI) i/o blindar els tres
   `.map()` de `fittingGridAdapter` (`:23`, `:33`, `:109`). Resultat: en comptes de pantalla blanca,
   *"Cal generar les talles primer"*. **Reproduïble i verificable a staging** (mateix codi).

---

## TAULA FINAL

| Afirmació del brief | Realitat verificada |
|---|---|
| "El deploy d'avui va portar fitxers compartits nous" | **FALS** — `origin/main` no s'ha mogut des d'**ahir 10:51**; l'adapter no es toca des del **2026-07-10** |
| "`fittingGridAdapter` nou + backend fitting vell" | **FALS** — tot el fitting és **byte-idèntic** entre `main` i `dev` |
| "El sprint de fitting nou mai es va desplegar a main" | **FALS** — **cap** commit de fitting a `main..dev` |
| "El 400 ve d'un contracte canviat" | **FALS** — payload `{model_id}` idèntic; el 400 és `ValueError` de precondició de dades |
| "PROD està a mig camí (barreja de versions)" | **FALS** — migracions de fitting al dia (**0016**); PROD == `main` d'ahir |
| El crash `.map()` | **CERT però CONSEQÜÈNCIA** del 400 (`measureSources.jsx:55` re-llança; adapter `:23/:33/:109` sense guarda) |
| Motor / `generate_graded_specs` | **INTOCAT** |
