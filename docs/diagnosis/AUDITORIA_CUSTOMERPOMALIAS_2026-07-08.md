# AUDITORIA — CustomerPOMAlias migrats (0031/0032)

Data: **2026-07-08** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` · schema `fhort`
Abast: auditar els `CustomerPOMAlias` sembrats per les migracions `pom 0031` (Brownie) i `0032` (dotted), després que la validació visual de l'Agus detectés mapatges sospitosos a la fitxa del client (tab Tècnic). **Cap correcció de dades:** la decisió és humana (Agus + Montse per validar el mapatge correcte).
Convenció: `fitxer:línia`; `[id]` = pk de `POMMaster`; `"NO EXISTEIX"` = confirmat absent.

---

## Resum executiu

1. **Hi ha 8 àlies a `fhort`**: 6 de **BRW** (origen `MIGRACIO`, de `0031`) + 2 de **FTT** (dotted, de `0032`). Els 2 de FTT són **correctes per construcció**; el problema és tot a `0031`.
2. **Causa arrel (0031):** la migració resol el POM objectiu per `POMMaster.filter(nom_client__icontains=tgt | pom_global__nom_en__icontains=tgt).order_by('id').first()` (`0031:44-46`). Amb targets **genèrics** (`'lining'`, `'armhole'`) l'`icontains` casa múltiples POMs i `.first()` en tria el de **menor id** — es perd el matís front/back i curve/depth. És la mateixa **classe** de bug prefix/substring→target-erroni que el cas SH DR ja registrat a `DIAGNOSI_RUN_CLIENT_VINCULACIO_2026-07-08.md:170`.
3. **1 error DUR confirmat:** `'lining length at center front'` → `[383] Lining Length at Center **Back**`. El POM correcte **existeix**: `[429] Lining Length at Center **Front** (codi LF-M76)`. A més **col·lisiona**: `front` i `back` apunten al MATEIX `[383]`.
4. **1 error PROBABLE, correcció no òbvia:** `'front armhole curve'` → `[284] Armhole **depth**` (curve ≠ depth). **NO EXISTEIX** cap POM "Armhole curve" al catàleg; només `[284] Armhole depth` i `[285] Armhole circumference`. Quin és el correcte és **decisió de domini (Montse)**.
5. La resta de BRW (`collar width`, `body zip length`, `lining bottom width along hem`, `lining length at center back`) són **plausiblement correctes** (vegeu bloc 2).
6. **Cap fila esborrada ni corregida.** Aquesta auditoria només documenta; la reparació va a un sprint propi amb el mapatge validat.

---

## BLOC 1 — Inventari complet dels 8 àlies (schema fhort)

| id | customer | client_code | → POM | pom_codi | origen | veredicte |
|---|---|---|---|---|---|---|
| — | BRW | `body zip length` | `[341]` Zipper length | ZIP L | MIGRACIO | ✅ plausible (únic POM 'zip') |
| — | BRW | `collar width` | `[382]` Collar Width (Neck Tie Length) | — | MIGRACIO | ✅ remap BRW deliberat |
| — | BRW | `front armhole curve` | `[284]` Armhole depth | AH DEP | MIGRACIO | ⚠️ **PROBABLE ERROR** (curve≠depth; sense "curve" al catàleg) |
| — | BRW | `lining bottom width along hem` | `[384]` Lining Bottom Width Along Hem | — | MIGRACIO | ✅ exacte |
| — | BRW | `lining length at center back` | `[383]` Lining Length at Center Back | 1-M76 | MIGRACIO | ✅ exacte |
| — | BRW | `lining length at center front` | `[383]` Lining Length at Center **Back** | 1-M76 | MIGRACIO | ❌ **ERROR DUR** (hauria de ser `[429]` LF-M76) |
| — | FTT | `T.1` | `[434]` FRONT RISE | — | MIGRACIO | ✅ identitat (dotted) |
| — | FTT | `T.2` | `[435]` BACK RISE | — | MIGRACIO | ✅ identitat (dotted) |

*(les `id` d'àlies s'ometen: són volàtils; la clau funcional és `(customer, client_code)`.)*

**Veredicte 1:** 2 àlies problemàtics dels 8 (tots dos BRW/0031). Els 6 restants correctes o plausibles.

---

## BLOC 2 — Detecció (a) col·lisions i (b) front/back invertit

**(a) Dos àlies del mateix customer → mateix POM:**
- **BRW → `[383]` Lining Length at Center Back** rep DOS àlies: `lining length at center back` (correcte) **i** `lining length at center front` (incorrecte). Únic cas de col·lisió.

**(b) Text `front`/`back` amb POM contrari:**
- **`'lining length at center front'` → `'Lining Length at Center Back'`** ⚠️ — inversió front→back confirmada.

**(c) Extra `curve`/`depth`:**
- **`'front armhole curve'` → `'Armhole depth'`** ⚠️ — divergència de mesura (curve vs depth).

**Per què (0031):** `BROWNIE_ALIASES` (`0031:17-27`) mapeja el codi Brownie a una **descripció canònica objectiu**, i el forward la resol amb `icontains` + `.first()` per id:
- `'lining length at center front': 'lining'` i `'lining length at center back': 'lining'` (`0031:24-25`) → tots dos busquen `icontains('lining')` → el de menor id és `[383]` (Back) → **col·lisió + inversió**.
- `'front armhole curve': 'armhole'` (`0031:21`) → `icontains('armhole')` → menor id `[284]` (depth) en comptes de `[285]` (circumference) o de cap "curve".

---

## BLOC 3 — Comprovació al catàleg (existeix el POM correcte?)

- `POMMaster` amb `'lining length at center'`: `[383]` Center **Back** (1-M76) **i** `[429]` Center **Front** (LF-M76). → El correcte per `front` **EXISTEIX** (`[429]`). Correcció DUR coneguda.
- `POMMaster` amb `'armhole'`: `[284]` Armhole **depth** (AH DEP), `[285]` Armhole **circumference** (AH CIRC). **NO EXISTEIX** "Armhole **curve**". → Correcció NO òbvia; candidats depth/circumference/altre → **cal Montse**.
- `POMMaster` amb `'zip'`: només `[341]` Zipper length. → `body zip length`→`[341]` és **inequívoc** (no hi ha alternativa).

**Veredicte 3:** l'error de lining té correcció determinista (`[429]`); l'armhole no — depèn del significat de la nomenclatura Brownie "front armhole curve".

---

## BLOC 4 — `0032` (dotted) — per què NO és sospitós

`0032` (`0032_...py:58-61`) crea `client_code = pom.codi_client` → `pom_id = pom.id` (el POM del qual s'ha llegit el codi). És una **identitat**: l'àlies apunta al seu propi POM d'origen; no hi ha resolució per similitud → **cap col·lisió possible**. Els 2 àlies FTT (`T.1`→FRONT RISE, `T.2`→BACK RISE) ho confirmen. `codi_client` no es toca (`0032:4`).

**Veredicte 4:** `0032` correcte; **no** requereix revisió.

---

## TAULA FINAL — accions per a l'Agus (decisió humana)

| # | Àlies (BRW) | Estat | Correcció | Qui decideix |
|---|---|---|---|---|
| A1 | `lining length at center front` → `[383]` Back | ❌ ERROR DUR + col·lisió | re-apuntar a `[429]` LF-M76 (Center Front) | Agus (determinista) |
| A2 | `front armhole curve` → `[284]` depth | ⚠️ PROBABLE ERROR | mapatge correcte desconegut (no hi ha "curve") | **Montse** valida → Agus executa |
| A3 | `body zip length` → `[341]` Zipper length | ✅ plausible | cap (únic POM 'zip') | — |
| A4 | `collar width`, `lining bottom width along hem`, `lining length at center back` | ✅ correctes | cap | — |
| R1 | Arrel `0031:44-46` (`icontains`+`.first()` per id) | ⚠️ patró lossy | si es re-sembra en el futur: match exacte/per code, no substring genèric | Agus (fase reparació) |

**Nota:** aquesta auditoria **no** ha esborrat ni modificat cap `CustomerPOMAlias` (SELECT read-only). La reparació de A1/A2 és un sprint propi; A2 bloquejat fins a validació de la Montse. La UI de la fitxa (P4) ja permet editar/esborrar àlies manualment (gate CONFIGURE) quan es decideixi el mapatge.
