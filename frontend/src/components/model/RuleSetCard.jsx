import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { gradingRuleSets, garmentGroups, models } from '../../api/endpoints'
import AxesSelector from '../grading/AxesSelector'
import RuleSetPicker from '../grading/RuleSetPicker'

// P3 — Picker de ruleset AL MODEL (SPEC §1.6: ruleset visible (P8) + CANVIABLE). Reusa AxesSelector +
// RuleSetPicker (els mateixos de la plantilla d'ítem; no es dupliquen). En triar, PATCH update-step2
// {grading_rule_set_id}: el backend re-materialitza les ModelGradingRule (config) — NO toca el motor
// de propagació (generate_graded_specs). Eixos inicials derivats del ruleset vigent del model.
export default function RuleSetCard({ model, onChanged }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [ruleSets, setRuleSets] = useState([])
  const [ggCodiById, setGgCodiById] = useState({})
  const [axes, setAxes] = useState({ target: model?.target ?? null, construction: model?.construction ?? null, fit: null, garmentGroup: null })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    let alive = true
    Promise.all([gradingRuleSets.list({ page_size: 200 }), garmentGroups.list({ page_size: 200 })])
      .then(([rsRes, ggRes]) => {
        if (!alive) return
        const rs = rsRes.data?.results ?? (Array.isArray(rsRes.data) ? rsRes.data : [])
        const gg = ggRes.data?.results ?? (Array.isArray(ggRes.data) ? ggRes.data : [])
        const map = {}; gg.forEach(g => { map[g.id] = g.codi })
        setRuleSets(rs); setGgCodiById(map)
        const rsObj = rs.find(r => r.id === model?.grading_rule_set)
        if (rsObj) setAxes({
          target: rsObj.targets_codis?.[0] ?? model?.target ?? null,
          construction: rsObj.construction_codi ?? model?.construction ?? null,
          fit: rsObj.fit_type_codi ?? null,
          garmentGroup: rsObj.garment_group ? (map[rsObj.garment_group] ?? null) : null,
        })
      }).catch(() => {})
    return () => { alive = false }
  }, [model?.id, model?.grading_rule_set, model?.target, model?.construction])

  const onPick = (rs) => {
    if (!rs || rs.id === model?.grading_rule_set) return
    setSaving(true); setMsg(null)
    models.updateStep2(model.id, { grading_rule_set_id: rs.id })
      .then(() => { setMsg({ type: 'ok', text: t('model_sheet.ruleset_changed') }); onChanged?.() })
      .catch(() => setMsg({ type: 'err', text: t('model_sheet.ruleset_err') }))
      .finally(() => setSaving(false))
  }

  return (
    <div style={{ border: '0.5px solid var(--border)', borderRadius: 8, padding: '12px 16px', marginBottom: 16, background: 'var(--bg-card)' }}>
      <div style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)', marginBottom: 8 }}>
        {t('dependency.ruleset')}
      </div>
      <AxesSelector ruleSets={ruleSets} value={axes} onChange={setAxes} />
      <div style={{ marginTop: 8, opacity: saving ? 0.6 : 1, pointerEvents: saving ? 'none' : 'auto' }}>
        <RuleSetPicker
          ruleSets={ruleSets}
          garmentGroupCodiById={ggCodiById}
          axes={axes}
          selectedId={model?.grading_rule_set ?? null}
          actionLabel={t('model_sheet.use_ruleset')}
          onPick={onPick}
          onEmptyAction={() => navigate('/poms/grading')}
          emptyActionLabel={t('item_authoring.create_ruleset')}
        />
      </div>
      {msg && (
        <div style={{ marginTop: 8, fontSize: 'var(--fs-body)', color: msg.type === 'ok' ? 'var(--ok)' : 'var(--err)' }}>{msg.text}</div>
      )}
    </div>
  )
}
