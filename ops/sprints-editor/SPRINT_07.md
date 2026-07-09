# SPRINT 07 — Vectorial 2: ploma, polígon, cursor precís
FRONTEND only. Depèn de S0 (història) i S1 (dreceres).

## Abast
1. PLOMA (P): substituir el placeholder soon:true (:2067). Clic = punt d'ancoratge;
   clic+drag = punt amb handles bezier simètrics; clic sobre el primer punt = tancar;
   Enter/Escape = acabar obert. Resultat = type:'path' estàndard (segments amb
   inX/inY/outX/outY — mateix format que l'import, editable després al PaperFlatEditor).
   Preview de traç mentre es dibuixa. Shift = angles 45° (coherent amb S1).
2. POLÍGON: nova eina al flyout de formes: N costats (diàleg o prop al panell, default
   6, min 3), inscrit al drag com rect/ellipse. Model: type:'path' tancat (no tipus nou
   — codi mínim, i queda editable per nodes).
3. CURSOR PRECÍS: creueta al llenç quan hi ha eina de dibuix activa (CSS cursor:
   crosshair); cursor per defecte amb selecció. Toggle Caps Lock NO (fora d'abast).
4. Habilitar la drecera A = selecció de nodes NOMÉS com a accés: A amb un path
   seleccionat = obrir el PaperFlatEditor (el sub-editor existent). No construir
   edició de nodes al llenç principal (fora d'abast — el sub-editor ja ho fa).

## Porta verda
Dibuixar amb ploma una forma tancada amb corbes → pintar-la → doble clic obre
PaperFlatEditor i els nodes coincideixen → desar → roundtrip fidel. Polígon de 6 i de 3.
Undo funciona a mig dibuix (treu l'últim punt) — si això complica, undo cancel·la el
traç sencer (el simple guanya, documentar l'elecció). Build net.

## Commits: 1. ploma · 2. polígon · 3. cursor + drecera A.
