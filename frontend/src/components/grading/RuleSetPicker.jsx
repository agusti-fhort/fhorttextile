import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  classifyRuleSets, matchingRuleSets, matchingRuleSetsStrict, orderWithSuggestedFirst,
} from './gradingAxes'

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
//  - suggestedId: id del ruleset que el CATÀLEG proposa per a la combinació (SizingProfile; abans
//    del 2026-07-23, l'item). SUGGERIR ≠ ARROSSEGAR: si és a la llista de candidats, se'l puja al
//    capdamunt i se'l marca — però NO s'assigna sol. El tècnic clica igualment. Si no hi és (o el
//    perfil no en porta cap: C3, perfil d'àmbit pur), no té cap efecte. Opcional.
//  - onEmptyAction + emptyActionLabel: acció de l'estat buit (p.ex. anar a Grading Rules). Opcional.
//  - strict + sizeSystemId: mode WIZARD (sprint WIZARD-COMPLET). strict=true → matching ESTRICTE amb
//    `sizeSystemId` obligatori i sense comodí NULL. Per defecte false → matching LENIENT (superfícies CRUD).
//  - eliminatiu: LLEI C5 (2026-07-23). true → els eixos deixen de ser un GATE i passen a ser un
//    filtre OPCIONAL: no s'amaga res, els incompatibles baixen, s'atenuen i diuen per què. Sense
//    cap eix triat, es veu el catàleg sencer. Incompatible amb `strict` (el wizard de model manté
//    el seu matching estricte fins que C5 s'hi escampi).

export default function RuleSetPicker({
  ruleSets = [], garmentGroupCodiById = {}, axes,
  onPick, actionLabel, selectedId = null, suggestedId = null,
  onEmptyAction, emptyActionLabel,
  strict = false, sizeSystemId = null, eliminatiu = false,
}) {
  const { t } = useTranslation()
  const matches = useMemo(
    () => {
      if (eliminatiu) {
        // C5 — cap exclusió: es classifica i es reordena. El suggerit puja dins dels compatibles.
        const c = classifyRuleSets(ruleSets, axes, garmentGroupCodiById)
        const i = suggestedId == null ? -1 : c.findIndex(x => x.rs.id === suggestedId && x.compatible)
        return i <= 0 ? c : [c[i], ...c.slice(0, i), ...c.slice(i + 1)]
      }
      const m = strict
        ? matchingRuleSetsStrict(ruleSets, axes, garmentGroupCodiById, sizeSystemId)
        : matchingRuleSets(ruleSets, axes, garmentGroupCodiById)
      // P6 — el suggerit de l'item (V1) puja al capdamunt SENSE alterar el conjunt: el
      // ventall el segueix decidint el matching d'eixos, aquí només canvia l'ordre.
      return orderWithSuggestedFirst(m, suggestedId).map(rs => ({ rs, compatible: true, motius: [] }))
    },
    [ruleSets, axes, garmentGroupCodiById, strict, sizeSystemId, suggestedId, eliminatiu],
  )

  // F1.3 — quan falta un eix, el picker JA NO desapareix en silenci (DIAGNOSI_MODEL_174, risc #5):
  // pinta un estat buit dient QUINS eixos li falten. El silenci absolut es llegia com «el botó no respon».
  // C5 — en mode eliminatiu no hi ha eixos «que falten»: són un filtre opcional, no una condició.
  const missing = eliminatiu ? [] : [
    !axes?.target && t('grading.axis_target'),
    !axes?.construction && t('grading.axis_construction'),
    !axes?.garmentGroup && t('grading.axis_group'),
    !axes?.fit && t('grading.axis_fit'),
    strict && sizeSystemId == null && t('grading.axis_size_system'),
  ].filter(Boolean)

  if (missing.length > 0) {
    return (
      <div style={emptyBox}>
        {t('grading.picker_missing_axes', { eixos: missing.join(' · ') })}
      </div>
    )
  }

  if (matches.length === 0) {
    return (
      <div style={emptyBox}>
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
      {matches.map(({ rs, compatible, motius }) => (
        <PickCard
          key={rs.id}
          rs={rs}
          selected={selectedId != null && rs.id === selectedId}
          suggested={suggestedId != null && rs.id === suggestedId}
          // C5 — l'atenuat NO es bloqueja: l'eina s'ofereix sencera i s'acota amb informació.
          motiu={compatible ? null : t('grading.picker_incompatible', {
            eixos: motius.map(m => t(`grading.axis_${m}`)).join(' · '),
          })}
          actionLabel={actionLabel}
          onPick={() => onPick?.(rs)}
        />
      ))}
    </div>
  )
}

const emptyBox = {
  marginTop: 8, padding: '2rem', border: '1px dashed var(--border)', borderRadius: 8,
  textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)',
}

function PickCard({ rs, selected, suggested = false, motiu = null, actionLabel, onPick }) {
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
      // C5 — atenuat, no amagat ni bloquejat.
      opacity: motiu ? 0.55 : 1,
    }}>
      <div style={{ minWidth: 0 }}>
        <div style={{
          fontWeight: 600, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
          display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
        }}>
          {rs.nom}
          {suggested && (
            <Pill bg="#fdf6ee" color="var(--gold)">{t('grading.suggested_by_profile')}</Pill>
          )}
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
        {/* C5 — l'incompatible diu PER QUÈ ho és. Un gris sense motiu és un silenci nou. */}
        {motiu && (
          <div style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 4,
            display: 'flex', alignItems: 'center', gap: 5,
          }}>
            <i className="ti ti-alert-triangle" aria-hidden="true" />{motiu}
          </div>
        )}
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
