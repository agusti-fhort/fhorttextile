import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fittingSessions, models } from '../api/endpoints'
import Card from '../components/ui/Card'

// Backend enum (línia divisòria sagrada — valors en català, no es toquen).
const FASES = ['Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

const labelStyle = {
  display: 'block', fontSize: 11, color: 'var(--gray)',
  marginBottom: 4, fontWeight: 400,
}
const inputStyle = {
  width: '100%', padding: '8px 10px', fontSize: 13,
  border: '0.5px solid #e4e4e2', borderRadius: 8,
  background: 'var(--white)',
  color: 'var(--charcoal)', boxSizing: 'border-box',
}
const fieldStyle = { marginBottom: '1rem' }

export default function FittingSessionNew() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [modelList, setModelList] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    fase: 'Proto',
    data: todayISO(),
    model: '',
    model_persona: '',
    assistents: '',
    lloc: '',
    notes: '',
  })

  useEffect(() => {
    models.list({ page_size: 200 }).then(res => setModelList(res.data.results || []))
  }, [])

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = (e) => {
    e.preventDefault()
    if (!form.model) { setError(t('fitting.session.select_model')); return }
    setSubmitting(true)
    setError('')
    // XOR del target: A1 sempre apunta a un Model (cas N=1, el comú). El target
    // garment_set queda diferit fins que existeixi un endpoint de garment-sets.
    const payload = {
      fase: form.fase,
      data: form.data,
      model: Number(form.model),
      model_persona: form.model_persona,
      assistents: form.assistents,
      lloc: form.lloc,
      notes: form.notes,
    }
    fittingSessions.create(payload)
      .then(res => navigate(`/fittings/${res.data.id}`))
      .catch(() => { setError(t('fitting.session.create_error')); setSubmitting(false) })
  }

  return (
    <div style={{maxWidth: 560}}>
      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>{t('fitting.sessions.new')}</h1>
      </div>

      <Card>
        <form onSubmit={submit}>
          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem'}}>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t('fitting.session.fase')}</label>
              <select style={inputStyle} value={form.fase} onChange={e => update('fase', e.target.value)}>
                {FASES.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t('fitting.session.date')}</label>
              <input style={inputStyle} type="date" value={form.data} onChange={e => update('data', e.target.value)} />
            </div>
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>{t('fitting.session.model')}</label>
            <select style={inputStyle} value={form.model} onChange={e => update('model', e.target.value)}>
              <option value="">{t('fitting.session.select_model')}</option>
              {modelList.map(m => (
                <option key={m.id} value={m.id}>
                  {m.codi_intern || m.codi_client || `#${m.id}`}{m.nom_prenda ? ` · ${m.nom_prenda}` : ''}
                </option>
              ))}
            </select>
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>{t('fitting.session.model_persona')}</label>
            <input style={inputStyle} type="text" value={form.model_persona} onChange={e => update('model_persona', e.target.value)} />
          </div>

          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem'}}>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t('fitting.session.assistents')}</label>
              <input style={inputStyle} type="text" value={form.assistents} onChange={e => update('assistents', e.target.value)} />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>{t('fitting.session.lloc')}</label>
              <input style={inputStyle} type="text" value={form.lloc} onChange={e => update('lloc', e.target.value)} />
            </div>
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>{t('fitting.session.notes')}</label>
            <textarea style={{...inputStyle, minHeight: 80, resize: 'vertical'}} value={form.notes} onChange={e => update('notes', e.target.value)} />
          </div>

          {error && (
            <div style={{fontSize: 12, color: 'var(--err)', marginBottom: '1rem'}}>{error}</div>
          )}

          <div style={{display: 'flex', gap: '0.5rem', justifyContent: 'flex-end'}}>
            <button type="button" onClick={() => navigate('/fittings')} style={{
              background: 'var(--white)', color: 'var(--gray)',
              border: '0.5px solid #e4e4e2', borderRadius: 8,
              padding: '8px 16px', fontSize: 12, cursor: 'pointer', 
            }}>
              {t('app.cancel')}
            </button>
            <button type="submit" disabled={submitting} style={{
              background: 'var(--charcoal)', color: 'var(--white)',
              border: 'none', borderRadius: 8, padding: '8px 16px',
              fontSize: 12, cursor: submitting ? 'default' : 'pointer',
              opacity: submitting ? 0.6 : 1, 
            }}>
              {submitting ? t('fitting.session.creating') : t('fitting.session.create')}
            </button>
          </div>
        </form>
      </Card>
    </div>
  )
}
