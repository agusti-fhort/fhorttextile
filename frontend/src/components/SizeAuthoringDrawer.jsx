import { useTranslation } from 'react-i18next'
import { Wizard } from '../pages/SizeMapSetup'

// Modal central d'autoria de talles muntable (1C-3). Embolcalla el Wizard de 5 passos extret
// de SizeMapSetup amb el patró de modal centrat (overlay fosc + panell centrat), amplada ~1100
// (porta la graella POM×talla dels passos 3/4). El Wizard interior NO es toca.
// Contracte: { open, prefill, onComplete, onClose }. prefill=null → autoria directa.
export default function SizeAuthoringDrawer({ open, prefill = null, onComplete, onClose }) {
  const { t } = useTranslation()

  if (!open) return null

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 200,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        padding: '3vh 16px', overflowY: 'auto',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 'min(1100px, 96vw)', maxHeight: '94vh',
          background: '#fff', zIndex: 201, borderRadius: 12,
          boxShadow: '0 12px 48px rgba(0,0,0,0.22)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
          fontFamily: 'IBM Plex Sans, sans-serif',
        }}
      >
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, fontFamily: 'IBM Plex Mono' }}>
              {t('size_map_new_run', 'Nou run de client')}
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: '#888' }}>
              {t('size_map_subtitle', 'Runs de client derivats i sistemes canònics')}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', fontSize: '1.5rem',
              cursor: 'pointer', color: '#888', lineHeight: 1, padding: '0 0.25rem',
            }}
          >
            ×
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '1.25rem 1.5rem' }}>
          <Wizard t={t} prefill={prefill} onClose={onClose} onComplete={onComplete} />
        </div>
      </div>
    </div>
  )
}
