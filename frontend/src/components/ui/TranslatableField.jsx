// <TranslatableField> — camp de text traduïble reutilitzable (patró híbrid).
// L'input principal edita el valor CANÒNIC (EN), que viu a la columna del model i és el
// fallback sempre present. Un botó "idiomes" desplega un panell per afegir/editar la
// traducció de cada idioma addicional. Sense estat propi de dades: rep `value` (EN) i
// `translations` ({ camp: { idioma: text } }) del pare i n'informa els canvis.
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { selS } from './buttons'

const MONO = 'IBM Plex Mono, monospace'

// Idiomes addicionals a l'EN canònic (la columna). Escalable a N: afegir codis ISO 639-1.
export const TRANSLATION_LANGS = ['ca', 'es']

// Valor a mostrar d'un camp traduïble: traducció de l'idioma de la UI o fallback a l'EN canònic.
export function pickTranslation(obj, field, lang) {
  if (!obj) return ''
  const code = (lang || 'en').slice(0, 2)
  const canonical = obj[field] ?? ''
  if (code === 'en') return canonical
  const tr = obj.translations?.[field]?.[code]
  return tr && tr.trim() ? tr : canonical
}

const labelS = {
  fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
  textTransform: 'uppercase', display: 'block',
}

export default function TranslatableField({
  label, field, value, onChange, translations = {}, onTranslationsChange,
  langs = TRANSLATION_LANGS, multiline = false, placeholder,
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const per = translations[field] || {}
  const filled = langs.filter(l => (per[l] || '').trim()).length

  const setLang = (lang, text) => onTranslationsChange({
    ...translations, [field]: { ...per, [lang]: text },
  })

  const Input = multiline ? 'textarea' : 'input'
  const inputStyle = { ...selS, width: '100%', ...(multiline ? { minHeight: 60, resize: 'vertical' } : {}) }

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
        <label style={labelS}>{label} <span style={{ color: 'var(--gray)' }}>· EN</span></label>
        <button type="button" onClick={() => setOpen(o => !o)} style={{
          background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
          padding: '3px 8px', fontSize: 'var(--fs-label)', fontFamily: MONO,
          color: filled ? 'var(--gold)' : 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: 4,
        }}>
          <i className="ti ti-language" style={{ fontSize: 13 }} />
          {t('i18n_field.languages')}{filled ? ` · ${filled}` : ''}
        </button>
      </div>
      <Input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={inputStyle} />
      {open && (
        <div style={{
          marginTop: 8, padding: 10, border: '0.5px solid var(--border)', borderRadius: 8,
          background: 'var(--bg-muted)', display: 'grid', gap: 8,
        }}>
          <span style={{ ...labelS, fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>{t('i18n_field.panel_hint')}</span>
          {langs.map(l => (
            <div key={l}>
              <label style={{ ...labelS, fontSize: 'var(--fs-label)', marginBottom: 4 }}>{l.toUpperCase()}</label>
              <Input value={per[l] || ''} onChange={e => setLang(l, e.target.value)}
                placeholder={value || placeholder} style={inputStyle} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
