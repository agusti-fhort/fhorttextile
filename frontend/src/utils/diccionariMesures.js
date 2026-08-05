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
export function composaInstancia(dicc, trams) {
  const eixos = Object.keys(dicc?.instancies || {})
  const pes = (s) => {
    const e = eixDe(dicc, s)
    const i = eixos.indexOf(e)
    return i < 0 ? 99 : i
  }
  return [...new Set(trams.filter(Boolean))].sort((a, b) => pes(a) - pes(b)).join(sepInst(dicc))
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
  const sufixos = (trams || [])
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
  // De l'últim al primer, que és l'ordre en què es van enganxar.
  for (const t of [...(trams || [])].reverse()) {
    const sufix = filaInstancia(dicc, t)?.sufix || ''
    if (!sufix) continue
    const cua = sep + sufix
    if (base.endsWith(cua)) base = base.slice(0, base.length - cua.length)
  }
  return base
}
