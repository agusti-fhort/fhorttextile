// LA FONT del diccionari d'identitat: qui el va a buscar i el memoritza.
//
// Separat de `diccionariMesures.js` perquè aquell fitxer no ha d'importar res (les regles de
// composició es proven amb `node --test`, i el runner no resol imports sense extensió). Aquí hi
// ha l'accés a dades i el hook; allà, el càlcul.
//
// LA RESPOSTA ES MEMORITZA A NIVELL DE MÒDUL: el vocabulari de la casa no canvia durant una
// sessió, i quatre pantalles que l'obrissin farien quatre peticions idèntiques.
//
// LA PROMESA ES COMPARTEIX (no només el resultat): dues pantalles que muntin alhora esperen la
// MATEIXA petició en comptes de disparar-ne dues. Si falla, es descarta perquè el proper muntatge
// ho torni a provar — un error de xarxa no pot deixar la sessió sense vocabulari per sempre.

import { useEffect, useState } from 'react'
import { diccionariMesures } from '../api/endpoints'

let cache = null
let enVol = null

/** Buida la memòria (proves; i el dia que hi hagi una pantalla d'edició del vocabulari). */
export function oblidaDiccionari() { cache = null; enVol = null }

export function carregaDiccionari() {
  if (cache) return Promise.resolve(cache)
  if (enVol) return enVol
  enVol = diccionariMesures.get()
    .then(r => { cache = r.data; enVol = null; return cache })
    .catch(e => { enVol = null; throw e })
  return enVol
}

/**
 * El diccionari, o `null` mentre no ha arribat. **Cap pantalla ha d'esperar-lo per pintar-se**:
 * amb `null` els gestos que en depenen queden inerts i la taula es veu igual. Un vocabulari que
 * triga no pot ser una pantalla en blanc.
 */
export function useDiccionariMesures() {
  const [dicc, setDicc] = useState(cache)
  useEffect(() => {
    if (cache) { setDicc(cache); return }
    let viu = true
    carregaDiccionari().then(d => { if (viu) setDicc(d) }).catch(() => {})
    return () => { viu = false }
  }, [])
  return dicc
}
