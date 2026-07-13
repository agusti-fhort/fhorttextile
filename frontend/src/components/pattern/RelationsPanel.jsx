import { useState } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * RELACIONS — el que s'ha declarat sobre el patró, editable.
 *
 * Tres famílies: POMs ancorats · Costures · Trams declarats. Substitueix
 * l'AnnotationPanel del tab, i hi afegeix el que W1 va fer possible: els AVISOS DE
 * COBERTURA (solapaments i excessos de vora) i els trams declarats.
 *
 * Els missatges es construeixen AQUÍ a partir de les xifres del servidor, no es
 * mostren els del servidor: el backend els escriu en català pla (no són claus i18n) i
 * el gate demana ca/en/es. La frase del servidor es conserva com a `title` — hi ha
 * matís que val la pena poder llegir sencer.
 */
export default function RelationsPanel({
  poms, sews, segments,
  onEsborraPom, onEsborraSew, onReanomenaTram, onEsborraTram,
}) {
  const { t } = useTranslation()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
      <Seccio titol={t('pattern.poms_anchored', { n: poms.length })}>
        {poms.length === 0 ? (
          <Buit text={t('pattern.poms_empty')} />
        ) : poms.map(p => (
          <Fila key={p.id}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 'var(--fs-body)', fontWeight: 600, fontFamily: 'var(--mono)',
              }}>
                {p.pom_code}
              </div>
              <div style={{
                fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {p.pom_nom} · {p.peca}
              </div>
            </div>
            <span style={{
              fontFamily: 'var(--mono)', fontSize: 'var(--fs-body)',
              color: p.valor_mesurat_cm == null ? 'var(--err)' : 'var(--text-main)',
            }}>
              {p.valor_mesurat_cm != null
                ? `${p.valor_mesurat_cm} cm`
                : t('pattern.pom_unmeasured')}
            </span>
            <BotoEsborra onClick={() => onEsborraPom(p.id)} etiqueta={t('app.delete')} />
          </Fila>
        ))}
      </Seccio>

      <Seccio titol={t('pattern.sews', { n: sews.length })}>
        {sews.length === 0 ? (
          <Buit text={t('pattern.sews_empty')} />
        ) : sews.map(s => (
          <Costura
            key={s.id} t={t} sew={s} onEsborra={() => onEsborraSew(s.id)}
          />
        ))}
      </Seccio>

      <Seccio titol={t('pattern.taller.segments', { n: segments.length })}>
        {segments.length === 0 ? (
          <Buit text={t('pattern.taller.segments_empty')} />
        ) : segments.map(s => (
          <Tram
            key={s.id} t={t} tram={s}
            onReanomena={onReanomenaTram} onEsborra={onEsborraTram}
          />
        ))}
      </Seccio>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

function Costura({ t, sew, onEsborra }) {
  const e = sew.estat || {}
  const cobertura = e.cobertura || []

  return (
    <div style={{
      border: `1px solid ${e.casa ? 'var(--ok)' : 'var(--err)'}`,
      background: e.casa ? 'var(--ok-bg)' : 'var(--err-bg)',
      borderRadius: 4, padding: '0.35rem 0.5rem',
      display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.4rem' }}>
        <i className={`ti ${e.casa ? 'ti-check' : 'ti-alert-triangle'}`}
           style={{ color: e.casa ? 'var(--ok)' : 'var(--err)', marginTop: 2 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 'var(--fs-body)', fontWeight: 600 }}>
            {t(`pattern.sew_type.${sew.tipus}`)}
            {sew.diferencial_cm ? ` · ${sew.diferencial_cm} cm` : ''}
          </div>
          {/* Les XIFRES, no l'adjectiu: "no casa" sense dir per quant no és diagnosticable. */}
          <div
            title={e.missatge || undefined}
            style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-main)',
                     fontFamily: 'var(--mono)' }}
          >
            {e.casa
              ? t('pattern.taller.sew_ok', { a: e.longitud_a_cm, b: e.longitud_b_cm })
              : t('pattern.taller.sew_off', {
                  desv: e.desviament_cm, a: e.longitud_a_cm, b: e.longitud_b_cm,
                })}
          </div>
        </div>
        <BotoEsborra onClick={onEsborra} etiqueta={t('app.delete')} />
      </div>

      {/* Cobertura (W1): la costura pot casar i la VORA estar malament igualment —
          dos trams que es trepitgen, o més centímetres cosits dels que la vora té. */}
      {cobertura.map((a, n) => (
        <div
          key={n}
          title={a.missatge || undefined}
          style={{
            display: 'flex', alignItems: 'flex-start', gap: '0.35rem',
            fontSize: 'var(--fs-caption)', color: 'var(--warn)',
            background: 'var(--warn-bg)', borderRadius: 4, padding: '3px 6px',
          }}
        >
          <i className="ti ti-alert-triangle" style={{ marginTop: 2 }} />
          <span>
            {a.mena === 'solapament'
              ? t('pattern.taller.cov_overlap', {
                  cm: a.solapament_cm, peca: a.peca, vora: a.vora,
                  vora_cm: a.longitud_vora_cm,
                })
              : t('pattern.taller.cov_excess', {
                  cm: a.exces_cm, suma: a.suma_cosida_cm, peca: a.peca, vora: a.vora,
                  vora_cm: a.longitud_vora_cm,
                })}
          </span>
        </div>
      ))}
    </div>
  )
}

function Tram({ t, tram, onReanomena, onEsborra }) {
  const [editant, setEditant] = useState(false)
  const [nom, setNom] = useState(tram.nom || '')
  const [rebuig, setRebuig] = useState(null)   // per què no s'ha pogut esborrar

  const desa = async () => {
    setEditant(false)
    if ((nom || '') !== (tram.nom || '')) await onReanomena(tram.id, nom)
  }

  const esborra = async () => {
    setRebuig(null)
    const r = await onEsborra(tram.id)
    // 409: el tram el reté una costura. El motiu es diu SENCER (quantes i quines), perquè
    // qui el vulgui esborrar sàpiga exactament què ha de desfer primer.
    if (r && !r.ok) {
      setRebuig(t('pattern.taller.segment_in_use', {
        n: r.sews.length, ids: r.sews.map(x => `#${x}`).join(', '),
      }))
    }
  }

  return (
    <div style={{
      border: '1px solid var(--border)', borderRadius: 4,
      padding: '0.3rem 0.5rem', background: 'var(--bg-card)',
      display: 'flex', flexDirection: 'column', gap: 3,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <i className="ti ti-line" style={{ color: 'var(--gold)', flexShrink: 0 }} />

        <div style={{ flex: 1, minWidth: 0 }}>
          {editant ? (
            <input
              autoFocus
              value={nom}
              onChange={e => setNom(e.target.value)}
              onBlur={desa}
              onKeyDown={e => {
                if (e.key === 'Enter') desa()
                if (e.key === 'Escape') { setNom(tram.nom || ''); setEditant(false) }
              }}
              aria-label={t('pattern.taller.segment_rename')}
              style={{
                width: '100%', fontSize: 'var(--fs-body)', padding: '0.1rem 0.3rem',
                border: '1px solid var(--gold)', borderRadius: 4,
              }}
            />
          ) : (
            <button
              onClick={() => setEditant(true)}
              title={t('pattern.taller.segment_rename')}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'text',
                textAlign: 'left', width: '100%',
                fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}
            >
              {tram.nom || t('pattern.taller.segment_unnamed')}
            </button>
          )}
          <div style={{
            fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {tram.peca} · {t('pattern.taller.segment_edge', { vora: tram.vora })}
          </div>
        </div>

        <span style={{
          fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)',
          color: 'var(--text-main)', flexShrink: 0,
        }}>
          {tram.longitud_cm != null ? `${tram.longitud_cm} cm` : '—'}
        </span>

        {/* Un tram EN ÚS no s'esborra: el botó ho diu abans de clicar-lo, i el servidor
            ho torna a dir si algú insisteix. */}
        {tram.en_us && (
          <i
            className="ti ti-needle-thread"
            title={t('pattern.taller.segment_used')}
            style={{ color: 'var(--text-muted)', flexShrink: 0 }}
          />
        )}
        <BotoEsborra onClick={esborra} etiqueta={t('app.delete')} />
      </div>

      {rebuig && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: '0.35rem',
          fontSize: 'var(--fs-caption)', color: 'var(--err)',
          background: 'var(--err-bg)', borderRadius: 4, padding: '3px 6px',
        }}>
          <i className="ti ti-alert-triangle" style={{ marginTop: 2 }} />
          <span>{rebuig}</span>
        </div>
      )}
    </div>
  )
}

function Seccio({ titol, children }) {
  return (
    <div>
      <h4 style={{
        fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '0.03em',
        color: 'var(--text-muted)', margin: '0 0 0.35rem',
      }}>
        {titol}
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {children}
      </div>
    </div>
  )
}

function Fila({ children }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.5rem',
      border: '1px solid var(--border)', borderRadius: 4,
      padding: '0.3rem 0.5rem', background: 'var(--bg-card)',
    }}>
      {children}
    </div>
  )
}

function Buit({ text }) {
  return (
    <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
      {text}
    </p>
  )
}

function BotoEsborra({ onClick, etiqueta }) {
  return (
    <button
      onClick={onClick}
      aria-label={etiqueta}
      style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', flexShrink: 0, padding: 2,
      }}
    >
      <i className="ti ti-trash" />
    </button>
  )
}
