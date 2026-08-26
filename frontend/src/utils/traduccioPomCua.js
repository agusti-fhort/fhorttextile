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
 * 🚨 QUANTS IDS CABEN EN UNA PETICIÓ. La porta (`GET /api/v1/translate/pom/`) en refusa més de
 * 300 amb un 400, i aquí no se n'hi enviaven mai menys dels que hi hagués: `buida()` agafava
 * el `Set` sencer d'un idioma i el passava en UNA sola crida.
 *
 * A `/poms` això vol dir el CATÀLEG SENCER —la pantalla el carrega tot des que `totesLesPagines`
 * va substituir un `page_size: 1000` que mentia—, i amb un catàleg de més de 300 la petició
 * naixia morta: 400, `catch` mut, i la ⓘ que no sortia mai sense que ningú veiés cap error.
 *
 * **200 i no 300 a posta.** El client no ha de saber el número exacte del servidor, només
 * quedar-hi per sota amb marge: si algun dia el sostre baixa, això segueix passant. I la URL
 * es queda curta, que és gratis.
 */
const MAX_PER_PETICIO = 200

/** `[1..450]` → `[[1..200], [201..400], [401..450]]`. */
function trosseja(ids, mida = MAX_PER_PETICIO) {
  const lots = []
  for (let i = 0; i < ids.length; i += mida) lots.push(ids.slice(i, i + mida))
  return lots
}

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
      // EN LOTS, i SEQÜENCIALS. Seqüencials i no en paral·lel perquè cada petició ja dispara
      // diverses crides al proveïdor al servidor (50 textos per crida): obrir-ne dues alhora
      // multiplicaria la ràfega contra un tercer sense guanyar gaire res a la pantalla, que
      // pinta la ⓘ a mesura que arriba.
      for (const lot of trosseja(ids)) {
        try {
          for (const it of (await demana(lot, lang)) || []) {
            cache.set(clau(lang, it.pom_id), it.text || '')
            novetat = true
          }
        } catch (e) {
          // ⚠️ UN 4xx NO ES REINTENTA. Es desmarcaven SEMPRE els ids, i per a un tall de xarxa
          // és el correcte —la ⓘ no pot quedar muda per sempre per un segon dolent—, però per
          // a un refús de la porta és una repetició garantida a cada entrada a la pantalla,
          // sempre amb el mateix resultat i sempre en silenci. Un lot que el servidor rebutja
          // es dona per preguntat: la ⓘ callarà, que és el que la casa ja fa amb un POM sense
          // traducció, en comptes de tornar-hi eternament.
          const codi = e?.response?.status
          if (!(codi >= 400 && codi < 500)) {
            for (const id of lot) demanats.delete(clau(lang, id))
          }
        }
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
