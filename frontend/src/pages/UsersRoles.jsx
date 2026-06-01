import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { users as usersApi, taskTypes as taskTypesApi } from '../api/endpoints'

// Tram 3 — Pantalla "Usuaris i rols" (gated manage_users).
// Peça B: matriu read-only (abast/gestió + allow-list de tasques). L'edició/filtres/bulk = Peça C.

// Columnes d'abast i gestió (capacitats efectives que retorna users.list()).
const CAPS = ['execute_tasks', 'define_tasks', 'schedule_fittings',
              'close_gates', 'configure', 'view_team_tasks', 'manage_users']

// Llenguatge visual (locked spec): crema/ambre per a la columna clau i el grup de tasques.
const CREMA = 'var(--warn-bg)'        // #faeeda
const AMBER_BORDER = '#ba7517'
const AMBER_TEXT = 'var(--warn)'      // #854f0b
const MONO = 'IBM Plex Mono, monospace'

const thBase = {
  fontFamily: MONO, fontSize: 10, fontWeight: 600, color: 'var(--text-muted)',
  padding: '8px 8px', textTransform: 'uppercase', letterSpacing: '.04em',
  whiteSpace: 'nowrap', borderBottom: '0.5px solid var(--gray-l)',
}

function ToggleCell({ on, readOnly = true, onClick, title }) {
  return (
    <td
      title={title}
      onClick={readOnly ? undefined : onClick}
      style={{
        textAlign: 'center', padding: '7px 8px', minWidth: 58,
        cursor: readOnly ? 'default' : 'pointer',
        borderBottom: '0.5px solid var(--gray-l)',
      }}
    >
      {on
        ? <i className="ti ti-check" style={{ fontSize: 14, color: 'var(--ok)' }} />
        : <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: '#e4e4e2' }} />}
    </td>
  )
}

export default function UsersRoles() {
  const { t } = useTranslation()
  const user = useAuthStore(s => s.user)
  const canManage = !!user?.capabilities?.includes('manage_users')

  const [rows, setRows] = useState([])
  const [taskTypes, setTaskTypes] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!canManage) return
    setLoading(true)
    Promise.all([usersApi.list(), taskTypesApi.list()])
      .then(([uRes, tRes]) => {
        setRows(uRes.data?.results ?? uRes.data ?? [])
        const tts = (tRes.data?.results ?? tRes.data ?? []).filter(tt => tt.active !== false)
        tts.sort((a, b) => (a.default_order ?? 0) - (b.default_order ?? 0))
        setTaskTypes(tts)
      })
      .catch(() => { setRows([]); setTaskTypes([]) })
      .finally(() => setLoading(false))
  }, [canManage])

  // user encara no carregat (fetchMe async) → evitar flash de "sense accés" als admins.
  if (user === null) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>
        {t('usersRoles.loading')}
      </div>
    )
  }

  // El backend ja enforça 403; aquí amaguem la UI per a qui no té la capacitat.
  if (!canManage) {
    return (
      <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
        <i className="ti ti-lock" style={{ fontSize: 32, color: 'var(--gray)' }} />
        <p style={{ marginTop: 12, fontSize: 13, color: 'var(--gray)' }}>
          {t('usersRoles.no_access')}
        </p>
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>{t('usersRoles.title')}</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('usersRoles.subtitle')}</p>
      </div>

      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>
          {t('usersRoles.loading')}
        </div>
      ) : rows.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>
          {t('usersRoles.empty')}
        </div>
      ) : (
        <div style={{
          overflowX: 'auto',
          border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)',
        }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12 }}>
            <thead>
              {/* Fila de grups */}
              <tr>
                <th style={{ ...thBase, position: 'sticky', left: 0, zIndex: 2, background: CREMA,
                             borderRight: `1px solid ${AMBER_BORDER}`, textAlign: 'left' }} />
                <th colSpan={CAPS.length} style={{ ...thBase, textAlign: 'center', color: 'var(--text-main)' }}>
                  {t('usersRoles.group_scope')}
                </th>
                <th colSpan={taskTypes.length} style={{ ...thBase, textAlign: 'center',
                             background: CREMA, color: AMBER_TEXT, borderLeft: `1px solid ${AMBER_BORDER}` }}>
                  {t('usersRoles.group_tasks')}
                </th>
              </tr>
              {/* Fila de columnes */}
              <tr>
                <th style={{ ...thBase, position: 'sticky', left: 0, zIndex: 2, background: CREMA,
                             borderRight: `1px solid ${AMBER_BORDER}`, textAlign: 'left', minWidth: 180 }}>
                  {t('usersRoles.col_user')}
                </th>
                {CAPS.map(cap => (
                  <th key={cap} style={{ ...thBase, textAlign: 'center' }} title={t(`usersRoles.caps.${cap}`)}>
                    {t(`usersRoles.caps.${cap}`)}
                  </th>
                ))}
                {taskTypes.map(tt => (
                  <th key={tt.id} style={{ ...thBase, textAlign: 'center', background: CREMA, color: AMBER_TEXT }}
                      title={`${tt.name} (${tt.code})`}>
                    {tt.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(u => {
                const caps = u.capabilities || []
                const allowed = u.allowed_tasks || []
                return (
                  <tr key={u.id}>
                    <td style={{ position: 'sticky', left: 0, zIndex: 1, background: CREMA,
                                 borderRight: `1px solid ${AMBER_BORDER}`, borderBottom: '0.5px solid var(--gray-l)',
                                 padding: '8px 12px', minWidth: 180 }}>
                      <div style={{ fontFamily: MONO, fontSize: 12, fontWeight: 600, color: 'var(--text-main)' }}>
                        {u.full_name || u.username}
                      </div>
                      <div style={{ fontSize: 10, color: AMBER_TEXT, marginTop: 2 }}>
                        {t('usersRoles.role')}: {u.rol_nom || '—'}
                      </div>
                    </td>
                    {CAPS.map(cap => (
                      <ToggleCell key={cap} on={caps.includes(cap)} title={t(`usersRoles.caps.${cap}`)} />
                    ))}
                    {taskTypes.map(tt => (
                      <ToggleCell key={tt.id} on={allowed.includes(tt.code)} title={tt.name} />
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
