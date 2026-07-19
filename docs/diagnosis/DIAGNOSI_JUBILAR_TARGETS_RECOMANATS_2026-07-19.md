# DIAGNOSI — Jubilació de `GarmentType.targets_recomanats` + endpoint `garment-types-by-target/`

> Data: 2026-07-19 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging` branca `dev`.
> Abast: confirmar ús-zero del camp M2M `targets_recomanats` i de l'endpoint dedicat, i que la
> taula intermèdia és buida (staging **i** PROD), per decidir-ne la retirada (G5 codi mort).
> Convenció: `fitxer:línia`; **"NO EXISTEIX" = confirmat absent al codi**, no especulat.

## Resum executiu
1. La compatibilitat target↔família viu a **`SizingProfile`** (decisió Agus 19/07); `targets_recomanats`
   és l'M2M abandonat que la diagnosi del wizard ja va marcar buit.
2. **Únic lector de dades** del camp: l'endpoint `garment_types_by_target_view` — que **no el crida ningú**.
3. **Taula intermèdia buida a staging (0) i a PROD (0, dump 2026-07-19)** — cap dada a perdre.
4. Reverse accessor `Target.garment_types` (related_name): **NO EXISTEIX** cap consumidor.
5. Veredicte: **ús zero + taula buida a tots dos entorns → retirada segura** (camp + endpoint).

## BLOC 1 — Aparicions de `targets_recomanats` (tot el codebase)
| # | `fitxer:línia` | Tipus | Acció retirada |
|---|---|---|---|
| 1 | [pom/models.py:413](../../backend/fhort/pom/models.py#L413) | Definició del camp M2M | treure el camp |
| 2 | [pom/migrations/0004_sprint_s1_foundations.py:190](../../backend/fhort/pom/migrations/0004_sprint_s1_foundations.py#L190) | `AddField` original | (històric; la nova migració fa `RemoveField`) |
| 3 | [pom/s2_views.py:390](../../backend/fhort/pom/s2_views.py#L390) | `.filter(targets_recomanats__codi=...)` dins l'endpoint | treure amb l'endpoint |
| 4 | [pom/s2_views.py:382](../../backend/fhort/pom/s2_views.py#L382) | docstring de l'endpoint | treure amb l'endpoint |
| 5 | [tasks/.../bootstrap_tenant.py:150](../../backend/fhort/tasks/management/commands/bootstrap_tenant.py#L150) | config de clonat M2M `('targets_recomanats',)` | `('targets_recomanats',)` → `()` |
| 6 | [tasks/.../bootstrap_tenant.py:32](../../backend/fhort/tasks/management/commands/bootstrap_tenant.py#L32) | docstring (llista d'M2M) | treure la menció |
| 7 | [pom/views.py:120](../../backend/fhort/pom/views.py#L120) | comentari (Onada 1: "és buit i NO és la font") | reescriure sense referenciar el camp |
| 8 | [frontend/.../garmentCatalog.js:11](../../frontend/src/components/grading/garmentCatalog.js#L11) | comentari | reescriure sense referenciar el camp |

**Reverse accessor** `.garment_types` (el `related_name` de l'M2M): `grep -n "\.garment_types\b"` sobre
backend (fora migracions) → **cap resultat**. NO EXISTEIX consumidor del revers.

**Veredicte Bloc 1:** cap consumidor FUNCIONAL de la dada. El bootstrap (#5) només clona l'M2M (buit →
no-op avui) i s'ha d'actualitzar amb la retirada. Els #7/#8 són comentaris propis (Onada 1).

## BLOC 2 — Endpoint `garment-types-by-target/`
- Definició: [pom/s2_views.py:379](../../backend/fhort/pom/s2_views.py#L379) (`garment_types_by_target_view`).
- Registre: [tasks/urls.py:168](../../backend/fhort/tasks/urls.py#L168) + import a [tasks/urls.py:155](../../backend/fhort/tasks/urls.py#L155).
- **Cridadors:** `frontend/src/api/endpoints.js` **NO** en té wrapper; `grep` de `garment-types-by-target`/
  `garment_types_by_target` a frontend + backend → només definició i registre. **NO EXISTEIX cap crida.**
- L'Onada 1 va substituir la seva funció (filtrar famílies per target) per `GarmentTypeViewSet ?target`
  (via SizingProfile) — l'endpoint quedava redundant des d'aleshores.

**Veredicte Bloc 2:** endpoint mort → entra a la jubilació (treure vista + import + ruta).

## BLOC 3 — Estat de la taula intermèdia
- Taula: `pom_garmenttype_targets_recomanats`.
- **Staging** (schema `fhort`, únic tenant): **0 files** (`through.objects.count() == 0`).
- **PROD** (dump `fhort_textile_20260719_023001.dump`, pg_restore v18): la taula existeix als schemas
  `public` i `fhort`; **`TABLE DATA` = 0 files a tots dos** (blocs COPY buits).

**Veredicte Bloc 3:** cap dada a migrar/perdre en cap entorn.

## TAULA FINAL — decisió
| element | estat | acció |
|---|---|---|
| Camp `GarmentType.targets_recomanats` | buit, sense lector funcional | **RemoveField** (migració) |
| Endpoint `garment-types-by-target/` | 0 cridadors | treure vista + import + ruta |
| `bootstrap_tenant` clone config #5/#6 | referència a l'M2M | actualitzar (no clonar el camp) |
| Comentaris #7/#8 | referencien el camp | reescriure |
| Dades staging/PROD | 0/0 | res a migrar |

💡 **PROPOSTA (a validar):** migració `RemoveField` a `pom` + retirada de l'endpoint i del clone.
**Regla del projecte:** el fitxer de migració es mostra abans d'aplicar; l'aplicació és
`migrate_schemas` (mai `--schema`) amb **auditoria de columnes després**. PROD ja confirmat buit al
dump del 19/07 (re-verificar l'absència de la columna post-`migrate_schemas` al deploy).
