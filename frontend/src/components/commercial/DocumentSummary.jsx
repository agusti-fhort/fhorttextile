// <DocumentSummary> — resum del document (totals) en contenidor PROPI, separat, a baix a la dreta.
// `lines` = [{ label, value, strong }] (base imposable · IVA · total; el total va `strong`). Si
// `showInternal`, afegeix un peu de COST INTERN discret (gris, fs-caption) — NOMÉS pantalla, mai al
// PDF. Sense text propi: labels per props (i18n a la pantalla).
const MONO = 'IBM Plex Mono, monospace'

export default function DocumentSummary({ lines = [], showInternal = false, internalLabel, internalValue }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
      <div style={{ minWidth: 280, border: '0.5px solid var(--border)', borderRadius: 12, background: 'var(--white)', overflow: 'hidden' }}>
        <div style={{ padding: '12px 16px' }}>
          {lines.map((l, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '3px 0' }}>
              <span style={{ color: 'var(--text-muted)', fontWeight: l.strong ? 600 : 400, fontSize: l.strong ? 'var(--fs-h3)' : 'var(--fs-body)' }}>{l.label}</span>
              <span style={{ fontFamily: MONO, fontWeight: l.strong ? 700 : 400, fontSize: l.strong ? 'var(--fs-h3)' : 'var(--fs-body)' }}>{l.value}</span>
            </div>
          ))}
        </div>
        {showInternal && (
          <div style={{
            display: 'flex', justifyContent: 'space-between', gap: 16, padding: '8px 16px',
            background: 'var(--intern-bg)', borderTop: '0.5px solid var(--border)',
          }}>
            <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)', fontFamily: MONO }}>{internalLabel}</span>
            <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)', fontFamily: MONO }}>{internalValue}</span>
          </div>
        )}
      </div>
    </div>
  )
}
