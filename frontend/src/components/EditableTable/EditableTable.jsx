import { useState, useEffect, useRef, useCallback } from 'react'
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
import { etiquetaCapa, etiquetaInstancia, CAPES, INSTANCIES } from '../../utils/capaInstancia'

// El bloc de REGLA es distingeix per FONS (crema de la casa) i per un SEPARADOR gruixut
// respecte de la mesura: el color agrupa, el filet talla. Dos senyals, no un — la lliçó del
// TEA 205, on un increment i una llargada mirats de reüll eren el mateix número.
const REGLA_BG = 'var(--model-band)'
const SEP = '2px solid var(--border)'
const REGIME_OPTIONS = ['LINEAR', 'STEP', 'FIXED']
import BateigInput from '../model/BateigInput'
import { baseMeasurements, models } from '../../api/endpoints'

// TIPOGRAFIA DE LA v8.1 (brief C5-UI · P1). Els dos cossos NO són tokens de la casa a posta:
// la maqueta aprovada demana 9,5px a la capçalera i 12,5px al valor, i cap dels graons del
// sistema (--fs-caption 8 · --fs-label 10 · --fs-body 12) hi cau a sobre. Es declaren aquí, amb
// nom, en comptes d'escampar-los per les cel·les — i els COLORS segueixen sent tokens, sempre.
const FS_HEAD = '9.5px'   // capçaleres, versaletes
const FS_VAL = '12.5px'   // valors i noms de fila

const thS = {
  padding: '4px 10px', textAlign: 'left', fontSize: FS_HEAD,
  fontWeight: 500, whiteSpace: 'nowrap',
  textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)',
  borderBottom: '1px solid var(--border)',
}
const tdS = { padding: '4px 10px', verticalAlign: 'middle', fontSize: FS_VAL }
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
      // v8.1 — BUIT ÉS BUIT, no zero. `parseFloat('') || 0` convertia una cel·la esborrada en
      // un 0, i un 0 no és `null`: la fila passava el filtre de `buildPayload` i es desava com
      // una mesura de zero centímetres. La llei del carril («buit = es descarta») no es podia
      // complir perquè no hi havia manera d'arribar al buit. Un text no numèric tampoc no
      // s'escriu: es queda al buffer de l'input, que el marca en vermell.
      if (col.includes('value')) {
        const cru = String(value ?? '').replace(',', '.').trim()
        if (cru === '') return { ...r, [col]: null }
        const n = parseFloat(cru)
        return Number.isNaN(n) ? r : { ...r, [col]: n }
      }
      return { ...r, [col]: value }
    }))
    setDirty(true)
  }

  // EL CARRIL (v8.1) — ↓/Enter baixa, ↑ puja, i el focus no surt mai de la columna de valors.
  // Els inputs es registren per `row.id` i la navegació es resol sobre `localRows`, que és
  // l'ordre REAL de la pantalla (el DnD el reordena); indexar per posició de render seria
  // navegar per un ordre que ja no existeix després d'arrossegar una fila.
  const valRefs = useRef({})
  const registerVal = useCallback((rowId, el) => {
    if (el) valRefs.current[rowId] = el
    else delete valRefs.current[rowId]
  }, [])
  const rowsRef = useRef(localRows)
  useEffect(() => { rowsRef.current = localRows }, [localRows])
  const navVal = useCallback((rowId, dir) => {
    const ordre = rowsRef.current
    const i = ordre.findIndex(r => r.id === rowId)
    const target = ordre[i + dir]
    if (target) valRefs.current[target.id]?.focus()
  }, [])

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

  // ── F4 · EL GEST DE CREAR UNA GERMANA ───────────────────────────────────────
  // Tot C4 és a sota des de fa dies —l'escriptura porta els dos eixos, la poda també, la clau
  // única de la BD és `(model, pom, capa, instancia)`— i no hi havia CAP porta d'usuari: les
  // germanes que hi ha a staging es van sembrar per script. Aquesta és la porta.
  //
  // NEIX AL COSTAT DE LA MARE, no al final de la taula: una germana és una cara MÉS de la
  // mateixa mesura i llegir-la a catorze files de distància no diria això. Neix BUIDA, i el
  // carril de valors hi entra com a qualsevol altra fila (l'ordre de tabulació és la posició).
  //
  // ⚠️ NO ES DESA SOLA, i és correcte: `buildPayload` només envia les files amb valor, com ha
  // fet sempre amb les files noves. Una germana sense mesura encara no és una mesura.
  const [germanaDe, setGermanaDe] = useState(null)   // fila mare del diàleg obert

  const creaGermana = ({ capa, instancia, nom_fitxa }) => {
    const mare = germanaDe
    setGermanaDe(null)
    if (!mare) return
    const nova = {
      ...mare,
      id: `tmp-${Date.now()}`,
      capa: capa || mare.capa || 'exterior',
      instancia: instancia || '',
      nom_fitxa,
      // El VALOR no s'hereta. Una germana de folre que naixés amb la mida de l'exterior seria
      // una xifra que ningú no ha mesurat, indistingible d'una de presa: el pitjor defecte
      // possible en una taula de mesures. Neix buida i el tècnic la mesura.
      base_value_cm: null,
      graded: {},
      // El BATEIG tampoc: el nom canònic del model és de la mesura, no del POM.
      nom_canonic_model: '', nom_traduit_model: '',
      // `clau` és la que serveix el backend per indexar els deltes; una fila que encara no
      // existeix no en té cap, i heretar la de la mare li ensenyaria el Δ de l'altra.
      clau: undefined,
    }
    setLocalRows(prev => {
      const i = prev.findIndex(r => r.id === mare.id)
      const fins = i < 0 ? prev.length : i + 1
      return [...prev.slice(0, fins), nova, ...prev.slice(fins)]
    })
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
        // C4/BLOC 1-BIS — ELS EIXOS ENTREN AL PAYLOAD D'ESCRIPTURA. Amb `pom_id` pelat,
        // l'upsert del backend resolia la fila amb el literal `(exterior, '')` i dues
        // germanes hi queien a sobre: la segona escrivia el seu valor a la fila de la
        // primera i la primera es quedava sense tocar. Pèrdua de dades en DESAR, no una
        // columna buida. Avui no fa mal perquè no hi ha cap germana viva; el dia que en
        // neixi una, ja seria tard.
        //
        // Viatgen com a DOS CAMPS i no com la cadena aplanada `{pom}|{capa}|{inst}`: ho mana
        // `pom/identitat.py` —«qui hagi de consultar, filtrar o escriure, que faci servir els
        // tres camps per separat»—. La cadena existeix només per a la vora del payload on la
        // mesura és clau d'un objecte JSON (`deltes`, `cells`), que no és aquest cas.
        //
        // Les files encara no desades (les de `poms-suggerits`) no en porten: el backend hi
        // aplica el literal de sempre, i ho fa dient-ho.
        capa: r.capa,
        instancia: r.instancia,
        base_value_cm: r.base_value_cm,
        notes: r.notes || '',
        nom_fitxa: r.nom_fitxa || '',
      }))
    const keep_pom_ids = localRows.map(r => r.pom_id).filter(Boolean)
    // C4/BLOC 1-TER — LA LLISTA DE «QUÈ ES CONSERVA» PORTA LA IDENTITAT DE CADA FILA.
    //
    // `keep_pom_ids` és una llista d'enters, i un `pom_id` pelat no pot dir «conserva el
    // folre i treu l'exterior». Amb dues germanes a la taula, treure'n una i desar no feia
    // res: el backend només mirava la fila d'exterior. L'usuari clicava la paperera, la fila
    // desapareixia de la pantalla, i en tornar a carregar hi era una altra vegada.
    //
    // Es construeix sobre `localRows` i NO sobre `measurements`, igual que el camp antic:
    // `measurements` només porta les files amb valor, i una fila buida que en quedés fora
    // deixaria de ser «conservada» — el backend l'esborraria. Seria fabricar un esborrat
    // silenciós dins del canvi que els ha de tancar.
    //
    // Els dos camps viatgen junts: el backend fa servir el nou i ignora el vell, i un desplegament
    // a mitges (bundle nou amb backend antic) segueix podant com abans en comptes de deixar
    // de podar.
    const keep_mesures = localRows
      .filter(r => r.pom_id)
      .map(r => ({ pom_id: r.pom_id, capa: r.capa, instancia: r.instancia }))
    // CAP `rules` (31/07). Aquesta taula ja no ensenya la regla, o sigui que tampoc no la pot
    // desar: enviava una entrada per CADA fila amb `logica: r.logica || 'LINEAR'`, i
    // `set_measurements_view` en fa upsert de ModelGradingRule. Efecte: desar mesures d'un
    // model sense graduació li creava regles residents —i per tant «ja té graduació»— sense
    // que ningú n'hagués informat cap. Amb la proposta del catàleg pintada a sobre, a més, el
    // que es materialitzava era la regla d'un altre. El backend segueix acceptant `rules`
    // (l'usen altres camins); el que desapareix és que aquesta pantalla n'enviï.
    return { measurements, keep_pom_ids, keep_mesures }
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
  const colCount = (readOnly ? 0 : 2) + 9
  const stickyHd = (left, w) => ({ ...thS, position: 'sticky', left, zIndex: 3, width: w, minWidth: w, background: 'var(--bg-muted)' })
  // Bloc d'IDENTITAT de la fila, congelat a l'esquerra: Capa · nomenclatura · nom. Amb dues
  // germanes vives (el mateix POM a l'exterior i al folre, la sisa esquerra i la dreta) el nom
  // sol ja no diu quina fila és cadascuna, i és justament la columna que ha de quedar visible
  // mentre s'escruta la taula cap a la dreta.
  const W_CAPA = 104
  const W_CODI = 90
  const W_NOM = 236
  // Quantes files es desaran i quantes cauran. La llei del carril («buit = es descarta») és
  // muda si el descart només es veu fila a fila: aquí es llegeix el total abans de desar.
  const nInformades = localRows.filter(r => r.base_value_cm != null && r.base_value_cm !== '').length
  const nBuides = localRows.length - nInformades

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
                <th rowSpan={2} style={stickyHd(0, W_CAPA)}>{t('capa.col')}</th>
                <th rowSpan={2} style={stickyHd(W_CAPA, W_CODI)}>{t('measuregrid.col_pom')}</th>
                <th rowSpan={2} style={stickyHd(W_CAPA + W_CODI, W_NOM)}>{t('measuregrid.col_nom')}</th>
                <th rowSpan={2} style={{ ...thS, textAlign: 'right', minWidth: 100, background: 'var(--gold-pale)' }}>
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
                {localRows.map((row, i) => (
                  <SortableRow
                    key={row.id}
                    row={row}
                    // El número de fila és la POSICIÓ a la pantalla, no `row.ordre`. Les germanes
                    // d'un mateix POM comparteixen `ordre` (l'exterior i el folre del pit són la
                    // mateixa posició de fitxa), i pintar-lo cru donava «1 · 1 · 1 · 1 · 2 · 3…»:
                    // una numeració que no compta res i que fa dubtar de si falten files.
                    n={i + 1}
                    displaySize={displaySize}
                    readOnly={readOnly}
                    onCellChange={handleCellChange}
                    onDelete={handleDeleteRow}
                    onGermana={() => setGermanaDe(row)}
                    delta={calcDelta(row)}
                    onBateig={handleBateig}
                    onRegla={handleRegla}
                    widths={{ capa: W_CAPA, codi: W_CODI, nom: W_NOM }}
                    registerVal={registerVal}
                    onNav={navVal}
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

      {germanaDe && (
        <GermanaDialog
          mare={germanaDe}
          // Les cares que aquest POM JA té a la taula: la clau de la BD és
          // `(model, pom, capa, instancia)` i oferir-ne una de repetida acabaria escrivint
          // damunt d'una fila existent en silenci. El diàleg les treu de la llista.
          existents={localRows.filter(r => r.pom_id === germanaDe.pom_id)}
          onCancel={() => setGermanaDe(null)}
          onCrear={creaGermana} />
      )}

      {!readOnly && (
        <div style={{ display: 'flex', gap: 18, marginTop: 10, fontSize: 'var(--fs-label)',
                      color: 'var(--text-muted)' }}>
          <span>{t('editable_table.count_filled', { n: nInformades })}</span>
          {nBuides > 0 && <span>{t('editable_table.count_empty', { n: nBuides })}</span>}
        </div>
      )}

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

function SortableRow({ row, n, displaySize, readOnly, onCellChange, onDelete, onGermana, delta, onBateig, onRegla,
                       widths, registerVal, onNav }) {
  const { t } = useTranslation()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: row.id })

  // BUIT = ES DESCARTA. La fila no desapareix ni es bloqueja: es rebaixa i s'hi diu, perquè el
  // descart passa en DESAR i no en teclejar. Qui la deixa en blanc ho fa a posta o per descuit,
  // i la diferència entre les dues coses és haver-ho pogut llegir abans de prémer el botó.
  const buida = row.base_value_cm == null || row.base_value_cm === ''

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
      <td style={{ ...tdS, color: 'var(--text-muted)', fontSize: 'var(--fs-label)' }}>{n}</td>
      {/* LA CAPA (D-31.22) — de quina matèria de la peça parla aquesta mesura. Es mostra SEMPRE,
          també quan totes les files diuen «Exterior»: una columna que apareix el dia que neix la
          primera germana faria que la taula canviés de forma sota els peus del tècnic, i el que
          ha de canviar és el CONTINGUT d'una cel·la, no el nombre de columnes.
          És LECTURA: moure una mesura de capa és partir-la en dues, i això és un acte propi
          (la germana de capa), no un desplegable que es toca de passada. */}
      <td style={{ ...stickyTd(0, widths.capa), color: 'var(--text-main)', whiteSpace: 'normal' }}>
        {etiquetaCapa(row.capa, t)}
      </td>
      <td style={stickyTd(widths.capa, widths.codi)}>
        {/* C3 — NOMENCLATURA DEL CLIENT del model (CustomerPOMAlias): el codi que el tècnic
            escriu als documents d'aquest client (Brownie diu "A" on el catàleg diu "CH"), i
            els seus noms EN/local. Sense àlies per aquest POM, el catàleg de la casa, com
            sempre. La nomenclatura per-model (nom_fitxa) segueix manant per damunt de tot:
            és la que el tècnic ha escrit aquí mateix. */}
        <NomenInput value={row.nom_fitxa} placeholder={row.client_code || row.pom_code || ''}
          readOnly={readOnly} onCommit={v => onCellChange(row.id, 'nom_fitxa', v)} />
        {row.is_key && (
          <i className="ti ti-star" title="KEY"
            style={{ fontSize: 9, marginLeft: 5, color: 'var(--gold)', verticalAlign: 'middle' }} />
        )}
      </td>
      <td style={{ ...stickyTd(widths.capa + widths.codi, widths.nom), opacity: buida ? 0.55 : 1 }}>
        {(() => {
          // Llei de presentació de la casa (nom internacional dalt · llengua de qui llegeix
          // sota), APLICADA AL CLIENT: si el POM té àlies, manen les seves descripcions.
          const dalt = row.client_name_en || row.nom_en || row.nom_ca || row.pom_code
          const sota = row.client_name_en ? row.client_name_local : row.nom_ca
          // v8.1 — EL SUBTÍTOL TRADUÏT PERMANENT SE'N VA A LA ⓘ. Era una segona línia a cada
          // fila d'una taula que ara n'ha de mostrar tretze i distingir-ne quatre germanes: el
          // que ha de saltar a la vista és QUINA mesura és cada fila (capa i instància), no el
          // mateix nom dit dues vegades. La traducció no es perd; es demana.
          // …i NOMÉS si diu una cosa diferent del que ja es llegeix. Una ⓘ que repeteix el nom de
          // la fila («Cord width» → «Cord width») és una promesa d'informació que no compleix; és
          // la mateixa regla que ja aplica `nomsDePom` a la segona línia de les altres taules.
          const nomVisible = row.nom_canonic_model || dalt
          const candidat = row.nom_traduit_model || sota || ''
          const traduit = candidat && candidat !== nomVisible ? candidat : ''
          // LA INSTÀNCIA VIU DINS DEL NOM, no en una columna a part i no com a sufix del codi.
          // Paraula sencera («Esquerra», mai «L») i EN EL COLOR DEL NOM: és el nom d'aquesta
          // mesura el que s'allarga, no una etiqueta enganxada al costat. Amb `AH-L`/`AH-R` com
          // a única marca, dir quina fila és quina volia dir conèixer la nomenclatura del client.
          const inst = etiquetaInstancia(row.instancia, t)
          const estilDalt = { fontSize: FS_VAL, color: 'var(--text-main)', whiteSpace: 'normal' }
          // EL BATEIG (31/07) — el nom canònic s'edita aquí, que és on es treballa.
          //
          // Mateix camp i MATEIXA PORTA que `MeasureGrid` (`baseMeasurements.setNoms` → PATCH
          // base-measurements/<id>/noms/), no un segon mecanisme. El catàleg va de PLACEHOLDER:
          // buidar el camp torna a deixar-lo manar.
          //
          // Una fila encara no desada (`tmp-…`) no té BaseMeasurement a què penjar el nom:
          // es queda com a text fins que es desa. Batejar-la abans seria escriure a un id
          // que no existeix.
          const bmId = row.id != null && !String(row.id).startsWith('tmp-') ? row.id : null
          const nomEditable = !readOnly && bmId != null && onBateig
          return (
            <NomCanonic
              value={row.nom_canonic_model || ''} placeholder={dalt || ''} instancia={inst}
              traduccio={traduit} editable={nomEditable} estil={estilDalt}
              title={t('measuregrid.nom_canonic_tip')}
              onSave={v => onBateig(bmId, { nom_canonic_model: v })} />
          )
        })()}
      </td>
      <td style={{ ...tdS, textAlign: 'right', background: 'var(--gold-pale)' }}>
        <CarrilInput
          value={row.base_value_cm}
          readOnly={readOnly}
          onCommit={v => onCellChange(row.id, 'base_value_cm', v)}
          registerVal={el => registerVal?.(row.id, el)}
          onNav={dir => onNav?.(row.id, dir)}
          hint={buida ? t('editable_table.row_discarded') : undefined} />
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
        <td style={{ ...tdS, whiteSpace: 'nowrap' }}>
          {/* F4 — AFEGIR GERMANA. Va a la fila, no a un menú global, perquè una germana no és
              «una mesura nova»: és una cara MÉS d'AQUESTA mesura, i el gest ha de sortir d'ella.
              Només amb `pom_id`: una fila que encara no s'ha desat no té POM a què agermanar-se. */}
          {row.pom_id != null && (
            <button type="button" onClick={onGermana}
              style={{ background: 'none', border: 'none', cursor: 'pointer',
                       color: 'var(--gold)', fontSize: 'var(--fs-h3)', padding: '2px 4px' }}
              title={t('germana.afegir')}>
              <i className="ti ti-layers-subtract" />
            </button>
          )}
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

// ── F4 · EL DIÀLEG DE LA GERMANA ────────────────────────────────────────────────────────────
//
// Dues menes de germana, i NO són el mateix acte:
//
//  · DE CAPA — la mateixa mesura en una altra matèria de la peça (l'ample de pit al folre). El
//    nom no cal: la capa ja la distingeix, i la BD no l'exigeix.
//  · D'INSTÀNCIA — la mateixa mesura en una altra cara/posició (la sisa esquerra i la dreta).
//    Aquí el NOM ÉS OBLIGATORI, i no és una tria d'UX: la invariant
//    `models_app_basemeasurement_instancia_exigeix_nom` ho imposa a la base de dades
//    (`CHECK NOT (instancia > '' AND nom_fitxa = '')`). Sense el camp, desar petaria amb un
//    IntegrityError que arribaria com un 500 mut. Es demana aquí, que és on es pot explicar.
//
// LES CARES QUE JA HI SÓN NO S'OFEREIXEN. La clau única és `(model, pom, capa, instancia)`:
// tornar a triar una combinació existent no crearia res, escriuria damunt de la fila que ja hi
// ha i el tècnic veuria desaparèixer una mesura sense saber per què.
//
// Les instàncies són les quatre amb literal propi (`INSTANCIES`). Un slug compost com
// `left-relaxed` és legítim al domini i el diccionari sencer arriba amb C4-ins; oferir aquí un
// camp lliure de slug seria demanar-li a la Montse que escrigui vocabulari canònic a mà.
function GermanaDialog({ mare, existents, onCancel, onCrear }) {
  const { t } = useTranslation()
  const [mena, setMena] = useState('capa')
  const [capa, setCapa] = useState('')
  const [instancia, setInstancia] = useState('')
  const [nom, setNom] = useState('')

  const capaMare = mare.capa || 'exterior'
  const preses = new Set(existents.map(r => `${r.capa || 'exterior'}|${r.instancia || ''}`))
  // Capes lliures: qualsevol de les sis que no tingui ja una fila amb la instància de la mare.
  const capesLliures = CAPES.filter(c => !preses.has(`${c}|${mare.instancia || ''}`))
  // Instàncies lliures: dins la capa de la mare. Una fila amb instància única (`''`) i una amb
  // `left` conviuen — no és cap conflicte, i el domini les admet totes dues.
  const instLliures = INSTANCIES.filter(i => !preses.has(`${capaMare}|${i}`))

  const nomCal = mena === 'instancia'
  const tria = mena === 'capa' ? capa : instancia
  const potCrear = !!tria && (!nomCal || nom.trim() !== '')

  const crea = () => {
    if (!potCrear) return
    onCrear(mena === 'capa'
      ? { capa, instancia: mare.instancia || '', nom_fitxa: nom.trim() || mare.nom_fitxa || '' }
      : { capa: capaMare, instancia, nom_fitxa: nom.trim() })
  }

  const opcio = (actiu, onClick, clau, text) => (
    <button key={clau} type="button" onClick={onClick}
      style={{
        padding: '5px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 'var(--fs-body)',
        border: `1px solid ${actiu ? 'var(--gold)' : 'var(--border)'}`,
        background: actiu ? 'var(--gold-pale)' : 'var(--white)',
        color: actiu ? 'var(--gold)' : 'var(--text-main)', fontWeight: actiu ? 500 : 400,
      }}>{text}</button>
  )

  return (
    <div onClick={onCancel}
      style={{ position: 'fixed', inset: 0, zIndex: 80, background: 'rgba(0,0,0,0.28)',
               display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div onClick={e => e.stopPropagation()}
        style={{ background: 'var(--white)', borderRadius: 10, padding: '1.25rem 1.4rem',
                 width: 'min(520px, 92vw)', boxShadow: '0 10px 40px rgba(0,0,0,0.2)' }}>
        <h3 style={{ margin: '0 0 4px', fontSize: 'var(--fs-h3)', fontWeight: 500 }}>
          {t('germana.titol')}
        </h3>
        <p style={{ margin: '0 0 14px', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
          {t('germana.subtitol', {
            nom: mare.nom_canonic_model || mare.nom_en || mare.nom_ca || mare.pom_code || '',
            capa: etiquetaCapa(capaMare, t),
          })}
        </p>

        <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
          {opcio(mena === 'capa', () => setMena('capa'), 'm-capa', t('germana.mena_capa'))}
          {opcio(mena === 'instancia', () => setMena('instancia'), 'm-inst', t('germana.mena_instancia'))}
        </div>

        <p style={{ margin: '0 0 6px', fontSize: 'var(--fs-label)', color: 'var(--text-muted)',
                    textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {t(mena === 'capa' ? 'germana.tria_capa' : 'germana.tria_instancia')}
        </p>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
          {mena === 'capa'
            ? (capesLliures.length
              ? capesLliures.map(c => opcio(capa === c, () => setCapa(c), c, etiquetaCapa(c, t)))
              : <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('germana.cap_capa')}</span>)
            : (instLliures.length
              ? instLliures.map(i => opcio(instancia === i, () => setInstancia(i), i, etiquetaInstancia(i, t)))
              : <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('germana.cap_instancia')}</span>)}
        </div>

        <label style={{ display: 'block', marginBottom: 14 }}>
          <span style={{ display: 'block', fontSize: 'var(--fs-label)', color: 'var(--text-muted)',
                         textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
            {t('germana.nom')}{nomCal && ' *'}
          </span>
          <input value={nom} onChange={e => setNom(e.target.value)}
            placeholder={nomCal ? t('germana.nom_ph_obligatori', { base: mare.nom_fitxa || '' })
              : (mare.nom_fitxa || '')}
            style={{ width: '100%', padding: '6px 10px', borderRadius: 6, fontSize: 'var(--fs-body)',
                     border: '1px solid var(--border)', boxSizing: 'border-box' }} />
          <span style={{ display: 'block', marginTop: 4, fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
            {t(nomCal ? 'germana.nom_ajuda_obligatori' : 'germana.nom_ajuda')}
          </span>
        </label>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button type="button" onClick={onCancel} style={btnSecondary}>{t('app.cancel')}</button>
          <button type="button" onClick={crea} disabled={!potCrear} style={btnPrimary(!potCrear)}>
            {t('germana.crear')}
          </button>
        </div>
      </div>
    </div>
  )
}

// EL NOM DE LA FILA (v8.1) — text que SALTA DE LÍNIA, amb la instància a dins i la traducció a la ⓘ.
//
// El nom no viu dins d'un input permanent com al bateig de `MeasureGrid`, i el motiu és físic: un
// `<input>` no fa salt de línia, i «1/2 bottom width relaxed» o «CENTER FRONT YOKE HEIGHT» hi
// queden tallats a mitja paraula. La llei de la v8.1 és que un nom no es talli mai. Així que en
// repòs és text (que embolcalla) i el camp del bateig hi entra amb un clic — mateix component i
// MATEIXA PORTA que a l'altra graella (`BateigInput` → `baseMeasurements.setNoms`), no un segon
// mecanisme.
//
// La INSTÀNCIA va enganxada al nom i en el SEU color: no és una etiqueta al costat, és que aquesta
// mesura es diu «Profunditat de sisa · Esquerra». La ⓘ porta el nom en l'idioma de qui llegeix;
// era una segona línia permanent a cada fila i ara es demana, que és la freqüència amb què es mira.
function NomCanonic({ value, placeholder, instancia, traduccio, editable, estil, title, onSave }) {
  const [editant, setEditant] = useState(false)
  const [hover, setHover] = useState(false)

  if (editable && editant) {
    return (
      <BateigInput value={value} placeholder={placeholder} title={title}
        autoFocus onExit={() => setEditant(false)} onSave={onSave} style={estil} />
    )
  }
  return (
    <div
      onClick={editable ? (() => setEditant(true)) : undefined}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      title={editable ? title : undefined}
      style={{
        ...estil, cursor: editable ? 'text' : 'default',
        borderBottom: `1px ${editable && hover ? 'dashed var(--border)' : 'solid transparent'}`,
      }}>
      {value || placeholder}
      {instancia && <span style={{ fontWeight: 500 }}>{` · ${instancia}`}</span>}
      {traduccio && (
        <i className="ti ti-info-circle" title={traduccio} aria-label={traduccio}
          onClick={e => e.stopPropagation()}
          style={{ fontSize: 12, marginLeft: 6, color: 'var(--text-muted)', cursor: 'help' }} />
      )}
    </div>
  )
}

// EL CARRIL (v8.1) — la columna de valors és un camp SEMPRE OBERT, no un text que s'ha de clicar.
//
// Amb `EditableCell` cada mesura costava un clic per entrar-hi i un altre clic per sortir-ne: tretze
// files són tretze viatges al ratolí, i la mà del tècnic no surt del teclat numèric. Ara ↓/Enter
// baixa, ↑ puja, i Tab recorre els camps de la fila com a qualsevol formulari.
//
// El buffer és LOCAL i el commit és IMMEDIAT: es tecleja lliure (coma decimal inclosa) i el que
// puja al model és el número net. Un text no numèric es queda al buffer i es marca en vermell —no
// s'escriu i no es perd—, perquè escriure `NaN` a la taula i esborrar-lo en silenci seria pitjor
// que no acceptar-lo. Buit sí que s'escriu: buit és una decisió (la fila es descarta).
function CarrilInput({ value, readOnly, onCommit, registerVal, onNav, hint }) {
  const [txt, setTxt] = useState(value == null ? '' : String(value))
  const [focused, setFocused] = useState(false)
  const [bad, setBad] = useState(false)

  // La font de veritat torna del model mentre no s'hi escriu; amb el focus a dins mana el buffer
  // (si no, un refresc de la taula trepitjaria el que s'està teclejant).
  useEffect(() => { if (!focused) { setTxt(value == null ? '' : String(value)); setBad(false) } }, [value, focused])

  if (readOnly) {
    return (
      <span style={{ fontFamily: 'monospace', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
        {value == null || value === '' ? <span style={{ color: 'var(--text-muted)' }}>—</span> : value}
      </span>
    )
  }

  const onChange = (raw) => {
    setTxt(raw)
    const net = raw.replace(',', '.').trim()
    if (net !== '' && Number.isNaN(parseFloat(net))) { setBad(true); return }
    setBad(false)
    onCommit(raw)
  }

  return (
    <input
      ref={registerVal}
      type="text" inputMode="decimal" value={txt} title={hint}
      onFocus={e => { setFocused(true); e.target.select() }}
      onBlur={() => setFocused(false)}
      onChange={e => onChange(e.target.value)}
      onKeyDown={e => {
        if (e.key === 'ArrowDown' || e.key === 'Enter') { e.preventDefault(); onNav(1) }
        else if (e.key === 'ArrowUp') { e.preventDefault(); onNav(-1) }
        else if (e.key === 'Escape') { setTxt(value == null ? '' : String(value)); setBad(false) }
      }}
      style={{
        width: 78, padding: '3px 8px', textAlign: 'right',
        fontFamily: 'inherit', fontSize: FS_VAL, fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
        color: 'var(--text-main)', background: 'var(--white)',
        border: `1px solid ${bad ? 'var(--err)' : 'var(--border)'}`, borderRadius: 5,
        boxSizing: 'border-box',
      }}
    />
  )
}

// Nomenclatura CURTA de la fila (`nom_fitxa`: A, A-FOL, AH-L). Camp sempre obert perquè el Tab
// del carril hi pugui entrar; en repòs sembla text pla (la vora només apareix en hover/focus),
// que és el patró del bateig i de la columna POM de `MeasureGrid`. El placeholder és el codi del
// catàleg: buit vol dir «mana el catàleg», mai «sense nom».
function NomenInput({ value, placeholder, readOnly, onCommit }) {
  const [txt, setTxt] = useState(value ?? '')
  const [focused, setFocused] = useState(false)
  useEffect(() => { if (!focused) setTxt(value ?? '') }, [value, focused])

  if (readOnly) {
    return <span style={{ fontFamily: 'monospace', fontWeight: 600, color: 'var(--gold)' }}>{value || placeholder}</span>
  }
  return (
    <input
      value={txt} placeholder={placeholder}
      onFocus={() => setFocused(true)}
      onBlur={() => { setFocused(false); if ((txt ?? '') !== (value ?? '')) onCommit(txt) }}
      onChange={e => setTxt(e.target.value)}
      onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur() }}
      style={{
        width: 74, padding: '2px 6px', fontFamily: 'monospace', fontSize: FS_VAL,
        fontWeight: 600, color: 'var(--gold)', background: focused ? 'var(--white)' : 'transparent',
        border: '1px solid transparent', borderRadius: 5, boxSizing: 'border-box',
        ...(focused && { borderColor: 'var(--gold)' }),
      }}
    />
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
