import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { fittingRepas } from '../../api/endpoints'
import { buildRepasGroups, buildRepasRows } from './repasGridAdapter'
import PecesDelModel from './PecesDelModel'
import { filesDeLaPeca } from '../../utils/identitatMesura'
import MeasureGrid from './MeasureGrid'

// REPÀS de fittings del model — la superfície de tornar-hi.
//
// Fer un fitting ja té casa (l'editor G1, dins Mesures en mode treball). Repassar-los no en tenia:
// cada sessió es tancava i els comentaris que el tècnic hi deixava quedaven dins la sessió. Aquí
// totes les sessions fetes es posen en columnes cronològiques sobre la MATEIXA anatomia de la taula
// de mesures (MeasureGrid: POM × columnes, capçalera tipus + @data), amb els comentaris a la vista.
//
// LECTURA TOTAL: cap edició, cap autosave, cap acció. Qui vulgui canviar un valor va a la sessió.

const MONO = 'IBM Plex Mono, monospace'

export default function FittingRepasPanel({ model }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let viu = true
    setLoading(true)
    fittingRepas.get(model.id)
      .then(r => { if (viu) setData(r.data) })
      .catch(() => { if (viu) setData(null) })
      .finally(() => { if (viu) setLoading(false) })
    return () => { viu = false }
  }, [model.id])

  if (loading) {
    return <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('common.loading')}</div>
  }

  const sessions = data?.sessions || []
  if (!sessions.length) {
    // Sense CAP columna no hi ha res a repassar, però el motiu no és sempre el mateix: un model
    // sense mesures i un model amb mesures i cap fitting són dues situacions diferents, i des que
    // la primera columna és l'ENTRADA DE POMs (B2) el segon cas ja no arriba mai aquí.
    return (
      <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)', padding: '8px 0' }}>
        {t((data?.rows || []).length ? 'fitting.repas.no_sessions' : 'fitting.repas.empty_all')}
      </div>
    )
  }
  // El recompte és de FITTINGS, i la columna d'entrada no n'és cap: és d'on es parteix.
  const nFittings = sessions.filter(s => s.origen !== 'ENTRADA').length

  const groups = buildRepasGroups(sessions, data.talla, data.model?.base_size_label, t)
  const rows = buildRepasRows(data.rows, sessions)

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 10 }}>
        <h3 style={{ fontFamily: MONO, fontSize: 'var(--fs-h3)', fontWeight: 500, margin: 0 }}>
          {t('fitting.repas.title')}
        </h3>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>
          {t('fitting.repas.count', { n: nFittings })}
          {data.talla && ` · ${t('fitting.repas.size', { talla: data.talla })}`}
        </span>
      </div>
      {/* SET-2/T7-B11 — EL REPÀS AL PATRÓ. `fitting/serializers` emet l'eix des de f6d99e30,
          o sigui que no hi ha cap frontera de dades: cada contenidor es queda les seves línies.
          Aquí no hi ha risc d'escriptura de cap mena —la graella és `editable={false}`— i per
          això entra sense esperar cap porta. */}
      <PecesDelModel model={model}>{peca => {
      const filesDelContenidor = filesDeLaPeca(rows, peca ? (peca.codi || '') : null)
      return (
        <MeasureGrid rows={filesDelContenidor} groups={groups} editable={false}
          empty={<p style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('fitting.repas.empty')}</p>} />
      )
      }}</PecesDelModel>
    </div>
  )
}
