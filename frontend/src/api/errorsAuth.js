/**
 * Lectura dels errors d'autenticació de DRF/simplejwt.
 *
 * Mòdul PUR a posta: cap import de React, d'axios ni del DOM. És el que permet provar-lo
 * amb el runner natiu de Node (`node --test`), que és el que fa la casa (no hi ha vitest
 * ni jest — vegeu `components/grading/gradingAxes.test.js`).
 *
 * EL CAS REAL (captura de PROD, 28/07 07:53): pujar un JPG al tab Fitxers amb l'access
 * token caducat pintava el JSON cru de DRF com a banner:
 *
 *     {"detail":"Given token not valid for any token type","code":"token_not_valid",
 *      "messages":[{"token_class":"AccessToken","token_type":"access",
 *                   "message":"Token is expired"}]}
 *
 * Això no és un missatge: és un bolcat. La persona que hi era només necessitava saber que
 * havia de tornar a entrar.
 */

/** El 401 diu «el token no val»? És l'única forma fiable de distingir-ho d'un 401 de
 *  permisos: simplejwt hi posa SEMPRE `code: 'token_not_valid'`. */
export function esTokenCaducat(dades) {
  if (!dades || typeof dades !== 'object') return false
  return dades.code === 'token_not_valid'
}

/**
 * Missatge de banner a partir del cos d'error del servidor.
 *
 * ACOTAT a posta (no és un refactor general de tots els errors de la casa): tradueix els
 * codis CONEGUTS a llenguatge humà i deixa la resta EXACTAMENT com estava, perquè
 * cap error deixi de veure's mentre no se'n decideixi el text.
 *
 * @param dades  cos JSON de la resposta (o null si no era JSON)
 * @param t      la `t` d'i18next
 * @param crua   com es pintava abans el cas no reconegut (per defecte, el JSON cru)
 */
export function missatgeError(dades, t, crua = undefined) {
  if (esTokenCaducat(dades)) return t('auth.session_expired')
  if (crua !== undefined) return crua
  try { return JSON.stringify(dades) } catch { return String(dades) }
}
