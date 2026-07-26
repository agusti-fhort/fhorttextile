# DIAGNOSI — El tram que s'expandeix (Definir tram)

> Patró A · READ-ONLY · 2026-07-15 · branca `dev`
> Defecte QA (captures 07-15): el preview A→B es pinta TARONJA amb una llargada
> (ex. 22,7 cm); en desar, el tram es pinta BLAU i MÉS LLARG que el previsualitzat.

## Veredicte en una línia

**No es desa res de dolent: el que menteix és el DIBUIX.** El rang `(point_a, point_b)`
viatja intacte fins a la BD i la longitud persistida és exactament la del preview. El
defecte és un **epsilon amb el signe girat** a `puntsDelSegment`
([patternGeometry.js:188-190](../../frontend/src/components/pattern/patternGeometry.js#L188-L190)),
que fa entrar al dibuix **un tram de vora de més a cada extrem**. El tram desat es pinta
sempre més llarg del que és — i més llarg del que s'ha ensenyat.

Reproduït sobre **4/4 dels trams declarats reals** del tenant `fhort` a staging. Cap
n'escapa.

---

## a) VIATGE DEL RANG — net, sense cap arrodoniment

El payload del create porta **només dos punts**, ni `t` ni longituds
([TallerPatro.jsx:733-738](../../frontend/src/pages/TallerPatro.jsx#L733-L738)):

```js
const cos = { point_a: puntsPom[0].id, point_b: puntsPom[1].id,
              nom: nomTram.trim(), arc_llarg: arcTram.arcLlarg }
```

El servidor resol el tram sobre la geometria
([annotation_views.py:774-795](../../backend/fhort/patterns/annotation_views.py#L774-L795)):
carrega la vora de `point_a` (`_BoundaryCache().get(pa.piece, pa.boundary_index)`), crida
`tram_entre_punts(boundary, pa.boundary_index, pa.ordre, pb.ordre, arc_llarg)` i escriu
`t_inici`/`t_fi` **verbatim**.

`tram_entre_punts` ([segments.py:105-183](../../backend/fhort/patterns/engine/segments.py#L105-L183))
calcula els paràmetres com a longitud acumulada del vèrtex:
`t_a = cum[index_a] / total`, `t_b = cum[index_b] / total`
([segments.py:149-150](../../backend/fhort/patterns/engine/segments.py#L149-L150)).

> **En tot el camí create NO hi ha cap `round`, cap tolerància, cap snapping i cap
> ajust als trams automàtics veïns.** Les úniques operacions no lineals són el `% 1.0`
> de tria d'arc i el `<=` de desempat. Els trams AUTO (`segmentar_vora`,
> [segments.py:186-244](../../backend/fhort/patterns/engine/segments.py#L186-L244)) són un
> camí de codi **separat**: els declarats no els consulten, ni s'hi alineen, ni s'hi
> retallen. **La hipòtesi «el backend arrodoneix el rang als trams veïns» queda REFUTADA.**

### SELECT del tram real vs el rang demanat

Els 4 trams declarats del tenant `fhort`. «Demanat» = vèrtexs A→B reconstruïts de
`t_inici`/`t_fi` via `acumulats_vora`:

| seg | peça | vora | demanat | `t_inici` → `t_fi` | desat correcte? |
|---|---|---|---|---|---|
| 290 | TATE_BACK | 5 | 165 → 167 | 0.6237906480 → 0.7756267308 | ✅ exacte |
| 291 | TATE_FRONT | 10 | 68 → 72 | 0.1144623162 → 0.2898889266 | ✅ exacte |
| 314 | TATE_FACING_YOKE | 1 | 18 → 19 | 0.5338718237 → 0.6293294126 | ✅ exacte |
| 315 | TATE_FRONT_FACING | 1 | 39 → 40 | 0.7152956202 → 0.7619580818 | ✅ exacte |

**El rang desat és el rang demanat.** El viatge del rang no té cap defecte.

---

## b) VIATGE DEL RENDER — la MATEIXA vora (sospita refutada)

La sospita «preview sobre cosit, desat resolt sobre tall» **no es confirma**. Tots dos
resolen la **mateixa** vora, per dos camins que convergeixen:

- **Preview (taronja):** `arcEntre` → `situaPunt(pieces, pa)` retorna la vora del punt
  **ancorat** i passa l'**objecte** vora a `arcDirigit`
  ([PatternViewer.jsx:320-325](../../frontend/src/components/pattern/PatternViewer.jsx#L320-L325)).
- **Desat (blau):** `puntsDelSegment` fa `piece.boundaries[segment.vora]`, un accés
  **posicional** ([patternGeometry.js:161](../../frontend/src/components/pattern/patternGeometry.js#L161)).

Coincideixen perquè `index` s'assigna per enumeració a l'import
([adapters.py:211-219](../../backend/fhort/patterns/adapters.py#L211-L219)) i l'API
reconstrueix `boundaries` en aquest mateix ordre
([serializers.py:113-122](../../backend/fhort/patterns/serializers.py#L113-L122)). A més,
`segment.vora` **és** `pa.boundary_index` — la vora del punt A, la mateixa que el preview.
No hi ha cap filtre per `role` enlloc del camí: cap dels dos «tria» tall ni cosit; tots dos
prenen la vora on viu el punt ancorat.

> Cap filtre per rol vol dir que el rol de la vora no és el problema **aquí**, però sí que
> és una fragilitat anotada: l'imant es tanca per `b.index === voraIman`
> ([TallerPatro.jsx:699-702](../../frontend/src/pages/TallerPatro.jsx#L699-L702)), mai per rol.
> Fora de scope.

### La causa exacta

[patternGeometry.js:181-196](../../frontend/src/components/pattern/patternGeometry.js#L181-L196):

```js
for (let i = 0; i < trams; i++) {
  const t0 = acumulat / total
  const t1 = (acumulat + llargs[i]) / total
  const dins = envolta
    ? (t1 > segment.t_inici - 1e-9 || t0 < segment.t_fi + 1e-9)
    : (t1 > segment.t_inici - 1e-9 && t0 < segment.t_fi + 1e-9)
  if (dins) {
    if (!out.length) out.push(pts[i])
    out.push(pts[(i + 1) % n])
  }
  acumulat += llargs[i]
}
```

Un tram de vora `[t0, t1]` se solapa amb `[t_inici, t_fi]` si `t1 > t_inici && t0 < t_fi`.
Amb igualtat exacta (`t1 === t_inici`) el solapament té mesura **zero** i el tram **no**
hi entra — que és el correcte.

**I `t1 === t_inici` passa SEMPRE**, perquè `t_inici` és, per construcció,
`cum[index_a]/total`: exactament la frontera entre el tram `index_a - 1` i el `index_a`.

L'epsilon volia absorbir el soroll de coma flotant, però està aplicat **cap enfora**
(`t_inici - 1e-9`, `t_fi + 1e-9`): en comptes d'estrènyer la comparació, **eixampla el rang
d'acceptació** i converteix l'empat exacte en solapament positiu. Resultat: hi entra el
tram **anterior** a A i el **posterior** a B.

```
vèrtexs:      163────164────165────166────167────168
demanat:                      A●━━━━━━━━━━●B          ← preview taronja
pintat:              ●━━━━━━━━━━━━━━━━━━━━━━━━━●      ← desat blau (+1 aresta a cada punta)
```

### Mesura sobre dades reals

Rèplica exacta de `puntsDelSegment` (JS) executada en Python sobre la geometria real:

| seg | demanat | ARA pinta | veritat | canvas blau | **expansió** |
|---|---|---|---|---|---|
| 290 | 165 → 167 | 164 → 168 | 29,80 cm | 30,02 cm | **+0,22 cm** |
| 291 | 68 → 72 | 67 → 73 | 32,13 cm | 33,14 cm | **+1,01 cm** |
| 314 | 18 → 19 | 17 → 20 | 4,01 cm | 13,02 cm | **+9,01 cm** |
| 315 | 39 → 40 | 38 → 41 | 3,98 cm | 13,53 cm | **+9,55 cm** |

L'expansió **no és constant**: és la llargada de les dues arestes veïnes. Per això a QA es
veu escandalosa en trams curts voltats d'arestes llargues (seg 314: un tram de 4 cm es pinta
de 13 cm, **3,2×**) i quasi imperceptible en trams llargs sobre corba fina (seg 290: +2 mm).
Això explica per què el defecte ha pogut viure fins ara sense saltar.

---

## c) LONGITUD — la xifra del preview és la veritat geomètrica

**El preview (22,7) diu la veritat. El dibuix blau és l'únic que menteix.**

Tres números, i dos d'ells ja coincideixen:

| Número | Origen | Correcte? |
|---|---|---|
| Preview taronja (22,7 cm) | `previa.longitud / 10`, de `arcsEntrePunts` recorrent vèrtexs A→B ([PatternViewer.jsx:565](../../frontend/src/components/pattern/PatternViewer.jsx#L565)) | ✅ |
| Llista / `longitud_cm` | `longitudTram(vora, t_inici, t_fi)` ([TallerPatro.jsx:~825](../../frontend/src/pages/TallerPatro.jsx#L825)) i, al servidor, `get_longitud_cm` ([annotation_views.py:744](../../backend/fhort/patterns/annotation_views.py#L744)) | ✅ (mateix valor) |
| **Llargada pintada al canvas** | `puntsDelSegment` | ❌ **l'única falsa** |

Conseqüència operativa: **la fitxa i la llista sempre han estat correctes**. Qui hagi
comparat el número de la llista amb el dibuix ha vist una contradicció, i el número tenia raó.
No hi ha cap dada corrupta a la BD i **el fix no requereix cap re-creació de trams**.

---

## d) COLOR / ESTAT — inventari

Tot es decideix inline dins `tramsDeclarats.map`
([PatternViewer.jsx:424-440](../../frontend/src/components/pattern/PatternViewer.jsx#L424-L440)),
amb `KONVA_COL` definit a [PatternViewer.jsx:29-49](../../frontend/src/components/pattern/PatternViewer.jsx#L29-L49):

| Estat | Constant | Valor | Gruix | Traç |
|---|---|---|---|---|
| Preview `seg` (en curs) | `tramSel` | `#fb8500` taronja | `4/zoom` | discontinu `[9,5]`, opacitat 0,85 |
| Arc ja fixat del gest | `tramSel` | `#fb8500` taronja | `5/zoom` | continu |
| **Tram desat** | `tram` | **`#0969da` blau** | `2.5/zoom` | continu |
| Desat + ressaltat a la llista | `tramSel` | `#fb8500` taronja | `4.5/zoom` | continu |
| Cosir · costat A | `sewA` | `#1f6feb` | `4.5/zoom` | continu |
| Cosir · costat B | `sewB` | `#8250df` | `4.5/zoom` | continu |
| Ombra de reobrir | `tramSel` | `#fb8500` | `3/zoom` | discontinu, opacitat 0,45 |

**El problema d'identitat visual és real i és independent del bug geomètric.** El taronja
`#fb8500` i el blau `#0969da` no són el mateix to amb un èmfasi diferent: són **dos colors
sense cap parentiu**. El gest ensenya un objecte taronja i en desa un de blau — i, avui, també
més llarg. Encara que la geometria es corregeixi, el salt de color continuarà llegint-se com
«ha aparegut una altra cosa», no com «això que acabes de fer, ara desat».

> Nota: `#fb8500` també és el color de *ressaltat de la llista* i de *l'ombra de reobrir* —
> el taronja ja fa **tres** feines. I `KONVA_COL.hover` (`#c27a2a`,
> [PatternViewer.jsx:41](../../frontend/src/components/pattern/PatternViewer.jsx#L41)) està
> **definit i no s'usa enlloc** (codi mort).
>
> La llei per al fix posterior: **una sola identitat per al tram** (el blau), i l'estat només
> en canvia l'ÈMFASI (gruix, discontinu→continu, opacitat) — mai el to. El preview hauria de
> ser el mateix blau, discontinu i translúcid; en desar, només es solidifica. Això no és
> aquest fix: **és un sprint de disseny a part**, i barrejar-lo amb la correcció geomètrica
> faria un commit amb dos focus.

---

## FIX MÍNIM PROPOSAT

Un sol canvi, dues línies, a `puntsDelSegment`
([patternGeometry.js:188-190](../../frontend/src/components/pattern/patternGeometry.js#L188-L190)):
**girar el signe de l'epsilon** perquè exigeixi solapament de mesura positiva.

```js
// ARA (eixampla: l'empat exacte entra)
const dins = envolta
  ? (t1 > segment.t_inici - 1e-9 || t0 < segment.t_fi + 1e-9)
  : (t1 > segment.t_inici - 1e-9 && t0 < segment.t_fi + 1e-9)

// FIX (estreny: cal solapament real)
const dins = envolta
  ? (t1 > segment.t_inici + 1e-9 || t0 < segment.t_fi - 1e-9)
  : (t1 > segment.t_inici + 1e-9 && t0 < segment.t_fi - 1e-9)
```

L'epsilon **cal** (el `t_inici` ve d'una suma de `hypot` feta en **Python** i el `t0` d'una
suma feta en **JS**: poden diferir en l'últim ulp), però ha d'anar **cap endins**. `1e-9` és
alhora molt més gran que el soroll de doubles (~1e-16 relatiu) i molt més petit que qualsevol
aresta real (la més curta d'aquestes peces és ~1e-5 del total).

### Validació del fix sobre les dades reals

| seg | demanat | ARA | FIX | veritat | error FIX |
|---|---|---|---|---|---|
| 290 | 165→167 | 164..168 · 30,02 cm | **165..167 · 29,80 cm** | 29,80 cm | **0,00** |
| 291 | 68→72 | 67..73 · 33,14 cm | **68..72 · 32,13 cm** | 32,13 cm | **0,00** |
| 314 | 18→19 | 17..20 · 13,02 cm | **18..19 · 4,01 cm** | 4,01 cm | **0,00** |
| 315 | 39→40 | 38..41 · 13,53 cm | **39..40 · 3,98 cm** | 3,98 cm | **0,00** |

**4/4 exactes.** El desat passa a pintar-se sobre exactament els vèrtexs demanats, i la
llargada pintada iguala la persistida i la del preview.

### Cobertura del fix

Una sola funció, però **cinc superfícies** en depenen. Totes es curen alhora:

| Superfície | Crida |
|---|---|
| Trams desats al canvas | [PatternViewer.jsx:423](../../frontend/src/components/pattern/PatternViewer.jsx#L423) |
| **Cosir · ressaltat A/B** | [PatternViewer.jsx:423](../../frontend/src/components/pattern/PatternViewer.jsx#L423) (mateix `map`; el color només canvia el `stroke`) |
| Cosir · proposta sota el cursor | [PatternViewer.jsx:499](../../frontend/src/components/pattern/PatternViewer.jsx#L499) |
| Ombra de reobrir tram | [TallerPatro.jsx:622](../../frontend/src/pages/TallerPatro.jsx#L622) |
| Costats de pinça | [TallerPatro.jsx:856](../../frontend/src/pages/TallerPatro.jsx#L856) |

> **Sí, afecta també els trams que «Cosir» ressalta** (pregunta del brief): el ressaltat
> `sewA`/`sewB` es pinta dins el **mateix** `map` i amb els **mateixos** `pts` expandits —
> només canvia el color. Verificat: els segs 290/291 són els dos costats de `sew 12` i tots
> dos expandeixen. El fix els cura sense tocar res del Cosir.

---

## Troballes col·laterals (ANOTADES, no tocades)

1. **⚠️ La branca `envolta` de `puntsDelSegment` està trencada, no només desalineada.**
   Per a un tram que travessa l'origen de la polilínia, els trams inclosos són els del
   **final** i els del **principi** del bucle, però `out` es construeix en ordre d'iteració:
   surt `[pts[0]…pts[tf], pts[ti+1]…]` — amb un **salt** de `tf` a `ti+1` i **saltant-se el
   vèrtex `ti`** (perquè `if (!out.length)` ja és fals). La polilínia pintada seria un
   garbuix. **Latent**: cap dels 4 trams reals no envolta (`envolta=False` a tots). Girar
   l'epsilon **no** ho arregla; cal reconstruir l'ordre (`[ti…n-1, 0…tf]`). Recomanació:
   peça pròpia, amb un tram que envolti fabricat a propòsit per al test.

2. **L'àpex de pinça hereta l'error.** `apex: primer[primer.length - 1]`
   ([TallerPatro.jsx:864](../../frontend/src/pages/TallerPatro.jsx#L864)) pren l'últim punt
   dels `costats` retornats per `puntsDelSegment`: amb el bug, **un vèrtex més enllà de
   l'àpex real**. **Latent avui** (`es_pinca=False` a les 4 SewRelation de staging), però
   s'activaria sol el dia que es declari una pinça. El fix de l'epsilon també el cura.

3. **`KONVA_COL.hover` (`#c27a2a`) és codi mort** — definit a
   [PatternViewer.jsx:41](../../frontend/src/components/pattern/PatternViewer.jsx#L41), zero
   usos. El feedback de hover es fa amb l'halo de l'imant i la barra d'estat.

4. **Dues maneres de resoldre la vora conviuen**: cerca per camp
   (`boundaries.find(b => b.index === sg.vora)`, [TallerPatro.jsx:~823](../../frontend/src/pages/TallerPatro.jsx#L823))
   i accés posicional (`boundaries[segment.vora]`, `puntsDelSegment`). Avui coincideixen per
   construcció de l'import. És una assumpció no escrita: el dia que `contorns` es filtri o es
   reordeni, les dues divergirien en silenci.

5. **Doc del model desalineat**: `models.py:248` diu que els segments AUTO surten «sobre el
   contorn de tall (S6)», però `segmentar_peca`
   ([segments.py:247-268](../../backend/fhort/patterns/engine/segments.py#L247-L268)) fa
   SEW-primer amb CUT de reserva.

---

## STOP

Cap escriptura de codi. Aquest document és l'única sortida. El fix (1 commit, 2 línies +
test de regressió amb els vèrtexs demanats) espera decisió del CTO.
