import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions } from '../../api/endpoints'
import Table from '../ui/Table'

const MONO = 'IBM Plex Mono, monospace'
const fmtDate = (v) => v ? new Date(v).toLocaleDateString('ca-ES', { dateStyle: 'medium' }) : '—'

// Pas 5B-fix · TRAM 3 — Tab Fitting = LOG. Llista les FittingSession del model + enllaç al detall.
// La programació viu al desplegable Accions.
export default function FittingTab({ model }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    fittingSessions.list({ model: model.id, ordering: '-data', page_size: 200 })
      .then(r => setList(r.data?.results ?? r.data ?? []))
      .catch(() => setList([]))
      .finally(() => setLoading(false))
  }, [model.id])

  useEffect(() => { load() }, [load])

  const columns = [
    { key: 'fase', label: t('model_sheet.phase') },
    { key: 'data', label: t('model_sheet.date'), render: r => fmtDate(r.data) },
    { key: 'estat', label: t('model_sheet.status'), render: r => <span style={{ fontWeight: 600, fontFamily: MONO, fontSize: 'var(--fs-body)' }}>{r.estat}</span> },
    { key: 'actions', label: '', align: 'right', render: r => <button style={miniBtn} onClick={() => navigate(`/fittings/${r.id}`)}>{t('model_sheet.view')} →</button> },
  ]

  return (
    <div>
      <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, margin: '0 0 14px', fontFamily: MONO }}>{t('model_sheet.fitting_title')}</h2>
      <Table columns={columns} data={list} loading={loading} empty={t('model_sheet.no_fittings')} onRowClick={r => navigate(`/fittings/${r.id}`)} />
    </div>
  )
}

const miniBtn = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '3px 8px', borderRadius: 4, cursor: 'pointer',
  background: 'var(--white)', color: 'var(--text-main)', border: '0.5px solid var(--gray-l)',
}
