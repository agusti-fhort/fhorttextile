> ⚠️ SUPERADA 2026-07-13 — implementada SENCERA: FIX A+A2 (portes de vinculació, `eb880fd`),
> FIX B (codi del document a la rectificació, `3db0b82`), FIX C (parser determinista amb porta
> d'abdicació, `e52d5a1`) i FIX D (avís de fila perduda, `d9066b3`). Consulta només com a històric.
>
> Continuen VIUS —i no els cobreix cap dels quatre fixos— la bandera 2 (`root_code_match`, tancada
> de retruc pel llindar del FIX A) i, sobretot, **el buit de catàleg**: els 9 codis Brownie sense
> `POMMaster` ni `CustomerPOMAlias` (§D1d). La palanca sobre aquests 9 **mai va ser el parser**.

# DIAGNOSI QA-S8 — IMPORTACIÓ SPEC SHEET BROWNIE

> **Tipus:** diagnosi (Patró A · read-only). **Data:** 2026-07-13.
> **Origen:** dos defectes trobats per QA humà important
> `BROWNIE - Tate crudo Spec Sheet POM.xlsx`.
> **Cas viu:** `ImportSession#33` → `Model#163` (BLUSA: TATE, crudo), estat `MESURES`.
> Contrast: `ImportSession#32` → `Model#188` (Rosalia), estat `CONFIRMAT`.
> **STOP:** cap escriptura. Cap fix aplicat. El que segueix és el mapa i la proposta.

---

## RESUM EXECUTIU

**D1.** El parser ràpid no abdica per la capçalera doble ni per les talles: abdica perquè
**busca el codi a la columna A i en aquest document la columna A és buida**. La taula viu
de la B a la H (`dims: B2:H127`). El test `row[0] == 'POM'`
(`extraction_views.py:166`) no es pot complir mai, i el fitxer cau a Opus. Verificat
executant el parser real sobre els bytes reals: **0 POMs, 0 talles**.

**D1d — la troballa que canvia la prioritat.** El matching **NO és de la IA**: el fa
`find_pom_master` (`extraction_views.py:519`), que és 100% determinista i corre igual pels
dos camins. He passat els codis i descripcions **exactes del document** per aquesta funció
i reprodueix el resultat de la IA **fila per fila** (mateix `match_type`, mateixa
confiança, mateix POM). ⇒ **Un parser determinista no recupera ni un dels 9 sense-match.**
Els 9 sense-match són un **buit de catàleg** (codis Brownie que no existeixen ni com a
`POMMaster` ni com a `CustomerPOMAlias`), no un defecte de parsing.

**El que el parser determinista SÍ que arregla:** el document té **26 POMs** i la IA n'ha
extret **25**. Ha perdut **`JJ` (1/2 Elbow width)** — l'única fila sense valor a la talla
base — **en silenci**, sense cap avís.

**D2.** La pantalla de rectificació (pas 3 del wizard) no "perd" el codi de client:
**el té al payload i no el fa servir** (`ImportWizard.jsx:812` pinta
`p.pom_codi || p.codi_fitxa`, i el codi del **catàleg** té precedència). El tècnic veu
`CH` on el document diu `A`, i `K.2` on diu `E`.

I hi ha un defecte més greu a sota, del qual la pèrdua de codi n'és el símptoma visible:
**tota la cadena W3→W5 identifica la fila per `pom_master_id`, no per fila del document.**
Amb `U2` i `U3` resolent tots dos al POM 439 (`root_code_match` → arrel `U`), **dues files
del document col·lapsen en una**: 25 files actives → 24 cel·les d'estat. El valor de `U2`
(5.5) **queda sobreescrit pel de `U3` (5)**, i en confirmar, `unique_together ('model','pom')`
només en pot desar una. **Una mesura del document es perd sense dir res.**

El guard que ho evita **ja existeix i està escrit** (`pom/size_map_views.py:53`), amb un
docstring que descriu exactament aquesta fallada. **Mai s'ha portat a l'importador de
models.**

---

## D1 — EL PARSER RÀPID ABDICA

### D1a · L'assumpció que falla, i on exactament

`_parse_excel_poms` — `backend/fhort/models_app/extraction_views.py:137-228`.

```python
# :164-170
for idx, row in enumerate(rows):
    a = row[0] if row else None
    if a is not None and str(a).strip().upper() == 'POM':   # ← :166
        header_idx = idx
        break
if header_idx is None:
    continue                                                 # ← :170  (full següent)
...
return [], []                                                # ← :228
```

**Estructura REAL del fitxer** (llegida amb openpyxl sobre els bytes de la sessió 33):

```
full únic: 'RECTI 1 COMMENTS'   ·   dims: B2:H127   ·   11 merges
f9  : (None, 'CODE', 'DESCRIPTION', 'GRADING', 'S', 'SAMPLE', 'ADJUSTMENTS', 'COMMENTS')
f10 : (None,  None,  'ENGLISH',      None,     None, 'RECTI 1',  None,        None)
f11 : (None,  None,  'Bodice:',      None,     None,  None,      None,        None)
f12 : (None, 'A',   '1/2 chest width (armpit to armpit)', None, 45, ...)
f13 : (None, 'D ',  '1/2 bottom width relaxed ',          None, 48, ...)
```

**La columna A és buida de dalt a baix.** `row[0]` és sempre `None`
(`read_only=True` + `iter_rows(values_only=True)` retorna files de longitud 8 des de la
columna A, no des de la B). Per tant `str(a).strip().upper() == 'POM'` **no es pot complir
mai** i `header_idx` queda a `None`.

**Verificació executant el parser real:**

```
_parse_excel_poms(bytes_reals) → 0 POMs, talles=[]   ← ABDICA
```

⚠️ **No és la capçalera doble ni el nombre de talles.** És un **desplaçament de columna**.
La capçalera doble i la talla única també el trencarien —ho detallo a D1c— però **no
arriben ni a executar-se**: el parser surt abans.

**Segon nivell d'assumpcions** (les que petarien si la capçalera es trobés): el mapa de
columnes està **cablejat per índex**, no per etiqueta —
`A=codi(0)`, `C=descripció(2)`, `D=DIM(3)`, `E+(4+)=talles` (`:172-224`). Sobre Brownie
això llegiria la descripció de `GRADING` (buida), el DIM de la columna de la talla `S`, i
prendria `SAMPLE`, `ADJUSTMENTS` i `COMMENTS` **com si fossin talles**.

**Tercer nivell:** `:199-201` — `if a is None or str(a).strip()=='': break`. La fila de
secció `'Bodice:'` (f11) té el CODE **buit** i el text a DESCRIPTION ⇒ **truncaria el bloc
de dades a la primera fila**, deixant 0 POMs.

### D1b · El pipeline que ha servit aquesta importació

**És el pipeline NOU** (`import-sessions`, wizard de 5 passos amb token). `extraction_service.py`
(`extract_from_file`, Opus, el G3 antic) **NO** hi intervé: només el fan servir els
endpoints de la **Size Library** (`pom/size_map_views.py:447,486`). Són dos importadors
germans i separats.

```
W1  POST /api/v1/import-sessions/<token>/cribratge/      extraction_views.py:271
      └─ desa el document a la sessió
W1b PATCH .../talles/                                     :397
W2  POST .../extraccio/                                   :760   ◀── AQUÍ ES DECIDEIX
      ├─ és .xlsx?  → _extraccio_via_excel(session)        :666
      │                 └─ _parse_excel_poms()             :137   → ([], [])
      │                 └─ if not raw_poms: return None    :681-682
      ├─ resposta_rapida is None → CAU AL CAMÍ COMÚ        :793-794
      ├─ _excel_to_text(file_bytes) → text pla             :811-812
      ├─ avisos.append('Format Excel no reconegut pel
      │                 parser ràpid; extracció via IA.')  :813   ◀── L'AVÍS QUE HO PROVA
      ├─ Opus `claude-opus-4-7`, 16k, effort=high          :819-827
      └─ per fila: find_pom_master(...)                    :869   ◀── MATCHING DETERMINISTA
W2b PATCH .../poms/    (confirmació + tenant-only)         :930
W3  PATCH .../mesures/                                     :1061
W5  POST .../confirmar/  → BaseMeasurement                 :1205
```

**Avisos reals desats a `ImportSession#33`** — coincideixen exactament amb el que va veure QA:

```
· Format Excel no reconegut pel parser ràpid; extracció via IA.
· 9 POM(s) sense match al catàleg — cal revisar o afegir manualment.
· 4 POM(s) amb confiança baixa — recomanada revisió.
```

⚠️ **Divergència entre els dos camins** (`:730` vs `:885`): la via ràpida marca
`'actiu': True` per a **totes** les files; la via Opus, `'actiu': bool(pm)` (només les que
tenen match). No afecta el resultat final —el filtre de W5 (`:1239`) exigeix
`pom_master_id`— però és una asimetria que s'ha de tancar si es toca el parser.

### D1c · Dimensió del perfil determinista "spec sheet Brownie/RECTI"

Set coses, per ordre de mossegada. **No implementat.**

| # | Què cal | Per què (evidència) |
|---|---|---|
| 1 | **Ancorar la taula per CONTINGUT, no per columna A.** Escanejar les cel·les fins a trobar una fila amb etiquetes reconeixibles (`CODE`/`POM` + `DESCRIPTION`) i **fixar els índexs de columna on de debò estan** (B..H). | La columna A és buida. És el defecte que ho tomba tot. |
| 2 | **Mapa de columnes per ETIQUETA, no per índex fix.** `CODE`→codi, `DESCRIPTION`→descripció, la resta per nom. | `:172-224` cabla `A/C/D/E+`; Brownie és `B/C/D/E..H`. |
| 3 | **Capçalera doble amb merges.** Compondre la capçalera de f9 **i** f10: els merges verticals (`B9:B10`, `D9:D10`, `E9:E10`, `G9:G10`, `H9:H10`) només porten valor a la cel·la superior; `C9=DESCRIPTION`/`C10=ENGLISH` i `F9=SAMPLE`/`F10=RECTI 1` **no** estan fusionats i són etiquetes distintes. | 11 merges reals al fitxer. |
| 4 | **Files de SECCIÓ:** codi buit + descripció plena (`'Bodice:'`) → **SALTAR**, mai `break`. | `:199-201` truncaria a la primera fila. |
| 5 | **Files de BANNER/sketch:** `'SKETCH WITH CODES'` (f39, dins el merge `B39:H39`) té "codi" però cap valor → fi de taula o descart. Igual per als blocs fusionats `B40:H67`, `B70:H97`, `B100:H127`. | Si no, entra com un POM fantasma. |
| 6 | **Talla única.** Identificar les columnes de talla **contra el run del tenant / el `SAMPLE SIZE` de les metadades (B6='S')**, no "tot de la columna E endavant". | Altrament `SAMPLE`, `ADJUSTMENTS` i `COMMENTS` es llegirien com a talles. |
| 7 | **Codis amb espai i decimals.** `'D '` → `strip()` (ja el fa, `:218`; **conservar-ho**). Decimals com `17.75` i coma decimal: `_num()` (`:148-157`) ja ho cobreix. | El document en té un de cada. |

**Bonus barat:** el bloc de metadades `B2:B7` (`BRAND`, `NAME STYLE`, `COLOR`,
`SAMPLE SIZE`, `SEASON`) es pot llegir de passada. Avui la via ràpida retorna
`'header': {}` (`:740,750`) **encara quan funciona** — la via Opus sí que omple el header.

⚠️ **RISC ESTRUCTURAL DEL FIX (llegir abans de tocar res).** El contracte actual és
"si el parser no en treu res, cau a la IA". Un parser **més llest però equivocat** ja no
cau: **substitueix la IA en silenci** i escriu dades dolentes. Qualsevol perfil nou ha de
mantenir l'abdicació com a comportament per defecte i **només** retornar files quan pugui
demostrar que ha entès la taula (p.ex. capçalera ancorada **i** ≥N files amb valor a la
talla base). Sense aquesta porta, el fix és més perillós que el defecte.

### D1d · On es calculen els 9 sense-match i les 4 confiances baixes

**Al backend, i de manera 100% determinista.** `extraction_views.py:866-892`:

```python
for i, msr in enumerate(measurements):          # ← les files que la IA ha llegit
    codi_fitxa  = (msr.get('client_code') or msr.get('code') or '').strip()
    descripcio  = (msr.get('description') or '').strip()
    pm, match_type, confidence = find_pom_master(codi_fitxa, descripcio,
                                                 customer=import_customer)   # ← :869
    if confidence == 'LOW': n_low += 1
    if pm is None:          n_nomatch += 1
```

La IA **només** aporta `code` + `description` + `values`. **No decideix cap match.**
`find_pom_master` (`:519-620`) és pura BD: àlies del client → sinònims → descripció →
codi legacy → arrel del codi.

**Prova empírica.** He passat els **codis i descripcions exactes del document** per
`find_pom_master` amb el mateix `customer` (BRW), neutralitzant els 9 `POMMaster`
tenant-only que aquesta mateixa importació va crear (ids 453-461), per simular el catàleg
d'abans:

| | via IA (real) | parser determinista (simulat) |
|---|---|---|
| files llegides | 25 | **26** |
| sense match | 9 | **10** (els mateixos + `JJ`) |
| confiança LOW | 4 (`F`, `FF`, `U2`, `U3`) | **4 — idèntics** |
| `match_type`/POM per fila | — | **idèntics, fila per fila** |

**Resposta a la pregunta:** amb parser determinista quedarien **exactament els mateixos 9
sense-match i les mateixes 4 confiances baixes**. El parser **no toca el matching**.

Els 10 sense-match són codis Brownie **absents del catàleg**: `G1`, `E1`, `E4`, `EP`, `S`,
`S2`, `J`, `JJ`, `J1`, `I3`. La palanca per reduir-los **no és el parser: és
`CustomerPOMAlias`** — i el sistema ja el sap sembrar sol
(`maybe_learn_customer_alias`, `:1348`). La segona importació de Brownie n'hauria de
resoldre bona part.

### D1e · La fila perduda (defecte NOU, no reportat per QA)

```
document (columna B, files 12-37):  26 POMs
ImportSession#33.poms_extrets:      25
perdut:  'JJ'  ·  '1/2 Elbow width'  ·  f34  ·  valor a la talla base = (buit)
```

L'única fila **sense valor** és l'única que la IA ha deixat caure, i **cap avís ho diu**.
Un parser determinista la recuperaria (POM sense mesura base és un cas legítim:
`BaseMeasurement.base_value_cm` és `null=True`, `models.py:560`).

---

## D2 — LA PANTALLA DE RECTIFICACIÓ PERD CODI DE CLIENT I ORDRE

### D2a · Què persisteix la primera pantalla en confirmar

**Es guarda tot. En tres llocs, i els tres correctes.**

**1) A la SESSIÓ** (`ImportSession.poms_extrets`, JSON) — `extraction_views.py:874-887`:
cada fila hi desa `codi_fitxa` (el codi del document) **i** `ordre` (la posició, `i` de
l'`enumerate`). Dades reals de la sessió 33:

```
ordre  codi_fitxa   match_type          confidence   pom_id
    0  'A'          description_match   MEDIUM          273
    1  'D'          exact_description   HIGH            436     ← 'D ' ja ve amb strip()
    2  'G1'         tenant_only         TENANT_ONLY     453
   ...
   15  'U2'         root_code_match     LOW             439     ◀─┐ mateix POM
   16  'U3'         root_code_match     LOW             439     ◀─┘
```

**2) AL MODEL** (`BaseMeasurement`) — `extraction_views.py:1319-1341` (W5):

```python
for i, p in enumerate(poms):                       # poms = actius amb match (:1239)
    _defaults = {
        'nom_fitxa': p.get('codi_fitxa') or '',    # ← :1327  el codi del CLIENT
        'ordre': i,                                # ← :1330  la posició
        'notes': p.get('descripcio') or '',
        ...
    }
    BaseMeasurement.objects.update_or_create(model=model, pom=pm, defaults=_defaults)
```

`BaseMeasurement.nom_fitxa` i `.ordre` existeixen (`models_app/models.py:578-587`) i el
`Meta.ordering` **ja és** `['model', 'ordre', 'pom']` (`:592`). Verificat al **Model#188**
(Rosalia, CONFIRMAT): les 10 files hi són amb `nom_fitxa` (`'A'`, `'D'`, `'F'`, `'FF'`,
`'U'`, …) i `ordre` 0-9 **correctes**.

**3) A L'ÀLIES** (`CustomerPOMAlias`) — sí, hi juga: `maybe_learn_customer_alias(...)`
(`:1348-1350`) sembra l'àlies del client quan el tècnic resol un codi a mà, perquè la
pròxima importació d'aquest client l'encerti sola.

⇒ **La persistència NO és el problema.** El codi de client i l'ordre hi són.

### D2b · Què alimenta la pantalla de rectificació, i on es perd

La pantalla és el **pas 3 del wizard** (`ImportWizard.jsx`), alimentada per la resposta de
`POST .../extraccio/` (`extraction_views.py:916-925`), que **sí que inclou `codi_fitxa` i
`ordre`** a cada fila de `poms_extrets`.

**Es perd a la presentació, no a les dades:**

```jsx
// ImportWizard.jsx:812
<b>{p.pom_codi || p.codi_fitxa}</b>          // ← el codi del CATÀLEG mana
```

`p.pom_codi` és `POMMaster.codi_client` (el codi **nostre**), i només si és `null` es
mostra el del document. Efecte real sobre el Model#163:

```
el document diu  'A'   →  la pantalla mostra  'CH'
el document diu  'E'   →  la pantalla mostra  'K.2'
el document diu  'E2'  →  la pantalla mostra  'A.1'
el document diu  'E3'  →  la pantalla mostra  'A.2'
```

El tècnic **no pot relacionar cap fila amb l'spec sheet que té al davant**. (El pas 2 sí
que ensenya el codi del document, `:681` — la incoherència entre les dues pantalles és
precisament el que fa que la pèrdua es noti al pas 3.)

**L'ORDRE: el defecte de sota, i és més greu.**

L'ordre de **render** sí que és el del document (`pomsTaula` és l'array filtrat,
`:280`). El que es perd és la **identitat de fila**: **tota la cadena W3→W5 indexa per
`pom_master_id`**, mai per fila del document.

```jsx
:107  const [taula, setTaula] = useState({})   // {pom_master_id: {talla: valor}}
:294  t[p.pom_master_id] = row                 // buildTaula
:299  const setCell = (pid, talla, val) => ...
:312  base_values[p.pom_master_id] = v         // grading-preview
:347  mesures.push({ pom_master_id: p.pom_master_id, talla_label, valor })
:810  <tr key={p.pom_master_id}>
```

i al backend, igual: `PATCH .../mesures/` rep `{pom_master_id, talla_label, valor}`
(`:1078-1084`), i W5 desa amb `update_or_create(model=model, pom=pm)` contra
`unique_together ('model','pom')` (`models.py:591`).

**⇒ Si dues files del document resolen al MATEIX POM, no hi caben.** I aquí n'hi ha dues:

`U2` i `U3` → `find_pom_master` no els troba per descripció, cau al **darrer recurs**
`root_code_match` (`:612-618`): arrel de lletres `U` → `POMMaster codi_client='U'` (id 439)
**per als dos**. Confiança `LOW`, però **s'auto-vinculen igualment**.

**Simulació del pas 3 amb les dades reals del Model#163:**

```
files actives (pomsTaula):    25
claus de l'objecte `taula`:   24        ← 1 FILA COL·LAPSADA

  #  doc   MOSTRA  key <tr>   valor doc   valor que pinta la cel·la
 15  U2    U            439         5.5                          5   🔴 VALOR CANVIAT
 16  U3    U            439           5                          5   ⬅ CLAU REPETIDA
```

Conseqüències, totes reals:
1. Les dues files es mostren com a **`U`** — indistingibles.
2. Comparteixen **una sola cel·la d'estat**: el 5.5 de `U2` **desapareix**, sobreescrit pel
   5 de `U3`. Editar-ne una edita l'altra.
3. `<tr key={439}>` **duplicat** (React).
4. En confirmar, `update_or_create(model, pom=439)` **escriu una sola fila**: guanya
   l'última (`nom_fitxa='U3'`, `ordre=16`, valor 5). **La mesura de `U2` es perd
   definitivament, sense cap avís.**

**El guard que ho evita JA ESTÀ ESCRIT** — `pom/size_map_views.py:53-76`,
`_apply_many_to_one_guard`. El seu docstring descriu la fallada al mil·límetre:

> *"si DUES files del mateix document resolen al MATEIX POM per DESCRIPCIÓ/fuzzy, cap de
> les dues auto-vincula → totes a pendents amb avís explícit […] dues files que hi
> caurien col·lapsarien i la segona sobreescriuria la primera"*

Es va escriure per a `GradingRule`, únic per `(rule_set, pom)`. **`BaseMeasurement` té
exactament la mateixa restricció** — `unique_together ('model','pom')` — i **el guard mai
s'ha portat a l'importador de models**. S'aplica només a la Size Library
(`size_map_views.py:353` i `:597`).

### D2c · Punt mínim d'intervenció

**Tres capes. La d'enmig és la que de debò tanca el forat.**

**(1) BACKEND — el guard (ROOT FIX).** Portar `_apply_many_to_one_guard` a
`extraction_views.py`, aplicat sobre `poms_extrets` just després del bucle de matching
(`:887`, abans dels comptadors d'avisos `:889-892`). Dues files → mateix POM (i que no
sigui `alias_match`) ⇒ **cap de les dues auto-vincula**; totes dues cauen a pendents amb
`weak_suggestion` visible, i el tècnic decideix (assignar-ne un altre, o crear tenant-only,
que és el que ja sap fer al pas 2 via `poms_tenant_only`, `:948-988`).

Amb això, `pom_master_id` **passa a ser injectiu** per sessió, i la resta de la cadena
(que hi està indexada) deixa de ser insegura **sense haver-la de reescriure**.

**(2) FRONTEND — la nomenclatura.** `ImportWizard.jsx:812`: invertir la precedència i
ensenyar els dos.

```jsx
<b>{p.codi_fitxa || p.pom_codi}</b>
{p.pom_codi && p.codi_fitxa && p.pom_codi !== p.codi_fitxa && (
  <span style={{ color: 'var(--text-muted)' }}> → {p.pom_codi}</span>
)}
```

El codi del document mana (és el que el tècnic té al paper); el del catàleg queda com a
secundari. Coherent amb el pas 2 (`:681`) i amb la taula del model, que ja fa
`nom_fitxa || pom_code` (`MeasureGrid.jsx:164-166`).

**(3) ORDRE com a dada de primera (opcional, i jo NO el faria ara).** Reindexar l'estat del
pas 3 per `p.ordre` en comptes de `p.pom_master_id` (`:107,294,299,312,332,347,373,810`).
**Amb el guard (1) posat, això deixa de ser necessari**: si el POM és injectiu, indexar per
POM ja preserva la fila. Fer-ho igualment vol dir tocar el contracte de
`PATCH /mesures/` i de `grading-preview/` — molt més radi per molt poc guany.

**La cadena posterior ja conserva codi_client + ordre**: `BaseMeasurement.nom_fitxa`/`ordre`
s'escriuen bé (`:1327,1330`), el `Meta.ordering` ja hi és (`models.py:592`), la taula del
model els llegeix (`views.py:833` `order_by('ordre','pom__codi_client')`, i `:880`
`'nom_fitxa': bm.nom_fitxa`), i el fitting també (`fitting/serializers.py:230-237`).
**No cal tocar-la.**

---

## FIX MÍNIM PROPOSAT — DIMENSIÓ I RISC

| # | Fix | Fitxers | Dimensió | Risc |
|---|---|---|---|---|
| **A** | **Guard many-to-one a l'import** (porta `_apply_many_to_one_guard`) | `extraction_views.py` (~15 línies) | **½ sessió** | **BAIX.** Codi ja escrit i en producció a la Size Library. Fa caure files a pendents en comptes d'auto-vincular-les: **més conservador**, mai menys. Tanca una pèrdua de dades silenciosa. |
| **B** | **Codi del document a la pantalla de rectificació** | `ImportWizard.jsx:812` (~4 línies) | **½ sessió** (amb i18n) | **MOLT BAIX.** Cosmètic i local. Cap contracte tocat. |
| **C** | **Perfil determinista "spec sheet Brownie/RECTI"** (D1c, 7 punts + porta d'abdicació) | `extraction_views.py:137-228` + tests amb el fitxer real | **1,5-2 sessions** | **MITJÀ-ALT.** Un parser que entén *massa* deixa de caure a la IA i escriu dades dolentes en silenci. **Innegociable:** porta d'abdicació explícita + fixture del fitxer real + test que el camí IA continua sent el fallback. |
| **D** | *(anotat, no proposat)* Avís quan el nombre de files extretes < files amb codi al document | — | — | Tanca la pèrdua silenciosa de `JJ`. Depèn de C. |

### Ordre recomanat

**A → B → C.** I la raó importa: **A i B són barats i tanquen els dos defectes que QA ha
vist**, sense tocar el parser. **C és el més car i és el que MENYS problema resol** — no
recupera ni un dels 9 sense-match (D1d ho demostra). C val la pena pel cost/latència
d'Opus, per la fila `JJ` i pel determinisme, **no** perquè millori el matching.

**La palanca de debò sobre els 9 sense-match no és cap dels tres: és el catàleg.** Els codis
Brownie no hi són. `maybe_learn_customer_alias` (`:1348`) ja sembra els àlies quan el tècnic
resol a mà, i els 9 `POMMaster` tenant-only (453-461) ja s'han creat en aquesta sessió: **la
propera importació de Brownie hauria de baixar sola**. Val la pena mesurar-ho **abans**
d'invertir en C.

---

## BANDERES PER AL CTO

1. **`ImportSession#33` (Model#163) està a mig camí** (`estat='MESURES'`, sense confirmar).
   Si es confirma **tal com està ara**, la mesura de `U2` (5.5) es perdrà en silenci
   (D2b·4). **Recomanació: no confirmar-la fins que el fix A hi sigui**, o resoldre `U2`/`U3`
   a mà al pas 2.
2. **`root_code_match` (`:612-618`) auto-vincula amb confiança `LOW`.** El comentari del codi
   diu que un LOW "no auto-vincula" (`:533-535`), però al camí d'import **sí que ho fa**: el
   llindar de `_apply_match_threshold` existeix a `size_map_views.py:29` i **no** a
   `extraction_views.py`. És la mateixa asimetria que el guard. Ho anoto: **fora d'abast**,
   però és el mateix forat.
3. **La via ràpida i la via Opus divergeixen en `actiu`** (`:730` `True` vs `:885` `bool(pm)`)
   i en `header` (`{}` vs l'extret). Tancar-ho quan es toqui el parser (fix C).
4. El document té **blocs fusionats grans** (`B40:H67`, `B70:H97`, `B100:H127`) amb sketch i
   comentaris. Qualsevol parser ha de tallar la taula abans, no recórrer fins a la fila 127.

---

*Diagnosi read-only. Cap escriptura, cap migració, cap fix aplicat.
Evidència verificada executant `_parse_excel_poms` i `find_pom_master` sobre els bytes
reals de `ImportSession#33` i les dades reals dels models 163 i 188.*
