
const FASES = [
  'Nou', 'Disseny', 'Tècnic', 'Prototip',
  'Mostres', 'Preproducció', 'Producció', 'Tancat'
]

const FASE_COLORS = {
  'Nou':          { bg: '#1a1a1a', text: '#555', border: '#2a2a2a' },
  'Disseny':      { bg: '#1a2a1a', text: '#4a8a4a', border: '#2a4a2a' },
  'Tècnic':       { bg: '#1a1a2a', text: '#4a4a8a', border: '#2a2a4a' },
  'Prototip':     { bg: '#2a1a1a', text: '#8a4a2a', border: '#4a2a1a' },
  'Mostres':      { bg: '#2a2a1a', text: '#8a7a2a', border: '#4a4a1a' },
  'Preproducció': { bg: '#1a2a2a', text: '#2a7a7a', border: '#1a4a4a' },
  'Producció':    { bg: '#2a1a2a', text: '#7a2a7a', border: '#4a1a4a' },
  'Tancat':       { bg: '#1a1a1a', text: '#5a5a5a', border: '#3a3a3a' },
}

export function FaseStepper({ faseActual, onFaseClick }) {
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
                  : '#111',
                color: active
                  ? '#1d1d1b'
                  : done
                  ? colors.text
                  : '#333',
                border: `1px solid ${active ? '#c27a2a' : done ? colors.border : '#222'}`,
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
                background: i < idx ? '#333' : '#1a1a1a',
                flexShrink: 0,
              }} />
            )}
          </div>
        )
      })}
    </div>
  )
}
