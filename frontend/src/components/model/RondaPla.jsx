import { useTranslation } from 'react-i18next'

import Badge from '../ui/Badge'
import { formatMinutes, formatDataHora, formatDataCurta, localeDeIdioma } from '../../utils/format'
import { RONDA_ENTREGADA, RONDA_OBERTA, RONDA_TANCADA } from '../../utils/rondes'

// M2 · MOCKUP A v2 — EL CONTENIDOR D'UNA VOLTA al Pla de treball.
//
// Pinta la capçalera i la línia d'entrega; les targetes de tasca arriben com a `children`, que és
// el que deixa que el Pla segueixi fent servir la SEVA targeta de sempre (v. l'acta: la versió
// compacta del mockup és presentació, i el transport i el handoff viuen a `WorkPlan`).
//
// 🔒 EL COL·LAPSE ÉS DERIVAT, NO PERSISTIT. Neix del `bloc.obertPerDefecte` (entregada = plegada,
// vigent = oberta) i l'usuari el pot canviar mentre és a la pantalla; enlloc no es desa. Un
// `localStorage` aquí convertiria un estat del domini en una preferència.

// Estat de la volta → variant del Badge de la casa. `entregada` és un FET consumat (verd d'èxit,
// com tot el que està fet al sistema); `tancada` sense entrega és la volta que ja no admet
// ningú i encara no ha declarat res —neutra, perquè no és ni un èxit ni una alerta.
const ESTAT_VARIANT = {
  [RONDA_ENTREGADA]: 'ok',
  [RONDA_TANCADA]: 'gray',
}

const capcalera = {
  display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
  padding: '10px 14px',
}

export default function RondaPla({ bloc, obert, onToggle, onEntregar, onOkClient, children }) {
  const { t, i18n } = useTranslation()
  const locale = localeDeIdioma(i18n.language)
  const { ronda, estat, entrega, tasques, total, fets, pct, minuts, fase, rectificacions } = bloc
  const orfe = ronda == null
  const segellada = estat === RONDA_ENTREGADA

  return (
    <div style={{
      background: 'var(--panel)', border: '1px solid var(--line)',
      borderRadius: 'var(--r-card)', marginBottom: 12, overflow: 'hidden',
    }}>
      <div style={{
        ...capcalera,
        borderBottom: (obert || entrega) ? '1px solid var(--line)' : 'none',
      }}>
        <button type="button" onClick={onToggle}
          aria-expanded={obert}
          title={obert ? t('rondes.plega') : t('rondes.desplega')}
          style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 20, height: 20, minHeight: 20, padding: 0,
            border: 'none', background: 'none', cursor: 'pointer', color: 'var(--text-soft)',
          }}>
          <i className={`ti ti-chevron-${obert ? 'down' : 'right'}`} aria-hidden="true"
             style={{ fontSize: 14 }} />
        </button>

        {/* NOM DE LA VOLTA. Les files sense volta hi són igual: el mockup no les dibuixa
            perquè no en té cap, però són la forma sencera de tot model llegat. */}
        <span style={{
          fontWeight: 600, fontSize: 'var(--fs-body)', letterSpacing: '.02em',
          color: segellada ? 'var(--text-soft)' : 'var(--text-main)', whiteSpace: 'nowrap',
        }}>
          {orfe ? t('rondes.sense_volta') : t('rondes.nom', { n: ronda.seq })}
        </span>

        {/* FIT-8 · el rastre del segell es veu AQUÍ, al costat del nom, i no només al log. */}
        {rectificacions > 0 && (
          <span title={t('rondes.rectificacions_titol')}
                style={{ fontSize: 'var(--fs-caption)', color: 'var(--warn-ink)',
                         fontFamily: 'var(--mono)', whiteSpace: 'nowrap' }}>
            {t('rondes.rectificacions', { count: rectificacions })}
          </span>
        )}

        {fase && <Badge variant="gray">{fase}</Badge>}
        {estat && <Badge variant={ESTAT_VARIANT[estat] || 'gold'}>{t(`rondes.estat_${estat}`)}</Badge>}

        {/* `lliurable` és un SENYAL, no una porta (M2 · CODA-BIS). Diu «ja hi és tot el que
            aquesta volta havia de produir» —totes les tasques `es_lliurable` són Done— i el seu
            lloc és al costat de l'estat, informant. El gest d'entregar ja no en depèn: v. el botó
            més avall. Les dues preguntes segueixen separades al contracte del serializer
            (`lliurable` deduït · `entregada` declarat) i ara també a la cara. */}
        {bloc.lliurable && !entrega && (
          <Badge variant="ok" icon="ti-package-export"
                 title={t('lliurable.badge_titol', { n: ronda?.seq })}>
            {t('rondes.lliurable')}
          </Badge>
        )}

        <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
                       fontFamily: 'var(--mono)' }}>
          {!orfe && (
            <>
              {t('rondes.inici')} <b style={{ color: 'var(--text-main)', fontWeight: 500 }}>{formatDataHora(bloc.inici, locale)}</b>
              {' · '}{t('rondes.fi')} <b style={{ color: 'var(--text-main)', fontWeight: 500 }}>{formatDataHora(bloc.fi, locale)}</b>
              {' · '}
            </>
          )}
          {t('rondes.temps')} <b style={{ color: 'var(--text-main)', fontWeight: 500 }}>{formatMinutes(minuts)}</b>
          {' · '}{t('rondes.n_tasques', { count: total })}
        </span>

        {/* PROGRÉS de la volta: fets/total i la barra. Mateixa lectura que el peu del Pla
            (que segueix parlant del MODEL sencer) i mateix farciment --ok: la barra diu
            QUANT S'HA FET, i el fet és verd a tot el sistema. */}
        <span style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto',
                       fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
                       fontFamily: 'var(--mono)' }}>
          <span>{fets}/{total} · {pct}%</span>
          <span style={{ width: 110, height: 5, borderRadius: 'var(--r-pill)',
                         background: 'var(--line-soft)', overflow: 'hidden', display: 'block' }}>
            <span style={{ display: 'block', width: `${pct}%`, height: '100%',
                           background: 'var(--ok)' }} />
          </span>
        </span>

        {/* «Marcar entregable» · **SEMPRE a la volta VIGENT**, sense condició de `lliurable`
            (M2 · CODA-BIS, decisió d'Agus).
            🔑 **El senyal deduït no pot ser la porta.** `ronda_lliurable` respon «ja hi és tot?»
            mirant NOMÉS les tasques `es_lliurable`, i per disseny torna `False` quan la volta no
            en té cap («no hi ha res per lliurar» no és «ja està lliurat»): una volta de feina que
            no produeix fitxa ni patró no s'hauria pogut entregar MAI des de la pantalla. I
            s'entrega el que hi ha —una volta es pot enviar a mitges—, o sigui que condicionar el
            gest al senyal era prohibir un cas real per protegir-ne un que ja té avís propi.
            Qui refusa, si cal, és el servidor; i el diàleg segueix dient que confirmar TANCARÀ la
            volta i quantes tasques vives s'endú.
            Es pinta a la volta VIGENT: una de tancada o entregada ja no admet cap entrega
            (`informar_entrega` la rebutjaria, i l'oferta seria una mentida de pantalla). */}
        {estat === RONDA_OBERTA && !entrega && (
          <button type="button" onClick={onEntregar}
            style={{
              fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)', padding: '5px 12px',
              borderRadius: 'var(--r-ctrl)', cursor: 'pointer',
              border: '1px solid var(--ok)', background: 'var(--panel)', color: 'var(--ok)',
              display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
            }}>
            <i className="ti ti-package-export" aria-hidden="true" style={{ fontSize: 14 }} />
            {t('rondes.marcar_entregable')}
          </button>
        )}
      </div>

      {/* LA LÍNIA D'ENTREGA (FIT-1): data · destinatari · qui informa · descripció · OK client.
          Fons `--sel` amb filet daurat: és la «forma de la casa» per al contenidor assenyalat
          (NORMA §1), i el que el mockup demanava amb el seu `--sel` propi. */}
      {entrega && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
          padding: '8px 14px', fontSize: 'var(--fs-caption)',
          background: 'var(--sel)', borderTop: '1px solid var(--gold-border)',
          color: 'var(--text-main)',
        }}>
          <i className="ti ti-package-export" aria-hidden="true"
             style={{ color: 'var(--gold)', fontSize: 14 }} />
          <span>
            {t('rondes.entrega_linia', {
              data: formatDataHora(entrega.data, locale),
              destinatari: entrega.destinatari,
            })}
            {entrega.qui_informa_nom && <> · {t('rondes.entrega_per', { qui: entrega.qui_informa_nom })}</>}
          </span>
          {/* FIT-1 · la descripció és TEXT LLIURE i no un lligam a cap artefacte: l'Entrega no
              té FK ni a la fitxa ni al patró (és un event informat, no un artefacte controlat),
              o sigui que aquí no hi pot haver enllaços. */}
          {entrega.descripcio && (
            <span style={{ color: 'var(--text-soft)', overflowWrap: 'anywhere' }}>
              · {entrega.descripcio}
            </span>
          )}
          <span style={{ marginLeft: 'auto' }}>
            {entrega.data_ok ? (
              <Badge variant="ok" title={entrega.qui_informa_ok_nom || undefined}>
                {t('rondes.ok_client_fet', { data: formatDataCurta(entrega.data_ok, locale) })}
              </Badge>
            ) : (
              <button type="button" onClick={onOkClient}
                style={{
                  fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)', padding: '2px 10px',
                  borderRadius: 'var(--r-pill)', cursor: 'pointer',
                  border: '1px solid var(--warn-state)', background: 'var(--warn-state-bg)',
                  color: 'var(--warn-ink)', whiteSpace: 'nowrap',
                }}>
                {t('rondes.ok_client_pendent')}
              </button>
            )}
          </span>
        </div>
      )}

      {obert && (
        <div style={{
          padding: '12px 14px', display: 'flex', flexWrap: 'wrap', gap: 12,
          // Volta ENTREGADA = feina segellada: es llegeix, no s'opera. El fade és el del mockup
          // i el transport se'n va del tot (el treu `WorkPlan`, que és qui el pinta).
          opacity: segellada ? 0.62 : 1,
        }}>
          {tasques.length === 0 ? (
            <div style={{ color: 'var(--text-faint)', fontStyle: 'italic',
                          fontSize: 'var(--fs-body)' }}>
              {t('rondes.volta_buida')}
            </div>
          ) : children}
        </div>
      )}
    </div>
  )
}
