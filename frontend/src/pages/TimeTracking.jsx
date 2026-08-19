import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { modelTasks, timers } from '../api/endpoints'
import Card from '../components/ui/Card'
import {
  darrersDies, diaDelTram, formataMinuts, horaLocal, minutsDelTram, tramObert, tramsDelDia,
} from '../utils/agregaTrams'

/**
 * F2.6 · §S-3 — LA PÀGINA DE TEMPS, REFETA SOBRE ELS CAMPS QUE EXISTEIXEN.
 *
 * Llegia `data_inici`, `data_fi` i `created_at`. Cap dels tres existeix: el serializer emet
 * `inici`, `fi`, `minuts`, `actiu`, `last_heartbeat` i `origen`, i `created_at` no és ni una
 * columna de la taula. `''` mai és igual a la data d'avui, de manera que **la llista del dia i el
 * gràfic de set dies eren buits sempre**: la pàgina ensenyava zero a qui havia treballat vuit
 * hores, i el botó de tancar disparava sobre el primer tram de la llista —normalment ja tancat—
 * i rebia un 400.
 *
 * El botó ja no hi és (F1.7 va jubilar l'endpoint, que tancava trams sense passar per la màquina
 * d'estats). Un tram es tanca amb el **Stop** de l'indicador de sessió, o amb la pausa per
 * inactivitat. Enlloc més: aquesta pàgina MIRA, no toca.
 *
 * L'agregació viu a `utils/agregaTrams` (pura, 14 tests); aquí només hi ha el pintat.
 */

const NOMS_TASCA_CACHE = new Map()

export default function TimeTracking() {
  const { t, i18n } = useTranslation()
  const [trams, setTrams] = useState([])
  const [noms, setNoms] = useState({})
  const [loading, setLoading] = useState(true)
  const [ara, setAra] = useState(() => Date.now())

  const carrega = useCallback(() => {
    setLoading(true)
    // `ordering: '-inici'` — el camp REAL. L'anterior (`-data_inici`) no era a `ordering_fields`
    // i DRF l'ignorava en silenci, cosa que amagava que el nom no existia.
    return timers.list({ page_size: 200, ordering: '-inici' })
      .then(res => {
        const files = res?.data?.results ?? res?.data ?? []
        setTrams(Array.isArray(files) ? files : [])
        return files
      })
      .catch(() => setTrams([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { carrega() }, [carrega])
  useEffect(() => {
    const id = setInterval(() => setAra(Date.now()), 30_000)
    return () => clearInterval(id)
  }, [])

  // El nom de la tasca no ve al tram (el serializer només en porta el codi del model). Es demana
  // una sola vegada per tasca i es memoritza: una pàgina de consulta no pot fer N peticions cada
  // cop que es repinta.
  useEffect(() => {
    const pendents = [...new Set(trams.map(x => x.model_task).filter(Boolean))]
      .filter(id => !NOMS_TASCA_CACHE.has(id))
    if (!pendents.length) { setNoms(Object.fromEntries(NOMS_TASCA_CACHE)); return }
    Promise.all(pendents.map(id => modelTasks.get(id)
      .then(r => NOMS_TASCA_CACHE.set(id, r?.data?.task_type_name || r?.data?.task_type_code || ''))
      .catch(() => NOMS_TASCA_CACHE.set(id, ''))))
      .then(() => setNoms(Object.fromEntries(NOMS_TASCA_CACHE)))
  }, [trams])

  const nomDe = (tram) => noms[tram.model_task] || t('time_tracking.task_n', { n: tram.model_task })
  const obert = tramObert(trams)
  const avui = new Date()
  const delDia = tramsDelDia(trams, diaDelTram({ inici: avui.toISOString() }))
  const dies = darrersDies(trams, 7, avui, ara)
  const totalSetmana = dies.reduce((acc, d) => acc + d.minuts, 0)
  const maxMinuts = Math.max(1, ...dies.map(d => d.minuts))
  const locale = i18n.language === 'es' ? 'es-ES' : i18n.language === 'en' ? 'en-GB' : 'ca-ES'

  // D-2 — la traça que la decisió demana: el temps DECLARAT es distingeix del MESURAT a simple
  // vista. Són la mateixa moneda per al Welford i per a l'albarà, però no la mateixa evidència.
  const PastillaOrigen = ({ tram }) => (
    tram.origen === 'declarat' ? (
      <span style={{
        fontSize: 'var(--fs-caption)', padding: '1px 7px', borderRadius: 999,
        border: '0.5px solid var(--gray-l)', color: 'var(--text-muted)', whiteSpace: 'nowrap',
      }}>
        <i className="ti ti-pencil" style={{ fontSize: 11, marginRight: 4 }} />
        {t('time_tracking.origen_declarat')}
      </span>
    ) : null
  )

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4 }}>
          {t('time_tracking.title')}
        </h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>
          {t('time_tracking.subtitle')}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.2rem', marginBottom: '1.2rem' }}>
        <Card title={t('time_tracking.active_timer')} icon="ti-player-play" padding={0}>
          {loading ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 'var(--fs-body)' }}>
              {t('time_tracking.loading')}
            </div>
          ) : !obert ? (
            <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--gray)', fontSize: 'var(--fs-body)' }}>
              <i className="ti ti-clock-off" style={{ fontSize: 32, display: 'block', marginBottom: 12, color: 'var(--gray-l)' }} />
              {t('time_tracking.no_active_task')}
            </div>
          ) : (
            <div style={{ padding: '1.4rem 1.2rem', textAlign: 'center' }}>
              <div style={{
                fontSize: 'var(--fs-h1)', fontWeight: 500, color: 'var(--gold)',
                fontVariantNumeric: 'tabular-nums',
              }}>
                {formataMinuts(minutsDelTram(obert, ara))}
              </div>
              <div style={{ fontSize: 'var(--fs-body)', marginTop: 6 }}>{nomDe(obert)}</div>
              <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', marginTop: 2 }}>
                {obert.model_task_codi} · {t('time_tracking.des_de', { hora: horaLocal(obert.inici) })}
              </div>
              <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 14 }}>
                {t('time_tracking.tancar_hint')}
              </p>
            </div>
          )}
        </Card>

        <Card title={t('time_tracking.today_entries', { count: delDia.length })} icon="ti-calendar-event" padding={0}>
          {delDia.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--gray)', fontSize: 'var(--fs-body)' }}>
              {t('time_tracking.no_entries_today')}
            </div>
          ) : (
            <div style={{ maxHeight: 260, overflowY: 'auto' }}>
              {delDia.map(entry => (
                <div key={entry.id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10,
                  padding: '0.7rem 1.2rem', borderBottom: '0.5px solid var(--gray-l)',
                  fontSize: 'var(--fs-body)',
                }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ marginBottom: 2, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{ color: 'var(--gold)', fontWeight: 500 }}>
                        {entry.model_task_codi}
                      </span>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{nomDe(entry)}</span>
                      <PastillaOrigen tram={entry} />
                    </div>
                    <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>
                      {horaLocal(entry.inici)} – {horaLocal(entry.fi)}
                    </div>
                  </div>
                  <span style={{ fontWeight: 500, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    {formataMinuts(minutsDelTram(entry, ara))}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title={t('time_tracking.weekly_summary')} icon="ti-chart-bar">
        <div style={{
          display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
          gap: '0.6rem', height: 140, marginBottom: '1rem',
        }}>
          {dies.map(d => (
            <div key={d.clau} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', fontVariantNumeric: 'tabular-nums' }}>
                {d.minuts > 0 ? formataMinuts(d.minuts) : '—'}
              </div>
              <div style={{
                width: '70%', height: `${(d.minuts / maxMinuts) * 100}%`,
                minHeight: d.minuts > 0 ? 4 : 0,
                background: d.minuts > 0 ? 'var(--gold)' : 'var(--gray-l)',
                borderRadius: '4px 4px 0 0', transition: 'height 0.3s',
              }} />
              <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', textTransform: 'capitalize' }}>
                {d.data.toLocaleDateString(locale, { weekday: 'short', day: 'numeric' })}
              </div>
            </div>
          ))}
        </div>
        <div style={{
          borderTop: '0.5px solid var(--gray-l)', paddingTop: '0.8rem',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>
            {t('time_tracking.weekly_total')}
          </span>
          <span style={{
            fontSize: 'var(--fs-h1)', fontWeight: 500, color: 'var(--gold)',
            fontVariantNumeric: 'tabular-nums',
          }}>
            {formataMinuts(totalSetmana)}
          </span>
        </div>
      </Card>
    </div>
  )
}
