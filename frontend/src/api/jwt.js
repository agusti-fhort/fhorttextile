/**
 * Lectura LOCAL de la caducitat d'un JWT. Mòdul pur (cap import) → provable amb `node --test`.
 *
 * PER QUÈ ES POT FER: un JWT està SIGNAT, no xifrat. El payload és base64url i qualsevol el
 * pot llegir; el que no es pot és falsificar-lo sense la clau. Llegir-ne `exp` al client no
 * és cap forat: és informació que el navegador ja té a les mans.
 *
 * QUIN CAMÍ S'HA PRES (K5) i per què: es decodifica el REFRESH token i se'n llegeix `exp`
 * directament. L'alternativa —derivar-ho de l'`exp` de l'access multiplicat pel cicle— seria
 * una estimació quan la dada exacta és aquí mateix, i a més seria FALSA: amb
 * ROTATE_REFRESH_TOKENS=True, `TokenRefreshSerializer.validate` crida `refresh.set_exp()` a
 * cada rotació (verificat al paquet instal·lat), de manera que la sessió és LLISCANT — acaba
 * 7 dies després de l'últim refresh, no 7 dies després del login. Només el refresh token viu
 * sap quan s'acaba de debò.
 *
 * El camí proxy queda com a fallback si el token no és llegible: sense `exp` no s'avisa (i
 * mana K1, que ja cobreix el cas amb un missatge humà). Val més no avisar que avisar quan no toca.
 */

/** Payload d'un JWT, o null si no és llegible. Mai llança. */
export function llegeixPayload(token) {
  if (typeof token !== 'string') return null
  const parts = token.split('.')
  if (parts.length !== 3) return null
  try {
    // base64url → base64, i el padding que `atob` exigeix.
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const ple = b64 + '='.repeat((4 - (b64.length % 4)) % 4)
    const cru = typeof atob === 'function'
      ? atob(ple)
      : Buffer.from(ple, 'base64').toString('binary')   // Node, per als tests
    // El payload pot portar accents: cal desfer l'UTF-8 abans de parsejar.
    const text = decodeURIComponent(
      Array.from(cru, c => '%' + c.charCodeAt(0).toString(16).padStart(2, '0')).join(''))
    const dades = JSON.parse(text)
    return (dades && typeof dades === 'object') ? dades : null
  } catch {
    return null
  }
}

/** Instant de caducitat en MIL·LISEGONS (el `exp` del JWT va en segons), o null. */
export function llegeixExpMs(token) {
  const payload = llegeixPayload(token)
  const exp = payload?.exp
  return (typeof exp === 'number' && Number.isFinite(exp)) ? exp * 1000 : null
}
