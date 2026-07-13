import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { patterns, models, modelTasks } from '../api/endpoints'
import PatternViewer from '../components/pattern/PatternViewer'
import {
  arcDirigit, longitudTram, puntsDelSegment, situaPunt,
} from '../components/pattern/patternGeometry'
import PieceList from '../components/pattern/PieceList'
import ModelPomList from '../components/pattern/ModelPomList'
import RelationsPanel from '../components/pattern/RelationsPanel'
import POMPicker from '../components/pattern/POMPicker'
import SewEditor from '../components/pattern/SewEditor'
import SegmentEditor from '../components/pattern/SegmentEditor'
import { textCobertura, textEstat } from '../components/pattern/sewText'
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
  const [propostaRessaltada, setPropostaRessaltada] = useState(null)

  // ── eines d'anotació (venen del tab: es TRASLLADEN, no es reescriuen) ─────
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
  const [pomEditId, setPomEditId] = useState(null)
  const [tramEditId, setTramEditId] = useState(null)
  const [sewEditId, setSewEditId] = useState(null)
  // La recepta que s'està reobrint, dibuixada de fons: es veu D'ON es ve mentre es recol·loca.
  const [ombra, setOmbra] = useState(null)
  // El veredicte de l'última costura declarada. Surt IMMEDIAT: si la costura no casa, o si
  // trepitja la vora, saber-ho d'aquí a tres clics és saber-ho tard.
  const [veredicte, setVeredicte] = useState(null)
  const [tascaId, setTascaId] = useState(null)      // per al render: hi ha rellotge?
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

      const [{ data: detall }, { data: geo }, { data: sw }, { data: fn }, { data: pr }] =
        await Promise.all([
          patterns.get(triat.id),
          patterns.geometry(triat.id),
          patterns.sew.list(modelId),
          patterns.modelPoms(triat.id),
          patterns.sew.propostes(modelId, triat.id),
        ])
      setActual(detall)
      setGeometria(geo)
      setSews(sw.results || sw || [])
      setFeina(fn)
      setPropostes(pr.propostes || [])
      setDescartatsProp(pr.descartats || null)
    } catch {
      setError(t('pattern.err_load'))
    } finally {
      setCarregant(false)
    }
  }, [modelId, fileParam, t])

  useEffect(() => { carregar() }, [carregar])

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

  // Clicar una fila PENDENT de la llista de treball ÉS l'ordre de col·locar aquell POM:
  // no obre cap cercador, perquè ja se sap quin POM és. El canvas passa a guiar.
  const colocarPOM = (fila) => {
    setPomActiu(fila)
    setPuntsPom([])
    setPickerObert(false)
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

  // Esc surt. I la tecla d'INVERTIR (←/→/F) gira l'arc que s'està previsualitzant, abans de
  // fixar-lo: dos punts d'una vora tancada defineixen dos camins, i el que el cursor no digui
  // ho ha de poder dir el teclat. Només mentre hi ha un arc viu — una tecla que no fa res quan
  // no toca ensenya a no fer-ne cas.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') { cancelar(); return }
      const potInvertir = (mode === 'seg' || mode === 'pinca') && puntsPom.length > 0
      if (!potInvertir) return
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key.toLowerCase() === 'f') {
        e.preventDefault()
        setArcInvertit(v => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [cancelar, mode, puntsPom])

  const onClicPunt = (iman) => {
    const punt = iman.punt
    const maxPunts = mode === 'pinca' ? 3 : 2
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
      if (nous.length === 2 && mode === 'pom') {
        // Dos punts. Si sabem de quin POM es tracta —perquè s'està col·locant de la llista de
        // treball, o perquè s'està REOBRINT un d'ancorat— s'ancora i s'acaba. Si no (via
        // secundària: un POM que no és a la fitxa), llavors sí que cal preguntar quin és.
        const master = pomActiu?.pom_master ?? ombra?.pomMaster
        if (master) ancorar(master, nous[0], nous[1])
        else setPickerObert(true)
      }
      // En mode TRAM i PINÇA no es crea res encara: falta el nom, i el vistiplau.
      return nous
    })
  }

  /** L'ancoratge, un de sol per a tots els camins: el guiat, el del picker, i el de REOBRIR. */
  const ancorar = async (pomMasterId, a, b) => {
    const peca = pecaDelPunt(a)
    setPickerObert(false)
    try {
      // S'envia la RECEPTA, mai el valor: el valor el llegeix el servidor de la geometria.
      const recepta = { mode: 'points', a: a.id, b: b.id }
      if (pomEditId) {
        // REOBERT (T5a): es RECALCULA sobre el MATEIX PatternPOM. Esborrar-lo i crear-ne un
        // altre li canviaria l'id i li esborraria la data —i qualsevol cosa que un dia hi
        // pengi—, per una feina que és una correcció, no un ancoratge nou.
        await patterns.poms.update(pomEditId, { definicio_mesura: recepta })
      } else {
        await patterns.poms.create({
          pattern_piece: peca.id,
          pom_master: pomMasterId,
          definicio_mesura: recepta,
          metode: 'recta',
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
  const triarTram = (tram) => {
    const llista = costatActiu === 'a' ? segmentsA : segmentsB
    const set = costatActiu === 'a' ? setSegmentsA : setSegmentsB
    set(llista.includes(tram.id) ? llista.filter(x => x !== tram.id) : [...llista, tram.id])
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
        casa: !!e.casa,
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
    // Les PROPOSTES entren aquí i no en una crida a part: confirmar-ne una, esborrar una costura
    // o marcar una pinça canvia la COBERTURA, i amb ella el que encara es pot proposar. Rellegir
    // les relacions i deixar les propostes velles a la pantalla seria ensenyar una llista que ja
    // no és certa —i oferir per cosir un tram que acaba de quedar cosit.
    const [{ data: geo }, { data: sw }, { data: fn }, { data: pr }] = await Promise.all([
      patterns.geometry(actual.id),
      patterns.sew.list(modelId),
      patterns.modelPoms(actual.id),
      patterns.sew.propostes(modelId, actual.id),
    ])
    setGeometria(geo)
    setSews(sw.results || sw || [])
    setFeina(fn)
    setPropostes(pr.propostes || [])
    setDescartatsProp(pr.descartats || null)
  }, [actual, modelId])

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
        casa: !!e.casa,
        estat: textEstat(t, e, unit),
        missatge: e.missatge || '',
        cobertura: (e.cobertura || []).map(a => ({
          text: textCobertura(t, a, unit), missatge: a.missatge || '',
        })),
      })
      await recarregarRelacions()
    } catch {
      setErrEina(t('pattern.taller.err_proposal_confirm'))
    }
  }

  /** Rebutjar-ne una: que no torni a sortir. El «no» es desa; si no, no seria un «no». */
  const rebutjarProposta = async (p) => {
    setPropostaRessaltada(null)
    try {
      await patterns.sew.rebutjarProposta({
        model: modelId, segment_a: p.a.segment_id, segment_b: p.b.segment_id,
      })
      await recarregarRelacions()
    } catch {
      setErrEina(t('pattern.taller.err_proposal_reject'))
    }
  }

  /** El nom que un tram proposat tindrà quan la proposta es confirmi. */
  const nomTramProposat = (costat) => t('pattern.taller.proposal_seg', {
    peca: costat.peca, llarg: formatLen(costat.longitud_cm, unit),
  })

  /**
   * Els dos trams de la proposta que el cursor assenyala, amb la geometria que el canvas
   * necessita per pintar-los. Els trams proposats són DERIVATS ('auto') i per tant NO són a la
   * llista de trams declarats: el canvas no els té, i se li han de donar.
   */
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

  /** Reobrir un POM ancorat: la recepta torna al canvas i es torna a marcar A i B. */
  const reobrirPOM = (pom) => {
    const def = pom.definicio_mesura || {}
    netejarSeleccio()
    setPomEditId(pom.id)
    setOmbra({
      mena: 'pom',
      pomMaster: pom.pom_master,
      codi: pom.pom_code,
      punts: [def.a, def.b].map(id => puntPerId(id)).filter(Boolean),
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

  // Els POMs ancorats, per al panell de RELACIONS: viuen a la geometria, penjats de la peça
  // que mesuren. (El creuament amb la fitxa ja no es fa aquí: el fa el servidor, a
  // `model-poms`. Fer-lo dues vegades i de dues maneres seria demanar que divergissin.)
  const pomsAncorats = useMemo(() => (geometria?.pieces || []).flatMap(p =>
    (p.poms || []).map(x => ({ ...x, peca: p.nom_block }))), [geometria])

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
        casa: !!e.casa,
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
            peca: p.nom_block,
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

  return (
    <div style={{
      width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column',
      background: 'var(--bg-page)', overflow: 'hidden',
    }}>
      <Capcalera t={t} model={model} fp={actual} modelId={modelId} onTorna={tornar} />

      <main style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <aside style={{
          width: 360, flexShrink: 0, display: 'flex', flexDirection: 'column',
          minHeight: 0, borderRight: '1px solid var(--border)', background: 'var(--bg-page)',
        }}>
          <Contenidor
            titol={t('pattern.pieces', { n: geometria?.pieces?.length || 0 })}
            icona="ti-vector-triangle" pes={1}
          >
            {actual && (
              <PieceList pieces={actual.pieces} pecaSel={pecaSel} onTria={setPecaSel} />
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
              pomActiu={pomActiu}
              onColocar={colocarPOM}
              onAfegirFora={afegirPOMForaDeFitxa}
              unit={unit}
            />
          </Contenidor>

          <Contenidor titol={t('pattern.taller.relations')} icona="ti-link" pes={1}>
            <RelationsPanel
              poms={pomsAncorats} sews={costures} pinces={pinces} segments={trams}
              tramsPerId={tramsPerId} unit={unit}
              propostes={propostes} descartatsProp={descartatsProp}
              onConfirmaProposta={confirmarProposta}
              onRebutjaProposta={rebutjarProposta}
              onRessaltaProposta={setPropostaRessaltada}
              onEsborraPom={esborrarPOM} onReobrePom={reobrirPOM}
              onEsborraSew={esborrarSew} onReobreSew={reobrirSew}
              onReanomenaSew={reanomenarSew}
              onEsborraPinca={esborrarPinca} onReanomenaPinca={reanomenarSew}
              onReanomenaTram={reanomenarTram} onReobreTram={reobrirTram}
              onEsborraTram={esborrarTram}
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
          />

          {errEina && (
            <Avis text={errEina} err onTanca={() => setErrEina(null)} />
          )}
          {veredicte && (
            <Veredicte t={t} v={veredicte} onTanca={veredicteVist} />
          )}
          {mode === 'pom' && (
            <Avis
              text={ombra?.mena === 'pom'
                ? t('pattern.taller.pom_reopen_hint', { codi: ombra.codi })
                : pomActiu
                  ? t(puntsPom.length === 0
                      ? 'pattern.taller.place_a' : 'pattern.taller.place_b',
                      { codi: pomActiu.codi_client,
                        nom: pomActiu.nom_client || pomActiu.nom_canonic })
                  : t(puntsPom.length === 0
                      ? 'pattern.pom_hint_first' : 'pattern.pom_hint_second')}
              onTanca={cancelar}
              tancaEtiqueta={t('pattern.taller.cancel_place')}
            />
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
              pinces={pinces}
              propostaRessaltada={propostaAlCanvas}
              unit={unit}
              omplirAlcada
            />
          )}

          {pickerObert && (
            <POMPicker
              onTria={pom => ancorar(pom.id, puntsPom[0], puntsPom[1])}
              onCancel={() => { setPickerObert(false); setPuntsPom([]) }}
            />
          )}
        </section>
      </main>
    </div>
  )
}

const round2 = (v) => Math.round(v * 100) / 100

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Contenidor de la columna: capçalera fixa i cos amb scroll PROPI. Els tres desborden per
 * dins — mai la pàgina.
 *
 * El repartiment és amb PES, no a parts iguals: la llista de treball és on es passa l'estona
 * i necessita ensenyar files, no dues i mitja. I la capçalera es plega: qui està col·locant
 * POMs pot tancar Peces i Relacions i quedar-se la columna sencera per a la feina.
 */
function Contenidor({ titol, icona, pes = 1, children }) {
  const { t } = useTranslation()
  const [plegat, setPlegat] = useState(false)

  return (
    <div style={{
      // Plegat NO creix: deixa tota la seva alçada als altres, que és per això que es plega.
      flex: plegat ? '0 0 auto' : `${pes} 1 0`,
      minHeight: 0, display: 'flex', flexDirection: 'column',
      borderBottom: '1px solid var(--border)',
    }}>
      <button
        onClick={() => setPlegat(p => !p)}
        aria-expanded={!plegat}
        style={{
          flexShrink: 0, display: 'flex', alignItems: 'center', gap: '0.4rem',
          padding: '0.45rem 0.7rem', background: 'var(--bg-card)',
          border: 'none', borderBottom: '1px solid var(--border)',
          cursor: 'pointer', textAlign: 'left', width: '100%',
          fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase',
          letterSpacing: '0.03em', color: 'var(--text-muted)',
        }}
      >
        <i className={`ti ${icona}`} />
        <span style={{ flex: 1 }}>{titol}</span>
        <i
          className={`ti ${plegat ? 'ti-chevron-down' : 'ti-chevron-up'}`}
          title={plegat ? t('pattern.taller.expand') : t('pattern.taller.collapse')}
        />
      </button>
      {!plegat && (
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '0.5rem 0.6rem' }}>
          {children}
        </div>
      )}
    </div>
  )
}

/**
 * Barra d'eines. Els botons NO obren ni pausen la tasca: això ho fa entrar i sortir del
 * taller. Aquí només es tria QUÈ s'està fent — i si no hi ha rellotge (403 de perfil),
 * les eines no s'ofereixen: el patró es pot mirar, però no anotar sense comptar el temps.
 */
function BarraEines({ t, mode, onMode, tascaId, errTasca }) {
  const boto = (actiu) => ({
    background: actiu ? 'var(--gold)' : 'var(--white)',
    color: actiu ? 'var(--white)' : 'var(--text-main)',
    border: `1px solid ${actiu ? 'var(--gold)' : 'var(--border)'}`,
    borderRadius: 4, padding: '0.35rem 0.8rem',
    cursor: tascaId ? 'pointer' : 'not-allowed',
    opacity: tascaId ? 1 : 0.5,
    fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', gap: '0.35rem',
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
          fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
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
  return (
    <div style={{
      flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 4,
      border: `1px solid ${v.casa ? 'var(--ok)' : 'var(--err)'}`,
      background: v.casa ? 'var(--ok-bg)' : 'var(--err-bg)',
      borderRadius: 4, padding: '0.4rem 0.6rem', fontSize: 'var(--fs-caption)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <i className={`ti ${v.casa ? 'ti-check' : 'ti-alert-triangle'}`}
           style={{ color: v.casa ? 'var(--ok)' : 'var(--err)' }} />
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

function Avis({ text, err = false, onTanca = null, tancaEtiqueta = null }) {
  const { t } = useTranslation()
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.4rem', flexShrink: 0,
      fontSize: 'var(--fs-caption)',
      color: err ? 'var(--err)' : 'var(--text-muted)',
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
      padding: '0 1rem', borderBottom: '1px solid var(--border)',
      background: 'var(--bg-card)',
    }}>
      <button
        onClick={onTorna}
        style={{
          display: 'flex', alignItems: 'center', gap: '0.35rem',
          background: 'var(--white)', border: '1px solid var(--border)',
          borderRadius: 4, padding: '0.3rem 0.7rem', cursor: 'pointer',
          fontSize: 'var(--fs-body)', color: 'var(--text-main)',
        }}
      >
        <i className="ti ti-arrow-left" />
        {t('pattern.taller.back')}
      </button>

      <span style={{ width: 1, height: 22, background: 'var(--border)' }} />

      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0,
        fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
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
          fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
        }}>
          <i className="ti ti-file-vector" />
          <span style={{
            maxWidth: 280, whiteSpace: 'nowrap', overflow: 'hidden',
            textOverflow: 'ellipsis', fontFamily: 'var(--mono)',
          }}>
            {fp.nom_fitxer}
          </span>
          <span style={{
            border: `1px solid ${fp.is_current ? 'var(--gold)' : 'var(--border)'}`,
            borderRadius: 10, padding: '1px 8px',
            background: fp.is_current ? 'var(--gold-pale)' : 'var(--white)',
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
      color: err ? 'var(--err)' : 'var(--text-muted)', fontSize: 'var(--fs-body)',
    }}>
      {text}
    </div>
  )
}
