import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { garmentTypes, garmentTypeItems } from '../../api/endpoints'
import { GARMENT_GROUPS, nomLocal } from '../grading/gradingAxes'

// Pas 5A — Selector de DOS NIVELLS: família (GarmentType) → ítem (GarmentTypeItem).
// onSelect({ family, item }) → el wizard desa garment_type_id + garment_type_item_id (baula motor).

// WIZARD-COMPLET C.2 — arbre únic: el vocabulari de grups és la font ÚNICA del frontend (GARMENT_GROUPS,
// a grading/gradingAxes). Aquí es filtra ACCESSORIES (sense famílies actives al selector de peça); així
// no hi ha una segona llista divergent (abans un array `GRUPS` propi = la font del desajust 6 vs 7).
const GRUPS = GARMENT_GROUPS.filter(g => g.codi !== 'ACCESSORIES')

const MONO = 'IBM Plex Mono, monospace'

function famName(f, lang) {
  if (lang === 'ca') return f.nom_ca || f.nom_en || f.nom_client || ''
  if (lang === 'es') return f.nom_es || f.nom_en || f.nom_client || ''
  return f.nom_en || f.nom_client || ''
}
function grupLabel(g, lang) { return nomLocal(g, lang) }

export default function GarmentTypeSelector({ onSelect, selectedItemId = null }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)

  const [grupActiu, setGrupActiu] = useState('TOPS')
  const [families, setFamilies] = useState([])
  const [loadingFam, setLoadingFam] = useState(false)
  const [family, setFamily] = useState(null)   // família triada → mostra el nivell ítems
  const [items, setItems] = useState([])
  const [loadingItems, setLoadingItems] = useState(false)
  const [err, setErr] = useState(false)

  // Nivell 1 — carrega famílies del grup actiu (sense mock; estat buit real).
  useEffect(() => {
    let alive = true
    setLoadingFam(true); setErr(false)
    garmentTypes.list({ grup: grupActiu, page_size: 200, actiu: 'true' })
      .then(res => { if (alive) setFamilies(res.data?.results ?? res.data ?? []) })
      .catch(() => { if (alive) { setFamilies([]); setErr(true) } })
      .finally(() => { if (alive) setLoadingFam(false) })
    return () => { alive = false }
  }, [grupActiu])

  // Nivell 2 — carrega ítems de la família triada.
  const openFamily = useCallback((f) => {
    setFamily(f); setItems([]); setLoadingItems(true); setErr(false)
    garmentTypeItems.list({ garment_type: f.id, active: 'true', page_size: 200 })
      .then(res => setItems(res.data?.results ?? res.data ?? []))
      .catch(() => { setItems([]); setErr(true) })
      .finally(() => setLoadingItems(false))
  }, [])

  const backToFamilies = () => { setFamily(null); setItems([]) }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: MONO }}>
      {family === null ? (
        <>
          {/* Pestanyes de grup */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', padding: '14px 16px',
            borderBottom: '0.5px solid var(--gray-l)', background: 'var(--white)' }}>
            {GRUPS.map(g => {
              const active = grupActiu === g.codi
              return (
                <button key={g.codi} onClick={() => setGrupActiu(g.codi)} style={{
                  padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontFamily: MONO,
                  fontSize: 'var(--fs-body)', fontWeight: active ? 600 : 400,
                  background: active ? 'var(--warn-bg)' : 'var(--white)',
                  color: active ? 'var(--warn)' : 'var(--text-main)',
                  border: `1px solid ${active ? 'var(--warn)' : 'var(--gray-l)'}`,
                }}>{grupLabel(g, lang)}</button>
              )
            })}
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
            {loadingFam && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: 0 }}>{t('garment_selector.loading_families')}</p>}
            {err && !loadingFam && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--err)', margin: 0 }}>{t('garment_selector.error')}</p>}
            {!loadingFam && !err && families.length === 0 && (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: 0 }}>{t('garment_selector.no_families')}</p>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              {families.map(f => (
                <button key={f.id} onClick={() => openFamily(f)} style={cardStyle(false)}>
                  <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>{famName(f, lang)}</span>
                  {f.codi_client && <span style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>{f.codi_client}</span>}
                  <span style={{ fontSize: 'var(--fs-label)', color: 'var(--warn)', marginTop: 4 }}>{t('garment_selector.choose_item')} →</span>
                </button>
              ))}
            </div>
          </div>
        </>
      ) : (
        <>
          {/* Capçalera nivell ítems */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px',
            borderBottom: '0.5px solid var(--gray-l)', background: 'var(--white)' }}>
            <button onClick={backToFamilies} style={{
              fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '5px 10px', borderRadius: 6, cursor: 'pointer',
              background: 'var(--white)', color: 'var(--gray)', border: '0.5px solid var(--gray-l)',
            }}>← {t('garment_selector.back')}</button>
            <span style={{ fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)' }}>{famName(family, lang)}</span>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
            {loadingItems && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: 0 }}>{t('garment_selector.loading_items')}</p>}
            {err && !loadingItems && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--err)', margin: 0 }}>{t('garment_selector.error')}</p>}
            {!loadingItems && !err && items.length === 0 && (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--warn)', margin: 0 }}>{t('garment_selector.no_items')}</p>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              {items.map(it => {
                const sel = selectedItemId === it.id
                return (
                  <button key={it.id} onClick={() => onSelect && onSelect({ family, item: it })} style={cardStyle(sel)}>
                    <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>{it.name}</span>
                    <span style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>{it.code}</span>
                    <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--gray)', marginTop: 4 }}>
                      {t('garment_selector.complexity')}: {it.complexity_order}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

const cardStyle = (selected) => ({
  display: 'flex', flexDirection: 'column', gap: 2, textAlign: 'left',
  border: `1px solid ${selected ? 'var(--warn)' : 'var(--gray-l)'}`,
  borderRadius: 8, padding: '12px 14px', cursor: 'pointer', fontFamily: MONO,
  background: selected ? 'var(--warn-bg)' : 'var(--white)',
})
