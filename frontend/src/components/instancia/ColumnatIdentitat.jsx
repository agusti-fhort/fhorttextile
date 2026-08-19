// EL COLUMNAT D'IDENTITAT — la capa i les instàncies d'una mesura, amb les píndoles de la casa.
//
// L'ORDRE DE LES COLUMNES ÉS L'ORDRE DE LA IDENTITAT: CAPA · POSICIÓ · ESTAT · MÉS. La capa va
// primera perquè és el primer eix —diu de quina MATÈRIA parla la mesura (exterior, folre)— i les
// instàncies la qualifiquen a dins. Sense la columna de capa, una fila «lining» de la fitxa
// s'aparellava a l'exterior i queia damunt de la germana que ja hi era: el cas real que la va
// portar (Agus, 16/08).
//
// El patró és el de la Definició manual (`EditableTable`, columnat INSTÀNCIA): un GRUP DE
// PÍNDOLES PER EIX del diccionari —avui posició i estat— i un `＋` per a les combinacions. Aquí
// se n'extreu la PELL i la tria, no la semàntica: a la Definició manual prémer una píndola
// PARTEIX la mesura (neix una germana al model, i tornar-hi la desfà); al pas 2 de l'import
// només diu de QUINA mesura del POM parla aquesta fila del document. Mateixa mà, dos gestos
// diferents — i per això el component és nou i no una crida al de la taula, que arrossega
// `repartida`, el desfer amb valors i la navegació per teclat de la seva graella.
//
// EL QUE SÍ QUE ÉS COMPARTIT és el que ha de ser-ho: el vocabulari (`GET
// /api/v1/mesures/diccionari/` via `dimensionsDe`), l'etiqueta (`etiquetaInstancia`) i la
// composició del slug (`composaInstancia`, dins de `triaTram`). Cap llista d'eixos escrita a mà.

import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import Modal from '../ui/Modal'
import { etiquetaCapa, etiquetaInstancia } from '../../utils/capaInstancia'
import { dimensionsDe, nomEnIdioma } from '../../utils/diccionariMesures'
import { aplicaCombinacio, tramsPerEix, triaTram } from './instanciaTria.js'

const pindolaS = (encesa) => ({
  font: 'inherit', fontSize: 'var(--fs-label)', borderRadius: 999, padding: '2px 10px',
  cursor: 'pointer', whiteSpace: 'nowrap',
  border: `1px solid ${encesa ? 'var(--gold)' : 'var(--border)'}`,
  background: encesa ? 'var(--gold-pale)' : 'var(--white)',
  color: encesa ? 'var(--gold)' : 'var(--text-main)',
  fontWeight: encesa ? 600 : 400,
})

function Pindola({ slug, dicc, encesa, onTria, tip }) {
  return (
    <button type="button" onClick={() => onTria(slug)} title={tip} aria-label={tip}
      aria-pressed={encesa} style={pindolaS(encesa)}>
      {etiquetaInstancia(slug, dicc)}
    </button>
  )
}

/**
 * `＋` — LA COMBINACIÓ, EN UN SOL LLOC. Les píndoles de la fila ja creuen eixos (prémer «Bottom»
 * i «Extended» dona `bottom-extended`), o sigui que aquest modal no hi afegeix cap poder nou:
 * hi afegeix VISTA. Amb tres eixos i vuit posicions, triar-ho tot des d'una fila estreta és
 * llegir de reüll; aquí es veu el que hi ha triat a cada eix i què en surt, i es torna a la
 * instància única amb un sol gest.
 */
function ModalCombinacio({ valor, dicc, onTanca, onAplica }) {
  const { t, i18n } = useTranslation()
  const [tria, setTria] = useState(() => tramsPerEix(dicc, valor))
  const dims = dimensionsDe(dicc)
  const resultat = aplicaCombinacio(dicc, tria)
  return (
    <Modal title={t('instancia.grup')} subtitle={t('instancia.mes_tip')}
      cancelLabel={t('app.cancel')} confirmLabel={t('app.apply')}
      onCancel={onTanca} onConfirm={() => onAplica(resultat)}>
      {dims.map(d => (
        <div key={d.clau} style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 4 }}>
            {nomEnIdioma(d, i18n.language)}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {d.opcions.map(o => (
              <Pindola key={o.slug} slug={o.slug} dicc={dicc} encesa={tria[d.clau] === o.slug}
                tip={etiquetaInstancia(o.slug, dicc)}
                onTria={s => setTria(prev => {
                  const n = { ...prev }
                  if (n[d.clau] === s) delete n[d.clau]
                  else n[d.clau] = s
                  return n
                })} />
            ))}
          </div>
        </div>
      ))}
      <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)' }}>
        {resultat
          ? <>{t('instancia.grup')}: <b>{etiquetaInstancia(resultat, dicc)}</b></>
          : t('instancia.unica')}
      </div>
    </Modal>
  )
}

/**
 * `valor` és el slug d'instància de la fila (`''` = la instància única, el cas normal) i
 * `onTria` en rep el nou sencer. El component no desa res: qui mana sobre la fila és qui el
 * munta.
 *
 * Sense diccionari (o si el GET ha fallat) no pinta res — la pantalla es comporta com abans en
 * comptes d'oferir una llista mig feta. És la mateixa llei que ja segueix `EditableTable`.
 */
export default function ColumnatIdentitat({ valor = '', capa = '', dicc, onTria, onCapa }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)
  const [modal, setModal] = useState(false)
  const dims = dimensionsDe(dicc)
  const capes = dicc?.capes || []
  if (!dims.length && !capes.length) return null
  const actuals = tramsPerEix(dicc, valor)
  const grupS = { padding: '6px 10px', borderLeft: `1px solid var(--border)` }
  const retolS = { fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase',
                   letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: 5 }

  // EL FORMAT DE MESURES (v8.1 · el columnat de la Definició manual): una capçalera INSTÀNCIA i,
  // a sota, un GRUP DE COLUMNES per eix del diccionari amb el seu rètol, més la del `＋`. No és
  // decoració: amb les píndoles en una tira sola, «Bottom» i «Relaxed» semblen la mateixa llista
  // i triar-ne una de cada sembla contradir-se. Amb els grups es veu que són dues preguntes.
  return (
    <div style={{ display: 'inline-block', border: `1px solid var(--border)`, borderRadius: 6,
                  background: 'var(--white)', overflow: 'hidden' }}>
      <div style={{ padding: '4px 10px', background: 'var(--gold-pale)', color: 'var(--gold)',
                    fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase',
                    letterSpacing: '0.04em' }}>
        {t('identitat.grup')}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'stretch' }}>
        {/* LA CAPA · el mateix control que la Definició manual (un <select> amb el vocabulari
            de `MeasurementLayer` que el diccionari publica): és una tria EXCLOENT d'una llista
            tancada i curta, no una graella d'opcions. Default `exterior` — qui no la toca es
            comporta com sempre. */}
        {capes.length > 0 && onCapa && (
          <div style={{ ...grupS, borderLeft: 'none' }}>
            <div style={retolS}>{t('capa.col')}</div>
            <select value={capa || 'exterior'} aria-label={t('capa.col')}
              onChange={e => onCapa(e.target.value)}
              style={{ font: 'inherit', fontSize: 'var(--fs-label)', color: 'var(--text-main)',
                       background: 'var(--white)', border: '1px solid var(--border)',
                       borderRadius: 5, padding: '2px 6px', minWidth: 96 }}>
              {capes.map(c => (
                <option key={c.slug} value={c.slug}>{etiquetaCapa(c.slug, dicc, lang)}</option>
              ))}
            </select>
          </div>
        )}
        {dims.map((d, k) => (
          <div key={d.clau} style={{ ...grupS,
                                     borderLeft: (k || (capes.length && onCapa)) ? grupS.borderLeft : 'none' }}>
            <div style={retolS}>{nomEnIdioma(d, i18n.language)}</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {d.opcions.map(o => (
                <Pindola key={o.slug} slug={o.slug} dicc={dicc} encesa={actuals[d.clau] === o.slug}
                  tip={actuals[d.clau] === o.slug
                    ? t('instancia.tip_treu', { nom: etiquetaInstancia(o.slug, dicc) })
                    : t('instancia.tip_aquesta', { nom: etiquetaInstancia(o.slug, dicc) })}
                  onTria={s => onTria(triaTram(dicc, valor, s))} />
              ))}
            </div>
          </div>
        ))}
        <div style={grupS}>
          <div style={retolS}>{t('instancia.mes')}</div>
          <button type="button" onClick={() => setModal(true)} title={t('instancia.mes_tip')}
            aria-label={t('instancia.mes_tip')}
            style={{ ...pindolaS(false), color: 'var(--text-muted)' }}>＋</button>
        </div>
      </div>
      {modal && (
        <ModalCombinacio valor={valor} dicc={dicc} onTanca={() => setModal(false)}
          onAplica={slug => { onTria(slug); setModal(false) }} />
      )}
    </div>
  )
}
