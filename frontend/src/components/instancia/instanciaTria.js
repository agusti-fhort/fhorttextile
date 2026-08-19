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
// censat com a vora oberta. Aquí la tria és PER EIX: cada grup en té una d'encesa com a molt, i
// prémer-ne una no toca els altres eixos.

// L'extensió `.js` hi és a posta: aquest mòdul el carrega el runner de Node (que no resol
// imports sense extensió) a més de Vite. És la mateixa raó per la qual `diccionariMesures.js`
// no importa res — les regles pures han de poder córrer fora del navegador.
import { composaInstancia, eixDe, tramsInstancia } from '../../utils/diccionariMesures.js'

/** `{eix: slug}` dels trams d'un valor — el que diu quina píndola va encesa a cada grup. */
export function tramsPerEix(dicc, valor) {
  const out = {}
  for (const s of tramsInstancia(dicc, valor)) {
    const e = eixDe(dicc, s)
    if (e) out[e] = s
  }
  return out
}

/**
 * Prémer una píndola: encén el seu tram al SEU eix i deixa els altres eixos com estaven; si ja
 * hi era, l'apaga. Torna el slug d'instància sencer (`''` = la instància única).
 */
export function triaTram(dicc, valor, slug) {
  const eix = eixDe(dicc, slug)
  // Un slug que el diccionari no coneix no pot dir de quin eix és, i per tant no pot dir QUÈ
  // rellevaria: es deixa el valor com estava en comptes de compondre una clau inventada.
  if (!eix) return valor || ''
  const actuals = tramsPerEix(dicc, valor)
  if (actuals[eix] === slug) delete actuals[eix]   // la píndola encesa s'apaga
  else actuals[eix] = slug
  return composaInstancia(dicc, Object.values(actuals))
}

/** La tria del modal `＋`: un tram (o cap) per eix, compostos per la porta única. */
export function aplicaCombinacio(dicc, perEix) {
  return composaInstancia(dicc, Object.values(perEix || {}).filter(Boolean))
}
