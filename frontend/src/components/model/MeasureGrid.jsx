import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'

import BateigInput from './BateigInput'
import { thStyle, SaveStatus, useDebouncedSave, fmtMeasure, useUnit } from '../../pages/fittingShared'
import { etiquetaCapa, etiquetaInstancia } from '../../utils/capaInstancia'
import { useDiccionariMesures, useEstatDiccionari } from '../../utils/diccionariMesuresFont'
import { useTraduccioPoms } from '../../utils/traduccioPomFont'
import { InfoTraduccio } from '../EditableTable/EditableTable'
import AvisDiccionari from '../ui/AvisDiccionari'

// MeasureGrid — editor únic de mesures (un component, dos modes treball/consulta) que serveix els
// DOS eixos via SLOTS, reusant l'esquelet del fitting editor (MeasureTable):
//  · files = POMs amb nomenclatura a 2 línies (nom EN canònic dalt · nom idioma usuari sota).
//  · columnes en GRUPS: cada grup = N columnes d'història READ-ONLY + 1 columna ACTIVA editable.
//      - check: 1 grup 'base', història = estadis (import/manual/checked), activa = Real.
//      - fitting: N grups (talles), història = versions, activa = Fit actual.
//  · slots: leadCols (sticky, p.ex. Règim del fitting), trailCols per grup (p.ex. Decisió/Nota del check),
//      i `actions` (barra de resolució). El proveïdor d'EIX construeix `groups`+`rows`; aquí no se'n sap res.
// Controlat: els valors arriben per `rows`; en desar es crida onSave(lineId, value) i, si retorna línies
// propagades (fitting), s'actualitzen les germanes (excepte la cel·la amb focus). Motors INTACTES.

// C5-UI — LA IDENTITAT DE LA FILA ÉS LA MATEIXA A TOTES LES SUPERFÍCIES. Aquesta graella la
// comparteixen Escalat, Comprovació, Fitting i Repàs, i les quatre poden servir dues germanes del
// mateix POM. Fins ara les dues files hi sortien amb el mateix nom i la diferència només es podia
// endevinar per la nomenclatura del client (A / A-FOL): la capa passa a tenir columna pròpia i la
// instància viu dins del nom, exactament com a la taula d'entrada de Mesures (P1). Una identitat
// que canviés de forma segons la pantalla seria la mateixa trampa que la nomenclatura tenia abans
// de `nomenclaturaPom.js`.
const COL_CAPA_W = 92
const COL_POM_W = 78
const COL_NOM_W = 160

// `filled` = gold-pale (NOMÉS la columna activa destaca); groupStart/End = filet subtil de
// delimitació del grup (no daurat, per no competir amb el destacat de l'activa).
// S45/G2 — ELS VALORS NUMÈRICS VAN CENTRATS a tota la superfície de mesures (v. la nota de
// criteri a `EditableTable`). Aquesta era la tercera taula de la família amb la seva pròpia
// resposta —`right` aquí, `center` a Mesures, `right` a Graduació—: tres taules que es miren
// de costat i tres alineacions. El que fa que una columna de xifres es pugui escombrar amunt
// i avall és `tabular-nums`, que es queda; la vora on s'arrambin és la part que ha de ser
// IGUAL a tot arreu, i ara ho és.
const cellTd = (filled, groupStart, groupEnd) => ({
  padding: '5px 8px', borderBottom: '1px solid var(--line-soft)', verticalAlign: 'middle',
  textAlign: 'center', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums',
  background: filled ? 'var(--sel)' : undefined,
  borderLeft: groupStart ? '1px solid var(--line)' : '1px solid var(--line-soft)',
  borderRight: groupEnd ? '1px solid var(--line)' : undefined,
})

// Parse numèric tolerant amb la COMA decimal (60,5 == 60.5). Buit → null; no-numèric → NaN.
// L'input editable és type=text inputMode=decimal perquè la coma s'hi pugui escriure (type=number la
// rebutja segons locale abans d'arribar a onChange).
const toNum = (v) => (v === '' || v == null) ? null : Number(String(v).replace(',', '.'))

const isModified = (value, baseValue) => value !== '' && value != null && baseValue != null
  && toNum(value) !== Number(baseValue)

// C2 (PRINCIPI DEL SOROLL) — fila CANDIDATA A PODA: cap valor real enlloc (base i talles totes a
// zero o buides, història inclosa). El model s'alimenta de realitat; una fila així no n'aporta cap.
// És un INDICADOR, no un automatisme: qui decideix és el tècnic, amb la columna d'acció.
const isNoiseRow = (row, groups) => {
  let vist = false
  for (const g of groups) {
    const cell = row.cells?.[g.key]
    if (!cell) continue
    const vals = []
    for (const h of (g.historyCols || [])) {
      const hv = cell.history?.[h.key]
      vals.push(hv && typeof hv === 'object' ? hv.value : hv)
    }
    if (cell.active) vals.push(cell.active.value)
    for (const v of vals) {
      if (v === null || v === undefined || v === '') continue
      vist = true
      if (Number(v) !== 0) return false
    }
  }
  // Sense cap valor llegit no es pot afirmar res: no es marca (millor callar que acusar).
  return vist
}

// Marcatge vermell de la cel·la activa: per defecte "difereix de base" (fitting); si l'active porta
// `tol` (check), vermell NOMÉS quan surt de la banda de tolerància [base-minus, base+plus].
const activeRed = (value, active) => {
  if (value === '' || value == null) return false
  if (active.tol && active.baseValue != null) {
    const v = toNum(value)
    return v < active.baseValue - active.tol.minus || v > active.baseValue + active.tol.plus
  }
  return isModified(value, active.baseValue)
}

// Indicador de COMENTARI de cel·la (repàs de fittings): un punt discret amb el text al `title`.
// Patró de tooltip de la casa (attr title, com el ★ KEY o la candidata a poda) — cap dependència
// nova. La dada arriba com history[key] = {value, nota} o active.nota; sense nota no es pinta res,
// de manera que els eixos que ja existien (check/fitting/escalat, valors nus) no canvien.
function NotaDot({ nota }) {
  if (!nota) return null
  return (
    <i className="ti ti-message-circle" title={nota} aria-label={nota}
      style={{ fontSize: 11, marginLeft: 4, color: 'var(--gold)', verticalAlign: 'middle' }} />
  )
}

// Cel·la activa editable (única amb input + autosave). Vermell si difereix de baseValue; negreta si
// editada a mà (ancoratge). Buida si no hi ha línia activa per a aquest (pom, grup).
const stepBtnStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'center', height: 11, width: 16,
  padding: 0, border: '1px solid var(--line)', background: 'var(--white)',
  color: 'var(--text-soft)', cursor: 'pointer', lineHeight: 1, fontSize: 'var(--fs-caption)',
}

// EL VEREDICTE PINTA EL NÚMERO (fitting_v3). L'etiqueta sola no bastava: el que es llegeix quan
// s'escombra la columna de dalt a baix és la XIFRA, i una xifra negra sota una etiqueta verda es
// llegeix com una mesura sense decidir. El color va al número, en negreta, i el rebuig el ratlla —
// que és el que vol dir «aquest valor no substitueix res».
// A9 · §1b(d) — l'ajustat va en `--warn-ink` com a TINTA (5.32:1). `--warn` era un taronja
// antic que no és cap dels tokens de la norma.
const VERDICTE_COL = { ACCEPTED: 'var(--ok)', ADJUSTED: 'var(--warn-ink)', REJECTED: 'var(--err)' }
// Les tecles del veredicte, en l'ordre del brief: A accepta · J ajusta · R rebutja. Viuen aquí i no
// a l'adaptador perquè el que les ha de sentir és el camp del número —la mà no en surt— i és
// aquest component qui el té. Sense `onVeredicte` (check, escalat, repàs) no s'escolta cap lletra.
const TECLA_VERDICTE = { a: 'ACCEPTED', j: 'ADJUSTED', r: 'REJECTED' }

function ActiveCell({ active, editable, value, edited, onChange, onCommit, focusRef, unit,
                      registerInput, onNav }) {
  const { t } = useTranslation()
  const [state, schedule] = useDebouncedSave(onCommit)
  const [focused, setFocused] = useState(false)
  // FIX-3 (DIAGNOSI_MESURES_TEA_205) — CAP FILA INERTA. Sense línia activa, aquí hi havia una
  // cel·la destacada i BUIDA: en una columna on totes les altres són caselles d'escriptura, es
  // llegeix com un camp que no respon, no com una absència. Un guió mut i el motiu al tooltip
  // diuen la veritat: en aquesta fila no hi ha res a anotar (encara).
  if (!active) {
    return (
      <td style={{ ...cellTd(true, false, false), color: 'var(--text-soft)' }}
        title={t('measuregrid.sense_linia')}>—</td>
    )
  }
  const modified = activeRed(value, active)
  // TRAM E — el valor de la talla base COPIAT: xifra en vermell i fons d'error suau, amb l'avís
  // al tooltip. Tokens de la llei G8 (`--err`/`--err-bg`), mai hex. El fons hi és perquè el
  // número, per definició, és igual al de la talla base: sense ell, una cel·la «correcta» i una
  // de prestada es veurien igual a la columna.
  const baseCopiada = !!active.baseCopiada
  const estilBaseCopiada = baseCopiada
    ? { background: 'var(--err-bg)', color: 'var(--err)' } : null
  const avisBaseCopiada = baseCopiada ? t('escalat.step_base_copiada') : undefined
  // E2b — pre-omplert sense gest: la xifra hi és perquè és la teòrica, no perquè ningú l'hagi
  // mesurada. Deixa de ser fantasma en tocar-la (`edited`), que és quan passa a ser una presa.
  const fantasma = !!active.fantasma && !edited
  const verdicte = active.veredicte || null
  const colVerdicte = verdicte ? VERDICTE_COL[verdicte] : null
  // `active.readonly` força lectura en una cel·la concreta encara que la graella sigui editable
  // (p.ex. la talla base de l'Escalat, que no s'edita com a override).
  if (!editable || active.readonly) {
    // Lectura: format de presentació (1 decimal cm · 2 inch). El veredicte també hi pinta: una
    // sessió segellada s'ha de poder rellegir amb els mateixos colors amb què es va decidir.
    return (
      <td title={avisBaseCopiada}
        style={{ ...cellTd(true, false, false),
                   ...estilBaseCopiada,
                   // E2b — el fantasma també en LECTURA: una consulta no pot fer passar per
                   // presa una xifra que ningú no ha mesurat (és la llei d'E1 a la pantalla).
                   color: baseCopiada ? 'var(--err)'
                     : fantasma ? 'var(--text-soft)'
                     : (colVerdicte || (modified ? 'var(--err)' : 'var(--text-main)')),
                   // `active.canvi` (B2) posa la negreta a la columna activa amb el mateix
                   // criteri que a les d'història: un canvi es marca encara que ningú no li
                   // hagi posat veredicte. Qui no l'envia, com abans.
                   fontWeight: verdicte || active.canvi ? 600 : undefined,
                   textDecoration: verdicte === 'REJECTED' ? 'line-through' : undefined }}>
        {fmtMeasure(value, unit) ?? '—'}
        <NotaDot nota={active.nota} />
      </td>
    )
  }
  // Edició: mentre s'escriu (focus) es mostra el valor CRU per teclejar lliure (coma inclosa); en
  // perdre el focus es mostra FORMATAT (1 decimal cm · 2 inch), coherent amb les cel·les de lectura.
  // Es desa sempre el valor canònic (toNum normalitza la coma al commit). type=text + fletxes pròpies
  // (type=number no admet coma; les fletxes natives només existeixen a type=number → es recreen aquí).
  const num = toNum(value)
  const shown = focused
    ? (value ?? '')
    : (num == null || Number.isNaN(num) ? (value ?? '') : fmtMeasure(num, unit))
  const bump = (dir) => {
    const baseN = (num == null || Number.isNaN(num)) ? 0 : num
    const next = String(Math.round((baseN + dir * 0.1) * 100) / 100)   // pas 0.1 (cm canònic)
    onChange(active.lineId, next)
    schedule(next)
  }
  return (
    <td title={avisBaseCopiada}
      style={{ ...cellTd(true, false, false), position: 'relative' }}>
      <span style={{ display: 'inline-flex', alignItems: 'stretch', gap: 2 }}>
        <input
          ref={el => registerInput?.(active.lineId, el)}
          type="text" inputMode="decimal" value={shown}
          onFocus={e => { setFocused(true); focusRef.current = active.lineId; e.target.select() }}
          onBlur={() => { setFocused(false); if (focusRef.current === active.lineId) focusRef.current = null }}
          onChange={e => { onChange(active.lineId, e.target.value); schedule(e.target.value) }}
          onKeyDown={e => {
            // EL VEREDICTE DES DEL TECLAT, sense sortir del número (fitting_v3). Només on n'hi ha:
            // en una graella sense veredicte una `a` no ha de fer res que l'usuari no esperi.
            const k = e.key.toLowerCase()
            if (active.onVeredicte && TECLA_VERDICTE[k] && !e.ctrlKey && !e.metaKey && !e.altKey) {
              e.preventDefault(); active.onVeredicte(TECLA_VERDICTE[k]); return
            }
            // E2b — ENTER SOBRE UN FANTASMA EL CONFIRMA. La cel·la surt pre-omplerta amb la
            // teòrica i això NO és una presa; l'Enter és el gest que diu «la peça arribada fa
            // exactament això». Sense aquesta branca, confirmar exigiria reteclejar el mateix
            // número, i el debounce d'`onChange` no salta perquè no hi ha hagut cap canvi.
            //
            // Va ABANS del `if (!onNav)`: confirmar no pot dependre de si hi ha carril. I només
            // amb `fantasma && !edited` — un cop l'usuari l'ha tocada, la cel·la ja és una presa
            // pel camí normal i l'Enter torna a ser només navegació.
            if (e.key === 'Enter' && active.fantasma && !edited) onCommit(value)
            if (!onNav) return
            if (e.key === 'ArrowDown' || e.key === 'Enter') { e.preventDefault(); onNav(active.lineId, 1) }
            else if (e.key === 'ArrowUp') { e.preventDefault(); onNav(active.lineId, -1) }
          }}
          style={{
            // S45/G2 — `center`, com la cel·la que substitueix mentre s'edita: amb l'input
            // a la dreta i la cel·la centrada, la xifra SALTAVA en clicar-hi.
            font: 'inherit', width: 70, padding: '2px 4px', textAlign: 'center',
            border: `1px solid ${colVerdicte || 'var(--line)'}`, borderRadius: 4, background: 'var(--white)',
            // ── E2c-bis (decisió d'Agus, 17/08) · GRIS NORMAL I RECTE ────────────────────
            // Això anava en `--text-faint` + CURSIVA, llegint el pre-omplert com un «estat
            // buit». No ho és: **és la mesura vigent de la presa actual**, vàlida mentre ningú
            // no la toqui. La cursiva la feia semblar provisional i el `--text-faint` (3.05:1,
            // reservat per norma a «deshabilitat i estats buits», `index.css:72`) la feia
            // semblar inactiva.
            //
            // Ara `--text-soft` (5.37:1, «secundari»): **gris perquè no està confirmada, recta
            // perquè és un valor de debò**. La distinció fantasma/presa NO es toca — segueix
            // sencera per sota, i qui mana és `presa_at`. Això és crom, no semàntica.
            // TRAM E — en EDICIÓ la marca es queda: la cel·la prestada s'ha de reconèixer
            // mentre s'hi escriu, que és exactament quan s'està reparant.
            ...(baseCopiada && !edited ? { background: 'var(--err-bg)' } : null),
            color: baseCopiada && !edited ? 'var(--err)'
              : fantasma ? 'var(--text-soft)'
              : (colVerdicte || (modified ? 'var(--err)' : 'var(--text-main)')),
            fontWeight: verdicte || (modified && edited) ? 700 : 400,
            textDecoration: verdicte === 'REJECTED' ? 'line-through' : undefined,
            fontVariantNumeric: 'tabular-nums', boxSizing: 'border-box',
          }}
        />
        <span style={{ display: 'inline-flex', flexDirection: 'column', justifyContent: 'center' }}>
          <button type="button" tabIndex={-1} title="+0.1" aria-label="+0.1"
            onMouseDown={e => e.preventDefault()} onClick={() => bump(1)}
            style={{ ...stepBtnStyle, borderRadius: '4px 4px 0 0', borderBottom: 'none' }}>
            <i className="ti ti-chevron-up" />
          </button>
          <button type="button" tabIndex={-1} title="-0.1" aria-label="-0.1"
            onMouseDown={e => e.preventDefault()} onClick={() => bump(-1)}
            style={{ ...stepBtnStyle, borderRadius: '0 0 4px 4px' }}>
            <i className="ti ti-chevron-down" />
          </button>
        </span>
      </span>
      <SaveStatus state={state} absolute />
    </td>
  )
}

// Sprint NOMS-POM (30/07) — input inline del BATEIG: ASPECTE DE TEXT PLA en repòs, camp en
// hover/focus (maqueta aprovada, pestanya 1). Desa on-blur i només si el text ha canviat de debò.
// Buit no és un buit: el placeholder ensenya el que en diu el CATÀLEG, que és qui mana mentre
// ningú no bategi la línia — la cel·la no es queda muda mai.

// Nomenclatura a 2 línies (llei de presentació): nom EN canònic a dalt (sembra, read-only) + nom
// local a sota (petit, cursiva, gris). Aquesta cel·la és DESCRIPTIVA (només noms); la nomenclatura
// CURTA (nom_fitxa, CH/WA/HI) s'edita a la columna POM (CodiCell) quan `editCodi`. Llegat: quan
// `editCodi` és fals (fitting), la 2a línia mostra nom_fitxa amb precedència i és EDITABLE via
// `onNomSave(bmId, value)` (P4: NO toca el POM tenant compartit).
function NomCell({ nomEn, nomLocal, nomFitxa, nomCanonicModel = '', nomTraduitModel = '',
                   instancia = '', marca = null, bmId, editable, onNomSave, onNomsSave = null,
                   editCodi = false, style, traduccio = '' }) {
  const { t } = useTranslation()
  const dicc = useDiccionariMesures()
  // La INSTÀNCIA s'enganxa al nom en TOTES les branques: és el nom d'aquesta mesura el que
  // s'allarga («Front armhole · Left»), i el que no pot passar és que la germana esquerra i la
  // dreta es llegeixin igual segons per quina branca hi entri la cel·la.
  // Va en ANGLÈS CANÒNIC i no es tradueix (05/08): és la paraula que allarga el nom del POM i
  // de la qual surt el sufix del codi. El diccionari mana quan hi és.
  const inst = etiquetaInstancia(instancia, dicc)
  const Inst = () => (inst ? <span style={{ fontWeight: 500 }}>{` · ${inst}`}</span> : null)
  // v3 (`.tagd`) — una germana que el sistema ha mogut sola porta etiqueta. El número d'una
  // derivada s'assembla a un de mesurat, i qui llegeix la columna de dalt a baix ha de poder
  // distingir una PRESA d'un CÀLCUL sense obrir res.
  const Marca = () => (marca ? (
    <span style={{ fontSize: 'var(--fs-caption)', border: '1px solid var(--line)',
                   borderRadius: 999, padding: '1px 7px', marginLeft: 6, whiteSpace: 'nowrap',
                   color: 'var(--text-soft)', background: 'var(--white)' }}>
      {t(`fitting.grid.marca_${marca}`)}
    </span>
  ) : null)
  const catCanonic = nomEn || nomLocal || ''
  const canon = nomEn && nomLocal && nomLocal !== nomEn ? nomLocal : (nomLocal || '')
  // editCodi → la 2a línia és el nom LOCAL (la nomenclatura curta viu a la columna POM, no aquí).
  const catLocal = editCodi ? canon : ((nomFitxa != null && nomFitxa !== '') ? nomFitxa : canon)
  const canEdit = !!(editable && bmId != null && onNomSave && !editCodi)
  // Sprint NOMS-POM (30/07) — EL BATEIG DEL MODEL. Amb `onNomsSave` les DUES línies passen a ser
  // el bateig d'aquesta línia de mesura (nom canònic EN + traducció del client) i s'editen aquí
  // mateix. Sense `onNomsSave` (fitting, repàs, consulta) la cel·la és EXACTAMENT la d'abans:
  // el bateig només hi entra com a precedència de LECTURA, i buit no canvia res.
  const bateig = !!(onNomsSave && editable && bmId != null)
  const top = nomCanonicModel || catCanonic
  // El llegat que edita `nom_fitxa` a la 2a línia mana sobre la precedència del bateig: allà
  // l'input ÉS la nomenclatura curta i no s'hi pot sobreposar un altre text.
  const modelName = canEdit ? catLocal : (nomTraduitModel || catLocal)
  const [val, setVal] = useState(modelName ?? '')
  const [focused, setFocused] = useState(false)
  useEffect(() => { if (!focused) setVal(modelName ?? '') }, [modelName, focused])
  const commit = () => {
    setFocused(false)
    const v = (val ?? '').trim()
    if (v !== (modelName ?? '')) onNomSave(bmId, v)
  }
  // Les DUES línies del nom, editables i amb el catàleg de fons (Mesures). Cada input desa el
  // seu camp per separat: rebatejar el canònic no ha d'arrossegar la traducció, ni al revés.
  if (bateig) {
    // Les DUES línies segueixen sent camps: aquí la segona no és un subtítol, és la superfície on
    // es bateja la traducció (P3 demana la identitat de fila, no que desaparegui un editor).
    return (
      <td style={style}>
        <div style={{ display: 'flex', alignItems: 'baseline' }}>
          <span style={{ flex: 1, minWidth: 0 }}>
            <BateigInput value={nomCanonicModel} placeholder={catCanonic || ''}
              title={t('measuregrid.nom_canonic_tip')}
              onSave={(v) => onNomsSave(bmId, { nom_canonic_model: v })}
              style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)' }} />
          </span>
          <span style={{ flex: 'none', fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}><Inst /></span>
        </div>
        <BateigInput value={nomTraduitModel} placeholder={catLocal || ''}
          title={t('measuregrid.nom_traduit_tip')}
          onSave={(v) => onNomsSave(bmId, { nom_traduit_model: v })}
          style={{ fontSize: 'var(--fs-caption)', fontStyle: 'italic', color: 'var(--text-soft)' }} />
      </td>
    )
  }
  // LECTURA PURA (Escalat, Repàs): el nom local deixa de ser una segona línia permanent i passa a
  // la ⓘ, com a P1. Aquí no s'hi edita res, o sigui que la línia només ocupava alçada; el que ha
  // de saltar a la vista en una taula amb germanes és QUINA mesura és cada fila.
  if (!canEdit) {
    // `traduccio` (tram ⓘ) va l'ÚLTIMA: el bateig del model i el nom del catàleg manen per
    // damunt del que digui un servei extern. Fins avui aquí no hi arribava mai res —el catàleg
    // v4 no porta noms locals— i la ⓘ d'aquestes tres pantalles no sortia mai.
    // Un nom local que repeteix el canònic no tapa la traducció demanada: v. la nota de la
    // mateixa regla a `EditableTable`.
    const candidat = (modelName && modelName !== top ? modelName : '') || traduccio
    const local = candidat && candidat !== top ? candidat : ''
    return (
      <td style={style}>
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', whiteSpace: 'normal' }}>
          {top || '—'}<Inst /><Marca />
          {/* LA MATEIXA ⓘ QUE LES ALTRES TAULES, no una que se li assembli. Aquí n'hi havia una
              de pròpia amb `title` natiu: el mecanisme que el 06/08 ja es va diagnosticar com a
              inservible —només surt amb el ratolí a sobre i esperant-se, no respon al clic ni al
              teclat, i sobre 12px la meitat de les vegades no arriba a sortir—. */}
          {local && <InfoTraduccio text={local} />}
        </div>
      </td>
    )
  }
  // LLEGAT (fitting): la 2a línia ÉS la nomenclatura curta del model i s'hi escriu. No es toca.
  return (
    <td style={style}>
      <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', whiteSpace: 'normal' }}>{top || '—'}<Inst /><Marca /></div>
      <input
        value={val ?? ''} onChange={e => setVal(e.target.value)}
        onFocus={() => setFocused(true)} onBlur={commit}
        onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur() }}
        placeholder={canon || ''}
        style={{
          font: 'inherit', fontSize: 'var(--fs-caption)', fontStyle: 'italic',
          color: 'var(--text-soft)', width: '100%', padding: '0 2px', boxSizing: 'border-box',
          borderRadius: 3, background: focused ? 'var(--white)' : 'transparent',
          // Affordance: subratllat tènue en repòs (pista d'editabilitat) → vora completa en focus.
          border: '1px solid transparent',
          borderBottom: focused ? '1px solid var(--line)' : '1px dashed var(--line)',
          ...(focused && { borderColor: 'var(--line)' }),
        }}
      />
    </td>
  )
}

// Columna POM = nomenclatura CURTA del model (nom_fitxa: CH/WA/HI). En lectura mostra `codi`
// (nom_fitxa || pom_code global). En edició (`editCodi` + bmId + onNomSave) és un input que desa
// nom_fitxa per-model via onNomSave (NO toca el POM global; placeholder = codi global per defecte).
// Mateix patró que el llegat del NomCell: buffer local, commit on blur, affordance només si editable.
function CodiCell({ codi, nomFitxa, pomCode, bmId, isKey, editable, editCodi, onNomSave, reorderable, style, title }) {
  const { t } = useTranslation()
  const canEdit = !!(editable && editCodi && bmId != null && onNomSave)
  const [val, setVal] = useState(nomFitxa ?? '')
  const [focused, setFocused] = useState(false)
  useEffect(() => { if (!focused) setVal(nomFitxa ?? '') }, [nomFitxa, focused])
  const commit = () => {
    setFocused(false)
    const v = (val ?? '').trim()
    if (v !== (nomFitxa ?? '')) onNomSave(bmId, v)
  }
  return (
    <td style={style} title={title}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        {reorderable && (
          <i className="ti ti-grip-vertical" title={t('measuregrid.reorder')}
            style={{ fontSize: 12, color: 'var(--text-soft)', cursor: 'grab' }} />
        )}
        {canEdit ? (
          <input
            value={val ?? ''} onChange={e => setVal(e.target.value)}
            onFocus={() => setFocused(true)} onBlur={commit}
            onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur() }}
            placeholder={pomCode || ''}
            style={{
              font: 'inherit', fontWeight: 500, color: 'var(--gold)', width: 52,
              padding: '0 2px', boxSizing: 'border-box', borderRadius: 3,
              background: focused ? 'var(--white)' : 'transparent',
              // Affordance: subratllat tènue en repòs → vora completa en focus.
              border: '1px solid transparent',
              borderBottom: focused ? '1px solid var(--line)' : '1px dashed var(--line)',
              ...(focused && { borderColor: 'var(--line)' }),
            }}
          />
        ) : (
          <span style={{ fontWeight: 500, color: 'var(--gold)' }}>{codi}</span>
        )}
        {isKey && <i className="ti ti-star" style={{ fontSize: 14, marginLeft: 3, color: 'var(--gold)' }} title="KEY" />}
      </span>
    </td>
  )
}

export default function MeasureGrid({
  rows = [],
  groups = [],            // [{key, label, accent?, historyCols:[{key,label}], activeLabel, trailCols:[{key,label}]}]
  leadCols = [],          // [{key, label, width, render:(row)=>node}]  sticky després de POM/Nom (consulta: render pot ser text)
  // FIX-4 (DIAGNOSI_MESURES_TEA_205) — MESURA i DELTA no es poden confondre. Amb `leadGroupLabel`
  // la graella guanya una FILA DE CAPÇALERA per damunt: els leadCols queden agrupats sota el seu
  // títol i amb el fons crema de la casa, i els grups de talla sota el seu. Al 205 algú va escriure
  // l'increment `1` a la cel·la de talla d'un POM amb base 46; el camp Δ i la cel·la de mesura eren
  // dos números iguals a pocs píxels, sense res que digués que són coses diferents.
  // OPT-IN: sense `leadGroupLabel` la capçalera és exactament la de sempre (check i fitting intactes).
  leadGroupLabel = null,  // títol del bloc de leadCols (p.ex. "Regla de graduació")
  groupsLabel = null,     // títol del bloc de grups de talla (p.ex. "Mesures per talla")
  editable = false,
  onSave,                 // (lineId, rawValue) => Promise (pot resoldre amb {lines:[{id,valor_real}]} per propagar)
  onNomSave = null,       // (bmId, value) => Promise — desa la nomenclatura curta del MODEL (nom_fitxa, P4); null = no editable
  // Sprint NOMS-POM — (bmId, {nom_canonic_model?|nom_traduit_model?}) => Promise: desa el BATEIG
  // de la línia. OPT-IN: null (fitting, repàs, consulta) → la cel·la del nom és la de sempre.
  onNomsSave = null,
  editCodi = false,       // on s'edita nom_fitxa: true → columna POM (codi curt CH/WA/HI, Mesures); false → 2a línia del Nom (fitting, llegat)
  reorderable = false,    // DnD de files (NOMÉS Mesures-edició); default false → Escalat/fitting/consulta intactes
  onReorder = null,       // (orderedBmIds) => Promise — desa el nou ordre global del model
  onPodar = null,         // C1 — (row) => Promise: treu el POM del model (SOFT). null = cap columna d'acció
  empty = null,           // node quan no hi ha files
}) {
  const { t, i18n } = useTranslation()
  // Les capes es diuen com el diccionari de la BD diu (F2.2), en l'idioma de qui llegeix.
  const dicc = useDiccionariMesures()
  const lang = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)
  const unit = useUnit()                       // unitat del tenant (CM|INCH) → format de presentació
  // EL VOCABULARI, A NIVELL DE GRAELLA. Qui el consumeix és `NomCell` (una cel·la per fila), i una
  // cel·la no és el lloc d'anunciar una fallada de xarxa: la graella pregunta per l'ESTAT i, si no
  // ha arribat, ho diu una vegada a dalt. La cel·la segueix amb `useDiccionariMesures` — la font
  // memoritza la resposta a nivell de mòdul, o sigui que no és una segona petició.
  const { error: diccError, reintenta: reintentaDicc } = useEstatDiccionari()
  const [vals, setVals] = useState({})        // buffer local lineId -> string
  const [edited, setEdited] = useState(() => new Set())  // ancoratge (editat a mà)
  const focusRef = useRef(null)
  const dragFrom = useRef(null)
  // C1 — confirmació LLEUGERA (dos temps a la mateixa fila, sense modal): el primer clic arma
  // la fila, el segon la poda. Treure una mesura del model no ha de ser un clic distret.
  const [podaArmada, setPodaArmada] = useState(null)   // pom_id
  const [podant, setPodant] = useState(false)
  const canPodar = !!(editable && onPodar)
  // Reordena (DnD): en deixar anar, calcula el nou ordre de bm_id i ho delega a onReorder (que desa +
  // refresca). Sense estat visual local: la fila es recol·loca en rellegir (simple i sense desincronies).
  const onRowDrop = (toIdx) => {
    const from = dragFrom.current
    dragFrom.current = null
    if (from == null || from === toIdx || !onReorder) return
    const ids = rows.map(r => r.bm_id)
    const [moved] = ids.splice(from, 1)
    ids.splice(toIdx, 0, moved)
    onReorder(ids.filter(x => x != null))
  }

  // Sincronitza el buffer des de les props quan canvien els valors actius (excepte la cel·la amb focus,
  // perquè la propagació/refresc no trepitgi el que l'usuari està escrivint).
  useEffect(() => {
    setVals(prev => {
      const next = { ...prev }
      for (const r of rows) {
        for (const g of groups) {
          const a = r.cells?.[g.key]?.active
          if (a && a.lineId !== focusRef.current && next[a.lineId] === undefined) {
            next[a.lineId] = a.value ?? ''
          }
        }
      }
      return next
    })
  }, [rows, groups])

  const onChange = useCallback((lineId, raw) => {
    setVals(prev => ({ ...prev, [lineId]: raw }))
    setEdited(prev => { const n = new Set(prev); n.add(lineId); return n })
  }, [])

  // EL CARRIL DINS DE LA COLUMNA (fitting_v3 · v8.1): ↓/Enter baixa i ↑ puja, SENSE canviar de
  // columna. Es navega dins del MATEIX grup a posta —una graella d'Escalat té una columna per
  // talla i saltar de talla a mig recorregut seria perdre el fil de la mesura que s'està prenent.
  // Els inputs es registren per `lineId`, que és la identitat que ja fa servir tot el buffer.
  const inputRefs = useRef({})
  const registerInput = useCallback((lineId, el) => {
    if (el) inputRefs.current[lineId] = el
    else delete inputRefs.current[lineId]
  }, [])
  // LA ⓘ TÉ FONT (tram ⓘ): un sol lot per graella, compartit per Escalat, Comprovació, Repàs i
  // Fitting, que són les quatre pantalles que munten aquesta graella.
  const traduccioDe = useTraduccioPoms(rows.map(r => r.pom_id))
  const gridRef = useRef({ rows, groups })
  useEffect(() => { gridRef.current = { rows, groups } }, [rows, groups])
  const onNav = useCallback((lineId, dir) => {
    const { rows: rr, groups: gg } = gridRef.current
    for (const g of gg) {
      const carril = rr.map(r => r.cells?.[g.key]?.active)
        .filter(a => a && !a.readonly).map(a => a.lineId)
      const i = carril.indexOf(lineId)
      if (i < 0) continue
      const seguent = carril[i + dir]
      if (seguent != null) inputRefs.current[seguent]?.focus()
      return
    }
  }, [])

  const commitFor = useCallback((lineId) => (raw) => {
    if (!onSave) return Promise.resolve()
    const num = toNum(raw)
    if (Number.isNaN(num)) return Promise.resolve()   // entrada incompleta/no-numèrica → no desa
    return Promise.resolve(onSave(lineId, num)).then(res => {
      const propagated = res && res.data ? res.data.linies || res.data.lines : (res && (res.linies || res.lines))
      if (Array.isArray(propagated)) {
        setVals(prev => {
          const next = { ...prev }
          for (const l of propagated) {
            if (l.id !== focusRef.current) next[l.id] = l.valor_real ?? ''
          }
          return next
        })
      }
      return res
    })
  }, [onSave])

  if (!rows.length) return empty

  // Offsets sticky acumulats: Capa(0) · POM · Nom · leadCols… (sense mutació, per al react-compiler).
  const baseLeft = COL_CAPA_W + COL_POM_W + COL_NOM_W
  const leadLefts = leadCols.map((_, i) => baseLeft + leadCols.slice(0, i).reduce((s, c) => s + c.width, 0))

  // FIX-4 deia el bloc de REGLA amb dos senyals: un FONS crema i un SEPARADOR gruixut just abans
  // de les mesures. AGUS (10/08, re-confirmat a pantalla el 12) EN TREU EL FONS: la regla és part
  // de la LÍNIA INFORMATIVA DEL POM, i el crema la convertia en una taula estrangera enganxada al
  // costat de la fila. La cel·la agafa el fons de la SEVA fila, com totes les altres.
  //
  // El que agrupa passa a ser el que ja hi havia i no s'aprofitava: la CAPÇALERA DE GRUP. Ara n'hi
  // ha tres i no dues —«POMs definits» sobre CAPA·POM·NOM, «Regla de graduació», «Mesures per
  // talla»— i el filet gruixut segueix tallant on toca. Nomenar és més fort que tenyir: un color
  // s'ha d'endevinar i un rètol es llegeix.
  const agrupat = !!leadGroupLabel
  const SEP = '2px solid var(--line)'                  // separador Regla | Mesures
  const esUltimLead = (i) => agrupat && i === leadCols.length - 1
  // I LES COLUMNES DE LA REGLA, A L'AMPLADA DEL SEU CONTINGUT. El que les eixamplava no eren els
  // valors —«+2,0», «XS»— sinó el RÈTOL: a 10px amb tracking .08em i `nowrap`, «TALLA BREAK» sol
  // demana ~103 px de columna per a un número de tres caràcters. Amb el rètol embolicat (ja té el
  // seu grup a sobre, que és qui diu de què va) i el padding retallat, qui mesura és la xifra.
  const leadHd = { whiteSpace: 'normal', padding: '0.5rem 0.4rem', lineHeight: 1.15 }

  const stickyHd = (left, w, i = null) => ({
    ...thStyle, position: 'sticky', left, zIndex: 3, minWidth: w, width: w,
    background: 'var(--panel)', textAlign: 'left',
    ...((agrupat && i != null) ? leadHd : null),
    ...(esUltimLead(i) && { borderRight: SEP }),
  })
  const stickyTd = (left, w, bg, i = null) => ({
    position: 'sticky', left, zIndex: 1, minWidth: w, width: w, background: bg,
    padding: (agrupat && i != null) ? '5px 6px' : '5px 10px',
    borderBottom: '1px solid var(--line-soft)',
    verticalAlign: 'middle', whiteSpace: 'nowrap',
    ...(esUltimLead(i) && { borderRight: SEP }),
  })
  const totalGroupCols = groups.reduce(
    (s, g) => s + (g.historyCols?.length || 0) + 1 + (g.trailCols?.length || 0), 0)
  const identitatHd = (left, w) => stickyHd(left, w)     // POM/Nom: mai del bloc de regla

  return (
    <>
      {diccError && (
        <AvisDiccionari hint={t('dicc.error_hint_noms')} onReintenta={reintentaDicc} />
      )}
    <div style={{ overflow: 'auto', maxHeight: '70vh', width: '100%' }}>
      <table style={{ borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
        <thead>
          {agrupat && (
            <tr>
              {/* SIMETRIA (Agus, 10/08): si la regla i les talles porten rètol de grup, les tres
                  columnes d'IDENTITAT també. Sense ell la fila de dalt començava en blanc i
                  «Regla de graduació» es llegia com el títol de TOTA la taula.
                  Sticky com les columnes que encapçala: un rètol de grup que llisca mentre les
                  seves columnes es queden clavades deixa de nomenar-les. Mateix motiu per al de
                  la regla, que fins ara no ho era. */}
              <th colSpan={3} style={stickyHd(0, baseLeft)}>{t('measuregrid.grup_poms')}</th>
              {leadCols.length > 0 && (
                <th colSpan={leadCols.length} style={{
                  ...thStyle, position: 'sticky', left: baseLeft, zIndex: 3,
                  textAlign: 'center', background: 'var(--panel)', borderRight: SEP,
                }}>{leadGroupLabel}</th>
              )}
              {totalGroupCols > 0 && (
                <th colSpan={totalGroupCols} style={{
                  ...thStyle, textAlign: 'center', background: 'var(--panel)',
                }}>{groupsLabel}</th>
              )}
              {canPodar && (
                <th rowSpan={3} style={{ ...thStyle, textAlign: 'center', width: 64, minWidth: 64,
                                         background: 'var(--panel)', borderLeft: '1px solid var(--line)' }}>
                  {t('measuregrid.col_accions')}
                </th>
              )}
            </tr>
          )}
          <tr>
            {/* Les tres d'identitat viuen SEMPRE en aquesta fila: amb grups, sota el seu rètol
                («POMs definits»); sense grups, com abans. El `rowSpan` cobreix la fila de
                sub-columnes en tots dos casos. */}
            <th rowSpan={2} style={identitatHd(0, COL_CAPA_W)}>{t('capa.col')}</th>
            <th rowSpan={2} style={identitatHd(COL_CAPA_W, COL_POM_W)}>{t('measuregrid.col_pom')}</th>
            <th rowSpan={2} style={identitatHd(COL_CAPA_W + COL_POM_W, COL_NOM_W)}>{t('measuregrid.col_nom')}</th>
            {leadCols.map((c, i) => (
              <th key={c.key} rowSpan={2} style={stickyHd(leadLefts[i], c.width, i)}>{c.label}</th>
            ))}
            {groups.map(g => {
              const span = (g.historyCols?.length || 0) + 1 + (g.trailCols?.length || 0)
              return (
                <th key={g.key} colSpan={span} style={{
                  ...thStyle, textAlign: 'center',
                  background: 'var(--panel)',
                  borderLeft: '1px solid var(--line)',
                }}>{g.label}</th>
              )
            })}
            {!agrupat && canPodar && (
              <th rowSpan={2} style={{ ...thStyle, textAlign: 'center', width: 64, minWidth: 64,
                                       background: 'var(--panel)', borderLeft: '1px solid var(--line)' }}>
                {t('measuregrid.col_accions')}
              </th>
            )}
          </tr>
          <tr>
            {groups.flatMap(g => {
              // S45/G2 — la subcapçalera de valor va on van els valors: centrada.
              const sub = (start) => ({ ...thStyle, textAlign: 'center', fontSize: 'var(--fs-caption)', padding: '3px 8px',
                background: 'var(--panel)',
                borderLeft: start ? '1px solid var(--line)' : '1px solid var(--line-soft)' })
              const activeSub = { ...sub(false), background: 'var(--sel)' }   // NOMÉS la columna activa destaca
              const hs = (g.historyCols || []).map((h, idx) => <th key={`${g.key}-h-${h.key}`} style={sub(idx === 0)}>{h.label}</th>)
              hs.push(<th key={`${g.key}-active`} style={activeSub}>{g.activeLabel}</th>)
              for (const tcol of (g.trailCols || [])) hs.push(<th key={`${g.key}-t-${tcol.key}`} style={{ ...sub(false), textAlign: 'center' }}>{tcol.label}</th>)
              return hs
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const rowBg = i % 2 === 0 ? 'var(--white)' : 'var(--bg-page)'
            // C2 — candidata a poda: indicador SUBTIL (un filet a l'esquerra), mai un automatisme.
            const soroll = isNoiseRow(r, groups)
            return (
              // C4/BLOC 3 — la clau de React de la FILA no pot ser el `pom_id`. Aquesta
              // graella la comparteixen les quatre superfícies (Mesures, Escalat, Fitting,
              // Repàs) i totes quatre poden servir dues germanes del mateix POM: dues `<tr>`
              // amb la mateixa clau fan que React en reconciliï una amb l'estat de l'altra
              // —cel·la enfocada, ordre en arrossegar— i avisi per consola sense que res peti.
              // `rowKey` el posa cada adaptador amb la identitat més forta que el SEU payload
              // li dona; el `pom_id` queda de pla B per a qui encara no en pot donar cap.
              <tr key={r.rowKey || r.pom_id} style={{ background: rowBg }}
                draggable={reorderable || undefined}
                onDragStart={reorderable ? (() => { dragFrom.current = i }) : undefined}
                onDragOver={reorderable ? (e => e.preventDefault()) : undefined}
                onDrop={reorderable ? (() => onRowDrop(i)) : undefined}>
                {/* LA CAPA (D-31.22), en lectura i sempre present. Una fila sense `capa` al
                    payload és l'exterior de sempre: `etiquetaCapa` ho resol, i així cap
                    adaptador que encara no la serveixi deixa la columna muda. */}
                <td style={{ ...stickyTd(0, COL_CAPA_W, rowBg), whiteSpace: 'normal',
                             color: 'var(--text-main)' }}>
                  {etiquetaCapa(r.capa, dicc, lang)}
                </td>
                <CodiCell codi={r.codi} nomFitxa={r.nom_fitxa} pomCode={r.pom_code} bmId={r.bm_id}
                  isKey={r.is_key} editable={editable} editCodi={editCodi} onNomSave={onNomSave}
                  reorderable={reorderable}
                  style={soroll
                    ? { ...stickyTd(COL_CAPA_W, COL_POM_W, rowBg), boxShadow: 'inset 3px 0 0 var(--line)' }
                    : stickyTd(COL_CAPA_W, COL_POM_W, rowBg)}
                  title={soroll ? t('measuregrid.poda_candidata') : undefined} />
                <NomCell nomEn={r.nom_en} nomLocal={r.nom_local} nomFitxa={r.nom_fitxa} bmId={r.bm_id}
                  traduccio={traduccioDe(r.pom_id)}
                  nomCanonicModel={r.nom_canonic_model} nomTraduitModel={r.nom_traduit_model}
                  instancia={r.instancia} marca={r.marca}
                  editable={editable} onNomSave={onNomSave} onNomsSave={onNomsSave}
                  editCodi={editCodi} style={stickyTd(COL_CAPA_W + COL_POM_W, COL_NOM_W, rowBg)} />
                {leadCols.map((c, idx) => (
                  <td key={c.key} style={stickyTd(leadLefts[idx], c.width, rowBg, idx)}>{c.render(r)}</td>
                ))}
                {groups.flatMap(g => {
                  const cell = r.cells?.[g.key] || {}
                  const out = (g.historyCols || []).map((h, idx) => {
                    const hv = cell.history?.[h.key]
                    const obj = hv && typeof hv === 'object'
                    const v = obj ? hv.value : hv
                    // EL CANVI ES MARCA (B2 · Agus, 10/08). Una columna d'història pintava tota
                    // en negre i el que hi passava —quin número s'havia mogut respecte de
                    // l'anterior— s'havia de trobar comparant xifra a xifra amb el dit.
                    // NEGRETA quan la cel·la canvia, i el color el posa el VEREDICTE de la
                    // modista (la paleta de sempre, `VERDICTE_COL`); sense veredicte, negreta
                    // sola. La resta, normal.
                    //
                    // Additiu a posta: qui no envia `canvi`/`veredicte` (fitting, escalat) pinta
                    // exactament igual que abans.
                    const canviat = obj && !!hv.canvi
                    const colVerd = canviat && hv.veredicte ? VERDICTE_COL[hv.veredicte] : null
                    return (
                      <td key={`${g.key}-h-${h.key}`}
                        style={{ ...cellTd(false, idx === 0, false),
                                 color: colVerd || 'var(--text-main)',
                                 fontWeight: canviat ? 600 : undefined,
                                 textDecoration: canviat && hv.veredicte === 'REJECTED'
                                   ? 'line-through' : undefined }}>
                        {fmtMeasure(v, unit) ?? '—'}
                        {obj && <NotaDot nota={hv.nota} />}
                      </td>
                    )
                  })
                  const a = cell.active
                  out.push(
                    <ActiveCell key={`${g.key}-active`} active={a} editable={editable} unit={unit}
                      value={a ? (vals[a.lineId] ?? '') : ''} edited={a ? edited.has(a.lineId) : false}
                      onChange={onChange} onCommit={a ? commitFor(a.lineId) : (() => Promise.resolve())} focusRef={focusRef}
                      registerInput={registerInput} onNav={onNav} />
                  )
                  for (const tcol of (g.trailCols || [])) {
                    out.push(<td key={`${g.key}-t-${tcol.key}`} style={{ padding: '5px 8px', borderBottom: '1px solid var(--line-soft)', verticalAlign: 'middle' }}>{cell.trail?.[tcol.key] ?? null}</td>)
                  }
                  return out
                })}
                {canPodar && (
                  <td style={{ padding: '5px 8px', borderBottom: '1px solid var(--line-soft)',
                               borderLeft: '1px solid var(--line)', textAlign: 'center',
                               verticalAlign: 'middle', whiteSpace: 'nowrap' }}>
                    {podaArmada === r.pom_id ? (
                      <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                        <button type="button" title={t('measuregrid.poda_confirma')}
                          aria-label={t('measuregrid.poda_confirma')} disabled={podant}
                          onClick={() => {
                            setPodant(true)
                            Promise.resolve(onPodar(r))
                              .finally(() => { setPodant(false); setPodaArmada(null) })
                          }}
                          style={{ border: 'none', background: 'transparent', cursor: podant ? 'wait' : 'pointer',
                                   color: 'var(--err)', padding: 2, lineHeight: 1 }}>
                          <i className="ti ti-check" aria-hidden="true" style={{ fontSize: 15 }} />
                        </button>
                        <button type="button" title={t('common.cancel')} aria-label={t('common.cancel')}
                          onClick={() => setPodaArmada(null)}
                          style={{ border: 'none', background: 'transparent', cursor: 'pointer',
                                   color: 'var(--text-soft)', padding: 2, lineHeight: 1 }}>
                          <i className="ti ti-x" aria-hidden="true" style={{ fontSize: 15 }} />
                        </button>
                      </span>
                    ) : (
                      <button type="button" title={t('measuregrid.poda_title')}
                        aria-label={t('measuregrid.poda_title')}
                        onClick={() => setPodaArmada(r.pom_id)}
                        style={{ border: 'none', background: 'transparent', cursor: 'pointer',
                                 color: 'var(--text-soft)', padding: 2, lineHeight: 1 }}>
                        <i className="ti ti-trash" aria-hidden="true" style={{ fontSize: 14 }} />
                      </button>
                    )}
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
    </>
  )
}
