import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { etiquetaPeca } from './pieceText'

/**
 * ROLS DE VORA (F4.2) — dir QUÈ és cada tram d'una peça ja identificada.
 *
 * Va sota `PieceIdentityList` i al mateix tab, i això és una decisió i no una comoditat:
 * batejar les vores és **la segona meitat del mateix gest**. La precondició d'aquesta
 * llista és exactament el producte d'aquella —un `piece_role` que ha signat una persona—,
 * i separar-les en dues pantalles obligaria a navegar entre elles per fer una sola lectura.
 * El Taller no és el lloc: allà hi viuen els trams DECLARATS, que són gestos del
 * patronista sobre la geometria; això d'aquí és vocabulari sobre el contorn derivat.
 *
 * 🚨 **El verd només el posa un humà, i la proposta no és mai verda.** Mateixa llei que
 * F4.1 i el mateix vocabulari visual: la proposta va amb `--warn-state`, l'estat de dada
 * pendent, i no queda desada fins que algú l'accepta. El que la fila diu —el rol CONFIRMAT—
 * arriba del servidor a `confirmed`, mai d'un estat del navegador.
 *
 * 🚨 **El silenci es diu, no s'amaga.** Un tram sense proposta té la seva línia igualment,
 * amb el motiu al `title`: sense això, «el catàleg no té paraula per a aquesta vora» i «no
 * s'ha executat res» es veurien igual, que és el error que la línia de recompte de
 * `PieceIdentityList` ja evita per a les peces.
 */
export default function PieceEdgeRoleList({
  files, vocabularis, onConfirma, onTria, pecaSel, desant, error,
  // ── F4.2-BIS · el cablatge amb el llenç. Al tab Patró no s'hi passen i la llista es
  // comporta com sempre; al Taller lliguen fila i tram en tots dos sentits.
  voraSel = null, onVoraSel = null,
  // Amb quines peces es treballa: al Taller, NOMÉS la que hi ha seleccionada al llenç.
  // Filtrar aquí i no al pare és el que fa que la llista sigui la MATEIXA en tots dos
  // llocs en comptes de dos components bessons que divergirien al primer canvi.
  nomesPeca = '',
}) {
  const { t, i18n } = useTranslation()
  const [esborrany, setEsborrany] = useState({})   // segment_id → slug | ''

  // Només les peces on la pregunta té sentit. Una peça sense rol confirmat no s'ofereix
  // aquí perquè no s'hi pot respondre: el vocabulari de vores el decideix el rol.
  const visibles = useMemo(
    () => (files || []).filter(f => !nomesPeca || f.nom_block === nomesPeca),
    [files, nomesPeca])
  const ambRol = useMemo(() => visibles.filter(f => f.piece_role), [visibles])
  const senseRol = visibles.length - ambRol.length

  if (!files) return null

  const valor = (f, p) => {
    const clau = p.segment_id
    if (clau in esborrany) return esborrany[clau]
    return f.confirmed?.[clau] || ''
  }
  const brut = (f) => f.proposals.some(p =>
    p.segment_id in esborrany && esborrany[p.segment_id] !== (f.confirmed?.[p.segment_id] || ''))

  const posa = (sid, slug) => setEsborrany(e => ({ ...e, [sid]: slug }))

  const acceptaTot = (f) => {
    const nou = {}
    for (const p of f.proposals) {
      if (p.edge_role && !f.confirmed?.[p.segment_id]) nou[p.segment_id] = p.edge_role
    }
    setEsborrany(e => ({ ...e, ...nou }))
  }

  const desa = async (f) => {
    const trams = f.proposals
      .filter(p => p.segment_id in esborrany)
      .map(p => ({ segment_id: p.segment_id, edge_role_slug: esborrany[p.segment_id] || null }))
    if (!trams.length) return
    await onConfirma(f.piece_id, trams)
    setEsborrany(e => {
      const n = { ...e }
      for (const x of trams) delete n[x.segment_id]
      return n
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', margin: 0 }}>
        {t('pattern.edges_hint')}
      </p>

      {ambRol.length === 0 && (
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', margin: 0 }}>
          {t('pattern.edges_needs_identity')}
        </p>
      )}

      {ambRol.map(f => (
        <TargetaPeca
          key={f.piece_id} f={f} t={t} idioma={i18n.language}
          vocabulari={vocabularis?.[f.piece_role] || []}
          sel={f.nom_block === pecaSel} onTria={onTria}
          valor={p => valor(f, p)} posa={posa}
          brut={brut(f)} desant={desant}
          voraSel={voraSel} onVoraSel={onVoraSel}
          onAccepta={() => acceptaTot(f)} onDesa={() => desa(f)}
        />
      ))}

      {/* El que queda fora es diu, amb el motiu. Una peça sense identitat no és un error
          d'aquesta pantalla, però tampoc no ha de desaparèixer sense explicació. */}
      {senseRol > 0 && (
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', margin: 0 }}>
          {t('pattern.edges_skipped_pieces', { count: senseRol })}
        </p>
      )}

      {error && (
        <p style={{ color: 'var(--error)', fontSize: 'var(--fs-caption)', margin: 0 }}>
          {error}
        </p>
      )}
    </div>
  )
}


function TargetaPeca({
  f, t, idioma, vocabulari, sel, onTria, valor, posa, brut, desant, onAccepta, onDesa,
  voraSel, onVoraSel,
}) {
  const proposats = f.proposals.filter(p => p.edge_role && !f.confirmed?.[p.segment_id])
  const muts = f.proposals.filter(p => !p.edge_role)
  const confirmats = f.proposals.filter(p => f.confirmed?.[p.segment_id])

  return (
    <div
      onClick={() => onTria?.(f.nom_block)}
      style={{
        border: `1px solid ${sel ? 'var(--gold)' : 'var(--line)'}`,
        borderRadius: 'var(--r-ctrl)', background: 'var(--panel)',
        padding: '0.5rem 0.6rem', display: 'flex', flexDirection: 'column', gap: '0.4rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem',
                    flexWrap: 'wrap' }}>
        <strong style={{ fontSize: 'var(--fs-body)' }}>{etiquetaPeca(f)}</strong>
        <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
                       fontStyle: 'italic' }}>
          {t('pattern.edges_counts', {
            confirmats: confirmats.length, proposats: proposats.length,
            muts: muts.length,
          })}
        </span>
        <span style={{ flex: 1 }} />
        {proposats.length > 0 && (
          <button
            onClick={e => { e.stopPropagation(); onAccepta() }}
            style={boto('var(--warn-state-bg)', 'var(--warn-ink)', 'var(--warn-state)')}
          >
            <i className="ti ti-wand" aria-hidden="true" />
            {t('pattern.edges_accept_all', { count: proposats.length })}
          </button>
        )}
        <button
          onClick={e => { e.stopPropagation(); onDesa() }}
          disabled={!brut || desant}
          style={{
            ...boto(brut ? 'var(--accio)' : 'var(--panel)',
                    brut ? 'var(--white)' : 'var(--text-soft)', 'var(--line)'),
            cursor: brut ? 'pointer' : 'not-allowed',
          }}
        >
          {desant ? t('pattern.edges_saving') : t('pattern.edges_confirm')}
        </button>
      </div>

      {/* El catàleg no dona cap paraula de vora a aquest rol de peça. No és que el motor
          hagi callat: és que no hi ha res a dir, i el desplegable no ha d'oferir un buit. */}
      {vocabulari.length === 0 && (
        <p style={{ margin: 0, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
          <i className="ti ti-info-circle" aria-hidden="true" />{' '}
          {t('pattern.edges_no_vocabulary', { rol: f.piece_role })}
        </p>
      )}

      {vocabulari.length > 0 && f.proposals.map(p => (
        <FilaTram
          key={p.segment_id ?? p.index} p={p} t={t} idioma={idioma}
          vocabulari={vocabulari} confirmat={f.confirmed?.[p.segment_id] || ''}
          value={valor(p)} onCanvia={slug => posa(p.segment_id, slug)}
          sel={voraSel === p.segment_id}
          onSel={onVoraSel ? () => onVoraSel(p.segment_id) : null}
        />
      ))}

      {f.landmarks.length > 0 && (
        <p style={{ margin: 0, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
                    display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <i className="ti ti-point" aria-hidden="true" />
          {t('pattern.edges_landmarks', {
            punts: f.landmarks.map(l => l.landmark + (l.side ? `·${l.side}` : '')).join(', '),
          })}
        </p>
      )}
    </div>
  )
}


/** Una vora: el xip d'estat, el selector filtrat, i l'evidència al `title`. */
function FilaTram({ p, t, idioma, vocabulari, confirmat, value, onCanvia, sel, onSel }) {
  const proposat = p.edge_role && !confirmat
  const brut = value !== confirmat
  const ev = p.evidence || {}
  const g = ev.geometry || {}
  const fila = useRef(null)

  // 🚨 El desplaçament el mana la SELECCIÓ, vingui d'on vingui. Clicar un tram al llenç ha
  // de portar la seva fila a la vista, i un contorn de setze trams no cap a la columna:
  // sense això, la meitat dels clics del patronista il·luminarien una fila que no veu.
  // `nearest` i no `center` perquè una fila que ja es veu no s'ha de moure sota el cursor.
  useEffect(() => {
    if (sel && fila.current) {
      fila.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [sel])

  return (
    <div
      ref={fila}
      onMouseEnter={onSel || undefined}
      style={{
        display: 'flex', alignItems: 'center', gap: '0.4rem',
        // La fila que el llenç assenyala. `--tram-sel` és el mateix token que el
        // `KONVA_COL.tramSel` del canvas reflecteix: el mateix tram, el mateix èmfasi,
        // als dos costats de la pantalla.
        // El padding esquerre hi és SEMPRE, i no només quan la fila està seleccionada:
        // afegir-lo amb la selecció faria saltar la fila 3 px cada cop que el cursor hi
        // passa. La barra de `inset` s'hi dibuixa a dins, i el número del tram queda
        // llegible al costat en comptes de sota (mesurat a la captura del fum).
        paddingLeft: 6,
        ...(sel ? {
          background: 'var(--bg-muted)',
          boxShadow: 'inset 3px 0 0 var(--tram-sel)',
          borderRadius: 'var(--r-ctrl)',
        } : null),
      }}
      onClick={e => { e.stopPropagation(); if (onSel) onSel() }}>
      <span style={{
        fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)',
        color: 'var(--text-soft)', minWidth: '2.2rem',
      }}>
        {p.index + 1}
      </span>

      <span style={{
        fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)',
        color: 'var(--text-soft)', minWidth: '4.5rem', textAlign: 'right',
      }}>
        {g.length_mm != null ? t('pattern.edges_len', { cm: (g.length_mm / 10).toFixed(1) }) : ''}
      </span>

      <select
        value={value}
        onChange={e => onCanvia(e.target.value)}
        // El camp marcat vol dir «el que veus i el que hi ha desat no són el mateix».
        // Val tant per a una proposta pre-omplerta com per a una tria manual pendent de
        // gravar: en tots dos casos la BD encara diu una altra cosa.
        style={{
          flex: 1, minWidth: 0, fontSize: 'var(--fs-caption)',
          padding: '0.2rem 0.3rem', borderRadius: 'var(--r-ctrl)',
          border: '1px solid var(--line)', background: 'var(--bg-main)',
          color: 'var(--text-main)',
          ...(brut ? {
            borderColor: 'var(--warn-state)', background: 'var(--warn-state-bg)',
            color: 'var(--warn-ink)',
          } : null),
        }}
        title={proposat
          ? t('pattern.edges_chip_t', {
              score: (p.score ?? 0).toFixed(2), why: ev.why || '',
            })
          : (ev.why || '')}
        aria-label={t('pattern.edges_role_of', { n: p.index + 1 })}
      >
        <option value="">{t('pattern.edges_role_none')}</option>
        {vocabulari.map(r => (
          <option key={r.slug} value={r.slug}>
            {r[`nom_${idioma}`] || r.nom_ca || r.nom_en}
          </option>
        ))}
      </select>

      {confirmat && (
        <i className="ti ti-circle-check" style={{ color: 'var(--ok)' }}
           title={t('pattern.edges_confirmed_t')} aria-hidden="true" />
      )}
      {proposat && (
        <i className="ti ti-wand" style={{ color: 'var(--warn-ink)' }}
           title={t('pattern.edges_proposed_t', { score: (p.score ?? 0).toFixed(2) })}
           aria-hidden="true" />
      )}
      {/* El silenci ÉS un estat i porta el seu motiu: un tram sense proposta no és un
          tram que ningú hagi mirat. */}
      {!p.edge_role && !confirmat && (
        <i className="ti ti-help-circle" style={{ color: 'var(--text-soft)' }}
           title={ev.why || t('pattern.edges_silent_t')} aria-hidden="true" />
      )}
    </div>
  )
}


const boto = (bg, fg, line) => ({
  cursor: 'pointer', background: bg, color: fg,
  border: `1px solid ${line}`, borderRadius: 'var(--r-ctrl)',
  padding: '0.25rem 0.55rem', fontSize: 'var(--fs-caption)',
  display: 'flex', alignItems: 'center', gap: '0.3rem',
  minHeight: 22,
})
