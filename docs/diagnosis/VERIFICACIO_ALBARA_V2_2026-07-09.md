# VERIFICACIÓ — Albarà v2 (FASE 1: safata + composició + INVOICED + guard)

Data: **2026-07-09** · staging `/var/www/ftt-staging`, branca `dev` · schema `fhort`, client real **Brownie** (id=7).
Diagnosi font: [DIAGNOSI_ALBARA_V2_2026-07-09.md](DIAGNOSI_ALBARA_V2_2026-07-09.md).
Mètode: Patró B. Verificació runtime dins **transacció revertida** (cap escriptura persistida).

## Commits FASE 1 (branca dev, sense push)

| Peça | Hash | Focus |
|---|---|---|
| P1 | `827acd4` | Esquema: `DeliveryNoteLine.visible` + `.model`; `DeliveryNote` INVOICED + `invoiced_at/by`; migració 0018 |
| P2 | `fc1625e` | `get_billable_items(customer)` per model + endpoint `billable/` |
| P3 | `195a39e` | `create_or_get_draft` + `add_lines_to_draft` + endpoints `draft/`·`add-lines/` + línia MANUAL + editar `visible`/qty |
| P4 | `142deda` | Emissió amb guard de línia visible + estat INVOICED (`mark-invoiced` individual/massiu) |
| P5 | `1095feb` | Guard reobertura (tasca en albarà ISSUED/INVOICED no es reobre); `force=True` a la migració retype |

`python manage.py check` net a cada peça. Migració 0018 aplicada a `public` + `fhort`; columnes
auditades a BD (`visible`, `model_id`, `invoiced_at`, `invoiced_by_id`).

## GATE DUR — 10/10 PASS

Script executat contra Brownie, tota la seqüència dins un `transaction.atomic()` revertit al final.

| # | Comprovació | Resultat |
|---|---|---|
| 1 | `get_billable_items(Brownie)` → 3 blocs-model (162/169/182) | **PASS** `[162,169,182]` |
| 1 | **R2**: les 3 tasques albaranables tenen `work_order=NULL` (invisibles al flux v1) | **PASS** `[None,None,None]` |
| 2 | Composició: crear DRAFT + afegir 2 tasques de 2 models → 2 blocs-model | **PASS** `[162,169]` |
| 3 | Visibilitat: preus 10 → total 20; amagar 1 línia → total 10 | **PASS** `20.00→10.00` |
| 4 | Doble comptatge: 162/169 surten de la safata; 182 hi queda | **PASS** `[246]` |
| 5 | Reobertura amb línia en **DRAFT** → PERMESA | **PASS** |
| 6 | Emissió (guard línia visible) → ISSUED; `mark-invoiced` → INVOICED (+`invoiced_at`) | **PASS** `2026-07-09` |
| 7 | Reobertura de tasca en albarà **INVOICED** → BLOQUEJADA | **PASS** *"No es pot reobrir una tasca ja albaranada (albarà emès)."* |
| 8 | Esborrar el DRAFT → l'ítem torna a la safata | **PASS** `gone=True back=True` |

**Cap escriptura persistida** (rollback confirmat).

## Notes de decisió verificades
- La safata parteix de `ModelTask` (no de WorkOrder): recull la feina amb `work_order=NULL` — la
  bretxa estructural R2 de la diagnosi queda tancada.
- Els TOTALS es calculen sobre `lines.filter(visible=True)` (`DeliveryNote.recalculate_totals`); les
  línies amagades existeixen a BD però no compten (traçabilitat/cost).
- Detecció "albaranat" = `delivery_note_lines__isnull=True` a la safata: una línia en QUALSEVOL estat
  (DRAFT/ISSUED/INVOICED) treu l'ítem; esborrar el DRAFT (CASCADE de línies) el retorna.
- Guard de reobertura limitat a `Done→InProgress` i a albarans **ISSUED/INVOICED** (DRAFT no bloqueja).
  `force=True` només a la migració `retype_scaling_to_grading`; els altres 2 call-sites interns
  (size_check, tancament POM) no reprocessen tasques Done (exclouen `status='Done'`), no cal tocar-los.

## Pendent (FASE 2, no verificat aquí)
UI de composició (P6), assignació bulk a Models (P7), traçabilitat (P8), rename Pendents (P9).
FORA D'SCOPE: PDF per model, Settlement/B5, gate de tier, informes.
