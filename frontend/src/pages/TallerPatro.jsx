import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { patterns, models, modelTasks } from '../api/endpoints'
import PatternViewer from '../components/pattern/PatternViewer'
import { longitudTram } from '../components/pattern/patternGeometry'
import PieceList from '../components/pattern/PieceList'
import ModelPomList from '../components/pattern/ModelPomList'
import RelationsPanel from '../components/pattern/RelationsPanel'
import POMPicker from '../components/pattern/POMPicker'
import SewEditor from '../components/pattern/SewEditor'

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

  // ── eines d'anotació (venen del tab: es TRASLLADEN, no es reescriuen) ─────
  const [mode, setMode] = useState('view')          // 'view' | 'pom' | 'sew'
  const [puntsPom, setPuntsPom] = useState([])      // punts clicats (imantats)
  const [pickerObert, setPickerObert] = useState(false)
  const [segmentsA, setSegmentsA] = useState([])
  const [segmentsB, setSegmentsB] = useState([])
  const [costatActiu, setCostatActiu] = useState('a')
  const [tipusSew, setTipusSew] = useState('casat')
  const [diferencial, setDiferencial] = useState(0)
  // El POM que s'està col·locant. Amb pomActiu, el canvas SAP quin POM marca i no cal cap
  // cercador: A → B → ancorat. Sense pomActiu, el mode POM és la via secundària (el POM
  // que no és a la fitxa) i llavors sí que cal preguntar quin és — el picker.
  const [pomActiu, setPomActiu] = useState(null)
  const [tascaId, setTascaId] = useState(null)      // per al render: hi ha rellotge?
  const [errTasca, setErrTasca] = useState(null)
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

      const [{ data: detall }, { data: geo }, { data: sw }, { data: fn }] =
        await Promise.all([
          patterns.get(triat.id),
          patterns.geometry(triat.id),
          patterns.sew.list(modelId),
          patterns.modelPoms(triat.id),
        ])
      setActual(detall)
      setGeometria(geo)
      setSews(sw.results || sw || [])
      setFeina(fn)
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
  }, [])

  const triarMode = (nou) => {
    setMode(m => (m === nou ? 'view' : nou))
    netejarSeleccio()
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

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') cancelar() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [cancelar])

  const onClicPunt = (iman) => {
    const punt = iman.punt
    // Forma FUNCIONAL a posta: llegir `puntsPom` del closure el faria servir el valor
    // d'abans del clic anterior si dos events arriben junts, i la mesura acabaria unint
    // un punt amb ell mateix.
    setPuntsPom(prev => {
      // Clicar dues vegades el MATEIX punt no és una mesura: és un zero. El segon clic
      // sobre el punt ja triat el DESTRIA, que és el que espera qui s'ha equivocat.
      if (prev.length && prev[prev.length - 1].id === punt.id) return prev.slice(0, -1)
      const nous = [...prev, punt].slice(-2)
      if (nous.length === 2) {
        // Dos punts. Si sabem quin POM s'està col·locant, s'ancora i s'acaba; si no (via
        // secundària), llavors sí que s'ha de preguntar quin és.
        if (pomActiu) ancorar(pomActiu.pom_master, nous[0], nous[1])
        else setPickerObert(true)
      }
      return nous
    })
  }

  /** L'ancoratge, un de sol per als dos camins: el guiat i el del picker. */
  const ancorar = async (pomMasterId, a, b) => {
    const peca = pecaDelPunt(a)
    setPickerObert(false)
    try {
      // S'envia la RECEPTA, mai el valor: el valor el llegeix el servidor de la geometria.
      await patterns.poms.create({
        pattern_piece: peca.id,
        pom_master: pomMasterId,
        definicio_mesura: { mode: 'points', a: a.id, b: b.id },
        metode: 'recta',
      })
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

  const onClicSegment = (seg) => {
    const llista = costatActiu === 'a' ? segmentsA : segmentsB
    const set = costatActiu === 'a' ? setSegmentsA : setSegmentsB
    set(llista.includes(seg.id) ? llista.filter(x => x !== seg.id) : [...llista, seg.id])
  }

  const declararCostura = async () => {
    try {
      await patterns.sew.create({
        model: modelId,
        segments_a: segmentsA,
        segments_b: segmentsB,
        tipus: tipusSew,
        diferencial_cm: parseFloat(diferencial) || 0,
      })
      netejarSeleccio()
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
    const [{ data: geo }, { data: sw }, { data: fn }] = await Promise.all([
      patterns.geometry(actual.id),
      patterns.sew.list(modelId),
      patterns.modelPoms(actual.id),
    ])
    setGeometria(geo)
    setSews(sw.results || sw || [])
    setFeina(fn)
  }, [actual, modelId])

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
    if (mode !== 'pom') return null
    if (puntsPom.length > 0) return pecaDelPunt(puntsPom[0])?.nom_block || null
    return pecaSel || null
  }, [mode, puntsPom, pecaSel, pecaDelPunt])

  // Els trams DECLARATS. De la geometria en surten TOTS —els que el motor proposa (gir→gir,
  // origen 'auto') i els que algú ha declarat—, però al taller només manen els declarats: la
  // proposta del motor és una hipòtesi de lectura, no una vora que ningú hagi dit que existeixi.
  //
  // La longitud i l'«en ús» es calculen aquí perquè ja tenim tot el que fa falta: la vora
  // (per a la longitud) i les costures (per saber qui el reté). Demanar-los al servidor seria
  // una tercera crida per a dades que ja són a la pantalla.
  const trams = useMemo(() => {
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
            />
          </Contenidor>

          <Contenidor titol={t('pattern.taller.relations')} icona="ti-link" pes={1}>
            <RelationsPanel
              poms={pomsAncorats} sews={sews} segments={trams}
              onEsborraPom={esborrarPOM}
              onEsborraSew={esborrarSew}
              onReanomenaTram={reanomenarTram}
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
          {mode === 'pom' && (
            <Avis
              text={pomActiu
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
          {mode === 'sew' && (
            <SewEditor
              segmentsA={segmentsA} segmentsB={segmentsB}
              costatActiu={costatActiu} onCostat={setCostatActiu}
              tipus={tipusSew} onTipus={setTipusSew}
              diferencial={diferencial} onDiferencial={setDiferencial}
              onDeclara={declararCostura}
              onNeteja={netejarSeleccio}
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
              onClicSegment={onClicSegment}
              pecaIman={pecaIman}
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
