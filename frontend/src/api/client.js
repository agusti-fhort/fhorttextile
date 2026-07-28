import axios from 'axios'

import { apiBaseURL } from './base'
import { esTokenCaducat } from './errorsAuth'
import { sessio } from './sessio'

// `apiBaseURL` viu ara a `base.js` (el necessiten `sessio.js` i `authFetch.js` sense
// dependre d'aquest mòdul). Es re-exporta perquè `endpoints.js` l'importa d'aquí.
export { apiBaseURL }

const client = axios.create({
  baseURL: apiBaseURL,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/**
 * REFRESH DEL TOKEN — per què això existeix.
 *
 * L'access token dura 1 h i el refresh 7 dies (settings.py:226-227), però el front no
 * cridava MAI /api/token/refresh/: davant de QUALSEVOL 401 esborrava els dos tokens
 * —inclòs el refresh, vàlid 6 dies i 23 h més— i feia `window.location.href`, un hard
 * reload que s'emporta la feina en curs. Mesurat als logs: 0 crides de refresh contra
 * 104 re-logins en 14 dies, i un interval d'expulsió de 61 min 26 s.
 * (DIAGNOSI_RENDIMENT_SESSIO_2026-07-22 §B1.4, §B1.7.)
 *
 * Ara un 401 és una hipòtesi («potser l'access ha caducat»), no un veredicte: només és
 * fi de sessió si el refresh TAMBÉ falla.
 *
 * EL MUTEX JA NO VIU AQUÍ (K1): viu a `sessio.js`, perquè aquest client no és l'única via
 * de sortida de l'app — la pujada de fitxers i un centenar de crides més van amb `fetch`
 * cru. Si cada via tingués el seu, dos 401 concurrents per vies diferents dispararien dos
 * refreshos i, amb ROTATE_REFRESH_TOKENS=True, el segon es quedaria amb un token que el
 * primer acaba de substituir.
 */

// Rutes on un 401 NO vol dir «token caducat» sinó «credencials dolentes»: refrescar-hi no
// té sentit i emmascararia l'error real del formulari de login.
const RUTES_SENSE_REFRESH = ['/api/token/', '/api/token/refresh/']

client.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status !== 401 || !original) return Promise.reject(err)
    if (RUTES_SENSE_REFRESH.some(r => original.url?.includes(r))) return Promise.reject(err)

    // Un 401 de PERMISOS (token viu, però no hi tens accés) no es refresca: refrescar-lo
    // no canviaria res i acabaria expulsant per un error que no és de sessió.
    // Nota: DRF respon 403 en la majoria d'aquests casos; això cobreix els que arriben 401
    // sense `code: token_not_valid` (p.ex. capçalera absent en una ruta autenticada).
    if (err.response?.data && !esTokenCaducat(err.response.data)) return Promise.reject(err)

    // Ja s'havia reintentat amb un token acabat de refrescar i ha tornat a fer 401: el
    // problema no és la caducitat. No insistim (és el que talla qualsevol bucle).
    if (original._reintentat) return Promise.reject(err)

    try {
      const access = await sessio.refresca()
      original._reintentat = true
      original.headers.Authorization = `Bearer ${access}`
      return client(original)
    } catch {
      // `sessio.refresca()` ja ha tancat la sessió i ha redirigit. Es propaga l'error
      // ORIGINAL, no el del refresh: qui va fer la crida vol saber què li ha fallat.
      return Promise.reject(err)
    }
  }
)

export default client
