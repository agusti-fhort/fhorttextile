# REPORT F3 · P-FREE-SEED — sembra automàtica del Free, seleccionable des del backoffice

**Data:** 2026-07-14 · **Branca:** `dev` (sense push) · **Diagnosi:** `arxiu/DIAGNOSI_F3_FREESEED.md` (segellada)

## Què s'ha construït (6 commits)
| Commit | Peça |
|--------|------|
| `b931d6b` | **B1** SeedProfile (backoffice/public) + migració 0005. `seleccio` guarda BLOCS, no models (frontera SHARED). |
| `b7b048f` | **B2** `bootstrap_tenant --profile <id>`: filtre per blocs + clausura de dependències + gate grading CANONICAL. Mode sense `--profile` intacte. |
| `3a04ce3` | `seed_free_plan`: sembra idempotent de la fila `Plan` Free (preu 0, sense Stripe). No toca `tenants/models.py` (de F1). |
| `3a81321` | **B3** hook a `ClientViewSet.create`: si el pla és Free → subprocés desacoblat `provision_free_tenant` (bootstrap + admin), cada pas al Registre. |
| `80c2fa1` | **B4+B5** pantalla "Perfils de sembra" (SPA) + endpoints DRF (CRUD + `blocs-meta` amb comptadors reals de fhort). |

## Decisions aplicades (del STOP)
- **A2** granularitat = **per blocs** (7: base · size_systems · garments · pom_masters · sizing_profiles · time_seeds · grading). Seleccionar-ne un n'arrossega la clausura.
- **A5** email de l'admin Free = **`Client.email_facturacio`**; si buit → admin DIFERIT i registrat, mai inventat.
- **A4** marcatge Free = **fila `Plan` "Free"** (F1 hi va afegir `NOM_FREE` a NOM_CHOICES / `tenants/0005`; F3 sembra la fila).
- **A3** grading al flux automàtic = **només `CANONICAL`**; NULL/CLIENT_RUN mai viatgen (llei RUN-CLIENT).

## Descobertes durant la implementació
- **Graf de dependències corregit contra el codi real:** `SizingProfile.grading_rule_set` és PROTECT i NO nullable → `sizing_profiles` arrossega `grading` (dependència dura). `GarmentTypeItem.grading_rule_set` i `.base_size_definition` són FK *nullables* → el motor MAP ara les posa NULL en sembra selectiva en lloc de fer skip dur (enllaç opcional no poblat).
- **Coordinació F1 en viu:** F1 va aterrar `NOM_FREE` + `tenants/0004`+`0005` mentre treballava; 0 migracions pendents d'altres apps en aplicar la meva `backoffice/0005`.

## Verificació (staging real, consumida i netejada)
| Cas | Resultat |
|-----|----------|
| 1 · Free sembra sol (perfil estructura) | **PASS** — alta 201 → `actiu`; 57 items, 217 POMMaster, **0 grading, 0 sizing**, 1 admin. Serveix exactament el seleccionat. |
| 2 · Pla Solo NO sembra sol | **PASS** — 201 → queda `onboarding`, schema buit (0 items, 0 users). |
| 3 · Perfil demana grading amb rulesets NULL | **PASS** — error clar (CANONICAL), 0 rulesets, `onboarding`, log `ok=False`. |
| 4 · Re-run bootstrap sobre el mateix tenant | **PASS** — idempotent (0 creats, 0 saltats). |
| 5 · Neteja | **PASS** — DROP SCHEMA + delete Client/Domain (fre/sta/gra/tst); staging torna a `fhort`+`public`. |

Regla del verd: `manage.py check` net · `npm run build` net (frontend-backoffice).

## ⚠️ Accions CTO / desplegament
1. **`migrate_schemas`** (aplica `backoffice/0005_seedprofile` a public). Fet a staging; cal a PROD.
2. **`manage.py seed_free_plan`** (sembra la fila Plan Free). Fet a staging; cal a PROD. **FLAG:** revisar les quotes del Free (max_models=1, usuaris=1, storage=1, ia=0) — sembrades conservadores perquè `REGLES_FREE_TIERS_GMJ_TMA.md §4` no és al repo.
3. **Crear el perfil default-Free real** des de la pantalla nova (decisió de producte: quins blocs). NO se n'ha fabricat cap: el canònic de REGLES §4 depèn del doc absent i del grading, que ara està gated.
4. **Grading al Free:** no se sembra fins que `manage.py set_grading_origen` classifiqui rulesets com a `CANONICAL` (avui 25/25 NULL a fhort). Fins llavors, un perfil Free que demani grading dona error clar (per disseny).

## Estat per al vault
- **F3 P-FREE-SEED COMPLET a `dev`** (6 commits, sense push): B1 SeedProfile · B2 bootstrap `--profile` (blocs + gate CANONICAL) · seed_free_plan · B3 hook d'alta desacoblat · B4+B5 pantalla + endpoints. 5 casos verificats end-to-end a staging i netejats.
- **Territori net:** cap fitxer de F1 tocat (`tenants/models.py`, pricing_*, sync_stripe intactes). F1 va lliurar `NOM_FREE`; F3 sembra la fila Plan Free.
- **Pendent producte (Agus):** crear el perfil default-Free real via pantalla; confirmar quotes del Free; `set_grading_origen` si es vol grading al Free.
- **Deute anotat:** el comptador `p.nulled` de bootstrap ara barreja "FK d'entitat" i "FK nullable a bloc no seleccionat" sota la mateixa etiqueta (cosmètic).
