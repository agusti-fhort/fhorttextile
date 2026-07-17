import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { garmentTypes, garmentTypeItems } from '../../api/endpoints'
import GroupPills, { PECA_GRUPS } from '../GarmentTypeSelector/GroupPills'

// ScopeSelector — ÀMBIT D'APLICABILITAT del contenidor de grading de client (sprint ÀMBIT).
// LLEI: «aplica a» = «està disponible per a». Selecció JERÀRQUICA i ACUMULATIVA sobre l'arbre únic:
// marcar un GRUP → disponible per a tots els seus garments · baixar a FAMÍLIA → tots els seus items ·
// baixar a ITEM → aquell item. MULTI-NODE: se'n poden marcar diversos alhora (p.ex. grup Parts
// superiors + item Blusa). La granularitat existeix a tots els nivells; la precisió FINAL l'aplica el
// tècnic en sembrar el model.
//
// value = [{ node_type: 'GROUP'|'TYPE'|'ITEM', group_codi?, garment_type_id?, garment_type_item_id?, label }]
// onChange(nodes) — el pare l'envia tal qual a `applies_to` del payload.

const MONO = 'IBM Plex Mono, monospace'

const sameNode = (a, b) =>
  a.node_type === b.node_type &&
  (a.group_codi ?? null) === (b.group_codi ?? null) &&
  (a.garment_type_id ?? null) === (b.garment_type_id ?? null) &&
  (a.garment_type_item_id ?? null) === (b.garment_type_item_id ?? null)

function famLabel(f, lang) {
  if (lang === 'ca') return f.nom_ca || f.nom_en || f.nom_client || ''
  if (lang === 'es') return f.nom_es || f.nom_en || f.nom_client || ''
  return f.nom_en || f.nom_client || ''
}

export default function ScopeSelector({ value = [], onChange }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  const [grup, setGrup] = useState(PECA_GRUPS[0]?.codi || 'TOPS')
  const [families, setFamilies] = useState([])
  const [familyId, setFamilyId] = useState(null)
  const [items, setItems] = useState([])

  useEffect(() => {
    if (!grup) { setFamilies([]); return }
    let alive = true
    setFamilyId(null); setItems([])
    garmentTypes.list({ grup, actiu: 'true', page_size: 200 })
      .then(r => { if (alive) setFamilies(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setFamilies([]) })
    return () => { alive = false }
  }, [grup])

  useEffect(() => {
    if (!familyId) { setItems([]); return }
    let alive = true
    garmentTypeItems.list({ garment_type: familyId, active: 'true', page_size: 200 })
      .then(r => { if (alive) setItems(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setItems([]) })
    return () => { alive = false }
  }, [familyId])

  const has = (n) => value.some(v => sameNode(v, n))
  const toggle = (n) => onChange?.(has(n) ? value.filter(v => !sameNode(v, n)) : [...value, n])

  const grupObj = PECA_GRUPS.find(g => g.codi === grup)
  const grupNode = { node_type: 'GROUP', group_codi: grup, label: grupObj?.nom_en || grup }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Àmbit triat — acumulatiu, cada node retirable */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', minHeight: 28, alignItems: 'center' }}>
        {value.length === 0
          ? <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
              {t('scope.empty')}
            </span>
          : value.map((n, i) => (
            <span key={i} style={{
              display: 'inline-flex', alignItems: 'center', gap: 6, padding: '3px 8px', borderRadius: 999,
              background: 'var(--warn-bg)', color: 'var(--warn)', border: '1px solid var(--warn)',
              fontFamily: MONO, fontSize: 'var(--fs-caption)', fontWeight: 600,
            }}>
              {t(`scope.node_${n.node_type}`)}: {n.label}
              <button type="button" onClick={() => toggle(n)} aria-label={t('scope.remove')}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0, lineHeight: 1 }}>
                <i className="ti ti-x" style={{ fontSize: 12 }} aria-hidden="true" />
              </button>
            </span>
          ))}
      </div>

      {/* Nivell 1 — GRUP: navega i, alhora, es pot marcar sencer */}
      <GroupPills value={grup} onChange={setGrup} />
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: MONO, fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
        <input type="checkbox" checked={has(grupNode)} onChange={() => toggle(grupNode)} />
        {t('scope.mark_group', { grup: grupObj ? (lang === 'ca' ? grupObj.nom_ca : lang === 'es' ? grupObj.nom_es : grupObj.nom_en) : grup })}
      </label>

      {/* Nivell 2 — FAMÍLIA: marcar-la (tots els seus items) o baixar-hi */}
      {families.length > 0 && (
        <div>
          <p style={lbl}>{t('scope.families')}</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {families.map(f => {
              const node = { node_type: 'TYPE', garment_type_id: f.id, label: famLabel(f, lang) || f.codi_client }
              const on = has(node)
              const open = familyId === f.id
              return (
                <span key={f.id} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 8px', borderRadius: 6,
                  border: `1px solid ${open ? 'var(--gold)' : 'var(--gray-l)'}`,
                  background: on ? 'var(--warn-bg)' : 'var(--white)',
                }}>
                  <input type="checkbox" checked={on} onChange={() => toggle(node)} title={t('scope.mark_family')} />
                  <button type="button" onClick={() => setFamilyId(open ? null : f.id)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: MONO,
                             fontSize: 'var(--fs-body)', color: open ? 'var(--gold)' : 'var(--text-main)', padding: 0 }}>
                    {famLabel(f, lang) || f.codi_client}
                  </button>
                </span>
              )
            })}
          </div>
        </div>
      )}

      {/* Nivell 3 — ITEM */}
      {familyId && items.length > 0 && (
        <div>
          <p style={lbl}>{t('scope.items')}</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {items.map(it => {
              const node = { node_type: 'ITEM', garment_type_item_id: it.id, label: it.name || it.code }
              const on = has(node)
              return (
                <label key={it.id} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 8px', borderRadius: 6,
                  border: '1px solid var(--gray-l)', background: on ? 'var(--warn-bg)' : 'var(--white)',
                  fontFamily: MONO, fontSize: 'var(--fs-body)', cursor: 'pointer',
                }}>
                  <input type="checkbox" checked={on} onChange={() => toggle(node)} />
                  {it.name || it.code}
                </label>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

const lbl = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 6,
  textTransform: 'uppercase', letterSpacing: '.06em', fontFamily: MONO,
}
