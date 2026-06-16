
// Light theme palette with high contrast (text readable over background)
const ESTAT_CONFIG = {
  // Model estats
  'Nou':                { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  "Pendent d'inputs":   { bg: '#f0dfc0', text: 'var(--text-main)', border: 'var(--border)' },
  'Preparat':           { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'En curs':            { bg: 'var(--gold)', text: 'var(--text-main)', border: 'var(--gold)' },
  'En revisió':         { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Bloquejat':          { bg: '#f0f0f0', text: 'var(--text-muted)', border: 'var(--border)' },
  'Tancat':             { bg: 'var(--text-main)', text: 'var(--white)', border: 'var(--text-main)' },
  // Prioritat
  'Baixa':              { bg: '#f0f0f0', text: 'var(--text-muted)', border: 'var(--border)' },
  'Normal':             { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Alta':               { bg: 'var(--gold)', text: 'var(--text-main)', border: 'var(--gold)' },
  'Urgent':             { bg: '#a32d2d', text: 'var(--white)', border: '#a32d2d' },
  // SF states (display labels — matches get_estat_display())
  'Pendent':            { bg: '#f0dfc0', text: 'var(--text-main)', border: 'var(--border)' },
  'Base oberta':        { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Base tancada':       { bg: 'var(--gold)', text: 'var(--text-main)', border: 'var(--gold)' },
  'Talles generades':   { bg: 'var(--text-main)', text: 'var(--white)', border: 'var(--text-main)' },
  // Tasca estats
  'Feta':               { bg: 'var(--text-main)', text: 'var(--white)', border: 'var(--text-main)' },
  'Bloquejada':         { bg: '#f0f0f0', text: 'var(--text-muted)', border: 'var(--border)' },
}

export function EstatBadge({ estat, size = 'sm' }) {
  if (!estat) return null
  const config = ESTAT_CONFIG[estat] || { bg: '#f0f0f0', text: 'var(--text-muted)', border: 'var(--border)' }
  const fontSize = size === 'xs' ? 10 : size === 'sm' ? 11 : 12

  return (
    <span style={{
      display: 'inline-block',
      padding: `2px ${size === 'xs' ? 6 : 8}px`,
      borderRadius: 3,
      fontSize,
      fontWeight: 500,
      background: config.bg,
      color: config.text,
      border: `1px solid ${config.border}`,
      whiteSpace: 'nowrap',
      letterSpacing: '0.02em',
    }}>
      {estat}
    </span>
  )
}
