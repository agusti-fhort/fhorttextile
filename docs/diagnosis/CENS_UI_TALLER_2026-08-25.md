# Cens de la UI actual del Taller de patró

**Data:** 2026-08-25 · **Fil:** S46-MOTOR · Patró A · previ al mockup definitiu
**Ordre d'Agus (25/08):** *«cal integrar-lo amb coses que ja tenim i que són valuoses,
com la visualització de capes i altres»*
**Captures:** `captures_ui_taller_2026-08-25/` (5 PNG)

> **Read-only.** Cap escriptura al repo fora d'aquest informe i la carpeta de captures
> (**sense commitar**). Cap `systemctl`, cap servei tocat, cap test executat, cap
> escriptura a BD — només `SELECT`. El script de captura viu al **scratchpad**, no al repo.

---

## 0 · El resum en set línies

1. **La UI del Taller és molt més del que el mockup v1 dona per fet: 7 995 línies** a
   `pages/TallerPatro.jsx` (1 967) + 16 components a `components/pattern/`.
2. 🔑 **La visualització de capes JA existeix i és bona**: **7 commutadors**
   (tall · cosit · internes · mirall · piquets · fil · punts) amb una llei pròpia —
   *una capa que el fitxer no porta no s'ofereix* — i paleta literal `KONVA_COL`. §2
3. 🔑 **Les cotes CAD estan FETES**: 4 mètodes (`recta · vora · ortogonal · projeccio`)
   amb la gramàtica servida pel **servidor**, i `cota_offset_mm` és **presentació pura,
   mai mesura**. §4
4. 🚨 **Dues premisses del brief no es compleixen.** **`GarmentPOMMapEditor` NO existeix**
   (mai construït; només una nota d'integració S7 sense aplicar) i **`/garment-pom-map`
   no és cap ruta**. §7
5. 🔑 **Reconciliació d'identitat:** el «model 837», el «1383» i «TRV-SS27-0001» són
   **el mateix**: model `1383`, `codi_intern = TRV-SS27-0001`, `nom_prenda = 837 VESTIT`.
6. **Contrast R1-R5:** 2 FET · 5 PARCIAL · 2 NOU. **Res del disseny v2 és terra verge:
   tot té una arrel a la UI actual.** §9
7. 🚩 **Les captures són reals però amb stub**: el JWT de QA segueix bloquejat per al
   meu usuari. Les dades són de staging (SQL), el bundle i el CSS són els de producció.
   El que NO he pogut capturar es diu a §1.2 — **i cal el token per tancar-ho**.

---

## 1 · Mètode de les captures, i què no cobreixen

### 1.1 Com s'han fet

El JWT de QA **l'agent no el pot emetre** (classificador; llei
`ftt-qa-token-jwt-bloquejat`), i un `goto` directe a staging captura **el 401 d'nginx**.
S'ha seguit el patró ja establert a `ops/qa/qa_niada_cosit_1383.py`: **servir el bundle
real de `frontend/dist`** —el mateix que nginx publica— i **stubejar `/api/`**.

> ✅ **El stub NO és inventat.** El payload de `geometry/` s'ha generat amb un `SELECT`
> contra la BD viva reproduint la forma de `PatternGeometrySerializer._piece`
> ([serializers.py:221-300](../../backend/fhort/patterns/serializers.py#L221)):
> **PatternFile 20 · v3 · polypattern · model 1383**, amb les coordenades, els piquets,
> els trams i el fil de veritat. Les 5 peces del 837 i els seus recomptes (1 224 punts al
> coll, 20 de gir, 1 196 de corba) són **dades d'staging**.

⚠️ **Primer intent: verd fals.** Amb tres claus de payload equivocades
(`naturals` ≠ `segments_naturals`, `metodes` amb `codi` i no `valor`, i el detall sense
`pieces`), la pantalla queia a l'`AppErrorBoundary` i la captura sortia amb «S'ha produït
un error inesperat». **La llei de mirar sempre la captura abans de donar-la per bona
(`ftt-qa-token-jwt-bloquejat`) ha estat el que ho ha caçat.**

### 1.2 ✅ Les 5 captures pendents, TANCADES amb el token (12:45-12:51 UTC)

Amb el JWT d'Agus, les captures 06-10 s'han fet **contra l'API VIVA** (proxy a
`127.0.0.1:8001` amb `Host` + `Bearer`), no amb stub: el que s'hi veu són **les dades
reals d'staging**.

> 🔒 **Read-only blindat, i va caldre.** El proxy **només deixa passar `GET`**; qualsevol
> `POST`/`PATCH`/`DELETE` s'intercepta i **no arriba al servidor**. A la primera passada
> es van bloquejar **dos `POST /api/v1/models/1383/open-task/`**: entrar al Taller *sense*
> paràmetre de tasca **obre o reprèn un rellotge de domini**
> ([TallerPatro.jsx:242-245](../../frontend/src/pages/TallerPatro.jsx#L242)).
> El paràmetre correcte és **`?task_id=`** (no `?task=`,
> [:42](../../frontend/src/pages/TallerPatro.jsx#L42)); amb
> `?task_id=380` (la tasca `pattern_digit` que el model **ja tenia**, en `Paused`) la
> segona passada va registrar **cap escriptura**. Una QA ingènua hauria escrit al domini.

**El token no s'ha desat enlloc**: ha viatjat només per variable d'entorn al procés, mai a
un fitxer ni a l'informe.

## 2 · 🔑 La visualització de CAPES — el «valuós» explícit d'Agus

📄 [PatternViewer.jsx:1117-1192](../../frontend/src/components/pattern/PatternViewer.jsx#L1117) (`Controls`)
· estat a [:177-181](../../frontend/src/components/pattern/PatternViewer.jsx#L177)
· paleta a [:33-56](../../frontend/src/components/pattern/PatternViewer.jsx#L33)
📸 `01_taller_estat_normal.png` · `02_capes_nomes_tall.png` · `03_capes_nomes_cosit.png` · `04_capes_totes_amb_punts.png`

**Set commutadors**, cadascun amb la seva icona Tabler:

| capa | icona | color `KONVA_COL` | què pinta |
|---|---|---|---|
| `cut` | `ti-line` | `#1d1d1b` | contorn de tall — el que es retalla |
| `sew` | `ti-needle-thread` | `#1f6feb` | línia de cosit |
| `internal` | `ti-line-dashed` | `#868685` | línies internes |
| `mirror` | `ti-flip-horizontal` | `#8250df` | eix de mirall |
| `notch` | `ti-scissors` | `#a32d2d` | piquets (rombe) |
| `grain` | `ti-arrow-narrow-up` | `#3b6d11` | fil de la roba |
| `punts` | `ti-point` | gir `#3b6d11` · corba `#bf8700` | vèrtexs, **amb la seva semàntica** |

> 🔑 **La llei que el mockup ha de conservar**, escrita al codi
> ([:1119-1120](../../frontend/src/components/pattern/PatternViewer.jsx#L1119)):
> *«Les capes que el fitxer NO porta no s'ofereixen: un toggle que no fa res és pitjor que
> no tenir-lo, perquè fa pensar que la capa hi és i està amagada.»*
> Ho resol `capesPresents(pieces)` ([patternGeometry.js:415-424](../../frontend/src/components/pattern/patternGeometry.js#L415)).

> 🔑 **`KONVA_COL` és l'ÚNICA excepció autoritzada a «colors via tokens, mai hex»**
> (CLAUDE.md): el canvas no resol `var(--)`. I **no és la paleta de l'SVG**: *«allà és un
> document, aquí és una eina»*.

**El commutador és visualment un estat, no un botó**: encès → fons `var(--sel)`, vora
`var(--gold)`, opacitat 1; apagat → opacitat 0,55 ([:1130-1135](../../frontend/src/components/pattern/PatternViewer.jsx#L1130)).

---

## 3 · El visor: gestos, zoom i selecció

📄 [PatternViewer.jsx](../../frontend/src/components/pattern/PatternViewer.jsx) (1 246 línies)

| capacitat | estat | rastre |
|---|---|---|
| **READ-ONLY estricte**: cap punt s'arrossega | ✅ | [:15](../../frontend/src/components/pattern/PatternViewer.jsx#L15) |
| **Pan propi** (no el `draggable` de Konva): espai o botó del mig | ✅ | [:168-171](../../frontend/src/components/pattern/PatternViewer.jsx#L168) |
| **Zoom** amb sostre alt a posta: *«els punts de gir d'una pinça viuen a 6 mm l'un de l'altre»* | ✅ | [:57-60](../../frontend/src/components/pattern/PatternViewer.jsx#L57) |
| **Encaixar** + percentatge en viu | ✅ | `Controls` |
| **Selecció de peça** i **atenuació de les altres** (`opacity 0.25`) | ✅ | [:466](../../frontend/src/components/pattern/PatternViewer.jsx#L466) · [:1052](../../frontend/src/components/pattern/PatternViewer.jsx#L1052) |
| **Imant**: el cursor s'enganxa al vèrtex; *«marcar un POM a ull seria un dibuix a sobre del patró»* | ✅ | [patternGeometry.js:238-255](../../frontend/src/components/pattern/patternGeometry.js#L238) |
| **Tecla d'invertir l'arc** en declarar un tram | ✅ | [patternGeometry.js:395-412](../../frontend/src/components/pattern/patternGeometry.js#L395) |
| **Barra d'estat** amb coordenades i mida del tram sota el cursor | ✅ | [:1195](../../frontend/src/components/pattern/PatternViewer.jsx#L1195) |
| **Els controls es teletransporten** a la barra del pare (portal) | ✅ | [:149-153](../../frontend/src/components/pattern/PatternViewer.jsx#L149) |

**Punts pintats: TOTS.** Al 837, `837.CUELLO` en té **1 224 (20 de gir · 1 196 de corba)**.
El toggle `punts` és tot-o-res; **la semàntica hi és** (gir quadrat verd · corba x groga ·
piquet rombe vermell) però **no hi ha filtre «només semàntics»**. → R2, §9.

**Cinc modes** ([TallerPatro.jsx:76](../../frontend/src/pages/TallerPatro.jsx#L76)):
`view · pom · seg · pinca · sew`, i **l'ordre dels botons és l'ordre del flux**
(*«PRIMER DECLARAR, DESPRÉS COSIR»*, [:1577](../../frontend/src/pages/TallerPatro.jsx#L1577)).

---

## 4 · 🔑 El panell de POMs i les cotes CAD (sprint 24/08) — FET

📄 [ModelPomList.jsx](../../frontend/src/components/pattern/ModelPomList.jsx) (682 línies)
· vocabulari a [patterns/models.py:517-535](../../backend/fhort/patterns/models.py#L517)
📸 `01_taller_estat_normal.png` (panell «POMS DEL MODEL · 0 DE 0 COL·LOCATS»)

**Els 4 mètodes, amb la gramàtica servida pel SERVIDOR** (no una llista al `.jsx`:
*«una llista escrita a mà dins d'un `.jsx` deriva dels `choices` del model i ningú no se
n'assabenta»*, [endpoints.js:~350](../../frontend/src/api/endpoints.js)):

| mètode | mode de recepta | àncores |
|---|---|---|
| `recta` | `points` | `a`, `b` |
| `vora` | `points` | `a`, `b` |
| `ortogonal` | `ortogonal` | `ref_a`, `ref_b`, `p` |
| `projeccio` | `projeccio` | `a`, `b` + opció `eix` (`AUTO`/`H`/`V`) |

**Lleis que el mockup ha de respectar:**
- 🔑 **El VALOR no s'envia mai**: s'envia la recepta i el servidor la resol sobre la
  geometria. *«Un valor teclejat no seria una mesura del patró, seria una opinió sobre el
  patró.»*
- 🔑 **`cota_offset_mm` és PRESENTACIÓ, MAI MESURA**
  ([models.py:536-554](../../backend/fhort/patterns/models.py#L536)): desplaçament
  perpendicular en mm; **no pot tocar `valor_mesurat_cm`**. I **no és
  `models_app.POMPlacement`** — *«comparteixen la paraula “cota” i res més»*.
- **Reobrir, mai esborrar-i-crear**: `PATCH` sobre el mateix `PatternPOM` i el servidor
  recalcula. *«Corregir on és una mesura no és tornar-la a ancorar.»*
- **Esborrat en bloc** amb `{esborrats, retinguts}`: *«qui n'ha marcat divuit no ha demanat
  que un de retingut en salvés disset»*.

**Accions del panell** (claus i18n): `act_point` · `act_unpoint` · `act_reanchor` ·
`act_delete` · `act_menu`, més una fitxa d'informació del POM (nom local, `name_en`,
categoria, referència, tolerància, d'on ve).

---

## 5 · «Buscar propostes» i els cosits

📄 [RelationsPanel.jsx](../../frontend/src/components/pattern/RelationsPanel.jsx) (911 línies)
· [ProposalsPanel.jsx](../../frontend/src/components/pattern/ProposalsPanel.jsx) ·
[DartProposalsPanel.jsx](../../frontend/src/components/pattern/DartProposalsPanel.jsx) ·
[SewEditor.jsx](../../frontend/src/components/pattern/SewEditor.jsx)
📸 `01_taller_estat_normal.png` (panell «RELACIONS»)

**El gest sencer, tal com és avui:**
1. **El Taller s'obre amb el grup BUIT i un botó** — decisió explícita (F/T1): *«A2 no és
   una lectura, és un motor que opina sobre tot el patró; córrer-lo sol, en obrir, feia que
   la llista aparegués sense que ningú l'hagués demanada»*
   ([TallerPatro.jsx:164-166](../../frontend/src/pages/TallerPatro.jsx#L164)).
   A la captura: *«El motor encara no ha mirat aquest patró»* + **`Buscar propostes`** (`ti-wand`).
2. Cada proposta ensenya **el desglòs dels senyals** que l'han produïda (piquets, longitud,
   noms) amb el diferencial en cm — no una xifra de confiança sola.
3. **Confirmar** (`sew.confirmarProposta`) · **rebutjar** (`sew.rebutjarProposta`, i el «no»
   queda desat a `SewRejections` i es pot **desfer**, `ti-arrow-back-up`).
4. **Pinces**: `sew.pinca` crea els dos costats i la costura **en UNA transacció** — *«fer-ho
   amb tres crides podia fallar a la tercera i deixar dos trams orfes»*.
5. **Tolerància**: `tolerance.accept/unaccept` amb nota — una costura que no casa es pot
   **acceptar amb acta**.
6. **L'estat d'una costura no es desa**: el servidor el recalcula sobre la geometria viva,
   *«perquè una costura que casava i ja no casa ho ha de dir»*.

---

## 6 · Identitat de les peces

📄 [PieceIdentityList.jsx](../../frontend/src/components/pattern/PieceIdentityList.jsx) (246 línies)
· endpoints `identificar/` i `identitat/`

**Camps actuals:** `nom` (bateig del model; el del fitxer queda de *placeholder*) ·
`piece_role` (picker del catàleg de rols, I2a) · `lateralitat` · `ordinal` · `estat_peca`
(**producció** vs **treball**).

**Flux:** identificació **EN BLOC** — *«identificar un patró és un sol gest, i qui mira un
davanter el mira contra l'esquena que té al costat»*—, amb `confirm` que hi deixa **acta**.
🔑 **El verd surt del SERVIDOR, no del navegador**: *«un estat que viu a localStorage diu
que algú va confirmar en AQUELL ordinador, que no és el que la pregunta vol saber.»*

> 🚨 **Correcció a la primera versió d'aquest informe.** Hi deia que *«les 5 peces tenen
> `piece_role` buit i el patró encara no està identificat»*. **És FALS**, i l'error és de
> mètode: ho vaig afirmar des del meu propi **stub** (on jo havia posat `piece_role: null`),
> no de la BD. Mesurat: `piece_role_id` = **6 · 1 · 2 · 4 · 20** — les cinc peces **estan
> identificades** (Coll · Davant · Esquena · Màniga · Tapeta), i la captura
> `09_identitat_peces.png` ho ensenya.
>
> El que **sí** és buit: `nom` (el bateig del model, que cau al *placeholder* del fitxer) i
> `lateralitat`. `estat_peca` = `produccio` a les cinc.

---

## 7 · 🚨 Dues premisses del brief que no es compleixen

### 7.1 `GarmentPOMMapEditor` **no existeix** — mai s'ha construït

No hi ha component, ni ruta, ni import. **L'únic rastre a tot el repo** és
`frontend/src/components/SPRINT_S7_INTEGRATION.txt:5-10`, una **nota d'integració que mai
es va aplicar**:

```
import GarmentPOMMapEditor from './pages/GarmentPOMMapEditor'
<Route path="/garment-pom-map" element={<GarmentPOMMapEditor />} />
```

`App.jsx` **no registra** cap `/garment-pom-map`. **No hi ha res a retirar (G4): no hi ha
res.**

**El que sí existeix i cal conservar:** el model `GarmentPOMMap` és **viu** al backend
([pom/views.py:473](../../backend/fhort/pom/views.py#L473), router
`garment-pom-maps`, escriptura gated `CONFIGURE`), i **s'edita des de
`/cataleg/peces`** — [CatalegPeces.jsx](../../frontend/src/pages/CatalegPeces.jsx) via
[TaulaPOMsCataleg.jsx](../../frontend/src/components/cataleg/TaulaPOMsCataleg.jsx) i
`MeasurementBaseGrid`. **La funció ja viu en un altre lloc; no cal moure-la.**

### 7.2 «El model 837 / el banc / TRV-SS27-0001» són **el mateix**

Mesurat: `models_app_model` id **1383** · `codi_intern` **TRV-SS27-0001** ·
`nom_prenda` **«837 VESTIT»**. Els 3 `PatternFile` de `fhort` (18, 19, 20) hi pengen tots,
amb les mateixes 5 peces. **`patterns_patternpiece` amb doblec: 0** (coherent amb el fil
del desplegat, tancat avui amb població afectada zero).

---

## 8 · Icones i tokens

### 8.1 Icones Tabler (outline, com mana CLAUDE.md)

| fitxer | icones |
|---|---|
| `TallerPatro.jsx` | `alert-triangle · arrow-left · arrows-horizontal · check · chevron-right · clock-play · corner-down-right · dimensions · file-vector · info-circle · line · link · needle-thread · point · ruler-2 · ruler-measure · triangle · vector-spline · vector-triangle · x` |
| `PatternViewer.jsx` | `arrow-narrow-up · flip-horizontal · hand-move · line · line-dashed · maximize · needle-thread · point · ruler-measure · scissors · switch-horizontal · zoom-in · zoom-out` |
| `ModelPomList.jsx` | `check · circle-check · circle-dashed · crosshair · dots-vertical · eye · focus-2 · info-circle · pencil · plus · trash · x` |
| `RelationsPanel.jsx` | `alert-triangle · arrow-back-up · arrows-move · ban · check · chevron-down/up · line · loader · needle-thread · pencil · rosette-discount-check · trash · triangle · wand` |
| `PatternTab.jsx` | `alert-triangle · arrow-back-up · arrow-up-right · file-download · file-vector · info-circle · loader · pointer · table · table-export · tools · upload · vector-triangle · x` |
| `ProposalsPanel` · `DartProposalsPanel` | `check · filter · minus · plus · point · triangle · wand · x` |
| altres | `PieceList`: `scissors-off · vector-triangle` · `SegmentEditor`: `check · line · triangle` · `seleccio`: `alert-triangle · trash · x` |

**Semàntica ja fixada que el mockup ha de reutilitzar:** `ti-ruler-measure` = mesurar ·
`ti-line` = tram · `ti-triangle` = pinça · `ti-needle-thread` = cosir · `ti-wand` = el motor
opina · `ti-point` = punts.

### 8.2 Tokens CSS (les 24 variables que el Taller fa servir de veritat)

`--fs-caption` (94) · `--text-soft` (86) · `--line` (60) · `--fs-body` (47) · `--gold` (41)
· `--panel` (40) · `--text-main` (36) · `--mono` (22) · `--err` (21) · `--white` (12) ·
`--ok` (10) · `--sel` (7) · `--err-bg` (6) · `--warn` / `--warn-bg` (5) · `--gold-border`
(4) · `--fs-h3` (4) · `--bg-muted` (4) · `--accio` (4) · `--fs-label` (3) · `--ok-bg` (2) ·
`--bg-page` (2) · **`--tram` i `--tram-sel`** (1 cadascun).

🔑 **`--tram` / `--tram-sel` tenen mirall literal a `KONVA_COL`** perquè *«el tram es pinta
IGUAL mentre es declara i un cop desat —és el mateix objecte—, i l'estat només en canvia
l'èmfasi»*. **Identitat ≠ èmfasi**: llei de disseny ja presa.

---

## 8-bis · 🔑 El que NOMÉS es veu amb la pantalla viva

Coses que el cens de codi no ensenyava i que les captures 06-10 fan evidents:

### 8-bis.1 La sub-barra de MÈTODES existeix i és visible (`08`)

En entrar al mode **Marcar POM** apareix una **segona fila** sota els modes:
**`↔ Recta` · `⌒ Per vora` · `↳ Caiguda` · `⊞ Cota`** — els 4 mètodes de §4, com a
commutadors amb el mateix llenguatge visual que les capes. **El mockup no els ha
d'inventar: ja tenen forma.**

### 8-bis.2 La col·locació és GUIADA, àncora per àncora (`08`)

Un bàner sota la barra diu: **«Col·locant J (1/2 ample de braç) — clica el punt A»**, amb
una ✕ per cancel·lar. El Taller **condueix el gest** i anomena l'àncora que toca. És
exactament el que R5b necessitarà per a la mesura lliure.

### 8-bis.3 La llista de POMs treballa amb la Δ fitxa→patró (`08`)

**«POMS DEL MODEL · 20 DE 21 COL·LOCATS»**, i cada fila porta
`22,0 cm → 22,4 cm` amb un xip **`✓ Δ +0,4`** i el rastre `fitxa → patró` + la peça on
seu (`837.DELANTERO`). El que falta per col·locar surt amb el xip `fitxa` i sense valor.
**La feina del taller ja té comptador i semàfor.**

### 8-bis.4 La proposta de cosit s'explica en paraules (`08`)

La targeta d'una proposta —`837.DELANTERO · 31,6 cm ⛓ 837.ESPALDA`, **55 %**— no dona una
xifra sola: en dona **el desglòs en llenguatge de taller**:

```
+  Els dos costats fan el mateix: 31,6 cm i 31,7 cm
+  837.DELANTERO i 837.ESPALDA són peces veïnes
+  Aquest taller ja havia confirmat trams així a 837.ESPALDA
o  Cap dels dos trams no porta piquets
⚠  Si la confirmes, NO casarà per 0,1 cm
                                        [✓ Confirmar]  [✕ No]
```

I al peu: **«7 parelles rebutjades no es mostren»** amb `🗑 Netejar`. 🔑 **El «+ / o / ⚠»
és un vocabulari de senyals ja dissenyat**, i el tercer punt demostra que **el motor
aprèn del taller** (`SegmentPreference`). El mockup ha de conservar-ho sencer.

### 8-bis.5 Les cotes es dibuixen sobre el patró, amb etiqueta (`08`, `09`)

Al llenç surten en magenta (`KONVA_COL.pom = #bf3989`) amb el codi i el valor:
`S2 22,0 cm`, `E1 7,7 cm`, `EK2 4,1 cm`, `F 22,4 cm`, `SLT 31,6 cm`, `F 110,8 cm`…
**R5a no és només «fet al backend»: es veu.**

### 8-bis.6 🚨 El visor ÉS A DUES PANTALLES (`09`)

La pestanya **Patró** del model ([PatternTab.jsx](../../frontend/src/components/pattern/PatternTab.jsx),
727 línies) porta **un segon visor** amb **els mateixos commutadors de capa**
(Tall · Cosit · Piquets · Fil · Punts, al 37 %), al costat de la llista d'identitat, i a
més:

- **CAD d'origen**: `polypattern · 1 mm · deduïdes per geometria · confiança baixa`
- **Selector de VERSIÓ** (`v3 · actual`)
- **`Obrir al taller` · `Descarregar DXF` · `Exportar niada` · `Veure el render SVG`**
- Dues zones de pujada: **DXF obligatori · RUL opcional**
- El rètol de la identitat: **«Digues què és cada peça. El sistema no ho endevina.»**

> 🚨 **Per al mockup:** el sistema de capes **ja té dos consumidors**. Si el mockup en
> dibuixa un tercer amb una altra gramàtica, en tindrem tres diferents. La decisió no és
> «com dibuixo les capes» sinó **«com les comparteixen les tres superfícies»**.

### 8-bis.7 El layout de referència G1 (`10`)

El fitting editor confirma el patró de la casa que el Taller ja segueix: **capçalera
enganxada** amb model i pestanyes (`Dashboard · Resum · Mesures · Escalat · Patró · Fitxa
tècnica · Fitxers · Registre d'activitat · Tasques`), **bàner de sessió** amb estat i
responsable, **llegenda de teclat** (`↓/Enter següent · ↑ anterior · Tab valor→veredicte→nota
· A accepta · J ajusta · R rebutja`) i graella amb `FIT 7 · FIT 8 · FIT ACTUAL` +
`ACCEPTED / ADJUSTED / REJECTED`. 🔑 **El Taller és l'única eina a pantalla completa fora
del Shell** — i això és deliberat ([App.jsx:433](../../frontend/src/App.jsx#L433)).

---

## 9 · Contrast amb el disseny v2 — FET / PARCIAL / NOU

| R | què demana | estat | què n'hi ha JA (rastre) | què falta |
|---|---|---|---|---|
| **R1** | col·locació de peces al llenç (moure / aïllar) | **PARCIAL** | **Aïllar existeix**: selecció + atenuació a `opacity 0.25` ([PatternViewer:466](../../frontend/src/components/pattern/PatternViewer.jsx#L466), [:1052](../../frontend/src/components/pattern/PatternViewer.jsx#L1052)) · `insert_at` es persisteix per peça | **Moure és NOU**: el visor és READ-ONLY estricte ([:15](../../frontend/src/components/pattern/PatternViewer.jsx#L15)). Cal decidir on viu la col·locació (presentació, mai dada) |
| **R2** | només punts semàntics | **PARCIAL** | **La semàntica hi és tota**: `turn`/`curve`/`notch` amb forma i color propis ([:1082-1101](../../frontend/src/components/pattern/PatternViewer.jsx#L1082)) | **El filtre és NOU**: `punts` és tot-o-res. Al 837, 1 196 punts de corba contra 20 de gir — **el soroll és de 60 a 1** |
| **R3** | costures ràpides (auto + clic / shift+clic) | **PARCIAL** | **L'auto està FET** (`Buscar propostes`, motor A2, amb desglòs de senyals i rebuig desat) · el clic manual també (mode `sew` + `SewEditor`) | **`shift+clic` NO existeix**: cap selecció múltiple al Taller |
| **R4** | panell de característiques de peça estil CLO | **PARCIAL** | `PieceIdentityList`: `nom · piece_role · lateralitat · ordinal · estat_peca` · a la BD: `grain`, `doblec_original`, `metadata` (material, quantity) | **Falten a la UI**: tall **CUT-n+n**, material, fil **editable**, eix de plec, **origen fix de grading** |
| **R5a** | cotes CAD | ✅ **FET** | 4 mètodes amb gramàtica del servidor · recepta mai valor · `cota_offset_mm` presentació pura · reobrir amb `PATCH` · esborrat en bloc | — |
| **R5b** | segments de guia + mesura lliure en mm | **PARCIAL** | **Els segments de guia estan FETS**: mode `seg`, trams `auto`/`natural`/`declarat`, arc curt amb tecla d'invertir | **La mesura lliure és NOVA**: `grep` de «mesura lliure» → cap resultat |
| **desplegat** | vista derivada amb eix declarat | **PARCIAL** | Les dades hi són (`has_fold`, `doblec_original` amb eix i costat) i **l'import ja desplega** · toggle de capa `mirror` | **La vista NO és commutable**: es veu el desplegat i prou; no hi ha «veure'l plegat» |

**Recompte: 1 FET · 5 PARCIAL · 1 NOU-dins-de-parcial.** Cap R no és terra verge.

---

## 10 · El que el mockup v1 NO recollia i cal integrar

**Per ordre d'importància:**

1. 🥇 **LES CAPES.** Set commutadors amb paleta pròpia i la llei *«una capa que el fitxer
   no porta no s'ofereix»*. És el que Agus ha demanat per nom i **el mockup v1 no en parla**.
2. 🥈 **La barra és UNA de sola.** Els controls del visor **es teletransporten per portal**
   a la barra del pare (`display: contents` perquè facin `wrap` un a un):
   *«una sola barra, no dues»* ([TallerPatro.jsx:1604-1609](../../frontend/src/pages/TallerPatro.jsx#L1604)).
   Un mockup amb dues barres desfaria una decisió ja presa.
3. 🥉 **El gest exigeix una TASCA OBERTA.** Els 4 modes són `disabled={!tascaId}`. A la
   captura es veuen grisos i **és correcte**. El mockup ha de dir d'on surt la tasca.
4. **El motor no opina fins que li ho demanen** (`Buscar propostes`). Un mockup que ensenyi
   la llista plena en obrir contradiu F/T1.
5. **L'imant.** No es pot marcar res «a ull»: *«seria un dibuix a sobre del patró»*.
6. **Identitat ≠ èmfasi** als colors de tram (`--tram` vs `--tram-sel`).
7. **La cota es desplaça, la mesura no.** Si el mockup deixa moure una cota, ha de deixar
   clar que això **mai** toca el valor.
8. **El verd de la identitat ve del servidor**, no del navegador.
9. **`GarmentPOMMapEditor` no s'ha de dibuixar**: no existeix i la seva funció ja viu a
   `/cataleg/peces`.
10. 🚨 **Les capes tenen DOS consumidors** (Taller i pestanya Patró). El mockup no ha de
    dissenyar-ne un tercer: ha de dir **com es comparteixen** (§8-bis.6).
11. **El vocabulari «+ / o / ⚠» de les propostes** i el seu llenguatge de taller (§8-bis.4).
12. **La col·locació guiada àncora per àncora** («clica el punt A») — la base de R5b.
13. **La sub-barra de mètodes** ja existeix amb forma pròpia (§8-bis.1).
14. 🚩 **`?task_id=` és part del contracte de la pantalla**: sense ell, obrir el Taller
    **escriu al domini**. Qualsevol enllaç del mockup cap al Taller ha de portar-lo.

---

## 11 · Captures

| fitxer | què ensenya |
|---|---|
| `01_taller_estat_normal.png` | El Taller sencer amb el 837: 5 peces, barra única, els 4 modes desactivats (sense tasca), panells PECES / POMS DEL MODEL / RELACIONS, zoom al 54 % |
| `02_capes_nomes_tall.png` | Només la capa **Tall**: el contorn negre net, sense cosit ni piquets ni fil ni punts |
| `03_capes_nomes_cosit.png` | Només la capa **Cosit**: la línia blava i les internes discontínues — **la prova que el sistema de capes val** |
| `04_capes_totes_amb_punts.png` | Totes enceses, amb els punts semàntics (gir verd · corba groc · piquet vermell) |
| `05_peca_seleccionada.png` | Una peça seleccionada i les altres atenuades (l'aïllament que ja existeix, R1) |
| **`06_modes_actius_amb_tasca.png`** | Amb `?task_id=380`: **els 4 modes ACTIUS** (verificat pel DOM: `Marcar POM · Definir tram · Marcar pinça · Cosir` tots habilitats) |
| **`07_cota_seleccionada.png`** | Una cota triada de la llista, amb la fila ressaltada |
| **`08_proposta_cosit_oberta.png`** | 🥇 **Tres estats en una**: mode POM actiu amb la sub-barra de mètodes · una cota en col·locació · **una proposta de cosit oberta amb el desglòs sencer** |
| **`09_identitat_peces.png`** | La pestanya **Patró** del model: identitat de les 5 peces + visor amb les mateixes capes |
| **`10_fitting_editor.png`** | El fitting editor (referència de layout G1), amb la graella de veredictes |

Totes a **1600×950**, bundle i CSS de producció. Les 01-05 amb dades d'staging per stub;
**les 06-10 contra l'API viva**.

---

## 12 · Rastre

| què | com |
|---|---|
| dades de les captures | `SELECT` reproduint `PatternGeometrySerializer._piece` sobre `fhort` (PatternFile 20) |
| BD | `sudo -u postgres psql -p 5433 -d ftt_staging` — **només `SELECT`** |
| captures | `/tmp/qa-venv/bin/python` + bundle de `frontend/dist`; script al **scratchpad**, no al repo |
| cens de codi | lectura de `pages/TallerPatro.jsx` i `components/pattern/*` (7 995 línies) |
| icones i tokens | extracció de `ti-*` i `var(--*)` sobre els mateixos fitxers |

**Cap servei tocat, cap test executat, cap escriptura al repo fora d'aquest informe i la
carpeta de captures.**
