import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import EditableTable from '../components/EditableTable/EditableTable'
import ImportWizard from '../components/ImportWizard/ImportWizard'
import Modal from '../components/ui/Modal'
import PropagatedEditor from './PropagatedEditor'
import CheckMeasureEditor from '../components/model/CheckMeasureEditor'
import { modelTasks } from '../api/endpoints'

const API = import.meta.env.VITE_API_URL || ''

const thStyle = {
  padding: '8px 12px', textAlign: 'left', fontSize: 'var(--fs-body)',
  fontWeight: 500, borderBottom: '1px solid var(--border)',
}
const tdStyle = { padding: '6px 12px', verticalAlign: 'middle' }

export default function ModelMeasurements() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const [model, setModel] = useState(null)
  const [mode, setMode] = useState('loading') // 'loading' | 'selector' | 'manual' | 'import' | 'resultat'
  const [searchParams] = useSearchParams()
  const taskId = searchParams.get('task_id')
  const [checkMode, setCheckMode] = useState(null) // null=determinant · true=tasca size_check · false=mesura normal

  // Manual
  const [pomsSuggerits, setPomsSuggerits] = useState([])
  const [selectedPomIds, setSelectedPomIds] = useState([])

  // Taula final
  const [taulaRows, setTaulaRows] = useState([])
  const [sizesAmbDades, setSizesAmbDades] = useState(null)
  const [deltes, setDeltes] = useState(null)
  const [saving, setSaving] = useState(false)
  const [generatingGrading, setGeneratingGrading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  // B5 — oferta conscient de sembra (4a font): modal a la primera entrada si l'item té valors.
  const [seedOffer, setSeedOffer] = useState(false)
  const [seedBusy, setSeedBusy] = useState(false)
  // Editor propagat (totes les talles, règim, breaks) en mode edició — PEÇA 2.
  const [showPropagated, setShowPropagated] = useState(false)

  useEffect(() => {
    if (!id) return
    Promise.all([
      fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders }).then(r => r.json()),
      fetch(`${API}/api/v1/models/${id}/poms-suggerits/`, { headers: authHeaders }).then(r => r.json()),
    ]).then(([modelData, pomsData]) => {
      setModel(modelData)
      const poms = pomsData.poms || []
      setPomsSuggerits(poms)
      setSelectedPomIds(prev => prev.length > 0 ? prev : poms.filter(p => p.is_key).map(p => p.pom_id))
    }).catch(() => setError(t('errors.load_failed')))
  }, [id])

  // Entrada des de la tasca: si task_id és una tasca 'size_check', la superfície entra en mode
  // treball de check (mesura + resolució a la mateixa pantalla); fora de tasca o altres tipus de
  // tasca → flux de mesura normal (read-only respecte del check).
  useEffect(() => {
    if (!taskId) { setCheckMode(false); return }
    let alive = true
    modelTasks.get(taskId)
      .then(r => { if (alive) setCheckMode(r.data?.task_type_code === 'size_check') })
      .catch(() => { if (alive) setCheckMode(false) })
    return () => { alive = false }
  }, [taskId])

  const togglePom = (pom) => {
    setSelectedPomIds(prev =>
      prev.includes(pom.pom_id)
        ? prev.filter(id => id !== pom.pom_id)
        : [...prev, pom.pom_id]
    )
  }

  const handleGenerateGrading = async () => {
    setGeneratingGrading(true); setError('')
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/generar-grading/`, {
        method: 'POST', headers: authHeaders,
      })
      const d = await r.json()
      if (r.ok) {
        setTaulaRows(d.rows || [])
        // Grading fills graded for all sizes → we refresh columns/delta.
        fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
          .then(r => r.json()).then(refreshTableMeta).catch(() => {})
      } else {
        setError(d.error || t('model_measurements.err_grading'))
      }
    } catch {
      setError(t('model_sheet.err_connection'))
    } finally {
      setGeneratingGrading(false)
    }
  }

  // Refresh column/delta metadata from taula-mesures (single source).
  const refreshTableMeta = (d) => {
    setSizesAmbDades(d.sizes_amb_dades || null)
    setDeltes(d.deltes || null)
  }

  // Recarrega la taula de mesures i fixa el mode (tancat → resultat; si no, afterMode).
  const reloadTable = (afterMode = 'selector') =>
    fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => {
        refreshTableMeta(d)
        if (d.rows && d.rows.length > 0) setTaulaRows(d.rows)
        setMode(d.tancat ? 'resultat' : afterMode)
      })
      .catch(() => setMode('selector'))

  // B5 — Confirmar la sembra: crida materialitzar-poms (B4: valor+nom_fitxa+tol, origen
  // ITEM_STANDARD, preservant sobirania) i mostra la graella sembrada.
  const confirmSeed = async () => {
    setSeedBusy(true)
    try {
      await fetch(`${API}/api/v1/models/${id}/materialitzar-poms/`, { method: 'POST', headers: authHeaders })
      setSeedOffer(false)
      await reloadTable('manual')   // la taula deixa de ser verge → no es repreguntarà
    } catch {
      setError(t('model_sheet.err_connection'))
    } finally {
      setSeedBusy(false)
    }
  }
  // Cancel·lar: no sembra (el tècnic omple des de zero). NO es persisteix el "no": la decisió
  // ferma emergeix de l'acció (escriure un valor) — mentre la taula segueixi verge, es torna a
  // oferir a la propera entrada (acceptat: no s'ha invertit feina).
  const cancelSeed = () => {
    setSeedOffer(false)
    setMode('selector')
  }

  // Primera entrada a Mesures: en comptes de materialitzar SILENCIOSAMENT, OFERIM sembrar amb les
  // mides estàndard de l'item (decisió conscient, 4a font). La memòria de la decisió DERIVA de
  // l'estat del model (sobirania al servidor, no localStorage): s'ofereix només si la taula és
  // VERGE (cap BaseMeasurement amb valor, de cap origen — buida o TEMPLATE buit) i l'item té valors.
  useEffect(() => {
    if (!id || !model) return
    if (checkMode !== false) return   // mode treball de check: no s'executa el flux de mesura normal (ni sembra)
    if (!model.garment_type_item) {
      setNotice(t('model_measurements.notice_no_item'))
      reloadTable(); return
    }

    fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
      .then(r => r.json())
      .then(async d => {
        refreshTableMeta(d)
        if (d.tancat) { if (d.rows) setTaulaRows(d.rows); setMode('resultat'); return }
        const rows = d.rows || []
        if (rows.length) setTaulaRows(rows)
        // VERGE = cap fila amb valor (de cap origen). TEMPLATE buit / sense files = verge.
        const verge = !rows.some(r => r.base_value_cm != null)
        // v2: edició lligada a tasca. Si el model JA té valors → obre l'edició DIRECTA (manual),
        // sense el flash del selector. Només es mostra el selector/wizard si la taula és verge.
        if (!verge) { setMode('manual'); return }

        // Taula verge: ¿l'item té valors base per oferir?
        let hasValues = false
        try {
          const r2 = await fetch(
            `${API}/api/v1/item-base-measurements/?garment_type_item=${model.garment_type_item}&page_size=500`,
            { headers: authHeaders })
          const dd = await r2.json()
          const ibm = dd.results || (Array.isArray(dd) ? dd : [])
          hasValues = ibm.some(x => x.base_value_cm != null)
        } catch { /* sense oferta; membresia silenciosa si cal */ }

        if (hasValues) {
          setMode('selector'); setSeedOffer(true)   // oferta conscient (modal sobre el selector)
        } else if (rows.length === 0) {
          // Sense valors d'item i sense membresia encara: materialitza membresia (com abans).
          fetch(`${API}/api/v1/models/${id}/materialitzar-poms/`, { method: 'POST', headers: authHeaders })
            .then(() => reloadTable())
            .catch(() => reloadTable())
        } else {
          setMode('selector')   // membresia ja materialitzada, item sense valors → res a oferir
        }
      })
      .catch(() => setMode('selector'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, model, checkMode])

  // Mode treball de check (entrat des de la tasca size_check): mesura + resolució a la mateixa
  // pantalla, amb el llibre major davant. Substitueix el flux de selector/manual/import.
  if (checkMode === null || (checkMode && !model)) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
        {t('model_sheet.loading')}
      </div>
    )
  }
  if (checkMode) {
    return (
      <div style={{ width: '100%', padding: '1rem' }}>
        {error && (
          <div style={{ margin: '0 0 1rem', background: '#fee', border: '1px solid #fcc', borderRadius: 8,
                        padding: '0.75rem 1rem', fontSize: 'var(--fs-body)', color: '#c00' }}>{error}</div>
        )}
        {notice && (
          <div style={{ margin: '0 0 1rem', background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8,
                        padding: '0.75rem 1rem', fontSize: 'var(--fs-body)', color: '#7a5a00' }}>{notice}</div>
        )}
        <CheckMeasureEditor
          model={model}
          onFeedback={(fb) => { if (fb?.type === 'err') { setNotice(''); setError(fb.text) } else { setError(''); setNotice(fb.text) } }}
          onResolved={() => navigate('/tasques/kanban')}
        />
      </div>
    )
  }

  return (
    <>
      {error && (
        <div style={{
          maxWidth: 1000, margin: '1rem auto 0',
          background: '#fee', border: '1px solid #fcc', borderRadius: 8,
          padding: '0.75rem 1rem', fontSize: 'var(--fs-body)', color: '#c00',
        }}>{error}</div>
      )}

      {notice && (
        <div style={{
          maxWidth: 1000, margin: '1rem auto 0',
          background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8,
          padding: '0.75rem 1rem', fontSize: 'var(--fs-body)', color: '#7a5a00',
        }}>{notice}</div>
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

      {showPropagated && (
        <PropagatedEditor
          modelId={parseInt(id)}
          readOnly
          onClose={() => {
            setShowPropagated(false)
            // Reflectir els overrides re-propagats a la taula de resultat.
            fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
              .then(r => r.json())
              .then(d => { setTaulaRows(d.rows || []); refreshTableMeta(d) })
              .catch(() => {})
          }}
        />
      )}

      {mode === 'loading' && !error && (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
          {t('model_sheet.loading')}
        </div>
      )}

      {mode === 'selector' && (
        <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem' }}>
          <ModelSummaryBar model={model} />

          <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, margin: '1.5rem 0 0.5rem' }}>
            {t('model_measurements.title')}
          </h2>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
            {t('model_measurements.intro')}
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div onClick={() => setMode('manual')}
              style={{
                background: 'var(--bg-main)',
                border: '0.5px solid var(--border)',
                borderRadius: 12, padding: '1.5rem', cursor: 'pointer',
              }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>
                <i className="ti ti-pencil" style={{ color: 'var(--gold)' }} />
              </div>
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
              style={{
                background: 'var(--bg-main)',
                border: '0.5px solid var(--border)',
                borderRadius: 12, padding: '1.5rem', cursor: 'pointer',
              }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>
                <i className="ti ti-bolt" style={{ color: 'var(--gold)' }} />
              </div>
              <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 6 }}>{t('model_measurements.import_title')}</div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                {t('model_measurements.import_desc')}
              </div>
            </div>
          </div>
        </div>
      )}

      {mode === 'manual' && (
        <div style={{ maxWidth: 1000, margin: '0 auto', padding: '2rem 1rem' }}>
          <ModelSummaryBar model={model} />

          {taulaRows.length === 0 && pomsSuggerits.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 8 }}>
                {t('model_measurements.suggested_poms')}
              </div>
              {pomsSuggerits.filter(p => p.is_key).length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gold)', marginRight: 6,
                                 fontWeight: 500 }}>KEY</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                    {pomsSuggerits.filter(p => p.is_key).map(p => (
                      <POMChipSuggerit key={p.pom_id} pom={p}
                        selected={selectedPomIds.includes(p.pom_id)}
                        onToggle={() => togglePom(p)} />
                    ))}
                  </div>
                </div>
              )}
              {pomsSuggerits.filter(p => !p.is_key).length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {pomsSuggerits.filter(p => !p.is_key).map(p => (
                    <POMChipSuggerit key={p.pom_id} pom={p}
                      selected={selectedPomIds.includes(p.pom_id)}
                      onToggle={() => togglePom(p)} />
                  ))}
                </div>
              )}
            </div>
          )}

          <EditableTable
            rows={taulaRows.length > 0 ? taulaRows : pomsSuggerits
              .filter(p => selectedPomIds.includes(p.pom_id))
              .map((p, i) => ({
                id: `tmp-${p.pom_id}`,
                pom_id: p.pom_id, pom_code: p.pom_code,
                nom_ca: p.nom_ca, nom_en: p.nom_en, nom_fitxa: '',
                base_value_cm: null, graded: {}, ordre: i,
              }))}
            sizeRun={(sizesAmbDades && sizesAmbDades.length
              ? sizesAmbDades
              : model?.size_run_model?.split('·').map(s => s.trim())) || []}
            baseSize={model?.base_size_label}
            deltes={deltes}
            modelId={parseInt(id)}
            isImport={false}
            onSaved={(newRows) => setTaulaRows(newRows)}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 24 }}>
            <button type="button" onClick={() => setMode('selector')}
              style={{ padding: '8px 16px', border: '0.5px solid var(--border)',
                       borderRadius: 6, background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              ← {t('app.back')}
            </button>
            {taulaRows.length > 0 && (
              <div style={{ display: 'flex', gap: 8 }}>
                {model?.grading_rule_set && (
                  <button type="button" onClick={handleGenerateGrading} disabled={generatingGrading}
                    style={{
                      padding: '8px 16px', border: '0.5px solid var(--gold)',
                      borderRadius: 6, background: 'transparent',
                      color: 'var(--gold)', fontSize: 'var(--fs-body)', cursor: 'pointer',
                    }}>
                    {generatingGrading ? t('model_measurements.generating') : t('model_measurements.generate_grading')}
                  </button>
                )}
                {model?.grading_rule_set && (
                  <button type="button" onClick={() => setShowPropagated(true)}
                    style={{
                      padding: '8px 16px', border: '0.5px solid var(--gold)',
                      borderRadius: 6, background: 'transparent',
                      color: 'var(--gold)', fontSize: 'var(--fs-body)', cursor: 'pointer',
                    }}>
                    {t('model_measurements.view_grading')}
                  </button>
                )}
                <button type="button" onClick={() => navigate(`/models/${id}/teixit`)}
                  style={{
                    padding: '8px 20px', background: 'var(--gold)', color: 'var(--white)',
                    border: 'none', borderRadius: 6, fontSize: 'var(--fs-h3)', fontWeight: 500,
                    cursor: 'pointer',
                  }}>
                  {t('model_measurements.continue_fabric')}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {mode === 'import' && (
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2rem 1rem' }}>
          <ModelSummaryBar model={model} />
          {/* Import Wizard de 5 passos (substitueix el flux inline antic). */}
          <ImportWizard
            model={model}
            onCancel={() => setMode('selector')}
            onComplete={() => {
              fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
                .then(r => r.json())
                .then(d => { setTaulaRows(d.rows || []); refreshTableMeta(d); setMode('resultat') })
                .catch(() => setMode('selector'))
            }}
          />
        </div>
      )}

      {mode === 'resultat' && (
        <div style={{ width: '100%', padding: '1rem' }}>
          <ModelSummaryBar model={model} />

          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, margin: 0 }}>
              {t('model_measurements.table_title')}
            </h2>
            <button type="button" onClick={() => setMode('manual')}
              style={{ padding: '6px 14px', border: '0.5px solid var(--border)',
                       borderRadius: 6, background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              {t('model_measurements.edit_measures')}
            </button>
          </div>

          <EditableTable
            rows={taulaRows}
            sizeRun={(sizesAmbDades && sizesAmbDades.length
              ? sizesAmbDades
              : model?.size_run_model?.split('·').map(s => s.trim())) || []}
            baseSize={model?.base_size_label}
            deltes={deltes}
            modelId={parseInt(id)}
            isImport={false}
            onSaved={(newRows) => setTaulaRows(newRows)}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginTop: 16 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              {model?.grading_rule_set && (
                <button type="button" onClick={handleGenerateGrading} disabled={generatingGrading}
                  style={{
                    padding: '8px 16px', border: '0.5px solid var(--gold)',
                    borderRadius: 6, background: 'transparent',
                    color: 'var(--gold)', fontSize: 'var(--fs-body)', cursor: 'pointer',
                  }}>
                  {generatingGrading ? t('model_measurements.generating') : t('model_measurements.generate_grading')}
                </button>
              )}
              {model?.grading_rule_set && (
                <button type="button" onClick={() => setShowPropagated(true)}
                  style={{
                    padding: '8px 16px', border: '0.5px solid var(--gold)',
                    borderRadius: 6, background: 'transparent',
                    color: 'var(--gold)', fontSize: 'var(--fs-body)', cursor: 'pointer',
                  }}>
                  {t('model_measurements.view_grading')}
                </button>
              )}
            </div>
            <button type="button" onClick={() => navigate(`/models/${id}/teixit`)}
              style={{
                padding: '8px 20px', borderRadius: 6, border: 'none',
                fontSize: 'var(--fs-h3)', fontWeight: 500,
                background: 'var(--gold)', color: 'var(--white)', cursor: 'pointer',
              }}>
              {t('model_measurements.continue_fabric')}
            </button>
          </div>
        </div>
      )}
    </>
  )
}

function POMChipSuggerit({ pom, selected, onToggle }) {
  return (
    <button type="button" onClick={onToggle}
      style={{
        padding: '3px 10px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer',
        border: selected
          ? '1.5px solid var(--gold)' : '0.5px solid var(--border)',
        background: selected ? '#fdf6ee' : 'transparent',
        color: selected ? '#7a4a10' : 'var(--text-muted)',
      }}>
      <span style={{ marginRight: 4 }}>{pom.pom_code}</span>
      {pom.nom_ca || pom.nom_en}
    </button>
  )
}

function ModelSummaryBar({ model }) {
  const { t } = useTranslation()
  if (!model) return null
  return (
    <div style={{
      display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap',
      background: 'var(--bg-muted)',
      border: '0.5px solid var(--border)',
      borderRadius: 8, padding: '10px 16px', marginBottom: 16, fontSize: 'var(--fs-body)',
    }}>
      <span><strong>{model.codi_intern}</strong></span>
      {model.nom_prenda && <span>{model.nom_prenda}</span>}
      {model.target && <span style={{ color: 'var(--text-muted)' }}>{t(`model_wizard.target_${model.target}`, model.target)}</span>}
      {model.construction && <span style={{ color: 'var(--text-muted)' }}>{t(`model_wizard.construction_${model.construction}`, model.construction)}</span>}
      {model.base_size_label && (
        <span style={{ color: 'var(--gold)' }}>{t('model_measurements.base_prefix')} {model.base_size_label}</span>
      )}
      {model.size_run_model && (
        <span style={{ color: 'var(--text-muted)' }}>
          {model.size_run_model}
        </span>
      )}
    </div>
  )
}
