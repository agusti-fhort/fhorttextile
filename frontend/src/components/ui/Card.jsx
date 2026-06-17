export default function Card({ title, icon, action, children, padding, style }) {
  return (
    <div style={{
      background: 'var(--white)',
      border: '0.5px solid #e4e4e2',
      borderRadius: 12,
      overflow: 'hidden',
      ...style,
    }}>
      {(title || action) && (
        <div style={{
          padding: '1rem 1.4rem',
          borderBottom: '0.5px solid #e4e4e2',
          display: 'flex', alignItems: 'center', gap: '0.8rem',
        }}>
          {icon && <i className={`ti ${icon}`} style={{fontSize: 18, color: 'var(--gold)'}} />}
          {title && <span style={{fontSize: 'var(--fs-h3)', fontWeight: 500}}>{title}</span>}
          {action && <div style={{marginLeft: 'auto'}}>{action}</div>}
        </div>
      )}
      <div style={{padding: padding ?? '1.2rem 1.4rem'}}>
        {children}
      </div>
    </div>
  )
}
