import { useTranslation } from 'react-i18next'

export default function Table({ columns, data, onRowClick, loading, empty, loadingText }) {
  const { t } = useTranslation()
  if (loading) {
    return (
      <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 'var(--fs-body)'}}>
        {loadingText || t('common.loading')}
      </div>
    )
  }
  if (!data || data.length === 0) {
    return (
      <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 'var(--fs-body)'}}>
        {empty || t('app.empty')}
      </div>
    )
  }
  return (
    <table style={{width: '100%', borderCollapse: 'collapse'}}>
      <thead>
        <tr>
          {columns.map(col => (
            <th key={col.key} style={{
              padding: '0.7rem 1rem',
              fontSize: 'var(--fs-label)', letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'var(--gray)', fontWeight: 400,
              borderBottom: '0.5px solid var(--gray-l)',
              textAlign: col.align || 'left', whiteSpace: 'nowrap',
              ...col.headerStyle,
            }}>
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr key={row.id ?? i}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            style={{
              borderBottom: i < data.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
              cursor: onRowClick ? 'pointer' : 'default',
            }}
            onMouseEnter={onRowClick ? e => e.currentTarget.style.background = 'var(--gray-l)' : undefined}
            onMouseLeave={onRowClick ? e => e.currentTarget.style.background = 'none' : undefined}
          >
            {columns.map(col => (
              <td key={col.key} style={{
                padding: '0.75rem 1rem',
                fontSize: 'var(--fs-body)',
                textAlign: col.align || 'left',
                ...col.cellStyle,
              }}>
                {col.render ? col.render(row) : row[col.key] ?? '—'}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
