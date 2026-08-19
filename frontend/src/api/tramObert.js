import { useEffect, useState } from 'react'

import { modelTasks, timers } from './endpoints'
import { creaFontTramObert } from './tramObertCore'

/**
 * F3.2 · EL TRAM OBERT — cablatge de la font única (S-18).
 *
 * La DECISIÓ viu a `tramObertCore.js` (pur, provable); aquí només hi ha els endpoints, el
 * rellotge i el hook. Els estats i el contracte de fallada són allà, i cal llegir-los abans de
 * tocar cap consumidor: `ERR_LLISTA` i `ERR_TASCA` són estats diferents a posta perquè el guard
 * i la píndola hi han de reaccionar diferent.
 */

export { CAP, ERR_LLISTA, ERR_TASCA, OBERT } from './tramObertCore'

const REFRESC_MS = 60_000   // el ritme que ja tenien tots dos: la sessió no canvia més de pressa

let interval = null
let alTornar = null

const font = creaFontTramObert({
  llistaTrams: () => timers.list({ actiu: 'true' }),
  llegeixTasca: id => modelTasks.get(id),
  arrenca: consulta => {
    interval = setInterval(consulta, REFRESC_MS)
    // En tornar el focus es rellegeix: si la pestanya ha estat hores en segon pla, el que hi
    // havia pot ser vell. Ho tenia el guard i ara ho tenen tots dos — és estrictament més
    // informació, cap consumidor no en perd cap cas.
    alTornar = () => { if (document.visibilityState === 'visible') consulta() }
    document.addEventListener('visibilitychange', alTornar)
    window.addEventListener('focus', alTornar)
  },
  atura: () => {
    clearInterval(interval)
    interval = null
    document.removeEventListener('visibilitychange', alTornar)
    window.removeEventListener('focus', alTornar)
    alTornar = null
  },
})

export const refresca = () => font.refresca()
export const subscriu = fn => font.subscriu(fn)

/** El tram obert, per a components. `null` mentre no hi ha hagut cap lectura encara. */
export function useTramObert() {
  const [resultat, setResultat] = useState(() => font.ultim)
  useEffect(() => subscriu(setResultat), [])
  return resultat
}
