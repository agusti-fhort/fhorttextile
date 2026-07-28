/**
 * EL MUTEX DEL REFRESH, sense navegador.
 *
 * Mòdul PUR a posta: cap import (ni axios, ni `import.meta.env`, ni localStorage). És el
 * que permet provar-lo amb el runner natiu de Node — `node --test src/api/sessio.test.js`
 * —, que és el que fa la casa. El cablatge real (axios, localStorage, `window.location`)
 * viu a `sessio.js` i s'injecta aquí.
 *
 * PER QUÈ UN MUTEX: amb ROTATE_REFRESH_TOKENS=True (settings.py:228) cada crida a
 * /api/token/refresh/ ROTA el refresh token. Dos refreshos concurrents → el segon es queda
 * amb un token que el primer acaba de substituir → expulsió amb la sessió encara vàlida.
 * I les crides concurrents no són hipotètiques: una pantalla dispara 11 XHR alhora
 * (ràfega real, DIAGNOSI_RENDIMENT_SESSIO_2026-07-22 §B2.4).
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

    /** Hi ha un refresh viu? (tests i diagnòstic) */
    get enMarxa() { return enCurs !== null },
  }
}
