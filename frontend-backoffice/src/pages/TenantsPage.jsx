import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { IconEye, IconRefresh, IconAlertTriangle, IconLoader2, IconPlus } from '@tabler/icons-react'
import { getTenants, MOCK_TENANTS } from '../api/tenants'
import { ESTAT_ORDRE, estatConfig, normalitzaEstat } from '../config/estats'
import useAuthStore from '../store/authStore'

const MONO = "'IBM Plex Mono', monospace"

// Tabs de filtre: TOTS + els quatre estats canònics.
const TABS = [{ key: 'tots', label: 'TOTS' }, ...ESTAT_ORDRE.map((k) => ({ key: k, label: estatConfig(k).label }))]

const thStyle = {
  textAlign: 'left',
  fontSize: 10,
  letterSpacing: '.08em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  fontWeight: 600,
  padding: '10px 14px',
  borderBottom: '1px solid var(--border)',
  whiteSpace: 'nowrap',
}
const tdStyle = {
  fontSize: 13,
  color: 'var(--text-main)',
  padding: '12px 14px',
  borderBottom: '1px solid var(--border)',
  verticalAlign: 'middle',
}

function Badge({ estat }) {
  const cfg = estatConfig(estat)
  return (
    <span style={{
      display: 'inline-block', padding: '4px 10px', borderRadius: 6,
      fontSize: 11, fontWeight: 600, letterSpacing: '.04em',
      color: cfg.color, background: cfg.bg,
    }}>
      {cfg.label}
    </span>
  )
}

export default function TenantsPage() {
  const navigate = useNavigate()
  const rol = useAuthStore((s) => s.rol)
  const userRol = useAuthStore((s) => s.user?.rol)
  const isAdmin = (rol || userRol || '').toString().toUpperCase() === 'ADMIN'

  const [tab, setTab] = useState('tots')
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [mock, setMock] = useState(false)

  const load = useCallback(async (estatKey) => {
    setLoading(true)
    setError('')
    const params = estatKey && estatKey !== 'tots' ? { estat: estatKey } : {}
    try {
      const data = await getTenants(params)
      // Tolerant amb paginació DRF ({results:[...]}) o llista plana.
      const list = Array.isArray(data) ? data : (data?.results ?? [])
      setTenants(list)
      setMock(false)
    } catch {
      // Fallback de desenvolupament: el backend pot no estar migrat encara.
      const filtered = estatKey && estatKey !== 'tots'
        ? MOCK_TENANTS.filter((t) => normalitzaEstat(t.estat) === estatKey)
        : MOCK_TENANTS
      setTenants(filtered)
      setMock(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(tab) }, [tab, load])

  return (
    <div style={{ padding: '28px 32px', fontFamily: MONO, minHeight: '100vh' }}>
      {/* Capçalera */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: 6 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>Tenants</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            type="button"
            onClick={() => load(tab)}
            style={{
              display: 'flex', alignItems: 'center', gap: 7, background: 'var(--bg-card)',
              border: '1px solid var(--border)', borderRadius: 8, padding: '8px 13px',
              fontFamily: MONO, fontSize: 12, color: 'var(--text-main)', cursor: 'pointer',
            }}
          >
            <IconRefresh size={15} stroke={1.7} /> Refrescar
          </button>
          {isAdmin && (
            <button
              type="button"
              onClick={() => navigate('/tenants/new')}
              style={{
                display: 'flex', alignItems: 'center', gap: 7, background: 'var(--gold)',
                border: 'none', borderRadius: 8, padding: '8px 14px',
                fontFamily: MONO, fontSize: 12, fontWeight: 600, color: '#fff', cursor: 'pointer',
              }}
            >
              <IconPlus size={15} stroke={2} /> Nou tenant
            </button>
          )}
        </div>
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 20px' }}>
        Clients de la plataforma · gestió d'estats i dades fiscals
      </p>

      {/* Avís mode mock */}
      {mock && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16,
          background: 'var(--warn-bg)', color: 'var(--warn)', border: '1px solid var(--warn)',
          borderRadius: 8, padding: '9px 13px', fontSize: 12,
        }}>
          <IconAlertTriangle size={15} stroke={1.7} />
          Dades de mostra — l'API de tenants encara no respon (backend Sprint 2 en curs).
        </div>
      )}

      {/* Tabs de filtre */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 18 }}>
        {TABS.map((tb) => {
          const active = tab === tb.key
          return (
            <button
              key={tb.key}
              type="button"
              onClick={() => setTab(tb.key)}
              style={{
                fontFamily: MONO, fontSize: 12, fontWeight: 600, letterSpacing: '.04em',
                padding: '8px 14px', borderRadius: 8, cursor: 'pointer',
                border: '1px solid ' + (active ? 'var(--gold)' : 'var(--border)'),
                background: active ? 'var(--gold)' : 'transparent',
                color: active ? '#fff' : 'var(--text-muted)',
                transition: 'all .15s',
              }}
            >
              {tb.label}
            </button>
          )
        })}
      </div>

      {/* Estats de càrrega / error / buit */}
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)', fontSize: 13, padding: '40px 0' }}>
          <IconLoader2 size={18} stroke={1.7} className="bo-spin" /> Carregant tenants…
          <style>{'@keyframes bo-spin{to{transform:rotate(360deg)}}.bo-spin{animation:bo-spin 1s linear infinite}'}</style>
        </div>
      ) : error ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--err)', fontSize: 13, padding: '40px 0' }}>
          <IconAlertTriangle size={16} stroke={1.7} /> {error}
        </div>
      ) : tenants.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>
          No hi ha tenants en aquest estat.
        </div>
      ) : (
        <div style={{ overflowX: 'auto', border: '1px solid var(--border)', borderRadius: 10, background: 'var(--bg-main)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
            <thead>
              <tr>
                <th style={thStyle}>Codi</th>
                <th style={thStyle}>Nom</th>
                <th style={thStyle}>Tipologia</th>
                <th style={thStyle}>Estat</th>
                <th style={thStyle}>Pla</th>
                <th style={thStyle}>Data alta</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Accions</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr
                  key={t.id ?? t.codi_tenant}
                  onClick={() => navigate(`/tenants/${t.codi_tenant}`)}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ ...tdStyle, fontWeight: 600, color: 'var(--text-muted)' }}>#{t.codi_tenant}</td>
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{t.nom}</td>
                  <td style={tdStyle}>{t.tipologia || '—'}</td>
                  <td style={tdStyle}><Badge estat={t.estat} /></td>
                  <td style={tdStyle}>{t.plan_nom || t.plan || '—'}</td>
                  <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{t.data_alta || '—'}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); navigate(`/tenants/${t.codi_tenant}`) }}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 6,
                        background: 'transparent', border: '1px solid var(--border)', borderRadius: 7,
                        padding: '6px 11px', fontFamily: MONO, fontSize: 12, color: 'var(--gold)',
                        cursor: 'pointer',
                      }}
                    >
                      <IconEye size={15} stroke={1.7} /> Veure detall
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
