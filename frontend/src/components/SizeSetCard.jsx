import Badge from './ui/Badge'

export default function SizeSetCard({ profile, onUse, onDetail, onClone, detailOpen }) {
  const isCustom = !!profile.customClient
  return (
    <div style={{
      background: 'var(--white)',
      border: '0.5px solid #e4e4e2',
      borderRadius: 12,
      padding: '1.2rem 1.3rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.9rem',
    }}>
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 8, minWidth: 0}}>
          <i className="ti ti-arrows-maximize" style={{fontSize: 16, color: 'var(--gold)'}} />
          <span style={{fontSize: 14, fontWeight: 500}}>{profile.name}</span>
        </div>
        {isCustom ? (
          <Badge variant="gold" icon="ti-user-cog">
            Personalitzat {profile.customClient}
          </Badge>
        ) : (
          <Badge variant="ok" icon="ti-certificate">
            Estàndard {profile.standard || 'ISO'}
          </Badge>
        )}
      </div>

      <div style={{display: 'flex', flexWrap: 'wrap', gap: 6}}>
        {profile.sizes.map(s => {
          const isBase = s === profile.base
          return (
            <span key={s} style={{
              fontSize: 11,
              padding: '4px 10px',
              borderRadius: 6,
              background: isBase ? 'var(--gold)' : 'var(--gold-pale)',
              color: isBase ? 'white' : 'var(--gold)',
              fontWeight: 500,
              fontVariantNumeric: 'tabular-nums',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
            }}>
              {s}
              {isBase && <span style={{fontSize: 10}}>★</span>}
            </span>
          )
        })}
      </div>

      <div style={{
        fontSize: 11,
        color: 'var(--gray)',
        fontWeight: 300,
        padding: '8px 10px',
        background: 'var(--gray-l)',
        borderRadius: 6,
      }}>
        <span style={{
          fontSize: 9, letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--gray)', marginRight: 6,
        }}>Grading</span>
        {profile.grading}
      </div>

      <div style={{display: 'flex', gap: 6, marginTop: 'auto'}}>
        <ActionBtn primary icon="ti-check" onClick={onUse}>Usar</ActionBtn>
        <ActionBtn icon={detailOpen ? 'ti-chevron-up' : 'ti-eye'} onClick={onDetail}>
          {detailOpen ? 'Tancar' : 'Veure detall'}
        </ActionBtn>
        <ActionBtn icon="ti-copy" onClick={onClone}>Clonar</ActionBtn>
      </div>
    </div>
  )
}

function ActionBtn({ icon, children, primary, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        background: primary ? 'var(--gold)' : 'var(--white)',
        color: primary ? 'white' : 'var(--ink, #1d1d1b)',
        border: primary ? 'none' : '0.5px solid #e4e4e2',
        borderRadius: 8,
        padding: '7px 10px',
        fontSize: 11.5,
        fontWeight: primary ? 500 : 400,
        cursor: 'pointer',
        fontFamily: 'inherit',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 5,
        transition: 'all 0.15s',
      }}
    >
      {icon && <i className={`ti ${icon}`} style={{fontSize: 13}} />}
      {children}
    </button>
  )
}
