import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { sizeSystems } from '../../api/endpoints'
import { useEixos } from '../grading/eixosFont'
import { useGarmentGroups } from '../grading/garmentCatalog'

// A2 · SIZE LIBRARY — la llista de RUNS i la seva fitxa (maqueta_size_library_v3).
//
// MATEIX PATRÓ QUE EL CATÀLEG DE POMs, i literalment: llista a l'esquerra, fitxa a la dreta,
// mateixes seccions, mateix peu d'accions, mateixos tokens. La maqueta ho demana amb aquestes
// paraules («un sol llenguatge per a tota la Configuració tècnica») i és el que fa que les dues
// pantalles s'aprenguin una sola vegada.
//
// ⚠️ AIXÒ SUBSTITUEIX EL SELECTOR DE PRESETS, que és el que hi havia a `/size-library`. La
// maqueta és explícita: «els presets amb graduació dins han desaparegut. Un run és una escala;
// els increments de POM viuen als jocs de regles. Aquí no hi ha ni un delta». El component vell
// (`SizingProfileSelector`) NO s'esborra —v. el report— però deixa d'estar muntat aquí.
//
// ⚠️ FORA EL BADGE «CANÒNIC DE LA CASA». `SizeSystem` NO té `is_system` ni cap flag de
// canonicitat (camps reals: codi, nom, descripcio, actiu, base_unit, norma_ref, parent,
// customer_codi, tipus_escala, customer). L'única cosa derivable de la dada és **si té client o
// no**, i això és el que la fitxa diu ara: «RUN DE <CLIENT>» o «SENSE CLIENT». Amb el badge cau
// la protecció d'esborrat per «canònic»: no tenia camp on recolzar-se, i ara el gate és
// NOMÉS L'ÚS, que el backend calcula i explica.
//
// ⚠️ LA MULTI-SELECCIÓ ES QUEDA, I ÉS CORRECTA. A `SizeSystem` les quatre capes són M2M
// (`targets`, `construccions`, `fits`, `grups`) i el serializer les emet i les accepta com a
// llistes de CODIS. La cardinalitat d'un sol valor és de `GradingRuleSet`, no d'aquí.

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
  cerca: {
    flex: 1, minWidth: 220, alignSelf: 'center', fontFamily: 'inherit', fontSize: 'var(--fs-body)',
    border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)', padding: '8px 12px',
    background: 'var(--panel)', color: 'var(--text-main)',
  },
  list: { maxHeight: 660, overflowY: 'auto' },
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
  code: { fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--gold)', width: 128, flex: 'none' },
  nm: { fontSize: 'var(--fs-body)', flex: 1, lineHeight: 1.35 },
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
  badge: {
    fontSize: 'var(--fs-label)', lineHeight: '12px', fontWeight: 600, letterSpacing: '.04em',
    padding: '3px 10px', borderRadius: 'var(--r-pill)',
  },
}

const btn = (variant) => ({
  border: '1px solid var(--gold-border)', background: 'var(--panel)', color: 'var(--text-main)',
  borderRadius: 'var(--r-ctrl)', padding: '8px 16px', fontFamily: 'inherit',
  fontSize: 'var(--fs-body)', fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap',
  ...(variant === 'ter' ? { borderColor: 'transparent', background: 'none', color: 'var(--text-soft)' } : null),
  ...(variant === 'dang' ? { color: 'var(--err)', borderColor: 'var(--err)' } : null),
})

// LES TALLES, AMB EL SEU ORDRE EXPLÍCIT (1, 2, 3…). Decisió heretada de la v1 i vigent: «un run
// desordenat és un grading incorrecte; si es veu, no torna a passar». El número no és decoració:
// és el camp `ordre`, que és el que el motor llegeix.
function Talles({ talles, buit }) {
  if (!talles?.length) return <span style={cx.buit}>{buit}</span>
  return (
    <span style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
      {[...talles].sort((a, b) => (a.ordre ?? 0) - (b.ordre ?? 0)).map(s => (
        <span key={s.id ?? s.etiqueta} style={{ ...cx.ab, display: 'inline-flex', gap: 5 }}>
          <span style={{ color: 'var(--text-faint)' }}>{s.ordre}</span>
          <b style={{ color: 'var(--text-main)', fontWeight: 600 }}>{s.etiqueta}</b>
        </span>
      ))}
    </span>
  )
}

/**
 * Una capa de restricció: multi-selecció sobre un vocabulari.
 *
 * ⚠️ **BUIT = «NO DECLARAT», NO «SERVEIX A TOTHOM».** És el que el backend té escrit
 * (`pom/models.py`, el comentari de les quatre capes: «buit NO vol dir universal»), i la maqueta
 * v3.1 el va corregir per aquest motiu. La diferència importa: «serveix a tothom» convida a
 * deixar-ho buit; «no declarat» diu que hi falta una decisió.
 */
function Capa({ titol, vocabulari, triats, onToggle, editable, t }) {
  const sel = new Set(triats || [])
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ ...cx.k, marginBottom: 5 }}>{titol}</div>
      {!vocabulari && <div style={cx.buit}>{t('size_library.vocab_loading')}</div>}
      {!!vocabulari?.length && (
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          {vocabulari.map(v => {
            const on = sel.has(v.codi)
            return (
              <button key={v.codi} type="button" disabled={!editable}
                      onClick={() => onToggle(v.codi)} aria-pressed={on}
                      style={{
                        ...cx.ab, cursor: editable ? 'pointer' : 'default', font: 'inherit',
                        fontSize: 'var(--fs-label)',
                        ...(on ? { background: 'var(--sel)', borderColor: 'var(--gold-border)',
                                   color: 'var(--text-main)', fontWeight: 600 } : null),
                      }}>{v.etiqueta}</button>
            )
          })}
        </div>
      )}
      {!sel.size && !!vocabulari?.length && (
        <div style={{ ...cx.buit, marginTop: 5 }}>{t('size_library.layer_undeclared')}</div>
      )}
    </div>
  )
}

export default function RunsCataleg({ onNou }) {
  const { t } = useTranslation()
  const [runs, setRuns] = useState([])
  const [q, setQ] = useState('')
  const [nomesActius, setNomesActius] = useState(true)
  const [selId, setSelId] = useState(null)
  const [us, setUs] = useState(null)
  const [carregant, setCarregant] = useState(true)
  const [error, setError] = useState(null)
  const [ocupat, setOcupat] = useState(false)

  // Els vocabularis de les quatre capes, de la BD. Cap llista escrita aquí (F2.2).
  const { targets, constructions, fits } = useEixos()
  const grups = useGarmentGroups()

  const carrega = useCallback(() => {
    setCarregant(true); setError(null)
    // Segueix la paginació fins al final: el comptador ha de dir el total REAL.
    const totes = async () => {
      const out = []
      let page = 1
      for (;;) {
        const r = await sizeSystems.list({ page_size: 200, page })
        const d = r.data
        out.push(...(d?.results ?? (Array.isArray(d) ? d : [])))
        if (d?.next) page++
        else return out
      }
    }
    totes()
      .then(rows => {
        setRuns(rows)
        setSelId(prev => (prev && rows.some(r => r.id === prev)) ? prev : (rows[0]?.id ?? null))
      })
      .catch(() => setError(t('size_library.load_error')))
      .finally(() => setCarregant(false))
  }, [t])

  useEffect(() => { carrega() }, [carrega])

  // L'ús es demana per run seleccionat: és el que habilita o bloqueja «Esborrar» i el que omple
  // la secció «On s'usa». Una crida per fitxa, no per fila de la llista.
  useEffect(() => {
    if (!selId) { setUs(null); return }
    let viu = true
    setUs(null)
    sizeSystems.us(selId).then(r => { if (viu) setUs(r.data) }).catch(() => { if (viu) setUs(null) })
    return () => { viu = false }
  }, [selId])

  const filtrats = useMemo(() => {
    const s = q.trim().toLowerCase()
    return runs
      .filter(r => (nomesActius ? r.actiu !== false : r.actiu === false))
      .filter(r => !s || `${r.codi || ''} ${r.nom || ''} ${r.customer_codi || ''}`.toLowerCase().includes(s))
  }, [runs, q, nomesActius])

  // Agrupats pel TIPUS D'ESCALA, que és el que separa els runs entre ells. Buit = no deduït.
  const grups_llista = useMemo(() => {
    const per = new Map()
    for (const r of filtrats) {
      const k = r.tipus_escala || ''
      if (!per.has(k)) per.set(k, [])
      per.get(k).push(r)
    }
    return [...per.entries()].sort((a, b) => String(a[0]).localeCompare(String(b[0])))
      .map(([esc, items]) => ({ esc, items }))
  }, [filtrats])

  const sel = useMemo(() => runs.find(r => r.id === selId) || null, [runs, selId])

  const vocabularis = useMemo(() => ({
    target: targets?.map(x => ({ codi: x.codi, etiqueta: x.nom_en })) ?? null,
    construccio: constructions?.map(x => ({ codi: x.codi, etiqueta: x.nom_en })) ?? null,
    fit: fits?.map(x => ({ codi: x.codi, etiqueta: x.nom_en })) ?? null,
    grup: grups?.length ? grups.map(x => ({ codi: x.codi, etiqueta: x.nom_en })) : null,
  }), [targets, constructions, fits, grups])

  const desa = async (patch) => {
    if (!sel) return
    setOcupat(true); setError(null)
    try {
      const { data } = await sizeSystems.update(sel.id, patch)
      setRuns(rs => rs.map(r => (r.id === sel.id ? { ...r, ...data } : r)))
    } catch (e) {
      // El backend valida `tipus_escala` contra les etiquetes i pot rebutjar amb un motiu que
      // la persona ha de llegir tal qual: no s'aixafa amb un text genèric.
      const d = e?.response?.data
      setError(typeof d === 'string' ? d
        : Object.values(d || {}).flat().join(' · ') || t('size_library.save_error'))
    } finally { setOcupat(false) }
  }

  const commutaCapa = (camp, codi) => {
    const actual = sel?.[camp] || []
    const nou = actual.includes(codi) ? actual.filter(c => c !== codi) : [...actual, codi]
    desa({ [camp]: nou })
  }

  const esborra = async () => {
    if (!sel || !us?.pot_esborrar) return
    if (!window.confirm(t('size_library.confirm_delete', { codi: sel.codi }))) return
    setOcupat(true)
    try { await sizeSystems.remove(sel.id); setSelId(null); carrega() }
    catch { setError(t('size_library.delete_error')) }
    finally { setOcupat(false) }
  }

  const editable = true   // l'escriptura la gated el backend (CONFIGURE); aquí no es duplica

  return (
    <div style={cx.wrap}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, padding: '16px 0 12px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 600, color: 'var(--text-main)' }}>
          {filtrats.length}
          <small style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, color: 'var(--text-soft)' }}>
            /{runs.length}</small>
        </span>
        <span style={{ fontSize: 'var(--fs-label)', letterSpacing: '.08em', textTransform: 'uppercase',
                       color: 'var(--text-soft)', fontWeight: 600 }}>{t('size_library.runs')}</span>
        <input style={cx.cerca} value={q} onChange={e => setQ(e.target.value)}
               placeholder={t('size_library.search_ph')} aria-label={t('size_library.search_ph')} />
        <span style={{ flexBasis: '100%', fontSize: 'var(--fs-body)', color: 'var(--text-soft)', marginTop: 2 }}>
          {t('size_library.subtitle_runs')}
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
            {[true, false].map(v => (
              <button key={String(v)} type="button" onClick={() => setNomesActius(v)}
                      aria-pressed={nomesActius === v}
                      style={{ ...cx.ab, cursor: 'pointer', font: 'inherit', fontSize: 'var(--fs-label)',
                               ...(nomesActius === v ? { background: 'var(--sel)',
                                 borderColor: 'var(--gold-border)', fontWeight: 600 } : null) }}>
                {v ? t('size_library.tab_active') : t('size_library.tab_off')}
              </button>
            ))}
            <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-label)', color: 'var(--text-faint)' }}>
              {t('size_library.count', { n: filtrats.length })}
            </span>
            <button type="button" style={btn()} onClick={onNou}>{t('size_library.new_run')}</button>
          </div>
          <div style={cx.list}>
            {carregant && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-faint)', fontStyle: 'italic' }}>
              {t('size_library.loading')}</div>}
            {!carregant && !filtrats.length && (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-faint)', fontStyle: 'italic' }}>
                {t('size_library.no_match')}</div>
            )}
            {grups_llista.map(g => (
              <div key={g.esc || 'sense'}>
                <div style={cx.cat}>{g.esc || t('size_library.scale_unknown')}
                  <span style={{ color: 'var(--text-faint)', letterSpacing: 0 }}> · {g.items.length}</span>
                </div>
                {g.items.map(r => (
                  <button key={r.id} type="button" onClick={() => setSelId(r.id)}
                          aria-current={r.id === selId ? 'true' : undefined}
                          style={{ ...cx.row, ...(r.id === selId ? cx.rowOn : null),
                                   opacity: r.actiu === false ? 0.5 : 1 }}>
                    <span style={cx.code}>{r.codi}</span>
                    <span style={cx.nm}>{r.nom}</span>
                    <span style={cx.ab}>{t('size_library.n_sizes', { n: r.talles?.length ?? 0 })}</span>
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
              {t('size_library.pick_one')}
            </div>
          )}
          {sel && (
            <>
              <div style={{ padding: '16px', borderBottom: '1px solid var(--line)' }}>
                <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-faint)', letterSpacing: '.04em' }}>
                  {sel.codi}
                </div>
                <div style={{ fontSize: 'var(--fs-h3)', lineHeight: '20px', fontWeight: 600, marginTop: 4 }}>
                  {sel.nom}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  <span style={{
                    ...cx.badge,
                    background: sel.actiu !== false ? 'var(--ok-bg)' : 'var(--bg-page)',
                    color: sel.actiu !== false ? 'var(--ok)' : 'var(--text-soft)',
                    border: `1px solid ${sel.actiu !== false ? 'var(--ok)' : 'var(--line)'}`,
                  }}>{sel.actiu !== false ? t('size_library.badge_active') : t('size_library.badge_off')}</span>
                  {/* ⚠️ NO és «canònic»: és si té client. `SizeSystem` no té cap flag de
                      canonicitat, i el badge que hi havia a la maqueta v3 s'hi recolzava. */}
                  <span style={{ ...cx.badge, background: 'var(--bg-page)', color: 'var(--text-main)',
                                 border: '1px solid var(--line)' }}>
                    {us?.te_client
                      ? t('size_library.badge_of_client', { client: us.client })
                      : t('size_library.badge_no_client')}
                  </span>
                  {/* L'ÀNCORA, en taronja viu: és el que el cens directe no veu. */}
                  {!!us?.us?.regles_ancorades && (
                    <span style={{ ...cx.badge, background: 'var(--warn-state-bg)', color: 'var(--warn-ink)',
                                   border: '1px solid var(--warn-state)' }}>
                      {t('size_library.badge_anchor', { n: us.us.regles_ancorades })}</span>
                  )}
                </div>
              </div>

              <div style={{ padding: '0 16px 14px', maxHeight: 560, overflowY: 'auto' }}>
                <section style={cx.sec}>
                  <div style={cx.secH}>{t('size_library.sec_scale')}</div>
                  {/* EL TIPUS D'ESCALA ES MOSTRA, NO S'EDITA A MÀ: el dedueix el sistema de les
                      etiquetes, i el backend rebutja qualsevol valor que les contradigui
                      (`validate_tipus_escala`). Aquí es llegeix. */}
                  <div style={cx.kv}><span style={cx.k}>{t('size_library.f_scale_type')}</span>
                    <span>{sel.tipus_escala || <span style={cx.buit}>{t('size_library.scale_unknown')}</span>}</span></div>
                  <div style={cx.kv}><span style={cx.k}>{t('size_library.f_sizes')}</span>
                    <Talles talles={sel.talles} buit={t('size_library.no_sizes')} /></div>
                </section>

                <section style={cx.sec}>
                  <div style={cx.secH}>{t('size_library.sec_restrictions')}</div>
                  <p style={{ ...cx.note, margin: '0 0 10px' }}>{t('size_library.restrictions_help')}</p>
                  <Capa titol={t('size_library.layer_target')} vocabulari={vocabularis.target}
                        triats={sel.target_codis} editable={editable} t={t}
                        onToggle={c => commutaCapa('target_codis', c)} />
                  <Capa titol={t('size_library.layer_construction')} vocabulari={vocabularis.construccio}
                        triats={sel.construccio_codis} editable={editable} t={t}
                        onToggle={c => commutaCapa('construccio_codis', c)} />
                  <Capa titol={t('size_library.layer_fit')} vocabulari={vocabularis.fit}
                        triats={sel.fit_codis} editable={editable} t={t}
                        onToggle={c => commutaCapa('fit_codis', c)} />
                  <Capa titol={t('size_library.layer_group')} vocabulari={vocabularis.grup}
                        triats={sel.grup_codis} editable={editable} t={t}
                        onToggle={c => commutaCapa('grup_codis', c)} />
                </section>

                <section style={cx.sec}>
                  <div style={cx.secH}>{t('size_library.sec_usage')}</div>
                  <div style={cx.us}>
                    <span><b style={cx.usN}>{us?.us?.jocs_de_regles ?? '·'}</b>
                      <span style={cx.usL}>{t('size_library.u_rulesets')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.models ?? '·'}</b>
                      <span style={cx.usL}>{t('size_library.u_models')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.items_base ?? '·'}</b>
                      <span style={cx.usL}>{t('size_library.u_base_sets')}</span></span>
                    <span><b style={cx.usN}>{us?.us?.perfils ?? '·'}</b>
                      <span style={cx.usL}>{t('size_library.u_profiles')}</span></span>
                    {/* 🔴 LA XIFRA QUE EL CENS DIRECTE NO VEU. Una regla no apunta al run: apunta
                        a una TALLA del run. Un run amb «0 usos» pot ser l'àncora de centenars de
                        regles — va passar amb TGIRL-EU-HEIGHT (350 regles de deu jocs). */}
                    <span><b style={{ ...cx.usN, color: us?.us?.regles_ancorades ? 'var(--warn-ink)' : 'var(--gold)' }}>
                      {us?.us?.regles_ancorades ?? '·'}</b>
                      <span style={cx.usL}>{t('size_library.u_anchored')}</span></span>
                  </div>
                  <p style={{ ...cx.note, marginTop: 8 }}>{t('size_library.anchored_help')}</p>
                </section>
              </div>

              <div style={cx.ffoot}>
                <button type="button" style={btn('ter')} disabled={ocupat}
                        onClick={() => desa({ actiu: sel.actiu === false })}>
                  {sel.actiu !== false ? t('size_library.act_deactivate') : t('size_library.act_reactivate')}
                </button>
                <button type="button" style={btn('dang')} onClick={esborra}
                        disabled={ocupat || !us || !us.pot_esborrar}>
                  {t('size_library.act_delete')}
                </button>
                {/* La nota diu SEMPRE el motiu, i la redacta el backend: és qui sap el recompte. */}
                <span style={cx.note}>{us ? us.motiu : t('size_library.usage_loading')}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
