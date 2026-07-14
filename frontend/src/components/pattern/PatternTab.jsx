import { useState, useEffect, useCallback, useRef } from 'react'
import FileDropCard from '../ui/FileDropCard'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { patterns } from '../../api/endpoints'
import Modal from '../ui/Modal'
import PatternViewer from './PatternViewer'
import PieceList from './PieceList'
import ExportModal from './ExportModal'

// Sostre real de pujada: 20 MiB al backend (services_fitxers.MAX_UPLOAD_BYTES), per sota
// dels 25M d'nginx. Es mostra a l'usuari perquè un DXF de niada pot ser gros i val més
// dir-ho abans que rebotar-ho després.
const MAX_MB = 20

// El render ve del servidor amb la seva paleta de DOCUMENT (patterns/svg.py) i NO es
// re-tinta: un patró tècnic ha de sortir igual a la pantalla, al paper i d'aquí a cinc
// anys. Els tokens són per a la UI, que canvia de tema; això no.

/**
 * Tab Patró — la PORTA (W2).
 *
 * Metadades, avisos, versions, upload, descàrregues i exportació de la niada. El VISOR hi
 * queda en mode consulta (zoom/pan/capes): es pot mirar el patró, no anotar-lo.
 *
 * Les EINES (marcar POM, cosir) i el rellotge de la tasca pattern_digit viuen al TALLER
 * (/models/:id/patro/taller). Una porta no és un banc de treball: qui ve a consultar el
 * fitxer no ha d'obrir cap tasca, i qui ve a treballar entra al taller i el rellotge corre.
 */
export default function PatternTab({ modelId }) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [carregant, setCarregant] = useState(true)
  const [cadena, setCadena] = useState([])        // totes les versions del model
  const [actual, setActual] = useState(null)      // el PatternFile que s'està mirant
  const [error, setError] = useState(null)        // { error, issues[] } del 422, o string
  const [pujant, setPujant] = useState(false)
  const [pecaSel, setPecaSel] = useState('')
  const [svgUrl, setSvgUrl] = useState('')
  const [svgCarregant, setSvgCarregant] = useState(false)
  const [confirmarVersio, setConfirmarVersio] = useState(null)  // { dxf, rul }
  const [geometria, setGeometria] = useState(null)
  const [geoCarregant, setGeoCarregant] = useState(false)
  // El visor interactiu és la vista principal; l'SVG del servidor continua sent el
  // render de DOCUMENT (paleta fixa, per imprimir i arxivar) i es pot demanar a part.
  const [vista, setVista] = useState('konva')   // 'konva' | 'svg'

  const [exportObert, setExportObert] = useState(false)

  // Els fitxers triats: estat CONTROLAT (les FileDropCard són controlades). Abans eren dos
  // refs a <input type="file">, i el DOM era l'única font de veritat de què havia triat
  // l'usuari: no es podia ni desactivar el botó de Pujar fins que hi hagués DXF.
  const [dxf, setDxf] = useState(null)
  const [rul, setRul] = useState(null)
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

  // ── la geometria (el que el visor Konva dibuixa) ──────────────────────────
  useEffect(() => {
    if (!actual) { setGeometria(null); return }
    let cancelat = false
    setGeoCarregant(true)
    patterns.geometry(actual.id)
      .then(({ data }) => { if (!cancelat) setGeometria(data) })
      .catch(() => { if (!cancelat) setGeometria(null) })
      .finally(() => { if (!cancelat) setGeoCarregant(false) })
    return () => { cancelat = true }
  }, [actual])

  // ── l'SVG de document (només quan es demana) ─────────────────────────────
  // Està gated per Authorization i un <img src> no pot portar capçaleres: es baixa com a
  // blob i es mostra per objectURL. L'objectURL es revoca sempre, o cada canvi de peça
  // deixaria un blob viu a la memòria del navegador.
  useEffect(() => {
    if (!actual || vista !== 'svg') return
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
  }, [actual, pecaSel, vista])

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
      setDxf(null)
      setRul(null)
    }
  }

  const onTriaFitxers = () => {
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
          dxf={dxf} rul={rul} setDxf={setDxf} setRul={setRul} onTria={onTriaFitxers}
        />
      ) : (
        <>
          <Capcalera
            t={t} fp={actual} cadena={cadena}
            onCanviaVersio={id => { setPecaSel(''); carregar(id) }}
            pujant={pujant} dxf={dxf} rul={rul} setDxf={setDxf} setRul={setRul} onTria={onTriaFitxers}
            onExporta={() => setExportObert(true)}
            onTaller={() => navigate(`/models/${modelId}/patro/taller?file=${actual.id}`)}
          />
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <div style={{ flex: '1 1 320px', minWidth: 300,
                          display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <h3 style={{ fontSize: 'var(--fs-h3)', margin: 0 }}>
                {t('pattern.pieces', { n: actual.pieces.length })}
              </h3>
              <PieceList pieces={actual.pieces} pecaSel={pecaSel} onTria={setPecaSel} />
            </div>

            <div style={{ flex: '2 1 460px', minWidth: 340, position: 'relative' }}>
              <CapcaleraVisor
                t={t} vista={vista} onCanviaVista={setVista}
                pecaSel={pecaSel} onTot={() => setPecaSel('')}
              />

              {vista === 'konva' ? (
                geoCarregant || !geometria ? (
                  <CaixaBuida t={t} text={t('pattern.viewer_loading')} />
                ) : (
                  <PatternViewer
                    pieces={geometria.pieces}
                    pecaSel={pecaSel}
                    onTriaPeca={setPecaSel}
                  />
                )
              ) : (
                <Visor
                  t={t} svgUrl={svgUrl} carregant={svgCarregant} pecaSel={pecaSel}
                />
              )}
            </div>
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
            // Cancel·lar la versió nova buida les targetes: els fitxers que hi havia eren per a
            // una pujada que l'usuari acaba de desdir.
            setConfirmarVersio(null)
            setDxf(null)
            setRul(null)
          }}
          onConfirm={() => {
            const { dxf, rul } = confirmarVersio
            setConfirmarVersio(null)
            pujar(dxf, rul, actual.id)
          }}
        />
      )}

      {exportObert && actual && (
        <ExportModal patternFile={actual} onCancel={() => setExportObert(false)} />
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

// Les dues targetes + UN botó de pujar. El DXF és la peça; el RUL, si hi és, l'acompanya —i
// és per això que hi ha un sol botó i no dos: pujar-los per separat mai no ha estat una opció
// (van a la mateixa petició), i dos inputs amb dos botons ho feien semblar.
// El botó està DESACTIVAT sense DXF: abans es podia clicar sempre i no passava res (un `return`
// mut), que és la manera més segura de fer creure a algú que l'aplicació s'ha penjat.
function CampsPujada({ t, pujant, dxf, rul, setDxf, setRul, onTria, compacte = false }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <FileDropCard
          accept={['.dxf']}
          icon="ti-vector-triangle"
          title={t('pattern.file_dxf')}
          required
          file={dxf}
          onFile={setDxf}
          disabled={pujant}
          hint={compacte ? null : t('pattern.max_size', { mb: MAX_MB })}
        />
        <FileDropCard
          accept={['.rul']}
          icon="ti-table"
          title={t('pattern.file_rul')}
          file={rul}
          onFile={setRul}
          disabled={pujant}
        />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <button
          onClick={onTria}
          disabled={pujant || !dxf}
          style={{
            background: 'var(--gold)', color: 'var(--white)', border: 'none',
            borderRadius: 6, padding: '0.5rem 1.1rem',
            cursor: pujant ? 'wait' : (!dxf ? 'not-allowed' : 'pointer'),
            opacity: (!dxf && !pujant) ? 0.45 : 1,
            fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', gap: '0.35rem',
          }}
        >
          <i className={pujant ? 'ti ti-loader' : 'ti ti-upload'} />
          {pujant ? t('pattern.uploading') : t('pattern.upload')}
        </button>
        {!dxf && !pujant && (
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-caption)' }}>
            {t('pattern.need_dxf')}
          </span>
        )}
      </div>
    </div>
  )
}

function ZonaBuida({ t, pujant, dxf, rul, setDxf, setRul, onTria }) {
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
        <CampsPujada t={t} pujant={pujant} dxf={dxf} rul={rul}
                     setDxf={setDxf} setRul={setRul} onTria={onTria} />
      </div>
    </div>
  )
}

function Capcalera({ t, fp, cadena, onCanviaVersio, pujant, dxf, rul, setDxf, setRul, onTria, onExporta, onTaller }) {
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
        {/* L'acció primària de la porta: obrir el patró al TALLER, que és on hi ha les
            eines i on el rellotge de la tasca corre. Aquí només es consulta. */}
        <button
          onClick={onTaller}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.35rem',
            fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--white)',
            border: 'none', borderRadius: 4, background: 'var(--gold)',
            padding: '0.35rem 0.9rem', cursor: 'pointer',
          }}
        >
          <i className="ti ti-tools" />
          {t('pattern.taller.open')}
        </button>

        {fp.download_url && (
          <BotoDescarrega fpId={fp.id} quin="dxf" icona="ti-file-download"
                          text={t('pattern.download_dxf')} t={t} />
        )}
        {fp.te_rul && fp.download_rul_url && (
          <BotoDescarrega fpId={fp.id} quin="rul" icona="ti-table-export"
                          text={t('pattern.download_rul')} t={t} />
        )}

        {/* Exportar la NIADA: no és descarregar el fitxer del client, és generar-ne un de
            nou graduat amb el nostre grading. Per això és un botó d'acció i no un enllaç
            de descàrrega — i per això passa per un gate. */}
        <button
          onClick={onExporta}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.35rem',
            fontSize: 'var(--fs-body)', color: 'var(--white)',
            border: 'none', borderRadius: 4, background: 'var(--text-main)',
            padding: '0.3rem 0.7rem', cursor: 'pointer',
          }}
        >
          <i className="ti ti-arrow-up-right" />
          {t('pattern.exp_button')}
        </button>

        <span style={{ flex: 1 }} />
        <CampsPujada t={t} pujant={pujant} dxf={dxf} rul={rul}
                     setDxf={setDxf} setRul={setRul} onTria={onTria} compacte />
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

// El token es demana AL CLIC, mai al render (W5 · fix D9).
//
// L'URL signada caduca als 15 minuts. Couvar-la amb la pàgina volia dir que qui obria el
// patró i es posava a treballar —el cas normal al Taller, no l'excepció— es trobava, mitja
// hora després, un botó que no descarregava res i cap explicació. El permís no és una
// propietat del fitxer que es pugui pintar i oblidar: té data de caducitat, i es demana quan
// es fa servir. Per això això ja no és un <a href>: és un botó que primer pregunta.
function BotoDescarrega({ fpId, quin, icona, text, t }) {
  const [demanant, setDemanant] = useState(false)
  const [err, setErr] = useState(false)

  const descarrega = async () => {
    setDemanant(true)
    setErr(false)
    try {
      const { data } = await patterns.downloadLinks(fpId)
      const url = quin === 'rul' ? data.download_rul_url : data.download_url
      if (!url) { setErr(true); return }
      window.location.assign(url)   // token acabat de signar: la descàrrega surt al moment
    } catch {
      setErr(true)
    } finally {
      setDemanant(false)
    }
  }

  return (
    <button
      onClick={descarrega}
      disabled={demanant}
      title={err ? t('pattern.err_download_link') : undefined}
      style={{
        display: 'flex', alignItems: 'center', gap: '0.35rem',
        fontSize: 'var(--fs-body)', color: err ? 'var(--err)' : 'var(--text-main)',
        border: `1px solid ${err ? 'var(--err)' : 'var(--border)'}`, borderRadius: 4,
        padding: '0.3rem 0.7rem', background: 'var(--white)',
        cursor: demanant ? 'wait' : 'pointer',
      }}
    >
      <i className={`ti ${demanant ? 'ti-loader' : icona}`} />
      {text}
    </button>
  )
}

function CapcaleraVisor({ t, vista, onCanviaVista, pecaSel, onTot }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem',
      flexWrap: 'wrap',
    }}>
      <h3 style={{ fontSize: 'var(--fs-h3)', margin: 0 }}>
        {vista === 'konva' ? t('pattern.viewer_interactive') : t('pattern.viewer_document')}
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
      <span style={{ flex: 1 }} />
      {/* L'SVG no mor amb el visor: és el render de DOCUMENT (paleta fixa, per imprimir
          i arxivar) i es pot demanar quan es vulgui. */}
      <button
        onClick={() => onCanviaVista(vista === 'konva' ? 'svg' : 'konva')}
        style={{
          background: 'var(--white)', border: '1px solid var(--border)', borderRadius: 4,
          padding: '0.2rem 0.6rem', cursor: 'pointer', fontSize: 'var(--fs-caption)',
          display: 'flex', alignItems: 'center', gap: '0.3rem',
        }}
      >
        <i className={vista === 'konva' ? 'ti ti-file-vector' : 'ti ti-pointer'} />
        {vista === 'konva' ? t('pattern.viewer_switch_svg') : t('pattern.viewer_switch_konva')}
      </button>
    </div>
  )
}

function CaixaBuida({ t, text }) {
  return (
    <div style={{
      border: '1px solid var(--border)', borderRadius: 8, background: 'var(--white)',
      minHeight: 320, display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: 'var(--text-muted)', fontSize: 'var(--fs-body)',
    }}>
      {text}
    </div>
  )
}

function Visor({ t, svgUrl, carregant, pecaSel }) {
  return (
    <div style={{
      border: '1px solid var(--border)', borderRadius: 8, background: 'var(--white)',
      padding: '0.5rem', minHeight: 320,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      {carregant && <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
        {t('pattern.viewer_loading')}
      </span>}
      {!carregant && !svgUrl && <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
        {t('pattern.viewer_error')}
      </span>}
      {!carregant && svgUrl && (
        // El SVG ve del servidor amb la seva paleta de document: NO es re-tinta.
        <img
          src={svgUrl}
          alt={pecaSel || t('pattern.viewer_all')}
          style={{ maxWidth: '100%', maxHeight: 560, objectFit: 'contain' }}
        />
      )}
    </div>
  )
}
