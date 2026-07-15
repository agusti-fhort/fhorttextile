# REPORT — QA-TALLER-A: fix `puntsDelSegment`

Data: 2026-07-15 · **Patró B (IMPLEMENTACIÓ)** · staging `/var/www/ftt-staging`, branca `dev`
Mana: `DIAGNOSI_TRAM_EXPANSIO.md` · Territori: `patternGeometry.js` + tokens de color del Taller

**Estat: 3 peces VERDES, 3 commits locals, CAP push.**

| peça | commit | estat |
|---|---|---|
| T1 · epsilon | `efa28d2` | ✅ verd |
| T2 · envolta + consolidació | `b58bdda` | ✅ verd |
| T3 · color (disseny) | `8cc9f0c` | ✅ verd |

**Coordinació:** verificat abans de començar — cap canvi pendent sobre `TallerPatro.jsx` ni
components de pinça, i cap commit nou des de `4d90db7`. La sessió B no estava escrivint. Aquest
fix entra ABANS que B construeixi els composts, com demanava el brief.

---

## T1 — EPSILON

`patternGeometry.js:189-195` — els epsilons del test de pertinença tenien el signe girat:
eixamplaven el rang (`t_inici - 1e-9`) en comptes d'estrènyer-lo. Com que `t_inici` és
`cum[i]/total` —exactament la frontera entre dues arestes—, l'aresta veïna que només TOCA el tram
hi entrava sempre.

**Test numèric sobre els 4 trams declarats reals del tenant `fhort`** (banc que executa les
funcions REALS del repo sobre la geometria exportada de la BD):

| seg | peça | veritat | abans pintava | ara pinta | error |
|---|---|---|---|---|---|
| 290 | TATE_BACK | 29,80 cm | 30,02 | **29,80** | **0,00** ✅ |
| 291 | TATE_FRONT | 32,13 cm | 33,14 | **32,13** | **0,00** ✅ |
| 314 | TATE_FACING_YOKE | 4,01 cm | 13,02 (3,2×) | **4,01** | **0,00** ✅ |
| 315 | TATE_FRONT_FACING | 3,98 cm | 13,53 | **3,98** | **0,00** ✅ |

## T2 — ENVOLTA (consolidat, no pedaç)

`patternGeometry.js:178-203` — la selecció d'arestes ja era bona; l'ORDRE d'emissió no. S'emetien
per índex de polilínia, així que el bocí `[0, t_fi]` sortia abans que el `[t_inici, 1]`: la línia
tornava enrere a mig traç i pintava una diagonal per dins de la peça. Ara les arestes se
seleccionen a part i s'emeten en l'ordre en què es caminen.

**Banc 5/5** (llargada **i** ordre de punts):

| cas | esperat | resultat |
|---|---|---|
| simple v4→v8 | 100 mm · `q0→q1→q2→q3→r0` | ✅ |
| aresta única v4→v5 | 25 mm · `q0→q1` | ✅ |
| **ENVOLTA origen v14→v2** | 100 mm · `s2→s3→p0→p1→p2` | ✅ (abans: 130,9 mm i traç creuat) |
| mig contorn v0→v8 | 200 mm | ✅ |
| vora OBERTA v1→v3 | 50 mm · `p1→p2→p3` | ✅ |

## T3 — COLOR (decisió del CTO, Patró C)

**Blau = identitat del tram · taronja = assenyalar.** El gest en curs (prèvia + arcs fixats) es
pinta ara del color del tram; el que diu "això encara no és del patró" és l'èmfasi (discontinu,
translúcid), i en desar-se el traç només es solidifica. El taronja es queda on sí que és èmfasi i
no identitat: el tram assenyalat des de la llista i l'ombra de reobrir.

Els dos colors deixen de ser hexs forasters: ara són tokens del design system (`--tram`,
`--tram-sel` a `index.css:37-43`), amb `KONVA_COL` (`PatternViewer.jsx:29-51`) declarat com el seu
mirall — Konva no resol `var()`, però ara es veu d'on surt el valor.

---

## Superfícies curades

Les 5 que comparteixen `puntsDelSegment`, totes amb el mateix fix:

| superfície | crida | estat |
|---|---|---|
| Trams desats al canvas | `PatternViewer.jsx:423` | ✅ verificat en viu a staging |
| **Cosir · ressaltat A/B** | `PatternViewer.jsx:423` (mateix `map`, canvia el `stroke`) | ✅ curat |
| Cosir · propostes sota el cursor | `PatternViewer.jsx:499` | ✅ curat |
| **Costats de pinça + àpex** | `TallerPatro.jsx:856` / `:864` | ✅ verificat (sota) |
| Ombra de reobrir | `TallerPatro.jsx:622` | ✅ curat |

### La pinça: el latent que la diagnosi havia marcat era REAL

Simulada sobre geometria real (TATE_FACING_YOKE, vora 1, tres girs consecutius), amb la lògica
calcada de `TallerPatro.jsx:856-864`. Prova amb dents: executada també contra el codi d'abans.

| | abans (`4d90db7`) | ara |
|---|---|---|
| àpex | punt **1467** ❌ (un vèrtex de més) | punt **1466** ✅ |
| costat 1 (motor 122,70 mm) | 128,34 mm ❌ | **122,70** ✅ |
| costat 2 (motor 15,45 mm) | 139,06 mm ❌ (9×) | **15,45** ✅ |
| els dos costats es toquen a l'àpex | ❌ | ✅ |

## Funcions que recorren per ÍNDEX en lloc de per `t` (T2 · consolidació)

El patró té **4 ocurrències vives**. Una curada; **3 queden, i totes són al motor de patrons —
fora del territori d'aquest sprint (zona intocable del `CLAUDE.md`), per tant NO tocades**:

| # | fitxer:línia | què passa | trenca? |
|---|---|---|---|
| 1 | `patternGeometry.js:181-196` | el defecte d'aquest sprint | ✅ **CURAT (T2)** |
| 2 | **`engine/operations.py:717-738` `_indexs_del_rang`** | ⚠️ **el risc gros, i NO és el tram que envolta**: converteix `(t_inici,t_fi)` a índexs buscant coincidència exacta amb els trams que `segmentar_vora` deriva (gir→gir). Un tram DECLARAT al taller no hi és MAI. Cadena: `adapters.py:608` → `SewSpec.costat_a` → `operations.py:681 _longitud_tram` → `MeasureError` → `_revalidar_costures` (`:665-697`) l'empassa i emet `costura_no_mesurable`. **Cap costura declarada al taller (W1-W4b) no es pot revalidar en una operació de moviment**, i el motor ho reporta com si el patró hagués canviat de versió — un diagnòstic FALS. | **SÍ** |
| 3 | `engine/operations.py:741-758` `_longitud_indexs` | camina amb `(i+1) % n` però **no rep `closed`**: amb vora oberta i `i0 > i1` recorreria l'aresta de tancament fantasma. Avui inabastable perquè el #2 el protegeix per accident — **si es corregeix el #2, la protecció desapareix**. | latent |
| 4 | `engine/dart_detection.py:133-135` `_arc` | `pts[i:j+1] if i <= j else pts[i:] + pts[:j+1]`, **sense `closed`**; `detectar` (`:247-248`) genera ternes amb `girs[(k+1) % n]` (dona la volta sempre) → sobre vora OBERTA cus l'aresta inexistent → costat inflat → pinça fantasma. Amb l'AMELIA (contorns tancats) no es veu. | **SÍ, amb vora oberta** |

**Recomanació** `💡 (a validar)`: el #2 mereix peça pròpia i és més gros que aquest sprint — la
funció hauria de morir i deixar pas a `longitud_tram(boundary_nou, t_inici, t_fi)` directament: les
operacions no creen ni destrueixen vèrtexs, i el `t` ja és el contracte. Fer el #2 obliga a fer el
#3 alhora.

Nota de consolidació: `patternGeometry.js:315-322` `puntsEntreIndexs` **ja emetia per recorregut** —
la funció bona vivia al costat de la dolenta. Ara les dues diuen el mateix.

---

## VERD

| control | resultat |
|---|---|
| `npx eslint` (fitxers tocats) | **0 errors** (3 avisos, tots preexistents: verificat idèntics a `4d90db7`) |
| `npm run build` | ✅ net |
| Banc: 4 trams reals | ✅ 4/4 error 0,00 |
| Banc: 5 casos sintètics | ✅ 5/5 (llargada i ordre) |
| Pinça: àpex + costats + frontissa | ✅ (i la prova falla contra el codi vell) |
| **Guionitzat al navegador (staging viu)** | ✅ parcial — vegeu sota |

### Guionitzat (Playwright contra `staging.fhorttextile.tech`, model 163 / TATE.DXF)

- **Els 4 trams desats al canvas real**: `29.8 · 32.1 · 4 · 4` cm, tots `#0969da`. Coincideixen amb
  la veritat del motor (29,80 · 32,13 · 4,01 · 3,98). **Abans: 30,02 · 33,14 · 13,02 · 13,53.** ✅
- **Definir un tram curt**: gest complet amb l'imant (punt A clicat, cursor a B). La prèvia es pinta
  `#0969da` **blau**, discontínua, opacitat 0,85, **1,55 cm**; l'etiqueta "1.5 cm" també blava. El
  motor diu 15,45 mm per aquest mateix costat, i el banc mesura el seu render desat a 15,45 mm:
  **prèvia i desat, la mateixa llargada i el mateix color**. ✅

**El que NO s'ha fet, i per què:** no s'ha completat el `create` del tram ni s'ha declarat una pinça
al navegador, perquè **hauria escrit dades de prova al tenant `fhort`** (un 5è tram declarat i una
`SewRelation` nova sobre el patró del model 163) i el brief no autoritzava crear dades. La cadena
que quedava per observar (`create` → refresc → render) **no la toca aquest fix**: el rang que
viatja és el mateix d'abans (la diagnosi ja el va declarar net), i el render d'arribada és el que
s'ha mesurat als 4 trams reals i a la pinça simulada. Si vols l'observació literal, cal el vistiplau
per crear i esborrar les dues files de prova.

---

## Per al CTO

1. **Revisar la cadena:** `git show efa28d2 b58bdda 8cc9f0c` · **el push el fas tu des d'SSH**.
2. **⚠️ El `dist/` de staging ja porta el fix**: `npm run build` (el gate del mètode) escriu a
   `frontend/dist`, que és el que nginx serveix (`/etc/nginx/sites-enabled/ftt-staging:18`). O sigui
   que `staging.fhorttextile.tech` **ja pinta els trams bé** — sense push i sense deploy. El codi
   font viu només en commits locals.
3. **Decidir sobre `operations.py:717`** (#2 de la taula): és més gros que un dibuix i menteix en
   silenci.

## Anotat, fora de scope (no tocat)

- `SegmentEditor.jsx` no ensenya el blau enlloc: la llista de trams no lliga amb el canvas, a
  diferència de `SewEditor` amb `sewA`/`sewB`. Cap llegenda de colors al Taller.
- `KONVA_COL.hover` (`#c27a2a`, `PatternViewer.jsx:41`) continua sent **constant morta** (0 usos).
- `frontend/` **no té cap prova** (ni `test` al `package.json` ni cap `*.test.*`): el banc d'aquest
  sprint viu al scratchpad, no al repo. La funció més geomètrica del Taller segueix sense xarxa.
  `💡 PROPOSTA (a validar)`: muntar Vitest i entrar-hi els 5 casos + els 4 trams reals.
- Els 3 avisos d'eslint de `PatternViewer.jsx` (fast-refresh a `:29`, refs durant el render a
  `:262`) són deute previ.
