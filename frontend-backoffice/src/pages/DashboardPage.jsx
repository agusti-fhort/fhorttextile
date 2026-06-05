import { useNavigate } from 'react-router-dom'
import { IconBuildingStore, IconArrowRight } from '@tabler/icons-react'

const MONO = "'IBM Plex Mono', monospace"

export default function DashboardPage() {
  const navigate = useNavigate()

  return (
    <div style={{ padding: '28px 32px', fontFamily: MONO, minHeight: '100vh' }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-main)', margin: '0 0 6px' }}>
        Dashboard
      </h1>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 24px' }}>
        Panell de control del backoffice — pròximament mètriques d'ús i facturació.
      </p>

      {/* Accés ràpid a Tenants */}
      <button
        type="button"
        onClick={() => navigate('/tenants')}
        style={{
          display: 'flex', alignItems: 'center', gap: 14, width: 'min(360px, 100%)',
          textAlign: 'left', background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 12, padding: '18px 20px', cursor: 'pointer', fontFamily: MONO,
        }}
      >
        <span style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: 42, height: 42, borderRadius: 10, background: 'var(--gold-pale)', color: 'var(--gold)',
          flex: '0 0 42px',
        }}>
          <IconBuildingStore size={22} stroke={1.6} />
        </span>
        <span style={{ flex: 1, minWidth: 0 }}>
          <span style={{ display: 'block', fontSize: 14, fontWeight: 600, color: 'var(--text-main)' }}>Tenants</span>
          <span style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            Llista, detall i gestió d'estats
          </span>
        </span>
        <IconArrowRight size={18} stroke={1.6} style={{ color: 'var(--gold)' }} />
      </button>
    </div>
  )
}
