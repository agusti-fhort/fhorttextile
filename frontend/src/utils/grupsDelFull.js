// ELS CONTENIDORS DE PRENDA DEL FULL DE FITTING — S42/C3.
//
// El full imprès és UNA taula correguda (la capçalera viu al `thead` i el navegador la
// repeteix): no hi ha pàgines on repartir res. El que hi obre la prenda és una FILA-TÍTOL dins
// del `tbody`, un cop per grup, allà on cau al flux. Aquest mòdul decideix quins grups hi ha i
// com es diuen; qui els pinta no ha de saber-ho.
//
// 🔑 LA LLEI DE PARTIR NO ES REESCRIU AQUÍ. `agrupaPerGarment` ja existeix des de T9 i ja fa la
// part difícil: agrupa CONSERVANT l'ordre d'aparició i posa al mateix grup les files d'una
// mateixa prenda encara que el payload les serveixi intercalades. Això últim no és un detall:
// el full les rep ordenades per `BaseMeasurement.ordre`, que és GLOBAL al model, i la temptació
// —emetre un títol cada cop que el `garment` canvia respecte de la fila anterior— dona dos
// títols «Short» el dia que una mesura de la mare s'hi coli pel mig. Al 1379 avui no passa, i
// per això el codi ingenu hi semblaria correcte.
//
// El que aquest mòdul hi afegeix són les dues coses que la fitxa no necessitava:
//   · L'ORDRE DELS GRUPS és el de `GET /peces/` —on la mare ve sintètica i sempre primera—, i
//     no el de la primera fila que arribi.
//   · EL NOM de cada grup, que només viu en aquell contracte.

// Extensió explícita: aquest mòdul ha de poder córrer també sota `node --test`, que no resol
// els especificadors sense `.js` (mateix criteri que `taulaBruta.js`).
import { agrupaPerGarment, calArbrePerGarment, garmentDeFila } from './garmentFitxa.js'
import { nomDeLaPeca } from './pecaDefinicio.js'

/**
 * Els grups de files del full, amb el títol que encapçala cadascun.
 *
 * `titol: null` vol dir «cap fila-títol»: el full torna a ser la taula neta d'abans d'aquest
 * tram. Passa en dos casos i tots dos són el mateix criteri —**un rètol que no distingeix res
 * és soroll**—: quan el model té una sola prenda, i quan no sabem com es diuen les que té.
 *
 * ⚠️ `peces` NUL O BUIT NO ÉS «no hi ha peces»: és «encara no ho sabem» (la crida a `/peces/`
 * no ha contestat o ha fallat). La mateixa llei que `filesDeLaPeca` aplica al contenidor de
 * Mesures: el pitjor que pot passar si la segona crida no arriba és no veure els rètols, mai
 * no veure la feina. Amb els noms absents, la taula surt plana i sencera.
 *
 * @param {Array} files    files ja resoltes del full, en el seu ordre
 * @param {Array} peces    contracte de `GET /models/<id>/peces/` (mare inclosa, primera)
 * @param {string} etiquetaMare  com es diu la mare al full («Base model»; el full va en anglès)
 * @returns {Array<{garment: string, titol: string|null, files: Array}>}
 */
export function grupsDelFull(files, peces, etiquetaMare) {
  const grups = agrupaPerGarment(files || [], garmentDeFila)
  if (!grups.length) return []

  const totes = peces || []
  // Sense noms no hi ha rètols, i amb una sola prenda tampoc: els dos casos degraden a la
  // taula d'abans, amb TOTES les files i en el mateix ordre.
  if (!totes.length || !calArbrePerGarment(grups)) {
    return [{ garment: grups[0].garment, titol: null, files: (files || []) }]
  }

  // L'ordre el mana el contracte. Una prenda que hi tingui files però que el contracte no
  // conegui —no hauria de passar mai— va al final en comptes de desaparèixer.
  const posicio = new Map(totes.map((p, i) => [p?.codi || '', i]))
  const rang = (g) => (posicio.has(g) ? posicio.get(g) : Number.MAX_SAFE_INTEGER)
  const perCodi = new Map(totes.map(p => [p?.codi || '', p]))

  return [...grups]
    .sort((a, b) => rang(a.garment) - rang(b.garment))
    .map(g => ({
      garment: g.garment,
      // El nom el resol el punt únic que ja fan servir les altres dues pantalles de prenda:
      // la mare no és «una peça sense nom», és el model, i això ho decideix `es_mare`.
      titol: nomDeLaPeca(perCodi.get(g.garment), etiquetaMare),
      files: g.items,
    }))
}
