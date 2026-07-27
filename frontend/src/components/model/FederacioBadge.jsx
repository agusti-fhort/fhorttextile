import { useTranslation } from 'react-i18next'

const MONO = 'IBM Plex Mono, monospace'

// RETORN-2 — les DUES cares del canal d'estat, en un sol lloc perquè no divergeixin.
//
// La federació v2 té dues cases mirant la MATEIXA peça des de banda i banda del pont, i
// cadascuna ha de veure el que l'altra li diu — no el que s'imagina:
//
//   · A la MARCA (`MaduresaBadge`): com va la feina a l'estudi. Ve de `federacio_estat`, que
//     escriu `federation_service.sync_estat` i ningú més. Si el camp és buit, no es pinta res:
//     un badge que digués «0/0» quan encara no ha arribat cap notícia seria inventar-se una
//     maduresa que ningú no ha publicat.
//   · A l'ESTUDI (`EncarrecDelClient`): que la urgència i la data que veu NO són seves. La
//     marca MANA en aquests dos camps i els hi sobreescriu; sense aquesta nota, un tècnic que
//     els canviï a mà no entendria per què tornen a canviar sols.

export function MaduresaBadge({ model, t: tExt }) {
  const { t: tInt } = useTranslation()
  const t = tExt || tInt
  const est = model?.federacio_estat
  if (!est) return null

  const tk = est.tasques || {}
  const total = tk.n_total ?? 0
  const fase = est.fase_actual
    ? t(`model_sheet.dashboard.phase.${est.fase_actual}`, est.fase_actual)
    : '—'
  const acabat = !!tk.totes_acabades

  return (
    <span
      title={t('federacio.maduresa_hint', { at: est.actualitzat_at || '—' })}
      style={{
        fontSize: 'var(--fs-caption)', padding: '2px 7px', borderRadius: 5, fontFamily: MONO,
        display: 'inline-flex', alignItems: 'center', gap: 5,
        background: acabat ? 'var(--ok-bg)' : 'var(--gray-l)',
        color: acabat ? 'var(--ok)' : 'var(--gray)',
      }}
    >
      <i className="ti ti-affiliate" aria-hidden="true" />
      {total > 0
        ? t('federacio.maduresa_badge', { done: tk.n_done ?? 0, total, fase })
        : t('federacio.maduresa_badge_sense_tasques', { fase })}
    </span>
  )
}

export function EncarrecDelClient({ model, t: tExt }) {
  const { t: tInt } = useTranslation()
  const t = tExt || tInt
  if (model?.origen !== 'EXTERN') return null
  return (
    <span
      title={t('federacio.encarrec_client_hint')}
      style={{
        fontSize: 'var(--fs-caption)', fontFamily: MONO, color: 'var(--gray)',
        display: 'inline-flex', alignItems: 'center', gap: 4,
      }}
    >
      <i className="ti ti-lock" aria-hidden="true" />
      {t('federacio.encarrec_client')}
    </span>
  )
}
