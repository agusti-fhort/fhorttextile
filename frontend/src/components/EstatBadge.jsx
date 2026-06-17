import { useTranslation } from 'react-i18next'

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

// i18n: the `estat` prop is the canonical CA display string (matches get_estat_display())
// and is kept as the style id (ESTAT_CONFIG lookup). Only the DISPLAYED label is translated.
// Reuses existing model.estats.* / model.prioritats.* keys; the rest live under estat_badge.*.
const ESTAT_KEY = {
  'Nou':                'model.estats.Nou',
  "Pendent d'inputs":   'estat_badge.pendent_inputs',
  'Preparat':           'estat_badge.preparat',
  'En curs':            'model.estats.EnCurs',
  'En revisió':         'model.estats.EnRevisio',
  'Bloquejat':          'estat_badge.bloquejat',
  'Tancat':             'model.estats.Tancat',
  'Baixa':              'model.prioritats.1',
  'Normal':             'model.prioritats.3',
  'Alta':               'model.prioritats.4',
  'Urgent':             'model.prioritats.5',
  'Pendent':            'estat_badge.pendent',
  'Base oberta':        'estat_badge.base_oberta',
  'Base tancada':       'estat_badge.base_tancada',
  'Talles generades':   'estat_badge.talles_generades',
  'Feta':               'estat_badge.feta',
  'Bloquejada':         'estat_badge.bloquejada',
}

export function EstatBadge({ estat, size = 'sm' }) {
  const { t } = useTranslation()
  if (!estat) return null
  const config = ESTAT_CONFIG[estat] || { bg: '#f0f0f0', text: 'var(--text-muted)', border: 'var(--border)' }
  const label = ESTAT_KEY[estat] ? t(ESTAT_KEY[estat]) : estat
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
      {label}
    </span>
  )
}
