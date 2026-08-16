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
