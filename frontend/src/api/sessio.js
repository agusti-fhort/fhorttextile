import axios from 'axios'

import { apiBaseURL } from './base'
import { creaGestorSessio } from './sessioCore'
import { pausaTascaActiva } from './tascaActiva'

/**
 * ESTAT DE SESSIÓ COMPARTIT — un sol refresh per a tota l'app.
 *
 * Per què això viu aquí i no dins de `client.js`: el client axios compartit NO és l'única
 * via de sortida. El front té ~113 crides amb `fetch` cru (pujada de fitxers del tab
 * Fitxers inclosa), i cadascuna que gestionés el seu propi refresh seria un mutex a part.
 * Amb `ROTATE_REFRESH_TOKENS=True` (settings.py:228) això no és una ineficiència sinó un
 * BUG: dos refreshos concurrents roten el token i el segon es queda amb un refresh que el
 * primer acaba de substituir → expulsió. El mutex ha de ser un, i per tant ha de viure
 * fora de qui el fa servir.
 *
 * Aquest mòdul és el CABLATGE (axios + localStorage + window.location); la lògica del
 * mutex viu a `sessioCore.js`, que no importa res i per això es pot provar amb Node.
 */

// ── La instància real ───────────────────────────────────────────────────────────────────

// Clau de sessionStorage: el motiu pel qual s'ha tancat la sessió. `tancaSessio` fa un
// `window.location.href` (recàrrega dura), i això s'emporta qualsevol estat de React o de
// `location.state` — sessionStorage és el que sobreviu al salt fins a /login.
export const CLAU_SESSIO_CADUCADA = 'sessio_caducada'

// Instància axios SEPARADA per al refresh: si es fes amb `client` entraria pel seu propi
// interceptor de resposta, i un refresh caducat provocaria una recursió infinita.
const refreshClient = axios.create({
  baseURL: apiBaseURL,
  headers: { 'Content-Type': 'application/json' },
})

export const sessio = creaGestorSessio({
  llegeixRefresh: () => localStorage.getItem('refresh_token'),
  desaTokens: dades => {
    localStorage.setItem('access_token', dades.access)
    // ROTATE_REFRESH_TOKENS=True (settings.py:228): la resposta porta un refresh NOU i
    // l'antic queda substituït. Si no el desàvem, la sessió moriria als 7 dies del login
    // en comptes d'anar-se renovant amb l'ús.
    if (dades.refresh) localStorage.setItem('refresh_token', dades.refresh)
  },
  demanaRefresh: refresh =>
    refreshClient.post('/api/token/refresh/', { refresh }).then(r => r.data),
  tancaSessio: () => {
    // K6 capa 1 — abans d'esborrar res, intent de deixar la tasca En curs en pausa. Surt amb
    // el token que hi hagi (probablement mort: és la paradoxa acceptada) i `keepalive` la fa
    // sobreviure a la redirecció. No s'espera i no es mira el resultat: si falla, la capa 2
    // (cron `pausa_tasques_oblidades`) ho recull.
    pausaTascaActiva()

    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // El motiu viatja fins a /login perquè hi surti un missatge humà en comptes de deixar
    // la persona davant d'un formulari buit sense saber què ha passat.
    try { sessionStorage.setItem(CLAU_SESSIO_CADUCADA, '1') } catch { /* mode privat */ }
    window.location.href = '/login'
  },
})
