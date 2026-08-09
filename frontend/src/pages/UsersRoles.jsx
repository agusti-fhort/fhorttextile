import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { users as usersApi, taskTypes as taskTypesApi } from '../api/endpoints'
import { taskTypeLabel } from '../utils/taskType'
import PageMenu from '../components/ui/PageMenu'
import { apagat, botoPri } from '../components/ui/buttons'
import { useEnumeracio } from '../utils/vocabulariDominiFont'

// Tram 3 — Pantalla "Usuaris i rols" (gated manage_users).
// Peça C: matriu editable (capacitats → permisos.grant/revoke; tasques → permisos.tasks) +
// filtres (search/role/can_task) + selecció i bulk amb confirmació i recompte.

// LES DUES ENUMERACIONS SE'N VAN DEL CLIENT (llei 1). `CAPS` i `ROLES` eren la còpia de
// `fhort/accounts/capabilities.py` — un fitxer que es declara a si mateix «font de veritat
// única»— i ara surten de `/vocabulari/` → `capacitats` · `rols`.
// ⚠️ L'ORDRE DE `capacitats` ÉS L'ORDRE DE LES COLUMNES d'aquesta matriu, i per això la font
// del backend ha hagut de ser una TUPLA: `ALL_CAPABILITIES` és un `frozenset` i no en té. Amb
// la còpia local, el dia que hi entrés una capacitat nova la matriu no l'hauria ensenyada mai.
//
// 🎨 I LA PANTALLA DEIXA DE SER TARONJA. `FIXA_BG`/`'var(--text-soft)'` eren `--warn-bg`/`--warn` —el
// SEMÀFOR— fent de fons de la columna fixa, de les capçaleres del bloc de tasques i de TOTES
// les etiquetes de formulari; i `FIXA_LINE` era un hex (`#ba7517`) que no és a cap paleta.
// La §1 reserva el taronja a la DADA («la dada porta el color»): aquí no hi havia cap dada
// taronja, hi havia una pantalla pintada de taronja. La columna fixa passa al fons de pàgina
// —que és el que la distingeix del panell blanc que hi llisca per sota— i els filets, a `--line`.
const MONO = 'IBM Plex Mono, monospace'
const FIXA_BG = 'var(--bg-page)'      // fons de la columna/capçalera FIXA (no és una selecció)
const FIXA_LINE = 'var(--line)'       // el filet que separa el bloc fix del que es desplaça

const thBase = {
  fontFamily: MONO, fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-soft)',
  padding: '8px 8px', textTransform: 'uppercase', letterSpacing: '.08em',
  whiteSpace: 'nowrap', borderBottom: '1px solid var(--line-soft)',
}
const inputS = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 10px',
  border: '1px solid var(--line-soft)', borderRadius: 'var(--r-ctrl)', background: 'var(--panel)',
  color: 'var(--text-main)',
}

// Cel·la de la matriu: NOMÉS visual (read-only). ✓ = actiu, punt gris = inactiu.
function ToggleCell({ on, title }) {
  return (
    <td
      title={title}
      style={{
        textAlign: 'center', padding: '7px 8px', minWidth: 58,
        borderBottom: '1px solid var(--line-soft)',
      }}
    >
      {on
        ? <i className="ti ti-check" style={{ fontSize: 14, color: 'var(--ok)' }} />
        : <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--line)' }} />}
    </td>
  )
}

// Cercle de color d'assignació (color_avatar). Fallback --gold si null.
function ColorDot({ color, size = 16 }) {
  return (
    <span style={{
      display: 'inline-block', width: size, height: size, borderRadius: '50%',
      background: color || 'var(--gold)', border: '1px solid var(--line-soft)',
      boxSizing: 'border-box', verticalAlign: 'middle',
    }} />
  )
}

export default function UsersRoles() {
  const { t } = useTranslation()
  // Sense vocabulari, ni la matriu ofereix columnes ni el select ofereix rols: no en sabem cap,
  // i inventar-ne seria replantar la còpia que aquest tram acaba de matar.
  const { codis: CAPS } = useEnumeracio('capacitats')
  const { codis: ROLES } = useEnumeracio('rols')
  const me = useAuthStore(s => s.user)
  const canManage = !!me?.capabilities?.includes('manage_users')

  const [rows, setRows] = useState([])
  const [taskTypes, setTaskTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(new Set())
  const [confirmState, setConfirmState] = useState(null)   // { action, value, label }
  const [feedback, setFeedback] = useState(null)           // { type, text }
  const [newUserOpen, setNewUserOpen] = useState(false)    // modal "Nou usuari"
  const [editUser, setEditUser] = useState(null)           // fila en edició (null = modal tancat)
  const [resetModal, setResetModal] = useState(null)       // { name, url } | { name, loading } | null

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

  // --- PATCH genèric des del modal d'edició (camps modificats) ---
  // Retorna la promesa; el modal gestiona el seu propi spinner/error inline.
  function patchUser(id, data) {
    return usersApi.patch(id, data).then(res => {
      setRows(rs => rs.map(r => (r.id === id ? { ...r, ...res.data } : r)))
      return res.data
    })
  }

  // --- Selecció ---
  const allSelected = rows.length > 0 && rows.every(r => selected.has(r.id))
  function toggleSelectAll() {
    setSelected(allSelected ? new Set() : new Set(rows.map(r => r.id)))
  }
  function toggleSelect(id) {
    setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  }

  // --- Generar enllaç de recuperació de contrasenya (gated manage_users, ja ho és la pàgina) ---
  function genResetLink(u) {
    const name = u.full_name || u.username
    setResetModal({ name, loading: true })
    usersApi.resetLink(u.id)
      .then(res => setResetModal({ name, url: res.data?.url || '' }))
      .catch(() => { setResetModal(null); setFeedback({ type: 'err', text: t('usersRoles.rl_error') }) })
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
    return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-soft)', fontSize: 'var(--fs-body)' }}>{t('usersRoles.loading')}</div>
  }
  if (!canManage) {
    return (
      <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-faint)', fontStyle: 'italic', fontFamily: MONO }}>{t('usersRoles.no_access')}</p>
      </div>
    )
  }

  return (
    <>
      {/* §8b · MENÚ DE PANTALLA, i l'acció hi puja. «Nou usuari» era un botó de fons DAURAT PLE
          a l'extrem de la barra de filtres: el daurat és marca, no acció (§5), i a més barrejava
          l'acció amb els filtres. Al menú deixa de ser botó i deixa de ser de color (§8e). */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu
          backTo="/"
          backTitle={t('usersRoles.back_title')}
          items={[{ key: 'nou', label: t('usersRoles.new_user'), onClick: () => setNewUserOpen(true) }]}
        />
      </div>

    <div style={{ minWidth: 0, maxWidth: '100%', paddingTop: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500, marginBottom: 4, color: 'var(--text-main)' }}>{t('usersRoles.title')}</h1>
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontFamily: MONO }}>{t('usersRoles.subtitle')}</p>
      </div>

      {/* Barra de filtres */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder={t('usersRoles.search_ph')} style={{ ...inputS, minWidth: 200 }}
        />
        <select value={role} onChange={e => setRole(e.target.value)} style={inputS}>
          <option value="">{t('usersRoles.all_roles')}</option>
          {(ROLES || []).map(r => <option key={r} value={r}>{t(`usersRoles.roles.${r}`)}</option>)}
        </select>
        <select value={canTask} onChange={e => setCanTask(e.target.value)} style={inputS}>
          <option value="">{t('usersRoles.all_tasks')}</option>
          {taskTypes.map(tt => <option key={tt.id} value={tt.code}>{taskTypeLabel(t, tt.code, tt.name)}</option>)}
        </select>
      </div>

      {/* Barra d'accions massives (apareix amb selecció) */}
      {selected.size > 0 && (
        <BulkBar
          t={t} count={selected.size} roles={ROLES || []} taskTypes={taskTypes}
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
          fontSize: 'var(--fs-body)', padding: '8px 12px', borderRadius: 'var(--r-ctrl)', marginBottom: 12,
          background: feedback.type === 'ok' ? 'var(--ok-bg)' : 'var(--err-bg)',
          color: feedback.type === 'ok' ? 'var(--ok)' : 'var(--err)',
        }}>{feedback.text}</div>
      )}

      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-soft)', fontSize: 'var(--fs-body)' }}>{t('usersRoles.loading')}</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-soft)', fontSize: 'var(--fs-body)' }}>{t('usersRoles.empty')}</div>
      ) : (
        <div style={{ overflowX: 'auto', maxWidth: '100%', border: '1px solid var(--line-soft)', borderRadius: 'var(--r-card)', background: 'var(--panel)' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 'var(--fs-body)' }}>
            <thead>
              <tr>
                <th style={{ ...thBase, position: 'sticky', left: 0, zIndex: 2, background: FIXA_BG,
                             borderRight: `1px solid ${FIXA_LINE}`, textAlign: 'left' }}>
                  <input type="checkbox" checked={allSelected} onChange={toggleSelectAll} title={t('usersRoles.select_all')} />
                </th>
                <th style={thBase} />
                <th colSpan={(CAPS || []).length} style={{ ...thBase, textAlign: 'center', color: 'var(--text-main)' }}>
                  {t('usersRoles.group_scope')}
                </th>
                <th colSpan={taskTypes.length} style={{ ...thBase, textAlign: 'center', background: FIXA_BG,
                             color: 'var(--text-soft)', borderLeft: `1px solid ${FIXA_LINE}` }}>
                  {t('usersRoles.group_tasks')}
                </th>
                <th style={thBase} />
              </tr>
              <tr>
                <th style={{ ...thBase, position: 'sticky', left: 0, zIndex: 2, background: FIXA_BG,
                             borderRight: `1px solid ${FIXA_LINE}`, textAlign: 'left', minWidth: 200 }}>
                  {t('usersRoles.col_user')}
                </th>
                <th style={{ ...thBase, textAlign: 'center' }}>{t('usersRoles.col_color')}</th>
                {(CAPS || []).map(cap => (
                  <th key={cap} style={{ ...thBase, textAlign: 'center' }} title={t(`usersRoles.caps.${cap}`)}>
                    {t(`usersRoles.caps.${cap}`)}
                  </th>
                ))}
                {taskTypes.map(tt => (
                  <th key={tt.id} style={{ ...thBase, textAlign: 'center', background: FIXA_BG, color: 'var(--text-soft)' }}
                      title={`${taskTypeLabel(t, tt.code, tt.name)} (${tt.code})`}>{taskTypeLabel(t, tt.code, tt.name)}</th>
                ))}
                <th style={{ ...thBase, textAlign: 'center' }}>{t('usersRoles.col_action')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(u => {
                const caps = u.capabilities || []
                const allowed = u.allowed_tasks || []
                return (
                  <tr key={u.id}>
                    <td style={{ position: 'sticky', left: 0, zIndex: 1, background: FIXA_BG,
                                 borderRight: `1px solid ${FIXA_LINE}`, borderBottom: '1px solid var(--line-soft)',
                                 padding: '8px 12px', minWidth: 200 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <input type="checkbox" checked={selected.has(u.id)} onChange={() => toggleSelect(u.id)} />
                        <div>
                          <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)' }}>
                            {u.full_name || u.username}
                          </div>
                          <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)', marginTop: 2 }}>
                            {t('usersRoles.role')}: {u.rol_nom || '—'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td style={{ textAlign: 'center', padding: '7px 8px', borderBottom: '1px solid var(--line-soft)' }}>
                      <ColorDot color={u.color_avatar} />
                    </td>
                    {(CAPS || []).map(cap => (
                      <ToggleCell key={cap} on={caps.includes(cap)} title={t(`usersRoles.caps.${cap}`)} />
                    ))}
                    {taskTypes.map(tt => (
                      <ToggleCell key={tt.id} on={allowed.includes(tt.code)} title={taskTypeLabel(t, tt.code, tt.name)} />
                    ))}
                    <td style={{ textAlign: 'center', padding: '7px 10px', borderBottom: '1px solid var(--line-soft)' }}>
                      {canManage && (
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                          <button onClick={() => setEditUser(u)} title={t('usersRoles.edit')} style={{
                            display: 'inline-flex', alignItems: 'center', gap: 5,
                            fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '5px 10px', borderRadius: 'var(--r-ctrl)',
                            border: '1px solid var(--line-soft)', background: 'var(--panel)',
                            color: 'var(--text-main)', cursor: 'pointer', whiteSpace: 'nowrap',
                          }}>
                            <i className="ti ti-pencil" style={{ fontSize: 13 }} />
                            {t('usersRoles.edit')}
                          </button>
                          <button onClick={() => genResetLink(u)} title={t('usersRoles.reset_link')} style={{
                            display: 'inline-flex', alignItems: 'center', gap: 5,
                            fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '5px 10px', borderRadius: 'var(--r-ctrl)',
                            border: '1px solid var(--line-soft)', background: 'var(--panel)',
                            color: 'var(--text-main)', cursor: 'pointer', whiteSpace: 'nowrap',
                          }}>
                            <i className="ti ti-key" style={{ fontSize: 13 }} />
                            {t('usersRoles.reset_link')}
                          </button>
                        </div>
                      )}
                    </td>
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
            background: 'var(--panel)', borderRadius: 'var(--r-card)', padding: '1.5rem',
            maxWidth: 400, width: '90%', boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 10 }}>{t('usersRoles.confirm_title')}</h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', lineHeight: 1.5, marginBottom: 18 }}>
              {t('usersRoles.confirm_msg', { action: confirmState.label, count: selected.size })}
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button onClick={() => setConfirmState(null)} style={{
                ...inputS, cursor: 'pointer', border: '1px solid var(--line-soft)', color: 'var(--text-soft)',
              }}>{t('usersRoles.cancel')}</button>
              <button onClick={applyBulk} style={{
                ...inputS, cursor: 'pointer', border: 'none', background: 'var(--accio)', color: 'var(--white)', fontWeight: 600,
              }}>{t('usersRoles.confirm')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal "Nou usuari" (alta amb rol; els toggles fins s'afinen després a la matriu) */}
      {newUserOpen && (
        <NewUserModal
          t={t} roles={ROLES || []}
          onClose={() => setNewUserOpen(false)}
          onCreated={(u) => {
            setNewUserOpen(false)
            setFeedback({ type: 'ok', text: t('usersRoles.nu_created', { name: u.full_name || u.username }) })
            fetchUsers()
          }}
        />
      )}

      {/* Modal d'edició per usuari (rol + tasques + nom complet + color) */}
      {editUser && (
        <UserEditModal
          t={t} user={editUser} roles={ROLES || []} taskTypes={taskTypes}
          onClose={() => setEditUser(null)}
          onSave={(diff) => patchUser(editUser.id, diff)}
          onSaved={() => {
            setEditUser(null)
            setFeedback({ type: 'ok', text: t('usersRoles.ue_updated') })
          }}
        />
      )}

      {/* Modal "Enllaç de recuperació" (URL copiable; no s'envia correu) */}
      {resetModal && (
        <ResetLinkModal t={t} data={resetModal} onClose={() => setResetModal(null)} />
      )}
    </div>
    </>
  )
}

function ResetLinkModal({ t, data, onClose }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    if (!data.url) return
    navigator.clipboard?.writeText(data.url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => {})
  }
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--panel)', borderRadius: 'var(--r-card)', padding: '1.5rem',
        maxWidth: 480, width: '92%', boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
      }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 12 }}>
          {t('usersRoles.rl_title')} — {data.name}
        </h2>
        {data.loading ? (
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('usersRoles.loading')}</p>
        ) : (
          <>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input readOnly value={data.url} onFocus={e => e.target.select()} style={{
                flex: 1, fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '8px 10px',
                border: '1px solid var(--line-soft)', borderRadius: 'var(--r-ctrl)', background: 'var(--line)',
                color: 'var(--text-main)',
              }} />
              <button onClick={copy} style={{
                fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '8px 14px', borderRadius: 'var(--r-ctrl)',
                border: 'none', background: 'var(--accio)', color: 'var(--white)', fontWeight: 600,
                cursor: 'pointer', whiteSpace: 'nowrap',
              }}>{copied ? t('usersRoles.rl_copied') : t('usersRoles.rl_copy')}</button>
            </div>
            <p style={{ marginTop: 12, fontSize: 'var(--fs-label)', color: 'var(--text-soft)', lineHeight: 1.5 }}>
              {t('usersRoles.rl_note')}
            </p>
          </>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 18 }}>
          <button onClick={onClose} style={{
            fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '8px 14px', borderRadius: 'var(--r-ctrl)',
            cursor: 'pointer', border: '1px solid var(--line-soft)', background: 'var(--panel)', color: 'var(--text-soft)',
          }}>{t('usersRoles.cancel')}</button>
        </div>
      </div>
    </div>
  )
}

function BulkBar({ t, count, roles, taskTypes, onSetRole, onActive, onTask }) {
  const [taskCode, setTaskCode] = useState('')
  const selS = { ...{
    fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '5px 8px',
    border: '1px solid var(--line-soft)', borderRadius: 'var(--r-ctrl)', background: 'var(--panel)',
  } }
  const btn = {
    fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '5px 10px', borderRadius: 'var(--r-ctrl)',
    border: '1px solid var(--line-soft)', background: 'var(--panel)', cursor: 'pointer', color: 'var(--text-main)',
  }
  return (
    <div style={{
      display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center',
      padding: '10px 12px', marginBottom: 12, borderRadius: 'var(--r-ctrl)',
      background: FIXA_BG, border: `1px solid ${FIXA_LINE}`,
    }}>
      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-soft)' }}>
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
        {taskTypes.map(tt => <option key={tt.id} value={tt.code}>{taskTypeLabel(t, tt.code, tt.name)}</option>)}
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
    fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '8px 10px', width: '100%', boxSizing: 'border-box',
    border: '1px solid var(--line-soft)', borderRadius: 'var(--r-ctrl)', background: 'var(--panel)', color: 'var(--text-main)',
  }
  const labelS = { fontSize: 'var(--fs-body)', color: 'var(--text-soft)', fontFamily: MONO, marginBottom: 4, display: 'block' }

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
        background: 'var(--panel)', borderRadius: 'var(--r-card)', padding: '1.5rem',
        maxWidth: 420, width: '90%', boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
      }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 14 }}>{t('usersRoles.nu_title')}</h2>
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
            <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)', marginTop: 4 }}>{t('usersRoles.nu_password_hint')}</div>
          </div>
        </div>
        {error && (
          <div style={{ marginTop: 12, fontSize: 'var(--fs-body)', padding: '8px 10px', borderRadius: 'var(--r-ctrl)',
                        background: 'var(--err-bg)', color: 'var(--err)' }}>{error}</div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 18 }}>
          <button onClick={onClose} disabled={saving} style={{
            fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '8px 14px', borderRadius: 'var(--r-ctrl)',
            cursor: 'pointer', border: '1px solid var(--line-soft)', background: 'var(--panel)', color: 'var(--text-soft)',
          }}>{t('usersRoles.cancel')}</button>
          {/* §5.7 · el deshabilitat baixa el FONS, no la tinta. La ratificació C2 va portar
              aquests dos botons de daurat ple a blau —que és el correcte—, però l'`opacity`
              que ja hi havia es va quedar: apaga també el text i el deixa per sota d'AA. */}
          <button onClick={submit} disabled={saving}
            style={{ ...botoPri, ...(saving ? apagat : null) }}>{t('usersRoles.nu_create')}</button>
        </div>
      </div>
    </div>
  )
}

function UserEditModal({ t, user, roles, taskTypes, onClose, onSave, onSaved }) {
  // Estat inicial = còpia local dels camps editables (no mutem la fila/store directament).
  const initial = {
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    rol_nom: user.rol_nom || 'technician',
    color_avatar: user.color_avatar || '#888888',
    tasks: user.permisos?.tasks || [],
  }
  const [form, setForm] = useState(initial)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  // is_admin (viu): rol admin O bé manage_users dins les capacitats efectives de la fila.
  // Si és admin, les tasques es gestionen via el rol → no editables (bypass total al backend).
  const isAdmin = form.rol_nom === 'admin' || (user.capabilities || []).includes('manage_users')
  const tasksSet = new Set(form.tasks)
  function toggleTask(code) {
    setForm(f => {
      const s = new Set(f.tasks)
      s.has(code) ? s.delete(code) : s.add(code)
      return { ...f, tasks: [...s] }
    })
  }

  const fieldS = {
    fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '8px 10px', width: '100%', boxSizing: 'border-box',
    border: '1px solid var(--line-soft)', borderRadius: 'var(--r-ctrl)', background: 'var(--panel)', color: 'var(--text-main)',
  }
  const labelS = { fontSize: 'var(--fs-body)', color: 'var(--text-soft)', fontFamily: MONO, marginBottom: 4, display: 'block' }

  function submit() {
    // PATCH parcial: només els camps modificats vs l'estat inicial.
    const diff = {}
    if (form.first_name !== initial.first_name) diff.first_name = form.first_name
    if (form.last_name !== initial.last_name) diff.last_name = form.last_name
    if (form.rol_nom !== initial.rol_nom) diff.rol_nom = form.rol_nom
    if (form.color_avatar !== initial.color_avatar) diff.color_avatar = form.color_avatar
    if (!isAdmin) {
      const a = [...initial.tasks].sort().join(','), b = [...form.tasks].sort().join(',')
      if (a !== b) diff.permisos = { ...(user.permisos || {}), tasks: form.tasks }
    }
    if (Object.keys(diff).length === 0) { onClose(); return }
    setSaving(true); setError(null)
    onSave(diff)
      .then(() => onSaved())
      .catch(err => { setSaving(false); setError(firstError(err?.response?.data, t('usersRoles.patch_error'))) })
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--panel)', borderRadius: 'var(--r-card)', padding: '1.5rem',
        maxWidth: 460, width: '92%', maxHeight: '88vh', overflowY: 'auto',
        boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
      }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 14 }}>
          {t('usersRoles.ue_title')} — {user.full_name || user.username}
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ flex: 1 }}>
              <label style={labelS}>{t('usersRoles.ue_first_name')}</label>
              <input value={form.first_name} onChange={e => set('first_name', e.target.value)} style={fieldS} autoFocus />
            </div>
            <div style={{ flex: 1 }}>
              <label style={labelS}>{t('usersRoles.ue_last_name')}</label>
              <input value={form.last_name} onChange={e => set('last_name', e.target.value)} style={fieldS} />
            </div>
          </div>
          <div>
            <label style={labelS}>{t('usersRoles.role')}</label>
            <select value={form.rol_nom} onChange={e => set('rol_nom', e.target.value)} style={fieldS}>
              {roles.map(r => <option key={r} value={r}>{t(`usersRoles.roles.${r}`)}</option>)}
            </select>
          </div>
          <div>
            <label style={labelS}>{t('usersRoles.ue_color')}</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <input type="color" value={form.color_avatar}
                     onChange={e => set('color_avatar', e.target.value)}
                     style={{ width: 48, height: 32, padding: 0, border: '1px solid var(--line-soft)',
                              borderRadius: 'var(--r-ctrl)', background: 'var(--panel)', cursor: 'pointer' }} />
              <ColorDot color={form.color_avatar} size={24} />
              <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{form.color_avatar}</span>
            </div>
          </div>
          <div>
            <label style={labelS}>{t('usersRoles.ue_tasks')}</label>
            {isAdmin && (
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginBottom: 8 }}>
                {t('usersRoles.ue_bypass_note')}
              </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 14px' }}>
              {taskTypes.map(tt => {
                const checked = isAdmin ? true : tasksSet.has(tt.code)
                return (
                  <label key={tt.id} style={{
                    display: 'flex', alignItems: 'center', gap: 7, fontFamily: MONO, fontSize: 'var(--fs-body)',
                    color: 'var(--text-main)', cursor: isAdmin ? 'default' : 'pointer',
                    opacity: isAdmin ? 0.6 : 1,
                  }}>
                    <input type="checkbox" checked={checked} disabled={isAdmin}
                           onChange={() => toggleTask(tt.code)} />
                    {taskTypeLabel(t, tt.code, tt.name)}
                  </label>
                )
              })}
            </div>
          </div>
        </div>
        {error && (
          <div style={{ marginTop: 12, fontSize: 'var(--fs-body)', padding: '8px 10px', borderRadius: 'var(--r-ctrl)',
                        background: 'var(--err-bg)', color: 'var(--err)' }}>{error}</div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 18 }}>
          <button onClick={onClose} disabled={saving} style={{
            fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '8px 14px', borderRadius: 'var(--r-ctrl)',
            cursor: 'pointer', border: '1px solid var(--line-soft)', background: 'var(--panel)', color: 'var(--text-soft)',
          }}>{t('usersRoles.cancel')}</button>
          {/* §5.7 · el deshabilitat baixa el FONS, no la tinta. La ratificació C2 va portar
              aquests dos botons de daurat ple a blau —que és el correcte—, però l'`opacity`
              que ja hi havia es va quedar: apaga també el text i el deixa per sota d'AA. */}
          <button onClick={submit} disabled={saving}
            style={{ ...botoPri, ...(saving ? apagat : null) }}>{saving ? t('usersRoles.ue_saving') : t('usersRoles.ue_save')}</button>
        </div>
      </div>
    </div>
  )
}
