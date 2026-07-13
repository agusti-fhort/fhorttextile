import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

// Targeta de pujada de fitxer (design system · Taller W5, fix D6).
//
// El que substitueix: un <input type="file"> natiu, que és invisible com a àrea de treball
// (un botonet gris de 90px), no diu QUÈ espera, no admet arrossegar, i no dona cap senyal
// quan el fitxer ja hi és. La targeta és tot el contrari: gran, clicable sencera, drop-target
// sencera, i diu en tot moment què vol i què té.
//
// La validació d'extensió viu AQUÍ, no al servidor. Un .pdf on hi va un .dxf no ha de viatjar
// per la xarxa, esperar-se, i tornar amb un 400: es rebutja a la targeta, a l'instant, dient
// què s'esperava. El servidor segueix validant (mai no es confia en el client), però l'usuari
// no paga la volta.
//
// props:
//   accept       — extensions acceptades, amb punt: ['.dxf'] · ['.xlsx', '.xls']
//   icon         — icona Tabler OUTLINE (mai -filled)
//   title        — què és aquest fitxer ("Fitxer DXF")
//   file         — el File triat, o null (component CONTROLAT: el pare té l'estat)
//   onFile       — (File|null) => void
//   required     — pinta "obligatori" / "opcional"
//   disabled     — durant la pujada
//   error        — error del SERVIDOR, ja resolt a text pel pare
//   hint         — text secundari opcional sota el títol ("màxim 20 MB")

const MIDA = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const extensioDe = (nom) => {
  const i = (nom || '').lastIndexOf('.')
  return i < 0 ? '' : nom.slice(i).toLowerCase()
}

export default function FileDropCard({
  accept = [],
  icon = 'ti-file-upload',
  title,
  file = null,
  onFile,
  required = false,
  disabled = false,
  error = null,
  hint = null,
}) {
  const { t } = useTranslation()
  const inputRef = useRef(null)
  const [sobre, setSobre] = useState(false)        // s'hi està arrossegant un fitxer a sobre
  const [errExt, setErrExt] = useState(null)       // el fitxer no és del tipus que toca

  const accepta = (f) => {
    if (!accept.length) return true
    return accept.map(a => a.toLowerCase()).includes(extensioDe(f.name))
  }

  const rebre = (f) => {
    if (!f) return
    if (!accepta(f)) {
      // El missatge diu QUÈ s'esperava i QUÈ ha arribat: "aquest fitxer no és un .dxf".
      setErrExt(t('filedrop.bad_ext', {
        esperat: accept.join(', '),
        rebut: extensioDe(f.name) || t('filedrop.no_ext'),
      }))
      onFile?.(null)
      return
    }
    setErrExt(null)
    onFile?.(f)
  }

  const obrir = () => { if (!disabled) inputRef.current?.click() }

  const ple = !!file
  const problema = errExt || error
  const vora = problema ? 'var(--err)' : sobre ? 'var(--gold)' : ple ? 'var(--ok)' : 'var(--gray-l)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: '1 1 260px', minWidth: 240 }}>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label={title}
        onClick={obrir}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); obrir() } }}
        onDragOver={e => { e.preventDefault(); if (!disabled) setSobre(true) }}
        onDragLeave={() => setSobre(false)}
        onDrop={e => {
          e.preventDefault()
          setSobre(false)
          if (disabled) return
          rebre(e.dataTransfer.files?.[0])
        }}
        style={{
          border: `1px ${sobre ? 'solid' : 'dashed'} ${vora}`,
          borderRadius: 10,
          background: sobre ? 'var(--gold-pale)' : 'var(--white)',
          padding: '1.1rem 1rem',
          display: 'flex', alignItems: 'center', gap: 12,
          cursor: disabled ? 'wait' : 'pointer',
          opacity: disabled ? 0.6 : 1,
          transition: 'border-color .12s, background .12s',
          minHeight: 92,
        }}
      >
        <i
          className={`ti ${ple ? 'ti-file-check' : icon}`}
          style={{ fontSize: 26, color: ple ? 'var(--ok)' : 'var(--gold)', flexShrink: 0 }}
        />

        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{
            display: 'flex', alignItems: 'baseline', gap: 6, flexWrap: 'wrap',
            fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)',
          }}>
            <span>{title}</span>
            <span style={{
              fontSize: 'var(--fs-caption)', fontWeight: 400,
              color: required ? 'var(--err)' : 'var(--text-muted)',
            }}>
              {required ? t('filedrop.required') : t('filedrop.optional')}
            </span>
          </div>

          {ple ? (
            <div style={{
              fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 3,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {file.name} · {MIDA(file.size)}
            </div>
          ) : (
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 3 }}>
              {t('filedrop.hint')}
              {accept.length > 0 && <span style={{ marginLeft: 4 }}>({accept.join(' · ')})</span>}
            </div>
          )}

          {hint && !ple && (
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 2 }}>
              {hint}
            </div>
          )}
        </div>

        {ple && !disabled && (
          <button
            type="button"
            onClick={e => { e.stopPropagation(); setErrExt(null); onFile?.(null) }}
            title={t('filedrop.remove')}
            aria-label={t('filedrop.remove')}
            style={{
              background: 'none', border: '0.5px solid var(--border)', borderRadius: 6,
              cursor: 'pointer', padding: '4px 8px', color: 'var(--text-muted)', flexShrink: 0,
            }}
          >
            <i className="ti ti-x" style={{ fontSize: 14 }} />
          </button>
        )}

        <input
          ref={inputRef}
          type="file"
          accept={accept.join(',')}
          hidden
          disabled={disabled}
          onChange={e => { rebre(e.target.files?.[0]); e.target.value = '' }}
        />
      </div>

      {problema && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: 6,
          background: 'var(--err-bg)', color: 'var(--err)',
          borderRadius: 6, padding: '7px 10px', fontSize: 'var(--fs-caption)',
        }}>
          <i className="ti ti-alert-triangle" style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }} />
          <span style={{ minWidth: 0 }}>{problema}</span>
        </div>
      )}
    </div>
  )
}
