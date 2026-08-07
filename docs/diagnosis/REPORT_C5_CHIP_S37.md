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
