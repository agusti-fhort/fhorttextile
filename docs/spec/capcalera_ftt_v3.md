# SPEC · CAPÇALERA FITXA FTT — maqueta v3.3 (APROVADA Agus 2026-07-31)

Substitueix `docs/spec/plantilla_capcalera_ftt.svg` (marcat SUPERAT, no esborrat).
És la spec canònica: la geometria de la capçalera es MESURA d'aquí, no s'interpreta.
Unitats: pt de document. Origen (0,0) = cantonada superior esquerra de la banda.
Coordenades de text = CANTONADA SUPERIOR ESQUERRA de la caixa de text
(line-height 1 al cos indicat). Font: IBM Plex Mono. Filets: 0,5pt tinta.

## COLORS
- tinta (valors, filets, subratllat): --ink del sistema
- gris-etiqueta (etiquetes 7pt i copyright): --ink-soft (referència maqueta #8a857c)
- Konva no resol var(): usar els literals de KONVA_COL corresponents

## ESTILS DE TEXT
| estil  | cos  | pes     | color         | tracking |
|--------|------|---------|---------------|----------|
| lbl    | 7pt  | regular | gris-etiqueta | +0,02em  |
| v10    | 10pt | regular | tinta         | 0        |
| v12    | 12pt | regular | tinta         | 0        |
| v18    | 18pt | regular | tinta         | 0        |
| cur    | 12pt | BOLD    | tinta         | 0        |

Talla activa (cur): + línia pròpia sota el text — gruix 1,2pt, amplada =
amplada exacta del glif de la talla, situada 2pt sota la línia base.
(És prim 'l', no textDecoration — R4 ja implementat.)

═══════════════════════════════════════════════════════════════════
## HORITZONTAL — banda 784,7 × 70,4
═══════════════════════════════════════════════════════════════════

### Filets
- rect exterior: (0, 0) → (784,7, 70,4)
- divisors verticals interiors (y 0→70,4): x = 141,4 · 463,2 · 714,2
- cap línia doble: caixes comparteixen filet

### Caixes resultants
| caixa | x0    | x1    | ample | contingut                |
|-------|-------|-------|-------|--------------------------|
| C1    | 0     | 141,4 | 141,4 | logo + copyright         |
| C2    | 141,4 | 463,2 | 321,8 | nom/temporada+col/refs   |
| C3    | 463,2 | 714,2 | 251,0 | run + target             |
| C4    | 714,2 | 784,7 | 70,5  | data + pàgina (quadrada) |

### C1 · logo
- CAIXA DEL LOGO: x 7,0 · y 18,0 · w 126,0 · h 28,0
  Asset del client escalat CONTAIN dins la caixa, proporcions intactes,
  alineat esquerra, centrat vertical. REGLA: cap agent canvia mida/proporció.
- copyright (lbl): x 6,3 · y 60,9 · text "FHORT TEXTILE TECH © 2026"

### C2
| element                    | estil | x     | y    |
|----------------------------|-------|-------|------|
| lbl NOM DE LA PEÇA         | lbl   | 148,5 | 1,6  |
| valor nom peça             | v12   | 147,1 | 9,8  |
| lbl TEMPORADA              | lbl   | 148,7 | 28,2 |
| lbl COL·LECCIÓ             | lbl   | 198,0 | 28,2 |
| valor temporada            | v10   | 148,2 | 36,8 |
| valor col·lecció           | v10   | 197,2 | 36,8 |
| lbl REFERÈNCIA INTERNA     | lbl   | 148,9 | 49,4 |
| lbl REFERÈNCIA CLIENT      | lbl   | 240,3 | 49,4 |
| valor ref interna          | v10   | 148,5 | 57,7 |
| valor ref client           | v10   | 239,7 | 57,7 |

### C3
| element                                | estil | x     | y    |
|----------------------------------------|-------|-------|------|
| lbl RUN DE TALLES                      | lbl   | 473,4 | 1,6  |
| valor run (separador "·")              | v12   | 472,6 | 9,8  |
|   → talla activa dins del run          | cur   | (in-line) | |
| lbl TARGET \| FIT TYPE \| CONSTRUCTION | lbl   | 473,3 | 27,5 |
| valor target \| fit \| construction    | v10   | 472,7 | 34,8 |

### C4
| element        | estil | x     | y    | nota                        |
|----------------|-------|-------|------|-----------------------------|
| lbl DATA       | lbl   | 718,2 | 1,6  |                             |
| valor data     | v10   | 718,2 | 9,5  |                             |
| lbl PÀGINA     | lbl   | 718,2 | 23,3 |                             |
| valor format   | v10   | 718,2 | 31,2 | "A4" (format de pàgina real)|
| valor "i/n"    | v18   | 731,1 | 44,1 |                             |

═══════════════════════════════════════════════════════════════════
## VERTICAL — banda 535,7 × 92,8
═══════════════════════════════════════════════════════════════════

### Filets
- rect exterior: (0, 0) → (535,7, 92,8)
- divisor horitzontal (x 0→535,7): y = 22,2   ← UNA sola línia
- divisor vertical (y 22,2→92,8): x = 321,0
- tira superior = 0→22,2 · caixa esquerra = 0→321,0 · caixa dreta = 321,0→535,7

### Tira superior
| element        | estil | x     | y    | nota                                   |
|----------------|-------|-------|------|----------------------------------------|
| CAIXA LOGO     | —     | 6,5   | 5,5  | w 49,0 · h 11,0 (contain, esq., centrat v.) |
| lbl DATA       | lbl   | 242,8 | 1,3  |                                        |
| valor data     | v10   | 242,8 | 9,2  |                                        |
| lbl PÀGINA     | lbl   | 347,1 | 1,6  |                                        |
| valor format   | v10   | 347,1 | 9,6  |                                        |
| valor "i/n"    | v18   | 378,7 | 1,8  |                                        |
| copyright      | lbl   | 428,6 | 11,6 |                                        |

### Caixa esquerra (estructura idèntica a C2 horitzontal)
| element                | estil | x    | y    |
|------------------------|-------|------|------|
| lbl NOM DE LA PEÇA     | lbl   | 6,7  | 24,0 |
| valor nom peça         | v12   | 5,4  | 32,3 |
| lbl TEMPORADA          | lbl   | 6,9  | 50,6 |
| lbl COL·LECCIÓ         | lbl   | 56,2 | 50,6 |
| valor temporada        | v10   | 6,5  | 59,2 |
| valor col·lecció       | v10   | 55,5 | 59,2 |
| lbl REFERÈNCIA INTERNA | lbl   | 7,1  | 71,8 |
| lbl REFERÈNCIA CLIENT  | lbl   | 98,5 | 71,8 |
| valor ref interna      | v10   | 6,7  | 80,1 |
| valor ref client       | v10   | 97,9 | 80,1 |

### Caixa dreta
| element                                | estil | x     | y    |
|----------------------------------------|-------|-------|------|
| lbl RUN DE TALLES                      | lbl   | 331,1 | 24,0 |
| valor run                              | v12   | 330,4 | 32,3 |
| lbl TARGET \| FIT TYPE \| CONSTRUCTION | lbl   | 331,1 | 49,9 |
| valor target \| fit \| construction    | v10   | 330,5 | 57,2 |

═══════════════════════════════════════════════════════════════════
## REGLES TRANSVERSALS
- Etiquetes: pel diccionari `headerLabels(tr)` ja injectat (B5) — les d'aquí
  són la variant ca; en/es per les claus `hdr_label_*`.
- Camps FORA: TECHNICIAN · GARMENT TYPE|ITEM · SIZE SYSTEM (B4 fet).
- Anti-desbordament (R3): cos nominal → shrink fins a sòl 10pt → EL·LIPSI.
  Mai segona línia. El run mai s'el·lipsa: si no cap a 10pt, REPORTAR.
- Data = data d'emissió, format DD-MM-YYYY (R5). Pàgina "i/n" amb n total.
- Alçades de banda per al backend (R6): `_HDR_PT` horitzontal 70,4 ·
  vertical 92,8 + reseed idempotent + audita BD.
- Paritat: tota prim nova als 3 traductors (PrimNode · addPrimsToGroup ·
  materialitzaHeader) — gate explícit, precedent 218585f.

---

## Derivacions declarades (no són a la maqueta; les fixa la implementació)

La maqueta dona el punt d'ORIGEN de cada text, no el seu límit dret. L'anti-desbordament
(R3) el necessita, i per tant es deriva així — si algun dia la maqueta els declara, manen
els seus:

- **Marge contra la vora d'una caixa**: el mateix sagnat que té el text per l'esquerra
  dins d'aquella caixa (C2 7,1 · C3 10,2 · C4 4,0 · caixa dreta vertical 9,4).
- **Carrer entre dues columnes d'una mateixa fila** (temporada↔col·lecció,
  ref interna↔ref client, i els camps de la tira vertical): 6pt.
- **Posició de la banda dins la pàgina**: es conserva la de l'spec anterior
  (x 28,6 · y 39 pt), que la maqueta no torna a declarar.
- **Any del copyright**: es pren de la data d'EMISSIÓ, no del literal "2026" de la
  maqueta — coherent amb R5 (la fitxa es re-data a cada render).
