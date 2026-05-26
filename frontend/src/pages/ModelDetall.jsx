
import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import useAuthStore from "../store/auth"
import { FaseStepper } from "../components/FaseStepper"
import { EstatBadge } from "../components/EstatBadge"
import { TaulaMesures } from "../components/TaulaMesures"
import { KanbanTasquesModel } from "../components/KanbanTasquesModel"
import { TallaBaseWizard } from "../components/TallaBaseWizard"
import { DesignFreezePanel } from "../components/DesignFreezePanel"
import { SizingProfileWizard } from "../components/SizingProfileWizard"
import { ExportModelPDF } from "../components/ExportButton"

const API = import.meta.env.VITE_API_URL || ""
const TABS = ["Model", "Mesures", "Size & Fitting", "Fitxers", "Servei", "Control"]

function useModel(id, token) {
  const [model, setModel] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch_ = () => {
    if (!id || !token) return
    setLoading(true)
    fetch(`${API}/api/v1/models/${id}/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => { setModel(d); setLoading(false) })
      .catch(e => { setError(`Error ${e}`); setLoading(false) })
  }

  useEffect(fetch_, [id, token])
  return { model, loading, error, refresh: fetch_ }
}

// ─── Helpers UI ──────────────────────────────────────────────────────────────

function FieldRow({ label, children, mono }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 8, padding: '5px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ color: 'var(--text-main)', fontSize: 11, fontFamily: 'IBM Plex Mono, monospace', paddingTop: 2 }}>
        {label}
      </span>
      <span style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: mono ? 'IBM Plex Mono, monospace' : 'inherit' }}>
        {children ?? <span style={{ color: 'var(--text-muted)' }}>—</span>}
      </span>
    </div>
  )
}

function Section({ title, children, collapsible }) {
  const [open, setOpen] = useState(true)
  return (
    <div style={{ marginBottom: 20 }}>
      {title && (
        <div
          onClick={() => collapsible && setOpen(o => !o)}
          style={{
            fontSize: 10,
            fontFamily: 'IBM Plex Mono, monospace',
            color: 'var(--text-muted)',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            marginBottom: 8,
            cursor: collapsible ? 'pointer' : 'default',
            userSelect: 'none',
          }}
        >
          {collapsible && (open ? '▾ ' : '▸ ')}{title}
        </div>
      )}
      {open && children}
    </div>
  )
}

function TabBtn({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '6px 14px',
        background: active ? 'var(--gold-pale)' : 'transparent',
        color: active ? 'var(--gold)' : 'var(--text-muted)',
        border: 'none',
        borderBottom: active ? '2px solid var(--gold)' : '2px solid transparent',
        fontSize: 11,
        fontFamily: 'IBM Plex Mono, monospace',
        cursor: 'pointer',
        whiteSpace: 'nowrap',
        transition: 'all 0.1s',
      }}
    >
      {label}
    </button>
  )
}

// ─── Tabs ────────────────────────────────────────────────────────────────────

function TabModel({ model, token, onSave }) {
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (model) setForm({
      nom_prenda: model.nom_prenda || '',
      color_referencia: model.color_referencia || '',
      temporada: model.temporada || '',
      any: model.any || '',
      origen_patro: model.origen_patro || '',
      versio: model.versio || '',
    })
  }, [model])

  const save = async () => {
    setSaving(true)
    try {
      const r = await fetch(`${API}/api/v1/models/${model.id}/`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(form),
      })
      if (r.ok) { const d = await r.json(); onSave && onSave(d) }
    } catch (e) { console.error(e) }
    setSaving(false)
  }

  const field = (key) => (
    <input
      value={form[key] || ''}
      onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
      style={inputStyle}
    />
  )

  const select_ = (key, opts) => (
    <select
      value={form[key] || ''}
      onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
      style={inputStyle}
    >
      <option value="">—</option>
      {opts.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  )

  return (
    <div>
      <Section title="Identificació">
        <FieldRow label="Codi" mono>{model?.codi}</FieldRow>
        <FieldRow label="Client">{model?.client_nom || model?.client}</FieldRow>
        <FieldRow label="Nom prenda">{field('nom_prenda')}</FieldRow>
        <FieldRow label="Color ref.">{field('color_referencia')}</FieldRow>
        <FieldRow label="Versió">{field('versio')}</FieldRow>
      </Section>
      <Section title="Temporada">
        <FieldRow label="Temporada">
          {select_('temporada', ['SS', 'FW', 'CO', 'SP'])}
        </FieldRow>
        <FieldRow label="Any">{field('any')}</FieldRow>
      </Section>
      <Section title="Origen">
        <FieldRow label="Origen patró">
          {select_('origen_patro', ['CAD Client', 'Digitalització', 'Des de zero'])}
        </FieldRow>
        <FieldRow label="Tipologia">{model?.tipologia_model_nom || model?.tipologia_model}</FieldRow>
      </Section>
      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button onClick={save} disabled={saving} style={btnPrimary}>
          {saving ? 'Guardant...' : 'Guardar'}
        </button>
      </div>
    </div>
  )
}

function TabMesures({ model, token, onSave }) {
  const [gGroups, setGGroups] = useState([])
  const [garmentGroup, setGarmentGroup] = useState('')
  const [saving, setSaving] = useState(false)
  const [showSizingWizard, setShowSizingWizard] = useState(false)
  const [sizingSaving, setSizingSaving] = useState(false)
  const [sizingError, setSizingError] = useState(null)

  useEffect(() => {
    if (!token) return
    fetch(`${API}/api/v1/garment-groups/?page_size=200`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (d) setGGroups(d.results || (Array.isArray(d) ? d : [])) })
      .catch(() => {})
  }, [token])

  useEffect(() => {
    setGarmentGroup(model?.garment_group ?? '')
  }, [model?.id, model?.garment_group])

  const dirty = String(garmentGroup ?? '') !== String(model?.garment_group ?? '')

  const save = async () => {
    setSaving(true)
    try {
      const r = await fetch(`${API}/api/v1/models/${model.id}/`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ garment_group: garmentGroup === '' ? null : garmentGroup }),
      })
      if (r.ok) { const d = await r.json(); onSave && onSave(d) }
    } catch (e) { console.error(e) }
    setSaving(false)
  }

  const saveSizing = async (result) => {
    setSizingSaving(true)
    setSizingError(null)
    try {
      const r = await fetch(`${API}/api/v1/models/${model.id}/`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          size_system: result.size_system_id,
          grading_rule_set: result.grading_rule_set_id,
          base_size_label: result.base_size_label,
          size_run_model: result.size_run_model,
        }),
      })
      if (r.ok) {
        const d = await r.json()
        onSave && onSave(d)
        setShowSizingWizard(false)
      } else {
        const d = await r.json().catch(() => ({}))
        setSizingError(d.detail || 'Error guardant la configuració de talles')
      }
    } catch (e) {
      setSizingError(String(e))
    }
    setSizingSaving(false)
  }

  return (
    <div>
      <Section title="Tipus de prenda">
        <FieldRow label="Garment Type">{model?.garment_type_nom || model?.garment_type}</FieldRow>
        <FieldRow label="Garment Group">
          <select
            value={garmentGroup ?? ''}
            onChange={e => setGarmentGroup(e.target.value)}
            style={inputStyle}
          >
            <option value="">—</option>
            {gGroups.map(g => (
              <option key={g.id} value={g.id}>{g.nom}</option>
            ))}
          </select>
        </FieldRow>
        <FieldRow label="Fit Type">{model?.fit_type_nom || model?.fit_type}</FieldRow>
      </Section>
      <Section title="Sistema de talla">
        <FieldRow label="Size System">{model?.size_system_nom || model?.size_system || '—'}</FieldRow>
        <FieldRow label="Talla base" mono>{model?.base_size_label || '—'}</FieldRow>
        <FieldRow label="Run de talles" mono>{model?.size_run_model || '—'}</FieldRow>
        <FieldRow label="Núm. talles">{
          model?.size_run_model
            ? model.size_run_model.split('·').filter(s => s.trim()).length
            : '—'
        }</FieldRow>
        <FieldRow label="Grading">{model?.grading_rule_set_nom || model?.grading_rule_set || '—'}</FieldRow>
        <div style={{ marginTop: 8 }}>
          {!showSizingWizard ? (
            <button onClick={() => setShowSizingWizard(true)} style={btnSecondary} disabled={sizingSaving}>
              {model?.size_system ? 'Reconfigurar talles' : 'Configurar talles'}
            </button>
          ) : (
            <div style={{
              marginTop: 8, padding: '1rem',
              border: '1px solid #e0d5c5', borderRadius: 6,
              background: '#fff',
            }}>
              <SizingProfileWizard
                onComplete={saveSizing}
                onCancel={() => setShowSizingWizard(false)}
              />
            </div>
          )}
          {sizingError && (
            <div style={{ marginTop: 8, color: '#a32d2d', fontSize: 11 }}>{sizingError}</div>
          )}
        </div>
      </Section>
      {dirty && (
        <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <button onClick={save} disabled={saving} style={btnPrimary}>
            {saving ? 'Guardant...' : 'Guardar'}
          </button>
        </div>
      )}
    </div>
  )
}

function TabSF({ model, token, refresh }) {
  const [sf, setSF] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!model?.id) return
    setLoading(true)
    fetch(`${API}/api/v1/size-fittings/?model=${model.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => {
        const results = Array.isArray(d) ? d : (d.results || [])
        setSF(results[0] || null)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [model?.id])

  if (loading) return <div style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: 'IBM Plex Mono, monospace' }}>Carregant SF...</div>

  return (
    <div>
      <DesignFreezePanel model={model} token={token} onApproved={refresh} />

      {sf && (
        <>
          <Section title="Configuració de tallatge">
            <FieldRow label="Size system">{sf.size_system_nom || model.size_system_nom || "—"}</FieldRow>
            <FieldRow label="Talla base" mono>{model.base_size_label || "—"}</FieldRow>
            <FieldRow label="Run de talles" mono>{model.size_run_model || "—"}</FieldRow>
            <FieldRow label="Grading">{model.grading_rule_set_nom || "—"}</FieldRow>
          </Section>

          <Section title="Mesures talla base">
            <TallaBaseWizard
              model={model}
              sfId={sf.id}
              token={token}
              onComplete={() => { refresh && refresh() }}
            />
          </Section>

          {(sf.estat === "TallesGenerades" || sf.estat === "BaseTancada") && (
            <Section title="Taula de mesures per talla">
              <TaulaMesures sfId={sf.id} token={token} />
            </Section>
          )}
        </>
      )}

      {!sf && (
        <div style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: 'IBM Plex Mono, monospace', padding: '12px 0' }}>
          No hi ha Size & Fitting per a aquest model.
        </div>
      )}
    </div>
  )
}

function TabFitxers({ model, token }) {
  const [fitxers, setFitxers] = useState([])
  const [uploading, setUploading] = useState(false)
  const CATS = ['Patrons', 'Dissenys', 'Fittings', 'Documents']

  useEffect(() => {
    if (!model?.id) return
    fetch(`${API}/api/v1/model-fitxers/?model=${model.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => setFitxers(Array.isArray(d) ? d : (d.results || [])))
  }, [model?.id])

  const handleUpload = async (e, categoria) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('fitxer', file)
    fd.append('model', model.id)
    fd.append('categoria', categoria)
    try {
      const r = await fetch(`${API}/api/v1/model-fitxers/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      })
      if (r.ok) {
        const d = await r.json()
        setFitxers(f => [d, ...f])
      }
    } catch (e) { console.error(e) }
    setUploading(false)
  }

  const bycat = CATS.reduce((a, c) => {
    a[c] = fitxers.filter(f => f.categoria === c)
    return a
  }, {})

  return (
    <div>
      {CATS.map(cat => (
        <Section key={cat} title={cat} collapsible>
          {bycat[cat].length === 0
            ? <div style={{ color: 'var(--text-main)', fontSize: 11, padding: '4px 0' }}>Sense fitxers</div>
            : bycat[cat].map(f => (
              <div key={f.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                <a
                  href={f.url || f.fitxer}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: '#6a6aaa', fontSize: 11, fontFamily: 'IBM Plex Mono, monospace' }}
                >
                  {f.nom_fitxer}
                </a>
                <span style={{ color: 'var(--text-main)', fontSize: 10 }}>
                  {f.versio ? `v${f.versio}` : ''}
                </span>
              </div>
            ))
          }
          <label style={{ display: 'inline-block', marginTop: 8, cursor: 'pointer' }}>
            <span style={{
              fontSize: 10, color: 'var(--text-main)', fontFamily: 'IBM Plex Mono, monospace',
              padding: '3px 8px', border: '1px solid var(--border)', borderRadius: 3,
            }}>
              {uploading ? 'Pujant...' : `+ Afegir a ${cat}`}
            </span>
            <input
              type="file"
              style={{ display: 'none' }}
              disabled={uploading}
              onChange={(e) => handleUpload(e, cat)}
            />
          </label>
        </Section>
      ))}
    </div>
  )
}

function TabServei({ model, token }) {
  const [serveis, setServeis] = useState([])
  const [paquets, setPaquets] = useState([])
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    if (!model?.id) return
    fetch(`${API}/api/v1/model-serveis/?model=${model.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => setServeis(Array.isArray(d) ? d : (d.results || [])))

    fetch(`${API}/api/v1/paquets-servei/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(d => setPaquets(Array.isArray(d) ? d : (d.results || [])))
  }, [model?.id])

  return (
    <div>
      <Section title="Serveis assignats">
        {serveis.length === 0
          ? <div style={{ color: 'var(--text-main)', fontSize: 11 }}>Sense serveis assignats.</div>
          : serveis.map(s => (
            <div key={s.id} style={{
              display: 'grid',
              gridTemplateColumns: '1fr 80px 100px',
              gap: 8,
              padding: '6px 0',
              borderBottom: '1px solid var(--border)',
              alignItems: 'center',
            }}>
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono, monospace' }}>
                  {s.nom_servei}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-main)' }}>{s.grup}</div>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'right' }}>
                {s.slots_base ? `${s.slots_base} slots` : ''}
              </div>
              <div>
                <EstatBadge estat={s.estat_autoritzacio || 'Pendent'} size="xs" />
              </div>
            </div>
          ))
        }
      </Section>
      <Section title="Slots">
        <FieldRow label="Previstos tècnic">{model?.slots_prev_tecnics ?? '—'}</FieldRow>
        <FieldRow label="Previstos confecció">{model?.slots_prev_confeccio ?? '—'}</FieldRow>
        <FieldRow label="Reals tècnic">{model?.slots_reals_tecnic ?? '—'}</FieldRow>
        <FieldRow label="Reals confecció">{model?.slots_reals_confeccio ?? '—'}</FieldRow>
      </Section>
    </div>
  )
}

function TabControl({ model, token, onUpdate }) {
  const [generant, setGenerant] = useState(false)
  const [msg, setMsg] = useState(null)

  const generarTasques = async () => {
    setGenerant(true)
    setMsg(null)
    try {
      const r = await fetch(`${API}/api/v1/models/${model.id}/generar-tasques/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: '{}',
      })
      const d = await r.json()
      if (d.error) setMsg({ type: 'error', text: d.error })
      else {
        setMsg({ type: 'ok', text: d.missatge })
        onUpdate && onUpdate()
      }
    } catch (e) {
      setMsg({ type: 'error', text: String(e) })
    }
    setGenerant(false)
  }

  return (
    <div>
      <Section title="Estat del model">
        <div style={{ marginBottom: 12 }}>
          <FaseStepper faseActual={model?.fase_actual || 'Nou'} />
        </div>
        <FieldRow label="Estat"><EstatBadge estat={model?.estat} /></FieldRow>
        <FieldRow label="Prioritat"><EstatBadge estat={model?.prioritat} size="xs" /></FieldRow>
        <FieldRow label="Responsable">{model?.responsable_nom || model?.responsable}</FieldRow>
        <FieldRow label="Data entrada">{model?.data_entrada}</FieldRow>
        <FieldRow label="Data objectiu">{model?.data_objectiu}</FieldRow>
      </Section>

      {model?.observacions && (
        <Section title="Observacions">
          <div style={{ color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.6 }}>
            {model.observacions}
          </div>
        </Section>
      )}

      <Section title="Tasques">
        <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          <button
            onClick={generarTasques}
            disabled={generant}
            style={btnSecondary}
          >
            {generant ? 'Generant...' : '⚡ Generar tasques des dels serveis'}
          </button>
        </div>
        {msg && (
          <div style={{
            padding: '6px 10px', borderRadius: 4, fontSize: 11, marginBottom: 12,
            fontFamily: 'IBM Plex Mono, monospace',
            background: msg.type === 'ok' ? '#1a2a1a' : '#2a1a1a',
            color: msg.type === 'ok' ? '#4a9a4a' : '#cc4444',
            border: `1px solid ${msg.type === 'ok' ? '#2a4a2a' : '#4a2020'}`,
          }}>
            {msg.text}
          </div>
        )}
        <KanbanTasquesModel
          modelId={model?.id}
          token={token}
          onGenerarTasques={generarTasques}
        />
      </Section>
    </div>
  )
}

// ─── ModelDetall principal ────────────────────────────────────────────────────

export default function ModelDetall() {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = useAuthStore.getState().token || localStorage.getItem('access_token')
  const [tab, setTab] = useState(0)

  // Guard auth: redirigeix si no hi ha token (cap fetch s'executarà sense auth)
  useEffect(() => { if (!token) navigate("/login") }, [token, navigate])

  const { model, loading, error, refresh } = useModel(id, token)

  if (loading) return (
    <div style={pageStyle}>
      <div style={{ color: 'var(--text-main)', fontSize: 12, fontFamily: 'IBM Plex Mono, monospace' }}>
        Carregant model {id}...
      </div>
    </div>
  )

  if (error) return (
    <div style={pageStyle}>
      <div style={{ color: '#cc4444', fontSize: 12 }}>{error}</div>
      <button onClick={() => navigate(-1)} style={{ ...btnSecondary, marginTop: 12 }}>← Tornar</button>
    </div>
  )

  if (!model) return null

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <button
          onClick={() => navigate(-1)}
          style={{ color: 'var(--text-main)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, marginBottom: 8, fontFamily: 'IBM Plex Mono, monospace' }}
        >
          ← Models
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
          <div>
            <h1 style={{ fontSize: 18, fontFamily: 'IBM Plex Mono, monospace', color: '#c27a2a', margin: 0 }}>
              {model.codi}
            </h1>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
              {model.nom_prenda}
              {model.client_nom && <span style={{ color: 'var(--text-muted)' }}> · {model.client_nom}</span>}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <EstatBadge estat={model.estat} />
            <EstatBadge estat={model.prioritat} size="xs" />
            <ExportModelPDF modelId={model.id} nomModel={model.codi_intern || model.codi} />
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <FaseStepper faseActual={model.fase_actual || 'Nou'} />
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid #1a1a1a', marginBottom: 20, overflowX: 'auto', gap: 0 }}>
        {TABS.map((t, i) => (
          <TabBtn key={t} label={t} active={tab === i} onClick={() => setTab(i)} />
        ))}
      </div>

      {/* Tab content */}
      <div style={{ minHeight: 400 }}>
        {tab === 0 && <TabModel model={model} token={token} onSave={refresh} />}
        {tab === 1 && <TabMesures model={model} token={token} onSave={refresh} />}
        {tab === 2 && <TabSF model={model} token={token} refresh={refresh} />}
        {tab === 3 && <TabFitxers model={model} token={token} />}
        {tab === 4 && <TabServei model={model} token={token} />}
        {tab === 5 && <TabControl model={model} token={token} onUpdate={refresh} />}
      </div>
    </div>
  )
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const pageStyle = {
  padding: '20px 24px',
  maxWidth: 960,
  margin: '0 auto',
  color: 'var(--text-muted)',
}

const inputStyle = {
  background: 'var(--bg-card)',
  border: '1px solid #222',
  borderRadius: 3,
  color: 'var(--text-muted)',
  fontSize: 12,
  fontFamily: 'IBM Plex Mono, monospace',
  padding: '4px 8px',
  width: '100%',
}

const btnPrimary = {
  padding: '7px 16px',
  background: 'var(--bg-muted)',
  color: '#7a7acc',
  border: '1px solid #3a3a6a',
  borderRadius: 4,
  fontSize: 11,
  fontFamily: 'IBM Plex Mono, monospace',
  cursor: 'pointer',
}

const btnSecondary = {
  padding: '6px 12px',
  background: 'transparent',
  color: 'var(--text-muted)',
  border: '1px solid var(--border)',
  borderRadius: 3,
  fontSize: 11,
  fontFamily: 'IBM Plex Mono, monospace',
  cursor: 'pointer',
}
