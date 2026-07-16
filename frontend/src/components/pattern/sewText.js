import { formatLen, formatLenNum } from '../../utils/format'

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

/** El símbol de la costura: dos trams encadenats. És una ICONA, mai un caràcter desat a la BD. */
export const CADENA = '⛓'

/**
 * El SEMÀFOR d'un veredicte (QA-TALLER H · T1): color i icona a partir del `grau` del servidor.
 *
 * El grau (`ok`/`warn`/`err`) el calcula el backend segons el tipus i el desajust; aquí només
 * es tradueix a tokens. **Res tenyeix la xifra**: el color va a la vora i a la icona, i el número
 * es queda negre —tolerància no és error, i un número vermell obliga a endevinar si ho és perquè
 * està fora o perquè importa.
 *
 * El frunzit (`grau === 'na'`) no té gradient —el diferencial és intencional—: cau a la lectura
 * binària del motor (`casa`), com sempre. I una costura sense grau (dades velles, o un estat que
 * encara no l'ha calculat) també, perquè el panell no ha de petar per un camp que falta.
 */
export function grauVisual(estat) {
  const e = estat || {}
  const grau = e.grau && e.grau !== 'na' ? e.grau : (e.casa ? 'ok' : 'err')
  const taula = {
    ok: { color: 'var(--ok)', bg: 'var(--ok-bg)', icona: 'ti-check' },
    warn: { color: 'var(--warn)', bg: 'var(--warn-bg)', icona: 'ti-alert-triangle' },
    err: { color: 'var(--err)', bg: 'var(--err-bg)', icona: 'ti-alert-triangle' },
  }
  return taula[grau] || taula.err
}

/**
 * L'ARITMÈTICA d'un costat, sencera (W4b/T2).
 *
 * Sense pinces és una xifra i prou. Amb pinces, és una OPERACIÓ —«32,1 − 2,3 (Pinça 1) =
 * 29,8»— i s'ensenya sencera, no el resultat. Un costat que de sobte mesura menys del que fa
 * la vora ha de poder dir per què; si no, el patronista només té dues sortides: creure-s'ho o
 * no fer-ne cas. Cap de les dues és bona.
 */
export function textAritmetica(estat, costat, unit = 'CM') {
  const e = estat || {}
  const net = costat === 'a' ? e.longitud_a_cm : e.longitud_b_cm
  const brut = costat === 'a' ? e.brut_a_cm : e.brut_b_cm
  const descomptes = (costat === 'a' ? e.descomptes_a : e.descomptes_b) || []

  if (!descomptes.length) return formatLen(net, unit)

  const restes = descomptes
    .map(d => `− ${formatLenNum(d.cm, unit)} (${d.nom})`)
    .join(' ')
  return `${formatLenNum(brut, unit)} ${restes} = ${formatLen(net, unit)}`
}

/** Casa o no casa, i per quant. Les xifres, no l'adjectiu — i amb el descompte a la vista. */
export function textEstat(t, estat, unit = 'CM') {
  const e = estat || {}
  const a = textAritmetica(e, 'a', unit)
  const b = textAritmetica(e, 'b', unit)
  return e.casa
    ? t('pattern.taller.sew_ok', { a, b })
    : t('pattern.taller.sew_off', { desv: formatLen(e.desviament_cm, unit), a, b })
}

/**
 * Un avís de cobertura de la vora (W1): dos trams que es trepitgen, o més centímetres
 * cosits dels que la vora té. Una costura pot CASAR i la vora estar malament igualment.
 */
export function textCobertura(t, avis, unit = 'CM') {
  return avis.mena === 'solapament'
    ? t('pattern.taller.cov_overlap', {
        cm: formatLen(avis.solapament_cm, unit), peca: avis.peca, vora: avis.vora,
        vora_cm: formatLen(avis.longitud_vora_cm, unit),
      })
    : t('pattern.taller.cov_excess', {
        cm: formatLen(avis.exces_cm, unit), suma: formatLen(avis.suma_cosida_cm, unit),
        peca: avis.peca, vora: avis.vora,
        vora_cm: formatLen(avis.longitud_vora_cm, unit),
      })
}

/**
 * EL NOM D'UNA COSTURA (W4b/T6).
 *
 * Per defecte es GENERA dels dos trams que uneix: «Lateral davanter ⛓ Lateral esquena ·
 * Frunzit 2,0 cm». No es desa: es composa cada cop, amb els noms que els trams tenen ARA. Un
 * nom desat seria un string congelat, i el dia que algú reanomenés un tram la costura
 * continuaria dient el nom vell — que és la manera d'acabar amb dues veritats sobre la
 * mateixa costura.
 *
 * Però si algú l'ha BATEJADA a mà, el bateig mana i es conserva: un nom que una persona ha
 * triat no el pot trepitjar un generador.
 *
 * La condició (tipus i diferencial) només s'hi diu si vol dir alguna cosa: un casat pla és el
 * cas normal i no cal anunciar-lo. Un frunzit de 2 cm, sí.
 */
export function nomCostura(t, sew, tramsPerId, unit = 'CM') {
  if (sew.nom) return sew.nom

  const costat = (ids) => {
    const noms = (ids || []).map(id => tramsPerId.get(id)?.nom).filter(Boolean)
    if (!noms.length) return t('pattern.taller.segment_unnamed')
    // «A +2»: un costat pot ser diversos trams (una màniga contra davanter + esquena), i
    // enumerar-los tots faria un nom impossible de llegir.
    return noms.length === 1 ? noms[0] : `${noms[0]} +${noms.length - 1}`
  }

  const base = `${costat(sew.segments_a)} ${CADENA} ${costat(sew.segments_b)}`
  const condicio = textCondicio(t, sew, unit)
  return condicio ? `${base} · ${condicio}` : base
}

/** La condició de muntatge: buida si és un casat pla (el cas normal no s'anuncia). */
export function textCondicio(t, sew, unit = 'CM') {
  const dif = Number(sew.diferencial_cm) || 0
  if (sew.tipus === 'casat' && !dif) return ''
  const tipus = t(`pattern.sew_type.${sew.tipus}`)
  return dif ? `${tipus} ${formatLen(dif, unit)}` : tipus
}
