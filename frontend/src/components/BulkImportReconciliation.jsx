import { useTranslation } from 'react-i18next'
import Badge from './ui/Badge'

// Conciliació de l'import massiu (IMPORT-2): el sistema ENSENYA el que ha entès de cada
// cel·la i espera confirmació — mai endevina en silenci. Una fila per model, una columna per
// camp mapat, i el codi_intern que ocuparà amb el seu estat de col·lisió.
// Mateixa família d'UX que el wizard de diccionari (proposta + badge), cap invent nou.
const MONO = 'IBM Plex Mono, monospace'

// El codi de colors de la casa. NORMALITZAT = groc: s'ha fet, i es veu què s'ha fet.
const CELL = {
  MATCH: { background: 'var(--ok-bg)', color: 'var(--ok)' },
  NORMALITZAT: { background: 'var(--warn-bg)', color: 'var(--warn)' },
  NO_MATCH: { background: 'var(--err-bg)', color: 'var(--err)' },
  BUIT: { background: 'transparent', color: 'var(--gray)' },
}
const ESTAT_VARIANT = { OK: 'ok', AVIS: 'warn', ERROR: 'err', DUPLICAT: 'gray' }

const CAMPS = ['familia', 'tipus', 'target', 'construccio', 'temporada', 'any',
  'run_talles', 'talla_base', 'es_conjunt']

export default function BulkImportReconciliation({ rec }) {
  const { t } = useTranslation()
  const resum = rec?.resum || {}
  const files = rec?.files || []
  const ocupats = resum.codis_ocupats || 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Resum de capçalera: "18 files netes · 2 amb avisos · 0 bloquejades" */}
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'center', fontSize: 'var(--fs-body)' }}>
        <span><Badge variant="ok">{resum.netes ?? 0}</Badge> {t('bulk_import.rec_netes')}</span>
        <span><Badge variant="warn">{resum.avisos ?? 0}</Badge> {t('bulk_import.rec_avisos')}</span>
        <span><Badge variant="err">{resum.bloquejades ?? 0}</Badge> {t('bulk_import.rec_bloquejades')}</span>
        <span style={{ marginLeft: 'auto', color: ocupats ? 'var(--err)' : 'var(--ok)', fontFamily: MONO }}>
          <i className={`ti ti-${ocupats ? 'alert-triangle' : 'circle-check'}`} />{' '}
          {ocupats
            ? t('bulk_import.rec_codis_ocupats', { n: ocupats })
            : t('bulk_import.rec_codis_lliures', { n: resum.codis_previstos ?? 0 })}
        </span>
      </div>

      {ocupats > 0 && (
        <div style={{ padding: '10px 12px', borderRadius: 8, background: 'var(--err-bg)', color: 'var(--err)', fontSize: 'var(--fs-body)' }}>
          {t('bulk_import.rec_colisio_avis')}
        </div>
      )}

      {/* Taula files × camps. Scroll horitzontal propi: 9 camps + codi no caben en un mòbil. */}
      <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 10, overflow: 'auto', maxHeight: 420 }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', fontFamily: MONO, fontSize: 'var(--fs-label)' }}>
          <thead>
            <tr>
              <th style={th} title={t('bulk_import.rec_col_incloure_hint')}>{t('bulk_import.rec_col_incloure')}</th>
              <th style={th}>{t('bulk_import.col_row')}</th>
              <th style={th}>{t('bulk_import.col_nom')}</th>
              <th style={th}>{t('bulk_import.rec_col_codi')}</th>
              {CAMPS.map(c => <th key={c} style={th}>{t(`bulk_import.camp_${c}`)}</th>)}
            </tr>
          </thead>
          <tbody>
            {files.length === 0 ? (
              <tr><td colSpan={4 + CAMPS.length} style={{ ...td, textAlign: 'center', color: 'var(--gray)' }}>
                {t('bulk_import.no_rows')}
              </td></tr>
            ) : files.map(f => {
              const inclosa = f.estat === 'OK' || f.estat === 'AVIS'
              return (
                <tr key={f.row_num}>
                  {/* Checkbox = indicador d'estat, no un control: qui decideix què entra és
                      l'estat de la fila. No prometem una selecció que el commit no honora. */}
                  <td style={{ ...td, textAlign: 'center' }}>
                    <input type="checkbox" checked={inclosa} disabled readOnly
                      title={inclosa ? t('bulk_import.rec_inclosa') : (f.motius || []).join(' · ')} />
                  </td>
                  <td style={td}>{f.row_num}</td>
                  <td style={td}>
                    <div>{f.nom || '—'}</div>
                    <Badge variant={ESTAT_VARIANT[f.estat] || 'gray'}>{t(`bulk_import.estat_${f.estat}`)}</Badge>
                    {!inclosa && (f.motius || []).length > 0 && (
                      <div style={{ color: 'var(--err)', fontSize: 'var(--fs-caption)', marginTop: 3, maxWidth: 220, whiteSpace: 'normal' }}>
                        {f.motius.join(' · ')}
                      </div>
                    )}
                  </td>
                  <td style={td}>
                    {f.complementa ? (
                      <span style={{ color: 'var(--warn)' }} title={t('bulk_import.rec_complementa_hint')}>
                        {f.complementa}
                      </span>
                    ) : f.codi_previst ? (
                      <span style={{ color: f.codi_lliure ? 'var(--ok)' : 'var(--err)', fontWeight: 600 }}
                        title={f.codi_lliure ? t('bulk_import.rec_codi_lliure') : t('bulk_import.rec_codi_ocupat')}>
                        {f.codi_previst}
                        {!f.codi_lliure && <i className="ti ti-alert-triangle" style={{ marginLeft: 4 }} />}
                      </span>
                    ) : <span style={{ color: 'var(--gray)' }}>—</span>}
                  </td>
                  {CAMPS.map(camp => (
                    <Cell key={camp} camp={camp} c={(f.camps || []).find(x => x.camp === camp)} t={t} />
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Llegenda t={t} />
    </div>
  )
}

// Una cel·la conciliada. NORMALITZAT ensenya "abans → després": el tècnic veu la
// transformació ARA, no la descobreix quan ja s'ha escrit.
function Cell({ camp, c, t }) {
  if (!c) return <td style={td}>—</td>
  const style = { ...td, ...CELL[c.estat], whiteSpace: 'nowrap' }
  const resolt = camp === 'es_conjunt' && c.valor_resolt
    ? t(c.valor_resolt === 'SI' ? 'bulk_import.rec_si' : 'bulk_import.rec_no')
    : c.valor_resolt

  if (c.estat === 'BUIT') return <td style={style}>—</td>

  if (c.estat === 'NO_MATCH') {
    return (
      <td style={style} title={c.motiu || ''}>
        <div style={{ textDecoration: 'line-through' }}>{c.valor_fitxer}</div>
        <div style={{ fontSize: 'var(--fs-caption)', whiteSpace: 'normal', maxWidth: 200 }}>{c.motiu}</div>
      </td>
    )
  }

  if (c.estat === 'NORMALITZAT') {
    return (
      <td style={style} title={c.candidat?.nom || ''}>
        <span style={{ color: 'var(--gray)' }}>{c.valor_fitxer}</span>
        <span style={{ margin: '0 4px' }}>→</span>
        <strong>{resolt}</strong>
      </td>
    )
  }

  return <td style={style} title={c.candidat?.nom || ''}>{resolt || '—'}</td>
}

function Llegenda({ t }) {
  const items = [
    ['MATCH', 'rec_llegenda_match'], ['NORMALITZAT', 'rec_llegenda_normalitzat'],
    ['NO_MATCH', 'rec_llegenda_no_match'], ['BUIT', 'rec_llegenda_buit'],
  ]
  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 'var(--fs-caption)', color: 'var(--gray)' }}>
      {items.map(([estat, key]) => (
        <span key={estat} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 12, height: 12, borderRadius: 3, border: '0.5px solid var(--gray-l)', ...CELL[estat] }} />
          {t(`bulk_import.${key}`)}
        </span>
      ))}
    </div>
  )
}

const th = {
  textAlign: 'left', padding: '8px 10px', borderBottom: '0.5px solid var(--gray-l)',
  position: 'sticky', top: 0, background: 'var(--white)', color: 'var(--gray)',
  fontWeight: 400, textTransform: 'uppercase', fontSize: 'var(--fs-caption)', whiteSpace: 'nowrap',
}
const td = { padding: '7px 10px', borderBottom: '0.5px solid var(--gray-l)', verticalAlign: 'top' }
