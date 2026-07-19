import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { garmentTypeItems } from '../../api/endpoints'
import { useGarmentCatalog } from '../grading/garmentCatalog'
import GroupPills from './GroupPills'

// Pas 5A — Selector de DOS NIVELLS: família (GarmentType) → ítem (GarmentTypeItem).
// onSelect({ family, item }) → el wizard desa garment_type_id + garment_type_item_id (baula motor).

// WIZARD-COMPLET C.2 + rectificació pills — arbre únic: els grups (ordre + etiquetes + estil de pill)
// viuen a GroupPills (font única), compartits amb Garment Types i el Navegador de POM Systems.
// Sprint Wizard unificat (Onada 1): grups i famílies venen de `useGarmentCatalog` (mateixa font que
// AxesSelector). Amb `target` → grups/famílies retallats als compatibles (NEWBORN inclòs per a nadó);
// sense target → catàleg complet.

const MONO = 'IBM Plex Mono, monospace'

function famName(f, lang) {
  if (lang === 'ca') return f.nom_ca || f.nom_en || f.nom_client || ''
  if (lang === 'es') return f.nom_es || f.nom_en || f.nom_client || ''
  return f.nom_en || f.nom_client || ''
}

export default function GarmentTypeSelector({ onSelect, selectedItemId = null, target = null }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)

  // Font única: grups (de BD, retallats pel target) + famílies (filtrades pel target al backend).
  const { groups, familiesOf, loading: loadingFam } = useGarmentCatalog(target)
  const [grupActiu, setGrupActiu] = useState(null)
  const [family, setFamily] = useState(null)   // família triada → mostra el nivell ítems
  const [items, setItems] = useState([])
  const [loadingItems, setLoadingItems] = useState(false)
  const [err, setErr] = useState(false)

  // Grup actiu per defecte = primer grup disponible; en re-calcular els grups (p.ex. canvi de target)
  // saltem a un de vàlid si l'actual ja no hi és.
  useEffect(() => {
    if (!groups.length) return
    if (!grupActiu || !groups.some(g => g.codi === grupActiu)) {
      setGrupActiu(groups[0].codi)
      setFamily(null); setItems([])
    }
  }, [groups, grupActiu])

  const families = familiesOf(grupActiu)

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
          {/* Pestanyes de grup — patró únic compartit (GroupPills). */}
          <div style={{ padding: '14px 16px', borderBottom: '0.5px solid var(--gray-l)', background: 'var(--white)' }}>
            <GroupPills groups={groups} value={grupActiu} onChange={g => { setGrupActiu(g); setFamily(null); setItems([]) }} />
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
            {loadingFam && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: 0 }}>{t('garment_selector.loading_families')}</p>}
            {!loadingFam && families.length === 0 && (
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
