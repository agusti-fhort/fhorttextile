# `ops/rosetta/` — el banc de paritat del 837

Compara el **grading real de la Montse** (`837 CORS 194 VESTIT M3-4 ESCALAT.DXF`, niada
explícita de 5 peces × 5 talles) amb **el que la fitxa del model 1383 declara**
(`GradedSpec` de la GV201 v9, segellada), i deixa el resultat en dos artefactes:

| artefacte | què és |
|---|---|
| `parity_837.json` | el **dataset** que el solver F6 carregarà com a banc |
| `../../docs/diagnosis/REPORT_ROSETTA_837_2026-08-27.md` | l'informe amb el veredicte |

## Córrer-ho

```bash
cd /var/www/ftt-rosetta && python3 ops/rosetta/rosetta_837.py
```

Escriu `parity_837.json` i escup l'informe per consola. **Read-only a la BD** (només
`SELECT` sobre `fhort`) i read-only al `media`; no toca cap taula ni cap fitxer del
producte.

## ⚠️ El fitxer NO entra pel camí de producte

Els 25 blocs `_TALLA` de la niada crearien 25 «peces» si passessin per
`services.save_pattern_file`. És **material de banc**: viu a `docs/ordres/` i es llegeix
des d'aquí, mai s'importa.

## Els mòduls

- **`camp_montse.py`** (A + B) — ingesta i alineació. Python pur: reutilitza
  `engine/aama_reader.py` (que no importa Django) i no en depèn de res més.
- **`rosetta_837.py`** (C + D) — mesura i comparació. Necessita Django només per llegir
  les receptes `PatternPOM` i els `GradedSpec`.
- **`rul_837.py`** (F6.3, A + B) — el **RUL** i el mapa regla→punt. Reutilitza
  `engine/rul_reader.py`; no en duplica la gramàtica. Python pur.
- **`exam_rul.py`** (F6.3, C + D) — reconstrueix les talles des del RUL i les compara amb la
  niada, i passa el solver amb l'horari declarat.
- **`exam_solver.py` · `exam_rank.py` · `exam_coupled.py` · `exam_structure.py` ·
  `exam_curves.py`** — els exàmens d'F6.1 i F6.2.

## ⚠️ El RUL arriba i canvia el punt 2 de la llista de sota

`837 CORS 194 VESTIT M3-4.RUL` (27/08, md5 `8379813b7f9767b6c38234f8ffadf77f`) porta les 90
regles amb deltes vius. Amb ell, **la graduació deixa de ser una cosa a inferir de 16 mesures i
passa a ser DADA**: base + RUL + mapa reprodueixen la niada de la Montse a **0,0073 mm** al
contorn de tall sencer (7 376 punts), que és l'arrodoniment del fitxer.

🚨 **Les dues numeracions no coincideixen.** El DXF invoca l'1 i 65–98 · 171–198 · 226–238; el
RUL en declara 90. Un `# 65` **no** és la `RULE: DELTA 65`. `rul_837.construeix_mapa` deriva la
correspondència dels blocs i no escriu cap número a mà; desplaçar-la un sol lloc porta la
reconstrucció de 0,0018 mm a 3,74 mm de mitjana i 51,53 de màxim.

🚨 **El RUL gradua el contorn de TALL i prou.** Cap desplaçament constant casa els números de la
línia de cosit (el millor deixa 11,8–18,3 mm): el CAD la deriva del tall.

## Les verificacions es poden veure VERMELLES

Cap de les cinc d'ingesta (A1 recompte · A2 correspondència · A3 orientació CCW ·
A4 origen únic de CONVENCIÓ-1 · A5 base ≡ patró mestre) és decorativa: totes cauen si es
toca el que miren. Per comprovar-ho, `dataclasses.replace` sobre el `Camp` abans de
`verifica()` —girar un bucle, moure un vèrtex 0,001 mm, empatar dos vèrtexs a Y mínima— i
la que toqui ha de dir `FAIL`.

## Les tres coses que aquest banc NO pot fer

1. **No porta capa 14.** El camp només té el contorn de tall; 19 de les 20 àncores de POM
   del 1383 viuen a la línia de cosit. S'hi **transporten**, i per tres camins alhora
   (`projeccio`, `vertex`, `fraccio`) perquè la dispersió entre ells sigui la barra d'error
   de cada fila i no una nota al peu. Un POM amb la barra travessant la tolerància queda
   **NO RESOLUBLE**, que no és el mateix que desviat.
2. ~~**No porta números de regla.**~~ **RESOLT (F6.3, 27/08).** El camp segueix sent
   extensional, però els números viuen al germà `…_AGUS.DXF` i **la taula que indexen ja la
   tenim**: `837 CORS 194 VESTIT M3-4.RUL`. v. la secció del RUL més amunt i
   `docs/diagnosis/REPORT_F63_RUL_2026-08-27.md`.
3. **És un sol model.** El 837 és el banc sencer de graduació que tenim
   (v. D-INV-7: el corpus GarmentCodeData no val per a grading).

## El DXF no és a git

Ni la niada (`docs/ordres/837 CORS 194 VESTIT M3-4 ESCALAT.DXF`) ni el patró mestre
(`backend/media/fhort/pattern_files/837_CORS_194_VESTIT_M3-4_AGUS.DXF`) es commiten: el
material CAD del 837 viu al servidor, com la resta de `docs/ordres/` i tot el `media/`.
El que sí que hi és, i és el que fa la feina reproduïble, són **els dos md5** —a la
capçalera de l'informe i a `parity_837.json` → `meta`— i el dataset, que porta la geometria
sencera de les cinc peces a les cinc talles.
