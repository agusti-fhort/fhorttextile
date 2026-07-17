import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { sizeSystems } from '../../api/endpoints'

// SizeSystemSelector — tria d'un SizeSystem existent i del seu RUN (sprint ÀMBIT, higiene d'entrada).
// Substitueix el textarea d'etiquetes de «Nou run de client»: el run ja no es tecleja, es TRIA. El
// pare rep el system sencer (amb `talles`) i n'extreu les etiquetes → la canonada de match/create
// d'aigües avall no canvia (segueix treballant amb etiquetes).
// Props: { value (id|null), onChange(system|null), targetCodi (filtra per target; buit = universal) }

const MONO = 'IBM Plex Mono, monospace'

export default function SizeSystemSelector({ value = null, onChange, targetCodi = null }) {
  const { t } = useTranslation()
  const [systems, setSystems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    sizeSystems.list({ actiu: true, page_size: 100 })
      .then(r => {
        if (!alive) return
        const rows = (r.data?.results ?? r.data ?? []).filter(s =>
          (s.talles || []).length > 0 &&
          (!targetCodi || !s.target_codis?.length || s.target_codis.includes(targetCodi)))
        setSystems(rows)
      })
      .catch(() => { if (alive) setSystems([]) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [targetCodi])

  if (loading) return <p style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: 0 }}>{t('size_system_selector.loading')}</p>
  if (systems.length === 0) return <p style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: 0 }}>{t('size_system_selector.empty')}</p>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 240, overflowY: 'auto' }}>
      {systems.map(s => {
        const actiu = value === s.id
        const labels = (s.talles || []).map(d => d.etiqueta || d.size_label || d.label).filter(Boolean)
        return (
          <div key={s.id} onClick={() => onChange?.(actiu ? null : s)} style={{
            padding: '8px 12px', borderRadius: 8, cursor: 'pointer', fontFamily: MONO,
            border: `1px solid ${actiu ? 'var(--warn)' : 'var(--gray-l)'}`,
            background: actiu ? 'var(--warn-bg)' : 'var(--white)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 600, fontSize: 'var(--fs-body)', color: actiu ? 'var(--warn)' : 'var(--text-main)' }}>
                {s.nom || s.codi}
              </span>
              {s.customer_codi
                ? <span style={pill('var(--gold-pale)', 'var(--gold)')}>{s.customer_codi}</span>
                : <span style={pill('var(--gray-l)', 'var(--gray)')}>{t('size_system_selector.canonical')}</span>}
            </div>
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--gray)', marginTop: 2 }}>
              {s.codi} · {labels.join(' · ')}
            </div>
          </div>
        )
      })}
    </div>
  )
}

const pill = (bg, color) => ({
  fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '1px 6px', borderRadius: 999,
  background: bg, color,
})
