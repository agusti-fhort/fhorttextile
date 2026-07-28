import { apiBaseURL } from './base'
import { esTokenCaducat } from './errorsAuth'
import { sessio } from './sessio'

/**
 * `fetch` amb Bearer i refresh — la mateixa llei que el client axios, per a les vies que
 * no hi passen.
 *
 * PER QUÈ CAL (cas real de PROD, captura 28/07 07:53): pujar un JPG al tab Fitxers amb
 * l'access token caducat no es reintentava mai. La pujada anava amb `fetch` cru, i el
 * `fetch` no té interceptors: el 401 arribava a la pantalla com a JSON de DRF i el fitxer
 * es perdia. La persona havia de tornar a entrar i tornar a triar el fitxer.
 *
 * Comparteix el mutex de `sessio.js` amb el client axios: N crides que fallin alhora
 * —vinguin d'on vinguin— fan UN sol refresh i es reintenten totes.
 *
 * REINTENT I COS DE LA PETICIÓ: FormData, Blob, string i URLSearchParams es poden tornar a
 * enviar tal qual, i és el que fa que la pujada no perdi el fitxer. Un `body` que sigui un
 * ReadableStream NO és reenviable (es consumeix en el primer intent); avui cap crida de la
 * casa n'usa, i si algun dia se n'usa un caldrà reconstruir-lo a cada intent.
 */
export async function authFetch(url, options = {}) {
  const fesLaCrida = token => fetch(apiBaseURL + url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  const res = await fesLaCrida(localStorage.getItem('access_token'))
  if (res.status !== 401) return res

  // `clone()` perquè qui ens ha cridat pugui llegir el cos igualment si resulta que el 401
  // no era de caducitat (llegir-lo dues vegades del mateix Response llançaria).
  const dades = await res.clone().json().catch(() => null)
  if (!esTokenCaducat(dades)) return res   // 401 de permisos: no és cosa nostra

  // `sessio.refresca()` tanca la sessió i redirigeix tot sol si el refresh també és mort;
  // aquí només cal no empassar-se l'error, perquè qui ha cridat sàpiga que no hi ha resposta.
  const access = await sessio.refresca()
  return fesLaCrida(access)
}

/** Igual que `authFetch` però retornant el JSON ja llegit i el `Response`, que és la
 *  forma que fan servir gairebé totes les crides de la casa. */
export async function authFetchJson(url, options = {}) {
  const res = await authFetch(url, options)
  const dades = await res.json().catch(() => null)
  return { res, dades, ok: res.ok }
}
