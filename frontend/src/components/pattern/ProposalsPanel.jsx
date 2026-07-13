import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CADENA } from './sewText'
import { formatLen, titleLen } from '../../utils/format'

/**
 * COSTURES PROPOSADES (A2) — el motor proposa, la persona decideix.
 *
 * La llei del paquet, feta pantalla: **aquí no hi ha res del patró**. Cap d'aquestes files
 * existeix a la BD; es recalculen senceres a cada crida sobre la geometria viva. Per això no es
 * poden editar, ni reanomenar, ni arrossegar: només confirmar (i llavors passen a ser una costura
 * de veritat, indistingible d'una feta a mà) o rebutjar (i llavors no tornen a sortir mai).
 *
 * **Les xifres, no l'adjectiu.** Una confiança sola («87%») no es pot discutir; els dos senyals
 * que la fan —«25,3 i 25,2 cm» i «2 piquets homòlegs»— sí. Qui hagi de dir que no ha de poder
 * veure en què s'ha equivocat la màquina, o el «no» és un acte de fe igual que el «sí».
 *
 * El text es construeix AQUÍ a partir de les dades del servidor (i18n-gate ca/en/es); la frase
 * del backend, que va en català pla, es conserva com a `title` — hi ha matís que val la pena
 * poder llegir sencer.
 */
export default function ProposalsPanel({
  propostes, descartats, unit = 'CM',
  onConfirma, onRebutja, onRessalta,
}) {
  const { t } = useTranslation()

  if (!propostes.length) {
    return (
      <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
        {t('pattern.taller.proposals_empty')}
      </p>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {propostes.map(p => (
        <Proposta
          key={p.clau.join('-')} t={t} p={p} unit={unit}
          onConfirma={onConfirma} onRebutja={onRebutja} onRessalta={onRessalta}
        />
      ))}

      {/* El que el motor ha DESCARTAT. No és decoració: si al patronista li falta una costura,
          ha de poder saber si és que el motor no l'ha vista o és que ni tan sols l'ha mirada. */}
      {descartats && (
        <p
          title={t('pattern.taller.proposals_dropped_title', {
            curts: descartats.curts, cosits: descartats.ja_cosits,
            fluixes: descartats.sota_llindar, conflicte: descartats.en_conflicte,
          })}
          style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
            margin: '0.2rem 0 0', display: 'flex', alignItems: 'center', gap: '0.3rem',
          }}
        >
          <i className="ti ti-filter" />
          {t('pattern.taller.proposals_dropped', {
            rebutjades: descartats.rebutjades, cosits: descartats.ja_cosits,
          })}
        </p>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

function Proposta({ t, p, unit, onConfirma, onRebutja, onRessalta }) {
  const [ocupat, setOcupat] = useState(false)
  const v = p.veredicte || {}

  // El nom que TINDRÀ la costura si es confirma. És el mateix que el generador de noms de
  // costura faria servir (`nomCostura`): els trams encara no tenen nom —són la lectura del CAD—,
  // i el que els identifica per a una persona és de quina peça són i quant fan.
  const nomTram = (c) => t('pattern.taller.proposal_seg', {
    peca: c.peca, llarg: formatLen(c.longitud_cm, unit),
  })
  const titol = `${nomTram(p.a)} ${CADENA} ${nomTram(p.b)}`

  const acte = async (fn) => {
    setOcupat(true)
    try { await fn() } finally { setOcupat(false) }
  }

  return (
    <div
      onMouseEnter={() => onRessalta(p)}
      onMouseLeave={() => onRessalta(null)}
      style={{
        border: '1px solid var(--border)', borderLeft: '3px solid var(--gold)',
        borderRadius: 4, padding: '0.35rem 0.5rem', background: 'var(--bg-card)',
        display: 'flex', flexDirection: 'column', gap: 3,
        opacity: ocupat ? 0.5 : 1,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem' }}>
        <i className="ti ti-wand" style={{ color: 'var(--gold)', marginTop: 2, flexShrink: 0 }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {titol}
          </div>
          <div style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
            fontFamily: 'var(--mono)',
          }}>
            {/* El tipus i, si n'hi ha, el frunzit INFERIT: la xifra que el motor ha llegit de la
                geometria, no una que s'hagi inventat. */}
            {t(`pattern.sew_type.${p.tipus}`)}
            {p.tipus === 'frunzit' && ` ${formatLen(p.diferencial_cm, unit)}`}
            {' · '}
            <span title={titleLen(p.a.longitud_cm)}>{formatLen(p.a.longitud_cm, unit)}</span>
            {' / '}
            <span title={titleLen(p.b.longitud_cm)}>{formatLen(p.b.longitud_cm, unit)}</span>
          </div>
        </div>

        {/* La CONFIANÇA. Un número, i el desglòs sencer al `title`: qui hagi de dir que no ha de
            poder veure en què s'ha equivocat la màquina. */}
        <span
          title={p.senyals.map(s => `${s.punts >= 0 ? '+' : ''}${s.punts} · ${s.detall}`).join('\n')}
          style={{
            fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)', fontWeight: 600,
            color: p.confianca >= 0.66 ? 'var(--ok)' : 'var(--text-muted)',
            border: '1px solid var(--border)', borderRadius: 10, padding: '0 6px',
            flexShrink: 0,
          }}
        >
          {Math.round(p.confianca * 100)}%
        </span>
      </div>

      {/* ELS SENYALS, un a un. És l'argument: per què el motor creu que aquests dos trams es
          cusen. Els negatius també —una proposta que arriba al llindar malgrat una evidència en
          contra ha de dir-ho. */}
      <ul style={{
        listStyle: 'none', margin: 0, padding: 0,
        display: 'flex', flexDirection: 'column', gap: 1,
      }}>
        {p.senyals.map(s => (
          <Senyal key={s.mena} t={t} senyal={s} unit={unit} />
        ))}
      </ul>

      {/* QUÈ PASSARÀ si es confirma: el veredicte del mateix motor que després la jutjarà. Una
          proposta que naixerà en vermell ho ha de dir ABANS, no després del clic. */}
      <div
        title={v.missatge || undefined}
        style={{
          display: 'flex', alignItems: 'center', gap: '0.3rem',
          fontSize: 'var(--fs-caption)',
          color: v.casa ? 'var(--ok)' : 'var(--warn)',
          background: v.casa ? 'var(--ok-bg)' : 'var(--warn-bg)',
          borderRadius: 4, padding: '2px 6px',
        }}
      >
        <i className={`ti ${v.casa ? 'ti-check' : 'ti-alert-triangle'}`} />
        <span>
          {v.casa
            ? t('pattern.taller.proposal_will_match')
            : t('pattern.taller.proposal_wont_match', {
              desv: formatLen(v.desviament_cm, unit),
            })}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '0.35rem' }}>
        <button
          onClick={() => acte(() => onConfirma(p))}
          disabled={ocupat}
          style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: '0.3rem', padding: '0.2rem 0.4rem',
            background: 'var(--gold)', color: 'var(--white)',
            border: '1px solid var(--gold)', borderRadius: 4,
            cursor: ocupat ? 'wait' : 'pointer', fontSize: 'var(--fs-caption)',
          }}
        >
          <i className="ti ti-check" />
          {t('pattern.taller.proposal_confirm')}
        </button>
        <button
          onClick={() => acte(() => onRebutja(p))}
          disabled={ocupat}
          title={t('pattern.taller.proposal_reject_title')}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.3rem', padding: '0.2rem 0.5rem',
            background: 'var(--white)', color: 'var(--text-muted)',
            border: '1px solid var(--border)', borderRadius: 4,
            cursor: ocupat ? 'wait' : 'pointer', fontSize: 'var(--fs-caption)',
          }}
        >
          <i className="ti ti-x" />
          {t('pattern.taller.proposal_reject')}
        </button>
      </div>
    </div>
  )
}

/**
 * Un senyal, dit amb les seves xifres.
 *
 * El text es construeix de `dades` (els números crus del servidor) i no del `detall` (que va en
 * català pla): el gate demana ca/en/es. El `detall` es guarda per al `title`.
 */
function Senyal({ t, senyal, unit }) {
  const d = senyal.dades || {}
  const contra = senyal.punts < 0
  const nul = senyal.punts === 0

  const text = () => {
    if (senyal.mena === 'piquets') {
      if (d.n_a !== d.n_b) {
        return t('pattern.taller.sig_notch_count', { a: d.n_a, b: d.n_b })
      }
      if (!d.n_a) return t('pattern.taller.sig_notch_none')
      if (contra) return t('pattern.taller.sig_notch_off', { n: d.n_a })
      return t(d.invertit ? 'pattern.taller.sig_notch_inv' : 'pattern.taller.sig_notch_ok',
        { n: d.n_a })
    }
    if (senyal.mena === 'longitud') {
      if (contra) {
        return t('pattern.taller.sig_len_far', {
          a: formatLen(d.llarg_a_cm, unit), b: formatLen(d.llarg_b_cm, unit),
        })
      }
      if (d.sobra) {
        return t('pattern.taller.sig_len_ease', {
          peca: d.sobra === 'a' ? d.peca_a : d.peca_b,
          cm: formatLen(Math.abs(d.diferencia_cm), unit),
          pct: Math.round((d.relatiu || 0) * 100),
        })
      }
      return t('pattern.taller.sig_len_same', {
        a: formatLen(d.llarg_a_cm, unit), b: formatLen(d.llarg_b_cm, unit),
      })
    }
    // Noms: el motiu és un codi del domini, i cada codi té la seva frase.
    return t(`pattern.taller.sig_name_${d.motiu || 'none'}`, {
      a: d.peca_a, b: d.peca_b,
    })
  }

  return (
    <li
      title={senyal.detall}
      style={{
        display: 'flex', alignItems: 'flex-start', gap: '0.3rem',
        fontSize: 'var(--fs-caption)',
        color: contra ? 'var(--err)' : nul ? 'var(--text-muted)' : 'var(--text-main)',
      }}
    >
      <i
        className={`ti ${contra ? 'ti-minus' : nul ? 'ti-point' : 'ti-plus'}`}
        style={{ marginTop: 2, flexShrink: 0, fontSize: 12 }}
      />
      <span style={{ minWidth: 0 }}>{text()}</span>
    </li>
  )
}
