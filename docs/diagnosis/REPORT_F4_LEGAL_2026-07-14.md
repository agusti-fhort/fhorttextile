# REPORT F4 · P-LEGAL — documents legals amb hash + acceptacions probatòries

**Data:** 2026-07-14 · **Branca:** `dev` (sense push) · **Sessió paral·lela a F2-B** (territori respectat)

## Què s'ha construït (5 commits)
| Commit | Peça |
|--------|------|
| `bac4af3` | **P1** models (LegalDocument · LegalDocumentVersion · LegalAcceptance) a public; hash sha256 determinista (LF+UTF-8) calculat en publicar; save-guards d'immutabilitat/append-only. Migració 0006. |
| `813c3b9` | **P1b** guard d'esborrat append-only a l'ORM (instància + QuerySet): tanca la via `.delete()` que el save-guard no cobria. |
| `f1d4e7a` | **P2** endpoints `api/backoffice/v1/legal/` (ADMIN): documents/versions DRAFT, publish, pending/accept/acceptances. IP real via X-Forwarded-For. |
| `e4569af` | **P3** gate `legal_pending` al `/me` del tenant + ruta `/api/v1/legal/accept/` per l'admin del tenant (capability MANAGE_USERS). |
| `ea53ed2` | **P4** pantalla "Documents legals" (SPA backoffice). |

## Decisions i models
- **Hash determinista:** `sha256_legal(normalitza_legal(text))` — normalització UTF-8 + LF. Es calcula EN PUBLICAR. Re-publicar el mateix text (fins i tot amb CRLF) en una versió/document nou → **mateix hash** (verificat).
- **Immutabilitat:** `LegalDocumentVersion.save()` rebutja canvis de contingut/hash si la fila a la BD ja és PUBLICADA (llegeix l'estat REAL, no el de la instància). `delete()` d'instància i de QuerySet bloquejats per a PUBLICADES; DRAFT editable/esborrable.
- **Append-only:** `LegalAcceptance` — `save()` rebutja modificar files existents; `delete()` (instància i QuerySet) sempre bloquejat. Idempotència per `UniqueConstraint(client, versio)`.
- **IP real rere proxy:** `client_ip()` llegeix la PRIMERA entrada de `X-Forwarded-For` (nginx `$proxy_add_x_forwarded_for`, confirmat a sites `backoffice` i `ftt-staging`); fallback a `REMOTE_ADDR`. F4 és el primer consumidor que la necessita bé.

## P3 — abast de la incursió al tenant (mínima, sancionada)
- **Un sol punt** a `accounts/me_view`: afegeix `legal_pending` (versions vigents amb `requereix_reacceptacio=True` que el `request.tenant` no ha acceptat). Els models SHARED es llegeixen des del schema del tenant (public al search_path — verificat). NO calen més punts d'inserció al `/me`.
- **Una sola ruta** al tenant: `/api/v1/legal/accept/` → `legal_accept_tenant_view` (viu a backoffice, reusa `record_acceptance`; no duplica la vista). Permís: capability `MANAGE_USERS` (l'admin accepta en nom de l'empresa, B2B).

## Verificació (staging, consumida i netejada)
| Cas | Resultat |
|-----|----------|
| 1 · Publicar → hash estable; re-crear versió idèntica → mateix hash | **PASS** (CRLF→LF determinista) |
| 2 · Editar PUBLICADA per shell → rebutjat pel save-guard | **PASS** |
| 3 · Accept → IP real rere proxy (XFF `203.0.113.9, 10.0.0.1, 127.0.0.1` → `203.0.113.9`) | **PASS** |
| 4 · Re-acceptar mateixa versió → cap duplicat | **PASS** (200, 1 fila) |
| 5 · Nova versió requereix_reacceptacio → `pending/` la retorna; `/me` del tenant inclou `legal_pending` | **PASS** (pending + gate /me verificat a P3) |
| 6 · Cap camí d'esborrat (endpoint publicada→409 + ORM instància/queryset bloquejats) | **PASS** |
| 7 · `manage.py check` + `npm run build` verds | **PASS** |

**Nota IP/curl:** el cas 3 s'ha provat amb el format EXACTE de capçalera que nginx injecta (`HTTP_X_FORWARDED_FOR` via WSGI), retornant la IP del client i no la del proxy. El path nginx→gunicorn en viu és config-verified (sites `backoffice`/`ftt-staging`); la comprovació curl end-to-end contra el servei desplegat queda com a control post-deploy (el gunicorn en marxa encara no té aquest codi).

**Captures:** el build de la SPA és verd; nginx serveix el `dist` anterior fins al deploy → les captures de la pantalla real queden com a lliurable post-deploy (l'agent no desplega, CLAUDE.md).

## Handoff a PLATAFORMA + F4-bis
- **Handoff plataforma (UI de tenant):** F4 exposa `legal_pending` al `/me` del tenant (id, tipus, nom, numero_versio, sha256, contingut). **La UI de tenant que el mostra i el flux de checkbox → `POST /api/v1/legal/accept/` és territori PLATAFORMA** (no construït aquí). Decisió v1: cap bloqueig funcional dur; només el flag a `/me`. Usuaris no-admin: la plataforma ha de mostrar "pendent d'acceptació per l'administrador" sense bloquejar-los la lectura.
- **F4-bis (1 commit, quan F2-B hagi aterrat):** omplir el placeholder "historial d'acceptacions a la tab Legal de la fitxa del client" (a `TenantDetailPanel`, territori F2-B) consumint `GET /api/backoffice/v1/legal/acceptances/?client=<id>` (ja disponible i read-only).

## ⚠️ Accions CTO / desplegament
1. **`migrate_schemas`** (aplica `backoffice/0006` a public). Fet a staging; cal a PROD.
2. Verificar en viu (post-deploy) el path nginx→gunicorn de la IP amb un `curl -H "X-Forwarded-For: …"` real i captures de la pantalla.
3. Contingut legal real (documents/versions) l'autora Agus des de la pantalla; F4 no sembra cap document.

## Estat per al vault
- **F4 P-LEGAL COMPLET a `dev`** (5 commits, sense push): P1 models+hash+immutabilitat · P1b guard d'esborrat ORM · P2 endpoints · P3 gate /me + accept tenant · P4 pantalla. 7 casos verificats, staging netejat (0 files legals).
- **Territori net:** cap fitxer de F2-B tocat (TenantDetailPanel/alta intactes). Incursió al tenant mínima i sancionada (1 punt a /me + 1 ruta accept). `backoffice/urls.py` conviu amb les rutes de F1.
- **Handoff:** UI de tenant del `legal_pending` → plataforma. **F4-bis** (historial a la tab Legal de la fitxa) → quan F2-B aterri.
- **Deute anotat:** `/me` fa N+1 consultes lleugeres a public per calcular pending (poques files legals; negligible v1).
