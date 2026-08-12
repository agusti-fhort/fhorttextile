import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { models } from '../../api/endpoints'
import { etiquetaCapa, etiquetaInstancia } from '../../utils/capaInstancia'
import { useEstatDiccionari } from '../../utils/diccionariMesuresFont'
import AvisDiccionari from '../ui/AvisDiccionari'

// LA COMPROVACIÓ (D-31.17 · maqueta_comprovacio_v2) — què falta i què s'ha de mirar abans que
// la fitxa surti cap al fabricant.
//
// CONSULTA PURA, i és la llei de la pantalla: aquí no hi ha cap botó que escrigui. Els enllaços
// porten a la FILA de la taula, que és on es treballa. Comprovar i entrar són dos moments
// diferents, i barrejar-los és el que ha portat problemes.
//
// ORDENADA PEL QUE COSTA MÉS DE DESCOBRIR SOL: un valor que falta el veus a la taula; una mesura
// que va quedar enrere quan la base es va moure, no. Per això les seccions no van per gravetat
// sinó per invisibilitat, i la de famílies —que és lectura, no punts a resoldre— va l'última.
//
// ⚠️ EL BUIT DECLARAT AMB MOTIU NO EXISTEIX ENCARA. La maqueta té files de cara ABSENT amb el
// seu perquè («el coll passa sota l'aixella esquerra») i el domini no les pot desar. Aquesta
// pantalla ensenya les cares que EXISTEIXEN i calla sobre les que no: inventar-hi un buit diria
// que algú s'ha descuidat una mesura que potser la peça no té. El backend ho declara a
// `limitacions` i aquí es diu amb paraules, no s'amaga.

const SECCIONS = [
  { id: 'bloquegen', badge: 'stop' },
  { id: 'enrere', badge: 'warn' },
  { id: 'descartades', badge: 'warn' },
  { id: 'tolerancia', badge: 'warn' },
]
// §1b(d) — la marca de dada taronja és `--warn-state`; `--warn` era el token antic.
const COLOR_BADGE = { stop: 'var(--err)', warn: 'var(--warn-state)', ok: 'var(--ok)' }

// §3 · radi de TARGETA = 12 (`--r-card`). El 9 no és cap dels tres radis del sistema.
const card = {
  background: 'var(--panel)', borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
  borderRadius: 'var(--r-card)', marginBottom: 14, overflow: 'hidden',
}
// §2 · capçalera de llista: th 10px MAJÚSCULES amb tracking .08em «a tot arreu».
const thS = {
  fontSize: 'var(--fs-label)', lineHeight: '12px', textTransform: 'uppercase',
  letterSpacing: '.08em', color: 'var(--text-soft)', fontWeight: 600, textAlign: 'left',
  padding: '8px 10px', whiteSpace: 'nowrap',
}
const tdS = { padding: '7px 10px', borderTopWidth: 1, borderTopStyle: 'solid',
              borderTopColor: 'var(--line-soft)', verticalAlign: 'middle' }
const tdNum = { ...tdS, textAlign: 'right', fontWeight: 500, whiteSpace: 'nowrap',
                fontVariantNumeric: 'tabular-nums' }
const codiS = { color: 'var(--gold)', fontWeight: 600, whiteSpace: 'nowrap' }
const perqueS = { fontSize: 'var(--fs-label)', color: 'var(--text-soft)' }

const xip = (buida) => ({
  background: buida ? 'transparent' : 'var(--sel)',
  color: buida ? 'var(--text-soft)' : 'var(--gold)',
  border: `1px solid ${buida ? 'var(--line)' : 'var(--line)'}`,
  borderRadius: 'var(--r-pill)', padding: '3px 10px', fontSize: 'var(--fs-caption)',
  marginRight: 3, whiteSpace: 'nowrap', display: 'inline-block',
})

const fmt = (n) => (n == null || n === '' ? '—' : String(n).replace('.', ','))
const fmtDia = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// El VEREDICTE DE LA MODISTA amb el color de sempre. És literalment la paleta de `MeasureGrid`
// (`VERDICTE_COL`) i es replica el CRITERI, no el codi: importar-lo faria que aquesta pantalla
// de consulta pura pengés de la graella d'edició. Ha de dir el mateix als dos llocs.
const VERDICTE_COL = { ACCEPTED: 'var(--ok)', ADJUSTED: 'var(--warn-ink)', REJECTED: 'var(--err)' }

// Secció plegable. El capçal és un `button` de debò (no un div amb `role`): la maqueta ja el
// fa focusable amb teclat i aquí surt gratis, amb el seu `aria-expanded`.
function Seccio({ titol, recompte, badge, obert, onGira, children }) {
  return (
    <div style={card}>
      <button type="button" onClick={onGira} aria-expanded={obert}
        style={{
          display: 'flex', alignItems: 'center', gap: 10, width: '100%',
          padding: '11px 16px', background: 'var(--panel)', border: 'none',
          borderBottom: obert ? '1px solid var(--line)' : 'none',
          cursor: 'pointer', font: 'inherit', textAlign: 'left',
        }}>
        <span aria-hidden="true" style={{ width: 8, height: 8, borderRadius: '50%',
                                          flex: 'none', background: COLOR_BADGE[badge] }} />
        <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>{titol}</span>
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)', marginLeft: 'auto' }}>{recompte}</span>
        {/* §8 · ICONES TABLER, mai un caràcter de text: un ▼ tipogràfic no té ni la mida ni el
            traç del sistema, i a 10px no es llegeix com una fletxa. */}
        <i className={`ti ti-chevron-${obert ? 'down' : 'right'}`} aria-hidden="true"
           style={{ fontSize: 16, color: 'var(--text-soft)', lineHeight: 1 }} />
      </button>
      {obert && <div style={{ padding: '4px 16px 14px' }}>{children}</div>}
    </div>
  )
}

function Taula({ columnes, children }) {
  return (
    <table style={{ borderCollapse: 'collapse', width: '100%' }}>
      <thead>
        <tr>{columnes.map((c, i) => (
          <th key={i} style={{ ...thS, ...(c.num ? { textAlign: 'right' } : {}) }}>{c.txt}</th>
        ))}</tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  )
}

// La IDENTITAT de la fila, igual que a la taula de mesures: codi en --gold, nom amb la
// instància DINS i en anglès canònic. Una comprovació que anomenés les files d'una altra
// manera obligaria a tornar a buscar-les a mà.
function Identitat({ p, dicc }) {
  const inst = etiquetaInstancia(p.instancia, dicc)
  return (
    <>
      <td style={tdS}><span style={codiS}>{p.codi}</span></td>
      <td style={tdS}>
        {p.nom}{inst && <span style={{ fontWeight: 500 }}>{` · ${inst}`}</span>}
      </td>
    </>
  )
}

export default function ComprovacioPanel({ model, onVeureFila = null }) {
  const { t, i18n } = useTranslation()
  // L'idioma per als literals del diccionari (les capes en porten tres). F2.2.
  const lang = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)
  // Sense el vocabulari, `Identitat` pinta la germana amb el codi cru (`etiquetaInstancia` fa
  // fallback): els punts de la comprovació segueixen sent correctes, però dues germanes del
  // mateix POM es llegeixen igual. Es demana l'ESTAT, no només el diccionari, per poder-ho DIR.
  const { dicc, error: diccError, reintenta: reintentaDicc } = useEstatDiccionari()
  const [dades, setDades] = useState(null)
  const [error, setError] = useState('')
  const [tancades, setTancades] = useState(() => new Set())

  useEffect(() => {
    let viu = true
    setDades(null); setError('')
    models.comprovacio(model.id)
      .then(r => { if (viu) setDades(r.data) })
      .catch(() => { if (viu) setError(t('comprovacio.error')) })
    return () => { viu = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model.id])

  const gira = (id) => setTancades(prev => {
    const n = new Set(prev)
    if (n.has(id)) n.delete(id); else n.add(id)
    return n
  })

  if (error) {
    return <p style={{ fontSize: 'var(--fs-body)', color: 'var(--err)' }}>{error}</p>
  }
  if (!dades) {
    return <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('common.loading')}</p>
  }

  const { veredicte, seccions, families, limitacions = [],
          darrer_fitting: darrerFitting = null, talla_base } = dades
  const bloqueja = veredicte.bloquegen > 0
  const enllac = (p) => (onVeureFila && p.bm_id != null ? (
    <button type="button" onClick={() => onVeureFila(p)}
      style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer',
               color: 'var(--gold)', fontSize: 'var(--fs-label)', textDecoration: 'underline' }}>
      {t('comprovacio.veure')}
    </button>
  ) : null)

  const cos = {
    bloquegen: (punts) => (
      <Taula columnes={[{ txt: t('comprovacio.col_pom') }, { txt: '' },
                        { txt: t('comprovacio.col_que_passa') }, { txt: '' }]}>
        {punts.map(p => (
          <tr key={`${p.bm_id}-${p.motiu}`}>
            <Identitat p={p} dicc={dicc} />
            <td style={{ ...tdS, ...perqueS }}>{t(`comprovacio.motiu_${p.motiu}`)}</td>
            <td style={{ ...tdS, textAlign: 'right' }}>{enllac(p)}</td>
          </tr>
        ))}
      </Taula>
    ),
    // «Quan» amb paraules i no amb una data: qui llegeix ha de decidir si cal tornar a mesurar,
    // i «fa 9 dies» ho respon; una marca de temps ISO, no.
    enrere: (punts) => (
      <Taula columnes={[{ txt: t('comprovacio.col_pom') }, { txt: '' },
                        { txt: t('comprovacio.col_mesurat'), num: true },
                        { txt: t('comprovacio.col_base_ara'), num: true },
                        { txt: t('comprovacio.col_quan') }]}>
        {punts.map(p => (
          <tr key={p.bm_id}>
            <Identitat p={p} dicc={dicc} />
            <td style={tdNum}>{fmt(p.mesurat)}</td>
            <td style={{ ...tdNum, color: 'var(--err)', fontWeight: 600 }}>{fmt(p.base_ara)}</td>
            <td style={{ ...tdS, ...perqueS }}>{t('comprovacio.enrere_quan', { dies: p.dies })}</td>
          </tr>
        ))}
      </Taula>
    ),
    descartades: (punts) => (
      <Taula columnes={[{ txt: t('comprovacio.col_pom') }, { txt: '' },
                        { txt: t('comprovacio.col_va_arribar'), num: true },
                        { txt: t('comprovacio.col_vigent'), num: true },
                        { txt: t('comprovacio.col_sessio') }]}>
        {punts.map((p, i) => (
          <tr key={`${p.pom_id}-${i}`}>
            <Identitat p={p} dicc={dicc} />
            <td style={{ ...tdNum, textDecoration: 'line-through', color: 'var(--text-soft)' }}>
              {fmt(p.va_arribar)}
            </td>
            <td style={tdNum}>{fmt(p.vigent)}</td>
            <td style={{ ...tdS, ...perqueS }}>{p.sessio}{p.nota ? ` — ${p.nota}` : ''}</td>
          </tr>
        ))}
      </Taula>
    ),
    // D'ON SURTEN AQUESTS NÚMEROS, dit abans de la taula. La secció els citava muts —ni de quin
    // fitting ni de quina talla— i era el primer motiu perquè no «lliguessin» amb res del que
    // es veu a la taula de mesures. El TEÒRIC és el valor contra el qual es va mesurar aquell
    // dia (decisió d'Agus, 10/08), no la base d'ara: sense la data, dir-ho és impossible.
    tolerancia: (punts) => (
      <>
        {darrerFitting && (
          <p style={{ margin: '4px 0 10px', ...perqueS }}>
            {t('comprovacio.tolerancia_font', {
              fase: darrerFitting.fase || '—',
              data: fmtDia(darrerFitting.data),
              talla: talla_base || '—',
            })}
          </p>
        )}
        <Taula columnes={[{ txt: t('comprovacio.col_pom') }, { txt: '' },
                          { txt: t('comprovacio.col_teoric'), num: true },
                          { txt: t('comprovacio.col_real'), num: true },
                          { txt: t('comprovacio.col_desviacio') },
                          { txt: t('comprovacio.col_veredicte') }]}>
          {punts.map(p => (
            <tr key={p.bm_id}>
              <Identitat p={p} dicc={dicc} />
              <td style={tdNum}>{fmt(p.teoric)}</td>
              <td style={tdNum}>{fmt(p.real)}</td>
              <td style={{ ...tdS, ...perqueS }}>
                {p.desviacio > 0 ? '+' : '−'}{fmt(Math.abs(p.desviacio))}
                {' · '}{t('comprovacio.tolerancia_banda', { minus: p.tol_minus, plus: p.tol_plus })}
              </td>
              {/* El veredicte de la modista és DADA DE DOMINI i no es tradueix (D-31.21), com
                  LINEAR/STEP: és el que va cap al fabricant al full imprès. El color és el de
                  sempre (`VERDICTE_COL` de MeasureGrid), perquè el mateix fet es llegeixi
                  igual a les dues superfícies. */}
              <td style={{ ...tdS, ...perqueS, color: VERDICTE_COL[p.veredicte] || 'var(--text-soft)',
                           fontWeight: p.veredicte ? 600 : 400 }}>
                {p.veredicte || '—'}
              </td>
            </tr>
          ))}
        </Taula>
      </>
    ),
  }

  return (
    // LA PANTALLA DECLARA LA SEVA MIDA DE COS (Agus, 10/08: «textos interiors massa grans»).
    // Aquí no hi havia cap mida lliure de més: hi havia una ABSÈNCIA. Les cel·les de les taules
    // —i el rètol de cada secció, que va amb `font: inherit`— no en declaraven cap i queien als
    // 16px del document, o sigui un valor que ningú havia decidit. La vista de Famílies era on
    // més es notava perquè és tot taula. És la mateixa nota que ja porten `KPICard` i el tauler
    // del Dashboard, i el que `MeasureGrid` fa a la seva `<table>`: el contenidor diu el cos i
    // els fills en són excepcions declarades.
    <div style={{ maxWidth: 1060, fontSize: 'var(--fs-body)' }}>
      {diccError && (
        <AvisDiccionari hint={t('dicc.error_hint_noms')} onReintenta={reintentaDicc} />
      )}
      <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 600, margin: '0 0 4px' }}>
        {t('comprovacio.titol')}
      </h2>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)', margin: '0 0 20px' }}>
        {t('comprovacio.subtitol')}
      </p>

      {/* EL VEREDICTE, i el filet de l'esquerra que en porta el color: la primera pregunta de
          qui obre aquesta pantalla és si la fitxa pot sortir o no. */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14, background: 'var(--white)',
        border: '1px solid var(--line)',
        borderLeft: `3px solid ${bloqueja ? 'var(--err)' : 'var(--ok)'}`,
        borderRadius: 9, padding: '15px 18px', marginBottom: 22,
      }}>
        <span aria-hidden="true" style={{ fontSize: 20, lineHeight: 1,
                                          color: bloqueja ? 'var(--err)' : 'var(--ok)' }}>
          {bloqueja ? '⊘' : '✓'}
        </span>
        <div>
          <b style={{ fontSize: 'var(--fs-h3)', display: 'block', marginBottom: 3 }}>
            {t(bloqueja ? 'comprovacio.veredicte_no' : 'comprovacio.veredicte_si')}
          </b>
          <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>
            {t('comprovacio.veredicte_detall', {
              bloquegen: veredicte.bloquegen, revisar: veredicte.a_revisar })}
          </span>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 18, textAlign: 'right' }}>
          {[['bloquegen', veredicte.bloquegen, 'var(--err)'],
            ['a_revisar', veredicte.a_revisar, 'var(--warn)'],
            ['correctes', veredicte.correctes, 'var(--text-main)']].map(([clau, n, col]) => (
            <div key={clau} style={{ fontSize: 'var(--fs-label)', textTransform: 'uppercase',
                                     letterSpacing: '0.05em', color: 'var(--text-soft)' }}>
              {/* L'ÚNICA mida lliure que hi havia: 17px no és cap graó de l'escala
                  (10 · 12 · 14 · 18 · 22 · 32). El recompte del veredicte és la xifra que
                  s'ha de llegir d'un cop d'ull → `--fs-h2`. */}
              <b style={{ display: 'block', fontSize: 'var(--fs-h2)', fontWeight: 600, color: col,
                          marginBottom: 2 }}>{n}</b>
              {t(`comprovacio.compte_${clau}`)}
            </div>
          ))}
        </div>
      </div>

      {SECCIONS.map(({ id, badge }) => {
        const punts = seccions[id] || []
        return (
          <Seccio key={id} badge={punts.length ? badge : 'ok'}
            titol={t(`comprovacio.sec_${id}`)}
            recompte={t('comprovacio.n_punts', { count: punts.length })}
            obert={!tancades.has(id)} onGira={() => gira(id)}>
            {punts.length
              ? cos[id](punts)
              : <p style={{ padding: '12px 10px', fontSize: 'var(--fs-body)',
                            color: 'var(--text-soft)' }}>{t(`comprovacio.buit_${id}`)}</p>}
          </Seccio>
        )
      })}

      {/* LES FAMÍLIES no són punts a resoldre: són la lectura de totes les cares d'una mesura
          juntes, que és l'única manera de veure que a una li falta el que l'altra té. */}
      <Seccio badge="ok" titol={t('comprovacio.sec_families')}
        recompte={t('comprovacio.n_families', { count: families.length })}
        obert={!tancades.has('fam')} onGira={() => gira('fam')}>
        {families.map(f => (
          <div key={f.pom_id} style={{ border: '1px solid var(--line)', borderRadius: 7,
                                       margin: '10px 0', overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '9px 12px',
                          background: 'var(--bg-page)', borderBottom: '1px solid var(--line)' }}>
              <span style={codiS}>{f.codi}</span>
              <span style={{ fontSize: 'var(--fs-body)' }}>{f.nom}</span>
              {f.categoria && (
                <span style={{ fontSize: 'var(--fs-label)', textTransform: 'uppercase',
                               letterSpacing: '0.05em', color: 'var(--text-soft)',
                               border: '1px solid var(--line)', borderRadius: 4,
                               padding: '1px 7px', background: 'var(--white)' }}>{f.categoria}</span>
              )}
              <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-label)', color: 'var(--text-soft)' }}>
                {f.folganca != null
                  ? t('comprovacio.folganca', { n: fmt(f.folganca) })
                  : t('comprovacio.n_cares', { count: f.files.length })}
              </span>
            </div>
            <Taula columnes={[{ txt: t('capa.col') }, { txt: t('comprovacio.col_instancia') },
                              { txt: t('comprovacio.col_talla_base', { talla: model?.base_size_label || '' }), num: true },
                              { txt: t('comprovacio.col_origen') }]}>
              {f.files.map(r => (
                <tr key={r.bm_id} style={{ background: (r.capa !== 'exterior') ? 'var(--fila-capa)' : undefined }}>
                  <td style={tdS}>{etiquetaCapa(r.capa, dicc, lang)}</td>
                  <td style={tdS}>
                    {r.instancia
                      ? <span style={xip(false)}>{etiquetaInstancia(r.instancia, dicc)}</span>
                      : <span style={xip(true)}>—</span>}
                  </td>
                  <td style={{ ...tdNum, ...(r.valor == null
                    ? { color: 'var(--text-soft)', fontStyle: 'italic', fontWeight: 400 } : {}) }}>
                    {r.valor == null ? t('comprovacio.no_informada') : fmt(r.valor)}
                  </td>
                  <td style={{ ...tdS, ...perqueS }}>{r.origen}</td>
                </tr>
              ))}
            </Taula>
          </div>
        ))}
      </Seccio>

      {/* EL QUE AQUESTA PANTALLA ENCARA NO POT DIR, dit aquí i no amagat. Una comprovació que
          calla sobre els seus propis límits convida a llegir-la com a completa. */}
      {limitacions.includes('buit_declarat_amb_motiu') && (
        <p style={{ marginTop: 18, padding: '12px 16px', border: '1px dashed var(--line)',
                    borderRadius: 8, background: 'var(--bg-page)',
                    fontSize: 'var(--fs-label)', color: 'var(--text-soft)', lineHeight: 1.7 }}>
          {t('comprovacio.limitacio_buit_declarat')}
        </p>
      )}
    </div>
  )
}
