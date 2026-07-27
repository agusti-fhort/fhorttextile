// Botó unificat de descàrrega de PDF dels documents comercials (P7). Mateix component, mateixa
// posició (capçalera de la fitxa, dreta), icona Tabler outline file-type-pdf i color --pdf-accent
// (token semàntic = var(--grana)). L'usen Oferta, Comanda i Albarà v2.
//
// SELECTOR D'IDIOMA (2026-07-27): quan es passa `onLangChange`, el botó ve precedit d'un selector
// d'idioma del document. Viu AQUÍ i no a cada pàgina perquè els tres fluxos comparteixen el botó:
// una sola definició, tres superfícies (llei d'unificar el ja construït). Sense `onLangChange` el
// component es comporta exactament com abans (l'usa la pàgina de demo del kit).
//
// El buit ('') és un valor legítim: «sense preselecció» — el client destinatari no en té cap de
// fixat. No bloqueja la descàrrega; el backend resol l'idioma efectiu (resolve_pdf_lang) i cau al
// fallback. Qui vulgui un idioma concret, el tria aquí.
import { useEffect, useState } from 'react'

const MONO = 'IBM Plex Mono, monospace'

export const PDF_LANGS = ['ca', 'en', 'es']

// Estat del selector per a una fitxa de document. El document arriba per fetch, així que
// l'idioma del client no hi és al primer render: quan arriba, s'adopta com a default —però
// NOMÉS si l'operador encara no ha triat res, perquè la seva tria no se li trepitgi a sota.
export function usePdfLang(customerLanguage) {
  const [lang, setLang] = useState(customerLanguage || '')
  const [touched, setTouched] = useState(false)
  useEffect(() => { if (!touched) setLang(customerLanguage || '') }, [customerLanguage, touched])
  return [lang, (v) => { setTouched(true); setLang(v) }]
}

export default function PdfButton({ onClick, disabled, label, lang, onLangChange, t }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      {onLangChange && (
        <select value={lang || ''} onChange={e => onLangChange(e.target.value)} disabled={disabled}
          title={t('commerce.pdf_lang')} aria-label={t('commerce.pdf_lang')} style={{
            background: 'none', border: '0.5px solid var(--border)', borderRadius: 6,
            padding: '5px 8px', fontSize: 'var(--fs-body)', fontFamily: MONO,
            color: 'var(--text-muted)', cursor: disabled ? 'default' : 'pointer',
          }}>
          <option value="">{t('commerce.pdf_lang_none')}</option>
          {PDF_LANGS.map(l => <option key={l} value={l}>{t(`commerce.pdf_lang_${l}`)}</option>)}
        </select>
      )}
      <button onClick={onClick} disabled={disabled} title={label} style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: 'none', border: '0.5px solid var(--pdf-accent)', borderRadius: 6,
        padding: '5px 11px', cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.5 : 1,
        fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--pdf-accent)',
      }}>
        <i className="ti ti-file-type-pdf" style={{ fontSize: 15 }} aria-hidden="true" />
        {label}
      </button>
    </span>
  )
}
