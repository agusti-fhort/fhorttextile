import { useState, useEffect } from 'react'
import { poms, sizeSystems, me } from '../api/endpoints'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'

const TABS = [
  { key: 'perfil',   label: 'Perfil',   icon: 'ti-building' },
  { key: 'poms',     label: 'POMs',     icon: 'ti-ruler-2' },
  { key: 'talles',   label: 'Talles',   icon: 'ti-arrows-maximize' },
  { key: 'usuaris',  label: 'Usuaris',  icon: 'ti-users' },
]

export default function Configuracio() {
  const [tab, setTab] = useState('perfil')

  return (
    <div>
      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Configuració</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          Paràmetres del tenant
        </p>
      </div>

      <div style={{
        display: 'flex', gap: 4, marginBottom: '1.2rem',
        borderBottom: '0.5px solid #e4e4e2',
      }}>
        {TABS.map(t => {
          const active = tab === t.key
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: active ? '2px solid var(--gold)' : '2px solid transparent',
                color: active ? 'var(--charcoal)' : 'var(--gray)',
                padding: '10px 18px',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'var(--font)',
                fontWeight: active ? 500 : 400,
                display: 'flex', alignItems: 'center', gap: 6,
                marginBottom: -1,
              }}
            >
              <i className={`ti ${t.icon}`} style={{fontSize: 14}} />
              {t.label}
            </button>
          )
        })}
      </div>

      {tab === 'perfil'  && <TabPerfil />}
      {tab === 'poms'    && <TabPoms />}
      {tab === 'talles'  && <TabTalles />}
      {tab === 'usuaris' && <TabUsuaris />}
    </div>
  )
}

function TabPerfil() {
  const [profile, setProfile] = useState(null)
  useEffect(() => {
    me.get().then(res => setProfile(res.data)).catch(() => {})
  }, [])

  return (
    <Card title="Perfil del tenant" icon="ti-building">
      {[
        ['Tenant',  profile?.tenant_nom || profile?.tenant || 'FHORT'],
        ['Unitats', 'cm'],
        ['Idioma',  'Català'],
      ].map(([k, v]) => (
        <div key={k} style={{
          display: 'flex', justifyContent: 'space-between',
          padding: '0.6rem 0', borderBottom: '0.5px solid var(--gray-l)',
          fontSize: 12,
        }}>
          <span style={{color: 'var(--gray)', fontWeight: 300}}>{k}</span>
          <span style={{fontWeight: 400}}>{v}</span>
        </div>
      ))}
    </Card>
  )
}

function TabPoms() {
  const [data, setData] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    poms.list({ page_size: 500 })
      .then(res => {
        setData(res.data.results || [])
        setTotal(res.data.count || 0)
      })
      .finally(() => setLoading(false))
  }, [])

  const perCategoria = data.reduce((acc, p) => {
    const c = p.categoria || 'Sense categoria'
    acc[c] = (acc[c] || 0) + 1
    return acc
  }, {})

  return (
    <Card title={`Catàleg POM (${total})`} icon="ti-ruler-2">
      {loading ? (
        <div style={{fontSize: 13, color: 'var(--gray)'}}>Carregant...</div>
      ) : (
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem'}}>
          {Object.entries(perCategoria).map(([cat, n]) => (
            <div key={cat} style={{
              padding: '1rem 1.2rem',
              border: '0.5px solid var(--gray-l)',
              borderRadius: 8,
            }}>
              <div style={{fontSize: 11, color: 'var(--gray)', marginBottom: 4}}>{cat}</div>
              <div style={{fontSize: 22, fontWeight: 500, color: 'var(--gold)'}}>{n}</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

function TabTalles() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    sizeSystems.list({ page_size: 100 })
      .then(res => setData(res.data.results || []))
      .finally(() => setLoading(false))
  }, [])

  return (
    <Card title={`Size Systems (${data.length})`} icon="ti-arrows-maximize" padding={0}>
      {loading ? (
        <div style={{padding: '2rem', fontSize: 13, color: 'var(--gray)', textAlign: 'center'}}>
          Carregant...
        </div>
      ) : data.length === 0 ? (
        <div style={{padding: '2rem', fontSize: 13, color: 'var(--gray)', textAlign: 'center'}}>
          Sense Size Systems
        </div>
      ) : data.map((s, i) => (
        <div key={s.id} style={{
          padding: '0.9rem 1.4rem',
          borderBottom: i < data.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{fontSize: 13, fontWeight: 500}}>{s.nom}</div>
            <div style={{fontSize: 11, color: 'var(--gray)'}}>Codi: {s.codi || '—'}</div>
          </div>
          <Badge variant={s.actiu ? 'ok' : 'gray'}>{s.actiu ? 'Actiu' : 'Inactiu'}</Badge>
        </div>
      ))}
    </Card>
  )
}

function TabUsuaris() {
  const [me_data, setMe] = useState(null)
  useEffect(() => {
    me.get().then(res => setMe(res.data)).catch(() => {})
  }, [])

  const users = me_data ? [me_data] : []

  return (
    <Card title={`Usuaris (${users.length})`} icon="ti-users" padding={0}>
      {users.length === 0 ? (
        <div style={{padding: '2rem', fontSize: 13, color: 'var(--gray)', textAlign: 'center'}}>
          Sense usuaris
        </div>
      ) : (
        <table style={{width: '100%', borderCollapse: 'collapse'}}>
          <thead>
            <tr>
              {['Nom', 'Rol', 'Cost/h', 'Estat'].map(h => (
                <th key={h} style={hStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u, i) => (
              <tr key={u.id} style={{
                borderBottom: i < users.length - 1 ? '0.5px solid var(--gray-l)' : 'none',
              }}>
                <td style={{padding: '0.75rem 1rem', fontSize: 13}}>
                  <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
                    <span style={{
                      width: 28, height: 28, borderRadius: '50%',
                      background: u.color_avatar || 'var(--gold)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: 'white', fontSize: 11, fontWeight: 500,
                    }}>
                      {(u.nom_complet || u.username || '?').slice(0, 2).toUpperCase()}
                    </span>
                    {u.nom_complet || u.username}
                  </div>
                </td>
                <td style={{padding: '0.75rem 1rem', fontSize: 12, color: 'var(--gray)'}}>
                  {u.rol_nom || '—'}
                </td>
                <td style={{padding: '0.75rem 1rem', fontSize: 12, fontVariantNumeric: 'tabular-nums'}}>
                  {u.cost_hora != null ? `${u.cost_hora} €` : '—'}
                </td>
                <td style={{padding: '0.75rem 1rem'}}>
                  <Badge variant={u.actiu ? 'ok' : 'gray'}>{u.actiu ? 'Actiu' : 'Inactiu'}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
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
