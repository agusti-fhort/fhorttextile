# PLA D'EXECUCIÓ · TRAM C — CAPES A MESURES (Fase 1)

**Data:** 2026-07-31 · Estat: PROPOSTA per a ratificació Agus (Patró C)
**Fonts:** Diagnosis/DIAGNOSI_CAPA_POMS.md (cens ~70 nodes, fitxer:línia) + ARQUITECTURA_FACETES_I_CAPES.md (§3b/3c/3d, decisions 30/07) + report represa C1 (3efe7f4b)
**Principi:** cap node inventat — tot surt del cens. Cap UI sense maqueta aprovada (llei 3c.5). Comporta CHECK viva fins a C4. Cap canvi visible fins a C4 (pin + fumeig com a xarxa a cada onada).

---

## 0 · PREREQUISITS (bloquegen l'arrencada, no es negocien)

| # | Què | Bloqueja | Estat |
|---|---|---|---|
| P1 | ✅ RESOLT (Agus 31/07): push amb C1 viu; CAP DEPLOY fins acabar el tram (dilema A/B dissolt: C1 arriba a PROD amb els consumidors ja fets) | — | — |
| P2 | ✅ VALIDAT per Montse (Agus 31/07): 6 capes canòniques | — | — |
| P3 | Decisió Patró C: **on viu la norma de folgança** (casa / GTI / model) | C3-derivació | ⏳ Agus (pendent §5 arquitectura) |
| P4 | Receptes Montse: folgances per capa per POM | C3-derivació (valors) | ⏳ paquet Montse |
| P5 | Maquetes pendents (vegeu §DISSENY) | C3-fitting · C4 sencer | ⏳ |

**PATRÓ A ROMANENT (únic, embegut com a Fase 0 de l'Onada 1):** re-cens delta a HEAD actual — (a) re-localitzar els ~20 nodes d'Onada 1 (línies del 30/07; dev ha mogut: NOMS-POM/TAULES/CAPÇALERA toquen serializers i TechSheetEditor); (b) grep de lectors NOUS nascuts als 5 sprints posteriors al cens; (c) vigència de la llista d'exclosos. Delta trivial → l'agent continua; node nou o desaparegut → STOP i report (bloquejador dur).

**Ja tancat (no re-obrir):** D1–D6 ratificades · grading: ModelGradingRule SENSE capa, GradedSpec AMB capa (3c.1; C1 ho ha construït així) · backfill tot=exterior (fet) · maqueta Mesures v2 APROVADA (columna capa davant, tint per grup, sense columna família, tolerància fora) · text POM editable per model = **JA LLIURAT** (sprint NOMS-POM) · catàleg 6 capes sembrat ×3 idiomes ×3 schemas (C1).

---

## C2 · CONSUMIDORS PER ONADES (comporta tancada · zero canvi visible)

### ONADA 1 — LECTORS-DICT 🟠 (candidata a nit end-to-end)
**RE-CENS 31/07 EXECUTAT** (docs/diagnosis/RECENS_DELTA_ONADA1_2026-07-31.md al repo): 12 IGUAL · 8 MOGUT (línia idèntica) · 0 CANVIAT/DESAPAREGUT · +4 NOUS (N1/N2/N4 → Onada 1 · N3 → Onada 2 dins materialize_lines) · +1 NO CENSAT preexistent (X1 base_stages_view → Onada 1, protegit pel pin). **ESMENA: els 5 nodes frontend (bmByPom/cotaLabelDe/lineByPom/pomMap/lineId) passen a C4** — el contracte no porta capa fins C4 (OpenAPI 0-diffs), adaptar-los ara seria codi mort; línies re-censades: TechSheetEditor 3452/5513/5614/276 · CheckMeasureEditor 217 · measureSources 18 · fittingGridAdapter 144.

Contracte per node: cap `{pom_id: valor}` sobre taules amb capa; la clau passa a `(pom_id, capa)` amb lookup per la capa de la línia consumidora, o filtre `capa` explícit i comentat quan el consumidor vol semànticament l'exterior. Amb comporta tancada el resultat és idèntic → **pin i fumeig byte-idèntic són el green flag**.

Nodes backend (línies del re-cens 31/07, HEAD 3efe7f4b):
1. `pom/services.py:711` `_load_model_overrides`
2. `pom/s10_views.py:43-55` toleràncies · `s8_views:179-183` · `s11_views:161-165` POMAlert · `s6_views:86-90`
3. `fitting/graded_spec_views.py:85-98` payload fitxa (4 mapes, inclou N1 `bateig_map` :95-98/:116-118)
4. `fitting/serializers.py:259-262` (+ corregir comentari :255 «unique per (model, pom)» → «(model, pom, capa)») · `serializers_size_check:81-84`
5. `models_app/pom_placement_views.py:68-71` bm_by_pom
6. `fitting/repas_views.py:253-259` (4 mapes, inclou N2 :259/:276-277) · `pom/grading_views.py:120-141`
7. **N4** `models_app/views.py:3962-3964` `_sembra_step_des_dels_specs` — filtre `capa` explícit (àncora exterior, ref. 3c.1)
8. **X1** `models_app/views.py:2992/:3000/:3004` `base_stages_view` — el node del pin: fumeig el vigila directe

**EXCLOSOS d'Onada 1 amb motiu:** `_load_base_measurements` :748-766 (MOTOR, INTOCABLE → C3 amb decisió humana) · `_load_grading_rules` :683-706 (regla sense capa per decisió 3c.1 — només verificar i comentar) · `patterns/views:544` + `grading_projection:179` + `adapters:585-624` (FASE 2 patrons; el forat viu "POM a 2 peces" és micro-fix independent ja anotat als fils oberts).

**Harness de prova 2-capes (decisió tècnica del brief):** dins de transacció de test, `DROP CONSTRAINT …_capa_gate_c1` → inserir fila folre → verificar que cap lector col·lapsa → rollback. És l'única manera de provar el cas real amb la comporta desplegada al test-DB.

### ONADA 2 — ESCRIPTORS 🔴/🟡
Tot escriptor declara capa (avui: literal `'exterior'`) i cap `get_or_create`/`.first()`/poda opera cec de capa:
1. `resolve_size_check` services_size_check:179-181 (get_or_create) + `materialize_lines` :24-37 — **inclou N3 `ja_hi_son` :35-40** (re-cens 31/07: creua SizeCheckLine × BaseMeasurement per pom sol; s'adapta amb l'escriptor, no es parteix la funció)
2. `consolidate_base_from_fitting` fitting/services:369-371
3. `tech_sheet_views:364` · `set_measurements_view` views:1779 · `gravar_pom_view` :1903
4. extraction confirm :2560 + delete de buides :2515-16 · `wizard_views:192,:205`
5. `materialize_poms` views:1181-1200 — **la capa neix a l'ITEM** (D6): sembra item→model heretant capa
6. còpia de model :1416 · `desactivar_pom_view` :3789 · poda creuada :1800/:1925/:2333 (mai desactivar l'altra capa)
7. `reorder` :2018 + ordering: decisió de la maqueta v2 = files ordenades per capa → **ordre viu dins de capa** (migració d'ordering + adaptació MeasureGrid:274-282)
8. Federació: `_clau_natural_pom` :552 + federation_service:689 — la capa VIATJA a la clau natural (mai endevinar, docstring :545-550)
9. MeasurementChangeLog: escriptors estampen capa (columna ja hi és; F1 verificat a C1); l'històric append-only NO es reescriu (decisió D3.2)

### ONADA 3 — IMPORT/WIZARD PAS 2 (té UI → maqueta abans del brief)
Les 3 regles de 3b en ordre: (1) lèxic multilingüe de capa a la descripció (LINING/FORRO/FOLRE/INNER→folre · FUS→entretela) · (2) capçaleres de secció tenyeixen files · (3) nomenclatura duplicada amb context→cada una a la seva capa; sense context→**CUA DE CONFIRMACIÓ, mai endevinar**. `many_to_one` passa a distingir àlies-dolent (mateixa capa) vs legítim (capes diferents) — retirar-lo tornaria l'esborrat silenciós (D4.4.3). Exhibit A de QA: model 205 PROD (doble F2 col·lapsada).

---

## C3 · MOTOR + DERIVACIÓ (decisió humana, mai de nit)

1. **Motor** `_load_base_measurements` :748-766 → `{(pom, capa): valor}`. Zona intocable: sessió diürna, Agus present, pin com a xarxa, fumeig T0' abans/després.
2. **Grading per capa:** mateixos deltes (regla compartida), GradedSpec emès per capa quan existeixin files no-exterior.
3. **REGLA DE DERIVACIÓ (família ancorada, 3c.4):** família = mateix (model, pom) a capes diferents; es propaga l'INCREMENT mai l'absolut; en corregir exterior (fittings inclosos) → informar afectacions + aplicar a la família d'un gest (defecte sí, desmarcable); tota propagació pel changelog F1 amb origen "derivat de". **Bloquejada per P3+P4.**
4. Auditoria de 3 plans (espec↔exterior · exterior↔folre · peça↔peça) — es dissenya aquí, es reconcilia amb AUDITORIA_DE_MODEL.md.

## C4 · AIXECAR LA COMPORTA + UI (només quan C2+C3 verds)

1. Mesures: columna capa (maqueta v2 aprovada) + manual "el POM ja existeix en una capa → ofereix l'altra" + tolerància fora de la vista (dada es conserva per veredictes)
2. Fitxa: subcontenidors per capa al panell d'assignables (gramàtica seccionsDelModel :5075) + **impressió: taules per capa al paper**
3. Import escriu capes reals (Onada 3 activada)
4. Migració de retirada de les 20 comportes `*_capa_gate_c1` — l'últim commit del tram, mai abans
5. OpenAPI exposa capa (primer canvi de contracte visible — versionar payload fitxa)

---

## DISSENY PREVI OBLIGAT (llei 3c.5 — cap brief amb UI sense maqueta aprovada)

| Maqueta | Per a | Estat |
|---|---|---|
| maqueta_capes_mesures_v2.html | C4-Mesures | ✅ APROVADA 30/07 |
| Fitting: presa de mesures amb avís de família | C3-derivació | ❌ pendent |
| Wizard pas 2: capa per fila + cua de confirmació | Onada 3 | ❌ pendent |
| Fitxa: subcontenidors per capa (panell + paper) | C4-fitxa | ❌ pendent |

## GREEN FLAGS (per onada, innegociables)
`manage.py check` · pin base_stages 13/13 · fumeig md5 contra T0' (byte-idèntic fins C4) · OpenAPI 0 diffs fins C4 · comporta viva (test negatiu dins rollback) · `npx eslint` fitxers tocats · `npm run build` · harness 2-capes verd on toqui · un concern per commit · CAP push d'agents.

## SEQÜÈNCIA PROPOSADA
P1→(Onada 1 nit)→report→(Onada 2 nit)→report→[P3/P4/maquetes en paral·lel]→Onada 3→C3 diürn→C4. Cada onada s'atura en vermell no explicat (regla del verd). FASE 2 (patrons/realització) fora d'aquest pla — es reprèn a part amb DISSENY_IDENTITAT_PECES + D1.3/D3.3 de la diagnosi.
