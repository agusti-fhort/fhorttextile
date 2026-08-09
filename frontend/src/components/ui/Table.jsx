import { useTranslation } from 'react-i18next'

// LA TAULA COMPARTIDA DE LA CASA. Conformada a la part B amb el Catàleg de tasques, que és qui
// la munta més nua. `ui/TaulaLlista` és la graella CANÒNICA del §8e (ordenació, amplades per
// contingut, ellipsis); aquesta és la taula simple de consulta, i el que li tocava era la pell:
//  · les capçaleres anaven a `--gray` en pes 400 amb tracking 0.1em → §2: th 10px MAJÚSCULES
//    amb tracking .08em «a tot arreu», en pes 600 i `--text-soft`;
//  · els filets, `0.5px solid var(--gray-l)` (un àlies de FARCIMENT fent de vora, i mig píxel
//    que no és de cap escala) → `--line` a la capçalera i `--line-soft` entre files;
//  · els estats de càrrega i buit eren caixes de 3rem centrades → §8c: frase `--text-faint`
//    cursiva, «mai caixa buida muda»;
//  · el hover de fila pintava `--gray-l` (gris fred) → `--sel`, que és el hover de la casa.
export default function Table({ columns, data, onRowClick, loading, empty, loadingText }) {
  const { t } = useTranslation()
  if (loading) {
    return (
      <div style={{padding: 16, color: 'var(--text-faint)', fontStyle: 'italic', fontSize: 'var(--fs-body)'}}>
        {loadingText || t('common.loading')}
      </div>
    )
  }
  if (!data || data.length === 0) {
    return (
      <div style={{padding: 16, color: 'var(--text-faint)', fontStyle: 'italic', fontSize: 'var(--fs-body)'}}>
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
              padding: '8px 16px',
              fontSize: 'var(--fs-label)', letterSpacing: '.08em',
              textTransform: 'uppercase',
              color: 'var(--text-soft)', fontWeight: 600,
              borderBottom: '1px solid var(--line)',
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
              borderBottom: i < data.length - 1 ? '1px solid var(--line-soft)' : 'none',
              cursor: onRowClick ? 'pointer' : 'default',
            }}
            onMouseEnter={onRowClick ? e => e.currentTarget.style.background = 'var(--sel)' : undefined}
            onMouseLeave={onRowClick ? e => e.currentTarget.style.background = 'none' : undefined}
          >
            {columns.map(col => (
              <td key={col.key} style={{
                padding: '12px 16px',
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
