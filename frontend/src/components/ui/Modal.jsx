import { selS, primaryBtn } from './buttons'
import { overlayBase } from './overlay'

// Modal base genèric (patró estàndard de la fase). NO inclou lògica de domini: el cos va com a children.
// Overlay tanca al clic fora; panel atura la propagació. Footer = Cancel·lar + acció primària.
// props: { title, subtitle?, children, confirmLabel, cancelLabel, onConfirm, onCancel, confirmDisabled? }
const MONO = 'IBM Plex Mono, monospace'

export default function Modal({ title, subtitle, children, confirmLabel, cancelLabel, onConfirm, onCancel, confirmDisabled = false }) {
  return (
    <div onClick={onCancel} style={overlayBase({ alignItems: 'center' })}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--white)', borderRadius: 12, padding: 22,
        width: 460, maxWidth: '92vw', maxHeight: '85vh', overflowY: 'auto',
      }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: subtitle ? 4 : 16, fontFamily: MONO }}>{title}</h2>
        {subtitle && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>{subtitle}</p>}
        {children}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <button onClick={onCancel} style={{ ...selS, cursor: 'pointer' }}>{cancelLabel}</button>
          <button onClick={onConfirm} disabled={confirmDisabled} style={{
            ...primaryBtn, marginLeft: 0,
            opacity: confirmDisabled ? 0.5 : 1, cursor: confirmDisabled ? 'not-allowed' : 'pointer',
          }}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
