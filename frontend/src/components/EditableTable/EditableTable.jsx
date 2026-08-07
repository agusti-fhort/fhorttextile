import { useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import {
  SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy,
  useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

import { etiquetaCapa, etiquetaInstancia, esGermanaDeCapa, CAPES } from '../../utils/capaInstancia'
import {
  dimensionsDe, eixPrincipal, nomEnIdioma, COMPLEMENTARIA, eixDe,
  tramsInstancia, composaInstancia,
  codiProposat, codiBase,
} from '../../utils/diccionariMesures'
import { useEstatDiccionari } from '../../utils/diccionariMesuresFont'
import AvisDiccionari from '../ui/AvisDiccionari'
import BateigInput from '../model/BateigInput'
import { baseMeasurements, poms } from '../../api/endpoints'

// LA REGLA DE GRADUACIÓ NO ÉS AQUÍ (ordre d'Agus, 05/08 · la maqueta que mana és la v8.1).
//
// Aquesta taula portava el bloc Règim · Δ · Δ break · Talla break, que va entrar amb la v8.2.
// S'ha retirat d'aquesta pantalla sencera: capçaleres, cel·les, el desplegable de règim i la
// porta que el desava (`models.setPomRegla`). Mesures és POMs, nomenclatura i valors.
//
// ⚠️ NO S'HA TOCAT NI EL MOTOR NI LES DADES: `ModelGradingRule` segueix igual, i la regla
// s'informa pel seu gest, que és on segueix vivint.
//
// P0.5b la va tornar a portar aquí en LECTURA (quatre columnes, sota `mostraGrading`) mentre
// graduar no tenia pantalla pròpia. P0.5d n'hi dona una —`GraduacioSuperficie`, on les quatre
// columnes són EDITABLES i on hi ha un «Gravar Graduació»— i per tant se'n tornen a anar
// d'aquí, ara del tot: cada superfície la seva feina. La CONSULTA (Taula de mesures) sí que
// les manté en lectura, que és el que P0.5b va deixar bé i no es toca.

// TIPOGRAFIA DE LA v8.1 (brief C5-UI · P1). Els dos cossos NO són tokens de la casa a posta:
// la maqueta aprovada demana 9,5px a la capçalera i 12,5px al valor, i cap dels graons del
// sistema (--fs-caption 8 · --fs-label 10 · --fs-body 12) hi cau a sobre. Es declaren aquí, amb
// nom, en comptes d'escampar-los per les cel·les — i els COLORS segueixen sent tokens, sempre.
// LES QUATRE COLUMNES DE LA REGLA (P0.5b). Es declaren un sol cop —capçalera i cel·la surten
// d'aquí— perquè afegir-ne o treure'n una no vulgui dir tocar dos llocs i que ballin.
// El valor es llegeix de la FILA; `null` vol dir «no ho diu» i es pinta `—`, mai un zero.
// Q2 (06/08) — LES AMPLADES DE LA FAMÍLIA, EN UN SOL LLOC I EXPORTADES.
//
// La Graduació (`GraduacioSuperficie`) és la MATEIXA taula amb altres columnes, i tenia les
// amplades escrites a mà: `W_NOM` clonat per còpia i la resta inventades (110/90/100/100 contra
// 96/84/96/96 d'aquí). Amb una taula a `width:100%` i totes les columnes fixades menys la
// primera, el sobrant se n'anava tot a la columna `#` — el forat de la captura de les 13:04.
// Ara els números viuen aquí i les dues pantalles els llegeixen; el `#` no en té cap a posta,
// perquè s'ha d'encongir al seu contingut a totes dues.
export const AMPLADES = {
  capa: 104, codi: 90, nom: 236, base: 100,
  regim: 96, delta: 84, delta_break: 96, talla_break: 96,
}

// LES QUATRE COLUMNES DE LA REGLA (P0.5b). Es declaren un sol cop —capçalera i cel·la surten
// d'aquí— perquè afegir-ne o treure'n una no vulgui dir tocar dos llocs i que ballin.
// El valor es llegeix de la FILA; `null` vol dir «no ho diu» i es pinta `—`, mai un zero.
const COLS_GRADING = [
  { clau: 'regim', i18n: 'fitting.grid.regime', ample: AMPLADES.regim, valor: r => r.logica || null },
  { clau: 'delta', i18n: 'editable_table.col.delta', ample: AMPLADES.delta,
    valor: r => (r.increment_base == null ? null : r.increment_base) },
  { clau: 'delta_break', i18n: 'editable_table.col.delta_break', ample: AMPLADES.delta_break,
    valor: r => (r.increment_break == null ? null : r.increment_break) },
  { clau: 'talla_break', i18n: 'editable_table.col.talla_break', ample: AMPLADES.talla_break,
    valor: r => r.talla_break_label || null },
]

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
  background: disabled ? 'var(--bg-muted)' : 'var(--gold)', color: disabled ? 'var(--text-muted)' : 'var(--text-main)',
  border: 'none', borderRadius: 6, padding: '7px 18px',
  fontSize: 'var(--fs-body)', fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer',
})
// v8.1 `kbd` :24-25 — la tecla dibuixada com una tecla: fons de capçalera, filet i cantonada.
function Kbd({ children }) {
  return (
    <kbd style={{
      background: 'var(--bg-muted)', border: '1px solid var(--border)', borderRadius: 4,
      padding: '1px 6px', font: 'inherit', fontSize: '10.5px', color: 'var(--text-main)',
    }}>{children}</kbd>
  )
}
const btnSecondary = {
  background: 'transparent', color: 'var(--text-muted)',
  border: '0.5px solid var(--border)',
  borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer',
}

// UNA SOLA TAULA, DOS MODES (05/08). «Definició POM» i «Mesurar prenda» són la mateixa eina
// —`mesures`— i han de ser la mateixa taula: la mateixa identitat de fila, els mateixos grups
// d'instància, el mateix carril, la mateixa barra d'estat, el mateix cercador. Fins avui eren
// dues pantalles que no s'assemblaven en res.
//
// El que ELS DIFERENCIA és una sola cosa, i és la que el domini diu: **l'autoria CREA la base;
// la presa MESURA CONTRA la base vigent**. D'aquí surten les dues úniques divergències:
//
//  1. ON VA EL NÚMERO DEL CARRIL. A l'autoria és la base i es desa amb el botó, en bloc. A la
//     presa és la PRESA, va a la seva línia de size check i s'hi desa sola; la base no es toca
//     fins que algú resol el check. Per això el mode `presa` no té botó de desar: no hi ha res
//     a confirmar en bloc, i deixar-lo hi seria una promesa d'un acte que no existeix.
//  2. UNA COLUMNA QUE LA v8.1 NO TÉ: la BASE VIGENT, en lectura, just abans del carril. Sense
//     ella «mesurar contra» no es pot fer —el que es compara és la xifra que s'acaba de prendre
//     amb la que el model ja tenia— i la maqueta no la porta perquè és d'autoria, on encara no
//     hi ha cap base contra què mesurar. S'hi afegeix a posta i es diu al report.
//
// La resta del mode `presa` NO és una pantalla nova: és aquesta, amb les escriptures d'identitat
// (capa · instància · nomenclatura · afegir · treure) anant per fila a la seva porta en comptes
// d'esperar el botó, perquè enmig d'una presa no hi ha cap moment natural per prémer «desar».
export default function EditableTable({
  rows,
  sizeRun,
  baseSize,
  modelId,
  isImport = false,
  readOnly = false,
  saveLabel,
  onPomSave,
  onSaved,
  // `null` = mode autoria_base. Amb objecte = mode presa, i porta les portes per fila:
  //   {baseLabel, onValor(row,val), onIdentitat(row,camps), onParteix(row,filles),
  //    onNova(pom,eixos), onTreu(row), onReordena(ids)}
  presa = null,
  // P0.5b, tornada a la CONSULTA (Agus, 06/08). `true` quan el model ja gradua —joc assignat o
  // regles pròpies—; sense això no hi són, perquè una taula que ensenya «Règim · Δ · Δ break ·
  // Talla break» a un model sense graduació promet quatre columnes que no es poden omplir.
  //
  // ⚠️ P0.5b només ho va cablejar a Definició POM, i P0.5d.4 les hi va treure (cada superfície
  // la seva feina: editar la regla és de `GraduacioSuperficie`). A la CONSULTA no hi han estat
  // mai, tot i que el comentari de dalt d'aquest fitxer ho donava per fet. Aquí hi tornen NOMÉS
  // en lectura: la consulta ensenya tot el que el model sap i no en deixa tocar res.
  mostraGrading = false,
}) {
  const esPresa = !!presa
  const { t, i18n } = useTranslation()
  const [localRows, setLocalRows] = useState(rows)
  // Crear POM propi del model: {nomInicial} mentre el formulari és obert, null si no.
  const [pomPropi, setPomPropi] = useState(null)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  // El vocabulari d'identitat (capes + instàncies + regla de composició). Amb `null` —mentre
  // no ha arribat, o si la petició falla— les píndoles surten inertes i la taula es veu igual:
  // la superfície de mesures no pot dependre d'un GET per pintar-se.
  const { dicc, error: diccError, reintenta: reintentaDicc } = useEstatDiccionari()
  // LES COLUMNES D'INSTÀNCIA I LES OPCIONS DE CADA UNA SÓN LES DE LA BD (D-31.26 · ordre d'Agus
  // 05/08). Un grup per EIX i, dins, totes les files d'aquell eix pel seu `display_order`: avui
  // vuit posicions i dos estats. Abans n'hi havia quatre escrites a mà al front —les de la
  // DEMOSTRACIÓ de la maqueta—, i les altres sis posicions no arribaven mai a la fila.
  // Amb el diccionari en vol la llista és buida i la taula es pinta igual, sense píndoles.
  const dims = dimensionsDe(dicc)
  // Les capes, també de la BD. `CAPES` és el mirall de la sembra i només serveix mentre el
  // diccionari no ha arribat: un desplegable buit no seria «encara no ho sé», seria «no n'hi ha».
  const capesDelDiccionari = dicc?.capes?.length ? dicc.capes.map(c => c.slug) : CAPES

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
      const seguit = arrayMove(prev, oldIdx, newIdx).map((r, i) => ({ ...r, ordre: i }))
      // A la presa l'ordre es desa tot sol: no hi ha botó que el pugui confirmar després.
      if (esPresa) marcaDesat(presa.onReordena(seguit.map(r => r.id))).catch(() => {})
      return seguit
    })
    if (!esPresa) setDirty(true)
  }

  const handleCellChange = (rowId, col, value) => {
    // A la PRESA cada camp té la seva porta i s'hi desa sol: el número va a la línia del check
    // i la nomenclatura a la mesura. Enmig d'una presa no hi ha cap moment natural per prémer
    // «desar», i el buffer local només serviria per perdre feina si algú tanca la pestanya.
    if (esPresa) {
      const fila = localRows.find(r => r.id === rowId)
      if (!fila) return
      if (col === 'base_value_cm') {
        const cru = String(value ?? '').replace(',', '.').trim()
        if (cru !== '' && Number.isNaN(parseFloat(cru))) return
        const net = cru === '' ? null : parseFloat(cru)
        setLocalRows(prev => prev.map(r => (r.id === rowId ? { ...r, base_value_cm: net } : r)))
        marcaDesat(presa.onValor(fila, net)).catch(() => {})
        return
      }
      setLocalRows(prev => prev.map(r => (r.id === rowId ? { ...r, [col]: value } : r)))
      marcaDesat(presa.onIdentitat(fila, { [col]: value })).catch(() => {})
      return
    }
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
  // v8.1 — DES DE L'ÚLTIMA FILA, ↓ ENTRA AL CERCADOR. El carril no s'acaba en una paret: el
  // gest natural després de la darrera mesura és afegir-ne una altra, i és allà on és el camp.
  const finderRef = useRef(null)
  const navVal = useCallback((rowId, dir) => {
    const ordre = rowsRef.current
    const i = ordre.findIndex(r => r.id === rowId)
    const target = ordre[i + dir]
    if (target) { valRefs.current[target.id]?.focus(); return }
    if (dir > 0 && i === ordre.length - 1) finderRef.current?.focus()
  }, [])

  // v8.1 — L'INDICADOR DE DESAT, per a les portes que desen SOLES.
  //
  // Aquesta taula té dos camps que no passen pel botó de desar: el BATEIG del nom i la REGLA.
  // Tots dos escriuen al servidor en perdre el focus, i fins ara no ho deia res: el tècnic
  // canviava un nom, no veia cap moviment, i l'única manera de saber si havia arribat era
  // recarregar. La maqueta ho resol amb un flaix a la barra d'estat, i és el que es fa aquí.
  //
  // L'ESTAT D'ERROR NO ÉS A LA MAQUETA i s'hi afegeix a posta: la maqueta no té servidor i no pot
  // fallar. Pintar «desat» quan la petició ha petat seria la pitjor mentida que pot dir un
  // indicador de desat — val més dir-ho i que el tècnic torni a provar-ho.
  const [desat, setDesat] = useState(null)          // null | 'saving' | 'saved' | 'failed'
  const desatT = useRef(null)
  useEffect(() => () => clearTimeout(desatT.current), [])
  const marcaDesat = (promesa) => {
    clearTimeout(desatT.current)
    setDesat('saving')
    return Promise.resolve(promesa)
      .then(r => {
        setDesat('saved')
        // El «desat» s'esvaeix sol: és una confirmació, no un estat de la taula.
        desatT.current = setTimeout(() => setDesat(null), 2000)
        return r
      })
      // L'error es queda a la vista fins al desat següent, que és quan deixa de ser cert.
      .catch(e => { setDesat('failed'); throw e })
  }

  // EL BATEIG — desa IMMEDIATAMENT per la porta pròpia i estreta del paquet NOMS-POM
  // (`PATCH base-measurements/<id>/noms/`), com ja fa la graella de consulta. No passa pel
  // botó de desar de la taula a posta: rebatejar una mesura no és editar-ne el valor, i
  // barrejar-ho voldria dir que canviar un nom deixés la taula «bruta» i arrossegués les
  // mesures a un desat que ningú ha demanat. `localRows` s'actualitza a mà perquè el que es
  // veu sigui el que s'acaba de desar sense haver de recarregar la taula sencera.
  const handleBateig = (bmId, camps) =>
    marcaDesat(baseMeasurements.setNoms(bmId, camps)
      .then(() => setLocalRows(prev => prev.map(r => (r.id === bmId ? { ...r, ...camps } : r)))))
      .catch(e => { console.error('No s\'ha pogut desar el nom', e) })

  const handleDeleteRow = (rowId) => {
    if (esPresa) {
      const fila = localRows.find(r => r.id === rowId)
      if (fila) marcaDesat(presa.onTreu(fila)).catch(() => {})
      return
    }
    setLocalRows(prev => prev.filter(r => r.id !== rowId).map((r, i) => ({ ...r, ordre: i })))
    setDirty(true)
  }

  // `eixos` ve del sufix del cercador (`C.f` → capa folre · `S.l` → instància left). Sense
  // sufix, la fila neix com sempre: exterior i instància única.
  const handleAddRow = (pom, eixos = {}) => {
    const capa = eixos.capa || 'exterior'
    const instancia = eixos.instancia || ''
    if (esPresa) {
      // A la presa la fila neix a la BD: no hi ha botó que la pugui desar més tard.
      marcaDesat(presa.onNova(pom, { capa, instancia })).catch(() => {})
      return
    }
    // La invariant `instancia_exigeix_nom` demana nom quan hi ha instància: el cercador el
    // PROPOSA aquí mateix amb la regla de D-31.26, i el patronista el pot reescriure.
    const nomFitxa = instancia
      ? (codiProposat(dicc, pom.codi_client || '', [instancia]) || instancia.toUpperCase())
      : ''
    const newRow = {
      id: `tmp-${Date.now()}`,
      pom_id: pom.id,
      pom_code: pom.codi_client,
      nom_ca: pom.nom_ca || pom.nom_client || '',
      nom_en: pom.nom_en || pom.nom_client || '',
      nom_fitxa: nomFitxa,
      capa,
      instancia,
      base_value_cm: null,
      graded: {},
      ordre: localRows.length,
    }
    setLocalRows(prev => [...prev, newRow])
    marcaNeix(newRow.id)
    setDirty(true)
  }

  // LA CAPA ES TRIA A LA FILA (v8.1 `select.cell` :56-58 · ordre d'Agus 05/08). Era LECTURA amb
  // l'argument que moure una mesura de capa és partir-la en dues; la maqueta diu una altra cosa i
  // mana ella: el desplegable canvia de quina matèria parla AQUESTA fila, i el botó del costat
  // (i la tecla `L`) és el que en fa una SEGONA a la capa següent. Són dos gestos diferents i
  // ara es distingeixen; abans n'hi havia un de sol i calia endevinar quin era.
  //
  // Les capes que aquest POM ja té amb la mateixa instància NO s'ofereixen: la clau única és
  // `(model, pom, capa, instancia)` i moure-s'hi escriuria damunt d'una fila viva en silenci.
  const capesLliuresDe = (row) => {
    const inst = row.instancia || ''
    const preses = new Set(localRows
      .filter(r => r.id !== row.id && r.pom_id === row.pom_id && (r.instancia || '') === inst)
      .map(r => r.capa || 'exterior'))
    return capesDelDiccionari.filter(c => !preses.has(c))
  }
  const handleCapa = (row, capa) => {
    if ((row.capa || 'exterior') === capa) return
    setLocalRows(prev => prev.map(r => (r.id === row.id ? { ...r, capa } : r)))
    if (esPresa) { marcaDesat(presa.onIdentitat(row, { capa })).catch(() => {}); return }
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
  //
  // EL DIÀLEG DE GERMANA HA MORT (05/08), i no és una funció menys: és la mateixa dues vegades.
  // Tenia dues branques —«una altra capa» i «una altra instància»— i totes dues ja tenen el seu
  // gest a la fila, que és on la maqueta les posa: la capa, al desplegable i al botó del costat
  // (tecla `L`); la instància, a les píndoles i al modal `＋`, que a més ofereix les vuit
  // posicions i el creuament dels dos eixos, cosa que el diàleg no feia. Dos camins per a un sol
  // acte volien dir dues maneres de compondre el codi i el slug de la mateixa germana.
  const [posicionsDe, setPosicionsDe] = useState(null)  // fila mare del modal `＋`

  // v8.1 — LA FILA ACTIVA I LA FILA QUE ACABA DE NÉIXER.
  //
  // Totes dues responen la mateixa pregunta —«on sóc?»— en dos moments diferents. Amb tretze
  // files i quatre germanes, la columna de valors sola no situa: el carril mou el focus amunt i
  // avall sense que res acompanyi la mirada cap a l'esquerra, on hi ha el nom que diu QUINA
  // mesura s'està teclejant. El ressaltat de fila és aquesta línia de lectura.
  //
  // `filaNeix` es buida sola: el flaix és la resposta a un gest, no un estat de la fila. Es guarda
  // l'id i no un booleà per fila perquè només n'hi pot haver una de recent.
  const [filaActiva, setFilaActiva] = useState(null)
  const [filaNeix, setFilaNeix] = useState(null)
  const neixT = useRef(null)
  useEffect(() => () => clearTimeout(neixT.current), [])
  const marcaNeix = (id) => {
    clearTimeout(neixT.current)
    setFilaNeix(id)
    neixT.current = setTimeout(() => setFilaNeix(null), 1100)
  }

  // v8.1 — LA TECLA `L`: la germana de CAPA sense diàleg i sense treure la mà del carril.
  //
  // La maqueta la resol amb `mkLayerSibling`, que agafa LA SEGÜENT capa del catàleg. Aquí s'agafa
  // la següent LLIURE (saltant les que aquest POM ja té amb la mateixa instància), perquè la clau
  // única és `(model, pom, capa, instancia)` i oferir-ne una de presa escriuria damunt d'una fila
  // existent en silenci. Sense cap capa lliure no fa res: no hi ha germana possible.
  //
  // El NOM no cal (la capa ja distingeix la fila i la BD no l'exigeix), o sigui que el gest pot
  // ser d'una sola tecla. El diàleg segueix existint per a qui vulgui TRIAR la capa; això és la
  // drecera del cas freqüent, que és folrar.
  const germanaCapaRapida = (mare) => {
    if (!mare) return
    const inst = mare.instancia || ''
    const preses = new Set(localRows
      .filter(r => r.pom_id === mare.pom_id && (r.instancia || '') === inst)
      .map(r => r.capa || 'exterior'))
    const seguent = capesDelDiccionari.find(c => !preses.has(c))
    if (!seguent) return
    if (esPresa) {
      marcaDesat(presa.onNova(
        { id: mare.pom_id, codi_client: mare.pom_code },
        { capa: seguent, instancia: inst, nom_fitxa: mare.nom_fitxa || '' })).catch(() => {})
      return
    }
    insereixGermana(mare, { capa: seguent, instancia: inst, nom_fitxa: mare.nom_fitxa || '' })
  }

  const insereixGermana = (mare, { capa, instancia, nom_fitxa }) => {
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
    marcaNeix(nova.id)
    setDirty(true)
  }

  // ── B1 · LES PÍNDOLES D'INSTÀNCIA (v8.1 · `dimState` :235-242) ─────────────────────────────
  //
  // L'ESTAT D'UNA DIMENSIÓ ES MIRA A LA FAMÍLIA, NO A LA FILA. La família és el mateix POM a la
  // mateixa capa: l'exterior i el folre del pit són dues mesures diferents i cadascuna es pot
  // partir per la seva banda. Quan una germana ja ha pres una opció de l'eix, l'eix queda REPARTIT
  // i les dues píndoles es deshabiliten —també la que està encesa—: repartir dues vegades pel
  // mateix eix no vol dir res, i la manera de desfer-ho és treure una de les dues files.
  //
  // `mine` es calcula per EIX i no per pertinença a les dues opcions en línia: una fila que ja
  // sigui `top` té l'eix POSICIÓ ocupat encara que ni «Esquerra» ni «Dreta» hi surtin enceses, i
  // el tooltip ho ha de dir amb el nom real (el diccionari en té vuit, i aquí només n'hi caben
  // dues; la resta viuen al modal `＋`).
  const dimState = (row, eix) => {
    const meus = tramsInstancia(dicc, row.instancia)
    const mine = meus.find(s => eixDe(dicc, s) === eix) || null
    const capa = row.capa || 'exterior'
    const repartida = localRows.some(x =>
      x.pom_id === row.pom_id && (x.capa || 'exterior') === capa &&
      tramsInstancia(dicc, x.instancia).some(s => eixDe(dicc, s) === eix))
    return { mine, repartida }
  }

  // PARTIR UN POM (v8.1 · `splitPair` :306-319). La fila DESAPAREIX i en neixen DUES: la que s'ha
  // triat i la seva complementària, totes dues amb els valors heretats i amb el codi compost
  // segons D-31.26 (`base + sufix`, concatenat).
  //
  // ⚠️ ELS VALORS S'HERETEN, i és el que mana la maqueta. És el contrari del que fa la germana de
  // CAPA (que neix buida a posta): allà s'AFEGEIX una mesura que ningú ha pres mai, i aquí es
  // PARTEIX una que ja estava presa —la sisa mesurada val per a totes dues bandes fins que algú
  // les torni a mesurar—. Són dos actes diferents i per això tenen dues respostes diferents.
  //
  // La fila original es perd a propòsit: la seva identitat `(pom, capa, '')` deixa d'existir, i
  // `keep_mesures` (que es construeix de `localRows`) ja no la portarà → el backend la poda i
  // escriu les dues noves. Això ÉS partir; conservar-la deixaria tres files on n'hi ha d'haver dues.
  //
  // `aplica` és el motor comú de les píndoles i del modal `＋`: rep els trams TRIATS (un per eix
  // com a molt) i si se n'ha de fer també la complementària. Un sol camí perquè les dues portes
  // componguin el codi i el slug exactament igual — dos camins voldrien dir dues identitats per a
  // la mateixa germana, i la clau única de la BD no perdona això.
  const aplicaInstancia = (row, trams, ambComplementaria) => {
    if (!dicc || !trams.length) return
    const eixosTocats = new Set(trams.map(s => eixDe(dicc, s)).filter(Boolean))
    const meus = tramsInstancia(dicc, row.instancia)
    const altres = meus.filter(s => !eixosTocats.has(eixDe(dicc, s)))
    // El codi base és el que quedava abans que cap sufix s'hi enganxés: re-partir `AHL` ha de
    // donar `AHL`/`AHR` i no `AHLL`.
    const base = codiBase(dicc, row.nom_fitxa || row.client_code || row.pom_code || '', meus)
    const fill = (tramsFila, marca) => {
      const tots = [...altres, ...tramsFila]
      const inst = composaInstancia(dicc, tots)
      // La invariant de BD `instancia_exigeix_nom` no admet nom buit amb instància. Amb un eix
      // que no compon sufix (els ESTATS) la proposta és el codi base tal qual, que ja val; si
      // ni tan sols n'hi hagués, el slug fa de nom abans que deixar petar el desat amb un 500.
      const codi = codiProposat(dicc, base, tots) || inst.toUpperCase()
      return {
        ...row,
        id: `tmp-${Date.now()}-${marca}`,
        instancia: inst,
        nom_fitxa: codi,
        // `clau` és la que serveix el backend per indexar els deltes: una identitat nova no en
        // té cap, i heretar la de la mare li ensenyaria el Δ d'una fila que ja no existeix.
        clau: undefined,
      }
    }
    // LA COMPLEMENTÀRIA ES GIRA PEL PRIMER EIX DEL DICCIONARI si n'hi ha (avui la posició: la
    // sisa esquerra vol dir que n'hi ha una de dreta); si només s'ha triat un ESTAT, es gira
    // l'estat. Les posicions sense parella (`side`, `waistband_seam`) no en tenen, i llavors no
    // se'n crea cap segona fila. Quin eix mana el diu el diccionari, no aquest fitxer.
    const principal = eixPrincipal(dicc)
    const aGirar = trams.find(s => COMPLEMENTARIA[s] && eixDe(dicc, s) === principal)
      || trams.find(s => COMPLEMENTARIA[s])
    const compTrams = ambComplementaria && aGirar
      ? trams.map(s => (s === aGirar ? COMPLEMENTARIA[s] : s))
      : null
    const files = [fill(trams, 'a')]
    if (compTrams) files.push(fill(compTrams, 'b'))
    if (esPresa) {
      // La fila mare no desapareix i en neix una de nova: a la BD la mesura ja existeix i té
      // preses penjades. Es REESCRIU la seva identitat i la germana s'hi afegeix al costat.
      marcaDesat(presa.onParteix(row, files)).catch(() => {})
      return
    }
    setLocalRows(prev => {
      const i = prev.findIndex(r => r.id === row.id)
      if (i < 0) return prev
      return [...prev.slice(0, i), ...files, ...prev.slice(i + 1)]
    })
    setDirty(true)
  }

  const parteix = (row, opt) => aplicaInstancia(row, [opt], true)

  // ── Q1 (06/08) · EL TOGGLE HONEST DE LA PÍNDOLA ────────────────────────────────────────────
  //
  // 🔴 EL DEFECTE: prémer una píndola PARTIA el POM a l'acte i no hi havia camí de tornada. La
  // píndola encesa quedava DESHABILITADA («repartir dues vegades pel mateix eix no vol dir res»)
  // i desfer-ho volia dir anar a treure la germana amb la ✕ i tornar a batejar la mare a mà: un
  // gest de dos passos per desdir-se'n d'un de sol. Una píndola que s'encén i no s'apaga no és
  // un interruptor, és una porta d'un sol sentit.
  //
  // LA LLEI: prémer una píndola NO seleccionada parteix (com sempre); prémer la JA SELECCIONADA
  // DESFÀ. I el POM base no es toca mai en cap dels dos sentits: desfer RETIRA LA GERMANA i
  // torna la fila premuda a la identitat base — la mesura del model sobreviu sempre.
  //
  // ⚠️ SI LA GERMANA TÉ VALOR ENTRAT, ES PREGUNTA. «Cap valor entrat» vol dir el carril buit
  // (a la presa, la xifra que s'hi ha pres; a l'autoria, el valor base): una germana que ningú
  // ha omplert es retira en silenci, i una amb número no s'esborra sense dir-ho. Les files que
  // encara no han arribat a la BD (`tmp-…`) es retiren sempre en silenci: no hi ha res a perdre.
  const [desfent, setDesfent] = useState(null)   // {row, eix, germanes} pendent de confirmació

  // V5a (06/08 vespre) — AQUEST MODAL TAMBÉ ES TANCA AMB TECLAT. El mateix que es va arreglar a
  // `ModalPosicions` (commit 57) i que aquest va tornar a néixer sense: el vel és
  // `position:fixed inset:0` i intercepta tots els clics de sota, o sigui que qui l'obre sense
  // voler hi queda atrapat. Cap modal de la casa pot ser un cul-de-sac de teclat.
  //
  // I EL FOCUS, QUE AQUÍ NO ÉS COSMÈTIC: en obrir-se va al botó de CANCEL·LAR, no al de
  // confirmar. Aquest modal retira germanes amb valor pres —feina de mesurar— i deixar el gest
  // destructiu just sota l'Enter és convidar-hi. En tancar-se, el focus torna d'on venia (la
  // píndola de la fila), que és des d'on es continua treballant.
  const desferCancelRef = useRef(null)
  const focusAbansDesfer = useRef(null)
  useEffect(() => {
    if (!desfent) return undefined
    focusAbansDesfer.current = document.activeElement
    const esc = (e) => { if (e.key === 'Escape') { e.preventDefault(); setDesfent(null) } }
    document.addEventListener('keydown', esc)
    desferCancelRef.current?.focus()
    return () => {
      document.removeEventListener('keydown', esc)
      focusAbansDesfer.current?.focus?.()
    }
  }, [desfent])

  const teValor = (r) => r.base_value_cm != null && r.base_value_cm !== ''
  const trasDe = (r, eix) => tramsInstancia(dicc, r.instancia).filter(s => eixDe(dicc, s) !== eix)
  const clauResta = (r, eix) => [...trasDe(r, eix)].sort().join('|')

  // LES GERMANES QUE VAN NÉIXER D'AQUESTA PARTICIÓ: mateixa família (POM + capa), amb un tram
  // d'aquest eix, i amb LA RESTA D'EIXOS IGUAL que la fila premuda. L'última condició importa el
  // dia que una família estigui partida per dos eixos: desfent la POSICIÓ de `left-relaxed` s'ha
  // de retirar `right-relaxed`, i no `left-extended`, que és una altra mesura.
  const germanesDeLEix = (row, eix) => {
    const capa = row.capa || 'exterior'
    const resta = clauResta(row, eix)
    return localRows.filter(x => x.id !== row.id
      && x.pom_id === row.pom_id && (x.capa || 'exterior') === capa
      && tramsInstancia(dicc, x.instancia).some(s => eixDe(dicc, s) === eix)
      && clauResta(x, eix) === resta)
  }

  // La identitat de la fila SENSE aquest eix: el slug es recompon amb els trams que queden i el
  // codi torna al seu base (`AHL` → `AH`), pel mateix camí que el va compondre.
  const identitatSenseEix = (row, eix) => {
    const meus = tramsInstancia(dicc, row.instancia)
    const resta = meus.filter(s => eixDe(dicc, s) !== eix)
    const base = codiBase(dicc, row.nom_fitxa || row.client_code || row.pom_code || '', meus)
    return {
      instancia: composaInstancia(dicc, resta),
      nom_fitxa: resta.length ? (codiProposat(dicc, base, resta) || base) : base,
    }
  }

  const aplicaDesfer = (row, eix, germanes) => {
    const ident = identitatSenseEix(row, eix)
    setDesfent(null)
    if (esPresa) {
      // Una superfície de presa que no declari la porta de desfer no ha de petar: la píndola
      // simplement no fa res (i es veu, perquè segueix encesa).
      if (!presa.onDesfaInstancia) return
      marcaDesat(presa.onDesfaInstancia(row, ident, germanes)).catch(() => {})
      return
    }
    const fora = new Set(germanes.map(g => g.id))
    setLocalRows(prev => prev
      .filter(r => !fora.has(r.id))
      .map(r => (r.id === row.id ? { ...r, ...ident, clau: undefined } : r)))
    setDirty(true)
  }

  const desfaInstancia = (row, eix) => {
    if (!dicc) return
    const germanes = germanesDeLEix(row, eix)
    const ambValor = germanes.filter(g => teValor(g) && !String(g.id).startsWith('tmp-'))
    if (ambValor.length) { setDesfent({ row, eix, germanes, ambValor }); return }
    aplicaDesfer(row, eix, germanes)
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
  // (`PropagatedEditor`), que és on ara es toquen els deltes. El prop `deltes` se'n va amb ella:
  // sense columna Δ, el mapa que el backend serveix no el mira ningú en aquesta pantalla.

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

  const displaySize = baseSize || sizeRun?.[0]
  // Les columnes reals de la taula, per al `colSpan` del peu: nansa · # · capa · codi · nom ·
  // (un grup per eix + el `＋`) · valor · accions. Es compta i no s'escriu a mà perquè el nombre
  // de grups d'instància el decideix la BD, i un literal aquí tornaria a ser el segon lloc que
  // creu saber quantes dimensions hi ha.
  const colCount = (readOnly ? 0 : 1) + 4 + (readOnly ? 0 : dims.length + 1)
    + (esPresa && !readOnly ? 1 : 0) + (mostraGrading ? COLS_GRADING.length : 0) + 1 + (readOnly ? 0 : 1)
  const stickyHd = (left, w) => ({ ...thS, position: 'sticky', left, zIndex: 3, width: w, minWidth: w, background: 'var(--bg-muted)' })
  // Bloc d'IDENTITAT de la fila, congelat a l'esquerra: Capa · nomenclatura · nom. Amb dues
  // germanes vives (el mateix POM a l'exterior i al folre, la sisa esquerra i la dreta) el nom
  // sol ja no diu quina fila és cadascuna, i és justament la columna que ha de quedar visible
  // mentre s'escruta la taula cap a la dreta.
  const { capa: W_CAPA, codi: W_CODI, nom: W_NOM } = AMPLADES
  // Quantes files es desaran i quantes cauran. La llei del carril («buit = es descarta») és
  // muda si el descart només es veu fila a fila: aquí es llegeix el total abans de desar.
  const nInformades = localRows.filter(r => r.base_value_cm != null && r.base_value_cm !== '').length
  const nBuides = localRows.length - nInformades

  return (
    <div style={!readOnly ? { paddingBottom: 56 } : undefined}>
      {/* v8.1 `.kbd-hint` :158-163 — LA LÍNIA DE DRECERES, sota el títol i sobre la taula.
          Aquesta taula es treballa amb les dues mans al teclat i cap de les tecles es podia
          endevinar: la `L` de la germana de capa existia des de B4 i no ho deia enlloc.
          Només s'hi anuncia el que FUNCIONA de debò en aquesta pantalla. */}
      {!readOnly && (
        <p style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)',
                    margin: '0 0 14px', lineHeight: 1.8 }}>
          <Kbd>↓</Kbd>/<Kbd>Enter</Kbd> {t('editable_table.kbd_next')} · <Kbd>↑</Kbd> {t('editable_table.kbd_prev')}
          {' · '}<b style={{ color: 'var(--gold)' }}><Kbd>L</Kbd> {t('editable_table.kbd_capa')}</b>
          {' · '}<b style={{ color: 'var(--gold)' }}><Kbd>I</Kbd> {t('editable_table.kbd_instancia')}</b>
          {' · '}<Kbd>N</Kbd> {t('editable_table.kbd_nomen')}
          {' · '}{t('editable_table.kbd_finder')}
          {/* «buit = es descarta» és una llei de l'AUTORIA. A la presa, una fila en blanc és
              una mesura que encara no s'ha pres — no es descarta res. */}
          {' · '}{t(esPresa ? 'presa.kbd_buit' : 'editable_table.kbd_buit')}
        </p>
      )}
      {/* P0.2 — EL VOCABULARI QUE NO ARRIBA ES DIU. Sense això, un GET fallat es veia
          exactament igual que un catàleg sense instàncies: les columnes de POSICIÓ i ESTAT
          desapareixien i la pantalla callava. El 06/08, amb el MILEY, això va deixar l'Agus
          sense poder crear germanes i sense cap pista del motiu.
          Va amb REINTENTA perquè la fallada típica és transitòria (la petició surt abans que
          la sessió estigui a punt): recarregar la pàgina no hauria de ser l'única sortida. */}
      {!readOnly && diccError && (
        <AvisDiccionari hint={t('dicc.error_hint_taula')} onReintenta={reintentaDicc} />
      )}
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
              <tr style={{
                background: 'var(--bg-muted)',
                borderBottom: '1px solid var(--border)',
              }}>
                {!readOnly && <th rowSpan={2} style={thS}></th>}
                <th rowSpan={2} style={thS}>#</th>
                <th rowSpan={2} style={stickyHd(0, W_CAPA)}>{t('capa.col')}</th>
                <th rowSpan={2} style={stickyHd(W_CAPA, W_CODI)}>{t('measuregrid.col_pom')}</th>
                <th rowSpan={2} style={stickyHd(W_CAPA + W_CODI, W_NOM)}>{t('measuregrid.col_nom')}</th>
                {/* v8.1 `th.grp` — EL GRUP D'INSTÀNCIA, amb `--sel` de fons i `--gold` a la
                    lletra. Un grup de columnes per EIX del diccionari (avui posició i estat) i
                    el `＋` de les combinacions. Va entre el NOM i el valor perquè és part de
                    QUINA mesura és la fila, no de què s'hi mesura. */}
                {!readOnly && dims.length > 0 && (
                  <th colSpan={dims.length + 1} style={{ ...thS, textAlign: 'center', background: 'var(--gold-pale)',
                                           color: 'var(--gold)', fontWeight: 600, borderLeft: '1px solid var(--border)' }}>
                    {t('instancia.grup')}
                  </th>
                )}
                {/* LA BASE VIGENT — la columna que la v8.1 NO té, i que LA PRESA necessita.
                    «Mesurar contra» vol dir comparar la xifra que s'acaba de prendre amb la que
                    el model ja tenia; sense aquesta columna el carril seria un número sol i la
                    comparació s'hauria de fer de memòria.

                    NOMÉS A LA PRESA, però. En CONSULTA les dues columnes diuen EL MATEIX número
                    —la base del model— des que la consulta llegeix `BaseMeasurement` en comptes
                    d'un check que pot no existir (`e6958b28`): allà «Talla base» i «Base vigent»
                    són la mateixa cosa escrita dues vegades, i una taula que repeteix una xifra
                    fa dubtar de si són dues xifres diferents. Es queda la que respon la pregunta
                    de la consulta: la TALLA BASE. */}
                {esPresa && !readOnly && (
                  <th rowSpan={2} style={{ ...thS, textAlign: 'right', minWidth: 96,
                                           borderLeft: '1px solid var(--border)' }}>
                    {presa.baseLabel || t('presa.col_base_vigent')}
                  </th>
                )}
                {/* v8.1 — LA CAPÇALERA DEL CARRIL DIU DE QUINA TALLA SÓN AQUESTES XIFRES.
                    Era el literal de la talla sol, amb el cos de versaleta de la resta de
                    capçaleres: una «S» de 9,5 px perduda entre «RÈGIM» i «DELTA BREAK». És
                    l'única columna on s'escriuen mesures i la primera pregunta de qui obre la
                    taula és de quina talla parlen — l'etiqueta ho nomena i el cos gran ho fa
                    trobar sense llegir.
                    Sense talla base (model sense `base_size_label`) es queda el literal de
                    sempre: inventar-hi una etiqueta «Talla base» sobre un «Valor base» seria
                    prometre una talla que ningú ha declarat.
                    v8.1 `th.baseh` — el carril va ACOTAT pels dos costats amb `--line`: és una
                    columna sencera de fons `--sel` i, sense filets, es vessa sobre les veïnes. */}
                <th rowSpan={2} style={{ ...thS, textAlign: 'right', minWidth: AMPLADES.base, background: 'var(--gold-pale)',
                                         borderLeft: '1px solid var(--border)', borderRight: '1px solid var(--border)' }}>
                  {displaySize ? (
                    <>
                      <span style={{ display: 'block', fontWeight: 600, color: 'var(--gold)' }}>
                        {t('editable_table.col.base_size_label')}
                      </span>
                      <span style={{ display: 'block', fontSize: 15, fontWeight: 600, lineHeight: 1.1,
                                     letterSpacing: 'normal', textTransform: 'none', color: 'var(--text-main)' }}>
                        {displaySize}
                      </span>
                    </>
                  ) : t('editable_table.col.base_value')}
                </th>
                {/* P0.5b — LA REGLA, en LECTURA, DESPRÉS de la talla base. Els quatre camps
                    viatgen a la fila; aquí només es pinten quan hi ha graduació de què parlar. */}
                {mostraGrading && COLS_GRADING.map((c, i) => (
                  <th key={c.clau} rowSpan={2}
                      style={{ ...thS, textAlign: 'right', minWidth: c.ample,
                               borderLeft: i === 0 ? '1px solid var(--border)' : '0.5px solid var(--border)' }}>
                    {t(c.i18n)}
                  </th>
                ))}
                {!readOnly && <th rowSpan={2} style={thS}></th>}
              </tr>
              {/* v8.1 `tr.r2` — la segona línia de la capçalera NOMENA CADA DIMENSIÓ. Els noms
                  són els del DICCIONARI (`eixos[].nom_*`), no literals d'i18n: el dia que la
                  Montse afegeixi un tercer eix, la columna nova ha de sortir amb el seu nom
                  sense tocar el front. */}
              {!readOnly && dims.length > 0 && (
                <tr style={{ background: 'var(--bg-muted)', borderBottom: '1px solid var(--border)' }}>
                  {dims.map((d, k) => (
                    <th key={d.clau} style={{ ...thS, textAlign: 'center', minWidth: 132,
                                              borderLeft: k === 0 ? '1px solid var(--border)' : '0.5px solid var(--border)' }}>
                      {nomEnIdioma(d, i18n.language)}
                    </th>
                  ))}
                  <th style={{ ...thS, textAlign: 'center', minWidth: 52,
                               borderLeft: '0.5px solid var(--border)' }}>{t('instancia.mes')}</th>
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
                    activa={row.id === filaActiva}
                    neix={row.id === filaNeix}
                    onActiva={setFilaActiva}
                    dicc={dicc}
                    dims={dims}
                    esPresa={esPresa}
                    dimState={dimState}
                    onParteix={parteix}
                    onDesfa={desfaInstancia}
                    onMesInstancia={() => setPosicionsDe(row)}
                    onGermanaCapa={() => germanaCapaRapida(row)}
                    capesLliures={capesLliuresDe(row)}
                    mostraGrading={mostraGrading}
                    onCapa={handleCapa}
                    onCellChange={handleCellChange}
                    onDelete={handleDeleteRow}
                    onBateig={handleBateig}
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
                    <CercadorPOM dicc={dicc} modelId={modelId} onAdd={handleAddRow}
                      onCrearPropi={nom => setPomPropi({ nomInicial: nom })}
                      registerFinder={el => { finderRef.current = el }}
                      onSurt={() => {
                        const ultima = rowsRef.current[rowsRef.current.length - 1]
                        if (ultima) valRefs.current[ultima.id]?.focus()
                      }} />
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </DndContext>
      </div>

      {posicionsDe && (
        <ModalPosicions
          mare={posicionsDe}
          dicc={dicc}
          // Les cares que aquest POM JA té: la clau única és `(model, pom, capa, instancia)` i
          // oferir-ne una de repetida escriuria damunt d'una fila existent en silenci.
          existents={localRows.filter(r => r.pom_id === posicionsDe.pom_id
            && (r.capa || 'exterior') === (posicionsDe.capa || 'exterior'))}
          onCancel={() => setPosicionsDe(null)}
          onAplica={(trams, ambComp) => { aplicaInstancia(posicionsDe, trams, ambComp); setPosicionsDe(null) }} />
      )}

      {/* Q1 — LA CONFIRMACIÓ DE DESFER. NOMÉS surt quan hi ha una xifra a perdre: desfer una
          partició que ningú ha omplert no ha de costar una pregunta. La fila premuda no hi
          surt perquè no se'n va enlloc — torna a la seva identitat base. */}
      {desfent && (
        <div onClick={() => setDesfent(null)}
          style={{ position: 'fixed', inset: 0, zIndex: 80, background: 'rgba(0,0,0,0.28)',
                   display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div onClick={e => e.stopPropagation()}
            role="dialog" aria-modal="true" aria-labelledby="desfa-titol"
            style={{ background: 'var(--white)', borderRadius: 10, padding: '1.25rem 1.4rem',
                     width: 'min(460px, 92vw)', boxShadow: '0 10px 40px rgba(0,0,0,0.2)' }}>
            <h3 id="desfa-titol"
                style={{ margin: '0 0 10px', fontSize: 'var(--fs-h3)', fontWeight: 600,
                         display: 'flex', alignItems: 'center', gap: 8 }}>
              <i className="ti ti-alert-triangle" style={{ color: 'var(--warn)' }} aria-hidden="true" />
              {t('instancia.desfa_titol')}
            </h3>
            <p style={{ margin: '0 0 12px', fontSize: 'var(--fs-body)', lineHeight: 1.5,
                        color: 'var(--text-main)' }}>
              {t('instancia.desfa_avis', { count: desfent.ambValor.length })}
            </p>
            <ul style={{ margin: '0 0 16px', paddingLeft: 18, fontSize: 'var(--fs-body)',
                         color: 'var(--text-muted)' }}>
              {desfent.ambValor.map(g => (
                <li key={g.id}>
                  {g.nom_fitxa || g.client_code || g.pom_code} · {etiquetaInstancia(g.instancia, dicc)}
                  {' · '}{g.base_value_cm}
                </li>
              ))}
            </ul>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button type="button" ref={desferCancelRef} onClick={() => setDesfent(null)}
                style={{ padding: '6px 14px', borderRadius: 6, border: '0.5px solid var(--border)',
                         background: 'var(--white)', color: 'var(--text-main)', font: 'inherit',
                         fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
                {t('common.cancel')}
              </button>
              <button type="button"
                onClick={() => aplicaDesfer(desfent.row, desfent.eix, desfent.germanes)}
                style={{ padding: '6px 14px', borderRadius: 6, border: 'none',
                         background: 'var(--err)', color: 'var(--white)', font: 'inherit',
                         fontSize: 'var(--fs-body)', fontWeight: 500, cursor: 'pointer' }}>
                {t('instancia.desfa_confirma')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* El POM neix i s'afegeix a la taula en el MATEIX gest: qui l'ha hagut de crear és perquè
          el vol posar en aquesta fila, i obligar-lo a tornar a cercar-lo seria fer-li dir dues
          vegades el que ja ha dit. `handleAddRow` rep la mateixa forma que un resultat de cerca,
          que és per això que el backend la retorna igual. */}
      {pomPropi && modelId && (
        <ModalPomPropi
          modelId={modelId}
          nomInicial={pomPropi.nomInicial}
          onTanca={() => setPomPropi(null)}
          onFet={(pom) => { setPomPropi(null); handleAddRow(pom, {}) }} />
      )}

      {/* v8.1 · `.statusbar` :140-144 — LA BARRA D'ESTAT VA FIXA AL PEU DE LA FINESTRA i no
          sota la taula. Amb tretze files i el carril obert, el que la barra diu —quantes es
          desaran i quantes cauran— és exactament el que s'ha de poder llegir MENTRE s'escriu, i
          sota la taula queda fora de pantalla just quan es fa servir. */}
      {!readOnly && (
        <div style={{
          position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 20,
          background: 'var(--white)', borderTop: '1px solid var(--border)',
          padding: '10px 24px', display: 'flex', gap: 22, alignItems: 'center',
          fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
        }}>
          <span>{t(esPresa ? 'presa.count_taken' : 'editable_table.count_filled', { n: nInformades })}</span>
          {nBuides > 0 && (
            <span>{t(esPresa ? 'presa.count_pending' : 'editable_table.count_empty', { n: nBuides })}</span>
          )}
          {/* A la dreta del tot: els recomptes diuen QUÈ hi ha a la taula i el flaix diu QUÈ
              acaba de passar. Són dues lectures diferents i no s'han de barrejar. */}
          {desat && (
            <span aria-live="polite" style={{ marginLeft: 'auto',
                                              color: desat === 'failed' ? 'var(--err)' : 'var(--gold)' }}>
              {t(`editable_table.save_${desat}`)}
            </span>
          )}
        </div>
      )}

      {/* CAP BOTÓ DE DESAR EN BLOC A LA PRESA: tot s'ha desat ja, camp a camp. Un botó aquí
          prometria un acte que no existeix, i el que SÍ que existeix —tancar el check— viu a la
          barra de resolució, que és de la sessió i no de la taula. */}
      {!readOnly && !esPresa && (dirty || onPomSave) && (
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

function SortableRow({ row, n, readOnly, activa, neix, onActiva, onCellChange, onDelete,
                       onBateig, widths, registerVal, onNav, esPresa,
                       dicc, dims, dimState, onParteix, onDesfa, onMesInstancia, onGermanaCapa,
                       capesLliures, onCapa, mostraGrading = false }) {
  const { t } = useTranslation()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: row.id })

  // EL LLAPIS D'IDENTITAT (Agus, 06/08) — la identitat de la fila (NOM + NOMENCLATURA) s'edita
  // amb un gest DELIBERAT, i tots dos camps alhora.
  //
  // Abans cada camp s'obria pel seu compte clicant-hi a sobre. En una taula que es treballa amb
  // el ratolí a sobre de tretze files, això vol dir que un clic mal posat obria un editor de
  // nom sense que ningú l'hagués demanat — i el que hi ha a sota és el nom amb què aquesta
  // mesura viatja al fabricant. Ara el text és ESTÀTIC i l'única porta és el llapis.
  //
  // L'estat viu a la FILA i no dins de cada camp, perquè el que s'obre és la identitat sencera:
  // el nom i la nomenclatura són la mateixa resposta a «quina mesura és aquesta», i editar-los
  // per separat era el que feia que se'n canviés un i l'altre es quedés dient una altra cosa.
  const [editantIdentitat, setEditantIdentitat] = useState(false)

  // BUIT = ES DESCARTA, i qui ho diu és la BARRA D'ESTAT del peu, no la fila.
  //
  // Aquí hi havia dues marques a cada fila en blanc: el nom rebaixat a `opacity .45` i un
  // «· es descartarà» enganxat al costat. Amb la taula acabada d'obrir —que és com arriba
  // sempre, amb totes les mesures per prendre— les portaven TOTES, i una marca que és a totes
  // les files no distingeix cap fila: era soroll amb forma d'avís (ordre d'Agus, 05/08).
  // El recompte del peu («n en blanc → es descartaran») ho diu un cop i ho diu bé.
  const buida = row.base_value_cm == null || row.base_value_cm === ''

  // L'arrossegament mana sobre el ressaltat: mentre una fila viatja, el que ha de dir el fons és
  // que viatja. El fons de la fila i el de les cel·les congelades han de ser el MATEIX valor, o
  // el ressaltat es partiria just a la frontera de la columna sticky.
  // v8.1 (`tr.lin` :45-46) — LA FILA D'UNA CAPA QUE NO ÉS L'EXTERIOR TÉ FONS PROPI. La columna
  // de Capa ja ho diu amb lletres, però amb tretze files el que separa dos blocs a cop d'ull és
  // el to, no llegir la primera cel·la de cadascuna. L'arrossegament mana sobre tots dos.
  const deCapa = esGermanaDeCapa(row.capa)
  const rowBg = isDragging ? 'var(--bg-muted)'
    : activa ? (deCapa ? 'var(--fila-capa-activa)' : 'var(--fila-activa)')
      : (deCapa ? 'var(--fila-capa)' : 'var(--white)')

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    background: rowBg,
    borderBottom: '0.5px solid var(--border)',
  }
  const stickyTd = (left, w) => ({
    ...tdS, position: 'sticky', left, zIndex: 1, width: w, minWidth: w,
    background: rowBg, borderBottom: '0.5px solid var(--border)',
  })

  return (
    <tr ref={setNodeRef} style={style} className={neix ? 'ftt-fila-neix' : undefined}
      data-fila={row.id}>
      {!readOnly && (
        <td style={tdS}>
          <span {...attributes} {...listeners}
            style={{ cursor: 'grab', color: 'var(--text-muted)', fontSize: 'var(--fs-h3)' }}>
            ⠿
          </span>
        </td>
      )}
      <td style={{ ...tdS, color: 'var(--text-muted)', fontSize: 'var(--fs-label)' }}>{n}</td>
      {/* LA CAPA (D-31.22 · v8.1 `.laywrap` :55) — de quina matèria de la peça parla aquesta
          mesura. Es mostra SEMPRE, també quan totes les files diuen «Exterior»: una columna que
          apareix el dia que neix la primera germana faria que la taula canviés de forma sota els
          peus del tècnic, i el que ha de canviar és el CONTINGUT d'una cel·la.
          DOS CONTROLS I DOS ACTES: el desplegable CANVIA la capa d'aquesta fila; el botó del
          costat (i la tecla `L` des del carril) en fa una SEGONA a la capa lliure següent. */}
      <td style={{ ...stickyTd(0, widths.capa), color: 'var(--text-main)', whiteSpace: 'normal' }}>
        {readOnly ? etiquetaCapa(row.capa, t) : (
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <select value={row.capa || 'exterior'} tabIndex={-1}
              aria-label={t('capa.col')}
              onChange={e => onCapa(row, e.target.value)}
              style={{
                font: 'inherit', fontSize: '11.5px', color: 'var(--text-main)',
                background: 'var(--white)', border: '1px solid var(--border)',
                borderRadius: 5, padding: '2px 6px', minWidth: 90, maxWidth: '100%',
              }}>
              {capesLliures.map(c => <option key={c} value={c}>{etiquetaCapa(c, t)}</option>)}
            </select>
            <button type="button" onClick={onGermanaCapa} tabIndex={-1}
              title={t('germana.capa_tecla')} aria-label={t('germana.capa_tecla')}
              style={{
                background: 'none', border: '1px solid transparent', borderRadius: 5,
                padding: 3, lineHeight: 0, color: 'var(--text-muted)', cursor: 'pointer',
                display: 'inline-flex',
              }}>
              <i className="ti ti-layers-subtract" style={{ fontSize: 15 }} />
            </button>
          </span>
        )}
      </td>
      <td style={stickyTd(widths.capa, widths.codi)}>
        {/* C3 — NOMENCLATURA DEL CLIENT del model (CustomerPOMAlias): el codi que el tècnic
            escriu als documents d'aquest client (Brownie diu "A" on el catàleg diu "CH"), i
            els seus noms EN/local. Sense àlies per aquest POM, el catàleg de la casa, com
            sempre. La nomenclatura per-model (nom_fitxa) segueix manant per damunt de tot:
            és la que el tècnic ha escrit aquí mateix. */}
        <NomenInput value={row.nom_fitxa} placeholder={row.client_code || row.pom_code || ''}
          readOnly={readOnly || !editantIdentitat}
          onCommit={v => onCellChange(row.id, 'nom_fitxa', v)} />
        {row.is_key && (
          <i className="ti ti-star" title="KEY"
            style={{ fontSize: 9, marginLeft: 5, color: 'var(--gold)', verticalAlign: 'middle' }} />
        )}
      </td>
      <td style={stickyTd(widths.capa + widths.codi, widths.nom)}>
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
          // Paraula sencera («Left», mai «L») i EN EL COLOR DEL NOM: és el nom d'aquesta mesura
          // el que s'allarga, no una etiqueta enganxada al costat. Amb `AH-L`/`AH-R` com a única
          // marca, dir quina fila és quina volia dir conèixer la nomenclatura del client.
          // EN ANGLÈS CANÒNIC i sense traduir (05/08): d'aquesta paraula surt el sufix del codi,
          // i «· Esquerra» amb codi `AHL` serien dues llengües a la mateixa línia.
          const inst = etiquetaInstancia(row.instancia, dicc)
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
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6 }}>
              <div style={{ minWidth: 0, flex: 1 }}>
                <NomCanonic
                  value={row.nom_canonic_model || ''} placeholder={dalt || ''} instancia={inst}
                  traduccio={traduit} editant={nomEditable && editantIdentitat} estil={estilDalt}
                  title={t('measuregrid.nom_canonic_tip')}
                  onExit={() => setEditantIdentitat(false)}
                  onSave={v => onBateig(bmId, { nom_canonic_model: v })} />
              </div>
              {/* L'ÚNICA porta a l'edició de la identitat. Obre el nom I la nomenclatura alhora:
                  són la mateixa resposta i s'han de poder quadrar de cop. */}
              {nomEditable && (
                <button type="button" data-llapis="1"
                  onClick={() => setEditantIdentitat(v => !v)}
                  aria-pressed={editantIdentitat}
                  title={t('editable_table.edita_identitat')}
                  aria-label={t('editable_table.edita_identitat')}
                  style={{
                    background: 'none', border: 'none', padding: 2, cursor: 'pointer',
                    color: editantIdentitat ? 'var(--gold)' : 'var(--text-muted)',
                    flexShrink: 0, lineHeight: 1,
                  }}>
                  <i className="ti ti-pencil" style={{ fontSize: 13 }} aria-hidden="true" />
                </button>
              )}
            </div>
          )
        })()}
      </td>
      {/* v8.1 `td.dimcell` — LES PÍNDOLES D'INSTÀNCIA: una cel·la per DIMENSIÓ del diccionari i,
          dins, totes les opcions d'aquella dimensió pel seu ordre de presentació. Amb el
          diccionari encara en vol no hi ha cap columna: la taula no espera cap GET per pintar-se
          i les columnes apareixen quan el vocabulari arriba. */}
      {/* LES PÍNDOLES SÓN LES DUES PRIMERES DE CADA EIX; la resta, pel `＋` (Agus, 06/08).
          La posició té VUIT opcions al diccionari i totes vuit a la fila feien una cel·la
          il·legible per oferir sempre les dues que es fan servir cada dia (Left · Right).
          CRITERI: **les dues primeres per `display_order` del diccionari** — no hi ha cap slug
          escrit al codi. Avui l'ordre del catàleg dona left(1) · right(2), que és exactament el
          que la decisió demana; si el catàleg reordena, la fila el segueix sense tocar res.
          Cap opció es perd: el modal del `＋` recorre TOTS els eixos amb TOTES les opcions, i a
          més és l'únic lloc que pot creuar-los (`left` i `relaxed` alhora). */}
      {!readOnly && dims.map((d, k) => {
        const st = dimState(row, d.clau)
        const visibles = d.opcions.slice(0, 2)
        return (
          <td key={d.clau} style={{ ...tdS, textAlign: 'center', padding: '4px 8px',
                                    borderLeft: k === 0 ? '1px solid var(--border)' : '0.5px solid var(--border)' }}>
            {/* Q1 — LA MATEIXA PÍNDOLA, ELS DOS SENTITS: encesa desfà, apagada parteix. */}
            {visibles.map(o => (
              <PindolaInstancia key={o.slug} fila={o}
                encesa={st.mine === o.slug} repartida={st.repartida} altra={st.mine} dicc={dicc}
                onTria={() => (st.mine === o.slug ? onDesfa(row, d.clau) : onParteix(row, o.slug))} />
            ))}
          </td>
        )
      })}
      {!readOnly && dims.length > 0 && (
        <td style={{ ...tdS, textAlign: 'center', padding: '4px 8px',
                     borderLeft: '0.5px solid var(--border)' }}>
          {/* v8.1 `.qmore` — el CREUAMENT dels eixos (una germana pot ser `left` i `relaxed`
              alhora) i la complementària desmarcable, que les píndoles no poden oferir perquè
              elles AFIRMEN que n'hi ha dues. */}
          <button type="button" onClick={onMesInstancia}
            title={t('instancia.mes_tip')} aria-label={t('instancia.mes_tip')}
            style={{ background: 'none', border: '1px dashed var(--border)', borderRadius: 999,
                     padding: '3px 9px', font: 'inherit', fontSize: 'var(--fs-label)',
                     color: 'var(--text-main)', cursor: 'pointer' }}>＋</button>
        </td>
      )}
      {/* LA BASE VIGENT, en lectura i NOMÉS a la presa (v. la capçalera). `—` quan el model
          encara no en té cap: una fila que s'està prenent per primera vegada no ment dient zero. */}
      {esPresa && !readOnly && (
        <td style={{ ...tdS, textAlign: 'right', borderLeft: '1px solid var(--border)',
                     fontVariantNumeric: 'tabular-nums', color: 'var(--text-main)' }}>
          {row.base_vigent == null || row.base_vigent === ''
            ? <span style={{ color: 'var(--text-muted)' }}>—</span>
            : row.base_vigent}
        </td>
      )}
      {/* v8.1 `td.valcell` — EL CARRIL, acotat pels dos costats amb `--line` sobre `--sel`. */}
      <td style={{ ...tdS, textAlign: 'right', background: 'var(--gold-pale)',
                   borderLeft: '1px solid var(--border)', borderRight: '1px solid var(--border)' }}>
        <CarrilInput
          value={row.base_value_cm}
          readOnly={readOnly}
          onCommit={v => onCellChange(row.id, 'base_value_cm', v)}
          registerVal={el => registerVal?.(row.id, el)}
          onNav={dir => onNav?.(row.id, dir)}
          // La fila activa és la que té el focus AL CARRIL, no la que s'ha clicat: el carril és
          // el recorregut de treball, i és ell qui ha de dir per on va.
          // v8.1 — la tecla `L` fa la germana de CAPA sense treure la mà del carril. És el gest
          // més freqüent de la taula (tota peça folrada el fa) i costava anar a buscar una icona.
          // `I` salta a la primera píndola lliure de la fila i `N` a la nomenclatura curta: les
          // dues columnes que s'editen mentre es prenen mesures, sense passar per Tab ni ratolí.
          onTeclaCapa={onGermanaCapa}
          onTeclaInstancia={() => {
            const p = document.querySelector(`[data-fila="${row.id}"] button[data-pindola="1"]:not(:disabled)`)
            p?.focus()
          }}
          onTeclaNomen={() => document.querySelector(`[data-fila="${row.id}"] input[data-nomen]`)?.focus()}
          onEnfoca={() => onActiva?.(row.id)}
          onDesenfoca={() => onActiva?.(prev => (prev === row.id ? null : prev))}
          hint={buida ? t(esPresa ? 'presa.row_pending' : 'editable_table.row_discarded') : undefined} />
      </td>
      {/* P0.5b — la regla d'aquesta mesura, en LECTURA. `—` quan el camp no diu res: una cel·la
          buida es llegiria com un zero, i un règim sense delta no és un delta de zero. */}
      {mostraGrading && COLS_GRADING.map((c, i) => (
        <td key={c.clau}
            style={{ ...tdS, textAlign: 'right', fontVariantNumeric: 'tabular-nums',
                     color: 'var(--text-main)',
                     borderLeft: i === 0 ? '1px solid var(--border)' : '0.5px solid var(--border)' }}>
          {c.valor(row) ?? <span style={{ color: 'var(--text-muted)' }}>—</span>}
        </td>
      ))}
      {!readOnly && (
        <td style={{ ...tdS, whiteSpace: 'nowrap' }}>
          {/* v8.1 `.del` — TREURE EL POM, i prou. El botó de germana que hi havia al costat era
              la porta del diàleg que ha mort: els seus dos actes viuen ara a la fila mateixa
              (el desplegable i el botó de capa · les píndoles i el `＋`). */}
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

// LA PÍNDOLA D'UNA OPCIÓ D'INSTÀNCIA (v8.1 · `.qw` :76-86). Paraula SENCERA, mai una inicial:
// «Left», no «L». El sufix `L` és per al CODI, i confondre les dues coses és el que feia que dir
// quina fila era quina volgués dir conèixer la nomenclatura del client. La paraula la porta el
// DICCIONARI i va en anglès canònic: no es tradueix, perquè és la que allarga el nom del POM.
//
// EL CONTROL VA EN ACTIU (ordre d'Agus, 05/08). Estava pintat en gris apagat sobre blanc i es
// llegia com una cosa que no es pot prémer; una píndola LLIURE és exactament el contrari —és el
// gest principal d'aquesta columna—. La paleta és la de la maqueta: `--line` sobre `--panel` amb
// la lletra en `--ink`, i encesa, `--sel` amb `--gold`.
//
// L'ÚNIC APAGAT que queda és el que `dimState` deshabilita: l'eix ja repartit entre germanes.
// Allà no hi ha res a prémer, i la manera de desfer-ho és treure una de les dues files.
//
// ELS TRES ESTATS, cadascun amb el seu tooltip, perquè es distingeixin sense provar-los:
//   · ENCESA      → «Left — aquesta fila»
//   · REPARTIDA   → «Repartida — la germana és Right» (o el nom real, si l'eix el va prendre una
//                   posició que no és cap de les dues: `top`, `cf`…)
//   · LLIURE      → «Left — parteix el POM (valors heretats)», que diu QUÈ passarà en prémer.
function PindolaInstancia({ fila, dicc, encesa, repartida, altra, onTria }) {
  const { t } = useTranslation()
  const nom = etiquetaInstancia(fila.slug, dicc)
  // Q1 — LA PÍNDOLA ENCESA JA NO ÉS INERT: és el gest per DESFER. El seu tooltip ho ha de dir,
  // perquè fins avui deia «aquesta és la instància d'aquesta fila» i semblava una etiqueta.
  const tip = encesa ? t('instancia.tip_desfa', { nom })
    : repartida ? t('instancia.tip_repartida', {
      nom: etiquetaInstancia(altra && altra !== fila.slug ? altra : fila.slug, dicc) })
      : t('instancia.tip_parteix', { nom })
  // La píndola de DESFER es marca a part (`data-pindola="desfa"`): la tecla `I` —saltar a la
  // primera píndola lliure— busca una de PARTIR, i amb un sol marcador hi podria caure la de
  // desfer i retirar una germana amb un Enter que ningú havia demanat. Les fletxes segueixen
  // recorrent-les totes.
  return (
    <button type="button" disabled={repartida && !encesa} onClick={onTria} title={tip} aria-label={tip}
      aria-pressed={encesa} data-pindola={encesa ? 'desfa' : '1'}
      // v8.1 :350-357 — un cop dins dels grups (tecla `I`), les fletxes els recorren i `Esc`
      // torna al carril. Sense això, `I` seria una porta d'entrada sense sortida.
      onKeyDown={e => {
        const fila = e.currentTarget.closest('[data-fila]')
        if (!fila) return
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          e.preventDefault()
          const totes = [...fila.querySelectorAll('button[data-pindola]:not(:disabled)')]
          const i = totes.indexOf(e.currentTarget)
          totes[i + (e.key === 'ArrowRight' ? 1 : -1)]?.focus()
        } else if (e.key === 'Escape') {
          e.preventDefault()
          fila.querySelector('input[data-carril]')?.focus()
        }
      }}
      style={{
        font: 'inherit', fontSize: 'var(--fs-label)', borderRadius: 999, padding: '2px 10px',
        margin: '0 2px', cursor: repartida && !encesa ? 'default' : 'pointer',
        border: `1px solid ${encesa ? 'var(--gold)' : 'var(--border)'}`,
        background: encesa ? 'var(--gold-pale)' : 'var(--white)',
        color: encesa ? 'var(--gold)' : 'var(--text-main)',
        fontWeight: encesa ? 600 : 400,
        opacity: repartida && !encesa ? 0.4 : 1,
      }}>{nom}</button>
  )
}

// ── B2 · EL MODAL `＋` · EL CREUAMENT DELS EIXOS (v8.1 `.qmore` :268) ────────────────────────
//
// Les píndoles de la fila ofereixen les opcions d'UN eix cadascuna, i amb això no es pot demanar
// una germana que sigui `left` I `relaxed` alhora: prémer la segona píndola reescriuria el primer
// eix. El creuament és el que viu aquí, i per això el modal recorre TOTS els eixos del diccionari
// —no dos escrits a mà— amb una tria per eix.
//
// LA COMPLEMENTÀRIA ÉS DESMARCABLE, i aquesta és l'altra diferència de fons amb les píndoles.
// Prémer una píndola AFIRMA que n'hi ha dues (si hi ha una sisa esquerra, n'hi ha una de dreta).
// Però «CF» pot ser l'única: una mesura al centre davant no implica que n'hi hagi una al centre
// darrere. Qui ho sap és el patronista, i aquí se li pregunta en comptes de decidir-ho per ell.
// Les posicions que no tenen parella (`side`, `waistband_seam`) ni tan sols ofereixen la casella.
function ModalPosicions({ mare, dicc, existents, onCancel, onAplica }) {
  const { t, i18n } = useTranslation()
  // La tria és PER EIX: `{POSICIO: 'left', ESTAT: 'relaxed'}`. Un estat per eix i no dos camps
  // amb nom propi, perquè els eixos els compta el diccionari.
  const [tria, setTria] = useState({})
  const [ambComp, setAmbComp] = useState(true)

  // ESC TANCA (cua post-QA, 06/08). El vel es tancava només amb clic a fora, i el fum de la
  // identitat de la fila ja ho va anotar el 05/08: qui l'obria sense voler s'hi quedava
  // atrapat —el vel és `position:fixed inset:0` i intercepta tots els clics de sota—. Cap
  // modal de la casa pot ser un cul-de-sac de teclat.
  useEffect(() => {
    const esc = (e) => { if (e.key === 'Escape') { e.preventDefault(); onCancel() } }
    document.addEventListener('keydown', esc)
    return () => document.removeEventListener('keydown', esc)
  }, [onCancel])

  const dims = dimensionsDe(dicc)
  const principal = eixPrincipal(dicc)
  // L'ordre dels trams és el dels EIXOS (posició abans que estat), que és el mateix que
  // `composaInstancia` fa servir per compondre el slug: així la proposta de codi que es llegeix
  // aquí és exactament la que s'escriurà.
  const trams = dims.map(d => tria[d.clau]).filter(Boolean)

  const preses = new Set(existents.map(r => r.instancia || ''))
  // Una combinació ja presa no s'ofereix: crear-la no faria res, escriuria damunt de la fila que
  // ja hi ha i el tècnic veuria desaparèixer una mesura sense saber per què.
  const jaHiEs = trams.length > 0 && preses.has(composaInstancia(dicc, trams))

  // Es gira el tram del PRIMER eix que en tingui, de complementària; si aquell no en té (o no
  // s'ha triat), el primer que en tingui de qualsevol eix. Mateixa regla que `aplicaInstancia`.
  const aGirar = trams.find(s => COMPLEMENTARIA[s] && eixDe(dicc, s) === principal)
    || trams.find(s => COMPLEMENTARIA[s]) || null
  const compDe = aGirar ? COMPLEMENTARIA[aGirar] : null
  const base = codiBase(dicc, mare.nom_fitxa || mare.client_code || mare.pom_code || '',
                        tramsInstancia(dicc, mare.instancia))
  const codiA = trams.length ? (codiProposat(dicc, base, trams) || composaInstancia(dicc, trams).toUpperCase()) : ''
  const compTrams = compDe ? trams.map(s => (s === aGirar ? compDe : s)) : []
  const codiB = compDe && ambComp
    ? (codiProposat(dicc, base, compTrams) || composaInstancia(dicc, compTrams).toUpperCase())
    : ''

  const xip = (actiu, onClick, clau, text, inert) => (
    <button key={clau} type="button" onClick={inert ? undefined : onClick} disabled={inert}
      style={{
        padding: '5px 12px', borderRadius: 999, cursor: inert ? 'default' : 'pointer',
        font: 'inherit', fontSize: 'var(--fs-body)',
        border: `1px solid ${actiu ? 'var(--gold)' : 'var(--border)'}`,
        background: actiu ? 'var(--gold-pale)' : 'var(--white)',
        color: actiu ? 'var(--gold)' : 'var(--text-main)', fontWeight: actiu ? 500 : 400,
        opacity: inert ? 0.4 : 1,
      }}>{text}</button>
  )

  return (
    <div onClick={onCancel}
      style={{ position: 'fixed', inset: 0, zIndex: 80, background: 'rgba(0,0,0,0.28)',
               display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div onClick={e => e.stopPropagation()}
        style={{ background: 'var(--white)', borderRadius: 10, padding: '1.25rem 1.4rem',
                 width: 'min(560px, 92vw)', boxShadow: '0 10px 40px rgba(0,0,0,0.2)' }}>
        <h3 style={{ margin: '0 0 4px', fontSize: 'var(--fs-h3)', fontWeight: 500 }}>
          {t('instancia.modal_titol')}
        </h3>
        <p style={{ margin: '0 0 14px', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
          {t('instancia.modal_subtitol', {
            nom: mare.nom_canonic_model || mare.nom_en || mare.nom_ca || mare.pom_code || '',
          })}
        </p>

        {/* UN BLOC PER EIX, amb el nom que el diccionari li dona. Si la Montse n'hi afegeix un
            tercer, aquí surt sol. */}
        {dims.map(d => (
          <div key={d.clau}>
            <p style={{ margin: '0 0 6px', fontSize: 'var(--fs-label)', color: 'var(--text-muted)',
                        textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {nomEnIdioma(d, i18n.language)}
            </p>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
              {d.opcions.map(f => xip(tria[d.clau] === f.slug,
                () => setTria(prev => ({ ...prev, [d.clau]: prev[d.clau] === f.slug ? '' : f.slug })),
                f.slug, etiquetaInstancia(f.slug, dicc), false))}
            </div>
          </div>
        ))}

        {compDe && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
                          fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
            <input type="checkbox" checked={ambComp} onChange={e => setAmbComp(e.target.checked)} />
            <span>{t('instancia.modal_complementaria', { nom: etiquetaInstancia(compDe, dicc) })}</span>
          </label>
        )}

        {/* LA PROPOSTA DE CODI, A LA VISTA ABANS DE CONFIRMAR. És el que anirà al `nom_fitxa`, i
            el patronista el pot reescriure després: val més que el vegi ara que no que el
            descobreixi a la taula. */}
        {trams.length > 0 && (
          <p style={{ margin: '0 0 12px', fontSize: 'var(--fs-body)',
                      color: jaHiEs ? 'var(--err)' : 'var(--text-muted)' }}>
            {jaHiEs
              ? t('instancia.modal_ja_hi_es')
              : t('instancia.modal_proposta', { codis: [codiA, codiB].filter(Boolean).join(' · ') })}
          </p>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button type="button" onClick={onCancel} style={btnSecondary}>{t('app.cancel')}</button>
          <button type="button" disabled={!trams.length || jaHiEs}
            onClick={() => onAplica(trams, ambComp && !!compDe)}
            style={btnPrimary(!trams.length || jaHiEs)}>
            {t('instancia.modal_crear')}
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
// `editant` ve de la FILA (el llapis), ja no d'un clic aquí dins: v. la capçalera de
// `SortableRow`. En repòs el text és ESTÀTIC —ni cursor de text, ni subratllat en passar-hi per
// sobre, ni res que convidi a clicar-lo—, perquè obrir l'editor del nom ha de ser una decisió i
// no la conseqüència d'un clic mal posat mentre es treballa la taula.
function NomCanonic({ value, placeholder, instancia, traduccio, marca = '', editant, estil, title, onExit, onSave }) {
  if (editant) {
    return (
      <BateigInput value={value} placeholder={placeholder} title={title}
        autoFocus onExit={onExit} onSave={onSave} style={estil} />
    )
  }
  return (
    <div style={{ ...estil, cursor: 'default' }}>
      {value || placeholder}
      {instancia && <span style={{ fontWeight: 500 }}>{` · ${instancia}`}</span>}
      {marca && (
        <span style={{ fontSize: 10, fontStyle: 'italic', color: 'var(--text-muted)' }}>{`  ${marca}`}</span>
      )}
      {traduccio && <InfoTraduccio text={traduccio} />}
    </div>
  )
}

// LA ⓘ DE LA TRADUCCIÓ — el nom en la llengua de qui llegeix, a demanda.
//
// PER QUÈ NO FUNCIONAVA (06/08). La dada hi era i l'atribut també: la ⓘ es pintava amb un
// `title` natiu i el text correcte a dins. El que fallava era el MECANISME — el tooltip del
// navegador només surt passant-hi per sobre i esperant-se un segon llarg, no respon al clic, i
// damunt d'una icona de 12px la meitat de les vegades no arriba a sortir. Es demanava una
// traducció i semblava que la ⓘ no fes res.
//
// Ara respon a les tres coses: HOVER, CLIC (que la deixa fixada, per poder-la llegir amb calma)
// i FOCUS de teclat. `Esc` i un clic a fora la tanquen.
//
// Va per PORTAL, i no és cosmètic: la cel·la del nom viu dins del contenidor `overflow-x:auto`
// de la taula, i qualsevol cosa posicionada que en surti queda RETALLADA — la mateixa trampa que
// es va pagar amb el desplegable del cercador (P0.2b).
// EXPORTADA (06/08): la Graduació ha de dur la MATEIXA ⓘ, no una que se li assembli. Copiar-la
// hauria estat el segon tooltip del sistema amb la seva pròpia manera de posicionar-se.
export function InfoTraduccio({ text }) {
  const [hover, setHover] = useState(false)
  const [fixat, setFixat] = useState(false)
  const [pos, setPos] = useState(null)
  const ref = useRef(null)
  const obert = hover || fixat

  useEffect(() => {
    if (!obert) { setPos(null); return undefined }
    const situa = () => {
      const r = ref.current?.getBoundingClientRect()
      if (r) setPos({ left: Math.min(r.left, window.innerWidth - 260), top: r.bottom + 6 })
    }
    situa()
    window.addEventListener('scroll', situa, true)
    window.addEventListener('resize', situa)
    return () => {
      window.removeEventListener('scroll', situa, true)
      window.removeEventListener('resize', situa)
    }
  }, [obert])

  useEffect(() => {
    if (!fixat) return undefined
    const fora = (e) => { if (!ref.current?.contains(e.target)) setFixat(false) }
    const esc = (e) => { if (e.key === 'Escape') setFixat(false) }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [fixat])

  return (
    <>
      <button
        ref={ref} type="button" data-info-traduccio="1"
        aria-label={text} aria-expanded={obert}
        onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
        onFocus={() => setHover(true)} onBlur={() => setHover(false)}
        // `stopPropagation` encara que el text ja no s'editi per clic: la ⓘ viu dins d'una
        // cel·la que participa del recorregut de la taula i no ha d'arrossegar-hi res.
        onClick={(e) => { e.stopPropagation(); setFixat(v => !v) }}
        // MIDA PRÒPIA, no la del glif: si la font d'icones no carrega, l'`<i>` es queda a zero
        // i el botó seria un objectiu de 0×0 —impossible de clicar i sense manera de saber per
        // què—. Amb la caixa declarada aquí, la ⓘ es pot demanar encara que el glif no hi sigui.
        style={{
          background: 'none', border: 'none', padding: 0, marginLeft: 6, lineHeight: 1,
          width: 16, height: 16, display: 'inline-flex',
          alignItems: 'center', justifyContent: 'center', verticalAlign: 'middle',
          color: obert ? 'var(--gold)' : 'var(--text-muted)', cursor: 'help',
        }}>
        <i className="ti ti-info-circle" style={{ fontSize: 12 }} aria-hidden="true" />
      </button>
      {obert && pos && createPortal(
        <div role="tooltip" style={{
          position: 'fixed', left: pos.left, top: pos.top, zIndex: 1300, maxWidth: 250,
          background: 'var(--white)', border: '1px solid var(--gold)', borderRadius: 6,
          padding: '5px 10px', fontSize: 'var(--fs-body)', color: 'var(--text-main)',
          boxShadow: '0 4px 14px rgba(0,0,0,0.12)', pointerEvents: 'none',
        }}>{text}</div>,
        document.body,
      )}
    </>
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
function CarrilInput({ value, readOnly, onCommit, registerVal, onNav, hint, onEnfoca, onDesenfoca,
                       onTeclaCapa, onTeclaInstancia, onTeclaNomen }) {
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
      data-carril="1"
      type="text" inputMode="decimal" value={txt} title={hint}
      onFocus={e => { setFocused(true); e.target.select(); onEnfoca?.() }}
      onBlur={() => { setFocused(false); onDesenfoca?.() }}
      onChange={e => onChange(e.target.value)}
      onKeyDown={e => {
        if (e.key === 'ArrowDown' || e.key === 'Enter') { e.preventDefault(); onNav(1) }
        else if (e.key === 'ArrowUp') { e.preventDefault(); onNav(-1) }
        else if (e.key === 'Escape') { setTxt(value == null ? '' : String(value)); setBad(false) }
        else if (!e.ctrlKey && !e.metaKey && !e.altKey) {
          // Al carril s'hi escriuen NÚMEROS: cap lletra hi és mai un valor, i per això poden ser
          // dreceres sense robar res al teclat numèric. Les tres de la v8.1 (:158-163):
          //   L → la germana de capa · I → els grups d'instància · N → la nomenclatura curta.
          const gest = { l: onTeclaCapa, i: onTeclaInstancia, n: onTeclaNomen }[e.key.toLowerCase()]
          if (gest) { e.preventDefault(); gest() }
        }
      }}
      style={{
        width: 78, padding: '3px 8px', textAlign: 'right',
        fontFamily: 'inherit', fontSize: FS_VAL, fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
        color: 'var(--text-main)', background: 'var(--white)',
        // v8.1 — la cel·la del carril amb el focus porta la vora daurada (`tr.cur input.val`).
        // El vermell del valor no numèric mana per damunt: un error és més urgent que una posició.
        border: `1px solid ${bad ? 'var(--err)' : focused ? 'var(--gold)' : 'var(--border)'}`, borderRadius: 5,
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
      data-nomen="1"
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

// ── B3 · EL CERCADOR DEL PEU DE TAULA (v8.1 · `tr.newrow` :272-277 · `.finder` :119) ─────────
//
// Tres coses que el botó «Afegir POM» d'abans no feia:
//
//  1. ÉS SEMPRE VISIBLE. Era un botó que calia trobar i clicar per obrir un camp. La v8.1 el vol
//     al peu, obert, perquè afegir una mesura és part de treballar la taula i no una excepció.
//  2. AGRUPA PER PROXIMITAT. «de l'item» · «de la família» · «del catàleg del client». Qui busca
//     «C» a la taula d'un jersei vol la seva cintura, no la d'una americana que comparteix
//     catàleg. El nivell el resol el backend (`?model=`), que és qui sap el mapa de l'item.
//  3. ENTÉN ELS SUFIXOS. «C.f» és la cintura AL FOLRE i «S.l» la sisa ESQUERRA: en una taula amb
//     germanes, escriure el codi i triar després la capa a un altre lloc són dos gestos per a
//     una sola intenció.
//
// LA RESOLUCIÓ DEL SUFIX ÉS DETERMINISTA i va per aquest ordre, contra el diccionari real:
//     sufix exacte d'instància (L·R·T·B·CF·CB·S) → prefix de CAPA → prefix d'instància.
// L'ordre importa perquè hi ha col·lisions: `f` és prefix de `folre` I de `fornitura`, i es
// resol pel `display_order` del catàleg (folre va primer, que és el que la maqueta demana amb
// «C.f»); `r` podria ser `right` o `relaxed`, i el sufix exacte `R` mana i dona `right`.
// Un sufix que no resol NO s'inventa: la cerca es fa amb el text sencer.
function resolSufix(dicc, cua) {
  if (!dicc || !cua) return null
  const c = cua.toLowerCase()
  const posicions = dicc.instancies?.POSICIO || []
  const estats = dicc.instancies?.ESTAT || []
  const totes = [...posicions, ...estats]
  const perOrdre = (a, b) => (a.display_order ?? 99) - (b.display_order ?? 99)

  const perSufix = totes.find(f => (f.sufix || '').toLowerCase() === c)
  if (perSufix) return { instancia: perSufix.slug }

  const capa = [...(dicc.capes || [])].sort(perOrdre)
    .find(f => f.slug.toLowerCase().startsWith(c) && f.slug !== dicc.regles?.capa_defecte)
  if (capa) return { capa: capa.slug }

  const inst = [...totes].sort(perOrdre).find(f => f.slug.toLowerCase().startsWith(c))
  if (inst) return { instancia: inst.slug }
  return null
}

// El 4t nivell, 'model', és per als POMs nascuts d'aquest client des d'un model (àlies amb
// `origen='MODEL'`). Va l'últim perquè la proximitat mana: primer el que l'item ja declara.
// ── CREAR POM PROPI DEL MODEL ────────────────────────────────────────────────────────────────
//
// La llei diu que els POMs es van a buscar al catàleg del client i que no s'encunyen codis
// lliures. Però un model pot necessitar una mesura que el catàleg encara no té —«Height sequins
// piece», el cas real del MILEY— i, sense una porta explícita, aquella necessitat se'n va per on
// pot: l'import agafava el codi del document tal qual i creava un POM orfe. Així va néixer el
// POM 440 amb `codi_client='U1'` quan Brownie ja tenia `U1 → Button spacing`.
//
// Per això aquí NO hi ha cap «crear "{query}"» que es fabriqui el codi del text cercat. Hi ha un
// formulari que demana les dues coses per separat —el NOM, que és lliure, i la NOMENCLATURA, que
// és un codi— i que deixa que el backend digui si el codi ja significa una altra cosa. El 409 no
// es tradueix: el missatge del servidor porta AMB QUÈ xoca, que és l'única cosa útil.
function ModalPomPropi({ modelId, nomInicial, onFet, onTanca }) {
  const { t } = useTranslation()
  const [nom, setNom] = useState(nomInicial || '')
  const [codi, setCodi] = useState('')
  const [err, setErr] = useState('')
  const [desant, setDesant] = useState(false)

  const desa = () => {
    if (!nom.trim() || !codi.trim() || desant) return
    setDesant(true); setErr('')
    poms.crearPropiDelModel(modelId, { nom: nom.trim(), nomenclatura: codi.trim() })
      .then(r => { onFet(r.data) })
      .catch(e => setErr(e?.response?.data?.message || e?.response?.data?.error
                         || t('editable_table.pom_propi_err')))
      .finally(() => setDesant(false))
  }

  const camp = (etiqueta, valor, set, ajuda, autoFocus) => (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ fontSize: FS_HEAD, textTransform: 'uppercase', letterSpacing: '0.05em',
                     color: 'var(--text-muted)' }}>{etiqueta}</span>
      <input value={valor} autoFocus={autoFocus}
        onChange={e => { set(e.target.value); setErr('') }}
        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); desa() } }}
        style={{ font: 'inherit', fontSize: FS_VAL, padding: '6px 10px', borderRadius: 5,
                 border: '1px solid var(--border)', background: 'var(--white)' }} />
      <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>{ajuda}</span>
    </label>
  )

  return (
    <div role="dialog" aria-modal="true" aria-label={t('editable_table.crear_pom_propi')}
      onMouseDown={e => { if (e.target === e.currentTarget) onTanca() }}
      style={{ position: 'fixed', inset: 0, zIndex: 1300, display: 'flex',
               alignItems: 'flex-start', justifyContent: 'center',
               background: 'rgba(0,0,0,0.28)', padding: '12vh 16px' }}>
      <div style={{ width: 'min(460px, 100%)', background: 'var(--white)', borderRadius: 12,
                    border: '0.5px solid var(--border)', padding: '1.1rem 1.3rem 1.3rem',
                    boxShadow: '0 12px 40px rgba(0,0,0,0.2)' }}>
        <h3 style={{ margin: '0 0 4px', fontSize: 'var(--fs-h3)', fontWeight: 500 }}>
          {t('editable_table.crear_pom_propi')}
        </h3>
        <p style={{ margin: '0 0 14px', fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
          {t('editable_table.pom_propi_intro')}
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {camp(t('editable_table.pom_propi_nom'), nom, setNom,
                t('editable_table.pom_propi_nom_hint'), true)}
          {camp(t('editable_table.pom_propi_codi'), codi, setCodi,
                t('editable_table.pom_propi_codi_hint'), false)}
        </div>
        {err && (
          <p style={{ margin: '12px 0 0', padding: '7px 10px', borderRadius: 6,
                      border: '0.5px solid var(--danger, #b3261e)',
                      color: 'var(--danger, #b3261e)', fontSize: 'var(--fs-body)' }}>{err}</p>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <button type="button" onClick={onTanca} style={btnSecondary}>{t('app.cancel')}</button>
          <button type="button" onClick={desa} disabled={!nom.trim() || !codi.trim() || desant}
            style={btnPrimary(!nom.trim() || !codi.trim() || desant)}>
            {desant ? t('common.saving') : t('app.create')}
          </button>
        </div>
      </div>
    </div>
  )
}

const NIVELLS = ['item', 'type', 'cataleg', 'model']

function CercadorPOM({ dicc, modelId, onAdd, registerFinder, onSurt, onCrearPropi }) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [sel, setSel] = useState(0)
  const [obert, setObert] = useState(false)
  // L'ACCIÓ DE CREAR TAMBÉ ÉS SELECCIÓ. Amb zero resultats el desplegable no és buit: hi ha
  // exactament UNA cosa a triar, i havia de ser amb el ratolí. `↓` la marca i `Enter` la
  // dispara, com faria amb un resultat — el ritme del carril no es trenca per canviar de mà.
  const [creaSel, setCreaSel] = useState(false)
  // Hi ha acció de crear? Mateixa condició que la que la pinta, en un sol lloc perquè el teclat
  // i el render no puguin discrepar.
  const potCrear = !!(modelId && onCrearPropi)
  const inputRef = useRef(null)

  // El text es parteix en «què busco» i «com el vull»: `C.f` → busca `C`, capa `folre`.
  const m = query.trim().match(/^(.*?)\.([a-zA-Z]{1,2})$/)
  const eixos = m ? resolSufix(dicc, m[2]) : null
  const cerca = eixos ? m[1] : query.trim()

  useEffect(() => {
    if (cerca.length < 2) { setResults([]); setObert(false); return }
    const timer = setTimeout(() => {
      poms.cerca({ q: cerca, page_size: 10, ...(modelId ? { model: modelId } : {}) })
        .then(r => {
          setResults(r.data?.results || [])
          setSel(0); setObert(true); setCreaSel(false)
        })
        .catch(() => { setResults([]); setObert(false) })
    }, 300)
    return () => clearTimeout(timer)
  }, [cerca, modelId])

  const tria = (p) => {
    if (!p) return
    onAdd(p, eixos || {})
    setQuery(''); setResults([]); setObert(false)
  }

  const perNivell = NIVELLS
    .map(n => [n, results.filter(r => (r.nivell || 'cataleg') === n)])
    .filter(([, files]) => files.length > 0)

  // P0.2b — LA LLISTA SORTIA TALLADA. Anava `position:absolute` dins del cercador, i el
  // cercador viu dins del `<div style={{overflowX:'auto'}}>` que fa scrollar la taula. Un
  // avantpassat amb overflow diferent de `visible` RETALLA els fills posicionats encara que
  // vagin amb z-index 40: no és un problema d'apilament, és de clipping, i pujar el z-index no
  // ho podia arreglar mai.
  //
  // Es porta al `body` amb un portal i es posiciona en coordenades de finestra. De passada es
  // decideix cada cop cap on s'obre: amunt si hi cap (que és el gest natural d'un cercador al
  // PEU de la taula) i avall si no —a prop del final de la finestra, obrir-se amunt deixava la
  // llista mig fora—. L'alçada màxima es retalla a l'espai real i la llista es fa scrollable
  // dins seu, que és el que la fa completa quan hi ha molts resultats.
  const posicioLlista = () => {
    const r = inputRef.current?.getBoundingClientRect()
    if (!r) return null
    const MARGE = 8
    const sobre = r.top - MARGE
    const sota = window.innerHeight - r.bottom - MARGE
    const amunt = sobre >= Math.min(290, sota) || sobre >= 180
    return {
      left: r.left,
      maxHeight: Math.max(120, Math.min(290, amunt ? sobre : sota)),
      ...(amunt ? { bottom: window.innerHeight - r.top + 4 } : { top: r.bottom + 4 }),
    }
  }
  // Es recalcula mentre és oberta: la finestra es pot redimensionar i la pàgina scrollar sota
  // una llista que ja no seria on toca. `capture` per enxampar també el scroll del contenidor
  // de la taula, que no bombolla.
  const [pos, setPos] = useState(null)
  useEffect(() => {
    if (!obert) { setPos(null); return undefined }
    const recalcula = () => setPos(posicioLlista())
    recalcula()
    window.addEventListener('resize', recalcula)
    window.addEventListener('scroll', recalcula, true)
    return () => {
      window.removeEventListener('resize', recalcula)
      window.removeEventListener('scroll', recalcula, true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [obert, results.length])

  return (
    <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 10 }}>
      <input
        ref={el => { inputRef.current = el; registerFinder?.(el) }}
        value={query} onChange={e => setQuery(e.target.value)}
        placeholder={t('editable_table.finder_ph')}
        onKeyDown={e => {
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            if (results.length) setSel(s => Math.min(s + 1, results.length - 1))
            else if (potCrear) setCreaSel(true)
          } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            // A dalt de tot de la llista (o sense llista) la fletxa TORNA AL CARRIL: el cercador
            // és el final del recorregut, no un cul-de-sac.
            if (creaSel) setCreaSel(false)
            else if (sel === 0 || !obert) { setObert(false); onSurt?.() } else setSel(s => s - 1)
          } else if (e.key === 'Enter') {
            e.preventDefault()
            // Sense resultats, Enter dispara l'ÚNICA cosa que hi ha. No cal haver premut `↓`
            // abans: exigir-ho seria demanar un pas per a una llista d'un sol element.
            if (!results.length && potCrear) { onCrearPropi(cerca); setObert(false); setCreaSel(false) }
            else tria(results[sel])
          } else if (e.key === 'Escape') {
            e.preventDefault(); setQuery(''); setObert(false); onSurt?.()
          }
        }}
        style={{
          font: 'inherit', fontSize: FS_VAL, color: 'var(--text-main)', width: 320,
          border: '1px solid var(--gold)', borderRadius: 5, padding: '6px 10px',
          background: 'var(--white)', boxSizing: 'border-box',
        }} />
      <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
        {eixos
          ? t('editable_table.finder_eix', {
            eix: eixos.capa ? etiquetaCapa(eixos.capa, t) : etiquetaInstancia(eixos.instancia, t),
          })
          : t('editable_table.finder_hint')}
      </span>

      {obert && pos && createPortal(
        <div style={{
          position: 'fixed', left: pos.left, top: pos.top, bottom: pos.bottom, zIndex: 1200,
          background: 'var(--white)', border: '1px solid var(--border)', borderRadius: 7,
          boxShadow: '0 -8px 24px rgba(0,0,0,0.12)', minWidth: 410,
          maxHeight: pos.maxHeight, overflowY: 'auto',
        }}>
          {perNivell.map(([nivell, files]) => (
            <div key={nivell}>
              <div style={{ fontSize: 'var(--fs-caption)', textTransform: 'uppercase',
                            letterSpacing: '0.06em', color: 'var(--text-muted)',
                            padding: '7px 12px 3px', borderTop: '1px solid var(--border)' }}>
                {t(`editable_table.finder_nivell_${nivell}`)}
              </div>
              {files.map(p => {
                const k = results.indexOf(p)
                return (
                  <div key={p.id} onMouseDown={e => { e.preventDefault(); tria(p) }}
                    onMouseEnter={() => setSel(k)}
                    style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 12px',
                             cursor: 'pointer', fontSize: 'var(--fs-body)',
                             background: k === sel ? 'var(--gold-pale)' : 'transparent' }}>
                    {/* EL CODI QUE ES PINTA ÉS EL DEL CLIENT. Abans hi anava `codi_client` de
                        `POMMaster`, que es diu «client» però és el codi de la CASA: el tècnic de
                        Brownie llegia «CH» sota el rètol «del catàleg del client» quan el seu
                        document diu «A». El backend ja serveix els tres camps d'àlies. */}
                    <span style={{ color: 'var(--gold)', fontWeight: 600, minWidth: 56 }}>
                      {p.client_code || p.codi_client}
                    </span>
                    <span>{p.client_name_en || p.nom_client || p.nom_en || p.nom_ca}</span>
                    {eixos && (
                      <span style={{ background: 'var(--gold-pale)', color: 'var(--gold)',
                                     border: '1px solid var(--border)', borderRadius: 999,
                                     padding: '1px 8px', fontSize: 'var(--fs-caption)' }}>
                        {eixos.capa ? etiquetaCapa(eixos.capa, t) : etiquetaInstancia(eixos.instancia, t)}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
          {results.length === 0 && (
            <div style={{ padding: '8px 12px', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
              {t('editable_table.no_pom_found', { query: cerca })}
            </div>
          )}
          {/* CAP RESULTAT NO VOL DIR CAP CAMÍ PER ENCUNYAR UN CODI (Agus, 06/08). El que hi ha
              aquí és un gest EXPLÍCIT que demana nom i nomenclatura i els valida contra el
              catàleg del client — no un «crear "{query}"» que es fabriqui el codi del text
              cercat, que és exactament com va néixer el POM 440 amb el codi d'un altre. */}
          {results.length === 0 && potCrear && (
            /* BOTÓ, no un `div`: és una acció, i com a botó el navegador ja li dona el rol i el
               nom accessible. `onMouseDown` amb `preventDefault` es queda perquè el `blur` de
               l'input tancaria el desplegable abans que el clic hi arribés. */
            <button type="button" aria-selected={creaSel}
              onMouseDown={e => { e.preventDefault(); onCrearPropi(cerca); setObert(false); setCreaSel(false) }}
              style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                       cursor: 'pointer', fontSize: 'var(--fs-body)', color: 'var(--gold)',
                       borderTop: '1px solid var(--border)', border: 'none', width: '100%',
                       textAlign: 'left', font: 'inherit',
                       background: creaSel ? 'var(--gold-pale)' : 'transparent' }}>
              <i className="ti ti-plus" style={{ fontSize: 14 }} aria-hidden="true" />
              {t('editable_table.crear_pom_propi')}
            </button>
          )}
        </div>,
        document.body,
      )}
    </div>
  )
}
