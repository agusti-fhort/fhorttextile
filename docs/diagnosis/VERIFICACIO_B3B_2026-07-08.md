# Verificació runtime B3b — SalesOrder + conversió oferta→comanda (2026-07-08)

Gate dur de la FASE 2 (S5). Execució en `schema_context('fhort')` dins `transaction.atomic()`
revertida (cap dada persistida). Codi verificat: commits S1–S4
(`9843704`, `d0fdaf4`, `43f7c5e`, `d9f5d31`).

## Cas base
- Client `BRW` (règim DOMESTIC), producte `FITSES` (IVA 21%), condició de pagament `30D`.
- Oferta SENT amb **2 línies**: 1×375,00 i 2×50,00 → subtotal **475,00** · IVA **99,75** ·
  total **574,75**.

## Resultats (14/14 PASS)

| # | Comprovació | Resultat |
|---|---|---|
| 1 | Conversió SENT → SalesOrder amb número **SO-2026-0001** | ✅ |
| 2 | Totals de la comanda **idèntics** a l'oferta (475,00 / 99,75 / 574,75) | ✅ |
| 3 | Línies **congelades**: 2 línies, `unit_price` copiat (375,00 / 50,00) | ✅ |
| 4 | `due_dates` **regenerats** sobre la comanda == els de l'oferta | ✅ |
| 5 | L'oferta queda **segellada** (`status=ACCEPTED`) | ✅ |
| 6 | Guard: oferta **DRAFT** no es converteix (ValidationError) | ✅ |
| 7 | Guard: **segona conversió** del mateix quote falla (source_quote unique) | ✅ |
| 8 | Guard: editar **preu/quantitat de línia de comanda** per API → read-only (ignorat) | ✅ |
| 9 | Guard: editar línia d'oferta **ACCEPTED** per API → `is_valid()` fals | ✅ |
| 10 | `qty_allocated` PATCH vàlid quan ≤ quantity (1,50 ≤ 2) | ✅ |
| 11 | `qty_allocated` > quantity **bloquejat** (5,00 > 2) | ✅ |
| 12 | Numeració SO **independent** d'OF (seqüències separades per doc_type) | ✅ |

Seqüències al final del cas: `quote` last_seq=10 · `sales_order` last_seq=1 (files
`DocumentSequence` distintes). Tot revertit en sortir de l'atomic.

## Notes
- La condició `30D` només té 1 fracció (100%), per això 1 venciment. El motor de venciments
  (`generate_due_dates`) és el mateix que Quote (verificat a B3a amb l'ajust del cèntim a la
  darrera fracció); la generalització B3b només resol la FK correcta (quote vs sales_order).
- Irreversibilitat imposada a dues capes: model (SalesOrderLine sense edició de preu al clonatge
  intern) + API (serializer `read_only`). No hi ha reversió; l'única sortida és
  `status=CANCELLED` de la comanda (no reobre l'oferta).

**Veredicte:** GATE VERD. Es continua a S6 (frontend).
