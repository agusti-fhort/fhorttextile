// LA MECÀNICA de la ⓘ: la cua, el lot i la memòria. Pura i sense dependències.
//
// Separada de `traduccioPomFont.js` pel mateix motiu que `diccionariMesures.js` ho està de la
// seva font: el que aquí s'ha de poder provar amb `node --test` és el COMPORTAMENT —que N noms
// siguin UNA petició, que el segon cop no en surti cap, que un tall de xarxa no deixi la ⓘ muda
// per sempre— i el runner no resol ni React ni axios. Allà hi ha el hook; aquí, la regla.
//
//     node --test frontend/src/utils/traduccioPomCua.test.js

/** `ca-ES` → `ca`. Mateixa reducció que fa el servidor, perquè la clau de cache coincideixi. */
export function baseLang(v) {
  return (v || '').trim().toLowerCase().replace('_', '-').split('-')[0]
}

const clau = (lang, id) => `${lang}|${id}`

/**
 * @param demana  `(ids, lang) => Promise<[{pom_id, text}]>` — l'accés real a dades.
 * @param programa `(fn) => void` — quan surt el lot. Per defecte, el proper tic.
 *
 * LA FINESTRA ÉS UN TIC, NO UN MICROTASK. Dins d'un mateix render de React hi han de cabre
 * TOTES les cel·les d'una taula; les promeses ja resoltes dels `useEffect` no esperen prou i el
 * lot sortiria partit en dos.
 */
export function creaCua(demana, programa = (fn) => setTimeout(fn, 0)) {
  let cache = new Map()        // `${lang}|${id}` → text (`''` = preguntat i sense traducció)
  const cua = new Map()        // lang → Set(ids) pendents
  const demanats = new Set()   // ja preguntats: no tornen a la cua
  const oients = new Set()
  let programat = false

  function avisa() {
    // Còpia de la llista abans de recórrer-la: un oient que es desmunti mentre s'avisa no ha de
    // moure el terra sota els altres.
    for (const fn of [...oients]) { try { fn() } catch { /* un render caigut no atura la resta */ } }
  }

  async function buida() {
    programat = false
    const feina = [...cua.entries()].map(([lang, ids]) => [lang, [...ids]])
    cua.clear()
    let novetat = false
    for (const [lang, ids] of feina) {
      if (!ids.length) continue
      try {
        for (const it of (await demana(ids, lang)) || []) {
          cache.set(clau(lang, it.pom_id), it.text || '')
          novetat = true
        }
      } catch {
        // NO es memoritza res i es desmarquen els ids. Desar-los com a «sense traducció» faria
        // que la ⓘ callés per sempre per un tall de xarxa d'un segon.
        for (const id of ids) demanats.delete(clau(lang, id))
      }
    }
    if (novetat) avisa()
  }

  return {
    /** Posa els ids a la cua del proper lot. Els ja preguntats no hi tornen. */
    demana(pomIds, lang) {
      const l = baseLang(lang)
      if (!l) return
      for (const id of pomIds || []) {
        if (id == null || id === '') continue
        const k = clau(l, id)
        if (demanats.has(k)) continue
        demanats.add(k)
        if (!cua.has(l)) cua.set(l, new Set())
        cua.get(l).add(id)
      }
      if (cua.size && !programat) { programat = true; programa(buida) }
    },
    /** El text memoritzat, o `''`. Síncron: qui pinta no espera ningú. */
    memoritzada(pomId, lang) {
      return cache.get(clau(baseLang(lang), pomId)) || ''
    },
    /** Avisa quan arriben textos nous. Torna la funció de baixa. */
    subscriu(fn) {
      oients.add(fn)
      return () => oients.delete(fn)
    },
    /** Buida la memòria (proves; i el dia que es canviï d'idioma sense recarregar). */
    oblida() {
      cache = new Map()
      cua.clear()
      demanats.clear()
      programat = false
    },
  }
}
