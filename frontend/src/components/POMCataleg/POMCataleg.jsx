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

// PELL NORMA_LAYOUT v1 (A1). L'estructura —mitja i mitja, seccions de la fitxa, peu d'accions—
// no es toca: ve de la maqueta v1 ja aprovada. El que canvia és el vestit, i tot són tokens:
//   --bg-card/--bg-muted → --panel (§1: «--white: TOT panell, targeta i capçalera»; les
//     capçaleres de panell i el peu deixen de ser crema) · --border → --line · --gold-pale →
//     --sel + filet d'or (§1: el crema ja no marca selecció) · --gray → --text-faint ·
//     --text-muted → --text-soft · radis 4/5/9 → --r-ctrl i --r-card · píndoles a --r-pill.
// Mides: capçaleres de secció i de categoria a 10px (§2, mínim absolut) via --fs-label, que és
// el rol correcte —van en MAJÚSCULES amb tracking—; --fs-caption queda per al text menor.
const cx = {
  wrap: { maxWidth: 1520, margin: '0 auto' },
  split: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'start' },
  box: {
    background: 'var(--panel)', border: '1px solid var(--line)',
    borderRadius: 'var(--r-card)', overflow: 'hidden',
  },
  bhead: {
    padding: '12px 16px', background: 'var(--panel)', borderBottom: '1px solid var(--line)',
    display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
  },
  input: {
    flex: 1, minWidth: 150, fontFamily: 'inherit', fontSize: 'var(--fs-body)',
    border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)', padding: '8px 12px',
    background: 'var(--panel)', color: 'var(--text-main)',
  },
  list: { maxHeight: 660, overflowY: 'auto' },
  // §8e: capçalera de llista = th 10px MAJÚSCULES tracking .08em «a tot arreu (també llistes
  // <div>)». Deixa de ser daurada: el daurat és marca i selecció, no rètol de columna.
  cat: {
    padding: '8px 16px 6px', fontSize: 'var(--fs-label)', lineHeight: '12px',
    letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-soft)',
    fontWeight: 600, background: 'var(--panel)',
    borderBottom: '1px solid var(--line-soft)', position: 'sticky', top: 0, zIndex: 2,
  },
  row: {
    padding: '8px 16px', borderBottom: '1px solid var(--line-soft)', cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 12, width: '100%', textAlign: 'left',
    background: 'transparent', border: 'none', borderBottomStyle: 'solid', font: 'inherit',
    color: 'inherit',
  },
  rowOn: { background: 'var(--sel)', boxShadow: 'inset 3px 0 0 var(--gold)' },
  code: { fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--gold)', width: 78, flex: 'none' },
  nm: { fontSize: 'var(--fs-body)', flex: 1, lineHeight: 1.35 },
  loc: { color: 'var(--text-soft)', fontStyle: 'italic', fontSize: 'var(--fs-label)', marginLeft: 8 },
  ab: {
    fontSize: 'var(--fs-label)', letterSpacing: '.04em', border: '1px solid var(--line)',
    borderRadius: 'var(--r-pill)', padding: '2px 8px', color: 'var(--text-soft)',
    background: 'var(--panel)', flex: 'none',
  },
  sec: { marginTop: 16 },
  secH: {
    fontSize: 'var(--fs-label)', lineHeight: '12px', letterSpacing: '.08em',
    textTransform: 'uppercase', color: 'var(--gold)', fontWeight: 600, paddingBottom: 6,
    borderBottom: '1px solid var(--line-soft)', marginBottom: 10,
  },
  kv: {
    display: 'grid', gridTemplateColumns: '132px 1fr', gap: 8, padding: '4px 0',
    fontSize: 'var(--fs-body)', alignItems: 'baseline',
  },
  k: {
    fontSize: 'var(--fs-label)', letterSpacing: '.05em', textTransform: 'uppercase',
    color: 'var(--text-soft)',
  },
  buit: { color: 'var(--text-faint)', fontStyle: 'italic' },
  tag: {
    fontSize: 'var(--fs-label)', border: '1px solid var(--line)', borderRadius: 'var(--r-pill)',
    padding: '3px 10px', background: 'var(--panel)',
  },
  us: { display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 'var(--fs-body)' },
  usN: { fontSize: 'var(--fs-h3)', color: 'var(--gold)', fontWeight: 600 },
  usL: {
    display: 'block', fontSize: 'var(--fs-label)', letterSpacing: '.05em',
    textTransform: 'uppercase', color: 'var(--text-soft)',
  },
  ffoot: {
    padding: '12px 16px', borderTop: '1px solid var(--line)', background: 'var(--panel)',
    display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
  },
  note: { fontSize: 'var(--fs-label)', color: 'var(--text-soft)', flex: 1, lineHeight: 1.5 },
  // §1 (esmena Agus 08/08): TOT badge d'estat és fons suau + tinta del color + VORA FINA DEL
  // MATEIX COLOR, sense excepció. Abans n'hi havia que anaven sense filet.
  badge: {
    fontSize: 'var(--fs-label)', lineHeight: '12px', fontWeight: 600, letterSpacing: '.04em',
    padding: '3px 10px', borderRadius: 'var(--r-pill)',
  },
}

// §5 · jerarquia d'acció. Aquesta pantalla és de CONSULTA i, ara mateix, no té cap acció
// primària: «Desactivar» és terciària (reversible, de servei) i «Esborrar» és destructiva amb
// vora. Per això no hi ha cap blau — §8c ho preveu: «pantalles de CONSULTA poden tenir ZERO
// accions primàries». El daurat ple que feia de `pri` desapareix: el daurat ja no és acció.
const btn = (variant) => ({
  border: '1px solid var(--gold-border)', background: 'var(--panel)', color: 'var(--text-main)',
  borderRadius: 'var(--r-ctrl)', padding: '8px 16px', fontFamily: 'inherit',
  fontSize: 'var(--fs-body)', fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap',
  ...(variant === 'ter' ? { borderColor: 'transparent', background: 'none', color: 'var(--text-soft)' } : null),
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
      {/* §8b.3 · IDENTITAT sobre el fons, sense contenidor: comptador + etiqueta + descripció.
          El comptador és SELECCIÓ, no KPI (§8e): el primer valor segueix el filtre de cerca i
          el total va menor i suau. Substitueix el títol h2 que hi havia: el nom de l'entitat
          deixa de ser títol i passa a ser element al costat del número. */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, padding: '16px 0 12px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 600, color: 'var(--text-main)' }}>
          {filtrats.length}
          <small style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-soft)' }}>
            /{llista.length}</small>
        </span>
        <span style={{ fontSize: 'var(--fs-label)', letterSpacing: '.08em', textTransform: 'uppercase',
                       color: 'var(--text-soft)', fontWeight: 600 }}>{t('poms.cat.title')}</span>
        <span style={{ flexBasis: '100%', fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginTop: 2 }}>
          {t('poms.cat.subtitle')}
        </span>
      </div>

      {error && (
        <div role="alert" style={{
          marginBottom: 12, padding: '8px 12px', borderRadius: 'var(--r-ctrl)',
          border: '1px solid var(--err)', background: 'var(--err-bg)', color: 'var(--err)',
          fontSize: 'var(--fs-body)',
        }}>{error}</div>
      )}

      <div style={cx.split}>
        {/* ── LLISTA ── */}
        <div style={cx.box}>
          <div style={cx.bhead}>
            <input style={cx.input} value={q} onChange={e => setQ(e.target.value)}
                   placeholder={t('poms.cat.search_ph')} aria-label={t('poms.cat.search_ph')} />
            <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-faint)', whiteSpace: 'nowrap' }}>
              {t('poms.cat.count', { n: filtrats.length })}
            </span>
          </div>
          <div style={cx.list}>
            {carregant && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-faint)', fontStyle: 'italic' }}>
              {t('poms.loading_catalogue')}</div>}
            {!carregant && !filtrats.length && (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-faint)', fontStyle: 'italic' }}>
                {t('poms.no_match')}</div>
            )}
            {grups.map(g => (
              <div key={g.cat || '—'}>
                <div style={cx.cat}>{nomCat(g.cat)}
                  <span style={{ color: 'var(--text-faint)', letterSpacing: 0 }}> · {g.items.length}</span>
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
            <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-faint)', fontStyle: 'italic' }}>
              {t('poms.cat.pick_one')}
            </div>
          )}
          {sel && (
            <>
              <div style={{ padding: '16px', borderBottom: '1px solid var(--line)' }}>
                <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-faint)', letterSpacing: '.04em' }}>
                  {sel.pom_code || sel.codi_client} · {nomCat(sel.categoria_nom || sel.categoria)}
                </div>
                <div style={{ fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600, marginTop: 4 }}>
                  {sel.name_en || sel.nom_client}</div>
                <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', fontStyle: 'italic', marginTop: 2 }}>
                  {sel.name_cat || sel.nom_client}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  <span style={{
                    ...cx.badge,
                    background: sel.actiu ? 'var(--ok-bg)' : 'var(--bg-page)',
                    color: sel.actiu ? 'var(--ok)' : 'var(--text-soft)',
                    border: `1px solid ${sel.actiu ? 'var(--ok)' : 'var(--line)'}`,
                  }}>{sel.actiu ? t('poms.cat.badge_active') : t('poms.cat.badge_off')}</span>
                  {us && (
                    <span style={{
                      ...cx.badge,
                      background: us.de_sistema ? 'var(--sel)' : 'var(--bg-page)',
                      color: 'var(--text-main)',
                      border: `1px solid ${us.de_sistema ? 'var(--gold-border)' : 'var(--line)'}`,
                    }}>{us.de_sistema ? t('poms.cat.badge_system') : t('poms.cat.badge_tenant')}</span>
                  )}
                  {sel.pendent_revisio && (
                    <span style={{ ...cx.badge, background: 'var(--warn-state-bg)', color: 'var(--warn-ink)',
                      border: '1px solid var(--warn-state)' }}>
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
                      fontSize: 'var(--fs-body)', borderBottom: '1px solid var(--line-soft)',
                    }}>
                      <span style={{ ...cx.k, alignSelf: 'center' }}>{a.customer_codi || a.customer}</span>
                      <span><span style={{ fontWeight: 600, color: 'var(--gold)' }}>{a.client_code}</span>{' '}
                        <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-label)' }}>
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
                    <p style={{ ...cx.note, marginTop: 8, color: 'var(--warn-ink)' }}>
                      {t('poms.cat.cascade_warn', {
                        n: us.cascada.reduce((a, f) => a + f.n, 0),
                      })}
                    </p>
                  )}
                </section>
              </div>

              <div style={cx.ffoot}>
                <button type="button" style={btn('ter')} onClick={desactiva} disabled={ocupat}>
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
