import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { matchingRuleSets } from './gradingAxes'

// RuleSetPicker — llistat de RuleSets que encaixen amb els eixos triats, amb acció final
// PARAMETRITZADA (Sprint Llibreria d'Items, B2). A diferència de RuleSetCard de GradingRuleSets,
// NO edita regles inline: només SELECCIONA (onPick). Estat buit amb slot d'acció contextual
// (a l'item: enllaç "crear a Grading Rules"). Component PUR: rep ruleSets + garmentGroupCodiById.
//
// Props:
//  - ruleSets, garmentGroupCodiById: dades carregades pel pare (B3).
//  - axes: { target, construction, fit, garmentGroup } (codis).
//  - onPick(ruleSet): acció final (a l'item: assignar la FK grading_rule_set).
//  - actionLabel: text del botó d'acció (p.ex. "Assignar").
//  - selectedId: id del ruleset ja triat (per ressaltar-lo). Opcional.
//  - onEmptyAction + emptyActionLabel: acció de l'estat buit (p.ex. anar a Grading Rules). Opcional.

export default function RuleSetPicker({
  ruleSets = [], garmentGroupCodiById = {}, axes,
  onPick, actionLabel, selectedId = null,
  onEmptyAction, emptyActionLabel,
}) {
  const { t } = useTranslation()
  const matches = useMemo(
    () => matchingRuleSets(ruleSets, axes, garmentGroupCodiById),
    [ruleSets, axes, garmentGroupCodiById],
  )

  const ready = axes && axes.target && axes.construction && axes.fit && axes.garmentGroup
  if (!ready) return null

  if (matches.length === 0) {
    return (
      <div style={{
        marginTop: 8, padding: '2rem', border: '1px dashed var(--border)', borderRadius: 8,
        textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)',
      }}>
        {t('grading.no_match')}
        <div style={{ marginTop: 8 }}>
          {onEmptyAction
            ? (
              <button type="button" onClick={onEmptyAction}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--gold)', fontSize: 'var(--fs-body)', textDecoration: 'underline',
                }}>
                {emptyActionLabel || t('grading.create_from_library')}
              </button>
            )
            : t('grading.create_from_library')}
        </div>
      </div>
    )
  }

  return (
    <div style={{ marginTop: 8 }}>
      {matches.map(rs => (
        <PickCard
          key={rs.id}
          rs={rs}
          selected={selectedId != null && rs.id === selectedId}
          actionLabel={actionLabel}
          onPick={() => onPick?.(rs)}
        />
      ))}
    </div>
  )
}

function PickCard({ rs, selected, actionLabel, onPick }) {
  const { t } = useTranslation()
  const reglesCount = rs.regles_count ?? rs.regles?.length ?? 0
  const breakCount = (rs.regles || []).filter(
    r => r.talla_break_label != null || r.valors_step?.above_xl != null).length

  return (
    <div style={{
      border: `1px solid ${selected ? 'var(--gold)' : 'var(--border)'}`,
      borderRadius: 10, marginBottom: 12, background: selected ? '#fdf6ee' : 'var(--white)',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      padding: '12px 18px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      gap: 14, flexWrap: 'wrap',
    }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
          {rs.nom}
        </div>
        <div style={{
          fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginTop: 2,
          display: 'flex', gap: 10, flexWrap: 'wrap',
        }}>
          {rs.targets_codis?.length > 0 && (
            <span>
              {rs.targets_codis.length > 1 ? t('grading.targets_label') : t('grading.target_label')}
              {rs.targets_codis.map((tc, i) => (
                <span key={tc}>
                  {i > 0 && <span style={{ color: '#bbb' }}> · </span>}
                  <strong>{t(`model_wizard.target_${tc}`, tc)}</strong>
                </span>
              ))}
            </span>
          )}
          {rs.construction_codi && <span>{t('grading.construction_label')}<strong>{t(`model_wizard.construction_${rs.construction_codi}`, rs.construction_codi)}</strong></span>}
          {rs.fit_type_codi && <span>{t('grading.fit_label')}<strong>{rs.fit_type_codi}</strong></span>}
          {rs.size_system_nom && <span>{t('grading.size_system_label')}<strong>{rs.size_system_nom}</strong></span>}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Pill bg="#eef4fc" color="#2a5a8a">{t('grading.rules_count', { count: reglesCount })}</Pill>
        {breakCount > 0 && <Pill bg="#fdf6ee" color="var(--gold)">{t('grading.with_break', { count: breakCount })}</Pill>}
        <Pill
          bg={rs.is_system_default ? '#f5f0ea' : '#f0f9f0'}
          color={rs.is_system_default ? 'var(--text-muted)' : '#3b6d11'}
        >{rs.is_system_default ? t('grading.system') : t('grading.custom')}</Pill>
        <button
          type="button"
          onClick={onPick}
          style={{
            fontSize: 'var(--fs-body)', padding: '6px 16px', borderRadius: 6, cursor: 'pointer',
            background: selected ? 'var(--white)' : 'var(--gold)',
            color: selected ? 'var(--gold)' : 'var(--white)',
            border: selected ? '1px solid var(--gold)' : 'none', fontWeight: 600,
          }}
        >
          {selected ? `✓ ${actionLabel}` : actionLabel}
        </button>
      </div>
    </div>
  )
}

function Pill({ bg, color, children }) {
  return (
    <span style={{
      fontSize: 'var(--fs-label)', padding: '3px 7px', borderRadius: 4,
      background: bg, color, fontWeight: 600, letterSpacing: '.04em', whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}
