import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { patterns } from '../../api/endpoints'
import Modal from '../ui/Modal'

// Sostre real de pujada: 20 MiB al backend (services_fitxers.MAX_UPLOAD_BYTES), per sota
// dels 25M d'nginx. Es mostra a l'usuari perquè un DXF de niada pot ser gros i val més
// dir-ho abans que rebotar-ho després.
const MAX_MB = 20

// El render ve del servidor amb la seva paleta de DOCUMENT (patterns/svg.py) i NO es
// re-tinta: un patró tècnic ha de sortir igual a la pantalla, al paper i d'aquí a cinc
// anys. Els tokens són per a la UI, que canvia de tema; això no.

export default function PatternTab({ modelId }) {
  const { t } = useTranslation()

  const [carregant, setCarregant] = useState(true)
  const [cadena, setCadena] = useState([])        // totes les versions del model
  const [actual, setActual] = useState(null)      // el PatternFile que s'està mirant
  const [error, setError] = useState(null)        // { error, issues[] } del 422, o string
  const [pujant, setPujant] = useState(false)
  const [pecaSel, setPecaSel] = useState('')
  const [svgUrl, setSvgUrl] = useState('')
  const [svgCarregant, setSvgCarregant] = useState(false)
  const [confirmarVersio, setConfirmarVersio] = useState(null)  // { dxf, rul }

  const dxfRef = useRef(null)
  const rulRef = useRef(null)
  const objectUrlRef = useRef('')

  // ── càrrega ──────────────────────────────────────────────────────────────
  const carregar = useCallback(async (seleccionarId = null) => {
    setCarregant(true)
    try {
      const { data } = await patterns.list(modelId)
      const llista = data.results || data || []
      setCadena(llista)
      const cap = llista.find(p => p.id === seleccionarId)
        || llista.find(p => p.is_current)
        || llista[0]
      if (cap) {
        const { data: detall } = await patterns.get(cap.id)
        setActual(detall)
      } else {
        setActual(null)
      }
    } catch {
      setError({ error: t('pattern.err_load') })
    } finally {
      setCarregant(false)
    }
  }, [modelId, t])

  useEffect(() => { carregar() }, [carregar])

  // ── el visor ─────────────────────────────────────────────────────────────
  // El render està gated per Authorization i un <img src> no pot portar capçaleres:
  // es baixa com a blob i es mostra per objectURL. L'objectURL es revoca sempre, o cada
  // canvi de peça deixaria un blob viu a la memòria del navegador.
  useEffect(() => {
    if (!actual) return
    let cancelat = false
    setSvgCarregant(true)
    patterns.renderSvg(actual.id, pecaSel)
      .then(({ data }) => {
        if (cancelat) return
        if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
        const url = URL.createObjectURL(data)
        objectUrlRef.current = url
        setSvgUrl(url)
      })
      .catch(() => { if (!cancelat) setSvgUrl('') })
      .finally(() => { if (!cancelat) setSvgCarregant(false) })
    return () => { cancelat = true }
  }, [actual, pecaSel])

  useEffect(() => () => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
  }, [])

  // ── pujada ───────────────────────────────────────────────────────────────
  const pujar = async (dxf, rul, versioAnteriorId = null) => {
    setPujant(true)
    setError(null)
    const fd = new FormData()
    fd.append('model', modelId)
    fd.append('fitxer_dxf', dxf)
    if (rul) fd.append('fitxer_rul', rul)
    if (versioAnteriorId) fd.append('versio_anterior_id', versioAnteriorId)
    try {
      const { data } = await patterns.upload(fd)
      setPecaSel('')
      await carregar(data.id)
    } catch (e) {
      // El 422 porta el detall estructurat del motor: es mostra tal com ve, mai un
      // "error genèric" que obligui l'usuari a endevinar què li passa al seu fitxer.
      setError(e.response?.data || { error: t('pattern.err_upload') })
    } finally {
      setPujant(false)
      if (dxfRef.current) dxfRef.current.value = ''
      if (rulRef.current) rulRef.current.value = ''
    }
  }

  const onTriaFitxers = () => {
    const dxf = dxfRef.current?.files?.[0]
    const rul = rulRef.current?.files?.[0]
    if (!dxf) return
    if (dxf.size > MAX_MB * 1024 * 1024) {
      setError({ error: t('pattern.err_too_big', { mb: MAX_MB }) })
      return
    }
    // Pujar sobre un patró existent és una VERSIÓ NOVA, mai una sobreescriptura muda.
    if (actual) setConfirmarVersio({ dxf, rul })
    else pujar(dxf, rul)
  }

  // ── render ───────────────────────────────────────────────────────────────
  if (carregant) {
    return <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
      {t('pattern.loading')}
    </p>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {error && <ErrorParse error={error} onTanca={() => setError(null)} />}

      {!actual ? (
        <ZonaBuida
          t={t} pujant={pujant}
          dxfRef={dxfRef} rulRef={rulRef} onTria={onTriaFitxers}
        />
      ) : (
        <>
          <Capcalera
            t={t} fp={actual} cadena={cadena}
            onCanviaVersio={id => { setPecaSel(''); carregar(id) }}
            pujant={pujant} dxfRef={dxfRef} rulRef={rulRef} onTria={onTriaFitxers}
          />
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <LlistaPeces
              t={t} pieces={actual.pieces} pecaSel={pecaSel} onTria={setPecaSel}
            />
            <Visor
              t={t} svgUrl={svgUrl} carregant={svgCarregant}
              pecaSel={pecaSel} onTot={() => setPecaSel('')}
            />
          </div>
        </>
      )}

      {confirmarVersio && (
        <Modal
          title={t('pattern.new_version_title')}
          message={t('pattern.new_version_msg', {
            versio: actual?.versio, seguent: (actual?.versio || 0) + 1,
          })}
          confirmLabel={t('pattern.new_version_confirm')}
          cancelLabel={t('app.cancel')}
          onCancel={() => {
            setConfirmarVersio(null)
            if (dxfRef.current) dxfRef.current.value = ''
            if (rulRef.current) rulRef.current.value = ''
          }}
          onConfirm={() => {
            const { dxf, rul } = confirmarVersio
            setConfirmarVersio(null)
            pujar(dxf, rul, actual.id)
          }}
        />
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

function ErrorParse({ error, onTanca }) {
  const { t } = useTranslation()
  const issues = error.issues || []
  return (
    <div style={{
      background: 'var(--err-bg)', border: '1px solid var(--err)', borderRadius: 6,
      padding: '0.75rem 1rem', fontSize: 'var(--fs-body)', color: 'var(--err)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <i className="ti ti-alert-triangle" />
        <strong style={{ flex: 1 }}>{error.error || t('pattern.err_upload')}</strong>
        <button
          onClick={onTanca}
          aria-label={t('app.close')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--err)' }}
        >
          <i className="ti ti-x" />
        </button>
      </div>
      {issues.length > 0 && (
        <ul style={{ margin: '0.5rem 0 0 1.5rem', padding: 0 }}>
          {issues.map((i, n) => (
            <li key={n}>
              <code style={{ fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)' }}>
                {i.codi}
              </code>
              {' — '}{i.missatge}
              {i.peca && <em> ({i.peca})</em>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function CampsPujada({ t, pujant, dxfRef, rulRef, onTria, compacte = false }) {
  return (
    <div style={{
      display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap',
      fontSize: 'var(--fs-body)',
    }}>
      <label style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span style={{ fontSize: 'var(--fs-label)', fontWeight: 600 }}>
          {t('pattern.file_dxf')} <span style={{ color: 'var(--err)' }}>*</span>
        </span>
        <input ref={dxfRef} type="file" accept=".dxf,.DXF" disabled={pujant} />
      </label>
      <label style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span style={{ fontSize: 'var(--fs-label)', fontWeight: 600 }}>
          {t('pattern.file_rul')} <span style={{ color: 'var(--text-muted)' }}>
            ({t('pattern.optional')})
          </span>
        </span>
        <input ref={rulRef} type="file" accept=".rul,.RUL" disabled={pujant} />
      </label>
      <button
        onClick={onTria}
        disabled={pujant}
        style={{
          background: 'var(--gold)', color: 'var(--white)', border: 'none',
          borderRadius: 4, padding: '0.4rem 0.9rem', cursor: pujant ? 'wait' : 'pointer',
          fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', gap: '0.35rem',
        }}
      >
        <i className={pujant ? 'ti ti-loader' : 'ti ti-upload'} />
        {pujant ? t('pattern.uploading') : t('pattern.upload')}
      </button>
      {!compacte && (
        <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)' }}>
          {t('pattern.max_size', { mb: MAX_MB })}
        </span>
      )}
    </div>
  )
}

function ZonaBuida({ t, pujant, dxfRef, rulRef, onTria }) {
  return (
    <div style={{
      border: '1px dashed var(--border)', borderRadius: 8, padding: '2rem',
      textAlign: 'center', background: 'var(--bg-card)',
    }}>
      <i className="ti ti-vector-triangle"
         style={{ fontSize: 32, color: 'var(--text-muted)' }} />
      <h3 style={{ fontSize: 'var(--fs-h3)', margin: '0.5rem 0 0.25rem' }}>
        {t('pattern.empty_title')}
      </h3>
      <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)', margin: '0 0 1rem' }}>
        {t('pattern.empty_hint')}
      </p>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <CampsPujada t={t} pujant={pujant} dxfRef={dxfRef} rulRef={rulRef} onTria={onTria} />
      </div>
    </div>
  )
}

function Capcalera({ t, fp, cadena, onCanviaVersio, pujant, dxfRef, rulRef, onTria }) {
  const g = fp.grade_table
  const avisos = fp.avisos_coherencia || []
  const capesDesconegudes = fp.empremta?.capes_desconegudes || []

  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '0.9rem 1rem',
      display: 'flex', flexDirection: 'column', gap: '0.75rem',
    }}>
      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <Dada t={t} clau="pattern.source_cad" valor={fp.font_cad || '—'} />
        {/* Les unitats no es diuen a seques: es diu COM se saben. Amb la capçalera del
            DXF buida, el factor és una deducció, i qui ho llegeixi ha de saber-ho. */}
        <Dada
          t={t} clau="pattern.units"
          valor={t('pattern.units_value', {
            escala: fp.escala_mm,
            metode: t(`pattern.units_method.${fp.unitats_metode || 'assumed'}`),
            confianca: t(`pattern.confidence.${fp.unitats_confianca || 'low'}`),
          })}
        />
        <Dada t={t} clau="pattern.file" valor={fp.nom_fitxer} />
        <Dada
          t={t} clau="pattern.version"
          valor={
            <select
              value={fp.id}
              onChange={e => onCanviaVersio(parseInt(e.target.value))}
              style={{
                fontSize: 'var(--fs-body)', padding: '2px 4px',
                border: '1px solid var(--border)', borderRadius: 4,
              }}
            >
              {cadena.map(v => (
                <option key={v.id} value={v.id}>
                  {t('pattern.version_option', { versio: v.versio })}
                  {v.is_current ? ` · ${t('pattern.current')}` : ''}
                </option>
              ))}
            </select>
          }
        />
      </div>

      {g && (
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase' }}>
            {t('pattern.sizes')}
          </span>
          {g.talles.map(talla => {
            const base = talla === g.talla_base
            return (
              <span
                key={talla}
                title={base ? t('pattern.base_size') : undefined}
                style={{
                  fontSize: 'var(--fs-caption)', padding: '2px 7px', borderRadius: 10,
                  border: `1px solid ${base ? 'var(--gold)' : 'var(--border)'}`,
                  background: base ? 'var(--gold-pale)' : 'var(--white)',
                  fontWeight: base ? 700 : 400,
                }}
              >
                {talla}{base ? ' ★' : ''}
              </span>
            )
          })}
        </div>
      )}

      {(avisos.length > 0 || capesDesconegudes.length > 0 || fp.pieces?.some(p => !p.has_sew)) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {avisos.map((a, n) => (
            <Avis key={n} tipus="warn" text={a.missatge} />
          ))}
          {fp.pieces?.some(p => !p.has_sew) && (
            <Avis tipus="info" text={t('pattern.no_sew_layer')} />
          )}
          {capesDesconegudes.length > 0 && (
            <Avis
              tipus="info"
              text={t('pattern.unknown_layers_kept', { capes: capesDesconegudes.join(', ') })}
            />
          )}
        </div>
      )}

      <div style={{
        display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center',
        borderTop: '1px solid var(--border)', paddingTop: '0.6rem',
      }}>
        {fp.download_url && (
          <BotoDescarrega href={fp.download_url} icona="ti-file-download"
                          text={t('pattern.download_dxf')} />
        )}
        {fp.te_rul && fp.download_rul_url && (
          <BotoDescarrega href={fp.download_rul_url} icona="ti-table-export"
                          text={t('pattern.download_rul')} />
        )}
        <span style={{ flex: 1 }} />
        <CampsPujada t={t} pujant={pujant} dxfRef={dxfRef} rulRef={rulRef}
                     onTria={onTria} compacte />
      </div>
    </div>
  )
}

function Dada({ t, clau, valor }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      <span style={{
        fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase',
        letterSpacing: '0.03em', color: 'var(--text-muted)',
      }}>
        {t(clau)}
      </span>
      <span style={{ fontSize: 'var(--fs-body)' }}>{valor}</span>
    </div>
  )
}

function Avis({ tipus, text }) {
  const colors = tipus === 'warn'
    ? { fg: 'var(--warn)', bg: 'var(--warn-bg)', icona: 'ti-alert-triangle' }
    : { fg: 'var(--text-muted)', bg: 'var(--bg-muted)', icona: 'ti-info-circle' }
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.4rem',
      fontSize: 'var(--fs-caption)', color: colors.fg, background: colors.bg,
      padding: '3px 8px', borderRadius: 4,
    }}>
      <i className={`ti ${colors.icona}`} />
      <span>{text}</span>
    </div>
  )
}

function BotoDescarrega({ href, icona, text }) {
  return (
    <a
      href={href}
      style={{
        display: 'flex', alignItems: 'center', gap: '0.35rem',
        fontSize: 'var(--fs-body)', color: 'var(--text-main)',
        border: '1px solid var(--border)', borderRadius: 4,
        padding: '0.3rem 0.7rem', textDecoration: 'none', background: 'var(--white)',
      }}
    >
      <i className={`ti ${icona}`} />
      {text}
    </a>
  )
}

function LlistaPeces({ t, pieces, pecaSel, onTria }) {
  const cm = mm => (mm / 10).toFixed(1)
  return (
    <div style={{ flex: '1 1 320px', minWidth: 300 }}>
      <h3 style={{ fontSize: 'var(--fs-h3)', margin: '0 0 0.5rem' }}>
        {t('pattern.pieces', { n: pieces.length })}
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        {pieces.map(p => {
          const sel = p.nom_block === pecaSel
          const bb = p.bounding_box_mm
          const c = p.punts_per_capa || {}
          return (
            <button
              key={p.id}
              onClick={() => onTria(sel ? '' : p.nom_block)}
              aria-pressed={sel}
              style={{
                textAlign: 'left', cursor: 'pointer',
                background: sel ? 'var(--gold-pale)' : 'var(--bg-card)',
                border: `1px solid ${sel ? 'var(--gold)' : 'var(--border)'}`,
                borderRadius: 6, padding: '0.5rem 0.7rem',
                display: 'flex', flexDirection: 'column', gap: 3,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <i className="ti ti-vector-triangle" style={{ color: 'var(--gold)' }} />
                <strong style={{ fontSize: 'var(--fs-body)' }}>{p.nom_block}</strong>
                {p.metadata?.material && (
                  <span style={{
                    fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                    border: '1px solid var(--border)', borderRadius: 8, padding: '0 6px',
                  }}>
                    {p.metadata.material}
                  </span>
                )}
                {!p.has_sew && (
                  <span title={t('pattern.no_sew_layer')}
                        style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)' }}>
                    <i className="ti ti-scissors-off" />
                  </span>
                )}
              </div>
              <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
                {t('pattern.piece_points', {
                  total: p.total_punts, turn: c.turn || 0, curve: c.curve || 0,
                  notch: c.notch || 0,
                })}
              </span>
              {bb && (
                <span style={{
                  fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                  fontFamily: 'var(--mono)',
                }}>
                  {cm(bb.ample)} × {cm(bb.alt)} cm
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function Visor({ t, svgUrl, carregant, pecaSel, onTot }) {
  return (
    <div style={{ flex: '2 1 420px', minWidth: 320 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem',
      }}>
        <h3 style={{ fontSize: 'var(--fs-h3)', margin: 0, flex: 1 }}>
          {pecaSel ? t('pattern.viewer_piece', { peca: pecaSel }) : t('pattern.viewer_all')}
        </h3>
        {pecaSel && (
          <button
            onClick={onTot}
            style={{
              background: 'none', border: '1px solid var(--border)', borderRadius: 4,
              padding: '0.2rem 0.6rem', cursor: 'pointer', fontSize: 'var(--fs-caption)',
              display: 'flex', alignItems: 'center', gap: '0.3rem',
            }}
          >
            <i className="ti ti-arrow-back-up" />
            {t('pattern.viewer_show_all')}
          </button>
        )}
      </div>
      <div style={{
        border: '1px solid var(--border)', borderRadius: 8, background: 'var(--white)',
        padding: '0.5rem', minHeight: 320,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {carregant && (
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
            {t('pattern.viewer_loading')}
          </span>
        )}
        {!carregant && !svgUrl && (
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
            {t('pattern.viewer_error')}
          </span>
        )}
        {!carregant && svgUrl && (
          // El SVG ve del servidor amb la seva paleta de document: NO es re-tinta.
          <img
            src={svgUrl}
            alt={pecaSel || t('pattern.viewer_all')}
            style={{ maxWidth: '100%', maxHeight: 560, objectFit: 'contain' }}
          />
        )}
      </div>
    </div>
  )
}
