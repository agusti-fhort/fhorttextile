import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { IconAlertTriangle, IconLock } from '@tabler/icons-react'
import client from '../api/client'
import { models } from '../api/endpoints'
import MeasureGrid from '../components/model/MeasureGrid'
import PecesDelModel from '../components/model/PecesDelModel'
import { filesDeLaPeca } from '../utils/identitatMesura'
import { buildEscalatGroups, buildEscalatRows, escalatRuleLeadCols } from '../components/model/fittingGridAdapter'
import { mesuraSemblaIncrement } from '../utils/plausibilitatMesura'
import { formatLen } from '../utils/format'
import { useUnit } from './fittingShared'

// ESCALAT — editor de la taula propagada del model (totes les talles) sobre l'editor únic MeasureGrid,
// CONVERGIT amb el fitting: totes les talles editables (base inclosa) i editar una cel·la PROPAGA per
// regla a les germanes (endpoint escalat/ajustar-talla → propaga_ancoratges, com piece-fitting-lines/
// propagar). El règim per POM es canvia amb setPomRegim. S'alimenta de taula-mesures (UNA taula vigent
// neta; LLEI: propagar = llenç net, no eix de versions). Versionar és l'acte conscient "Propagar a
// grading" a MESURES, no aquí.
export default function PropagatedEditor({ modelId, onClose, inline = false, readOnly = false }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [modelInfo, setModelInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [reloadKey, setReloadKey] = useState(0)   // remunta MeasureGrid en canvi de règim (re-sembra)
  const [sealed, setSealed] = useState(null)      // payload del 409 {version_number, sortida, ...}
  const [bumping, setBumping] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    return client.get(`/api/v1/models/${modelId}/taula-mesures/`)
      .then(res => setData(res.data))
      .catch(() => setErr(t('model_measurements.propagated_load_err')))
      .finally(() => setLoading(false))
  }, [modelId, t])

  useEffect(() => { load() }, [load])
  // Identitat de model per al contenidor de peça (dependència, joc de regles i run).
  useEffect(() => { models.get(modelId).then(r => setModelInfo(r.data)).catch(() => {}) }, [modelId])

  const base = (data?.base_size || '').trim()
  // Identitat estable: `data?.size_run || []` fabricava un array nou a cada render i feia recalcular
  // els useMemo de sota sempre (i el linter ho canta).
  const sizes = useMemo(() => data?.size_run || [], [data])
  const gridGroups = buildEscalatGroups(sizes, base, t)
  const gridRows = useMemo(
    () => buildEscalatRows(data?.rows || [], sizes, base),
    [data, sizes, base])

  // Índex per lineId → {vigent, base} de la fila. El fan servir les dues guardes de sota, i és
  // l'única lectura de l'estat que necessiten (cap dada nova del backend).
  const perLinia = useMemo(() => {
    const m = new Map()
    for (const r of gridRows) {
      for (const s of sizes) {
        const a = r.cells?.[s]?.active
        // C4/BLOC 3 — hi entra el `pom_id` (i els eixos) perquè l'escriptura no hagi de
        // desmuntar el lineId: la fila ja sap qui és, i el mapa ja la té localitzada.
        if (a) m.set(a.lineId, { vigent: a.value, base: r.base_value_cm, codi: r.codi, talla: s,
                                 pom_id: r.pom_id, capa: r.capa, instancia: r.instancia,
                                 garment: r.garment })
      }
    }
    return m
  }, [gridRows, sizes])

  // La pregunta de plausibilitat viva: {lineId, valor, base, codi, talla, resolt}. Mai un bloqueig.
  const [confirmPlaus, setConfirmPlaus] = useState(null)
  const confirmRef = useRef(null)

  // L'escriptura de debò, un cop passades les guardes.
  const desa = useCallback((lineId, value) => {
    // C4/BLOC 3 — el POM i la talla surten del `perLinia`, NO de trossejar el lineId. La
    // primera meitat del lineId ha passat a ser la clau sencera de la mesura
    // (`{pom}|{capa}|{inst}`), i el `Number(...)` que hi havia n'hauria tret `NaN`: la crida
    // se n'aniria a `/escalat/NaN/ajustar-talla/` i cada cel·la de l'Escalat deixaria de desar.
    // Llegir-ho del mapa, a més, treu del mig la pregunta de com es desmunta una clau: la fila
    // ja porta els camps per separat, que és el que `pom/identitat.py` demana que es faci.
    const info = perLinia.get(lineId)
    if (!info) return Promise.resolve()
    // S42/F1 — I LA PEÇA, que aquesta funció ja tenia a la mà. `perLinia` carrega
    // `garment: r.garment` (25 línies més amunt) i la crida n'enviava DOS DE TRES: la junta
    // era aquesta línia, no la dada. Sense l'eix, el backend resolia la fila per una clau de
    // dues columnes i, amb la mare i la 02 compartint POM, casava amb DUES → 500.
    return models.escalatAjustarTalla(modelId, info.pom_id, info.talla, value,
                                      { capa: info.capa, instancia: info.instancia,
                                        garment: info.garment })
      .catch(e => {
        // G6-B/T3 — la versió vigent està SEGELLADA: el backend refusa l'escriptura (409). Sense
        // això, el rebuig arribaria com un error mut i el tècnic no sabria ni per què no es desa
        // ni què pot fer. El 409 ja porta la sortida; aquí només es fa visible.
        if (e?.response?.status === 409 && e.response.data?.error === 'sealed') {
          setSealed(e.response.data)
        }
        throw e   // MeasureGrid ha de saber igualment que la cel·la NO s'ha desat.
      })
  }, [modelId, perLinia])

  // Escriptura per talla (convergit amb el fitting): ancora la talla i PROPAGA per regla a les germanes.
  // Retorna l'axios promise; MeasureGrid llegeix res.data.linies i refresca la fila (germanes + base).
  const onGridSave = useCallback((lineId, value) => {
    if (value == null) return Promise.resolve()
    const info = perLinia.get(lineId)

    // GUARDA-RAIL — escriure el valor que la cel·la JA té és un NO-OP: ni crida. FIX-1 fa que
    // reescriure el vigent torni la mateixa corba, però la crida que no es fa no es pot equivocar
    // mai, i estalvia una re-derivació sencera del grading per un teclejat sense conseqüència.
    if (info && info.vigent !== '' && info.vigent != null
        && Number(info.vigent) === Number(value)) {
      return Promise.resolve()
    }

    // FIX-4 — GUARDA DE PLAUSIBILITAT, en DESAR (mai en teclejar: interrompre a cada tecla faria
    // impossible escriure «1» abans de «16»). Pregunta, no bloqueja: el «sí» desa amb normalitat.
    if (info && mesuraSemblaIncrement(value, info.base)) {
      return new Promise((resolve, reject) => {
        confirmRef.current = { resolve, reject }
        setConfirmPlaus({ lineId, valor: value, base: info.base, codi: info.codi, talla: info.talla })
      })
    }

    return desa(lineId, value)
  }, [perLinia, desa])

  // «Desar igualment» → l'escriptura normal. Cancel·lar → cap escriptura i la cel·la torna al seu
  // valor desat (remuntatge de la graella): que no quedi a la pantalla un número que no és a la BD.
  const resolPlaus = useCallback((desaIgualment) => {
    const pend = confirmPlaus
    const cb = confirmRef.current
    confirmRef.current = null
    setConfirmPlaus(null)
    if (!pend || !cb) return
    if (!desaIgualment) {
      cb.resolve(null)
      load().then(() => setReloadKey(k => k + 1))
      return
    }
    desa(pend.lineId, pend.valor).then(cb.resolve, cb.reject)
  }, [confirmPlaus, desa, load])

  // La sortida legítima: crear una versió nova (v+1) que superi la segellada. No hi ha auto-bump
  // al backend a propòsit — superar un segell és un acte conscient, i aquest botó és aquest acte.
  const onCrearNovaVersio = () => {
    setBumping(true)
    models.generarGrading(modelId, { new_version: true, allow_reopen_sealed: true })
      .then(() => { setSealed(null); return load().then(() => setReloadKey(k => k + 1)) })
      .catch(() => setErr(t('model_measurements.sealed_bump_err')))
      .finally(() => setBumping(false))
  }

  // Canvi de règim del POM (endpoint independent de la sessió) → rellegeix i remunta la graella.
  // S42/F1 · Q1-bis — LA REGLA ÉS DE LA PEÇA. `ModelGradingRule` és única per
  // `(model, pom, garment)` des de T3 i `set_pom_regim_view` ja resol l'eix des del #12d;
  // aquesta crida l'identificava amb el `pom_id` pelat, o sigui que canviar el règim des del
  // contenidor de la 02 reescrivia la regla de la MARE. La fila el porta (`taula-mesures`
  // l'emet), com a l'ajust de talla d'aquí sobre.
  const onRegimChange = (row, nova) => {
    if (!nova || nova === (row.logica ?? '')) return
    models.setPomRegim(modelId, row.pom_id, nova, row.garment || '')
      .then(() => load().then(() => setReloadKey(k => k + 1)))
      .catch(() => setErr(t('model_measurements.regim_err')))
  }

  const unit = useUnit()
  const leadCols = escalatRuleLeadCols(t, onRegimChange, readOnly, unit, sizes)

  // inline=true: incrustat com a contingut de pestanya (sense overlay fix ni botó tancar).
  const outerStyle = inline
    ? {}
    : { position: 'fixed', inset: 0, zIndex: 50, background: 'rgba(0,0,0,0.45)', display: 'flex', flexDirection: 'column' }
  const bodyStyle = inline
    ? { background: 'var(--white)' }
    : { flex: 1, overflow: 'auto', background: 'var(--white)', padding: '1rem' }

  return (
    <div style={outerStyle}>
      <div style={bodyStyle}>
        {/* Overlay (ruta /escalat o modal "Veure escalat"): botó tancar sempre disponible. */}
        {!inline && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
            <button type="button" onClick={onClose}
              style={{ padding: '6px 16px', border: '0.5px solid var(--border)', borderRadius: 6,
                       background: 'var(--white)', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              {t('model_measurements.propagated_close')}
            </button>
          </div>
        )}
        {/* SET-2/T7-A3 · MATEIX PATRÓ QUE MESURES: la barra crema de resum del model se'n va
            (el que deia ja és a la capçalera de la pàgina, i el run i la base baixen al
            contenidor de peça, dits amb tipografia). La FRANJA CONTEXTUAL no era part del
            resum i es queda: és l'únic lloc que diu de què va aquesta pantalla. */}
        <div style={{ display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap',
                      padding: '0 2px 10px', fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>
          <span>
            <strong>{t('model_sheet.tab_grading')}</strong>
            {' — '}
            {readOnly ? t('model_measurements.propagated_hint_ro') : t('model_measurements.propagated_hint')}
          </span>
        </div>
        {err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginBottom: 8 }}>{err}</div>}
        {/* G6-B/T3 — La versió vigent està segellada i el backend ha refusat l'escriptura. El
            rebuig ha de tenir CARA i SORTIDA: què passa, i què pots fer-hi. */}
        {sealed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
                        marginBottom: 8, padding: '10px 12px', borderRadius: 6,
                        border: '0.5px solid var(--border)', background: 'var(--bg-subtle)' }}>
            <IconLock size={18} stroke={1.5} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <span style={{ fontSize: 'var(--fs-body)', flex: 1, minWidth: 220 }}>
              {t('model_measurements.sealed_title', { v: sealed.version_number })}
              {' '}
              <span style={{ color: 'var(--text-muted)' }}>
                {t('model_measurements.sealed_hint')}
              </span>
            </span>
            {!readOnly && (
              <button type="button" onClick={onCrearNovaVersio} disabled={bumping}
                style={{ padding: '6px 14px', borderRadius: 6, border: '0.5px solid var(--border)',
                         background: 'var(--white)', cursor: bumping ? 'default' : 'pointer',
                         fontSize: 'var(--fs-body)', whiteSpace: 'nowrap' }}>
                {bumping ? t('app.loading') : t('model_measurements.sealed_new_version')}
              </button>
            )}
            <button type="button" onClick={() => setSealed(null)}
              style={{ padding: '6px 10px', borderRadius: 6, border: 0, background: 'transparent',
                       cursor: 'pointer', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
              {t('app.close')}
            </button>
          </div>
        )}
        {/* FIX-4 — la pregunta de plausibilitat. MAI un bloqueig dur: hi ha peces petites
            legítimes, i una validació que impedeix desar només ensenya a esquivar-la. Es
            pregunta, i el «sí» desa amb normalitat. */}
        {confirmPlaus && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
                        marginBottom: 8, padding: '10px 12px', borderRadius: 6,
                        border: '1px solid var(--warn)', background: 'var(--warn-bg)' }}>
            <IconAlertTriangle size={18} stroke={1.5} style={{ color: 'var(--warn)', flexShrink: 0 }} />
            <span style={{ fontSize: 'var(--fs-body)', flex: 1, minWidth: 260 }}>
              {t('model_measurements.plaus_mesura', {
                valor: formatLen(confirmPlaus.valor, unit),
                base: formatLen(confirmPlaus.base, unit),
              })}
            </span>
            <button type="button" onClick={() => resolPlaus(true)}
              style={{ padding: '6px 14px', borderRadius: 6, border: '0.5px solid var(--border)',
                       background: 'var(--white)', cursor: 'pointer',
                       fontSize: 'var(--fs-body)', whiteSpace: 'nowrap' }}>
              {t('model_measurements.plaus_desa')}
            </button>
            <button type="button" onClick={() => resolPlaus(false)}
              style={{ padding: '6px 10px', borderRadius: 6, border: 0, background: 'transparent',
                       cursor: 'pointer', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
              {t('common.cancel')}
            </button>
          </div>
        )}
        {/* SET-2/T7-B2b — un contenidor per prenda; v. `PecesDelModel`. */}
        {/* SET-2/T7-B8 — cada contenidor, les seves files (v. `CheckMeasureEditor`). El desat
            d'Escalat també va per LÍNIA amb la PK. */}
        <PecesDelModel model={modelInfo}>{peca => {
        const filesDelContenidor = filesDeLaPeca(gridRows, peca ? (peca.codi || '') : null)
        return (<>
        {loading && !data ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('app.loading')}</div>
        ) : filesDelContenidor.length === 0 ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('model_measurements.propagated_empty')}</div>
        ) : (
          <MeasureGrid
            key={`${modelId}:${reloadKey}`}
            editable={!readOnly}
            rows={filesDelContenidor} groups={gridGroups}
            leadCols={leadCols}
            leadGroupLabel={t('measuregrid.grup_regla')}
            groupsLabel={t('measuregrid.grup_mesures')}
            onSave={onGridSave}
          />
        )}
        </>)
        }}</PecesDelModel>
      </div>
    </div>
  )
}
