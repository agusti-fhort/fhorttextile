import { useMemo, useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  TARGETS, nomLocal,
  availableTargetCodes, availableConstructions, availableFits,
} from '../grading/gradingAxes'
import { useGarmentCatalog } from '../grading/garmentCatalog'
import { garmentTypeItems } from '../../api/endpoints'
import GroupPills from '../GarmentTypeSelector/GroupPills'

// CascadeSelector — component ÚNIC de la cascada de vestit (target→construcció→fit→grup→família→ítem).
// Unifica els tres selectors que abans divergien (AxesSelector · GarmentTypeSelector · ScopeSelector),
// que ja bevien de la mateixa font (useGarmentCatalog). Base: AxesSelector (mode single) + ScopeSelector
// (mode multi). Ref docs/diagnosis/DIAGNOSI_UNIFICACIO_SELECTORS_CASCADE.md (matriu P6 = contracte).
//
// Props:
//   mode='single'|'multi'   — 'single' = un sol camí, valor pla; 'multi' = selecció acumulativa de nodes.
//   value                   — (single) { target, construction, fit, garmentGroup, garmentTypeId, garmentTypeItemId }.
//   nodes                   — (multi) [{ node_type:'GROUP'|'TYPE'|'ITEM', group_codi?, garment_type_id?, garment_type_item_id?, label }].
//   onChange                — (single) onChange(valuePla) · (multi) onChange(nodes[]).
//   target?                 — codi de target per retallar el catàleg. En single, si no es passa, es
//                             deriva de value.target. En multi, per defecte null (no bloquejant).
//   ruleSets?=[]            — disponibilitat dels eixos superiors (només single, nivells target/construcció/fit).
//   minLevel?='target'      — primer nivell visible ('target'|'construction'|'fit'|'group'|'family'|'item').
//   maxLevel?='item'        — últim nivell visible.
//   stopPolicy?='free'      — 'free' = parar a qualsevol nivell (ítem és toggle) · 'require-item' = en
//                             triar ítem crida onConfirm (emet-i-tanca, patró GarmentTypeSelector).
//   onConfirm?              — (single, require-item) onConfirm({ value, family, item }) en triar ítem.
//   compat?                 — (només single) LLEI C5: { construction?, fit? }. Quan s'informa, el
//                             catàleg NO exclou res: les famílies/grups sense perfil de talles per a
//                             la combinació surten ATENUATS i avall, amb el motiu, en comptes de
//                             desaparèixer. Sense la prop, comportament històric (filtre excloent).
//   showCounts?=false       — (només multi) mostra el comptador de models per node.
//   counts?                 — (multi, showCounts) { by_type:{<garment_type_id>:n}, by_item:{<item_id>:n} }
//                             injectat pel consumidor (endpoint /models/garment-counts/); el component NO fa fetch.

const LEVELS = ['target', 'construction', 'fit', 'group', 'family', 'item']
const lvl = (name) => LEVELS.indexOf(name)

function famLabel(f, lang) {
  if (lang === 'ca') return f.nom_ca || f.nom_en || f.nom_client || ''
  if (lang === 'es') return f.nom_es || f.nom_en || f.nom_client || ''
  return f.nom_en || f.nom_client || ''
}

export default function CascadeSelector({ mode = 'single', ...rest }) {
  return mode === 'multi'
    ? <MultiCascade {...rest} />
    : <SingleCascade {...rest} />
}

// ── MODE SINGLE — evolució d'AxesSelector: valor pla, patch complet amb neteja d'eixos inferiors,
// gatings de visibilitat i toggle de família/ítem. Afegeix acotació minLevel/maxLevel i require-item.
function SingleCascade({
  ruleSets = [], value, onChange, target, compat = null,
  minLevel = 'target', maxLevel = 'item', stopPolicy = 'free', onConfirm,
}) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  const {
    target: vTarget = null, construction = null, fit = null, garmentGroup = null,
    garmentTypeId = null, garmentTypeItemId = null,
  } = value || {}
  // Target del catàleg: prop explícita (p.ex. wizard, nivells que comencen a grup) o derivat del valor.
  const catalogTarget = target ?? vTarget ?? null

  const minIdx = lvl(minLevel)
  const maxIdx = lvl(maxLevel)
  const inRange = (name) => { const i = lvl(name); return i >= minIdx && i <= maxIdx }

  const targetCodes = useMemo(() => availableTargetCodes(ruleSets), [ruleSets])
  const constructions = useMemo(() => availableConstructions(ruleSets, vTarget), [ruleSets, vTarget])
  const fits = useMemo(() => availableFits(ruleSets, vTarget, construction), [ruleSets, vTarget, construction])

  const { groups, familiesOf } = useGarmentCatalog(catalogTarget, compat)
  const families = familiesOf(garmentGroup)
  const [items, setItems] = useState([])

  useEffect(() => {
    if (!garmentTypeId) { setItems([]); return }
    let alive = true
    garmentTypeItems.list({ garment_type: garmentTypeId, active: 'true', page_size: 200 })
      .then(r => { if (alive) setItems(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setItems([]) })
    return () => { alive = false }
  }, [garmentTypeId])

  // Cada selecció reseteja els eixos de sota (mateix comportament que AxesSelector).
  const pick = (patch) => onChange?.({
    target: vTarget, construction, fit, garmentGroup, garmentTypeId, garmentTypeItemId, ...patch })

  // Prerequisit de visibilitat del pas Grup: si el pas construcció/fit és visible, cal fit triat;
  // si el grup és el primer nivell visible (p.ex. wizard), es mostra directament.
  const groupPrereq = inRange('construction') ? !!fit : true

  const onItemClick = (it) => {
    if (stopPolicy === 'require-item') {
      const fam = families.find(f => f.id === garmentTypeId) || null
      const next = { target: vTarget, construction, fit, garmentGroup, garmentTypeId, garmentTypeItemId: it.id }
      onChange?.(next)
      onConfirm?.({ value: next, family: fam, item: it })
    } else {
      pick({ garmentTypeItemId: garmentTypeItemId === it.id ? null : it.id })
    }
  }

  return (
    <div>
      {/* Pas 1: Target */}
      {inRange('target') && (
        <StepSection number={1} title={t('grading.step_target')}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {TARGETS.map(tg => (
              <TargetCard
                key={tg.codi}
                target={tg}
                selected={vTarget === tg.codi}
                available={targetCodes.has(tg.codi)}
                onClick={() => pick({ target: tg.codi, construction: null, fit: null, garmentGroup: null, garmentTypeId: null, garmentTypeItemId: null })}
              />
            ))}
          </div>
        </StepSection>
      )}

      {/* Pas 2: Construction + Fit */}
      {inRange('construction') && vTarget && (constructions.length > 0 || fits.length > 0) && (
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
      {inRange('group') && groupPrereq && (
        <StepSection number={3} title={t('grading.step_group')}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {groups.map(g => (
              <SelectionButton
                key={g.codi}
                label={g.nom_en}
                sublabel={lang !== 'en' ? nomLocal(g, lang) : null}
                selected={garmentGroup === g.codi}
                motiu={motiuDe(g, t)}
                onClick={() => pick({ garmentGroup: g.codi, garmentTypeId: null, garmentTypeItemId: null })}
              />
            ))}
          </div>
        </StepSection>
      )}

      {/* Pas 4: Família (OPCIONAL en free) */}
      {inRange('family') && garmentGroup && families.length > 0 && (
        <StepSection number={4} title={t('grading.step_family')}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {families.map(f => (
              <SelectionButton
                key={f.id}
                label={famLabel(f, lang)}
                sublabel={f.codi_client || null}
                selected={garmentTypeId === f.id}
                motiu={motiuDe(f, t)}
                onClick={() => pick({
                  garmentTypeId: garmentTypeId === f.id ? null : f.id, garmentTypeItemId: null })}
              />
            ))}
          </div>
        </StepSection>
      )}

      {/* Pas 5: Item — en free és toggle; en require-item emet i crida onConfirm. */}
      {inRange('item') && garmentTypeId && items.length > 0 && (
        <StepSection number={5} title={t('grading.step_item')}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {items.map(it => (
              <SelectionButton
                key={it.id}
                label={it.name || it.code}
                sublabel={it.code || null}
                selected={garmentTypeItemId === it.id}
                onClick={() => onItemClick(it)}
              />
            ))}
          </div>
        </StepSection>
      )}
    </div>
  )
}

// ── MODE MULTI — evolució de ScopeSelector: selecció JERÀRQUICA i ACUMULATIVA de nodes; navegar i
// marcar són accions ortogonals a cada nivell. Preserva EXACTAMENT sameNode/has/toggle. Afegeix counts.
const MONO = 'IBM Plex Mono, monospace'

const sameNode = (a, b) =>
  a.node_type === b.node_type &&
  (a.group_codi ?? null) === (b.group_codi ?? null) &&
  (a.garment_type_id ?? null) === (b.garment_type_id ?? null) &&
  (a.garment_type_item_id ?? null) === (b.garment_type_item_id ?? null)

function MultiCascade({
  value = [], nodes, onChange, target,
  maxLevel = 'item', showCounts = false, counts,
}) {
  // Contracte històric de ScopeSelector: la prop és `value`. Acceptem també `nodes` com a àlies.
  const selected = nodes ?? value ?? []
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  const { groups, familiesOf } = useGarmentCatalog(target ?? null)
  const [grup, setGrup] = useState(null)
  const [familyId, setFamilyId] = useState(null)
  const [items, setItems] = useState([])
  const families = familiesOf(grup)
  const showItemLevel = lvl('item') <= lvl(maxLevel)

  useEffect(() => {
    if (!groups.length) return
    if (!grup || !groups.some(g => g.codi === grup)) { setGrup(groups[0].codi); setFamilyId(null); setItems([]) }
  }, [groups, grup])

  useEffect(() => {
    if (!familyId) { setItems([]); return }
    let alive = true
    garmentTypeItems.list({ garment_type: familyId, active: 'true', page_size: 200 })
      .then(r => { if (alive) setItems(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setItems([]) })
    return () => { alive = false }
  }, [familyId])

  const has = (n) => selected.some(v => sameNode(v, n))
  const toggle = (n) => onChange?.(has(n) ? selected.filter(v => !sameNode(v, n)) : [...selected, n])

  const grupObj = groups.find(g => g.codi === grup)
  const grupNode = { node_type: 'GROUP', group_codi: grup, label: grupObj?.nom_en || grup }

  const countChip = (n) => {
    if (!showCounts || n == null) return null
    return <span style={countStyle}>{n}</span>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Àmbit triat — acumulatiu, cada node retirable */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', minHeight: 28, alignItems: 'center' }}>
        {selected.length === 0
          ? <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
              {t('scope.empty')}
            </span>
          : selected.map((n, i) => (
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
      <GroupPills groups={groups} value={grup} onChange={g => { setGrup(g); setFamilyId(null); setItems([]) }} />
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
                  {countChip(counts?.by_type?.[f.id])}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {/* Nivell 3 — ITEM */}
      {showItemLevel && familyId && items.length > 0 && (
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
                  {countChip(counts?.by_item?.[it.id])}
                </label>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Estils i subcomponents (single) — tokens CSS; els hex literals d'AxesSelector moren aquí.
const labelStyle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 6,
  textTransform: 'uppercase', letterSpacing: '.06em',
}

const lbl = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 6,
  textTransform: 'uppercase', letterSpacing: '.06em', fontFamily: MONO,
}

const countStyle = {
  fontFamily: MONO, fontSize: 'var(--fs-caption)', fontWeight: 600,
  color: 'var(--warn)', background: 'var(--warn-bg)', borderRadius: 999, padding: '0 6px',
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
        background: selected ? 'var(--gold-pale)' : available ? 'var(--white)' : 'var(--gray-l)',
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

// C5 — motiu traduït d'un node atenuat, o null si és compatible (o si no s'ha demanat compat).
function motiuDe(node, t) {
  if (node?.compat?.ok !== false) return null
  return t('grading.compat_motiu', { eix: t(`grading.axis_${node.compat.motiu || 'target'}`) })
}

// `motiu` (C5): el node NO és compatible amb la combinació demanada. S'atenua i ho DIU — però
// segueix clicable: l'eina s'ofereix sencera i s'acota amb informació, no amb ocultació ni bloqueig.
function SelectionButton({ label, sublabel, selected, motiu = null, onClick }) {
  return (
    <button
      onClick={onClick}
      title={motiu || undefined}
      style={{
        border: `1px solid ${selected ? 'var(--gold)' : 'var(--border)'}`,
        borderRadius: 6, padding: sublabel || motiu ? '5px 12px' : '6px 14px',
        background: selected ? 'var(--gold-pale)' : 'var(--white)',
        color: selected ? 'var(--gold)' : 'var(--text-main)',
        fontWeight: selected ? 600 : 400, fontSize: 'var(--fs-body)',
        cursor: 'pointer', transition: 'all .15s', textAlign: 'left', lineHeight: 1.25,
        opacity: motiu ? 0.5 : 1,
      }}
    >
      {label}
      {sublabel && (
        <span style={{
          display: 'block', fontSize: 'var(--fs-caption)',
          color: selected ? 'var(--gold)' : 'var(--text-muted)', fontWeight: 400, marginTop: 1,
        }}>
          {sublabel}
        </span>
      )}
      {motiu && (
        <span style={{
          display: 'block', fontSize: 'var(--fs-caption)',
          color: 'var(--text-muted)', fontWeight: 400, marginTop: 1,
        }}>
          {motiu}
        </span>
      )}
    </button>
  )
}
