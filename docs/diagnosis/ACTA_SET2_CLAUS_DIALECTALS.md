# ACTA — Les tres claus dialectals que NO s'han migrat (SET-2/T6b · 2026-08-11)

> Censat i deixat com estava, a posta. Aquesta acta existeix perquè la decisió porti data i
> condició: no és «ja ho farem», és «es fa quan passi això».

## Els fets

`identitatMesura` va créixer a quatre trams i el `garment` hi va entrar l'últim (T6b). El cens
apuntava una sola còpia inlined de la fórmula —`fittingGridAdapter:155`, substituïda per la
crida— però n'hi ha **tres més**, i **no són intercanviables amb ella**:

| lloc | forma | per què no és la mateixa |
|---|---|---|
| `TechSheetEditor.jsx:339` `identitatDeCota` | `${pomId}\|${capa \|\| 'exterior'}\|${instancia \|\| ''}` | el defecte de `capa` és `'exterior'`, no `''` |
| `TechSheetEditor.jsx:340` `identitatDeFila` | idem | parella coherent amb la de sobre |
| `TaulaPOMsCataleg.jsx:64` `clau` | idem | mateix dialecte, un altre consumidor |

Les tres són **internament coherents** —a `TechSheetEditor` les dues es comparen entre elles i
totes dues fan servir `'exterior'`— i **cap no es compara amb la sortida d'`identitatMesura`**
(verificat: aquell mòdul només l'importen `FittingPrintSheet`, `FittingDetail`, `SessionPanel` i
`measureSources`). Per això **avui no hi ha dany**.

## Per què no s'han tocat

Migrar-les a `identitatMesura` els canviaria la clau (`capa` buida deixaria de ser `'exterior'`) i
això és un canvi de comportament en dues superfícies que aquest tram no ha diagnosticat. Un canvi
així es fa amb el seu cens de lectors i el seu banc, no de passada.

## La condició, que és el que fa útil aquesta acta

> **El dia que l'eix de peça arribi a la fitxa tècnica o al catàleg de POMs** —és a dir, quan
> `TechSheetEditor` o `TaulaPOMsCataleg` hagin de pintar mesures de més d'una prenda— aquestes
> tres claus col·lapsaran dues germanes de dues peces, en silenci i sense error, exactament com
> hauria fet `fittingGridAdapter:155`.

Fins llavors, són correctes. A partir de llavors, són un defecte obert. Qui porti l'eix de peça a
qualsevol d'aquestes dues superfícies, hi entra amb aquesta acta a la mà.

## Segon punt censat, del mateix tram

`base_stages_view` (`models_app/views.py:3911`) i `fitting/serializers.py:348` emeten `capa` i
`instancia` però **no `garment`**. `measurements_table_view` sí que l'emet, amb la `clau` de
quatre trams (T6a). Conseqüència pràctica: **Mesures i Escalat ja poden distingir prendes;
Comprovació i Fitting, no** — i el `clauDeFila` d'aquestes dues cau al tram buit fins que el
payload el porti. No és un defecte d'avui (no hi ha peces), és el següent micro-tram de backend.
