
import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { VersionBadge } from "./VersionBadge"
import { GradingHistoryPanel } from "./GradingHistoryPanel"
import { useUnit } from "./UnitToggle"
import { ExportSizeSetCSV, ExportGradingCSV } from "./ExportButton"
import SizeSystemDrawer from "./SizeSystem/SizeSystemDrawer"
import useAuthStore from "../store/auth"
import { sizingProfiles, gradingRuleSets } from "../api/endpoints"

export function SizeSetDetail({ profileId, onClose, onRefresh }) {
  const { t } = useTranslation()
  const { unit, format } = useUnit()
  const canConfigure = !!useAuthStore(s => s.user)?.capabilities?.includes('configure')
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState({})
  const [saving, setSaving] = useState(null)
  const [msg, setMsg] = useState(null)
  const [showHistory, setShowHistory] = useState(false)
  const [restoring, setRestoring] = useState(false)
  // SIZE-2a — edició post-hoc de talles del sistema (CRUD reubicat des de /poms/sizes).
  const [editTalles, setEditTalles] = useState(false)

  const reloadProfile = () => {
    if (!profileId) return
    sizingProfiles.get(profileId)
      .then(({ data: d }) => setProfile(d))
      .catch(() => {})
  }

  useEffect(() => {
    if (!profileId) return
    setLoading(true)
    sizingProfiles.get(profileId)
      .then(({ data: d }) => { setProfile(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [profileId])

  const handleEdit = (pomCodi, currentVal) => {
    setEditing(prev => ({ ...prev, [pomCodi]: currentVal }))
  }

  const handleSave = async (pomCodi) => {
    if (!profile?.grading_rule_set?.id) return
    setSaving(pomCodi)
    const newVal = editing[pomCodi]

    if (profile.is_custom) {
      // Editar via endpoint versionat (S4)
      try {
        await gradingRuleSets.editRule(profile.grading_rule_set.id, pomCodi, { increment: parseFloat(newVal) })
        setMsg({ type: 'ok', text: t('size_library.rule_updated', { pom: pomCodi, value: newVal, unit: unit === 'INCH' ? '"' : 'cm' }) })
        setEditing(prev => { const n = {...prev}; delete n[pomCodi]; return n })
        reloadProfile()
      } catch (e) {
        if (e.response) {
          setMsg({ type: 'error', text: e.response.data?.error || t('size_library.err_save_edit') })
        } else {
          setMsg({ type: 'error', text: String(e) })
        }
      }
    } else {
      setMsg({
        type: 'warn',
        text: t('size_library.standard_clone_first'),
        pomCodi
      })
    }
    setSaving(null)
  }

  const handleRestore = async () => {
    if (!profile?.id) return
    if (!confirm(t('size_library.confirm_restore'))) return
    setRestoring(true)
    try {
      const { data: d } = await sizingProfiles.restore(profile.id)
      setMsg({ type: 'ok', text: d?.missatge || t('size_library.restored_ok') })
      reloadProfile()
      onRefresh && onRefresh()
    } catch (e) {
      if (e.response) {
        setMsg({ type: 'error', text: e.response.data?.error || t('size_library.err_restore') })
      } else {
        setMsg({ type: 'error', text: String(e) })
      }
    }
    setRestoring(false)
  }

  if (loading) return (
    <div style={{ padding: 24, fontFamily: "IBM Plex Mono, monospace", color: "var(--text-muted)" }}>
      {t('size_library.loading_detail')}
    </div>
  )
  if (!profile) return null

  const sizes = profile.size_definitions || []
  const rules = profile.grading_rules_all || profile.grading_rules_preview || []

  return (
    <div style={{ fontFamily: "IBM Plex Mono, monospace" }}>
      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: 16, paddingBottom: 12, borderBottom: "1px solid var(--border)",
      }}>
        <div>
          <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, color: "var(--text-main)" }}>
            {profile.size_system?.nom}
          </div>
          <div style={{ fontSize: 'var(--fs-body)', color: "var(--text-muted)", marginTop: 2 }}>
            {profile.target?.codi ? t(`model_wizard.target_${profile.target.codi}`, profile.target.nom_en) : profile.target?.nom_en} · {profile.construction?.codi ? t(`model_wizard.construction_${profile.construction.codi}`, profile.construction.nom_en) : profile.construction?.nom_en} · {profile.fit_type_nom}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <ExportSizeSetCSV profileId={profile.id} />
          {profile.grading_rule_set?.id && (
            <ExportGradingCSV ruleSetId={profile.grading_rule_set.id} />
          )}
          <VersionBadge
            isCustom={profile.is_custom}
            version={profile.version}
            onClick={profile.is_custom ? () => setShowHistory(true) : undefined}
          />
          {profile.is_custom && profile.grading_rule_set?.id && (
            <button
              onClick={() => setShowHistory(s => !s)}
              title={t('size_library.history_title')}
              style={{
                padding: '2px 8px', borderRadius: 3, fontSize: 'var(--fs-label)',
                background: showHistory ? '#f5e6d0' : 'var(--white)',
                color: showHistory ? 'var(--gold)' : 'var(--text-muted)',
                border: '1px solid var(--border)', cursor: 'pointer',
              }}
            >
              ⟳ {t('size_library.history')}
            </button>
          )}
          {profile.is_custom && (
            <button
              onClick={handleRestore}
              disabled={restoring}
              title={t('size_library.restore_title')}
              style={{
                padding: '2px 8px', borderRadius: 3, fontSize: 'var(--fs-label)',
                background: 'var(--white)', color: '#a32d2d',
                border: '1px solid #f0c0c0',
                cursor: restoring ? 'not-allowed' : 'pointer',
                opacity: restoring ? 0.6 : 1,
              }}
            >
              {restoring ? '...' : `↺ ${t('size_library.restore')}`}
            </button>
          )}
          {canConfigure && profile.size_system?.id && (
            <button
              onClick={() => setEditTalles(true)}
              title={t('size_library.edit_sizes_title')}
              style={{
                padding: '2px 8px', borderRadius: 3, fontSize: 'var(--fs-label)',
                background: 'var(--white)', color: 'var(--gold)',
                border: '1px solid #e0c8a0', cursor: 'pointer',
              }}
            >
              ✎ {t('size_library.edit_sizes')}
            </button>
          )}
          {onClose && (
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontSize: 'var(--fs-h2)' }}>×</button>
          )}
        </div>
      </div>

      {/* Historial expandible */}
      {showHistory && profile.grading_rule_set?.id && (
        <div style={{
          marginBottom: 16, padding: '12px 14px', borderRadius: 6,
          background: '#fdf9f5', border: '1px solid var(--border)',
        }}>
          <GradingHistoryPanel
            ruleSetId={profile.grading_rule_set.id}
            onClose={() => setShowHistory(false)}
          />
        </div>
      )}

      {/* Missatge */}
      {msg && (
        <div style={{
          padding: "6px 10px", marginBottom: 12, borderRadius: 4, fontSize: 'var(--fs-body)',
          background: msg.type === 'ok' ? "#f0f9f0" : msg.type === 'warn' ? "#fff8f0" : "#fff0f0",
          border: `1px solid ${msg.type === 'ok' ? "#c0dd97" : msg.type === 'warn' ? "#e0c8a0" : "#f09595"}`,
          color: msg.type === 'ok' ? "#3b6d11" : msg.type === 'warn' ? "var(--gold)" : "#a32d2d",
        }}>
          {msg.text}
        </div>
      )}

      {/* Taula de grading */}
      {rules.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 8 }}>
            {t('size_library.grading_rules')} — {profile.grading_rule_set?.nom}
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 'var(--fs-body)' }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--border)" }}>
                  <th style={{ textAlign: "left", padding: "5px 8px", color: "var(--text-muted)", fontWeight: 600 }}>POM</th>
                  <th style={{ textAlign: "left", padding: "5px 8px", color: "var(--text-muted)", fontWeight: 600 }}>{t('size_library.col_name')}</th>
                  <th style={{ textAlign: "center", padding: "5px 8px", color: "var(--text-muted)", fontWeight: 600 }}>{t('size_library.col_logic')}</th>
                  <th style={{ textAlign: "right", padding: "5px 8px", color: "var(--gold)", fontWeight: 600 }}>{t('size_library.col_delta', { unit: unit === 'INCH' ? 'inch' : 'cm' })}</th>
                  {profile.is_custom && <th style={{ width: 40 }}></th>}
                </tr>
              </thead>
              <tbody>
                {rules.map((rule, i) => {
                  const isEditing = rule.pom_codi in editing
                  return (
                    <tr key={i} style={{
                      borderBottom: "1px solid #f5ede0",
                      background: i % 2 === 0 ? "var(--white)" : "#fdf9f5",
                    }}>
                      <td style={{ padding: "5px 8px", color: "var(--gold)", fontWeight: 600 }}>
                        {rule.pom_codi}
                      </td>
                      <td style={{ padding: "5px 8px", color: "var(--text-main)" }}>
                        {rule.pom_nom_en}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "center", color: "var(--text-muted)" }}>
                        {rule.logica}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right" }}>
                        {isEditing ? (
                          <div style={{ display: "flex", gap: 4, justifyContent: "flex-end" }}>
                            <input
                              type="number" step="0.1"
                              value={editing[rule.pom_codi]}
                              onChange={e => setEditing(prev => ({ ...prev, [rule.pom_codi]: e.target.value }))}
                              style={{ width: 60, padding: "2px 4px", border: "1px solid var(--gold)", borderRadius: 3, fontSize: 'var(--fs-body)', textAlign: "right" }}
                            />
                            <button
                              onClick={() => handleSave(rule.pom_codi)}
                              disabled={saving === rule.pom_codi}
                              style={{ padding: "2px 6px", borderRadius: 3, fontSize: 'var(--fs-label)', background: "#f5e6d0", color: "var(--gold)", border: "1px solid var(--gold)", cursor: "pointer" }}
                            >
                              ✓
                            </button>
                            <button
                              onClick={() => setEditing(prev => { const n={...prev}; delete n[rule.pom_codi]; return n })}
                              style={{ padding: "2px 6px", borderRadius: 3, fontSize: 'var(--fs-label)', background: "var(--white)", color: "var(--text-muted)", border: "1px solid var(--border)", cursor: "pointer" }}
                            >
                              ×
                            </button>
                          </div>
                        ) : (
                          <span style={{ color: "var(--text-main)", fontWeight: 500 }}>+{format(rule.increment)}</span>
                        )}
                      </td>
                      {profile.is_custom && !isEditing && (
                        <td style={{ padding: "5px 4px", textAlign: "center" }}>
                          <button
                            onClick={() => handleEdit(rule.pom_codi, rule.increment)}
                            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontSize: 'var(--fs-body)', padding: "0 4px" }}
                            title={t('size_library.edit_increment_title')}
                          >
                            ✏
                          </button>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sizes */}
      {sizes.length > 0 && (
        <div>
          <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 8 }}>
            {t('size_library.size_run')} — {profile.size_system?.nom}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
            {sizes.map((s, i) => (
              <div key={i} style={{
                padding: "5px 10px", borderRadius: 4,
                background: "#fdf9f5", border: "1px solid var(--border)",
                fontSize: 'var(--fs-body)', textAlign: "center", minWidth: 48,
              }}>
                <div style={{ fontWeight: 600, color: "var(--text-main)" }}>{s.size_label}</div>
                {s.body_bust_cm && (
                  <div style={{ fontSize: 'var(--fs-caption)', color: "var(--text-muted)" }}>{s.body_bust_cm}cm</div>
                )}
                {s.body_height_cm && (
                  <div style={{ fontSize: 'var(--fs-caption)', color: "var(--text-muted)" }}>{s.body_height_cm}cm</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Nota si es estandard */}
      {!profile.is_custom && (
        <div style={{
          marginTop: 16, padding: "8px 12px", borderRadius: 4,
          background: "#fdf9f5", border: "1px solid var(--border)",
          fontSize: 'var(--fs-body)', color: "var(--text-muted)",
        }}>
          ℹ {t('size_library.standard_iso_note')}
        </div>
      )}

      {/* SIZE-2a — drawer d'edició de talles del sistema (CRUD reubicat des de /poms/sizes). */}
      {editTalles && profile.size_system?.id && (
        <SizeSystemDrawer
          sizeSystem={profile.size_system}
          onClose={() => { setEditTalles(false); reloadProfile() }}
          onDeleted={() => { setEditTalles(false); onRefresh && onRefresh(); onClose && onClose() }}
        />
      )}
    </div>
  )
}
