import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { models } from '../../api/endpoints'
import useAuthStore from '../../store/auth'
import Modal from '../ui/Modal'

// P0+P2+P3 — L'ACTE DE PROMOCIÓ model→item, a la superfície on el tècnic ja treballa les mesures.
//
// LLEI (Agus, 2026-07-22): «La sobirania del model és sobre els SEUS valors. L'estàndard del
// taller és un acte separat, explícit i CONFIGURE — mai un efecte secundari d'un import.»
// Per això és un BOTÓ, no un pas d'un flux: qui promou ha de voler promoure.
//
// Dues fases sempre (D-PROM): primer clic = dry-run que ensenya el diff sencer i no escriu res;
// el botó del modal és el que aplica. Visible NOMÉS amb capability CONFIGURE — el mateix gate
// que el backend, perquè la UI no ofereixi una porta que després es tanca amb un 403.

const MONO = 'IBM Plex Mono, monospace'

const secS = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 4,
  border: '0.5px solid var(--gold)', background: 'var(--white)', color: 'var(--gold)',
  cursor: 'pointer', fontSize: 'var(--fs-body)', fontFamily: MONO,
}

// Una secció del diff. `tone` tenyeix el comptador; les files sempre en mono per llegir números.
function Bloc({ titol, files, tone, render }) {
  if (!files?.length) return null
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 'var(--fs-label)', fontWeight: 600, color: tone, marginBottom: 4 }}>
        {titol} ({files.length})
      </div>
      <ul style={{ margin: 0, paddingLeft: 18, fontSize: 'var(--fs-caption)', fontFamily: MONO,
                   color: 'var(--text-muted)', maxHeight: 150, overflowY: 'auto' }}>
        {files.map(f => <li key={f.pom_id} style={{ marginBottom: 1 }}>{render(f)}</li>)}
      </ul>
    </div>
  )
}

export default function PromoteToItemButton({ model, onFeedback }) {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canConfigure = !!me?.capabilities?.includes('configure')
  const [diff, setDiff] = useState(null)
  const [busy, setBusy] = useState(false)

  // El gate de la UI és el MATEIX que el del backend: sense CONFIGURE el botó no existeix.
  // Un model sense item no té plantilla on promoure res.
  if (!canConfigure || !model?.garment_type_item) return null

  const err = (e) => onFeedback?.({
    type: 'err',
    text: e?.response?.data?.error || e?.response?.data?.detall || t('promote.err'),
  })

  const simular = () => {
    setBusy(true)
    models.promoureAItem(model.id, false)
      .then(r => setDiff(r.data))
      .catch(err)
      .finally(() => setBusy(false))
  }

  const aplicar = () => {
    setBusy(true)
    models.promoureAItem(model.id, true)
      .then(r => {
        setDiff(null)
        onFeedback?.({ type: 'ok', text: r.data.message })
      })
      .catch(err)
      .finally(() => setBusy(false))
  }

  const resum = diff?.resum
  // Res a escriure = res a confirmar. El modal segueix obert per ensenyar els «sobrarien».
  const senseCanvis = resum && resum.nous === 0 && resum.canvien === 0 && resum.iguals === 0

  return (
    <>
      <button type="button" onClick={simular} disabled={busy} style={{
        ...secS, opacity: busy ? 0.6 : 1, cursor: busy ? 'wait' : 'pointer' }}>
        <i className="ti ti-arrow-up-circle" aria-hidden="true" style={{ fontSize: 16 }} />
        {t('promote.cta')}
      </button>

      {diff && (
        <Modal
          title={t('promote.title', { item: diff.item_code })}
          subtitle={t('promote.subtitle', { model: diff.model_codi, talla: diff.talla_model })}
          cancelLabel={t('common.cancel')}
          confirmLabel={t('promote.confirm')}
          confirmDisabled={busy || senseCanvis}
          onCancel={() => setDiff(null)}
          onConfirm={aplicar}
        >
          {/* P3 — la talla que s'escriurà a la plantilla. És l'única cosa que la promoció
              aporta i que ningú més sap: el moment on el sistema SAP en quina talla parlen
              els valors. Si no es pot resoldre, es diu per què i no s'amaga. */}
          <div style={{ background: 'var(--bg-muted)', borderRadius: 6, padding: '8px 10px',
                        marginBottom: 12, fontSize: 'var(--fs-caption)', fontFamily: MONO }}>
            {diff.talla_a_escriure
              ? t('promote.talla_ok', { talla: diff.talla_a_escriure })
              : <span style={{ color: 'var(--err)' }}>{diff.talla_motiu}</span>}
          </div>

          <Bloc titol={t('promote.nous')} files={diff.nous} tone="var(--ok)"
            render={f => `${f.codi} · ${f.nom} → ${f.valor_model} cm`} />
          <Bloc titol={t('promote.canvien')} files={diff.canvien} tone="var(--gold)"
            render={f => `${f.codi} · ${f.valor_item ?? '—'} → ${f.valor_model} cm`} />
          <Bloc titol={t('promote.iguals')} files={diff.iguals} tone="var(--text-muted)"
            render={f => `${f.codi} · ${f.valor_model} cm`} />
          <Bloc titol={t('promote.sobrarien')} files={diff.sobrarien} tone="var(--text-muted)"
            render={f => `${f.codi} · ${f.valor_item ?? '—'}`} />

          {diff.sobrarien?.length > 0 && (
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 6 }}>
              {t('promote.sobrarien_help')}
            </div>
          )}
          {senseCanvis && (
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 6 }}>
              {t('promote.sense_canvis')}
            </div>
          )}
        </Modal>
      )}
    </>
  )
}
