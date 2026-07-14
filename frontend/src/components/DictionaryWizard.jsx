import { useState } from 'react'
import { customerDictionary, poms } from '../api/endpoints'
import Badge from './ui/Badge'
import { primaryBtn, selS } from './ui/buttons'
import FileDropCard from './ui/FileDropCard'
import { overlayBase } from './ui/overlay'

// Wizard de revisió del diccionari de nomenclatura del client (setup, un sol cop).
// Pas 1: descarregar plantilla + pujar l'Excel omplert → preview (proposta per fila).
// Pas 2: revisar la taula (POM proposat + badge de confiança + match manual + crear POM nou
// SENSE gate + deixar sense resoldre) i desar. El servidor no re-resol: desa el confirmat.
const MONO = 'IBM Plex Mono, monospace'
const CONF_VARIANT = { HIGH: 'ok', MEDIUM: 'gold', LOW: 'warn', NO_MATCH: 'gray' }

const th = {
  padding: '0.6rem 0.8rem', fontSize: 'var(--fs-label)', letterSpacing: '0.08em',
  textTransform: 'uppercase', color: 'var(--gray)', fontWeight: 400, textAlign: 'left',
  borderBottom: '0.5px solid var(--gray-l)', whiteSpace: 'nowrap',
}
const td = { padding: '0.6rem 0.8rem', fontSize: 'var(--fs-body)', verticalAlign: 'top', borderBottom: '0.5px solid var(--gray-l)' }
const miniBtn = {
  background: 'var(--white)', border: '0.5px solid var(--border)', borderRadius: 6, cursor: 'pointer',
  padding: '3px 8px', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 'var(--fs-label)',
}

export default function DictionaryWizard({ customer, t, onClose, onDone }) {
  const [step, setStep] = useState('upload')
  const [fitxer, setFitxer] = useState(null)
  const [rows, setRows] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [conflicts, setConflicts] = useState(null)

  const downloadTemplate = async () => {
    try {
      const res = await customerDictionary.template(customer.id)
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url; a.download = `diccionari_${customer.codi}.xlsx`; a.click()
      URL.revokeObjectURL(url)
    } catch { setError(t('dictionary.err_template')) }
  }

  // El fitxer es TRIA (targeta) i després s'ANALITZA (botó): dos passos, com al tab Patró.
  // Abans, triar-lo disparava la pujada de cop des de l'onChange de l'input: no hi havia manera
  // de veure què havies triat, ni de canviar d'idea, ni de treure'l.
  const analitza = async (file) => {
    if (!file) return
    setBusy(true); setError('')
    try {
      const fd = new FormData(); fd.append('file', file)
      const res = await customerDictionary.preview(customer.id, fd)
      const prev = res.data?.rows || []
      // Estat editable inicial: si hi ha proposta → 'link'; si no → 'skip' (sense resoldre).
      setRows(prev.map(r => ({
        ...r,
        action: r.proposal ? 'link' : 'skip',
        pom_master_id: r.proposal?.pom_master_id ?? null,
        chosen: r.proposal ? { codi: r.proposal.codi_global || r.proposal.codi_client, nom: r.proposal.nom_en } : null,
        acknowledge_manual: false,
        searching: false, searchQ: '', searchResults: [],
      })))
      setStep('review')
    } catch (err) {
      setError(err?.response?.data?.error || t('dictionary.err_preview'))
    } finally { setBusy(false) }
  }

  const patch = (i, p) => setRows(prev => prev.map((r, idx) => idx === i ? { ...r, ...p } : r))

  const doSearch = (i, q) => {
    patch(i, { searchQ: q })
    if (!q.trim()) { patch(i, { searchResults: [] }); return }
    poms.list({ search: q.trim(), page_size: 15 })
      .then(res => patch(i, { searchResults: res.data?.results ?? (Array.isArray(res.data) ? res.data : []) }))
      .catch(() => patch(i, { searchResults: [] }))
  }

  const pickPom = (i, pm) => patch(i, {
    action: 'link', pom_master_id: pm.id,
    chosen: { codi: pm.codi_client, nom: pm.nom_client },
    searching: false, searchQ: '', searchResults: [],
  })

  const counts = {
    total: rows.length,
    resolved: rows.filter(r => r.action === 'link' && r.pom_master_id).length,
    created: rows.filter(r => r.action === 'create').length,
    unresolved: rows.filter(r => r.action === 'skip').length,
  }

  const save = async (ackAll = false) => {
    setSaving(true); setError(''); setConflicts(null)
    const payload = {
      rows: rows.map(r => ({
        row_num: r.row_num, codi_client: r.codi_client,
        descripcio_en: r.descripcio_en, descripcio_local: r.descripcio_local, idioma: r.idioma,
        action: r.action,
        pom_master_id: r.action === 'link' ? r.pom_master_id : undefined,
        acknowledge_manual: ackAll || r.acknowledge_manual || false,
      })),
    }
    try {
      const res = await customerDictionary.commit(customer.id, payload)
      onDone(res.data)
    } catch (err) {
      if (err?.response?.status === 409 && err.response.data?.manual_conflicts) {
        setConflicts(err.response.data.manual_conflicts)
      } else {
        setError(err?.response?.data?.error || t('dictionary.err_commit'))
      }
    } finally { setSaving(false) }
  }

  return (
    <div style={overlayBase({ alignItems: 'flex-start', overflowY: 'auto', padding: '3vh 0' })}
      onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ background: 'var(--white)', borderRadius: 12, width: 'min(1100px, 94vw)', boxShadow: '0 10px 40px rgba(0,0,0,0.18)', overflow: 'hidden' }}>
        {/* Capçalera */}
        <div style={{ padding: '1rem 1.25rem', borderBottom: '0.5px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 'var(--fs-h2)', fontWeight: 500, fontFamily: MONO }}>{t('dictionary.title')}</h2>
            <p style={{ margin: '2px 0 0', fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>
              <span style={{ fontFamily: MONO, fontWeight: 600 }}>{customer.codi}</span> · {customer.nom}
            </p>
          </div>
          <button onClick={onClose} style={{ ...miniBtn, fontSize: 'var(--fs-h3)', padding: '2px 10px' }}>×</button>
        </div>

        {error && <div style={{ margin: '12px 1.25rem 0', padding: '8px 12px', borderRadius: 6, background: 'var(--err-bg)', color: 'var(--err)', fontSize: 'var(--fs-body)' }}>{error}</div>}

        {step === 'upload' && (
          <div style={{ padding: '1.5rem 1.25rem' }}>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginTop: 0 }}>{t('dictionary.upload_help')}</p>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
              <FileDropCard
                accept={['.xlsx', '.xls']}
                icon="ti-file-spreadsheet"
                title={t('dictionary.upload')}
                required
                file={fitxer}
                onFile={setFitxer}
                disabled={busy}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingTop: 4 }}>
                <button onClick={downloadTemplate} style={miniBtn}>
                  <i className="ti ti-download" style={{ fontSize: 13, marginRight: 5 }} />{t('dictionary.download_template')}
                </button>
                <button
                  onClick={() => analitza(fitxer)}
                  disabled={busy || !fitxer}
                  style={{
                    ...primaryBtn, marginLeft: 0,
                    opacity: (!fitxer && !busy) ? 0.45 : 1,
                    cursor: busy ? 'wait' : (!fitxer ? 'not-allowed' : 'pointer'),
                  }}
                >
                  <i className={busy ? 'ti ti-loader' : 'ti ti-upload'} style={{ fontSize: 14 }} />
                  {busy ? t('dictionary.reading') : t('dictionary.upload')}
                </button>
              </div>
            </div>
          </div>
        )}

        {step === 'review' && (
          <div>
            {/* Comptadors */}
            <div style={{ padding: '10px 1.25rem', display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 'var(--fs-body)', color: 'var(--text-muted)', borderBottom: '0.5px solid var(--gray-l)' }}>
              <span>{t('dictionary.count_total', { count: counts.total })}</span>
              <span><Badge variant="ok">{counts.resolved}</Badge> {t('dictionary.count_resolved')}</span>
              <span><Badge variant="gold">{counts.created}</Badge> {t('dictionary.count_created')}</span>
              <span><Badge variant="gray">{counts.unresolved}</Badge> {t('dictionary.count_unresolved')}</span>
            </div>

            {conflicts && (
              <div style={{ margin: '12px 1.25rem 0', padding: '10px 12px', borderRadius: 8, background: 'var(--warn-bg)', color: 'var(--warn)', fontSize: 'var(--fs-body)' }}>
                <div style={{ marginBottom: 6 }}>{t('dictionary.manual_conflict', { count: conflicts.length })}</div>
                <button onClick={() => save(true)} style={{ ...miniBtn, borderColor: 'var(--warn)', color: 'var(--warn)' }}>{t('dictionary.confirm_overwrite')}</button>
              </div>
            )}

            <div style={{ maxHeight: '55vh', overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead style={{ position: 'sticky', top: 0, background: 'var(--white)' }}>
                  <tr>
                    <th style={th}>{t('dictionary.col_code')}</th>
                    <th style={th}>{t('dictionary.col_desc')}</th>
                    <th style={th}>{t('dictionary.col_pom')}</th>
                    <th style={th}>{t('dictionary.col_conf')}</th>
                    <th style={th}></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => {
                    const flag = r.diff || r.n_match > 1
                    return (
                      <tr key={r.row_num} style={{ background: flag ? 'var(--warn-bg)' : 'transparent' }}>
                        <td style={{ ...td, fontFamily: MONO, fontWeight: 600 }}>{r.codi_client}</td>
                        <td style={td}>
                          <div>{r.descripcio_en || <span style={{ color: 'var(--text-muted)' }}>—</span>}</div>
                          {r.descripcio_local && <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
                            {r.idioma && <span style={{ fontFamily: MONO, marginRight: 4 }}>[{r.idioma}]</span>}{r.descripcio_local}
                          </div>}
                        </td>
                        <td style={td}>
                          {r.action === 'create' ? (
                            <Badge variant="gold">{t('dictionary.new_pom')}</Badge>
                          ) : r.action === 'skip' ? (
                            <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>{t('dictionary.unresolved')}</span>
                          ) : r.chosen ? (
                            <div style={{ lineHeight: 1.2 }}>
                              <div style={{ fontFamily: MONO, fontWeight: 600, color: 'var(--gold)' }}>{r.chosen.codi}</div>
                              <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>{r.chosen.nom}</div>
                            </div>
                          ) : '—'}
                          {r.n_match > 1 && <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--warn)', marginTop: 2 }}>{t('dictionary.ambiguous', { count: r.n_match })}</div>}
                          {r.existing && r.diff && <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--warn)', marginTop: 2 }}>
                            {t('dictionary.diff_existing')}{r.preserve_manual && ` · ${t('dictionary.was_manual')}`}
                          </div>}
                          {r.searching && (
                            <div style={{ marginTop: 6 }}>
                              <input autoFocus value={r.searchQ} onChange={e => doSearch(i, e.target.value)}
                                placeholder={t('dictionary.search_pom')} style={{ ...selS, width: 220 }} />
                              {r.searchResults.length > 0 && (
                                <ul style={{ listStyle: 'none', padding: 0, margin: '4px 0 0', maxHeight: 140, overflowY: 'auto', border: '0.5px solid var(--gray-l)', borderRadius: 6 }}>
                                  {r.searchResults.map(pm => (
                                    <li key={pm.id}>
                                      <button onClick={() => pickPom(i, pm)} style={{ width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer', padding: '5px 8px', fontSize: 'var(--fs-body)', borderBottom: '0.5px solid var(--border)' }}>
                                        <span style={{ fontFamily: MONO, fontWeight: 600 }}>{pm.codi_client}</span> · {pm.nom_client}
                                      </button>
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          )}
                        </td>
                        <td style={td}>
                          <Badge variant={CONF_VARIANT[r.confidence] || 'gray'}>{r.confidence}</Badge>
                        </td>
                        <td style={{ ...td, whiteSpace: 'nowrap', textAlign: 'right' }}>
                          <button onClick={() => patch(i, { searching: !r.searching })} style={miniBtn} title={t('dictionary.manual_match')}>
                            <i className="ti ti-search" style={{ fontSize: 13 }} />
                          </button>{' '}
                          <button onClick={() => patch(i, { action: 'create', searching: false })} style={miniBtn} title={t('dictionary.create_pom')}>
                            <i className="ti ti-plus" style={{ fontSize: 13 }} />
                          </button>{' '}
                          <button onClick={() => patch(i, { action: 'skip', searching: false })} style={miniBtn} title={t('dictionary.leave_unresolved')}>
                            <i className="ti ti-minus" style={{ fontSize: 13 }} />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Peu: desar sense restriccions dures */}
            <div style={{ padding: '1rem 1.25rem', borderTop: '0.5px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button onClick={onClose} style={miniBtn}>{t('dictionary.cancel')}</button>
              <button onClick={() => save(false)} disabled={saving} style={{ ...primaryBtn, marginLeft: 0, opacity: saving ? 0.6 : 1 }}>
                <i className="ti ti-device-floppy" style={{ fontSize: 14 }} />{saving ? t('dictionary.saving') : t('dictionary.save')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
