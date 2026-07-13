/**
 * El que una costura DIU, en text — un sol lloc.
 *
 * El backend escriu els seus missatges en català pla (`estat.missatge`, els avisos de
 * cobertura): no són claus i18n i el gate demana ca/en/es. Així que aquí es reconstrueixen
 * a partir de les XIFRES estructurades que el servidor sí que dona, i la frase del servidor
 * es conserva com a `title` — hi ha matís que val la pena poder llegir sencer.
 *
 * Viu a part perquè el MATEIX text l'han de dir dos llocs: l'avís immediat en declarar una
 * costura, i la fitxa de la costura a RELACIONS. Si cadascú se'l fabriqués, acabarien dient
 * coses diferents de la mateixa costura.
 */

/** Casa o no casa, i per quant. Les xifres, no l'adjectiu. */
export function textEstat(t, estat) {
  const e = estat || {}
  return e.casa
    ? t('pattern.taller.sew_ok', { a: e.longitud_a_cm, b: e.longitud_b_cm })
    : t('pattern.taller.sew_off', {
        desv: e.desviament_cm, a: e.longitud_a_cm, b: e.longitud_b_cm,
      })
}

/**
 * Un avís de cobertura de la vora (W1): dos trams que es trepitgen, o més centímetres
 * cosits dels que la vora té. Una costura pot CASAR i la vora estar malament igualment.
 */
export function textCobertura(t, avis) {
  return avis.mena === 'solapament'
    ? t('pattern.taller.cov_overlap', {
        cm: avis.solapament_cm, peca: avis.peca, vora: avis.vora,
        vora_cm: avis.longitud_vora_cm,
      })
    : t('pattern.taller.cov_excess', {
        cm: avis.exces_cm, suma: avis.suma_cosida_cm, peca: avis.peca,
        vora: avis.vora, vora_cm: avis.longitud_vora_cm,
      })
}
