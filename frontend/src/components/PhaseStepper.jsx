import { useTranslation } from 'react-i18next'

// Enum de FASES del cicle de vida del model (id intacte: indexOf amb faseActual + lookup de
// FASE_COLORS). El LABEL mostrat es tradueix via model_phases.<id>; l'id NO es tradueix.
const FASES = [
  'Nou', 'Disseny', 'Tècnic', 'Prototip',
  'Mostres', 'Preproducció', 'Producció', 'Tancat'
]

// Light theme palette: pale gold background + black text for "done" phases;
// pure gold background + black text for "active"; low-opacity grey for "future".
// Regla de contrast: text sempre var(--text-main) (sobre fons clar) o var(--white) (sobre fons fosc).
const FASE_COLORS = {
  'Nou':          { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Disseny':      { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Tècnic':       { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Prototip':     { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Mostres':      { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Preproducció': { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Producció':    { bg: '#f5e6d0', text: 'var(--text-main)', border: 'var(--border)' },
  'Tancat':       { bg: 'var(--text-main)', text: 'var(--white)', border: 'var(--text-main)' },
}

export function PhaseStepper({ faseActual, onFaseClick }) {
  const { t } = useTranslation()
  const idx = FASES.indexOf(faseActual)

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      overflowX: 'auto',
      padding: '4px 0',
      gap: 0,
      scrollbarWidth: 'none',
    }}>
      {FASES.map((fase, i) => {
        const done = i < idx
        const active = i === idx
        const future = i > idx
        const colors = FASE_COLORS[fase] || FASE_COLORS['Nou']

        return (
          <div key={fase} style={{ display: 'flex', alignItems: 'center' }}>
            <div
              onClick={() => onFaseClick && onFaseClick(fase)}
              title={t(`model_phases.${fase}`, fase)}
              style={{
                padding: '3px 10px',
                borderRadius: 3,
                fontSize: 11,
                fontWeight: active ? 700 : done ? 500 : 400,
                background: active
                  ? 'var(--gold)'
                  : done
                  ? colors.bg
                  : '#f0f0f0',
                color: active
                  ? 'var(--text-main)'
                  : done
                  ? colors.text
                  : 'var(--text-muted)',
                border: `1px solid ${active ? 'var(--gold)' : done ? colors.border : 'var(--border)'}`,
                whiteSpace: 'nowrap',
                cursor: onFaseClick ? 'pointer' : 'default',
                transition: 'all 0.15s',
                opacity: future ? 0.4 : 1,
              }}
            >
              {active && <span style={{ marginRight: 4, opacity: 0.8 }}>▶</span>}
              {done && <span style={{ marginRight: 4, opacity: 0.5 }}>✓</span>}
              {t(`model_phases.${fase}`, fase)}
            </div>
            {i < FASES.length - 1 && (
              <div style={{
                width: 12,
                height: 1,
                background: i < idx ? 'var(--gold)' : 'var(--border)',
                flexShrink: 0,
              }} />
            )}
          </div>
        )
      })}
    </div>
  )
}
