import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { pomAlerts } from '../api/endpoints'
import client from '../api/client'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'

// `estat` filter values double as the backend query/PATCH id → kept as id; only the label is translated.
const ESTATS = ['Pendent', 'Acceptat', 'Corregit', 'Tots']
const SUBTITLE_KEY = {
  Tots: 'alerts.subtitle_all',
  Pendent: 'alerts.subtitle_pending',
  Acceptat: 'alerts.subtitle_accepted',
  Corregit: 'alerts.subtitle_corrected',
}

// `tipus` is the id (drives variant/icon style); label resolved from alerts.type.* at render.
const typeMeta = {
  desviacio:    { variant: 'warn', icon: 'ti-ruler-2' },
  fora_rang:    { variant: 'err',  icon: 'ti-alert-triangle' },
  manca_mesura: { variant: 'gate', icon: 'ti-question-mark' },
  conflicte:    { variant: 'gray', icon: 'ti-git-merge' },
}

const statusVariant = {
  'Pendent':  'warn',
  'Acceptat': 'gate',
  'Corregit': 'ok',
}

export default function Alerts() {
  const { t } = useTranslation()
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [estat, setEstat] = useState('Pendent')
  const [updating, setUpdating] = useState(null)

  const load = () => {
    setLoading(true)
    const params = estat === 'Tots' ? { page_size: 200 } : { estat, page_size: 200 }
    pomAlerts.list(params)
      .then(res => setData(res.data.results || []))
      .finally(() => setLoading(false))
  }

  useEffect(load, [estat])

  const updateStatus = async (id, nouEstat) => {
    setUpdating(id)
    try {
      await pomAlerts.update(id, { estat: nouEstat })
      load()
    } finally {
      setUpdating(null)
    }
  }

  const resolve = async (id) => {
    setUpdating(id)
    try {
      // New S11 endpoint; fallback to PATCH if not yet deployed
      await client.post(`/api/v1/alerts/${id}/resoldre/`)
        .catch(() => pomAlerts.update(id, { estat: 'Corregit' }))
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
          <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>{t('dashboard.pom_alerts')}</h1>
          <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
            {t(SUBTITLE_KEY[estat] || 'alerts.subtitle_all', { count: data.length })}
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
                cursor: 'pointer', 
              }}
            >
              {t('alerts.status.' + e, e)}
            </button>
          ))}
        </div>
      </div>

      <Card padding={0}>
        {loading ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            {t('common.loading')}
          </div>
        ) : data.length === 0 ? (
          <div style={{padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13}}>
            <i className="ti ti-circle-check" style={{fontSize: 32, color: 'var(--ok)', display: 'block', marginBottom: 12}} />
            {t('alerts.empty', { status: t('alerts.status.' + estat, estat).toLowerCase() })}
          </div>
        ) : (
          <table style={{width: '100%', borderCollapse: 'collapse'}}>
            <thead>
              <tr>
                {[
                  t('alerts.col.model'), 'POM', t('alerts.col.type'), t('alerts.col.detected'),
                  t('alerts.col.expected'), 'Z', t('alerts.col.status'), t('alerts.col.date'), '',
                ].map((h, hi) => (
                  <th key={hi} style={hStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((a, i) => {
                const meta = typeMeta[a.tipus] || typeMeta.desviacio
                const tipusId = typeMeta[a.tipus] ? a.tipus : 'desviacio'
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
                        {t('alerts.type.' + tipusId)}
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
                      <Badge variant={statusVariant[a.estat] || 'gray'}>{t('alerts.status.' + a.estat, a.estat)}</Badge>
                    </td>
                    <td style={{padding: '0.7rem 1rem', fontSize: 11, color: 'var(--gray)'}}>
                      {(a.data_creacio || a.created_at || '').slice(0, 10)}
                    </td>
                    <td style={{padding: '0.5rem 1rem', textAlign: 'right'}}>
                      {a.estat !== 'Corregit' && (
                        <div style={{display: 'flex', gap: 6, justifyContent: 'flex-end'}}>
                          {a.estat === 'Pendent' && (
                            <button
                              disabled={updating === a.id}
                              onClick={() => updateStatus(a.id, 'Acceptat')}
                              style={btnStyle('var(--gate)')}
                            >
                              {t('alerts.accept')}
                            </button>
                          )}
                          <button
                            disabled={updating === a.id}
                            onClick={() => resolve(a.id)}
                            style={btnStyle('var(--ok)')}
                          >
                            {t('alerts.resolve')}
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
  fontWeight: 500,
})
