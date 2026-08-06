import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { garmentTypeItems } from '../../api/endpoints'
import { useGarmentCatalog } from '../grading/garmentCatalog'
import { nomLocal } from '../grading/gradingAxes'

// CascadeFinder — EL navegador de catàleg GRUP › FAMÍLIA › ITEM, en tres columnes de finder.
// (maqueta_wizard_model_v1, validada per l'Agus el 06/08/2026).
//
// Per què existeix: triar una peça es feia de dues maneres diferents segons la pantalla — el
// wizard amb la cascada de píndoles (CascadeSelector single) i Garment Types amb mestre-detall
// (llista plana + cards). Dos sistemes per triar EL MATEIX és el que l'Agus ha vetat. Aquest
// component és el sistema únic; qui el consumeix hi posa el seu cromo al voltant (filtres a
// dalt al wizard, accions de CRUD a Garment Types), però la TRIA es fa sempre igual.
//
// El que NO fa, a posta:
//   · no filtra per descarte — els filtres són del consumidor, i aquí arriben com a `query`
//     (text) i `compat` (eixos). Cap dels dos AMAGA res: atenuen i deixen triable (D-31.3).
//   · no coneix cap acció de catàleg (editar/esborrar/nou): és un selector, no una pàgina.
//
// Props:
//   value            — { garmentGroup, garmentTypeId, garmentTypeItemId }. Controlat pel consumidor.
//   onChange(next)   — patch complet del valor; en pujar de nivell, els de sota es netegen.
//   onPickItem?      — ({ group, family, item }) en triar un ítem (fulla). Additiu a onChange.
//   target?          — codi de target per a la compatibilitat de famílies (SizingProfile).
//   compat?          — { construction, fit }. Quan s'informa, useGarmentCatalog anota cada família
//                      amb `.compat={ok,motiu}` en comptes d'excloure-la: l'atenuem i ho diem.
//   query?           — text de cerca (nom o codi d'ítem). Filtra la POBLACIÓ d'ítems que compta i
//                      que es llista; els nivells de sobre s'atenuen si es queden sense coincidències.
//   renderHeader?    — ({ total, matching, filtrant }) → nus pintat SOBRE les columnes. És una render
//                      prop (durant el render, sense effect) perquè el comptador de la maqueta viu a
//                      la barra de filtres del consumidor i no aquí dins.
//   renderItemMeta?  — (item) → nus a la dreta de la fila d'ítem. Per defecte, el compte de POMs.
//   height?          — alçada de les columnes (la maqueta en fixa 268).
const MONO = 'IBM Plex Mono, monospace'

function famLabel(f, lang) {
  if (lang === 'ca') return f.nom_ca || f.nom_client || f.nom_en || ''
  if (lang === 'es') return f.nom_es || f.nom_client || f.nom_en || ''
  return f.nom_en || f.nom_client || ''
}

export default function CascadeFinder({
  value, onChange, onPickItem,
  target = null, compat = null, query = '',
  renderHeader, renderItemMeta, height = 268,
}) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  const { garmentGroup = null, garmentTypeId = null, garmentTypeItemId = null } = value || {}
  const { groups, familiesOf, families } = useGarmentCatalog(target, compat)

  // TOTS els ítems actius en UNA crida, no per família. La cerca de la maqueta és per nom o codi
  // de PEÇA i el comptador diu «N peces al catàleg»: les dues coses necessiten la població sencera,
  // i demanar-la família a família serien tantes crides com famílies per pintar una sola columna.
  const [items, setItems] = useState([])
  useEffect(() => {
    let alive = true
    // Sense `ordering`: aquest ViewSet no porta OrderingFilter i el paràmetre s'ignoraria en
    // silenci. L'ordre ja ve del queryset (garment_type · complexity_order · code), que és
    // exactament el que la columna d'ítems vol.
    garmentTypeItems.list({ active: 'true', page_size: 1000 })
      .then(r => { if (alive) setItems(r.data?.results ?? (Array.isArray(r.data) ? r.data : [])) })
      .catch(() => { if (alive) setItems([]) })
    return () => { alive = false }
  }, [])

  // La família de cada ítem, per poder pujar del compte d'ítems al grup que el conté.
  const grupDeFamilia = useMemo(
    () => Object.fromEntries(families.map(f => [f.id, f.grup])), [families])

  const q = query.trim().toLowerCase()
  const passa = (it) => !q || `${it.name || ''} ${it.code || ''}`.toLowerCase().includes(q)
  const coincidents = useMemo(() => items.filter(passa), [items, q])   // eslint-disable-line react-hooks/exhaustive-deps

  // Recomptes de la maqueta: quants ítems coincidents penja cada node. Zero ≠ amagat: atenua.
  const perFamilia = useMemo(() => {
    const n = {}
    for (const it of coincidents) n[it.garment_type] = (n[it.garment_type] || 0) + 1
    return n
  }, [coincidents])
  const perGrup = useMemo(() => {
    const n = {}
    for (const it of coincidents) {
      const g = grupDeFamilia[it.garment_type]
      if (g) n[g] = (n[g] || 0) + 1
    }
    return n
  }, [coincidents, grupDeFamilia])

  const famsDelGrup = familiesOf(garmentGroup)
  const itemsDeFamilia = useMemo(
    () => items.filter(it => it.garment_type === garmentTypeId), [items, garmentTypeId])

  // Cada tria neteja els nivells de sota: baixar per una branca no pot deixar penjada la selecció
  // d'una altra (és el mateix contracte que ja té CascadeSelector).
  const triaGrup = (codi) => onChange?.({
    garmentGroup: codi, garmentTypeId: null, garmentTypeItemId: null })
  const triaFamilia = (id) => onChange?.({
    garmentGroup, garmentTypeId: id, garmentTypeItemId: null })
  const triaItem = (it) => {
    onChange?.({ garmentGroup, garmentTypeId, garmentTypeItemId: it.id })
    onPickItem?.({
      group: garmentGroup,
      family: families.find(f => f.id === garmentTypeId) || null,
      item: it,
    })
  }

  return (
    <div>
      {renderHeader?.({ total: items.length, matching: coincidents.length, filtrant: !!q })}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', border: '0.5px solid var(--gray-l)',
        borderRadius: 8, overflow: 'hidden', background: 'var(--white)',
      }}>
        {/* GRUP */}
        <Columna titol={t('cascade_finder.col_group')} height={height}>
          {groups.map(g => (
            <Fila
              key={g.codi}
              nom={lang === 'en' ? g.nom_en : nomLocal(g, lang)}
              codi={g.codi}
              seleccionat={garmentGroup === g.codi}
              atenuat={!perGrup[g.codi]}
              motiu={motiuDe(g, t)}
              dreta={<span style={chev}>{perGrup[g.codi] || '·'} ›</span>}
              onClick={() => triaGrup(g.codi)}
            />
          ))}
        </Columna>

        {/* FAMÍLIA */}
        <Columna titol={t('cascade_finder.col_family')} height={height}>
          {!garmentGroup
            ? <Buit text={t('cascade_finder.pick_group')} />
            : famsDelGrup.map(f => (
              <Fila
                key={f.id}
                nom={famLabel(f, lang)}
                codi={f.codi_client}
                seleccionat={garmentTypeId === f.id}
                atenuat={!perFamilia[f.id]}
                motiu={motiuDe(f, t)}
                dreta={<span style={chev}>{perFamilia[f.id] || '·'} ›</span>}
                onClick={() => triaFamilia(f.id)}
              />
            ))}
        </Columna>

        {/* ITEM */}
        <Columna titol={t('cascade_finder.col_item')} height={height} last>
          {!garmentTypeId
            ? <Buit text={t('cascade_finder.pick_family')} />
            : itemsDeFamilia.length === 0
              ? <Buit text={t('cascade_finder.no_items')} />
              : itemsDeFamilia.map(it => (
                <Fila
                  key={it.id}
                  nom={it.name || it.code}
                  codi={it.code}
                  seleccionat={garmentTypeItemId === it.id}
                  atenuat={!passa(it)}
                  dreta={renderItemMeta
                    ? renderItemMeta(it)
                    : <span style={compte}>{t('cascade_finder.poms_n', { n: it.poms_count ?? 0 })}</span>}
                  onClick={() => triaItem(it)}
                />
              ))}
        </Columna>
      </div>
    </div>
  )
}

// C5 — el motiu traduït d'un node que el catàleg ha marcat incompatible. Mateixa font de text que
// CascadeSelector: el node s'atenua i DIU per què, però segueix sent triable.
function motiuDe(node, t) {
  if (node?.compat?.ok !== false) return null
  return t('grading.compat_motiu', { eix: t(`grading.axis_${node.compat.motiu || 'target'}`) })
}

function Columna({ titol, height, last = false, children }) {
  return (
    <div style={{
      borderRight: last ? 'none' : '0.5px solid var(--gray-l)',
      minHeight: height, maxHeight: height, overflowY: 'auto',
    }}>
      <div style={{
        position: 'sticky', top: 0, zIndex: 2, background: 'var(--gold-pale)',
        borderBottom: '0.5px solid var(--gray-l)', padding: '6px 12px', fontFamily: MONO,
        fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '.06em',
        color: 'var(--text-muted)',
      }}>{titol}</div>
      {children}
    </div>
  )
}

// `atenuat`: el node no té coincidències amb el filtre viu, o el catàleg l'ha marcat incompatible.
// S'esvaeix i SEGUEIX CLICABLE — el filtre acota, no bloqueja (D-31.3).
function Fila({ nom, codi, seleccionat, atenuat = false, motiu = null, dreta, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={motiu || undefined}
      style={{
        display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left',
        padding: '7px 12px', cursor: 'pointer', border: 'none',
        borderBottom: '0.5px solid var(--gray-l)', fontFamily: MONO,
        background: seleccionat ? 'var(--gold-pale)' : 'transparent',
        opacity: atenuat ? 0.35 : 1,
      }}
    >
      <span style={{ minWidth: 0, flex: 1 }}>
        <span style={{
          display: 'block', fontSize: 'var(--fs-body)',
          fontWeight: seleccionat ? 600 : 400,
          color: seleccionat ? 'var(--gold)' : 'var(--text-main)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{nom}</span>
        {codi && <span style={{
          display: 'block', fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 1,
        }}>{codi}</span>}
      </span>
      {dreta}
    </button>
  )
}

function Buit({ text }) {
  return (
    <div style={{
      padding: '14px 12px', fontFamily: MONO, fontSize: 'var(--fs-caption)',
      color: 'var(--text-muted)', fontStyle: 'italic',
    }}>{text}</div>
  )
}

const chev = { fontFamily: MONO, fontSize: 'var(--fs-label)', color: 'var(--text-muted)', flexShrink: 0 }
const compte = { fontFamily: MONO, fontSize: 'var(--fs-label)', color: 'var(--text-muted)', flexShrink: 0 }
