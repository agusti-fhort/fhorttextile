import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fittings, fittingLines, sizeFittings } from '../api/endpoints'
import client from '../api/client'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import { ExportFittingCSV } from '../components/ExportButton'

const estatVariant = {
  ok:    'ok',
  avis:  'warn',
  error: 'err',
}

export default function FittingDetall() {
  const { sfId, id } = useParams()
  const navigate = useNavigate()
  const [fitting, setFitting] = useState(null)
  const [sf, setSf] = useState(null)
  const [lines, setLines] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fittings.list({ size_fitting: sfId, page_size: 100 }),
      fittingLines.list({ fitting: id, page_size: 500 }),
      sizeFittings.get(sfId),
    ]).then(([fRes, lRes, sfRes]) => {
      const found = (fRes.data.results || []).find(f => String(f.id) === String(id))
      setFitting(found || null)
      setLines(lRes.data.results || [])
      setSf(sfRes.data)
    }).finally(() => setLoading(false))
  }, [sfId, id])

  if (loading) return (
    <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
      Carregant...
    </div>
  )

  return (
    <div>
      <button onClick={() => navigate(`/fitting/${sfId}`)} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--gray)', fontSize: 12, fontFamily: 'var(--font)',
        marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <i className="ti ti-arrow-left" style={{fontSize: 14}} />
        Tornar al Size Fitting
      </button>

      <Card style={{marginBottom: '1.2rem'}}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          flexWrap: 'wrap', gap: '1rem',
        }}>
          <div>
            <div style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6}}>
              <span style={{fontSize: 13, color: 'var(--gold)', fontWeight: 500}}>
                {sf?.model_codi || sf?.model_codi_intern || ''}
              </span>
              <span style={{fontSize: 12, color: 'var(--gray)'}}>
                · SF #{sf?.numero ?? '—'}
              </span>
              {fitting?.estat && (
                <Badge variant={estatVariant[fitting.estat] || 'gray'}>{fitting.estat}</Badge>
              )}
            </div>
            <h1 style={{fontSize: 20, fontWeight: 500}}>
              Sessió fitting #{fitting?.numero ?? fitting?.id ?? id}
            </h1>
          </div>
          <div style={{display: 'flex', alignItems: 'center', gap: '2rem', fontSize: 12, flexWrap: 'wrap'}}>
            <div>
              <div style={{color: 'var(--gray)', fontWeight: 300, fontSize: 11, marginBottom: 4}}>Data fitting</div>
              <div>{fitting?.data_fitting || fitting?.data || '—'}</div>
            </div>
            <div>
              <div style={{color: 'var(--gray)', fontWeight: 300, fontSize: 11, marginBottom: 4}}>Responsable</div>
              <div>{fitting?.responsable_nom || fitting?.responsable || '—'}</div>
            </div>
            {fitting?.id && <ExportFittingCSV fittingId={fitting.id} />}
          </div>
        </div>
      </Card>

      <Card title={`Línies de fitting (${lines.length})`} icon="ti-list-details" padding={0}>
        {lines.length === 0 ? (
          <div style={{padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            Cap línia de fitting registrada.
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse', fontVariantNumeric: 'tabular-nums'}}>
            <thead>
              <tr>
                {['POM', 'Talla', 'Target', 'Mesurat', 'Δ real', 'Estat'].map(h => (
                  <th key={h} style={hStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lines.map((l, i) => {
                const delta = l.delta_real ?? l.delta
                return (
                  <tr key={l.id} style={{
                    borderBottom: i < lines.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
                  }}>
                    <td style={{padding: '0.7rem 1rem', fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>
                      {l.pom_codi || l.pom_codi_client || l.pom}
                    </td>
                    <td style={{padding: '0.7rem 1rem', fontSize: 12}}>
                      {l.talla_codi || l.talla_nom || l.talla || '—'}
                    </td>
                    <td style={{padding: '0.7rem 1rem', fontSize: 12, color: 'var(--gray)'}}>
                      {l.valor_target ?? l.target ?? '—'}
                    </td>
                    <td style={{padding: '0.7rem 1rem', fontSize: 12, fontWeight: 500}}>
                      {l.valor_mesurat ?? l.mesurat ?? '—'}
                    </td>
                    <td style={{
                      padding: '0.7rem 1rem', fontSize: 12,
                      color: delta == null ? 'var(--gray)' : delta > 0 ? 'var(--ok)' : delta < 0 ? 'var(--err)' : 'var(--charcoal)',
                      fontWeight: 500,
                    }}>
                      {delta == null ? '—' : (delta > 0 ? '+' : '') + delta}
                    </td>
                    <td style={{padding: '0.7rem 1rem'}}>
                      <Badge variant={estatVariant[l.estat] || 'gray'}>
                        {l.estat || '—'}
                      </Badge>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
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
