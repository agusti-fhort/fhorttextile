// LA TRIA D'INSTÀNCIA A LES PÍNDOLES — la regla, fora del component.
//
// Les píndoles del pas 2 són GRUPS PER EIX (posició · estat) i cada grup en té una d'encesa com
// a molt. El que aquest mòdul decideix és què passa en prémer-ne una: quin slug en surt. I la
// composició no la fa ell —la fa `composaInstancia`, la porta única de la casa— perquè l'ordre
// dels trams és el dels EIXOS del diccionari i no el dels clics: `left-relaxed` i `relaxed-left`
// serien dues claus per a la mateixa germana, i la clau única de la BD és
// `(model, pom, capa, instancia)`.
//
// El `<select>` que P2 va deixar només sabia fer una cosa: substituir. Amb ell, «Bottom» i
// després «Extended» donava `extended` —la posició es perdia— i per això `left-relaxed` va quedar
// censat com a vora oberta. Aquí la tria és PER BLOC D'EXCLUSIÓ: cada bloc en té una d'encesa
// com a molt, i prémer-ne una no toca els altres blocs.
//
// ⚠️ EL BLOC NO ÉS L'EIX des del 22-23/08: la POSICIÓ en té dos —CARA (front · back) i LATERAL
// (left · right)— i `back`+`left` és una germana legítima. Qui declara quin slug és de quin bloc
// és el diccionari (`subeix`), i la regla de si dos poden conviure és `xoquen`.

// L'extensió `.js` hi és a posta: aquest mòdul el carrega el runner de Node (que no resol
// imports sense extensió) a més de Vite. És la mateixa raó per la qual `diccionariMesures.js`
// no importa res — les regles pures han de poder córrer fora del navegador.
import {
  clauExclusio, composaInstancia, tramsInstancia, xoquen,
} from '../../utils/diccionariMesures.js'

/**
 * `{clau: slug}` dels trams d'un valor — el que diu quina píndola va encesa a cada grup.
 *
 * ⚠️ LA CLAU ÉS LA D'EXCLUSIÓ, NO L'EIX (22-23/08). Des que la posició en té dos —CARA i
 * LATERAL—, `back` i `left` són dues píndoles enceses del MATEIX eix i han de poder conviure:
 * amb la clau per eix, la segona apagava la primera i «l'esquena esquerra» era impossible de
 * dir. Les posicions sense sub-eix (`top`, `cf`…) conserven la clau de l'eix i, per tant, el
 * comportament de sempre.
 */
export function tramsPerEix(dicc, valor) {
  const out = {}
  for (const s of tramsInstancia(dicc, valor)) {
    const c = clauExclusio(dicc, s)
    if (c) out[c] = s
  }
  return out
}

/**
 * Prémer una píndola: encén el seu tram i APAGA les que no hi poden conviure (`xoquen`), deixant
 * la resta com estava; si ja hi era, l'apaga. Torna el slug sencer (`''` = la instància única).
 *
 * Encendre `left` treu `right` però NO `back`; encendre `top` —que no té sub-eix— treu tota la
 * resta de la posició. La regla és la del diccionari, no una llista de casos.
 */
export function triaTram(dicc, valor, slug) {
  const clau = clauExclusio(dicc, slug)
  // Un slug que el diccionari no coneix no pot dir de quin eix és, i per tant no pot dir QUÈ
  // rellevaria: es deixa el valor com estava en comptes de compondre una clau inventada.
  if (!clau) return valor || ''
  const actuals = tramsPerEix(dicc, valor)
  if (actuals[clau] === slug) {
    delete actuals[clau]                           // la píndola encesa s'apaga
  } else {
    for (const [c, s] of Object.entries(actuals)) {
      if (xoquen(dicc, slug, s)) delete actuals[c]  // les incompatibles marxen
    }
    actuals[clau] = slug
  }
  return composaInstancia(dicc, Object.values(actuals))
}

/** La tria del modal `＋`: un tram (o cap) per bloc d'exclusió, compostos per la porta única. */
export function aplicaCombinacio(dicc, perEix) {
  return composaInstancia(dicc, Object.values(perEix || {}).filter(Boolean))
}

/**
 * La tria del modal quan s'hi prem una opció: la mateixa llei que a la fila (`triaTram`), sobre
 * el mapa de la tria en comptes del slug. Viu aquí i no al component perquè les dues portes
 * han de dir el mateix — el modal era l'únic lloc que podia creuar eixos, i creuar-los ara vol
 * dir respectar els sub-eixos.
 */
export function triaAlModal(dicc, perEix, slug) {
  const clau = clauExclusio(dicc, slug)
  if (!clau) return perEix || {}
  const out = { ...(perEix || {}) }
  if (out[clau] === slug) {
    delete out[clau]
    return out
  }
  for (const [c, s] of Object.entries(out)) {
    if (xoquen(dicc, slug, s)) delete out[c]
  }
  out[clau] = slug
  return out
}
