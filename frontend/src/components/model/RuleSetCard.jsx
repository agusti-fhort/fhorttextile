import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { gradingRuleSets } from '../../api/endpoints'

// Sprint WIZARD-COMPLET (C.3) — la targeta de graduació del model passa a LECTURA ENRIQUIDA: resum
// complet de la selecció (nom, target, construcció, fit, sistema, nº regles, provinença). El CANVI ja
// NO es fa aquí a un sol clic (re-materialitzava les regles residents en silenci): viu al WIZARD.
// L'enllaç «Canviar graduació» obre el wizard d'edició al pas 4, on el canvi és explícit i re-materialitza
// pel camí existent (update-step2). Tolera el buit: model sense graduació → «— pendent» + enllaç per definir-la.
export default function RuleSetCard({ model }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [rs, setRs] = useState(null)
  const grsId = model?.grading_rule_set ?? null

  useEffect(() => {
    if (!grsId) { setRs(null); return }
    let alive = true
    gradingRuleSets.get(grsId)
      .then(res => { if (alive) setRs(res.data || null) })
      .catch(() => { if (alive) setRs(null) })
    return () => { alive = false }
  }, [grsId])

  const goEditGrading = () => navigate(`/models/${model.id}/editar?block=4`)

  const pending = <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>{t('model_sheet.grading_pending')}</span>
  const origenLabel = rs?.origen ? t(`grading.origen_${rs.origen}`, rs.origen) : (rs ? t('grading.origen_none') : null)

  return (
    <div style={{ border: '0.5px solid var(--border)', borderRadius: 8, padding: '12px 16px', marginBottom: 16, background: 'var(--bg-card)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
        <div style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>
          {t('dependency.ruleset')}
        </div>
        <button type="button" onClick={goEditGrading}
          style={{ background: 'none', border: '1px solid var(--gold)', color: 'var(--gold)', borderRadius: 6,
                   padding: '5px 12px', fontSize: 'var(--fs-body)', cursor: 'pointer', fontWeight: 600 }}>
          <i className="ti ti-edit" style={{ fontSize: 14 }} aria-hidden="true" /> {grsId ? t('model_sheet.change_grading') : t('model_sheet.define_grading')}
        </button>
      </div>

      {!grsId ? (
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('model_sheet.no_grading_yet')}</div>
      ) : (
        <div>
          <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, color: 'var(--text-main)', marginBottom: 8 }}>
            {rs?.nom ?? (model.grading_rule_set_nom || pending)}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
            <ReadItem label={t('grading.target_label').replace(/[:：]\s*$/, '')}
              value={rs?.targets_codis?.length ? rs.targets_codis.map(tc => t(`model_wizard.target_${tc}`, tc)).join(' · ') : pending} />
            <ReadItem label={t('model_wizard.construction')}
              value={rs?.construction_codi ? t(`model_wizard.construction_${rs.construction_codi}`, rs.construction_codi) : pending} />
            <ReadItem label={t('grading.fit_type_label')}
              value={rs?.fit_type_codi ? t(`model_wizard.fit_${rs.fit_type_codi}`, rs.fit_type_codi) : pending} />
            <ReadItem label={t('model_wizard.grading_system')} value={rs?.size_system_nom || pending} />
            <ReadItem label={t('grading.step_group')} value={rs?.garment_group_nom || pending} />
            <ReadItem label={t('model_sheet.grading_rules_label')} value={String(rs?.regles_count ?? 0)} />
            <ReadItem label={t('model_sheet.grading_origin')} value={origenLabel || pending} />
          </div>
        </div>
      )}
    </div>
  )
}

function ReadItem({ label, value, hideLabel }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {!hideLabel && (
        <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }}>{label}</span>
      )}
      <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}
