import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { IconAlertTriangle } from '@tabler/icons-react'
import client from '../api/client'
import { models, presaEscalat } from '../api/endpoints'
import MeasureGrid from '../components/model/MeasureGrid'
import PecesDelModel from '../components/model/PecesDelModel'
import BarraPresaEscalat from '../components/model/BarraPresaEscalat'
import { filesDeLaPeca } from '../utils/identitatMesura'
import { buildEscalatGroups, buildEscalatRows, escalatRuleLeadCols } from '../components/model/fittingGridAdapter'
import { mesuraSemblaIncrement } from '../utils/plausibilitatMesura'
import { formatLen } from '../utils/format'
import { useUnit } from './fittingShared'

// ESCALAT — la taula del model per talles, sobre l'editor únic MeasureGrid.
//
// ⚠️ E1/B3 (17/08) — AQUESTA PANTALLA HA CANVIAT DE NATURALESA. El que hi havia escrit aquí
// deia: «editar una cel·la PROPAGA per regla a les germanes (endpoint escalat/ajustar-talla →
// propaga_ancoratges)». Era cert i era el defecte: la columna «Fit actual» EDITAVA LA CORBA
// TEÒRICA —escrivia `BaseMeasurement`/`ModelGradingOverride` i re-derivava els specs a cada
// tecla—, de manera que «Mesurar prenda» clonava com a teòric el número que el tècnic acabava
// d'anotar i la desviació sortia sempre zero (DIAGNOSI_E1 §3.2).
//
// ARA ÉS EL PAS 1 DEL FLUX E1: la PRESA de les peces físiques arribades. «Fit actual» anota a
// `PieceFittingLine.valor_real` (porta `fitting/model/<id>/presa/`) i NO toca res del domini.
// E2a (QA d'Agus, 17/08) — per talla es veuen DOS valors: **Mesura** (la teòrica de contracte)
// i **Fit actual** (l'arribada). Hi havia una tercera columna, «Propagada», i ensenyava el
// MATEIX número que la teòrica mentre no s'hagués propagat —o sigui quasi sempre—: dues
// columnes amb la mateixa xifra fan buscar la diferència que no hi és.
// El vermell segueix dient que la peça arribada s'aparta del que s'esperava (R1), i el seu
// referent segueix sent la teòrica (v. `cellaEscalat`).
//
// Decidir (acceptar/ajustar/rebutjar) NO es fa aquí: és el pas 2, «Mesurar prenda», i NOMÉS a
// la talla base (R2, guard partit d'E1/B1). Propagar segueix sent l'acte conscient de Mesures.
// El règim per POM es canvia amb setPomRegim; la corba vigent surt de taula-mesures.
export default function PropagatedEditor({ modelId, onClose, inline = false, readOnly = false }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [modelInfo, setModelInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [reloadKey, setReloadKey] = useState(0)   // remunta MeasureGrid en canvi de règim (re-sembra)
  const [presa, setPresa] = useState(null)        // E1/B3 — estat de la presa viva + valors

  // E1/B3 — DUES fonts, i cadascuna diu una cosa que l'altra no sap:
  //   · `taula-mesures` → la CORBA VIGENT del model (teòrica propagada);
  //   · `fitting/model/<id>/presa/` → la PRESA de les peces arribades (+ l'estat de la presa).
  // La segona no bloqueja la primera: si falla o no hi ha presa oberta, la graella surt com
  // sempre i el rètol d'estat ho diu. Buidar la taula perquè no hi ha presa seria el pitjor
  // error d'una superfície de feina.
  const load = useCallback(() => {
    setLoading(true)
    return Promise.all([
      client.get(`/api/v1/models/${modelId}/taula-mesures/`)
        .then(res => { setData(res.data); return true })
        .catch(() => { setErr(t('model_measurements.propagated_load_err')); return false }),
      presaEscalat.get(modelId).then(r => setPresa(r.data)).catch(() => setPresa(null)),
    ]).finally(() => setLoading(false))
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
    () => buildEscalatRows(data?.rows || [], sizes, base, presa?.preses || {}),
    [data, sizes, base, presa])

  // Índex per lineId → {vigent, base} de la fila. El fan servir les dues guardes de sota, i és
  // l'única lectura de l'estat que necessiten (cap dada nova del backend).
  const perLinia = useMemo(() => {
    const m = new Map()
    for (const r of gridRows) {
      for (const s of sizes) {
        const a = r.cells?.[s]?.active
        // C4/BLOC 3 — hi entra el `pom_id` (i els eixos) perquè l'escriptura no hagi de
        // desmuntar el lineId: la fila ja sap qui és, i el mapa ja la té localitzada.
        // E2b — `fantasma` viatja amb la línia perquè la GUARDA-RAIL de sota el pugui
        // distingir: amb el pre-omplert, `value` ÉS la teòrica i la guarda es menjaria la
        // confirmació sense dir res.
        if (a) m.set(a.lineId, { vigent: a.value, base: r.base_value_cm, codi: r.codi, talla: s,
                                 fantasma: !!a.fantasma,
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
    // 🔑 E1/B3 — AQUESTA CEL·LA JA NO EDITA LA CORBA: ANOTA UNA PRESA.
    //
    // Això cridava `models.escalatAjustarTalla`, que escrivia `BaseMeasurement` (o un
    // `ModelGradingOverride`) i re-derivava els specs a cada tecla. Per això «Mesurar prenda»
    // clonava com a teòric el número que el tècnic acabava d'anotar i la desviació sortia
    // sempre zero: el pas 1 destruïa el referent del pas 2 (DIAGNOSI_E1 §3.2).
    //
    // Ara va a `PieceFittingLine.valor_real` per una porta que no toca el domini. El que la
    // presa NO fa —consolidar, propagar— continua tenint les seves portes, i cadascuna és un
    // acte que algú decideix.
    return presaEscalat.desa(modelId, info.pom_id, info.talla, value,
                             { capa: info.capa, instancia: info.instancia,
                               garment: info.garment })
      .then(res => { load(); return res })
      .catch(e => {
        // Els dos rebutjos que aquesta porta pot donar tenen CARA: sense presa oberta no hi
        // ha on anotar (i el gest d'obrir-la és a la barra d'estat), i una sessió segellada és
        // acta. Un rebuig mut faria que el tècnic seguís mesurant creient que es desa.
        const codi = e?.response?.data?.codi
        if (codi === 'sense_presa_oberta' || codi === 'sessio_segellada') {
          setErr(t(`escalat.${codi}`))
        }
        throw e   // MeasureGrid ha de saber igualment que la cel·la NO s'ha desat.
      })
  }, [modelId, perLinia, load, t])

  // Anotació de la presa d'una cel·la. Retorna l'axios promise; la resposta porta la cel·la
  // resolta pel servidor (teòric · real · desviació · estat) i `load()` refresca la graella.
  const onGridSave = useCallback((lineId, value) => {
    if (value == null) return Promise.resolve()
    const info = perLinia.get(lineId)

    // GUARDA-RAIL — reescriure el valor que la cel·la JA té és un NO-OP: ni crida. `info.vigent`
    // és ara LA PRESA que hi ha desada (no la corba), o sigui que això estalvia una escriptura
    // idèntica, no una re-derivació: el motiu ha canviat amb la naturalesa de la cel·la, però
    // la crida que no es fa segueix sent la que no es pot equivocar mai.
    //
    // 🚨 E2b — I NO S'APLICA AL FANTASMA. Amb el pre-omplert, `info.vigent` ÉS la teòrica que
    // la cel·la ensenya sense que ningú l'hagi mesurada: confirmar-la és un GEST (ha de crear
    // la presa i escriure `presa_at`), i aquesta guarda l'hauria engolit en silenci —el número
    // coincideix— deixant l'usuari convençut que havia confirmat. La guarda existeix per
    // estalviar escriptures IDÈNTIQUES a una presa que ja hi és; sense presa no hi ha res a
    // estalviar.
    if (info && !info.fantasma && info.vigent !== '' && info.vigent != null
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

  // ⚠️ E1/B3 — AQUÍ HI HAVIA EL RÈTOL DE «VERSIÓ SEGELLADA» I EL BOTÓ DE SUPERAR-LA, i se'n
  // van perquè han quedat INASSOLIBLES, no per gust. El 409 `sealed` el donava el motor en
  // re-derivar els specs, i aquesta pantalla el disparava perquè cada tecla els re-derivava.
  // Ara la cel·la anota una presa i no toca cap `GradingVersion`: el segell no s'hi pot
  // trobar mai, i un rètol que no pot sortir és pitjor que no tenir-ne —qui llegeixi el
  // fitxer en dedueix que l'Escalat escriu al grading, que és precisament el que ja no fa.
  //
  // EL GEST NO ES PERD i no calia que visqués aquí: la porta que SÍ topa amb el segell és
  // «Propagar a grading» (`ModelSheet.onPropagarClick`), que ja ofereix la doble confirmació
  // amb `allow_reopen_sealed`. Superar un segell és un acte de propagació, no de presa.

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
        {/* E1/B3 · R5 — L'ESTAT DE LA PRESA I EL PAS SEGÜENT. La navegació va a una porta que
            JA EXISTEIX i no n'inventa cap: amb sessió resolta, `?tab=Mesures&fitting_session=<id>`
            és el camí que `ModelSheet` ja sap obrir (obre la tasca `size_check` d'aquella
            sessió i aterra a la presa); sense presa oberta, al tab Mesures, on el stepper té
            el gest de «Mesurar prenda». ⚠️ Obrir una presa CREA sessió + peça + N línies, i per
            això aquesta pantalla no ho fa sola: hi porta (decisió D5 de la diagnosi, OBERTA). */}
        <BarraPresaEscalat
          presa={presa} readOnly={readOnly}
          onDecidir={() => navigate(
            `/models/${modelId}?tab=Mesures&fitting_session=${presa?.session?.id ?? ''}`)}
          onObrir={() => navigate(`/models/${modelId}?tab=Mesures`)} />
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
