import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import EditableTable from '../EditableTable/EditableTable'
import ImportWizard from '../ImportWizard/ImportWizard'
import Modal from '../ui/Modal'
import ModelPicker from './ModelPicker'
import { IconBulb, IconX } from '@tabler/icons-react'
import { models } from '../../api/endpoints'

const API = import.meta.env.VITE_API_URL || ''

// Sprint B — les quatre peces independents que una còpia model→model pot portar. L'ordre és el
// de la resposta del backend; els noms són els del body de l'endpoint (cap traducció d'aquí cap
// allà: la clau i18n es deriva del nom del flag).
const COPY_FLAGS = ['copy_values', 'copy_run', 'copy_grading', 'copy_files']

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
export default function MeasuresEntryPanel({ model, onMaterialized, onPomSaved, entryMode = false, intent = null }) {
  const { t } = useTranslation()
  const id = model?.id
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const [mode, setMode] = useState('loading')   // 'loading' | 'selector' | 'manual' | 'import'
  const [pomsSuggerits, setPomsSuggerits] = useState([])
  const [selectedPomIds, setSelectedPomIds] = useState([])   // graella manual
  const [taulaRows, setTaulaRows] = useState([])
  const [sizesAmbDades, setSizesAmbDades] = useState(null)
  const [deltes, setDeltes] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  // B4 — quan la sembra retorna code='base_set_absent', el món del model (item × sistema de
  // talles × fit) no té mesures estàndard. NO és un error i no bloqueja res: la sembra ha
  // materialitzat la pertinença igualment. És una PROPOSTA, perquè l'acte real (la promoció) vol
  // el model ja mesurat i no té sentit oferir-lo aquí.
  const [baseSetAbsent, setBaseSetAbsent] = useState(null)
  const [seedBusy, setSeedBusy] = useState(false)
  const [savingPom, setSavingPom] = useState(false)
  // Confirmació de Gravar POM (paral·lel a "Propagar"): missatge SIMPLE la 1a vegada; ADVERTÈNCIA si
  // resembra (el model JA tenia base → llenç net que substitueix). `hadBaseRef` captura l'estat ABANS
  // de cap sembra (primer cop que veiem files de taula-mesures). `confirmRef` desa la promesa que
  // savePom torna a EditableTable: resol en confirmar+desar, rebutja en cancel·lar (no marca "desat").
  const [pomConfirmOpen, setPomConfirmOpen] = useState(false)
  const [pomReseed, setPomReseed] = useState(false)
  const pendingPayloadRef = useRef(null)
  const confirmRef = useRef(null)
  const hadBaseRef = useRef(null)
  const captureHadBase = (rows) => {
    if (hadBaseRef.current === null) hadBaseRef.current = (rows || []).some(r => r.base_value_cm != null)
  }

  const toggleIn = (setter) => (pom) => setter(prev =>
    prev.includes(pom.pom_id) ? prev.filter(x => x !== pom.pom_id) : [...prev, pom.pom_id])
  const togglePom = toggleIn(setSelectedPomIds)      // graella manual (arrenca amb els KEY)

  const refreshTableMeta = (d) => {
    setSizesAmbDades(d.sizes_amb_dades || null)
    setDeltes(d.deltes || null)
  }

  // Recarrega la taula i fixa el mode (mirall de ModelMeasurements.reloadTable, sense l'estat 'tancat':
  // un model verge en genesi no pot estar tancat).
  const reloadTable = (afterMode = 'manual') =>
    fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => { refreshTableMeta(d); captureHadBase(d.rows); if (d.rows?.length) setTaulaRows(d.rows); setMode(afterMode) })
      .catch(() => setMode('selector'))

  // C1 — «Introduir manualment» entra DIRECTE a la taula. La sembra de la llista de POMs de
  // l'item (el que fins ara preguntava un modal previ) és el DEFECTE SILENCIÓS: no hi havia
  // res a preguntar, perquè `materialitzar-poms` és idempotent i no trepitja cap fila ja
  // tocada (sobirania del model, B5). La llei F2.1 —escriure és un acte del tècnic— es
  // manté: l'acte és el clic a la targeta, no un "sí" a una pregunta que no aportava res.
  const entrarManual = async () => {
    setMode('manual')
    if (!model?.garment_type_item || taulaRows.length > 0) return
    setSeedBusy(true)
    try {
      const body = pomsSuggerits.length > 0
        ? JSON.stringify({ pom_ids: pomsSuggerits.map(p => p.pom_id) })
        : undefined
      const res = await fetch(`${API}/api/v1/models/${id}/materialitzar-poms/`, { method: 'POST', headers: authHeaders, body })
      const data = await res.json().catch(() => ({}))
      setBaseSetAbsent(data?.base_set_absent || null)
      await reloadTable('manual')
    } catch {
      setError(t('model_sheet.err_connection'))
    } finally {
      setSeedBusy(false)
    }
  }

  // ── Sprint B · CÒPIA model→model ────────────────────────────────────────────────────────
  // Tercera via de gènesi, germana de la sembra des de l'item: mateixa llei F2.1 (la còpia és
  // un ACTE DEL TÈCNIC — el picker tria, però res s'escriu fins que el modal es confirma) i
  // mateix desenllaç (`reloadTable('manual')`, per poder ajustar abans de sortir).
  const [copyPicker, setCopyPicker] = useState(false)
  const [copySrc, setCopySrc] = useState(null)          // model d'origen triat
  const [copySrcPoms, setCopySrcPoms] = useState([])    // POMs REALS de l'origen (per als chips)
  const [copyPomIds, setCopyPomIds] = useState([])
  const [copyFlags, setCopyFlags] = useState(
    { copy_values: true, copy_run: true, copy_grading: true, copy_files: true })
  const [copyBusy, setCopyBusy] = useState(false)
  const toggleCopyPom = toggleIn(setCopyPomIds)

  // El subconjunt es tria sobre els POMs de l'ORIGEN, no sobre el mapa de l'item: és el que
  // l'endpoint filtra (`pom_ids` es compara amb les mesures del model font).
  const pickCopySource = async (m) => {
    setCopyPicker(false)
    setCopySrc(m)
    setNotice('')
    setCopyFlags({ copy_values: true, copy_run: true, copy_grading: true, copy_files: true })
    try {
      const res = await fetch(`${API}/api/v1/models/${m.id}/taula-mesures/`, { headers: authHeaders })
      const d = await res.json()
      const poms = (d.rows || []).map(r => ({
        pom_id: r.pom_id, pom_code: r.pom_code, nom_ca: r.nom_ca, nom_en: r.nom_en,
      }))
      setCopySrcPoms(poms)
      setCopyPomIds(poms.map(p => p.pom_id))   // proposta: tot; el tècnic hi treu el que no vol
    } catch {
      setCopySrcPoms([]); setCopyPomIds([])
    }
  }

  const confirmCopy = async () => {
    setCopyBusy(true)
    setError('')
    try {
      // Els chips SÓN la petició (mateix criteri que `confirmSeed`). Només s'omet `pom_ids` si
      // no hem pogut llegir els POMs de l'origen: llavors no hi ha res a triar.
      const body = { ...copyFlags, ...(copySrcPoms.length > 0 ? { pom_ids: copyPomIds } : {}) }
      const r = await models.copiarDeModel(id, copySrc.id, body)
      const avisos = r.data?.warnings || []
      setCopySrc(null)
      await reloadTable('manual')
      // Res en silenci: si el backend ha bloquejat valors o ha ignorat el run, es diu.
      if (avisos.length) setNotice(avisos.join(' · '))
    } catch (err) {
      setError(err?.response?.data?.error || t('measures_entry.copy_error'))
      setCopySrc(null)
    } finally {
      setCopyBusy(false)
    }
  }
  const cancelCopy = () => setCopySrc(null)

  // La caixa buida de ModelSheet té una porta pròpia cap a la còpia: quan s'hi entra amb aquesta
  // intenció, el picker s'obre sol. NO escriu res (la llei F2.1 es manté: el modal de confirmació
  // segueix sent l'únic punt que escriu), i l'oferta de sembra des de l'item es calla per no
  // ensenyar dues portes alhora.
  const intentRef = useRef(false)
  useEffect(() => {
    if (intent !== 'copy' || intentRef.current) return
    intentRef.current = true
    setCopyPicker(true)
  }, [intent])

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
        captureHadBase(rows)
        if (rows.length) setTaulaRows(rows)
        const verge = !rows.some(r => r.base_value_cm != null)
        // Si ja té valors (no verge): en mode ENTRADA (Definició POM / Editar POM) va DIRECTE a la graella
        // poblada ('manual') per editar/resembrar — NO al wizard de selecció (manual/import), que és només
        // per a la gènesi des de zero. "Importar taula" segueix disponible a dalt de la graella. Fora de
        // mode entrada, surt a consulta.
        if (!verge) {
          if (entryMode) { setMode('manual'); return }
          onMaterialized?.(); return
        }

        // C1 — mirar segueix sense escriure res: la pantalla de les tres targetes és el que
        // rep un model verge, i la sembra passa quan el tècnic tria «Introduir manualment».
        // (Aquí hi havia una segona lectura de `item-base-measurements` que només servia per
        // decidir QUIN text posava el modal de sembra; sense modal, no cal demanar-la.)
        setMode('selector')
      })
      .catch(() => { if (alive) setMode('selector') })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const sizeRun = (sizesAmbDades && sizesAmbDades.length
    ? sizesAmbDades
    : model?.size_run_model?.split('·').map(s => s.trim())) || []
  const hasValues = taulaRows.some(r => r.base_value_cm != null)

  // Gravar POM passa per CONFIRMACIÓ (paral·lel a Propagar). savePom (cridat per EditableTable amb el
  // payload) NO desa directament: obre el modal i torna una promesa que es resol quan l'usuari confirma
  // i el desat reïx, o es rebutja si cancel·la/falla (perquè EditableTable no marqui la taula com a desada).
  const savePom = (payload) => new Promise((resolve, reject) => {
    pendingPayloadRef.current = payload
    setPomReseed(!!hadBaseRef.current)
    confirmRef.current = { resolve, reject }
    setError('')
    setPomConfirmOpen(true)
  })

  const confirmGravarPom = async () => {
    setSavingPom(true)
    setError('')
    try {
      await models.gravarPom(id, pendingPayloadRef.current)
      setPomConfirmOpen(false)
      confirmRef.current?.resolve()
      onPomSaved?.()
    } catch (err) {
      const msg = err?.response?.data?.error || err?.response?.data?.errors?.join?.(' · ')
        || t('model_measurements.save_pom_err')
      setError(msg)
      setPomConfirmOpen(false)
      confirmRef.current?.reject(err)
    } finally {
      setSavingPom(false)
      confirmRef.current = null
      pendingPayloadRef.current = null
    }
  }

  const cancelGravarPom = () => {
    setPomConfirmOpen(false)
    confirmRef.current?.reject(new Error('cancelled'))
    confirmRef.current = null
    pendingPayloadRef.current = null
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

      {baseSetAbsent && (
        <div style={{ margin: '0 0 1rem', background: 'var(--white)', border: '0.5px solid var(--border)',
                      borderRadius: 8, padding: '0.75rem 1rem', fontSize: 'var(--fs-body)',
                      display: 'flex', alignItems: 'flex-start', gap: 10 }}>
          <IconBulb size={18} stroke={1.5} style={{ color: 'var(--gold)', flexShrink: 0, marginTop: 2 }} />
          <div style={{ flex: 1 }}>
            <div style={{ color: 'var(--text-main)' }}>
              {t('measures_entry.base_set_absent', {
                system: baseSetAbsent.size_system || '—',
                fit: baseSetAbsent.fit_type || t('base_set_panel.fit_regular'),
              })}
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-label)', marginTop: 4 }}>
              {t('measures_entry.base_set_absent_hint')}
            </div>
          </div>
          <button type="button" onClick={() => setBaseSetAbsent(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2,
                     color: 'var(--text-muted)', display: 'inline-flex' }}
            title={t('common.close')}>
            <IconX size={16} stroke={1.5} />
          </button>
        </div>
      )}

      {copyPicker && (
        <ModelPicker
          title={t('measures_entry.copy_pick_title')}
          subtitle={t('measures_entry.copy_pick_subtitle')}
          searchPlaceholder={t('measures_entry.copy_pick_search_ph')}
          emptyLabel={t('measures_entry.copy_pick_empty')}
          loadingLabel={t('common.loading')}
          cancelLabel={t('common.cancel')}
          excludeId={id}
          onPick={pickCopySource}
          onClose={() => setCopyPicker(false)}
        />
      )}

      {copySrc && (
        <Modal
          title={t('measures_entry.copy_confirm_title', { codi: copySrc.codi_intern })}
          subtitle={t('measures_entry.copy_confirm_subtitle')}
          cancelLabel={t('common.cancel')}
          confirmLabel={copyBusy ? t('common.saving') : t('measures_entry.copy_confirm_ok')}
          onCancel={cancelCopy}
          onConfirm={confirmCopy}
          confirmDisabled={copyBusy}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {COPY_FLAGS.map(f => (
              <label key={f} style={{ display: 'flex', alignItems: 'center', gap: 8,
                                      fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
                <input type="checkbox" checked={copyFlags[f]}
                  onChange={e => setCopyFlags(prev => ({ ...prev, [f]: e.target.checked }))} />
                <span style={{ color: 'var(--text-main)' }}>{t(`measures_entry.copy_flag_${f}`)}</span>
              </label>
            ))}
          </div>
          <p style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', margin: '10px 0 0' }}>
            {t('measures_entry.copy_sobirania_hint')}
          </p>
          {copySrcPoms.length > 0 && (
            <>
              <p style={{ fontSize: 'var(--fs-body)', margin: '12px 0 0',
                          color: copyPomIds.length === 0 ? 'var(--warn)' : 'var(--text-muted)' }}>
                {copyPomIds.length === 0
                  ? t('measures_entry.copy_count_zero')
                  : t('measures_entry.copy_count', { total: copySrcPoms.length, tria: copyPomIds.length })}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8, maxHeight: 200,
                            overflowY: 'auto', border: '0.5px solid var(--border)', borderRadius: 8, padding: 8 }}>
                {copySrcPoms.map(p => (
                  <POMChipSuggerit key={p.pom_id} pom={p} selected={copyPomIds.includes(p.pom_id)}
                    onToggle={() => toggleCopyPom(p)} />
                ))}
              </div>
            </>
          )}
        </Modal>
      )}

      {pomConfirmOpen && (
        <Modal
          title={t('model_measurements.gravar_confirm_title')}
          cancelLabel={t('model_measurements.gravar_confirm_cancel')}
          confirmLabel={savingPom ? t('common.saving') : t('model_measurements.gravar_confirm_ok')}
          onCancel={cancelGravarPom}
          onConfirm={confirmGravarPom}
          confirmDisabled={savingPom}
        >
          <p style={{ fontSize: 'var(--fs-body)', margin: 0, display: 'flex', alignItems: 'flex-start', gap: 8,
                      color: pomReseed ? 'var(--err)' : 'var(--text-muted)' }}>
            {pomReseed && <i className="ti ti-alert-triangle" style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }} />}
            {pomReseed ? t('model_measurements.gravar_confirm_reseed') : t('model_measurements.gravar_confirm_simple')}
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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            <div onClick={seedBusy ? undefined : entrarManual}
              style={{ background: 'var(--bg-main)', border: '0.5px solid var(--border)',
                       borderRadius: 12, padding: '1.5rem', cursor: seedBusy ? 'default' : 'pointer',
                       opacity: seedBusy ? 0.6 : 1 }}>
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
            {/* Sprint B — tercera via de gènesi: el patrimoni d'un model germà. Ni manual ni
                import: el que ja està mesurat en un altre model d'aquesta col·lecció. */}
            <div onClick={() => setCopyPicker(true)}
              style={{ background: 'var(--bg-main)', border: '0.5px solid var(--border)',
                       borderRadius: 12, padding: '1.5rem', cursor: 'pointer' }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}><i className="ti ti-copy" style={{ color: 'var(--gold)' }} /></div>
              <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 6 }}>{t('measures_entry.copy_title')}</div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('measures_entry.copy_desc')}</div>
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
