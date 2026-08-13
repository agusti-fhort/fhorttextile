// LA FONT DE LA ⓘ AL FRONT — el nom d'un POM en la llengua de qui llegeix.
//
// UN SOL PUNT DE CRIDA per a tot el sistema. La ⓘ es pinta a la taula de Mesures, a la
// Graduació, a l'Escalat/Comprovació/Repàs, al catàleg de POMs i al navegador de POMs; si cada
// pantalla se'n fes la seva, el mateix nom es demanaria cinc vegades i cadascuna decidiria pel
// seu compte quan tornar-hi. Aquí hi ha l'accés a dades i el hook; la mecànica (cua, lot,
// memòria) viu a `traduccioPomCua.js`, i el mecanisme visual és `InfoTraduccio`, exportat des
// d'`EditableTable` i compartit per totes.
//
// **CACHE DE SESSIÓ EN MEMÒRIA, MAI `localStorage`** (llei de la casa). La cache de veritat és
// la del servidor; aquesta només evita repetir la petició en canviar de pantalla, i es mor amb
// la pestanya — que és exactament el que ha de fer una còpia derivada.
//
// **EL SILENCI ÉS UNA RESPOSTA VÀLIDA.** Un POM sense traducció torna `''` i la ⓘ no es pinta.
// Cap error, cap toast, cap estat de càrrega: la ⓘ que encara no ha arribat es veu igual que la
// que no existeix, i quan arriba, apareix. Una traducció no pot fer esperar una taula de mesures.

import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { traduccions as apiTraduccions } from '../api/endpoints'
import { baseLang, creaCua } from './traduccioPomCua'

export { baseLang }

const cua = creaCua(async (ids, lang) => {
  const { data } = await apiTraduccions.poms(ids, lang)
  return data?.items || []
})

/** Buida la memòria (proves; i el dia que es canviï d'idioma sense recarregar). */
export function oblidaTraduccions() { cua.oblida() }

/** El text memoritzat, o `''`. Síncron: qui pinta no espera ningú. */
export function traduccioMemoritzada(pomId, lang) { return cua.memoritzada(pomId, lang) }

/** Posa uns POMs a la cua del proper lot, sense hook (escalfaments, precàrregues). */
export function demanaTraduccions(pomIds, lang) { cua.demana(pomIds, lang) }

/**
 * EL HOOK ÚNIC. Rep els POMs VISIBLES d'una pantalla i torna `traduccioDe(pomId)`.
 *
 * Torna una FUNCIÓ i no un objecte a posta: les files es pinten dins d'un `map` i cada cel·la
 * pregunta pel seu id; construir un objecte nou a cada render només serviria per canviar la
 * identitat de la referència i fer treballar els `memo` de sota.
 */
export function useTraduccioPoms(pomIds, langOpcional) {
  const { i18n } = useTranslation()
  const lang = baseLang(langOpcional || i18n?.language)
  // La llista d'ids arriba nova a cada render (surt d'un `map`); el que ha de disparar la
  // petició és el CONTINGUT, no la identitat de l'array.
  const signatura = (pomIds || []).filter(x => x != null && x !== '').join(',')
  // `versio` no és un comptador decoratiu: entra a les dependències de la funció que es torna
  // perquè aquesta canviï d'identitat quan arriben textos nous. Sense això, un consumidor
  // memoritzat es quedaria amb la versió muda i la ⓘ no sortiria fins al proper render seu.
  const [versio, setVersio] = useState(0)

  useEffect(() => {
    if (!lang) return undefined
    const baixa = cua.subscriu(() => setVersio(n => n + 1))
    cua.demana(signatura ? signatura.split(',') : [], lang)
    return baixa
  }, [signatura, lang])

  // El linter llegeix `versio` com a dependència sobrera perquè no apareix al cos: hi és a
  // posta (v. a dalt), la lectura va a una cache de mòdul que React no vigila.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useCallback((pomId) => cua.memoritzada(pomId, lang), [lang, versio])
}
