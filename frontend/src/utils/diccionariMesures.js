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
 * LA CLAU D'EXCLUSIÓ d'un slug: **la seva FAMÍLIA**, que és el bloc dins del qual només pot
 * haver-hi UNA etiqueta encesa. `null` si el diccionari no el coneix (no es pot dir què
 * rellevaria un slug del qual no se sap la família).
 *
 * 🚨 ERA `eix` + `/sub-eix` QUAN N'HI HAVIA. Amb dues famílies declarades de deu slugs, els sis
 * que no en tenien queien a la clau de l'EIX i per tant s'excloïen entre ells i amb tota la
 * resta: prémer «Top» apagava «Left». Des de la llei del 26/08 **cap slug és orfe** i la
 * família sola és la clau.
 */
export function clauExclusio(dicc, slug) {
  // ⚠️ EL FALLBACK A L'EIX NO ÉS DECORACIÓ. Un payload sense `subeix` —un backend anterior a
  // aquest tram, que és exactament el cas d'un PROD amb el gunicorn ranci— deixaria TOTES les
  // píndoles sense clau, i llavors `triaTram` no en pot encendre cap: els xips es tornarien
  // INERTS, que és pitjor que excloents. Amb l'eix al darrere, un payload vell es comporta com
  // es comportava; amb famílies, mana la família.
  return subeixDe(dicc, slug) || eixDe(dicc, slug) || null
}

/**
 * `true` si dues etiquetes NO poden conviure a la mateixa germana. És el MIRALL exacte de
 * `MeasurementInstance.error_de_combinacio` al backend, i les dues bandes han de dir el mateix:
 * la UI evita el gest impossible i la porta el rebutja igualment (una pantalla no és una barana).
 *
 * LA REGLA, SENCERA: **xoquen si i només si són de la MATEIXA FAMÍLIA.**
 *
 *   · famílies diferents → conviuen (`front`+`left`, `top`+`left`, `cf`+`left`, `side`+`top`);
 *   · mateixa família → xoquen (`left`+`right`, `front`+`back`, `top`+`bottom`, `cf`+`cb`,
 *     `side`+`waistband_seam`, `relaxed`+`extended`);
 *   · vocabulari desconegut → NO es jutja i conviu (com fa el backend).
 *
 * ⚠️ **LES REDUNDÀNCIES CONVIUEN.** `front`+`cf` diu dues vegades que és del davant i és
 * legal: el sistema no fa de policia semàntic (llei d'Agus, 26/08).
 */
export function xoquen(dicc, a, b) {
  const fa = subeixDe(dicc, a)
  const fb = subeixDe(dicc, b)
  if (fa && fb) return fa === fb
  // Sense família a banda i banda no es pot aplicar la llei nova: es cau a la d'abans (mateix
  // EIX → xoquen), que és com es comportava un payload sense `subeix`. Amb el vocabulari de la
  // casa això no passa mai —cap slug és orfe des del 26/08—; passa amb un backend endarrerit o
  // amb una instància que s'hagi creat un tenant.
  const ea = eixDe(dicc, a)
  const eb = eixDe(dicc, b)
  if (!ea || !eb) return false
  return ea === eb
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
 * EL PES CANÒNIC d'un tram: la posició de la seva FAMÍLIA a `dicc.subeixos`, i prou.
 *
 * 🚨 AIXÒ ÉS EL QUE SUBSTITUEIX L'ATZAR ALFABÈTIC. Era
 *
 *     const eixos = Object.keys(dicc?.instancies || {})     // ← l'ordre d'un objecte JSON
 *     return (i < 0 ? 99 : i) * 100 + (j < 0 ? 99 : j)      // ← eix primer, sub-eix després
 *
 * i les claus d'aquell objecte les posa el backend amb `order_by('eix')`, que és **alfabètic**:
 * `'ESTAT' < 'POSICIO'`. O sigui que el sistema componia `extended-right` mentre el docstring
 * d'aquesta mateixa funció deia «posició abans que estat». La BD en porta la prova
 * (`extended-right`, `relaxed-right`), i **l'ordre entra a la clau única de cinc taules**.
 *
 * ⚠️ **LA FONT ÉS `dicc.subeixos` I NO `dicc.eixos`**, i la tria importa:
 *   · `subeixos` és la llista de FAMÍLIES en ordre canònic, emesa des de `MeasurementInstance
 *     .FAMILIES` — que és **on la llei d'Agus viu escrita** (peça → banda → verticalitat →
 *     costura → línia → estat);
 *   · `eixos` és una altra cosa: POSICIÓ i ESTAT, el que agrupa les COLUMNES de la taula de
 *     mesures. Des de la llei del 26/08 l'eix **ja no decideix res de l'ordre**: cada slug té
 *     família i la família sola en diu el lloc. Fer-lo servir mantindria dos nivells
 *     d'ordenació on la llei només en té un, i el dia que la família i l'eix no casessin
 *     tornaríem a tenir dues respostes per a la mateixa pregunta.
 *
 * ⚠️ AQUEST ORDRE NO ÉS EL `display_order`, i no s'hi ha de fer coincidir. El `display_order`
 * diu en quin ordre s'OFEREIXEN els xips (Left · Right · Front · Back: el que es fa servir cada
 * dia, primer); això diu com es COMPON el slug que va a la clau i el sufix que va al fabricant
 * (`BL`, mai `LB`). Dues preguntes, dues respostes.
 *
 * El que el diccionari no conegui va al final: no es pot inventar on cau un slug del qual no se
 * sap la família. `sort` és estable, o sigui que entre desconeguts es conserva l'ordre d'entrada.
 */
function pesCanonic(dicc, slug) {
  const families = dicc?.subeixos || []
  const i = families.indexOf(subeixDe(dicc, slug))
  if (i >= 0) return i
  // ⚠️ MATEIX FALLBACK QUE `clauExclusio`, i pel mateix motiu. Amb un payload sense `subeix`
  // —un backend anterior a aquest tram— tots els trams pesarien igual i l'ordre del slug seria
  // el dels CLICS: la mateixa germana tindria dues claus, que és el defecte que això tanca.
  // Amb l'eix al darrere, un payload vell compon com componia. Els family-less van DESPRÉS de
  // les famílies conegudes: un payload mixt no pot deixar-los al mig i moure les que sí que en
  // tenen.
  const eixos = Object.keys(dicc?.instancies || {})
  const j = eixos.indexOf(eixDe(dicc, slug))
  return families.length + (j < 0 ? eixos.length : j)
}

/** Els trams, sense repetits i en l'ordre CANÒNIC. La porta única de tot el que compon. */
const canonics = (dicc, trams) =>
  [...new Set((trams || []).filter(Boolean))]
    .sort((a, b) => pesCanonic(dicc, a) - pesCanonic(dicc, b))

/**
 * Compon el slug d'instància a partir dels trams, en l'ORDRE CANÒNIC de la llei (26/08):
 * **peça → banda → verticalitat → costura → línia → estat**. `back-left`, mai `left-back`;
 * `right-extended`, mai `extended-right`. Un ordre que depengués de l'ordre de clic —o de com
 * es diguin els eixos— faria dues claus per a la mateixa germana, i la clau única de la BD és
 * `(model, pom, capa, instancia, garment)`.
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
