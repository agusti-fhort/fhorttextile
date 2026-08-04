import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import {
  SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy,
  useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

import { formatDelta } from '../../utils/format'

// El bloc de REGLA es distingeix per FONS (crema de la casa) i per un SEPARADOR gruixut
// respecte de la mesura: el color agrupa, el filet talla. Dos senyals, no un — la lliçó del
// TEA 205, on un increment i una llargada mirats de reüll eren el mateix número.
const REGLA_BG = 'var(--model-band)'
const SEP = '2px solid var(--border)'
const REGIME_OPTIONS = ['LINEAR', 'STEP', 'FIXED']
import BateigInput from '../model/BateigInput'
import { baseMeasurements, models } from '../../api/endpoints'

const thS = {
  padding: '6px 10px', textAlign: 'left', fontSize: 'var(--fs-body)',
  fontWeight: 500, whiteSpace: 'nowrap',
  borderBottom: '1px solid var(--border)',
}
const tdS = { padding: '4px 10px', verticalAlign: 'middle', fontSize: 'var(--fs-body)' }
// Règims editables a mà (les NORMES de gradació, mirall de GradingRule.LOGICA_CHOICES). FIXED és una
// norma igual que LINEAR/STEP → canviable des del desplegable. ZERO/EXCEPTION NO s'ofereixen com a tria
// nova (ZERO = nínxol "sempre 0"; EXCEPTION = tipus APLICAT per cel·la pel motor —override/excepció—,
// no un règim de POM); si una fila ja en porta un, es manté com a opció perquè el valor real no s'emmascari.
const btnPrimary = (disabled) => ({
  background: disabled ? 'var(--bg-muted)' : 'var(--gold)', color: disabled ? 'var(--text-muted)' : 'var(--white)',
  border: 'none', borderRadius: 6, padding: '7px 18px',
  fontSize: 'var(--fs-body)', fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer',
})
const btnSecondary = {
  background: 'transparent', color: 'var(--text-muted)',
  border: '0.5px solid var(--border)',
  borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer',
}

export default function EditableTable({
  rows,
  sizeRun,
  baseSize,
  deltes,
  modelId,
  isImport = false,
  readOnly = false,
  saveLabel,
  onPomSave,
  onSaved,
}) {
  const { t } = useTranslation()
  const [localRows, setLocalRows] = useState(rows)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => { setLocalRows(rows); setDirty(false) }, [rows])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    setLocalRows(prev => {
      const oldIdx = prev.findIndex(r => r.id === active.id)
      const newIdx = prev.findIndex(r => r.id === over.id)
      if (oldIdx < 0 || newIdx < 0) return prev
      return arrayMove(prev, oldIdx, newIdx).map((r, i) => ({ ...r, ordre: i }))
    })
    setDirty(true)
  }

  const handleCellChange = (rowId, col, value) => {
    setLocalRows(prev => prev.map(r => {
      if (r.id !== rowId) return r
      if (col.startsWith('graded.')) {
        const size = col.split('.')[1]
        return { ...r, graded: { ...r.graded, [size]: parseFloat(value) || 0 } }
      }
      if (col.includes('value')) return { ...r, [col]: parseFloat(value) || 0 }
      return { ...r, [col]: value }
    }))
    setDirty(true)
  }

  // EL BATEIG — desa IMMEDIATAMENT per la porta pròpia i estreta del paquet NOMS-POM
  // (`PATCH base-measurements/<id>/noms/`), com ja fa la graella de consulta. No passa pel
  // botó de desar de la taula a posta: rebatejar una mesura no és editar-ne el valor, i
  // barrejar-ho voldria dir que canviar un nom deixés la taula «bruta» i arrossegués les
  // mesures a un desat que ningú ha demanat. `localRows` s'actualitza a mà perquè el que es
  // veu sigui el que s'acaba de desar sense haver de recarregar la taula sencera.
  const handleBateig = (bmId, camps) =>
    baseMeasurements.setNoms(bmId, camps)
      .then(() => setLocalRows(prev => prev.map(r => (r.id === bmId ? { ...r, ...camps } : r))))
      .catch(e => { console.error('No s\'ha pogut desar el nom', e) })

  // LA REGLA es desa per la SEVA porta (`set_pom_regim_view`, upsert de la ModelGradingRule
  // resident), immediatament i per POM. NO passa pel botó de desar de la taula, i `buildPayload`
  // segueix sense enviar `rules`: aquell camí fabricava residents amb `logica||'LINEAR'` per a
  // CADA fila, i desar mesures acabava donant graduació a un model que no en tenia. Aquell guard
  // no torna.
  const handleRegla = (row, camp, valor) => {
    if (!row.pom_id) return
    const cru = (valor ?? '').toString().trim()
    let net = null
    if (cru !== '') {
      if (camp === 'logica' || camp === 'talla_break_label') net = cru
      else {
        const n = parseFloat(cru.replace(',', '.'))
        if (Number.isNaN(n)) return
        net = n
      }
    }
    if (String(row[camp] ?? '') === String(net ?? '')) return
    setLocalRows(prev => prev.map(r => (r.id === row.id ? { ...r, [camp]: net } : r)))
    models.setPomRegla(modelId, row.pom_id, { [camp]: net })
      .catch(e => console.error('No s\'ha pogut desar la regla', e))
  }

  const handleDeleteRow = (rowId) => {
    setLocalRows(prev => prev.filter(r => r.id !== rowId).map((r, i) => ({ ...r, ordre: i })))
    setDirty(true)
  }

  const handleAddRow = (pom) => {
    const newRow = {
      id: `tmp-${Date.now()}`,
      pom_id: pom.id,
      pom_code: pom.codi_client,
      nom_ca: pom.nom_ca || pom.nom_client || '',
      nom_en: pom.nom_en || pom.nom_client || '',
      nom_fitxa: '',
      base_value_cm: null,
      graded: {},
      ordre: localRows.length,
    }
    setLocalRows(prev => [...prev, newRow])
    setDirty(true)
  }

  const calcDelta = (row) => {
    // Δ computed on the backend (mean of increments between sizes with data).
    //
    // C4/BLOC 3 — LA CLAU DEL DICT ÉS `row.clau`, NO `row.pom_id`. El bloc 1 va desancorar
    // `taula-mesures` i la clau de `deltes` va passar a `{pom_id}|{capa}|{instancia}`
    // (`pom/identitat.clau_mesura`), que és el que la fila porta ara a `clau`. Amb `pom_id`
    // pelat no hi havia col·lisió: hi havia BUIT — `deltes['12']` no existeix quan la clau
    // desada és `'12|exterior|'`, o sigui que la columna Δ ensenyava '—' a TOTES les files de
    // TOTS els models, també els que no tenen cap germana. No petava i no avisava.
    //
    // La clau no es reconstrueix aquí: la porta la fila. El backend és l'únic que decideix com
    // s'aplana (v. la capçalera de `pom/identitat.py`), i muntar-la a mà en aquest fitxer seria
    // el segon lloc que ho sap.
    if (deltes && row.clau) {
      const d = deltes[row.clau]
      return d == null ? '—' : `±${d}`
    }
    // Local fallback (table without backend deltas, e.g. new unsaved rows).
    if (!sizeRun || sizeRun.length < 2) return '—'
    const valOf = (s) => s === baseSize ? row.base_value_cm : row.graded?.[s]
    const first = valOf(sizeRun[0])
    const last = valOf(sizeRun[sizeRun.length - 1])
    if (first == null || last == null) return '—'
    return (last - first).toFixed(1)
  }

  const buildPayload = () => {
    const measurements = localRows
      .filter(r => r.base_value_cm != null && r.base_value_cm !== '')
      .map(r => ({
        pom_id: r.pom_id,
        base_value_cm: r.base_value_cm,
        notes: r.notes || '',
        nom_fitxa: r.nom_fitxa || '',
      }))
    const keep_pom_ids = localRows.map(r => r.pom_id).filter(Boolean)
    // CAP `rules` (31/07). Aquesta taula ja no ensenya la regla, o sigui que tampoc no la pot
    // desar: enviava una entrada per CADA fila amb `logica: r.logica || 'LINEAR'`, i
    // `set_measurements_view` en fa upsert de ModelGradingRule. Efecte: desar mesures d'un
    // model sense graduació li creava regles residents —i per tant «ja té graduació»— sense
    // que ningú n'hagués informat cap. Amb la proposta del catàleg pintada a sobre, a més, el
    // que es materialitzava era la regla d'un altre. El backend segueix acceptant `rules`
    // (l'usen altres camins); el que desapareix és que aquesta pantalla n'enviï.
    return { measurements, keep_pom_ids }
  }

  // La GUARDA DE PLAUSIBILITAT del Δ (FIX-4) se'n va amb el bloc de regla: sense camp Δ en
  // aquesta taula no hi pot haver cap delta sospitós que confondre amb una mesura. La guarda
  // INVERSA —una cel·la de talla que sembla un increment— segueix viva a Escalat
  // (`PropagatedEditor`), que és on ara es toquen els deltes.

  const desa = async () => {
    setSaving(true)
    const token = localStorage.getItem('access_token')
    const API = import.meta.env.VITE_API_URL || ''
    const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

    try {
      const payload = buildPayload()

      if (onPomSave) {
        await onPomSave(payload)
        setDirty(false)
        if (onSaved) onSaved(localRows)
        return
      }

      await fetch(`${API}/api/v1/models/${modelId}/set-measurements/`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify(payload),
      })

      const order = localRows.map(r => r.id).filter(id => id && !String(id).startsWith('tmp-'))
      if (order.length > 0) {
        await fetch(`${API}/api/v1/models/${modelId}/reorder-measurements/`, {
          method: 'POST', headers: authHeaders,
          body: JSON.stringify({ order }),
        })
      }

      setDirty(false)
      if (onSaved) onSaved(localRows)
    } catch (e) {
      console.error('Error guardant', e)
    } finally {
      setSaving(false)
    }
  }

  const handleSave = () => desa()

  // W3 (31/07) — LES COLUMNES DE REGLA ES MOSTREN SEMPRE, buides si el model no té graduació.
  //
  // Abans es condicionaven a «alguna fila amb règim», i això deixava l'usuari sense lloc on
  // entrar la regla A MÀ: qui cancel·la el wizard de Graduació ha de trobar les columnes
  // allà, buides, per treballar-les. Ensenyar-les buides no és soroll — és la superfície de
  // treball, i el guió ('–') diu la veritat: aquest model encara no gradua.
  //
  // LA PROTECCIÓ QUE ES MANTÉ, i que és la lliçó del 1302: mai PRE-OMPLERTES. El payload
  // d'aquesta taula porta les regles del MODEL i prou (mai la proposta, mai el fallback del
  // catàleg) → BD neta = columnes buides. I desar mesures segueix sense fabricar cap regla:
  // `buildPayload` no envia `rules`, i aquell guard mort no torna.
  const displaySize = baseSize || sizeRun?.[0]
  const colCount = (readOnly ? 0 : 2) + 7
  const stickyHd = (left, w) => ({ ...thS, position: 'sticky', left, zIndex: 3, width: w, minWidth: w, background: 'var(--bg-muted)' })

  return (
    <div>
      {isImport && (
        <div style={{
          background: 'var(--warn-bg)', border: '1px solid var(--warn)',
          borderRadius: 8, padding: '10px 16px', marginBottom: 12,
          fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <i className="ti ti-alert-triangle" style={{ color: 'var(--warn)', fontSize: 16 }} />
          <span>
            <strong>{t('editable_table.import_title')}</strong>{' '}
            {t('editable_table.import_hint')}
          </span>
        </div>
      )}

      <div style={{ overflowX: 'auto', width: '100%' }}>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <table style={{ borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
            <thead>
              {/* LA GRADUACIÓ NO ES VEU AQUÍ (decisió d'Agus, 31/07). Mesures és POMs,
                  nomenclatura i valors — res més.
                  Fins avui aquesta taula portava el bloc «Regla de graduació» (Règim · Δ ·
                  Δ break · Talla break) que hi va posar FIX-4/C4. El QA del model 1302 va
                  ensenyar per què no hi pot ser: un model creat expressament SENSE graduació
                  hi mostrava «CH · LINEAR +2,0/+3,0 @XS» —el ruleset penjat del seu item, que
                  el model no havia adoptat mai— i, com que `buildPayload` reenviava el que la
                  taula ensenyava i `set_measurements_view` en feia upsert, desar les mesures
                  hauria convertit aquella PROPOSTA en regla del model sense que ningú
                  l'acceptés. La graduació s'informa pel seu gest (botó Graduació → Escalat) i
                  només allà.
                  El codi de RESOLUCIÓ de regles no s'ha tocat: Escalat el segueix fent servir. */}
              <tr style={{
                background: 'var(--bg-muted)',
                borderBottom: '1px solid var(--border)',
              }}>
                {!readOnly && <th rowSpan={2} style={thS}></th>}
                <th rowSpan={2} style={thS}>#</th>
                <th rowSpan={2} style={stickyHd(0, 90)}>{t('measuregrid.col_pom')}</th>
                <th rowSpan={2} style={stickyHd(90, 190)}>{t('measuregrid.col_nom')}</th>
                <th rowSpan={2} style={{ ...thS, textAlign: 'right', minWidth: 90, background: 'var(--gold-pale)' }}>
                  {displaySize || t('editable_table.col.base_value')}
                </th>
                {(
                  <th colSpan={4} style={{ ...thS, textAlign: 'center', background: REGLA_BG, borderLeft: SEP }}>
                    {t('measuregrid.grup_regla')}
                  </th>
                )}
                {!readOnly && <th rowSpan={2} style={thS}></th>}
              </tr>
              {(
                <tr style={{ background: 'var(--bg-muted)', borderBottom: '1px solid var(--border)' }}>
                  <th style={{ ...thS, minWidth: 92, background: REGLA_BG, borderLeft: SEP }}>{t('editable_table.col.regime')}</th>
                  <th style={{ ...thS, textAlign: 'right', minWidth: 82, background: REGLA_BG }}>{t('editable_table.col.delta')}</th>
                  <th style={{ ...thS, textAlign: 'right', minWidth: 82, background: REGLA_BG }}>{t('editable_table.col.break_delta')}</th>
                  <th style={{ ...thS, minWidth: 100, background: REGLA_BG }}>{t('editable_table.col.break_size')}</th>
                </tr>
              )}
            </thead>
            <SortableContext items={localRows.map(r => r.id)} strategy={verticalListSortingStrategy}>
              <tbody>
                {localRows.map(row => (
                  <SortableRow
                    key={row.id}
                    row={row}
                    displaySize={displaySize}
                    readOnly={readOnly}
                    onCellChange={handleCellChange}
                    onDelete={handleDeleteRow}
                    delta={calcDelta(row)}
                    onBateig={handleBateig}
                    onRegla={handleRegla}
                  />
                ))}
              </tbody>
            </SortableContext>
            {!readOnly && (
              <tfoot>
                <tr>
                  <td colSpan={colCount} style={{ padding: '8px 12px' }}>
                    <AddPOMInline onAdd={handleAddRow} />
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </DndContext>
      </div>


      {!readOnly && (dirty || onPomSave) && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 12 }}>
          {dirty && (
            <button type="button" onClick={() => { setLocalRows(rows); setDirty(false) }}
              style={btnSecondary}>
              <i className="ti ti-arrow-back-up" /> {t('editable_table.discard')}
            </button>
          )}
          <button type="button" onClick={handleSave} disabled={saving}
            style={btnPrimary(saving)}>
            {saving ? t('common.saving') : saveLabel || t('editable_table.confirm_table')}
          </button>
        </div>
      )}
    </div>
  )
}

function SortableRow({ row, displaySize, readOnly, onCellChange, onDelete, delta, onBateig, onRegla }) {
  const { t } = useTranslation()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: row.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    background: isDragging ? 'var(--bg-muted)' : undefined,
    borderBottom: '0.5px solid var(--border)',
  }

  const rowBg = isDragging ? 'var(--bg-muted)' : 'var(--white)'
  const stickyTd = (left, w) => ({
    ...tdS, position: 'sticky', left, zIndex: 1, width: w, minWidth: w,
    background: rowBg, borderBottom: '0.5px solid var(--border)',
  })

  return (
    <tr ref={setNodeRef} style={style}>
      {!readOnly && (
        <td style={tdS}>
          <span {...attributes} {...listeners}
            style={{ cursor: 'grab', color: 'var(--text-muted)', fontSize: 'var(--fs-h3)' }}>
            ⠿
          </span>
        </td>
      )}
      <td style={{ ...tdS, color: 'var(--text-muted)' }}>{(row.ordre ?? 0) + 1}</td>
      <td style={stickyTd(0, 90)}>
        {/* C3 — NOMENCLATURA DEL CLIENT del model (CustomerPOMAlias): el codi que el tècnic
            escriu als documents d'aquest client (Brownie diu "A" on el catàleg diu "CH"), i
            els seus noms EN/local. Sense àlies per aquest POM, el catàleg de la casa, com
            sempre. La nomenclatura per-model (nom_fitxa) segueix manant per damunt de tot:
            és la que el tècnic ha escrit aquí mateix. */}
        <EditableCell value={row.nom_fitxa || row.client_code || row.pom_code}
          onChange={v => onCellChange(row.id, 'nom_fitxa', v)}
          mono gold readOnly={readOnly} />
        {row.is_key && (
          <i className="ti ti-star" title="KEY"
            style={{ fontSize: 9, marginLeft: 5, color: 'var(--gold)', verticalAlign: 'middle' }} />
        )}
      </td>
      <td style={stickyTd(90, 190)}>
        {(() => {
          // Llei de presentació de la casa (nom internacional dalt · llengua de qui llegeix
          // sota), APLICADA AL CLIENT: si el POM té àlies, manen les seves descripcions.
          const dalt = row.client_name_en || row.nom_en || row.nom_ca || row.pom_code
          // C5 — el subtítol anava al token de captions (8px), pensat per a badges i peus, no
          // per a una columna que es llegeix a cada fila: puja al token immediatament superior
          // (--fs-label, 10px). Segueix per sota del nom (--fs-body, 12px).
          const sota = row.client_name_en ? row.client_name_local : row.nom_ca
          const estilDalt = { fontSize: 'var(--fs-body)', color: 'var(--text-main)', whiteSpace: 'normal' }
          const estilSota = { fontSize: 'var(--fs-label)', fontStyle: 'italic', color: 'var(--text-muted)', whiteSpace: 'normal' }
          // EL BATEIG (31/07) — les DUES línies s'editen aquí, que és on es treballa.
          //
          // El paquet del bateig va cablejar això a `MeasureGrid` (consulta/check) i aquesta
          // taula —la d'entrada de Mesures— es va quedar amb dos `div` estàtics: el clic no
          // armava res perquè no hi havia res a armar. Mateix camp i MATEIXA PORTA que allà
          // (`baseMeasurements.setNoms` → PATCH base-measurements/<id>/noms/), no un segon mecanisme.
          //
          // El catàleg va de PLACEHOLDER: buidar el camp torna a deixar-lo manar, i mentre el
          // bateig és buit el que es llegeix és exactament el d'abans.
          //
          // Una fila encara no desada (`tmp-…`) no té BaseMeasurement a què penjar el nom:
          // es queda com a text fins que es desa. Batejar-la abans seria escriure a un id
          // que no existeix.
          const bmId = row.id != null && !String(row.id).startsWith('tmp-') ? row.id : null
          if (!readOnly && bmId != null && onBateig) {
            return (
              <>
                <BateigInput value={row.nom_canonic_model || ''} placeholder={dalt || ''}
                  title={t('measuregrid.nom_canonic_tip')}
                  onSave={v => onBateig(bmId, { nom_canonic_model: v })}
                  style={estilDalt} />
                <BateigInput value={row.nom_traduit_model || ''} placeholder={sota || dalt || ''}
                  title={t('measuregrid.nom_traduit_tip')}
                  onSave={v => onBateig(bmId, { nom_traduit_model: v })}
                  style={estilSota} />
              </>
            )
          }
          return (
            <>
              <div style={estilDalt}>{row.nom_canonic_model || dalt}</div>
              {(row.nom_traduit_model || (sota && sota !== dalt)) && (
                <div style={estilSota}>{row.nom_traduit_model || sota}</div>
              )}
            </>
          )
        })()}
      </td>
      <td style={{ ...tdS, textAlign: 'right', background: 'var(--gold-pale)' }}>
        <EditableCell
          value={row.base_value_cm}
          onChange={v => onCellChange(row.id, 'base_value_cm', v)}
          mono right readOnly={readOnly} />
      </td>
      {(
        <>
          <td style={{ ...tdS, background: REGLA_BG, borderLeft: SEP }}>
            {(() => {
              const cur = row.logica || 'LINEAR'
              // No emmascarar: si la fila porta un valor fora de les normes editables
              // (ZERO/EXCEPTION), s'afegeix com a opció perquè el valor real es vegi i es pugui
              // canviar a LINEAR/STEP/FIXED.
              const opts = REGIME_OPTIONS.includes(cur) ? REGIME_OPTIONS : [...REGIME_OPTIONS, cur]
              return (
                <select value={cur} disabled={readOnly}
                  onChange={e => onRegla(row, 'logica', e.target.value)}
                  style={{ font: 'inherit', border: '1px solid var(--border)', borderRadius: 4,
                           padding: '2px 4px', background: readOnly ? 'transparent' : 'var(--white)',
                           color: 'var(--text-main)' }}>
                  {opts.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              )
            })()}
          </td>
          {/* `signed`: un delta es PINTA sempre amb signe (+1 / +1,5). En edició es tecleja el
              número nu; el signe és de la LECTURA, que és on es confon amb una mesura. */}
          <td style={{ ...tdS, textAlign: 'right', background: REGLA_BG }}>
            <EditableCell value={row.increment_base ?? ''}
              onChange={v => onRegla(row, 'increment_base', v)}
              mono right signed readOnly={readOnly} />
          </td>
          <td style={{ ...tdS, textAlign: 'right', background: REGLA_BG }}>
            <EditableCell value={row.increment_break}
              onChange={v => onRegla(row, 'increment_break', v)}
              mono right signed readOnly={readOnly} />
          </td>
          <td style={{ ...tdS, background: REGLA_BG }}>
            {/* Etiqueta de talla: DADA de domini (XS, 3XL). Ni signe ni traducció. */}
            <EditableCell value={row.talla_break_label || ''}
              onChange={v => onRegla(row, 'talla_break_label', v)}
              readOnly={readOnly} />
          </td>
        </>
      )}
      {!readOnly && (
        <td style={tdS}>
          <button type="button" onClick={() => onDelete(row.id)}
            style={{ background: 'none', border: 'none', cursor: 'pointer',
                     color: 'var(--text-muted)', fontSize: 'var(--fs-h3)', padding: '2px 4px' }}
            title={t('editable_table.delete_row')}>
            <i className="ti ti-x" />
          </button>
        </td>
      )}
    </tr>
  )
}

function EditableCell({ value, onChange, mono, gold, right, signed, readOnly }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value ?? '')

  useEffect(() => { setVal(value ?? '') }, [value])

  if (readOnly || !editing) {
    // FIX-4 — `signed`: en LECTURA un delta porta sempre el seu signe (+1 / +1,5). És l'única
    // marca que el distingeix d'una mesura a cop d'ull, i és a cop d'ull que es confonen.
    const nuu = (val !== '' && val != null) ? (signed ? formatDelta(val) : val) : null
    const display = nuu != null ? nuu
      : <span style={{ color: 'var(--text-muted)' }}>—</span>
    return (
      <span
        onClick={() => !readOnly && setEditing(true)}
        style={{
          display: 'block', cursor: readOnly ? 'default' : 'pointer',
          fontFamily: mono ? 'monospace' : undefined,
          color: gold ? 'var(--gold)' : undefined,
          textAlign: right ? 'right' : undefined,
          minWidth: 30, padding: '1px 2px',
          borderBottom: readOnly ? 'none' : '1px dashed transparent',
        }}
        onMouseEnter={e => { if (!readOnly) e.currentTarget.style.borderBottomColor = 'var(--border)' }}
        onMouseLeave={e => { e.currentTarget.style.borderBottomColor = 'transparent' }}>
        {display}
      </span>
    )
  }

  return (
    <input
      autoFocus
      type={typeof value === 'number' ? 'number' : 'text'}
      inputMode={typeof value === 'number' ? 'decimal' : undefined}
      step="0.1"
      value={val}
      onChange={e => setVal(e.target.value)}
      onBlur={() => { onChange(val); setEditing(false) }}
      onKeyDown={e => {
        if (e.key === 'Enter') { onChange(val); setEditing(false) }
        if (e.key === 'Escape') { setVal(value ?? ''); setEditing(false) }
        if (e.key === 'Tab') { onChange(val); setEditing(false) }
      }}
      style={{
        width: mono ? 60 : '100%', padding: '1px 4px',
        border: '1px solid var(--gold)', borderRadius: 3,
        fontSize: 'var(--fs-body)', fontFamily: mono ? 'monospace' : undefined,
        textAlign: right ? 'right' : undefined,
        background: 'var(--gold-pale)',
      }}
    />
  )
}

function AddPOMInline({ onAdd }) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const token = localStorage.getItem('access_token')
  const API = import.meta.env.VITE_API_URL || ''

  useEffect(() => {
    if (query.length < 2) { setResults([]); return }
    const timer = setTimeout(async () => {
      try {
        const r = await fetch(
          `${API}/api/v1/poms/cerca/?q=${encodeURIComponent(query)}&page_size=10`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        const d = await r.json()
        setResults(d.results || d || [])
      } catch {
        setResults([])
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  const handleCreatePOM = async (nom) => {
    try {
      const r = await fetch(`${API}/api/v1/poms/crear-tenant/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          nom_client: nom,
          codi_client: nom.toUpperCase().replace(/\s+/g, '_').slice(0, 20),
          actiu: true,
          pendent_revisio: true,
        }),
      })
      const d = await r.json()
      if (r.ok) {
        onAdd({ id: d.id, codi_client: d.codi_client, nom_client: d.nom_client })
        setQuery(''); setResults([]); setOpen(false)
      }
    } catch (e) {
      console.error('Error creant POM', e)
    }
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}
        style={{ background: 'none', border: 'none', cursor: 'pointer',
                 fontSize: 'var(--fs-body)', color: 'var(--gold)', padding: '4px 0',
                 }}>
        <i className="ti ti-plus" /> {t('editable_table.add_pom')}
      </button>
    )
  }

  return (
    <div style={{ position: 'relative', display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
      <input
        autoFocus
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder={t('editable_table.search_placeholder')}
        style={{ padding: '4px 8px', border: '1px solid var(--border)',
                 borderRadius: 4, fontSize: 'var(--fs-body)', width: 220,
                 }}
      />
      {(results.length > 0 || query.length >= 2) && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4,
          background: 'var(--bg-main)',
          border: '0.5px solid var(--border)', borderRadius: 6,
          zIndex: 100, minWidth: 280,
        }}>
          {results.map(p => (
            <div key={p.id}
              onClick={() => { onAdd(p); setQuery(''); setResults([]); setOpen(false) }}
              style={{ padding: '6px 12px', cursor: 'pointer', fontSize: 'var(--fs-body)',
                       borderBottom: '0.5px solid var(--border)',
                       }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-muted)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <span style={{ color: 'var(--gold)', marginRight: 8 }}>
                {p.codi_client}
              </span>
              {p.nom_client || p.nom_ca || p.nom_en}
            </div>
          ))}
          {query.length >= 2 && results.length === 0 && (
            <div style={{
              padding: '8px 12px', fontSize: 'var(--fs-body)',
              color: 'var(--text-muted)',
            }}>
              {t('editable_table.no_pom_found', { query })}{' '}
              <button type="button"
                onClick={() => handleCreatePOM(query)}
                style={{ background: 'none', border: 'none', cursor: 'pointer',
                         color: 'var(--gold)', fontSize: 'var(--fs-body)', padding: 0,
                         }}>
                + {t('editable_table.create_pom', { query })}
              </button>
            </div>
          )}
        </div>
      )}
      <button type="button" onClick={() => { setOpen(false); setQuery('') }}
        style={{ background: 'none', border: 'none', cursor: 'pointer',
                 fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
        ✕
      </button>
    </div>
  )
}
