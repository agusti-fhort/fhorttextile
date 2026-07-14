import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { formatLen } from '../../utils/format'

/**
 * PINCES PROPOSADES (A1) — germà de `ProposalsPanel`, i a posta.
 *
 * Mateixa llei i mateix gest: **aquí no hi ha res del patró**. Cap fila existeix a la BD; es
 * recalculen a cada canvi de la geometria. Només es poden confirmar (i llavors passen a ser una
 * pinça de veritat, feta pel MATEIX camí de codi que els tres clics de W4b) o rebutjar (i llavors
 * no tornen a sortir).
 *
 * El número que mana és la TELA QUE ES MENJA (la suma dels dos costats): és, exactament, el que
 * després apareixerà restat a la costura que la conté («− 2,3 (Pinça 1)»). Es diu aquí perquè,
 * quan surti allà, es pugui venir a comprovar d'on sortia.
 */
export default function DartProposalsPanel({
  candidats, descartats, unit = 'CM', onConfirma, onRebutja, onRessalta,
}) {
  const { t } = useTranslation()

  if (!candidats.length) {
    return (
      <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
        {t('pattern.taller.darts_empty')}
      </p>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {candidats.map(c => (
        <Candidat
          key={c.clau.join('-')} t={t} c={c} unit={unit}
          onConfirma={onConfirma} onRebutja={onRebutja} onRessalta={onRessalta}
        />
      ))}

      {descartats && (descartats.ja_declarades > 0 || descartats.rebutjades > 0) && (
        <p style={{
          fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: '0.2rem 0 0',
          display: 'flex', alignItems: 'center', gap: '0.3rem',
        }}>
          <i className="ti ti-filter" />
          {t('pattern.taller.darts_dropped', {
            declarades: descartats.ja_declarades, rebutjades: descartats.rebutjades,
          })}
        </p>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

function Candidat({ t, c, unit, onConfirma, onRebutja, onRessalta }) {
  const [ocupat, setOcupat] = useState(false)

  const acte = async (fn) => {
    setOcupat(true)
    try { await fn() } finally { setOcupat(false) }
  }

  return (
    <div
      onMouseEnter={() => onRessalta(c)}
      onMouseLeave={() => onRessalta(null)}
      style={{
        border: '1px solid var(--border)', borderLeft: '3px solid var(--gold)',
        borderRadius: 4, padding: '0.35rem 0.5rem', background: 'var(--bg-card)',
        display: 'flex', flexDirection: 'column', gap: 3, opacity: ocupat ? 0.5 : 1,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem' }}>
        <i className="ti ti-triangle" style={{ color: 'var(--gold)', marginTop: 2, flexShrink: 0 }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {t('pattern.taller.dart_proposed', { peca: c.peca })}
          </div>
          <div style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontFamily: 'var(--mono)',
          }}>
            {t('pattern.taller.dart_legs', {
              a: formatLen(c.costat_a_cm, unit), b: formatLen(c.costat_b_cm, unit),
            })}
          </div>
        </div>

        {/* LA TELA QUE ES MENJA: el número que la costura mostrarà restat. */}
        <span
          title={t('pattern.taller.dart_intake_title')}
          style={{
            fontFamily: 'var(--mono)', fontSize: 'var(--fs-body)', fontWeight: 600,
            color: 'var(--gold)', flexShrink: 0,
          }}
        >
          −{formatLen(c.intake_cm, unit)}
        </span>

        <span
          title={c.senyals.map(s => `+${s.punts} · ${s.detall}`).join('\n')}
          style={{
            fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)', fontWeight: 600,
            color: c.confianca >= 0.66 ? 'var(--ok)' : 'var(--text-muted)',
            border: '1px solid var(--border)', borderRadius: 10, padding: '0 6px',
            flexShrink: 0,
          }}
        >
          {Math.round(c.confianca * 100)}%
        </span>
      </div>

      {/* Les MESURES que fan la proposta: la boca (el número que de debò la decideix), la
          fondària, i si els extrems porten piquet. Qui hagi de dir que no ha de veure per què. */}
      <ul style={{
        listStyle: 'none', margin: 0, padding: 0,
        display: 'flex', flexDirection: 'column', gap: 1,
      }}>
        <Senyal
          text={t('pattern.taller.dart_sig_mouth', {
            boca: formatLen(c.boca_cm, unit), pct: (c.boca_rel * 100).toFixed(1),
          })}
        />
        <Senyal
          text={t('pattern.taller.dart_sig_depth', { prof: formatLen(c.profunditat_cm, unit) })}
        />
        <Senyal
          text={c.piquets_boca
            ? t('pattern.taller.dart_sig_notches', { n: c.piquets_boca })
            : t('pattern.taller.dart_sig_no_notches')}
          fluix={!c.piquets_boca}
        />
      </ul>

      <div style={{ display: 'flex', gap: '0.35rem' }}>
        <button
          onClick={() => acte(() => onConfirma(c))}
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
          onClick={() => acte(() => onRebutja(c))}
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

function Senyal({ text, fluix = false }) {
  return (
    <li style={{
      display: 'flex', alignItems: 'flex-start', gap: '0.3rem',
      fontSize: 'var(--fs-caption)',
      color: fluix ? 'var(--text-muted)' : 'var(--text-main)',
    }}>
      <i
        className={`ti ${fluix ? 'ti-point' : 'ti-plus'}`}
        style={{ marginTop: 2, flexShrink: 0, fontSize: 12 }}
      />
      <span style={{ minWidth: 0 }}>{text}</span>
    </li>
  )
}
