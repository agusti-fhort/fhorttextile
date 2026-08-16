// LA FILA DEL PAS 2 — què SAP dir de si mateixa.
//
//     cd frontend && node --test src/components/ImportWizard/filaPas2.test.js
//
// P2-ter · LA FILA INFORMA, NO EDITA. Les píndoles se'n van de la fila: la instància entra al
// NOM, com a la graella del pas 3 i com a la fitxa (`sufixIdentitat`), i qui la vol canviar obre
// el panell. Una fila que és alhora rètol i comandament fa dubtar de si el que s'hi veu és el
// que hi ha o el que s'hi està triant.
//
// I això obliga a una cosa: el nom ha de portar la instància PENDENT, no la desada. Entre triar
// una instància al panell i desar el pas 2 hi ha una estona en què la decisió viu només a
// l'estat local; si el rètol llegís la fila del servidor, diria «única» just després que algú
// hagi triat «Bottom» — i el següent gest seria tornar-hi a entrar per comprovar-ho.
//
/**
 * La IDENTITAT que la fila ha de DIR —capa i instància—: la PENDENT si n'hi ha, i si no, la
 * desada. `pendents` és `{ordre: {capa?, instancia?}}`: UN sol mapa per als dos eixos, i no un
 * per eix, perquè dos mapes paral·lels sobre la mateixa fila són dues veritats que un dia
 * discrepen — que és el defecte que aquest tram sencer persegueix.
 *
 * `??` i no `||` a posta: `''` és una decisió («treu-la, torna a la instància única» · «torna a
 * l'exterior») i amb `||` es llegiria com «no s'ha triat res», ressuscitant la desada.
 */
export function identitatEfectiva(fila, pendents) {
  const p = (pendents || {})[(fila || {}).ordre] || {}
  return {
    capa: (p.capa ?? (fila || {}).capa) || '',
    instancia: (p.instancia ?? (fila || {}).instancia) || '',
  }
}

/** Només la instància — el que demana el columnat quan pregunta pel seu eix. */
export function instanciaEfectiva(fila, pendents) {
  return identitatEfectiva(fila, pendents).instancia
}

/** Només la capa. `''` = l'exterior de sempre; qui la pinta ja ho resol (`etiquetaCapa`). */
export function capaEfectiva(fila, pendents) {
  return identitatEfectiva(fila, pendents).capa
}

/**
 * La fila tal com s'ha de LLEGIR: la mateixa, amb la identitat efectiva. Es passa sencera a
 * `sufixIdentitat` (la porta única) en comptes de compondre aquí cap etiqueta: qui escriu
 * «· Bottom» a la casa és aquella funció, i n'hi ha d'haver una sola.
 */
export function filaAmbIdentitat(fila, pendents) {
  return { ...fila, ...identitatEfectiva(fila, pendents) }
}

// ═══════════════════════════════════════════════════════════════════════════════════════
// SET-2/T8-ter · LA PEÇA — I PER QUÈ NO SEGUEIX LA LLEI DE LES ALTRES DUES
//
// P2-ter diu «LA FILA INFORMA, NO EDITA»: capa i instància se'n van al panell i la fila només
// les llegeix. La peça fa el contrari —desplegable a la fila, sempre visible, a la dreta de
// tot— i **no és una excepció, és una NATURA de dada diferent** (Agus, 16/08, §6):
//
//   · capa i instància són EIXOS DE GERMANOR: matisos d'UNA mesura («el pit de l'exterior i el
//     pit del folre»). Es responen mirant la mesura de prop → el panell, i la fila n'informa.
//   · la peça és una FRONTERA: de QUI és aquesta fila. Es respon mirant la COLUMNA sencera
//     («quines files són del short?») i s'ha de poder escanejar i corregir en bloc sense obrir
//     res. Amagar-la al panell obligaria a obrir divuit files per repartir un document.
//
// La distinció ja era llei al BACKEND abans que a la UI: `_load_grading_rules_per_garment`
// (`pom/services.py`) diu, literal, que la capa i la instància no entren a la clau de la regla
// perquè són eixos de germanor, i que el garment SÍ perquè és una frontera (D4). La UI, doncs,
// no n'estrena cap: la fa visible.
//
// El TRANSPORT, en canvi, és el mateix i a posta: la peça pendent viu al MATEIX mapa que els
// altres dos eixos. El comentari de dalt ja argumenta per què no n'hi ha un per eix —dos mapes
// paral·lels sobre la mateixa fila són dues veritats que un dia discrepen— i això no canvia
// perquè la pregunta sigui d'una altra natura.
// ═══════════════════════════════════════════════════════════════════════════════════════

/**
 * La PEÇA que la fila ha de dir: la pendent si n'hi ha, si no la desada, i si no la de la
 * SESSIÓ. `??` per la mateixa raó que als altres dos eixos: `''` és la decisió «la mare» i amb
 * `||` es llegiria com «no s'ha triat res», ressuscitant la desada.
 *
 * ⚠️ LA PROPOSTA HI ENTRA — CORRECCIÓ DEL 16/08, i val la pena dir per què era al revés.
 *
 * Aquesta funció excloïa `garment_proposat` amb l'argument «una proposta que ningú ha confirmat
 * no pot viatjar com si fos una decisió». Sona bé i era FALS a la pantalla: el detector del pas 2
 * comparava la fila com si fos de la mare mentre el desplegable deia «Short», i la Brumà donava
 * «M1 xoca amb G1» amb la peça informada a la cel·la (QA Agus, captura 13:21). **Un conflicte
 * calculat contra una cosa que la pantalla no mostra és una acusació que no es pot verificar.**
 *
 * El disseny d'Agus ja ho deia amb la paraula justa: la secció del document és el **PRE-MARCAT**.
 * Un pre-marcat és un valor POSAT que l'usuari pot canviar, no una insinuació — i enviar el pas
 * l'accepta, com qualsevol casella pre-marcada de la casa.
 *
 * `estatDeLaPeca` segueix distingint QUI ho ha dit (verd = una persona · àmbar = el document), que
 * és el que la columna ha de deixar escanejar. El que ja no fa és que les dues meitats de la
 * pantalla parlin de files diferents.
 */
export function pecaEfectiva(fila, pendents, garmentSessio = '') {
  const p = (pendents || {})[(fila || {}).ordre] || {}
  return (p.garment ?? (fila || {}).garment ?? (fila || {}).garment_proposat ?? garmentSessio) || ''
}

/**
 * L'ESTAT de la cel·la de peça: `'decidit'` · `'proposat'` · `'defecte'`.
 *
 * Els tres colors de la columna (verd · àmbar · neutre) surten d'aquí i no del component: és
 * una regla i es prova amb `node --test`, no mirant una pantalla.
 *
 * `decidit` és **qualsevol tria humana**, també la que CONFIRMA el proposat amb un clic — i
 * també quan coincideix amb la mare. «Ningú no ho ha mirat» i «algú ha dit que és de la mare»
 * no són el mateix estat, i la columna existeix precisament per poder distingir-los d'un cop
 * d'ull.
 */
export function estatDeLaPeca(fila, pendents) {
  const p = (pendents || {})[(fila || {}).ordre] || {}
  if (p.garment !== undefined || (fila || {}).garment !== undefined) return 'decidit'
  if ((fila || {}).garment_proposat) return 'proposat'
  return 'defecte'
}

/**
 * La peça que la cel·la MOSTRA: la decidida si n'hi ha, i si no la PROPOSADA (que és el sentit
 * de proposar-la — que es vegi ja col·locada i només calgui confirmar-la).
 */
export function pecaVisible(fila, pendents, garmentSessio = '') {
  return pecaEfectiva(fila, pendents, garmentSessio)
}

// SET-2/T8-ter · I PER PEÇA ÉS UNA PARTICIÓ, NO UNA TIRA DE GRUPS CONSECUTIUS.
//
// La diferència amb `agrupaPerSeccio` no és d'estil. La SECCIÓ és una capçalera del DOCUMENT i
// per això s'insereix quan canvia i pot repetir-se: així ho diu el paper. La PEÇA és una
// FRONTERA del model, i el pas 3 és el patró de contenidors de la casa (`PecesDelModel`) —
// primer la mare, després cada peça, cadascuna amb TOTES les seves files. Un document que
// alterni faldilla · short · faldilla ha de donar DOS contenidors, no tres: si no, el tècnic
// veuria la mateixa peça dues vegades i no sabria quina de les dues taules és «la del short».
//
// L'ORDRE és el de `peces` (la mare primer, que és com `peces_del_model` les serveix), no el
// d'aparició al document: el contenidor és del model i el seu ordre és el del model.
export const agrupaPerPeca = (items, pecaDe, ordreCodis) => {
  const perCodi = new Map()
  for (const item of items) {
    const codi = pecaDe(item) || ''
    if (!perCodi.has(codi)) perCodi.set(codi, [])
    perCodi.get(codi).push(item)
  }
  const ordre = (ordreCodis || []).length ? ordreCodis : [...perCodi.keys()]
  const grups = []
  for (const codi of ordre) {
    if (perCodi.has(codi)) { grups.push({ codi, items: perCodi.get(codi) }); perCodi.delete(codi) }
  }
  // Les peces que ja no són del model (esborrades enmig d'un import) no desapareixen de la
  // taula: es pinten al final amb el seu codi. Amagar-les seria perdre files en silenci.
  for (const [codi, items2] of perCodi) grups.push({ codi, items: items2 })
  return grups
}
