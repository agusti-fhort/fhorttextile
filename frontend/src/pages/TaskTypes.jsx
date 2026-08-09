import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { taskTypes } from '../api/endpoints'
import Center from '../components/ui/Center'
import Table from '../components/ui/Table'
import PageMenu from '../components/ui/PageMenu'
import Badge from '../components/ui/Badge'

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
    // §1 · el badge de la casa: fons suau + tinta + VORA FINA DEL MATEIX COLOR, píndola sempre.
    // Aquest es pintava a mà, sense vora, amb `--gray-l` de fons per a l'inactiu (un àlies de
    // farciment) i `--gray` de tinta (3.64:1). `ui/Badge` ja té les dues formes.
    { key: 'active', label: t('task_types.col_active'),
      render: r => (
        <Badge variant={r.active ? 'ok' : 'gray'}>
          {r.active ? t('task_types.active') : t('task_types.inactive')}
        </Badge>
      ) },
  ]

  return (
    <>
      {/* §8b · menú de pantalla. Sense seccions i sense acció —el catàleg és READ-ONLY i el
          backend hi retorna 405— queda la fletxa (§8b.2), que aquí és tot el que hi ha per fer
          a part de mirar. Cap acció inventada: la pantalla no en té cap i no n'ha de tenir. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu backTo="/" backTitle={t('task_types.back_title')} />
      </div>

    <div style={{ minWidth: 0, maxWidth: 1000, paddingTop: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500, marginBottom: 4, color: 'var(--text-main)', fontFamily: MONO }}>{t('task_types.title')}</h1>
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontFamily: MONO }}>{t('task_types.subtitle')}</p>
      </div>

      {loading ? <Center>{t('task_types.loading')}</Center>
        : error ? <Center>{t('task_types.error')}</Center>
          : (
            <div style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-card)', background: 'var(--panel)', fontSize: 'var(--fs-body)', overflowX: 'auto' }}>
              <Table columns={columns} data={items} loading={false} empty={t('task_types.empty')} />
            </div>
          )}
    </div>
    </>
  )
}
