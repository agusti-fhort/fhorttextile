import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { gradingRuleSets, garmentGroups, sizingProfiles } from '../../api/endpoints'
import RuleSetPicker from './RuleSetPicker'
import { availableFitsStrict } from './gradingAxes'
import { useEixos } from './eixosFont'
import { Chip, Field, MONO, ReadChip } from './wizardUI'

// EL PAS DE GRADUACIÓ, en UN sol component per als DOS llocs que l'ensenyen (31/07).
//
// Fins avui era el `block === 4` de `ModelWizard.jsx` i no es podia obrir des d'enlloc més. La
// decisió d'Agus és que el gest de graduar visqui a MESURES: el botó «Graduació» obre AQUEST
// mateix pas com a overlay, sense navegar i sense wizard. Per això és un component i no una
// còpia: si el criteri de matching o la llista de fits canvien, canvien als dos llocs alhora.
//
// SELF-SUFICIENT a posta: carrega ell mateix els jocs de regles, el mapa de grups i el
// suggeriment del perfil. L'alternativa —rebre-ho tot per props— hauria obligat l'overlay a
// reproduir els efectes de càrrega del wizard, que és exactament la còpia que s'ha d'evitar.
//
// CONTROLAT en el que és DECISIÓ: `fit`, `gradingRuleSetId` i `noGrading` són de qui el crida.
// El wizard els porta al seu payload; l'overlay els fa servir per materialitzar a l'instant.
// `onUsar(rs)` és el clic a «Usar aquest joc» — l'únic acte que escriu, i cadascú decideix què
// vol dir escriure al seu context.
//
// `noGrading` OPCIONAL: amb `onNoGrading=null` la casella «Sense graduació» no es pinta. La
// vol el wizard (crear un model sense graduació és legítim, P4); no la vol l'overlay, on
// l'usuari ha vingut expressament a informar-la i tancar ja és la manera de no fer-ho.
export default function GraduacioPanel({
  axes,                  // {target, construction, garmentGroupCodi, garmentTypeId, garmentTypeItemId}
  sizing,                // {size_system_id, size_system_nom} | null
  sizingMissing = null,  // 'system'|'run'|'base'|null — què falta per poder graduar
  fit, onFit,
  gradingRuleSetId, onUsar,
  noGrading = false, onNoGrading = null,
  customerCodi = null,
}) {
  const { t } = useTranslation()
  const [ruleSets, setRuleSets] = useState([])
  const [ggCodiById, setGgCodiById] = useState({})
  const [perfilSuggestedRsId, setPerfilSuggestedRsId] = useState(null)

  useEffect(() => {
    let viu = true
    Promise.all([
      gradingRuleSets.list({ page_size: 200, amb_regles: 1 }),
      garmentGroups.list({ page_size: 200 }),
    ]).then(([rsRes, ggRes]) => {
      if (!viu) return
      const rs = rsRes.data?.results ?? (Array.isArray(rsRes.data) ? rsRes.data : [])
      const gg = ggRes.data?.results ?? (Array.isArray(ggRes.data) ? ggRes.data : [])
      const map = {}; gg.forEach(g => { map[g.id] = g.codi })
      setRuleSets(rs); setGgCodiById(map)
    }).catch(() => { if (viu) setRuleSets([]) })
    return () => { viu = false }
  }, [])

  // El suggeriment ve del PERFIL (SizingProfile), no de l'item: és la font viva des del
  // 2026-07-23. Només ORDENA el picker (SUGGERIR ≠ ARROSSEGAR); mai s'assigna sol.
  const { target, construction, garmentGroupCodi, garmentTypeId, garmentTypeItemId } = axes || {}
  useEffect(() => {
    if (!target || !construction || !fit || !garmentTypeId) { setPerfilSuggestedRsId(null); return }
    let viu = true
    sizingProfiles.list({ target, construction, fit, garment_type: garmentTypeId, customer_codi: customerCodi || undefined })
      .then(({ data }) => {
        if (!viu) return
        const amb = (data?.results || []).find(p => p.grading_rule_set?.id != null)
        setPerfilSuggestedRsId(amb?.grading_rule_set?.id ?? null)
      })
      .catch(() => { if (viu) setPerfilSuggestedRsId(null) })
    return () => { viu = false }
  }, [target, construction, fit, garmentTypeId, customerCodi])

  // Sprint ÀMBIT — el node de la peça (item → família → grup) viatja als eixos: un contenidor
  // amb àmbit aplica si el conté a ell o a un ancestre seu.
  const nodeAxes = useMemo(() => ({
    target, construction, garmentGroup: garmentGroupCodi,
    garmentTypeId: garmentTypeId ?? null, garmentTypeItemId: garmentTypeItemId ?? null,
  }), [target, construction, garmentGroupCodi, garmentTypeId, garmentTypeItemId])

  const ssId = sizing?.size_system_id ?? null
  // Fits que porten a una graduació REAL per a la combinació fixada (matching estricte). El
  // catàleg de fits ve de `/fit-types/` i entra per paràmetre: `availableFitsStrict` és pura.
  const { fits: catFits } = useEixos()
  const fitOptions = useMemo(
    () => availableFitsStrict(ruleSets, nodeAxes, ggCodiById, ssId, catFits),
    [ruleSets, nodeAxes, ggCodiById, ssId, catFits])
  // El matching estricte el fa el PICKER amb aquests mateixos eixos (`strict`): calcular-lo
  // també aquí seria fer-lo dues vegades i obrir la porta que divergissin.
  const gradingAxes = useMemo(() => ({ ...nodeAxes, fit }), [nodeAxes, fit])

  // F1.3 — eixos del matching estricte encara sense resoldre. Sense això, qualsevol eix a null
  // buidava la llista i la UI ho reportava com «no hi ha cap joc de regles» (motiu fals).
  const eixosGradingMancants = [
    !target && t('grading.axis_target'),
    !construction && t('grading.axis_construction'),
    !garmentGroupCodi && t('grading.axis_group'),
  ].filter(Boolean)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Context FIX de la peça+talles (arbre únic: no es re-tria aquí; el grup el mana l'item) */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <ReadChip label={t('model_wizard.target')} value={target ? t(`model_wizard.target_${target}`) : '—'} />
        <ReadChip label={t('model_wizard.construction')} value={construction ? t(`model_wizard.construction_${construction}`) : '—'} />
        <ReadChip label={t('model_wizard.grading_group')} value={garmentGroupCodi || '—'} />
        <ReadChip label={t('model_wizard.grading_system')} value={sizing?.size_system_nom || '—'} />
      </div>

      {onNoGrading && (
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: MONO, fontSize: 'var(--fs-body)', cursor: 'pointer', color: 'var(--text-main)' }}>
          <input type="checkbox" checked={noGrading}
            onChange={e => onNoGrading(e.target.checked)} />
          {t('model_wizard.no_grading')}
        </label>
      )}

      {/* F1.3 — el missatge diu QUÈ falta de veritat, no sempre «defineix les talles». */}
      {!noGrading && !sizing && (
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: 0 }}>
          {t(`model_wizard.grading_needs_${sizingMissing || 'system'}`)}
        </p>
      )}

      {!noGrading && sizing && (
        <>
          {/* C5: la llista NO s'escurça als fits que porten a graduació — es marquen els que no
              hi porten. Abans desapareixien, i una llista buida deia un motiu fals. */}
          <Field label={t('model_wizard.pick_fit')}>
            {eixosGradingMancants.length > 0 && (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: '0 0 8px' }}>
                {t('model_wizard.grading_missing_axes', { eixos: eixosGradingMancants.join(' · ') })}
              </p>
            )}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {(catFits || []).map(f => {
                const ambGraduacio = fitOptions.some(o => o.codi === f.codi)
                return (
                  <Chip key={f.codi} active={fit === f.codi}
                    motiu={ambGraduacio ? null : t('model_wizard.fit_sense_graduacio')}
                    onClick={() => onFit(f.codi)}>
                    {t(`model_wizard.fit_${f.codi}`, f.nom_en)}
                  </Chip>
                )
              })}
            </div>
          </Field>
          {fit && (
            <RuleSetPicker
              ruleSets={ruleSets}
              garmentGroupCodiById={ggCodiById}
              axes={gradingAxes}
              strict
              sizeSystemId={ssId}
              selectedId={gradingRuleSetId}
              suggestedId={perfilSuggestedRsId}
              actionLabel={t('model_sheet.use_ruleset')}
              onPick={onUsar}
            />
          )}
        </>
      )}
    </div>
  )
}
