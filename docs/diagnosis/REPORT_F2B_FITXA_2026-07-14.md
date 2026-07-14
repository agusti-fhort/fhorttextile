# REPORT · F2-B P-FITXA — Alta mínima comercial + fitxa amb relacions vives

> Data: 2026-07-14 · Patró B · staging `dev` · **sense push** (el fa l'Agus).
> Base: `DIAGNOSI_F2_FITXA.md` + D1–D6 segellades (`17fcc68`). Scope tancat, no ampliat.

## Commits (6)
| # | Commit | Concern |
|---|---|---|
| P1a | `0965ab6` | backend — `pais`+`email_facturacio` obligatoris a l'alta (ClientCreateSerializer) |
| Troballa 2 | `6c33a73` | SPA — mocks NOMÉS en dev; a staging/PROD, error real (no dades inventades) |
| P1b | `1513106` | SPA — marcar els 5 obligatoris al formulari d'alta (D1) |
| P1c | `1915b7c` | SPA — obligatoris només al create + avís de sembra Free sota el selector |
| P2 | `90f5c43` | backend — connector pricing↔`Client.pais` (deute F1/D2) |
| P3 | `2666cc5` | SPA — Condicions amb contracte vigent + tab Legal (D6) |

## P0 — Troballes de les captures (Agus)
- **Troballa 1** (cap botó d'alta): el botó "Nou tenant" **ja existia** a `TenantsPage.jsx:101`
  (sessió concurrent) → res a fer.
- **Troballa 2** (`/tenants/nou` → detall amb mock "Stripe Configurat" fals): **RESOLT**. La ruta
  `/tenants/new` ja era correcta (abans de `:codi`); el problema era el **fallback mock viu**.
  Ara els fallbacks es gaten amb `import.meta.env.DEV` DIRECTAMENT → al build de staging/PROD el
  branch del mock i les seves dades s'**eliminen per dead-code** (verificat: "Atelier Nord" absent
  del bundle). Un error d'API mostra un **error real**, mai dades inventades. També gated el mateix
  `MOCK_TENANTS` a `ContractFormPage` (mateixa classe de bug).

## P1 — Alta mínima comercial (D1)
- Backend `ClientCreateSerializer`: `pais` i `email_facturacio` → `required` + `allow_blank=False`,
  missatges clars. `plan` segueix `required` **SENSE default Free** (tria explícita de l'operador).
- SPA `TenantFormPage`: els 5 obligatoris (`codi_tenant, nom, plan, pais, email_facturacio`) marcats
  amb asterisc i validats. **Matís validat**: la validació d'obligatoris comercials corre **només al
  create** (`!isEdit`); l'edició de SYS/FTT (plan=None, email buit) **no es bloqueja**. Selector de
  plans des de l'**API real** (Free + els que hi hagi). Avís sota el selector quan es tria Free:
  «En crear-se, aquest tenant es provisionarà automàticament amb el perfil de sembra Free».

## P2 — Connector pricing↔país (D2, deute F1)
- Nou mòdul `views_pricing_client.py` (**NO toca cap fitxer de F1**): reutilitza `resolve_pricing`
  i l'alimenta amb `Client.pais`. `resolve_pricing_for_client(client)` = servei intern per a
  simulacions/pantalles futures; `GET /api/backoffice/v1/pricing/for-client/<codi_tenant>/` l'exposa.
  Fallback EUR intacte (viu dins `resolve_pricing`).

## P3 — Fitxa amb relacions vives (D6)
- **Condicions Comercials**: bloc **CONTRACTE VIGENT** entre "Pla i condicions" i el placeholder
  d'historial (que es queda tal qual). Read-only: llegeix el `TenantContract` actiu
  (`GET /contractes/?client=<codi>&actiu=true` → detail amb línies) i mostra vigència + tarifa
  negociada per línia (servei·preu/moneda·inclosos), amb enllaç a l'editor `/contractes/:id` (**no
  el duplica**). Sense contracte → «Cap contracte vigent» (no error).
- **Tab Legal** nova entre "Mètode de Pagament" i "Activitat" (no toca els placeholders F6/F7):
  placeholder estructurat «Historial d'acceptacions» + estat buit, a punt per a **F4-bis** (1 commit
  de la sessió F4 quan cablegi `GET legal/acceptances/` sota la mateixa capçalera).

## Verificació
| # | Prova | Resultat |
|---|---|---|
| 1 | Alta sense `pais`/`email` → 400 clar (API + SPA) | ✅ 400 amb errors a `pais`+`email_facturacio` (ADMIN, end-to-end); SPA valida client-side |
| 2 | Alta no-Free → 201, onboarding, cap sembra | ✅ 0 logs `client.seed` als tenants existents + guard `if plan.nom==Free` (només Free sembra) |
| 3 | Alta Free → 201 + hook | ⚠️ 201/onboarding/plan=Free ✅ i el hook **es llança** (create crida `_llanca_sembra_free`); **NO s'ha pogut observar la sembra** (veure Watchpoint) |
| 4 | Pricing client `pais=DE` sense Price DE → fallback EUR; `pais=ES` → EUR | ✅ |
| 5 | Fitxa amb contracte → Condicions mostra contracte+tarifa; sense → buit | ✅ FTT (3 línies: 500/8/299 EUR); SYS/TST → «Cap contracte vigent» |
| 6 | `npm run build` + `manage.py check` verds | ✅ |

Neteja E2E: els tenants de prova (QZ1/QZ2) s'han eliminat (Client+Domain+`DROP SCHEMA`+logs).
Tenants reals **FTT i SYS intactes** (TST el va retirar la sessió F3 concurrent, no jo).

## ⚠️ Watchpoint per a Agus / F3 (fora de scope F2-B)
- **No hi ha cap `SeedProfile` a staging (0 files), ni `is_default_free`.** El hook Free de F3 **es
  llança** a l'alta però `provision_free_tenant` no pot sembrar sense el `SeedProfile` per defecte →
  la sembra no s'observa (falla abans de deixar log de `client.seed`). **No és un blocador d'F2-B**
  (l'alta retorna 201, el meu canvi d'email obligatori alimenta el hook correctament); és un **buit
  de dades d'F3**: cal sembrar un `SeedProfile` `is_default_free=True` perquè el tier Free provisioni.

## Deutes anotats (no F2-B)
- **i18n de la fitxa**: tota la fitxa de tenant és literal català (només `login` té `t()` — ja
  detectat a F2-A). Les meves cadenes noves segueixen aquesta convenció del fitxer; el deute real és
  una **passada d'i18n dedicada per a tot el backoffice**, no just el meu delta.
- Regrup fi dels camps opcionals de l'alta (fiscal/adreça): de moment visibles i opcionals; si es vol
  diferir-los a una superfície d'onboarding, cal primer la màquina que tanca `onboarding_complet`
  (avui cap codi l'escriu — deute de F2-A).

## Estat per al vault
- **F2-B tancada a `dev`** (6 commits, sense push). `check` + `build` verds.
- **Alta**: 5 obligatoris comercials (create-only), `plan` sense default Free, email alimenta el hook.
- **Pricing**: ja es pot resoldre per client concret (`pricing/for-client/<codi>`), fallback EUR.
- **Fitxa**: el contracte i la tarifa ja es veuen des de la fitxa (enllacen l'editor Sprint 5); tab
  Legal preparada per a F4-bis.
- **Accions Agus**: (1) push des de SSH; (2) coordinar amb F3 la sembra d'un `SeedProfile`
  `is_default_free` perquè el tier Free provisioni de debò; (3) F4-bis cablejarà la tab Legal.
