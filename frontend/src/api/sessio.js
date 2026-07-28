import axios from 'axios'

import { apiBaseURL } from './base'

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
 * `creaGestorSessio` és una fàbrica amb les dependències injectades perquè la lògica del
 * mutex es pugui provar sense navegador (`node --test`): sense localStorage, sense axios i
 * sense `window.location`.
 */
export function creaGestorSessio({ llegeixRefresh, desaTokens, demanaRefresh, tancaSessio }) {
  // La promesa del refresh EN CURS. És el mutex: qui arriba mentre n'hi ha un de viu
  // s'espera al mateix, no en dispara un altre.
  let enCurs = null

  return {
    /** Retorna una promesa amb l'access token NOU. Si no es pot refrescar, tanca la
     *  sessió i rebutja — qui l'ha cridada no ha de decidir res més. */
    refresca() {
      if (enCurs) return enCurs

      const refresh = llegeixRefresh()
      if (!refresh) {
        tancaSessio()
        return Promise.reject(new Error('sessio: no hi ha refresh token'))
      }

      enCurs = demanaRefresh(refresh)
        .then(dades => {
          desaTokens(dades)
          return dades.access
        })
        .catch(err => {
          // El refresh també és mort (caducat o invàlid): ARA sí que s'ha acabat la sessió.
          tancaSessio()
          throw err
        })
        .finally(() => { enCurs = null })

      return enCurs
    },

    /** Només per a tests i diagnòstic: hi ha un refresh viu? */
    get enMarxa() { return enCurs !== null },
  }
}

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
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // El motiu viatja fins a /login perquè hi surti un missatge humà en comptes de deixar
    // la persona davant d'un formulari buit sense saber què ha passat.
    try { sessionStorage.setItem(CLAU_SESSIO_CADUCADA, '1') } catch { /* mode privat */ }
    window.location.href = '/login'
  },
})
