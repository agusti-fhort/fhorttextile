# AUDITORIA COMPLETA — CustomerPOMAlias (tota la població)

Data: **2026-07-08** · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` · schema `fhort`
Abast: enumerar **tota** la població de `CustomerPOMAlias` (no una mostra) i marcar cada fila després que `AUDITORIA_CUSTOMERPOMALIAS_2026-07-08.md` trobés l'arrel: `pom 0031` resol el POM amb `icontains(target)` + `.order_by('id').first()` (`0031:44-46`) amb targets genèrics. **Cap escriptura de dades** (SELECT read-only); la correcció serà una migració idempotent decidida per l'Agus (validada per la Montse on calgui).
Convenció: `[id]` = pk de `POMMaster`; `fitxer:línia`; `"NO EXISTEIX"` = confirmat absent al catàleg. Aquest doc **supera la mostra** del doc parcial germà (que segueix vàlid com a primer cribratge).

---

## Resum executiu

1. **Població TOTAL = 8 àlies, en 1 sol tenant (`fhort`)**: BRW 6 (origen `MIGRACIO`, de `0031`) + FTT 2 (dotted, de `0032`). **NO EXISTEIX** cap altre schema tenant amb àlies → aquesta és tota la població, no una mostra.
2. **Recompte per veredicte: OK 5 · SOSPITÓS 1 · ERROR CONFIRMAT 2.**
3. **2 ERROR CONFIRMAT** (contradicció direccional codi↔POM):
   - `lining length at center **front**` → `[383]` Center **Back** — **correcció DETERMINISTA**: `[429]` Lining Length at Center Front (LF-M76). Existeix nom exacte.
   - `front armhole **curve**` → `[284]` Armhole **depth** — **NO determinista**: no hi ha "Armhole curve" al catàleg; candidats `[284]` depth / `[285]` circumference → **decisió Montse**.
4. **1 SOSPITÓS per construcció, correcte per atzar**: `lining length at center back` → `[383]`. El target genèric `'lining'` casa **3 POMs** i `0031` va triar el de menor id `[383]`, que resulta ser el correcte. No cal corregir-lo, però el mecanisme era lossy.
5. **1 col·lisió**: BRW → `[383]` rep DOS àlies (`front` erroni + `back` correcte). Es resol sol quan es corregeixi A1.
6. **`0032` (dotted) NET a tota la població**: 0 àlies dotted amb `pom.codi_client != client_code` (mapa identitat íntegre). No requereix cap acció.

---

## BLOC 1 — Taula completa de la població (8/8)

Columna `#match` = quants POMs actius casa el target de `0031` via `icontains` (nom_client ∪ pom_global.nom_en). `>1` ⇒ sospitós per construcció (es va triar el de menor id).

| customer | client_code | POM actual | target 0031 | #match | veredicte | correcció proposada |
|---|---|---|---|---|---|---|
| BRW | `body zip length` | `[341]` Zipper length (ZIP L) | `zip` | 1 | ✅ OK | — |
| BRW | `collar width` | `[382]` Collar Width (Neck Tie Length) (S1-M76) | `neck tie length` | 1 | ✅ OK | — |
| BRW | `front armhole curve` | `[284]` Armhole depth (AH DEP) | `armhole` | **2** `[284]`depth · `[285]`circ | ❌ **ERROR** (curve≠depth) | **no determinista** → Montse (`[284]`/`[285]`) |
| BRW | `lining bottom width along hem` | `[384]` Lining Bottom Width Along Hem (F1-M76) | `lining bottom` | 1 | ✅ OK (exacte) | — |
| BRW | `lining length at center back` | `[383]` Lining Length at Center Back (1-M76) | `lining` | **3** `[383]`·`[384]`·`[429]` | ⚠️ SOSPITÓS (correcte per atzar) | — (ja correcte) |
| BRW | `lining length at center front` | `[383]` Lining Length at Center **Back** (1-M76) | `lining` | **3** `[383]`·`[384]`·`[429]` | ❌ **ERROR** (front≠back) + col·lisió | **✎ `[429]`** Lining Length at Center Front (LF-M76) — DETERMINISTA |
| FTT | `T.1` | `[434]` FRONT RISE | — (0032 identitat) | — | ✅ OK | — |
| FTT | `T.2` | `[435]` BACK RISE | — (0032 identitat) | — | ✅ OK | — |

**Veredicte 1:** de 8, en calen corregir 2 (A1 determinista, A2 via Montse); 1 sospitós ja correcte; 5 nets.

---

## BLOC 2 — ERROR CONFIRMAT (contradicció direccional)

Detecció automàtica de parells antònims (front/back, curve/depth, curve/circumference, top/bottom, inner/outer, left/right, upper/lower, high/low, inside/outside): quan el `client_code` conté un pol i el nom del POM el pol contrari (i no el propi).

**E1 — `lining length at center front` → `[383]` Lining Length at Center Back** (`front!=back`):
- Causa: target `'lining'` (`0031:24`) casa `[383]` (Back), `[384]` (Bottom), `[429]` (Front); `.first()` per id → `[383]`.
- **Correcció DETERMINISTA:** existeix nom EXACTE `[429]` "Lining Length at Center Front" (codi `LF-M76`). 💡 PROPOSTA: re-apuntar l'àlies a `pom_id=429`.

**E2 — `front armhole curve` → `[284]` Armhole depth** (`curve!=depth`):
- Causa: target `'armhole'` (`0031:21`) casa `[284]` depth i `[285]` circumference; `.first()` per id → `[284]`.
- **NO EXISTEIX** cap POM "Armhole curve" al catàleg. Correcció **no determinista**: candidats `[284]` Armhole depth (AH DEP) o `[285]` Armhole circumference (AH CIRC), o cap. 💡 PROPOSTA: **bloquejar fins a validació de la Montse** (què significa "front armhole curve" en la nomenclatura Brownie).

**Veredicte 2:** E1 corregible sense ambigüitat; E2 requereix decisió de domini.

---

## BLOC 3 — SOSPITÓS (lossy però correcte)

**S1 — `lining length at center back` → `[383]`**: el target `'lining'` casa 3 POMs; `0031` va triar el de menor id `[383]`, que **casualment** és el correcte (Center Back). No hi ha res a corregir, però il·lustra la fragilitat del mecanisme: si `[383]` hagués tingut id superior a un altre "lining", també hauria fallat. Marcat SOSPITÓS **per construcció**, no per estat.

**Veredicte 3:** sense acció; testimoni de l'arrel.

---

## BLOC 4 — Col·lisions (dos àlies del mateix customer → mateix POM)

- **BRW → `[383]`** rep `lining length at center back` (correcte) **i** `lining length at center front` (E1, erroni). Única col·lisió de la població. **Es dissol automàticament** en aplicar la correcció E1 (`front` → `[429]`).

**Veredicte 4:** 1 col·lisió, conseqüència d'E1; no requereix acció pròpia.

---

## BLOC 5 — `0032` (dotted) i completesa de població

- **`0032` NET:** dels àlies dotted (`T.1`, `T.2`), 0 tenen `pom.codi_client != client_code`. És un mapa **identitat** (`0032:58-61`: `client_code = pom.codi_client → pom_id = pom.id`) → cap resolució per similitud, cap col·lisió possible. `T.1`→FRONT RISE, `T.2`→BACK RISE (el `front`/`back` viu al **nom** del POM, no al codi dotted → la detecció direccional no aplica: el codi `T.1` no afirma cap direcció).
- **Completesa:** enumerats tots els schemas tenant via `get_tenant_model()`; **només existeix `fhort`**. Els 8 àlies auditats són el 100% de la població. Si en el futur s'afegeixen tenants amb dades BRW, caldrà repetir aquesta auditoria al seu schema.

**Veredicte 5:** `0032` correcte; població coberta al 100%.

---

## TAULA FINAL — accions (decisió humana; correcció = migració idempotent)

| # | Àlies (customer) | Veredicte | Correcció proposada | Determinista? | Qui decideix |
|---|---|---|---|---|---|
| A1 | `lining length at center front` (BRW) | ❌ ERROR + col·lisió | `pom_id` → **429** (LF-M76) | **SÍ** | Agus |
| A2 | `front armhole curve` (BRW) | ❌ ERROR | `[284]` depth / `[285]` circ / altre | **NO** | **Montse** → Agus |
| S1 | `lining length at center back` (BRW) | ⚠️ SOSPITÓS | cap (ja correcte) | — | — |
| — | `body zip length`, `collar width`, `lining bottom width along hem` (BRW) | ✅ OK | cap | — | — |
| — | `T.1`, `T.2` (FTT) | ✅ OK (0032 identitat) | cap | — | — |
| R1 | Arrel `0031:44-46` (`icontains`+`.first()` per id) | ⚠️ patró lossy | futura re-sembra: match exacte/per code, no substring genèric | — | Agus (reparació) |

💡 **PROPOSTA (a validar) — forma de la reparació:** migració de dades **idempotent** que, per `(customer, client_code)`, faci `update_or_create` del `pom_id` correcte NOMÉS per a A1 (determinista) i deixi A2 fora fins a la decisió de la Montse. Idempotent = re-executable sense duplicar ni sobreescriure correccions manuals ja fetes des de la UI (gate CONFIGURE, fitxa P4). **Cap fila s'ha tocat en aquesta auditoria.**

### Nota de mètode
Patró A read-only estricte: cap escriptura de dades, cap migració, cap commit de codi. L'única escriptura és aquest document. Les `💡 PROPOSTA` i la columna de correcció són material per a la decisió humana (Patró C), no fets executats.
