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
// extended). Els deu slugs són a `INSTANCIES`, aquí sota, i els seus literals a i18n.
//
// ⚠️ QUÈ ES DUPLICA I QUÈ NO. Aquí hi ha els SLUGS i els seus literals, perquè una etiqueta s'ha
// de poder pintar abans que cap petició torni i ha de canviar en canviar d'idioma. L'ESTRUCTURA
// —de quin eix és cadascun, quin sufix compon el codi, en quin ordre s'ofereixen— NO es duplica:
// la mana el backend (`GET /api/v1/mesures/diccionari/` · `utils/diccionariMesuresFont.js`), i és
// el que ha de llegir tot el que ESCRIU (partir un POM, el modal de posicions, el cercador amb
// sufixos). Tenir l'estructura en dos llocs seria la trampa que `nomenclaturaPom.js` ja va pagar.
//
// La INSTÀNCIA és un slug compost canònic (`'left'`, `'left-relaxed'`): es desmunta pels guions i
// cada tram es tradueix per separat, perquè els dos eixos són ORTOGONALS (v. la capçalera de
// `pom.MeasurementInstance`). Un tram desconegut es mostra CRU en comptes de desaparèixer: val
// més veure `sleeve-2` que no veure res.

/** Slugs de capa que el catàleg de la casa sembra, en ordre de presentació (D-31.22). */
export const CAPES = ['exterior', 'folre', 'entretela', 'farciment', 'reforc', 'fornitura']

/**
 * LES PARAULES D'INSTÀNCIA NO ES TRADUEIXEN (decisió d'Agus, 05/08). Van en ANGLÈS CANÒNIC, tal
 * com les porta el diccionari (`MeasurementInstance.nom_en`), i per un motiu que no és d'estil:
 * la paraula ALLARGA EL NOM DEL POM i d'ella surt el sufix del codi. «FRONT ARMHOLE · Left» amb
 * sufix `L` es llegeix igual a la pantalla catalana, a l'anglesa i a la fitxa que va al
 * fabricant; «FRONT ARMHOLE · Esquerra» amb codi `AHL` són dues llengües a la mateixa línia i
 * el sufix deixa de dir d'on ve. És DADA de domini, com LINEAR/STEP o un codi de POM.
 *
 * Per això aquests literals ja NO són a `i18n/*.json`: hi eren, i s'han tret.
 *
 * Aquest mapa és el MIRALL de la sembra (`seed_measurement_instances.POSICIONS`/`ESTATS`), i
 * existeix per una sola raó: etiquetar una fila ABANS que el diccionari arribi. Qui el tingui a
 * mà passa `dicc` i llavors mana la BD —que és qui pot tenir una instància que un tenant s'hagi
 * creat—; sense diccionari, mana aquest mapa; sense cap dels dos, el slug es mostra cru.
 */
export const NOM_INSTANCIA = {
  left: 'Left', right: 'Right', top: 'Top', bottom: 'Bottom',
  cf: 'CF', cb: 'CB', side: 'Side seam', waistband_seam: 'Waistband seam',
  // `extended` va NET (Agus, 06/08): «stretched» i «stretched out» són aquest mateix estat, no
  // un sinònim que calgui arrossegar al nom. Aquest mapa és el MIRALL de la sembra i la sembra ja
  // diu 'Extended' — i, a diferència del camí del diccionari, aquest NO passa per `curta()`: si
  // aquí hi quedés la barra, sortiria sencera a tota superfície que etiqueti una fila abans que
  // el diccionari arribi.
  relaxed: 'Relaxed', extended: 'Extended',
}

/** Els slugs que el diccionari sembra (D-31.26): vuit posicions i dos estats. */
export const INSTANCIES = Object.keys(NOM_INSTANCIA)

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
 * La INSTÀNCIA en ANGLÈS CANÒNIC, PARAULA SENCERA i mai abreujada (`'left-relaxed'` → «Left ·
 * Relaxed»). `''` és la instància ÚNICA i torna `''`: no hi ha res a qualificar, i pintar-hi un
 * guió faria semblar que hi falta alguna cosa.
 *
 * `dicc` és opcional i és qui MANA quan hi és: el diccionari de la BD pot portar una instància
 * que aquest fitxer no coneix (la que un tenant s'hagi creat). Sense ell, el mirall de la sembra.
 */
export function etiquetaInstancia(slug, dicc = null) {
  if (!slug) return ''
  return String(slug).split(SEP_INSTANCIA)
    .map(tram => nomDelDiccionari(dicc, tram) || NOM_INSTANCIA[tram] || cru(tram))
    .join(' · ')
}

/** El `nom_en` d'un tram simple, tal com el diccionari de la BD el porta. */
function nomDelDiccionari(dicc, tram) {
  for (const files of Object.values(dicc?.instancies || {})) {
    const f = files.find(x => x.slug === tram)
    if (f) return curta(f.nom_en || '')
  }
  return ''
}

/**
 * L'ETIQUETA CURTA d'una instància: el primer terme, sense els sinònims.
 *
 * NEIXIA per a un cas concret: el catàleg deia `nom_en = 'Extended / stretched'` i a la píndola i
 * dins del nom de la fila això era soroll —dues paraules per a un sol concepte, en una cel·la que
 * ja va justa—, o sigui que es presentava «Extended» (Agus, 06/08).
 *
 * **AQUELL CAS JA NO EXISTEIX.** L'Agus va decidir que `extended` i `stretched`/`stretched out`
 * són el mateix estat i que el nom canònic va net; `pom/0060_extended_net.py` ho va aplicar als
 * tres schemes (`public`, `fhort`, `los`) i `seed_measurement_instances.py` ja no torna a posar
 * la barra. El PENDENT de revisar-ho amb la Montse queda tancat per aquella decisió.
 *
 * **I LA FUNCIÓ ES QUEDA IGUALMENT** (Agus, 06/08). Ara no retalla res —no hi ha cap nom amb
 * barra al diccionari— i precisament per això és barata: és la xarxa per al dia que un tenant o
 * una sembra futura en torni a introduir un. La regla és el separador, no una llista de casos.
 *
 * ⚠️ Segueix sent **NOMÉS PRESENTACIÓ**: el nom canònic de la BD no es toca des d'aquí. Si el que
 * s'ha de canviar és el nom del catàleg, es fa al catàleg —sembra + migració de dades, les dues
 * bandes alhora—, com es va fer amb aquest.
 */
export const curta = (nom) => String(nom || '').split('/')[0].trim() || String(nom || '')

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
 *
 * La CAPA es tradueix (és una matèria: folre, entretela) i la INSTÀNCIA no (és vocabulari
 * canònic que allarga el nom del POM). Per això `t` només serveix la primera.
 */
export function sufixIdentitat(fila, t, dicc = null) {
  if (!fila) return ''
  const trams = []
  const inst = etiquetaInstancia(fila.instancia, dicc)
  if (inst) trams.push(inst)
  if (esGermanaDeCapa(fila.capa)) trams.push(etiquetaCapa(fila.capa, t))
  return trams.length ? ` · ${trams.join(' · ')}` : ''
}
