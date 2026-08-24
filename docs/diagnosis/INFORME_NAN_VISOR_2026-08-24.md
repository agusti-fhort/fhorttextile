# INFORME — REGRESSIÓ: NaN A L'ENCAIX, ELS DOS VISORS EN BLANC

**Data:** 24/08/2026 · **Patró B — URGENT.** Staging, `/var/www/ftt-staging`, branca `dev`.
**Cap push. Cap suite executada** (llei 23/08).
**Símptoma (Agus, 13:44):** els dos visors del 1383 en blanc — pestanya Patró i Taller
(`?file=20`). Zoom «NaN%», peu «NaN, NaN». Els panells laterals, bé.

---

## VEREDICTE EN TRES LÍNIES

> **Causa trobada, i és meva.** `5e6c1bec` (l'últim commit del sprint de cotes, el que
> recollia les troballes dels revisors) va reconstruir el `bbox` amb només les quatre
> cantonades per passar-lo a `escalaPerCabre` — i aquella funció **no llegeix les cantonades:
> llegeix `bbox.ample` i `bbox.alt`**, dos camps derivats que no hi vaig copiar.
>
> `Math.max(undefined, 1)` és NaN, i el NaN baixava sencer fins al zoom i a la posició.
> **Cap dada del banc hi té res a veure**: ni els offsets, ni els 14 ancoratges vells, ni el
> camp nou. Era aritmètica de la vista.
>
> **Corregit i verificat amb navegador de debò**, els dos visors: zoom 56% i 37%, els dos
> llenços pintant, cap NaN, zero errors de consola. **Commit `f43308b4`.**

---

## 1 · LA CADENA, DE DALT A BAIX

`patternGeometry.js` — el que `bboxDePeces` torna de sempre:

```js
return { minX, minY, maxX, maxY, ample: maxX - minX, alt: maxY - minY }
```

…i el que `escalaPerCabre` en llegia:

```js
const w = Math.max(bbox.ample, 1)     // ← NO les cantonades: els camps DERIVATS
const h = Math.max(bbox.alt, 1)
```

`PatternViewer.jsx:209`, tal com el va deixar `5e6c1bec`:

```js
const z = clampZoom(escalaPerCabre({ minX, maxX, minY, maxY }, w, h))
```

| Pas | Valor |
|---|---|
| `bbox.ample` de l'objecte fabricat | `undefined` |
| `Math.max(undefined, 1)` | **NaN** |
| `Math.min(NaN, NaN)` | NaN |
| `clampZoom(NaN)` = `Math.max(0.02, Math.min(40, NaN))` | **NaN** ← no filtra |
| `setZoom(NaN)` | control: **«NaN%»** |
| `setPos({x: NaN, y: NaN})` | peu: **«NaN, NaN»** |
| Konva amb `scaleX = NaN` | **llenç en blanc** |

**Per què els panells anaven bé:** peces, POMs i relacions es pinten des dels seus propis
payloads i no passen per l'encaix. Només el llenç depèn del zoom i de la posició — i és el
que feia que semblés un problema de dades quan era de vista.

### La prova, contra el mòdul d'abans del commit culpable

Amb el bbox real del PF20 (`minX 891 · maxX 2029 · minY 731 · maxY 1376`):

| Entrada | `escalaPerCabre` **ABANS** (`5e6c1bec~1`) | **ARA** |
|---|---|---|
| bbox sencer (amb `ample`/`alt`) | 0,6678 | 0,6678 |
| **bbox a mitges** (el que es fabricava) | **NaN** | **0,6678** |

I el guard nou d'entrada, amb un punt brut al mig:
`bboxDePeces([{x:10,y:10}, {x:null,y:5}, {x:30,y:40}])` → `{minX:10, maxX:30, minY:10, maxY:40}`.
El punt brut se salta; abans hauria fet `minX = null` i, d'allà, `ample` a la brossa.

### Qui el va introduir, i per què hi era

`5e6c1bec` arreglava una bandera REAL del revisor-diff: arrossegar una cota reenquadrava el
llenç, perquè `encaixar` depenia de l'OBJECTE `bbox`, que `bboxDePeces` refà a cada canvi
d'identitat de `pieces`. La solució —dependre de les quatre xifres— és correcta i es queda.
El que va fallar és el pas del mig: **fabricar un objecte per passar-lo a una funció sense
mirar què en llegia.**

---

## 2 · EL FIX (`f43308b4`)

No al lloc on va petar, sinó allà on es podia tornar a petar.

| # | On | Què |
|---|---|---|
| 1 | `escalaPerCabre` | **Dedueix `w`/`h` de les cantonades.** Demanava dades que ja tenia; ara no en demana cap que no pugui deduir, i qualsevol cridant amb només les cantonades funciona |
| 2 | `bboxDePeces` | **Cada punt passa per `Number.isFinite`.** Un sol punt brut contaminava el mínim i el màxim. Comparar sense guard no salva: `null < Infinity` és cert |
| 3 | `escalaPerCabre` · `clampZoom` | **Cap dels dos deixa sortir un NaN.** Amb entrada no mesurable, escala 1 |
| 4 | `PatternViewer:209` | La crida passa l'objecte **sencer**. Ja no cal (l'1 ho cobreix), però fabricar-ne un d'incomplet és el que va cegar els visors |

> 🔑 **LA LLIÇÓ, per si torna a passar:** *tot `reduce`/`min`/`max` de bbox amb guard d'entrada,
> i tot valor que arribi a una transformació de llenç amb guard de sortida.* **Un element brut
> mai ha de cegar el visor.** Un patró a escala equivocada és un problema que es veu i es
> diagnostica; un llenç en blanc amb «NaN%» no diu ni què ha passat ni on.

**MAI un revert cec del tram.** El commit culpable arreglava quatre vetos i dues banderes
altes —entre elles, que la cota s'empassava el clic de l'imant—; tirar-lo enrere hauria
canviat un visor en blanc per un Taller que no ancora.

---

## 3 · EL FORAT DE L'SMOKE — que també és troballa

L'smoke del sprint va donar **verd** i no ho era. Dues raons, i totes dues són meves:

**1 · No va obrir mai un navegador.** Era `curl` contra l'API: el vocabulari de mètodes, el
payload de geometria, el rebot d'un eix invàlid, el PATCH de l'offset i el seu desfet. Tot
correcte, i **tot cec al render**. La regressió és a `scaleX` de Konva: no hi ha resposta HTTP
que la pugui delatar.

**2 · El commit culpable no es va smokejar.** `5e6c1bec` va entrar DESPRÉS de l'últim smoke
(11:20/11:25 UTC). El que es va córrer després va ser `npm run build` verd i un `curl` a
`metodes/` — cap dels dos renderitza res. **Un `build` verd no és una pantalla viva**, que és
precisament la lliçó que aquest mateix projecte ja tenia escrita per al backend
(«build verd ≠ backend viu») i que no s'havia traduït al front.

### El que s'ha fet servir ara, i que queda muntat

nginx té **auth bàsica sobre l'HTML** de staging (`/etc/nginx/sites-enabled/ftt-staging:12`) i
`auth_basic off` per a l'API — que és exactament per què el `curl` passava i el navegador es
menjava un **401 de nginx** abans d'arribar a l'app.

La sortida, sense tocar cap configuració ni buscar cap credencial: **servir el `dist` real i
proxiar `/api` al gunicorn amb el Host del tenant** (el patró que la casa ja fa servir per a la
QA de pantalla). Amb això, Chromium headless veu l'app de debò amb dades de debò.

| Visor | zoom | canvas | píxels pintats | NaN | consola |
|---|---|---|---|---|---|
| Taller (`?file=20`) | **56%** | 1212×839 | **45.033** | cap | 0 errors |
| Pestanya Patró (`?tab=Patró`) | **37%** | 770×560 | **26.790** | cap | 0 errors |

> ⚠️ Dues coses de mètode que han sortit del propi smoke i que val la pena que constin:
> · El tab es tria per `?tab=Patró` **amb accent** (`SECCIONS_MODEL`). Amb `?tab=patro` la
>   pàgina cau al tab per defecte i el visor no es munta — i un smoke mal parametritzat torna
>   «en blanc» per un motiu que no és el que es busca. Hi vaig caure a la primera passada.
> · Obrir el Taller **reobre** la tasca `pattern_digit` que ja existia (la 380, del 23/08).
>   No se n'ha creat cap de nova: verificat.

---

## 4 · ELS CONTROLS

| Control | Resultat |
|---|---|
| `npx eslint` (els 2 fitxers tocats) | **0 errors** · 5 avisos a `PatternViewer.jsx`, tots anteriors; `patternGeometry.js` a 0 |
| `npm run build` | **verd** |
| Suites | **cap executada** (llei 23/08) |
| `dist` desplegat | porta el fix, i l'smoke corre contra ELL |
| Backend | **no tocat** en aquest fix |
| Banc del 1383 | **intacte**: 14 ancoratges, tots els offsets a 0 |

---

## 5 · EL QUE QUEDA OBERT

1. 🚩 **L'smoke de pantalla no és cap gate: és un script que he muntat ara i viu al
   scratchpad.** Mentre no visqui a `ops/qa/`, el proper tram tornarà a donar verd sense mirar
   cap llenç. Convertir-lo en banc (les dues rutes, el recompte de píxels i el «cap NaN al
   text») és mitja hora i tanca el forat de debò.
2. 🚩 **`ops/qa/qa_auditoria_computats.py` segueix sense córrer-se** —ve del tram anterior—, i
   ara sabem per què costa: demana sessió viva darrere de l'auth bàsica. El proxy d'aquest
   informe també li serviria.
3. 🚩 **Cap test cobreix `bboxDePeces`/`escalaPerCabre`.** Són funcions pures, sense BD i sense
   React: el banc més barat del repo. Un cas per forma (sencer, a mitges, buit, amb un punt
   brut) hauria atrapat això en un segon. **No s'ha escrit aquí** perquè el tram és una
   urgència i el brief acota; queda proposat.
