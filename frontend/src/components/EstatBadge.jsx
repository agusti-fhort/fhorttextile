
// Light theme palette with high contrast (text readable over background)
const ESTAT_CONFIG = {
  // Model estats
  'Nou':                { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  "Pendent d'inputs":   { bg: '#f0dfc0', text: '#1d1d1b', border: '#e0d5c5' },
  'Preparat':           { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'En curs':            { bg: '#c27a2a', text: '#1d1d1b', border: '#c27a2a' },
  'En revisió':         { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Bloquejat':          { bg: '#f0f0f0', text: '#868685', border: '#e0d5c5' },
  'Tancat':             { bg: '#1d1d1b', text: '#ffffff', border: '#1d1d1b' },
  // Prioritat
  'Baixa':              { bg: '#f0f0f0', text: '#868685', border: '#e0d5c5' },
  'Normal':             { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Alta':               { bg: '#c27a2a', text: '#1d1d1b', border: '#c27a2a' },
  'Urgent':             { bg: '#a32d2d', text: '#ffffff', border: '#a32d2d' },
  // SF states (display labels — matches get_estat_display())
  'Pendent':            { bg: '#f0dfc0', text: '#1d1d1b', border: '#e0d5c5' },
  'Base oberta':        { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Base tancada':       { bg: '#c27a2a', text: '#1d1d1b', border: '#c27a2a' },
  'Talles generades':   { bg: '#1d1d1b', text: '#ffffff', border: '#1d1d1b' },
  // Tasca estats
  'Feta':               { bg: '#1d1d1b', text: '#ffffff', border: '#1d1d1b' },
  'Bloquejada':         { bg: '#f0f0f0', text: '#868685', border: '#e0d5c5' },
}

export function EstatBadge({ estat, size = 'sm' }) {
  if (!estat) return null
  const config = ESTAT_CONFIG[estat] || { bg: '#f0f0f0', text: '#868685', border: '#e0d5c5' }
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
