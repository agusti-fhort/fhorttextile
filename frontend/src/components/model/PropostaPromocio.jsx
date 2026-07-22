import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { watchpoints } from '../../api/endpoints'

const PILL = (actiu) => ({
  padding: '2px 10px', borderRadius: 12, cursor: 'pointer',
  fontSize: 'var(--fs-caption)', lineHeight: 1.6,
  border: `0.5px solid ${actiu ? 'var(--gold)' : 'var(--border)'}`,
  background: actiu ? 'var(--gold-soft, var(--white))' : 'var(--white)',
  color: actiu ? 'var(--gold)' : 'var(--text-muted)',
})

// D1 · PROPOSTA DE PROMOCIÓ (Agus 2026-07-22).
//
// El contenidor de client és INTOCABLE per a escriptura automàtica: un import que porta POMs
// que el catàleg no té (`amplia`) o que hi divergeixen (`conflicte`) els desa NOMÉS al model
// i deixa aquesta proposta. Aquí es decideix, POM a POM, si pugen al catàleg del client.
//
// Res puja sol: només s'envien els POMs marcats explícitament com a «promocionar». Els que es
// deixen com estan segueixen vius al model — «només model» no és una pèrdua, és una decisió.
export default function PropostaPromocio({ wp, modelId, editable = false, onDone = null }) {
  const { t } = useTranslation()
  const items = wp.dades?.items || []
  const [tria, setTria] = useState({})       // {pom_id: true} = promocionar
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(false)

  const pendents = items.filter(i => i.estat === 'nomes_model')
  const triats = pendents.filter(i => tria[i.pom_id]).map(i => i.pom_id)

  const aplica = () => {
    if (!triats.length || busy) return
    setBusy(true); setErr(false)
    watchpoints.promocionarPoms(modelId, { watchpoint_id: wp.id, promocions: triats })
      .then(() => { setTria({}); onDone?.() })
      .catch(() => setErr(true))            // visible: un fallo de promoció no s'empassa
      .finally(() => setBusy(false))
  }

  return (
    <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
      <div style={{ fontWeight: 500 }}>{t('promocio_poms.title')}</div>
      <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: '2px 0 6px' }}>
        {t('promocio_poms.subtitle', { contenidor: wp.dades?.contenidor_nom || '' })}
      </div>

      {items.map(i => (
        <div key={i.pom_id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 0' }}>
          <span style={{ fontWeight: 500, minWidth: 48 }}>{i.pom_codi}</span>
          <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                         color: 'var(--text-muted)', fontSize: 'var(--fs-caption)' }}>
            {i.pom_nom}
            {' · '}
            {t(`promocio_poms.bucket.${i.bucket}`)}
          </span>
          {i.estat === 'promocionat' ? (
            <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--ok)' }}>
              <i className="ti ti-check" /> {t('promocio_poms.estat.promocionat')}
            </span>
          ) : !editable ? (
            <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
              {t('promocio_poms.estat.nomes_model')}
            </span>
          ) : (
            <div style={{ display: 'flex', gap: 4 }}>
              <button type="button" style={PILL(!tria[i.pom_id])}
                onClick={() => setTria(s => ({ ...s, [i.pom_id]: false }))}>
                {t('promocio_poms.accio.nomes_model')}
              </button>
              <button type="button" style={PILL(!!tria[i.pom_id])}
                onClick={() => setTria(s => ({ ...s, [i.pom_id]: true }))}>
                {t('promocio_poms.accio.promocionar')}
              </button>
            </div>
          )}
        </div>
      ))}

      {editable && pendents.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8 }}>
          <button type="button" onClick={aplica} disabled={busy || !triats.length}
            style={{ padding: '4px 12px', border: '0.5px solid var(--gold)', borderRadius: 4,
                     background: 'var(--white)', color: 'var(--gold)', fontSize: 'var(--fs-body)',
                     cursor: (busy || !triats.length) ? 'default' : 'pointer',
                     opacity: (busy || !triats.length) ? 0.5 : 1 }}>
            {t('promocio_poms.aplicar', { n: triats.length })}
          </button>
          <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
            {t('promocio_poms.nota_intocable')}
          </span>
        </div>
      )}
      {err && (
        <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--err)', marginTop: 6 }}>
          {t('promocio_poms.err')}
        </div>
      )}
    </div>
  )
}
