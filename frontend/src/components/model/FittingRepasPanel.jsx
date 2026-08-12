import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { fittingRepas } from '../../api/endpoints'
import { buildRepasGroups, buildRepasRows } from './repasGridAdapter'
import PecesDelModel from './PecesDelModel'
import { filesDeLaPeca } from '../../utils/identitatMesura'
import { recompteFittings, tallaDeLaCapcalera } from '../../utils/repasPerPeca'
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
  const groups = buildRepasGroups(sessions, data.talla, data.model?.base_size_label, t)
  const rows = buildRepasRows(data.rows, sessions)

  return (
    <div>
      {/* EL TÍTOL ES QUEDA A FORA perquè nomena LA PANTALLA, i una pantalla no es reparteix.
          El que baixa és el que parla de la FEINA: el recompte i la talla (SET-2/PRED-1). */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 10 }}>
        <h3 style={{ fontFamily: MONO, fontSize: 'var(--fs-h3)', fontWeight: 500, margin: 0 }}>
          {t('fitting.repas.title')}
        </h3>
      </div>
      {/* SET-2/T7-B11 — EL REPÀS AL PATRÓ. `fitting/serializers` emet l'eix des de f6d99e30,
          o sigui que no hi ha cap frontera de dades: cada contenidor es queda les seves línies.
          Aquí no hi ha risc d'escriptura de cap mena —la graella és `editable={false}`— i per
          això entra sense esperar cap porta. */}
      {/* SET-2/PRED-1 — I EL RECOMPTE BAIXA AMB ELLES. Vivia aquí dalt i es calculava sobre el
          MODEL (`sessions.filter(...)`): al 1320 deia «2 sessions fetes» damunt de dos
          contenidors on cap prenda n'ensenyava dues (1 i 1). Les sessions segueixen sent del
          model —una convocatòria convoca el model sencer, D6— i el que es parteix és QUÈ
          N'ENSENYA CADA PRENDA. La llei viu a `utils/repasPerPeca` amb banc: ja hem perdut una
          vegada una llei que només existia com a expressió enmig d'un JSX (B2b). */}
      <PecesDelModel model={model}>{peca => {
      const eix = peca ? (peca.codi || '') : null
      const filesDelContenidor = filesDeLaPeca(rows, eix)
      // ⚠️ EL RECOMPTE ES FA SOBRE LES FILES CRUES, no sobre les adaptades. `buildRepasRows`
      // projecta `valors` a `cells.repas.history` per a la graella i el camp original ja no hi
      // és: passar-li `rows` retorna 0 sense petar, que és el pitjor error possible en un
      // número. Ho va caçar l'arnès (P3: pantalla=0 · payload=1) i per això la línia diu quines
      // files són amb el nom de la variable.
      const filesCrues = filesDeLaPeca(data.rows || [], eix)
      const n = recompteFittings(filesCrues, sessions)
      const talla = tallaDeLaCapcalera(data.talla, peca)
      return (<>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap',
                      margin: '0 0 8px', fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>
          <span>
            {/* PLURAL DE DEBÒ (`count_one`/`count_other`, com `n_punts` a la Comprovació). El
                rètol deia sempre el total del model, que en un model amb fittings mai era 1;
                partit per prenda, l'1 passa a ser el cas normal i «1 sessions fetes» es llegia
                a la primera captura. La variable ha de dir-se `count`: és la que i18next mira
                per triar la forma. */}
            {t('fitting.repas.count', { count: n })}
            {talla.talla && ` · ${t('fitting.repas.size', { talla: talla.talla })}`}
          </span>
          {/* ⚠️ EL SEGON PREDICAT DE MODEL D'AQUESTA PANTALLA, DIT I NO AMAGAT. El backend
              resol UNA talla per a tota la vista (la del model) i filtra les línies per ella;
              una prenda pot declarar la seva pròpia base. Quan divergeixen, el que NO es pot
              fer és pintar la base de la prenda al rètol: les files que es veuen són les de la
              talla de la vista, i canviar només el rètol faria la mentida més convincent. Es
              diu, com la Comprovació diu les seves `limitacions`. */}
          {talla.divergeix && (
            <span style={{ fontStyle: 'italic', color: 'var(--warn-ink)' }}>
              {t('fitting.repas.talla_divergent', { propia: talla.propia })}
            </span>
          )}
        </div>
        <MeasureGrid rows={filesDelContenidor} groups={groups} editable={false}
          empty={<p style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>{t('fitting.repas.empty')}</p>} />
      </>)
      }}</PecesDelModel>
    </div>
  )
}
