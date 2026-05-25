import { useState, useEffect } from 'react'
import { pomAlerts } from '../api/endpoints'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'

const ESTATS = ['Pendent', 'Acceptat', 'Corregit']

const tipusMeta = {
  desviacio:    { variant: 'warn', icon: 'ti-ruler-2',        label: 'Desviació' },
  fora_rang:    { variant: 'err',  icon: 'ti-alert-triangle', label: 'Fora de rang' },
  manca_mesura: { variant: 'gate', icon: 'ti-question-mark',  label: 'Manca mesura' },
  conflicte:    { variant: 'gray', icon: 'ti-git-merge',      label: 'Conflicte' },
}

const estatVariant = {
  'Pendent':  'warn',
  'Acceptat': 'gate',
  'Corregit': 'ok',
}

export default function Avisos() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [estat, setEstat] = useState('Pendent')
  const [updating, setUpdating] = useState(null)

  const load = () => {
    setLoading(true)
    pomAlerts.list({ estat, page_size: 200 })
      .then(res => setData(res.data.results || []))
      .finally(() => setLoading(false))
  }

  useEffect(load, [estat])

  const updateEstat = async (id, nouEstat) => {
    setUpdating(id)
    try {
      await pomAlerts.update(id, { estat: nouEstat })
      load()
    } finally {
      setUpdating(null)
    }
  }

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', marginBottom: '1.5rem',
      }}>
        <div>
          <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Avisos POM</h1>
          <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
            {data.length} avisos {estat.toLowerCase()}s
          </p>
        </div>
        <div style={{display: 'flex', gap: '0.5rem'}}>
          {ESTATS.map(e => (
            <button
              key={e}
              onClick={() => setEstat(e)}
              style={{
                background: estat === e ? 'var(--charcoal)' : 'var(--white)',
                color:      estat === e ? 'var(--white)' : 'var(--gray)',
                border: '0.5px solid #e4e4e2', borderRadius: 8,
                padding: '6px 14px', fontSize: 12,
                cursor: 'pointer', fontFamily: 'var(--font)',
              }}
            >
              {e}
            </button>
          ))}
        </div>
      </div>

      <Card padding={0}>
        {loading ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            Carregant...
          </div>
        ) : data.length === 0 ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            <i className="ti ti-circle-check" style={{fontSize: 32, color: 'var(--ok)', display: 'block', marginBottom: 12}} />
            Cap avís en estat {estat.toLowerCase()}.
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr>
                {['Model', 'POM', 'Tipus', 'Detectat', 'Esperat', 'Z', 'Estat', 'Data', ''].map(h => (
                  <th key={h} style={hStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((a, i) => {
                const meta = tipusMeta[a.tipus] || tipusMeta.desviacio
                return (
                  <tr key={a.id} style={{
                    borderBottom: i < data.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
                  }}>
                    <td style={{padding: '0.7rem 1rem', fontSize: 11, color: 'var(--gold)', fontWeight: 500}}>
                      {a.model_codi || a.model}
                    </td>
                    <td style={{padding: '0.7rem 1rem', fontSize: 12, fontVariantNumeric: 'tabular-nums'}}>
                      {a.pom_codi || a.pom}
                    </td>
                    <td style={{padding: '0.7rem 1rem'}}>
                      <Badge variant={meta.variant} icon={meta.icon}>
                        {meta.label}
                      </Badge>
                    </td>
                    <td style={{padding: '0.7rem 1rem', fontSize: 12, fontVariantNumeric: 'tabular-nums'}}>
                      {a.valor_detectat ?? '—'}
                    </td>
                    <td style={{padding: '0.7rem 1rem', fontSize: 12, color: 'var(--gray)', fontVariantNumeric: 'tabular-nums'}}>
                      {a.valor_esperat ?? '—'}
                    </td>
                    <td style={{padding: '0.7rem 1rem', fontSize: 12, fontVariantNumeric: 'tabular-nums'}}>
                      {a.z_score != null ? Number(a.z_score).toFixed(2) : '—'}
                    </td>
                    <td style={{padding: '0.7rem 1rem'}}>
                      <Badge variant={estatVariant[a.estat] || 'gray'}>{a.estat}</Badge>
                    </td>
                    <td style={{padding: '0.7rem 1rem', fontSize: 11, color: 'var(--gray)'}}>
                      {(a.data_creacio || a.created_at || '').slice(0, 10)}
                    </td>
                    <td style={{padding: '0.5rem 1rem', textAlign: 'right'}}>
                      {a.estat === 'Pendent' && (
                        <div style={{display: 'flex', gap: 6, justifyContent: 'flex-end'}}>
                          <button
                            disabled={updating === a.id}
                            onClick={() => updateEstat(a.id, 'Acceptat')}
                            style={btnStyle('var(--gate)')}
                          >
                            Acceptar
                          </button>
                          <button
                            disabled={updating === a.id}
                            onClick={() => updateEstat(a.id, 'Corregit')}
                            style={btnStyle('var(--ok)')}
                          >
                            Corregit
                          </button>
                        </div>
                      )}
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

const btnStyle = (color) => ({
  background: 'var(--white)',
  color,
  border: `0.5px solid ${color}`,
  borderRadius: 6,
  padding: '4px 10px',
  fontSize: 11,
  cursor: 'pointer',
  fontFamily: 'var(--font)',
  fontWeight: 500,
})
