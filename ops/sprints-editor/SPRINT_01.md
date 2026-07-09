# SPRINT 01 — Reflexos de selecció i teclat
FRONTEND only. TechSheetEditor.jsx. Depèn de S0 (tota mutació nova → història).

## Abast
1. RUBBER-BAND: drag sobre llenç buit amb eina selecció = marc de selecció (rect
   semitransparent gold); selecciona objectes de capa free intersecats; Shift acumula.
2. DRECERES D'EINA: V=selecció · T=text · R=rect · E=el·lipse · L=línia · Espai=pan
   (ja existeix). Ignorar amb focus a input/textarea. (A i P reservades: S7.)
3. NUDGE: fletxes = ±1mm; Shift+fletxes = ±10mm. Selecció múltiple es mou junta.
   Coalescing d'història (ràfega = 1 entrada).
4. SHIFT-RESTRICCIÓ: dibuix de línia/fletxa amb Shift = angles a 45°; resize amb Shift
   al Transformer = proporcional (keepRatio dinàmic — avui fix només per data_block).
5. GRUPS: doble clic sobre group = entrar-hi (seleccionar/moure fills); Escape o clic
   fora = sortir. Codi mínim: estat "grup actiu" + hit-test dins del grup.
6. LOCK/HIDE per objecte: camps nous al JSON `locked:bool` i `visible:bool` (default
   true/absents = comportament actual, retrocompatible). Icones ull/cadenat al panell
   de capes (Tabler outline). Locked = no seleccionable/movible; hidden = no es pinta
   NI a live NI a export (dues bandes!).

## Porta verda
Verificador reprodueix els 6 gestos. locked/visible respectats a export (miniatura).
Documents .ftt existents (sense els camps nous) carreguen idèntics. Build net.

## Commits: un per punt (6) o agrupats en 3 si són petits (1+2, 3+4, 5+6).
