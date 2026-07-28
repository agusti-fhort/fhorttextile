// Què compta com a PEÇA DE PATRÓ inserida a la fitxa.
//
// Des de `b4cb0b7` (legacySketchSvgToPath separa el croquis per rols) el conversor retorna
// DUES formes segons què hi trobi: un `path` quan el dibuix té un sol rol, i un
// `group kind:'sketch'` amb un fill per rol quan n'hi ha més d'un. La inserció de peça es va
// quedar amb la forma antiga i rebutjava el grup, de manera que una peça amb rols separats
// no s'hi podia posar.
//
// La condició del grup és la MATEIXA que ja fa servir el reemplaçament in-situ d'un SVG
// (TechSheetEditor.jsx, «Reemplaçar l'SVG in-situ»): `type === 'group' && kind === 'sketch'`.
// Aquí no s'inventa cap forma nova; es diu en un sol lloc perquè els dos usos —acceptar la
// peça i comptar-les— no puguin tornar a divergir.
//
// Mòdul pur i sense dependències: es prova amb `node --test` (vegeu pecaInsercio.test.js).

/** Un croquis convertit amb els rols separats en capes. */
export const esGrupSketch = o => o?.type === 'group' && o?.kind === 'sketch'

/** Formes que el conversor pot tornar i que SÍ es poden inserir com a peça. */
export const esPecaInserible = o => o?.type === 'path' || esGrupSketch(o)

/**
 * Peces de patró ja col·locades en una pàgina. Alimenta la cascada d'inserció: dues peces
 * seguides a la mateixa cantonada es tapen i qui n'insereix dues creu que n'hi ha una.
 * Ha de comptar les DUES formes — si només compta els `path`, una pàgina plena de peces amb
 * rols separats torna 0 i totes cauen al mateix lloc, que és el bug que la cascada evita.
 */
export const comptaPecesInserides = objs =>
  (objs || []).filter(o => esPecaInserible(o) && o?.piece_name).length
