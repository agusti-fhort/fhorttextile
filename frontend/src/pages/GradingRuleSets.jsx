import { useState, useEffect } from 'react'
import { gradingRuleSets, gradingRules } from '../api/endpoints'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'

export default function GradingRuleSets() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  const [rules, setRules] = useState({})
  const [loadingRules, setLoadingRules] = useState(false)

  useEffect(() => {
    gradingRuleSets.list({ page_size: 100 })
      .then(res => setData(res.data.results || []))
      .finally(() => setLoading(false))
  }, [])

  const toggle = (id) => {
    if (expanded === id) {
      setExpanded(null)
      return
    }
    setExpanded(id)
    if (!rules[id]) {
      setLoadingRules(true)
      gradingRules.list({ grading_rule_set: id, page_size: 500 })
        .then(res => setRules(prev => ({ ...prev, [id]: res.data.results || [] })))
        .finally(() => setLoadingRules(false))
    }
  }

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1.5rem',
      }}>
        <div>
          <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Grading Rule Sets</h1>
          <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
            {data.length} conjunts de regles de grading
          </p>
        </div>
        <button style={{
          background: 'var(--gold)', color: 'white',
          border: 'none', borderRadius: 8,
          padding: '8px 14px', fontSize: 12,
          cursor: 'pointer', fontFamily: 'var(--font)',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <i className="ti ti-plus" style={{fontSize: 14}} />
          Nou Rule Set
        </button>
      </div>

      <Card padding={0}>
        {loading ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            Carregant...
          </div>
        ) : data.length === 0 ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            No hi ha cap Grading Rule Set encara.
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr>
                {['Nom', 'Garment Group', 'Size System', 'Regles', 'Estat', ''].map(h => (
                  <th key={h} style={hStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((rs, i) => {
                const isExp = expanded === rs.id
                return (
                  <RuleSetRow
                    key={rs.id} rs={rs} i={i} isExp={isExp}
                    onToggle={toggle}
                    rules={rules[rs.id]}
                    loadingRules={loadingRules && isExp}
                    last={i === data.length - 1}
                  />
                )
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}

function RuleSetRow({ rs, isExp, onToggle, rules, loadingRules, last }) {
  return (
    <>
      <tr
        onClick={() => onToggle(rs.id)}
        style={{
          borderBottom: '0.5px solid var(--gray-l)',
          cursor: 'pointer',
        }}
      >
        <td style={{padding: '0.75rem 1rem', fontSize: 13, fontWeight: 500}}>{rs.nom}</td>
        <td style={{padding: '0.75rem 1rem', fontSize: 12, color: 'var(--gray)'}}>
          {rs.garment_group_nom || rs.garment_group || '—'}
        </td>
        <td style={{padding: '0.75rem 1rem', fontSize: 12, color: 'var(--gray)'}}>
          {rs.size_system_nom || rs.size_system || '—'}
        </td>
        <td style={{padding: '0.75rem 1rem', fontSize: 12, fontVariantNumeric: 'tabular-nums'}}>
          {rs.num_regles ?? rs.rules_count ?? '—'}
        </td>
        <td style={{padding: '0.75rem 1rem'}}>
          <Badge variant={rs.actiu ? 'ok' : 'gray'}>
            {rs.actiu ? 'Actiu' : 'Inactiu'}
          </Badge>
        </td>
        <td style={{padding: '0.75rem 1rem', textAlign: 'right', color: 'var(--gray)'}}>
          <i className={`ti ${isExp ? 'ti-chevron-up' : 'ti-chevron-down'}`} />
        </td>
      </tr>
      {isExp && (
        <tr style={{borderBottom: last ? 'none' : '0.5px solid var(--gray-l)'}}>
          <td colSpan={6} style={{padding: '0.8rem 1.4rem', background: 'var(--gray-l)'}}>
            {loadingRules ? (
              <div style={{fontSize: 12, color: 'var(--gray)', padding: '0.5rem 0'}}>
                Carregant regles...
              </div>
            ) : !rules || rules.length === 0 ? (
              <div style={{fontSize: 12, color: 'var(--gray)', padding: '0.5rem 0'}}>
                Cap regla definida en aquest set.
              </div>
            ) : (
              <table style={{width: '100%', borderCollapse: 'collapse', background: 'var(--white)', borderRadius: 8, overflow: 'hidden'}}>
                <thead>
                  <tr>
                    {['POM', 'De', 'A', 'Delta', 'Notes'].map(h => (
                      <th key={h} style={{...hStyle, padding: '0.5rem 0.8rem'}}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rules.map((r, j) => (
                    <tr key={r.id} style={{borderBottom: j < rules.length - 1 ? '0.5px solid var(--gray-l)' : 'none'}}>
                      <td style={{padding: '0.5rem 0.8rem', fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>
                        {r.pom_codi || r.pom}
                      </td>
                      <td style={{padding: '0.5rem 0.8rem', fontSize: 11}}>
                        {r.talla_desde_codi || r.talla_desde || '—'}
                      </td>
                      <td style={{padding: '0.5rem 0.8rem', fontSize: 11}}>
                        {r.talla_fins_codi || r.talla_fins || '—'}
                      </td>
                      <td style={{
                        padding: '0.5rem 0.8rem', fontSize: 11,
                        fontVariantNumeric: 'tabular-nums', fontWeight: 500,
                      }}>
                        {r.delta != null ? (r.delta > 0 ? '+' : '') + r.delta : '—'}
                      </td>
                      <td style={{padding: '0.5rem 0.8rem', fontSize: 11, color: 'var(--gray)'}}>
                        {r.notes || ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </td>
        </tr>
      )}
    </>
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
