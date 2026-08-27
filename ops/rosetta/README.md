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

## Els dos mòduls

- **`camp_montse.py`** (A + B) — ingesta i alineació. Python pur: reutilitza
  `engine/aama_reader.py` (que no importa Django) i no en depèn de res més.
- **`rosetta_837.py`** (C + D) — mesura i comparació. Necessita Django només per llegir
  les receptes `PatternPOM` i els `GradedSpec`.

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
2. **No porta números de regla.** El camp és extensional (coordenades per talla). Les
   regles viuen al germà `…_AGUS.DXF`.
3. **És un sol model.** El 837 és el banc sencer de graduació que tenim
   (v. D-INV-7: el corpus GarmentCodeData no val per a grading).

## El DXF no és a git

Ni la niada (`docs/ordres/837 CORS 194 VESTIT M3-4 ESCALAT.DXF`) ni el patró mestre
(`backend/media/fhort/pattern_files/837_CORS_194_VESTIT_M3-4_AGUS.DXF`) es commiten: el
material CAD del 837 viu al servidor, com la resta de `docs/ordres/` i tot el `media/`.
El que sí que hi és, i és el que fa la feina reproduïble, són **els dos md5** —a la
capçalera de l'informe i a `parity_837.json` → `meta`— i el dataset, que porta la geometria
sencera de les cinc peces a les cinc talles.
