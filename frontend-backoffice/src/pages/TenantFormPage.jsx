import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import {
  getTenant, createTenant, updateTenant, getPlans, MOCK_PLANS, MOCK_TENANTS,
} from '../api/tenants'
import { COUNTRIES } from '../config/fiscal'

const MONO = "'IBM Plex Mono', monospace"

const TIPOLOGIES = [{ v: 'estudi', l: 'Estudi' }, { v: 'marca', l: 'Marca' }]
const MONEDES = ['EUR', 'USD', 'GBP']
const IDIOMES = [{ v: 'ca', l: 'Català' }, { v: 'es', l: 'Castellà' }, { v: 'en', l: 'Anglès' }]
const TIPUS_CLIENT = [{ v: 'b2b', l: 'Empresa (B2B)' }, { v: 'b2c', l: 'Particular (B2C)' }]
const UNITATS = [{ v: 'cm', l: 'Centímetres' }, { v: 'inch', l: 'Polzades' }]

const EMPTY = {
  codi_tenant: '', nom: '', tipologia: 'estudi', plan: '', moneda: 'EUR', idioma: 'ca',
  rao_social: '', nif: '', tipus_client: 'b2b', email_facturacio: '',
  adreca_linia1: '', adreca_linia2: '', ciutat: '', estat_provincia: '', codi_postal: '', pais: 'ES',
  unitats: 'cm', feature_flags: '{}',
}

// ── Estils reutilitzables ─────────────────────────────────────────────────
const labelStyle = { display: 'block', fontSize: 11, letterSpacing: '.05em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600 }
const baseInput = { width: '100%', fontFamily: MONO, fontSize: 13, color: 'var(--text-main)', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px', outline: 'none' }
const sectionTitle = { fontSize: 12, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--gold)', fontWeight: 600, margin: '26px 0 14px', paddingBottom: 8, borderBottom: '1px solid var(--border)' }

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

export default function TenantFormPage() {
  const { codi } = useParams()
  const navigate = useNavigate()
  const rol = useAuthStore((s) => s.rol)
  const userRol = useAuthStore((s) => s.user?.rol)
  const isAdmin = (rol || userRol || '').toString().toUpperCase() === 'ADMIN'

  const isEdit = !!codi
  const [form, setForm] = useState(EMPTY)
  const [plans, setPlans] = useState(import.meta.env.DEV ? MOCK_PLANS : [])
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState({})   // errors per camp (del backend)
  const [globalError, setGlobalError] = useState('')

  const set = (k) => (e) => {
    const val = e?.target ? e.target.value : e
    setForm((f) => ({ ...f, [k]: val }))
  }

  // Carrega plans disponibles per al selector.
  useEffect(() => {
    getPlans()
      .then((d) => setPlans(Array.isArray(d) ? d : (d?.results ?? [])))
      .catch(() => setPlans(import.meta.env.DEV ? MOCK_PLANS : []))
  }, [])

  // Mode edició: carrega el tenant i omple el formulari.
  const loadTenant = useCallback(async () => {
    setLoading(true)
    try {
      const t = await getTenant(codi)
      hydrate(t)
    } catch {
      if (import.meta.env.DEV) {
        const m = MOCK_TENANTS.find((x) => x.codi_tenant === codi)
        if (m) hydrate(m)
      } else {
        // Staging/PROD: mai omplir el formulari amb dades inventades.
        setGlobalError(`No s’ha pogut carregar el tenant «${codi}» per editar-lo.`)
      }
    } finally {
      setLoading(false)
    }
  }, [codi])

  useEffect(() => { if (isEdit) loadTenant() }, [isEdit, loadTenant])

  function hydrate(t) {
    setForm({
      codi_tenant: t.codi_tenant || '',
      nom: t.nom || '',
      tipologia: t.tipologia || 'estudi',
      plan: t.plan_id ?? t.plan ?? '',
      moneda: t.moneda || 'EUR',
      idioma: t.idioma || 'ca',
      rao_social: t.rao_social || '',
      nif: t.nif || t.vat_number || '',
      tipus_client: t.tipus_client || 'b2b',
      email_facturacio: t.email_facturacio || '',
      adreca_linia1: t.adreca_linia1 || '',
      adreca_linia2: t.adreca_linia2 || '',
      ciutat: t.ciutat || '',
      estat_provincia: t.estat_provincia || '',
      codi_postal: t.codi_postal || '',
      pais: t.pais || 'ES',
      unitats: t.unitats || 'cm',
      feature_flags: JSON.stringify(t.feature_flags ?? {}, null, 0),
    })
  }

  // Resol el plan: si el form té un nom de pla en comptes d'id, el converteix a id.
  const resolvePlanId = useCallback(() => {
    if (!form.plan) return ''
    if (typeof form.plan === 'number') return form.plan
    const byId = plans.find((p) => String(p.id) === String(form.plan))
    if (byId) return byId.id
    const byName = plans.find((p) => p.nom === form.plan)
    return byName ? byName.id : form.plan
  }, [form.plan, plans])

  // Quan els plans arriben després d'hidratar en edició, normalitza plan→id.
  useEffect(() => {
    if (isEdit && form.plan && typeof form.plan !== 'number') {
      const id = resolvePlanId()
      if (id && id !== form.plan) setForm((f) => ({ ...f, plan: id }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plans])

  function validateLocal() {
    const e = {}
    if (!isEdit) {
      if (!/^[A-Z0-9]{3}$/.test(form.codi_tenant)) e.codi_tenant = 'Han de ser 3 caràcters alfanumèrics en majúscules.'
    }
    if (!form.nom.trim()) e.nom = 'El nom és obligatori.'
    if (!form.plan) e.plan = 'Selecciona un pla.'
    // D1 (F2-B): alta mínima comercial — pais i email_facturacio obligatoris.
    if (!form.pais) e.pais = 'El país és obligatori.'
    if (!form.email_facturacio.trim()) e.email_facturacio = 'L’email de facturació és obligatori.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email_facturacio)) e.email_facturacio = 'Introdueix un email vàlid.'
    try {
      JSON.parse(form.feature_flags || '{}')
    } catch {
      e.feature_flags = 'JSON no vàlid.'
    }
    return e
  }

  function buildPayload() {
    const payload = {
      nom: form.nom,
      tipologia: form.tipologia,
      plan: resolvePlanId() || null,
      moneda: form.moneda,
      idioma: form.idioma,
      rao_social: form.rao_social,
      nif: form.nif,
      tipus_client: form.tipus_client,
      email_facturacio: form.email_facturacio,
      adreca_linia1: form.adreca_linia1,
      adreca_linia2: form.adreca_linia2,
      ciutat: form.ciutat,
      estat_provincia: form.estat_provincia,
      codi_postal: form.codi_postal,
      pais: form.pais,
      unitats: form.unitats,
      feature_flags: JSON.parse(form.feature_flags || '{}'),
    }
    if (!isEdit) payload.codi_tenant = form.codi_tenant
    return payload
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setGlobalError('')
    const local = validateLocal()
    setErrors(local)
    if (Object.keys(local).length) return

    setSaving(true)
    try {
      const payload = buildPayload()
      if (isEdit) {
        await updateTenant(codi, payload)
        navigate(`/tenants/${codi}`)
      } else {
        const created = await createTenant(payload)
        navigate(`/tenants/${created.codi_tenant || form.codi_tenant}`)
      }
    } catch (err) {
      const data = err?.response?.data
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        // Errors de validació per camp del backend.
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

  const handleCancel = () => navigate(isEdit ? `/tenants/${codi}` : '/tenants')

  if (!isAdmin) {
    return (
      <div style={{ padding: '28px 32px', fontFamily: MONO, color: 'var(--err)', fontSize: 13 }}>
        Accés restringit: només els administradors poden crear o editar tenants.
        <div style={{ marginTop: 14 }}>
          <button type="button" onClick={() => navigate('/tenants')} style={{ ...baseInput, width: 'auto', cursor: 'pointer' }}>← Tornar a tenants</button>
        </div>
      </div>
    )
  }

  if (loading) {
    return <div style={{ padding: '28px 32px', fontFamily: MONO, color: 'var(--text-muted)', fontSize: 13 }}>Carregant…</div>
  }

  return (
    <div style={{ padding: '28px 32px', fontFamily: MONO, maxWidth: 860 }}>
      <div style={{ marginBottom: 4 }}>
        <button type="button" onClick={handleCancel} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 12, cursor: 'pointer', padding: 0 }}>
          ← {isEdit ? 'Detall del tenant' : 'Tenants'}
        </button>
      </div>
      <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-main)', margin: '0 0 24px' }}>
        {isEdit ? `Editar tenant #${form.codi_tenant}` : 'Nou tenant'}
      </h1>

      {globalError && (
        <div style={{ marginBottom: 18, background: 'var(--err-bg)', color: 'var(--err)', border: '1px solid var(--err)', borderRadius: 8, padding: '9px 13px', fontSize: 12 }}>
          {globalError}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* ── Identitat ── */}
        <div style={sectionTitle}>Identitat</div>
        <Grid>
          <Field label="Codi tenant" required={!isEdit} error={errors.codi_tenant}>
            <input
              value={form.codi_tenant}
              onChange={(e) => setForm((f) => ({ ...f, codi_tenant: e.target.value.toUpperCase().slice(0, 3) }))}
              readOnly={isEdit}
              maxLength={3}
              placeholder="ABC"
              style={{ ...baseInput, letterSpacing: '.2em', textTransform: 'uppercase', background: isEdit ? 'var(--bg-muted)' : 'var(--bg-card)', color: isEdit ? 'var(--text-muted)' : 'var(--text-main)', cursor: isEdit ? 'not-allowed' : 'text' }}
            />
          </Field>
          <Field label="Nom" required error={errors.nom}>
            <input value={form.nom} onChange={set('nom')} style={baseInput} />
          </Field>
          <Field label="Tipologia" required error={errors.tipologia}>
            <select value={form.tipologia} onChange={set('tipologia')} style={baseInput}>
              {TIPOLOGIES.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select>
          </Field>
          <Field label="Pla" required error={errors.plan}>
            <select value={form.plan} onChange={set('plan')} style={baseInput}>
              <option value="">— Selecciona —</option>
              {plans.map((p) => <option key={p.id} value={p.id}>{p.nom}</option>)}
            </select>
          </Field>
          <Field label="Moneda" required error={errors.moneda}>
            <select value={form.moneda} onChange={set('moneda')} style={baseInput}>
              {MONEDES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          <Field label="Idioma" required error={errors.idioma}>
            <select value={form.idioma} onChange={set('idioma')} style={baseInput}>
              {IDIOMES.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select>
          </Field>
        </Grid>

        {/* ── Dades fiscals ── */}
        <div style={sectionTitle}>Dades fiscals</div>
        <Grid>
          <Field label="Raó social" error={errors.rao_social}>
            <input value={form.rao_social} onChange={set('rao_social')} style={baseInput} />
          </Field>
          <Field label="NIF / VAT number" error={errors.nif || errors.vat_number}>
            <input value={form.nif} onChange={set('nif')} style={baseInput} />
          </Field>
          <Field label="Tipus de client" error={errors.tipus_client}>
            <select value={form.tipus_client} onChange={set('tipus_client')} style={baseInput}>
              {TIPUS_CLIENT.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select>
          </Field>
          <Field label="Email facturació" required error={errors.email_facturacio}>
            <input type="email" value={form.email_facturacio} onChange={set('email_facturacio')} style={baseInput} />
          </Field>
        </Grid>

        {/* ── Adreça ── */}
        <div style={sectionTitle}>Adreça</div>
        <Grid>
          <Field label="Adreça línia 1" error={errors.adreca_linia1}>
            <input value={form.adreca_linia1} onChange={set('adreca_linia1')} style={baseInput} />
          </Field>
          <Field label="Adreça línia 2" error={errors.adreca_linia2}>
            <input value={form.adreca_linia2} onChange={set('adreca_linia2')} style={baseInput} />
          </Field>
          <Field label="Ciutat" error={errors.ciutat}>
            <input value={form.ciutat} onChange={set('ciutat')} style={baseInput} />
          </Field>
          <Field label="Estat / Província" error={errors.estat_provincia}>
            <input value={form.estat_provincia} onChange={set('estat_provincia')} style={baseInput} />
          </Field>
          <Field label="Codi postal" error={errors.codi_postal}>
            <input value={form.codi_postal} onChange={set('codi_postal')} style={baseInput} />
          </Field>
          <Field label="País" required error={errors.pais}>
            <select value={form.pais} onChange={set('pais')} style={baseInput}>
              {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name} ({c.code})</option>)}
            </select>
          </Field>
        </Grid>

        {/* ── Configuració ── */}
        <div style={sectionTitle}>Configuració</div>
        <Grid>
          <Field label="Unitats" error={errors.unitats}>
            <select value={form.unitats} onChange={set('unitats')} style={baseInput}>
              {UNITATS.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select>
          </Field>
        </Grid>
        <Field label="Feature flags (JSON)" error={errors.feature_flags}>
          <textarea
            value={form.feature_flags}
            onChange={set('feature_flags')}
            rows={3}
            spellCheck={false}
            placeholder='{"flag_a": true}'
            style={{ ...baseInput, resize: 'vertical', fontFamily: MONO }}
          />
        </Field>

        {/* ── Accions ── */}
        <div style={{ display: 'flex', gap: 12, marginTop: 28 }}>
          <button
            type="button"
            onClick={handleCancel}
            disabled={saving}
            style={{ ...baseInput, width: 'auto', padding: '11px 22px', color: 'var(--text-muted)', cursor: 'pointer', background: 'transparent' }}
          >
            Cancel·lar
          </button>
          <button
            type="submit"
            disabled={saving}
            style={{
              width: 'auto', padding: '11px 26px', border: 'none', borderRadius: 8,
              background: 'var(--gold)', color: '#fff', fontFamily: MONO, fontSize: 13, fontWeight: 600,
              cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? 'Desant…' : 'Desar'}
          </button>
        </div>
      </form>
    </div>
  )
}
