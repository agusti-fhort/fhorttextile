import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { users as usersApi, taskTypes as taskTypesApi } from '../api/endpoints'

// Tram 3 — Pantalla "Usuaris i rols" (gated manage_users).
// Peça C: matriu editable (capacitats → permisos.grant/revoke; tasques → permisos.tasks) +
// filtres (search/role/can_task) + selecció i bulk amb confirmació i recompte.

const CAPS = ['execute_tasks', 'define_tasks', 'schedule_fittings',
              'close_gates', 'configure', 'view_team_tasks', 'manage_users']
const ROLES = ['technician', 'product_manager', 'manager', 'admin']

const CREMA = 'var(--warn-bg)'        // #faeeda
const AMBER_BORDER = '#ba7517'
const AMBER_TEXT = 'var(--warn)'      // #854f0b
const MONO = 'IBM Plex Mono, monospace'

const thBase = {
  fontFamily: MONO, fontSize: 10, fontWeight: 600, color: 'var(--text-muted)',
  padding: '8px 8px', textTransform: 'uppercase', letterSpacing: '.04em',
  whiteSpace: 'nowrap', borderBottom: '0.5px solid var(--gray-l)',
}
const inputS = {
  fontFamily: MONO, fontSize: 12, padding: '6px 10px',
  border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)',
  color: 'var(--text-main)',
}

function ToggleCell({ on, readOnly, onClick, title }) {
  return (
    <td
      title={title}
      onClick={readOnly ? undefined : onClick}
      style={{
        textAlign: 'center', padding: '7px 8px', minWidth: 58,
        cursor: readOnly ? 'default' : 'pointer',
        opacity: readOnly ? 0.55 : 1,
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
  const me = useAuthStore(s => s.user)
  const canManage = !!me?.capabilities?.includes('manage_users')

  const [rows, setRows] = useState([])
  const [taskTypes, setTaskTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(new Set())
  const [confirmState, setConfirmState] = useState(null)   // { action, value, label }
  const [feedback, setFeedback] = useState(null)           // { type, text }
  const [newUserOpen, setNewUserOpen] = useState(false)    // modal "Nou usuari"

  // Filtres
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [canTask, setCanTask] = useState('')

  const fetchUsers = useCallback(() => {
    const params = {}
    if (search.trim()) params.search = search.trim()
    if (role) params.role = role
    if (canTask) params.can_task = canTask
    setLoading(true)
    usersApi.list(params)
      .then(res => setRows(res.data?.results ?? res.data ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
    setSelected(new Set())   // la selecció no sobreviu a un canvi de filtre
  }, [search, role, canTask])

  // Tipus de tasca (un sol cop).
  useEffect(() => {
    if (!canManage) return
    taskTypesApi.list()
      .then(res => {
        const tts = (res.data?.results ?? res.data ?? []).filter(tt => tt.active !== false)
        tts.sort((a, b) => (a.default_order ?? 0) - (b.default_order ?? 0))
        setTaskTypes(tts)
      })
      .catch(() => setTaskTypes([]))
  }, [canManage])

  // Usuaris (debounce per a la cerca).
  useEffect(() => {
    if (!canManage) return
    const id = setTimeout(fetchUsers, 300)
    return () => clearTimeout(id)
  }, [canManage, fetchUsers])

  // --- Edició per cel·la: capacitats → grant/revoke, tasques → tasks ---
  function patchUser(id, permisos) {
    return usersApi.patch(id, { permisos })
      .then(res => {
        setRows(rs => rs.map(r => (r.id === id ? { ...r, ...res.data } : r)))
        setFeedback(null)
      })
      .catch(() => setFeedback({ type: 'err', text: t('usersRoles.patch_error') }))
  }

  function toggleCap(u, cap) {
    const p = { ...(u.permisos || {}) }
    const grant = new Set(p.grant || [])
    const revoke = new Set(p.revoke || [])
    if ((u.capabilities || []).includes(cap)) {   // efectiu ON → forçar OFF
      revoke.add(cap); grant.delete(cap)
    } else {                                       // efectiu OFF → forçar ON
      grant.add(cap); revoke.delete(cap)
    }
    p.grant = [...grant]; p.revoke = [...revoke]
    patchUser(u.id, p)
  }

  function toggleTask(u, code) {
    const p = { ...(u.permisos || {}) }
    const tasks = new Set(p.tasks || [])
    if ((u.allowed_tasks || []).includes(code)) tasks.delete(code)
    else tasks.add(code)
    p.tasks = [...tasks]
    patchUser(u.id, p)
  }

  // --- Selecció ---
  const allSelected = rows.length > 0 && rows.every(r => selected.has(r.id))
  function toggleSelectAll() {
    setSelected(allSelected ? new Set() : new Set(rows.map(r => r.id)))
  }
  function toggleSelect(id) {
    setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  // --- Bulk: prepara confirmació amb recompte ---
  function askBulk(action, value, label) {
    if (selected.size === 0) return
    setConfirmState({ action, value, label })
  }
  function applyBulk() {
    const { action, value } = confirmState
    usersApi.bulk({ user_ids: [...selected], action, value })
      .then(res => {
        setFeedback({ type: 'ok', text: t('usersRoles.bulk_done', { updated: res.data?.updated ?? 0 }) })
        setConfirmState(null)
        fetchUsers()
      })
      .catch(() => { setFeedback({ type: 'err', text: t('usersRoles.patch_error') }); setConfirmState(null) })
  }

  if (me == null) {
    return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{t('usersRoles.loading')}</div>
  }
  if (!canManage) {
    return (
      <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
        <i className="ti ti-lock" style={{ fontSize: 32, color: 'var(--gray)' }} />
        <p style={{ marginTop: 12, fontSize: 13, color: 'var(--gray)' }}>{t('usersRoles.no_access')}</p>
      </div>
    )
  }

  return (
    <div style={{ minWidth: 0, maxWidth: '100%' }}>
      <div style={{ marginBottom: '1.2rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>{t('usersRoles.title')}</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('usersRoles.subtitle')}</p>
      </div>

      {/* Barra de filtres */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder={t('usersRoles.search_ph')} style={{ ...inputS, minWidth: 200 }}
        />
        <select value={role} onChange={e => setRole(e.target.value)} style={inputS}>
          <option value="">{t('usersRoles.all_roles')}</option>
          {ROLES.map(r => <option key={r} value={r}>{t(`usersRoles.roles.${r}`)}</option>)}
        </select>
        <select value={canTask} onChange={e => setCanTask(e.target.value)} style={inputS}>
          <option value="">{t('usersRoles.all_tasks')}</option>
          {taskTypes.map(tt => <option key={tt.id} value={tt.code}>{tt.name}</option>)}
        </select>
        {/* Botó "Nou usuari" (la pàgina ja està gated per manage_users). */}
        <button onClick={() => setNewUserOpen(true)} style={{
          marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6,
          background: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 6,
          padding: '7px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer', fontFamily: MONO,
        }}>
          <i className="ti ti-plus" style={{ fontSize: 14 }} />
          {t('usersRoles.new_user')}
        </button>
      </div>

      {/* Barra d'accions massives (apareix amb selecció) */}
      {selected.size > 0 && (
        <BulkBar
          t={t} count={selected.size} roles={ROLES} taskTypes={taskTypes}
          onSetRole={(r) => askBulk('set_role', r, `${t('usersRoles.bulk_role')}: ${t(`usersRoles.roles.${r}`)}`)}
          onActive={(on) => askBulk('set_active', on, on ? t('usersRoles.bulk_activate') : t('usersRoles.bulk_deactivate'))}
          onTask={(code, on) => {
            const nm = taskTypes.find(x => x.code === code)?.name || code
            askBulk('set_task', { code, on }, `${on ? t('usersRoles.bulk_task_add') : t('usersRoles.bulk_task_remove')}: ${nm}`)
          }}
        />
      )}

      {feedback && (
        <div style={{
          fontSize: 12, padding: '8px 12px', borderRadius: 6, marginBottom: 12,
          background: feedback.type === 'ok' ? 'var(--ok-bg)' : 'var(--err-bg)',
          color: feedback.type === 'ok' ? 'var(--ok)' : 'var(--err)',
        }}>{feedback.text}</div>
      )}

      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{t('usersRoles.loading')}</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{t('usersRoles.empty')}</div>
      ) : (
        <div style={{ overflowX: 'auto', maxWidth: '100%', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12 }}>
            <thead>
              <tr>
                <th style={{ ...thBase, position: 'sticky', left: 0, zIndex: 2, background: CREMA,
                             borderRight: `1px solid ${AMBER_BORDER}`, textAlign: 'left' }}>
                  <input type="checkbox" checked={allSelected} onChange={toggleSelectAll} title={t('usersRoles.select_all')} />
                </th>
                <th colSpan={CAPS.length} style={{ ...thBase, textAlign: 'center', color: 'var(--text-main)' }}>
                  {t('usersRoles.group_scope')}
                </th>
                <th colSpan={taskTypes.length} style={{ ...thBase, textAlign: 'center', background: CREMA,
                             color: AMBER_TEXT, borderLeft: `1px solid ${AMBER_BORDER}` }}>
                  {t('usersRoles.group_tasks')}
                </th>
              </tr>
              <tr>
                <th style={{ ...thBase, position: 'sticky', left: 0, zIndex: 2, background: CREMA,
                             borderRight: `1px solid ${AMBER_BORDER}`, textAlign: 'left', minWidth: 200 }}>
                  {t('usersRoles.col_user')}
                </th>
                {CAPS.map(cap => (
                  <th key={cap} style={{ ...thBase, textAlign: 'center' }} title={t(`usersRoles.caps.${cap}`)}>
                    {t(`usersRoles.caps.${cap}`)}
                  </th>
                ))}
                {taskTypes.map(tt => (
                  <th key={tt.id} style={{ ...thBase, textAlign: 'center', background: CREMA, color: AMBER_TEXT }}
                      title={`${tt.name} (${tt.code})`}>{tt.name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(u => {
                const caps = u.capabilities || []
                const allowed = u.allowed_tasks || []
                const isSelf = u.id === me.id
                return (
                  <tr key={u.id}>
                    <td style={{ position: 'sticky', left: 0, zIndex: 1, background: CREMA,
                                 borderRight: `1px solid ${AMBER_BORDER}`, borderBottom: '0.5px solid var(--gray-l)',
                                 padding: '8px 12px', minWidth: 200 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <input type="checkbox" checked={selected.has(u.id)} onChange={() => toggleSelect(u.id)} />
                        <div>
                          <div style={{ fontFamily: MONO, fontSize: 12, fontWeight: 600, color: 'var(--text-main)' }}>
                            {u.full_name || u.username}
                          </div>
                          <div style={{ fontSize: 10, color: AMBER_TEXT, marginTop: 2 }}>
                            {t('usersRoles.role')}: {u.rol_nom || '—'}
                          </div>
                        </div>
                      </div>
                    </td>
                    {CAPS.map(cap => {
                      // Salvaguarda: no et pots treure manage_users a tu mateix (auto-bloqueig).
                      const lockSelf = isSelf && cap === 'manage_users'
                      return (
                        <ToggleCell
                          key={cap} on={caps.includes(cap)} readOnly={lockSelf}
                          title={lockSelf ? t('usersRoles.self_lock') : t(`usersRoles.caps.${cap}`)}
                          onClick={() => toggleCap(u, cap)}
                        />
                      )
                    })}
                    {taskTypes.map(tt => (
                      <ToggleCell key={tt.id} on={allowed.includes(tt.code)} title={tt.name}
                                  onClick={() => toggleTask(u, tt.code)} />
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal de confirmació amb recompte */}
      {confirmState && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
        }} onClick={() => setConfirmState(null)}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--white)', borderRadius: 12, padding: '1.5rem',
            maxWidth: 400, width: '90%', boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
          }}>
            <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>{t('usersRoles.confirm_title')}</h2>
            <p style={{ fontSize: 13, color: 'var(--text-main)', lineHeight: 1.5, marginBottom: 18 }}>
              {t('usersRoles.confirm_msg', { action: confirmState.label, count: selected.size })}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button onClick={() => setConfirmState(null)} style={{
                ...inputS, cursor: 'pointer', border: '0.5px solid var(--gray-l)', color: 'var(--gray)',
              }}>{t('usersRoles.cancel')}</button>
              <button onClick={applyBulk} style={{
                ...inputS, cursor: 'pointer', border: 'none', background: 'var(--gold)', color: '#fff', fontWeight: 600,
              }}>{t('usersRoles.confirm')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal "Nou usuari" (alta amb rol; els toggles fins s'afinen després a la matriu) */}
      {newUserOpen && (
        <NewUserModal
          t={t} roles={ROLES}
          onClose={() => setNewUserOpen(false)}
          onCreated={(u) => {
            setNewUserOpen(false)
            setFeedback({ type: 'ok', text: t('usersRoles.nu_created', { name: u.full_name || u.username }) })
            fetchUsers()
          }}
        />
      )}
    </div>
  )
}

function BulkBar({ t, count, roles, taskTypes, onSetRole, onActive, onTask }) {
  const [taskCode, setTaskCode] = useState('')
  const selS = { ...{
    fontFamily: MONO, fontSize: 12, padding: '5px 8px',
    border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)',
  } }
  const btn = {
    fontFamily: MONO, fontSize: 12, padding: '5px 10px', borderRadius: 6,
    border: '0.5px solid var(--gray-l)', background: 'var(--white)', cursor: 'pointer', color: 'var(--text-main)',
  }
  return (
    <div style={{
      display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center',
      padding: '10px 12px', marginBottom: 12, borderRadius: 8,
      background: CREMA, border: `0.5px solid ${AMBER_BORDER}`,
    }}>
      <span style={{ fontFamily: MONO, fontSize: 12, fontWeight: 600, color: AMBER_TEXT }}>
        {t('usersRoles.selected', { n: count })}
      </span>
      {/* set_role */}
      <select defaultValue="" onChange={e => { if (e.target.value) { onSetRole(e.target.value); e.target.value = '' } }} style={selS}>
        <option value="">{t('usersRoles.bulk_role')}…</option>
        {roles.map(r => <option key={r} value={r}>{t(`usersRoles.roles.${r}`)}</option>)}
      </select>
      {/* set_active */}
      <button style={btn} onClick={() => onActive(true)}>{t('usersRoles.bulk_activate')}</button>
      <button style={btn} onClick={() => onActive(false)}>{t('usersRoles.bulk_deactivate')}</button>
      {/* set_task */}
      <select value={taskCode} onChange={e => setTaskCode(e.target.value)} style={selS}>
        <option value="">{t('usersRoles.pick_task')}</option>
        {taskTypes.map(tt => <option key={tt.id} value={tt.code}>{tt.name}</option>)}
      </select>
      <button style={btn} disabled={!taskCode} onClick={() => onTask(taskCode, true)}>{t('usersRoles.bulk_task_add')}</button>
      <button style={btn} disabled={!taskCode} onClick={() => onTask(taskCode, false)}>{t('usersRoles.bulk_task_remove')}</button>
    </div>
  )
}

// Extreu un missatge llegible de la resposta d'error del backend (DRF: {field:[...]} / {error} / {detail}).
function firstError(data, fallback) {
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (data.error) return data.error
  if (data.detail) return data.detail
  const k = Object.keys(data)[0]
  if (!k) return fallback
  const v = data[k]
  return Array.isArray(v) ? v[0] : String(v)
}

function NewUserModal({ t, roles, onClose, onCreated }) {
  const [form, setForm] = useState({ username: '', email: '', nom_complet: '', rol_nom: 'technician', password: '' })
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const fieldS = {
    fontFamily: MONO, fontSize: 13, padding: '8px 10px', width: '100%', boxSizing: 'border-box',
    border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)', color: 'var(--text-main)',
  }
  const labelS = { fontSize: 11, color: AMBER_TEXT, fontFamily: MONO, marginBottom: 4, display: 'block' }

  function submit() {
    // Validació client mínima; la resta (únic, rol vàlid…) la valida el backend.
    if (!form.username.trim() || !form.password) { setError(t('usersRoles.nu_required')); return }
    setSaving(true); setError(null)
    usersApi.create({
      username: form.username.trim(), email: form.email.trim(),
      nom_complet: form.nom_complet.trim(), rol_nom: form.rol_nom, password: form.password,
    })
      .then(res => onCreated(res.data))
      .catch(err => setError(firstError(err?.response?.data, t('usersRoles.patch_error'))))
      .finally(() => setSaving(false))
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--white)', borderRadius: 12, padding: '1.5rem',
        maxWidth: 420, width: '90%', boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
      }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>{t('usersRoles.nu_title')}</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={labelS}>{t('usersRoles.nu_username')} *</label>
            <input value={form.username} onChange={e => set('username', e.target.value)} style={fieldS} autoFocus />
          </div>
          <div>
            <label style={labelS}>{t('usersRoles.nu_nom_complet')}</label>
            <input value={form.nom_complet} onChange={e => set('nom_complet', e.target.value)} style={fieldS} />
          </div>
          <div>
            <label style={labelS}>{t('usersRoles.nu_email')}</label>
            <input type="email" value={form.email} onChange={e => set('email', e.target.value)} style={fieldS} />
          </div>
          <div>
            <label style={labelS}>{t('usersRoles.role')}</label>
            <select value={form.rol_nom} onChange={e => set('rol_nom', e.target.value)} style={fieldS}>
              {roles.map(r => <option key={r} value={r}>{t(`usersRoles.roles.${r}`)}</option>)}
            </select>
          </div>
          <div>
            <label style={labelS}>{t('usersRoles.nu_password')} *</label>
            <input type="password" value={form.password} onChange={e => set('password', e.target.value)} style={fieldS} />
            <div style={{ fontSize: 10, color: 'var(--gray)', marginTop: 4 }}>{t('usersRoles.nu_password_hint')}</div>
          </div>
        </div>
        {error && (
          <div style={{ marginTop: 12, fontSize: 12, padding: '8px 10px', borderRadius: 6,
                        background: 'var(--err-bg)', color: 'var(--err)' }}>{error}</div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 18 }}>
          <button onClick={onClose} disabled={saving} style={{
            fontFamily: MONO, fontSize: 13, padding: '8px 14px', borderRadius: 6,
            cursor: 'pointer', border: '0.5px solid var(--gray-l)', background: 'var(--white)', color: 'var(--gray)',
          }}>{t('usersRoles.cancel')}</button>
          <button onClick={submit} disabled={saving} style={{
            fontFamily: MONO, fontSize: 13, padding: '8px 16px', borderRadius: 6,
            cursor: saving ? 'default' : 'pointer', border: 'none',
            background: 'var(--gold)', color: '#fff', fontWeight: 600, opacity: saving ? 0.6 : 1,
          }}>{t('usersRoles.nu_create')}</button>
        </div>
      </div>
    </div>
  )
}
