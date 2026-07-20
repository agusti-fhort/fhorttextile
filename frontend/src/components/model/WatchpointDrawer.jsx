import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import WatchpointsPanel from './WatchpointsPanel'

// Watchpoint FLOTANT (D-12) — overlay (drawer dret) accessible des de la capçalera del model,
// independent de la pestanya activa. Reusa el patró de presentació de SizeSystemDrawer per a l'shell
// (overlay + panell dret, tanca al clic fora i amb ESC) i munta el WatchpointsPanel existent TAL QUAL
// com a fil cronològic (crear + llistar -created_at + resolve/reopen).
// CRÍTIC: NO toca l'estat del model (cap reloadModel/onChanged). El panell recarrega NOMÉS la seva
// pròpia llista internament → obrir/escriure aquí no provoca cap re-mount de la pestanya activa.
export default function WatchpointDrawer({ modelId, open, onClose, onChanged }) {
  const { t } = useTranslation()

  // ESC tanca (només mentre està obert).
  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <>
      <div onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)', zIndex: 200 }} />

      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(680px, 90vw)',
        background: 'var(--white)', zIndex: 201, boxShadow: '-4px 0 24px rgba(0,0,0,0.15)',
        display: 'flex', flexDirection: 'column',
      }}>
        <div style={{
          padding: '0.75rem 1.25rem', borderBottom: '0.5px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 8,
            fontSize: 'var(--fs-h3)', fontWeight: 600, color: 'var(--text-main)' }}>
            <i className="ti ti-message-2" aria-hidden="true" style={{ color: 'var(--gold)' }} />
            {t('watchpoints.title')}
          </span>
          <button type="button" onClick={onClose} aria-label={t('watchpoints.title')}
            style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer',
                     color: 'var(--text-muted)', lineHeight: 1, padding: '0 0.25rem' }}>
            ×
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '0 1.25rem 1.25rem' }}>
          <WatchpointsPanel modelId={modelId} taskId={null} editable={true} onChanged={onChanged} />
        </div>
      </div>
    </>
  )
}
