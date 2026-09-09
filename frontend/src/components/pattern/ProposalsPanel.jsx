import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CADENA } from './sewText'
import { formatLen, titleLen } from '../../utils/format'
import { Casella } from './seleccio'

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
  sel = null, onAlterna = null,
  onConfirma, onRebutja, onRessalta,
  // F4.3 · les expectatives de NUCLI que aquest model encara no té cosides, i el gest
  // d'acceptar-ne unes quantes de cop.
  absents = [], onConfirmaBloc = null, confirmantBloc = false,
}) {
  const { t } = useTranslation()

  // 🚨 El checklist es pinta ENCARA QUE no hi hagi cap proposta: són dues preguntes
  // diferents —«què et proposo» i «què esperaria el catàleg»— i la segona és justament la
  // que val en un patró que ningú no ha cosit encara. Amagar-la amb la primera buida seria
  // callar el que més ajuda.
  if (!propostes.length) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', margin: 0 }}>
          {t('pattern.taller.proposals_empty')}
        </p>
        <Absents t={t} absents={absents} />
      </div>
    )
  }

  const forts = propostes.filter(p => p.confianca >= 0.60)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {/* PROPOSA EL COSIT SENCER: acceptar en bloc les que van bé de debò. El llindar de
          bloc (0,60) NO és el de proposar (0,40): oferir-les a la llista i acceptar-les
          totes de cop sense mirar-les una a una són dos gestos amb dos riscos diferents, i
          el segon ha de ser més exigent. Les altres segueixen a la llista, una a una. */}
      {onConfirmaBloc && forts.length > 1 && (
        <button
          onClick={() => onConfirmaBloc(forts)}
          disabled={confirmantBloc}
          style={{
            alignSelf: 'flex-start', cursor: confirmantBloc ? 'progress' : 'pointer',
            background: 'var(--panel)', color: 'var(--text-main)',
            border: '1px solid var(--line)', borderRadius: 'var(--r-ctrl)',
            padding: '0.3rem 0.6rem', fontSize: 'var(--fs-caption)',
            display: 'flex', alignItems: 'center', gap: '0.35rem', minHeight: 24,
          }}
          title={t('pattern.taller.proposals_all_t')}
        >
          <i className="ti ti-needle-thread" aria-hidden="true" />
          {confirmantBloc
            ? t('pattern.taller.proposals_all_running')
            : t('pattern.taller.proposals_all', { count: forts.length })}
        </button>
      )}

      {propostes.map(p => (
        <Proposta
          key={p.clau.join('-')} t={t} p={p} unit={unit}
          marcat={sel ? sel.has(p.clau.join('-')) : null}
          onMarca={onAlterna ? () => onAlterna(p.clau.join('-')) : null}
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
            fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
            margin: '0.2rem 0 0', display: 'flex', alignItems: 'center', gap: '0.3rem',
          }}
        >
          <i className="ti ti-filter" />
          {t('pattern.taller.proposals_dropped', {
            rebutjades: descartats.rebutjades, cosits: descartats.ja_cosits,
          })}
        </p>
      )}

      <Absents t={t} absents={absents} />
    </div>
  )
}


/**
 * A2b · EL CHECKLIST: què esperaria el catàleg i aquest model encara no té cosit.
 *
 * 🚨 **Informació, MAI un error.** Un vestit pot no portar una costura que el corpus
 * considera de nucli, i dir-li «falta» amb to de defecte ensenyaria el patronista a no
 * llegir la llista — el mateix mal que un llindar de proposta massa baix. Va en gris, amb
 * icona de llista i no d'avís, i la frase diu «n'esperaria», no «te'n falta».
 */
function Absents({ t, absents }) {
  if (!absents || !absents.length) return null
  return (
    <div style={{
      marginTop: '0.35rem', paddingTop: '0.35rem', borderTop: '1px solid var(--line)',
      display: 'flex', flexDirection: 'column', gap: 2,
    }}>
      <p style={{
        margin: 0, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
        display: 'flex', alignItems: 'center', gap: '0.3rem',
      }}>
        <i className="ti ti-list-check" aria-hidden="true" />
        {t('pattern.taller.expected_title', { count: absents.length })}
      </p>
      {absents.map((a, i) => (
        <p
          key={`${a.a.piece_role}-${a.a.edge_role}-${a.b.piece_role}-${a.b.edge_role}-${i}`}
          title={a.detall}
          style={{
            margin: 0, paddingLeft: '1.1rem',
            fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
          }}
        >
          {t('pattern.taller.expected_row', {
            a: `${a.a.piece_role}·${a.a.edge_role}`,
            b: `${a.b.piece_role}·${a.b.edge_role}`,
          })}
        </p>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

function Proposta({ t, p, unit, marcat, onMarca, onConfirma, onRebutja, onRessalta }) {
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
        border: '1px solid var(--line)', borderLeft: '3px solid var(--gold)',
        borderRadius: 4, padding: '0.35rem 0.5rem', background: 'var(--panel)',
        display: 'flex', flexDirection: 'column', gap: 3,
        opacity: ocupat ? 0.5 : 1,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem' }}>
        {/* La casella només hi és si algú l'escolta: el panell també es fa servir sense
            selecció, i una casella que no fa res és pitjor que cap casella. */}
        {onMarca && (
          <Casella
            marcat={marcat} onChange={onMarca}
            etiqueta={t('pattern.taller.bulk_select_row')}
          />
        )}
        <i className="ti ti-wand" style={{ color: 'var(--gold)', marginTop: 2, flexShrink: 0 }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {titol}
          </div>
          <div style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
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
            color: p.confianca >= 0.66 ? 'var(--ok)' : 'var(--text-soft)',
            border: '1px solid var(--line)', borderRadius: 10, padding: '0 6px',
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

      {/* C2 · «Confirma» era daurat ple. No pot passar a blau: és una acció DE FILA i n'hi ha
          una per proposta a la llista, mentre que la §5.1 dona UNA primària per pantalla —
          N blaus alhora no diuen «el que has vingut a fer», diuen soroll. Va a SECUNDÀRIA
          (§5.2), que és el que la norma reserva a les accions de la casa; el pes contra
          «Rebutja» el segueix marcant el filet d'or contra el filet neutre. */}
      <div style={{ display: 'flex', gap: '0.35rem' }}>
        <button
          onClick={() => acte(() => onConfirma(p))}
          disabled={ocupat}
          style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: '0.3rem', padding: '0.2rem 0.4rem',
            background: 'var(--panel)', color: 'var(--text-main)',
            border: '1px solid var(--gold-border)', borderRadius: 4,
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
            background: 'var(--panel)', color: 'var(--text-soft)',
            border: '1px solid var(--line)', borderRadius: 4,
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
  const { i18n } = useTranslation()
  const d = senyal.dades || {}
  // Els milers, en l'idioma de la pantalla. `toLocaleString()` sol agafa el del NAVEGADOR i
  // escrivia «436,842» enmig d'una frase en català, que és la mateixa xifra dita malament.
  const mil = (n) => (n ?? 0).toLocaleString(i18n.language || 'ca')
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
    // El COSTUM del taller (QA-TALLER-B · T4): què s'ha confirmat o corregit abans en aquest
    // rol de peça. El servidor n'envia les PECES a `dades`, i la frase es construeix aquí —
    // el seu `detall` va en català pla i es queda al `title`, com la resta.
    if (senyal.mena === 'preferencia') {
      if (contra) {
        return t('pattern.taller.sig_pref_against', { peces: (d.contra || []).join(', ') })
      }
      return t('pattern.taller.sig_pref_ok', { peces: (d.confirmats || []).join(', ') })
    }
    // F4.3 · L'EXPECTATIVA DEL CATÀLEG. Els números són els de la plantilla, crus: «espera
    // aquesta parella» sense xifres seria un adjectiu, i el que fa discutible un senyal és
    // poder mirar sobre quants patrons s'ha mesurat.
    if (senyal.mena === 'cataleg') {
      if (d.veto) {
        return t('pattern.taller.sig_cat_never', {
          seams: mil(d.observed_seams), den: mil(d.observed_den),
        })
      }
      return t(`pattern.taller.sig_cat_${d.grau || 'rare'}`, {
        seams: mil(d.observed_seams), den: mil(d.observed_den),
      })
    }
    // F4.3 · EL PRECEDENT DEL TALLER: no el corpus, sinó aquesta casa.
    if (senyal.mena === 'precedent') {
      return t(d.vegades > 1 ? 'pattern.taller.sig_prec_many' : 'pattern.taller.sig_prec_one', {
        model: d.model_nom, mes: (d.vegades || 1) - 1,
      })
    }
    if (senyal.mena === 'noms') {
      // El motiu és un codi del domini, i cada codi té la seva frase.
      return t(`pattern.taller.sig_name_${d.motiu || 'none'}`, {
        a: d.peca_a, b: d.peca_b,
      })
    }
    // Una mena que aquesta versió de la UI no coneix: val més el català pla del servidor que
    // una clau i18n inventada que sortiria com a text cru. El motor pot afegir senyals nous
    // sense que la pantalla els hagi de saber abans.
    return senyal.detall || ''
  }

  return (
    <li
      title={senyal.detall}
      style={{
        display: 'flex', alignItems: 'flex-start', gap: '0.3rem',
        fontSize: 'var(--fs-caption)',
        color: contra ? 'var(--err)' : nul ? 'var(--text-soft)' : 'var(--text-main)',
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
