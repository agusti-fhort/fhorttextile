import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { poms, pomCategories, customerAliases } from '../../api/endpoints'

// U1 · CATÀLEG DE POMs — mitja i mitja: la llista no perd context i la fitxa té espai per
// dir-ho tot (maqueta_cataleg_poms_v1). Substitueix les dues pestanyes de POM Systems: aquí
// només hi ha catàleg. El `POMBrowser` no desapareix —el consumeixen 5 pantalles més—, però
// deixa de ser una pestanya d'aquesta.
//
// ⚠️ SOBRE ELS «TAGS» DE CAPES I INSTÀNCIES. La casa té `Chip` (botó seleccionable,
// `wizardUI.jsx:25`) i `ReadChip` (caixa etiqueta/valor), i cap dels dos té el contracte d'una
// llista de tags de NOMÉS LECTURA. El `tagBase` de `RunRestrictionTags` sí que el tindria, però
// és privat i el seu fitxer cau dins la frontera dura d'aquest sprint. Aquí es fa marcatge
// LOCAL de pàgina amb tokens —no un component compartit nou, que hauria demanat aturar-se— i
// s'ANOTA al report que un `Tag` compartit és la convergència òbvia de les tres formes.

const cx = {
  wrap: { maxWidth: 1520, margin: '0 auto' },
  split: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 13, alignItems: 'start' },
  box: {
    background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 9, overflow: 'hidden',
  },
  bhead: {
    padding: '10px 14px', background: 'var(--bg-muted)', borderBottom: '1px solid var(--border)',
    display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
  },
  input: {
    flex: 1, minWidth: 150, fontFamily: 'inherit', fontSize: 'var(--fs-label)',
    border: '1px solid var(--border)', borderRadius: 5, padding: '5px 9px',
    background: 'var(--bg-card)', color: 'var(--text-main)',
  },
  list: { maxHeight: 660, overflowY: 'auto' },
  cat: {
    padding: '8px 14px 5px', fontSize: 'var(--fs-caption)', letterSpacing: '.06em',
    textTransform: 'uppercase', color: 'var(--gold)', background: 'var(--bg-muted)',
    borderBottom: '1px solid var(--border)', position: 'sticky', top: 0, zIndex: 2,
  },
  row: {
    padding: '8px 14px', borderBottom: '1px solid var(--border)', cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 10, width: '100%', textAlign: 'left',
    background: 'transparent', border: 'none', borderBottomStyle: 'solid', font: 'inherit',
    color: 'inherit',
  },
  rowOn: { background: 'var(--gold-pale)', boxShadow: 'inset 3px 0 0 var(--gold)' },
  code: { fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--gold)', width: 78, flex: 'none' },
  nm: { fontSize: 'var(--fs-body)', flex: 1, lineHeight: 1.35 },
  loc: { color: 'var(--text-muted)', fontStyle: 'italic', fontSize: 'var(--fs-label)', marginLeft: 7 },
  ab: {
    fontSize: 'var(--fs-caption)', letterSpacing: '.04em', border: '1px solid var(--border)',
    borderRadius: 4, padding: '2px 6px', color: 'var(--text-muted)',
    background: 'var(--bg-card)', flex: 'none',
  },
  sec: { marginTop: 14 },
  secH: {
    fontSize: 'var(--fs-caption)', letterSpacing: '.06em', textTransform: 'uppercase',
    color: 'var(--gold)', paddingBottom: 5, borderBottom: '1px solid var(--border)',
    marginBottom: 9,
  },
  kv: {
    display: 'grid', gridTemplateColumns: '140px 1fr', gap: 8, padding: '3px 0',
    fontSize: 'var(--fs-body)', alignItems: 'baseline',
  },
  k: {
    fontSize: 'var(--fs-caption)', letterSpacing: '.05em', textTransform: 'uppercase',
    color: 'var(--text-muted)',
  },
  buit: { color: 'var(--gray)', fontStyle: 'italic' },
  tag: {
    fontSize: 'var(--fs-label)', border: '1px solid var(--border)', borderRadius: 5,
    padding: '2px 8px', background: 'var(--bg-card)',
  },
  us: { display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 'var(--fs-body)' },
  usN: { fontSize: 'var(--fs-h3)', color: 'var(--gold)', fontWeight: 600 },
  usL: {
    display: 'block', fontSize: 'var(--fs-caption)', letterSpacing: '.05em',
    textTransform: 'uppercase', color: 'var(--text-muted)',
  },
  ffoot: {
    padding: '11px 16px', borderTop: '1px solid var(--border)', background: 'var(--bg-muted)',
    display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
  },
  note: { fontSize: 'var(--fs-label)', color: 'var(--text-muted)', flex: 1, lineHeight: 1.5 },
  badge: {
    fontSize: 'var(--fs-caption)', letterSpacing: '.04em', padding: '2px 8px', borderRadius: 999,
  },
}

const btn = (variant) => ({
  border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--text-main)',
  borderRadius: 6, padding: '6px 12px', fontFamily: 'inherit', fontSize: 'var(--fs-label)',
  cursor: 'pointer', whiteSpace: 'nowrap',
  ...(variant === 'pri' ? { background: 'var(--gold)', borderColor: 'var(--gold)', color: 'var(--white)', fontWeight: 600 } : null),
  ...(variant === 'dang' ? { color: 'var(--err)', borderColor: 'var(--err)' } : null),
})

function Tags({ valors, buit }) {
  if (!valors?.length) return <span style={cx.buit}>{buit}</span>
  return (
    <span style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
      {valors.map(v => <span key={v} style={cx.tag}>{v}</span>)}
    </span>
  )
}

export default function POMCataleg() {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'ca').slice(0, 2)

  const [llista, setLlista] = useState([])
  const [cats, setCats] = useState([])
  const [q, setQ] = useState('')
  const [selId, setSelId] = useState(null)
  const [us, setUs] = useState(null)
  const [alies, setAlies] = useState([])
  const [carregant, setCarregant] = useState(true)
  const [error, setError] = useState(null)
  const [ocupat, setOcupat] = useState(false)

  const carrega = useCallback(() => {
    setCarregant(true); setError(null)
    Promise.all([
      poms.list({ page_size: 1000, ordering: 'codi_client' }),
      pomCategories.list({ page_size: 200 }),
    ])
      .then(([p, c]) => {
        const rows = p.data?.results ?? (Array.isArray(p.data) ? p.data : [])
        setLlista(rows)
        setCats(c.data?.results ?? (Array.isArray(c.data) ? c.data : []))
        setSelId(prev => (prev && rows.some(r => r.id === prev)) ? prev : (rows[0]?.id ?? null))
      })
      .catch(() => setError(t('poms.cat.load_error')))
      .finally(() => setCarregant(false))
  }, [t])

  useEffect(() => { carrega() }, [carrega])

  // L'ús es demana per POM seleccionat: és el que habilita el botó d'esborrar i el que
  // omple les dues seccions d'ús observat. Una crida per fitxa, no per fila de la llista.
  useEffect(() => {
    if (!selId) { setUs(null); setAlies([]); return }
    let viu = true
    setUs(null)
    poms.us(selId).then(r => { if (viu) setUs(r.data) }).catch(() => { if (viu) setUs(null) })
    customerAliases.list({ pom: selId, page_size: 100 })
      .then(r => { if (viu) setAlies(r.data?.results ?? (Array.isArray(r.data) ? r.data : [])) })
      .catch(() => { if (viu) setAlies([]) })
    return () => { viu = false }
  }, [selId])

  const nomCat = useCallback((codi) => {
    const c = cats.find(x => x.codi === codi || x.nom_en === codi || x.nom_ca === codi)
    if (!c) return codi || t('poms.uncategorized')
    return (lang === 'ca' ? c.nom_ca : c.nom_en) || c.nom_ca || c.nom_en || c.codi
  }, [cats, lang, t])

  const filtrats = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return llista
    return llista.filter(p => `${p.codi_client || ''} ${p.nom_client || ''} ${p.pom_code || ''} `
      .concat(`${p.name_en || ''} ${p.name_cat || ''} ${p.categoria || ''}`).toLowerCase().includes(s))
  }, [llista, q])

  // Agrupats per categoria, respectant l'ordre que ja porta la llista.
  const grups = useMemo(() => {
    const out = []
    for (const p of filtrats) {
      const c = p.categoria_nom || p.categoria || ''
      const ult = out[out.length - 1]
      if (!ult || ult.cat !== c) out.push({ cat: c, items: [p] })
      else ult.items.push(p)
    }
    return out
  }, [filtrats])

  const sel = useMemo(() => llista.find(p => p.id === selId) || null, [llista, selId])

  const desactiva = async () => {
    if (!sel) return
    setOcupat(true)
    try { await poms.update(sel.id, { actiu: !sel.actiu }); carrega() }
    catch { setError(t('poms.cat.save_error')) }
    finally { setOcupat(false) }
  }

  const esborra = async () => {
    if (!sel || !us?.pot_esborrar) return
    if (!window.confirm(t('poms.cat.confirm_delete', { codi: sel.codi_client }))) return
    setOcupat(true)
    try { await poms.remove(sel.id); setSelId(null); carrega() }
    catch { setError(t('poms.cat.delete_error')) }
    finally { setOcupat(false) }
  }

  return (
    <div style={cx.wrap}>
      <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 600, margin: '0 0 3px' }}>
        {t('poms.cat.title')}
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-label)', margin: '0 0 14px' }}>
        {t('poms.cat.subtitle')}
      </p>

      {error && (
        <div role="alert" style={{
          marginBottom: 10, padding: '8px 12px', borderRadius: 6,
          border: '1px solid var(--err)', color: 'var(--err)', fontSize: 'var(--fs-label)',
        }}>{error}</div>
      )}

      <div style={cx.split}>
        {/* ── LLISTA ── */}
        <div style={cx.box}>
          <div style={cx.bhead}>
            <input style={cx.input} value={q} onChange={e => setQ(e.target.value)}
                   placeholder={t('poms.cat.search_ph')} aria-label={t('poms.cat.search_ph')} />
            <span style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', whiteSpace: 'nowrap' }}>
              {t('poms.cat.count', { n: filtrats.length })}
            </span>
          </div>
          <div style={cx.list}>
            {carregant && <div style={{ padding: 40, textAlign: 'center', color: 'var(--gray)' }}>
              {t('poms.loading_catalogue')}</div>}
            {!carregant && !filtrats.length && (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--gray)' }}>
                {t('poms.no_match')}</div>
            )}
            {grups.map(g => (
              <div key={g.cat || '—'}>
                <div style={cx.cat}>{nomCat(g.cat)}
                  <span style={{ color: 'var(--gray)', letterSpacing: 0 }}> · {g.items.length}</span>
                </div>
                {g.items.map(p => (
                  <button key={p.id} type="button"
                          onClick={() => setSelId(p.id)}
                          aria-current={p.id === selId ? 'true' : undefined}
                          style={{
                            ...cx.row,
                            ...(p.id === selId ? cx.rowOn : null),
                            opacity: p.actiu ? 1 : 0.5,
                          }}>
                    <span style={cx.code}>{p.pom_code || p.codi_client}</span>
                    <span style={cx.nm}>
                      {p.name_en || p.nom_client}
                      <span style={cx.loc}>{p.name_cat || p.nom_client}</span>
                    </span>
                    {(p.abbreviation || p.codi_client) && (
                      <span style={cx.ab}>{p.abbreviation || p.codi_client}</span>)}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* ── FITXA ── */}
        <div style={cx.box}>
          {!sel && (
            <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--gray)' }}>
              {t('poms.cat.pick_one')}
            </div>
          )}
          {sel && (
            <>
              <div style={{ padding: '13px 16px', borderBottom: '1px solid var(--border)' }}>
                <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', letterSpacing: '.04em' }}>
                  {sel.pom_code || sel.codi_client} · {nomCat(sel.categoria_nom || sel.categoria)}
                </div>
                <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginTop: 3 }}>
                  {sel.name_en || sel.nom_client}</div>
                <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: 2 }}>
                  {sel.name_cat || sel.nom_client}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  <span style={{
                    ...cx.badge,
                    background: sel.actiu ? 'var(--ok-bg)' : 'var(--bg-muted)',
                    color: sel.actiu ? 'var(--ok)' : 'var(--text-muted)',
                  }}>{sel.actiu ? t('poms.cat.badge_active') : t('poms.cat.badge_off')}</span>
                  {us && (
                    <span style={{
                      ...cx.badge,
                      background: us.de_sistema ? 'var(--gold-pale)' : 'var(--bg-muted)',
                      color: us.de_sistema ? 'var(--gold)' : 'var(--text-muted)',
                    }}>{us.de_sistema ? t('poms.cat.badge_system') : t('poms.cat.badge_tenant')}</span>
                  )}
                  {sel.pendent_revisio && (
                    <span style={{ ...cx.badge, background: 'var(--warn-bg)', color: 'var(--warn)' }}>
                      {t('poms.cat.badge_review')}</span>
                  )}
                </div>
              </div>

              <div style={{ padding: '0 16px 14px', maxHeight: 560, overflowY: 'auto' }}>
                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_identity')}</div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_name_en')}</span>
                    <span>{sel.name_en || sel.nom_client}</span></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_name_local')}</span>
                    <span>{sel.name_cat || sel.nom_client}</span></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_nomenclature')}</span>
                    <span>{sel.abbreviation || sel.codi_client}</span></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_family')}</span>
                    <span>{nomCat(sel.categoria_nom || sel.categoria) || <span style={cx.buit}>—</span>}</span></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_unit')}</span>
                    <span>{sel.unitat || <span style={cx.buit}>—</span>}</span></div>
                </section>

                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_howto')}</div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_from')}</span>
                    <span>{sel.start_point || <span style={cx.buit}>—</span>}</span></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_to')}</span>
                    <span>{sel.end_point || <span style={cx.buit}>—</span>}</span></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_reference')}</span>
                    <span>{sel.reference_point || <span style={cx.buit}>—</span>}</span></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_scope')}</span>
                    <span>{[sel.scope, sel.orientation, sel.state, sel.line].filter(Boolean).join(' · ')
                      || <span style={cx.buit}>—</span>}</span></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_body')}</span>
                    <span>{sel.body_section || <span style={cx.buit}>—</span>}</span></div>
                </section>

                {/* 🔑 ÚS OBSERVAT, no política declarada (decisió Agus 07/08). El model no té
                    enlloc «quines capes admet aquest POM»; això és el que es fa servir DE DEBÒ,
                    i el text ho ha de dir amb aquestes paraules. */}
                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_observed')}</div>
                  <p style={{ ...cx.note, margin: '0 0 8px' }}>{t('poms.cat.observed_help')}</p>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_layers')}</span>
                    <Tags valors={us?.observat?.capes} buit={t('poms.cat.observed_none')} /></div>
                  <div style={cx.kv}><span style={cx.k}>{t('poms.cat.f_instances')}</span>
                    <Tags valors={us?.observat?.instancies} buit={t('poms.cat.observed_none')} /></div>
                </section>

                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_aliases')}</div>
                  {!alies.length && <div style={cx.buit}>{t('poms.cat.aliases_none')}</div>}
                  {alies.map(a => (
                    <div key={a.id} style={{
                      display: 'grid', gridTemplateColumns: '96px 1fr', gap: 8, padding: '4px 0',
                      fontSize: 'var(--fs-body)', borderBottom: '1px solid var(--border)',
                    }}>
                      <span style={{ ...cx.k, alignSelf: 'center' }}>{a.customer_codi || a.customer}</span>
                      <span><span style={{ fontWeight: 600, color: 'var(--gold)' }}>{a.client_code}</span>{' '}
                        <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-label)' }}>
                          {a.client_description || ''}</span></span>
                    </div>
                  ))}
                  <p style={{ ...cx.note, marginTop: 8 }}>{t('poms.cat.aliases_readonly')}</p>
                </section>

                <section style={cx.sec}>
                  <div style={cx.secH}>{t('poms.cat.sec_usage')}</div>
                  <div style={cx.us}>
                    <span><b style={cx.usN}>{us?.us?.items ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_items')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.families ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_families')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.grups ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_groups')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.models ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_models')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.rules ?? '—'}</b>
                      <span style={cx.usL}>{t('poms.cat.u_rules')}</span></span>
                  </div>
                  {!!us?.cascada?.length && (
                    <p style={{ ...cx.note, marginTop: 8, color: 'var(--warn)' }}>
                      {t('poms.cat.cascade_warn', {
                        n: us.cascada.reduce((a, f) => a + f.n, 0),
                      })}
                    </p>
                  )}
                </section>
              </div>

              <div style={cx.ffoot}>
                <button type="button" style={btn()} onClick={desactiva} disabled={ocupat}>
                  {sel.actiu ? t('poms.cat.act_deactivate') : t('poms.cat.act_reactivate')}
                </button>
                <button type="button" style={btn('dang')} onClick={esborra}
                        disabled={ocupat || !us || !us.pot_esborrar}>
                  {t('poms.cat.act_delete')}
                </button>
                {/* La nota diu SEMPRE el motiu, la redacta el backend (és qui sap el recompte). */}
                <span style={cx.note}>{us ? us.motiu : t('poms.cat.usage_loading')}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
