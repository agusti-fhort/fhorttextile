// EL DICCIONARI D'IDENTITAT D'UNA MESURA, al front: capes · instàncies · regla de composició.
//
// Font: `GET /api/v1/mesures/diccionari/` (D-31.22 + D-31.26). Aquí hi viuen les REGLES —com es
// compon el codi d'una germana i com es compon el seu slug—; qui va a buscar el diccionari és
// `utils/diccionariMesuresFont.js`.
//
// ⚠️ NO DUPLIQUIS AQUEST VOCABULARI. `utils/capaInstancia.js` porta constants per al camí de
// LECTURA —etiquetar una fila abans que cap petició torni— i prou. Tot el que ESCRIU (el gest de
// partir un POM, el modal de posicions, el cercador amb sufixos) ha de venir d'aquí: el dia que
// la Montse afegeixi una posició, el sistema n'ha de tenir una sola resposta.
//
// ⚠️ AQUEST FITXER NO IMPORTA RES. Les regles de composició són l'única part del vocabulari que
// el sistema CALCULA, i han de ser provables amb `node --test` sense arrossegar React ni axios
// (el runner no resol imports sense extensió). Qui va a buscar el diccionari és
// `utils/diccionariMesuresFont.js`, que sí que en depèn.

/**
 * PARELLES COMPLEMENTÀRIES. Partir un POM per una opció crea la fila triada I la seva germana:
 * la maqueta v8.1 ho fa amb `COMP`, i és el que fa que el gest sigui «partir» i no «afegir».
 *
 * Viuen aquí i no al backend perquè NO són vocabulari: són una propietat geomètrica de la peça
 * (si n'hi ha una d'esquerra n'hi ha una de dreta) i el diccionari no la declara. Les posicions
 * SENSE parella (`side`, `waistband_seam`) no es parteixen: s'afegeixen d'una en una pel modal.
 */
export const COMPLEMENTARIA = {
  left: 'right', right: 'left',
  top: 'bottom', bottom: 'top',
  cf: 'cb', cb: 'cf',
  relaxed: 'extended', extended: 'relaxed',
}

/**
 * LES DIMENSIONS DE LA TAULA SURTEN DE LA BD, NO D'AQUÍ (D-31.26 · «a BD i no a cap constant»).
 *
 * Un grup de columnes per EIX, i les opcions del grup són les files d'aquell eix, en el seu
 * `display_order`. Abans hi havia una llista escrita a mà amb quatre slugs (`left`/`right` ·
 * `relaxed`/`extended`), que són les DADES DE DEMOSTRACIÓ de la maqueta: el diccionari real en
 * porta VUIT a l'eix de posició, i les altres sis no tenien manera d'arribar a la fila.
 *
 * Sense diccionari torna una llista buida: la taula es pinta igual, sense cap píndola, i les
 * columnes apareixen quan el vocabulari arriba. Cap pantalla espera un GET per dibuixar-se.
 */
export function dimensionsDe(dicc) {
  const perEix = dicc?.instancies || {}
  // `eixos` mana l'ORDRE i porta el nom de la columna; sense ell (backend antic) es cau a les
  // claus del diccionari d'instàncies, que almenys en dona la llista.
  const declarats = dicc?.eixos?.length
    ? dicc.eixos
    : Object.keys(perEix).map(clau => ({ clau, nom_en: clau, nom_ca: clau, nom_es: clau }))
  return declarats
    .map(e => ({ ...e, opcions: [...(perEix[e.clau] || [])]
      .sort((a, b) => (a.display_order ?? 99) - (b.display_order ?? 99)) }))
    .filter(e => e.opcions.length > 0)
}

/**
 * L'EIX QUE ES GIRA en partir un POM: el PRIMER que el diccionari declara (avui, la posició).
 *
 * Era el literal `'POSICIO'`. La regla de fons no és «la posició»: és que la lateralitat mana
 * sobre l'estat perquè va primer —si es tria «esquerra · relaxada», la germana és «dreta ·
 * relaxada», no «esquerra · estirada»—, i qui declara aquest ordre és el diccionari.
 */
export const eixPrincipal = (dicc) => dimensionsDe(dicc)[0]?.clau || null

/**
 * EL NOM D'UNA FILA DEL DICCIONARI en l'idioma de qui llegeix. Val per a capes i per a eixos —
 * totes dues coses viatgen amb els tres noms sencers a posta (v. `identity_views._fila`), perquè
 * canviar d'idioma no hagi de tornar a demanar el vocabulari.
 *
 * ⚠️ NO val per a les INSTÀNCIES: aquelles van en anglès canònic i no es tradueixen (les paraules
 * que allarguen el nom del POM i en componen el sufix). Per a elles, `etiquetaInstancia`.
 */
export const nomEnIdioma = (fila, lang) =>
  fila?.[`nom_${String(lang || 'ca').slice(0, 2)}`]
  || fila?.nom_en || fila?.nom_ca || fila?.clau || fila?.slug || ''

/**
 * EL SUB-EIX d'un slug simple (`'CARA'` · `'LATERAL'` · `''`), tal com el diccionari el publica.
 *
 * LA POSICIÓ TÉ DOS EIXOS (Agus, 22-23/08): la CARA (front · back) i el LATERAL (left · right).
 * Una mesura pot ser «l'esquena, banda esquerra» —tots dos alhora— i no pot ser «esquerra i
 * dreta». Les posicions que NO en declaren cap (`top`, `cf`, `side`…) es comporten com sempre:
 * excloents amb tota la resta del seu eix.
 *
 * ⚠️ El sub-eix NO s'escriu aquí: ve com a camp de la fila (`subeix`). Tenir la llista de quins
 * slugs són cara i quins lateral en dos llocs és exactament la trampa que `nomenclaturaPom.js`
 * ja va pagar.
 */
export const subeixDe = (dicc, slug) => filaInstancia(dicc, slug)?.subeix || ''

/**
 * LA CLAU D'EXCLUSIÓ d'un slug: el bloc dins del qual només pot haver-hi UNA etiqueta encesa.
 * `null` si el diccionari no el coneix (no es pot dir què rellevaria).
 */
export function clauExclusio(dicc, slug) {
  const eix = eixDe(dicc, slug)
  if (!eix) return null
  const sub = subeixDe(dicc, slug)
  return sub ? `${eix}/${sub}` : eix
}

/**
 * `true` si dues etiquetes NO poden conviure a la mateixa germana. És el MIRALL exacte de
 * `MeasurementInstance.error_de_combinacio` al backend, i les dues bandes han de dir el mateix:
 * la UI evita el gest impossible i la porta el rebutja igualment (una pantalla no és una barana).
 *
 *   · eixos diferents → conviuen (`left` + `relaxed`);
 *   · mateix eix, sub-eixos diferents → conviuen (`back` + `left`);
 *   · mateix sub-eix → xoquen (`left` + `right`, `front` + `back`);
 *   · algun SENSE sub-eix → xoquen (`top` + `left`): el comportament de sempre.
 */
export function xoquen(dicc, a, b) {
  const ea = eixDe(dicc, a)
  const eb = eixDe(dicc, b)
  if (!ea || !eb || ea !== eb) return false
  const sa = subeixDe(dicc, a)
  const sb = subeixDe(dicc, b)
  if (!sa || !sb) return true
  return sa === sb
}

/** L'eix (`POSICIO`/`ESTAT`) d'un slug d'instància simple, o `null` si no és al diccionari. */
export function eixDe(dicc, slug) {
  if (!dicc || !slug) return null
  for (const [eix, files] of Object.entries(dicc.instancies || {})) {
    if (files.some(f => f.slug === slug)) return eix
  }
  return null
}

/** La fila del diccionari d'un slug simple. */
export function filaInstancia(dicc, slug) {
  if (!dicc || !slug) return null
  for (const files of Object.values(dicc.instancies || {})) {
    const f = files.find(x => x.slug === slug)
    if (f) return f
  }
  return null
}

const sepInst = (dicc) => dicc?.regles?.instancia_separador ?? '-'

/** Els trams d'un slug compost (`'left-relaxed'` → `['left','relaxed']`). */
export const tramsInstancia = (dicc, slug) =>
  (slug ? String(slug).split(sepInst(dicc)) : []).filter(Boolean)

/**
 * Compon el slug d'instància a partir dels trams, en l'ORDRE DELS EIXOS del diccionari
 * (posició abans que estat): `left-relaxed`, mai `relaxed-left`. Un ordre que depengués de
 * l'ordre de clic faria dues claus per a la mateixa germana, i la clau única de la BD és
 * `(model, pom, capa, instancia)`.
 */
/**
 * EL PES CANÒNIC d'un tram: primer l'EIX que el diccionari declara i, dins de l'eix, el SUB-EIX
 * (`subeixos`, en l'ordre que el backend emet: CARA abans que LATERAL).
 *
 * ⚠️ AQUEST ORDRE NO ÉS EL `display_order`, i no s'hi ha de fer coincidir. El `display_order`
 * diu en quin ordre s'OFEREIXEN els xips (Left · Right · Front · Back: el que es fa servir cada
 * dia, primer); això diu com es COMPON el codi que va al fabricant, que es llegeix cara-i-banda
 * (`BL`, mai `LB`). Dues preguntes, dues respostes.
 *
 * Un tram sense sub-eix va al final del seu eix — i és inofensiu: no pot conviure amb cap altre
 * del mateix eix (v. `xoquen`).
 */
function pesCanonic(dicc, slug) {
  const eixos = Object.keys(dicc?.instancies || {})
  const i = eixos.indexOf(eixDe(dicc, slug))
  const j = (dicc?.subeixos || []).indexOf(subeixDe(dicc, slug))
  return (i < 0 ? 99 : i) * 100 + (j < 0 ? 99 : j)
}

/** Els trams, sense repetits i en l'ordre CANÒNIC. La porta única de tot el que compon. */
const canonics = (dicc, trams) =>
  [...new Set((trams || []).filter(Boolean))]
    .sort((a, b) => pesCanonic(dicc, a) - pesCanonic(dicc, b))

/**
 * Compon el slug d'instància a partir dels trams, en l'ORDRE CANÒNIC (posició abans que estat;
 * i dins la posició, cara abans que lateral): `back-left-relaxed`, mai `left-back-relaxed`. Un
 * ordre que depengués de l'ordre de clic faria dues claus per a la mateixa germana, i la clau
 * única de la BD és `(model, pom, capa, instancia)`.
 */
export function composaInstancia(dicc, trams) {
  return canonics(dicc, trams).join(sepInst(dicc))
}

/**
 * EL CODI PROPOSAT d'una germana: `base + sufix` CONCATENAT, sense separador, estil Brownie
 * natiu (D-31.26 · `B`+`T` → `BT`, `FS`+`CF` → `FSCF`). La regla la mana el backend
 * (`regles.sufix_separador`), no aquest fitxer.
 *
 * **LA CAPA NO TOCA MAI EL CODI** (`regles.capa_al_codi: false`): diu de quina matèria és la
 * mesura, no quina de les cares. I els ESTATS no componen sufix (el seu és `''`): fan servir el
 * codi oficial del client si en tenen. Per tots dos motius el resultat pot ser el codi base tal
 * qual, i això NO és un error — és la proposta, i el patronista la pot reescriure sempre.
 */
export function codiProposat(dicc, base, trams) {
  const sep = dicc?.regles?.sufix_separador ?? ''
  // EL MATEIX ORDRE QUE EL SLUG (`canonics`): amb dos sub-eixos, `back`+`left` ha de donar
  // `BL` tant si s'ha premut la cara primer com si s'ha premut la banda. Sense això, el codi
  // depenia de l'ordre dels clics mentre el slug ja no ho feia — dues respostes per a la
  // mateixa germana, i la que va al fabricant era la del clic.
  const sufixos = canonics(dicc, trams)
    .map(t => filaInstancia(dicc, t)?.sufix || '')
    .filter(Boolean)
  return [base || '', ...sufixos].filter(Boolean).join(sep)
}

/**
 * EL CODI BASE: el que quedava abans que cap sufix d'instància s'hi enganxés (`AHL` amb
 * `['left']` → `AH`). Cal per RE-partir una fila que ja porta instància sense acumular sufixos
 * (`AHL` → `AHLR`, que no vol dir res).
 *
 * Es treu NOMÉS pel final i NOMÉS el sufix dels trams que la fila declara: endevinar-lo mirant
 * si el codi acaba en «L» esguerraria un POM que es digui «TOTAL».
 */
export function codiBase(dicc, codi, trams) {
  let base = String(codi || '')
  const sep = dicc?.regles?.sufix_separador ?? ''
  // De l'últim al primer, que és l'ordre en què es van enganxar — i «enganxar» vol dir l'ordre
  // CANÒNIC, el mateix amb què `codiProposat` els va compondre, no el que el qui crida passi.
  for (const t of canonics(dicc, trams).reverse()) {
    const sufix = filaInstancia(dicc, t)?.sufix || ''
    if (!sufix) continue
    const cua = sep + sufix
    if (base.endsWith(cua)) base = base.slice(0, base.length - cua.length)
  }
  return base
}
