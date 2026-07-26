# DIAGNOSI — Bifurcació `dev` ↔ `main` (2026-07-14)

> Patró A · read-only · cap merge, cap push, cap canvi als dos entorns.
> Refs frescos (`git fetch`) el 2026-07-14. Àncores: hashos verificables amb `git show`.

## Veredicte primer

**No hi ha bifurcació.** La premissa del brief —"dues evolucions paral·leles divergents"—
**no es sosté contra els refs**. La relació real és la més simple de totes:

> `dev` conté **el 100% del codi de `main`**, més 110 commits.
> `main` té **un (1) fitxer** que `dev` no té: `docs/deploy.md` (+27 línies, documentació).
> **Cap fitxer de codi ha estat tocat per totes dues bandes. La superfície de conflicte és zero.**

Això ho diu una sola ordre:

```
$ git diff --stat b93db34..origin/main      # tot el que main ha guanyat des de l'avantpassat comú
 docs/deploy.md | 28 +++++++++++++++++++++++++++-
 1 file changed, 27 insertions(+), 1 deletion(-)
```

## 1 · Topologia

| | Ref | Hash | Data | Commits des de l'avantpassat |
|---|---|---|---|---|
| Avantpassat comú | `merge-base` | `b93db34` | **2026-07-12 08:03** | — |
| PROD | `origin/main` | `4a82f5f` | 2026-07-12 08:33 | **26** |
| Staging | `origin/dev` | `d2394e0` | 2026-07-14 06:47 | **110** |
| Staging local | `dev` | `9620990` | 2026-07-14 10:20 | 110 + 4 (sprint IMPORT, sense push) |

Les branques **no es van separar fa mesos: es van separar fa dos dies**, i per 30 minuts.
El 2026-07-12 a les 08:03, `main` va absorbir `dev` sencer (merge `4ec04cf`, sprints X+Y). A
les 08:33 va rebre un commit d'ops (`4a82f5f`, la segona porta `app.fhorttextile.tech`) que
**només toca `docs/deploy.md`**. Des d'aleshores `dev` ha corregut 110 commits i `main` no s'ha
mogut.

Els 26 commits de `main` porten dates d'autor de juny (`2026-06-12`…) i fan pensar en una
història paral·lela antiga. No ho és: són **l'espinada històrica de `main`** (merges i deploys
successius de `dev`). El seu **efecte net de contingut** sobre l'avantpassat comú és,
literalment, el fitxer de documentació de dalt.

## 2 · Mapa de fitxers

| Classe | Fitxers | Conflicte? |
|---|---|---|
| (a) **Només `main`** | `docs/deploy.md` | — |
| (b) **Només `dev`** | 138 fitxers (l'app `patterns` sencera, Taller, G6, QA-S8, biblioteca, i18n…) | — |
| (c) **Tocats per les DUES** | **cap** | **cap** |

Simulació de merge (`git merge-tree`, read-only): **net, zero conflictes**. `dev` no ha tocat
mai `docs/deploy.md` des de l'avantpassat comú.

## 3 · Les divergències que el brief donava per fetes — no existeixen

Cada afirmació del brief, contrastada amb els refs:

| Afirmació | Realitat verificada |
|---|---|
| `bulk_import_service.py` 642 vs 646 línies | **579 línies a `origin/main`, `origin/dev` i l'avantpassat comú.** Idèntic als tres. (590 al meu `dev` local: les +11 del sprint IMPORT/T3.) |
| `services.py` només a dev | **És a totes dues.** |
| `bulk_import_views.py` només a main | **És a totes dues.** |
| `main` porta el refactor gran `6f6181b` | **`6f6181b` no existeix.** Ni a `ftt-staging`, ni a cap dels altres 7 clons/worktrees del servidor. És un hash fantasma. |

D'on surten els números del brief, no ho puc reconstruir des de git. La sospita raonable és una
comparació contra **l'arbre de treball** (que té feina no commitada de sessions concurrents) o
contra **el codi realment desplegat a PROD**, que —com diu la memòria del projecte— **no és
`origin/main`**: PROD no té SSH i el seu estat real es llegeix del backup diari. Aquesta
diagnosi respon la pregunta de **git**; **no certifica què corre de debò a la màquina de PROD**.
Si el dubte és aquest, és una altra diagnosi i necessita el dump.

## 4 · El refactor: no hi ha cap base pre-refactor

La pregunta clau del brief era: *si `dev` no té el refactor de `main`, tot el treball s'ha de
re-basar abans d'anar a PROD.* La resposta és **no cal**: `main` **no té ni una línia de codi**
que `dev` no tingui. `dev` no està construït sobre cap base antiga; està construït **sobre
`main`**.

**Què es va desplegar de debò el 07-12** (merge `4ec04cf`): sprints X+Y — fitting dissolt en
tasques, tasca unificada Mesurar prenda, fulla de convocatòria, assets C4-C5, bootstrap tenant.
**Res més.**

**Què NO ha arribat mai a PROD** (viu només a `dev`):

- **Motor de patrons** — l'app `backend/fhort/patterns/` **sencera** (18 fitxers + 7 migracions). No existeix a `main`.
- **Taller de patró** (W2–W4b) — `frontend/src/pages/TallerPatro.jsx`, `PatternViewer.jsx`.
- **G6** (segell del grading) — inclosa `fitting/migrations/0016_gradingversion_una_sola_activa`.
- **QA-S8** (parser determinista d'import), biblioteca de client, i el sprint IMPORT d'avui.

## 5 · Opcions de reconciliació (dimensionades; no decideixo)

El problema **no és git**. Git és trivial aquí. El problema és **la mida del payload de deploy**.

| Opció | Què és | Cost | Risc |
|---|---|---|---|
| **A · Deploy normal (el de sempre)** | Merge `dev` → `main` com els 4 deploys anteriors. `docs/deploy.md` es fusiona sol (ningú l'ha tocat a dev). | Minuts | **Git: nul.** El risc és el payload, no la branca. |
| **B · Back-merge primer** | `main` → `dev` (porta `deploy.md`), després `dev` → `main`. Deixa les branques idèntiques abans de tocar PROD. | Minuts | Nul. Higiene, no necessitat. |
| **C · Re-basar / re-crear `dev`** | El que el brief temia caldre. | Dies | **Alt i injustificat.** Reescriuria 110 commits per resoldre un problema que no existeix. **Descartable.** |

**Recomanació de dimensió (no de decisió):** A o B són equivalents en risc de git. El que
mereix un sprint propi de debò és **el deploy en si**, i el seu risc no és la topologia:

- **11 migracions** noves, 7 de les quals creen una app sencera (`patterns`) → `migrate_schemas`
  sobre tots els tenants de PROD.
- **+96k línies** de diff, però atenció a la lectura: **69k són dos fixtures DXF de test**
  (`TATE_prova.dxf` 62.772 línies). El codi de producte real és molt més petit del que el número
  suggereix.
- Dependències noves del motor de patrons → `requirements.lock` a PROD.
- Permisos de `media/` per als uploads de DXF (trampa coneguda: gunicorn corre com `www-data`).

**Un sol deploy de 110 commits que estrena una app Django sencera a PROD és la decisió que
val la pena pensar** — no si les branques han divergit, perquè no ho han fet.

---
*Read-only. Cap escriptura als entorns, cap merge, cap push. Aquest document no s'ha commitat:
queda a l'arbre de treball perquè l'Agus decideixi si entra a git.*
