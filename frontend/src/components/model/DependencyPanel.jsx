import { useTranslation } from 'react-i18next'

// P8 — Arbre de dependència + ruleset (LECTURA a Mesures). Mostra la llinatge
// garment_type → garment_type_item → model i el grading_rule_set vigent (d'ell se'n desprèn la
// sembra del grading). A Mesures és NOMÉS lectura: l'autoria (canviar tipus/ítem, editar el ruleset)
// viu a l'edició del model — aquí es deixa el SEAM (visible, no editable).
export default function DependencyPanel({ model }) {
  const { t } = useTranslation()
  if (!model) return null
  const gtItem = model.garment_type_item_nom
    ? `${model.garment_type_item_nom}${model.garment_type_item_code ? ` (${model.garment_type_item_code})` : ''}`
    : null
  const chain = [model.garment_type_nom, gtItem, model.codi_intern].filter(Boolean)
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      padding: '6px 12px', marginBottom: 12, fontSize: 'var(--fs-body)',
      border: '0.5px solid var(--border)', borderRadius: 6, background: 'var(--bg-card)',
    }}>
      <i className="ti ti-sitemap" style={{ color: 'var(--text-muted)' }} />
      <span style={{ color: 'var(--text-muted)' }}>{t('dependency.title')}:</span>
      {chain.map((c, i) => (
        <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          {i > 0 && <i className="ti ti-chevron-right" style={{ fontSize: 11, color: 'var(--text-muted)' }} />}
          <span style={{ color: 'var(--text-main)' }}>{c}</span>
        </span>
      ))}
      <span style={{ marginLeft: 16, color: 'var(--text-muted)' }}>{t('dependency.ruleset')}:</span>
      <span style={{ color: model.grading_rule_set_nom ? 'var(--gold)' : 'var(--text-muted)' }}>
        {model.grading_rule_set_nom || t('dependency.no_ruleset')}
      </span>
      <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontStyle: 'italic' }}>
        {t('dependency.editable_hint')}
      </span>
    </div>
  )
}
