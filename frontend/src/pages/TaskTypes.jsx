import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { taskTypes } from '../api/endpoints'
import Center from '../components/ui/Center'
import Table from '../components/ui/Table'

// Catàleg de TaskType — READ-ONLY. El catàleg és canònic/sistema (sembrat per migració):
// el tenant NO l'edita. Aquesta pàgina és només consulta (sense alta/edició/esborrat).
// Backend: TaskTypeViewSet (ReadOnlyModelViewSet); escriure-hi retorna 405.
const MONO = 'IBM Plex Mono, monospace'

export default function TaskTypes() {
  const { t } = useTranslation()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])

  useEffect(() => {
    let alive = true
    taskTypes.list({ ordering: 'default_order' })
      .then(res => res.data?.results ?? (Array.isArray(res.data) ? res.data : []))
      .then(rows => { if (alive) setItems(rows) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const columns = [
    { key: 'code', label: t('task_types.col_code'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.code}</span> },
    { key: 'name', label: t('task_types.col_name') },
    { key: 'default_order', label: t('task_types.col_order'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{r.default_order}</span> },
    { key: 'active', label: t('task_types.col_active'),
      render: r => (
        <span style={{
          fontSize: 'var(--fs-label)', fontWeight: 600, padding: '2px 8px', borderRadius: 999, fontFamily: MONO,
          background: r.active ? 'var(--ok-bg)' : 'var(--gray-l)',
          color: r.active ? 'var(--ok)' : 'var(--gray)',
        }}>{r.active ? t('task_types.active') : t('task_types.inactive')}</span>
      ) },
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('task_types.title')}</h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('task_types.subtitle')}</p>
      </div>

      {loading ? <Center>{t('task_types.loading')}</Center>
        : error ? <Center>{t('task_types.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={items} loading={false} empty={t('task_types.empty')} />
            </div>
          )}
    </div>
  )
}
