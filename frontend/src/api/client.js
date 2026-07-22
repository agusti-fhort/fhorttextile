import axios from 'axios'

/**
 * BASE URL — SAME-ORIGIN per defecte.
 *
 * Abans el baseURL era `import.meta.env.VITE_API_URL` a seques, i `.env` hi posava un
 * domini ABSOLUT (p.ex. `https://staging.fhorttextile.tech`). Conseqüència estructural:
 * el build quedava CABLEJAT a un domini, i qualsevol altre host que servís el mateix
 * `dist/` enviava igualment les crides al domini cablejat — amb el Host equivocat, que
 * amb django-tenants vol dir el TENANT equivocat. D'aquí naixia la necessitat de tenir
 * un build per domini (`dist-tenants/`) i d'obrir CORS cap a l'origen cablejat.
 *
 * Ara el defecte és RELATIU (`''`): la crida cau sobre l'origen que ha servit la pàgina,
 * el Host real viatja tal qual i UN SOL build serveix qualsevol domini/tenant. És el
 * mateix patró que `tenantDiscovery.submit` (endpoints.js) ja feia a posta.
 *
 * `VITE_API_URL` sobreviu com a OVERRIDE opcional: si està definit i no és buit, mana
 * (cas del dev local, on el front va a :5173 i el back a :8000 → `.env.development`).
 */
export const apiBaseURL = import.meta.env.VITE_API_URL || ''

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
 * Instància separada per al refresh: si es fes amb `client` entraria pel seu propi
 * interceptor de resposta, i un refresh caducat provocaria una recursió infinita.
 */
const refreshClient = axios.create({
  baseURL: apiBaseURL,
  headers: { 'Content-Type': 'application/json' },
})

// Rutes on un 401 NO vol dir «token caducat» sinó «credencials dolentes»: refrescar-hi no
// té sentit i emmascararia l'error real del formulari de login.
const RUTES_SENSE_REFRESH = ['/api/token/', '/api/token/refresh/']

let isRefreshing = false
// Cua de les peticions que reben un 401 MENTRE un refresh ja està en marxa. Sense ella,
// una pantalla que dispara 11 XHR alhora (ràfega real mesurada, §B2.4) faria 11 crides
// simultànies a /refresh/: amb ROTATE_REFRESH_TOKENS=True cadascuna rota el token i les
// altres deu es quedarien amb un refresh ja substituït.
let cuaEspera = []

const resolCua = (error, token = null) => {
  cuaEspera.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token)))
  cuaEspera = []
}

const tancaSessio = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  window.location.href = '/login'
}

client.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status !== 401 || !original) return Promise.reject(err)
    if (RUTES_SENSE_REFRESH.some(r => original.url?.includes(r))) return Promise.reject(err)

    // Ja s'havia reintentat amb un token acabat de refrescar i ha tornat a fer 401: el
    // problema no és la caducitat. No insistim (és el que talla qualsevol bucle).
    if (original._reintentat) {
      tancaSessio()
      return Promise.reject(err)
    }

    const refresh = localStorage.getItem('refresh_token')
    if (!refresh) {
      tancaSessio()
      return Promise.reject(err)
    }

    // Ja hi ha un refresh en marxa: esperar-lo i reintentar amb el token que en surti.
    if (isRefreshing) {
      return new Promise((resolve, reject) => cuaEspera.push({ resolve, reject }))
        .then(token => {
          original._reintentat = true
          original.headers.Authorization = `Bearer ${token}`
          return client(original)
        })
    }

    isRefreshing = true
    try {
      const { data } = await refreshClient.post('/api/token/refresh/', { refresh })
      localStorage.setItem('access_token', data.access)
      // ROTATE_REFRESH_TOKENS=True (settings.py:228): la resposta porta un refresh NOU i
      // l'antic queda substituït. Si no el desàvem, la sessió moriria als 7 dies del
      // login en comptes d'anar-se renovant amb l'ús.
      if (data.refresh) localStorage.setItem('refresh_token', data.refresh)

      resolCua(null, data.access)
      original._reintentat = true
      original.headers.Authorization = `Bearer ${data.access}`
      return client(original)
    } catch (errRefresh) {
      // El refresh també és mort (caducat o invàlid): ARA sí que s'ha acabat la sessió.
      // Aquest és el comportament d'abans, però com a fallback, no com a primera reacció.
      resolCua(errRefresh)
      tancaSessio()
      return Promise.reject(err)
    } finally {
      isRefreshing = false
    }
  }
)

export default client
