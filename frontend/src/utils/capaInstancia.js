// LA IDENTITAT VISIBLE D'UNA MESURA — com s'escriuen la CAPA i la INSTÀNCIA a la pantalla.
//
// Els dos eixos de C4 viatgen als payloads com a SLUG (`capa: 'folre'`, `instancia: 'left'`) i
// és el slug el que es desa (llei D2: el literal mostra l'idioma de qui llegeix, la BD guarda el
// slug). Aquest mòdul és l'ÚNIC lloc del front que sap traduir-los, perquè quatre superfícies
// —Mesures, Escalat, Comprovació i Fitting— han de dir «Folre» exactament igual: la lliçó de
// `nomenclaturaPom.js`, on el mateix nom sortia bé en una taula i malament a la del costat.
//
// ⚠️ EL VOCABULARI ÉS D-31.22 I NO EL DE LES MAQUETES. Les maquetes aprovades diuen
// «Interlining», «Binding», «Knit» i «Reinforcement» en llocs: són ERRONIS i no s'han copiat.
// La taula bona, i la que hi ha aquí, és:
//     exterior=Exterior/Shell · folre=Folre/Lining · entretela=Entretela/Interfacing ·
//     farciment=Farciment/Padding · reforc=Reforç/Underlining · fornitura=Fornitura/Trim
//
// ⚠️ PER QUÈ UNA CONSTANT I NO UNA CRIDA AL CATÀLEG: `pom.MeasurementLayer` existeix i a staging
// està sembrat amb aquests mateixos sis slugs, però a PROD la taula és BUIDA i no hi ha cap
// endpoint que la publiqui. Una pantalla que en depengués sortiria sense etiquetes el dia del
// desplegament. La sembra i el seu lector són feina de BACKEND, i queda ANOTADA com a pendent;
// mentrestant el front porta el vocabulari escrit, que és exactament el que ja hi ha a la BD.
// TODO(backend): sembrar `MeasurementLayer` a PROD + publicar-lo, i llavors llegir-lo d'aquí.
//
// La INSTÀNCIA és un slug compost canònic (`'left'`, `'left-relaxed'`): es desmunta pels guions i
// cada tram es tradueix per separat, perquè el diccionari d'instàncies encara no existeix (arriba
// amb C4-ins i la Montse) i inventar-ne un aquí seria fabricar la font única equivocada. Un tram
// desconegut es mostra CRU en comptes de desaparèixer: val més veure `sleeve-2` que no veure res.

/** Slugs de capa que el catàleg de la casa sembra, en ordre de presentació (D-31.22). */
export const CAPES = ['exterior', 'folre', 'entretela', 'farciment', 'reforc', 'fornitura']

/** Trams d'instància amb literal propi. La resta es mostra crua (v. capçalera). */
export const INSTANCIES = ['left', 'right', 'relaxed', 'extended']

const SEP_INSTANCIA = '-'

// Un slug sense literal es presenta amb la inicial en majúscula i els guions desfets: és DADA de
// domini, com LINEAR/STEP o un codi de POM, i traduir-la no és possible ni desitjable.
const cru = (slug) => slug.charAt(0).toUpperCase() + slug.slice(1).replace(/[-_]/g, ' ')

/**
 * Literal de la CAPA en l'idioma de qui llegeix. `''`/`null` → `'exterior'` (la capa única:
 * la columna és NOT NULL amb default i el buit vol dir «l'exterior de sempre», no «sense capa»).
 */
export function etiquetaCapa(slug, t) {
  const s = slug || 'exterior'
  return CAPES.includes(s) ? t(`capa.${s}`) : cru(s)
}

/**
 * Literal de la INSTÀNCIA en l'idioma de qui llegeix, PARAULA SENCERA i mai abreujada
 * (`'left-relaxed'` → «Esquerra · Relaxada»). `''` és la instància ÚNICA i torna `''`: no hi ha
 * res a qualificar, i pintar-hi un guió faria semblar que hi falta alguna cosa.
 */
export function etiquetaInstancia(slug, t) {
  if (!slug) return ''
  return String(slug).split(SEP_INSTANCIA)
    .map(tram => (INSTANCIES.includes(tram) ? t(`instancia.${tram}`) : cru(tram)))
    .join(' · ')
}

/** `true` si la fila parla d'una capa que no és l'exterior (per si cal marcar-la). */
export const esGermanaDeCapa = (slug) => !!slug && slug !== 'exterior'
