> ⚠️ SUPERADA 2026-07-21 — implementada pel sprint Patró B end-to-end (fases 1-7, commits
> 73babdb→254eaa8). Consulta només com a històric.

# DIAGNOSI — Llenguatge visual compartit: TallerPatro ⇄ editor de fitxa tècnica

Data: 2026-07-21 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` · **HEAD = `130916d`**

**Abast.** Unificar el **llenguatge visual** (mides, tipografia, colors, patró de botó, patró de col·lapsable) entre `TallerPatro.jsx` (referència) i `TechSheetEditor.jsx`. Es mapeja: anatomia del panell esquerre del Taller com a precedent del futur contenidor de POMs (P1), la seva barra d'accions (P2), què queda a la paleta vertical de TSE si les eines de node migren (P3), i un **inventari d'estil pur costat a costat** per separar la deriva involuntària de la diferència intencionada (P4′).

> **CORRECCIÓ D'ABAST (Agus, durant la diagnosi).** Els blocs originals P4 (quins blocs del panell dret encaixarien a l'esquerra) i P5 (cost de moure el panell) **es retiren**: **NO es mouen components entre panells**. Taller de Patró i editor de fitxa fan coses diferents (patronatge vs document) i **cada un manté la seva estructura de zones**. Els substitueix P4′. El material de layout ja recollit es conserva només com a §Annex, sense recomanació.

**Convenció.** Cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**, no especulat. Propostes marcades 💡 — **les decisions són humanes (Patró C)**.

**Avisos de context:**
- **No s'ha rebut cap captura.** El brief en menciona una; al missatge no hi havia imatge. **Tot el mapa surt del codi.** Diferències de percepció visual que no es dedueixin del JSX no hi són.
- **Concurrència.** Sessió Patró B en paral·lel sobre `TechSheetEditor.jsx`: 3 commits nous (`d012ea5`, `b38bc29`, `130916d`, +45/−12). **Les línies del brief havien caducat i s'han reancorat totes a `130916d`.** `TallerPatro.jsx` no l'ha tocat ningú. Aquesta sessió no ha escrit res fora d'aquest doc ni ha fet cap `pull`.

**Correcció d'ancoratges respecte del brief:**

| Peça | Brief | Real a `130916d` |
|---|---|---|
| `PALETTE` | — | `:3883-3927` |
| Render paleta | `:4426-4491` | `:4459-4524` |
| `ribbonTabs` / `renderRibbonContent` | `:4010-4135` | `:4043` / `:4096` |

---

## Resum executiu

1. **El vocabulari de COLOR ja està unificat i ningú se n'havia adonat.** `COL` de TSE (`:73-85`) mapeja als **mateixos `var()`** que fa servir el Taller: `--gold`, `--gold-pale`, `--border`, `--text-main`, `--text-muted`, `--white`. La deriva **no és de color**: és de **geometria i tipografia**.

2. **Deriva involuntària detectada, tres focus concrets:** radi de cantonada (Taller 4/6 · TSE 5/6/8), pes del títol de secció (600 vs **700**) i `letter-spacing` (0.03em vs **0.05em**). Cap d'aquestes diferències té justificació funcional.

3. **Diferència que SÍ sembla intencionada:** el Taller té **dues intensitats d'actiu** (`--gold` ple = mode actiu · `--gold-pale` = element seleccionat); TSE només en té una (`goldPale` a tot arreu). És una capacitat expressiva que a TSE **no existeix**.

4. **TSE té deriva INTERNA pròpia**: tres mides de botó petit conviuen — 32×32 (`paletteBtn :3690`), 30×26 (`miniBtn :5347`), 28×26 (`nodeBarBtn :5362`).

5. **Hi ha una peça idèntica als dos fitxers**, prova de llinatge comú: el separador vertical (`width:1, height:18, background var(--border)`) — `PatternViewer.jsx:870` i `TechSheetEditor.jsx:5363`.

6. **Només 2 de 22 eines de la paleta són candidates a moure**: `node` (`:3886`) i `subpath` (`:3887`). Les altres 20 són inserció/creació/navegació i **sobreviuen**.

7. **⚠️ Dues tensions amb decisions ja preses** (§Tensions): la tab "Editar" reverteix la decisió G4 documentada al codi, i **TallerPatro no és un ribbon**, així que aquesta metàfora no s'hereta de la referència.

---

## BLOC P1 — TallerPatro: anatomia del panell esquerre

### P1.1 · Estructura i seccions
- Shell: `TallerPatro.jsx:1089` (`100vw/100vh`, flex column) · capçalera pròpia `<Capcalera>` (`:1504`, `height:52`) · `<main flex row minHeight:0>` a `:1095`.
- **Exactament TRES `Contenidor`** (no n'hi ha cap més al fitxer):

| Secció | Línia | `titol` (ca) | Icona | `pes` | Contingut |
|---|---|---|---|---|---|
| PECES | `:1100` | "Peces ({n})" (`ca.json:3580`) | `ti-vector-triangle` | `1` | `<PieceList>` (`:1105`) |
| POMS DEL MODEL | `:1109` | "Poms del model · {a} de {t} col·locats" (`ca.json:3428`) | `ti-ruler-measure` | **`1.5`** | `<ModelPomList>` (`:1115`) |
| RELACIONS | `:1124` | "Relacions" (`ca.json:3490`) | `ti-link` | `1` | `<RelationsPanel>` (`:1125`) |

- **Segon nivell de seccions** dins de Relacions: component local `Seccio` (`RelationsPanel.jsx:901`), 6 subseccions (`:93`, `:133`, `:143`, `:198`, `:227`, `:252`).
- **Gramàtica de dos nivells ja resolta**: capçalera de contenidor a sang (`:1326`) vs capçalera de secció **inset** (`RelationsPanel.jsx:904-916`, `borderRadius:4`, `margin:'0 0 0.35rem'`), **mateix `--charcoal`/`--white`/`--fs-label`/uppercase**. Comentari literal a `:898`: *"mateix color, jerarquia diferent"*.

### P1.2 · Targeta de peça
- `PieceList` (`components/pattern/PieceList.jsx:11`) — **ja compartit** entre Taller (`:1105`) i tab Patró (`PatternTab.jsx:186`).
- Targeta = `<button>` (`:22`), `aria-pressed` (`:25`), toggle (`:24`). Tres nivells: (1) icona + `<strong>nom_block</strong>` + badge pill de material + `ti-scissors-off` si `!has_sew` (`:34-51`); (2) recompte de punts, `--fs-caption` gris (`:52-57`); (3) bbox `ample × alt cm` en `--mono` gris (`:58-65`).

### P1.3 · Llista de POMs — **precedent directe del futur contenidor de POMs**
- `ModelPomList.jsx:27`; fila a `:82`. Columna `gap:3` (`:32`); buit → paràgraf gris (`:34`); acció secundària amb **vora dashed** (`:50-61`).
- La fila **no és un botó sencer**: `div` amb dos germans (botó-fila + botó info), perquè un botó dins d'un botó no és HTML vàlid (comentari `:107`).
- Caixa (`:96-105`): daurats si actiu, i **`borderLeft: 3px solid` com a semàfor d'estat** — `--ok` col·locat · `--gold` actiu · `--border` pendent.
- **Ordre exacte de la fila**:
  1. Icona d'estat (`:123`): `ti-circle-check` verd · `ti-crosshair` daurat · `ti-circle-dashed` gris.
  2. Bloc central (`:129`): línia 1 = **codi de client en `--mono` bold** + nom canònic EN (`f.nom?.en`, fallback nom client, `:92`) + badge pill `nom_fitxa` (`:143-151`); línia 2 = descripció, `--fs-caption` gris amb ellipsis (`:156-163`); línia 3 = àlies en cursiva (`:167-175`); línia 4 = nom de peça si col·locat (`:177-181`).
  3. Bloc numèric a la dreta (`:188`), `--mono`, `textAlign:'right'`: valor fitxa `→` valor mesurat (`:203-219`) amb etiqueta sota (`:221-225`).
  4. `XipVeredicte` (`:252`): pill `Δ`, `--ok`/`--ok-bg` amb `ti-check` o `--err`/`--err-bg` amb `ti-x`; **sense tolerància → pill neutre sense judici** (`:255-263`).
  5. `BotoInfo` (`:290`): popover `role="dialog"`, `top:100%; right:0; zIndex:3000`, `<dl>` on **les línies buides no es pinten** (`:320`).
- **Llei tipogràfica explícita** (comentaris `:18`, `:23`): *el codi de client mana, el nom va a sota en gris; **la xifra no es tenyeix mai — el color el porta el xip***.

### P1.4 · Amplada i alçada
- **`width: 360, flexShrink: 0`** en un únic lloc (`:1096-1099`), amb `borderRight` i `background: var(--bg-page)`.
- **NO EXISTEIX** cap `@media`, amplada percentual ni splitter. Els únics `resize` són del canvas (`PatternViewer.jsx:174-193`).
- Repartiment per **pes proporcional**: `flex: plegat ? '0 0 auto' : `${pes} 1 0`` (`:1317`). Amb 1/1.5/1, POMs es queda 1.5/3.5 de l'alçada lliure; en plegar cedeix **tota** la seva alçada.
- Cos amb `overflowY:auto` (`:1340-1344`) → **cada secció té scroll propi; la pàgina no fa scroll mai** (comentari `:1298`). Plegat, el cos **es desmunta**.
- **`minHeight:0` propagat a tota la cadena** és el que ho fa funcionar — estructural, no cosmètic.

> **Veredicte P1: el patró de contenidor i la fila de POM són heretables tal qual.** Única fricció: `Contenidor` **no està exportat** (funció local a `:1310`).

---

## BLOC P2 — TallerPatro: barra d'accions

### P2.1 · Botons de mode
- `BarraEines` (`:1354`), renderitzat **dins la columna del canvas** (`:1162`), no a la capçalera.
- **NO EXISTEIX cap array declaratiu**: 4 `<button>` JSX a mà, en ordre de flux (comentari `:1377`):

| Línia | mode | icona | i18n (ca) |
|---|---|---|---|
| `:1370` | `pom` | `ti-ruler-measure` | "Marcar POM" (`ca.json:3612`) |
| `:1378` | `seg` | `ti-line` | "Definir tram" (`ca.json:3427`) |
| `:1388` | `pinca` | `ti-triangle` | "Marcar pinça" (`ca.json:3426`) |
| `:1395` | `sew` | `ti-needle-thread` | "Cosir" (`ca.json:3613`) |

- **Gating dur**: sense `tascaId` (rellotge), tots `disabled` i al 50% d'opacitat (`:1360-1361`, comentari `:1350`). A la dreta, molla + xip d'estat de tasca (`:1403-1414`).

### P2.2 · Barra secundària
- `Controls` viu **dins el viewer** (`PatternViewer.jsx:836`, renderitzat a `:363`).
- Array declaratiu **només** per als toggles de capa (`:839-842`), filtrat per `presents.has(capa)` (`:872`) — **una capa que el fitxer no porta no s'ofereix** (comentari `:837`).
- Ordre (`:849-901`): zoom− · zoom+ · Encaixar · % en `--mono` (`minWidth:52`) · **separador d'1px** (`:870`) · toggles de capa · toggle "punts" (`:888`).
- Botó **més petit** que els de mode: la jerarquia és **mida + color**.
- Tercera franja sota el llenç: `BarraEstat` (`:905`), `--fs-caption --mono` gris.

### P2.3 · No és un ribbon (FET estructural)
Pila vertical de **franges fixes, totes visibles alhora** (`:1158`, `flexDirection:'column', gap:'0.5rem'`): barra de modes (`:1366`) → franja d'avisos condicional (`:1167`, `:1170`, `:1173`, `:1188`, `:1203`) → editor contextual del mode (`:1212`, `:1220`, `:1229`) → viewer amb `Controls` a dalt i `BarraEstat` a baix.

- **NO EXISTEIXEN tabs** ni grups etiquetats. La barra de modes **no canvia de contingut**: sempre els mateixos 4 botons. **El que canvia amb el mode és el que apareix a sota.**
- Estat: `mode` (`:69`), selector `triarMode` **toggle** (`:241-255`).

---

## BLOC P3 — Què queda a la paleta vertical de TSE

### P3.1 · Inventari (`130916d`)

| Categoria | Eina `k` | Icona | Línia | Veredicte |
|---|---|---|---|---|
| `select` | `select` | `ti-pointer-2` | `:3885` | **SOBREVIU** |
| `select` | `node` | `ti-vector` | `:3886` | **MOURE** |
| `select` | `subpath` | `ti-vector-triangle` | `:3887` | **MOURE** |
| `draw` | `draw` | `ti-pencil` | `:3890` | SOBREVIU |
| `draw` | `pen` | `ti-vector-bezier` | `:3891` | SOBREVIU |
| `draw`/`shapes` | `rect`,`rect_round`,`ellipse`,`polygon` | — | `:3893-3896` | SOBREVIU |
| `draw`/`lines` | `line`,`line_dot` | — | `:3899-3900` | SOBREVIU |
| `draw`/`arrows` | `arrow`,`arrow2`,`arrow_curve` | — | `:3903-3905` | SOBREVIU |
| `text` | `text`,`text_box` | — | `:3910-3911` | SOBREVIU |
| `annot` | `cota_pom` | `ti-ruler-measure` | `:3915` | SOBREVIU |
| `annot` | `note` | `ti-arrow-guide` | `:3916` | SOBREVIU |
| `annot`/`presets` | `preset_callout`,`preset_detail_circle`,`preset_legend` | — | `:3918-3920` | SOBREVIU |
| `nav` | `pan` | `ti-hand-stop` | `:3925` | SOBREVIU |
| (fora `PALETTE`) | botó imatge | `ti-photo` | `:4510-4514` | **DUPLICAT ×3** |
| peu | swatches `fill`/`stroke`/`swap` | — | `:3930-3932` | **DUPLICAT + MORT** |

- **Cap item de `PALETTE` porta `soon`.** El suport existeix (`:4468`, `:4480`, `:4497`, estil `:3696`) però **cap item el declara** → "eina de paleta marcada soon" = **NO EXISTEIX**. Els únics morts són els 3 swatches (`disabled` literal a `:4518`).
- `TOOL_SHORTCUT` (`:109`) només cobreix 7 de 22 eines; el mapa real és a `:2619`.

### P3.2 · Per què només `node` i `subpath`
- `node` és **l'única porta de paleta al sub-editor**: `tool==='node'` → `startVectorEdit(o)` (`:4568-4569`) → `setEditingFlatId` (`:3241-3247`). **Ja té bessó**: `direct_select` a la barra F1 (`:5353`, render `:4322-4326`).
- `subpath` no obre el sub-editor: opera a nivell Konva (`:4583` → `PathObj :1431`) i **alimenta el bloc de subpath del panell dret** (`:4947-4966`). Bessó a F1: `shape_select` (`:5352`).
- El ribbon **no té cap comandament de selecció ni de pan** (`:4096-4168`; zoom sí a `:4116-4119`).

### P3.3 · Fets col·laterals
- **La paleta i el sub-editor MAI coexisteixen**: `onStageMouseDown` (`:2913`), `onStageMouseMove` (`:2978`) i `onStageMouseUp` (`:3030`) surten amb `if (editingFlatId) return`.
- **Duplicats vius**: inserir imatge (paleta `:4510` · ribbon `:4137` · menú `:4189` — **tres camins**, i el de la paleta salta el panell d'import); cursors node/subpath (paleta vs F1).
- **Cap eina de paleta apareix als menús de text** (`:4246-4251`) → **NO EXISTEIX**.
- **Tres superfícies amb semàntica solapada**: ribbon `organize` (`:4143-4166`) · menú Objecte (`:4206-4239`) · barra F1 (`:4340-4399`).
- Paleta: **46 px fixos**, només si `locked` (`:4460-4461`); flyouts `position:fixed` ancorats al `DOMRect` viu del botó (`:4481`, `:4490`, `:4495`), press-and-hold 300 ms (`:3941`) → **es reancoren sols** si el layout canvia.

> **Veredicte P3: la paleta sobreviu quasi sencera.** Marxen 2 eines, en queden 20. El deute de duplicats és **independent** d'aquesta feina.

---

## BLOC P4′ — Inventari d'estil pur, costat a costat

Objectiu: separar **deriva involuntària** de **diferència intencionada**. Valors literals dels dos fitxers.

### P4′.1 · Color — **ja unificat** (troballa)
`COL` de TSE (`TechSheetEditor.jsx:73-85`) **no són hex: són `var()`**, els mateixos tokens del Taller.

| Rol | TallerPatro | TSE (`COL`) | Veredicte |
|---|---|---|---|
| Accent | `var(--gold)` | `gold: 'var(--gold)'` `:75` | **IDÈNTIC** |
| Actiu suau | `var(--gold-pale)` | `goldPale: 'var(--gold-pale)'` `:76` | **IDÈNTIC** |
| Filet | `var(--border)` | `border: 'var(--border)'` `:77` | **IDÈNTIC** |
| Text principal | `var(--text-main)` | `textMain: 'var(--text-main)'` `:78` | **IDÈNTIC** |
| Text secundari | `var(--text-muted)` | `textMuted: 'var(--text-muted)'` `:79` | **IDÈNTIC** |
| Interior de control | `var(--white)` | `field: 'var(--white)'` `:84` | **IDÈNTIC** |
| Fons de contenidor | `var(--bg-page)` (aside `:1097`) · `var(--bg-card)` (targetes) | `bg: 'var(--bg-card)'` `:80` | **DIFERENT** (page vs card) |
| Capçalera de secció | **`var(--charcoal)`** (`:1327`) | **NO EXISTEIX a `COL`** | **ABSENT a TSE** |
| Semàfor / veredicte | `--ok`, `--ok-bg`, `--err`, `--err-bg` | **NO EXISTEIXEN a `COL`** | **ABSENT a TSE** |

→ **La deriva no és de color.** Els que falten a TSE (`--charcoal`, `--ok`, `--err`) són els que fan la capçalera fosca i el xip de veredicte.

### P4′.2 · Radi de cantonada — **DERIVA**

| Peça | Valor | Ancoratge |
|---|---|---|
| Taller · botó de mode | **4** | `TallerPatro.jsx:1359` |
| Taller · botó de `Controls` | **4** | `PatternViewer.jsx:845` |
| Taller · fila de POM | **4** | `ModelPomList.jsx:101` |
| Taller · capçalera de `Seccio` (inset) | **4** | `RelationsPanel.jsx:905` |
| Taller · targeta de peça | **6** | `PieceList.jsx:27` |
| TSE · `paletteBtn` | **5** | `:3691` |
| TSE · `ribbonToolStyle` | **5** | `:4059` |
| TSE · `ribbonTabStyle` | **5 5 0 0** | `:4051` |
| TSE · `ribbonSelectStyle` | **5** | `:4066` |
| TSE · `propInput` | **5** | `:5364` |
| TSE · `nodeBarBtn` | **6** | `:5362` |
| TSE · `miniBtn` | **6** | `:5347` |
| TSE · dropzone d'import | **8** | `:4709` |

→ Taller usa **4 i 6**; TSE usa **5, 6 i 8**. El **5 no existeix al Taller** i el **4 no existeix a TSE**. Sense justificació funcional → **deriva**.

### P4′.3 · Estat ACTIU — **diferència de capacitat, probablement intencionada al Taller**

| Patró | TallerPatro | TSE |
|---|---|---|
| **Mode/eina activa** | `background: var(--gold)` **ple** + `color: var(--white)` (invertit) — `TallerPatro.jsx:1356-1358` | `background: goldPale` + `borderColor: gold` + `color: gold` — `paletteBtnOn :3694` |
| **Element seleccionat** | `background: var(--gold-pale)` + `border: var(--gold)` — `PieceList.jsx:27-28`, `ModelPomList.jsx:97-99`, `PatternViewer.jsx:879-881` | (mateix tractament que l'anterior) |

→ **El Taller té DUES intensitats; TSE només UNA.** Tots els actius de TSE (`paletteBtnOn :3694`, `nodeBarBtn :5362`, `ribbonToolStyle :4059`, `ribbonTabStyle :4052`) usen el mateix `goldPale`+`gold`. TSE **no pot distingir visualment "eina activa" de "element seleccionat"**.

### P4′.4 · Títol de secció — **DERIVA (pes i tracking)**

| Propietat | Taller (`Contenidor`, `:1330-1334`) | TSE (`SectionTitle`, `:5343`) | Veredicte |
|---|---|---|---|
| `fontSize` | `var(--fs-label)` | `var(--fs-label)` | **IDÈNTIC** |
| `fontWeight` | **600** | **700** | **DERIVA** |
| `textTransform` | `uppercase` | `uppercase` | **IDÈNTIC** |
| `letterSpacing` | **0.03em** | **0.05em** | **DERIVA** |
| `color` | `var(--white)` | `COL.gold` | estructural |
| `background` | `var(--charcoal)` | cap | estructural |
| Interactiu | `<button>` amb `aria-expanded` (`:1323`) | `<div>` estàtic | estructural |
| Espaiat | `padding: '0.45rem 0.7rem'` | `margin: '12px 0 6px'` | estructural |

→ `fontSize`/`uppercase` coincideixen; **`fontWeight` i `letterSpacing` no**, i no hi ha cap raó funcional. La resta són diferències estructurals reals (capçalera col·lapsable vs etiqueta estàtica).
→ Nota: el títol del panell d'import de TSE (`:4685`) usa **700 + 0.05em + `textMuted`** — una **tercera** variant dins del mateix fitxer.

### P4′.5 · Mides de botó

| Botó | Mida / padding | Font | Ancoratge |
|---|---|---|---|
| Taller · mode | `padding: '0.35rem 0.8rem'` | (heretada) | `:1359` |
| Taller · `Controls` | `padding: '0.2rem 0.5rem'` | `var(--fs-caption)` | `PatternViewer.jsx:845-846` |
| TSE · `paletteBtn` | **32 × 32** | — | `:3690` |
| TSE · `miniBtn` | **30 × 26** | — | `:5347` |
| TSE · `nodeBarBtn` | **28 × 26** | — | `:5362` |
| TSE · `ribbonToolStyle` | `width:72, minHeight:50`, `padding:'5px 3px'` | `var(--fs-caption)` | `:4057-4060` |
| TSE · `ribbonTabStyle` | `minWidth:86, height:28` | — | `:4050` |

→ **Deriva INTERNA de TSE**: tres mides de botó petit conviuen (32×32 · 30×26 · 28×26) sense diferència de rol que ho expliqui.
→ El Taller dimensiona per **padding** (elàstic al contingut); TSE per **width/height fixos**. Diferència de mètode, no només de valor.

### P4′.6 · **Dos tokens s'usen però NO estan definits** (troballa)

Verificat contra `frontend/src/index.css` (únic full CSS del projecte, `find src -name "*.css"`):

- **`--bg-page`: NO EXISTEIX cap definició.** S'usa a 3 fitxers (`App.jsx`, `Entrar.jsx`, **`TallerPatro.jsx:1097`** — el fons del panell esquerre de referència). Sense definició, `background: var(--bg-page)` és invàlid en temps de càlcul → **l'aside del Taller no té fons propi**, mostra el que hi hagi al darrere.
- **`--mono`: NO EXISTEIX cap definició global.** L'única és **inline i local a una altra pàgina** (`Login.jsx:262`). S'usa a **10 fitxers**, entre ells `ModelPomList.jsx`, `PatternViewer.jsx`, `RelationsPanel.jsx`, `TallerPatro.jsx:1461`, `:1563`.
  - **Per què sembla que funciona:** `index.css:56` conté `* { font-family: 'IBM Plex Mono', monospace; … }` — **tota l'app ja és monoespaiada**. `font-family: var(--mono)` cau i hereta… la mateixa mono. El resultat és correcte **per accident**.
  - **Conseqüència per al llenguatge visual:** la distinció "xifra en `--mono` vs text normal" que el codi del Taller creu que fa (comentaris `ModelPomList.jsx:18`, `:23`) **no existeix visualment**: tot és mono.
  - TSE no depèn del token: declara `export const FONT = 'IBM Plex Mono, monospace'` (`:59`) i l'aplica explícitament. **Els dos fitxers arriben al mateix lloc per camins diferents** — un per token trencat + herència global, l'altre per constant JS.

Tokens que **sí** existeixen (verificat a `index.css`): `--gold-pale:#f5e6d0` (`:13`), `--charcoal:#1d1d1b` (`:22`), `--ok:#3b6d11` (`:28`), `--ok-bg:#eaf3de` (`:29`), `--err:#a32d2d` (`:32`), `--err-bg:#fcebeb` (`:33`), `--bg-card:#fafafa` (`:7`), `--fs-caption:8px` (`:47`), `--fs-label:10px` (`:48`).

### P4′.7 · Peces que ja coincideixen (llinatge comú)

| Peça | Taller | TSE | Estat |
|---|---|---|---|
| Separador vertical | `width:1, height:18, background var(--border)` — `PatternViewer.jsx:870` | `nodeBarSep` idèntic — `:5363` | **IDÈNTIC** |
| Escala tipogràfica | `--fs-label`/`--fs-body`/`--fs-caption` | mateixes vars | **IDÈNTIC** |
| Xifres | `--mono` | `--mono` a taules | **IDÈNTIC** |
| Deshabilitat | `opacity: 0.5` (`:1361`) | `0.42` (`:4061`) / `0.4` (`:3696`) / `0.45` (`:4734`) | **DERIVA** (4 valors) |
| Vora d'acció secundària | `1px dashed var(--border)` (`ModelPomList.jsx:52`) | `1.5px dashed` (dropzone `:4709`) | **DERIVA** (gruix) |

> **Veredicte P4′.** El color ja és comú; la deriva és **geomètrica i tipogràfica** i es concentra en cinc punts mesurables: **radi (4/6 vs 5/6/8)**, **pes del títol (600 vs 700)**, **tracking (0.03 vs 0.05em)**, **opacitat de deshabilitat (0.5 / 0.45 / 0.42 / 0.4)** i **mides de botó petit (3 dins de TSE)**. La **única diferència que sembla disseny** és la doble intensitat d'actiu del Taller, que a TSE **no existeix**.

---

## Tensions amb decisions ja preses (FET, per decidir sabent-ho)

- **T1 · La tab "Editar" al ribbon reverteix la decisió G4 documentada al codi.** El comentari `:4077-4081` estableix que la superfície única d'eines de node és la **barra contextual F1** (`:4310-4415`); amb `editingFlatId` actiu el ribbon retorna **només Fet/Cancel** (`:4100`). Una tab al ribbon crea **una quarta** superfície amb semàntica solapada (ja n'hi ha tres: ribbon `organize` · menú Objecte · F1).
- **T2 · TallerPatro no és un ribbon** (P2.3). La metàfora de tabs **no s'hereta de la referència**: és una decisió pròpia de l'editor. Convé no justificar-la com a "unificació".
- **T3 · Si `subpath` migra, ha de migrar-hi el gest.** El bloc de subpath del panell dret (`:4947-4966`) només es pobla amb `activeSubpath`, que només escriu l'eina `subpath` (`:4583`). Moure el botó sense el gest deixa el bloc mort.

---

## Propostes

💡 **P-A (a validar) — extreure `Contenidor` a `components/ui/`.** És local i no exportat (`TallerPatro.jsx:1310`). És el prerequisit perquè això sigui "convergir" i no "pegar" (CLAUDE.md). Afegir-hi `defaultOpen`; fer `pes` opcional (el panell de la fitxa és scrollable, no de flex repartit).

💡 **P-B (a validar) — tancar la deriva amb 5 decisions numèriques, no amb un redisseny.** Un radi únic, un pes de títol, un tracking, una opacitat de deshabilitat i una escala de botó petit. Són canvis mecànics i verificables, i **no toquen estructura de zones** (que és el que Agus ha exclòs).

💡 **P-C (a validar) — decidir si TSE adopta la doble intensitat d'actiu.** És l'única diferència amb valor semàntic (P4′.3). Si s'adopta, cal afegir el `--gold` ple com a estat "eina activa" i deixar `goldPale` per a "seleccionat".

💡 **P-D (a validar) — els tokens que falten a `COL`.** `--charcoal` (capçalera de secció) i `--ok`/`--err` (+`-bg`) no són a `COL` (`:73-85`), però **sí que existeixen** a `index.css` (`:22`, `:28-29`, `:32-33`). Si el contenidor de POMs de l'editor ha de tenir capçalera fosca i xip de veredicte com el Taller, només cal afegir-los a `COL` — cap token nou.

💡 **P-F (a validar) — arreglar els dos tokens trencats (P4′.6), independentment d'aquesta feina.** `--bg-page` i `--mono` s'usen i **no estan definits**. Són deute preexistent i de correcció barata, però convé decidir-ho conscientment: definir `--mono` faria visible una distinció mono/sans que **avui no existeix** (tot és mono per `index.css:56`), i podria canviar l'aspecte de 10 fitxers alhora. **No és un canvi cosmètic petit.**

💡 **P-E (a validar) — el contenidor de POMs de l'editor pot calcar `ModelPomList`** (P1.3) sense inventar res: semàfor de `borderLeft` 3px, codi en mono bold manant, nom EN al costat, badge de `nom_fitxa`, i **la xifra sense tenyir — el color el porta el xip**.

---

## TAULA FINAL — EXISTEIX / FALTA / DIFERENT / DERIVA

| # | Peça | Estat | Ancoratge |
|---|---|---|---|
| 1 | Vocabulari de color | **JA UNIFICAT** | `COL :73-85` = `var()` del Taller |
| 2 | `--charcoal` a `COL` | **FALTA** (però existeix a `index.css:22`) | `COL :73-85` |
| 3 | `--ok`/`--err` a `COL` | **FALTA** (però existeixen a `index.css:28-33`) | `COL :73-85` |
| 3b | `--bg-page` | **USAT I NO DEFINIT** | `TallerPatro.jsx:1097`; cap definició |
| 3c | `--mono` | **USAT I NO DEFINIT** (10 fitxers) | només `Login.jsx:262` inline; salva-ho `index.css:56` |
| 4 | Radi de cantonada | **DERIVA** | Taller 4/6 · TSE 5/6/8 |
| 5 | Pes del títol de secció | **DERIVA** | 600 (`:1332`) vs 700 (`:5343`) |
| 6 | `letter-spacing` del títol | **DERIVA** | 0.03em vs 0.05em |
| 7 | Opacitat de deshabilitat | **DERIVA ×4** | 0.5 · 0.45 · 0.42 · 0.4 |
| 8 | Mides de botó petit a TSE | **DERIVA INTERNA ×3** | 32×32 · 30×26 · 28×26 |
| 9 | Gruix de vora dashed | **DERIVA** | 1px vs 1.5px |
| 10 | Doble intensitat d'actiu | **DIFERENT (disseny)** | Taller `:1356` vs TSE `:3694` |
| 11 | Mètode de dimensionat | **DIFERENT** | padding (Taller) vs width/height (TSE) |
| 12 | Separador vertical | **IDÈNTIC** | `PatternViewer.jsx:870` = `:5363` |
| 13 | Escala tipogràfica | **IDÈNTICA** | `--fs-*` als dos |
| 14 | `Contenidor` exportable | **FALTA** | `TallerPatro.jsx:1310` |
| 15 | Col·lapsables a TSE | **NO EXISTEIX** | cap chevron al dock |
| 16 | Contenidor de POMs a TSE | **NO EXISTEIX** | grep `pom` al dock: cap |
| 17 | Fila de POM reutilitzable | **EXISTEIX** | `ModelPomList.jsx:82-263` |
| 18 | Eines de paleta a moure | **2 de 22** | `:3886`, `:3887` |
| 19 | Bloc de subpath orfe si migra | **RISC** | `:4947-4966` ← `:4583` |
| 20 | Tab "Editar" vs G4 | **DIFERENT** | `:4077-4081`, `:4100` |
| 21 | TallerPatro com a ribbon | **NO EXISTEIX** | `:1158`, `:1370-1395` |
| 22 | Duplicat "inserir imatge" | **EXISTEIX ×3** | `:4510` · `:4137` · `:4189` |
| 23 | Swatches de la paleta | **MORTS** | `:3930-3932`, `:4518` |

---

## Annex — material de layout (P4/P5 retirats)

Es conserva com a **fet**, sense recomanació, perquè l'abast exclou moure components entre panells.

- Panell dret de TSE: `<aside>` `:4670-5110`, **`width: 270`** en un únic lloc (`:4670`), amb `borderLeft` com a **única propietat direccional**. Panell esquerre del Taller: `width: 360` (`:1096`).
- `<main>` de TSE (`:4438`): `flex:1, display:'flex', minHeight:0, position:'relative'`, amb 3 fills — paleta `:4461` (46 px), centre `:4527` (grid amb regles de 18 px), aside `:4670`.
- **No hi ha lògica acoblada a la posició** dels panells: `offsetLeft` **NO EXISTEIX** al fitxer; resta d'amplada (`- 270`, `- 46`) **NO EXISTEIX**; `syncRuler` (`:1944-1949`) treballa amb la **diferència de dos rects vius**; el pan (`:3126-3140`) amb **deltes**; el canvas amb `stage.getPointerPosition()` (`:2854`); els flyouts es reancoren sols del rect viu (`:4481`, `:4490`).
- **Drag&drop al dock: NO EXISTEIX** (només drop de fitxers del SO a `:4707`). Capes reordena **per botons de fletxa** (`:4782`, `:4784`), no per arrossegament.

---

### Obert / pendent de verificar

- **La captura de referència no s'ha rebut**: tot P1/P2/P4′ surt del codi, no d'una comparació visual.
- No s'ha mesurat cap valor renderitzat al navegador: tots els números són els literals del codi. En particular, **P4′.6 dedueix el comportament de la cascada CSS per lectura, no per inspecció** — convindria confirmar-ho amb DevTools abans d'actuar-hi.
- `PaperFlatEditor` (`:4649`, lazy) no s'ha auditat per dins.
