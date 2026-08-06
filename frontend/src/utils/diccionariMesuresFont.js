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

import { useCallback, useEffect, useState } from 'react'
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
 * L'ESTAT del vocabulari: `{dicc, error, reintenta}`.
 *
 * **`error` existeix perquè «encara no ha arribat» i «no arribarà» no són el mateix**, i fins ara
 * es deien igual —`null` totes dues— amb un `.catch(() => {})` al mig. La conseqüència es va
 * veure el 06/08 amb el MILEY: el GET del diccionari va fallar, les columnes d'INSTÀNCIA van
 * desaparèixer de «Definició POM» **sense dir res**, i des de la pantalla allò no es distingia
 * d'un catàleg que no en tingués. No es podien crear germanes i no hi havia cap pista de per què.
 *
 * `reintenta` hi és perquè el mode de fallada típic és transitori (una petició que surt abans que
 * la sessió estigui a punt). Sense ell, l'única sortida era recarregar la pàgina i perdre el que
 * s'estava escrivint.
 *
 * Segueix valent la llei de sempre: **cap pantalla no l'ha d'esperar per pintar-se**. Amb `dicc`
 * a `null` la taula es veu igual; el que canvia és que si és per un error, es DIU.
 */
export function useEstatDiccionari() {
  const [estat, setEstat] = useState(() => ({ dicc: cache, error: false }))
  const [intent, setIntent] = useState(0)
  useEffect(() => {
    let viu = true
    // Sense drecera per a `cache`: `carregaDiccionari()` ja resol immediat quan la té, i així
    // no hi ha cap `setState` síncron dins de l'efecte (renderitzades en cascada).
    carregaDiccionari()
      .then(d => { if (viu) setEstat({ dicc: d, error: false }) })
      .catch(() => { if (viu) setEstat({ dicc: null, error: true }) })
    return () => { viu = false }
  }, [intent])
  // `oblidaDiccionari()` abans de reintentar: si no, la promesa fallada ja s'ha descartat però
  // una `cache` a mitges es podria donar per bona.
  const reintenta = useCallback(() => {
    oblidaDiccionari()
    setEstat({ dicc: null, error: false })
    setIntent(n => n + 1)
  }, [])
  return { ...estat, reintenta }
}

/** El diccionari i prou, per a qui no ha de dir res quan falla. */
export function useDiccionariMesures() {
  return useEstatDiccionari().dicc
}
