import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import {
  getTenant, getContactes, createContacte, deleteContacte,
  getPlans, updateTenant, MOCK_TENANTS, MOCK_CONTACTES, MOCK_PLANS,
} from '../api/tenants'
import { estatConfig } from '../config/estats'
import { countryName, regimVat, regimVatLabel } from '../config/fiscal'

const MONO = "'IBM Plex Mono', monospace"

const TABS = [
  { key: 'dades', label: 'DADES' },
  { key: 'condicions', label: 'CONDICIONS COMERCIALS' },
  { key: 'facturacio', label: 'FACTURACIÓ I PAGAMENTS' },
  { key: 'pagament', label: 'MÈTODE DE PAGAMENT' },
  { key: 'activitat', label: 'ACTIVITAT' },
  { key: 'tiquets', label: 'TIQUETS' },
]

// ── Helpers de presentació ────────────────────────────────────────────────
const labelStyle = { fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }
const cardStyle = { background: 'var(--bg-main)', border: '1px solid var(--border)', borderRadius: 12, padding: '22px 24px' }

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={labelStyle}>{label}</div>
      <div style={{ fontSize: 13, color: 'var(--text-main)', wordBreak: 'break-word' }}>{value || '—'}</div>
    </div>
  )
}

function SectionTitle({ children, action }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '4px 0 16px' }}>
      <div style={{ fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--gold)', fontWeight: 600 }}>{children}</div>
      {action}
    </div>
  )
}

function Grid({ children }) {
  return <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0 24px' }}>{children}</div>
}

// ── Layout compacte de la pestanya DADES ──────────────────────────────────
// Tres targetes en fila (33%), padding reduït, camps apilats en vertical.
// En mòbil (<768px) passen a columna única (media query via <style>).
const compactCard = { ...cardStyle, padding: '14px 16px' }
const dadesResponsiveCss = `
.bo-dades-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; align-items: start; }
@media (max-width: 767px) { .bo-dades-grid { grid-template-columns: 1fr; } }
`

function MiniTitle({ children, action }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, margin: '0 0 10px' }}>
      <div style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--gold)', fontWeight: 600 }}>{children}</div>
      {action}
    </div>
  )
}

function CompactField({ label, value, last }) {
  return (
    <div style={{ marginBottom: last ? 0 : 11 }}>
      <div style={{ fontSize: 9.5, letterSpacing: '.07em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 12.5, color: 'var(--text-main)', wordBreak: 'break-word' }}>{value || '—'}</div>
    </div>
  )
}

function Badge({ estat }) {
  const cfg = estatConfig(estat)
  return <span style={{ display: 'inline-block', padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600, letterSpacing: '.04em', color: cfg.color, background: cfg.bg }}>{cfg.label}</span>
}

function Placeholder({ children }) {
  return (
    <div style={{ ...cardStyle, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, padding: '48px 24px' }}>
      {children}
    </div>
  )
}

const ghostBtn = { display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent', border: '1px solid var(--border)', borderRadius: 8, padding: '7px 13px', fontFamily: MONO, fontSize: 12, color: 'var(--gold)', cursor: 'pointer' }

export default function TenantDetailPage() {
  const { codi } = useParams()
  const navigate = useNavigate()
  const rol = useAuthStore((s) => s.rol)
  const userRol = useAuthStore((s) => s.user?.rol)
  const isAdmin = (rol || userRol || '').toString().toUpperCase() === 'ADMIN'

  const [tab, setTab] = useState('dades')
  const [tenant, setTenant] = useState(null)
  const [contactes, setContactes] = useState([])
  const [plans, setPlans] = useState(MOCK_PLANS)
  const [loading, setLoading] = useState(true)
  const [mock, setMock] = useState(false)

  const loadTenant = useCallback(async () => {
    setLoading(true)
    try {
      const t = await getTenant(codi)
      setTenant(t)
      setMock(false)
    } catch {
      const m = MOCK_TENANTS.find((x) => x.codi_tenant === codi) || MOCK_TENANTS[0]
      setTenant(m)
      setMock(true)
    } finally {
      setLoading(false)
    }
  }, [codi])

  const loadContactes = useCallback(async () => {
    try {
      const c = await getContactes(codi)
      setContactes(Array.isArray(c) ? c : (c?.results ?? []))
    } catch {
      setContactes(MOCK_CONTACTES)
    }
  }, [codi])

  useEffect(() => {
    loadTenant()
    loadContactes()
    getPlans().then((d) => setPlans(Array.isArray(d) ? d : (d?.results ?? MOCK_PLANS))).catch(() => setPlans(MOCK_PLANS))
  }, [loadTenant, loadContactes])

  if (loading || !tenant) {
    return <div style={{ padding: '28px 32px', fontFamily: MONO, color: 'var(--text-muted)', fontSize: 13 }}>Carregant…</div>
  }

  const planObj = plans.find((p) => p.nom === (tenant.plan_nom || tenant.plan) || String(p.id) === String(tenant.plan_id))
  const stripeOk = tenant.stripe_configurat ?? !!tenant.stripe_customer_id
  const regim = tenant.regim_vat || regimVat(tenant.pais, tenant.tipus_client)

  return (
    <div style={{ padding: '28px 32px', fontFamily: MONO }}>
      {/* Capçalera */}
      <div style={{ marginBottom: 4 }}>
        <button type="button" onClick={() => navigate('/tenants')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 12, cursor: 'pointer', padding: 0 }}>
          ← Tenants
        </button>
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: '.08em', color: 'var(--text-muted)' }}>#{tenant.codi_tenant}</div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-main)', margin: '2px 0 8px' }}>{tenant.nom}</h1>
          <Badge estat={tenant.estat} />
        </div>
        {isAdmin && (
          <button type="button" onClick={() => navigate(`/tenants/${tenant.codi_tenant}/edit`)} style={ghostBtn}>
            <i className="ti ti-edit" style={{ fontSize: 15 }} /> Editar
          </button>
        )}
      </div>

      {mock && (
        <div style={{ marginBottom: 16, background: 'var(--warn-bg)', color: 'var(--warn)', border: '1px solid var(--warn)', borderRadius: 8, padding: '9px 13px', fontSize: 12 }}>
          Dades de mostra — l'API de tenants encara no respon (backend Sprint 3 en curs).
        </div>
      )}

      {/* Pestanyes */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', borderBottom: '1px solid var(--border)', marginBottom: 22 }}>
        {TABS.map((tb) => {
          const active = tab === tb.key
          return (
            <button
              key={tb.key}
              type="button"
              onClick={() => setTab(tb.key)}
              style={{
                fontFamily: MONO, fontSize: 11.5, fontWeight: 600, letterSpacing: '.04em',
                padding: '10px 14px', cursor: 'pointer', background: 'none', border: 'none',
                color: active ? 'var(--gold)' : 'var(--text-muted)',
                borderBottom: '2px solid ' + (active ? 'var(--gold)' : 'transparent'),
                marginBottom: -1,
              }}
            >
              {tb.label}
            </button>
          )
        })}
      </div>

      {/* ── Contingut ── */}
      {tab === 'dades' && (
        <DadesTab tenant={tenant} regim={regim} stripeOk={stripeOk} contactes={contactes}
          isAdmin={isAdmin} codi={codi} onContactesChange={loadContactes} mock={mock} />
      )}

      {tab === 'condicions' && (
        <CondicionsTab tenant={tenant} planObj={planObj} plans={plans} isAdmin={isAdmin}
          codi={codi} onChanged={loadTenant} />
      )}

      {tab === 'facturacio' && (
        <div>
          <div style={{ ...cardStyle, marginBottom: 16 }}>
            <SectionTitle>Informació fiscal</SectionTitle>
            <Grid>
              <Field label="Règim de VAT" value={regimVatLabel(regim)} />
              <Field label="Tipus de client" value={tenant.tipus_client === 'b2b' ? 'Empresa (B2B)' : tenant.tipus_client === 'b2c' ? 'Particular (B2C)' : '—'} />
              <Field label="País fiscal" value={countryName(tenant.pais)} />
            </Grid>
          </div>
          <Placeholder>Factures i pagaments — disponible al Sprint 6.</Placeholder>
        </div>
      )}

      {tab === 'pagament' && (
        <div>
          <div style={{ ...cardStyle, marginBottom: 16 }}>
            <SectionTitle>Stripe</SectionTitle>
            <div style={{ fontSize: 14, fontWeight: 600, color: stripeOk ? 'var(--ok)' : 'var(--text-muted)' }}>
              {stripeOk ? '✓ Configurat' : '— Pendent'}
            </div>
          </div>
          <Placeholder>Gestió Stripe — Sprint 7.</Placeholder>
        </div>
      )}

      {tab === 'activitat' && <Placeholder>Log d'activitat — Sprint 10.</Placeholder>}
      {tab === 'tiquets' && <Placeholder>Tiquets de suport — Sprint 9.</Placeholder>}
    </div>
  )
}

// ── Pestanya DADES ────────────────────────────────────────────────────────
function DadesTab({ tenant, regim, stripeOk, contactes, isAdmin, codi, onContactesChange, mock }) {
  const adreca = [tenant.adreca_linia1, tenant.adreca_linia2].filter(Boolean).join(', ') || tenant.adreca_fiscal || tenant.adreca

  const tipusClient = tenant.tipus_client === 'b2b' ? 'Empresa (B2B)' : tenant.tipus_client === 'b2c' ? 'Particular (B2C)' : '—'
  const stripeVal = <span style={{ color: stripeOk ? 'var(--ok)' : 'var(--text-muted)', fontWeight: 600 }}>{stripeOk ? '✓ Configurat' : '— Pendent'}</span>

  return (
    <div>
      <style>{dadesResponsiveCss}</style>

      {/* Tres targetes en fila (33% c/u); columna única en mòbil */}
      <div className="bo-dades-grid">
        <div style={compactCard}>
          <MiniTitle>Dades fiscals</MiniTitle>
          <CompactField label="Raó social" value={tenant.rao_social} />
          <CompactField label="NIF / VAT" value={tenant.nif || tenant.vat_number} />
          <CompactField label="Tipus de client" value={tipusClient} />
          <CompactField label="Email facturació" value={tenant.email_facturacio} />
          <CompactField label="Règim de VAT (calculat)" value={regimVatLabel(regim)} last />
        </div>

        <div style={compactCard}>
          <MiniTitle>Adreça</MiniTitle>
          <CompactField label="Adreça" value={adreca} />
          <CompactField label="Ciutat" value={tenant.ciutat} />
          <CompactField label="Estat / Província" value={tenant.estat_provincia} />
          <CompactField label="Codi postal" value={tenant.codi_postal} />
          <CompactField label="País" value={countryName(tenant.pais)} last />
        </div>

        <div style={compactCard}>
          <MiniTitle>Plataforma</MiniTitle>
          <CompactField label="Tipologia" value={tenant.tipologia} />
          <CompactField label="Stripe" value={stripeVal} />
          <CompactField label="Data d'alta" value={tenant.data_alta} last={!tenant.data_suspensio && !tenant.data_baixa} />
          {tenant.data_suspensio && <CompactField label="Data suspensió" value={tenant.data_suspensio} last={!tenant.data_baixa} />}
          {tenant.data_baixa && <CompactField label="Data baixa" value={tenant.data_baixa} last />}
        </div>
      </div>

      {/* Contactes: ample complet, sota les tres targetes */}
      <div style={{ marginTop: 16 }}>
        <ContactesSection contactes={contactes} isAdmin={isAdmin} codi={codi} onChange={onContactesChange} mock={mock} />
      </div>
    </div>
  )
}

// ── Subsecció CONTACTES ───────────────────────────────────────────────────
const EMPTY_CONTACTE = { nom: '', cognom: '', carrec: '', email: '', telefon: '', principal: false }
const ctInput = { width: '100%', fontFamily: MONO, fontSize: 13, color: 'var(--text-main)', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 11px', outline: 'none' }

function ContactesSection({ contactes, isAdmin, codi, onChange, mock }) {
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState(EMPTY_CONTACTE)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => {
    const v = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setForm((f) => ({ ...f, [k]: v }))
  }

  const handleAdd = async () => {
    setError('')
    if (!form.nom.trim()) { setError('El nom és obligatori.'); return }
    setSaving(true)
    try {
      await createContacte(codi, form)
      setForm(EMPTY_CONTACTE)
      setAdding(false)
      onChange()
    } catch {
      setError(mock ? 'API no disponible (mode mostra): no es pot desar el contacte.' : 'No s’ha pogut afegir el contacte.')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteContacte(codi, id)
      onChange()
    } catch {
      // silenci: en mode mock el delete no persisteix
    }
  }

  return (
    <div style={cardStyle}>
      <MiniTitle action={isAdmin && !adding ? (
        <button type="button" onClick={() => { setError(''); setAdding(true) }} style={ghostBtn}>
          <i className="ti ti-plus" style={{ fontSize: 15 }} /> Afegir contacte
        </button>
      ) : null}>Contactes</MiniTitle>

      {contactes.length === 0 && !adding && (
        <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '8px 0' }}>Cap contacte registrat.</div>
      )}

      {contactes.map((c) => (
        <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 0', borderBottom: '1px solid var(--border)' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)' }}>
              {[c.nom, c.cognom].filter(Boolean).join(' ')}
              {c.principal && (
                <span style={{ marginLeft: 8, fontSize: 10, fontWeight: 600, letterSpacing: '.04em', color: 'var(--gold)', background: 'var(--gold-pale)', padding: '2px 8px', borderRadius: 5 }}>PRINCIPAL</span>
              )}
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>
              {[c.carrec, c.email, c.telefon].filter(Boolean).join(' · ') || '—'}
            </div>
          </div>
          {isAdmin && (
            <button type="button" onClick={() => handleDelete(c.id)} aria-label="Esborrar contacte"
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--err)', padding: 6 }}>
              <i className="ti ti-trash" style={{ fontSize: 16 }} />
            </button>
          )}
        </div>
      ))}

      {adding && (
        <div style={{ marginTop: 16, padding: 16, background: 'var(--bg-card)', borderRadius: 10, border: '1px solid var(--border)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 10 }}>
            <input placeholder="Nom *" value={form.nom} onChange={set('nom')} style={ctInput} />
            <input placeholder="Cognom" value={form.cognom} onChange={set('cognom')} style={ctInput} />
            <input placeholder="Càrrec" value={form.carrec} onChange={set('carrec')} style={ctInput} />
            <input placeholder="Email" type="email" value={form.email} onChange={set('email')} style={ctInput} />
            <input placeholder="Telèfon" value={form.telefon} onChange={set('telefon')} style={ctInput} />
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, fontSize: 12, color: 'var(--text-main)', cursor: 'pointer' }}>
            <input type="checkbox" checked={form.principal} onChange={set('principal')} /> Contacte principal
          </label>
          {error && <p style={{ fontSize: 12, color: 'var(--err)', margin: '10px 0 0' }}>{error}</p>}
          <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
            <button type="button" onClick={() => { setAdding(false); setError('') }} disabled={saving}
              style={{ ...ghostBtn, color: 'var(--text-muted)' }}>Cancel·lar</button>
            <button type="button" onClick={handleAdd} disabled={saving}
              style={{ background: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 18px', fontFamily: MONO, fontSize: 12, fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1 }}>
              {saving ? 'Desant…' : 'Desar contacte'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Pestanya CONDICIONS COMERCIALS ────────────────────────────────────────
function CondicionsTab({ tenant, planObj, plans, isAdmin, codi, onChanged }) {
  const [changing, setChanging] = useState(false)
  const [planId, setPlanId] = useState(planObj?.id ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    setError('')
    if (!planId) { setError('Selecciona un pla.'); return }
    setSaving(true)
    try {
      await updateTenant(codi, { plan: Number(planId) })
      setChanging(false)
      onChanged()
    } catch {
      setError('No s’ha pogut canviar el pla.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div style={{ ...cardStyle, marginBottom: 16 }}>
        <SectionTitle action={isAdmin && !changing ? (
          <button type="button" onClick={() => { setError(''); setPlanId(planObj?.id ?? ''); setChanging(true) }} style={ghostBtn}>
            <i className="ti ti-arrows-exchange" style={{ fontSize: 15 }} /> Canviar pla
          </button>
        ) : null}>Pla i condicions</SectionTitle>

        <Grid>
          <Field label="Pla assignat" value={tenant.plan_nom || tenant.plan || planObj?.nom} />
          <Field label="Models inclosos" value={planObj?.models_inclosos != null ? String(planObj.models_inclosos) : '—'} />
          <Field label="Preu model extra" value={planObj?.preu_model_extra != null ? `${planObj.preu_model_extra} ${planObj.moneda_pla || ''}`.trim() : '—'} />
          <Field label="Moneda del pla" value={planObj?.moneda_pla || tenant.moneda} />
        </Grid>

        {changing && (
          <div style={{ marginTop: 8, padding: 16, background: 'var(--bg-card)', borderRadius: 10, border: '1px solid var(--border)' }}>
            <div style={labelStyle}>Nou pla</div>
            <select value={planId} onChange={(e) => setPlanId(e.target.value)}
              style={{ width: '100%', maxWidth: 320, fontFamily: MONO, fontSize: 13, color: 'var(--text-main)', background: 'var(--bg-main)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px' }}>
              <option value="">— Selecciona —</option>
              {plans.map((p) => <option key={p.id} value={p.id}>{p.nom}</option>)}
            </select>
            {error && <p style={{ fontSize: 12, color: 'var(--err)', margin: '10px 0 0' }}>{error}</p>}
            <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
              <button type="button" onClick={() => { setChanging(false); setError('') }} disabled={saving} style={{ ...ghostBtn, color: 'var(--text-muted)' }}>Cancel·lar</button>
              <button type="button" onClick={handleSave} disabled={saving}
                style={{ background: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 18px', fontFamily: MONO, fontSize: 12, fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1 }}>
                {saving ? 'Desant…' : 'Confirmar'}
              </button>
            </div>
          </div>
        )}
      </div>

      <Placeholder>Historial de canvis de condicions — pròximament.</Placeholder>
    </div>
  )
}
