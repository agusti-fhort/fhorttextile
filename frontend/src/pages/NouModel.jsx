import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { models, garmentTypes } from '../api/endpoints'

const TEMPORADES = [
  { value: 'SS', label: 'SS · Spring/Summer' },
  { value: 'FW', label: 'FW · Fall/Winter' },
  { value: 'CO', label: 'CO · Cruise' },
  { value: 'SP', label: 'SP · Special' },
]

const FITS = ['Regular', 'Slim', 'Relaxed', 'Oversized']

const PRIORITATS = [
  { value: 1, label: '1 · Baixa' },
  { value: 3, label: '3 · Normal' },
  { value: 4, label: '4 · Alta' },
  { value: 5, label: '5 · Urgent' },
]

export default function NouModel() {
  const navigate = useNavigate()
  const anyActual = new Date().getFullYear()

  const [form, setForm] = useState({
    nom_prenda: '',
    codi_client: '',
    temporada: 'SS',
    any: anyActual,
    garment_type: '',
    fit_type: 'Regular',
    color_referencia: '',
    prioritat: 3,
    data_objectiu: '',
    observacions: '',
  })
  const [gTypes, setGTypes] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    garmentTypes.list({ page_size: 200 })
      .then(res => setGTypes(res.data.results || []))
  }, [])

  const setField = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.nom_prenda) {
      setError('El nom de la prenda és obligatori.')
      return
    }
    setSubmitting(true)
    try {
      const payload = { ...form }
      if (!payload.garment_type) delete payload.garment_type
      if (!payload.data_objectiu) delete payload.data_objectiu
      const res = await models.create(payload)
      navigate(`/models/${res.data.id}`)
    } catch (err) {
      const msg = err.response?.data ? JSON.stringify(err.response.data) : 'Error desconegut'
      setError(`No s'ha pogut crear el model: ${msg}`)
      setSubmitting(false)
    }
  }

  return (
    <div>
      <button onClick={() => navigate('/models')} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--gray)', fontSize: 12, fontFamily: 'var(--font)',
        marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <i className="ti ti-arrow-left" style={{fontSize: 14}} />
        Tornar a Models
      </button>

      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Nou model</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          Crea un model nou per al tenant
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 12,
        padding: '1.5rem 1.8rem',
        maxWidth: 880,
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: '1.2rem',
        }}>
          <Field label="Nom de la prenda *">
            <Input value={form.nom_prenda} onChange={v => setField('nom_prenda', v)} required />
          </Field>
          <Field label="Referència client">
            <Input value={form.codi_client} onChange={v => setField('codi_client', v)} />
          </Field>

          <Field label="Temporada">
            <Select value={form.temporada} onChange={v => setField('temporada', v)} options={TEMPORADES} />
          </Field>
          <Field label="Any">
            <Input type="number" value={form.any} onChange={v => setField('any', Number(v))} />
          </Field>

          <Field label="Garment Type">
            <Select
              value={form.garment_type}
              onChange={v => setField('garment_type', v)}
              options={[{value: '', label: '—'}, ...gTypes.map(g => ({value: g.id, label: g.nom}))]}
            />
          </Field>
          <Field label="Fit Type">
            <Select
              value={form.fit_type}
              onChange={v => setField('fit_type', v)}
              options={FITS.map(f => ({value: f, label: f}))}
            />
          </Field>

          <Field label="Color de referència">
            <Input value={form.color_referencia} onChange={v => setField('color_referencia', v)} />
          </Field>
          <Field label="Prioritat">
            <Select
              value={form.prioritat}
              onChange={v => setField('prioritat', Number(v))}
              options={PRIORITATS}
            />
          </Field>

          <Field label="Data objectiu">
            <Input type="date" value={form.data_objectiu} onChange={v => setField('data_objectiu', v)} />
          </Field>
          <div />

          <div style={{gridColumn: '1 / -1'}}>
            <Field label="Observacions">
              <textarea
                value={form.observacions}
                onChange={e => setField('observacions', e.target.value)}
                rows={4}
                style={{
                  width: '100%', resize: 'vertical',
                  background: 'var(--white)',
                  border: '0.5px solid #e4e4e2',
                  borderRadius: 8,
                  padding: '8px 12px',
                  fontSize: 12,
                  fontFamily: 'var(--font)',
                  outline: 'none',
                }}
              />
            </Field>
          </div>
        </div>

        {error && (
          <div style={{
            marginTop: '1rem', padding: '0.7rem 1rem',
            background: 'var(--err-bg)', color: 'var(--err)',
            borderRadius: 8, fontSize: 12,
          }}>
            {error}
          </div>
        )}

        <div style={{
          marginTop: '1.5rem', display: 'flex',
          justifyContent: 'flex-end', gap: '0.6rem',
        }}>
          <button type="button" onClick={() => navigate('/models')} style={{
            background: 'var(--white)', color: 'var(--gray)',
            border: '0.5px solid #e4e4e2', borderRadius: 8,
            padding: '8px 16px', fontSize: 12,
            cursor: 'pointer', fontFamily: 'var(--font)',
          }}>
            Cancel·lar
          </button>
          <button type="submit" disabled={submitting} style={{
            background: submitting ? 'rgba(194,122,42,0.5)' : 'var(--gold)',
            color: 'white', border: 'none', borderRadius: 8,
            padding: '8px 20px', fontSize: 12, fontWeight: 500,
            cursor: submitting ? 'not-allowed' : 'pointer',
            fontFamily: 'var(--font)',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <i className="ti ti-check" style={{fontSize: 14}} />
            {submitting ? 'Creant...' : 'Crear model'}
          </button>
        </div>
      </form>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label style={{display: 'flex', flexDirection: 'column', gap: 6}}>
      <span style={{fontSize: 11, color: 'var(--gray)', fontWeight: 400}}>{label}</span>
      {children}
    </label>
  )
}

function Input({ value, onChange, type = 'text', required }) {
  return (
    <input
      type={type}
      value={value}
      required={required}
      onChange={e => onChange(e.target.value)}
      style={{
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 12,
        fontFamily: 'var(--font)',
        outline: 'none',
      }}
    />
  )
}

function Select({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 12,
        fontFamily: 'var(--font)',
        outline: 'none',
        appearance: 'none',
        backgroundImage: 'url("data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'10\' height=\'10\' viewBox=\'0 0 10 10\'><path d=\'M2 4 L5 7 L8 4\' stroke=\'%23868685\' stroke-width=\'1.2\' fill=\'none\'/></svg>")',
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 10px center',
        paddingRight: 28,
      }}
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}
