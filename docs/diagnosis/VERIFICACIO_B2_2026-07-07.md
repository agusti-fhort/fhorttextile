# VERIFICACIÓ RUNTIME — Comercial B2 (Quote)

Data: **2026-07-07** · staging `/var/www/ftt-staging`, branca `dev` · schema `fhort`.
Mètode: script en calent dins `schema_context('fhort')` + `transaction.atomic()` revertida
(cap dada persistida). Commits verificats: P1 `f5d31da` · P2 `ee38a44` · P3 `67fc078`.

## Migracions aplicades i auditades
- `migrate_schemas` (mai `--schema`) → `commerce.0003_documentsequence`, `commerce.0004_quote_quoteline` **OK** a `public` i `fhort`.
- Auditoria directa a BD (`information_schema`): `commerce_quote`, `commerce_quoteline`,
  `commerce_documentsequence` existeixen **NOMÉS a `fhort`**, **absents a `public`** →
  aïllament multi-tenant confirmat (commerce és TENANT_APPS pur, `settings.py:72`).

## Casos (tots PASS)
| # | Cas | Resultat |
|---|---|---|
| 1 | `document_number` format `OF-YYYY-NNNN` | PASS · `OF-2026-0001` |
| 2 | Numeració correlativa (+1, sense forats ni duplicats) | PASS · `OF-2026-0001 → OF-2026-0002` |
| 3 | `subtotal = Σ line_total` (recalc via signal) | PASS · `35.00` |
| 3b | `total = subtotal + tax_amount` | PASS · `42.00` (35 + 7) |
| 4 | Guard: afegir línia a Quote `SENT` → `ValidationError` | PASS |
| 5 | `DocumentSequence` per (doc_type, any) al schema `fhort` | PASS · `last_seq=2` |

**Resultat: TOT VERD.** No hi ha bloquejador; es continua a P5 (PDF).
