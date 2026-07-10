import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { dataCurta, iconaDe, midaLlegible } from './fileMeta'

// Vista Finder de fitxers (S03c · C4). Subcomponent COMPARTIT: el fan servir l'AssetNavigator
// (els dos mons: fitxers de model i de catàleg) i la secció Fitxers de GarmentTypes (D21).
//
// És presentacional: rep una llista ja carregada i NO sap res d'endpoints ni d'accions de domini.
// Qui el munta decideix què vol dir "seleccionar" (inserir, usar-al-model, només mirar).
//
// L'ordenació és CLIENT-SIDE a propòsit: cap dels dos ViewSets d'origen exposa OrderingFilter
// per `nom_fitxer` ni per `tipus` (només `data_pujada`), i les llistes són curtes — un fitxer
// viu penja d'UN model o d'UN item, no del tenant sencer.

const MONO = 'IBM Plex Mono, monospace'

const COLS = ['nom', 'tipus', 'data']

export default function FileList({ files, selectedId, onSelect, onOpen, emptyLabel }) {
  const { t } = useTranslation()
  const [sort, setSort] = useState({ col: 'data', asc: false })

  const ordenats = useMemo(() => {
    const clau = {
      nom: (f) => (f.nom_fitxer || '').toLowerCase(),
      tipus: (f) => f.tipus || '',
      data: (f) => f.data_pujada || '',
    }[sort.col]
    return [...(files || [])].sort((a, b) => {
      const x = clau(a); const y = clau(b)
      if (x === y) return 0
      return (x > y ? 1 : -1) * (sort.asc ? 1 : -1)
    })
  }, [files, sort])

  const capçalera = (col) => (
    <button key={col} type="button" onClick={() => setSort(s => ({ col, asc: s.col === col ? !s.asc : true }))}
      style={{
        background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: MONO,
        fontSize: 'var(--fs-caption)', textTransform: 'uppercase', letterSpacing: '0.05em',
        color: sort.col === col ? 'var(--gold)' : 'var(--text-muted)', padding: 0,
        display: 'inline-flex', alignItems: 'center', gap: 3,
      }}>
      {t(`asset_navigator.col_${col}`)}
      {sort.col === col && <i className={`ti ti-chevron-${sort.asc ? 'up' : 'down'}`} aria-hidden="true" />}
    </button>
  )

  if (!files) {
    return <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('app.loading')}</div>
  }
  if (!files.length) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)', fontStyle: 'italic' }}>
        {emptyLabel || t('asset_navigator.no_files')}
      </div>
    )
  }

  return (
    <div>
      <div style={{
        display: 'flex', gap: 14, padding: '6px 10px', borderBottom: '0.5px solid var(--border)',
        position: 'sticky', top: 0, background: 'var(--white)', zIndex: 1,
      }}>
        {COLS.map(capçalera)}
      </div>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {ordenats.map(f => {
          const actiu = f.id === selectedId
          return (
            <li key={f.id}>
              <button type="button"
                onClick={() => onSelect?.(f)}
                onDoubleClick={() => onOpen?.(f)}
                aria-current={actiu || undefined}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 10, textAlign: 'left',
                  padding: '8px 10px', border: 'none', cursor: 'pointer', fontFamily: MONO,
                  background: actiu ? 'var(--gold-pale)' : 'transparent',
                  borderBottom: '0.5px solid var(--border)',
                }}>
                <i className={`ti ${iconaDe(f.nom_fitxer)}`} aria-hidden="true"
                  style={{ fontSize: 16, color: actiu ? 'var(--gold)' : 'var(--text-muted)', flexShrink: 0 }} />
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span style={{
                    display: 'block', fontSize: 'var(--fs-body)', color: 'var(--text-main)',
                    fontWeight: actiu ? 600 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>{f.nom_fitxer}</span>
                  {/* Procedència (C2.4). Nomes ModelFitxer porta `derivat_de_label`; un ItemFitxer
                      no te origen: es la font. Per aixo la linia apareix o no, sense placeholder. */}
                  {f.derivat_de_label && (
                    <span style={{ display: 'block', fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 1 }}>
                      <i className="ti ti-arrow-narrow-right" aria-hidden="true" style={{ marginRight: 3 }} />
                      {t('asset_navigator.derived_from', { origen: f.derivat_de_label })}
                    </span>
                  )}
                </span>
                <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', width: 90, flexShrink: 0 }}>{f.tipus}</span>
                <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', width: 56, flexShrink: 0, textAlign: 'right' }}>{midaLlegible(f.mida_bytes)}</span>
                <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', width: 68, flexShrink: 0, textAlign: 'right' }}>{dataCurta(f.data_pujada)}</span>
                <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', width: 34, flexShrink: 0, textAlign: 'right' }}>v{f.versio}</span>
                <span style={{
                  fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', width: 96, flexShrink: 0,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>{f.pujat_per_nom || '—'}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
