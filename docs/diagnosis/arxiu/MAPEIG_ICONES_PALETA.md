> ⚠️ SUPERADA 2026-07-07 — implementada (paleta + closca E1-E3). Consulta només com a històric.

# MAPEIG D'ICONES TABLER — paleta d'eines (estil Adobe, flyouts)

> Patró A, **READ-ONLY absolut**. Cap canvi, cap commit, cap push. `/var/www/ftt-staging/frontend`.
> Data: 2026-06-28. Tots els noms VERIFICATS contra el set instal·lat (no inventats).

---

## 1) Com s'usen les icones Tabler (set i versió)

**FETS:**
- **DOM (editor):** icones com a **webfont**, classe `ti ti-<nom>` (p.ex.
  `<i className="ti ti-pointer" />`). Definides a `TOOL_GROUPS`
  ([TechSheetEditor.jsx:1834+](../../frontend/src/pages/TechSheetEditor.jsx#L1834)) i arreu de la UI.
- **Càrrega del webfont:** CDN a `index.html:8` →
  `https://cdn.jsdelivr.net/npm/@tabler/icons-webfont/dist/tabler-icons.min.css`.
  ⚠️ **NO porta versió fixada** → carrega l'**última** publicada del webfont.
- **Paquets instal·lats** (`package.json:18`): `@tabler/icons-react ^3.44.0` i, com a transitiu,
  `@tabler/icons 3.44.0`. `@tabler/icons-react` només s'usa FORA de l'editor (p.ex. ProjectGantt);
  l'editor usa el webfont.
- **Font de veritat verificada:** `node_modules/@tabler/icons/icons/outline/*.svg` (versió **3.44.0**,
  **5093 icones outline**). `ti-<nom>` existeix sii hi ha `<nom>.svg` a `outline/`. La verificació
  d'aquest document s'ha fet contra aquesta llista (3.44.0 és un **límit inferior** segur: el CDN
  "latest" en té igual o més; Tabler gairebé mai retira icones).

⚖️ **DECISIÓ (Agus):** el CDN sense versió fa que la disponibilitat d'icones no sigui determinista.
Recomanació: **fixar la versió** del webfont al CDN (p.ex. `@tabler/icons-webfont@3.44.0`) o
instal·lar-lo localment, perquè el set sigui estable i coincideixi amb el verificat aquí.

**Nota outline vs filled:** `ti-<nom>` és OUTLINE. Les variants plenes existeixen com a
`ti-<nom>-filled` al webfont (p.ex. `ti-square-filled`), però aquest mapeig recomana **outline**
(coherent amb la closca). On una icona "plena" seria ideal (swatch de fill), s'usa l'equivalent
outline.

---

## 2) MAPEIG per eina

Llegenda: ✅ = verificat que EXISTEIX a outline 3.44.0 · 🔴 = NO existeix (cal aproximació) ·
**negreta** = proposta principal · "ja" = ja s'usa avui (reaprofitable).

### SELECCIÓ
| Eina | Proposta (✅) | Alternatives (✅) | Ja avui? |
|---|---|---|---|
| Selecció objecte (fletxa negra) | **`ti-pointer`** | `ti-hand-finger` · `ti-click` · `ti-arrow-up-left` | ✅ (botó Select) |
| Selecció directa (nodes, fletxa blanca) | **`ti-vector-bezier`** | `ti-arrow-up-left` (fletxa "buida") · `ti-vector` · `ti-point` | ✅ (`ti-vector-bezier` ja al fitxer) |
| Selecció de subpath | **`ti-vector`** | `ti-lasso` · `ti-vector-spline` · `ti-point` | ✅ (`ti-vector`, flat insert) |

💡 No hi ha cap icona Tabler específica de "fletxa blanca/direct-select" ni de "subpath". Les
proposades transmeten "edició de nodes/traç vectorial"; `ti-arrow-up-left` és el més semblant a la
fletxa buida d'Adobe.

### DIBUIX
| Eina | Proposta (✅) | Alternatives (✅) | Ja avui? |
|---|---|---|---|
| Ploma (pen/bézier) | **`ti-vector-bezier`** | `ti-ballpen` · `ti-writing` · `ti-pencil` | — |
| Formes (grup) | **`ti-shape`** | `ti-shape-2` · `ti-components` · `ti-square` | ✅ (grup shapes) |
| · Rectangle | **`ti-square`** | `ti-rectangle` | ✅ |
| · Rect. arrodonit | **`ti-square-rounded`** | `ti-border-radius` | ✅ |
| · El·lipse | **`ti-circle`** | `ti-oval` | ✅ |
| Línia | **`ti-line`** | `ti-minus` (ja) · `ti-slash` | ✅ (com `ti-minus`) |
| Línia puntejada | **`ti-line-dashed`** | `ti-line-dotted` | ✅ |
| Fletxa simple | **`ti-arrow-right`** | `ti-arrow-narrow-right` | ✅ |
| Fletxa doble | **`ti-arrows-horizontal`** | `ti-arrows-left-right` · `ti-arrow-bar-both` | ✅ |

🔴 **`ti-pen` NO existeix** → per a la ploma, usar **`ti-vector-bezier`** (o `ti-ballpen`).
🔴 `ti-rectangle-rounded` NO existeix → `ti-square-rounded` (ja) o `ti-border-radius`.

### TEXT
| Eina | Proposta (✅) | Alternatives (✅) | Ja avui? |
|---|---|---|---|
| Text (una "T") | **`ti-letter-t`** | `ti-typography` (ja, grup) · `ti-cursor-text` (ja, eina) · `ti-letter-case` | ✅ (com `ti-cursor-text`/`ti-typography`) |
| Text amb caixa | **`ti-text-caption`** | `ti-forms` · `ti-text-wrap` · `ti-box-padding` | ✅ |

### ANOTACIÓ
| Eina | Proposta (✅) | Alternatives (✅) | Ja avui? |
|---|---|---|---|
| Cota POM (doble fletxa+text) | **`ti-ruler-measure`** | `ti-dimensions` · `ti-arrow-autofit-width` · `ti-ruler-2` | — |
| Anotació (fletxa+comentari) | **`ti-message-2`** | `ti-note` · `ti-message` · `ti-message-circle` | — |
| Callout | **`ti-message-2-share`** | `ti-speakerphone` · `ti-quote` | ✅ (preset_callout) |
| Detall | **`ti-zoom-in-area`** | `ti-circle-dashed` (ja) · `ti-focus-2` · `ti-focus-centered` | ✅ (com `ti-circle-dashed`) |
| Llegenda | **`ti-list-details`** | `ti-list` · `ti-list-check` | ✅ (preset_legend) |

💡 Cap icona "cota/dimensió amb text" exacta; `ti-ruler-measure` i `ti-arrow-autofit-width`
(fletxa doble dins límits) són les més pròximes a una cota POM.

### MODIFICAR
| Eina | Proposta (✅) | Alternatives (✅) | Ja avui? |
|---|---|---|---|
| Buscatraços (grup) | **`ti-circles-relation`** | `ti-vector` · `ti-polygon` | — |
| · Unir (union) | **`ti-layers-union`** | `ti-circles-relation` | — |
| · Restar (subtract) | **`ti-layers-subtract`** | — | — |
| · Intersecar | **`ti-layers-intersect`** | — | — |
| · Excloure (difference) | **`ti-layers-difference`** | — | — |
| Rotar | **`ti-rotate`** | `ti-rotate-clockwise` · `ti-rotate-2` · `ti-rotate-rectangle` | — |
| Escalar | **`ti-resize`** | `ti-arrows-diagonal` · `ti-dimensions` · `ti-maximize` | — |
| Mirall H | **`ti-flip-horizontal`** | — | ✅ (dock) |
| Mirall V | **`ti-flip-vertical`** | — | ✅ (dock) |
| Retallar imatge (crop) | **`ti-crop`** | `ti-crop-1-1` · `ti-frame` | — |

✅ **El buscatraços té cobertura completa i idònia:** `ti-layers-union` / `ti-layers-subtract` /
`ti-layers-intersect` / `ti-layers-difference` (les 4 operacions booleanes). 🔴 NO existeixen
`ti-union`, `ti-exclude`.

### NAVEGACIÓ
| Eina | Proposta (✅) | Alternatives (✅) | Ja avui? |
|---|---|---|---|
| Mà (pan) | **`ti-hand-stop`** | `ti-hand-grab` · `ti-hand-move` · `ti-hand-finger` | — |
| Zoom | **`ti-zoom`** | `ti-zoom-in` · `ti-zoom-out` · `ti-search` · `ti-zoom-scan` | — (zoom-in/out ja a la barra d'estat com `ti-plus`/`ti-minus`) |
| Cursor precís | **`ti-crosshair`** | `ti-target` · `ti-focus-2` · `ti-current-location` | — |

🔴 **`ti-hand` NO existeix** → per a la mà de pan, usar **`ti-hand-stop`** (mà oberta) o
`ti-hand-grab`.

### PEU (swatches)
| Eina | Proposta (✅) | Alternatives (✅) | Ja avui? |
|---|---|---|---|
| Swatch fill | **`ti-color-swatch`** | `ti-palette` · `ti-square` · `ti-paint` | — |
| Swatch stroke | **`ti-border-style`** | `ti-border-all` · `ti-square` (contorn) · `ti-line` | — |
| Intercanvi fill↔stroke | **`ti-arrows-exchange`** | `ti-switch-horizontal` · `ti-arrows-diff` · `ti-transfer` · `ti-replace` | — |

💡 Swatch de FILL idealment seria un quadrat ple; en outline, `ti-color-swatch` (mostrari) o
`ti-square` (contorn). Si es vol distinció visual fill-ple vs stroke-contorn, el webfont permet
`ti-square-filled` (PLE) per al fill i `ti-square` (outline) per al stroke — però surt de l'estil
outline pur (⚖️).

---

## 3) RESUM — icones JA assignades avui (reaprofitables)

A `TOOL_GROUPS` ([:1834-1867](../../frontend/src/pages/TechSheetEditor.jsx#L1834-L1867)) i a la
resta de la UI de l'editor:

| Element | Icona avui |
|---|---|
| Grup shapes | `ti-shape` |
| rect / rect_round / ellipse | `ti-square` / `ti-square-rounded` / `ti-circle` |
| Grup draw | `ti-pencil` |
| line / line_dot | `ti-minus` / `ti-line-dashed` |
| arrow / arrow2 | `ti-arrow-right` / `ti-arrows-horizontal` |
| draw (mà alçada) | `ti-scribble` |
| Grup text | `ti-typography` |
| text / text_box | `ti-cursor-text` / `ti-text-caption` |
| Grup presets | `ti-components` |
| callout / detall / llegenda | `ti-message-2-share` / `ti-circle-dashed` / `ti-list-details` |
| Select (botó) | `ti-pointer` |
| Imatge (botó) | `ti-photo` |
| Mirall H/V (dock) | `ti-flip-horizontal` / `ti-flip-vertical` |
| Flat/vector | `ti-vector` / `ti-vector-bezier` |

→ La gran majoria d'eines de DIBUIX/TEXT/FORMES ja tenen icona vàlida. El que falta crear (icona
nova, totes verificades ✅) és sobretot: **selecció directa/subpath, ploma, anotació/cota, tot
MODIFICAR (buscatraços/rotar/escalar/crop), tota NAVEGACIÓ (mà/zoom/cursor precís) i el PEU
(swatches)**.

---

## 🔴 NOMS QUE NO EXISTEIXEN (no usar) + aproximació

| Nom temptador | Estat | Usar en lloc seu |
|---|---|---|
| `ti-pen` | 🔴 no existeix | `ti-vector-bezier` (o `ti-ballpen`) |
| `ti-points` | 🔴 (sí `ti-point`) | `ti-point` |
| `ti-rectangle-rounded` | 🔴 | `ti-square-rounded` / `ti-border-radius` |
| `ti-union` | 🔴 | `ti-layers-union` |
| `ti-exclude` | 🔴 | `ti-layers-difference` (excloure) / `ti-layers-subtract` (restar) |
| `ti-hand` | 🔴 | `ti-hand-stop` / `ti-hand-grab` |
| `ti-square-filled` (outline) | 🔴 a outline | `ti-color-swatch` / `ti-square` (o `ti-square-filled` com a FILLED webfont) |

---

*Diagnosi read-only. Cap fitxer de codi tocat. Cap commit, cap push.*
