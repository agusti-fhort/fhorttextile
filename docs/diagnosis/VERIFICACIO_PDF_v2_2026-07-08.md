# VERIFICACIÓ — PDF d'oferta v2 (disseny Montserrat validat)

Data: **2026-07-08** · staging `/var/www/ftt-staging`, branca `dev` · schema `fhort`.
Commits: P1 `e57c38f` · P2 `a87b6c6` · P4 `a5e86aa` · P3 `b874b04`.

## Diagnosi prèvia (Patró A lleuger)
- **A)** Servei PDF a `backend/fhort/commerce/pdf_service.py` (signatura `generate_quote_pdf(quote)->bytes` intacta).
- **B)** Model `accounts.TenantConfig` → afegit `logo_file`. El serializer real és
  `pom/s2_serializers.py:TenantConfigSerializer` (NO `accounts/serializers.py`, que no en té);
  és `serializers.Serializer` amb camps explícits → **no s'edita** (fora d'scope commerce/+accounts/
  i la UI d'upload és futura). El PDF llegeix `logo_file` directament del model.
- **C)** ⚠️ **Cap font Montserrat al servidor** (ni `.ttf` ni `.woff`). Implementat `PDF_FONTS_DIR`
  configurable (default `backend/assets/fonts/`, override per env) + **fallback a Helvetica amb WARNING**.
  L'Agus ha de deixar els 4 TTF (veure `backend/assets/fonts/README.md`) per al look validat.

## Migracions (aplicades i auditades)
- `migrate_schemas` → `accounts.0005_tenantconfig_logo_file` + `commerce.0005_seed_minute_unit` OK.
- BD `fhort`: columna `accounts_tenantconfig.logo_file` present · unitat `('minute','Minute')` sembrada.

## End-to-end (endpoint real, savepoint revertit)
| Cas | Resultat |
|---|---|
| `GET /quotes/{id}/pdf/` → 200 | PASS |
| Content-Type `application/pdf` | PASS |
| `%PDF-` magic | PASS |
| `Content-Disposition: attachment; filename="OF-2026-0003.pdf"` | PASS |
| Fallback: `PDF_FONTS_DIR` inexistent → PDF vàlid, **cap 500** | PASS |

## Criteri de mida (>20KB) — depèn de les fonts
- **Sense TTFs** (estat actual del servidor): fallback Helvetica, **~3KB** (Helvetica és font base,
  no s'incrusta). Vàlid i funcional.
- **Amb TTFs** (provat amb TTF real substitut, no commitat): fonts **incrustades → 43KB (>20KB)**.
  Confirma que el criteri >20KB del brief es compleix un cop l'Agus instal·li Montserrat.

**Resultat: TOT VERD.** Pendent només: deixar els 4 TTF Montserrat a `PDF_FONTS_DIR` (l'Agus).
