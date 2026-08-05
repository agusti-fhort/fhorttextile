import { useTranslation } from 'react-i18next'

/**
 * F2.7 · RONDA — «aquest model ja ha donat el que havia de donar».
 *
 * Lliurable vol dir que TOTES les tasques `es_lliurable` de la volta són Done: els PRODUCTES
 * (fitxa, patró) hi són. No vol dir que la volta estigui tancada — el POM pot seguir obert i
 * això segueix sent cert.
 *
 * Només ENSENYA el fet. Notificar activament (correu, push) és una decisió a part que aquest
 * sprint no pren: el PM ho veu quan mira, que és el que s'ha demanat.
 *
 * `compacte` per a la llista de models (una pastilla dins d'una fila) i complet per a la fitxa.
 */
export default function BadgeLliurable({ rondes, compacte = false, locale = 'ca-ES' }) {
  const { t } = useTranslation()
  if (!rondes?.length) return null

  // La més recent mana: és la que el PM ha d'actuar. L'històric va a sota, a la fitxa.
  const ultima = rondes[rondes.length - 1]
  const data = ultima.lliurat_el
    ? new Date(ultima.lliurat_el).toLocaleDateString(locale, { day: 'numeric', month: 'short' })
    : null

  const pastilla = {
    display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
    fontFamily: 'IBM Plex Mono, monospace', borderRadius: 999,
    border: '0.5px solid var(--ok)', color: 'var(--ok)', background: 'var(--ok-bg)',
    padding: compacte ? '1px 8px' : '3px 11px',
    fontSize: compacte ? 'var(--fs-caption)' : 'var(--fs-label)',
  }

  if (compacte) {
    return (
      <span style={pastilla} title={t('lliurable.badge_titol', { n: ultima.seq })}>
        <i className="ti ti-package-export" style={{ fontSize: 12 }} />
        {t('lliurable.compacte', { n: ultima.seq })}
      </span>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
      <span style={pastilla}>
        <i className="ti ti-package-export" style={{ fontSize: 14 }} />
        {t('lliurable.badge', { n: ultima.seq })}
        {data && <span style={{ opacity: 0.75 }}>· {data}</span>}
      </span>
      {/* L'HISTÒRIC: la genealogia que F1 va crear, feta visible. Amb dues voltes o més, saber
          només l'última no explica res — el PM vol veure que ja se n'han lliurat tres. */}
      {rondes.length > 1 && (
        <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                       fontFamily: 'IBM Plex Mono, monospace' }}>
          {t('lliurable.historic', {
            llista: rondes.map(r => t(`lliurable.motiu_${r.motiu}`, { n: r.seq })).join(' · '),
          })}
        </span>
      )}
    </div>
  )
}
