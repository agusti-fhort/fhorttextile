
const FASES = [
  'Nou', 'Disseny', 'Tècnic', 'Prototip',
  'Mostres', 'Preproducció', 'Producció', 'Tancat'
]

// Light theme palette: pale gold background + black text for "done" phases;
// pure gold background + black text for "active"; low-opacity grey for "future".
// Regla de contrast: text sempre #1d1d1b (sobre fons clar) o #ffffff (sobre fons fosc).
const FASE_COLORS = {
  'Nou':          { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Disseny':      { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Tècnic':       { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Prototip':     { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Mostres':      { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Preproducció': { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Producció':    { bg: '#f5e6d0', text: '#1d1d1b', border: '#e0d5c5' },
  'Tancat':       { bg: '#1d1d1b', text: '#ffffff', border: '#1d1d1b' },
}

export function PhaseStepper({ faseActual, onFaseClick }) {
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
              title={fase}
              style={{
                padding: '3px 10px',
                borderRadius: 3,
                fontSize: 11,
                fontFamily: 'IBM Plex Mono, monospace',
                fontWeight: active ? 700 : done ? 500 : 400,
                background: active
                  ? '#c27a2a'
                  : done
                  ? colors.bg
                  : '#f0f0f0',
                color: active
                  ? '#1d1d1b'
                  : done
                  ? colors.text
                  : '#868685',
                border: `1px solid ${active ? '#c27a2a' : done ? colors.border : '#e0d5c5'}`,
                whiteSpace: 'nowrap',
                cursor: onFaseClick ? 'pointer' : 'default',
                transition: 'all 0.15s',
                opacity: future ? 0.4 : 1,
              }}
            >
              {active && <span style={{ marginRight: 4, opacity: 0.8 }}>▶</span>}
              {done && <span style={{ marginRight: 4, opacity: 0.5 }}>✓</span>}
              {fase}
            </div>
            {i < FASES.length - 1 && (
              <div style={{
                width: 12,
                height: 1,
                background: i < idx ? '#c27a2a' : '#e0d5c5',
                flexShrink: 0,
              }} />
            )}
          </div>
        )
      })}
    </div>
  )
}
