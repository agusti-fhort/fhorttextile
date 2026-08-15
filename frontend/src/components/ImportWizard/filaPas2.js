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
 * La instància que la fila ha de DIR: la PENDENT si n'hi ha, i si no, la desada.
 *
 * `??` i no `||` a posta: `''` és una decisió («treu-la, torna a la instància única») i amb `||`
 * es llegiria com «no s'ha triat res», ressuscitant la desada. La diferència es veu en un sol
 * gest: treure la instància d'una fila que ja en tenia una.
 */
export function instanciaEfectiva(fila, pendents) {
  const pendent = (pendents || {})[(fila || {}).ordre]
  return (pendent ?? (fila || {}).instancia) || ''
}

/**
 * La fila tal com s'ha de LLEGIR: la mateixa, amb la identitat efectiva. Es passa sencera a
 * `sufixIdentitat` (la porta única) en comptes de compondre aquí cap etiqueta: qui escriu
 * «· Bottom» a la casa és aquella funció, i n'hi ha d'haver una sola.
 */
export function filaAmbIdentitat(fila, pendents) {
  return { ...fila, instancia: instanciaEfectiva(fila, pendents) }
}
