import { useTranslation } from 'react-i18next'

/**
 * POMS DEL MODEL — la llista de treball del taller (v1 d'esquelet, NOMÉS lectura).
 *
 * No és el catàleg global de POMs: són les Mesures d'AQUEST model (BaseMeasurement), les
 * que la fitxa ja dona per bones. La idea del disseny és que els POMs no es BUSQUIN sinó
 * que es COL·LOQUIN: aquí es veu què queda per ancorar i què ja ho està, i amb quin valor.
 * El flux de col·locació (clicar una fila i marcar-la al canvas) és W3; aquí encara es
 * marca amb el botó "Marcar POM" de sempre.
 *
 * NOMENCLATURA (convenció de la casa): el codi de client mana i el nom va a sota, en gris.
 */
export default function ModelPomList({ mesures, ancorats }) {
  const { t } = useTranslation()

  if (mesures.length === 0) {
    return (
      <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', margin: 0 }}>
        {t('pattern.taller.model_poms_empty')}
      </p>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {mesures.map(m => {
        const anc = ancorats.get(m.pom_id)
        return (
          <div
            key={m.id}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              border: '1px solid var(--border)', borderRadius: 4,
              borderLeft: `3px solid ${anc ? 'var(--ok)' : 'var(--border)'}`,
              padding: '0.3rem 0.5rem', background: 'var(--bg-card)',
            }}
          >
            <i
              className={`ti ${anc ? 'ti-circle-check' : 'ti-circle-dashed'}`}
              title={anc ? t('pattern.taller.pom_anchored') : t('pattern.taller.pom_pending')}
              style={{ color: anc ? 'var(--ok)' : 'var(--text-muted)', flexShrink: 0 }}
            />

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                display: 'flex', alignItems: 'baseline', gap: '0.35rem',
                fontSize: 'var(--fs-body)', fontWeight: 600,
              }}>
                <span style={{ fontFamily: 'var(--mono)' }}>{m.codi_client}</span>
                {/* La nomenclatura de la fletxa al croquis: és com el patronista l'anomena
                    al dibuix, i per això va al costat del codi i no amagada al detall. */}
                {m.nom_fitxa && (
                  <span style={{
                    fontSize: 'var(--fs-caption)', fontWeight: 400,
                    color: 'var(--text-muted)', border: '1px solid var(--border)',
                    borderRadius: 8, padding: '0 5px',
                  }}>
                    {m.nom_fitxa}
                  </span>
                )}
              </div>
              <div style={{
                fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {m.nom_client || m.nom_ca}
                {anc ? ` · ${anc.peca}` : ''}
              </div>
            </div>

            {/* Valor de FITXA i, si el POM ja està ancorat, el valor MESURAT al patró.
                Els dos junts: la comparació és tota la gràcia de tenir-los a la mateixa
                fila. Quadrar-los (toleràncies, desviament) és feina de W3. */}
            <div style={{
              textAlign: 'right', fontFamily: 'var(--mono)',
              fontSize: 'var(--fs-caption)', flexShrink: 0,
            }}>
              <div style={{ color: 'var(--text-muted)' }}>
                {m.base_value_cm != null
                  ? t('pattern.taller.value_sheet', { cm: m.base_value_cm })
                  : '—'}
              </div>
              {anc && (
                <div style={{
                  color: anc.valor_mesurat_cm == null ? 'var(--err)' : 'var(--text-main)',
                  fontWeight: 600,
                }}>
                  {anc.valor_mesurat_cm != null
                    ? t('pattern.taller.value_pattern', { cm: anc.valor_mesurat_cm })
                    : t('pattern.pom_unmeasured')}
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
