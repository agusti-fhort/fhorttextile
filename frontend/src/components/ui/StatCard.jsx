export default function StatCard({ icon, label, value, sub, subColor }) {
  return (
    <div style={{
      background: 'var(--white)',
      border: '0.5px solid #e4e4e2',
      borderRadius: 12,
      padding: '1.2rem 1.4rem',
    }}>
      <div style={{
        fontSize: 'var(--fs-body)', color: 'var(--gray)',
        marginBottom: '0.5rem',
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        {icon && <i className={`ti ${icon}`} style={{fontSize: 14, color: 'var(--gold)'}} />}
        {label}
      </div>
      <div style={{
        fontSize: '2rem', fontWeight: 500,
        color: 'var(--charcoal)', lineHeight: 1,
        marginBottom: '0.3rem',
      }}>
        {value}
      </div>
      {sub && (
        <div style={{fontSize: 'var(--fs-body)', color: subColor || 'var(--gray)', fontWeight: 300}}>
          {sub}
        </div>
      )}
    </div>
  )
}
