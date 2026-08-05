/**
 * F2.3 · LA SESSIÓ ACTIVA — decisió pura (el JSX viu a `components/SessioActiva.jsx`).
 *
 * D-2 diu que el Stop és l'ÚNIC gest que tanca una tasca, i que Done és el que entra a albarà.
 * Perquè això sigui just, el tècnic ha de poder veure en tot moment QUÈ té obert i des de quan:
 * un gest que factura no pot dependre de recordar-se'n.
 *
 * ⚠️ UN TRAM OBERT NO ÉS PROVA QUE LA TASCA ESTIGUI EN CURS. A staging hi ha (hi havia) timers
 * zombis oberts damunt de tasques ja pausades. `GuardTascaOblidada` ja va aprendre aquesta
 * lliçó a base de 282 POSTs en minuts; l'indicador la hereta en comptes de repetir-la:
 * la font de veritat és l'ESTAT DE LA TASCA, i el tram només hi posa el rellotge.
 */

/** Segons transcorreguts des de l'obertura del tram. `ara` s'injecta per fer-ho provable. */
export function segonsDeSessio(tram, ara = Date.now()) {
  if (!tram?.inici) return 0
  return Math.max(0, Math.floor((ara - new Date(tram.inici).getTime()) / 1000))
}

/** `1h 05m` · `12m` · `0m`. Sense segons: l'indicador informa, no cronometra. */
export function durada(segons) {
  const total = Math.max(0, Math.floor(segons / 60))
  const h = Math.floor(total / 60)
  const m = total % 60
  return h > 0 ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`
}

/**
 * Què ha d'ensenyar l'indicador. Retorna `null` quan no ha d'aparèixer — i el cas «no apareix»
 * és tan important com l'altre: un indicador que menteix sobre una sessió que no corre és pitjor
 * que no tenir-ne cap.
 *
 * @param {object|null} tram   fila de `TimerEntrada` (la del propi tècnic, oberta)
 * @param {object|null} tasca  fila de `ModelTaskSerializer` corresponent
 */
export function estatSessio(tram, tasca) {
  if (!tram || tram.fi != null) return null
  if (!tasca || tasca.status !== 'InProgress') return null   // tram zombi: no s'ensenya
  return {
    timerId: tram.id,
    taskId: tasca.id,
    nom: tasca.task_type_name || tasca.task_type_code || '',
    model: tasca.model_codi || '',
    modelId: tasca.model,
    inici: tram.inici,
    declarat: tram.origen === 'declarat',
  }
}
