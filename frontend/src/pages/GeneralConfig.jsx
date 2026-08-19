import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { tenantConfig } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import PageMenu from '../components/ui/PageMenu'
import { apagat, botoPri, selS } from '../components/ui/buttons'
import { useElements } from '../utils/vocabulariDominiFont'

// Mòdul Sistema — M5 · Configuració General del tenant (TenantConfig). Exposa hourly_rate (tarifa
// interna de COST, ≠ tarifes de venda de Product) i la config bàsica de l'estudi. GET/PATCH a
// /api/v1/tenant-config/. Escriptura visible per a CONFIGURE (gate del menú).
const MONO = 'IBM Plex Mono, monospace'
// LES DUES ENUMERACIONS SE'N VAN DEL CLIENT (llei 1). `UNITS` i `NORMS` eren dues còpies dels
// `choices` de `TenantConfig` (`accounts/models.py:31-32`) i ara surten de `/vocabulari/` →
// `unitats_mesura` · `normes_referencia`. El mòdul del vocabulari les tenia CENSADES-PENDENTS
// amb el motiu escrit —«l'ordre les condicionava a que Mesures/Fitting les PINTESSIN, i no les
// pinten»—; la condició s'ha complert per l'altra banda: la pantalla que SÍ que les pinta és
// aquesta, i passa conformitat ara.
// ⚠️ Sense vocabulari, els dos selects NO ofereixen cap opció. És la conducta de la casa i és
// deliberada: un select amb una llista de reserva és la segona font de veritat, disfressada.

// Compara el payload enviat amb la resposta 200 del backend i torna els camps que NO s'han
// desat (per no mostrar mai un "desat" fals). `hourly_rate` es compara numèricament (el backend
// normalitza els decimals, p.ex. "25" → "25.00"); la resta com a text normalitzat.
const _norm = (v) => (v == null ? '' : String(v).trim())
function unsavedFields(payload, data) {
  if (!data) return Object.keys(payload)
  return Object.keys(payload).filter(k => {
    if (k === 'hourly_rate') {
      const a = payload[k] == null || payload[k] === '' ? null : Number(payload[k])
      const b = data[k] == null || data[k] === '' ? null : Number(data[k])
      return a !== b
    }
    return _norm(payload[k]) !== _norm(data[k])
  })
}

export default function GeneralConfig() {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  // `useElements` i no `useEnumeracio` a posta: la norma de referència s'ensenya amb l'ETIQUETA
  // del propi `choices` («ISO 8559 (EU)»), que és nom d'estàndard i no es tradueix. La unitat, en
  // canvi, té claus i18n pròpies des de sempre i les conserva: el codi mana, l'etiqueta la tria
  // qui pinta.
  const { elements: unitats } = useElements('unitats_mesura')
  const { elements: normes } = useElements('normes_referencia')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [f, setF] = useState({
    nom_empresa: '', legal_name: '', tax_id: '', address: '', postal_code: '', city: '',
    country: 'ES', email: '', phone: '',
    unitat_mesura: 'CM', norma_referencia: 'ISO_8559', hourly_rate: '', iban: '', payment_notes: '',
  })
  const [logo, setLogo] = useState(null)   // URL del logo del tenant (preview)
  const logoRef = useRef(null)
  const set = (k, v) => setF(prev => ({ ...prev, [k]: v }))

  const hydrate = (d) => {
    setF({
      nom_empresa: d.nom_empresa || '',
      legal_name: d.legal_name || '',
      tax_id: d.tax_id || '',
      address: d.address || '',
      postal_code: d.postal_code || '',
      city: d.city || '',
      country: d.country || 'ES',
      email: d.email || '',
      phone: d.phone || '',
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
    const payload = {
      nom_empresa: f.nom_empresa, unitat_mesura: f.unitat_mesura,
      norma_referencia: f.norma_referencia,
      legal_name: f.legal_name, tax_id: f.tax_id, address: f.address,
      postal_code: f.postal_code, city: f.city, country: f.country,
      email: f.email, phone: f.phone,
      hourly_rate: f.hourly_rate === '' ? null : f.hourly_rate,
      iban: f.iban, payment_notes: f.payment_notes,
    }
    tenantConfig.update(payload)
      .then(res => {
        // Toast d'èxit NOMÉS si la resposta confirma els valors enviats; mai un "desat" fals.
        const unsaved = unsavedFields(payload, res.data)
        if (unsaved.length) {
          setFeedback({ type: 'err', text: t('config_general.save_mismatch', {
            fields: unsaved.map(k => t(`config_general.${k}`)).join(', ') }) })
        } else {
          hydrate(res.data)   // reflecteix l'estat persistit real
          setFeedback({ type: 'ok', text: t('config_general.saved') })
        }
      })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || e?.response?.data?.detail || t('config_general.error') }))
      .finally(() => setSaving(false))
  }

  const onLogoPick = (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setSaving(true); setFeedback(null)
    tenantConfig.uploadLogo(file)
      .then(res => { hydrate(res.data); setFeedback({ type: 'ok', text: t('config_general.logo_uploaded') }) })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || t('config_general.error') }))
      .finally(() => setSaving(false))
  }

  if (loading) return <Center>{t('config_general.loading')}</Center>
  if (error) return <Center>{t('config_general.error')}</Center>

  return (
    <>
      {/* §8b · menú de pantalla; sense seccions ni acció, queda la fletxa (§8b.2). L'acció
          primària de la pantalla (Desar) viu al CONTINGUT, que és on la §8e la deixa. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu backTo="/" backTitle={t('config_general.back_title')} />
      </div>

    <div style={{ minWidth: 0, maxWidth: 560, paddingTop: 16 }}>
      {/* §8b.3 · identitat. El títol anava a `--fs-h2` (18) quan el títol de PÀGINA de la casa
          és `--fs-h1` (22/500); i el subtítol, a pes 300, que no és cap dels tres pesos. */}
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500, marginBottom: 4, color: 'var(--text-main)', fontFamily: MONO }}>{t('config_general.title')}</h1>
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontFamily: MONO }}>{t('config_general.subtitle')}</p>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      <input ref={logoRef} type="file" accept=".svg,.png,.jpg,.jpeg,image/svg+xml,image/png,image/jpeg" hidden onChange={onLogoPick} />
      <div style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-card)', background: 'var(--panel)', fontSize: 'var(--fs-body)', padding: 16 }}>
        <Field label={t('config_general.nom_empresa')}>
          <input value={f.nom_empresa} onChange={e => set('nom_empresa', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }} />
        </Field>

        {/* Identitat fiscal de l'emissor — surt a la capçalera dels documents PDF (fi del hardcode). */}
        <p style={{ fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-soft)', fontWeight: 600, textTransform: 'uppercase', margin: '4px 0 12px', letterSpacing: '.08em' }}>{t('config_general.fiscal_section')}</p>
        <Field label={t('config_general.legal_name')} hint={t('config_general.legal_name_hint')}>
          <input value={f.legal_name} onChange={e => set('legal_name', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('config_general.tax_id')}>
          <input value={f.tax_id} onChange={e => set('tax_id', e.target.value)} disabled={!canEdit} placeholder="B12345678" style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('config_general.address')}>
          <input value={f.address} onChange={e => set('address', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }} />
        </Field>
        <div style={{ display: 'flex', gap: 12 }}>
          <div style={{ flex: '0 0 120px' }}>
            <Field label={t('config_general.postal_code')}>
              <input value={f.postal_code} onChange={e => set('postal_code', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }} />
            </Field>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Field label={t('config_general.city')}>
              <input value={f.city} onChange={e => set('city', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }} />
            </Field>
          </div>
          <div style={{ flex: '0 0 90px' }}>
            <Field label={t('config_general.country')} hint={t('config_general.country_hint')}>
              <input value={f.country} onChange={e => set('country', e.target.value.toUpperCase().slice(0, 2))} disabled={!canEdit} placeholder="ES" style={{ ...selS, width: '100%' }} />
            </Field>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Field label={t('config_general.email')}>
              <input type="email" value={f.email} onChange={e => set('email', e.target.value)} disabled={!canEdit} placeholder="hola@empresa.cat" style={{ ...selS, width: '100%' }} />
            </Field>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Field label={t('config_general.phone')}>
              <input value={f.phone} onChange={e => set('phone', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }} />
            </Field>
          </div>
        </div>

        <Field label={t('config_general.logo')} hint={t('config_general.logo_hint')}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 88, height: 44, border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-page)', overflow: 'hidden', flex: 'none' }}>
              {logo
                ? <img src={logo} alt="logo" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                : <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-faint)', fontFamily: MONO }}>—</span>}
            </div>
            {canEdit && (
              <button onClick={() => logoRef.current?.click()} disabled={saving} style={{ ...selS, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <i className="ti ti-photo" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />{logo ? t('config_general.logo_replace') : t('config_general.logo_upload')}
              </button>
            )}
          </div>
        </Field>
        <Field label={t('config_general.unitat_mesura')}>
          <select value={f.unitat_mesura} onChange={e => set('unitat_mesura', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }}>
            {(unitats || []).map(u => <option key={u.codi} value={u.codi}>{u.codi === 'CM' ? t('config_general.unit_cm') : t('config_general.unit_inch')}</option>)}
          </select>
        </Field>
        <Field label={t('config_general.norma_referencia')}>
          <select value={f.norma_referencia} onChange={e => set('norma_referencia', e.target.value)} disabled={!canEdit} style={{ ...selS, width: '100%' }}>
            {(normes || []).map(n => <option key={n.codi} value={n.codi}>{n.etiqueta}</option>)}
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

        {/* §5.1 · l'acció primària de la pantalla, i l'única. El deshabilitat baixa el FONS,
            no la tinta (§5.7): l'`opacity: 0.5` apagava també el text.
            (El comentari va FORA del `{canEdit && (…)}`: a dins encara ets en context
            d'expressió i les claus es llegirien com un objecte literal.) */}
        {canEdit && (
          <button onClick={save} disabled={saving} style={{ ...botoPri, marginTop: 8, ...(saving ? apagat : null) }}>
            <i className="ti ti-device-floppy" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />{t('config_general.save')}
          </button>
        )}
      </div>
    </div>
    </>
  )
}

// §2 · el RÈTOL de camp de la casa: 10px MAJÚSCULES amb tracking, no cos a 12 en majúscules
// (que és la mida d'un valor, no d'una etiqueta). I les tintes, l'escala de la §1b(c).
function Field({ label, hint, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: '.08em', fontFamily: MONO, color: 'var(--text-soft)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
      {hint && <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-faint)', margin: '4px 0 0' }}>{hint}</p>}
    </div>
  )
}
