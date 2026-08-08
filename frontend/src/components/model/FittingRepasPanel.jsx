import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { fittingRepas } from '../../api/endpoints'
import { buildRepasGroups, buildRepasRows } from './repasGridAdapter'
import MeasureGrid from './MeasureGrid'

// REPÀS de fittings del model — la superfície de tornar-hi.
//
// Fer un fitting ja té casa (l'editor G1, dins Mesures en mode treball). Repassar-los no en tenia:
// cada sessió es tancava i els comentaris que el tècnic hi deixava quedaven dins la sessió. Aquí
// totes les sessions fetes es posen en columnes cronològiques sobre la MATEIXA anatomia de la taula
// de mesures (MeasureGrid: POM × columnes, capçalera tipus + @data), amb els comentaris a la vista.
//
// LECTURA TOTAL: cap edició, cap autosave, cap acció. Qui vulgui canviar un valor va a la sessió.

const MONO = 'IBM Plex Mono, monospace'

export default function FittingRepasPanel({ model }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let viu = true
    setLoading(true)
    fittingRepas.get(model.id)
      .then(r => { if (viu) setData(r.data) })
      .catch(() => { if (viu) setData(null) })
      .finally(() => { if (viu) setLoading(false) })
    return () => { viu = false }
  }, [model.id])

  if (loading) {
    return <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('common.loading')}</div>
  }

  const sessions = data?.sessions || []
  if (!sessions.length) {
    return (
      <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)', padding: '8px 0' }}>
        {t('fitting.repas.no_sessions')}
      </div>
    )
  }

  const groups = buildRepasGroups(sessions, data.talla, data.model?.base_size_label, t)
  const rows = buildRepasRows(data.rows, sessions)

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 10 }}>
        <h3 style={{ fontFamily: MONO, fontSize: 'var(--fs-h3)', fontWeight: 500, margin: 0 }}>
          {t('fitting.repas.title')}
        </h3>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>
          {t('fitting.repas.count', { n: sessions.length })}
          {data.talla && ` · ${t('fitting.repas.size', { talla: data.talla })}`}
        </span>
      </div>
      <MeasureGrid rows={rows} groups={groups} editable={false}
        empty={<p style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('fitting.repas.empty')}</p>} />
    </div>
  )
}
