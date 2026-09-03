# ESMENA DE MAQUETES · S38 — llista de canvis per revisar

**Data:** 08/08/2026 · **Sessió paral·lela.** Cap fitxer d'`ops/maquetes/` tocat, cap commit,
cap push, cap contacte amb el vault. Els tres HTML corregits esperen aquí per pujar-los tu.

**Fonts contra les quals s'ha esmenat:** `FTT-Brain/NORMA_LAYOUT.md` (=
`ops/maquetes/NORMA_LAYOUT.md`), `docs/diagnosis/REVISIO_ENDPOINTS_FASE_A.md` (T2), i els
models reals — llegits directament, no citats de memòria.

**Verificació:** els tres carreguen a Chromium **sense cap error de JS**, s'han exercitat els
gestos que he tocat (veredicte, derivació, marcar break, triar capes, canviar de run) i s'ha
escombrat el desbordament horitzontal a 1500 i 1280 px: cap.

> ⚠️ **Un punt del brief era mig fals i NO l'he aplicat: v. §4.** La cardinalitat FK és de
> `GradingRuleSet`; a `SizeSystem` les quatre capes són M2M i la multi-selecció ja era correcta.

---

## 1 · `maqueta_fitting_v4.html` (77 línies)

| # | Què deia | Què diu ara | Per què |
|---|---|---|---|
| 1.1 | `LAYEN` amb `Interlining · Binding · Knit · Reinforcement`, 2 capes inventades (`Vores`, `Punt`) i 2 capes reals absents (`farciment`, `fornitura`) | Vocabulari D-31.22: **Shell · Lining · Interfacing · Padding · Underlining · Trim** | `utils/capaInstancia.js:9-13` ja ho havia deixat escrit: «són ERRONIS i no s'han copiat». La v4 no ho havia incorporat |
| 1.2 | Peu del PDF amb els mateixos 6 noms falsos | Els 6 noms reals | Mateix motiu; era la segona còpia |
| 1.3 | `sis:{lay:'Folre', folg:2.0}` — **la folgança com a propietat de la fila** | `sis:{lay:'Folre', val:47.0}` — **la germana té valor propi** | `services_derivacio.py:1-12`: «no hi ha cap norma de folgança enlloc del sistema i no se n'inventa cap. La folgança és, sempre, la RESTA entre dues files» |
| 1.4 | Derivada = `exterior − folg` | Derivada = `valor propi + increment de l'exterior`; la folgança es **llegeix** com a resta i no es desa | «Es mou el VALOR, mai el grading»: es propaga l'INCREMENT, mai l'absolut |
| 1.5 | Rebuig → derivada = `últim històric − folg` | Rebuig → derivada = **el seu propi últim valor vàlid** | Sense folgança desada, l'últim valor vàlid és seu, no una resta |
| 1.6 | Etiqueta «folgança 2,0 cm» | «2,0 cm de folgança · *resta Exterior − Folre*» | Que es llegeixi que és una lectura, no un camp |
| 1.7 | Spec de la germana al PDF = `R.val − folg` | = el seu valor propi | Coherència amb 1.3 |
| 1.8 | Toast amb `Lining` literal | `LAYEN[...]` de la capa germana | Deixa de dependre d'una capa concreta |
| 1.9 | Identitat: `· Plana ·` | `· Teixit pla ·` | `ConstructionType.WOVEN.nom_cat` = «Teixit pla». Era el punt **«no verificat»** del report; ara verificat contra `fhort` |
| 1.10 | *(conducta afegida)* el valor teclejat es perdia a cada redibuix | `st[i].val` desa el valor mesurat; `onchange` redibuixa i torna el focus | **Sense això la correcció no es veu**: la germana no es movia mai i el mecanisme quedava invisible. És l'únic canvi de comportament del lot |

## 2 · `maqueta_grading_rules_v4.html` (178 línies)

| # | Què deia | Què diu ara | Per què |
|---|---|---|---|
| 2.1 | `REGIMS=['LINEAR','LINEAR+BREAK','STEP','FIXED']` en un **`<select>` que escriu** | Els **5 reals**: `LINEAR · STEP · FIXED · ZERO · EXCEPTION`, marcats **il·lustratius**, amb la font anotada: `GET /api/v1/vocabulari/ → regims_graduacio` | `LINEAR+BREAK` no existeix ni pot existir; hi faltaven `ZERO` i `EXCEPTION`. Desar-hi hauria produït un valor invàlid |
| 2.2 | 20 files de mostra amb règim `LINEAR+BREAK` | `LINEAR` (i una `ZERO` i una `EXCEPTION` perquè els 5 es vegin en ús) | El break és **propietat de la regla**, no un règim (`grading_regime.py`: «el break és SAGRAT… la regla és LINEAR encara que el delta base sigui 0») |
| 2.3 | `s.brk` — **break del JOC** | `r.brk` per regla; el gest de clicar la talla es conserva i **escriu a les regles amb Δ break** | `talla_break_label` viu a `GradingRule`; 530 regles de `fhort` en tenen un i no han de ser el mateix |
| 2.4 | Columna «Talla break» = `s.brk` si el règim era `LINEAR+BREAK` | = `r.brk` de la seva fila | Conseqüència de 2.3 |
| 2.5 | Δ break deshabilitat si el joc no tenia break | Sempre editable | És el Δ break qui dona break a la regla, no al revés |
| 2.6 | Construcció · Fit · Grup en **multi-selecció** (`toggle()`) | **UN sol valor** (`triaUnica`): triar-ne un desmarca l'anterior, re-clicar **desdeclara**. Target segueix multi | A `GradingRuleSet`: `targets` M2M, però `construction`, `fit_type` i `garment_group` són **FK** |
| 2.7 | «Un joc sense cap relació marcada **val per a tothom**» (avís, previsualització, columna de la llista i peu) | «**NO DECLARAT** — ningú no ha dit encara per a qui és» | `pom/models.py:617` i `serializers.py:126` diuen el contrari **per escrit**: «buit NO és universal, és no declarat» |
| 2.8 | Vocabularis declarats i muts | Els 4 marcats **il·lustratius** amb el seu endpoint, i posats als valors reals de `fhort` | Regla d'or. `CONSTR` deia «Punt» (real: **Teixit de punt**), 3 fits retallats i **cap dels 8 grups existia** (n'hi ha 12, en anglès, sense traducció al model) |
| 2.9 | Mapa `N` de noms de POM sense avís | Comentari que és il·lustratiu i que 7 dels 22 codis no existeixen | Perquè ningú no el prengui per referència |
| 2.10 | *(defecte propi, caçat mesurant)* la caixa nova d'avís no ajustava el text | Classe `avis neu` en comptes de `avis n` | `.n` ja és la utilitat del comptador i porta `white-space:nowrap`: la meva classe hi va col·lidir i el text quedava tallat. **A ull semblava correcte; ho va delatar mesurar `scrollWidth`** |

## 3 · `maqueta_size_library_v3.html` (84 línies)

| # | Què deia | Què diu ara | Per què |
|---|---|---|---|
| 3.1 | Camp `sys` + badge **«CANÒNIC DE LA CASA»** | Fora. La llista i la fitxa diuen «de la casa» / «RUN DE *X*» / «SENSE CLIENT», **derivat del client buit** | `SizeSystem` **no té `is_system`** ni cap flag de canonicitat |
| 3.2 | «Esborrar» bloquejat si `r.sys` | Bloquejat **només per ús** | La protecció penjava d'un camp inexistent. **Si cal protegir els runs de la casa, és una decisió que necessita un camp real** — v. §5 |
| 3.3 | «Restriccions · cap — **serveix a tothom**» (i el peu) | «cap capa declarada» + frase que ho explica: buit = **no declarat** | Mateixa llei que 2.7 |
| 3.4 | Vocabularis declarats | Marcats il·lustratius amb el seu endpoint, valors reals | Mateix motiu que 2.8; les dades de mostra s'han reetiquetat («Vestits»→`Dresses & Jumpsuits`, «Punt»→`Teixit de punt`, «Parts inferiors»→`Bottoms`…) |

---

## 4 · 🛑 UN PUNT DEL BRIEF QUE NO HE APLICAT, I PER QUÈ

> El brief demanava per a la size library «**mateixa cardinalitat FK**» que a grading.

**No s'hi val, i aplicar-ho hauria introduït una mentida nova.** A `SizeSystem` les **quatre**
capes són **ManyToMany** (`pom/models.py:617-628`), amb el comentari del propi model:
«amb el patró que la casa ja fa servir per a `targets`: M2M al vocabulari… 0..n per capa».

| | targets | construcció | fit | grup |
|---|---|---|---|---|
| `GradingRuleSet` | M2M | **FK** | **FK** | **FK** |
| `SizeSystem` | M2M | **M2M** (`construccions`) | **M2M** (`fits`) | **M2M** (`grups`) |

La multi-selecció de la size library **ja era correcta i s'hi queda**. El que sí que comparteixen
les dues pantalles —i sí que he aplicat— és la reformulació del buit (§2.7 / §3.3), que és la
mateixa llei per a les dues.

## 5 · Conducta afegida (per si la vols vetar)

1. **Fitting** — el valor teclejat ara persisteix a l'estat i la germana s'hi mou (§1.10). Sense
   això la correcció de la folgança no s'hauria pogut ni veure.
2. **Grading** — clicar una talla escriu el break a **totes** les regles que tenen Δ break. És el
   gest que vas ratificar a la v2, però ara desa on toca. **Límit conegut:** així no es pot donar
   un break diferent a dues regles del mateix joc, cosa que el model **sí** permet. Si això ha de
   ser possible, cal decidir com (columna editable per fila?).
3. **Size library** — s'ha perdut la protecció «no esborrar un run canònic» (§3.2). Ara mateix un
   run de la casa sense ús és esborrable. **Decisió teva:** o es viu així, o el gate necessita un
   camp real al model.

## 6 · Vist i NO tocat (fora del brief)

- **Grading, «Un joc no depèn de cap run»** (ident. i hint de talles). `GradingRuleSet.size_system`
  segueix sent FK real amb guard d'immutabilitat, i **39 de 46** rulesets de `fhort` la tenen
  poblada. La frase descriu **l'estat objectiu** de CAT2.1 (les regles ja ancoren per etiqueta, pas
  (a) fet i backfillat al 100%), **no el d'avui** (el pas (b), retirar la FK, no s'ha fet). No l'he
  tocada perquè no era al brief i perquè la redacció correcta depèn de si es dona (b) per imminent.
- **Grading, codis de mostra** (`BRW-CATALEG-v4`): el camp real és `codi_sistema` i els valors
  reals tenen la forma `EU_WOVEN_WOMAN_REGULAR`. Són dades de mostra, que la regla d'or permet.
- **Size library, `us.{items,models,rules,anchor}`**: **no hi ha cap endpoint «on s'usa» per a
  runs** (l'únic germà és `/poms/{id}/us/`). La secció pinta quatre comptadors que avui ningú no
  serveix. És T1 del report i demana backend, no maqueta.
- **Size library, l'ordre de talla** pinta l'índex de l'array, no el camp `ordre` — justament el que
  C4 va fer únic.
- **Cosmètic preexistent (les dues llistes):** `.t1` i `.cd` són spans inline dins de `.nm`, i el nom
  i el codi surten enganxats («Alpha EU — Women`ALPHA_EU_W`»). Ve de la v3, no del que he tocat.

## 7 · Fitxers

```
maqueta_fitting_v4.html        ← esmenat (77 línies)
maqueta_grading_rules_v4.html  ← esmenat (178 línies)
maqueta_size_library_v3.html   ← esmenat (84 línies)
maqueta_fitting_v4.png · shot_grading_regles.png ·
shot_grading_relacions.png · shot_sizelib.png     ← captures de verificació
```
