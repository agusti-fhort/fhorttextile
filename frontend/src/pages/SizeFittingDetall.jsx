import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { sizeFittings, gradingVersions, gradedSpecLines } from '../api/endpoints'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'

const estatVariant = {
  'Pendent':         'gray',
  'BaseOberta':      'warn',
  'TallesGenerades': 'gate',
  'Tancat':          'ok',
}

export default function SizeFittingDetall() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [sf, setSf] = useState(null)
  const [versions, setVersions] = useState([])
  const [activeVersionId, setActiveVersionId] = useState(null)
  const [lines, setLines] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingLines, setLoadingLines] = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      sizeFittings.get(id),
      gradingVersions.list({ size_fitting: id, page_size: 50 }),
    ]).then(([sfRes, vRes]) => {
      setSf(sfRes.data)
      const vs = vRes.data.results || []
      setVersions(vs)
      const aprovada = vs.find(v => v.aprovada) || vs[0]
      if (aprovada) setActiveVersionId(aprovada.id)
    }).finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (!activeVersionId) return
    setLoadingLines(true)
    gradedSpecLines.list({ grading_version: activeVersionId, page_size: 500 })
      .then(res => setLines(res.data.results || []))
      .finally(() => setLoadingLines(false))
  }, [activeVersionId])

  if (loading) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
      Carregant...
    </div>
  )
  if (!sf) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--err)', fontSize: 13}}>
      Size Fitting no trobat.
    </div>
  )

  const talles = (() => {
    const set = new Map()
    lines.forEach(l => {
      const key = l.talla_id || l.size_definition || l.talla
      const label = l.talla_codi || l.talla_nom || l.talla || String(key)
      if (key != null && !set.has(key)) set.set(key, label)
    })
    return Array.from(set, ([id, label]) => ({ id, label }))
  })()

  const poms = (() => {
    const map = new Map()
    lines.forEach(l => {
      const key = l.pom_id || l.pom
      if (key == null) return
      if (!map.has(key)) {
        map.set(key, {
          id: key,
          codi: l.pom_codi || l.pom_codi_client || '',
          nom:  l.pom_nom  || l.pom_nom_client  || '',
          cells: {},
        })
      }
      const tk = l.talla_id || l.size_definition || l.talla
      map.get(key).cells[tk] = l
    })
    return Array.from(map.values())
  })()

  const cellBg = (line) => {
    if (!line) return undefined
    if (line.estat === 'error') return 'var(--err-bg)'
    if (line.estat === 'avis')  return 'var(--warn-bg)'
    return undefined
  }

  return (
    <div>
      <button onClick={() => navigate('/fitting')} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--gray)', fontSize: 12, fontFamily: 'var(--font)',
        marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <i className="ti ti-arrow-left" style={{fontSize: 14}} />
        Tornar a Size & Fitting
      </button>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr',
        gap: '1.2rem', marginBottom: '1.2rem',
      }}>
        <Card title="Informació del SF" icon="ti-ruler-2">
          {[
            ['Model',     sf.model_codi || sf.model_codi_intern || sf.model],
            ['Número',    `SF #${sf.numero ?? '—'}`],
            ['Tipus',     sf.tipus],
            ['Estat',     <Badge key="e" variant={estatVariant[sf.estat] || 'gray'}>{sf.estat}</Badge>],
            ['Data creació', sf.data_creacio || sf.created_at || '—'],
            ['Notes',     sf.notes || '—'],
          ].map(([k, v]) => (
            <div key={k} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '0.5rem 0', borderBottom: '0.5px solid var(--gray-l)',
              fontSize: 12,
            }}>
              <span style={{color: 'var(--gray)', fontWeight: 300}}>{k}</span>
              <span style={{fontWeight: 400}}>{v ?? '—'}</span>
            </div>
          ))}
          {(sf.model_id || sf.model) && (
            <button
              onClick={() => navigate(`/models/${sf.model_id || sf.model}`)}
              style={{
                marginTop: '1rem', width: '100%',
                background: 'var(--white)', color: 'var(--charcoal)',
                border: '0.5px solid #e4e4e2', borderRadius: 8,
                padding: '8px 14px', fontSize: 12,
                cursor: 'pointer', fontFamily: 'var(--font)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              }}
            >
              <i className="ti ti-external-link" style={{fontSize: 14}} />
              Veure model
            </button>
          )}
        </Card>

        <Card title={`Grading Versions (${versions.length})`} icon="ti-git-branch">
          {versions.length === 0 ? (
            <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
              Encara no hi ha versions de grading.
            </p>
          ) : versions.map(v => {
            const isActive = v.id === activeVersionId
            return (
              <div key={v.id}
                onClick={() => setActiveVersionId(v.id)}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '0.7rem 0.8rem', marginBottom: 6, cursor: 'pointer',
                  borderRadius: 8,
                  border: isActive ? '1px solid var(--gold)' : '0.5px solid var(--gray-l)',
                  background: v.aprovada ? 'var(--gold-pale)' : 'var(--white)',
                }}
              >
                <span style={{fontSize: 12, fontWeight: 500}}>
                  v{v.numero || v.versio || v.id}
                </span>
                <span style={{fontSize: 11, color: 'var(--gray)', fontWeight: 300}}>
                  {v.data_creacio || v.created_at || ''}
                </span>
                {v.aprovada && <Badge variant="gold" icon="ti-circle-check">Aprovada</Badge>}
              </div>
            )
          })}
        </Card>
      </div>

      <Card title="Línies de grading" icon="ti-table" padding={0}>
        {loadingLines ? (
          <div style={{padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            Carregant línies...
          </div>
        ) : lines.length === 0 ? (
          <div style={{padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            Cap línia de grading per a aquesta versió.
          </div>
        ) : (
          <div style={{overflowX: 'auto'}}>
            <table style={{width: '100%', borderCollapse: 'collapse', fontVariantNumeric: 'tabular-nums'}}>
              <thead>
                <tr>
                  <th style={hStyle}>POM</th>
                  <th style={hStyle}>Nom</th>
                  {talles.map(t => (
                    <th key={t.id} style={{...hStyle, textAlign: 'center'}}>{t.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {poms.map((p, i) => (
                  <tr key={p.id} style={{
                    borderBottom: i < poms.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
                  }}>
                    <td style={{padding: '0.6rem 1rem', fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>
                      {p.codi}
                    </td>
                    <td style={{padding: '0.6rem 1rem', fontSize: 12}}>
                      {p.nom}
                    </td>
                    {talles.map(t => {
                      const cell = p.cells[t.id]
                      return (
                        <td key={t.id} style={{
                          padding: '0.5rem 0.8rem',
                          fontSize: 12, textAlign: 'center',
                          background: cellBg(cell),
                        }}>
                          {cell ? (
                            <>
                              <div>{cell.valor ?? cell.valor_graduat ?? '—'}</div>
                              {(cell.delta != null && cell.delta !== 0) && (
                                <div style={{
                                  fontSize: 10,
                                  color: cell.delta > 0 ? 'var(--ok)' : 'var(--err)',
                                  fontWeight: 300,
                                }}>
                                  {cell.delta > 0 ? '+' : ''}{cell.delta}
                                </div>
                              )}
                            </>
                          ) : '—'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

const hStyle = {
  padding: '0.7rem 1rem',
  fontSize: 10, letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: 'var(--gray)', fontWeight: 400,
  borderBottom: '0.5px solid #e4e4e2',
  textAlign: 'left', whiteSpace: 'nowrap',
}
