// Modal "Afegir model a la convocatòria" — extret de FittingSessionList (P4) perquè el
// comparteixin la LLISTA (menú d'accions de grup) i la FULLA de convocatòria. Sense duplicar-lo:
// és el mateix acte i el mateix endpoint (`fitting-sessions/group/<uuid>/add-model/`).
//
// El backend encadena l'hora al final de l'última sessió viva del grup i aplica el guard de
// solapament; aquí NO es replica cap d'aquestes regles.
//
// props: { uuid, faseInicial, onDone, onCancel }
//   onDone() — s'ha afegit el model; el cridador recarrega les seves dades.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { fittingSessions, models as modelsApi } from '../../api/endpoints'
import Modal from '../ui/Modal'

const FASES = ['Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']

const selectStyle = {
  width: '100%', padding: '6px 8px', border: '1px solid var(--gray-l)',
  borderRadius: 4, fontSize: 'var(--fs-body)',
}

export default function AddModelToGroupModal({ uuid, faseInicial = '', onDone, onCancel }) {
  const { t } = useTranslation()
  const [modelOpts, setModelOpts] = useState([])
  const [modelId, setModelId] = useState('')
  const [fase, setFase] = useState(faseInicial)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    modelsApi.list({ page_size: 500, ordering: 'codi_intern' })
      .then(r => setModelOpts(r.data.results || r.data || []))
      .catch(() => {})
  }, [])

  const confirmar = () => {
    if (!modelId) { setErr(t('fitting.group.select_model')); return }
    setBusy(true); setErr(null)
    const payload = { model_id: Number(modelId) }
    if (fase) payload.fase = fase
    fittingSessions.groupAddModel(uuid, payload)
      .then(() => onDone())
      .catch(e => setErr(e.response?.status === 409
        ? (e.response?.data?.error || t('fitting.group.model_in_group'))
        : (e.response?.data?.error || 'error')))
      .finally(() => setBusy(false))
  }

  return (
    <Modal title={t('fitting.group.add_model')}
      confirmLabel={busy ? t('common.saving') : t('common.confirm')}
      cancelLabel={t('common.cancel')} confirmDisabled={busy}
      onConfirm={confirmar} onCancel={() => !busy && onCancel()}>
      <label style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('fitting.session.target')}</label>
      <select value={modelId} onChange={e => setModelId(e.target.value)}
        style={{ ...selectStyle, marginBottom: 12 }}>
        <option value="">— {t('fitting.group.select_model')} —</option>
        {modelOpts.map(m => (
          <option key={m.id} value={m.id}>{m.codi_intern}{m.nom_prenda ? ` · ${m.nom_prenda}` : ''}</option>
        ))}
      </select>
      <label style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('fitting.session.fase')}</label>
      <select value={fase} onChange={e => setFase(e.target.value)} style={selectStyle}>
        {FASES.map(f => <option key={f} value={f}>{f}</option>)}
      </select>
      {err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginTop: 10 }}>{err}</div>}
    </Modal>
  )
}
