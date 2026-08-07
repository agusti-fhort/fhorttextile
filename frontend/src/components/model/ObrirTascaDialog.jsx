import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { overlayBase } from '../ui/overlay'
import { selS } from '../ui/buttons'
import {
  CARA_ALBARANADA, CARA_CAP, CARA_CONFLICTE, CARA_LLIURADA,
} from '../../utils/caraObrirTasca'

/**
 * F2.1 · EL MODAL D'OBRIR TASCA — UNA peça, tres cares.
 *
 * Tres cares i no tres components a posta: el que canvia entre elles són el títol, la frase i les
 * opcions; el gest és el mateix («què vols fer amb aquesta tasca?»). Tres components voldria dir
 * tres llocs on la regla d'or es pot trencar per separat.
 *
 *   ⚠️ REGLA D'OR — aquest modal NO ES MUNTA en el cas normal. Qui decideix és
 *   `utils/caraObrirTasca` (pur i provat); si retorna CARA_CAP el consumidor obre directament i
 *   aquí no s'hi arriba mai. Zero fricció, zero clics.
 *
 * En les tres cares, **«Només consultar» és el botó per defecte**: la lectura no té conseqüències
 * i les altres opcions sí (reassignar el rellotge d'algú, crear feina facturable). El defecte
 * d'un diàleg és el que passa quan algú prem Enter sense llegir.
 *
 * `onAccio(accio)` amb: 'consultar' | 'treballar' | 'ronda' | 'correccio'.
 */
export default function ObrirTascaDialog({ cara, tasca, rondaOberta, onAccio, onCancel }) {
  const { t } = useTranslation()
  const [enviant, setEnviant] = useState(false)
  if (!cara || cara === CARA_CAP) return null

  const fes = (accio) => { setEnviant(true); onAccio(accio) }

  const nomTasca = tasca?.task_type_name || ''
  const seguent = (rondaOberta?.seq || 1) + 1

  // Cada cara: títol, cos, i les opcions SECUNDÀRIES (la de consultar és sempre la primària).
  const cares = {
    [CARA_CONFLICTE]: {
      icona: 'ti-user-exclamation',
      // S-19 — el nom que hi va és el de qui hi TÉ EL RELLOTGE, i prou: la cara de conflicte
      // ja només surt quan n'hi ha un d'obert. Caure a `assignee_nom` seria tornar a barrejar
      // planificació amb realitat, justament al text que diu qui la té.
      titol: t('obrir_tasca.conflicte_titol', { tecnic: tasca?.obert_per_nom || '—' }),
      cos: t('obrir_tasca.conflicte_cos'),
      opcions: [{
        clau: 'treballar',
        etiqueta: t('obrir_tasca.conflicte_treballar'),
        nota: t('obrir_tasca.conflicte_treballar_nota'),
      }],
    },
    [CARA_LLIURADA]: {
      icona: 'ti-package-export',
      titol: t('obrir_tasca.lliurada_titol', { tasca: nomTasca }),
      cos: t('obrir_tasca.lliurada_cos'),
      opcions: [
        { clau: 'ronda', etiqueta: t('obrir_tasca.lliurada_ronda', { n: seguent }),
          nota: t('obrir_tasca.lliurada_ronda_nota') },
        { clau: 'correccio', etiqueta: t('obrir_tasca.lliurada_correccio'),
          nota: t('obrir_tasca.lliurada_correccio_nota') },
      ],
    },
    [CARA_ALBARANADA]: {
      icona: 'ti-file-invoice',
      titol: t('obrir_tasca.albaranada_titol'),
      cos: t('obrir_tasca.albaranada_cos'),
      opcions: [{
        clau: 'correccio',
        etiqueta: t('obrir_tasca.albaranada_extra'),
        nota: t('obrir_tasca.albaranada_extra_nota'),
      }],
    },
  }
  const c = cares[cara]
  if (!c) return null

  return (
    <div onClick={onCancel} style={overlayBase({ alignItems: 'center' })}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--white)', borderRadius: 12, padding: 22,
        width: 480, maxWidth: '92vw', maxHeight: '85vh', overflowY: 'auto',
        fontFamily: 'IBM Plex Mono, monospace',
      }}>
        <h2 style={{
          fontSize: 'var(--fs-h3)', fontWeight: 500, marginBottom: 6,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <i className={`ti ${c.icona}`} style={{ color: 'var(--gold)' }} />
          {c.titol}
        </h2>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 18, lineHeight: 1.5 }}>
          {c.cos}
        </p>

        {/* PRIMÀRIA: consultar. La lectura no té conseqüències; tota la resta en té. */}
        <button
          onClick={() => fes('consultar')}
          disabled={enviant}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            background: 'var(--gold)', color: 'var(--text-main)', border: 'none', borderRadius: 6,
            padding: '10px 14px', fontSize: 'var(--fs-body)', fontWeight: 600,
            fontFamily: 'inherit', cursor: enviant ? 'not-allowed' : 'pointer',
            opacity: enviant ? 0.5 : 1,
          }}
        >
          <i className="ti ti-eye" />
          {t('obrir_tasca.consultar')}
        </button>
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: '6px 0 16px' }}>
          {t('obrir_tasca.consultar_nota')}
        </p>

        {/* SECUNDÀRIES: cada una amb la seva conseqüència escrita a sota. */}
        {c.opcions.map(o => (
          <div key={o.clau} style={{ marginBottom: 14 }}>
            <button
              onClick={() => fes(o.clau)}
              disabled={enviant}
              style={{
                ...selS, width: '100%', textAlign: 'left', padding: '9px 12px',
                cursor: enviant ? 'not-allowed' : 'pointer', opacity: enviant ? 0.5 : 1,
              }}
            >
              {o.etiqueta}
            </button>
            <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: '5px 0 0' }}>
              {o.nota}
            </p>
          </div>
        ))}

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
          <button onClick={onCancel} disabled={enviant}
            style={{ ...selS, cursor: enviant ? 'not-allowed' : 'pointer', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}>
            {t('common.cancel')}
          </button>
        </div>
      </div>
    </div>
  )
}
