import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { IconPlus, IconTrash, IconAlertTriangle } from '@tabler/icons-react'
import { itemBaseSets, sizeSystems, sizeDefinitions, fitTypes } from '../../api/endpoints'
import MeasurementBaseGrid from '../MeasurementBaseGrid/MeasurementBaseGrid'

// BaseSetPanel — els MONS d'un Item (Sprint BaseSet condicionat, B4).
//
// LLEI (Agus, Patró C 2026-07-25): «L'item MAI es parteix. Un sol GTI per peça, un sol superset
// de POMs. El món viu als satèl·lits: BaseSets condicionats per (item × size_system × fit).»
// Aquest panell és la superfície d'aquella llei al catàleg: llista els mons que l'item ja té,
// en deixa néixer de nous, i escopa la graella de valors al món SELECCIONAT.
//
// Per què la graella va a dins i no al costat: els valors d'un POM canvien de món a món (la
// mateixa camisa en ALPHA_EU_M i en KIDS_CM no té la mateixa amplada de pit), i una graella que
// no digués de quin món parla seria una taula de mesures sense talla base — exactament el que el
// guard P1 va néixer per impedir.
//
// La talla base es tria EN CREAR el set (llei 2) i després no es toca des d'aquí: canviar-la
// reinterpretaria totes les mesures que ja hi pengen, i això no és un desplegable.

const MONO = 'IBM Plex Mono, monospace'

const btnPrimary = (disabled) => ({
  background: disabled ? '#ccc' : 'var(--gold)', color: 'var(--text-main)', border: 'none',
  borderRadius: 6, padding: '7px 16px', fontSize: 'var(--fs-body)', fontWeight: 500,
  cursor: disabled ? 'not-allowed' : 'pointer',
})
const btnSecondary = {
  background: 'transparent', color: 'var(--text-muted)', border: '0.5px solid var(--border)',
  borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer',
}
const selectS = {
  border: '0.5px solid var(--border)', borderRadius: 6, padding: '7px 10px',
  fontSize: 'var(--fs-body)', background: 'var(--white)', minWidth: 150,
}
const fieldLabel = {
  fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)',
  textTransform: 'uppercase', display: 'block', marginBottom: 5,
}
const sectionTitle = {
  fontSize: 'var(--fs-label)', fontWeight: 700, color: 'var(--gold)',
  letterSpacing: '0.08em', textTransform: 'uppercase', margin: '0 0 12px',
}

export default function BaseSetPanel({ garmentTypeItemId, readOnly = false }) {
  const { t } = useTranslation()
  const [sets, setSets] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Formulari de naixement
  const [creating, setCreating] = useState(false)
  const [systems, setSystems] = useState([])
  const [fits, setFits] = useState([])
  const [talles, setTalles] = useState([])
  const [novaSystem, setNovaSystem] = useState('')
  const [novaFit, setNovaFit] = useState('')
  const [novaTalla, setNovaTalla] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!garmentTypeItemId) return
    setLoading(true); setError(null)
    try {
      const res = await itemBaseSets.list({
        garment_type_item: garmentTypeItemId, page_size: 200,
      })
      const rows = res.data.results || res.data || []
      setSets(rows)
      // Un sol món: seleccionar-lo sol estalvia un clic que no decideix res.
      setSelected((prev) => (rows.some(s => s.id === prev) ? prev
        : (rows.length === 1 ? rows[0].id : null)))
    } catch (e) {
      console.error('Error carregant els BaseSets de l\'item', e)
      setError(t('base_set_panel.load_error'))
    } finally {
      setLoading(false)
    }
  }, [garmentTypeItemId, t])

  useEffect(() => { load() }, [load])

  const obrirFormulari = async () => {
    setCreating(true)
    try {
      const [ssRes, ftRes] = await Promise.all([
        sizeSystems.list({ actiu: true, page_size: 200 }),
        fitTypes.list({ page_size: 100 }),
      ])
      setSystems(ssRes.data.results || ssRes.data || [])
      setFits(ftRes.data.results || ftRes.data || [])
    } catch (e) {
      console.error('Error carregant sistemes i fits', e)
      setError(t('base_set_panel.load_error'))
    }
  }

  // Les talles depenen del sistema: sense sistema no hi ha llista, i triar-ne una d'un altre
  // sistema faria néixer el set mentint sobre en què parla (el backend ho refusa amb 400).
  useEffect(() => {
    if (!novaSystem) { setTalles([]); setNovaTalla(''); return }
    sizeDefinitions.list({ size_system: novaSystem, page_size: 200 })
      .then(res => {
        const rows = res.data.results || res.data || []
        setTalles(rows)
        setNovaTalla('')
      })
      .catch(e => console.error('Error carregant talles', e))
  }, [novaSystem])

  const crear = async () => {
    if (!novaSystem || !novaTalla) return
    setSaving(true); setError(null)
    try {
      const res = await itemBaseSets.create({
        garment_type_item: garmentTypeItemId,
        size_system: Number(novaSystem),
        fit_type: novaFit ? Number(novaFit) : null,
        base_size_definition: Number(novaTalla),
      })
      setCreating(false)
      setNovaSystem(''); setNovaFit(''); setNovaTalla('')
      await load()
      setSelected(res.data.id)
    } catch (e) {
      const detall = e?.response?.data
      setError(detall?.base_size_definition?.[0]
        || detall?.non_field_errors?.[0]
        || t('base_set_panel.create_error'))
    } finally {
      setSaving(false)
    }
  }

  const esborrar = async (set) => {
    if (!window.confirm(t('base_set_panel.delete_confirm', {
      system: set.size_system_codi,
      fit: set.fit_type_codi || t('base_set_panel.fit_regular'),
    }))) return
    setError(null)
    try {
      await itemBaseSets.remove(set.id)
      if (selected === set.id) setSelected(null)
      await load()
    } catch (e) {
      setError(e?.response?.data?.error || t('base_set_panel.delete_error'))
    }
  }

  if (loading) {
    return <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
      {t('common.loading')}
    </p>
  }

  const selectedSet = sets.find(s => s.id === selected) || null

  return (
    <div>
      <p style={sectionTitle}>{t('base_set_panel.title')}</p>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', margin: '0 0 14px' }}>
        {t('base_set_panel.intro')}
      </p>

      {error && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
          border: '0.5px solid var(--border)', borderRadius: 8, padding: '8px 12px',
          background: 'var(--white)', color: 'var(--text-main)', fontSize: 'var(--fs-body)',
        }}>
          <IconAlertTriangle size={16} stroke={1.5} style={{ color: 'var(--gold)' }} />
          {error}
        </div>
      )}

      {sets.length === 0 && !creating && (
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 14 }}>
          {t('base_set_panel.empty')}
        </p>
      )}

      {sets.length > 0 && (
        <div style={{ overflowX: 'auto', marginBottom: 14 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['system', 'fit', 'base_size', 'measures', 'origin'].map(k => (
                  <th key={k} style={{
                    padding: '6px 10px', textAlign: 'left', fontSize: 'var(--fs-label)',
                    fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase',
                    fontWeight: 500, whiteSpace: 'nowrap',
                    borderBottom: '1px solid var(--border)',
                  }}>{t(`base_set_panel.col_${k}`)}</th>
                ))}
                <th style={{ borderBottom: '1px solid var(--border)' }} />
              </tr>
            </thead>
            <tbody>
              {sets.map(s => (
                <tr key={s.id}
                  onClick={() => setSelected(s.id)}
                  style={{
                    cursor: 'pointer',
                    background: s.id === selected ? '#fdf6ee' : 'transparent',
                    borderBottom: '0.5px solid var(--border)',
                  }}>
                  <td style={{ padding: '7px 10px', fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
                    {s.id === selected ? '★ ' : ''}{s.size_system_codi}
                  </td>
                  <td style={{ padding: '7px 10px', fontSize: 'var(--fs-body)' }}>
                    {s.fit_type_codi || t('base_set_panel.fit_regular')}
                  </td>
                  <td style={{ padding: '7px 10px', fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
                    {s.base_size_label}
                  </td>
                  <td style={{ padding: '7px 10px', fontSize: 'var(--fs-body)' }}>
                    {/* Amb valor / total: un set de 37 files buides no és un set mesurat. */}
                    {t('base_set_panel.measures_count', {
                      amb: s.mesures_amb_valor ?? 0, total: s.mesures_count ?? 0,
                    })}
                  </td>
                  <td style={{
                    padding: '7px 10px', fontSize: 'var(--fs-label)', color: 'var(--text-muted)',
                  }}>
                    {t(`base_set_panel.origin_${(s.origen || 'MANUAL').toLowerCase()}`)}
                  </td>
                  <td style={{ padding: '7px 10px', textAlign: 'right' }}>
                    {!readOnly && (
                      <button type="button" title={t('base_set_panel.delete')}
                        onClick={(ev) => { ev.stopPropagation(); esborrar(s) }}
                        style={{
                          background: 'none', border: 'none', cursor: 'pointer', padding: 2,
                          color: 'var(--text-muted)', display: 'inline-flex',
                        }}>
                        <IconTrash size={16} stroke={1.5} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!readOnly && !creating && (
        <button type="button" onClick={obrirFormulari} style={{
          ...btnSecondary, display: 'inline-flex', alignItems: 'center', gap: 6,
        }}>
          <IconPlus size={16} stroke={1.5} /> {t('base_set_panel.new')}
        </button>
      )}

      {creating && (
        <div style={{
          border: '0.5px solid var(--border)', borderRadius: 10, padding: 16,
          background: 'var(--white)', marginBottom: 16,
        }}>
          <p style={{ ...sectionTitle, marginBottom: 10 }}>{t('base_set_panel.new_title')}</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, alignItems: 'flex-end' }}>
            <div>
              <label style={fieldLabel} htmlFor="bs-system">{t('base_set_panel.col_system')}</label>
              <select id="bs-system" style={selectS} value={novaSystem}
                onChange={(e) => setNovaSystem(e.target.value)}>
                <option value="">{t('base_set_panel.choose')}</option>
                {systems.map(ss => <option key={ss.id} value={ss.id}>{ss.codi}</option>)}
              </select>
            </div>
            <div>
              <label style={fieldLabel} htmlFor="bs-fit">{t('base_set_panel.col_fit')}</label>
              <select id="bs-fit" style={selectS} value={novaFit}
                onChange={(e) => setNovaFit(e.target.value)}>
                {/* Buit = Regular: és la convenció de lookup, no un camp sense omplir. */}
                <option value="">{t('base_set_panel.fit_regular')}</option>
                {fits.map(f => <option key={f.id} value={f.id}>{f.nom_en || f.codi}</option>)}
              </select>
            </div>
            <div>
              <label style={fieldLabel} htmlFor="bs-size">{t('base_set_panel.col_base_size')}</label>
              <select id="bs-size" style={selectS} value={novaTalla} disabled={!novaSystem}
                onChange={(e) => setNovaTalla(e.target.value)}>
                <option value="">{t('base_set_panel.choose')}</option>
                {talles.map(sd => <option key={sd.id} value={sd.id}>{sd.etiqueta}</option>)}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={crear} disabled={!novaSystem || !novaTalla || saving}
                style={btnPrimary(!novaSystem || !novaTalla || saving)}>
                {saving ? t('common.saving') : t('base_set_panel.create')}
              </button>
              <button type="button" onClick={() => { setCreating(false); setError(null) }}
                style={btnSecondary}>
                {t('common.cancel')}
              </button>
            </div>
          </div>
          <p style={{
            fontSize: 'var(--fs-label)', color: 'var(--text-muted)', margin: '12px 0 0',
          }}>
            {t('base_set_panel.base_size_hint')}
          </p>
        </div>
      )}

      {selectedSet && (
        <div style={{ marginTop: 20 }}>
          <p style={sectionTitle}>
            {t('base_set_panel.grid_title', {
              system: selectedSet.size_system_codi,
              fit: selectedSet.fit_type_codi || t('base_set_panel.fit_regular'),
              size: selectedSet.base_size_label,
            })}
          </p>
          <MeasurementBaseGrid
            garmentTypeItemId={garmentTypeItemId}
            baseSetId={selectedSet.id}
            readOnly={readOnly}
            onSaved={load}
          />
        </div>
      )}

      {!selectedSet && sets.length > 1 && (
        <p style={{
          fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginTop: 16,
        }}>
          {t('base_set_panel.pick_one')}
        </p>
      )}
    </div>
  )
}
