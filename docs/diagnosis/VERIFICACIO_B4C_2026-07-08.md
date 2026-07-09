# VERIFICACIÓ B4c — Albarà (DeliveryNote) · cas Brownie complet

Data: 2026-07-08 · staging `/var/www/ftt-staging`, branca `dev` · Patró B (implementació).
Tanca el **CAS BROWNIE**: comanda → encàrrec → tasques → extra → deducció → albarà → PDF.
Test d'acceptació del mòdul Comercial. **CAP push** (el fa l'Agus des de SSH).

## Abast implementat (4 commits)
| # | Commit | Focus |
|---|--------|-------|
| 1 | `ae40ec6` | `commerce: DeliveryNote/Line + marca WO albaranat` |
| 2 | `2f1ae2b` | `commerce: generacio albara amb gate extres + emissio` |
| 3 | `aa43382` | `commerce: PDF albara sense venciments` |
| 4 | `2c320f7` | `commerce: frontend Albarans + modal emissio` |

## P0 — ConsumAlbara: VEREDICTE
No existeix cap classe `ConsumAlbara`. `models_app/models.py:743` és `ConsumptionRecord`
(docstring "Sprint 4: albarà de consum") — **domini de consum/meritació, DISJUNT** del
`DeliveryNote` comercial de B4c. Consumidors vius: tots dins el domini consum (hook
`services_c.py:140-154`, `reconcile_consumption.py`, `models_app/views.py` llista 4.5,
mirall backoffice). **ZERO referències des de `commerce/`** (grep buit). No és el nostre
albarà ni s'hi relaciona. Decisió: NO tocat, documentat, seguit (segons brief).

## Decisions aplicades
- Albarà **SENSE venciments**: `recalculate_totals` NO crida `generate_due_dates`; cap 3a FK
  a `DocumentDueDate` (no es reobre el XOR dual-FK de B3b).
- Neix **DRAFT** amb línies **proposades** pel sistema; editables (preu/descripció) només en
  DRAFT (guard patró Quote). **ISSUED = congelat**; els WO inclosos queden marcats albaranats.
- Agrega **1..N WorkOrder CLOSED del mateix customer** (granularitat = WO sencer).
- **EXTRA_ABSORB no genera línia.**
- `product` de la línia fet **nullable** (override): línies TASK/DEDUCTION/EXTRA/MANUAL sense
  article; `compute_document_totals` tracta `product=None` com a 0%. L'IVA de les línies d'un
  WO ORDER surt del `order_line.product`.
- `issued_by` → `accounts.UserProfile` (patró de la casa `created_by`/`closed_by`; el "FK User"
  del brief era laxe).

## Gate d'extres (el TODO de B4b, ara a l'emissió)
Viu a `generate_delivery_note`: cap `ModelTask off_recipe=True` sense `WorkOrderAdjustment`
que la resolgui → bloqueja llistant-les ("pendents de revisió comercial"). NO al close.

## Verificació RUNTIME (txn revertida, schema `fhort`) — 16/16 PASS
Cas sintètic sobre el customer real **Textiles y Confecciones Brownie SL** (id 7), article
`FITSES` (INTERNAL_SERVICE, 21%). Script: `scratchpad/verify_b4c.py`.

**CAS A — WO ORDER: 2 Done recepta + EXTRA_BILL 150 + DEDUCTION**
- Albarà DRAFT amb 4 línies: 2×TASK @100 (preu snapshot), 1×EXTRA +150, 1×DEDUCTION −100.
- subtotal **250.00** (100+100+150−100) · IVA 21% base agregada **52.50** · total **302.50**.
- WO marcat albaranat (`delivery_note` = la nota).

**CAS B — extra SENSE Adjustment** → `generate` bloqueja: "L'encàrrec WO-… té extres pendents
de revisió comercial: pattern_hand."

**CAS C — WO COLLECTOR** → línia TASK amb `quantity=90` (minuts reals de TimerEntrada),
`unit_price=0` proposat, `product=None` (el Salva posa preu en DRAFT; cap tarifa inventada).

**CAS D — segona inclusió del mateix WO** → bloqueja: "…ja està albaranat."

**CAS E — issue congela** → status ISSUED + issued_by/at; editar una línia post-ISSUED **falla**
(guard DRAFT-only).

**CAS F — esborrar DRAFT** → el WO queda alliberat (`delivery_note` → NULL via SET_NULL),
re-albaranable.

## PDF (`scratchpad/albara_b4c.pdf`)
`generate_document_pdf(dn, doc_title='Albarà', show_payment=False)`: SENSE bloc de venciments/
condicions ni "Vàlid fins"; peu amb Observacions/notes; línia DEDUCTION amb signe − i color
discret (DGREY). PDF byte-vàlid (`%PDF-1.4`), total 121.00 (base 100 = 200−100, +21% IVA).
`_money(-100)` → `-100,00` (signe verificat). **Obertura visual pendent de l'Agus** (l'entorn
d'agent no té renderitzador de PDF).

## Portes verdes
- `python manage.py check` net (a cada peça).
- `npm run build` net.
- Guardians frontend: cap hex, icones Tabler outline (`ti-truck-delivery`, `ti-file-invoice`,
  `ti-send`, `ti-file-download`, `ti-trash`, `ti-arrow-left`, `ti-check`), i18n ca/en/es paritat.

## Fora d'scope (confirmat)
Settlement/liquidació + venciments d'albarà (B5) · gate de tier (B5) · informes (B6) ·
tresoreria (B7) · tarifa de venda per defecte del col·lector (decisió de producte futura) ·
`ConsumAlbara`/`ConsumptionRecord` (només P0, cap toc).

## Per al CTO
- Revisar `git show` dels 4 commits (`origin/dev..HEAD`) i fer **push des de SSH**.
- Obrir `scratchpad/albara_b4c.pdf` per a la confirmació visual de la línia negativa.
- (Opcional) Ara que B4a+B4b+B4c són complets, valorar segellar `DIAGNOSI_B4_WORKORDER` i
  moure-la a `arxiu/` — deixada vigent perquè B5 (Settlement) encara s'hi recolza.
