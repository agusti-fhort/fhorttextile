# SPRINT 00 — Fonament: undo/redo + copy/paste/duplicate
FRONTEND only. Fitxer: TechSheetEditor.jsx (+ mòdul nou).

## Objectiu
Pila d'història sobre el JSON del document i clipboard intern. PRE-REQUISIT de tota la run.

## Disseny
- Mòdul nou frontend/src/pages/ftt/history.js (primera extracció fora del monòlit; només
  lògica, cap JSX — patró "vàlvula d'escapament": presentació es queda, lògica surt).
- Model: pila d'snapshots de `pages` (estructura v2) amb límit (50) i COALESCING:
  mutacions contínues (drag, resize, tecleig a textarea) generen UNA entrada en
  estabilitzar-se (reutilitzar el senyal del debounce 2s de l'autosave :1481-1501 o
  commit-on-end-of-gesture al dragend/transformend — decidir a la mini-diagnosi, el
  més simple guanya).
- Undo: Cmd/Ctrl+Z · Redo: Shift+Cmd/Ctrl+Z. Ignorar si focus dins input/textarea.
- Clipboard intern (estat, no navegador): Cmd/Ctrl+C copia selecció (deep clone, uid nous
  en enganxar) · Cmd/Ctrl+V enganxa amb offset +5mm · Cmd/Ctrl+D duplica directe.
  Només objectes de capa free (com Delete :existent).
- Undo/redo restaura també la selecció raonablement (o la buida — el simple guanya).

## Porta verda
- Seqüència manual del verificador (headless o instruccions reproduïbles): crear rect →
  moure'l → undo (torna) → redo (reavança) → copy/paste (nou objecte offset, uid distint)
  → duplicate → delete → undo (reapareix).
- Drag llarg = 1 sola entrada d'història. Escriure en text = no trenca undo global.
- npm run build net. Autosave i lock intactes.

## Commits suggerits
1. history.js (mòdul + integració mutacions bàsiques) · 2. keyboard undo/redo ·
3. clipboard C/V/D.
