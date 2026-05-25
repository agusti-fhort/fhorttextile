import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { models, sizeFittings } from '../api/endpoints'

const TIPUS = [
  { value: 'Proto',   label: 'Proto'   },
  { value: 'Fit',     label: 'Fit'     },
  { value: 'SizeSet', label: 'SizeSet' },
  { value: 'PP',      label: 'PP'      },
  { value: 'TOP',     label: 'TOP'     },
]

export default function NouSizeFitting() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [model, setModel] = useState(null)
  const [existing, setExisting] = useState([])
  const [tipus, setTipus] = useState('Proto')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      models.get(id),
      sizeFittings.list({ model: id, page_size: 100 }),
    ]).then(([mRes, sfRes]) => {
      setModel(mRes.data)
      setExisting(sfRes.data.results || [])
    }).finally(() => setLoading(false))
  }, [id])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const res = await sizeFittings.create({
        model: Number(id),
        tipus,
        notes,
      })
      navigate(`/fitting/${res.data.id}`)
    } catch (err) {
      const msg = err.response?.data ? JSON.stringify(err.response.data) : 'Error desconegut'
      setError(`No s'ha pogut crear el Size Fitting: ${msg}`)
      setSubmitting(false)
    }
  }

  if (loading) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
      Carregant...
    </div>
  )
  if (!model) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--err)', fontSize: 13}}>
      Model no trobat.
    </div>
  )

  const pare = existing[existing.length - 1]

  return (
    <div>
      <button onClick={() => navigate(`/models/${id}`)} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--gray)', fontSize: 12, fontFamily: 'var(--font)',
        marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <i className="ti ti-arrow-left" style={{fontSize: 14}} />
        Tornar al model
      </button>

      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Nou Size Fitting</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          Crea un Size Fitting per al model
        </p>
      </div>

      <div style={{
        background: 'var(--gold-pale)',
        border: '0.5px solid rgba(194,122,42,0.3)',
        borderRadius: 12,
        padding: '1rem 1.4rem',
        marginBottom: '1.2rem',
        display: 'flex', gap: '2rem', flexWrap: 'wrap',
      }}>
        <div>
          <div style={{fontSize: 11, color: 'var(--gray)', marginBottom: 4}}>Model</div>
          <div style={{fontSize: 13, fontWeight: 500, color: 'var(--gold)'}}>
            {model.codi_intern}
          </div>
        </div>
        <div>
          <div style={{fontSize: 11, color: 'var(--gray)', marginBottom: 4}}>Nom</div>
          <div style={{fontSize: 13}}>{model.nom_prenda}</div>
        </div>
        <div>
          <div style={{fontSize: 11, color: 'var(--gray)', marginBottom: 4}}>Fase actual</div>
          <div style={{fontSize: 13, color: 'var(--gate)'}}>{model.fase_actual || '—'}</div>
        </div>
        {pare && (
          <div>
            <div style={{fontSize: 11, color: 'var(--gray)', marginBottom: 4}}>SF pare</div>
            <div style={{fontSize: 13}}>SF #{pare.numero} · {pare.tipus}</div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} style={{
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 12,
        padding: '1.5rem 1.8rem',
        maxWidth: 720,
      }}>
        <label style={{display: 'flex', flexDirection: 'column', gap: 6, marginBottom: '1.2rem'}}>
          <span style={{fontSize: 11, color: 'var(--gray)'}}>Tipus *</span>
          <select
            value={tipus}
            onChange={e => setTipus(e.target.value)}
            style={{
              background: 'var(--white)',
              border: '0.5px solid #e4e4e2',
              borderRadius: 8,
              padding: '8px 12px',
              fontSize: 12,
              fontFamily: 'var(--font)',
              outline: 'none',
            }}
          >
            {TIPUS.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>

        <label style={{display: 'flex', flexDirection: 'column', gap: 6}}>
          <span style={{fontSize: 11, color: 'var(--gray)'}}>Notes</span>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={5}
            style={{
              background: 'var(--white)',
              border: '0.5px solid #e4e4e2',
              borderRadius: 8,
              padding: '8px 12px',
              fontSize: 12,
              fontFamily: 'var(--font)',
              outline: 'none',
              resize: 'vertical',
            }}
          />
        </label>

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
          <button type="button" onClick={() => navigate(`/models/${id}`)} style={{
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
            <i className="ti ti-ruler-2" style={{fontSize: 14}} />
            {submitting ? 'Creant...' : 'Crear SF'}
          </button>
        </div>
      </form>
    </div>
  )
}
