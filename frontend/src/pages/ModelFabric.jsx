import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const API = import.meta.env.VITE_API_URL || ''

const labelStyle = {
  display: 'block', fontSize: 12,
  color: 'var(--text-muted)', marginBottom: 4,
}
const inputStyle = {
  width: '100%', padding: '7px 10px', fontSize: 13,
  border: '0.5px solid var(--border)',
  borderRadius: 6, background: 'var(--bg-main)',
  boxSizing: 'border-box',
}
const btnSecondary = {
  padding: '8px 16px', background: 'transparent', fontSize: 13,
  border: '0.5px solid var(--border)',
  borderRadius: 6, cursor: 'pointer',
}

export default function ModelFabric() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}` }

  const [model, setModel] = useState(null)
  const [isoTable, setIsoTable] = useState([])
  const [form, setForm] = useState({
    fabric_main: '',
    fabric_composition: '',
    shrinkage_type: 'NONE',
    shrinkage_warp: '',
    shrinkage_weft: '',
    shrinkage_pct: '',
    shrinkage_iso_key: '',
    fabric_notes: '',
  })
  const [biaxial, setBiaxial] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders }).then(r => r.json()),
      fetch(`${API}/api/v1/models/iso-shrinkage/`, { headers: authHeaders }).then(r => r.json()),
    ]).then(([modelData, isoData]) => {
      setModel(modelData)
      setIsoTable(Array.isArray(isoData) ? isoData : [])
      setForm({
        fabric_main: modelData.fabric_main || '',
        fabric_composition: modelData.fabric_composition || '',
        shrinkage_type: modelData.shrinkage_type || 'NONE',
        shrinkage_warp: modelData.shrinkage_warp ?? '',
        shrinkage_weft: modelData.shrinkage_weft ?? '',
        shrinkage_pct: modelData.shrinkage_pct ?? '',
        shrinkage_iso_key: modelData.shrinkage_iso_key || '',
        fabric_notes: modelData.fabric_notes || '',
      })
      if (modelData.shrinkage_pct != null) setBiaxial(false)
    }).catch(() => setError(t('errors.load_failed')))
  }, [id])

  const handleISOSelect = (isoEntry) => {
    setForm(f => ({
      ...f,
      shrinkage_type: 'ISO',
      shrinkage_iso_key: isoEntry.id,   // identitat del teixit triat (no només els %)
      shrinkage_warp: isoEntry.warp,
      shrinkage_weft: isoEntry.weft,
      shrinkage_pct: '',
    }))
    setBiaxial(true)
  }

  const handleSave = async () => {
    setSaving(true); setError('')
    try {
      const payload = {
        fabric_main: form.fabric_main,
        fabric_composition: form.fabric_composition,
        shrinkage_type: form.shrinkage_type,
        // Desa quin teixit ISO es va triar; buit si la selecció no és ISO.
        shrinkage_iso_key: form.shrinkage_type === 'ISO' ? form.shrinkage_iso_key : '',
        fabric_notes: form.fabric_notes,
      }
      if (biaxial) {
        payload.shrinkage_warp = form.shrinkage_warp !== '' ? parseFloat(form.shrinkage_warp) : null
        payload.shrinkage_weft = form.shrinkage_weft !== '' ? parseFloat(form.shrinkage_weft) : null
        payload.shrinkage_pct = null
      } else {
        payload.shrinkage_pct = form.shrinkage_pct !== '' ? parseFloat(form.shrinkage_pct) : null
        payload.shrinkage_warp = null
        payload.shrinkage_weft = null
      }

      // 1) Persistir el teixit (com fins ara).
      const r = await fetch(`${API}/api/v1/models/${id}/update-fabric/`, {
        method: 'PATCH', headers: authHeaders,
        body: JSON.stringify(payload),
      })
      if (!r.ok) { const d = await r.json(); setError(JSON.stringify(d)); return }

      // 2) Sprint B · tancar la taula de mides (estat 'Tancat'). Resol/crea el SizeFitting
      // del model al backend. Si encara no hi ha mides → avís clar, NO navegar.
      const rc = await fetch(`${API}/api/v1/models/${id}/tancar-taula/`, {
        method: 'POST', headers: authHeaders,
      })
      if (!rc.ok) {
        const d = await rc.json().catch(() => ({}))
        setError(d.error || t('model_fabric.err_close_table'))
        return
      }

      // 3) Èxit: el flux de mides es tanca → tornar al Kanban (no a /fitxers).
      navigate('/tasques/kanban')
    } catch {
      setError(t('model_sheet.err_connection'))
    } finally {
      setSaving(false)
    }
  }

  if (!model) return null

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: '2rem 1rem',
                  }}>

      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        marginBottom: '1.5rem',
        padding: '8px 14px',
        background: 'var(--bg-muted)',
        borderRadius: 8, fontSize: 13,
      }}>
        <span style={{ color: 'var(--text-muted)' }}>
          {model.codi_intern}
        </span>
        {model.nom_prenda && (
          <span style={{ fontWeight: 500 }}>{model.nom_prenda}</span>
        )}
        {model.construction && (
          <span style={{ color: 'var(--text-muted)' }}>{t(`model_wizard.construction_${model.construction}`, model.construction)}</span>
        )}
      </div>

      <h2 style={{ fontSize: 18, fontWeight: 500, marginBottom: '0.25rem' }}>
        {t('model_fabric.title')}
      </h2>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
        {t('model_fabric.subtitle')}
      </p>

      {error && (
        <div style={{ background: '#fee', border: '1px solid #fcc', borderRadius: 6,
                      padding: '8px 12px', marginBottom: 12, fontSize: 13, color: '#c00' }}>
          {error}
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>{t('model_sheet.field_main_fabric')}</label>
        <input value={form.fabric_main}
          onChange={e => setForm(f => ({...f, fabric_main: e.target.value}))}
          placeholder={t('model_fabric.ph_fabric')}
          style={inputStyle} />
      </div>

      <div style={{ marginBottom: 20 }}>
        <label style={labelStyle}>{t('model_sheet.field_composition')}</label>
        <input value={form.fabric_composition}
          onChange={e => setForm(f => ({...f, fabric_composition: e.target.value}))}
          placeholder={t('model_fabric.ph_composition')}
          style={inputStyle} />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>{t('model_sheet.field_shrinkage')}</label>

        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
            {t('model_fabric.iso_hint')}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {isoTable.map(entry => {
              // Selecció per id del teixit (no per warp/weft, que col·lisionen entre teixits:
              // Woven Cotton i Linen comparteixen 3/3). Així només es marca el xip clicat.
              const active = form.shrinkage_type === 'ISO'
                && form.shrinkage_iso_key === entry.id
              return (
                <button key={entry.id} type="button"
                  onClick={() => handleISOSelect(entry)}
                  style={{
                    padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                    border: active
                      ? '1.5px solid var(--gold)'
                      : '0.5px solid var(--border)',
                    background: active ? '#fdf6ee' : 'transparent',
                    color: 'var(--text-muted)',
                  }}>
                  {entry.nom}
                  <span style={{ marginLeft: 6, fontSize: 11 }}>
                    {entry.warp}%/{entry.weft}%
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
          <button type="button" onClick={() => setBiaxial(true)}
            style={{
              padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
              border: 'none',
              background: biaxial ? 'var(--gold)' : 'var(--bg-muted)',
              color: biaxial ? 'var(--white)' : 'var(--text-muted)',
            }}>
            {t('model_fabric.mode_biaxial')}
          </button>
          <button type="button" onClick={() => setBiaxial(false)}
            style={{
              padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
              border: 'none',
              background: !biaxial ? 'var(--gold)' : 'var(--bg-muted)',
              color: !biaxial ? 'var(--white)' : 'var(--text-muted)',
            }}>
            {t('model_fabric.mode_single')}
          </button>
        </div>

        {biaxial ? (
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <label style={{ ...labelStyle, fontSize: 11 }}>{t('model_fabric.warp_pct')}</label>
              <input type="number" step="0.5" min="0" max="30"
                value={form.shrinkage_warp}
                onChange={e => setForm(f => ({
                  ...f, shrinkage_warp: e.target.value, shrinkage_type: 'SUPPLIER',
                  shrinkage_iso_key: ''
                }))}
                placeholder={t('model_fabric.ph_pct')}
                style={{ ...inputStyle, width: 80 }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ ...labelStyle, fontSize: 11 }}>{t('model_fabric.weft_pct')}</label>
              <input type="number" step="0.5" min="0" max="30"
                value={form.shrinkage_weft}
                onChange={e => setForm(f => ({
                  ...f, shrinkage_weft: e.target.value, shrinkage_type: 'SUPPLIER',
                  shrinkage_iso_key: ''
                }))}
                placeholder={t('model_fabric.ph_pct')}
                style={{ ...inputStyle, width: 80 }} />
            </div>
          </div>
        ) : (
          <div>
            <label style={{ ...labelStyle, fontSize: 11 }}>{t('model_fabric.shrinkage_pct_label')}</label>
            <input type="number" step="0.5" min="0" max="30"
              value={form.shrinkage_pct}
              onChange={e => setForm(f => ({
                ...f, shrinkage_pct: e.target.value, shrinkage_type: 'SUPPLIER'
              }))}
              placeholder={t('model_fabric.ph_pct')}
              style={{ ...inputStyle, width: 80 }} />
          </div>
        )}
      </div>

      <div style={{ marginBottom: 24 }}>
        <label style={labelStyle}>{t('model.fields.observacions')}</label>
        <textarea value={form.fabric_notes}
          onChange={e => setForm(f => ({...f, fabric_notes: e.target.value}))}
          rows={2} placeholder={t('model_fabric.ph_notes')}
          style={{ ...inputStyle, resize: 'vertical' }} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <button type="button"
          onClick={() => navigate(`/models/${id}/mesures`)}
          style={btnSecondary}>
          ← {t('app.back')}
        </button>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button"
            onClick={() => navigate(`/models/${id}/fitxers`)}
            style={btnSecondary}>
            {t('model_fabric.skip')}
          </button>
          <button type="button" onClick={handleSave} disabled={saving}
            style={{
              padding: '8px 20px', background: saving ? '#ccc' : 'var(--gold)',
              color: 'var(--white)', border: 'none', borderRadius: 6,
              fontSize: 14, fontWeight: 500,
              cursor: saving ? 'not-allowed' : 'pointer',
            }}>
            {saving ? t('model_fabric.closing') : t('model_fabric.close_finish')}
          </button>
        </div>
      </div>
    </div>
  )
}
