import { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { patterns, models, baseMeasurements } from '../api/endpoints'
import PatternViewer from '../components/pattern/PatternViewer'
import PieceList from '../components/pattern/PieceList'
import ModelPomList from '../components/pattern/ModelPomList'
import RelationsPanel from '../components/pattern/RelationsPanel'

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
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [carregant, setCarregant] = useState(true)
  const [error, setError] = useState(null)
  const [model, setModel] = useState(null)
  const [actual, setActual] = useState(null)       // el PatternFile obert
  const [geometria, setGeometria] = useState(null)
  const [sews, setSews] = useState([])
  const [trams, setTrams] = useState([])           // segments DECLARATS
  const [mesures, setMesures] = useState([])       // BaseMeasurement del model
  const [pecaSel, setPecaSel] = useState('')

  // El taller s'obre SEMPRE sobre un fitxer concret. Si no ve per `?file=`, s'agafa el
  // vigent del model: entrar-hi sense fitxer és un accident de navegació, no una
  // instrucció d'obrir el taller buit.
  const carregar = useCallback(async () => {
    setCarregant(true)
    try {
      const [{ data: m }, { data: llista }, { data: bm }] = await Promise.all([
        models.get(modelId),
        patterns.list(modelId),
        baseMeasurements.list(modelId),
      ])
      setModel(m)
      setMesures(bm.results || bm || [])

      const files = llista.results || llista || []
      const triat = (fileParam && files.find(f => f.id === parseInt(fileParam)))
        || files.find(f => f.is_current)
        || files[0]
      if (!triat) { setActual(null); return }

      const [{ data: detall }, { data: geo }, { data: sw }, { data: sg }] = await Promise.all([
        patterns.get(triat.id),
        patterns.geometry(triat.id),
        patterns.sew.list(modelId),
        patterns.segments.list(triat.id),
      ])
      setActual(detall)
      setGeometria(geo)
      setSews(sw.results || sw || [])
      setTrams(tramsDeclarats(sg))
    } catch {
      setError(t('pattern.err_load'))
    } finally {
      setCarregant(false)
    }
  }, [modelId, fileParam, t])

  useEffect(() => { carregar() }, [carregar])

  // Després de tocar una relació es rellegeix TOT el que en depèn: esborrar una costura
  // canvia la cobertura de les altres i allibera els seus trams. Rellegir només el que
  // s'ha tocat deixaria la resta mentint a la pantalla.
  const recarregarRelacions = useCallback(async () => {
    if (!actual) return
    const [{ data: geo }, { data: sw }, { data: sg }] = await Promise.all([
      patterns.geometry(actual.id),
      patterns.sew.list(modelId),
      patterns.segments.list(actual.id),
    ])
    setGeometria(geo)
    setSews(sw.results || sw || [])
    setTrams(tramsDeclarats(sg))
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

  // Els POMs ancorats viuen a la geometria (penjats de la peça que mesuren); la llista de
  // Mesures del model viu al model. La frontissa entre els dos mons és el POMMaster.
  const pomsAncorats = useMemo(() => (geometria?.pieces || []).flatMap(p =>
    (p.poms || []).map(x => ({ ...x, peca: p.nom_block }))), [geometria])

  const ancoratsPerPom = useMemo(() => {
    const m = new Map()
    pomsAncorats.forEach(p => m.set(p.pom_master, p))
    return m
  }, [pomsAncorats])

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
            icona="ti-vector-triangle"
          >
            {actual && (
              <PieceList pieces={actual.pieces} pecaSel={pecaSel} onTria={setPecaSel} />
            )}
          </Contenidor>

          <Contenidor
            titol={t('pattern.taller.model_poms', {
              ancorats: ancoratsPerPom.size, total: mesures.length,
            })}
            icona="ti-ruler-measure"
          >
            <ModelPomList mesures={mesures} ancorats={ancoratsPerPom} />
          </Contenidor>

          <Contenidor titol={t('pattern.taller.relations')} icona="ti-link">
            <RelationsPanel
              poms={pomsAncorats} sews={sews} segments={trams}
              onEsborraPom={esborrarPOM}
              onEsborraSew={esborrarSew}
              onReanomenaTram={reanomenarTram}
              onEsborraTram={esborrarTram}
            />
          </Contenidor>
        </aside>

        <section style={{
          flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column',
          minHeight: 0, padding: '0.6rem 0.8rem',
        }}>
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
              omplirAlcada
            />
          )}
        </section>
      </main>
    </div>
  )
}

// Del fitxer en surten TOTS els trams: els que el motor proposa (gir→gir, origen 'auto')
// i els que algú ha declarat. Al taller només manen els DECLARATS — la proposta del motor
// és una hipòtesi de lectura, no una vora que ningú hagi dit que existeixi.
const tramsDeclarats = (data) =>
  (data.results || data || []).filter(s => s.origen === 'declarat')

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Contenidor de la columna: capçalera fixa i cos amb scroll PROPI. Els tres es reparteixen
 * l'alçada i cadascun desborda per dins — mai la pàgina.
 */
function Contenidor({ titol, icona, children }) {
  return (
    <div style={{
      flex: '1 1 0', minHeight: 0, display: 'flex', flexDirection: 'column',
      borderBottom: '1px solid var(--border)',
    }}>
      <div style={{
        flexShrink: 0, display: 'flex', alignItems: 'center', gap: '0.4rem',
        padding: '0.45rem 0.7rem', background: 'var(--bg-card)',
        borderBottom: '1px solid var(--border)',
        fontSize: 'var(--fs-label)', fontWeight: 600, textTransform: 'uppercase',
        letterSpacing: '0.03em', color: 'var(--text-muted)',
      }}>
        <i className={`ti ${icona}`} />
        {titol}
      </div>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '0.5rem 0.6rem' }}>
        {children}
      </div>
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
