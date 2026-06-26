import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import EditableTable from '../EditableTable/EditableTable'
import ImportWizard from '../ImportWizard/ImportWizard'
import Modal from '../ui/Modal'
import { models } from '../../api/endpoints'

const API = import.meta.env.VITE_API_URL || ''

// MeasuresEntryPanel (J1a) — flux d'ENTRADA/genesi de mesures, portat des de la pàgina standalone
// ModelMeasurements perquè el TAB Mesures del ModelSheet pugui rebre l'entrada d'un model verge sense
// sortir del full de model (DECISIONS §15.A, "superfície de Mesures única = tab"). Cobreix els camins:
//   (a) cas BUIT  → selector (manual / import)
//   (b) seed des de GarmentTypeItem (oferta conscient → materialitzar-poms, origen ITEM_STANDARD)
//   (c) import (ImportWizard)
//   + manual (EditableTable amb POMs suggerits)
// NO inclou el camí 'size_check' (CheckMeasureEditor): això és el flux de TREBALL del tab, no la
// genesi (es reapuntarà a J1b). Quan la base queda materialitzada, crida onMaterialized() perquè el
// tab rellegeixi taula-mesures i passi a la superfície de consulta/treball (CheckMeasureEditor).
export default function MeasuresEntryPanel({ model, onMaterialized, onPomSaved, entryMode = false }) {
  const { t } = useTranslation()
  const id = model?.id
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const [mode, setMode] = useState('loading')   // 'loading' | 'selector' | 'manual' | 'import'
  const [pomsSuggerits, setPomsSuggerits] = useState([])
  const [selectedPomIds, setSelectedPomIds] = useState([])
  const [taulaRows, setTaulaRows] = useState([])
  const [sizesAmbDades, setSizesAmbDades] = useState(null)
  const [deltes, setDeltes] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [seedOffer, setSeedOffer] = useState(false)
  const [seedBusy, setSeedBusy] = useState(false)
  const [savingPom, setSavingPom] = useState(false)

  const togglePom = (pom) => {
    setSelectedPomIds(prev =>
      prev.includes(pom.pom_id) ? prev.filter(x => x !== pom.pom_id) : [...prev, pom.pom_id])
  }

  const refreshTableMeta = (d) => {
    setSizesAmbDades(d.sizes_amb_dades || null)
    setDeltes(d.deltes || null)
  }

  // Recarrega la taula i fixa el mode (mirall de ModelMeasurements.reloadTable, sense l'estat 'tancat':
  // un model verge en genesi no pot estar tancat).
  const reloadTable = (afterMode = 'manual') =>
    fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => { refreshTableMeta(d); if (d.rows?.length) setTaulaRows(d.rows); setMode(afterMode) })
      .catch(() => setMode('selector'))

  // B5 — confirmar la sembra: materialitzar-poms (valor+nom_fitxa+tol, origen ITEM_STANDARD) i mostra
  // la graella sembrada en mode manual perquè el tècnic pugui ajustar abans de sortir a la consulta.
  const confirmSeed = async () => {
    setSeedBusy(true)
    try {
      await fetch(`${API}/api/v1/models/${id}/materialitzar-poms/`, { method: 'POST', headers: authHeaders })
      setSeedOffer(false)
      await reloadTable('manual')
    } catch {
      setError(t('model_sheet.err_connection'))
    } finally {
      setSeedBusy(false)
    }
  }
  const cancelSeed = () => { setSeedOffer(false); setMode('selector') }

  // Càrrega inicial: poms suggerits + decisió de sembra (mirall de ModelMeasurements). La memòria de la
  // decisió DERIVA de l'estat del model (taula verge?), no de localStorage.
  useEffect(() => {
    if (!id) return
    let alive = true
    fetch(`${API}/api/v1/models/${id}/poms-suggerits/`, { headers: authHeaders })
      .then(r => r.json())
      .then(pomsData => {
        if (!alive) return
        const poms = pomsData.poms || []
        setPomsSuggerits(poms)
        setSelectedPomIds(prev => prev.length ? prev : poms.filter(p => p.is_key).map(p => p.pom_id))
      })
      .catch(() => { if (alive) setError(t('errors.load_failed')) })

    if (!model.garment_type_item) {
      setNotice(t('model_measurements.notice_no_item'))
      reloadTable('selector'); return () => { alive = false }
    }

    fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
      .then(r => r.json())
      .then(async d => {
        if (!alive) return
        refreshTableMeta(d)
        const rows = d.rows || []
        if (rows.length) setTaulaRows(rows)
        const verge = !rows.some(r => r.base_value_cm != null)
        // Si ja té valors (no verge): en mode ENTRADA (Definició POM) NO sortim a consulta — obrim el
        // selector perquè l'usuari pugui afegir POMs / importar. Fora de mode entrada, surt a consulta.
        if (!verge) {
          if (entryMode) { setMode('selector'); return }
          onMaterialized?.(); return
        }

        let hasValues = false
        try {
          const r2 = await fetch(
            `${API}/api/v1/item-base-measurements/?garment_type_item=${model.garment_type_item}&page_size=500`,
            { headers: authHeaders })
          const dd = await r2.json()
          const ibm = dd.results || (Array.isArray(dd) ? dd : [])
          hasValues = ibm.some(x => x.base_value_cm != null)
        } catch { /* sense oferta */ }

        if (!alive) return
        if (hasValues) {
          setMode('selector'); setSeedOffer(true)
        } else if (rows.length === 0) {
          fetch(`${API}/api/v1/models/${id}/materialitzar-poms/`, { method: 'POST', headers: authHeaders })
            .then(() => reloadTable('selector')).catch(() => reloadTable('selector'))
        } else {
          setMode('selector')
        }
      })
      .catch(() => { if (alive) setMode('selector') })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const sizeRun = (sizesAmbDades && sizesAmbDades.length
    ? sizesAmbDades
    : model?.size_run_model?.split('·').map(s => s.trim())) || []
  const hasValues = taulaRows.some(r => r.base_value_cm != null)

  const savePom = async (payload) => {
    setSavingPom(true)
    setError('')
    try {
      await models.gravarPom(id, payload)
      onPomSaved?.()
    } catch (err) {
      const msg = err?.response?.data?.error || err?.response?.data?.errors?.join?.(' · ')
        || t('model_measurements.save_pom_err')
      setError(msg)
      throw err
    } finally {
      setSavingPom(false)
    }
  }

  return (
    <div>
      {error && (
        <div style={{ margin: '0 0 1rem', background: 'var(--err-bg)', border: '1px solid var(--err)', borderRadius: 8,
                      padding: '0.75rem 1rem', fontSize: 'var(--fs-body)', color: 'var(--err)' }}>{error}</div>
      )}
      {notice && (
        <div style={{ margin: '0 0 1rem', background: 'var(--warn-bg)', border: '1px solid var(--warn)', borderRadius: 8,
                      padding: '0.75rem 1rem', fontSize: 'var(--fs-body)', color: 'var(--warn)' }}>{notice}</div>
      )}

      {seedOffer && (
        <Modal
          title={t('model_measurements.seed_title')}
          subtitle={t('model_measurements.seed_subtitle')}
          cancelLabel={t('model_measurements.seed_cancel')}
          confirmLabel={seedBusy ? t('common.saving') : t('model_measurements.seed_confirm')}
          onCancel={cancelSeed}
          onConfirm={confirmSeed}
          confirmDisabled={seedBusy}
        >
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', margin: 0 }}>
            {t('model_measurements.seed_body')}
          </p>
        </Modal>
      )}

      {mode === 'loading' && !error && (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
          {t('model_sheet.loading')}
        </div>
      )}

      {mode === 'selector' && (
        <div style={{ maxWidth: 800 }}>
          <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, margin: '0 0 0.5rem' }}>
            {t('model_measurements.pom_title')}
          </h2>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
            {t('model_measurements.intro')}
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div onClick={() => setMode('manual')}
              style={{ background: 'var(--bg-main)', border: '0.5px solid var(--border)',
                       borderRadius: 12, padding: '1.5rem', cursor: 'pointer' }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}><i className="ti ti-pencil" style={{ color: 'var(--gold)' }} /></div>
              <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 6 }}>{t('model_measurements.manual_title')}</div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                {t('model_measurements.manual_desc', { type: model?.garment_type_nom || t('model_measurements.this_garment') })}
              </div>
              {pomsSuggerits.length > 0 && (
                <div style={{ marginTop: 12, fontSize: 'var(--fs-body)', color: 'var(--gold)' }}>
                  {t('model_measurements.poms_available', { total: pomsSuggerits.length, key: pomsSuggerits.filter(p => p.is_key).length })}
                </div>
              )}
            </div>
            <div onClick={() => setMode('import')}
              style={{ background: 'var(--bg-main)', border: '0.5px solid var(--border)',
                       borderRadius: 12, padding: '1.5rem', cursor: 'pointer' }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}><i className="ti ti-bolt" style={{ color: 'var(--gold)' }} /></div>
              <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 6 }}>{t('model_measurements.import_title')}</div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('model_measurements.import_desc')}</div>
            </div>
          </div>
        </div>
      )}

      {mode === 'manual' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, marginBottom: 14 }}>
            <div>
              <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, margin: '0 0 0.25rem' }}>
                {t('model_measurements.pom_title')}
              </h2>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                {t('model_measurements.pom_subtitle')}
              </div>
            </div>
            <button type="button" onClick={() => setMode('import')}
              style={{ background: 'transparent', color: 'var(--gold)', border: '0.5px solid var(--gold)',
                       borderRadius: 6, padding: '7px 12px', fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
              <i className="ti ti-upload" /> {t('model_measurements.import_table')}
            </button>
          </div>
          {taulaRows.length === 0 && pomsSuggerits.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 8 }}>
                {t('model_measurements.suggested_poms')}
              </div>
              {pomsSuggerits.filter(p => p.is_key).length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gold)', marginRight: 6, fontWeight: 500 }}>KEY</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                    {pomsSuggerits.filter(p => p.is_key).map(p => (
                      <POMChipSuggerit key={p.pom_id} pom={p} selected={selectedPomIds.includes(p.pom_id)} onToggle={() => togglePom(p)} />
                    ))}
                  </div>
                </div>
              )}
              {pomsSuggerits.filter(p => !p.is_key).length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {pomsSuggerits.filter(p => !p.is_key).map(p => (
                    <POMChipSuggerit key={p.pom_id} pom={p} selected={selectedPomIds.includes(p.pom_id)} onToggle={() => togglePom(p)} />
                  ))}
                </div>
              )}
            </div>
          )}

          <EditableTable
            rows={taulaRows.length > 0 ? taulaRows : pomsSuggerits
              .filter(p => selectedPomIds.includes(p.pom_id))
              .map((p, i) => ({
                id: `tmp-${p.pom_id}`, pom_id: p.pom_id, pom_code: p.pom_code,
                nom_ca: p.nom_ca, nom_en: p.nom_en, nom_fitxa: '',
                base_value_cm: null, graded: {}, ordre: i,
              }))}
            sizeRun={sizeRun}
            baseSize={model?.base_size_label}
            deltes={deltes}
            modelId={id}
            isImport={false}
            saveLabel={savingPom ? t('common.saving') : t('model_measurements.save_pom')}
            onPomSave={savePom}
            onSaved={(newRows) => setTaulaRows(newRows)}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 24 }}>
            <button type="button" onClick={() => setMode('selector')}
              style={{ padding: '8px 16px', border: '0.5px solid var(--border)', borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              ← {t('app.back')}
            </button>
            {hasValues && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('model_measurements.unsaved_pom_hint')}</span>}
          </div>
        </div>
      )}

      {mode === 'import' && (
        <ImportWizard
          model={model}
          onCancel={() => setMode('selector')}
          onComplete={() => reloadTable('manual')}
        />
      )}
    </div>
  )
}

function POMChipSuggerit({ pom, selected, onToggle }) {
  return (
    <button type="button" onClick={onToggle}
      style={{
        padding: '3px 10px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer',
        border: selected ? '1.5px solid var(--gold)' : '0.5px solid var(--border)',
        background: selected ? 'var(--gold-pale)' : 'transparent',
        color: selected ? 'var(--gold)' : 'var(--text-muted)',
      }}>
      <span style={{ marginRight: 4 }}>{pom.pom_code}</span>
      {pom.nom_ca || pom.nom_en}
    </button>
  )
}
