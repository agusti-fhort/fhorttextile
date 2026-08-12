import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { clauDeFila, filesDeLaPeca } from '../../utils/identitatMesura'
import { useNavigate } from 'react-router-dom'
import client from '../../api/client'
import { models, sizeChecks, sizeCheckLines, baseMeasurements, pieceFittingLines } from '../../api/endpoints'
import { effectiveRegime } from '../../utils/gradingRegime'
import { aDocument, aMotor, etiquetaRegla, opcionsDocument } from '../../utils/breakConvention'
import { useEnumeracio } from '../../utils/vocabulariDominiFont'
import { finestraHistoric } from './fittingGridAdapter'
import MeasureGrid from './MeasureGrid'
import EditableTable from '../EditableTable/EditableTable'
import BackButton from '../BackButton'
import PecesDelModel from './PecesDelModel'
import WatchpointsPanel from './WatchpointsPanel'
import SessionPanel from './SessionPanel'
import SessionActions from './SessionActions'
import { boto, botoPorta } from '../ui/buttons'

// CHECK sobre l'editor únic MeasureGrid (substitueix SizeCheckWork): UNA graella amb l'historial
// d'estadis (base-stages, read-only) com a columnes + la columna activa 'Real' (valor_real) + el
// slot Decisió/Nota per línia. La presa entra com valor_real → en resoldre, el motor la propaga a
// BaseMeasurement origen='CHECKED' (una sola columna 'checked'). MOTOR (resolve_size_check) INTACTE.

const MONO = 'IBM Plex Mono, monospace'
const TEXT_2 = 'var(--text-soft)'
const BORDER = 'var(--line)'

// P9 — presa TIPADA per origen: cada estadi de l'historial mostra de quina presa ve, amb un punt de
// color per família d'origen (origen ja viu a MeasurementChangeLog.context). Verd = sessió de fitting;
// daurat = presa humana de taller/proto (size check / manual); gris = derivada/importada/sembra.
// L'etiqueta de text (basestage.ctx.*) ja nomena l'origen; el punt el TIPA visualment a la columna.
const stageAccent = (ctx) => ({
  fitting: 'var(--ok)',
  checked: 'var(--gold)',
  manual: 'var(--gold-l)',
  import: 'var(--text-soft)',
  calculated: 'var(--text-soft)',
  standard: 'var(--text-soft)',
}[ctx] || null)
const fmtStageDate = (iso) => iso ? new Date(iso).toLocaleDateString('ca-ES', { day: '2-digit', month: '2-digit' }) : ''

function StageLabel({ ctx, at, first }) {
  const { t } = useTranslation()
  const accent = stageAccent(ctx)
  return (
    <span>
      {accent && <span aria-hidden="true" style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: accent, marginRight: 4, verticalAlign: 'middle' }} />}
      {first ? t('basestage.stage_measure') : t(`basestage.ctx.${ctx}`, ctx)}
      {at && <span style={{ display: 'block', fontWeight: 400, fontSize: 'var(--fs-caption)' }}>@{fmtStageDate(at)}</span>}
    </span>
  )
}

// Slot Decisió·Nota (trail) per línia del check — port de SizeCheckCell: select de decisió +
// preescriptura/neteja de NOTA_DESCARTAT + nota; autosave via sizeCheckLines.update.
const inputBase = { font: 'inherit', fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '2px 4px', border: `1px solid ${BORDER}`, borderRadius: 3, background: 'var(--white)', boxSizing: 'border-box' }
function DecisioNotaCell({ line }) {
  const { t } = useTranslation()
  const NOTA_DESCARTAT = t('sizecheck.note_discarded_default', 'Cenyir-se a les mesures originals')
  const [decisio, setDecisio] = useState(line.decisio ?? '')
  const [nota, setNota] = useState(line.nota ?? '')
  const saveNota = useRef(null)

  const onDecisioChange = (v) => {
    const next = v || null
    setDecisio(v)
    sizeCheckLines.update(line.id, { decisio: next }).catch(() => setDecisio(line.decisio ?? ''))
    if (next === 'valor_descartat') {
      if (!nota) { setNota(NOTA_DESCARTAT); sizeCheckLines.update(line.id, { nota: NOTA_DESCARTAT }).catch(() => {}) }
    } else if (next === 'tolerancia_acceptada') {
      if (nota === NOTA_DESCARTAT) { setNota(''); sizeCheckLines.update(line.id, { nota: '' }).catch(() => {}) }
    }
  }
  const onNotaChange = (v) => {
    setNota(v)
    clearTimeout(saveNota.current)
    saveNota.current = setTimeout(() => sizeCheckLines.update(line.id, { nota: v }).catch(() => {}), 800)
  }
  useEffect(() => () => clearTimeout(saveNota.current), [])

  return (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      <select value={decisio} onChange={e => onDecisioChange(e.target.value)} style={{ ...inputBase, color: 'var(--text-main)' }}>
        <option value="">{t('sizecheck.decisio.none', '—')}</option>
        <option value="tolerancia_acceptada">{t('sizecheck.decisio.accepted', 'Tolerància acceptada')}</option>
        <option value="valor_descartat">{t('sizecheck.decisio.discarded', 'Valor descartat')}</option>
      </select>
      <input type="text" value={nota} placeholder="…" onChange={e => onNotaChange(e.target.value)}
        style={{ ...inputBase, minWidth: 140, color: 'var(--text-main)' }} />
    </div>
  )
}

// Slot Decisió·Nota en mode CONSULTA (read-only): text pla, mateixes etiquetes i18n.
function ReadOnlyDecisioNota({ line }) {
  const { t } = useTranslation()
  const dec = line.decisio === 'tolerancia_acceptada' ? t('sizecheck.decisio.accepted', 'Tolerància acceptada')
    : line.decisio === 'valor_descartat' ? t('sizecheck.decisio.discarded', 'Valor descartat') : '—'
  return (
    <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
      <span style={{ color: 'var(--text-main)' }}>{dec}</span>
      {line.nota && <span style={{ color: TEXT_2 }}> · {line.nota}</span>}
    </span>
  )
}

// CODA · retoc 3 (Agus) — LA JERARQUIA DE LA §5, i UN SOL BLAU per pantalla i estat.
// Aquí hi havia tres variants pròpies: `gold` (daurat ple = la llei anterior a la §5), `err`
// (vermell PLE en repòs, que la §5.5 prohibeix fora d'una confirmació) i `plain`. Ara la forma
// ve de `ui/buttons`, que és on viu la regla:
//   `gold`  → PRIMÀRIA blava   · `plain` → TERCIÀRIA   · `err` → DESTRUCTIVA amb VORA
// El vermell ple sobreviu NOMÉS dins del modal de confirmació (`err-ple`), que és on la §5.5
// el vol: quan l'usuari ja ha dit que sí i el botó ha de dir què passarà.
const btn = (variant, disabled = false) => boto(
  variant === 'gold' ? 'pri' : variant === 'plain' ? 'ter' : variant, disabled)
// fitting_v3 `kbd` :31-32 — la tecla dibuixada com una tecla.
function Tecla({ children }) {
  return (
    <kbd style={{ border: `1px solid ${BORDER}`, borderRadius: 3, padding: '1px 5px',
                  background: 'var(--white)', font: 'inherit', fontSize: 10,
                  color: 'var(--text-soft)' }}>{children}</kbd>
  )
}
const overlay = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }
const modal = { background: 'var(--white)', borderRadius: 8, padding: 24, maxWidth: 460, fontFamily: MONO, boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }

// Etiqueta compacta de regla (delta · trencament), com el fitting (fittingGridAdapter.regleLabel).
// El trencament es diu en CONVENCIÓ DE DOCUMENT: el ±1 el fa `utils/breakConvention`, mai aquí.
function regleLabel(row, t, sizeRun) {
  if (row.logica == null) return ''
  if (row.logica === 'STEP') return t('fitting.grid.rule_free')
  // LINEAR+0 sense break = FIXED: no té delta a ensenyar (§LLEI a utils/gradingRegime).
  if (effectiveRegime(row) === 'FIXED') return ''
  return etiquetaRegla(row, sizeRun, t('fitting.grid.break'))
}

// P3 — editor de la REGLA VIVA del model (delta + break) a la talla base. La regla és patrimoni del
// MODEL: s'escriu a ModelGradingRule (origen='MANUAL') via models.setPomRule i el motor la llegeix
// tal qual (NO es toca el càlcul). Sense break → delta uniforme (talla_break_label null = LINEAR pur).
// Amb break (talla + valor) → LINEAR amb trencament. STEP (irregular) no s'edita aquí; es mostra inert.
const regleInput = {
  font: 'inherit', fontFamily: MONO, fontSize: 'var(--fs-caption)', width: 46, padding: '1px 3px',
  textAlign: 'right', border: `1px solid ${BORDER}`, borderRadius: 3, background: 'var(--white)',
  color: 'var(--text-main)', boxSizing: 'border-box',
}
const normRegle = (v) => (v === null || v === undefined ? '' : String(v).trim())
function RegleEditCell({ modelId, row, sizeRun, onFeedback }) {
  const { t } = useTranslation()
  const [delta, setDelta] = useState(row.increment_base ?? '')
  const [brk, setBrk] = useState(row.increment_break ?? '')
  const [brkSize, setBrkSize] = useState(row.talla_break_label ?? '')
  // L'ÚLTIM ESTAT DESAT. El `onBlur` no és una intenció de desar: salta també quan només s'ha
  // passat pel camp. Sense aquesta referència, tabular per la taula feia un POST per fila, i
  // `set_pom_regim_view` MATERIALITZA la resident des del fallback del catàleg i li estampa
  // `origen='MANUAL'` — una passada de teclat convertia el patrimoni heretat en autoria humana.
  const desat = useRef({
    d: row.increment_base ?? '', b: row.increment_break ?? '', bs: row.talla_break_label ?? '',
  })
  useEffect(() => {
    setDelta(row.increment_base ?? ''); setBrk(row.increment_break ?? '')
    setBrkSize(row.talla_break_label ?? '')
    desat.current = {
      d: row.increment_base ?? '', b: row.increment_break ?? '', bs: row.talla_break_label ?? '',
    }
  }, [row.pom_id, row.increment_base, row.increment_break, row.talla_break_label])

  const save = (d, b, bs) => {
    const ref = desat.current
    // NOMÉS ELS CAMPS CANVIATS: `set_pom_regim_view` actualitza per PRESÈNCIA de clau (views.py:4619),
    // igual que fa `GraduacioSuperficie.grava` — el que no s'envia no es toca.
    const brkVal = normRegle(bs) ? (normRegle(b) === '' ? null : b) : null
    const payload = {}
    if (normRegle(d) !== normRegle(ref.d)) payload.increment_base = normRegle(d) === '' ? null : d
    if (normRegle(bs) !== normRegle(ref.bs)) payload.talla_break_label = normRegle(bs) || null
    if (normRegle(brkVal) !== normRegle(ref.b)) payload.increment_break = brkVal
    if (!Object.keys(payload).length) return          // res ha canviat: cap escriptura
    // CAP RÈGIM PER DEFECTE (lliçó del 31/07). S'enviava `logica:'LINEAR'` sempre: una fila que
    // heretava una altra lògica del catàleg quedava reescrita a LINEAR sense que ningú ho demanés.
    // Només es declara el règim quan la fila NO en té cap i algú hi acaba d'escriure un delta o un
    // trencament — el mateix criteri que `GraduacioSuperficie` (:158-162). Si ja en té, no es toca.
    if (!row.logica && (normRegle(d) !== '' || normRegle(bs) !== '')) payload.logica = 'LINEAR'
    models.setPomRule(modelId, row.pom_id, payload)
      .then(() => { desat.current = { d, b: brkVal, bs } })
      .catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.regle_save_err') }))
  }
  if (row.logica === 'STEP') {
    // Règim irregular (STEP): no es desglossa a delta+break; es mostra inert (s'edita al fitting).
    return <div style={{ fontSize: 'var(--fs-caption)', color: TEXT_2 }}>{t('fitting.grid.rule_free')}</div>
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-caption)', color: TEXT_2 }}>
        <span style={{ width: 30 }}>{t('measuregrid.regle_delta')}</span>
        <input type="text" inputMode="decimal" value={delta} aria-label={t('measuregrid.regle_delta')}
          onChange={e => setDelta(e.target.value)} onBlur={() => save(delta, brk, brkSize)}
          style={regleInput} />
      </label>
      <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--fs-caption)', color: TEXT_2 }}>
        <span style={{ width: 30 }}>{t('measuregrid.regle_break')}</span>
        <input type="text" inputMode="decimal" value={brk} aria-label={t('measuregrid.regle_break')}
          disabled={!brkSize} onChange={e => setBrk(e.target.value)} onBlur={() => save(delta, brk, brkSize)}
          style={{ ...regleInput, opacity: brkSize ? 1 : 0.5 }} />
        <span>{t('measuregrid.regle_from')}</span>
        {/* ⚠️ `brkSize` es queda en convenció de MOTOR (és el que viatja a `save` i a `desat`);
            l'única cosa que canvia és el que es VEU i el que s'hi tria. Traduir l'estat sencer
            hauria obligat a repassar la comparació de brut del `save`, que no és d'aquest tram. */}
        <select value={aDocument(brkSize, sizeRun) || ''} aria-label={t('measuregrid.regle_from')}
          onChange={e => { const v = aMotor(e.target.value, sizeRun) || ''; setBrkSize(v); save(delta, brk, v) }}
          style={{ font: 'inherit', fontSize: 'var(--fs-caption)', padding: '1px 2px', border: `1px solid ${BORDER}`,
                   borderRadius: 3, background: 'var(--white)', color: 'var(--text-main)' }}>
          <option value="">{t('measuregrid.regle_none')}</option>
          {opcionsDocument(sizeRun).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
    </div>
  )
}

// FONT per defecte: el CHECK. Encapsula els 4 seams (load · buildGroups/buildRows · makeOnSave ·
// buildLeadCols) reusant els sub-components d'aquest fitxer. El comportament és idèntic al d'abans
// de Sprint Y; el component només l'orquestra a través de la font (cap `if (mode)` escampat).
const checkSource = {
  kind: 'check',
  supportsResolve: true,
  supportsReorder: true,
  supportsPoda: true,     // C1 — la taula de mesures del model és seva: aquí sí s'hi pot podar.

  load(model, ctx) {
    // CONSULTA: NO obre cap check (només llegeix el més recent). TREBALL: open idempotent.
    const checkP = ctx.readOnly
      ? sizeChecks.list({ model: model.id, ordering: '-created_at', page_size: 1 })
          .then(r => { const rows = r.data?.results ?? r.data ?? []; return rows.length ? sizeChecks.get(rows[0].id).then(x => x.data) : null })
          .catch(() => null)
      : sizeChecks.open(model.id).then(r => r.data).catch(() => null)
    // LA REGLA DE CADA FILA — nomes per a la CONSULTA (P0.5b, tornada el 06/08).
    //
    // `base-stages` NO porta la regla: serveix identitat, estadis i el valor base. Els quatre
    // camps (`logica`, `increment_base`, `increment_break`, `talla_break_label`) viatgen a
    // `taula-mesures`, que es la mateixa font que fa servir `GraduacioSuperficie`. Es demana
    // NOMES en lectura: en treball no es pinten aquestes columnes i seria una peticio de mes.
    const reglesP = ctx.readOnly
      ? client.get(`/api/v1/models/${model.id}/taula-mesures/`).then(r => r.data).catch(() => null)
      : Promise.resolve(null)
    return Promise.all([models.baseStages(model.id).then(r => r.data).catch(() => null), checkP, reglesP])
      .then(([stages, chk, regles]) => {
        if (!chk && !ctx.readOnly) ctx.onFeedback?.({ type: 'err', text: ctx.t('sizecheck.open_error') })
        return { baseData: stages, check: chk, regles }
      })
  },

  buildGroups(raw, ctx) {
    const stages = raw.baseData?.stages || []
    return [{
      key: 'base',
      label: raw.baseData?.base_size || ctx.t('basestage.stage_measure'),
      accent: true,
      historyCols: stages.map((s, i) => ({ key: s.key, label: <StageLabel ctx={s.context} at={i === 0 ? null : s.at} first={i === 0} /> })),
      activeLabel: ctx.t('sizecheck.col_real'),
      trailCols: [{ key: 'dn', label: `${ctx.t('sizecheck.col_decision')} · ${ctx.t('sizecheck.col_note')}` }],
    }]
  },

  buildRows(raw, ctx) {
    const stages = raw.baseData?.stages || []
    // C4/BLOC 1-BIS — EL CREUAMENT ÉS PER LA PK DE LA MESURA, NO PEL POM. Es feia
    // `lineByPom[l.pom_id]`, i amb dues germanes vives les DUES files de `base_stages`
    // rebien la MATEIXA línia de check: el mateix valor mesurat, el mateix veredicte de
    // tolerància i la mateixa cel·la de decisió·nota. Una de les dues preses no arribava a
    // la pantalla i el veredicte quedava atribuït a la germana equivocada.
    //
    // Les dues bandes parlen ara el mateix idioma: `base_stages` ja servia
    // `base_measurement_id` i les línies del check el porten des d'A2 (`bebd11a0`). Es
    // creua per la PK i no pels eixos perquè la PK és una clau i prou —no cal recompondre
    // res— i perquè `base_stages` no emet capa ni instància.
    const lineByBm = new Map()
    for (const l of (raw.check?.lines || [])) {
      if (l.base_measurement_id != null) lineByBm.set(l.base_measurement_id, l)
    }
    return (raw.baseData?.rows || []).map(r => {
      const line = lineByBm.get(r.base_measurement_id)
      return {
        pom_id: r.pom_id,
        // Clau de fila per a MeasureGrid: la PK de la mesura, que `base_stages` ja serveix.
        // SET-2/T6b — el pla B era el `pom_id` sol, i col·lapsava germanes AVUI: dues files
        // del mateix POM a dues capes compartien clau i React reconciliava una amb l'estat de
        // l'altra. Ara el pla B és la identitat sencera, per la mateixa porta que els altres
        // dos adaptadors.
        rowKey: clauDeFila(r, r.base_measurement_id),
        // C4/BLOC 2 — els eixos viatgen amb la fila perquè la PODA pugui dir quina germana
        // treu (`onPodar`, més avall). `base_stages` els serveix des de `6e259c8b`.
        // SET-2/T7-B7 — I EL TERCER EIX. La fila ha de dir DE QUINA PRENDA és, i no per
        // pintar-ho: perquè el desat l'envia (`utils/payloadMesures`) i la poda del
        // backend conserva per una clau de QUATRE. Sense l'eix a la fila, el payload cau
        // al de la peça del CONTENIDOR, i en una taula amb files de dues prendes això
        // deixaria les de l'altra fora del conjunt a conservar — esborrat silenciós.
        capa: r.capa, instancia: r.instancia,
        garment: r.garment,
        codi: r.nom_fitxa || r.pom_code,
        pom_code: r.pom_code,
        nom_en: r.nom_en, nom_local: r.nom_ca,
        // Sprint NOMS-POM — el bateig del model (buit = mana el catàleg de sobre).
        nom_canonic_model: r.nom_canonic_model || '',
        nom_traduit_model: r.nom_traduit_model || '',
        nom_fitxa: r.nom_fitxa, bm_id: r.base_measurement_id,
        is_key: r.is_key,
        logica: line?.logica, increment_base: line?.increment_base,
        increment_break: line?.increment_break, talla_break_label: line?.talla_break_label,
        tol_minus: line?.tol_minus, tol_plus: line?.tol_plus,
        cells: { base: {
          history: Object.fromEntries(stages.map(s => [s.key, (s.key in r.takes) ? r.takes[s.key] : null])),
          active: line ? { lineId: line.id, value: line.valor_real ?? line.valor_teoric, baseValue: line.valor_teoric, tol: { minus: line.tol_minus, plus: line.tol_plus } } : null,
          trail: { dn: line ? (ctx.readOnly ? <ReadOnlyDecisioNota line={line} /> : <DecisioNotaCell line={line} />) : null },
        } },
      }
    })
  },

  makeOnSave() {
    return (lineId, value) => sizeCheckLines.update(lineId, { valor_real: value })
  },

  onNomSave(bmId, value) {
    return baseMeasurements.update(bmId, { nom_fitxa: value || null })
  },

  // Sprint NOMS-POM — el BATEIG (nom canònic + traducció). Només la font CHECK el declara: la
  // taula de Mesures és la superfície on el model és patrimoni. Al fitting una fila és una presa
  // d'una sessió i el nom no s'hi rebateja.
  onNomsSave(bmId, camps) {
    return baseMeasurements.setNoms(bmId, camps)
  },

  onReorder(model, orderedBmIds) {
    return baseMeasurements.reorder(model.id, orderedBmIds)
  },

  // Règim: en CONSULTA (o lockRules), lectura (logica + etiqueta de regla). En TREBALL, la regla
  // (delta + break) és EDITABLE — patrimoni viu del model (P3). Sprint Y: lockRules la posa en
  // lectura sense fer read-only les preses (mode sessió de fitting sobre la font check no s'usa avui,
  // però la branca és coherent amb la font fitting).
  buildLeadCols(raw, ctx) {
    const lockRegle = ctx.readOnly || ctx.lockRules
    return [{
      key: 'regim', label: ctx.t('fitting.grid.regime'), width: lockRegle ? 118 : 184,
      render: (row) => (lockRegle ? (
        <div>
          <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-main)' }}>{row.logica ?? '—'}</div>
          {regleLabel(row, ctx.t, ctx.sizeRun) && (
            <div style={{ fontSize: 'var(--fs-caption)', color: TEXT_2, whiteSpace: 'nowrap', marginTop: 1 }}>{regleLabel(row, ctx.t, ctx.sizeRun)}</div>
          )}
        </div>
      ) : (
        <RegleEditCell modelId={ctx.model.id} row={row} sizeRun={ctx.sizeRun} onFeedback={ctx.onFeedback} />
      )),
    }, {
      key: 'tol', label: ctx.t('sizecheck.col_tolerance'), width: 72,
      render: (row) => (
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>
          {row.tol_minus != null ? `-${row.tol_minus}/+${row.tol_plus}` : '—'}
        </span>
      ),
    }]
  },
}

// Els recomptes es fan sobre les línies de la TALLA BASE, que són les úniques que es decideixen
// (l'eix multi-talla viu a Escalat): comptar-les totes donaria tres vegades el mateix veredicte.
// El buffer optimista mana sobre la línia, igual que a la cel·la, o el recompte aniria un pas
// enrere del que la modista acaba de prémer.
// El COLOR de cada veredicte (crom, com a `fittingGridAdapter`); QUINS veredictes hi ha ho diu
// `/vocabulari/`. Abans les dues coses anaven fusionades en una sola llista i per tant la
// pantalla declarava el vocabulari per poder-lo pintar.
const RECOMPTE_COL = { ACCEPTED: 'var(--ok)', ADJUSTED: 'var(--warn)', REJECTED: 'var(--err)' }
function RecomptesFitting({ lines, baseLabel, buffer }) {
  const { t } = useTranslation()
  const { codis: verdictes } = useEnumeracio('veredictes_fitting')
  const base = lines.filter(l => !baseLabel || l.size_label === baseLabel)
  const veredicteDe = (l) => (l.id in (buffer || {}) ? buffer[l.id] : (l.decisio || null))
  // ⚠️ SENSE VOCABULARI, TOT SÓN PENDENTS I NO ZERO ACCEPTADES. El recompte es construeix a
  // partir dels veredictes que sabem que existeixen; si no en sabem cap, la barra diu que no hi
  // ha res decidit —cosa que és certa des d'on mirem— en comptes d'afirmar tres zeros.
  const n = Object.fromEntries((verdictes || []).map(v => [v, 0]))
  let pendents = 0
  for (const l of base) {
    const v = veredicteDe(l)
    if (v && v in n) n[v] += 1
    else pendents += 1
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
                  padding: '10px 16px', marginTop: 12, borderTop: '1px solid var(--line)',
                  background: 'var(--bg-page)', fontSize: 'var(--fs-body)', color: TEXT_2 }}>
      {(verdictes || []).map(clau => (
        <span key={clau}>
          <span aria-hidden="true" style={{ width: 8, height: 8, borderRadius: '50%',
                                            display: 'inline-block', marginRight: 5,
                                            background: RECOMPTE_COL[clau] || 'var(--text-soft)' }} />
          {clau} <b style={{ color: 'var(--text-main)', fontWeight: 600 }}>{n[clau]}</b>
        </span>
      ))}
      <span>
        {t('fitting.grid.sense_decidir')}{' '}
        <b style={{ color: pendents ? 'var(--text-main)' : TEXT_2, fontWeight: 600 }}>{pendents}</b>
      </span>
    </div>
  )
}

export default function CheckMeasureEditor({ model, onFeedback, onResolved, onBack = null, readOnly = false, taskId = null, source = null, sourceCtx = null, lockRules = false, onSessionSaved = null }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const src = source || checkSource
  const [raw, setRaw] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(null)
  const [reschedule, setReschedule] = useState(null)
  const [reDate, setReDate] = useState('')

  // Run de talles del model (per al desplegable "a partir de" del break de la regla).
  const sizeRun = (model?.size_run_model || '').split('·').map(s => s.trim()).filter(Boolean)

  // C5-UI/P4 — EL VEREDICTE i la finestra d'HISTÒRIC són estat d'aquesta pantalla, no de la font.
  //
  // `veredictes` és un BUFFER OPTIMISTA, no la font de veritat. La font és `line.decisio`, que el
  // serializer emet i `buildFittingRows` sembra; el buffer només existeix perquè el botó respongui
  // a l'instant sense esperar el PATCH ni rellegir la peça sencera.
  //
  // EN FALLAR, ES DESFÀ. Un veredicte que es pinta i no arriba al servidor és pitjor que un que no
  // es pinta: la modista continua avall creient que ha decidit. Es treu l'entrada del buffer (no
  // s'hi escriu el valor vell) perquè la cel·la torni a llegir la línia, que és qui té la veritat.
  //
  // `histFrom` a `null` vol dir «les dues últimes preses», que és el que es mira en obrir. Es
  // recalcula contra el total real a `finestraHistoric`, o sigui que una versió nova no deixa mai
  // la finestra fora de rang.
  const [veredictes, setVeredictes] = useState({})
  const [histFrom, setHistFrom] = useState(null)
  const totalPreses = raw?.versionNumbers?.length ?? 0
  const decisio = src.kind === 'fitting' && !readOnly ? {
    valors: veredictes,
    onVeredicte: (lineId, v) => {
      setVeredictes(prev => ({ ...prev, [lineId]: v }))
      // Mateixa porta que la nota: PATCH per línia. `''` i no `null` — el buit del camp és una
      // cadena buida i vol dir «sense decidir», que NO és ACCEPTED (v. `PieceFittingLine`).
      pieceFittingLines.update(lineId, { decisio: v || '' })
        .catch(() => {
          setVeredictes(prev => { const n = { ...prev }; delete n[lineId]; return n })
          onFeedback?.({ type: 'err', text: t('fitting.grid.verdicte_err') })
        })
    },
    onNota: (lineId, nota) => pieceFittingLines.update(lineId, { nota: nota || '' })
      .catch(() => onFeedback?.({ type: 'err', text: t('fitting.grid.note_err') })),
  } : null
  const hist = src.kind === 'fitting' ? {
    from: histFrom,
    onMove: (dir) => setHistFrom(f => finestraHistoric(totalPreses, (f ?? Math.max(0, totalPreses - 2)) + dir)),
  } : null

  const ctx = { t, model, readOnly, lockRules, onFeedback, sizeRun,
                fittingSession: sourceCtx?.fittingSession, decisio, hist }

  // 🔴 LA CÀRREGA QUE ARRIBA TARD NO POT MANAR (05/08).
  //
  // Aquesta pantalla canvia de FONT en calent: s'obre amb la font `check` i, quan la sessió de
  // fitting acaba d'arribar, `src` passa a `fittingSource` i es torna a carregar. Les dues
  // càrregues viatgen alhora i totes dues feien `setRaw`, o sigui que qui manava era **la que
  // resolia l'última**, no la que correspon a la font vigent.
  //
  // Efecte mesurat al banc (model 188, sessió 147): `piece-fittings/31/` tornava primer i
  // `size-checks/25/` després, i la graella de FITTING es quedava amb el `raw` del CHECK —que no
  // porta `pomRows`— i pintava «Encara no hi ha mesures base» sobre una peça amb 52 línies. Sense
  // error a la consola i sense res a la xarxa que ho digués: la pantalla, simplement, era buida.
  //
  // El comptador és el mínim que ho tanca: cada càrrega s'apunta el seu torn i, en tornar, només
  // escriu si segueix sent l'última demanada. No cal AbortController —les respostes velles poden
  // arribar, només han de callar.
  const torn = useRef(0)
  const load = useCallback(() => {
    const meu = ++torn.current
    setLoading(true)
    Promise.resolve(src.load(model, { t, readOnly, onFeedback, fittingSession: sourceCtx?.fittingSession }))
      .then(r => { if (meu === torn.current) setRaw(r) })
      // El 400 de create-piece («el model no té cap GradingVersion activa») és un diagnòstic
      // accionable, no un error de xarxa: cal DIR-LO. Però el text del backend és català fix, i
      // aquesta superfície la miren tenants EN/ES → el cas conegut passa per clau i18n; la resta
      // d'errors mostren el text del servidor (patró de doResolve), amb el genèric de xarxa de
      // seguretat. Amb raw=null la graella surt buida i la pantalla queda viva.
      .catch(e => {
        if (meu !== torn.current) return   // una càrrega vella tampoc no pot buidar la nova
        setRaw(null)
        const msg = e?.response?.data?.error || ''
        onFeedback?.({
          type: 'err',
          text: /GradingVersion|talles/i.test(msg)
            ? t('fitting.save.no_grading', { codi: model.codi_intern })
            : (msg || t('sizecheck.open_error')),
        })
      })
      .finally(() => { if (meu === torn.current) setLoading(false) })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model.id, readOnly, src, sourceCtx?.fittingSession])

  useEffect(() => { load() }, [load])

  const check = raw?.check || null
  const hasDescartades = (check?.lines || []).some(l => l.decisio === 'valor_descartat')
  const onResolveClick = (estat) => {
    if (estat === 'Acceptat') {
      if (hasDescartades) { openReschedule('Acceptat', true); return }
      if (check?.te_deltes) { setConfirm('Acceptat'); return }
      doResolve('Acceptat'); return
    }
    openReschedule('Descartat', false)
  }
  const openReschedule = (estat, descartades) => { setReDate(check?.data_represa_default || ''); setReschedule({ estat, descartades }) }
  const doResolve = (estat, opts = {}) => {
    if (!check) return
    setConfirm(null); setReschedule(null); setBusy(true)
    sizeChecks.resolve(check.id, estat, opts)
      .then(r => {
        const d = r.data || {}
        const dr = d.data_represa
        let text
        if (d.estat === 'Acceptat') text = t('sizecheck.fb_saved', { n: d.written || 0 }) + (d.regradat ? t('sizecheck.fb_regraded', { v: d.nova_version }) : '')
        else if (d.estat === 'Rebutjat') text = t('sizecheck.fb_rejected', { d: dr || '—' })
        else text = t('sizecheck.fb_discarded', { d: dr || '—' })
        onFeedback?.({ type: 'ok', text })
        onResolved?.()
      })
      .catch(e => onFeedback?.({ type: 'err', text: e.response?.data?.error || t('sizecheck.resolve_error') }))
      .finally(() => setBusy(false))
  }

  // onSave el fa la font (check: PATCH size-check-line; fitting: despatx STEP/LINEAR). Depèn de raw
  // (el fitting hi llegeix el mapa de règims). onNomSave/onReorder: comuns, delegats a la font i
  // rellegint (mirall del comportament anterior). lockRules bloqueja el nom (mode sessió).
  const onSave = useCallback((lineId, value) => (raw ? src.makeOnSave(raw, ctx)(lineId, value) : Promise.resolve()),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [raw, src])
  const onNomSave = useCallback((bmId, value) =>
    Promise.resolve(src.onNomSave?.(bmId, value))
      .then(() => load())
      .catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.nom_save_err') })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [src, load, onFeedback, t])
  // Sprint NOMS-POM — desa el bateig d'UNA línia i rellegeix (mateix patró que onNomSave: la
  // graella és controlada i la font de veritat torna del servidor, mai del buffer local).
  const onNomsSave = useCallback((bmId, camps) =>
    Promise.resolve(src.onNomsSave?.(bmId, camps))
      .then(() => load())
      .catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.nom_save_err') })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [src, load, onFeedback, t])
  const onReorder = useCallback((orderedBmIds) =>
    Promise.resolve(src.onReorder?.(model, orderedBmIds))
      .then(() => load())
      .catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.reorder_err') })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [src, model.id, load, onFeedback, t])
  // C1 (PRINCIPI DEL SOROLL) — poda d'un POM del model des de la graella: SOFT (is_active=False)
  // + registre al log de mesures. La UI diu «treure»; la BD guarda memòria. Mai DELETE dur.
  const onPodar = useCallback((row) =>
    // C4/BLOC 2 — es poda LA FILA, no el POM. Sense els eixos, treure la sisa dreta
    // desactivava l'esquerra o l'exterior, i quina ho decidia l'ordenació de la consulta.
    // `base_stages` els serveix des de `6e259c8b`.
    models.desactivarPom(model.id, row.pom_id, undefined,
                         { capa: row.capa, instancia: row.instancia })
      .then(() => load())
      .then(() => onFeedback?.({ type: 'ok', text: t('measuregrid.poda_ok', { codi: row.codi || row.pom_code || '' }) }))
      .catch(() => onFeedback?.({ type: 'err', text: t('measuregrid.poda_err') })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [model.id, load, onFeedback, t])

  // ── EL MODE `presa` DE L'EINA `mesures` ─────────────────────────────────────────────────────
  //
  // La font `check` deixa de construir columnes i passa a servir FILES amb la forma que la taula
  // de mesures ja entén. És la mateixa conversió que feia `buildRows`, retallada al que la v8.1
  // ensenya: identitat (capa · instància · nomenclatura · nom) + la presa + la base vigent.
  //
  // QUÈ HI HA DEIXAT DE SORTIR, i per què: el RÈGIM, la Δ, el break i «a partir de» (prendre una
  // mesura no és editar la regla de graduació), la TOLERÀNCIA, i el vocabulari de fitting —«REAL
  // (PROTO)» i «DECISIÓ · NOTA»—, que és d'una altra eina. Ordre d'Agus, 05/08.
  // La regla per POM, de `taula-mesures` (nomes en consulta: v. `checkSource.load`).
  const reglaPerPom = new Map(
    ((raw?.regles?.rows) || []).map(x => [x.pom_id, {
      logica: x.logica, increment_base: x.increment_base,
      increment_break: x.increment_break, talla_break_label: x.talla_break_label,
    }]))
  // LES COLUMNES DE GRADUACIO surten quan el model GRADUA: joc assignat o alguna regla propia.
  // Amb joc pero sense regla resolta, la fila diu `—`, que es informacio i no un forat.
  const graduaAlgunaCosa = !!model?.grading_rule_set
    || [...reglaPerPom.values()].some(x => x.logica)

  const esPresa = src.kind === 'check'
  const rowsPresa = !esPresa ? [] : (raw?.baseData?.rows || []).map(r => {
    const line = (raw?.check?.lines || []).find(
      l => l.base_measurement_id != null && l.base_measurement_id === r.base_measurement_id)
    return {
      // La taula indexa per `row.id`, que és el que fa servir per saber si una fila ja viu a la
      // BD (el bateig hi penja). Aquí SEMPRE hi viu: la presa no inventa mesures.
      id: r.base_measurement_id,
      lineId: line?.id ?? null,
      pom_id: r.pom_id, pom_code: r.pom_code,
      capa: r.capa, instancia: r.instancia,
      nom_fitxa: r.nom_fitxa || '',
      nom_en: r.nom_en, nom_ca: r.nom_ca,
      nom_canonic_model: r.nom_canonic_model || '',
      nom_traduit_model: r.nom_traduit_model || '',
      is_key: r.is_key,
      // EL CARRIL PORTA LA PRESA, no la base: és el número que la modista escriu avui.
      //
      // …PERÒ EN CONSULTA NO HI HA PRESA. La «Taula de mesures» és una pantalla de LECTURA del
      // model: la pregunta que ve a respondre és quina base té la fitxa, no què s'està mesurant
      // avui. Llegint `line.valor_real`/`line.valor_teoric` també aquí, la consulta depenia d'un
      // SizeCheck obert: un model amb els valors gravats a Definició POM i sense cap check
      // (MILEY, BRW-SS26-0003 — 12 files MANUAL amb valor i zero SizeCheck) ensenyava les files
      // correctes i les dues columnes a «—». Les files arribaven perquè vénen de `base_stages`;
      // els valors no, perquè venien de l'altra banda.
      //
      // La font primària és `BaseMeasurement`, i `base_stages_view` ja la serveix a
      // `base_value_cm` (`models_app/views.py:3517`); el seu propi docstring fixa la semàntica:
      // «l'últim estadi coincideix amb la base vigent (BaseMeasurement)» (`:3418`). O sigui que
      // en consulta les dues columnes són la MATEIXA cosa, i és aquesta.
      //
      // El mode presa NO canvia: amb `readOnly=false` el carril segueix portant `valor_real` i la
      // base vigent segueix sent el `valor_teoric` que el check va congelar en obrir-se — que és
      // el que la presa ha de comparar, i no s'ha de moure mentre es pren.
      base_value_cm: readOnly ? (r.base_value_cm ?? null) : (line?.valor_real ?? null),
      // LA REGLA, per a les quatre columnes de lectura de la consulta. Es creua per `pom_id` i
      // no pels eixos a posta: `ModelGradingRule` no porta capa ni instancia (decisio de domini
      // amb acta —mateix POM, mateix increment a totes les cares—), o sigui que dues germanes
      // COMPARTEIXEN regla i han de sortir amb la mateixa. Creuar per la fila donaria buit.
      ...(reglaPerPom.get(r.pom_id) || {}),
      // …i al costat, la base VIGENT, que és contra el que es mesura.
      base_vigent: readOnly ? (r.base_value_cm ?? null) : (line?.valor_teoric ?? null),
    }
  })

  // Les PORTES PER FILA. Cadascuna escriu el mínim i rellegeix: la font de veritat torna del
  // servidor, mai del buffer local (mateix patró que `onNomSave`/`onReorder` d'aquí sobre).
  const presaPortes = {
    baseLabel: t('presa.col_base_vigent'),
    // La presa va a la SEVA línia de size check. La base del model no es toca fins que algú
    // resol la comprovació — és tota la diferència entre prendre i autoritzar.
    onValor: (row, valor) => (row.lineId == null
      ? Promise.reject(new Error('sense línia'))
      : sizeCheckLines.update(row.lineId, { valor_real: valor })),
    onIdentitat: (row, camps) => baseMeasurements.update(row.id, camps).then(() => load()),
    // PARTIR un POM des de la presa: la mesura ja existeix i té preses penjades, o sigui que la
    // MARE es reescriu (no es destrueix, com fa l'autoria sobre files encara no desades) i la
    // germana neix al seu costat amb el valor heretat i el MATEIX origen que la mare — mai
    // 'MANUAL', que diria que algú l'ha mesurada a mà.
    onParteix: (row, filles) => {
      const [a, b] = filles
      return baseMeasurements.update(row.id, { instancia: a.instancia, nom_fitxa: a.nom_fitxa })
        .then(() => (b ? baseMeasurements.create({
          model: model.id, pom: row.pom_id, capa: row.capa || 'exterior',
          instancia: b.instancia, nom_fitxa: b.nom_fitxa,
          base_value_cm: row.base_vigent ?? null, origen: row.origen || 'TEMPLATE',
        }) : null))
        .then(() => load())
    },
    // Q1 — DESFER una instància des de la presa: el revers exacte d'`onParteix`. Primer es
    // RETIREN les germanes (poda tova, amb registre) i només llavors es torna la MARE a la seva
    // identitat base: fer-ho al revés podria xocar amb la clau única `(model, pom, capa,
    // instancia)` si alguna germana ja ocupés la identitat de destí.
    //
    // La mare NO s'esborra mai: és la mesura del model, i desfer una partició no és treure una
    // mesura de la fitxa. Per això aquí hi ha un `update` i no un `desactivarPom`.
    onDesfaInstancia: (row, ident, germanes) =>
      Promise.all((germanes || []).map(g => models.desactivarPom(
        model.id, g.pom_id, undefined, { capa: g.capa, instancia: g.instancia })))
        .then(() => baseMeasurements.update(row.id, ident))
        .then(() => load()),
    onNova: (pom, eixos) => baseMeasurements.create({
      model: model.id, pom: pom.id, capa: eixos.capa || 'exterior',
      instancia: eixos.instancia || '', nom_fitxa: eixos.nom_fitxa || '',
      // Neix SENSE valor: una mesura que ningú ha pres no en té cap, i 'TEMPLATE' és
      // exactament el que el domini diu d'una fila materialitzada i encara buida.
      base_value_cm: null, origen: 'TEMPLATE',
    }).then(() => load()),
    onTreu: (row) => onPodar(row),
    onReordena: (ids) => baseMeasurements.reorder(model.id, ids).then(() => load()),
  }

  if (loading) return <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>{t('common.loading')}</div>

  // Els 4 seams de dades venen SEMPRE de la font — cap `if (mode)` escampat pel render.
  const groups = raw ? src.buildGroups(raw, ctx) : []
  const rows = raw ? src.buildRows(raw, ctx) : []
  const leadCols = raw ? src.buildLeadCols(raw, ctx) : []
  const canReorder = !readOnly && src.supportsReorder
  // Només la superfície de MESURES del model (font check) és propietària de la taula de POMs:
  // al fitting la fila és una presa d'una sessió, no patrimoni que es pugui podar des d'allà.
  const canPodar = !readOnly && src.supportsPoda
  const canEditNom = !readOnly && !lockRules   // lockRules: nomenclatura read-only, preses editables

  return (
    <div>
      {/* SET-2/T7-A · LA BARRA CREMA DE RESUM DEL MODEL SE'N VA (maqueta d'Agus, 10/08).
          Deia `codi_intern` i `nom_prenda`, que la capçalera de la pàgina ja diu en gran dues
          línies més amunt, i `Base: S` + el run, que ara baixen al contenidor de peça dits amb
          tipografia. El que NO era redundant —el botó de tornar, que hi vivia a dins— es queda:
          `EditorHeader` només el pintava quan li arribava `onBack`, i aquí es pinta igual.
          (`EditorHeader` segueix VIU amb UN consumidor: `FittingDetail`, que és una altra
          pàgina —`/fittings/:id`— i queda fora de l'abast d'aquest tram.) */}
      {onBack && <div style={{ marginBottom: 8 }}><BackButton onClick={onBack} /></div>}
      {/* Sprint Y — en mode sessió (font fitting), el panell de la sessió: context + Canvis/Observacions/Imatges. */}
      {ctx.fittingSession && <SessionPanel session={ctx.fittingSession} pieceFittingId={raw?.pieceFittingId} grid={raw?.grid} modelId={model.id} />}
      {/* AQUÍ HI HAVIA «Promoure com a estàndard de l'item» (Agus, 06/08: FORA).
          Promoure és un acte de CATÀLEG —escriu a `GarmentTypeItem`, que és patrimoni de la casa
          i no d'aquest model— i estava penjat de les superfícies de PRESA i de CONSULTA del
          model, que són de mesurar. Que hi visqués perquè «el tècnic ja hi és» és el mateix
          argument que faria caber-hi qualsevol cosa.
          🚩 ON HAURIA DE VIURE: no s'ha decidit i no es decideix aquí. El candidat natural és la
          fitxa de l'ITEM (`ItemAuthoring`), que és l'única pantalla que ja edita el catàleg i que
          avui només s'obre des de `GarmentTypes`; l'altre és una acció del menú del model, fora
          de la taula. `PromoteToItemButton` queda VIU i sense consumidors a posta: el gest existeix
          i el que falta és el lloc. V. el report. */}
      {/* «MESURAR PRENDA» ÉS L'EINA `mesures`, EN MODE `presa` (05/08) — la MATEIXA taula que
          «Definició POM», no una pantalla que se li assembli. Per això aquí hi ha `EditableTable`
          i no la graella de consulta: la identitat de la fila, els grups d'instància, el carril,
          la barra d'estat i el cercador han de ser els mateixos objectes, no dues còpies.
          El FITTING (font `fitting`) segueix a `MeasureGrid`: és una altra eina, amb la seva
          maqueta (fitting_v3) i el seu vocabulari —versions, veredicte, decisió i nota—, i
          barrejar-les seria desfer el que aquest canvi acaba d'unificar. */}
      {/* fitting_v3 `.hint` :159-162 — LA LÍNIA DE DRECERES del fitting. Les tecles existeixen
          des de fa temps (↓/Enter i ↑ recorren el carril; A · J · R posen el veredicte sense
          treure la mà del número) i no ho deia res: qui obria la sessió les havia de saber
          d'abans. Només s'hi anuncia el que funciona en aquesta pantalla. */}
      {/* SET-2/T7-B2b — UN CONTENIDOR PER PRENDA. Abans era un `PecaContenidor` pelat, i per
          això la fila superior no naixia mai: els seus dos props no els passava ningú. El cos
          d'una peça que no és la mare no pot tenir res fins al #12 (comportes), i ho DIU. */}
      {/* SET-2/T7-B8 — CADA CONTENIDOR, LES SEVES FILES. `base-stages` i `taula-mesures` no
          filtren per peça (no tenen com): serveixen totes les files amb el seu eix i el
          repartiment és de la pantalla. Amb `peca == null` (la llista encara no ha contestat)
          hi són totes: buidar una taula pel dubte és el pitjor error d'una superfície de feina.
          El desat d'aquí va per LÍNIA amb la PK (`sizeCheckLines.update(lineId, …)`), o sigui
          que no travessa `_poda_mesures` i filtrar no obre cap finestra. */}
      <PecesDelModel model={model}>{peca => {
      const eixPeca = peca ? (peca.codi || '') : null
      const filesDelContenidor = filesDeLaPeca(rows, eixPeca)
      const presaDelContenidor = filesDeLaPeca(rowsPresa, eixPeca)
      return (<>
      {!esPresa && !readOnly && rows.length > 0 && (
        <p style={{ fontSize: 'var(--fs-label)', color: 'var(--text-soft)',
                    margin: '0 0 10px', lineHeight: 1.8 }}>
          <Tecla>↓</Tecla>/<Tecla>Enter</Tecla> {t('fitting.grid.kbd_next')} · <Tecla>↑</Tecla> {t('fitting.grid.kbd_prev')}
          {' · '}<Tecla>Tab</Tecla> {t('fitting.grid.kbd_tab')}
          {' · '}<b style={{ color: 'var(--ok)' }}><Tecla>A</Tecla> {t('fitting.grid.kbd_accepta')}</b>
          {' · '}<b style={{ color: 'var(--warn)' }}><Tecla>J</Tecla> {t('fitting.grid.kbd_ajusta')}</b>
          {' · '}<b style={{ color: 'var(--err)' }}><Tecla>R</Tecla> {t('fitting.grid.kbd_rebutja')}</b>
          {' · '}{t('fitting.grid.kbd_buit')}
        </p>
      )}
      {esPresa ? (
        <EditableTable
          rows={presaDelContenidor}
          sizeRun={sizeRun}
          baseSize={raw?.baseData?.base_size || model?.base_size_label}
          modelId={model.id}
          readOnly={readOnly}
          presa={presaPortes}
          mostraGrading={readOnly && graduaAlgunaCosa}
        />
      ) : (
      <MeasureGrid rows={filesDelContenidor} groups={groups} leadCols={leadCols} editable={!readOnly}
        onSave={readOnly ? undefined : onSave} onNomSave={canEditNom ? onNomSave : undefined}
        onNomsSave={canEditNom && src.onNomsSave ? onNomsSave : undefined}
        editCodi reorderable={canReorder} onReorder={canReorder ? onReorder : undefined}
        onPodar={canPodar ? onPodar : undefined}
        empty={
          // Estat buit GUIAT: un model sense BaseMeasurement (POM per definir) no pot ser un
          // cul-de-sac. En mode treball sobre la superfície de mesures (font check) expliquem
          // el pas que falta i oferim la CTA a Definició POM (mode entrada). Fora d'això, el text pla.
          (src.kind === 'check' && !readOnly) ? (
            <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2, padding: '8px 0', display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'flex-start' }}>
              <span>{t('basestage.no_base_title')}</span>
              <button type="button" onClick={() => navigate(`/models/${model.id}?tab=Mesures&mode=entry`)}
                style={botoPorta}>
                <i className="ti ti-ruler-2" aria-hidden="true" style={{ fontSize: 16, color: 'currentColor' }} />
                {t('basestage.no_base_cta')}
              </button>
            </div>
          ) : (
            <p style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: TEXT_2 }}>{t('basestage.empty')}</p>
          )
        } />
      )}
      </>)
      }}</PecesDelModel>

      {/* v3 (`.bar` :193-198) — LA BARRA DE RECOMPTES. La graella diu QUÈ té cada fila; això diu
          on és la sessió sencera, que és la pregunta de qui la tanca. «Sense decidir» és el que
          de debò importa: el buit NO és ACCEPTED, i el que no es pot marxar deixant enrere són
          les cel·les que ningú ha mirat. */}
      {src.kind === 'fitting' && rows.length > 0 && (
        <RecomptesFitting lines={raw?.lines || []} baseLabel={raw?.baseLabel || ''}
          buffer={veredictes} />
      )}

      {src.supportsResolve && !readOnly && check && rows.length > 0 && (
        <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
          <button type="button" style={btn('gold', busy)} disabled={busy}
            onClick={() => onResolveClick('Acceptat')}>{t('sizecheck.save')}</button>
          <button type="button" style={btn('err', busy)} disabled={busy}
            onClick={() => onResolveClick('Descartat')}>{t('sizecheck.discard')}</button>
        </div>
      )}

      {/* D-12 — Watchpoints del model (crear en treball, veure sempre). Origen = la tasca actual. */}
      {/* Sprint Y — accions del mode sessió (gravar-i-tornar + reobertura + descartar). Y6 cablarà
          el retorn a la fulla via onSessionSaved; per defecte surt de l'edició (onResolved). */}
      {ctx.fittingSession && !readOnly && (
        <SessionActions session={ctx.fittingSession} pieceFittingId={raw?.pieceFittingId} taskId={taskId}
          onSaved={() => (onSessionSaved || onResolved)?.()} onReload={load} onFeedback={onFeedback} />
      )}

      {model?.id && <WatchpointsPanel modelId={model.id} taskId={taskId} editable={!readOnly} />}

      {confirm && (
        <div style={overlay} onClick={() => setConfirm(null)}>
          <div onClick={e => e.stopPropagation()} style={modal}>
            <h3 style={{ margin: '0 0 12px', fontSize: 'var(--fs-h3)', fontWeight: 600 }}>{t('sizecheck.propagate_title')}</h3>
            <p style={{ margin: '0 0 18px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--text-main)' }}>{t('sizecheck.propagate_warning')}</p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button type="button" style={btn('plain', busy)} disabled={busy}
                onClick={() => setConfirm(null)}>{t('common.cancel')}</button>
              <button type="button" style={btn('gold', busy)} disabled={busy}
                onClick={() => doResolve('Acceptat')}>{t('sizecheck.confirm_propagate')}</button>
            </div>
          </div>
        </div>
      )}
      {reschedule && (
        <div style={overlay} onClick={() => setReschedule(null)}>
          <div onClick={e => e.stopPropagation()} style={modal}>
            <h3 style={{ margin: '0 0 12px', fontSize: 'var(--fs-h3)', fontWeight: 600 }}>{t('sizecheck.reschedule_title')}</h3>
            {reschedule.descartades && (
              <p style={{ margin: '0 0 12px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--err)' }}>{t('sizecheck.reschedule_rejected')}</p>
            )}
            <p style={{ margin: '0 0 8px', fontSize: 'var(--fs-body)', lineHeight: 1.5, color: 'var(--text-main)' }}>{t('sizecheck.reschedule_help')}</p>
            <input type="date" value={reDate} onChange={e => setReDate(e.target.value)}
              style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 8px', borderRadius: 4, border: `1px solid ${BORDER}`, marginBottom: 18, width: '100%', boxSizing: 'border-box' }} />
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button type="button" style={btn('plain', busy)} disabled={busy}
                onClick={() => setReschedule(null)}>{t('common.cancel')}</button>
              {/* §5.5 — el vermell PLE viu NOMÉS aquí: al botó que confirma la destrucció, quan
                  l'usuari ja ha dit que sí i el color ha de dir què passarà. */}
              <button type="button" disabled={busy || !reDate}
                style={btn(reschedule.estat === 'Descartat' ? 'err-ple' : 'gold', busy || !reDate)}
                onClick={() => doResolve(reschedule.estat, { data_represa: reDate })}>{t('sizecheck.reschedule_confirm')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
