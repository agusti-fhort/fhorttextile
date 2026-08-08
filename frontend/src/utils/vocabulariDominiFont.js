// LA FONT de les enumeracions de domini: qui les va a buscar i les memoritza.
//
// GERMÀ EXACTE de `diccionariMesuresFont.js` i a posta: aquella és la font del vocabulari
// d'IDENTITAT d'una mesura (capes, instàncies) i aquesta la de les enumeracions de CICLE
// (règims de graduació, fases del model, estats del model, fases de tasca). Mateixa forma,
// mateixes garanties, mateix idioma — la casa no ha de tenir dues maneres de llegir vocabulari.
//
// PER QUÈ EXISTEIX. Les llistes eren als `choices` dels models des de sempre i cap endpoint no
// les publicava, o sigui que el frontend se les escrivia a mà: ~20 constants en 17 fitxers. I
// havien derivat — la còpia dels règims a `SizeMapSetup` en tenia QUATRE quan el model en
// declara CINC (hi faltava `EXCEPTION`), i una maqueta va arribar a dibuixar un `LINEAR+BREAK`
// que no existeix ni pot existir. Llei d'Agus (08/08): **cap enumeració de domini es declara al
// frontend**; una constant al client que dupliqui uns `choices` és una segona font de veritat
// que ningú actualitza el dia que la primera canvia.
//
// LA RESPOSTA ES MEMORITZA A NIVELL DE MÒDUL i LA PROMESA ES COMPARTEIX: quatre pantalles que
// muntin alhora esperen la MATEIXA petició. Si falla, es descarta perquè el proper muntatge ho
// torni a provar.
//
// ⚠️ **CAP LLISTA DE RESERVA.** Si l'endpoint no contesta, `voc` és `null` i `error` és cert, i
// qui ho consumeix HO HA DE DIR i no oferir opcions. Escriure aquí una llista de fallback seria
// tornar a plantar la segona font de veritat que aquest mòdul existeix per matar — i pitjor,
// una que només es faria servir el dia que ningú la mira.

import { useCallback, useEffect, useState } from 'react'
import { vocabulariDomini } from '../api/endpoints'

let cache = null
let enVol = null

/** Buida la memòria (proves; i el dia que el vocabulari sigui editable). */
export function oblidaVocabulari() { cache = null; enVol = null }

export function carregaVocabulari() {
  if (cache) return Promise.resolve(cache)
  if (enVol) return enVol
  enVol = vocabulariDomini.get()
    .then(r => { cache = r.data; enVol = null; return cache })
    .catch(e => { enVol = null; throw e })
  return enVol
}

/**
 * L'ESTAT del vocabulari: `{voc, error, reintenta}`.
 *
 * `error` existeix perquè «encara no ha arribat» i «no arribarà» no són el mateix — la lliçó del
 * MILEY (06/08), on un GET fallat va fer desaparèixer columnes sense dir res i des de la pantalla
 * allò no es distingia d'un catàleg buit. `reintenta` hi és perquè el mode de fallada típic és
 * transitori (una petició que surt abans que la sessió estigui a punt).
 */
export function useEstatVocabulari() {
  const [estat, setEstat] = useState(() => ({ voc: cache, error: false }))
  const [intent, setIntent] = useState(0)
  useEffect(() => {
    let viu = true
    carregaVocabulari()
      .then(v => { if (viu) setEstat({ voc: v, error: false }) })
      .catch(() => { if (viu) setEstat({ voc: null, error: true }) })
    return () => { viu = false }
  }, [intent])
  const reintenta = useCallback(() => {
    oblidaVocabulari()
    setEstat({ voc: null, error: false })
    setIntent(n => n + 1)
  }, [])
  return { ...estat, reintenta }
}

/**
 * Els CODIS d'una enumeració, o `null` mentre no se sap.
 *
 * Torna `null` —i no `[]`— quan el vocabulari no hi és, perquè `[]` voldria dir «aquesta
 * enumeració és buida» i això és una afirmació que no podem fer. Qui rep `null` no ha d'oferir
 * opcions; qui rep `[]` sí que en pot dir que no n'hi ha cap.
 *
 * @param {object|null} voc  el que torna `useEstatVocabulari().voc`
 * @param {string} clau      'regims_graduacio' · 'fases_model' · 'estats_model' · 'fases_tasca'
 */
export function codisDe(voc, clau) {
  const llista = voc?.[clau]
  return Array.isArray(llista) ? llista.map(x => x.codi) : null
}

/** Hook de conveniència: els codis d'UNA enumeració + si ha fallat. */
export function useEnumeracio(clau) {
  const { voc, error, reintenta } = useEstatVocabulari()
  return { codis: codisDe(voc, clau), error, reintenta }
}
