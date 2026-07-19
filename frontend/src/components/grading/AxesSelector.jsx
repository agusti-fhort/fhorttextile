import { useMemo, useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  TARGETS, nomLocal,
  availableTargetCodes, availableConstructions, availableFits,
} from './gradingAxes'
import { useGarmentCatalog } from './garmentCatalog'
import { garmentTypeItems } from '../../api/endpoints'

// AxesSelector — cascada target → construcció/fit → grup → FAMÍLIA → ITEM.
// Sprint ÀMBIT: la cascada baixa fins a l'ITEM (arbre únic Grup→Família→Item, el mateix que el
// selector de peça i Garment Types). Família i item són OPCIONALS: parar-se al grup manté el
// comportament d'abans (filtre ample); baixar-hi precisa la disponibilitat per àmbit multi-node.
// value = { target, construction, fit, garmentGroup, garmentTypeId, garmentTypeItemId }.
// Sprint Wizard unificat (Onada 1): grups i famílies venen de `useGarmentCatalog` (font única) i es
// filtren pel TARGET triat — el pas Grup mostra només grups amb famílies compatibles (NEWBORN inclòs
// per a targets nadó), i Família/Item baixen en cascada. Sense target → catàleg complet. Els items
// segueixen carregant-se per família.

export default function AxesSelector({ ruleSets = [], value, onChange }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  const {
    target = null, construction = null, fit = null, garmentGroup = null,
    garmentTypeId = null, garmentTypeItemId = null,
  } = value || {}

  const targetCodes = useMemo(() => availableTargetCodes(ruleSets), [ruleSets])
  const constructions = useMemo(() => availableConstructions(ruleSets, target), [ruleSets, target])
  const fits = useMemo(() => availableFits(ruleSets, target, construction), [ruleSets, target, construction])

  // Font única: grups (de BD, retallats pel target) + famílies (filtrades pel target al backend).
  const { groups, familiesOf } = useGarmentCatalog(target)
  const families = familiesOf(garmentGroup)
  const [items, setItems] = useState([])

  // Pas 5 — items de la família triada.
  useEffect(() => {
    if (!garmentTypeId) { setItems([]); return }
    let alive = true
    garmentTypeItems.list({ garment_type: garmentTypeId, active: 'true', page_size: 200 })
      .then(r => { if (alive) setItems(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setItems([]) })
    return () => { alive = false }
  }, [garmentTypeId])

  // Cada selecció reseteja els eixos de sota (mateix comportament que abans).
  const pick = (patch) => onChange?.({
    target, construction, fit, garmentGroup, garmentTypeId, garmentTypeItemId, ...patch })

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
              onClick={() => pick({ target: tg.codi, construction: null, fit: null, garmentGroup: null, garmentTypeId: null, garmentTypeItemId: null })}
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
                    onClick={() => pick({ construction: c.codi, fit: null, garmentGroup: null, garmentTypeId: null, garmentTypeItemId: null })}
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
                      onClick={() => pick({ fit: f.codi, garmentGroup: null, garmentTypeId: null, garmentTypeItemId: null })}
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
            {groups.map(g => (
              <SelectionButton
                key={g.codi}
                label={g.nom_en}
                sublabel={lang !== 'en' ? nomLocal(g, lang) : null}
                selected={garmentGroup === g.codi}
                onClick={() => pick({ garmentGroup: g.codi, garmentTypeId: null, garmentTypeItemId: null })}
              />
            ))}
          </div>
        </StepSection>
      )}

      {/* Pas 4: Família (OPCIONAL) — arbre únic Grup→Família→Item. Parar-se aquí manté el filtre ample. */}
      {garmentGroup && families.length > 0 && (
        <StepSection number={4} title={t('grading.step_family')}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {families.map(f => (
              <SelectionButton
                key={f.id}
                label={famLabel(f, lang)}
                sublabel={f.codi_client || null}
                selected={garmentTypeId === f.id}
                onClick={() => pick({
                  garmentTypeId: garmentTypeId === f.id ? null : f.id, garmentTypeItemId: null })}
              />
            ))}
          </div>
        </StepSection>
      )}

      {/* Pas 5: Item (OPCIONAL) — la unitat operativa. */}
      {garmentTypeId && items.length > 0 && (
        <StepSection number={5} title={t('grading.step_item')}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {items.map(it => (
              <SelectionButton
                key={it.id}
                label={it.name || it.code}
                sublabel={it.code || null}
                selected={garmentTypeItemId === it.id}
                onClick={() => pick({ garmentTypeItemId: garmentTypeItemId === it.id ? null : it.id })}
              />
            ))}
          </div>
        </StepSection>
      )}
    </div>
  )
}

// Nom de família segons idioma (mateix criteri que el selector de peça).
function famLabel(f, lang) {
  if (lang === 'ca') return f.nom_ca || f.nom_en || f.nom_client || ''
  if (lang === 'es') return f.nom_es || f.nom_en || f.nom_client || ''
  return f.nom_en || f.nom_client || ''
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
