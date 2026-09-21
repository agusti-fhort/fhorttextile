import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { IconEye, IconRefresh, IconAlertTriangle, IconLoader2 } from '@tabler/icons-react'
import { getLeadCounts, getLeads, MOCK_LEADS } from '../api/leads'
import { LEAD_ESTAT_ORDRE, leadEstatConfig } from '../config/leadEstats'

const MONO = "'IBM Plex Mono', monospace"

// Ordre demanat: Nous / Contactats / Tancats / Tots (obre a Nous) — diferent de
// TenantsPage, on TOTS va primer. Totes porten el seu recompte (leads/counts/).
const TABS = [...LEAD_ESTAT_ORDRE.map((k) => ({ key: k, label: leadEstatConfig(k).label })),
  { key: 'tots', label: 'TOTS' }]

const thStyle = {
  textAlign: 'left', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase',
  color: 'var(--text-muted)', fontWeight: 600, padding: '10px 14px',
  borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap',
}
const tdStyle = {
  fontSize: 13, color: 'var(--text-main)', padding: '12px 14px',
  borderBottom: '1px solid var(--border)', verticalAlign: 'middle',
}

const fmtDate = (v) => v ? new Date(v).toLocaleDateString('ca-ES', { dateStyle: 'medium' }) : '—'

function Badge({ estat }) {
  const cfg = leadEstatConfig(estat)
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

export default function LeadsPage() {
  const navigate = useNavigate()

  const [tab, setTab] = useState('nou')
  const [leads, setLeads] = useState([])
  const [counts, setCounts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [mock, setMock] = useState(false)

  const load = useCallback(async (estatKey) => {
    setLoading(true)
    setError('')
    const params = estatKey && estatKey !== 'tots' ? { estat: estatKey } : {}
    try {
      const data = await getLeads(params)
      const list = Array.isArray(data) ? data : (data?.results ?? [])
      setLeads(list)
      setMock(false)
    } catch {
      if (import.meta.env.DEV) {
        // Fallback NOMÉS en dev local: el backend pot no estar migrat encara.
        const filtered = estatKey && estatKey !== 'tots'
          ? MOCK_LEADS.filter((l) => l.estat === estatKey)
          : MOCK_LEADS
        setLeads(filtered)
        setMock(true)
      } else {
        // Staging/PROD: error real, mai dades inventades.
        setLeads([])
        setError('No s’ha pogut carregar la llista de leads. Torna-ho a provar.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  // Recompte de CADA pestanya, font única (leads/counts/, una sola consulta agregada
  // al backend) — independent de la pestanya activa i de la mida de la llista
  // carregada. Si falla, les pestanyes es mostren sense número (no bloqueja la llista).
  const loadCounts = useCallback(async () => {
    try {
      setCounts(await getLeadCounts())
    } catch {
      if (import.meta.env.DEV) {
        const per = (estat) => MOCK_LEADS.filter((l) => l.estat === estat).length
        setCounts({ nou: per('nou'), contactat: per('contactat'), tancat: per('tancat'), tots: MOCK_LEADS.length })
      } else {
        setCounts(null)
      }
    }
  }, [])

  useEffect(() => { load(tab) }, [tab, load])
  useEffect(() => { loadCounts() }, [loadCounts])

  const refresca = () => { load(tab); loadCounts() }

  return (
    <div style={{ padding: '28px 32px', fontFamily: MONO, minHeight: '100vh' }}>
      {/* Capçalera */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: 6 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>Leads</h1>
        <button
          type="button"
          onClick={refresca}
          style={{
            display: 'flex', alignItems: 'center', gap: 7, background: 'var(--bg-card)',
            border: '1px solid var(--border)', borderRadius: 8, padding: '8px 13px',
            fontFamily: MONO, fontSize: 12, color: 'var(--text-main)', cursor: 'pointer',
          }}
        >
          <IconRefresh size={15} stroke={1.7} /> Refrescar
        </button>
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 20px' }}>
        Leads del formulari públic de la web · gestió d'estat i seguiment
      </p>

      {mock && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16,
          background: 'var(--warn-bg)', color: 'var(--warn)', border: '1px solid var(--warn)',
          borderRadius: 8, padding: '9px 13px', fontSize: 12,
        }}>
          <IconAlertTriangle size={15} stroke={1.7} />
          Dades de mostra — l'API de leads encara no respon.
        </div>
      )}

      {/* Tabs de filtre */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 18 }}>
        {TABS.map((tb) => {
          const active = tab === tb.key
          const comptador = counts != null ? ` (${counts[tb.key]})` : ''
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
              {tb.label}{comptador}
            </button>
          )
        })}
      </div>

      {/* Estats de càrrega / error / buit */}
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)', fontSize: 13, padding: '40px 0' }}>
          <IconLoader2 size={18} stroke={1.7} className="bo-spin" /> Carregant leads…
          <style>{'@keyframes bo-spin{to{transform:rotate(360deg)}}.bo-spin{animation:bo-spin 1s linear infinite}'}</style>
        </div>
      ) : error ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--err)', fontSize: 13, padding: '40px 0' }}>
          <IconAlertTriangle size={16} stroke={1.7} /> {error}
        </div>
      ) : leads.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>
          No hi ha leads en aquest estat.
        </div>
      ) : (
        <div style={{ overflowX: 'auto', border: '1px solid var(--border)', borderRadius: 10, background: 'var(--bg-main)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
            <thead>
              <tr>
                <th style={thStyle}>Data</th>
                <th style={thStyle}>Nom</th>
                <th style={thStyle}>Empresa</th>
                <th style={thStyle}>Email</th>
                <th style={thStyle}>Idioma</th>
                <th style={thStyle}>Estat</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Accions</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((l) => (
                <tr key={l.id} onClick={() => navigate(`/leads/${l.id}`)} style={{ cursor: 'pointer' }}>
                  <td style={{ ...tdStyle, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{fmtDate(l.created_at)}</td>
                  <td style={{ ...tdStyle, fontWeight: 600 }}>{l.nom}</td>
                  <td style={tdStyle}>{l.empresa || '—'}</td>
                  <td style={tdStyle}>{l.email}</td>
                  <td style={tdStyle}>{(l.idioma || '—').toUpperCase()}</td>
                  <td style={tdStyle}><Badge estat={l.estat} /></td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); navigate(`/leads/${l.id}`) }}
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
