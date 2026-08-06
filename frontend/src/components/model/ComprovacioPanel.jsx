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
const COLOR_BADGE = { stop: 'var(--err)', warn: 'var(--warn)', ok: 'var(--ok)' }

const card = {
  background: 'var(--white)', border: '1px solid var(--border)', borderRadius: 9,
  marginBottom: 14, overflow: 'hidden',
}
const thS = {
  fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '0.05em',
  color: 'var(--text-muted)', fontWeight: 500, textAlign: 'left',
  padding: '9px 10px 7px', whiteSpace: 'nowrap',
}
const tdS = { padding: '8px 10px', borderTop: '1px solid var(--border)', verticalAlign: 'middle' }
const tdNum = { ...tdS, textAlign: 'right', fontWeight: 500, whiteSpace: 'nowrap',
                fontVariantNumeric: 'tabular-nums' }
const codiS = { color: 'var(--gold)', fontWeight: 600, whiteSpace: 'nowrap' }
const perqueS = { fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }

const xip = (buida) => ({
  background: buida ? 'transparent' : 'var(--gold-pale)',
  color: buida ? 'var(--text-muted)' : 'var(--gold)',
  border: `1px solid ${buida ? 'var(--border)' : 'var(--border)'}`,
  borderRadius: 999, padding: '2px 8px', fontSize: 'var(--fs-label)',
  marginRight: 3, whiteSpace: 'nowrap', display: 'inline-block',
})

const fmt = (n) => (n == null || n === '' ? '—' : String(n).replace('.', ','))

// Secció plegable. El capçal és un `button` de debò (no un div amb `role`): la maqueta ja el
// fa focusable amb teclat i aquí surt gratis, amb el seu `aria-expanded`.
function Seccio({ titol, recompte, badge, obert, onGira, children }) {
  return (
    <div style={card}>
      <button type="button" onClick={onGira} aria-expanded={obert}
        style={{
          display: 'flex', alignItems: 'center', gap: 10, width: '100%',
          padding: '11px 16px', background: 'var(--bg-muted)', border: 'none',
          borderBottom: obert ? '1px solid var(--border)' : 'none',
          cursor: 'pointer', font: 'inherit', textAlign: 'left',
        }}>
        <span aria-hidden="true" style={{ width: 8, height: 8, borderRadius: '50%',
                                          flex: 'none', background: COLOR_BADGE[badge] }} />
        <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>{titol}</span>
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginLeft: 'auto' }}>{recompte}</span>
        <span aria-hidden="true" style={{ color: 'var(--text-muted)', fontSize: 10,
                                          transform: obert ? 'none' : 'rotate(-90deg)' }}>▼</span>
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
  const { t } = useTranslation()
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
    return <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('common.loading')}</p>
  }

  const { veredicte, seccions, families, limitacions = [] } = dades
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
            <td style={{ ...tdNum, textDecoration: 'line-through', color: 'var(--text-muted)' }}>
              {fmt(p.va_arribar)}
            </td>
            <td style={tdNum}>{fmt(p.vigent)}</td>
            <td style={{ ...tdS, ...perqueS }}>{p.sessio}{p.nota ? ` — ${p.nota}` : ''}</td>
          </tr>
        ))}
      </Taula>
    ),
    tolerancia: (punts) => (
      <Taula columnes={[{ txt: t('comprovacio.col_pom') }, { txt: '' },
                        { txt: t('comprovacio.col_teoric'), num: true },
                        { txt: t('comprovacio.col_real'), num: true },
                        { txt: t('comprovacio.col_desviacio') }]}>
        {punts.map(p => (
          <tr key={p.bm_id}>
            <Identitat p={p} dicc={dicc} />
            <td style={tdNum}>{fmt(p.teoric)}</td>
            <td style={tdNum}>{fmt(p.real)}</td>
            <td style={{ ...tdS, ...perqueS }}>
              {p.desviacio > 0 ? '+' : '−'}{fmt(Math.abs(p.desviacio))}
              {' · '}{t('comprovacio.tolerancia_banda', { minus: p.tol_minus, plus: p.tol_plus })}
            </td>
          </tr>
        ))}
      </Taula>
    ),
  }

  return (
    <div style={{ maxWidth: 1060 }}>
      {diccError && (
        <AvisDiccionari hint={t('dicc.error_hint_noms')} onReintenta={reintentaDicc} />
      )}
      <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 600, margin: '0 0 4px' }}>
        {t('comprovacio.titol')}
      </h2>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', margin: '0 0 20px' }}>
        {t('comprovacio.subtitol')}
      </p>

      {/* EL VEREDICTE, i el filet de l'esquerra que en porta el color: la primera pregunta de
          qui obre aquesta pantalla és si la fitxa pot sortir o no. */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14, background: 'var(--white)',
        border: '1px solid var(--border)',
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
          <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
            {t('comprovacio.veredicte_detall', {
              bloquegen: veredicte.bloquegen, revisar: veredicte.a_revisar })}
          </span>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 18, textAlign: 'right' }}>
          {[['bloquegen', veredicte.bloquegen, 'var(--err)'],
            ['a_revisar', veredicte.a_revisar, 'var(--warn)'],
            ['correctes', veredicte.correctes, 'var(--text-main)']].map(([clau, n, col]) => (
            <div key={clau} style={{ fontSize: 'var(--fs-label)', textTransform: 'uppercase',
                                     letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
              <b style={{ display: 'block', fontSize: 17, fontWeight: 600, color: col,
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
                            color: 'var(--text-muted)' }}>{t(`comprovacio.buit_${id}`)}</p>}
          </Seccio>
        )
      })}

      {/* LES FAMÍLIES no són punts a resoldre: són la lectura de totes les cares d'una mesura
          juntes, que és l'única manera de veure que a una li falta el que l'altra té. */}
      <Seccio badge="ok" titol={t('comprovacio.sec_families')}
        recompte={t('comprovacio.n_families', { count: families.length })}
        obert={!tancades.has('fam')} onGira={() => gira('fam')}>
        {families.map(f => (
          <div key={f.pom_id} style={{ border: '1px solid var(--border)', borderRadius: 7,
                                       margin: '10px 0', overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '9px 12px',
                          background: 'var(--bg-card)', borderBottom: '1px solid var(--border)' }}>
              <span style={codiS}>{f.codi}</span>
              <span style={{ fontSize: 'var(--fs-body)' }}>{f.nom}</span>
              {f.categoria && (
                <span style={{ fontSize: 'var(--fs-label)', textTransform: 'uppercase',
                               letterSpacing: '0.05em', color: 'var(--text-muted)',
                               border: '1px solid var(--border)', borderRadius: 4,
                               padding: '1px 7px', background: 'var(--white)' }}>{f.categoria}</span>
              )}
              <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
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
                  <td style={tdS}>{etiquetaCapa(r.capa, t)}</td>
                  <td style={tdS}>
                    {r.instancia
                      ? <span style={xip(false)}>{etiquetaInstancia(r.instancia, dicc)}</span>
                      : <span style={xip(true)}>—</span>}
                  </td>
                  <td style={{ ...tdNum, ...(r.valor == null
                    ? { color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 400 } : {}) }}>
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
        <p style={{ marginTop: 18, padding: '12px 16px', border: '1px dashed var(--border)',
                    borderRadius: 8, background: 'var(--bg-card)',
                    fontSize: 'var(--fs-label)', color: 'var(--text-muted)', lineHeight: 1.7 }}>
          {t('comprovacio.limitacio_buit_declarat')}
        </p>
      )}
    </div>
  )
}
