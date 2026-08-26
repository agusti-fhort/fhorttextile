# Veredicte · els 4 vermells de `fhort.patterns` (gate de tren) — 2026-08-26

1. **El canari té SEGELL CADUCAT, no regressió.** El segell es va mesurar el 30/07
   (`2b4132c9`) i el writer va canviar deliberadament el 24/08; cap segell no el va seguir.
2. **Adjudicat per DIFF, no per intuïció:** l'arbre a `32ef5eb2^` reprodueix el segell VELL
   byte a byte, i del vell a l'actual hi ha 10.301 línies a banda i banda amb **100 valors
   diferents: 98 de codi de grup 1** (contingut de TEXT — el número de regla, +1 exacte) i
   **2 de codi 1000** (segell d'ezdxf, que `empremta_dxf` ja neutralitza). **Zero codis de
   coordenada tocats, cens d'entitats idèntic → 100 % [ESPERAT], 0 [REGRESSIÓ].**
3. **El fix del desplegat (`3b7e4841`) hi aporta ZERO bytes, mesurat:** amb l'`aama_reader`
   revertit el sha no es mou. Concorda amb la premissa d'identitat, que també s'ha verificat
   —`test_cap_peca_de_lamelia_no_te_doblec` passa: l'AMELIA no té cap peça amb doblec.
4. **Re-segellat** a `5f9a7aa7…` amb nota al fixture (per què, quan, contra quins commits).
   La validesa EXTERNA no la dona aquest test: la dona la paritat PolyPattern del 24/08, i
   **el gate de niada segueix PENDENT**.
5. **Els 3 de paperassa actualitzats a la llei vigent, sense afluixar cap assert** (se n'hi
   ha AFEGIT): `projeccio` al vocabulari (`3f81313c`) i la regla de repòs per `REGLA_ZERO`
   en comptes del literal `0` (`32ef5eb2`), amb un `assertNotIn(0, …)` nou que hauria caçat
   sol aquesta caducitat.

---

## Detall de la classificació (canari)

| delta | n | codi de grup | classe |
|---|---:|---|---|
| número de regla, +1 exacte (TEXT, capes 2/8/4) | 98 | 1 | **[ESPERAT]** · `32ef5eb2` numeració des d'1 · `d8b80458` el número viatja a les capes |
| segell d'ezdxf | 2 | 1000 | neutralitzat per `empremta_dxf` — no és delta |
| coordenades de punts | **0** | 10/20/11/21/40… | — |
| ordre de punts / cens d'entitats | **0** | — | cens idèntic, 10.301 = 10.301 línies |

Al RUL, els mateixos dos canvis deliberats, explícits: capçalera ara sencera
(`version ANSI/AAMA-292-B`, `AUTHOR:`, `GRADE RULE TABLE:`) i `DELTA 0/1/2` → `DELTA 1/2/3`
amb **els valors de delta idèntics**.

## Reproduïbilitat

Worktree `gate-4-vermells` (`/var/www/ftt-gate`). Els tres artefactes del diff es van
generar amb el mateix arbre i la mateixa BD (`test_ftt_gate`, `--keepdb`), revertint només
els fitxers de cada commit:

| variant | arbre | sha del DXF |
|---|---|---|
| A · pre-writer | `32ef5eb2^` (5 fitxers + `tests.py`) | `a87451a2…` = **el segell vell** |
| B · writer sí, motor no | dev amb `aama_reader.py` a `3b7e4841^` | `5f9a7aa7…` |
| C · dev actual | dev | `5f9a7aa7…` = **el segell nou** |

A≠C i B=C ⇒ tot el delta és del writer (24/08) i cap del motor (25/08).
