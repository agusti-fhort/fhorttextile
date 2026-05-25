const VARIANTS = {
  ok:   { bg: 'var(--ok-bg)',   color: 'var(--ok)'   },
  warn: { bg: 'var(--warn-bg)', color: 'var(--warn)' },
  err:  { bg: 'var(--err-bg)',  color: 'var(--err)'  },
  gate: { bg: 'var(--gate-bg)', color: 'var(--gate)' },
  gold: { bg: 'var(--gold-pale)', color: 'var(--gold)' },
  gray: { bg: 'var(--gray-l)',  color: 'var(--gray)' },
}

export default function Badge({ variant = 'gray', icon, children, style }) {
  const v = VARIANTS[variant] || VARIANTS.gray
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontSize: 11, padding: '3px 8px', borderRadius: 6,
      background: v.bg, color: v.color,
      fontWeight: 400, whiteSpace: 'nowrap',
      ...style,
    }}>
      {icon && <i className={`ti ${icon}`} style={{fontSize: 12}} />}
      {children}
    </span>
  )
}
