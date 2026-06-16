
export function VersionBadge({ isCustom, version, parentNom, onClick }) {
  if (!isCustom) {
    return (
      <span style={{
        padding: '2px 8px', borderRadius: 3, fontSize: 10,
        background: '#f0f9f0', color: '#3b6d11',
        border: '1px solid #c0dd97', cursor: 'default',
      }}>
        Estàndard ISO
      </span>
    )
  }

  return (
    <button
      onClick={onClick}
      style={{
        padding: '2px 8px', borderRadius: 3, fontSize: 10,
        background: '#f5e6d0', color: 'var(--gold)',
        border: '1px solid var(--gold)',
        cursor: onClick ? 'pointer' : 'default',
        display: 'flex', alignItems: 'center', gap: 4,
      }}
    >
      <span>✏ Personalitzat</span>
      {version > 1 && <span style={{ fontSize: 9, opacity: .7 }}>v{version}</span>}
    </button>
  )
}
