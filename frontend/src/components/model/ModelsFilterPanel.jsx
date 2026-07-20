import { useRef, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import CascadeSelector from '../CascadeSelector/CascadeSelector'
import { garmentTypeLabel, garmentGroupLabel } from './filterOptions'

// ModelsFilterPanel — panell desplegable de filtres avançats de la llista de Models, en 4 famílies
// (Identitat · Peça · Tècnic · Operatiu). TOT filtre viu a la URL (via setParams del pare): la URL és
// la font de veritat i el contracte de conjunt C2 la llegeix tal qual. La Peça és el CascadeSelector
// mode=multi amb showCounts: el pare li injecta els garment-counts del conjunt (menys la pròpia Peça).
// Els noms venen de useFilterOptions (opts), no del payload de la llista.

const MONO = 'IBM Plex Mono, monospace'
const CSV = (v) => (v || '').split(',').filter(Boolean)

export default function ModelsFilterPanel({ sp, setParams, opts, garmentCounts }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)
  const get = (k) => sp.get(k) || ''
  const set = (k, v) => setParams({ [k]: v || undefined, page: undefined })

  // Etiquetes d'ítem capturades en interactuar (el catàleg d'ítems no es carrega sencer); en fred
  // les famílies/grups es resolen d'opts i els ítems cauen a #id fins reobrir-ne la família (G-D5).
  const itemLabels = useRef({})

  // Peça: reconstrueix els nodes del CascadeSelector des dels tres params de la URL.
  const nodes = useMemo(() => {
    const gg = CSV(get('garment_group_codi__in')).map(c => ({ node_type: 'GROUP', group_codi: c, label: garmentGroupLabel(opts, c) }))
    const gt = CSV(get('garment_type__in')).map(id => ({ node_type: 'TYPE', garment_type_id: Number(id), label: garmentTypeLabel(opts, id, lang) }))
    const gti = CSV(get('garment_type_item__in')).map(id => ({ node_type: 'ITEM', garment_type_item_id: Number(id), label: itemLabels.current[id] || `#${id}` }))
    return [...gg, ...gt, ...gti]
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp, opts, lang])

  const onNodes = (next) => {
    next.forEach(n => { if (n.node_type === 'ITEM') itemLabels.current[n.garment_type_item_id] = n.label })
    const gg = next.filter(n => n.node_type === 'GROUP').map(n => n.group_codi)
    const gt = next.filter(n => n.node_type === 'TYPE').map(n => n.garment_type_id)
    const gti = next.filter(n => n.node_type === 'ITEM').map(n => n.garment_type_item_id)
    setParams({
      garment_group_codi__in: gg.join(',') || undefined,
      garment_type__in: gt.join(',') || undefined,
      garment_type_item__in: gti.join(',') || undefined,
      page: undefined,
    })
  }

  const selRuleset = opts.rulesets.find(r => String(r.id) === get('grading_rule_set'))

  return (
    <div style={panel}>
      {/* Identitat */}
      <Family title={t('models_filters.fam_identity')}>
        <Sel label={t('models_filters.customer')} value={get('customer')} onChange={v => set('customer', v)}
          placeholder={t('models_filters.all_customers')}
          options={opts.customers.map(c => ({ value: c.id, label: c.nom }))} />
        <Txt label={t('models_filters.collection')} value={get('collection')} onChange={v => set('collection', v)}
          placeholder={t('models_filters.collection_ph')} />
        <Num label={t('models_filters.any')} value={get('any')} onChange={v => set('any', v)} />
      </Family>

      {/* Peça — CascadeSelector multi amb comptadors del conjunt */}
      <Family title={t('models_filters.fam_garment')}>
        <div style={{ gridColumn: '1 / -1' }}>
          <CascadeSelector mode="multi" value={nodes} onChange={onNodes} showCounts counts={garmentCounts} />
        </div>
      </Family>

      {/* Tècnic */}
      <Family title={t('models_filters.fam_technical')}>
        <Sel label={t('models_filters.size_system')} value={get('size_system')} onChange={v => set('size_system', v)}
          placeholder={t('models_filters.all_size_systems')}
          options={opts.sizeSystems.map(s => ({ value: s.id, label: s.nom || s.codi }))} />
        <Sel label={t('models_filters.ruleset')} value={get('grading_rule_set')} onChange={v => set('grading_rule_set', v)}
          placeholder={t('models_filters.all_rulesets')}
          options={opts.rulesets.map(r => ({ value: r.id, label: r.nom || r.codi_sistema }))} />
        <Sel label={t('models_filters.target')} value={get('target')} onChange={v => set('target', v)}
          placeholder={t('models_filters.all_targets')}
          options={opts.targets.map(x => ({ value: x.codi, label: x.nom_en || x.codi }))} />
        <Sel label={t('models_filters.fit')} value={get('fit')} onChange={v => set('fit', v)}
          placeholder={t('models_filters.all_fits')}
          options={opts.fits.map(x => ({ value: x.codi, label: x.nom_en || x.codi }))} />
        <Sel label={t('models_filters.construction')} value={get('construction')} onChange={v => set('construction', v)}
          placeholder={t('models_filters.all_constructions')}
          options={opts.constructions.map(x => ({ value: x.codi, label: x.nom_en || x.codi }))} />
        {selRuleset && (selRuleset.codi_sistema || selRuleset.nom) && (
          <div style={{ gridColumn: '1 / -1', fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
            {t('models_filters.ruleset_layers')}: {selRuleset.codi_sistema || selRuleset.nom}
          </div>
        )}
      </Family>

      {/* Operatiu */}
      <Family title={t('models_filters.fam_operational')}>
        <Sel label={t('models_filters.responsable')} value={get('responsable')} onChange={v => set('responsable', v)}
          placeholder={t('models_filters.all_responsables')}
          options={opts.users.map(u => ({ value: u.profile_id, label: u.nom_complet || u.username }))} />
        <Sel label={t('models_filters.assignee')} value={get('assignee')} onChange={v => set('assignee', v)}
          placeholder={t('models_filters.all_assignees')}
          options={opts.users.map(u => ({ value: u.profile_id, label: u.nom_complet || u.username }))} />
        <Sel label={t('models_filters.task_type')} value={get('task_type')} onChange={v => set('task_type', v)}
          placeholder={t('models_filters.all_task_types')}
          options={opts.taskTypes.map(tt => ({ value: tt.code, label: tt.name || tt.code }))} />
        <Sel label={t('models_filters.task_status')} value={get('task_status')} onChange={v => set('task_status', v)}
          placeholder={t('models_filters.all_task_status')}
          options={['Pending', 'Paused', 'InProgress', 'Done'].map(s => ({ value: s, label: s }))} />
        <DateField label={t('models_filters.date_from')} value={get('data_objectiu_after')} onChange={v => set('data_objectiu_after', v)} />
        <DateField label={t('models_filters.date_to')} value={get('data_objectiu_before')} onChange={v => set('data_objectiu_before', v)} />
        <Toggle label={t('models_filters.watchpoints_open')} on={get('watchpoints_open') === 'true'}
          onChange={on => set('watchpoints_open', on ? 'true' : '')} />
        <Toggle label={t('models_filters.in_plan')} on={get('in_plan') === 'true'}
          onChange={on => set('in_plan', on ? 'true' : '')} />
      </Family>
    </div>
  )
}

function Family({ title, children }) {
  return (
    <div style={{ marginBottom: 4 }}>
      <p style={famTitle}>{title}</p>
      <div style={grid}>{children}</div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
      <span style={fieldLabel}>{label}</span>
      {children}
    </label>
  )
}

function Sel({ label, value, onChange, options, placeholder }) {
  return (
    <Field label={label}>
      <select value={value} onChange={e => onChange(e.target.value)} style={inp}>
        <option value="">{placeholder}</option>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </Field>
  )
}

function Txt({ label, value, onChange, placeholder }) {
  return (
    <Field label={label}>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={inp} />
    </Field>
  )
}

function Num({ label, value, onChange }) {
  return (
    <Field label={label}>
      <input type="number" value={value} onChange={e => onChange(e.target.value)} style={inp} />
    </Field>
  )
}

function DateField({ label, value, onChange }) {
  return (
    <Field label={label}>
      <input type="date" value={value} onChange={e => onChange(e.target.value)} style={inp} />
    </Field>
  )
}

function Toggle({ label, on, onChange }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)', cursor: 'pointer', alignSelf: 'end', paddingBottom: 6 }}>
      <input type="checkbox" checked={on} onChange={e => onChange(e.target.checked)} />
      {label}
    </label>
  )
}

const panel = {
  border: '0.5px solid var(--gray-l)', borderRadius: 10, background: 'var(--bg-card)',
  padding: '14px 16px', margin: '0 0 12px', display: 'flex', flexDirection: 'column', gap: 12,
}
const grid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, alignItems: 'start' }
const famTitle = { fontFamily: MONO, fontSize: 'var(--fs-label)', fontWeight: 700, color: 'var(--gold)', letterSpacing: '.08em', textTransform: 'uppercase', margin: '0 0 8px' }
const fieldLabel = { fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em' }
const inp = { padding: '6px 10px', border: '0.5px solid var(--gray-l)', borderRadius: 6, fontSize: 'var(--fs-body)', fontFamily: MONO, background: 'var(--white)', color: 'var(--text-main)', width: '100%', boxSizing: 'border-box' }
