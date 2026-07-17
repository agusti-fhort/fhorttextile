# DIAGNOSI — facturació recurrent (quota + consum): les juntes mai fetes treballar juntes

Data: 2026-07-17 · **Patró A exprés (READ-ONLY)** · staging `dev` · precedeix F-RECUR B

> Convenció: `fitxer:línia`; "NO EXISTEIX" = confirmat absent al codi. Fase A curta abans de
> construir; cap contradicció de paradigma trobada → es continua a la fase B (regles toves).

## Resum

- **A1 — eix temporal INSUFICIENT.** `TenantContract` té `data_inici`/`data_fi`/`actiu`
  (`models.py:227-229`) → sap si un contracte és vigent en un període, però **NO** té periodicitat:
  res diu si la quota és mensual, trimestral o anual. `ContractLine` no en té gens. **Gap: cal un eix
  de periodicitat configurable** (mensual per defecte).
- **A2 — el forat anti-doble-cobrament EXISTEIX i és real.** `ModelConsumptionEvent` té
  `['id','codi_client','period','opaque_ref','merited_at']` (`models.py:79-87`): **cap vincle a
  factura**. Avui el consum es compta amb `.count()` (`billing_service.py:63-65`), no es marca — re-
  executar refacturaria. **Cens staging:** 25 events; **FTT 4** (viu, 2026-06), i **21 ORFES** de
  tenants morts: BRW 18 (13 al juny + 5 al juliol) i LOS 3 (juny). Vius: només FTT i SYS.
- **A3 — la resolució de tarifa EXISTEIX, a mitges.** `billing_service` ja fa quota (`tier_fee`) +
  consum (`model_count`, amb `exces = n_models - inclosos`, `:80`). Però llegeix **només** la
  `ContractLine` del contracte (`:71`); **no hi ha fallback a Plan** ni error clar si falta la línia
  (simplement no factura el concepte). Els "inclosos" viuen a `ContractLine.inclosos` (`:252`).
- **A4 — ServiceCatalog COBREIX.** `tier_fee` (quota) + `model_count` (consum) + `manual` són suficients
  (`models.py:99-103`); a PROD/staging ja existeixen `QUOTA_BASE` i `MODEL_INICIAT`. **Cap tipus nou.**
- **A5 — el motor F-FACT-B1 és REUTILITZABLE tal qual.** `Invoice`/`InvoiceLine` fiscals, sèries,
  IVA per règim, DRAFT i PDF ja hi són. La comanda ha de crear DRAFTs amb els camps fiscals i **NO**
  emetre (l'emissió és acció humana amb sèrie). La sèrie mai hardcoded: paràmetre `--serie`.

## El pla de construcció (gaps, no contradiccions)

1. **Periodicitat** com a dada a `ContractLine` (o `TenantContract`): `periodicitat` (mensual default)
   + una manera de saber si la quota toca en aquest període. Migració backoffice additiva.
2. **Vincle event→InvoiceLine**: FK a `ModelConsumptionEvent` (`invoice_line`, nullable) + la garantia
   que un event vinculat no re-entra. Constraint dura, no disciplina.
3. **`billing_service` actual**: és previ a F-FACT-B1 (crea DRAFT sense IVA ni sèrie, i **compta sense
   vincular**). La comanda nova ha de: reutilitzar-ne la lògica de quota/consum, però **vincular** els
   events i deixar la factura llesta perquè `compute_totals` (F-FACT-B1) hi posi l'IVA en emetre.
   ⚠️ Watchpoint: NO trencar `generate_invoice` ni el seu endpoint `facturacio/generar/` mentre no
   es jubili — conviuen fins que la comanda nova el substitueixi.
4. **Orfes**: capacitat de marca d'exclusió/arxiu (no decisió d'ara). Els 21 events orfes no s'han de
   poder facturar (no hi ha Client viu → el motor ja els deixaria fora per manca de contracte, però
   convé una marca explícita perquè no reapareguin si el codi_tenant es reutilitza).

## Veredicte

Cap contradicció de paradigma. Tot són gaps additius sobre juntes que ja existeixen. **Es continua a
la fase B.**
