# REPORT · S37 — Vet de C5: chip de la casa + fora hex

> Tanca el 🔴 VET del `guardia-ui` sobre C5 (`b406cdfc`) descrit a
> [`REVISIO_C1C6_2026-08-07.md` §2](REVISIO_C1C6_2026-08-07.md).
> Abast: **només el vet**. Cap pantalla nova, cap canvi funcional, cap backend.
> Data: 2026-08-07 · branca `dev` · sense push.

---

## 0 · Resum

| Punt del vet | Estat |
|---|---|
| §2.1 · Chip duplicat → Chip de la casa | ✅ FET · component duplicat esborrat, 0 consumidors |
| §2.2 · 4 hex amb token exacte | ✅ FET · `--gold-pale` ×2 + `--err` ×1 (el 3r `--gold-pale` vivia dins el chip esborrat) |
| §2.2 · 3 hex sense token | 🛑 **NO tocats — decisió de l'Agus** (§4) |
| Contrast de l'estat «triat» | ✅ 2.80:1 → **6.73:1** (AA demana 4.5:1) |
| `npm run build` | ✅ verd |
| `eslint` | ✅ **0 errors** (1 warning preexistent, idèntic a HEAD) |
| Fum de navegador ca/en/es | ✅ 2 pantalles de 3 · **Graduació és codi mort** (§5.3) |
| **Veredicte del `guardia-ui`** (el mateix que va vetar) | ✅ **VET TANCAT** |

> **ANNEX (micro-tram posterior, mateix dia).** L'Agus aprova els 2 tokens proposats a
> §4 i el fix del botó anotat a §6. Executat a §7-§9. Els 🛑 de §4 queden **resolts**.

---

## 1 · El component duplicat: cens abans d'esborrar

**El duplicat:** `RunRestrictionEditor.jsx:18-24` (a HEAD) — una factoria d'estil
`chip(actiu)`, no un component: retornava un objecte d'estil que s'aplicava a un
`<button>` cru dins `Capa`.

**Cens d'ús ABANS d'esborrar** (`grep -rn` a tot `frontend/src`):

| Consumidor de `chip()` | Fitxer:línia | Migrat a |
|---|---|---|
| Els botons de les 4 capes, dins `Capa` | `RunRestrictionEditor.jsx:36` | `<Chip>` de `grading/wizardUI` |

**Total: 1 consumidor, tots dins el mateix fitxer.** La factoria era local (`const`
sense `export`) → cap altre fitxer del repo la podia consumir, i cap l'havia copiada.
Un cop migrat l'únic consumidor, el cens dona **zero** i el component s'esborra.

**Cens del fitxer sencer** (qui consumeix `RunRestrictionEditor`, per saber el radi):

| Consumidor | Fitxer:línia |
|---|---|
| `SizeSetDetail` (detall del run · Biblioteca de talles) | `SizeSetDetail.jsx:9` (import) · `:199` (ús) |

Un sol consumidor, una sola pantalla.

### El contracte encaixa — no ha calgut aturar-se

El `Chip` de la casa (`components/grading/wizardUI.jsx:25`) declara
`{ active, onClick, disabled, motiu, children }`. L'antic era un `<button>` pelat
amb un objecte d'estil: **sense `title`, sense `disabled`**. El contracte nou és per
tant un **superset estricte** — `Capa` només fa servir `active`+`onClick`+`children`,
i `disabled`/`motiu` queden disponibles, com ja passa a `ModelWizard.jsx:637`.

**Cap capacitat perduda.** Els chips ORFES de grup (`RunRestrictionEditor.jsx:87-89`,
els codis que el run ja porta però que no són a la llista viva) es concatenen a
`opcions` i passen pel mateix `Chip`. Com que `orfes` es deriva de `triats.grup_codis`,
sempre entren amb `active=true` → blanc sobre `--warn` (6.73:1) i a `--fs-body` 12px
en comptes de `--fs-label` 10px: **l'orfe és ara més llegible que abans**.

El propi `wizardUI.jsx:1-8` porta escrit que el component ha de ser un de sol i
«**MAI una còpia**». Ara ho és: les mateixes capes (target al wizard, fit a
Graduació, les 4 capes del run) comparteixen un únic control.

---

## 2 · Contrast: el motiu mesurable del vet

Ràtios WCAG 2.1 calculats de nou sobre els valors reals d'`index.css`
(no reproduïts del report anterior):

| Estat | Abans (chip duplicat) | Després (Chip de la casa) |
|---|---|---|
| **TRIAT** | `--gold` `#c27a2a` sobre `#f5e6d0` → **2.80:1** ❌ | `--white` `#ffffff` sobre `--warn` `#854f0b` → **6.73:1** ✅ |
| NO triat | `--text-muted` `#868685` sobre `--white` → **3.64:1** ❌ | `--text-main` `#1d1d1b` sobre el panell (fons transparent) → **16.23:1** ✅ |

AA demana 4.5:1. **Els DOS estats del chip duplicat queien per sota**; el vet només
havia mesurat el «triat». Els dos els compleix ara.

> Matís sobre la xifra del vet: §2.2 citava «≈5.9:1» per al parell de la casa. Aquest
> és el ràtio de `--warn` sobre `--warn-bg` (**5.87:1**), que no és el que el `Chip`
> pinta de debò: pinta text `--white` sobre fons `--warn`, que dona **6.73:1**. La
> conclusió no canvia (tots dos passen AA); la xifra correcta és 6.73.

**El color ja no és l'únic senyal: en són quatre.** Vora `0.5px → 1.5px`, pes
tipogràfic `400 → 500`, fons `transparent → --warn`, text `--text-main → --white`
(`wizardUI.jsx:29-31`). La clàusula «el color és l'únic senyal de seleccionat» del vet
queda satisfeta. Segueix sense `aria-pressed` —anotat a §6, però és el comportament
del control de la casa i el brief prohibeix adaptar-lo.

---

### 2.1 · L'aspecte canvia (i havia de canviar) — però no trenca res

El `Chip` de la casa és més gran que la variant esborrada: padding `6px 14px` vs
`3px 10px`, radi `6` vs `3`, `--fs-body` 12px vs `--fs-label` 10px. Comprovat:

- **Cap desbordament possible.** El contenidor (`SizeSetDetail.jsx:109`) no té amplada
  fixa i la fila de chips és `flexWrap: "wrap"` (`RunRestrictionEditor.jsx:29`): els
  chips creixen i **embolcallen**. La capa de grup (12 grups reals a `fhort`) ocupa
  més files, i prou.
- **Cap comparació costat a costat** amb els tags de lectura: mai coexisteixen (§6).
- **Guanya coherència amb els germans:** la tria de target aquí és ara literalment el
  mateix control que a `ModelWizard.jsx:637`, i el fit el mateix que a
  `GraduacioPanel.jsx:136` — exactament el que demanava el brief de C5 («els mateixos
  chips de N2, cap layout nou») i que C5 no va complir.

---

## 3 · Taula hex → token (els 4 amb token exacte)

| Literal | Fitxer:línia (a HEAD) | Token | Estat |
|---|---|---|---|
| `#f5e6d0` | `RunRestrictionEditor.jsx:21` (dins `chip()`) | `--gold-pale` | ✅ **desapareix** amb el component esborrat |
| `#f5e6d0` | `RunRestrictionEditor.jsx:132` (botó Desar) | `--gold-pale` (`index.css:17`) | ✅ substituït |
| `#f5e6d0` | `SizeSetDetail.jsx:169` (toggle ⚑ Restriccions) | `--gold-pale` | ✅ substituït |
| `#a32d2d` | `RunRestrictionEditor.jsx:126` (missatge d'error) | `--err` (`index.css:45`) | ✅ substituït |

**4 de 4 tancats.** Els valors són idèntics als dels tokens → **canvi zero de píxel**
en aquests quatre punts; l'única diferència visual de tot el tram és el chip.

---

## 4 · 🛑 Els 3 hex sense token exacte — DECISIÓ DE L'AGUS

No s'han tocat. Substituir-los **canviaria el color de debò** (no és una equivalència
com les de §3), i això és una decisió de disseny, no de neteja. El vet ja ho deia:
«demanen decisió: batejar-los o alinear-los».

### 4.1 · `#e0c8a0` ×2 — vora daurada

Ubicacions al delta: `RunRestrictionEditor.jsx:93` (vora del panell) ·
`SizeSetDetail.jsx:170` (vora del toggle ⚑).

| Candidat | Valor | Distància | Encaixa? |
|---|---|---:|---|
| `--border` | `#e0d5c5` | ΔE76 **14.5** · ΔRGB 39 | ❌ ΔE>10 és diferència clarament visible: `#e0c8a0` és vora **daurada**, `--border` és crema neutra |
| `--gold-pale` | `#f5e6d0` | ΔE76 14.8 · ΔRGB 60 | ❌ massa clar per a una vora |
| `--base-hairline` | `#e3cfa3` | ΔRGB 8.2 | ❌ el més proper en valor, però semàntica errònia: «filet de la columna de talla base (graella fitting)» (`index.css:23`) |

**Cap token raonable. Recomanació: batejar-lo.** No és un valor d'aquesta peça: són
**13 usos en 8 fitxers** (`SizeSetDetail.jsx` ×3, `ImportWizard.jsx` ×3,
`POMBrowser.jsx` ×2, `RunRestrictionTags.jsx:63`, `SizeSetCard.jsx:57`,
`GradingRuleSets.jsx`, `MeasurementBaseGrid.jsx`, i aquest). És **la vora daurada de
facto del sistema, sense nom**. Proposta: `--gold-border: #e0c8a0` a `index.css`, al
costat de `--gold-pale`, en peça pròpia de tokens. L'alternativa (`--border`) el faria
gris i trencaria la lectura «daurat = acció».

### 4.2 · `#fdfaf6` ×1 — fons del panell

Ubicació: `RunRestrictionEditor.jsx:94`.

| Candidat | Valor | Distància | Encaixa? |
|---|---|---:|---|
| `#fdf9f5` (**no és token**) | `#fdf9f5` | ΔE76 **0.45** · ΔRGB 1.4 | el veí — visualment indistingible |
| `--bg-card` | `#fafafa` | ΔE76 2.3 · ΔRGB 5.0 | ⚠️ passable de xifra, però és **gris neutre** i això és crema: trencaria la família |
| `--fila-activa` | `#fdf8ee` | ΔRGB 8.2 | ❌ semàntica errònia: reservat a la fila enfocada de la taula de mesures (`index.css:24-27`) |

**El cens decideix:** `#fdfaf6` s'usa **exactament UN cop a tot el frontend** —aquesta
línia—, mentre que `#fdf9f5` en té **8 en 5 fitxers**, i **tres són els panells
germans de la MATEIXA pantalla** (`SizeSetDetail.jsx:217` historial, `:343`, `:363`,
més la zebra `:261`). A ΔE76 0.45 no és una decisió de color: és un **4t crema
gratuït**, molt probablement un `#fdf9f5` mal copiat.

**Recomanació:** alinear-lo a `#fdf9f5` (cost zero, mata una divergència) i, com a pas
net posterior, batejar aquell valor (`--bg-panel-warm`) i propagar-lo als 8 usos.
Alinear sol NO compleix la llei —seguiria sent hex—, per això el bateig és el final.

**Totes dues propostes són fora de l'abast d'aquest tram** (tocarien 14+ fitxers).
Queden aquí per a la decisió.

---

## 5 · Verificació

### 5.1 · Portes dures

| Control | Resultat |
|---|---|
| `npm run build` (`frontend/`) | ✅ **verd** — `✓ built in 795ms` |
| `npx eslint` dels 2 fitxers | ✅ **0 errors**, 1 warning |
| El warning, ¿és baseline? | ✅ **preexistent i idèntic a HEAD**: `SizeSetDetail.jsx:40 react-hooks/set-state-in-effect`, dins un `useEffect` que aquest tram no toca. Verificat linant la còpia de `git show HEAD:…` → mateix «0 errors, 1 warning» |
| i18n ca/en/es | ✅ **cap clau nova ni tocada**; paritat 15/15/15 de les claus de C5 |
| El bundle porta el canvi | ✅ `dist/assets/index-*.js` reconstruït a les 11:50:35, amb `gold-pale` dins |

> ⚠️ A staging, `nginx` serveix `frontend/dist` → **construir ÉS desplegar**. El canvi
> ja és viu a `staging.fhorttextile.tech`. El commit només guarda el FONT.

### 5.2 · Fum de navegador — ca/en/es, amb captures

**Mètode.** Contra el bundle `frontend/dist` de les 11:50 (el que ja porta el canvi:
`SizeLibrary-*.js` conté `var(--gold-pale)` ×2 i `var(--err)`, i importa
`wizardUI-*.js`, l'únic chunk amb `1.5px solid var(--warn)`). Servit i stubejat des
d'UN sol `page.route('**/*')`; **cap crida surt a xarxa**, o sigui que la validesa del
token és irrellevant. Botons localitzats per ICONA, mai pel text traduït.

Captures a [`captures-c5-chip-s37/`](captures-c5-chip-s37/).

| Pantalla | ca | en | es | Captura |
|---|:-:|:-:|:-:|---|
| **Editor de restriccions del RUN** (la migrada) | ✅ | ✅ | ✅ | `c5_restriccions_{ca,en,es}_triat.png` |
| **Wizard · chips de TARGET** | ✅ | ✅ | ✅ | `wizard_pas2_{ca,en,es}_triat.png` |
| **Wizard · pas 3 «Talles»** (mateix `Chip`) | ✅ | ✅ | ✅ | `wizard_pas3_talles_{ca,en,es}_triat.png` |
| **Graduació** (`GraduacioPanel.jsx:136`) | 🚫 | 🚫 | 🚫 | **inaccessible — v. avall** |
| Abans/després del chip, costat a costat | — | — | — | `c5_chip_abans_despres.png` |

**Estat «triat» confirmat en viu:** `background rgb(133,79,11)` (= `--warn`) +
`color rgb(255,255,255)`, idèntic al del wizard. Les 4 capes amb almenys un triat.

**Cap canvi de comportament** (era la condició d'aturada del brief):
- el toggle commuta als DOS sentits als 3 idiomes (`transparent` ⇄ `rgb(133,79,11)`);
- el **chip ORFE** (`ZZ-ORFE-LEGACY`, codi que el run porta però que no és a la llista
  viva) segueix sortint i segueix actiu — la conservació de `:87-89` no s'ha trencat;
- zero errors JS a consola;
- `SizeSetDetail.jsx:169` resol en viu a `rgb(245,230,208)` = exactament l'antic
  `#f5e6d0`. **Canvi de token pur, zero píxels de diferència**, com anunciava §3.

**⚠️ Correcció al brief:** els chips de `ModelWizard.jsx:637-639` viuen al **pas 2
(«Peça»)**, no al 3. El pas 3 («Talles») també usa el mateix `Chip` i s'ha capturat
igualment. Tots dos intactes, com tocava.

### 5.3 · 🚫 Graduació no s'ha pogut veure — i el motiu importa

`GraduacioPanel` **no és arribable des de cap superfície viva de l'app d'avui**:

- només es munta a `ModelWizard.jsx:853`, sota `block === 4 && mostraGrading`;
- `mostraGrading = initialBlock === 4` (`ModelWizard.jsx:509`);
- `initialBlock` és **només un prop**, mai un query param (`:71`, cap `useSearchParams`),
  i **cap fitxer del repo el passa** (`grep -rn "initialBlock\|embedModelId" src/` → 0
  resultats fora del propi `ModelWizard.jsx`);
- el stepper té **3 passos** (confirmat a la captura): el pas 4 no existeix;
- el calaix de Graduació del `ModelSheet` ja no el fa servir — usa
  `GraduacioContenidor.jsx`, que **no importa `Chip`**.

**No és regressió d'aquest tram** (`wizardUI.jsx` no s'ha tocat, `git diff` buit), però
és **codi mort** i el vet el citava com a consumidor viu. S'anota: el cens real de
consumidors del `Chip` de la casa és **3 imports, 2 arribables**
(`ModelWizard.jsx:10` ✅ · `RunRestrictionEditor.jsx:4` ✅ · `GraduacioPanel.jsx:7` 🚫).

### 5.4 · Límit honest d'aquest fum

Va contra API **stubejada** —el gunicorn viu rebutja els tokens encunyats des del
shell, i no es creen usuaris de QA a staging—. Per tant valida **el render i la
interacció** del bundle desplegat, i **no** el contracte del backend: el
`PATCH /api/v1/size-systems/{id}/` de «Desar restriccions» **no s'ha exercit contra
dades reals**. Aquest tram no toca cap camí de desat, o sigui que el risc és el mateix
que abans; però queda dit.

---

## 6 · Fora d'abast, anotat (no tocat)

CLAUDE.md: «Scope creep vist fora de scope → s'ANOTA al report, no es toca».

- 🔴 **El botó «Desar restriccions» arrossega EXACTAMENT el mateix defecte de contrast
  que el chip vetat.** `RunRestrictionEditor.jsx:127` pinta `--gold #c27a2a` sobre
  `--gold-pale #f5e6d0` = **2.80:1**, la mateixa parella que el vet va mesurar al chip.
  Es veu a ull a `c5_restriccions_ca_triat.png`. Aquest tram n'ha tokenitzat el color
  (§3) però **el ràtio no canvia: un token no arregla un contrast**. El vet no ho
  cobria —només parlava del chip— i és l'**acció principal** del panell. Mereix peça
  pròpia; les parelles de la casa disponibles són `--white` sobre `--gold` (**3.44:1**,
  segueix fallant AA) o `--white` sobre `--warn` (**6.73:1**, la del chip).
  **Decisió de disseny.**
- **`#f5e6d0` amb token exacte disponible sobreviu a 5 punts FORA del delta de C5:**
  `SizeSetDetail.jsx:139` (toggle Historial) i `:284` · `RunRestrictionTags.jsx:63` ·
  `SizeSetCard.jsx:57` i `:97`. Mateix cas exacte que els de §3 (`--gold-pale`), però
  no són d'aquesta peça.
- **`RunRestrictionTags.jsx:63`** (la vista de LECTURA de les mateixes 4 capes) manté
  el seu propi estil de tag petit i daurat. **No és el chip duplicat que el vet
  assenyala** —és lectura, no tria— i **mai coexisteix amb l'editor**:
  `SizeSetDetail.jsx:198-211` és un ternari, o l'un o l'altre. No hi ha comparació
  costat a costat, i per tant cap regressió; el que hi ha és la mateixa informació amb
  dos aspectes segons el mode. Val la pena mirar-s'ho algun dia.
- **`aria-pressed` absent al `Chip` de la casa** — forat del component COMPARTIT, el
  pateixen igual `ModelWizard.jsx:637` i `GraduacioPanel.jsx:136`. El repo l'usa a
  10+ llocs (`PieceList.jsx:27`, `ModelPomList.jsx:113`, `fittingGridAdapter.jsx:193`…).
  Arreglar-lo és peça pròpia sobre `wizardUI.jsx`, no d'aquest delta.
- **Altres factories de chip al repo** (`pattern/SegmentEditor.jsx:21`,
  `pattern/SewEditor.jsx:40`, `planning/ProjectGantt.jsx:267`, i un `Chip` local a
  `planning/DashboardGovPanel.jsx:103`): **cap és còpia d'aquesta** —geometries i
  tokens diferents, i totes anteriors a C5. S'anoten, no es veten.
- **Els chips ORFES de grup són irrecuperables un cop destogglejats**
  (`RunRestrictionEditor.jsx:87-89`): la llista `orfes` es deriva de `triats`, o sigui
  que treure un orfe el fa desaparèixer i no es pot tornar a afegir. **Preexistent de
  C5**, no tocat aquí. Ara que el `Chip` de la casa exposa `motiu`, l'orfe podria dur
  un `title` explicatiu («codi no present al catàleg viu») — capacitat que l'antic
  chip no tenia.
- Vora del chip NO triat (`--gray-l #f0f0f0`) sobre el panell crema: **1.10:1**, sota
  el 3:1 de WCAG 1.4.11. El text hi és a 16:1, i és propietat del component compartit
  sobre qualsevol fons clar. Informatiu.
- `gap: 5` a la fila de chips (`RunRestrictionEditor.jsx:29`) queda just per a un chip
  de radi 6 i padding 14px; els germans van a `gap: 8`. Estètic, no trenca.

---
---

# ANNEX · Micro-tram: 2 tokens nous + fix de contrast del botó primari

> Decisió de l'Agus (Patró C, 07/08/2026): aprovats els dos tokens proposats a §4 i el
> fix del botó anotat a §6. Abast tancat a aquestes 3 coses.

## 7 · Els dos cremes, resolts

### 7.1 · `--gold-border: #e0c8a0` — batejat i propagat

Declarat a `frontend/src/index.css:22`, al costat de `--gold-pale`. **Valor idèntic al
literal → zero canvi de píxel.** Els 13 usos censats a §4.1, migrats un per un:

| Fitxer | Línia(es) | Usos | Què és |
|---|---|:-:|---|
| `components/RunRestrictionEditor.jsx` | 93 | 1 | vora del panell de restriccions |
| `components/SizeSetDetail.jsx` | 170, 183, 231 | 3 | toggle ⚑, toggle ✎, vora del missatge `warn` |
| `components/SizeSetCard.jsx` | 57 | 1 | vora del tag de restricció a la card |
| `components/RunRestrictionTags.jsx` | 63 | 1 | vora del tag de LECTURA de les 4 capes |
| `components/POMBrowser/POMBrowser.jsx` | 447, 489 | 2 | vora del POM clau · vora de la capçalera |
| `components/ImportWizard/ImportWizard.jsx` | 912, 1093, 1280 | 3 | vores de les 3 caixes d'avís daurades |
| `components/MeasurementBaseGrid/MeasurementBaseGrid.jsx` | 313 | 1 | vora de la cel·la daurada |
| `pages/GradingRuleSets.jsx` | 516 | 1 | vora del badge |
| **TOTAL** | | **13** | **en 8 fitxers** |

### 7.2 · `#fdfaf6` → `#fdf9f5` — el crema accidental, col·lapsat

L'ús únic (`RunRestrictionEditor.jsx`, fons del panell) passa al valor dels panells
germans de la mateixa pantalla. **Segueix sent un literal**, com deia el brief: `#fdf9f5`
no té token, i no se n'ha creat un tercer per a això.

> 🚩 **Queda obert:** `#fdf9f5` són ara **10 usos en 6 fitxers** sense nom
> (`SizeSetDetail`, `GradingRuleSets`, `SizeLibrary`, `GradingHistoryPanel`,
> `POMBrowser`, i aquest). El bateig (`--bg-panel-warm` o similar) és la peça següent
> d'aquesta neteja, no aquesta.

## 8 · El botó «Desar restriccions»: 2.80:1 → 6.73:1

### 8.1 · Hi havia DUES parelles primàries, i comparteixen nom

Buscant el botó primari canònic apareix una col·lisió que val la pena saber:

| On | Parella | Ràtio | Abast |
|---|---|---:|---|
| `components/ui/buttons.js:10` — `primaryBtn` **exportat** | `--white` sobre `--gold` `#c27a2a` | **3.44:1** ❌ | **58 botons en 26 fitxers** |
| `pages/ModelWizard.jsx:942` — `primaryBtn` **local**, mateix nom | `--white` sobre `--warn` `#854f0b` | **6.73:1** ✅ | l'acció primària del wizard (Següent · Crear · Desar) |

**Triada: `--white` sobre `--warn`.** És l'única de les dues que compleix AA, ja és la
parella d'una acció primària de la casa, i és **la mateixa que el `Chip` triat** del
mateix panell — o sigui que el panell queda amb una sola família de to. Precedent
exacte: el wizard ja conviu amb chips `--warn` i botó primari `--warn`.

Descartades per no complir AA (i per no inventar res): `--gold-l` (3.13:1),
`--gold` (3.44:1). `--grana` compleix (8.96:1) però és **color de marca**, no d'acció.

### 8.2 · El canvi

`RunRestrictionEditor.jsx` — el botó passa de `--gold` sobre `--gold-pale` a `--white`
sobre `--warn`, amb `fontWeight: 500` i `border: none` (la resta de la parella
canònica). L'estat `desant` manté el tractament que ja tenia (`opacity: .6`,
`cursor: not-allowed`); WCAG 1.4.3 exclou els controls inactius.

| | Parella | Ràtio |
|---|---|---:|
| Abans | `--gold` `#c27a2a` sobre `--gold-pale` `#f5e6d0` | **2.80:1** ❌ |
| Després | `--white` `#ffffff` sobre `--warn` `#854f0b` | **6.73:1** ✅ |

## 9 · Verificació de l'annex

| Control | Resultat |
|---|---|
| `npm run build` | ✅ verd — `✓ built in 832ms` |
| `grep` final de `#e0c8a0` al codi font | ✅ **0 usos** (només la declaració del token a `index.css:22`) |
| `grep` final de `#fdfaf6` | ✅ **0 usos** (només una menció dins un comentari) |
| `eslint` dels 8 fitxers tocats | ⚠️ **0 errors introduïts**, però **2 de preexistents** — v. avall |
| Fum del panell (el botó FUNCIONA) | ✅ PATCH real capturat, camí OK i camí d'error (§9.2) |
| Zero píxels del token | ✅ `rgb(224,200,160)` en viu · 6/13 mesurats, 7/13 per prova estàtica |

### 9.1 · ⚠️ El `eslint` d'aquest annex NO és «0 errors» — i el motiu

El brief demanava `eslint` a 0 errors. Els 8 fitxers donen **2 errors**, tots dos a
`ImportWizard.jsx` i tots dos **preexistents i idèntics a HEAD** (verificat linant la
còpia de `git show HEAD:…`): `no-unused-vars` a `:80` (`TallaChip`) i `:315`
(`docLabels`). **Aquest tram no n'introdueix cap**; a `ImportWizard.jsx` només hi ha
tocat 3 literals de color. Esborrar-los seria una 4a cosa i el brief tanca l'abast a 3.

> 🔴 **`TallaChip` (`ImportWizard.jsx:80`) és una 5a variant de chip, i és MORTA.** Mai
> s'usa, i porta **6 hex crus** —`#f0f9f0`, `#fff0f0`, `#c0dd97`, `#f0c0c0`, `#3b6d11`,
> `#a32d2d`—, dos dels quals tenen token EXACTE (`--ok` = `#3b6d11`, `--err` =
> `#a32d2d`). Esborrar-la tanca l'error de lint i 6 hex de cop. Peça pròpia.

### 9.2 · Fum del panell — el botó FUNCIONA, no només es pinta

Contra el `dist` fresc, tot stubejat des d'un únic `page.route`. Captures a
[`captures-c5-chip-s37/`](captures-c5-chip-s37/): `b_boto_abans_despres.png`,
`a_panell_ca.png`, `a_error_400_ca.png`, `c_llista_badges_ca.png`.

**Colors resolts en viu** (`getComputedStyle`): `background rgb(133,79,11)` (`--warn`) ·
`color rgb(255,255,255)` (`--white`) · `fontWeight 500` · `border none`. Tot com toca.

**El PATCH real capturat** (cos de la petició, no una suposició):
```
PATCH /api/v1/size-systems/7/
{"target_codis":["WOMAN","MATERNITY","MAN"],"grup_codis":["TOPS","DRESSES","ZZ-ORFE-LEGACY"],
 "construccio_codis":["WOVEN"],"fit_codis":["REGULAR"]}
```
Les 4 llistes hi són i **reflecteixen exactament els clics fets** (`MAN` afegit a target,
`SLIM` tret de fit). El codi **orfe** `ZZ-ORFE-LEGACY` sobreviu al viatge.

| Camí | Resultat |
|---|---|
| Toggle dels chips abans de desar | ✅ commuten als dos sentits (`rgba(0,0,0,0)` ⇄ `rgb(133,79,11)`) |
| Resposta 200 | ✅ el panell es tanca (0 panells al DOM) |
| Resposta 400 `{"detail":…}` | ✅ el text del servidor es pinta en `--err` (6.75:1), el panell **segueix obert**, el botó es re-habilita |
| Errors de JS a consola | ✅ cap (només el del 400 provocat) |

**Zero píxels al token:** `--gold-border` resol en viu a `rgb(224,200,160)` = `#e0c8a0`.
Mesurats al DOM **6 dels 13 usos** (panell, toggle ⚑, botó ✎, badge de
`RunRestrictionTags`, badge de `SizeSetCard`), tots idèntics. Els **7 restants**
(`GradingRuleSets:516`, `POMBrowser:447,489`, `MeasurementBaseGrid:313`,
`ImportWizard:912,1093,1280`) **no s'han mesurat en viu** —el `CascadeSelector` de
`/poms/grading` no avança amb dades stubejades—, però queden coberts per prova
estàtica: `dist/assets/*.css` emet `--gold-border:#e0c8a0`, i **cap chunk JS de `dist/`
conté ja el literal `e0c8a0`**. És prova per construcció, no mesura de píxel; queda dit.

### 9.3 · 🚩 Defecte PREEXISTENT trobat pel fum: el missatge de desat no apareix MAI

En resposta OK no es pinta cap missatge (mostrejat cada 50 ms durant 2 s: cap).
La causa, verificada al codi:

- `SizeSetDetail.jsx:202-207` (`onSaved`) fa `setMsg({type:'ok', …})` i **tot seguit**
  crida `onRefresh()`;
- `SizeLibrary.jsx:98` defineix `onRefresh` com
  `() => { setDetailProfileId(null); setSelectorKey(k => k + 1) }` — o sigui que
  **desmunta el `SizeSetDetail` sencer** abans que el missatge arribi a pintar-se.

Efecte col·lateral: qui desa **perd tot el context** — el detall es tanca i el selector
de target es remunta buit. **Preexistent, idèntic a HEAD**, i `SizeLibrary.jsx` no s'ha
tocat en cap dels dos trams (`git diff HEAD` buit per a aquell fitxer): aquest micro-tram
només ha canviat colors i no ha regressat res. **S'anota, no es toca.**

## 10 · Fora d'abast, anotat (no tocat)

- 🔴 **El `primaryBtn` COMPARTIT falla AA a tot el mòdul comercial.**
  `ui/buttons.js:10` és `--white` sobre `--gold` = **3.44:1**, i el fan servir **58
  botons en 26 fitxers** (`ProductDetail`, `QuoteDetail`, `DeliveryNoteDetail`,
  `Planning`, `GeneralConfig`, `Encarrecs`…). És el **mateix defecte que el vet va
  obrir**, però multiplicat per 58 i al component compartit. Canviar-lo a `--warn`
  ho arreglaria d'una sola línia — però és un canvi d'aspecte a mig producte:
  **decisió de l'Agus, no d'un agent.**
- **Dos `primaryBtn` amb el mateix nom** (l'exportat i el local de `ModelWizard.jsx:942`)
  és la mateixa malaltia que el chip de C5: una variant local que ombreja el nom del
  component compartit. El local és el que està BÉ; el compartit és el que falla.
- `TallaChip` mort a `ImportWizard.jsx:80` (§9.1).
- **`GraduacioPanel` confirmat codi mort** — ja recollit a §5.3: `initialBlock` mai
  passat, stepper de 3 passos. Candidat de neteja, i **afecta el disseny futur de la
  pantalla de Grading Rules** (qui la dissenyi no pot donar per fet que Graduació
  s'obre des d'allà: avui no s'obre des d'enlloc).

---
---

# ANNEX 2 · Micro-tram: toast fantasma, TallaChip mort i porta de lint

> Decisió de l'Agus (Patró C, 07/08/2026): corregir el `primaryBtn` compartit ABANS de
> pintar les 4 pantalles noves. **El pas 1 ha quedat ATURAT per la seva pròpia condició
> d'aturada** (§11); els passos 2-4 estan fets i verds.

## 11 · 🛑 El `primaryBtn` compartit: ATURAT, i per què

El brief deia: «🛑 Si en aplicar-ho trobes que `--warn` s'usa també per a estats d'avís
REALS i la col·lisió semàntica és visible en alguna pantalla, ATURA». **Les dues
condicions es compleixen.**

**(a) `--warn` NO és un color d'acció, és un token d'ESTAT.** `index.css:44` el declara
sota `/* Estats (per badges puntuals — mantenir contrast) */`, al costat de `--ok` i
`--err`. Té **122 usos** amb semàntica d'avís: `at_risk` (`Planning.jsx:405`), `Paused`
(`OrderDetail.jsx:299`), `size_map_unmatched` i `g.warning` (`SizeMapSetup.jsx:619,842`),
`msg.type==='warn'` (`GradingRuleSets.jsx:222-223`), rellotge d'alerta
(`GuardTascaOblidada.jsx:273`), «avui» (`PlanningCalendar.jsx:468`).

**(b) La col·lisió seria visible.** `SizeMapSetup.jsx:485-495`: una **caixa d'avís
sencera** (`background: --warn-bg`, `border: --warn`, `color: --warn`) i **just a sota**
un `primaryBtn`. Es repeteix a `:619`→`:630` i `:715/:781/:842`→`:941/:952`.

> **El matís honest, que juga en contra de l'aturada:** aquesta col·lisió **ja existeix
> avui** al wizard — `ModelWizard.jsx:842` pinta un avís en `--warn` i `:942` hi té el
> botó primari local, també `--warn`. La pregunta real no és «apareix una col·lisió
> nova» sinó «com de greu es fa en generalitzar-la a 58 botons de 26 fitxers».

### 11.0 · La resposta, amb evidència visual

**El creuament: 11 dels 26 fitxers ja pinten `--warn`, i 10 amb semàntica d'avís real.**
Són **25 dels 58 botons (43%)** que viurien en una pantalla que ja fa servir el token:
`SizeMapSetup` (12 usos de `--warn` · 7 botons), `TaskAssignWizard` (7·3),
`DictionaryWizard` (5·2), `Encarrecs` (3·1), `Planning` (3·1), `GuardTascaOblidada` (2·1),
`Recursos` (2·1), `CustomerDetail` (2·4), `GarmentTypes` (2·3), `DashboardGovPanel` (1·1),
`OrderDetail` (1·1).

Tres casos que ho ensenyen millor que cap xifra:

- **`TaskAssignWizard.jsx:363-378` — el botó és FILL d'una caixa `--warn`.** La caixa té
  `background: --warn-bg` + `border: --warn`, i el botó «Substituir» (`:375`) hi viu a
  dins. Amb el canvi, el **farciment del botó és la mateixa tinta que la vora de la
  caixa**: deixa de ser una acció DINS d'un avís i es llegeix com una peça de l'avís.
- **`ui/Modal.jsx:21` — la col·lisió viu al COMPONENT COMPARTIT.** Qualsevol modal amb
  un avís al cos la reprodueix; confirmat a `Encarrecs.jsx:203-217` i `Recursos.jsx:185-195`.
- **`Encarrecs.jsx:148`+`:230` — el frame decisiu**
  ([`F_encarrecs_parella_DESPRES.png`](captures-c5-chip-s37/F_encarrecs_parella_DESPRES.png)).
  En 400px hi conviuen el primari «Traspassar (2)», el seu germà secundari «Tots els
  pendents» (`ghostBtn`, `--gold`) i els badges «Pendent» (text `--warn`). Amb el canvi
  **el primari deixa de coincidir amb el seu germà i passa a coincidir amb el badge
  d'avís** — exactament al revés del que ha de fer.

**I el wizard no demostra el que semblava.**
[`E_modelwizard_VIU.png`](captures-c5-chip-s37/E_modelwizard_VIU.png) (captura real,
sense cap injecció): el `ModelWizard` ja és tot `--warn` i **es veu bé**. Però a la
mateixa pantalla hi conviuen tres blocs plens de `#854f0b` — el chip `2026`, el chip
`SS Spring/Summer` i el botó `Següent →`: **l'acció primària és indistingible d'un
toggle seleccionat**. El wizard no prova que `--warn` funcioni com a color d'acció;
prova que funciona **quan és l'únic accent de la pantalla**. En 25 pantalles no ho serà.

### 11.0.1 · 🚨 El fet que decideix: canviar `primaryBtn` NO arregla l'accessibilitat

Hi ha **40 superfícies més amb `background: var(--gold)` i text blanc que NO són
`primaryBtn`** (verificat amb grep), i es quedarien totes a **3.44:1**. Entre elles:

| Superfície | Fitxer:línia |
|---|---|
| **El botó de LOGIN** | **`Entrar.jsx:198`** (`submitBtn`) |
| Restablir contrasenya | `ResetPassword.jsx:75,100` |
| Error boundary de l'app | `App.jsx:274` |
| Tab actiu de Planificació | `Planning.jsx:501` |
| `ModelSheet` ×4 · `FittingDetail.jsx:499` · `GradingRuleSets.jsx:968` · `Dashboard.jsx:483` | — |

O sigui que el pas 1, sol, passaria de **98 superfícies amb un sol color** a **58 marrons
foscos + 40 marrons clars, sense cap regla que ho expliqui** — i deixaria la pantalla
d'entrada, la primera que veu tothom, incomplint AA. **Això no és una millora: és partir
el llenguatge d'acció en dos.**

### 11.1 · Les opcions, amb els ràtios (text `--white`)

| Candidat | Valor | Ràtio | Comentari |
|---|---|---:|---|
| `--gold` (avui) | `#c27a2a` | **3.44:1** ❌ | el defecte a corregir |
| `--gold-l` | `#c68338` | 3.13:1 ❌ | pitjor |
| `--warn` (proposat al brief) | `#854f0b` | **6.73:1** ✅ | passa AA, però és el token d'AVÍS |
| **`#9b6222`** (proposta) | `#9b6222` | **5.04:1** ✅ | **literalment `--gold` al 80% de lluminositat**. Deixaria `--warn` fent només d'avís |
| `--grana` | `#8a1f3d` | 8.96:1 ✅ | compleix, però és **color de MARCA** (`index.css:18`; `--pdf-accent` hi penja) |

🔑 **`--warn` NO és «un `--gold` fosc»** — és un marró **un 20% més saturat**, i d'un to
diferent. `#9b6222` sí que ho és. En HSL:

| | to | saturació | lluminositat |
|---|---:|---:|---:|
| `--gold` | 31.6° | **64.4%** | 46.3% |
| `--warn` | 33.4° | **84.7%** | 28.2% |
| `#9b6222` | 31.7° | **64.0%** | 37.1% |

Per això `--warn` trenca la família i `#9b6222` no: el primari en seria «el germà fosc»,
i el ghost, el tab actiu i els chips seguirien parlant el mateix idioma.

**Recomanació: batejar `--gold-action: #9b6222`.**

> 🚩 **Condició per fer-ho bé:** aplicar-lo NOMÉS a `primaryBtn` deixa viu el problema de
> §11.0.1. La peça sencera és **un únic `--gold-action` als 58 botons I als 40 orfes** —
> i el botó de login n'és el primer. Això ja no és el micro-tram que el brief descrivia:
> és una peça de token de sistema, i la tria de color és **Patró C**.

**`--grana` descartat:** 58 botons granats convertirien cada acció en una declaració
d'identitat de marca, i en lectura ràpida s'acosta massa a `--err`.

### 11.2 · L'altra troballa del pas 1: els dos `primaryBtn` NO es podran fusionar

El brief deia «si ara queda idèntic al compartit, elimina el local». **No quedaria
idèntic ni igualant-ne els colors:**

| | `ui/buttons.js:10` (compartit) | `ModelWizard.jsx:942` (local) |
|---|---|---|
| forma | objecte estàtic | **funció** `(disabled) => ({…})` |
| padding | `7px 14px` | `8px 20px` |
| mida | `--fs-body` (12px) | `--fs-h3` (14px) |
| pes | `600` | `500` |
| `disabled` | no en té — cada crida hi posa `opacity` | parella pròpia (`--gray-l` / `--gray`) |
| layout | `display:flex`, `marginLeft:auto` | cap |

Fusionar-los és una peça pròpia (unificar geometria + estat `disabled`), no un efecte
automàtic d'igualar el color. **No s'ha tocat.**

## 12 · El toast fantasma, arreglat

**El defecte** (trobat pel fum del tram anterior, §9.3): `setMsg` seguit d'`onRefresh()`
que desmunta el component → el missatge no arribava mai a pintar-se.

**La via triada — la de menys codi, i sense cap llibreria de toasts:** el pare
(`SizeLibrary`) **ja tenia** una caixa de missatge global que no es desmunta
(`SizeLibrary.jsx:65-76`, usada per `handleClone` i pel drawer d'autoria). El missatge
només havia de poder-hi arribar. 3 línies:

- `SizeSetDetail.jsx:41` — ajudant `avisaIRefresca(m)`: si hi ha `onRefresh`, li passa el
  missatge; si no, cau al `setMsg` local de sempre (el component segueix servint sol).
- Usat als **dos** punts que el perdien: `handleRestore` (`:91`) i l'`onSaved` de les
  restriccions (`:209`). **El de restaurar patia el mateix defecte i ningú l'havia vist.**
- `SizeLibrary.jsx:100` — `onRefresh={(m) => { …; if (m) setMsg(m) }}`.

Descartat: refrescar sense desmuntar (hauria calgut canviar la política de refresc del
pare, molt més codi i més radi).

### 12.1 · Fum del camí de desat

| Comprovació | Resultat |
|---|---|
| PATCH 200 → **el missatge es veu** | ✅ «Restriccions del run desades» a la caixa global, **primera vista a t+50 ms, present en 39/40 mostres (~1950 ms)**, i viu encara a t+6 s |
| No s'ha duplicat | ✅ la caixa LOCAL del detall queda a 0 ocurrències: el missatge ha MIGRAT |
| La llista reflecteix el canvi | ✅ detall tancat i `SizingProfileSelector` remuntat (+1 `GET construction-types` i +1 `GET sizing-profiles`) |
| Restaurar (↺, `handleRestore`) | ✅ `confirm()` acceptat, `POST …/restaurar/`, el `missatge` del servidor surt a la caixa global (39/40 mostres) |
| Camí d'error (PATCH 400) | ✅ **intacte**: l'error es pinta DINS del panell, el panell NO es tanca, cap missatge global, cap remuntatge (no passa per `onRefresh`) |

Captures: `1b_despres_desar_ca.png`, `1c_missatge_global_ca.png`,
`2_despres_restaurar_ca.png`, `3_error_400_ca.png`.

> Anotat, no tocat: `handleRestore` crida `reloadProfile()` just abans d'`avisaIRefresca`,
> i aquell GET arriba a un component que es desmunta (el `setProfile` és un no-op). És
> feina morta inofensiva. **S'ha conservat a posta**: treure-la seria un canvi de
> comportament fora de l'abast d'aquest brief.

## 13 · `TallaChip` mort i els 2 `no-unused-vars`

**Cens ABANS d'esborrar** (`grep -rn` a `frontend/src` i `frontend-backoffice/src`):

| Símbol | Ocurrències | Consumidors |
|---|:-:|:-:|
| `TallaChip` (`ImportWizard.jsx:80`) | **1** — la seva pròpia definició | **0** |
| `docLabels` (`ImportWizard.jsx:315`) | **1** — la seva pròpia assignació | **0** |

Esborrats tots dos (−22 línies). `TallaChip` era la **5a variant de chip** del sistema, i
mai s'havia usat.

### 13.1 · ⚠️ El grep dels «6 hex de TallaChip» NO pot donar zero — i no és un defecte

El brief demanava «grep 0 ocurrències dels 6 hex de TallaChip». **No és assolible, i
tampoc desitjable:** aquells 6 valors els fan servir components **vius** de tot el
frontend, inclòs el mateix `ImportWizard.jsx`.

| Hex | Usos a `src/` | Fitxers | Token exacte? |
|---|:-:|:-:|---|
| `#3b6d11` | 26 | 14 | **sí — `--ok`** |
| `#a32d2d` | 22 | 13 | **sí — `--err`** |
| `#f0f9f0` | 15 | 11 | no (proper a `--ok-bg` `#eaf3de`) |
| `#fff0f0` | 10 | 7 | no (proper a `--err-bg` `#fcebeb`) |
| `#c0dd97` | 10 | 7 | no |
| `#f0c0c0` | 6 | 3 | no |

**El que SÍ ha quedat a zero:** les 6 instàncies que vivien dins `TallaChip`. La resta
són d'altres components i queden **fora de l'abast** (89 usos). 🚩 Dos d'ells (`#3b6d11`
i `#a32d2d`, 48 usos) tenen token EXACTE i són candidats directes d'un tram de tokens.

## 14 · 🟢 PORTA DE LINT VERDA — amb el recompte

**`eslint` de tot `frontend/src`: 0 errors.** N'hi havia **6**.

| Error | Fitxer:línia | Com s'ha tancat |
|---|---|---|
| `no-unused-vars` `TallaChip` | `ImportWizard.jsx:80` | component mort esborrat |
| `no-unused-vars` `docLabels` | `ImportWizard.jsx:315` | assignació morta esborrada |
| `no-unused-vars` `MONO` | `FittingSessionList.jsx:12` | constant morta esborrada |
| `no-unused-vars` `flatIdRef` | `PaperFlatEditor.jsx:46` | ref morta esborrada |
| `no-unused-vars` `TOOL_SHORTCUT` | `TechSheetEditor.jsx:192` | constant morta esborrada |
| `no-unused-vars` `fileRef` | `TechSheetEditor.jsx:2770` | ref morta esborrada |
| `no-undef` `Buffer` ×2 | `api/jwt.js:31` · `api/avisSessio.test.js:76` | **NO era codi trencat** — v. avall |

Les 4 variables mortes de fora d'`ImportWizard` tenien **una sola ocurrència cadascuna**
(la seva pròpia declaració): cens a zero abans d'esborrar. `TechSheetEditor.jsx` estava
net de canvis de sessions concurrents abans de tocar-lo.

**Els dos `Buffer`:** `api/jwt.js:31` hi cau **només** quan no existeix `atob`
(`typeof atob === 'function' ? atob(…) : Buffer.from(…)`), o sigui a Node, als tests, i el
test hi entra a posta. És codi de Node legítim dins d'un projecte de navegador.
S'han **declarat els globals de Node només per a aquests dos fitxers**
(`eslint.config.js`, bloc nou) en comptes d'apagar `no-undef` — aquella regla és la porta
que W4/T5 va pagar amb una pantalla trencada, i el propi config demana no tocar-la.

**Warnings: 258**, cap de nou. Tots són de la categoria `IDIOMA_I_DX` que
`eslint.config.js:33-43` declara explícitament «s'anota, no atura»
(`set-state-in-effect` 106, `only-export-components` 68, `exhaustive-deps` 29…).

## 15 · Verificació global de l'annex 2

| Control | Resultat |
|---|---|
| `npm run build` | ✅ verd — `✓ built in 913ms` |
| `eslint` de tot `src/` | ✅ **0 errors** · 258 warnings preexistents |
| Suite de tests | ✅ **218/218 passen**, 0 fallen |
| Fum del toast (desar · restaurar · error) | ✅ §12.1 |
| Cens de `TallaChip` a zero | ✅ §13 |

### 15.1 · ⚠️ Correcció al brief: aquí no hi ha vitest

El brief demanava «vitest (218)». **El projecte no té vitest** —ni la dependència ni cap
script `test` a `package.json`— i els fitxers de test ho diuen a la capçalera: van amb el
**runner natiu de Node**. El comandament correcte és:

```
cd frontend && node --test "src/**/*.test.js"     # → 218 tests, 218 pass, 0 fail
```

⚠️ Ull amb la forma: `node --test src/` (sense el glob) NO troba els tests i falla amb un
únic error enganyós. El número 218 del brief és exacte; el nom del runner, no.
