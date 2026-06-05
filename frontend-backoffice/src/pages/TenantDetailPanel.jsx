import { useState } from 'react'
import { IconX, IconEdit, IconCheck, IconAlertTriangle } from '@tabler/icons-react'
import useAuthStore from '../store/authStore'
import { updateEstat } from '../api/tenants'
import { ESTAT_ORDRE, estatConfig } from '../config/estats'

const MONO = "'IBM Plex Mono', monospace"

const overlayStyle = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(29,29,27,.38)',
  zIndex: 50,
  display: 'flex',
  justifyContent: 'flex-end',
}

const drawerStyle = {
  width: 'min(440px, 92vw)',
  height: '100vh',
  background: 'var(--bg-main)',
  borderLeft: '1px solid var(--border)',
  boxShadow: '-24px 0 60px -40px rgba(29,29,27,.4)',
  display: 'flex',
  flexDirection: 'column',
  fontFamily: MONO,
  animation: 'bo-drawer-in .22s cubic-bezier(.2,.7,.2,1) both',
}

const labelStyle = {
  fontSize: 10,
  letterSpacing: '.08em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: 4,
}
const valueStyle = { fontSize: 13, color: 'var(--text-main)', wordBreak: 'break-word' }

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={labelStyle}>{label}</div>
      <div style={valueStyle}>{value || '—'}</div>
    </div>
  )
}

function SectionTitle({ children }) {
  return (
    <div style={{ fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--gold)', fontWeight: 600, margin: '6px 0 14px' }}>
      {children}
    </div>
  )
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

export default function TenantDetailPanel({ tenant, onClose, onUpdated }) {
  const rol = useAuthStore((s) => s.rol)
  const userRol = useAuthStore((s) => s.user?.rol)
  const isAdmin = (rol || userRol || '').toString().toUpperCase() === 'ADMIN'

  const [editing, setEditing] = useState(false)
  const [nouEstat, setNouEstat] = useState(estatConfig(tenant?.estat).key)
  const [motiu, setMotiu] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (!tenant) return null

  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      await updateEstat(tenant.id, nouEstat, motiu)
      setEditing(false)
      setMotiu('')
      onUpdated?.({ ...tenant, estat: nouEstat })
    } catch {
      setError('No s’ha pogut canviar l’estat. Torna-ho a intentar.')
    } finally {
      setSaving(false)
    }
  }

  const stripeOk = tenant.stripe_configurat ?? !!tenant.stripe_customer_id

  return (
    <div style={overlayStyle} onClick={onClose}>
      <style>{DRAWER_CSS}</style>
      <div style={drawerStyle} onClick={(e) => e.stopPropagation()}>
        {/* Capçalera */}
        <div style={{
          display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
          gap: 12, padding: '20px 22px', borderBottom: '1px solid var(--border)',
        }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 11, letterSpacing: '.08em', color: 'var(--text-muted)' }}>
              #{tenant.codi_tenant}
            </div>
            <div style={{ fontSize: 17, fontWeight: 600, color: 'var(--text-main)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {tenant.nom}
            </div>
            <div style={{ marginTop: 8 }}><Badge estat={tenant.estat} /></div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tancar"
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, display: 'flex' }}
          >
            <IconX size={20} stroke={1.6} />
          </button>
        </div>

        {/* Cos */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 22px' }}>
          <SectionTitle>Dades fiscals</SectionTitle>
          <Field label="Raó social" value={tenant.rao_social} />
          <Field label="NIF / Identificació fiscal" value={tenant.nif} />
          <Field label="Adreça" value={tenant.adreca} />
          <Field label="País" value={tenant.pais} />
          <Field label="Email facturació" value={tenant.email_facturacio} />

          <div style={{ height: 1, background: 'var(--border)', margin: '8px 0 20px' }} />

          <SectionTitle>Plataforma</SectionTitle>
          <Field label="Tipologia" value={tenant.tipologia} />
          <Field label="Pla" value={tenant.plan_nom || tenant.plan} />

          {/* Stripe — mai mostrem cap ID real */}
          <div style={{ marginBottom: 16 }}>
            <div style={labelStyle}>Stripe</div>
            <div style={{ ...valueStyle, color: stripeOk ? 'var(--ok)' : 'var(--text-muted)', fontWeight: 600 }}>
              {stripeOk ? '✓ Configurat' : '— Pendent'}
            </div>
          </div>

          <div style={{ height: 1, background: 'var(--border)', margin: '8px 0 20px' }} />

          <SectionTitle>Historial</SectionTitle>
          <Field label="Data d'alta" value={tenant.data_alta} />
          {tenant.data_suspensio && <Field label="Data de suspensió" value={tenant.data_suspensio} />}
          {tenant.data_baixa && <Field label="Data de baixa" value={tenant.data_baixa} />}
        </div>

        {/* Peu — canvi d'estat (només ADMIN) */}
        {isAdmin && (
          <div style={{ borderTop: '1px solid var(--border)', padding: '16px 22px' }}>
            {!editing ? (
              <button
                type="button"
                onClick={() => { setError(''); setNouEstat(estatConfig(tenant.estat).key); setEditing(true) }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8,
                  padding: '10px 14px', fontFamily: MONO, fontSize: 13, color: 'var(--text-main)',
                  cursor: 'pointer', width: '100%', justifyContent: 'center',
                }}
              >
                <IconEdit size={16} stroke={1.6} /> Canviar estat
              </button>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <div style={labelStyle}>Nou estat</div>
                  <select
                    value={nouEstat}
                    onChange={(e) => setNouEstat(e.target.value)}
                    style={{
                      width: '100%', fontFamily: MONO, fontSize: 13, color: 'var(--text-main)',
                      background: 'var(--bg-card)', border: '1px solid var(--border)',
                      borderRadius: 8, padding: '10px 12px', outline: 'none',
                    }}
                  >
                    {ESTAT_ORDRE.map((k) => (
                      <option key={k} value={k}>{estatConfig(k).label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <div style={labelStyle}>Motiu (opcional)</div>
                  <textarea
                    value={motiu}
                    onChange={(e) => setMotiu(e.target.value)}
                    rows={2}
                    placeholder="Motiu del canvi d'estat…"
                    style={{
                      width: '100%', fontFamily: MONO, fontSize: 13, color: 'var(--text-main)',
                      background: 'var(--bg-card)', border: '1px solid var(--border)',
                      borderRadius: 8, padding: '10px 12px', outline: 'none', resize: 'vertical',
                    }}
                  />
                </div>

                {error && (
                  <p style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--err)', margin: 0 }}>
                    <IconAlertTriangle size={15} stroke={1.7} /> {error}
                  </p>
                )}

                <div style={{ display: 'flex', gap: 10 }}>
                  <button
                    type="button"
                    onClick={() => { setEditing(false); setError('') }}
                    disabled={saving}
                    style={{
                      flex: 1, background: 'transparent', border: '1px solid var(--border)',
                      borderRadius: 8, padding: '10px', fontFamily: MONO, fontSize: 13,
                      color: 'var(--text-muted)', cursor: saving ? 'not-allowed' : 'pointer',
                    }}
                  >
                    Cancel·lar
                  </button>
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                      flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                      background: 'var(--gold)', border: 'none', borderRadius: 8, padding: '10px',
                      fontFamily: MONO, fontSize: 13, fontWeight: 600, color: '#fff',
                      cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1,
                    }}
                  >
                    <IconCheck size={16} stroke={2} /> {saving ? 'Desant…' : 'Confirmar'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

const DRAWER_CSS = `
@keyframes bo-drawer-in{from{opacity:.4;transform:translateX(24px)}to{opacity:1;transform:none}}
`
