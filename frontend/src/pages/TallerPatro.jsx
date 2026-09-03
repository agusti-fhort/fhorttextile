import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { patterns, models, modelTasks } from '../api/endpoints'
import PatternViewer, { METRICA_EINA, METRICA_EINA_COMPACTA } from '../components/pattern/PatternViewer'
import {
  arcDirigit, longitudTram, puntsDelSegment, puntsEntreIndexs, situaPunt,
} from '../components/pattern/patternGeometry'
import PieceList from '../components/pattern/PieceList'
import PieceEdgeRoleList from '../components/pattern/PieceEdgeRoleList'
import { etiquetaPeca } from '../components/pattern/pieceText'
import ModelPomList from '../components/pattern/ModelPomList'
import RelationsPanel from '../components/pattern/RelationsPanel'
import POMPicker from '../components/pattern/POMPicker'
import SewEditor from '../components/pattern/SewEditor'
import SegmentEditor from '../components/pattern/SegmentEditor'
import Contenidor from '../components/ui/Contenidor'
import Modal from '../components/ui/Modal'
import { grauVisual, textCobertura, textEstat } from '../components/pattern/sewText'
import { formatLen } from '../utils/format'
import { useUnit } from './fittingShared'

/**
 * TALLER DE PATRÓ (W2) — el mòdul dedicat, a pantalla completa.
 *
 * Viu FORA del Shell (com l'editor de fitxa tècnica): una eina de treball no és una
 * pàgina més del menú, i el canvas ha de poder ocupar tot el que hi ha. Res de la
 * pàgina fa scroll amb el document: l'alçada la mana el viewport (100vh) i qui
 * desborda és cada contenidor per dins.
 *
 * Columna esquerra fixa, tres contenidors d'scroll INDEPENDENT: PECES · POMS DEL MODEL ·
 * RELACIONS. Anar a buscar una costura no ha de fer perdre de vista la peça que s'està
 * mirant, i per això no comparteixen barra.
 *
 * El tab Patró de la fitxa queda de PORTA (metadades, versions, upload, exportació);
 * les EINES (marcar POM, cosir) viuen aquí.
 */
export default function TallerPatro() {
  const { id } = useParams()
  const modelId = parseInt(id)
  const [sp] = useSearchParams()
  const fileParam = sp.get('file')
  const taskParam = sp.get('task_id')
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [carregant, setCarregant] = useState(true)
  const [error, setError] = useState(null)
  const [model, setModel] = useState(null)
  const [actual, setActual] = useState(null)       // el PatternFile obert
  const [geometria, setGeometria] = useState(null)
  const [sews, setSews] = useState([])
  const [feina, setFeina] = useState(null)        // la llista de treball (W3/T1)
  const [pecaSel, setPecaSel] = useState('')
  // ── A2. Les costures PROPOSADES. No es desen enlloc: es recalculen senceres a cada canvi de
  // la geometria (confirmar-ne una, esborrar una costura, marcar una pinça), perquè la cobertura
  // canvia i amb ella el que encara es pot proposar.
  const [propostes, setPropostes] = useState([])
  const [descartatsProp, setDescartatsProp] = useState(null)
  // Si algú ja ha buscat. Distingeix «encara no ho he demanat» de «ho he demanat i no n'hi ha
  // cap»: són dues coses diferents i la pantalla no les pot dir igual.
  const [cercades, setCercades] = useState(false)
  const [buscant, setBuscant] = useState(false)
  const [rebuigs, setRebuigs] = useState([])
  const [propostaRessaltada, setPropostaRessaltada] = useState(null)
  // ── A1. Les PINCES que el motor veu. Mateixa vida que les costures proposades: no es desen,
  // es recalculen, i marcar-ne una (o rebutjar-la) les refà.
  const [pincesProp, setPincesProp] = useState([])
  const [descartatsPinca, setDescartatsPinca] = useState(null)
  const [pincaPropRessaltada, setPincaPropRessaltada] = useState(null)

  // ── eines d'anotació (venen del tab: es TRASLLADEN, no es reescriuen) ─────
  // El node de la barra on el visor deixa anar els seus controls. És ESTAT i no un ref
  // perquè el portal s'ha de tornar a pintar quan el node existeix: amb un ref, el primer
  // render passaria `null` i els controls no arribarien mai.
  const [slotVisor, setSlotVisor] = useState(null)
  const [mode, setMode] = useState('view')     // 'view' | 'pom' | 'seg' | 'pinca' | 'sew'
  // Els punts clicats (imantats). El fan servir els TRES modes de punts: marcar un POM (2),
  // definir un tram (2) i marcar una pinça (3). El gest és el mateix; el que canvia és quants
  // punts són i què se'n fa.
  const [puntsPom, setPuntsPom] = useState([])
  const [pickerObert, setPickerObert] = useState(false)
  const [segmentsA, setSegmentsA] = useState([])
  const [segmentsB, setSegmentsB] = useState([])
  const [costatActiu, setCostatActiu] = useState('a')
  const [tipusSew, setTipusSew] = useState('casat')
  const [diferencial, setDiferencial] = useState(0)
  const [nomSew, setNomSew] = useState('')
  // El POM que s'està col·locant. Amb pomActiu, el canvas SAP quin POM marca i no cal cap
  // cercador: A → B → ancorat. Sense pomActiu, el mode POM és la via secundària (el POM
  // que no és a la fitxa) i llavors sí que cal preguntar quin és — el picker.
  const [pomActiu, setPomActiu] = useState(null)
  // ── El vocabulari de MÈTODES de mesura, servit pel backend (cap enum aquí). Cada entrada
  // porta la seva gramàtica: `{codi, mode, ancores}`. `ancores` és el que fa que el gest
  // sigui guiat sense que aquesta pantalla sàpiga què és una caiguda ortogonal — en diu
  // quants clics vol i com es diu cadascun, i la guia i la recepta surten d'aquí.
  const [metodes, setMetodes] = useState([])
  const [metodeSel, setMetodeSel] = useState('')
  // Les OPCIONS triades del mètode viu (`{eix: 'H'}`…). Un diccionari i no un estat per
  // opció: quines n'hi ha ho diu el servidor, i una variable per cadascuna voldria dir
  // saber-les aquí.
  const [opcionsSel, setOpcionsSel] = useState({})
  const [nomTram, setNomTram] = useState('')
  const [creantTram, setCreantTram] = useState(false)
  const [tramRessaltat, setTramRessaltat] = useState(null)
  // ── W4b/T3c. La previsualització direccional. `arcInvertit` és la bandera VIVA (l'arc que
  // el cursor està assenyalant ara); `invertits` és el que es va triar a cada arc ja fixat.
  // Van separades perquè invertir el segon costat d'una pinça no pot girar el primer, que ja
  // estava decidit.
  const [arcInvertit, setArcInvertit] = useState(false)
  const [invertits, setInvertits] = useState([])
  // ── W4b/T5. REOBRIR per editar. Amb un id posat, el gest no crea res nou: RECALCULA sobre
  // la mateixa fila. Mai esborrar-i-crear — les costures referencien els trams, i els POMs
  // porten la seva història.
  // La COTA assenyalada al canvas. És selecció de PANTALLA, no d'edició: no obre res, només
  // diu «aquesta», i és el que dona sentit a la tecla Supr.
  const [pomSel, setPomSel] = useState(null)
  // La cota que Supr ha assenyalat i que espera el vistiplau. Esborrar un ancoratge amb una
  // tecla i sense preguntar seria l'única acció destructiva del Taller sense confirmació.
  const [esborraCota, setEsborraCota] = useState(null)
  const [pomEditId, setPomEditId] = useState(null)
  const [tramEditId, setTramEditId] = useState(null)
  const [sewEditId, setSewEditId] = useState(null)
  // La recepta que s'està reobrint, dibuixada de fons: es veu D'ON es ve mentre es recol·loca.
  const [ombra, setOmbra] = useState(null)
  // El veredicte de l'última costura declarada. Surt IMMEDIAT: si la costura no casa, o si
  // trepitja la vora, saber-ho d'aquí a tres clics és saber-ho tard.
  const [veredicte, setVeredicte] = useState(null)
  const [tascaId, setTascaId] = useState(null)      // per al render: hi ha rellotge?

  // ── ROLS DE VORA (F4.2-BIS) ───────────────────────────────────────────────
  // Declarar-los és FEINA, i per això viuen aquí i no a la porta: el Taller és on el
  // rellotge corre i on hi ha zoom i pan per comprovar cada mida abans de dir-la
  // (ordre de l'Agus, 03/09: «no puc comprovar la mida si no puc navegar»).
  const [vores, setVores] = useState(null)
  const [vocabularis, setVocabularis] = useState({})
  const [voraSel, setVoraSel] = useState(null)      // segment_id assenyalat, als dos costats
  // L'ordre d'ENQUADRAR (F4.2-TER). Comptador i no id: ha de disparar-se una vegada per
  // GEST —i tornar a clicar la mateixa fila hi ha de tornar—, mai per passada del cursor
  // ni per re-render.
  const [enquadra, setEnquadra] = useState(null)   // { id, n }
  const enquadraTram = useCallback((id) => {
    setEnquadra(e => ({ id, n: (e?.n || 0) + 1 }))
  }, [])
  const [desantVores, setDesantVores] = useState(false)
  const [errorVores, setErrorVores] = useState('')
  const [errTasca, setErrTasca] = useState(null)
  const unit = useUnit()                            // CM | INCH — la llei d'unitat del tenant
  // L'error d'una EINA (no s'ha pogut ancorar, no s'ha pogut cosir) no és l'error de
  // càrrega: aquell deixa la pàgina sense patró, aquest només ha fet fallar una acció.
  const [errEina, setErrEina] = useState(null)

  // El patró de tasca EXACTE del tab (PatternTab:54-64), traslladat. El ref és d'UN SOL
  // ÚS perquè un segon Paused→Paused rebotaria amb un 400 (ALLOWED no el contempla).
  // La diferència amb el tab: la tasca ja no s'obre en entrar al MODE d'anotació, sinó en
  // entrar al TALLER, i es pausa en sortir-ne. Obrir el taller ÉS posar-se a treballar.
  const activeTaskRef = useRef(null)
  const pauseActiveTask = useCallback(() => {
    const tid = activeTaskRef.current
    if (tid == null) return
    activeTaskRef.current = null
    modelTasks.transition(tid, { to_status: 'Paused' }).catch(() => {})
  }, [])

  // El taller s'obre SEMPRE sobre un fitxer concret. Si no ve per `?file=`, s'agafa el
  // vigent del model: entrar-hi sense fitxer és un accident de navegació, no una
  // instrucció d'obrir el taller buit.
  const carregar = useCallback(async () => {
    setCarregant(true)
    try {
      const [{ data: m }, { data: llista }] = await Promise.all([
        models.get(modelId),
        patterns.list(modelId),
      ])
      setModel(m)

      const files = llista.results || llista || []
      const triat = (fileParam && files.find(f => f.id === parseInt(fileParam)))
        || files.find(f => f.is_current)
        || files[0]
      if (!triat) { setActual(null); return }

      // Les PROPOSTES no entren aquí (F/T1): el Taller s'obre amb el grup buit i un botó.
      // A2 no és una lectura, és un motor que opina sobre tot el patró — i córrer-lo sol, en
      // obrir, feia que la llista aparegués sense que ningú l'hagués demanada.
      const [{ data: detall }, { data: geo }, { data: sw }, { data: fn }, { data: pp }] =
        await Promise.all([
          patterns.get(triat.id),
          patterns.geometry(triat.id),
          patterns.sew.list(modelId),
          patterns.modelPoms(triat.id),
          patterns.sew.pincesProposades(modelId, triat.id),
        ])
      setActual(detall)
      setGeometria(geo)
      setSews(sw.results || sw || [])
      setFeina(fn)
      setPincesProp(pp.candidats || [])
      setDescartatsPinca(pp.descartats || null)
    } catch {
      setError(t('pattern.err_load'))
    } finally {
      setCarregant(false)
    }
  }, [modelId, fileParam, t])

  useEffect(() => { carregar() }, [carregar])

  // ── ROLS DE VORA · lectura i gest ─────────────────────────────────────────
  /** Els trams amb la proposta, i el vocabulari per rol de peça. Una crida per pantalla. */
  const carregarVores = useCallback(async (fpId) => {
    if (!fpId) { setVores(null); return }
    try {
      const { data } = await patterns.edgeRoles(fpId)
      setVores(data.results || [])
      // Un cop per ROL DE PEÇA i no per peça: dues peces del mateix rol tenen el mateix
      // vocabulari, i demanar-lo cinc vegades seria cinc voltes per la mateixa resposta.
      const rols = [...new Set((data.results || []).map(f => f.piece_role).filter(Boolean))]
      const parells = await Promise.all(rols.map(async r => {
        try {
          const { data: v } = await patterns.edgeVocabulary(fpId, r)
          return [r, v || []]
        } catch { return [r, []] }
      }))
      setVocabularis(Object.fromEntries(parells))
    } catch {
      setVores([])
    }
  }, [])

  useEffect(() => { carregarVores(actual?.id) }, [actual, carregarVores])

  /** El gest humà. Refresca, perquè els landmarks derivats en depenen. */
  const confirmarVores = useCallback(async (pieceId, trams) => {
    setErrorVores('')
    setDesantVores(true)
    try {
      await patterns.confirmarVores(actual.id, { piece_id: pieceId, trams })
      await carregarVores(actual.id)
    } catch (e) {
      setErrorVores(e?.response?.data?.error || t('pattern.edges_err'))
    } finally {
      setDesantVores(false)
    }
  }, [actual, carregarVores, t])

  /**
   * Els trams amb rol per PINTAR, resolts sobre la geometria que ja tenim.
   *
   * 🚨 El front no CALCULA geometria: la RESOL. Un `PatternSegment` es desa com a fracció
   * de vora precisament perquè es pugui ancorar sense clavar-lo a un índex de vèrtex, i
   * `puntsDelSegment` és la mateixa funció amb què el Taller pinta els trams declarats des
   * de S6. Demanar al servidor una polilínia que aquí es dedueix del que ja ha enviat seria
   * una segona font per a la mateixa veritat.
   */
  const voresAlCanvas = useMemo(() => {
    if (!vores || !geometria) return []
    const segsPerId = new Map()
    for (const p of geometria.pieces || []) {
      for (const sg of p.segments || []) segsPerId.set(sg.id, { ...sg, piece_id: p.id })
    }
    return vores.flatMap(f => {
      // NOMÉS la peça que s'està mirant. Pintar els setze trams de cada peça alhora
      // tornaria el patró sencer un garbuix de colors, que és el contrari del que aquesta
      // pantalla ve a fer.
      if (!pecaSel || f.nom_block !== pecaSel || !f.piece_role) return []
      return f.proposals.flatMap(pr => {
        const sg = segsPerId.get(pr.segment_id)
        if (!sg) return []
        const g = pr.evidence?.geometry || {}
        return [{
          ...sg,
          id: pr.segment_id,
          edge_role: f.confirmed?.[pr.segment_id] || pr.edge_role,
          confirmat: !!f.confirmed?.[pr.segment_id],
          longitud_cm: g.length_mm != null ? g.length_mm / 10 : null,
        }]
      })
    })
  }, [vores, geometria, pecaSel])

  /**
   * Els «no» vius d'aquest model. És una consulta a una taula, no el motor: es pot llegir sol.
   *
   * Viu AQUÍ dalt, i no al costat de `desferRebuig`, perquè el seu efecte la porta a les
   * dependències i les dependències s'avaluen DURANT el render: declarada més avall, el render
   * petava sencer contra la seva pròpia zona morta abans que ningú la cridés.
   */
  const llegirRebuigs = useCallback(async () => {
    try {
      const { data } = await patterns.sewRejections.list(modelId)
      setRebuigs(data.results || data || [])
    } catch { /* la llista de rebuigs no és crítica: si no ve, no es diu res */ }
  }, [modelId])

  // El vocabulari de mètodes: una sola lectura en obrir el taller. Si no ve (xarxa, permís),
  // la pantalla es queda sense selector i el gest segueix sent el de dos punts de sempre —
  // ni un mètode inventat aquí ni una eina que no es pot fer servir.
  useEffect(() => {
    let viu = true
    patterns.poms.metodes()
      .then(({ data }) => {
        if (!viu) return
        const llista = data || []
        setMetodes(llista)
        setMetodeSel(prev => prev || llista[0]?.codi || '')
      })
      .catch(() => { /* sense vocabulari, el Taller no ofereix el selector i prou */ })
    return () => { viu = false }
  }, [])

  // Els REBUIGS sí que es llegeixen en obrir (F/T3): és una consulta a una taula, no el motor.
  // El que T1 treu de l'arrencada és A2, que opina sobre tot el patró — no saber quants «no»
  // hi ha vius és el que fa que un recompte de zero propostes menteixi.
  useEffect(() => { llegirRebuigs() }, [llegirRebuigs])

  // ── el rellotge ──────────────────────────────────────────────────────────
  // Entrar al taller obre la tasca; sortir-ne la pausa. Arribar amb `?task_id=` (des del
  // pla de treball o de l'arbre de tasques) REPRÈN aquella tasca en lloc d'encunyar-ne una
  // de nova: qui hi navega ja l'ha deixada En curs, i tornar-la a obrir seria demanar una
  // transició que no cal.
  const tascaEncetada = useRef(false)
  useEffect(() => {
    if (tascaEncetada.current) return
    tascaEncetada.current = true

    if (taskParam) {
      const tid = parseInt(taskParam)
      activeTaskRef.current = tid
      setTascaId(tid)
      return
    }
    models.openTask(modelId, 'pattern_digit')
      .then(res => {
        activeTaskRef.current = res.data.task_id
        setTascaId(res.data.task_id)
      })
      .catch(e => {
        // 403 task_type_not_allowed: l'allow-list del perfil (UserProfile.permisos.tasks)
        // no inclou pattern_digit. És DADA, no codi, i el missatge ho ha de dir clar: qui
        // ho llegeixi ha de saber què demanar i a qui. El patró es pot MIRAR igualment;
        // el que no es pot és anotar-lo sense rellotge.
        setErrTasca(e.response?.data?.code === 'task_type_not_allowed'
          ? t('pattern.err_task_not_allowed')
          : t('pattern.err_task'))
      })
  }, [modelId, taskParam, t])

  // Sortir del taller pausa la tasca, per la porta que sigui: el botó de tornar, el botó
  // enrere del navegador o tancar-ho tot. El rellotge no es queda corrent sol.
  useEffect(() => () => { pauseActiveTask() }, [pauseActiveTask])

  // ── eines ────────────────────────────────────────────────────────────────
  const netejarSeleccio = useCallback(() => {
    setPuntsPom([])
    setPickerObert(false)
    setPomActiu(null)
    setSegmentsA([])
    setSegmentsB([])
    setCostatActiu('a')
    setNomTram('')
    setNomSew('')
    setArcInvertit(false)
    setInvertits([])
    setPomEditId(null)
    setTramEditId(null)
    setSewEditId(null)
    setOmbra(null)
  }, [])

  const triarMode = (nou) => {
    netejarSeleccio()
    setMode(m => {
      const seguent = m === nou ? 'view' : nou
      // «Tram 3» és un nom pobre, però un camp buit és pitjor: el suggeriment es pot
      // esborrar, i qui té pressa no es queda sense poder desar.
      if (seguent === 'seg') {
        setNomTram(t('pattern.taller.segment_default', { n: trams.length + 1 }))
      }
      if (seguent === 'pinca') {
        setNomTram(t('pattern.taller.pinca_default', { n: pinces.length + 1 }))
      }
      return seguent
    })
  }

  // El mètode viu i la seva gramàtica. Amb el vocabulari encara no arribat (o caigut), es
  // cau al gest de sempre: dos punts. No és un enum escrit aquí —és el mínim que la pantalla
  // sap fer sense servidor— i el selector no s'ofereix fins que el vocabulari hi és.
  const metodeActiu = useMemo(
    () => metodes.find(m => m.codi === metodeSel) || null,
    [metodes, metodeSel])
  const ancoresPom = metodeActiu?.ancores || ['a', 'b']
  // `useMemo` i no un `||` pelat: entra a les dependències de `valorOpcio`, i un objecte
  // literal nou a cada render li canviaria la identitat sempre.
  const opcionsPom = useMemo(() => metodeActiu?.opcions || {}, [metodeActiu])

  /** El valor triat d'una opció, o el primer que el vocabulari en dona (que és el defecte). */
  const valorOpcio = useCallback(
    (nom) => opcionsSel[nom] ?? (opcionsPom[nom]?.[0] ?? ''),
    [opcionsSel, opcionsPom])

  // Clicar una fila PENDENT de la llista de treball ÉS l'ordre de col·locar aquell POM:
  // no obre cap cercador, perquè ja se sap quin POM és. El canvas passa a guiar.
  const colocarPOM = (fila) => {
    setPomActiu(fila)
    setPuntsPom([])
    setPickerObert(false)
    // El mètode NO s'arrossega d'un POM al següent: haver mesurat una caiguda no vol dir que
    // la mesura següent en sigui una, i heretar-lo en silenci faria que el canvas demanés
    // tres clics per a una amplada. Es torna al primer del vocabulari, que és el per defecte
    // del model.
    setMetodeSel(metodes[0]?.codi || '')
    setOpcionsSel({})
    setMode('pom')
  }

  // La via secundària: un POM que NO és a la fitxa. Aquí sí que cal preguntar quin és, i
  // per això aquest camí (i només aquest) acaba al picker del catàleg.
  const afegirPOMForaDeFitxa = () => {
    setPomActiu(null)
    setPuntsPom([])
    setMode('pom')
  }

  // Esc surt de la col·locació sense deixar res penjat: ni punts a mig clicar, ni un POM
  // actiu que ja no s'està col·locant, ni el picker obert. (D7)
  const cancelar = useCallback(() => {
    netejarSeleccio()
    setMode('view')
  }, [netejarSeleccio])

  const veredicteVist = () => setVeredicte(null)

  // ⚠️ AQUESTS DOS VIUEN AQUÍ DALT, i pel mateix motiu que `llegirRebuigs` (v. la seva
  // capçalera): `pomSelViu` entra a les dependències de l'efecte de teclat de sota, i les
  // dependències s'avaluen DURANT el render. Declarats més avall, el render peta sencer
  // contra la seva pròpia zona morta.
  //
  // Els POMs ancorats viuen a la geometria, penjats de la peça que mesuren. (El creuament
  // amb la fitxa no es fa aquí: el fa el servidor, a `model-poms`. Fer-lo dues vegades i de
  // dues maneres seria demanar que divergissin.)
  const pomsAncorats = useMemo(() => (geometria?.pieces || []).flatMap(p =>
    (p.poms || []).map(x => ({ ...x, peca: etiquetaPeca(p) }))), [geometria])

  // I la cota assenyalada ha d'EXISTIR. Es comprova DERIVANT-HO i no netejant l'estat amb un
  // efecte: si el POM desapareix —esborrat des d'una altra pestanya, o una versió nova del
  // patró—, l'id mort deixa de pintar-se i Supr no hi arriba. Un efecte que fes
  // `setPomSel(null)` faria el mateix amb un render de més i una cascada pel mig.
  const pomSelViu = useMemo(
    () => (pomsAncorats.some(p => p.id === pomSel) ? pomSel : null),
    [pomsAncorats, pomSel])

  // Esc surt. La tecla d'INVERTIR (←/→/F) gira l'arc que s'està previsualitzant, abans de
  // fixar-lo: dos punts d'una vora tancada defineixen dos camins, i el que el cursor no digui
  // ho ha de poder dir el teclat. I Supr esborra la cota assenyalada. Tot tres, només mentre
  // toca — una tecla que no fa res quan no toca ensenya a no fer-ne cas.
  //
  // 🚨 **EL GUARD DE `e.target`, QUE FALTAVA.** Aquest listener és GLOBAL, i sense mirar d'on
  // ve la tecla, escriure una «f» al nom d'un tram girava l'arc que s'estava previsualitzant
  // — el bug conegut de la tecla F. La malaltia no és de la F: és del listener, i per això la
  // porta es posa una sola vegada i val per a les tres tecles. Supr hi entrava de cap: el
  // Taller té camps de text oberts (nom de tram, nom de costura) i esborrar caràcters hi
  // hauria esborrat cotes.
  //
  // Escape en queda FORA a posta: cancel·lar el gest des d'un camp de text és el que la
  // pantalla anuncia («Esc per sortir») i el que qualsevol espera.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        // Amb la confirmació d'esborrat oberta, Escape és SEVA. Sense això, desdir-se'n
        // deixava el modal obert i, de propina, avortava la col·locació que hi havia a sota.
        if (esborraCota != null) { setEsborraCota(null); return }
        cancelar()
        return
      }
      if (esCampDeText(e.target)) return

      if ((e.key === 'Delete' || e.key === 'Backspace') && pomSelViu != null) {
        e.preventDefault()
        setEsborraCota(pomSelViu)
        return
      }

      const potInvertir = (mode === 'seg' || mode === 'pinca') && puntsPom.length > 0
      if (!potInvertir) return
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key.toLowerCase() === 'f') {
        e.preventDefault()
        setArcInvertit(v => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [cancelar, mode, puntsPom, pomSelViu, esborraCota])

  const onClicPunt = (iman) => {
    const punt = iman.punt
    // Quants clics vol aquest gest. En mode POM ho diu el MÈTODE (dos per a una recta o una
    // longitud per vora, tres per a una caiguda ortogonal), i ho diu el servidor: si un dia
    // n'entra un de quatre àncores, aquesta línia ja el guia.
    const maxPunts = mode === 'pinca' ? 3 : mode === 'pom' ? ancoresPom.length : 2
    // Forma FUNCIONAL a posta: llegir `puntsPom` del closure el faria servir el valor
    // d'abans del clic anterior si dos events arriben junts, i la mesura acabaria unint
    // un punt amb ell mateix.
    setPuntsPom(prev => {
      // Clicar dues vegades el MATEIX punt no és una mesura: és un zero. El segon clic
      // sobre el punt ja triat el DESTRIA, que és el que espera qui s'ha equivocat.
      if (prev.length && prev[prev.length - 1].id === punt.id) {
        setInvertits(inv => inv.slice(0, prev.length - 1))
        return prev.slice(0, -1)
      }
      if (prev.length >= maxPunts) return prev

      // L'arc que acaba en aquest punt queda fixat amb la bandera d'ARA. La següent comença
      // neta: invertir un costat no és una preferència que s'arrossegui a la resta del gest.
      if (prev.length >= 1) setInvertits(inv => [...inv.slice(0, prev.length - 1), arcInvertit])
      setArcInvertit(false)

      const nous = [...prev, punt]
      if (nous.length === maxPunts && mode === 'pom') {
        // Totes les àncores posades. Si sabem de quin POM es tracta —perquè s'està col·locant
        // de la llista de treball, o perquè s'està REOBRINT un d'ancorat— s'ancora i s'acaba.
        // Si no (via secundària: un POM que no és a la fitxa), llavors sí que cal preguntar
        // quin és.
        const master = pomActiu?.pom_master ?? ombra?.pomMaster
        if (master) ancorar(master, nous)
        else setPickerObert(true)
      }
      // En mode TRAM i PINÇA no es crea res encara: falta el nom, i el vistiplau.
      return nous
    })
  }

  /**
   * Arrossegar una cota: desa ON SEU, mai QUANT MESURA.
   *
   * El canvas s'actualitza abans que el servidor respongui —una cota que torna al seu lloc i
   * hi salta mig segon després no s'assembla a arrossegar res— i, si el desat falla, la
   * geometria es rellegeix sencera: val més que la cota reculi que no que la pantalla digui
   * una posició que la BD no té.
   */
  const mouCota = async (pom, offset) => {
    setGeometria(g => (g ? {
      ...g,
      pieces: (g.pieces || []).map(pc => ({
        ...pc,
        poms: (pc.poms || []).map(
          q => (q.id === pom.id ? { ...q, cota_offset_mm: offset } : q)),
      })),
    } : g))
    try {
      await patterns.poms.update(pom.id, { cota_offset_mm: offset })
    } catch {
      setErrEina(t('pattern.taller.err_cota_moure'))
      try {
        const { data: geo } = await patterns.geometry(actual.id)
        setGeometria(geo)
      } catch { /* si tampoc es pot rellegir, l'error d'eina ja ho ha dit */ }
    }
  }

  /** L'ancoratge, un de sol per a tots els camins: el guiat, el del picker, i el de REOBRIR. */
  const ancorar = async (pomMasterId, punts) => {
    const peca = pecaDelPunt(punts[0])
    setPickerObert(false)
    try {
      // S'envia la RECEPTA, mai el valor: el valor el llegeix el servidor de la geometria.
      // La forma de la recepta la dicta el MÈTODE, i el mètode ve del servidor: aquí no hi
      // ha cap `{mode: 'points', a, b}` escrit a mà que el dia que entri un mètode nou es
      // quedi enrere sense que ningú ho vegi.
      const recepta = { mode: metodeActiu?.mode || 'points' }
      ancoresPom.forEach((clau, i) => { recepta[clau] = punts[i].id })
      // I les opcions del mètode, si en té. Van a la recepta i no a un camp propi perquè
      // formen part del QUÈ es mesura: l'eix d'una cota no és una preferència de dibuix, és
      // la meitat de la pregunta.
      Object.keys(opcionsPom).forEach(nom => { recepta[nom] = valorOpcio(nom) })

      if (pomEditId) {
        // REOBERT (T5a): es RECALCULA sobre el MATEIX PatternPOM. Esborrar-lo i crear-ne un
        // altre li canviaria l'id i li esborraria la data —i qualsevol cosa que un dia hi
        // pengi—, per una feina que és una correcció, no un ancoratge nou.
        //
        // El `metode` hi viatja NOMÉS si se sap quin és. Amb el vocabulari caigut no hi ha
        // mètode viu, i enviar-hi el recanvi ('recta') CONVERTIRIA en silenci el POM que
        // s'està corregint —una caiguda o una longitud per vora passarien a recta sense que
        // ningú ho digués. Omès, el servidor conserva el que ja hi ha desat, que és el que
        // feia aquesta crida abans que hi hagués mètodes per triar.
        const cos = { definicio_mesura: recepta }
        if (metodeActiu) cos.metode = metodeActiu.codi
        await patterns.poms.update(pomEditId, cos)
      } else {
        // En crear, en canvi, no hi ha res a conservar: sense vocabulari s'ancora amb el
        // mètode per defecte del model, que és el que la pantalla acaba de guiar.
        await patterns.poms.create({
          pattern_piece: peca.id,
          pom_master: pomMasterId,
          definicio_mesura: recepta,
          metode: metodeActiu?.codi || 'recta',
        })
      }
      // Feina feta: la fila passa a col·locada i el canvas deixa de guiar. Qui vulgui
      // col·locar-ne un altre, el clica a la llista — que és d'on surt la feina.
      netejarSeleccio()
      setMode('view')
      await recarregarRelacions()
    } catch (e) {
      setErrEina(e.response?.data?.non_field_errors?.[0]
        ? t('pattern.err_pom_duplicate')
        : t('pattern.err_pom'))
      setPuntsPom([])
    }
  }

  // Cosir tria NOMÉS trams DECLARATS: ni del canvas ni de la llista es pot agafar una
  // proposta del motor. Un tram 'auto' és una hipòtesi de lectura del CAD; una costura és
  // una afirmació sobre la peça, i no es fa una afirmació amb una hipòtesi.
  //
  // El costat actiu AVANÇA A→B tot sol després del primer tram (QA-TALLER G · T1). El gest
  // natural —clicar els dos trams d'una màniga seguits— els repartia tots dos a A perquè res
  // no movia el focus, i el botó no s'activava mai. Ara el primer clic omple A i passa el
  // focus a B; el segon cau a B. Cosir mateixa peça és legítim (una màniga es cus sobre si
  // mateixa): la restricció «B tancat a la peça de l'A» és dels POMs, no d'aquí.
  //
  // Només avança en el PRIMER tram, i només si tot dos costats eren buits: un costat pot
  // tenir MÉS d'un tram (una sisa = davanter + esquena), i avançar a cada clic ho faria
  // impossible. Per afegir-ne més a A, es torna a triar el xip A a mà.
  const triarTram = (tram) => {
    const esA = costatActiu === 'a'
    const llista = esA ? segmentsA : segmentsB
    const set = esA ? setSegmentsA : setSegmentsB
    const treu = llista.includes(tram.id)
    set(treu ? llista.filter(x => x !== tram.id) : [...llista, tram.id])
    if (!treu && esA && segmentsA.length === 0 && segmentsB.length === 0) {
      setCostatActiu('b')
    }
  }

  const declararCostura = async () => {
    try {
      const cos = {
        model: modelId,
        segments_a: segmentsA,
        segments_b: segmentsB,
        tipus: tipusSew,
        diferencial_cm: parseFloat(diferencial) || 0,
        nom: nomSew.trim(),
      }
      // REOBERTA (T5c): la mateixa costura, amb la composició nova. No se n'encunya una altra
      // —perdria la data i l'autor per un canvi de tipus.
      const { data } = sewEditId
        ? await patterns.sew.update(sewEditId, cos)
        : await patterns.sew.create(cos)
      // La resposta ja porta l'estat calculat sobre la geometria viva (casa/no casa) i els
      // avisos de cobertura de la vora. La costura es crea IGUALMENT —l'avís informa, no
      // bloqueja: el patronista mana— però es diu de seguida i amb les xifres. Un avís que
      // s'ha d'anar a buscar és un avís que no s'ha donat.
      const e = data.estat || {}
      setVeredicte({
        casa: !!e.casa, grau: e.grau,
        estat: textEstat(t, e, unit),
        missatge: e.missatge || '',
        cobertura: (e.cobertura || []).map(a => ({
          text: textCobertura(t, a, unit), missatge: a.missatge || '',
        })),
      })
      netejarSeleccio()
      setMode('view')
      await recarregarRelacions()
    } catch {
      setErrEina(t('pattern.err_sew'))
    }
  }

  // Després de tocar una relació es rellegeix TOT el que en depèn: esborrar una costura
  // canvia la cobertura de les altres i allibera els seus trams. Rellegir només el que
  // s'ha tocat deixaria la resta mentint a la pantalla.
  const recarregarRelacions = useCallback(async () => {
    if (!actual) return
    // Les PROPOSTES ja NO entren aquí (F/T1). Abans sí, amb una raó bona: confirmar-ne una o
    // esborrar una costura canvia la cobertura, i la llista vella deixava d'estar certa. Però
    // el remei era pitjor —cada acció recalculava A2 i la llista es reomplia sola d'amagat, i
    // rebutjar-ne una en feia aparèixer de noves (els trams alliberats)—, i una llista que es
    // mou quan no l'has tocada no es pot revisar.
    //
    // Ara qui la refà és qui la mira: «Buscar propostes». El preu és que la llista pot quedar
    // VELLA respecte de la geometria, i es paga a posta: val més una llista que no es mou que
    // una que es mou sola. Confirmar-ne una la treu de la llista (allà on es confirma), que és
    // l'única part que la persona ja sap segur.
    const [{ data: geo }, { data: sw }, { data: fn }, { data: pp }] =
      await Promise.all([
        patterns.geometry(actual.id),
        patterns.sew.list(modelId),
        patterns.modelPoms(actual.id),
        patterns.sew.pincesProposades(modelId, actual.id),
      ])
    setGeometria(geo)
    setSews(sw.results || sw || [])
    setFeina(fn)
    setPincesProp(pp.candidats || [])
    setDescartatsPinca(pp.descartats || null)
  }, [actual, modelId])

  /**
   * BUSCAR PROPOSTES (F/T1) — l'única porta per la qual la llista es reomple.
   *
   * A2 corre quan algú ho demana, i prou. Respecta els rebuigs persistents (els aplica el
   * servidor) i no toca res del patró: proposar és una opinió, no un canvi.
   */
  const buscarPropostes = async () => {
    if (!actual) return
    setBuscant(true)
    try {
      const { data } = await patterns.sew.propostes(modelId, actual.id)
      setPropostes(data.propostes || [])
      setDescartatsProp(data.descartats || null)
      setCercades(true)
    } catch {
      setErrEina(t('pattern.taller.err_proposals_search'))
    } finally {
      setBuscant(false)
    }
  }

  // ── A1: confirmar i rebutjar una PINÇA proposada ─────────────────────────

  /**
   * Confirmar una pinça proposada: **el gest de W4b, pel mateix camí de codi.**
   *
   * No hi ha cap endpoint de confirmació: es crida `pinca()` amb els tres punts que el candidat
   * ja porta, exactament com si algú els hagués clicat al canvas. Un segon camí per a la mateixa
   * cosa hauria estat un lloc més on la llei de la pinça podria divergir — i el dia que W4b
   * canviés, l'assistit es quedaria enrere sense que cap test ho digués.
   */
  const confirmarPinca = async (c) => {
    setPincaPropRessaltada(null)
    const nom = t('pattern.taller.pinca_default', { n: pinces.length + 1 })
    try {
      const { data } = await patterns.sew.pinca({
        model: modelId,
        point_a: c.point_a, point_vertex: c.point_vertex, point_b: c.point_b,
        nom,
        nom_a: t('pattern.taller.pinca_side_a', { nom }),
        nom_b: t('pattern.taller.pinca_side_b', { nom }),
      })
      const e = data.estat || {}
      setVeredicte({
        casa: !!e.casa, grau: e.grau,
        estat: textEstat(t, e, unit),
        missatge: e.missatge || '',
        cobertura: (e.cobertura || []).map(a => ({
          text: textCobertura(t, a, unit), missatge: a.missatge || '',
        })),
      })
      await recarregarRelacions()
    } catch {
      setErrEina(t('pattern.taller.err_pinca'))
    }
  }

  const rebutjarPinca = async (c) => {
    setPincaPropRessaltada(null)
    try {
      await patterns.sew.rebutjarPinca({
        model: modelId,
        point_a: c.point_a, point_vertex: c.point_vertex, point_b: c.point_b,
      })
      await recarregarRelacions()
    } catch {
      setErrEina(t('pattern.taller.err_proposal_reject'))
    }
  }

  // ── A2: confirmar i rebutjar ─────────────────────────────────────────────

  /**
   * Confirmar una proposta: el gest manual, fet en un clic.
   *
   * Els NOMS dels dos trams surten d'aquí i no del servidor perquè aquí és on hi ha els tres
   * idiomes (i18n-gate). El nom de la COSTURA es deixa buit a posta: buit vol dir «genera'l dels
   * trams que uneix» (`nomCostura`), i un nom generat es refà sol el dia que algú reanomeni un
   * tram — un de congelat, no.
   */
  const confirmarProposta = async (p) => {
    setPropostaRessaltada(null)
    try {
      const { data } = await patterns.sew.confirmarProposta({
        model: modelId,
        segment_a: p.a.segment_id,
        segment_b: p.b.segment_id,
        tipus: p.tipus,
        diferencial_cm: p.diferencial_cm,
        nom_a: nomTramProposat(p.a),
        nom_b: nomTramProposat(p.b),
      })
      // La costura acabada de néixer diu de seguida com ha quedat, igual que quan es declara a
      // mà: el veredicte que la proposta PREDEIA, ara constatat sobre la costura de veritat.
      const e = data.estat || {}
      setVeredicte({
        casa: !!e.casa, grau: e.grau,
        estat: textEstat(t, e, unit),
        missatge: e.missatge || '',
        cobertura: (e.cobertura || []).map(a => ({
          text: textCobertura(t, a, unit), missatge: a.missatge || '',
        })),
      })
      // Se'n va de la llista, i la llista no es recalcula (F/T1): confirmar-ne una és l'única
      // cosa que la persona ja sap segur —aquella parella ja no és cap proposta, és una
      // costura—, i és l'únic que la llista es permet saber sense que li ho demanin.
      treuDeLaLlista(p)
      await recarregarRelacions()
    } catch {
      setErrEina(t('pattern.taller.err_proposal_confirm'))
    }
  }

  // ── ACCEPTAR/DESACCEPTAR un desajust (QA-TALLER H · T3) ───────────────────
  // Acceptar no toca geometria ni mesura: registra una decisió auditable al servidor. Després
  // es rellegeixen les relacions perquè la fila mostri l'estat viu (acceptat / per qui).

  const acceptarTolerancia = async (sewId, nota = '') => {
    try {
      await patterns.tolerance.accept(sewId, nota)
      await recarregarRelacions()
    } catch {
      setErrEina(t('pattern.taller.err_tol_accept'))
    }
  }

  const desacceptarTolerancia = async (sewId, nota = '') => {
    try {
      await patterns.tolerance.unaccept(sewId, nota)
      await recarregarRelacions()
    } catch {
      setErrEina(t('pattern.taller.err_tol_accept'))
    }
  }

  /** Treure una proposta de la llista mostrada. NO toca el motor: només la pantalla. */
  const treuDeLaLlista = (p) => {
    const clau = p.clau.join('-')
    setPropostes(l => l.filter(x => x.clau.join('-') !== clau))
  }

  /** Rebutjar-ne una: que no torni a sortir. El «no» es desa; si no, no seria un «no». */
  const rebutjarProposta = async (p) => {
    setPropostaRessaltada(null)
    try {
      await patterns.sew.rebutjarProposta({
        model: modelId, segment_a: p.a.segment_id, segment_b: p.b.segment_id,
      })
      treuDeLaLlista(p)
      await llegirRebuigs()
    } catch {
      setErrEina(t('pattern.taller.err_proposal_reject'))
    }
  }

  // ── ESBORRAT EN BLOC (QA-TALLER E · T3) ───────────────────────────────────
  //
  // Cada família té la seva crida, i totes tornen el MATEIX informe
  // `{esborrats, retinguts}`: el panell no ha de saber quina mena d'entitat acaba de tocar
  // per saber llegir què s'ha quedat.
  //
  // **Totes rellegeixen al `finally`, i totes avisen si peten** (E/T4). L'esborrat és atòmic
  // PER ÍTEM —un èxit parcial és el disseny, no una avaria—, i això vol dir que quan la crida
  // rebota a mig bloc els ítems que ja han caigut han caigut de debò. Rellegir només en cas
  // d'èxit deixaria la columna pintant files mortes i la selecció marcada a sobre: la pantalla
  // mentiria justament el dia que ha anat malament.

  /** L'esborrat en bloc, amb la llei que val per a totes les famílies. */
  const enBloc = async (fn) => {
    try {
      const { data } = await fn()
      return data
    } catch (e) {
      setErrEina(t('pattern.taller.err_bulk'))
      throw e
    } finally {
      await recarregarRelacions()
    }
  }

  // ── LES DUES MANERES DE TREURE UNA PROPOSTA (F/T2) ────────────────────────
  //
  // No són la mateixa cosa dita dues vegades: són dues intencions, i confondre-les era el
  // defecte. El bulk d'E escrivia 27 rebuigs PERMANENTS amb un clic —una decisió que ningú
  // no havia pres parella per parella— i s'ha retirat.

  /**
   * NETEJAR LA LLISTA — efímer. No escriu res, enlloc.
   *
   * «Ja he mirat això, treu-m'ho del davant» no és «aquestes parelles no es cusen». Per això
   * no demana confirmació i no en cal: tornar a buscar les retorna totes. La llibertat de
   * netejar sense conseqüències és el que fa que la llista es pugui fer servir com una taula
   * de treball en comptes d'un formulari que s'ha d'omplir bé a la primera.
   *
   * Torna `cercades` a fals a posta: netejar desfà la cerca, no la deixa vigent i buida. Si no
   * ho fes, el buit diria «el motor no veu cap costura» —la frase de «cercat i cap»— quan la
   * veritat és que n'havia trobades i les has amagades. Un buit que menteix sobre per què és
   * buit és justament el que T3 no vol; el buit honest, aquí, és «torna-ho a buscar».
   */
  const netejarPropostes = () => {
    setPropostaRessaltada(null)
    setPropostes([])
    setCercades(false)
  }

  /**
   * REBUTJAR-NE VÀRIES — persistent. El «no» de sempre, dit sobre unes quantes alhora.
   *
   * Aquí NO hi ha bulk del servidor, i és a posta: una proposta no és cap fila (es recalcula
   * a cada crida) i rebutjar-la és crear-ne el REBUIG. L'endpoint que ja hi ha és idempotent
   * (`get_or_create`), i inventar-ne un segon per a un bucle hauria estat un lloc més on la
   * llei del rebuig podria divergir. Les crides van en paral·lel, i el que rebota s'informa
   * en comptes de fer caure les altres.
   *
   * NO recalcula la llista: només en treu les que s'han rebutjat. Recalcular-la aquí és
   * exactament el que feia aparèixer propostes noves dels trams que el rebuig acabava
   * d'alliberar — el motor omplint el buit que la persona acabava de fer.
   */
  const rebutjarBlocProposta = async (props) => {
    setPropostaRessaltada(null)
    try {
      const resultats = await Promise.allSettled(props.map(p =>
        patterns.sew.rebutjarProposta({
          model: modelId, segment_a: p.a.segment_id, segment_b: p.b.segment_id,
        })))
      // `allSettled`: una que rebota no se n'emporta les altres, i les que han rebotat es
      // diuen a l'informe en comptes de desaparèixer sense dir res.
      const retinguts = resultats.flatMap((r, i) => (r.status === 'rejected'
        ? [{ id: props[i].clau.join('-'), motiu: 'error' }]
        : []))
      if (retinguts.length) setErrEina(t('pattern.taller.err_bulk'))
      const fallades = new Set(retinguts.map(x => x.id))
      props.forEach(p => { if (!fallades.has(p.clau.join('-'))) treuDeLaLlista(p) })
      return { retinguts }
    } finally {
      await llegirRebuigs()
    }
  }

  // ── ELS REBUIGS: DESFER-LOS (F/T3) ────────────────────────────────────────
  // (`llegirRebuigs` viu a dalt, amb el seu efecte: v. la nota de la zona morta.)

  /**
   * Desfer un rebuig, i tornar a buscar si hi havia llista.
   *
   * Rebuscar aquí NO trenca T1: desfer un rebuig és una acció de la persona SOBRE la llista de
   * propostes, i el que en demana és, exactament, «torna-me-la a ensenyar». El que T1 prohibeix
   * és que la llista es mogui quan ningú l'ha tocada.
   */
  const desferRebuig = async (id) => {
    try {
      await patterns.sewRejections.remove(id)
      await llegirRebuigs()
      if (cercades) await buscarPropostes()
    } catch {
      setErrEina(t('pattern.taller.err_rejection_undo'))
    }
  }

  // 🚩 L'ESBORRAT EN BLOC DE POMS NO SOBREVIU A LA FUSIÓ DE PANELLS, i queda dit aquí perquè
  // el client (`patterns.poms.bulkRemove` → `pattern-poms/bulk-delete/`) segueix existint i
  // funcionant: el que ha desaparegut és la SUPERFÍCIE, no la capacitat.
  //
  // El motiu és de forma: el panell únic té una fila per MESURA DE LA FITXA, i un POM hi pot
  // portar més d'un ancoratge (el pit, mesurat al davant i a l'esquena). Una casella per fila
  // marcaria una fila d'espec, no un ancoratge, i «esborra els 3 marcats» hauria hagut de
  // decidir sola quins dels ancoratges cauen. Tornar-hi vol una selecció per ANCORATGE, que
  // és una peça pròpia i no aquest tram.

  // Costures i pinces comparteixen endpoint —una pinça ÉS una SewRelation— però no
  // selecció: al panell són dos grups, perquè esborrar costures i esborrar pinces són dues
  // intencions, i el compte de la paperera ha de dir la mena que caurà.
  const esborrarBlocSew = ids => enBloc(() => patterns.sew.bulkRemove(ids))

  const esborrarBlocTram = ids => enBloc(() => patterns.segments.bulkRemove(ids))

  /** El nom que un tram proposat tindrà quan la proposta es confirmi. */
  const nomTramProposat = (costat) => t('pattern.taller.proposal_seg', {
    peca: costat.peca, llarg: formatLen(costat.longitud_cm, unit),
  })

  /**
   * Els dos trams de la proposta que el cursor assenyala, amb la geometria que el canvas
   * necessita per pintar-los. Els trams proposats són DERIVATS ('auto') i per tant NO són a la
   * llista de trams declarats: el canvas no els té, i se li han de donar.
   */
  /**
   * Les pinces proposades, amb la geometria que el canvas necessita: el vèrtex (on va el glif) i
   * els dos costats (per encendre'ls al hover).
   *
   * Els tres punts arriben com a IDS —són els mateixos que el gest de W4b farà servir—, i el
   * costat de la pinça és el RECORREGUT de la vora entre ells, no la recta: entre dos girs hi pot
   * haver punts de corba, i dibuixar la corda ensenyaria una pinça que no és la que es marcarà.
   */
  const pincesAlCanvas = useMemo(() => {
    const peces = geometria?.pieces || []
    return pincesProp.map(c => {
      const peca = peces.find(p => p.id === c.piece_id)
      const vora = peca && (peca.boundaries || []).find(b => b.index === c.vora)
      if (!vora) return null
      const idx = (id) => (vora.points || []).findIndex(q => q.id === id)
      const ia = idx(c.point_a), iv = idx(c.point_vertex), ib = idx(c.point_b)
      if (ia < 0 || iv < 0 || ib < 0) return null
      return {
        clau: c.clau.join('-'),
        apex: vora.points[iv],
        costats: [puntsEntreIndexs(vora, ia, iv), puntsEntreIndexs(vora, iv, ib)],
      }
    }).filter(Boolean)
  }, [pincesProp, geometria])

  const propostaAlCanvas = useMemo(() => {
    if (!propostaRessaltada) return null
    const tram = (c) => {
      const peca = (geometria?.pieces || []).find(p => p.id === c.piece_id)
      const sg = peca && (peca.segments || []).find(s => s.id === c.segment_id)
      return sg ? { ...sg, piece_id: c.piece_id } : null
    }
    const a = tram(propostaRessaltada.a)
    const b = tram(propostaRessaltada.b)
    return a && b ? { a, b } : null
  }, [propostaRessaltada, geometria])

  const esborrarPOM = async (pomId) => {
    await patterns.poms.remove(pomId)
    await recarregarRelacions()
  }

  const esborrarSew = async (sewId) => {
    await patterns.sew.remove(sewId)
    await recarregarRelacions()
  }

  const reanomenarTram = async (tramId, nom) => {
    await patterns.segments.rename(tramId, nom)
    await recarregarRelacions()
  }

  const reanomenarSew = async (sewId, nom) => {
    await patterns.sew.update(sewId, { nom })
    await recarregarRelacions()
  }

  // ── REOBRIR (T5) ─────────────────────────────────────────────────────────
  // Les tres entitats es reobren des de RELACIONS i s'editen amb EL MATEIX GEST amb què es van
  // crear. No hi ha un segon editor: hi ha el taller, i el taller sap tornar-hi.

  /** Un punt de la geometria, pel seu id. */
  const puntPerId = useCallback((id) => {
    for (const p of geometria?.pieces || []) {
      for (const b of p.boundaries || []) {
        const q = (b.points || []).find(x => x.id === id)
        if (q) return q
      }
    }
    return null
  }, [geometria])

  /** Reobrir un POM ancorat: la recepta torna al canvas i es tornen a marcar les àncores.

   * El selector es posa al mètode del POM que s'obre, i no al que hi hagués triat abans:
   * reobrir una caiguda per corregir-la i que el canvas et demanés dos punts seria començar
   * a fer-ne una altra cosa. Les àncores que es dibuixen de fons són les d'AQUELL mètode —
   * llegir-hi sempre `a` i `b` deixaria l'ombra buida en tot el que no fos una recta.
   */
  const reobrirPOM = (pom) => {
    const def = pom.definicio_mesura || {}
    const conegut = metodes.find(m => m.codi === pom.metode)
    // Sense el vocabulari no se sap quantes àncores vol aquest POM ni com es diuen, i el gest
    // cauria al de dos punts: reobrir una caiguda per recol·locar-li un extrem li demanaria
    // dos clics i n'enviaria una recepta de recta. Val més no obrir-lo i dir-ho.
    if (metodes.length && !conegut) {
      setErrEina(t('pattern.taller.err_metode_desconegut', { metode: pom.metode }))
      return
    }
    if (!metodes.length) {
      setErrEina(t('pattern.taller.err_sense_vocabulari'))
      return
    }
    const claus = conegut.ancores
    netejarSeleccio()
    setPomEditId(pom.id)
    if (pom.metode) setMetodeSel(pom.metode)
    // Les opcions que la recepta ja porta: reobrir una cota en V i que el selector digués
    // AUTO seria oferir-se a canviar-la sense dir-ho.
    setOpcionsSel(Object.fromEntries(
      Object.keys(conegut.opcions || {})
        .filter(nom => def[nom] !== undefined)
        .map(nom => [nom, def[nom]])))
    setOmbra({
      mena: 'pom',
      pomMaster: pom.pom_master,
      codi: pom.pom_code,
      punts: claus.map(clau => puntPerId(def[clau])).filter(Boolean),
    })
    setMode('pom')
  }

  /** Reobrir un tram: es recol·loquen els extrems, sobre la MATEIXA fila. */
  const reobrirTram = (tram) => {
    netejarSeleccio()
    setTramEditId(tram.id)
    setNomTram(tram.nom || '')
    const peca = (geometria?.pieces || []).find(p => p.id === tram.piece_id)
    setOmbra({
      mena: 'seg',
      nom: tram.nom,
      punts: peca ? puntsDelSegment(peca, tram) : [],
    })
    setMode('seg')
  }

  /** Reobrir una costura: tipus, diferencial i composició de costats, a l'editor de cosir. */
  const reobrirSew = (sew) => {
    netejarSeleccio()
    setSewEditId(sew.id)
    setSegmentsA([...(sew.segments_a || [])])
    setSegmentsB([...(sew.segments_b || [])])
    setTipusSew(sew.tipus)
    setDiferencial(sew.diferencial_cm ?? 0)
    setNomSew(sew.nom || '')
    setMode('sew')
  }

  /**
   * Esborrar una pinça: la costura I els seus dos costats.
   *
   * Els costats d'una pinça no existeixen sense ella —són la pinça—, i deixar-los enrere
   * ompliria el patró de trams que ningú no cus i que ningú no sabria d'on venen. Ho fa el
   * servidor en una transacció (v. `SewRelationViewSet.destroy`): des d'aquí seria tres
   * crides que poden fallar per la meitat.
   */
  const esborrarPinca = async (sewId) => {
    await patterns.sew.remove(sewId)
    await recarregarRelacions()
  }

  // El 409 no és un error del sistema: és el sistema dient que no. Torna el motiu
  // (quines costures el retenen) perquè la fila el pugui explicar allà mateix.
  const esborrarTram = async (tramId) => {
    try {
      await patterns.segments.remove(tramId)
      await recarregarRelacions()
      return { ok: true }
    } catch (e) {
      const sewIds = e.response?.data?.sew_relations
      if (Array.isArray(sewIds)) return { ok: false, sews: sewIds }
      throw e
    }
  }

  /** La peça que conté un punt de la geometria. */
  const pecaDelPunt = useCallback((punt) => (geometria?.pieces || []).find(p =>
    (p.boundaries || []).some(v => (v.points || []).some(q => q.id === punt.id))),
  [geometria])

  // La peça on l'imant pot caçar (D8). Un cop clicat el punt A, el B ha de sortir de la
  // MATEIXA peça: un PatternPOM penja d'UNA peça, i una mesura amb un extrem a cada peça no
  // seria una mesura d'aquesta peça — seria una recepta que el servidor no pot resoldre.
  // Abans del primer clic mana la peça seleccionada, si n'hi ha; si no, tot el patró.
  const pecaIman = useMemo(() => {
    if (mode !== 'pom' && mode !== 'seg') return null
    if (puntsPom.length > 0) return pecaDelPunt(puntsPom[0])?.nom_block || null
    return pecaSel || null
  }, [mode, puntsPom, pecaSel, pecaDelPunt])

  /** La vora (índex) i la posició d'un punt dins d'ella.
   *
   * El MATEIX `situaPunt` que el canvas fa servir per a la previsualització: si cadascú
   * situés els punts pel seu compte, un dia el canvas pintaria un arc i el taller en crearia
   * un altre. */
  const voraDelPunt = useCallback(
    (punt) => situaPunt(geometria?.pieces || [], punt),
    [geometria])

  // Definint un tram, l'imant queda tancat a la VORA del punt A. Un tram és un tros d'UNA
  // vora: si el punt B pogués sortir d'una altra, el motor ho rebutjaria — i és millor no
  // deixar clicar el que no es pot fer que deixar-ho clicar i després dir que no.
  const voraIman = useMemo(() => {
    if (mode !== 'seg' || puntsPom.length === 0) return null
    return voraDelPunt(puntsPom[0])?.index ?? null
  }, [mode, puntsPom, voraDelPunt])

  /** L'arc entre dos punts ja clicats, amb la direcció que es va triar en fixar-lo. */
  const arcFixat = useCallback((i, j) => {
    const a = voraDelPunt(puntsPom[i])
    const b = voraDelPunt(puntsPom[j])
    if (!a || !b || a.index !== b.index) return null
    // El MATEIX `arcDirigit` que el canvas fa servir per pintar la prèvia: si cadascú triés
    // l'arc pel seu compte, un dia es pintaria un i es crearia l'altre.
    return arcDirigit(a.vora, a.ordre, b.ordre, !!invertits[i])
  }, [puntsPom, invertits, voraDelPunt])

  // El tram que s'està a punt de declarar (dos punts fixats).
  const arcTram = useMemo(
    () => (mode === 'seg' && puntsPom.length === 2 ? arcFixat(0, 1) : null),
    [mode, puntsPom, arcFixat])

  // Els dos costats de la pinça que s'està a punt de marcar (tres punts fixats).
  const costatsPinca = useMemo(() => {
    if (mode !== 'pinca' || puntsPom.length !== 3) return null
    const a = arcFixat(0, 1)
    const b = arcFixat(1, 2)
    return a && b ? [a, b] : null
  }, [mode, puntsPom, arcFixat])

  const crearTram = async () => {
    if (!arcTram || !nomTram.trim()) return
    setCreantTram(true)
    try {
      // Dos PUNTS i quin arc; ni t ni longituds. El tram el resol el servidor sobre la
      // geometria — igual que el valor d'un POM.
      const cos = {
        point_a: puntsPom[0].id,
        point_b: puntsPom[1].id,
        nom: nomTram.trim(),
        arc_llarg: arcTram.arcLlarg,
      }
      // RECOL·LOCAT (T5b): la MATEIXA fila. Esborrar-la i crear-ne una altra buidaria el
      // costat de les costures que la cusen, en silenci.
      if (tramEditId) await patterns.segments.update(tramEditId, cos)
      else await patterns.segments.create(cos)
      netejarSeleccio()
      setMode('view')
      await recarregarRelacions()
    } catch (e) {
      setErrEina(e.response?.data?.tram
        || e.response?.data?.point_a
        || e.response?.data?.detail
        || t('pattern.taller.err_segment'))
      setPuntsPom([])
    } finally {
      setCreantTram(false)
    }
  }

  /**
   * Marcar una pinça: tres punts, i el servidor en fa dos trams i una costura de pinça.
   *
   * UNA sola crida. Fer-ho amb tres (dos trams i la costura) podia fallar a la tercera i
   * deixar dos trams orfes al patró, amb nom de pinça i sense pinça.
   */
  const crearPinca = async () => {
    if (!costatsPinca || !nomTram.trim()) return
    setCreantTram(true)
    try {
      const nom = nomTram.trim()
      const { data } = await patterns.sew.pinca({
        model: modelId,
        point_a: puntsPom[0].id,
        point_vertex: puntsPom[1].id,
        point_b: puntsPom[2].id,
        nom,
        nom_a: t('pattern.taller.pinca_side_a', { nom }),
        nom_b: t('pattern.taller.pinca_side_b', { nom }),
      })
      // La pinça diu de seguida què ha fet: quanta tela es menja. És el número que després
      // apareixerà restat a la costura que la conté, i val més veure'l néixer.
      const e = data.estat || {}
      setVeredicte({
        casa: !!e.casa, grau: e.grau,
        estat: textEstat(t, e, unit),
        missatge: e.missatge || '',
        cobertura: (e.cobertura || []).map(a => ({
          text: textCobertura(t, a, unit), missatge: a.missatge || '',
        })),
      })
      netejarSeleccio()
      setMode('view')
      await recarregarRelacions()
    } catch (e) {
      setErrEina(e.response?.data?.tram
        || e.response?.data?.detail
        || t('pattern.taller.err_pinca'))
      setPuntsPom([])
    } finally {
      setCreantTram(false)
    }
  }

  // Els trams DECLARATS. De la geometria en surten TOTS —els que el motor proposa (gir→gir,
  // origen 'auto') i els que algú ha declarat—, però al taller només manen els declarats: la
  // proposta del motor és una hipòtesi de lectura, no una vora que ningú hagi dit que existeixi.
  //
  // La longitud i l'«en ús» es calculen aquí perquè ja tenim tot el que fa falta: la vora
  // (per a la longitud) i les costures (per saber qui el reté). Demanar-los al servidor seria
  // una tercera crida per a dades que ja són a la pantalla.
  // Els costats de les PINCES són trams declarats, però NO són vocabulari de costura: un
  // costat de pinça es cus contra el seu germà, mai contra una altra peça. Oferir-los per
  // cosir seria oferir un disbarat, i llistar-los amb els altres ompliria la llista de
  // treball de files que ningú ha de tocar. Viuen a la seva pinça, i és allà que s'editen.
  const idsCostatPinca = useMemo(() => new Set(
    sews.filter(s => s.es_pinca)
      .flatMap(s => [...(s.segments_a || []), ...(s.segments_b || [])])
  ), [sews])

  const totsElsTrams = useMemo(() => {
    const enUs = new Set(sews.flatMap(s => [...(s.segments_a || []), ...(s.segments_b || [])]))
    return (geometria?.pieces || []).flatMap(p =>
      (p.segments || [])
        .filter(sg => sg.origen === 'declarat')
        .map(sg => {
          const vora = (p.boundaries || []).find(b => b.index === sg.vora)
          return {
            ...sg,
            peca: etiquetaPeca(p),
            piece_id: p.id,
            longitud_cm: vora ? round2(longitudTram(vora, sg.t_inici, sg.t_fi) / 10) : null,
            en_us: enUs.has(sg.id),
          }
        }))
  }, [geometria, sews])

  const trams = useMemo(
    () => totsElsTrams.filter(tr => !idsCostatPinca.has(tr.id)),
    [totsElsTrams, idsCostatPinca])

  /** Tots els trams per id — el diccionari amb què es genera el nom d'una costura (T6). */
  const tramsPerId = useMemo(
    () => new Map(totsElsTrams.map(tr => [tr.id, tr])), [totsElsTrams])

  /**
   * Les PINÇES, amb la geometria que el canvas necessita per pintar-les.
   *
   * El VÈRTEX és el punt on els dos costats es toquen: l'últim punt del primer costat. No cal
   * desar-lo enlloc —surt de la geometria— i desar-lo seria tenir-ne dues versions el dia que
   * algú recol·loqués un costat.
   */
  const pinces = useMemo(() => {
    const peces = geometria?.pieces || []
    return sews.filter(s => s.es_pinca).map(s => {
      const ids = [...(s.segments_a || []), ...(s.segments_b || [])]
      const costats = ids.map(id => {
        const tr = tramsPerId.get(id)
        const peca = tr && peces.find(p => p.id === tr.piece_id)
        return peca ? puntsDelSegment(peca, tr) : []
      }).filter(pts => pts.length >= 2)
      const primer = costats[0] || []
      const e = s.estat || {}
      return {
        id: s.id,
        nom: s.nom || t('pattern.taller.pinca_unnamed', { id: s.id }),
        costats,
        apex: primer.length ? primer[primer.length - 1] : null,
        // La tela que aquesta pinça es menja: la suma dels seus dos costats. És, exactament,
        // el número que es veurà restat a la costura que la conté.
        cm: round2((e.longitud_a_cm || 0) + (e.longitud_b_cm || 0)),
        legs: ids.map(id => tramsPerId.get(id)).filter(Boolean),
        estat: e,
        sew: s,
      }
    })
  }, [sews, geometria, tramsPerId, t])

  /** Les costures de debò: les que no són pinces. Una pinça no és una costura més. */
  const costures = useMemo(() => sews.filter(s => !s.es_pinca), [sews])

  const tornar = () => navigate(`/models/${modelId}?tab=Patró`)

  // ÀNCORA DE MESURA (§8d) — v. el motiu llarg a `components/pattern/PatternTab.jsx`.
  return (
    <div data-ftt-screen="taller-patro" style={{
      width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column',
      background: 'var(--bg-page)', overflow: 'hidden',
    }}>
      <Capcalera t={t} model={model} fp={actual} modelId={modelId} onTorna={tornar} />

      <main style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <aside style={{
          width: 360, flexShrink: 0, display: 'flex', flexDirection: 'column',
          minHeight: 0, borderRight: '1px solid var(--line)', background: 'var(--bg-page)',
        }}>
          <Contenidor
            titol={t('pattern.pieces', { n: geometria?.pieces?.length || 0 })}
            icona="ti-vector-triangle" pes={1}
          >
            {actual && (
              <PieceList pieces={actual.pieces} pecaSel={pecaSel} onTria={setPecaSel} />
            )}
          </Contenidor>

          {/* ROLS DE VORA (F4.2-BIS). Sota la llista de peces perquè és la seva
              continuació: es bategen les vores DE la peça que hi ha seleccionada, i la
              selecció que mana és la mateixa. El panell es plega quan no hi ha peça
              triada — sense peça no hi ha pregunta a fer. */}
          <Contenidor
            titol={t('pattern.edges_title')} icona="ti-vector-bezier-2" pes={1.5}
          >
            {!pecaSel ? (
              <p style={{
                margin: 0, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
              }}>
                {t('pattern.edges_pick_piece')}
              </p>
            ) : (
              <PieceEdgeRoleList
                files={vores}
                vocabularis={vocabularis}
                nomesPeca={pecaSel}
                pecaSel={pecaSel}
                voraSel={voraSel}
                onVoraSel={(id, enq) => {
                  // Passar-hi per sobre només assenyala; el clic assenyala I enquadra.
                  if (!enq) { setVoraSel(id); return }
                  const tanca = voraSel === id && !!enquadra
                  setVoraSel(tanca ? null : id)
                  if (!tanca) enquadraTram(id)
                }}
                onConfirma={confirmarVores}
                desant={desantVores}
                error={errorVores}
              />
            )}
          </Contenidor>

          <Contenidor
            titol={t('pattern.taller.model_poms', {
              ancorats: feina?.ancorats || 0, total: feina?.total || 0,
            })}
            icona="ti-ruler-measure" pes={1.5}
          >
            <ModelPomList
              files={feina?.results || []}
              poms={pomsAncorats}
              pomActiu={pomActiu}
              pomSelId={pomSelViu}
              onColocar={colocarPOM}
              onAfegirFora={afegirPOMForaDeFitxa}
              onReobre={reobrirPOM}
              onEsborra={id => setEsborraCota(id)}
              onAssenyala={id => setPomSel(v => (v === id ? null : id))}
              unit={unit}
            />
          </Contenidor>

          <Contenidor titol={t('pattern.taller.relations')} icona="ti-link" pes={1}>
            <RelationsPanel
              sews={costures} pinces={pinces} segments={trams}
              tramsPerId={tramsPerId} unit={unit}
              onEnquadraTram={enquadraTram}
              propostes={propostes} descartatsProp={descartatsProp}
              cercades={cercades} buscant={buscant}
              onBuscaPropostes={buscarPropostes} onNetejaPropostes={netejarPropostes}
              rebuigs={rebuigs} onDesfaRebuig={desferRebuig}
              onConfirmaProposta={confirmarProposta}
              onRebutjaProposta={rebutjarProposta}
              onRessaltaProposta={setPropostaRessaltada}
              pincesProposades={pincesProp} descartatsPinca={descartatsPinca}
              onConfirmaPinca={confirmarPinca}
              onRebutjaPinca={rebutjarPinca}
              onRessaltaPinca={c => setPincaPropRessaltada(c ? c.clau.join('-') : null)}
              onEsborraSew={esborrarSew} onReobreSew={reobrirSew}
              onReanomenaSew={reanomenarSew}
              onEsborraPinca={esborrarPinca} onReanomenaPinca={reanomenarSew}
              onReanomenaTram={reanomenarTram} onReobreTram={reobrirTram}
              onEsborraTram={esborrarTram}
              onAcceptaTolerancia={acceptarTolerancia}
              onDesacceptaTolerancia={desacceptarTolerancia}
              onRebutjaBlocProposta={rebutjarBlocProposta}
              onEsborraBlocSew={esborrarBlocSew}
              onEsborraBlocPinca={esborrarBlocSew}
              onEsborraBlocTram={esborrarBlocTram}
            />
          </Contenidor>
        </aside>

        {/* `position: relative` NO és decoració: el POMPicker s'ancora en absolut i sense
            un pare posicionat aniria a raure al racó de la finestra, sobre la columna. */}
        <section style={{
          flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column',
          minHeight: 0, padding: '0.6rem 0.8rem', gap: '0.5rem', position: 'relative',
        }}>
          <BarraEines
            t={t} mode={mode} onMode={triarMode}
            tascaId={tascaId} errTasca={errTasca}
            slotVisor={setSlotVisor}
          />

          {errEina && (
            <Avis text={errEina} err onTanca={() => setErrEina(null)} />
          )}
          {veredicte && (
            <Veredicte t={t} v={veredicte} onTanca={veredicteVist} />
          )}
          {mode === 'pom' && (
            <>
              {/* El selector només apareix si el servidor ha dit quins mètodes hi ha, i
                  només si n'hi ha més d'un: una tria d'una sola opció no és una tria. */}
              {metodes.length > 1 && (
                <SelectorMetode
                  t={t} metodes={metodes} triat={metodeSel}
                  opcions={opcionsPom} valorOpcio={valorOpcio}
                  onOpcio={(nom, valor) => {
                    setOpcionsSel(o => ({ ...o, [nom]: valor }))
                    // Canviar l'eix a mig gest no invalida els clics: les àncores són les
                    // mateixes i el que canvia és què se'n projecta. No es reinicia res.
                  }}
                  onTria={codi => {
                    setMetodeSel(codi)
                    setPuntsPom([])
                    // Les opcions són DEL mètode: un eix triat per a una cota no vol dir res
                    // per a una caiguda, i arrossegar-lo faria que el vocabulari nou nasqués
                    // amb un valor que no és seu.
                    setOpcionsSel({})
                    // I l'ombra de la reobertura se'n va amb els punts: dibuixava les àncores
                    // del mètode VELL, i amb un recompte diferent deixava dos punts de fons
                    // mentre el comptador en demanava tres. D'on es ve deixa de ser rellevant
                    // quan es canvia el QUÈ es mesura.
                    setOmbra(o => (o ? { ...o, punts: [] } : o))
                  }}
                  pas={puntsPom.length} ancores={ancoresPom}
                />
              )}
              <Avis
                text={textAncoratge(t, {
                  ombra, pomActiu, fets: puntsPom.length, ancores: ancoresPom,
                })}
                onTanca={cancelar}
                tancaEtiqueta={t('pattern.taller.cancel_place')}
              />
            </>
          )}
          {mode === 'seg' && (
            <Avis
              text={tramEditId && puntsPom.length === 0
                ? t('pattern.taller.seg_reopen_hint', { nom: ombra?.nom || '' })
                : puntsPom.length === 0
                  ? t('pattern.taller.seg_a')
                  : puntsPom.length === 1
                    ? t('pattern.taller.seg_b')
                    : t('pattern.taller.seg_ready')}
              onTanca={cancelar}
              tancaEtiqueta={t('pattern.taller.cancel_place')}
            />
          )}
          {/* MARCAR PINÇA (T1): tres clics — inici, vèrtex, final. La guia diu SEMPRE quin
              toca, perquè un gest de tres passos sense guia és un gest que s'endevina. */}
          {mode === 'pinca' && (
            <Avis
              text={t(['pattern.taller.pinca_a', 'pattern.taller.pinca_vertex',
                       'pattern.taller.pinca_b'][puntsPom.length]
                      || 'pattern.taller.pinca_ready')}
              onTanca={cancelar}
              tancaEtiqueta={t('pattern.taller.cancel_place')}
            />
          )}
          {mode === 'seg' && arcTram && (
            <SegmentEditor
              llargMm={arcTram.longitud}
              nom={nomTram} onNom={setNomTram}
              onCrea={crearTram} onCancela={cancelar} creant={creantTram}
              unit={unit}
            />
          )}
          {mode === 'pinca' && costatsPinca && (
            <SegmentEditor
              pinca
              llargMm={costatsPinca[0].longitud + costatsPinca[1].longitud}
              nom={nomTram} onNom={setNomTram}
              onCrea={crearPinca} onCancela={cancelar} creant={creantTram}
              unit={unit}
            />
          )}
          {mode === 'sew' && (
            <SewEditor
              segmentsA={segmentsA} segmentsB={segmentsB}
              costatActiu={costatActiu} onCostat={setCostatActiu}
              tipus={tipusSew} onTipus={setTipusSew}
              diferencial={diferencial} onDiferencial={setDiferencial}
              nom={nomSew} onNom={setNomSew}
              editant={!!sewEditId}
              onDeclara={declararCostura}
              onNeteja={cancelar}
              trams={trams}
              onTriaTram={triarTram}
              onRessalta={setTramRessaltat}
              onDefinirTram={() => triarMode('seg')}
              unit={unit}
            />
          )}

          {carregant ? (
            <Centrat text={t('pattern.viewer_loading')} />
          ) : error ? (
            <Centrat text={error} err />
          ) : !geometria ? (
            <Centrat text={t('pattern.taller.no_file')} />
          ) : (
            <PatternViewer
              pieces={geometria.pieces}
              pecaSel={pecaSel}
              onTriaPeca={setPecaSel}
              mode={mode}
              puntsPom={puntsPom}
              ancoresPom={ancoresPom}
              pomSel={pomSelViu}
              onSeleccionaPom={p => setPomSel(v => (v === p.id ? null : p.id))}
              onMouPom={tascaId ? mouCota : null}
              onClicPunt={onClicPunt}
              segmentsA={segmentsA}
              segmentsB={segmentsB}
              costatActiu={costatActiu}
              pecaIman={pecaIman}
              voraIman={voraIman}
              arcInvertit={arcInvertit}
              invertits={invertits}
              ombra={ombra}
              tramsDeclarats={trams}
              tramRessaltat={tramRessaltat}
              onClicTram={triarTram}
              voresRolades={voresAlCanvas}
              voraRessaltada={voraSel}
              // Del llenç a la fila NO s'enquadra: qui clica un tram al patró ja el té
              // davant, i moure-li la càmera sota el dit seria prendre-li el lloc on és.
              onClicVora={vr => setVoraSel(v => (v === vr.id ? null : vr.id))}
              enquadra={enquadra}
              pinces={pinces}
              propostaRessaltada={propostaAlCanvas}
              pincesProposades={pincesAlCanvas}
              pincaProposadaRessaltada={pincaPropRessaltada}
              unit={unit}
              omplirAlcada
              contenidorEines={slotVisor}
            />
          )}

          {pickerObert && (
            <POMPicker
              onTria={pom => ancorar(pom.id, puntsPom)}
              onCancel={() => { setPickerObert(false); setPuntsPom([]) }}
            />
          )}

          {/* Supr sobre una cota assenyalada: es pregunta, sempre. És l'única acció
              destructiva que es pot disparar amb una tecla, i una tecla no és una decisió. */}
          {esborraCota != null && (
            <Modal
              title={t('pattern.taller.cota_delete_title')}
              subtitle={t('pattern.taller.cota_delete_body')}
              confirmLabel={t('pattern.taller.cota_delete_ok')}
              cancelLabel={t('app.cancel')}
              onCancel={() => setEsborraCota(null)}
              onConfirm={() => {
                const id = esborraCota
                setEsborraCota(null)
                setPomSel(null)
                esborrarPOM(id).catch(() => setErrEina(t('pattern.err_pom')))
              }}
            />
          )}
        </section>
      </main>
    </div>
  )
}

const round2 = (v) => Math.round(v * 100) / 100

/**
 * La tecla ve d'un camp on algú està escrivint?
 *
 * La porta que faltava al listener global del Taller. Un `keydown` a `window` no sap res del
 * focus, i sense preguntar-ho una drecera d'una sola lletra és una bomba: escriure el nom
 * d'un tram girava l'arc (el bug de la tecla F), i Supr hauria esborrat cotes mentre algú
 * corregia un nom.
 *
 * `isContentEditable` hi entra perquè no tot camp de text és un `<input>`, i el `role` de
 * `textbox` perquè un component pot fer-ne un sense ser cap dels dos.
 */
function esCampDeText(target) {
  if (!target) return false
  const tag = (target.tagName || '').toUpperCase()
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
    || target.isContentEditable === true
    || target.getAttribute?.('role') === 'textbox'
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Barra d'eines. Els botons NO obren ni pausen la tasca: això ho fa entrar i sortir del
 * taller. Aquí només es tria QUÈ s'està fent — i si no hi ha rellotge (403 de perfil),
 * les eines no s'ofereixen: el patró es pot mirar, però no anotar sense comptar el temps.
 */
function BarraEines({ t, mode, onMode, tascaId, errTasca, slotVisor }) {
  const boto = (actiu) => ({
    background: actiu ? 'var(--gold)' : 'var(--panel)',
    color: actiu ? 'var(--text-main)' : 'var(--text-main)',
    border: `1px solid ${actiu ? 'var(--gold)' : 'var(--line)'}`,
    cursor: tascaId ? 'pointer' : 'not-allowed',
    opacity: tascaId ? 1 : 0.5,
    display: 'flex', alignItems: 'center',
    ...METRICA_EINA,
  })

  return (
    <div style={{
      display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap',
      flexShrink: 0,
    }}>
      <button
        onClick={() => onMode('pom')} disabled={!tascaId}
        aria-pressed={mode === 'pom'} style={boto(mode === 'pom')}
      >
        <i className="ti ti-ruler-measure" />
        {t('pattern.mode_pom')}
      </button>
      {/* PRIMER DECLARAR, DESPRÉS COSIR: l'ordre dels botons és l'ordre del flux. */}
      <button
        onClick={() => onMode('seg')} disabled={!tascaId}
        aria-pressed={mode === 'seg'} style={boto(mode === 'seg')}
      >
        <i className="ti ti-line" />
        {t('pattern.taller.mode_seg')}
      </button>
      {/* MARCAR PINÇA, al costat de Cosir: una pinça és el que explica per què una vora fa 32
          cm i només en cus 30. Sense poder-la declarar, aquella costura no casa mai i el patró
          està bé. */}
      <button
        onClick={() => onMode('pinca')} disabled={!tascaId}
        aria-pressed={mode === 'pinca'} style={boto(mode === 'pinca')}
      >
        <i className="ti ti-triangle" />
        {t('pattern.taller.mode_pinca')}
      </button>
      <button
        onClick={() => onMode('sew')} disabled={!tascaId}
        aria-pressed={mode === 'sew'} style={boto(mode === 'sew')}
      >
        <i className="ti ti-needle-thread" />
        {t('pattern.mode_sew')}
      </button>

      {/* Els controls del visor (zoom · encaixar · capes) aterren AQUÍ per portal, seguits de
          Cosir i amb la mateixa mida: una sola barra, no dues. `display: contents` treu aquest
          contenidor de la maquetació perquè els botons siguin fills flex de la barra i hi
          facin `wrap` un a un, com els de dalt. Si el fitxer no ha carregat encara, el visor
          no es pinta i aquí no hi arriba res: la barra queda amb les eines de mode i prou. */}
      <span ref={slotVisor} style={{ display: 'contents' }} />

      <span style={{ flex: 1 }} />

      {errTasca ? (
        <span style={{
          display: 'flex', alignItems: 'center', gap: '0.35rem',
          fontSize: 'var(--fs-caption)', color: 'var(--err)',
          background: 'var(--err-bg)', borderRadius: 4, padding: '3px 8px',
        }}>
          <i className="ti ti-alert-triangle" />
          {errTasca}
        </span>
      ) : tascaId && (
        <span style={{
          display: 'flex', alignItems: 'center', gap: '0.35rem',
          fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
        }}>
          <i className="ti ti-clock-play" />
          {t('pattern.task_running')}
        </span>
      )}
    </div>
  )
}

/**
 * El veredicte d'una costura acabada de declarar: casa o no casa (amb les xifres) i, si la
 * vora ha quedat malament, els avisos de cobertura amb els cm exactes.
 *
 * NO bloqueja: la costura ja està feta. El patronista mana, i pot tenir raons per declarar
 * una costura que no casa. El que no pot passar és que no ho sàpiga.
 */
function Veredicte({ t, v, onTanca }) {
  // El mateix semàfor que a RELACIONS (H/T1): l'avís immediat en declarar i la fila han de dir
  // el mateix color per a la mateixa costura.
  const g = grauVisual(v)
  return (
    <div style={{
      flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 4,
      border: `1px solid ${g.color}`,
      background: g.bg,
      borderRadius: 4, padding: '0.4rem 0.6rem', fontSize: 'var(--fs-caption)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <i className={`ti ${g.icona}`} style={{ color: g.color }} />
        <strong>{t('pattern.taller.sew_done')}</strong>
        <span title={v.missatge || undefined} style={{ fontFamily: 'var(--mono)' }}>
          {v.estat}
        </span>
        <span style={{ flex: 1 }} />
        <button
          onClick={onTanca}
          aria-label={t('app.close')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
        >
          <i className="ti ti-x" />
        </button>
      </div>
      {v.cobertura.map((a, i) => (
        <div
          key={i}
          title={a.missatge || undefined}
          style={{
            display: 'flex', alignItems: 'flex-start', gap: '0.35rem',
            color: 'var(--warn)', background: 'var(--warn-bg)',
            borderRadius: 4, padding: '3px 6px',
          }}
        >
          <i className="ti ti-alert-triangle" style={{ marginTop: 2 }} />
          <span>{a.text}</span>
        </div>
      ))}
    </div>
  )
}

/**
 * La frase que guia el gest d'ancorar. Una funció i no un niu de ternaris dins del JSX
 * perquè ara té dues famílies de casos i llegir-les barrejades no ho posava fàcil.
 *
 * Les mesures de DUES àncores conserven els textos de sempre, literals: són gest conformat
 * i no hi havia cap motiu per reescriure'ls. Les de TRES o més entren per la branca nova,
 * que diu sempre quina àncora toca i en quin pas va — un gest de tres clics sense guia és
 * un gest que s'endevina (la mateixa llei que ja regeix el de la pinça).
 */
function textAncoratge(t, { ombra, pomActiu, fets, ancores }) {
  const reobrint = ombra?.mena === 'pom'
  const nom = ancores[Math.min(fets, ancores.length - 1)]

  if (ancores.length <= 2) {
    if (reobrint) return t('pattern.taller.pom_reopen_hint', { codi: ombra.codi })
    if (pomActiu) {
      return t(fets === 0 ? 'pattern.taller.place_a' : 'pattern.taller.place_b', {
        codi: pomActiu.codi_client,
        nom: pomActiu.nom_client || pomActiu.nom_canonic,
      })
    }
    return t(fets === 0 ? 'pattern.pom_hint_first' : 'pattern.pom_hint_second')
  }

  const dades = {
    ancora: t(`pattern.taller.ancora.${nom}`),
    pas: fets + 1,
    total: ancores.length,
  }
  if (reobrint) {
    return t('pattern.taller.ancora_reopen', { ...dades, codi: ombra.codi })
  }
  if (pomActiu) {
    return t('pattern.taller.ancora_pas', {
      ...dades,
      codi: pomActiu.codi_client,
      nom: pomActiu.nom_client || pomActiu.nom_canonic,
    })
  }
  return t('pattern.taller.ancora_pas_sense_pom', dades)
}

//: Pictograma per mètode. NOMÉS decoració: un codi que no hi sigui cau al genèric i el
//: mètode segueix funcionant igual. El que no pot viure al client és QUINS mètodes hi ha
//: (això ve del servidor); com es dibuixen, sí.
const ICONA_METODE = {
  // ⚠️ `ti-line` NO: a dos pams d'aquí, a la barra d'eines, ja vol dir «mode Tram»
  // (BarraEines). Dos significats per al mateix glif a la mateixa pantalla és pitjor que un
  // glif menys evocador.
  recta: 'ti-arrows-horizontal',
  vora: 'ti-vector-spline',
  ortogonal: 'ti-corner-down-right',
  // `ti-ruler-measure` NO: ja és el botó del mode POM a la barra d'eines. `ti-dimensions`
  // és el glif de cota de tota la vida i no el fa servir ningú més al repo.
  projeccio: 'ti-dimensions',
}

/**
 * Tria del mètode de mesura, i —quan el mètode vol més de dues àncores— el comptador de
 * passos amb l'àncora que toca ara marcada.
 *
 * Canviar de mètode REINICIA els punts clicats (ho fa qui el crida). No és una pèrdua de
 * feina: dos punts posats per a una recta no són les dues primeres àncores d'una caiguda,
 * i deixar-los-hi hauria fet que el tercer clic ancorés una cosa que ningú no ha marcat.
 */
/** La clau i18n d'un valor d'opció. El buit té nom («auto») perquè una clau no pot acabar
 *  en punt: el vocabulari serveix `''` per a l'automàtic i aquí es bateja per poder-lo dir. */
const clauValor = (valor) => valor || 'auto'

function SelectorMetode({
  t, metodes, triat, onTria, pas, ancores, opcions = {}, valorOpcio, onOpcio,
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap',
      flexShrink: 0, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
    }}>
      <span>{t('pattern.taller.metode_label')}</span>
      {/* `aria-pressed`, i NO `role="radio"`: el control visualment idèntic de la barra
          d'eines ja parla així, i dues gramàtiques d'ARIA per a la mateixa pell a la mateixa
          pantalla és pitjor que una de menys específica. Un `role="radiogroup"` de debò
          voldria roving tabindex i navegació per fletxes, que aquí no hi ha. */}
      <div style={{ display: 'flex', gap: '0.3rem' }}>
        {metodes.map(m => {
          const actiu = m.codi === triat
          return (
            <button
              key={m.codi} aria-pressed={actiu}
              onClick={() => onTria(m.codi)}
              title={t(`pattern.taller.metode_ajuda.${m.codi}`)}
              style={{
                display: 'flex', alignItems: 'center', cursor: 'pointer',
                color: 'var(--text-main)',
                background: actiu ? 'var(--gold)' : 'var(--panel)',
                border: `1px solid ${actiu ? 'var(--gold)' : 'var(--line)'}`,
                ...METRICA_EINA_COMPACTA,
              }}
            >
              <i className={`ti ${ICONA_METODE[m.codi] || 'ti-ruler-2'}`} />
              {t(`pattern.taller.metode.${m.codi}`)}
            </button>
          )
        })}
      </div>

      {/* LES OPCIONS del mètode viu (avui, l'eix d'una cota de projecció). El bucle no sap
          quantes n'hi ha ni com es diuen: les serveix el vocabulari, i el dia que un mètode
          en porti una segona, surt sola. */}
      {Object.entries(opcions).map(([nom, valors]) => (
        <div key={nom} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <span>{t(`pattern.taller.opcio.${nom}`)}</span>
          {valors.map(v => {
            const actiu = valorOpcio(nom) === v
            return (
              <button
                key={clauValor(v)} aria-pressed={actiu}
                onClick={() => onOpcio(nom, v)}
                title={t(`pattern.taller.opcio_ajuda.${nom}.${clauValor(v)}`)}
                style={{
                  display: 'flex', alignItems: 'center', cursor: 'pointer',
                  color: 'var(--text-main)',
                  background: actiu ? 'var(--gold)' : 'var(--panel)',
                  border: `1px solid ${actiu ? 'var(--gold)' : 'var(--line)'}`,
                  ...METRICA_EINA_COMPACTA,
                }}
              >
                {t(`pattern.taller.opcio_valor.${nom}.${clauValor(v)}`)}
              </button>
            )
          })}
        </div>
      ))}

      {/* El comptador només per als gestos llargs: amb dos clics, la frase de l'avís ja ho diu
          tot i una fila de xips seria soroll. */}
      {ancores.length > 2 && (
        // `role="list"`/`"listitem"`: un <span> pelat té rol implícit `generic`, i l'ARIA
        // prohibeix el nom d'autor en aquest rol —o sigui que l'`aria-label` del xip no
        // arribava a cap lector de pantalla i es llegia només el text de dins. `listitem`
        // sí que l'admet. (`aria-current` és global i ja funcionava.)
        <div role="list" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          {ancores.map((nom, i) => {
            const fet = i < pas
            const ara = i === pas
            const estat = ara ? 'ara' : fet ? 'fet' : 'pendent'
            return (
              <span
                key={nom} role="listitem"
                aria-current={ara ? 'step' : undefined}
                aria-label={t(`pattern.taller.ancora_estat.${estat}`, {
                  ancora: t(`pattern.taller.ancora.${nom}`),
                })}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.2rem',
                  // Píndola i no radi 4: és un xip d'estat (NORMA §3). I «on soc» s'escriu
                  // amb `--sel` + filet d'or, mai amb el daurat ple —el daurat de fons és de
                  // CONTROL, i com a tinta de text no arriba a AA (3,16:1 sobre --sel).
                  borderRadius: 'var(--r-pill)', padding: '0.1rem 0.5rem',
                  border: `1px solid ${ara ? 'var(--gold-border)' : 'var(--line)'}`,
                  background: ara ? 'var(--sel)' : 'transparent',
                  // Sense `opacity`: apagar text de 10 px el deixava a 2,43:1. El que
                  // distingeix «fet» de «pendent» és l'icona, que no es compra amb contrast.
                  color: ara ? 'var(--text-main)' : 'var(--text-soft)',
                  // El pes és el SEGON canal de «on soc». Els dos cromàtics que la norma
                  // prescriu es queden, mesurats, per sota del llindar de visibilitat
                  // (fons --sel vs --panel = 1,09:1 · filet --gold-border vs --line =
                  // 1,29:1), i `ti-point` és el mateix glif que el del pas pendent. El pes
                  // és la mateixa tècnica que la norma ja fa servir per compensar.
                  fontWeight: ara ? 600 : 400,
                }}
              >
                <i className={`ti ${fet ? 'ti-check' : 'ti-point'}`} aria-hidden="true" />
                {t(`pattern.taller.ancora.${nom}`)}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}

function Avis({ text, err = false, onTanca = null, tancaEtiqueta = null }) {
  const { t } = useTranslation()
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.4rem', flexShrink: 0,
      fontSize: 'var(--fs-caption)',
      color: err ? 'var(--err)' : 'var(--text-soft)',
      background: err ? 'var(--err-bg)' : 'var(--bg-muted)',
      border: err ? '1px solid var(--err)' : '1px solid transparent',
      borderRadius: 4, padding: '0.3rem 0.6rem',
    }}>
      <i className={`ti ${err ? 'ti-alert-triangle' : 'ti-info-circle'}`} />
      <span style={{ flex: 1 }}>{text}</span>
      {onTanca && (
        <button
          onClick={onTanca}
          aria-label={tancaEtiqueta || t('app.close')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
        >
          <i className="ti ti-x" />
        </button>
      )}
    </div>
  )
}

function Capcalera({ t, model, fp, modelId, onTorna }) {
  return (
    <header style={{
      flexShrink: 0, height: 52, display: 'flex', alignItems: 'center', gap: '0.8rem',
      padding: '0 1rem', borderBottom: '1px solid var(--line)',
      background: 'var(--panel)',
    }}>
      <button
        onClick={onTorna}
        style={{
          display: 'flex', alignItems: 'center', gap: '0.35rem',
          background: 'var(--panel)', border: '1px solid var(--line)',
          borderRadius: 4, padding: '0.3rem 0.7rem', cursor: 'pointer',
          fontSize: 'var(--fs-body)', color: 'var(--text-main)',
        }}
      >
        <i className="ti ti-arrow-left" />
        {t('pattern.taller.back')}
      </button>

      <span style={{ width: 1, height: 22, background: 'var(--line)' }} />

      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0,
        fontSize: 'var(--fs-body)', color: 'var(--text-soft)',
      }}>
        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {model?.codi_intern || `#${modelId}`}
          {model?.nom_prenda ? ` · ${model.nom_prenda}` : ''}
        </span>
        <i className="ti ti-chevron-right" style={{ fontSize: 14 }} />
        <strong style={{ color: 'var(--text-main)', fontWeight: 600, whiteSpace: 'nowrap' }}>
          {t('pattern.taller.title')}
        </strong>
      </div>

      <span style={{ flex: 1 }} />

      {fp && (
        <span style={{
          display: 'flex', alignItems: 'center', gap: '0.4rem',
          fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
        }}>
          <i className="ti ti-file-vector" />
          <span style={{
            maxWidth: 280, whiteSpace: 'nowrap', overflow: 'hidden',
            textOverflow: 'ellipsis', fontFamily: 'var(--mono)',
          }}>
            {fp.nom_fitxer}
          </span>
          <span style={{
            border: `1px solid ${fp.is_current ? 'var(--gold)' : 'var(--line)'}`,
            borderRadius: 10, padding: '1px 8px',
            background: fp.is_current ? 'var(--sel)' : 'var(--panel)',
            color: 'var(--text-main)',
          }}>
            {t('pattern.version_option', { versio: fp.versio })}
          </span>
        </span>
      )}
    </header>
  )
}

function Centrat({ text, err = false }) {
  return (
    <div style={{
      flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: err ? 'var(--err)' : 'var(--text-soft)', fontSize: 'var(--fs-body)',
    }}>
      {text}
    </div>
  )
}
