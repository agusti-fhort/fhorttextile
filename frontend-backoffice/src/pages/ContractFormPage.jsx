import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTenants, MOCK_TENANTS } from '../api/tenants'
import { getServeis, createContracte } from '../api/contracts'

const MONO = "'IBM Plex Mono', monospace"
const MONEDES = ['EUR', 'USD', 'GBP']

// ── Estils reutilitzables (mateix patró que TenantFormPage) ────────────────
const labelStyle = { display: 'block', fontSize: 11, letterSpacing: '.05em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600 }
const baseInput = { width: '100%', fontFamily: MONO, fontSize: 13, color: 'var(--text-main)', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px', outline: 'none' }
const sectionTitle = { fontSize: 12, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--gold)', fontWeight: 600, margin: '26px 0 14px', paddingBottom: 8, borderBottom: '1px solid var(--border)' }
const cellInput = { ...baseInput, padding: '7px 9px', borderRadius: 6 }

function Field({ label, required, error, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={labelStyle}>{label}{required && <span style={{ color: 'var(--err)' }}> *</span>}</label>
      {children}
      {error && <p style={{ fontSize: 11, color: 'var(--err)', margin: '5px 0 0' }}>{error}</p>}
    </div>
  )
}

function Grid({ children }) {
  return <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0 18px' }}>{children}</div>
}

const EMPTY_LINE = { service: '', preu: '', moneda: 'EUR', inclosos: 0 }

export default function ContractFormPage() {
  const navigate = useNavigate()

  const [form, setForm] = useState({ client_codi: '', data_inici: '', data_fi: '', actiu: true, nota: '' })
  const [lines, setLines] = useState([{ ...EMPTY_LINE }])
  const [tenants, setTenants] = useState([])
  const [serveis, setServeis] = useState([])
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState({})
  const [globalError, setGlobalError] = useState('')

  const set = (k) => (e) => {
    const val = e?.target ? (e.target.type === 'checkbox' ? e.target.checked : e.target.value) : e
    setForm((f) => ({ ...f, [k]: val }))
  }

  // Selector de clients (tenants). getTenants ja retorna data; fallback a MOCK.
  useEffect(() => {
    getTenants({})
      .then((d) => setTenants(Array.isArray(d) ? d : (d?.results ?? [])))
      .catch(() => setTenants(MOCK_TENANTS))
  }, [])

  // Selector de serveis. getServeis retorna la resposta axios → cal .data.
  useEffect(() => {
    getServeis({ actiu: true })
      .then((r) => { const d = r.data; setServeis(Array.isArray(d) ? d : (d?.results ?? [])) })
      .catch(() => setServeis([]))
  }, [])

  // ── Línies ────────────────────────────────────────────────────────────
  const setLine = (i, k, v) => setLines((ls) => ls.map((l, idx) => idx === i ? { ...l, [k]: v } : l))
  const addLine = () => setLines((ls) => [...ls, { ...EMPTY_LINE }])
  const removeLine = (i) => setLines((ls) => ls.filter((_, idx) => idx !== i))

  function validateLocal() {
    const e = {}
    if (!form.client_codi) e.client_codi = 'Selecciona un client.'
    if (!form.data_inici) e.data_inici = 'La data d’inici és obligatòria.'
    if (form.data_fi && form.data_inici && form.data_fi < form.data_inici) {
      e.data_fi = 'La data de fi no pot ser anterior a la d’inici.'
    }
    return e
  }

  function buildPayload() {
    return {
      client_codi: form.client_codi,
      data_inici: form.data_inici,
      data_fi: form.data_fi || null,
      actiu: form.actiu,
      nota: form.nota,
      // Només línies amb servei seleccionat.
      lines: lines
        .filter((l) => l.service)
        .map((l) => ({
          service: l.service,
          preu: l.preu === '' ? null : l.preu,
          moneda: l.moneda,
          inclosos: l.inclosos === '' ? 0 : Number(l.inclosos),
        })),
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setGlobalError('')
    const local = validateLocal()
    setErrors(local)
    if (Object.keys(local).length) return

    setSaving(true)
    try {
      await createContracte(buildPayload())
      navigate('/contractes')
    } catch (err) {
      const data = err?.response?.data
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        const fieldErrors = {}
        Object.entries(data).forEach(([k, v]) => {
          fieldErrors[k] = Array.isArray(v) ? v.join(' ') : String(v)
        })
        setErrors((prev) => ({ ...prev, ...fieldErrors }))
        if (data.detail) setGlobalError(String(data.detail))
      } else {
        setGlobalError('No s’ha pogut desar. Comprova la connexió i torna-ho a provar.')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => navigate('/contractes')

  const thStyle = { padding: '8px 10px', fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em', textAlign: 'left', borderBottom: '1px solid var(--border)', fontWeight: 600 }
  const tdStyle = { padding: '6px 8px', borderBottom: '0.5px solid var(--border)', verticalAlign: 'middle' }

  return (
    <div style={{ padding: '28px 32px', fontFamily: MONO, maxWidth: 860 }}>
      <div style={{ marginBottom: 4 }}>
        <button type="button" onClick={handleCancel} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 12, cursor: 'pointer', padding: 0 }}>
          ← Contractes
        </button>
      </div>
      <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-main)', margin: '0 0 24px' }}>
        Nou contracte
      </h1>

      {globalError && (
        <div style={{ marginBottom: 18, background: 'var(--err-bg)', color: 'var(--err)', border: '1px solid var(--err)', borderRadius: 8, padding: '9px 13px', fontSize: 12 }}>
          {globalError}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* ── Contracte ── */}
        <div style={sectionTitle}>Contracte</div>
        <Grid>
          <Field label="Client" required error={errors.client_codi}>
            <select value={form.client_codi} onChange={set('client_codi')} style={baseInput}>
              <option value="">— Selecciona —</option>
              {tenants.map((tn) => (
                <option key={tn.codi_tenant} value={tn.codi_tenant}>
                  {tn.codi_tenant} · {tn.nom}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Data inici" required error={errors.data_inici}>
            <input type="date" value={form.data_inici} onChange={set('data_inici')} style={baseInput} />
          </Field>
          <Field label="Data fi (opcional)" error={errors.data_fi}>
            <input type="date" value={form.data_fi} onChange={set('data_fi')} style={baseInput} />
          </Field>
        </Grid>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, margin: '4px 0 16px' }}>
          <input type="checkbox" checked={form.actiu} onChange={set('actiu')} />
          Actiu
        </label>
        <Field label="Nota" error={errors.nota}>
          <textarea value={form.nota} onChange={set('nota')} rows={3}
            style={{ ...baseInput, resize: 'vertical', fontFamily: MONO }} />
        </Field>

        {/* ── Línies de servei ── */}
        <div style={sectionTitle}>Línies de servei</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 12 }}>
          <thead><tr>
            {['Servei', 'Preu', 'Moneda', 'Inclosos', ''].map((h, i) => <th key={i} style={thStyle}>{h}</th>)}
          </tr></thead>
          <tbody>
            {lines.map((l, i) => (
              <tr key={i}>
                <td style={tdStyle}>
                  <select value={l.service} onChange={(e) => setLine(i, 'service', e.target.value)} style={cellInput}>
                    <option value="">— Servei —</option>
                    {serveis.map((s) => (
                      <option key={s.id} value={s.id}>{s.code} · {s.nom}</option>
                    ))}
                  </select>
                </td>
                <td style={tdStyle}>
                  <input type="number" step="0.0001" value={l.preu}
                    onChange={(e) => setLine(i, 'preu', e.target.value)}
                    style={{ ...cellInput, width: 110 }} />
                </td>
                <td style={tdStyle}>
                  <select value={l.moneda} onChange={(e) => setLine(i, 'moneda', e.target.value)}
                    style={{ ...cellInput, width: 90 }}>
                    {MONEDES.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </td>
                <td style={tdStyle}>
                  <input type="number" value={l.inclosos}
                    onChange={(e) => setLine(i, 'inclosos', e.target.value)}
                    style={{ ...cellInput, width: 90 }} />
                </td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>
                  <button type="button" onClick={() => removeLine(i)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--err)', fontSize: 16 }}>
                    ×
                  </button>
                </td>
              </tr>
            ))}
            {!lines.length && (
              <tr><td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
                Cap línia. Afegeix-ne una.
              </td></tr>
            )}
          </tbody>
        </table>
        <button type="button" onClick={addLine}
          style={{ background: 'transparent', border: '1px solid var(--border)', borderRadius: 8, padding: '7px 13px', fontFamily: MONO, fontSize: 12, color: 'var(--gold)', cursor: 'pointer' }}>
          + Afegir línia
        </button>

        {/* ── Accions ── */}
        <div style={{ display: 'flex', gap: 12, marginTop: 28 }}>
          <button type="button" onClick={handleCancel} disabled={saving}
            style={{ ...baseInput, width: 'auto', padding: '11px 22px', color: 'var(--text-muted)', cursor: 'pointer', background: 'transparent' }}>
            Cancel·lar
          </button>
          <button type="submit" disabled={saving}
            style={{
              width: 'auto', padding: '11px 26px', border: 'none', borderRadius: 8,
              background: 'var(--gold)', color: '#fff', fontFamily: MONO, fontSize: 13, fontWeight: 600,
              cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1,
            }}>
            {saving ? 'Desant…' : 'Desar'}
          </button>
        </div>
      </form>
    </div>
  )
}
