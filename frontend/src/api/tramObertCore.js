/**
 * F3.2 · EL TRAM OBERT — LA DECISIÓ, sense navegador (S-18).
 *
 * Mòdul pur (cap import) → provable amb `node --test`. El cablatge (endpoints, `setInterval`,
 * `visibilitychange`, React) viu a `tramObert.js` i s'injecta aquí, com ja fan `sessioCore.js`
 * i `tascaActivaCore.js`.
 *
 * PER QUÈ EXISTEIX. Dos components preguntaven el mateix cada minut i cadascú s'ho muntava pel
 * seu compte: `GuardTascaOblidada` (vigila la INACTIVITAT) i `SessioActiva` (mostra la
 * PRESÈNCIA). Quatre peticions per minut per saber una sola cosa, i amb dos rellotges
 * desfasats: el guard podia haver pausat una tasca i la píndola seguir dient que corria fins a
 * un minut després.
 *
 * ⚠️ **AIXÒ NO DECIDEIX QUÈ FA NINGÚ.** Emet el que hi ha —quin tram tinc obert i quina fila de
 * tasca hi correspon— i cada consumidor hi aplica la seva política. Convergir la LECTURA treu
 * duplicació; convergir la POLÍTICA perdria casos, perquè davant del mateix fet els dos
 * consumidors han de fer coses diferents. Per això els modes de fallada són estats explícits i
 * no un `null` per a tot: un `null` únic obligaria tothom a la mateixa reacció, que és
 * exactament el cas que es perdria.
 *
 *   · `CAP`         — no tinc cap tram obert. Tots dos netegen.
 *   · `OBERT`       — tram obert + la seva fila de tasca, EN QUALSEVOL ESTAT. Qui filtri per
 *                     `InProgress` és el consumidor: el guard perquè un tram zombi damunt d'una
 *                     tasca pausada li feia demanar una transició il·legal (282 POSTs en
 *                     minuts), i `estatSessio` perquè una píndola que menteix és pitjor que cap
 *                     píndola.
 *   · `ERR_LLISTA`  — la llista ha fallat. **El guard ho IGNORA i es manté armat**: una caiguda
 *                     de xarxa no és prova que la tasca s'hagi tancat, i desarmar-se cada cop
 *                     que un GET falla és desarmar-se justament quan el guard hauria de comptar.
 *                     `SessioActiva` sí que neteja: sense dada confirmada no ensenya res.
 *   · `ERR_TASCA`   — tinc el tram però no la seva tasca. Tots dos netegen (era el que ja feien:
 *                     el guard no arma sense saber l'estat, i la píndola no pinta un nom que no
 *                     té).
 *
 * L'ORDRE DE LES RESPOSTES MANA, NO EL DE LES PETICIONS. `refresca()` es crida just després
 * d'una transició i pot avançar una consulta periòdica que ja anava en vol; si aquella arribés
 * després, tornaria a emetre el món d'ABANS de la transició — i el guard es rearmaria damunt del
 * tram que acaba de tancar. Cada consulta porta número i només emet si cap de posterior no ho ha
 * fet ja.
 */

export const CAP = 'cap'
export const OBERT = 'obert'
export const ERR_LLISTA = 'err_llista'
export const ERR_TASCA = 'err_tasca'

/** El tram obert d'una resposta de `timers.list` (paginada o no). `null` si no n'hi ha cap. */
export function tramObertDe(resposta) {
  const files = resposta?.data?.results ?? resposta?.data ?? []
  return (Array.isArray(files) ? files : []).find(f => f.fi == null) ?? null
}

/**
 * La font compartida. `llistaTrams()` i `llegeixTasca(id)` s'injecten; tota la resta és decisió.
 * `arrenca`/`atura` reben el callback de sondeig i tornen la baixa: qui sap de `setInterval` i
 * de `visibilitychange` és el cablatge, no això.
 */
export function creaFontTramObert({ llistaTrams, llegeixTasca, arrenca, atura }) {
  const subscriptors = new Set()
  let viu = false
  let ultim = null      // últim resultat emès, per no fer esperar un subscriptor nou
  let seq = 0           // número de consulta
  let emesa = 0         // número de l'última consulta que ha emès

  function emet(resultat, meu) {
    if (meu < emesa) return          // resposta endarrerida: ja n'hi ha una de més nova
    emesa = meu
    ultim = resultat
    subscriptors.forEach(fn => fn(resultat))
  }

  /** Una lectura. SEMPRE resol: els errors són estats emesos, no excepcions propagades. */
  function consulta() {
    const meu = ++seq
    return Promise.resolve()
      .then(llistaTrams)
      .then(resposta => {
        const obert = tramObertDe(resposta)
        if (!obert) return emet({ estat: CAP }, meu)
        return Promise.resolve()
          .then(() => llegeixTasca(obert.model_task))
          .then(r => emet({ estat: OBERT, tram: obert, tasca: r?.data ?? null }, meu))
          .catch(() => emet({ estat: ERR_TASCA, tram: obert }, meu))
      })
      .catch(() => emet({ estat: ERR_LLISTA }, meu))
  }

  return {
    /** Força una lectura ara (després d'una transició, per no ensenyar el món d'abans). */
    refresca: consulta,

    get ultim() { return ultim },

    /**
     * Escolta el tram obert. Retorna la baixa. El sondeig viu mentre hi hagi algú escoltant i
     * no un instant més: cap `setInterval` orfe darrere d'un component desmuntat.
     */
    subscriu(fn) {
      subscriptors.add(fn)
      if (ultim) fn(ultim)          // el que arriba tard no espera 60 s per saber què corre
      if (!viu) { viu = true; arrenca(consulta); consulta() }
      return () => {
        subscriptors.delete(fn)
        if (subscriptors.size) return
        viu = false
        atura()
        // L'últim resultat s'oblida: si algú es torna a subscriure d'aquí a una estona, val més
        // no saber res que servir-li una foto vella com si fos d'ara.
        ultim = null
      }
    },
  }
}
