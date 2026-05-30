
import { useState, useEffect, useCallback } from "react"

const API = import.meta.env.VITE_API_URL || ""

const S = {
  label: { fontSize: 11, color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono, monospace', marginBottom: 4, display: 'block' },
  input: { width: '100%', padding: '5px 8px', border: '1px solid #e0d5c5', borderRadius: 4, fontSize: 12, fontFamily: 'IBM Plex Mono, monospace', background: 'var(--bg-main)', color: 'var(--text-main)', boxSizing: 'border-box' },
  row: { display: 'grid', gridTemplateColumns: '80px 1fr 70px 60px 60px 32px', gap: 6, alignItems: 'center', padding: '5px 0', borderBottom: '1px solid #f5ede0' },
  rowHeader: { display: 'grid', gridTemplateColumns: '80px 1fr 70px 60px 60px 32px', gap: 6, padding: '4px 0 8px', borderBottom: '2px solid #e0d5c5' },
  btn: (variant = 'secondary') => ({
    padding: '7px 16px', borderRadius: 4, fontSize: 11, cursor: 'pointer',
    fontFamily: 'IBM Plex Mono, monospace', border: '1px solid',
    ...(variant === 'primary'
      ? { background: 'var(--gold-pale)', color: 'var(--gold)', borderColor: 'var(--gold)' }
      : variant === 'danger'
      ? { background: 'var(--err-bg)', color: 'var(--err)', borderColor: 'var(--err)' }
      : { background: 'var(--bg-main)', color: 'var(--text-muted)', borderColor: 'var(--border)' })
  }),
  tag: (color = 'var(--gold)') => ({
    display: 'inline-block', padding: '2px 8px', borderRadius: 3,
    fontSize: 10, fontFamily: 'IBM Plex Mono, monospace',
    background: color === 'var(--gold)' ? 'var(--gold-pale)' : '#e8f5e8',
    color, border: `1px solid ${color}33`,
  }),
}

function ColHeader({ children }) {
  return <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600 }}>{children}</span>
}

function POMRow({ pom, onChange, onRemove }) {
  return (
    <div style={S.row}>
      <input
        value={pom.codi_client}
        onChange={e => onChange({ ...pom, codi_client: e.target.value })}
        placeholder="Codi"
        style={{ ...S.input, fontSize: 11 }}
      />
      <input
        value={pom.nom_client}
        onChange={e => onChange({ ...pom, nom_client: e.target.value })}
        placeholder={pom.nom_ca || "Nom"}
        style={{ ...S.input, fontSize: 11 }}
      />
      <input
        type="number"
        step="0.1"
        value={pom.valor_cm === 0 ? '' : pom.valor_cm}
        onChange={e => onChange({ ...pom, valor_cm: parseFloat(e.target.value) || 0 })}
        placeholder="cm"
        style={{ ...S.input, textAlign: 'right' }}
      />
      <input
        type="number"
        step="0.1"
        value={pom.tol_minus || ''}
        onChange={e => onChange({ ...pom, tol_minus: parseFloat(e.target.value) || 0 })}
        placeholder="±"
        style={{ ...S.input, textAlign: 'right', fontSize: 11 }}
      />
      <input
        type="number"
        step="0.1"
        value={pom.tol_plus || ''}
        onChange={e => onChange({ ...pom, tol_plus: parseFloat(e.target.value) || 0 })}
        placeholder="±"
        style={{ ...S.input, textAlign: 'right', fontSize: 11 }}
      />
      <button onClick={onRemove} style={{ ...S.btn('danger'), padding: '4px 8px' }} title="Eliminar">×</button>
    </div>
  )
}

function CercaPOMModal({ token, onSelect, onClose }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [nouPom, setNouPom] = useState(false)
  const [form, setForm] = useState({ codi_client: '', nom_client: '', categoria_id: '' })
  const [saving, setSaving] = useState(false)
  const [categories, setCategories] = useState([])

  useEffect(() => {
    fetch(`${API}/api/v1/pom-categories/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(d => setCategories(Array.isArray(d) ? d : (d.results || [])))
      .catch(() => {})
  }, [token])

  const search = useCallback(async (text) => {
    if (text.length < 2) { setResults([]); return }
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/v1/poms/cerca/?q=${encodeURIComponent(text)}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const d = await r.json()
      setResults(d.results || [])
    } catch (e) {}
    setLoading(false)
  }, [token])

  useEffect(() => {
    const t = setTimeout(() => search(q), 300)
    return () => clearTimeout(t)
  }, [q, search])

  const handleCreate = async () => {
    if (!form.codi_client || !form.nom_client) return
    setSaving(true)
    try {
      const r = await fetch(`${API}/api/v1/poms/crear-tenant/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const d = await r.json()
      if (r.ok) {
        onSelect({ id: d.id, codi_client: d.codi_client, nom_client: d.nom_client, nom_ca: '', valor_cm: 0 })
        onClose()
      } else {
        alert(d.error || 'Error creant POM')
      }
    } catch (e) { alert(String(e)) }
    setSaving(false)
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: 'var(--bg-main)', borderRadius: 8, padding: 24, width: 480,
        border: '1px solid #e0d5c5', maxHeight: '80vh', overflowY: 'auto',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600, color: 'var(--text-main)' }}>
            {nouPom ? 'Nou POM' : 'Cerca POM'}
          </span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 18 }}>×</button>
        </div>

        {!nouPom ? (
          <>
            <input
              autoFocus
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Cerca per codi o nom..."
              style={{ ...S.input, marginBottom: 12 }}
            />
            {loading && <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '4px 0' }}>Cercant...</div>}
            {results.map(p => (
              <div
                key={p.id}
                onClick={() => { onSelect({ ...p, valor_cm: 0 }); onClose() }}
                style={{
                  padding: '8px 10px', cursor: 'pointer', borderRadius: 4,
                  fontFamily: 'IBM Plex Mono, monospace', fontSize: 12,
                  display: 'flex', gap: 10, alignItems: 'center',
                  borderBottom: '1px solid #f5ede0',
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#fdf6ee'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span style={{ color: 'var(--gold)', fontWeight: 600, minWidth: 50 }}>{p.codi_client}</span>
                <span style={{ color: 'var(--text-main)' }}>{p.nom_client || p.nom_ca}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: 10, marginLeft: 'auto' }}>{p.categoria_nom}</span>
              </div>
            ))}
            {q.length >= 2 && !loading && results.length === 0 && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '8px 0' }}>
                Sense resultats.{' '}
                <button onClick={() => { setNouPom(true); setForm({ codi_client: q, nom_client: '', categoria_id: '' }) }}
                  style={{ background: 'none', border: 'none', color: 'var(--gold)', cursor: 'pointer', fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, textDecoration: 'underline' }}>
                  Crear nou POM "{q}"
                </button>
              </div>
            )}
          </>
        ) : (
          <>
            <div style={{ marginBottom: 12 }}>
              <label style={S.label}>Codi client *</label>
              <input value={form.codi_client} onChange={e => setForm(f => ({ ...f, codi_client: e.target.value }))} style={S.input} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={S.label}>Nom *</label>
              <input value={form.nom_client} onChange={e => setForm(f => ({ ...f, nom_client: e.target.value }))} style={S.input} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={S.label}>Categoria</label>
              <select value={form.categoria_id} onChange={e => setForm(f => ({ ...f, categoria_id: e.target.value }))} style={S.input}>
                <option value="">— Sense categoria —</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.nom_ca || c.nom_en}</option>)}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => setNouPom(false)} style={S.btn()}>← Tornar</button>
              <button onClick={handleCreate} disabled={saving} style={S.btn('primary')}>
                {saving ? 'Guardant...' : '+ Crear POM'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export function TallaBaseWizard({ model, sfId, token, onComplete }) {
  const [poms, setPoms] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [showCerca, setShowCerca] = useState(false)
  const [msg, setMsg] = useState(null)
  const [sfEstat, setSfEstat] = useState(null)

  // Carregar BaseMeasurements existents + POMs suggerits
  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        // Primers, BaseMeasurements existents
        const r1 = await fetch(`${API}/api/v1/models/${model.id}/base-measurements/`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        const d1 = await r1.json()
        const existing = d1.results || []

        if (existing.length > 0) {
          setPoms(existing.map(bm => ({
            pom_id: bm.pom_id,
            codi_client: bm.codi_client,
            nom_client: bm.nom_client,
            nom_ca: bm.nom_ca || '',
            valor_cm: bm.base_value_cm,
            tol_minus: 0.5,
            tol_plus: 0.5,
          })))
        } else {
          // Suggerits per garment_type
          const gt = model.garment_type || ''
          const r2 = await fetch(`${API}/api/v1/poms/suggerits-v2/${gt ? `?garment_type=${gt}` : ''}`, {
            headers: { Authorization: `Bearer ${token}` }
          })
          const d2 = await r2.json()
          setPoms((d2.results || []).map(p => ({
            pom_id: p.id,
            codi_client: p.codi_client,
            nom_client: p.nom_client,
            nom_ca: p.nom_global_ca || '',
            valor_cm: 0,
            tol_minus: 0.5,
            tol_plus: 0.5,
          })))
        }
      } catch (e) {
        setMsg({ type: 'error', text: String(e) })
      }
      setLoading(false)
    }
    if (model?.id) load()
  }, [model?.id, token])

  const handleChange = (idx, updated) => {
    setPoms(prev => prev.map((p, i) => i === idx ? updated : p))
  }

  const handleRemove = (idx) => {
    setPoms(prev => prev.filter((_, i) => i !== idx))
  }

  const handleAddPOM = (pom) => {
    if (poms.find(p => p.pom_id === pom.id)) return
    setPoms(prev => [...prev, {
      pom_id: pom.id,
      codi_client: pom.codi_client,
      nom_client: pom.nom_client,
      nom_ca: pom.nom_ca || '',
      valor_cm: 0,
      tol_minus: 0.5,
      tol_plus: 0.5,
    }])
  }

  const handleSave = async () => {
    setSaving(true)
    setMsg(null)
    try {
      const payload = poms.map(p => ({
        pom_id: p.pom_id,
        valor_cm: p.valor_cm || 0,
        notes: '',
      }))
      const r = await fetch(`${API}/api/v1/models/${model.id}/guardar-talla-base/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ poms: payload }),
      })
      const d = await r.json()
      if (r.ok) setMsg({ type: 'ok', text: d.missatge })
      else setMsg({ type: 'error', text: d.error })
    } catch (e) {
      setMsg({ type: 'error', text: String(e) })
    }
    setSaving(false)
  }

  const handleConfirm = async () => {
    // Save first
    await handleSave()
    setConfirming(true)
    setMsg(null)
    try {
      const r = await fetch(`${API}/api/v1/models/${model.id}/confirmar-talla-base/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const d = await r.json()
      if (r.ok) {
        setMsg({ type: 'ok', text: d.missatge + (d.talles_generades ? ` · ${d.talles_generades} talles generades` : '') })
        setSfEstat(d.estat_sf)
        onComplete && onComplete(d)
      } else {
        setMsg({ type: 'error', text: d.error })
      }
    } catch (e) {
      setMsg({ type: 'error', text: String(e) })
    }
    setConfirming(false)
  }

  const pomsWithValue = poms.filter(p => p.valor_cm > 0).length
  const baseTancada = sfEstat === 'BaseTancada' || sfEstat === 'TallesGenerades'

  if (loading) return (
    <div style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: 'IBM Plex Mono, monospace', padding: '16px 0' }}>
      Carregant POMs...
    </div>
  )

  return (
    <div style={{ fontFamily: 'IBM Plex Mono, monospace' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <span style={{ fontSize: 12, color: 'var(--text-main)', fontWeight: 600 }}>Mesures talla base</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 12 }}>
            {pomsWithValue} / {poms.length} POMs amb valor
          </span>
        </div>
        {baseTancada && <span style={S.tag('#2a7a2a')}>✓ Talla base confirmada</span>}
      </div>

      {/* Taula POMs */}
      <div style={S.rowHeader}>
        <ColHeader>Codi</ColHeader>
        <ColHeader>Nom</ColHeader>
        <ColHeader>Valor (cm)</ColHeader>
        <ColHeader>Tol −</ColHeader>
        <ColHeader>Tol +</ColHeader>
        <span />
      </div>

      <div style={{ maxHeight: 320, overflowY: 'auto' }}>
        {poms.map((pom, i) => (
          <POMRow
            key={`${pom.pom_id}-${i}`}
            pom={pom}
            onChange={updated => handleChange(i, updated)}
            onRemove={() => handleRemove(i)}
          />
        ))}
        {poms.length === 0 && (
          <div style={{ color: 'var(--text-muted)', fontSize: 11, padding: '12px 0', textAlign: 'center' }}>
            Sense POMs. Afegeix-ne des del catàleg.
          </div>
        )}
      </div>

      {/* Nota POMs valor 0 */}
      {poms.some(p => p.valor_cm === 0) && (
        <div style={{ fontSize: 10, color: 'var(--gold)', marginTop: 8 }}>
          ⚠ Els POMs amb valor 0 s'eliminaran en confirmar la talla base.
        </div>
      )}

      {/* Missatge */}
      {msg && (
        <div style={{
          padding: '6px 10px', marginTop: 12, borderRadius: 4, fontSize: 11,
          background: msg.type === 'ok' ? 'var(--ok-bg)' : 'var(--err-bg)',
          border: `1px solid ${msg.type === 'ok' ? '#c0dd97' : '#f09595'}`,
          color: msg.type === 'ok' ? 'var(--ok)' : 'var(--err)',
        }}>
          {msg.text}
        </div>
      )}

      {/* Botons */}
      {!baseTancada && (
        <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
          <button onClick={() => setShowCerca(true)} style={S.btn()}>
            + Afegir POM
          </button>
          <button onClick={handleSave} disabled={saving} style={S.btn()}>
            {saving ? 'Guardant...' : '💾 Guardar'}
          </button>
          <button
            onClick={handleConfirm}
            disabled={confirming || pomsWithValue < 3}
            style={S.btn('primary')}
            title={pomsWithValue < 3 ? 'Cal mínim 3 POMs amb valor' : ''}
          >
            {confirming ? 'Confirmant...' : '✓ Confirmar talla base'}
          </button>
        </div>
      )}

      {/* Search modal */}
      {showCerca && (
        <CercaPOMModal
          token={token}
          onSelect={handleAddPOM}
          onClose={() => setShowCerca(false)}
        />
      )}
    </div>
  )
}
