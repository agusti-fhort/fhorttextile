/**
 * K6 capa 1 — la DECISIÓ de pausar, sense navegador.
 *
 * Mòdul pur (cap import) → provable amb `node --test`. El cablatge real (fetch, localStorage,
 * apiBaseURL) viu a `tascaActiva.js` i s'injecta aquí, com ja fa `sessioCore.js`.
 *
 * LA LLEI: marxar de la feina no és acabar-la. Això només sap demanar `Paused`; `Done` és un
 * gest humà i no surt mai d'aquí.
 */
export function creaPausador({ llegeixToken, envia }) {
  let idTascaActiva = null

  return {
    /** La crida `GuardTascaOblidada` quan sap quina tasca duc En curs (o null). */
    recorda(taskId) { idTascaActiva = taskId ?? null },

    get id() { return idTascaActiva },

    /**
     * Intenta pausar. SEMPRE resol, mai rebutja: `true` si el servidor ho ha acceptat.
     * El fracàs s'empassa perquè aquesta capa és un intent, no la garantia — i sobretot
     * perquè no pot bloquejar mai la sortida de qui està tancant la sessió.
     */
    pausa() {
      const id = idTascaActiva
      if (!id) return Promise.resolve(false)
      const token = llegeixToken()
      if (!token) return Promise.resolve(false)

      return Promise.resolve()
        .then(() => envia(id, token))
        .then(ok => {
          // Només s'oblida si de debò s'ha pausat: si ha fallat, la tasca segueix En curs i
          // el proper intent (o el cron) l'ha de poder veure.
          if (ok) idTascaActiva = null
          return !!ok
        })
        .catch(() => false)
    },
  }
}
