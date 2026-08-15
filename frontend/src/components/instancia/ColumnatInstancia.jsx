// EL COLUMNAT D'INSTÀNCIA — les píndoles de la casa, com a component compartit.
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
import { etiquetaInstancia } from '../../utils/capaInstancia'
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
export default function ColumnatInstancia({ valor = '', dicc, onTria, ambRetols = false }) {
  const { t, i18n } = useTranslation()
  const [modal, setModal] = useState(false)
  const dims = dimensionsDe(dicc)
  if (!dims.length) return null
  const actuals = tramsPerEix(dicc, valor)

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6 }}>
      {dims.map(d => (
        <div key={d.clau} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 4 }}>
          {ambRetols && (
            <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginRight: 2 }}>
              {nomEnIdioma(d, i18n.language)}
            </span>
          )}
          {d.opcions.map(o => (
            <Pindola key={o.slug} slug={o.slug} dicc={dicc} encesa={actuals[d.clau] === o.slug}
              tip={actuals[d.clau] === o.slug
                ? t('instancia.tip_treu', { nom: etiquetaInstancia(o.slug, dicc) })
                : t('instancia.tip_aquesta', { nom: etiquetaInstancia(o.slug, dicc) })}
              onTria={s => onTria(triaTram(dicc, valor, s))} />
          ))}
        </div>
      ))}
      <button type="button" onClick={() => setModal(true)} title={t('instancia.mes_tip')}
        aria-label={t('instancia.mes_tip')}
        style={{ ...pindolaS(false), color: 'var(--text-muted)' }}>＋</button>
      {modal && (
        <ModalCombinacio valor={valor} dicc={dicc} onTanca={() => setModal(false)}
          onAplica={slug => { onTria(slug); setModal(false) }} />
      )}
    </div>
  )
}
