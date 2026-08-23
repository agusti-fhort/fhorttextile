// LA TRIA DE LA LLISTA DE POMs — la regla, fora del component.
//
// 🔴 EL PROBLEMA QUE TANCA (Agus, 23/08): la pantalla deia «521/521» quan el catàleg VIU en són
// 141. Tres de cada quatre files són ARXIU —la llei S44 diu que el catàleg vell mor com a
// `actiu=False`, no s'esborra— i embrutaven la llista de treball. Ara hi ha tabs.
//
// ⚠️ **ELS RECOMPTES NO COMPTEN LA PÀGINA: COMPTEN LA LLISTA SENCERA.** La pantalla ja carrega
// TOTS els POMs (`totesLesPagines(poms.list, {page_size: 200})` a `POMCataleg`, que segueix la
// paginació de DRF fins al final), o sigui que aquí hi ha les 521 files i no un tros. És la
// condició que fa honestos aquests números —i la que fa possible la creuada de la cerca amb
// xifra exacta— i per això és el PRIMER que s'ha de tornar a comprovar el dia que la pantalla
// passi a paginar de debò: llavors els recomptes han de venir del servidor.
//
// L'extensió `.js` hi és a posta: aquest mòdul el carrega el runner de Node (que no resol
// imports sense extensió) a més de Vite. Mateixa raó que `instanciaTria.js`.

export const TAB_ACTIUS = 'actius'
export const TAB_INACTIUS = 'inactius'
export const TAB_TOTS = 'tots'

/** L'ordre dels tabs a la barra. `actius` PRIMER, i és el defecte: és la llista de treball. */
export const TABS = [TAB_ACTIUS, TAB_INACTIUS, TAB_TOTS]

/** El tab d'una fila. Una fila només pot ser d'un dels dos primers. */
const esActiu = (p) => p?.actiu !== false

/** Les files d'un tab, sense cap altre filtre. */
export function delTab(llista, tab) {
  const files = llista || []
  if (tab === TAB_ACTIUS) return files.filter(esActiu)
  if (tab === TAB_INACTIUS) return files.filter(p => !esActiu(p))
  return files
}

/**
 * Casa la fila amb el text de cerca? El mateix camp de text que la pantalla ja tenia: codi,
 * nom (els dos vocabularis) i categoria.
 */
export function casa(p, q) {
  const s = String(q || '').trim().toLowerCase()
  if (!s) return true
  return `${p.codi_client || ''} ${p.nom_client || ''} ${p.pom_code || ''} `
    .concat(`${p.name_en || ''} ${p.name_cat || ''} ${p.categoria || ''}`)
    .toLowerCase().includes(s)
}

/**
 * Els recomptes dels tres tabs, sobre la llista SENCERA i sense tenir en compte la cerca:
 * el número del tab diu quantes files HI HA a l'altra banda, no quantes en queden del que
 * s'està buscant ara — si no, canviar el text de cerca faria ballar les tres xifres i cap
 * d'elles diria ja què hi ha al catàleg.
 */
export function recomptes(llista) {
  const files = llista || []
  const actius = files.filter(esActiu).length
  return { [TAB_ACTIUS]: actius, [TAB_INACTIUS]: files.length - actius, [TAB_TOTS]: files.length }
}

/** LA TRIA: tab → cerca. Torna les files que la llista ha de pintar. */
export function tria(llista, { tab = TAB_ACTIUS, q = '' } = {}) {
  return { files: delTab(llista, tab).filter(p => casa(p, q)) }
}

/**
 * L'ORDRE DINS D'UNA FAMÍLIA: els inactius DARRERE (Agus, 23/08). Només es nota al tab «Tots»
 * —als altres dos el grup és homogeni—, i per això no es condiciona al tab: una regla que val
 * sempre no té cas especial que es pugui oblidar.
 *
 * L'ordenació de JS és ESTABLE, o sigui que dins de cada meitat es conserva l'ordre que venia
 * del servidor (`ordering: 'codi_client'`).
 */
export const inactiusDarrere = (items) =>
  [...(items || [])].sort((a, b) => (esActiu(a) ? 0 : 1) - (esActiu(b) ? 0 : 1))
