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

## FASE 2 — UI + assignació + traçabilitat (commits + build)

| Peça | Hash | Focus | Verd |
|---|---|---|---|
| P6 | `d24bd7d` | Pantalla de composició: safata per model (selecció per check), blocs-model amb capçalera + subtotal, ull de visibilitat, temps intern en gris, comentaris MANUAL, INVOICED | `npm run build` net |
| P7 | `ddfb6c8` | Acció massiva "Assignar a comanda" al menú de Models (reutilitza `assign_model_to_order_line`; guard un sol client) | build net |
| P8 | `821ec7e` | Traçabilitat: badge "amb comanda/directe" a Models + bloc cadena comanda→WO→albarà a la fitxa (lectura pura) | build net |
| P9 | `aeb49e6` | Rename tab Planificació "Pendents" → "Pendents d'assignar" (label i18n) | build net |

Guardians de front (delta): i18n ca/en/es en paritat (verificat per script a cada peça); icones
Tabler outline; colors via tokens CSS; IBM Plex Mono. Rutes noves resoltes (billable, draft,
add-lines, mark-invoiced, mark-invoiced-bulk). `has_order` i els números de document (WorkOrder/
DeliveryNoteLine) verificats a runtime contra `fhort`.

Nota (anotació, no bloqueja): el bloc de traçabilitat de la fitxa mostra els albarans v1 via
`WorkOrder.delivery_note` i els v2 via `?model=` a les línies; un albarà v1 (línies amb `model=NULL`)
apareix pel costat WO, no per la consulta de línies — comportament esperat.

## FORA D'SCOPE (confirmat)
PDF per model (prototip visual amb l'Agus primer), Settlement/B5 (l'INVOICED n'és l'avançada),
gate de tier, informes.

## PDF v2 per model (prototip validat portat a `pdf_service`)

`generate_delivery_note_pdf(delivery_note) -> bytes` (a `commerce/pdf_service.py`), geometria
LITERAL del prototip validat; capçalera i client heretats del pressupost (mateixa família).
Franja per model (fons `MODEL_BAND #F4EFE4`) amb ref intern + nom + [ref client si difereix] +
collection + temporada/any + "Lliurament · <última finished_at>"; detalls columnats (Descripció ·
Data · Qt · Unitat · Preu · Import), marcador `● feta`/`● pendent` si el model és parcial,
comentaris MANUAL en cursiva, subtotal per model, HR 0.3pt entre models, resum sense venciments.
La `pdf` action del `DeliveryNoteViewSet` ara crida aquest generador (substitueix el pla de B4c).

**Verificació runtime (Brownie real, txn revertida) — 8/8 PASS:**
| Comprovació | Resultat |
|---|---|
| Model amagat (182, `visible=False`) NO surt; visibles = {162,169} | **PASS** |
| Model 169 parcial (tasca reoberta en DRAFT → `● pendent`) | **PASS** |
| Model 162 complet (sense marcador) | **PASS** |
| Subtotals per model (162=30,00 · 169=45,00) | **PASS** |
| Total document = 75,00 (182 amagat exclòs dels totals) | **PASS** |
| Comentari MANUAL present i visible | **PASS** |
| Cap dada interna (min/temps/cost/tècnic) a les descripcions | **PASS** |
| PDF vàlid (`%PDF`, 25.471 bytes) | **PASS** |

Selecció/agrupació verificades replicant EXACTAMENT el que llegeix el generador (línies visibles →
grup per model → parcial via `model_task.status` → subtotal). Render visual no disponible al box
(sense poppler): mostra a `albara_v2_sample.pdf` (arrel del repo, no committat) per a la confirmació
visual de l'Agus. **A confirmar amb l'Agus:** línia de cortesia a "0,00 €" (mantenir 0, no "Inclòs").

## Estat final
FASE 1 (backend, gate 10/10) + FASE 2 (UI) + PDF v2 per model completes a `dev`, **sense push**
(el push el fa l'Agus). Revisar amb `git show <hash>`.
