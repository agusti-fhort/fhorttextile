# F4.2-BIS · ELS ROLS DE VORA ES DECLAREN AL TALLER — informe de tancament

> Sprint del **2026-09-03**, worktree `/var/www/ftt-f42`, branca `f42-edge-landmarks`.
> **Cap push.** Ordre d'Agus: «no puc comprovar la mida si no puc navegar».

---

## 0 · EL TITULAR

**Fet, i verificat amb ULLS.** El panell de rols de vora viu ara al Taller, la selecció va
lligada en tots dos sentits amb el llenç, i la mida del tram assenyalat es llegeix sobre el
patró. El gest complet —triar peça → assenyalar tram → acceptar → gravar— s'ha corregut
sobre el **CUELLO real del 837** i ha escrit **exactament una fila**, la que tocava.

**Cap canvi de backend.** La premissa de la Fase A del brief («si F4.2 ja torna la
geometria pintable, res a tocar») s'ha verificat abans de construir i es compleix.

---

## 1 · FASE A · PER QUÈ EL BACKEND NO S'HA TOCAT

El brief admetia estendre la resposta si no servia geometria pintable. **No cal**, i es va
comprovar abans d'escriure cap línia:

| Comprovació | Resultat |
|---|---|
| `geometry/` serveix TOTS els segments o només els declarats? | **TOTS** (`serializers.py:325`, `piece.segments.all()`, sense filtre d'origen) |
| Què en serveix? | `id`, `vora`, `t_inici`, `t_fi`, `tipus_vora`, `origen`, `nom` |
| Els `segment_id` d'`edge-roles/` són d'aquest conjunt? | **Sí**, mesurat al 837: `{1511,1512} ⊆ ids de geometria` |
| Hi ha resolutor al front? | **Sí**: `patternGeometry.puntsDelSegment`, en ús des de S6 |

🔑 **El front no CALCULA geometria: la RESOL.** Un `PatternSegment` es desa com a fracció de
vora precisament per poder-lo ancorar sense clavar-lo a un índex de vèrtex
(`models.py:367`), i `puntsDelSegment` és **la mateixa funció amb què el Taller pinta els
trams declarats des de S6**. Demanar al servidor una polilínia que aquí es dedueix del que
ja ha enviat seria una segona font per a la mateixa veritat — exactament el que la llei
prohibeix.

Recompte de segments servits pel 837 (v3): CUELLO 10 auto + 2 natural + 1 declarat ·
DELANTERO 28+16+14 · ESPALDA 24+12+11 · MANGA 9+4+4 · TAPETA 8+4+0.

---

## 2 · FASE B · EL PANELL AL TALLER

### B1 · MOGUT, no duplicat

`PieceEdgeRoleList` és **el mateix component**. Guanya tres props (`voraSel`, `onVoraSel`,
`nomesPeca`) i el tab Patró en perd l'ús. **El filtre per peça viu DINS del component**, no
al pare: és el que fa que segueixi sent una sola llista en comptes de dos bessons que
divergirien al primer canvi (llei «no more patches»).

Va **sota la llista de peces**, perquè n'és la continuació: es bategen les vores DE la peça
seleccionada, i la selecció que mana és la mateixa (`pecaSel`). Sense peça triada, el panell
diu què falta en comptes de quedar-se buit.

### B2 · EL CABLATGE, ALS DOS SENTITS

| Gest | Efecte |
|---|---|
| Fila assenyalada (clic o cursor a sobre) | El tram s'encén al llenç amb `KONVA_COL.tramSel`, gruix 6/zoom, i **porta la mida al costat** |
| Clic sobre un tram al llenç | La fila s'enfoca i fa `scrollIntoView({block:'nearest'})` |
| Zoom/pan | **No s'han tocat**: són els del Taller de sempre |

🚨 **La mida només al tram ASSENYALAT.** Una xifra a cada tram tornaria a fer il·legible
justament el que aquesta pantalla ve a resoldre: el DELANTERO en té setze.

🔑 **`--tram-sel` (CSS) i `KONVA_COL.tramSel` són el mateix taronja.** El mateix tram i el
mateix èmfasi als dos costats de la pantalla, i és el token que la paleta ja declarava per a
«assenyalar: èmfasi, no identitat».

**Dos colors d'IDENTITAT** i no un: `vora` (verd blau, gravat) i `voraProposta` (ambre,
**ratllat**) — la mateixa gramàtica que les costures proposades d'A2, on ratlles vol dir
«encara no és del patró».

### B3 · El gate de tasca

Es respecta **tal com és**. La captura ho ensenya: *«Tasca "Patró digitalització" en curs»*.
Declarar rols és feina i corre dins del rellotge — coherent amb `PatternTab.jsx:26`.

### B4 · El tab Patró

La llista **es retira**. Hi queden la identitat de peces i **els landmarks al visor**, que
són LECTURA: mirar un patró no ha d'obrir cap tasca. La crida a `edge-roles/` hi queda
perquè els landmarks hi viatgen; el que se n'ha anat és tota manera d'escriure-hi, i les N
crides de vocabulari que ja no llegia ningú.

---

## 3 · UN BUG PROPI, TROBAT I CORREGIT

🚨 **Els landmarks que vaig pintar al tram anterior (commit `40a31775`) sortien
EMMIRALLATS.** L'`Stage` va amb `scaleY={zoom}` POSITIU: no hi ha cap flip, i és cada forma
la que nega la seva pròpia y (`[p.x, -p.y]`, i 18 llocs més). El meu bloc feia `y={lm.y}` i
compensava l'etiqueta amb un `scaleY={-1}` que no desfeia res. El punt queia a l'altra banda
de l'eix i el text sortia del revés.

Corregit a `01002fc0`. **No ho hauria vist sense mirar el llenç**: cap test, cap build i cap
lint el veien, i el tram anterior el va donar per bo.

---

## 4 · EL FUM AMB ULLS

`ops/qa/f42bis_taller_vores.mjs` — CDP cru contra el `chrome-headless-shell` de playwright
(Node 22 ja porta `WebSocket`). No mesura una maqueta: obre el **Taller real del 1383**.

### 4.1 · El muntatge, i per què cap procés viu no s'ha tocat

| Peça | On |
|---|---|
| Django del WORKTREE | `127.0.0.1:8137`, `/proc/…/cwd → /var/www/ftt-f42/backend` |
| Vite dev, mode `smoke` | `127.0.0.1:5199`, proxy `/api` → 8137 |
| JWT | `TenantTokenObtainPairSerializer`, amb el claim `tenant_schema=fhort` |
| Config del proxy | **efímera**, esborrada en acabar; el `vite.config.js` del repo no s'ha tocat |

🚨 **EL PORT QUE VAIG TRIAR PRIMER NO ERA MEU.** El 8099 el té un Django d'una ALTRA sessió,
arrencat el **4 d'agost** i servint `/var/www/ftt-staging/backend`. Els meus endpoints hi
donaven **404** i era correcte: parlava amb el codi vell d'un altre procés. Un fum que tria
un port sense mirar qui el té acaba mesurant la feina d'algú altre — i el 404 tenia tota la
pinta d'un bug meu. Es comprova amb `/proc/<pid>/cwd`, que és la mateixa llei que
`ftt-backend-desplegat-vs-disc` diu per al gunicorn.

🚨 **`.env.development` cablava `VITE_API_URL=http://localhost:8000`**: en mode dev el
navegador no passava pel proxy i les crides no arribaven enlloc. Es corre amb `--mode smoke`,
que no carrega cap `.env` i deixa el `baseURL` RELATIU (que és el defecte que `api/base.js`
va construir a posta).

🚨 **Dues vegades la SONDA va mentir abans que la pantalla**, i totes dues queden escrites al
fitxer de QA:
1. Apuntar a «qualsevol node amb el text de la peça» clicava un contenidor sense handler: el
   fum donava per triada una peça que no ho estava. La peça es tria amb un `<button>`
   (`PieceList.jsx:24`).
2. El headless pinta en **anglès** si no se li posa l'idioma, i la clau **NO** és
   `i18nextLng` sinó **`fhort.lang`** (`i18n/index.js:26`).

### 4.2 · El marcador

```
pantalla: TALLER
tria de peça 837.CUELLO: clicada
panell: 2 files · desplegable = [sense rol · Unió de coll · Costura lateral del coll ·
                                 Costura del centre del coll]
canvas: 1212 × 839
accepta-tots: «Accepta les 1»  ·  grava: clicat
re-correguda: «sense botó accepta» · «BOTÓ DESACTIVAT (res per gravar)»
```

🔑 El desplegable ofereix **només el vocabulari del coll**: el guard de `needs_piece_role`
(D3) es veu a la pantalla, no només al test.

### 4.3 · Les captures (`docs/diagnosis/f42bis_smoke/`)

| Fitxer | Què s'hi veu |
|---|---|
| `01_taller_vora_illuminada.png` | El Taller sencer, el rellotge en curs, el panell i el coll encès |
| `02_coll_mida_al_llenc.png` | El tram assenyalat **gruixut i sencer**, el germà **ratllat**, i **«52,6 cm»** llegible |
| `03_panell_fila_enfocada.png` | «1 dits · 0 proposats · 1 sense proposta» · fila 1 amb la barra taronja i el **verd de confirmat** · fila 2 amb la **ⓘ del silenci** |

### 4.4 · Dos defectes que NOMÉS es veien mirant

Els dos van sortir de la captura i estan corregits (`acb66e64`):

1. 🚨 **La mida queia damunt de la cota d'un POM** i les dues xifres es feien un garbuix.
   Amb la funció construïda i el llenç pintat, l'ordre que va originar aquest tram quedava
   sense complir. Ara la xifra s'aparta cap afora seguint la direcció del centre de la peça
   al tram —com una cota de CAD— i va sobre **caixa opaca amb vora**, perquè «afora» no és
   cap garantia de buit en una niada.
2. El número del tram quedava **sota** la barra de la fila seleccionada. `paddingLeft`
   permanent (posar-l'hi amb la selecció faria saltar la fila 3 px sota el cursor).

---

## 5 · LA VERIFICACIÓ SQL DE L'ESCRIPTURA

**Abans:** `edge_role` confirmats = **0** als dos tenants.

**Després del `accepta-tots` + `grava` sobre el CUELLO:**

```
  id  | nom_block  | origen  | vora |   t0   |   t1   | nom |   edge_role
------+------------+---------+------+--------+--------+-----+---------------
 1511 | 837.CUELLO | natural |    1 | 0.2276 | 0.7722 |     | collar_attach
(1 row)

total_amb_edge_role | 1
los                 | 0
```

**S'ha escrit NOMÉS on toca, i es pot dir en quatre punts:**
1. **Una fila i prou.** El segon tram del coll (1512) segueix a NULL — el proposador hi calla
   perquè el GTI 28 no té `collar_outer_edge` (forat de catàleg ja informat a F4.2 §4.D1),
   i el que calla no s'escriu.
2. **La geometria intacta**: `origen`, `vora`, `t_inici`, `t_fi` i `nom` són els d'abans.
   `UPDATE_FIELDS == ['edge_role']` ho fa complir, i el test ho afirma.
3. **Cap altra peça, cap altre tenant.**
4. **Idempotent**: la re-correguda troba el botó desactivat i **no torna a escriure**
   (recompte encara 1).

---

## 6 · VERD

| Control | Resultat |
|---|---|
| `manage.py check` | net |
| `npm run build` | net (còpia aïllada del worktree, mai in situ) |
| `npm run lint` sobre els fitxers tocats | **0 errors** |
| i18n ca/en/es | **paritat GLOBAL** (1 clau nova: `edges_pick_piece`) |
| `tests_edge_labeler` | **`Ran 25 tests in 95.967s · OK`** — cap regressió |

### 6.1 · Sobre els tests

Els tests del component reubicat **no calien tocar**: `PieceEdgeRoleList` no en tenia de
propis (els seus són els del servei i del proposador, que no han canviat). El cablatge
selecció↔llenç **no té test de component** —el harness no en munta cap de React— i per això
va documentat al fum amb captures, tal com el brief preveia.

---

## 7 · FRONTERES RESPECTADES

- **Cap canvi al proposador ni als landmarks** (tret del bug de pintura, §3).
- **Cap endpoint nou, cap canvi de backend.**
- **L'ÚNICA escriptura de BD és la declarada al brief**: 1 fila d'`edge_role` al CUELLO,
  feta des de la UI pel camí humà.
- ⚠️ **Entrar al Taller obre la tasca `pattern_digit`**, i el fum hi ha entrat. No és un
  efecte lateral que hagi buscat: és el que la pantalla FA per disseny, i el brief demana
  precisament que el gate es respecti tal com és. El model és el banc de QA 1383.
- **El Taller no guanya cap altra funció.**
- **Cap push.** Els processos del fum (Django 8137, vite 5199) s'aturen en acabar; el
  Django del 8099 d'una altra sessió **no s'ha tocat**.

---

## 8 · EL RESTART

Igual que a F4.2, i pel mateix motiu verificat: **no s'ha reiniciat staging**. El gunicorn
viu serveix `/var/www/ftt-staging/backend`, que segueix a `73574dcc` i **no conté ni una
línia d'aquest tram**; aquesta feina viu a `f42-edge-landmarks`, al worktree i sense merge.
Reiniciar rellançaria exactament el mateix codi que ja corre.

El que sí que s'ha fet és el que un restart pretén provar, i millor: **el codi d'aquesta
branca s'ha arrencat de debò** (Django propi al 8137 + vite al 5199), s'ha navegat amb un
navegador real i les captures de §4.3 en són l'acta. El merge i el desplegament són de
l'Agus.
