# DIAGNOSI — REVISIÓ PATRÓ MODEL TATE (queixa: "coses que no quadren")

**Data:** 2026-07-31 · **Patró A pur** (cap BD tocada, cap fitxer modificat)
**Font:** `TATE_fhort.DXF` (pujat a xat; **el .RUL NO ha pujat** → deltes de graduat no verificables)
**Substrat:** TAXONOMIA_PECES_PATRO Tanda 1 (TATE ja censat: PolyPattern 11.0.1 · AC1009 · AAMA · mm · 10 blocs = 8 producció + 2 bases `1rst_*` · sample S)
**Mètode:** ezdxf + shapely; arcs mesurats sobre contorn L1, piquets L4, punts de graduat L2 + regla `# N`, interns L8, drills L13. Res estimat.

## Construcció llegida
Brusa asimètrica: FRONT i BACK peces SENCERES (Quantity 1,0), tancament en diagonal per FRONT_YOKE (botons: 3 drills yoke + 5 drills/traus front), NECK_BAND corbada + entretela, màniga (1,1 = parell) amb obertura al puny, vistes FRONT_FACING i FACING_YOKE. Plecs laterals al davant marcats amb doble piquet + fletxa interna (L8).

## ✗ NO QUADRA (mesurat, per ordre de gravetat)

1. **NECK_BAND simètrica sobre escot asimètric.** Arcs de la banda entre piquets: **124.0 · 102.6 · 102.9 · 123.9** (simètrica). Escot real: yoke-costat 131.8 · esquena 100.4+100.4 · davant-costat 115.6. → Els piquets d'espatlla de la banda cauen **±8 mm** fora de les costures d'espatlla: en un costat falten 7.8 mm de banda (131.8→124.0) i a l'altre en sobren 8.3 (115.6→123.9). El TOTAL gairebé quadra (453.4 vs 448.2) i per això no es veu fins a cosir. Símptoma típic de taller: "el coll no em cau bé de piquets". **Candidat №1 a la queixa.**

2. **Costat inferior curt.** Costat superior: 357.3 − plec 23.0 = **334.3 = esquena 334.3 exacte ✓** (la intenció del patró és claríssima). Costat inferior: 355.6 − plec 25.2 = **330.4 vs 334.3 → −3.9 mm**, i els dos plecs laterals són asimètrics (23.0 vs 25.2) en un fitxer on tota la resta de simetries clava ≤0.2 mm. Un costat va ser retocat i l'altre no.

3. **Espatlles invertides.** Davant A 121.3 · davant B (yoke) 122.9 vs esquena 118.3/118.5 → el DAVANT és **+3.0/+4.4 mm més llarg** que l'esquena. La convenció és l'inrevés (embegut a l'esquena). A més, diferent per costat.

4. **Embegut de copa asimètric.** La MATEIXA màniga (1,1) entra en dues sises diferents: costat A embegut total 14.0 mm (mitja copa davant 8.2) · costat B **7.1 mm (mitja copa davant 0.5!)**. Una màniga muntarà bé i l'altra plana/tibant per davant.

## ⚠ SOSPITES DE GRADUAT (verificar amb el .RUL, no pujat)

5. **L'obertura del puny de la màniga NO gradua**: els 4 cantons de l'obertura + 1 punt del puny porten regla `# 1` (=0,0 per evidència de corpus: les bases `1rst_*` només porten #1) mentre la resta del puny porta regles pròpies → la posició/fondària de l'obertura queda clavada a la S a totes les talles.
6. **La guia de col·locació del yoke al front** (línia interna L8) porta `# 1` als dos extrems mentre la costura del yoke gradua → guia falsa a partir de la M.

## ✓ QUADRA (descartat)
Simetria d'esquena ≤0.2 mm · baixos 505.0/504.1 · piquets sisa↔copa (50.8↔50.5 · 60.3↔58.5/57.7) · yoke↔front piquet-a-piquet 80.2↔79.6 · FACING_YOKE 210.1↔yoke 210.5 · FRONT_FACING 186.8↔vora front 186.5 · entretela = netto de la banda (−12.7/extrem, −7.5/costat, arcs de piquets coherents) · integritat punt↔regla 100% a les 10 peces (cap punt orfe, cap regla òrfena) · numeració de regles per peça sense col·lisions (#2–#251; #144-148 compartides drill↔trau co-localitzats, correcte).

## Nota oberta (intenció, no error demostrat)
Vora del yoke 210.5 vs vora del front 186.5: **+25.7 mm concentrats a l'extrem del coll**. Piquet-a-piquet quadra; el diferencial és a l'extrem. Pot ser el solapament del tancament per disseny — preguntar Montse abans de tocar res.

## ⚡ ADDENDUM 31/07 (tarda) — RECLAMACIÓ DEL CLIENT: MARGES DE COSTURA

Client (via Salva): "les peces del cos no porten marge de costura; les altres sí". **Verificat: el símptoma és real, però el tall correcte és per-VORA, no per-peça:**

- **Rosetta:** `1rst_sleeve` (única peça amb L14) porta la línia de cosit a **7,0 mm exactes** del tall (355/400 mostres; trams a 0 = vores netes/doblecs). El marge de la casa és 7 mm.
- **Prova d'impossibilitat:** desplaçant les costures aparellades 7 mm cap dins (hipòtesi "marge inclòs"): embegut de copa = **−13,9 / −19,1 mm** → la màniga no entraria. A t=0: +14,0/+7,0 = normal. → **Les vores de MUNTATGE (sisa, copa, escot, espatlles, costats, vora yoke) SÓN la línia de cosit: NETES, sense els 7 mm.**
- **El que SÍ va inclòs:** baix del cos ~40 mm (piquets a 39,3–39,8 dels cantons) · baix de puny ~37 mm (línia de doblec + piquets 20/40) · **NECK_BAND amb 7,5 mm laterals + 12,7 extrems** (prova: entretela = netto exacte).
- Conseqüència 1: **el DXF tal qual NO es pot tallar**: cal +7 mm a totes les costures de muntatge, +0 a baixos i banda. Una vora neta ni tan sols es pot cosir (línia de cosit = vora de tall).
- Conseqüència 2 (revisa la troballa №1): la finestra de cosit real de la banda = 453,4 − 2×12,7 ≈ 428 vs escot net 448,2 → la banda queda **~20 mm curta en total**, concentrada al costat del yoke (−13,5 després de descomptar marges de vora davantera; costat A −2,7). La troballa №1 empitjora amb la lectura correcta dels marges.
- Risc mostres: si el confeccionista de mostres va tallar el DXF tal qual i va cosir a 7 mm, la mostra aprovada és ~14 mm més estreta per parell de costures que el patró net. Cal saber què es va fer a mostres abans de comparar amb producció.

## Per tancar la revisió
- Demanar el **TATE_fhort.RUL** → confirmar #1=(0,0) i validar 5/6 + els ±25 mm/talla de Tanda 1.
- Preguntes Montse: (a) el plec lateral inferior, 25.2 i costat −3.9: retoc conscient o descuit? (b) espatlla davant > esquena: volgut? (c) banda de coll simètrica: es va dissenyar abans del yoke asimètric? (d) +25.7 de la vora del yoke = solapament?
