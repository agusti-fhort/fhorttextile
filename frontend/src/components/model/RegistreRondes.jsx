import { Fragment, useState } from 'react'
import { useTranslation } from 'react-i18next'

import Badge from '../ui/Badge'
import { formatMinutes, formatDataHora, formatDataCurta, localeDeIdioma } from '../../utils/format'
import { agrupaPerRonda, RONDA_ENTREGADA, RONDA_TANCADA } from '../../utils/rondes'

// M2 · MOCKUP B v3 — EL REGISTRE D'ACTIVITAT, EN UNA SOLA GRAELLA.
//
// SUBSTITUEIX la taula de passos del Registre d'activitat (micro-decisió d'Agus: sense
// convivència i sense flag). Una capçalera única a dalt; cada ronda és una FILA-RESUM plegable
// que agrega als MATEIXOS eixos de columna que el detall (temps · inici · fi), i l'entrega és
// una fila més del detall.
//
// ⚠️ **VÀLVULA D'ESCAPAMENT (declarada a l'acta).** Aquesta graella NO munta `ui/Table`. La taula
// de la casa serveix llistes PLANES: no té `colgroup` d'amplades fixes, ni files de tipus
// diferent (resum / detall / entrega), ni una fila clicable enmig de files que no ho són. La
// capa de PRESENTACIÓ es duplica aquí —amb la mateixa pell: mateixos `th` de 10px en
// majúscules, mateixos filets `--line`/`--line-soft`, mateix hover `--sel`— i la LÒGICA es
// comparteix de debò: `utils/rondes` és el mateix mòdul que fa servir el Pla de treball.
//
// 🔒 El col·lapse es DERIVA (entregada = plegada, vigent = oberta) i no es desa enlloc.

const AMPLADES = ['34%', '16%', '10%', '16%', '16%', '8%']

const ESTAT_VARIANT = { [RONDA_ENTREGADA]: 'ok', [RONDA_TANCADA]: 'gray' }

// Estat de TASCA → variant del Badge. Mateix criteri que el Pla i que el dashboard F1: un sol
// significat per color a tot el producte.
const STATUS_VARIANT = { Done: 'ok', InProgress: 'gold', Paused: 'warn', Pending: 'gray' }

const th = (align) => ({
  padding: '9px 14px', fontSize: 'var(--fs-label)', letterSpacing: '.08em',
  textTransform: 'uppercase', color: 'var(--text-soft)', fontWeight: 600,
  borderBottom: '1px solid var(--line)', textAlign: align || 'left', whiteSpace: 'nowrap',
})

const td = (extra) => ({
  padding: '8px 14px', fontSize: 'var(--fs-body)',
  borderBottom: '1px solid var(--line-soft)',
  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  ...extra,
})

const mono = { fontFamily: 'var(--mono)' }

export default function RegistreRondes({ passos, rondes }) {
  const { t, i18n } = useTranslation()
  const locale = localeDeIdioma(i18n.language)
  const [plegatManual, setPlegatManual] = useState({})

  // Els passos de l'albarà porten `ronda_seq` i `qui` des d'M2, i els seus minuts s'anomenen
  // `minutes` (el Pla els diu `temps_consumit_min`): per això el mòdul compartit els demana.
  const blocs = agrupaPerRonda(passos, rondes, {
    minutsDe: (p) => p.minutes ?? 0,
    esFeta: (p) => p.status === 'Done',
  })
  const obert = (bloc) => plegatManual[bloc.clau] ?? bloc.obertPerDefecte
  const commuta = (bloc) => setPlegatManual(p => ({ ...p, [bloc.clau]: !obert(bloc) }))

  if (!blocs.length) {
    return (
      <div style={{ padding: 16, color: 'var(--text-faint)', fontStyle: 'italic',
                    fontSize: 'var(--fs-body)' }}>
        {t('rondes.reg_buit')}
      </div>
    )
  }

  return (
    <div style={{ background: 'var(--panel)', border: '1px solid var(--line)',
                  borderRadius: 'var(--r-card)', overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed',
                      minWidth: 720 }}>
        <colgroup>{AMPLADES.map((w, i) => <col key={i} style={{ width: w }} />)}</colgroup>
        <thead>
          <tr>
            <th style={th()}>{t('albara.taskType')}</th>
            <th style={th()}>{t('albara.status')}</th>
            <th style={th('right')}>{t('albara.time')}</th>
            <th style={th()}>{t('albara.start')}</th>
            <th style={th()}>{t('albara.end')}</th>
            <th style={th()}>{t('rondes.reg_col_qui')}</th>
          </tr>
        </thead>
        <tbody>
          {blocs.map(bloc => {
            const desplegat = obert(bloc)
            const segellada = bloc.estat === RONDA_ENTREGADA
            const orfe = bloc.ronda == null
            return (
              <Fragment key={bloc.clau}>
                {/* FILA-RESUM: el mateix eix de columna que el detall. Plegada, la volta segueix
                    dient el seu resultat (estat + fi), que és el que el mockup demana. */}
                <tr onClick={() => commuta(bloc)} style={{ cursor: 'pointer' }}
                    onMouseEnter={e => { e.currentTarget.style.filter = 'brightness(0.98)' }}
                    onMouseLeave={e => { e.currentTarget.style.filter = 'none' }}>
                  <td style={td({ background: 'var(--bg-page)', borderTop: '1px solid var(--line)' })}>
                    <i className={`ti ti-chevron-${desplegat ? 'down' : 'right'}`} aria-hidden="true"
                       style={{ fontSize: 12, color: 'var(--text-soft)', marginRight: 6 }} />
                    <span style={{ fontWeight: 600 }}>
                      {orfe ? t('rondes.sense_volta') : t('rondes.nom', { n: bloc.seq })}
                    </span>
                    {bloc.rectificacions > 0 && (
                      <span style={{ ...mono, marginLeft: 8, fontSize: 'var(--fs-caption)',
                                     color: 'var(--warn-ink)' }}>
                        {t('rondes.rectificacions', { count: bloc.rectificacions })}
                      </span>
                    )}
                  </td>
                  <td style={td({ background: 'var(--bg-page)', borderTop: '1px solid var(--line)' })}>
                    {bloc.estat && (
                      <Badge variant={ESTAT_VARIANT[bloc.estat] || 'gold'}>
                        {t(`rondes.estat_${bloc.estat}`)}
                      </Badge>
                    )}
                  </td>
                  <td style={td({ ...mono, background: 'var(--bg-page)', textAlign: 'right',
                                  fontWeight: 600, borderTop: '1px solid var(--line)' })}>
                    {formatMinutes(bloc.minuts)}
                  </td>
                  <td style={td({ ...mono, background: 'var(--bg-page)', fontWeight: 600,
                                  borderTop: '1px solid var(--line)' })}>
                    {orfe ? '—' : formatDataHora(bloc.inici, locale)}
                  </td>
                  <td style={td({ ...mono, background: 'var(--bg-page)', fontWeight: 600,
                                  borderTop: '1px solid var(--line)' })}>
                    {orfe ? '—' : formatDataHora(bloc.fi, locale)}
                  </td>
                  <td style={td({ background: 'var(--bg-page)', color: 'var(--text-soft)',
                                  borderTop: '1px solid var(--line)' })}>
                    {t('rondes.n_tasques', { count: bloc.total })}
                  </td>
                </tr>

                {desplegat && bloc.tasques.map((p, i) => (
                  <tr key={`${bloc.clau}-${i}`}>
                    {/* La sagnia diu de qui penja la fila; el fade, que la volta és segellada. */}
                    <td style={td({ paddingLeft: 34, color: segellada ? 'var(--text-soft)' : undefined })}>
                      {p.task_type || '—'}
                    </td>
                    <td style={td()}>
                      <Badge variant={STATUS_VARIANT[p.status] || 'gray'}>
                        {t(`model_sheet.dashboard.task_status.${p.status}`, { defaultValue: p.status })}
                      </Badge>
                    </td>
                    <td style={td({ ...mono, textAlign: 'right' })}>{formatMinutes(p.minutes)}</td>
                    <td style={td(mono)}>{formatDataHora(p.started_at, locale)}</td>
                    <td style={td(mono)}>{formatDataHora(p.finished_at, locale)}</td>
                    <td style={td({ color: 'var(--text-soft)' })}>{p.qui || '—'}</td>
                  </tr>
                ))}

                {/* L'ENTREGA viu DINS del detall, amb el fons `--sel` i el filet daurat de la
                    casa. En plegar la volta, el seu resultat queda dit a la fila-resum. */}
                {desplegat && bloc.entrega && (
                  <tr>
                    <td style={td({ paddingLeft: 34, background: 'var(--sel)',
                                    borderTop: '1px solid var(--gold-border)' })}>
                      <i className="ti ti-package-export" aria-hidden="true"
                         style={{ color: 'var(--gold)', fontSize: 14, marginRight: 6 }} />
                      <b>{t('rondes.reg_entrega_a', { destinatari: bloc.entrega.destinatari })}</b>
                      {bloc.entrega.descripcio && (
                        <span style={{ color: 'var(--text-soft)' }}> · {bloc.entrega.descripcio}</span>
                      )}
                    </td>
                    <td style={td({ background: 'var(--sel)', borderTop: '1px solid var(--gold-border)' })}>
                      {bloc.entrega.data_ok
                        ? <Badge variant="ok">{t('rondes.ok_client_fet', { data: formatDataCurta(bloc.entrega.data_ok, locale) })}</Badge>
                        : <Badge variant="warn">{t('rondes.ok_client_pendent')}</Badge>}
                    </td>
                    <td style={td({ ...mono, background: 'var(--sel)', textAlign: 'right',
                                    borderTop: '1px solid var(--gold-border)' })}>—</td>
                    <td style={td({ ...mono, background: 'var(--sel)',
                                    borderTop: '1px solid var(--gold-border)' })}>
                      {formatDataHora(bloc.entrega.data, locale)}
                    </td>
                    <td style={td({ ...mono, background: 'var(--sel)',
                                    borderTop: '1px solid var(--gold-border)' })}>—</td>
                    <td style={td({ background: 'var(--sel)', color: 'var(--text-soft)',
                                    borderTop: '1px solid var(--gold-border)' })}>
                      {bloc.entrega.qui_informa_nom || '—'}
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
