/**
 * QUAN toca avisar que la sessió s'acaba. Mòdul pur (cap import) → provable amb `node --test`.
 *
 * Es raona amb INSTANTS ABSOLUTS, mai amb comptadors acumulats — la mateixa decisió que ja
 * mana a `GuardTascaOblidada` i pel mateix motiu: les pestanyes en segon pla es throttlegen i
 * un comptador quedaria endarrerit exactament en el cas que això ha de cobrir (algú que torna
 * al portàtil al cap d'una estona). Qui decideix és `Date.now()` contra l'`exp` del token; el
 * tick només serveix per mirar-ho de tant en tant.
 */

/** Marge d'avís: 5 minuts abans de la fi REAL de la sessió (decisió K5). */
export const MARGE_AVIS_MS = 5 * 60 * 1000

/** Cada quant es mira. No cal setTimeout llarg: un timer de dies no sobreviu a una
 *  suspensió del portàtil, i un sondeig curt sí. */
export const TICK_AVIS_MS = 30 * 1000

export const ESTAT_VIVA = 'viva'          // queda temps de sobres
export const ESTAT_AVIS = 'avis'          // dins dels últims 5 min: cal preguntar
export const ESTAT_CADUCADA = 'caducada'  // ja s'ha acabat

/**
 * Estat de la sessió en un instant donat.
 * @param expMs  caducitat del refresh token en ms (null = no llegible)
 * @param araMs  `Date.now()`
 */
export function estatSessio(expMs, araMs) {
  // Sense dada no s'inventa res: mana K1 (401 → missatge humà). Avisar per suposició seria
  // pitjor que no avisar.
  if (typeof expMs !== 'number' || !Number.isFinite(expMs)) return ESTAT_VIVA
  if (araMs >= expMs) return ESTAT_CADUCADA
  if (araMs >= expMs - MARGE_AVIS_MS) return ESTAT_AVIS
  return ESTAT_VIVA
}

/**
 * Cal obrir el modal ARA?
 *
 * `expVist` és l'`exp` pel qual ja s'ha preguntat. És el que fa que el modal sigui UN PER
 * CICLE DE SESSIÓ i no un bucle: en prémer «Continua treballant» es refresca, el token nou
 * porta un `exp` NOU (ROTATE_REFRESH_TOKENS + `set_exp()`) i el modal es tornarà a armar per
 * a aquell, no per a aquest. Si l'usuari tanca el modal sense respondre, tampoc reapareix per
 * al mateix cicle: quan venci, mana K1.
 */
export function calAvisar(expMs, araMs, expVist) {
  return estatSessio(expMs, araMs) === ESTAT_AVIS && expMs !== expVist
}
