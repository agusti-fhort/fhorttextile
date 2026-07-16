# REPORT · F1 P-PRICE — Catàleg de preus a Stripe (font única del preu)

> Data: 2026-07-14 · Branca: `dev` (staging) · Sense push (llei de mètode).
> Base: `PLA_IMPLEMENTACIO_BACKOFFICE.md` peça F1 · `FTT_PRICING_MODEL_V1.md §17`.
> Decisions: **D-P2** (el motor propi factura; Stripe NOMÉS cobra i és font de veritat
> del PREU) · **D-P3** (ajust per país via Prices; arrenca amb EUR, matriu pendent).

---

## PAS 0 — Secrets (guarda)

- `STRIPE_SECRET_KEY` i `STRIPE_PUBLISHABLE_KEY` **absents** a l'inici → STOP i petició a
  l'Agus. Afegides per l'Agus a `backend/.env`, verificades **només pel nom + prefix**
  (mai el valor): `sk_test_…` / `pk_test_…` → **mode test confirmat**.
- Cap `sk_`/`pk_` literal al codi commitejat (grep final net). El `.env` no entra a git.

---

## P0 — Patró A curt (cens read-only)

### Camps de preu vius (billing vell = **parked**, NO tocats)
| Fitxer:línia | Camp | Tipus | Nota |
|---|---|---|---|
| `tenants/models.py:35` | `Plan.preu_mensual` | Decimal(10,2) | quota base del pla |
| `tenants/models.py:47` | `Plan.preu_model_extra` | Decimal(10,4) | excés per model |
| `tenants/models.py:48` | `Plan.moneda_pla` | Char(3)='EUR' | |
| `backoffice/models.py:57` | `ContractLine.preu` | Decimal(10,4) | preu real per tenant |
| `backoffice/models.py:121` | `InvoiceLine.preu_unit` | Decimal(10,4) | |
| `backoffice/models.py:122` | `InvoiceLine.total` | Decimal(10,2) | |
| `backoffice/models.py:89` | `Invoice.total` | Decimal(10,2) | |

> Aquests camps són el **billing vell** (motor propi). F1 NO els toca: Stripe custodia
> el preu de catàleg; el motor seguirà facturant amb les seves entitats. F5/F7 sabran
> què hi ha aquí.

### Preus hardcoded (250/750/imports)
- `backoffice/**` (.py) i `frontend-backoffice/src/**`: **cap** literal 250/750 ni import
  en cèntims. Els números del catàleg viuen només al document `FTT_PRICING_MODEL_V1.md`.
- `ServiceCatalog` (`backoffice/models.py:82`) ja és **sense preu** per disseny ("el preu
  viu al ContractLine de cada tenant"). Coherent amb "la BD FHORT no guarda imports".

### Estat BD
- `public.tenants_plan` → **0 files** (cap seed de Plan; esperat).

---

## P1 — Catàleg declaratiu + sync (commit `ed84834`)

- **`backend/fhort/backoffice/pricing_catalog.yaml`** — 6 entrades:
  `starter|team` × `platform(month) | model(one_time) | extra_user(month)`.
  El càrrec per **model és one_time** (preu unitari que F6 usarà per cobrar meritacions),
  **no** subscripció. Free NO hi és (no hi ha res a cobrar). Convenció de `lookup_key`:
  `{tier}_{concepte}_{moneda}[_{pais}]`; cap entrada amb país encara.

  | lookup_key | unit_amount (cèntims) | interval |
  |---|---|---|
  | `starter_platform_eur` | 25000 (250 €) | month |
  | `starter_model_eur` | 2500 (25 €) | one_time |
  | `starter_extra_user_eur` | 3000 (30 €) | month |
  | `team_platform_eur` | 75000 (750 €) | month |
  | `team_model_eur` | 2500 (25 €) | one_time |
  | `team_extra_user_eur` | 3000 (30 €) | month |

- **`pricing_service.py`** — `load_catalog()` (validació forta + convenció),
  `configure_stripe()`, `resolve_pricing()` (cache/degradació per a P2), `sget()`
  (stripe 15.x **no** té `.get()` als seus objectes → accessor segur).

- **`sync_stripe_catalog`** (management command) — `--dry-run` per defecte (llegeix Stripe
  **sense tocar**), `--apply` executa. **Idempotent per lookup_key**: `OK-CREATED` /
  `OK-UNCHANGED` / `OK-ROTATED`. Rotació = crea Price nou amb `transfer_lookup_key=True`
  + **arxiva** l'antic (`active=False`). **MAI esborra** res a Stripe. Product amb id
  determinista `fhort_{tier}_{concepte}` (retrieve fort, no `search` eventual).

- **`settings.py`** — `STRIPE_SECRET_KEY`/`STRIPE_PUBLISHABLE_KEY` del `.env`, ruta del
  catàleg, `PRICING_CACHE_TTL=300`.
- **`requirements.txt`** — `stripe==15.3.0`, `PyYAML==6.0.3` (import directe). Instal·lats
  al venv (`backend/venv`).

## P2 — Endpoint amb cache (commit `795b3eb`)

- `GET /api/backoffice/v1/pricing/` (autenticat) i `GET …/pricing/public/` (AllowAny, per
  a la web). Mateixa resposta. `?country=ES` → `{tier}_{concepte}_eur_{pais}` amb fallback
  a la variant EUR base. **Free hardcoded a 0** a la resposta.
- **Cache 5 min** per país (LocMemCache, default de Django). Un sol `prices.list` per
  refresc, **batchejat en trossos de 10** (límit dur de Stripe).
- **Degradació**: Stripe cau i hi ha cache → serveix stale + `X-Pricing-Stale: true`;
  cap cache → **503** amb missatge clar. Clau absent = Stripe indisponible. MAI inventa.

## P3 — Ganxo a Plan (commit `616d814`)

- `Plan.stripe_lookup_platform` / `stripe_lookup_model` (CharField 100, nullable). NO és
  preu: és el **punter** al `lookup_key` de Stripe. Migració `tenants/0004` (app SHARED →
  schema `public`); auditat a `public.tenants_plan` (varchar 100, nullable). **Sense seed**
  de Plans (va amb la fitxa de client, fase posterior).

---

## Verificació (tot en mode test de Stripe)

| # | Prova | Resultat |
|---|---|---|
| 1 | `sync` dry-run (llegeix Stripe, no toca) | ✅ pla coherent; res tocat |
| 2 | `sync --apply` → CREATED×6; 2a vegada → UNCHANGED×6 | ✅ idempotència |
| 3 | `team_platform_eur` → 800 €, `--apply` → ROTATED; antiga `active=false`, lookup_key transferit; nova `active=true`. Endpoint (cache invalidada) reflecteix el vigent | ✅ · revertit a 750 i re-aplicat (catàleg als valors del document) |
| 4 | Endpoint `?country=DE` → fallback EUR (cap entrada de país) | ✅ `team_platform_eur` 75000 |
| 5 | Clau invàlida (env buit **només al shell de prova**, `.env` real intacte): amb cache → stale + header; sense cache → 503 | ✅ |
| 6 | grep final: cap `sk_`/`pk_` ni import en cèntims al codi commitejat | ✅ net |

`manage.py check` net abans de cada commit.

---

## Estat per al vault

- **F1 P-PRICE tancada a `dev`** (3 commits: `ed84834` P1 · `795b3eb` P2 · `616d814` P3).
  **Sense push** — el push i el deploy els fa l'Agus des de SSH.
- **Estat viu a Stripe (test)**: 6 Prices actius amb els `lookup_key` del catàleg,
  `team_platform_eur` = **750 €** (l'històric de proves va deixar Prices arxivats
  `active=false` amb el lookup_key ja transferit — normal, MAI s'esborren).
- **Font de veritat del preu = Stripe.** El YAML és el catàleg desitjat; la BD FHORT
  només guarda `lookup_keys` (ganxo a Plan, encara buit).

### Accions de l'Agus per al deploy
1. `pip install -r requirements.txt` al venv de PROD (arrossega `stripe`, `PyYAML`,
   `requests`, `urllib3`) i regenerar `requirements.lock`.
2. Afegir `STRIPE_SECRET_KEY` i `STRIPE_PUBLISHABLE_KEY` (mode **live** a PROD) al `.env`.
3. `migrate_schemas` (migració `tenants/0004`, app SHARED).
4. `python manage.py sync_stripe_catalog --apply` **al compte Stripe de PROD** (crearà els
   Prices live). Revisar el resum abans de donar-ho per bo.

### Pendents / decisions per a l'Agus
- **Matriu multi-país (D-P3)**: de moment només EUR. Quan hi hagi la matriu, afegir
  entrades amb `country` al YAML (`{tier}_{concepte}_eur_{pais}`) i re-sync; l'endpoint ja
  resol el fallback.
- **Seed de Plans + omplir `stripe_lookup_*`**: fase posterior amb la fitxa de client.
- **Enterprise**: fora de catàleg públic (contracte a mida), no va a Stripe — confirmat.
- El **billing vell** (`ContractLine`/`Invoice`, motor propi) segueix parked; F5/F7 decidiran
  com conviu amb el cobrament via Stripe.
