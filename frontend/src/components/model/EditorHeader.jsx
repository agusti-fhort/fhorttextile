import { useTranslation } from 'react-i18next'
import BackButton from '../BackButton'

// Capçalera UNIFICADA dels editors de mesura (check ara; fitting a P5). Tres parts:
//  · botó de tornar transversal (`onBack`) a dalt, perquè mai s'arribi a l'editor sense sortida.
//  · barra d'IDENTITAT DE MODEL comuna (codi · nom · target/construction · base · run) — igual als
//    dos editors i als dos modes (treball/consulta).
//  · slot de FRANJA CONTEXTUAL (`context`) sota: el que és propi de la superfície (sessió de fitting:
//    persona/responsable/lloc; tasca de check). El check no n'hi posa cap encara.
export default function EditorHeader({ model, context = null, onBack = null }) {
  const { t } = useTranslation()
  if (!model) return null
  return (
    <div style={{ marginBottom: 16 }}>
      {onBack && (
        <div style={{ marginBottom: 8 }}><BackButton onClick={onBack} /></div>
      )}
      <div style={{
        display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap',
        background: 'var(--bg-muted)', border: '0.5px solid var(--border)',
        borderRadius: 8, padding: '10px 16px', fontSize: 'var(--fs-body)',
      }}>
        <span><strong>{model.codi_intern}</strong></span>
        {model.nom_prenda && <span>{model.nom_prenda}</span>}
        {model.target && <span style={{ color: 'var(--text-muted)' }}>{t(`model_wizard.target_${model.target}`, model.target)}</span>}
        {model.construction && <span style={{ color: 'var(--text-muted)' }}>{t(`model_wizard.construction_${model.construction}`, model.construction)}</span>}
        {model.base_size_label && <span style={{ color: 'var(--gold)' }}>{t('model_measurements.base_prefix')} {model.base_size_label}</span>}
        {model.size_run_model && <span style={{ color: 'var(--text-muted)' }}>{model.size_run_model}</span>}
      </div>
      {context && (
        <div style={{
          display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap',
          padding: '6px 16px', fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
        }}>{context}</div>
      )}
    </div>
  )
}
