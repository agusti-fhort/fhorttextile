import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { patterns } from '../../api/endpoints'

// Modal d'exportació de la niada (S7-T5).
//
// No reutilitza <Modal/>: aquell té l'amplada clavada a 460 px i aquí hi ha d'entrar una
// TAULA (talles × POMs). Es duplica la presentació de l'overlay —que és el que el projecte
// ja fa quan la lògica compartida no és neta— i prou.
//
// LA REGLA D'AQUEST MODAL: el que es veu abans de reconèixer és el que s'exporta. Les
// omissions no es resumeixen en un número ni es guarden darrere d'un desplegable. Un modal
// que amaga que un POM no s'ha graduat converteix el gate en un tràmit — i el gate és
// l'única persona que hi ha entre el nostre motor i una màquina de tallar tela.

const MONO = 'IBM Plex Mono, monospace'

export default function ExportModal({ patternFile, onCancel }) {
  const { t } = useTranslation()

  const [versions, setVersions] = useState([])
  const [versioSel, setVersioSel] = useState('')
  const [perfil, setPerfil] = useState('polypattern')
  const [preview, setPreview] = useState(null)
  const [carregant, setCarregant] = useState(true)
  const [calculant, setCalculant] = useState(false)
  const [error, setError] = useState(null)     // { error, detall? }
  const [reconegut, setReconegut] = useState(false)
  const [baixant, setBaixant] = useState(false)

  // ── Les versions de grading. NOMÉS les aprovades: les serveix així el servidor.
  useEffect(() => {
    let cancelat = false
    patterns.export.gradingVersions(patternFile.id)
      .then(({ data }) => {
        if (cancelat) return
        setVersions(data)
        if (data.length > 0) setVersioSel(String(data[0].id))
      })
      .catch(() => { if (!cancelat) setError({ error: t('pattern.exp_err_versions') }) })
      .finally(() => { if (!cancelat) setCarregant(false) })
    return () => { cancelat = true }
  }, [patternFile.id, t])

  // ── La previsualització. Es refà a cada canvi de versió o de perfil, i **reseteja el
  //    reconeixement**: el que l'usuari va acceptar era l'altra taula, no aquesta.
  const calcular = useCallback(async () => {
    if (!versioSel) return
    setCalculant(true)
    setError(null)
    setPreview(null)
    setReconegut(false)
    try {
      const { data } = await patterns.export.preview(patternFile.id, {
        grading_version_id: Number(versioSel),
        destination_profile: perfil,
      })
      setPreview(data)
    } catch (e) {
      setError(e?.response?.data || { error: t('pattern.exp_err_preview') })
    } finally {
      setCalculant(false)
    }
  }, [patternFile.id, versioSel, perfil, t])

  useEffect(() => { calcular() }, [calcular])

  // ── Els bytes. Dues descàrregues perquè són dos artefactes (DXF + RUL germà), i el
  //    navegador no en pot baixar dos d'una sola resposta.
  const descarregar = async () => {
    setBaixant(true)
    setError(null)
    const cos = {
      grading_version_id: Number(versioSel),
      destination_profile: perfil,
      acknowledged: true,
      texts_shown: preview.text_gate,
    }
    try {
      const dxf = await patterns.export.dxf(patternFile.id, cos)
      baixarBlob(dxf.data, nomNiada(patternFile.nom_fitxer, 'dxf'))
      const rul = await patterns.export.rul(patternFile.id, cos)
      baixarBlob(rul.data, nomNiada(patternFile.nom_fitxer, 'rul'))
      onCancel()
    } catch (e) {
      setError(await comErrorJson(e) || { error: t('pattern.exp_err_download') })
    } finally {
      setBaixant(false)
    }
  }

  const potExportar = Boolean(
    preview && preview.autovalidacio?.ok && reconegut && !baixant && !calculant,
  )

  return (
    <div onClick={onCancel} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--white)', borderRadius: 12, padding: 22,
        width: 900, maxWidth: '95vw', maxHeight: '88vh', overflowY: 'auto',
      }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>
          {t('pattern.exp_title')}
        </h2>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>
          {t('pattern.exp_subtitle')}
        </p>

        {carregant && <p style={{ fontSize: 'var(--fs-body)' }}>{t('pattern.loading')}</p>}

        {!carregant && versions.length === 0 && (
          <Avis to="warn">{t('pattern.exp_no_approved')}</Avis>
        )}

        {!carregant && versions.length > 0 && (
          <>
            {/* ── Els dos selectors ─────────────────────────────────────── */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
              <Camp etiqueta={t('pattern.exp_grading_version')}>
                <select
                  value={versioSel}
                  onChange={e => setVersioSel(e.target.value)}
                  style={inputStyle}
                >
                  {versions.map(v => (
                    <option key={v.id} value={v.id}>
                      {v.nom} · {new Date(v.data).toLocaleDateString()} · {v.specs} specs
                    </option>
                  ))}
                </select>
                <small style={{ color: 'var(--gray)', fontSize: '0.75rem' }}>
                  {t('pattern.exp_only_approved')}
                </small>
              </Camp>

              <Camp etiqueta={t('pattern.exp_profile')}>
                <select
                  value={perfil}
                  onChange={e => setPerfil(e.target.value)}
                  style={inputStyle}
                >
                  <option value="polypattern">PolyPattern</option>
                  {/* Deshabilitats AMB EL MOTIU: no tenim cap fitxer real d'aquests CAD per
                      derivar-ne l'empremta, i inventar-se-la donaria un round-trip verd
                      contra un format que no hem vist mai. */}
                  <option value="tuka" disabled>Tuka — {t('pattern.exp_profile_na')}</option>
                  <option value="gerber" disabled>Gerber — {t('pattern.exp_profile_na')}</option>
                  <option value="clo" disabled>CLO — {t('pattern.exp_profile_na')}</option>
                </select>
              </Camp>
            </div>

            {calculant && <p style={{ fontSize: 'var(--fs-body)' }}>{t('pattern.exp_computing')}</p>}

            {error && (
              <Avis to="err">
                <strong>{error.error}</strong>
                {error.detall?.diferencies?.length > 0 && (
                  <ul style={{ margin: '8px 0 0 18px', fontSize: '0.8rem' }}>
                    {error.detall.diferencies.slice(0, 8).map((d, i) => <li key={i}>{d}</li>)}
                  </ul>
                )}
              </Avis>
            )}

            {preview && (
              <>
                <TaulaPreview preview={preview} t={t} />
                <Omissions preview={preview} t={t} />
                <Autovalidacio auto={preview.autovalidacio} t={t} />

                {/* ── EL GATE ───────────────────────────────────────────── */}
                <label style={{
                  display: 'flex', gap: 10, alignItems: 'flex-start', marginTop: 16,
                  padding: 12, border: '1px solid var(--border)', borderRadius: 6,
                  background: 'var(--bg-soft, #fafafa)', cursor: 'pointer',
                }}>
                  <input
                    type="checkbox"
                    checked={reconegut}
                    disabled={!preview.autovalidacio?.ok}
                    onChange={e => setReconegut(e.target.checked)}
                    style={{ marginTop: 3 }}
                  />
                  <span style={{ fontSize: 'var(--fs-body)', lineHeight: 1.45 }}>
                    {preview.text_gate}
                  </span>
                </label>
              </>
            )}
          </>
        )}

        {/* ── Peu ───────────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
          <button onClick={onCancel} style={btnGhost}>{t('app.cancel')}</button>
          <button onClick={descarregar} disabled={!potExportar} style={{
            ...btnPrimary,
            opacity: potExportar ? 1 : 0.45,
            cursor: potExportar ? 'pointer' : 'not-allowed',
          }}>
            <i className="ti ti-file-download" style={{ marginRight: 6 }} />
            {baixant ? t('pattern.exp_downloading') : t('pattern.exp_download')}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── La taula: una fila per talla, una columna per POM ────────────────────────
function TaulaPreview({ preview, t }) {
  const codis = preview.talles[0]?.poms.map(p => p.pom_code) || []

  return (
    <div style={{ overflowX: 'auto', marginBottom: 14 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr>
            <th style={thStyle}>{t('pattern.exp_size')}</th>
            {codis.map(c => <th key={c} style={thStyle}>{c}</th>)}
            <th style={thStyle}>{t('pattern.exp_sew')}</th>
          </tr>
        </thead>
        <tbody>
          {preview.talles.map(sp => (
            <tr key={sp.talla}>
              <td style={{ ...tdStyle, fontWeight: sp.es_base ? 600 : 400, fontFamily: MONO }}>
                {sp.talla}
                {sp.es_base && (
                  <small style={{ color: 'var(--gray)', marginLeft: 6 }}>
                    {t('pattern.exp_base')}
                  </small>
                )}
              </td>

              {sp.poms.map(p => (
                <td key={p.pom_code} style={tdStyle}>
                  {p.valor_cm === null ? '—' : (
                    <>
                      <span style={{ fontFamily: MONO }}>{p.valor_cm.toFixed(2)}</span>
                      {p.delta_spec_cm === null ? (
                        // Ancorat però sense grading: no es mou. Es diu, no es dissimula.
                        <small style={{ color: 'var(--warn, #b26a00)', display: 'block' }}>
                          {t('pattern.exp_no_grading')}
                        </small>
                      ) : (
                        <small style={{
                          display: 'block',
                          color: p.ok ? 'var(--gray)' : 'var(--danger, #c0392b)',
                        }}>
                          {p.delta_spec_cm >= 0 ? '+' : ''}{p.delta_spec_cm.toFixed(2)}
                          {!p.ok && ` ⚠ ${p.desviament_cm?.toFixed(2)}`}
                        </small>
                      )}
                    </>
                  )}
                </td>
              ))}

              <td style={tdStyle}>
                {sp.costures.length === 0 ? '—' : sp.costures.map(s => (
                  <span
                    key={s.sew_id}
                    title={s.missatge}
                    style={{
                      display: 'inline-block', marginRight: 6,
                      color: s.casa ? 'var(--ok, #2e7d32)' : 'var(--danger, #c0392b)',
                    }}
                  >
                    <i className={`ti ${s.casa ? 'ti-check' : 'ti-alert-triangle'}`} />
                    {' '}#{s.sew_id}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <small style={{ color: 'var(--gray)', fontSize: '0.72rem' }}>
        {t('pattern.exp_table_hint')}
      </small>
    </div>
  )
}

// ── El que NO ha entrat a la niada. Sempre visible. ──────────────────────────
function Omissions({ preview, t }) {
  const total = preview.omissions.length + preview.problemes_poms.length
  if (total === 0) return null

  const senseSpec = preview.omissions.filter(o => o.codi === 'pom_sense_spec')
  const senseAncora = preview.omissions.filter(o => o.codi === 'spec_sense_pom')
  const forats = preview.omissions.filter(o => o.codi === 'cella_buida')

  return (
    <Avis to="warn">
      <strong>{t('pattern.exp_omissions')} ({total})</strong>
      <ul style={{ margin: '8px 0 0 18px', fontSize: '0.8rem', lineHeight: 1.5 }}>
        {senseSpec.map(o => (
          <li key={`s-${o.pom_code}`}>
            <strong>{o.pom_code}</strong> — {t('pattern.exp_om_no_spec')}
          </li>
        ))}
        {forats.map((o, i) => (
          <li key={`f-${i}`}><strong>{o.pom_code}</strong> — {o.missatge}</li>
        ))}
        {preview.problemes_poms.map((p, i) => <li key={`p-${i}`}>{p}</li>)}
        {senseAncora.length > 0 && (
          <li>
            {t('pattern.exp_om_no_anchor', { count: senseAncora.length })}
            {' '}
            <span style={{ color: 'var(--gray)', fontFamily: MONO }}>
              {senseAncora.map(o => o.pom_code).join(', ')}
            </span>
          </li>
        )}
      </ul>
    </Avis>
  )
}

// ── La porta. Si és vermella, no hi ha bytes. ────────────────────────────────
function Autovalidacio({ auto, t }) {
  if (!auto) return null
  return (
    <Avis to={auto.ok ? 'ok' : 'err'}>
      <strong>{t('pattern.exp_selfcheck')}</strong>
      <div style={{ fontSize: '0.8rem', marginTop: 4 }}>{auto.resum}</div>
      {!auto.ok && (
        <div style={{ fontSize: '0.8rem', marginTop: 6 }}>{t('pattern.exp_selfcheck_blocked')}</div>
      )}
    </Avis>
  )
}

// ── Bocins ───────────────────────────────────────────────────────────────────
function Camp({ etiqueta, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 260, flex: 1 }}>
      <label style={{ fontSize: '0.78rem', color: 'var(--gray)' }}>{etiqueta}</label>
      {children}
    </div>
  )
}

const COLORS = {
  ok: { bg: '#f1f8f2', border: '#2e7d32' },
  warn: { bg: '#fff8e6', border: '#b26a00' },
  err: { bg: '#fdf1f0', border: '#c0392b' },
}

function Avis({ to = 'warn', children }) {
  const c = COLORS[to] || COLORS.warn
  return (
    <div style={{
      background: c.bg, borderLeft: `3px solid ${c.border}`,
      padding: '10px 12px', borderRadius: 4, marginBottom: 12,
      fontSize: 'var(--fs-body)',
    }}>
      {children}
    </div>
  )
}

const inputStyle = {
  border: '1px solid var(--border)', borderRadius: 4,
  padding: '0.4rem 0.6rem', fontSize: 'var(--fs-body)', background: 'var(--white)',
}
const thStyle = {
  textAlign: 'left', padding: '6px 8px', borderBottom: '2px solid var(--border)',
  fontWeight: 500, color: 'var(--gray)', whiteSpace: 'nowrap',
}
const tdStyle = {
  padding: '6px 8px', borderBottom: '1px solid var(--border)', verticalAlign: 'top',
}
const btnGhost = {
  border: '1px solid var(--border)', borderRadius: 4, background: 'var(--white)',
  padding: '0.45rem 1rem', fontSize: 'var(--fs-body)', cursor: 'pointer',
}
const btnPrimary = {
  border: 'none', borderRadius: 4, background: 'var(--text-main)', color: 'var(--white)',
  padding: '0.45rem 1.1rem', fontSize: 'var(--fs-body)',
}

function nomNiada(nom, ext) {
  const base = (nom || 'patro').replace(/\.[^.]+$/, '')
  return `${base}_niada.${ext}`
}

function baixarBlob(blob, nom) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nom
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// Un 403/422 amb `responseType: 'blob'` arriba com a Blob, no com a JSON: si no es
// desembolica, l'usuari veu «[object Blob]» en comptes del motiu.
async function comErrorJson(e) {
  const dades = e?.response?.data
  if (!dades) return null
  if (dades instanceof Blob) {
    try { return JSON.parse(await dades.text()) } catch { return null }
  }
  return dades
}
