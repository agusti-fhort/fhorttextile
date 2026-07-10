import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { modelFitxers, itemFitxers } from '../../api/endpoints'
import { UPLOAD_ACCEPT } from '../../utils/uploads'
import AssetNavigator from '../assets/AssetNavigator'

// FilePicker de l'editor de fitxa (S03b · P7). Reactiva el punt d'entrada que el comentari
// de TechSheetEditor.jsx anticipava ("futur tab Components").
//
// Tres pestanyes:
//   Model    — fitxers del model actual. Inserir imatge → onInsert(f) → addModelFitxer (P2b.3),
//              cridada TAL COM ÉS: aquest component no reimplementa la injecció al canvas.
//   Catàleg  — fitxers de l'ItemFitxer del garment_type_item del model. "Usar al model" crida
//              el cicle ① (P5), que crea una CÒPIA al model; després apareix a la pestanya Model.
//   Importar — puja un fitxer extern DIRECTAMENT al model (mai al catàleg des d'aquí).
//
// L'upload va per fetch cru amb només la capçalera Authorization: si s'hi posa Content-Type,
// el navegador no afegeix el boundary multipart i request.FILES arriba buit (incident conegut,
// documentat al runbook de l'sprint comercial).

const MONO = 'IBM Plex Mono, monospace'
const IMG_RE = /\.(jpg|jpeg|png|svg|webp|gif)$/i
const TABS = ['model', 'catalog', 'import']

const isImage = (f) => IMG_RE.test(f?.nom_fitxer || '') || (f?.mimetype || '').startsWith('image/')

const tabBtn = (active) => ({
  flex: 1, padding: '8px 4px', cursor: 'pointer', fontFamily: MONO,
  fontSize: 'var(--fs-body)', background: active ? 'var(--gold-pale)' : 'transparent',
  color: active ? 'var(--gold)' : 'var(--text-muted)',
  border: 'none', borderBottom: `2px solid ${active ? 'var(--gold)' : 'transparent'}`,
})

const actionBtn = {
  background: 'var(--white)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
  borderRadius: 5, padding: '4px 10px', fontSize: 'var(--fs-caption)',
  cursor: 'pointer', fontFamily: MONO, whiteSpace: 'nowrap',
}

export default function FilePicker({ modelId, garmentTypeItemId, onInsert, onClose }) {
  const { t } = useTranslation()
  const [tab, setTab] = useState('model')
  const [mFiles, setMFiles] = useState(null)
  const [cFiles, setCFiles] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [navOpen, setNavOpen] = useState(false)
  // Memòria de camí del navegador, a nivell d'aquest panell: obrir-lo i tancar-lo no ha de fer
  // recomençar la navegació. Mai localStorage.
  const [nav, setNav] = useState({ tab: 'models', cust: null, any: null, temp: null, modelId: null, gtId: null, gtiId: null })

  const loadModel = useCallback(() => {
    modelFitxers.list({ model: modelId, is_current: true, ordering: '-data_pujada' })
      .then(r => setMFiles(r.data?.results ?? r.data ?? []))
      .catch(() => setMFiles([]))
  }, [modelId])

  const loadCatalog = useCallback(() => {
    if (!garmentTypeItemId) { setCFiles([]); return }
    itemFitxers.list({ garment_type_item: garmentTypeItemId, is_current: true })
      .then(r => setCFiles(r.data?.results ?? r.data ?? []))
      .catch(() => setCFiles([]))
  }, [garmentTypeItemId])

  useEffect(() => { loadModel(); loadCatalog() }, [loadModel, loadCatalog])

  const usarAlModel = async (f) => {
    setBusy(true); setError(null); setNotice(null)
    try {
      await itemFitxers.usarAlModel(f.id, modelId)
      loadModel()                                  // ara ja és a la pestanya Model
      setNotice(t('file_picker.used_ok', { nom: f.nom_fitxer }))
    } catch (e) {
      setError(e?.response?.data?.error || t('file_picker.use_error'))
    } finally {
      setBusy(false)
    }
  }

  // S03c · C5.2 — "Explora tot el tenant": el mateix AssetNavigator que la fitxa tècnica, aquí
  // en modal sobre l'editor. El navegador NOMÉS retorna la selecció; la sobirania la imposa aquí:
  //
  //   fitxer del model actual  → s'insereix tal qual
  //   fitxer d'un ALTRE model  → usar-al-model (model→model, C3.2) i s'insereix la CÒPIA
  //   ItemFitxer del catàleg   → usar-al-model del germà d'items (cicle ①)
  //
  // El que arriba al canvas és SEMPRE un fitxer d'aquest model, mai l'original: si s'hi inserís
  // l'origen, esborrar el model A trencaria el document del model B. El discriminant és el propi
  // objecte (un ItemFitxer porta `garment_type_item`; un ModelFitxer porta `model`).
  const triarDelNavegador = async (f) => {
    if (!f) return
    setBusy(true); setError(null); setNotice(null)
    try {
      let aInserir = f
      if (f.garment_type_item != null) {
        aInserir = (await itemFitxers.usarAlModel(f.id, modelId)).data
      } else if (String(f.model) !== String(modelId)) {
        aInserir = (await modelFitxers.usarAlModel(f.id, modelId)).data
      }
      setNavOpen(false)
      if (aInserir !== f) { loadModel(); setNotice(t('file_picker.used_ok', { nom: f.nom_fitxer })) }
      onInsert(aInserir)
    } catch (e) {
      setError(e?.response?.data?.error || t('file_picker.use_error'))
    } finally {
      setBusy(false)
    }
  }

  const importar = async (file) => {
    if (!file) return
    setBusy(true); setError(null); setNotice(null)
    const fd = new FormData()
    fd.append('fitxer', file)
    fd.append('nom', file.name)
    try {
      // Sense Content-Type: el navegador hi posa el boundary multipart.
      const API = import.meta.env.VITE_API_URL || ''
      const r = await fetch(`${API}/api/v1/models/${modelId}/upload-fitxer/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        body: fd,
      })
      if (!r.ok) throw new Error('upload')
      loadModel()
      setTab('model')
      setNotice(t('file_picker.import_ok', { nom: file.name }))
    } catch {
      setError(t('file_picker.import_error'))
    } finally {
      setBusy(false)
    }
  }

  const renderFiles = (files, { catalog = false } = {}) => {
    if (files === null) {
      return <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('app.loading')}</p>
    }
    if (files.length === 0) {
      return (
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)', fontStyle: 'italic' }}>
          {catalog && !garmentTypeItemId ? t('file_picker.no_item') : t('file_picker.empty')}
        </p>
      )
    }
    return files.map(f => (
      <div key={f.id} style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '7px 0',
        borderBottom: '0.5px solid var(--border)', fontSize: 'var(--fs-body)',
      }}>
        <i className={`ti ${isImage(f) ? 'ti-photo' : 'ti-file'}`} aria-hidden="true"
           style={{ color: 'var(--gold)', flexShrink: 0 }} />
        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              title={f.nom_fitxer}>
          {f.nom_fitxer}
        </span>
        {catalog ? (
          <button type="button" style={actionBtn} disabled={busy} onClick={() => usarAlModel(f)}>
            {t('file_picker.use_in_model')}
          </button>
        ) : isImage(f) ? (
          <button type="button" style={actionBtn} disabled={busy} onClick={() => onInsert(f)}>
            {t('file_picker.insert')}
          </button>
        ) : (
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)' }}>
            {(f.tipus || '').toLowerCase() || '—'}
          </span>
        )}
      </div>
    ))
  }

  return (
    <aside
      role="dialog"
      aria-label={t('file_picker.title')}
      style={{
        position: 'absolute', top: 0, right: 0, bottom: 0, width: 340, zIndex: 30,
        background: 'var(--white)', borderLeft: '0.5px solid var(--border)',
        display: 'flex', flexDirection: 'column', fontFamily: MONO,
      }}>
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 12px', borderBottom: '0.5px solid var(--border)',
      }}>
        <strong style={{ fontSize: 'var(--fs-body)', fontWeight: 500 }}>{t('file_picker.title')}</strong>
        <button type="button" onClick={onClose} aria-label={t('file_picker.close')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
          <i className="ti ti-x" aria-hidden="true" />
        </button>
      </header>

      <div style={{ display: 'flex', borderBottom: '0.5px solid var(--border)' }}>
        {TABS.map(k => (
          <button key={k} type="button" style={tabBtn(tab === k)} onClick={() => setTab(k)}>
            {t(`file_picker.tab_${k}`)}
          </button>
        ))}
      </div>

      <div style={{ padding: '8px 12px', borderBottom: '0.5px solid var(--border)' }}>
        <button type="button" disabled={busy} onClick={() => setNavOpen(true)}
          style={{ ...actionBtn, width: '100%', justifyContent: 'center', display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px' }}>
          <i className="ti ti-building-warehouse" aria-hidden="true" />
          {t('file_picker.explore_tenant')}
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px' }}>
        {error && (
          <div role="alert" style={{ color: 'var(--err)', fontSize: 'var(--fs-caption)', marginBottom: 8 }}>
            {error}
          </div>
        )}
        {notice && (
          <div style={{ color: 'var(--gold)', fontSize: 'var(--fs-caption)', marginBottom: 8 }}>
            {notice}
          </div>
        )}

        {tab === 'model' && renderFiles(mFiles)}
        {tab === 'catalog' && renderFiles(cFiles, { catalog: true })}
        {tab === 'import' && (
          <div>
            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)', marginBottom: 10 }}>
              {t('file_picker.import_hint')}
            </p>
            <input type="file" disabled={busy}
              accept={UPLOAD_ACCEPT}
              aria-label={t('file_picker.tab_import')}
              onChange={e => importar(e.target.files?.[0])}
              style={{ fontSize: 'var(--fs-body)', fontFamily: MONO }} />
          </div>
        )}
      </div>

      {navOpen && (
        <AssetNavigator
          mode="files"
          nav={nav}
          onNav={setNav}
          onClose={() => setNavOpen(false)}
          onPick={triarDelNavegador}
          pickable={isImage}
          actionLabel={t('file_picker.insert')}
        />
      )}
    </aside>
  )
}
