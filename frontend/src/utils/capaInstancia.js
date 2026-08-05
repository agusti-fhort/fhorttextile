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
// ⚠️ PER QUÈ UNES CONSTANTS I NO UNA CRIDA AL CATÀLEG: aquest mòdul és el camí de LECTURA i ha de
// poder etiquetar una fila abans que cap petició torni. Les dues taules existeixen i estan
// sembrades (`pom.MeasurementLayer`, 6 files · `pom.MeasurementInstance`, 10 files, verificat el
// 05/08 als tres schemes: public, fhort i los), o sigui que el que hi ha escrit aquí sota és
// exactament el que hi ha a la BD, no una invenció.
//
// ⚠️ EL DICCIONARI D'INSTÀNCIES JA EXISTEIX. El va crear `b631b12d` (F2 · D-31.26) i té DOS EIXOS:
// POSICIÓ (left · right · top · bottom · cf · cb · side · waistband_seam) i ESTAT (relaxed ·
// extended). Aquí sota només n'hi ha QUATRE amb literal propi, que és per què `cf` es llegeix
// avui «Cf» i no «CF». Qui necessiti el diccionari SENCER —el gest de crear una germana, que ha
// d'oferir les vuit posicions i els dos estats per separat, i la proposta de codi amb sufix— l'ha
// de demanar al backend (`GET /api/v1/mesures/diccionari/`) i NO ampliar aquesta llista: duplicar
// el vocabulari en dos llocs és la trampa que `nomenclaturaPom.js` ja va pagar una vegada.
//
// La INSTÀNCIA és un slug compost canònic (`'left'`, `'left-relaxed'`): es desmunta pels guions i
// cada tram es tradueix per separat, perquè els dos eixos són ORTOGONALS (v. la capçalera de
// `pom.MeasurementInstance`). Un tram desconegut es mostra CRU en comptes de desaparèixer: val
// més veure `sleeve-2` que no veure res.

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

/**
 * EL SUFIX QUE FA ÚNIC EL NOM D'UNA MESURA — per a les superfícies d'UNA sola línia de text.
 *
 * Les graelles tenen una columna de CAPA i poden posar la instància dins la cel·la del nom. Les
 * taules de PAPER de la fitxa tècnica no: hi ha una cel·la, i el que hi càpiga és tot el que el
 * tècnic llegirà. Amb dues germanes, «Chest width» i «Chest width» eren dues files idèntiques
 * amb xifres diferents — el pitjor que pot fer un document que va al fabricant.
 *
 * L'ORDRE ÉS instància i DESPRÉS capa, i no a l'inrevés: la instància qualifica la mesura («la
 * sisa esquerra») i la capa diu de quina matèria parla («…al folre»). Es llegeix com es diu.
 *
 * L'EXTERIOR NO S'ESCRIU. És la capa per defecte i la que té la immensa majoria de files: dir-ho
 * a cada línia seria repetir «Exterior» tretze vegades per distingir-ne una. La germana és la
 * que porta marca, que és també com es llegeix un document en paper.
 *
 * Torna `''` per a la mesura única d'exterior — el cas normal, que no ha de canviar de forma.
 */
export function sufixIdentitat(fila, t) {
  if (!fila) return ''
  const trams = []
  const inst = etiquetaInstancia(fila.instancia, t)
  if (inst) trams.push(inst)
  if (esGermanaDeCapa(fila.capa)) trams.push(etiquetaCapa(fila.capa, t))
  return trams.length ? ` · ${trams.join(' · ')}` : ''
}
