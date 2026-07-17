# DIAGNOSI — «Nou run de client» (size-map) no ingereix l'Excel de bases

Data: **2026-07-17** · **Patró A (READ-ONLY)** · staging `dev`, tenant `fhort`. Cap escriptura de codi.
Símptoma (PROD, captures Agus): amb l'Excel de bases de la Blusa POP (21 POMs en absoluts, codis Brownie
A/D/E2/EK/SF…) el camí size-map retorna **«No s'han trobat POMs al fitxer»** tot i que el diccionari BRW
(94 àlies) hi és.

> `fitxer:línia` = fet verificat. `NO EXISTEIX` = confirmat absent.

## Causa exacta (confirmada amb el fixture real)

**El camí size-map i el de l'ImportWizard fan servir DOS extractors d'Excel DIFERENTS**, i el del
size-map és un parser **posicional rígid** que no encaixa amb el format real de la fitxa Brownie.

- **size-map** (`sizeMap.gradingPreviewFile` → `size_map_grading_preview_file_view`,
  `pom/size_map_views.py:437`): per a Excel crida **`_parse_grading_excel`** (`size_map_views.py:361`),
  que assumeix **capçalera a la fila 1, A=codi, B=descripció, C endavant=talles** (`:376-379`). Sense
  ancoratge per contingut, sense mapa per etiqueta, i **sense fallback a IA per a Excel** (el fallback
  `extract_from_file` només s'usa a la branca PDF/imatge, `:487-489`).
- **ImportWizard / fitxa de model** (`extraction_views.py:1100`): crida **`_parse_excel_poms`**
  (`extraction_views.py:232`), que **ancora la capçalera pel CONTINGUT** (una fila amb etiqueta de CODI
  `_ETIQ_CODI` *i* de DESCRIPCIÓ `_ETIQ_DESC`, a la columna que sigui, `:277-287`), **mapa les talles per
  etiqueta** (`_RE_TALLA`, `:326-330`), llegeix el `SAMPLE SIZE` del bloc de metadades (`:340-346`), i
  **abdica a la IA** si no pot demostrar que ha entès la taula (`:240-255`). Té bateria de tests contra
  els fixtures Brownie (`models_app/test_parser_excel.py`).

**Estructura REAL de la fitxa Brownie** (fixture `brownie_rosalia_spec_sheet.xlsx`, llegit):

| fila | col A (0) | col B (1) | col C (2) | col D (3) | col E+ (4+) |
|---|---|---|---|---|---|
| 0 | — | — | — | — | — |
| 1-6 | — | DATE/BRAND/…/**SAMPLE SIZE** | valors metadada | — | — |
| **8** | — | **CODE** | **DESCRIPTION** | GRADING | **XXS · XS · S · M …** |
| 11+ | — | **A** | 1/2 chest width | — | valors per talla |

Aplicant-hi `_parse_grading_excel`:
- `header = rows[0]` = tot buit → `size_cols` (columnes i≥2 amb capçalera no buida) = **[]**.
- Amb `size_cols` buit, cada fila té `values = {}` → **cap POM s'afegeix mai** (`size_map_views.py:388-394`).
- `poms_in = []` → es dispara **«No s'han trobat POMs al fitxer»** (`size_map_views.py:513-514`).

**Totes** les premisses posicionals del parser rígid són falses per a la fitxa Brownie: columna A buida
(el codi és a B), bloc de metadades de 6 files a sobre, capçalera real a la fila 8, talles a partir de E.

## Resposta a les 3 preguntes

1. **Mateix extractor o dos?** → **DOS de diferents.** size-map = `_parse_grading_excel` (posicional
   rígid, 1 sol lloc d'ús, `size_map_views.py:474`); import = `_parse_excel_poms` (ancorat per contingut
   + abdicació a IA).
2. **Per què no reconeix els codis que l'import sí?** → **No és un problema de codis ni de diccionari:**
   el parser del size-map **no extreu cap fila** (llegeix la fila 1 com a capçalera —buida— i espera
   codi/desc/talles a A/B/C+). Retorna 0 POMs **abans** d'arribar al matching. El diccionari de client
   **SÍ està cablejat** en aquest camí (`_resolve_run_customer` `:38` → `find_pom_master(codi, descripcio,
   customer=customer)` `:542`), però **mai s'hi arriba**.
3. **(a) Excel dolent / (b) extractor incomplet / (c) no passa pel diccionari?** → **(b).** L'Excel és el
   MATEIX format que l'ImportWizard ingereix bé a staging; el diccionari SÍ hi és al camí. El defecte és
   que **l'extractor del size-map és rígid/incomplet** (capçalera-fila-1, columnes fixes A/B/C+, sense
   ancoratge per contingut ni fallback a IA per a Excel).

## Opcions de fix (NO implementades)

- **Opció 1 — UNIFICAR (recomanada, tanca el fork-deute).** Fer que la branca Excel del size-map passi
  per **`_parse_excel_poms`** (l'extractor robust de l'import) en comptes de `_parse_grading_excel`,
  reaprofitant tota la canonada de baix del size-map (re-clau al run del tenant `:526-533`,
  `find_pom_master` amb customer `:542`, derivació de grading). Esquemes compatibles: `_parse_excel_poms`
  retorna `(poms, talles, meta)` amb camps de més (`dim`, `tol_*`) però el size-map només consumeix
  `{codi_fitxa, descripcio, values}`. Passar-li `base_hint`=base_size i `run_hint`=tenant_run (ja
  disponibles, `:465-472`). `_parse_grading_excel` queda orfe (1 sol ús) → es pot jubilar. Hereta els
  tests del fixture Brownie i l'abdicació a IA «de franc».
- **Opció 2 — Excel→IA de reserva al size-map.** Si `_parse_grading_excel` torna buit, caure a
  `extract_from_file` (com la branca PDF). Parcial: emmascara el forat del parser i crema IA per a un
  Excel que es pot llegir de manera determinista. No unifica.
- **Opció 3 — fer robust `_parse_grading_excel`** (ancoratge per contingut, saltar col A buida, talles
  per etiqueta). **Desaconsellada:** DUPLICA la lògica que ja viu, provada, a `_parse_excel_poms` →
  nou fork divergent (exactament el que s'ha d'evitar).

**Recomanació:** Opció 1. És un canvi acotat a la branca Excel de `size_map_grading_preview_file_view`
(substituir la crida a `_parse_grading_excel` per `_parse_excel_poms` + adaptar l'esquema de sortida),
sense tocar el matching, el re-clau ni la derivació de grading.
