import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { IconAlertTriangle, IconBulb, IconLock } from '@tabler/icons-react'
import client from '../api/client'
import { models } from '../api/endpoints'
import MeasureGrid from '../components/model/MeasureGrid'
import EditorHeader from '../components/model/EditorHeader'
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
// G1 (2026-07-31) — MODE GRADUACIÓ (`graduacio`). La segona porta d'aquesta pantalla: s'hi entra
// des del botó «Graduació» de Mesures (o perquè Propagar hi ha portat el tècnic, G2) i el que
// canvia és que el bloc de Regla és EDITABLE i que, si el model no té graduació, la franja de
// dalt diu d'on surt la proposta i ofereix acceptar-la.
// `onAccepted` / `onCancelada` són el fil de la REPRESA de Propagar: acceptar reprèn el gest
// original, cancel·lar l'avorta sencer (cap estat a mitges).
export default function PropagatedEditor({
  modelId, onClose, inline = false, readOnly = false,
  graduacio = false, onAccepted = null, onCancelada = null,
}) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [modelInfo, setModelInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [reloadKey, setReloadKey] = useState(0)   // remunta MeasureGrid en canvi de règim (re-sembra)
  const [sealed, setSealed] = useState(null)      // payload del 409 {version_number, sortida, ...}
  const [bumping, setBumping] = useState(false)
  const [acceptant, setAcceptant] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    return client.get(`/api/v1/models/${modelId}/taula-mesures/`)
      .then(res => setData(res.data))
      .catch(() => setErr(t('model_measurements.propagated_load_err')))
      .finally(() => setLoading(false))
  }, [modelId, t])

  useEffect(() => { load() }, [load])
  // Identitat de model per a la capçalera unificada (EditorHeader).
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
        if (a) m.set(a.lineId, { vigent: a.value, base: r.base_value_cm, codi: r.codi, talla: s })
      }
    }
    return m
  }, [gridRows, sizes])

  // La pregunta de plausibilitat viva: {lineId, valor, base, codi, talla, resolt}. Mai un bloqueig.
  const [confirmPlaus, setConfirmPlaus] = useState(null)
  const confirmRef = useRef(null)

  // L'escriptura de debò, un cop passades les guardes.
  const desa = useCallback((lineId, value) => {
    const i = lineId.lastIndexOf(':')
    const pomId = Number(lineId.slice(0, i))
    const talla = lineId.slice(i + 1)
    return models.escalatAjustarTalla(modelId, pomId, talla, value)
      .catch(e => {
        // G6-B/T3 — la versió vigent està SEGELLADA: el backend refusa l'escriptura (409). Sense
        // això, el rebuig arribaria com un error mut i el tècnic no sabria ni per què no es desa
        // ni què pot fer. El 409 ja porta la sortida; aquí només es fa visible.
        if (e?.response?.status === 409 && e.response.data?.error === 'sealed') {
          setSealed(e.response.data)
        }
        throw e   // MeasureGrid ha de saber igualment que la cel·la NO s'ha desat.
      })
  }, [modelId])

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
  const onRegimChange = (row, nova) => {
    if (!nova || nova === (row.logica ?? '')) return
    models.setPomRegim(modelId, row.pom_id, nova)
      .then(() => load().then(() => setReloadKey(k => k + 1)))
      .catch(() => setErr(t('model_measurements.regim_err')))
  }

  // G1 — edició dels tres camps de la regla. Passa per la MATEIXA porta que el règim
  // (`setPomRegim` = upsert de la ModelGradingRule resident): cap mecànica nova d'escriptura.
  // Buit → null (esborra el camp), i és una operació legítima: un break que sobra es treu.
  const onRuleChange = useCallback((row, camp, valor) => {
    const cru = (valor ?? '').toString().trim()
    let net = null
    if (cru !== '') {
      if (camp === 'talla_break_label') net = cru
      else {
        const n = parseFloat(cru.replace(',', '.'))
        if (Number.isNaN(n)) { setErr(t('graduacio.delta_no_numeric')); return }
        net = n
      }
    }
    // Sense canvi real no es toca el backend (evita la re-sembra de tota la graella).
    const previ = row[camp] ?? null
    if (String(previ ?? '') === String(net ?? '')) return
    setErr('')
    models.setPomRegla(modelId, row.pom_id, { [camp]: net })
      .then(() => load().then(() => setReloadKey(k => k + 1)))
      .catch(() => setErr(t('graduacio.regla_err')))
  }, [modelId, t, load])

  // G1 — ACCEPTAR la proposta: el model adopta el ruleset del catàleg i les regles passen a ser
  // residents seves (mecanisme del wizard, P3). En acceptar, `onAccepted` reprèn el gest que ens
  // hagi portat aquí (G2: la propagació en cua) — el tècnic no ha de re-clicar res.
  const grad = data?.graduacio || null
  const esProposta = !!grad?.es_proposta
  const onAcceptar = () => {
    if (acceptant) return
    setAcceptant(true)
    setErr('')
    models.graduacioAcceptar(modelId, { rule_set_id: grad?.rule_set_id || undefined })
      .then(() => load().then(() => {
        setReloadKey(k => k + 1)
        if (onAccepted) onAccepted()
      }))
      .catch(e => setErr(e?.response?.data?.message || t('graduacio.accepta_err')))
      .finally(() => setAcceptant(false))
  }

  const unit = useUnit()
  const leadCols = escalatRuleLeadCols(
    t, onRegimChange, readOnly, unit, graduacio ? onRuleChange : null)

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
        {/* Capçalera UNIFICADA: identitat de model + franja contextual (Escalat · pista). */}
        <EditorHeader
          model={modelInfo}
          context={
            <span>
              <strong>{t('model_sheet.tab_grading')}</strong>
              {' — '}
              {readOnly ? t('model_measurements.propagated_hint_ro') : t('model_measurements.propagated_hint')}
            </span>
          }
        />
        {err && <div style={{ color: 'var(--err)', fontSize: 'var(--fs-body)', marginBottom: 8 }}>{err}</div>}
        {/* G1 — LA FRANJA DE GRADUACIÓ. Només en mode graduació. Diu QUÈ s'està mirant (les
            regles del model, una proposta del catàleg, o res) i, si és proposta, ofereix
            acceptar-la. El botó de cancel·lar hi és sempre que algú ens hagi portat aquí amb un
            gest en cua (G2): avortar-lo ha de ser tan fàcil com acceptar-lo. */}
        {graduacio && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
                        marginBottom: 10, padding: '10px 12px', borderRadius: 6,
                        border: `0.5px solid ${esProposta ? 'var(--gold)' : 'var(--border)'}`,
                        background: esProposta ? 'var(--gold-pale)' : 'var(--bg-subtle)' }}>
            <IconBulb size={18} stroke={1.5}
                      style={{ color: esProposta ? 'var(--gold)' : 'var(--text-muted)', flexShrink: 0 }} />
            <span style={{ fontSize: 'var(--fs-body)', flex: 1, minWidth: 240 }}>
              {esProposta
                ? t(grad.font === 'perfil' ? 'graduacio.proposta_perfil' : 'graduacio.proposta_item',
                    { ruleset: grad.rule_set_nom })
                : (grad?.font === 'model'
                    ? t('graduacio.vigents')
                    : t('graduacio.sense_proposta'))}
            </span>
            {esProposta && (
              <button type="button" onClick={onAcceptar} disabled={acceptant}
                style={{ padding: '6px 14px', borderRadius: 6, border: 0, background: 'var(--gold)',
                         color: 'var(--white)', cursor: acceptant ? 'default' : 'pointer',
                         opacity: acceptant ? 0.6 : 1, fontSize: 'var(--fs-body)', whiteSpace: 'nowrap' }}>
                {acceptant ? t('graduacio.acceptant') : t('graduacio.accepta')}
              </button>
            )}
            {onCancelada && (
              <button type="button" onClick={onCancelada}
                style={{ padding: '6px 10px', borderRadius: 6, border: 0, background: 'transparent',
                         cursor: 'pointer', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                {t('common.cancel')}
              </button>
            )}
          </div>
        )}
        {/* G4 — ESTAT BUIT HONEST. Escalat d'un model sense graduació ensenya la base i les
            columnes de regla buides; sense aquesta línia, això es llegeix com «s'ha trencat
            alguna cosa». No és una advertència: un model amb només talla base és COMPLET per a
            la seva fase (P4), i la graduació s'incorporarà quan calgui propagar. */}
        {!graduacio && grad && grad.font !== 'model' && gridRows.length > 0 && (
          <div style={{ marginBottom: 10, padding: '8px 12px', borderRadius: 6,
                        border: '0.5px solid var(--border)', background: 'var(--bg-subtle)',
                        fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
            {t('graduacio.escalat_sense_graduacio')}
          </div>
        )}
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
        {loading && !data ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('app.loading')}</div>
        ) : gridRows.length === 0 ? (
          <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>{t('model_measurements.propagated_empty')}</div>
        ) : (
          <MeasureGrid
            key={`${modelId}:${reloadKey}`}
            editable={!readOnly}
            rows={gridRows} groups={gridGroups}
            leadCols={leadCols}
            leadGroupLabel={t('measuregrid.grup_regla')}
            groupsLabel={t('measuregrid.grup_mesures')}
            onSave={onGridSave}
          />
        )}
      </div>
    </div>
  )
}
