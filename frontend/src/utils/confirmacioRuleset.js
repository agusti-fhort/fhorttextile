// QUINA CONFIRMACIÓ JA S'HA DEMANAT — SET-2/T7-B4.
//
// `useConfirmacioRuleset` reintenta mentre el backend torni un 409 conegut: pregunta, l'usuari
// diu que sí, i el reintent porta el flag d'aquell cas. La pregunta que aquest mòdul respon és
// **quan dos 409 són el MATEIX avís i quan són dos avisos diferents**, perquè d'això depèn si el
// bucle torna a preguntar o es planta.
//
// ── PER QUÈ LA CLAU CREIX A (TIPUS, GARMENT) ───────────────────────────────────────────────
// Fins ara la memòria del bucle era el NOM DEL FLAG i prou: un cop demanat
// `esborrat_residents`, un segon 409 del mateix `tipus` es llegia com «el backend no ha acceptat
// el flag» i es rellançava com a error. Amb UNA sola prenda això era exacte. Amb dues no ho és:
// des de SET-2/R11 el 409 diu DE QUINA PEÇA parla (`per_garment`, i `garment` quan l'avís és
// d'una sola), i «esborrar les regles de la 02» i «esborrar les de la mare» són dos gestos
// distints que mereixen dues preguntes. Amb la clau vella, el segon arribava a l'usuari com una
// avaria vermella en comptes d'una pregunta.
//
// ⚠️ EL QUE AQUESTA CLAU **NO** FA és inventar-se un flag per peça. El flag que el servidor
// accepta avui és d'abast MODEL (`confirmar_esborrat_residents`), i un client que n'enviés un de
// scoped parlaria un dialecte que l'altra banda no entén. Aquí només es decideix QUANTES VEGADES
// es pregunta; QUÈ autoritza cada resposta ho segueix dient el contracte del servidor. El dia
// que una porta validi prenda a prenda, el flag necessitarà l'abast al servidor i aquest mòdul
// ja hi estarà a punt.
//
// Mòdul pur i sense dependències: es prova amb `node --test` (vegeu confirmacioRuleset.test.js).

/**
 * Els 409 que es poden CONFIRMAR, amb el flag que els autoritza al reintent.
 *
 * Els altres dos casos de `_validar_ruleset_assignable` (joc buit · sistema de talles divergent)
 * són bloqueig dur i arriben com a 400: no hi ha res a preguntar i no són d'aquí.
 */
export const FLAG_PER_TIPUS = {
  ruleset_altre_client: 'confirmar_altre_client',
  esborrat_residents: 'confirmar_esborrat_residents',
  etiquetes_fora_del_run: 'confirmar_etiquetes_fora_del_run',
}

/**
 * De quina prenda parla un avís.
 *
 * Mana el PAYLOAD (`garment`), que és qui ho sap; el context del gest només és el pla B per als
 * avisos que encara no el diuen. `''` és la mare, i és un valor legítim —no un «no ho sé»—: la
 * llei del vocabulari (F22) ja va tancar que un eix buit i un eix absent no es poden confondre.
 */
export function garmentDeLavis(dades, contextGarment = '') {
  const delPayload = dades?.garment
  return typeof delPayload === 'string' ? delPayload : (contextGarment || '')
}

/**
 * La clau amb què el bucle recorda que ja ha preguntat això. `null` = no és un avís confirmable.
 *
 * Dos avisos amb el mateix `tipus` però de peces diferents donen DUES claus, i per tant dues
 * preguntes. Dos avisos idèntics en donen una: repetir-la seria un bucle infinit amb cara de
 * pantalla penjada, que és el que la memòria del bucle evita des del primer dia.
 */
export function clauDeConfirmacio(dades, contextGarment = '') {
  const tipus = dades?.tipus
  if (!FLAG_PER_TIPUS[tipus]) return null
  return `${tipus}|${garmentDeLavis(dades, contextGarment)}`
}
