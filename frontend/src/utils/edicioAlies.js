// L'EDICIÓ EN LÍNIA D'UN ÀLIES DE LA BIBLIOTECA DE NOMENCLATURA.
//
// La regla viu FORA del component —com `filtrePoms.js` i `instanciaTria.js`— perquè és el que
// la fa provable amb `node --test` sense React, i perquè el que decideix QUÈ s'envia al servidor
// no ha de dependre de com està pintada la fila.
//
// 🔒 EL `client_code` NO HI ÉS, I NO HI POT SER. És la identitat de l'àlies: el matcher hi busca
// a les importacions i la unicitat `(customer, client_code)` el protegeix. Canviar-lo no és
// editar: és esborrar-ne un i crear-ne un altre. El servidor també ho defensa (una pantalla no
// és una barana), i per això aquí no és una omissió sinó una llista tancada.

export const CAMPS_EDITABLES = ['description_en', 'description_local', 'language', 'pom']

// El `pom` viatja com a id i pot ser `null` (àlies pendent de mapar); els altres tres, com a
// text. Es normalitzen a la forma que el servidor espera i no a la que la fila ensenya.
const _text = (v) => (v == null ? '' : String(v))
const _pom = (v) => (v == null || v === '' ? null : Number(v))

/** L'esborrany inicial d'una fila: només els camps que l'edició toca. */
export function esborranyDe(alias) {
  return {
    description_en: _text(alias?.description_en),
    description_local: _text(alias?.description_local),
    language: _text(alias?.language),
    pom: _pom(alias?.pom),
  }
}

/** Els camps que han canviat, normalitzats. Buit = res a desar. */
export function canvisDe(esborrany, alias) {
  const original = esborranyDe(alias)
  const nou = esborranyDe(esborrany)
  const out = {}
  for (const c of CAMPS_EDITABLES) {
    if (nou[c] !== original[c]) out[c] = nou[c]
  }
  return out
}

export function hiHaCanvis(esborrany, alias) {
  return Object.keys(canvisDe(esborrany, alias)).length > 0
}

/**
 * El cos del PATCH: NOMÉS el que ha canviat.
 *
 * Enviar la fila sencera funcionaria, però un PATCH mínim diu al servidor —i a qui llegeixi el
 * log— què s'ha volgut tocar de debò, i no reescriu amb el mateix valor camps que un altre
 * podria haver canviat mentrestant.
 */
export function payloadDe(esborrany, alias) {
  return canvisDe(esborrany, alias)
}

/**
 * El text d'error que ha de sortir A LA FILA.
 *
 * DRF respon `{camp: [missatge]}` per a les validacions i `{detail: missatge}` per als permisos.
 * Es tria el PRIMER missatge útil perquè el que la fila té és una línia: un objecte serialitzat
 * amb claus i claudàtors hi cabria però no es llegiria. Si no se'n troba cap, es cau al text
 * genèric que la pantalla ja té traduït.
 */
export function errorDeResposta(err, generic) {
  const data = err?.response?.data
  if (typeof data === 'string' && data.trim()) return data.trim()
  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string' && data.detail.trim()) return data.detail.trim()
    for (const clau of Object.keys(data)) {
      const v = data[clau]
      const text = Array.isArray(v) ? v.find(x => typeof x === 'string' && x.trim()) : v
      if (typeof text === 'string' && text.trim()) return text.trim()
    }
  }
  return generic
}
