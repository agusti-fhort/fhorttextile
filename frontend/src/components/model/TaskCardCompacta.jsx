import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import Badge from '../ui/Badge'
import { formatMinutes } from '../../utils/format'
import { taskTypeLabel } from '../../utils/taskType'
import { lecturaDeTasca } from '../../utils/tascaPla'

// M2 · CODA — LA TARGETA COMPACTA DE TASCA (`.tasca` de `proposta_A_v2_pla_treball.html`).
//
// És la targeta que el mockup posa DINS d'un contenidor de ronda: nom · temps/obertures · un
// transport petit · pastilla d'estat. Prou més densa que la gran perquè quatre o cinc hi càpiguen
// en una fila sota la capçalera de la volta, que és el que fa llegible el pla per rondes.
//
// ⚠️ **VÀLVULA D'ESCAPAMENT (llei de la casa).** Això és una SEGONA capa de presentació, no una
// extracció: `TaskCard` (la gran, a `WorkPlan.jsx`) no s'ha tocat i segueix pintant el pla dels
// models sense voltes. El que comparteixen de debò és el mòdul de lògica `utils/tascaPla` — els
// mapes d'icona, estat i transport, i la lectura de qui pot fer què. Si divergissin, dues
// superfícies dirien coses diferents de la mateixa tasca.
//
// Mides del mockup, amb els tokens de la casa: `.tasca` 8px/10px de farciment i mínim 190px;
// `.tasca-nom` a `--fs-body` en pes 600; `.tasca-meta` a `--fs-caption` en `--text-soft`;
// `.tbtn` de 20×20. El radi 8 del mockup no és de l'escala de la casa (6 · 12 · 999) i baixa a
// `--r-ctrl`, que és el veí i el que ja porten els controls.

const CARD = {
  flex: '1 1 190px', maxWidth: 260, minWidth: 190,
  borderWidth: 1, borderStyle: 'solid', borderRadius: 'var(--r-ctrl)',
  padding: '8px 10px', background: 'var(--panel)',
}

// `.tbtn`: 20×20 amb filet `--line` i radi de control. El deshabilitat baixa el FONS i conserva
// la tinta (§5.7): l'`opacity` apagaria també la icona i la deixaria per sota d'AA — i el que diu
// un botó apagat és justament el que ara no es pot fer.
// `destructiu` NO és un matís de color: és el que separa aquest botó dels tres del costat.
// §8 dona QUATRE tintes i la destructiva és `--err`; §8e ho concreta per a aquest cas exacte
// («Paperera per fila: icona destructiva 14, hover --err-bg»). Sense això la paperera sortia
// amb la MATEIXA pell que Play/Pause/Stop —`--text-soft` a 11px— a la mateixa línia: la
// posició la separava, però el que la fa reconeixible és el color, i un gest irreversible no
// es pot distingir d'un de reversible només per on cau.
function TransportMini({ icon, active, title, onClick, destructiu = false }) {
  const [sobre, setSobre] = useState(false)
  const tinta = destructiu ? 'var(--err)' : 'var(--text-soft)'
  return (
    <button type="button" title={title} disabled={!active}
      onClick={e => {
        e.preventDefault()
        e.stopPropagation()
        if (active) onClick?.(e)
      }}
      onMouseEnter={() => setSobre(true)}
      onMouseLeave={() => setSobre(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 20, height: 20, minHeight: 20, padding: 0,
        borderRadius: 'var(--r-ctrl)',
        borderWidth: 1, borderStyle: 'solid',
        borderColor: destructiu && sobre ? 'var(--err)' : 'var(--line)',
        background: (destructiu && sobre && active) ? 'var(--err-bg)'
          : (active ? 'var(--panel)' : 'var(--bg-page)'),
        color: active ? tinta : 'var(--text-faint)',
        cursor: active ? 'pointer' : 'not-allowed',
        // §8: l'escala d'icona és 14/16/20. Els tres del transport es queden a 11 (són de la
        // maqueta `.tbtn` i van en bloc); la destructiva puja a 14, que és el que §8e demana.
        fontSize: destructiu ? 14 : 11,
      }}>
      <i className={`ti ${icon}`} aria-hidden="true"
         style={{ fontSize: 'inherit', color: 'currentColor' }} />
    </button>
  )
}

export default function TaskCardCompacta({
  task, mine, hasToolRoute, segellada = false, onPlay, onPause, onStop, onDeclarar, onTreure,
}) {
  const { t } = useTranslation()
  const { transport, playActive, otherTech, out, icon, variant } =
    lecturaDeTasca(task, { mine, hasToolRoute })

  return (
    <div style={{
      ...CARD,
      // El filet gruixut de l'esquerra quan la tasca és FORA D'ENCÀRREC es queda: és marca de
      // DADA (§1), no selecció, i per això sobreviu a la compactació.
      borderColor: out ? 'var(--err)' : 'var(--line)',
      borderLeftWidth: out ? 3 : 1,
      opacity: otherTech ? 0.55 : 1,
    }}>
      {/* `.tasca-cap` — icona del tipus + nom, truncat i sense desbordar mai */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0, marginBottom: 6 }}>
        <i className={`ti ${icon}`} aria-hidden="true"
           style={{ fontSize: 14, color: 'var(--gold)', flexShrink: 0 }} />
        <span title={taskTypeLabel(t, task.task_type_code, task.task_type_name)}
              style={{ fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)',
                       overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {taskTypeLabel(t, task.task_type_code, task.task_type_name)}
        </span>
      </div>

      {/* `.tasca-meta` — temps · obertures · (qui la duu, si és d'altri). El mockup els posa
          tots tres en una sola línia; la regla de QUAN es diu el tècnic és la mateixa que a la
          targeta gran (només quan no és meva i té assignat), no una de nova. */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 7,
                    minWidth: 0, fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)',
                    color: 'var(--text-soft)' }}>
        <span style={{ whiteSpace: 'nowrap' }}>{formatMinutes(task.temps_consumit_min ?? 0)}</span>
        <span style={{ whiteSpace: 'nowrap' }}>
          {t('model_sheet.dashboard.workplan.openings', { n: task.obertures ?? 0 })}
        </span>
        {otherTech && task.assignee_nom && (
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                title={task.assignee_nom}>
            {task.assignee_nom}
          </span>
        )}
      </div>

      {out && (
        <div style={{ marginBottom: 7, fontSize: 'var(--fs-caption)', color: 'var(--err)',
                      overflowWrap: 'anywhere' }}>
          {t('model_sheet.dashboard.workplan.out_of_charge')}
        </div>
      )}

      {/* `.tasca-peu` — transport a l'esquerra, estat a la dreta.
          VOLTA ENTREGADA = FEINA SEGELLADA: el transport no s'apaga, se'n VA (`.segellada
          .transport{display:none}` del mockup). Un botó deshabilitat convida a prémer-lo i promet
          que algun dia s'encendrà; el que diu la llei és que aquesta feina ja s'ha entregat i que
          rectificar-la obre volta nova. No és un guard: `Done→InProgress` segueix sent legal
          (el segell és TOU, FIT-2) i el camí és el diàleg de la tasca, que deixa rastre al log. */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    gap: 8 }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {segellada ? <span /> : (<>
            <TransportMini icon="ti-player-play" active={playActive}
              title={mine ? t('model_sheet.dashboard.workplan.play')
                          : t('model_sheet.dashboard.workplan.handoff_play')}
              onClick={() => onPlay(task)} />
            <TransportMini icon="ti-player-pause" active={mine && transport.pause}
              title={t('model_sheet.dashboard.workplan.pause')} onClick={() => onPause(task)} />
            <TransportMini icon="ti-player-stop" active={mine && transport.stop}
              title={t('model_sheet.dashboard.workplan.stop')} onClick={() => onStop(task)} />
            {/* F2.5 · D-2 — les EXTERNES es fan fora de l'eina i el rellotge no hi arriba mai:
                l'única manera que aquell temps entri al sistema és dir-lo, i per això va aquí i
                no dins d'un menú. Les internes no el veuen mai. */}
            {task.tipus_extern && (
              <TransportMini icon="ti-clock-plus" active title={t('temps_declarat.boto')}
                             onClick={() => onDeclarar(task)} />
            )}
          </>)}
        </div>
        {/* Grup DRET: estat + paperera. Van junts perquè el peu segueixi sent un
            `space-between` de DOS blocs; solta, la paperera cauria al mig i desquadraria la
            línia. I va a l'extrem OPOSAT del transport a posta: és l'únic gest destructiu de la
            targeta i no ha de compartir veïnatge amb el Play. */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Badge variant={variant}>
            {t(`model_sheet.dashboard.task_status.${task.status}`, { defaultValue: task.status })}
          </Badge>
          {/* LA PAPERERA · NOMÉS sobre `Pending`, i no com a botó apagat sinó ABSENT.
              El backend ja refusa la resta amb un 409 («una tasca iniciada, pausada o feta
              conserva la seva història»), i oferir el gest per després negar-lo seria prometre
              una cosa que la llei no permet. A la volta segellada tampoc hi és, com el transport.
              El que passa en prémer-la depèn de si la tasca té ENCÀRREC, i això ho decideix
              `WorkPlan` amb el FK: aquí només es demana. Tabler outline, tinta per token. */}
          {!segellada && task.status === 'Pending' && onTreure && (
            <TransportMini icon="ti-trash" active destructiu
              title={task.encarrec ? t('paperera.titol_lligada') : t('paperera.titol_lliure')}
              onClick={() => onTreure(task)} />
          )}
        </div>
      </div>
    </div>
  )
}
