import { useTranslation } from 'react-i18next'

/**
 * POMS DEL MODEL — la LLISTA DE TREBALL del taller (W3).
 *
 * No és el catàleg global de POMs: són les Mesures d'AQUEST model, les que la fitxa ja
 * dona per bones. **Els POMs no es busquen: es col·loquen.** Una fila PENDENT és un botó:
 * clicar-la entra al mode de col·locació D'AQUELL POM, i el canvas guia (punt A → punt B).
 * Cap cercador pel mig — el cercador de catàleg queda com a acció secundària, per al POM
 * que no és a la fitxa.
 *
 * Una fila COL·LOCADA ensenya el que això persegueix: què deia la fitxa, què mesura el
 * patró, i la diferència. La tolerància només pinta l'estat quan n'hi ha: sense tolerància
 * es dona la xifra i no es jutja.
 *
 * NOMENCLATURA (convenció de la casa): el codi de client mana i el nom va a sota, en gris.
 */
export default function ModelPomList({ files, pomActiu, onColocar, onAfegirFora }) {
  const { t } = useTranslation()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {files.length === 0 ? (
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
          {t('pattern.taller.model_poms_empty')}
        </p>
      ) : files.map(f => (
        <Fila
          key={f.base_measurement} t={t} f={f}
          actiu={pomActiu?.base_measurement === f.base_measurement}
          onColocar={() => onColocar(f)}
        />
      ))}

      {/* Via SECUNDÀRIA: el POM que no és a la fitxa. Existeix (algú vol mesurar una cosa
          que la fitxa no demana), però no mana la pantalla: la feina és la llista. */}
      <button
        onClick={onAfegirFora}
        style={{
          marginTop: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.35rem',
          background: 'none', border: '1px dashed var(--border)', borderRadius: 4,
          padding: '0.35rem 0.6rem', cursor: 'pointer',
          fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
        }}
      >
        <i className="ti ti-plus" />
        {t('pattern.taller.pom_outside')}
      </button>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

function Fila({ t, f, actiu, onColocar }) {
  const colocat = f.ancorat

  // L'estat de la Δ: només es jutja si es POT jutjar. `dins_tolerancia` ve a null quan la
  // fitxa no dona valor (plantilla sense mesura) — llavors hi ha xifra, però no veredicte.
  const estat = f.dins_tolerancia == null ? null : f.dins_tolerancia
  const colorDelta = estat == null ? 'var(--text-main)'
    : estat ? 'var(--ok)' : 'var(--err)'

  return (
    <button
      onClick={colocat ? undefined : onColocar}
      disabled={colocat}
      aria-pressed={actiu}
      title={colocat ? undefined : t('pattern.taller.pom_place_hint', { codi: f.codi_client })}
      style={{
        textAlign: 'left', width: '100%',
        cursor: colocat ? 'default' : 'pointer',
        background: actiu ? 'var(--gold-pale)' : 'var(--bg-card)',
        border: `1px solid ${actiu ? 'var(--gold)' : 'var(--border)'}`,
        borderLeft: `3px solid ${colocat ? 'var(--ok)' : actiu ? 'var(--gold)' : 'var(--border)'}`,
        borderRadius: 4, padding: '0.3rem 0.5rem',
        display: 'flex', alignItems: 'center', gap: '0.5rem',
      }}
    >
      <i
        className={`ti ${colocat ? 'ti-circle-check' : actiu ? 'ti-crosshair' : 'ti-circle-dashed'}`}
        style={{ color: colocat ? 'var(--ok)' : actiu ? 'var(--gold)' : 'var(--text-muted)',
                 flexShrink: 0 }}
      />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          display: 'flex', alignItems: 'baseline', gap: '0.35rem',
          fontSize: 'var(--fs-body)', fontWeight: 600,
        }}>
          <span style={{ fontFamily: 'var(--mono)' }}>{f.codi_client}</span>
          {/* La nomenclatura de la fletxa al croquis: és com el patronista l'anomena al
              dibuix, i per això va al costat del codi i no amagada al detall. */}
          {f.nom_fitxa && (
            <span style={{
              fontSize: 'var(--fs-caption)', fontWeight: 400, color: 'var(--text-muted)',
              border: '1px solid var(--border)', borderRadius: 8, padding: '0 5px',
            }}>
              {f.nom_fitxa}
            </span>
          )}
        </div>
        <div style={{
          fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {f.nom_client || f.nom_canonic}
          {colocat ? ` · ${f.peca}` : ''}
        </div>
      </div>

      <div style={{
        textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 'var(--fs-caption)',
        flexShrink: 0, lineHeight: 1.35,
      }}>
        <div style={{ color: 'var(--text-muted)' }}>
          {f.valor_fitxa_cm != null
            ? t('pattern.taller.value_sheet', { cm: f.valor_fitxa_cm })
            : t('pattern.taller.value_sheet_none')}
        </div>
        {colocat && (
          <div style={{ color: colorDelta, fontWeight: 600 }}>
            {f.valor_mesurat_cm == null
              ? t('pattern.pom_unmeasured')
              : f.delta_cm == null
                ? t('pattern.taller.value_pattern', { cm: f.valor_mesurat_cm })
                : t('pattern.taller.value_delta', {
                    cm: f.valor_mesurat_cm, delta: signe(f.delta_cm),
                  })}
          </div>
        )}
      </div>
    </button>
  )
}

// La Δ es llegeix amb el signe SEMPRE: «+0.4» i «−0.4» diuen coses oposades al patronista,
// i un «0.4» a seques no diu cap de les dues.
const signe = (d) => (d > 0 ? `+${d}` : `${d}`)
