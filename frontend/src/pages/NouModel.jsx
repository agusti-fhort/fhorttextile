import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { models, garmentTypes, garmentGroups } from '../api/endpoints'
import { SizingProfileWizard } from '../components/SizingProfileWizard'
import POMBrowser from '../components/POMBrowser/POMBrowser'

const API = import.meta.env.VITE_API_URL || ''

const CONFIDENCE_BADGES = {
  high:   { label: 'HIGH',   bg: '#EBF8EC', color: '#1E8449' },
  medium: { label: 'MEDIUM', bg: '#FEF9E7', color: '#7D6608' },
  low:    { label: 'LOW',    bg: '#FDEDEC', color: '#C0392B' },
}

const TAB_KEYS = ['model', 'mesures', 'fitting', 'fitxers', 'servei', 'control']
const TABS_DISABLED_ON_CREATE = new Set(['fitting', 'fitxers', 'servei', 'control'])

const TEMPORADES = ['SS', 'FW', 'CO', 'SP']
const FIT_TYPES  = ['Regular', 'Slim', 'Relaxed', 'Oversize', 'Tailored']
const ESTATS     = ['Nou', 'EnCurs', 'EnRevisio', 'Tancat']
const PRIORITATS = [1, 3, 4, 5]
// Els valors han de coincidir amb ORIGEN_PATRO_CHOICES del backend.
const ORIGENS_PATRO = [
  { value: 'CAD Client',     labelKey: 'cad_client' },
  { value: 'Digitalització', labelKey: 'digitalitzacio' },
  { value: 'Des de zero',    labelKey: 'des_de_zero' },
]

export default function NouModel() {
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useTranslation()
  const anyActual = new Date().getFullYear()

  // Estat d'importació via location.state (vingut del wizard d'import).
  const importState = location.state?.fromImport ? location.state : null
  const isImport = !!importState

  // El matching POM-fitxa → POMMaster passa al backend a create-from-extraction/,
  // així que aquí no hi ha codis POMMaster encara. L'usuari els assigna al
  // POMBrowser si vol; el backend resol la resta.

  // Pre-fill del SizingProfileWizard via wizard_context: mostrem el resum
  // directament i evitem que l'usuari hagi de tornar a configurar talles.
  const initialSizingResult = (isImport && importState.wizard_context?.size_system_id)
    ? {
        size_system_id:      importState.wizard_context.size_system_id,
        size_system_nom:     importState.wizard_context.size_system_nom,
        grading_rule_set_id: importState.wizard_context.grading_rule_set_id,
        grading_rule_set_nom:importState.wizard_context.grading_rule_set_nom,
        base_size_label:     importState.wizard_context.base_size_label,
        size_run_model:      importState.wizard_context.size_run_model,
        target_codi:         importState.wizard_context.target_codi,
        construction_codi:   importState.wizard_context.construction_codi,
      }
    : null

  const [activeTab, setActiveTab] = useState('model')
  const [form, setForm] = useState({
    // Tab Model — camps reals del backend
    codi_client: '',
    codi_tenant: '',
    nom_prenda: '',
    descripcio: '',
    temporada: 'SS',
    any: anyActual,
    color_referencia: '',
    familia: '',
    estat: 'Nou',
    prioritat: 3,
    data_objectiu: '',
    observacions: '',
    origen_patro: '',
    versio: '',
    // Tab Mesures
    garment_type: '',
    garment_group: '',
    fit_type: 'Regular',
    size_system: '',
    base_size_label: '',
    size_run_model: '',
    grading_rule_set: '',
    // TODO(backend): persistir els POMs assignats al Model
    // (cal endpoint/camp al backend; per ara només UI a la wizard).
    selected_pom_codes: isImport ? [] : [],
    // Pre-fill via location.state.prefill — sobreescriu els defaults
    ...(importState?.prefill || {}),
  })

  const [gTypes, setGTypes] = useState([])
  const [gGroups, setGGroups] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [showWizard, setShowWizard] = useState(false)
  const [sizingResult, setSizingResult] = useState(initialSizingResult)

  useEffect(() => {
    garmentTypes.list({ page_size: 200 }).then(r => setGTypes(r.data.results || [])).catch(() => {})
    garmentGroups.list({ page_size: 200 }).then(r => setGGroups(r.data.results || [])).catch(() => {})
  }, [])

  // Auto-deriva garment_group quan ve d'importació amb garment_type pre-emplenat
  // i les llistes (gTypes/gGroups) ja han carregat. Replica handleGarmentTypeChange.
  useEffect(() => {
    if (!isImport || !form.garment_type || form.garment_group) return
    if (gTypes.length === 0 || gGroups.length === 0) return
    const gt = gTypes.find(g => String(g.id) === String(form.garment_type))
    const grupCodi = gt?.grup
    if (!grupCodi) return
    const group = gGroups.find(g => g.codi === grupCodi)
    if (group) setForm(f => ({ ...f, garment_group: group.id }))
  }, [isImport, form.garment_type, form.garment_group, gTypes, gGroups])

  const setField = (k, v) => setForm(f => ({ ...f, [k]: v }))

  // Fix 1 (S15) — quan canvia garment_type, omple garment_group automàticament
  // a partir del camp `grup` del GarmentType seleccionat.
  // La dada ja està a gTypes (carregat al mount), evitant una crida extra a
  // /api/v1/garment-types/<id>/. gGroups es mapeja per codi → id.
  const handleGarmentTypeChange = (gtId) => {
    setForm(f => {
      const gt = gTypes.find(g => String(g.id) === String(gtId))
      const grupCodi = gt?.grup || ''
      const group = grupCodi
        ? gGroups.find(g => g.codi === grupCodi)
        : null
      return {
        ...f,
        garment_type: gtId,
        garment_group: group ? group.id : f.garment_group,
      }
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.nom_prenda) {
      setError(t('errors.required') + ': ' + t('model.fields.nom_prenda'))
      return
    }
    if (!form.garment_type) {
      setError(t('errors.required') + ': ' + t('model.fields.garment_type'))
      setActiveTab('mesures')
      return
    }

    setSubmitting(true)
    try {
      let modelId
      if (isImport) {
        // Branca d'importació: el backend reb extracted + wizard_context + overrides
        // i s'encarrega de construir el model amb els POMs i talles detectats.
        const token = localStorage.getItem('access_token')
        const r = await fetch(`${API}/api/v1/models/create-from-extraction/`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            extracted: importState.extracted,
            wizard_context: importState.wizard_context,
            overrides: { ...form },
          }),
        })
        const data = await r.json()
        if (!r.ok) {
          throw new Error(data.error || data.detail || `HTTP ${r.status}`)
        }
        modelId = data.model_id || data.id
      } else {
        // Branca normal — sense canvis.
        // codi_tenant és REQUIRED; si no s'ha posat, derivem-lo dels 3 primers
        // chars de codi_client (uppercase).
        const codiTenantAuto = (form.codi_tenant || form.codi_client.slice(0, 3).toUpperCase() || 'TNT').slice(0, 3)
        const payload = {
          nom_prenda: form.nom_prenda,
          codi_client: form.codi_client,
          codi_tenant: codiTenantAuto,
          descripcio: form.descripcio || null,
          temporada: form.temporada,
          any: Number(form.any),
          color_referencia: form.color_referencia || null,
          familia: form.familia || null,
          estat: form.estat,
          prioritat: Number(form.prioritat),
          observacions: form.observacions || null,
          garment_type: form.garment_type,
          fit_type: form.fit_type,
          sequencial: 1,  // signal pre_save recalcula automàticament
        }
        if (form.data_objectiu)   payload.data_objectiu = form.data_objectiu
        if (form.size_system)     payload.size_system = form.size_system
        if (form.base_size_label) payload.base_size_label = form.base_size_label
        if (form.size_run_model)  payload.size_run_model = form.size_run_model
        if (form.grading_rule_set)payload.grading_rule_set = form.grading_rule_set
        if (form.garment_group)   payload.garment_group = form.garment_group
        if (form.origen_patro)    payload.origen_patro = form.origen_patro
        if (form.versio)          payload.versio = form.versio

        const res = await models.create(payload)
        modelId = res.data.id
      }
      navigate(`/models/${modelId}`)
    } catch (err) {
      const detail = err.response?.data ? JSON.stringify(err.response.data) : err.message
      setError(`${t('errors.create_failed')}: ${detail}`)
      setSubmitting(false)
    }
  }

  return (
    <div>
      <button onClick={() => navigate('/models')} style={btnGhost}>
        <i className="ti ti-arrow-left" style={{fontSize: 14}} />
        {t('app.back')}
      </button>

      <div style={{marginBottom: '1.2rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>{t('model.new')}</h1>
      </div>

      {isImport && (
        <div style={{
          background: '#EBF8EC', border: '1px solid #A9DFBF',
          borderRadius: 8, padding: '0.75rem 1rem', marginBottom: '1rem',
          fontSize: '0.85rem', color: '#1E8449',
        }}>
          <strong>Dades importades de fitxa tècnica.</strong>{' '}
          Revisa i completa els camps. Els POMs detectats es mostraran abans de guardar.
        </div>
      )}

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: 4,
        borderBottom: '0.5px solid #e4e4e2',
        marginBottom: '1rem',
      }}>
        {TAB_KEYS.map(k => {
          const disabled = TABS_DISABLED_ON_CREATE.has(k)
          const isActive = activeTab === k
          return (
            <button
              key={k}
              type="button"
              onClick={() => !disabled && setActiveTab(k)}
              disabled={disabled}
              title={disabled ? t('model.tab_unavailable') : ''}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: isActive ? '2px solid var(--gold)' : '2px solid transparent',
                padding: '8px 14px',
                fontSize: 12,
                fontFamily: 'var(--font)',
                fontWeight: isActive ? 500 : 400,
                color: disabled ? '#bbb' : isActive ? 'var(--charcoal)' : 'var(--gray)',
                cursor: disabled ? 'not-allowed' : 'pointer',
              }}
            >
              {t(`model.tabs.${k}`)}
            </button>
          )
        })}
      </div>

      <form onSubmit={handleSubmit} style={{
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 12,
        padding: '1.4rem 1.6rem',
        maxWidth: 980,
      }}>
        {activeTab === 'model' && (
          <Grid>
            <Field label={t('model.fields.codi_intern')}>
              <Input value="" disabled placeholder="(auto-generat)" />
            </Field>
            <Field label={t('model.fields.codi_client') + ' *'}>
              <Input value={form.codi_client} onChange={v => setField('codi_client', v)} required />
            </Field>

            <Field label={t('model.fields.codi_tenant')} hint={t('model.fields.codi_tenant_help')}>
              <Input value={form.codi_tenant} onChange={v => setField('codi_tenant', v.toUpperCase().slice(0, 3))} maxLength={3} placeholder="(auto: 3 prim. de codi_client)" />
            </Field>
            <Field label={t('model.fields.familia')}>
              <Input value={form.familia} onChange={v => setField('familia', v)} />
            </Field>

            <Field label={t('model.fields.nom_prenda') + ' *'} span={2}>
              <Input value={form.nom_prenda} onChange={v => setField('nom_prenda', v)} required />
            </Field>

            <Field label={t('model.fields.descripcio')} span={2}>
              <Textarea value={form.descripcio} onChange={v => setField('descripcio', v)} rows={3} />
            </Field>

            <Field label={t('model.fields.temporada')}>
              <Select value={form.temporada} onChange={v => setField('temporada', v)}
                options={TEMPORADES.map(s => ({ value: s, label: t(`model.temporades.${s}`) }))} />
            </Field>
            <Field label={t('model.fields.any')}>
              <Input type="number" value={form.any} onChange={v => setField('any', Number(v))} />
            </Field>

            <Field label={t('model.fields.color_referencia')}>
              <Input value={form.color_referencia} onChange={v => setField('color_referencia', v)} />
            </Field>
            <Field label={t('model.fields.estat')}>
              <Select value={form.estat} onChange={v => setField('estat', v)}
                options={ESTATS.map(e => ({ value: e, label: t(`model.estats.${e}`) }))} />
            </Field>

            <Field label={t('model.fields.prioritat')}>
              <Select value={form.prioritat} onChange={v => setField('prioritat', Number(v))}
                options={PRIORITATS.map(p => ({ value: p, label: `${p} · ${t(`model.prioritats.${p}`)}` }))} />
            </Field>
            <Field label={t('model.fields.responsable')}>
              <Input value="" disabled placeholder={t('model.unsupported_field')} />
            </Field>

            <Field label={t('model.fields.data_entrada')}>
              <Input value="" disabled placeholder="(auto)" />
            </Field>
            <Field label={t('model.fields.data_objectiu')}>
              <Input type="date" value={form.data_objectiu} onChange={v => setField('data_objectiu', v)} />
            </Field>

            <SectionHeader>{t('model.sections.origen')}</SectionHeader>
            <Field label={t('model.fields.origen_patro')}>
              <Select
                value={form.origen_patro}
                onChange={v => setField('origen_patro', v)}
                options={[
                  { value: '', label: '—' },
                  ...ORIGENS_PATRO.map(o => ({ value: o.value, label: t(`model.origens.${o.labelKey}`) })),
                ]}
              />
            </Field>
            <Field label={t('model.fields.versio')}>
              <Input value={form.versio} onChange={v => setField('versio', v)} placeholder="v1" />
            </Field>

            <Field label={t('model.fields.observacions')} span={2}>
              <Textarea value={form.observacions} onChange={v => setField('observacions', v)} rows={4} />
            </Field>
          </Grid>
        )}

        {activeTab === 'mesures' && (
          <Grid>
            <Field label={t('model.fields.garment_type') + ' *'}>
              <Select value={form.garment_type} onChange={v => handleGarmentTypeChange(v)}
                options={[{ value: '', label: '—' }, ...gTypes.map(g => ({ value: g.id, label: g.nom_client || g.codi_client }))]} />
            </Field>
            <Field label={t('model.fields.garment_group')}>
              <Select value={form.garment_group} onChange={v => setField('garment_group', v)}
                options={[{ value: '', label: '—' }, ...gGroups.map(g => ({ value: g.id, label: g.nom }))]} />
            </Field>

            <Field label={t('model.fields.fit_type')}>
              <Select value={form.fit_type} onChange={v => setField('fit_type', v)}
                options={FIT_TYPES.map(f => ({ value: f, label: f }))} />
            </Field>

            <Field label="Configuració de talles" span={2}>
              {!showWizard && !sizingResult && (
                <button type="button" onClick={() => setShowWizard(true)} style={btnSecondary}>
                  <i className="ti ti-plus" style={{fontSize: 14}} />
                  Configurar talles
                </button>
              )}

              {showWizard && (
                <div style={{
                  marginTop: 8, padding: '1rem',
                  border: '0.5px solid #e4e4e2', borderRadius: 8,
                  background: 'var(--white)',
                }}>
                  <SizingProfileWizard
                    initialValues={isImport ? {
                      target: importState.wizard_context?.target_codi,
                      construction: importState.wizard_context?.construction_codi,
                      size_run: importState.prefill?.size_run_model,
                      base_size: importState.prefill?.base_size_label,
                    } : {}}
                    onComplete={(result) => {
                      setSizingResult(result)
                      setShowWizard(false)
                      setForm(f => ({
                        ...f,
                        size_system: result.size_system_id,
                        grading_rule_set: result.grading_rule_set_id,
                        base_size_label: result.base_size_label,
                        size_run_model: result.size_run_model,
                      }))
                    }}
                    onCancel={() => setShowWizard(false)}
                  />
                </div>
              )}

              {sizingResult && !showWizard && (
                <div style={{
                  padding: '0.8rem 1rem',
                  border: '0.5px solid #e4e4e2', borderRadius: 8,
                  background: 'var(--white)',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  gap: 12,
                }}>
                  <div>
                    <div style={{fontSize: 13, fontWeight: 500}}>
                      {sizingResult.size_system_nom} · {sizingResult.base_size_label} ★
                    </div>
                    <div style={{fontSize: 11, color: 'var(--gray)', fontWeight: 300, marginTop: 2, fontVariantNumeric: 'tabular-nums'}}>
                      {sizingResult.size_run_model}
                    </div>
                  </div>
                  <button type="button" onClick={() => setShowWizard(true)} style={btnSecondary}>
                    <i className="ti ti-edit" style={{fontSize: 14}} />
                    Canviar
                  </button>
                </div>
              )}
            </Field>

            <Field label="Punts de mesura (POMs)" span={2} hint={form.garment_type ? `${(form.selected_pom_codes || []).length} POMs assignats` : 'Selecciona primer un tipus de prenda'}>
              {isImport && (importState.extracted?.poms?.length > 0) && (
                <PomsImportPreview poms={importState.extracted.poms} />
              )}
              {form.garment_type ? (
                <div style={{
                  height: '60vh',
                  border: '0.5px solid #e4e4e2', borderRadius: 8,
                  overflow: 'hidden', background: 'var(--white)',
                }}>
                  <POMBrowser
                    mode="assign"
                    garmentTypeCode={form.garment_type}
                    activePoms={form.selected_pom_codes || []}
                    onTogglePom={(pomCode) => {
                      setForm(f => {
                        const current = f.selected_pom_codes || []
                        const updated = current.includes(pomCode)
                          ? current.filter(c => c !== pomCode)
                          : [...current, pomCode]
                        return { ...f, selected_pom_codes: updated }
                      })
                    }}
                  />
                </div>
              ) : (
                <div style={{
                  padding: '1rem 1.2rem',
                  border: '0.5px dashed #e4e4e2', borderRadius: 8,
                  fontSize: 12, color: 'var(--gray)',
                  background: 'var(--white)',
                }}>
                  Selecciona un tipus de prenda per assignar POMs al model.
                </div>
              )}
            </Field>
          </Grid>
        )}

        {TABS_DISABLED_ON_CREATE.has(activeTab) && (
          <div style={{
            padding: '2rem',
            textAlign: 'center',
            color: 'var(--gray)',
            fontSize: 12,
            background: 'var(--gray-l)',
            borderRadius: 8,
          }}>
            <i className="ti ti-lock" style={{fontSize: 22, display: 'block', marginBottom: 10}} />
            {t('model.tab_unavailable')}
          </div>
        )}

        {error && (
          <div style={{
            marginTop: '1rem', padding: '0.7rem 1rem',
            background: 'var(--err-bg)', color: 'var(--err)',
            borderRadius: 8, fontSize: 12,
          }}>
            {error}
          </div>
        )}

        <div style={{
          marginTop: '1.5rem', display: 'flex',
          justifyContent: 'flex-end', gap: '0.6rem',
        }}>
          <button type="button" onClick={() => navigate('/models')} style={btnSecondary}>
            {t('app.cancel')}
          </button>
          <button type="submit" disabled={submitting} style={{
            ...btnPrimary,
            background: submitting ? 'rgba(194,122,42,0.5)' : 'var(--gold)',
            cursor: submitting ? 'not-allowed' : 'pointer',
          }}>
            <i className="ti ti-check" style={{fontSize: 14}} />
            {submitting ? t('model.actions.creating') : t('model.actions.create')}
          </button>
        </div>
      </form>
    </div>
  )
}

const btnGhost = {
  background: 'none', border: 'none', cursor: 'pointer',
  color: 'var(--gray)', fontSize: 12, fontFamily: 'var(--font)',
  marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: 6,
}
const btnSecondary = {
  background: 'var(--white)', color: 'var(--gray)',
  border: '0.5px solid #e4e4e2', borderRadius: 8,
  padding: '8px 16px', fontSize: 12,
  cursor: 'pointer', fontFamily: 'var(--font)',
}
const btnPrimary = {
  color: 'white', border: 'none', borderRadius: 8,
  padding: '8px 20px', fontSize: 12, fontWeight: 500,
  fontFamily: 'var(--font)',
  display: 'flex', alignItems: 'center', gap: 6,
}

function Grid({ children }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '1.1rem',
    }}>
      {children}
    </div>
  )
}

function SectionHeader({ children }) {
  return (
    <div style={{
      gridColumn: '1 / -1',
      marginTop: '0.6rem',
      paddingBottom: 4,
      borderBottom: '0.5px solid #e4e4e2',
      fontSize: 10,
      letterSpacing: '0.12em',
      textTransform: 'uppercase',
      color: 'var(--gray)',
      fontWeight: 500,
    }}>
      {children}
    </div>
  )
}

function Field({ label, children, hint, span = 1 }) {
  return (
    <label style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      gridColumn: span === 2 ? '1 / -1' : 'auto',
    }}>
      <span style={{fontSize: 11, color: 'var(--gray)', fontWeight: 400}}>{label}</span>
      {children}
      {hint && (
        <span style={{fontSize: 10, color: 'var(--gray)', fontWeight: 300}}>{hint}</span>
      )}
    </label>
  )
}

const inputStyle = {
  background: 'var(--white)',
  border: '0.5px solid #e4e4e2',
  borderRadius: 8,
  padding: '8px 12px',
  fontSize: 12,
  fontFamily: 'var(--font)',
  outline: 'none',
}

function Input({ value, onChange, type = 'text', required, disabled, placeholder }) {
  return (
    <input
      type={type}
      value={value ?? ''}
      required={required}
      disabled={disabled}
      placeholder={placeholder}
      onChange={e => onChange && onChange(e.target.value)}
      style={{
        ...inputStyle,
        background: disabled ? '#f6f6f4' : 'var(--white)',
        color: disabled ? '#aaa' : 'inherit',
        cursor: disabled ? 'not-allowed' : 'text',
      }}
    />
  )
}

function Textarea({ value, onChange, rows = 3 }) {
  return (
    <textarea
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      rows={rows}
      style={{
        ...inputStyle,
        width: '100%',
        resize: 'vertical',
      }}
    />
  )
}

function Select({ value, onChange, options }) {
  return (
    <select
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      style={{
        ...inputStyle,
        appearance: 'none',
        backgroundImage: 'url("data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'10\' height=\'10\' viewBox=\'0 0 10 10\'><path d=\'M2 4 L5 7 L8 4\' stroke=\'%23868685\' stroke-width=\'1.2\' fill=\'none\'/></svg>")',
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 10px center',
        paddingRight: 28,
      }}
    >
      {options.map(o => (
        <option key={String(o.value)} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

function PomsImportPreview({ poms }) {
  return (
    <div style={{
      marginBottom: 12, padding: '0.75rem',
      border: '1px solid #e5e7eb', borderRadius: 8, background: 'var(--white)',
    }}>
      <div style={{
        fontSize: 11, fontWeight: 600, color: '#666', marginBottom: 8,
        textTransform: 'uppercase', letterSpacing: '0.06em',
      }}>
        POMs detectats al document ({poms.length})
      </div>
      <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#f8f9fa' }}>
            {['Codi fitxa', 'Descripció', 'Valor base (cm)', 'Confiança IA'].map(h => (
              <th key={h} style={{
                padding: '0.4rem 0.6rem', textAlign: 'left',
                fontWeight: 600, color: '#666', fontSize: 11,
                borderBottom: '1px solid #e5e7eb',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {poms.map((p, i) => {
            const conf = String(p.confidence || 'low').toLowerCase()
            const badge = CONFIDENCE_BADGES[conf] || CONFIDENCE_BADGES.low
            return (
              <tr key={i} style={{
                background: i % 2 === 0 ? 'var(--white)' : '#fafafa',
                borderBottom: '1px solid #f0f0f0',
              }}>
                <td style={{
                  padding: '0.4rem 0.6rem', fontFamily: 'IBM Plex Mono, monospace',
                  fontSize: 11, color: '#c27a2a', fontWeight: 600,
                }}>{p.code || '—'}</td>
                <td style={{
                  padding: '0.4rem 0.6rem', fontSize: 11, color: '#333',
                }}>{p.description || <span style={{ color: '#aaa' }}>—</span>}</td>
                <td style={{
                  padding: '0.4rem 0.6rem', fontFamily: 'IBM Plex Mono, monospace',
                  textAlign: 'right',
                }}>{p.base_value_cm != null ? p.base_value_cm : '—'}</td>
                <td style={{ padding: '0.4rem 0.6rem' }}>
                  <span style={{
                    fontSize: 10, padding: '0.15rem 0.4rem', borderRadius: 3,
                    background: badge.bg, color: badge.color,
                    fontWeight: 600, letterSpacing: '0.04em',
                  }}>{badge.label}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p style={{ margin: '0.6rem 0 0', fontSize: 11, color: '#888' }}>
        L'assignació de POMs es resoldrà automàticament en crear el model.
      </p>
    </div>
  )
}
