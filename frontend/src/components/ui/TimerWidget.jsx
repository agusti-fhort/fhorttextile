import { useState, useEffect } from 'react'

function format(secs) {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}

export default function TimerWidget({ tasca, model, inici, compact = false }) {
  const [secs, setSecs] = useState(0)

  useEffect(() => {
    if (!inici) return
    const update = () => {
      const start = new Date(inici).getTime()
      setSecs(Math.max(0, Math.floor((Date.now() - start) / 1000)))
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [inici])

  if (compact) {
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        fontSize: 'var(--fs-body)', color: 'var(--warn)',
        fontVariantNumeric: 'tabular-nums',
      }}>
        <i className="ti ti-player-play-filled" style={{fontSize: 11}} />
        {format(secs)}
      </span>
    )
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '1.5rem', gap: '0.5rem',
    }}>
      {model && (
        <span style={{fontSize: 'var(--fs-body)', color: 'var(--gold)', fontWeight: 500}}>
          {model}
        </span>
      )}
      {tasca && (
        <span style={{fontSize: 'var(--fs-body)', fontWeight: 400}}>
          {tasca}
        </span>
      )}
      <div style={{
        fontSize: '2.5rem', fontWeight: 500,
        color: 'var(--charcoal)',
        fontVariantNumeric: 'tabular-nums',
        letterSpacing: '0.04em',
      }}>
        {format(secs)}
      </div>
    </div>
  )
}
