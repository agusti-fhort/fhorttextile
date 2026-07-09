import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { tenantConfig } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import { selS, primaryBtn } from '../components/ui/buttons'

// Mòdul Sistema — M5 · Configuració General del tenant (TenantConfig). Exposa hourly_rate (tarifa
// interna de COST, ≠ tarifes de venda de Product) i la config bàsica de l'estudi. GET/PATCH a
// /api/v1/tenant-config/. Escriptura visible per a CONFIGURE (gate del menú).
const MONO = 'IBM Plex Mono, monospace'
const UNITS = ['CM', 'INCH']
const NORMS = ['ISO_8559', 'ASTM_D13']

export default function GeneralConfig() {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [f, setF] = useState({ nom_empresa: '', unitat_mesura: 'CM', norma_referencia: 'ISO_8559', hourly_rate: '', iban: '', payment_notes: '' })
  const [logo, setLogo] = useState(null)   // URL del logo del tenant (preview)
  const logoRef = useRef(null)
  const set = (k, v) => setF(prev => ({ ...prev, [k]: v }))

  const hydrate = (d) => {
    setF({
      nom_empresa: d.nom_empresa || '',
      unitat_mesura: d.unitat_mesura || 'CM',
      norma_referencia: d.norma_referencia || 'ISO_8559',
      hourly_rate: d.hourly_rate ?? '',
      iban: d.iban || '',
      payment_notes: d.payment_notes || '',
    })
    setLogo(d.logo_file || null)
  }

  useEffect(() => {
    let alive = true
    tenantConfig.get()
      .then(res => { if (alive) hydrate(res.data) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const save = () => {
    setSaving(true); setFeedback(null)
    tenantConfig.update({
      nom_empresa: f.nom_empresa, unitat_mesura: f.unitat_mesura,
      norma_referencia: f.norma_referencia,
      hourly_rate: f.hourly_rate === '' ? null : f.hourly_rate,
      iban: f.iban, payment_notes: f.payment_notes,
    })
      .then(() => setFeedback({ type: 'ok', text: t('config_general.saved') }))
      .catch(() => setFeedback({ type: 'err', text: t('config_general.error') }))
      .finally(() => setSaving(false))
  }

  const onLogoPick = (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setSaving(true); setFeedback(null)
    tenantConfig.uploadLogo(file)
      .then(res => { hydrate(res.data); setFeedback({ type: 'ok', text: t('config_general.logo_uploaded') }) })
      .catch(() => setFeedback({ type: 'err', text: t('config_general.error') }))
      .finally(() => setSaving(false))
  }

  if (loading) return <Center>{t('config_general.loading')}</Center>
  if (error) return <Center>{t('config_general.error')}</Center>

  return (
    <div style={{ minWidth: 0, maxWidth: 560 }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('config_general.title')}</h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('config_general.subtitle')}</p>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      <input ref={logoRef} type="file" accept="image/*" hidden onChange={onLogoPick} />
      <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: 20 }}>
        <Field label={t('config_general.nom_empresa')}>
          <input value={f.nom_empresa} onChange={e => set('nom_empresa', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('config_general.logo')} hint={t('config_general.logo_hint')}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 88, height: 44, border: '0.5px solid var(--gray-l)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-muted)', overflow: 'hidden', flex: 'none' }}>
              {logo
                ? <img src={logo} alt="logo" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                : <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--gray)', fontFamily: MONO }}>—</span>}
            </div>
            {canEdit && (
              <button onClick={() => logoRef.current?.click()} disabled={saving} style={{ ...selS, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <i className="ti ti-photo" style={{ fontSize: 14 }} />{logo ? t('config_general.logo_replace') : t('config_general.logo_upload')}
              </button>
            )}
          </div>
        </Field>
        <Field label={t('config_general.unitat_mesura')}>
          <select value={f.unitat_mesura} onChange={e => set('unitat_mesura', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }}>
            {UNITS.map(u => <option key={u} value={u}>{u === 'CM' ? t('config_general.unit_cm') : t('config_general.unit_inch')}</option>)}
          </select>
        </Field>
        <Field label={t('config_general.norma_referencia')}>
          <select value={f.norma_referencia} onChange={e => set('norma_referencia', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }}>
            {NORMS.map(n => <option key={n} value={n}>{n === 'ISO_8559' ? 'ISO 8559' : 'ASTM D13'}</option>)}
          </select>
        </Field>
        <Field label={t('config_general.hourly_rate')} hint={t('config_general.hourly_rate_hint')}>
          <input type="text" inputMode="decimal" value={f.hourly_rate} onChange={e => set('hourly_rate', e.target.value)}
            disabled={!canEdit} placeholder="ex: 25.00" style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('config_general.iban')} hint={t('config_general.iban_hint')}>
          <input value={f.iban} onChange={e => set('iban', e.target.value)} disabled={!canEdit}
            placeholder="ES00 0000 0000 0000 0000 0000" style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('config_general.payment_notes')} hint={t('config_general.payment_notes_hint')}>
          <textarea value={f.payment_notes} onChange={e => set('payment_notes', e.target.value)} disabled={!canEdit}
            rows={2} style={{ ...selS, width: '100%', resize: 'vertical', fontFamily: MONO }} />
        </Field>

        {canEdit && (
          <button onClick={save} disabled={saving} style={{ ...primaryBtn, marginLeft: 0, marginTop: 8, opacity: saving ? 0.5 : 1 }}>
            <i className="ti ti-device-floppy" style={{ fontSize: 14 }} />{t('config_general.save')}
          </button>
        )}
      </div>
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
      {hint && <p style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', margin: '4px 0 0' }}>{hint}</p>}
    </div>
  )
}
