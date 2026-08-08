// LA FONT dels TRES EIXOS de grading: targets, construccions i fits.
//
// TERCERA GERMANA de `diccionariMesuresFont.js` (vocabulari d'IDENTITAT d'una mesura) i de
// `vocabulariDominiFont.js` (enumeracions de CICLE). Mateixa forma, mateixes garanties, mateix
// idioma. Viu aquí i no allà per una raó de FONS, no d'ordre: aquests tres no són `choices` d'un
// model —són TAULES (`pom.Target`, `pom.ConstructionType`, `pom.FitType`), amb files, ordre propi
// (`display_order`) i noms en tres idiomes—, i ja tenien endpoint des de S2. El que faltava no
// era publicar-los: era que algú els llegís.
//
// PER QUÈ EXISTEIX. `components/grading/gradingAxes.js` en portava una CÒPIA sencera —13 targets,
// 4 construccions, 10 fits, amb els noms en tres idiomes escrits a mà—, i sis pantalles la
// importaven. Era la còpia més grossa de tot el projecte i no era ni al cens de la Fase 1. La
// còpia i la taula ja divergien pel cantó que compta: `TARGETS` porta un rename de vocabulari de
// sector (P0b: BOY→KID_BOY, TODDLER_*→BABY_*) que va caldre fer a MÀ als dos llocs, i el dia que
// se n'afegeixi un de nou a la taula no apareixerà a cap pantalla fins que algú recordi aquest
// fitxer.
//
// `nom_cat` → `nom_ca`. El backend diu `nom_cat` (`Target`, `ConstructionType`, `FitType`) i la
// casa diu `nom_ca` (`MeasurementLayer`, `POMGlobal`, i la còpia que això substitueix). La
// traducció es fa AQUÍ, un sol cop i en un sol lloc, perquè cap pantalla hagi de saber que hi ha
// dos noms per a la mateixa cosa. `nomLocal()` de `gradingAxes` segueix funcionant igual.
//
// ⚠️ CAP LLISTA DE RESERVA, per la mateixa raó que a les germanes: si els endpoints no
// contesten, les llistes són `null` i qui les consumeix no ofereix eixos. Un fallback aquí seria
// replantar la còpia que aquest mòdul existeix per matar.

import { useCallback, useEffect, useState } from 'react'
import { targets as targetsApi, constructionTypes, fitTypes } from '../../api/endpoints'

let cache = null
let enVol = null

/** `{codi, nom_cat, nom_es, …}` del backend → la forma que la casa fa servir. */
function normalitza(fila) {
  return {
    ...fila,
    nom_en: fila.nom_en || fila.codi,
    nom_ca: fila.nom_cat || fila.nom_ca || fila.nom_en || fila.codi,
    nom_es: fila.nom_es || fila.nom_en || fila.codi,
  }
}

const files = (r) => (r.data?.results ?? r.data ?? []).map(normalitza)

/** Buida la memòria (proves; i el dia que el catàleg d'eixos sigui editable des de la UI). */
export function oblidaEixos() { cache = null; enVol = null }

export function carregaEixos() {
  if (cache) return Promise.resolve(cache)
  if (enVol) return enVol
  // Les tres peticions van EN PARAL·LEL i es resolen com una de sola: són tres taules del mateix
  // catàleg i cap pantalla en fa servir una d'aïllada (la cascada les vol totes tres alhora).
  enVol = Promise.all([
    targetsApi.list({ page_size: 200 }),
    constructionTypes.list({ page_size: 200 }),
    fitTypes.list({ page_size: 200 }),
  ])
    .then(([t, c, f]) => {
      cache = { targets: files(t), constructions: files(c), fits: files(f) }
      enVol = null
      return cache
    })
    .catch(e => { enVol = null; throw e })
  return enVol
}

/**
 * L'ESTAT dels tres eixos: `{targets, constructions, fits, error, reintenta}`.
 *
 * Les tres llistes són `null` —i no `[]`— mentre no se sap, pel mateix motiu que `codisDe`:
 * `[]` afirmaria «aquest catàleg és buit» i això no ho podem dir. `error` distingeix «encara no
 * ha arribat» de «no arribarà».
 */
export function useEixos() {
  const [estat, setEstat] = useState(() => ({ eixos: cache, error: false }))
  const [intent, setIntent] = useState(0)
  useEffect(() => {
    let viu = true
    carregaEixos()
      .then(e => { if (viu) setEstat({ eixos: e, error: false }) })
      .catch(() => { if (viu) setEstat({ eixos: null, error: true }) })
    return () => { viu = false }
  }, [intent])
  const reintenta = useCallback(() => {
    oblidaEixos()
    setEstat({ eixos: null, error: false })
    setIntent(n => n + 1)
  }, [])
  return {
    targets: estat.eixos?.targets ?? null,
    constructions: estat.eixos?.constructions ?? null,
    fits: estat.eixos?.fits ?? null,
    error: estat.error,
    reintenta,
  }
}
