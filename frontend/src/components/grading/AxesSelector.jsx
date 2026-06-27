import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  TARGETS, GARMENT_GROUPS, nomLocal,
  availableTargetCodes, availableConstructions, availableFits,
} from './gradingAxes'

// AxesSelector — cascada target → construcció/fit → grup (Sprint Llibreria d'Items, B2).
// Component PUR i reutilitzable: rep `ruleSets` (per il·luminar només els eixos disponibles) i
// emet els 4 CODIS via onChange. Reprodueix l'idioma visual de GradingRuleSets (família) sense
// tocar-lo (vàlvula d'escapament). value = { target, construction, fit, garmentGroup } (codis|null).

export default function AxesSelector({ ruleSets = [], value, onChange }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  const { target = null, construction = null, fit = null, garmentGroup = null } = value || {}

  const targetCodes = useMemo(() => availableTargetCodes(ruleSets), [ruleSets])
  const constructions = useMemo(() => availableConstructions(ruleSets, target), [ruleSets, target])
  const fits = useMemo(() => availableFits(ruleSets, target, construction), [ruleSets, target, construction])

  // Cada selecció reseteja els eixos de sota (mateix comportament que GradingRuleSets).
  const pick = (patch) => onChange?.({ target, construction, fit, garmentGroup, ...patch })

  return (
    <div>
      {/* Pas 1: Target */}
      <StepSection number={1} title={t('grading.step_target')}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {TARGETS.map(tg => (
            <TargetCard
              key={tg.codi}
              target={tg}
              selected={target === tg.codi}
              available={targetCodes.has(tg.codi)}
              onClick={() => pick({ target: tg.codi, construction: null, fit: null, garmentGroup: null })}
            />
          ))}
        </div>
      </StepSection>

      {/* Pas 2: Construction + Fit */}
      {target && (constructions.length > 0 || fits.length > 0) && (
        <StepSection number={2} title={t('grading.step_construction_fit')}>
          <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
            <div>
              <p style={labelStyle}>{t('grading.construction_type')}</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {constructions.map(c => (
                  <SelectionButton
                    key={c.codi}
                    label={t(`model_wizard.construction_${c.codi}`, c.nom_en)}
                    selected={construction === c.codi}
                    onClick={() => pick({ construction: c.codi, fit: null, garmentGroup: null })}
                  />
                ))}
              </div>
            </div>
            {construction && fits.length > 0 && (
              <div>
                <p style={labelStyle}>{t('grading.fit_type_label')}</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {fits.map(f => (
                    <SelectionButton
                      key={f.codi}
                      label={t(`model_wizard.fit_${f.codi}`, f.nom_en)}
                      selected={fit === f.codi}
                      onClick={() => pick({ fit: f.codi, garmentGroup: null })}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </StepSection>
      )}

      {/* Pas 3: Garment Group */}
      {fit && (
        <StepSection number={3} title={t('grading.step_group')}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {GARMENT_GROUPS.map(g => (
              <SelectionButton
                key={g.codi}
                label={g.nom_en}
                sublabel={lang !== 'en' ? nomLocal(g, lang) : null}
                selected={garmentGroup === g.codi}
                onClick={() => pick({ garmentGroup: g.codi })}
              />
            ))}
          </div>
        </StepSection>
      )}
    </div>
  )
}

const labelStyle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 6,
  textTransform: 'uppercase', letterSpacing: '.06em',
}

function StepSection({ number, title, children }) {
  return (
    <div style={{ marginBottom: '1.4rem' }}>
      <p style={{
        fontSize: 'var(--fs-label)', fontWeight: 700, color: 'var(--gold)',
        letterSpacing: '0.08em', textTransform: 'uppercase', margin: '0 0 10px',
      }}>
        {number} · {title}
      </p>
      {children}
    </div>
  )
}

function TargetCard({ target, selected, available, onClick }) {
  const { t } = useTranslation()
  return (
    <div
      onClick={available ? onClick : undefined}
      role={available ? 'button' : undefined}
      tabIndex={available ? 0 : undefined}
      onKeyDown={e => { if (available && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); onClick() } }}
      style={{
        border: `1px solid ${selected ? 'var(--gold)' : 'var(--border)'}`,
        borderRadius: 8, padding: '8px 14px',
        cursor: available ? 'pointer' : 'not-allowed',
        background: selected ? '#fdf6ee' : available ? 'var(--white)' : '#f8f8f8',
        opacity: available ? 1 : 0.4,
        minWidth: 100, textAlign: 'center', transition: 'all .15s',
      }}
    >
      <div style={{
        fontSize: 'var(--fs-body)',
        fontWeight: selected ? 600 : 400,
        color: selected ? 'var(--gold)' : 'var(--text-main)',
      }}>
        {t(`model_wizard.target_${target.codi}`, target.nom_en)}
      </div>
    </div>
  )
}

function SelectionButton({ label, sublabel, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        border: `1px solid ${selected ? 'var(--gold)' : 'var(--border)'}`,
        borderRadius: 6, padding: sublabel ? '5px 12px' : '6px 14px',
        background: selected ? '#fdf6ee' : 'var(--white)',
        color: selected ? 'var(--gold)' : 'var(--text-main)',
        fontWeight: selected ? 600 : 400, fontSize: 'var(--fs-body)',
        cursor: 'pointer', transition: 'all .15s', textAlign: 'left', lineHeight: 1.25,
      }}
    >
      {label}
      {sublabel && (
        <span style={{
          display: 'block', fontSize: 'var(--fs-caption)',
          color: selected ? '#a06622' : 'var(--text-muted)', fontWeight: 400, marginTop: 1,
        }}>
          {sublabel}
        </span>
      )}
    </button>
  )
}
