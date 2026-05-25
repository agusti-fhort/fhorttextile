import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { models, tasks, fittings } from '../api/endpoints'

const FASES = ['Proto', 'Fit', 'SizeSet', 'PP', 'TOP']

const estatColors = {
  'Nou':        { bg: 'var(--gray-l)',   color: 'var(--gray)'  },
  'EnCurs':     { bg: 'var(--warn-bg)',  color: 'var(--warn)'  },
  'EnRevisió':  { bg: 'var(--gate-bg)', color: 'var(--gate)'  },
  'Tancat':     { bg: 'var(--ok-bg)',    color: 'var(--ok)'    },
}

function Badge({ estat }) {
  const s = estatColors[estat] || estatColors['Nou']
  return (
    <span style={{...s, fontSize: 12, padding: '4px 10px', borderRadius: 6}}>
      {estat}
    </span>
  )
}

function Pipeline({ faseActual }) {
  const idx = FASES.indexOf(faseActual)
  return (
    <div style={{display: 'flex', gap: 0, marginTop: '0.5rem'}}>
      {FASES.map((f, i) => {
        const done   = i < idx
        const active = i === idx
        return (
          <div key={f} style={{
            flex: 1,
            background: done ? 'var(--ok)' : active ? 'var(--gold)' : 'var(--gray-l)',
            color: (done || active) ? 'white' : 'var(--gray)',
            padding: '8px 12px',
            fontSize: 11, fontWeight: active ? 500 : 300,
            borderRight: i < FASES.length - 1 ? '1px solid white' : 'none',
            textAlign: 'center',
            borderRadius: i === 0 ? '8px 0 0 8px' : i === FASES.length - 1 ? '0 8px 8px 0' : 0,
          }}>
            {f}
          </div>
        )
      })}
    </div>
  )
}

export default function ModelDetall() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [model, setModel] = useState(null)
  const [modelTasques, setModelTasques] = useState([])
  const [sizeFittings, setSizeFittings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      models.get(id),
      tasks.listByModel(id),
      fittings.listByModel(id),
    ]).then(([mRes, tRes, fRes]) => {
      setModel(mRes.data)
      setModelTasques(tRes.data.results || [])
      setSizeFittings(fRes.data.results || [])
    }).finally(() => setLoading(false))
  }, [id])

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

  return (
    <div>
      {/* Capçalera */}
      <div style={{marginBottom: '1.5rem'}}>
        <button
          onClick={() => navigate('/models')}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--gray)', fontSize: 12, fontFamily: 'var(--font)',
            marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          <i className="ti ti-arrow-left" style={{fontSize: 14}} />
          Tornar a models
        </button>
        <div style={{display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between'}}>
          <div>
            <div style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6}}>
              <span style={{fontSize: 13, color: 'var(--gold)', fontWeight: 500}}>
                {model.codi_intern}
              </span>
              <Badge estat={model.estat} />
            </div>
            <h1 style={{fontSize: 22, fontWeight: 500, marginBottom: 4}}>
              {model.nom_prenda}
            </h1>
            <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
              Ref. client: {model.codi_client || '—'} · Temporada: {model.temporada} {model.any} · Responsable: {model.responsable || '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Pipeline */}
      <div style={{
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 12,
        padding: '1.2rem 1.4rem',
        marginBottom: '1.2rem',
      }}>
        <div style={{fontSize: 11, color: 'var(--gray)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6}}>
          <i className="ti ti-route" style={{color: 'var(--gold)'}} />
          Pipeline tècnic
        </div>
        <Pipeline faseActual={model.fase_actual} />
      </div>

      {/* Grid info + fittings */}
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.2rem', marginBottom: '1.2rem'}}>

        {/* Info tècnica */}
        <div style={{
          background: 'var(--white)',
          border: '0.5px solid #e4e4e2',
          borderRadius: 12,
          padding: '1.2rem 1.4rem',
        }}>
          <div style={{fontSize: 11, color: 'var(--gray)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: 6}}>
            <i className="ti ti-info-circle" style={{color: 'var(--gold)'}} />
            Informació tècnica
          </div>
          {[
            ['Garment Type', model.garment_type],
            ['Fit Type', model.fit_type],
            ['Temporada', `${model.temporada} ${model.any}`],
            ['Prioritat', model.prioritat],
            ['Data entrada', model.data_entrada],
            ['Data objectiu', model.data_objectiu || '—'],
          ].map(([label, val]) => (
            <div key={label} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '0.5rem 0',
              borderBottom: '0.5px solid var(--gray-l)',
              fontSize: 12,
            }}>
              <span style={{color: 'var(--gray)', fontWeight: 300}}>{label}</span>
              <span style={{fontWeight: 400}}>{val || '—'}</span>
            </div>
          ))}
        </div>

        {/* Size Fittings */}
        <div style={{
          background: 'var(--white)',
          border: '0.5px solid #e4e4e2',
          borderRadius: 12,
          padding: '1.2rem 1.4rem',
        }}>
          <div style={{fontSize: 11, color: 'var(--gray)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: 6}}>
            <i className="ti ti-ruler-2" style={{color: 'var(--gold)'}} />
            Size Fittings ({sizeFittings.length})
          </div>
          {sizeFittings.length === 0 ? (
            <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
              Encara no hi ha Size Fittings per a aquest model.
            </p>
          ) : sizeFittings.map(sf => (
            <div key={sf.id} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '0.6rem 0', borderBottom: '0.5px solid var(--gray-l)',
            }}>
              <span style={{fontSize: 12}}>SF #{sf.numero} · {sf.tipus}</span>
              <span style={{
                fontSize: 11, padding: '2px 8px', borderRadius: 6,
                background: 'var(--gate-bg)', color: 'var(--gate)',
              }}>{sf.estat}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Tasques */}
      <div style={{
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 12,
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '1rem 1.4rem',
          borderBottom: '0.5px solid #e4e4e2',
          display: 'flex', alignItems: 'center', gap: '0.8rem',
        }}>
          <i className="ti ti-checklist" style={{fontSize: 18, color: 'var(--gold)'}} />
          <span style={{fontSize: 14, fontWeight: 500}}>Tasques ({modelTasques.length})</span>
        </div>
        {modelTasques.length === 0 ? (
          <div style={{padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            Encara no hi ha tasques assignades a aquest model.
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr>
                {['Ordre', 'Tasca', 'Fase', 'Estat', 'Temps', 'Gate'].map(h => (
                  <th key={h} style={{
                    padding: '0.7rem 1rem', fontSize: 10,
                    letterSpacing: '0.1em', textTransform: 'uppercase',
                    color: 'var(--gray)', fontWeight: 400,
                    borderBottom: '0.5px solid #e4e4e2', textAlign: 'left',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {modelTasques.map((t, i) => (
                <tr key={t.id} style={{
                  borderBottom: i < modelTasques.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
                }}>
                  <td style={{padding: '0.7rem 1rem', fontSize: 12, color: 'var(--gray)'}}>{t.ordre}</td>
                  <td style={{padding: '0.7rem 1rem', fontSize: 13}}>{t.nom_tasca || t.tasca}</td>
                  <td style={{padding: '0.7rem 1rem', fontSize: 12, color: 'var(--gate)'}}>{t.fase || '—'}</td>
                  <td style={{padding: '0.7rem 1rem'}}>
                    <span style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 6,
                      background: estatColors[t.estat]?.bg || 'var(--gray-l)',
                      color: estatColors[t.estat]?.color || 'var(--gray)',
                    }}>{t.estat}</span>
                  </td>
                  <td style={{padding: '0.7rem 1rem', fontSize: 12}}>{t.minuts_reals ? `${t.minuts_reals}min` : '—'}</td>
                  <td style={{padding: '0.7rem 1rem'}}>
                    {t.es_gate && (
                      <span style={{
                        fontSize: 10, padding: '2px 7px', borderRadius: 4,
                        background: 'var(--gate-bg)', color: 'var(--gate)',
                        fontWeight: 500,
                      }}>GATE</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
