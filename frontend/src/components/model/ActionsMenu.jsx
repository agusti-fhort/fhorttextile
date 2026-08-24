import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { suppliers as suppliersApi, productions, fittingSessions, models as modelsApi, plan, commerce, recursos as recursosApi, encarrecs } from '../../api/endpoints'
import useAuthStore from '../../store/auth'
import Modal from '../ui/Modal'
import { selS } from '../ui/buttons'
import TaskAssignWizard from '../TaskAssignWizard'
import { useEnumeracio, codiSeguent, codiAnterior } from '../../utils/vocabulariDominiFont'

const CURRENT = '__current__'   // "fase actual de cada model" (bulk)
const MONO = 'IBM Plex Mono, monospace'
// Cercle de color d'assignació (color_avatar). Fallback --gold si null. (replica de TaskAssignWizard)
const ColorDot = ({ color, size = 16 }) => (
  <span style={{ display: 'inline-block', width: size, height: size, borderRadius: '50%',
    background: color || 'var(--gold)', border: '0.5px solid var(--gray-l)', flexShrink: 0 }} />
)
// `nextPhase`/`prevPhase` han BAIXAT a dins del component: ara depenen del vocabulari, que és
// asíncron. La lògica no ha canviat gens —és `codiSeguent`/`codiAnterior` sobre la mateixa
// llista ordenada—, i ara és la MATEIXA que fa servir `DashboardGovPanel`, que en tenia una
// còpia pròpia. `PHASES` deixa d'exportar-se: `Models.jsx` demana el vocabulari pel seu compte.
const todayISO = () => new Date().toISOString().slice(0, 10)

// Pas 5C · TRAM 2 — Desplegable "Accions" per a UN model (fitxa) o N (selecció a la llista).
// Bulk = itera les crides per-model existents; cada model va a la SEVA next/prev. Feedback agregat.
// `selectionSet` (C2) = selecció de CONJUNT filtrat {filters, excludeIds, count}: no hi ha
// llista d'objectes al client. En aquest mode NOMÉS "assignar tasques" s'escala (envia
// filters+exclude_ids); la resta d'accions (runBulk per-element) queden deshabilitades.
export default function ActionsMenu({ targets, model, selectionSet = null, onChanged, onFeedback, triggerLabel, variant = 'boto' }) {
  const { t } = useTranslation()
  // Les fases del model són DADA (`Model.FASE_CHOICES`) i arriben de `/vocabulari/`. Mentre no
  // hi són, avançar i retrocedir de fase no s'ofereixen: `codiSeguent(null, …)` és `null` i
  // `someNext`/`somePrev` són falsos. És el que toca —no sabem quina fase ve després—, i no una
  // llista escrita aquí que el dia que el model canviï ningú no actualitzarà.
  const { codis: fases } = useEnumeracio('fases_model')
  const nextPhase = (f) => codiSeguent(fases, f)
  const prevPhase = (f) => codiAnterior(fases, f)
  const conjunt = !!selectionSet
  const list = (targets && targets.length ? targets : (model ? [model] : []))
  const single = (!conjunt && list.length === 1) ? list[0] : null
  const n = conjunt ? (selectionSet.count || 0) : list.length   // mida de la selecció (per etiquetes/estat)

  const [open, setOpen] = useState(false)
  const [modal, setModal] = useState(null)
  const [busy, setBusy] = useState(false)
  const [confirmPending, setConfirmPending] = useState(null)   // {payload, text} — conflicte suau a confirmar
  const [supps, setSupps] = useState([])
  const [prods, setProds] = useState([])   // només per al cas single (precondició fitting + defaults)
  const [form, setForm] = useState({})
  const [elegibles, setElegibles] = useState([])   // assistents amb schedule_fittings (modal fitting)
  const [loadingEleg, setLoadingEleg] = useState(false)
  const [orders, setOrders] = useState([])         // comandes OPEN del client (modal assign_order)
  // P7 — l'assignació a un recurs només existeix en una MARCA: és la seva sobirania sobre
  // qui pot treballar cada model. En un Estudi el camp `studio_assignat` no vol dir res.
  const isBrand = useAuthStore(st => st.tenant?.tipologia === 'marca')
  // RETORN-1 — l'ENVIAMENT és el mirall de l'assignació: només existeix en un ESTUDI, i només
  // per a les peces que venen d'una marca (EXTERN). Una peça nascuda aquí no té on anar.
  const isStudio = useAuthStore(st => st.tenant?.tipologia === 'estudi')
  const enviables = list.filter(m => m.origen === 'EXTERN')
  const canConfigure = useAuthStore(st => st.user?.capabilities?.includes('configure')) ?? false
  // M3 — el cicle de vida del model és un acte de GOVERN: el servidor el gateja amb
  // `close_gates` (la mateixa de gate/regress de fase i del segell de graduació).
  const canCloseGates = useAuthStore(st => st.user?.capabilities?.includes('close_gates')) ?? false
  const [recursosActius, setRecursosActius] = useState([])   // només ACTIU: la resta no deixa passar res

  // Clients distints de la selecció (l'assignació a comanda exigeix un sol client).
  const customerIds = [...new Set(list.map(m => m.customer).filter(Boolean))]
  const multiCustomer = customerIds.length > 1

  useEffect(() => {
    suppliersApi.list({ active: 'true', ordering: 'name', page_size: 500 }).then(r => setSupps(r.data?.results ?? r.data ?? [])).catch(() => {})
  }, [])
  useEffect(() => {
    if (!single) { setProds([]); return }
    productions.list({ model: single.id, page_size: 200 }).then(r => setProds(r.data?.results ?? r.data ?? [])).catch(() => setProds([]))
  }, [single?.id])

  // Informatiu (✓ a la fase i decisió de mostrar el camp de recepció prevista). Ja NO bloqueja.
  const deliveredPhases = new Set(prods.filter(p => p.status === 'Delivered').map(p => p.phase))
  const someNext = list.some(m => nextPhase(m.fase_actual))
  const somePrev = list.some(m => prevPhase(m.fase_actual))
  const defaultPhase = single ? single.fase_actual : CURRENT

  const openModal = (kind) => {
    setOpen(false)
    if (kind === 'assign_order') {
      setForm({ order_id: '', line_id: '' })
      setOrders([])
      if (!multiCustomer && customerIds[0]) {
        commerce.orders.list({ customer: customerIds[0], status: 'OPEN', page_size: 200 })
          .then(r => setOrders(r.data?.results ?? r.data ?? [])).catch(() => setOrders([]))
      }
    }
    if (kind === 'assign_resource') {
      setForm({ studio_codi: '' })
      // Es demanen en obrir i no en muntar: la immensa majoria d'obertures del menú no
      // acaben aquí, i la llista de recursos no ha de costar una query a cada selecció.
      recursosApi.list()
        .then(r => setRecursosActius((r.data?.results ?? r.data ?? []).filter(x => x.estat === 'ACTIU')))
        .catch(() => setRecursosActius([]))
    }
    // M3 — el tancament comença SEMPRE sense `ronda`: la volta oberta no es dedueix al client,
    // la diu el servidor amb el 409. Preguntar-ho abans hauria estat una segona font de veritat.
    if (kind === 'tancar_model') setForm({ motiu: 'acabat', ronda: null, destinatari: '', descripcio: '' })
    if (kind === 'reobrir_model' || kind === 'jubilar_model') setForm({ motiu_text: '' })
    if (kind === 'production') setForm({ supplier_id: '', phase: defaultPhase, expected_at: '', notes: '' })
    if (kind === 'fitting') {
      setForm({ fase: single ? single.fase_actual : CURRENT, data: todayISO(), expected_at: '',
                start_time: '', duracio_minuts: '', attendee_ids: [] })
      setLoadingEleg(true)
      plan.eligibleAttendees()
        .then(r => {
          const listE = r.data?.results ?? r.data ?? []
          setElegibles(listE)
          // Preseleccionar el primer elegible per defecte (si encara no n'hi ha cap).
          if (listE.length > 0) setForm(f => (f.attendee_ids?.length ? f : { ...f, attendee_ids: [listE[0].profile_id] }))
        })
        .catch(() => setElegibles([]))
        .finally(() => setLoadingEleg(false))
    }
    setModal(kind)
  }

  // Itera per-model amb feedback agregat: "X fet, Y omesos".
  const runBulk = async (perModel) => {
    setBusy(true)
    let ok = 0; const omesos = []
    for (const m of list) {
      try { await perModel(m); ok++ }
      catch (e) { omesos.push(`${m.codi_intern}: ${e.response?.data?.error || e.response?.data?.detail || 'error'}`) }
    }
    setBusy(false); setModal(null)
    const txt = t('model_sheet.bulk_done', { ok }) + (omesos.length ? ' · ' + t('model_sheet.bulk_skipped', { n: omesos.length }) : '')
    onFeedback({ type: omesos.length ? 'err' : 'ok', text: txt })
    onChanged && onChanged()
  }

  const phaseFor = (m) => (form.phase === CURRENT ? m.fase_actual : form.phase)
  const runProduction = () => {
    if (!form.supplier_id) { onFeedback({ type: 'err', text: t('model_sheet.select_supplier') }); return }
    if (!form.expected_at) { onFeedback({ type: 'err', text: t('model_sheet.expected_required') }); return }
    runBulk(async m => {
      const r = await productions.requestProduction(m.id, { supplier_id: Number(form.supplier_id), phase: phaseFor(m), expected_at: form.expected_at, notes: form.notes || '' })
      return r
    })
  }
  // Schedule single amb gestió de conflictes (P1): 409 dur (sense força) i
  // 200 requires_confirmation (suau → confirmació i recrida amb force=true).
  const submitSchedule = async (payload, force = false) => {
    setBusy(true)
    try {
      const r = await fittingSessions.schedule(force ? { ...payload, force: true } : payload)
      if (r.data?.requires_confirmation) {   // conflicte suau → demanar confirmació
        setBusy(false)
        setConfirmPending({ payload, text: r.data.warning })
        return
      }
      setBusy(false); setModal(null); setConfirmPending(null)
      onFeedback({ type: 'ok', text: t('model_sheet.fitting_scheduled') })
      onChanged && onChanged()
    } catch (e) {
      setBusy(false)
      if (e.response?.status === 409) {   // conflicte DUR: no es pot forçar
        onFeedback({ type: 'err', text: t('model_sheet.fitting_overlap') })
      } else {
        onFeedback({ type: 'err', text: e.response?.data?.error || 'error' })
      }
    }
  }

  const runFitting = () => {
    // Single → schedule individual (retrocompat P5; gestiona expected_at via adaptativa).
    if (list.length === 1) {
      const m = list[0]
      return submitSchedule({
        fase: (form.fase === CURRENT ? m.fase_actual : form.fase),
        data: form.data,
        model_id: m.id,
        start_time: form.start_time || undefined,
        duracio_minuts: form.duracio_minuts ? parseInt(form.duracio_minuts, 10) : undefined,
        attendee_ids: form.attendee_ids || [],
        ...(form.expected_at ? { expected_at: form.expected_at } : {}),
      })
    }
    // Bulk → sessions ENCADENADES via schedule-bulk (convocatòria UUID). schedule-bulk pren UNA
    // fase; amb CURRENT els models poden tenir fase_actual diferents → 1 convocatòria per fase.
    const groups = {}
    for (const m of list) {
      const fase = form.fase === CURRENT ? m.fase_actual : form.fase
      ;(groups[fase] = groups[fase] || []).push(m)
    }
    setBusy(true)
    Promise.all(Object.entries(groups).map(([fase, ms]) =>
      fittingSessions.scheduleBulk({
        model_ids: ms.map(m => m.id),
        fase,
        data: form.data,
        start_time: form.start_time || undefined,
        duracio_minuts: form.duracio_minuts ? parseInt(form.duracio_minuts, 10) : undefined,
        attendee_ids: form.attendee_ids || [],
        ...(form.expected_at ? { expected_at: form.expected_at } : {}),
      })
    ))
      .then(results => {
        setBusy(false); setModal(null)
        // P1: schedule-bulk retorna {created, skipped, warnings} (ja no n_sessions).
        const created = results.reduce((a, r) => a + (r.data?.created?.length ?? 0), 0)
        const skipped = results.reduce((a, r) => a + (r.data?.skipped?.length ?? 0), 0)
        const warnings = results.flatMap(r => r.data?.warnings ?? [])
        let txt = t('model_sheet.fitting_bulk_scheduled', { n: created })
        if (skipped > 0) txt += ' · ' + t('model_sheet.fitting_bulk_skipped', { n: skipped })
        if (warnings.length > 0) txt += ' · ' + t('model_sheet.fitting_bulk_warnings', { n: warnings.length })
        onFeedback({ type: (skipped > 0 || warnings.length > 0) ? 'err' : 'ok', text: txt })
        onChanged && onChanged()
      })
      .catch(e => {
        setBusy(false)
        onFeedback({ type: 'err', text: e.response?.data?.error || 'error' })
      })
  }
  const runAdvance = () => runBulk(m => { const nx = nextPhase(m.fase_actual); if (!nx) throw { response: { data: { error: t('model_sheet.phase_top') } } }; return modelsApi.gate(m.id, { to_phase: nx }) })
  const runBack = () => runBulk(m => { const pv = prevPhase(m.fase_actual); if (!pv) throw { response: { data: { error: t('model_sheet.phase_first') } } }; return modelsApi.regress(m.id, { to_phase: pv }) })
  // v2 albarà — assignar N models a una línia de comanda OPEN (reutilitza assign_model_to_order_line
  // un-a-un: cada crida imputa +1 a la línia). El client ha de ser únic (guard del servei).
  const selectedOrder = orders.find(o => String(o.id) === String(form.order_id))
  const runAssignOrder = () => {
    if (!form.line_id) { onFeedback({ type: 'err', text: t('model_sheet.assign_order_pick_line') }); return }
    runBulk(m => commerce.orderLines.assignModel(form.line_id, { model_id: m.id }))
  }

  // P7 — UNA SOLA CRIDA, no runBulk: l'endpoint és en bloc i torna comptes agregats. El 409
  // (vincle no ACTIU) ha d'arribar sencer a l'usuari: és la llei de les dues claus dient que
  // el pont desmenteix l'assignació, no un error tècnic que es pugui resumir com a "omès".
  // ── M3 · EL CICLE DE VIDA (FIT-9/10/11) ───────────────────────────────────────────────────
  //
  // 🚨 EL 409 NO ÉS UN ERROR: ÉS LA PREGUNTA. Tancar un model amb una volta oberta vol dir
  // tancar feina que algú està fent, i el servidor no ho decideix sol (FIT-10). La primera
  // crida torna `code='ronda_oberta'` amb el número de la volta; llavors el diàleg canvia de
  // cara i demana el destinatari de l'entrega, perquè el que farà la segona crida és
  // exactament això: informar-la (porta d'M1), tancar la volta i acabar el model d'un cop.
  const runTancarModel = () => {
    if (!single) return
    setBusy(true)
    const cos = { motiu: form.motiu || 'acabat' }
    if (form.ronda) {
      cos.confirmar_entrega = true
      cos.destinatari = form.destinatari || ''
      cos.descripcio = form.descripcio || ''
    }
    modelsApi.tancar(single.id, cos)
      .then(r => {
        setBusy(false); setModal(null)
        onFeedback({ type: 'ok', text: t('model_sheet.cicle.tancat_ok', { codi: single.codi_intern }) })
        onChanged && onChanged()
        return r
      })
      .catch(e => {
        setBusy(false)
        const dades = e.response?.data || {}
        if (dades.code === 'ronda_oberta' && dades.ronda) {
          // Segona cara del MATEIX diàleg (no un segon modal): la pregunta arriba amb el número
          // de la volta i el formulari passa a demanar el que l'entrega necessita.
          setForm(f => ({ ...f, ronda: dades.ronda, destinatari: f.destinatari || '' }))
          return
        }
        onFeedback({ type: 'err', text: dades.error || 'error' })
      })
  }

  const runActeSimple = (kind) => {
    if (!single) return
    setBusy(true)
    const crida = kind === 'jubilar_model' ? modelsApi.jubilar : modelsApi.reobrir
    crida(single.id, { motiu: form.motiu_text || '' })
      .then(() => {
        setBusy(false); setModal(null)
        const clau = kind === 'jubilar_model' ? 'model_sheet.cicle.jubilat_ok'
                                              : 'model_sheet.cicle.reobert_ok'
        onFeedback({ type: 'ok', text: t(clau, { codi: single.codi_intern }) })
        onChanged && onChanged()
      })
      .catch(e => {
        setBusy(false)
        onFeedback({ type: 'err', text: e.response?.data?.error || 'error' })
      })
  }

  const runAssignResource = () => {
    setBusy(true)
    modelsApi.assignarRecurs({ model_ids: list.map(m => m.id), studio_codi: form.studio_codi || '' })
      .then(r => {
        setBusy(false); setModal(null)
        const { assignats = 0, ja_hi_eren = 0 } = r.data || {}
        const key = form.studio_codi ? 'model_sheet.assign_resource_done' : 'model_sheet.assign_resource_cleared'
        let txt = t(key, { n: assignats })
        if (ja_hi_eren) txt += ' · ' + t('model_sheet.assign_resource_already', { n: ja_hi_eren })
        onFeedback({ type: 'ok', text: txt })
        onChanged && onChanged()
      })
      .catch(e => {
        setBusy(false)
        onFeedback({ type: 'err', text: e.response?.data?.error || 'error' })
      })
  }

  // RETORN-1 — ENVIAR A LA MARCA. Itera l'endpoint per-model (un model per crida, a posta) i
  // AGREGA l'informe en lloc de comptar només èxits: el que l'usuari ha de saber després de
  // clicar no és «10 fet», és QUÈ ha arribat i què no. Els POMs no aparellats es reporten
  // units de tots els models: són un problema de catàleg, no d'una peça concreta.
  const runEnviarMarca = async () => {
    setBusy(true)
    let ok = 0
    const errors = []
    const tot = { mesures: 0, regles: 0, fitxers: 0 }
    const noAparellats = new Set()
    for (const m of enviables) {
      try {
        const r = await encarrecs.enviar({ model_id: m.id })
        ok++
        const v = r.data?.viatjat || {}
        tot.mesures += v.mesures || 0
        tot.regles += v.regles || 0
        tot.fitxers += v.fitxers || 0
        ;(r.data?.no_aparellat || []).forEach(x => noAparellats.add(x))
      } catch (e) {
        errors.push(`${m.codi_intern}: ${e.response?.data?.error || 'error'}`)
      }
    }
    setBusy(false); setModal(null)
    let txt = t('federacio.enviar_done', { n: ok, ...tot })
    if (noAparellats.size) txt += ' · ' + t('federacio.enviar_no_aparellats', { n: noAparellats.size })
    if (errors.length) txt += ' · ' + t('federacio.enviar_errors', { n: errors.length })
    onFeedback({ type: errors.length ? 'err' : 'ok', text: txt })
    onChanged && onChanged()
  }

  // B — La creació de Watchpoints (D-12) viu ara a l'overlay flotant de la capçalera del model
  // (WatchpointDrawer → WatchpointsPanel), única porta de creació. Aquí ja no hi ha "Fer comentari".

  // En mode CONJUNT, tot menys "assignar" queda deshabilitat amb el mateix motiu (i18n).
  const conjuntHint = conjunt ? t('model_sheet.bulk_conjunt_disabled') : ''
  const items = [
    { key: 'assign', label: t('model_sheet.assign_tasks'), icon: 'ti-users-plus', enabled: n > 0 },
    { key: 'production', label: t('model_sheet.send_to_production'), icon: 'ti-send', enabled: !conjunt && list.length > 0, hint: conjuntHint },
    { key: 'fitting', label: t('model_sheet.schedule_fitting'), icon: 'ti-calendar-plus', enabled: !conjunt && list.length > 0, hint: conjuntHint },
    // L'assignació a comanda demana CONFIGURE al servidor des de sempre
    // (`commerce/views.py`, `assign-model`), però l'entrada de menú no ho deia: un tècnic la
    // veia, obria el modal, triava línia i només aleshores es menjava un 403. Es gateja com
    // les dues germanes de sota. NO demana `comercial`: assignar és cartera, no comerç
    // (decisió d'Agus, 2026-08-14), i el selector li arriba podat d'imports.
    ...(canConfigure
      ? [{ key: 'assign_order', label: t('model_sheet.assign_order'), icon: 'ti-clipboard-list',
           enabled: !conjunt && list.length > 0, hint: conjuntHint }]
      : []),
    // Només en una Marca amb CONFIGURE. Fora del mode conjunt: l'endpoint pren model_ids
    // explícits (no filtres), com production/fitting/assign_order.
    ...((isBrand && canConfigure)
      ? [{ key: 'assign_resource', label: t('model_sheet.assign_resource'), icon: 'ti-affiliate',
           enabled: !conjunt && list.length > 0, hint: conjuntHint }]
      : []),
    // RETORN-1 — només en un ESTUDI amb CONFIGURE i només si hi ha peces EXTERN a la
    // selecció. Fora del mode conjunt: la crida pren models explícits, no filtres.
    ...((isStudio && canConfigure && enviables.length > 0)
      ? [{ key: 'send_brand', label: t('federacio.enviar_action'), icon: 'ti-cloud-upload',
           enabled: !conjunt, hint: conjuntHint }]
      : []),
    { key: 'advance', label: t('model_sheet.advance_phase'), icon: 'ti-arrow-right', enabled: !conjunt && someNext, hint: conjuntHint },
    { key: 'back', label: t('model_sheet.back_phase'), icon: 'ti-arrow-left', enabled: !conjunt && somePrev, hint: conjuntHint },
    // ── M3 · EL CICLE DE VIDA (FIT-9/10/11) ────────────────────────────────────────────────
    // Només amb UN model i només amb `close_gates`, que és el que el servidor demana. L'entrada
    // es gateja aquí i no s'ensenya-i-403: és el mateix que es va corregir a «assignar a
    // comanda» (un tècnic la veia, omplia el diàleg i només llavors es menjava el rebuig).
    // Les tres són EXCLOENTS entre si perquè els estats ho són: un model obert es tanca, un
    // d'acabat es jubila o es reobre, i un de jubilat només es reobre.
    ...((canCloseGates && single && single.estat === 'nou')
      ? [{ key: 'tancar_model', label: t('model_sheet.cicle.tancar'), icon: 'ti-flag-check',
           enabled: true }]
      : []),
    ...((canCloseGates && single && single.estat === 'acabat')
      ? [{ key: 'jubilar_model', label: t('model_sheet.cicle.jubilar'), icon: 'ti-archive',
           enabled: true }]
      : []),
    ...((canCloseGates && single && (single.estat === 'acabat' || single.estat === 'jubilat'))
      ? [{ key: 'reobrir_model', label: t('model_sheet.cicle.reobrir'), icon: 'ti-lock-open',
           enabled: true }]
      : []),
  ]
  const phaseSelectOptions = (withCurrent) => (
    <>
      {!single && withCurrent && <option value={CURRENT}>{t('model_sheet.current_phase')}</option>}
      {(fases || []).map(p => <option key={p} value={p}>{p}{single && p === single.fase_actual ? ' ●' : ''}</option>)}
    </>
  )

  return (
    <div style={{ position: 'relative' }}>
      <button type="button" onClick={() => n && setOpen(o => !o)} disabled={!n}
        aria-haspopup="menu" aria-expanded={open}
        style={{
          ...(variant === 'menu' ? triggerMenu : triggerBtn),
          // §5.7 — deshabilitat: BAIXA EL FONS, no la tinta. L'`opacity` d'abans apagava
          // també el text i el deixava per sota d'AA.
          //
          // …PERÒ AL MENÚ NO HI HA FONS QUE BAIXAR: la píndola de la barra és transparent en
          // repòs, i donar-li `--bg-page` la deixa a un pas de `--sel`, que en aquesta barra
          // vol dir EXACTAMENT EL CONTRARI (píndola activa/hover). Allà mana la §1, que
          // reserva `--text-faint` per a «només deshabilitat».
          ...(n ? null : (variant === 'menu'
            ? { color: 'var(--text-faint)', cursor: 'not-allowed' }
            : { background: 'var(--bg-page)', cursor: 'not-allowed' })),
        }}>
        {triggerLabel || t('model_sheet.actions')}{n > 1 ? ` (${n})` : ''}
        {/* §8: icona dins de botó = 14px i SEMPRE currentColor, perquè segueixi la tinta. */}
        <i className="ti ti-chevron-down" aria-hidden="true"
          style={{ fontSize: 14, color: 'currentColor' }} />
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 40 }} />
          <div style={menuBox}>
            {items.map(it => (
              <button key={it.key} type="button" disabled={!it.enabled}
                onClick={() => it.enabled && openModal(it.key)} title={it.hint || ''}
                style={{ ...menuItem, opacity: it.enabled ? 1 : 0.45, cursor: it.enabled ? 'pointer' : 'not-allowed' }}>
                <i className={`ti ${it.icon}`} aria-hidden="true" /> {it.label}
                {it.hint && <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--gray)', marginLeft: 'auto' }}>ⓘ</span>}
              </button>
            ))}
          </div>
        </>
      )}

      {modal === 'assign' && (
        <TaskAssignWizard
          {...(conjunt
            ? { filters: selectionSet.filters, excludeIds: selectionSet.excludeIds, count: selectionSet.count }
            : { modelIds: list.map(m => m.id) })}
          onClose={() => setModal(null)}
          onSuccess={() => { setModal(null); onChanged?.() }}
        />
      )}

      {modal === 'production' && (
        <Modal title={t('model_sheet.send_to_production')} confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.send')} cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy} onConfirm={runProduction} onCancel={() => !busy && setModal(null)}>
          {!single && <div style={infoBox}>{t('model_sheet.bulk_apply', { n: list.length })}</div>}
          <Row label={t('model_sheet.supplier')}>
            <select style={fullSel} value={form.supplier_id} onChange={e => setForm(f => ({ ...f, supplier_id: e.target.value }))}>
              <option value="">— {t('model_sheet.select_supplier')} —</option>
              {supps.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Row>
          <Row label={t('model_sheet.phase')}><select style={fullSel} value={form.phase} onChange={e => setForm(f => ({ ...f, phase: e.target.value }))}>{phaseSelectOptions(true)}</select></Row>
          <Row label={t('model_sheet.expected_at') + ' *'}><input type="date" style={fullSel} value={form.expected_at} onChange={e => setForm(f => ({ ...f, expected_at: e.target.value }))} /></Row>
          <Row label={t('model_sheet.notes')}><textarea style={{ ...fullSel, minHeight: 50, resize: 'vertical' }} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} /></Row>
        </Modal>
      )}

      {modal === 'assign_order' && (
        <Modal title={t('model_sheet.assign_order')} confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.assign_order_confirm')} cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy || multiCustomer || !form.line_id} onConfirm={runAssignOrder} onCancel={() => !busy && setModal(null)}>
          {multiCustomer ? (
            <div style={warnBox}>{t('model_sheet.assign_order_multi_customer')}</div>
          ) : (
            <>
              {!single && <div style={infoBox}>{t('model_sheet.assign_order_bulk', { n: list.length })}</div>}
              <div style={{ ...infoBox, background: 'var(--gold-pale)', color: 'var(--text-main)' }}>
                {t('model_sheet.assign_order_customer')}: <strong>{list[0]?.customer_nom || '—'}</strong>
              </div>
              <Row label={t('model_sheet.assign_order_order')}>
                <select style={fullSel} value={form.order_id} onChange={e => setForm(f => ({ ...f, order_id: e.target.value, line_id: '' }))}>
                  <option value="">— {t('model_sheet.assign_order_pick_order')} —</option>
                  {orders.map(o => <option key={o.id} value={o.id}>{o.document_number}</option>)}
                </select>
              </Row>
              {orders.length === 0 && <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 12 }}>{t('model_sheet.assign_order_no_orders')}</div>}
              {selectedOrder && (
                <Row label={t('model_sheet.assign_order_line')}>
                  <select style={fullSel} value={form.line_id} onChange={e => setForm(f => ({ ...f, line_id: e.target.value }))}>
                    <option value="">— {t('model_sheet.assign_order_pick_line')} —</option>
                    {(selectedOrder.lines || []).map(l => {
                      const free = Number(l.quantity ?? 0) - Number(l.qty_allocated ?? 0)
                      return <option key={l.id} value={l.id} disabled={free <= 0}>
                        {(l.product_name || l.product_code || `#${l.id}`)} · {Number(l.qty_allocated ?? 0)}/{Number(l.quantity ?? 0)}{free <= 0 ? ` (${t('model_sheet.assign_order_full')})` : ''}
                      </option>
                    })}
                  </select>
                </Row>
              )}
            </>
          )}
        </Modal>
      )}

      {/* M3 · FIT-10 — TANCAR MODEL. Un sol diàleg amb DUES cares: la de sempre (motiu) i, si
          el servidor ha dit que hi ha una volta oberta, la de la confirmació amb el número de
          la volta i les dades de l'entrega. Dos modals haurien fet dues preguntes separades
          d'una decisió que és una de sola. */}
      {modal === 'tancar_model' && (
        <Modal title={t('model_sheet.cicle.tancar')}
          confirmLabel={busy ? t('model_sheet.working')
                             : (form.ronda ? t('model_sheet.cicle.confirmar_i_tancar')
                                           : t('model_sheet.cicle.tancar_confirm'))}
          cancelLabel={t('model_sheet.cancel')}
          confirmDisabled={busy || (Boolean(form.ronda) && !(form.destinatari || '').trim())}
          onConfirm={runTancarModel} onCancel={() => !busy && setModal(null)}>
          {form.ronda ? (
            <>
              <div style={warnBox}>
                {t('model_sheet.cicle.ronda_oberta_avis', { n: form.ronda.seq })}
              </div>
              <Row label={t('model_sheet.cicle.destinatari') + ' *'}>
                <input style={fullSel} value={form.destinatari || ''} autoFocus
                  onChange={e => setForm(f => ({ ...f, destinatari: e.target.value }))} />
              </Row>
              <Row label={t('model_sheet.cicle.descripcio')}>
                <textarea style={{ ...fullSel, minHeight: 50, resize: 'vertical' }}
                  value={form.descripcio || ''}
                  onChange={e => setForm(f => ({ ...f, descripcio: e.target.value }))} />
              </Row>
            </>
          ) : (
            <>
              <div style={infoBox}>{t('model_sheet.cicle.tancar_ajuda')}</div>
              <Row label={t('model_sheet.cicle.motiu')}>
                <select style={fullSel} value={form.motiu || 'acabat'}
                  onChange={e => setForm(f => ({ ...f, motiu: e.target.value }))}>
                  <option value="acabat">{t('model_sheet.cicle.motiu_acabat')}</option>
                  <option value="tret_de_cataleg">{t('model_sheet.cicle.motiu_tret')}</option>
                </select>
              </Row>
            </>
          )}
        </Modal>
      )}

      {(modal === 'reobrir_model' || modal === 'jubilar_model') && (() => {
        const esJubilar = modal === 'jubilar_model'
        return (
          <Modal title={t(esJubilar ? 'model_sheet.cicle.jubilar' : 'model_sheet.cicle.reobrir')}
            confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.cicle.confirmar')}
            cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy}
            onConfirm={() => runActeSimple(modal)} onCancel={() => !busy && setModal(null)}>
            <div style={infoBox}>
              {t(esJubilar ? 'model_sheet.cicle.jubilar_ajuda' : 'model_sheet.cicle.reobrir_ajuda')}
            </div>
            {/* El motiu de la reobertura és TEXT LLIURE a posta (el backend no en té vocabulari):
                els motius els posa la vida i una llista tancada els faria caber a la força. */}
            <Row label={t('model_sheet.cicle.motiu_lliure')}>
              <input style={fullSel} value={form.motiu_text || ''}
                onChange={e => setForm(f => ({ ...f, motiu_text: e.target.value }))} />
            </Row>
          </Modal>
        )
      })()}

      {modal === 'assign_resource' && (
        <Modal title={t('model_sheet.assign_resource')}
          confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.assign_resource_confirm')}
          cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy}
          onConfirm={runAssignResource} onCancel={() => !busy && setModal(null)}>
          {!single && <div style={infoBox}>{t('model_sheet.bulk_apply', { n: list.length })}</div>}
          <Row label={t('model_sheet.assign_resource_pick')}>
            <select style={fullSel} value={form.studio_codi}
              onChange={e => setForm(f => ({ ...f, studio_codi: e.target.value }))}>
              {/* El buit NO és "cap tria": és l'acció de RETIRAR, i el backend l'accepta
                  sempre — també amb el pont tancat. Per això és una opció amb nom. */}
              <option value="">— {t('model_sheet.assign_resource_clear')} —</option>
              {recursosActius.map(r => (
                <option key={r.id} value={r.studio_codi}>{r.studio_codi} · {r.studio_nom}</option>
              ))}
            </select>
          </Row>
          {recursosActius.length === 0 && (
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 12 }}>
              {t('model_sheet.assign_resource_none')}
            </div>
          )}
        </Modal>
      )}

      {/* RETORN-1 — la confirmació DIU QUÈ VIATJARÀ i, sobretot, QUÈ NO. Enviar feina a la
          casa del client és un acte que no es desfà amb un botó, i l'usuari ha de saber abans
          de clicar que el seu .ftt i els seus patrons es queden aquí. */}
      {modal === 'send_brand' && (
        <Modal title={t('federacio.enviar_action')}
          confirmLabel={busy ? t('model_sheet.working') : t('federacio.enviar_confirm')}
          cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy}
          onConfirm={runEnviarMarca} onCancel={() => !busy && setModal(null)}>
          <div style={infoBox}>{t('federacio.enviar_intro', { n: enviables.length })}</div>
          <ul style={{ margin: '0 0 12px 18px', padding: 0, fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>
            <li>{t('federacio.enviar_inclou_mesures')}</li>
            <li>{t('federacio.enviar_inclou_regles')}</li>
            <li>{t('federacio.enviar_inclou_fitxers')}</li>
          </ul>
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 12 }}>
            {t('federacio.enviar_exclou')}
          </div>
          <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
            {t('federacio.enviar_sobirania')}
          </div>
          {enviables.length < list.length && (
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--gray)', marginTop: 8 }}>
              {t('federacio.enviar_no_externs', { n: list.length - enviables.length })}
            </div>
          )}
        </Modal>
      )}

      {modal === 'fitting' && (
        <Modal title={t('model_sheet.schedule_fitting')} confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.schedule_fitting')} cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy} onConfirm={runFitting} onCancel={() => !busy && setModal(null)}>
          {!single && <div style={infoBox}>{t('model_sheet.fitting_bulk_note', { n: list.length })}</div>}
          <Row label={t('model_sheet.phase')}>
            <select style={fullSel} value={form.fase} onChange={e => setForm(f => ({ ...f, fase: e.target.value }))}>
              {single
                ? (fases || []).map(p => <option key={p} value={p}>{p}{deliveredPhases.has(p) ? ' ✓' : ''}</option>)
                : phaseSelectOptions(true)}
            </select>
          </Row>
          <Row label={t('model_sheet.date')}><input type="date" style={fullSel} value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))} /></Row>
          <Row label={t('model_sheet.fitting_start_time')}>
            <input type="time" style={fullSel} value={form.start_time || ''}
              onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))} />
          </Row>
          <Row label={t('model_sheet.fitting_duration')}>
            <input type="number" min={5} step={5} style={fullSel} value={form.duracio_minuts || ''}
              placeholder={t('model_sheet.fitting_duration_ph')}
              onChange={e => setForm(f => ({ ...f, duracio_minuts: e.target.value }))} />
          </Row>
          <div style={{ marginBottom: 12, marginTop: -4 }}>
            <small style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
              {form.start_time
                ? t('model_sheet.fitting_franja_note', { dur: form.duracio_minuts || '10', hora: form.start_time })
                : t('model_sheet.fitting_nofranja_note')}
            </small>
          </div>
          <Row label={t('model_sheet.fitting_attendees')}>
            {loadingEleg
              ? <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('model_sheet.loading')}</span>
              : elegibles.length === 0
                ? <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('model_sheet.fitting_no_attendees')}</span>
                : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 120, overflowY: 'auto' }}>
                    {elegibles.map(e => {
                      const sel = (form.attendee_ids || []).includes(e.profile_id)
                      return (
                        <label key={e.profile_id} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
                          padding: '4px 6px', borderRadius: 6, fontSize: 'var(--fs-body)', fontFamily: MONO,
                          background: sel ? 'var(--gold-pale)' : 'transparent' }}>
                          <input type="checkbox" checked={sel} style={{ accentColor: 'var(--gold)' }}
                            onChange={() => setForm(f => ({ ...f,
                              attendee_ids: sel
                                ? f.attendee_ids.filter(id => id !== e.profile_id)
                                : [...(f.attendee_ids || []), e.profile_id] }))} />
                          <ColorDot color={e.color_avatar} size={14} />
                          {e.full_name}
                        </label>
                      )
                    })}
                  </div>
                )}
          </Row>
          {!deliveredPhases.has(form.fase) && (
            <div style={{ marginTop: 8 }}>
              <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                {t('fitting_expected_at_label')}
              </label>
              <input
                type="date"
                value={form.expected_at || ''}
                onChange={e => setForm(f => ({ ...f, expected_at: e.target.value }))}
                style={{ width: '100%', marginTop: 4, fontSize: 'var(--fs-body)', border: '1px solid var(--border)', borderRadius: 4, padding: '4px 8px' }}
              />
              <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 2 }}>
                {t('fitting_expected_at_hint')}
              </div>
            </div>
          )}
        </Modal>
      )}

      {/* Conflicte SUAU (P1): el model ja té fitting d'aquesta fase en una altra franja. */}
      {confirmPending && (
        <Modal title={t('model_sheet.fitting_dup_title')}
          confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.fitting_create_anyway')}
          cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy}
          onConfirm={() => submitSchedule(confirmPending.payload, true)}
          onCancel={() => !busy && setConfirmPending(null)}>
          <p style={{ fontSize: 'var(--fs-body)', lineHeight: 1.5 }}>
            {confirmPending.text || t('model_sheet.fitting_dup_warn')}
          </p>
        </Modal>
      )}

      {(modal === 'advance' || modal === 'back') && (() => {
        const isAdv = modal === 'advance'
        const target = single ? (isAdv ? nextPhase(single.fase_actual) : prevPhase(single.fase_actual)) : null
        const titleKey = single
          ? (isAdv ? 'model_sheet.advance_confirm' : 'model_sheet.back_confirm')
          : (isAdv ? 'model_sheet.advance_bulk_confirm' : 'model_sheet.back_bulk_confirm')
        return (
          <Modal title={t(titleKey, { phase: target, n: list.length })}
            confirmLabel={busy ? t('model_sheet.working') : t(isAdv ? 'model_sheet.advance_phase' : 'model_sheet.back_phase')}
            cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy}
            onConfirm={() => (isAdv ? runAdvance() : runBack())} onCancel={() => !busy && setModal(null)}>
            <p style={{ fontSize: 'var(--fs-body)', lineHeight: 1.5 }}>{t(isAdv ? 'model_sheet.advance_help' : 'model_sheet.regress_help')}</p>
          </Modal>
        )
      })()}
    </div>
  )
}

function Row({ label, children }) {
  return <div style={{ marginBottom: 12 }}><div style={{ fontSize: 'var(--fs-label)', textTransform: 'uppercase', letterSpacing: '.04em', color: 'var(--gray)', marginBottom: 4, fontFamily: MONO }}>{label}</div>{children}</div>
}

// EL DISPARADOR D'«ACCIONS ▾» ÉS SECUNDARI (NORMA_LAYOUT §5.6, T0-bis.4).
//
// «Accions ⋯» és el calaix de les ocasionals —duplicar, exportar, arxivar—, i un calaix no és
// mai «el que has vingut a fer»: la primària n'és una per pantalla i aquesta no ho és.
//
// Fins ara consumia `primaryBtn`, cosa que era CORRECTA mentre la primària era daurada (S37):
// aleshores «vora/fons de la casa» i «acció primària» eren el mateix color i el préstec no es
// notava. En passar la primària a blau (T0-bis.2) el préstec va quedar a la vista: el menú
// d'accions sortia blau a /models, al dashboard del model i al TaskAssignWizard.
//
// Es corregeix AQUÍ, un sol cop, i no a les tres pantalles: el disparador és compartit.
// §8e — QUAN L'ACCIÓ PUJA AL MENÚ DE PANTALLA DEIXA DE SER UN BOTÓ: dins de la barra blanca
// el llenguatge és el de la píndola de navegació, no el del botó secundari. Mateixa forma que
// `PageMenu` i que el `BotoMenu` de la llista de Models; `variant="menu"` és opt-in, i el
// consumidor de sempre (capçalera de la fitxa del model) no canvia gens.
const triggerMenu = {
  display: 'inline-flex', alignItems: 'center', gap: 6,
  borderWidth: 1, borderStyle: 'solid', borderColor: 'transparent',
  borderRadius: 'var(--r-pill)', background: 'none',
  padding: '6px 14px', fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px',
  color: 'var(--text-soft)', cursor: 'pointer', whiteSpace: 'nowrap',
}
// §5.2 · SECUNDÀRIA: blanc + vora --gold-border + tinta fosca, **padding 8×16** i pes 500 —
// les mides exactes que la norma escriu i que el `.btn` de la maqueta del §8b pinta. Abans
// anava a 7×14 i pes 600, que és el pes d'un primari.
const triggerBtn = {
  display: 'inline-flex', alignItems: 'center', gap: 6,
  background: 'var(--panel)', color: 'var(--text-main)',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--gold-border)',
  borderRadius: 'var(--r-ctrl)',
  padding: '8px 16px', fontSize: 'var(--fs-body)', fontWeight: 500, lineHeight: '16px',
  cursor: 'pointer', fontFamily: MONO,
}
const menuBox = { position: 'absolute', right: 0, top: 'calc(100% + 4px)', zIndex: 41, background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4, minWidth: 230 }
const menuItem = { display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left', background: 'none', border: 'none', padding: '8px 10px', borderRadius: 6, fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)' }
const fullSel = { ...selS, width: '100%' }
const warnBox = { background: 'var(--warn-bg)', border: '0.5px solid var(--warn)', color: 'var(--warn)', borderRadius: 8, padding: '8px 12px', marginBottom: 12, fontSize: 'var(--fs-body)', lineHeight: 1.5, fontFamily: MONO }
const infoBox = { background: 'var(--gray-l)', borderRadius: 8, padding: '8px 12px', marginBottom: 12, fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-main)' }
