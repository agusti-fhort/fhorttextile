# DIAGNOSI Q8-ter/T5 · retirar del panell les taules substituïdes

> 18/08/2026 · abans de tocar res. Condició del brief: «fitxes velles JA DESADES han de seguir
> renderitzant; retirem l'entrada del panell, no el renderitzador».

## ✅ LA CONDICIÓ ES COMPLEIX, I NO PER SORT

**El renderitzador de `type: 'table'` NO mira mai el `kind`.** Verificat als dos punts on es
pinta una taula —el llenç viu (`:2349`) i el render offscreen d'export/miniatures (`:2110`)—:
tots dos criden `buildTableCellPrimitives(obj)`, que llegeix `columns`, `rows` i `style` i res
més. `kind` és **metadada de procedència**, no un discriminant de render.

Conseqüència: una fitxa desada amb una `base_measures`, una `pom_fitting`, una `pom_grading` o
una `fitting_history` es continua pintant EXACTAMENT igual amb el panell buit d'aquelles
entrades. El que es retira és **la manera de crear-ne de noves**, no la manera de dibuixar les
que hi ha.

L'única branca de render que SÍ que mira el `kind` és `graded_table` (`:2084`), i és d'un altre
`type` (`data_block`): no entra a la retirada.

## El que queda orfe si es retiren les quatre entrades

| Node | Consumidors després de la retirada |
|---|---|
| `insertTableT1a` · `insertTableBaseMeasures` · `insertTableT1b` · `insertTableRepas` | **cap** → cauen amb la ruta |
| `runTableVariant` · modal sub-selector de size fitting (`:8825-8850`) | **cap** (existia només per a T1a/T1b) |
| `sfAmbGrading` · `nRepas` (+ el seu `useEffect`) · `t1aOk` · `t1aMotiu` · `nSpecs` | **cap** |
| `baseMeasuresOk` | **2** (les portes de Q8b i Q8c) → es queda |

`buildTableCellPrimitives`, `fitTableObj`, `partirEnTaules`, `inserirTaules` i `escalonat` es
queden: els fan servir la BOM i la personalitzada, que no es retiren.

## 🚩 REPORTAT ABANS DE RETIRAR — i queda FORA d'aquest tram

**El modal `pickFitting` (`:8797`) ja és òrfena ARA, abans d'aquest tram**: no hi ha ni un sol
`setPickFitting(true)` a tot el fitxer. És l'última consumidora de `insertGradedTable` (el bloc
`graded_table` LEGACY) i de `sizeFittings`.

No es toca aquí per dues raons: no és de les quatre entrades que el brief retira, i el seu
render (`graded_table`) **ha de seguir viu** per als documents que ja en porten. S'anota al cens
de poda per a qui el reculli.
